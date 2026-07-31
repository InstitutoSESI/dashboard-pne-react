import json
import sys
import unittest
from pathlib import Path


DATA_PIPELINE_DIR = Path(__file__).resolve().parents[1]
if str(DATA_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_PIPELINE_DIR))

from src.municipal_diagnostic import (  # noqa: E402
    _build_decision_reading,
    _public_trajectory,
    build_municipal_diagnostic_v2,
    build_state_benchmark_registry,
    calculate_directional_percentile,
    calculate_directional_distance,
    calculate_state_favorable_difference,
    load_indicator_catalog,
)


GENERATED_AT = "2026-07-19T12:00:00-03:00"


def result(value, target, direction="at_least", year=2024, series=None):
    payload = {
        "available": value is not None,
        "end_year": year if value is not None else None,
        "end_value": value,
        "meta": target,
        "meta_label": f"Referência {target}" if target is not None else "Sem referência",
        "direction": direction,
    }
    if series is not None:
        payload["series"] = [
            {"ano": point_year, "valor": point_value}
            for point_year, point_value in series
        ]
    return payload


class DirectionalDistanceTest(unittest.TestCase):
    def test_at_least_attained_and_gap(self):
        self.assertEqual(
            calculate_directional_distance(90, 80, "at_least"),
            {"goalAttained": True, "favorableDistance": 10.0, "remainingGap": 0.0},
        )
        self.assertEqual(
            calculate_directional_distance(70, 80, "at_least"),
            {"goalAttained": False, "favorableDistance": -10.0, "remainingGap": 10.0},
        )

    def test_at_most_attained_and_gap(self):
        self.assertEqual(
            calculate_directional_distance(20, 30, "at_most"),
            {"goalAttained": True, "favorableDistance": 10.0, "remainingGap": 0.0},
        )
        self.assertEqual(
            calculate_directional_distance(40, 30, "at_most"),
            {"goalAttained": False, "favorableDistance": -10.0, "remainingGap": 10.0},
        )

    def test_null_incompatible_and_outside_domain_are_not_compared(self):
        empty = {"goalAttained": None, "favorableDistance": None, "remainingGap": None}
        self.assertEqual(calculate_directional_distance(None, 80, "at_least"), empty)
        self.assertEqual(calculate_directional_distance(70, None, "at_least"), empty)
        self.assertEqual(
            calculate_directional_distance(70, 80, "at_least", comparison_allowed=False),
            empty,
        )
        self.assertEqual(
            calculate_directional_distance(
                110,
                100,
                "at_least",
                value_domain_status="outside_domain_territorial_mismatch",
            ),
            empty,
        )


class MunicipalDiagnosticContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = load_indicator_catalog()

    def build(self, overrides=None, benchmark_registry=None, **kwargs):
        return build_municipal_diagnostic_v2(
            municipality_name="Município de teste",
            municipality_id="4300000",
            results=overrides or {},
            generated_at=GENERATED_AT,
            catalog=self.catalog,
            benchmark_registry=benchmark_registry,
            **kwargs,
        )

    def indicator(self, contract, indicator_id):
        return next(
            item for item in contract["indicators"] if item["indicatorId"] == indicator_id
        )

    def test_all_50_indicators_are_serialized_and_missing_is_never_zero(self):
        contract = self.build()
        self.assertEqual(contract["summary"]["indicatorCount"], 54)
        self.assertEqual(len(contract["indicators"]), 54)
        self.assertEqual(len({item["indicatorId"] for item in contract["indicators"]}), 54)
        self.assertEqual(contract["summary"]["availableResults"], 0)
        for indicator in contract["indicators"]:
            self.assertEqual(indicator["dataStatus"], "missing")
            self.assertIsNone(indicator["rawValue"])
            self.assertIsNone(indicator["displayValue"])
            self.assertIn("rawValue", indicator["nullReasons"])
            self.assertIn("displayValue", indicator["nullReasons"])
            self.assertIsNone(indicator["priorityScore"])
            self.assertIn("priorityScore", indicator["nullReasons"])

    def test_problematic_indicators_are_blocked_and_partial_cases_remain_explicit(self):
        contract = self.build(
            {
                "basico_15_17": result(90, 85),
                "alfabetizacao": result(90, 100),
                "saeb_matematica_anos_iniciais": result(95, 90),
                "medio_tecnico_articulado_percentual": result(10, 50),
                "fundamental_concluido_18_mais": result(70, 85),
                "aee": result(90, 100),
                "creche": result(50, 60),
                "salas_climatizadas": result(80, 100),
                "salas_acessiveis": result(80, 100),
            }
        )
        blocked = {
            "basico_15_17": "methodologically_incompatible",
            "alfabetizacao": "pending_official_definition",
            "saeb_matematica_anos_iniciais": "methodologically_incompatible",
            "medio_tecnico_articulado_percentual": "methodologically_incompatible",
            "fundamental_concluido_18_mais": "methodologically_incompatible",
            "aee": "methodologically_incompatible",
        }
        attention_ids = {item["indicatorId"] for item in contract["attentionItems"]}
        for indicator_id, comparison_status in blocked.items():
            indicator = self.indicator(contract, indicator_id)
            self.assertEqual(indicator["targetComparisonStatus"], comparison_status)
            self.assertIsNone(indicator["goalAttained"])
            self.assertIsNone(indicator["favorableDistance"])
            self.assertIsNone(indicator["remainingGap"])
            self.assertNotIn(indicator_id, attention_ids)

        basico = self.indicator(contract, "basico_15_17")
        self.assertEqual(basico["configuredReference"]["kind"], "legacy_reference")
        alfabetizacao = self.indicator(contract, "alfabetizacao")
        self.assertEqual(
            [milestone["value"] for milestone in alfabetizacao["targetMilestones"]],
            [80, 100],
        )
        saeb = self.indicator(contract, "saeb_matematica_anos_iniciais")
        self.assertEqual(
            {milestone["dimension"] for milestone in saeb["targetMilestones"]},
            {"basic_or_higher", "adequate_or_higher"},
        )
        self.assertEqual(
            self.indicator(contract, "fundamental_concluido_18_mais")[
                "operationalizationStatus"
            ],
            "proxy",
        )
        self.assertEqual(self.indicator(contract, "aee")["presentation"]["statusCode"], "proxy")

        for indicator_id in ("creche", "salas_climatizadas", "salas_acessiveis"):
            indicator = self.indicator(contract, indicator_id)
            self.assertEqual(indicator["legalCorrespondence"], "partial")
            self.assertEqual(indicator["targetComparisonStatus"], "eligible")
            self.assertIn(indicator_id, attention_ids)
            self.assertTrue(
                any(flag["code"] == "partial_legal_correspondence" for flag in indicator["flags"])
            )

    def test_population_coverage_formulas_and_operational_fields_are_preserved(self):
        expected = {
            "creche": ("mat_basico_0_3", "pop_0_3"),
            "pre_escola": ("mat_infantil_pre", "pop_4_5"),
            "basico_6_17": ("mat_basico_6_17", "pop_6_17"),
            "basico_15_17": ("mat_basico_15_17", "pop_15_17"),
        }
        definitions = {
            item["indicatorId"]: item for item in self.catalog["indicators"]
        }
        for indicator_id, (numerator, denominator) in expected.items():
            definition = definitions[indicator_id]
            self.assertEqual(definition["numerator"], numerator)
            self.assertEqual(definition["denominator"], denominator)
            self.assertEqual(
                definition["formula"],
                f"100 * sum({numerator}) / denominator_aggregate({denominator})",
            )
            self.assertEqual(
                definition["valueDomainPolicy"],
                "allow_above_max_known_mixed_territorial_basis",
            )
            self.assertEqual(
                definition["displayPolicy"],
                "cap_at_100_preserve_raw_for_audit",
            )

    def test_mixed_territorial_basis_keeps_raw_and_caps_public_display(self):
        contract = self.build(
            {
                "creche": result(105.5, 60),
                "pre_escola": result(122.222, 100),
                "basico_6_17": result(101.25, 100),
                "basico_15_17": result(104.75, 85),
                "pos_graduacao": result(108.2, 70),
            }
        )
        preserved_ids = {item["indicatorId"] for item in contract["preservedItems"]}
        excluded_ids = {item["indicatorId"] for item in contract["excludedItems"]}

        for indicator_id in ("creche", "pre_escola", "basico_6_17"):
            indicator = self.indicator(contract, indicator_id)
            self.assertEqual(indicator["dataStatus"], "available")
            self.assertEqual(indicator["displayValue"], 100.0)
            self.assertEqual(indicator["valueDomainStatus"], "within_domain")
            self.assertEqual(indicator["targetComparisonStatus"], "eligible")
            self.assertTrue(indicator["goalAttained"])
            self.assertEqual(
                indicator["favorableDistance"],
                indicator["rawValue"] - indicator["configuredReference"]["value"],
            )
            self.assertIn(indicator_id, preserved_ids)
            self.assertNotIn(indicator_id, excluded_ids)
            flag_codes = {flag["code"] for flag in indicator["flags"]}
            self.assertIn("KNOWN_MIXED_TERRITORIAL_BASIS", flag_codes)
            self.assertIn("VALUE_ABOVE_100_ALLOWED_BY_METHOD", flag_codes)

        pre_school = self.indicator(contract, "pre_escola")
        self.assertEqual(pre_school["rawValue"], 122.222)
        self.assertEqual(pre_school["displayValue"], 100.0)
        self.assertAlmostEqual(pre_school["favorableDistance"], 22.222)
        self.assertEqual(
            pre_school["methodology"]["formula"],
            "100 * sum(mat_infantil_pre) / denominator_aggregate(pop_4_5)",
        )
        self.assertEqual(
            pre_school["methodology"]["territorialBasis"],
            {
                "numerator": "município da escola",
                "denominator": "população residente municipal",
            },
        )

        age_15_17 = self.indicator(contract, "basico_15_17")
        self.assertEqual(age_15_17["dataStatus"], "available")
        self.assertEqual(age_15_17["displayValue"], 100.0)
        self.assertEqual(age_15_17["valueDomainStatus"], "within_domain")
        self.assertEqual(
            age_15_17["targetComparisonStatus"], "methodologically_incompatible"
        )
        self.assertIsNone(age_15_17["goalAttained"])
        self.assertEqual(
            age_15_17["exclusionReasons"][0]["code"], "legacy_target_not_legal"
        )

        postgrad = self.indicator(contract, "pos_graduacao")
        self.assertEqual(postgrad["rawValue"], 108.2)
        self.assertEqual(postgrad["displayValue"], 100.0)
        self.assertEqual(postgrad["dataStatus"], "unverifiable")
        self.assertEqual(postgrad["valueDomainStatus"], "outside_domain_unverifiable")
        self.assertNotIn("pos_graduacao", preserved_ids)

    def test_aee_above_100_does_not_receive_mixed_territorial_permission(self):
        contract = self.build({"aee": result(140.8, 100)})
        aee = self.indicator(contract, "aee")
        self.assertNotEqual(aee["valueDomainStatus"], "within_domain")
        self.assertEqual(
            aee["targetComparisonStatus"], "methodologically_incompatible"
        )
        self.assertEqual(aee["exclusionReasons"][0]["code"], "ineligible_aee_denominator")
        self.assertIsNone(aee["goalAttained"])
        self.assertNotIn(
            "KNOWN_MIXED_TERRITORIAL_BASIS",
            {flag["code"] for flag in aee["flags"]},
        )

    def test_temporarios_is_direction_aware_at_most(self):
        attained = self.build({"temporarios": result(20, 30, "at_most")})
        indicator = self.indicator(attained, "temporarios")
        self.assertEqual(indicator["direction"], "at_most")
        self.assertTrue(indicator["goalAttained"])
        self.assertEqual(indicator["favorableDistance"], 10.0)
        self.assertEqual(indicator["remainingGap"], 0.0)
        self.assertIn(
            "temporarios", {item["indicatorId"] for item in attained["preservedItems"]}
        )

        gap = self.build({"temporarios": result(40, 30, "at_most")})
        indicator = self.indicator(gap, "temporarios")
        self.assertFalse(indicator["goalAttained"])
        self.assertEqual(indicator["remainingGap"], 10.0)
        self.assertAlmostEqual(indicator["legacyRelativeGapScore"], 1 / 3)
        self.assertEqual(gap["attentionItems"][0]["indicatorId"], "temporarios")

    def test_summary_order_and_serialization_are_deterministic(self):
        overrides = {
            "creche": result(30, 60),
            "pre_escola": result(50, 100),
            "temporarios": result(40, 30, "at_most"),
        }
        first = self.build(overrides)
        second = self.build(overrides)
        self.assertEqual(first, second)
        encoded = json.dumps(first, ensure_ascii=False, sort_keys=True, allow_nan=False)
        self.assertEqual(json.loads(encoded), first)
        self.assertEqual(
            [item["indicatorId"] for item in first["attentionItems"]],
            ["creche", "pre_escola", "temporarios"],
        )
        self.assertEqual(first["summary"]["availableResults"], 3)
        self.assertEqual(first["summary"]["validLegalComparisons"], 3)
        self.assertEqual(first["summary"]["comparableGaps"], 3)
        self.assertEqual(first["summary"]["goalsAttained"], 0)
        self.assertFalse(first["generationMetadata"]["finalPriorityScorePublished"])
        self.assertFalse(first["generationMetadata"]["financialRecommendationPublished"])


