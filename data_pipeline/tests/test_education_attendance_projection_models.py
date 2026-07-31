import math
import sys
import unittest
from pathlib import Path

import pandas as pd


DATA_PIPELINE_DIR = Path(__file__).resolve().parents[1]
if str(DATA_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_PIPELINE_DIR))

from src.education_attendance_projection_models import (  # noqa: E402
    combine_municipal_state_log_trends,
    forecast_damped_log_value,
    theil_sen_log_slope,
)
from src.pne_2026_projections import (  # noqa: E402
    INDICATOR_CONFIGS,
    MODEL_VALIDATION,
    MODEL_VALIDATION_VALUE_POLICY,
    MUNICIPAL_SHRINK_NUMERATOR_MODEL,
    PERSISTENCE_NUMERATOR_MODEL,
    STATE_DAMPED_HOLT_NUMERATOR_MODEL,
    build_indicator_projection,
    project_numerator,
)
from scripts.rematerialize_education_attendance_projections import (  # noqa: E402
    EXPECTED_METHODS,
    EXPECTED_TREND_BASES,
)


def _parameters(window: int) -> dict:
    return {
        "candidateId": (
            f"municipal_shrink_h2014_w{window}_d0.80_all_years_k4"
        ),
        "historyStartYear": 2014,
        "windowObservations": window,
        "damping": 0.8,
        "shrinkage": 4,
        "excludedYears": [],
        "maximumAbsoluteAnnualLogTrend": 0.15,
    }


def _log_linear_series(start_year: int, count: int, level: float, slope: float):
    return [
        {
            "ano": year,
            "valor": math.expm1(level + slope * (year - start_year)),
        }
        for year in range(start_year, start_year + count)
    ]


class SharedProjectionModelTests(unittest.TestCase):
    def test_theil_sen_accepts_zero_ignores_non_finite_and_clips(self):
        zero_slope, zero_count = theil_sen_log_slope(
            [2021, 2022, 2023, 2024, 2025],
            [0, 0, 0, 0, 0],
            window=5,
        )
        clipped, count = theil_sen_log_slope(
            [2019, 2020, 2021, 2022, 2023, 2024, 2025],
            [1, float("nan"), 10, 100, float("inf"), 10_000, 100_000],
            window=5,
        )

        self.assertEqual((zero_slope, zero_count), (0.0, 5))
        self.assertEqual(count, 5)
        self.assertEqual(clipped, 0.15)

    def test_shrinkage_weights_follow_n_over_n_plus_four(self):
        five = combine_municipal_state_log_trends(0.01, 0.10, 5, 4)
        eight = combine_municipal_state_log_trends(0.01, 0.10, 8, 4)

        self.assertAlmostEqual(five.municipal_weight, 5 / 9)
        self.assertAlmostEqual(five.state_weight, 4 / 9)
        self.assertAlmostEqual(five.slope, (5 / 9) * 0.10 + (4 / 9) * 0.01)
        self.assertAlmostEqual(eight.municipal_weight, 2 / 3)
        self.assertAlmostEqual(eight.state_weight, 1 / 3)

    def test_fallbacks_are_deterministic(self):
        no_state = combine_municipal_state_log_trends(None, 0.03, 5, 4)
        no_local = combine_municipal_state_log_trends(0.02, None, 0, 4)

        self.assertIsNone(no_state.slope)
        self.assertEqual(no_state.fallback, "persistence_missing_state_trend")
        self.assertEqual(no_local.slope, 0.02)
        self.assertEqual(
            no_local.fallback,
            "state_only_missing_municipal_trend",
        )
        self.assertIsNone(forecast_damped_log_value(float("nan"), 0.01, 0.8, 1))


