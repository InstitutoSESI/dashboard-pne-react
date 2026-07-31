"""Referência estadual do RS para o ciclo PNE 2026-2036.

Este módulo mantém a regra estadual fora da camada de apresentação. As razões
percentuais são calculadas somente depois da consolidação dos numeradores e
denominadores municipais válidos; portanto, não há média de percentuais
municipais em nenhuma etapa.
"""

from __future__ import annotations

import math
from typing import Any, Callable, Mapping

import pandas as pd


STATE_CODE = "RS"
STATE_NAME = "Rio Grande do Sul"
EXPECTED_RS_MUNICIPALITIES = 497
REFERENCE_START_YEAR = 2015
REFERENCE_END_YEAR = 2025
CYCLE_BASELINE_YEAR = 2025
CENSUS_YEARS = (2010, 2022)
METHODOLOGY_VERSION = "pne2026-rs-reference-v3"
STATE_PROJECTION_MINIMUM_OBSERVATIONS = 5

COMPARABLE = "comparable"
UNAVAILABLE = "unavailable"
METHODOLOGY_PENDING = "methodology_pending"

PUBLIC_DEPENDENCIES = ("federal", "estadual", "municipal")


def _metadata(
    indicator_id: str,
    *,
    aggregation_method: str,
    numerator_definition: str,
    denominator_definition: str,
    filters: Mapping[str, Any] | None,
    source: str,
    source_type: str,
    notes: str,
    comparison_status: str = UNAVAILABLE,
) -> dict[str, Any]:
    return {
        "indicator_id": indicator_id,
        "aggregation_method": aggregation_method,
        "numerator_definition": numerator_definition,
        "denominator_definition": denominator_definition,
        "filters": dict(filters or {}),
        "source": source,
        "source_type": source_type,
        "null_policy": (
            "Nulos não são zero; somente pares válidos entram na razão. "
            "Denominador zero produz valor nulo."
        ),
        "methodology_version": METHODOLOGY_VERSION,
        "comparison_status": comparison_status,
        "unit": "percent",
        "compatibility": {
            "indicatorRule": "same_indicator_id_required",
            "formulaStatus": "curated_equivalent",
            "yearRule": "same_year_required",
            "rangeStatus": "curated_equivalent",
            "stageStatus": "curated_equivalent",
            "unit": "percent",
            "universeStatus": "curated_equivalent",
            "administrativeDependenceStatus": "registry_filters_required",
            "aggregationRuleStatus": "curated_equivalent",
            "methodologyVersion": METHODOLOGY_VERSION,
            "territorialBasisStatus": "curated_equivalent",
        },
        "notes": notes,
    }


def _ratio_config(
    indicator_id: str,
    *,
    loader_key: str,
    numerator_column: str,
    denominator_column: str,
    numerator_definition: str,
    denominator_definition: str,
    filters: Mapping[str, Any] | None = None,
    denominator_aggregation: str = "sum",
    source: str = "INEP Censo Escolar",
    source_type: str = "derived_from_raw_counts",
    notes: str = "",
    allowed_years: tuple[int, ...] | None = None,
    coverage: str | None = None,
    allow_projection: bool = True,
) -> dict[str, Any]:
    return {
        **_metadata(
            indicator_id,
            aggregation_method="ratio_of_sums",
            numerator_definition=numerator_definition,
            denominator_definition=denominator_definition,
            filters=filters,
            source=source,
            source_type=source_type,
            notes=notes,
        ),
        "loader_key": loader_key,
        "numerator_column": numerator_column,
        "denominator_column": denominator_column,
        "denominator_aggregation": denominator_aggregation,
        "allowed_years": allowed_years,
        "coverage": coverage,
        "allow_projection": allow_projection,
    }


RATIO_CONFIGS: dict[str, dict[str, Any]] = {
    "creche": _ratio_config(
        "creche",
        loader_key="creche",
        numerator_column="mat_basico_0_3",
        denominator_column="pop_0_3",
        numerator_definition="Matrículas da educação infantil de 0 a 3 anos.",
        denominator_definition="População de 0 a 3 anos do município.",
        denominator_aggregation="max",
        source="INEP Censo Escolar + estimativas populacionais oficiais",
        notes="Mesmo ano e população de referência do indicador municipal.",
    ),
    "pre_escola": _ratio_config(
        "pre_escola",
        loader_key="pre_escola",
        numerator_column="mat_infantil_pre",
        denominator_column="pop_4_5",
        numerator_definition="Matrículas da educação infantil de 4 a 5 anos.",
        denominator_definition="População de 4 a 5 anos do município.",
        denominator_aggregation="max",
        source="INEP Censo Escolar + estimativas populacionais oficiais",
        notes="Mesmo ano e população de referência do indicador municipal.",
    ),
    "basico_6_17": _ratio_config(
        "basico_6_17",
        loader_key="basico_6_17",
        numerator_column="mat_basico_6_17",
        denominator_column="pop_6_17",
        numerator_definition="Matrículas da educação básica de 6 a 17 anos.",
        denominator_definition="População de 6 a 17 anos do município.",
        denominator_aggregation="max",
        source="INEP Censo Escolar + estimativas populacionais oficiais",
        notes="Mesmo ano e população de referência do indicador municipal.",
    ),
    "basico_15_17": _ratio_config(
        "basico_15_17",
        loader_key="basico_15_17",
        numerator_column="mat_basico_15_17",
        denominator_column="pop_15_17",
        numerator_definition=(
            "Matrículas da educação básica associadas à faixa de 15 a 17 anos, "
            "agregadas pelo município da escola."
        ),
        denominator_definition="População de 15 a 17 anos do município.",
        denominator_aggregation="max",
        source="INEP Censo Escolar + estimativas populacionais oficiais",
        notes="Somar numeradores e denominadores; não substituir por média de percentuais.",
    ),
    "basico_integral": _ratio_config(
        "basico_integral",
        loader_key="basico_integral",
        numerator_column="mat_basico_integral",
        denominator_column="mat_basico",
        numerator_definition="Matrículas públicas da educação básica em jornada integral.",
        denominator_definition="Matrículas públicas da educação básica alvo da ETI.",
        filters={"dependencia": "publica"},
        notes="Filtro de dependência pública preservado.",
    ),
    "eja_integrada_educacao_profissional_percentual": _ratio_config(
        "eja_integrada_educacao_profissional_percentual",
        loader_key="eja",
        numerator_column="mat_eja_integrada_educacao_profissional_calculada",
        denominator_column="mat_eja_denominador_calculado",
        numerator_definition=(
            "Curso técnico integrado à EJA + FIC integrado à EJA fundamental + "
            "FIC integrado à EJA médio."
        ),
        denominator_definition="Matrículas da EJA fundamental + matrículas da EJA médio.",
        source="INEP — Sinopse Estatística da Educação Básica, tabelas EJA 1.35 e Educação Profissional 1.30/1.42.",
        notes="Componentes brutos agregados antes da razão; denominador zero permanece nulo.",
    ),
    "medio_tecnico_articulado_percentual": _ratio_config(
        "medio_tecnico_articulado_percentual",
        loader_key="medio_tecnico_articulado",
        numerator_column="mat_articulado_total",
        denominator_column="mat_medio",
        numerator_definition=(
            "Matrículas em cursos técnicos integrados ou concomitantes ao ensino médio."
        ),
        denominator_definition="Matrículas totais do ensino médio.",
        source="INEP — Sinopse Estatística da Educação Básica.",
        notes=(
            "Soma integrada + concomitante antes da razão. O agregado não identifica "
            "estudantes únicos; a referência de 50% é apenas de acompanhamento."
        ),
        allowed_years=tuple(range(2015, 2026)),
        coverage="aproximada",
        allow_projection=False,
    ),
    "pos_graduacao": _ratio_config(
        "pos_graduacao",
        loader_key="pos_graduacao",
        numerator_column="docentes_pos_graduacao",
        denominator_column="total_docentes",
        numerator_definition="Docentes da educação básica com pós-graduação.",
        denominator_definition="Total de docentes da educação básica.",
        filters={"dependencia": "total"},
        notes="Filtro de dependência total preservado.",
    ),
    "temporarios": _ratio_config(
        "temporarios",
        loader_key="temporarios",
        numerator_column="docentes_temporarios",
        denominator_column="total_docentes",
        numerator_definition="Docentes públicos com vínculo temporário.",
        denominator_definition="Total de docentes da rede pública.",
        filters={"dependencia": "publica"},
        notes="Filtro de rede pública preservado.",
    ),
}


