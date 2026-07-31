import copy
import json
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PIPELINE_DIR = REPO_ROOT / "data_pipeline"
if str(PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(PIPELINE_DIR))

from src.pne2026_public_diagnostic_v2 import (  # noqa: E402
    CATALOG_VERSION,
    PUBLIC_SCHEMA_VERSION,
    PUBLIC_VERSION,
    apply_pne2026_diagnostic_presentation,
    audit_pne2026_public_diagnostic_v2,
    build_pne2026_public_diagnostic_v2,
    load_pne2026_diagnostic_presentation_catalog,
)
from data_pipeline.tests.test_pne2026_diagnostic_snapshot_parity import (  # noqa: E402
    _GitBlobSnapshot,
)


EXPECTED_ESSENTIALS = [
    "creche",
    "pre_escola",
    "basico_6_17",
    "basico_integral",
    "idade_regular_nono",
    "saeb_matematica_anos_finais",
    "medio_concluido_18_29",
    "adequacao_af",
    "salas_acessiveis",
]
EXPECTED_THEME_LABELS = [
    "Atendimento escolar",
    "Educação em tempo integral",
    "Aprendizagem e trajetória escolar",
    "Escolaridade e alfabetização",
    "Educação profissional e EJA",
    "Profissionais da educação",
    "Infraestrutura escolar",
    "Gestão escolar e educação ambiental",
]


def _diagnostic(indicators=None):
    return {
        "municipalityId": "4300000",
        "municipalityName": "Município de teste",
        "indicators": indicators or [],
        "pne2026PublicDiagnostic": {"version": "pne2026-public-diagnostic-v1"},
    }


def _pne_result(value, year=2025, *, attained=False, meta=100):
    return {
        "available": value is not None,
        "end_value": value,
        "end_year": year if value is not None else None,
        "meta": meta,
        "direction": "at_least",
        "distance": None if value is None else value - meta,
        "atingida": attained,
        "display": {
            "end_value": "-" if value is None else f"{value}%",
            "status": "Meta atingida" if attained else "Meta não atingida",
            "interpretation": "Leitura pública herdada do PNE.",
        },
    }


def _flatten(contract):
    return [result for goal in contract["goals"] for result in goal["results"]]


