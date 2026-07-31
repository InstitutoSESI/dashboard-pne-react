from __future__ import annotations

import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


class PneConsolidatedIndicatorRoundTests(unittest.TestCase):
    def test_child_literacy_snapshot_and_disclosure_boundary(self) -> None:
        from src.child_literacy import (
            EXPECTED_AVAILABLE,
            EXPECTED_RS_VALUES,
            load_snapshot,
            participation_is_eligible,
        )

        municipal, state, manifest = load_snapshot()
        self.assertEqual(len(municipal), 497)
        self.assertEqual(manifest["availableByYear"], {
            str(year): value for year, value in EXPECTED_AVAILABLE.items()
        })
        self.assertFalse(participation_is_eligible(69.99))
        self.assertTrue(participation_is_eligible(70.0))
        state_by_year = {int(row["year"]): row["value"] for row in state}
        self.assertEqual(state_by_year, EXPECTED_RS_VALUES)
        for year, expected in EXPECTED_AVAILABLE.items():
            observed = sum(
                point["dataStatus"] == "available"
                for row in municipal
                for point in row["series"]
                if int(point["year"]) == year
            )
            self.assertEqual(observed, expected)

    def test_goal_11d_preserves_zeros_and_reconciles_state(self) -> None:
        from src.pne_goal_11d import (
            EXPECTED_RS_VALUES,
            EXPECTED_ZERO_NUMERATORS,
            load_snapshot,
        )

        municipal, state, manifest = load_snapshot()
        self.assertEqual(len(municipal), 497)
        for year, expected in EXPECTED_ZERO_NUMERATORS.items():
            points = [
                point
                for row in municipal
                for point in row["series"]
                if int(point["year"]) == year
            ]
            self.assertEqual(sum(point["numerator"] == 0 for point in points), expected)
            self.assertTrue(all(point["dataStatus"] == "available" for point in points))
        state_by_year = {int(row["year"]): row["value"] for row in state}
        for year, expected in EXPECTED_RS_VALUES.items():
            self.assertAlmostEqual(state_by_year[year], expected, places=12)
        self.assertEqual(
            manifest["territorialBasis"]["numerator"],
            "municipality_of_school",
        )

    def test_goal_14_uses_exact_census_categories_and_ratio_of_sums(self) -> None:
        from src.pne_goal_14_census import load_snapshot

        municipal, state, manifest = load_snapshot()
        self.assertEqual(len(municipal), 497)
        self.assertEqual(set(manifest["tables"]), {"10058", "10059", "10061"})
        for row in municipal:
            self.assertEqual(set(row["indicators"]), {"14.a", "14.b", "14.d"})
            for result in row["indicators"].values():
                self.assertEqual(result["dataStatus"], "available")
                self.assertAlmostEqual(
                    result["value"],
                    100 * result["numerator"] / result["denominator"],
                    places=12,
                )
        for state_result in state:
            relation_id = state_result["relationId"]
            numerator = sum(
                row["indicators"][relation_id]["numerator"] for row in municipal
            )
            denominator = sum(
                row["indicators"][relation_id]["denominator"] for row in municipal
            )
            self.assertEqual(state_result["numerator"], numerator)
            self.assertEqual(state_result["denominator"], denominator)

    def test_goal_15b_is_decomposed_and_numerator_never_exceeds_denominator(self) -> None:
        from src.pne_goal_15b import RELATION_IDS, load_snapshot

        municipal, state, manifest = load_snapshot()
        self.assertEqual(len(municipal), 497)
        self.assertEqual(
            set(RELATION_IDS),
            {
                "15.b.total",
                "15.b.universidades",
                "15.b.centros_universitarios",
                "15.b.faculdades",
            },
        )
        for row in municipal:
            for point in row["series"]:
                for result in point["indicators"].values():
                    self.assertLessEqual(result["numerator"], result["denominator"])
        latest_total = next(
            row
            for row in state
            if row["year"] == 2024 and row["relationId"] == "15.b.total"
        )
        self.assertEqual(
            (latest_total["numerator"], latest_total["denominator"]),
            (13755, 22295),
        )
        self.assertIn("acompanhamento", manifest["organizationRecutPolicy"])

    def test_contract_cardinality_modes_and_preserved_blocks(self) -> None:
        contract = json.loads(
            (REPO_ROOT / "contracts" / "pne2026-goal-indicator-contract.json")
            .read_text(encoding="utf-8")
        )
        relations = {row["relationId"]: row for row in contract["relations"]}
        self.assertEqual(contract["contractVersion"], "1.9.0")
        self.assertEqual(len(contract["relations"]), 59)
        self.assertEqual(
            {
                mode: sum(row["mode"] == mode for row in contract["relations"])
                for mode in ("progress", "tracking", "complementary", "hidden")
            },
            {
                "progress": 27,
                "tracking": 15,
                "complementary": 15,
                "hidden": 2,
            },
        )
        self.assertEqual(relations["relation.7.a.internet"]["mode"], "complementary")
        self.assertFalse(relations["relation.7.a.internet"]["includeInDiagnostic"])
        self.assertEqual(relations["relation.17.d.temporarios"]["mode"], "complementary")
        self.assertFalse(relations["relation.17.d.temporarios"]["canProjection"])
        self.assertEqual(relations["relation.3.a.alfabetizacao"]["mode"], "progress")
        self.assertEqual(
            relations["relation.14.a.graduacao_frequencia_18_24"]["mode"],
            "tracking",
        )

    def test_literacy_query_does_not_average_or_select_public_network(self) -> None:
        sql = (
            REPO_ROOT / "data_pipeline" / "queries" / "taxa_alfabetizacao.sql"
        ).read_text(encoding="utf-8").casefold()
        self.assertNotIn("avg(", sql)
        self.assertIn("= 'municipal'", sql)
        self.assertIn("count(*) over", sql)


if __name__ == "__main__":
    unittest.main()
