"""Contrato do indicador de cobertura estimada da Educação Escolar Indígena."""

from __future__ import annotations

import json
from typing import Any, Iterable


INDICATOR_ID = "educacao-indigena-cobertura-estimada-4-17"
ENROLLMENT_YEARS = (2023, 2024, 2025)
COMPONENT_CUTS = {
    "preSchool": "pre_escola",
    "elementarySchool": "ensino_fundamental",
    "highSchool": "ensino_medio",
}
REFERENCE_GROUPS = {
    "preSchool": ("4_5", "4 a 5 anos"),
    "elementarySchool": ("6_14", "6 a 14 anos"),
    "highSchool": ("15_17", "15 a 17 anos"),
}


def _clean_integer(value: object) -> int | None:
    if value is None:
        return None
    try:
        if value != value:  # NaN
            return None
    except TypeError:
        pass
    return int(value)


def _source_metadata(population_rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    for row in population_rows:
        metadata = row.get("metadados_fonte")
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except json.JSONDecodeError:
                metadata = None
        if isinstance(metadata, dict):
            return metadata
    return {}


def _population_group(
    population_rows: list[dict[str, Any]], group_key: str
) -> dict[str, Any]:
    matches = [
        row for row in population_rows if str(row.get("faixa_etaria")) == group_key
    ]
    if len(matches) > 1:
        raise ValueError(f"Faixa populacional duplicada: {group_key}.")
    if not matches:
        return {
            "pessoas_indigenas": None,
            "status_valor": "missing",
            "tabela_origem": "9970",
        }
    return matches[0]


def _enrollment_value(
    enrollment_rows: list[dict[str, Any]], year: int, cut: str
) -> int | None:
    matches = [
        row
        for row in enrollment_rows
        if int(row.get("ano") or 0) == year
        and str(row.get("unidade")) == "matriculas"
        and str(row.get("recorte")) == cut
    ]
    if len(matches) > 1:
        raise ValueError(f"Matrícula duplicada para {year}/{cut}.")
    return _clean_integer(matches[0].get("valor")) if matches else None


def _series_item(
    population_value: int | None,
    population_status: str,
    components: dict[str, int | None],
) -> dict[str, Any]:
    components_available = all(value is not None for value in components.values())
    aligned_total = (
        sum(int(value) for value in components.values())
        if components_available
        else None
    )
    enrollments = {**components, "alignedTotal": aligned_total}

    if population_status != "available" or population_value is None:
        return {
            "enrollments": enrollments,
            "percentage": None,
            "status": "unavailable",
        }
    if not components_available:
        return {
            "enrollments": enrollments,
            "percentage": None,
            "status": "unavailable",
        }
    if population_value == 0:
        if aligned_total == 0:
            return {
                "enrollments": enrollments,
                "percentage": None,
                "status": "not_applicable",
            }
        return {
            "enrollments": enrollments,
            "percentage": None,
            "status": "denominator_zero_with_enrollments",
        }
    return {
        "enrollments": enrollments,
        "percentage": aligned_total / population_value * 100,
        "status": "available",
    }


def build_coverage_contract(
    population_rows: list[dict[str, Any]],
    enrollment_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Relaciona as três etapas oficiais ao denominador fixo do Censo 2022."""

    population_4_17 = _population_group(population_rows, "4_17")
    population_value = _clean_integer(population_4_17.get("pessoas_indigenas"))
    population_status = str(population_4_17.get("status_valor") or "missing")
    metadata = _source_metadata(population_rows)
    aggregate = str(
        metadata.get("aggregate")
        or population_4_17.get("tabela_origem")
        or "9970"
    )

    series = {}
    inep_sources = set()
    for year in ENROLLMENT_YEARS:
        components = {
            component: _enrollment_value(enrollment_rows, year, cut)
            for component, cut in COMPONENT_CUTS.items()
        }
        series[str(year)] = _series_item(
            population_value,
            population_status,
            components,
        )
        for row in enrollment_rows:
            if (
                int(row.get("ano") or 0) == year
                and str(row.get("unidade")) == "matriculas"
                and row.get("tabela_fonte")
            ):
                inep_sources.add((year, str(row["tabela_fonte"])))

    reference_groups = {}
    for component, (group_key, age_range) in REFERENCE_GROUPS.items():
        group = _population_group(population_rows, group_key)
        reference_groups[component] = {
            "ageRange": age_range,
            "population2022": _clean_integer(group.get("pessoas_indigenas")),
            "status": str(group.get("status_valor") or "missing"),
        }

    ibge_source = {
        "provider": "IBGE",
        "survey": "Censo Demográfico 2022",
        "sidraAggregate": aggregate,
        "period": 2022,
        "variable": "Pessoas indígenas",
        "unit": "pessoas",
        "territorialLevel": "Município",
        "populationBasis": "residência no município",
    }
    for source_key, target_key in (
        ("extractedAt", "extractedAt"),
        ("queryUrl", "queryUrl"),
        ("metadataUrl", "metadataUrl"),
        ("responseSha256", "responseSha256"),
        ("importerSchemaVersion", "importerSchemaVersion"),
    ):
        if metadata.get(source_key) is not None:
            ibge_source[target_key] = metadata[source_key]

    sources = [ibge_source]
    sources.extend(
        {
            "provider": "INEP",
            "survey": "Sinopse Estatística da Educação Básica",
            "year": year,
            "table": table,
            "unit": "matrículas",
            "municipalityBasis": "localização do estabelecimento de ensino",
        }
        for year, table in sorted(inep_sources)
    )

    return {
        "schemaVersion": 1,
        "indicatorId": INDICATOR_ID,
        "label": "Cobertura estimada da educação escolar indígena — 4 a 17 anos",
        "ageRange": {"from": 4, "to": 17, "label": "4 a 17 anos"},
        "population": {
            "year": 2022,
            "value": population_value,
            "unit": "pessoas",
            "status": population_status,
            "label": "População indígena recenseada em 2022",
            "source": {
                "provider": "IBGE",
                "survey": "Censo Demográfico 2022",
                "sidraAggregate": aggregate,
            },
        },
        "series": series,
        "referenceAgeGroups": reference_groups,
        "methodologicalFlags": [
            "fixed_2022_denominator",
            "enrollments_not_unique_people",
            "different_source_universes",
            "resident_population_vs_school_location",
            "may_exceed_100",
        ],
        "methodologicalNotes": [
            (
                "O denominador corresponde à população indígena residente no município "
                "e recenseada em 2022; o numerador corresponde às matrículas vinculadas "
                "à oferta escolar localizada no município em cada ano."
            ),
            (
                "O Censo Demográfico contabiliza pessoas, enquanto a Sinopse contabiliza "
                "matrículas. Uma pessoa pode possuir mais de uma matrícula e estudantes "
                "podem se deslocar entre municípios."
            ),
            (
                "Nem toda pessoa indígena matriculada frequenta necessariamente uma "
                "oferta classificada como Educação Escolar Indígena. O indicador não "
                "identifica indivíduos e não é uma taxa oficial de escolarização."
            ),
            (
                "O resultado pode superar 100% porque as matrículas não representam "
                "necessariamente pessoas únicas e os universos territorial e temporal "
                "das fontes não são idênticos."
            ),
        ],
        "sources": sources,
    }
