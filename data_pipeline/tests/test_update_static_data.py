from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

from data_pipeline.src.config import (
    MUNICIPAL_FINANCE_EXPORT_DIR,
    STATIC_PARTITIONED_DATA_DIR,
)


PIPELINE_ROOT = Path(__file__).resolve().parents[1]
UPDATE_SPEC = importlib.util.spec_from_file_location(
    "update_static_data",
    PIPELINE_ROOT / "scripts" / "update_static_data.py",
)
update = importlib.util.module_from_spec(UPDATE_SPEC)
assert UPDATE_SPEC.loader is not None
sys.modules[UPDATE_SPEC.name] = update
UPDATE_SPEC.loader.exec_module(update)


class StaticDataSyncTests(unittest.TestCase):
    municipality_ids = ("4300034", "4300059")

    @staticmethod
    def write(path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def build_complete_source(self, root: Path) -> None:
        for filename in update.ROOT_STATIC_FILES:
            self.write(root / filename, f"source:{filename}\n")
        for relative in update.CYCLE_STATIC_FILES:
            self.write(root / relative, f"source:{relative}\n")
        for municipality_id in self.municipality_ids:
            for filename in update.MUNICIPAL_STATIC_FILES:
                self.write(
                    root / "municipios" / municipality_id / filename,
                    f"source:{municipality_id}:{filename}\n",
                )

    def test_pipeline_staging_roots_are_isolated_by_domain(self) -> None:
        self.assertNotEqual(STATIC_PARTITIONED_DATA_DIR, MUNICIPAL_FINANCE_EXPORT_DIR)
        self.assertEqual(STATIC_PARTITIONED_DATA_DIR.name, "static_partitioned")
        self.assertEqual(MUNICIPAL_FINANCE_EXPORT_DIR.name, "municipal_finance")

    def test_public_root_contract_excludes_retired_municipality_catalog(self) -> None:
        self.assertNotIn("municipios.json", update.ROOT_STATIC_FILES)
        self.assertIn("municipios.json", update.RETIRED_PUBLIC_ROOT_FILES)
        self.assertFalse(update.is_managed_static_path(Path("municipios.json")))

    def test_sync_updates_only_the_static_contract_it_owns(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            source_root = base / "static_partitioned"
            public_root = base / "public" / "data"
            public_root.mkdir(parents=True)
            self.build_complete_source(source_root)

            unrelated = {
                public_root / "educacao" / "index.json": "education\n",
                public_root / "financeiro" / "catalogos.json": "finance\n",
                public_root / "pne2026-diagnostic-v3" / "current.json": "v3\n",
                public_root / "municipios" / self.municipality_ids[0] / "financeiro.json": "finance\n",
                public_root / "municipios" / self.municipality_ids[0] / "qse-anual.json": "qse\n",
            }
            for path, content in unrelated.items():
                self.write(path, content)

            retired_catalog = public_root / "municipios.json"
            self.write(retired_catalog, "outdated\n")
            orphan = public_root / "municipios" / "legacy-slug" / "index.json"
            self.write(orphan, "obsolete\n")
            results: list[update.StepResult] = []

            stats = update.sync_partitioned_to_public(
                results,
                source_root=source_root,
                public_root=public_root,
                expected_municipalities=len(self.municipality_ids),
            )

            self.assertEqual(stats.removed, 2)
            self.assertEqual(stats.updated, 0)
            self.assertFalse(orphan.exists())
            self.assertFalse(retired_catalog.exists())
            self.assertEqual([result.name for result in results], ["sync"])
            for path, content in unrelated.items():
                self.assertEqual(path.read_text(encoding="utf-8"), content)
            for municipality_id in self.municipality_ids:
                for filename in update.MUNICIPAL_STATIC_FILES:
                    target = public_root / "municipios" / municipality_id / filename
                    self.assertTrue(target.is_file())

    def test_incomplete_staging_aborts_before_writing_public_data(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            source_root = base / "static_partitioned"
            public_root = base / "public" / "data"
            public_root.mkdir(parents=True)
            self.build_complete_source(source_root)
            (source_root / "municipios" / self.municipality_ids[0] / "details.json").unlink()
            public_catalog = public_root / "municipios_index.json"
            self.write(public_catalog, "published\n")

            with self.assertRaisesRegex(RuntimeError, "details.json"):
                update.sync_partitioned_to_public(
                    [],
                    source_root=source_root,
                    public_root=public_root,
                    expected_municipalities=len(self.municipality_ids),
                )

            self.assertEqual(public_catalog.read_text(encoding="utf-8"), "published\n")

    def test_retired_catalog_is_rejected_from_publication_staging(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source_root = Path(temporary) / "static_partitioned"
            self.build_complete_source(source_root)
            self.write(source_root / "municipios.json", "legacy\n")

            with self.assertRaisesRegex(RuntimeError, "fora do contrato"):
                update.validate_static_partition(
                    source_root,
                    expected_municipalities=len(self.municipality_ids),
                )

    def test_mixed_domain_staging_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            source_root = base / "static_partitioned"
            public_root = base / "public" / "data"
            public_root.mkdir(parents=True)
            self.build_complete_source(source_root)
            self.write(
                source_root / "municipios" / self.municipality_ids[0] / "financeiro.json",
                "finance\n",
            )

            with self.assertRaisesRegex(RuntimeError, "fora do contrato"):
                update.sync_partitioned_to_public(
                    [],
                    source_root=source_root,
                    public_root=public_root,
                    expected_municipalities=len(self.municipality_ids),
                )

    def test_different_municipal_sets_are_rejected_before_sync(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            source_root = base / "static_partitioned"
            public_root = base / "public" / "data"
            public_root.mkdir(parents=True)
            self.build_complete_source(source_root)
            displaced = source_root / "municipios" / "4300067" / "details.json"
            self.write(displaced, "displaced\n")
            (
                source_root
                / "municipios"
                / self.municipality_ids[0]
                / "details.json"
            ).unlink()

            with self.assertRaisesRegex(RuntimeError, "3 municipios; esperado 2"):
                update.sync_partitioned_to_public(
                    [],
                    source_root=source_root,
                    public_root=public_root,
                    expected_municipalities=len(self.municipality_ids),
                )


if __name__ == "__main__":
    unittest.main()
