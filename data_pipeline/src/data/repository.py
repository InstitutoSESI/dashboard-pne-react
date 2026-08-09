import os
import re
import time
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from ..pipeline_profiling import (
    profile_query,
    profiled_cache_call,
    profiled_query_call,
    record_tabular_result,
)
from ..state_config import resolve_pipeline_state_code

if TYPE_CHECKING:
    from supabase import Client

BASE_DIR = Path(__file__).resolve().parent.parent.parent
QUERIES_DIR = BASE_DIR / "queries"
ENV_FILES = (BASE_DIR / ".env", QUERIES_DIR / ".env")
DEFAULT_CACHE_TTL_SECONDS = 900
DEFAULT_DATA_BACKEND = "postgres_local"
_UF_QUERY_PARAM_PATTERN = re.compile(r":uf\b")


@dataclass(frozen=True)
class JoinSpec:
    table_name: str
    merge_keys: tuple[str, ...]
    how: str = "left"


@dataclass(frozen=True)
class DatasetSpec:
    name: str
    base_table: str
    joins: tuple[JoinSpec, ...] = ()
    local_query_file: str | None = None


DATASET_SPECS: dict[str, DatasetSpec] = {
    "pne_data": DatasetSpec(
        name="pne_data",
        base_table="pne_matriculas_creche",
        joins=(JoinSpec("pne_pop_0_3", ("ano", "municipio")),),
        local_query_file="matriculas_creche.sql",
    ),
    "pre_escola_data": DatasetSpec(
        name="pre_escola_data",
        base_table="pne_matriculas_pre_escola",
        joins=(JoinSpec("pne_pop_4_5", ("ano", "municipio")),),
        local_query_file="matriculas_pre_escola.sql",
    ),
    "basico_6_17_data": DatasetSpec(
        name="basico_6_17_data",
        base_table="pne_matriculas_basico_6_17",
        joins=(JoinSpec("pne_pop_6_17", ("ano", "municipio")),),
        local_query_file="matriculas_basico_6_17.sql",
    ),
    "basico_15_17_data": DatasetSpec(
        name="basico_15_17_data",
        base_table="pne_matriculas_basico_15_17",
        joins=(JoinSpec("pne_pop_15_17", ("ano", "municipio")),),
        local_query_file="matriculas_basico_15_17.sql",
    ),
    "basico_0_5_data": DatasetSpec(
        name="basico_0_5_data",
        base_table="pne_matriculas_basico_0_5",
        joins=(JoinSpec("pne_pop_0_5", ("ano", "municipio")),),
        local_query_file="matriculas_basico_0_5.sql",
    ),
    "basico_4_17_data": DatasetSpec(
        name="basico_4_17_data",
        base_table="pne_matriculas_basico_4_17",
        joins=(JoinSpec("pne_pop_4_17", ("ano", "municipio")),),
        local_query_file="matriculas_basico_4_17.sql",
    ),
    "basico_6_14_data": DatasetSpec(
        name="basico_6_14_data",
        base_table="pne_matriculas_basico_6_14",
        joins=(JoinSpec("pne_pop_6_14", ("ano", "municipio")),),
        local_query_file="matriculas_basico_6_14.sql",
    ),
    "basico_integral_data": DatasetSpec(
        name="basico_integral_data",
        base_table="pne_matriculas_basico_integral",
        local_query_file="matriculas_basico_integral.sql",
    ),
    "escolas_integral_data": DatasetSpec(
        name="escolas_integral_data",
        base_table="pne_escolas_publicas_integral",
        local_query_file="escolas_integral.sql",
    ),
    "escolas_integral_por_dependencia_data": DatasetSpec(
        name="escolas_integral_por_dependencia_data",
        base_table="pne_escolas_publicas_integral_por_dependencia",
        local_query_file="escolas_integral_por_dependencia.sql",
    ),
    "creche_por_dependencia_data": DatasetSpec(
        name="creche_por_dependencia_data",
        base_table="pne_matriculas_creche_por_dependencia",
        local_query_file="matriculas_creche_por_dependencia.sql",
    ),
    "pre_escola_por_dependencia_data": DatasetSpec(
        name="pre_escola_por_dependencia_data",
        base_table="pne_matriculas_pre_escola_por_dependencia",
        local_query_file="matriculas_pre_escola_por_dependencia.sql",
    ),
    "basico_6_17_por_dependencia_data": DatasetSpec(
        name="basico_6_17_por_dependencia_data",
        base_table="pne_matriculas_basico_6_17_por_dependencia",
        local_query_file="matriculas_basico_6_17_por_dependencia.sql",
    ),
    "basico_15_17_por_dependencia_data": DatasetSpec(
        name="basico_15_17_por_dependencia_data",
        base_table="pne_matriculas_basico_15_17_por_dependencia",
        local_query_file="matriculas_basico_15_17_por_dependencia.sql",
    ),
    "basico_integral_por_dependencia_data": DatasetSpec(
        name="basico_integral_por_dependencia_data",
        base_table="pne_matriculas_basico_integral_por_dependencia",
        local_query_file="matriculas_basico_integral_por_dependencia.sql",
    ),
    "medio_tecnico_data": DatasetSpec(
        name="medio_tecnico_data",
        base_table="pne_matriculas_medio_tecnico",
        local_query_file="matriculas_medio_tecnico.sql",
    ),
    "medio_tecnico_articulado_data": DatasetSpec(
        name="medio_tecnico_articulado_data",
        base_table="pne_matriculas_medio_tecnico_articulado",
        local_query_file="matriculas_medio_tecnico_articulado.sql",
    ),
    "ept_nivel_medio_data": DatasetSpec(
        name="ept_nivel_medio_data",
        base_table="ept_nivel_medio",
        local_query_file="ept_nivel_medio.sql",
    ),
    "eja_integrada_educacao_profissional_data": DatasetSpec(
        name="eja_integrada_educacao_profissional_data",
        base_table="eja_integrada_educacao_profissional",
        local_query_file="eja_integrada_educacao_profissional.sql",
    ),
    "censo_populacao_alfabetizacao_data": DatasetSpec(
        name="censo_populacao_alfabetizacao_data",
        base_table="censo_populacao_alfabetizacao",
        local_query_file="censo_populacao_alfabetizacao.sql",
    ),
    "censo_populacao_escolaridade_media_18_29_data": DatasetSpec(
        name="censo_populacao_escolaridade_media_18_29_data",
        base_table="censo_populacao_escolaridade_media_18_29",
        local_query_file="censo_populacao_escolaridade_media_18_29.sql",
    ),
    "censo_populacao_escolaridade_media_18_29_racial_data": DatasetSpec(
        name="censo_populacao_escolaridade_media_18_29_racial_data",
        base_table="censo_populacao_escolaridade_media_18_29_racial",
        local_query_file="censo_populacao_escolaridade_media_18_29_racial.sql",
    ),
    "censo_populacao_ensino_medio_15_17_data": DatasetSpec(
        name="censo_populacao_ensino_medio_15_17_data",
        base_table="censo_populacao_ensino_medio_15_17",
        local_query_file="censo_populacao_ensino_medio_15_17.sql",
    ),
    "censo_populacao_ensino_fundamental_6_14_data": DatasetSpec(
        name="censo_populacao_ensino_fundamental_6_14_data",
        base_table="censo_populacao_ensino_fundamental_6_14",
        local_query_file="censo_populacao_ensino_fundamental_6_14.sql",
    ),
    "censo_populacao_ensino_fundamental_concluido_18_mais_data": DatasetSpec(
        name="censo_populacao_ensino_fundamental_concluido_18_mais_data",
        base_table="censo_populacao_ensino_fundamental_concluido_18_mais",
        local_query_file="censo_populacao_ensino_fundamental_concluido_18_mais.sql",
    ),
    "censo_populacao_ensino_fundamental_concluido_18_29_data": DatasetSpec(
        name="censo_populacao_ensino_fundamental_concluido_18_29_data",
        base_table="censo_populacao_ensino_fundamental_concluido_18_29",
        local_query_file="censo_populacao_ensino_fundamental_concluido_18_29.sql",
    ),
    "censo_populacao_ensino_fundamental_concluido_15_29_data": DatasetSpec(
        name="censo_populacao_ensino_fundamental_concluido_15_29_data",
        base_table="censo_populacao_ensino_fundamental_concluido_15_29",
        local_query_file="censo_populacao_ensino_fundamental_concluido_15_29.sql",
    ),
    "censo_populacao_ensino_fundamental_concluido_15_mais_data": DatasetSpec(
        name="censo_populacao_ensino_fundamental_concluido_15_mais_data",
        base_table="censo_populacao_ensino_fundamental_concluido_15_mais",
        local_query_file="censo_populacao_ensino_fundamental_concluido_15_mais.sql",
    ),
    "censo_populacao_ensino_medio_concluido_18_mais_data": DatasetSpec(
        name="censo_populacao_ensino_medio_concluido_18_mais_data",
        base_table="censo_populacao_ensino_medio_concluido_18_mais",
        local_query_file="censo_populacao_ensino_medio_concluido_18_mais.sql",
    ),
    "censo_populacao_ensino_medio_concluido_18_29_data": DatasetSpec(
        name="censo_populacao_ensino_medio_concluido_18_29_data",
        base_table="censo_populacao_ensino_medio_concluido_18_29",
        local_query_file="censo_populacao_ensino_medio_concluido_18_29.sql",
    ),
    "taxa_alfabetizacao_data": DatasetSpec(
        name="taxa_alfabetizacao_data",
        base_table="pne_taxa_alfabetizacao",
        local_query_file="taxa_alfabetizacao.sql",
    ),
    "saeb_proficiencia_data": DatasetSpec(
        name="saeb_proficiencia_data",
        base_table="saeb_proficiencia",
        local_query_file="saeb_proficiencia_niveis.sql",
    ),
    "saeb_ideb_data": DatasetSpec(
        name="saeb_ideb_data",
        base_table="saeb_ideb",
        local_query_file="saeb_ideb.sql",
    ),
    "distorcao_idade_serie_data": DatasetSpec(
        name="distorcao_idade_serie_data",
        base_table="distorcao_idade_serie",
        local_query_file="distorcao_idade_serie.sql",
    ),
    "adequacao_docente_data": DatasetSpec(
        name="adequacao_docente_data",
        base_table="adequacao_docente",
        local_query_file="adequacao_docente.sql",
    ),
    "docentes_pos_graduacao_data": DatasetSpec(
        name="docentes_pos_graduacao_data",
        base_table="docentes_pos_graduacao",
        local_query_file="docentes_pos_graduacao.sql",
    ),
    "docentes_temporarios_data": DatasetSpec(
        name="docentes_temporarios_data",
        base_table="docentes_temporarios",
        local_query_file="docentes_temporarios.sql",
    ),
    "rendimento_professores_data": DatasetSpec(
        name="rendimento_professores_data",
        base_table="rendimento_professores_razao_percentual",
        local_query_file="rendimento_professores.sql",
    ),
    "atendimento_educacional_especializado_data": DatasetSpec(
        name="atendimento_educacional_especializado_data",
        base_table="atendimento_educacional_especializado",
        local_query_file="atendimento_educacional_especializado.sql",
    ),
    "infraestrutura_escolar_data": DatasetSpec(
        name="infraestrutura_escolar_data",
        base_table="infraestrutura_escolar",
        local_query_file="infraestrutura_escolar.sql",
    ),
    "school_infrastructure_source_data": DatasetSpec(
        name="school_infrastructure_source_data",
        base_table="vw_educacao_infraestrutura_escolar_ativa",
        local_query_file="school_infrastructure_source.sql",
    ),
    "special_education_school_source_data": DatasetSpec(
        name="special_education_school_source_data",
        base_table="censo_educacao_especial_escolas",
        local_query_file="special_education_school_source.sql",
    ),
    "escolas_integral_referencia_data": DatasetSpec(
        name="escolas_integral_referencia_data",
        base_table="censo_escolas",
        local_query_file="infraestrutura_escolar_referencia.sql",
    ),
    "saeb_matematica_data": DatasetSpec(
        name="saeb_matematica_data",
        base_table="saeb_proficiencia",
        local_query_file="saeb_matematica.sql",
    ),
    "pne_2014_2024_metricas_data": DatasetSpec(
        name="pne_2014_2024_metricas_data",
        base_table="pne_2014_2024_metricas",
        local_query_file="pne_2014_2024_metricas.sql",
    ),
    "pne_2026_2036_metricas_data": DatasetSpec(
        name="pne_2026_2036_metricas_data",
        base_table="pne_2026_2036_metricas",
        local_query_file="pne_2026_2036_metricas.sql",
    ),
    "infraestrutura_escolar_por_dependencia_data": DatasetSpec(
        name="infraestrutura_escolar_por_dependencia_data",
        base_table="pne_infraestrutura_escolar_por_dependencia",
        local_query_file="infraestrutura_escolar_por_dependencia.sql",
    ),
}

