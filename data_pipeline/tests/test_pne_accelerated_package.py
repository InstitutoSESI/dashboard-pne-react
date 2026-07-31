from __future__ import annotations

import unittest

from data_pipeline.src.pne_accelerated_package import (
    AEE_RELATION_ID,
    HIGHER_FACULTY_EDUCATION_RELATION_ID,
    HIGHER_GRADUATES_RELATION_ID,
    INDIGENOUS_RELATION_ID,
    aee_school_offer_result,
    build_accelerated_package_results,
    higher_faculty_education_result,
    higher_graduates_result,
    indigenous_coverage_result,
)


def _aee_document(
    numerator=None,
    denominator=None,
    value=None,
    state="observed",
):
    return {
        "years": [
            {
                "year": 2025,
                "cuts": {
                    "total": {
                        "aee": {
                            "shareOfferingAee": {
                                "state": state,
                                "numerator": numerator,
                                "denominator": denominator,
                                "value": value,
                            }
                        }
                    }
                },
            }
        ]
    }


def _indigenous_document(
    *,
    numerator=3,
    denominator=2,
    percentage=150,
    population_status="available",
    population_year=2022,
    point_status="available",
):
    return {
        "blocos": {
            "educacao_indigena": {
                "coberturaEstimada": {
                    "population": {
                        "status": population_status,
                        "year": population_year,
                        "value": denominator,
                    },
                    "series": {
                        "2024": {
                            "status": "available",
                            "enrollments": {"alignedTotal": 1},
                            "percentage": 50,
                        },
                        "2025": {
                            "status": point_status,
                            "enrollments": {"alignedTotal": numerator},
                            "percentage": percentage,
                        },
                    },
                }
            }
        }
    }


def _faculty_breakdown(values, *, exhaustive=True, status="observed"):
    categories = [
        "Sem Graduação",
        "Graduação",
        "Especialização",
        "Mestrado",
        "Doutorado",
    ]
    return {
        "id": "faculty_education",
        "year": 2024,
        "status": status,
        "exhaustive": exhaustive,
        "categories": [
            {"id": category, "status": "observed", "value": value}
            for category, value in zip(categories, values, strict=True)
        ],
    }


