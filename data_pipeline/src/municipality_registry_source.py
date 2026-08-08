"""Normalização fail-closed de fontes oficiais para cadastros municipais candidatos."""

from __future__ import annotations

from collections.abc import Mapping
import json
import re
import unicodedata
from typing import Any

from .state_config import StateConfig


MUNICIPALITY_REGISTRY_CANDIDATE_ALGORITHM = "municipality-registry-candidate-v1"
_IBGE_CODE_PATTERN = re.compile(r"[0-9]{7}")
_NON_SLUG_CHARACTERS = re.compile(r"[^a-z0-9]+")


class MunicipalityRegistrySourceError(ValueError):
    """Indica que a fonte oficial não pode produzir um cadastro confiável."""


def load_source_json_with_textual_numbers(raw_bytes: bytes) -> object:
    """Lê JSON preservando todo token numérico como texto desde o parser."""

    if not isinstance(raw_bytes, bytes):
        raise MunicipalityRegistrySourceError("O snapshot da fonte deve ser bytes.")
    try:
        source_text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise MunicipalityRegistrySourceError(
            "O snapshot da fonte não é UTF-8 válido."
        ) from exc
    try:
        return json.loads(source_text, parse_int=str, parse_float=str)
    except json.JSONDecodeError as exc:
        raise MunicipalityRegistrySourceError(
            f"O snapshot da fonte não é JSON válido: {exc}."
        ) from exc


def slugify_municipality_name(name: str) -> str:
    """Produz o slug candidato sem atribuir ao slug função de identidade."""

    decomposed = unicodedata.normalize("NFKD", name)
    without_marks = "".join(
        character
        for character in decomposed
        if not unicodedata.combining(character)
    )
    return _NON_SLUG_CHARACTERS.sub("-", without_marks.casefold()).strip("-")


def _require_mapping(value: object, *, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise MunicipalityRegistrySourceError(f"{label} deve ser um objeto.")
    return value


def _nested_mapping(
    entry: Mapping[str, Any],
    fields: tuple[str, ...],
    *,
    label: str,
) -> Mapping[str, Any]:
    current: Mapping[str, Any] = entry
    for field in fields:
        current = _require_mapping(
            current.get(field),
            label=f"{label}.{field}",
        )
    return current


def _validate_source_state(
    entry: Mapping[str, Any],
    *,
    state_config: StateConfig,
    label: str,
) -> None:
    state_objects = (
        _nested_mapping(
            entry,
            ("microrregiao", "mesorregiao", "UF"),
            label=label,
        ),
        _nested_mapping(
            entry,
            ("regiao-imediata", "regiao-intermediaria", "UF"),
            label=label,
        ),
    )
    expected = {
        "id": state_config.municipality_ibge_prefix,
        "sigla": state_config.state_code,
        "nome": state_config.state_name,
    }
    for state_object in state_objects:
        observed = {field: state_object.get(field) for field in expected}
        if observed != expected:
            raise MunicipalityRegistrySourceError(
                f"{label}: hierarquia estadual divergente; "
                f"esperado {expected!r}, observado {observed!r}."
            )


def build_municipality_registry_candidate(
    source_payload: object,
    *,
    state_config: StateConfig,
) -> dict[str, Any]:
    """Materializa um `municipality-registry-v1` candidato a partir do IBGE."""

    if not isinstance(source_payload, list):
        raise MunicipalityRegistrySourceError(
            "A resposta de municípios do IBGE deve ser uma lista."
        )
    if len(source_payload) != state_config.expected_municipality_count:
        raise MunicipalityRegistrySourceError(
            "Cobertura municipal divergente: "
            f"esperados {state_config.expected_municipality_count}, "
            f"observados {len(source_payload)}."
        )

    municipalities: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    seen_names: set[str] = set()
    seen_slugs: set[str] = set()
    for index, raw_entry in enumerate(source_payload, start=1):
        label = f"Município da fonte na posição {index}"
        entry = _require_mapping(raw_entry, label=label)
        municipality_id = entry.get("id")
        name = entry.get("nome")
        if not isinstance(municipality_id, str) or not _IBGE_CODE_PATTERN.fullmatch(
            municipality_id
        ):
            raise MunicipalityRegistrySourceError(
                f"{label}: id deve chegar do parser como texto com sete dígitos."
            )
        if not municipality_id.startswith(state_config.municipality_ibge_prefix):
            raise MunicipalityRegistrySourceError(
                f"{label}: código {municipality_id} não possui o prefixo "
                f"{state_config.municipality_ibge_prefix}."
            )
        if not isinstance(name, str) or not name.strip():
            raise MunicipalityRegistrySourceError(
                f"{label}: nome deve ser texto não vazio."
            )
        _validate_source_state(entry, state_config=state_config, label=label)

        slug = slugify_municipality_name(name)
        if not slug:
            raise MunicipalityRegistrySourceError(
                f"{label}: nome {name!r} não produz slug válido."
            )
        normalized_slug = slug.casefold()
        if municipality_id in seen_ids:
            raise MunicipalityRegistrySourceError(
                f"{label}: código IBGE duplicado {municipality_id}."
            )
        if name in seen_names:
            raise MunicipalityRegistrySourceError(
                f"{label}: nome municipal duplicado {name!r}."
            )
        if normalized_slug in seen_slugs:
            raise MunicipalityRegistrySourceError(
                f"{label}: slug candidato duplicado {slug!r}."
            )

        seen_ids.add(municipality_id)
        seen_names.add(name)
        seen_slugs.add(normalized_slug)
        municipalities.append(
            {"ibgeCode": municipality_id, "name": name, "slug": slug}
        )

    return {
        "schemaVersion": "municipality-registry-v1",
        "stateCode": state_config.state_code,
        "municipalityCount": len(municipalities),
        "municipalities": municipalities,
    }