LOCAL_QUERY_FILES_BY_TABLE: dict[str, str] = {
    "pne_matriculas_creche": "matriculas_creche.sql",
    "pne_matriculas_creche_por_dependencia": "matriculas_creche_por_dependencia.sql",
    "pne_matriculas_pre_escola_por_dependencia": "matriculas_pre_escola_por_dependencia.sql",
    "pne_matriculas_basico_6_17_por_dependencia": "matriculas_basico_6_17_por_dependencia.sql",
    "pne_matriculas_basico_15_17_por_dependencia": "matriculas_basico_15_17_por_dependencia.sql",
    "pne_matriculas_basico_integral_por_dependencia": "matriculas_basico_integral_por_dependencia.sql",
    "pne_pop_0_3": "pop_0_3.sql",
    "pne_matriculas_pre_escola": "matriculas_pre_escola.sql",
    "pne_pop_4_5": "pop_4_5.sql",
    "pne_pop_6_17": "pop_6_17.sql",
    "pne_matriculas_basico_6_17": "matriculas_basico_6_17.sql",
    "pne_pop_15_17": "pop_15_17.sql",
    "pne_matriculas_basico_15_17": "matriculas_basico_15_17.sql",
    "pne_matriculas_basico_0_5": "matriculas_basico_0_5.sql",
    "pne_pop_0_5": "pop_0_5.sql",
    "pne_matriculas_basico_4_17": "matriculas_basico_4_17.sql",
    "pne_pop_4_17": "pop_4_17.sql",
    "pne_matriculas_basico_6_14": "matriculas_basico_6_14.sql",
    "pne_pop_6_14": "pop_6_14.sql",
    "pne_matriculas_basico_integral": "matriculas_basico_integral.sql",
    "pne_escolas_publicas_integral": "escolas_integral.sql",
    "pne_escolas_publicas_integral_por_dependencia": "escolas_integral_por_dependencia.sql",
    "pne_matriculas_medio_tecnico": "matriculas_medio_tecnico.sql",
    "pne_matriculas_medio_tecnico_articulado": "matriculas_medio_tecnico_articulado.sql",
    "ept_nivel_medio": "ept_nivel_medio.sql",
    "eja_integrada_educacao_profissional": "eja_integrada_educacao_profissional.sql",
    "censo_populacao_alfabetizacao": "censo_populacao_alfabetizacao.sql",
    "censo_populacao_escolaridade_media_18_29": "censo_populacao_escolaridade_media_18_29.sql",
    "censo_populacao_escolaridade_media_18_29_racial": "censo_populacao_escolaridade_media_18_29_racial.sql",
    "censo_populacao_ensino_medio_15_17": "censo_populacao_ensino_medio_15_17.sql",
    "censo_populacao_ensino_fundamental_6_14": "censo_populacao_ensino_fundamental_6_14.sql",
    "censo_populacao_ensino_fundamental_concluido_18_mais": "censo_populacao_ensino_fundamental_concluido_18_mais.sql",
    "censo_populacao_ensino_fundamental_concluido_18_29": "censo_populacao_ensino_fundamental_concluido_18_29.sql",
    "censo_populacao_ensino_fundamental_concluido_15_29": "censo_populacao_ensino_fundamental_concluido_15_29.sql",
    "censo_populacao_ensino_fundamental_concluido_15_mais": "censo_populacao_ensino_fundamental_concluido_15_mais.sql",
    "censo_populacao_ensino_medio_concluido_18_mais": "censo_populacao_ensino_medio_concluido_18_mais.sql",
    "censo_populacao_ensino_medio_concluido_18_29": "censo_populacao_ensino_medio_concluido_18_29.sql",
    "pne_taxa_alfabetizacao": "taxa_alfabetizacao.sql",
    "saeb_proficiencia": "saeb_proficiencia_niveis.sql",
    "saeb_ideb": "saeb_ideb.sql",
    "distorcao_idade_serie": "distorcao_idade_serie.sql",
    "adequacao_docente": "adequacao_docente.sql",
    "docentes_pos_graduacao": "docentes_pos_graduacao.sql",
    "docentes_temporarios": "docentes_temporarios.sql",
    "rendimento_professores_razao_percentual": "rendimento_professores.sql",
    "atendimento_educacional_especializado": "atendimento_educacional_especializado.sql",
    "infraestrutura_escolar": "infraestrutura_escolar.sql",
    "vw_educacao_infraestrutura_escolar_ativa": "school_infrastructure_source.sql",
    "censo_educacao_especial_escolas": "special_education_school_source.sql",
    "censo_escolas": "infraestrutura_escolar_referencia.sql",
    "pne_infraestrutura_escolar_por_dependencia": "infraestrutura_escolar_por_dependencia.sql",
    "pne_2014_2024_metricas": "pne_2014_2024_metricas.sql",
    "pne_2026_2036_metricas": "pne_2026_2036_metricas.sql",
    "matriculas_privadas_conveniadas_poder_publico": "matriculas_privadas_conveniadas.sql",
    "siope_fundeb_municipio_dashboard": "fundeb.sql",
    "fnde_pnate_municipio_dashboard": "pnate.sql",
}


