"""Materializa o contrato municipal-education-overview-v1 sem gravar dados públicos.

O módulo recebe linhas no grão da ``vw_educacao_visao_geral_municipal`` e
produz um contrato isolado por município. A escrita em ``public/data`` fica
intencionalmente fora deste módulo e será responsabilidade da VGM-3.
"""

from __future__ import annotations

import math
import re
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from typing import Any


SCHEMA_VERSION = "municipal-education-overview-v1"
SOURCE_ID = "inep_censo_escolar"
PERFORMANCE_SOURCE_ID = "inep_taxas_rendimento_escolar"
SOURCE_URL = (
    "https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/"
    "microdados/censo-escolar"
)
PERFORMANCE_SOURCE_URL = (
    "https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/"
    "indicadores-educacionais/taxas-de-rendimento-escolar"
)
VIEW_NAME = "vw_educacao_visao_geral_municipal"
REFERENCE_YEAR = 2025
COMPARISON_YEAR = 2015

NETWORKS = ("municipal", "estadual", "federal", "privada")
LOCATIONS = ("urbana", "rural")
CORE_FIELDS = (
    "mat_basico",
    "mat_infantil",
    "mat_infantil_creche",
    "mat_infantil_pre",
    "mat_fundamental",
    "mat_fundamental_anos_iniciais",
    "mat_fundamental_anos_finais",
)
VALIDATED_FIELDS = CORE_FIELDS + ("mat_medio",)
SOURCE_FIELDS = {
    "mat_basico": "QT_MAT_BAS",
    "mat_infantil": "QT_MAT_INF",
    "mat_infantil_creche": "QT_MAT_INF_CRE",
    "mat_infantil_pre": "QT_MAT_INF_PRE",
    "mat_fundamental": "QT_MAT_FUND",
    "mat_fundamental_anos_iniciais": "QT_MAT_FUND_AI",
    "mat_fundamental_anos_finais": "QT_MAT_FUND_AF",
    "mat_medio": "QT_MAT_MED",
    "mat_eja": "QT_MAT_EJA",
    "mat_eja_fundamental": "QT_MAT_EJA_FUND",
    "mat_eja_medio": "QT_MAT_EJA_MED",
    "mat_medio_tecnico_integrado": "QT_MAT_MED_IFTP_CT",
    "mat_profissional_tecnico_concomitante": "QT_MAT_PROF_TEC_CONC",
    "mat_profissional_tecnico_subsequente": "QT_MAT_PROF_TEC_SUBS",
    "mat_profissional_tecnico_iftp_exclusivo": "QT_MAT_PROF_TEC_IFTP_CT",
    "mat_profissional_iftp_qualificacao": "QT_MAT_PROF_IFTP_QP",
    "mat_profissional_fic_concomitante": "QT_MAT_PROF_FIC_CONC",
    "mat_educacao_especial": "QT_MAT_ESP",
    "mat_educacao_especial_classes_comuns": "QT_MAT_ESP_CC",
    "mat_educacao_especial_classes_exclusivas": "QT_MAT_ESP_CE",
}
SUPPLEMENTAL_FIELDS = tuple(field for field in SOURCE_FIELDS if field not in CORE_FIELDS)
PERFORMANCE_FIELDS = {
    "approval": "taxa_aprovacao",
    "failure": "taxa_reprovacao",
    "dropout": "taxa_abandono",
}
PERFORMANCE_STAGES = {
    "elementary": "fundamental",
    "initialYears": "fundamental_anos_iniciais",
    "finalYears": "fundamental_anos_finais",
    "highSchool": "medio",
}
AUDIT_FIELDS = (
    "qntd_escolas",
    "mat_medio",
    "mat_eja",
    "mat_profissional",
    "docentes_basico",
    "turmas_basico",
)
RESOLVED_STATES = {"observed", "derived_zero"}


def _require_text_municipality_id(value: object, *, source: str) -> str:
    if not isinstance(value, str) or re.fullmatch(r"\d{7}", value) is None:
        raise ValueError(
            f"{source}: código IBGE municipal deve permanecer texto com sete dígitos."
        )
    return value


def _is_nullish(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float):
        return math.isnan(value) or math.isinf(value)
    return False


def _number(value: Any) -> float | int | None:
    if _is_nullish(value):
        return None
    if isinstance(value, bool):
        raise ValueError("Valores de matrícula não podem ser booleanos.")
    numeric = float(value)
    if not math.isfinite(numeric):
        return None
    return int(numeric) if numeric.is_integer() else numeric


def _unavailable_value(year: int, field: str) -> dict[str, Any]:
    return {
        "value": None,
        "state": "unavailable",
        "year": year,
        "sourceId": SOURCE_ID,
        "sourceField": SOURCE_FIELDS.get(field, field),
    }


def _direct_value(values: Mapping[str, Any], year: int, field: str) -> dict[str, Any]:
    numeric = _number(values.get(field))
    if numeric is None:
        return _unavailable_value(year, field)
    if numeric < 0:
        raise ValueError(f"{field} não pode conter valor negativo.")
    return {
        "value": numeric,
        "state": "observed",
        "year": year,
        "sourceId": SOURCE_ID,
        "sourceField": SOURCE_FIELDS[field],
    }


