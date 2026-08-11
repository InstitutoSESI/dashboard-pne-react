from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path


DATA_PIPELINE_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = DATA_PIPELINE_DIR.parent
sys.path.insert(0, str(DATA_PIPELINE_DIR))

from src.municipal_finance_icms_education import (  # noqa: E402
    ICMS_EDUCATION_SOURCE_ID,
    build_icms_education_contract,
    load_icms_education_registry,
    load_icms_education_source,
    merge_icms_education_source,
    validate_icms_education_contract,
)


BUNDLE_ROOT = (
    DATA_PIPELINE_DIR / "data" / "municipal_finance" / "icms_education" / "rs"
)
REGISTRY_PATH = REPO_ROOT / "config" / "municipalities" / "rs.json"


class MunicipalFinanceIcmsEducationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.municipalities = load_icms_education_registry(REGISTRY_PATH)
        cls.source = load_icms_education_source(BUNDLE_ROOT, REGISTRY_PATH)

    def test_source_has_exact_registry_coverage_for_all_three_years(self) -> None:
        quality = self.source["quality"]
        self.assertEqual(quality["rows"], 1_491)
        self.assertEqual(quality["municipalitiesFound"], 497)
        self.assertEqual(
            quality["rowsByReferenceYear"],
            {"2022": 497, "2023": 497, "2024": 497},
        )
        self.assertEqual(set(self.source["records"]), {
            item["ibgeCode"] for item in self.municipalities
        })

    def test_formulas_and_published_pre_deviation_are_explicit(self) -> None:
        quality = self.source["quality"]
        self.assertEqual(quality["imersFormulaMaxAbsoluteError"], "0.00000680")
        self.assertEqual(
            quality["municipalSizeFormulaMaxAbsoluteError"],
            "0.000000004660",
        )
        self.assertEqual(
            quality["preShareTotalDeviationsPercentagePoints"]["2024"],
            "0.002323507",
        )
        self.assertEqual(
            quality["warningCodes"],
            ["source_published_pre_total_deviation_2024"],
        )

    def test_agudo_preserves_official_latest_values_and_history(self) -> None:
        merged = merge_icms_education_source(
            {"stateCode": "RS", "sources": {}},
            self.source,
            self.municipalities,
        )
        block = build_icms_education_contract(merged, "4300109")
        self.assertIsNotNone(block)
        assert block is not None
        validate_icms_education_contract(block, "4300109")
        self.assertEqual(block["sourceId"], ICMS_EDUCATION_SOURCE_ID)
        self.assertEqual(block["latestAssessmentYear"], 2024)
        self.assertEqual(block["latestDistributionYear"], 2026)
        self.assertEqual(block["latest"]["imers"], 71.00519)
        self.assertEqual(block["latest"]["preSharePercent"], 0.189147163)
        self.assertEqual(block["latest"]["components"]["iqa"], 72.08107)
        self.assertEqual(
            [item["assessmentYear"] for item in block["history"]],
            [2022, 2023, 2024],
        )

    def test_bundle_fails_closed_when_raw_hash_changes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="icms-education-test-") as directory:
            copied_root = Path(directory) / "rs"
            shutil.copytree(BUNDLE_ROOT, copied_root)
            raw_path = copied_root / "raw" / "imers-pre-2022-2024.csv"
            raw_path.write_bytes(raw_path.read_bytes() + b"\n")
            with self.assertRaisesRegex(RuntimeError, "Hash ou tamanho divergente"):
                load_icms_education_source(copied_root, REGISTRY_PATH)


if __name__ == "__main__":
    unittest.main()
