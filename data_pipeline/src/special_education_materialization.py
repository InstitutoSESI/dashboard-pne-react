"""Contrato municipal de Educação Especial e Educação Bilíngue de Surdos."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import shutil
import tempfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any, Callable

import pandas as pd


SCHEMA_VERSION = "special-education-v1"
SOURCE_ID = "inep_censo_escolar_school_microdata"
YEARS = tuple(range(2014, 2026))
CUTS = ("total", "publica", "municipal", "estadual", "federal", "privada", "urbana", "rural")
RESOLVED_STATES = {"observed", "derived_zero"}

SPECIAL_SUM_FIELDS = {
    "enrollments": "QT_MAT_ESP",
    "commonClassEnrollments": "QT_MAT_ESP_CC",
    "exclusiveClassEnrollments": "QT_MAT_ESP_CE",
    "classes": "QT_TUR_ESP",
    "commonClassClasses": "QT_TUR_ESP_CC",
    "exclusiveClassClasses": "QT_TUR_ESP_CE",
    "teacherAssignments": "QT_DOC_ESP",
    "commonClassTeacherAssignments": "QT_DOC_ESP_CC",
    "exclusiveClassTeacherAssignments": "QT_DOC_ESP_CE",
}
SPECIAL_STAGE_FIELDS = {
    "earlyChildhood": "QT_MAT_ESP_INF",
    "creche": "QT_MAT_ESP_INF_CRE",
    "preSchool": "QT_MAT_ESP_INF_PRE",
    "elementary": "QT_MAT_ESP_FUND",
    "initialYears": "QT_MAT_ESP_FUND_AI",
    "finalYears": "QT_MAT_ESP_FUND_AF",
    "highSchool": "QT_MAT_ESP_MED",
    "professional": "QT_MAT_ESP_PROF",
    "youthAndAdult": "QT_MAT_ESP_EJA",
}
BILINGUAL_SUM_FIELDS = {
    "enrollments": "QT_MAT_BAS_LIBRAS",
    "classes": "QT_TUR_BAS_LIBRAS",
    "teacherAssignments": "QT_DOC_BAS_LIBRAS",
    "interpreterAssignments": "QT_PROF_TRAD_LIBRAS",
    "guideInterpreterAssignments": "QT_DOC_BAS_GUIA_INTERPRETE",
    "librasCurriculumClasses": "QT_TUR_BAS_DISC_LIBRAS",
    "librasCurriculumTeacherAssignments": "QT_DOC_BAS_DISC_LIBRAS",
    "bilingualSpecializationTeacherAssignments": "QT_DOC_BAS_ESPEC_BIL_SURDOS",
    "managementSpecializationTeacherAssignments": "QT_DOC_BAS_ESPEC_GESTAO",
}
ALL_FIELDS = tuple(
    dict.fromkeys(
        [
            *SPECIAL_SUM_FIELDS.values(),
            *SPECIAL_STAGE_FIELDS.values(),
            "QT_DOC_BAS",
            "QT_MAT_ESP_INT",
            "QT_TUR_ESP_INT",
            "TP_AEE",
            "IN_SALA_ATENDIMENTO_ESPECIAL",
            *BILINGUAL_SUM_FIELDS.values(),
            "IN_MATERIAL_PED_BIL_SURDOS",
        ]
    )
)
def _point(
    value: int | float | None,
    state: str,
    *,
    reason: str | None = None,
    numerator: int | float | None = None,
    denominator: int | float | None = None,
    observed_schools: int | None = None,
    missing_schools: int | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {"value": value, "state": state, "sourceId": SOURCE_ID}
    if reason:
        result["reason"] = reason
    if numerator is not None:
        result["numerator"] = numerator
    if denominator is not None:
        result["denominator"] = denominator
    if observed_schools is not None:
        result["observedSchools"] = observed_schools
    if missing_schools is not None:
        result["missingSchools"] = missing_schools
    return result


def _available(frame: pd.DataFrame, field: str) -> bool:
    available_fields = frame.attrs.get("available_fields")
    if available_fields is not None:
        return field in available_fields
    column = f"disponivel_{field.lower()}"
    return column in frame and bool(frame[column].fillna(False).astype(bool).any())


def _extreme(frame: pd.DataFrame, field: str) -> pd.Series:
    column = f"valor_extremo_{field.lower()}"
    if column not in frame:
        return pd.Series(False, index=frame.index)
    return frame[column].fillna(False).astype(bool)


def _structural_empty(frame: pd.DataFrame, field: str) -> pd.Series:
    column = f"vazio_estrutural_{field.lower()}"
    if column not in frame:
        return pd.Series(False, index=frame.index)
    return frame[column].fillna(False).astype(bool)


def _sum(frame: pd.DataFrame, field: str, year_frame: pd.DataFrame) -> dict[str, Any]:
    if not _available(year_frame, field):
        return _point(None, "unavailable", reason="source_column_absent")
    if frame.empty:
        return _point(
            0,
            "derived_zero",
            reason="complete_cut_has_no_school",
            observed_schools=0,
            missing_schools=0,
        )
    values = pd.to_numeric(frame[field], errors="coerce")
    extremes = _extreme(frame, field)
    structural_empty = _structural_empty(frame, field)
    values = values.mask(structural_empty & values.isna(), 0)
    valid = values[~extremes & values.notna()]
    value = valid.sum()
    numeric: int | float = int(value) if float(value).is_integer() else float(value)
    missing = ~extremes & values.isna()
    observed_schools = int((~extremes & values.notna()).sum())
    missing_schools = int((extremes | missing).sum())
    if extremes.any():
        return _point(
            numeric or None,
            "partial",
            reason="non_publishable_extreme_value",
            observed_schools=observed_schools,
            missing_schools=missing_schools,
        )
    if missing.any():
        return _point(
            numeric or None,
            "partial",
            reason="incomplete_school_aggregation",
            observed_schools=observed_schools,
            missing_schools=missing_schools,
        )
    return _point(
        numeric,
        "observed",
        observed_schools=observed_schools,
        missing_schools=0,
    )


def _count(
    frame: pd.DataFrame,
    fields: tuple[str, ...],
    year_frame: pd.DataFrame,
    predicate: Callable[[pd.DataFrame], pd.Series],
    *,
    missing_is_non_match: bool = False,
) -> dict[str, Any]:
    if not all(_available(year_frame, field) for field in fields):
        return _point(None, "unavailable", reason="source_column_absent")
    if frame.empty:
        return _point(
            0,
            "derived_zero",
            reason="complete_cut_has_no_school",
            observed_schools=0,
            missing_schools=0,
        )
    if any(_extreme(frame, field).any() for field in fields):
        missing_schools = int(
            pd.concat([_extreme(frame, field) for field in fields], axis=1)
            .any(axis=1)
            .sum()
        )
        return _point(
            None,
            "partial",
            reason="non_publishable_extreme_value",
            observed_schools=len(frame) - missing_schools,
            missing_schools=missing_schools,
        )
    normalized = frame.copy()
    for field in fields:
        structural_empty = _structural_empty(normalized, field)
        normalized.loc[structural_empty & normalized[field].isna(), field] = 0
    missing = normalized[list(fields)].isna().any(axis=1)
    observed_schools = int((~missing).sum())
    missing_schools = int(missing.sum())
    if missing.any() and not missing_is_non_match:
        matches = normalized.loc[~missing]
        value = int(matches.loc[predicate(matches), "cod_escola"].nunique())
        return _point(
            value or None,
            "partial",
            reason="incomplete_school_aggregation",
            observed_schools=observed_schools,
            missing_schools=missing_schools,
        )
    return _point(
        int(normalized.loc[predicate(normalized), "cod_escola"].nunique()),
        "observed",
        observed_schools=len(normalized) if missing_is_non_match else observed_schools,
        missing_schools=0 if missing_is_non_match else missing_schools,
    )


def _percentage(numerator: dict[str, Any], denominator: dict[str, Any]) -> dict[str, Any]:
    if numerator["state"] not in RESOLVED_STATES or denominator["state"] not in RESOLVED_STATES:
        state = "partial" if "partial" in {numerator["state"], denominator["state"]} else "unavailable"
        return _point(None, state, reason="unresolved_component")
    if denominator["value"] == 0:
        return _point(
            None,
            "not_applicable",
            reason="zero_denominator",
            numerator=numerator["value"],
            denominator=0,
        )
    return _point(
        100 * numerator["value"] / denominator["value"],
        "observed",
        numerator=numerator["value"],
        denominator=denominator["value"],
    )


def _cut(frame: pd.DataFrame, cut: str) -> pd.DataFrame:
    if cut == "total":
        return frame
    if cut == "publica":
        return frame[frame["rede_publica"].fillna(False).astype(bool)]
    if cut in {"municipal", "estadual", "federal", "privada"}:
        return frame[frame["dependencia"] == cut]
    return frame[frame["localizacao"] == cut]


def _special(frame: pd.DataFrame, year_frame: pd.DataFrame) -> dict[str, Any]:
    result = {name: _sum(frame, field, year_frame) for name, field in SPECIAL_SUM_FIELDS.items()}
    result["schools"] = _count(
        frame,
        ("QT_MAT_ESP",),
        year_frame,
        lambda rows: pd.to_numeric(rows["QT_MAT_ESP"], errors="coerce") > 0,
    )
    eligible = frame[pd.to_numeric(frame.get("QT_MAT_ESP"), errors="coerce").fillna(0) > 0]
    result["teacherAssignmentsInSchools"] = _sum(eligible, "QT_DOC_BAS", year_frame)
    result["stages"] = {
        name: _sum(frame, field, year_frame) for name, field in SPECIAL_STAGE_FIELDS.items()
    }
    result["fullTimeEnrollments"] = _sum(frame, "QT_MAT_ESP_INT", year_frame)
    result["fullTimeClasses"] = _sum(frame, "QT_TUR_ESP_INT", year_frame)
    return result


def _aee(frame: pd.DataFrame, year_frame: pd.DataFrame) -> dict[str, Any]:
    eligible_frame = frame[
        pd.to_numeric(frame.get("QT_MAT_ESP"), errors="coerce").fillna(0) > 0
    ]
    eligible = _count(
        frame,
        ("QT_MAT_ESP",),
        year_frame,
        lambda rows: pd.to_numeric(rows["QT_MAT_ESP"], errors="coerce") > 0,
    )
    offer = _count(
        frame,
        ("TP_AEE",),
        year_frame,
        lambda rows: pd.to_numeric(rows["TP_AEE"], errors="coerce").isin([1, 2]),
        missing_is_non_match=True,
    )
    exclusive_aee = _count(
        frame,
        ("TP_AEE",),
        year_frame,
        lambda rows: pd.to_numeric(rows["TP_AEE"], errors="coerce").eq(2),
        missing_is_non_match=True,
    )
    rooms = _count(
        frame,
        ("IN_SALA_ATENDIMENTO_ESPECIAL",),
        year_frame,
        lambda rows: pd.to_numeric(
            rows["IN_SALA_ATENDIMENTO_ESPECIAL"], errors="coerce"
        ).eq(1),
        missing_is_non_match=True,
    )
    exclusive_classes = _count(
        frame,
        ("QT_MAT_ESP_CE",),
        year_frame,
        lambda rows: pd.to_numeric(rows["QT_MAT_ESP_CE"], errors="coerce") > 0,
    )
    eligible_offer = _count(
        eligible_frame,
        ("TP_AEE",),
        year_frame,
        lambda rows: pd.to_numeric(rows["TP_AEE"], errors="coerce").isin([1, 2]),
    )
    eligible_rooms = _count(
        eligible_frame,
        ("IN_SALA_ATENDIMENTO_ESPECIAL",),
        year_frame,
        lambda rows: pd.to_numeric(
            rows["IN_SALA_ATENDIMENTO_ESPECIAL"], errors="coerce"
        ).eq(1),
    )
    return {
        "eligibleSchools": eligible,
        "schoolsOfferingAee": offer,
        "schoolsExclusiveAee": exclusive_aee,
        "schoolsWithResourceRoom": rooms,
        "schoolsWithExclusiveClassEnrollment": exclusive_classes,
        "shareOfferingAee": _percentage(eligible_offer, eligible),
        "shareWithResourceRoom": _percentage(eligible_rooms, eligible),
    }


def _bilingual(frame: pd.DataFrame, year_frame: pd.DataFrame) -> dict[str, Any]:
    result = {
        name: _sum(frame, field, year_frame)
        for name, field in BILINGUAL_SUM_FIELDS.items()
    }
    result["schools"] = _count(
        frame,
        ("QT_MAT_BAS_LIBRAS", "QT_TUR_BAS_LIBRAS"),
        year_frame,
        lambda rows: (
            pd.to_numeric(rows["QT_MAT_BAS_LIBRAS"], errors="coerce").fillna(0)
            + pd.to_numeric(rows["QT_TUR_BAS_LIBRAS"], errors="coerce").fillna(0)
        )
        > 0,
    )
    result["schoolsWithMaterials"] = _count(
        frame,
        ("IN_MATERIAL_PED_BIL_SURDOS",),
        year_frame,
        lambda rows: pd.to_numeric(
            rows["IN_MATERIAL_PED_BIL_SURDOS"], errors="coerce"
        ).eq(1),
    )
    return result


def field_availability(source: pd.DataFrame) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for field in ALL_FIELDS:
        years = [
            year
            for year in YEARS
            if _available(source[source["ano"] == year], field)
        ]
        result[field] = {
            "sourceId": SOURCE_ID,
            "sourceVariable": field,
            "observedYears": years,
            "unavailableYears": [year for year in YEARS if year not in years],
        }
    return result


def build_contract(
    source: pd.DataFrame,
    municipality: dict[str, Any],
    availability: dict[str, Any],
) -> dict[str, Any]:
    code = municipality["id_municipio"]
    if not isinstance(code, str) or re.fullmatch(r"\d{7}", code) is None:
        raise ValueError("Código IBGE municipal deve permanecer texto com sete dígitos.")
    municipal = source[source["id_municipio"] == code]
    years = []
    for year in YEARS:
        year_frame = municipal[municipal["ano"] == year].copy()
        year_frame.attrs["available_fields"] = {
            field
            for field, metadata in availability.items()
            if year in metadata["observedYears"]
        }
        cuts = {}
        for cut in CUTS:
            selected = _cut(year_frame, cut)
            special = _special(selected, year_frame)
            cuts[cut] = {
                "specialEducation": special,
                "commonClassInclusionRate": _percentage(
                    special["commonClassEnrollments"], special["enrollments"]
                ),
                "aee": _aee(selected, year_frame),
                "bilingualDeafEducation": _bilingual(selected, year_frame),
            }
        years.append({"year": year, "cuts": cuts})
    return {
        "schemaVersion": SCHEMA_VERSION,
        "municipality": {
            "code": code,
            "name": municipality["municipio"],
            "slug": municipality.get("slug"),
        },
        "sources": [
            {
                "id": SOURCE_ID,
                "provider": "INEP",
                "survey": "Censo Escolar da Educação Básica",
                "normalizedTable": "censo_educacao_especial_escolas",
                "grain": "NU_ANO_CENSO x CO_ENTIDADE",
                "url": (
                    "https://www.gov.br/inep/pt-br/acesso-a-informacao/"
                    "dados-abertos/microdados/censo-escolar"
                ),
            }
        ],
        "fieldAvailability": availability,
        "cuts": list(CUTS),
        "years": years,
    }


def json_bytes(payload: Any) -> bytes:
    return (
        json.dumps(
            payload,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def write_json_atomic(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(json_bytes(payload))
    os.replace(temporary, path)


def tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def validate_contract(contract: dict[str, Any]) -> list[str]:
    errors = []
    for yearly in contract["years"]:
        total = yearly["cuts"]["total"]["specialEducation"]
        for key in (
            "enrollments",
            "commonClassEnrollments",
            "exclusiveClassEnrollments",
        ):
            point = total[key]
            if point["value"] is not None and point["value"] < 0:
                errors.append(f"{yearly['year']}/{key}: negative")
            if point["value"] == 88888:
                errors.append(f"{yearly['year']}/{key}: 88888")
        values = [
            total[key]
            for key in ("enrollments", "commonClassEnrollments", "exclusiveClassEnrollments")
        ]
        if all(item["state"] in RESOLVED_STATES for item in values):
            if values[1]["value"] > values[0]["value"]:
                errors.append(f"{yearly['year']}: common exceeds total")
            if values[2]["value"] > values[0]["value"]:
                errors.append(f"{yearly['year']}: exclusive exceeds total")
            if values[1]["value"] + values[2]["value"] != values[0]["value"]:
                errors.append(f"{yearly['year']}: common + exclusive != total")
    return errors


def build_manifest(root: Path, municipality_count: int) -> dict[str, Any]:
    municipal_files = sorted((root / "municipios").glob("*.json"))
    return {
        "schemaVersion": SCHEMA_VERSION,
        "municipalityCount": municipality_count,
        "fileCount": len(municipal_files),
        "years": list(YEARS),
        "cuts": list(CUTS),
        "contentHash": tree_hash(root / "municipios"),
        "municipalitiesPath": "municipios/{IBGE}.json",
    }


def replace_directory_atomically(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    backup = destination.with_name(destination.name + ".previous")
    if backup.exists():
        shutil.rmtree(backup)
    if destination.exists():
        os.replace(destination, backup)
    try:
        try:
            os.replace(source, destination)
        except PermissionError:
            if destination.exists():
                raise
            shutil.copytree(source, destination)
            shutil.rmtree(source)
    except Exception:
        if backup.exists() and not destination.exists():
            os.replace(backup, destination)
        raise
    if backup.exists():
        shutil.rmtree(backup)


def _build_municipality_contract(
    job: tuple[pd.DataFrame, dict[str, Any], dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    source, municipality, availability = job
    contract = build_contract(source, municipality, availability)
    return municipality, contract, validate_contract(contract)


def validate_source_municipality_universe(
    source: pd.DataFrame,
    expected_ids: frozenset[str],
) -> None:
    if "id_municipio" not in source.columns:
        raise ValueError("A fonte não possui id_municipio.")
    raw_codes = source["id_municipio"].dropna().tolist()
    invalid = sorted(
        {
            repr(value)
            for value in raw_codes
            if not isinstance(value, str)
            or re.fullmatch(r"\d{7}", value) is None
        }
    )
    if invalid:
        raise ValueError(
            "A fonte deve preservar código municipal como texto; "
            f"inválidos={invalid[:5]}."
        )
    observed_ids = set(raw_codes)
    if observed_ids != expected_ids:
        raise ValueError(
            "A fonte diverge do registro municipal; "
            f"ausentes={sorted(expected_ids - observed_ids)[:5]}, "
            f"extras={sorted(observed_ids - expected_ids)[:5]}."
        )
    for year in YEARS:
        year_ids = set(source.loc[source["ano"].eq(year), "id_municipio"].dropna())
        if year_ids != expected_ids:
            raise ValueError(
                f"A fonte de {year} diverge do registro municipal; "
                f"ausentes={sorted(expected_ids - year_ids)[:5]}, "
                f"extras={sorted(year_ids - expected_ids)[:5]}."
            )


def materialize(
    source: pd.DataFrame,
    municipalities: list[dict[str, Any]],
    destination: Path,
) -> dict[str, Any]:
    if source.duplicated(["ano", "cod_escola"]).any():
        raise ValueError("A fonte não possui chave ano x escola única.")
    municipality_ids = [municipality["id_municipio"] for municipality in municipalities]
    if any(
        not isinstance(identifier, str)
        or re.fullmatch(r"\d{7}", identifier) is None
        for identifier in municipality_ids
    ):
        raise ValueError("O registro municipal deve preservar códigos IBGE textuais.")
    if len(set(municipality_ids)) != len(municipality_ids):
        raise ValueError("O registro municipal contém códigos duplicados.")
    expected_ids = frozenset(municipality_ids)
    validate_source_municipality_universe(source, expected_ids)
    availability = field_availability(source)
    source_by_municipality = {
        code: frame
        for code, frame in source.groupby("id_municipio", sort=False)
    }
    temporary = Path(tempfile.mkdtemp(prefix=".special-education-", dir=destination.parent))
    errors = []
    try:
        ordered_municipalities = list(municipalities)

        jobs = (
            (
                source_by_municipality.get(
                    municipality["id_municipio"],
                    source.iloc[0:0],
                ),
                municipality,
                availability,
            )
            for municipality in ordered_municipalities
        )
        with ProcessPoolExecutor(max_workers=8) as executor:
            contracts = executor.map(_build_municipality_contract, jobs)
            for municipality, contract, contract_errors in contracts:
                errors.extend(
                    f"{municipality['id_municipio']}: {error}"
                    for error in contract_errors
                )
                write_json_atomic(
                    temporary
                    / "municipios"
                    / f"{municipality['id_municipio']}.json",
                    contract,
                )
        if errors:
            raise ValueError(f"Validação falhou: {errors[:10]}")
        manifest = build_manifest(temporary, len(municipalities))
        generated_ids = {
            path.stem for path in (temporary / "municipios").glob("*.json")
        }
        if generated_ids != expected_ids:
            raise ValueError(
                "A materialização não produziu o conjunto municipal exato; "
                f"ausentes={sorted(expected_ids - generated_ids)[:5]}, "
                f"extras={sorted(generated_ids - expected_ids)[:5]}."
            )
        write_json_atomic(temporary / "index.json", manifest)
        replace_directory_atomically(temporary, destination)
        temporary = None
        return manifest
    finally:
        if temporary is not None and temporary.exists():
            shutil.rmtree(temporary)
