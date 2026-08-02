"""Regras de neg?cio puras, sem depend?ncia da aplica??o Dash."""

import math

import time

import pandas as pd


from src.data_loader import get_data_cache_ttl_seconds, load_adequacao_docente_data, load_atendimento_educacional_especializado_data, load_basico_15_17_data, load_basico_6_17_data, load_basico_integral_data, load_censo_populacao_alfabetizacao_data, load_censo_populacao_ensino_fundamental_concluido_15_29_data, load_censo_populacao_ensino_fundamental_concluido_15_mais_data, load_censo_populacao_ensino_fundamental_concluido_18_mais_data, load_censo_populacao_ensino_medio_concluido_18_29_data, load_censo_populacao_ensino_medio_concluido_18_mais_data, load_docentes_pos_graduacao_data, load_docentes_temporarios_data, load_eja_integrada_educacao_profissional_data, load_escolas_integral_data, load_ept_nivel_medio_data, load_infraestrutura_escolar_data, load_medio_tecnico_articulado_data, load_pne_data, load_pne_2026_2036_metricas_data, load_pre_escola_data, load_rendimento_professores_data, load_saeb_proficiencia_data, load_taxa_alfabetizacao_data, load_distorcao_idade_serie_data
from src.data_loader import load_school_infrastructure_contract
from src.school_infrastructure_materialization import (
    REFERENCE_YEAR as SCHOOL_INFRASTRUCTURE_REFERENCE_YEAR,
    adapt_pne_internet_yearly,
)

from src.pne_trend import attach_trend
from src.pne.goal_indicator_contract import (
    CONTRACT,
    get_formula_for_indicator,
    get_indicator,
    get_indicator_reference_profile,
    get_relation_context_for_indicator,
)

from src.medio_tecnico_articulado import (
    BASELINE_YEAR as CYCLE_BASELINE_YEAR,
    MedioTecnicoArticuladoValidationError,
    calculate_medio_tecnico_articulado_series,
    calculate_public_expansion_series,
    calculate_subsequent_expansion_series,
)

from src.pne.common import GOAL_AT_LEAST, GOAL_AT_MOST, _build_accumulated_growth_result, _build_eja_integrada_percentual_result, _build_ratio_result, _build_result, _build_value_result, _empty_result, _goal_achieved, _safe_load

TARGET_START_YEAR = 2015

TARGET_END_YEAR = 2025

def _contract_reference(indicator_id, observed_year=TARGET_END_YEAR):
    return get_indicator_reference_profile(indicator_id, observed_year)


def _contract_reference_value(indicator_id, observed_year=TARGET_END_YEAR):
    reference = _contract_reference(indicator_id, observed_year)
    if reference is None:
        raise ValueError(f"Indicador sem referência canônica: {indicator_id}")
    return float(reference["value"])


def _contract_milestone_value(indicator_id, position):
    reference = _contract_reference(indicator_id)
    milestones = (reference or {}).get("milestones") or []
    if not milestones:
        raise ValueError(f"Indicador sem marcos canônicos: {indicator_id}")
    return float(milestones[position]["value"])


def _contract_goal_milestones(goal_id, reference_id, dimension=None):
    goal = CONTRACT["goals"][goal_id]
    reference = next(
        (
            item
            for item in goal.get("legalReferences", [])
            if item["referenceId"] == reference_id
        ),
        None,
    )
    if reference is None:
        raise ValueError(f"Referência canônica ausente: {reference_id}")
    return [
        milestone
        for milestone in reference["milestones"]
        if dimension is None or milestone.get("dimension") == dimension
    ]


def _contract_goal_milestone_value(
    goal_id,
    reference_id,
    position,
    *,
    dimension=None,
):
    milestones = _contract_goal_milestones(
        goal_id,
        reference_id,
        dimension,
    )
    if not milestones:
        raise ValueError(
            f"Marco canônico ausente: {reference_id}/{dimension or 'overall'}"
        )
    return float(milestones[position]["value"])


META_CRECHE = _contract_reference_value("creche")

META_PRE_ESCOLA = _contract_reference_value("pre_escola")

META_BASICO_6_17 = _contract_reference_value("basico_6_17")

META_BASICO_15_17 = _contract_reference_value("basico_15_17")

META_BASICO_INTEGRAL_INICIAL = _contract_milestone_value("basico_integral", 0)

META_BASICO_INTEGRAL_FINAL = _contract_milestone_value("basico_integral", -1)

META_ESCOLAS_INTEGRAL_INICIAL = _contract_milestone_value("escolas_integral", 0)

META_ESCOLAS_INTEGRAL_FINAL = _contract_milestone_value("escolas_integral", -1)

META_EJA_INTEGRADA_EPT_INTERMEDIARIA = _contract_milestone_value(
    "eja_integrada_educacao_profissional_percentual",
    0,
)

META_EJA_INTEGRADA_EPT_FINAL = _contract_milestone_value(
    "eja_integrada_educacao_profissional_percentual",
    -1,
)

META_MEDIO_TECNICO_ARTICULADO = _contract_reference_value(
    "medio_tecnico_articulado_percentual"
)

META_EPT_PARTICIPACAO_PUBLICA = _contract_reference_value(
    "medio_tecnico_participacao_publica"
)

META_SUBSEQUENTE_EXPANSAO = _contract_reference_value("subsequente_expansao")

META_ALFABETIZACAO_POP_15_MAIS_5_ANO = _contract_milestone_value(
    "alfabetizacao_pop_15_mais",
    0,
)

META_ALFABETIZACAO_POP_15_MAIS_FINAL = _contract_milestone_value(
    "alfabetizacao_pop_15_mais",
    -1,
)

META_FUNDAMENTAL_CONCLUIDO_18_MAIS = _contract_reference_value(
    "fundamental_concluido_15_mais"
)

META_FUNDAMENTAL_CONCLUIDO_15_29 = _contract_reference_value(
    "fundamental_concluido_15_29"
)

META_MEDIO_CONCLUIDO_18_MAIS = _contract_reference_value(
    "medio_concluido_18_mais"
)

META_MEDIO_CONCLUIDO_18_29 = _contract_reference_value(
    "medio_concluido_18_29"
)

META_ALFABETIZACAO = _contract_milestone_value("alfabetizacao", -1)

META_SAEB_ADEQUADO = {
    "anos_iniciais": _contract_reference_value(
        "saeb_matematica_anos_iniciais"
    ),
    "anos_finais": _contract_reference_value(
        "saeb_matematica_anos_finais"
    ),
    "ensino_medio": _contract_reference_value(
        "saeb_matematica_ensino_medio"
    ),
}

META_SAEB_BASICO = {
    "anos_iniciais": _contract_goal_milestone_value(
        "5.a",
        "reference.5.a.saeb_matematica_anos_iniciais",
        0,
        dimension="basic_or_higher",
    ),
    "anos_finais": _contract_goal_milestone_value(
        "5.b",
        "reference.5.b.saeb_matematica_anos_finais",
        0,
        dimension="basic_or_higher",
    ),
    "ensino_medio": _contract_goal_milestone_value(
        "5.d",
        "reference.5.d.saeb_matematica_ensino_medio",
        0,
        dimension="basic_or_higher",
    ),
}

META_IDADE_REGULAR = {
    "quinto_ano": _contract_reference_value("idade_regular_quinto"),
    "nono_ano": _contract_reference_value("idade_regular_nono"),
    "ensino_medio": _contract_reference_value("idade_regular_medio"),
}

META_ADEQUACAO = {
    "anos_iniciais": _contract_reference_value("adequacao_ai"),
    "anos_finais": _contract_reference_value("adequacao_af"),
    "ensino_medio": _contract_reference_value("adequacao_em"),
}

META_POS_GRADUACAO = _contract_goal_milestone_value(
    "17.f",
    "reference.17.f.pos_graduacao",
    -1,
)

META_RENDIMENTO_MAGISTERIO = _contract_goal_milestone_value(
    "17.b",
    "reference.17.b.rendimento_magisterio",
    -1,
)

META_TEMPORARIOS = _contract_goal_milestone_value(
    "17.d",
    "reference.17.d.temporarios",
    -1,
)

META_INFRA_CONECTIVIDADE_2_ANO = _contract_goal_milestone_value(
    "7.a",
    "reference.7.a.connectivity",
    0,
)

META_INFRA_CONECTIVIDADE_5_ANO = _contract_goal_milestone_value(
    "7.a",
    "reference.7.a.connectivity",
    1,
)

META_INFRA_CONECTIVIDADE_FINAL = _contract_goal_milestone_value(
    "7.a",
    "reference.7.a.connectivity",
    -1,
)

META_INFRA_CONSELHO_ESCOLAR = _contract_reference_value("conselho_escolar")

ANO_TRANSICAO_META_2031 = int(
    _contract_reference("basico_integral")["milestones"][0]["year"]
)

ANO_FINAL_PNE_2036 = int(CONTRACT["cycle"]["endYear"])

