import copy
import json
import re
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_PIPELINE_DIR = REPO_ROOT / "data_pipeline"
if str(DATA_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_PIPELINE_DIR))

from src.municipal_diagnostic import (  # noqa: E402
    build_municipal_diagnostic_v2,
    build_pne_2026_public_diagnostic,
    calculate_directional_distance,
    load_indicator_catalog,
    load_pne_2026_public_diagnostic_config,
)


EXPECTED_GOAL_IDS = [
    "1.a",
    "1.c",
    "4.a",
    "6.a",
    "12.a",
    "12.b",
    "3.a",
    "5.a",
    "5.b",
    "5.d",
    "4.b",
    "4.c",
    "4.d",
    "17.a",
    "17.f",
    "17.b",
    "17.d",
    "8.c",
    "18.b",
    "8.b",
    "19.c",
    "11.a",
    "11.b",
    "11.c",
]

EXPECTED_PUBLISHED_GOAL_IDS = [
    "4.b",
    "4.c",
    "4.d",
    "6.a",
    "8.b",
    "8.c",
    "11.a",
    "11.b",
    "11.c",
    "12.a",
    "12.b",
    "17.a",
    "17.d",
    "17.f",
    "18.b",
    "19.c",
]

EXPECTED_CURRENT_PAGE_GOAL_IDS = [
    "1.a",
    "1.c",
    "4.a",
    "6.a",
    "12.c",
    "12.a",
    "12.b",
    "3.a",
    "5.a",
    "5.b",
    "5.d",
    "4.b",
    "4.c",
    "4.d",
    "17.a",
    "17.f",
    "17.b",
    "17.d",
    "8.c",
    "18.b",
    "8.b",
    "19.c",
    "11.a",
    "11.b",
    "11.c",
]


def goal_sort_key(goal_id):
    number, letter = goal_id.split(".", maxsplit=1)
    return int(number), letter


def synthetic_indicator(
    *,
    indicator_id="basico_integral",
    current=80.0,
    target=70.0,
    direction="at_least",
    year=2025,
):
    distance = calculate_directional_distance(current, target, direction)
    return {
        "indicatorId": indicator_id,
        "theme": "atendimento",
        "title": "Resultado municipal de teste",
        "currentYear": year,
        "rawValue": current,
        "displayValue": current,
        "unit": "percent",
        "direction": direction,
        "targetComparisonStatus": "eligible",
        "configuredReference": {
            "value": target,
            "year": 2036,
            "direction": direction,
        },
        **distance,
        "source": {"sourceIds": ["inep_censo_escolar"]},
        "benchmarks": {
            "state": {"status": "unavailable"},
            "municipalDistribution": {"status": "unavailable"},
        },
        "similarMunicipalities": {"status": "unavailable"},
        "trajectory": {"status": "not_available"},
    }


def contract_with(*indicators):
    return {"indicators": list(indicators)}


def only_result(public_contract):
    results = [
        result
        for goal in public_contract["goals"]
        for result in goal["results"]
    ]
    if len(results) != 1:
        raise AssertionError(f"Esperado um resultado; encontrados {len(results)}")
    return results[0]


def add_state(indicator, state_value, position):
    direction = indicator["direction"]
    current = indicator["rawValue"]
    favorable = (
        current - state_value if direction == "at_least" else state_value - current
    )
    indicator["benchmarks"]["state"] = {
        "status": "comparable",
        "value": state_value,
        "year": indicator["currentYear"],
        "municipalityValue": current,
        "municipalityYear": indicator["currentYear"],
        "method": "ratio_of_sums",
        "coverageRate": 1.0,
        "favorableDifference": favorable,
        "position": position,
    }


class PublicDiagnosticConfigurationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = load_pne_2026_public_diagnostic_config()

    def test_closed_allowlist_and_authorized_relationship_counts(self):
        goals = self.config["goals"]
        relationships = [
            relationship
            for goal in goals
            for relationship in goal["relationships"]
        ]
        self.assertEqual([goal["goalId"] for goal in goals], EXPECTED_GOAL_IDS)
        self.assertEqual(len(goals), 24)
        self.assertEqual(len(relationships), 20)
        self.assertEqual(
            sum(item["relationship"] == "direct" for item in relationships), 11
        )
        self.assertEqual(
            sum(
                item["relationship"] == "partial_component"
                for item in relationships
            ),
            9,
        )
        indicator_ids = [item["indicatorId"] for item in relationships]
        self.assertEqual(len(indicator_ids), len(set(indicator_ids)))

    def test_allowlist_drift_against_current_page_and_goal_refs(self):
        refs_text = (REPO_ROOT / "src/data/pne2026IndicatorGoalRefs.js").read_text(
            encoding="utf-8"
        )
        contract = json.loads(
            (
                REPO_ROOT
                / "contracts"
                / "pne2026-goal-indicator-contract.json"
            ).read_text(encoding="utf-8")
        )
        refs = {
            relation["indicatorId"]: relation["goalId"]
            for relation in contract["relations"]
            if relation["includeInCycleGoalRefs"]
        }
        self.assertIn("PNE_2026_GOAL_INDICATOR_CONTRACT", refs_text)
        page = json.loads(
            (REPO_ROOT / "public/data/indicadores.json").read_text(encoding="utf-8")
        )["cycles"]["pne_2026_2036"]
        first_occurrences = []
        for category in page["categories"]:
            for item in category["items"]:
                goal_id = refs.get(item["key"])
                if goal_id and goal_id not in first_occurrences:
                    first_occurrences.append(goal_id)
        self.assertEqual(first_occurrences, EXPECTED_CURRENT_PAGE_GOAL_IDS)

        configured_pairs = {
            (goal["goalId"], relationship["indicatorId"])
            for goal in self.config["goals"]
            for relationship in goal["relationships"]
        }
        self.assertTrue(
            all(refs.get(indicator_id) == goal_id for goal_id, indicator_id in configured_pairs)
        )
        current_page_ids = {
            item["key"] for category in page["categories"] for item in category["items"]
        }
        self.assertTrue(
            all(indicator_id in current_page_ids for _, indicator_id in configured_pairs)
        )

    def test_official_source_registry_is_complete_and_restricted(self):
        self.assertEqual(
            {source["id"] for source in self.config["sources"]},
            {"inep_censo_escolar", "ibge_censo_demografico_2010_2022"},
        )
        for source in self.config["sources"]:
            self.assertTrue(source["organization"])
            self.assertTrue(source["publicTitle"])
            self.assertTrue(source["period"])
            self.assertRegex(source["officialUrl"], r"^https://(www\.)?(gov\.br/inep|ibge\.gov\.br)/")


