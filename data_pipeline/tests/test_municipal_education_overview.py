from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_DIR / "data_pipeline"))

from src.municipal_education_overview import (  # noqa: E402
    audit_fully_null_rows,
    build_2025_completeness_evidence,
    materialize_municipal_education_overview,
)


MUNICIPALITY = {
    "idMunicipality": "4320008",
    "name": "Sapucaia do Sul",
    "slug": "sapucaia-do-sul",
}

COMPLETE_EVIDENCE = {
    "referenceYear": 2025,
    "expectedMunicipalities": 497,
    "municipalitiesPresent": 497,
    "annualLoadPresent": True,
    "validDependencyDomain": True,
    "validSchoolLocationDomain": True,
    "duplicateGrainCount": 0,
    "negativeValueCount": 0,
    "isCompleteForDerivedZero": True,
}


def row(year: int, dependency: str, location: str, scale: int = 1, **overrides):
    values = {
        "ano": year,
        "id_municipio": "4320008",
        "dependencia": dependency,
        "localizacao": location,
        "mat_basico": 100 * scale,
        "mat_infantil": 30 * scale,
        "mat_infantil_creche": 12 * scale,
        "mat_infantil_pre": 18 * scale,
        "mat_fundamental": 50 * scale,
        "mat_fundamental_anos_iniciais": 25 * scale,
        "mat_fundamental_anos_finais": 25 * scale,
        "mat_medio": 10 * scale,
    }
    values.update(overrides)
    return values


def supplemental(rows):
    total = sum(item.get("mat_basico") or 0 for item in rows if item["ano"] == 2025)
    early = sum(item.get("mat_infantil") or 0 for item in rows if item["ano"] == 2025)
    elementary = sum(item.get("mat_fundamental") or 0 for item in rows if item["ano"] == 2025)
    high_school = total // 10
    eja = total // 20
    professional = total - early - elementary - high_school - eja
    concomitant = professional // 2
    return {
        "mat_medio": high_school,
        "mat_eja": eja,
        "mat_eja_fundamental": total // 40,
        "mat_eja_medio": eja - total // 40,
        "mat_medio_tecnico_integrado": total // 50,
        "mat_profissional_tecnico_concomitante": concomitant,
        "mat_profissional_tecnico_subsequente": professional - concomitant,
        "mat_profissional_tecnico_iftp_exclusivo": 0,
        "mat_profissional_iftp_qualificacao": 0,
        "mat_profissional_fic_concomitante": 0,
        "mat_educacao_especial": total // 10,
        "mat_educacao_especial_classes_comuns": total // 20,
        "mat_educacao_especial_classes_exclusivas": total // 20,
    }


def performance_rows():
    return [
        {
            "ano": 2025,
            "etapa_ensino": stage,
            "taxa_aprovacao": 90.0,
            "taxa_reprovacao": 8.0,
            "taxa_abandono": 2.0,
        }
        for stage in ("fundamental", "fundamental_anos_iniciais", "fundamental_anos_finais", "medio")
    ]