SAEB_ETAPA_CODIGO = {
    "anos_iniciais": 5,
    "anos_finais": 9,
    "ensino_medio": 12,
}

SAEB_ETAPA_LABELS = {
    "anos_iniciais": "Anos iniciais",
    "anos_finais": "Anos finais",
    "ensino_medio": "Ensino médio",
}

SAEB_MATERIA_LABELS = {
    "matematica": "Matemática",
    "portugues": "Português",
}

SAEB_NIVEL_COLUMNS = {
    "basico": "taxa_basico_ou_superior",
    "adequado": "taxa_adequado_ou_superior",
}

SAEB_RESULT_GROUPS = {
    f"saeb_{materia}_{nivel}_{etapa}": {
        "materia": materia,
        "nivel": nivel,
        "etapa": etapa,
        "etapa_codigo": etapa_codigo,
        "value_column": SAEB_NIVEL_COLUMNS[nivel],
        "meta": (
            META_SAEB_BASICO[etapa]
            if nivel == "basico"
            else META_SAEB_ADEQUADO[etapa]
        ),
    }
    for materia in ("matematica", "portugues")
    for nivel in ("basico", "adequado")
    for etapa, etapa_codigo in SAEB_ETAPA_CODIGO.items()
}

SAEB_DISPLAY_GROUPS = {
    f"saeb_{materia}_{etapa}": {
        "materia": materia,
        "etapa": etapa,
        "etapa_codigo": etapa_codigo,
    }
    for materia in ("matematica", "portugues")
    for etapa, etapa_codigo in SAEB_ETAPA_CODIGO.items()
}

IDADE_REGULAR_RESULT_GROUPS = {
    "idade_regular_quinto": ("quinto_ano", META_IDADE_REGULAR["quinto_ano"]),
    "idade_regular_nono": ("nono_ano", META_IDADE_REGULAR["nono_ano"]),
    "idade_regular_medio": ("ensino_medio", META_IDADE_REGULAR["ensino_medio"]),
}

ADEQUACAO_RESULT_GROUPS = {
    "adequacao_ai": ("anos_iniciais", META_ADEQUACAO["anos_iniciais"]),
    "adequacao_af": ("anos_finais", META_ADEQUACAO["anos_finais"]),
    "adequacao_em": ("ensino_medio", META_ADEQUACAO["ensino_medio"]),
}

INFRA_ITEMS = [
    {
        "key": "internet",
        "label": "Escolas da educação básica com acesso à internet",
        "sub": "",
        "desc": "Percentual de escolas da educação básica com acesso à internet.",
        "value_column": "percentual_internet",
        "count_column": "escolas_com_internet",
        "denominator_column": "qntd_escolas",
        "start_year": TARGET_START_YEAR,
    },
    {
        "key": "internet_alunos",
        "label": "Escolas com internet disponível para os alunos",
        "sub": "",
        "desc": "Percentual de escolas com internet disponível para uso dos alunos.",
        "value_column": "percentual_internet_alunos",
        "count_column": "escolas_com_internet_alunos",
        "denominator_column": "qntd_escolas",
        "start_year": 2019,
    },
    {
        "key": "internet_aprendizagem",
        "label": "Escolas com internet usada na aprendizagem",
        "sub": "",
        "desc": "Percentual de escolas com internet aplicada aos processos de ensino e aprendizagem.",
        "value_column": "percentual_internet_aprendizagem",
        "count_column": "escolas_com_internet_aprendizagem",
        "denominator_column": "qntd_escolas",
        "start_year": 2019,
    },
    {
        "key": "internet_comunidade",
        "label": "Escolas com internet aberta à comunidade",
        "sub": "",
        "desc": "Percentual de escolas com internet aberta ao uso da comunidade.",
        "value_column": "percentual_internet_comunidade",
        "count_column": "escolas_com_internet_comunidade",
        "denominator_column": "qntd_escolas",
        "start_year": 2019,
    },
    {
        "key": "acesso_internet_computador",
        "label": "Escolas com acesso dos alunos à internet por computador",
        "sub": "",
        "desc": "Percentual de escolas em que os alunos acessam a internet por computadores da escola.",
        "value_column": "percentual_acesso_internet_computador",
        "count_column": "escolas_com_acesso_internet_computador",
        "denominator_column": "qntd_escolas",
        "start_year": 2019,
    },
    {
        "key": "acesso_internet_disp_pessoais",
        "label": "Escolas com acesso dos alunos à internet por dispositivos pessoais",
        "sub": "",
        "desc": "Percentual de escolas em que os alunos acessam a internet por dispositivos pessoais.",
        "value_column": "percentual_acesso_internet_disp_pessoais",
        "count_column": "escolas_com_acesso_internet_disp_pessoais",
        "denominator_column": "qntd_escolas",
        "start_year": 2019,
    },
    {
        "key": "rede_local",
        "label": "Escolas com rede local de computadores",
        "sub": "",
        "desc": "Percentual de escolas com rede local de interligação de computadores.",
        "value_column": "percentual_rede_local",
        "count_column": "escolas_com_rede_local",
        "denominator_column": "qntd_escolas",
        "start_year": 2019,
    },
    {
        "key": "rede_wireless",
        "label": "Escolas com rede local sem fio",
        "sub": "",
        "desc": "Percentual de escolas com rede local wireless.",
        "value_column": "percentual_rede_wireless",
        "count_column": "escolas_com_rede_wireless",
        "denominator_column": "qntd_escolas",
        "start_year": 2019,
    },
    {
        "key": "banda_larga",
        "label": "Escolas com internet banda larga",
        "sub": "",
        "desc": "Percentual de escolas com oferta de internet banda larga.",
        "value_column": "percentual_banda_larga",
        "count_column": "escolas_com_banda_larga",
        "denominator_column": "qntd_escolas",
        "start_year": TARGET_START_YEAR,
    },
    {
        "key": "educacao_ambiental",
        "label": "Escolas que promovem educação ambiental",
        "sub": "",
        "desc": "Percentual de escolas que promovem educação ambiental.",
        "value_column": "percentual_educacao_ambiental",
        "count_column": "escolas_com_educacao_ambiental",
        "denominator_column": "qntd_escolas",
        "start_year": 2024,
        "meta": 100.0,
        "meta_label": "Meta PNE 2036",
        "tracks_goal": True,
    },
    {
        "key": "conselho_escolar",
        "label": "Escolas públicas que declararam possuir conselho escolar",
        "sub": "",
        "desc": "Percentual de escolas públicas que declararam possuir conselho escolar no Censo Escolar; a resposta não comprova composição, regularidade de reuniões, permanência ou funcionamento efetivo.",
        "value_column": "percentual_conselho_escolar",
        "count_column": "escolas_publicas_com_orgao_conselho_escolar",
        "denominator_column": "escolas_publicas_total",
        "start_year": 2019,
        "meta": META_INFRA_CONSELHO_ESCOLAR,
        "meta_label": "Meta PNE 2036",
        "tracks_goal": True,
    },
    {
        "key": "proposta_pedagogica",
        "label": "Escolas públicas com projeto político pedagógico",
        "sub": "",
        "desc": "Percentual de escolas públicas da educação básica que possuem projeto político pedagógico ou proposta pedagógica. Considera as escolas que responderam sim ou não à atualização nos últimos 12 meses.",
        "value_column": "percentual_proposta_pedagogica",
        "count_column": "escolas_publicas_com_proposta_pedagogica",
        "denominator_column": "escolas_publicas_total",
        "start_year": TARGET_START_YEAR,
    },
    {
        "key": "salas_climatizadas",
        "label": "Salas de aula climatizadas",
        "sub": "",
        "desc": "Percentual de salas de aula utilizadas que são climatizadas.",
        "value_column": "percentual_salas_climatizadas",
        "count_column": "qt_salas_utiliza_climatizadas",
        "denominator_column": "qt_salas_utilizadas",
        "start_year": 2019,
        "meta": 100.0,
        "meta_label": "Meta PNE 2036",
        "tracks_goal": True,
    },
    {
        "key": "salas_acessiveis",
        "label": "Salas de aula com acessibilidade",
        "sub": "",
        "desc": "Percentual de salas de aula utilizadas com acessibilidade.",
        "value_column": "percentual_salas_acessiveis",
        "count_column": "qt_salas_utilizadas_acessiveis",
        "denominator_column": "qt_salas_utilizadas",
        "start_year": 2019,
        "meta": 100.0,
        "meta_label": "Meta PNE 2036",
        "tracks_goal": True,
    },
    {
        "key": "desktop_aluno",
        "label": "Escolas com computadores de mesa para alunos",
        "sub": "",
        "desc": "Percentual de escolas com computadores de mesa disponíveis para os alunos.",
        "value_column": "percentual_desktop_aluno",
        "count_column": "escolas_com_desktop_aluno",
        "denominator_column": "qntd_escolas",
        "start_year": 2019,
    },
    {
        "key": "comp_portatil_aluno",
        "label": "Escolas com computadores portáteis para alunos",
        "sub": "",
        "desc": "Percentual de escolas com computadores portáteis disponíveis para os alunos.",
        "value_column": "percentual_comp_portatil_aluno",
        "count_column": "escolas_com_comp_portatil_aluno",
        "denominator_column": "qntd_escolas",
        "start_year": 2019,
    },
    {
        "key": "tablet_aluno",
        "label": "Escolas com tablets para alunos",
        "sub": "",
        "desc": "Percentual de escolas com tablets disponíveis para os alunos.",
        "value_column": "percentual_tablet_aluno",
        "count_column": "escolas_com_tablet_aluno",
        "denominator_column": "qntd_escolas",
        "start_year": 2019,
    },
]

