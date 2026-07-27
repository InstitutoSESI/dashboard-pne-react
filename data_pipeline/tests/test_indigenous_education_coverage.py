from __future__ import annotations

import sys
import unittest
from pathlib import Path

DATA_PIPELINE_DIR = Path(__file__).resolve().parents[1]
if str(DATA_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_PIPELINE_DIR))

from src.indigenous_education_coverage import build_coverage_contract


def population(value, status="available"):
    return [
        {
            "faixa_etaria": "4_17",
            "pessoas_indigenas": value,
            "status_valor": status,
            "tabela_origem": "9970",
            "metadados_fonte": {
                "aggregate": "9970",
                "responseSha256": "abc",
            },
        },
        {
            "faixa_etaria": "4_5",
            "pessoas_indigenas": 2,
            "status_valor": "available",
        },
        {
            "faixa_etaria": "6_14",
            "pessoas_indigenas": 9,
            "status_valor": "available",
        },
        {
            "faixa_etaria": "15_17",
            "pessoas_indigenas": 3,
            "status_valor": "available",
        },
    ]


def enrollments(pre=2, elementary=9, high=3):
    rows = []
    for year in (2023, 2024, 2025):
        for cut, value in (
            ("pre_escola", pre),
            ("ensino_fundamental", elementary),
            ("ensino_medio", high),
        ):
            rows.append(
                {
                    "ano": year,
                    "unidade": "matriculas",
                    "recorte": cut,
                    "valor": value,
                    "tabela_fonte": f"Educação Indígena {year}",
                }
            )
    return rows


class IndigenousEducationCoverageTest(unittest.TestCase):
    def test_calculates_full_precision_without_capping_above_100(self):
        contract = build_coverage_contract(population(10), enrollments())
        item = contract["series"]["2025"]
        self.assertEqual(item["enrollments"]["alignedTotal"], 14)
        self.assertEqual(item["percentage"], 140)
        self.assertEqual(item["status"], "available")

    def test_zero_denominator_states_are_distinct(self):
        without_enrollments = build_coverage_contract(
            population(0), enrollments(0, 0, 0)
        )
        self.assertEqual(
            without_enrollments["series"]["2025"]["status"], "not_applicable"
        )
        with_enrollments = build_coverage_contract(population(0), enrollments())
        self.assertEqual(
            with_enrollments["series"]["2025"]["status"],
            "denominator_zero_with_enrollments",
        )
        self.assertIsNone(with_enrollments["series"]["2025"]["percentage"])

    def test_missing_component_keeps_indicator_unavailable(self):
        rows = enrollments()
        rows = [
            row
            for row in rows
            if not (row["ano"] == 2024 and row["recorte"] == "ensino_medio")
        ]
        contract = build_coverage_contract(population(14), rows)
        self.assertEqual(contract["series"]["2024"]["status"], "unavailable")
        self.assertIsNone(
            contract["series"]["2024"]["enrollments"]["alignedTotal"]
        )


if __name__ == "__main__":
    unittest.main()
