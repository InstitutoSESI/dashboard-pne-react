"""Materializa o Job 5G-B V7 em staging, sem frontend ou publicação."""

from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
from typing import Any, Iterator, Mapping, Sequence

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, URL


REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_PIPELINE_DIR = REPO_ROOT / "data_pipeline"
if str(DATA_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_PIPELINE_DIR))

from src.special_education_materialization import (  # noqa: E402
    _aee as special_aee,
    _special as special_metrics,
    field_availability as special_field_availability,
)
from src.vocacoes_pne_job2 import (  # noqa: E402
    assert_outside_public_data,
    directory_content_digest,
    sha256_file,
    staging_directory_for,
    validate_unique_key,
    write_csv_gzip,
    write_json,
)


JOB_ID = "v7-job5gb"
SCHEMA_VERSION = "vocacoes-pne-v7-job5gb-v1"
FINAL_STATE = "JOB_5GB_PARTIAL_WITH_DATA_GAPS"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / ".tmp" / "vocacoes-pne" / JOB_ID
REGION_CONFIG_PATH = REPO_ROOT / "config" / "regions" / "rs.json"
MUNICIPALITY_REGISTRY_PATH = REPO_ROOT / "config" / "municipalities" / "rs.json"
PNE_CONTRACT_PATH = REPO_ROOT / "contracts" / "pne2026-goal-indicator-contract.json"
PNE_POLICY_PATH = REPO_ROOT / "contracts" / "pne2026-diagnostic-presentation-policy.json"
JOB2_ROOT = REPO_ROOT / ".tmp" / "vocacoes-pne" / "v7-job2" / "2c"
JOB5F_ROOT = REPO_ROOT / ".tmp" / "vocacoes-pne" / "v7-job5f"
JOB5GA_ROOT = REPO_ROOT / ".tmp" / "vocacoes-pne" / "v7-job5ga"
JOB5GAR_ROOT = REPO_ROOT / ".tmp" / "vocacoes-pne" / "v7-job5gar"
CADUNICO_ROOT = (
    REPO_ROOT
    / ".tmp"
    / "vocacoes-regiao"
    / "rodada-02"
    / "reexec-ciclo3-root"
    / "aquisicao"
    / "bruto"
    / "cadunico_sagi"
)
NOVA_SANTA_RITA_ID = "4313375"
YEARS = tuple(range(2014, 2026))

OUTPUT_FILES = (
    "DICIONARIO_ESCOLARIDADE_ADULTA_2010_2022_V1.json",
    "PAINEL_ESCOLARIDADE_ADULTA_2010_2022_V1.csv.gz",
    "PAINEL_EJA_DISTRIBUICAO_2022_V1.csv.gz",
    "PAINEL_EJA_HISTORICA_2014_2025_V1.csv.gz",
    "PAINEL_EJA_INTEGRADA_EPT_V1.csv.gz",
    "PAINEL_VULNERABILIDADE_EDUCACIONAL_V1.csv.gz",
    "PAINEL_EDUCACAO_ESPECIAL_AEE_V1.csv.gz",
    "PAINEL_EDUCACAO_RURAL_TERRITORIO_V1.csv.gz",
    "MATRIZ_VINCULOS_PNE_PME_JOB5GB_V1.csv.gz",
    "NOVA_SANTA_RITA_JOB5GB_V1.json",
    "MATRIZ_OPORTUNIDADES_REAVALIADAS_JOB5GB_V1.csv.gz",
    "MAPA_SECOES_POTENCIAIS_JOB5GB_V1.md",
    "LIMITACOES_JOB5GB_V1.json",
    "PACOTE_REVISAO_EXTERNA_JOB5GB.json",
    "MANIFEST_JOB5GB.json",
)

ALLOWED_CLASSIFICATIONS = {
    "READY_FOR_INTERNAL_VISUAL_PROTOTYPE",
    "READY_WITH_LIMITS",
    "DESCRIPTIVE_CONTEXT_ONLY",
    "PROMISING_NEEDS_MORE_TESTING",
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
CRITERIA = {
    "c1": "Pergunta substantiva e consequência potencial para planejamento",
    "c2": "Mecanismo ou processo plausível explicitado sem causalidade automática",
    "c3": "Universo definido e não confundido com outros públicos",
    "c4": "Lente territorial explícita e compatível",
    "c5": "Fonte local oficial ou artefato congelado com proveniência",
    "c6": "Período adequado e mudanças de definição examinadas",
    "c7": "Completude do recorte, grão e unicidade verificados",
    "c8": "Agregação por componentes e fórmulas válidas",
    "c9": "Semântica segura e inferências proibidas registradas",
    "c10": "Evidência municipal, Vale e Nova Santa Rita preservada",
    "c11": "Informação adicional não redundante para acompanhamento",
    "c12": "Questão de planejamento e indicador de acompanhamento identificados",
}
EXPECTED_MANIFEST_HASHES = {
    JOB5F_ROOT / "manifest.json": "0980d08fa60ee0b15633ff58b6f4df80eaa8f5357d5c1248bf4e8f9a836d31d0",
    JOB5GA_ROOT / "MANIFEST_JOB5GA.json": "e9a327c517e1a77f8b256663899916853f0d84fe87d3e82adcc6f29dcc58ab2c",
    JOB5GAR_ROOT / "MANIFEST_JOB5GAR.json": "4cad7f2a349be252ba85face41731d41d4b38a48419730c842ee9a6e09b97252",
}


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _stable(frame: pd.DataFrame, columns: Sequence[str]) -> pd.DataFrame:
    return frame.sort_values(list(columns), kind="mergesort", na_position="last").reset_index(drop=True)


def _require_ibge(value: Any) -> str:
    if not isinstance(value, str) or re.fullmatch(r"\d{7}", value) is None:
        raise ValueError(f"Código IBGE inválido ou não textual: {value!r}")
    return value


def _load_scope() -> tuple[list[str], dict[str, str], list[str], dict[str, str]]:
    region_payload = _load_json(REGION_CONFIG_PATH)
    region = next(item for item in region_payload["regions"] if item["slug"] == "vale-do-sinos")
    region_codes = [_require_ibge(value) for value in region["municipalityIbgeCodes"]]
    if len(region_codes) != 10 or len(set(region_codes)) != 10:
        raise ValueError("O Vale do Sinos deve conter exatamente dez municípios.")
    registry = _load_json(MUNICIPALITY_REGISTRY_PATH)["municipalities"]
    state_names = {_require_ibge(item["ibgeCode"]): item["name"] for item in registry}
    if len(state_names) != 497:
        raise ValueError("O registro canônico do RS deve conter 497 municípios.")
    region_names = {code: state_names[code] for code in region_codes}
    if region_names.get(NOVA_SANTA_RITA_ID) != "Nova Santa Rita":
        raise ValueError("Nova Santa Rita não foi preservada no universo canônico.")
    return region_codes, region_names, list(state_names), state_names


def _database_url(database: str = "sesi") -> URL:
    required = ("DB_USUARIO", "DB_SENHA", "DB_HOST")
    missing = [key for key in required if not os.getenv(key)]
    if missing:
        raise RuntimeError(f"Variáveis locais ausentes: {', '.join(missing)}")
    return URL.create(
        "postgresql+psycopg2",
        username=os.environ["DB_USUARIO"],
        password=os.environ["DB_SENHA"],
        host=os.environ["DB_HOST"],
        port=int(os.getenv("DB_PORT", "5432")),
        database=database,
    )


@contextmanager
def _read_only_connection() -> Iterator[Connection]:
    engine = create_engine(
        _database_url(),
        connect_args={"options": "-c default_transaction_read_only=on -c statement_timeout=180000"},
    )
    try:
        with engine.connect() as connection:
            transaction = connection.begin()
            try:
                connection.execute(text("SET TRANSACTION READ ONLY"))
                mode = connection.execute(text("SELECT current_setting('transaction_read_only')")).scalar_one()
                if mode != "on":
                    raise RuntimeError("A sessão do Job 5G-B não está em modo somente leitura.")
                yield connection
            finally:
                transaction.rollback()
    finally:
        engine.dispose()


def _frame_digest(frame: pd.DataFrame, sort_columns: Sequence[str]) -> str:
    stable = _stable(frame.copy(), sort_columns)
    payload = stable.to_csv(index=False, lineterminator="\n", na_rep="null").encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _verify_previous_packages() -> dict[str, Any]:
    verified: dict[str, Any] = {}
    for manifest_path, expected in EXPECTED_MANIFEST_HASHES.items():
        actual = sha256_file(manifest_path)
        if actual != expected:
            raise ValueError(f"Manifest congelado divergente: {manifest_path}: {actual} != {expected}")
        payload = _load_json(manifest_path)
        artifact_count = 0
        for artifact in payload.get("artifacts", []):
            artifact_path = manifest_path.parent / artifact["path"]
            if sha256_file(artifact_path) != artifact["sha256"]:
                raise ValueError(f"Artefato congelado divergente: {artifact_path}")
            artifact_count += 1
        verified[manifest_path.parent.name] = {
            "manifestPath": manifest_path.relative_to(REPO_ROOT).as_posix(),
            "manifestSha256": actual,
            "artifactCount": artifact_count,
        }
    return verified


def _query_sources(
    connection: Connection, state_codes: Sequence[str], region_codes: Sequence[str]
) -> dict[str, pd.DataFrame]:
    adult = pd.read_sql_query(
        text(
            """
            SELECT f.ano::int AS year,
                   f.id_municipio::text AS municipality_ibge_code,
                   f.populacao_18_mais_ensino_fundamental_concluido::double precision AS fundamental_completed,
                   m.populacao_18_mais_ensino_medio_concluido::double precision AS high_school_completed,
                   c.populacao_18_mais_total::double precision AS adult_population
            FROM public.censo_populacao_ensino_fundamental_concluido_18_mais f
            JOIN public.censo_populacao_ensino_medio_concluido_18_mais m
              ON m.ano=f.ano AND m.id_municipio=f.id_municipio AND m.sigla_uf=f.sigla_uf
            LEFT JOIN public.pne2026_censo_10061_municipal_components c
              ON c.ano=f.ano AND c.id_municipio::text=f.id_municipio::text
            WHERE f.sigla_uf='RS' AND f.ano IN (2010, 2022)
            """
        ),
        connection,
    )
    schema = pd.read_sql_query(
        text(
            """
            SELECT column_name FROM information_schema.columns
            WHERE table_schema='public' AND table_name='censo_educacao_especial_escolas'
            ORDER BY ordinal_position
            """
        ),
        connection,
    )["column_name"].tolist()
    wanted = {
        "ano", "cod_escola", "id_municipio", "dependencia", "localizacao", "rede_publica",
        "QT_MAT_ESP", "QT_MAT_ESP_CC", "QT_MAT_ESP_CE", "QT_TUR_ESP", "QT_TUR_ESP_CC",
        "QT_TUR_ESP_CE", "QT_DOC_ESP", "QT_DOC_ESP_CC", "QT_DOC_ESP_CE", "QT_DOC_BAS",
        "QT_MAT_ESP_INF", "QT_MAT_ESP_INF_CRE", "QT_MAT_ESP_INF_PRE", "QT_MAT_ESP_FUND",
        "QT_MAT_ESP_FUND_AI", "QT_MAT_ESP_FUND_AF", "QT_MAT_ESP_MED", "QT_MAT_ESP_PROF",
        "QT_MAT_ESP_EJA", "QT_MAT_ESP_INT", "QT_TUR_ESP_INT", "TP_AEE",
        "IN_SALA_ATENDIMENTO_ESPECIAL",
    }
    prefixes = ("disponivel_", "valor_extremo_", "vazio_estrutural_")
    selected = [column for column in schema if column in wanted or column.startswith(prefixes)]
    if not wanted.issubset(set(selected)):
        raise ValueError(f"Fonte especial sem colunas requeridas: {sorted(wanted-set(selected))}")
    quoted = ", ".join(f'"{column}"' for column in selected)
    special = pd.read_sql_query(
        text(f'SELECT {quoted} FROM public.censo_educacao_especial_escolas WHERE id_municipio = ANY(:codes)'),
        connection,
        params={"codes": list(state_codes)},
    )
    rural = pd.read_sql_query(
        text(
            """
            SELECT ano::int AS year, id_municipio::text AS municipality_ibge_code,
                   cod_escola::text AS school_code,
                   mat_basico, mat_infantil, mat_fundamental, mat_medio,
                   mat_profissional, mat_eja,
                   turmas_basico, turmas_infantil, turmas_fundamental, turmas_medio,
                   turmas_profissional, turmas_eja
            FROM public.censo_escolas
            WHERE id_municipio = ANY(:codes)
              AND ano BETWEEN 2014 AND 2025
              AND lower(localizacao)='rural'
              AND (situacao_funcionamento=1 OR situacao_funcionamento IS NULL)
            """
        ),
        connection,
        params={"codes": list(state_codes)},
    )
    indigenous = pd.read_sql_query(
        text(
            """
            SELECT ano::int AS year,
                   id_municipio::text AS municipality_ibge_code,
                   recorte::text AS segment,
                   unidade::text AS unit_of_observation,
                   valor::double precision AS value,
                   grupo_comparabilidade::text AS comparability_group
            FROM public.educacao_indigena_municipal
            WHERE id_municipio = ANY(:codes)
              AND ano BETWEEN 2023 AND 2025
              AND recorte='total'
            """
        ),
        connection,
        params={"codes": list(region_codes)},
    )
    return {
        "adult": adult,
        "special": special,
        "rural": rural,
        "indigenous": indigenous,
    }


def _entity_specs(
    region_codes: Sequence[str], region_names: Mapping[str, str], state_codes: Sequence[str]
) -> list[tuple[str, str | None, str, set[str]]]:
    specs = [("municipality", code, region_names[code], {code}) for code in region_codes]
    specs.append(("region", None, "Vale do Sinos", set(region_codes)))
    specs.append(("state", None, "Rio Grande do Sul", set(state_codes)))
    return specs


def _adult_dictionary() -> dict[str, Any]:
    return {
        "schemaVersion": "adult-schooling-dictionary-v1",
        "universe": "resident_population_18_or_more",
        "unit": "persons_and_percent",
        "territorialLens": "resident_population",
        "period": [2010, 2022],
        "source": "IBGE Censo Demográfico 2010 e 2022; tabelas locais de conclusão e componentes SIDRA 10061",
        "denominatorAudit": {
            "2010": "SOURCE_UNAVAILABLE",
            "2022": "COMPARABLE",
            "finding": "O denominador 18+ de 2010 não está materializado na fonte local canônica; nenhuma aproximação foi feita.",
        },
        "categories": [
            {
                "categoryId": "fundamental_completed_or_more",
                "ageUniverse": "18_or_more",
                "definition2010": "Contagem residente de 18 anos ou mais com ensino fundamental concluído.",
                "definition2022": "Contagem residente de 18 anos ou mais com ensino fundamental concluído.",
                "compatibility": "COMPARABLE",
                "harmonizationRule": "Usar a contagem cumulativa observada; participação somente com denominador censitário do mesmo ano.",
                "incompatibilities": ["O vínculo legal principal 11.b usa 15+; o recorte 18+ é componente oculto no diagnóstico atual."],
            },
            {
                "categoryId": "high_school_completed_or_more",
                "ageUniverse": "18_or_more",
                "definition2010": "Contagem residente de 18 anos ou mais com ensino médio concluído.",
                "definition2022": "Contagem residente de 18 anos ou mais com ensino médio concluído.",
                "compatibility": "COMPARABLE",
                "harmonizationRule": "Usar a contagem cumulativa observada; participação somente com denominador censitário do mesmo ano.",
                "incompatibilities": [],
            },
            {
                "categoryId": "fundamental_completed_without_high_school",
                "ageUniverse": "18_or_more",
                "definition2010": "Diferença entre as duas contagens cumulativas compatíveis.",
                "definition2022": "Diferença entre as duas contagens cumulativas compatíveis.",
                "compatibility": "PARTIALLY_HARMONIZABLE",
                "harmonizationRule": "fundamental_completed_or_more - high_school_completed_or_more, somente quando não negativa.",
                "incompatibilities": ["Categoria derivada, não rótulo bruto da fonte."],
            },
            {
                "categoryId": "without_fundamental_completed",
                "ageUniverse": "18_or_more",
                "definition2010": None,
                "definition2022": "População 18+ total menos população 18+ com fundamental concluído.",
                "compatibility": "SOURCE_UNAVAILABLE",
                "harmonizationRule": "Não calcular mudança intercensitária sem denominador local de 2010.",
                "incompatibilities": ["Denominador 18+ de 2010 ausente."],
            },
        ],
        "aggregation": "Vale e RS recompostos por soma das contagens; nenhuma média simples de percentuais.",
    }


def _build_adult_panel(
    raw: pd.DataFrame,
    region_codes: Sequence[str],
    region_names: Mapping[str, str],
    state_codes: Sequence[str],
) -> pd.DataFrame:
    raw = raw.copy()
    raw["municipality_ibge_code"] = raw["municipality_ibge_code"].astype(str)
    if set(raw["municipality_ibge_code"]) != set(state_codes):
        raise ValueError("Fonte adulta não cobre os 497 códigos canônicos do RS.")
    validate_unique_key(raw, ["year", "municipality_ibge_code"], label="Escolaridade adulta bruta")
    if (raw["fundamental_completed"] < raw["high_school_completed"]).any():
        raise ValueError("Conclusão do médio excede conclusão do fundamental.")
    rows: list[dict[str, Any]] = []
    specs = _entity_specs(region_codes, region_names, state_codes)
    category_specs = (
        ("fundamental_completed_or_more", "fundamental_completed"),
        ("high_school_completed_or_more", "high_school_completed"),
        ("fundamental_completed_without_high_school", "derived_middle"),
        ("without_fundamental_completed", "derived_low"),
    )
    for entity_scope, code, name, members in specs:
        selected = raw[raw["municipality_ibge_code"].isin(members)]
        by_year = selected.groupby("year", as_index=True).agg(
            fundamental_completed=("fundamental_completed", "sum"),
            high_school_completed=("high_school_completed", "sum"),
            adult_population=("adult_population", lambda s: s.sum(min_count=len(s))),
        )
        values: dict[tuple[int, str], float | None] = {}
        shares: dict[tuple[int, str], float | None] = {}
        for year in (2010, 2022):
            point = by_year.loc[year]
            for category, source_column in category_specs:
                if source_column == "derived_middle":
                    value = point["fundamental_completed"] - point["high_school_completed"]
                elif source_column == "derived_low":
                    value = (
                        point["adult_population"] - point["fundamental_completed"]
                        if pd.notna(point["adult_population"])
                        else None
                    )
                else:
                    value = point[source_column]
                value = None if value is None or pd.isna(value) else float(value)
                population = point["adult_population"]
                share = None if value is None or pd.isna(population) or population == 0 else 100 * value / population
                values[(year, category)] = value
                shares[(year, category)] = share
        for year in (2010, 2022):
            for category, _ in category_specs:
                value = values[(year, category)]
                share = shares[(year, category)]
                change = (
                    values[(2022, category)] - values[(2010, category)]
                    if values[(2010, category)] is not None and values[(2022, category)] is not None
                    else None
                )
                pp_change = (
                    shares[(2022, category)] - shares[(2010, category)]
                    if shares[(2010, category)] is not None and shares[(2022, category)] is not None
                    else None
                )
                rows.append(
                    {
                        "entity_scope": entity_scope,
                        "municipality_ibge_code": code,
                        "municipality_name": name,
                        "year": year,
                        "age_universe": "18_or_more",
                        "schooling_category": category,
                        "count_value": value,
                        "count_value_status": "observed" if value is not None else "unavailable",
                        "adult_population_denominator": (
                            float(by_year.loc[year, "adult_population"])
                            if pd.notna(by_year.loc[year, "adult_population"])
                            else None
                        ),
                        "adult_population_status": "observed" if pd.notna(by_year.loc[year, "adult_population"]) else "unavailable",
                        "share_percent": share,
                        "share_status": "observed" if share is not None else "unavailable",
                        "absolute_change_2010_2022": change,
                        "percentage_point_change_2010_2022": pp_change,
                        "municipal_contribution_to_vale_change_percent": None,
                        "territorial_lens": "resident_population",
                        "source": "IBGE_Censo_Demografico_2010_2022_local_materialization",
                        "aggregation_rule": "sum_compatible_counts_then_ratio",
                    }
                )
    panel = pd.DataFrame(rows)
    for category in [item[0] for item in category_specs]:
        regional = panel[
            panel["entity_scope"].eq("region")
            & panel["year"].eq(2022)
            & panel["schooling_category"].eq(category)
        ]["absolute_change_2010_2022"].iloc[0]
        if pd.notna(regional) and regional != 0:
            mask = panel["entity_scope"].eq("municipality") & panel["schooling_category"].eq(category)
            panel.loc[mask, "municipal_contribution_to_vale_change_percent"] = (
                100 * panel.loc[mask, "absolute_change_2010_2022"] / regional
            )
    return _stable(panel, ["entity_scope", "municipality_ibge_code", "year", "schooling_category"])


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype={"municipality_ibge_code": "string"}, keep_default_na=False, na_values=["null"])


