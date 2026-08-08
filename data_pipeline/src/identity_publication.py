"""Materialização e validação da publicação municipal somente de identidade."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
from typing import Any

from .municipality_registry import MunicipalityRegistry
from .state_config import StateConfig
from .state_publication import StatePublication


IDENTITY_PUBLICATION_SCHEMA_VERSION = "state-identity-publication-v1"
MUNICIPAL_IDENTITY_SCHEMA_VERSION = "municipality-identity-publication-v1"
ANALYTICS_UNAVAILABLE_REASON = "analytics_not_published"


class IdentityPublicationError(ValueError):
    """Indica que uma publicação somente de identidade é incompleta ou inválida."""


@dataclass(frozen=True, slots=True)
class PromotionResult:
    changed_files: int
    preserved_files: int
    removed_files: int
    publication_noop: bool


def _json_bytes(payload: object) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    ).encode("utf-8")


def build_identity_publication_files(
    *,
    publication: StatePublication,
    state_config: StateConfig,
    registry: MunicipalityRegistry,
    generated_at: str,
    source_manifest_path: str,
    source_manifest_sha256: str,
    response_body_sha256: str,
) -> dict[PurePosixPath, bytes]:
    if publication.analytics_status != "identity-only":
        raise IdentityPublicationError(
            "Somente perfis identity-only podem usar esta materialização."
        )
    if publication.state_code != state_config.state_code:
        raise IdentityPublicationError("Publicação e configuração estadual divergem.")
    if registry.state_code != state_config.state_code:
        raise IdentityPublicationError("Registro e configuração estadual divergem.")
    if not isinstance(generated_at, str) or not generated_at.strip():
        raise IdentityPublicationError("generated_at deve ser texto não vazio.")
    for label, digest in (
        ("source_manifest_sha256", source_manifest_sha256),
        ("response_body_sha256", response_body_sha256),
    ):
        if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
            raise IdentityPublicationError(f"{label} deve ser SHA-256 hexadecimal.")

    analytics_message = publication.analytics_message
    assert isinstance(analytics_message, str)
    files: dict[PurePosixPath, bytes] = {
        PurePosixPath("publication.json"): _json_bytes(
            {
                "schemaVersion": IDENTITY_PUBLICATION_SCHEMA_VERSION,
                "stateCode": state_config.state_code,
                "stateName": state_config.state_name,
                "publicationStatus": "identity-only",
                "analyticsStatus": "unavailable",
                "analyticsMessage": analytics_message,
                "municipalityCount": registry.municipality_count,
                "generatedAt": generated_at,
                "source": {
                    "provider": "IBGE",
                    "manifestPath": source_manifest_path,
                    "manifestSha256": source_manifest_sha256,
                    "responseBodySha256": response_body_sha256,
                },
            }
        ),
        PurePosixPath("municipios_index.json"): _json_bytes(
            registry.build_public_index_payload(generated_at=generated_at)
        ),
    }
    for record in registry.ordered_records:
        files[
            PurePosixPath("municipios") / record.ibge_code / "index.json"
        ] = _json_bytes(
            {
                "schemaVersion": MUNICIPAL_IDENTITY_SCHEMA_VERSION,
                "stateCode": state_config.state_code,
                "publicationStatus": "identity-only",
                "id_municipio": record.ibge_code,
                "municipio": record.name,
                "slug": record.slug,
                "analytics": {
                    "status": "unavailable",
                    "reason": ANALYTICS_UNAVAILABLE_REASON,
                    "message": analytics_message,
                },
            }
        )
    return files


def write_staged_publication(
    files: Mapping[PurePosixPath, bytes],
    staging_root: Path,
) -> None:
    root = Path(staging_root)
    if root.exists() and any(root.iterdir()):
        raise IdentityPublicationError(f"Staging não está vazio: {root}.")
    root.mkdir(parents=True, exist_ok=True)
    for relative_path, content in sorted(files.items(), key=lambda item: str(item[0])):
        target = root.joinpath(*relative_path.parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(target.name + ".tmp")
        temporary.write_bytes(content)
        os.replace(temporary, target)


def _read_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise IdentityPublicationError(f"JSON inválido em {path}: {exc}.") from exc


def validate_identity_publication(
    root: Path,
    *,
    publication: StatePublication,
    state_config: StateConfig,
    registry: MunicipalityRegistry,
    generated_at: str,
    source_manifest_path: str,
    source_manifest_sha256: str,
    response_body_sha256: str,
) -> None:
    root = Path(root)
    if not root.is_dir():
        raise IdentityPublicationError(f"Raiz publicada ausente: {root}.")
    expected_files = {
        PurePosixPath("publication.json"),
        PurePosixPath("municipios_index.json"),
        *(
            PurePosixPath("municipios") / record.ibge_code / "index.json"
            for record in registry.ordered_records
        ),
    }
    observed_files = {
        PurePosixPath(path.relative_to(root).as_posix())
        for path in root.rglob("*")
        if path.is_file()
    }
    if observed_files != expected_files:
        missing = sorted(str(path) for path in expected_files - observed_files)
        unexpected = sorted(str(path) for path in observed_files - expected_files)
        raise IdentityPublicationError(
            "Conjunto publicado divergente; "
            f"ausentes={missing}, inesperados={unexpected}."
        )

    manifest = _read_json(root / "publication.json")
    if not isinstance(manifest, dict):
        raise IdentityPublicationError("publication.json deve ser objeto.")
    expected_manifest_fields = {
        "schemaVersion",
        "stateCode",
        "stateName",
        "publicationStatus",
        "analyticsStatus",
        "analyticsMessage",
        "municipalityCount",
        "generatedAt",
        "source",
    }
    if set(manifest) != expected_manifest_fields:
        raise IdentityPublicationError("publication.json possui campos divergentes.")
    if manifest.get("schemaVersion") != IDENTITY_PUBLICATION_SCHEMA_VERSION:
        raise IdentityPublicationError("publication.json possui schema desconhecido.")
    expected_manifest_values = {
        "stateCode": state_config.state_code,
        "stateName": state_config.state_name,
        "publicationStatus": "identity-only",
        "analyticsStatus": "unavailable",
        "analyticsMessage": publication.analytics_message,
        "municipalityCount": registry.municipality_count,
    }
    for field, expected in expected_manifest_values.items():
        if manifest.get(field) != expected:
            raise IdentityPublicationError(
                f"publication.json diverge em {field}: {manifest.get(field)!r}."
            )
    if manifest.get("generatedAt") != generated_at:
        raise IdentityPublicationError("publication.json diverge no instante de origem.")
    expected_source = {
        "provider": "IBGE",
        "manifestPath": source_manifest_path,
        "manifestSha256": source_manifest_sha256,
        "responseBodySha256": response_body_sha256,
    }
    if manifest.get("source") != expected_source:
        raise IdentityPublicationError("publication.json diverge na proveniência.")

    expected_index = registry.build_public_index_payload(generated_at=generated_at)
    if _read_json(root / "municipios_index.json") != expected_index:
        raise IdentityPublicationError(
            "municipios_index.json diverge do registro municipal canônico."
        )
    for record in registry.ordered_records:
        payload = _read_json(root / "municipios" / record.ibge_code / "index.json")
        if not isinstance(payload, dict):
            raise IdentityPublicationError(
                f"Índice municipal de {record.ibge_code} deve ser objeto."
            )
        expected_identity = {
            "schemaVersion": MUNICIPAL_IDENTITY_SCHEMA_VERSION,
            "stateCode": state_config.state_code,
            "publicationStatus": "identity-only",
            "id_municipio": record.ibge_code,
            "municipio": record.name,
            "slug": record.slug,
            "analytics": {
                "status": "unavailable",
                "reason": ANALYTICS_UNAVAILABLE_REASON,
                "message": publication.analytics_message,
            },
        }
        if payload != expected_identity:
            raise IdentityPublicationError(
                f"Índice municipal de {record.ibge_code} diverge do cadastro."
            )


def _files_by_relative_path(root: Path) -> dict[Path, Path]:
    if not root.exists():
        return {}
    return {
        path.relative_to(root): path
        for path in root.rglob("*")
        if path.is_file()
    }


def _same_content(left: Path, right: Path) -> bool:
    if left.stat().st_size != right.stat().st_size:
        return False
    return hashlib.sha256(left.read_bytes()).digest() == hashlib.sha256(
        right.read_bytes()
    ).digest()


def _remove_empty_directories(root: Path) -> None:
    if not root.exists():
        return
    for directory in sorted(
        (path for path in root.rglob("*") if path.is_dir()),
        key=lambda path: len(path.parts),
        reverse=True,
    ):
        try:
            directory.rmdir()
        except OSError:
            pass


def promote_staged_publication(
    staging_root: Path,
    target_root: Path,
    *,
    validate_target: Callable[[Path], None],
) -> PromotionResult:
    staging_root = Path(staging_root)
    target_root = Path(target_root)
    staged_files = _files_by_relative_path(staging_root)
    if not staged_files:
        raise IdentityPublicationError("Staging validado não contém arquivos.")
    target_files = _files_by_relative_path(target_root)
    changed = sorted(
        relative
        for relative, staged in staged_files.items()
        if relative not in target_files or not _same_content(staged, target_files[relative])
    )
    preserved = len(staged_files) - len(changed)
    stale = sorted(set(target_files) - set(staged_files))
    if not changed and not stale:
        validate_target(target_root)
        shutil.rmtree(staging_root)
        return PromotionResult(0, preserved, 0, True)

    backup_root = staging_root.parent / f"{staging_root.name}-backup"
    if backup_root.exists():
        shutil.rmtree(backup_root)
    target_root.mkdir(parents=True, exist_ok=True)
    backed_up: list[Path] = []
    promoted: list[Path] = []
    try:
        for relative in [*changed, *stale]:
            target = target_root / relative
            if not target.is_file():
                continue
            backup = backup_root / relative
            backup.parent.mkdir(parents=True, exist_ok=True)
            os.replace(target, backup)
            backed_up.append(relative)
        for relative in changed:
            source = staging_root / relative
            target = target_root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            os.replace(source, target)
            promoted.append(relative)
        validate_target(target_root)
    except Exception:
        for relative in reversed(promoted):
            target = target_root / relative
            if target.exists():
                target.unlink()
        for relative in reversed(backed_up):
            backup = backup_root / relative
            target = target_root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            if backup.exists():
                os.replace(backup, target)
        _remove_empty_directories(target_root)
        raise
    else:
        shutil.rmtree(backup_root, ignore_errors=True)
        shutil.rmtree(staging_root, ignore_errors=True)
        _remove_empty_directories(target_root)
        return PromotionResult(len(changed), preserved, len(stale), False)