class MunicipalEducationOverviewTests(unittest.TestCase):
    def materialize(self, rows):
        return materialize_municipal_education_overview(
            rows,
            MUNICIPALITY,
            "2026-07-22T12:00:00-03:00",
            completeness=COMPLETE_EVIDENCE,
            comparison_completeness={**COMPLETE_EVIDENCE, "referenceYear": 2015},
            supplemental=supplemental(rows),
            performance_rows=performance_rows(),
        )

    def test_uses_2025_without_annual_fallback(self):
        contract = self.materialize([row(2024, "municipal", "urbana")])

        self.assertEqual(contract["reference"]["year"], 2025)
        self.assertEqual(contract["publicationState"], "unavailable")
        self.assertIsNone(contract["basicEducation"]["total"]["value"])

    def test_missing_central_total_makes_2025_unavailable(self):
        contract = self.materialize([row(2025, "municipal", "urbana", mat_fundamental=None)])

        self.assertEqual(contract["reference"]["year"], 2025)
        self.assertEqual(contract["publicationState"], "unavailable")
        self.assertEqual(contract["elementary"]["total"]["total"]["state"], "unavailable")

    def test_missing_federal_network_becomes_derived_zero(self):
        rows = [
            row(2025, "municipal", "urbana"),
            row(2025, "estadual", "rural"),
            row(2025, "privada", "urbana"),
        ]
        contract = self.materialize(rows)

        self.assertEqual(contract["publicationState"], "published")
        self.assertEqual(
            contract["earlyChildhood"]["total"]["byNetwork"]["federal"]["enrollments"]["state"],
            "derived_zero",
        )
        self.assertEqual(
            contract["earlyChildhood"]["total"]["byNetwork"]["federal"]["enrollments"]["value"],
            0,
        )

    def test_observed_zero_network_value_is_derived_with_complete_2025_evidence(self):
        contract = self.materialize(
            [
                row(2025, "municipal", "urbana"),
                row(2025, "federal", "urbana", mat_infantil=0),
            ]
        )

        federal = contract["earlyChildhood"]["total"]["byNetwork"]["federal"]["enrollments"]
        self.assertEqual(federal["state"], "derived_zero")
        self.assertEqual(federal["value"], 0)

    def test_missing_private_network_and_rural_location_become_derived_zero(self):
        contract = self.materialize([row(2025, "municipal", "urbana")])

        stage = contract["earlyChildhood"]["total"]
        self.assertEqual(stage["byNetwork"]["private"]["enrollments"]["state"], "derived_zero")
        self.assertEqual(stage["bySchoolLocation"]["rural"]["enrollments"]["state"], "derived_zero")
        self.assertEqual(set(stage["byNetwork"]), {"publicSubtotal", "municipal", "state", "federal", "private"})
        self.assertEqual(set(stage["bySchoolLocation"]), {"urban", "rural"})

    def test_null_core_row_blocks_only_its_related_cuts(self):
        null_row = row(
            2025,
            "estadual",
            "rural",
            mat_basico=None,
            mat_infantil=None,
            mat_infantil_creche=None,
            mat_infantil_pre=None,
            mat_fundamental=None,
            mat_fundamental_anos_iniciais=None,
            mat_fundamental_anos_finais=None,
            mat_medio=None,
            qntd_escolas=1,
        )
        rows = [
            row(2025, "municipal", "urbana"),
            null_row,
            row(2025, "privada", "urbana"),
        ]
        contract = self.materialize(rows)

        self.assertEqual(contract["publicationState"], "partial")
        self.assertEqual(contract["basicEducation"]["total"]["value"], 200)
        self.assertEqual(
            contract["earlyChildhood"]["total"]["byNetwork"]["state"]["enrollments"]["state"],
            "unavailable",
        )
        self.assertEqual(
            contract["earlyChildhood"]["total"]["byNetwork"]["federal"]["enrollments"]["state"],
            "derived_zero",
        )
        self.assertEqual(contract["quality"]["nullCoreRows"][0]["dependency"], "estadual")

    def test_public_subtotal_accepts_observed_and_derived_zero(self):
        contract = self.materialize([
            row(2025, "municipal", "urbana"),
            row(2025, "estadual", "rural"),
            row(2025, "privada", "urbana"),
        ])

        public_subtotal = contract["earlyChildhood"]["total"]["byNetwork"]["publicSubtotal"]["enrollments"]
        self.assertEqual(public_subtotal["state"], "observed")
        self.assertEqual(public_subtotal["value"], 60)

    def test_public_subtotal_rejects_unavailable_component(self):
        null_state = row(
            2025,
            "estadual",
            "rural",
            mat_basico=None,
            mat_infantil=None,
            mat_infantil_creche=None,
            mat_infantil_pre=None,
            mat_fundamental=None,
            mat_fundamental_anos_iniciais=None,
            mat_fundamental_anos_finais=None,
            mat_medio=None,
        )
        contract = self.materialize([row(2025, "municipal", "urbana"), null_state])

        public_subtotal = contract["earlyChildhood"]["total"]["byNetwork"]["publicSubtotal"]["enrollments"]
        self.assertEqual(public_subtotal["state"], "unavailable")

    def test_derived_zero_participates_in_reconciliations(self):
        contract = self.materialize([row(2025, "municipal", "urbana")])

        self.assertEqual(contract["publicationState"], "published")
        self.assertTrue(
            all(item["status"] == "reconciled" for item in contract["quality"]["reconciliations"])
        )

    def test_failed_central_reconciliation_makes_contract_invalid(self):
        rows = [
            row(2025, "municipal", "urbana", mat_infantil=31),
            row(2025, "estadual", "rural"),
            row(2025, "federal", "urbana"),
            row(2025, "privada", "rural"),
        ]
        contract = self.materialize(rows)

        self.assertEqual(contract["publicationState"], "invalid")
        self.assertTrue(
            any(item["status"] == "divergent" for item in contract["quality"]["reconciliations"])
        )

    def test_additive_composition_special_education_and_performance_are_materialized(self):
        contract = self.materialize([row(2025, "municipal", "urbana")])

        composition = contract["basicEducationComposition"]
        self.assertEqual(composition["total"]["value"], 100)
        self.assertEqual(composition["components"]["otherProfessionalOffers"]["total"]["value"], 5)
        self.assertEqual(composition["reconciliation"]["status"], "reconciled")
        self.assertEqual(contract["highSchool"]["total"]["total"]["value"], 10)
        self.assertEqual(contract["highSchool"]["integratedTechnical"]["total"]["value"], 2)
        self.assertEqual(contract["highSchool"]["total"]["byNetwork"]["municipal"]["enrollments"]["value"], 10)
        self.assertEqual(contract["highSchool"]["total"]["bySchoolLocation"]["urban"]["enrollments"]["value"], 10)
        self.assertEqual(contract["specialEducation"]["total"]["value"], 10)
        self.assertEqual(contract["schoolPerformance"]["stages"]["elementary"]["approval"]["value"], 90)

    def test_high_school_without_enrollments_is_not_applicable_in_performance(self):
        source = supplemental([row(2025, "municipal", "urbana")])
        source["mat_medio"] = 0
        source["mat_eja"] = 15
        source["mat_eja_fundamental"] = 8
        source["mat_eja_medio"] = 7
        contract = materialize_municipal_education_overview(
            [row(2025, "municipal", "urbana", mat_medio=0)],
            MUNICIPALITY,
            "2026-07-22T12:00:00-03:00",
            completeness=COMPLETE_EVIDENCE,
            supplemental=source,
            performance_rows=[item for item in performance_rows() if item["etapa_ensino"] != "medio"],
        )

        high_school = contract["schoolPerformance"]["stages"]["highSchool"]
        self.assertTrue(all(value["state"] == "not_applicable" for value in high_school.values()))

    def test_audit_preserves_structural_rows_as_non_zero(self):
        null_row = row(
            2025,
            "municipal",
            "rural",
            mat_basico=None,
            mat_infantil=None,
            mat_infantil_creche=None,
            mat_infantil_pre=None,
            mat_fundamental=None,
            mat_fundamental_anos_iniciais=None,
            mat_fundamental_anos_finais=None,
            mat_medio=None,
            qntd_escolas=1,
        )
        audit = audit_fully_null_rows([null_row, row(2025, "privada", "urbana")])

        self.assertEqual(audit["totalRows"], 1)
        self.assertEqual(audit["affectedMunicipalityYears"], 1)
        self.assertEqual(audit["byGrain"][0]["otherEducationalFieldsPopulated"], ["qntd_escolas"])
        self.assertEqual(audit["municipalityYearsAllCoreNull"], [])

    def test_completeness_evidence_requires_the_expected_2025_coverage(self):
        evidence = build_2025_completeness_evidence(
            [row(2025, "municipal", "urbana")],
            {"4320008"},
        )

        self.assertTrue(evidence["isCompleteForDerivedZero"])
        self.assertEqual(evidence["municipalitiesPresent"], 1)

        with self.assertRaisesRegex(ValueError, "permanecer texto"):
            build_2025_completeness_evidence(
                [{**row(2025, "municipal", "urbana"), "id_municipio": 4320008}],
                {"4320008"},
            )

    def test_historical_comparison_calculates_growth_reduction_and_stability(self):
        contract = self.materialize([
            row(2015, "municipal", "urbana", mat_basico=80, mat_infantil=40, mat_infantil_creche=20, mat_infantil_pre=20),
            row(2025, "municipal", "urbana", mat_basico=100, mat_infantil=30, mat_infantil_creche=20, mat_infantil_pre=10),
        ])

        stages = contract["enrollmentComparison"]["stages"]
        self.assertEqual(stages["basicEducation"]["total"]["percentageChange"]["value"], 25)
        self.assertEqual(stages["earlyChildhood"]["total"]["percentageChange"]["value"], -25)
        self.assertEqual(stages["creche"]["total"]["percentageChange"]["value"], 0)

    def test_historical_comparison_handles_zero_denominator_and_unavailable_value(self):
        contract = self.materialize([
            row(2015, "municipal", "urbana", mat_medio=0, mat_eja=None),
            row(2025, "municipal", "urbana", mat_medio=10, mat_eja=5),
        ])

        stages = contract["enrollmentComparison"]["stages"]
        self.assertEqual(stages["highSchool"]["total"]["percentageChange"]["state"], "not_applicable")
        self.assertIsNone(stages["highSchool"]["total"]["percentageChange"]["value"])
        self.assertEqual(stages["youthAndAdultEducation"]["total"]["percentageChange"]["state"], "unavailable")


if __name__ == "__main__":
    unittest.main()
