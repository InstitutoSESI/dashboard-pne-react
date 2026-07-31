from __future__ import annotations

import unittest

from data_pipeline.scripts.materialize_pne2026_public_diagnostic_v3 import (
    _status_payload,
    prepare_staging,
)
from data_pipeline.src.pne.goal_indicator_contract import CONTRACT
from data_pipeline.src.pne.diagnostic_presentation_policy import POLICY
from data_pipeline.src.pne_goal_11b_census import (
    COMPLETED_EDUCATION_KEYS,
    age_in_scope,
    education_level_counts_as_complete,
    load_snapshot,
    ratio_result,
    state_ratio,
)


class PneGoal11bCensusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows, cls.manifest = load_snapshot()

    def test_age_boundaries(self):
        self.assertFalse(age_in_scope(14, "15_29"))
        self.assertTrue(age_in_scope(15, "15_29"))
        self.assertTrue(age_in_scope(17, "15_29"))
        self.assertTrue(age_in_scope(18, "15_29"))
        self.assertTrue(age_in_scope(29, "15_29"))
        self.assertFalse(age_in_scope(30, "15_29"))
        self.assertTrue(age_in_scope(30, "15_plus"))

    def test_education_categories(self):
        for level in COMPLETED_EDUCATION_KEYS:
            self.assertTrue(education_level_counts_as_complete(level), level)
        for level in (
            "below_fundamental",
            "indeterminate",
            "non_response",
        ):
            self.assertFalse(education_level_counts_as_complete(level), level)

    def test_missing_zero_and_suppression_semantics(self):
        self.assertEqual(
            ratio_result(
                {
                    "status": "available",
                    "numerator": 0,
                    "denominator": 10,
                }
            )["value"],
            0,
        )
        self.assertEqual(
            ratio_result(
                {
                    "status": "available",
                    "numerator": 0,
                    "denominator": 0,
                }
            )["dataStatus"],
            "not_applicable",
        )
        self.assertEqual(
            ratio_result(
                {
                    "status": "available",
                    "numerator": 1,
                    "denominator": None,
                }
            )["dataStatus"],
            "unavailable",
        )
        self.assertEqual(
            ratio_result(
                {
                    "status": "suppressed",
                    "numerator": None,
                    "denominator": None,
                }
            )["dataStatus"],
            "suppressed",
        )

    def test_snapshot_has_497_reconciled_municipalities_and_only_2022(self):
        self.assertEqual(len(self.rows), 497)
        self.assertEqual({row["year"] for row in self.rows}, {2022})
        self.assertEqual(
            self.manifest["reconciliation"][
                "fifteenToTwentyNineNumeratorDifferences"
            ],
            0,
        )
        self.assertEqual(
            self.manifest["reconciliation"]["eighteenPlusNumeratorDifferences"],
            0,
        )
        self.assertTrue(
            all(
                row["fifteenToTwentyNine"]["status"] == "available"
                and row["fifteenPlus"]["status"] == "available"
                for row in self.rows
            )
        )

    def test_state_reference_is_ratio_of_sums(self):
        for component in ("fifteenToTwentyNine", "fifteenPlus"):
            observed = state_ratio(self.rows, component)
            numerator = sum(
                row[component]["numerator"] for row in self.rows
            )
            denominator = sum(
                row[component]["denominator"] for row in self.rows
            )
            self.assertEqual(observed["numerator"], numerator)
            self.assertEqual(observed["denominator"], denominator)
            self.assertAlmostEqual(
                observed["value"],
                100 * numerator / denominator,
                places=12,
            )

    def test_status_uses_unrounded_value(self):
        import pandas as pd

        below = _status_payload(
            pd.Series(
                {
                    "ano": 2022,
                    "data_status": "available",
                    "valor": 84.999999,
                    "numerador": 1,
                    "denominador": 1,
                }
            ),
            target=85.0,
            public_reading="",
        )
        above = _status_payload(
            pd.Series(
                {
                    "ano": 2022,
                    "data_status": "available",
                    "valor": 85.000001,
                    "numerador": 1,
                    "denominador": 1,
                }
            ),
            target=85.0,
            public_reading="",
        )
        self.assertEqual(below["classification"], "advance")
        self.assertEqual(above["classification"], "maintain")

    def test_public_contract_has_two_cards_without_18_plus_or_projection(self):
        public = [
            relation
            for relation in CONTRACT["relations"]
            if relation["goalId"] == "11.b"
            and relation["includeInDiagnostic"]
        ]
        self.assertEqual(
            [relation["indicatorId"] for relation in public],
            [
                "fundamental_concluido_15_mais",
                "fundamental_concluido_15_29",
            ],
        )
        self.assertTrue(all(not relation["canProjection"] for relation in public))
        hidden_18 = next(
            relation
            for relation in CONTRACT["relations"]
            if relation["relationId"]
            == "relation.11.b.fundamental_concluido_18_mais"
        )
        self.assertEqual(hidden_18["mode"], "hidden")
        self.assertFalse(hidden_18["includeInCycleGoalRefs"])
        policy_ids = {entry["relationId"] for entry in POLICY["relations"]}
        self.assertNotIn(hidden_18["relationId"], policy_ids)
        self.assertTrue(
            {relation["relationId"] for relation in public} <= policy_ids
        )

    def test_materialization_has_two_11b_results_without_trend(self):
        prepared = prepare_staging()
        for payload in prepared["payloads"]:
            results = [
                result
                for result in payload["results"]
                if result["goalId"] == "11.b"
            ]
            self.assertEqual(len(results), 2)
            self.assertEqual(
                {result["indicatorId"] for result in results},
                {
                    "fundamental_concluido_15_mais",
                    "fundamental_concluido_15_29",
                },
            )
            self.assertTrue(
                all(
                    "trend" not in result and "projection" not in result
                    for result in results
                )
            )


if __name__ == "__main__":
    unittest.main()