INFRA_SCHOOL_CONFIGS: dict[str, dict[str, Any]] = {
    "internet": {"field": "escolas_com_internet", "public_only": False},
    "internet_alunos": {"field": "escolas_com_internet_alunos", "public_only": False},
    "internet_aprendizagem": {
        "field": "escolas_com_internet_aprendizagem",
        "public_only": False,
    },
    "internet_comunidade": {"field": "escolas_com_internet_comunidade", "public_only": False},
    "acesso_internet_computador": {
        "field": "escolas_com_acesso_internet_computador",
        "public_only": False,
    },
    "acesso_internet_disp_pessoais": {
        "field": "escolas_com_acesso_internet_disp_pessoais",
        "public_only": False,
    },
    "rede_local": {"field": "escolas_com_rede_local", "public_only": False},
    "rede_wireless": {
        "fields": ("escolas_com_rede_local_wireless", "escolas_com_rede_local_cabo_wireless"),
        "public_only": False,
    },
    "banda_larga": {"field": "escolas_com_banda_larga", "public_only": False},
    "educacao_ambiental": {"field": "escolas_com_educacao_ambiental", "public_only": False},
    "conselho_escolar": {
        "field": "escolas_com_orgao_conselho_escolar",
        "public_only": True,
    },
    "proposta_pedagogica": {
        "field": "tp_proposta_pedagogica",
        "classifier": "proposal",
        "public_only": True,
    },
    "salas_climatizadas": {
        "field": "qt_salas_utiliza_climatizadas",
        "denominator_field": "qt_salas_utilizadas",
        "public_only": False,
    },
    "salas_acessiveis": {
        "field": "qt_salas_utilizadas_acessiveis",
        "denominator_field": "qt_salas_utilizadas",
        "public_only": False,
    },
    "desktop_aluno": {"field": "escolas_com_desktop_aluno", "public_only": False},
    "comp_portatil_aluno": {"field": "escolas_com_comp_portatil_aluno", "public_only": False},
    "tablet_aluno": {"field": "escolas_com_tablet_aluno", "public_only": False},
}


INFRA_DEFINITIONS = {
    "all_school": "Escolas da educação básica do Censo Escolar elegíveis no ano.",
    "public_school": (
        "Escolas públicas (federal, estadual e municipal) com pelo menos uma "
        "matrícula de educação básica no ano."
    ),
}


CENSUS_CONFIGS: dict[str, dict[str, Any]] = {
    "alfabetizacao_pop_15_mais": {
        "loader_key": "censo_alfabetizacao",
        "numerator_column": "alfabetizadas_15_mais",
        "denominator_column": "total_15_mais",
        "numerator_definition": "População de 15 anos ou mais alfabetizada.",
        "denominator_definition": "População total de 15 anos ou mais.",
    },
    "fundamental_concluido_18_mais": {
        "loader_key": "censo_fundamental_18",
        "numerator_column": "populacao_18_mais_ensino_fundamental_concluido",
        "denominator_column": "populacao_18_mais_total",
        "numerator_definition": "População de 18 anos ou mais com ensino fundamental concluído.",
        "denominator_definition": "População total de 18 anos ou mais.",
    },
    "fundamental_concluido_15_29": {
        "loader_key": "censo_fundamental_15_29",
        "numerator_column": "populacao_15_29_ensino_fundamental_concluido",
        "denominator_column": "populacao_15_29_total",
        "numerator_definition": "População de 15 a 29 anos com ensino fundamental concluído.",
        "denominator_definition": "População total de 15 a 29 anos.",
    },
    "fundamental_concluido_15_mais": {
        "loader_key": "censo_fundamental_15_mais",
        "numerator_column": "populacao_15_mais_ensino_fundamental_concluido",
        "denominator_column": "populacao_15_mais_total",
        "numerator_definition": "População de 15 anos ou mais com ensino fundamental concluído.",
        "denominator_definition": "População total de 15 anos ou mais.",
    },
    "medio_concluido_18_mais": {
        "loader_key": "censo_medio_18",
        "numerator_column": "populacao_18_mais_ensino_medio_concluido",
        "denominator_column": "populacao_18_mais_total",
        "numerator_definition": "População de 18 anos ou mais com ensino médio concluído.",
        "denominator_definition": "População total de 18 anos ou mais.",
    },
    "medio_concluido_18_29": {
        "loader_key": "censo_medio_18_29",
        "numerator_column": "populacao_18_29_ensino_medio_concluido",
        "denominator_column": "populacao_18_29_total",
        "numerator_definition": "População de 18 a 29 anos com ensino médio concluído.",
        "denominator_definition": "População total de 18 a 29 anos.",
    },
}


BLOCKED_REASONS: dict[str, str] = {
    "aee": (
        "Sem referência estadual: a série municipal tem denominador metodologicamente "
        "inadequado e pode ultrapassar 100%."
    ),
    "eja_integrada_educacao_profissional": (
        "Comparação bloqueada até município e RS usarem a mesma razão de numerador "
        "e denominador."
    ),
    "alfabetizacao": "Fonte municipal sem série estadual comparável no pipeline.",
    "idade_regular_quinto": "Indicador de idade regular não será reconstruído por média municipal.",
    "idade_regular_nono": "Indicador de idade regular não será reconstruído por média municipal.",
    "idade_regular_medio": "Indicador de idade regular não será reconstruído por média municipal.",
    "adequacao_ai": "Indicador de adequação docente sem referência estadual habilitada.",
    "adequacao_af": "Indicador de adequação docente sem referência estadual habilitada.",
    "adequacao_em": "Indicador de adequação docente sem referência estadual habilitada.",
    "rendimento_magisterio": "Rendimento do magistério sem denominadores agregáveis no pipeline.",
}

for _materia in ("matematica", "portugues"):
    for _etapa in ("anos_iniciais", "anos_finais", "ensino_medio"):
        BLOCKED_REASONS[f"saeb_{_materia}_{_etapa}"] = (
            "SAEB não será convertido por média municipal nem ponderado por matrículas; "
            "referência estadual bloqueada."
        )


