"""Compatibilidade explícita das rotas municipais públicas da Educação."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import json
from pathlib import Path
import re
from types import MappingProxyType
import unicodedata
from typing import Any

from .config import EDUCATION_MUNICIPALITY_ROUTE_COMPATIBILITY_DIR
from .municipality_registry import (
    MunicipalityRecord,
    MunicipalityRegistry,
)
from .state_config import StateConfig


EDUCATION_MUNICIPALITY_ROUTE_COMPATIBILITY_SCHEMA_VERSION = (
    "education-municipality-route-compat-v1"
)
_COMPATIBILITY_FIELDS = frozenset({"schemaVersion", "stateCode", "slugOverrides"})


class EducationMunicipalityRouteCompatibilityError(ValueError):
    """Indica que a compatibilidade de rotas educacionais é inválida."""


@dataclass(frozen=True, slots=True)
class EducationMunicipalityRouteCompatibility:
    schema_version: str
    state_code: str
    slug_overrides: Mapping[str, str]


def resolve_education_municipality_route_compatibility_path(
    state_config: StateConfig,
    *,
    compatibility_dir: Path = EDUCATION_MUNICIPALITY_ROUTE_COMPATIBILITY_DIR,
) -> Path:
    return Path(compatibility_dir) / f"{state_config.state_code.lower()}.json"


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise EducationMunicipalityRouteCompatibilityError(
                f"Configuração de rotas educacionais contém chave JSON duplicada: {key!r}."
            )
        result[key] = value
    return result


def _validate_fields(payload: Mapping[str, Any]) -> None:
    fields = set(payload)
    missing = sorted(_COMPATIBILITY_FIELDS - fields)
    unexpected = sorted(fields - _COMPATIBILITY_FIELDS)
    if missing:
        raise EducationMunicipalityRouteCompatibilityError(
            "Configuração de rotas educacionais: campos obrigatórios ausentes: "
            + ", ".join(missing)
            + "."
        )
    if unexpected:
        raise EducationMunicipalityRouteCompatibilityError(
            "Configuração de rotas educacionais: campos inesperados: "
            + ", ".join(unexpected)
            + "."
        )


def _validate_public_slug(value: object, *, municipality_id: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or value != value.casefold()
        or re.fullmatch(r"[\w-]+", value) is None
    ):
        raise EducationMunicipalityRouteCompatibilityError(
            "Override de slug educacional inválido para "
            f"{municipality_id}: {value!r}."
        )
    return value


def _parse_compatibility(
    payload: object,
    *,
    state_config: StateConfig,
    registry: MunicipalityRegistry,
) -> EducationMunicipalityRouteCompatibility:
    if not isinstance(payload, dict):
        raise EducationMunicipalityRouteCompatibilityError(
            "Configuração de rotas educacionais deve ser um objeto JSON."
        )
    _validate_fields(payload)

    schema_version = payload["schemaVersion"]
    if schema_version != EDUCATION_MUNICIPALITY_ROUTE_COMPATIBILITY_SCHEMA_VERSION:
        raise EducationMunicipalityRouteCompatibilityError(
            "Configuração de rotas educacionais possui schemaVersion desconhecido: "
            f"{schema_version!r}."
        )
    state_code = payload["stateCode"]
    if state_code != state_config.state_code or registry.state_code != state_config.state_code:
        raise EducationMunicipalityRouteCompatibilityError(
            "Configuração de rotas, StateConfig e MunicipalityRegistry devem possuir "
            f"o mesmo estado; configuração={state_code!r}, "
            f"StateConfig={state_config.state_code!r}, registro={registry.state_code!r}."
        )

    raw_overrides = payload["slugOverrides"]
    if not isinstance(raw_overrides, dict):
        raise EducationMunicipalityRouteCompatibilityError(
            "slugOverrides deve ser um objeto indexado por código IBGE textual."
        )

    overrides: dict[str, str] = {}
    for municipality_id, raw_slug in raw_overrides.items():
        if not isinstance(municipality_id, str) or re.fullmatch(r"\d{7}", municipality_id) is None:
            raise EducationMunicipalityRouteCompatibilityError(
                "Chave de slugOverrides deve ser código IBGE textual com sete dígitos: "
                f"{municipality_id!r}."
            )
        if municipality_id not in registry.ids:
            raise EducationMunicipalityRouteCompatibilityError(
                f"Override de slug educacional órfão: {municipality_id}."
            )
        slug = _validate_public_slug(raw_slug, municipality_id=municipality_id)
        canonical_slug = registry.get_by_id(municipality_id).slug
        if slug == canonical_slug:
            raise EducationMunicipalityRouteCompatibilityError(
                f"Override de slug educacional redundante para {municipality_id}: {slug!r}."
            )
        overrides[municipality_id] = slug

    resulting_slugs: dict[str, str] = {}
    for record in registry.ordered_records:
        slug = overrides.get(record.ibge_code, record.slug)
        normalized = slug.casefold()
        previous = resulting_slugs.get(normalized)
        if previous is not None:
            raise EducationMunicipalityRouteCompatibilityError(
                "Slugs públicos educacionais resultantes não são únicos: "
                f"{previous} e {record.ibge_code} usam {slug!r}."
            )
        resulting_slugs[normalized] = record.ibge_code

    return EducationMunicipalityRouteCompatibility(
        schema_version=EDUCATION_MUNICIPALITY_ROUTE_COMPATIBILITY_SCHEMA_VERSION,
        state_code=state_config.state_code,
        slug_overrides=MappingProxyType(overrides),
    )


def load_education_municipality_route_compatibility(
    state_config: StateConfig,
    registry: MunicipalityRegistry,
    *,
    compatibility_dir: Path = EDUCATION_MUNICIPALITY_ROUTE_COMPATIBILITY_DIR,
    compatibility_path: Path | None = None,
) -> EducationMunicipalityRouteCompatibility:
    path = Path(compatibility_path) if compatibility_path else (
        resolve_education_municipality_route_compatibility_path(
            state_config,
            compatibility_dir=compatibility_dir,
        )
    )
    if not path.is_file():
        raise FileNotFoundError(
            "Configuração de compatibilidade de rotas educacionais não encontrada para "
            f"{state_config.state_code}: {path}."
        )
    try:
        payload = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
        )
    except json.JSONDecodeError as exc:
        raise EducationMunicipalityRouteCompatibilityError(
            f"Configuração de rotas educacionais inválida em {path}: {exc}."
        ) from exc
    return _parse_compatibility(
        payload,
        state_config=state_config,
        registry=registry,
    )


def resolve_education_public_slug(
    record: MunicipalityRecord,
    compatibility: EducationMunicipalityRouteCompatibility,
) -> str:
    """Projeta somente a rota pública; a identidade permanece em ``ibge_code``."""
    return compatibility.slug_overrides.get(record.ibge_code, record.slug)


def _historical_education_publication_sort_key(record: MunicipalityRecord) -> tuple[str, str]:
    """Reproduz deterministicamente a ordem histórica do ``ORDER BY municipio``."""
    decomposed = unicodedata.normalize("NFKD", record.name.casefold())
    collation_key = "".join(
        character
        for character in decomposed
        if not unicodedata.combining(character) and character.isalnum()
    )
    return collation_key, record.ibge_code


def build_education_municipalities_index_payload(
    registry: MunicipalityRegistry,
    compatibility: EducationMunicipalityRouteCompatibility,
) -> dict[str, list[dict[str, str]]]:
    """Renderiza em memória o índice público histórico sem ler ``public/data``."""
    if registry.state_code != compatibility.state_code:
        raise EducationMunicipalityRouteCompatibilityError(
            "Registro municipal e compatibilidade de rotas pertencem a estados diferentes."
        )
    records = sorted(
        registry.ordered_records,
        key=_historical_education_publication_sort_key,
    )
    municipalities = [
        {
            "id_municipio": record.ibge_code,
            "municipio": record.name,
            "slug": resolve_education_public_slug(record, compatibility),
            "caminho": f"educacao/municipios/{record.ibge_code}.json",
        }
        for record in records
    ]
    public_slugs = [municipality["slug"].casefold() for municipality in municipalities]
    if len(set(public_slugs)) != len(public_slugs):
        raise EducationMunicipalityRouteCompatibilityError(
            "A projeção do índice educacional contém slugs públicos duplicados."
        )
    return {"municipios": municipalities}


def render_education_municipalities_index(
    registry: MunicipalityRegistry,
    compatibility: EducationMunicipalityRouteCompatibility,
) -> bytes:
    payload = build_education_municipalities_index_payload(registry, compatibility)
    return json.dumps(
        payload,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8")