def _performance_value(value: Any, year: int, field: str, *, not_applicable: bool = False) -> dict[str, Any]:
    numeric = _number(value)
    if not_applicable:
        return {
            "value": None,
            "state": "not_applicable",
            "year": year,
            "sourceId": PERFORMANCE_SOURCE_ID,
            "sourceField": PERFORMANCE_FIELDS[field],
        }
    if numeric is None:
        return {
            "value": None,
            "state": "unavailable",
            "year": year,
            "sourceId": PERFORMANCE_SOURCE_ID,
            "sourceField": PERFORMANCE_FIELDS[field],
        }
    if numeric < 0 or numeric > 100:
        raise ValueError(f"Taxa de rendimento fora do intervalo em {field}.")
    return {
        "value": numeric,
        "state": "observed",
        "year": year,
        "sourceId": PERFORMANCE_SOURCE_ID,
        "sourceField": PERFORMANCE_FIELDS[field],
    }


def _derived_zero_value(year: int, field: str) -> dict[str, Any]:
    return {
        "value": 0,
        "state": "derived_zero",
        "year": year,
        "sourceId": SOURCE_ID,
        "sourceField": SOURCE_FIELDS.get(field, field),
    }


def _has_all_core_fields_null(row: Mapping[str, Any]) -> bool:
    return all(_is_nullish(row.get(field)) for field in CORE_FIELDS)


def _observed_value(
    rows: Sequence[Mapping[str, Any]],
    year: int,
    field: str,
    *,
    ignore_fully_null_rows: bool = False,
) -> dict[str, Any]:
    relevant_rows = [
        row for row in rows
        if not (ignore_fully_null_rows and _has_all_core_fields_null(row))
    ]
    values = [_number(row.get(field)) for row in relevant_rows]
    if not relevant_rows or any(value is None for value in values):
        return _unavailable_value(year, field)
    return {
        "value": sum(value for value in values if value is not None),
        "state": "observed",
        "year": year,
        "sourceId": SOURCE_ID,
        "sourceField": SOURCE_FIELDS[field],
    }


def _derived_value(values: Sequence[Mapping[str, Any]], year: int, label: str) -> dict[str, Any]:
    if any(value["state"] not in RESOLVED_STATES for value in values):
        return _unavailable_value(year, label)
    total = sum(value["value"] for value in values)
    if total == 0 and all(value["state"] == "derived_zero" for value in values):
        return _derived_zero_value(year, label)
    return {
        "value": total,
        "state": "observed",
        "year": year,
        "sourceId": SOURCE_ID,
        "sourceField": label,
    }


def _percentage(numerator: Mapping[str, Any], denominator: Mapping[str, Any], year: int) -> dict[str, Any]:
    numerator_value = numerator["value"] if numerator["state"] in RESOLVED_STATES else None
    denominator_value = denominator["value"] if denominator["state"] in RESOLVED_STATES else None
    if numerator_value is None or denominator_value is None:
        return {
            "value": None,
            "numerator": numerator_value,
            "denominator": denominator_value,
            "state": "unavailable",
            "year": year,
            "sourceId": SOURCE_ID,
        }
    if denominator_value == 0:
        return {
            "value": None,
            "numerator": numerator_value,
            "denominator": denominator_value,
            "state": "not_applicable",
            "year": year,
            "sourceId": SOURCE_ID,
        }
    return {
        "value": numerator_value / denominator_value * 100,
        "numerator": numerator_value,
        "denominator": denominator_value,
        "state": "derived_zero" if numerator["state"] == "derived_zero" else "observed",
        "year": year,
        "sourceId": SOURCE_ID,
    }


def _breakdown(value: Mapping[str, Any], total: Mapping[str, Any], year: int) -> dict[str, Any]:
    return {"enrollments": dict(value), "share": _percentage(value, total, year)}


def _comparison_value(
    value_2015: Mapping[str, Any], value_2025: Mapping[str, Any]
) -> dict[str, Any]:
    resolved_2015 = value_2015["state"] in RESOLVED_STATES
    resolved_2025 = value_2025["state"] in RESOLVED_STATES
    first = value_2015["value"] if resolved_2015 else None
    last = value_2025["value"] if resolved_2025 else None
    if not resolved_2015 or not resolved_2025:
        state = "unavailable"
        percentage = None
    elif first == 0:
        state = "not_applicable"
        percentage = None
    else:
        state = "observed"
        percentage = (last - first) / first * 100
    return {
        "value2015": dict(value_2015),
        "value2025": dict(value_2025),
        "absoluteChange": None if first is None or last is None else last - first,
        "percentageChange": {
            "value": percentage,
            "numerator": None if first is None or last is None else last - first,
            "denominator": first,
            "state": state,
            "year": REFERENCE_YEAR,
            "sourceId": SOURCE_ID,
        },
    }


def _historical_stage_comparison(
    stage_2015: Mapping[str, Any], stage_2025: Mapping[str, Any]
) -> dict[str, Any]:
    result = {"total": _comparison_value(stage_2015["total"], stage_2025["total"])}
    result["byNetwork"] = {
        key: _comparison_value(
            stage_2015["byNetwork"][key]["enrollments"],
            stage_2025["byNetwork"][key]["enrollments"],
        )
        for key in ("publicSubtotal", "municipal", "state", "federal", "private")
    }
    result["bySchoolLocation"] = {
        key: _comparison_value(
            stage_2015["bySchoolLocation"][key]["enrollments"],
            stage_2025["bySchoolLocation"][key]["enrollments"],
        )
        for key in ("urban", "rural")
    }
    return result