def _build_eja_distribution(region_codes: Sequence[str]) -> pd.DataFrame:
    source_path = JOB2_ROOT / "eja_demanda_oferta_2022.csv.gz"
    source = _read_csv(source_path)
    source = source[source["entity_scope"].isin(["municipality", "region"])].copy()
    numeric = ["potential_public", "eja_enrollments", "participacao_publico_i", "participacao_matriculas_i", "diferenca_distribuicao_pp"]
    for column in numeric:
        source[column] = pd.to_numeric(source[column], errors="raise")
    municipal = source[source["entity_scope"].eq("municipality")]
    if set(municipal["municipality_ibge_code"].astype(str)) != set(region_codes):
        raise ValueError("EJA 2022 não preserva os dez municípios do Vale.")
    panel = pd.DataFrame(
        {
            "entity_scope": source["entity_scope"],
            "municipality_ibge_code": source["municipality_ibge_code"],
            "municipality_name": source["municipality_name"],
            "year": 2022,
            "stage": source["stage"],
            "resident_adult_public": source["potential_public"],
            "school_location_eja_enrollments": source["eja_enrollments"],
            "share_of_regional_public_percent": 100 * source["participacao_publico_i"],
            "share_of_regional_enrollments_percent": 100 * source["participacao_matriculas_i"],
            "distribution_difference_percentage_points": 100 * source["diferenca_distribuicao_pp"],
            "distribution_direction": source["diferenca_distribuicao_pp"].map(lambda value: "above_public_share" if value > 0 else ("below_public_share" if value < 0 else "equal_share")),
            "resident_universe_definition": source["universe_definition"],
            "resident_public_population_source": source["stage"].map(
                {
                    "fundamental": "public.populacao_idade_2022_estimated_total_minus_census_completion",
                    "high_school": "census_completion_count_difference_2022",
                }
            ),
            "resident_public_compatibility_with_adult_panel": source["stage"].map(
                {
                    "fundamental": "definition_incompatible_population_total_source",
                    "high_school": "comparable_count_difference",
                }
            ),
            "territorial_lens": "resident_population_vs_school_location",
            "network_scope": "total_all_dependencies",
            "administrative_dependency_is_analytic_dimension": False,
            "administrative_dependency_is_QA_dimension": True,
            "value_status": "observed",
            "source": "Job2C_eja_demanda_oferta_2022_frozen",
        }
    )
    nsr = panel[panel["municipality_ibge_code"].eq(NOVA_SANTA_RITA_ID)].set_index("stage")
    if nsr.loc["fundamental", "distribution_direction"] != "above_public_share":
        raise ValueError("A direção fundamental de Nova Santa Rita foi alterada.")
    if nsr.loc["high_school", "distribution_direction"] != "below_public_share":
        raise ValueError("A direção média de Nova Santa Rita foi alterada.")
    validate_unique_key(panel, ["entity_scope", "municipality_ibge_code", "stage"], label="EJA distribuição")
    return _stable(panel, ["entity_scope", "municipality_ibge_code", "stage"])


def _historical_source(region_codes: Sequence[str]) -> pd.DataFrame:
    source = _read_csv(JOB2_ROOT / "eja_integrada_historica.csv.gz")
    source["year"] = pd.to_numeric(source["year"], errors="raise").astype(int)
    value_columns = [column for column in source if column.startswith("mat_eja_") or column == "mat_eja_total"]
    for column in value_columns + ["integrated_share_percent"]:
        source[column] = pd.to_numeric(source[column], errors="raise")
    municipal = source[source["entity_scope"].eq("municipality")]
    if set(municipal["municipality_ibge_code"].astype(str)) != set(region_codes):
        raise ValueError("EJA histórica não preserva os dez municípios do Vale.")
    if not (source["mat_eja_total"] == source["mat_eja_fundamental_total"] + source["mat_eja_medio_total"]).all():
        raise ValueError("EJA total não fecha com fundamental + médio.")
    if not (
        source["mat_eja_integrada_educacao_profissional"]
        == source["mat_eja_curso_tecnico_integrada"]
        + source["mat_eja_fic_integrado_fundamental"]
        + source["mat_eja_fic_integrado_medio"]
    ).all():
        raise ValueError("EJA integrada não fecha com as modalidades.")
    administrative_closure = (
        source["mat_eja_integrada_educacao_profissional"]
        == source["mat_eja_integrada_educacao_profissional_publica"]
        + source["mat_eja_integrada_educacao_profissional_privada"]
    )
    source.attrs["administrative_dependency_closure_mismatch_count"] = int((~administrative_closure).sum())
    source.attrs["administrative_dependency_closure_mismatch_years"] = sorted(
        source.loc[~administrative_closure, "year"].unique().tolist()
    )
    validate_unique_key(source, ["entity_scope", "municipality_ibge_code", "year"], label="EJA histórica congelada")
    return source