INFRA_RESULT_KEYS = {item["key"] for item in INFRA_ITEMS}

BATCHED_RESULT_KEYS = (
    set(SAEB_DISPLAY_GROUPS)
    | set(IDADE_REGULAR_RESULT_GROUPS)
    | set(ADEQUACAO_RESULT_GROUPS)
    | INFRA_RESULT_KEYS
)

INFORMATIVE_META_LABEL = "Visualização informativa"

def _meta_basico_integral_por_ano(ano):
    return (
        META_BASICO_INTEGRAL_FINAL
        if ano and int(ano) >= ANO_TRANSICAO_META_2031
        else META_BASICO_INTEGRAL_INICIAL
    )

def _meta_basico_integral_label(ano):
    return (
        "Meta PNE 2036"
        if ano and int(ano) >= ANO_TRANSICAO_META_2031
        else "Meta PNE 2031"
    )

def _meta_escolas_integral_por_ano(ano):
    return (
        META_ESCOLAS_INTEGRAL_FINAL
        if ano and int(ano) >= ANO_TRANSICAO_META_2031
        else META_ESCOLAS_INTEGRAL_INICIAL
    )

def _meta_escolas_integral_label(ano):
    return (
        "Meta PNE 2036"
        if ano and int(ano) >= ANO_TRANSICAO_META_2031
        else "Meta PNE 2031"
    )

def _meta_infra_conectividade_por_ano(ano):
    if ano and int(ano) >= ANO_FINAL_PNE_2036:
        return META_INFRA_CONECTIVIDADE_FINAL
    if ano and int(ano) >= ANO_TRANSICAO_META_2031:
        return META_INFRA_CONECTIVIDADE_5_ANO
    return META_INFRA_CONECTIVIDADE_2_ANO

def _meta_infra_conectividade_label(ano):
    if ano and int(ano) >= ANO_FINAL_PNE_2036:
        return "Meta PNE 2036"
    if ano and int(ano) >= ANO_TRANSICAO_META_2031:
        return "Meta PNE 2031"
    return "Meta PNE 2028"

def _apply_dynamic_item_goal(result, item):
    if item.get("dynamic_meta") == "infra_conectividade":
        return _apply_result_goal(
            result,
            _meta_infra_conectividade_por_ano(result.get("end_year")),
            _meta_infra_conectividade_label(result.get("end_year")),
        )
    return result

def _meta_alfabetizacao_pop_15_mais_por_ano(ano):
    return (
        META_ALFABETIZACAO_POP_15_MAIS_FINAL
        if ano and int(ano) >= ANO_FINAL_PNE_2036
        else META_ALFABETIZACAO_POP_15_MAIS_5_ANO
    )

def _meta_alfabetizacao_pop_15_mais_label(ano):
    return (
        "Meta PNE 2036" if ano and int(ano) >= ANO_FINAL_PNE_2036 else "Meta PNE 2031"
    )

def _apply_result_goal(result, meta, meta_label, direction=GOAL_AT_LEAST):
    if not result.get("available"):
        return _empty_result(meta, direction=direction, meta_label=meta_label)

    updated = dict(result)
    updated["meta"] = meta
    updated["meta_label"] = meta_label
    updated["direction"] = direction
    end_value = updated.get("end_value")
    if end_value is None or pd.isna(end_value):
        updated["distance"] = None
        updated["atingida"] = False
    else:
        if direction == GOAL_AT_MOST:
            distance = float(meta) - float(end_value)
            updated["progress_delta"] = (
                None
                if updated.get("raw_delta") is None
                else -float(updated["raw_delta"])
            )
        else:
            distance = float(end_value) - float(meta)
            updated["progress_delta"] = updated.get("raw_delta")
        updated["distance"] = distance
        updated["atingida"] = _goal_achieved(distance)
    updated["tracks_goal"] = True
    return updated

def _empty_informative_result():
    result = _empty_result(0.0, tracks_goal=False)
    result["meta"] = None
    result["meta_label"] = INFORMATIVE_META_LABEL
    return result

def _finalize_informative_result(result):
    updated = dict(result)
    updated["tracks_goal"] = False
    updated["meta"] = None
    updated["meta_label"] = INFORMATIVE_META_LABEL
    updated["atingida"] = False
    updated.pop("distance", None)
    return updated

def _build_grouped_value_results(
    df,
    municipio,
    *,
    group_column,
    value_column,
    result_groups,
    meta_label,
    target_start_year,
    target_end_year,
    filters=None,
    direction=GOAL_AT_LEAST,
):
    results = {
        result_key: _empty_result(
            meta,
            direction=direction,
            meta_label=meta_label,
        )
        for result_key, (_, meta) in result_groups.items()
    }

    if (
        df.empty
        or "municipio" not in df.columns
        or "ano" not in df.columns
        or group_column not in df.columns
        or value_column not in df.columns
    ):
        return results

    dff = df[df["municipio"] == municipio].copy()
    if filters:
        for column, value in filters.items():
            if column not in dff.columns:
                return results
            dff = dff[dff[column] == value]
    if dff.empty:
        return results

    dff = dff.loc[:, ["ano", group_column, value_column]].copy()
    dff["ano"] = pd.to_numeric(dff["ano"], errors="coerce")
    dff[value_column] = pd.to_numeric(dff[value_column], errors="coerce")
    dff = dff.dropna(subset=["ano", value_column]).copy()
    if dff.empty:
        return results

    dff["ano"] = dff["ano"].astype(int)
    yearly = (
        dff.groupby([group_column, "ano"], as_index=False)[value_column]
        .mean()
        .rename(columns={value_column: "valor"})
    )

    for result_key, (group_value, meta) in result_groups.items():
        yearly_slice = yearly[yearly[group_column] == group_value][["ano", "valor"]]
        if yearly_slice.empty:
            continue
        results[result_key] = _build_result(
            yearly_slice,
            meta,
            direction=direction,
            meta_label=meta_label,
            target_start_year=target_start_year,
            target_end_year=target_end_year,
        )

    return results

def _calculate_saeb_results(municipio):
    results = {
        result_key: _empty_result(
            META_SAEB_ADEQUADO[config["etapa"]], meta_label="Meta PNE 2031"
        )
        for result_key, config in SAEB_DISPLAY_GROUPS.items()
    }
    df = _safe_load(load_saeb_proficiencia_data)
    required_columns = {"municipio", "materia", "etapa_codigo", "ano"} | {
        config["value_column"] for config in SAEB_RESULT_GROUPS.values()
    }
    if df.empty or not required_columns.issubset(df.columns):
        return results

    dff = df[df["municipio"] == municipio].copy()
    if dff.empty:
        return results

    dff["ano"] = pd.to_numeric(dff["ano"], errors="coerce")
    dff["etapa_codigo"] = pd.to_numeric(dff["etapa_codigo"], errors="coerce")
    dff = dff.dropna(subset=["ano", "etapa_codigo"]).copy()
    if dff.empty:
        return results

    dff["etapa_codigo"] = dff["etapa_codigo"].astype(int)

    def build_level_result(filtered_df, *, value_column, meta):
        level_frame = filtered_df[["ano", value_column]].copy()
        level_frame[value_column] = pd.to_numeric(
            level_frame[value_column], errors="coerce"
        )
        level_frame = level_frame.dropna(subset=[value_column])
        if level_frame.empty:
            return _empty_result(meta, meta_label="Meta PNE 2031")

        yearly = level_frame.rename(columns={value_column: "valor"})
        return _build_result(
            yearly,
            meta,
            meta_label="Meta PNE 2031",
            target_start_year=2017,
            target_end_year=TARGET_END_YEAR,
        )

    for result_key, config in SAEB_DISPLAY_GROUPS.items():
        filtered = dff[
            (dff["materia"] == config["materia"])
            & (dff["etapa_codigo"] == config["etapa_codigo"])
        ].copy()
        if filtered.empty:
            continue

        basic_result = build_level_result(
            filtered,
            value_column=SAEB_NIVEL_COLUMNS["basico"],
            meta=META_SAEB_BASICO[config["etapa"]],
        )
        adequate_result = build_level_result(
            filtered,
            value_column=SAEB_NIVEL_COLUMNS["adequado"],
            meta=META_SAEB_ADEQUADO[config["etapa"]],
        )
        adequate_result["saeb_combined"] = True
        adequate_result["basic_result"] = basic_result
        results[result_key] = adequate_result

    return results

