import importlib.util
import json
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PIPELINE_ROOT = REPO_ROOT / "data_pipeline"
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))
MODULE_SPEC = importlib.util.spec_from_file_location(
    "education_attendance",
    REPO_ROOT / "data_pipeline" / "src" / "education_attendance.py",
)
attendance = importlib.util.module_from_spec(MODULE_SPEC)
assert MODULE_SPEC.loader is not None
MODULE_SPEC.loader.exec_module(attendance)


def projection(value=80.0, denominator=100.0, numerator=80.0):
    return {
        "available": True,
        "base_year": 2025,
        "historical_years": [2024, 2025],
        "historical_numerator": [70.0, numerator],
        "historical_population": [100.0, denominator],
        "historical_percent_raw": [70.0, value],
        "historical_percent": [70.0, min(100.0, value)],
        "years": [2026, 2036],
        "projected_numerator": [numerator + 1, numerator + 10],
        "projected_population": [99.0, 90.0],
        "projected_percent_raw": [81.8, 100.0],
        "projected_percent": [81.8, 100.0],
        "method": "last_observed_numerator_with_state_age_denominator",
        "trend": {
            "selectedBasis": "lower_magnitude_long_term_trend",
            "diverges": False,
        },
        "denominator_model": {
            "method": "municipal_base_scaled_by_rs_age_group_change",
        },
        "uncertainty": {
            "status": "not_estimated",
            "interval": None,
        },
        "warnings": [],
    }


def planning_contract(denominator=100.0, numerator=25.0):
    value = numerator / denominator * 100 if denominator > 0 else None
    return {
        "status": "available",
        "model": "last_components",
        "targetValidationStatus": "configured_unvalidated",
        "historical": [
            {"year": 2024, "numerator": numerator - 2, "denominator": denominator, "value": value - 2},
            {"year": 2025, "numerator": numerator, "denominator": denominator, "value": value},
        ],
        "projected": [
            {"year": 2036, "numerator": numerator, "denominator": denominator, "rawValue": value}
        ],
        "targets": [{"year": 2036, "value": 50.0, "type": "configured_reference"}],
        "referenceTrajectory": [
            {"year": 2025, "value": value or 0},
            {"year": 2031, "value": 35.0},
            {"year": 2036, "value": 50.0},
        ],
        "diagnostics": {"warnings": []},
    }


