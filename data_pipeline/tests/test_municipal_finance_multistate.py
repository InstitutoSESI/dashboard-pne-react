from __future__ import annotations

import json
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path


DATA_PIPELINE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DATA_PIPELINE_DIR))

from src.municipal_finance import (  # noqa: E402
    FinanceState,
    coverage_payload,
    load_municipality_registry,
)
from src.municipal_finance_constitutional import (  # noqa: E402
    ConstitutionalState,
    build_crosswalk,
    validate_crosswalk,
)
from src.municipal_finance_p5b2 import (  # noqa: E402
    coverage_summary,
    validate_ibge_code,
)
from src.qse_annual import Municipality, parse_qse_annual_lines  # noqa: E402


class MunicipalFinanceMultistateTest(unittest.TestCase):
    def setUp(self) -> None:
        self.finance_state = FinanceState("AL", "27", 2)
        self.constitutional_state = ConstitutionalState("AL", "27", 2)

    def test_registro_e_cobertura_usam_configuracao_de_al(self) -> None:
        payload = {
            "municipios": [
                {"id_municipio": "2700102", "nome": "Água Branca", "slug": "agua-branca"},
                {"id_municipio": "2700201", "nome": "Anadia", "slug": "anadia"},
            ]
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "municipios_index.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            municipalities = load_municipality_registry(path, self.finance_state)
        self.assertEqual([item["ibgeCode"] for item in municipalities], ["2700102", "2700201"])
        self.assertEqual(coverage_payload([], 2)["municipalities"], 2)
        summary = coverage_summary(
            ["2700102"],
            ["2700102", "2700201"],
            municipality_ibge_prefix="27",
            state_code="AL",
        )
        self.assertEqual(summary["denominator"], 2)
        self.assertEqual(summary["missingCodes"], ["2700201"])

    def test_crosswalk_al_e_derivado_dos_codigos_ibge_oficiais(self) -> None:
        municipalities = [
            {"ibgeCode": "2700102", "name": "Água Branca", "slug": "agua-branca"},
            {"ibgeCode": "2700201", "name": "Anadia", "slug": "anadia"},
        ]
        with tempfile.TemporaryDirectory() as directory:
            registry = Path(directory) / "al.json"
            registry.write_text("{}\n", encoding="utf-8")
            payload = build_crosswalk(municipalities, registry, self.constitutional_state)
        crosswalk = validate_crosswalk(payload, self.constitutional_state)
        self.assertEqual(payload["crosswalkVersion"], "siope-ibge-al-2024-v1")
        self.assertEqual(payload["sourcePath"], "al.json")
        self.assertEqual(crosswalk["270010"]["ibgeCode"], "2700102")

    def test_qse_filtra_al_e_preserva_valor_oficial(self) -> None:
        municipalities = {
            "2700102": Municipality("2700102", "Água Branca", "agua-branca"),
        }
        records, quality = parse_qse_annual_lines(
            [
                "AL ÁGUA BRANCA 2700102 1.234,00 0,0001 12.345,67",
                "RS CONTAMINAÇÃO 4300109 1.000,00 0,0001 99.999,99",
            ],
            2024,
            municipalities,
            state_code="AL",
            municipality_ibge_prefix="27",
        )
        self.assertEqual(records["2700102"]["distributedAmount"], Decimal("12345.67"))
        self.assertEqual(quality["municipalitiesWithValue"], 1)
        self.assertEqual(validate_ibge_code("2700102", "27", "AL"), "2700102")
        with self.assertRaises(ValueError):
            validate_ibge_code("4300109", "27", "AL")

    def test_qse_legado_usa_crosswalk_explicito_para_apostrofos_removidos(self) -> None:
        municipalities = {
            "2705705": Municipality(
                "2705705", "Olho d'Água das Flores", "olho-d-agua-das-flores"
            ),
        }
        records, quality = parse_qse_annual_lines(
            ["AL OLHO DAGUA DAS FLORES 1.234,56"],
            2020,
            municipalities,
            state_code="AL",
            municipality_ibge_prefix="27",
        )
        self.assertEqual(records["2705705"]["distributedAmount"], Decimal("1234.56"))
        self.assertEqual(quality["unmappedRecords"], [])


if __name__ == "__main__":
    unittest.main()
