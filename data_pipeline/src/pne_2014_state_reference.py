"""Referência estadual do RS para os indicadores comparáveis do PNE 2014–2024.

O ciclo encerrado tem um artefato próprio. Nenhum valor estadual é derivado da
média de percentuais municipais: cada série usa os numeradores e denominadores
brutos compatíveis com o cálculo municipal, no mesmo ano e universo.
"""

from __future__ import annotations

from typing import Any, Mapping

import pandas as pd

from src.pne_2014_child_literacy import (
    SOURCE_LABEL as CHILD_LITERACY_SOURCE_LABEL,
    load_snapshot as load_child_literacy_snapshot,
)
from .pne_state_reference import (
    COMPARABLE,
    EXPECTED_RS_MUNICIPALITIES,
    METHODOLOGY_PENDING,
    PUBLIC_DEPENDENCIES,
    STATE_CODE,
    STATE_NAME,
    UNAVAILABLE,
    _add_common_series_fields,
    _build_census_records,
    _build_escolas_integral_records,
    _build_medio_tecnico_participacao_records,
    _load_reference_frames,
    aggregate_ratio_of_sums,
)


REFERENCE_START_YEAR = 2014
REFERENCE_END_YEAR = 2024
METHODOLOGY_VERSION = "pne2014-rs-reference-v1"


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
    unit: str = "percent",
) -> dict[str, Any]:
    return {
        "indicator_id": indicator_id,
        "unit": unit,
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
    }


