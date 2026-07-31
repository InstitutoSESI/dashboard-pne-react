import math
import sys
import unittest
from pathlib import Path


DATA_PIPELINE_DIR = Path(__file__).resolve().parents[1]
if str(DATA_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_PIPELINE_DIR))

from src.pne_trend import attach_trend, calculate_trend  # noqa: E402


def point(year, value, **extra):
    return {"ano": year, "valor": value, **extra}


class PneTrendTests(unittest.TestCase):
    def test_classifies_up_stable_down_and_keeps_a_real_zero(self):
        up = calculate_trend(
            [point(year, value) for year, value in zip(range(2021, 2026), [10, 12, 14, 16, 18])],
            2025,
        )
        stable = calculate_trend(
            [point(year, value) for year, value in zip(range(2021, 2026), [10, 10.1, 10.2, 10.3, 10.4])],
            2025,
        )
        down = calculate_trend(
            [point(year, value) for year, value in zip(range(2021, 2026), [18, 16, 14, 12, 10])],
            2025,
        )
        zero = calculate_trend(
            [point(year, value) for year, value in zip(range(2021, 2026), [0, 1, 2, 3, 4])],
            2025,
        )

        self.assertEqual(up["status"], "up")
        self.assertEqual(up["label"], "Alta")
        self.assertEqual(up["observations"], 5)
        self.assertEqual(up["start_year"], 2021)
        self.assertEqual(up["end_year"], 2025)
        self.assertEqual(up["method"], "theil_sen_v1")
        self.assertAlmostEqual(up["slope"], 2)
        self.assertAlmostEqual(up["threshold"], 0.5)
        self.assertAlmostEqual(up["consistency"], 1)
        self.assertEqual(stable["status"], "stable")
        self.assertEqual(stable["label"], "Estável")
        self.assertEqual(down["status"], "down")
        self.assertEqual(zero["status"], "up")
        self.assertEqual(zero["observations"], 5)

    def test_oscillation_is_inconclusive_instead_of_stable(self):
        result = calculate_trend(
            [point(year, value) for year, value in zip(range(2021, 2026), [10, 20, 10, 20, 10])],
            2025,
        )

        self.assertEqual(result["status"], "inconclusive")
        self.assertIsNone(result["label"])

    def test_window_follows_card_year_automatically(self):
        series = [point(year, year - 2010) for year in range(2018, 2026)]

        result_2025 = calculate_trend(series, 2025)
        result_2027 = calculate_trend(
            [point(year, year - 2010) for year in range(2020, 2028)],
            2027,
        )

        self.assertEqual((result_2025["start_year"], result_2025["end_year"]), (2021, 2025))
        self.assertEqual((result_2027["start_year"], result_2027["end_year"]), (2023, 2027))

    def test_three_observations_are_allowed_only_when_consecutive(self):
        consecutive = calculate_trend(
            [point(2023, 1), point(2024, 2), point(2025, 3)],
            2025,
        )
        nonconsecutive = calculate_trend(
            [point(2021, 1), point(2023, 2), point(2025, 3)],
            2025,
        )

        self.assertEqual(consecutive["status"], "up")
        self.assertEqual(consecutive["observations"], 3)
        self.assertEqual(nonconsecutive["status"], "unavailable")
        self.assertEqual(
            nonconsecutive["unavailable_reason"],
            "three_observations_not_frequency_compatible",
        )

    def test_invalid_values_are_not_interpolated_or_zero_filled(self):
        invalid_history = calculate_trend(
            [
                point(2021, 0),
                point(2022, None),
                point(2023, ""),
                point(2024, math.nan),
                point(2025, 4),
            ],
            2025,
        )

        self.assertEqual(invalid_history["status"], "unavailable")
        self.assertEqual(invalid_history["observations"], 2)

    def test_empty_history_is_unavailable(self):
        result = calculate_trend([], 2025)

        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(result["unavailable_reason"], "missing_history")

    def test_percent_threshold_is_versioned_and_uses_mad(self):
        result = calculate_trend(
            [point(year, value) for year, value in zip(range(2021, 2026), [0, 4, 8, 16, 24])],
            2025,
            value_type="percent",
        )

        self.assertAlmostEqual(result["threshold"], 1)
        self.assertEqual(result["threshold_method"], "percent_tau_mad_v1")

    def test_methodology_break_makes_history_unavailable(self):
        result = calculate_trend(
            [
                point(2021, 1),
                point(2022, 2),
                point(2023, 3, metodologia_break=True),
                point(2024, 4),
                point(2025, 5),
            ],
            2025,
        )

        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(result["unavailable_reason"], "methodology_break")

    def test_biennial_and_census_series_are_unavailable(self):
        biennial = calculate_trend(
            [point(2021, 1), point(2023, 2), point(2025, 3)],
            2025,
        )
        declared_biennial = calculate_trend(
            [point(2021, 1), point(2023, 2), point(2025, 3)],
            2025,
            observation_interval_years=2,
        )
        census = calculate_trend(
            [point(2010, 1), point(2022, 2)],
            2022,
            observation_interval_years=12,
        )

        self.assertEqual(biennial["status"], "unavailable")
        self.assertNotEqual(declared_biennial["status"], "unavailable")
        self.assertEqual(declared_biennial["observations"], 3)
        self.assertEqual(census["status"], "unavailable")

    def test_trend_must_end_at_the_card_year(self):
        result = calculate_trend(
            [point(2021, 1), point(2022, 2), point(2023, 3), point(2024, 4)],
            2025,
        )

        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(result["unavailable_reason"], "history_does_not_end_at_card_year")

    def test_at_most_does_not_invert_the_arrow_direction(self):
        result = attach_trend(
            {
                "available": True,
                "end_year": 2025,
                "direction": "at_most",
                "series": [point(year, value) for year, value in zip(range(2021, 2026), [10, 12, 14, 16, 18])],
            }
        )

        self.assertEqual(result["trend"]["status"], "up")

    def test_trend_is_computable_without_state_reference(self):
        result = attach_trend(
            {
                "available": True,
                "end_year": 2025,
                "series": [point(year, value) for year, value in zip(range(2021, 2026), [10, 12, 14, 16, 18])],
            }
        )

        self.assertEqual(result["trend"]["status"], "up")
        self.assertNotIn("state_reference", result)


if __name__ == "__main__":
    unittest.main()
