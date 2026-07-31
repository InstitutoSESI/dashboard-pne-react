from __future__ import annotations

import unittest

from data_pipeline.src.municipal_diagnostic import (
    PNE_2026_CYCLE_ID,
    build_municipal_diagnostic_v2,
)
from data_pipeline.src.pne.diagnostic_presentation_policy import (
    FORBIDDEN_FIELDS,
    POLICY,
    validate_policy,
)
from data_pipeline.src.pne.goal_indicator_contract import CONTRACT


def _result(value: float, *, meta: float, direction: str) -> dict:
    return {
        "available": True,
        "end_value": value,
        "end_year": 2030,
        "meta": meta,
        "meta_label": "Referência municipal divergente",
        "direction": direction,
        "atingida": True,
        "distance": 999,
        "series": [
            {"ano": 2028, "valor": value - 2},
            {"ano": 2029, "valor": value - 1},
            {"ano": 2030, "valor": value},
        ],
        "trend": {"slope": 1, "observations": 3},
    }


class Pne2026DiagnosticContractMigrationTest(unittest.TestCase):
    def test_policy_is_editorial_and_complete(self):
        self.assertIs(validate_policy(POLICY), POLICY)
        self.assertEqual(len(POLICY["relations"]), 51)
        for entry in POLICY["relations"]:
            self.assertFalse(set(entry) & FORBIDDEN_FIELDS)
            relation = next(
                relation
                for relation in CONTRACT["relations"]
                if relation["relationId"] == entry["relationId"]
            )
            self.assertTrue(relation["includeInDiagnostic"])
            self.assertNotEqual(relation["mode"], "hidden")

    def test_2026_contract_overrides_municipal_methodology_and_caps_complementary(self):
        contract = build_municipal_diagnostic_v2(
            municipality_name="Teste",
            generated_at="2026-07-28T00:00:00-03:00",
            cycle_id=PNE_2026_CYCLE_ID,
            results={
                "creche": _result(50, meta=999, direction="at_most"),
                "temporarios": _result(20, meta=999, direction="at_least"),
                "rendimento_magisterio": _result(
                    120, meta=1, direction="at_most"
                ),
            },
            projections={
                "temporarios": {
                    "available": True,
                    "years": [2031],
                    "projected_percent_raw": [10],
                }
            },
        )
        indicators = {
            indicator["indicatorId"]: indicator
            for indicator in contract["indicators"]
        }

        creche = indicators["creche"]
        self.assertEqual(creche["configuredReference"]["value"], 60)
        self.assertEqual(creche["configuredReference"]["year"], 2036)
        self.assertEqual(creche["direction"], "at_least")
        self.assertFalse(creche["goalAttained"])
        self.assertEqual(
            creche["methodology"]["formulaId"], "formula.creche"
        )

        complementary = indicators["temporarios"]
        self.assertEqual(complementary["direction"], "at_most")
        self.assertIsNone(complementary["configuredReference"]["value"])
        self.assertIsNone(complementary["goalAttained"])
        self.assertIsNone(complementary["remainingGap"])
        self.assertEqual(
            complementary["targetComparisonStatus"], "not_applicable"
        )
        self.assertEqual(
            complementary["trajectory"]["scenarioType"], "historical_trend_only"
        )
        self.assertIsNone(
            complementary["trajectory"]["estimatedAchievementYear"]
        )

        hidden = indicators["rendimento_magisterio"]
        self.assertIsNone(hidden["goalAttained"])
        public_ids = {
            result["indicatorId"]
            for goal in contract["pne2026PublicDiagnostic"]["goals"]
            for result in goal["results"]
        }
        self.assertNotIn("temporarios", public_ids)
        self.assertNotIn("rendimento_magisterio", public_ids)

    def test_previous_cycle_keeps_legacy_resolution(self):
        legacy = build_municipal_diagnostic_v2(
            municipality_name="Teste",
            generated_at="2026-07-28T00:00:00-03:00",
            cycle_id="pne_2014_2024",
            results={
                "temporarios": _result(20, meta=30, direction="at_most"),
            },
        )
        indicator = next(
            item
            for item in legacy["indicators"]
            if item["indicatorId"] == "temporarios"
        )
        self.assertTrue(indicator["goalAttained"])
        self.assertEqual(indicator["configuredReference"]["value"], 30)
        self.assertEqual(
            legacy["generationMetadata"]["cycleContract"], "legacy-isolated"
        )


if __name__ == "__main__":
    unittest.main()
