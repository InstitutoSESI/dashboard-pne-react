"""Carregamento estrito da configuração estadual versionada."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
from typing import Any

from .config import STATE_CONFIG_DIR


STATE_CONFIG_SCHEMA_VERSION = "state-config-v1"
DEFAULT_STATE_CODE = "RS"
PIPELINE_STATE_ENV_VAR = "PNE_PIPELINE_STATE"
_STATE_CONFIG_FIELDS = frozenset(
    {
        "schemaVersion",
        "stateCode",
        "stateName",
        "stateNameForms",
        "municipalityIbgePrefix",
        "expectedMunicipalityCount",
        "locale",
    }
)
_STATE_NAME_FORM_FIELDS = frozenset({"nominative", "withDe", "withCom"})


class StateConfigError(ValueError):
    """Indica que uma configuração estadual não cumpre o contrato."""


@dataclass(frozen=True, slots=True)
class StateNameForms:
    nominative: str
    with_de: str
    with_com: str


@dataclass(frozen=True, slots=True)
class StateConfig:
    schema_version: str
    state_code: str
    state_name: str
    state_name_forms: StateNameForms
    municipality_ibge_prefix: str
    expected_municipality_count: int
    locale: str


def normalize_state_code(value: object) -> str:
    if not isinstance(value, str):
        raise StateConfigError("Código estadual deve ser texto com duas letras.")
    normalized = value.strip().upper()
    if not re.fullmatch(r"[A-Z]{2}", normalized):
        raise StateConfigError(
            f"Código estadual inválido {value!r}; informe exatamente duas letras."
        )
    return normalized


def resolve_state_config_path(
    state_code: object = DEFAULT_STATE_CODE,
    *,
    config_dir: Path = STATE_CONFIG_DIR,
) -> Path:
    normalized = normalize_state_code(state_code)
    return Path(config_dir) / f"{normalized.lower()}.json"


def _require_non_empty_string(payload: dict[str, Any], field: str) -> str:
    value = payload[field]
    if not isinstance(value, str) or not value.strip():
        raise StateConfigError(
            f"Configuração estadual inválida: {field!r} deve ser texto não vazio."
        )
    return value


def _parse_state_name_forms(payload: object) -> StateNameForms:
    if not isinstance(payload, dict):
        raise StateConfigError(
            "Configuração estadual inválida: 'stateNameForms' deve ser um objeto."
        )
    fields = set(payload)
    missing = sorted(_STATE_NAME_FORM_FIELDS - fields)
    unexpected = sorted(fields - _STATE_NAME_FORM_FIELDS)
    if missing:
        raise StateConfigError(
            "Configuração estadual inválida: campos obrigatórios ausentes em "
            "'stateNameForms': " + ", ".join(missing) + "."
        )
    if unexpected:
        raise StateConfigError(
            "Configuração estadual inválida: campos inesperados em "
            "'stateNameForms': " + ", ".join(unexpected) + "."
        )
    return StateNameForms(
        nominative=_require_non_empty_string(payload, "nominative"),
        with_de=_require_non_empty_string(payload, "withDe"),
        with_com=_require_non_empty_string(payload, "withCom"),
    )


def _parse_state_config(
    payload: object,
    *,
    requested_state_code: str,
) -> StateConfig:
    if not isinstance(payload, dict):
        raise StateConfigError(
            "Configuração estadual inválida: o documento deve ser um objeto JSON."
        )

    fields = set(payload)
    missing = sorted(_STATE_CONFIG_FIELDS - fields)
    unexpected = sorted(fields - _STATE_CONFIG_FIELDS)
    if missing:
        raise StateConfigError(
            "Configuração estadual inválida: campos obrigatórios ausentes: "
            + ", ".join(missing)
            + "."
        )
    if unexpected:
        raise StateConfigError(
            "Configuração estadual inválida: campos inesperados: "
            + ", ".join(unexpected)
            + "."
        )

    schema_version = _require_non_empty_string(payload, "schemaVersion")
    if schema_version != STATE_CONFIG_SCHEMA_VERSION:
        raise StateConfigError(
            "Configuração estadual inválida: schemaVersion desconhecido "
            f"{schema_version!r}."
        )

    state_code = _require_non_empty_string(payload, "stateCode")
    if not re.fullmatch(r"[A-Z]{2}", state_code):
        raise StateConfigError(
            "Configuração estadual inválida: 'stateCode' deve conter duas letras maiúsculas."
        )
    if state_code != requested_state_code:
        raise StateConfigError(
            "Configuração estadual inválida: stateCode "
            f"{state_code!r} diverge do estado solicitado {requested_state_code!r}."
        )

    state_name = _require_non_empty_string(payload, "stateName")
    state_name_forms = _parse_state_name_forms(payload["stateNameForms"])
    municipality_ibge_prefix = _require_non_empty_string(
        payload, "municipalityIbgePrefix"
    )
    if not re.fullmatch(r"\d{2}", municipality_ibge_prefix):
        raise StateConfigError(
            "Configuração estadual inválida: 'municipalityIbgePrefix' deve conter dois dígitos."
        )

    expected_count = payload["expectedMunicipalityCount"]
    if (
        isinstance(expected_count, bool)
        or not isinstance(expected_count, int)
        or expected_count <= 0
    ):
        raise StateConfigError(
            "Configuração estadual inválida: 'expectedMunicipalityCount' "
            "deve ser inteiro positivo."
        )

    locale = _require_non_empty_string(payload, "locale")
    return StateConfig(
        schema_version=schema_version,
        state_code=state_code,
        state_name=state_name,
        state_name_forms=state_name_forms,
        municipality_ibge_prefix=municipality_ibge_prefix,
        expected_municipality_count=expected_count,
        locale=locale,
    )


def load_state_config(
    state_code: object = DEFAULT_STATE_CODE,
    *,
    config_dir: Path = STATE_CONFIG_DIR,
) -> StateConfig:
    normalized = normalize_state_code(state_code)
    path = resolve_state_config_path(normalized, config_dir=config_dir)
    if not path.is_file():
        raise FileNotFoundError(
            f"Configuração estadual não encontrada para {normalized}: {path}."
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise StateConfigError(
            f"Configuração estadual inválida em {path}: JSON malformado: {exc}."
        ) from exc
    return _parse_state_config(payload, requested_state_code=normalized)


def resolve_pipeline_state_code(
    *,
    config_dir: Path = STATE_CONFIG_DIR,
) -> str:
    """Resolve a UF ativa do pipeline local a partir do ambiente.

    Lê a variável de ambiente ``PNE_PIPELINE_STATE``; quando ausente ou vazia,
    usa ``DEFAULT_STATE_CODE`` ("RS"). O valor é normalizado com
    ``normalize_state_code`` e validado contra a configuração estadual
    correspondente via ``load_state_config`` — uma UF sem configuração
    versionada nunca é aceita silenciosamente (fail-closed).

    Esta função é a costura de transição para a migração multi-UF do
    pipeline: hoje cada processo do pipeline geral roda para uma única UF,
    escolhida pelo ambiente. A Fase 3 vai substituir esta leitura de
    ambiente por um argumento de linha de comando explícito (`--state`) nos
    comandos do pipeline; até lá, `resolve_pipeline_state_code` concentra a
    resolução para que essa troca futura fique local a este módulo.
    """
    raw_value = os.environ.get(PIPELINE_STATE_ENV_VAR)
    state_code = raw_value if raw_value and raw_value.strip() else DEFAULT_STATE_CODE
    normalized = normalize_state_code(state_code)
    load_state_config(normalized, config_dir=config_dir)
    return normalized
