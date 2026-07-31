from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from data_pipeline.scripts.materialize_pne2026_public_diagnostic_v3 import (
    GitBlobSnapshot,
    compare_staging_directories,
    prepare_staging,
    staging_hashes,
    validate_staging_output_path,
    write_staging,
)
from data_pipeline.src.pne.goal_indicator_contract import CONTRACT
from data_pipeline.src.pne2026_public_diagnostic_v3 import (
    CONTRACT_HASH,
    PRESENTATION_POLICY_HASH,
    PUBLIC_V3_SCHEMA_VERSION,
    Pne2026PublicDiagnosticV3Error,
    _upgrade_legacy_attendance_projection,
    flatten_v2_results,
    validate_pne2026_public_diagnostic_v3,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
RELATIONS_BY_ID = {
    relation["relationId"]: relation for relation in CONTRACT["relations"]
}
RELATIONS_BY_PAIR = {
    (relation["goalId"], relation["indicatorId"]): relation
    for relation in CONTRACT["relations"]
}


class _WorkingTreeJsonSnapshot:
    def __enter__(self) -> "_WorkingTreeJsonSnapshot":
        return self

    def read_json(self, path: str) -> dict:
        return json.loads((REPO_ROOT / path).read_text(encoding="utf-8"))

    def __exit__(self, *_: object) -> None:
        return None


def _relation_for_v2(result: dict) -> dict:
    relation_id = result.get("relationId")
    if relation_id:
        return RELATIONS_BY_ID[relation_id]
    return RELATIONS_BY_PAIR[(result["goalId"], result["indicatorId"])]


def _v2_normalized_record(
    result: dict,
    technical_by_indicator: dict[str, dict],
) -> dict:
    relation = _relation_for_v2(result)
    technical = technical_by_indicator.get(relation["indicatorId"]) or {}
    methodology = technical.get("methodology") or {}
    trajectory = result.get("trajectory") or {}
    trend = {
        "historicalReading": trajectory["historicalReading"]
    } if trajectory.get("historicalReading") is not None else None
    projection = {
        key: trajectory[key]
        for key in ("estimatedAchievementYear", "achievementReading")
        if trajectory.get(key) is not None
    } or None
    return {
        "relationId": relation["relationId"],
        "goalId": relation["goalId"],
        "indicatorId": relation["indicatorId"],
        "dataStatus": result.get("dataStatus") or "available",
        "reasonCode": None,
        "year": (result.get("current") or {}).get("year"),
        "value": (result.get("current") or {}).get("value"),
        "numeratorField": methodology.get("numerator"),
        "numeratorValue": None,
        "denominatorField": methodology.get("denominator"),
        "denominatorValue": None,
        "resolvedReferenceId": (
            relation.get("referenceId")
            if relation["mode"] == "progress"
            and result.get("indicatorReference")
            else None
        ),
        "distance": (
            result.get("distance") if relation.get("canDistance") else None
        ),
        "remainingGap": (
            result.get("remainingGap")
            if relation.get("canDistance")
            else None
        ),
        "favorableDifference": (
            result.get("favorableDifference")
            if relation.get("canDistance")
            else None
        ),
        "status": (
            result.get("status") if relation.get("canStatus") else None
        ),
        "classification": (
            result.get("classification")
            if relation.get("canStatus")
            else None
        ),
        "publicReading": result.get("publicReading"),
        "stateComparison": (
            result.get("stateComparison")
            if relation.get("stateReferencePolicy") != "none"
            else None
        ),
        "statewidePosition": (
            result.get("statewidePosition")
            if relation.get("stateReferencePolicy") != "none"
            else None
        ),
        "similarMunicipalityComparison": (
            result.get("similarMunicipalities")
            if relation.get("stateReferencePolicy") != "none"
            else None
        ),
        "trend": trend if relation.get("canProjection") else None,
        "projection": projection if relation.get("canProjection") else None,
    }


def _v3_normalized_record(result: dict) -> dict:
    return {
        key: result.get(key)
        for key in (
            "relationId",
            "goalId",
            "indicatorId",
            "dataStatus",
            "reasonCode",
            "year",
            "value",
            "numeratorField",
            "numeratorValue",
            "denominatorField",
            "denominatorValue",
            "resolvedReferenceId",
            "distance",
            "remainingGap",
            "favorableDifference",
            "status",
            "classification",
            "publicReading",
            "stateComparison",
            "statewidePosition",
            "similarMunicipalityComparison",
            "trend",
            "projection",
        )
    }


class Pne2026PublicDiagnosticV3Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prepared = prepare_staging()
        cls.manifest = cls.prepared["manifest"]
        cls.payload_by_id = {
            payload["municipality"]["id"]: payload
            for payload in cls.prepared["payloads"]
        }
        with GitBlobSnapshot() as snapshot:
            cls.acegua_contract = snapshot.read_json(
                "public/data/municipios/4300034/diagnostico.json"
            )
        cls.acegua = cls.payload_by_id["4300034"]

    def test_schema_versions_hashes_and_canonical_summary(self):
        self.assertEqual(
            self.acegua["schemaVersion"], PUBLIC_V3_SCHEMA_VERSION
        )
        self.assertEqual(self.acegua["contractVersion"], "1.9.0")
        self.assertEqual(self.acegua["contractHash"], CONTRACT_HASH)
        self.assertEqual(
            self.acegua["presentationPolicyVersion"], "1.7.0"
        )
        self.assertEqual(
            self.acegua["presentationPolicyHash"],
            PRESENTATION_POLICY_HASH,
        )
        self.assertEqual(
            self.acegua["summary"]["visibleResultCount"],
            len(self.acegua["results"]),
        )

    def test_relation_id_is_required_and_matches_the_auditable_pair(self):
        missing = deepcopy(self.acegua)
        del missing["results"][0]["relationId"]
        with self.assertRaisesRegex(
            Pne2026PublicDiagnosticV3Error, "relationId"
        ):
            validate_pne2026_public_diagnostic_v3(missing)

        mismatch = deepcopy(self.acegua)
        mismatch["results"][0]["goalId"] = "1.c"
        with self.assertRaisesRegex(
            Pne2026PublicDiagnosticV3Error, "identidade canônica"
        ):
            validate_pne2026_public_diagnostic_v3(mismatch)

        unknown = deepcopy(self.acegua)
        unknown["results"][0]["relationId"] = "relation.unknown"
        with self.assertRaisesRegex(
            Pne2026PublicDiagnosticV3Error, "desconhecido"
        ):
            validate_pne2026_public_diagnostic_v3(unknown)

    def test_allowlist_hashes_hidden_and_complementary_invariants(self):
        deprecated = deepcopy(self.acegua)
        deprecated["results"][0]["relationshipType"] = "direct"
        with self.assertRaisesRegex(
            Pne2026PublicDiagnosticV3Error, "campos desconhecidos"
        ):
            validate_pne2026_public_diagnostic_v3(deprecated)

        bad_hash = deepcopy(self.acegua)
        bad_hash["contractHash"] = "0" * 64
        with self.assertRaisesRegex(
            Pne2026PublicDiagnosticV3Error, "contractHash"
        ):
            validate_pne2026_public_diagnostic_v3(bad_hash)

        hidden = deepcopy(self.acegua)
        hidden_relation = next(
            relation
            for relation in CONTRACT["relations"]
            if relation["mode"] == "hidden"
        )
        hidden["results"][0].update(
            {
                "relationId": hidden_relation["relationId"],
                "goalId": hidden_relation["goalId"],
                "indicatorId": hidden_relation["indicatorId"],
            }
        )
        hidden["summary"]["presentationPriorityCounts"]["essential"] -= 1
        hidden["summary"]["presentationPriorityCounts"]["standard"] += 1
        with self.assertRaisesRegex(
            Pne2026PublicDiagnosticV3Error, "oculta"
        ):
            validate_pne2026_public_diagnostic_v3(hidden)

        complementary = deepcopy(self.acegua)
        item = next(
            result
            for result in complementary["results"]
            if RELATIONS_BY_ID[result["relationId"]]["mode"]
            == "complementary"
        )
        item["distance"] = 1
        with self.assertRaisesRegex(
            Pne2026PublicDiagnosticV3Error,
            "não autorizado|complementar",
        ):
            validate_pne2026_public_diagnostic_v3(complementary)

        suppressed = deepcopy(self.acegua)
        negative = next(
            result
            for result in suppressed["results"]
            if result["dataStatus"] == "unavailable"
        )
        negative["dataStatus"] = "suppressed"
        negative["reasonCode"] = "source_suppression"
        suppressed["summary"]["dataStatusCounts"]["unavailable"] -= 1
        suppressed["summary"]["dataStatusCounts"]["suppressed"] += 1
        self.assertEqual(
            validate_pne2026_public_diagnostic_v3(suppressed),
            suppressed,
        )

    def test_basico_15_17_uses_the_canonical_monitoring_reference(self):
        result = next(
            item
            for item in self.acegua["results"]
            if item["relationId"] == "relation.4.a.basico_15_17"
        )
        self.assertEqual(
            RELATIONS_BY_ID[result["relationId"]]["mode"],
            "tracking",
        )
        self.assertEqual(
            result["resolvedReferenceId"],
            "monitoring.4.a.basico_15_17",
        )
        self.assertEqual(result["distance"], result["value"] - 100)
        self.assertEqual(
            result["status"],
            "Referência alcançada"
            if result["value"] >= 100
            else "Abaixo da referência",
        )
        for field in (
            "classification",
            "stateComparison",
            "statewidePosition",
            "similarMunicipalityComparison",
            "trend",
            "projection",
        ):
            self.assertNotIn(field, result)

    def test_summary_must_be_recomputed_from_the_final_results(self):
        invalid = deepcopy(self.acegua)
        invalid["summary"]["complementaryResultCount"] += 1
        with self.assertRaisesRegex(
            Pne2026PublicDiagnosticV3Error, "summary"
        ):
            validate_pne2026_public_diagnostic_v3(invalid)

    def test_complete_generation_manifest_matches_the_validated_baseline(self):
        self.assertEqual(self.manifest["generatedMunicipalityCount"], 497)
        self.assertEqual(
            self.manifest["totalResultCount"],
            sum(self.manifest["modeCounts"].values()),
        )
        self.assertEqual(self.manifest["totalResultCount"], 25347)
        self.assertEqual(
            self.manifest["modeCounts"],
            {
                "progress": 13419,
                "tracking": 7455,
                "complementary": 4473,
            },
        )
        self.assertEqual(
            self.manifest["referenceKindCounts"],
            {"legal": 11648, "monitoring": 6005},
        )
        self.assertEqual(
            self.manifest["presentationPriorityCounts"],
            {"essential": 6461, "standard": 18886},
        )
        self.assertEqual(self.manifest["minimumResultsPerMunicipality"], 51)
        self.assertEqual(self.manifest["maximumResultsPerMunicipality"], 51)
        self.assertEqual(
            self.manifest["dataStatusCounts"],
            {
                "available": 19812,
                "unavailable": 3137,
                "not_applicable": 2398,
                "suppressed": 0,
            },
        )
        self.assertEqual(self.manifest["percentValuesAbove100Count"], 428)
        self.assertEqual(self.manifest["countValuesAbove100Count"], 99)
        self.assertEqual(
            self.manifest["classificationCounts"],
            {"advance": 10057, "maintain": 1591, "unclassified": 0},
        )
        self.assertEqual(
            self.manifest["hiddenExcludedCount"],
            961,
        )
        self.assertGreaterEqual(self.manifest["hiddenExcludedCount"], 0)
        self.assertGreaterEqual(
            self.manifest["percentValuesAbove100Count"], 0
        )
        self.assertGreaterEqual(
            self.manifest["countValuesAbove100Count"], 0
        )
        self.assertLessEqual(
            self.manifest["minimumResultsPerMunicipality"],
            self.manifest["maximumResultsPerMunicipality"],
        )
        self.assertEqual(self.manifest["duplicateRelationCount"], 0)
        self.assertEqual(self.manifest["invalidFileCount"], 0)
        self.assertEqual(
            self.manifest["presentationPolicyHash"],
            PRESENTATION_POLICY_HASH,
        )

    def test_record_by_record_v2_to_v3_parity_for_all_municipalities(self):
        before = []
        after = []
        with _WorkingTreeJsonSnapshot() as snapshot:
            registry = snapshot.read_json(
                "public/data/municipios_index.json"
            )
            for entry in sorted(
                registry["municipios"],
                key=lambda item: str(item["id_municipio"]),
            ):
                municipality_id = str(entry["id_municipio"])
                contract = snapshot.read_json(
                    "public/data/municipios/"
                    f"{municipality_id}/diagnostico.json"
                )
                technical = {
                    item["indicatorId"]: item
                    for item in contract.get("indicators") or []
                }
                public_v2 = contract["pne2026PublicDiagnosticV2"]
                v2_visible = []
                for result in flatten_v2_results(public_v2):
                    relation = _relation_for_v2(result)
                    if (
                        relation["mode"] != "hidden"
                        and relation["includeInDiagnostic"] is True
                    ):
                        v2_visible.append(result)
                v2_by_relation = {
                    _relation_for_v2(result)["relationId"]: result
                    for result in v2_visible
                }
                v3_by_relation = {
                    result["relationId"]: result
                    for result in self.payload_by_id[
                        municipality_id
                    ]["results"]
                }
                changed_relations = {
                    "relation.11.b.fundamental_concluido_18_mais",
                    "relation.11.b.fundamental_concluido_15_29",
                    "relation.11.b.fundamental_concluido_15_mais",
                    "relation.1.a.creche",
                    "relation.1.c.pre_escola",
                    "relation.4.a.basico_6_17",
                    "relation.4.a.basico_15_17",
                    "relation.4.b.idade_regular_quinto",
                    "relation.4.c.idade_regular_nono",
                    "relation.4.d.idade_regular_medio",
                    "relation.8.b.salas_climatizadas",
                    "relation.18.b.conselho_escolar",
                    "relation.19.c.salas_acessiveis",
                    "relation.12.a.medio_tecnico_articulado_percentual",
                    "relation.12.a.medio_tecnico_participacao_publica",
                    "relation.12.b.subsequente_expansao",
                    "relation.9.d.educacao_indigena_cobertura_estimada_4_17",
                    "relation.10.b.aee_oferta_escolas_elegiveis",
                    "relation.14.c.superior_concluintes_oferta_local",
                    "relation.15.c.superior_docentes_mestres_doutores_sede",
                    "relation.15.a.cpc_cursos_oferta_local",
                    "relation.16.a.capes_titulados_oferta_local",
                    "relation.17.c.munic_planos_carreira_declarados",
                    "relation.17.e.enade_licenciaturas_oferta_local",
                    "relation.18.c.munic_forum_educacao_declarado",
                }
                stable_relation_ids = (
                    set(v2_by_relation) & set(v3_by_relation)
                ) - changed_relations
                stable_relation_ids = {
                    relation_id
                    for relation_id in stable_relation_ids
                    if RELATIONS_BY_ID[relation_id]["mode"]
                    != "complementary"
                }
                for relation_id in sorted(stable_relation_ids):
                    before.append(
                        {
                            "municipalityId": municipality_id,
                            **_v2_normalized_record(
                                v2_by_relation[relation_id], technical
                            ),
                        }
                    )
                    after.append(
                        {
                            "municipalityId": municipality_id,
                            **_v3_normalized_record(
                                v3_by_relation[relation_id]
                            ),
                        }
                    )
        self.assertEqual(before, after)
        digest = lambda value: hashlib.sha256(
            json.dumps(
                value,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        self.assertEqual(digest(before), digest(after))

    def test_required_methodological_regressions_are_preserved(self):
        acegua_values = {
            result["indicatorId"]: result["value"]
            for result in self.acegua["results"]
            if result["dataStatus"] == "available"
        }
        self.assertEqual(round(acegua_values["pre_escola"], 1), 122.2)
        self.assertEqual(round(acegua_values["basico_6_17"], 1), 111.8)
        hidden_indicators = {"rendimento_magisterio"}
        complementary_goal_ids = {
            "7.a",
            "17.d",
            "17.f",
            "14.c",
            "15.c",
            "15.a",
            "16.a",
            "17.e",
            "9.d",
            "10.b",
        }
        all_results = [
            result
            for payload in self.prepared["payloads"]
            for result in payload["results"]
        ]
        self.assertFalse(
            hidden_indicators
            & {result["indicatorId"] for result in all_results}
        )
        for indicator_id in (
            "medio_tecnico_participacao_publica",
            "subsequente_expansao",
        ):
            ept_results = [
                result
                for result in all_results
                if result["indicatorId"] == indicator_id
            ]
            self.assertEqual(len(ept_results), 497)
            self.assertTrue(
                all(
                    result["dataStatus"] == "unavailable"
                    and result["reasonCode"]
                    == "no_post_baseline_observation"
                    for result in ept_results
                )
            )
        absence_reasons = self.prepared["methodologyAudit"]["absenceReasonCounts"]
        self.assertEqual(
            absence_reasons[
                "relation.15.a.cpc_cursos_oferta_local:"
                "local_offer_status_unknown"
            ],
            249,
        )
        self.assertEqual(
            absence_reasons[
                "relation.16.a.capes_titulados_oferta_local:"
                "no_local_stricto_sensu_offer_or_student_record"
            ],
            462,
        )
        jaguari_capes = next(
            result
            for result in self.payload_by_id["4311106"]["results"]
            if result["relationId"]
            == "relation.16.a.capes_titulados_oferta_local"
        )
        self.assertEqual(jaguari_capes["dataStatus"], "available")
        self.assertEqual(jaguari_capes["value"], 24)
        for forbidden in (
            "distance",
            "remainingGap",
            "favorableDifference",
            "status",
            "classification",
            "trend",
            "projection",
            "resolvedReferenceId",
        ):
            self.assertNotIn(forbidden, jaguari_capes)
        self.assertEqual(
            absence_reasons[
                "relation.17.e.enade_licenciaturas_oferta_local:"
                "no_evaluation_in_cycle"
            ],
            178,
        )
        self.assertGreater(
            self.prepared["methodologyAudit"]["preservedNonPackageRecordCount"],
            0,
        )
        self.assertGreaterEqual(
            self.prepared["methodologyAudit"]["changedNonPackageRecordCount"],
            0,
        )
        self.assertGreaterEqual(
            self.prepared["methodologyAudit"]["changedTrackingRecordCount"],
            0,
        )
        self.assertGreaterEqual(
            self.prepared["methodologyAudit"]["changedProjectionRecordCount"],
            0,
        )
        for goal_id in complementary_goal_ids:
            canonical = [
                relation
                for relation in CONTRACT["relations"]
                if relation["goalId"] == goal_id
            ]
            self.assertTrue(canonical, goal_id)
            self.assertTrue(
                all(relation["mode"] == "complementary" for relation in canonical),
                goal_id,
            )

            matching = [
                result
                for result in all_results
                if result["goalId"] == goal_id
            ]
            self.assertTrue(
                all(
                    RELATIONS_BY_ID[result["relationId"]]["mode"]
                    == "complementary"
                    for result in matching
                ),
                goal_id,
            )
        integrated = [
            result
            for result in all_results
            if result["indicatorId"]
            == "medio_tecnico_articulado_percentual"
        ]
        self.assertTrue(integrated)
        self.assertTrue(
            all(
                RELATIONS_BY_ID[result["relationId"]]["mode"]
                == "tracking"
                for result in integrated
            )
        )
        complementary = [
            result
            for result in all_results
            if RELATIONS_BY_ID[result["relationId"]]["mode"]
            == "complementary"
        ]
        for field in (
            "distance",
            "status",
            "classification",
            "projection",
        ):
            self.assertTrue(
                all(field not in result for result in complementary),
                field,
            )
        self.assertTrue(
            any(
                RELATIONS_BY_ID[result["relationId"]]["canProjection"]
                and "projection" not in result
                for result in all_results
            )
        )
        minimum_payload = min(
            self.prepared["payloads"],
            key=lambda payload: len(payload["results"]),
        )
        self.assertEqual(len(minimum_payload["results"]), 51)
        self.assertTrue(
            any(
                result["dataStatus"] != "available"
                for result in minimum_payload["results"]
            )
        )
        for result in all_results:
            self.assertNotIn("numerator", result)
            self.assertNotIn("denominator", result)

    def test_legacy_attendance_projection_removes_unsupported_exact_year(self):
        migrated = _upgrade_legacy_attendance_projection(
            {
                "indicatorId": "creche",
                "projection": {
                    "estimatedAchievementYear": 2033,
                    "achievementReading": (
                        "Se a evolução recente continuar, o município pode "
                        "alcançar o valor previsto em 2033."
                    ),
                    "modelReading": "Cenário modelado por tendência suavizada.",
                    "denominatorReading": "Texto legado do denominador.",
                    "uncertaintyReading": "Texto legado da incerteza.",
                },
            }
        )
        projection = migrated["projection"]
        self.assertNotIn("estimatedAchievementYear", projection)
        self.assertNotIn("achievementReading", projection)
        self.assertIn("mantém o número de matrículas", projection["modelReading"])
        self.assertNotIn("tendência suavizada", projection["modelReading"])
        self.assertIn("denominador", projection["denominatorReading"])
        self.assertIn("não é uma previsão oficial", projection["uncertaintyReading"])

        trend_migrated = _upgrade_legacy_attendance_projection(
            {
                "indicatorId": "pre_escola",
                "projection": {"modelReading": "Texto legado."},
            }
        )
        self.assertIn(
            "tendência estadual amortecida",
            trend_migrated["projection"]["modelReading"],
        )

    def test_staging_is_atomic_deterministic_and_never_targets_public_data(self):
        with self.assertRaisesRegex(ValueError, "public/data"):
            validate_staging_output_path(
                REPO_ROOT / "public" / "data" / "pne-v3"
            )
        with tempfile.TemporaryDirectory(
            prefix="pne-v3-test-", dir=REPO_ROOT
        ) as temporary_root:
            root = Path(temporary_root)
            left = write_staging(root / "left", self.prepared)
            right = write_staging(root / "right", self.prepared)
            compare_staging_directories(left, right)
            hashes = staging_hashes(left)
            self.assertEqual(len(hashes), 498)
            self.assertIn("manifest.json", hashes)
            self.assertEqual(
                sum(path.startswith("municipalities/") for path in hashes),
                497,
            )
            self.assertEqual(
                hashes["manifest.json"],
                staging_hashes(right)["manifest.json"],
            )


if __name__ == "__main__":
    unittest.main()