def _build_eja_historical(source: pd.DataFrame) -> pd.DataFrame:
    stage_columns = {
        "fundamental": "mat_eja_fundamental_total",
        "high_school": "mat_eja_medio_total",
        "total_context": "mat_eja_total",
    }
    rows: list[dict[str, Any]] = []
    region_changes = {
        stage: float(
            source[(source["entity_scope"].eq("region")) & source["year"].eq(2025)][column].iloc[0]
            - source[(source["entity_scope"].eq("region")) & source["year"].eq(2014)][column].iloc[0]
        )
        for stage, column in stage_columns.items()
    }
    for record in source.itertuples(index=False):
        record_code = "" if pd.isna(record.municipality_ibge_code) else str(record.municipality_ibge_code)
        entity = source[
            source["entity_scope"].eq(record.entity_scope)
            & source["municipality_ibge_code"].fillna("").astype(str).eq(record_code)
        ].sort_values("year")
        for stage, column in stage_columns.items():
            current = float(getattr(record, column))
            prior_rows = entity[entity["year"].eq(record.year - 1)]
            prior = float(prior_rows[column].iloc[0]) if not prior_rows.empty else None
            baseline = float(entity[entity["year"].eq(2014)][column].iloc[0])
            end = float(entity[entity["year"].eq(2025)][column].iloc[0])
            total = float(record.mat_eja_total)
            rows.append(
                {
                    "entity_scope": record.entity_scope,
                    "municipality_ibge_code": record.municipality_ibge_code,
                    "municipality_name": record.municipality_name,
                    "year": record.year,
                    "stage": stage,
                    "eja_enrollments": current,
                    "value_status": "observed",
                    "year_over_year_absolute_change": None if prior is None else current - prior,
                    "year_over_year_percent_change": None if prior in (None, 0) else 100 * (current - prior) / prior,
                    "absolute_change_2014_2025": end - baseline,
                    "municipal_contribution_to_vale_change_percent": (
                        100 * (end - baseline) / region_changes[stage]
                        if record.entity_scope == "municipality" and region_changes[stage] != 0
                        else None
                    ),
                    "stage_composition_percent": (
                        100 * current / total if stage != "total_context" and total != 0 else (100.0 if stage == "total_context" and total != 0 else None)
                    ),
                    "series_break_status": "not_confirmed_local_definition_metadata_absent",
                    "territorial_lens": "school_location",
                    "network_scope": "total_all_dependencies",
                    "administrative_dependency_is_analytic_dimension": False,
                    "administrative_dependency_is_QA_dimension": True,
                    "source": "Job2C_eja_integrada_historica_frozen",
                }
            )
    panel = pd.DataFrame(rows)
    validate_unique_key(panel, ["entity_scope", "municipality_ibge_code", "year", "stage"], label="EJA histórica")
    return _stable(panel, ["entity_scope", "municipality_ibge_code", "year", "stage"])


def _build_eja_integrated(source: pd.DataFrame) -> pd.DataFrame:
    modalities = {
        "integrated_total": "mat_eja_integrada_educacao_profissional",
        "technical_integrated": "mat_eja_curso_tecnico_integrada",
        "fic_fundamental": "mat_eja_fic_integrado_fundamental",
        "fic_high_school": "mat_eja_fic_integrado_medio",
    }
    rows: list[dict[str, Any]] = []
    for record in source.itertuples(index=False):
        for modality, column in modalities.items():
            value = float(getattr(record, column))
            total = float(record.mat_eja_total)
            rows.append(
                {
                    "entity_scope": record.entity_scope,
                    "municipality_ibge_code": record.municipality_ibge_code,
                    "municipality_name": record.municipality_name,
                    "year": record.year,
                    "modality": modality,
                    "integrated_eja_enrollments": value,
                    "value_status": "observed",
                    "eja_total_enrollments": total,
                    "share_of_eja_percent": None if total == 0 else 100 * value / total,
                    "share_status": "not_applicable" if total == 0 else "observed",
                    "territorial_lens": "school_location",
                    "network_scope": "total_all_dependencies",
                    "administrative_dependency_is_analytic_dimension": False,
                    "administrative_dependency_is_QA_dimension": True,
                    "source": "Job2C_eja_integrada_historica_frozen",
                    "planning_question": "Como articular o acompanhamento da EJA e da educação profissional sem concluir adequação de escala?",
                }
            )
    panel = pd.DataFrame(rows)
    validate_unique_key(panel, ["entity_scope", "municipality_ibge_code", "year", "modality"], label="EJA integrada")
    return _stable(panel, ["entity_scope", "municipality_ibge_code", "year", "modality"])


CADUNICO_METRICS = {
    "registered_families": ("cadun_qtd_familias_cadastradas_i", "families"),
    "registered_people": ("cadun_qtd_pessoas_cadastradas_i", "people"),
    "updated_families": ("cadun_qtd_familias_atualizadas_i", "families"),
    "low_income_registered_families": ("cadun_qtd_familias_cadastradas_baixa_renda_i", "families"),
    "low_income_registered_people": ("cadun_qtd_pessoas_cadastradas_baixa_renda_i", "people"),
    "registered_families_up_to_half_minimum_wage_per_capita": ("cadun_qtd_familias_cadastradas_rfpc_ate_meio_sm_i", "families"),
    "registered_people_up_to_half_minimum_wage_per_capita": ("cadun_qtd_pessoas_cadastradas_rfpc_ate_meio_sm_i", "people"),
    "registered_families_pbf_poverty_line": ("cadun_qtd_familias_cadastradas_pobreza_pbf_i", "families"),
    "registered_people_pbf_poverty_line": ("cadun_qtd_pessoas_cadastradas_pobreza_pbf_i", "people"),
    "updated_families_declared_zero_income": ("cadun_qtd_familias_atualizadas_renda_zero_i", "families"),
    "registered_people_age_0_15": ("qtd_pes_total_cadunico_idade_0_a_15_i", "people"),
}


def _build_vulnerability(
    region_codes: Sequence[str], region_names: Mapping[str, str]
) -> tuple[pd.DataFrame, dict[str, str]]:
    rows: list[dict[str, Any]] = []
    hashes: dict[str, str] = {}
    for code in region_codes:
        path = CADUNICO_ROOT / f"misocial_{code[:6]}.json"
        hashes[path.relative_to(REPO_ROOT).as_posix()] = sha256_file(path)
        docs = _load_json(path).get("response", {}).get("docs", [])
        point = next((item for item in docs if str(item.get("anomes_s")) == "202412"), None)
        if point is None or str(point.get("codigo_ibge")) != code[:6]:
            raise ValueError(f"CadÚnico sem âncora 202412 para {code}")
        for metric, (field, unit) in CADUNICO_METRICS.items():
            value = point.get(field)
            rows.append(
                {
                    "entity_scope": "municipality",
                    "context_domain": "registered_vulnerability_context",
                    "municipality_ibge_code": code,
                    "municipality_name": region_names[code],
                    "reference_period": "2024-12",
                    "metric": metric,
                    "unit_of_observation": unit,
                    "value": value,
                    "value_status": "observed" if value is not None else "unavailable",
                    "territorial_lens": "registered_residence_or_source_declared_municipality",
                    "network_scope": "not_applicable",
                    "administrative_dependency_is_analytic_dimension": False,
                    "administrative_dependency_is_QA_dimension": False,
                    "source": "MDS_SAGI_MI_Social_local_raw_snapshot",
                    "educational_profile_compatibility": "context_only_no_adult_schooling_fields",
                    "micro_linkage_performed": False,
                }
            )
    municipal = pd.DataFrame(rows)
    region_rows = []
    for (period, metric, unit), group in municipal.groupby(["reference_period", "metric", "unit_of_observation"], sort=True):
        complete = group["value"].notna().all()
        region_rows.append(
            {
                "entity_scope": "region",
                "context_domain": "registered_vulnerability_context",
                "municipality_ibge_code": None,
                "municipality_name": "Vale do Sinos",
                "reference_period": period,
                "metric": metric,
                "unit_of_observation": unit,
                "value": float(group["value"].sum()) if complete else None,
                "value_status": "observed" if complete else "unavailable",
                "territorial_lens": "registered_residence_or_source_declared_municipality",
                "network_scope": "not_applicable",
                "administrative_dependency_is_analytic_dimension": False,
                "administrative_dependency_is_QA_dimension": False,
                "source": "MDS_SAGI_MI_Social_local_raw_snapshot",
                "educational_profile_compatibility": "context_only_no_adult_schooling_fields",
                "micro_linkage_performed": False,
            }
        )
    panel = pd.concat([municipal, pd.DataFrame(region_rows)], ignore_index=True)
    validate_unique_key(
        panel,
        ["context_domain", "entity_scope", "municipality_ibge_code", "reference_period", "metric"],
        label="Vulnerabilidade",
    )
    return _stable(panel, ["context_domain", "entity_scope", "municipality_ibge_code", "metric"]), hashes


def _build_indigenous_context(
    source: pd.DataFrame,
    region_codes: Sequence[str],
    region_names: Mapping[str, str],
) -> pd.DataFrame:
    expected_units = {"docentes", "estabelecimentos", "matriculas", "turmas"}
    source = source.copy()
    source["municipality_ibge_code"] = source["municipality_ibge_code"].map(_require_ibge)
    if set(source["municipality_ibge_code"]) != set(region_codes):
        raise ValueError("Educação indígena não preserva os dez municípios do Vale.")
    if set(source["year"]) != {2023, 2024, 2025}:
        raise ValueError("Educação indígena não preserva a janela compatível 2023-2025.")
    if set(source["unit_of_observation"]) != expected_units:
        raise ValueError("Unidades inesperadas na educação indígena.")
    if not source["comparability_group"].eq("comparavel_2023_2025").all():
        raise ValueError("Grupo de comparabilidade indígena inesperado.")
    if len(source) != 10 * 3 * 4 or source["value"].isna().any() or source["value"].lt(0).any():
        raise ValueError("Completude de linhas ou valores inválidos na educação indígena.")
    validate_unique_key(
        source,
        ["municipality_ibge_code", "year", "unit_of_observation"],
        label="Educação indígena local",
    )
    metric_map = {
        "docentes": ("indigenous_teachers_total", "teachers"),
        "estabelecimentos": ("indigenous_schools_total", "schools"),
        "matriculas": ("indigenous_enrollments_total", "enrollments"),
        "turmas": ("indigenous_classes_total", "classes"),
    }
    municipal_rows = []
    for record in source.itertuples(index=False):
        metric, unit = metric_map[record.unit_of_observation]
        municipal_rows.append(
            {
                "entity_scope": "municipality",
                "context_domain": "indigenous_education_specific_public",
                "municipality_ibge_code": record.municipality_ibge_code,
                "municipality_name": region_names[record.municipality_ibge_code],
                "reference_period": str(record.year),
                "metric": metric,
                "unit_of_observation": unit,
                "value": float(record.value),
                "value_status": "observed",
                "territorial_lens": "school_location",
                "network_scope": "total_all_dependencies",
                "administrative_dependency_is_analytic_dimension": False,
                "administrative_dependency_is_QA_dimension": True,
                "source": "INEP_educacao_indigena_municipal",
                "educational_profile_compatibility": "specific_school_observation_without_resident_denominator",
                "micro_linkage_performed": False,
            }
        )
    municipal = pd.DataFrame(municipal_rows)
    region_rows = []
    for (period, metric, unit), group in municipal.groupby(
        ["reference_period", "metric", "unit_of_observation"], sort=True
    ):
        region_rows.append(
            {
                "entity_scope": "region",
                "context_domain": "indigenous_education_specific_public",
                "municipality_ibge_code": None,
                "municipality_name": "Vale do Sinos",
                "reference_period": period,
                "metric": metric,
                "unit_of_observation": unit,
                "value": float(group["value"].sum()),
                "value_status": "observed",
                "territorial_lens": "school_location",
                "network_scope": "total_all_dependencies",
                "administrative_dependency_is_analytic_dimension": False,
                "administrative_dependency_is_QA_dimension": True,
                "source": "INEP_educacao_indigena_municipal",
                "educational_profile_compatibility": "specific_school_observation_without_resident_denominator",
                "micro_linkage_performed": False,
            }
        )
    panel = pd.concat([municipal, pd.DataFrame(region_rows)], ignore_index=True)
    validate_unique_key(
        panel,
        ["context_domain", "entity_scope", "municipality_ibge_code", "reference_period", "metric"],
        label="Educação indígena no painel de públicos específicos",
    )
    return _stable(
        panel,
        ["context_domain", "entity_scope", "municipality_ibge_code", "reference_period", "metric"],
    )


