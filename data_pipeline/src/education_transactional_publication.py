"""Publicacao transacional e fail-closed da Educacao municipal principal."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import json
import math
import os
from pathlib import Path
import re
import shutil
import tempfile
import time
from typing import Any
import uuid

from .config import DATA_PIPELINE_DIR, EDUCATION_DATA_DIR, PUBLIC_DATA_DIR
from .education_municipality_routes import (
    EducationMunicipalityRouteCompatibility,
    build_education_municipalities_index_payload,
)
from .municipality_registry import MunicipalityRegistry
from .pipeline_profiling import get_active_profile_session, profile_operation
from .state_config import DEFAULT_STATE_CODE, normalize_state_code
from .state_publication import StatePublicationError, resolve_education_data_dir


EDUCATION_STAGING_PARENT = DATA_PIPELINE_DIR / ".staging" / "education"
EDUCATION_STAGING_MARKER = ".education-publication-staging.json"

MANAGED_EDUCATION_ROOT_FILES = frozenset(
    {"index.json", "municipios_index.json"}
)
MANAGED_EDUCATION_MUNICIPAL_DIRECTORY = "municipios"
MANAGED_EDUCATION_MUNICIPAL_PATTERN = re.compile(r"\d{7}\.json")

MUNICIPAL_DOCUMENT_FIELDS = frozenset(
    {
        "id_municipio",
        "municipio",
        "updated_at",
        "fontes",
        "avisos",
        "blocos",
    }
)
EDUCATION_BLOCKS = (
    "matriculas",
    "rede_escolar",
    "turmas_docentes",
    "alunos_turma",
    "fluxo",
    "aprendizagem",
    "oferta_tecnica",
    "educacao_indigena",
    "sistema_s",
    "vaar",
)
EDUCATION_INDEX_BLOCKS = (
    "matriculas",
    "rede_escolar",
    "alunos_turma",
    "turmas_docentes",
    "fluxo",
    "aprendizagem",
    "oferta_tecnica",
    "educacao_indigena",
    "sistema_s",
    "vaar",
)
EDUCATION_INDEX_FIELDS = frozenset(
    {
        "updated_at",
        "anos_disponiveis",
        "total_municipios",
        "fontes",
        "avisos_metodologicos",
        "blocos_disponiveis",
        "campos_indisponiveis",
        "caminhos",
        "arquivos_gerados",
    }
)


class EducationPublicationError(RuntimeError):
    """Erro fail-closed da geracao, validacao ou publicacao educacional."""


class EducationStagingError(EducationPublicationError):
    """Staging ausente, inseguro ou fora do contrato."""


class EducationValidationError(EducationPublicationError):
    """A arvore prospectiva nao cumpre o contrato publico."""


class EducationPromotionError(EducationPublicationError):
    """A promocao falhou e a publicacao anterior foi restaurada."""


class EducationRollbackError(EducationPublicationError):
    """A restauracao encontrou erro e o backup foi preservado."""


@dataclass(frozen=True, slots=True)
class EducationStagingRun:
    run_id: str
    run_root: Path
    output_root: Path


@dataclass(frozen=True, slots=True)
class EducationValidationReport:
    files: tuple[Path, ...]
    municipality_count: int
    updated_at: str


@dataclass(frozen=True, slots=True)
class EducationPublicationStats:
    created: int
    updated: int
    preserved: int
    removed: int


@dataclass(frozen=True, slots=True)
class EducationTransactionResult:
    validation: EducationValidationReport
    stats: EducationPublicationStats | None
    staged_output: Path | None


@dataclass(frozen=True, slots=True)
class _PromotionAction:
    kind: str
    relative: Path
    staged: Path | None
    target: Path


def managed_education_relative_paths(
    registry: MunicipalityRegistry,
) -> frozenset[Path]:
    """Allowlist prospectiva exata para um registro municipal validado."""
    paths = {Path(name) for name in MANAGED_EDUCATION_ROOT_FILES}
    paths.update(
        Path(MANAGED_EDUCATION_MUNICIPAL_DIRECTORY)
        / f"{record.ibge_code}.json"
        for record in registry.ordered_records
    )
    return frozenset(paths)


def is_managed_education_public_path(relative: Path) -> bool:
    """Reconhece apenas a propriedade ativa, inclusive orfaos municipais."""
    if relative.as_posix() in MANAGED_EDUCATION_ROOT_FILES:
        return True
    return (
        len(relative.parts) == 2
        and relative.parts[0] == MANAGED_EDUCATION_MUNICIPAL_DIRECTORY
        and MANAGED_EDUCATION_MUNICIPAL_PATTERN.fullmatch(relative.parts[1])
        is not None
    )


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _validate_staging_location(
    path: Path,
    *,
    public_data_root: Path,
) -> Path:
    resolved = path.resolve()
    public_resolved = public_data_root.resolve()
    if resolved == public_resolved or _is_relative_to(resolved, public_resolved):
        raise EducationStagingError(
            f"Staging da Educacao nao pode ficar em public/data: {resolved}."
        )
    if resolved == resolved.parent or resolved in {
        DATA_PIPELINE_DIR.resolve(),
        DATA_PIPELINE_DIR.parent.resolve(),
    }:
        raise EducationStagingError(
            f"Diretorio de staging amplo ou inseguro: {resolved}."
        )
    return resolved


def create_education_staging_run(
    requested_directory: Path | None = None,
    *,
    public_root: Path = EDUCATION_DATA_DIR,
) -> EducationStagingRun:
    """Cria um run exclusivo fora da arvore publica."""
    run_id = uuid.uuid4().hex
    run_root = (
        Path(requested_directory)
        if requested_directory is not None
        else EDUCATION_STAGING_PARENT / run_id
    )
    run_root = _validate_staging_location(
        run_root,
        public_data_root=Path(public_root).parent,
    )
    if run_root.exists():
        raise EducationStagingError(
            f"Diretorio de staging ja existe; use um caminho exclusivo: {run_root}."
        )
    try:
        run_root.mkdir(parents=True, exist_ok=False)
        marker = run_root / EDUCATION_STAGING_MARKER
        marker.write_text(
            json.dumps(
                {"schemaVersion": "education-staging-v1", "runId": run_id},
                separators=(",", ":"),
            ),
            encoding="utf-8",
        )
        output_root = run_root / "output"
        output_root.mkdir()
    except Exception:
        if run_root.exists():
            shutil.rmtree(run_root, ignore_errors=True)
        raise
    return EducationStagingRun(run_id, run_root, output_root)


def cleanup_education_staging_run(
    staging: EducationStagingRun,
    *,
    public_root: Path = EDUCATION_DATA_DIR,
) -> None:
    """Remove somente um run marcado e previamente validado como seguro."""
    run_root = _validate_staging_location(
        staging.run_root,
        public_data_root=Path(public_root).parent,
    )
    marker = run_root / EDUCATION_STAGING_MARKER
    if not run_root.exists():
        return
    if not marker.is_file():
        raise EducationStagingError(
            f"Recusa ao limpar staging sem marcador de seguranca: {run_root}."
        )
    shutil.rmtree(run_root)


def render_education_json(payload: Any) -> bytes:
    """Serializa deterministicamente sem aceitar constantes nao finitas."""
    return json.dumps(
        payload,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8")


def _reject_non_finite_constant(value: str) -> None:
    raise ValueError(f"Constante JSON nao finita: {value}.")


def _load_json_object(path: Path, *, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=_reject_non_finite_constant,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise EducationValidationError(f"{label} invalido: {exc}") from exc
    if not isinstance(payload, dict) or not payload:
        raise EducationValidationError(
            f"{label} deve ser um objeto JSON nao vazio."
        )
    _validate_finite_values(payload, label=label)
    return payload


def _validate_finite_values(value: Any, *, label: str) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise EducationValidationError(f"{label} contem NaN ou Infinity.")
    if isinstance(value, Mapping):
        for child in value.values():
            _validate_finite_values(child, label=label)
    elif isinstance(value, list):
        for child in value:
            _validate_finite_values(child, label=label)


def _require_exact_fields(
    payload: Mapping[str, Any],
    expected: frozenset[str],
    *,
    label: str,
) -> None:
    fields = set(payload)
    missing = sorted(expected - fields)
    extra = sorted(fields - expected)
    if missing or extra:
        raise EducationValidationError(
            f"{label} possui schema invalido; ausentes={missing}, extras={extra}."
        )


def _validate_index(
    path: Path,
    registry: MunicipalityRegistry,
) -> tuple[dict[str, Any], str]:
    payload = _load_json_object(path, label="index.json")
    _require_exact_fields(
        payload,
        EDUCATION_INDEX_FIELDS,
        label="index.json",
    )
    updated_at = payload.get("updated_at")
    if not isinstance(updated_at, str) or not updated_at.strip():
        raise EducationValidationError(
            "index.json: updated_at deve ser texto nao vazio."
        )
    if payload.get("total_municipios") != registry.municipality_count:
        raise EducationValidationError(
            "index.json: total_municipios diverge do registro."
        )
    if payload.get("arquivos_gerados") != {
        "municipios": registry.municipality_count
    }:
        raise EducationValidationError(
            "index.json: arquivos_gerados diverge do lote integral."
        )
    if payload.get("caminhos") != {
        "municipios_index": "educacao/municipios_index.json",
        "municipios": "educacao/municipios/{id_municipio}.json",
    }:
        raise EducationValidationError(
            "index.json: caminhos publicos incompatíveis."
        )
    if payload.get("blocos_disponiveis") != list(EDUCATION_INDEX_BLOCKS):
        raise EducationValidationError(
            "index.json: blocos_disponiveis incompatíveis."
        )
    for field, expected_type in (
        ("anos_disponiveis", dict),
        ("fontes", list),
        ("avisos_metodologicos", list),
        ("campos_indisponiveis", list),
    ):
        if not isinstance(payload.get(field), expected_type):
            raise EducationValidationError(
                f"index.json: {field} possui tipo invalido."
            )
    return payload, updated_at


def _validate_municipal_document(
    path: Path,
    *,
    registry: MunicipalityRegistry,
    expected_updated_at: str,
) -> None:
    municipality_id = path.stem
    payload = _load_json_object(
        path,
        label=f"municipio {municipality_id}",
    )
    _require_exact_fields(
        payload,
        MUNICIPAL_DOCUMENT_FIELDS,
        label=f"municipio {municipality_id}",
    )
    if (
        not isinstance(payload.get("id_municipio"), str)
        or payload["id_municipio"] != municipality_id
        or re.fullmatch(r"\d{7}", municipality_id) is None
    ):
        raise EducationValidationError(
            f"{municipality_id}: codigo IBGE textual diverge do caminho."
        )
    try:
        record = registry.get_by_id(municipality_id)
    except KeyError as exc:
        raise EducationValidationError(
            f"{municipality_id}: municipio extra ao registro."
        ) from exc
    if payload.get("municipio") != record.name:
        raise EducationValidationError(
            f"{municipality_id}: nome diverge do registro municipal."
        )
    if payload.get("updated_at") != expected_updated_at:
        raise EducationValidationError(
            f"{municipality_id}: updated_at diverge do manifesto."
        )
    if not isinstance(payload.get("fontes"), list) or not isinstance(
        payload.get("avisos"), list
    ):
        raise EducationValidationError(
            f"{municipality_id}: fontes ou avisos possuem tipo invalido."
        )
    blocks = payload.get("blocos")
    if not isinstance(blocks, dict) or set(blocks) != set(EDUCATION_BLOCKS):
        raise EducationValidationError(
            f"{municipality_id}: conjunto de blocos educacionais invalido."
        )
    empty_blocks = [
        name for name in EDUCATION_BLOCKS
        if not isinstance(blocks.get(name), dict) or not blocks[name]
    ]
    if empty_blocks:
        raise EducationValidationError(
            f"{municipality_id}: blocos vazios ou invalidos: {empty_blocks}."
        )


def _validate_education_staging_impl(
    output_root: Path,
    registry: MunicipalityRegistry,
    route_compatibility: EducationMunicipalityRouteCompatibility,
    *,
    public_root: Path = EDUCATION_DATA_DIR,
) -> EducationValidationReport:
    """Valida integralmente a arvore prospectiva antes da promocao."""
    output_root = _validate_staging_location(
        Path(output_root),
        public_data_root=Path(public_root).parent,
    )
    if not output_root.is_dir():
        raise EducationStagingError(
            f"Arvore de saida educacional ausente: {output_root}."
        )
    expected = managed_education_relative_paths(registry)
    files = tuple(
        sorted(path for path in output_root.rglob("*") if path.is_file())
    )
    observed = {path.relative_to(output_root) for path in files}
    missing = sorted(path.as_posix() for path in expected - observed)
    extra = sorted(path.as_posix() for path in observed - expected)
    if missing or extra:
        raise EducationValidationError(
            "Staging educacional diverge da allowlist; "
            f"ausentes={missing[:10]}, extras={extra[:10]}."
        )
    allowed_directories = {Path(MANAGED_EDUCATION_MUNICIPAL_DIRECTORY)}
    observed_directories = {
        path.relative_to(output_root)
        for path in output_root.rglob("*")
        if path.is_dir()
    }
    extra_directories = sorted(
        path.as_posix() for path in observed_directories - allowed_directories
    )
    if extra_directories:
        raise EducationValidationError(
            "Staging educacional contem diretorios fora do contrato: "
            f"{extra_directories[:10]}."
        )

    _index, updated_at = _validate_index(output_root / "index.json", registry)
    municipalities_index = _load_json_object(
        output_root / "municipios_index.json",
        label="municipios_index.json",
    )
    expected_index = build_education_municipalities_index_payload(
        registry,
        route_compatibility,
    )
    if municipalities_index != expected_index:
        raise EducationValidationError(
            "municipios_index.json diverge do registro ou dos slugs compativeis."
        )

    municipal_root = output_root / MANAGED_EDUCATION_MUNICIPAL_DIRECTORY
    for record in registry.ordered_records:
        _validate_municipal_document(
            municipal_root / f"{record.ibge_code}.json",
            registry=registry,
            expected_updated_at=updated_at,
        )
    return EducationValidationReport(
        files=tuple(output_root / relative for relative in sorted(expected)),
        municipality_count=registry.municipality_count,
        updated_at=updated_at,
    )


def validate_education_staging(
    output_root: Path,
    registry: MunicipalityRegistry,
    route_compatibility: EducationMunicipalityRouteCompatibility,
    *,
    public_root: Path = EDUCATION_DATA_DIR,
) -> EducationValidationReport:
    with profile_operation(
        "validation",
        "education.staging_validation",
        metadata={"stagingRoot": output_root},
    ) as operation:
        report = _validate_education_staging_impl(
            output_root,
            registry,
            route_compatibility,
            public_root=public_root,
        )
        operation.add_counters(
            filesRead=len(report.files),
            bytesRead=sum(path.stat().st_size for path in report.files),
            payloadsVerified=len(report.files),
            municipalities=report.municipality_count,
        )
        return report


def iter_managed_education_public_files(public_root: Path) -> tuple[Path, ...]:
    """Lista somente arquivos que a publicacao principal pode substituir/remover."""
    public_root = Path(public_root)
    managed: list[Path] = []
    for name in sorted(MANAGED_EDUCATION_ROOT_FILES):
        path = public_root / name
        if path.is_file():
            managed.append(path)
    municipal_root = public_root / MANAGED_EDUCATION_MUNICIPAL_DIRECTORY
    if municipal_root.is_dir():
        managed.extend(
            sorted(
                path
                for path in municipal_root.iterdir()
                if path.is_file()
                and MANAGED_EDUCATION_MUNICIPAL_PATTERN.fullmatch(path.name)
                is not None
            )
        )
    return tuple(managed)


def files_match(source: Path, target: Path) -> bool:
    session = get_active_profile_session()
    started_ns = time.perf_counter_ns() if session is not None else 0
    bytes_compared = 0
    if not target.is_file() or source.stat().st_size != target.stat().st_size:
        if session is not None:
            session.accumulate_event(
                category="read",
                name="education.file_comparison",
                duration_ns=time.perf_counter_ns() - started_ns,
                counters={"filesCompared": 1, "bytesCompared": 0},
            )
        return False
    with source.open("rb") as source_stream, target.open("rb") as target_stream:
        while True:
            source_chunk = source_stream.read(1024 * 1024)
            target_chunk = target_stream.read(1024 * 1024)
            bytes_compared += len(source_chunk) + len(target_chunk)
            if source_chunk != target_chunk:
                if session is not None:
                    session.accumulate_event(
                        category="read",
                        name="education.file_comparison",
                        duration_ns=time.perf_counter_ns() - started_ns,
                        counters={
                            "filesCompared": 1,
                            "bytesCompared": bytes_compared,
                        },
                    )
                return False
            if not source_chunk:
                if session is not None:
                    session.accumulate_event(
                        category="read",
                        name="education.file_comparison",
                        duration_ns=time.perf_counter_ns() - started_ns,
                        counters={
                            "filesCompared": 1,
                            "bytesCompared": bytes_compared,
                        },
                    )
                return True


def _matches_ignoring_publication_date(
    staged: Path,
    target: Path,
    relative: Path,
) -> bool:
    """Detecta lote sem mudança de fonte apesar da data operacional do run."""
    if not target.is_file() or relative.as_posix() == "municipios_index.json":
        return False
    try:
        staged_payload = json.loads(
            staged.read_text(encoding="utf-8"),
            parse_constant=_reject_non_finite_constant,
        )
        target_payload = json.loads(
            target.read_text(encoding="utf-8"),
            parse_constant=_reject_non_finite_constant,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        return False
    if not isinstance(staged_payload, dict) or not isinstance(target_payload, dict):
        return False
    if not all(
        isinstance(payload.get("updated_at"), str)
        and payload["updated_at"].strip()
        for payload in (staged_payload, target_payload)
    ):
        return False
    staged_payload.pop("updated_at", None)
    target_payload.pop("updated_at", None)
    return staged_payload == target_payload


def _copy_file_atomically(source: Path, target: Path, *, token: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{target.name}.education-{token}-",
        suffix=".tmp",
        dir=target.parent,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as destination, source.open("rb") as origin:
            shutil.copyfileobj(origin, destination, length=1024 * 1024)
            destination.flush()
            os.fsync(destination.fileno())
        shutil.copystat(source, temporary)
        os.replace(temporary, target)
    finally:
        if temporary.exists():
            temporary.unlink()


def _build_promotion_actions_impl(
    output_root: Path,
    public_root: Path,
    report: EducationValidationReport,
) -> tuple[list[_PromotionAction], EducationPublicationStats]:
    staged_targets = [
        (
            staged,
            staged.relative_to(output_root),
            public_root / staged.relative_to(output_root),
        )
        for staged in report.files
    ]
    semantic_noop = all(
        target.is_file()
        and (
            files_match(staged, target)
            or _matches_ignoring_publication_date(staged, target, relative)
        )
        for staged, relative, target in staged_targets
    )
    expected_targets: set[Path] = set()
    actions: list[_PromotionAction] = []
    created = updated = preserved = 0
    for staged, relative, target in staged_targets:
        expected_targets.add(target.resolve())
        if target.exists() and not target.is_file():
            raise EducationPromotionError(
                f"Destino administrado nao e arquivo: {target}."
            )
        if semantic_noop or files_match(staged, target):
            preserved += 1
            continue
        kind = "updated" if target.is_file() else "created"
        actions.append(_PromotionAction(kind, relative, staged, target))
        if kind == "created":
            created += 1
        else:
            updated += 1

    removals = []
    for target in iter_managed_education_public_files(public_root):
        if target.resolve() in expected_targets:
            continue
        relative = target.relative_to(public_root)
        if not is_managed_education_public_path(relative):
            raise EducationPromotionError(
                f"Recusa ao remover caminho fora da allowlist: {relative}."
            )
        removals.append(_PromotionAction("removed", relative, None, target))
    actions.extend(sorted(removals, key=lambda action: action.relative.as_posix()))
    return actions, EducationPublicationStats(
        created=created,
        updated=updated,
        preserved=preserved,
        removed=len(removals),
    )


def _build_promotion_actions(
    output_root: Path,
    public_root: Path,
    report: EducationValidationReport,
) -> tuple[list[_PromotionAction], EducationPublicationStats]:
    with profile_operation(
        "promotion",
        "education.promotion_plan",
        metadata={"eventGranularity": "aggregate"},
    ) as operation:
        actions, stats = _build_promotion_actions_impl(
            output_root,
            public_root,
            report,
        )
        bytes_promoted = sum(
            action.staged.stat().st_size
            for action in actions
            if action.staged is not None and action.kind in {"created", "updated"}
        )
        operation.add_counters(
            filesEvaluated=len(report.files),
            created=stats.created,
            updated=stats.updated,
            preserved=stats.preserved,
            removed=stats.removed,
            bytesPromoted=bytes_promoted,
            noOp=int(not actions),
        )
        return actions, stats


def _promote_education_staging_impl(
    output_root: Path,
    public_root: Path,
    registry: MunicipalityRegistry,
    route_compatibility: EducationMunicipalityRouteCompatibility,
    *,
    before_mutation: Callable[[str, Path, int], None] | None = None,
) -> EducationPublicationStats:
    """Promove por arquivo com journal, backups integrais e rollback."""
    profile_session = get_active_profile_session()
    output_root = Path(output_root).resolve()
    public_root = Path(public_root).resolve()
    if not public_root.is_dir():
        raise EducationPromotionError(
            f"Diretorio publico educacional ausente: {public_root}."
        )
    report = validate_education_staging(
        output_root,
        registry,
        route_compatibility,
        public_root=public_root,
    )
    actions, stats = _build_promotion_actions(output_root, public_root, report)
    if not actions:
        return stats

    token = uuid.uuid4().hex
    backup_root = output_root.parent / f".rollback-{token}"
    backup_root.mkdir(parents=False, exist_ok=False)
    backups: dict[Path, Path] = {}
    prepared: dict[Path, Path] = {}
    applied: list[_PromotionAction] = []
    created_target_directories: list[Path] = []
    rollback_failed = False
    try:
        for action in actions:
            if action.kind in {"updated", "removed"}:
                backup = backup_root / action.relative
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(action.target, backup)
                if not files_match(action.target, backup):
                    raise EducationPromotionError(
                        f"Backup de promocao divergiu: {action.relative}."
                    )
                backups[action.relative] = backup
            if action.kind in {"created", "updated"}:
                target_parent = action.target.parent
                if not target_parent.exists():
                    target_parent.mkdir(parents=False, exist_ok=False)
                    created_target_directories.append(target_parent)
                elif not target_parent.is_dir():
                    raise EducationPromotionError(
                        f"Diretorio de destino administrado invalido: {target_parent}."
                    )
                descriptor, temporary_name = tempfile.mkstemp(
                    prefix=f".{action.target.name}.education-{token}-",
                    suffix=".tmp",
                    dir=action.target.parent,
                )
                temporary = Path(temporary_name)
                with os.fdopen(descriptor, "wb") as destination, action.staged.open(
                    "rb"
                ) as source:
                    shutil.copyfileobj(source, destination, length=1024 * 1024)
                    destination.flush()
                    os.fsync(destination.fileno())
                if not files_match(action.staged, temporary):
                    temporary.unlink(missing_ok=True)
                    raise EducationPromotionError(
                        f"Temporario de promocao divergiu: {action.relative}."
                    )
                prepared[action.relative] = temporary

        for position, action in enumerate(actions, start=1):
            if before_mutation is not None:
                before_mutation(action.kind, action.relative, position)
            if action.kind in {"created", "updated"}:
                os.replace(prepared[action.relative], action.target)
                prepared.pop(action.relative, None)
            else:
                action.target.unlink()
            applied.append(action)
    except Exception as exc:
        rollback_started_ns = (
            time.perf_counter_ns() if profile_session is not None else 0
        )
        rollback_errors: list[str] = []
        for temporary in prepared.values():
            try:
                temporary.unlink(missing_ok=True)
            except Exception as rollback_exc:  # pragma: no cover - falha de SO
                rollback_errors.append(f"temporario {temporary}: {rollback_exc}")
        prepared.clear()
        for action in reversed(applied):
            try:
                if action.kind == "created":
                    if action.target.exists():
                        action.target.unlink()
                else:
                    backup = backups[action.relative]
                    _copy_file_atomically(backup, action.target, token=token)
            except Exception as rollback_exc:  # pragma: no cover - falha de SO
                rollback_errors.append(
                    f"{action.relative.as_posix()}: {rollback_exc}"
                )
        for directory in reversed(created_target_directories):
            try:
                directory.rmdir()
            except Exception as rollback_exc:  # pragma: no cover - falha de SO
                rollback_errors.append(
                    f"diretorio {directory.relative_to(public_root)}: {rollback_exc}"
                )
        if profile_session is not None:
            profile_session.record_aggregate_event(
                category="promotion",
                name="education.rollback",
                duration_ns=time.perf_counter_ns() - rollback_started_ns,
                counters={
                    "rollbackAttempts": 1,
                    "actionsReverted": len(applied),
                    "rollbackErrors": len(rollback_errors),
                },
                metadata={"publicationRestored": not rollback_errors},
                status="error" if rollback_errors else "success",
            )
        if rollback_errors:
            rollback_failed = True
            raise EducationRollbackError(
                "Rollback educacional incompleto; backup preservado em "
                f"{backup_root}: {rollback_errors[:5]}"
            ) from exc
        raise EducationPromotionError(
            f"Promocao educacional falhou; publicacao anterior restaurada: {exc}"
        ) from exc
    finally:
        for temporary in prepared.values():
            temporary.unlink(missing_ok=True)
        if backup_root.exists() and not rollback_failed:
            shutil.rmtree(backup_root)
    return stats


def promote_education_staging(
    output_root: Path,
    public_root: Path,
    registry: MunicipalityRegistry,
    route_compatibility: EducationMunicipalityRouteCompatibility,
    *,
    before_mutation: Callable[[str, Path, int], None] | None = None,
) -> EducationPublicationStats:
    with profile_operation(
        "promotion",
        "education.promotion",
        metadata={"publicRoot": public_root},
    ) as operation:
        stats = _promote_education_staging_impl(
            output_root,
            public_root,
            registry,
            route_compatibility,
            before_mutation=before_mutation,
        )
        operation.add_counters(
            created=stats.created,
            updated=stats.updated,
            preserved=stats.preserved,
            removed=stats.removed,
            noOp=int(
                stats.created == 0
                and stats.updated == 0
                and stats.removed == 0
            ),
        )
        return stats


def publish_education_transactionally(
    *,
    registry: MunicipalityRegistry,
    route_compatibility: EducationMunicipalityRouteCompatibility,
    materialize: Callable[[Path], None],
    public_root: Path = EDUCATION_DATA_DIR,
    staging_directory: Path | None = None,
    no_promote: bool = False,
    before_mutation: Callable[[str, Path, int], None] | None = None,
) -> EducationTransactionResult:
    """Executa materializacao, validacao integral e somente entao promocao."""
    with profile_operation(
        "write",
        "education.staging_create",
        metadata={"customDirectory": staging_directory is not None},
    ) as staging_event:
        staging = create_education_staging_run(
            staging_directory,
            public_root=public_root,
        )
        staging_event.add_counter("directoriesCreated", 2)
    validated = False
    preserve_staging = False
    try:
        with profile_operation(
            "compute",
            "education.materialization",
            metadata={"eventGranularity": "aggregate"},
        ):
            materialize(staging.output_root)
        report = validate_education_staging(
            staging.output_root,
            registry,
            route_compatibility,
            public_root=public_root,
        )
        validated = True
        if no_promote:
            preserve_staging = True
            with profile_operation(
                "promotion",
                "education.promotion_skipped",
                counters={"noPromote": 1, "filesPreservedInStaging": len(report.files)},
                metadata={"reason": "no_promote"},
            ):
                pass
            return EducationTransactionResult(report, None, staging.output_root)
        stats = promote_education_staging(
            staging.output_root,
            public_root,
            registry,
            route_compatibility,
            before_mutation=before_mutation,
        )
        return EducationTransactionResult(report, stats, None)
    except EducationRollbackError:
        preserve_staging = True
        raise
    finally:
        if not preserve_staging or not validated:
            with profile_operation(
                "promotion",
                "education.staging_cleanup",
                metadata={"validated": validated},
            ) as cleanup_event:
                cleanup_education_staging_run(staging, public_root=public_root)
                cleanup_event.add_counter("stagingRunsRemoved", 1)


def default_public_root(state_code: object = DEFAULT_STATE_CODE) -> Path:
    """Fronteira publica unica; a raiz vem do manifesto de publicacao da UF.

    O exportador continua sem conhecer ``public/data`` diretamente: o estado
    padrao resolve a raiz historica e qualquer outra UF resolve a propria raiz
    publicada, sem fallback silencioso para a publicacao alheia.
    """
    if EDUCATION_DATA_DIR.parent != PUBLIC_DATA_DIR:
        raise EducationPublicationError(
            "Configuracao do diretorio publico educacional inconsistente."
        )
    try:
        education_root = resolve_education_data_dir(state_code)
    except (FileNotFoundError, StatePublicationError, ValueError) as exc:
        raise EducationPublicationError(
            f"Raiz publica educacional indisponivel para {state_code!r}: {exc}"
        ) from exc
    if (
        normalize_state_code(state_code) == DEFAULT_STATE_CODE
        and education_root != EDUCATION_DATA_DIR.resolve()
    ):
        raise EducationPublicationError(
            "Configuracao do diretorio publico educacional inconsistente."
        )
    return education_root