def _duplicate_grains(rows: Iterable[Mapping[str, Any]]) -> list[tuple[int, str, str]]:
    seen: set[tuple[int, str, str]] = set()
    duplicates: list[tuple[int, str, str]] = []
    for row in rows:
        key = (int(row["ano"]), str(row["dependencia"]), str(row["localizacao"]))
        if key in seen:
            duplicates.append(key)
        seen.add(key)
    return duplicates


def build_year_completeness_evidence(
    rows: Iterable[Mapping[str, Any]],
    year: int,
    expected_municipality_ids: Iterable[str],
) -> dict[str, Any]:
    """Formaliza a evidência global exigida para inferir zeros em um ano."""
    expected_ids = frozenset(
        _require_text_municipality_id(identifier, source="universo esperado")
        for identifier in expected_municipality_ids
    )
    if not expected_ids:
        raise ValueError("O universo esperado deve conter municípios.")
    selected_rows = [dict(row) for row in rows if int(row["ano"]) == year]
    municipality_ids = {
        _require_text_municipality_id(
            row.get("id_municipio"), source=f"completude de {year}"
        )
        for row in selected_rows
    }
    grain_seen: set[tuple[str, str, str]] = set()
    duplicate_count = 0
    invalid_domain_count = 0
    negative_count = 0
    for row in selected_rows:
        grain = (
            _require_text_municipality_id(
                row.get("id_municipio"), source=f"completude de {year}"
            ),
            str(row.get("dependencia")),
            str(row.get("localizacao")),
        )
        if grain in grain_seen:
            duplicate_count += 1
        grain_seen.add(grain)
        if row.get("dependencia") not in NETWORKS or row.get("localizacao") not in LOCATIONS:
            invalid_domain_count += 1
        negative_count += sum(
            1
            for field in VALIDATED_FIELDS
            if _number(row.get(field)) is not None and _number(row.get(field)) < 0
        )

    annual_load_present = bool(selected_rows) and municipality_ids == expected_ids
    return {
        "referenceYear": year,
        "expectedMunicipalities": len(expected_ids),
        "municipalitiesPresent": len(municipality_ids),
        "annualLoadPresent": annual_load_present,
        "validDependencyDomain": invalid_domain_count == 0,
        "validSchoolLocationDomain": invalid_domain_count == 0,
        "duplicateGrainCount": duplicate_count,
        "negativeValueCount": negative_count,
        "isCompleteForDerivedZero": (
            annual_load_present
            and invalid_domain_count == 0
            and duplicate_count == 0
            and negative_count == 0
        ),
    }


def build_2025_completeness_evidence(
    rows: Iterable[Mapping[str, Any]],
    expected_municipality_ids: Iterable[str],
) -> dict[str, Any]:
    return build_year_completeness_evidence(
        rows,
        REFERENCE_YEAR,
        expected_municipality_ids,
    )


