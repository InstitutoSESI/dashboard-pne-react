"""Materializacao segura dos contratos publicos da Educacao Superior."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import statistics
import tempfile
import time
import uuid
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from .higher_education import (
    DATA_STATUSES,
    REQUIRED_TABLES,
    STATUS_DERIVED_ZERO,
    STATUS_NOT_APPLICABLE,
    STATUS_OBSERVED,
    STATUS_UNAVAILABLE,
    SUPPORTED_YEARS,
    NormalizedRecord,
    ParsedAudit,
    load_municipality_universe,
)


SCHEMA_VERSION = 1
MATERIALIZER_VERSION = "esup-materializer-v1"
MAX_INDEX_BYTES = 100 * 1024
REVIEW_MUNICIPAL_BYTES = 75 * 1024
MAX_MUNICIPAL_BYTES = 150 * 1024
AVAILABILITIES = ("current", "historical_only", "unavailable")


@dataclass(frozen=True)
class IndicatorSpec:
    id: str
    metric: str
    universe: str
    territorial_reference: str
    source_table: str


@dataclass(frozen=True)
class BreakdownSpec:
    id: str
    metric: str
    dimension: str
    universe: str
    territorial_reference: str
    source_table: str
    categories: tuple[tuple[str, str], ...]
    reconciliation_measure: str


INDICATORS = (
    IndicatorSpec(
        "esup-matriculas-total",
        "enrollments_total",
        "graduation",
        "course_offer_location",
        "7.1",
    ),
    IndicatorSpec(
        "esup-matriculas-presenciais",
        "enrollments_presential",
        "presential_graduation",
        "course_offer_location",
        "7.2",
    ),
    IndicatorSpec(
        "esup-matriculas-ead",
        "enrollments_distance",
        "distance_graduation",
        "ead_offer_location",
        "7.3",
    ),
    IndicatorSpec(
        "esup-ies-sede",
        "ies_headquarters",
        "institutions_offering_graduation_or_sequential",
        "ies_administrative_headquarters",
        "1.1",
    ),
    IndicatorSpec(
        "esup-polos-ead",
        "ead_poles",
        "distance_graduation",
        "ead_offer_location",
        "7.3",
    ),
    IndicatorSpec(
        "esup-vagas-presenciais",
        "vacancies_presential",
        "presential_graduation",
        "course_offer_location",
        "7.2",
    ),
    IndicatorSpec(
        "esup-ingressantes",
        "entrants_total",
        "graduation",
        "course_offer_location",
        "7.1",
    ),
    IndicatorSpec(
        "esup-concluintes",
        "graduates_total",
        "graduation",
        "course_offer_location",
        "7.1",
    ),
    IndicatorSpec(
        "esup-docentes",
        "faculty_total",
        "faculty_in_graduation_or_sequential",
        "faculty_institution_headquarters",
        "2.1",
    ),
)

BREAKDOWNS = (
    BreakdownSpec(
        "enrollment_dependency",
        "enrollments_by_dependency",
        "administrative_dependency",
        "graduation",
        "course_offer_location",
        "5.1",
        (
            ("federal", "Federal"),
            ("estadual", "Estadual"),
            ("municipal", "Municipal"),
            ("privada", "Privada"),
        ),
        "enrollment_dependencies",
    ),
    BreakdownSpec(
        "enrollment_organization",
        "enrollments_by_organization",
        "academic_organization",
        "graduation",
        "course_offer_location",
        "5.1",
        (
            ("universidade", "Universidade"),
            ("centro_universitario", "Centro universitário"),
            ("faculdade", "Faculdade"),
            ("instituto_federal_cefet", "Instituto Federal/Cefet"),
        ),
        "enrollment_organizations",
    ),
    BreakdownSpec(
        "ies_dependency",
        "ies_by_dependency",
        "administrative_dependency",
        "institutions_offering_graduation_or_sequential",
        "ies_administrative_headquarters",
        "1.1",
        (
            ("federal", "Federal"),
            ("estadual", "Estadual"),
            ("municipal", "Municipal"),
            ("privada", "Privada"),
        ),
        "ies_dependencies",
    ),
    BreakdownSpec(
        "ies_organization",
        "ies_by_organization",
        "academic_organization",
        "institutions_offering_graduation_or_sequential",
        "ies_administrative_headquarters",
        "1.1",
        (
            ("universidade", "Universidade"),
            ("centro_universitario", "Centro universitário"),
            ("faculdade", "Faculdade"),
            ("instituto_federal_cefet", "Instituto Federal/Cefet"),
        ),
        "ies_organizations",
    ),
    BreakdownSpec(
        "faculty_education",
        "faculty_by_education",
        "faculty_education",
        "faculty_in_graduation_or_sequential",
        "faculty_institution_headquarters",
        "2.3",
        (
            ("Sem Graduação", "Sem graduação"),
            ("Graduação", "Graduação"),
            ("Especialização", "Especialização"),
            ("Mestrado", "Mestrado"),
            ("Doutorado", "Doutorado"),
        ),
        "faculty_education",
    ),
)

SOURCE_TABLES = {
    "1.1": (
        "institutions_offering_graduation_or_sequential",
        "ies_administrative_headquarters",
    ),
    "2.1": (
        "faculty_in_graduation_or_sequential",
        "faculty_institution_headquarters",
    ),
    "2.3": (
        "faculty_in_graduation_or_sequential",
        "faculty_institution_headquarters",
    ),
    "5.1": ("graduation", "course_offer_location"),
    "7.1": ("graduation", "course_offer_location"),
    "7.2": ("presential_graduation", "course_offer_location"),
    "7.3": ("distance_graduation", "ead_offer_location"),
}

FORBIDDEN_KEYS = {
    "courses",
    "cine",
    "shift",
    "academic_degree",
    "sex",
    "race",
    "age",
    "disability",
    "nationality",
    "financing",
    "reserved_vacancies",
    "candidates",
    "admission_forms",
    "academic_status",
    "faculty_regime",
    "ranking",
    "stateComparison",
    "populationCoverage",
    "latestValue",
    "trend",
    "variation",
    "sha256",
    "fileName",
    "firstYear",
    "latestYear",
    "availableYears",
}


def _json_bytes(payload: Mapping) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False) + "\n"
    ).encode("utf-8")


def _source_id(table: str, year: int) -> str:
    return f"s-{table}-{year}"


def _data_version(source_files: Sequence[Mapping]) -> str:
    fingerprint = {
        "schemaVersion": SCHEMA_VERSION,
        "materializerVersion": MATERIALIZER_VERSION,
        "sourceHashes": [
            item["sha256"]
            for item in sorted(source_files, key=lambda source: source["year"])
        ],
    }
    digest = hashlib.sha256(
        json.dumps(
            fingerprint,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    return f"esup-v1-{digest[:20]}"


def _validate_source_files(source_files: Sequence[Mapping]) -> None:
    years = [int(item["year"]) for item in source_files]
    if years != list(SUPPORTED_YEARS):
        raise ValueError(
            f"Fontes da materializacao devem cobrir {SUPPORTED_YEARS}: {years}."
        )
    for item in source_files:
        if set(item.get("tables", ())) != set(REQUIRED_TABLES):
            raise ValueError(
                f"Fonte {item.get('year')} nao contem as sete tabelas aprovadas."
            )
        if not re.fullmatch(r"[0-9a-f]{64}", str(item.get("sha256", ""))):
            raise ValueError(f"SHA-256 invalido na fonte de {item.get('year')}.")
        if Path(str(item.get("fileName", ""))).name != item.get("fileName"):
            raise ValueError("O registro de fonte nao pode conter caminho local.")


def _source_registry(source_files: Sequence[Mapping]) -> dict[str, dict]:
    registry: dict[str, dict] = {}
    by_year = {int(item["year"]): item for item in source_files}
    for year in SUPPORTED_YEARS:
        source = by_year[year]
        for table in REQUIRED_TABLES:
            universe, territory = SOURCE_TABLES[table]
            registry[_source_id(table, year)] = {
                "year": year,
                "table": table,
                "fileName": source["fileName"],
                "sha256": source["sha256"],
                "universe": universe,
                "territorialReference": territory,
            }
    return registry


def _record_indices(
    records: Sequence[NormalizedRecord],
) -> tuple[
    dict[tuple[str, str, int], NormalizedRecord],
    dict[tuple[str, str, int, str], NormalizedRecord],
]:
    direct_metrics = {spec.metric for spec in INDICATORS}
    breakdown_by_metric = {spec.metric: spec for spec in BREAKDOWNS}
    direct: dict[tuple[str, str, int], NormalizedRecord] = {}
    breakdown: dict[tuple[str, str, int, str], NormalizedRecord] = {}
    for record in records:
        if record.metric in direct_metrics:
            key = (record.municipality_id, record.metric, record.year)
            if key in direct:
                raise ValueError(f"Indicador duplicado na materializacao: {key}.")
            direct[key] = record
        elif record.metric in breakdown_by_metric:
            spec = breakdown_by_metric[record.metric]
            category = getattr(record, spec.dimension)
            if category is None:
                raise ValueError(
                    f"Categoria ausente em {record.metric}, "
                    f"{record.municipality_id}/{record.year}."
                )
            key = (
                record.municipality_id,
                record.metric,
                record.year,
                category,
            )
            if key in breakdown:
                raise ValueError(f"Categoria duplicada na materializacao: {key}.")
            breakdown[key] = record
    return direct, breakdown


def _reconciliation_index(quality_report: Mapping) -> dict[tuple[str, int, str], bool]:
    index: dict[tuple[str, int, str], bool] = {}
    for item in quality_report.get("reconciliations", ()):
        if item.get("scope") != "municipality":
            continue
        index[
            (
                str(item["measure"]),
                int(item["year"]),
                str(item["municipalityId"]),
            )
        ] = item.get("status") == "matched"
    return index


def _point_source(record: NormalizedRecord | None, spec: IndicatorSpec, year: int) -> dict:
    if record is None:
        return {"sourceId": None}
    if record.status != STATUS_DERIVED_ZERO:
        return {"sourceId": _source_id(record.source_table, year)}
    other_table = "7.3" if spec.source_table == "7.2" else "7.2"
    return {"sourceIds": [_source_id("7.1", year), _source_id(other_table, year)]}


def _indicator_payload(
    spec: IndicatorSpec,
    municipality_id: str,
    direct: Mapping[tuple[str, str, int], NormalizedRecord],
) -> dict:
    series: list[dict] = []
    for year in SUPPORTED_YEARS:
        record = direct.get((municipality_id, spec.metric, year))
        point = {
            "year": year,
            "value": record.value if record is not None else None,
            "status": record.status if record is not None else STATUS_UNAVAILABLE,
        }
        point.update(_point_source(record, spec, year))
        series.append(point)
    return {
        "id": spec.id,
        "universe": spec.universe,
        "territorialReference": spec.territorial_reference,
        "series": series,
    }


def _breakdown_payload(
    spec: BreakdownSpec,
    municipality_id: str,
    year: int,
    breakdown: Mapping[tuple[str, str, int, str], NormalizedRecord],
    reconciliations: Mapping[tuple[str, int, str], bool],
) -> dict:
    categories: list[dict] = []
    records: list[NormalizedRecord] = []
    for category_id, label in spec.categories:
        record = breakdown.get((municipality_id, spec.metric, year, category_id))
        if record is not None:
            records.append(record)
        categories.append(
            {
                "id": category_id,
                "label": label,
                "value": record.value if record is not None else None,
                "status": (
                    record.status if record is not None else STATUS_UNAVAILABLE
                ),
            }
        )
    status = (
        STATUS_OBSERVED
        if any(record.status == STATUS_OBSERVED for record in records)
        else (
            STATUS_NOT_APPLICABLE
            if any(record.status == STATUS_NOT_APPLICABLE for record in records)
            else STATUS_UNAVAILABLE
        )
    )
    return {
        "id": spec.id,
        "year": year,
        "universe": spec.universe,
        "territorialReference": spec.territorial_reference,
        "exhaustive": reconciliations.get(
            (spec.reconciliation_measure, year, municipality_id),
            False,
        ),
        "status": status,
        "sourceId": _source_id(spec.source_table, year) if records else None,
        "categories": categories,
    }


def _availability(indicators: Mapping[str, Mapping]) -> str:
    useful_years = {
        point["year"]
        for indicator in indicators.values()
        for point in indicator["series"]
        if point["status"] in {STATUS_OBSERVED, STATUS_DERIVED_ZERO}
        and point["value"] is not None
    }
    if max(SUPPORTED_YEARS) in useful_years:
        return "current"
    if useful_years:
        return "historical_only"
    return "unavailable"


def _coverage(
    records: Mapping[tuple[str, str, int], NormalizedRecord],
    spec: IndicatorSpec,
) -> dict[str, int]:
    return {
        str(year): sum(
            1
            for (municipality_id, metric, record_year), record in records.items()
            if metric == spec.metric
            and record_year == year
            and municipality_id
            and record.status in {STATUS_OBSERVED, STATUS_DERIVED_ZERO}
            and record.value is not None
        )
        for year in SUPPORTED_YEARS
    }


def _breakdown_coverage(
    records: Mapping[tuple[str, str, int, str], NormalizedRecord],
    spec: BreakdownSpec,
) -> dict[str, int]:
    return {
        str(year): len(
            {
                municipality_id
                for (
                    municipality_id,
                    metric,
                    record_year,
                    _category,
                ), record in records.items()
                if metric == spec.metric
                and record_year == year
                and record.status in {STATUS_OBSERVED, STATUS_DERIVED_ZERO}
                and record.value is not None
            }
        )
        for year in SUPPORTED_YEARS
    }


def build_public_contracts(
    audit: ParsedAudit,
    municipality_universe: Mapping[str, str],
) -> tuple[dict, dict[str, dict]]:
    if len(municipality_universe) != 497:
        raise ValueError("A materializacao exige exatamente 497 municipios.")
    _validate_source_files(audit.source_files)
    for record in audit.records:
        if record.year not in SUPPORTED_YEARS:
            raise ValueError(f"Ano fora do contrato: {record.year}.")
        if record.municipality_id not in municipality_universe:
            raise ValueError(
                f"Municipio fora do universo: {record.municipality_id}."
            )
    direct, breakdown = _record_indices(audit.records)
    reconciliations = _reconciliation_index(audit.quality_report)
    sources = _source_registry(audit.source_files)

    indicator_catalog = [
        {
            "id": spec.id,
            "universe": spec.universe,
            "territorialReference": spec.territorial_reference,
            "sourceTable": spec.source_table,
            "coverageByYear": _coverage(direct, spec),
        }
        for spec in INDICATORS
    ]
    breakdown_catalog = [
        {
            "id": spec.id,
            "universe": spec.universe,
            "territorialReference": spec.territorial_reference,
            "sourceTable": spec.source_table,
            "categories": [
                {"id": category_id, "label": label}
                for category_id, label in spec.categories
            ],
            "coverageByYear": _breakdown_coverage(breakdown, spec),
        }
        for spec in BREAKDOWNS
    ]
    manifest = {
        "schemaVersion": SCHEMA_VERSION,
        "dataVersion": _data_version(audit.source_files),
        "firstYear": min(SUPPORTED_YEARS),
        "latestYear": max(SUPPORTED_YEARS),
        "availableYears": list(SUPPORTED_YEARS),
        "municipalityCount": 497,
        "indicators": indicator_catalog,
        "breakdowns": breakdown_catalog,
        "sources": sources,
    }

    municipalities: dict[str, dict] = {}
    for municipality_id, municipality in sorted(municipality_universe.items()):
        indicators = {
            spec.id: _indicator_payload(spec, municipality_id, direct)
            for spec in INDICATORS
        }
        breakdowns = [
            _breakdown_payload(
                spec,
                municipality_id,
                year,
                breakdown,
                reconciliations,
            )
            for spec in sorted(BREAKDOWNS, key=lambda item: item.id)
            for year in SUPPORTED_YEARS
        ]
        municipalities[municipality_id] = {
            "schemaVersion": SCHEMA_VERSION,
            "municipality": {
                "id": municipality_id,
                "name": municipality,
            },
            "availability": _availability(indicators),
            "indicators": indicators,
            "breakdowns": breakdowns,
        }
    return manifest, municipalities


def write_public_contracts(
    directory: Path,
    manifest: Mapping,
    municipalities: Mapping[str, Mapping],
) -> None:
    if directory.exists() and any(directory.iterdir()):
        raise ValueError(f"Diretorio de staging nao esta vazio: {directory}.")
    directory.mkdir(parents=True, exist_ok=True)
    municipality_directory = directory / "municipios"
    municipality_directory.mkdir()
    (directory / "index.json").write_bytes(_json_bytes(manifest))
    for municipality_id, payload in sorted(municipalities.items()):
        (municipality_directory / f"{municipality_id}.json").write_bytes(
            _json_bytes(payload)
        )


def _walk_keys(value) -> Iterable[str]:
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from _walk_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_keys(child)


def _walk_strings(value) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from _walk_strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_strings(child)


def _validate_point(point: Mapping, source_ids: set[str], available_years: set[int]) -> None:
    if point.get("year") not in available_years:
        raise ValueError(f"Ano invalido em ponto: {point}.")
    status = point.get("status")
    value = point.get("value")
    if status not in DATA_STATUSES:
        raise ValueError(f"Status invalido em ponto: {point}.")
    if value is not None and (
        isinstance(value, bool) or not isinstance(value, int) or value < 0
    ):
        raise ValueError(f"Valor invalido em ponto: {point}.")
    if value is None and status not in {STATUS_UNAVAILABLE, STATUS_NOT_APPLICABLE}:
        raise ValueError(f"Nulo com status incompativel: {point}.")
    if status == STATUS_DERIVED_ZERO and value != 0:
        raise ValueError(f"derived_zero sem valor zero: {point}.")
    references = []
    if "sourceId" in point and point["sourceId"] is not None:
        references.append(point["sourceId"])
    references.extend(point.get("sourceIds", ()))
    if any(reference not in source_ids for reference in references):
        raise ValueError(f"sourceId inexistente: {point}.")
    if status in {STATUS_OBSERVED, STATUS_DERIVED_ZERO} and not references:
        raise ValueError(f"Ponto utilizavel sem fonte: {point}.")


def _validate_no_local_paths(payload: Mapping) -> None:
    for value in _walk_strings(payload):
        normalized = value.replace("\\", "/").lower()
        if re.search(r"(?:[a-z]:/|/users/|/tmp/|appdata/|\\.superior-stage-)", normalized):
            raise ValueError(f"Caminho local encontrado no payload: {value!r}.")


def validate_public_directory(
    directory: Path,
    municipality_universe: Mapping[str, str],
) -> dict:
    index_path = directory / "index.json"
    municipal_directory = directory / "municipios"
    if not index_path.is_file() or not municipal_directory.is_dir():
        raise ValueError("Estrutura publica da Educacao Superior incompleta.")
    manifest = json.loads(index_path.read_text(encoding="utf-8"))
    if manifest.get("schemaVersion") != SCHEMA_VERSION:
        raise ValueError("schemaVersion invalida no manifesto.")
    if manifest.get("availableYears") != list(SUPPORTED_YEARS):
        raise ValueError("availableYears invalido no manifesto.")
    if [item.get("id") for item in manifest.get("indicators", ())] != [
        spec.id for spec in INDICATORS
    ]:
        raise ValueError("Catalogo de indicadores invalido.")
    if [item.get("id") for item in manifest.get("breakdowns", ())] != [
        spec.id for spec in BREAKDOWNS
    ]:
        raise ValueError("Catalogo de decomposicoes invalido.")
    source_ids = set(manifest.get("sources", {}))
    if len(source_ids) != len(SUPPORTED_YEARS) * len(REQUIRED_TABLES):
        raise ValueError("Registro central de fontes incompleto.")
    _validate_no_local_paths(manifest)

    files = sorted(municipal_directory.glob("*.json"))
    expected_names = {f"{municipality_id}.json" for municipality_id in municipality_universe}
    if len(files) != 497 or {path.name for path in files} != expected_names:
        raise ValueError("A saida nao contem os 497 arquivos municipais esperados.")

    availability_counts = Counter()
    indicator_file_counts = Counter()
    indicator_usable_file_counts = Counter()
    breakdown_file_counts = Counter()
    breakdown_usable_file_counts = Counter()
    indicator_status_counts = Counter()
    breakdown_status_counts = Counter()
    referenced_sources: set[str] = set()
    sizes: list[int] = []
    allowed_years = set(SUPPORTED_YEARS)
    expected_indicator_ids = [spec.id for spec in INDICATORS]
    expected_breakdown_order = [
        (spec.id, year)
        for spec in sorted(BREAKDOWNS, key=lambda item: item.id)
        for year in SUPPORTED_YEARS
    ]

    for path in files:
        payload = json.loads(path.read_text(encoding="utf-8"))
        municipality_id = path.stem
        municipality = payload.get("municipality", {})
        if municipality != {
            "id": municipality_id,
            "name": municipality_universe[municipality_id],
        }:
            raise ValueError(f"Dimensao municipal divergente em {path.name}.")
        availability = payload.get("availability")
        if availability not in AVAILABILITIES:
            raise ValueError(f"Disponibilidade invalida em {path.name}.")
        availability_counts[availability] += 1
        if set(payload) != {
            "schemaVersion",
            "municipality",
            "availability",
            "indicators",
            "breakdowns",
        }:
            raise ValueError(f"Campos de topo invalidos em {path.name}.")
        keys = set(_walk_keys(payload))
        forbidden = keys & FORBIDDEN_KEYS
        if forbidden:
            raise ValueError(f"Campos excluidos em {path.name}: {sorted(forbidden)}.")
        _validate_no_local_paths(payload)

        indicators = payload.get("indicators", {})
        if list(indicators) != expected_indicator_ids:
            raise ValueError(f"Ordem ou IDs de indicadores invalidos em {path.name}.")
        for indicator_id, indicator in indicators.items():
            indicator_file_counts[indicator_id] += 1
            series = indicator.get("series", ())
            if [point.get("year") for point in series] != list(SUPPORTED_YEARS):
                raise ValueError(f"Serie desordenada em {path.name}/{indicator_id}.")
            usable = False
            for point in series:
                _validate_point(point, source_ids, allowed_years)
                indicator_status_counts[point["status"]] += 1
                usable = usable or (
                    point["status"] in {STATUS_OBSERVED, STATUS_DERIVED_ZERO}
                    and point["value"] is not None
                )
                if point.get("sourceId"):
                    referenced_sources.add(point["sourceId"])
                referenced_sources.update(point.get("sourceIds", ()))
            if usable:
                indicator_usable_file_counts[indicator_id] += 1

        breakdowns = payload.get("breakdowns", ())
        if [(item.get("id"), item.get("year")) for item in breakdowns] != (
            expected_breakdown_order
        ):
            raise ValueError(f"Decomposicoes desordenadas em {path.name}.")
        seen_breakdown_ids: set[str] = set()
        usable_breakdown_ids: set[str] = set()
        for item in breakdowns:
            breakdown_id = item["id"]
            seen_breakdown_ids.add(breakdown_id)
            _validate_point(
                {
                    "year": item["year"],
                    "value": (
                        0
                        if item["status"] == STATUS_OBSERVED
                        else None
                    ),
                    "status": item["status"],
                    "sourceId": item.get("sourceId"),
                },
                source_ids,
                allowed_years,
            )
            category_usable = False
            for category in item.get("categories", ()):
                _validate_point(
                    {
                        "year": item["year"],
                        "value": category.get("value"),
                        "status": category.get("status"),
                        "sourceId": item.get("sourceId"),
                    },
                    source_ids,
                    allowed_years,
                )
                breakdown_status_counts[category["status"]] += 1
                category_usable = category_usable or (
                    category["status"] in {STATUS_OBSERVED, STATUS_DERIVED_ZERO}
                    and category["value"] is not None
                )
            if item.get("sourceId"):
                referenced_sources.add(item["sourceId"])
            if category_usable:
                usable_breakdown_ids.add(breakdown_id)
        for breakdown_id in seen_breakdown_ids:
            breakdown_file_counts[breakdown_id] += 1
        for breakdown_id in usable_breakdown_ids:
            breakdown_usable_file_counts[breakdown_id] += 1
        sizes.append(path.stat().st_size)

    if sum(availability_counts.values()) != 497:
        raise ValueError("Contagem de disponibilidade municipal invalida.")
    if not referenced_sources.issubset(source_ids):
        raise ValueError("Ha sourceIds municipais fora do manifesto.")
    index_size = index_path.stat().st_size
    if index_size > MAX_INDEX_BYTES:
        raise ValueError(f"index.json excede {MAX_INDEX_BYTES} bytes.")
    if max(sizes) > MAX_MUNICIPAL_BYTES:
        raise ValueError(f"Arquivo municipal excede {MAX_MUNICIPAL_BYTES} bytes.")
    sorted_sizes = sorted(sizes)
    p95_index = max(0, int(0.95 * len(sorted_sizes) + 0.999999) - 1)
    return {
        "municipalityFileCount": len(files),
        "availability": {
            availability: availability_counts[availability]
            for availability in AVAILABILITIES
        },
        "indicatorFiles": dict(indicator_file_counts),
        "indicatorUsableFiles": dict(indicator_usable_file_counts),
        "breakdownFiles": dict(breakdown_file_counts),
        "breakdownUsableFiles": dict(breakdown_usable_file_counts),
        "statusCounts": {
            "indicators": {
                status: indicator_status_counts[status]
                for status in (
                    STATUS_OBSERVED,
                    STATUS_DERIVED_ZERO,
                    STATUS_UNAVAILABLE,
                    STATUS_NOT_APPLICABLE,
                )
            },
            "breakdownCategories": {
                status: breakdown_status_counts[status]
                for status in (
                    STATUS_OBSERVED,
                    STATUS_DERIVED_ZERO,
                    STATUS_UNAVAILABLE,
                    STATUS_NOT_APPLICABLE,
                )
            },
        },
        "sourceIds": {
            "declared": len(source_ids),
            "referenced": len(referenced_sources),
            "invalid": 0,
        },
        "sizeBytes": {
            "manifest": index_size,
            "directoryTotal": sum(
                path.stat().st_size for path in directory.rglob("*.json")
            ),
            "municipalMinimum": min(sorted_sizes),
            "municipalMedian": statistics.median(sorted_sizes),
            "municipalP95": sorted_sizes[p95_index],
            "municipalMaximum": max(sorted_sizes),
            "municipalAboveReviewThreshold": sum(
                size > REVIEW_MUNICIPAL_BYTES for size in sizes
            ),
        },
    }


def tree_hash(directory: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(directory.rglob("*.json")):
        digest.update(path.relative_to(directory).as_posix().encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _rename_directory_with_retry(
    source: Path,
    target: Path,
    *,
    attempts: int,
) -> None:
    for attempt in range(attempts):
        try:
            os.rename(source, target)
            return
        except PermissionError:
            if attempt + 1 == attempts:
                raise
            time.sleep(min(0.1 * (attempt + 1), 1.0))


def replace_directory_atomically(
    staging: Path,
    output: Path,
    *,
    rename_attempts: int = 20,
) -> None:
    if not staging.is_dir():
        raise ValueError("Diretorio de staging ausente.")
    output.parent.mkdir(parents=True, exist_ok=True)
    backup = output.parent / f".{output.name}.backup-{uuid.uuid4().hex}"
    previous_moved = False
    try:
        if output.exists():
            _rename_directory_with_retry(
                output,
                backup,
                attempts=rename_attempts,
            )
            previous_moved = True
        _rename_directory_with_retry(
            staging,
            output,
            attempts=rename_attempts,
        )
    except Exception:
        if previous_moved and not output.exists() and backup.exists():
            _rename_directory_with_retry(
                backup,
                output,
                attempts=rename_attempts,
            )
        raise
    finally:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
    if backup.exists():
        shutil.rmtree(backup)


def materialize_higher_education(
    audit: ParsedAudit,
    *,
    municipality_index_path: Path,
    output_directory: Path,
) -> dict:
    municipality_universe = load_municipality_universe(municipality_index_path)
    output_directory = output_directory.resolve()
    output_directory.parent.mkdir(parents=True, exist_ok=True)
    system_temporary = Path(tempfile.gettempdir()).resolve()
    staging_parent = (
        system_temporary
        if system_temporary.drive.lower() == output_directory.drive.lower()
        else output_directory.parent
    )
    stage_paths = [
        Path(
            tempfile.mkdtemp(
                prefix=".superior-stage-",
                dir=staging_parent,
            )
        )
        for _ in range(2)
    ]
    try:
        validations: list[dict] = []
        hashes: list[str] = []
        data_version = None
        for stage in stage_paths:
            manifest, municipalities = build_public_contracts(
                audit,
                municipality_universe,
            )
            data_version = manifest["dataVersion"]
            write_public_contracts(stage, manifest, municipalities)
            validations.append(
                validate_public_directory(stage, municipality_universe)
            )
            hashes.append(tree_hash(stage))
        if hashes[0] != hashes[1]:
            raise ValueError(
                f"Materializacao nao deterministica: {hashes[0]} != {hashes[1]}."
            )
        replace_directory_atomically(stage_paths[0], output_directory)
        shutil.rmtree(stage_paths[1])
        final_validation = validate_public_directory(
            output_directory,
            municipality_universe,
        )
        return {
            "schemaVersion": SCHEMA_VERSION,
            "dataVersion": data_version,
            "outputDirectory": str(output_directory),
            "treeHash": hashes[0],
            "determinism": {
                "firstHash": hashes[0],
                "secondHash": hashes[1],
                "matched": True,
            },
            "validation": final_validation,
        }
    except Exception:
        for stage in stage_paths:
            if stage.exists():
                shutil.rmtree(stage, ignore_errors=True)
        raise
