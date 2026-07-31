from __future__ import annotations

import json
import inspect
import math
from pathlib import Path
import tempfile
import unittest

import openpyxl

from data_pipeline.scripts.sync_pne_capes_2024 import parse_capes
from data_pipeline.scripts.sync_pne_munic_2021 import _response
from data_pipeline.scripts.sync_pne_quality_offer import (
    _empty_quality_record,
    _parse_cpc,
    _position,
)
from data_pipeline.src.pne.goal_indicator_contract import CONTRACT
from data_pipeline.src.pne_macro_ingestion import (
    DATA_ROOT,
    canonical_json_bytes,
    file_sha256,
    load_municipality_universe,
    normalized_snapshot,
)
from data_pipeline.src.pne_macro_round import (
    CAPES_TITLES_RELATION_ID,
    CPC_QUALITY_RELATION_ID,
    ENADE_LIC_RELATION_ID,
    MACRO_RELATION_IDS,
    MUNIC_CAREER_RELATION_ID,
    MUNIC_FORUM_RELATION_ID,
    capes_titles_result,
    load_macro_source_records,
    municipal_management_results,
    quality_offer_results,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
INCORPORATED_SOURCE_DIRS = ("munic_2021", "capes_2024", "quality_offer")
BLOCKED_SOURCE_DIRS = ("director_selection", "inec_connectivity")


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _assert_finite_numbers(test: unittest.TestCase, value: object) -> None:
    if isinstance(value, dict):
        for child in value.values():
            _assert_finite_numbers(test, child)
    elif isinstance(value, list):
        for child in value:
            _assert_finite_numbers(test, child)
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        test.assertTrue(math.isfinite(float(value)))


class PneMacroRoundSourceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifests = {
            name: _load_json(DATA_ROOT / name / "manifest.json")
            for name in (*INCORPORATED_SOURCE_DIRS, *BLOCKED_SOURCE_DIRS)
        }
        cls.normalized = {
            name: _load_json(DATA_ROOT / name / "normalized.json")
            for name in INCORPORATED_SOURCE_DIRS
        }
        (
            cls.munic_records,
            cls.capes_records,
            cls.quality_records,
        ) = load_macro_source_records()

    def test_each_approved_source_has_497_canonical_municipal_records(self):
        expected_ids = set(load_municipality_universe()[0])
        for name, payload in self.normalized.items():
            with self.subTest(source=name):
                self.assertEqual(payload["municipalityCount"], 497)
                self.assertEqual(set(payload["records"]), expected_ids)
                self.assertEqual(len(payload["records"]), len(set(payload["records"])))
                source_path = DATA_ROOT / name / "normalized.json"
                self.assertEqual(source_path.read_bytes(), canonical_json_bytes(payload))
                self.assertEqual(
                    file_sha256(source_path),
                    self.manifests[name]["normalization"]["normalizedSha256"],
                )

    def test_raw_snapshots_have_official_metadata_size_and_sha256(self):
        for name in INCORPORATED_SOURCE_DIRS:
            for entry in self.manifests[name]["rawFiles"]:
                with self.subTest(source=name, file=entry["fileName"]):
                    raw_path = DATA_ROOT / name / "raw" / entry["fileName"]
                    self.assertTrue(raw_path.is_file())
                    self.assertTrue(entry["officialUrl"].startswith("https://"))
                    self.assertEqual(raw_path.stat().st_size, entry["size"])
                    self.assertEqual(file_sha256(raw_path), entry["sha256"])

    def test_blocked_sources_are_audited_without_normalized_public_result(self):
        for name in BLOCKED_SOURCE_DIRS:
            with self.subTest(source=name):
                manifest = self.manifests[name]
                self.assertEqual(manifest["status"], "blocked")
                self.assertEqual(manifest["coverage"]["municipalityCount"], 0)
                self.assertFalse((DATA_ROOT / name / "normalized.json").exists())
                self.assertTrue(manifest["rawFiles"])

    def test_observed_zero_is_distinct_from_absence_and_not_applicable(self):
        management = municipal_management_results(
            {
                "year": 2021,
                "careerPlans": {"teacherPlan": "no", "nonTeachingPlan": "no"},
                "educationForum": "no",
            }
        )
        self.assertEqual(management[MUNIC_CAREER_RELATION_ID]["value"], 0)
        self.assertEqual(management[MUNIC_CAREER_RELATION_ID]["dataStatus"], "available")
        self.assertEqual(management[MUNIC_FORUM_RELATION_ID]["value"], 0)
        self.assertEqual(management[MUNIC_FORUM_RELATION_ID]["dataStatus"], "available")

        capes_zero = capes_titles_result(
            {
                "year": 2024,
                "localProgramCount": 1,
                "mastersAwarded": 0,
                "doctoratesAwarded": 0,
            }
        )
        self.assertEqual(capes_zero["value"], 0)
        self.assertEqual(capes_zero["dataStatus"], "available")
        self.assertEqual(
            capes_titles_result(
                {
                    "year": 2024,
                    "localProgramCount": 0,
                    "mastersAwarded": 0,
                    "doctoratesAwarded": 0,
                }
            )["dataStatus"],
            "not_applicable",
        )
        self.assertEqual(
            capes_titles_result(
                {
                    "year": 2024,
                    "localProgramCount": None,
                    "mastersAwarded": 0,
                    "doctoratesAwarded": 0,
                }
            )["dataStatus"],
            "unavailable",
        )
        for degree_field in ("mastersAwarded", "doctoratesAwarded"):
            positive = capes_titles_result(
                {
                    "year": 2024,
                    "localProgramCount": 0,
                    "mastersAwarded": 0,
                    "doctoratesAwarded": 0,
                    degree_field: 3,
                }
            )
            with self.subTest(degree=degree_field):
                self.assertEqual(positive["dataStatus"], "available")
                self.assertEqual(positive["value"], 3)

        incomplete = capes_titles_result(
            {
                "year": 2024,
                "localProgramCount": 1,
                "mastersAwarded": 0,
                "doctoratesAwarded": 0,
                "sourceCoverageStatus": "incomplete",
            }
        )
        self.assertEqual(incomplete["dataStatus"], "unavailable")
        self.assertEqual(
            capes_titles_result(
                {
                    "year": 2024,
                    "localProgramCount": 1,
                    "mastersAwarded": 1,
                    "doctoratesAwarded": 0,
                    "territorialityStatus": "inconclusive",
                }
            )["dataStatus"],
            "unavailable",
        )
        self.assertEqual(
            capes_titles_result(
                {
                    "year": 2024,
                    "localProgramCount": 1,
                    "mastersAwarded": 0,
                    "doctoratesAwarded": 0,
                    "titleDataStatus": "suppressed",
                }
            )["dataStatus"],
            "suppressed",
        )

    def test_all_positive_capes_titles_are_available_and_preserved(self):
        positive_municipalities = 0
        for municipality_id, record in self.capes_records.items():
            total = record["mastersAwarded"] + record["doctoratesAwarded"]
            result = capes_titles_result(record)
            if total <= 0:
                continue
            positive_municipalities += 1
            with self.subTest(municipality=municipality_id):
                self.assertEqual(result["dataStatus"], "available")
                self.assertEqual(result["value"], total)
        self.assertEqual(positive_municipalities, 35)

    def test_capes_output_is_strictly_the_497_rs_ibge_codes(self):
        self.assertEqual(len(self.capes_records), 497)
        self.assertTrue(all(code.startswith("43") for code in self.capes_records))
        self.assertNotIn("3205309", self.capes_records)

    def test_capes_network_territoriality_is_generic_and_reconciled(self):
        manifest = self.manifests["capes_2024"]
        reconciliations = manifest["audit"]["territorialReconciliation"]
        self.assertEqual(
            len(manifest["audit"]["municipalReconciliation"]),
            497,
        )
        self.assertEqual(len(reconciliations), 29)
        self.assertEqual(
            len({row["programCode"] for row in reconciliations}),
            15,
        )
        jaguari = next(
            row
            for row in reconciliations
            if row["programCode"] == "30004012074P8"
            and row["studentLinkedInstitutionMunicipality"] == "JAGUARI/RS"
        )
        self.assertEqual(jaguari["programHeadquarterMunicipality"], "VITÓRIA/ES")
        self.assertEqual(jaguari["mastersAwarded"], 24)
        self.assertEqual(jaguari["doctoratesAwarded"], 0)
        self.assertEqual(
            jaguari["territorialDecision"],
            "student_linked_participant_institution_municipality",
        )
        self.assertIn("IFFARROUPILHA", jaguari["participantInstitutions"][0])
        self.assertNotIn("jaguari", inspect.getsource(parse_capes).casefold())
        state = manifest["audit"]["stateAggregation"]
        self.assertEqual(state["municipalTitleSum"], 7683)
        self.assertEqual(state["uniqueTitleRows"], 7683)
        self.assertEqual(state["duplicateTitleRows"], 0)
        self.assertTrue(state["publishable"])

    def test_quality_ratios_preserve_zero_unknown_and_cycle_absence(self):
        zero_record = {
            "cpc2023": {"adequateCount": 0, "validCount": 2},
            "enadeLicenciaturas2025": {"adequateCount": 0, "validCount": 8},
        }
        with_offer = {
            "indicators": {
                "esup-matriculas-total": {
                    "series": [{"year": 2024, "status": "observed", "value": 1}]
                }
            }
        }
        no_offer = {
            "indicators": {
                "esup-matriculas-total": {
                    "series": [{"year": 2024, "status": "derived_zero", "value": 0}]
                }
            }
        }
        result = quality_offer_results(zero_record, higher_education=with_offer)
        self.assertEqual(result[CPC_QUALITY_RELATION_ID]["value"], 0)
        self.assertEqual(result[CPC_QUALITY_RELATION_ID]["denominator"], 2)
        self.assertEqual(result[ENADE_LIC_RELATION_ID]["value"], 0)
        self.assertEqual(result[ENADE_LIC_RELATION_ID]["denominator"], 8)

        empty = {
            "cpc2023": {"adequateCount": 0, "validCount": 0},
            "enadeLicenciaturas2025": {"adequateCount": 0, "validCount": 0},
        }
        self.assertEqual(
            quality_offer_results(empty, higher_education=no_offer)[
                CPC_QUALITY_RELATION_ID
            ]["dataStatus"],
            "not_applicable",
        )
        self.assertEqual(
            quality_offer_results(empty, higher_education=with_offer)[
                CPC_QUALITY_RELATION_ID
            ]["reasonCode"],
            "no_evaluation_in_cycle",
        )
        self.assertEqual(
            quality_offer_results(empty, higher_education={})[
                CPC_QUALITY_RELATION_ID
            ]["reasonCode"],
            "local_offer_status_unknown",
        )

    def test_suppression_is_unknown_not_zero(self):
        suppressed = sum(
            record["enadeLicenciaturas2025"]["suppressedParticipantCount"]
            for record in self.quality_records.values()
        )
        valid = sum(
            record["enadeLicenciaturas2025"]["validCount"]
            for record in self.quality_records.values()
        )
        self.assertEqual(suppressed, 22)
        self.assertEqual(valid, 4236)
        self.assertEqual(
            self.manifests["quality_offer"]["absencePolicy"]["suppressedResult"],
            "unknown; never zero",
        )

    def test_unknown_fields_and_dictionary_changes_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "não reconhecida"):
            _response("Talvez")
        with self.assertRaisesRegex(ValueError, "Coluna ausente"):
            _position({}, "CPC (Faixa)")
        with tempfile.TemporaryDirectory(prefix="pne-capes-schema-") as root:
            root_path = Path(root)
            programs = root_path / "programs.csv"
            students = root_path / "students.csv"
            programs.write_text("AN_BASE;SG_UF_PROGRAMA\n2024;RS\n", encoding="latin1")
            students.write_text("AN_BASE;SG_UF_PROGRAMA\n2024;RS\n", encoding="latin1")
            with self.assertRaisesRegex(ValueError, "Programas CAPES sem colunas"):
                parse_capes(programs, students)

    def test_duplicate_course_is_rejected(self):
        names = load_municipality_universe()[0]
        records = {
            municipality_id: _empty_quality_record(municipality_id, name)
            for municipality_id, name in names.items()
        }
        workbook = openpyxl.Workbook()
        worksheet = workbook.active
        worksheet.append(
            [
                "Código do Município",
                "Sigla da UF",
                "Código do Curso",
                "CPC (Faixa)",
                "Organização Acadêmica",
                "Categoria Administrativa",
            ]
        )
        for concept in (3, 4):
            worksheet.append(
                [4300034, "RS", "curso-duplicado", concept, "Universidade", "Pública"]
            )
        with tempfile.TemporaryDirectory(prefix="pne-cpc-duplicate-") as root:
            path = Path(root) / "cpc.xlsx"
            workbook.save(path)
            with self.assertRaisesRegex(ValueError, "duplicado"):
                _parse_cpc(path, records)
        workbook.close()

    def test_all_numbers_are_finite_and_normalization_is_deterministic(self):
        for name, payload in self.normalized.items():
            with self.subTest(source=name):
                _assert_finite_numbers(self, payload)
                self.assertNotIn(b"NaN", canonical_json_bytes(payload))
                self.assertNotIn(b"Infinity", canonical_json_bytes(payload))
        sample = self.normalized["munic_2021"]
        names = load_municipality_universe()[0]
        left = normalized_snapshot(
            source_id=sample["sourceId"],
            edition=sample["edition"],
            records=sample["records"],
            municipality_names=names,
        )
        right = normalized_snapshot(
            source_id=sample["sourceId"],
            edition=sample["edition"],
            records=dict(reversed(list(sample["records"].items()))),
            municipality_names=names,
        )
        self.assertEqual(canonical_json_bytes(left), canonical_json_bytes(right))

    def test_macro_relations_have_no_state_average_or_classifying_capability(self):
        relations = {
            relation["relationId"]: relation for relation in CONTRACT["relations"]
        }
        self.assertEqual(set(MACRO_RELATION_IDS), {
            MUNIC_CAREER_RELATION_ID,
            MUNIC_FORUM_RELATION_ID,
            CAPES_TITLES_RELATION_ID,
            CPC_QUALITY_RELATION_ID,
            ENADE_LIC_RELATION_ID,
        })
        for relation_id in MACRO_RELATION_IDS:
            relation = relations[relation_id]
            with self.subTest(relation=relation_id):
                expected_mode = (
                    "tracking"
                    if relation_id
                    in {MUNIC_CAREER_RELATION_ID, MUNIC_FORUM_RELATION_ID}
                    else "complementary"
                )
                self.assertEqual(relation["mode"], expected_mode)
                self.assertEqual(relation["stateReferencePolicy"], "none")
                self.assertEqual(
                    relation["canDistance"], expected_mode == "tracking"
                )
                self.assertEqual(
                    relation["canStatus"], expected_mode == "tracking"
                )
                self.assertFalse(relation["canProjection"])
                self.assertIsNone(relation["referenceId"])


if __name__ == "__main__":
    unittest.main()