class PublicDiagnosticBuilderTest(unittest.TestCase):
    def test_public_goals_use_integer_then_letter_order(self):
        public = build_pne_2026_public_diagnostic(
            contract_with(
                synthetic_indicator(indicator_id="alfabetizacao_pop_15_mais"),
                synthetic_indicator(indicator_id="educacao_ambiental"),
                synthetic_indicator(indicator_id="idade_regular_quinto"),
            )
        )
        self.assertEqual(
            [goal["goalId"] for goal in public["goals"]],
            ["4.b", "8.c", "11.a"],
        )
        self.assertEqual([goal["order"] for goal in public["goals"]], [1, 2, 3])

    def test_at_least_maintain_distance_and_partial_component_language(self):
        public = build_pne_2026_public_diagnostic(
            contract_with(synthetic_indicator(current=80, target=70))
        )
        result = only_result(public)
        self.assertEqual(result["classification"], "maintain")
        self.assertEqual(result["favorableDifference"], 10)
        self.assertEqual(result["remainingGap"], 0)
        self.assertEqual(result["relationship"], "partial_component")
        goal = public["goals"][0]
        self.assertNotIn("classification", goal)
        self.assertNotIn("status", goal)
        self.assertNotIn("goalAttained", goal)
        self.assertIn("este resultado", result["targetReading"])

    def test_at_most_advance_and_directionally_correct_text(self):
        indicator = synthetic_indicator(
            indicator_id="temporarios",
            current=40,
            target=30,
            direction="at_most",
        )
        public = build_pne_2026_public_diagnostic(contract_with(indicator))
        result = only_result(public)
        self.assertEqual(result["relationship"], "direct")
        self.assertEqual(result["classification"], "advance")
        self.assertEqual(result["favorableDifference"], -10)
        self.assertEqual(result["remainingGap"], 10)
        self.assertIn("reduzir", result["targetReading"])

    def test_directional_inconsistency_fails_generation(self):
        indicator = synthetic_indicator(current=80, target=70)
        indicator["remainingGap"] = 10
        with self.assertRaisesRegex(ValueError, "Campos direcionais divergentes"):
            build_pne_2026_public_diagnostic(contract_with(indicator))

    def test_state_above_near_below_omission_and_combined_readings(self):
        cases = [
            (70, "better", "above", "posição favorável"),
            (80.05, "equivalent", "near", "posição favorável"),
            (90, "worse", "below", "continuar sendo acompanhado"),
        ]
        for state_value, position, public_state, reading_fragment in cases:
            with self.subTest(public_state=public_state):
                indicator = synthetic_indicator(current=80, target=70)
                add_state(indicator, state_value, position)
                result = only_result(
                    build_pne_2026_public_diagnostic(contract_with(indicator))
                )
                self.assertEqual(result["stateComparison"]["state"], public_state)
                self.assertIn(reading_fragment, result["publicReading"])

        result = only_result(
            build_pne_2026_public_diagnostic(
                contract_with(synthetic_indicator(current=60, target=70))
            )
        )
        self.assertNotIn("stateComparison", result)
        self.assertEqual(result["classification"], "advance")

    def test_at_most_state_language_represents_favorable_direction(self):
        indicator = synthetic_indicator(
            indicator_id="temporarios",
            current=20,
            target=30,
            direction="at_most",
        )
        add_state(indicator, 30, "better")
        result = only_result(
            build_pne_2026_public_diagnostic(contract_with(indicator))
        )
        self.assertEqual(result["stateComparison"]["state"], "above")
        self.assertIn("abaixo do valor", result["stateComparison"]["reading"])
        self.assertIn("posição favorável", result["stateComparison"]["reading"])

    def test_statewide_bands_and_invalid_percentile_omission(self):
        cases = [
            (75, "top_quarter"),
            (50, "middle"),
            (24.99, "more_room_to_advance"),
        ]
        for percentile, band in cases:
            with self.subTest(percentile=percentile):
                indicator = synthetic_indicator()
                indicator["benchmarks"]["municipalDistribution"] = {
                    "status": "available",
                    "performancePercentile": percentile,
                }
                result = only_result(
                    build_pne_2026_public_diagnostic(contract_with(indicator))
                )
                self.assertEqual(result["statewidePosition"]["band"], band)
                self.assertNotIn("percentile", result["statewidePosition"])

        indicator = synthetic_indicator()
        indicator["benchmarks"]["municipalDistribution"] = {
            "status": "available",
            "performancePercentile": 101,
        }
        result = only_result(
            build_pne_2026_public_diagnostic(contract_with(indicator))
        )
        self.assertNotIn("statewidePosition", result)

    def test_similar_offering_comparison_gate_and_public_shape(self):
        indicator = synthetic_indicator()
        indicator["similarMunicipalities"] = {
            "status": "available",
            "indicatorId": "basico_integral",
            "year": 2025,
            "featuresUsed": ["offering_size"],
            "statistics": {"median": 70},
            "compatibility": {
                "sameIndicator": True,
                "sameYear": True,
                "sameFormula": True,
                "sameUnit": True,
                "sameTerritorialBasis": True,
                "sameOfferBasis": True,
            },
        }
        result = only_result(
            build_pne_2026_public_diagnostic(contract_with(indicator))
        )
        comparison = result["similarMunicipalities"]
        self.assertEqual(comparison["state"], "above")
        self.assertEqual(comparison["median"], 70)
        self.assertNotIn("compatibility", comparison)
        self.assertNotIn("cohort", comparison)

        indicator["similarMunicipalities"]["compatibility"]["sameFormula"] = False
        result = only_result(
            build_pne_2026_public_diagnostic(contract_with(indicator))
        )
        self.assertNotIn("similarMunicipalities", result)

    def test_public_trajectory_gate(self):
        indicator = synthetic_indicator()
        indicator["trajectory"] = {
            "status": "available",
            "scenarioType": "component_maintenance",
            "quality": "media",
            "observedFavorableAnnualPace": 1.5,
            "historyPointCount": 5,
            "projectedValue": 82,
            "baseYear": 2025,
            "estimatedAchievementYear": 2030,
        }
        result = only_result(
            build_pne_2026_public_diagnostic(contract_with(indicator))
        )
        self.assertEqual(result["trajectory"]["historicalState"], "improved")
        self.assertEqual(result["trajectory"]["estimatedAchievementYear"], 2030)
        self.assertNotIn("quality", result["trajectory"])
        self.assertNotIn("model", result["trajectory"])

        indicator["trajectory"].update(
            {"scenarioType": "required_trajectory", "quality": "not_assessed"}
        )
        result = only_result(
            build_pne_2026_public_diagnostic(contract_with(indicator))
        )
        self.assertNotIn("trajectory", result)

    def test_publication_gates_sources_deduplication_and_summary(self):
        first = synthetic_indicator(current=80, target=70)
        second = synthetic_indicator(
            indicator_id="escolas_integral", current=60, target=70
        )
        public = build_pne_2026_public_diagnostic(contract_with(first, second))
        self.assertEqual(public["summary"]["displayedResultsCount"], 2)
        self.assertEqual(public["summary"]["reachedResultsCount"], 1)
        self.assertEqual(public["summary"]["advanceResultsCount"], 1)
        self.assertEqual(len(public["sources"]), 1)
        self.assertEqual(len(public["goals"]), 1)
        self.assertEqual(len(public["goals"][0]["results"]), 2)
        self.assertEqual(
            [result["indicatorId"] for result in public["goals"][0]["results"]],
            ["basico_integral", "escolas_integral"],
        )

        for field in ("rawValue", "currentYear"):
            with self.subTest(missing=field):
                blocked = synthetic_indicator()
                blocked[field] = None
                output = build_pne_2026_public_diagnostic(contract_with(blocked))
                self.assertEqual(output["summary"]["displayedResultsCount"], 0)
                self.assertEqual(output["goals"], [])

        blocked = synthetic_indicator()
        blocked["source"]["sourceIds"] = []
        output = build_pne_2026_public_diagnostic(contract_with(blocked))
        self.assertEqual(output["goals"], [])

        config = load_pne_2026_public_diagnostic_config()
        config["sources"][0]["officialUrl"] = ""
        output = build_pne_2026_public_diagnostic(
            contract_with(synthetic_indicator()), config=config
        )
        self.assertEqual(output["goals"], [])
        self.assertEqual(output["sources"], [])

    def test_input_is_unchanged_output_is_deterministic_and_exclusions_are_silent(self):
        technical = contract_with(
            synthetic_indicator(),
            synthetic_indicator(indicator_id="internet", current=90, target=100),
        )
        before = copy.deepcopy(technical)
        first = build_pne_2026_public_diagnostic(technical)
        second = build_pne_2026_public_diagnostic(technical)
        self.assertEqual(technical, before)
        self.assertEqual(first, second)
        result_ids = {
            result["indicatorId"]
            for goal in first["goals"]
            for result in goal["results"]
        }
        self.assertEqual(result_ids, {"basico_integral"})
        self.assertNotIn("internet", json.dumps(first))
        self.assertEqual(len(technical["indicators"]), 2)

    def test_pipeline_always_adds_layer_without_changing_schema_version(self):
        contract = build_municipal_diagnostic_v2(
            municipality_name="Município de teste",
            municipality_id="4300000",
            results={},
            generated_at="2026-07-21T00:00:00-03:00",
            catalog=load_indicator_catalog(),
        )
        self.assertEqual(contract["schemaVersion"], "municipal-diagnostic-v2")
        self.assertIn("pne2026PublicDiagnostic", contract)
        self.assertEqual(len(contract["indicators"]), 54)
        self.assertEqual(contract["pne2026PublicDiagnostic"]["goals"], [])

    def test_types_keep_the_exclusive_v3_contract_versioned(self):
        types = (
            REPO_ROOT / "src/features/diagnostic/diagnosticTypes.ts"
        ).read_text(encoding="utf-8")
        self.assertIn("interface Pne2026PublicDiagnosticV3", types)
        self.assertIn("schemaVersion: 'pne2026-public-diagnostic-v4'", types)
        self.assertIn("contractVersion: '1.9.0'", types)
        self.assertIn("diagnosticSource: 'v3'", types)
        self.assertNotIn("Pne2026PublicDiagnosticV1", types)


