from __future__ import annotations

import sys
import unittest
from pathlib import Path

DATA_PIPELINE_DIR = Path(__file__).resolve().parents[1]
if str(DATA_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_PIPELINE_DIR))

from src.rural_education_coverage import build_coverage_contract


def population(value, status="available"):
    return [
        {
            "populacao_rural_estimada_4_17": value,
            "status_valor": status,
            "populacao_rural_0_4": 2,
            "populacao_rural_5_9": 3,
            "populacao_rural_10_14": 4,
            "populacao_rural_15_19": 5,
            "peso_idade_4_no_grupo_0_4": 0.2,
            "peso_idades_15_17_no_grupo_15_19": 0.6,
            "metadados_fonte": {
                "ruralGroups": {"aggregate": "10089", "responseSha256": "abc"},
                "exactAgeWeights": {"aggregate": "9606", "responseSha256": "def"},
            },
        }
    ]


def enrollments(values=(2, 3, 4, 5)):
    rows = []
    for year in (2023, 2024, 2025):
        for age_group, value in zip(("4_5", "6_10", "11_14", "15_17"), values):
            rows.append(
                {
                    "ano": year,
                    "faixa_etaria": age_group,
                    "matriculas": value,
                    "status_valor": "available",
                    "metadados_fonte": {
                        "sourceFile": f"microdados_ed_basica_{year}.csv",
                        "sourceSha256": str(year),
                    },
                }
            )
    return rows


class RuralEducationCoverageTest(unittest.TestCase):
    def test_calculates_full_precision_without_capping(self):
        contract = build_coverage_contract(population(10), enrollments())
        item = contract["series"]["2025"]
        self.assertEqual(item["enrollments"]["alignedTotal"], 14)
        self.assertEqual(item["percentage"], 140)
        self.assertEqual(item["status"], "available")

    def test_zero_denominator_states_remain_distinct(self):
        without = build_coverage_contract(population(0), enrollments((0, 0, 0, 0)))
        self.assertEqual(without["series"]["2025"]["status"], "not_applicable")
        with_enrollments = build_coverage_contract(population(0), enrollments())
        self.assertEqual(
            with_enrollments["series"]["2025"]["status"],
            "denominator_zero_with_enrollments",
        )
        self.assertIsNone(with_enrollments["series"]["2025"]["percentage"])

    def test_missing_component_keeps_year_unavailable(self):
        rows = [
            row
            for row in enrollments()
            if not (row["ano"] == 2024 and row["faixa_etaria"] == "15_17")
        ]
        contract = build_coverage_contract(population(14), rows)
        self.assertEqual(contract["series"]["2024"]["status"], "unavailable")
        self.assertIsNone(contract["series"]["2024"]["enrollments"]["alignedTotal"])


if __name__ == "__main__":
    unittest.main()