RATIO_CONFIGS: dict[str, dict[str, Any]] = {
    "creche": _ratio_config(
        "creche",
        loader_key="creche",
        numerator_column="mat_infantil_creche",
        denominator_column="pop_0_3",
        numerator_definition="Matrículas da educação infantil de 0 a 3 anos.",
        denominator_definition="População de 0 a 3 anos do município.",
        denominator_aggregation="max",
        source="INEP Censo Escolar + estimativas populacionais oficiais",
        notes="Mesmo ano e população de referência do indicador municipal.",
        allowed_years=tuple(range(REFERENCE_START_YEAR, REFERENCE_END_YEAR + 1)),
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
        allowed_years=tuple(range(REFERENCE_START_YEAR, REFERENCE_END_YEAR + 1)),
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
        allowed_years=tuple(range(REFERENCE_START_YEAR, REFERENCE_END_YEAR + 1)),
    ),
    "basico_15_17": _ratio_config(
        "basico_15_17",
        loader_key="basico_15_17",
        numerator_column="mat_basico_15_17",
        denominator_column="pop_15_17",
        numerator_definition=(
            "Pessoas de 15 a 17 anos que frequentam a escola ou já concluíram "
            "a educação básica."
        ),
        denominator_definition="População de 15 a 17 anos do município.",
        denominator_aggregation="max",
        source="INEP Censo Escolar + estimativas populacionais oficiais",
        notes="Mesmo ano e população de referência do indicador municipal.",
        allowed_years=tuple(range(REFERENCE_START_YEAR, REFERENCE_END_YEAR + 1)),
    ),
    "basico_integral": _ratio_config(
        "basico_integral",
        loader_key="basico_integral",
        numerator_column="mat_basico_integral",
        denominator_column="mat_basico",
        numerator_definition="Matrículas públicas da educação básica em jornada integral.",
        denominator_definition="Matrículas públicas da educação básica no universo da ETI.",
        filters={"dependencia": "publica"},
        source="INEP Censo Escolar",
        notes="Filtro da rede pública preservado; pares válidos são agregados antes da razão.",
        allowed_years=tuple(range(REFERENCE_START_YEAR, REFERENCE_END_YEAR + 1)),
    ),
    "eja_integrada_educacao_profissional_percentual": _ratio_config(
        "eja_integrada_educacao_profissional_percentual",
        loader_key="eja",
        numerator_column="mat_eja_integrada_educacao_profissional_calculada",
        denominator_column="mat_eja_denominador_calculado",
        numerator_definition=(
            "Matrículas de EJA integrada à educação profissional, calculadas a "
            "partir dos componentes brutos da base."
        ),
        denominator_definition="Matrículas da EJA fundamental + matrículas da EJA médio.",
        source="INEP — Sinopse Estatística da Educação Básica, tabelas EJA 1.35 e Educação Profissional 1.30/1.42.",
        notes=(
            "A série estadual usa contagens brutas; a comparação fica bloqueada "
            "se o par de contagens não for válido."
        ),
        allowed_years=tuple(range(REFERENCE_START_YEAR, REFERENCE_END_YEAR + 1)),
    ),
    "pos_graduacao": _ratio_config(
        "pos_graduacao",
        loader_key="pos_graduacao",
        numerator_column="docentes_pos_graduacao",
        denominator_column="total_docentes",
        numerator_definition="Docentes da educação básica com pós-graduação.",
        denominator_definition="Total de docentes da educação básica.",
        filters={"dependencia": "total"},
        source="INEP Censo Escolar",
        notes="Filtro de dependência total preservado.",
        allowed_years=tuple(range(REFERENCE_START_YEAR, REFERENCE_END_YEAR + 1)),
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
    "ensino_medio_ou_basica_completa_pop_15_17": {
        "loader_key": "censo_15_17",
        "numerator_column": "populacao_15_17_ensino_medio_ou_basica_completa",
        "denominator_column": "populacao_15_17_total",
        "numerator_definition": (
            "População de 15 a 17 anos que frequenta o ensino médio ou concluiu "
            "a educação básica."
        ),
        "denominator_definition": "População total de 15 a 17 anos.",
    },
    "ensino_fundamental_ou_completo_pop_6_14": {
        "loader_key": "censo_6_14",
        "numerator_column": "populacao_6_14_ensino_fundamental_ou_completo",
        "denominator_column": "populacao_6_14_total",
        "numerator_definition": (
            "População de 6 a 14 anos que frequenta ou concluiu o ensino fundamental."
        ),
        "denominator_definition": "População total de 6 a 14 anos.",
    },
}


BLOCKED_REASONS: dict[str, str] = {
    "ideb_anos_iniciais": "Bloqueado: IDEB é índice, sem numerador e denominador agregáveis.",
    "ideb_anos_finais": "Bloqueado: IDEB é índice, sem numerador e denominador agregáveis.",
    "ideb_ensino_medio": "Bloqueado: IDEB é índice, sem numerador e denominador agregáveis.",
    "adequacao_ai": (
        "Bloqueado: a base municipal disponível fornece percentual de adequação, "
        "sem contagens brutas compatíveis."
    ),
    "adequacao_af": (
        "Bloqueado: a base municipal disponível fornece percentual de adequação, "
        "sem contagens brutas compatíveis."
    ),
    "adequacao_em": (
        "Bloqueado: a base municipal disponível fornece percentual de adequação, "
        "sem contagens brutas compatíveis."
    ),
    "rendimento_magisterio": (
        "Bloqueado: a base municipal disponível fornece somente uma razão de "
        "rendimentos, sem numerador e denominador estaduais agregáveis."
    ),
    "escolaridade_media_18_29": (
        "Bloqueado: média de anos de estudo sem contagens brutas compatíveis; "
        "não usar média de médias municipais."
    ),
    "razao_escolaridade_racial_18_29": (
        "Bloqueado: razão entre médias, sem numerador e denominador brutos "
        "compatíveis; não usar média de taxas municipais."
    ),
    "medio_tecnico_total": (
        "Bloqueado: indicador informativo de contagem, sem meta percentual "
        "comparável no card."
    ),
    "medio_tecnico": (
        "Bloqueado: indicador informativo de contagem, sem meta percentual "
        "comparável no card."
    ),
}

UNAVAILABLE_REASONS: dict[str, str] = {
    "ensino_medio_ou_basica_completa_pop_15_17": (
        "Sem referência estadual publicada: a fonte de contagens brutas do Censo "
        "para este recorte etário não retornou uma série válida no export atual."
    ),
    "ensino_fundamental_ou_completo_pop_6_14": (
        "Sem referência estadual publicada: a fonte de contagens brutas do Censo "
        "para este recorte etário não retornou uma série válida no export atual."
    ),
}


def _blocked_metadata(indicator_id: str, reason: str, *, unit: str = "percent") -> dict[str, Any]:
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
        unit=unit,
    )


