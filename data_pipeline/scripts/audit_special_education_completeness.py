#!/usr/bin/env python3
"""Audita completude escolar por ano, município e variável temática."""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

import pandas as pd


DATA_PIPELINE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DATA_PIPELINE_DIR))

from src.data_loader import load_special_education_school_source_data  # noqa: E402
from src.municipality_registry import (  # noqa: E402
    MunicipalityRegistryError,
    load_municipality_registry,
)
from src.state_config import (  # noqa: E402
    DEFAULT_STATE_CODE,
    StateConfigError,
    load_state_config,
    normalize_state_code,
)
from src.state_qa_samples import (  # noqa: E402
    StateQaSampleError,
    resolve_qa_sample_ids,
)


FIELDS = (
    "QT_MAT_ESP",
    "QT_MAT_ESP_CC",
    "QT_MAT_ESP_CE",
    "QT_TUR_ESP",
    "QT_TUR_ESP_CC",
    "QT_TUR_ESP_CE",
    "QT_DOC_ESP",
    "QT_DOC_ESP_CC",
    "QT_DOC_ESP_CE",
    "TP_AEE",
    "IN_SALA_ATENDIMENTO_ESPECIAL",
    "QT_MAT_BAS_LIBRAS",
    "QT_TUR_BAS_LIBRAS",
    "QT_DOC_BAS_LIBRAS",
)
FLAG_FIELDS = {"TP_AEE", "IN_SALA_ATENDIMENTO_ESPECIAL"}


def _state_scope_key(state_config) -> str:
    """Escopo estadual nomeado pela configuração ativa, nunca por constante RS."""
    decomposed = unicodedata.normalize("NFKD", state_config.state_name)
    ascii_name = "".join(
        character for character in decomposed if not unicodedata.combining(character)
    )
    return re.sub(r"[^a-z0-9]+", "_", ascii_name.casefold()).strip("_")


def _flag(frame: pd.DataFrame, prefix: str, field: str) -> pd.Series:
    column = f"{prefix}_{field.lower()}"
    if column not in frame:
        return pd.Series(False, index=frame.index)
    return frame[column].fillna(False).astype(bool)


def profile(frame: pd.DataFrame, field: str) -> dict:
    availability_column = f"disponivel_{field.lower()}"
    available = (
        field in frame
        and availability_column in frame
        and bool(frame[availability_column].fillna(False).astype(bool).any())
    )
    if not available:
        return {
            "available": False,
            "activeSchools": int(len(frame)),
            "linesFound": int(len(frame)),
        }
    values = pd.to_numeric(frame[field], errors="coerce")
    structural = _flag(frame, "vazio_estrutural", field)
    extremes = _flag(frame, "valor_extremo", field)
    eligible = (
        pd.to_numeric(frame["QT_MAT_ESP"], errors="coerce").fillna(0).gt(0)
        if field in FLAG_FIELDS
        else pd.Series(True, index=frame.index)
    )
    missing = eligible & values.isna() & ~structural
    observed = eligible & ~missing & ~extremes
    return {
        "available": True,
        "activeSchools": int(len(frame)),
        "linesFound": int(len(frame)),
        "positiveValues": int(values.gt(0).sum()),
        "explicitZeros": int((values.eq(0) & ~structural).sum()),
        "structuralEmptyNormalizedToZero": int(structural.sum()),
        "nullValues": int(values.isna().sum()),
        "extremeValues": int(extremes.sum()),
        "observedSum": float(values[~extremes].sum()),
        "eligibleSchools": int(eligible.sum()),
        "observedSchools": int(observed.sum()),
        "missingSchools": int((missing | (eligible & extremes)).sum()),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--state",
        default=DEFAULT_STATE_CODE,
        help=f"Código estadual configurado (padrão: {DEFAULT_STATE_CODE}).",
    )
    args = parser.parse_args(argv)

    try:
        state_code = normalize_state_code(args.state)
        state_config = load_state_config(state_code)
        registry = load_municipality_registry(state_config)
        sample_municipality_ids = resolve_qa_sample_ids(state_config, registry)
    except (
        FileNotFoundError,
        StateConfigError,
        MunicipalityRegistryError,
        StateQaSampleError,
    ) as exc:
        print(f"Configuração estadual inválida: {exc}", file=sys.stderr)
        return 2

    source = load_special_education_school_source_data(
        municipality_ids=registry.ids
    )
    municipalities = {
        code: registry.get_by_id(code).name for code in sample_municipality_ids
    }
    scopes = {
        _state_scope_key(state_config): source,
        **{
            code: source[source["id_municipio"].eq(code)]
            for code in municipalities
        },
    }
    result = {
        "schemaVersion": 1,
        "municipalities": municipalities,
        "profiles": {
            scope: {
                str(year): {
                    field: profile(frame[frame["ano"].eq(year)], field)
                    for field in FIELDS
                }
                for year in range(2014, 2026)
            }
            for scope, frame in scopes.items()
        },
    }
    serialized = json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf-8")
    else:
        print(serialized, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