def _calculate_idade_regular_results(municipio):
    return _build_grouped_value_results(
        _safe_load(load_distorcao_idade_serie_data),
        municipio,
        group_column="etapa_proxy",
        value_column="taxa_idade_regular",
        result_groups=IDADE_REGULAR_RESULT_GROUPS,
        meta_label="Meta PNE 2036",
        target_start_year=2017,
        target_end_year=TARGET_END_YEAR,
    )

def _calculate_adequacao_results(municipio):
    return _build_grouped_value_results(
        _safe_load(load_adequacao_docente_data),
        municipio,
        group_column="etapa",
        value_column="percentual_adequacao",
        result_groups=ADEQUACAO_RESULT_GROUPS,
        meta_label="Meta PNE 2036",
        target_start_year=2019,
        target_end_year=TARGET_END_YEAR,
        filters={"dependencia": "total"},
    )

def _calculate_infra_results(municipio):
    results = {item["key"]: _empty_informative_result() for item in INFRA_ITEMS}
    df = _safe_load(load_infraestrutura_escolar_data)

    if df.empty or "municipio" not in df.columns or "ano" not in df.columns:
        return results

    numeric_columns = sorted(
        {
            item["count_column"]
            for item in INFRA_ITEMS
            if item["count_column"] in df.columns
        }
        | {
            item["denominator_column"]
            for item in INFRA_ITEMS
            if item["denominator_column"] in df.columns
        }
    )
    if not numeric_columns:
        return results

    dff = df[df["municipio"] == municipio].loc[:, ["ano", *numeric_columns]].copy()
    if dff.empty:
        return results

    dff["ano"] = pd.to_numeric(dff["ano"], errors="coerce")
    dff = dff.dropna(subset=["ano"]).copy()
    if dff.empty:
        return results

    dff["ano"] = dff["ano"].astype(int)
    dff[numeric_columns] = dff[numeric_columns].apply(pd.to_numeric, errors="coerce")

    yearly = dff.groupby("ano", as_index=False)[numeric_columns].sum(min_count=1)
    if yearly.empty:
        return results

    for item in INFRA_ITEMS:
        count_column = item["count_column"]
        denominator_column = item["denominator_column"]
        if (
            count_column not in yearly.columns
            or denominator_column not in yearly.columns
        ):
            continue

        yearly_slice = yearly[yearly["ano"] >= int(item["start_year"])][
            ["ano", count_column, denominator_column]
        ].copy()
        is_canonical_internet = item["key"] == "internet"
        if is_canonical_internet:
            yearly_slice = yearly_slice[
                yearly_slice["ano"].ne(SCHOOL_INFRASTRUCTURE_REFERENCE_YEAR)
            ].copy()
        if yearly_slice.empty:
            yearly_slice = pd.DataFrame(columns=["ano", count_column, denominator_column])

        denominator = yearly_slice[denominator_column].where(
            yearly_slice[denominator_column] != 0,
            pd.NA,
        )
        yearly_slice["valor"] = yearly_slice[count_column].div(denominator).mul(100)
        yearly_slice = yearly_slice.dropna(subset=["valor"])
        if is_canonical_internet:
            contract = _safe_load(
                lambda: load_school_infrastructure_contract(municipio)
            )
            if isinstance(contract, dict):
                yearly_slice = adapt_pne_internet_yearly(yearly_slice, contract)
        if yearly_slice.empty:
            continue

        result = _build_result(
            yearly_slice[["ano", "valor"]],
            item.get("meta", 0.0),
            meta_label=item.get("meta_label", INFORMATIVE_META_LABEL),
            target_start_year=item["start_year"],
            target_end_year=TARGET_END_YEAR,
            tracks_goal=item.get("tracks_goal", False),
        )
        results[item["key"]] = (
            _apply_dynamic_item_goal(result, item)
            if item.get("tracks_goal", False)
            else _finalize_informative_result(result)
        )

    return results

def _calc_creche(municipio):
    return _build_ratio_result(
        load_pne_data,
        municipio,
        numerator="mat_basico_0_3",
        denominator="pop_0_3",
        meta=META_CRECHE,
        meta_label="Meta PNE 2036",
        den_agg="max",
        target_start_year=TARGET_START_YEAR,
        target_end_year=TARGET_END_YEAR,
    )

def _calc_pre_escola(municipio):
    return _build_ratio_result(
        load_pre_escola_data,
        municipio,
        numerator="mat_infantil_pre",
        denominator="pop_4_5",
        meta=META_PRE_ESCOLA,
        meta_label="Meta PNE 2036",
        den_agg="max",
        target_start_year=TARGET_START_YEAR,
        target_end_year=TARGET_END_YEAR,
    )

def _calc_basico_6_17(municipio):
    return _build_ratio_result(
        load_basico_6_17_data,
        municipio,
        numerator="mat_basico_6_17",
        denominator="pop_6_17",
        meta=META_BASICO_6_17,
        meta_label="Meta PNE 2036",
        den_agg="max",
        target_start_year=TARGET_START_YEAR,
        target_end_year=TARGET_END_YEAR,
    )

def _calc_basico_15_17(municipio):
    return _build_ratio_result(
        load_basico_15_17_data,
        municipio,
        numerator="mat_basico_15_17",
        denominator="pop_15_17",
        meta=META_BASICO_15_17,
        meta_label="Meta PNE 2036",
        den_agg="max",
        target_start_year=TARGET_START_YEAR,
        target_end_year=TARGET_END_YEAR,
    )

def _calc_basico_integral(municipio):
    result = _build_ratio_result(
        load_basico_integral_data,
        municipio,
        numerator="mat_basico_integral",
        denominator="mat_basico",
        meta=META_BASICO_INTEGRAL_INICIAL,
        meta_label="Meta vigente do PNE",
        target_start_year=TARGET_START_YEAR,
        target_end_year=TARGET_END_YEAR,
    )
    if not result.get("available"):
        return result
    return _apply_result_goal(
        result,
        _meta_basico_integral_por_ano(result.get("end_year")),
        _meta_basico_integral_label(result.get("end_year")),
    )

def _calc_escolas_integral(municipio):
    result = _build_ratio_result(
        load_escolas_integral_data,
        municipio,
        numerator="escolas_publicas_com_integral",
        denominator="escolas_publicas_total",
        meta=META_ESCOLAS_INTEGRAL_INICIAL,
        meta_label="Meta vigente do PNE",
        target_start_year=TARGET_START_YEAR,
        target_end_year=TARGET_END_YEAR,
    )
    if not result.get("available"):
        return result
    return _apply_result_goal(
        result,
        _meta_escolas_integral_por_ano(result.get("end_year")),
        _meta_escolas_integral_label(result.get("end_year")),
    )

def _calc_aee(municipio):
    result = _build_precomputed_result(
        municipio,
        "aee",
        meta=0.0,
        meta_label=INFORMATIVE_META_LABEL,
    )
    if result is None:
        result = _build_ratio_result(
            load_atendimento_educacional_especializado_data,
            municipio,
            numerator="quantidade_aee",
            denominator="total_turmas_educacao_especial",
            meta=0.0,
            meta_label=INFORMATIVE_META_LABEL,
            target_start_year=TARGET_START_YEAR,
            target_end_year=TARGET_END_YEAR,
        )
    return _finalize_informative_result(result)

def _calc_eja_integrada_educacao_profissional(municipio):
    result = _build_eja_integrada_percentual_result(
        load_eja_integrada_educacao_profissional_data,
        municipio,
        meta=META_EJA_INTEGRADA_EPT_INTERMEDIARIA,
        meta_label="Referência intermediária PNE 2031",
        target_start_year=TARGET_START_YEAR,
        target_end_year=TARGET_END_YEAR,
    )
    result["meta_references"] = [
        {"year": 2031, "value": META_EJA_INTEGRADA_EPT_INTERMEDIARIA, "label": "Referência intermediária"},
        {"year": 2036, "value": META_EJA_INTEGRADA_EPT_FINAL, "label": "Meta final"},
    ]
    if result.get("available"):
        result["display"] = dict(result.get("display") or {})
        result["display"]["status"] = (
            "Atinge a meta no momento"
            if result.get("atingida")
            else "Ainda não atinge a meta"
        )
    return result

def _empty_medio_tecnico_articulado_result():
    result = _empty_result(
        META_MEDIO_TECNICO_ARTICULADO,
        meta_label="Meta PNE 2036",
        tracks_goal=True,
    )
    result.update(
        {
            "show_in_cycle": True,
            "include_in_cycle_summary": True,
            "coverage": "aproximada",
            "value_mode": "percent",
        }
    )
    return result

