"""Registro municipal canônico e projeções públicas derivadas."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass, field
import json
from pathlib import Path
import re
from types import MappingProxyType
import unicodedata
from typing import Any

from .config import MUNICIPALITY_REGISTRY_DIR
from .state_config import StateConfig


MUNICIPALITY_REGISTRY_SCHEMA_VERSION = "municipality-registry-v1"
_REGISTRY_FIELDS = frozenset(
    {"schemaVersion", "stateCode", "municipalityCount", "municipalities"}
)
_RECORD_FIELDS = frozenset({"ibgeCode", "name", "slug"})


class MunicipalityRegistryError(ValueError):
    """Indica que o registro municipal não cumpre o contrato."""


@dataclass(frozen=True, slots=True)
class MunicipalityRecord:
    ibge_code: str
    name: str
    slug: str


@dataclass(frozen=True, slots=True)
class MunicipalityRegistry:
    schema_version: str
    state_code: str
    municipality_count: int
    ordered_records: tuple[MunicipalityRecord, ...]
    records_by_id: Mapping[str, MunicipalityRecord]
    ids: frozenset[str]
    names_by_id: Mapping[str, str]
    ids_by_normalized_name: Mapping[str, tuple[str, ...]]
    _ids_by_exact_name: Mapping[str, tuple[str, ...]] = field(repr=False)

    def get_by_id(self, municipality_id: str) -> MunicipalityRecord:
        try:
            return self.records_by_id[municipality_id]
        except KeyError as exc:
            raise KeyError(
                f"Código IBGE municipal ausente no registro de {self.state_code}: "
                f"{municipality_id}."
            ) from exc

    def resolve_unique_name(self, name: object) -> MunicipalityRecord:
        if not isinstance(name, str) or not name.strip():
            raise MunicipalityRegistryError(
                "Nome municipal deve ser texto não vazio para resolução."
            )

        exact_ids = self._ids_by_exact_name.get(name, ())
        if len(exact_ids) == 1:
            return self.records_by_id[exact_ids[0]]
        if len(exact_ids) > 1:
            raise MunicipalityRegistryError(
                f"Nome municipal ambíguo no registro de {self.state_code}: {name!r}."
            )

        normalized = normalize_municipality_name(name)
        normalized_ids = self.ids_by_normalized_name.get(normalized, ())
        if len(normalized_ids) == 1:
            return self.records_by_id[normalized_ids[0]]
        if len(normalized_ids) > 1:
            raise MunicipalityRegistryError(
                f"Nome municipal ambíguo no registro de {self.state_code}: {name!r}."
            )
        raise MunicipalityRegistryError(
            f"Nome municipal ausente no registro de {self.state_code}: {name!r}."
        )

    def build_public_index_payload(self, *, generated_at: str) -> dict[str, Any]:
        if not isinstance(generated_at, str) or not generated_at.strip():
            raise MunicipalityRegistryError(
                "generated_at deve ser informado explicitamente como texto não vazio."
            )
        return {
            "generated_at": generated_at,
            "total_municipios": self.municipality_count,
            "municipios": [
                {
                    "nome": record.name,
                    "id_municipio": record.ibge_code,
                    "slug": record.slug,
                    "path": f"/data/municipios/{record.ibge_code}/index.json",
                }
                for record in self.ordered_records
            ],
        }


def normalize_municipality_name(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return " ".join(
        "".join(char if char.isalnum() else " " for char in text.casefold()).split()
    )


def resolve_municipality_registry_path(
    state_config: StateConfig,
    *,
    registry_dir: Path = MUNICIPALITY_REGISTRY_DIR,
) -> Path:
    return Path(registry_dir) / f"{state_config.state_code.lower()}.json"


def _validate_fields(
    payload: Mapping[str, Any],
    expected: frozenset[str],
    *,
    label: str,
) -> None:
    fields = set(payload)
    missing = sorted(expected - fields)
    unexpected = sorted(fields - expected)
    if missing:
        raise MunicipalityRegistryError(
            f"{label}: campos obrigatórios ausentes: {', '.join(missing)}."
        )
    if unexpected:
        raise MunicipalityRegistryError(
            f"{label}: campos inesperados: {', '.join(unexpected)}."
        )


def _parse_registry(
    payload: object,
    *,
    state_config: StateConfig,
) -> MunicipalityRegistry:
    if not isinstance(payload, dict):
        raise MunicipalityRegistryError(
            "Registro municipal inválido: o documento deve ser um objeto JSON."
        )
    _validate_fields(payload, _REGISTRY_FIELDS, label="Registro municipal inválido")

    if payload["schemaVersion"] != MUNICIPALITY_REGISTRY_SCHEMA_VERSION:
        raise MunicipalityRegistryError(
            "Registro municipal inválido: schemaVersion deve ser "
            f"{MUNICIPALITY_REGISTRY_SCHEMA_VERSION!r}."
        )
    if payload["stateCode"] != state_config.state_code:
        raise MunicipalityRegistryError(
            "Registro municipal inválido: stateCode "
            f"{payload['stateCode']!r} diverge de {state_config.state_code!r}."
        )

    declared_count = payload["municipalityCount"]
    if (
        isinstance(declared_count, bool)
        or not isinstance(declared_count, int)
        or declared_count <= 0
    ):
        raise MunicipalityRegistryError(
            "Registro municipal inválido: municipalityCount deve ser inteiro positivo."
        )
    entries = payload["municipalities"]
    if not isinstance(entries, list):
        raise MunicipalityRegistryError(
            "Registro municipal inválido: municipalities deve ser uma lista."
        )
    if declared_count != len(entries):
        raise MunicipalityRegistryError(
            "Registro municipal inválido: municipalityCount declara "
            f"{declared_count}, mas há {len(entries)} entradas."
        )
    if declared_count != state_config.expected_municipality_count:
        raise MunicipalityRegistryError(
            "Registro municipal inválido: municipalityCount declara "
            f"{declared_count}, esperado {state_config.expected_municipality_count} "
            f"para {state_config.state_code}."
        )

    records: list[MunicipalityRecord] = []
    seen_ids: set[str] = set()
    seen_slugs: set[str] = set()
    normalized_names: defaultdict[str, list[str]] = defaultdict(list)
    exact_names: defaultdict[str, list[str]] = defaultdict(list)
    for index, entry in enumerate(entries, start=1):
        label = f"Município na posição {index}"
        if not isinstance(entry, dict):
            raise MunicipalityRegistryError(f"{label}: entrada deve ser um objeto.")
        _validate_fields(entry, _RECORD_FIELDS, label=label)

        municipality_id = entry["ibgeCode"]
        if not isinstance(municipality_id, str) or not re.fullmatch(
            r"\d{7}", municipality_id
        ):
            raise MunicipalityRegistryError(
                f"{label}: ibgeCode deve ser texto com exatamente sete dígitos."
            )
        if not municipality_id.startswith(state_config.municipality_ibge_prefix):
            raise MunicipalityRegistryError(
                f"{label}: ibgeCode {municipality_id} não possui o prefixo "
                f"{state_config.municipality_ibge_prefix} de {state_config.state_code}."
            )
        if municipality_id in seen_ids:
            raise MunicipalityRegistryError(
                f"{label}: ibgeCode duplicado {municipality_id}."
            )

        name = entry["name"]
        if not isinstance(name, str) or not name.strip():
            raise MunicipalityRegistryError(f"{label}: name deve ser texto não vazio.")
        slug = entry["slug"]
        if not isinstance(slug, str) or not slug.strip():
            raise MunicipalityRegistryError(f"{label}: slug deve ser texto não vazio.")
        normalized_slug = slug.casefold()
        if normalized_slug in seen_slugs:
            raise MunicipalityRegistryError(f"{label}: slug duplicado {slug!r}.")

        record = MunicipalityRecord(
            ibge_code=municipality_id,
            name=name,
            slug=slug,
        )
        records.append(record)
        seen_ids.add(municipality_id)
        seen_slugs.add(normalized_slug)
        normalized_names[normalize_municipality_name(name)].append(municipality_id)
        exact_names[name].append(municipality_id)

    ordered_records = tuple(records)
    records_by_id = {record.ibge_code: record for record in ordered_records}
    return MunicipalityRegistry(
        schema_version=MUNICIPALITY_REGISTRY_SCHEMA_VERSION,
        state_code=state_config.state_code,
        municipality_count=declared_count,
        ordered_records=ordered_records,
        records_by_id=MappingProxyType(records_by_id),
        ids=frozenset(records_by_id),
        names_by_id=MappingProxyType(
            {record.ibge_code: record.name for record in ordered_records}
        ),
        ids_by_normalized_name=MappingProxyType(
            {key: tuple(value) for key, value in normalized_names.items()}
        ),
        _ids_by_exact_name=MappingProxyType(
            {key: tuple(value) for key, value in exact_names.items()}
        ),
    )


def load_municipality_registry(
    state_config: StateConfig,
    *,
    registry_dir: Path = MUNICIPALITY_REGISTRY_DIR,
    registry_path: Path | None = None,
) -> MunicipalityRegistry:
    path = registry_path or resolve_municipality_registry_path(
        state_config, registry_dir=registry_dir
    )
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(
            f"Registro municipal não encontrado para {state_config.state_code}: {path}."
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise MunicipalityRegistryError(
            f"Registro municipal inválido em {path}: JSON malformado: {exc}."
        ) from exc
    return _parse_registry(payload, state_config=state_config)