def state_indicator(
    indicator_id,
    value=None,
    *,
    year=2025,
    status="comparable",
    method="ratio_of_sums",
    coverage=100.0,
):
    series = []
    if value is not None:
        series.append(
            {
                "indicator_id": indicator_id,
                "year": year,
                "value": value,
                "aggregation_method": method,
                "municipalities_valid": 20,
                "municipalities_expected": 20,
                "municipal_coverage_percent": coverage,
                "denominator_coverage_percent": coverage,
                "comparison_status": status,
            }
        )
    return {
        "indicator_id": indicator_id,
        "aggregation_method": method,
        "methodology_version": "pne2026-rs-reference-v1",
        "comparison_status": status,
        "unit": "percent",
        "compatibility": {
            "indicatorRule": "same_indicator_id_required",
            "formulaStatus": "curated_equivalent",
            "yearRule": "same_year_required",
            "rangeStatus": "curated_equivalent",
            "stageStatus": "curated_equivalent",
            "unit": "percent",
            "universeStatus": "curated_equivalent",
            "administrativeDependenceStatus": "registry_filters_required",
            "aggregationRuleStatus": "curated_equivalent",
            "methodologyVersion": "pne2026-rs-reference-v1",
            "territorialBasisStatus": "curated_equivalent",
        },
        "series": series,
    }


class StateBenchmarkContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = load_indicator_catalog()

    def build_registry(self, state_indicators, municipal_results):
        return build_state_benchmark_registry(
            state_reference={
                "municipalities_expected": 20,
                "indicators": state_indicators,
            },
            municipal_results=municipal_results,
            catalog=self.catalog,
        )

    def build_contract(self, results, registry):
        return build_municipal_diagnostic_v2(
            municipality_name="M0",
            municipality_id="4300000",
            results=results,
            generated_at=GENERATED_AT,
            catalog=self.catalog,
            benchmark_registry=registry,
        )

    def indicator(self, contract, indicator_id):
        return next(
            item for item in contract["indicators"] if item["indicatorId"] == indicator_id
        )

    def test_favorable_difference_and_percentile_follow_direction(self):
        self.assertAlmostEqual(
            calculate_state_favorable_difference(35.1, 42.7, "at_least"), -7.6
        )
        self.assertAlmostEqual(
            calculate_state_favorable_difference(13.2, 35.8, "at_most"), 22.6
        )
        self.assertEqual(
            calculate_directional_percentile([10, 20, 30], 30, "at_least"),
            250 / 3,
        )
        self.assertEqual(
            calculate_directional_percentile([10, 20, 30], 10, "at_most"),
            250 / 3,
        )

    def test_distribution_uses_same_year_quantiles_and_directional_percentile(self):
        municipal_results = {
            f"M{index}": {"creche": result(index + 1, 60, year=2025)}
            for index in range(20)
        }
        registry = self.build_registry(
            {"creche": state_indicator("creche", 10.5)}, municipal_results
        )
        contract = self.build_contract(municipal_results["M10"], registry)
        distribution = self.indicator(contract, "creche")["benchmarks"][
            "municipalDistribution"
        ]
        self.assertEqual(distribution["status"], "available")
        self.assertEqual(distribution["year"], 2025)
        self.assertEqual(distribution["municipalityCount"], 20)
        self.assertEqual(distribution["coverageRate"], 1.0)
        self.assertEqual(distribution["median"], 10.5)
        self.assertEqual(distribution["q1"], 5.75)
        self.assertEqual(distribution["q3"], 15.25)
        self.assertEqual(distribution["performancePercentile"], 52.5)

    def test_contextual_benchmarks_preserve_raw_values_and_attention_order(self):
        municipal_results = {}
        for index in range(20):
            municipal_results[f"M{index}"] = {
                "creche": result(20 + index, 60, year=2025),
                "pre_escola": result(90 + index, 100, year=2025),
                "basico_15_17": result(70 + index, 85, year=2025),
                "pos_graduacao": result(40 + index, 70, year=2025),
                "temporarios": result(20 + index, 30, "at_most", year=2025),
            }
        municipal_results["M0"] = {
            "creche": result(35.1, 60, year=2025),
            "pre_escola": result(122.222, 100, year=2025),
            "basico_15_17": result(82.9, 85, year=2025),
            "pos_graduacao": result(49.4, 70, year=2025),
            "temporarios": result(13.2, 30, "at_most", year=2025),
        }
        state_indicators = {
            "creche": state_indicator("creche", 42.7),
            "pre_escola": state_indicator("pre_escola", 94.6),
            "basico_15_17": state_indicator("basico_15_17", 89.1),
            "pos_graduacao": state_indicator("pos_graduacao", 56.8),
            "temporarios": state_indicator("temporarios", 35.8),
        }
        registry = self.build_registry(state_indicators, municipal_results)
        with_benchmark = self.build_contract(municipal_results["M0"], registry)
        without_benchmark = self.build_contract(municipal_results["M0"], None)

        self.assertEqual(
            [item["indicatorId"] for item in with_benchmark["attentionItems"]],
            [item["indicatorId"] for item in without_benchmark["attentionItems"]],
        )
        creche = self.indicator(with_benchmark, "creche")
        self.assertAlmostEqual(
            creche["benchmarks"]["state"]["favorableDifference"], -7.6
        )
        self.assertEqual(creche["benchmarks"]["state"]["position"], "worse")

        temporary = self.indicator(with_benchmark, "temporarios")
        self.assertAlmostEqual(
            temporary["benchmarks"]["state"]["favorableDifference"], 22.6
        )
        self.assertEqual(temporary["benchmarks"]["state"]["position"], "better")
        self.assertGreater(
            temporary["benchmarks"]["municipalDistribution"]["performancePercentile"],
            90,
        )

        pre_school = self.indicator(with_benchmark, "pre_escola")
        self.assertEqual(pre_school["rawValue"], 122.222)
        self.assertEqual(pre_school["displayValue"], 100.0)
        self.assertAlmostEqual(
            pre_school["benchmarks"]["state"]["favorableDifference"], 27.622
        )

        age_15_17 = self.indicator(with_benchmark, "basico_15_17")
        self.assertEqual(
            age_15_17["targetComparisonStatus"], "methodologically_incompatible"
        )
        self.assertEqual(age_15_17["benchmarks"]["state"]["status"], "comparable")
        self.assertIsNotNone(
            age_15_17["benchmarks"]["state"]["favorableDifference"]
        )

        summary = with_benchmark["stateBenchmarkSummary"]
        self.assertEqual(summary["analyzedCount"], 4)
        self.assertEqual(summary["eligibleAnalyzedCount"], 4)
        self.assertEqual(
            summary["analyzedCount"],
            summary["betterCount"]
            + summary["worseCount"]
            + summary["equivalentCount"]
            + summary["unavailableCount"],
        )
        self.assertEqual(
            with_benchmark["stateBenchmarkExpandedSummary"]["analyzedCount"], 5
        )
        self.assertLessEqual(len(summary["largestUnfavorableIndicatorIds"]), 3)
        self.assertLessEqual(len(summary["largestFavorableIndicatorIds"]), 2)

    def test_pending_and_year_mismatch_never_receive_state_difference(self):
        municipal_results = {
            f"M{index}": {
                "aee": result(50 + index, 100, year=2025),
                "creche": result(20 + index, 60, year=2025),
            }
            for index in range(20)
        }
        registry = self.build_registry(
            {
                "aee": state_indicator(
                    "aee", status="methodology_pending", method="not_available"
                ),
                "creche": state_indicator("creche", 40, year=2024),
            },
            municipal_results,
        )
        contract = self.build_contract(municipal_results["M0"], registry)
        aee = self.indicator(contract, "aee")["benchmarks"]["state"]
        creche = self.indicator(contract, "creche")["benchmarks"]["state"]
        self.assertEqual(aee["status"], "methodology_pending")
        self.assertIsNone(aee["favorableDifference"])
        self.assertEqual(creche["status"], "year_mismatch")
        self.assertIsNone(creche["favorableDifference"])

    def test_latest_methodologically_valid_common_year_is_used_without_changing_latest_value(self):
        municipal_results = {
            f"M{index}": {
                "creche": result(
                    30 + index,
                    60,
                    year=2025,
                    series=[(2024, 20 + index), (2025, 30 + index)],
                )
            }
            for index in range(20)
        }
        registry = self.build_registry(
            {"creche": state_indicator("creche", 32.5, year=2024)},
            municipal_results,
        )
        contract = self.build_contract(municipal_results["M0"], registry)
        indicator = self.indicator(contract, "creche")
        state = indicator["benchmarks"]["state"]
        distribution = indicator["benchmarks"]["municipalDistribution"]

        self.assertEqual(indicator["currentYear"], 2025)
        self.assertEqual(indicator["rawValue"], 30)
        self.assertEqual(state["status"], "comparable")
        self.assertEqual(state["year"], 2024)
        self.assertEqual(state["municipalityValue"], 20)
        self.assertEqual(state["municipalityYear"], 2024)
        self.assertEqual(state["municipalityLatestYear"], 2025)
        self.assertTrue(state["usesLatestCommonYear"])
        self.assertAlmostEqual(state["favorableDifference"], -12.5)
        self.assertEqual(distribution["year"], 2024)
        self.assertEqual(distribution["municipalityCount"], 20)

    def test_latest_valid_common_year_replaces_an_insufficient_current_state_point(self):
        municipal_results = {
            f"M{index}": {
                "creche": result(
                    30 + index,
                    60,
                    year=2025,
                    series=[(2024, 20 + index), (2025, 30 + index)],
                )
            }
            for index in range(20)
        }
        state = state_indicator("creche", 32.5, year=2024)
        state["series"].append(
            {
                "indicator_id": "creche",
                "year": 2025,
                "value": 40,
                "aggregation_method": "ratio_of_sums",
                "municipalities_valid": 14,
                "municipalities_expected": 20,
                "municipal_coverage_percent": 70,
                "denominator_coverage_percent": 70,
                "comparison_status": "comparable",
            }
        )
        registry = self.build_registry({"creche": state}, municipal_results)
        contract = self.build_contract(municipal_results["M0"], registry)
        benchmark = self.indicator(contract, "creche")["benchmarks"]["state"]

        self.assertEqual(benchmark["status"], "comparable")
        self.assertEqual(benchmark["year"], 2024)
        self.assertEqual(benchmark["municipalityYear"], 2024)
        self.assertTrue(benchmark["usesLatestCommonYear"])

    def test_common_year_is_rejected_when_methodological_signature_differs(self):
        municipal_results = {
            f"M{index}": {
                "creche": result(
                    30 + index,
                    60,
                    year=2025,
                    series=[(2024, 20 + index), (2025, 30 + index)],
                )
            }
            for index in range(20)
        }
        state = state_indicator("creche", 32.5, year=2024)
        state["compatibility"]["rangeStatus"] = "pending"
        registry = self.build_registry({"creche": state}, municipal_results)
        contract = self.build_contract(municipal_results["M0"], registry)
        benchmark = self.indicator(contract, "creche")["benchmarks"]["state"]

        self.assertEqual(benchmark["status"], "methodology_pending")
        self.assertIsNone(benchmark["value"])
        self.assertIsNone(benchmark["favorableDifference"])

    def test_formula_unit_and_universe_mismatch_block_comparison(self):
        indicator_ids = ("creche", "pre_escola", "basico_6_17")
        municipal_results = {
            f"M{index}": {
                indicator_id: result(30 + index, 60, year=2025)
                for indicator_id in indicator_ids
            }
            for index in range(20)
        }
        state_indicators = {
            indicator_id: state_indicator(indicator_id, 40)
            for indicator_id in indicator_ids
        }
        state_indicators["creche"]["unit"] = "count"
        state_indicators["pre_escola"]["compatibility"]["formulaStatus"] = "pending"
        state_indicators["basico_6_17"]["compatibility"]["universeStatus"] = "pending"
        registry = self.build_registry(state_indicators, municipal_results)
        contract = self.build_contract(municipal_results["M0"], registry)
        for indicator_id in indicator_ids:
            state = self.indicator(contract, indicator_id)["benchmarks"]["state"]
            self.assertEqual(state["status"], "methodology_pending")
            self.assertIsNone(state["favorableDifference"])


class TrajectoryGovernancePeerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = load_indicator_catalog()

    def build(self, results, **kwargs):
        return build_municipal_diagnostic_v2(
            municipality_name="M0",
            municipality_id="4300000",
            results=results,
            generated_at=GENERATED_AT,
            catalog=self.catalog,
            **kwargs,
        )

    @staticmethod
    def indicator(contract, indicator_id):
        return next(
            item for item in contract["indicators"] if item["indicatorId"] == indicator_id
        )

    def test_observed_and_required_pace_respect_at_least_and_at_most(self):
        creche = result(40, 60, "at_least", year=2025)
        creche["trend"] = {"slope": 1.5, "observations": 5, "method": "theil_sen_v1"}
        temporary = result(40, 30, "at_most", year=2025)
        temporary["trend"] = {"slope": 2.0, "observations": 5, "method": "theil_sen_v1"}
        contract = self.build({"creche": creche, "temporarios": temporary})
        creche_trajectory = self.indicator(contract, "creche")["trajectory"]
        temporary_trajectory = self.indicator(contract, "temporarios")["trajectory"]
        self.assertEqual(creche_trajectory["observedFavorableAnnualPace"], 1.5)
        self.assertAlmostEqual(creche_trajectory["requiredAnnualPace"], 20 / 11)
        self.assertEqual(temporary_trajectory["observedFavorableAnnualPace"], -2.0)
        self.assertAlmostEqual(temporary_trajectory["requiredAnnualPace"], 10 / 6)
        self.assertEqual(temporary_trajectory["paceStatus"], "moving_away")

    def test_inconclusive_historical_trend_is_not_treated_as_observed_pace(self):
        creche = result(40, 60, "at_least", year=2025)
        creche["trend"] = {
            "status": "inconclusive",
            "slope": 1.5,
            "observations": 5,
            "method": "theil_sen_v1",
        }
        trajectory = self.indicator(self.build({"creche": creche}), "creche")[
            "trajectory"
        ]

        self.assertIsNone(trajectory["observedFavorableAnnualPace"])
        self.assertEqual(trajectory["paceStatus"], "inconclusive")

    def test_trend_projection_and_component_maintenance_are_distinct(self):
        contract = self.build(
            {
                "creche": result(40, 60, year=2025),
                "basico_integral": result(20, 50, year=2025),
            },
            projections={
                "creche": {
                    "available": True,
                    "target_year": 2036,
                    "horizon_year": 2036,
                    "method": "last_observed_numerator_with_state_age_denominator",
                    "years": [2036],
                    "projected_percent_raw": [51.0],
                    "projected_2036_raw": 51.0,
                    "trend": {
                        "selectedBasis": "last_observation_persistence",
                        "diverges": False,
                    },
                    "denominator_model": {
                        "method": "municipal_base_scaled_by_rs_age_group_change",
                    },
                    "uncertainty": {
                        "status": "not_estimated",
                        "interval": None,
                    },
                    "quality": "media",
                    "warnings": [],
                }
            },
            planning_scenarios={
                "basico_integral": {
                    "status": "available",
                    "model": "last_components",
                    "projectionPeriod": {"endYear": 2036},
                    "projected": [{"year": 2031, "rawValue": 20.0}],
                    "qualityEvidence": {"provisionalLevel": "media"},
                    "diagnostics": {"warnings": []},
                }
            },
        )
        trend = self.indicator(contract, "creche")["trajectory"]
        maintenance = self.indicator(contract, "basico_integral")["trajectory"]
        self.assertEqual(trend["scenarioType"], "trend_projection")
        self.assertEqual(trend["projectedValue"], 51.0)
        self.assertEqual(maintenance["scenarioType"], "component_maintenance")
        self.assertEqual(maintenance["projectedValue"], 20.0)
        self.assertEqual(trend["uncertainty"]["status"], "not_estimated")
        self.assertEqual(maintenance["uncertainty"]["status"], "not_estimated")
        self.assertEqual(
            trend["denominatorModel"]["method"],
            "municipal_base_scaled_by_rs_age_group_change",
        )
        self.assertEqual(
            maintenance["trendModel"]["selectedBasis"],
            "latest_observed_components_held_constant",
        )

    def test_public_reading_distinguishes_municipal_and_state_trend(self):
        reading = _public_trajectory(
            {
                "targetComparisonStatus": "eligible",
                "trajectory": {
                    "status": "available",
                    "scenarioType": "trend_projection",
                    "quality": "media",
                    "observedFavorableAnnualPace": 0.5,
                    "historyPointCount": 5,
                    "projectedValue": 82.0,
                    "model": (
                        "municipal_state_shrunk_theil_sen_log_enrollment_"
                        "with_state_age_denominator"
                    ),
                    "trendModel": {
                        "selectedBasis": (
                            "municipal_state_shrunk_theil_sen_log"
                        ),
                        "diverges": False,
                    },
                },
            }
        )

        self.assertIn(
            "histórico de matrículas do município e do Rio Grande do Sul",
            reading["modelReading"],
        )
        self.assertNotIn("Holt", reading["modelReading"])
        self.assertNotIn("mantém o número", reading["modelReading"])

    def test_divergent_projection_does_not_publish_exact_achievement_year(self):
        contract = self.build(
            {"creche": result(40, 60, year=2025)},
            projections={
                "creche": {
                    "available": True,
                    "target_year": 2036,
                    "method": "attendance_projection",
                    "years": [2036],
                    "projected_percent_raw": [65.0],
                    "projected_2036_raw": 65.0,
                    "trend": {"diverges": True},
                    "quality": "media",
                    "warnings": [],
                }
            },
        )
        trajectory = self.indicator(contract, "creche")["trajectory"]
        self.assertIsNone(trajectory["estimatedAchievementYear"])
        self.assertIn(
            "attendance_projection_divergent_trends",
            trajectory["warningCodes"],
        )

    def test_next_official_milestone_is_selected(self):
        contract = self.build({"basico_integral": result(20, 50, year=2025)})
        trajectory = self.indicator(contract, "basico_integral")["trajectory"]
        self.assertEqual(trajectory["referenceStatus"], "official")
        self.assertEqual(trajectory["targetYear"], 2031)
        self.assertEqual(trajectory["targetValue"], 35.0)

    def test_governance_is_explicit_for_four_classes(self):
        contract = self.build(
            {
                "creche": result(40, 60),
                "basico_integral": result(20, 50),
                "basico_15_17": result(80, 85),
                "alfabetizacao_pop_15_mais": result(90, 100),
            }
        )
        expected = {
            "creche": "direct",
            "basico_integral": "shared",
            "basico_15_17": "state_led",
            "alfabetizacao_pop_15_mais": "territorial",
        }
        for indicator_id, classification in expected.items():
            self.assertEqual(
                self.indicator(contract, indicator_id)["governance"]["classification"],
                classification,
            )

    def test_exposure_is_available_only_when_dependency_components_reconcile(self):
        details = {
            "escolas_integral": {
                "series_components": [
                    {"ano": 2025, "numerador": 10, "denominador": 20}
                ],
                "series_dependencia_components": [
                    {
                        "ano": 2025,
                        "dependencia": "municipal",
                        "numerador": 8,
                        "denominador": 15,
                    },
                    {
                        "ano": 2025,
                        "dependencia": "estadual",
                        "numerador": 2,
                        "denominador": 5,
                    },
                ],
            }
        }
        contract = self.build(
            {
                "escolas_integral": result(50, 50, year=2025),
                "creche": result(40, 60, year=2025),
            },
            indicator_details=details,
        )
        available = self.indicator(contract, "escolas_integral")["municipalExposure"]
        unavailable = self.indicator(contract, "creche")["municipalExposure"]
        self.assertEqual(available["status"], "available")
        self.assertEqual(available["municipalNumeratorShare"], 80.0)
        self.assertEqual(available["municipalDenominatorShare"], 75.0)
        self.assertEqual(unavailable["status"], "unavailable")
        self.assertIsNone(unavailable["municipalNumeratorShare"])

    def build_peer_contract(self, municipality_count):
        municipal_results = {
            f"M{index}": {"creche": result(30 + index / 10, 60, year=2025)}
            for index in range(municipality_count)
        }
        municipal_details = {
            f"M{index}": {
                "creche": {
                    "series_components_by_cycle": {
                        "pne_2026_2036": [
                            {"ano": 2025, "numerador": 30 + index, "denominador": 100 + index}
                        ]
                    }
                }
            }
            for index in range(municipality_count)
        }
        registry = build_state_benchmark_registry(
            state_reference={
                "municipalities_expected": municipality_count,
                "indicators": {"creche": state_indicator("creche", 40)},
            },
            municipal_results=municipal_results,
            municipal_details=municipal_details,
            catalog=self.catalog,
        )
        return self.build(
            municipal_results["M0"],
            benchmark_registry=registry,
            indicator_details=municipal_details["M0"],
        )

    def test_peer_cohort_has_20_members_percentile_and_documented_relaxation(self):
        peers = self.indicator(self.build_peer_contract(25), "creche")[
            "similarMunicipalities"
        ]
        self.assertEqual(peers["status"], "available")
        self.assertGreaterEqual(peers["cohortSize"], 20)
        self.assertLessEqual(peers["cohortSize"], 50)
        self.assertIsNotNone(peers["performancePercentile"])
        self.assertEqual(peers["featuresUsed"], ["offering_size"])
        self.assertIn(
            "demographic_features_unavailable_use_offering_size_only",
            peers["relaxationCodes"],
        )

    def test_peer_cohort_is_absent_below_20_compatible_municipalities(self):
        peers = self.indicator(self.build_peer_contract(12), "creche")[
            "similarMunicipalities"
        ]
        self.assertEqual(peers["status"], "unavailable")
        self.assertEqual(peers["reasonCode"], "fewer_than_20_compatible_municipalities")
        self.assertEqual(peers["members"], [])

    def test_decision_classification_is_descriptive_and_does_not_publish_score(self):
        creche = result(40, 60, year=2025)
        creche["trend"] = {"slope": -1.0, "observations": 4, "method": "theil_sen_v1"}
        contract = self.build({"creche": creche})
        indicator = self.indicator(contract, "creche")
        self.assertEqual(
            indicator["decisionReading"]["classification"], "municipal_direct_action"
        )
        self.assertLessEqual(len(indicator["decisionReading"]["reasonCodes"]), 3)
        self.assertFalse(indicator["decisionReading"]["financialEligibilityVerified"])
        self.assertFalse(indicator["decisionReading"]["changesAttentionOrder"])
        self.assertIsNone(indicator["priorityScore"])


