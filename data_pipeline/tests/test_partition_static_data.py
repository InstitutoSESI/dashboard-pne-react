from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


PIPELINE_ROOT = Path(__file__).resolve().parents[1]
PARTITION_SPEC = importlib.util.spec_from_file_location(
    "partition_static_data_publication",
    PIPELINE_ROOT / "scripts" / "partition_static_data.py",
)
partition = importlib.util.module_from_spec(PARTITION_SPEC)
assert PARTITION_SPEC.loader is not None
sys.modules[PARTITION_SPEC.name] = partition
PARTITION_SPEC.loader.exec_module(partition)


class PartitionStaticDataPublicationTests(unittest.TestCase):
    def test_internal_municipality_aggregate_is_not_copied_to_public_staging(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_root = root / "source"
            output_root = root / "partitioned"
            source_root.mkdir()
            output_root.mkdir()
            (source_root / "municipios.json").write_text("internal\n", encoding="utf-8")
            (source_root / "indicadores.json").write_text("indicators\n", encoding="utf-8")
            (output_root / "municipios.json").write_text("legacy\n", encoding="utf-8")
            stats = {"created": 0, "updated": 0, "preserved": 0, "removed": 0}
            expected_paths: set[Path] = set()

            with (
                patch.object(partition, "SOURCE_DIR", source_root),
                patch.object(partition, "OUTPUT_DIR", output_root),
            ):
                partition.copy_root_static_files(stats, expected_paths)
                partition.remove_orphan_json_files(output_root, expected_paths, stats)

            self.assertTrue((source_root / "municipios.json").is_file())
            self.assertFalse((output_root / "municipios.json").exists())
            self.assertEqual(
                (output_root / "indicadores.json").read_text(encoding="utf-8"),
                "indicators\n",
            )


if __name__ == "__main__":
    unittest.main()
