import time
from functools import lru_cache

from src.data.repository import (
    clear_data_cache,
    fetch_raw_table,
    fetch_table,
    load_atendimento_overview_data,
    get_data_cache_ttl_seconds,
    get_supabase_client,
    load_dataset,
    load_municipios,
)
from src.school_infrastructure_materialization import build_contracts


def fetch_supabase_table(_client, table_name: str):
    return fetch_table(table_name)


def load_pne_data():
    return load_dataset("pne_data")


def load_pre_escola_data():
    return load_dataset("pre_escola_data")


def load_basico_6_17_data():
    return load_dataset("basico_6_17_data")


def load_basico_15_17_data():
    return load_dataset("basico_15_17_data")


def load_basico_0_5_data():
    return load_dataset("basico_0_5_data")


def load_basico_4_17_data():
    return load_dataset("basico_4_17_data")


def load_basico_6_14_data():
    return load_dataset("basico_6_14_data")


def load_basico_integral_data():
    return load_dataset("basico_integral_data")


def load_escolas_integral_data():
    return load_dataset("escolas_integral_data")


def load_escolas_integral_referencia_data():
    return load_dataset("escolas_integral_referencia_data")


def load_infraestrutura_escolar_referencia_data():
    return load_dataset("escolas_integral_referencia_data")


def load_escolas_integral_por_dependencia_data():
    return load_dataset("escolas_integral_por_dependencia_data")


def load_creche_por_dependencia_data():
    return load_dataset("creche_por_dependencia_data")


def load_pre_escola_por_dependencia_data():
    return load_dataset("pre_escola_por_dependencia_data")


def load_basico_6_17_por_dependencia_data():
    return load_dataset("basico_6_17_por_dependencia_data")


def load_basico_15_17_por_dependencia_data():
    return load_dataset("basico_15_17_por_dependencia_data")


def load_basico_integral_por_dependencia_data():
    return load_dataset("basico_integral_por_dependencia_data")


def load_medio_tecnico_data():
    return load_dataset("medio_tecnico_data")


def load_medio_tecnico_articulado_data():
    return load_dataset("medio_tecnico_articulado_data")


def load_ept_nivel_medio_data():
    return load_dataset("ept_nivel_medio_data")


def load_eja_integrada_educacao_profissional_data():
    return load_dataset("eja_integrada_educacao_profissional_data")


def load_censo_populacao_alfabetizacao_data():
    return load_dataset("censo_populacao_alfabetizacao_data")


def load_censo_populacao_escolaridade_media_18_29_data():
    return load_dataset("censo_populacao_escolaridade_media_18_29_data")


def load_censo_populacao_escolaridade_media_18_29_racial_data():
    return load_dataset("censo_populacao_escolaridade_media_18_29_racial_data")


def load_censo_populacao_ensino_medio_15_17_data():
    return load_dataset("censo_populacao_ensino_medio_15_17_data")


def load_censo_populacao_ensino_fundamental_6_14_data():
    return load_dataset("censo_populacao_ensino_fundamental_6_14_data")


def load_censo_populacao_ensino_fundamental_concluido_18_mais_data():
    return load_dataset("censo_populacao_ensino_fundamental_concluido_18_mais_data")


def load_censo_populacao_ensino_fundamental_concluido_18_29_data():
    return load_dataset("censo_populacao_ensino_fundamental_concluido_18_29_data")


def load_censo_populacao_ensino_fundamental_concluido_15_29_data():
    return load_dataset("censo_populacao_ensino_fundamental_concluido_15_29_data")


def load_censo_populacao_ensino_fundamental_concluido_15_mais_data():
    return load_dataset("censo_populacao_ensino_fundamental_concluido_15_mais_data")


def load_censo_populacao_ensino_medio_concluido_18_mais_data():
    return load_dataset("censo_populacao_ensino_medio_concluido_18_mais_data")


def load_censo_populacao_ensino_medio_concluido_18_29_data():
    return load_dataset("censo_populacao_ensino_medio_concluido_18_29_data")


def load_taxa_alfabetizacao_data(*, cycle=None):
    if cycle == "pne_2014_2024":
        from src.pne_2014_child_literacy import load_dataframe

        return load_dataframe()
    return load_dataset("taxa_alfabetizacao_data")


def load_saeb_proficiencia_data():
    return load_dataset("saeb_proficiencia_data")


def load_saeb_ideb_data():
    return load_dataset("saeb_ideb_data")


def load_distorcao_idade_serie_data():
    return load_dataset("distorcao_idade_serie_data")


def load_adequacao_docente_data():
    return load_dataset("adequacao_docente_data")


def load_docentes_pos_graduacao_data():
    return load_dataset("docentes_pos_graduacao_data")


def load_docentes_temporarios_data():
    return load_dataset("docentes_temporarios_data")


def load_rendimento_professores_data():
    return load_dataset("rendimento_professores_data")


def load_atendimento_educacional_especializado_data():
    return load_dataset("atendimento_educacional_especializado_data")


def load_infraestrutura_escolar_data():
    return load_dataset("infraestrutura_escolar_data")