def _blocked_metadata(indicator_id: str, reason: str) -> dict[str, Any]:
    return _metadata(
        indicator_id,
        aggregation_method="not_available",
        numerator_definition="Não habilitado.",
        denominator_definition="Não habilitado.",
        filters={},
        source="Sem fonte estadual comparável habilitada",
        source_type="methodology_pending",
        notes=reason,
        comparison_status=METHODOLOGY_PENDING,
    )


def build_registry() -> dict[str, dict[str, Any]]:
    """Retorna o registro completo, inclusive indicadores bloqueados."""

    registry: dict[str, dict[str, Any]] = {}
    registry.update({key: dict(value) for key, value in RATIO_CONFIGS.items()})

    registry["escolas_integral"] = _metadata(
        "escolas_integral",
        aggregation_method="school_level_classification_then_ratio_of_sums",
        numerator_definition=(
            "Escolas públicas elegíveis em que cada escola, individualmente, tem "
            "pelo menos 25% dos alunos em jornada integral."
        ),
        denominator_definition=(
            "Escolas públicas elegíveis com par válido de matrículas básicas e "
            "matrículas integrais."
        ),
        filters={"dependencia": list(PUBLIC_DEPENDENCIES), "mat_basico": ">= 1"},
        source="INEP Censo Escolar — registro por escola",
        source_type="school_level_classification",
        notes=(
            "A classificação de 25% é feita escola a escola antes da soma estadual; "
            "nunca sobre o total estadual."
        ),
    )

    for key, config in INFRA_SCHOOL_CONFIGS.items():
        public_only = bool(config.get("public_only"))
        is_room = "denominator_field" in config
        if is_room:
            numerator_definition = f"Soma de {config['field']} nas salas com par válido."
            denominator_definition = f"Soma de {config['denominator_field']} nas salas elegíveis."
            method = "ratio_of_sums_from_school_records"
        elif config.get("classifier") == "proposal":
            numerator_definition = "Escolas elegíveis com resposta válida (código 0 ou 1)."
            denominator_definition = INFRA_DEFINITIONS["public_school"]
            method = "ratio_of_valid_school_records"
        else:
            numerator_definition = f"Escolas elegíveis com {config.get('field', 'recurso')} informado."
            denominator_definition = (
                INFRA_DEFINITIONS["public_school"]
                if public_only
                else INFRA_DEFINITIONS["all_school"]
            )
            method = "ratio_of_valid_school_records"
        registry[key] = _metadata(
            key,
            aggregation_method=method,
            numerator_definition=numerator_definition,
            denominator_definition=denominator_definition,
            filters=(
                {"dependencia": list(PUBLIC_DEPENDENCIES), "mat_basico": ">= 1"}
                if public_only
                else {"universo": "todas as escolas do Censo Escolar"}
            ),
            source="INEP Censo Escolar — registro por escola",
            source_type="school_level_reconstruction",
            notes=(
                "Cobertura do denominador usa o universo estadual das escolas/salas, "
                "não somente a contagem de municípios."
            ),
        )

    for key, config in CENSUS_CONFIGS.items():
        registry[key] = _metadata(
            key,
            aggregation_method="ratio_of_sums_census_snapshot",
            numerator_definition=config["numerator_definition"],
            denominator_definition=config["denominator_definition"],
            filters={"anos": list(CENSUS_YEARS)},
            source="IBGE Censo Demográfico + população por idade oficial",
            source_type="census_raw_count_reconstruction",
            notes=(
                "Somente os snapshots de 2010 e 2022 são válidos; não interpolar, "
                "projetar nem criar série anual contínua."
            ),
        )

    registry["medio_tecnico_participacao_publica"] = _metadata(
        "medio_tecnico_participacao_publica",
        aggregation_method="state_net_expansion_from_2025",
        numerator_definition=(
            "Total estadual público atual menos total estadual público em 2025."
        ),
        denominator_definition=(
            "Total estadual de EPT atual menos total estadual de EPT em 2025."
        ),
        filters={
            "ano_base": CYCLE_BASELINE_YEAR,
            "dependencias_publicas": list(PUBLIC_DEPENDENCIES),
        },
        source="INEP Censo Escolar — EPT de nível médio",
        source_type="state_series_growth",
        notes=(
            "Agrega primeiro os totais estaduais de EPT e calcula diferenças líquidas "
            "contra a base fixa de 2025."
        ),
    )
    registry["subsequente_expansao"] = _metadata(
        "subsequente_expansao",
        aggregation_method="state_total_growth_from_2025",
        numerator_definition=(
            "Total estadual atual de matrículas técnicas subsequentes menos o total de 2025."
        ),
        denominator_definition="Total estadual de matrículas técnicas subsequentes em 2025.",
        filters={"ano_base": CYCLE_BASELINE_YEAR},
        source="INEP Censo Escolar — EPT de nível médio",
        source_type="state_series_growth",
        notes=(
            "Base estadual fixa em 2025; base zero gera valor nulo. A cobertura da base "
            "e do ano corrente é registrada para validar comparabilidade."
        ),
    )

    for key, reason in BLOCKED_REASONS.items():
        registry[key] = _blocked_metadata(key, reason)

    return registry


def _is_finite(value: Any) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _number_or_none(value: Any) -> float | None:
    if not _is_finite(value):
        return None
    return float(value)


def _apply_filters(frame: pd.DataFrame, filters: Mapping[str, Any] | None) -> pd.DataFrame:
    dff = frame.copy()
    for column, value in (filters or {}).items():
        if column not in dff.columns:
            return dff.iloc[0:0].copy()
        if isinstance(value, (list, tuple, set, frozenset)):
            dff = dff[dff[column].isin(value)]
        else:
            dff = dff[dff[column] == value]
    return dff


def _aggregate_series(series: pd.Series, method: str) -> Any:
    numeric = pd.to_numeric(series, errors="coerce")
    if method == "sum":
        return numeric.sum(min_count=1)
    if method == "max":
        return numeric.max(skipna=True)
    if method == "min":
        return numeric.min(skipna=True)
    if method == "mean":
        return numeric.mean(skipna=True)
    raise ValueError(f"Agregação não suportada: {method}")


def _coverage_percent(valid_value: Any, universe_value: Any) -> float | None:
    valid_number = _number_or_none(valid_value)
    universe_number = _number_or_none(universe_value)
    if valid_number is None or universe_number is None or universe_number <= 0:
        return None
    return 100.0 * valid_number / universe_number


def _record_notes(base_notes: str, extra_notes: list[str]) -> str:
    values = [str(value).strip() for value in [base_notes, *extra_notes] if str(value).strip()]
    return " ".join(dict.fromkeys(values))