class Pne2026PublicDiagnosticV2CatalogTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = load_pne2026_diagnostic_presentation_catalog()
        cls.results = cls.catalog["results"]
        cls.by_id = {item["indicatorId"]: item for item in cls.results}

    def test_versioned_allowlist_has_exactly_34_unique_pairs_and_24_goals(self):
        pairs = [(item["goalId"], item["indicatorId"]) for item in self.results]
        self.assertEqual(self.catalog["catalogVersion"], CATALOG_VERSION)
        self.assertEqual(len(pairs), 34)
        self.assertEqual(len(set(pairs)), 34)
        self.assertEqual(len({item["indicatorId"] for item in self.results}), 34)
        self.assertEqual(len({item["goalId"] for item in self.results}), 24)

    def test_tiers_and_fixed_essential_order_are_canonical(self):
        essentials = sorted(
            (item for item in self.results if item["tier"] == "essential"),
            key=lambda item: item["priorityOrder"],
        )
        self.assertEqual([item["indicatorId"] for item in essentials], EXPECTED_ESSENTIALS)
        self.assertEqual(sum(item["tier"] == "essential" for item in self.results), 9)
        self.assertEqual(
            sum(item["tier"] == "complementary" for item in self.results), 25
        )

    def test_eight_public_themes_have_stable_ids_and_separate_order(self):
        themes = self.catalog["themes"]
        self.assertEqual([theme["label"] for theme in themes], EXPECTED_THEME_LABELS)
        self.assertEqual([theme["order"] for theme in themes], list(range(1, 9)))
        self.assertTrue(all(theme["id"].endswith("_v2") for theme in themes))

    def test_only_two_exact_pairs_are_contextual_proxies(self):
        proxies = {
            (item["goalId"], item["indicatorId"])
            for item in self.results
            if item["relationshipType"] == "contextual_proxy"
        }
        self.assertEqual(
            proxies,
            {
                ("11.b", "fundamental_concluido_18_mais"),
            },
        )
        self.assertEqual(
            {item["relationshipType"] for item in self.results},
            {"direct", "partial_component", "contextual_proxy"},
        )

    def test_global_order_is_numeric_and_canonical_within_each_goal(self):
        self.assertEqual([item["resultOrder"] for item in self.results], list(range(1, 35)))
        numeric_goal_order = sorted(
            dict.fromkeys(item["goalId"] for item in self.results),
            key=lambda goal_id: (int(goal_id.split(".")[0]), goal_id.split(".")[1]),
        )
        self.assertEqual(
            list(dict.fromkeys(item["goalId"] for item in self.results)),
            numeric_goal_order,
        )

    def test_basico_15_17_is_complementary_without_reference(self):
        item = self.by_id["basico_15_17"]
        self.assertNotIn("indicatorReference", item)
        self.assertNotIn("legalGoal", item)
        self.assertEqual(item["classificationPolicy"], "informative_only")

    def test_six_saeb_results_are_partial_official_and_not_comparable_or_projected(self):
        saeb = [item for item in self.results if item["indicatorId"].startswith("saeb_")]
        self.assertEqual(len(saeb), 6)
        for item in saeb:
            self.assertEqual(item["relationshipType"], "partial_component")
            self.assertEqual(item["sourceIds"], ["inep_saeb"])
            self.assertEqual(item["indicatorReference"]["dimension"], "adequate_or_higher")
            self.assertEqual(item["legalGoal"]["deadline"], 2036)
            self.assertEqual(
                item["usage"],
                {
                    "stateComparison": False,
                    "statewidePosition": False,
                    "similarMunicipalities": False,
                    "trajectory": False,
                },
            )
            methodology = self.catalog["methodologyOverrides"][item["indicatorId"]]
            self.assertIn("Saeb 2023", methodology["universe"])
            self.assertIn(methodology["adequateLevelMinimum"], {4, 5, 6})

    def test_ept_results_remain_four_distinct_results_and_12c_has_two_milestones(self):
        ept_ids = [
            "medio_tecnico_articulado_percentual",
            "medio_tecnico_participacao_publica",
            "subsequente_expansao",
            "eja_integrada_educacao_profissional_percentual",
        ]
        self.assertEqual(
            [item["indicatorId"] for item in self.results if item["indicatorId"] in ept_ids],
            ept_ids,
        )
        eja = self.by_id["eja_integrada_educacao_profissional_percentual"]
        self.assertEqual(eja["goalId"], "12.c")
        self.assertEqual(eja["indicatorReference"], {"value": 25, "year": 2031})
        self.assertEqual(eja["finalReference"], {"value": 50, "year": 2036})

    def test_every_result_has_explicit_value_policy_and_above_100_policies_are_semantic(self):
        self.assertTrue(all(item.get("valuePolicy") for item in self.results))
        self.assertEqual(
            self.by_id["subsequente_expansao"]["valuePolicy"],
            "accumulated_growth_from_minus_100",
        )
        self.assertEqual(
            self.by_id["rendimento_magisterio"]["valuePolicy"],
            "comparative_ratio_above_100",
        )
        self.assertEqual(
            self.by_id["medio_tecnico_articulado_percentual"]["valuePolicy"],
            "enrolment_ratio_above_100",
        )

    def test_catalog_preserves_the_five_historical_provenance_records(self):
        missing = {item["indicatorId"] for item in self.results if not item["sourceIds"]}
        self.assertEqual(
            missing,
            {
                "creche",
                "pre_escola",
                "basico_6_17",
                "basico_15_17",
                "rendimento_magisterio",
            },
        )
        source_ids = {source["id"] for source in self.catalog["sources"]}
        self.assertNotIn("pipeline_rendimento_professores_provenance_pending", source_ids)
        self.assertNotIn("municipal_age_population_panel", source_ids)

    def test_pipeline_export_metadata_includes_goal_ref_and_12c_without_react_map(self):
        categories = {
            "test": {
                "items": [
                    {"key": "eja_integrada_educacao_profissional_percentual"},
                    {"key": "aee"},
                ]
            }
        }
        apply_pne2026_diagnostic_presentation(categories)
        eja, unrelated = categories["test"]["items"]
        self.assertEqual(eja["goalId"], "12.c")
        self.assertEqual(eja["diagnosticPresentation"]["goalId"], "12.c")
        self.assertNotIn("goalId", unrelated)