def build_registry() -> dict[str, dict[str, Any]]:
    registry: dict[str, dict[str, Any]] = {
        key: dict(value) for key, value in RATIO_CONFIGS.items()
    }

    registry["alfabetizacao"] = {
        **_metadata(
            "alfabetizacao",
            aggregation_method="official_state_municipal_network_result",
            numerator_definition="Não publicado na fonte agregada oficial.",
            denominator_definition="Não publicado na fonte agregada oficial.",
            filters={"rede": "municipal", "anos": [2023, 2024]},
            source=CHILD_LITERACY_SOURCE_LABEL,
            source_type="official_state_published_percentage",
            notes=(
                "Resultado estadual oficial da rede municipal. Não é média de "
                "percentuais municipais e não representa conclusão da Meta 5."
            ),
        ),
        "null_policy": "Ausência de resultado oficial permanece nula; nulo não é zero.",
    }

    registry["escolas_integral"] = _metadata(
        "escolas_integral",
        aggregation_method="school_level_classification_then_ratio_of_sums",
        numerator_definition=(
            "Escolas públicas elegíveis em que cada escola, individualmente, "
            "tem pelo menos 25% dos alunos em jornada integral."
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

    registry["medio_tecnico_participacao_publica"] = _metadata(
        "medio_tecnico_participacao_publica",
        aggregation_method="state_aggregate_positive_expansions_from_2013",
        numerator_definition=(
            "Expansão positiva acumulada estadual das matrículas públicas de EPT "
            "de nível médio."
        ),
        denominator_definition=(
            "Expansão positiva acumulada estadual pública + privada de EPT de nível médio."
        ),
        filters={"ano_base": 2013, "segmentos": ["publica", "privada"]},
        source="INEP Censo Escolar — EPT de nível médio",
        source_type="state_series_growth",
        notes=(
            "Agrega primeiro os totais estaduais e calcula a participação somente "
            "sobre expansões anuais positivas."
        ),
    )

    for key, config in CENSUS_CONFIGS.items():
        registry[key] = _metadata(
            key,
            aggregation_method="ratio_of_sums_census_snapshot",
            numerator_definition=config["numerator_definition"],
            denominator_definition=config["denominator_definition"],
            filters={"anos": [2010, 2022]},
            source="IBGE Censo Demográfico + população por idade oficial",
            source_type="census_raw_count_reconstruction",
            notes=(
                "Somente os snapshots de 2010 e 2022 são válidos; não interpolar, "
                "projetar nem criar série anual contínua."
            ),
        )

    units = {
        "ideb_anos_iniciais": "index",
        "ideb_anos_finais": "index",
        "ideb_ensino_medio": "index",
        "escolaridade_media_18_29": "years",
        "medio_tecnico_total": "count",
        "medio_tecnico": "count",
    }
    for key, reason in BLOCKED_REASONS.items():
        registry[key] = _blocked_metadata(key, reason, unit=units.get(key, "percent"))

    return registry


def _status_for_records(records: list[dict[str, Any]]) -> str:
    return COMPARABLE if any(record.get("comparison_status") == COMPARABLE for record in records) else UNAVAILABLE


def _build_alfabetizacao_state_records() -> list[dict[str, Any]]:
    _municipal, state_rows, _manifest = load_child_literacy_snapshot()
    records = []
    for row in state_rows:
        year = int(row["ano"])
        value = row.get("taxa_alfabetizacao")
        if year > REFERENCE_END_YEAR or value is None:
            continue
        records.append(
            {
                "indicator_id": "alfabetizacao",
                "year": year,
                "value": float(value),
                "numerator": None,
                "denominator": None,
                "aggregation_method": "official_state_municipal_network_result",
                "municipalities_valid": None,
                "municipalities_expected": EXPECTED_RS_MUNICIPALITIES,
                "municipal_coverage_percent": None,
                "denominator_coverage_percent": None,
                "comparison_status": COMPARABLE,
                "notes": (
                    "Resultado estadual oficial da rede municipal; não calculado "
                    "por média de percentuais municipais."
                ),
            }
        )
    return records


def build_alfabetizacao_state_reference_entry() -> tuple[
    dict[str, Any],
    dict[str, Any],
]:
    metadata = build_registry()["alfabetizacao"]
    records = _add_common_series_fields(
        _build_alfabetizacao_state_records(),
        metadata,
        methodology_version=METHODOLOGY_VERSION,
    )
    status = _status_for_records(records)
    updated_metadata = {**metadata, "comparison_status": status}
    return updated_metadata, {
        **updated_metadata,
        "available": any(record.get("value") is not None for record in records),
        "series": records,
    }


def build_state_reference() -> dict[str, Any]:
    """Calcula o artefato estadual completo do ciclo encerrado."""

    registry = build_registry()
    frames, load_errors = _load_reference_frames()
    indicators: dict[str, dict[str, Any]] = {}

    for indicator_id, metadata in registry.items():
        if indicator_id == "alfabetizacao":
            metadata, indicator = build_alfabetizacao_state_reference_entry()
            registry[indicator_id] = metadata
            indicators[indicator_id] = indicator
            continue
        if indicator_id in BLOCKED_REASONS:
            indicators[indicator_id] = {
                **metadata,
                "available": False,
                "series": [],
            }
            continue

        records: list[dict[str, Any]] = []
        if indicator_id in RATIO_CONFIGS:
            config = RATIO_CONFIGS[indicator_id]
            frame = frames.get(config["loader_key"], pd.DataFrame())
            if config.get("allowed_years"):
                if "ano" in frame.columns:
                    years = pd.to_numeric(frame["ano"], errors="coerce")
                    frame = frame[years.isin(config["allowed_years"])]
                else:
                    frame = frame.iloc[0:0].copy()
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
            records = [
                record
                for record in records
                if REFERENCE_START_YEAR <= record["year"] <= REFERENCE_END_YEAR
            ]
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
                reference_start_year=2013,
                reference_end_year=REFERENCE_END_YEAR,
            )
            records = [record for record in records if record["year"] >= REFERENCE_START_YEAR]

        records = _add_common_series_fields(
            records,
            metadata,
            methodology_version=METHODOLOGY_VERSION,
        )
        status = _status_for_records(records)
        updated_metadata = {**metadata, "comparison_status": status}
        if indicator_id in UNAVAILABLE_REASONS and status == UNAVAILABLE:
            updated_metadata["notes"] = (
                f"{metadata['notes']} {UNAVAILABLE_REASONS[indicator_id]}"
            )
        indicators[indicator_id] = {
            **updated_metadata,
            "available": any(record.get("value") is not None for record in records),
            "series": records,
        }
        registry[indicator_id] = updated_metadata

    enabled = sorted(
        indicator_id
        for indicator_id, indicator in indicators.items()
        if indicator.get("comparison_status") == COMPARABLE
    )
    unavailable = sorted(
        indicator_id
        for indicator_id, indicator in indicators.items()
        if indicator.get("comparison_status") == UNAVAILABLE
        and indicator_id not in BLOCKED_REASONS
    )
    return {
        "cycle": "pne_2014_2024",
        "state": STATE_CODE,
        "state_name": STATE_NAME,
        "generated_at": None,
        "municipalities_expected": EXPECTED_RS_MUNICIPALITIES,
        "municipalities_universe": "Todos os municípios do Rio Grande do Sul",
        "methodology_version": METHODOLOGY_VERSION,
        "registry": registry,
        "indicators": indicators,
        "enabled_indicators": enabled,
        "blocked_indicators": sorted(BLOCKED_REASONS),
        "unavailable_indicators": unavailable,
        "source_load_errors": load_errors,
        "notes": (
            "Referência fixa do RS, independente do município selecionado. "
            "Valores armazenados sem arredondamento; a apresentação arredonda somente "
            "no último passo. Nenhuma taxa municipal foi usada como substituta de "
            "numerador ou denominador estadual."
        ),
    }


__all__ = [
    "BLOCKED_REASONS",
    "CENSUS_CONFIGS",
    "COMPARABLE",
    "EXPECTED_RS_MUNICIPALITIES",
    "METHODOLOGY_VERSION",
    "RATIO_CONFIGS",
    "UNAVAILABLE_REASONS",
    "build_alfabetizacao_state_reference_entry",
    "build_registry",
    "build_state_reference",
]