def aggregate_ratio_of_sums(
    frame: pd.DataFrame,
    numerator_column: str,
    denominator_column: str,
    *,
    indicator_id: str = "",
    filters: Mapping[str, Any] | None = None,
    numerator_aggregation: str = "sum",
    denominator_aggregation: str = "sum",
    year_column: str = "ano",
    municipality_column: str = "municipio",
    denominator_universe_column: str | None = None,
    municipalities_expected: int = EXPECTED_RS_MUNICIPALITIES,
    base_notes: str = "",
) -> list[dict[str, Any]]:
    """Consolida município/ano e calcula a razão estadual depois das somas.

    A função deixa explícita a exclusão de pares incompletos. O campo opcional
    ``denominator_universe_column`` permite medir a cobertura do denominador
    original (por exemplo, salas ou escolas elegíveis), sem confundi-la com a
    cobertura de municípios.
    """

    if frame is None or frame.empty:
        return []
    required = {year_column, municipality_column, numerator_column, denominator_column}
    if not required.issubset(frame.columns):
        return []

    dff = _apply_filters(frame, filters)
    if dff.empty:
        return []
    dff = dff.copy()
    dff[year_column] = pd.to_numeric(dff[year_column], errors="coerce")
    dff[numerator_column] = pd.to_numeric(dff[numerator_column], errors="coerce")
    dff[denominator_column] = pd.to_numeric(dff[denominator_column], errors="coerce")
    dff = dff.dropna(subset=[year_column, municipality_column]).copy()
    if dff.empty:
        return []
    dff[year_column] = dff[year_column].astype(int)
    dff[municipality_column] = dff[municipality_column].astype(str)

    if denominator_universe_column is None:
        denominator_universe_column = denominator_column
    if denominator_universe_column not in dff.columns:
        dff[denominator_universe_column] = dff[denominator_column]
    dff[denominator_universe_column] = pd.to_numeric(
        dff[denominator_universe_column], errors="coerce"
    )

    group_columns = [municipality_column, year_column]
    all_groups = dff[group_columns].drop_duplicates().copy()
    valid_pair = dff[numerator_column].notna() & dff[denominator_column].notna()
    valid = dff.loc[valid_pair].copy()

    if valid.empty:
        municipal = all_groups.copy()
        municipal[numerator_column] = pd.NA
        municipal[denominator_column] = pd.NA
    else:
        municipal = (
            valid.groupby(group_columns, as_index=False)
            .agg(
                {
                    numerator_column: numerator_aggregation,
                    denominator_column: denominator_aggregation,
                }
            )
        )
        municipal = all_groups.merge(municipal, on=group_columns, how="left")

    universe = (
        dff.groupby(group_columns, as_index=False)[denominator_universe_column]
        .agg(lambda values: _aggregate_series(values, denominator_aggregation))
        .rename(columns={denominator_universe_column: "__denominator_universe"})
    )
    municipal = municipal.merge(universe, on=group_columns, how="left")

    records: list[dict[str, Any]] = []
    for year, year_frame in municipal.groupby(year_column, sort=True):
        pair_mask = year_frame[numerator_column].notna() & year_frame[denominator_column].notna()
        valid_frame = year_frame.loc[pair_mask]
        numerator = _number_or_none(
            valid_frame[numerator_column].sum(min_count=1) if not valid_frame.empty else None
        )
        denominator = _number_or_none(
            valid_frame[denominator_column].sum(min_count=1) if not valid_frame.empty else None
        )
        universe_value = _number_or_none(
            year_frame["__denominator_universe"].sum(min_count=1)
        )
        municipalities_valid = int(valid_frame[municipality_column].nunique())
        value = (
            None
            if numerator is None or denominator is None or denominator <= 0
            else 100.0 * numerator / denominator
        )
        extra_notes: list[str] = []
        if valid_frame.empty:
            extra_notes.append("Sem par numerador/denominador válido no ano.")
        if denominator is not None and denominator <= 0:
            extra_notes.append("Denominador estadual zero ou não positivo; valor nulo.")
        if municipalities_valid < municipalities_expected:
            extra_notes.append(
                f"Pares válidos em {municipalities_valid} de {municipalities_expected} municípios."
            )
        records.append(
            {
                "indicator_id": indicator_id,
                "year": int(year),
                "value": value,
                "numerator": numerator,
                "denominator": denominator,
                "aggregation_method": "ratio_of_sums",
                "municipalities_valid": municipalities_valid,
                "municipalities_expected": int(municipalities_expected),
                "municipal_coverage_percent": (
                    100.0 * municipalities_valid / municipalities_expected
                    if municipalities_expected > 0
                    else None
                ),
                "denominator_coverage_percent": _coverage_percent(
                    denominator, universe_value
                ),
                "comparison_status": COMPARABLE if value is not None else UNAVAILABLE,
                "notes": _record_notes(base_notes, extra_notes),
            }
        )
    return records


def _add_common_series_fields(
    records: list[dict[str, Any]],
    metadata: Mapping[str, Any],
    *,
    methodology_version: str = METHODOLOGY_VERSION,
) -> list[dict[str, Any]]:
    result = []
    for record in records:
        result.append(
            {
                **record,
                "source": metadata["source"],
                "source_type": metadata["source_type"],
                "methodology_version": methodology_version,
            }
        )
    return result


def _build_school_ratio_records(
    frame: pd.DataFrame,
    *,
    indicator_id: str,
    config: Mapping[str, Any],
    municipalities_expected: int,
) -> list[dict[str, Any]]:
    if frame is None or frame.empty or not {"ano", "municipio"}.issubset(frame.columns):
        return []
    dff = frame.copy()
    dff["ano"] = pd.to_numeric(dff["ano"], errors="coerce")
    dff = dff.dropna(subset=["ano", "municipio"]).copy()
    dff["ano"] = dff["ano"].astype(int)
    dff["municipio"] = dff["municipio"].astype(str)

    if config.get("public_only"):
        if "dependencia" not in dff.columns or "mat_basico" not in dff.columns:
            return []
        dff["mat_basico"] = pd.to_numeric(dff["mat_basico"], errors="coerce")
        dff["dependencia"] = dff["dependencia"].astype(str).str.lower().str.strip()
        dff = dff[
            dff["dependencia"].isin(PUBLIC_DEPENDENCIES) & (dff["mat_basico"] >= 1)
        ].copy()
    if dff.empty:
        return []

    is_room = "denominator_field" in config
    if is_room:
        numerator = pd.to_numeric(dff[config["field"]], errors="coerce")
        denominator = pd.to_numeric(dff[config["denominator_field"]], errors="coerce")
        denominator = denominator.where(denominator >= 0)
        dff["__numerator"] = numerator
        dff["__denominator"] = denominator
        dff["__universe"] = denominator
    elif config.get("classifier") == "proposal":
        proposal = pd.to_numeric(dff[config["field"]], errors="coerce")
        dff["__numerator"] = proposal.where(proposal.isin((0, 1)), pd.NA).map(
            lambda value: 1.0 if _is_finite(value) else math.nan
        )
        dff["__denominator"] = 1.0
        dff["__universe"] = 1.0
    elif "fields" in config:
        first = pd.to_numeric(dff[config["fields"][0]], errors="coerce")
        second = pd.to_numeric(dff[config["fields"][1]], errors="coerce")
        dff["__numerator"] = first.add(second, fill_value=pd.NA)
        dff["__denominator"] = 1.0
        dff["__universe"] = 1.0
    else:
        dff["__numerator"] = pd.to_numeric(dff[config["field"]], errors="coerce")
        dff["__denominator"] = 1.0
        dff["__universe"] = 1.0

    return aggregate_ratio_of_sums(
        dff,
        "__numerator",
        "__denominator",
        indicator_id=indicator_id,
        denominator_universe_column="__universe",
        municipalities_expected=municipalities_expected,
        base_notes=(
            "Pares calculados no registro por escola; nulos foram excluídos e "
            "não convertidos em zero."
        ),
    )