def _calc_medio_tecnico_articulado_percentual(municipio):
    df = _safe_load(load_medio_tecnico_articulado_data)
    required_columns = {
        "ano",
        "municipio",
        "id_municipio",
        "mat_integrado_total",
        "mat_concomitante_total",
        "mat_medio",
    }
    if df.empty or not required_columns.issubset(df.columns):
        return _empty_medio_tecnico_articulado_result()

    dff = df[df["municipio"] == municipio].copy()
    if dff.empty:
        return _empty_medio_tecnico_articulado_result()

    try:
        calculated = calculate_medio_tecnico_articulado_series(dff)
    except MedioTecnicoArticuladoValidationError as exc:
        print(f"Indicador aproximado indisponível para {municipio}: {exc}")
        return _empty_medio_tecnico_articulado_result()

    calculated = calculated[
        calculated["ano"].between(TARGET_START_YEAR, TARGET_END_YEAR)
    ].copy()
    valid = calculated.dropna(subset=["percentual_calculado"]).copy()
    if valid.empty:
        return _empty_medio_tecnico_articulado_result()

    yearly = valid[["ano", "percentual_calculado"]].rename(
        columns={"percentual_calculado": "valor"}
    )
    result = _build_result(
        yearly,
        META_MEDIO_TECNICO_ARTICULADO,
        meta_label="Meta PNE 2036",
        target_start_year=TARGET_START_YEAR,
        target_end_year=TARGET_END_YEAR,
        tracks_goal=True,
    )
    if not result.get("available"):
        return _empty_medio_tecnico_articulado_result()

    flag_by_year = {
        int(row["ano"]): bool(row["acima_de_100"])
        for _, row in valid.iterrows()
    }
    result["series"] = [
        {
            "ano": int(point["ano"]),
            "valor": float(point["valor"]),
            "acima_de_100": flag_by_year.get(int(point["ano"]), False),
        }
        for point in result["series"]
    ]
    above_100_years = sorted(
        year for year, is_above in flag_by_year.items() if is_above
    )
    result.update(
        {
            "show_in_cycle": True,
            "include_in_cycle_summary": True,
            "coverage": "aproximada",
            "value_mode": "percent",
            "acima_de_100": bool(above_100_years),
            "acima_de_100_anos": above_100_years,
            "dataStatus": "available",
        }
    )
    latest = valid[valid["ano"] == int(result["end_year"])].iloc[-1]
    result["numerator"] = float(latest["mat_articulado_total"])
    result["denominator"] = float(latest["mat_medio"])
    if above_100_years:
        result["display"] = dict(result.get("display") or {})
        result["display"]["warning"] = (
            "Valores acima de 100% podem ocorrer porque a medida usa matrículas "
            "e não estudantes únicos."
        )
    return result


def _fixed_baseline_result(series, meta):
    if series is None or series.empty:
        result = _empty_result(meta, meta_label="Meta PNE 2036")
        result.update(
            {
                "base_year": CYCLE_BASELINE_YEAR,
                "dataStatus": "unavailable",
                "reasonCode": "source_unavailable",
            }
        )
        return result

    available = series[series["data_status"] == "available"].copy()
    if available.empty:
        latest = series.sort_values("ano").iloc[-1]
        result = _empty_result(meta, meta_label="Meta PNE 2036")
        result.update(
            {
                "base_year": CYCLE_BASELINE_YEAR,
                "dataStatus": str(latest["data_status"]),
                "reasonCode": str(latest["reason_code"]),
            }
        )
        for source, destination in (
            ("numerador", "numerator"),
            ("denominador", "denominator"),
            ("reference_value", "reference_value"),
        ):
            if source in latest.index and pd.notna(latest[source]):
                result[destination] = float(latest[source])
        return result

    available = available.sort_values("ano")
    result = _build_result(
        available[["ano", "valor"]],
        meta,
        meta_label="Meta PNE 2036",
        target_start_year=int(available["ano"].min()),
        target_end_year=int(available["ano"].max()),
    )
    latest = available[available["ano"] == int(result["end_year"])].iloc[-1]
    result.update(
        {
            "base_year": CYCLE_BASELINE_YEAR,
            "dataStatus": "available",
            "numerator": float(latest["numerador"]),
            "denominator": float(latest["denominador"]),
        }
    )
    if "reference_value" in latest.index and pd.notna(latest["reference_value"]):
        result["reference_value"] = float(latest["reference_value"])
    return result


def _calc_medio_tecnico_participacao_publica(municipio):
    df = _safe_load(load_ept_nivel_medio_data)
    if df.empty or "municipio" not in df.columns:
        return _fixed_baseline_result(
            pd.DataFrame(), META_EPT_PARTICIPACAO_PUBLICA
        )
    dff = df[df["municipio"] == municipio].copy()
    try:
        series = calculate_public_expansion_series(dff)
    except MedioTecnicoArticuladoValidationError:
        series = pd.DataFrame()
    return _fixed_baseline_result(series, META_EPT_PARTICIPACAO_PUBLICA)

def _calc_subsequente_expansao(municipio):
    df = _safe_load(load_ept_nivel_medio_data)
    if df.empty or "municipio" not in df.columns:
        return _fixed_baseline_result(pd.DataFrame(), META_SUBSEQUENTE_EXPANSAO)
    dff = df[df["municipio"] == municipio].copy()
    try:
        series = calculate_subsequent_expansion_series(dff)
    except MedioTecnicoArticuladoValidationError:
        series = pd.DataFrame()
    return _fixed_baseline_result(series, META_SUBSEQUENTE_EXPANSAO)

def _calc_alfabetizacao(municipio):
    precomputed = _build_precomputed_result(
        municipio,
        "alfabetizacao",
        meta=META_ALFABETIZACAO,
        meta_label="Meta PNE 2036",
        target_start_year=2019,
        target_end_year=TARGET_END_YEAR,
    )
    if precomputed is not None:
        return precomputed

    return _build_value_result(
        load_taxa_alfabetizacao_data,
        municipio,
        value_column="taxa_alfabetizacao",
        meta=META_ALFABETIZACAO,
        meta_label="Meta PNE 2036",
        target_start_year=2019,
        target_end_year=TARGET_END_YEAR,
    )

def _calc_alfabetizacao_pop_15_mais(municipio):
    result = _build_ratio_result(
        load_censo_populacao_alfabetizacao_data,
        municipio,
        numerator="alfabetizadas_15_mais",
        denominator="total_15_mais",
        meta=META_ALFABETIZACAO_POP_15_MAIS_5_ANO,
        meta_label="Meta PNE 2031",
        target_start_year=2010,
        target_end_year=2022,
    )
    meta = _meta_alfabetizacao_pop_15_mais_por_ano(result.get("end_year"))
    meta_label = _meta_alfabetizacao_pop_15_mais_label(result.get("end_year"))
    return _apply_result_goal(result, meta, meta_label)

def _calc_fundamental_concluido_18_mais(municipio):
    return _build_ratio_result(
        load_censo_populacao_ensino_fundamental_concluido_18_mais_data,
        municipio,
        numerator="populacao_18_mais_ensino_fundamental_concluido",
        denominator="populacao_18_mais_total",
        meta=META_FUNDAMENTAL_CONCLUIDO_18_MAIS,
        meta_label="Meta PNE 2036",
        target_start_year=2010,
        target_end_year=2022,
    )

def _calc_fundamental_concluido_15_29(municipio):
    return _build_ratio_result(
        load_censo_populacao_ensino_fundamental_concluido_15_29_data,
        municipio,
        numerator="populacao_15_29_ensino_fundamental_concluido",
        denominator="populacao_15_29_total",
        meta=META_FUNDAMENTAL_CONCLUIDO_15_29,
        meta_label="Meta PNE 2036",
        target_start_year=2022,
        target_end_year=2022,
    )


def _calc_fundamental_concluido_15_mais(municipio):
    return _build_ratio_result(
        load_censo_populacao_ensino_fundamental_concluido_15_mais_data,
        municipio,
        numerator="populacao_15_mais_ensino_fundamental_concluido",
        denominator="populacao_15_mais_total",
        meta=META_FUNDAMENTAL_CONCLUIDO_18_MAIS,
        meta_label="Meta PNE 2036",
        target_start_year=2022,
        target_end_year=2022,
    )

def _calc_medio_concluido_18_mais(municipio):
    return _build_ratio_result(
        load_censo_populacao_ensino_medio_concluido_18_mais_data,
        municipio,
        numerator="populacao_18_mais_ensino_medio_concluido",
        denominator="populacao_18_mais_total",
        meta=META_MEDIO_CONCLUIDO_18_MAIS,
        meta_label="Meta PNE 2036",
        target_start_year=2010,
        target_end_year=2022,
    )

def _calc_medio_concluido_18_29(municipio):
    return _build_ratio_result(
        load_censo_populacao_ensino_medio_concluido_18_29_data,
        municipio,
        numerator="populacao_18_29_ensino_medio_concluido",
        denominator="populacao_18_29_total",
        meta=META_MEDIO_CONCLUIDO_18_29,
        meta_label="Meta PNE 2036",
        target_start_year=2010,
        target_end_year=2022,
    )

