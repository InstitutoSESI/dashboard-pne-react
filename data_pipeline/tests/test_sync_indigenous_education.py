from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "sync_indigenous_education_from_sinopse.py"
)
SPEC = importlib.util.spec_from_file_location("sync_indigenous_education", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class IndigenousEducationImportTest(unittest.TestCase):
    def test_record_preserves_zero_and_missing_values(self):
        columns = MODULE.UNITS["matriculas"]["new_columns"]
        row = [None] * max(columns)
        row[2] = "Aceguá"
        row[3] = 4300034
        for column in columns:
            row[column - 1] = 0
        row[columns[2] - 1] = None

        records = MODULE._record_from_row(
            tuple(row),
            row_number=16,
            year=2025,
            unit_key="matriculas",
            columns=columns,
            sheet_name="Educação Indígena 1.74",
        )

        by_cut = {record["recorte"]: record["valor"] for record in records}
        self.assertEqual(by_cut["total"], 0)
        self.assertIsNone(by_cut["creche"])
        self.assertEqual(records[0]["id_municipio"], "4300034")

    def test_header_validation_rejects_shifted_semantics(self):
        columns = MODULE.UNITS["matriculas"]["new_columns"]
        width = max(columns)
        header_rows = [[None] * width for _ in range(4)]
        header_rows[0][0] = (
            "Número de Matrículas da Educação Indígena por Etapa de Ensino"
        )
        header_rows[0][3] = "Código do Município"
        for (cut_key, _), column in zip(MODULE.CUTS, columns, strict=True):
            header_rows[1][column - 1] = " ".join(MODULE.HEADER_TOKENS[cut_key])
        header_rows[1][columns[2] - 1] = "Valor deslocado"

        with self.assertRaisesRegex(ValueError, "creche"):
            MODULE._validate_layout_headers(
                [tuple(row) for row in header_rows],
                unit_key="matriculas",
                columns=columns,
                sheet_name="Educação Indígena 1.74",
            )

    def test_ibge_code_requires_seven_digits(self):
        with self.assertRaisesRegex(ValueError, "Código IBGE inválido"):
            MODULE._ibge_code(123456, row_number=10)


if __name__ == "__main__":
    unittest.main()
