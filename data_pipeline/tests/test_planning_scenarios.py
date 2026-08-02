import copy
import importlib.util
import json
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PIPELINE_ROOT = REPO_ROOT / "data_pipeline"
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

PLANNING_SPEC = importlib.util.spec_from_file_location(
    "planning_scenarios",
    PIPELINE_ROOT / "src" / "planning_scenarios.py",
)
planning = importlib.util.module_from_spec(PLANNING_SPEC)
assert PLANNING_SPEC.loader is not None
PLANNING_SPEC.loader.exec_module(planning)

PARTITION_SPEC = importlib.util.spec_from_file_location(
    "partition_static_data",
    PIPELINE_ROOT / "scripts" / "partition_static_data.py",
)
partition = importlib.util.module_from_spec(PARTITION_SPEC)
assert PARTITION_SPEC.loader is not None
PARTITION_SPEC.loader.exec_module(partition)


class PlanningScenarioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        index = json.loads(
            (REPO_ROOT / "public" / "data" / "municipios_index.json").read_text(
                encoding="utf-8"
            )
        )
        cls.municipalities = [item["nome"] for item in index["municipios"]]
        cls.payload = planning.load_approved_planning_scenarios(
            PIPELINE_ROOT / "data" / "planning_scenarios",
            cls.municipalities,
        )

    def test_approved_artifacts_become_public_contracts_for_all_municipalities(self):
        payload = self.payload
        self.assertEqual(payload["publicationStatus"], "published")
        self.assertEqual(payload["scenarioType"], "maintenance")
        self.assertEqual(payload["municipalityCount"], 497)
        self.assertEqual(set(payload["indicatorKeys"]), set(planning.INDICATOR_KEYS))
        for contracts in payload["municipios"].values():
            self.assertEqual(set(contracts), set(planning.INDICATOR_KEYS))
            for indicator_key, contract in contracts.items():
                self.assertEqual(contract["model"], "last_components")
                if indicator_key in {"basico_integral", "escolas_integral"}:
                    self.assertEqual(contract["referenceKind"], "legal")
                    self.assertEqual(
                        contract["targetValidationStatus"],
                        "official_law",
                    )
                    self.assertTrue(contract["referenceId"].startswith("reference.6.a."))
                else:
                    self.assertEqual(contract["referenceKind"], "configured")
                    self.assertEqual(
                        contract["targetValidationStatus"],
                        "configured_unvalidated",
                    )
                self.assertEqual(
                    contract["formulaId"],
                    f"formula.{indicator_key}",
                )
                self.assertNotIn("mode", contract)
                self.assertNotIn("productionDecision", contract)
                self.assertTrue(contract["referenceTrajectory"])
                self.assertTrue(
                    all("requiredAnnualPacePp" in target for target in contract["targets"])
                )

        planning.validate_public_planning_scenarios(payload, self.municipalities)

    def test_public_validation_rejects_reference_and_coverage_divergences(self):
        municipality = self.municipalities[0]
        contracts = self.payload["municipios"][municipality]
        cases = (
            ("basico_integral", "targetValidationStatus", "configured_unvalidated"),
            ("pos_graduacao", "targetValidationStatus", "official_law"),
            ("basico_integral", "referenceId", "reference.invalid"),
            ("basico_integral", "referenceKind", "configured"),
            ("temporarios", "targetValidationStatus", "unknown"),
        )
        for indicator_key, field, invalid_value in cases:
            with self.subTest(indicator_key=indicator_key, field=field):
                original = contracts[indicator_key][field]
                contracts[indicator_key][field] = invalid_value
                try:
                    with self.assertRaises(ValueError):
                        planning.validate_public_planning_scenarios(
                            self.payload,
                            self.municipalities,
                        )
                finally:
                    contracts[indicator_key][field] = original

        original_contracts = dict(contracts)
        del contracts["temporarios"]
        try:
            with self.assertRaisesRegex(ValueError, "incomplete or unexpected"):
                planning.validate_public_planning_scenarios(
                    self.payload,
                    self.municipalities,
                )
        finally:
            contracts.clear()
            contracts.update(original_contracts)

    def test_contract_validation_rejects_non_persistent_or_incomplete_points(self):
        artifact = json.loads(
            (
                PIPELINE_ROOT
                / "data"
                / "planning_scenarios"
                / "shadow-projections"
                / "basico_integral.json"
            ).read_text(encoding="utf-8")
        )
        original = artifact["projections"][0]

        changed_component = copy.deepcopy(original)
        changed_component["projected"][0]["rawNumerator"] += 1
        with self.assertRaisesRegex(ValueError, "last-components persistence"):
            planning._validate_contract(
                changed_component,
                "basico_integral",
                changed_component["municipality"],
            )

        incomplete_horizon = copy.deepcopy(original)
        del incomplete_horizon["projected"][3]
        with self.assertRaisesRegex(ValueError, "complete and consecutive"):
            planning._validate_contract(
                incomplete_horizon,
                "basico_integral",
                incomplete_horizon["municipality"],
            )

    def test_required_pace_respects_both_directions(self):
        at_least = {
            "direction": "at_least",
            "historical": [{"year": 2025, "value": 20}],
            "targets": [
                {"year": 2031, "value": 35},
                {"year": 2036, "value": 50},
            ],
        }
        at_most = {
            "direction": "at_most",
            "historical": [{"year": 2025, "value": 42}],
            "targets": [{"year": 2031, "value": 30}],
        }
        increasing_trajectory = planning.build_reference_trajectory(at_least)
        decreasing_trajectory = planning.build_reference_trajectory(at_most)
        increasing_targets = planning.build_reference_targets(
            at_least, increasing_trajectory
        )
        decreasing_targets = planning.build_reference_targets(
            at_most, decreasing_trajectory
        )
        self.assertEqual(increasing_targets[0]["requiredAnnualPacePp"], 2.5)
        self.assertEqual(increasing_targets[1]["requiredAnnualPacePp"], 3.0)
        self.assertEqual(decreasing_targets[0]["requiredAnnualPacePp"], -2.0)
        self.assertEqual(decreasing_trajectory[-1], {"year": 2036, "value": 30.0})

    def test_reference_does_not_invert_series_when_already_satisfied(self):
        contract = {
            "direction": "at_most",
            "historical": [{"year": 2025, "value": 25}],
            "targets": [{"year": 2031, "value": 30}],
        }
        trajectory = planning.build_reference_trajectory(contract)
        targets = planning.build_reference_targets(contract, trajectory)
        self.assertEqual({point["value"] for point in trajectory}, {25.0})
        self.assertEqual(targets[0]["requiredAnnualPacePp"], 0.0)

    def test_partition_keeps_current_projections_and_adds_separate_scenarios(self):
        current = {"creche": {"available": True}}
        scenarios = {"basico_integral": {"scenarioType": "maintenance"}}
        payloads = {
            "fundeb": {},
            "pnate": {},
            "projecoes": {"municipios": {"Teste": current}},
            "planning_scenarios": {"municipios": {"Teste": scenarios}},
            "education_attendance": {"municipios": {"Teste": {"contractVersion": "education-attendance-v1"}}},
            "pne_2014_2024_indicadores": {},
            "pne_2014_2024_rankings": {},
            "pne_2026_2036_indicadores": {},
            "pne_2026_2036_rankings": {},
            "diagnostico": {},
        }
        record = partition.MunicipalityRecord(
            ibge_code="4300001",
            name="Teste",
            slug="teste",
        )
        payload = partition.build_municipio_payload(payloads, "Teste", record)
        self.assertEqual(payload["id_municipio"], "4300001")
        self.assertEqual(payload["municipio"], "Teste")
        self.assertEqual(payload["slug"], "teste")
        cycle = payload["pne_2026_2036"]
        self.assertIs(cycle["projecoes"], current)
        self.assertIs(cycle["cenarios_planejamento"], scenarios)
        self.assertEqual(payload["educacao"]["atendimento_cenarios"]["contractVersion"], "education-attendance-v1")


if __name__ == "__main__":
    unittest.main()
