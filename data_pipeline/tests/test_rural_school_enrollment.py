from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

DATA_PIPELINE_DIR = Path(__file__).resolve().parents[1]
if str(DATA_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_PIPELINE_DIR))

from src.rural_school_enrollment import aggregate_rural_enrollment_year


HEADER = [
    "NU_ANO_CENSO",
    "SG_UF",
    "CO_MUNICIPIO",
    "TP_SITUACAO_FUNCIONAMENTO",
    "TP_LOCALIZACAO",
    "QT_MAT_BAS_4_5",
    "QT_MAT_BAS_6_10",
    "QT_MAT_BAS_11_14",
    "QT_MAT_BAS_15_17",
]


def write_csv(path: Path, rows: list[list[object]]) -> None:
    lines = [";".join(HEADER)]
    lines.extend(";".join(str(value) for value in row) for row in rows)
    path.write_text("\n".join(lines) + "\n", encoding="latin1")


class RuralSchoolEnrollmentTest(unittest.TestCase):
    def test_filters_active_rural_schools_and_fills_canonical_zeros(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "microdados_ed_basica_2025.csv"
            write_csv(
                path,
                [
                    [2025, "RS", "4300109", 1, 2, 2, 3, 4, 5],
                    [2025, "RS", "4300109", 2, 2, 90, 90, 90, 90],
                    [2025, "RS", "4300109", 1, 1, 80, 80, 80, 80],
                    [2025, "RS", "4300208", 1, 2, "", "", "", ""],
                ],
            )
            rows, audit = aggregate_rural_enrollment_year(
                path,
                year=2025,
                state_code="RS",
                municipality_codes={"4300109", "4300208"},
                chunk_size=2,
            )
        by_key = {(row["id_municipio"], row["faixa_etaria"]): row for row in rows}
        self.assertEqual(by_key[("4300109", "4_17")]["matriculas"], 14)
        self.assertEqual(by_key[("4300208", "4_17")]["matriculas"], 0)
        self.assertEqual(by_key[("4300208", "4_17")]["origem_valor"], "derived_zero")
        self.assertEqual(audit["activeRuralSchoolRows"], 2)
        self.assertEqual(audit["allAgeFieldsNullRowsExcluded"], 1)

    def test_partial_null_age_fields_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "microdados_ed_basica_2025.csv"
            write_csv(path, [[2025, "RS", "4300109", 1, 2, 1, "", 3, 4]])
            with self.assertRaisesRegex(ValueError, "parcialmente nulos"):
                aggregate_rural_enrollment_year(
                    path,
                    year=2025,
                    state_code="RS",
                    municipality_codes={"4300109"},
                )

    def test_filters_the_requested_state_without_rs_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "microdados_ed_basica_2025.csv"
            write_csv(
                path,
                [
                    [2025, "RS", "4300109", 1, 2, 90, 90, 90, 90],
                    [2025, "AL", "2704302", 1, 2, 2, 3, 4, 5],
                ],
            )
            rows, audit = aggregate_rural_enrollment_year(
                path,
                year=2025,
                state_code="al",
                municipality_codes={"2704302"},
            )
        total = next(row for row in rows if row["faixa_etaria"] == "4_17")
        self.assertEqual(total["id_municipio"], "2704302")
        self.assertEqual(total["matriculas"], 14)
        self.assertEqual(audit["stateRows"], 1)
        self.assertEqual(audit["source"]["filters"]["state"], "SG_UF == 'AL'")


if __name__ == "__main__":
    unittest.main()