def _build_escolas_integral_records(
    frame: pd.DataFrame,
    *,
    municipalities_expected: int,
) -> list[dict[str, Any]]:
    required = {"ano", "municipio", "dependencia", "mat_basico", "mat_basico_integral"}
    if frame is None or frame.empty or not required.issubset(frame.columns):
        return []
    dff = frame.copy()
    dff["ano"] = pd.to_numeric(dff["ano"], errors="coerce")
    dff["mat_basico"] = pd.to_numeric(dff["mat_basico"], errors="coerce")
    dff["mat_basico_integral"] = pd.to_numeric(
        dff["mat_basico_integral"], errors="coerce"
    )
    dff["dependencia"] = dff["dependencia"].astype(str).str.lower().str.strip()
    dff = dff[
        dff["ano"].notna()
        & dff["municipio"].notna()
        & dff["dependencia"].isin(PUBLIC_DEPENDENCIES)
        & (dff["mat_basico"] >= 1)
    ].copy()
    if dff.empty:
        return []
    dff["ano"] = dff["ano"].astype(int)
    dff["municipio"] = dff["municipio"].astype(str)
    dff["__universe"] = 1.0
    valid = dff["mat_basico_integral"].notna() & (dff["mat_basico"] > 0)
    dff["__denominator"] = dff["__universe"].where(valid, pd.NA)
    dff["__ratio"] = dff["mat_basico_integral"].div(dff["mat_basico"]).mul(100.0)
    dff["__numerator"] = dff["__denominator"].where(dff["__ratio"] >= 25.0, 0.0)
    dff.loc[dff["__denominator"].isna(), "__numerator"] = pd.NA

    records = aggregate_ratio_of_sums(
        dff,
        "__numerator",
        "__denominator",
        indicator_id="escolas_integral",
        denominator_universe_column="__universe",
        municipalities_expected=municipalities_expected,
        base_notes=(
            "Cada escola foi classificada individualmente com corte de 25%; "
            "a razão estadual é numerador de escolas classificadas sobre escolas "
            "com par válido."
        ),
    )
    for record in records:
        record["aggregation_method"] = "school_level_classification_then_ratio_of_sums"
    return records


def _build_census_records(
    frame: pd.DataFrame,
    *,
    indicator_id: str,
    config: Mapping[str, Any],
    municipalities_expected: int,
) -> list[dict[str, Any]]:
    if frame is None or frame.empty or "ano" not in frame.columns:
        return []
    dff = frame[pd.to_numeric(frame["ano"], errors="coerce").isin(CENSUS_YEARS)].copy()
    return aggregate_ratio_of_sums(
        dff,
        config["numerator_column"],
        config["denominator_column"],
        indicator_id=indicator_id,
        municipalities_expected=municipalities_expected,
        base_notes=(
            "Snapshot censitário de 2010/2022; nenhum ano intermediário foi "
            "interpolado ou projetado."
        ),
    )


def _prepare_ept_state(frame: pd.DataFrame) -> dict[int, dict[str, Any]]:
    required = {
        "ano",
        "municipio",
        "mat_ept_nivel_medio_total",
        "mat_ept_nivel_medio_publica",
        "mat_ept_nivel_medio_privada",
    }
    if frame is None or frame.empty or not required.issubset(frame.columns):
        return {}
    dff = frame.copy()
    dff["ano"] = pd.to_numeric(dff["ano"], errors="coerce")
    for column in required - {"ano", "municipio"}:
        dff[column] = pd.to_numeric(dff[column], errors="coerce")
    dff = dff.dropna(subset=["ano", "municipio"]).copy()
    dff["ano"] = dff["ano"].astype(int)
    dff["municipio"] = dff["municipio"].astype(str)
    valid = dff[
        dff[
            [
                "mat_ept_nivel_medio_total",
                "mat_ept_nivel_medio_publica",
                "mat_ept_nivel_medio_privada",
            ]
        ].notna().all(axis=1)
    ].copy()
    state: dict[int, dict[str, Any]] = {}
    for year, year_frame in dff.groupby("ano", sort=True):
        valid_year = valid[valid["ano"] == year]
        total_universe = dff.loc[
            (dff["ano"] == year) & dff["mat_ept_nivel_medio_total"].notna(),
            "mat_ept_nivel_medio_total",
        ].sum(min_count=1)
        state[int(year)] = {
            "total": _number_or_none(valid_year["mat_ept_nivel_medio_total"].sum(min_count=1)),
            "public": _number_or_none(valid_year["mat_ept_nivel_medio_publica"].sum(min_count=1)),
            "private": _number_or_none(valid_year["mat_ept_nivel_medio_privada"].sum(min_count=1)),
            "municipalities_valid": int(valid_year["municipio"].nunique()),
            "municipalities": set(valid_year["municipio"].unique()),
            "denominator_universe": _number_or_none(total_universe),
        }
    return state


