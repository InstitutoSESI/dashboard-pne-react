from __future__ import annotations

import importlib.util
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

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

from src.municipality_registry import load_municipality_registry  # noqa: E402
from src.state_config import StateConfig  # noqa: E402


class StaticDataSyncTests(unittest.TestCase):
    municipality_records = (
        ("4300034", "Aceguá", "acegua"),
        ("4300059", "Água Santa", "agua-santa"),
    )
    municipality_ids = tuple(record[0] for record in municipality_records)

    @staticmethod
    def write(path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    @classmethod
    def registry(cls, root: Path):
        state = StateConfig(
            schema_version="state-config-v1",
            state_code="RS",
            state_name="Rio Grande do Sul",
            municipality_ibge_prefix="43",
            expected_municipality_count=len(cls.municipality_records),
            locale="pt-BR",
        )
        path = root / "municipality-registry.json"
        path.write_text(
            json.dumps(
                {
                    "schemaVersion": "municipality-registry-v1",
                    "stateCode": "RS",
                    "municipalityCount": len(cls.municipality_records),
                    "municipalities": [
                        {"ibgeCode": code, "name": name, "slug": slug}
                        for code, name, slug in cls.municipality_records
                    ],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        return state, load_municipality_registry(state, registry_path=path)

    @staticmethod
    def write_json(path: Path, payload: dict) -> None:
        StaticDataSyncTests.write(
            path,
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        )

    def build_complete_source(self, root: Path, registry) -> None:
        self.write_json(root / "indicadores.json", {})
        self.write_json(
            root / "municipios_index.json",
            registry.build_public_index_payload(
                generated_at="2026-08-01T00:00:00+00:00"
            ),
        )
        for relative in update.CYCLE_STATIC_FILES:
            self.write_json(root / relative, {})
        for record in registry.ordered_records:
            self.write_json(
                root / "municipios" / record.ibge_code / "index.json",
                {
                    "id_municipio": record.ibge_code,
                    "municipio": record.name,
                    "slug": record.slug,
                },
            )
            self.write_json(
                root / "municipios" / record.ibge_code / "details.json",
                {},
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
            _state, registry = self.registry(base)
            self.build_complete_source(source_root, registry)

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
            legacy_diagnostic = (
                public_root
                / "municipios"
                / self.municipality_ids[0]
                / "diagnostico.json"
            )
            self.write(legacy_diagnostic, "legacy\n")
            diagnostic_lookalike = legacy_diagnostic.with_name("diagnostico.json.bak")
            self.write(diagnostic_lookalike, "keep\n")
            results: list[update.StepResult] = []

            stats = update.sync_partitioned_to_public(
                results,
                source_root=source_root,
                public_root=public_root,
                registry=registry,
            )

            self.assertEqual(stats.removed, 3)
            self.assertEqual(stats.updated, 0)
            self.assertFalse(orphan.exists())
            self.assertTrue(orphan.parent.is_dir())
            self.assertFalse(retired_catalog.exists())
            self.assertFalse(legacy_diagnostic.exists())
            self.assertEqual(diagnostic_lookalike.read_text(encoding="utf-8"), "keep\n")
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
            _state, registry = self.registry(base)
            self.build_complete_source(source_root, registry)
            (source_root / "municipios" / self.municipality_ids[0] / "details.json").unlink()
            public_catalog = public_root / "municipios_index.json"
            self.write(public_catalog, "published\n")

            with self.assertRaisesRegex(RuntimeError, "details.json"):
                update.sync_partitioned_to_public(
                    [],
                    source_root=source_root,
                    public_root=public_root,
                    registry=registry,
                )

            self.assertEqual(public_catalog.read_text(encoding="utf-8"), "published\n")

    def test_retired_catalog_is_rejected_from_publication_staging(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            source_root = base / "static_partitioned"
            _state, registry = self.registry(base)
            self.build_complete_source(source_root, registry)
            self.write(source_root / "municipios.json", "legacy\n")

            with self.assertRaisesRegex(RuntimeError, "fora do contrato"):
                update.validate_static_partition(
                    source_root,
                    registry,
                )

    def test_legacy_diagnostic_is_rejected_from_publication_staging(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            source_root = base / "static_partitioned"
            _state, registry = self.registry(base)
            self.build_complete_source(source_root, registry)
            self.write(
                source_root
                / "municipios"
                / self.municipality_ids[0]
                / "diagnostico.json",
                "legacy\n",
            )

            with self.assertRaisesRegex(RuntimeError, "fora do contrato"):
                update.validate_static_partition(
                    source_root,
                    registry,
                )

    def test_mixed_domain_staging_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            source_root = base / "static_partitioned"
            public_root = base / "public" / "data"
            public_root.mkdir(parents=True)
            _state, registry = self.registry(base)
            self.build_complete_source(source_root, registry)
            self.write(
                source_root / "municipios" / self.municipality_ids[0] / "financeiro.json",
                "finance\n",
            )

            with self.assertRaisesRegex(RuntimeError, "fora do contrato"):
                update.sync_partitioned_to_public(
                    [],
                    source_root=source_root,
                    public_root=public_root,
                    registry=registry,
                )

    def test_different_municipal_sets_are_rejected_before_sync(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            source_root = base / "static_partitioned"
            public_root = base / "public" / "data"
            public_root.mkdir(parents=True)
            _state, registry = self.registry(base)
            self.build_complete_source(source_root, registry)
            shutil.rmtree(source_root / "municipios" / self.municipality_ids[0])
            self.write_json(
                source_root / "municipios" / "4300067" / "index.json",
                {
                    "id_municipio": "4300067",
                    "municipio": "Município deslocado",
                    "slug": "municipio-deslocado",
                },
            )
            self.write_json(
                source_root / "municipios" / "4300067" / "details.json",
                {},
            )

            with self.assertRaisesRegex(
                RuntimeError,
                "Conjunto municipal.*ausentes=.*4300034.*extras=.*4300067",
            ):
                update.sync_partitioned_to_public(
                    [],
                    source_root=source_root,
                    public_root=public_root,
                    registry=registry,
                )

    def test_slug_directory_and_divergent_index_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            source_root = base / "static_partitioned"
            _state, registry = self.registry(base)
            self.build_complete_source(source_root, registry)
            self.write_json(source_root / "municipios" / "acegua" / "index.json", {})
            with self.assertRaisesRegex(RuntimeError, "fora do contrato"):
                update.validate_static_partition(source_root, registry)

            shutil.rmtree(source_root / "municipios" / "acegua")
            index_path = source_root / "municipios_index.json"
            index = json.loads(index_path.read_text(encoding="utf-8"))
            index["municipios"][0]["slug"] = "slug-divergente"
            self.write_json(index_path, index)
            with self.assertRaisesRegex(RuntimeError, "diverge da projeção"):
                update.validate_static_partition(source_root, registry)

    def test_education_only_keeps_the_embedded_materializer_on_public_details(self) -> None:
        args = SimpleNamespace(
            dry_run=True,
            skip_export=False,
            skip_partition=False,
            skip_education=False,
            education_only=True,
            skip_build=True,
            validate_only=False,
            no_include_derived=False,
            profile=False,
            state="RS",
        )
        with (
            patch.object(update, "parse_args", return_value=args),
            patch.object(update, "print_dry_run") as print_dry_run,
        ):
            self.assertEqual(update.main(), 0)

        commands = print_dry_run.call_args.args[0]
        self.assertEqual([name for name, _command in commands], ["education", "inequality", "validate"])
        inequality_command = dict(commands)["inequality"]
        self.assertIn(str(update.PUBLIC_DATA_DIR / "municipios"), inequality_command)
        self.assertIn(
            str(update.PUBLIC_DATA_DIR / "educacao" / "municipios"),
            inequality_command,
        )
        self.assertFalse(print_dry_run.call_args.kwargs["run_sync"])
        self.assertIn("--state", dict(commands)["inequality"])

    def test_full_update_materializes_staging_from_current_education_output(self) -> None:
        args = SimpleNamespace(
            dry_run=True,
            skip_export=False,
            skip_partition=False,
            skip_education=False,
            education_only=False,
            skip_build=True,
            validate_only=False,
            no_include_derived=False,
            profile=False,
            state="rs",
        )
        with (
            patch.object(update, "parse_args", return_value=args),
            patch.object(update, "print_dry_run") as print_dry_run,
        ):
            self.assertEqual(update.main(), 0)

        commands = print_dry_run.call_args.args[0]
        self.assertEqual(
            [name for name, _command in commands],
            ["export", "partition", "education", "inequality", "validate"],
        )
        inequality_command = dict(commands)["inequality"]
        self.assertIn(
            str(update.STATIC_PARTITIONED_DATA_DIR / "municipios"),
            inequality_command,
        )
        self.assertIn(
            str(update.PUBLIC_DATA_DIR / "educacao" / "municipios"),
            inequality_command,
        )
        self.assertTrue(print_dry_run.call_args.kwargs["run_sync"])
        partition_command = dict(commands)["partition"]
        self.assertEqual(partition_command[-2:], ["--state", "RS"])

    def test_unknown_state_fails_before_any_pipeline_step(self) -> None:
        args = SimpleNamespace(
            dry_run=True,
            skip_export=False,
            skip_partition=False,
            skip_education=False,
            education_only=False,
            skip_build=True,
            validate_only=False,
            no_include_derived=False,
            profile=False,
            state="AL",
        )
        with (
            patch.object(update, "parse_args", return_value=args),
            patch.object(
                update,
                "load_state_config",
                side_effect=FileNotFoundError("Configuração estadual não encontrada para AL"),
            ),
            patch.object(update, "run_command") as run_command,
            patch.object(update, "sync_partitioned_to_public") as sync,
        ):
            self.assertEqual(update.main(), 2)
        run_command.assert_not_called()
        sync.assert_not_called()


if __name__ == "__main__":
    unittest.main()
