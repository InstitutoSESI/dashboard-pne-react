from __future__ import annotations

import sys
import unittest
from pathlib import Path

DATA_PIPELINE_DIR = Path(__file__).resolve().parents[1]
if str(DATA_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_PIPELINE_DIR))

from src import rural_population_sidra as sidra


def rural_rows(values=None, statuses=None):
    values = values or {"0_4": 100, "5_9": 100, "10_14": 100, "15_19": 100}
    statuses = statuses or {}
    return [
        {
            "id_municipio": "4300109",
            "faixa_etaria": key,
            "populacao_rural": values[key],
            "status_valor": statuses.get(key, "available"),
        }
        for key in sidra.RURAL_GROUP_AGE_IDS
    ]


def age_rows(values=None):
    values = values or {age: 10 for age in range(20)}
    return [
        {
            "id_municipio": "4300109",
            "idade": age,
            "populacao_municipal": values[age],
            "status_valor": "available",
        }
        for age in range(20)
    ]


class RuralPopulationSidraTest(unittest.TestCase):
    def test_special_symbols_preserve_distinct_states(self):
        self.assertEqual(sidra.parse_sidra_value("-"), (0, "available"))
        self.assertEqual(sidra.parse_sidra_value("0"), (0, "available"))
        self.assertEqual(sidra.parse_sidra_value("X"), (None, "suppressed"))
        self.assertEqual(sidra.parse_sidra_value(".."), (None, "not_applicable"))
        self.assertEqual(sidra.parse_sidra_value("..."), (None, "unavailable"))
        self.assertEqual(sidra.parse_sidra_value(None), (None, "missing"))

    def test_estimate_uses_only_edge_weights_without_rounding(self):
        rows = sidra.estimate_population_4_17(
            rural_rows(), age_rows(), source_metadata={"provider": "IBGE"}
        )
        self.assertEqual(len(rows), 1)
        result = rows[0]
        self.assertEqual(result["peso_idade_4_no_grupo_0_4"], 0.2)
        self.assertEqual(result["peso_idades_15_17_no_grupo_15_19"], 0.6)
        self.assertEqual(result["populacao_rural_estimada_4_17"], 280.0)
        self.assertEqual(result["status_valor"], "available")

    def test_unavailable_source_is_not_converted_to_zero(self):
        rows = sidra.estimate_population_4_17(
            rural_rows(values={"0_4": None, "5_9": 1, "10_14": 1, "15_19": 1}, statuses={"0_4": "suppressed"}),
            age_rows(),
            source_metadata={},
        )
        self.assertIsNone(rows[0]["populacao_rural_estimada_4_17"])
        self.assertEqual(rows[0]["status_valor"], "suppressed")

    def test_zero_edge_groups_remain_available_with_zero_total_weights(self):
        ages = {age: 10 for age in range(20)}
        for age in (*range(0, 5), *range(15, 20)):
            ages[age] = 0
        rows = sidra.estimate_population_4_17(
            rural_rows(values={"0_4": 0, "5_9": 11, "10_14": 13, "15_19": 0}),
            age_rows(ages),
            source_metadata={},
        )
        self.assertEqual(rows[0]["populacao_rural_estimada_4_17"], 24)
        self.assertEqual(rows[0]["status_valor"], "available")
        self.assertIsNone(rows[0]["peso_idade_4_no_grupo_0_4"])


if __name__ == "__main__":
    unittest.main()
