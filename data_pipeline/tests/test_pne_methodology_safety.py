import sys
import unittest
from pathlib import Path


DATA_PIPELINE_DIR = Path(__file__).resolve().parents[1]
if str(DATA_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_PIPELINE_DIR))

from src.pne.common import _goal_achieved  # noqa: E402
from src.pne_2026_projections import (  # noqa: E402
    STATE_DAMPED_HOLT_NUMERATOR_MODEL,
    project_numerator,
)


class PneMethodologySafetyTests(unittest.TestCase):
    def test_goal_achievement_uses_raw_value_not_rounded_display(self):
        self.assertFalse(_goal_achieved(-0.04))
        self.assertTrue(_goal_achieved(0.04))
        self.assertTrue(_goal_achieved(0.0))

    def test_projection_requires_five_consecutive_observations(self):
        one = project_numerator([{"ano": 2025, "valor": 100}])
        four = project_numerator(
            [
                {"ano": 2022, "valor": 70},
                {"ano": 2023, "valor": 80},
                {"ano": 2024, "valor": 90},
                {"ano": 2025, "valor": 100},
            ]
        )
        five = project_numerator(
            [
                {"ano": 2021, "valor": 60},
                {"ano": 2022, "valor": 70},
                {"ano": 2023, "valor": 80},
                {"ano": 2024, "valor": 90},
                {"ano": 2025, "valor": 100},
            ]
        )

        self.assertFalse(one["available"])
        self.assertFalse(four["available"])
        self.assertTrue(five["available"])
        self.assertEqual(
            {point["valor"] for point in five["projected"]},
            {100.0},
        )

    def test_projection_rejects_duplicate_year_and_methodology_break(self):
        duplicate = project_numerator([
            {"ano": 2024, "valor": 80},
            {"ano": 2025, "valor": 90},
            {"ano": 2025, "valor": 100},
        ])
        methodology_break = project_numerator([
            {"ano": 2023, "valor": 80},
            {"ano": 2024, "valor": 90, "methodology_break": True},
            {"ano": 2025, "valor": 100},
        ])
        irregular = project_numerator(
            [
                {"ano": 2020, "valor": 50},
                {"ano": 2021, "valor": 60},
                {"ano": 2022, "valor": 70},
                {"ano": 2023, "valor": 80},
                {"ano": 2025, "valor": 100},
            ]
        )

        self.assertFalse(duplicate["available"])
        self.assertFalse(methodology_break["available"])
        self.assertFalse(irregular["available"])

    def test_projection_exposes_selected_trend_and_divergence(self):
        projection = project_numerator(
            [
                {"ano": 2017, "valor": 0},
                {"ano": 2018, "valor": 10},
                {"ano": 2019, "valor": 20},
                {"ano": 2020, "valor": 30},
                {"ano": 2021, "valor": 40},
                {"ano": 2022, "valor": 50},
                {"ano": 2023, "valor": 45},
                {"ano": 2024, "valor": 40},
                {"ano": 2025, "valor": 35},
            ]
        )

        self.assertTrue(projection["available"])
        self.assertTrue(projection["trend"]["diverges"])
        self.assertEqual(projection["trend"]["observationCount"], 9)
        self.assertEqual(
            projection["trend"]["selectedBasis"],
            "last_observation_persistence",
        )
        self.assertEqual(
            {point["valor"] for point in projection["projected"]},
            {35.0},
        )
        self.assertTrue(
            any(
                "direcoes opostas" in warning
                for warning in projection["warnings"]
            )
        )

    def test_projection_rejects_stale_series_instead_of_skipping_years(self):
        projection = project_numerator(
            [
                {"ano": 2019, "valor": 60},
                {"ano": 2020, "valor": 70},
                {"ano": 2021, "valor": 80},
                {"ano": 2022, "valor": 90},
                {"ano": 2023, "valor": 100},
            ]
        )

        self.assertFalse(projection["available"])
        self.assertIn("Horizonte", projection["reason"])

    def test_projection_can_apply_backtested_state_enrollment_trend(self):
        local_series = [
            {"ano": year, "valor": value}
            for year, value in zip(
                range(2021, 2026),
                [90, 92, 95, 98, 100],
                strict=True,
            )
        ]
        state_series = [
            {"ano": year, "valor": value}
            for year, value in zip(
                range(2019, 2026),
                [900, 920, 950, 980, 1010, 1040, 1080],
                strict=True,
            )
        ]

        projection = project_numerator(
            local_series,
            model=STATE_DAMPED_HOLT_NUMERATOR_MODEL,
            state_series=state_series,
            model_parameters={
                "alpha": 0.4,
                "beta": 0.3,
                "damping": 0.9,
                "transform": "identity",
            },
        )

        self.assertTrue(projection["available"])
        self.assertEqual(
            projection["trend"]["selectedBasis"],
            "state_aggregate_damped_holt",
        )
        self.assertGreater(projection["projected"][0]["valor"], 100)
        self.assertEqual(
            projection["trend"]["aggregateModel"]["territory"],
            "Rio Grande do Sul",
        )


if __name__ == "__main__":
    unittest.main()
