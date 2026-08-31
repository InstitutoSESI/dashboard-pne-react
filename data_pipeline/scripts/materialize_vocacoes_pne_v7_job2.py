"""Materializa, fora de ``public/data``, os painéis analíticos V7 do Job 2."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import unicodedata
from typing import Any, Iterator, Mapping, Sequence
from zipfile import ZipFile

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, URL


REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_PIPELINE_DIR = REPO_ROOT / "data_pipeline"
if str(DATA_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_PIPELINE_DIR))

from src.vocacoes_pne_job2 import (  # noqa: E402
    FORBIDDEN_STOCK_TABLE,
    JOB_ID,
    SCHEMA_VERSION,
    artifact_record,
    assert_outside_public_data,
    canonical_json_bytes,
    eja_distribution_metrics,
    municipal_distribution,
    replace_directory_transactionally,
    require_ibge_code,
    safe_ratio,
    sha256_bytes,
    sha256_file,
    staging_directory_for,
    subjob_state,
    validate_ibge_codes,
    validate_nonnegative,
    validate_unique_key,
    weighted_value,
    write_csv_gzip,
    write_json,
)


DEFAULT_OUTPUT_DIR = REPO_ROOT / ".tmp" / "vocacoes-pne" / JOB_ID
CONTRACT_PATH = DATA_PIPELINE_DIR / "contracts" / "vocacoes-pne-v7-job2.json"
VERSIONED_BRIDGE_PATH = (
    DATA_PIPELINE_DIR
    / "contracts"
    / "vocacoes-pne-course-cbo-rs-v1-projection.json"
)
REGION_CONFIG_PATH = REPO_ROOT / "config" / "regions" / "rs.json"
MUNICIPALITY_REGISTRY_PATH = REPO_ROOT / "config" / "municipalities" / "rs.json"
R6_RESEARCH_PATH = (
    REPO_ROOT
    / "scripts"
    / "checks"
    / "fixtures"
    / "vocacoes-pne"
    / "segunda-saida-pesquisa-vale-do-sinos.json"
)
EXPECTED_R6_HASH = "bee5d4b7a255631eb6dd49a8c0cb80e7ae68d2f8ff0c5ccc26e78047e31754b8"
EXPECTED_BRIDGE_HASH = "e11a6d1d6acf961ca0c28d778158571bef64f108ac32f7b3a9df0e2dac21cf8f"
COURSE_2025_ENTRY = (
    "microdados_censo_escolar_2025_v2/dados/"
    "Tabela_Curso_Tecnico_2025_V2.csv"
)
CAGED_COLUMNS = (
    "competênciamov",
    "uf",
    "município",
    "subclasse",
    "cbo2002ocupação",
    "graudeinstrução",
    "idade",
    "raçacor",
    "sexo",
    "tipomovimentação",
    "indicadoraprendiz",
    "saldomovimentação",
)


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_external_roots() -> tuple[Path, Path]:
    project_root = REPO_ROOT.parents[1]
    sesi_candidates = [
        Path(os.environ["SESI_DB_DIR"]) if os.getenv("SESI_DB_DIR") else None,
        project_root / "SESI" / "DB",
        REPO_ROOT.parent / "SESI" / "DB",
    ]
    cei_candidates = [
        Path(os.environ["CEI_ROOT"]) if os.getenv("CEI_ROOT") else None,
        project_root / "CEI",
    ]

    def first_existing(candidates: Sequence[Path | None], label: str) -> Path:
        for candidate in candidates:
            if candidate is not None and candidate.exists():
                return candidate.resolve()
        raise FileNotFoundError(f"Raiz local não localizada: {label}.")

    return first_existing(sesi_candidates, "SESI/DB"), first_existing(cei_candidates, "CEI")


def _load_region() -> tuple[dict[str, Any], dict[str, str]]:
    region_payload = _load_json(REGION_CONFIG_PATH)
    region = next(
        item for item in region_payload["regions"] if item["slug"] == "vale-do-sinos"
    )
    codes = validate_ibge_codes(region["municipalityIbgeCodes"])
    if region["municipalityCount"] != 10 or len(codes) != 10:
        raise ValueError("O recorte canônico do Vale do Sinos não contém dez municípios.")

    registry = _load_json(MUNICIPALITY_REGISTRY_PATH)
    names = {
        item["ibgeCode"]: item["name"]
        for item in registry["municipalities"]
        if item["ibgeCode"] in codes
    }
    if set(names) != set(codes):
        raise ValueError("O registro municipal não cobre integralmente o Vale do Sinos.")
    if names.get("4313375") != "Nova Santa Rita":
        raise ValueError("Nova Santa Rita não foi preservada no universo municipal.")
    return region, names


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
def _read_only_connection(database: str) -> Iterator[Connection]:
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
                    raise RuntimeError(f"A sessão {database} não está em modo somente leitura.")
                yield connection
            finally:
                transaction.rollback()
    finally:
        engine.dispose()


def _read_sql(database: str, query: str, params: Mapping[str, Any] | None = None) -> pd.DataFrame:
    if FORBIDDEN_STOCK_TABLE in query.lower():
        raise ValueError(f"A tabela defeituosa {FORBIDDEN_STOCK_TABLE} é proibida.")
    with _read_only_connection(database) as connection:
        return pd.read_sql_query(text(query), connection, params=dict(params or {}))


def _stable_sort(frame: pd.DataFrame, columns: Sequence[str] | None = None) -> pd.DataFrame:
    if frame.empty:
        return frame.reset_index(drop=True)
    sort_columns = list(columns or frame.columns)
    return frame.sort_values(sort_columns, kind="mergesort", na_position="last").reset_index(
        drop=True
    )


def _status_for_value(value: Any) -> str:
    return "unavailable" if value is None or pd.isna(value) else "observed"


def _distribution_rows(
    frame: pd.DataFrame,
    *,
    region_codes: set[str],
    group_columns: Sequence[str],
    value_column: str,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    scopes = (
        ("region", frame[frame["municipality_ibge_code"].isin(region_codes)]),
        ("state", frame),
    )
    for scope, scoped in scopes:
        for keys, group in scoped.groupby(list(group_columns), dropna=False, sort=True):
            key_values = keys if isinstance(keys, tuple) else (keys,)
            row = dict(zip(group_columns, key_values, strict=True))
            row.update(
                {
                    "entity_scope": scope,
                    "comparison_method": "municipal_distribution_not_regional_rate",
                    **municipal_distribution(group[value_column]),
                }
            )
            rows.append(row)
    return _stable_sort(pd.DataFrame(rows))


def _melt_metrics(
    frame: pd.DataFrame,
    *,
    id_columns: Sequence[str],
    metrics: Mapping[str, str],
) -> pd.DataFrame:
    melted = frame.melt(
        id_vars=list(id_columns),
        value_vars=list(metrics),
        var_name="source_metric",
        value_name="value",
    )
    melted["metric"] = melted["source_metric"].map(metrics)
    melted["value_status"] = melted["value"].map(_status_for_value)
    return melted.drop(columns=["source_metric"])


def _materialize_2a(
    *,
    region_codes: list[str],
    municipality_names: Mapping[str, str],
) -> dict[str, pd.DataFrame]:
    print("2A: lendo trajetória escolar e condições auxiliares")
    rendimento = _read_sql(
        "sesi",
        """
        SELECT ano, id_municipio AS municipality_ibge_code, dependencia,
               localizacao, etapa_ensino, taxa_aprovacao, taxa_reprovacao,
               taxa_abandono
        FROM public.rendimento_escolar
        WHERE sigla_uf = 'RS' AND localizacao = 'total'
        """,
    )
    rendimento["municipality_ibge_code"].map(require_ibge_code)
    rendimento_long = _melt_metrics(
        rendimento,
        id_columns=(
            "ano",
            "municipality_ibge_code",
            "dependencia",
            "localizacao",
            "etapa_ensino",
        ),
        metrics={
            "taxa_aprovacao": "approval_rate_percent",
            "taxa_reprovacao": "failure_rate_percent",
            "taxa_abandono": "dropout_rate_percent",
        },
    )
    rendimento_long["source_table"] = "public.rendimento_escolar"

    distorcao = _read_sql(
        "sesi",
        """
        SELECT ano, id_municipio AS municipality_ibge_code, dependencia,
               'total'::text AS localizacao, categoria AS etapa_ensino,
               valor AS value
        FROM public.distorcao_idade_serie
        WHERE sigla_uf = 'RS'
        """,
    )
    distorcao["municipality_ibge_code"].map(require_ibge_code)
    distorcao["metric"] = "age_grade_distortion_rate_percent"
    distorcao["value_status"] = distorcao["value"].map(_status_for_value)
    distorcao["source_table"] = "public.distorcao_idade_serie"

    trajectory = pd.concat(
        [rendimento_long, distorcao[rendimento_long.columns]], ignore_index=True
    )
    trajectory["municipality_name"] = trajectory["municipality_ibge_code"].map(
        municipality_names
    )
    trajectory_municipal = _stable_sort(
        trajectory[trajectory["municipality_ibge_code"].isin(region_codes)]
    )
    trajectory_comparisons = _distribution_rows(
        trajectory,
        region_codes=set(region_codes),
        group_columns=(
            "ano",
            "dependencia",
            "localizacao",
            "etapa_ensino",
            "metric",
            "source_table",
        ),
        value_column="value",
    )

    adequacao = _read_sql(
        "sesi",
        """
        SELECT ano, id_municipio AS municipality_ibge_code, dependencia,
               localizacao, etapa, percentual_adequacao AS value
        FROM public.adequacao_docente
        WHERE sigla_uf = 'RS' AND localizacao = 'total'
        """,
    )
    adequacao["metric"] = "teacher_adequacy_percent"
    adequacao["weight"] = float("nan")
    adequacao["numerator"] = float("nan")
    adequacao["denominator"] = float("nan")
    adequacao["source_table"] = "public.adequacao_docente"
    adequacao = adequacao.rename(columns={"etapa": "dimension"})

    alunos_turma = _read_sql(
        "sesi",
        """
        SELECT ano, id_municipio AS municipality_ibge_code, dependencia,
               localizacao, etapa_ensino || ':' || serie_label AS dimension,
               alunos_por_turma AS value
        FROM public.alunos_turma
        WHERE sigla_uf = 'RS' AND localizacao = 'total'
              AND dependencia = 'total'
        """,
    )
    alunos_turma["metric"] = "students_per_class"
    alunos_turma["weight"] = float("nan")
    alunos_turma["numerator"] = float("nan")
    alunos_turma["denominator"] = float("nan")
    alunos_turma["source_table"] = "public.alunos_turma"

    inse = _read_sql(
        "sesi",
        """
        SELECT ano, id_municipio AS municipality_ibge_code, rede AS dependencia,
               'total'::text AS localizacao, 'all_students'::text AS dimension,
               media_inse AS value, qtd_alunos_inse AS weight
        FROM public.inse
        WHERE sigla_uf = 'RS' AND rede = 'total'
        """,
    )
    inse["metric"] = "inse_mean"
    inse["numerator"] = float("nan")
    inse["denominator"] = float("nan")
    inse["source_table"] = "public.inse"

    ideb = _read_sql(
        "sesi",
        """
        SELECT ano, id_municipio AS municipality_ibge_code, rede AS dependencia,
               'total'::text AS localizacao,
               categoria || ':' || indicador AS dimension, valor AS value
        FROM public.saeb_ideb
        WHERE sigla_uf = 'RS' AND indicador = 'ideb'
        """,
    )
    ideb["metric"] = "ideb_score"
    ideb["weight"] = float("nan")
    ideb["numerator"] = float("nan")
    ideb["denominator"] = float("nan")
    ideb["source_table"] = "public.saeb_ideb"

    infrastructure = _read_sql(
        "sesi",
        """
        SELECT ano, id_municipio AS municipality_ibge_code,
               SUM(qntd_escolas)::double precision AS schools,
               SUM(escolas_com_internet)::double precision AS schools_with_internet,
               SUM(escolas_com_banda_larga)::double precision AS schools_with_broadband,
               SUM(in_biblioteca_sala_leitura)::double precision AS schools_with_library,
               SUM(in_quadra_esportes)::double precision AS schools_with_sports_court,
               SUM(in_agua_potavel)::double precision AS schools_with_drinking_water
        FROM public.censo
        WHERE sigla_uf = 'RS'
        GROUP BY ano, id_municipio
        """,
    )
    infrastructure_rows: list[dict[str, Any]] = []
    infrastructure_metrics = {
        "schools_with_internet": "schools_with_internet_percent",
        "schools_with_broadband": "schools_with_broadband_percent",
        "schools_with_library": "schools_with_library_percent",
        "schools_with_sports_court": "schools_with_sports_court_percent",
        "schools_with_drinking_water": "schools_with_drinking_water_percent",
    }
    for row in infrastructure.itertuples(index=False):
        for source_column, metric in infrastructure_metrics.items():
            numerator = getattr(row, source_column)
            infrastructure_rows.append(
                {
                    "ano": row.ano,
                    "municipality_ibge_code": row.municipality_ibge_code,
                    "dependencia": "all",
                    "localizacao": "all",
                    "dimension": "all_schools",
                    "value": safe_ratio(numerator, row.schools, multiplier=100.0),
                    "weight": row.schools,
                    "numerator": numerator,
                    "denominator": row.schools,
                    "metric": metric,
                    "source_table": "public.censo",
                }
            )
    infrastructure_long = pd.DataFrame(infrastructure_rows)
    infrastructure_long["weight"] = infrastructure_long["denominator"]

    conditions = pd.concat(
        [adequacao, alunos_turma, inse, ideb, infrastructure_long],
        ignore_index=True,
        sort=False,
    )
    conditions["municipality_ibge_code"].map(require_ibge_code)
    conditions["municipality_name"] = conditions["municipality_ibge_code"].map(
        municipality_names
    )
    conditions["value_status"] = conditions["value"].map(_status_for_value)
    conditions_municipal = _stable_sort(
        conditions[conditions["municipality_ibge_code"].isin(region_codes)]
    )

    comparison_rows: list[dict[str, Any]] = []
    for scope, scoped in (
        ("region", conditions[conditions["municipality_ibge_code"].isin(region_codes)]),
        ("state", conditions),
    ):
        grouping = [
            "ano",
            "dependencia",
            "localizacao",
            "dimension",
            "metric",
            "source_table",
        ]
        for keys, group in scoped.groupby(grouping, dropna=False, sort=True):
            row = dict(zip(grouping, keys, strict=True))
            has_components = group["numerator"].notna().any() if "numerator" in group else False
            if has_components:
                numerator = pd.to_numeric(group["numerator"], errors="coerce").sum(min_count=1)
                denominator = pd.to_numeric(group["denominator"], errors="coerce").sum(
                    min_count=1
                )
                row.update(
                    {
                        "entity_scope": scope,
                        "comparison_method": "sum_numerator_over_sum_denominator",
                        "value": safe_ratio(numerator, denominator, multiplier=100.0),
                        "numerator": numerator,
                        "denominator": denominator,
                        "municipality_count": int(group["value"].notna().sum()),
                    }
                )
            elif row["metric"] == "inse_mean":
                row.update(
                    {
                        "entity_scope": scope,
                        "comparison_method": "student_weighted_mean",
                        "value": weighted_value(group["value"], group["weight"]),
                        "numerator": None,
                        "denominator": pd.to_numeric(group["weight"], errors="coerce").sum(
                            min_count=1
                        ),
                        "municipality_count": int(group["value"].notna().sum()),
                    }
                )
            else:
                row.update(
                    {
                        "entity_scope": scope,
                        "comparison_method": "municipal_distribution_not_regional_rate",
                        "value": None,
                        "numerator": None,
                        "denominator": None,
                        **municipal_distribution(group["value"]),
                    }
                )
            comparison_rows.append(row)
    conditions_comparisons = _stable_sort(pd.DataFrame(comparison_rows))

    return {
        "trajectory_municipal": trajectory_municipal,
        "trajectory_comparisons": trajectory_comparisons,
        "conditions_municipal": conditions_municipal,
        "conditions_comparisons": conditions_comparisons,
    }


def _read_caged_youth(
    *,
    caged_root: Path,
    municipality_mapping: Mapping[str, str],
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    region_six_digit_codes = set(municipality_mapping)
    cube_parts: list[pd.DataFrame] = []
    state_parts: list[pd.DataFrame] = []
    file_inventory: list[dict[str, Any]] = []
    for year in range(2020, 2026):
        year_file_count = 0
        for month in range(1, 13):
            competence = f"{year}{month:02d}"
            for source_type in ("MOV", "FOR", "EXC"):
                path = caged_root / competence / f"CAGED{source_type}{competence}.txt"
                if not path.exists():
                    if source_type == "MOV":
                        raise FileNotFoundError(f"Arquivo obrigatório do CAGED ausente: {path}")
                    continue
                year_file_count += 1
                byte_size = path.stat().st_size
                file_inventory.append(
                    {
                        "path": path.relative_to(caged_root).as_posix(),
                        "byteSize": byte_size,
                        "empty": byte_size == 0,
                        "sourceType": source_type,
                    }
                )
                if byte_size == 0:
                    if source_type == "MOV":
                        raise ValueError(f"Arquivo MOV obrigatório está vazio: {path}")
                    continue
                for chunk in pd.read_csv(
                    path,
                    sep=";",
                    encoding="utf-8",
                    dtype="string",
                    usecols=list(CAGED_COLUMNS),
                    chunksize=350_000,
                    on_bad_lines="error",
                ):
                    ages = pd.to_numeric(chunk["idade"], errors="coerce")
                    rs_youth = chunk.loc[
                        chunk["uf"].eq("43") & ages.between(15, 24, inclusive="both")
                    ].copy()
                    if rs_youth.empty:
                        continue
                    rs_youth["age_group"] = pd.cut(
                        pd.to_numeric(rs_youth["idade"], errors="raise"),
                        bins=[15, 18, 25],
                        labels=["15_17", "18_24"],
                        right=False,
                    ).astype("string")
                    direction = pd.to_numeric(
                        rs_youth["saldomovimentação"], errors="raise"
                    )
                    invalid_directions = ~direction.isin([-1, 1])
                    if invalid_directions.any():
                        raise ValueError(
                            f"CAGED {path.name}: saldo fora de -1/+1 em "
                            f"{int(invalid_directions.sum())} registros."
                        )
                    rs_youth["event_type"] = direction.map(
                        {1: "admission", -1: "dismissal"}
                    )
                    rs_youth["source_type"] = source_type
                    rs_youth["source_event_count"] = 1
                    rs_youth["adjustment_count"] = -1 if source_type == "EXC" else 1
                    competence_values = rs_youth["competênciamov"].astype("string")
                    valid_competence = competence_values.str.fullmatch(r"[0-9]{6}", na=False)
                    if not valid_competence.all():
                        raise ValueError(f"Competência inválida em {path.name}.")
                    rs_youth["year"] = competence_values.str.slice(0, 4).astype("int64")
                    rs_youth["month"] = competence_values.str.slice(4, 6).astype("int64")
                    rs_youth = rs_youth[rs_youth["year"].between(2020, 2025)].copy()
                    if rs_youth.empty:
                        continue

                    state_parts.append(
                        rs_youth.groupby(
                            ["year", "month", "age_group", "event_type", "source_type"],
                            dropna=False,
                            observed=True,
                            as_index=False,
                        )["adjustment_count"].sum()
                    )

                    regional = rs_youth[
                        rs_youth["município"].isin(region_six_digit_codes)
                    ].copy()
                    if regional.empty:
                        continue
                    regional["municipality_ibge_code"] = regional["município"].map(
                        municipality_mapping
                    )
                    if regional["municipality_ibge_code"].isna().any():
                        raise ValueError("CAGED contém município regional sem código canônico.")
                    regional["occupation_code"] = (
                        regional["cbo2002ocupação"].astype("string").str.zfill(6)
                    )
                    regional["cnae_subclass_code"] = (
                        regional["subclasse"].astype("string").str.zfill(7)
                    )
                    regional["schooling_code"] = (
                        regional["graudeinstrução"].astype("string").str.zfill(2)
                    )
                    regional = regional.rename(
                        columns={
                            "sexo": "sex_code",
                            "raçacor": "race_color_code",
                            "tipomovimentação": "movement_code",
                            "indicadoraprendiz": "apprentice_indicator_code",
                        }
                    )
                    for dimension in (
                        "movement_code",
                        "occupation_code",
                        "cnae_subclass_code",
                        "schooling_code",
                        "sex_code",
                        "race_color_code",
                        "apprentice_indicator_code",
                    ):
                        regional[dimension] = regional[dimension].fillna("unknown")
                    group_columns = [
                        "municipality_ibge_code",
                        "year",
                        "month",
                        "age_group",
                        "event_type",
                        "movement_code",
                        "occupation_code",
                        "cnae_subclass_code",
                        "schooling_code",
                        "sex_code",
                        "race_color_code",
                        "apprentice_indicator_code",
                        "source_type",
                    ]
                    cube_parts.append(
                        regional.groupby(
                            group_columns,
                            dropna=False,
                            observed=True,
                            as_index=False,
                        ).agg(
                            source_event_count=("source_event_count", "sum"),
                            adjustment_count=("adjustment_count", "sum"),
                        )
                    )
        print(f"2B: CAGED {year} processado ({year_file_count} arquivos locais)")

    if not cube_parts or not state_parts:
        raise ValueError("O recorte jovem do CAGED ficou vazio.")
    cube_source = pd.concat(cube_parts, ignore_index=True)
    cube_group_columns = [
        column for column in cube_source.columns if column not in {"source_event_count", "adjustment_count"}
    ]
    cube_source = (
        cube_source.groupby(
            cube_group_columns, dropna=False, observed=True, as_index=False
        )[["source_event_count", "adjustment_count"]]
        .sum()
    )
    pivot_keys = [column for column in cube_group_columns if column != "source_type"]
    cube = cube_source.pivot(
        index=pivot_keys,
        columns="source_type",
        values="source_event_count",
    ).reset_index()
    cube.columns.name = None
    for source_type in ("MOV", "FOR", "EXC"):
        if source_type not in cube:
            cube[source_type] = 0
        else:
            cube[source_type] = cube[source_type].fillna(0)
    cube = cube.rename(
        columns={
            "MOV": "reported_events",
            "FOR": "late_report_events",
            "EXC": "excluded_events",
        }
    )
    cube["adjusted_event_count"] = (
        cube["reported_events"] + cube["late_report_events"] - cube["excluded_events"]
    )
    cube["adjustment_quality"] = cube["adjusted_event_count"].map(
        lambda value: "nonnegative" if value >= 0 else "negative_after_fine_grain_adjustment"
    )
    cube = _stable_sort(cube)

    region_monthly = (
        cube.groupby(
            ["municipality_ibge_code", "year", "month", "age_group", "event_type"],
            as_index=False,
            dropna=False,
            observed=True,
        )["adjusted_event_count"]
        .sum()
        .pivot_table(
            index=["municipality_ibge_code", "year", "month", "age_group"],
            columns="event_type",
            values="adjusted_event_count",
            aggfunc="sum",
            fill_value=0,
            observed=True,
        )
        .reset_index()
    )
    region_monthly.columns.name = None
    for column in ("admission", "dismissal"):
        if column not in region_monthly:
            region_monthly[column] = 0
    region_monthly = region_monthly.rename(
        columns={"admission": "admissions", "dismissal": "dismissals"}
    )
    region_monthly["balance"] = (
        region_monthly["admissions"] - region_monthly["dismissals"]
    )
    region_monthly["entity_scope"] = "municipality"

    state_source = pd.concat(state_parts, ignore_index=True)
    state_source = state_source.groupby(
        ["year", "month", "age_group", "event_type", "source_type"],
        as_index=False,
        observed=True,
        dropna=False,
    )["adjustment_count"].sum()
    state_counts = state_source.groupby(
        ["year", "month", "age_group", "event_type"],
        as_index=False,
        observed=True,
        dropna=False,
    )["adjustment_count"].sum()
    state_monthly = state_counts.pivot_table(
        index=["year", "month", "age_group"],
        columns="event_type",
        values="adjustment_count",
        aggfunc="sum",
        fill_value=0,
        observed=True,
    ).reset_index()
    state_monthly.columns.name = None
    for column in ("admission", "dismissal"):
        if column not in state_monthly:
            state_monthly[column] = 0
    state_monthly = state_monthly.rename(
        columns={"admission": "admissions", "dismissal": "dismissals"}
    )
    state_monthly["balance"] = state_monthly["admissions"] - state_monthly["dismissals"]
    state_monthly["municipality_ibge_code"] = pd.NA
    state_monthly["entity_scope"] = "state"
    monthly = _stable_sort(pd.concat([region_monthly, state_monthly], ignore_index=True))
    validate_nonnegative(monthly, ("admissions", "dismissals"), label="CAGED mensal")

    metadata = {
        "emptyAdjustmentFileCount": sum(
            record["empty"] and record["sourceType"] != "MOV"
            for record in file_inventory
        ),
        "fileCount": len(file_inventory),
        "fileInventorySha256": sha256_bytes(canonical_json_bytes(file_inventory)),
        "files": file_inventory,
        "partial2026Excluded": True,
    }
    return monthly, cube, metadata


def _materialize_2b(
    *,
    region_codes: list[str],
    municipality_names: Mapping[str, str],
    cei_root: Path,
) -> tuple[dict[str, pd.DataFrame], dict[str, Any]]:
    print("2B: lendo RAIS em sessão somente leitura")
    rais = _read_sql(
        "cei",
        """
        SELECT ano AS year, CAST(id_municipio AS text) AS municipality_ibge_code,
               sexo AS sex_code, raca_cor AS race_color_code,
               faixa_etaria AS age_group_code, grau_instrucao AS schooling_code,
               vinculos_ativos AS active_bonds
        FROM public.rais_vinculos
        WHERE faixa_etaria IN ('2', '3')
        """,
    )
    rais["municipality_ibge_code"].map(require_ibge_code)
    rais["age_group"] = rais["age_group_code"].map({"2": "15_17", "3": "18_24"})
    if rais["age_group"].isna().any():
        raise ValueError("A RAIS contém faixa jovem fora do dicionário canônico.")
    rais_region = rais[rais["municipality_ibge_code"].isin(region_codes)].copy()
    rais_region["municipality_name"] = rais_region["municipality_ibge_code"].map(
        municipality_names
    )
    rais_region["entity_scope"] = "municipality"
    rais_region = _stable_sort(rais_region)
    validate_unique_key(
        rais_region,
        (
            "year",
            "municipality_ibge_code",
            "sex_code",
            "race_color_code",
            "age_group_code",
            "schooling_code",
        ),
        label="RAIS jovem dimensional",
    )
    validate_nonnegative(rais_region, ("active_bonds",), label="RAIS jovem dimensional")

    rais_summary_municipal = rais_region.groupby(
        ["year", "municipality_ibge_code", "municipality_name", "age_group"],
        as_index=False,
        dropna=False,
    )["active_bonds"].sum()
    rais_summary_municipal["entity_scope"] = "municipality"
    rais_summary_region = rais_summary_municipal.groupby(
        ["year", "age_group"], as_index=False
    )["active_bonds"].sum()
    rais_summary_region["municipality_ibge_code"] = pd.NA
    rais_summary_region["municipality_name"] = "Vale do Sinos"
    rais_summary_region["entity_scope"] = "region"
    rais_summary_state = rais.groupby(["year", "age_group"], as_index=False)[
        "active_bonds"
    ].sum()
    rais_summary_state["municipality_ibge_code"] = pd.NA
    rais_summary_state["municipality_name"] = "Rio Grande do Sul"
    rais_summary_state["entity_scope"] = "state"
    rais_summary = _stable_sort(
        pd.concat(
            [rais_summary_municipal, rais_summary_region, rais_summary_state],
            ignore_index=True,
        )
    )

    municipality_map_frame = _read_sql(
        "cei",
        """
        SELECT id_municipio, id_municipio_6
        FROM public.municipio
        WHERE sigla_uf = 'RS'
        """,
    )
    region_mapping = {
        row.id_municipio_6: row.id_municipio
        for row in municipality_map_frame.itertuples(index=False)
        if row.id_municipio in region_codes
    }
    if set(region_mapping.values()) != set(region_codes):
        raise ValueError("A ponte municipal CEI não cobre os dez códigos canônicos.")
    for code in region_mapping.values():
        require_ibge_code(code)

    caged_root = cei_root / "db" / "data" / "caged"
    print("2B: varrendo arquivos locais do Novo CAGED (2020–2025)")
    caged_monthly, caged_cube, caged_metadata = _read_caged_youth(
        caged_root=caged_root,
        municipality_mapping=region_mapping,
    )
    caged_monthly["municipality_name"] = caged_monthly["municipality_ibge_code"].map(
        municipality_names
    )
    caged_monthly.loc[
        caged_monthly["entity_scope"].eq("state"), "municipality_name"
    ] = "Rio Grande do Sul"

    return (
        {
            "rais_summary": rais_summary,
            "rais_cube": rais_region,
            "caged_monthly": caged_monthly,
            "caged_cube": caged_cube,
        },
        caged_metadata,
    )


def _materialize_2c(
    *,
    region_codes: list[str],
    municipality_names: Mapping[str, str],
) -> dict[str, pd.DataFrame]:
    print("2C: lendo EJA e componentes censitários em sessão somente leitura")
    count_columns = [
        "mat_eja_total",
        "mat_eja_fundamental_total",
        "mat_eja_medio_total",
        "mat_eja_curso_tecnico_integrada",
        "mat_eja_fic_integrado_fundamental",
        "mat_eja_fic_integrado_medio",
        "mat_eja_integrada_educacao_profissional",
        "mat_eja_integrada_educacao_profissional_publica",
        "mat_eja_integrada_educacao_profissional_privada",
    ]
    eja = _read_sql(
        "sesi",
        """
        SELECT ano AS year, id_municipio AS municipality_ibge_code,
               mat_eja_total, mat_eja_fundamental_total, mat_eja_medio_total,
               mat_eja_curso_tecnico_integrada,
               mat_eja_fic_integrado_fundamental,
               mat_eja_fic_integrado_medio,
               mat_eja_integrada_educacao_profissional,
               mat_eja_integrada_educacao_profissional_publica,
               mat_eja_integrada_educacao_profissional_privada
        FROM public.eja_integrada_educacao_profissional
        WHERE sigla_uf = 'RS'
        """,
    )
    eja["municipality_ibge_code"].map(require_ibge_code)
    eja_region_municipal = eja[eja["municipality_ibge_code"].isin(region_codes)].copy()
    eja_region_municipal["municipality_name"] = eja_region_municipal[
        "municipality_ibge_code"
    ].map(municipality_names)
    eja_region_municipal["entity_scope"] = "municipality"

    def aggregate_eja(frame: pd.DataFrame, scope: str, name: str) -> pd.DataFrame:
        grouped = frame.groupby("year", as_index=False)[count_columns].sum(min_count=1)
        grouped["municipality_ibge_code"] = pd.NA
        grouped["municipality_name"] = name
        grouped["entity_scope"] = scope
        return grouped

    eja_region = aggregate_eja(eja_region_municipal, "region", "Vale do Sinos")
    eja_state = aggregate_eja(eja, "state", "Rio Grande do Sul")
    eja_historical = pd.concat(
        [eja_region_municipal, eja_region, eja_state], ignore_index=True, sort=False
    )
    eja_historical["integrated_share_percent"] = [
        safe_ratio(integrated, total, multiplier=100.0)
        for integrated, total in zip(
            eja_historical["mat_eja_integrada_educacao_profissional"],
            eja_historical["mat_eja_total"],
            strict=True,
        )
    ]
    eja_historical["value_status"] = eja_historical[
        "mat_eja_integrada_educacao_profissional"
    ].map(_status_for_value)
    eja_historical = _stable_sort(eja_historical)
    validate_nonnegative(eja_historical, count_columns, label="EJA histórica")

    demand_components = _read_sql(
        "sesi",
        """
        WITH population AS (
            SELECT id_municipio, SUM(pop_estimada)::double precision AS population_18_plus
            FROM public.populacao_idade
            WHERE sigla_uf = 'RS' AND ano = 2022 AND idade >= 18
            GROUP BY id_municipio
        ), fundamental AS (
            SELECT LPAD(CAST(id_municipio AS text), 7, '0') AS id_municipio,
                   populacao_18_mais_ensino_fundamental_concluido
                       AS fundamental_completed_18_plus
            FROM public.censo_populacao_ensino_fundamental_concluido_18_mais
            WHERE sigla_uf = 'RS' AND ano = 2022
        ), medio AS (
            SELECT LPAD(CAST(id_municipio AS text), 7, '0') AS id_municipio,
                   populacao_18_mais_ensino_medio_concluido
                       AS high_school_completed_18_plus
            FROM public.censo_populacao_ensino_medio_concluido_18_mais
            WHERE sigla_uf = 'RS' AND ano = 2022
        )
        SELECT p.id_municipio AS municipality_ibge_code,
               p.population_18_plus,
               f.fundamental_completed_18_plus,
               m.high_school_completed_18_plus,
               e.mat_eja_fundamental_total AS fundamental_eja_enrollments,
               e.mat_eja_medio_total AS high_school_eja_enrollments
        FROM population p
        JOIN fundamental f ON f.id_municipio = p.id_municipio
        JOIN medio m ON m.id_municipio = p.id_municipio
        JOIN public.eja_integrada_educacao_profissional e
          ON e.id_municipio = p.id_municipio AND e.ano = 2022
        WHERE e.sigla_uf = 'RS'
        """,
    )
    demand_components["municipality_ibge_code"].map(require_ibge_code)
    demand_components = demand_components[
        demand_components["municipality_ibge_code"].isin(region_codes)
    ].copy()
    demand_components["potential_fundamental_eja"] = (
        demand_components["population_18_plus"]
        - demand_components["fundamental_completed_18_plus"]
    )
    demand_components["potential_high_school_eja"] = (
        demand_components["fundamental_completed_18_plus"]
        - demand_components["high_school_completed_18_plus"]
    )
    validate_nonnegative(
        demand_components,
        ("potential_fundamental_eja", "potential_high_school_eja"),
        label="Público potencial da EJA",
    )
    demand_components["municipality_name"] = demand_components[
        "municipality_ibge_code"
    ].map(municipality_names)

    demand_rows: list[dict[str, Any]] = []
    stage_specs = (
        (
            "fundamental",
            "potential_fundamental_eja",
            "fundamental_eja_enrollments",
            "adultos de 18 anos ou mais sem ensino fundamental concluído",
        ),
        (
            "high_school",
            "potential_high_school_eja",
            "high_school_eja_enrollments",
            "adultos de 18 anos ou mais com fundamental e sem médio concluído",
        ),
    )
    for stage, potential_column, enrollment_column, universe_definition in stage_specs:
        regional_potential = float(demand_components[potential_column].sum())
        regional_enrollments = float(demand_components[enrollment_column].sum())
        for row in demand_components.itertuples(index=False):
            potential = getattr(row, potential_column)
            enrollments = getattr(row, enrollment_column)
            demand_rows.append(
                {
                    "year": 2022,
                    "entity_scope": "municipality",
                    "municipality_ibge_code": row.municipality_ibge_code,
                    "municipality_name": row.municipality_name,
                    "stage": stage,
                    "potential_public": potential,
                    "eja_enrollments": enrollments,
                    "universe_definition": universe_definition,
                    "territorial_lens": "resident_population_vs_school_location",
                    **eja_distribution_metrics(
                        potential_public=potential,
                        enrollments=enrollments,
                        regional_potential_public=regional_potential,
                        regional_enrollments=regional_enrollments,
                    ),
                }
            )
        demand_rows.append(
            {
                "year": 2022,
                "entity_scope": "region",
                "municipality_ibge_code": None,
                "municipality_name": "Vale do Sinos",
                "stage": stage,
                "potential_public": regional_potential,
                "eja_enrollments": regional_enrollments,
                "universe_definition": universe_definition,
                "territorial_lens": "resident_population_vs_school_location",
                **eja_distribution_metrics(
                    potential_public=regional_potential,
                    enrollments=regional_enrollments,
                    regional_potential_public=regional_potential,
                    regional_enrollments=regional_enrollments,
                ),
            }
        )
    demand_offer = _stable_sort(pd.DataFrame(demand_rows))
    return {"eja_historical": eja_historical, "demand_offer": demand_offer}


def _resolve_bridge_path() -> Path:
    bridge = _load_json(VERSIONED_BRIDGE_PATH)
    source = bridge.get("source", {})
    statistics = bridge.get("statistics", {})
    if source.get("sha256") != EXPECTED_BRIDGE_HASH:
        raise ValueError("A projeção versionada da ponte cursos–CBO diverge do hash-fonte contratado.")
    if len(bridge.get("mappings", [])) != 115:
        raise ValueError("A projeção versionada da ponte cursos–CBO não contém os 115 pares contratados.")
    if statistics.get("unmappedCourses") != 22:
        raise ValueError("A projeção versionada da ponte cursos–CBO não preserva os 22 cursos não mapeados.")
    return VERSIONED_BRIDGE_PATH


def _load_course_sources(sesi_db_root: Path) -> tuple[pd.DataFrame, dict[str, Any]]:
    censo_root = sesi_db_root / "data" / "censo_escolar"
    frames: list[pd.DataFrame] = []
    source_records: list[dict[str, Any]] = []
    for year in (2023, 2024):
        path = (
            censo_root
            / f"microdados_censo_escolar_{year}"
            / "dados"
            / f"suplemento_cursos_tecnicos_{year}.csv"
        )
        frame = pd.read_csv(path, sep=";", encoding="cp1252", dtype="string")
        frames.append(frame)
        source_records.append(
            {
                "year": year,
                "path": str(path),
                "byteSize": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )

    zip_path = censo_root / "microdados_censo_escolar_2025.zip"
    with ZipFile(zip_path) as archive:
        with archive.open(COURSE_2025_ENTRY) as stream:
            frames.append(
                pd.read_csv(
                    stream,
                    sep=";",
                    encoding="cp1252",
                    dtype="string",
                    low_memory=False,
                )
            )
    source_records.append(
        {
            "year": 2025,
            "path": str(zip_path),
            "entry": COURSE_2025_ENTRY,
            "byteSize": zip_path.stat().st_size,
            "sha256": sha256_file(zip_path),
        }
    )
    return pd.concat(frames, ignore_index=True), {"files": source_records}


def _materialize_2d(
    *,
    region_codes: list[str],
    municipality_names: Mapping[str, str],
    sesi_db_root: Path,
) -> tuple[dict[str, pd.DataFrame], dict[str, Any]]:
    print("2D: lendo inventário local de cursos técnicos 2023–2025")
    raw_courses, course_source_metadata = _load_course_sources(sesi_db_root)
    raw_courses = raw_courses[raw_courses["CO_MUNICIPIO"].isin(region_codes)].copy()
    courses = raw_courses.rename(
        columns={
            "NU_ANO_CENSO": "year",
            "CO_MUNICIPIO": "municipality_ibge_code",
            "NO_MUNICIPIO": "source_municipality_name",
            "CO_ENTIDADE": "school_code",
            "NO_ENTIDADE": "school_name",
            "ID_AREA_CURSO_PROFISSIONAL": "technological_axis_code",
            "NO_AREA_CURSO_PROFISSIONAL": "technological_axis_name",
            "CO_CURSO_EDUC_PROFISSIONAL": "course_code",
            "NO_CURSO_EDUC_PROFISSIONAL": "course_name",
            "QT_CURSO_TEC": "class_count",
            "QT_MAT_CURSO_TEC": "technical_enrollments",
        }
    )
    course_columns = [
        "year",
        "municipality_ibge_code",
        "source_municipality_name",
        "school_code",
        "school_name",
        "technological_axis_code",
        "technological_axis_name",
        "course_code",
        "course_name",
        "class_count",
        "technical_enrollments",
    ]
    courses = courses[course_columns].copy()
    courses["year"] = pd.to_numeric(courses["year"], errors="raise").astype("int64")
    courses["class_count"] = pd.to_numeric(courses["class_count"], errors="raise").astype(
        "int64"
    )
    courses["technical_enrollments"] = pd.to_numeric(
        courses["technical_enrollments"], errors="raise"
    ).astype("int64")
    courses["municipality_ibge_code"].map(require_ibge_code)
    courses["municipality_name"] = courses["municipality_ibge_code"].map(
        municipality_names
    )
    courses["territorial_lens"] = "school_location"
    courses = _stable_sort(courses)
    validate_unique_key(
        courses,
        ("year", "school_code", "course_code"),
        label="Oferta técnica por escola e curso",
    )
    validate_nonnegative(
        courses, ("class_count", "technical_enrollments"), label="Oferta técnica"
    )

    census_technical = _read_sql(
        "sesi",
        """
        SELECT ano AS year, id_municipio AS municipality_ibge_code,
               SUM(mat_profissional_tecnico)::bigint AS census_technical_enrollments
        FROM public.censo
        WHERE sigla_uf = 'RS' AND ano BETWEEN 2023 AND 2025
        GROUP BY ano, id_municipio
        """,
    )
    census_technical["municipality_ibge_code"].map(require_ibge_code)
    census_technical = census_technical[
        census_technical["municipality_ibge_code"].isin(region_codes)
    ].copy()
    course_totals = courses.groupby(
        ["year", "municipality_ibge_code"], as_index=False
    ).agg(
        course_rows=("course_code", "size"),
        course_count=("course_code", "nunique"),
        technological_axis_count=("technological_axis_name", "nunique"),
        course_technical_enrollments=("technical_enrollments", "sum"),
    )
    coverage = pd.MultiIndex.from_product(
        [range(2023, 2026), region_codes], names=["year", "municipality_ibge_code"]
    ).to_frame(index=False)
    coverage = coverage.merge(
        census_technical,
        on=["year", "municipality_ibge_code"],
        how="left",
        validate="one_to_one",
    ).merge(
        course_totals,
        on=["year", "municipality_ibge_code"],
        how="left",
        validate="one_to_one",
    )
    for column in (
        "course_rows",
        "course_count",
        "technological_axis_count",
        "course_technical_enrollments",
    ):
        coverage[column] = coverage[column].fillna(0).astype("int64")
    if coverage["census_technical_enrollments"].isna().any():
        raise ValueError("O agregado censitário não cobre os dez municípios em 2023–2025.")
    coverage["reconciliation_difference"] = (
        coverage["course_technical_enrollments"]
        - coverage["census_technical_enrollments"]
    )
    if coverage["reconciliation_difference"].ne(0).any():
        bad = coverage[coverage["reconciliation_difference"].ne(0)]
        raise ValueError(f"A oferta por curso não reconciliou em {len(bad)} município-anos.")
    coverage["availability_status"] = coverage.apply(
        lambda row: (
            "observed_zero"
            if row["course_technical_enrollments"] == 0
            else "observed"
        ),
        axis=1,
    )
    coverage["municipality_name"] = coverage["municipality_ibge_code"].map(
        municipality_names
    )
    coverage = _stable_sort(coverage)

    print("2D: lendo painel ocupacional RAIS 2019–2025")
    occupations = _read_sql(
        "cei",
        """
        WITH occupation_panel AS (
            SELECT ano AS year, CAST(id_municipio AS text) AS municipality_ibge_code,
                   cnae_2_subclasse AS cnae_subclass_code,
                   ocupacao AS occupation_code, vinculos_ativos AS active_bonds
            FROM public.rais_vinculos_ocupacao
            WHERE ano BETWEEN 2019 AND 2024
            UNION ALL
            SELECT ano AS year, CAST(id_municipio AS text) AS municipality_ibge_code,
                   cnae_2_subclasse AS cnae_subclass_code,
                   cod_ocupacao AS occupation_code, vinculos_ativos AS active_bonds
            FROM public.rais_ocupacoes_rs_25
            WHERE ano = 2025
        )
        SELECT p.year, p.municipality_ibge_code, p.cnae_subclass_code,
               p.occupation_code, o.desc_ocupacao AS occupation_name,
               c.subclasse AS cnae_subclass_name, p.active_bonds
        FROM occupation_panel p
        LEFT JOIN public.ocupacao o ON o.cod_ocupacao = p.occupation_code
        LEFT JOIN public.cnae c ON c.cod_subclasse = p.cnae_subclass_code
        """,
    )
    occupations["municipality_ibge_code"].map(require_ibge_code)
    occupations = occupations[occupations["municipality_ibge_code"].isin(region_codes)].copy()
    occupations["occupation_code"] = occupations["occupation_code"].astype("string").str.zfill(6)
    occupations["cnae_subclass_code"] = (
        occupations["cnae_subclass_code"].astype("string").str.zfill(7)
    )
    occupations["occupation_subgroup_code"] = occupations["occupation_code"].str.slice(
        0, 2
    )
    occupations["municipality_name"] = occupations["municipality_ibge_code"].map(
        municipality_names
    )
    occupations["entity_scope"] = "municipality"
    region_occupations = occupations.groupby(
        [
            "year",
            "cnae_subclass_code",
            "cnae_subclass_name",
            "occupation_code",
            "occupation_name",
            "occupation_subgroup_code",
        ],
        as_index=False,
        dropna=False,
    )["active_bonds"].sum()
    region_occupations["municipality_ibge_code"] = pd.NA
    region_occupations["municipality_name"] = "Vale do Sinos"
    region_occupations["entity_scope"] = "region"
    occupations = _stable_sort(
        pd.concat([occupations, region_occupations], ignore_index=True, sort=False)
    )
    validate_nonnegative(occupations, ("active_bonds",), label="Painel ocupacional")

    bridge_path = _resolve_bridge_path()
    bridge = _load_json(bridge_path)
    bridge_rows = pd.DataFrame(bridge["mappings"])
    bridge_rows = bridge_rows.rename(
        columns={
            "courseCode": "course_code",
            "occupationSubgroupCode": "occupation_subgroup_code",
            "correspondenceType": "correspondence_type",
        }
    )
    bridge_columns = [
        "course_code",
        "occupation_subgroup_code",
        "correspondence_type",
    ]
    bridge_rows = bridge_rows[bridge_columns].copy()
    bridge_rows["course_code"] = bridge_rows["course_code"].astype("string")
    bridge_rows["occupation_subgroup_code"] = bridge_rows[
        "occupation_subgroup_code"
    ].astype("string")

    courses_2025 = courses[courses["year"].eq(2025)].copy()
    courses_bridge = courses_2025.merge(
        bridge_rows,
        on="course_code",
        how="left",
        validate="many_to_many",
    )
    courses_bridge["bridge_status"] = courses_bridge[
        "occupation_subgroup_code"
    ].map(lambda value: "mapped" if pd.notna(value) else "unmapped")
    courses_bridge["additivity_note"] = (
        "course enrollments repeat across mapped CBO subgroups and are not additive"
    )
    regional_subgroups = (
        occupations[
            occupations["entity_scope"].eq("region") & occupations["year"].eq(2025)
        ]
        .groupby("occupation_subgroup_code", as_index=False)["active_bonds"]
        .sum()
        .rename(columns={"active_bonds": "regional_active_bonds_2025"})
    )
    regional_subgroups["occupation_subgroup_name"] = regional_subgroups[
        "occupation_subgroup_code"
    ].map(bridge["occupationSubgroups"])
    if regional_subgroups.loc[
        regional_subgroups["occupation_subgroup_code"].isin(
            bridge_rows["occupation_subgroup_code"]
        ),
        "occupation_subgroup_name",
    ].isna().any():
        raise ValueError("A projeção da ponte não nomeia todos os subgrupos CBO utilizados.")
    courses_bridge = courses_bridge.merge(
        regional_subgroups,
        on="occupation_subgroup_code",
        how="left",
        validate="many_to_one",
    )
    courses_bridge["occupational_presence_status"] = courses_bridge.apply(
        lambda row: (
            "not_mapped"
            if row["bridge_status"] == "unmapped"
            else (
                "present"
                if pd.notna(row["regional_active_bonds_2025"])
                and row["regional_active_bonds_2025"] > 0
                else "absent"
            )
        ),
        axis=1,
    )
    courses_bridge = _stable_sort(courses_bridge)

    mapped_codes = set(bridge_rows["course_code"].dropna())
    course_level = courses_2025.groupby(
        ["course_code", "course_name", "technological_axis_name"], as_index=False
    )["technical_enrollments"].sum()
    course_level["bridge_status"] = course_level["course_code"].map(
        lambda code: "mapped" if code in mapped_codes else "unmapped"
    )
    coverage_bridge = (
        course_level.groupby("bridge_status", as_index=False)
        .agg(
            course_count=("course_code", "nunique"),
            technical_enrollments=("technical_enrollments", "sum"),
        )
    )
    coverage_bridge["course_share"] = coverage_bridge["course_count"] / course_level[
        "course_code"
    ].nunique()
    coverage_bridge["enrollment_share"] = coverage_bridge[
        "technical_enrollments"
    ] / course_level["technical_enrollments"].sum()
    coverage_bridge["bridge_source_sha256"] = EXPECTED_BRIDGE_HASH
    coverage_bridge["bridge_projection_sha256"] = sha256_file(bridge_path)
    coverage_bridge["semantic_limit"] = (
        "formative normative correspondence; no adequacy or sufficiency claim"
    )
    coverage_bridge = _stable_sort(coverage_bridge)

    metadata = {
        "bridgePath": bridge_path.relative_to(REPO_ROOT).as_posix(),
        "bridgeProjectionSha256": sha256_file(bridge_path),
        "bridgeSourceSha256": EXPECTED_BRIDGE_HASH,
        "bridgeStatistics": bridge["statistics"],
        "courseSources": course_source_metadata,
    }
    return (
        {
            "courses": courses,
            "course_coverage": coverage,
            "occupations": occupations,
            "courses_bridge": courses_bridge,
            "bridge_coverage": coverage_bridge,
        },
        metadata,
    )


def _age_group(age: int) -> str:
    if age <= 3:
        return "0_3"
    if age <= 5:
        return "4_5"
    if age <= 10:
        return "6_10"
    if age <= 14:
        return "11_14"
    if age <= 17:
        return "15_17"
    if age <= 24:
        return "18_24"
    if age <= 29:
        return "25_29"
    if age <= 59:
        return "30_59"
    if age <= 79:
        return "60_79"
    return "80_plus"


def _extract_r6_context(
    *,
    municipality_names: Mapping[str, str],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    actual_hash = sha256_file(R6_RESEARCH_PATH)
    if actual_hash != EXPECTED_R6_HASH:
        raise ValueError("O artefato de pesquisa V6 diverge do hash basal contratado.")
    payload = _load_json(R6_RESEARCH_PATH)
    mobility_candidate = next(
        candidate for candidate in payload["candidates"] if candidate["id"] == "vds-deslocamento-oferta"
    )
    cohort_candidate = next(
        candidate for candidate in payload["candidates"] if candidate["id"] == "vds-coortes-rede"
    )

    def fact(candidate: Mapping[str, Any], fact_id: str) -> Mapping[str, Any]:
        return next(item for item in candidate["facts"] if item["id"] == fact_id)

    municipality_values = fact(
        mobility_candidate, "vds-deslocamento-oferta.municipios"
    )["values"]
    mobility_rows: list[dict[str, Any]] = []
    for entry in municipality_values["entries"]:
        code = require_ibge_code(entry["ibgeCode"])
        if code not in municipality_names:
            raise ValueError(f"Município inesperado na mobilidade V6: {code}.")
        for universe, values in entry["universes"].items():
            mobility_rows.append(
                {
                    "year": 2022,
                    "entity_scope": "municipality",
                    "municipality_ibge_code": code,
                    "municipality_name": municipality_names[code],
                    "universe": universe,
                    "students_total": values["total"],
                    "students_outside_municipality": values["outsideMunicipality"],
                    "outside_share_percent": values["outsideSharePercent"],
                    "residual": None,
                    "state_outside_share_percent": None,
                    "territorial_lens": "student_residence",
                    "evidence_class": "preliminary",
                }
            )
    region_values = fact(
        mobility_candidate, "vds-deslocamento-oferta.deslocamento"
    )["values"]
    state_comparison = {
        entry["universe"]: entry["stateOutsideSharePercent"]
        for entry in fact(
            mobility_candidate, "vds-deslocamento-oferta.comparacao-rs"
        )["values"]["entries"]
    }
    for entry in region_values["entries"]:
        mobility_rows.append(
            {
                "year": 2022,
                "entity_scope": "region",
                "municipality_ibge_code": None,
                "municipality_name": "Vale do Sinos",
                "universe": entry["universe"],
                "students_total": entry["total"],
                "students_outside_municipality": entry["outsideMunicipality"],
                "outside_share_percent": entry["outsideSharePercent"],
                "residual": entry["residual"],
                "state_outside_share_percent": state_comparison[entry["universe"]],
                "territorial_lens": "student_residence",
                "evidence_class": "preliminary",
            }
        )
    mobility = _stable_sort(pd.DataFrame(mobility_rows))

    context = {
        "schemaVersion": "vocacoes-pne-v7-job2-context-v6-v1",
        "source": {
            "path": R6_RESEARCH_PATH.relative_to(REPO_ROOT).as_posix(),
            "sha256": actual_hash,
            "sourceCatalog": payload["sourceCatalog"],
        },
        "births": fact(cohort_candidate, "vds-coortes-rede.nascimentos")["values"],
        "population0To14": fact(
            cohort_candidate, "vds-coortes-rede.populacao-0-14"
        )["values"],
        "schoolNetwork": fact(cohort_candidate, "vds-coortes-rede.rede")["values"],
        "mobility": {
            "year": 2022,
            "destinationAvailable": False,
            "municipalityCount": municipality_values["tests"]["municipalityCount"],
            "sourceEvidenceClass": "preliminary",
        },
        "caveats": [
            "A mobilidade mede residentes que estudam fora; a fonte V6 não identifica o destino.",
            "O dado do Censo Demográfico 2022 foi classificado como preliminar na V6.",
            "O contexto V6 é reutilizado sem recalcular metodologia alternativa.",
        ],
    }
    return mobility, context


def _materialize_2e(
    *,
    region_codes: list[str],
    municipality_names: Mapping[str, str],
) -> tuple[dict[str, Any], dict[str, Any]]:
    print("2E: lendo demografia e rede escolar em sessão somente leitura")
    population = _read_sql(
        "sesi",
        """
        SELECT ano AS year, id_municipio AS municipality_ibge_code,
               idade AS age, SUM(pop_estimada)::bigint AS estimated_population
        FROM public.populacao_idade
        WHERE sigla_uf = 'RS' AND id_municipio = ANY(:codes)
        GROUP BY ano, id_municipio, idade
        """,
        {"codes": region_codes},
    )
    population["municipality_ibge_code"].map(require_ibge_code)
    population["age"] = pd.to_numeric(population["age"], errors="raise").astype("int64")
    population["age_group"] = population["age"].map(_age_group)
    population["municipality_name"] = population["municipality_ibge_code"].map(
        municipality_names
    )
    municipal_cohorts = population.groupby(
        ["year", "municipality_ibge_code", "municipality_name", "age_group"],
        as_index=False,
    )["estimated_population"].sum()
    municipal_cohorts["entity_scope"] = "municipality"
    region_cohorts = municipal_cohorts.groupby(
        ["year", "age_group"], as_index=False
    )["estimated_population"].sum()
    region_cohorts["municipality_ibge_code"] = pd.NA
    region_cohorts["municipality_name"] = "Vale do Sinos"
    region_cohorts["entity_scope"] = "region"
    state_cohorts = _read_sql(
        "sesi",
        """
        SELECT ano AS year, idade AS age, SUM(pop_estimada)::bigint AS estimated_population
        FROM public.populacao_idade
        WHERE sigla_uf = 'RS'
        GROUP BY ano, idade
        """,
    )
    state_cohorts["age"] = pd.to_numeric(state_cohorts["age"], errors="raise").astype(
        "int64"
    )
    state_cohorts["age_group"] = state_cohorts["age"].map(_age_group)
    state_cohorts = state_cohorts.groupby(
        ["year", "age_group"], as_index=False
    )["estimated_population"].sum()
    state_cohorts["municipality_ibge_code"] = pd.NA
    state_cohorts["municipality_name"] = "Rio Grande do Sul"
    state_cohorts["entity_scope"] = "state"
    cohorts = _stable_sort(
        pd.concat([municipal_cohorts, region_cohorts, state_cohorts], ignore_index=True)
    )
    cohorts["territorial_lens"] = "resident_population"
    cohorts["evidence_class"] = "estimated_indirect"
    validate_nonnegative(cohorts, ("estimated_population",), label="Coortes demográficas")

    network = _read_sql(
        "sesi",
        """
        SELECT ano AS year, id_municipio AS municipality_ibge_code,
               SUM(qntd_escolas)::bigint AS schools,
               SUM(mat_infantil_pre)::bigint AS preschool_enrollments,
               SUM(mat_fundamental)::bigint AS fundamental_enrollments,
               SUM(mat_medio)::bigint AS high_school_enrollments,
               SUM(mat_profissional_tecnico)::bigint AS technical_enrollments,
               SUM(mat_eja)::bigint AS eja_enrollments
        FROM public.censo
        WHERE sigla_uf = 'RS' AND id_municipio = ANY(:codes)
        GROUP BY ano, id_municipio
        """,
        {"codes": region_codes},
    )
    network["municipality_ibge_code"].map(require_ibge_code)
    network["municipality_name"] = network["municipality_ibge_code"].map(
        municipality_names
    )
    network["entity_scope"] = "municipality"
    network_columns = [
        "schools",
        "preschool_enrollments",
        "fundamental_enrollments",
        "high_school_enrollments",
        "technical_enrollments",
        "eja_enrollments",
    ]
    network_region = network.groupby("year", as_index=False)[network_columns].sum()
    network_region["municipality_ibge_code"] = pd.NA
    network_region["municipality_name"] = "Vale do Sinos"
    network_region["entity_scope"] = "region"
    network_state = _read_sql(
        "sesi",
        """
        SELECT ano AS year, SUM(qntd_escolas)::bigint AS schools,
               SUM(mat_infantil_pre)::bigint AS preschool_enrollments,
               SUM(mat_fundamental)::bigint AS fundamental_enrollments,
               SUM(mat_medio)::bigint AS high_school_enrollments,
               SUM(mat_profissional_tecnico)::bigint AS technical_enrollments,
               SUM(mat_eja)::bigint AS eja_enrollments
        FROM public.censo
        WHERE sigla_uf = 'RS'
        GROUP BY ano
        """,
    )
    network_state["municipality_ibge_code"] = pd.NA
    network_state["municipality_name"] = "Rio Grande do Sul"
    network_state["entity_scope"] = "state"
    network = _stable_sort(pd.concat([network, network_region, network_state], ignore_index=True))
    network["territorial_lens"] = "school_location"
    network["evidence_class"] = "observed"
    validate_nonnegative(network, network_columns, label="Rede escolar")

    school_stage_counts = _read_sql(
        "sesi",
        """
        SELECT id_municipio AS municipality_ibge_code,
               COUNT(DISTINCT cod_escola) FILTER (WHERE mat_infantil_pre > 0)
                   AS preschool_schools,
               COUNT(DISTINCT cod_escola) FILTER (WHERE mat_fundamental > 0)
                   AS fundamental_schools,
               COUNT(DISTINCT cod_escola) FILTER (WHERE mat_medio > 0)
                   AS high_school_schools
        FROM public.censo_escolas
        WHERE sigla_uf = 'RS' AND ano = 2025 AND id_municipio = ANY(:codes)
        GROUP BY id_municipio
        """,
        {"codes": region_codes},
    )
    baseline_network = network[
        network["entity_scope"].eq("municipality") & network["year"].eq(2025)
    ].merge(
        school_stage_counts,
        on="municipality_ibge_code",
        how="left",
        validate="one_to_one",
    )
    stage_specs = (
        ("preschool", 4, 5, "preschool_enrollments", "preschool_schools"),
        ("fundamental", 6, 14, "fundamental_enrollments", "fundamental_schools"),
        ("high_school", 15, 17, "high_school_enrollments", "high_school_schools"),
    )
    population_2025 = population[population["year"].eq(2025)].copy()
    scenario_rows: list[dict[str, Any]] = []
    for target_year in range(2026, 2031):
        horizon = target_year - 2025
        for stage, target_min, target_max, enrollment_column, school_column in stage_specs:
            source_min = max(0, target_min - horizon)
            source_max = target_max - horizon
            for row in baseline_network.itertuples(index=False):
                source_population = population_2025[
                    population_2025["municipality_ibge_code"].eq(
                        row.municipality_ibge_code
                    )
                    & population_2025["age"].between(source_min, source_max)
                ]["estimated_population"].sum()
                baseline_enrollments = getattr(row, enrollment_column)
                scenario_rows.append(
                    {
                        "reference_year": 2025,
                        "target_year": target_year,
                        "entity_scope": "municipality",
                        "municipality_ibge_code": row.municipality_ibge_code,
                        "municipality_name": row.municipality_name,
                        "stage": stage,
                        "source_age_min": source_min,
                        "source_age_max": source_max,
                        "mechanical_cohort_size": int(source_population),
                        "baseline_enrollments_2025": baseline_enrollments,
                        "baseline_schools_2025": getattr(row, school_column),
                        "cohort_to_baseline_enrollment_ratio": safe_ratio(
                            source_population, baseline_enrollments
                        ),
                        "scenario_method": "fixed_2025_cohort_aging_no_migration_mortality_or_entry_adjustment",
                        "evidence_class": "calculated",
                    }
                )
    scenario_municipal = pd.DataFrame(scenario_rows)
    scenario_region = scenario_municipal.groupby(
        [
            "reference_year",
            "target_year",
            "stage",
            "source_age_min",
            "source_age_max",
            "scenario_method",
            "evidence_class",
        ],
        as_index=False,
    ).agg(
        mechanical_cohort_size=("mechanical_cohort_size", "sum"),
        baseline_enrollments_2025=("baseline_enrollments_2025", "sum"),
        baseline_schools_2025=("baseline_schools_2025", "sum"),
    )
    scenario_region["entity_scope"] = "region"
    scenario_region["municipality_ibge_code"] = pd.NA
    scenario_region["municipality_name"] = "Vale do Sinos"
    scenario_region["cohort_to_baseline_enrollment_ratio"] = [
        safe_ratio(cohort, enrollments)
        for cohort, enrollments in zip(
            scenario_region["mechanical_cohort_size"],
            scenario_region["baseline_enrollments_2025"],
            strict=True,
        )
    ]
    scenario = _stable_sort(
        pd.concat([scenario_municipal, scenario_region], ignore_index=True, sort=False)
    )

    mobility, v6_context = _extract_r6_context(municipality_names=municipality_names)
    metadata = {
        "r6ResearchPath": R6_RESEARCH_PATH.relative_to(REPO_ROOT).as_posix(),
        "r6ResearchSha256": sha256_file(R6_RESEARCH_PATH),
        "mobilityDestinationAvailable": False,
        "scenarioIsForecast": False,
    }
    return (
        {
            "cohorts": cohorts,
            "network": network,
            "scenario": scenario,
            "mobility": mobility,
            "v6_context": v6_context,
        },
        metadata,
    )


ARTIFACT_SPECS: dict[str, dict[str, Any]] = {
    "2a/trajetoria_municipal.csv.gz": {
        "grain": [
            "year",
            "municipality_ibge_code",
            "dependencia",
            "localizacao",
            "etapa_ensino",
            "metric",
        ],
        "period": "2018/2025 (rendimento); 2019/2025 (distorção)",
        "lens": "school_location",
        "unit": "percent",
        "aggregation_rule": "municipal observed rate; no regional averaging",
    },
    "2a/trajetoria_comparacoes.csv.gz": {
        "grain": [
            "entity_scope",
            "year",
            "dependencia",
            "localizacao",
            "etapa_ensino",
            "metric",
        ],
        "period": "2018/2025 (rendimento); 2019/2025 (distorção)",
        "lens": "school_location",
        "unit": "municipal distribution",
        "aggregation_rule": "min/q1/median/q3/max; not a regional rate",
    },
    "2a/condicoes_oferta.csv.gz": {
        "grain": [
            "year",
            "municipality_ibge_code",
            "dependencia",
            "localizacao",
            "dimension",
            "metric",
        ],
        "period": "2011/2025 depending on source",
        "lens": "school_location",
        "unit": "source-specific",
        "aggregation_rule": "municipal observation with explicit components when available",
    },
    "2a/condicoes_comparacoes.csv.gz": {
        "grain": [
            "entity_scope",
            "year",
            "dependencia",
            "localizacao",
            "dimension",
            "metric",
        ],
        "period": "2011/2025 depending on source",
        "lens": "school_location",
        "unit": "source-specific",
        "aggregation_rule": "sum numerator/sum denominator, student weighting, or municipal distribution",
    },
    "2b/rais_estoque_jovem_anual.csv.gz": {
        "grain": ["entity_scope", "year", "municipality_ibge_code", "age_group"],
        "period": "2019/2025",
        "lens": "workplace_municipality",
        "unit": "active formal bonds",
        "aggregation_rule": "sum active_bonds",
    },
    "2b/rais_cubo_jovem.csv.gz": {
        "grain": [
            "year",
            "municipality_ibge_code",
            "sex_code",
            "race_color_code",
            "age_group_code",
            "schooling_code",
        ],
        "period": "2019/2025",
        "lens": "workplace_municipality",
        "unit": "active formal bonds",
        "aggregation_rule": "source natural grain; unique key validated",
    },
    "2b/caged_jovens_mensal.csv.gz": {
        "grain": ["entity_scope", "municipality_ibge_code", "year", "month", "age_group"],
        "period": "2020-01/2025-12; partial 2026 excluded",
        "lens": "workplace_municipality",
        "unit": "adjusted movement events",
        "aggregation_rule": "MOV + FOR - EXC by original admission/dismissal direction",
    },
    "2b/caged_jovens_cubo.csv.gz": {
        "grain": [
            "municipality_ibge_code",
            "year",
            "month",
            "age_group",
            "event_type",
            "movement_code",
            "occupation_code",
            "cnae_subclass_code",
            "schooling_code",
            "sex_code",
            "race_color_code",
            "apprentice_indicator_code",
        ],
        "period": "2020-01/2025-12; partial 2026 excluded",
        "lens": "workplace_municipality",
        "unit": "movement events and adjustments",
        "aggregation_rule": "MOV, FOR and EXC preserved; adjusted count = MOV + FOR - EXC",
    },
    "2c/eja_integrada_historica.csv.gz": {
        "grain": ["entity_scope", "year", "municipality_ibge_code"],
        "period": "2014/2025",
        "lens": "school_location",
        "unit": "enrollments and percent",
        "aggregation_rule": "sum enrollment components; ratio recomputed after aggregation",
    },
    "2c/eja_demanda_oferta_2022.csv.gz": {
        "grain": ["entity_scope", "municipality_ibge_code", "year", "stage"],
        "period": "2022",
        "lens": "resident_population_vs_school_location",
        "unit": "people, enrollments, fractions and enrollments per thousand",
        "aggregation_rule": "canonical V7 EJA formulas; difference stored as 0-1 fraction",
    },
    "2d/oferta_cursos_tecnicos.csv.gz": {
        "grain": ["year", "school_code", "course_code"],
        "period": "2023/2025",
        "lens": "school_location",
        "unit": "classes and technical enrollments",
        "aggregation_rule": "observed Censo Escolar course-school rows",
    },
    "2d/cobertura_oferta_municipal.csv.gz": {
        "grain": ["year", "municipality_ibge_code"],
        "period": "2023/2025",
        "lens": "school_location",
        "unit": "courses, axes and enrollments",
        "aggregation_rule": "course inventory reconciled to public.censo; observed zero explicit",
    },
    "2d/ocupacoes_rais.csv.gz": {
        "grain": [
            "entity_scope",
            "year",
            "municipality_ibge_code",
            "cnae_subclass_code",
            "occupation_code",
        ],
        "period": "2019/2025",
        "lens": "workplace_municipality",
        "unit": "active formal bonds",
        "aggregation_rule": "sum active bonds; municipality and region kept separate",
    },
    "2d/cursos_cbo_2025.csv.gz": {
        "grain": ["school_code", "course_code", "occupation_subgroup_code"],
        "period": "2025",
        "lens": "school_location_vs_workplace_municipality",
        "unit": "non-additive course enrollment context and active bonds",
        "aggregation_rule": "existing V1 normative bridge; repeated enrollments are not additive",
    },
    "2d/cobertura_ponte_2025.csv.gz": {
        "grain": ["bridge_status"],
        "period": "2025",
        "lens": "regional",
        "unit": "courses, enrollments and shares",
        "aggregation_rule": "mapped/unmapped coverage without adequacy claim",
    },
    "2e/coortes_demograficas.csv.gz": {
        "grain": ["entity_scope", "year", "municipality_ibge_code", "age_group"],
        "period": "2014/2025",
        "lens": "resident_population",
        "unit": "estimated people",
        "aggregation_rule": "sum age-sex population estimates into declared age groups",
    },
    "2e/rede_escolar.csv.gz": {
        "grain": ["entity_scope", "year", "municipality_ibge_code"],
        "period": "2014/2025",
        "lens": "school_location",
        "unit": "schools and enrollments",
        "aggregation_rule": "sum source components across dependency and location",
    },
    "2e/cenario_mecanico_coortes.csv.gz": {
        "grain": ["entity_scope", "target_year", "municipality_ibge_code", "stage"],
        "period": "reference 2025; scenarios 2026/2030",
        "lens": "resident_population_vs_school_location",
        "unit": "people, enrollments, schools and ratio",
        "aggregation_rule": "mechanical cohort aging; not a forecast",
    },
    "2e/mobilidade_educacional_2022.csv.gz": {
        "grain": ["entity_scope", "municipality_ibge_code", "year", "universe"],
        "period": "2022",
        "lens": "student_residence",
        "unit": "students and percent",
        "aggregation_rule": "reused V6 snapshot; destination unavailable",
    },
    "2e/contexto_v6.json": {
        "grain": "regional V6 context",
        "period": "2015/2025 with births through 2024 and mobility in 2022",
        "lens": "mixed_explicit",
        "unit": "source-specific",
        "aggregation_rule": "verbatim structured extraction from hashed V6 research artifact",
    },
}


def _save_frame(
    *,
    staging: Path,
    relative_path: str,
    frame: pd.DataFrame,
    subjob: str,
    artifacts: list[dict[str, Any]],
) -> None:
    spec = ARTIFACT_SPECS[relative_path]
    path = staging / relative_path
    write_csv_gzip(path, frame)
    artifacts.append(
        artifact_record(
            root=staging,
            path=path,
            frame=frame,
            subjob=subjob,
            grain=spec["grain"],
            period=spec["period"],
            lens=spec["lens"],
            unit=spec["unit"],
            aggregation_rule=spec["aggregation_rule"],
        )
    )


def _save_json_artifact(
    *,
    staging: Path,
    relative_path: str,
    payload: Any,
    subjob: str,
    artifacts: list[dict[str, Any]],
) -> None:
    spec = ARTIFACT_SPECS[relative_path]
    path = staging / relative_path
    write_json(path, payload)
    artifacts.append(
        artifact_record(
            root=staging,
            path=path,
            frame=None,
            subjob=subjob,
            grain=spec["grain"],
            period=spec["period"],
            lens=spec["lens"],
            unit=spec["unit"],
            aggregation_rule=spec["aggregation_rule"],
        )
    )


def _paths_for_subjob(artifacts: Sequence[Mapping[str, Any]], subjob: str) -> list[str]:
    return sorted(item["path"] for item in artifacts if item["subjob"] == subjob)


def _validate_contract_artifacts(
    contract: Mapping[str, Any], artifacts: Sequence[Mapping[str, Any]]
) -> None:
    actual = {item["path"] for item in artifacts}
    for subjob in contract["subjobs"]:
        missing = set(subjob["minimumArtifacts"]) - actual
        if missing:
            raise ValueError(
                f"{subjob['id']}: artefatos mínimos ausentes: {sorted(missing)}."
            )


def materialize(output_directory: Path) -> dict[str, Any]:
    assert_outside_public_data(output_directory, REPO_ROOT)
    load_dotenv(DATA_PIPELINE_DIR / ".env")
    contract = _load_json(CONTRACT_PATH)
    region, municipality_names = _load_region()
    region_codes = list(region["municipalityIbgeCodes"])
    sesi_db_root, cei_root = _resolve_external_roots()

    staging = staging_directory_for(output_directory)
    artifacts: list[dict[str, Any]] = []
    states: list[dict[str, Any]] = []
    metadata: dict[str, Any] = {}
    try:
        print("ESTADO 2A IN_PROGRESS")
        frames_2a = _materialize_2a(
            region_codes=region_codes, municipality_names=municipality_names
        )
        _save_frame(
            staging=staging,
            relative_path="2a/trajetoria_municipal.csv.gz",
            frame=frames_2a["trajectory_municipal"],
            subjob="2A",
            artifacts=artifacts,
        )
        _save_frame(
            staging=staging,
            relative_path="2a/trajetoria_comparacoes.csv.gz",
            frame=frames_2a["trajectory_comparisons"],
            subjob="2A",
            artifacts=artifacts,
        )
        _save_frame(
            staging=staging,
            relative_path="2a/condicoes_oferta.csv.gz",
            frame=frames_2a["conditions_municipal"],
            subjob="2A",
            artifacts=artifacts,
        )
        _save_frame(
            staging=staging,
            relative_path="2a/condicoes_comparacoes.csv.gz",
            frame=frames_2a["conditions_comparisons"],
            subjob="2A",
            artifacts=artifacts,
        )
        states.append(
            subjob_state(
                "2A",
                status="READY",
                reason="Séries municipais materializadas e comparações sem média simples.",
                artifacts=_paths_for_subjob(artifacts, "2A"),
                validations={
                    "municipalityCount": int(
                        frames_2a["trajectory_municipal"]["municipality_ibge_code"].nunique()
                    ),
                    "simpleRegionalAverageUsed": False,
                    "publicDataChanged": False,
                },
            )
        )
        print("ESTADO 2A READY")

        print("ESTADO 2B IN_PROGRESS")
        frames_2b, caged_metadata = _materialize_2b(
            region_codes=region_codes,
            municipality_names=municipality_names,
            cei_root=cei_root,
        )
        metadata["caged"] = caged_metadata
        for relative_path, key in (
            ("2b/rais_estoque_jovem_anual.csv.gz", "rais_summary"),
            ("2b/rais_cubo_jovem.csv.gz", "rais_cube"),
            ("2b/caged_jovens_mensal.csv.gz", "caged_monthly"),
            ("2b/caged_jovens_cubo.csv.gz", "caged_cube"),
        ):
            _save_frame(
                staging=staging,
                relative_path=relative_path,
                frame=frames_2b[key],
                subjob="2B",
                artifacts=artifacts,
            )
        states.append(
            subjob_state(
                "2B",
                status="READY",
                reason="RAIS e Novo CAGED local cobrem estoque e fluxo jovem; 2026 parcial foi excluído.",
                artifacts=_paths_for_subjob(artifacts, "2B"),
                validations={
                    "raisMunicipalityCount": int(
                        frames_2b["rais_cube"]["municipality_ibge_code"].nunique()
                    ),
                    "cagedMunicipalityCount": int(
                        frames_2b["caged_cube"]["municipality_ibge_code"].nunique()
                    ),
                    "cagedPartial2026Excluded": True,
                    "emptyAdjustmentFileCount": caged_metadata[
                        "emptyAdjustmentFileCount"
                    ],
                    "negativeFineGrainAdjustmentRows": int(
                        frames_2b["caged_cube"]["adjusted_event_count"].lt(0).sum()
                    ),
                    "negativeMonthlyAdmissionOrDismissalRows": int(
                        frames_2b["caged_monthly"][["admissions", "dismissals"]]
                        .lt(0)
                        .any(axis=1)
                        .sum()
                    ),
                    "firstEmploymentClaimMaterialized": False,
                    "defectiveStockTableUsed": False,
                },
            )
        )
        print("ESTADO 2B READY")

        print("ESTADO 2C IN_PROGRESS")
        frames_2c = _materialize_2c(
            region_codes=region_codes, municipality_names=municipality_names
        )
        _save_frame(
            staging=staging,
            relative_path="2c/eja_integrada_historica.csv.gz",
            frame=frames_2c["eja_historical"],
            subjob="2C",
            artifacts=artifacts,
        )
        _save_frame(
            staging=staging,
            relative_path="2c/eja_demanda_oferta_2022.csv.gz",
            frame=frames_2c["demand_offer"],
            subjob="2C",
            artifacts=artifacts,
        )
        states.append(
            subjob_state(
                "2C",
                status="READY",
                reason="Demanda e oferta foram materializadas com as fórmulas canônicas e escala fracionária preservada.",
                artifacts=_paths_for_subjob(artifacts, "2C"),
                validations={
                    "municipalityCount": int(
                        frames_2c["demand_offer"]
                        .loc[lambda frame: frame["entity_scope"].eq("municipality"), "municipality_ibge_code"]
                        .nunique()
                    ),
                    "distributionDifferenceStoredScale": "fraction_0_1",
                    "denominatorZeroProducesNull": True,
                },
            )
        )
        print("ESTADO 2C READY")

        print("ESTADO 2D IN_PROGRESS")
        frames_2d, metadata_2d = _materialize_2d(
            region_codes=region_codes,
            municipality_names=municipality_names,
            sesi_db_root=sesi_db_root,
        )
        metadata["occupationsAndTraining"] = metadata_2d
        for relative_path, key in (
            ("2d/oferta_cursos_tecnicos.csv.gz", "courses"),
            ("2d/cobertura_oferta_municipal.csv.gz", "course_coverage"),
            ("2d/ocupacoes_rais.csv.gz", "occupations"),
            ("2d/cursos_cbo_2025.csv.gz", "courses_bridge"),
            ("2d/cobertura_ponte_2025.csv.gz", "bridge_coverage"),
        ):
            _save_frame(
                staging=staging,
                relative_path=relative_path,
                frame=frames_2d[key],
                subjob="2D",
                artifacts=artifacts,
            )
        mapped_coverage = frames_2d["bridge_coverage"].set_index("bridge_status")
        states.append(
            subjob_state(
                "2D",
                status="READY",
                reason="Oferta 2023–2025, ocupações 2019–2025 e ponte V1 compatível foram materializadas sem alegação de adequação.",
                artifacts=_paths_for_subjob(artifacts, "2D"),
                validations={
                    "municipalityCount": int(
                        frames_2d["course_coverage"]["municipality_ibge_code"].nunique()
                    ),
                    "observedZeroMunicipalityYears": int(
                        frames_2d["course_coverage"]["availability_status"]
                        .eq("observed_zero")
                        .sum()
                    ),
                    "reconciliationDifferenceAbsolute": int(
                        frames_2d["course_coverage"]["reconciliation_difference"]
                        .abs()
                        .sum()
                    ),
                    "mappedCourseCount": int(mapped_coverage.loc["mapped", "course_count"]),
                    "mappedEnrollmentShare": float(
                        mapped_coverage.loc["mapped", "enrollment_share"]
                    ),
                    "adequacyClaimMaterialized": False,
                },
            )
        )
        print("ESTADO 2D READY")

        print("ESTADO 2E IN_PROGRESS")
        frames_2e, metadata_2e = _materialize_2e(
            region_codes=region_codes, municipality_names=municipality_names
        )
        metadata["demographyNetworkMobility"] = metadata_2e
        for relative_path, key in (
            ("2e/coortes_demograficas.csv.gz", "cohorts"),
            ("2e/rede_escolar.csv.gz", "network"),
            ("2e/cenario_mecanico_coortes.csv.gz", "scenario"),
            ("2e/mobilidade_educacional_2022.csv.gz", "mobility"),
        ):
            _save_frame(
                staging=staging,
                relative_path=relative_path,
                frame=frames_2e[key],
                subjob="2E",
                artifacts=artifacts,
            )
        _save_json_artifact(
            staging=staging,
            relative_path="2e/contexto_v6.json",
            payload=frames_2e["v6_context"],
            subjob="2E",
            artifacts=artifacts,
        )
        states.append(
            subjob_state(
                "2E",
                status="READY",
                reason="Coortes, rede, cenário mecânico e mobilidade V6 foram relacionados com lentes e caveats explícitos.",
                artifacts=_paths_for_subjob(artifacts, "2E"),
                validations={
                    "municipalityCount": int(
                        frames_2e["cohorts"]
                        .loc[lambda frame: frame["entity_scope"].eq("municipality"), "municipality_ibge_code"]
                        .nunique()
                    ),
                    "mobilityMunicipalityCount": int(
                        frames_2e["mobility"]
                        .loc[lambda frame: frame["entity_scope"].eq("municipality"), "municipality_ibge_code"]
                        .nunique()
                    ),
                    "mobilityDestinationAvailable": False,
                    "scenarioIsForecast": False,
                },
            )
        )
        print("ESTADO 2E READY")

        _validate_contract_artifacts(contract, artifacts)
        artifacts = sorted(artifacts, key=lambda item: item["path"])
        manifest = {
            "schemaVersion": SCHEMA_VERSION,
            "jobId": JOB_ID,
            "classification": "DATA_LOGIC",
            "region": {
                "stateCode": "RS",
                "slug": region["slug"],
                "name": region["name"],
                "municipalityCount": region["municipalityCount"],
                "municipalities": [
                    {"ibgeCode": code, "name": municipality_names[code]}
                    for code in region_codes
                ],
            },
            "generation": {
                "deterministic": True,
                "clockUsed": False,
                "networkUsed": False,
                "databaseUsed": True,
                "databaseReadOnly": True,
                "databaseWrites": False,
                "supabaseUsed": False,
                "publicDataChanged": False,
                "fullBuildUsed": False,
                "outputFormat": "csv_gzip_deterministic",
                "parquetEngineAvailable": False,
            },
            "baseline": contract["baseline"],
            "sources": {
                "contract": {
                    "path": CONTRACT_PATH.relative_to(REPO_ROOT).as_posix(),
                    "sha256": sha256_file(CONTRACT_PATH),
                },
                "script": {
                    "path": Path(__file__).resolve().relative_to(REPO_ROOT).as_posix(),
                    "sha256": sha256_file(Path(__file__).resolve()),
                },
                "core": {
                    "path": "data_pipeline/src/vocacoes_pne_job2.py",
                    "sha256": sha256_file(DATA_PIPELINE_DIR / "src" / "vocacoes_pne_job2.py"),
                },
                "regionRegistry": {
                    "path": REGION_CONFIG_PATH.relative_to(REPO_ROOT).as_posix(),
                    "sha256": sha256_file(REGION_CONFIG_PATH),
                },
                "municipalityRegistry": {
                    "path": MUNICIPALITY_REGISTRY_PATH.relative_to(REPO_ROOT).as_posix(),
                    "sha256": sha256_file(MUNICIPALITY_REGISTRY_PATH),
                },
                "r6Research": {
                    "path": R6_RESEARCH_PATH.relative_to(REPO_ROOT).as_posix(),
                    "sha256": sha256_file(R6_RESEARCH_PATH),
                },
                "postgresql": contract["sources"][:2],
                "localMetadata": metadata,
            },
            "forbiddenSources": contract["forbiddenSources"],
            "subjobs": states,
            "artifacts": artifacts,
            "summary": {
                "subjobCount": len(states),
                "readyCount": sum(state["status"] == "READY" for state in states),
                "blockedCount": sum(
                    state["status"] == "BLOCKED_WITH_EVIDENCE" for state in states
                ),
                "artifactCount": len(artifacts),
                "artifactRowCount": sum(
                    artifact["rowCount"] or 0 for artifact in artifacts
                ),
            },
        }
        write_json(staging / "execution_state.json", {"jobId": JOB_ID, "subjobs": states})
        write_json(staging / "manifest.json", manifest)
        promotion = replace_directory_transactionally(staging, output_directory)
        manifest_path = output_directory / "manifest.json"
        return {
            "artifactCount": len(artifacts),
            "manifestPath": str(manifest_path),
            "manifestSha256": sha256_file(manifest_path),
            "outputDirectory": str(output_directory),
            "promotion": promotion,
            "readyCount": manifest["summary"]["readyCount"],
            "rowCount": manifest["summary"]["artifactRowCount"],
        }
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Diretório analítico explícito fora de public/data.",
    )
    args = parser.parse_args()
    report = materialize(args.output_dir.resolve())
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