def _calc_saeb(municipio, materia, nivel, etapa_key):
    config = SAEB_RESULT_GROUPS[f"saeb_{materia}_{nivel}_{etapa_key}"]
    return _build_value_result(
        load_saeb_proficiencia_data,
        municipio,
        value_column=config["value_column"],
        meta=config["meta"],
        meta_label="Meta PNE 2031",
        filters={
            "materia": materia,
            "etapa_codigo": SAEB_ETAPA_CODIGO[etapa_key],
        },
        target_start_year=2017,
        target_end_year=TARGET_END_YEAR,
    )

def _calc_idade_regular(municipio, etapa_key):
    df = _safe_load(load_distorcao_idade_serie_data)
    if (
        df.empty
        or "municipio" not in df.columns
        or "etapa_proxy" not in df.columns
        or "taxa_idade_regular" not in df.columns
    ):
        return _empty_result(META_IDADE_REGULAR[etapa_key], meta_label="Meta PNE 2036")

    dff = df[df["municipio"] == municipio].copy()
    dff = dff[dff["etapa_proxy"] == etapa_key]
    if dff.empty:
        return _empty_result(META_IDADE_REGULAR[etapa_key], meta_label="Meta PNE 2036")

    yearly = (
        dff.groupby("ano", as_index=False)["taxa_idade_regular"]
        .mean()
        .rename(columns={"taxa_idade_regular": "valor"})
    )
    return _build_result(
        yearly,
        META_IDADE_REGULAR[etapa_key],
        meta_label="Meta PNE 2036",
        target_start_year=2017,
        target_end_year=TARGET_END_YEAR,
    )

def _calc_adequacao(municipio, etapa_key):
    return _build_value_result(
        load_adequacao_docente_data,
        municipio,
        value_column="percentual_adequacao",
        meta=META_ADEQUACAO[etapa_key],
        meta_label="Meta PNE 2036",
        filters={"etapa": etapa_key, "dependencia": "total"},
        target_start_year=2019,
        target_end_year=TARGET_END_YEAR,
    )

def _calc_pos_graduacao(municipio):
    return _build_ratio_result(
        load_docentes_pos_graduacao_data,
        municipio,
        numerator="docentes_pos_graduacao",
        denominator="total_docentes",
        meta=META_POS_GRADUACAO,
        meta_label="Meta PNE 2036",
        filters={"dependencia": "total"},
        target_start_year=TARGET_START_YEAR,
        target_end_year=TARGET_END_YEAR,
    )

def _calc_temporarios(municipio):
    return _build_ratio_result(
        load_docentes_temporarios_data,
        municipio,
        numerator="docentes_temporarios",
        denominator="total_docentes",
        meta=META_TEMPORARIOS,
        meta_label="Meta PNE 2031",
        direction=GOAL_AT_MOST,
        filters={"dependencia": "publica"},
        target_start_year=TARGET_START_YEAR,
        target_end_year=TARGET_END_YEAR,
    )

def _calc_rendimento_magisterio(municipio):
    return _build_value_result(
        load_rendimento_professores_data,
        municipio,
        value_column="razao_percentual_remuneracao_media",
        meta=META_RENDIMENTO_MAGISTERIO,
        meta_label="Meta PNE 2036",
        target_start_year=2014,
        target_end_year=2024,
    )

def _calc_infra_totalizado(municipio, item_cfg):
    df = _safe_load(load_infraestrutura_escolar_data)
    result = _empty_result(0.0, tracks_goal=False)
    result["meta"] = None
    result["meta_label"] = "VisualizaÃ§Ã£o informativa"

    if df.empty or "municipio" not in df.columns:
        return result

    dff = df[df["municipio"] == municipio].copy()
    if dff.empty or "ano" not in dff.columns:
        return result

    dff["ano"] = pd.to_numeric(dff["ano"], errors="coerce")
    dff = dff.dropna(subset=["ano"]).copy()
    dff["ano"] = dff["ano"].astype(int)
    dff = dff[dff["ano"] >= int(item_cfg["start_year"])].copy()
    if dff.empty:
        return result

    count_column = item_cfg["count_column"]
    denominator_column = item_cfg["denominator_column"]
    if count_column not in dff.columns or denominator_column not in dff.columns:
        return result

    dff[count_column] = pd.to_numeric(dff[count_column], errors="coerce")
    dff[denominator_column] = pd.to_numeric(dff[denominator_column], errors="coerce")
    dff = dff.dropna(subset=[count_column, denominator_column]).copy()
    is_canonical_internet = item_cfg["key"] == "internet"
    if is_canonical_internet:
        dff = dff[dff["ano"].ne(SCHOOL_INFRASTRUCTURE_REFERENCE_YEAR)].copy()
    if dff.empty:
        grouped = pd.DataFrame(columns=["ano", "valor"])
    else:
        grouped = dff.groupby("ano", as_index=False).agg(
            {count_column: "sum", denominator_column: "sum"}
        )
        grouped["valor"] = grouped.apply(
            lambda row: (
                100.0 * row[count_column] / row[denominator_column]
                if row[denominator_column]
                else None
            ),
            axis=1,
        )
        grouped = grouped.dropna(subset=["valor"]).copy()

    if is_canonical_internet:
        contract = _safe_load(lambda: load_school_infrastructure_contract(municipio))
        if isinstance(contract, dict):
            grouped = adapt_pne_internet_yearly(grouped, contract)
    if grouped.empty:
        return result

    result = _build_result(
        grouped[["ano", "valor"]],
        0.0,
        meta_label="VisualizaÃ§Ã£o informativa",
        target_start_year=item_cfg["start_year"],
        target_end_year=TARGET_END_YEAR,
        tracks_goal=False,
    )
    result["tracks_goal"] = False
    result["meta"] = None
    result["meta_label"] = "VisualizaÃ§Ã£o informativa"
    return result

