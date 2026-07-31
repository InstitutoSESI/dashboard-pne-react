import sys
import unittest
from pathlib import Path


DATA_PIPELINE_DIR = Path(__file__).resolve().parents[1]
if str(DATA_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_PIPELINE_DIR))

from src.pne.goal_indicator_contract import (  # noqa: E402
    CONTRACT,
    contract_hash,
    get_formula_for_indicator,
    get_indicator_reference_profile,
    get_relation,
    get_relation_context,
    resolve_comparison_reference,
    resolve_legal_reference,
    stable_contract_json,
    validate_contract,
)


class Pne2026GoalIndicatorContractTests(unittest.TestCase):
    def test_contract_cardinalities_and_validation(self):
        self.assertIs(validate_contract(CONTRACT), CONTRACT)
        self.assertEqual(CONTRACT["contractVersion"], "1.9.0")
        self.assertEqual(len(CONTRACT["goals"]), 73)
        self.assertEqual(len(CONTRACT["indicators"]), 59)
        self.assertEqual(len(CONTRACT["relations"]), 59)
        self.assertEqual(len(CONTRACT["sources"]), 17)
        self.assertEqual(len(CONTRACT["formulas"]), 59)
        modes = {
            mode: sum(
                relation["mode"] == mode
                for relation in CONTRACT["relations"]
            )
            for mode in ("progress", "tracking", "complementary", "hidden")
        }
        self.assertEqual(
            modes,
            {
                "progress": 27,
                "tracking": 15,
                "complementary": 15,
                "hidden": 2,
            },
        )

    def test_basico_15_17_uses_a_municipal_monitoring_reference(self):
        relation = get_relation("4.a", "basico_15_17")
        self.assertEqual(relation["mode"], "tracking")
        self.assertIsNone(relation["referenceId"])
        self.assertEqual(relation["referenceKind"], "monitoring")
        self.assertTrue(relation["canDistance"])
        self.assertTrue(relation["canStatus"])
        self.assertFalse(relation["canProjection"])
        self.assertFalse(relation["includeInReferenceSummary"])
        self.assertTrue(relation["includeInCycleSummary"])
        self.assertFalse(relation["includeInLegalSummary"])
        self.assertTrue(relation["includeInDiagnostic"])
        self.assertTrue(relation["includeInCycleGoalRefs"])
        reference = resolve_comparison_reference("4.a", "basico_15_17")
        self.assertEqual(reference["value"], 100)
        self.assertEqual(reference["direction"], "at_least")
        reference_ids = {
            reference["referenceId"]
            for reference in CONTRACT["goals"]["4.a"]["legalReferences"]
        }
        self.assertNotIn("reference.4.a.basico_15_17", reference_ids)
        self.assertEqual(get_relation("4.a", "basico_6_17")["mode"], "progress")

    def test_non_comparable_relations_have_no_classifying_capability(self):
        for relation in CONTRACT["relations"]:
            if relation["mode"] in {"progress", "tracking"}:
                continue
            self.assertFalse(relation["canDistance"])
            self.assertFalse(relation["canStatus"])
            self.assertFalse(relation["canProjection"])
            self.assertIsNone(relation["referenceId"])
            if relation["mode"] == "hidden":
                self.assertFalse(relation["includeInDiagnostic"])
                self.assertFalse(relation["includeInReferenceSummary"])

    def test_attendance_formula_references_and_population_lineage(self):
        expected = {
            "creche": ("legal", 60, 2036),
            "pre_escola": ("legal", 100, 2028),
            "basico_6_17": ("legal", 100, 2029),
            "basico_15_17": ("monitoring", 100, None),
        }
        for indicator_id, (kind, value, year) in expected.items():
            reference = get_indicator_reference_profile(indicator_id, 2025)
            self.assertEqual(reference["kind"], kind)
            self.assertEqual(reference["value"], value)
            self.assertEqual(reference["year"], year)
            formula = get_formula_for_indicator(indicator_id)
            self.assertEqual(formula["runtime"]["strategy"], "ratio_of_counts")
            self.assertTrue(formula["runtime"]["numeratorField"])
            self.assertTrue(formula["runtime"]["denominatorField"])

        expected_models = {
            "creche": "last_observation_persistence",
            "pre_escola": "last_observation_persistence",
            "basico_6_17": "municipal_state_shrunk_theil_sen_log",
            "basico_15_17": "state_aggregate_damped_holt",
        }
        for indicator_id, expected_model in expected_models.items():
            projection_config = get_formula_for_indicator(indicator_id)[
                "runtime"
            ]["projection"]
            self.assertEqual(
                projection_config["numeratorModel"],
                expected_model,
            )
        robust_parameters = get_formula_for_indicator("basico_6_17")[
            "runtime"
        ]["projection"]["parameters"]
        self.assertEqual(robust_parameters["historyStartYear"], 2014)
        self.assertEqual(robust_parameters["windowObservations"], 5)
        self.assertEqual(robust_parameters["damping"], 0.8)
        self.assertEqual(robust_parameters["shrinkage"], 4)
        self.assertEqual(robust_parameters["excludedYears"], [])
        self.assertEqual(
            robust_parameters["maximumAbsoluteAnnualLogTrend"],
            0.15,
        )

        projection_policy = CONTRACT["projectionPolicies"][
            "attendance_backtested_hybrid_minimum_five_consecutive"
        ]
        self.assertEqual(
            projection_policy["selectionAndValidationValuePolicy"],
            "raw_without_display_cap",
        )
        self.assertEqual(
            projection_policy["displayPolicy"],
            "cap_at_100_preserve_raw_for_audit",
        )

        historical = CONTRACT["sources"]["municipal_age_population_panel"]
        self.assertEqual(
            historical["lineage"]["pathConfiguration"],
            "SESI_DB_DIR",
        )
        projection = CONTRACT["sources"]["ibge_population_projection_2024"]
        self.assertEqual(
            projection["lineage"]["pathConfiguration"],
            "POPULATION_PROJECTION_SOURCE_PATH",
        )

    def test_accelerated_relations_keep_their_approved_modes(self):
        expected = {
            ("9.d", "educacao_indigena_cobertura_estimada_4_17"): "complementary",
            ("10.b", "aee_oferta_escolas_elegiveis"): "complementary",
            ("14.c", "superior_concluintes_oferta_local"): "complementary",
            ("15.c", "superior_docentes_mestres_doutores_sede"): "complementary",
        }
        for (goal_id, indicator_id), mode in expected.items():
            relation = get_relation(goal_id, indicator_id)
            self.assertEqual(relation["mode"], mode)
            self.assertTrue(relation["includeInDiagnostic"])
            self.assertFalse(relation["includeInReferenceSummary"])
            self.assertIsNone(relation["referenceId"])
            self.assertEqual(relation["canDistance"], mode == "tracking")
            self.assertEqual(relation["canStatus"], mode == "tracking")
            self.assertFalse(relation["canProjection"])

    def test_selectors_and_multidimensional_reference(self):
        literacy = get_relation("3.a", "alfabetizacao")
        self.assertEqual(literacy["mode"], "progress")
        self.assertTrue(literacy["includeInDiagnostic"])

        hidden = get_relation("17.b", "rendimento_magisterio")
        self.assertEqual(hidden["mode"], "hidden")
        self.assertFalse(hidden["includeInDiagnostic"])

        reference = resolve_legal_reference(
            "5.a",
            "saeb_matematica_anos_iniciais",
            2030,
        )
        self.assertEqual(reference["targetYear"], 2031)
        self.assertEqual(len(reference["milestonesAtYear"]), 2)
        self.assertNotIn("milestone", reference)

        context = get_relation_context(
            "5.a",
            "saeb_matematica_anos_iniciais",
            2030,
        )
        self.assertEqual(context["relation"]["referenceDimension"], "adequate_or_higher")
        self.assertEqual(
            context["legalReference"]["milestone"]["dimension"],
            "adequate_or_higher",
        )
        self.assertEqual(len(context["legalReference"]["milestonesAtYear"]), 1)

    def test_normalization_and_hash_are_deterministic(self):
        self.assertEqual(stable_contract_json(), stable_contract_json())
        self.assertEqual(
            contract_hash(),
            "c9f4baaee43a7f105863a07bcac69d2f56a90095b75d0c7bcde25ca533fedab5",
        )


if __name__ == "__main__":
    unittest.main()