def _point_to_value(point: Mapping[str, Any]) -> tuple[float | None, str, str | None]:
    state = point["state"]
    if state in {"observed", "derived_zero"}:
        return point.get("value"), "observed", point.get("reason")
    if state == "partial" and point.get("reason") == "non_publishable_extreme_value":
        return None, "suppressed", point.get("reason")
    if state == "partial":
        return None, "unavailable", point.get("reason")
    if state in ALLOWED_VALUE_STATES:
        return point.get("value"), state, point.get("reason")
    raise ValueError(f"Estado especial desconhecido: {state}")


def _build_special_panel(
    source: pd.DataFrame,
    region_codes: Sequence[str],
    region_names: Mapping[str, str],
    state_codes: Sequence[str],
) -> pd.DataFrame:
    source = source.copy()
    source["id_municipio"] = source["id_municipio"].astype(str)
    if source.duplicated(["ano", "cod_escola"]).any():
        raise ValueError("Fonte especial não preserva ano x escola único.")
    availability = special_field_availability(source)
    specs = _entity_specs(region_codes, region_names, state_codes)
    metrics = {
        "special_enrollments": ("special", "enrollments", "all"),
        "common_class_enrollments": ("special", "commonClassEnrollments", "all"),
        "exclusive_class_enrollments": ("special", "exclusiveClassEnrollments", "all"),
        "schools_with_special_enrollment": ("special", "schools", "all"),
        "schools_offering_aee": ("aee", "schoolsOfferingAee", "all"),
        "schools_with_aee_resource_room": ("aee", "schoolsWithResourceRoom", "all"),
        "special_enrollments_early_childhood": ("stage", "earlyChildhood", "early_childhood"),
        "special_enrollments_fundamental": ("stage", "elementary", "fundamental"),
        "special_enrollments_high_school": ("stage", "highSchool", "high_school"),
        "special_enrollments_professional": ("stage", "professional", "professional"),
        "special_enrollments_eja": ("stage", "youthAndAdult", "eja"),
    }
    rows: list[dict[str, Any]] = []
    for year in YEARS:
        year_all = source[source["ano"].eq(year)].copy()
        year_all.attrs["available_fields"] = {
            field for field, metadata in availability.items() if year in metadata["observedYears"]
        }
        for entity_scope, code, name, members in specs:
            frame = year_all[year_all["id_municipio"].isin(members)]
            special = special_metrics(frame, year_all)
            aee = special_aee(frame, year_all)
            for metric, (group, key, stage) in metrics.items():
                point = special["stages"][key] if group == "stage" else (special[key] if group == "special" else aee[key])
                value, status, reason = _point_to_value(point)
                rows.append(
                    {
                        "entity_scope": entity_scope,
                        "municipality_ibge_code": code,
                        "municipality_name": name,
                        "year": year,
                        "metric": metric,
                        "stage": stage,
                        "value": value,
                        "value_status": status,
                        "reason": reason,
                        "unit": "schools" if metric.startswith("schools_") else "enrollments",
                        "territorial_lens": "school_location",
                        "network_scope": "total_all_dependencies",
                        "administrative_dependency_is_analytic_dimension": False,
                        "administrative_dependency_is_QA_dimension": True,
                        "source": "INEP_Censo_Escolar_censo_educacao_especial_escolas",
                    }
                )
    panel = pd.DataFrame(rows)
    validate_unique_key(panel, ["entity_scope", "municipality_ibge_code", "year", "metric"], label="Especial/AEE")
    return _stable(panel, ["entity_scope", "municipality_ibge_code", "year", "metric"])


def _build_rural_panel(
    source: pd.DataFrame,
    region_codes: Sequence[str],
    region_names: Mapping[str, str],
    state_codes: Sequence[str],
) -> pd.DataFrame:
    source = source.copy()
    source["municipality_ibge_code"] = source["municipality_ibge_code"].astype(str)
    if source.duplicated(["year", "school_code"]).any():
        raise ValueError("Fonte rural não preserva ano x escola único.")
    stage_columns = {
        "all": ("mat_basico", "turmas_basico"),
        "early_childhood": ("mat_infantil", "turmas_infantil"),
        "fundamental": ("mat_fundamental", "turmas_fundamental"),
        "high_school": ("mat_medio", "turmas_medio"),
        "professional": ("mat_profissional", "turmas_profissional"),
        "eja": ("mat_eja", "turmas_eja"),
    }
    rows: list[dict[str, Any]] = []
    for year in YEARS:
        year_source = source[source["year"].eq(year)]
        for entity_scope, code, name, members in _entity_specs(region_codes, region_names, state_codes):
            frame = year_source[year_source["municipality_ibge_code"].isin(members)]
            for stage, (enrollment_column, classes_column) in stage_columns.items():
                schools = int(frame["school_code"].nunique()) if stage == "all" else int(
                    frame.loc[
                        pd.to_numeric(frame[enrollment_column], errors="coerce").fillna(0).gt(0)
                        | pd.to_numeric(frame[classes_column], errors="coerce").fillna(0).gt(0),
                        "school_code",
                    ].nunique()
                )
                metrics = {
                    "rural_schools": schools,
                    "rural_enrollments": float(pd.to_numeric(frame[enrollment_column], errors="coerce").fillna(0).sum()),
                    "rural_classes": float(pd.to_numeric(frame[classes_column], errors="coerce").fillna(0).sum()),
                }
                for metric, value in metrics.items():
                    rows.append(
                        {
                            "entity_scope": entity_scope,
                            "municipality_ibge_code": code,
                            "municipality_name": name,
                            "year": year,
                            "stage": stage,
                            "metric": metric,
                            "value": value,
                            "value_status": "observed",
                            "unit": "schools" if metric == "rural_schools" else ("enrollments" if metric == "rural_enrollments" else "classes"),
                            "territorial_lens": "rural_school_location",
                            "network_scope": "total_all_dependencies",
                            "administrative_dependency_is_analytic_dimension": False,
                            "administrative_dependency_is_QA_dimension": True,
                            "source": "INEP_Censo_Escolar_censo_escolas",
                            "resident_rural_population_combined": False,
                        }
                    )
    panel = pd.DataFrame(rows)
    validate_unique_key(panel, ["entity_scope", "municipality_ibge_code", "year", "stage", "metric"], label="Educação rural")
    return _stable(panel, ["entity_scope", "municipality_ibge_code", "year", "stage", "metric"])


def _build_pne_links() -> pd.DataFrame:
    rows = [
        ("adult_fundamental_18_plus", "11.b", "fundamental_concluido_18_mais", "hidden", "partial_component", "resident_population", True, "Contagem 18+ intercensitária; relação vigente está oculta para a Meta 11.b."),
        ("adult_high_school_18_plus", "11.c", "medio_concluido_18_mais", "progress", "direct", "resident_population", True, "Componente censitário direto, sem recalcular o indicador legal."),
        ("eja_distribution_fundamental_2022", "11.d", "eja_atendimento_18_mais", "progress", "partial_component", "resident_population_vs_school_location", True, "Distribuição separada do público fundamental; não equivale ao indicador legal misto."),
        ("eja_distribution_high_school_2022", "11.d", "eja_atendimento_18_mais", "progress", "partial_component", "resident_population_vs_school_location", True, "Distribuição separada do público médio; não equivale ao indicador legal misto."),
        ("eja_historical_fundamental", "11.d", "eja_atendimento_18_mais", "progress", "partial_component", "school_location", True, "Matrículas localizadas por etapa como acompanhamento descritivo."),
        ("eja_historical_high_school", "11.d", "eja_atendimento_18_mais", "progress", "partial_component", "school_location", True, "Matrículas localizadas por etapa como acompanhamento descritivo."),
        ("eja_integrated_ept", "12.c", "eja_integrada_educacao_profissional_percentual", "progress", "direct", "school_location", True, "Componentes brutos do indicador vigente, sem alterar fórmula ou status."),
        ("vulnerability_context", "11.e", "not_materialized", "not_structured", "contextual_proxy", "registered_residence_or_source_declared_municipality", True, "Contexto cadastral agregado para orientar pergunta de equidade; não mede público EJA."),
        ("indigenous_education_observed", "9.d", "educacao_indigena_cobertura_estimada_4_17", "complementary", "partial_component", "school_location", True, "Somente componentes escolares observados; o denominador residente do indicador vigente não foi combinado nem recalculado."),
        ("special_education_common_exclusive", "10.a", "not_materialized", "not_structured", "partial_component", "school_location", True, "Matrículas e escolas observadas; não mede população residente ou permanência."),
        ("aee_school_offer", "10.b", "aee_oferta_escolas_elegiveis", "complementary", "partial_component", "school_location", True, "Oferta declarada por escola, sem denominador estudantil residente."),
        ("rural_school_distribution", "11.e", "not_materialized", "not_structured", "contextual_proxy", "rural_school_location", True, "Distribuição territorial escolar para organizar acompanhamento da EJA rural."),
        ("teacher_training_initial_years_tracking", "17.a", "adequacao_ai", "progress", "contextual_proxy", "school_location", False, "Referência contratual de formação docente; valores não foram rematerializados neste job."),
        ("teacher_training_final_years_tracking", "17.a", "adequacao_af", "progress", "contextual_proxy", "school_location", False, "Referência contratual de formação docente; valores não foram rematerializados neste job."),
        ("teacher_training_high_school_tracking", "17.a", "adequacao_em", "progress", "contextual_proxy", "school_location", False, "Referência contratual de formação docente; valores não foram rematerializados neste job."),
        ("teacher_postgraduate_tracking", "17.f", "pos_graduacao", "complementary", "contextual_proxy", "school_location", False, "Referência contratual de formação docente; valores não foram rematerializados neste job."),
    ]
    result = pd.DataFrame(
        [
            {
                "analysis_id": analysis,
                "goal_id": goal,
                "indicator_id": indicator,
                "mode": mode,
                "link_type": link,
                "monitoring_indicator": indicator,
                "period": "2010-2025 conforme análise",
                "source": "pne2026-goal-indicator-contract-v1.9.0_and_job5gb_panels",
                "territorial_lens": lens,
                "limitation": limitation,
                "adds_concrete_decision": decision,
                "contract_recalculated": False,
                "contract_changed": False,
            }
            for analysis, goal, indicator, mode, link, lens, decision, limitation in rows
        ]
    )
    periods = {
        "adult_fundamental_18_plus": "2010-2022",
        "adult_high_school_18_plus": "2010-2022",
        "eja_distribution_fundamental_2022": "2022",
        "eja_distribution_high_school_2022": "2022",
        "eja_historical_fundamental": "2014-2025",
        "eja_historical_high_school": "2014-2025",
        "eja_integrated_ept": "2014-2025",
        "vulnerability_context": "2024-12",
        "indigenous_education_observed": "2023-2025",
        "special_education_common_exclusive": "2014-2025",
        "aee_school_offer": "2014-2025",
        "rural_school_distribution": "2014-2025",
        "teacher_training_initial_years_tracking": "contract_2026_2036_no_values_materialized",
        "teacher_training_final_years_tracking": "contract_2026_2036_no_values_materialized",
        "teacher_training_high_school_tracking": "contract_2026_2036_no_values_materialized",
        "teacher_postgraduate_tracking": "contract_2026_2036_no_values_materialized",
    }
    result["period"] = result["analysis_id"].map(periods)
    if result["period"].isna().any():
        raise ValueError("Período ausente na matriz PNE/PME.")
    contract = _load_json(PNE_CONTRACT_PATH)
    relations = {
        (item["goalId"], item["indicatorId"], item["mode"])
        for item in contract["relations"]
    }
    for row in result[result["indicator_id"].ne("not_materialized")].itertuples(index=False):
        if (row.goal_id, row.indicator_id, row.mode) not in relations:
            raise ValueError(
                f"Vínculo PNE ausente do contrato vigente: {row.goal_id}/{row.indicator_id}/{row.mode}"
            )
    return result


def _criteria_row(
    analysis_id: str,
    classification: str,
    question: str,
    statuses: Sequence[str],
    evidence: Sequence[str],
) -> dict[str, Any]:
    if classification not in ALLOWED_CLASSIFICATIONS or len(statuses) != 12 or len(evidence) != 12:
        raise ValueError(f"Classificação C1-C12 inválida: {analysis_id}")
    row: dict[str, Any] = {
        "analysis_id": analysis_id,
        "substantive_question": question,
        "classification": classification,
        "score": None,
        "automatic_approval": False,
        "external_judgment_required": True,
    }
    for index, criterion in enumerate(CRITERIA, start=1):
        row[f"c{index}_meaning"] = CRITERIA[criterion]
        row[f"c{index}_status"] = statuses[index - 1]
        row[f"c{index}_evidence"] = evidence[index - 1]
    return row


