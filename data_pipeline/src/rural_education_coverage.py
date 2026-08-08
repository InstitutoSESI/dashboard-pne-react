"""Contrato do indicador de cobertura estimada da população rural de 4–17."""

from __future__ import annotations

import json
from typing import Any, Iterable


INDICATOR_ID = "rural-cobertura-estimada-4-17"
ENROLLMENT_YEARS = (2023, 2024, 2025)
ENROLLMENT_COMPONENTS = {
    "age4To5": "4_5",
    "age6To10": "6_10",
    "age11To14": "11_14",
    "age15To17": "15_17",
}


def _clean_number(value: object) -> float | int | None:
    if value is None:
        return None
    try:
        if value != value:  # NaN
            return None
    except TypeError:
        pass
    numeric = float(value)
    return int(numeric) if numeric.is_integer() else numeric


def _metadata(row: dict[str, Any]) -> dict[str, Any]:
    metadata = row.get("metadados_fonte")
    if isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except json.JSONDecodeError:
            metadata = None
    return metadata if isinstance(metadata, dict) else {}


def _population_row(population_rows: list[dict[str, Any]]) -> dict[str, Any]:
    if len(population_rows) > 1:
        raise ValueError("População rural municipal duplicada.")
    return population_rows[0] if population_rows else {
        "populacao_rural_estimada_4_17": None,
        "status_valor": "missing",
    }


def _enrollment_value(
    enrollment_rows: list[dict[str, Any]], year: int, age_group: str
) -> int | None:
    matches = [
        row
        for row in enrollment_rows
        if int(row.get("ano") or 0) == year
        and str(row.get("faixa_etaria")) == age_group
    ]
    if len(matches) > 1:
        raise ValueError(f"Matrícula rural duplicada para {year}/{age_group}.")
    if not matches or str(matches[0].get("status_valor")) != "available":
        return None
    value = _clean_number(matches[0].get("matriculas"))
    return int(value) if value is not None else None


def _series_item(
    population_value: float | int | None,
    population_status: str,
    components: dict[str, int | None],
) -> dict[str, Any]:
    components_available = all(value is not None for value in components.values())
    aligned_total = (
        sum(int(value) for value in components.values()) if components_available else None
    )
    enrollments = {**components, "alignedTotal": aligned_total}
    if population_status != "available" or population_value is None:
        return {"enrollments": enrollments, "percentage": None, "status": "unavailable"}
    if not components_available:
        return {"enrollments": enrollments, "percentage": None, "status": "unavailable"}
    if population_value == 0:
        status = "not_applicable" if aligned_total == 0 else "denominator_zero_with_enrollments"
        return {"enrollments": enrollments, "percentage": None, "status": status}
    return {
        "enrollments": enrollments,
        "percentage": aligned_total / population_value * 100,
        "status": "available",
    }


