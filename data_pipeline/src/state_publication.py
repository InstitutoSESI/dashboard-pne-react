"""Contrato estrito que liga um produto estadual aos seus artefatos publicados."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from .config import REPO_ROOT
from .state_config import normalize_state_code


STATE_PUBLICATION_SCHEMA_VERSION = "state-publication-v2"
ANALYTICS_STATUSES = frozenset({"complete", "identity-only"})
_PUBLICATION_FIELDS = frozenset(
    {
        "schemaVersion",
        "stateCode",
        "stateConfigPath",
        "municipalityRegistryPath",
        "publicDataDirectory",
        "analyticsStatus",
        "analyticsMessage",
    }
)


class StatePublicationError(ValueError):
    """Indica que um perfil estadual de publicação não cumpre o contrato."""


@dataclass(frozen=True, slots=True)
class StatePublication:
    schema_version: str
    state_code: str
    state_config_path: Path
    municipality_registry_path: Path
    public_data_directory: Path
    analytics_status: str
    analytics_message: str | None


def _require_non_empty_string(payload: dict[str, Any], field: str) -> str:
    value = payload[field]
    if not isinstance(value, str) or not value.strip():
        raise StatePublicationError(
            f"Publicação estadual inválida: {field!r} deve ser texto não vazio."
        )
    return value


def _resolve_repository_path(repo_root: Path, value: str, *, field: str) -> Path:
    configured = Path(value)
    if configured.is_absolute():
        raise StatePublicationError(
            f"Publicação estadual inválida: {field!r} deve ser relativo ao repositório."
        )
    resolved_root = repo_root.resolve()
    resolved = (resolved_root / configured).resolve()
    if resolved == resolved_root or resolved_root not in resolved.parents:
        raise StatePublicationError(
            f"Publicação estadual inválida: {field!r} escapa do repositório."
        )
    if resolved.relative_to(resolved_root).parts[0] in {
        ".git",
        "build",
        "dist",
        "node_modules",
    }:
        raise StatePublicationError(
            f"Publicação estadual inválida: {field!r} usa árvore operacional proibida."
        )
    return resolved


def load_state_publication(
    state_code: object,
    *,
    repo_root: Path = REPO_ROOT,
) -> StatePublication:
    normalized = normalize_state_code(state_code)
    resolved_root = Path(repo_root).resolve()
    manifest_path = (
        resolved_root / "config" / "publications" / f"{normalized.lower()}.json"
    )
    if not manifest_path.is_file():
        raise FileNotFoundError(
            f"Publicação estadual não encontrada para {normalized}: {manifest_path}."
        )
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise StatePublicationError(
            f"Publicação estadual inválida em {manifest_path}: JSON malformado: {exc}."
        ) from exc
    if not isinstance(payload, dict):
        raise StatePublicationError(
            "Publicação estadual inválida: o documento deve ser um objeto."
        )
    fields = set(payload)
    if fields != _PUBLICATION_FIELDS:
        missing = sorted(_PUBLICATION_FIELDS - fields)
        unexpected = sorted(fields - _PUBLICATION_FIELDS)
        details = []
        if missing:
            details.append("ausentes: " + ", ".join(missing))
        if unexpected:
            details.append("inesperados: " + ", ".join(unexpected))
        raise StatePublicationError(
            "Publicação estadual inválida: campos divergentes ("
            + "; ".join(details)
            + ")."
        )
    if payload["schemaVersion"] != STATE_PUBLICATION_SCHEMA_VERSION:
        raise StatePublicationError(
            "Publicação estadual inválida: schemaVersion deve ser "
            f"{STATE_PUBLICATION_SCHEMA_VERSION!r}."
        )
    if payload["stateCode"] != normalized:
        raise StatePublicationError(
            f"Publicação estadual inválida: stateCode diverge de {normalized}."
        )

    analytics_status = _require_non_empty_string(payload, "analyticsStatus")
    if analytics_status not in ANALYTICS_STATUSES:
        raise StatePublicationError(
            "Publicação estadual inválida: analyticsStatus desconhecido."
        )
    analytics_message = payload["analyticsMessage"]
    if analytics_status == "complete" and analytics_message is not None:
        raise StatePublicationError(
            "Publicação completa deve declarar analyticsMessage null."
        )
    if analytics_status == "identity-only" and (
        not isinstance(analytics_message, str) or not analytics_message.strip()
    ):
        raise StatePublicationError(
            "Publicação identity-only exige analyticsMessage não vazio."
        )

    return StatePublication(
        schema_version=STATE_PUBLICATION_SCHEMA_VERSION,
        state_code=normalized,
        state_config_path=_resolve_repository_path(
            resolved_root,
            _require_non_empty_string(payload, "stateConfigPath"),
            field="stateConfigPath",
        ),
        municipality_registry_path=_resolve_repository_path(
            resolved_root,
            _require_non_empty_string(payload, "municipalityRegistryPath"),
            field="municipalityRegistryPath",
        ),
        public_data_directory=_resolve_repository_path(
            resolved_root,
            _require_non_empty_string(payload, "publicDataDirectory"),
            field="publicDataDirectory",
        ),
        analytics_status=analytics_status,
        analytics_message=analytics_message,
    )