INDICADORES = {
    "atendimento": {
        "label": "Atendimento Escolar",
        "icon": "🎓",
        "accent": "#4f46e5",
        "items": [
            {
                "key": "creche",
                "label": "Matrículas de crianças de 0 a 3 anos em relação à população residente estimada",
                "sub": "",
                "desc": "Matrículas de crianças de 0 a 3 anos registradas nas escolas do município divididas pela população residente estimada da mesma faixa; o resultado pode superar 100% por causa da diferença de territorialidade.",
                "meta_label": "Meta PNE 2036",
                "compute": _calc_creche,
            },
            {
                "key": "pre_escola",
                "label": "Matrículas de crianças de 4 a 5 anos em relação à população residente estimada",
                "sub": "",
                "desc": "Matrículas de crianças de 4 a 5 anos registradas nas escolas do município divididas pela população residente estimada da mesma faixa; o resultado pode superar 100% por causa da diferença de territorialidade.",
                "meta_label": "Meta PNE 2036",
                "compute": _calc_pre_escola,
            },
            {
                "key": "basico_6_17",
                "label": "Matrículas de 6 a 17 anos em relação à população residente estimada",
                "sub": "",
                "desc": "Matrículas de estudantes de 6 a 17 anos registradas nas escolas do município divididas pela população residente estimada da mesma faixa; o resultado pode superar 100% por causa da diferença de territorialidade.",
                "meta_label": "Meta PNE 2036",
                "compute": _calc_basico_6_17,
            },
            {
                "key": "basico_15_17",
                "label": "Matrículas da educação básica de estudantes de 15 a 17 anos em relação à população da faixa",
                "sub": "",
                "desc": "Matrículas da educação básica associadas à faixa de 15 a 17 anos, no município da escola, divididas pela população residente da faixa.",
                "meta_label": "Meta PNE 2036",
                "compute": _calc_basico_15_17,
            },
            {
                "key": "basico_integral",
                "label": "Alunos do público-alvo da ETI em jornada integral na rede pública",
                "sub": "",
                "desc": "Percentual de alunos da educação básica pública que pertencem ao público-alvo da Educação em Tempo Integral (ETI) e estão em jornada de tempo integral.",
                "meta_label": "Meta PNE 2031",
                "compute": _calc_basico_integral,
            },
            {
                "key": "escolas_integral",
                "label": "Escolas públicas com alunos em jornada de tempo integral",
                "sub": "",
                "desc": "Percentual de escolas públicas da educação básica que possuem, pelo menos, 25% dos alunos em jornada integral.",
                "meta_label": "Meta PNE 2031",
                "compute": _calc_escolas_integral,
            },
            {
                "key": "aee",
                "label": "Oferta de AEE e salas de recursos na educação especial",
                "sub": "",
                "desc": "Participação das turmas ou salas de AEE em relação ao total da educação especial no município.",
                "meta_label": INFORMATIVE_META_LABEL,
                "compute": _calc_aee,
                "tracks_goal": False,
            },
            {
                "key": "eja_integrada_educacao_profissional_percentual",
                "label": "Percentual das matrículas da EJA articuladas à educação profissional",
                "sub": "",
                "desc": "Percentual das matrículas da EJA articuladas à educação profissional no município.",
                "meta_label": "Referência intermediária PNE 2031",
                "presentationMode": "ratio-dual-milestone",
                "compute": _calc_eja_integrada_educacao_profissional,
                "tracks_goal": True,
                "value_mode": "percent",
            },
            {
                "key": "medio_tecnico_articulado_percentual",
                "label": "Matrículas técnicas integradas ou concomitantes em relação às matrículas do Ensino Médio",
                "sub": "",
                "desc": "Razão entre matrículas técnicas integradas ou concomitantes e matrículas do Ensino Médio; os agregados não identificam estudantes únicos e a referência de 50% é de acompanhamento.",
                "source": "INEP — Sinopse Estatística da Educação Básica.",
                "meta_label": "Meta PNE 2036",
                "compute": _calc_medio_tecnico_articulado_percentual,
                "show_in_cycle": True,
                "include_in_cycle_summary": False,
                "tracks_goal": True,
                "coverage": "aproximada",
                "value_mode": "percent",
            },
            {
                "key": "medio_tecnico_participacao_publica",
                "label": "Participação pública na expansão da EPT de nível médio desde 2025",
                "sub": "",
                "desc": "Participação da expansão líquida pública na expansão líquida total da Educação Profissional e Tecnológica de nível médio desde a base fixa de 2025.",
                "meta_label": "Meta PNE 2036",
                "compute": _calc_medio_tecnico_participacao_publica,
            },
            {
                "key": "subsequente_expansao",
                "label": "Expansão das matrículas em cursos técnicos subsequentes desde 2025",
                "sub": "",
                "desc": "Expansão das matrículas nos cursos técnicos subsequentes da Educação Profissional e Tecnológica de nível médio no município em relação à base fixa de 2025.",
                "meta_label": "Meta PNE 2036",
                "compute": _calc_subsequente_expansao,
            },
        ],
    },
    "escolaridade_populacao": {
        "label": "Escolaridade da População",
        "icon": "👥",
        "accent": "#2563eb",
        "items": [
            {
                "key": "alfabetizacao_pop_15_mais",
                "label": "Taxa de alfabetização da população de 15 anos ou mais",
                "sub": "",
                "desc": "Percentual da população de 15 anos ou mais alfabetizada, com base nos Censos Demográficos.",
                "meta_label": "Meta vigente do PNE",
                "compute": _calc_alfabetizacao_pop_15_mais,
            },
            {
                "key": "fundamental_concluido_18_mais",
                "label": "População de 18 anos ou mais com ensino fundamental concluído",
                "sub": "",
                "desc": "Percentual da população de 18 anos ou mais com ensino fundamental concluído, com base nos Censos Demográficos.",
                "meta_label": "Meta PNE 2036",
                "compute": _calc_fundamental_concluido_18_mais,
            },
            {
                "key": "fundamental_concluido_15_mais",
                "label": "População de 15 anos ou mais com ensino fundamental concluído",
                "sub": "",
                "desc": "Percentual da população de 15 anos ou mais com ensino fundamental concluído no Censo Demográfico 2022.",
                "meta_label": "Meta PNE 2036",
                "compute": _calc_fundamental_concluido_15_mais,
            },
            {
                "key": "fundamental_concluido_15_29",
                "label": "População de 15 a 29 anos com ensino fundamental concluído",
                "sub": "",
                "desc": "Percentual da população de 15 a 29 anos com ensino fundamental concluído, com base nos Censos Demográficos.",
                "meta_label": "Meta PNE 2036",
                "compute": _calc_fundamental_concluido_15_29,
            },
            {
                "key": "medio_concluido_18_mais",
                "label": "População de 18 anos ou mais com ensino médio concluído",
                "sub": "",
                "desc": "Percentual da população de 18 anos ou mais com ensino médio concluído, com base nos Censos Demográficos.",
                "meta_label": "Meta PNE 2036",
                "compute": _calc_medio_concluido_18_mais,
            },
            {
                "key": "medio_concluido_18_29",
                "label": "População de 18 a 29 anos com ensino médio concluído",
                "sub": "",
                "desc": "Percentual da população de 18 a 29 anos com ensino médio concluído, com base nos Censos Demográficos.",
                "meta_label": "Meta PNE 2036",
                "compute": _calc_medio_concluido_18_29,
            },
        ],
    },
    "rendimento": {
        "label": "Rendimento Escolar",
        "icon": "📈",
        "accent": "#10b981",
        "items": [
            {
                "key": "alfabetizacao",
                "label": "Estudantes alfabetizados na rede pública",
                "sub": "",
                "desc": "Percentual de estudantes alfabetizados na rede pública do município.",
                "meta_label": "Meta PNE 2036",
                "compute": _calc_alfabetizacao,
            },
            *[
                {
                    "key": result_key,
                    "label": (
                        "Desempenho em "
                        f"{SAEB_MATERIA_LABELS[config['materia']]} - "
                        f"{SAEB_ETAPA_LABELS[config['etapa']].lower()}"
                    ),
                    "sub": "",
                    "desc": (
                        "Percentual de estudantes nos níveis básico ou superior e adequado ou "
                        f"superior em {SAEB_MATERIA_LABELS[config['materia']]} - "
                        f"{SAEB_ETAPA_LABELS[config['etapa']].lower()}."
                    ),
                    "meta_label": "Meta PNE 2031",
                    "compute": (
                        lambda municipio,
                        materia=config["materia"],
                        etapa=config["etapa"]: _calc_saeb(
                            municipio, materia, "adequado", etapa
                        )
                    ),
                }
                for result_key, config in SAEB_DISPLAY_GROUPS.items()
            ],
            {
                "key": "idade_regular_quinto",
                "label": "Estudantes matriculados sem distorção — anos iniciais",
                "sub": "",
                "desc": "Percentual de estudantes matriculados sem distorção idade-série nos anos iniciais do ensino fundamental.",
                "meta_label": "Meta PNE 2036",
                "compute": lambda municipio: _calc_idade_regular(
                    municipio, "quinto_ano"
                ),
            },
            {
                "key": "idade_regular_nono",
                "label": "Estudantes matriculados sem distorção — anos finais",
                "sub": "",
                "desc": "Percentual de estudantes matriculados sem distorção idade-série nos anos finais do ensino fundamental.",
                "meta_label": "Meta PNE 2036",
                "compute": lambda municipio: _calc_idade_regular(municipio, "nono_ano"),
            },
            {
                "key": "idade_regular_medio",
                "label": "Estudantes matriculados sem distorção — Ensino Médio",
                "sub": "",
                "desc": "Percentual de estudantes matriculados sem distorção idade-série no ensino médio.",
                "meta_label": "Meta PNE 2036",
                "compute": lambda municipio: _calc_idade_regular(
                    municipio, "ensino_medio"
                ),
            },
        ],
    },
    "corpo_docente": {
        "label": "Corpo Docente",
        "icon": "👩‍🏫",
        "accent": "#f59e0b",
        "items": [
            {
                "key": "adequacao_ai",
                "label": "Docentes com formação adequada nos anos iniciais",
                "sub": "",
                "desc": "Percentual de docentes com formação adequada nos anos iniciais do ensino fundamental.",
                "meta_label": "Meta PNE 2036",
                "compute": lambda municipio: _calc_adequacao(
                    municipio, "anos_iniciais"
                ),
            },
            {
                "key": "adequacao_af",
                "label": "Docentes com formação adequada nos anos finais",
                "sub": "",
                "desc": "Percentual de docentes com formação adequada nos anos finais do ensino fundamental.",
                "meta_label": "Meta PNE 2036",
                "compute": lambda municipio: _calc_adequacao(municipio, "anos_finais"),
            },
            {
                "key": "adequacao_em",
                "label": "Docentes com formação adequada no ensino médio",
                "sub": "",
                "desc": "Percentual de docentes com formação adequada no ensino médio.",
                "meta_label": "Meta PNE 2036",
                "compute": lambda municipio: _calc_adequacao(municipio, "ensino_medio"),
            },
            {
                "key": "pos_graduacao",
                "label": "Docentes da educação básica com pós-graduação",
                "sub": "",
                "desc": "Percentual de docentes da educação básica com especialização, mestrado ou doutorado.",
                "meta_label": "Meta PNE 2036",
                "compute": _calc_pos_graduacao,
            },
            {
                "key": "rendimento_magisterio",
                "label": "Rendimento do magistério em relação a outros profissionais com nível superior",
                "sub": "",
                "desc": "Relação percentual entre o rendimento bruto médio mensal dos profissionais do magistério da educação básica, com nível superior completo, e o rendimento bruto médio mensal dos demais profissionais assalariados, com nível superior completo.",
                "meta_label": "Meta PNE 2036",
                "compute": _calc_rendimento_magisterio,
            },
            {
                "key": "temporarios",
                "label": "Docentes da rede pública com contrato temporário",
                "sub": "",
                "desc": "Percentual de docentes da rede pública com vínculo temporário.",
                "meta_label": "Meta PNE 2031",
                "compute": _calc_temporarios,
            },
        ],
    },
    "infraestrutura": {
        "label": "Infraestrutura Escolar",
        "icon": "🏫",
        "accent": "#3b82f6",
        "summary_mode": "count",
        "summary_text": "indicadores temáticos",
        "items": [
            {
                "key": item["key"],
                "label": item["label"],
                "sub": item["sub"],
                "desc": item["desc"],
                "meta_label": item.get("meta_label", "Visualização informativa"),
                "tracks_goal": item.get("tracks_goal", False),
                "compute": (
                    lambda cfg: (
                        lambda municipio: _calc_infra_totalizado(municipio, cfg)
                    )
                )(item),
            }
            for item in INFRA_ITEMS
        ],
    },
}

