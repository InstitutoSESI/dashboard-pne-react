from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

DATA_PIPELINE_DIR = Path(__file__).resolve().parents[1]
if str(DATA_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_PIPELINE_DIR))

from src import indigenous_population_sidra as sidra


def fixture_metadata():
    return {
        "id": 9970,
        "nome": "Pessoas indígenas, por idade, localização e situação do domicílio",
        "periodicidade": {"inicio": 2022, "fim": 2022},
        "nivelTerritorial": {"Administrativo": ["N1", "N2", "N3", "N6"]},
        "variaveis": [
            {"id": 350, "nome": "Pessoas indígenas", "unidade": "Pessoas"}
        ],
        "classificacoes": [
            {
                "id": 287,
                "nome": "Idade",
                "categorias": [
                    {
                        "id": int(category_id),
                        "nome": (
                            "Menos de 1 ano"
                            if age == 0
                            else ("1 ano" if age == 1 else f"{age} anos")
                        ),
                    }
                    for age, category_id in sidra.AGE_IDS.items()
                ],
            },
            {
                "id": 2661,
                "nome": "Localização do domicílio",
                "categorias": [{"id": 32776, "nome": "Total"}],
            },
            {
                "id": 1,
                "nome": "Situação do domicílio",
                "categorias": [{"id": 6795, "nome": "Total"}],
            },
        ],
    }


class IndigenousPopulationSidraTest(unittest.TestCase):
    def test_metadata_validation_checks_semantic_labels(self):
        contract = sidra.validate_metadata(fixture_metadata())
        self.assertEqual(contract["variable"]["label"], "Pessoas indígenas")
        self.assertEqual(
            contract["classifications"]["age"]["categories"]["17"]["label"],
            "17 anos",
        )

        invalid = copy.deepcopy(fixture_metadata())
        invalid["classificacoes"][1]["categorias"][0]["nome"] = "Rural"
        with self.assertRaisesRegex(ValueError, "não representa Total"):
            sidra.validate_metadata(invalid)

    def test_special_symbols_are_not_converted_to_zero(self):
        self.assertEqual(sidra.parse_sidra_value("-"), (0, "available"))
        self.assertEqual(sidra.parse_sidra_value("0"), (0, "available"))
        self.assertEqual(sidra.parse_sidra_value("X"), (None, "suppressed"))
        self.assertEqual(sidra.parse_sidra_value(".."), (None, "not_applicable"))
        self.assertEqual(sidra.parse_sidra_value("..."), (None, "unavailable"))
        self.assertEqual(sidra.parse_sidra_value(None), (None, "missing"))

    def test_age_groups_require_every_simple_age(self):
        rows = [
            {
                "ano_censo": 2022,
                "id_municipio": "4300109",
                "idade": age,
                "pessoas_indigenas": 1,
                "status_valor": "available",
            }
            for age in range(18)
        ]
        groups = {
            row["faixa_etaria"]: row for row in sidra.aggregate_age_groups(rows)
        }
        self.assertEqual(groups["4_17"]["pessoas_indigenas"], 14)
        self.assertEqual(groups["0_3"]["pessoas_indigenas"], 4)

        rows[10]["pessoas_indigenas"] = None
        rows[10]["status_valor"] = "suppressed"
        groups = {
            row["faixa_etaria"]: row for row in sidra.aggregate_age_groups(rows)
        }
        self.assertIsNone(groups["4_17"]["pessoas_indigenas"])
        self.assertEqual(groups["4_17"]["status_valor"], "suppressed")


if __name__ == "__main__":
    unittest.main()
