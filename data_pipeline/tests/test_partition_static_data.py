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

from src.municipality_registry import (  # noqa: E402
    MunicipalityRegistryError,
    load_municipality_registry,
)
from src.state_config import StateConfig  # noqa: E402


class PartitionStaticDataPublicationTests(unittest.TestCase):
    records = (
        ("4300034", "Aceguá", "acegua"),
        ("4300059", "Água Santa", "agua-santa"),
    )

    @classmethod
    def _registry(cls, root: Path, records=None):
        records = records or cls.records
        state = StateConfig(
            schema_version="state-config-v1",
            state_code="RS",
            state_name="Rio Grande do Sul",
            municipality_ibge_prefix="43",
            expected_municipality_count=len(records),
            locale="pt-BR",
        )
        path = root / "registry.json"
        path.write_text(
            json.dumps(
                {
                    "schemaVersion": "municipality-registry-v1",
                    "stateCode": "RS",
                    "municipalityCount": len(records),
                    "municipalities": [
                        {"ibgeCode": code, "name": name, "slug": slug}
                        for code, name, slug in records
                    ],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        return state, load_municipality_registry(state, registry_path=path)

    @staticmethod
    def _payloads(names: list[str]) -> dict:
        empty_by_name = {name: {} for name in names}
        return {
            "municipios": {
                "generated_at": "2026-08-01T00:00:00+00:00",
                "municipios": names,
            },
            "indicadores": {},
            "indicator_details": {
                "municipios": {
                    name: {"indicator_details": {"sample": {"title": name}}}
                    for name in names
                }
            },
            "fundeb": {"municipios": {name: {"fundeb": None} for name in names}},
            "pnate": {"municipios": {name: {"pnate": None} for name in names}},
            "pne_2014_2024_indicadores": {"municipios": empty_by_name},
            "pne_2014_2024_rankings": {"municipios": empty_by_name},
            "pne_2026_2036_indicadores": {"municipios": empty_by_name},
            "pne_2026_2036_rankings": {"municipios": empty_by_name},
            "projecoes": {"municipios": empty_by_name},
            "planning_scenarios": {"municipios": empty_by_name},
            "education_attendance": {"municipios": empty_by_name},
        }

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
            state, registry = self._registry(root)
            payloads = self._payloads(["Água Santa", "Aceguá"])
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
                patch.object(partition, "load_state_config", return_value=state),
                patch.object(partition, "load_municipality_registry", return_value=registry),
                patch.object(partition, "load_aggregate_payloads", return_value=payloads),
                patch.object(partition, "validate_fundeb_payload"),
                patch.object(partition, "validate_pnate_payload"),
                patch.object(partition, "validate_planning_scenarios_payload"),
            ):
                self.assertEqual(partition.main(), 0)

            registry = json.loads(
                (output_root / "municipios_index.json").read_text(encoding="utf-8")
            )
            self.assertEqual(registry["total_municipios"], 2)
            self.assertEqual(
                [entry["id_municipio"] for entry in registry["municipios"]],
                ["4300034", "4300059"],
            )
            self.assertEqual(
                [entry["slug"] for entry in registry["municipios"]],
                ["acegua", "agua-santa"],
            )
            for municipality_id, _name, _slug in self.records:
                files = {
                    path.name
                    for path in (output_root / "municipios" / municipality_id).iterdir()
                }
                self.assertEqual(files, {"index.json", "details.json"})

    def test_identity_comes_from_registry_even_without_or_with_divergent_fundeb_id(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _state, registry = self._registry(root)
            record = registry.get_by_id("4300034")
            payloads = self._payloads(["Aceguá", "Água Santa"])
            payloads["fundeb"]["municipios"]["Aceguá"] = {
                "fundeb": {
                    "resumo_ultimo_ano": {"id_municipio": "9999999"},
                    "historico": [{"id_municipio": "4200035"}],
                }
            }

            built = partition.build_municipio_payload(payloads, "Aceguá", record)
            self.assertEqual(built["id_municipio"], "4300034")
            self.assertEqual(built["municipio"], "Aceguá")
            self.assertEqual(built["slug"], "acegua")

            payloads["fundeb"]["municipios"]["Aceguá"] = {
                "fundeb": {"resumo_ultimo_ano": {}, "historico": []}
            }
            without_id = partition.build_municipio_payload(payloads, "Aceguá", record)
            self.assertEqual(without_id["id_municipio"], "4300034")

    def test_aggregate_missing_extra_and_ambiguous_names_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _state, registry = self._registry(root)
            with self.assertRaisesRegex(RuntimeError, "diverge do registro"):
                partition.resolve_aggregate_municipalities(
                    {"municipios": ["Aceguá"]}, registry
                )
            with self.assertRaisesRegex(RuntimeError, "não resolvido"):
                partition.resolve_aggregate_municipalities(
                    {"municipios": ["Aceguá", "Município extra"]}, registry
                )

            _state, ambiguous = self._registry(
                root,
                records=(
                    ("4300034", "Água", "agua-acento"),
                    ("4300059", "Agua", "agua-sem-acento"),
                ),
            )
            with self.assertRaisesRegex(RuntimeError, "ambíguo"):
                partition.resolve_aggregate_municipalities(
                    {"municipios": ["AGUA", "Água"]}, ambiguous
                )

    def test_invalid_registry_fails_before_output_directory_is_created(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_root = root / "source"
            output_root = root / "partitioned"
            source_root.mkdir()
            state, _registry = self._registry(root)
            argv = [
                "partition_static_data.py",
                "--source-dir",
                str(source_root),
                "--output-dir",
                str(output_root),
            ]
            with (
                patch.object(sys, "argv", argv),
                patch.object(partition, "load_state_config", return_value=state),
                patch.object(
                    partition,
                    "load_municipality_registry",
                    side_effect=MunicipalityRegistryError("registro inválido"),
                ),
            ):
                with self.assertRaisesRegex(MunicipalityRegistryError, "registro inválido"):
                    partition.main()
            self.assertFalse(output_root.exists())

    def test_partition_source_has_no_slug_or_fundeb_identity_fallback(self) -> None:
        source = (PIPELINE_ROOT / "scripts" / "partition_static_data.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("extract_fundeb_id", source)
        self.assertNotIn("def slugify", source)
        self.assertNotIn("def unique_slugs", source)
        self.assertNotIn("id_municipio or slug", source)

    def test_planning_validation_delegates_to_the_public_contract_validator(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _state, registry = self._registry(root)
            names = ["Aceguá", "Água Santa"]
            payload = {"contractVersion": "planning-scenarios-v1"}
            with patch.object(
                partition,
                "validate_public_planning_scenarios",
            ) as validate:
                partition.validate_planning_scenarios_payload(
                    {"planning_scenarios": payload},
                    names,
                    registry,
                )

            validate.assert_called_once_with(payload, names)


if __name__ == "__main__":
    unittest.main()