def _build_opportunities(panels: Mapping[str, pd.DataFrame]) -> pd.DataFrame:
    common_supported = ["SUPPORTED"] * 12
    definitions = [
        (
            "A_ESCOLARIDADE_ADULTA_2010_2022",
            "READY_WITH_LIMITS",
            "Como as contagens cumulativas de conclusão adulta mudaram entre os Censos?",
            ["SUPPORTED", "SUPPORTED", "SUPPORTED", "SUPPORTED", "SUPPORTED", "PARTIAL", "PARTIAL", "SUPPORTED", "SUPPORTED", "SUPPORTED", "SUPPORTED", "SUPPORTED"],
            [
                "Mudança intercensitária informa o estoque educacional residente.",
                "Escolarização acumulada é processo plausível; não há atribuição causal.",
                "Universo residente de 18 anos ou mais.",
                "Lente de residência explícita.",
                "Censos 2010/2022 e componentes locais rastreados.",
                "Contagens comparáveis; denominador 18+ de 2010 ausente.",
                "497 municípios nas contagens; participações 2010 indisponíveis.",
                "Vale e RS somados por contagens compatíveis.",
                "Categorias cumulativas e derivadas rotuladas separadamente.",
                "Dez municípios e Nova Santa Rita presentes.",
                "Acrescenta leitura intercensitária ainda não materializada no Job 5F.",
                "Indicadores 11.b/11.c vinculados sem recálculo legal.",
            ],
        ),
        (
            "B_EJA_DISTRIBUICAO_2022",
            "READY_FOR_INTERNAL_VISUAL_PROTOTYPE",
            "Como público residente e matrículas localizadas se distribuem por etapa no Vale?",
            ["SUPPORTED", "SUPPORTED", "SUPPORTED", "SUPPORTED", "SUPPORTED", "PARTIAL", "SUPPORTED", "PARTIAL", "SUPPORTED", "SUPPORTED", "SUPPORTED", "SUPPORTED"],
            [
                "Contraste distributivo por etapa responde à pergunta municipal.",
                "Localização escolar pode redistribuir matrículas sem identificar residência.",
                "Públicos fundamental e médio permanecem distintos.",
                "Residência e localização da escola aparecem separadas.",
                "Artefato Job 2C congelado e aprovado com correção C9.",
                "Âncora 2022 comum; o total populacional do fundamental vem de fonte distinta da escolaridade adulta.",
                "22 linhas: dez municípios e Vale em duas etapas.",
                "Médio fecha com a escolaridade adulta; fundamental preserva diferença regional de fonte de 18.401 pessoas.",
                "Nenhum indicador por mil ou mensagem de atendimento.",
                "Nova Santa Rita preserva direções opostas por etapa.",
                "Acrescenta distribuição, não duplica o indicador legal.",
                "Vínculo parcial com 11.d e pergunta de acompanhamento explícita.",
            ],
        ),
        (
            "C_EJA_HISTORICA_2014_2025",
            "READY_WITH_LIMITS",
            "Como EJA fundamental e médio mudaram e contribuíram para a variação regional?",
            ["SUPPORTED", "SUPPORTED", "SUPPORTED", "SUPPORTED", "SUPPORTED", "SUPPORTED", "SUPPORTED", "SUPPORTED", "SUPPORTED", "SUPPORTED", "SUPPORTED", "PARTIAL"],
            [
                "Série por etapa informa volume e composição.",
                "Mudança e redistribuição são processos descritivos plausíveis.",
                "Matrículas localizadas, não pessoas residentes.",
                "Localização da escola explícita.",
                "Artefato Job 2C congelado, 2014-2025.",
                "Janela completa; metadado local não confirma quebras de definição.",
                "Dez municípios, Vale e RS, grão anual único.",
                "Total fecha exatamente como fundamental + médio.",
                "Não converte mudança em procura, acesso ou funcionamento institucional.",
                "Nova Santa Rita e contribuição municipal presentes.",
                "Acrescenta evolução temporal à distribuição de 2022.",
                "Acompanha 11.d apenas como componente descritivo.",
            ],
        ),
        (
            "D_EJA_INTEGRADA_EPT",
            "READY_WITH_LIMITS",
            "Qual é o espaço observado da EJA articulada à educação profissional?",
            ["SUPPORTED", "SUPPORTED", "SUPPORTED", "SUPPORTED", "SUPPORTED", "SUPPORTED", "SUPPORTED", "PARTIAL", "SUPPORTED", "SUPPORTED", "SUPPORTED", "SUPPORTED"],
            [
                "Matrículas integradas e modalidades respondem à articulação observada.",
                "Articulação EJA-EPT é processo substantivo; sem conclusão sobre escala.",
                "Matrículas escolares e modalidades explicitadas.",
                "Localização da escola explícita.",
                "Artefato Job 2C congelado e contrato PNE vigente.",
                "2014-2025 sem interpolação.",
                "Dez municípios, Vale e RS; zeros observados preservados.",
                "Modalidades fecham com o total integrado; 11 linhas auxiliares por dependência divergem e foram excluídas da análise.",
                "Zero local não vira conclusão isolada.",
                "Nova Santa Rita e Vale presentes.",
                "Acrescenta composição por modalidade.",
                "Vínculo direto com 12.c sem recálculo do indicador.",
            ],
        ),
        (
            "E_VULNERABILIDADE",
            "DESCRIPTIVE_CONTEXT_ONLY",
            "Que contexto cadastral agregado ajuda a formular perguntas de equidade?",
            ["SUPPORTED", "PARTIAL", "PARTIAL", "SUPPORTED", "SUPPORTED", "SUPPORTED", "SUPPORTED", "SUPPORTED", "SUPPORTED", "SUPPORTED", "PARTIAL", "PARTIAL"],
            [
                "Contagens cadastrais territoriais acrescentam contexto social.",
                "Campos de renda são contexto plausível, sem ligação individual.",
                "Famílias e pessoas cadastradas; escolaridade adulta ausente.",
                "Município declarado pela fonte; unidade preservada.",
                "MDS/SAGI local, dezembro de 2024, hashes por município.",
                "Âncora mensal comum 2024-12.",
                "Dez municípios e Vale; dados apenas agregados.",
                "Vale por soma dentro da mesma unidade.",
                "Sem microvinculação e sem identificar público EJA.",
                "Nova Santa Rita presente.",
                "Acrescenta contexto, mas não perfil educacional adulto.",
                "Apenas proxy contextual para equidade e busca ativa futura.",
            ],
        ),
        (
            "E2_EDUCACAO_INDIGENA",
            "READY_WITH_LIMITS",
            "Que fatos escolares indígenas observados no Vale precisam entrar no acompanhamento territorial?",
            ["SUPPORTED", "SUPPORTED", "PARTIAL", "SUPPORTED", "SUPPORTED", "SUPPORTED", "SUPPORTED", "SUPPORTED", "SUPPORTED", "SUPPORTED", "SUPPORTED", "PARTIAL"],
            [
                "Matrículas, estabelecimentos, turmas e docentes observados acrescentam um público específico.",
                "A organização escolar indígena é processo observável, sem atribuição causal.",
                "A fonte descreve oferta escolar; não contém denominador residente compatível.",
                "Localização da escola e rede total explícitas.",
                "Tabela local INEP educacao_indigena_municipal rastreada em transação somente leitura.",
                "Série comparável 2023-2025, sem interpolação.",
                "Dez municípios e Vale, quatro unidades e grão único.",
                "Vale recomposto somente por soma das contagens municipais compatíveis.",
                "Zeros observados não viram conclusão sobre acesso ou inexistência regional.",
                "Nova Santa Rita permanece com zeros observados; São Leopoldo concentra os valores positivos.",
                "Acrescenta público específico não materializado nas demais frentes.",
                "Vínculo parcial com 9.d; o indicador vigente não foi recalculado.",
            ],
        ),
        (
            "F_EDUCACAO_ESPECIAL_AEE",
            "READY_WITH_LIMITS",
            "Quais matrículas, classes e escolas com AEE precisam de acompanhamento territorial?",
            common_supported,
            [
                "Componentes observados informam continuidade e articulação.",
                "Oferta escolar é processo observável sem estimar prevalência.",
                "Matrículas e escolas, não população residente.",
                "Localização da escola e rede total.",
                "Censo Escolar normalizado e materializador validado existente.",
                "2014-2025 com disponibilidade por campo.",
                "497 municípios; dez, Vale, RS e grãos únicos.",
                "Agregação por soma/contagem de escolas com estados explícitos.",
                "Sem taxa de população residente ou atribuição por dependência.",
                "Nova Santa Rita presente.",
                "Acrescenta classes comuns/exclusivas, etapas e AEE.",
                "Vínculos 10.a/10.b sem criar denominador estudantil.",
            ],
        ),
        (
            "G_EDUCACAO_RURAL_TERRITORIO",
            "READY_WITH_LIMITS",
            "Como escolas, matrículas e turmas rurais se distribuem no território?",
            common_supported,
            [
                "Distribuição escolar rural informa organização territorial.",
                "Localização da escola é mecanismo contextual, não residência.",
                "Escolas, matrículas e turmas preservadas por etapa.",
                "Lente rural da escola explícita.",
                "Censo Escolar local por escola.",
                "2014-2025 com regra explícita de situação da escola.",
                "497 municípios, grão ano x escola único.",
                "Vale e RS por somas de contagens escolares.",
                "Sem inferir deslocamento, residência ou encerramento.",
                "Nova Santa Rita presente inclusive quando valor é zero.",
                "Acrescenta contexto territorial por etapa.",
                "Proxy contextual para 11.e, sem indicador legal recalculado.",
            ],
        ),
        (
            "H_VINCULOS_PNE_PME",
            "READY_WITH_LIMITS",
            "Quais vínculos vigentes organizam o acompanhamento sem alterar contratos?",
            common_supported,
            [
                "Matriz liga cada análise a decisão de acompanhamento.",
                "Vínculos distinguem direto, componente e proxy.",
                "Universo é herdado e explicitado em cada painel.",
                "Lentes são herdadas sem fusão.",
                "Contrato v1.9.0 e política vigente lidos localmente.",
                "Período registrado por análise.",
                "Recorte dirigido sem republicar diagnósticos.",
                "Nenhuma fórmula legal foi executada ou alterada.",
                "Limitações contratuais preservadas.",
                "Indicadores de Nova Santa Rita são referências, não recálculos.",
                "Acrescenta governança de acompanhamento.",
                "Decisão concreta registrada por vínculo.",
            ],
        ),
    ]
    rows = [_criteria_row(analysis, classification, question, statuses, evidence) for analysis, classification, question, statuses, evidence in definitions]
    result = pd.DataFrame(rows)
    sources = {
        "A_ESCOLARIDADE_ADULTA_2010_2022": "IBGE_Censo_Demografico_2010_2022_local_materialization",
        "B_EJA_DISTRIBUICAO_2022": "Job2C_eja_demanda_oferta_2022_frozen",
        "C_EJA_HISTORICA_2014_2025": "Job2C_eja_integrada_historica_frozen",
        "D_EJA_INTEGRADA_EPT": "Job2C_eja_integrada_historica_frozen",
        "E_VULNERABILIDADE": "MDS_SAGI_MI_Social_local_raw_snapshot",
        "E2_EDUCACAO_INDIGENA": "INEP_educacao_indigena_municipal",
        "F_EDUCACAO_ESPECIAL_AEE": "INEP_Censo_Escolar_censo_educacao_especial_escolas",
        "G_EDUCACAO_RURAL_TERRITORIO": "INEP_Censo_Escolar_censo_escolas",
        "H_VINCULOS_PNE_PME": "pne2026_goal_indicator_contract_v1.9.0",
    }
    lenses = {
        "A_ESCOLARIDADE_ADULTA_2010_2022": "resident_population",
        "B_EJA_DISTRIBUICAO_2022": "resident_population_vs_school_location",
        "C_EJA_HISTORICA_2014_2025": "school_location",
        "D_EJA_INTEGRADA_EPT": "school_location",
        "E_VULNERABILIDADE": "registered_residence_or_source_declared_municipality",
        "E2_EDUCACAO_INDIGENA": "school_location",
        "F_EDUCACAO_ESPECIAL_AEE": "school_location",
        "G_EDUCACAO_RURAL_TERRITORIO": "rural_school_location",
        "H_VINCULOS_PNE_PME": "contractual_tracking_multiple_lenses",
    }
    result["source"] = result["analysis_id"].map(sources)
    result["territorial_lens"] = result["analysis_id"].map(lenses)
    return result


def _records(panel: pd.DataFrame, mask: pd.Series, columns: Sequence[str]) -> list[dict[str, Any]]:
    frame = panel.loc[mask, list(columns)].copy()
    return json.loads(frame.to_json(orient="records", force_ascii=False))