def load_environment() -> None:
    for env_file in ENV_FILES:
        if env_file.exists():
            load_dotenv(env_file, override=False)


def require_env(name: str) -> str:
    load_environment()
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Variável de ambiente obrigatória ausente: {name}")
    return value


def get_data_cache_ttl_seconds() -> int:
    load_environment()
    raw_value = os.getenv("DATA_CACHE_TTL_SECONDS", str(DEFAULT_CACHE_TTL_SECONDS))
    try:
        return max(int(raw_value), 0)
    except ValueError:
        return DEFAULT_CACHE_TTL_SECONDS


def get_data_backend() -> str:
    load_environment()
    backend = os.getenv("DATA_BACKEND", DEFAULT_DATA_BACKEND).strip().lower()
    if backend in {"postgres", "postgres_local", "local_postgres"}:
        return "postgres_local"
    if backend == "supabase":
        return "supabase"
    return DEFAULT_DATA_BACKEND


def _current_cache_bucket() -> int:
    ttl_seconds = get_data_cache_ttl_seconds()
    if ttl_seconds <= 0:
        return -1
    return int(time.time() // ttl_seconds)


@lru_cache(maxsize=1)
def get_supabase_client() -> "Client":
    from supabase import create_client

    url = require_env("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY") or require_env("SUPABASE_KEY")
    return create_client(url, key)


@lru_cache(maxsize=1)
def get_local_postgres_engine() -> Engine:
    db_user = require_env("DB_USUARIO")
    db_password = require_env("DB_SENHA")
    db_host = require_env("DB_HOST")
    db_name = require_env("DB_BANCO")
    db_port = os.getenv("DB_PORT", "5432")

    return create_engine(
        f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    )


def _fetch_supabase_table_uncached(client: "Client", table_name: str) -> pd.DataFrame:
    with profile_query(
        f"repository.supabase.{table_name}",
        metadata={
            "datasetId": table_name,
            "backend": "supabase",
            "broadQuery": True,
            "municipalityFilter": "local_after_query",
        },
    ) as operation:
        all_data = []
        limit = 1000
        offset = 0
        pages = 0

        while True:
            response = (
                client.table(table_name)
                .select("*")
                .range(offset, offset + limit - 1)
                .execute()
            )
            pages += 1
            data = getattr(response, "data", [])
            if not data:
                break
            all_data.extend(data)
            if len(data) < limit:
                break
            offset += limit

        frame = pd.DataFrame(all_data)
        operation.add_counter("pages", pages)
        record_tabular_result(operation, frame)
        return frame


@lru_cache(maxsize=32)
def _fetch_table_cached(table_name: str, cache_bucket: int) -> pd.DataFrame:
    return _fetch_supabase_table_uncached(get_supabase_client(), table_name)


def _get_table_frame(table_name: str) -> pd.DataFrame:
    ttl_seconds = get_data_cache_ttl_seconds()
    if ttl_seconds <= 0:
        return _fetch_supabase_table_uncached(get_supabase_client(), table_name)
    return profiled_cache_call(
        "repository.raw_table_cache",
        lambda: _fetch_table_cached(table_name, _current_cache_bucket()),
        _fetch_table_cached.cache_info,
        metadata={"datasetId": table_name, "backend": "supabase"},
    )


def _build_supabase_dataset(spec: DatasetSpec) -> pd.DataFrame:
    base_frame = _get_table_frame(spec.base_table).copy()
    if base_frame.empty:
        return pd.DataFrame()

    merged_frame = base_frame
    for join_spec in spec.joins:
        join_frame = _get_table_frame(join_spec.table_name).copy()
        if join_frame.empty:
            return pd.DataFrame()
        merged_frame = pd.merge(
            merged_frame,
            join_frame,
            on=list(join_spec.merge_keys),
            how=join_spec.how,
        )

    return merged_frame


def _read_local_query_table(table_name: str) -> pd.DataFrame:
    query_file = LOCAL_QUERY_FILES_BY_TABLE.get(table_name)
    if not query_file:
        raise RuntimeError(
            f"Tabela sem query local configurada para o backend Postgres: {table_name}"
        )

    query_path = QUERIES_DIR / query_file
    if not query_path.exists():
        raise FileNotFoundError(f"Query local não encontrada: {query_path}")

    query = query_path.read_text(encoding="utf-8")
    params = (
        {"uf": resolve_pipeline_state_code()}
        if _UF_QUERY_PARAM_PATTERN.search(query)
        else None
    )
    try:
        return profiled_query_call(
            f"repository.postgres.{table_name}",
            lambda: pd.read_sql_query(
                text(query), get_local_postgres_engine(), params=params
            ),
            metadata={
                "datasetId": table_name,
                "backend": "postgres_local",
                "broadQuery": True,
                "municipalityFilter": "local_after_query",
                "parametersBound": bool(params),
            },
        )
    except Exception as exc:
        message = str(exc)
        if (
            "UndefinedTable" in message
            or 'relation "' in message
            and '" does not exist' in message
        ):
            return pd.DataFrame()
        raise


def _read_local_sql(
    query: str,
    params: dict | None = None,
    *,
    query_id: str = "repository.local_sql",
) -> pd.DataFrame:
    try:
        return profiled_query_call(
            query_id,
            lambda: pd.read_sql_query(
                text(query), get_local_postgres_engine(), params=params
            ),
            metadata={
                "datasetId": query_id,
                "backend": "postgres_local",
                "parametersBound": bool(params),
            },
        )
    except Exception as exc:
        message = str(exc)
        if (
            "UndefinedTable" in message
            or 'relation "' in message
            and '" does not exist' in message
        ):
            return pd.DataFrame()
        raise


def _fetch_supabase_columns_uncached(table_name: str, columns: str) -> pd.DataFrame:
    with profile_query(
        f"repository.supabase.{table_name}.columns",
        metadata={
            "datasetId": table_name,
            "backend": "supabase",
            "columnSelection": "explicit",
        },
    ) as operation:
        all_data = []
        limit = 1000
        offset = 0
        pages = 0
        client = get_supabase_client()

        while True:
            response = (
                client.table(table_name)
                .select(columns)
                .range(offset, offset + limit - 1)
                .execute()
            )
            pages += 1
            data = getattr(response, "data", [])
            if not data:
                break
            all_data.extend(data)
            if len(data) < limit:
                break
            offset += limit

        frame = pd.DataFrame(all_data)
        operation.add_counter("pages", pages)
        record_tabular_result(operation, frame)
        return frame


def _build_local_dataset(spec: DatasetSpec) -> pd.DataFrame:
    base_frame = _read_local_query_table(spec.base_table).copy()
    if base_frame.empty:
        return pd.DataFrame()

    merged_frame = base_frame
    for join_spec in spec.joins:
        join_frame = _read_local_query_table(join_spec.table_name).copy()
        if join_frame.empty:
            return pd.DataFrame()
        merged_frame = pd.merge(
            merged_frame,
            join_frame,
            on=list(join_spec.merge_keys),
            how=join_spec.how,
        )

    return merged_frame


def _build_overview_metric(
    dataset_frame: pd.DataFrame,
    *,
    num_col: str,
    den_col: str,
    agg_dict: dict[str, str],
    taxa_col: str,
    ano_col: str,
) -> pd.DataFrame:
    if dataset_frame.empty or "municipio" not in dataset_frame.columns:
        return pd.DataFrame(columns=["municipio", taxa_col, ano_col])

    grouped_frame = dataset_frame.copy()
    for column in agg_dict:
        if column not in grouped_frame.columns:
            grouped_frame[column] = 0

    grouped_frame = grouped_frame.groupby(["municipio", "ano"], as_index=False).agg(
        agg_dict
    )
    if grouped_frame.empty:
        return pd.DataFrame(columns=["municipio", taxa_col, ano_col])

    latest_rows = (
        grouped_frame.sort_values(["municipio", "ano"])
        .groupby("municipio", as_index=False)
        .tail(1)
        .copy()
    )

    numerador = latest_rows[num_col].fillna(0)
    denominador = latest_rows[den_col].fillna(0)
    latest_rows[taxa_col] = numerador.div(denominador.where(denominador != 0, pd.NA))
    latest_rows[taxa_col] = latest_rows[taxa_col].fillna(0).mul(100)
    latest_rows[ano_col] = latest_rows["ano"].fillna("-")

    return latest_rows[["municipio", taxa_col, ano_col]]


@lru_cache(maxsize=len(DATASET_SPECS))
def _load_supabase_dataset_cached(dataset_name: str, cache_bucket: int) -> pd.DataFrame:
    spec = DATASET_SPECS[dataset_name]
    return _build_supabase_dataset(spec)


@lru_cache(maxsize=len(DATASET_SPECS))
def _load_local_dataset_cached(dataset_name: str, cache_bucket: int) -> pd.DataFrame:
    spec = DATASET_SPECS[dataset_name]
    return _build_local_dataset(spec)


def _load_dataset_frame(dataset_name: str, cache_bucket: int | None) -> pd.DataFrame:
    spec = DATASET_SPECS[dataset_name]
    backend = get_data_backend()

    if backend == "supabase":
        if cache_bucket is None:
            return _build_supabase_dataset(spec)
        return profiled_cache_call(
            "repository.dataset_cache",
            lambda: _load_supabase_dataset_cached(dataset_name, cache_bucket),
            _load_supabase_dataset_cached.cache_info,
            metadata={"datasetId": dataset_name, "backend": backend},
        )

    if cache_bucket is None:
        return _build_local_dataset(spec)
    return profiled_cache_call(
        "repository.dataset_cache",
        lambda: _load_local_dataset_cached(dataset_name, cache_bucket),
        _load_local_dataset_cached.cache_info,
        metadata={"datasetId": dataset_name, "backend": backend},
    )


def _build_atendimento_overview_frames(cache_bucket: int | None) -> list[pd.DataFrame]:
    dataset_loader = lambda name: _load_dataset_frame(name, cache_bucket)

    return [
        _build_overview_metric(
            dataset_loader("pne_data"),
            num_col="mat_infantil_creche",
            den_col="pop_0_3",
            agg_dict={"mat_infantil_creche": "sum", "pop_0_3": "max"},
            taxa_col="taxa_creche",
            ano_col="ano_creche",
        ),
        _build_overview_metric(
            dataset_loader("pre_escola_data"),
            num_col="mat_infantil_pre",
            den_col="pop_4_5",
            agg_dict={"mat_infantil_pre": "sum", "pop_4_5": "max"},
            taxa_col="taxa_pre",
            ano_col="ano_pre",
        ),
        _build_overview_metric(
            dataset_loader("basico_6_17_data"),
            num_col="mat_basico_6_17",
            den_col="pop_6_17",
            agg_dict={"mat_basico_6_17": "sum", "pop_6_17": "max"},
            taxa_col="taxa_basico_6_17",
            ano_col="ano_basico_6_17",
        ),
        _build_overview_metric(
            dataset_loader("basico_15_17_data"),
            num_col="mat_basico_15_17",
            den_col="pop_15_17",
            agg_dict={"mat_basico_15_17": "sum", "pop_15_17": "max"},
            taxa_col="taxa_basico_15_17",
            ano_col="ano_basico_15_17",
        ),
        _build_overview_metric(
            dataset_loader("basico_integral_data"),
            num_col="mat_basico_integral",
            den_col="mat_basico",
            agg_dict={"mat_basico_integral": "sum", "mat_basico": "sum"},
            taxa_col="taxa_basico_integral",
            ano_col="ano_basico_integral",
        ),
        _build_overview_metric(
            dataset_loader("escolas_integral_data"),
            num_col="escolas_publicas_com_integral",
            den_col="escolas_publicas_total",
            agg_dict={
                "escolas_publicas_com_integral": "sum",
                "escolas_publicas_total": "sum",
            },
            taxa_col="taxa_escolas_integral",
            ano_col="ano_escolas_integral",
        ),
        _build_overview_metric(
            dataset_loader("medio_tecnico_data"),
            num_col="mat_profissional_tecnico",
            den_col="mat_medio",
            agg_dict={"mat_profissional_tecnico": "sum", "mat_medio": "sum"},
            taxa_col="taxa_medio_tecnico",
            ano_col="ano_medio_tecnico",
        ),
        _build_overview_metric(
            dataset_loader("atendimento_educacional_especializado_data"),
            num_col="quantidade_aee",
            den_col="total_turmas_educacao_especial",
            agg_dict={
                "quantidade_aee": "sum",
                "total_turmas_educacao_especial": "sum",
            },
            taxa_col="taxa_aee",
            ano_col="ano_aee",
        ),
    ]


def _merge_atendimento_overview_frames(
    metric_frames: list[pd.DataFrame],
) -> pd.DataFrame:
    overview_frame = pd.DataFrame(columns=["municipio"])

    for metric_frame in metric_frames:
        if metric_frame.empty:
            continue
        if overview_frame.empty:
            overview_frame = metric_frame.copy()
            continue
        overview_frame = overview_frame.merge(metric_frame, on="municipio", how="outer")

    return overview_frame.fillna("-")


@lru_cache(maxsize=4)
def _load_atendimento_overview_cached(cache_bucket: int) -> pd.DataFrame:
    return _merge_atendimento_overview_frames(
        _build_atendimento_overview_frames(cache_bucket)
    )


def fetch_table(table_name: str) -> pd.DataFrame:
    return _get_table_frame(table_name).copy()


def fetch_raw_table(table_name: str) -> pd.DataFrame:
    backend = get_data_backend()
    if backend == "supabase":
        return _get_table_frame(table_name).copy()
    return _read_local_query_table(table_name).copy()


def load_dataset(dataset_name: str) -> pd.DataFrame:
    if dataset_name not in DATASET_SPECS:
        raise KeyError(f"Dataset não registrado: {dataset_name}")

    ttl_seconds = get_data_cache_ttl_seconds()
    if ttl_seconds <= 0:
        return _load_dataset_frame(dataset_name, None)

    return _load_dataset_frame(dataset_name, _current_cache_bucket())


@lru_cache(maxsize=8)
def _load_municipios_cached(
    cache_bucket: int,
    state_code: str,
) -> tuple[str, ...]:
    backend = get_data_backend()

    if backend == "supabase":
        df = _fetch_supabase_columns_uncached("pne_matriculas_creche", "municipio")
    else:
        df = _read_local_sql(
            """
            SELECT DISTINCT m.municipio
            FROM censo c
            JOIN municipios m
              ON c.id_municipio::text = m.id_municipio::text
            WHERE m.municipio IS NOT NULL
              AND c.sigla_uf = :uf
              AND m.sigla_uf = :uf
            ORDER BY m.municipio
            """,
            params={"uf": state_code},
            query_id="repository.postgres.municipalities",
        )

    if df.empty or "municipio" not in df.columns:
        return ()

    municipios = df["municipio"].dropna().astype(str).drop_duplicates().tolist()
    municipios.sort()
    return tuple(municipios)


def load_municipios() -> list[str]:
    state_code = resolve_pipeline_state_code()
    ttl_seconds = get_data_cache_ttl_seconds()
    if ttl_seconds <= 0:
        return list(_load_municipios_cached.__wrapped__(-1, state_code))
    bucket = _current_cache_bucket()
    return list(
        profiled_cache_call(
            "repository.municipalities_cache",
            lambda: _load_municipios_cached(bucket, state_code),
            _load_municipios_cached.cache_info,
            metadata={"datasetId": "municipalities", "stateCode": state_code},
        )
    )


def load_atendimento_overview_data() -> pd.DataFrame:
    ttl_seconds = get_data_cache_ttl_seconds()
    if ttl_seconds <= 0:
        return _merge_atendimento_overview_frames(
            _build_atendimento_overview_frames(None)
        ).copy()
    bucket = _current_cache_bucket()
    return profiled_cache_call(
        "repository.overview_cache",
        lambda: _load_atendimento_overview_cached(bucket),
        _load_atendimento_overview_cached.cache_info,
        metadata={"datasetId": "education_attendance_overview"},
    ).copy()


def clear_data_cache() -> None:
    get_supabase_client.cache_clear()
    get_local_postgres_engine.cache_clear()
    _fetch_table_cached.cache_clear()
    _load_supabase_dataset_cached.cache_clear()
    _load_local_dataset_cached.cache_clear()
    _load_atendimento_overview_cached.cache_clear()
    _load_municipios_cached.cache_clear()
