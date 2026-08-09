import sys
import unittest
from pathlib import Path

import pandas as pd


DATA_PIPELINE_DIR = Path(__file__).resolve().parents[1]
if str(DATA_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_PIPELINE_DIR))

from src.pne_state_reference import (  # noqa: E402
    COMPARABLE,
    RATIO_CONFIGS,
    _build_census_records,
    _build_escolas_integral_records,
    _build_medio_tecnico_participacao_records,
    _build_subsequente_records,
    _finalize_series,
    aggregate_ratio_of_sums,
    build_state_projections,
)


class StateReferenceTests(unittest.TestCase):
    def test_unavailable_records_do_not_form_a_pseudo_series(self):
        unavailable = [
            {"year": 2024, "value": None, "comparison_status": "unavailable"},
            {"year": 2025, "value": None, "comparison_status": "unavailable"},
        ]
        status, series = _finalize_series(unavailable)

        self.assertEqual(status, "unavailable")
        self.assertEqual(series, [])

        comparable = unavailable + [
            {"year": 2026, "value": 1.0, "comparison_status": COMPARABLE}
        ]
        status, series = _finalize_series(comparable)
        self.assertEqual(status, COMPARABLE)
        self.assertEqual(series, comparable)

    def test_uses_ratio_of_sums_instead_of_mean_municipal_percentages(self):
        frame = pd.DataFrame(
            [
                {"ano": 2025, "municipio": "A", "numerador": 1, "denominador": 2},
                {"ano": 2025, "municipio": "B", "numerador": 9, "denominador": 100},
            ]
        )

        record = aggregate_ratio_of_sums(
            frame,
            "numerador",
            "denominador",
            indicator_id="teste",
            municipalities_expected=2,
        )[0]

        self.assertAlmostEqual(record["value"], 100 * 10 / 102)
        self.assertNotAlmostEqual(record["value"], (50 + 9) / 2)
        self.assertEqual(record["numerator"], 10)
        self.assertEqual(record["denominator"], 102)

    def test_excludes_missing_pairs_and_keeps_zero_denominator_null(self):
        frame = pd.DataFrame(
            [
                {"ano": 2025, "municipio": "A", "numerador": 1, "denominador": 0},
                {"ano": 2025, "municipio": "B", "numerador": None, "denominador": 2},
                {"ano": 2025, "municipio": "C", "numerador": 3, "denominador": 3},
            ]
        )

        record = aggregate_ratio_of_sums(
            frame,
            "numerador",
            "denominador",
            indicator_id="teste",
            municipalities_expected=3,
        )[0]

        self.assertEqual(record["numerator"], 4)
        self.assertEqual(record["denominator"], 3)
        self.assertEqual(record["municipalities_valid"], 2)
        self.assertAlmostEqual(record["value"], 100 * 4 / 3)

        zero_frame = pd.DataFrame(
            [{"ano": 2025, "municipio": "A", "numerador": 0, "denominador": 0}]
        )
        zero_record = aggregate_ratio_of_sums(
            zero_frame,
            "numerador",
            "denominador",
            indicator_id="teste",
            municipalities_expected=1,
        )[0]
        self.assertIsNone(zero_record["value"])

    def test_denominator_coverage_is_not_municipality_coverage(self):
        frame = pd.DataFrame(
            [
                {
                    "ano": 2025,
                    "municipio": "A",
                    "numerador": 1,
                    "denominador": 2,
                    "universo_denominador": 10,
                },
                {
                    "ano": 2025,
                    "municipio": "B",
                    "numerador": 1,
                    "denominador": 2,
                    "universo_denominador": 20,
                },
            ]
        )

        record = aggregate_ratio_of_sums(
            frame,
            "numerador",
            "denominador",
            indicator_id="teste",
            denominator_universe_column="universo_denominador",
            municipalities_expected=497,
        )[0]

        self.assertEqual(record["municipal_coverage_percent"], 200 / 497)
        self.assertAlmostEqual(record["denominator_coverage_percent"], 100 * 4 / 30)

    def test_state_value_is_not_rounded_before_presentation(self):
        frame = pd.DataFrame(
            [{"ano": 2025, "municipio": "A", "numerador": 1, "denominador": 3}]
        )
        record = aggregate_ratio_of_sums(
            frame,
            "numerador",
            "denominador",
            indicator_id="teste",
            municipalities_expected=1,
        )[0]
        self.assertAlmostEqual(record["value"], 100 / 3)
        self.assertNotEqual(record["value"], round(100 / 3))

    def test_integral_school_threshold_is_classified_before_state_sum(self):
        frame = pd.DataFrame(
            [
                {
                    "ano": 2025,
                    "municipio": "A",
                    "dependencia": "municipal",
                    "mat_basico": 100,
                    "mat_basico_integral": 25,
                },
                {
                    "ano": 2025,
                    "municipio": "B",
                    "dependencia": "estadual",
                    "mat_basico": 100,
                    "mat_basico_integral": 0,
                },
            ]
        )
        record = _build_escolas_integral_records(
            frame, municipalities_expected=2
        )[0]
        self.assertEqual(record["numerator"], 1)
        self.assertEqual(record["denominator"], 2)
        self.assertEqual(record["value"], 50)

    def test_census_keeps_only_2010_and_2022(self):
        frame = pd.DataFrame(
            [
                {"ano": 2010, "municipio": "A", "num": 8, "den": 10},
                {"ano": 2021, "municipio": "A", "num": 9, "den": 10},
                {"ano": 2022, "municipio": "A", "num": 9, "den": 10},
            ]
        )
        records = _build_census_records(
            frame,
            indicator_id="teste_censo",
            config={"numerator_column": "num", "denominator_column": "den"},
            municipalities_expected=1,
        )
        self.assertEqual([record["year"] for record in records], [2010, 2022])

    def test_state_projection_uses_validated_aggregate_persistence(self):
        projections = build_state_projections(
            {
                "teste": {
                    "series": [
                        {
                            "year": year,
                            "numerator": numerator,
                            "denominator": 100,
                            "value": numerator,
                        }
                        for year, numerator in (
                            (2021, 5),
                            (2022, 10),
                            (2023, 12),
                            (2024, 10),
                            (2025, 20),
                        )
                    ]
                }
            },
            start_year=2026,
            end_year=2036,
        )
        projection = projections["teste"]
        self.assertEqual(
            projection["method"],
            "aggregate_state_persistence_baseline",
        )
        self.assertIn("sem média municipal", projection["source"])
        self.assertEqual(projection["series"][0]["year"], 2026)
        self.assertEqual(projection["series"][-1]["year"], 2036)
        self.assertEqual(
            {point["numerator"] for point in projection["series"]},
            {20.0},
        )
        self.assertEqual(
            {point["denominator"] for point in projection["series"]},
            {100.0},
        )
        self.assertEqual(
            {point["value"] for point in projection["series"]},
            {20.0},
        )
        self.assertEqual(projection["uncertainty"]["status"], "not_estimated")

    def test_state_projection_rejects_short_gapped_or_stale_history(self):
        short = build_state_projections(
            {
                "teste": {
                    "series": [
                        {"year": year, "numerator": 10, "denominator": 100}
                        for year in range(2022, 2026)
                    ]
                }
            }
        )["teste"]
        gapped = build_state_projections(
            {
                "teste": {
                    "series": [
                        {"year": year, "numerator": 10, "denominator": 100}
                        for year in (2020, 2021, 2022, 2023, 2025)
                    ]
                }
            }
        )["teste"]
        stale = build_state_projections(
            {
                "teste": {
                    "series": [
                        {"year": year, "numerator": 10, "denominator": 100}
                        for year in range(2020, 2025)
                    ]
                }
            }
        )["teste"]

        for projection in (short, gapped, stale):
            self.assertFalse(projection["available"])
            self.assertEqual(projection["projection_status"], "unavailable")
            self.assertEqual(
                projection["reason"],
                "insufficient_or_stale_annual_history",
            )

    def test_percentages_with_valid_count_pairs_are_bounded(self):
        frame = pd.DataFrame(
            [
                {"ano": 2025, "municipio": "A", "numerador": 7, "denominador": 10},
                {"ano": 2025, "municipio": "B", "numerador": 8, "denominador": 10},
            ]
        )
        record = aggregate_ratio_of_sums(
            frame,
            "numerador",
            "denominador",
            indicator_id="teste",
            municipalities_expected=2,
        )[0]
        self.assertGreaterEqual(record["value"], 0)
        self.assertLessEqual(record["value"], 100)
        self.assertLessEqual(record["numerator"], record["denominator"])
        self.assertEqual(record["comparison_status"], COMPARABLE)

    def test_articulation_state_reference_uses_sum_of_both_components(self):
        config = RATIO_CONFIGS["medio_tecnico_articulado_percentual"]
        self.assertEqual(config["numerator_column"], "mat_articulado_total")
        frame = pd.DataFrame(
            [
                {
                    "ano": 2025,
                    "municipio": "A",
                    "mat_articulado_total": 10,
                    "mat_medio": 20,
                },
                {
                    "ano": 2025,
                    "municipio": "B",
                    "mat_articulado_total": 90,
                    "mat_medio": 1000,
                },
            ]
        )
        record = aggregate_ratio_of_sums(
            frame,
            config["numerator_column"],
            config["denominator_column"],
            indicator_id="medio_tecnico_articulado_percentual",
            municipalities_expected=2,
        )[0]
        self.assertAlmostEqual(record["value"], 100 * 100 / 1020)
        self.assertNotAlmostEqual(record["value"], (50 + 9) / 2)

    def test_public_expansion_state_reference_uses_net_state_totals(self):
        frame = pd.DataFrame(
            [
                {
                    "ano": 2025,
                    "municipio": "A",
                    "mat_ept_nivel_medio_total": 100,
                    "mat_ept_nivel_medio_publica": 60,
                    "mat_ept_nivel_medio_privada": 40,
                },
                {
                    "ano": 2025,
                    "municipio": "B",
                    "mat_ept_nivel_medio_total": 1000,
                    "mat_ept_nivel_medio_publica": 500,
                    "mat_ept_nivel_medio_privada": 500,
                },
                {
                    "ano": 2026,
                    "municipio": "A",
                    "mat_ept_nivel_medio_total": 120,
                    "mat_ept_nivel_medio_publica": 80,
                    "mat_ept_nivel_medio_privada": 40,
                },
                {
                    "ano": 2026,
                    "municipio": "B",
                    "mat_ept_nivel_medio_total": 990,
                    "mat_ept_nivel_medio_publica": 495,
                    "mat_ept_nivel_medio_privada": 495,
                },
            ]
        )
        record = _build_medio_tecnico_participacao_records(
            frame, municipalities_expected=2
        )[1]
        self.assertEqual(record["numerator"], 15)
        self.assertEqual(record["denominator"], 10)
        self.assertEqual(record["value"], 150)

    def test_subsequent_state_reference_uses_growth_of_state_totals(self):
        frame = pd.DataFrame(
            [
                {"ano": 2025, "municipio": "A", "mat_subsequente_total": 10},
                {"ano": 2025, "municipio": "B", "mat_subsequente_total": 90},
                {"ano": 2026, "municipio": "A", "mat_subsequente_total": 20},
                {"ano": 2026, "municipio": "B", "mat_subsequente_total": 140},
            ]
        )
        record = _build_subsequente_records(
            frame, municipalities_expected=2
        )[1]
        self.assertEqual(record["numerator"], 60)
        self.assertEqual(record["denominator"], 100)
        self.assertEqual(record["value"], 60)


if __name__ == "__main__":
    unittest.main()