class Pne2026PublicDiagnosticV2BuilderTest(unittest.TestCase):
    def test_parallel_contract_is_catalog_derived_and_preserves_v1_input(self):
        diagnostic = _diagnostic()
        original_v1 = copy.deepcopy(diagnostic["pne2026PublicDiagnostic"])
        contract = build_pne2026_public_diagnostic_v2(
            diagnostic,
            {"indicadores": {"basico_integral": _pne_result(40)}},
        )
        self.assertEqual(contract["version"], PUBLIC_VERSION)
        self.assertEqual(contract["schemaVersion"], PUBLIC_SCHEMA_VERSION)
        self.assertEqual(contract["presentationCatalogVersion"], CATALOG_VERSION)
        self.assertEqual(len(contract["scope"]["resultPairs"]), 31)
        self.assertEqual(diagnostic["pne2026PublicDiagnostic"], original_v1)
        self.assertTrue(contract["publicationReady"])

    def test_missing_essential_is_not_zeroed_or_replaced_by_complementary_result(self):
        contract = build_pne2026_public_diagnostic_v2(
            _diagnostic(),
            {"indicadores": {"escolas_integral": _pne_result(40)}},
        )
        results = _flatten(contract)
        self.assertEqual([result["indicatorId"] for result in results], ["escolas_integral"])
        self.assertEqual(contract["summary"]["essentialAvailableCount"], 0)
        self.assertEqual(contract["scope"]["essentialIndicatorIds"], EXPECTED_ESSENTIALS)
        self.assertEqual(len(contract["presentation"]["resultDefinitions"]), 31)

    def test_contextual_proxy_is_numeric_but_never_classified(self):
        contract = build_pne2026_public_diagnostic_v2(
            _diagnostic(),
            {"indicadores": {"fundamental_concluido_18_mais": _pne_result(90, 2022)}},
        )
        [result] = _flatten(contract)
        self.assertEqual(result["relationshipType"], "contextual_proxy")
        self.assertIsNone(result["classification"])
        self.assertIsNone(result["remainingGap"])
        self.assertIsNone(result["favorableDifference"])

    def test_integrated_technical_component_is_complementary_without_classification(self):
        below = build_pne2026_public_diagnostic_v2(
            _diagnostic(),
            {"indicadores": {"medio_tecnico_articulado_percentual": _pne_result(20)}},
        )
        at_target = build_pne2026_public_diagnostic_v2(
            _diagnostic(),
            {
                "indicadores": {
                    "medio_tecnico_articulado_percentual": _pne_result(
                        50, attained=True, meta=50
                    )
                }
            },
        )
        self.assertIsNone(_flatten(below)[0]["classification"])
        self.assertIsNone(_flatten(at_target)[0]["classification"])
        self.assertIsNone(_flatten(at_target)[0]["indicatorReference"])
        self.assertIsNone(_flatten(at_target)[0]["distance"])

    def test_subsequente_growth_is_hidden_until_the_2025_baseline_is_fixed(self):
        for value in (-100.1, -100, 240.5):
            with self.subTest(value=value):
                contract = build_pne2026_public_diagnostic_v2(
                    _diagnostic(),
                    {"indicadores": {"subsequente_expansao": _pne_result(value)}},
                )
                self.assertEqual(_flatten(contract), [])

    def test_any_finite_result_already_public_in_pne_is_preserved(self):
        contract = build_pne2026_public_diagnostic_v2(
            _diagnostic(),
            {"indicadores": {"pos_graduacao": _pne_result(110)}},
        )
        [result] = _flatten(contract)
        self.assertEqual(result["current"]["value"], 110)
        self.assertEqual(contract["summary"]["availableResultCount"], 1)

    def test_previously_blocked_result_inherits_source_and_period_from_pne_flow(self):
        technical = {
            "indicatorId": "creche",
            "displayValue": 42.5,
            "unit": "percent",
            "source": {
                "sourceIds": [
                    "inep_censo_escolar",
                    "municipal_age_population_panel",
                ],
                "labels": [
                    "INEP — Censo Escolar",
                    "Base municipal de população por idade",
                ],
                "periodicity": "anual",
                "latestYear": 2025,
            },
        }
        contract = build_pne2026_public_diagnostic_v2(
            _diagnostic([technical]),
            {"indicadores": {"creche": _pne_result(42.5, meta=60)}},
        )
        [result] = _flatten(contract)
        self.assertEqual(result["source"], technical["source"])
        self.assertEqual(result["sourceIds"], technical["source"]["sourceIds"])
        self.assertEqual(result["current"]["displayValue"], 42.5)
        self.assertEqual(result["current"]["displayText"], "42.5%")
        self.assertEqual(result["indicatorReference"]["value"], 60)
        self.assertEqual(result["publicReading"], "Leitura pública herdada do PNE.")
        self.assertEqual(result["publicDescription"], result["relationshipReading"])
        self.assertIn(
            "municipal_age_population_panel",
            {source["id"] for source in contract["sources"]},
        )

    def test_saeb_optional_comparisons_and_trajectory_are_suppressed_by_catalog(self):
        technical = {
            "indicatorId": "saeb_matematica_anos_finais",
            "benchmarks": {
                "state": {
                    "status": "comparable",
                    "value": 50,
                    "year": 2023,
                    "position": "better",
                }
            },
            "similarMunicipalities": {"status": "available", "cohortSize": 20},
            "trajectory": {"status": "available", "estimatedAchievementYear": 2030},
        }
        contract = build_pne2026_public_diagnostic_v2(
            _diagnostic([technical]),
            {"indicadores": {"saeb_matematica_anos_finais": _pne_result(70, 2023)}},
        )
        [result] = _flatten(contract)
        self.assertNotIn("stateComparison", result)
        self.assertNotIn("statewidePosition", result)
        self.assertNotIn("similarMunicipalities", result)
        self.assertNotIn("trajectory", result)

    def test_allowed_materialized_optional_evidence_is_sanitized_and_counted(self):
        technical = {
            "indicatorId": "basico_integral",
            "rawValue": 40,
            "currentYear": 2025,
            "unit": "percent",
            "direction": "at_least",
            "targetComparisonStatus": "eligible",
            "benchmarks": {
                "state": {
                    "status": "comparable",
                    "municipalityValue": 40,
                    "municipalityYear": 2025,
                    "value": 30,
                    "year": 2025,
                    "method": "ratio_of_sums",
                    "coverageRate": 1,
                    "municipalityCount": 497,
                    "favorableDifference": 10,
                    "position": "better",
                },
                "municipalDistribution": {
                    "status": "available",
                    "performancePercentile": 80,
                },
            },
            "similarMunicipalities": {
                "status": "available",
                "indicatorId": "basico_integral",
                "year": 2025,
                "cohortSize": 20,
                "featuresUsed": ["offering_size"],
                "compatibility": {
                    "sameIndicator": True,
                    "sameYear": True,
                    "sameFormula": True,
                    "sameUnit": True,
                    "sameTerritorialBasis": True,
                    "sameOfferBasis": True,
                },
                "statistics": {"median": 32},
                "members": [{"municipalityName": "Interno"}],
            },
            "trajectory": {
                "status": "available",
                "scenarioType": "component_maintenance",
                "model": "last_components",
                "baseYear": 2025,
                "observedFavorableAnnualPace": 1,
                "historyPointCount": 2,
                "projectedValue": 50,
                "quality": "media",
                "estimatedAchievementYear": 2030,
                "sourceCodes": ["internal_code"],
            },
        }
        contract = build_pne2026_public_diagnostic_v2(
            _diagnostic([technical]),
            {"indicadores": {"basico_integral": _pne_result(40)}},
        )
        [result] = _flatten(contract)
        self.assertEqual(result["stateComparison"]["state"], "above")
        self.assertEqual(result["stateComparison"]["municipalityValue"], 40)
        self.assertEqual(result["stateComparison"]["stateValue"], 30)
        self.assertEqual(result["stateComparison"]["unit"], "percent")
        self.assertIn("reading", result["stateComparison"])
        self.assertIn("valueReading", result["stateComparison"])
        self.assertIn("reading", result["statewidePosition"])
        self.assertNotIn("members", result["similarMunicipalities"])
        self.assertNotIn("trajectory", result)
        self.assertEqual(contract["summary"]["estimatedAchievementYearCount"], 0)
        self.assertEqual(contract["summary"]["stateAboveOrNearCount"], 1)
        self.assertEqual(contract["summary"]["stateBelowCount"], 0)

    def test_builder_contains_no_react_manual_map_or_public_file_write(self):
        module_text = (
            PIPELINE_DIR / "src" / "pne2026_public_diagnostic_v2.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("pne2026IndicatorGoalRefs", module_text)
        self.assertNotIn("public/data/municipios", module_text)
        self.assertNotIn("write_text", module_text)
        self.assertNotIn("def _classify", module_text)
        self.assertNotIn("def _value_is_allowed", module_text)
        react_files = list((REPO_ROOT / "src").rglob("*.jsx")) + list(
            (REPO_ROOT / "src").rglob("*.tsx")
        )
        self.assertFalse(
            any(
                "pne2026-public-diagnostic-v2" in path.read_text(encoding="utf-8")
                for path in react_files
            )
        )


class Pne2026PublicDiagnosticV2AuditTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with _GitBlobSnapshot() as snapshot:
            registry = snapshot.json("public/data/municipios_index.json")
            payloads = []
            for municipality in registry["municipios"]:
                municipality_id = municipality["id_municipio"]
                diagnostic = snapshot.json(
                    f"public/data/municipios/{municipality_id}/diagnostico.json"
                )
                pne_cycle = snapshot.json(
                    f"public/data/municipios/{municipality_id}/index.json"
                )["pne_2026_2036"]
                payloads.append((diagnostic, pne_cycle))
        cls.audit = audit_pne2026_public_diagnostic_v2(payloads)

    def test_all_497_municipalities_have_integral_pne_v2_parity(self):
        self.assertEqual(self.audit["municipalityCount"], 497)
        self.assertEqual(self.audit["authorizedPairCount"], 34)
        self.assertEqual(self.audit["goalCount"], 22)
        self.assertEqual(self.audit["indicatorCount"], 31)
        self.assertEqual(self.audit["pneAvailableOccurrences"], 15114)
        self.assertEqual(self.audit["v2AvailableOccurrences"], 15114)
        self.assertTrue(self.audit["publicationReady"])
        self.assertEqual(self.audit["pneAbsentOccurrences"], 293)
        self.assertEqual(self.audit["duplicateResultCount"], 0)
        self.assertEqual(self.audit["outOfCatalogResultCount"], 0)
        self.assertEqual(self.audit["sourceBlockedIndicatorIds"], [])
        self.assertEqual(
            self.audit["historicalSourceBlockerIndicatorIds"],
            [
                "basico_15_17",
                "basico_6_17",
                "creche",
                "pre_escola",
                "rendimento_magisterio",
            ],
        )
        self.assertEqual(
            self.audit["pneV2Divergences"]["missingInV2ByIndicator"], {}
        )
        self.assertEqual(
            self.audit["pneV2Divergences"]["unexpectedInV2ByIndicator"], {}
        )
        self.assertEqual(
            self.audit["pneV2Divergences"]["valueDifferencesByIndicator"], {}
        )
        for key in (
            "yearDifferencesByIndicator",
            "unitDifferencesByIndicator",
            "classificationDifferencesByIndicator",
            "sourceDifferencesByIndicator",
        ):
            self.assertEqual(self.audit["pneV2Divergences"][key], {})

    def test_visible_results_are_inherited_without_recalculation(self):
        self.assertEqual(
            {
                indicator_id: self.audit["occurrencesByIndicator"][indicator_id]
                for indicator_id in (
                    "creche",
                    "pre_escola",
                    "basico_6_17",
                    "basico_15_17",
                )
            },
            {
                "creche": 497,
                "pre_escola": 497,
                "basico_6_17": 497,
                "basico_15_17": 497,
            },
        )
        self.assertEqual(self.audit["pneNegativeValuesByIndicator"], {})
        self.assertEqual(
            self.audit["v2NegativeValuesByIndicator"],
            self.audit["pneNegativeValuesByIndicator"],
        )
        self.assertEqual(
            self.audit["v2ValuesAbove100ByIndicator"],
            self.audit["pneValuesAbove100ByIndicator"],
        )

    def test_hidden_subsequente_is_not_part_of_the_visible_audit(self):
        self.assertEqual(
            self.audit["subsequenteExpansao"],
            {
                "pneAvailable": 0,
                "currentV1Available": 14,
                "v2Available": 0,
                "pneAbove100": 0,
                "v2Above100": 0,
            },
        )

    def test_audit_counts_relationships_classifications_and_optional_evidence(self):
        self.assertEqual(
            sum(self.audit["relationshipCounts"].values()),
            self.audit["v2AvailableOccurrences"],
        )
        self.assertEqual(
            sum(self.audit["classificationCounts"].values()),
            self.audit["v2AvailableOccurrences"],
        )
        self.assertIn("stateComparison", self.audit["optionalEvidenceCounts"])
        self.assertIn("trajectory", self.audit["optionalEvidenceCounts"])


if __name__ == "__main__":
    unittest.main()
