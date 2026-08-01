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


class Pne2026PublicDiagnosticPromotionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.prepared = prepare_staging()

    def _source(self, root: Path) -> Path:
        source = root / "source"
        source.mkdir()
        for relative_path, content in sorted(self.prepared["contents"].items()):
            output = source / relative_path
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(content)
        return source

    def test_staging_and_release_share_the_semantic_hash(self):
        with tempfile.TemporaryDirectory(
            prefix="pne-publication-semantics-", dir=REPO_ROOT
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
            self.assertEqual(validated["releaseManifest"]["semanticHash"], source_hash)
            self.assertEqual(
                validated["releaseId"],
                validated["sourceManifest"]["generationHash"],
            )

    def test_check_is_read_only_and_wrong_destinations_are_blocked(self):
        with tempfile.TemporaryDirectory(
            prefix="pne-publication-check-", dir=REPO_ROOT
        ) as temporary_root:
            root = Path(temporary_root)
            source = self._source(root)
            destination = root / "publication"
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

    def test_promotion_keeps_only_the_active_release(self):
        with tempfile.TemporaryDirectory(
            prefix="pne-publication-prune-", dir=REPO_ROOT
        ) as temporary_root:
            root = Path(temporary_root)
            source = self._source(root)
            destination = root / "publication"
            with patch.object(
                promotion, "PUBLIC_V3_DIR", destination.resolve()
            ):
                first = promotion.promote(source, destination)
                inactive = destination / "releases" / ("a" * 64)
                inactive.mkdir()
                (inactive / "obsolete.json").write_text("{}", encoding="utf-8")
                second = promotion.promote(source, destination)
                active = promotion.validate_public_package(destination)

            self.assertEqual(first["releaseId"], second["releaseId"])
            self.assertEqual(second["inactiveReleaseCount"], 1)
            self.assertFalse(inactive.exists())
            self.assertEqual(active["fileCount"], 498)
            release_names = [
                path.name for path in (destination / "releases").iterdir()
            ]
            self.assertEqual(release_names, [first["releaseId"]])
            current = json.loads(
                (destination / "current.json").read_text(encoding="utf-8")
            )
            self.assertEqual(set(current), promotion.POINTER_FIELDS)
            self.assertEqual(current["releaseId"], first["releaseId"])

    def test_existing_release_with_same_hash_and_different_bytes_is_rejected(self):
        with tempfile.TemporaryDirectory(
            prefix="pne-publication-conflict-", dir=REPO_ROOT
        ) as temporary_root:
            root = Path(temporary_root)
            source = self._source(root)
            destination = root / "publication"
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
            prefix="pne-publication-pointer-", dir=REPO_ROOT
        ) as temporary_root:
            destination = Path(temporary_root) / "publication"
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
                patch.object(promotion, "validate_current_pointer", return_value={}),
                patch.object(
                    promotion.os,
                    "replace",
                    side_effect=PermissionError("blocked"),
                ),
            ):
                with self.assertRaises(PermissionError):
                    promotion._write_current_atomically(destination, pointer)
            self.assertEqual(current.read_bytes(), previous)


if __name__ == "__main__":
    unittest.main()