def audit_fully_null_rows(rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Caracteriza linhas em que os sete campos centrais são simultaneamente NULL."""
    groups: dict[tuple[int, str, str, str], list[Mapping[str, Any]]] = defaultdict(list)
    municipality_years: dict[tuple[int, str], list[Mapping[str, Any]]] = defaultdict(list)

    rows_list = list(rows)
    for row in rows_list:
        municipality_id = _require_text_municipality_id(
            row.get("id_municipio"), source="auditoria de nulos"
        )
        municipality_years[(int(row["ano"]), municipality_id)].append(row)
        if all(_is_nullish(row.get(field)) for field in CORE_FIELDS):
            key = (
                int(row["ano"]),
                municipality_id,
                str(row.get("dependencia")),
                str(row.get("localizacao")),
            )
            groups[key].append(row)

    by_grain = []
    for (year, municipality_id, network, location), grouped_rows in sorted(groups.items()):
        other_populated = sorted(
            field
            for field in AUDIT_FIELDS
            if any(not _is_nullish(row.get(field)) for row in grouped_rows)
        )
        by_grain.append(
            {
                "year": year,
                "idMunicipality": municipality_id,
                "dependency": network,
                "schoolLocation": location,
                "rowCount": len(grouped_rows),
                "otherEducationalFieldsPopulated": other_populated,
            }
        )

    all_null_municipality_years = [
        {"year": year, "idMunicipality": municipality_id}
        for (year, municipality_id), grouped_rows in sorted(municipality_years.items())
        if grouped_rows
        and all(
            all(_is_nullish(row.get(field)) for field in CORE_FIELDS)
            for row in grouped_rows
        )
    ]
    affected_municipality_years = {(item["year"], item["idMunicipality"]) for item in by_grain}

    return {
        "totalRows": sum(item["rowCount"] for item in by_grain),
        "affectedYears": sorted({item["year"] for item in by_grain}),
        "affectedMunicipalities": len({item["idMunicipality"] for item in by_grain}),
        "affectedMunicipalityYears": len(affected_municipality_years),
        "byGrain": by_grain,
        "municipalityYearsAllCoreNull": all_null_municipality_years,
    }


def _can_derive_zero(
    rows: Sequence[Mapping[str, Any]],
    total: Mapping[str, Any],
    completeness: Mapping[str, Any],
) -> bool:
    return (
        not rows
        and total["state"] == "observed"
        and bool(completeness.get("isCompleteForDerivedZero"))
    )


def _zero_value_is_derivable(
    value: Mapping[str, Any],
    total: Mapping[str, Any],
    completeness: Mapping[str, Any],
) -> bool:
    return (
        value["state"] == "observed"
        and value["value"] == 0
        and total["state"] == "observed"
        and bool(completeness.get("isCompleteForDerivedZero"))
    )


def _network_breakdown(
    rows: Sequence[Mapping[str, Any]],
    year: int,
    field: str,
    total: Mapping[str, Any],
    completeness: Mapping[str, Any],
) -> dict[str, Any]:
    values = {}
    for network in NETWORKS:
        network_rows = [row for row in rows if row["dependencia"] == network]
        observed_value = _observed_value(network_rows, year, field)
        values[network] = (
            _derived_zero_value(year, field)
            if (
                _can_derive_zero(network_rows, total, completeness)
                or _zero_value_is_derivable(observed_value, total, completeness)
            )
            else observed_value
        )
    public_subtotal = _derived_value(
        [values["municipal"], values["estadual"], values["federal"]],
        year,
        "derived:municipal+estadual+federal",
    )
    return {
        "publicSubtotal": _breakdown(public_subtotal, total, year),
        "municipal": _breakdown(values["municipal"], total, year),
        "state": _breakdown(values["estadual"], total, year),
        "federal": _breakdown(values["federal"], total, year),
        "private": _breakdown(values["privada"], total, year),
    }


def _location_breakdown(
    rows: Sequence[Mapping[str, Any]],
    year: int,
    field: str,
    total: Mapping[str, Any],
    completeness: Mapping[str, Any],
) -> dict[str, Any]:
    values = {}
    for location in LOCATIONS:
        location_rows = [row for row in rows if row["localizacao"] == location]
        observed_value = _observed_value(location_rows, year, field)
        values[location] = (
            _derived_zero_value(year, field)
            if (
                _can_derive_zero(location_rows, total, completeness)
                or _zero_value_is_derivable(observed_value, total, completeness)
            )
            else observed_value
        )
    return {
        "urban": _breakdown(values["urbana"], total, year),
        "rural": _breakdown(values["rural"], total, year),
    }


def _stage(
    rows: Sequence[Mapping[str, Any]],
    year: int,
    field: str,
    basic_total: Mapping[str, Any],
    completeness: Mapping[str, Any],
    parent_total: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    total = _observed_value(rows, year, field, ignore_fully_null_rows=True)
    payload = {
        "total": total,
        "shareOfBasicEducation": _percentage(total, basic_total, year),
        "byNetwork": _network_breakdown(rows, year, field, total, completeness),
        "bySchoolLocation": _location_breakdown(rows, year, field, total, completeness),
    }
    if parent_total is not None:
        payload["shareOfParentStage"] = _percentage(total, parent_total, year)
    return payload


def _reconciliation(
    identifier: str,
    label: str,
    expected: Mapping[str, Any],
    observed: Mapping[str, Any],
) -> dict[str, Any]:
    if expected["state"] not in RESOLVED_STATES or observed["state"] not in RESOLVED_STATES:
        return {
            "id": identifier,
            "label": label,
            "expected": None,
            "observed": None,
            "difference": None,
            "status": "not_evaluated",
        }
    difference = observed["value"] - expected["value"]
    return {
        "id": identifier,
        "label": label,
        "expected": expected["value"],
        "observed": observed["value"],
        "difference": difference,
        "status": "reconciled" if difference == 0 else "divergent",
    }


def _sum_values(values: Sequence[Mapping[str, Any]], year: int, label: str) -> dict[str, Any]:
    return _derived_value(values, year, label)


def materialize_municipal_education_overview(
    rows: Iterable[Mapping[str, Any]],
    municipality: Mapping[str, str],
    generated_at: str,
    completeness: Mapping[str, Any] | None = None,
    comparison_completeness: Mapping[str, Any] | None = None,
    supplemental: Mapping[str, Any] | None = None,
    performance_rows: Iterable[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Produz um contrato municipal sem efeitos de escrita.

    O contrato é um snapshot exclusivo de 2025. Linhas com os sete campos
    centrais nulos não viram zero: elas deixam indisponível apenas o recorte
    de rede/localização correspondente, desde que os totais municipais possam
    ser agregados a partir das demais linhas observadas.
    """
    source_rows = [dict(row) for row in rows]
    supplemental_values = dict(supplemental or {})
    performance_source_rows = [dict(row) for row in (performance_rows or [])]
    completeness_evidence = dict(completeness or {
        "referenceYear": REFERENCE_YEAR,
        "expectedMunicipalities": 0,
        "municipalitiesPresent": 0,
        "annualLoadPresent": False,
        "validDependencyDomain": False,
        "validSchoolLocationDomain": False,
        "duplicateGrainCount": 0,
        "negativeValueCount": 0,
        "isCompleteForDerivedZero": False,
    })
    required_municipality_keys = {"idMunicipality", "name", "slug"}
    missing_municipality_keys = required_municipality_keys - set(municipality)
    if missing_municipality_keys:
        raise ValueError(f"Município sem chaves: {sorted(missing_municipality_keys)}")

    municipality_id = _require_text_municipality_id(
        municipality["idMunicipality"], source="contrato municipal"
    )
    if any(
        _require_text_municipality_id(
            row.get("id_municipio"), source="linhas da visão geral"
        )
        != municipality_id
        for row in source_rows
    ):
        raise ValueError("As linhas de origem devem pertencer a um único município.")
    if any(
        "id_municipio" in row
        and _require_text_municipality_id(
            row.get("id_municipio"), source="linhas de desempenho"
        )
        != municipality_id
        for row in performance_source_rows
    ):
        raise ValueError("As linhas de desempenho devem pertencer ao município.")
    if any(row.get("dependencia") not in NETWORKS for row in source_rows):
        raise ValueError("Dependência administrativa fora do contrato VGM-1.")
    if any(row.get("localizacao") not in LOCATIONS for row in source_rows):
        raise ValueError("Localização da escola fora do contrato VGM-1.")

    selected_rows = [row for row in source_rows if int(row["ano"]) == REFERENCE_YEAR]
    comparison_rows = [row for row in source_rows if int(row["ano"]) == COMPARISON_YEAR]
    duplicate_grains = _duplicate_grains(selected_rows)
    audit = audit_fully_null_rows(source_rows)
    negative_fields = [
        field
        for row in selected_rows
        for field in VALIDATED_FIELDS
        if (_number(row.get(field)) is not None and _number(row.get(field)) < 0)
    ]
    basic_total = _observed_value(
        selected_rows, REFERENCE_YEAR, "mat_basico", ignore_fully_null_rows=True
    )
    early_total = _stage(
        selected_rows, REFERENCE_YEAR, "mat_infantil", basic_total, completeness_evidence
    )
    creche = _stage(
        selected_rows,
        REFERENCE_YEAR,
        "mat_infantil_creche",
        basic_total,
        completeness_evidence,
        early_total["total"],
    )
    pre_school = _stage(
        selected_rows,
        REFERENCE_YEAR,
        "mat_infantil_pre",
        basic_total,
        completeness_evidence,
        early_total["total"],
    )
    elementary_total = _stage(
        selected_rows, REFERENCE_YEAR, "mat_fundamental", basic_total, completeness_evidence
    )
    initial_years = _stage(
        selected_rows,
        REFERENCE_YEAR,
        "mat_fundamental_anos_iniciais",
        basic_total,
        completeness_evidence,
        elementary_total["total"],
    )
    final_years = _stage(
        selected_rows,
        REFERENCE_YEAR,
        "mat_fundamental_anos_finais",
        basic_total,
        completeness_evidence,
        elementary_total["total"],
    )

    high_school = _stage(
        selected_rows, REFERENCE_YEAR, "mat_medio", basic_total, completeness_evidence
    )
    eja_stage = _stage(
        selected_rows, REFERENCE_YEAR, "mat_eja", basic_total, completeness_evidence
    )
    eja_total = _direct_value(supplemental_values, REFERENCE_YEAR, "mat_eja")
    eja_elementary = _direct_value(supplemental_values, REFERENCE_YEAR, "mat_eja_fundamental")
    eja_high_school = _direct_value(supplemental_values, REFERENCE_YEAR, "mat_eja_medio")
    integrated_technical = _direct_value(
        supplemental_values, REFERENCE_YEAR, "mat_medio_tecnico_integrado"
    )
    concomitant = _direct_value(
        supplemental_values, REFERENCE_YEAR, "mat_profissional_tecnico_concomitante"
    )
    subsequent = _direct_value(
        supplemental_values, REFERENCE_YEAR, "mat_profissional_tecnico_subsequente"
    )
    other_professional_components = [
        _direct_value(supplemental_values, REFERENCE_YEAR, field)
        for field in (
            "mat_profissional_tecnico_iftp_exclusivo",
            "mat_profissional_iftp_qualificacao",
            "mat_profissional_fic_concomitante",
        )
    ]
    other_professional = _sum_values(
        other_professional_components,
        REFERENCE_YEAR,
        "derived:QT_MAT_PROF_TEC_IFTP_CT+QT_MAT_PROF_IFTP_QP+QT_MAT_PROF_FIC_CONC",
    )
    professional_other_offers = _sum_values(
        [concomitant, subsequent, other_professional],
        REFERENCE_YEAR,
        "derived:QT_MAT_PROF_TEC_CONC+QT_MAT_PROF_TEC_SUBS+QT_MAT_PROF_TEC_IFTP_CT+QT_MAT_PROF_IFTP_QP+QT_MAT_PROF_FIC_CONC",
    )
    special_total = _direct_value(
        supplemental_values, REFERENCE_YEAR, "mat_educacao_especial"
    )
    special_common = _direct_value(
        supplemental_values, REFERENCE_YEAR, "mat_educacao_especial_classes_comuns"
    )
    special_exclusive = _direct_value(
        supplemental_values, REFERENCE_YEAR, "mat_educacao_especial_classes_exclusivas"
    )

    comparison_completeness = dict(comparison_completeness or {
        "referenceYear": COMPARISON_YEAR,
        "isCompleteForDerivedZero": False,
    })
    basic_2015 = _observed_value(
        comparison_rows, COMPARISON_YEAR, "mat_basico", ignore_fully_null_rows=True
    )
    historical_2015 = {
        "earlyChildhood": _stage(comparison_rows, COMPARISON_YEAR, "mat_infantil", basic_2015, comparison_completeness),
        "creche": _stage(comparison_rows, COMPARISON_YEAR, "mat_infantil_creche", basic_2015, comparison_completeness),
        "preSchool": _stage(comparison_rows, COMPARISON_YEAR, "mat_infantil_pre", basic_2015, comparison_completeness),
        "elementary": _stage(comparison_rows, COMPARISON_YEAR, "mat_fundamental", basic_2015, comparison_completeness),
        "initialYears": _stage(comparison_rows, COMPARISON_YEAR, "mat_fundamental_anos_iniciais", basic_2015, comparison_completeness),
        "finalYears": _stage(comparison_rows, COMPARISON_YEAR, "mat_fundamental_anos_finais", basic_2015, comparison_completeness),
        "highSchool": _stage(comparison_rows, COMPARISON_YEAR, "mat_medio", basic_2015, comparison_completeness),
        "youthAndAdultEducation": _stage(comparison_rows, COMPARISON_YEAR, "mat_eja", basic_2015, comparison_completeness),
    }
    historical_2025 = {
        "earlyChildhood": early_total,
        "creche": creche,
        "preSchool": pre_school,
        "elementary": elementary_total,
        "initialYears": initial_years,
        "finalYears": final_years,
        "highSchool": high_school,
        "youthAndAdultEducation": eja_stage,
    }
    enrollment_comparison = {
        "years": [COMPARISON_YEAR, REFERENCE_YEAR],
        "stages": {
            "basicEducation": {"total": _comparison_value(basic_2015, basic_total)},
            **{
                key: _historical_stage_comparison(historical_2015[key], historical_2025[key])
                for key in historical_2015
            },
        },
        "methodologyNote": (
            "A variação é (matrículas de 2025 − matrículas de 2015) / matrículas de 2015 × 100. "
            "Base zero em 2015 e valores indisponíveis não produzem taxa."
        ),
    }

    composition_sum = _sum_values(
        [
            early_total["total"],
            elementary_total["total"],
            high_school["total"],
            eja_total,
            professional_other_offers,
        ],
        REFERENCE_YEAR,
        "derived:composicao_educacao_basica",
    )

    performance_by_stage = {
        str(row.get("etapa_ensino")): row
        for row in performance_source_rows
        if int(row.get("ano", REFERENCE_YEAR)) == REFERENCE_YEAR
    }
    school_performance: dict[str, Any] = {
        "referenceYear": REFERENCE_YEAR,
        "stages": {},
        "sourceId": PERFORMANCE_SOURCE_ID,
    }
    for public_stage, source_stage in PERFORMANCE_STAGES.items():
        row = performance_by_stage.get(source_stage)
        not_applicable = (
            public_stage == "highSchool"
            and high_school["total"]["state"] in RESOLVED_STATES
            and high_school["total"]["value"] == 0
        )
        school_performance["stages"][public_stage] = {
            field: _performance_value(
                None if row is None else row.get(source_field),
                REFERENCE_YEAR,
                field,
                not_applicable=not_applicable,
            )
            for field, source_field in PERFORMANCE_FIELDS.items()
        }
    performance_checks = []
    for stage, values in school_performance["stages"].items():
        rates = list(values.values())
        if any(rate["state"] != "observed" for rate in rates):
            performance_checks.append(
                {"stage": stage, "sum": None, "difference": None, "status": "not_evaluated"}
            )
            continue
        rate_sum = sum(rate["value"] for rate in rates)
        difference = rate_sum - 100
        performance_checks.append(
            {
                "stage": stage,
                "sum": rate_sum,
                "difference": difference,
                "status": "reconciled" if abs(difference) <= 0.11 else "divergent",
            }
        )

    reconciliations = [
        _reconciliation(
            "early_childhood_substages",
            "Creche + pré-escola = Educação Infantil",
            early_total["total"],
            _sum_values([creche["total"], pre_school["total"]], REFERENCE_YEAR, "derived:creche+pre_escola"),
        ),
        _reconciliation(
            "elementary_substages",
            "Anos iniciais + anos finais = Ensino Fundamental",
            elementary_total["total"],
            _sum_values([initial_years["total"], final_years["total"]], REFERENCE_YEAR, "derived:anos_iniciais+anos_finais"),
        ),
        _reconciliation(
            "eja_substages",
            "EJA Fundamental + EJA Médio = EJA",
            eja_total,
            _sum_values([eja_elementary, eja_high_school], REFERENCE_YEAR, "derived:eja_fundamental+eja_medio"),
        ),
        _reconciliation(
            "special_education_classes",
            "Classes comuns + classes exclusivas = Educação Especial",
            special_total,
            _sum_values([special_common, special_exclusive], REFERENCE_YEAR, "derived:classes_comuns+classes_exclusivas"),
        ),
        _reconciliation(
            "basic_education_composition",
            "Cinco componentes aditivos = Educação Básica",
            basic_total,
            composition_sum,
        ),
    ]

    stage_reconciliations = (
        ("early_childhood", early_total),
        ("creche", creche),
        ("pre_school", pre_school),
        ("elementary", elementary_total),
        ("initial_years", initial_years),
        ("final_years", final_years),
        ("high_school", high_school),
    )
    for stage_id, stage in stage_reconciliations:
        network = stage["byNetwork"]
        location = stage["bySchoolLocation"]
        reconciliations.extend(
            [
                _reconciliation(
                    f"{stage_id}_public_subtotal",
                    "Municipal + estadual + federal = subtotal público",
                    network["publicSubtotal"]["enrollments"],
                    _sum_values(
                        [
                            network["municipal"]["enrollments"],
                            network["state"]["enrollments"],
                            network["federal"]["enrollments"],
                        ],
                        REFERENCE_YEAR,
                        "derived:municipal+estadual+federal",
                    ),
                ),
                _reconciliation(
                    f"{stage_id}_network_total",
                    "Subtotal público + privada = total da etapa",
                    stage["total"],
                    _sum_values(
                        [
                            network["publicSubtotal"]["enrollments"],
                            network["private"]["enrollments"],
                        ],
                        REFERENCE_YEAR,
                        "derived:publica+privada",
                    ),
                ),
                _reconciliation(
                    f"{stage_id}_location_total",
                    "Urbana + rural = total da etapa",
                    stage["total"],
                    _sum_values(
                        [location["urban"]["enrollments"], location["rural"]["enrollments"]],
                        REFERENCE_YEAR,
                        "derived:urbana+rural",
                    ),
                ),
            ]
        )

    central_values = [
        basic_total,
        early_total["total"],
        creche["total"],
        pre_school["total"],
        elementary_total["total"],
        initial_years["total"],
        final_years["total"],
        high_school["total"],
        eja_total,
        eja_elementary,
        eja_high_school,
        integrated_technical,
        professional_other_offers,
        concomitant,
        subsequent,
        other_professional,
        special_total,
        special_common,
        special_exclusive,
    ]
    central_available = all(value["state"] == "observed" for value in central_values)
    central_reconciliation_failed = any(
        reconciliation["status"] == "divergent" for reconciliation in reconciliations
        if reconciliation["id"] in {
            "early_childhood_substages",
            "elementary_substages",
            "eja_substages",
            "special_education_classes",
            "basic_education_composition",
        }
    )
    reconciliation_failed = any(
        reconciliation["status"] == "divergent" for reconciliation in reconciliations
    )

    secondary_values = [
        stage["byNetwork"][network]["enrollments"]
        for stage in (early_total, creche, pre_school, elementary_total, initial_years, final_years, high_school)
        for network in ("publicSubtotal", "municipal", "state", "federal", "private")
    ] + [
        stage["bySchoolLocation"][location]["enrollments"]
        for stage in (early_total, creche, pre_school, elementary_total, initial_years, final_years, high_school)
        for location in ("urban", "rural")
    ]

    null_core_rows = [
        {
            "year": REFERENCE_YEAR,
            "dependency": item["dependency"],
            "schoolLocation": item["schoolLocation"],
            "rowCount": item["rowCount"],
            "otherEducationalFieldsPopulated": item["otherEducationalFieldsPopulated"],
        }
        for item in audit["byGrain"]
        if item["year"] == REFERENCE_YEAR
    ]

    warnings = []
    if null_core_rows:
        warnings.append(
            "Linhas com os sete totais centrais nulos foram registradas no recorte afetado; elas não foram convertidas em zero nem usadas nos totais municipais."
        )
    if any(value["state"] not in RESOLVED_STATES for value in secondary_values):
        warnings.append(
            "Recortes de rede ou localização sem linha observada permanecem indisponíveis; o materializador não infere zero."
        )
    if duplicate_grains:
        warnings.append("Foram detectadas duplicidades no grão ano + dependência + localização.")
    if negative_fields:
        warnings.append("Foram detectadas matrículas negativas nos campos centrais.")
    if not completeness_evidence.get("isCompleteForDerivedZero"):
        warnings.append(
            "A evidência global de completude de 2025 não permite inferir zeros derivados."
        )
    if any(item["status"] == "divergent" for item in performance_checks):
        warnings.append(
            "Uma ou mais somas das taxas de rendimento divergem de 100% além da tolerância de arredondamento; os valores oficiais foram preservados."
        )

    if duplicate_grains or negative_fields or central_reconciliation_failed or reconciliation_failed:
        publication_state = "invalid"
    elif not central_available:
        publication_state = "unavailable"
    elif any(value["state"] not in RESOLVED_STATES for value in secondary_values):
        publication_state = "partial"
    else:
        publication_state = "published"

    methodology = [
        "O snapshot usa exclusivamente o ano de 2025; não há seleção dinâmica nem fallback anual.",
        "Educação Básica usa QT_MAT_BAS como total oficial e não é recomposta pela soma das etapas.",
        "A base territorial é o município onde a escola está localizada; urbana e rural referem-se à localização da escola.",
        "Subtotais públicos só são derivados quando municipal, estadual e federal estão observados ou com zero derivado; ausências não confirmadas permanecem indisponíveis.",
        "Linhas com os sete campos centrais nulos não aumentam totais e mantêm indisponível apenas o recorte de rede/localização afetado.",
        "Zero derivado exige carga municipal completa de 2025, domínios válidos, ausência de duplicidade/negativos, total da etapa observado e ausência de nullCoreRow no recorte.",
        "Os cinco componentes principais da composição reconciliam com QT_MAT_BAS; detalhamentos internos não são somados novamente.",
        "A Educação Especial é um recorte transversal já incluído nas etapas e modalidades da Educação Básica.",
        "As taxas de rendimento usam os registros municipais do INEP para o conjunto das redes, sem média entre escolas ou dependências.",
    ]

    return {
        "schemaVersion": SCHEMA_VERSION,
        "publicationState": publication_state,
        "municipality": {
            "idMunicipality": municipality_id,
            "name": str(municipality["name"]),
            "slug": str(municipality["slug"]),
        },
        "reference": {"year": REFERENCE_YEAR, "generatedAt": generated_at},
        "universe": {
            "territorialBasis": "school_location",
            "locationLabel": "Localização da escola",
            "basicEducationSourceField": "QT_MAT_BAS",
            "methodologyNotes": methodology,
        },
        "basicEducation": {"total": basic_total},
        "basicEducationComposition": {
            "total": basic_total,
            "components": {
                "earlyChildhood": {
                    "total": early_total["total"],
                    "details": {"creche": creche["total"], "preSchool": pre_school["total"]},
                },
                "elementary": {
                    "total": elementary_total["total"],
                    "details": {"initialYears": initial_years["total"], "finalYears": final_years["total"]},
                },
                "highSchool": {
                    "total": high_school["total"],
                    "details": {"integratedTechnical": integrated_technical},
                },
                "youthAndAdultEducation": {
                    "total": eja_total,
                    "details": {"elementary": eja_elementary, "highSchool": eja_high_school},
                },
                "otherProfessionalOffers": {
                    "total": professional_other_offers,
                    "details": {
                        "concomitantTechnical": concomitant,
                        "subsequentTechnical": subsequent,
                        "otherOffers": other_professional,
                    },
                },
            },
            "reconciliation": next(
                item for item in reconciliations if item["id"] == "basic_education_composition"
            ),
        },
        "specialEducation": {
            "total": special_total,
            "commonClasses": special_common,
            "exclusiveClasses": special_exclusive,
        },
        "highSchool": {
            "total": high_school,
            "integratedTechnical": {
                "total": integrated_technical,
                "shareOfHighSchool": _percentage(
                    integrated_technical, high_school["total"], REFERENCE_YEAR
                ),
            },
        },
        "schoolPerformance": school_performance,
        "enrollmentComparison": enrollment_comparison,
        "earlyChildhood": {"total": early_total, "creche": creche, "preSchool": pre_school},
        "elementary": {"total": elementary_total, "initialYears": initial_years, "finalYears": final_years},
        "sources": [
            {
                "id": f"{SOURCE_ID}_2015",
                "organization": "Instituto Nacional de Estudos e Pesquisas Educacionais Anísio Teixeira (INEP)",
                "title": "Censo Escolar da Educação Básica",
                "referenceYear": COMPARISON_YEAR,
                "url": SOURCE_URL,
            },
            {
                "id": SOURCE_ID,
                "organization": "Instituto Nacional de Estudos e Pesquisas Educacionais Anísio Teixeira (INEP)",
                "title": "Censo Escolar da Educação Básica",
                "referenceYear": REFERENCE_YEAR,
                "url": SOURCE_URL,
            },
            {
                "id": PERFORMANCE_SOURCE_ID,
                "organization": "Instituto Nacional de Estudos e Pesquisas Educacionais Anísio Teixeira (INEP)",
                "title": "Taxas de Rendimento Escolar",
                "referenceYear": REFERENCE_YEAR,
                "url": PERFORMANCE_SOURCE_URL,
            },
        ],
        "methodology": methodology,
        "quality": {
            "reconciliations": reconciliations,
            "semanticWarnings": warnings,
            "nullCoreRows": null_core_rows,
            "completeness": completeness_evidence,
            "schoolPerformanceChecks": performance_checks,
        },
    }


def load_municipal_overview_rows(engine: Any, id_municipio: str) -> list[dict[str, Any]]:
    """Lê a visão VGM-1 para um município; não cria nem escreve contratos."""
    from sqlalchemy import text

    query = text(
        f"""
        SELECT v.ano, v.id_municipio, v.dependencia, v.localizacao,
               v.mat_basico, v.mat_infantil, v.mat_infantil_creche, v.mat_infantil_pre,
               v.mat_fundamental, v.mat_fundamental_anos_iniciais,
               v.mat_fundamental_anos_finais, c.mat_medio
        FROM {VIEW_NAME} AS v
        INNER JOIN censo AS c
          ON c.ano = v.ano
         AND c.id_municipio = v.id_municipio
         AND c.dependencia = v.dependencia
         AND c.localizacao = v.localizacao
        WHERE v.id_municipio::text = :id_municipio
        ORDER BY v.ano, v.dependencia, v.localizacao
        """
    )
    municipality_id = _require_text_municipality_id(
        id_municipio, source="consulta da visão geral"
    )
    with engine.connect() as connection:
        return [
            dict(row)
            for row in connection.execute(
                query, {"id_municipio": municipality_id}
            ).mappings()
        ]
