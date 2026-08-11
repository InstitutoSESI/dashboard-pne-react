from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


DATA_PIPELINE_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = DATA_PIPELINE_DIR.parent
sys.path.insert(0, str(DATA_PIPELINE_DIR))

from src.municipal_finance import (  # noqa: E402
    build_contract,
    derived_rate,
    load_municipality_registry,
    load_source_snapshot,
)
from src.municipal_finance_constitutional import (  # noqa: E402
    load_constitutional_snapshot,
    merge_constitutional_snapshot,
)
from src.municipal_finance_icms_education import (  # noqa: E402
    load_icms_education_source,
    merge_icms_education_source,
)


class MunicipalFinanceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        municipalities = load_municipality_registry(REPO_ROOT / "public" / "data" / "municipios_index.json")
        snapshot = load_source_snapshot(
            DATA_PIPELINE_DIR / "data" / "municipal_finance" / "source_snapshot.json"
        )
        constitutional_snapshot = load_constitutional_snapshot(
            DATA_PIPELINE_DIR / "data" / "municipal_finance" / "constitutional_source_snapshot.json"
        )
        snapshot = merge_constitutional_snapshot(snapshot, constitutional_snapshot)
        icms_education_source = load_icms_education_source(
            DATA_PIPELINE_DIR / "data" / "municipal_finance" / "icms_education" / "rs",
            REPO_ROOT / "config" / "municipalities" / "rs.json",
        )
        snapshot = merge_icms_education_source(
            snapshot,
            icms_education_source,
            municipalities,
        )
        cls.contracts = {
            municipality["ibgeCode"]: build_contract(municipality, snapshot)
            for municipality in municipalities
        }

    def test_zero_denominator_is_null(self) -> None:
        result = derived_rate(
            [10.0],
            0.0,
            "x / y",
            ["x"],
            "y",
            "siconfi_dca_function_2024",
            2024,
        )
        self.assertIsNone(result["value"])
        self.assertEqual(result["nullReasonCode"], "zero_denominator")

    def test_missing_component_is_not_zero(self) -> None:
        result = derived_rate(
            [10.0, None],
            100.0,
            "(x + z) / y",
            ["x", "z"],
            "y",
            "siconfi_dca_function_2024",
            2024,
        )
        self.assertIsNone(result["value"])
        self.assertEqual(result["nullReasonCode"], "missing_calculation_component")

    def test_agudo_reference_values(self) -> None:
        contract = self.contracts["4300109"]
        self.assertEqual(contract["amounts"]["qseDistributedClosedYear"]["value"], 1_045_009.11)
        self.assertEqual(contract["amounts"]["fundebTotalAnnualForecast"]["value"], 21_730_973.67)
        self.assertEqual(contract["programStatuses"]["fundebVaar"]["status"], "confirmed_non_beneficiary")
        self.assertEqual(contract["reconciliation"]["status"], "reconciled")
        self.assertEqual(
            contract["constitutionalApplication"]["mdeAppliedAmount"]["canonical"]["value"],
            18_296_611.85,
        )
        self.assertEqual(
            contract["constitutionalApplication"]["mdeAppliedRate"]["canonical"]["value"],
            25.71,
        )
        self.assertEqual(contract["constitutionalApplication"]["mdeAppliedRate"]["canonical"]["referenceYear"], 2025)
        self.assertEqual(contract["icmsEducation"]["latestAssessmentYear"], 2024)
        self.assertEqual(contract["icmsEducation"]["latestDistributionYear"], 2026)
        self.assertEqual(contract["icmsEducation"]["latest"]["imers"], 71.00519)
        self.assertEqual(
            contract["icmsEducation"]["latest"]["preSharePercent"],
            0.189147163,
        )

    def test_nova_santa_rita_vaar_is_forecast_included_in_total(self) -> None:
        contract = self.contracts["4313375"]
        vaar = contract["amounts"]["fundebVaarAnnualForecast"]
        self.assertEqual(contract["programStatuses"]["fundebVaar"]["status"], "confirmed_beneficiary")
        self.assertEqual(vaar["value"], 3_360_004.63)
        self.assertEqual(vaar["financialStage"], "forecast")
        self.assertEqual(vaar["compositionStatus"], "included_in_total")
        self.assertFalse(vaar["summationAllowed"])

    def test_andre_da_rocha_preserves_missing_optional_dca_field_without_zero_imputation(self) -> None:
        contract = self.contracts["4300661"]
        outstanding = contract["execution"]["dcaEducation"]["outstandingNonProcessed"]
        self.assertEqual(contract["dataQuality"]["level"], "medium")
        self.assertEqual(contract["execution"]["dcaEducation"]["referenceYear"], 2025)
        self.assertIsNone(outstanding["value"])
        self.assertEqual(outstanding["nullReasonCode"], "not_published")
        self.assertNotEqual(outstanding["value"], 0)

    def test_contract_serialization_is_stable(self) -> None:
        contract = self.contracts["4314902"]
        first = json.dumps(contract, ensure_ascii=False, separators=(",", ":"))
        second = json.dumps(contract, ensure_ascii=False, separators=(",", ":"))
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
