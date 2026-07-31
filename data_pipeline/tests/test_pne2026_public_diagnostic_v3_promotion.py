from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from data_pipeline.scripts.materialize_pne2026_public_diagnostic_v3 import (
    prepare_staging,
)
from data_pipeline.scripts import promote_pne2026_public_diagnostic_v3 as promotion


REPO_ROOT = Path(__file__).resolve().parents[2]


class Pne2026PublicDiagnosticV3PromotionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prepared = prepare_staging()

    def _source(self, root: Path) -> Path:
        source = root / "source"
        source.mkdir()
        for relative_path, content in sorted(
            self.prepared["contents"].items()
        ):
            output = source / relative_path
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(content)
        return source

    def test_staging_and_release_share_the_normalized_semantic_hash(self):
        with tempfile.TemporaryDirectory(
            prefix="pne-v3-semantics-", dir=REPO_ROOT
        ) as temporary_root:
            validated = promotion.validate_source_package(
                self._source(Path(temporary_root))
            )
            source_hash = promotion.semantic_manifest_hash(
                validated["sourceManifest"], source_kind="staging"
            )
            release_hash = promotion.semantic_manifest_hash(
                validated["releaseManifest"], source_kind="release"
            )
            self.assertEqual(source_hash, release_hash)
            self.assertEqual(
                validated["releaseManifest"]["semanticHash"], source_hash
            )
            self.assertEqual(
                validated["releaseId"],
                validated["sourceManifest"]["generationHash"],
            )

    def test_check_is_read_only_and_wrong_destinations_are_blocked(self):
        with tempfile.TemporaryDirectory(
            prefix="pne-v3-check-", dir=REPO_ROOT
        ) as temporary_root:
            root = Path(temporary_root)
            source = self._source(root)
            destination = root / "public-v3"
            with patch.object(
                promotion, "PUBLIC_V3_DIR", destination.resolve()
            ):
                report = promotion.promote(source, destination, check=True)
            self.assertEqual(report["mode"], "check")
            self.assertFalse(destination.exists())
            with self.assertRaisesRegex(ValueError, "Destino bloqueado"):
                promotion.validate_public_destination(
                    REPO_ROOT / "public" / "data" / "municipios"
                )

    def test_release_is_immutable_current_is_minimal_and_repromotion_validates(self):
        with tempfile.TemporaryDirectory(
            prefix="pne-v3-immutable-", dir=REPO_ROOT
        ) as temporary_root:
            root = Path(temporary_root)
            source = self._source(root)
            destination = root / "public-v3"
            with patch.object(
                promotion, "PUBLIC_V3_DIR", destination.resolve()
            ):
                first = promotion.promote(source, destination)
                release_root = (
                    destination / "releases" / first["releaseId"]
                )
                before = {
                    path.relative_to(release_root).as_posix(): path.read_bytes()
                    for path in release_root.rglob("*")
                    if path.is_file()
                }
                second = promotion.promote(source, destination)
                after = {
                    path.relative_to(release_root).as_posix(): path.read_bytes()
                    for path in release_root.rglob("*")
                    if path.is_file()
                }
                active = promotion.validate_public_package(destination)
            self.assertEqual(first["releaseId"], second["releaseId"])
            self.assertEqual(before, after)
            self.assertEqual(active["fileCount"], 498)
            current = json.loads(
                (destination / "current.json").read_text(encoding="utf-8")
            )
            self.assertEqual(set(current), promotion.POINTER_FIELDS)
            self.assertEqual(current["releaseId"], first["releaseId"])
            self.assertEqual(
                current["manifestPath"],
                f"releases/{first['releaseId']}/manifest.json",
            )
            self.assertFalse((destination / "manifest.json").exists())

    def test_existing_release_with_same_hash_and_different_bytes_is_rejected(self):
        with tempfile.TemporaryDirectory(
            prefix="pne-v3-conflict-", dir=REPO_ROOT
        ) as temporary_root:
            root = Path(temporary_root)
            source = self._source(root)
            destination = root / "public-v3"
            with patch.object(
                promotion, "PUBLIC_V3_DIR", destination.resolve()
            ):
                report = promotion.promote(source, destination)
                municipal = next(
                    (
                        destination
                        / "releases"
                        / report["releaseId"]
                        / "municipios"
                    ).glob("*.json")
                )
                municipal.write_bytes(municipal.read_bytes() + b" ")
                with self.assertRaises(ValueError):
                    promotion.promote(source, destination)

    def test_failed_pointer_replace_preserves_the_previous_pointer(self):
        with tempfile.TemporaryDirectory(
            prefix="pne-v3-pointer-failure-", dir=REPO_ROOT
        ) as temporary_root:
            destination = Path(temporary_root) / "public-v3"
            destination.mkdir()
            current = destination / "current.json"
            previous = b'{"previous":true}\n'
            current.write_bytes(previous)
            release_id = "a" * 64
            pointer = {
                "schemaVersion": promotion.POINTER_SCHEMA,
                "releaseId": release_id,
                "manifestPath": f"releases/{release_id}/manifest.json",
                "aggregateHash": release_id,
                "contractVersion": promotion.CONTRACT_VERSION,
                "contractHash": promotion.CONTRACT_HASH,
                "presentationPolicyVersion": promotion.PRESENTATION_POLICY_VERSION,
                "presentationPolicyHash": promotion.PRESENTATION_POLICY_HASH,
            }
            with (
                patch.object(
                    promotion,
                    "validate_current_pointer",
                    return_value={},
                ),
                patch.object(
                    promotion.os,
                    "replace",
                    side_effect=PermissionError("blocked"),
                ),
            ):
                with self.assertRaises(PermissionError):
                    promotion._write_current_atomically(destination, pointer)
            self.assertEqual(current.read_bytes(), previous)

    def test_pointer_rollback_between_two_fixture_releases_is_reversible(self):
        with tempfile.TemporaryDirectory(
            prefix="pne-v3-rollback-", dir=REPO_ROOT
        ) as temporary_root:
            destination = Path(temporary_root) / "public-v3"
            destination.mkdir()
            release_ids = ("a" * 64, "b" * 64)

            def fake_release(root: Path):
                release_id = root.name
                return {
                    "releaseId": release_id,
                    "semanticHash": "c" * 64,
                    "manifest": {
                        "aggregateHash": release_id,
                        "contractVersion": promotion.CONTRACT_VERSION,
                        "contractHash": promotion.CONTRACT_HASH,
                        "presentationPolicyVersion": (
                            promotion.PRESENTATION_POLICY_VERSION
                        ),
                        "presentationPolicyHash": (
                            promotion.PRESENTATION_POLICY_HASH
                        ),
                    },
                }

            def fake_active(root: Path):
                pointer = json.loads(
                    (root / "current.json").read_text(encoding="utf-8")
                )
                return {"releaseId": pointer["releaseId"]}

            with (
                patch.object(
                    promotion, "PUBLIC_V3_DIR", destination.resolve()
                ),
                patch.object(
                    promotion,
                    "validate_release_package",
                    side_effect=fake_release,
                ),
                patch.object(
                    promotion,
                    "validate_current_pointer",
                    return_value={},
                ),
                patch.object(
                    promotion,
                    "validate_public_package",
                    side_effect=fake_active,
                ),
            ):
                promotion.activate_release(release_ids[0], destination)
                promotion.activate_release(release_ids[1], destination)
                final = promotion.activate_release(
                    release_ids[0], destination
                )
            self.assertEqual(final["releaseId"], release_ids[0])
            self.assertEqual(
                json.loads(
                    (destination / "current.json").read_text(encoding="utf-8")
                )["releaseId"],
                release_ids[0],
            )


if __name__ == "__main__":
    unittest.main()