def load_school_infrastructure_source_data():
    return load_dataset("school_infrastructure_source_data")


def load_special_education_school_source_data():
    return load_dataset("special_education_school_source_data")


@lru_cache(maxsize=4)
def _load_school_infrastructure_contracts_cached(cache_bucket: int):
    source = load_school_infrastructure_source_data()
    if source.empty:
        return {}, {}
    if "municipio" not in source.columns:
        municipalities = load_infraestrutura_escolar_data()[
            ["id_municipio", "municipio"]
        ].drop_duplicates()
        source = source.copy()
        source["id_municipio"] = source["id_municipio"].astype(str)
        municipalities["id_municipio"] = municipalities["id_municipio"].astype(str)
        source = source.merge(municipalities, on="id_municipio", how="left")
    codes = sorted(source["id_municipio"].astype(str).unique())
    contracts = build_contracts(source, codes)
    names = (
        source[["id_municipio", "municipio"]]
        .drop_duplicates()
        .assign(id_municipio=lambda frame: frame["id_municipio"].astype(str))
    )
    code_by_name = dict(zip(names["municipio"], names["id_municipio"]))
    return contracts, code_by_name


def load_school_infrastructure_contract(municipio):
    ttl = get_data_cache_ttl_seconds()
    bucket = time.time_ns() if ttl <= 0 else int(time.time() // ttl)
    contracts, code_by_name = _load_school_infrastructure_contracts_cached(bucket)
    code = code_by_name.get(municipio, str(municipio))
    return contracts.get(code)


def load_infraestrutura_escolar_por_dependencia_data():
    return load_dataset("infraestrutura_escolar_por_dependencia_data")


def load_saeb_matematica_data():
    return load_dataset("saeb_matematica_data")


def load_pne_2014_2024_metricas_data():
    return load_dataset("pne_2014_2024_metricas_data")


def load_fundeb_data():
    return fetch_raw_table("siope_fundeb_municipio_dashboard")


def load_pnate_data():
    return fetch_raw_table("fnde_pnate_municipio_dashboard")


def load_pne_2026_2036_metricas_data():
    return load_dataset("pne_2026_2036_metricas_data")


def load_matriculas_privadas_conveniadas():
    return fetch_raw_table("matriculas_privadas_conveniadas_poder_publico")


__all__ = [
    "clear_data_cache",
    "fetch_supabase_table",
    "load_atendimento_overview_data",
    "get_data_cache_ttl_seconds",
    "get_supabase_client",
    "load_fundeb_data",
    "load_pnate_data",
    "load_municipios",
    "load_basico_15_17_data",
    "load_basico_0_5_data",
    "load_basico_4_17_data",
    "load_basico_6_14_data",
    "load_basico_6_17_data",
    "load_basico_integral_data",
    "load_escolas_integral_data",
    "load_escolas_integral_referencia_data",
    "load_infraestrutura_escolar_referencia_data",
    "load_escolas_integral_por_dependencia_data",
    "load_creche_por_dependencia_data",
    "load_pre_escola_por_dependencia_data",
    "load_basico_6_17_por_dependencia_data",
    "load_basico_15_17_por_dependencia_data",
    "load_basico_integral_por_dependencia_data",
    "load_ept_nivel_medio_data",
    "load_eja_integrada_educacao_profissional_data",
    "load_censo_populacao_alfabetizacao_data",
    "load_censo_populacao_escolaridade_media_18_29_data",
    "load_censo_populacao_escolaridade_media_18_29_racial_data",
    "load_censo_populacao_ensino_medio_15_17_data",
    "load_censo_populacao_ensino_fundamental_6_14_data",
    "load_censo_populacao_ensino_fundamental_concluido_18_mais_data",
    "load_censo_populacao_ensino_fundamental_concluido_18_29_data",
    "load_censo_populacao_ensino_fundamental_concluido_15_29_data",
    "load_censo_populacao_ensino_fundamental_concluido_15_mais_data",
    "load_censo_populacao_ensino_medio_concluido_18_mais_data",
    "load_censo_populacao_ensino_medio_concluido_18_29_data",
    "load_medio_tecnico_data",
    "load_medio_tecnico_articulado_data",
    "load_pne_data",
    "load_pre_escola_data",
    "load_adequacao_docente_data",
    "load_docentes_pos_graduacao_data",
    "load_docentes_temporarios_data",
    "load_rendimento_professores_data",
    "load_atendimento_educacional_especializado_data",
    "load_infraestrutura_escolar_data",
    "load_school_infrastructure_source_data",
    "load_school_infrastructure_contract",
    "load_special_education_school_source_data",
    "load_infraestrutura_escolar_por_dependencia_data",
    "load_distorcao_idade_serie_data",
    "load_saeb_ideb_data",
    "load_saeb_proficiencia_data",
    "load_saeb_matematica_data",
    "load_matriculas_privadas_conveniadas",
    "load_pne_2014_2024_metricas_data",
    "load_pne_2026_2036_metricas_data",
    "load_taxa_alfabetizacao_data",
]
