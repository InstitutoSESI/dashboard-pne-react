"""Leitura offline e resultados homologados da macro-rodada do PNE."""

from __future__ import annotations

from collections.abc import Mapping
import json
import math
from pathlib import Path
from typing import Any

from .pne_macro_ingestion import (
    DATA_ROOT,
    EXPECTED_MUNICIPALITIES,
    NORMALIZED_SCHEMA,
)


MUNIC_CAREER_RELATION_ID = "relation.17.c.munic_planos_carreira_declarados"
MUNIC_FORUM_RELATION_ID = "relation.18.c.munic_forum_educacao_declarado"
CAPES_TITLES_RELATION_ID = "relation.16.a.capes_titulados_oferta_local"
CPC_QUALITY_RELATION_ID = "relation.15.a.cpc_cursos_oferta_local"
ENADE_LIC_RELATION_ID = "relation.17.e.enade_licenciaturas_oferta_local"

MACRO_RELATION_IDS = frozenset(
    {
        MUNIC_CAREER_RELATION_ID,
        MUNIC_FORUM_RELATION_ID,
        CAPES_TITLES_RELATION_ID,
        CPC_QUALITY_RELATION_ID,
        ENADE_LIC_RELATION_ID,
    }
)

SOURCE_PATHS = {
    "ibge_munic_2021": DATA_ROOT / "munic_2021" / "normalized.json",
    "capes_sucupira_2024": DATA_ROOT / "capes_2024" / "normalized.json",
    "inep_quality_offer": DATA_ROOT / "quality_offer" / "normalized.json",
}


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


def load_normalized_source(
    source_id: str,
    path: Path | None = None,
) -> dict[str, Mapping[str, Any]]:
    source_path = path or SOURCE_PATHS[source_id]
    payload = json.loads(source_path.read_text(encoding="utf-8"))
    if payload.get("schemaVersion") != NORMALIZED_SCHEMA:
        raise ValueError(f"{source_id}: schema normalizado inválido.")
    if payload.get("sourceId") != source_id:
        raise ValueError(f"{source_id}: identidade da fonte divergente.")
    records = payload.get("records")
    if (
        not isinstance(records, dict)
        or payload.get("municipalityCount") != EXPECTED_MUNICIPALITIES
        or len(records) != EXPECTED_MUNICIPALITIES
    ):
        raise ValueError(f"{source_id}: cobertura municipal incompleta.")
    for municipality_id, record in records.items():
        if (
            not isinstance(record, Mapping)
            or record.get("municipalityId") != municipality_id
        ):
            raise ValueError(
                f"{source_id}: registro municipal inválido em {municipality_id}."
            )
    return dict(sorted(records.items()))


def load_macro_source_records() -> tuple[
    dict[str, Mapping[str, Any]],
    dict[str, Mapping[str, Any]],
    dict[str, Mapping[str, Any]],
]:
    return (
        load_normalized_source("ibge_munic_2021"),
        load_normalized_source("capes_sucupira_2024"),
        load_normalized_source("inep_quality_offer"),
    )


