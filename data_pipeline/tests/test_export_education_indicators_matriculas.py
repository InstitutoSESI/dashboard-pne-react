import importlib.util
import sys
import types
import unittest
from pathlib import Path

import pandas as pd


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "export_education_indicators.py"
)
SPEC = importlib.util.spec_from_file_location(
    "export_education_indicators",
    SCRIPT_PATH,
)
UTILS_EDUCACAO = types.ModuleType("utils_educacao")
UTILS_EDUCACAO.get_engine = lambda _database: object()
sys.modules["utils_educacao"] = UTILS_EDUCACAO
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class EducationEnrollmentExportTest(unittest.TestCase):
    def test_total_uses_official_basic_education_value(self):
        municipality_id = "4300001"
        categories = pd.DataFrame(
            [
                {
                    "ano": 2025,
                    "id_municipio": municipality_id,
                    "dependencia": "total",
                    "localizacao": "total",
                    "etapa_ensino": stage,
                    "matriculas": enrollments,
                    "matriculas_integral": integral,
                }
                for stage, enrollments, integral in (
                    ("infantil", 20, 8),
                    ("fundamental", 50, 4),
                    ("fundamental_anos_iniciais", 30, 3),
                    ("fundamental_anos_finais", 20, 1),
                    ("medio", 20, 0),
                    ("eja", 10, None),
                    ("profissional", 20, None),
                )
            ]
        )
        official = pd.DataFrame(
            [
                {
                    "ano": 2025,
                    "id_municipio": municipality_id,
                    "dependencia": dependency,
                    "localizacao": location,
                    "mat_basico": enrollments,
                }
                for dependency, location, enrollments in (
                    ("municipal", "urbana", 60),
                    ("estadual", "rural", 20),
                    ("federal", "urbana", 10),
                    ("privada", "urbana", 10),
                )
            ]
        )

        block = MODULE.montar_bloco_matriculas(
            categories,
            municipality_id,
            official,
        )

        self.assertEqual(block["series"]["total"], [{"ano": 2025, "valor": 100}])
        self.assertEqual(block["resumo_ultimo_ano"]["total_matriculas"], 100)
        self.assertEqual(
            block["resumo_ultimo_ano"]["por_etapa"]["profissional"],
            20,
        )
        self.assertEqual(
            block["series"]["por_dependencia"]["publica"],
            [{"ano": 2025, "valor": 90}],
        )
        self.assertEqual(
            block["series"]["por_dependencia"]["privada"],
            [{"ano": 2025, "valor": 10}],
        )
        self.assertEqual(
            block["series"]["por_localizacao"]["urbana"],
            [{"ano": 2025, "valor": 80}],
        )
        self.assertEqual(
            block["series"]["por_localizacao"]["rural"],
            [{"ano": 2025, "valor": 20}],
        )
        self.assertEqual(
            block["resumo_ultimo_ano"]["percentual_integral"],
            10.0,
        )

    def test_missing_official_total_fails_instead_of_summing_categories(self):
        categories = pd.DataFrame(
            [
                {
                    "ano": 2025,
                    "id_municipio": "4300001",
                    "dependencia": "total",
                    "localizacao": "total",
                    "etapa_ensino": "fundamental",
                    "matriculas": 50,
                    "matriculas_integral": 5,
                }
            ]
        )

        with self.assertRaisesRegex(
            ValueError,
            "total oficial de matrículas da Educação Básica indisponível",
        ):
            MODULE.montar_bloco_matriculas(
                categories,
                "4300001",
                pd.DataFrame(),
            )


if __name__ == "__main__":
    unittest.main()
