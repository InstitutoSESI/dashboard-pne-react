import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd


DATA_PIPELINE_DIR = Path(__file__).resolve().parents[2]
if str(DATA_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_PIPELINE_DIR))

from research.projections.education_attendance_projection_experiment import (  # noqa: E402
    Candidate,
    ForecastEngine,
    _theil_sen_log_slope,
    deterministic_split,
    paired_municipality_bootstrap,
    prediction_detail,
    select_one_standard_error,
    summarize_detail,
)


class EducationAttendanceProjectionExperimentTests(unittest.TestCase):
    def test_robust_slope_recovers_log_growth(self):
        years = np.arange(2007, 2017, dtype=float)
        values = np.expm1(4 + 0.03 * (years - years[0]))
        slope, count = _theil_sen_log_slope(
            years, values, window=None, exclude_pandemic=False
        )
        self.assertEqual(count, 10)
        self.assertAlmostEqual(slope, 0.03, places=8)

    def test_robust_slope_can_exclude_pandemic_years(self):
        years = np.arange(2017, 2026, dtype=float)
        values = np.array([100, 102, 104, 30, 35, 40, 112, 114, 116], dtype=float)
        included, _ = _theil_sen_log_slope(
            years, values, window=None, exclude_pandemic=False
        )
        excluded, count = _theil_sen_log_slope(
            years, values, window=None, exclude_pandemic=True
        )
        self.assertEqual(count, 6)
        self.assertNotAlmostEqual(excluded, included, places=6)

    def test_split_is_deterministic_stratified_and_exact(self):
        rows = [
            {"ano": 2025, "codigo_municipio": f"43{index:05d}", "obrigatoria_4_17": index}
            for index in range(1, 498)
        ]
        frame = pd.DataFrame(rows)
        first = deterministic_split(frame, seed=123, stratification_year=2025)
        second = deterministic_split(frame, seed=123, stratification_year=2025)
        pd.testing.assert_frame_equal(first, second)
        self.assertEqual(int(first["role"].eq("heldout").sum()), 118)
        self.assertEqual(set(first["size_stratum"]), {1, 2, 3, 4})
        self.assertTrue(
            first.loc[first["role"].eq("heldout")]
            .groupby("size_stratum")
            .size()
            .between(29, 30)
            .all()
        )

    def test_forecast_persistence_keeps_origin_value(self):
        enrollment = pd.DataFrame(
            {
                "ano": list(range(2014, 2026)),
                "codigo_municipio": ["4300001"] * 12,
                "creche": np.arange(12, dtype=float),
            }
        )
        points = pd.DataFrame(
            {
                "origin_numerator": [10.0],
                "codigo_municipio": ["4300001"],
                "origin_year": [2024],
                "target_year": [2025],
                "horizon": [1],
            }
        )
        engine = ForecastEngine(enrollment, "creche")
        forecast = engine.predict(Candidate("p", "persistence", 0), points)
        self.assertEqual(forecast.tolist(), [10.0])

    def test_municipal_shrinkage_stays_between_local_and_state_slopes(self):
        years = list(range(2014, 2026))
        rows = []
        for year in years:
            rows.append(
                {
                    "ano": year,
                    "codigo_municipio": "4300001",
                    "creche": 100 * 1.08 ** (year - 2014),
                }
            )
            rows.append(
                {
                    "ano": year,
                    "codigo_municipio": "4300002",
                    "creche": 900 * 1.01 ** (year - 2014),
                }
            )
        engine = ForecastEngine(pd.DataFrame(rows), "creche")
        candidate = Candidate(
            "s", "municipal_shrink", 3, 2014, None, 0.9, 12.0, False
        )
        state_slope, _ = engine.state_slope(candidate, 2024)
        local_slope, _ = engine.local_slope(candidate, "4300001", 2024)
        points = pd.DataFrame(
            {
                "origin_numerator": [100 * 1.08**10],
                "codigo_municipio": ["4300001"],
                "origin_year": [2024],
                "target_year": [2025],
                "horizon": [1],
            }
        )
        forecast = float(engine.predict(candidate, points)[0])
        state_only = np.expm1(np.log1p(points.loc[0, "origin_numerator"]) + state_slope * 0.9)
        local_only = np.expm1(np.log1p(points.loc[0, "origin_numerator"]) + local_slope * 0.9)
        self.assertGreater(forecast, min(state_only, local_only))
        self.assertLess(forecast, max(state_only, local_only))

    def test_one_standard_error_prefers_simpler_eligible_model(self):
        summary = pd.DataFrame(
            [
                {
                    "candidate_id": "complex",
                    "mae_percentage_points": 2.0,
                    "cluster_standard_error": 0.2,
                    "complexity": 3,
                },
                {
                    "candidate_id": "simple",
                    "mae_percentage_points": 2.1,
                    "cluster_standard_error": 0.1,
                    "complexity": 0,
                },
            ]
        )
        best, selected, threshold = select_one_standard_error(summary)
        self.assertEqual(best, "complex")
        self.assertEqual(selected, "simple")
        self.assertAlmostEqual(threshold, 2.2)

    def test_exact_tie_prefers_later_history_start(self):
        summary = pd.DataFrame(
            [
                {
                    "candidate_id": "start_2007",
                    "mae_percentage_points": 2.0,
                    "cluster_standard_error": 0.0,
                    "complexity": 3,
                    "history_start": 2007,
                },
                {
                    "candidate_id": "start_2014",
                    "mae_percentage_points": 2.0,
                    "cluster_standard_error": 0.0,
                    "complexity": 3,
                    "history_start": 2014,
                },
            ]
        )
        best, selected, _ = select_one_standard_error(summary)
        self.assertEqual(best, "start_2014")
        self.assertEqual(selected, "start_2014")

    def test_bootstrap_is_paired_by_municipality_and_deterministic(self):
        points = pd.DataFrame(
            {
                "codigo_municipio": ["1", "1", "2", "2"],
                "origin_year": [2023, 2024, 2023, 2024],
                "target_year": [2024, 2025, 2024, 2025],
                "horizon": [1, 1, 1, 1],
                "origin_numerator": [1.0] * 4,
                "actual_numerator": [1.0] * 4,
                "predicted_population": [1.0] * 4,
                "actual_population": [1.0] * 4,
                "actual_coverage_raw": [100.0] * 4,
            }
        )
        current = prediction_detail(points, np.array([1.2] * 4), "current")
        candidate = prediction_detail(points, np.array([1.1] * 4), "candidate")
        first = paired_municipality_bootstrap(current, candidate, iterations=100, seed=9)
        second = paired_municipality_bootstrap(current, candidate, iterations=100, seed=9)
        self.assertEqual(first, second)
        self.assertAlmostEqual(first["mean_improvement_pp"], 10.0)

    def test_model_selection_metric_is_not_erased_by_display_cap(self):
        points = pd.DataFrame(
            {
                "codigo_municipio": ["4300001"],
                "origin_year": [2024],
                "target_year": [2025],
                "horizon": [1],
                "origin_numerator": [100.0],
                "actual_numerator": [120.0],
                "predicted_population": [100.0],
                "actual_population": [100.0],
                "actual_coverage_raw": [120.0],
            }
        )
        detail = prediction_detail(points, np.array([100.0]), "candidate")
        summary = summarize_detail(detail)
        self.assertAlmostEqual(summary["numerator_model_mae_pp"], 20.0)
        self.assertAlmostEqual(summary["scenario_mae_pp"], 20.0)
        self.assertAlmostEqual(summary["display_capped_mae_pp"], 0.0)


if __name__ == "__main__":
    unittest.main()
