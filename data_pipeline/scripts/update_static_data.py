from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
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
from src.state_publication import (  # noqa: E402
    StatePublicationError,
    resolve_public_data_dir,
)
from src.pipeline_profiling import (  # noqa: E402
    ProfileError,
    ProfileOutputError,
    ProfileSession,
    activate_profile_session,
    get_active_profile_session,
    profile_operation,
    profile_step,
    sanitize_profile_path,
    validate_profile_output_path,
    write_profile_report,
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
    reused: bool = False
    publication_noop: bool = False
    reason: str | None = None


@dataclass(frozen=True)
class SyncStats:
    created: int
    updated: int
    preserved: int
    removed: int
    files_evaluated: int = 0
    bytes_compared: int = 0
    bytes_copied: int = 0
    directories_examined: int = 0


EDUCATION_RESULT_ENV = "PNE_EDUCATION_RESULT_PATH"
EDUCATION_RESULT_SCHEMA_VERSION = "education-run-result-v1"


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


DEFAULT_ALLOWED_UPDATE_ROOT = "public/data"


def repo_relative_public_root(public_root: Path) -> str:
    """Rotula a raiz publicada da UF relativa ao repositorio, sem fallback."""
    resolved = Path(public_root).resolve()
    root = Path(REPO_ROOT).resolve()
    try:
        return resolved.relative_to(root).as_posix()
    except ValueError as exc:
        raise SystemExit(
            f"[update-data] Raiz publicada fora do repositorio: {resolved}."
        ) from exc


def is_allowed_update_path(
    path: str,
    allowed_root: str = DEFAULT_ALLOWED_UPDATE_ROOT,
) -> bool:
    normalized = path.replace("\\", "/")
    return normalized == allowed_root or normalized.startswith(f"{allowed_root}/")


def ensure_git_update_safe(
    allowed_root: str = DEFAULT_ALLOWED_UPDATE_ROOT,
) -> None:
    status = run_git_status()
    if not status:
        print("[update-data] Git status inicial: limpo.")
        return

    blocked = [
        path
        for path in status_paths(status)
        if not is_allowed_update_path(path, allowed_root)
    ]
    if blocked:
        print("[update-data] Git status inicial:")
        print(status)
        print(
            f"[update-data] Alteracoes fora de {allowed_root} impedem o update completo:"
        )
        for path in blocked:
            print(f"  - {path}")
        raise SystemExit(1)

    print(
        "[update-data] Git status inicial contem apenas alteracoes permitidas em "
        f"{allowed_root}."
    )


def run_command(name: str, command: list[str], results: list[StepResult]) -> None:
    print(f"[update-data] Iniciando {name}: {format_command(command)}")
    profile_session = get_active_profile_session()
    if profile_session is not None:
        step_category = "build" if name == "build" else "orchestration"
        operation: object | None = None
        try:
            with profile_step(
                f"step.{name}",
                session=profile_session,
                category=step_category,
                metadata={"step": name},
            ) as step:
                with profile_operation(
                    "subprocess",
                    name,
                    session=profile_session,
                    metadata={
                        "command": command,
                        "workingDirectory": REPO_ROOT,
                    },
                ) as operation:
                    environment = os.environ.copy()
                    child = None
                    if name != "build":
                        child = profile_session.child_context(
                            parent_event_id=operation.event_id,
                            command=name,
                            parameters={"step": name},
                        )
                        environment.update(child.environment)
                    completed = subprocess.run(
                        command,
                        cwd=REPO_ROOT,
                        check=False,
                        env=environment,
                    )
                    operation.add_counter("exitCode", completed.returncode)
                    operation.add_counter("processesStarted", 1)
                    if child is not None:
                        operation.add_metadata(childRunId=child.run_id)
                    if completed.returncode != 0:
                        operation.mark_error(
                            "SubprocessExitError",
                            f"{name} encerrou com codigo {completed.returncode}",
                        )
                        step.mark_error(
                            "SubprocessExitError",
                            f"{name} encerrou com codigo {completed.returncode}",
                        )
            duration = operation.duration_ns / 1_000_000_000
        except BaseException:
            duration_ns = getattr(operation, "duration_ns", 0) if operation else 0
            results.append(StepResult(name, "erro", duration_ns / 1_000_000_000))
            raise
        if completed.returncode != 0:
            results.append(StepResult(name, "erro", duration))
            print(f"[update-data] ERRO em {name} apos {duration:.1f}s.")
            raise SystemExit(completed.returncode)
        results.append(StepResult(name, "ok", duration))
        print(f"[update-data] {name} concluido em {duration:.1f}s.")
        return

    start = time.perf_counter()
    completed = subprocess.run(command, cwd=REPO_ROOT, check=False)
    duration = time.perf_counter() - start
    if completed.returncode != 0:
        results.append(StepResult(name, "erro", duration))
        print(f"[update-data] ERRO em {name} apos {duration:.1f}s.")
        raise SystemExit(completed.returncode)
    results.append(StepResult(name, "ok", duration))
    print(f"[update-data] {name} concluido em {duration:.1f}s.")


def run_education_command(command: list[str], results: list[StepResult]) -> None:
    """Executa Educacao e incorpora seu resultado sem persistir um sidecar."""

    with tempfile.TemporaryDirectory(prefix="pne-education-result-") as temporary:
        result_path = Path(temporary) / "education-result.json"
        previous = os.environ.get(EDUCATION_RESULT_ENV)
        os.environ[EDUCATION_RESULT_ENV] = str(result_path)
        try:
            run_command("education", command, results)
        finally:
            if previous is None:
                os.environ.pop(EDUCATION_RESULT_ENV, None)
            else:
                os.environ[EDUCATION_RESULT_ENV] = previous

        if not result_path.is_file():
            return
        try:
            payload = json.loads(result_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise RuntimeError("Resultado operacional da Educacao e invalido.") from exc
        required = {
            "schemaVersion",
            "reused",
            "publicationNoop",
            "reason",
            "stagingCreated",
            "municipalitiesMaterialized",
            "filesRendered",
            "bytesRendered",
            "filesValidated",
            "promoted",
            "stateWritten",
        }
        counter_fields = (
            "stagingCreated",
            "municipalitiesMaterialized",
            "filesRendered",
            "bytesRendered",
            "filesValidated",
        )
        if (
            not isinstance(payload, dict)
            or set(payload) != required
            or payload.get("schemaVersion") != EDUCATION_RESULT_SCHEMA_VERSION
            or not isinstance(payload.get("reused"), bool)
            or not isinstance(payload.get("publicationNoop"), bool)
            or not isinstance(payload.get("reason"), str)
            or not isinstance(payload.get("promoted"), bool)
            or not isinstance(payload.get("stateWritten"), bool)
            or any(
                isinstance(payload.get(field), bool)
                or not isinstance(payload.get(field), int)
                or payload[field] < 0
                for field in counter_fields
            )
        ):
            raise RuntimeError("Contrato do resultado operacional da Educacao divergiu.")
        if payload["reused"] and (
            payload["publicationNoop"]
            or payload["promoted"]
            or payload["stateWritten"]
            or any(payload[field] != 0 for field in counter_fields)
        ):
            raise RuntimeError("Resultado reused declarou efeito transacional.")
        education_result = next(
            (result for result in reversed(results) if result.name == "education"),
            None,
        )
        if education_result is not None:
            education_result.reused = payload["reused"]
            education_result.publication_noop = payload["publicationNoop"]
            education_result.reason = payload["reason"]


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


def iter_managed_public_files(
    public_root: Path,
    metrics: dict[str, int] | None = None,
) -> list[Path]:
    managed: list[Path] = []
    for relative in sorted(
        ROOT_STATIC_FILES | CYCLE_STATIC_FILES | RETIRED_PUBLIC_ROOT_FILES
    ):
        path = public_root / Path(relative)
        if path.is_file():
            managed.append(path)

    municipal_root = public_root / "municipios"
    if municipal_root.is_dir():
        directories = sorted(path for path in municipal_root.iterdir() if path.is_dir())
        if metrics is not None:
            metrics["directories_examined"] += len(directories) + 1
        for directory in directories:
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


def files_match(
    source: Path,
    target: Path,
    metrics: dict[str, int] | None = None,
) -> bool:
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
            if metrics is not None:
                metrics["bytes_compared"] += len(source_chunk) + len(target_chunk)
            if source_chunk != target_chunk:
                return False
            if not source_chunk:
                return True


def copy_file_atomically(
    source: Path,
    target: Path,
    metrics: dict[str, int] | None = None,
) -> None:
    temporary = target.with_name(f".{target.name}.{os.getpid()}.tmp")
    try:
        shutil.copy2(source, temporary)
        os.replace(temporary, target)
        if metrics is not None:
            metrics["bytes_copied"] += source.stat().st_size
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
    profile_session = get_active_profile_session()
    profile_metrics = {
        "bytes_compared": 0,
        "bytes_copied": 0,
        "directories_examined": 0,
    }
    comparison_duration_ns = 0
    promotion_duration_ns = 0

    if not source_root.exists():
        raise RuntimeError(f"[update-data] Diretorio particionado nao encontrado: {source_root}")
    if not public_root.exists():
        raise RuntimeError(f"[update-data] Diretorio public/data nao encontrado: {public_root}")

    if registry is None:
        state_config = load_state_config(state_code)
        registry = load_municipality_registry(state_config)
    with profile_operation(
        "validation",
        "sync.staging_validation",
        session=profile_session,
        metadata={"sourceRoot": source_root},
    ) as validation_event:
        source_files = validate_static_partition(source_root, registry)
        validation_event.add_counter("files", len(source_files))
        if profile_session is not None:
            profile_metrics["directories_examined"] += len(
                {path.parent.resolve() for path in source_files}
            ) + 1
            validation_event.add_counter(
                "bytesRead",
                sum(path.stat().st_size for path in source_files),
            )
    expected_targets: set[Path] = set()
    created = updated = preserved = removed = 0

    for source in source_files:
        relative = source.relative_to(source_root)
        target = public_root / relative
        expected_targets.add(target.resolve())
        target.parent.mkdir(parents=True, exist_ok=True)

        comparison_started_ns = (
            time.perf_counter_ns() if profile_session is not None else 0
        )
        matches = files_match(
            source,
            target,
            profile_metrics if profile_session is not None else None,
        )
        if profile_session is not None:
            comparison_duration_ns += time.perf_counter_ns() - comparison_started_ns
        if matches:
            preserved += 1
            continue
        action = "updated" if target.exists() else "created"

        promotion_started_ns = (
            time.perf_counter_ns() if profile_session is not None else 0
        )
        copy_file_atomically(
            source,
            target,
            profile_metrics if profile_session is not None else None,
        )
        if profile_session is not None:
            promotion_duration_ns += time.perf_counter_ns() - promotion_started_ns
        if action == "created":
            created += 1
        else:
            updated += 1

    removal_started_ns = time.perf_counter_ns() if profile_session is not None else 0
    for target in iter_managed_public_files(
        public_root,
        profile_metrics if profile_session is not None else None,
    ):
        if target.resolve() not in expected_targets:
            target.unlink()
            removed += 1
    if profile_session is not None:
        promotion_duration_ns += time.perf_counter_ns() - removal_started_ns
        profile_session.record_aggregate_event(
            category="read",
            name="sync.comparison",
            duration_ns=comparison_duration_ns,
            counters={
                "filesEvaluated": len(source_files),
                "bytesCompared": profile_metrics["bytes_compared"],
            },
        )
        profile_session.record_aggregate_event(
            category="promotion",
            name="sync.promotion",
            duration_ns=promotion_duration_ns,
            counters={
                "created": created,
                "updated": updated,
                "preserved": preserved,
                "removed": removed,
                "bytesCopied": profile_metrics["bytes_copied"],
                "directoriesExamined": profile_metrics["directories_examined"],
            },
        )

    duration = time.perf_counter() - start
    results.append(StepResult(name, "ok", duration))
    stats = SyncStats(
        created,
        updated,
        preserved,
        removed,
        files_evaluated=len(source_files),
        bytes_compared=profile_metrics["bytes_compared"],
        bytes_copied=profile_metrics["bytes_copied"],
        directories_examined=profile_metrics["directories_examined"],
    )
    print(f"[update-data] {name} concluido em {duration:.1f}s.")
    print(f"[update-data] sync criados: {stats.created}")
    print(f"[update-data] sync atualizados: {stats.updated}")
    print(f"[update-data] sync preservados: {stats.preserved}")
    print(f"[update-data] sync removidos: {stats.removed}")
    return stats


def print_dry_run(
    commands: list[tuple[str, list[str]]],
    run_sync: bool,
    run_build: bool,
    public_root: Path = PUBLIC_DATA_DIR,
) -> None:
    profile_session = get_active_profile_session()
    print("[update-data] Dry run: nenhum comando que altera arquivos sera executado.")
    print("[update-data] Checagem segura: git status --short")
    with profile_operation(
        "validation",
        "dry_run.git_status",
        session=profile_session,
        metadata={"readOnly": True},
    ) as validation_event:
        status = run_git_status()
        validation_event.add_counter("dirtyPaths", len(status_paths(status)))
    print(status or "[update-data] Git status atual: limpo.")

    sync_printed = False
    for name, command in commands:
        print(f"[update-data] Rodaria {name}: {format_command(command)}")
        with profile_operation(
            "orchestration",
            f"plan.{name}",
            session=profile_session,
            metadata={"planned": True, "executed": False, "command": command},
        ) as planned_event:
            planned_event.add_counter("processesPlanned", 1)
            planned_event.add_counter("processesStarted", 0)
        if name == "inequality" and run_sync:
            print(
                "[update-data] Rodaria sync: "
                f"{STATIC_PARTITIONED_DATA_DIR} -> {public_root}"
            )
            sync_printed = True
    if run_sync and not sync_printed:
        print(
            "[update-data] Rodaria sync: "
            f"{STATIC_PARTITIONED_DATA_DIR} -> {public_root}"
        )
    if run_sync:
        with profile_operation(
            "orchestration",
            "plan.sync",
            session=profile_session,
            metadata={"planned": True, "executed": False},
        ):
            pass
    if run_build:
        print(f"[update-data] Rodaria build: {format_command([NPM, 'run', 'build'])}")
        print("[update-data] build: planejado, não executado por dry-run")
        with profile_operation(
            "build",
            "plan.build",
            session=profile_session,
            metadata={"planned": True, "executed": False},
        ) as build_event:
            build_event.add_counter("processesPlanned", 1)
            build_event.add_counter("processesStarted", 0)


def print_summary(
    results: list[StepResult],
    skipped: list[str],
    validate_ok: bool,
    build_status: str,
    profile: bool = False,
) -> None:
    print("[update-data] Resumo:")
    for result in results:
        duration = "" if result.duration is None else f" ({result.duration:.1f}s)"
        detail = ""
        if result.reused:
            detail = f", reused=true, reason={result.reason}"
        elif result.publication_noop:
            detail = ", reused=false, publicationNoop=true"
        print(f"  - {result.name}: {result.status}{detail}{duration}")
    for name in skipped:
        print(f"  - {name}: pulado")
    print(f"[update-data] validate:details: {'passou' if validate_ok else 'nao executado'}")
    print(f"[update-data] build: {build_status}")
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


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Orquestra export, partition, sync e validacao dos dados estaticos; "
            "o build completo e opcional."
        )
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
        help="Exporta somente Educacao, materializa a desigualdade e valida.",
    )
    education_fingerprint_group = parser.add_mutually_exclusive_group()
    education_fingerprint_group.add_argument(
        "--education-fingerprint-shadow",
        action="store_true",
        help=(
            "Propaga o piloto de fingerprint shadow para a Educacao; mede "
            "wouldSkip, mas nao pula nenhuma etapa."
        ),
    )
    education_fingerprint_group.add_argument(
        "--education-fingerprint-skip",
        action="store_true",
        help=(
            "Reutiliza somente a etapa de Educacao quando fingerprint e "
            "outputs estiverem comprovadamente integros."
        ),
    )
    build_group = parser.add_mutually_exclusive_group()
    build_group.add_argument(
        "--build",
        action="store_true",
        help="Executa o build completo apos todas as etapas de dados passarem.",
    )
    build_group.add_argument(
        "--skip-build",
        action="store_true",
        help="Alias legado: mantem o comportamento padrao sem build.",
    )
    parser.add_argument("--validate-only", action="store_true", help="Roda apenas npm run validate:details.")
    parser.add_argument(
        "--no-include-derived",
        action="store_true",
        help="Executa o export sem --include-derived.",
    )
    parser.add_argument(
        "--profile",
        action="store_true",
        help=(
            "Gera profile.json e summary.json com as etapas do pipeline; "
            "sem esta flag nenhum relatorio e criado."
        ),
    )
    parser.add_argument(
        "--profile-output",
        type=Path,
        default=None,
        help=(
            "Diretorio seguro para o relatorio; requer --profile. "
            "O padrao e data_pipeline/export/profiles/<run-id>."
        ),
    )
    parser.add_argument(
        "--state",
        default=DEFAULT_STATE_CODE,
        help=f"Código estadual configurado (padrão: {DEFAULT_STATE_CODE}).",
    )
    args = parser.parse_args(argv)
    if args.validate_only and args.build:
        parser.error("--validate-only nao pode ser combinado com --build.")
    if args.profile_output is not None and not args.profile:
        parser.error("--profile-output requer --profile.")
    if args.profile_output is not None:
        try:
            validate_profile_output_path(args.profile_output, run_id="validation")
        except ProfileOutputError as exc:
            parser.error(str(exc))
    return args


