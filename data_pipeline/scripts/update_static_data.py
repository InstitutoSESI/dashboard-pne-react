from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path


DATA_PIPELINE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DATA_PIPELINE_DIR))

from src.config import (  # noqa: E402
    PUBLIC_DATA_DIR,
    REPO_ROOT,
    STATIC_PARTITIONED_DATA_DIR,
)
from src.municipality_registry import (  # noqa: E402
    MunicipalityRegistry,
    MunicipalityRegistryError,
    load_municipality_registry,
)
from src.state_config import (  # noqa: E402
    DEFAULT_STATE_CODE,
    StateConfigError,
    load_state_config,
)

PYTHON = sys.executable
NPM = "npm.cmd" if os.name == "nt" else "npm"
ROOT_STATIC_FILES = frozenset(
    {"indicadores.json", "municipios_index.json"}
)
RETIRED_PUBLIC_ROOT_FILES = frozenset({"municipios.json"})
CYCLE_STATIC_FILES = frozenset(
    {
        "pne_2014_2024/referencia_estadual.json",
        "pne_2026_2036/referencia_estadual.json",
    }
)
MUNICIPAL_STATIC_FILES = frozenset(
    {"details.json", "index.json"}
)
RETIRED_MUNICIPAL_STATIC_FILES = frozenset({"diagnostico.json"})

try:
    sys.stdout.reconfigure(line_buffering=True)
except AttributeError:
    pass


@dataclass
class StepResult:
    name: str
    status: str
    duration: float | None = None


@dataclass(frozen=True)
class SyncStats:
    created: int
    updated: int
    preserved: int
    removed: int


def format_command(command: list[str]) -> str:
    return " ".join(command)