class AcceleratedPnePackageTest(unittest.TestCase):
    def test_aee_offer_and_no_offer_use_school_counts(self):
        result = aee_school_offer_result(_aee_document(1, 2, 50))
        self.assertEqual(result["dataStatus"], "available")
        self.assertEqual(result["numerator"], 1)
        self.assertEqual(result["denominator"], 2)
        self.assertEqual(result["value"], 50)
        self.assertIn("oferta escolar", result["publicReading"])
        self.assertIn("não a proporção de estudantes", result["publicReading"])

        none_offering = aee_school_offer_result(_aee_document(0, 4, 0))
        self.assertEqual(none_offering["dataStatus"], "available")
        self.assertEqual(none_offering["value"], 0)

    def test_aee_zero_denominator_missing_and_invalid_components(self):
        self.assertEqual(
            aee_school_offer_result(_aee_document(0, 0, None)),
            {
                "dataStatus": "not_applicable",
                "reasonCode": "denominator_zero",
                "year": 2025,
                "value": None,
            },
        )
        self.assertEqual(
            aee_school_offer_result(_aee_document())["reasonCode"],
            "required_component_unavailable",
        )
        with self.assertRaisesRegex(ValueError, "incompatíveis"):
            aee_school_offer_result(_aee_document(3, 2, 150))

    def test_indigenous_small_denominator_preserves_above_100_and_warns(self):
        result = indigenous_coverage_result(_indigenous_document())
        self.assertEqual(result["year"], 2025)
        self.assertEqual(result["numerator"], 3)
        self.assertEqual(result["denominator"], 2)
        self.assertEqual(result["value"], 150)
        self.assertIn("acima de 100%", result["publicReading"])
        self.assertIn("residentes de 4 a 17 anos", result["publicReading"])

    def test_indigenous_warning_only_when_value_is_above_100(self):
        result = indigenous_coverage_result(
            _indigenous_document(numerator=0, denominator=5, percentage=0)
        )
        self.assertEqual(result["dataStatus"], "available")
        self.assertEqual(result["value"], 0)
        self.assertNotIn("acima de 100%", result["publicReading"])

    def test_indigenous_zero_or_missing_population_is_explicit(self):
        zero = indigenous_coverage_result(
            _indigenous_document(numerator=0, denominator=0, percentage=None)
        )
        self.assertEqual(zero["dataStatus"], "not_applicable")
        self.assertEqual(zero["reasonCode"], "denominator_zero")

        missing = indigenous_coverage_result(
            _indigenous_document(
                denominator=None,
                population_status="unavailable",
            )
        )
        self.assertEqual(missing["dataStatus"], "unavailable")
        self.assertEqual(
            missing["reasonCode"], "resident_population_unavailable"
        )

        wrong_year = indigenous_coverage_result(
            _indigenous_document(population_year=2021)
        )
        self.assertEqual(wrong_year["dataStatus"], "unavailable")

    def test_higher_graduates_distinguish_zero_from_absence(self):
        zero = higher_graduates_result(
            {
                "indicators": {
                    "esup-concluintes": {
                        "series": [
                            {"year": 2024, "status": "derived_zero", "value": 0}
                        ]
                    }
                }
            }
        )
        self.assertEqual(zero["dataStatus"], "available")
        self.assertEqual(zero["value"], 0)

        observed = higher_graduates_result(
            {
                "indicators": {
                    "esup-concluintes": {
                        "series": [
                            {"year": 2024, "status": "observed", "value": 12}
                        ]
                    }
                }
            }
        )
        self.assertEqual(observed["value"], 12)
        self.assertIn("não representa residentes", observed["publicReading"])

        absent = higher_graduates_result({"indicators": {}})
        self.assertEqual(absent["dataStatus"], "unavailable")
        self.assertEqual(absent["reasonCode"], "local_offer_unavailable")

    def test_higher_faculty_requires_exhaustive_breakdown(self):
        result = higher_faculty_education_result(
            {"breakdowns": [_faculty_breakdown([1, 2, 3, 4, 10])]}
        )
        self.assertEqual(result["dataStatus"], "available")
        self.assertEqual(result["numerator"], 14)
        self.assertEqual(result["denominator"], 20)
        self.assertEqual(result["value"], 70)
        self.assertIn("sede administrativa", result["publicReading"])

        incomplete = _faculty_breakdown([1, 2, 3, 4, 10])
        incomplete["categories"].pop()
        unavailable = higher_faculty_education_result(
            {"breakdowns": [incomplete]}
        )
        self.assertEqual(unavailable["dataStatus"], "unavailable")

        non_exhaustive = higher_faculty_education_result(
            {
                "breakdowns": [
                    _faculty_breakdown(
                        [1, 2, 3, 4, 10], exhaustive=False
                    )
                ]
            }
        )
        self.assertEqual(non_exhaustive["dataStatus"], "unavailable")

    def test_higher_no_ies_and_zero_faculty_denominator_are_not_applicable(self):
        no_ies = higher_faculty_education_result(
            {
                "breakdowns": [
                    {
                        "id": "faculty_education",
                        "year": 2024,
                        "status": "not_applicable",
                    }
                ]
            }
        )
        self.assertEqual(no_ies["dataStatus"], "not_applicable")
        self.assertEqual(no_ies["reasonCode"], "denominator_zero")

        zero = higher_faculty_education_result(
            {"breakdowns": [_faculty_breakdown([0, 0, 0, 0, 0])]}
        )
        self.assertEqual(zero["dataStatus"], "not_applicable")

    def test_package_builder_has_only_the_four_approved_relations(self):
        package = build_accelerated_package_results(
            special_education=_aee_document(1, 2, 50),
            municipal_education=_indigenous_document(),
            higher_education={
                "indicators": {
                    "esup-concluintes": {
                        "series": [
                            {"year": 2024, "status": "observed", "value": 12}
                        ]
                    }
                },
                "breakdowns": [_faculty_breakdown([1, 2, 3, 4, 10])],
            },
        )
        self.assertEqual(
            set(package),
            {
                AEE_RELATION_ID,
                INDIGENOUS_RELATION_ID,
                HIGHER_GRADUATES_RELATION_ID,
                HIGHER_FACULTY_EDUCATION_RELATION_ID,
            },
        )


if __name__ == "__main__":
    unittest.main()