def _build_nsr_dossier(panels: Mapping[str, pd.DataFrame]) -> dict[str, Any]:
    adult = panels["adult"]
    eja_dist = panels["eja_distribution"]
    eja_hist = panels["eja_history"]
    eja_ept = panels["eja_ept"]
    vulnerability = panels["vulnerability"]
    special = panels["special"]
    rural = panels["rural"]
    links = panels["pne_links"]
    groups = [
        {
            "id": "adult_schooling_2010_2022",
            "classification": "READY_WITH_LIMITS",
            "municipalFacts": _records(adult, adult["municipality_ibge_code"].eq(NOVA_SANTA_RITA_ID), ["year", "schooling_category", "count_value", "share_percent", "absolute_change_2010_2022"]),
            "compatibleValeContrast": _records(adult, adult["entity_scope"].eq("region"), ["year", "schooling_category", "count_value", "share_percent", "absolute_change_2010_2022"]),
            "compatibleRSContrast": _records(adult, adult["entity_scope"].eq("state"), ["year", "schooling_category", "count_value", "share_percent", "absolute_change_2010_2022"]),
            "period": "2010-2022",
            "source": "IBGE Censos Demográficos, materialização local",
            "lens": "resident_population",
            "monitoringIndicator": ["fundamental_concluido_18_mais", "medio_concluido_18_mais"],
            "planningQuestion": "Quais grupos de escolaridade adulta devem orientar o acompanhamento intercensitário, respeitada a lacuna do denominador 2010?",
            "prohibitedInferences": ["causal_attribution", "annual_interpolation", "eja_public_identity"],
            "potentialVisual": "grouped_counts_with_missing_share_marker",
        },
        {
            "id": "eja_distribution_2022",
            "classification": "READY_FOR_INTERNAL_VISUAL_PROTOTYPE",
            "municipalFacts": _records(eja_dist, eja_dist["municipality_ibge_code"].eq(NOVA_SANTA_RITA_ID), ["stage", "resident_adult_public", "school_location_eja_enrollments", "share_of_regional_public_percent", "share_of_regional_enrollments_percent", "distribution_difference_percentage_points", "distribution_direction", "resident_public_compatibility_with_adult_panel"]),
            "compatibleValeContrast": _records(eja_dist, eja_dist["entity_scope"].eq("region"), ["stage", "resident_adult_public", "school_location_eja_enrollments"]),
            "compatibleRSContrast": [],
            "rsContrastStatus": "SOURCE_UNAVAILABLE_IN_FROZEN_DISTRIBUTION_ARTIFACT",
            "period": "2022",
            "source": "Job 2C congelado",
            "lens": "resident_population_vs_school_location",
            "monitoringIndicator": ["eja_atendimento_18_mais"],
            "planningQuestion": "Como acompanhar separadamente as distribuições do fundamental e do médio?",
            "prohibitedInferences": ["served_public", "institutional_adequacy", "unobserved_barrier"],
            "potentialVisual": "two_stage_distribution_balance",
        },
        {
            "id": "eja_history",
            "classification": "READY_WITH_LIMITS",
            "municipalFacts": _records(eja_hist, eja_hist["municipality_ibge_code"].eq(NOVA_SANTA_RITA_ID) & eja_hist["year"].isin([2014, 2025]), ["year", "stage", "eja_enrollments", "absolute_change_2014_2025", "stage_composition_percent"]),
            "compatibleValeContrast": _records(eja_hist, eja_hist["entity_scope"].eq("region") & eja_hist["year"].isin([2014, 2025]), ["year", "stage", "eja_enrollments", "absolute_change_2014_2025", "stage_composition_percent"]),
            "compatibleRSContrast": _records(eja_hist, eja_hist["entity_scope"].eq("state") & eja_hist["year"].isin([2014, 2025]), ["year", "stage", "eja_enrollments", "absolute_change_2014_2025", "stage_composition_percent"]),
            "period": "2014-2025",
            "source": "Job 2C congelado",
            "lens": "school_location",
            "monitoringIndicator": ["eja_atendimento_18_mais"],
            "planningQuestion": "Quais mudanças de volume e composição por etapa requerem acompanhamento?",
            "prohibitedInferences": ["demand_change", "access_change", "institution_opening_closure"],
            "potentialVisual": "stage_lines_complete_window",
        },
        {
            "id": "eja_integrated_ept",
            "classification": "READY_WITH_LIMITS",
            "municipalFacts": _records(eja_ept, eja_ept["municipality_ibge_code"].eq(NOVA_SANTA_RITA_ID) & eja_ept["year"].isin([2014, 2022, 2025]), ["year", "modality", "integrated_eja_enrollments", "share_of_eja_percent", "value_status"]),
            "compatibleValeContrast": _records(eja_ept, eja_ept["entity_scope"].eq("region") & eja_ept["year"].isin([2014, 2022, 2025]), ["year", "modality", "integrated_eja_enrollments", "share_of_eja_percent"]),
            "compatibleRSContrast": _records(eja_ept, eja_ept["entity_scope"].eq("state") & eja_ept["year"].isin([2014, 2022, 2025]), ["year", "modality", "integrated_eja_enrollments", "share_of_eja_percent"]),
            "period": "2014-2025",
            "source": "Job 2C congelado",
            "lens": "school_location",
            "monitoringIndicator": ["eja_integrada_educacao_profissional_percentual"],
            "planningQuestion": "Que articulações entre EJA e educação profissional merecem acompanhamento regional?",
            "prohibitedInferences": ["scale_adequacy", "expansion_need", "local_access_absence"],
            "potentialVisual": "modality_small_multiples_with_explicit_zero",
        },
        {
            "id": "vulnerability",
            "classification": "DESCRIPTIVE_CONTEXT_ONLY",
            "municipalFacts": _records(vulnerability, vulnerability["municipality_ibge_code"].eq(NOVA_SANTA_RITA_ID) & vulnerability["context_domain"].eq("registered_vulnerability_context"), ["context_domain", "reference_period", "metric", "unit_of_observation", "value", "value_status"]),
            "compatibleValeContrast": _records(vulnerability, vulnerability["entity_scope"].eq("region") & vulnerability["context_domain"].eq("registered_vulnerability_context"), ["context_domain", "reference_period", "metric", "unit_of_observation", "value", "value_status"]),
            "specificPublicFacts": _records(vulnerability, vulnerability["municipality_ibge_code"].eq(NOVA_SANTA_RITA_ID) & vulnerability["context_domain"].eq("indigenous_education_specific_public"), ["context_domain", "reference_period", "metric", "unit_of_observation", "value", "value_status"]),
            "specificPublicValeContrast": _records(vulnerability, vulnerability["entity_scope"].eq("region") & vulnerability["context_domain"].eq("indigenous_education_specific_public"), ["context_domain", "reference_period", "metric", "unit_of_observation", "value", "value_status"]),
            "compatibleRSContrast": [],
            "rsContrastStatus": "SOURCE_NOT_MATERIALIZED_FOR_STATE_IN_THIS_JOB",
            "period": ["2024-12", "2023-2025"],
            "source": ["MDS/SAGI MI Social, snapshot local", "INEP educacao_indigena_municipal"],
            "lens": ["registered_residence_or_source_declared_municipality", "school_location"],
            "monitoringIndicator": ["not_materialized", "educacao_indigena_cobertura_estimada_4_17"],
            "planningQuestion": "Que contexto agregado e que públicos específicos exigem acompanhamento de equidade sem fundir cadastro, residência e oferta escolar?",
            "prohibitedInferences": ["cadunico_equals_eja_public", "micro_linkage", "student_identity", "indigenous_school_enrollment_equals_resident_public"],
            "potentialVisual": "context_metric_groups_by_unit",
        },
        {
            "id": "special_education_aee",
            "classification": "READY_WITH_LIMITS",
            "municipalFacts": _records(special, special["municipality_ibge_code"].eq(NOVA_SANTA_RITA_ID) & special["year"].eq(2025), ["year", "metric", "stage", "value", "value_status"]),
            "compatibleValeContrast": _records(special, special["entity_scope"].eq("region") & special["year"].eq(2025), ["year", "metric", "stage", "value", "value_status"]),
            "compatibleRSContrast": _records(special, special["entity_scope"].eq("state") & special["year"].eq(2025), ["year", "metric", "stage", "value", "value_status"]),
            "period": "2014-2025",
            "source": "INEP Censo Escolar normalizado",
            "lens": "school_location",
            "monitoringIndicator": ["aee_oferta_escolas_elegiveis"],
            "planningQuestion": "Como acompanhar continuidade, inclusão, articulação e acessibilidade entre etapas?",
            "prohibitedInferences": ["resident_prevalence", "student_coverage", "dependency_responsibility"],
            "potentialVisual": "special_components_and_aee_schools",
        },
        {
            "id": "rural_education",
            "classification": "READY_WITH_LIMITS",
            "municipalFacts": _records(rural, rural["municipality_ibge_code"].eq(NOVA_SANTA_RITA_ID) & rural["year"].eq(2025), ["year", "stage", "metric", "value", "value_status"]),
            "compatibleValeContrast": _records(rural, rural["entity_scope"].eq("region") & rural["year"].eq(2025), ["year", "stage", "metric", "value", "value_status"]),
            "compatibleRSContrast": _records(rural, rural["entity_scope"].eq("state") & rural["year"].eq(2025), ["year", "stage", "metric", "value", "value_status"]),
            "period": "2014-2025",
            "source": "INEP Censo Escolar por escola",
            "lens": "rural_school_location",
            "monitoringIndicator": ["not_materialized"],
            "planningQuestion": "Como a distribuição escolar rural por etapa deve entrar no acompanhamento territorial?",
            "prohibitedInferences": ["distance", "travel_time", "student_residence", "school_closure"],
            "potentialVisual": "rural_stage_distribution_lines",
        },
        {
            "id": "pne_pme_links",
            "classification": "READY_WITH_LIMITS",
            "municipalFacts": json.loads(links.to_json(orient="records", force_ascii=False)),
            "compatibleValeContrast": [],
            "compatibleRSContrast": [],
            "period": "current_contract_2026_2036",
            "source": "PNE 2026 goal-indicator contract v1.9.0",
            "lens": "contractual_tracking",
            "monitoringIndicator": sorted(set(links["indicator_id"])),
            "planningQuestion": "Quais indicadores organizam o acompanhamento sem alterar metas, fórmulas ou status?",
            "prohibitedInferences": ["legal_indicator_recalculation", "contract_change", "diagnostic_republication"],
            "potentialVisual": "goal_indicator_link_matrix",
        },
    ]
    return {
        "schemaVersion": "nova-santa-rita-job5gb-v1",
        "municipalityIbgeCode": NOVA_SANTA_RITA_ID,
        "municipalityName": "Nova Santa Rita",
        "groupCount": len(groups),
        "groups": groups,
        "networkScope": "total_all_dependencies",
        "administrativeDependencyIsAnalyticDimension": False,
        "administrativeDependencyIsQADimension": True,
        "publicNarrativeProduced": False,
    }


