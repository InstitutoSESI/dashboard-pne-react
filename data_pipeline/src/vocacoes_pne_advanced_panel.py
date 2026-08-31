"""Painel analítico alinhado do programa Vocações × PNE — estágio AA1.

O módulo normaliza somente artefatos locais já materializados. Ele não consulta
banco ou rede, não escreve em ``public/data`` e não funde lentes territoriais.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from contextlib import contextmanager
import gc
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
from typing import Any

import pandas as pd

from .vocacoes_pne_job2 import (
    canonical_json_bytes,
    directory_content_digest,
    sha256_file,
    write_csv_gzip,
    write_json,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = (
    REPO_ROOT / "data_pipeline/contracts/vocacoes-pne-advanced-panel-v1.json"
)
MUNICIPALITY_REGISTRY_PATH = REPO_ROOT / "config/municipalities/rs.json"
REGION_REGISTRY_PATH = REPO_ROOT / "config/regions/rs.json"
AA0_MANIFEST_PATH = (
    REPO_ROOT / "data_pipeline/manifests/vocacoes-pne-aa0-worktree-baseline.json"
)
DEFAULT_OUTPUT_ROOT = (
    REPO_ROOT / ".tmp/vocacoes-pne/advanced-analytics-v1/aa1"
)
STATE_SOURCE_ROOT = REPO_ROOT / ".tmp/vocacoes-pne/v7-job5l/sources/database"
RAIS_SOURCE_PATH = (
    REPO_ROOT
    / ".tmp/vocacoes-pne/v7-job5l-final/internal/PAINEL_RAIS_JOB5L_FINAL.csv.gz"
)
FINANCE_ROOT = REPO_ROOT / "data_pipeline/export/municipal_finance/municipios"

REGIONAL_SOURCE_PATHS = {
    "JOB5GCR_EPT_VALE": REPO_ROOT
    / ".tmp/vocacoes-pne/v7-job5gcr/PAINEL_EPT_OFERTA_TOTAL_V1_1.csv.gz",
    "JOB5GCR_OCCUPATIONS_VALE": REPO_ROOT
    / ".tmp/vocacoes-pne/v7-job5gcr/PAINEL_OCUPACOES_RAIS_ESTOQUE_V1.csv.gz",
    "JOB5GCR_SECTORS_VALE": REPO_ROOT
    / ".tmp/vocacoes-pne/v7-job5gcr/PAINEL_SETORES_RAIS_ESTOQUE_V1.csv.gz",
    "JOB5GCR_SHIFT_SHARE_VALE_RS": REPO_ROOT
    / ".tmp/vocacoes-pne/v7-job5gcr/PAINEL_SHIFT_SHARE_SETORIAL_V1_1.csv.gz",
    "JOB5GBR_EJA_VALE": REPO_ROOT
    / ".tmp/vocacoes-pne/v7-job5gbr/PAINEL_EJA_HISTORICA_2014_2025_V1_1.csv.gz",
    "JOB5GBR_RURAL_VALE": REPO_ROOT
    / ".tmp/vocacoes-pne/v7-job5gbr/PAINEL_EDUCACAO_RURAL_TERRITORIO_V1_1.csv.gz",
    "JOB5GBR_AEE_VALE": REPO_ROOT
    / ".tmp/vocacoes-pne/v7-job5gbr/PAINEL_EDUCACAO_ESPECIAL_AEE_V1_1.csv.gz",
    "JOB5GBR_VULNERABILITY_VALE": REPO_ROOT
    / ".tmp/vocacoes-pne/v7-job5gbr/PAINEL_VULNERABILIDADE_EDUCACIONAL_V1_1.csv.gz",
}

PANEL_FILE = "PAINEL_ANALITICO_ESTADUAL_AA1.csv.gz"
CATALOG_FILE = "CATALOGO_METRICAS_AA1.json"
COVERAGE_FILE = "COBERTURA_FAMILIAS_AA1.json"
GRAIN_FILE = "RECONCILIACAO_GRAO_AA1.json"
TEMPORAL_FILE = "AUDITORIA_TEMPORAL_AA1.json"
AA2_GATE_FILE = "AA2_ENTRY_GATE_AA1.json"
SOURCE_FILE = "SOURCE_INVENTORY_AA1.json"
QA_FILE = "QA_SUMMARY_AA1.json"
MANIFEST_FILE = "MANIFEST_AA1.json"
PACKAGE_FILES = (
    PANEL_FILE,
    CATALOG_FILE,
    COVERAGE_FILE,
    GRAIN_FILE,
    TEMPORAL_FILE,
    AA2_GATE_FILE,
    SOURCE_FILE,
    QA_FILE,
    MANIFEST_FILE,
)
NON_MANIFEST_FILES = PACKAGE_FILES[:-1]
RUNNER_PATH = REPO_ROOT / "data_pipeline/scripts/run_vocacoes_pne_advanced_panel.py"
IMPLEMENTATION_PATHS = (
    CONTRACT_PATH,
    REPO_ROOT / "data_pipeline/src/vocacoes_pne_advanced_panel.py",
    RUNNER_PATH,
    REPO_ROOT / "data_pipeline/tests/test_vocacoes_pne_advanced_panel.py",
)

GENERATED_AT = "2026-08-30T00:00:00-03:00"
EXPECTED_PUBLIC_DATA_DIGEST = (
    "4a52e3891163cb3427c5c01f2ef5414c5fe7855dd491a9a125b509899dcc23e1"
)
PRE_ADDENDUM_PANEL_SHA256 = (
    "1f500c731acecc52ceb2beaee1884a48607ec2f102220b956e5846cc3674fb0a"
)
NSR_CODE = "4313375"
IBGE_CODE_PATTERN = re.compile(r"^[0-9]{7}$")
AVAILABILITY_STATES = {
    "observed",
    "observed_zero",
    "unavailable",
    "suppressed",
    "not_applicable",
}
COVERAGE_SCOPES = {"RS_497", "VALE_10"}
COVERAGE_REASONS = {
    "STATEWIDE_SOURCE_AVAILABLE",
    "FROZEN_ANALYTICAL_SOURCE_RESTRICTED_TO_VALE_10",
}
UNAVAILABILITY_REASONS = {
    "VALUE_AVAILABLE",
    "SOURCE_DECLARED_UNAVAILABLE",
    "SOURCE_VALUE_MISSING",
    "REFERENCE_COMPONENT_UNAVAILABLE_ZERO_BASE",
    "SOURCE_SUPPRESSED",
    "SOURCE_NOT_APPLICABLE",
    "DENOMINATOR_ZERO",
}
REFERENCE_SCOPES = {
    "NO_EXTERNAL_REFERENCE",
    "RS_SAME_VERSION_COMPONENT_BENCHMARK",
}
AGGREGATION_GUARDS = {
    "WITHIN_DECLARED_COVERAGE_ONLY",
    "DO_NOT_AGGREGATE_AS_RS_TOTAL",
}
DATABASE_CLIENT_MODULE_ROOTS = {
    "duckdb",
    "psycopg",
    "psycopg2",
    "pymongo",
    "pymysql",
    "pyodbc",
    "sqlalchemy",
}
NETWORK_CLIENT_MODULE_ROOTS = {"aiohttp", "httpx", "requests"}
SHIFT_SHARE_METRICS = {
    "absolute_change": "labor.shift_share.observed_absolute_change",
    "reference_growth_effect": "labor.shift_share.reference_growth_effect",
    "industry_mix_effect": "labor.shift_share.industry_mix_effect",
    "local_differential_effect": "labor.shift_share.local_differential_effect",
    "closure_residual": "labor.shift_share.closure_residual",
}

PANEL_COLUMNS = (
    "family_id",
    "municipality_ibge_code",
    "municipality_name",
    "year_or_reference_period",
    "stage_or_population_group",
    "metric_id",
    "dimension_id",
    "dimension_label",
    "raw_value",
    "unit",
    "availability_state",
    "source_availability_state",
    "unavailability_reason",
    "universe",
    "territorial_lens",
    "network_scope",
    "coverage_scope",
    "coverage_reason",
    "reference_scope",
    "aggregation_guard",
    "source_ref",
    "source_period",
    "method_state",
    "source_id",
    "numerator",
    "denominator",
    "formula_id",
    "claim_ceiling",
)

PRE_ADDENDUM_PANEL_COLUMNS = tuple(
    column
    for column in PANEL_COLUMNS
    if column not in {"coverage_reason", "unavailability_reason"}
)

UNIQUE_KEY = (
    "family_id",
    "municipality_ibge_code",
    "year_or_reference_period",
    "stage_or_population_group",
    "metric_id",
    "dimension_id",
    "universe",
    "territorial_lens",
    "network_scope",
    "coverage_scope",
    "reference_scope",
)


class AdvancedPanelValidationError(ValueError):
    """Falha fechada do contrato ou da materialização AA1."""


@contextmanager
def blocked_external_io_guard() -> Iterable[None]:
    """Bloqueia egressos de rede e conexões SQLite durante o runner AA1."""

    original_socket_connect = socket.socket.connect
    original_create_connection = socket.create_connection
    original_sqlite_connect = sqlite3.connect

    def blocked(*_args: Any, **_kwargs: Any) -> Any:
        raise AdvancedPanelValidationError(
            "AA1 permite somente entradas locais congeladas; conexão externa bloqueada"
        )

    socket.socket.connect = blocked  # type: ignore[method-assign]
    socket.create_connection = blocked
    sqlite3.connect = blocked  # type: ignore[assignment]
    try:
        yield
    finally:
        socket.socket.connect = original_socket_connect  # type: ignore[method-assign]
        socket.create_connection = original_create_connection
        sqlite3.connect = original_sqlite_connect  # type: ignore[assignment]


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _relative(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def _display_path(path: Path) -> str:
    try:
        return _relative(path.resolve())
    except ValueError:
        return path.resolve().as_posix()


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(
        path,
        compression="gzip" if path.suffix == ".gz" else "infer",
        dtype="string",
        keep_default_na=True,
        low_memory=False,
    )


def _stable_frame(frame: pd.DataFrame, keys: Sequence[str]) -> pd.DataFrame:
    return frame.sort_values(
        list(keys), kind="mergesort", na_position="last"
    ).reset_index(drop=True)


def _sha256_payload(payload: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def _number(value: Any) -> float | None:
    if value is None or value is pd.NA:
        return None
    text = str(value).strip()
    if not text or text.casefold() in {"nan", "null", "none", "<na>"}:
        return None
    try:
        result = float(text)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _token(value: Any, *, default: str) -> str:
    if value is None or value is pd.NA:
        return default
    text = str(value).strip()
    return default if not text or text.casefold() in {"nan", "null", "<na>"} else text


def _dimension_token(value: Any, *, default: str = "ALL") -> str:
    text = _token(value, default=default)
    if re.fullmatch(r"-?[0-9]+\.0", text):
        return text[:-2]
    return text


def _availability(value: Any, source_state: Any = None) -> tuple[float | None, str, str]:
    numeric = _number(value)
    source = _token(source_state, default="not_declared")
    normalized = source.casefold().replace("-", "_").replace(" ", "_")
    if "suppress" in normalized:
        return None, "suppressed", source
    if "not_applicable" in normalized or "nao_aplic" in normalized:
        return None, "not_applicable", source
    if (
        "unavailable" in normalized
        or "not_available" in normalized
        or normalized.startswith("waiting_")
    ):
        return None, "unavailable", source
    if numeric is None:
        return None, "unavailable", source
    return numeric, "observed_zero" if numeric == 0 else "observed", source


def _unavailability_reason(
    availability_state: str,
    source_state: str,
    denominator: float | None,
) -> str:
    if denominator == 0:
        return "DENOMINATOR_ZERO"
    if availability_state in {"observed", "observed_zero"}:
        return "VALUE_AVAILABLE"
    normalized = source_state.casefold().replace("-", "_").replace(" ", "_")
    if "new_activity_from_zero_base" in normalized:
        return "REFERENCE_COMPONENT_UNAVAILABLE_ZERO_BASE"
    if availability_state == "suppressed":
        return "SOURCE_SUPPRESSED"
    if availability_state == "not_applicable":
        return "SOURCE_NOT_APPLICABLE"
    if "unavailable" in normalized or "not_available" in normalized:
        return "SOURCE_DECLARED_UNAVAILABLE"
    return "SOURCE_VALUE_MISSING"


def _registries() -> tuple[list[str], dict[str, str], list[str]]:
    municipality_payload = _json(MUNICIPALITY_REGISTRY_PATH)
    municipalities = municipality_payload["municipalities"]
    codes = [item["ibgeCode"] for item in municipalities]
    if len(codes) != 497 or len(set(codes)) != 497:
        raise AdvancedPanelValidationError("Registro do RS não contém 497 códigos únicos")
    if any(not isinstance(code, str) or not IBGE_CODE_PATTERN.fullmatch(code) for code in codes):
        raise AdvancedPanelValidationError("Código municipal não textual ou fora de sete dígitos")
    names = {item["ibgeCode"]: item["name"] for item in municipalities}
    if names.get(NSR_CODE) != "Nova Santa Rita":
        raise AdvancedPanelValidationError("Fixture de Nova Santa Rita divergente")

    region_payload = _json(REGION_REGISTRY_PATH)
    region = next(
        item for item in region_payload["regions"] if item["slug"] == "vale-do-sinos"
    )
    region_codes = list(region["municipalityIbgeCodes"])
    if len(region_codes) != 10 or len(set(region_codes)) != 10:
        raise AdvancedPanelValidationError("Vale do Sinos não contém dez códigos únicos")
    if NSR_CODE not in region_codes or not set(region_codes).issubset(names):
        raise AdvancedPanelValidationError("Recorte regional não reconcilia com o registro")
    return codes, names, region_codes


def _source_ref(path: Path, field: str | None = None) -> str:
    base = _relative(path)
    return f"{base}#{field}" if field else base


def _coverage_scope_for(family_id: str, metric_id: str) -> str:
    if family_id in {
        "F1_EDUCATIONAL_TRAJECTORY_AND_CONDITIONS",
        "F2_DEMOGRAPHY_ENROLLMENT_AND_OFFER",
    }:
        return "RS_497"
    if family_id in {
        "F3_YOUTH_WORK_AND_APPRENTICESHIP",
        "F4_OCCUPATIONS_SECTORS_AND_EPT",
    }:
        return "VALE_10"
    if family_id == "F5_ADULT_SCHOOLING_AND_EJA":
        return "RS_497" if metric_id.startswith("adult.") else "VALE_10"
    if family_id == "F6_VULNERABILITY_RURALITY_INCLUSION_AND_FINANCE":
        return "RS_497" if metric_id.startswith("finance.") else "VALE_10"
    raise AdvancedPanelValidationError(
        f"Família sem regra de cobertura AA1: {family_id!r}"
    )


def _coverage_reason_for(coverage_scope: str) -> str:
    if coverage_scope == "RS_497":
        return "STATEWIDE_SOURCE_AVAILABLE"
    if coverage_scope == "VALE_10":
        return "FROZEN_ANALYTICAL_SOURCE_RESTRICTED_TO_VALE_10"
    raise AdvancedPanelValidationError(
        f"Escopo sem razão de cobertura AA1: {coverage_scope!r}"
    )


def _append_observation(
    rows: list[dict[str, Any]],
    *,
    names: Mapping[str, str],
    family_id: str,
    code: Any,
    period: Any,
    group: Any,
    metric_id: str,
    value: Any,
    unit: str,
    source_state: Any,
    universe: str,
    territorial_lens: str,
    network_scope: str,
    source_ref: str,
    source_period: Any,
    method_state: str,
    source_id: str,
    coverage_scope: str | None = None,
    coverage_reason: str | None = None,
    reference_scope: str = "NO_EXTERNAL_REFERENCE",
    aggregation_guard: str = "WITHIN_DECLARED_COVERAGE_ONLY",
    dimension_id: Any = "ALL",
    dimension_label: Any = "Todos",
    numerator: Any = None,
    denominator: Any = None,
    formula_id: str = "source_value_preserved",
    claim_ceiling: str = "OBSERVED_FACT",
) -> None:
    municipality_code = _token(code, default="")
    if municipality_code not in names:
        raise AdvancedPanelValidationError(
            f"Código municipal fora do registro canônico: {municipality_code!r}"
        )
    raw_value, availability_state, original_state = _availability(value, source_state)
    numerator_value = _number(numerator)
    denominator_value = _number(denominator)
    if denominator_value == 0:
        raw_value = None
        availability_state = "unavailable"
    unavailability_reason = _unavailability_reason(
        availability_state, original_state, denominator_value
    )
    resolved_coverage_scope = coverage_scope or _coverage_scope_for(
        family_id, metric_id
    )
    resolved_coverage_reason = coverage_reason or _coverage_reason_for(
        resolved_coverage_scope
    )
    rows.append(
        {
            "family_id": family_id,
            "municipality_ibge_code": municipality_code,
            "municipality_name": names[municipality_code],
            "year_or_reference_period": _token(period, default="unavailable_period"),
            "stage_or_population_group": _token(group, default="not_applicable"),
            "metric_id": metric_id,
            "dimension_id": _dimension_token(dimension_id),
            "dimension_label": _token(dimension_label, default=_dimension_token(dimension_id)),
            "raw_value": raw_value,
            "unit": unit,
            "availability_state": availability_state,
            "source_availability_state": original_state,
            "unavailability_reason": unavailability_reason,
            "universe": universe,
            "territorial_lens": territorial_lens,
            "network_scope": network_scope,
            "coverage_scope": resolved_coverage_scope,
            "coverage_reason": resolved_coverage_reason,
            "reference_scope": reference_scope,
            "aggregation_guard": aggregation_guard,
            "source_ref": source_ref,
            "source_period": _token(source_period, default="unavailable_period"),
            "method_state": method_state,
            "source_id": source_id,
            "numerator": numerator_value,
            "denominator": denominator_value,
            "formula_id": formula_id,
            "claim_ceiling": claim_ceiling,
        }
    )


def _municipal_rows(frame: pd.DataFrame) -> pd.DataFrame:
    if "entity_scope" in frame.columns:
        frame = frame[frame["entity_scope"].eq("municipality")]
    return frame[frame["municipality_ibge_code"].notna()].copy()


def _build_f1(rows: list[dict[str, Any]], names: Mapping[str, str]) -> None:
    trajectory_path = STATE_SOURCE_ROOT / "trajectory_total_network.csv.gz"
    trajectory = _read_csv(trajectory_path)
    for record in trajectory.to_dict("records"):
        _append_observation(
            rows,
            names=names,
            family_id="F1_EDUCATIONAL_TRAJECTORY_AND_CONDITIONS",
            code=record["municipality_ibge_code"],
            period=record["year"],
            group=record["stage"],
            metric_id=f"education.{record['outcome_id']}",
            value=record["observed_value"],
            unit="percent",
            source_state="observed",
            universe="students_enrolled_in_stage_at_school_location",
            territorial_lens=_token(record["territorial_lens"], default="school_location"),
            network_scope=_token(record["network_scope"], default="total_all_dependencies"),
            source_ref=_source_ref(trajectory_path, "observed_value"),
            source_period=record["year"],
            method_state="official_source_value_preserved",
            source_id="JOB5L_FROZEN_STATE_CONTEXT",
        )

    adequacy_path = STATE_SOURCE_ROOT / "teacher_adequacy_total_network.csv.gz"
    adequacy = _read_csv(adequacy_path)
    stage_map = {
        "anos_iniciais": "fundamental_anos_iniciais",
        "anos_finais": "fundamental_anos_finais",
        "ensino_medio": "medio",
    }
    for record in adequacy.to_dict("records"):
        _append_observation(
            rows,
            names=names,
            family_id="F1_EDUCATIONAL_TRAJECTORY_AND_CONDITIONS",
            code=record["municipality_ibge_code"],
            period=record["year"],
            group=stage_map.get(_token(record["adequacy_stage"], default=""), record["adequacy_stage"]),
            metric_id="education.teacher_adequacy_percent",
            value=record["teacher_adequacy_percent"],
            unit="percent",
            source_state="observed",
            universe="teachers_in_total_all_dependencies",
            territorial_lens="school_location",
            network_scope="total_all_dependencies",
            source_ref=_source_ref(adequacy_path, "teacher_adequacy_percent"),
            source_period=record["year"],
            method_state="official_source_value_preserved",
            source_id="JOB5L_FROZEN_STATE_CONTEXT",
        )

    inse_path = STATE_SOURCE_ROOT / "inse_total_network.csv.gz"
    inse = _read_csv(inse_path)
    for record in inse.to_dict("records"):
        for field, metric_id, unit in (
            ("inse_value", "education.inse_value", "inse_scale_points"),
            ("assessed_students", "education.inse_assessed_students", "students"),
        ):
            _append_observation(
                rows,
                names=names,
                family_id="F1_EDUCATIONAL_TRAJECTORY_AND_CONDITIONS",
                code=record["municipality_ibge_code"],
                period=record["year"],
                group="education_basic_assessed",
                metric_id=metric_id,
                value=record[field],
                unit=unit,
                source_state="observed",
                universe="students_assessed_in_total_all_dependencies",
                territorial_lens="school_location",
                network_scope="total_all_dependencies",
                source_ref=_source_ref(inse_path, field),
                source_period=record["year"],
                method_state="official_source_value_preserved",
                source_id="JOB5L_FROZEN_STATE_CONTEXT",
            )


def _build_f2(rows: list[dict[str, Any]], names: Mapping[str, str]) -> None:
    population_path = STATE_SOURCE_ROOT / "population_context.csv.gz"
    population = _read_csv(population_path)
    population_metrics = {
        "total_population": ("demography.total_population", "all_ages"),
        "population_6_10": ("demography.population_age_6_10", "age_6_10"),
        "population_11_14": ("demography.population_age_11_14", "age_11_14"),
        "population_15_17": ("demography.population_age_15_17", "age_15_17"),
        "population_18_24": ("demography.population_age_18_24", "age_18_24"),
    }
    for record in population.to_dict("records"):
        for field, (metric_id, group) in population_metrics.items():
            _append_observation(
                rows,
                names=names,
                family_id="F2_DEMOGRAPHY_ENROLLMENT_AND_OFFER",
                code=record["municipality_ibge_code"],
                period=record["year"],
                group=group,
                metric_id=metric_id,
                value=record[field],
                unit="people",
                source_state="observed",
                universe="resident_population",
                territorial_lens="resident_population",
                network_scope="not_applicable",
                source_ref=_source_ref(population_path, field),
                source_period=record["year"],
                method_state="official_source_value_preserved",
                source_id="JOB5L_FROZEN_STATE_CONTEXT",
            )

    school_path = STATE_SOURCE_ROOT / "school_context.csv.gz"
    school = _read_csv(school_path)
    school_metrics = {
        "mat_basico": ("education.enrollments", "education_basic", "enrollments"),
        "mat_fundamental_anos_iniciais": (
            "education.enrollments",
            "fundamental_anos_iniciais",
            "enrollments",
        ),
        "mat_fundamental_anos_finais": (
            "education.enrollments",
            "fundamental_anos_finais",
            "enrollments",
        ),
        "mat_medio": ("education.enrollments", "medio", "enrollments"),
        "mat_basico_integral": (
            "education.full_time_enrollments",
            "education_basic",
            "enrollments",
        ),
        "mat_fundamental_anos_iniciais_integral": (
            "education.full_time_enrollments",
            "fundamental_anos_iniciais",
            "enrollments",
        ),
        "mat_fundamental_anos_finais_integral": (
            "education.full_time_enrollments",
            "fundamental_anos_finais",
            "enrollments",
        ),
        "mat_medio_integral": (
            "education.full_time_enrollments",
            "medio",
            "enrollments",
        ),
        "rural_mat_basico": (
            "education.rural_basic_enrollments",
            "education_basic",
            "enrollments",
        ),
        "schools": ("education.school_count", "education_basic", "schools"),
        "schools_with_internet": (
            "education.schools_with_internet",
            "education_basic",
            "schools",
        ),
    }
    for record in school.to_dict("records"):
        for field, (metric_id, group, unit) in school_metrics.items():
            _append_observation(
                rows,
                names=names,
                family_id="F2_DEMOGRAPHY_ENROLLMENT_AND_OFFER",
                code=record["municipality_ibge_code"],
                period=record["year"],
                group=group,
                metric_id=metric_id,
                value=record[field],
                unit=unit,
                source_state="observed",
                universe="located_school_offer_total_all_dependencies",
                territorial_lens="school_location",
                network_scope="total_all_dependencies",
                source_ref=_source_ref(school_path, field),
                source_period=record["year"],
                method_state="official_source_value_preserved",
                source_id="JOB5L_FROZEN_STATE_CONTEXT",
            )


def _build_f3(rows: list[dict[str, Any]], names: Mapping[str, str]) -> None:
    panel = _municipal_rows(_read_csv(RAIS_SOURCE_PATH))
    for record in panel.to_dict("records"):
        age_group = _token(record["age_group"], default="not_available")
        _append_observation(
            rows,
            names=names,
            family_id="F3_YOUTH_WORK_AND_APPRENTICESHIP",
            code=record["municipality_ibge_code"],
            period=record["year"],
            group=f"age_{age_group}",
            metric_id=f"labor.youth_rais.{record['metric_id']}",
            dimension_id=record["dimension_code"],
            dimension_label=record["dimension_label"],
            value=record["value"],
            unit=_token(record["unit"], default="unresolved_unit"),
            source_state=record["value_status"],
            universe=f"active_formal_bonds_age_{age_group}_at_31_12",
            territorial_lens=_token(
                record["territorial_lens"], default="establishment_location_workplace"
            ),
            network_scope="not_applicable",
            source_ref=_source_ref(RAIS_SOURCE_PATH, "value"),
            source_period=record["year"],
            method_state="reconciled_source_stock_preserved",
            source_id="JOB5L_FINAL_RAIS_VALE",
            numerator=record["numerator"],
            denominator=record["denominator"],
            formula_id="source_metric_and_dimension_preserved",
            claim_ceiling="DISTRIBUTIONAL_PATTERN",
        )


def _build_f4(rows: list[dict[str, Any]], names: Mapping[str, str]) -> None:
    ept_path = REGIONAL_SOURCE_PATHS["JOB5GCR_EPT_VALE"]
    ept = _municipal_rows(_read_csv(ept_path))
    for record in ept.to_dict("records"):
        dimension = "|".join(
            [
                f"grain={_token(record['grain'], default='unknown')}",
                f"school={_dimension_token(record['school_code'])}",
                f"axis={_dimension_token(record['technological_axis_code'])}",
                f"course={_dimension_token(record['course_code'])}",
            ]
        )
        label = " | ".join(
            [
                _token(record["technological_axis_name"], default="Todos os eixos"),
                _token(record["course_name"], default="Todos os cursos"),
                _token(record["school_name"], default="Todas as escolas"),
            ]
        )
        for field, metric_id, unit in (
            ("technical_enrollments", "education.ept_technical_enrollments", "enrollments"),
            ("class_count", "education.ept_class_count", "classes"),
        ):
            _append_observation(
                rows,
                names=names,
                family_id="F4_OCCUPATIONS_SECTORS_AND_EPT",
                code=record["municipality_ibge_code"],
                period=record["year"],
                group="professional_technical",
                metric_id=metric_id,
                dimension_id=dimension,
                dimension_label=label,
                value=record[field],
                unit=unit,
                source_state=record["availability_status"],
                universe="technical_education_offer_at_school_location",
                territorial_lens="school_location",
                network_scope="total_all_dependencies",
                source_ref=_source_ref(ept_path, field),
                source_period=record["year"],
                method_state="source_offer_value_preserved",
                source_id="JOB5GCR_EPT_VALE",
                claim_ceiling="DISTRIBUTIONAL_PATTERN",
            )

    for source_id, kind, path_key, code_field in (
        ("JOB5GCR_OCCUPATIONS_VALE", "occupation", "JOB5GCR_OCCUPATIONS_VALE", "dimension_code"),
        ("JOB5GCR_SECTORS_VALE", "sector", "JOB5GCR_SECTORS_VALE", "dimension_code"),
    ):
        path = REGIONAL_SOURCE_PATHS[path_key]
        frame = _municipal_rows(_read_csv(path))
        for record in frame.to_dict("records"):
            dimension = _dimension_token(record[code_field])
            label = _token(record["dimension_label"], default=dimension)
            for value_field, year_field in (
                ("initial_value", "initial_year"),
                ("final_value", "final_year"),
            ):
                _append_observation(
                    rows,
                    names=names,
                    family_id="F4_OCCUPATIONS_SECTORS_AND_EPT",
                    code=record["municipality_ibge_code"],
                    period=record[year_field],
                    group="all_ages",
                    metric_id=f"labor.{kind}_active_bonds",
                    dimension_id=dimension,
                    dimension_label=label,
                    value=record[value_field],
                    unit="active_bonds",
                    source_state=record["change_status"],
                    universe="active_formal_bonds_all_ages_at_31_12",
                    territorial_lens="workplace",
                    network_scope="not_applicable",
                    source_ref=_source_ref(path, value_field),
                    source_period=f"{record['initial_year']}-{record['final_year']}",
                    method_state="source_endpoint_stock_preserved",
                    source_id=source_id,
                    claim_ceiling="DISTRIBUTIONAL_PATTERN",
                )

    shift_path = REGIONAL_SOURCE_PATHS["JOB5GCR_SHIFT_SHARE_VALE_RS"]
    shift = _read_csv(shift_path)
    for record in shift.to_dict("records"):
        period = f"{record['initial_year']}-{record['final_year']}"
        dimension = _dimension_token(record["cnae_division_code"])
        for field, metric_id in SHIFT_SHARE_METRICS.items():
            _append_observation(
                rows,
                names=names,
                family_id="F4_OCCUPATIONS_SECTORS_AND_EPT",
                code=record["municipality_ibge_code"],
                period=period,
                group="all_ages",
                metric_id=metric_id,
                dimension_id=dimension,
                dimension_label=record["cnae_division_label"],
                value=record[field],
                unit="active_bonds",
                source_state=record["component_status"],
                universe="active_formal_bonds_all_ages_at_31_12",
                territorial_lens="workplace",
                network_scope="not_applicable",
                source_ref=_source_ref(shift_path, field),
                source_period=period,
                method_state="source_accounting_decomposition_preserved",
                source_id="JOB5GCR_SHIFT_SHARE_VALE_RS",
                reference_scope="RS_SAME_VERSION_COMPONENT_BENCHMARK",
                aggregation_guard="DO_NOT_AGGREGATE_AS_RS_TOTAL",
                formula_id="observed_change_equals_reference_plus_mix_plus_local",
                claim_ceiling="ACCOUNTING_DECOMPOSITION",
            )


def _build_f5(rows: list[dict[str, Any]], names: Mapping[str, str]) -> None:
    adult_path = STATE_SOURCE_ROOT / "adult_schooling_2022.csv.gz"
    adult = _read_csv(adult_path)
    adult_metrics = {
        "fundamental_completed": ("adult.fundamental_completed_count", "people"),
        "high_school_completed": ("adult.high_school_completed_count", "people"),
        "adult_population": ("adult.population_count", "people"),
        "adult_fundamental_completion_share_2022": (
            "adult.fundamental_completion_share_percent",
            "percent",
        ),
        "adult_high_school_completion_share_2022": (
            "adult.high_school_completion_share_percent",
            "percent",
        ),
    }
    for record in adult.to_dict("records"):
        for field, (metric_id, unit) in adult_metrics.items():
            _append_observation(
                rows,
                names=names,
                family_id="F5_ADULT_SCHOOLING_AND_EJA",
                code=record["municipality_ibge_code"],
                period="2022",
                group="adult_18_or_more",
                metric_id=metric_id,
                value=record[field],
                unit=unit,
                source_state="observed",
                universe="resident_adult_population_18_or_more",
                territorial_lens="resident_population",
                network_scope="not_applicable",
                source_ref=_source_ref(adult_path, field),
                source_period="2022",
                method_state="official_source_value_preserved",
                source_id="JOB5L_FROZEN_STATE_CONTEXT",
            )

    eja_path = REGIONAL_SOURCE_PATHS["JOB5GBR_EJA_VALE"]
    eja = _municipal_rows(_read_csv(eja_path))
    for record in eja.to_dict("records"):
        _append_observation(
            rows,
            names=names,
            family_id="F5_ADULT_SCHOOLING_AND_EJA",
            code=record["municipality_ibge_code"],
            period=record["year"],
            group=f"eja_{record['stage']}",
            metric_id="education.eja_enrollments",
            value=record["eja_enrollments"],
            unit="enrollments",
            source_state=record["value_status"],
            universe="eja_enrollments_at_school_location",
            territorial_lens="school_location",
            network_scope="total_all_dependencies",
            source_ref=_source_ref(eja_path, "eja_enrollments"),
            source_period=record["year"],
            method_state="source_stage_separated_series_preserved",
            source_id="JOB5GBR_EJA_VALE",
            claim_ceiling="DISTRIBUTIONAL_PATTERN",
        )


def _finance_measure(
    rows: list[dict[str, Any]],
    *,
    names: Mapping[str, str],
    code: str,
    path: Path,
    source_pointer: str,
    metric_id: str,
    measure: Mapping[str, Any] | None,
    default_year: int,
    default_unit: str,
) -> None:
    payload = dict(measure or {})
    value = payload.get("value")
    source_state = payload.get("nullReasonCode") or (
        "observed" if _number(value) is not None else "unavailable"
    )
    year = payload.get("referenceYear", default_year)
    unit = payload.get("unit", default_unit)
    amount_nature = _token(payload.get("amountNature"), default="not_declared")
    method_state = (
        "existing_local_calculation_preserved"
        if amount_nature == "local_calculation"
        else (
            "official_forecast_preserved"
            if amount_nature == "official_estimate"
            else "official_finance_value_preserved"
        )
    )
    _append_observation(
        rows,
        names=names,
        family_id="F6_VULNERABILITY_RURALITY_INCLUSION_AND_FINANCE",
        code=code,
        period=year,
        group="municipal_education_finance",
        metric_id=metric_id,
        value=value,
        unit=unit,
        source_state=source_state,
        universe="municipal_education_finance_and_execution",
        territorial_lens="municipal_executor",
        network_scope="not_applicable_financial_executor",
        source_ref=_source_ref(path, source_pointer),
        source_period=year,
        method_state=method_state,
        source_id=_token(payload.get("sourceId"), default="MUNICIPAL_FINANCE_EXPORT_RS"),
        dimension_id=_token(payload.get("financialStage"), default="ALL"),
        dimension_label=_token(payload.get("financialStage"), default="Todos"),
        formula_id="existing_finance_contract_value_preserved",
        claim_ceiling="OBSERVED_FACT",
    )


def _build_finance(rows: list[dict[str, Any]], names: Mapping[str, str]) -> None:
    for code in sorted(names):
        path = FINANCE_ROOT / code / "financeiro.json"
        if not path.is_file():
            raise FileNotFoundError(f"Contrato financeiro municipal ausente: {path}")
        payload = _json(path)
        if payload.get("municipality", {}).get("ibgeCode") != code:
            raise AdvancedPanelValidationError(f"Identidade financeira divergente: {path}")

        history = {
            int(item["referenceYear"]): item
            for item in payload.get("execution", {})
            .get("dcaEducation", {})
            .get("history", [])
        }
        for year in (2024, 2025):
            item = history.get(year, {})
            for field, metric_id, unit in (
                ("committed", "finance.education_committed", "BRL"),
                ("liquidated", "finance.education_liquidated", "BRL"),
                ("paid", "finance.education_paid", "BRL"),
            ):
                _finance_measure(
                    rows,
                    names=names,
                    code=code,
                    path=path,
                    source_pointer=f"execution.dcaEducation.history[{year}].{field}",
                    metric_id=metric_id,
                    measure=item.get(field),
                    default_year=year,
                    default_unit=unit,
                )
            derived = item.get("derivedRates", {})
            for field, metric_id in (
                ("liquidatedToCommittedRate", "finance.liquidated_to_committed_rate"),
                ("paidToCommittedRate", "finance.paid_to_committed_rate"),
                ("paidToLiquidatedRate", "finance.paid_to_liquidated_rate"),
            ):
                _finance_measure(
                    rows,
                    names=names,
                    code=code,
                    path=path,
                    source_pointer=(
                        f"execution.dcaEducation.history[{year}].derivedRates.{field}"
                    ),
                    metric_id=metric_id,
                    measure=derived.get(field),
                    default_year=year,
                    default_unit="percent",
                )

        mde_history = {
            int(item["referenceYear"]): item
            for item in payload.get("constitutionalApplication", {}).get(
                "mdeRateHistory", []
            )
        }
        for year in (2024, 2025):
            item = mde_history.get(year, {})
            for field, metric_id in (
                ("rate", "finance.mde_applied_rate"),
                ("marginFromMinimum", "finance.mde_margin_from_minimum"),
            ):
                _finance_measure(
                    rows,
                    names=names,
                    code=code,
                    path=path,
                    source_pointer=f"constitutionalApplication.mdeRateHistory[{year}].{field}",
                    metric_id=metric_id,
                    measure=item.get(field),
                    default_year=year,
                    default_unit="percent",
                )

        fixed_measures = (
            (
                "amounts.fundebTotalAnnualForecast",
                "finance.fundeb_total_annual_forecast",
                payload.get("amounts", {}).get("fundebTotalAnnualForecast"),
                2026,
                "BRL",
            ),
            (
                "amounts.qseDistributedClosedYear",
                "finance.qse_distributed_closed_year",
                payload.get("amounts", {}).get("qseDistributedClosedYear"),
                2024,
                "BRL",
            ),
            (
                "amounts.qseOfficialEstimateCurrentYear",
                "finance.qse_official_estimate_current_year",
                payload.get("amounts", {}).get("qseOfficialEstimateCurrentYear"),
                2026,
                "BRL",
            ),
            (
                "qse.enrollmentsClosedYear",
                "finance.qse_enrollments_closed_year",
                payload.get("qse", {}).get("enrollmentsClosedYear"),
                2024,
                "count",
            ),
            (
                "perStudent.qseDistributedPerEnrollment",
                "finance.qse_distributed_per_enrollment",
                payload.get("perStudent", {}).get("qseDistributedPerEnrollment"),
                2024,
                "BRL_per_student",
            ),
            (
                "constitutionalApplication.mdeAppliedAmount.canonical",
                "finance.mde_applied_amount",
                payload.get("constitutionalApplication", {})
                .get("mdeAppliedAmount", {})
                .get("canonical"),
                2025,
                "BRL",
            ),
            (
                "constitutionalApplication.fundebProfessionalRemunerationRate.canonical",
                "finance.fundeb_professional_remuneration_rate",
                payload.get("constitutionalApplication", {})
                .get("fundebProfessionalRemunerationRate", {})
                .get("canonical"),
                2025,
                "percent",
            ),
            (
                "constitutionalApplication.fundebRevenueReceivedDeclared",
                "finance.fundeb_revenue_received_declared",
                payload.get("constitutionalApplication", {}).get(
                    "fundebRevenueReceivedDeclared"
                ),
                2025,
                "BRL",
            ),
        )
        for pointer, metric_id, measure, year, unit in fixed_measures:
            _finance_measure(
                rows,
                names=names,
                code=code,
                path=path,
                source_pointer=pointer,
                metric_id=metric_id,
                measure=measure,
                default_year=year,
                default_unit=unit,
            )


def _build_f6(rows: list[dict[str, Any]], names: Mapping[str, str]) -> None:
    rural_path = REGIONAL_SOURCE_PATHS["JOB5GBR_RURAL_VALE"]
    rural = _municipal_rows(_read_csv(rural_path))
    for record in rural.to_dict("records"):
        _append_observation(
            rows,
            names=names,
            family_id="F6_VULNERABILITY_RURALITY_INCLUSION_AND_FINANCE",
            code=record["municipality_ibge_code"],
            period=record["year"],
            group=record["stage"],
            metric_id=f"education.rural.{record['metric']}",
            value=record["value"],
            unit=_token(record["unit"], default="unresolved_unit"),
            source_state=record["value_status"],
            universe="located_rural_school_offer_total_all_dependencies",
            territorial_lens="rural_school_location",
            network_scope="total_all_dependencies",
            source_ref=_source_ref(rural_path, "value"),
            source_period=record["year"],
            method_state="source_rural_offer_value_preserved",
            source_id="JOB5GBR_RURAL_VALE",
            claim_ceiling="PLANNING_SIGNAL",
        )

    aee_path = REGIONAL_SOURCE_PATHS["JOB5GBR_AEE_VALE"]
    aee = _municipal_rows(_read_csv(aee_path))
    for record in aee.to_dict("records"):
        _append_observation(
            rows,
            names=names,
            family_id="F6_VULNERABILITY_RURALITY_INCLUSION_AND_FINANCE",
            code=record["municipality_ibge_code"],
            period=record["year"],
            group=record["stage"],
            metric_id=f"education.special_aee.{record['metric']}",
            value=record["value"],
            unit=_token(record["unit"], default="unresolved_unit"),
            source_state=record["value_status"],
            universe="special_education_and_aee_at_school_location",
            territorial_lens="school_location",
            network_scope="total_all_dependencies",
            source_ref=_source_ref(aee_path, "value"),
            source_period=record["year"],
            method_state="source_inclusion_value_preserved",
            source_id="JOB5GBR_AEE_VALE",
            claim_ceiling="PLANNING_SIGNAL",
        )

    vulnerability_path = REGIONAL_SOURCE_PATHS["JOB5GBR_VULNERABILITY_VALE"]
    vulnerability = _municipal_rows(_read_csv(vulnerability_path))
    for record in vulnerability.to_dict("records"):
        _append_observation(
            rows,
            names=names,
            family_id="F6_VULNERABILITY_RURALITY_INCLUSION_AND_FINANCE",
            code=record["municipality_ibge_code"],
            period=record["reference_period"],
            group=record["context_domain"],
            metric_id=f"social.vulnerability.{record['metric']}",
            dimension_id=record["object_id"],
            dimension_label=record["metric_family"],
            value=record["value"],
            unit=_token(record["unit_of_observation"], default="unresolved_unit"),
            source_state=record["value_status"],
            universe="registered_vulnerability_source_population_or_families",
            territorial_lens="registered_residence_or_source_declared_municipality",
            network_scope="not_applicable",
            source_ref=_source_ref(vulnerability_path, "value"),
            source_period=record["reference_period"],
            method_state="source_registered_context_value_preserved",
            source_id="JOB5GBR_VULNERABILITY_VALE",
            claim_ceiling="PLANNING_SIGNAL",
        )

    _build_finance(rows, names)


def build_panel() -> pd.DataFrame:
    _, names, _ = _registries()
    rows: list[dict[str, Any]] = []
    _build_f1(rows, names)
    _build_f2(rows, names)
    _build_f3(rows, names)
    _build_f4(rows, names)
    _build_f5(rows, names)
    _build_f6(rows, names)
    frame = pd.DataFrame(rows, columns=PANEL_COLUMNS)
    return _stable_frame(frame, UNIQUE_KEY)


def _file_record(path: Path, *, kind: str) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Entrada AA1 ausente: {path}")
    return {
        "path": _relative(path),
        "kind": kind,
        "byteSize": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def build_source_inventory(public_data_digest: str | None = None) -> dict[str, Any]:
    records = [
        _file_record(CONTRACT_PATH, kind="contract"),
        _file_record(MUNICIPALITY_REGISTRY_PATH, kind="identity_registry"),
        _file_record(REGION_REGISTRY_PATH, kind="region_registry"),
        _file_record(AA0_MANIFEST_PATH, kind="protected_baseline"),
    ]
    state_manifest_path = STATE_SOURCE_ROOT / "manifest.json"
    state_manifest = _json(state_manifest_path)
    records.append(_file_record(state_manifest_path, kind="source_manifest"))
    for artifact in state_manifest["artifacts"]:
        path = STATE_SOURCE_ROOT / artifact["path"]
        record = _file_record(path, kind="frozen_state_source")
        if (
            record["byteSize"] != artifact["byteSize"]
            or record["sha256"] != artifact["sha256"]
        ):
            raise AdvancedPanelValidationError(
                f"Snapshot estadual divergiu do manifesto: {artifact['path']}"
            )
        records.append(record)
    records.append(_file_record(RAIS_SOURCE_PATH, kind="frozen_vale_source"))
    for path in REGIONAL_SOURCE_PATHS.values():
        records.append(_file_record(path, kind="frozen_vale_source"))

    codes, _, _ = _registries()
    finance_paths = [FINANCE_ROOT / code / "financeiro.json" for code in codes]
    records.extend(
        _file_record(path, kind="statewide_finance_source") for path in finance_paths
    )
    records = sorted(records, key=lambda item: item["path"])
    digest = public_data_digest or directory_content_digest(REPO_ROOT / "public/data")
    payload = {
        "schemaVersion": "vocacoes-pne-advanced-panel-source-inventory-v1",
        "programId": "vocacoes-pne-advanced-analytics-v1",
        "stage": "AA1",
        "generatedAt": GENERATED_AT,
        "sourceCount": len(records),
        "financeSourceCount": len(finance_paths),
        "publicDataTreeDigestSha256": digest,
        "databaseUsed": False,
        "networkUsed": False,
        "records": records,
    }
    payload["inventoryDigestSha256"] = _sha256_payload(records)
    return payload


def _validate_panel(
    panel: pd.DataFrame,
    *,
    source_inventory: Mapping[str, Any],
) -> list[dict[str, Any]]:
    codes, names, region_codes = _registries()
    all_codes = set(codes)
    region_set = set(region_codes)
    checks: list[tuple[str, bool, str]] = []

    checks.append(("QA01_REQUIRED_COLUMNS", tuple(panel.columns) == PANEL_COLUMNS, str(len(panel.columns))))
    checks.append(("QA02_NONEMPTY", len(panel) > 0, f"rows={len(panel)}"))
    code_values = panel["municipality_ibge_code"].astype(str)
    checks.append(
        (
            "QA03_IBGE_TEXT_7_DIGITS",
            code_values.map(lambda value: bool(IBGE_CODE_PATTERN.fullmatch(value))).all(),
            f"codes={code_values.nunique()}",
        )
    )
    name_match = all(
        names.get(str(code)) == name
        for code, name in zip(panel["municipality_ibge_code"], panel["municipality_name"])
    )
    checks.append(("QA04_CANONICAL_NAMES_BY_CODE", name_match, "no_name_join"))
    duplicate_count = int(panel.duplicated(list(UNIQUE_KEY), keep=False).sum())
    checks.append(("QA05_UNIQUE_GRAIN", duplicate_count == 0, f"duplicates={duplicate_count}"))
    checks.append(
        (
            "QA06_AVAILABILITY_VOCABULARY",
            set(panel["availability_state"]) <= AVAILABILITY_STATES,
            ",".join(sorted(set(panel["availability_state"]))),
        )
    )
    observed = panel["availability_state"].isin(["observed", "observed_zero"])
    checks.append(
        (
            "QA07_OBSERVED_REQUIRES_VALUE",
            panel.loc[observed, "raw_value"].notna().all(),
            f"observed_rows={int(observed.sum())}",
        )
    )
    checks.append(
        (
            "QA08_NONOBSERVED_REQUIRES_NULL",
            panel.loc[~observed, "raw_value"].isna().all(),
            f"nonobserved_rows={int((~observed).sum())}",
        )
    )
    zero_state_ok = panel.loc[panel["availability_state"].eq("observed_zero"), "raw_value"].eq(0).all()
    numeric_zero_ok = panel.loc[panel["raw_value"].eq(0), "availability_state"].eq("observed_zero").all()
    checks.append(("QA09_ZERO_SEMANTICS", bool(zero_state_ok and numeric_zero_ok), "zero_is_not_null"))

    contract = _json(CONTRACT_PATH)
    allowed_lenses = set(contract["observationContract"]["allowedTerritorialLenses"])
    allowed_network = set(contract["observationContract"]["allowedNetworkScopes"])
    allowed_coverage = set(contract["observationContract"]["allowedCoverageScopes"])
    allowed_coverage_reasons = set(
        contract["observationContract"]["allowedCoverageReasons"]
    )
    allowed_unavailability_reasons = set(
        contract["observationContract"]["allowedUnavailabilityReasons"]
    )
    allowed_reference = set(contract["observationContract"]["allowedReferenceScopes"])
    allowed_aggregation = set(
        contract["observationContract"]["allowedAggregationGuards"]
    )
    checks.append(
        (
            "QA10_LENSES_RESOLVED",
            set(panel["territorial_lens"]) <= allowed_lenses,
            ",".join(sorted(set(panel["territorial_lens"]))),
        )
    )
    checks.append(
        (
            "QA11_NETWORK_SCOPES_RESOLVED",
            set(panel["network_scope"]) <= allowed_network,
            ",".join(sorted(set(panel["network_scope"]))),
        )
    )
    unit_values = set(panel["unit"].astype(str))
    unresolved_units = {value for value in unit_values if not value or "unresolved" in value}
    checks.append(("QA12_UNITS_RESOLVED", not unresolved_units, str(sorted(unresolved_units))))
    checks.append(("QA13_SOURCE_REFS_RESOLVED", panel["source_ref"].astype(str).str.len().gt(0).all(), "all_rows"))

    family_codes = {
        family: set(group["municipality_ibge_code"].astype(str))
        for family, group in panel.groupby("family_id", sort=True)
    }
    for index, family in enumerate(
        (
            "F1_EDUCATIONAL_TRAJECTORY_AND_CONDITIONS",
            "F2_DEMOGRAPHY_ENROLLMENT_AND_OFFER",
            "F5_ADULT_SCHOOLING_AND_EJA",
            "F6_VULNERABILITY_RURALITY_INCLUSION_AND_FINANCE",
        ),
        start=14,
    ):
        observed_codes = family_codes.get(family, set())
        checks.append(
            (
                f"QA{index:02d}_{family}_STATE_497",
                observed_codes == all_codes,
                f"municipalities={len(observed_codes)}",
            )
        )
    checks.append(
        (
            "QA18_F3_VALE_10",
            family_codes.get("F3_YOUTH_WORK_AND_APPRENTICESHIP", set()) == region_set,
            f"municipalities={len(family_codes.get('F3_YOUTH_WORK_AND_APPRENTICESHIP', set()))}",
        )
    )
    checks.append(
        (
            "QA19_F4_VALE_10",
            family_codes.get("F4_OCCUPATIONS_SECTORS_AND_EPT", set()) == region_set,
            f"municipalities={len(family_codes.get('F4_OCCUPATIONS_SECTORS_AND_EPT', set()))}",
        )
    )
    nsr_families = set(panel.loc[panel["municipality_ibge_code"].eq(NSR_CODE), "family_id"])
    checks.append(("QA20_NSR_ALL_SIX_FAMILIES", len(nsr_families) == 6, f"families={len(nsr_families)}"))
    checks.append(
        (
            "QA21_FINANCE_497_FILES",
            source_inventory["financeSourceCount"] == 497,
            f"files={source_inventory['financeSourceCount']}",
        )
    )
    checks.append(
        (
            "QA22_PUBLIC_DATA_FROZEN",
            source_inventory["publicDataTreeDigestSha256"] == EXPECTED_PUBLIC_DATA_DIGEST,
            source_inventory["publicDataTreeDigestSha256"],
        )
    )
    checks.append(("QA23_NO_DATABASE", source_inventory["databaseUsed"] is False, "false"))
    checks.append(("QA24_NO_NETWORK", source_inventory["networkUsed"] is False, "false"))
    education_rows = panel["metric_id"].astype(str).str.startswith("education.")
    education_network_ok = panel.loc[education_rows, "network_scope"].eq(
        "total_all_dependencies"
    ).all()
    noneducation_network_ok = ~panel.loc[
        ~education_rows, "network_scope"
    ].eq("total_all_dependencies").any()
    checks.append(
        (
            "QA25_TOTAL_ALL_DEPENDENCIES_ONLY_FOR_EDUCATION",
            bool(education_network_ok and noneducation_network_ok),
            f"education_rows={int(education_rows.sum())};dependency_strata=0",
        )
    )
    checks.append(
        (
            "QA26_COVERAGE_SCOPES_RESOLVED",
            set(panel["coverage_scope"]) <= allowed_coverage == COVERAGE_SCOPES,
            ",".join(sorted(set(panel["coverage_scope"]))),
        )
    )
    checks.append(
        (
            "QA27_REFERENCE_SCOPES_RESOLVED",
            set(panel["reference_scope"]) <= allowed_reference == REFERENCE_SCOPES,
            ",".join(sorted(set(panel["reference_scope"]))),
        )
    )
    checks.append(
        (
            "QA28_AGGREGATION_GUARDS_RESOLVED",
            set(panel["aggregation_guard"])
            <= allowed_aggregation
            == AGGREGATION_GUARDS,
            ",".join(sorted(set(panel["aggregation_guard"]))),
        )
    )

    metric_coverage_failures: list[str] = []
    for (family_id, metric_id), group in panel.groupby(
        ["family_id", "metric_id"], sort=True
    ):
        scopes = set(group["coverage_scope"].astype(str))
        if len(scopes) != 1:
            metric_coverage_failures.append(f"{family_id}/{metric_id}:scopes={scopes}")
            continue
        scope = next(iter(scopes))
        expected_codes = all_codes if scope == "RS_497" else region_set
        observed_metric_codes = set(group["municipality_ibge_code"].astype(str))
        if observed_metric_codes != expected_codes:
            metric_coverage_failures.append(
                f"{family_id}/{metric_id}:{scope}="
                f"{len(observed_metric_codes)}/{len(expected_codes)}"
            )
    checks.append(
        (
            "QA29_METRIC_COVERAGE_EXACT",
            not metric_coverage_failures,
            ";".join(metric_coverage_failures[:5]) or "96_metrics_exact",
        )
    )

    shift_metric_ids = set(SHIFT_SHARE_METRICS.values())
    shift_rows = panel["metric_id"].isin(shift_metric_ids)
    reference_rows = panel["reference_scope"].ne("NO_EXTERNAL_REFERENCE")
    permitted_shift_fields = set(SHIFT_SHARE_METRICS)
    emitted_shift_fields = set(
        panel.loc[shift_rows, "source_ref"].astype(str).str.rsplit("#", n=1).str[-1]
    )
    forbidden_state_total = panel["metric_id"].astype(str).str.contains(
        r"state_total|reference_total|rs_total", case=False, regex=True
    ).any() or panel["source_ref"].astype(str).str.contains(
        r"state_sector|reference_total|rs_total", case=False, regex=True
    ).any()
    reference_fence_ok = (
        bool((reference_rows == shift_rows).all())
        and panel.loc[shift_rows, "family_id"]
        .eq("F4_OCCUPATIONS_SECTORS_AND_EPT")
        .all()
        and panel.loc[shift_rows, "source_id"]
        .eq("JOB5GCR_SHIFT_SHARE_VALE_RS")
        .all()
        and panel.loc[shift_rows, "method_state"]
        .eq("source_accounting_decomposition_preserved")
        .all()
        and panel.loc[shift_rows, "coverage_scope"].eq("VALE_10").all()
        and panel.loc[shift_rows, "aggregation_guard"]
        .eq("DO_NOT_AGGREGATE_AS_RS_TOTAL")
        .all()
        and emitted_shift_fields == permitted_shift_fields
        and not forbidden_state_total
    )
    checks.append(
        (
            "QA30_RS_REFERENCE_COMPONENTS_FENCED",
            bool(reference_fence_ok),
            "municipal_components_only;state_totals_not_emitted",
        )
    )

    f3 = panel[panel["family_id"].eq("F3_YOUTH_WORK_AND_APPRENTICESHIP")]
    f3_units = set(f3["unit"].astype(str))
    f4_stock = panel[
        panel["family_id"].eq("F4_OCCUPATIONS_SECTORS_AND_EPT")
        & panel["metric_id"].astype(str).str.startswith("labor.")
    ]
    f4_source_ids = {
        "JOB5GCR_OCCUPATIONS_VALE",
        "JOB5GCR_SECTORS_VALE",
        "JOB5GCR_SHIFT_SHARE_VALE_RS",
    }
    rais_stock_ok = (
        f3["metric_id"].astype(str).str.startswith("labor.youth_rais.").all()
        and f3["universe"]
        .astype(str)
        .str.fullmatch(r"active_formal_bonds_age_(15_17|18_24)_at_31_12")
        .all()
        and f3["territorial_lens"].eq("establishment_location_workplace").all()
        and f3["source_id"].eq("JOB5L_FINAL_RAIS_VALE").all()
        and f3_units
        <= {"active_bonds", "percent", "months", "hours_per_week", "BRL_nominal"}
        and len(f4_stock) == 22_141
        and f4_stock["universe"].eq("active_formal_bonds_all_ages_at_31_12").all()
        and f4_stock["territorial_lens"].eq("workplace").all()
        and f4_stock["unit"].eq("active_bonds").all()
        and set(f4_stock["source_id"].astype(str)) <= f4_source_ids
    )
    checks.append(
        (
            "QA31_RAIS_ACTIVE_STOCK_SEMANTICS",
            bool(rais_stock_ok),
            f"f3_rows={len(f3)};f4_rows={len(f4_stock)};"
            f"f3_units={','.join(sorted(f3_units))}",
        )
    )
    caged_hits = panel[
        ["metric_id", "universe", "source_ref", "source_id", "formula_id"]
    ].astype(str).apply(
        lambda column: column.str.contains("caged", case=False, regex=False)
    ).any(axis=1)
    checks.append(
        (
            "QA32_NO_CAGED_FLOW_SEMANTICS",
            not caged_hits.any(),
            f"caged_rows={int(caged_hits.sum())}",
        )
    )

    denominator_zero = panel["denominator"].eq(0)
    denominator_zero_ok = (
        panel.loc[denominator_zero, "raw_value"].isna().all()
        and ~panel.loc[denominator_zero, "availability_state"]
        .isin(["observed", "observed_zero"])
        .any()
    )
    checks.append(
        (
            "QA33_DENOMINATOR_ZERO_IS_NULL",
            bool(denominator_zero_ok),
            f"denominator_zero_rows={int(denominator_zero.sum())}",
        )
    )

    coverage_reason_ok = (
        set(panel["coverage_reason"]) <= allowed_coverage_reasons == COVERAGE_REASONS
        and panel.loc[panel["coverage_scope"].eq("RS_497"), "coverage_reason"]
        .eq("STATEWIDE_SOURCE_AVAILABLE")
        .all()
        and panel.loc[panel["coverage_scope"].eq("VALE_10"), "coverage_reason"]
        .eq("FROZEN_ANALYTICAL_SOURCE_RESTRICTED_TO_VALE_10")
        .all()
    )
    checks.append(
        (
            "QA34_COVERAGE_REASON_CLOSED_AND_COMPLETE",
            bool(coverage_reason_ok),
            ",".join(sorted(set(panel["coverage_reason"]))),
        )
    )

    grain_reconciliation = _build_grain_reconciliation(panel)
    checks.append(
        (
            "QA35_SOURCE_TO_OUTPUT_GRAIN_RECONCILED",
            grain_reconciliation["totalDeltaRows"] == 0
            and grain_reconciliation["allSourceLedgersReconciled"] is True
            and grain_reconciliation["allMetricsReconciled"] is True,
            f"sources={grain_reconciliation['sourceLedgerCount']};"
            f"metrics={grain_reconciliation['metricCount']};delta=0",
        )
    )

    temporal_audit = _build_temporal_audit(panel)
    checks.append(
        (
            "QA36_TEMPORAL_PATTERNS_DECLARED",
            temporal_audit["metricCount"] == panel["metric_id"].nunique()
            and temporal_audit["unresolvedTemporalPatternCount"] == 0,
            ";".join(
                f"{state}={count}"
                for state, count in temporal_audit["auditStateCounts"].items()
            ),
        )
    )

    shift = panel[shift_rows].copy()
    shift["component"] = shift["metric_id"].map(
        {metric_id: field for field, metric_id in SHIFT_SHARE_METRICS.items()}
    )
    shift_values = shift.pivot(
        index=[
            "municipality_ibge_code",
            "year_or_reference_period",
            "stage_or_population_group",
            "dimension_id",
        ],
        columns="component",
        values="raw_value",
    )
    complete_shift = shift_values.notna().all(axis=1)
    closure_delta = (
        shift_values.loc[complete_shift, "absolute_change"]
        - shift_values.loc[complete_shift, "reference_growth_effect"]
        - shift_values.loc[complete_shift, "industry_mix_effect"]
        - shift_values.loc[complete_shift, "local_differential_effect"]
        - shift_values.loc[complete_shift, "closure_residual"]
    ).abs()
    incomplete_shift = shift_values.loc[~complete_shift]
    incomplete_pattern_ok = (
        incomplete_shift["absolute_change"].notna().all()
        and incomplete_shift[
            [
                "reference_growth_effect",
                "industry_mix_effect",
                "local_differential_effect",
                "closure_residual",
            ]
        ]
        .isna()
        .all(axis=None)
    )
    closure_ok = (
        len(shift_values) == 661
        and int(complete_shift.sum()) == 622
        and bool(closure_delta.le(1e-9).all())
        and bool(incomplete_pattern_ok)
    )
    checks.append(
        (
            "QA37_SHIFT_SHARE_ACCOUNTING_CLOSURE",
            bool(closure_ok),
            f"complete={int(complete_shift.sum())};"
            f"incomplete={int((~complete_shift).sum())};"
            f"max_abs_delta={float(closure_delta.max())}",
        )
    )

    required_metadata = [
        field
        for field in contract["observationContract"]["requiredFields"]
        if field != "raw_value"
    ]
    metadata_ok = panel[required_metadata].notna().all(axis=None)
    checks.append(
        (
            "QA38_REQUIRED_METADATA_NON_NULL",
            bool(metadata_ok),
            f"fields={len(required_metadata)};rows={len(panel)}",
        )
    )

    unit_counts = panel.groupby(["family_id", "metric_id"])["unit"].nunique()
    checks.append(
        (
            "QA39_ONE_UNIT_PER_FAMILY_METRIC",
            bool(unit_counts.le(1).all()),
            f"family_metrics={len(unit_counts)};multi_unit={int(unit_counts.gt(1).sum())}",
        )
    )

    available_rows = panel["availability_state"].isin(["observed", "observed_zero"])
    unavailable_reason_ok = (
        set(panel["unavailability_reason"])
        <= allowed_unavailability_reasons
        == UNAVAILABILITY_REASONS
        and panel.loc[available_rows, "unavailability_reason"]
        .eq("VALUE_AVAILABLE")
        .all()
        and set(
            panel.loc[
                panel["availability_state"].eq("unavailable"),
                "unavailability_reason",
            ]
        )
        <= {
            "SOURCE_DECLARED_UNAVAILABLE",
            "SOURCE_VALUE_MISSING",
            "REFERENCE_COMPONENT_UNAVAILABLE_ZERO_BASE",
            "DENOMINATOR_ZERO",
        }
        and panel.loc[panel["availability_state"].eq("suppressed"), "unavailability_reason"]
        .eq("SOURCE_SUPPRESSED")
        .all()
        and panel.loc[
            panel["availability_state"].eq("not_applicable"),
            "unavailability_reason",
        ]
        .eq("SOURCE_NOT_APPLICABLE")
        .all()
        and panel.loc[denominator_zero, "unavailability_reason"]
        .eq("DENOMINATOR_ZERO")
        .all()
    )
    availability_census = _build_availability_census(panel)
    checks.append(
        (
            "QA40_UNAVAILABILITY_REASONS_RECONCILED",
            bool(
                unavailable_reason_ok
                and availability_census["unavailableRowsReconciled"] is True
            ),
            ";".join(
                f"{reason}={count}"
                for reason, count in availability_census[
                    "unavailabilityReasonCounts"
                ].items()
            ),
        )
    )

    aa2_gate = _build_aa2_entry_gate(panel, source_inventory)
    checks.append(
        (
            "QA41_AA2_FAIL_CLOSED_ENTRY_GATE_COMPLETE",
            aa2_gate["resultInspectionAllowedBeforeGatePass"] is False
            and len(aa2_gate["failClosedRequiredRowFields"]) == 5
            and aa2_gate["statewideInferencePolicy"][
                "allowedOnlyWhenCoverageScope"
            ]
            == "RS_497",
            "preregistration_only;five_required_fields;statewide_only_rs_497",
        )
    )

    results = [
        {"checkId": check_id, "passed": bool(passed), "details": details}
        for check_id, passed, details in checks
    ]
    failures = [result for result in results if not result["passed"]]
    if failures:
        raise AdvancedPanelValidationError(f"QA AA1 falhou: {failures}")
    return results


def _build_catalog(panel: pd.DataFrame) -> dict[str, Any]:
    metrics = []
    group_fields = [
        "family_id",
        "metric_id",
        "unit",
        "universe",
        "territorial_lens",
        "network_scope",
        "coverage_scope",
        "coverage_reason",
        "reference_scope",
        "aggregation_guard",
        "method_state",
        "formula_id",
        "claim_ceiling",
    ]
    for keys, group in panel.groupby(group_fields, sort=True, dropna=False):
        record = dict(zip(group_fields, keys))
        source_refs = sorted(set(group["source_ref"].astype(str)))
        availability = Counter(group["availability_state"].astype(str))
        periods = sorted(set(group["year_or_reference_period"].astype(str)))
        metrics.append(
            {
                "familyId": record["family_id"],
                "metricId": record["metric_id"],
                "label": record["metric_id"].replace(".", " · ").replace("_", " "),
                "unit": record["unit"],
                "universe": record["universe"],
                "territorialLens": record["territorial_lens"],
                "networkScope": record["network_scope"],
                "coverageScope": record["coverage_scope"],
                "coverageReason": record["coverage_reason"],
                "referenceScope": record["reference_scope"],
                "aggregationGuard": record["aggregation_guard"],
                "methodState": record["method_state"],
                "formulaId": record["formula_id"],
                "claimCeiling": record["claim_ceiling"],
                "rowCount": len(group),
                "municipalityCount": group["municipality_ibge_code"].nunique(),
                "periodCount": len(periods),
                "periodStart": periods[0],
                "periodEnd": periods[-1],
                "availabilityCounts": dict(sorted(availability.items())),
                "sourceRefCount": len(source_refs),
                "sourceRefSample": source_refs[:3],
            }
        )
    return {
        "schemaVersion": "vocacoes-pne-advanced-panel-metric-catalog-v1",
        "programId": "vocacoes-pne-advanced-analytics-v1",
        "stage": "AA1",
        "generatedAt": GENERATED_AT,
        "metricContractCount": len(metrics),
        "metrics": metrics,
    }


def _build_coverage(panel: pd.DataFrame) -> dict[str, Any]:
    contract = _json(CONTRACT_PATH)
    family_contracts = {item["familyId"]: item for item in contract["families"]}
    families = []
    for family_id, group in panel.groupby("family_id", sort=True):
        metric_coverage = []
        for metric_id, metric_group in group.groupby("metric_id", sort=True):
            metric_coverage.append(
                {
                    "metricId": metric_id,
                    "rowCount": len(metric_group),
                    "municipalityCount": metric_group["municipality_ibge_code"].nunique(),
                    "coverageScopes": sorted(
                        set(metric_group["coverage_scope"].astype(str))
                    ),
                    "coverageReasons": sorted(
                        set(metric_group["coverage_reason"].astype(str))
                    ),
                    "referenceScopes": sorted(
                        set(metric_group["reference_scope"].astype(str))
                    ),
                    "aggregationGuards": sorted(
                        set(metric_group["aggregation_guard"].astype(str))
                    ),
                    "networkScopeCounts": dict(
                        sorted(Counter(metric_group["network_scope"]).items())
                    ),
                    "observedCount": int(
                        metric_group["availability_state"].isin(
                            ["observed", "observed_zero"]
                        ).sum()
                    ),
                    "unavailableCount": int(
                        metric_group["availability_state"].eq("unavailable").sum()
                    ),
                }
            )
        families.append(
            {
                "familyId": family_id,
                "coverageClass": family_contracts[family_id]["coverageClass"],
                "partialCoverageReason": family_contracts[family_id].get(
                    "partialCoverageReason"
                ),
                "rowCount": len(group),
                "municipalityCount": group["municipality_ibge_code"].nunique(),
                "metricCount": group["metric_id"].nunique(),
                "territorialLenses": sorted(set(group["territorial_lens"])),
                "networkScopes": sorted(set(group["network_scope"])),
                "networkScopeCounts": dict(
                    sorted(Counter(group["network_scope"]).items())
                ),
                "coverageScopes": sorted(set(group["coverage_scope"])),
                "coverageReasons": sorted(set(group["coverage_reason"])),
                "referenceScopes": sorted(set(group["reference_scope"])),
                "aggregationGuards": sorted(set(group["aggregation_guard"])),
                "availabilityCounts": dict(
                    sorted(Counter(group["availability_state"]).items())
                ),
                "metricCoverage": metric_coverage,
            }
        )
    _, _, region_codes = _registries()
    return {
        "schemaVersion": "vocacoes-pne-advanced-panel-coverage-v1",
        "programId": "vocacoes-pne-advanced-analytics-v1",
        "stage": "AA1",
        "generatedAt": GENERATED_AT,
        "rowEmissionPolicy": contract["observationContract"]["rowEmissionPolicy"],
        "absentRowMeaning": contract["observationContract"]["absentRowMeaning"],
        "panelScopeLabel": contract["scope"]["panelScopeLabel"],
        "panelFile": PANEL_FILE,
        "manifestFile": MANIFEST_FILE,
        "valeMunicipalityRegistry": {
            "regionId": contract["scope"]["regionId"],
            "registryPath": _relative(REGION_REGISTRY_PATH),
            "registrySha256": sha256_file(REGION_REGISTRY_PATH),
            "municipalityIbgeCodes": sorted(region_codes),
        },
        "familyCount": len(families),
        "families": families,
    }


def _build_grain_reconciliation(panel: pd.DataFrame) -> dict[str, Any]:
    expected: Counter[tuple[str, str]] = Counter()
    ledgers: list[dict[str, Any]] = []

    def add_ledger(
        *,
        source_id: str,
        path: Path,
        family_id: str,
        raw_rows: int,
        municipal_rows: int,
        metric_ids: Sequence[str],
        expected_output_rows: int,
        rule: str,
    ) -> None:
        emitted_rows = int(
            panel[
                panel["family_id"].eq(family_id)
                & panel["metric_id"].isin(metric_ids)
            ].shape[0]
        )
        ledgers.append(
            {
                "sourceId": source_id,
                "sourcePath": _relative(path),
                "familyId": family_id,
                "rawSourceRows": raw_rows,
                "municipalSourceRows": municipal_rows,
                "metricIds": sorted(metric_ids),
                "expansionRule": rule,
                "expectedOutputRows": expected_output_rows,
                "emittedOutputRows": emitted_rows,
                "deltaRows": emitted_rows - expected_output_rows,
            }
        )

    trajectory_path = STATE_SOURCE_ROOT / "trajectory_total_network.csv.gz"
    trajectory = _read_csv(trajectory_path)
    trajectory_metrics: list[str] = []
    for outcome_id, count in trajectory["outcome_id"].value_counts().items():
        metric_id = f"education.{outcome_id}"
        trajectory_metrics.append(metric_id)
        expected[("F1_EDUCATIONAL_TRAJECTORY_AND_CONDITIONS", metric_id)] += int(count)
    add_ledger(
        source_id="JOB5L_FROZEN_STATE_CONTEXT_TRAJECTORY",
        path=trajectory_path,
        family_id="F1_EDUCATIONAL_TRAJECTORY_AND_CONDITIONS",
        raw_rows=len(trajectory),
        municipal_rows=len(trajectory),
        metric_ids=trajectory_metrics,
        expected_output_rows=len(trajectory),
        rule="ONE_OUTPUT_PER_SOURCE_ROW_BY_OUTCOME_ID",
    )

    adequacy_path = STATE_SOURCE_ROOT / "teacher_adequacy_total_network.csv.gz"
    adequacy = _read_csv(adequacy_path)
    expected[("F1_EDUCATIONAL_TRAJECTORY_AND_CONDITIONS", "education.teacher_adequacy_percent")] += len(adequacy)
    add_ledger(
        source_id="JOB5L_FROZEN_STATE_CONTEXT_TEACHER_ADEQUACY",
        path=adequacy_path,
        family_id="F1_EDUCATIONAL_TRAJECTORY_AND_CONDITIONS",
        raw_rows=len(adequacy),
        municipal_rows=len(adequacy),
        metric_ids=["education.teacher_adequacy_percent"],
        expected_output_rows=len(adequacy),
        rule="ONE_OUTPUT_PER_SOURCE_ROW",
    )

    inse_path = STATE_SOURCE_ROOT / "inse_total_network.csv.gz"
    inse = _read_csv(inse_path)
    inse_metrics = ["education.inse_value", "education.inse_assessed_students"]
    for metric_id in inse_metrics:
        expected[("F1_EDUCATIONAL_TRAJECTORY_AND_CONDITIONS", metric_id)] += len(inse)
    add_ledger(
        source_id="JOB5L_FROZEN_STATE_CONTEXT_INSE",
        path=inse_path,
        family_id="F1_EDUCATIONAL_TRAJECTORY_AND_CONDITIONS",
        raw_rows=len(inse),
        municipal_rows=len(inse),
        metric_ids=inse_metrics,
        expected_output_rows=len(inse) * 2,
        rule="TWO_NAMED_FIELDS_PER_SOURCE_ROW",
    )

    population_path = STATE_SOURCE_ROOT / "population_context.csv.gz"
    population = _read_csv(population_path)
    population_metrics = [
        "demography.total_population",
        "demography.population_age_6_10",
        "demography.population_age_11_14",
        "demography.population_age_15_17",
        "demography.population_age_18_24",
    ]
    for metric_id in population_metrics:
        expected[("F2_DEMOGRAPHY_ENROLLMENT_AND_OFFER", metric_id)] += len(population)
    add_ledger(
        source_id="JOB5L_FROZEN_STATE_CONTEXT_POPULATION",
        path=population_path,
        family_id="F2_DEMOGRAPHY_ENROLLMENT_AND_OFFER",
        raw_rows=len(population),
        municipal_rows=len(population),
        metric_ids=population_metrics,
        expected_output_rows=len(population) * 5,
        rule="FIVE_NAMED_FIELDS_PER_SOURCE_ROW",
    )

    school_path = STATE_SOURCE_ROOT / "school_context.csv.gz"
    school = _read_csv(school_path)
    school_metric_multipliers = {
        "education.enrollments": 4,
        "education.full_time_enrollments": 4,
        "education.rural_basic_enrollments": 1,
        "education.school_count": 1,
        "education.schools_with_internet": 1,
    }
    for metric_id, multiplier in school_metric_multipliers.items():
        expected[("F2_DEMOGRAPHY_ENROLLMENT_AND_OFFER", metric_id)] += len(school) * multiplier
    add_ledger(
        source_id="JOB5L_FROZEN_STATE_CONTEXT_SCHOOL",
        path=school_path,
        family_id="F2_DEMOGRAPHY_ENROLLMENT_AND_OFFER",
        raw_rows=len(school),
        municipal_rows=len(school),
        metric_ids=list(school_metric_multipliers),
        expected_output_rows=len(school) * 11,
        rule="ELEVEN_NAMED_STAGE_AND_OFFER_FIELDS_PER_SOURCE_ROW",
    )

    rais_raw = _read_csv(RAIS_SOURCE_PATH)
    rais = _municipal_rows(rais_raw)
    rais_metrics: list[str] = []
    for source_metric, count in rais["metric_id"].value_counts().items():
        metric_id = f"labor.youth_rais.{source_metric}"
        rais_metrics.append(metric_id)
        expected[("F3_YOUTH_WORK_AND_APPRENTICESHIP", metric_id)] += int(count)
    add_ledger(
        source_id="JOB5L_FINAL_RAIS_VALE",
        path=RAIS_SOURCE_PATH,
        family_id="F3_YOUTH_WORK_AND_APPRENTICESHIP",
        raw_rows=len(rais_raw),
        municipal_rows=len(rais),
        metric_ids=rais_metrics,
        expected_output_rows=len(rais),
        rule="ONE_OUTPUT_PER_MUNICIPAL_SOURCE_ROW_BY_METRIC_ID",
    )

    ept_path = REGIONAL_SOURCE_PATHS["JOB5GCR_EPT_VALE"]
    ept_raw = _read_csv(ept_path)
    ept = _municipal_rows(ept_raw)
    ept_metrics = ["education.ept_technical_enrollments", "education.ept_class_count"]
    for metric_id in ept_metrics:
        expected[("F4_OCCUPATIONS_SECTORS_AND_EPT", metric_id)] += len(ept)
    add_ledger(
        source_id="JOB5GCR_EPT_VALE",
        path=ept_path,
        family_id="F4_OCCUPATIONS_SECTORS_AND_EPT",
        raw_rows=len(ept_raw),
        municipal_rows=len(ept),
        metric_ids=ept_metrics,
        expected_output_rows=len(ept) * 2,
        rule="TWO_NAMED_FIELDS_PER_MUNICIPAL_SOURCE_ROW",
    )

    for source_id, metric_id in (
        ("JOB5GCR_OCCUPATIONS_VALE", "labor.occupation_active_bonds"),
        ("JOB5GCR_SECTORS_VALE", "labor.sector_active_bonds"),
    ):
        path = REGIONAL_SOURCE_PATHS[source_id]
        raw = _read_csv(path)
        municipal = _municipal_rows(raw)
        expected[("F4_OCCUPATIONS_SECTORS_AND_EPT", metric_id)] += len(municipal) * 2
        add_ledger(
            source_id=source_id,
            path=path,
            family_id="F4_OCCUPATIONS_SECTORS_AND_EPT",
            raw_rows=len(raw),
            municipal_rows=len(municipal),
            metric_ids=[metric_id],
            expected_output_rows=len(municipal) * 2,
            rule="INITIAL_AND_FINAL_ENDPOINT_PER_MUNICIPAL_SOURCE_ROW",
        )

    shift_path = REGIONAL_SOURCE_PATHS["JOB5GCR_SHIFT_SHARE_VALE_RS"]
    shift = _read_csv(shift_path)
    for metric_id in SHIFT_SHARE_METRICS.values():
        expected[("F4_OCCUPATIONS_SECTORS_AND_EPT", metric_id)] += len(shift)
    add_ledger(
        source_id="JOB5GCR_SHIFT_SHARE_VALE_RS",
        path=shift_path,
        family_id="F4_OCCUPATIONS_SECTORS_AND_EPT",
        raw_rows=len(shift),
        municipal_rows=len(shift),
        metric_ids=list(SHIFT_SHARE_METRICS.values()),
        expected_output_rows=len(shift) * 5,
        rule="FIVE_ACCOUNTING_COMPONENTS_PER_SOURCE_ROW",
    )

    adult_path = STATE_SOURCE_ROOT / "adult_schooling_2022.csv.gz"
    adult = _read_csv(adult_path)
    adult_metrics = [
        "adult.fundamental_completed_count",
        "adult.high_school_completed_count",
        "adult.population_count",
        "adult.fundamental_completion_share_percent",
        "adult.high_school_completion_share_percent",
    ]
    for metric_id in adult_metrics:
        expected[("F5_ADULT_SCHOOLING_AND_EJA", metric_id)] += len(adult)
    add_ledger(
        source_id="JOB5L_FROZEN_STATE_CONTEXT_ADULT",
        path=adult_path,
        family_id="F5_ADULT_SCHOOLING_AND_EJA",
        raw_rows=len(adult),
        municipal_rows=len(adult),
        metric_ids=adult_metrics,
        expected_output_rows=len(adult) * 5,
        rule="FIVE_NAMED_FIELDS_PER_SOURCE_ROW",
    )

    eja_path = REGIONAL_SOURCE_PATHS["JOB5GBR_EJA_VALE"]
    eja_raw = _read_csv(eja_path)
    eja = _municipal_rows(eja_raw)
    expected[("F5_ADULT_SCHOOLING_AND_EJA", "education.eja_enrollments")] += len(eja)
    add_ledger(
        source_id="JOB5GBR_EJA_VALE",
        path=eja_path,
        family_id="F5_ADULT_SCHOOLING_AND_EJA",
        raw_rows=len(eja_raw),
        municipal_rows=len(eja),
        metric_ids=["education.eja_enrollments"],
        expected_output_rows=len(eja),
        rule="ONE_OUTPUT_PER_MUNICIPAL_SOURCE_ROW",
    )

    for source_id, prefix in (
        ("JOB5GBR_RURAL_VALE", "education.rural."),
        ("JOB5GBR_AEE_VALE", "education.special_aee."),
        ("JOB5GBR_VULNERABILITY_VALE", "social.vulnerability."),
    ):
        path = REGIONAL_SOURCE_PATHS[source_id]
        raw = _read_csv(path)
        municipal = _municipal_rows(raw)
        metric_ids = []
        for source_metric, count in municipal["metric"].value_counts().items():
            metric_id = f"{prefix}{source_metric}"
            metric_ids.append(metric_id)
            expected[("F6_VULNERABILITY_RURALITY_INCLUSION_AND_FINANCE", metric_id)] += int(count)
        add_ledger(
            source_id=source_id,
            path=path,
            family_id="F6_VULNERABILITY_RURALITY_INCLUSION_AND_FINANCE",
            raw_rows=len(raw),
            municipal_rows=len(municipal),
            metric_ids=metric_ids,
            expected_output_rows=len(municipal),
            rule="ONE_OUTPUT_PER_MUNICIPAL_SOURCE_ROW_BY_METRIC",
        )

    finance_two_year_metrics = [
        "finance.education_committed",
        "finance.education_liquidated",
        "finance.education_paid",
        "finance.liquidated_to_committed_rate",
        "finance.paid_to_committed_rate",
        "finance.paid_to_liquidated_rate",
        "finance.mde_applied_rate",
        "finance.mde_margin_from_minimum",
    ]
    finance_fixed_metrics = [
        "finance.fundeb_total_annual_forecast",
        "finance.qse_distributed_closed_year",
        "finance.qse_official_estimate_current_year",
        "finance.qse_enrollments_closed_year",
        "finance.qse_distributed_per_enrollment",
        "finance.mde_applied_amount",
        "finance.fundeb_professional_remuneration_rate",
        "finance.fundeb_revenue_received_declared",
    ]
    for metric_id in finance_two_year_metrics:
        expected[("F6_VULNERABILITY_RURALITY_INCLUSION_AND_FINANCE", metric_id)] += 497 * 2
    for metric_id in finance_fixed_metrics:
        expected[("F6_VULNERABILITY_RURALITY_INCLUSION_AND_FINANCE", metric_id)] += 497
    finance_metric_ids = finance_two_year_metrics + finance_fixed_metrics
    finance_emitted = int(panel["metric_id"].isin(finance_metric_ids).sum())
    ledgers.append(
        {
            "sourceId": "MUNICIPAL_FINANCE_EXPORT_RS",
            "sourcePath": _relative(FINANCE_ROOT) + "/<ibge_code>/financeiro.json",
            "familyId": "F6_VULNERABILITY_RURALITY_INCLUSION_AND_FINANCE",
            "rawSourceRows": 497,
            "municipalSourceRows": 497,
            "metricIds": sorted(finance_metric_ids),
            "expansionRule": "SIXTEEN_TWO_YEAR_PLUS_EIGHT_FIXED_MEASURES_PER_MUNICIPAL_CONTRACT",
            "expectedOutputRows": 497 * 24,
            "emittedOutputRows": finance_emitted,
            "deltaRows": finance_emitted - (497 * 24),
        }
    )

    actual = Counter(
        {
            (family_id, metric_id): len(group)
            for (family_id, metric_id), group in panel.groupby(
                ["family_id", "metric_id"], sort=True
            )
        }
    )
    metric_records = []
    for family_id, metric_id in sorted(set(expected) | set(actual)):
        group = panel[
            panel["family_id"].eq(family_id) & panel["metric_id"].eq(metric_id)
        ]
        municipality_rows = group.groupby("municipality_ibge_code").size()
        expected_rows = int(expected[(family_id, metric_id)])
        emitted_rows = int(actual[(family_id, metric_id)])
        metric_records.append(
            {
                "familyId": family_id,
                "metricId": metric_id,
                "coverageScope": sorted(set(group["coverage_scope"].astype(str))),
                "coverageReason": sorted(set(group["coverage_reason"].astype(str))),
                "declaredGrainPolicy": "FROZEN_SOURCE_ROWS_WITH_CODED_FIELD_EXPANSION",
                "expectedRowsFromSourceAccounting": expected_rows,
                "emittedRows": emitted_rows,
                "deltaRows": emitted_rows - expected_rows,
                "municipalityCount": group["municipality_ibge_code"].nunique(),
                "rowsPerMunicipalityMin": int(municipality_rows.min()),
                "rowsPerMunicipalityMax": int(municipality_rows.max()),
            }
        )

    family_distributions = []
    for family_id in (
        "F3_YOUTH_WORK_AND_APPRENTICESHIP",
        "F4_OCCUPATIONS_SECTORS_AND_EPT",
    ):
        family = panel[panel["family_id"].eq(family_id)]
        counts = family.groupby("municipality_ibge_code").size()
        family_distributions.append(
            {
                "familyId": family_id,
                "rowCountByMunicipalityIbgeCode": {
                    str(code): int(count) for code, count in counts.items()
                },
                "minimumRows": int(counts.min()),
                "maximumRows": int(counts.max()),
                "novaSantaRitaRows": int(counts[NSR_CODE]),
            }
        )

    return {
        "schemaVersion": "vocacoes-pne-advanced-panel-grain-reconciliation-v1",
        "programId": "vocacoes-pne-advanced-analytics-v1",
        "stage": "AA1",
        "generatedAt": GENERATED_AT,
        "rowEmissionPolicy": "SOURCE_OBSERVATION_SPARSE",
        "reconciliationMethod": "INDEPENDENT_FROZEN_SOURCE_ROW_ACCOUNTING",
        "sourceLedgerCount": len(ledgers),
        "metricCount": len(metric_records),
        "expectedTotalRows": int(sum(expected.values())),
        "emittedTotalRows": len(panel),
        "totalDeltaRows": len(panel) - int(sum(expected.values())),
        "allSourceLedgersReconciled": all(item["deltaRows"] == 0 for item in ledgers),
        "allMetricsReconciled": all(item["deltaRows"] == 0 for item in metric_records),
        "sourceLedgers": ledgers,
        "metricReconciliation": metric_records,
        "valeFamilyRowDistributions": family_distributions,
    }


def _build_temporal_audit(panel: pd.DataFrame) -> dict[str, Any]:
    records = []
    audit_states = Counter()
    for (family_id, metric_id), group in panel.groupby(
        ["family_id", "metric_id"], sort=True
    ):
        periods = sorted(set(group["year_or_reference_period"].astype(str)))
        source_periods = sorted(set(group["source_period"].astype(str)))
        exact_years = sorted(
            int(period) for period in periods if re.fullmatch(r"[0-9]{4}", period)
        )
        all_exact_years = len(exact_years) == len(periods)
        missing_years = (
            sorted(set(range(min(exact_years), max(exact_years) + 1)) - set(exact_years))
            if len(exact_years) >= 2
            else []
        )

        if metric_id.startswith("education.inse_"):
            audit_state = "OFFICIAL_NON_ANNUAL_SOURCE_SCHEDULE"
            aa2_rule = "COMPARE_ONLY_PUBLISHED_INSE_YEARS"
        elif metric_id in {
            "labor.occupation_active_bonds",
            "labor.sector_active_bonds",
        }:
            audit_state = "ENDPOINT_ONLY_SOURCE_DESIGN"
            aa2_rule = "TREAT_2019_AND_2025_AS_ENDPOINTS_NOT_MISSING_INTERIOR_YEARS"
        elif metric_id.startswith("labor.shift_share."):
            audit_state = "INTERVAL_DECOMPOSITION"
            aa2_rule = "TREAT_2019_2025_AS_ONE_ACCOUNTING_INTERVAL"
        elif metric_id.startswith("social.vulnerability."):
            audit_state = "REFERENCE_MONTH_SNAPSHOT"
            aa2_rule = "NO_TIME_TREND_FROM_SINGLE_REFERENCE_MONTH"
        elif len(periods) == 1:
            audit_state = "SINGLE_PERIOD_SNAPSHOT"
            aa2_rule = "NO_TIME_TREND_FROM_SINGLE_PERIOD"
        elif all_exact_years and not missing_years:
            audit_state = "CONTIGUOUS_ANNUAL_SERIES"
            aa2_rule = "ANNUAL_COMPARISON_ALLOWED_WITHIN_STABLE_METADATA"
        else:
            raise AdvancedPanelValidationError(
                f"Padrão temporal AA1 sem declaração: {family_id}/{metric_id} {periods}"
            )

        audit_states[audit_state] += 1
        period_source_mismatch_count = int(
            group["year_or_reference_period"]
            .astype(str)
            .ne(group["source_period"].astype(str))
            .sum()
        )
        definition_fields = [
            "unit",
            "universe",
            "territorial_lens",
            "network_scope",
            "formula_id",
        ]
        definition_signatures = group[definition_fields].drop_duplicates()
        definition_signature_count = len(definition_signatures)
        definition_signature_interpretation = (
            "PARALLEL_AGE_GROUP_UNIVERSES_NOT_TEMPORAL_BREAK"
            if definition_signature_count > 1
            and family_id == "F3_YOUTH_WORK_AND_APPRENTICESHIP"
            else "SINGLE_STABLE_DEFINITION_SIGNATURE"
        )
        records.append(
            {
                "familyId": family_id,
                "metricId": metric_id,
                "auditState": audit_state,
                "aa2ComparabilityRule": aa2_rule,
                "periodTokens": periods,
                "sourcePeriodTokens": source_periods,
                "periodStart": periods[0],
                "periodEnd": periods[-1],
                "periodCount": len(periods),
                "missingInteriorCalendarYears": missing_years,
                "missingYearsInterpretation": (
                    "DECLARED_SOURCE_SCHEDULE_OR_ENDPOINT_DESIGN"
                    if missing_years
                    else "NOT_APPLICABLE_OR_NONE"
                ),
                "periodSourceMismatchCount": period_source_mismatch_count,
                "definitionSignatureCount": definition_signature_count,
                "definitionSignatureInterpretation": (
                    definition_signature_interpretation
                ),
                "methodStates": sorted(set(group["method_state"].astype(str))),
                "declaredDefinitionBreaks": [],
            }
        )

    multiple_signature_metrics = [
        record["metricId"]
        for record in records
        if record["definitionSignatureCount"] > 1
    ]
    return {
        "schemaVersion": "vocacoes-pne-advanced-panel-temporal-audit-v1",
        "programId": "vocacoes-pne-advanced-analytics-v1",
        "stage": "AA1",
        "generatedAt": GENERATED_AT,
        "metricCount": len(records),
        "unresolvedTemporalPatternCount": 0,
        "temporalDefinitionBreakCount": 0,
        "multipleDefinitionSignatureMetricCount": len(multiple_signature_metrics),
        "multipleDefinitionSignatureInterpretation": (
            "PARALLEL_F3_AGE_GROUP_UNIVERSES_NOT_TEMPORAL_BREAK"
        ),
        "multipleDefinitionSignatureMetricIds": multiple_signature_metrics,
        "auditStateCounts": dict(sorted(audit_states.items())),
        "metrics": records,
    }


def _build_availability_census(panel: pd.DataFrame) -> dict[str, Any]:
    availability_counts = Counter(panel["availability_state"].astype(str))
    reason_counts = Counter(panel["unavailability_reason"].astype(str))
    unavailable = panel[panel["availability_state"].eq("unavailable")]
    metric_records = []
    for (family_id, metric_id), group in unavailable.groupby(
        ["family_id", "metric_id"], sort=True
    ):
        metric_records.append(
            {
                "familyId": family_id,
                "metricId": metric_id,
                "unavailableCount": len(group),
                "unavailabilityReasonCounts": dict(
                    sorted(Counter(group["unavailability_reason"]).items())
                ),
                "sourceAvailabilityStateCounts": dict(
                    sorted(Counter(group["source_availability_state"]).items())
                ),
            }
        )
    family_counts = {
        family_id: int(len(group))
        for family_id, group in unavailable.groupby("family_id", sort=True)
    }
    return {
        "schemaVersion": "vocacoes-pne-advanced-panel-availability-census-v1",
        "rowCount": len(panel),
        "rawNullCount": int(panel["raw_value"].isna().sum()),
        "availabilityStateCounts": {
            state: int(availability_counts.get(state, 0))
            for state in sorted(AVAILABILITY_STATES)
        },
        "unavailabilityReasonCounts": {
            reason: int(reason_counts.get(reason, 0))
            for reason in sorted(UNAVAILABILITY_REASONS)
        },
        "unavailableCountByFamily": family_counts,
        "unavailableCountByMetric": metric_records,
        "unavailableMetricCount": len(metric_records),
        "unavailableRowsReconciled": sum(
            record["unavailableCount"] for record in metric_records
        )
        == int(panel["availability_state"].eq("unavailable").sum()),
    }


def _build_aa2_entry_gate(
    panel: pd.DataFrame,
    source_inventory: Mapping[str, Any],
) -> dict[str, Any]:
    contract = _json(CONTRACT_PATH)
    observation = contract["observationContract"]
    return {
        "schemaVersion": "vocacoes-pne-aa2-entry-gate-from-aa1-v1",
        "programId": "vocacoes-pne-advanced-analytics-v1",
        "stage": "AA1_TO_AA2",
        "generatedAt": GENERATED_AT,
        "modeAllowedBeforeGatePass": "PREREGISTRATION_ONLY",
        "resultInspectionAllowedBeforeGatePass": False,
        "panelFile": PANEL_FILE,
        "coverageFile": COVERAGE_FILE,
        "grainReconciliationFile": GRAIN_FILE,
        "temporalAuditFile": TEMPORAL_FILE,
        "availabilityCensusContainerFile": QA_FILE,
        "sourceInventoryFile": SOURCE_FILE,
        "sourceInventoryDigestSha256": source_inventory["inventoryDigestSha256"],
        "expectedCounts": {
            "rows": len(panel),
            "families": panel["family_id"].nunique(),
            "metrics": panel["metric_id"].nunique(),
            "municipalities": panel["municipality_ibge_code"].nunique(),
        },
        "failClosedRequiredRowFields": [
            "coverage_scope",
            "coverage_reason",
            "reference_scope",
            "aggregation_guard",
            "unavailability_reason",
        ],
        "closedVocabularies": {
            "coverage_scope": observation["allowedCoverageScopes"],
            "coverage_reason": observation["allowedCoverageReasons"],
            "reference_scope": observation["allowedReferenceScopes"],
            "aggregation_guard": observation["allowedAggregationGuards"],
            "unavailability_reason": observation["allowedUnavailabilityReasons"],
        },
        "failClosedConditions": [
            "MISSING_REQUIRED_FIELD",
            "NULL_REQUIRED_FIELD",
            "UNKNOWN_ENUM_VALUE",
            "SOURCE_INVENTORY_DIGEST_MISMATCH",
            "SOURCE_TO_OUTPUT_RECONCILIATION_DELTA_NONZERO",
            "UNDECLARED_TEMPORAL_PATTERN",
            "PUBLIC_DATA_DIGEST_MISMATCH",
        ],
        "statewideInferencePolicy": {
            "allowedOnlyWhenCoverageScope": "RS_497",
            "vale10NeverRepresentsStatewide": True,
        },
        "aggregationPolicy": {
            "DO_NOT_AGGREGATE_AS_RS_TOTAL": "HARD_ERROR_IF_STATE_TOTAL_REQUESTED",
            "WITHIN_DECLARED_COVERAGE_ONLY": "REQUIRE_SCOPE_MATCH",
        },
        "sparseJoinPolicy": {
            "joinProducedNullMeaning": "ROW_ABSENT_OUTSIDE_SOURCE_OR_GRAIN",
            "neverCoerceToZero": True,
            "neverCoerceToUnavailableWithoutSourceRow": True,
        },
        "shiftShareSerializationTolerance": 1e-9,
        "causalClaimsAllowed": False,
        "rankingsAllowed": False,
    }


def _build_analytical_continuity(
    panel: pd.DataFrame,
    *,
    scratch_parent: Path,
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(
        prefix=".aa1-continuity-", dir=scratch_parent
    ) as temporary:
        projection_path = Path(temporary) / "pre-addendum-panel-projection.csv.gz"
        write_csv_gzip(
            projection_path,
            panel.loc[:, PRE_ADDENDUM_PANEL_COLUMNS],
        )
        projection_sha256 = sha256_file(projection_path)
    return {
        "preAddendumPanelSha256": PRE_ADDENDUM_PANEL_SHA256,
        "currentPreAddendumColumnProjectionSha256": projection_sha256,
        "equal": projection_sha256 == PRE_ADDENDUM_PANEL_SHA256,
        "excludedAddendumMetadataColumns": [
            "coverage_reason",
            "unavailability_reason",
        ],
        "currentDenominatorZeroRowCount": int(panel["denominator"].eq(0).sum()),
        "analyticalValueOrFormulaDifferenceCount": 0,
    }


def _artifact_set(output_dir: Path) -> list[dict[str, Any]]:
    return [
        {
            "path": name,
            "byteSize": (output_dir / name).stat().st_size,
            "sha256": sha256_file(output_dir / name),
        }
        for name in NON_MANIFEST_FILES
    ]


def _artifact_set_digest(output_dir: Path) -> str:
    return _sha256_payload(_artifact_set(output_dir))


def materialize_package(
    output_dir: Path,
    *,
    source_inventory: Mapping[str, Any] | None = None,
    external_io_guarded: bool = False,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=False)
    inventory = dict(source_inventory or build_source_inventory())
    panel = build_panel()
    checks = _validate_panel(panel, source_inventory=inventory)
    catalog = _build_catalog(panel)
    coverage = _build_coverage(panel)
    grain_reconciliation = _build_grain_reconciliation(panel)
    temporal_audit = _build_temporal_audit(panel)
    availability_census = _build_availability_census(panel)
    aa2_entry_gate = _build_aa2_entry_gate(panel, inventory)
    analytical_continuity = _build_analytical_continuity(
        panel, scratch_parent=output_dir
    )
    if analytical_continuity["equal"] is not True:
        raise AdvancedPanelValidationError(
            "Projeção analítica AA1 divergiu do painel pré-adendo"
        )

    write_csv_gzip(output_dir / PANEL_FILE, panel)
    write_json(output_dir / CATALOG_FILE, catalog)
    write_json(output_dir / COVERAGE_FILE, coverage)
    write_json(output_dir / GRAIN_FILE, grain_reconciliation)
    write_json(output_dir / TEMPORAL_FILE, temporal_audit)
    write_json(output_dir / AA2_GATE_FILE, aa2_entry_gate)
    write_json(output_dir / SOURCE_FILE, inventory)
    availability_counts = Counter(panel["availability_state"].astype(str))
    qa = {
        "schemaVersion": "vocacoes-pne-advanced-panel-qa-v1",
        "programId": "vocacoes-pne-advanced-analytics-v1",
        "stage": "AA1",
        "generatedAt": GENERATED_AT,
        "controlCount": len(checks),
        "failedCount": 0,
        "checks": checks,
        "counts": {
            "rowCount": len(panel),
            "familyCount": panel["family_id"].nunique(),
            "metricCount": panel["metric_id"].nunique(),
            "municipalityCount": panel["municipality_ibge_code"].nunique(),
            "observedZeroCount": int(
                panel["availability_state"].eq("observed_zero").sum()
            ),
            "unavailableCount": int(
                panel["availability_state"].eq("unavailable").sum()
            ),
            "rawNullCount": int(panel["raw_value"].isna().sum()),
            "denominatorZeroCount": int(panel["denominator"].eq(0).sum()),
            "availabilityStateCounts": {
                state: int(availability_counts.get(state, 0))
                for state in sorted(AVAILABILITY_STATES)
            },
            "rowAbsentCount": None,
            "rowAbsentMeaning": "NOT_A_ROW_STATE_RECONCILED_BY_SOURCE_ACCOUNTING",
        },
        "availabilityCensus": availability_census,
    }
    write_json(output_dir / QA_FILE, qa)
    artifacts = _artifact_set(output_dir)
    manifest = {
        "schemaVersion": "vocacoes-pne-advanced-panel-manifest-v1",
        "programId": "vocacoes-pne-advanced-analytics-v1",
        "stage": "AA1",
        "generatedAt": GENERATED_AT,
        "finalState": "AA1_PANEL_READY_WITH_EXPLICIT_PARTIAL_COVERAGE",
        "classification": "DATA_LOGIC",
        "contract": _file_record(CONTRACT_PATH, kind="contract"),
        "implementationFiles": [
            _file_record(path, kind="implementation")
            for path in IMPLEMENTATION_PATHS
        ],
        "artifacts": artifacts,
        "artifactSetDigestSha256": _sha256_payload(artifacts),
        "sourceInventoryDigestSha256": inventory["inventoryDigestSha256"],
        "analyticalContinuity": analytical_continuity,
        "publicDataIntegrity": {
            "beforeTreeDigestSha256": inventory["publicDataTreeDigestSha256"],
            "afterTreeDigestSha256": inventory["publicDataTreeDigestSha256"],
            "unchanged": inventory["publicDataTreeDigestSha256"]
            == EXPECTED_PUBLIC_DATA_DIGEST,
        },
        "counts": qa["counts"],
        "generation": {
            "deterministic": True,
            "transactional": True,
            "manifestLast": True,
            "twoIndependentMaterializationsRequired": True,
            "twoIndependentOperatingSystemProcessesRequired": True,
            "distinctPythonHashSeedsRequired": True,
            "networkGuardEnabled": external_io_guarded,
            "databaseGuardEnabled": external_io_guarded,
            "databaseUsed": False,
            "networkUsed": False,
            "publicDataChanged": False,
            "fullBuildUsed": False,
        },
        "independentMaterializationVerification": {
            "state": "PENDING_RUNNER_COMPARISON",
            "equal": None,
            "artifactSetDigestSha256": None,
        },
    }
    write_json(output_dir / MANIFEST_FILE, manifest)
    return manifest


def _finalize_determinism(
    output_dir: Path,
    digest: str,
    *,
    process_evidence: Sequence[Mapping[str, Any]],
) -> None:
    manifest_path = output_dir / MANIFEST_FILE
    manifest = _json(manifest_path)
    manifest["independentMaterializationVerification"] = {
        "state": "VERIFIED_IDENTICAL",
        "equal": True,
        "artifactSetDigestSha256": digest,
        "processIsolation": "TWO_FRESH_OPERATING_SYSTEM_PROCESSES",
        "processCount": len(process_evidence),
        "processEvidence": list(process_evidence),
    }
    write_json(manifest_path, manifest)


def materialize_single_candidate(output_dir: Path) -> dict[str, Any]:
    public_digest_before = directory_content_digest(REPO_ROOT / "public/data")
    if public_digest_before != EXPECTED_PUBLIC_DATA_DIGEST:
        raise AdvancedPanelValidationError(
            "public/data divergiu antes da materialização candidata AA1"
        )
    inventory = build_source_inventory(public_digest_before)
    materialize_package(
        output_dir,
        source_inventory=inventory,
        external_io_guarded=True,
    )
    del inventory
    gc.collect()
    public_digest_after = directory_content_digest(REPO_ROOT / "public/data")
    if public_digest_after != public_digest_before:
        raise AdvancedPanelValidationError(
            "public/data mudou durante a materialização candidata AA1"
        )
    loaded_module_roots = {name.partition(".")[0] for name in sys.modules}
    loaded_database_clients = sorted(
        loaded_module_roots & DATABASE_CLIENT_MODULE_ROOTS
    )
    loaded_network_clients = sorted(loaded_module_roots & NETWORK_CLIENT_MODULE_ROOTS)
    return {
        "outputDir": _display_path(output_dir),
        "artifactSetDigestSha256": _artifact_set_digest(output_dir),
        "candidateTreeDigestSha256": directory_content_digest(output_dir),
        "implementationSha256": sha256_file(
            REPO_ROOT / "data_pipeline/src/vocacoes_pne_advanced_panel.py"
        ),
        "networkGuardEnabled": True,
        "databaseGuardEnabled": True,
        "loadedDatabaseClientModules": loaded_database_clients,
        "loadedNetworkClientModules": loaded_network_clients,
        "publicDataBeforeTreeDigestSha256": public_digest_before,
        "publicDataAfterTreeDigestSha256": public_digest_after,
    }


def _run_candidate_process(output_dir: Path, *, python_hash_seed: str) -> dict[str, Any]:
    environment = os.environ.copy()
    environment["PYTHONHASHSEED"] = python_hash_seed
    command = [
        sys.executable,
        str(RUNNER_PATH),
        "--single-candidate",
        "--output-dir",
        str(output_dir),
    ]
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise AdvancedPanelValidationError(
            "Processo candidato AA1 falhou "
            f"(seed={python_hash_seed}, exit={completed.returncode}): "
            f"{completed.stderr.strip()}"
        )
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise AdvancedPanelValidationError(
            f"Saída candidata AA1 inválida (seed={python_hash_seed})"
        ) from error
    result["pythonHashSeed"] = python_hash_seed
    result["processMode"] = "FRESH_OS_PROCESS"
    return result


def _replace_directory_transactionally(staging: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    rollback = target.with_name(f".{target.name}.rollback-aa1")
    if rollback.exists():
        shutil.rmtree(rollback)
    moved_existing = False
    try:
        if target.exists():
            os.replace(target, rollback)
            moved_existing = True
        os.replace(staging, target)
    except Exception:
        if target.exists() and not moved_existing:
            shutil.rmtree(target)
        if moved_existing and rollback.exists() and not target.exists():
            os.replace(rollback, target)
        raise
    else:
        if rollback.exists():
            shutil.rmtree(rollback)


def materialize_twice_transactionally(output_dir: Path = DEFAULT_OUTPUT_ROOT) -> dict[str, Any]:
    public_digest_before = directory_content_digest(REPO_ROOT / "public/data")
    if public_digest_before != EXPECTED_PUBLIC_DATA_DIGEST:
        raise AdvancedPanelValidationError("public/data divergiu antes da materialização AA1")
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    first = Path(tempfile.mkdtemp(prefix=".aa1-first-", dir=output_dir.parent))
    second = Path(tempfile.mkdtemp(prefix=".aa1-second-", dir=output_dir.parent))
    shutil.rmtree(first)
    shutil.rmtree(second)
    try:
        first_result = _run_candidate_process(first, python_hash_seed="101")
        second_result = _run_candidate_process(second, python_hash_seed="202")
        first_digest = _artifact_set_digest(first)
        second_digest = _artifact_set_digest(second)
        if first_digest != second_digest:
            raise AdvancedPanelValidationError(
                "As duas materializações AA1 produziram conjuntos divergentes"
            )
        implementation_sha256 = sha256_file(
            REPO_ROOT / "data_pipeline/src/vocacoes_pne_advanced_panel.py"
        )
        for candidate in (first_result, second_result):
            if candidate["implementationSha256"] != implementation_sha256:
                raise AdvancedPanelValidationError(
                    "Processo candidato AA1 usou implementação divergente"
                )
            if (
                candidate["networkGuardEnabled"] is not True
                or candidate["databaseGuardEnabled"] is not True
            ):
                raise AdvancedPanelValidationError(
                    "Processo candidato AA1 executou sem guardas externos"
                )
            if (
                candidate["loadedDatabaseClientModules"]
                or candidate["loadedNetworkClientModules"]
            ):
                raise AdvancedPanelValidationError(
                    "Processo candidato AA1 carregou cliente externo proibido"
                )
            if (
                candidate["publicDataBeforeTreeDigestSha256"]
                != EXPECTED_PUBLIC_DATA_DIGEST
                or candidate["publicDataAfterTreeDigestSha256"]
                != EXPECTED_PUBLIC_DATA_DIGEST
            ):
                raise AdvancedPanelValidationError(
                    "Processo candidato AA1 observou public/data divergente"
                )
        process_evidence = [
            {
                "processMode": candidate["processMode"],
                "pythonHashSeed": candidate["pythonHashSeed"],
                "implementationSha256": candidate["implementationSha256"],
                "candidateArtifactSetDigestSha256": candidate[
                    "artifactSetDigestSha256"
                ],
                "networkGuardEnabled": candidate["networkGuardEnabled"],
                "databaseGuardEnabled": candidate["databaseGuardEnabled"],
                "loadedDatabaseClientModules": candidate[
                    "loadedDatabaseClientModules"
                ],
                "loadedNetworkClientModules": candidate[
                    "loadedNetworkClientModules"
                ],
                "publicDataBeforeTreeDigestSha256": candidate[
                    "publicDataBeforeTreeDigestSha256"
                ],
                "publicDataAfterTreeDigestSha256": candidate[
                    "publicDataAfterTreeDigestSha256"
                ],
            }
            for candidate in (first_result, second_result)
        ]
        _finalize_determinism(
            first, first_digest, process_evidence=process_evidence
        )
        _finalize_determinism(
            second, second_digest, process_evidence=process_evidence
        )
        first_tree = directory_content_digest(first)
        second_tree = directory_content_digest(second)
        if first_tree != second_tree:
            raise AdvancedPanelValidationError(
                "As duas árvores AA1 divergiram após o manifesto final"
            )
        public_digest_after = second_result["publicDataAfterTreeDigestSha256"]
        if public_digest_after != public_digest_before:
            raise AdvancedPanelValidationError("public/data mudou durante a materialização AA1")
        validate_existing_output(first, verify_sources=False)
        _replace_directory_transactionally(first, output_dir)
        return {
            "outputDir": _display_path(output_dir),
            "artifactSetDigestSha256": first_digest,
            "fullTreeDigestSha256": first_tree,
            "independentMaterializationsEqual": True,
            "processIsolation": "TWO_FRESH_OPERATING_SYSTEM_PROCESSES",
            "pythonHashSeeds": ["101", "202"],
            "networkGuardEnabled": True,
            "databaseGuardEnabled": True,
            "loadedDatabaseClientModules": [],
            "loadedNetworkClientModules": [],
            "publicDataTreeDigestSha256": public_digest_after,
        }
    finally:
        if first.exists():
            shutil.rmtree(first)
        if second.exists():
            shutil.rmtree(second)


def validate_existing_output(
    output_dir: Path = DEFAULT_OUTPUT_ROOT,
    *,
    verify_sources: bool = True,
) -> dict[str, Any]:
    if not output_dir.is_dir():
        raise FileNotFoundError(f"Pacote AA1 ausente: {output_dir}")
    actual_files = sorted(path.name for path in output_dir.iterdir() if path.is_file())
    if actual_files != sorted(PACKAGE_FILES):
        raise AdvancedPanelValidationError(
            f"Arquivos AA1 divergentes: {actual_files} != {sorted(PACKAGE_FILES)}"
        )
    manifest = _json(output_dir / MANIFEST_FILE)
    if manifest["finalState"] != "AA1_PANEL_READY_WITH_EXPLICIT_PARTIAL_COVERAGE":
        raise AdvancedPanelValidationError("Estado final AA1 divergente")
    if manifest["contract"]["sha256"] != sha256_file(CONTRACT_PATH):
        raise AdvancedPanelValidationError("Contrato AA1 divergiu do manifesto")
    for record in manifest["implementationFiles"]:
        path = REPO_ROOT / record["path"]
        if path.stat().st_size != record["byteSize"] or sha256_file(path) != record["sha256"]:
            raise AdvancedPanelValidationError(
                f"Implementação AA1 divergiu: {record['path']}"
            )
    for artifact in manifest["artifacts"]:
        path = output_dir / artifact["path"]
        if path.stat().st_size != artifact["byteSize"] or sha256_file(path) != artifact["sha256"]:
            raise AdvancedPanelValidationError(f"Artefato AA1 divergiu: {artifact['path']}")
    if _artifact_set_digest(output_dir) != manifest["artifactSetDigestSha256"]:
        raise AdvancedPanelValidationError("Digest do conjunto AA1 divergiu")
    determinism = manifest["independentMaterializationVerification"]
    if determinism.get("state") != "VERIFIED_IDENTICAL" or determinism.get("equal") is not True:
        raise AdvancedPanelValidationError("Duas materializações AA1 não estão verificadas")
    if determinism["artifactSetDigestSha256"] != manifest["artifactSetDigestSha256"]:
        raise AdvancedPanelValidationError("Prova de determinismo AA1 divergiu")
    if (
        determinism.get("processIsolation")
        != "TWO_FRESH_OPERATING_SYSTEM_PROCESSES"
        or determinism.get("processCount") != 2
        or sorted(
            item.get("pythonHashSeed")
            for item in determinism.get("processEvidence", [])
        )
        != ["101", "202"]
        or any(
            item.get("loadedDatabaseClientModules")
            or item.get("loadedNetworkClientModules")
            for item in determinism.get("processEvidence", [])
        )
    ):
        raise AdvancedPanelValidationError(
            "Prova de isolamento entre processos AA1 divergiu"
        )
    generation = manifest["generation"]
    if (
        generation.get("networkGuardEnabled") is not True
        or generation.get("databaseGuardEnabled") is not True
    ):
        raise AdvancedPanelValidationError("Guardas externos AA1 não comprovados")

    panel = _read_csv(output_dir / PANEL_FILE)
    panel["raw_value"] = pd.to_numeric(panel["raw_value"], errors="coerce")
    inventory = _json(output_dir / SOURCE_FILE)
    checks = _validate_panel(panel, source_inventory=inventory)
    grain = _json(output_dir / GRAIN_FILE)
    temporal = _json(output_dir / TEMPORAL_FILE)
    aa2_gate = _json(output_dir / AA2_GATE_FILE)
    if grain != _build_grain_reconciliation(panel):
        raise AdvancedPanelValidationError("Reconciliação de grão AA1 divergiu")
    if temporal != _build_temporal_audit(panel):
        raise AdvancedPanelValidationError("Auditoria temporal AA1 divergiu")
    if aa2_gate != _build_aa2_entry_gate(panel, inventory):
        raise AdvancedPanelValidationError("Gate de entrada AA2 divergiu")
    qa = _json(output_dir / QA_FILE)
    if qa["failedCount"] != 0 or len(checks) != qa["controlCount"]:
        raise AdvancedPanelValidationError("QA AA1 materializado divergiu")
    if qa.get("availabilityCensus") != _build_availability_census(panel):
        raise AdvancedPanelValidationError("Censo de disponibilidade AA1 divergiu")
    continuity = manifest.get("analyticalContinuity", {})
    if (
        continuity.get("preAddendumPanelSha256")
        != PRE_ADDENDUM_PANEL_SHA256
        or continuity.get("currentPreAddendumColumnProjectionSha256")
        != PRE_ADDENDUM_PANEL_SHA256
        or continuity.get("equal") is not True
        or continuity.get("analyticalValueOrFormulaDifferenceCount") != 0
    ):
        raise AdvancedPanelValidationError("Continuidade analítica AA1 divergiu")
    if verify_sources:
        current_public_digest = directory_content_digest(REPO_ROOT / "public/data")
        current_inventory = build_source_inventory(current_public_digest)
        if current_inventory["inventoryDigestSha256"] != inventory["inventoryDigestSha256"]:
            raise AdvancedPanelValidationError("Fontes AA1 divergiram do inventário congelado")
        if current_public_digest != EXPECTED_PUBLIC_DATA_DIGEST:
            raise AdvancedPanelValidationError("public/data divergiu do baseline AA1")
    return {
        "state": manifest["finalState"],
        "rowCount": manifest["counts"]["rowCount"],
        "familyCount": manifest["counts"]["familyCount"],
        "metricCount": manifest["counts"]["metricCount"],
        "municipalityCount": manifest["counts"]["municipalityCount"],
        "artifactSetDigestSha256": manifest["artifactSetDigestSha256"],
        "sourceInventoryDigestSha256": manifest["sourceInventoryDigestSha256"],
        "publicDataUnchanged": manifest["publicDataIntegrity"]["unchanged"],
    }


__all__ = [
    "AdvancedPanelValidationError",
    "DEFAULT_OUTPUT_ROOT",
    "build_panel",
    "build_source_inventory",
    "materialize_package",
    "materialize_twice_transactionally",
    "validate_existing_output",
]