def _build_medio_tecnico_participacao_records(
    frame: pd.DataFrame,
    *,
    municipalities_expected: int,
    reference_start_year: int = CYCLE_BASELINE_YEAR,
    reference_end_year: int | None = None,
) -> list[dict[str, Any]]:
    state = _prepare_ept_state(frame)
    if not state:
        return []
    if reference_end_year is not None:
        state = {
            year: record
            for year, record in state.items()
            if year <= reference_end_year
        }
    if reference_start_year != CYCLE_BASELINE_YEAR:
        cumulative_public = 0.0
        cumulative_total = 0.0
        previous = None
        legacy_records: list[dict[str, Any]] = []
        for year in sorted(
            year for year in state if year >= reference_start_year
        ):
            current = state[year]
            if (
                previous is not None
                and year - 1 in state
                and current["public"] is not None
                and current["private"] is not None
                and previous["public"] is not None
                and previous["private"] is not None
            ):
                public_delta = current["public"] - previous["public"]
                private_delta = current["private"] - previous["private"]
                cumulative_public += max(public_delta, 0.0)
                cumulative_total += max(public_delta, 0.0) + max(
                    private_delta, 0.0
                )
            value = (
                100.0 * cumulative_public / cumulative_total
                if cumulative_total > 0
                else None
            )
            legacy_records.append(
                {
                    "indicator_id": "medio_tecnico_participacao_publica",
                    "year": year,
                    "value": value,
                    "numerator": cumulative_public,
                    "denominator": cumulative_total,
                    "aggregation_method": (
                        "state_aggregate_positive_expansions_from_"
                        f"{reference_start_year}"
                    ),
                    "municipalities_valid": current[
                        "municipalities_valid"
                    ],
                    "municipalities_expected": int(
                        municipalities_expected
                    ),
                    "municipal_coverage_percent": (
                        100.0
                        * current["municipalities_valid"]
                        / municipalities_expected
                    ),
                    "denominator_coverage_percent": _coverage_percent(
                        current["total"], current["denominator_universe"]
                    ),
                    "comparison_status": (
                        COMPARABLE if value is not None else UNAVAILABLE
                    ),
                    "notes": (
                        "Método histórico do ciclo encerrado: soma somente "
                        "expansões anuais positivas da série estadual."
                    ),
                }
            )
            previous = current
        return legacy_records
    base = state.get(reference_start_year)
    records: list[dict[str, Any]] = []
    aggregation_method = f"state_net_expansion_from_{reference_start_year}"
    for year in sorted(year for year in state if year >= reference_start_year):
        current = state[year]
        extra: list[str] = []
        if year == reference_start_year:
            records.append(
                {
                    "indicator_id": "medio_tecnico_participacao_publica",
                    "year": year,
                    "value": None,
                    "numerator": None,
                    "denominator": None,
                    "aggregation_method": aggregation_method,
                    "municipalities_valid": current["municipalities_valid"],
                    "municipalities_expected": int(municipalities_expected),
                    "municipal_coverage_percent": 100.0
                    * current["municipalities_valid"]
                    / municipalities_expected,
                    "denominator_coverage_percent": _coverage_percent(
                        current["total"], current["denominator_universe"]
                    ),
                    "comparison_status": UNAVAILABLE,
                    "notes": (
                        f"{reference_start_year} é o ano-base; não há expansão "
                        "acumulada no próprio ano."
                    ),
                }
            )
            continue

        if base is None:
            extra.append(
                f"Ano-base {reference_start_year} ausente; série estadual indisponível."
            )
        if current["municipalities_valid"] < municipalities_expected:
            extra.append(
                f"Cobertura corrente em {current['municipalities_valid']} de "
                f"{municipalities_expected} municípios."
            )
        if base is not None and current["municipalities"] != base["municipalities"]:
            extra.append("Cobertura de municípios mudou entre a base e o ano corrente.")

        if (
            base is not None
            and current["public"] is not None
            and current["total"] is not None
            and base["public"] is not None
            and base["total"] is not None
        ):
            public_expansion = current["public"] - base["public"]
            total_expansion = current["total"] - base["total"]
        else:
            public_expansion = None
            total_expansion = None
            extra.append("Par estadual base/atual incompleto para calcular a expansão.")

        value = (
            100.0 * public_expansion / total_expansion
            if public_expansion is not None
            and total_expansion is not None
            and total_expansion > 0
            else None
        )
        if total_expansion is not None and total_expansion <= 0:
            extra.append("Expansão total líquida nula ou negativa; razão não aplicável.")
        records.append(
            {
                "indicator_id": "medio_tecnico_participacao_publica",
                "year": year,
                "value": value,
                "numerator": public_expansion,
                "denominator": total_expansion,
                "aggregation_method": aggregation_method,
                "municipalities_valid": current["municipalities_valid"],
                "municipalities_expected": int(municipalities_expected),
                "municipal_coverage_percent": 100.0
                * current["municipalities_valid"]
                / municipalities_expected,
                "denominator_coverage_percent": _coverage_percent(
                    current["total"], current["denominator_universe"]
                ),
                "comparison_status": COMPARABLE if value is not None else UNAVAILABLE,
                "notes": _record_notes(
                    "A expansão líquida foi calculada entre os totais estaduais de "
                    f"{reference_start_year} e {year}; não houve média municipal.",
                    extra,
                ),
            }
        )
    return records


def _build_subsequente_records(
    frame: pd.DataFrame,
    *,
    municipalities_expected: int,
) -> list[dict[str, Any]]:
    if frame is None or frame.empty or "municipio" not in frame.columns or "ano" not in frame.columns:
        return []
    value_column = (
        "mat_profissional_tecnico_subsequente"
        if "mat_profissional_tecnico_subsequente" in frame.columns
        else "mat_subsequente_total"
    )
    if value_column not in frame.columns:
        return []
    dff = frame[["ano", "municipio", value_column]].copy()
    dff["ano"] = pd.to_numeric(dff["ano"], errors="coerce")
    dff[value_column] = pd.to_numeric(dff[value_column], errors="coerce")
    dff = dff.dropna(subset=["ano", "municipio"]).copy()
    dff["ano"] = dff["ano"].astype(int)
    dff["municipio"] = dff["municipio"].astype(str)
    dff = dff[dff["ano"] >= CYCLE_BASELINE_YEAR]
    if dff.empty:
        return []
    state: dict[int, dict[str, Any]] = {}
    for year, year_frame in dff.groupby("ano", sort=True):
        valid = year_frame[value_column].notna()
        valid_frame = year_frame.loc[valid]
        universe = year_frame[value_column].dropna().sum(min_count=1)
        state[int(year)] = {
            "total": _number_or_none(valid_frame[value_column].sum(min_count=1)),
            "municipalities_valid": int(valid_frame["municipio"].nunique()),
            "municipalities": set(valid_frame["municipio"].unique()),
            "universe": _number_or_none(universe),
        }
    base = state.get(CYCLE_BASELINE_YEAR)
    records: list[dict[str, Any]] = []
    for year, current in sorted(state.items()):
        base_total = base["total"] if base else None
        current_total = current["total"]
        numerator = (
            current_total - base_total
            if current_total is not None and base_total is not None
            else None
        )
        denominator = base_total
        value = (
            None
            if numerator is None or denominator is None or denominator <= 0
            else 100.0 * numerator / denominator
        )
        extra: list[str] = []
        if base is None:
            extra.append("Ano-base 2025 ausente; expansão estadual indisponível.")
        elif denominator <= 0:
            extra.append("Total estadual da base 2025 zero; valor nulo.")
        if current["municipalities"] != base["municipalities"] if base else False:
            extra.append("Cobertura de municípios mudou entre 2025 e o ano corrente.")
        if year == CYCLE_BASELINE_YEAR:
            value = None
            numerator = None
            extra.append(
                "2025 é o ano-base; não há expansão no próprio ano."
            )
        records.append(
            {
                "indicator_id": "subsequente_expansao",
                "year": year,
                "value": value,
                "numerator": numerator,
                "denominator": denominator,
                "aggregation_method": "state_total_growth_from_2025",
                "municipalities_valid": current["municipalities_valid"],
                "municipalities_expected": int(municipalities_expected),
                "municipal_coverage_percent": 100.0
                * current["municipalities_valid"]
                / municipalities_expected,
                "denominator_coverage_percent": (
                    _coverage_percent(base["total"], base["universe"]) if base else None
                ),
                "comparison_status": COMPARABLE if value is not None else UNAVAILABLE,
                "notes": _record_notes(
                    "Total estadual atual e total estadual de 2025 foram usados; "
                    "não foram somadas expansões municipais.",
                    extra,
                ),
            }
        )
    return records


def _load_frame(loader: Callable[[], pd.DataFrame]) -> tuple[pd.DataFrame, str | None]:
    try:
        frame = loader()
        return (frame.copy() if isinstance(frame, pd.DataFrame) else pd.DataFrame(), None)
    except Exception as exc:  # noqa: BLE001 - keep other indicators exportable.
        return pd.DataFrame(), str(exc)


