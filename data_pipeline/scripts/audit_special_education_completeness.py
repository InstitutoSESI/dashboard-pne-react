#!/usr/bin/env python3
"""Audita completude escolar por ano, município e variável temática."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd


DATA_PIPELINE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DATA_PIPELINE_DIR))

from src.data_loader import load_special_education_school_source_data  # noqa: E402


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
MUNICIPALITIES = {
    "4300034": "Aceguá",
    "4300406": "Alegrete",
    "4318705": "São Leopoldo",
}
FLAG_FIELDS = {"TP_AEE", "IN_SALA_ATENDIMENTO_ESPECIAL"}


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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    source = load_special_education_school_source_data()
    scopes = {
        "rio_grande_do_sul": source,
        **{
            code: source[source["id_municipio"].astype(str).eq(code)]
            for code in MUNICIPALITIES
        },
    }
    result = {
        "schemaVersion": 1,
        "municipalities": MUNICIPALITIES,
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
