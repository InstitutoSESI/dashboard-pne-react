import sys
import unittest
from pathlib import Path

import pandas as pd


DATA_PIPELINE_DIR = Path(__file__).resolve().parents[1]
if str(DATA_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_PIPELINE_DIR))

from src.medio_tecnico_articulado import (  # noqa: E402
    MedioTecnicoArticuladoValidationError,
    calculate_public_expansion_series,
    calculate_medio_tecnico_articulado_series,
    calculate_subsequent_expansion_series,
)
from src.pne.common import _build_result, _select_reference_rows  # noqa: E402


def row(**overrides):
    values = {
        "ano": 2025,
        "id_municipio": "4300001",
        "mat_integrado_total": 10,
        "mat_concomitante_total": 0,
        "mat_medio": 100,
    }
    values.update(overrides)
    return values


class MedioTecnicoArticuladoTests(unittest.TestCase):
    def test_zero_component_is_valid_and_missing_is_not_zero(self):
        frame = pd.DataFrame(
            [
                row(id_municipio="4300001", mat_integrado_total=0, mat_concomitante_total=0),
                row(id_municipio="4300002", mat_integrado_total=None),
                row(id_municipio="4300003", mat_medio=0),
            ]
        )

        result = calculate_medio_tecnico_articulado_series(frame)

        zero = result[result["id_municipio"] == "4300001"].iloc[0]
        missing = result[result["id_municipio"] == "4300002"].iloc[0]
        zero_denominator = result[result["id_municipio"] == "4300003"].iloc[0]
        self.assertEqual(zero["mat_articulado_total"], 0)
        self.assertEqual(zero["percentual_calculado"], 0)
        self.assertFalse(zero["acima_de_100"])
        self.assertTrue(pd.isna(missing["mat_articulado_total"]))
        self.assertTrue(pd.isna(missing["percentual_calculado"]))
        self.assertTrue(pd.isna(zero_denominator["percentual_calculado"]))

    def test_percentage_sums_integrated_and_concomitant_enrolments(self):
        result = calculate_medio_tecnico_articulado_series(
            pd.DataFrame(
                [row(mat_integrado_total=20, mat_concomitante_total=30, mat_medio=100)]
            )
        )

        point = result.iloc[0]
        self.assertEqual(point["mat_articulado_total"], 50)
        self.assertAlmostEqual(point["percentual_calculado"], 50.0)
        self.assertAlmostEqual(point["percentual_articulado_total"], 50.0)

    def test_either_articulation_component_can_be_zero(self):
        result = calculate_medio_tecnico_articulado_series(
            pd.DataFrame(
                [
                    row(
                        id_municipio="4300001",
                        mat_integrado_total=25,
                        mat_concomitante_total=0,
                    ),
                    row(
                        id_municipio="4300002",
                        mat_integrado_total=0,
                        mat_concomitante_total=40,
                    ),
                ]
            )
        )
        self.assertEqual(result["percentual_calculado"].tolist(), [25.0, 40.0])

    def test_above_one_hundred_is_preserved(self):
        result = calculate_medio_tecnico_articulado_series(
            pd.DataFrame([row(mat_integrado_total=110, mat_concomitante_total=10, mat_medio=100)])
        )
        point = result.iloc[0]
        self.assertAlmostEqual(point["percentual_calculado"], 120.0)
        self.assertAlmostEqual(point["percentual_articulado_total"], 120.0)
        self.assertTrue(point["acima_de_100"])

    def test_missing_component_makes_percentage_unavailable(self):
        result = calculate_medio_tecnico_articulado_series(
            pd.DataFrame([row(mat_integrado_total=25, mat_concomitante_total=None, mat_medio=100)])
        )

        point = result.iloc[0]
        self.assertTrue(pd.isna(point["percentual_calculado"]))
        self.assertTrue(pd.isna(point["mat_articulado_total"]))
        self.assertTrue(pd.isna(point["percentual_articulado_total"]))

    def test_negative_and_duplicate_rows_are_rejected(self):
        with self.assertRaises(MedioTecnicoArticuladoValidationError):
            calculate_medio_tecnico_articulado_series(
                pd.DataFrame([row(mat_concomitante_total=-1)])
            )

        with self.assertRaises(MedioTecnicoArticuladoValidationError):
            calculate_medio_tecnico_articulado_series(
                pd.DataFrame([row(), row()])
            )

    def test_dependency_totals_reconcile_without_being_resummed(self):
        result = calculate_medio_tecnico_articulado_series(
            pd.DataFrame(
                [
                    row(
                        mat_integrado_total=10,
                        mat_concomitante_total=20,
                        mat_integrado_federal=1,
                        mat_integrado_estadual=2,
                        mat_integrado_municipal=3,
                        mat_integrado_privada=4,
                        mat_concomitante_federal=5,
                        mat_concomitante_estadual=5,
                        mat_concomitante_municipal=5,
                        mat_concomitante_privada=5,
                    )
                ]
            )
        )
        self.assertEqual(result.iloc[0]["mat_articulado_total"], 30)

    def test_dependency_mismatch_is_rejected(self):
        with self.assertRaises(MedioTecnicoArticuladoValidationError):
            calculate_medio_tecnico_articulado_series(
                pd.DataFrame(
                    [
                        row(
                            mat_integrado_total=11,
                            mat_integrado_federal=1,
                            mat_integrado_estadual=2,
                            mat_integrado_municipal=3,
                            mat_integrado_privada=4,
                        )
                    ]
                )
            )

    def test_public_expansion_uses_fixed_2025_baseline_and_preserves_range(self):
        frame = pd.DataFrame(
            [
                {
                    "ano": 2025,
                    "id_municipio": "4300001",
                    "mat_ept_nivel_medio_total": 100,
                    "mat_ept_nivel_medio_publica": 60,
                },
                {
                    "ano": 2026,
                    "id_municipio": "4300001",
                    "mat_ept_nivel_medio_total": 110,
                    "mat_ept_nivel_medio_publica": 75,
                },
                {
                    "ano": 2027,
                    "id_municipio": "4300001",
                    "mat_ept_nivel_medio_total": 120,
                    "mat_ept_nivel_medio_publica": 55,
                },
            ]
        )
        result = calculate_public_expansion_series(frame)
        self.assertAlmostEqual(result.iloc[0]["valor"], 150.0)
        self.assertAlmostEqual(result.iloc[1]["valor"], -25.0)

    def test_public_expansion_allows_zero_public_baseline_when_total_expands(self):
        result = calculate_public_expansion_series(
            pd.DataFrame(
                [
                    {
                        "ano": 2025,
                        "id_municipio": "4300001",
                        "mat_ept_nivel_medio_total": 0,
                        "mat_ept_nivel_medio_publica": 0,
                    },
                    {
                        "ano": 2026,
                        "id_municipio": "4300001",
                        "mat_ept_nivel_medio_total": 10,
                        "mat_ept_nivel_medio_publica": 6,
                    },
                ]
            )
        ).iloc[0]

        self.assertEqual(result["data_status"], "available")
        self.assertIsNone(result["reason_code"])
        self.assertEqual(result["numerador"], 6.0)
        self.assertEqual(result["denominador"], 10.0)
        self.assertEqual(result["valor"], 60.0)

    def test_public_expansion_statuses_are_explicit(self):
        no_post = calculate_public_expansion_series(
            pd.DataFrame(
                [
                    {
                        "ano": 2025,
                        "id_municipio": "4300001",
                        "mat_ept_nivel_medio_total": 100,
                        "mat_ept_nivel_medio_publica": 60,
                    }
                ]
            )
        ).iloc[0]
        self.assertEqual(no_post["reason_code"], "no_post_baseline_observation")

        non_positive = calculate_public_expansion_series(
            pd.DataFrame(
                [
                    {
                        "ano": 2025,
                        "id_municipio": "4300001",
                        "mat_ept_nivel_medio_total": 100,
                        "mat_ept_nivel_medio_publica": 60,
                    },
                    {
                        "ano": 2026,
                        "id_municipio": "4300001",
                        "mat_ept_nivel_medio_total": 90,
                        "mat_ept_nivel_medio_publica": 55,
                    },
                ]
            )
        ).iloc[0]
        self.assertEqual(non_positive["data_status"], "not_applicable")
        self.assertEqual(non_positive["reason_code"], "non_positive_total_expansion")

    def test_public_expansion_missing_base_and_current_are_unavailable(self):
        result = calculate_public_expansion_series(
            pd.DataFrame(
                [
                    {
                        "ano": 2025,
                        "id_municipio": "4300001",
                        "mat_ept_nivel_medio_total": 100,
                        "mat_ept_nivel_medio_publica": 60,
                    },
                    {
                        "ano": 2026,
                        "id_municipio": "4300002",
                        "mat_ept_nivel_medio_total": 120,
                        "mat_ept_nivel_medio_publica": 80,
                    },
                ]
            )
        ).set_index("id_municipio")
        self.assertEqual(
            result.loc["4300001", "reason_code"],
            "current_observation_unavailable",
        )
        self.assertEqual(
            result.loc["4300002", "reason_code"],
            "baseline_observation_unavailable",
        )

    def test_public_dependency_universe_mismatch_is_rejected(self):
        with self.assertRaises(MedioTecnicoArticuladoValidationError):
            calculate_public_expansion_series(
                pd.DataFrame(
                    [
                        {
                            "ano": 2025,
                            "id_municipio": "4300001",
                            "mat_ept_nivel_medio_total": 100,
                            "mat_ept_nivel_medio_publica": 70,
                            "mat_ept_nivel_medio_privada": 40,
                        }
                    ]
                )
            )

    def test_subsequent_expansion_handles_zero_and_negative_change(self):
        frame = pd.DataFrame(
            [
                {
                    "ano": 2025,
                    "id_municipio": "4300001",
                    "mat_subsequente_total": 100,
                },
                {
                    "ano": 2026,
                    "id_municipio": "4300001",
                    "mat_subsequente_total": 50,
                },
                {
                    "ano": 2027,
                    "id_municipio": "4300001",
                    "mat_subsequente_total": 160,
                },
            ]
        )
        result = calculate_subsequent_expansion_series(frame)
        self.assertAlmostEqual(result.iloc[0]["valor"], -50.0)
        self.assertAlmostEqual(result.iloc[1]["valor"], 60.0)
        self.assertAlmostEqual(result.iloc[1]["reference_value"], 160.0)

        zero_base = calculate_subsequent_expansion_series(
            pd.DataFrame(
                [
                    {
                        "ano": 2025,
                        "id_municipio": "4300001",
                        "mat_subsequente_total": 0,
                    },
                    {
                        "ano": 2026,
                        "id_municipio": "4300001",
                        "mat_subsequente_total": 10,
                    },
                ]
            )
        ).iloc[0]
        self.assertEqual(zero_base["data_status"], "not_applicable")
        self.assertEqual(zero_base["reason_code"], "baseline_zero")

    def test_subsequent_expansion_missing_observations_and_thresholds(self):
        result = calculate_subsequent_expansion_series(
            pd.DataFrame(
                [
                    {
                        "ano": 2025,
                        "id_municipio": "4300001",
                        "mat_subsequente_total": 100,
                    },
                    {
                        "ano": 2026,
                        "id_municipio": "4300002",
                        "mat_subsequente_total": 100,
                    },
                    {
                        "ano": 2027,
                        "id_municipio": "4300001",
                        "mat_subsequente_total": 0,
                    },
                    {
                        "ano": 2027,
                        "id_municipio": "4300002",
                        "mat_subsequente_total": 170,
                    },
                ]
            )
        )
        by_pair = result.set_index(["id_municipio", "ano"])
        self.assertEqual(
            by_pair.loc[("4300001", 2026), "reason_code"],
            "current_observation_unavailable",
        )
        self.assertEqual(
            by_pair.loc[("4300002", 2026), "reason_code"],
            "baseline_observation_unavailable",
        )
        self.assertEqual(by_pair.loc[("4300001", 2027), "valor"], -100.0)

        for current, expected in ((150, 50.0), (160, 60.0), (250, 150.0)):
            point = calculate_subsequent_expansion_series(
                pd.DataFrame(
                    [
                        {
                            "ano": 2025,
                            "id_municipio": "4300001",
                            "mat_subsequente_total": 100,
                        },
                        {
                            "ano": 2026,
                            "id_municipio": "4300001",
                            "mat_subsequente_total": current,
                        },
                    ]
                )
            ).iloc[0]
            self.assertEqual(point["valor"], expected)

    def test_subsequent_status_uses_unrounded_value(self):
        from src.pne.calculations_2026 import _fixed_baseline_result

        result = _fixed_baseline_result(
            pd.DataFrame(
                [
                    {
                        "ano": 2026,
                        "valor": 59.999999,
                        "numerador": 59.999999,
                        "denominador": 100,
                        "reference_value": 160,
                        "data_status": "available",
                        "reason_code": None,
                    }
                ]
            ),
            60,
        )
        self.assertFalse(result["atingida"])
        self.assertLess(result["distance"], 0)

    def test_closed_cycle_reference_never_falls_forward_to_2025(self):
        series = pd.DataFrame(
            [
                {"ano": 2014, "valor": 10},
                {"ano": 2025, "valor": 20},
            ]
        )
        start, end = _select_reference_rows(series, 2014, 2024)
        self.assertEqual(int(start["ano"]), 2014)
        self.assertEqual(int(end["ano"]), 2014)

        result = _build_result(
            series,
            50,
            target_start_year=2014,
            target_end_year=2024,
        )
        self.assertEqual(result["end_year"], 2014)
        self.assertNotEqual(result["end_year"], 2025)


if __name__ == "__main__":
    unittest.main()
