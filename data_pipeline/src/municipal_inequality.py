"""Materialização do recorte municipal de desigualdade educacional."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import Any


DOCUMENT_SCHEMA_VERSION = "municipal-inequality-v1"
METHODOLOGY_VERSION = "municipal-inequality-p4b-v1"
MINIMUM_CELL_SIZE = 10


def _finite_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric if math.isfinite(numeric) else None


def _inequality_number(value: Any) -> int | float | None:
    numeric = _finite_number(value)
    if numeric is None:
        return None
    return int(numeric) if numeric.is_integer() else numeric


def _empty_group(group_code: str, status: str) -> dict[str, Any]:
    return {
        "groupCode": group_code,
        "status": status,
        "publicationStatus": status,
        "year": None,
        "numerator": None,
        "denominator": None,
        "percentage": None,
        "coverage": "missing",
        "suppressionReasonCode": None,
    }


def build_urban_rural_integral_pilot(
    rows: Sequence[Mapping[str, Any]] | None,
) -> dict[str, Any]:
    """Calcula o recorte urbano/rural sem imputação nem mistura de períodos."""

    public_rows = [
        row
        for row in (rows or [])
        if str(row.get("dependencia") or "").strip().lower() == "publica"
        and str(row.get("localizacao") or "").strip().lower()
        in {"urbana", "rural"}
        and _finite_number(row.get("ano")) is not None
    ]
    available_years = sorted(
        {int(float(row["ano"])) for row in public_rows}, reverse=True
    )
    year = available_years[0] if available_years else None

    groups: list[dict[str, Any]] = []
    for group_code, source_code in (("urban", "urbana"), ("rural", "rural")):
        matching = (
            [
                row
                for row in public_rows
                if int(float(row["ano"])) == year
                and str(row.get("localizacao") or "").strip().lower()
                == source_code
            ]
            if year is not None
            else []
        )
        if not matching:
            group = _empty_group(group_code, "missing")
            group["year"] = year
            groups.append(group)
            continue
        if len(matching) != 1:
            group = _empty_group(group_code, "methodology_incompatible")
            group["year"] = year
            group["coverage"] = "municipality_public_network"
            groups.append(group)
            continue

        numerator = _inequality_number(matching[0].get("matriculas_integral"))
        denominator = _inequality_number(matching[0].get("matriculas"))
        if numerator is None or denominator is None:
            group = _empty_group(group_code, "missing")
            group["year"] = year
            groups.append(group)
            continue
        if denominator < 0 or numerator < 0 or numerator > denominator:
            group = _empty_group(group_code, "methodology_incompatible")
            group["year"] = year
            group["coverage"] = "municipality_public_network"
            groups.append(group)
            continue
        if denominator == 0:
            groups.append(
                {
                    "groupCode": group_code,
                    "status": "not_applicable",
                    "publicationStatus": "not_applicable",
                    "year": year,
                    "numerator": 0,
                    "denominator": 0,
                    "percentage": None,
                    "coverage": "municipality_public_network",
                    "suppressionReasonCode": None,
                }
            )
            continue

        complementary_count = denominator - numerator
        has_small_cell = (
            denominator < MINIMUM_CELL_SIZE
            or 0 < numerator < MINIMUM_CELL_SIZE
            or 0 < complementary_count < MINIMUM_CELL_SIZE
        )
        if has_small_cell:
            group = _empty_group(group_code, "suppressed_small_cell")
            group["year"] = year
            group["coverage"] = "municipality_public_network"
            group["suppressionReasonCode"] = "small_cell"
            groups.append(group)
            continue

        groups.append(
            {
                "groupCode": group_code,
                "status": "available",
                "publicationStatus": "available",
                "year": year,
                "numerator": numerator,
                "denominator": denominator,
                "percentage": round(
                    float(numerator) / float(denominator) * 100.0, 6
                ),
                "coverage": "municipality_public_network",
                "suppressionReasonCode": None,
            }
        )

    if any(group["status"] == "suppressed_small_cell" for group in groups):
        for group in groups:
            if group["status"] in {"available", "not_applicable"}:
                group.update(
                    {
                        "status": "suppressed_small_cell",
                        "publicationStatus": "suppressed_small_cell",
                        "numerator": None,
                        "denominator": None,
                        "percentage": None,
                        "suppressionReasonCode": "complementary_suppression",
                    }
                )

    statuses = {group["status"] for group in groups}
    if "methodology_incompatible" in statuses:
        status = "methodology_incompatible"
    elif "suppressed_small_cell" in statuses:
        status = "suppressed_small_cell"
    elif "available" in statuses:
        status = "available"
    elif statuses == {"not_applicable"}:
        status = "not_applicable"
    else:
        status = "missing"

    group_by_code = {group["groupCode"]: group for group in groups}
    urban = group_by_code["urban"]
    rural = group_by_code["rural"]
    observed_difference = (
        round(float(urban["percentage"]) - float(rural["percentage"]), 6)
        if urban["status"] == rural["status"] == "available"
        else None
    )
    return {
        "status": status,
        "methodologyVersion": METHODOLOGY_VERSION,
        "indicatorId": "basico_integral",
        "dimension": "urban_rural",
        "year": year,
        "universeCode": "public_basic_education_enrollments",
        "formulaCode": "integral_enrollments_over_eligible_enrollments",
        "minimumCellSize": MINIMUM_CELL_SIZE,
        "observedDifferencePercentagePoints": observed_difference,
        "groups": groups,
    }


def build_document(
    *,
    municipality_id: str,
    municipality_name: str,
    generated_at: str,
    rows: Sequence[Mapping[str, Any]] | None = None,
    inequality_pilot: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Produz o contrato incorporado aos detalhes municipais compartilhados."""

    if len(municipality_id) != 7 or not municipality_id.isdigit():
        raise ValueError(f"Código municipal inválido: {municipality_id!r}.")
    if not municipality_name.strip():
        raise ValueError("Nome municipal ausente.")
    if not generated_at.strip():
        raise ValueError("Data de geração ausente.")
    if inequality_pilot is not None and rows is not None:
        raise ValueError("Informe linhas ou um piloto já publicado, nunca ambos.")
    pilot = (
        deepcopy(dict(inequality_pilot))
        if inequality_pilot is not None
        else build_urban_rural_integral_pilot(rows)
    )
    expected_identity = {
        "methodologyVersion": METHODOLOGY_VERSION,
        "indicatorId": "basico_integral",
        "dimension": "urban_rural",
        "universeCode": "public_basic_education_enrollments",
        "formulaCode": "integral_enrollments_over_eligible_enrollments",
        "minimumCellSize": MINIMUM_CELL_SIZE,
    }
    for field, expected in expected_identity.items():
        if pilot.get(field) != expected:
            raise ValueError(
                f"Piloto de desigualdade divergente em {field}: "
                f"{pilot.get(field)!r}; esperado {expected!r}."
            )
    groups = pilot.get("groups")
    if not isinstance(groups, list) or {
        group.get("groupCode")
        for group in groups
        if isinstance(group, Mapping)
    } != {"urban", "rural"}:
        raise ValueError("Piloto de desigualdade sem os grupos urbano e rural.")
    return {
        "schemaVersion": DOCUMENT_SCHEMA_VERSION,
        "generatedAt": generated_at,
        "municipality": {
            "id": municipality_id,
            "name": municipality_name,
        },
        "inequalityPilot": pilot,
    }


__all__ = [
    "DOCUMENT_SCHEMA_VERSION",
    "METHODOLOGY_VERSION",
    "MINIMUM_CELL_SIZE",
    "build_document",
    "build_urban_rural_integral_pilot",
]