def _load_reference_frames() -> tuple[dict[str, pd.DataFrame], dict[str, str]]:
    from src.data_loader import (
        load_basico_15_17_data,
        load_basico_6_17_data,
        load_basico_integral_data,
        load_censo_populacao_alfabetizacao_data,
        load_censo_populacao_ensino_fundamental_concluido_15_29_data,
        load_censo_populacao_ensino_fundamental_concluido_15_mais_data,
        load_censo_populacao_ensino_fundamental_concluido_18_mais_data,
        load_censo_populacao_ensino_medio_concluido_18_29_data,
        load_censo_populacao_ensino_medio_concluido_18_mais_data,
        load_docentes_pos_graduacao_data,
        load_docentes_temporarios_data,
        load_eja_integrada_educacao_profissional_data,
        load_ept_nivel_medio_data,
        load_infraestrutura_escolar_data,
        load_infraestrutura_escolar_referencia_data,
        load_medio_tecnico_articulado_data,
        load_pne_data,
        load_pre_escola_data,
    )

    loaders: dict[str, Callable[[], pd.DataFrame]] = {
        "creche": load_pne_data,
        "pre_escola": load_pre_escola_data,
        "basico_6_17": load_basico_6_17_data,
        "basico_15_17": load_basico_15_17_data,
        "basico_integral": load_basico_integral_data,
        "medio_tecnico_articulado": load_medio_tecnico_articulado_data,
        "pos_graduacao": load_docentes_pos_graduacao_data,
        "temporarios": load_docentes_temporarios_data,
        "eja": load_eja_integrada_educacao_profissional_data,
        "ept": load_ept_nivel_medio_data,
        "infra_school": load_infraestrutura_escolar_referencia_data,
        "infra_aggregate": load_infraestrutura_escolar_data,
        "censo_alfabetizacao": load_censo_populacao_alfabetizacao_data,
        "censo_fundamental_18": load_censo_populacao_ensino_fundamental_concluido_18_mais_data,
        "censo_fundamental_15_29": load_censo_populacao_ensino_fundamental_concluido_15_29_data,
        "censo_fundamental_15_mais": load_censo_populacao_ensino_fundamental_concluido_15_mais_data,
        "censo_medio_18": load_censo_populacao_ensino_medio_concluido_18_mais_data,
        "censo_medio_18_29": load_censo_populacao_ensino_medio_concluido_18_29_data,
    }
    frames: dict[str, pd.DataFrame] = {}
    errors: dict[str, str] = {}
    for key, loader in loaders.items():
        frames[key], error = _load_frame(loader)
        if error:
            errors[key] = error
    return frames, errors


def _status_for_records(records: list[dict[str, Any]], default: str = UNAVAILABLE) -> str:
    if any(record.get("comparison_status") == COMPARABLE for record in records):
        return COMPARABLE
    return default


def _build_totals_audit(frames: Mapping[str, pd.DataFrame]) -> list[dict[str, Any]]:
    """Compara totais independentes disponíveis e registra divergências sem forçar igualdade."""

    audit: list[dict[str, Any]] = []
    infra = frames.get("infra_aggregate", pd.DataFrame())
    schools = frames.get("infra_school", pd.DataFrame())

    def latest_value(frame: pd.DataFrame, column: str, *, unique_school: bool = False) -> tuple[int | None, float | None]:
        if frame.empty or "ano" not in frame.columns or column not in frame.columns:
            return None, None
        years = pd.to_numeric(frame["ano"], errors="coerce").dropna()
        if years.empty:
            return None, None
        year = int(years.max())
        rows = frame[pd.to_numeric(frame["ano"], errors="coerce") == year]
        if unique_school and "cod_escola" in rows.columns:
            return year, float(rows["cod_escola"].nunique())
        value = pd.to_numeric(rows[column], errors="coerce").sum(min_count=1)
        return year, _number_or_none(value)

    comparisons = [
        ("escolas", infra, "qntd_escolas", schools, "cod_escola", True),
        ("salas", infra, "qt_salas_utilizadas", schools, "qt_salas_utilizadas", False),
        ("matriculas_0_3", frames.get("creche", pd.DataFrame()), "mat_basico_0_3", schools, "mat_basico_0_3", False),
        ("docentes_basico", frames.get("pos_graduacao", pd.DataFrame()), "total_docentes", schools, "docentes_basico", False),
    ]
    for label, reference_frame, reference_column, comparison_frame, comparison_column, unique_school in comparisons:
        reference_year, reference_value = latest_value(reference_frame, reference_column)
        comparison_year, comparison_value = latest_value(
            comparison_frame, comparison_column, unique_school=unique_school
        )
        if reference_value is None or comparison_value is None:
            status = "comparison_unavailable"
            divergence = None
        else:
            divergence = reference_value - comparison_value
            status = "reconciled" if abs(divergence) < 1e-9 else "divergence_recorded"
        audit.append(
            {
                "metric": label,
                "reference_year": reference_year,
                "reference_value": reference_value,
                "comparison_year": comparison_year,
                "comparison_value": comparison_value,
                "divergence": divergence,
                "status": status,
                "notes": (
                    "Divergência registrada para investigação; nenhuma igualdade "
                    "foi imposta manualmente."
                ),
            }
        )

    population_frame = frames.get("creche", pd.DataFrame())
    population_year, population_value = latest_value(population_frame, "pop_0_3")
    audit.append(
        {
            "metric": "populacao_0_3",
            "reference_year": population_year,
            "reference_value": population_value,
            "comparison_year": None,
            "comparison_value": None,
            "divergence": None,
            "status": "comparison_unavailable",
            "notes": (
                "O pipeline não contém uma segunda publicação independente para "
                "este total populacional; o valor de referência não foi forçado."
            ),
        }
    )
    return audit


def _state_persistence_components(
    series: list[Mapping[str, Any]],
    *,
    start_year: int,
) -> tuple[float | None, float | None, int, str | None]:
    """Validate a recent annual window and return its last paired components."""

    if any(
        record.get("methodology_break")
        or record.get("methodological_break")
        or record.get("quebra_metodologica")
        for record in series
    ):
        return None, None, 0, "methodology_break"

    records: list[tuple[int, float, float]] = []
    for record in series:
        if not (
            _is_finite(record.get("year"))
            and _is_finite(record.get("numerator"))
            and _is_finite(record.get("denominator"))
        ):
            continue
        numeric_year = float(record["year"])
        if not numeric_year.is_integer():
            continue
        records.append(
            (
                int(numeric_year),
                float(record["numerator"]),
                float(record["denominator"]),
            )
        )

    years = [year for year, _, _ in records]
    if len(years) != len(set(years)):
        return None, None, len(records), "duplicate_years"

    by_year = {year: (numerator, denominator) for year, numerator, denominator in records}
    required_years = list(
        range(
            start_year - STATE_PROJECTION_MINIMUM_OBSERVATIONS,
            start_year,
        )
    )
    if any(year not in by_year for year in required_years):
        return None, None, len(records), "insufficient_or_stale_annual_history"

    recent = [by_year[year] for year in required_years]
    if any(numerator < 0 or denominator <= 0 for numerator, denominator in recent):
        return None, None, len(records), "invalid_components"

    numerator, denominator = recent[-1]
    return numerator, denominator, len(records), None