def _apply_canonical_indicator_catalog():
    for category in INDICADORES.values():
        for item in category["items"]:
            indicator = get_indicator(item["key"])
            if indicator is None:
                continue
            formula = get_formula_for_indicator(item["key"]) or {}
            reference = _contract_reference(item["key"])
            item["label"] = indicator["publicTitle"]
            item["desc"] = (
                indicator.get("publicDescription")
                or formula.get("description")
                or item.get("desc")
            )
            item["formulaId"] = indicator["formulaId"]
            item["sourceIds"] = list(indicator["sourceIds"])
            if reference is not None:
                item["meta_label"] = (
                    f"Meta PNE {reference['year']}"
                    if reference["kind"] == "legal" and reference.get("year")
                    else reference["label"]
                )
            else:
                context = get_relation_context_for_indicator(item["key"])
                relation = (context or {}).get("relation") or {}
                if relation.get("mode") in {"complementary", "hidden"}:
                    item.pop("meta_label", None)
                    item["tracks_goal"] = False
            context = get_relation_context_for_indicator(item["key"])
            relation = (context or {}).get("relation") or {}
            if relation:
                item["goalId"] = relation["goalId"]
                item["monitoring_mode"] = relation["mode"]
                if relation["mode"] != "progress":
                    item["include_in_cycle_summary"] = False


_apply_canonical_indicator_catalog()

CATEGORY_ORDER = [
    "atendimento",
    "rendimento",
    "corpo_docente",
    "infraestrutura",
    "escolaridade_populacao",
]

def _results_cache_bucket():
    ttl_seconds = get_data_cache_ttl_seconds()
    if ttl_seconds <= 0:
        return None
    return int(time.time() // ttl_seconds)

def _load_precomputed_metric_frame(cache_bucket):
    return _safe_load(load_pne_2026_2036_metricas_data)

def _precomputed_metric_frame():
    cache_bucket = _results_cache_bucket()
    if cache_bucket is None:
        return _safe_load(load_pne_2026_2036_metricas_data)
    return _load_precomputed_metric_frame(cache_bucket)

def _build_precomputed_result(
    municipio,
    indicador,
    *,
    meta,
    meta_label,
    direction=GOAL_AT_LEAST,
    target_start_year=TARGET_START_YEAR,
    target_end_year=TARGET_END_YEAR,
    tracks_goal=True,
):
    df = _precomputed_metric_frame()
    if df.empty or "municipio" not in df.columns or "indicador" not in df.columns:
        return None
    if "ano" not in df.columns or "valor" not in df.columns:
        return None

    dff = df[(df["municipio"] == municipio) & (df["indicador"] == indicador)].copy()
    if dff.empty:
        return None

    dff["ano"] = pd.to_numeric(dff["ano"], errors="coerce")
    dff["valor"] = pd.to_numeric(dff["valor"], errors="coerce")
    dff = dff.dropna(subset=["ano", "valor"])
    if dff.empty:
        return None

    return _build_result(
        dff[["ano", "valor"]],
        meta,
        direction=direction,
        meta_label=meta_label,
        target_start_year=target_start_year,
        target_end_year=target_end_year,
        tracks_goal=tracks_goal,
    )


def _apply_canonical_reference(indicator_key, result):
    if not isinstance(result, dict):
        return result
    context = get_relation_context_for_indicator(
        indicator_key,
        result.get("end_year") or TARGET_END_YEAR,
    )
    relation = (context or {}).get("relation") or {}
    if relation.get("mode") in {"complementary", "hidden"}:
        updated = dict(result)
        updated["meta"] = None
        updated.pop("meta_label", None)
        updated["tracks_goal"] = False
        updated["distance"] = None
        updated["atingida"] = False
        updated["deadline"] = None
        updated["reference_kind"] = None
        updated["reference_id"] = None
        updated["reference_validation_status"] = None
        return updated
    reference = _contract_reference(
        indicator_key,
        result.get("end_year") or TARGET_END_YEAR,
    )
    if reference is None:
        return result

    updated = dict(result)
    updated["meta"] = float(reference["value"])
    updated["meta_label"] = (
        f"Meta PNE {reference['year']}"
        if reference["kind"] == "legal" and reference.get("year")
        else reference["label"]
    )
    updated["direction"] = reference["direction"]
    updated["reference_kind"] = reference["kind"]
    updated["reference_id"] = reference["referenceId"]
    updated["reference_validation_status"] = reference["validationStatus"]
    updated["deadline"] = reference.get("year")
    end_value = updated.get("end_value")
    if end_value is None or pd.isna(end_value):
        updated["distance"] = None
        updated["atingida"] = False
        return updated

    distance = (
        float(reference["value"]) - float(end_value)
        if reference["direction"] == GOAL_AT_MOST
        else float(end_value) - float(reference["value"])
    )
    updated["distance"] = distance
    updated["atingida"] = _goal_achieved(distance)
    return updated


def _attach_trends(results):
    item_lookup = {
        item["key"]: item
        for category in INDICADORES.values()
        for item in category["items"]
    }
    enriched = {}
    for indicator_key, result in results.items():
        result = _apply_canonical_reference(indicator_key, result)
        item = item_lookup.get(indicator_key, {})
        if item.get("monitoring_mode") in {
            "approximate_reference",
            "complementary",
            "hidden",
        }:
            enriched[indicator_key] = result
            continue
        value_type = item.get("value_mode") or result.get("value_mode", "percent")
        enriched[indicator_key] = attach_trend(
            result,
            value_type=value_type,
            methodology_break_years=item.get("methodology_break_years"),
            observation_interval_years=(
                2 if indicator_key.startswith("saeb_") else 1
            ),
        )
    return enriched

def _calculate_results_cached(municipio, cache_bucket):
    results = {
        item["key"]: item["compute"](municipio)
        for category in INDICADORES.values()
        for item in category["items"]
        if item["key"] not in BATCHED_RESULT_KEYS
    }
    results.update(_calculate_saeb_results(municipio))
    results.update(_calculate_idade_regular_results(municipio))
    results.update(_calculate_adequacao_results(municipio))
    results.update(_calculate_infra_results(municipio))
    return _attach_trends(results)

def _calculate_results(municipio):
    cache_bucket = _results_cache_bucket()
    if cache_bucket is None:
        return _calculate_results_cached.__wrapped__(municipio, None)
    return _calculate_results_cached(municipio, cache_bucket)

def _calculate_results_for_indicators_cached(municipio, indicator_keys, cache_bucket):
    """Calcula somente os itens selecionados para a exportação rápida.

    SAEB, idade regular, adequação e infraestrutura continuam sendo calculados por
    grupo porque as respectivas consultas retornam vários resultados de uma vez.
    Apenas as chaves pedidas são mantidas no payload final.
    """

    selected_keys = set(indicator_keys)
    results = {
        item["key"]: item["compute"](municipio)
        for category in INDICADORES.values()
        for item in category["items"]
        if item["key"] in selected_keys and item["key"] not in BATCHED_RESULT_KEYS
    }
    if selected_keys & set(SAEB_DISPLAY_GROUPS):
        results.update(_calculate_saeb_results(municipio))
    if selected_keys & set(IDADE_REGULAR_RESULT_GROUPS):
        results.update(_calculate_idade_regular_results(municipio))
    if selected_keys & set(ADEQUACAO_RESULT_GROUPS):
        results.update(_calculate_adequacao_results(municipio))
    if selected_keys & INFRA_RESULT_KEYS:
        results.update(_calculate_infra_results(municipio))
    return _attach_trends(
        {key: value for key, value in results.items() if key in selected_keys}
    )

def _calculate_results_for_indicators(municipio, indicator_keys):
    normalized_keys = tuple(dict.fromkeys(indicator_keys))
    cache_bucket = _results_cache_bucket()
    if cache_bucket is None:
        return _calculate_results_for_indicators_cached.__wrapped__(
            municipio, normalized_keys, None
        )
    return _calculate_results_for_indicators_cached(
        municipio, normalized_keys, cache_bucket
    )

def _subsequente_distance_value(result):
    end_value = result.get("end_value")
    meta = result.get("meta")
    if end_value is None or meta is None or pd.isna(end_value) or pd.isna(meta):
        return None
    if float(end_value) < 0:
        return float(meta)
    return max(float(meta) - float(end_value), 0.0)