def run_git_status() -> str:
    result = subprocess.run(
        ["git", "status", "--short"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git status failed")
    return result.stdout.rstrip()


def status_paths(status_output: str) -> list[str]:
    paths: list[str] = []
    for line in status_output.splitlines():
        if not line:
            continue
        raw_path = line[3:].strip()
        if " -> " in raw_path:
            paths.extend(part.strip().strip('"') for part in raw_path.split(" -> "))
        else:
            paths.append(raw_path.strip('"'))
    return paths


def is_allowed_update_path(path: str) -> bool:
    normalized = path.replace("\\", "/")
    return normalized == "public/data" or normalized.startswith("public/data/")


def ensure_git_update_safe() -> None:
    status = run_git_status()
    if not status:
        print("[update-data] Git status inicial: limpo.")
        return

    blocked = [path for path in status_paths(status) if not is_allowed_update_path(path)]
    if blocked:
        print("[update-data] Git status inicial:")
        print(status)
        print("[update-data] Alteracoes fora de public/data impedem o update completo:")
        for path in blocked:
            print(f"  - {path}")
        raise SystemExit(1)

    print("[update-data] Git status inicial contem apenas alteracoes permitidas em public/data.")


def run_command(name: str, command: list[str], results: list[StepResult]) -> None:
    print(f"[update-data] Iniciando {name}: {format_command(command)}")
    start = time.perf_counter()
    completed = subprocess.run(command, cwd=REPO_ROOT, check=False)
    duration = time.perf_counter() - start
    if completed.returncode != 0:
        results.append(StepResult(name, "erro", duration))
        print(f"[update-data] ERRO em {name} apos {duration:.1f}s.")
        raise SystemExit(completed.returncode)
    results.append(StepResult(name, "ok", duration))
    print(f"[update-data] {name} concluido em {duration:.1f}s.")


def iter_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*") if path.is_file())


def is_managed_static_path(relative: Path) -> bool:
    normalized = relative.as_posix()
    if normalized in ROOT_STATIC_FILES or normalized in CYCLE_STATIC_FILES:
        return True
    return (
        len(relative.parts) == 3
        and relative.parts[0] == "municipios"
        and len(relative.parts[1]) == 7
        and relative.parts[1].isdigit()
        and relative.parts[2] in MUNICIPAL_STATIC_FILES
    )


def validate_static_partition(
    source_root: Path,
    registry: MunicipalityRegistry,
) -> list[Path]:
    source_files = iter_files(source_root)
    unexpected = [
        path.relative_to(source_root).as_posix()
        for path in source_files
        if not is_managed_static_path(path.relative_to(source_root))
    ]
    if unexpected:
        preview = ", ".join(unexpected[:5])
        raise RuntimeError(
            "[update-data] Staging estatico contem arquivos fora do contrato: "
            f"{preview}."
        )

    required = ROOT_STATIC_FILES | CYCLE_STATIC_FILES
    available = {path.relative_to(source_root).as_posix() for path in source_files}
    missing = sorted(required - available)
    if missing:
        raise RuntimeError(
            "[update-data] Staging estatico incompleto; ausentes: " + ", ".join(missing)
        )

    municipal_contracts: dict[str, set[str]] = {}
    for path in source_files:
        relative = path.relative_to(source_root)
        if len(relative.parts) == 3 and relative.parts[0] == "municipios":
            municipal_contracts.setdefault(relative.parts[1], set()).add(path.name)

    municipal_root = source_root / "municipios"
    observed_ids = (
        {path.name for path in municipal_root.iterdir() if path.is_dir()}
        if municipal_root.is_dir()
        else set()
    )
    if observed_ids != registry.ids:
        missing_ids = sorted(registry.ids - observed_ids)
        extra_ids = sorted(observed_ids - registry.ids)
        raise RuntimeError(
            "[update-data] Conjunto municipal do staging diverge do registro; "
            f"ausentes={missing_ids[:5]}, extras={extra_ids[:5]}."
        )

    if set(municipal_contracts) != registry.ids:
        raise RuntimeError(
            "[update-data] Staging estatico nao possui contratos para todos os "
            "diretorios municipais do registro."
        )

    incomplete = {
        municipality_id: sorted(MUNICIPAL_STATIC_FILES - filenames)
        for municipality_id, filenames in municipal_contracts.items()
        if filenames != MUNICIPAL_STATIC_FILES
    }
    if incomplete:
        preview = ", ".join(
            f"{municipality_id}: {','.join(missing)}"
            for municipality_id, missing in sorted(incomplete.items())[:5]
        )
        raise RuntimeError(
            "[update-data] Staging estatico contem contratos municipais "
            f"incompletos: {preview}."
        )

    index_path = source_root / "municipios_index.json"
    try:
        index_payload = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(
            f"[update-data] municipios_index.json invalido no staging: {exc}."
        ) from exc
    if not isinstance(index_payload, dict):
        raise RuntimeError(
            "[update-data] municipios_index.json do staging deve ser um objeto."
        )
    generated_at = index_payload.get("generated_at")
    try:
        expected_index = registry.build_public_index_payload(
            generated_at=generated_at
        )
    except MunicipalityRegistryError as exc:
        raise RuntimeError(
            f"[update-data] municipios_index.json invalido no staging: {exc}"
        ) from exc
    if index_payload != expected_index:
        raise RuntimeError(
            "[update-data] municipios_index.json do staging diverge da projeção do registro."
        )

    for record in registry.ordered_records:
        municipal_index_path = (
            source_root / "municipios" / record.ibge_code / "index.json"
        )
        try:
            municipal_payload = json.loads(
                municipal_index_path.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(
                f"[update-data] Contrato municipal inválido em {record.ibge_code}: {exc}."
            ) from exc
        if not isinstance(municipal_payload, dict):
            raise RuntimeError(
                f"[update-data] index.json de {record.ibge_code} deve ser um objeto."
            )
        expected_identity = {
            "id_municipio": record.ibge_code,
            "municipio": record.name,
            "slug": record.slug,
        }
        observed_identity = {
            field: municipal_payload.get(field) for field in expected_identity
        }
        if observed_identity != expected_identity:
            raise RuntimeError(
                "[update-data] Identidade municipal divergente no staging para "
                f"{record.ibge_code}: {observed_identity!r}."
            )

    return source_files


def iter_managed_public_files(public_root: Path) -> list[Path]:
    managed: list[Path] = []
    for relative in sorted(
        ROOT_STATIC_FILES | CYCLE_STATIC_FILES | RETIRED_PUBLIC_ROOT_FILES
    ):
        path = public_root / Path(relative)
        if path.is_file():
            managed.append(path)

    municipal_root = public_root / "municipios"
    if municipal_root.is_dir():
        for directory in sorted(path for path in municipal_root.iterdir() if path.is_dir()):
            for filename in sorted(MUNICIPAL_STATIC_FILES):
                path = directory / filename
                if path.is_file():
                    managed.append(path)
            if len(directory.name) == 7 and directory.name.isdigit():
                for filename in sorted(RETIRED_MUNICIPAL_STATIC_FILES):
                    path = directory / filename
                    if path.is_file():
                        managed.append(path)
    return managed


def files_match(source: Path, target: Path) -> bool:
    if not target.is_file():
        return False
    source_stat = source.stat()
    target_stat = target.stat()
    if source_stat.st_size != target_stat.st_size:
        return False
    if source_stat.st_mtime_ns == target_stat.st_mtime_ns:
        return True

    chunk_size = 1024 * 1024
    with source.open("rb") as source_file, target.open("rb") as target_file:
        while True:
            source_chunk = source_file.read(chunk_size)
            target_chunk = target_file.read(chunk_size)
            if source_chunk != target_chunk:
                return False
            if not source_chunk:
                return True


def copy_file_atomically(source: Path, target: Path) -> None:
    temporary = target.with_name(f".{target.name}.{os.getpid()}.tmp")
    try:
        shutil.copy2(source, temporary)
        os.replace(temporary, target)
    finally:
        if temporary.exists():
            temporary.unlink()


def sync_partitioned_to_public(
    results: list[StepResult],
    source_root: Path = STATIC_PARTITIONED_DATA_DIR,
    public_root: Path = PUBLIC_DATA_DIR,
    registry: MunicipalityRegistry | None = None,
    state_code: str = DEFAULT_STATE_CODE,
) -> SyncStats:
    name = "sync"
    print(f"[update-data] Iniciando {name}: {source_root} -> {public_root}")
    start = time.perf_counter()

    if not source_root.exists():
        raise RuntimeError(f"[update-data] Diretorio particionado nao encontrado: {source_root}")
    if not public_root.exists():
        raise RuntimeError(f"[update-data] Diretorio public/data nao encontrado: {public_root}")

    if registry is None:
        state_config = load_state_config(state_code)
        registry = load_municipality_registry(state_config)
    source_files = validate_static_partition(source_root, registry)
    expected_targets: set[Path] = set()
    created = updated = preserved = removed = 0

    for source in source_files:
        relative = source.relative_to(source_root)
        target = public_root / relative
        expected_targets.add(target.resolve())
        target.parent.mkdir(parents=True, exist_ok=True)

        if files_match(source, target):
            preserved += 1
            continue
        action = "updated" if target.exists() else "created"

        copy_file_atomically(source, target)
        if action == "created":
            created += 1
        else:
            updated += 1

    for target in iter_managed_public_files(public_root):
        if target.resolve() not in expected_targets:
            target.unlink()
            removed += 1

    duration = time.perf_counter() - start
    results.append(StepResult(name, "ok", duration))
    stats = SyncStats(created, updated, preserved, removed)
    print(f"[update-data] {name} concluido em {duration:.1f}s.")
    print(f"[update-data] sync criados: {stats.created}")
    print(f"[update-data] sync atualizados: {stats.updated}")
    print(f"[update-data] sync preservados: {stats.preserved}")
    print(f"[update-data] sync removidos: {stats.removed}")
    return stats


def print_dry_run(commands: list[tuple[str, list[str]]], run_sync: bool, run_build: bool) -> None:
    print("[update-data] Dry run: nenhum comando que altera arquivos sera executado.")
    print("[update-data] Checagem segura: git status --short")
    status = run_git_status()
    print(status or "[update-data] Git status atual: limpo.")

    sync_printed = False
    for name, command in commands:
        print(f"[update-data] Rodaria {name}: {format_command(command)}")
        if name == "inequality" and run_sync:
            print(
                "[update-data] Rodaria sync: "
                f"{STATIC_PARTITIONED_DATA_DIR} -> {PUBLIC_DATA_DIR}"
            )
            sync_printed = True
    if run_sync and not sync_printed:
        print(
            "[update-data] Rodaria sync: "
            f"{STATIC_PARTITIONED_DATA_DIR} -> {PUBLIC_DATA_DIR}"
        )
    if run_build:
        print(f"[update-data] Rodaria build: {format_command([NPM, 'run', 'build'])}")


def print_summary(
    results: list[StepResult],
    skipped: list[str],
    validate_ok: bool,
    build_ok: bool | None,
    profile: bool = False,
) -> None:
    print("[update-data] Resumo:")
    for result in results:
        duration = "" if result.duration is None else f" ({result.duration:.1f}s)"
        print(f"  - {result.name}: {result.status}{duration}")
    for name in skipped:
        print(f"  - {name}: pulado")
    print(f"[update-data] validate:details: {'passou' if validate_ok else 'nao executado'}")
    if build_ok is None:
        print("[update-data] build: nao executado")
    else:
        print(f"[update-data] build: {'passou' if build_ok else 'falhou'}")
    if profile:
        print("[update-data] Perfil por duração:")
        for result in sorted(
            results,
            key=lambda item: item.duration or 0,
            reverse=True,
        ):
            print(f"  - {result.name}: {(result.duration or 0):.3f}s")
    print("[update-data] Git status final:")
    print(run_git_status() or "  limpo")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Orquestra export, partition, sync, validacao e build dos dados estaticos."
    )
    parser.add_argument("--dry-run", action="store_true", help="Mostra as etapas sem alterar arquivos.")
    parser.add_argument("--skip-export", action="store_true", help="Pula a etapa de export.")
    parser.add_argument("--skip-partition", action="store_true", help="Pula partition e sync para public/data.")
    parser.add_argument(
        "--skip-education",
        action="store_true",
        help="Pula a exportacao dos indicadores de Educacao.",
    )
    parser.add_argument(
        "--education-only",
        action="store_true",
        help="Exporta somente Educacao, valida e, salvo --skip-build, recompila a aplicacao.",
    )
    parser.add_argument("--skip-build", action="store_true", help="Pula npm run build.")
    parser.add_argument("--validate-only", action="store_true", help="Roda apenas npm run validate:details.")
    parser.add_argument(
        "--no-include-derived",
        action="store_true",
        help="Executa o export sem --include-derived.",
    )
    parser.add_argument(
        "--profile",
        action="store_true",
        help="Mostra o perfil das etapas do export, partition, sync, validação e build.",
    )
    parser.add_argument(
        "--state",
        default=DEFAULT_STATE_CODE,
        help=f"Código estadual configurado (padrão: {DEFAULT_STATE_CODE}).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.education_only and args.skip_education:
        raise SystemExit("--education-only e --skip-education sao mutuamente exclusivos.")
    try:
        state_config = load_state_config(args.state)
        registry = load_municipality_registry(state_config)
    except (FileNotFoundError, StateConfigError, MunicipalityRegistryError) as exc:
        print(f"[update-data] Configuração estadual inválida: {exc}", file=sys.stderr)
        return 2
    results: list[StepResult] = []
    skipped: list[str] = []

    export_command = [PYTHON, "data_pipeline/scripts/export_static_data.py"]
    if not args.no_include_derived:
        export_command.append("--include-derived")
    if args.profile:
        export_command.append("--profile")
    partition_command = [
        PYTHON,
        "data_pipeline/scripts/partition_static_data.py",
        "--state",
        state_config.state_code,
    ]
    education_command = [
        PYTHON,
        "data_pipeline/scripts/export_education_indicators.py",
    ]
    validate_command = [
        NPM,
        "run",
        "validate:details",
        "--",
        "--state",
        state_config.state_code,
    ]
    build_command = [NPM, "run", "build"]

    if args.validate_only:
        if args.dry_run:
            print_dry_run([("validate", validate_command)], run_sync=False, run_build=False)
            return 0
        run_command("validate", validate_command, results)
        print_summary(
            results,
            ["export", "partition", "sync", "inequality-pilot", "education", "build"],
            validate_ok=True,
            build_ok=None,
            profile=args.profile,
        )
        return 0

    run_export = not args.skip_export and not args.education_only
    run_partition = not args.skip_partition and not args.education_only
    run_sync = run_partition
    run_education = not args.skip_education
    run_inequality = run_partition or run_education
    run_build = not args.skip_build
    inequality_output_root = (
        STATIC_PARTITIONED_DATA_DIR / "municipios"
        if run_partition
        else PUBLIC_DATA_DIR / "municipios"
    )
    inequality_command = [
        PYTHON,
        "data_pipeline/scripts/materialize_municipal_inequality.py",
        "--output-root",
        str(inequality_output_root),
        "--education-root",
        str(PUBLIC_DATA_DIR / "educacao" / "municipios"),
        "--state",
        state_config.state_code,
    ]

    planned_commands: list[tuple[str, list[str]]] = []
    if run_export:
        planned_commands.append(("export", export_command))
    if run_partition:
        planned_commands.append(("partition", partition_command))
    if run_education:
        planned_commands.append(("education", education_command))
    if run_inequality:
        planned_commands.append(("inequality", inequality_command))
    planned_commands.append(("validate", validate_command))

    if args.dry_run:
        print_dry_run(planned_commands, run_sync=run_sync, run_build=run_build)
        return 0

    if run_export or run_partition or run_sync or run_education:
        ensure_git_update_safe()

    if run_export:
        run_command("export", export_command, results)
    else:
        skipped.append("export")

    if run_partition:
        run_command("partition", partition_command, results)
    else:
        skipped.extend(["partition", "sync"])

    if run_education:
        run_command("education", education_command, results)
    else:
        skipped.append("education")

    if run_inequality:
        run_command("inequality", inequality_command, results)
    else:
        skipped.append("inequality")

    if run_sync:
        sync_partitioned_to_public(results, registry=registry)

    run_command("validate", validate_command, results)
    validate_ok = True

    build_ok: bool | None = None
    if run_build:
        run_command("build", build_command, results)
        build_ok = True
    else:
        skipped.append("build")

    print_summary(
        results,
        skipped,
        validate_ok=validate_ok,
        build_ok=build_ok,
        profile=args.profile,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