def run_pipeline(args: argparse.Namespace) -> int:
    if args.education_only and args.skip_education:
        raise SystemExit("--education-only e --skip-education sao mutuamente exclusivos.")
    shadow_requested = bool(getattr(args, "education_fingerprint_shadow", False))
    skip_requested = bool(getattr(args, "education_fingerprint_skip", False))
    fingerprint_requested = shadow_requested or skip_requested
    selected_fingerprint_flag = (
        "--education-fingerprint-skip"
        if skip_requested
        else "--education-fingerprint-shadow"
    )
    if fingerprint_requested and args.skip_education:
        raise SystemExit(
            f"{selected_fingerprint_flag} requer a etapa de Educacao ativa."
        )
    if fingerprint_requested and args.validate_only:
        raise SystemExit(
            f"{selected_fingerprint_flag} nao pode ser combinado com --validate-only."
        )
    try:
        with profile_operation(
            "validation",
            "initial_configuration",
            metadata={"requestedState": args.state},
        ) as validation_event:
            state_config = load_state_config(args.state)
            registry = load_municipality_registry(state_config)
            public_data_root = resolve_public_data_dir(state_config.state_code)
            allowed_update_root = repo_relative_public_root(public_data_root)
            if get_active_profile_session() is not None:
                validation_event.add_counter(
                    "municipalities",
                    registry.municipality_count,
                )
    except (
        FileNotFoundError,
        StateConfigError,
        MunicipalityRegistryError,
        StatePublicationError,
    ) as exc:
        print(f"[update-data] Configuração estadual inválida: {exc}", file=sys.stderr)
        return 2
    results: list[StepResult] = []
    skipped: list[str] = []
    if args.skip_build:
        print(
            "[update-data] Compatibilidade: --skip-build e legado; "
            "o build ja nao e solicitado por padrao."
        )

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
        "--state",
        state_config.state_code,
    ]
    if shadow_requested:
        education_command.append("--fingerprint-shadow")
    elif skip_requested:
        education_command.append("--fingerprint-skip")
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
            print_dry_run(
                [("validate", validate_command)],
                run_sync=False,
                run_build=False,
                public_root=public_data_root,
            )
            return 0
        try:
            run_command("validate", validate_command, results)
        except (SystemExit, Exception):
            print_summary(
                results,
                ["export", "partition", "sync", "inequality", "education"],
                validate_ok=False,
                build_status="não solicitado",
                profile=args.profile,
            )
            raise
        print_summary(
            results,
            ["export", "partition", "sync", "inequality", "education"],
            validate_ok=True,
            build_status="não solicitado",
            profile=args.profile,
        )
        return 0

    run_export = not args.skip_export and not args.education_only
    run_partition = not args.skip_partition and not args.education_only
    run_sync = run_partition
    run_education = not args.skip_education
    run_inequality = run_partition or run_education
    run_build = args.build
    inequality_output_root = (
        STATIC_PARTITIONED_DATA_DIR / "municipios"
        if run_partition
        else public_data_root / "municipios"
    )
    inequality_command = [
        PYTHON,
        "data_pipeline/scripts/materialize_municipal_inequality.py",
        "--output-root",
        str(inequality_output_root),
        "--education-root",
        str(public_data_root / "educacao" / "municipios"),
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
        if fingerprint_requested:
            mode = "skip" if skip_requested else "shadow"
            print(
                f"[update-data] Fingerprint {mode} solicitado no plano: nenhum "
                "digest tabular ou task state sera acessado no dry-run."
            )
        print_dry_run(
            planned_commands,
            run_sync=run_sync,
            run_build=run_build,
            public_root=public_data_root,
        )
        return 0

    validate_ok = False
    build_started = False
    try:
        if run_export or run_partition or run_sync or run_education:
            with profile_operation(
                "validation",
                "git_update_safety",
                metadata={"allowedRoot": allowed_update_root},
            ):
                ensure_git_update_safe(allowed_update_root)

        if run_export:
            run_command("export", export_command, results)
        else:
            skipped.append("export")

        if run_partition:
            run_command("partition", partition_command, results)
        else:
            skipped.extend(["partition", "sync"])

        if run_education:
            run_education_command(education_command, results)
        else:
            skipped.append("education")

        if run_inequality:
            run_command("inequality", inequality_command, results)
        else:
            skipped.append("inequality")

        if run_sync:
            with profile_step("step.sync", metadata={"step": "sync"}) as sync_event:
                sync_stats = sync_partitioned_to_public(
                    results,
                    public_root=public_data_root,
                    registry=registry,
                )
                if get_active_profile_session() is not None and sync_stats is not None:
                    sync_event.add_counters(
                        created=sync_stats.created,
                        updated=sync_stats.updated,
                        preserved=sync_stats.preserved,
                        removed=sync_stats.removed,
                        filesEvaluated=sync_stats.files_evaluated,
                        bytesCompared=sync_stats.bytes_compared,
                        bytesCopied=sync_stats.bytes_copied,
                        directoriesExamined=sync_stats.directories_examined,
                    )

        run_command("validate", validate_command, results)
        validate_ok = True

        if run_build:
            build_started = True
            run_command("build", build_command, results)
    except (SystemExit, Exception):
        if run_build:
            build_status = (
                "falhou" if build_started else "não alcançado por falha anterior"
            )
        else:
            build_status = "não solicitado"
        print_summary(
            results,
            skipped,
            validate_ok=validate_ok,
            build_status=build_status,
            profile=args.profile,
        )
        raise

    print_summary(
        results,
        skipped,
        validate_ok=validate_ok,
        build_status="concluído" if run_build else "não solicitado",
        profile=args.profile,
    )
    return 0


def _profile_parameters(args: argparse.Namespace) -> dict[str, object]:
    return {
        "state": args.state,
        "dryRun": args.dry_run,
        "buildRequested": args.build,
        "validateOnly": args.validate_only,
        "educationOnly": args.education_only,
        "skipExport": args.skip_export,
        "skipPartition": args.skip_partition,
        "skipEducation": args.skip_education,
        "educationFingerprintShadow": bool(
            getattr(args, "education_fingerprint_shadow", False)
        ),
        "educationFingerprintSkip": bool(
            getattr(args, "education_fingerprint_skip", False)
        ),
        "includeDerived": not args.no_include_derived,
    }


def _write_root_profile(session: ProfileSession) -> tuple[Path, Path] | None:
    try:
        paths = write_profile_report(session)
    except ProfileError as exc:
        print(f"[profile] Falha ao escrever o relatorio: {exc}", file=sys.stderr)
        return None
    print(
        "[profile] Relatorios gerados: "
        f"{sanitize_profile_path(paths[0])}, {sanitize_profile_path(paths[1])}"
    )
    return paths


def main() -> int:
    args = parse_args()
    if not args.profile:
        return run_pipeline(args)

    try:
        session = ProfileSession.create_root(
            state_code=args.state,
            command="update_static_data",
            parameters=_profile_parameters(args),
            requested_output=args.profile_output,
        )
    except ProfileOutputError as exc:
        print(f"[profile] Diretorio recusado: {exc}", file=sys.stderr)
        return 2

    result = 1
    with activate_profile_session(session):
        try:
            with profile_step(
                "pipeline.total",
                session=session,
                metadata={
                    "dryRun": args.dry_run,
                    "buildRequested": args.build,
                },
            ) as total_event:
                try:
                    result = run_pipeline(args)
                finally:
                    total_event.add_counter(
                        "processesStarted",
                        sum(
                            1
                            for event in session.events
                            if event.category == "subprocess"
                        ),
                    )
                    total_event.add_counter("dryRun", int(args.dry_run))
                    total_event.add_counter("buildRequested", int(args.build))
                total_event.add_counter("exitCode", result)
                if result != 0:
                    total_event.mark_error("NonZeroExit", f"exit code {result}")
        except BaseException as exc:
            session.finish("error", exc)
            _write_root_profile(session)
            raise
        else:
            session.finish("success" if result == 0 else "error")

    if _write_root_profile(session) is None and result == 0:
        return 3
    return result


if __name__ == "__main__":
    raise SystemExit(main())
