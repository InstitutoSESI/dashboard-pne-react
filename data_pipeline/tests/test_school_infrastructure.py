import sys
import unittest
from pathlib import Path

import pandas as pd


PIPELINE_ROOT = Path(__file__).resolve().parents[1]
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

from src.school_infrastructure import (  # noqa: E402
    aggregate_school_infrastructure,
    summarize_source_quality,
)


def school(
    entity,
    *,
    active=1,
    dependency=3,
    location=1,
    municipality="4300000",
    water=1,
    no_energy=0,
    internet=1,
    library=1,
    court=1,
    sewer=1,
):
    return {
        "ano": 2025,
        "id_municipio": municipality,
        "cod_escola": entity,
        "situacao_funcionamento": active,
        "tp_dependencia": dependency,
        "tp_localizacao": location,
        "in_agua_potavel": water,
        "in_energia_inexistente": no_energy,
        "in_internet": internet,
        "in_biblioteca_sala_leitura": library,
        "in_quadra_esportes": court,
        "in_esgoto_rede_publica": sewer,
    }


def row(result, indicator, cut="total"):
    return result[
        result["indicador"].eq(indicator) & result["recorte"].eq(cut)
    ].iloc[0]


class SchoolInfrastructureTests(unittest.TestCase):
    def test_inactive_school_is_excluded(self):
        result = aggregate_school_infrastructure(
            pd.DataFrame([school(1), school(2, active=2)])
        )
        self.assertEqual(row(result, "internet")["totalActiveSchools"], 1)

    def test_conflicting_duplicate_entity_raises(self):
        with self.assertRaisesRegex(ValueError, "conflitantes"):
            aggregate_school_infrastructure(
                pd.DataFrame([school(1), school(1, internet=0)])
            )

    def test_identical_duplicate_is_deterministic(self):
        result = aggregate_school_infrastructure(
            pd.DataFrame([school(1), school(1)])
        )
        self.assertEqual(row(result, "internet")["totalActiveSchools"], 1)

    def test_null_and_invalid_are_missing(self):
        frame = pd.DataFrame(
            [
                school(1, internet=None),
                school(2, internet=7),
                school(3, internet=""),
            ]
        )
        result = aggregate_school_infrastructure(frame)
        total = row(result, "internet")
        quality = summarize_source_quality(frame).set_index("indicador")
        self.assertEqual(total["missingSchools"], 3)
        self.assertEqual(total["denominator"], 0)
        self.assertEqual(quality.loc["internet", "nullSchools"], 2)
        self.assertEqual(quality.loc["internet", "invalidSchools"], 1)

    def test_observed_zero_is_real_zero_percent(self):
        result = aggregate_school_infrastructure(
            pd.DataFrame([school(1, sewer=0), school(2, sewer=0)])
        )
        total = row(result, "esgoto_rede_publica")
        self.assertEqual(total["numerator"], 0)
        self.assertEqual(total["denominator"], 2)
        self.assertEqual(total["percentage"], 0.0)
        self.assertEqual(total["status"], "published")

    def test_energy_rule_is_inverted(self):
        result = aggregate_school_infrastructure(
            pd.DataFrame([school(1, no_energy=0), school(2, no_energy=1)])
        )
        total = row(result, "energia_eletrica")
        self.assertEqual(total["numerator"], 1)
        self.assertEqual(total["denominator"], 2)

    def test_numerator_never_exceeds_denominator(self):
        result = aggregate_school_infrastructure(
            pd.DataFrame([school(1), school(2, water=None)])
        )
        self.assertTrue((result["numerator"] <= result["denominator"]).all())

    def test_zero_denominator_has_null_percentage(self):
        result = aggregate_school_infrastructure(
            pd.DataFrame([school(1, internet=None)])
        )
        total = row(result, "internet")
        self.assertEqual(total["denominator"], 0)
        self.assertTrue(pd.isna(total["percentage"]))
        self.assertEqual(total["status"], "unavailable")

    def test_dependency_cuts_and_public_reconciliation(self):
        frame = pd.DataFrame(
            [
                school(1, dependency=1),
                school(2, dependency=2),
                school(3, dependency=3),
                school(4, dependency=4),
            ]
        )
        result = aggregate_school_infrastructure(frame)
        for cut in ["federal", "estadual", "municipal", "privada"]:
            self.assertEqual(row(result, "internet", cut)["totalActiveSchools"], 1)
        self.assertEqual(row(result, "internet", "publica")["totalActiveSchools"], 3)
        public = row(result, "internet", "publica")
        components = sum(
            row(result, "internet", cut)["numerator"]
            for cut in ["federal", "estadual", "municipal"]
        )
        self.assertEqual(public["numerator"], components)

    def test_urban_and_rural_cuts(self):
        result = aggregate_school_infrastructure(
            pd.DataFrame([school(1, location=1), school(2, location=2)])
        )
        self.assertEqual(row(result, "internet", "urbana")["denominator"], 1)
        self.assertEqual(row(result, "internet", "rural")["denominator"], 1)

    def test_percentage_is_not_rounded(self):
        result = aggregate_school_infrastructure(
            pd.DataFrame(
                [school(1, internet=1), school(2, internet=0), school(3, internet=0)]
            )
        )
        percentage = row(result, "internet")["percentage"]
        self.assertAlmostEqual(percentage, 100 / 3)
        self.assertNotEqual(percentage, round(percentage, 2))

    def test_published_partial_and_unavailable(self):
        result = aggregate_school_infrastructure(
            pd.DataFrame(
                [
                    school(1, internet=1, water=1, court=None),
                    school(2, internet=None, water=0, court=None),
                ]
            )
        )
        self.assertEqual(row(result, "agua_potavel")["status"], "published")
        self.assertEqual(row(result, "internet")["status"], "partial")
        self.assertEqual(row(result, "quadra_esportes")["status"], "unavailable")

    def test_cut_without_schools_keeps_zero_total(self):
        result = aggregate_school_infrastructure(
            pd.DataFrame([school(1, dependency=3)])
        )
        federal = row(result, "internet", "federal")
        self.assertEqual(federal["totalActiveSchools"], 0)
        self.assertEqual(federal["denominator"], 0)
        self.assertEqual(federal["status"], "unavailable")


if __name__ == "__main__":
    unittest.main()