def _limitations() -> dict[str, Any]:
    return {
        "schemaVersion": "job5gb-limitations-v1",
        "global": [
            "Universos de residência, cadastro e localização escolar não identificam as mesmas pessoas.",
            "Dependência administrativa foi usada somente para QA de fechamento e não integra a análise.",
            "Nenhum dado publicado ou contrato legal foi alterado.",
        ],
        "fronts": {
            "adult_schooling": ["Denominador residente 18+ de 2010 ausente na materialização local; participações e diferenças em pontos percentuais intercensitárias ficam indisponíveis."],
            "eja_distribution": [
                "Distribuição territorial não identifica residência dos matriculados nem mede relação individual entre públicos.",
                "No fundamental, o público congelado do Job 2C usa a estimativa anual public.populacao_idade para o total 18+ e diverge em 18.401 pessoas no Vale do total censitário SIDRA 10061 usado no painel adulto; no médio, a diferença de contagens cumulativas fecha exatamente.",
            ],
            "eja_history": ["Metadados locais não confirmam ou descartam quebras de definição; mudanças abruptas permanecem questões de QA."],
            "eja_integrated_ept": [
                "Zero observado local não prova inexistência de alternativa regional ou necessidade de nova oferta.",
                "Em 11 linhas de 2016-2018, as colunas auxiliares pública/privada do artefato congelado não recompõem o total integrado; elas permanecem somente em QA e foram excluídas da análise.",
            ],
            "vulnerability": ["Fonte local não traz escolaridade declarada nem faixas adultas detalhadas; uso restrito a contexto cadastral agregado."],
            "indigenous_education": ["A série 2023-2025 descreve fatos na localização escolar; não foi combinada com população indígena residente e não recompõe o indicador contratual."],
            "special_aee": ["Matrícula não mede prevalência residente; AEE é observado como oferta escolar, sem denominador residente compatível."],
            "rural": ["Localização rural da escola não informa residência, distância ou deslocamento dos estudantes."],
            "pne_pme": ["Vínculos organizam acompanhamento; indicadores legais não foram recalculados."],
        },
        "vulnerabilitySourceAudit": {
            "source": "MDS/SAGI MI Social local raw snapshot",
            "referencePeriod": "2024-12",
            "municipalityCount": 10,
            "unitOfObservation": ["families", "people"],
            "familyAndPersonUnitsMixed": False,
            "adultAgeBandsAvailable": False,
            "availableAgeBand": "0_15_only",
            "declaredSchoolingAvailable": False,
            "individualRecordsPresent": False,
            "duplicateIndividualsEvaluable": False,
            "familyDefinitionDocumentedInLocalPayload": False,
            "updateFieldAvailable": True,
            "microLinkagePerformed": False,
        },
        "indigenousEducationSourceAudit": {
            "source": "public.educacao_indigena_municipal",
            "period": "2023-2025",
            "municipalityCount": 10,
            "segment": "total",
            "comparabilityGroup": "comparavel_2023_2025",
            "units": ["enrollments", "schools", "classes", "teachers"],
            "lens": "school_location",
            "networkScope": "total_all_dependencies",
            "residentDenominatorCombined": False,
            "legalIndicatorRecalculated": False,
            "positiveMunicipality": "4318705",
            "novaSantaRitaZerosAreObserved": True,
        },
        "specialSourceAudit": {
            "used": "public.censo_educacao_especial_escolas",
            "grain": "year_x_school",
            "lens": "school_location",
            "aeeUsedAs": "schools_declaring_aee_offer_and_resource_room",
            "excludedFromAnalysis": "public.atendimento_educacional_especializado.quantidade_aee_due_to_ambiguous_local_measure_definition",
            "residentDenominatorUsed": False,
        },
        "ruralSourceAudit": {
            "used": "public.censo_escolas",
            "grain": "year_x_school",
            "schoolLocation": "rural",
            "operatingStatusRule": "situacao_funcionamento_1_or_null_for_legacy_years",
            "residentRuralPopulationCombined": False,
        },
        "excluded": ["Job 5G-C", "Job 5H", "Job 6", "frontend", "public narrative", "publication"],
    }


def _section_map(opportunities: pd.DataFrame) -> str:
    lines = [
        "# MAPA DE SEÇÕES POTENCIAIS — JOB 5G-B V1",
        "",
        "> Artefato interno para julgamento externo. Não é narrativa pública nem especificação de interface.",
        "",
        "Rede educacional: `total_all_dependencies`. Dependência administrativa: somente QA.",
        "",
    ]
    for row in opportunities.itertuples(index=False):
        lines.extend(
            [
                f"## {row.analysis_id}",
                "",
                f"- Estado: `{row.classification}`",
                f"- Pergunta: {row.substantive_question}",
                f"- Evidência C9: {row.c9_evidence}",
                f"- Julgamento externo obrigatório: `{str(row.external_judgment_required).lower()}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Guardas de composição",
            "",
            "- EJA fundamental e médio permanecem separados.",
            "- Residência, cadastro e localização escolar permanecem em lentes distintas.",
            "- Zeros observados não são convertidos em ausência ou conclusão institucional.",
            "- Nenhum indicador por mil integra o envelope visual.",
            "- Não iniciar Job 5G-C, Job 5H ou Job 6.",
            "",
        ]
    )
    return "\n".join(lines)


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def _promote_package(staging: Path, target: Path) -> str:
    """Promove o lote com rollback; o manifesto é o último marcador gravado."""

    if target.exists() and directory_content_digest(staging) == directory_content_digest(target):
        shutil.rmtree(staging)
        return "unchanged"
    target.parent.mkdir(parents=True, exist_ok=True)
    backup = target.parent / f".{target.name}.backup"
    if backup.exists():
        raise FileExistsError(f"Backup residual impede promoção segura: {backup}")
    try:
        if target.exists():
            os.replace(target, backup)
        target.mkdir()
        files = sorted(path for path in staging.rglob("*") if path.is_file())
        files.sort(
            key=lambda path: (
                path.name == OUTPUT_FILES[-1],
                path.relative_to(staging).as_posix(),
            )
        )
        for source_path in files:
            relative = source_path.relative_to(staging)
            target_path = target / relative
            target_path.parent.mkdir(parents=True, exist_ok=True)
            partial = target_path.with_name(f".{target_path.name}.partial")
            shutil.copy2(source_path, partial)
            os.replace(partial, target_path)
        if directory_content_digest(target) != directory_content_digest(staging):
            raise RuntimeError("Destino promovido diverge do staging validado.")
        if backup.exists():
            shutil.rmtree(backup)
        shutil.rmtree(staging)
        return "replaced"
    except Exception:
        if target.exists():
            shutil.rmtree(target, ignore_errors=True)
        if backup.exists():
            os.replace(backup, target)
        raise


def _artifact(path: Path, root: Path, frame: pd.DataFrame | None = None) -> dict[str, Any]:
    return {
        "path": path.relative_to(root).as_posix(),
        "byteSize": path.stat().st_size,
        "sha256": sha256_file(path),
        "rowCount": None if frame is None else int(len(frame)),
        "columns": None if frame is None else list(frame.columns),
    }


def _validate_frames(panels: Mapping[str, pd.DataFrame], region_codes: Sequence[str]) -> dict[str, Any]:
    checks: dict[str, Any] = {}
    for name, panel in panels.items():
        if "source" not in panel or "territorial_lens" not in panel:
            raise ValueError(f"{name}: fonte ou lente ausente do schema")
        if panel["source"].isna().any() or panel["territorial_lens"].isna().any():
            raise ValueError(f"{name}: linha sem fonte ou lente")
        if name in {"pne_links", "opportunities"}:
            checks[name] = {"rows": int(len(panel)), "columns": int(len(panel.columns))}
            continue
        if "value_status" in panel:
            states = set(panel["value_status"].dropna())
            if not states.issubset(ALLOWED_VALUE_STATES):
                raise ValueError(f"{name}: estados inválidos {states-ALLOWED_VALUE_STATES}")
        if "municipality_ibge_code" in panel:
            codes = set(panel["municipality_ibge_code"].dropna().astype(str))
            invalid = [code for code in codes if re.fullmatch(r"\d{7}", code) is None]
            if invalid:
                raise ValueError(f"{name}: códigos IBGE inválidos {invalid[:5]}")
            if name != "adult" and not set(region_codes).issubset(codes):
                raise ValueError(f"{name}: universo municipal incompleto")
        if "network_scope" in panel:
            invalid_network = set(panel["network_scope"].dropna()) - {
                "total_all_dependencies",
                "not_applicable",
            }
            if invalid_network:
                raise ValueError(f"{name}: rede inválida {invalid_network}")
            educational_rows = panel["network_scope"].ne("not_applicable")
            if educational_rows.any() and not panel.loc[
                educational_rows, "network_scope"
            ].eq("total_all_dependencies").all():
                raise ValueError(f"{name}: evidência educacional sem rede total")
        if "administrative_dependency_is_analytic_dimension" in panel and panel["administrative_dependency_is_analytic_dimension"].astype(bool).any():
            raise ValueError(f"{name}: dependência administrativa virou dimensão analítica")
        checks[name] = {"rows": int(len(panel)), "columns": int(len(panel.columns))}
    distribution = panels["eja_distribution"]
    if "matriculas_por_mil" in distribution.columns:
        raise ValueError("Indicador por mil entrou no envelope do Job 5G-B.")
    opportunities = panels["opportunities"]
    if not set(opportunities["classification"]).issubset(ALLOWED_CLASSIFICATIONS):
        raise ValueError("Classificação de oportunidade inválida.")
    if opportunities["score"].notna().any() or opportunities["automatic_approval"].astype(bool).any():
        raise ValueError("C1-C12 não podem gerar score ou aprovação automática.")
    for index in range(1, 13):
        if set(opportunities[f"c{index}_status"]) - {"SUPPORTED", "PARTIAL", "NOT_SUPPORTED", "NOT_EVALUABLE"}:
            raise ValueError(f"C{index} contém estado inválido.")
    adult = panels["adult"]
    adult_public = adult[
        adult["year"].eq(2022)
        & adult["schooling_category"].isin(
            ["without_fundamental_completed", "fundamental_completed_without_high_school"]
        )
    ].copy()
    adult_public["stage"] = adult_public["schooling_category"].map(
        {
            "without_fundamental_completed": "fundamental",
            "fundamental_completed_without_high_school": "high_school",
        }
    )
    adult_public["entity_key"] = adult_public["municipality_ibge_code"].fillna("").astype(str)
    distribution_for_closure = distribution.copy()
    distribution_for_closure["entity_key"] = distribution_for_closure[
        "municipality_ibge_code"
    ].fillna("").astype(str)
    public_closure = distribution_for_closure.merge(
        adult_public[
            ["entity_scope", "entity_key", "stage", "count_value"]
        ],
        on=["entity_scope", "entity_key", "stage"],
        how="left",
        validate="one_to_one",
    )
    public_closure["public_residual"] = (
        pd.to_numeric(public_closure["resident_adult_public"], errors="raise")
        - pd.to_numeric(public_closure["count_value"], errors="raise")
    )
    fundamental_public_residual = public_closure.loc[
        public_closure["stage"].eq("fundamental"), "public_residual"
    ]
    high_school_public_residual = public_closure.loc[
        public_closure["stage"].eq("high_school"), "public_residual"
    ]
    if high_school_public_residual.abs().max() != 0:
        raise ValueError("Público residente médio da EJA 2022 diverge da contagem adulta recomposta.")
    fundamental_region_residual = public_closure.loc[
        public_closure["stage"].eq("fundamental")
        & public_closure["entity_scope"].eq("region"),
        "public_residual",
    ]
    if len(fundamental_region_residual) != 1:
        raise ValueError("Residual regional do público fundamental não é único.")
    history_2022 = panels["eja_history"]
    history_2022 = history_2022[
        history_2022["year"].eq(2022)
        & history_2022["stage"].isin(["fundamental", "high_school"])
        & history_2022["entity_scope"].isin(["municipality", "region"])
    ].copy()
    history_2022["entity_key"] = history_2022["municipality_ibge_code"].fillna("").astype(str)
    enrollment_closure = distribution_for_closure.merge(
        history_2022[
            ["entity_scope", "entity_key", "stage", "eja_enrollments"]
        ],
        on=["entity_scope", "entity_key", "stage"],
        how="left",
        validate="one_to_one",
    )
    enrollment_residual = (
        pd.to_numeric(enrollment_closure["school_location_eja_enrollments"], errors="raise")
        - pd.to_numeric(enrollment_closure["eja_enrollments"], errors="raise")
    ).abs()
    if enrollment_residual.max() != 0:
        raise ValueError("Matrículas EJA 2022 divergem da série histórica.")
    special = panels["special"]
    observed_special = special[
        special["metric"].isin(
            ["special_enrollments", "common_class_enrollments", "exclusive_class_enrollments"]
        )
        & special["value_status"].eq("observed")
    ].copy()
    observed_special["entity_key"] = observed_special["municipality_ibge_code"].fillna("").astype(str)
    special_pivot = observed_special.pivot_table(
        index=["entity_scope", "entity_key", "year"],
        columns="metric",
        values="value",
        aggfunc="first",
    ).dropna()
    special_residual = (
        special_pivot["special_enrollments"]
        - special_pivot["common_class_enrollments"]
        - special_pivot["exclusive_class_enrollments"]
    ).abs()
    if not special_residual.empty and special_residual.max() != 0:
        raise ValueError("Matrículas especiais não fecham entre classes comuns e exclusivas.")
    vulnerability = panels["vulnerability"]
    indigenous = vulnerability[
        vulnerability["context_domain"].eq("indigenous_education_specific_public")
    ].copy()
    indigenous_municipal = indigenous[indigenous["entity_scope"].eq("municipality")]
    indigenous_region = indigenous[indigenous["entity_scope"].eq("region")]
    if len(indigenous_municipal) != 120 or len(indigenous_region) != 12:
        raise ValueError("Painel indígena não preserva 120 linhas municipais e 12 regionais.")
    if set(indigenous_municipal["municipality_ibge_code"].astype(str)) != set(region_codes):
        raise ValueError("Painel indígena não preserva os dez municípios.")
    indigenous_nsr = indigenous_municipal[
        indigenous_municipal["municipality_ibge_code"].eq(NOVA_SANTA_RITA_ID)
    ]
    if len(indigenous_nsr) != 12 or not indigenous_nsr["value"].eq(0).all() or not indigenous_nsr["value_status"].eq("observed").all():
        raise ValueError("Zeros observados indígenas de Nova Santa Rita não foram preservados.")
    for record in indigenous_region.itertuples(index=False):
        municipal_sum = indigenous_municipal[
            indigenous_municipal["reference_period"].eq(record.reference_period)
            & indigenous_municipal["metric"].eq(record.metric)
        ]["value"].sum()
        if float(record.value) != float(municipal_sum):
            raise ValueError("Agregação indígena do Vale não fecha por contagens municipais.")
    positive_indigenous_codes = sorted(
        set(
            indigenous_municipal.loc[
                pd.to_numeric(indigenous_municipal["value"], errors="raise").gt(0),
                "municipality_ibge_code",
            ].astype(str)
        )
    )
    checks["crossPanelClosure"] = {
        "ejaResidentPublicHighSchool2022MaximumResidual": float(
            high_school_public_residual.abs().max()
        ),
        "ejaResidentPublicFundamental2022RegionalResidual": float(
            fundamental_region_residual.iloc[0]
        ),
        "ejaResidentPublicFundamental2022MaximumMunicipalResidual": float(
            public_closure.loc[
                public_closure["stage"].eq("fundamental")
                & public_closure["entity_scope"].eq("municipality"),
                "public_residual",
            ].abs().max()
        ),
        "ejaResidentPublicFundamentalClosureStatus": "DEFINITION_INCOMPATIBLE_POPULATION_TOTAL_SOURCE",
        "ejaEnrollments2022MaximumResidual": float(enrollment_residual.max()),
        "specialCommonExclusiveMaximumResidual": (
            None if special_residual.empty else float(special_residual.max())
        ),
    }
    checks["indigenousEducation"] = {
        "municipalRows": int(len(indigenous_municipal)),
        "regionalRows": int(len(indigenous_region)),
        "periods": sorted(indigenous["reference_period"].unique().tolist()),
        "positiveMunicipalityCodes": positive_indigenous_codes,
        "novaSantaRitaObservedZeroRows": int(len(indigenous_nsr)),
        "regionalAggregationMaximumResidual": 0.0,
        "residentDenominatorCombined": False,
    }
    checks["novaSantaRitaDistributionDirections"] = {
        row.stage: row.distribution_direction
        for row in distribution[distribution["municipality_ibge_code"].eq(NOVA_SANTA_RITA_ID)].itertuples()
    }
    checks["municipalityUniverse"] = {
        "expectedMunicipalityCount": 10,
        "observedMunicipalityCount": len(region_codes),
        "novaSantaRitaPresent": NOVA_SANTA_RITA_ID in set(region_codes),
        "ibgeIdentity": "text_7_digits",
    }
    return checks


