#!/usr/bin/env python3
"""Valida a fonte normalizada e o contrato special-education-v1."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd


DATA_PIPELINE_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = DATA_PIPELINE_DIR.parent
sys.path.insert(0, str(DATA_PIPELINE_DIR))

from src.data_loader import load_special_education_school_source_data  # noqa: E402
from src.special_education_materialization import (  # noqa: E402
    ALL_FIELDS,
    RESOLVED_STATES,
    SCHEMA_VERSION,
    validate_contract,
)


ROOT = REPO_ROOT / "public" / "data" / "educacao" / "educacao-especial"
OVERVIEW = REPO_ROOT / "public" / "data" / "educacao" / "visao-geral-municipal"
ALLOWED_STATES = {
    "observed",
    "derived_zero",
    "partial",
    "unavailable",
    "not_applicable",
}


def walk_points(value: Any, path: str = ""):
    if isinstance(value, dict):
        if {"value", "state", "sourceId"} <= value.keys():
            yield path, value
        for key, child in value.items():
            yield from walk_points(child, f"{path}/{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from walk_points(child, f"{path}/{index}")


def resolved_value(point: dict) -> int | float | None:
    return point["value"] if point["state"] in RESOLVED_STATES else None


def reconcile_cut(yearly: dict, path: tuple[str, ...], errors: list[str]) -> None:
    def point(cut: str) -> dict:
        value: Any = yearly["cuts"][cut]
        for key in path:
            value = value[key]
        return value

    total = resolved_value(point("total"))
    networks = [resolved_value(point(cut)) for cut in ("federal", "estadual", "municipal", "privada")]
    locations = [resolved_value(point(cut)) for cut in ("urbana", "rural")]
    public = resolved_value(point("publica"))
    if total is not None and all(value is not None for value in networks):
        if sum(networks) != total:
            errors.append(f"{yearly['year']}/{'/'.join(path)}: redes não reconciliam")
        if public is not None and sum(networks[:3]) != public:
            errors.append(f"{yearly['year']}/{'/'.join(path)}: pública não reconcilia")
    if total is not None and all(value is not None for value in locations):
        if sum(locations) != total:
            errors.append(f"{yearly['year']}/{'/'.join(path)}: localizações não reconciliam")


def main() -> int:
    errors: list[str] = []
    source = load_special_education_school_source_data()
    if source.duplicated(["ano", "cod_escola"]).any():
        errors.append("fonte: chave ano x escola duplicada")
    if source["id_municipio"].astype(str).nunique() != 497:
        errors.append("fonte: universo municipal diferente de 497")
    coverage = source.groupby("ano")["id_municipio"].nunique()
    if any(coverage.get(year, 0) != 497 for year in range(2014, 2026)):
        errors.append("fonte: ano sem cobertura dos 497 municípios")
    numeric = source[[field for field in ALL_FIELDS if field in source]].apply(
        pd.to_numeric, errors="coerce"
    )
    if (numeric.apply(lambda column: column.dropna().lt(0).any())).any():
        errors.append("fonte: valor negativo")
    observed = source[
        source[["QT_MAT_ESP", "QT_MAT_ESP_CC", "QT_MAT_ESP_CE"]]
        .notna()
        .all(axis=1)
    ]
    if (
        (observed["QT_MAT_ESP_CC"] > observed["QT_MAT_ESP"]).any()
        or (observed["QT_MAT_ESP_CE"] > observed["QT_MAT_ESP"]).any()
        or (
            observed["QT_MAT_ESP_CC"] + observed["QT_MAT_ESP_CE"]
            != observed["QT_MAT_ESP"]
        ).any()
    ):
        errors.append("fonte: matrículas comuns/exclusivas não reconciliam")

    files = sorted((ROOT / "municipios").glob("*.json"))
    if len(files) != 497:
        errors.append(f"contrato: {len(files)} arquivos municipais")
    manifest = json.loads((ROOT / "index.json").read_text(encoding="utf-8"))
    if manifest.get("schemaVersion") != SCHEMA_VERSION:
        errors.append("manifesto: schemaVersion inválido")
    if manifest.get("municipalityCount") != 497 or manifest.get("fileCount") != 497:
        errors.append("manifesto: contagens inválidas")

    compared = 0
    for path in files:
        raw = path.read_bytes()
        contract = json.loads(raw)
        errors.extend(f"{path.stem}: {error}" for error in validate_contract(contract))
        for point_path, point in walk_points(contract):
            if point["state"] not in ALLOWED_STATES:
                errors.append(f"{path.stem}{point_path}: estado inválido")
            if point["value"] is not None and (
                not isinstance(point["value"], (int, float))
                or not (-float("inf") < float(point["value"]) < float("inf"))
            ):
                errors.append(f"{path.stem}{point_path}: valor não finito")
            if point["value"] is not None and point["value"] < 0:
                errors.append(f"{path.stem}{point_path}: valor negativo")
            if any(point.get(key) == 88888 for key in ("value", "numerator", "denominator")):
                errors.append(f"{path.stem}{point_path}: sentinela extrema publicada")

        for yearly in contract["years"]:
            for metric in (
                "enrollments",
                "commonClassEnrollments",
                "exclusiveClassEnrollments",
                "classes",
                "commonClassClasses",
                "exclusiveClassClasses",
                "teacherAssignments",
                "commonClassTeacherAssignments",
                "exclusiveClassTeacherAssignments",
                "schools",
            ):
                reconcile_cut(yearly, ("specialEducation", metric), errors)
            bilingual = yearly["cuts"]["total"]["bilingualDeafEducation"]
            if yearly["year"] < 2025:
                for metric in ("enrollments", "classes", "teacherAssignments", "schools"):
                    if bilingual[metric]["state"] != "unavailable":
                        errors.append(
                            f"{path.stem}/{yearly['year']}/{metric}: "
                            "ano bilíngue preenchido artificialmente"
                        )

        overview_path = OVERVIEW / path.name
        if overview_path.exists():
            overview = json.loads(overview_path.read_text(encoding="utf-8"))
            old_value = overview["specialEducation"]["total"]["value"]
            new_year = next(item for item in contract["years"] if item["year"] == 2025)
            new_value = new_year["cuts"]["total"]["specialEducation"]["enrollments"]["value"]
            compared += 1
            if old_value != new_value:
                errors.append(f"{path.stem}: divergência com Visão Geral 2025")

    result = {
        "schemaVersion": SCHEMA_VERSION,
        "valid": not errors,
        "sourceRows": len(source),
        "sourceMunicipalities": int(source["id_municipio"].nunique()),
        "municipalityFiles": len(files),
        "overviewCompared": compared,
        "errorCount": len(errors),
        "errors": errors[:100],
        "manifestContentHash": manifest.get("contentHash"),
    }
    print(json.dumps(result, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
