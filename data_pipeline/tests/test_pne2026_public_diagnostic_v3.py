from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from data_pipeline.scripts.materialize_pne2026_public_diagnostic_v3 import (
    _apply_published_state_references,
    _bootstrap_cycle_methodology_results,
    compare_staging_directories,
    prepare_staging,
    staging_hashes,
    validate_staging_output_path,
    write_staging,
)
from data_pipeline.src.pne2026_public_diagnostic_v3 import (
    CONTRACT_HASH,
    PRESENTATION_POLICY_HASH,
    PUBLIC_V3_SCHEMA_VERSION,
    Pne2026PublicDiagnosticV3Error,
    validate_pne2026_public_diagnostic_v3,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
PUBLICATION_ROOT = REPO_ROOT / "public" / "data" / "pne2026-diagnostic-v3"


class CycleBootstrapTest(unittest.TestCase):
    def test_only_repairs_missing_or_no_observation_from_available_cycle_data(
        self,
    ):
        active_payload = {
            "results": [
                {
                    "relationId": "relation.1.a.creche",
                    "dataStatus": "unavailable",
                    "reasonCode": "no_observation",
                },
                {
                    "relationId": "relation.1.c.pre_escola",
                    "dataStatus": "suppressed",
                    "reasonCode": "small_numbers",
                },
                {
                    "relationId": "relation.8.b.salas_climatizadas",
                    "dataStatus": "unavailable",
                    "reasonCode": "source_unavailable",
                },
            ]
        }
        cycle_indicators = {
            "creche": {
                "available": True,
                "end_year": 2025,
                "end_value": 0,
                "distance": -60,
                "display": {
                    "status": "Meta não atingida",
                    "interpretation": "Observação zero preservada.",
                },
            },
            "pre_escola": {
                "available": True,
                "end_year": 2025,
                "end_value": 80,
                "distance": -20,
            },
            "basico_6_17": {
                "available": True,
                "end_year": 2025,
                "end_value": 100,
                "distance": 0,
            },
            "salas_climatizadas": {
                "available": True,
                "end_year": 2025,
                "end_value": 50,
                "distance": -50,
            },
            "idade_regular_quinto": {"available": False},
        }

        results = _bootstrap_cycle_methodology_results(
            active_payload,
            cycle_indicators,
        )

        self.assertEqual(
            set(results),
            {"relation.1.a.creche", "relation.4.a.basico_6_17"},
        )
        self.assertEqual(results["relation.1.a.creche"]["value"], 0.0)
        self.assertEqual(results["relation.1.a.creche"]["year"], 2025)
        self.assertEqual(
            results["relation.1.a.creche"]["classification"],
            "advance",
        )
        self.assertEqual(
            results["relation.1.a.creche"]["publicReading"],
            "Observação zero preservada.",
        )
        self.assertEqual(
            results["relation.4.a.basico_6_17"]["classification"],
            "maintain",
        )

    def test_available_cycle_result_fails_closed_when_distance_is_missing(self):
        with self.assertRaisesRegex(RuntimeError, "distância finita"):
            _bootstrap_cycle_methodology_results(
                {"results": []},
                {
                    "creche": {
                        "available": True,
                        "end_year": 2025,
                        "end_value": 42,
                    }
                },
            )


class PublishedStateReferenceTest(unittest.TestCase):
    def test_adds_exact_comparable_point_and_preserves_existing_comparison(self):
        payload = {
            "results": [
                {
                    "relationId": "relation.1.a.creche",
                    "indicatorId": "creche",
                    "dataStatus": "available",
                    "year": 2025,
                    "value": 48.5,
                },
                {
                    "relationId": "relation.1.c.pre_escola",
                    "indicatorId": "pre_escola",
                    "dataStatus": "available",
                    "year": 2025,
                    "value": 95.0,
                    "stateComparison": {"preserved": True},
                },
            ]
        }
        supplemented = _apply_published_state_references(
            payload,
            {
                ("creche", 2025): {"unit": "percent", "value": 38.1},
                ("pre_escola", 2025): {"unit": "percent", "value": 89.7},
            },
        )

        self.assertEqual(supplemented, ["relation.1.a.creche"])
        comparison = payload["results"][0]["stateComparison"]
        self.assertEqual(comparison["state"], "above")
        self.assertEqual(comparison["municipalityValue"], 48.5)
        self.assertEqual(comparison["stateValue"], 38.1)
        self.assertAlmostEqual(comparison["difference"], 10.4)
        self.assertEqual(
            payload["results"][1]["stateComparison"],
            {"preserved": True},
        )

    def test_keeps_missing_or_incompatible_reference_explicitly_absent(self):
        payload = {
            "results": [
                {
                    "relationId": "relation.1.a.creche",
                    "indicatorId": "creche",
                    "dataStatus": "available",
                    "year": 2025,
                    "value": 48.5,
                }
            ]
        }

        supplemented = _apply_published_state_references(payload, {})

        self.assertEqual(supplemented, [])
        self.assertNotIn("stateComparison", payload["results"][0])


class Pne2026PublicDiagnosticV3Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.current = json.loads(
            (PUBLICATION_ROOT / "current.json").read_text(encoding="utf-8")
        )
        cls.release_root = (
            PUBLICATION_ROOT / "releases" / cls.current["releaseId"]
        )
        cls.prepared = prepare_staging()
        cls.manifest = cls.prepared["manifest"]
        cls.payload_by_id = {
            payload["municipality"]["id"]: payload
            for payload in cls.prepared["payloads"]
        }
        cls.acegua = cls.payload_by_id["4300034"]

    def test_schema_hashes_and_summary_are_canonical(self):
        self.assertEqual(self.acegua["schemaVersion"], PUBLIC_V3_SCHEMA_VERSION)
        self.assertEqual(self.acegua["contractVersion"], "1.9.0")
        self.assertEqual(self.acegua["contractHash"], CONTRACT_HASH)
        self.assertEqual(self.acegua["presentationPolicyVersion"], "1.7.0")
        self.assertEqual(
            self.acegua["presentationPolicyHash"], PRESENTATION_POLICY_HASH
        )
        self.assertEqual(len(self.acegua["results"]), 51)
        self.assertEqual(
            sum(self.acegua["summary"][key] for key in (
                "progressResultCount",
                "trackingResultCount",
                "complementaryResultCount",
            )),
            51,
        )

    def test_complete_generation_matches_the_active_publication(self):
        self.assertEqual(self.manifest["generatedMunicipalityCount"], 497)
        self.assertEqual(self.manifest["totalResultCount"], 25347)
        self.assertEqual(
            self.manifest["modeCounts"],
            {"progress": 13419, "tracking": 7455, "complementary": 4473},
        )
        self.assertEqual(self.manifest["minimumResultsPerMunicipality"], 51)
        self.assertEqual(self.manifest["maximumResultsPerMunicipality"], 51)
        self.assertEqual(self.manifest["duplicateRelationCount"], 0)
        self.assertEqual(self.manifest["invalidFileCount"], 0)
        self.assertEqual(self.manifest["hiddenExcludedCount"], 0)
        self.assertEqual(
            self.manifest["generationHash"], self.current["releaseId"]
        )

        for municipality_id, generated in self.payload_by_id.items():
            published = json.loads(
                (
                    self.release_root
                    / "municipios"
                    / f"{municipality_id}.json"
                ).read_text(encoding="utf-8")
            )
            self.assertEqual(generated, published, municipality_id)

    def test_validator_rejects_unknown_fields_and_identity_mismatches(self):
        unknown_field = deepcopy(self.acegua)
        unknown_field["results"][0]["relationshipType"] = "direct"
        with self.assertRaisesRegex(
            Pne2026PublicDiagnosticV3Error, "campos desconhecidos"
        ):
            validate_pne2026_public_diagnostic_v3(unknown_field)

        bad_hash = deepcopy(self.acegua)
        bad_hash["contractHash"] = "0" * 64
        with self.assertRaisesRegex(
            Pne2026PublicDiagnosticV3Error, "contractHash"
        ):
            validate_pne2026_public_diagnostic_v3(bad_hash)

        mismatched = deepcopy(self.acegua)
        mismatched["results"][0]["goalId"] = "1.c"
        with self.assertRaisesRegex(
            Pne2026PublicDiagnosticV3Error, "identidade canônica"
        ):
            validate_pne2026_public_diagnostic_v3(mismatched)

    def test_summary_is_recomputed_from_results(self):
        invalid = deepcopy(self.acegua)
        invalid["summary"]["progressResultCount"] += 1
        with self.assertRaisesRegex(Pne2026PublicDiagnosticV3Error, "summary"):
            validate_pne2026_public_diagnostic_v3(invalid)

    def test_staging_is_atomic_deterministic_and_outside_public_data(self):
        with self.assertRaises(ValueError):
            validate_staging_output_path(REPO_ROOT / "public" / "data" / "x")
        with self.assertRaises(ValueError):
            validate_staging_output_path(REPO_ROOT)

        with tempfile.TemporaryDirectory(
            prefix="pne-current-staging-", dir=REPO_ROOT
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


if __name__ == "__main__":
    unittest.main()