class EducationAttendanceTests(unittest.TestCase):
    def setUp(self):
        self.municipalities = ["A", "B", "C", "D"]
        self.projections = {
            "municipios": {
                name: {
                    key: projection(80.0, 100.0 + index * 100, 80.0)
                    for key in attendance.AGE_INDICATORS
                }
                for index, name in enumerate(self.municipalities)
            }
        }
        self.planning = {
            "municipios": {
                name: {"basico_integral": planning_contract(100.0 + index * 100)}
                for index, name in enumerate(self.municipalities)
            }
        }

    def build(self):
        return attendance.build_education_attendance_payload(
            self.projections,
            self.planning,
            self.municipalities,
        )

    def test_contract_preserves_raw_values_and_metadata(self):
        contract = self.build()["municipios"]["A"]["ageCoverage"]["creche"]
        self.assertEqual(contract["contractVersion"], "education-attendance-v2")
        self.assertEqual(contract["observed"]["rawValue"], 80.0)
        self.assertEqual(contract["observed"]["displayValue"], 80.0)
        self.assertEqual(contract["scenario"]["projected"][-1]["rawValue"], 100.0)
        self.assertEqual(contract["scenario"]["type"], "conditional_projection")
        self.assertEqual(contract["reference"]["year"], 2036)
        self.assertEqual(contract["formulaId"], "formula.creche")
        self.assertEqual(
            contract["scenario"]["trend"]["selectedBasis"],
            "lower_magnitude_long_term_trend",
        )
        self.assertEqual(
            contract["scenario"]["denominatorModel"]["method"],
            "municipal_base_scaled_by_rs_age_group_change",
        )
        self.assertEqual(
            contract["scenario"]["uncertainty"]["status"],
            "not_estimated",
        )

    def test_contract_uses_canonical_legal_and_monitoring_references(self):
        age_coverage = self.build()["municipios"]["A"]["ageCoverage"]
        self.assertEqual(age_coverage["pre_escola"]["reference"]["year"], 2028)
        self.assertEqual(age_coverage["basico_6_17"]["reference"]["year"], 2029)
        monitoring = age_coverage["basico_15_17"]["reference"]
        self.assertEqual(monitoring["kind"], "monitoring")
        self.assertEqual(monitoring["value"], 100)
        self.assertIsNone(monitoring["year"])
        self.assertEqual(monitoring["label"], "Referência de acompanhamento")

    def test_invalid_denominator_remains_non_calculable(self):
        self.projections["municipios"]["A"]["creche"] = projection(0.0, 0.0, 10.0)
        contract = self.build()["municipios"]["A"]["ageCoverage"]["creche"]
        self.assertIsNone(contract["observed"]["rawValue"])
        self.assertTrue(contract["diagnostics"]["invalidDenominator"])

    def test_small_denominator_rule_is_deterministic_and_strict(self):
        first = self.build()
        second = self.build()
        self.assertEqual(first["smallDenominatorRule"], second["smallDenominatorRule"])
        self.assertEqual(first["smallDenominatorRule"]["thresholds"]["creche"], 175.0)
        self.assertTrue(first["municipios"]["A"]["ageCoverage"]["creche"]["diagnostics"]["smallDenominator"])
        self.assertFalse(first["municipios"]["B"]["ageCoverage"]["creche"]["diagnostics"]["smallDenominator"])

    def test_enrollment_and_stage_only_contracts_are_not_emitted(self):
        payload = self.build()
        municipality = payload["municipios"]["A"]
        self.assertEqual(set(municipality), {"contractVersion", "municipality", "ageCoverage", "integral"})
        self.assertEqual(set(municipality["integral"]), {"overall"})
        serialized = json.dumps(payload, ensure_ascii=False).lower()
        self.assertNotIn("enrollmentscenarios", serialized)
        self.assertNotIn("last_value", serialized)
        self.assertNotIn('"type": "maintenance"', serialized)

    def test_integral_uses_only_existing_pne_reference_trajectory(self):
        overall = self.build()["municipios"]["A"]["integral"]["overall"]
        self.assertEqual(overall["scenario"]["type"], "pne_reference_trajectory")
        self.assertEqual(overall["scenario"]["method"], "configured_pne_reference_trajectory")
        self.assertEqual(
            [(point["year"], point["rawValue"]) for point in overall["scenario"]["projected"]],
            [(2031, 35.0), (2036, 50.0)],
        )
        self.assertNotIn("model", overall["scenario"])
        self.assertNotIn("qualityEvidence", overall["scenario"])

    def test_age_queries_use_direct_fields_and_exact_age_denominators(self):
        cases = {
            "0_5": ("mat_basico_0_3", "mat_basico_4_5", "between 0 and 5"),
            "4_17": ("mat_basico_4_5", "mat_basico_15_17", "between 4 and 17"),
            "6_14": ("mat_basico_6_10", "mat_basico_11_14", "between 6 and 14"),
        }
        for suffix, (first_field, last_field, age_filter) in cases.items():
            numerator = (REPO_ROOT / "data_pipeline" / "queries" / f"matriculas_basico_{suffix}.sql").read_text(encoding="utf-8").lower()
            denominator = (REPO_ROOT / "data_pipeline" / "queries" / f"pop_{suffix}.sql").read_text(encoding="utf-8").lower()
            self.assertIn(first_field, numerator)
            self.assertIn(last_field, numerator)
            self.assertIn(age_filter, denominator)
            self.assertIn("sum(t1.pop_estimada)", denominator)

    def test_generated_artifact_matches_simplified_contract(self):
        index = json.loads(
            (REPO_ROOT / "public" / "data" / "municipios_index.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(len(index["municipios"]), 497)
        for municipality in index["municipios"]:
            municipal_path = (
                REPO_ROOT
                / "public"
                / "data"
                / "municipios"
                / municipality["id_municipio"]
                / "index.json"
            )
            payload = json.loads(municipal_path.read_text(encoding="utf-8"))
            contract = payload["educacao"]["atendimento_cenarios"]
            self.assertEqual(contract["contractVersion"], "education-attendance-v2")
            serialized = json.dumps(contract, ensure_ascii=False).lower()
            self.assertNotIn("enrollmentscenarios", serialized)
            self.assertNotIn("last_value", serialized)
            self.assertNotIn('"type": "maintenance"', serialized)
            self.assertEqual(set(contract["ageCoverage"]), set(attendance.AGE_INDICATORS))
            self.assertEqual(set(contract["integral"]), {"overall"})
            for indicator in contract["ageCoverage"].values():
                self.assertEqual(
                    indicator["scenario"]["type"],
                    "conditional_projection",
                )
                expected_method = {
                    "creche": "last_observed_numerator_with_state_age_denominator",
                    "pre_escola": "last_observed_numerator_with_state_age_denominator",
                    "basico_6_17": (
                        "municipal_state_shrunk_theil_sen_log_enrollment_"
                        "with_state_age_denominator"
                    ),
                    "basico_15_17": (
                        "state_aggregate_damped_holt_enrollment_with_"
                        "state_age_denominator"
                    ),
                    "infantil_0_5": "last_observed_numerator_with_state_age_denominator",
                    "obrigatoria_4_17": (
                        "municipal_state_shrunk_theil_sen_log_enrollment_"
                        "with_state_age_denominator"
                    ),
                    "escolar_6_14": "last_observed_numerator_with_state_age_denominator",
                }[indicator["indicatorKey"]]
                self.assertEqual(indicator["scenario"]["method"], expected_method)

    def test_public_display_is_capped_while_raw_ratio_is_preserved(self):
        self.projections["municipios"]["A"]["creche"] = projection(
            118.7,
            100.0,
            118.7,
        )
        contract = self.build()["municipios"]["A"]["ageCoverage"]["creche"]

        self.assertEqual(contract["observed"]["rawValue"], 118.7)
        self.assertEqual(contract["observed"]["displayValue"], 100.0)
        self.assertTrue(contract["diagnostics"]["above100"])
        self.assertIn("limitada a 100%", contract["diagnostics"]["warnings"][0])


if __name__ == "__main__":
    unittest.main()
