"""Job 5G-A V7: demografia, trajetória e condições escolares.

A materialização é deliberadamente descritiva. Ela usa rede total, mantém
população residente separada da educação por localização da escola, não cria
taxa regional a partir de taxas municipais e trata coortes como pressão
mecânica transparente, nunca como previsão.
"""

from __future__ import annotations

from contextlib import contextmanager
import json
import math
import os
from pathlib import Path
import re
import shutil
import tempfile
from typing import Any, Iterable, Iterator, Mapping, Sequence

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, URL

from src.vocacoes_pne_job2 import (
    assert_outside_public_data,
    directory_content_digest,
    require_ibge_code,
    safe_ratio,
    sha256_file,
    staging_directory_for,
    validate_unique_key,
    write_csv_gzip,
    write_json,
)


SCHEMA_VERSION = "vocacoes-pne-v7-job5ga-v1"
JOB_ID = "v7-job5ga"
VERDICT = "JOB_5GA_PARTIAL_WITH_DATA_GAPS"
REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_PIPELINE_DIR = REPO_ROOT / "data_pipeline"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / ".tmp" / "vocacoes-pne" / JOB_ID
JOB2_ROOT = REPO_ROOT / ".tmp" / "vocacoes-pne" / "v7-job2"
JOB5F_ROOT = REPO_ROOT / ".tmp" / "vocacoes-pne" / "v7-job5f"
CONTRACT_PATH = DATA_PIPELINE_DIR / "contracts" / "vocacoes-pne-v7-job5ga.json"
CORE_PATH = Path(__file__).resolve()
LAUNCHER_PATH = DATA_PIPELINE_DIR / "scripts" / "run_vocacoes_pne_v7_job5ga.py"
REGION_CONFIG_PATH = REPO_ROOT / "config" / "regions" / "rs.json"
MUNICIPALITY_REGISTRY_PATH = REPO_ROOT / "config" / "municipalities" / "rs.json"
NORMALIZED_ROOT = (
    REPO_ROOT
    / ".tmp"
    / "foresight-r5b"
    / "insumos"
    / "fontes"
    / "normalizadas"
    / "inep_indicadores_eb"
    / "2023_2025_municipios"
)
OBSERVATIONS_PATH = NORMALIZED_ROOT / "observations_pilotos.jsonl"
SOURCE_SPEC_PATH = NORMALIZED_ROOT / "source-spec.json"
IRD_PATH = (
    REPO_ROOT
    / ".tmp"
    / "foresight-r5b"
    / "insumos"
    / "fontes"
    / "xlsx"
    / "IRD_MUNICIPIOS_2025.xlsx"
)
NOVA_SANTA_RITA_ID = "4313375"

OUTPUT_FILES = (
    "CONTRATO_TRAJETORIA_OFICIAL_DESCRITIVA_V1.json",
    "PAINEL_TRAJETORIA_OFICIAL_DESCRITIVA_V1.csv.gz",
    "PAINEL_NASCIMENTOS_EDUCACAO_INFANTIL_V1.csv.gz",
    "PAINEL_DOCENTES_TURMAS_JORNADA_V1.csv.gz",
    "PAINEL_CONDICOES_ESCOLARES_TOTAL_V1.csv.gz",
    "PAINEL_PRESSAO_MECANICA_COORTES_AUDITADO_V1.csv.gz",
    "NOVA_SANTA_RITA_JOB5GA_V1.json",
    "MATRIZ_OPORTUNIDADES_REAVALIADAS_JOB5GA.csv.gz",
    "MAPA_SECOES_POTENCIAIS_JOB5GA.md",
    "LIMITACOES_JOB5GA.json",
    "PACOTE_REVISAO_EXTERNA_JOB5GA.json",
    "MANIFEST_JOB5GA.json",
)

ALLOWED_CLASSIFICATIONS = {
    "READY_FOR_INTERNAL_VISUAL_PROTOTYPE",
    "PROMISING_NEEDS_MORE_TESTING",
    "DESCRIPTIVE_CONTEXT_ONLY",
    "INSUFFICIENT_DATA",
    "REJECTED",
}
ALLOWED_VALUE_STATES = {
    "observed",
    "null",
    "unavailable",
    "suppressed",
    "not_applicable",
}
TRAJECTORY_METRICS = {
    "approval_rate_percent",
    "failure_rate_percent",
    "dropout_rate_percent",
    "age_grade_distortion_rate_percent",
}
CONDITION_METRICS = {
    "students_per_class",
    "teacher_adequacy_percent",
    "inse_mean",
    "schools_with_broadband_percent",
    "schools_with_drinking_water_percent",
    "schools_with_internet_percent",
    "schools_with_library_percent",
    "schools_with_sports_court_percent",
}
COUNT_METRICS = {
    "docentes",
    "turmas",
    "matriculas",
    "matriculas_tempo_integral",
}


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _json_safe(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (np.integer, np.floating)):
        value = value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if pd.isna(value):
        return None
    return value


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(
        path,
        dtype={"municipality_ibge_code": "string"},
        keep_default_na=False,
        na_values=["null"],
    )


def _stable(frame: pd.DataFrame, columns: Sequence[str] | None = None) -> pd.DataFrame:
    result = frame.copy()
    sort_columns = list(columns or result.columns)
    sort_columns = [column for column in sort_columns if column in result.columns]
    if sort_columns:
        result = result.sort_values(sort_columns, kind="stable", na_position="last")
    return result.reset_index(drop=True)


def _total_rows(frame: pd.DataFrame) -> pd.DataFrame:
    dependency = frame["dependencia"].astype("string").str.casefold()
    location = frame["localizacao"].astype("string").str.casefold()
    return frame[
        dependency.isin({"total", "all"}) & location.isin({"total", "all"})
    ].copy()


def _normalize_stage(value: Any) -> str:
    raw = str(value).strip()
    raw = re.sub(r"^taxa_distorcao_", "", raw)
    mapping = {
        "fundamental_anos_iniciais": "anos_iniciais",
        "fundamental_anos_finais": "anos_finais",
        "fundamental": "fundamental",
        "medio": "medio",
        "ensino_medio": "medio",
        "educacao_infantil": "educacao_infantil",
        "infantil": "educacao_infantil",
        "pre_escola": "pre_escola",
        "preschool": "pre_escola",
        "pré-escola": "pre_escola",
        "creche": "creche",
        "high_school": "medio",
    }
    return mapping.get(raw.casefold(), raw.casefold().replace(" ", "_"))


def _unit_for_metric(metric: str) -> str:
    if metric in COUNT_METRICS:
        return "count"
    if metric in {"alunos_por_turma", "students_per_class"}:
        return "students_per_class"
    if metric == "estudantes_por_docente":
        return "students_per_reported_teacher"
    if metric.startswith("horas_aula_diaria"):
        return "hours_per_day"
    if metric == "inse_mean":
        return "inse_scale_points"
    return "percent"


def _load_scope() -> tuple[list[str], dict[str, str], list[str]]:
    regions = _load_json(REGION_CONFIG_PATH)
    region = next(item for item in regions["regions"] if item["slug"] == "vale-do-sinos")
    codes = list(region["municipalityIbgeCodes"])
    if len(codes) != 10 or region["municipalityCount"] != 10:
        raise ValueError("O recorte canônico do Vale do Sinos não contém dez municípios.")
    for code in codes:
        require_ibge_code(code)
    registry = _load_json(MUNICIPALITY_REGISTRY_PATH)
    all_rs_codes = [item["ibgeCode"] for item in registry["municipalities"]]
    names = {
        item["ibgeCode"]: item["name"]
        for item in registry["municipalities"]
        if item["ibgeCode"] in set(codes)
    }
    if set(names) != set(codes) or names.get(NOVA_SANTA_RITA_ID) != "Nova Santa Rita":
        raise ValueError("Registro municipal canônico inconsistente para o Job 5G-A.")
    if len(all_rs_codes) != 497:
        raise ValueError("O registro canônico do RS não contém 497 municípios.")
    for code in all_rs_codes:
        require_ibge_code(code)
    return codes, names, all_rs_codes


def _verify_inputs(contract: Mapping[str, Any]) -> dict[str, str]:
    if tuple(contract["outputs"]) != OUTPUT_FILES:
        raise ValueError("Allowlist de outputs diverge do contrato Job 5G-A.")
    scope = contract["scope"]
    if scope["networkScope"] != "total_all_dependencies":
        raise ValueError("Escopo de rede total não foi preservado.")
    if scope["administrativeDependencyIsAnalyticDimension"]:
        raise ValueError("Dependência administrativa não pode ser dimensão analítica.")
    if not scope["administrativeDependencyIsQADimension"]:
        raise ValueError("Dependência administrativa deve permanecer dimensão de QA.")
    if contract["h2Boundary"]["state"] != "NOT_EVALUABLE_DUE_TO_DATA_OR_QA_LIMIT":
        raise ValueError("O estado congelado de H2 foi alterado.")
    verified: dict[str, str] = {}
    for relative, expected in contract["inputFingerprints"].items():
        path = REPO_ROOT / relative
        if not path.is_file():
            raise FileNotFoundError(f"Entrada canônica ausente: {relative}")
        actual = sha256_file(path)
        if actual != expected:
            raise ValueError(f"Hash divergente: {relative}: {actual} != {expected}")
        verified[relative] = actual
    return verified


def _database_url(database: str) -> URL:
    required = ("DB_USUARIO", "DB_SENHA", "DB_HOST")
    missing = [key for key in required if not os.getenv(key)]
    if missing:
        raise RuntimeError(f"Variáveis locais ausentes: {', '.join(missing)}.")
    return URL.create(
        "postgresql+psycopg2",
        username=os.environ["DB_USUARIO"],
        password=os.environ["DB_SENHA"],
        host=os.environ["DB_HOST"],
        port=int(os.getenv("DB_PORT", "5432")),
        database=database,
    )


@contextmanager
def _read_only_connection(database: str = "sesi") -> Iterator[Connection]:
    engine = create_engine(
        _database_url(database),
        connect_args={
            "options": "-c default_transaction_read_only=on -c statement_timeout=180000"
        },
    )
    try:
        with engine.connect() as connection:
            transaction = connection.begin()
            try:
                connection.execute(text("SET TRANSACTION READ ONLY"))
                mode = connection.execute(
                    text("SELECT current_setting('transaction_read_only')")
                ).scalar_one()
                if mode != "on":
                    raise RuntimeError("A conexão do Job 5G-A não está em modo somente leitura.")
                yield connection
            finally:
                transaction.rollback()
    finally:
        engine.dispose()


def _read_sql(connection: Connection, query: str, codes: Sequence[str]) -> pd.DataFrame:
    return pd.read_sql_query(text(query), connection, params={"codes": list(codes)})


