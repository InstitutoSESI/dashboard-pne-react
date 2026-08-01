import copy
import sys
import unittest
from pathlib import Path


DATA_PIPELINE_DIR = Path(__file__).resolve().parents[1]
if str(DATA_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_PIPELINE_DIR))

from src.municipal_inequality import (  # noqa: E402
    build_document,
    build_urban_rural_integral_pilot,
)


def row(location, numerator, denominator, year=2025):
    return {
        "ano": year,
        "dependencia": "publica",
        "localizacao": location,
        "matriculas_integral": numerator,
        "matriculas": denominator,
    }


class MunicipalInequalityPilotTest(unittest.TestCase):
    def test_available_groups_use_same_year_universe_and_formula(self):
        pilot = build_urban_rural_integral_pilot(
            [row("urbana", 25, 100), row("rural", 30, 100)]
        )
        self.assertEqual(pilot["status"], "available")
        self.assertEqual(pilot["methodologyVersion"], "municipal-inequality-p4b-v1")
        self.assertEqual(pilot["indicatorId"], "basico_integral")
        self.assertEqual(pilot["dimension"], "urban_rural")
        self.assertEqual(pilot["year"], 2025)
        self.assertEqual(pilot["universeCode"], "public_basic_education_enrollments")
        self.assertEqual(
            pilot["formulaCode"],
            "integral_enrollments_over_eligible_enrollments",
        )
        self.assertEqual(pilot["observedDifferencePercentagePoints"], -5.0)
        self.assertEqual(
            [group["status"] for group in pilot["groups"]],
            ["available", "available"],
        )
        self.assertEqual(
            [group["percentage"] for group in pilot["groups"]],
            [25.0, 30.0],
        )

    def test_latest_year_is_used_without_combining_periods(self):
        pilot = build_urban_rural_integral_pilot(
            [
                row("urbana", 20, 100, 2024),
                row("rural", 20, 100, 2024),
                row("urbana", 30, 100, 2025),
                row("rural", 40, 100, 2025),
            ]
        )
        self.assertEqual(pilot["year"], 2025)
        self.assertEqual(
            [group["year"] for group in pilot["groups"]],
            [2025, 2025],
        )

    def test_small_cell_and_complementary_group_are_both_suppressed(self):
        pilot = build_urban_rural_integral_pilot(
            [row("urbana", 25, 100), row("rural", 2, 8)]
        )
        self.assertEqual(pilot["status"], "suppressed_small_cell")
        self.assertIsNone(pilot["observedDifferencePercentagePoints"])
        self.assertEqual(
            {group["suppressionReasonCode"] for group in pilot["groups"]},
            {"small_cell", "complementary_suppression"},
        )
        for group in pilot["groups"]:
            self.assertEqual(group["status"], "suppressed_small_cell")
            self.assertIsNone(group["numerator"])
            self.assertIsNone(group["denominator"])
            self.assertIsNone(group["percentage"])

    def test_small_numerator_is_suppressed_as_identification_risk(self):
        pilot = build_urban_rural_integral_pilot(
            [row("urbana", 25, 100), row("rural", 5, 100)]
        )
        self.assertTrue(
            all(group["status"] == "suppressed_small_cell" for group in pilot["groups"])
        )

    def test_missing_is_null_and_never_becomes_zero(self):
        pilot = build_urban_rural_integral_pilot([row("urbana", 25, 100)])
        rural = next(group for group in pilot["groups"] if group["groupCode"] == "rural")
        self.assertEqual(rural["status"], "missing")
        self.assertIsNone(rural["numerator"])
        self.assertIsNone(rural["denominator"])
        self.assertIsNone(rural["percentage"])
        self.assertIsNone(pilot["observedDifferencePercentagePoints"])

    def test_explicit_zero_offer_is_not_applicable_not_missing(self):
        pilot = build_urban_rural_integral_pilot(
            [row("urbana", 25, 100), row("rural", 0, 0)]
        )
        rural = next(group for group in pilot["groups"] if group["groupCode"] == "rural")
        self.assertEqual(rural["status"], "not_applicable")
        self.assertEqual(rural["numerator"], 0)
        self.assertEqual(rural["denominator"], 0)
        self.assertIsNone(rural["percentage"])

    def test_invalid_formula_components_are_not_published(self):
        pilot = build_urban_rural_integral_pilot(
            [row("urbana", 101, 100), row("rural", 20, 100)]
        )
        urban = next(group for group in pilot["groups"] if group["groupCode"] == "urban")
        self.assertEqual(pilot["status"], "methodology_incompatible")
        self.assertEqual(urban["status"], "methodology_incompatible")
        self.assertIsNone(urban["percentage"])

    def test_generation_is_deterministic(self):
        rows = [row("rural", 30, 100), row("urbana", 25, 100)]
        self.assertEqual(
            build_urban_rural_integral_pilot(copy.deepcopy(rows)),
            build_urban_rural_integral_pilot(copy.deepcopy(rows)),
        )

    def test_compact_document_can_preserve_the_published_pilot(self):
        pilot = build_urban_rural_integral_pilot(
            [row("urbana", 25, 100), row("rural", 30, 100)]
        )
        document = build_document(
            municipality_id="4300034",
            municipality_name="Aceguá",
            generated_at="2026-07-19T23:50:16-03:00",
            inequality_pilot=pilot,
        )
        pilot["status"] = "changed-after-build"
        self.assertEqual(document["schemaVersion"], "municipal-inequality-v1")
        self.assertEqual(document["municipality"]["id"], "4300034")
        self.assertEqual(document["inequalityPilot"]["status"], "available")

    def test_document_rejects_rows_and_precomputed_pilot_together(self):
        pilot = build_urban_rural_integral_pilot(
            [row("urbana", 25, 100), row("rural", 30, 100)]
        )
        with self.assertRaisesRegex(ValueError, "nunca ambos"):
            build_document(
                municipality_id="4300034",
                municipality_name="Aceguá",
                generated_at="2026-07-19T23:50:16-03:00",
                rows=[],
                inequality_pilot=pilot,
            )

if __name__ == "__main__":
    unittest.main()
