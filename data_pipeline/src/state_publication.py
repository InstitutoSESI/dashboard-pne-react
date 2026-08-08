"""Contrato estrito que liga um produto estadual aos seus artefatos publicados."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from .config import DEFAULT_PUBLIC_DATA_DIR, REPO_ROOT
from .state_config import DEFAULT_STATE_CODE, normalize_state_code


STATE_PUBLICATION_SCHEMA_VERSION = "state-publication-v3"
ANALYTICS_STATUSES = frozenset({"complete", "partial", "identity-only"})
#: Produtos analíticos navegáveis; `partial` habilita um subconjunto explícito.
ANALYTICS_PRODUCTS = ("pne", "educacao", "financiamento")
_PUBLICATION_FIELDS = frozenset(
    {
        "schemaVersion",
        "stateCode",
        "stateConfigPath",
        "municipalityRegistryPath",
        "publicDataDirectory",
        "analyticsStatus",
        "analyticsMessage",
        "enabledProducts",
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
    enabled_products: tuple[str, ...] | None

    def product_enabled(self, product: str) -> bool:
        """Publicação completa habilita tudo; `partial` só o que declarou."""
        if self.analytics_status == "complete":
            return product in ANALYTICS_PRODUCTS
        if self.analytics_status == "partial":
            return product in (self.enabled_products or ())
        return False


def _require_non_empty_string(payload: dict[str, Any], field: str) -> str:
    value = payload[field]
    if not isinstance(value, str) or not value.strip():
        raise StatePublicationError(
            f"Publicação estadual inválida: {field!r} deve ser texto não vazio."
        )
    return value


def _parse_enabled_products(
    value: object,
    *,
    analytics_status: str,
) -> tuple[str, ...] | None:
    """`partial` exige lista explícita; os demais status exigem ``null``."""
    if analytics_status != "partial":
        if value is not None:
            raise StatePublicationError(
                f"Publicação {analytics_status} deve declarar enabledProducts null."
            )
        return None
    if not isinstance(value, list) or not value:
        raise StatePublicationError(
            "Publicação partial exige enabledProducts como lista não vazia."
        )
    products: list[str] = []
    for item in value:
        if not isinstance(item, str) or item not in ANALYTICS_PRODUCTS:
            raise StatePublicationError(
                f"Produto analítico desconhecido em enabledProducts: {item!r}."
            )
        if item in products:
            raise StatePublicationError(
                f"Produto analítico duplicado em enabledProducts: {item!r}."
            )
        products.append(item)
    if len(products) == len(ANALYTICS_PRODUCTS):
        raise StatePublicationError(
            "Publicação com todos os produtos habilitados deve declarar "
            "analyticsStatus complete."
        )
    return tuple(products)


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
    if analytics_status in {"identity-only", "partial"} and (
        not isinstance(analytics_message, str) or not analytics_message.strip()
    ):
        raise StatePublicationError(
            f"Publicação {analytics_status} exige analyticsMessage não vazio."
        )
    enabled_products = _parse_enabled_products(
        payload["enabledProducts"],
        analytics_status=analytics_status,
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
        enabled_products=enabled_products,
    )


def resolve_public_data_dir(
    state_code: object = DEFAULT_STATE_CODE,
    *,
    repo_root: Path = REPO_ROOT,
) -> Path:
    """Raiz pública publicada da UF, declarada no manifesto de publicação.

    RS resolve ``public/data``; AL resolve ``state-publications/al/data``. Não há
    fallback: uma UF sem manifesto falha em vez de escrever na raiz de outra.
    """
    publication = load_state_publication(state_code, repo_root=repo_root)
    resolved = publication.public_data_directory
    if publication.state_code == DEFAULT_STATE_CODE and resolved != DEFAULT_PUBLIC_DATA_DIR.resolve():
        raise StatePublicationError(
            "A raiz pública do estado padrão não pode divergir de "
            f"{DEFAULT_PUBLIC_DATA_DIR}."
        )
    return resolved


def resolve_education_data_dir(
    state_code: object = DEFAULT_STATE_CODE,
    *,
    repo_root: Path = REPO_ROOT,
) -> Path:
    """Raiz educacional administrada da UF, sempre sob a raiz publicada."""
    return resolve_public_data_dir(state_code, repo_root=repo_root) / "educacao"