def _query_education_and_population(
    all_rs_codes: Sequence[str],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    with _read_only_connection() as connection:
        teachers = _read_sql(
            connection,
            """
            SELECT ano::int AS year, id_municipio::text AS municipality_ibge_code,
                   etapa_ensino::text AS stage, turmas::double precision AS turmas,
                   docentes::double precision AS docentes,
                   matriculas::double precision AS matriculas,
                   alunos_por_turma::double precision AS alunos_por_turma,
                   alunos_por_docente::double precision AS alunos_por_docente
            FROM public.vw_educacao_turmas_docentes
            WHERE id_municipio::text = ANY(:codes)
              AND lower(dependencia::text) IN ('total', 'all')
              AND lower(localizacao::text) IN ('total', 'all')
            """,
            all_rs_codes,
        )
        integral = _read_sql(
            connection,
            """
            SELECT ano::int AS year, id_municipio::text AS municipality_ibge_code,
                   etapa_ensino::text AS stage,
                   matriculas::double precision AS matriculas,
                   matriculas_integral::double precision AS matriculas_integral,
                   percentual_integral::double precision AS percentual_integral
            FROM public.vw_educacao_matriculas
            WHERE id_municipio::text = ANY(:codes)
              AND lower(dependencia::text) IN ('total', 'all')
              AND lower(localizacao::text) IN ('total', 'all')
            """,
            all_rs_codes,
        )
        schools = _read_sql(
            connection,
            """
            SELECT ano::int AS year, id_municipio::text AS municipality_ibge_code,
                   etapa_ensino::text AS stage, escolas::double precision AS escolas
            FROM public.vw_educacao_rede_escolar_etapa
            WHERE id_municipio::text = ANY(:codes)
              AND lower(dependencia::text) IN ('total', 'all')
              AND lower(localizacao::text) IN ('total', 'all')
            """,
            all_rs_codes,
        )
        ages = _read_sql(
            connection,
            """
            SELECT ano::int AS year, id_municipio::text AS municipality_ibge_code,
                   idade::int AS age, SUM(pop_estimada)::double precision AS population
            FROM public.populacao_idade
            WHERE id_municipio::text = ANY(:codes)
            GROUP BY ano, id_municipio, idade
            """,
            all_rs_codes,
        )
    for label, frame, key in (
        ("docentes_turmas", teachers, ["year", "municipality_ibge_code", "stage"]),
        ("tempo_integral", integral, ["year", "municipality_ibge_code", "stage"]),
        ("escolas_etapa", schools, ["year", "municipality_ibge_code", "stage"]),
        ("populacao_idade", ages, ["year", "municipality_ibge_code", "age"]),
    ):
        frame["municipality_ibge_code"] = frame["municipality_ibge_code"].astype("string")
        frame["municipality_ibge_code"].map(require_ibge_code)
        if "stage" in frame:
            frame["stage"] = frame["stage"].map(_normalize_stage)
        validate_unique_key(frame, key, label=label)
    return teachers, integral, schools, ages


def _distribution_context(
    frame: pd.DataFrame,
    *,
    group_columns: Sequence[str],
    value_column: str = "value",
    universe_codes: Sequence[str],
    prefix: str,
) -> pd.DataFrame:
    universe = frame[frame["municipality_ibge_code"].isin(set(universe_codes))].copy()
    universe[value_column] = pd.to_numeric(universe[value_column], errors="coerce")
    grouped = universe.groupby(list(group_columns), dropna=False)[value_column]
    summary = grouped.agg(
        **{
            f"{prefix}_municipality_count": "count",
            f"{prefix}_minimum": "min",
            f"{prefix}_quartile_1": lambda values: values.quantile(0.25),
            f"{prefix}_municipal_median": "median",
            f"{prefix}_quartile_3": lambda values: values.quantile(0.75),
            f"{prefix}_maximum": "max",
        }
    ).reset_index()
    return summary


def _add_municipal_position(
    frame: pd.DataFrame,
    *,
    group_columns: Sequence[str],
    value_column: str = "value",
) -> pd.DataFrame:
    result = frame.copy()
    result["position_low_to_high_among_ten"] = result.groupby(
        list(group_columns), dropna=False
    )[value_column].rank(method="min", ascending=True, na_option="keep")
    result["percentile_low_to_high_among_ten"] = result.groupby(
        list(group_columns), dropna=False
    )[value_column].rank(method="average", pct=True, ascending=True, na_option="keep")
    return result


def _trajectory_panel(codes: Sequence[str], names: Mapping[str, str]) -> pd.DataFrame:
    source = _total_rows(_read_csv(JOB2_ROOT / "2a" / "trajetoria_municipal.csv.gz"))
    source = source[source["municipality_ibge_code"].isin(set(codes))].copy()
    source = source[source["metric"].isin(TRAJECTORY_METRICS)].copy()
    source["year"] = pd.to_numeric(source.pop("ano"), errors="raise").astype("int64")
    source["stage"] = source.pop("etapa_ensino").map(_normalize_stage)
    source["value"] = pd.to_numeric(source["value"], errors="coerce")
    source["municipality_name"] = source["municipality_ibge_code"].map(names)
    source["value_status"] = source["value_status"].fillna("unavailable")
    source["network_scope"] = "total_all_dependencies"
    source["source_dependency_qa"] = "total"
    source["source_location_qa"] = "total"
    source["unit"] = "percent"
    source["territorial_lens"] = "school_location"
    source["regional_rate_value"] = np.nan
    source["regional_rate_status"] = "not_applicable"
    source["regional_rate_method"] = "not_computed"
    source["rs_official_rate_value"] = np.nan
    source["rs_official_rate_status"] = "unavailable"

    comparisons = _total_rows(_read_csv(JOB2_ROOT / "2a" / "trajetoria_comparacoes.csv.gz"))
    comparisons["year"] = pd.to_numeric(comparisons.pop("ano"), errors="raise").astype("int64")
    comparisons["stage"] = comparisons.pop("etapa_ensino").map(_normalize_stage)
    comparison_columns = [
        "year",
        "stage",
        "metric",
        "entity_scope",
        "comparison_method",
        "municipality_count",
        "minimum",
        "quartile_1",
        "median",
        "quartile_3",
        "maximum",
    ]
    comparisons = comparisons[comparison_columns]
    region = comparisons[comparisons["entity_scope"] == "region"].drop(columns="entity_scope")
    region = region.rename(columns={column: f"vale_{column}" for column in region.columns if column not in {"year", "stage", "metric"}})
    state = comparisons[comparisons["entity_scope"] == "state"].drop(columns="entity_scope")
    state = state.rename(columns={column: f"rs_{column}" for column in state.columns if column not in {"year", "stage", "metric"}})
    source = source.merge(region, on=["year", "stage", "metric"], how="left", validate="many_to_one")
    source = source.merge(state, on=["year", "stage", "metric"], how="left", validate="many_to_one")

    group_key = ["municipality_ibge_code", "stage", "metric"]
    observed = source[source["value"].notna()].sort_values("year", kind="stable")
    window = observed.groupby(group_key, as_index=False).agg(
        period_start_year=("year", "first"),
        period_end_year=("year", "last"),
        period_start_value=("value", "first"),
        period_end_value=("value", "last"),
        observed_year_count=("year", "count"),
    )
    window["full_window_change_pp"] = window["period_end_value"] - window["period_start_value"]
    window["observed_direction"] = np.select(
        [window["full_window_change_pp"] > 0, window["full_window_change_pp"] < 0],
        ["increase", "decrease"],
        default="no_observed_change",
    )
    source = source.merge(window, on=group_key, how="left", validate="many_to_one")
    deltas = window.copy()
    delta_summary = deltas.groupby(["stage", "metric"], as_index=False).agg(
        vale_median_municipal_change_pp=("full_window_change_pp", "median"),
        municipalities_with_increase=("observed_direction", lambda x: int((x == "increase").sum())),
        municipalities_with_decrease=("observed_direction", lambda x: int((x == "decrease").sum())),
        municipalities_with_no_observed_change=("observed_direction", lambda x: int((x == "no_observed_change").sum())),
        municipalities_with_change_observed=("full_window_change_pp", "count"),
    )
    source = source.merge(delta_summary, on=["stage", "metric"], how="left", validate="many_to_one")
    delta_positions = _add_municipal_position(
        deltas.rename(columns={"full_window_change_pp": "value"}),
        group_columns=["stage", "metric"],
    )[["municipality_ibge_code", "stage", "metric", "position_low_to_high_among_ten", "percentile_low_to_high_among_ten"]]
    delta_positions = delta_positions.rename(
        columns={
            "position_low_to_high_among_ten": "change_position_low_to_high_among_ten",
            "percentile_low_to_high_among_ten": "change_percentile_low_to_high_among_ten",
        }
    )
    source = source.merge(delta_positions, on=group_key, how="left", validate="many_to_one")

    rate_family = source[source["metric"].isin({"approval_rate_percent", "failure_rate_percent", "dropout_rate_percent"})]
    pivot = rate_family.pivot_table(
        index=["municipality_ibge_code", "stage", "year"],
        columns="metric",
        values="value",
        aggfunc="first",
    ).reset_index()
    family_rows: list[dict[str, Any]] = []
    for (code, stage), group in pivot.groupby(["municipality_ibge_code", "stage"], sort=True):
        complete = group.dropna(
            subset=["approval_rate_percent", "failure_rate_percent", "dropout_rate_percent"]
        ).sort_values("year")
        movement = "insufficient_joint_observations"
        closure_residual = None
        if len(complete) >= 2:
            first = complete.iloc[0]
            last = complete.iloc[-1]
            directions = []
            for metric in ("approval_rate_percent", "failure_rate_percent", "dropout_rate_percent"):
                change = float(last[metric] - first[metric])
                directions.append(f"{metric}:{'increase' if change > 0 else 'decrease' if change < 0 else 'no_observed_change'}")
            movement = "|".join(directions)
            closure_residual = float(
                last["approval_rate_percent"]
                + last["failure_rate_percent"]
                + last["dropout_rate_percent"]
                - 100.0
            )
        family_rows.append(
            {
                "municipality_ibge_code": code,
                "stage": stage,
                "official_rate_family_joint_movement": movement,
                "official_rate_family_latest_rounding_residual_pp": closure_residual,
            }
        )
    source = source.merge(pd.DataFrame(family_rows), on=["municipality_ibge_code", "stage"], how="left", validate="many_to_one")
    source = _add_municipal_position(source, group_columns=["year", "stage", "metric"])
    source["difference_from_vale_municipal_median_pp"] = source["value"] - pd.to_numeric(source["vale_median"], errors="coerce")
    source["difference_from_rs_municipal_median_pp"] = source["value"] - pd.to_numeric(source["rs_median"], errors="coerce")
    columns = [
        "year", "municipality_ibge_code", "municipality_name", "stage", "metric",
        "value", "value_status", "unit", "network_scope", "source_dependency_qa",
        "source_location_qa", "territorial_lens", "source_table", "period_start_year",
        "period_end_year", "period_start_value", "period_end_value", "observed_year_count",
        "full_window_change_pp", "observed_direction", "vale_median_municipal_change_pp",
        "municipalities_with_increase", "municipalities_with_decrease",
        "municipalities_with_no_observed_change", "municipalities_with_change_observed",
        "change_position_low_to_high_among_ten", "change_percentile_low_to_high_among_ten",
        "official_rate_family_joint_movement", "official_rate_family_latest_rounding_residual_pp",
        "vale_comparison_method", "vale_municipality_count", "vale_minimum", "vale_quartile_1",
        "vale_median", "vale_quartile_3", "vale_maximum", "difference_from_vale_municipal_median_pp",
        "rs_comparison_method", "rs_municipality_count", "rs_minimum", "rs_quartile_1",
        "rs_median", "rs_quartile_3", "rs_maximum", "difference_from_rs_municipal_median_pp",
        "position_low_to_high_among_ten", "percentile_low_to_high_among_ten",
        "regional_rate_value", "regional_rate_status", "regional_rate_method",
        "rs_official_rate_value", "rs_official_rate_status",
    ]
    panel = _stable(source[columns], ["municipality_ibge_code", "stage", "metric", "year"])
    validate_unique_key(panel, ["municipality_ibge_code", "year", "stage", "metric"], label="trajetoria_oficial")
    return panel


def _long_db_rows(
    teachers_rs: pd.DataFrame,
    integral_rs: pd.DataFrame,
    codes: Sequence[str],
    names: Mapping[str, str],
) -> pd.DataFrame:
    teachers = teachers_rs[teachers_rs["municipality_ibge_code"].isin(set(codes))].copy()
    metric_columns = {
        "turmas": "turmas",
        "docentes": "docentes",
        "matriculas": "matriculas",
        "alunos_por_turma": "alunos_por_turma",
        "alunos_por_docente": "estudantes_por_docente",
    }
    rows: list[pd.DataFrame] = []
    for source_column, metric in metric_columns.items():
        part = teachers[["year", "municipality_ibge_code", "stage", source_column]].rename(columns={source_column: "value"})
        part["metric"] = metric
        part["source_table"] = "public.vw_educacao_turmas_docentes"
        part["counting_unit"] = {
            "turmas": "turma",
            "docentes": "docente_reportado_na_etapa",
            "matriculas": "matricula",
            "alunos_por_turma": "turma",
            "estudantes_por_docente": "docente_reportado_na_etapa",
        }[metric]
        rows.append(part)
    integral = integral_rs[integral_rs["municipality_ibge_code"].isin(set(codes))].copy()
    for source_column, metric, counting_unit in (
        ("matriculas_integral", "matriculas_tempo_integral", "matricula"),
        ("percentual_integral", "percentual_tempo_integral", "matricula"),
    ):
        part = integral[["year", "municipality_ibge_code", "stage", source_column]].rename(columns={source_column: "value"})
        part["metric"] = metric
        part["source_table"] = "public.vw_educacao_matriculas"
        part["counting_unit"] = counting_unit
        rows.append(part)
    panel = pd.concat(rows, ignore_index=True)
    panel["municipality_name"] = panel["municipality_ibge_code"].map(names)
    panel["value_status"] = np.where(panel["value"].notna(), "observed", "unavailable")
    panel["unit"] = panel["metric"].map(_unit_for_metric)
    panel["network_scope"] = "total_all_dependencies"
    panel["source_dependency_qa"] = "total"
    panel["source_location_qa"] = "total"
    panel["territorial_lens"] = "school_location"
    panel["reason_code"] = pd.NA

    state_long: list[pd.DataFrame] = []
    for source_column, metric in metric_columns.items():
        p = teachers_rs[["year", "municipality_ibge_code", "stage", source_column]].rename(columns={source_column: "value"})
        p["metric"] = metric
        state_long.append(p)
    for source_column, metric in (
        ("matriculas_integral", "matriculas_tempo_integral"),
        ("percentual_integral", "percentual_tempo_integral"),
    ):
        p = integral_rs[["year", "municipality_ibge_code", "stage", source_column]].rename(columns={source_column: "value"})
        p["metric"] = metric
        state_long.append(p)
    state = pd.concat(state_long, ignore_index=True)
    vale_context = _distribution_context(panel, group_columns=["year", "stage", "metric"], universe_codes=codes, prefix="vale")
    rs_context = _distribution_context(state, group_columns=["year", "stage", "metric"], universe_codes=state["municipality_ibge_code"].unique(), prefix="rs")
    panel = panel.merge(vale_context, on=["year", "stage", "metric"], how="left", validate="many_to_one")
    panel = panel.merge(rs_context, on=["year", "stage", "metric"], how="left", validate="many_to_one")
    return _add_municipal_position(panel, group_columns=["year", "stage", "metric"])


def _condition_rows(codes: Sequence[str], names: Mapping[str, str]) -> pd.DataFrame:
    source = _total_rows(_read_csv(JOB2_ROOT / "2a" / "condicoes_oferta.csv.gz"))
    source = source[
        source["municipality_ibge_code"].isin(set(codes))
        & source["metric"].isin(CONDITION_METRICS)
    ].copy()
    source["year"] = pd.to_numeric(source.pop("ano"), errors="raise").astype("int64")
    source["stage"] = source.pop("dimension").map(_normalize_stage)
    source["value"] = pd.to_numeric(source["value"], errors="coerce")
    source["municipality_name"] = source["municipality_ibge_code"].map(names)
    source["counting_unit"] = source["metric"].map(
        lambda metric: "student_assessed" if metric == "inse_mean" else "school" if metric.startswith("schools_with_") else "turma" if metric == "students_per_class" else "docencia"
    )
    source["unit"] = source["metric"].map(_unit_for_metric)
    source["network_scope"] = "total_all_dependencies"
    source["source_dependency_qa"] = "total"
    source["source_location_qa"] = "total"
    source["territorial_lens"] = "school_location"
    source["reason_code"] = pd.NA
    comparisons = _total_rows(_read_csv(JOB2_ROOT / "2a" / "condicoes_comparacoes.csv.gz"))
    comparisons["year"] = pd.to_numeric(comparisons.pop("ano"), errors="raise").astype("int64")
    comparisons["stage"] = comparisons.pop("dimension").map(_normalize_stage)
    keep = ["year", "stage", "metric", "entity_scope", "comparison_method", "municipality_count", "minimum", "quartile_1", "median", "quartile_3", "maximum"]
    comparisons = comparisons[comparisons["metric"].isin(CONDITION_METRICS)][keep]
    for scope, prefix in (("region", "vale"), ("state", "rs")):
        part = comparisons[comparisons["entity_scope"] == scope].drop(columns="entity_scope")
        part = part.rename(columns={column: f"{prefix}_{column}" for column in part.columns if column not in {"year", "stage", "metric"}})
        source = source.merge(part, on=["year", "stage", "metric"], how="left", validate="many_to_one")
    source = _add_municipal_position(source, group_columns=["year", "stage", "metric"])
    return source


def _normalized_indicator_rows(codes: Sequence[str], names: Mapping[str, str]) -> pd.DataFrame:
    spec = _load_json(SOURCE_SPEC_PATH)
    selected = [
        item for item in spec["selectedMeasures"]
        if item["measureId"].startswith("inep.had.") or item["measureId"].startswith("inep.ied.")
    ]
    observations: dict[tuple[str, str], dict[str, Any]] = {}
    with OBSERVATIONS_PATH.open("r", encoding="utf-8") as stream:
        for line in stream:
            item = json.loads(line)
            code = item.get("municipalityIbge7")
            measure = item.get("measureId", "")
            dimensions = item.get("dimensions", {})
            if (
                code in set(codes)
                and (measure.startswith("inep.had.") or measure.startswith("inep.ied."))
                and str(dimensions.get("dependencia", "")).casefold() == "total"
                and str(dimensions.get("localizacao", "")).casefold() == "total"
            ):
                key = (code, measure)
                if key in observations:
                    raise ValueError(f"Observação normalizada duplicada: {key}")
                observations[key] = item
    rows: list[dict[str, Any]] = []
    for code in codes:
        for definition in selected:
            measure = definition["measureId"]
            item = observations.get((code, measure))
            value_status = item["valueStatus"] if item else "unavailable"
            value = item.get("valueRaw") if item else None
            suffix = measure.split(".")[-1]
            stage = {
                "ed_inf_total": "educacao_infantil",
                "creche": "creche",
                "pre_escola": "pre_escola",
                "fun_total": "fundamental",
                "fun_ai": "anos_iniciais",
                "fun_af": "anos_finais",
                "med_total": "medio",
            }.get(suffix, suffix)
            rows.append(
                {
                    "year": int(definition["periodStart"][:4]),
                    "municipality_ibge_code": code,
                    "municipality_name": names[code],
                    "stage": stage,
                    "metric": measure.replace("inep.", "").replace(".", "_"),
                    "value": value,
                    "value_status": value_status,
                    "unit": definition["unit"],
                    "counting_unit": definition["countingUnit"],
                    "source_table": "SRC_INEP_INDICADORES_EB.normalized_priority_bundle",
                    "network_scope": "total_all_dependencies",
                    "source_dependency_qa": "total",
                    "source_location_qa": "total",
                    "territorial_lens": "school_location",
                    "reason_code": item.get("reasonCode") if item else "municipality_not_materialized_in_normalized_bundle",
                }
            )
    return pd.DataFrame(rows)


def _ird_rows(codes: Sequence[str], names: Mapping[str, str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    frame = pd.read_excel(
        IRD_PATH,
        sheet_name=0,
        header=9,
        converters={"CO_MUNICIPIO": lambda value: str(value).split(".", 1)[0].zfill(7)},
    )
    frame["CO_MUNICIPIO"].map(require_ibge_code)
    frame = frame[
        frame["NO_CATEGORIA"].astype("string").str.casefold().eq("total")
        & frame["NO_DEPENDENCIA"].astype("string").str.casefold().eq("total")
    ].copy()
    definitions = {
        "EDU_BAS_CAT_1": "regularidade_docente_faixa_ate_2",
        "EDU_BAS_CAT_2": "regularidade_docente_faixa_2_a_3",
        "EDU_BAS_CAT_3": "regularidade_docente_faixa_3_a_4",
        "EDU_BAS_CAT_4": "regularidade_docente_faixa_4_a_5",
    }
    all_rows: list[pd.DataFrame] = []
    for column, metric in definitions.items():
        part = frame[["NU_ANO_CENSO", "CO_MUNICIPIO", column]].rename(
            columns={"NU_ANO_CENSO": "year", "CO_MUNICIPIO": "municipality_ibge_code", column: "value"}
        )
        part["metric"] = metric
        all_rows.append(part)
    state = pd.concat(all_rows, ignore_index=True)
    municipal = state[state["municipality_ibge_code"].isin(set(codes))].copy()
    municipal["municipality_name"] = municipal["municipality_ibge_code"].map(names)
    municipal["stage"] = "educacao_basica"
    municipal["value"] = pd.to_numeric(municipal["value"], errors="coerce")
    municipal["value_status"] = np.where(municipal["value"].notna(), "observed", "unavailable")
    municipal["unit"] = "percent"
    municipal["counting_unit"] = "escola"
    municipal["source_table"] = "SRC_INEP_INDICADORES_EB.IRD_MUNICIPIOS_2025"
    municipal["network_scope"] = "total_all_dependencies"
    municipal["source_dependency_qa"] = "total"
    municipal["source_location_qa"] = "total"
    municipal["territorial_lens"] = "school_location"
    municipal["reason_code"] = pd.NA
    state["stage"] = "educacao_basica"
    return municipal, state


def _enrich_context(panel: pd.DataFrame, state_rows: pd.DataFrame | None = None) -> pd.DataFrame:
    result = panel.copy()
    keys = ["year", "stage", "metric"]
    vale = _distribution_context(result, group_columns=keys, universe_codes=result["municipality_ibge_code"].unique(), prefix="vale")
    result = result.merge(vale, on=keys, how="left", validate="many_to_one", suffixes=("", "_new"))
    if state_rows is not None and not state_rows.empty:
        rs = _distribution_context(state_rows, group_columns=keys, universe_codes=state_rows["municipality_ibge_code"].unique(), prefix="rs")
        result = result.merge(rs, on=keys, how="left", validate="many_to_one", suffixes=("", "_new"))
    for prefix in ("vale", "rs"):
        for field in ("municipality_count", "minimum", "quartile_1", "municipal_median", "quartile_3", "maximum"):
            new = f"{prefix}_{field}_new"
            current = f"{prefix}_{field}"
            if new in result:
                if current in result:
                    result[current] = result[current].combine_first(result[new])
                else:
                    result[current] = result[new]
                result = result.drop(columns=new)
    result = _add_municipal_position(result, group_columns=keys)
    result["difference_from_vale_municipal_median"] = result["value"] - pd.to_numeric(result.get("vale_municipal_median"), errors="coerce")
    if "rs_municipal_median" in result:
        result["difference_from_rs_municipal_median"] = result["value"] - pd.to_numeric(result["rs_municipal_median"], errors="coerce")
    else:
        result["difference_from_rs_municipal_median"] = np.nan
    return result


def _teachers_panel(
    teachers_rs: pd.DataFrame,
    integral_rs: pd.DataFrame,
    codes: Sequence[str],
    names: Mapping[str, str],
) -> pd.DataFrame:
    base = _long_db_rows(teachers_rs, integral_rs, codes, names)
    conditions = _condition_rows(codes, names)
    conditions = conditions[conditions["metric"].isin({"teacher_adequacy_percent", "students_per_class"})].copy()
    condition_rs = conditions[[
        "year", "stage", "metric", "rs_municipality_count", "rs_minimum",
        "rs_quartile_1", "rs_median", "rs_quartile_3", "rs_maximum",
    ]].drop_duplicates(["year", "stage", "metric"])
    condition_rs = condition_rs.rename(columns={"rs_median": "rs_municipal_median"})
    common = [
        "year", "municipality_ibge_code", "municipality_name", "stage", "metric", "value",
        "value_status", "unit", "counting_unit", "source_table", "network_scope",
        "source_dependency_qa", "source_location_qa", "territorial_lens", "reason_code",
    ]
    normalized = _normalized_indicator_rows(codes, names)
    ird, ird_state = _ird_rows(codes, names)
    panel = pd.concat([base[common], conditions[common], normalized[common], ird[common]], ignore_index=True)
    panel = panel.merge(condition_rs, on=["year", "stage", "metric"], how="left", validate="many_to_one")

    state_base_parts: list[pd.DataFrame] = []
    for source, mappings in (
        (teachers_rs, (("turmas", "turmas"), ("docentes", "docentes"), ("matriculas", "matriculas"), ("alunos_por_turma", "alunos_por_turma"), ("alunos_por_docente", "estudantes_por_docente"))),
        (integral_rs, (("matriculas_integral", "matriculas_tempo_integral"), ("percentual_integral", "percentual_tempo_integral"))),
    ):
        for source_column, metric in mappings:
            part = source[["year", "municipality_ibge_code", "stage", source_column]].rename(columns={source_column: "value"})
            part["metric"] = metric
            state_base_parts.append(part)
    state_base = pd.concat(state_base_parts, ignore_index=True)
    ird_state = ird_state[["year", "municipality_ibge_code", "stage", "metric", "value"]]
    state_context = pd.concat([state_base, ird_state], ignore_index=True)
    panel = _enrich_context(panel, state_context)
    panel["regional_indicator_value"] = np.nan
    panel["regional_indicator_status"] = "not_applicable"
    panel["regional_context_method"] = "municipal_distribution_not_regional_indicator"
    panel.loc[panel["metric"].isin(COUNT_METRICS | {"alunos_por_turma", "estudantes_por_docente", "percentual_tempo_integral"}), "regional_context_method"] = "exact_components_available_but_panel_preserves_municipal_grain"
    columns = common + [
        "vale_municipality_count", "vale_minimum", "vale_quartile_1", "vale_municipal_median",
        "vale_quartile_3", "vale_maximum", "rs_municipality_count", "rs_minimum",
        "rs_quartile_1", "rs_municipal_median", "rs_quartile_3", "rs_maximum",
        "difference_from_vale_municipal_median", "difference_from_rs_municipal_median",
        "position_low_to_high_among_ten", "percentile_low_to_high_among_ten",
        "regional_indicator_value", "regional_indicator_status", "regional_context_method",
    ]
    for column in columns:
        if column not in panel:
            panel[column] = np.nan
    panel = _stable(panel[columns], ["municipality_ibge_code", "year", "stage", "metric"])
    validate_unique_key(panel, ["municipality_ibge_code", "year", "stage", "metric"], label="docentes_turmas_jornada")
    return panel


def _infant_panel(
    teachers_rs: pd.DataFrame,
    schools_rs: pd.DataFrame,
    codes: Sequence[str],
    names: Mapping[str, str],
) -> pd.DataFrame:
    cohorts = _read_csv(JOB2_ROOT / "2e" / "coortes_demograficas.csv.gz")
    cohorts = cohorts[
        cohorts["entity_scope"].eq("municipality")
        & cohorts["municipality_ibge_code"].isin(set(codes))
        & cohorts["age_group"].isin({"0_3", "4_5"})
    ].copy()
    cohort_rows = cohorts.rename(columns={"estimated_population": "value", "age_group": "stage"})
    cohort_rows["metric"] = "resident_population"
    cohort_rows["stage"] = cohort_rows["stage"].map({"0_3": "creche_age_0_3", "4_5": "pre_school_age_4_5"})
    cohort_rows["unit"] = "people"
    cohort_rows["counting_unit"] = "resident"
    cohort_rows["source_table"] = "public.populacao_idade via Job2 frozen"
    cohort_rows["value_status"] = np.where(pd.to_numeric(cohort_rows["value"], errors="coerce").notna(), "observed", "unavailable")
    cohort_rows["territorial_lens"] = "resident_population"

    infant_stages = {"creche", "pre_escola", "educacao_infantil"}
    teachers = teachers_rs[
        teachers_rs["municipality_ibge_code"].isin(set(codes)) & teachers_rs["stage"].isin(infant_stages)
    ].copy()
    education_parts: list[pd.DataFrame] = []
    for source_column, metric, unit, counting_unit in (
        ("matriculas", "school_enrollments", "count", "matricula"),
        ("turmas", "school_classes", "count", "turma"),
    ):
        part = teachers[["year", "municipality_ibge_code", "stage", source_column]].rename(columns={source_column: "value"})
        part["metric"] = metric
        part["unit"] = unit
        part["counting_unit"] = counting_unit
        part["source_table"] = "public.vw_educacao_turmas_docentes"
        part["value_status"] = np.where(part["value"].notna(), "observed", "unavailable")
        part["territorial_lens"] = "school_location"
        education_parts.append(part)
    schools = schools_rs[
        schools_rs["municipality_ibge_code"].isin(set(codes)) & schools_rs["stage"].isin(infant_stages)
    ].copy()
    schools = schools.rename(columns={"escolas": "value"})
    schools["metric"] = "schools"
    schools["unit"] = "count"
    schools["counting_unit"] = "school"
    schools["source_table"] = "public.vw_educacao_rede_escolar_etapa"
    schools["value_status"] = np.where(schools["value"].notna(), "observed", "unavailable")
    schools["territorial_lens"] = "school_location"
    education_parts.append(schools)

    common = ["year", "municipality_ibge_code", "stage", "value", "metric", "unit", "counting_unit", "source_table", "value_status", "territorial_lens"]
    municipal = pd.concat([cohort_rows[common], *[part[common] for part in education_parts]], ignore_index=True)
    municipal["municipality_name"] = municipal["municipality_ibge_code"].map(names)
    municipal["network_scope"] = np.where(municipal["territorial_lens"].eq("school_location"), "total_all_dependencies", "not_applicable")
    municipal["source_dependency_qa"] = np.where(municipal["territorial_lens"].eq("school_location"), "total", "not_applicable")
    municipal["source_location_qa"] = np.where(municipal["territorial_lens"].eq("school_location"), "total", "not_applicable")
    municipal["birth_window_min_lag_years"] = municipal["stage"].map({"creche_age_0_3": 0, "pre_school_age_4_5": 4, "creche": 0, "pre_escola": 4, "educacao_infantil": 0})
    municipal["birth_window_max_lag_years"] = municipal["stage"].map({"creche_age_0_3": 3, "pre_school_age_4_5": 5, "creche": 3, "pre_escola": 5, "educacao_infantil": 5})
    municipal["birth_window_start_year"] = municipal["year"] - municipal["birth_window_max_lag_years"]
    municipal["birth_window_end_year"] = municipal["year"] - municipal["birth_window_min_lag_years"]
    municipal["migration_limitation"] = "resident_population_and_school_location_are_separate; migration_and_school_choice_are_not_observed_here"

    birth_rows: list[dict[str, Any]] = []
    for code in codes:
        for year in range(2015, 2025):
            birth_rows.append(
                {
                    "year": year,
                    "municipality_ibge_code": code,
                    "municipality_name": names[code],
                    "stage": "births_by_mother_residence",
                    "value": None,
                    "metric": "births",
                    "unit": "births",
                    "counting_unit": "live_birth",
                    "source_table": "SINASC regional endpoints frozen in Job2; municipal series absent",
                    "value_status": "unavailable",
                    "territorial_lens": "resident_population",
                    "network_scope": "not_applicable",
                    "source_dependency_qa": "not_applicable",
                    "source_location_qa": "not_applicable",
                    "birth_window_min_lag_years": 0,
                    "birth_window_max_lag_years": 0,
                    "birth_window_start_year": year,
                    "birth_window_end_year": year,
                    "migration_limitation": "municipal_birth_series_not_materialized; migration_between_birth_and_school_age_not_observed",
                }
            )
    births = pd.DataFrame(birth_rows)
    municipal["value"] = pd.to_numeric(municipal["value"], errors="coerce").astype("Float64")
    births["value"] = pd.Series(pd.array([pd.NA] * len(births), dtype="Float64"))
    panel = pd.concat([municipal, births], ignore_index=True)
    panel = _enrich_context(panel)
    panel["vale_births_endpoint_value"] = np.nan
    panel["vale_births_endpoint_status"] = "not_applicable"
    panel.loc[(panel["metric"] == "births") & panel["year"].eq(2015), ["vale_births_endpoint_value", "vale_births_endpoint_status"]] = [13004.0, "observed"]
    panel.loc[(panel["metric"] == "births") & panel["year"].eq(2024), ["vale_births_endpoint_value", "vale_births_endpoint_status"]] = [9276.0, "observed"]
    panel["vale_births_series_completeness"] = np.where(panel["metric"].eq("births"), "regional_endpoints_only_2015_2024", "not_applicable")
    panel["rs_comparison_status"] = "unavailable_same_contract"
    columns = [
        "year", "municipality_ibge_code", "municipality_name", "stage", "metric", "value",
        "value_status", "unit", "counting_unit", "territorial_lens", "network_scope",
        "source_dependency_qa", "source_location_qa", "source_table", "birth_window_min_lag_years",
        "birth_window_max_lag_years", "birth_window_start_year", "birth_window_end_year",
        "migration_limitation", "vale_municipality_count", "vale_minimum", "vale_quartile_1",
        "vale_municipal_median", "vale_quartile_3", "vale_maximum",
        "difference_from_vale_municipal_median", "position_low_to_high_among_ten",
        "percentile_low_to_high_among_ten", "vale_births_endpoint_value",
        "vale_births_endpoint_status", "vale_births_series_completeness", "rs_comparison_status",
    ]
    panel = _stable(panel[columns], ["municipality_ibge_code", "year", "stage", "metric"])
    validate_unique_key(panel, ["municipality_ibge_code", "year", "stage", "metric"], label="nascimentos_educacao_infantil")
    return panel


def _conditions_panel(teachers: pd.DataFrame, codes: Sequence[str], names: Mapping[str, str]) -> pd.DataFrame:
    conditions = _condition_rows(codes, names)
    condition_rs = conditions[[
        "year", "stage", "metric", "rs_municipality_count", "rs_minimum",
        "rs_quartile_1", "rs_median", "rs_quartile_3", "rs_maximum",
    ]].drop_duplicates(["year", "stage", "metric"])
    condition_rs = condition_rs.rename(columns={"rs_median": "rs_municipal_median"})
    common = [
        "year", "municipality_ibge_code", "municipality_name", "stage", "metric", "value",
        "value_status", "unit", "counting_unit", "source_table", "network_scope",
        "source_dependency_qa", "source_location_qa", "territorial_lens", "reason_code",
    ]
    extras = teachers[
        teachers["metric"].str.startswith(("horas_aula_diaria", "ied_", "regularidade_docente_"))
        | teachers["metric"].isin({"percentual_tempo_integral", "matriculas_tempo_integral", "estudantes_por_docente"})
    ][common].copy()
    panel = pd.concat([conditions[common], extras], ignore_index=True)
    panel = panel.merge(condition_rs, on=["year", "stage", "metric"], how="left", validate="many_to_one")
    panel = _enrich_context(panel)
    panel["profile_role"] = panel["metric"].map(
        lambda metric: "infrastructure_connectivity" if metric.startswith("schools_with_") else "socioeconomic_context" if metric == "inse_mean" else "school_organization_and_workforce"
    )
    panel["causal_interpretation_allowed"] = False
    panel["correlation_used_as_insight"] = False
    columns = common + [
        "profile_role", "vale_municipality_count", "vale_minimum", "vale_quartile_1",
        "vale_municipal_median", "vale_quartile_3", "vale_maximum",
        "difference_from_vale_municipal_median", "position_low_to_high_among_ten",
        "percentile_low_to_high_among_ten", "difference_from_rs_municipal_median",
        "causal_interpretation_allowed", "correlation_used_as_insight",
    ]
    panel = _stable(panel[columns], ["municipality_ibge_code", "year", "stage", "metric"])
    validate_unique_key(panel, ["municipality_ibge_code", "year", "stage", "metric"], label="condicoes_escolares")
    return panel


def _pressure_panel(
    ages_rs: pd.DataFrame,
    codes: Sequence[str],
) -> pd.DataFrame:
    panel = _read_csv(JOB2_ROOT / "2e" / "cenario_mecanico_coortes.csv.gz")
    panel["municipality_ibge_code"] = panel["municipality_ibge_code"].astype("string")
    panel["stage"] = panel["stage"].map(_normalize_stage)
    numeric = [
        "reference_year", "target_year", "source_age_min", "source_age_max",
        "mechanical_cohort_size", "baseline_enrollments_2025", "baseline_schools_2025",
        "cohort_to_baseline_enrollment_ratio",
    ]
    for column in numeric:
        panel[column] = pd.to_numeric(panel[column], errors="coerce")
    ages_2025 = ages_rs[ages_rs["year"].eq(2025) & ages_rs["municipality_ibge_code"].isin(set(codes))].copy()
    audited: list[float | None] = []
    for row in panel.itertuples(index=False):
        relevant = ages_2025[
            ages_2025["age"].between(row.source_age_min, row.source_age_max, inclusive="both")
        ]
        if row.entity_scope == "municipality":
            relevant = relevant[relevant["municipality_ibge_code"].eq(row.municipality_ibge_code)]
        elif row.entity_scope != "region":
            raise ValueError(f"Escopo mecânico inesperado: {row.entity_scope}")
        audited.append(float(relevant["population"].sum()) if not relevant.empty else None)
    panel["audited_mechanical_cohort_size"] = audited
    panel["cohort_size_closure_residual"] = panel["mechanical_cohort_size"] - panel["audited_mechanical_cohort_size"]
    panel["recomputed_ratio"] = panel.apply(
        lambda row: safe_ratio(row["mechanical_cohort_size"], row["baseline_enrollments_2025"]), axis=1
    )
    panel["formula_closure_residual"] = panel["cohort_to_baseline_enrollment_ratio"] - panel["recomputed_ratio"]
    panel["mechanical_difference_from_baseline_enrollments"] = panel["mechanical_cohort_size"] - panel["baseline_enrollments_2025"]
    panel["source_age_window_width"] = panel["source_age_max"] - panel["source_age_min"] + 1
    panel["window_overlap_policy"] = "each_target_year_uses_its_documented_2025_age_window; adjacent_horizons_overlap_by_design"
    panel["unit"] = "people_and_ratio"
    panel["formula"] = "mechanical_cohort_size / baseline_enrollments_2025"
    panel["classification"] = "PRESSAO_MECANICA_TRANSPARENTE"
    panel["is_forecast"] = False
    panel["scenario_without_migration"] = True
    panel["flow_schooling_adjustment"] = False
    panel["mobility_adjustment"] = False
    panel["retention_adjustment"] = False
    panel["school_choice_adjustment"] = False
    sensitivity = panel.groupby(["entity_scope", "municipality_ibge_code", "stage"], dropna=False, as_index=False).agg(
        horizon_min_ratio=("cohort_to_baseline_enrollment_ratio", "min"),
        horizon_max_ratio=("cohort_to_baseline_enrollment_ratio", "max"),
    )
    sensitivity["horizon_ratio_range"] = sensitivity["horizon_max_ratio"] - sensitivity["horizon_min_ratio"]
    panel = panel.merge(sensitivity, on=["entity_scope", "municipality_ibge_code", "stage"], how="left", validate="many_to_one")
    municipal = panel[panel["entity_scope"].eq("municipality")].copy()
    municipal = _add_municipal_position(municipal, group_columns=["target_year", "stage"], value_column="cohort_to_baseline_enrollment_ratio")
    positions = municipal[["municipality_ibge_code", "target_year", "stage", "position_low_to_high_among_ten", "percentile_low_to_high_among_ten"]]
    panel = panel.merge(positions, on=["municipality_ibge_code", "target_year", "stage"], how="left", validate="many_to_one")
    medians = municipal.groupby(["target_year", "stage"], as_index=False)["cohort_to_baseline_enrollment_ratio"].median().rename(columns={"cohort_to_baseline_enrollment_ratio": "vale_municipal_median_ratio"})
    panel = panel.merge(medians, on=["target_year", "stage"], how="left", validate="many_to_one")
    panel["difference_from_vale_municipal_median_ratio"] = panel["cohort_to_baseline_enrollment_ratio"] - panel["vale_municipal_median_ratio"]
    panel["rs_comparison_status"] = "unavailable_same_contract"
    panel = _stable(panel, ["entity_scope", "municipality_ibge_code", "stage", "target_year"])
    validate_unique_key(panel, ["entity_scope", "municipality_ibge_code", "stage", "target_year"], label="pressao_mecanica")
    return panel


CRITERIA = {
    "C1": "PNE_PME_relevance",
    "C2": "mechanism_defined_before_result",
    "C3": "compatible_universes_and_lenses",
    "C4": "coherent_period",
    "C5": "sufficient_stability",
    "C6": "fact_integration",
    "C7": "useful_municipal_difference",
    "C8": "municipality_stage_public_indicator_planning_question",
    "C9": "editorial_communicability",
    "C10": "traceability",
    "C11": "non_redundancy",
    "C12": "increment_beyond_demography",
}


def _opportunity_matrix() -> pd.DataFrame:
    definitions = [
        ("D1_TRAJETORIA_OFICIAL_DESCRITIVA_V1", "A", "READY_FOR_INTERNAL_VISUAL_PROTOTYPE", "Taxas oficiais municipais e distribuições municipais, sem taxa regional recomposta.", "C5_NOT_ASSESSED_WITHOUT_EXACT_DENOMINATORS"),
        ("D1_NASCIMENTOS_EDUCACAO_INFANTIL", "B", "INSUFFICIENT_DATA", "População e rede escolar disponíveis; série municipal de nascimentos ausente.", "MUNICIPAL_BIRTH_SERIES_UNAVAILABLE"),
        ("D1_DOCENTES_TURMAS_JORNADA", "C", "PROMISING_NEEDS_MORE_TESTING", "Docentes, turmas, matrículas e tempo integral completos; HAD e IED parciais.", "HAD_IED_PARTIAL_TEN_MUNICIPALITY_COVERAGE"),
        ("D1_TRAJETORIA_ALUNOS_TURMA", "C", "DESCRIPTIVE_CONTEXT_ONLY", "Série municipal descritiva; correlações ecológicas não são insight.", "NO_CORRELATION_STORY"),
        ("D1_TRAJETORIA_ADEQUACAO_DOCENTE", "C", "DESCRIPTIVE_CONTEXT_ONLY", "Adequação por docência preserva unidade e período.", "NO_CAUSAL_INTERPRETATION"),
        ("D1_TRAJETORIA_HORAS_AULA", "C", "PROMISING_NEEDS_MORE_TESTING", "HAD 2025 local disponível apenas para parte dos dez municípios.", "PARTIAL_LOCAL_NORMALIZATION"),
        ("D1_TRAJETORIA_TEMPO_INTEGRAL", "C", "READY_FOR_INTERNAL_VISUAL_PROTOTYPE", "Numerador e denominador compatíveis por município, ano e etapa.", "DESCRIPTIVE_ONLY"),
        ("D1_TRAJETORIA_ESFORCO_DOCENTE", "C", "PROMISING_NEEDS_MORE_TESTING", "IED 2025 parcial e com quebra metodológica declarada.", "NO_PRE_2025_COMPARISON"),
        ("D1_TRAJETORIA_REGULARIDADE_DOCENTE", "C", "DESCRIPTIVE_CONTEXT_ONLY", "IRD 2025 completo; unidade é escola e não docente.", "SINGLE_YEAR"),
        ("D1_PERFIL_CONDICOES_ESCOLARES_TOTAL_V1", "D", "READY_FOR_INTERNAL_VISUAL_PROTOTYPE", "Perfil municipal com contexto distributivo do Vale, sem inferência causal.", "NO_SYNTHETIC_INDEX"),
        ("D1_TRAJETORIA_INFRAESTRUTURA", "D", "DESCRIPTIVE_CONTEXT_ONLY", "Infraestrutura e conectividade como contexto escolar.", "COUNTS_DO_NOT_ESTABLISH_CAPACITY"),
        ("D1_TRAJETORIA_CONECTIVIDADE", "D", "DESCRIPTIVE_CONTEXT_ONLY", "Conectividade escolar descritiva.", "NO_CAUSAL_INTERPRETATION"),
        ("D1_TRAJETORIA_INSE", "D", "DESCRIPTIVE_CONTEXT_ONLY", "INSE refere-se aos alunos avaliados, não à população residente.", "ASSESSMENT_POPULATION_LENS"),
        ("D1_COORTES_DEMANDA_FUTURA_MECANICA", "E", "READY_FOR_INTERNAL_VISUAL_PROTOTYPE", "Reformulado estritamente como PRESSAO_MECANICA_TRANSPARENTE.", "NOT_A_FORECAST"),
        ("D1_COORTES_TRANSICOES_ETAPAS", "E", "DESCRIPTIVE_CONTEXT_ONLY", "Janelas etárias e sobreposição explicitadas por horizonte.", "NO_FLOW_SCHOOLING_ADJUSTMENT"),
        ("D2_PREVISAO_MATRICULA_POR_COORTE", "E", "REJECTED", "Previsão não é sustentada pela pressão mecânica.", "FORECAST_PROHIBITED"),
        ("D2_NASCIMENTOS_MIGRACAO_OFERTA", "B", "INSUFFICIENT_DATA", "Migração é limitação explícita e não variável observada nessa frente.", "MIGRATION_NOT_OBSERVED"),
        ("D2_TAXA_REGIONAL_TRAJETORIA_EXATA", "A", "INSUFFICIENT_DATA", "Componentes exatos regionais permanecem indisponíveis; H2 segue congelada.", "H2_FROZEN"),
        ("D2_CAUSAL_CONDICOES_TRAJETORIA", "D", "REJECTED", "Perfil de condições não identifica efeito causal.", "CAUSAL_CLAIM_PROHIBITED"),
    ]
    rows: list[dict[str, Any]] = []
    for analysis_id, front, classification, evidence, limitation in definitions:
        row: dict[str, Any] = {
            "analysis_id": analysis_id,
            "front": front,
            "classification": classification,
            "classification_reason": evidence,
            "primary_limitation": limitation,
            "score": pd.NA,
            "automatic_approval": False,
            "external_judgment_required": True,
        }
        for criterion, meaning in CRITERIA.items():
            status = "SUPPORTED_AS_EVIDENCE"
            criterion_evidence = evidence
            if criterion == "C5" and front in {"A", "B", "E"}:
                status = "NOT_ASSESSED_OR_NOT_APPLICABLE"
                criterion_evidence = limitation
            if classification == "INSUFFICIENT_DATA" and criterion in {"C3", "C4", "C6", "C7", "C9"}:
                status = "PARTIAL_OR_NOT_SUPPORTED"
                criterion_evidence = limitation
            if classification == "REJECTED" and criterion in {"C2", "C3", "C6", "C9"}:
                status = "NOT_SUPPORTED"
                criterion_evidence = limitation
            row[f"{criterion.lower()}_meaning"] = meaning
            row[f"{criterion.lower()}_status"] = status
            row[f"{criterion.lower()}_evidence"] = criterion_evidence
        rows.append(row)
    panel = pd.DataFrame(rows)
    if not set(panel["classification"]).issubset(ALLOWED_CLASSIFICATIONS):
        raise ValueError("Classificação analítica fora da taxonomia autorizada.")
    return _stable(panel, ["front", "analysis_id"])


def _series_records(frame: pd.DataFrame, metrics: Iterable[str] | None = None, stages: Iterable[str] | None = None) -> list[dict[str, Any]]:
    selected = frame[frame["municipality_ibge_code"].eq(NOVA_SANTA_RITA_ID)].copy()
    if metrics is not None:
        selected = selected[selected["metric"].isin(set(metrics))]
    if stages is not None:
        selected = selected[selected["stage"].isin(set(stages))]
    columns = [
        column for column in (
            "year", "target_year", "stage", "metric", "value", "value_status",
            "cohort_to_baseline_enrollment_ratio", "mechanical_cohort_size",
            "baseline_enrollments_2025", "vale_median", "vale_municipal_median",
            "vale_municipal_median_ratio", "difference_from_vale_municipal_median",
            "difference_from_vale_municipal_median_pp", "difference_from_vale_municipal_median_ratio",
            "position_low_to_high_among_ten", "rs_median", "rs_municipal_median",
            "rs_comparison_status", "unit", "source_table",
        ) if column in selected.columns
    ]
    return [_json_safe(item) for item in selected[columns].to_dict("records")]


def _nova_santa_rita(
    trajectory: pd.DataFrame,
    infant: pd.DataFrame,
    teachers: pd.DataFrame,
    conditions: pd.DataFrame,
    pressure: pd.DataFrame,
) -> dict[str, Any]:
    base = {
        "period": None,
        "source": None,
        "trackingIndicator": None,
        "planningQuestion": None,
        "limits": None,
        "potentialVisual": None,
        "classification": "DESCRIPTIVE_CONTEXT_ONLY",
    }
    had_metrics = set(teachers.loc[teachers["metric"].str.startswith("had_"), "metric"])
    specifications = [
        ("educacao_infantil", infant, {"resident_population", "school_enrollments", "school_classes", "schools", "births"}, None, "2014–2025; nascimentos regionais apenas 2015/2024", "População estimada, Censo Escolar e endpoints SINASC congelados", "população 0–3/4–5; matrículas; turmas; escolas; nascimentos", "Quais mudanças observadas devem entrar no acompanhamento anual da educação infantil?", "Nascimentos municipais ausentes; migração e escolha de escola não observadas.", "small multiples por lente e etapa", "INSUFFICIENT_DATA"),
        ("fundamental", trajectory, TRAJECTORY_METRICS, {"fundamental"}, "2018–2025 ou 2019–2025", "Inep — taxas oficiais municipais", "aprovação, reprovação, abandono e distorção", "Quais movimentos observados no fundamental merecem acompanhamento?", "Sem denominadores exatos, causalidade ou taxa regional.", "linhas municipais com mediana distributiva", "READY_FOR_INTERNAL_VISUAL_PROTOTYPE"),
        ("anos_iniciais", trajectory, TRAJECTORY_METRICS, {"anos_iniciais"}, "2018–2025 ou 2019–2025", "Inep — taxas oficiais municipais", "família de rendimento e distorção nos anos iniciais", "Como evoluíram os indicadores oficiais nos anos iniciais?", "Sem regra de pequeno denominador.", "linha e posição na distribuição", "READY_FOR_INTERNAL_VISUAL_PROTOTYPE"),
        ("anos_finais", trajectory, TRAJECTORY_METRICS, {"anos_finais"}, "2018–2025 ou 2019–2025", "Inep — taxas oficiais municipais", "família de rendimento e distorção nos anos finais", "Como evoluíram os indicadores oficiais nos anos finais?", "Sem regra de pequeno denominador.", "linha e posição na distribuição", "READY_FOR_INTERNAL_VISUAL_PROTOTYPE"),
        ("medio", trajectory, TRAJECTORY_METRICS, {"medio"}, "2018–2025 ou 2019–2025", "Inep — taxas oficiais municipais", "família de rendimento e distorção no médio", "Como evoluíram os indicadores oficiais no ensino médio?", "Sem denominadores exatos ou taxa regional.", "linha e posição na distribuição", "READY_FOR_INTERNAL_VISUAL_PROTOTYPE"),
        ("docentes", teachers, {"docentes", "estudantes_por_docente", "teacher_adequacy_percent"}, None, "períodos próprios por indicador", "Censo Escolar e indicadores Inep", "docentes, estudantes por docente e adequação", "Quais dimensões do quadro docente acompanhar por etapa?", "Docente reportado na etapa não equivale necessariamente a pessoa única.", "perfil por etapa", "PROMISING_NEEDS_MORE_TESTING"),
        ("jornada", teachers, had_metrics, None, "2025 para HAD", "Inep — HAD", "horas-aula diária", "Que jornada declarada deve ser monitorada por etapa?", "Horas declaradas não são tempo efetivo; pares municipais incompletos.", "dot plot por etapa", "PROMISING_NEEDS_MORE_TESTING"),
        ("tempo_integral", teachers, {"matriculas_tempo_integral", "percentual_tempo_integral"}, None, "2014–2025", "Censo Escolar", "matrículas e percentual em tempo integral", "Como o tempo integral varia por etapa?", "Contagens não demonstram capacidade nem procura efetiva.", "linha por etapa", "READY_FOR_INTERNAL_VISUAL_PROTOTYPE"),
        ("condicoes", conditions, None, None, "períodos próprios por indicador", "Censo Escolar, Inep e Saeb", "organização, docentes, infraestrutura, conectividade e INSE", "Quais condições escolares devem compor o acompanhamento municipal?", "Perfil contextual; sem índice sintético, causalidade ou correlação editorial.", "perfil matricial", "READY_FOR_INTERNAL_VISUAL_PROTOTYPE"),
        ("trajetoria_oficial", trajectory, TRAJECTORY_METRICS, None, "2018–2025 ou 2019–2025", "Inep — taxas oficiais municipais", "aprovação, reprovação, abandono e distorção", "Quais direções observadas exigem acompanhamento?", "H2 permanece congelada e não é reaberta.", "small multiples por etapa e indicador", "READY_FOR_INTERNAL_VISUAL_PROTOTYPE"),
        ("pressao_mecanica", pressure, None, None, "referência 2025; horizontes 2026–2030", "População por idade e rede escolar congelada", "razão mecânica coorte/matrícula-base", "Como os tamanhos mecânicos de coorte variam entre horizontes?", "Sem migração, fluxo escolar, retenção, mobilidade ou escolha de escola; não é previsão.", "tabela horizonte × etapa", "READY_FOR_INTERNAL_VISUAL_PROTOTYPE"),
    ]
    sections: list[dict[str, Any]] = []
    for identifier, frame, metrics, stages, period, source, indicator, question, limits, visual, classification in specifications:
        item = dict(base)
        item.update(
            {
                "id": identifier,
                "series": _series_records(frame, metrics, stages),
                "differenceFromVale": "included_per_series_when_comparable",
                "positionAmongTen": "included_per_series_when_comparable",
                "rsComparison": "official aggregate only when present in the same contract; otherwise municipal distribution or explicit unavailability",
                "period": period,
                "source": source,
                "trackingIndicator": indicator,
                "planningQuestion": question,
                "limits": limits,
                "potentialVisual": visual,
                "classification": classification,
            }
        )
        sections.append(item)
    return {
        "schemaVersion": "nova-santa-rita-job5ga-v1",
        "municipalityIbgeCode": NOVA_SANTA_RITA_ID,
        "municipalityName": "Nova Santa Rita",
        "networkScope": "total_all_dependencies",
        "administrativeDependencyIsAnalyticDimension": False,
        "sectionCount": len(sections),
        "sections": sections,
    }


def _trajectory_contract() -> dict[str, Any]:
    return {
        "schemaVersion": "contrato-trajetoria-oficial-descritiva-v1",
        "objectId": "D1_TRAJETORIA_OFICIAL_DESCRITIVA_V1",
        "isH2": False,
        "h2FrozenState": "NOT_EVALUABLE_DUE_TO_DATA_OR_QA_LIMIT",
        "classification": "READY_FOR_INTERNAL_VISUAL_PROTOTYPE",
        "grain": ["municipality_ibge_code", "year", "stage", "metric"],
        "networkScope": "total_all_dependencies",
        "administrativeDependencyRole": "qa_only",
        "territorialLens": "school_location",
        "officialMetrics": sorted(TRAJECTORY_METRICS),
        "allowedOperations": [
            "municipal_time_series",
            "change_in_percentage_points",
            "observed_direction",
            "joint_movement_of_approval_failure_dropout",
            "distribution_of_changes_across_ten_municipalities",
            "count_municipalities_by_direction",
            "municipal_median_explicitly_labeled",
            "official_rs_value_only_if_same_contract_provides_it",
        ],
        "regionalComparison": {
            "method": "municipal_distribution_not_regional_rate",
            "regionalRateComputed": False,
            "meanOfRatesComputed": False,
            "officialRsRateAvailableInSameContract": False,
            "rsContextProvided": "municipal_distribution_not_official_state_rate",
        },
        "prohibitedOperations": [
            "regional_rate_by_mean_or_sum",
            "small_denominator_rule_without_exact_denominator",
            "rounding_back_calculation",
            "causal_inference",
            "H2_state_change_or_reopening",
        ],
        "valueStatePolicy": {
            "observedZero": "observed",
            "missing": "unavailable",
            "suppressed": "suppressed",
            "notApplicable": "not_applicable",
            "zeroDenominator": "null",
        },
        "potentialPublicEnvelopeOnly": True,
        "finalNarrative": False,
    }


def _limitations() -> dict[str, Any]:
    return {
        "schemaVersion": "limitacoes-job5ga-v1",
        "jobId": JOB_ID,
        "finalState": VERDICT,
        "items": [
            {"front": "A", "code": "EXACT_RATE_DENOMINATORS_UNAVAILABLE", "effect": "No regional rate, denominator-dependent claim or H2 decision."},
            {"front": "A", "code": "OFFICIAL_RS_AGGREGATE_NOT_IN_SAME_CONTRACT", "effect": "RS is shown only as a municipal distribution where available."},
            {"front": "B", "code": "MUNICIPAL_BIRTH_SERIES_UNAVAILABLE", "effect": "Only frozen Vale endpoints for 2015 and 2024 are retained; municipal birth rows are unavailable."},
            {"front": "B", "code": "MIGRATION_NOT_OBSERVED", "effect": "Birth, resident-age and school-location lenses cannot be linked as effective enrolment flow."},
            {"front": "C", "code": "HAD_IED_PARTIAL_NORMALIZED_COVERAGE", "effect": "Local normalized HAD and IED observations do not cover all ten municipalities; missing cells remain unavailable."},
            {"front": "C", "code": "IED_2025_METHOD_BREAK", "effect": "No comparison with prior years is allowed."},
            {"front": "C", "code": "IRD_COUNTING_UNIT_SCHOOL", "effect": "IRD bands are shares of schools, never shares of teachers."},
            {"front": "D", "code": "CONTEXT_PROFILE_ONLY", "effect": "No synthetic index, causal result or correlation insight is produced."},
            {"front": "E", "code": "MECHANICAL_PRESSURE_ONLY", "effect": "No migration, mortality, school flow, retention, mobility or school-choice adjustment; the output is not a forecast."},
        ],
        "publicNarrativeAllowed": False,
        "externalJudgmentRequired": True,
    }


def _map_markdown(matrix: pd.DataFrame) -> str:
    lines = [
        "# Mapa de seções potenciais — Job 5G-A V7",
        "",
        "> Inventário interno para protótipo. Não é narrativa final, publicação ou fechamento do portfólio.",
        "",
        "| Ordem | Seção potencial | Objeto | Classificação | Limite editorial |",
        "|---:|---|---|---|---|",
        "| 1 | Trajetória oficial municipal | D1_TRAJETORIA_OFICIAL_DESCRITIVA_V1 | READY_FOR_INTERNAL_VISUAL_PROTOTYPE | Taxas oficiais municipais; mediana explicitamente distributiva; H2 congelada. |",
        "| 2 | Nascimentos e educação infantil | D1_NASCIMENTOS_EDUCACAO_INFANTIL | INSUFFICIENT_DATA | Nascimentos municipais indisponíveis; migração e escolha de escola como limites. |",
        "| 3 | Docentes, turmas e jornada | D1_DOCENTES_TURMAS_JORNADA | PROMISING_NEEDS_MORE_TESTING | HAD/IED parciais; períodos e unidades próprios. |",
        "| 4 | Perfil de condições escolares | D1_PERFIL_CONDICOES_ESCOLARES_TOTAL_V1 | READY_FOR_INTERNAL_VISUAL_PROTOTYPE | Contexto sem índice sintético, causalidade ou correlação como história. |",
        "| 5 | Pressão mecânica transparente | D1_COORTES_DEMANDA_FUTURA_MECANICA | READY_FOR_INTERNAL_VISUAL_PROTOTYPE | Cenário sem migração; não é previsão. |",
        "",
        "## Bloco obrigatório de Nova Santa Rita",
        "",
        "Reconstruir educação infantil, fundamental, anos iniciais, anos finais, médio, docentes, jornada, tempo integral, condições, trajetória oficial e pressão mecânica usando as séries e posições auditadas do pacote.",
        "",
        "## Exclusões desta rodada",
        "",
        "Job 5G-B, Job 5H, compilador, interface, publicação, narrativa final, aquisição externa e Job 6 permanecem fora do escopo.",
        "",
        f"Matriz reavaliada: {len(matrix)} análises; C1–C12 são evidência sem score ou aprovação automática.",
        "",
    ]
    return "\n".join(lines)


def _artifact(path: Path, root: Path, rows: int | None = None) -> dict[str, Any]:
    return {
        "path": path.relative_to(root).as_posix(),
        "sha256": sha256_file(path),
        "byteSize": path.stat().st_size,
        "rowCount": rows,
    }


def _validate_outputs(root: Path, codes: Sequence[str]) -> dict[str, Any]:
    actual = tuple(sorted(path.name for path in root.iterdir() if path.is_file()))
    if actual != tuple(sorted(OUTPUT_FILES)):
        raise ValueError(f"Output incompleto: {actual}")
    panels = {
        "trajectory": _read_csv(root / OUTPUT_FILES[1]),
        "infant": _read_csv(root / OUTPUT_FILES[2]),
        "teachers": _read_csv(root / OUTPUT_FILES[3]),
        "conditions": _read_csv(root / OUTPUT_FILES[4]),
        "pressure": _read_csv(root / OUTPUT_FILES[5]),
        "matrix": _read_csv(root / OUTPUT_FILES[7]),
    }
    for label, frame in panels.items():
        if label == "matrix":
            continue
        municipal = frame[frame.get("entity_scope", pd.Series("municipality", index=frame.index)).fillna("municipality").eq("municipality")]
        present = set(municipal["municipality_ibge_code"].dropna().astype("string"))
        if present != set(codes):
            raise ValueError(f"{label}: universo municipal divergente: {sorted(present)}")
        municipal["municipality_ibge_code"].dropna().map(require_ibge_code)
        if NOVA_SANTA_RITA_ID not in present:
            raise ValueError(f"{label}: Nova Santa Rita ausente.")
    trajectory = panels["trajectory"]
    if trajectory["regional_rate_value"].notna().any():
        raise ValueError("Foi criada taxa regional proibida.")
    if not trajectory["regional_rate_method"].eq("not_computed").all():
        raise ValueError("Método regional inesperado na trajetória.")
    pressure = panels["pressure"]
    if pressure["is_forecast"].astype("string").str.casefold().isin({"true", "1"}).any():
        raise ValueError("Pressão mecânica foi classificada como previsão.")
    if pd.to_numeric(pressure["formula_closure_residual"], errors="coerce").abs().max() > 1e-12:
        raise ValueError("Fórmula da pressão mecânica não fechou.")
    if pd.to_numeric(pressure["cohort_size_closure_residual"], errors="coerce").abs().max() > 0:
        raise ValueError("Auditoria da coorte mecânica não fechou contra população por idade.")
    if panels["conditions"]["correlation_used_as_insight"].astype("string").str.casefold().isin({"true", "1"}).any():
        raise ValueError("Correlação foi promovida a insight.")
    if not set(panels["matrix"]["classification"]).issubset(ALLOWED_CLASSIFICATIONS):
        raise ValueError("Matriz contém classificação não autorizada.")
    if panels["matrix"]["score"].notna().any():
        raise ValueError("A matriz C1–C12 não pode usar score.")
    statuses: set[str] = set()
    for label in ("trajectory", "infant", "teachers", "conditions"):
        statuses.update(panels[label]["value_status"].dropna().astype(str).unique())
    if not statuses.issubset(ALLOWED_VALUE_STATES):
        raise ValueError(f"Estados de valor inválidos: {sorted(statuses)}")
    return {
        "panelRows": {key: int(len(value)) for key, value in panels.items()},
        "municipalityCount": 10,
        "novaSantaRitaPresent": True,
        "networkScope": "total_all_dependencies",
        "trajectoryRegionalRateComputed": False,
        "mechanicalFormulaMaxResidual": float(pd.to_numeric(pressure["formula_closure_residual"], errors="coerce").abs().max()),
        "mechanicalCohortMaxResidual": float(pd.to_numeric(pressure["cohort_size_closure_residual"], errors="coerce").abs().max()),
        "correlationUsedAsInsight": False,
    }


def _copy_manifest_last(source: Path, target: Path) -> None:
    target.mkdir(parents=True, exist_ok=False)
    files = sorted(path for path in source.iterdir() if path.is_file())
    files.sort(key=lambda path: (path.name == "MANIFEST_JOB5GA.json", path.name))
    for source_path in files:
        target_path = target / source_path.name
        partial = target / f".{source_path.name}.partial"
        shutil.copy2(source_path, partial)
        os.replace(partial, target_path)


def _promote(staging: Path, target: Path) -> str:
    if target.exists() and directory_content_digest(staging) == directory_content_digest(target):
        shutil.rmtree(staging)
        return "unchanged"
    target.parent.mkdir(parents=True, exist_ok=True)
    candidate = Path(tempfile.mkdtemp(prefix=f".{target.name}.candidate-", dir=target.parent))
    backup = target.parent / f".{target.name}.backup"
    if backup.exists():
        shutil.rmtree(backup)
    try:
        shutil.rmtree(candidate)
        _copy_manifest_last(staging, candidate)
        if directory_content_digest(candidate) != directory_content_digest(staging):
            raise RuntimeError("Candidato diverge do staging validado.")
        if target.exists():
            _copy_manifest_last(target, backup)
            shutil.rmtree(target)
        os.replace(candidate, target)
        if directory_content_digest(target) != directory_content_digest(staging):
            raise RuntimeError("Destino promovido diverge do staging.")
        if backup.exists():
            shutil.rmtree(backup)
        shutil.rmtree(staging)
        return "replaced"
    except Exception:
        if target.exists():
            shutil.rmtree(target)
        if backup.exists():
            os.replace(backup, target)
        if candidate.exists():
            shutil.rmtree(candidate)
        raise


def materialize(output_root: Path = DEFAULT_OUTPUT_ROOT) -> dict[str, Any]:
    output_root = output_root.resolve()
    assert_outside_public_data(output_root, REPO_ROOT)
    load_dotenv(DATA_PIPELINE_DIR / ".env")
    contract = _load_json(CONTRACT_PATH)
    verified_inputs = _verify_inputs(contract)
    codes, names, all_rs_codes = _load_scope()
    teachers_rs, integral_rs, schools_rs, ages_rs = _query_education_and_population(all_rs_codes)
    trajectory = _trajectory_panel(codes, names)
    teachers = _teachers_panel(teachers_rs, integral_rs, codes, names)
    infant = _infant_panel(teachers_rs, schools_rs, codes, names)
    conditions = _conditions_panel(teachers, codes, names)
    pressure = _pressure_panel(ages_rs, codes)
    matrix = _opportunity_matrix()
    nsr = _nova_santa_rita(trajectory, infant, teachers, conditions, pressure)
    limitations = _limitations()
    staging = staging_directory_for(output_root)
    try:
        write_json(staging / OUTPUT_FILES[0], _trajectory_contract())
        write_csv_gzip(staging / OUTPUT_FILES[1], trajectory)
        write_csv_gzip(staging / OUTPUT_FILES[2], infant)
        write_csv_gzip(staging / OUTPUT_FILES[3], teachers)
        write_csv_gzip(staging / OUTPUT_FILES[4], conditions)
        write_csv_gzip(staging / OUTPUT_FILES[5], pressure)
        write_json(staging / OUTPUT_FILES[6], nsr)
        write_csv_gzip(staging / OUTPUT_FILES[7], matrix)
        (staging / OUTPUT_FILES[8]).write_text(_map_markdown(matrix), encoding="utf-8", newline="\n")
        write_json(staging / OUTPUT_FILES[9], limitations)
        review = {
            "schemaVersion": "pacote-revisao-externa-job5ga-v1",
            "jobId": JOB_ID,
            "finalState": VERDICT,
            "externalReviewer": "GPT-5.6 Pro",
            "checkpoint": "post_external_judgment_job5f",
            "job5fDecision": "APPROVED_WITH_REQUIRED_ANALYTICAL_AND_EDITORIAL_CORRECTIONS",
            "materialNewAnalyticalValue": "CONFIRMED",
            "mapStatus": "EXPLORATORY_INVENTORY_ONLY",
            "h2State": "NOT_EVALUABLE_DUE_TO_DATA_OR_QA_LIMIT",
            "h2FrozenUnchanged": True,
            "frontClassifications": {
                "A": "READY_FOR_INTERNAL_VISUAL_PROTOTYPE",
                "B": "INSUFFICIENT_DATA",
                "C": "PROMISING_NEEDS_MORE_TESTING",
                "D": "READY_FOR_INTERNAL_VISUAL_PROTOTYPE",
                "E": "READY_FOR_INTERNAL_VISUAL_PROTOTYPE",
            },
            "requiredCorrectionsApplied": [
                "no_editorial_use_of_enrollment_per_thousand",
                "no_eja_reach_coverage_demand_or_sufficiency_interpretation",
                "no_ecological_correlation_as_insight",
                "no_denominator_dependent_rate_claim",
                "mechanical_pressure_not_forecast",
                "no_capacity_conclusion_from_counts",
                "h2_frozen_unchanged",
                "administrative_dependency_qa_only",
            ],
            "database": {"used": True, "mode": "transaction_read_only", "database": "sesi", "queries": 4},
            "networkUsed": False,
            "externalAcquisitionUsed": False,
            "publicNarrativeWritten": False,
            "frontendChanged": False,
            "job6Started": False,
            "limitationsFile": OUTPUT_FILES[9],
            "matrixFile": OUTPUT_FILES[7],
            "stopForExternalJudgment": True,
        }
        write_json(staging / OUTPUT_FILES[10], review)
        pre_manifest_artifacts = [
            _artifact(staging / name, staging, rows={
                OUTPUT_FILES[1]: len(trajectory), OUTPUT_FILES[2]: len(infant),
                OUTPUT_FILES[3]: len(teachers), OUTPUT_FILES[4]: len(conditions),
                OUTPUT_FILES[5]: len(pressure), OUTPUT_FILES[7]: len(matrix),
            }.get(name))
            for name in OUTPUT_FILES[:-1]
        ]
        manifest = {
            "schemaVersion": "manifest-job5ga-v1",
            "jobId": JOB_ID,
            "classification": "DATA_LOGIC",
            "domains": ["DATA_MATERIALIZATION", "ANALYTICAL_TESTING"],
            "finalState": VERDICT,
            "objective": "Materializar e testar demografia, trajetória oficial e condições escolares na primeira direção.",
            "scope": contract["scope"],
            "sourceFingerprints": {
                **verified_inputs,
                "config/regions/rs.json": sha256_file(REGION_CONFIG_PATH),
                "config/municipalities/rs.json": sha256_file(MUNICIPALITY_REGISTRY_PATH),
                "data_pipeline/contracts/vocacoes-pne-v7-job5ga.json": sha256_file(CONTRACT_PATH),
                "data_pipeline/src/vocacoes_pne_job5ga.py": sha256_file(CORE_PATH),
                "data_pipeline/scripts/run_vocacoes_pne_v7_job5ga.py": sha256_file(LAUNCHER_PATH),
            },
            "formulas": {
                "trajectoryChangePp": "official_end_rate - official_start_rate",
                "regionalTrajectoryRate": "not_computed",
                "studentsPerTeacher": "source_view_ratio_at_compatible_municipality_year_stage_grain",
                "integralShare": "source_view_percentage_with_compatible_total_and_integral_enrollments",
                "mechanicalPressure": "mechanical_cohort_size / baseline_enrollments_2025",
            },
            "formulasAltered": False,
            "summary": {
                "municipalityCount": 10,
                "novaSantaRitaPresent": True,
                "trajectoryRows": len(trajectory),
                "infantRows": len(infant),
                "teachersRows": len(teachers),
                "conditionsRows": len(conditions),
                "pressureRows": len(pressure),
                "opportunityRows": len(matrix),
                "outputCount": len(OUTPUT_FILES),
                "manifestSelfExcludedFromArtifactHashes": True,
            },
            "generation": {
                "deterministic": True,
                "transactional": True,
                "manifestLast": True,
                "partialPromotionAllowed": False,
                "databaseUsed": True,
                "databaseReadOnly": True,
                "networkUsed": False,
                "externalAcquisitionUsed": False,
                "publicDataChanged": False,
                "frontendChanged": False,
                "fullBuildUsed": False,
                "compilerUsed": False,
                "previousJobArtifactsChanged": False,
                "publicNarrativeWritten": False,
                "job6Started": False,
            },
            "artifacts": pre_manifest_artifacts,
            "stopForExternalJudgment": True,
            "externalReviewer": "GPT-5.6 Pro",
        }
        write_json(staging / OUTPUT_FILES[11], manifest)
        validation = _validate_outputs(staging, codes)
        promotion = _promote(staging, output_root)
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise
    return {
        "finalState": VERDICT,
        "outputDirectory": output_root.as_posix(),
        "outputCount": len(OUTPUT_FILES),
        "manifestSha256": sha256_file(output_root / OUTPUT_FILES[11]),
        "promotion": promotion,
        "validation": validation,
    }


def validate_existing_output(output_root: Path = DEFAULT_OUTPUT_ROOT) -> dict[str, Any]:
    output_root = output_root.resolve()
    assert_outside_public_data(output_root, REPO_ROOT)
    contract = _load_json(CONTRACT_PATH)
    _verify_inputs(contract)
    codes, _, _ = _load_scope()
    validation = _validate_outputs(output_root, codes)
    return {
        "finalState": VERDICT,
        "outputDirectory": output_root.as_posix(),
        "outputCount": len(OUTPUT_FILES),
        "manifestSha256": sha256_file(output_root / OUTPUT_FILES[11]),
        "promotion": "validated_existing",
        "validation": validation,
    }