class ProductionProjectionSelectionTests(unittest.TestCase):
    def test_five_year_candidate_matches_the_validated_formula(self):
        local = _log_linear_series(2021, 5, 4.0, 0.09)
        state = _log_linear_series(2021, 5, 8.0, 0.01)
        result = project_numerator(
            local,
            target_years=[2026],
            model=MUNICIPAL_SHRINK_NUMERATOR_MODEL,
            state_series=state,
            model_parameters=_parameters(5),
        )

        expected_slope = (5 / 9) * 0.09 + (4 / 9) * 0.01
        expected = round(
            math.expm1(
                math.log1p(local[-1]["valor"])
                + expected_slope * 0.8
            ),
            1,
        )
        details = result["trend"]["municipalStateModel"]

        self.assertTrue(result["available"])
        self.assertEqual(result["projected"], [{"ano": 2026, "valor": expected}])
        self.assertAlmostEqual(details["municipalWeight"], 5 / 9)
        self.assertAlmostEqual(details["stateWeight"], 4 / 9)
        self.assertEqual(
            result["trend"]["selectedBasis"],
            MUNICIPAL_SHRINK_NUMERATOR_MODEL,
        )

    def test_eight_year_candidate_uses_two_thirds_municipal_weight(self):
        result = project_numerator(
            _log_linear_series(2018, 8, 4.0, 0.05),
            target_years=[2026],
            model=MUNICIPAL_SHRINK_NUMERATOR_MODEL,
            state_series=_log_linear_series(2018, 8, 8.0, 0.01),
            model_parameters=_parameters(8),
        )

        self.assertTrue(result["available"])
        self.assertAlmostEqual(
            result["trend"]["municipalStateModel"]["municipalWeight"],
            2 / 3,
        )

    def test_missing_state_trend_falls_back_to_persistence(self):
        local = _log_linear_series(2021, 5, 4.0, 0.05)
        result = project_numerator(
            local,
            target_years=[2026, 2027],
            model=MUNICIPAL_SHRINK_NUMERATOR_MODEL,
            state_series=[],
            model_parameters=_parameters(5),
        )

        expected = round(local[-1]["valor"], 1)
        self.assertTrue(result["available"])
        self.assertEqual(
            [point["valor"] for point in result["projected"]],
            [expected, expected],
        )
        self.assertEqual(
            result["trend"]["municipalStateModel"]["fallback"],
            "persistence_missing_state_trend",
        )

    def test_only_the_three_authorized_model_selections_changed(self):
        self.assertEqual(
            {
                key: config["numerator_model"]
                for key, config in INDICATOR_CONFIGS.items()
            },
            {
                "creche": PERSISTENCE_NUMERATOR_MODEL,
                "pre_escola": PERSISTENCE_NUMERATOR_MODEL,
                "basico_6_17": MUNICIPAL_SHRINK_NUMERATOR_MODEL,
                "basico_15_17": STATE_DAMPED_HOLT_NUMERATOR_MODEL,
                "infantil_0_5": PERSISTENCE_NUMERATOR_MODEL,
                "obrigatoria_4_17": MUNICIPAL_SHRINK_NUMERATOR_MODEL,
                "escolar_6_14": PERSISTENCE_NUMERATOR_MODEL,
            },
        )
        self.assertEqual(
            EXPECTED_TREND_BASES,
            {
                "creche": "last_observation_persistence",
                "pre_escola": "last_observation_persistence",
                "basico_6_17": MUNICIPAL_SHRINK_NUMERATOR_MODEL,
                "basico_15_17": "state_aggregate_damped_holt",
                "infantil_0_5": "last_observation_persistence",
                "obrigatoria_4_17": MUNICIPAL_SHRINK_NUMERATOR_MODEL,
                "escolar_6_14": "last_observation_persistence",
            },
        )
        self.assertEqual(
            EXPECTED_METHODS["pre_escola"],
            "last_observed_numerator_with_state_age_denominator",
        )

    def test_validation_metadata_uses_raw_uncapped_error(self):
        self.assertEqual(
            MODEL_VALIDATION_VALUE_POLICY,
            {
                "metric": (
                    "100_abs_predicted_minus_observed_numerator_over_"
                    "observed_target_population"
                ),
                "valuePolicy": "raw_without_display_cap",
                "displayCapApplied": False,
            },
        )
        self.assertEqual(
            MODEL_VALIDATION["pre_escola"]["improvementBootstrap95"],
            [1.7792, 3.5227],
        )
        self.assertEqual(
            MODEL_VALIDATION["basico_6_17"]["selectedCandidate"],
            "municipal_shrink_h2014_w5_d0.80_all_years_k4",
        )
        self.assertEqual(
            MODEL_VALIDATION["obrigatoria_4_17"]["selectedCandidate"],
            "municipal_shrink_h2014_w8_d0.80_all_years_k4",
        )

    def test_municipal_state_model_has_an_exact_public_method(self):
        cases = {
            "basico_6_17": ("mat_basico_6_17", "pop_6_17", "6-17"),
            "obrigatoria_4_17": ("mat_basico_4_17", "pop_4_17", "4-17"),
        }
        for indicator_key, (numerator, denominator, age_group) in cases.items():
            rows = []
            for municipality, level, slope in (
                ("A", 4.0, 0.04),
                ("B", 6.0, 0.01),
            ):
                for point in _log_linear_series(2018, 8, level, slope):
                    rows.append(
                        {
                            "municipio": municipality,
                            "ano": point["ano"],
                            numerator: point["valor"],
                            denominator: 1000.0,
                        }
                    )
            result = build_indicator_projection(
                "A",
                {"key": indicator_key},
                {
                    age_group: pd.Series(
                        {year: 1000.0 for year in range(2025, 2037)},
                        dtype=float,
                    )
                },
                dataframe=pd.DataFrame(rows),
            )

            self.assertTrue(result["available"], indicator_key)
            self.assertEqual(
                result["method"],
                (
                    "municipal_state_shrunk_theil_sen_log_enrollment_"
                    "with_state_age_denominator"
                ),
            )
            self.assertEqual(
                result["trend"]["selectedBasis"],
                MUNICIPAL_SHRINK_NUMERATOR_MODEL,
            )

    def test_cap_is_only_display_and_raw_value_is_preserved_for_audit(self):
        frame = pd.DataFrame(
            {
                "municipio": ["A"] * 5,
                "ano": list(range(2021, 2026)),
                "mat_infantil_pre": [120.0] * 5,
                "pop_4_5": [100.0] * 5,
            }
        )
        rs_by_group = {
            "4-5": pd.Series(
                {year: 100.0 for year in range(2025, 2037)},
                dtype=float,
            )
        }

        result = build_indicator_projection(
            "A",
            {"key": "pre_escola"},
            rs_by_group,
            dataframe=frame,
        )

        self.assertTrue(result["available"])
        self.assertEqual(result["projected_percent_raw"], [120.0] * 11)
        self.assertEqual(result["projected_percent"], [100.0] * 11)
        self.assertEqual(result["projected_at_target_raw"], 120.0)
        self.assertEqual(result["projected_at_target"], 100.0)
        self.assertEqual(result["distance_to_target"], 0.0)


if __name__ == "__main__":
    unittest.main()
