"""Resultados homologados da rodada acelerada do PNE.

O módulo não consulta bancos nem serviços externos. Ele projeta, em um único
retrato municipal, componentes que já existem nas materializações públicas de
Educação Especial, Educação Escolar Indígena e Educação Superior.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any


AEE_RELATION_ID = "relation.10.b.aee_oferta_escolas_elegiveis"
INDIGENOUS_RELATION_ID = (
    "relation.9.d.educacao_indigena_cobertura_estimada_4_17"
)
HIGHER_GRADUATES_RELATION_ID = (
    "relation.14.c.superior_concluintes_oferta_local"
)
HIGHER_FACULTY_EDUCATION_RELATION_ID = (
    "relation.15.c.superior_docentes_mestres_doutores_sede"
)

AVAILABLE_POINT_STATES = frozenset({"observed", "derived_zero"})
FACULTY_EDUCATION_CATEGORIES = (
    "Sem Graduação",
    "Graduação",
    "Especialização",
    "Mestrado",
    "Doutorado",
)
ADVANCED_DEGREE_CATEGORIES = frozenset({"Mestrado", "Doutorado"})


def _finite_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def _absence(
    *,
    year: int,
    status: str,
    reason_code: str,
) -> dict[str, Any]:
    return {
        "dataStatus": status,
        "reasonCode": reason_code,
        "year": year,
        "value": None,
    }


def aee_school_offer_result(document: Mapping[str, Any]) -> dict[str, Any]:
    """Extrai a oferta escolar de AEE; não a converte em taxa de estudantes."""

    years = [
        item
        for item in document.get("years") or []
        if isinstance(item, Mapping) and isinstance(item.get("year"), int)
    ]
    if not years:
        return _absence(
            year=2025,
            status="unavailable",
            reason_code="required_component_unavailable",
        )
    latest = max(years, key=lambda item: int(item["year"]))
    year = int(latest["year"])
    total = (latest.get("cuts") or {}).get("total") or {}
    component = (total.get("aee") or {}).get("shareOfferingAee") or {}
    numerator = component.get("numerator")
    denominator = component.get("denominator")
    value = component.get("value")

    if _finite_number(denominator) and float(denominator) == 0:
        return _absence(
            year=year,
            status="not_applicable",
            reason_code="denominator_zero",
        )
    if (
        component.get("state") not in AVAILABLE_POINT_STATES
        or not _finite_number(numerator)
        or not _finite_number(denominator)
        or float(denominator) <= 0
        or not _finite_number(value)
    ):
        return _absence(
            year=year,
            status="unavailable",
            reason_code="required_component_unavailable",
        )
    if float(numerator) < 0 or float(numerator) > float(denominator):
        raise ValueError("Oferta de AEE contém contagens incompatíveis.")

    return {
        "dataStatus": "available",
        "year": year,
        "value": float(value),
        "numerator": float(numerator),
        "denominator": float(denominator),
        "publicReading": (
            f"{int(numerator)} de {int(denominator)} escolas com matrículas da "
            "educação especial oferecem AEE. A medida descreve oferta escolar "
            "e não a proporção de estudantes efetivamente atendidos da Meta 10.b."
        ),
    }


def indigenous_coverage_result(document: Mapping[str, Any]) -> dict[str, Any]:
    """Projeta somente o retrato mais recente, com denominador censitário 2022."""

    block = (document.get("blocos") or {}).get("educacao_indigena") or {}
    coverage = block.get("coberturaEstimada") or {}
    population = coverage.get("population") or {}
    population_year = population.get("year")
    denominator = population.get("value")
    raw_series = coverage.get("series") or {}
    years = sorted(
        int(year)
        for year in raw_series
        if str(year).isdigit()
    )
    year = years[-1] if years else 2025

    if population_year != 2022 or population.get("status") != "available":
        return _absence(
            year=year,
            status="unavailable",
            reason_code="resident_population_unavailable",
        )
    if not _finite_number(denominator):
        return _absence(
            year=year,
            status="unavailable",
            reason_code="resident_population_unavailable",
        )
    if float(denominator) == 0:
        return _absence(
            year=year,
            status="not_applicable",
            reason_code="denominator_zero",
        )
    if float(denominator) < 0 or not years:
        return _absence(
            year=year,
            status="unavailable",
            reason_code="required_component_unavailable",
        )

    point = raw_series.get(str(year), raw_series.get(year)) or {}
    numerator = (point.get("enrollments") or {}).get("alignedTotal")
    value = point.get("percentage")
    if (
        point.get("status") != "available"
        or not _finite_number(numerator)
        or float(numerator) < 0
        or not _finite_number(value)
    ):
        return _absence(
            year=year,
            status="unavailable",
            reason_code="required_component_unavailable",
        )

    reading = (
        f"{int(numerator)} matrículas da oferta escolar indígena localizada no "
        f"município em {year}, para {int(denominator)} pessoas indígenas "
        "residentes de 4 a 17 anos recenseadas em 2022. É uma medida "
        "complementar: localização da oferta e residência usam bases "
        "territoriais distintas."
    )
    if float(value) > 100:
        reading += (
            " O resultado acima de 100% foi preservado porque matrículas não "
            "equivalem a pessoas únicas e pode haver deslocamento entre municípios."
        )
    return {
        "dataStatus": "available",
        "year": year,
        "value": float(value),
        "numerator": float(numerator),
        "denominator": float(denominator),
        "publicReading": reading,
    }


def higher_graduates_result(document: Mapping[str, Any]) -> dict[str, Any]:
    """Usa o último total observado de concluintes por local da oferta."""

    indicator = (document.get("indicators") or {}).get("esup-concluintes") or {}
    points = [
        point
        for point in indicator.get("series") or []
        if (
            isinstance(point, Mapping)
            and isinstance(point.get("year"), int)
            and point.get("status") in AVAILABLE_POINT_STATES
            and _finite_number(point.get("value"))
        )
    ]
    if not points:
        return _absence(
            year=2024,
            status="unavailable",
            reason_code="local_offer_unavailable",
        )
    latest = max(points, key=lambda point: int(point["year"]))
    value = float(latest["value"])
    if value < 0:
        raise ValueError("Concluintes locais não podem ser negativos.")
    return {
        "dataStatus": "available",
        "year": int(latest["year"]),
        "value": value,
        "publicReading": (
            "Concluintes vinculados a cursos cuja oferta está localizada no "
            f"município em {int(latest['year'])}. O total não representa "
            "residentes e não distribui a meta nacional entre municípios."
        ),
    }


def higher_faculty_education_result(
    document: Mapping[str, Any],
) -> dict[str, Any]:
    """Calcula mestres+doutores apenas em decomposição exaustiva por sede."""

    candidates = [
        item
        for item in document.get("breakdowns") or []
        if (
            isinstance(item, Mapping)
            and item.get("id") == "faculty_education"
            and isinstance(item.get("year"), int)
            and item.get("status") == "observed"
            and item.get("exhaustive") is True
        )
    ]
    if not candidates:
        not_applicable = any(
            isinstance(item, Mapping)
            and item.get("id") == "faculty_education"
            and item.get("status") == "not_applicable"
            for item in document.get("breakdowns") or []
        )
        return _absence(
            year=2024,
            status="not_applicable" if not_applicable else "unavailable",
            reason_code=(
                "denominator_zero"
                if not_applicable
                else "exhaustive_faculty_education_unavailable"
            ),
        )

    latest = max(candidates, key=lambda item: int(item["year"]))
    categories = {
        str(category.get("id")): category
        for category in latest.get("categories") or []
        if isinstance(category, Mapping)
    }
    if set(categories) != set(FACULTY_EDUCATION_CATEGORIES):
        return _absence(
            year=int(latest["year"]),
            status="unavailable",
            reason_code="exhaustive_faculty_education_unavailable",
        )
    values: dict[str, float] = {}
    for category_id in FACULTY_EDUCATION_CATEGORIES:
        category = categories[category_id]
        value = category.get("value")
        if (
            category.get("status") not in AVAILABLE_POINT_STATES
            or not _finite_number(value)
            or float(value) < 0
        ):
            return _absence(
                year=int(latest["year"]),
                status="unavailable",
                reason_code="exhaustive_faculty_education_unavailable",
            )
        values[category_id] = float(value)

    denominator = sum(values.values())
    if denominator == 0:
        return _absence(
            year=int(latest["year"]),
            status="not_applicable",
            reason_code="denominator_zero",
        )
    numerator = sum(
        values[category_id] for category_id in ADVANCED_DEGREE_CATEGORIES
    )
    value = 100 * numerator / denominator
    return {
        "dataStatus": "available",
        "year": int(latest["year"]),
        "value": value,
        "numerator": numerator,
        "denominator": denominator,
        "publicReading": (
            f"{int(numerator)} de {int(denominator)} docentes nas IES com sede "
            f"administrativa no município em {int(latest['year'])} têm mestrado "
            "ou doutorado. A base local não comprova todos os recortes jurídicos "
            "da Meta 15.c e não representa docentes residentes."
        ),
    }


def build_accelerated_package_results(
    *,
    special_education: Mapping[str, Any],
    municipal_education: Mapping[str, Any],
    higher_education: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    """Retorna as quatro relações homologadas com estados de ausência explícitos."""

    return {
        AEE_RELATION_ID: aee_school_offer_result(special_education),
        INDIGENOUS_RELATION_ID: indigenous_coverage_result(municipal_education),
        HIGHER_GRADUATES_RELATION_ID: higher_graduates_result(higher_education),
        HIGHER_FACULTY_EDUCATION_RELATION_ID: higher_faculty_education_result(
            higher_education
        ),
    }


__all__ = [
    "AEE_RELATION_ID",
    "HIGHER_FACULTY_EDUCATION_RELATION_ID",
    "HIGHER_GRADUATES_RELATION_ID",
    "INDIGENOUS_RELATION_ID",
    "aee_school_offer_result",
    "build_accelerated_package_results",
    "higher_faculty_education_result",
    "higher_graduates_result",
    "indigenous_coverage_result",
]
