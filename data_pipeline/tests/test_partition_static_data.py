from __future__ import annotations

import importlib.util
import json
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

    def test_municipal_partition_writes_only_index_and_details(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_root = root / "source"
            output_root = root / "static_partitioned"
            source_root.mkdir()
            (source_root / "indicadores.json").write_text("{}\n", encoding="utf-8")
            municipalities = {"Aceguá": "4300034", "Água Santa": "4300059"}
            payloads = {
                "municipios": {
                    "generated_at": "2026-08-01T00:00:00+00:00",
                    "municipios": list(municipalities),
                },
                "indicator_details": {
                    "municipios": {
                        name: {"indicator_details": {"sample": {"title": name}}}
                        for name in municipalities
                    }
                },
                "fundeb": {},
            }
            argv = [
                "partition_static_data.py",
                "--source-dir",
                str(source_root),
                "--output-dir",
                str(output_root),
            ]

            with (
                patch.object(sys, "argv", argv),
                patch.object(partition, "PIPELINE_EXPORT_DIR", output_root.parent),
                patch.object(partition, "EXPECTED_MUNICIPALITIES", len(municipalities)),
                patch.object(partition, "load_aggregate_payloads", return_value=payloads),
                patch.object(partition, "validate_fundeb_payload"),
                patch.object(partition, "validate_pnate_payload"),
                patch.object(partition, "validate_planning_scenarios_payload"),
                patch.object(
                    partition,
                    "extract_fundeb_id",
                    side_effect=lambda _payload, name: municipalities[name],
                ),
                patch.object(
                    partition,
                    "build_municipio_payload",
                    side_effect=lambda _payloads, name, slug, municipality_id: {
                        "id_municipio": municipality_id,
                        "municipio": name,
                        "slug": slug,
                    },
                ),
            ):
                self.assertEqual(partition.main(), 0)

            registry = json.loads(
                (output_root / "municipios_index.json").read_text(encoding="utf-8")
            )
            self.assertEqual(registry["total_municipios"], len(municipalities))
            for municipality_id in municipalities.values():
                files = {
                    path.name
                    for path in (output_root / "municipios" / municipality_id).iterdir()
                }
                self.assertEqual(files, {"index.json", "details.json"})


if __name__ == "__main__":
    unittest.main()