def build_state_projections(
    indicators: Mapping[str, Mapping[str, Any]],
    *,
    start_year: int = 2026,
    end_year: int = 2036,
) -> dict[str, dict[str, Any]]:
    """Constrói uma linha de base de persistência para a série estadual.

    A função recebe a série estadual pronta e não recebe resultados municipais;
    isso torna impossível calcular o cenário por média municipal por acidente.
    O último par agregado é mantido porque essa regra superou a extrapolação
    linear no backtesting rolling-origin. Snapshots censitários permanecem sem
    cenário.
    """

    if end_year < start_year:
        raise ValueError("end_year must be greater than or equal to start_year")

    projections: dict[str, dict[str, Any]] = {}
    for indicator_id, payload in indicators.items():
        if payload.get("allow_projection") is False:
            projections[indicator_id] = {
                "available": False,
                "projection_status": "not_applicable",
                "method": "observed_series_only",
                "source": "Série observada; indicador aproximado sem trajetória ou projeção",
                "methodology_version": METHODOLOGY_VERSION,
                "series": [],
            }
            continue
        if indicator_id in CENSUS_CONFIGS:
            projections[indicator_id] = {
                "available": False,
                "projection_status": "not_applicable",
                "method": "census_snapshots_only",
                "source": "Série estadual — sem interpolação ou projeção censitária",
                "methodology_version": METHODOLOGY_VERSION,
                "series": [],
            }
            continue
        series = payload.get("series", [])
        numerator, denominator, observation_count, validation_error = (
            _state_persistence_components(series, start_year=start_year)
        )
        if validation_error is not None:
            projections[indicator_id] = {
                "available": False,
                "projection_status": "unavailable",
                "method": "aggregate_state_persistence_baseline",
                "source": (
                    "Série estadual agregada; último par observado mantido; "
                    "sem média municipal"
                ),
                "methodology_version": METHODOLOGY_VERSION,
                "reason": validation_error,
                "validation": {
                    "minimumComparableObservations": (
                        STATE_PROJECTION_MINIMUM_OBSERVATIONS
                    ),
                    "requiredObservationIntervalYears": 1,
                    "requireLatestYear": start_year - 1,
                    "observationCount": observation_count,
                },
                "series": [],
            }
            continue
        value = 100.0 * numerator / denominator
        projected_series = [
            {
                "year": year,
                "value": value,
                "numerator": numerator,
                "denominator": denominator,
                "comparison_status": COMPARABLE,
            }
            for year in range(start_year, end_year + 1)
        ]
        projections[indicator_id] = {
            "available": True,
            "projection_status": "available",
            "method": "aggregate_state_persistence_baseline",
            "source": (
                "Série estadual agregada; último par observado mantido; "
                "sem média municipal"
            ),
            "methodology_version": METHODOLOGY_VERSION,
            "validation": {
                "minimumComparableObservations": (
                    STATE_PROJECTION_MINIMUM_OBSERVATIONS
                ),
                "requiredObservationIntervalYears": 1,
                "requireLatestYear": start_year - 1,
                "observationCount": observation_count,
            },
            "uncertainty": {
                "status": "not_estimated",
                "interval": None,
                "reason": (
                    "Linha de base determinística de persistência; não foi "
                    "estimado intervalo probabilístico."
                ),
                "interpretation": (
                    "O resultado é um cenário condicional, não uma previsão oficial."
                ),
            },
            "series": projected_series,
        }
    return projections


def build_state_reference() -> dict[str, Any]:
    """Calcula e retorna o artefato estadual completo do ciclo."""

    registry = build_registry()
    frames, load_errors = _load_reference_frames()
    indicators: dict[str, dict[str, Any]] = {}

    for indicator_id, metadata in registry.items():
        records: list[dict[str, Any]] = []
        if indicator_id in BLOCKED_REASONS:
            indicators[indicator_id] = {**metadata, "series": []}
            continue
        if indicator_id in RATIO_CONFIGS:
            config = RATIO_CONFIGS[indicator_id]
            frame = frames.get(config["loader_key"], pd.DataFrame())
            if config.get("allowed_years"):
                frame = frame[pd.to_numeric(frame.get("ano"), errors="coerce").isin(config["allowed_years"])]
            records = aggregate_ratio_of_sums(
                frame,
                config["numerator_column"],
                config["denominator_column"],
                indicator_id=indicator_id,
                filters=config.get("filters"),
                denominator_aggregation=config.get("denominator_aggregation", "sum"),
                municipalities_expected=EXPECTED_RS_MUNICIPALITIES,
                base_notes=config["notes"],
            )
        elif indicator_id == "escolas_integral":
            records = _build_escolas_integral_records(
                frames.get("infra_school", pd.DataFrame()),
                municipalities_expected=EXPECTED_RS_MUNICIPALITIES,
            )
        elif indicator_id in INFRA_SCHOOL_CONFIGS:
            records = _build_school_ratio_records(
                frames.get("infra_school", pd.DataFrame()),
                indicator_id=indicator_id,
                config=INFRA_SCHOOL_CONFIGS[indicator_id],
                municipalities_expected=EXPECTED_RS_MUNICIPALITIES,
            )
        elif indicator_id in CENSUS_CONFIGS:
            config = CENSUS_CONFIGS[indicator_id]
            records = _build_census_records(
                frames.get(config["loader_key"], pd.DataFrame()),
                indicator_id=indicator_id,
                config=config,
                municipalities_expected=EXPECTED_RS_MUNICIPALITIES,
            )
        elif indicator_id == "medio_tecnico_participacao_publica":
            records = _build_medio_tecnico_participacao_records(
                frames.get("ept", pd.DataFrame()),
                municipalities_expected=EXPECTED_RS_MUNICIPALITIES,
            )
        elif indicator_id == "subsequente_expansao":
            records = _build_subsequente_records(
                frames.get("ept", pd.DataFrame()),
                municipalities_expected=EXPECTED_RS_MUNICIPALITIES,
            )

        records = _add_common_series_fields(records, metadata)
        status = _status_for_records(records)
        updated_metadata = {**metadata, "comparison_status": status}
        indicators[indicator_id] = {**updated_metadata, "series": records}
        registry[indicator_id] = updated_metadata

    return {
        "cycle": "pne_2026_2036",
        "state": STATE_CODE,
        "state_name": STATE_NAME,
        "generated_at": None,
        "municipalities_expected": EXPECTED_RS_MUNICIPALITIES,
        "municipalities_universe": "Todos os municípios do Rio Grande do Sul",
        "methodology_version": METHODOLOGY_VERSION,
        "registry": registry,
        "indicators": indicators,
        "projections": build_state_projections(indicators),
        "totals_audit": _build_totals_audit(frames),
        "source_load_errors": load_errors,
        "notes": (
            "Referência fixa do RS, independente do município selecionado. "
            "Valores armazenados sem arredondamento; a apresentação arredonda somente "
            "no último passo."
        ),
    }


__all__ = [
    "BLOCKED_REASONS",
    "CENSUS_CONFIGS",
    "COMPARABLE",
    "EXPECTED_RS_MUNICIPALITIES",
    "INFRA_SCHOOL_CONFIGS",
    "METHODOLOGY_PENDING",
    "METHODOLOGY_VERSION",
    "RATIO_CONFIGS",
    "UNAVAILABLE",
    "aggregate_ratio_of_sums",
    "build_registry",
    "build_state_projections",
    "build_state_reference",
]