def _enrollment_sources(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    sources: dict[int, dict[str, Any]] = {}
    for row in rows:
        year = int(row.get("ano") or 0)
        metadata = _metadata(row)
        if year and metadata:
            sources.setdefault(year, metadata)
    result = []
    for year, metadata in sorted(sources.items()):
        source = {
            "provider": "INEP",
            "survey": "Censo Escolar da Educação Básica",
            "year": year,
            "unit": "matrículas",
            "municipalityBasis": "localização do estabelecimento de ensino",
            "schoolSituation": "em atividade",
            "schoolLocation": "rural",
        }
        for source_key, target_key in (
            ("officialUrl", "officialUrl"),
            ("sourceFile", "sourceFile"),
            ("sourceSha256", "sourceSha256"),
            ("sourceSize", "sourceSize"),
        ):
            if metadata.get(source_key) is not None:
                source[target_key] = metadata[source_key]
        result.append(source)
    return result


def build_coverage_contract(
    population_rows: list[dict[str, Any]],
    enrollment_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Relaciona matrículas rurais anuais ao denominador estimado do Censo 2022."""

    population = _population_row(population_rows)
    population_value = _clean_number(population.get("populacao_rural_estimada_4_17"))
    population_status = str(population.get("status_valor") or "missing")
    metadata = _metadata(population)
    series = {
        str(year): _series_item(
            population_value,
            population_status,
            {
                component: _enrollment_value(enrollment_rows, year, age_group)
                for component, age_group in ENROLLMENT_COMPONENTS.items()
            },
        )
        for year in ENROLLMENT_YEARS
    }

    source_rural = metadata.get("ruralGroups") or {}
    source_weights = metadata.get("exactAgeWeights") or {}
    sources = [
        {
            "provider": "IBGE",
            "survey": "Censo Demográfico 2022",
            "sidraAggregate": str(source_rural.get("aggregate") or "10089"),
            "period": 2022,
            "variable": "População residente",
            "unit": "pessoas",
            "territorialLevel": "Município",
            "householdSituation": "rural",
            "populationBasis": "residência no município",
            **{
                key: source_rural[key]
                for key in ("queryUrl", "metadataUrl", "responseSha256")
                if source_rural.get(key) is not None
            },
        },
        {
            "provider": "IBGE",
            "survey": "Censo Demográfico 2022",
            "sidraAggregate": str(source_weights.get("aggregate") or "9606"),
            "period": 2022,
            "variable": "População residente por idade simples",
            "unit": "pessoas",
            "use": "pesos municipais para desagregar somente as faixas de borda",
            **{
                key: source_weights[key]
                for key in ("queryUrl", "metadataUrl", "responseSha256")
                if source_weights.get(key) is not None
            },
        },
        *_enrollment_sources(enrollment_rows),
    ]

    return {
        "schemaVersion": 1,
        "indicatorId": INDICATOR_ID,
        "label": "Cobertura estimada da população rural de 4 a 17 anos na Educação Básica",
        "ageRange": {"from": 4, "to": 17, "label": "4 a 17 anos"},
        "population": {
            "year": 2022,
            "value": population_value,
            "unit": "pessoas",
            "status": population_status,
            "label": "População rural estimada de 4 a 17 anos",
            "components": {
                "rural0To4": _clean_number(population.get("populacao_rural_0_4")),
                "rural5To9": _clean_number(population.get("populacao_rural_5_9")),
                "rural10To14": _clean_number(population.get("populacao_rural_10_14")),
                "rural15To19": _clean_number(population.get("populacao_rural_15_19")),
                "age4Weight": _clean_number(population.get("peso_idade_4_no_grupo_0_4")),
                "age15To17Weight": _clean_number(
                    population.get("peso_idades_15_17_no_grupo_15_19")
                ),
            },
        },
        "series": series,
        "methodologicalFlags": [
            "estimated_population_denominator",
            "fixed_2022_denominator",
            "enrollments_not_unique_people",
            "resident_population_vs_school_location",
            "different_source_universes",
            "may_exceed_100",
        ],
        "methodologicalNotes": [
            (
                "O denominador de 4 a 17 anos é estimado a partir das faixas rurais "
                "0–4, 5–9, 10–14 e 15–19 do Censo 2022. Nas faixas de borda, a "
                "proporção da idade 4 e das idades 15–17 é aproximada pela distribuição "
                "etária da população total do próprio município."
            ),
            (
                "O numerador soma as matrículas por idade registradas em escolas em "
                "atividade e de localização rural no município; ele não identifica a "
                "situação rural ou urbana do domicílio de cada estudante."
            ),
            (
                "O Censo Demográfico contabiliza pessoas e o Censo Escolar contabiliza "
                "matrículas. Uma pessoa pode ter mais de uma matrícula e estudantes "
                "podem se deslocar entre áreas rurais, urbanas e municípios."
            ),
            (
                "O indicador é uma aproximação de cobertura territorial, não uma taxa "
                "oficial de escolarização, e pode superar 100%."
            ),
        ],
        "sources": sources,
    }