def materialize(output_root: Path = DEFAULT_OUTPUT_ROOT) -> dict[str, Any]:
    output_root = output_root.resolve()
    assert_outside_public_data(output_root, REPO_ROOT)
    if (REPO_ROOT / "src").resolve() in output_root.parents or output_root == (REPO_ROOT / "src").resolve():
        raise ValueError("O staging do Job 5G-B não pode atingir o frontend.")
    load_dotenv(DATA_PIPELINE_DIR / ".env")
    region_codes, region_names, state_codes, _ = _load_scope()
    previous = _verify_previous_packages()
    if _load_json(PNE_CONTRACT_PATH).get("contractVersion") != "1.9.0":
        raise ValueError("Contrato PNE vigente inesperado.")
    _load_json(PNE_POLICY_PATH)
    with _read_only_connection() as connection:
        sources = _query_sources(connection, state_codes, region_codes)
    source_digests = {
        "adultDatabaseSnapshot": _frame_digest(sources["adult"], ["year", "municipality_ibge_code"]),
        "specialDatabaseSnapshot": _frame_digest(sources["special"], ["ano", "id_municipio", "cod_escola"]),
        "ruralDatabaseSnapshot": _frame_digest(sources["rural"], ["year", "municipality_ibge_code", "school_code"]),
        "indigenousEducationDatabaseSnapshot": _frame_digest(
            sources["indigenous"],
            ["year", "municipality_ibge_code", "unit_of_observation"],
        ),
        "ejaDistributionJob2C": sha256_file(JOB2_ROOT / "eja_demanda_oferta_2022.csv.gz"),
        "ejaHistoryJob2C": sha256_file(JOB2_ROOT / "eja_integrada_historica.csv.gz"),
        "pneContract": sha256_file(PNE_CONTRACT_PATH),
        "pnePresentationPolicy": sha256_file(PNE_POLICY_PATH),
    }
    historical_source = _historical_source(region_codes)
    vulnerability, cadunico_hashes = _build_vulnerability(region_codes, region_names)
    indigenous_context = _build_indigenous_context(
        sources["indigenous"], region_codes, region_names
    )
    vulnerability = _stable(
        pd.concat([vulnerability, indigenous_context], ignore_index=True),
        ["context_domain", "entity_scope", "municipality_ibge_code", "reference_period", "metric"],
    )
    panels: dict[str, pd.DataFrame] = {
        "adult": _build_adult_panel(sources["adult"], region_codes, region_names, state_codes),
        "eja_distribution": _build_eja_distribution(region_codes),
        "eja_history": _build_eja_historical(historical_source),
        "eja_ept": _build_eja_integrated(historical_source),
        "vulnerability": vulnerability,
        "special": _build_special_panel(sources["special"], region_codes, region_names, state_codes),
        "rural": _build_rural_panel(sources["rural"], region_codes, region_names, state_codes),
        "pne_links": _build_pne_links(),
    }
    panels["opportunities"] = _build_opportunities(panels)
    qa = _validate_frames(panels, region_codes)
    qa["ejaIntegratedAdministrativeDependencyClosure"] = {
        "mismatchCount": historical_source.attrs["administrative_dependency_closure_mismatch_count"],
        "mismatchYears": historical_source.attrs["administrative_dependency_closure_mismatch_years"],
        "analyticUse": False,
        "networkTotalSource": "mat_eja_integrada_educacao_profissional",
    }
    dictionary = _adult_dictionary()
    dossier = _build_nsr_dossier(panels)
    limitations = _limitations()
    review_package = {
        "schemaVersion": "job5gb-external-review-v1",
        "jobId": "JOB_5GB",
        "finalState": FINAL_STATE,
        "score": None,
        "automaticApproval": False,
        "externalJudgmentRequired": True,
        "externalReviewer": "GPT-5.6 Pro",
        "canonicalInputs": {
            "JOB_5GAR_EXECUTION": "APPROVED",
            "JOB_5GA_REQUIRED_CORRECTIONS": "CLOSED",
            "FRONT_E_PRESSAO_MECANICA": "READY_FOR_INTERNAL_VISUAL_PROTOTYPE_WITH_COMPLETE_WINDOW_AND_MIXED_LENS_GUARDRAILS",
            "H2_TRAJETORIA_MUNICIPAL_V2": "NOT_EVALUABLE_DUE_TO_DATA_OR_QA_LIMIT_FROZEN_UNCHANGED",
            "JOB_5H": "NOT_AUTHORIZED",
            "JOB_6": "NOT_AUTHORIZED",
            "PILOT_GATE_11_V7": "BLOCKED",
        },
        "externalDecisionRecord": {
            "decision": "A classificação provisória da pressão mecânica foi substituída pelo julgamento externo fornecido no briefing.",
            "retroactiveMutationPerformed": False,
        },
        "frontStates": {
            row.analysis_id: row.classification for row in panels["opportunities"].itertuples(index=False)
        },
        "qa": qa,
        "stopForExternalJudgment": True,
        "job5gcStarted": False,
        "job5hStarted": False,
        "publicNarrativeProduced": False,
    }
    staging = staging_directory_for(output_root)
    artifacts: list[dict[str, Any]] = []
    try:
        json_outputs = {
            OUTPUT_FILES[0]: dictionary,
            OUTPUT_FILES[9]: dossier,
            OUTPUT_FILES[12]: limitations,
            OUTPUT_FILES[13]: review_package,
        }
        for name, payload in json_outputs.items():
            path = staging / name
            write_json(path, payload)
            artifacts.append(_artifact(path, staging))
        frame_outputs = {
            OUTPUT_FILES[1]: panels["adult"],
            OUTPUT_FILES[2]: panels["eja_distribution"],
            OUTPUT_FILES[3]: panels["eja_history"],
            OUTPUT_FILES[4]: panels["eja_ept"],
            OUTPUT_FILES[5]: panels["vulnerability"],
            OUTPUT_FILES[6]: panels["special"],
            OUTPUT_FILES[7]: panels["rural"],
            OUTPUT_FILES[8]: panels["pne_links"],
            OUTPUT_FILES[10]: panels["opportunities"],
        }
        for name, frame in frame_outputs.items():
            path = staging / name
            write_csv_gzip(path, frame)
            artifacts.append(_artifact(path, staging, frame))
        map_path = staging / OUTPUT_FILES[11]
        _write_text(map_path, _section_map(panels["opportunities"]))
        artifacts.append(_artifact(map_path, staging))
        artifacts = sorted(artifacts, key=lambda item: item["path"])
        manifest = {
            "schemaVersion": SCHEMA_VERSION,
            "jobId": "JOB_5GB",
            "classification": "DATA_LOGIC",
            "domains": ["DATA_MATERIALIZATION", "ANALYTICAL_TESTING"],
            "objective": "Materializar escolaridade adulta, EJA, vulnerabilidade, educação especial/AEE, ruralidade e vínculos PNE/PME para julgamento externo.",
            "finalState": FINAL_STATE,
            "artifacts": artifacts,
            "sourceFingerprints": source_digests,
            "cadunicoSourceFingerprints": cadunico_hashes,
            "previousPackages": previous,
            "formulasPreserved": [
                "regional_share = municipal_count / sum_compatible_regional_counts",
                "distribution_difference_pp = 100 * (enrollment_share - resident_public_share)",
                "eja_total = eja_fundamental + eja_high_school",
                "integrated_total = technical_integrated + fic_fundamental + fic_high_school",
                "aggregate_percent = 100 * sum(numerator) / sum(denominator)",
            ],
            "formulasAltered": False,
            "generation": {
                "databaseUsed": True,
                "databaseReadOnly": True,
                "networkUsed": False,
                "publicDataChanged": False,
                "frontendChanged": False,
                "compilerUsed": False,
                "fullBuildUsed": False,
                "published": False,
                "job5gcStarted": False,
                "job5hStarted": False,
                "job6Started": False,
            },
            "qa": qa,
            "score": None,
            "automaticApproval": False,
            "externalJudgmentRequired": True,
            "stopForExternalJudgment": True,
        }
        manifest_path = staging / OUTPUT_FILES[14]
        write_json(manifest_path, manifest)
        if set(path.name for path in staging.iterdir()) != set(OUTPUT_FILES):
            raise ValueError("O staging não contém exatamente os 15 outputs do Job 5G-B.")
        validation = validate_existing_output(staging, verify_previous=False)
        promotion = _promote_package(staging, output_root)
    except Exception:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
        raise
    return {
        "finalState": FINAL_STATE,
        "outputRoot": str(output_root),
        "outputCount": len(OUTPUT_FILES),
        "promotion": promotion,
        "validation": validation,
    }


def validate_existing_output(
    output_root: Path = DEFAULT_OUTPUT_ROOT, *, verify_previous: bool = True
) -> dict[str, Any]:
    output_root = output_root.resolve()
    assert_outside_public_data(output_root, REPO_ROOT)
    if set(path.name for path in output_root.iterdir()) != set(OUTPUT_FILES):
        raise ValueError("Pacote existente não contém exatamente os 15 outputs.")
    manifest = _load_json(output_root / OUTPUT_FILES[14])
    if manifest["finalState"] != FINAL_STATE or not manifest["stopForExternalJudgment"]:
        raise ValueError("Estado final ou parada externa divergente.")
    for artifact in manifest["artifacts"]:
        path = output_root / artifact["path"]
        if path.stat().st_size != artifact["byteSize"] or sha256_file(path) != artifact["sha256"]:
            raise ValueError(f"Artefato divergente do manifesto: {path.name}")
    if verify_previous:
        _verify_previous_packages()
    opportunities = _read_csv(output_root / OUTPUT_FILES[10])
    if opportunities["score"].notna().any():
        raise ValueError("Score deve permanecer vazio.")
    if opportunities["automatic_approval"].astype(str).str.casefold().isin({"true", "1"}).any():
        raise ValueError("Aprovação automática proibida.")
    return {
        "finalState": FINAL_STATE,
        "outputCount": len(OUTPUT_FILES),
        "packageDigest": directory_content_digest(output_root),
        "promotion": "validated_existing",
    }


__all__ = [
    "ALLOWED_CLASSIFICATIONS",
    "DEFAULT_OUTPUT_ROOT",
    "FINAL_STATE",
    "NOVA_SANTA_RITA_ID",
    "OUTPUT_FILES",
    "REPO_ROOT",
    "materialize",
    "validate_existing_output",
]