class PublicDiagnosticPayloadAuditTest(unittest.TestCase):
    def test_all_497_contracts_match_the_homologated_public_audit(self):
        public_data = REPO_ROOT / "public/data"
        index = json.loads(
            (public_data / "municipios_index.json").read_text(encoding="utf-8")
        )
        totals = {
            "contracts": 0,
            "technicalIndicators": 0,
            "displayedResults": 0,
            "stateComparisons": 0,
            "statewidePositions": 0,
            "similarMunicipalities": 0,
            "trajectories": 0,
            "estimatedYears": 0,
        }
        per_municipality = []
        allowed_ids = None
        municipalities_with_trajectory = 0
        public_ids = set()
        for entry in index["municipios"]:
            contract = json.loads(
                (
                    public_data
                    / "municipios"
                    / entry["id_municipio"]
                    / "diagnostico.json"
                ).read_text(encoding="utf-8")
            )
            public = build_pne_2026_public_diagnostic(contract)
            self.assertEqual(contract["pne2026PublicDiagnostic"], public)
            goal_ids = [goal["goalId"] for goal in public["goals"]]
            self.assertEqual(goal_ids, sorted(goal_ids, key=goal_sort_key))
            self.assertEqual(len(goal_ids), len(set(goal_ids)))
            self.assertTrue(set(goal_ids) <= set(EXPECTED_PUBLISHED_GOAL_IDS))
            self.assertEqual(
                [goal["order"] for goal in public["goals"]],
                list(range(1, len(goal_ids) + 1)),
            )
            self.assertTrue(all(goal["results"] for goal in public["goals"]))
            results = [
                result for goal in public["goals"] for result in goal["results"]
            ]
            allowed_ids = set(public["scope"]["allowedIndicatorIds"])
            public_ids.update(result["indicatorId"] for result in results)
            totals["contracts"] += 1
            totals["technicalIndicators"] += len(contract["indicators"])
            totals["displayedResults"] += len(results)
            totals["stateComparisons"] += sum(
                "stateComparison" in result for result in results
            )
            totals["statewidePositions"] += sum(
                "statewidePosition" in result for result in results
            )
            totals["similarMunicipalities"] += sum(
                "similarMunicipalities" in result for result in results
            )
            trajectory_count = sum("trajectory" in result for result in results)
            totals["trajectories"] += trajectory_count
            totals["estimatedYears"] += sum(
                "estimatedAchievementYear" in result.get("trajectory", {})
                for result in results
            )
            municipalities_with_trajectory += trajectory_count > 0
            per_municipality.append(len(results))
            self.assertTrue(
                all(result["sourceIds"] for result in results), entry["nome"]
            )

        self.assertEqual(index["total_municipios"], 497)
        self.assertEqual(
            totals,
            {
                "contracts": 497,
                "technicalIndicators": 24_353,
                "displayedResults": 9_119,
                "stateComparisons": 6_148,
                "statewidePositions": 5_964,
                "similarMunicipalities": 6_086,
                "trajectories": 1_982,
                "estimatedYears": 583,
            },
        )
        self.assertEqual(min(per_municipality), 15)
        self.assertEqual(max(per_municipality), 20)
        self.assertEqual(sum(count == 0 for count in per_municipality), 0)
        self.assertEqual(municipalities_with_trajectory, 497)
        self.assertTrue(public_ids <= allowed_ids)


if __name__ == "__main__":
    unittest.main()