class DecisionSummaryP3CTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = load_indicator_catalog()

    def build(self, results, **kwargs):
        return build_municipal_diagnostic_v2(
            municipality_name="M0",
            municipality_id="4300000",
            results=results,
            generated_at=GENERATED_AT,
            catalog=self.catalog,
            **kwargs,
        )

    @staticmethod
    def ready_result(value, target, *, direction="at_least", slope=-1.0):
        payload = result(value, target, direction=direction, year=2025)
        payload["trend"] = {
            "slope": slope,
            "observations": 4,
            "method": "theil_sen_v1",
        }
        return payload

    @staticmethod
    def indicator(contract, indicator_id):
        return next(
            item for item in contract["indicators"] if item["indicatorId"] == indicator_id
        )

    def test_insufficient_evidence_is_investigation_without_ordinal_position(self):
        contract = self.build({"aee": result(40, 100, year=2025)})
        investigation = contract["decisionSummary"]["investigationItems"]
        reference = next(item for item in investigation if item["indicatorId"] == "aee")
        self.assertNotIn("selectionPosition", reference)
        self.assertEqual(self.indicator(contract, "aee")["evidenceLevel"], "insufficient")
        self.assertNotIn(
            "aee",
            {item["indicatorId"] for item in contract["decisionSummary"]["municipalActionItems"]},
        )

    def test_attained_reference_is_preserved_only_with_high_evidence(self):
        common = {
            "comparison_status": "eligible",
            "goal_attained": True,
            "trajectory": {"paceStatus": "target_already_met"},
            "governance": {"classification": "direct"},
            "exposure": {"status": "available"},
        }
        monitored = _build_decision_reading(
            **common,
            evidence={"level": "medium", "reasonCodes": []},
        )
        preserved = _build_decision_reading(
            **common,
            evidence={"level": "high", "reasonCodes": []},
        )
        self.assertEqual(monitored["classification"], "monitor")
        self.assertEqual(monitored["summaryCollection"], "monitoring")
        self.assertIn(
            "quantitative_reference_attained_with_caveats",
            monitored["reasonCodes"],
        )
        self.assertEqual(preserved["classification"], "preserve_result")
        self.assertEqual(preserved["summaryCollection"], "preservation")

    def test_state_and_territorial_indicators_are_never_municipal_direct_action(self):
        contract = self.build(
            {
                "idade_regular_medio": self.ready_result(70, 100),
                "alfabetizacao_pop_15_mais": self.ready_result(90, 97),
            }
        )
        for indicator_id in ("idade_regular_medio", "alfabetizacao_pop_15_mais"):
            indicator = self.indicator(contract, indicator_id)
            self.assertNotEqual(
                indicator["decisionReading"]["classification"],
                "municipal_direct_action",
            )
            self.assertNotEqual(
                indicator["decisionReading"]["summaryCollection"],
                "municipal_action",
            )

    def test_direct_action_and_shared_coordination_are_selected_with_sufficient_evidence(self):
        contract = self.build(
            {
                "creche": self.ready_result(40, 60),
                "basico_integral": self.ready_result(20, 35),
            }
        )
        self.assertIn(
            "creche",
            {item["indicatorId"] for item in contract["decisionSummary"]["municipalActionItems"]},
        )
        self.assertIn(
            "basico_integral",
            {item["indicatorId"] for item in contract["decisionSummary"]["coordinationItems"]},
        )

    def test_collection_limits_uniqueness_determinism_and_null_priority(self):
        results = {
            "creche": self.ready_result(25, 60),
            "pre_escola": self.ready_result(70, 100),
            "basico_integral": self.ready_result(20, 35),
            "escolas_integral": self.ready_result(20, 50),
            "adequacao_ai": self.ready_result(60, 100),
            "adequacao_af": self.ready_result(55, 100),
            "idade_regular_medio": self.ready_result(60, 100),
        }
        first = self.build(results)
        second = self.build(results)
        first_summary = first["decisionSummary"]
        self.assertEqual(first_summary, second["decisionSummary"])
        self.assertLessEqual(len(first_summary["municipalActionItems"]), 3)
        self.assertLessEqual(len(first_summary["coordinationItems"]), 2)
        all_ids = [
            item["indicatorId"]
            for key in (
                "municipalActionItems",
                "coordinationItems",
                "investigationItems",
                "monitoringItems",
                "preservationItems",
            )
            for item in first_summary[key]
        ]
        self.assertEqual(len(all_ids), len(set(all_ids)))
        self.assertTrue(all(item["priorityScore"] is None for item in first["indicators"]))

    def test_at_most_direction_uses_unfavorable_pace_without_converting_absence_to_zero(self):
        temporarios = self.ready_result(40, 30, direction="at_most", slope=2.0)
        contract = self.build({"temporarios": temporarios})
        indicator = self.indicator(contract, "temporarios")
        self.assertEqual(indicator["trajectory"]["paceStatus"], "moving_away")
        self.assertEqual(indicator["direction"], "at_most")
        missing = self.indicator(contract, "creche")
        self.assertIsNone(missing["rawValue"])
        self.assertIsNone(missing["displayValue"])


if __name__ == "__main__":
    unittest.main()
