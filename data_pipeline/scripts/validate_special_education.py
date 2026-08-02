#!/usr/bin/env python3
"""Valida a fonte normalizada e o contrato special-education-v1."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd


DATA_PIPELINE_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = DATA_PIPELINE_DIR.parent
sys.path.insert(0, str(DATA_PIPELINE_DIR))

from src.data_loader import load_special_education_school_source_data  # noqa: E402
from src.education_municipality_routes import (  # noqa: E402
    EducationMunicipalityRouteCompatibilityError,
    load_education_municipality_route_compatibility,
    resolve_education_public_slug,
)
from src.municipality_registry import (  # noqa: E402
    MunicipalityRegistryError,
    load_municipality_registry,
)
from src.special_education_materialization import (  # noqa: E402
    ALL_FIELDS,
    RESOLVED_STATES,
    SCHEMA_VERSION,
    validate_contract,
    validate_source_municipality_universe,
)
from src.state_config import (  # noqa: E402
    DEFAULT_STATE_CODE,
    StateConfigError,
    load_state_config,
    normalize_state_code,
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
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
        route_compatibility = load_education_municipality_route_compatibility(
            state_config,
            registry,
        )
    except (
        FileNotFoundError,
        StateConfigError,
        MunicipalityRegistryError,
        EducationMunicipalityRouteCompatibilityError,
    ) as exc:
        print(f"Configuração estadual inválida: {exc}", file=sys.stderr)
        return 2

    errors: list[str] = []
    source = load_special_education_school_source_data(
        municipality_ids=registry.ids
    )
    if source.duplicated(["ano", "cod_escola"]).any():
        errors.append("fonte: chave ano x escola duplicada")
    try:
        validate_source_municipality_universe(source, registry.ids)
    except ValueError as exc:
        errors.append(f"fonte: {exc}")
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
    file_ids = {path.stem for path in files}
    if file_ids != registry.ids:
        errors.append(
            "contrato: conjunto municipal divergente; "
            f"ausentes={sorted(registry.ids - file_ids)[:5]}, "
            f"extras={sorted(file_ids - registry.ids)[:5]}"
        )
    manifest = json.loads((ROOT / "index.json").read_text(encoding="utf-8"))
    if manifest.get("schemaVersion") != SCHEMA_VERSION:
        errors.append("manifesto: schemaVersion inválido")
    if (
        manifest.get("municipalityCount") != registry.municipality_count
        or manifest.get("fileCount") != registry.municipality_count
    ):
        errors.append("manifesto: contagens inválidas")

    compared = 0
    for path in files:
        raw = path.read_bytes()
        contract = json.loads(raw)
        record = registry.records_by_id.get(path.stem)
        municipality = contract.get("municipality", {})
        if record is not None and municipality != {
            "code": record.ibge_code,
            "name": record.name,
            "slug": resolve_education_public_slug(record, route_compatibility),
        }:
            errors.append(f"{path.stem}: referência municipal pública divergente")
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
        "sourceMunicipalities": len(set(source["id_municipio"].dropna())),
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