def municipal_management_results(
    record: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    year = int(record.get("year") or 2021)
    career = record.get("careerPlans") or {}
    teacher = career.get("teacherPlan")
    non_teaching = career.get("nonTeachingPlan")
    if teacher not in {"yes", "no"} or non_teaching not in {"yes", "no"}:
        career_result = _absence(
            year=year,
            status="unavailable",
            reason_code="munic_response_unknown",
        )
    else:
        numerator = int(teacher == "yes") + int(non_teaching == "yes")
        career_result = {
            "dataStatus": "available",
            "year": year,
            "value": numerator,
            "numerator": numerator,
            "denominator": 2,
            "publicReading": (
                f"{numerator} de 2 tipos de plano de carreira foram declarados "
                "na MUNIC 2021: magistério e profissionais não docentes. A "
                "existência declarada não comprova implementação, piso, limite "
                "de 2/3 da jornada ou atendimento integral da Meta 17.c."
            ),
        }

    forum = record.get("educationForum")
    if forum not in {"yes", "no"}:
        forum_result = _absence(
            year=year,
            status="unavailable",
            reason_code="munic_response_unknown",
        )
    else:
        value = int(forum == "yes")
        forum_result = {
            "dataStatus": "available",
            "year": year,
            "value": value,
            "numerator": value,
            "denominator": 1,
            "publicReading": (
                "O município declarou "
                f"{'ter instituído' if value else 'não ter instituído'} Fórum "
                "Permanente de Educação na MUNIC 2021. A resposta não comprova "
                "instituição por lei, permanência ou funcionamento."
            ),
        }
    return {
        MUNIC_CAREER_RELATION_ID: career_result,
        MUNIC_FORUM_RELATION_ID: forum_result,
    }


def capes_titles_result(record: Mapping[str, Any]) -> dict[str, Any]:
    year = int(record.get("year") or 2024)
    program_count = record.get("localProgramCount")
    masters = record.get("mastersAwarded")
    doctors = record.get("doctoratesAwarded")
    title_status = str(record.get("titleDataStatus") or "available")
    if title_status == "suppressed":
        return _absence(
            year=year,
            status="suppressed",
            reason_code="capes_titles_suppressed",
        )
    if (
        title_status != "available"
        or record.get("sourceCoverageStatus", "complete") != "complete"
        or record.get("territorialityStatus", "homologated") != "homologated"
    ):
        return _absence(
            year=year,
            status="unavailable",
            reason_code="capes_source_incomplete_or_territoriality_inconclusive",
        )
    if not all(
        _finite_number(value) and float(value) >= 0
        for value in (masters, doctors)
    ):
        return _absence(
            year=year,
            status="unavailable",
            reason_code="capes_required_component_unknown",
        )
    total = int(masters) + int(doctors)
    if total == 0 and not (
        _finite_number(program_count) and float(program_count) >= 0
    ):
        return _absence(
            year=year,
            status="unavailable",
            reason_code="capes_required_component_unknown",
        )
    if total == 0 and int(program_count) == 0:
        return _absence(
            year=year,
            status="not_applicable",
            reason_code="no_local_stricto_sensu_offer_or_student_record",
        )
    if _finite_number(program_count):
        program_total = int(program_count)
        program_label = "programa" if program_total == 1 else "programas"
        offer_reading = (
            f"em {program_total} {program_label} com sede ou IES vinculada "
            "no município "
        )
    else:
        offer_reading = "na oferta territorialmente homologada no município "
    return {
        "dataStatus": "available",
        "year": year,
        "value": total,
        "numerator": total,
        "denominator": None,
        "publicReading": (
            f"{int(masters)} títulos de mestrado e {int(doctors)} de doutorado "
            f"foram registrados {offer_reading}em {year}. "
            "Em programas em rede, a territorialidade é a da IES à qual o "
            "discente está vinculado, não a sede da instituição principal nem "
            "a residência do titulado. A meta nacional não foi distribuída "
            "entre municípios."
        ),
    }


def _has_local_higher_offer(document: Mapping[str, Any]) -> bool | None:
    indicator = (
        (document.get("indicators") or {}).get("esup-matriculas-total") or {}
    )
    points = [
        point
        for point in indicator.get("series") or []
        if (
            isinstance(point, Mapping)
            and point.get("status") in {"observed", "derived_zero"}
            and _finite_number(point.get("value"))
        )
    ]
    if not points:
        return None
    latest = max(points, key=lambda point: int(point.get("year") or 0))
    return float(latest["value"]) > 0


def _quality_ratio_result(
    component: Mapping[str, Any],
    *,
    year: int,
    label: str,
    limitation: str,
    higher_education: Mapping[str, Any],
) -> dict[str, Any]:
    numerator = component.get("adequateCount")
    denominator = component.get("validCount")
    if not (
        _finite_number(numerator)
        and _finite_number(denominator)
        and float(numerator) >= 0
        and float(denominator) >= 0
        and float(numerator) <= float(denominator)
    ):
        return _absence(
            year=year,
            status="unavailable",
            reason_code="quality_component_unknown",
        )
    if float(denominator) == 0:
        has_offer = _has_local_higher_offer(higher_education)
        if has_offer is False:
            return _absence(
                year=year,
                status="not_applicable",
                reason_code="no_local_higher_education_offer",
            )
        return _absence(
            year=year,
            status="unavailable",
            reason_code=(
                "no_evaluation_in_cycle"
                if has_offer is True
                else "local_offer_status_unknown"
            ),
        )
    value = 100 * float(numerator) / float(denominator)
    return {
        "dataStatus": "available",
        "year": year,
        "value": value,
        "numerator": int(numerator),
        "denominator": int(denominator),
        "publicReading": (
            f"{int(numerator)} de {int(denominator)} {label}. {limitation}"
        ),
    }


def quality_offer_results(
    record: Mapping[str, Any],
    *,
    higher_education: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    cpc = record.get("cpc2023") or {}
    enade = record.get("enadeLicenciaturas2025") or {}
    return {
        CPC_QUALITY_RELATION_ID: _quality_ratio_result(
            cpc,
            year=2023,
            label=(
                "cursos locais com CPC válido obtiveram faixa 3, 4 ou 5 "
                "no ciclo de 2023"
            ),
            limitation=(
                "O recorte é do ciclo avaliado e não representa toda a oferta "
                "de graduação nem cumprimento integral da Meta 15.a."
            ),
            higher_education=higher_education,
        ),
        ENADE_LIC_RELATION_ID: _quality_ratio_result(
            enade,
            year=2025,
            label=(
                "concluintes participantes, em resultados locais não "
                "suprimidos de pedagogia e licenciaturas, alcançaram ou "
                "superaram o Padrão 1 de Proficiência no Enade 2025"
            ),
            limitation=(
                "A unidade é o curso avaliado; o conceito não informa o "
                "percentual individual de concluintes com desempenho adequado "
                "exigido pela Meta 17.e."
            ),
            higher_education=higher_education,
        ),
    }


def build_macro_round_results(
    *,
    municipality_id: str,
    munic_records: Mapping[str, Mapping[str, Any]],
    capes_records: Mapping[str, Mapping[str, Any]],
    quality_records: Mapping[str, Mapping[str, Any]],
    higher_education: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    if not all(
        municipality_id in source
        for source in (munic_records, capes_records, quality_records)
    ):
        raise KeyError(f"Fonte macro sem município {municipality_id}.")
    results = municipal_management_results(munic_records[municipality_id])
    results[CAPES_TITLES_RELATION_ID] = capes_titles_result(
        capes_records[municipality_id]
    )
    results.update(
        quality_offer_results(
            quality_records[municipality_id],
            higher_education=higher_education,
        )
    )
    if set(results) != MACRO_RELATION_IDS:
        raise RuntimeError("Pacote da macro-rodada contém relações inesperadas.")
    return results


__all__ = [
    "CAPES_TITLES_RELATION_ID",
    "CPC_QUALITY_RELATION_ID",
    "ENADE_LIC_RELATION_ID",
    "MACRO_RELATION_IDS",
    "MUNIC_CAREER_RELATION_ID",
    "MUNIC_FORUM_RELATION_ID",
    "SOURCE_PATHS",
    "build_macro_round_results",
    "capes_titles_result",
    "load_macro_source_records",
    "load_normalized_source",
    "municipal_management_results",
    "quality_offer_results",
]
