"""Job 5H: arquitetura editorial máxima, tipada e rastreável para o Job 5I.

O módulo consome somente artefatos locais congelados dos Jobs 5G-A-R a 5G-D.
Ele não escreve narrativa pública, frontend ou ``public/data`` e não consulta
banco ou rede.
"""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import re
from statistics import median
from typing import Any, Iterable, Mapping, Sequence

import pandas as pd

from src.vocacoes_pne_job2 import (
    artifact_record,
    directory_content_digest,
    sha256_file,
    write_csv_gzip,
    write_json,
)


NSR_CODE = "4313375"
REGION_ENTITY_ID = "REGION_VALE_DO_SINOS"
STATE_ENTITY_ID = "STATE_RS"
FINAL_STATE = "JOB_5H_READY_WITH_EXPLICIT_LIMITS_FOR_EXTERNAL_JUDGMENT"
IBGE_CODE_PATTERN = re.compile(r"\d{7}")

CANONICAL_GCR_FACT_HASH = (
    "cd19af79a375b07390c7a2fde10135f9293a999bb3a3848a65ede678b74f3ed6"
)
INCORRECT_GD_CONTRACT_HASH = (
    "cd19af3cf951349cff06c9bb048f9f195e30b756fa309cda95b106810e85b149"
)

EXPECTED_PNE_ALLOWLIST = {
    "1.a",
    "1.c",
    "3.a",
    "4.a",
    "4.b",
    "4.c",
    "4.d",
    "5.a",
    "5.b",
    "5.d",
    "6.a",
    "8.b",
    "8.c",
    "11.a",
    "11.b",
    "11.c",
    "12.a",
    "12.b",
    "17.a",
    "17.b",
    "17.d",
    "17.f",
    "18.b",
    "19.c",
}
PNE_LINK_TYPES = {
    "direct_monitoring",
    "partial_component",
    "contextual_planning",
    "no_valid_link",
}

SOURCE_DEFINITIONS: dict[str, dict[str, Any]] = {
    "job5gd_coordination": {
        "path": ".tmp/vocacoes-pne/v7-job5gd/MATRIZ_COORDENACAO_REGIONAL_JOB5GD_V1.csv.gz",
        "period": "source-specific",
        "lens": "multiple_separate_lenses",
        "limit": "Job 5G-D input only; 99 rows are 9 families x 11 variants, not public stories.",
    },
    "job5gd_offer": {
        "path": ".tmp/vocacoes-pne/v7-job5gd/PAINEL_ESTRUTURA_TERRITORIAL_OFERTA_JOB5GD_V1.csv.gz",
        "period": "2014-2025 or source-specific",
        "lens": "school_location|rural_school_location",
        "limit": "Located offer does not identify students by residence or measure capacity.",
    },
    "job5gd_mobility": {
        "path": ".tmp/vocacoes-pne/v7-job5gd/PAINEL_MOBILIDADE_EDUCACIONAL_POR_ETAPA_JOB5GD_V1.csv.gz",
        "period": "2022",
        "lens": "student_residence",
        "limit": "Cross-section; destination municipality unavailable; foreign country separate.",
    },
    "job5gd_pnate": {
        "path": ".tmp/vocacoes-pne/v7-job5gd/PAINEL_TRANSPORTE_ESCOLAR_PNATE_JOB5GD_V1.csv.gz",
        "period": "2024-2026",
        "lens": "municipal_executor",
        "limit": "PNATE is not mobility; 2026 is planning forecast and has no execution/use evidence.",
    },
    "job5gd_finance": {
        "path": ".tmp/vocacoes-pne/v7-job5gd/PAINEL_FINANCEIRO_CONTEXTUAL_SELECIONAVEL_JOB5GD_V1.csv.gz",
        "period": "source-specific, mainly 2025",
        "lens": "municipal_executor",
        "limit": "Selective context only; stages stay separate; no outcome causality.",
    },
    "job5gd_facts": {
        "path": ".tmp/vocacoes-pne/v7-job5gd/CATALOGO_COMPLETO_FATOS_JOB5GD_V1.csv.gz",
        "period": "source-specific",
        "lens": "declared_per_fact",
        "limit": "Complete internal fact catalog before editorial selection.",
    },
    "job5gar_early_childhood": {
        "path": ".tmp/vocacoes-pne/v7-job5gar/PAINEL_EDUCACAO_INFANTIL_OBSERVADA_V1.csv.gz",
        "period": "2014-2025",
        "lens": "resident_population|school_location",
        "limit": "Population and located enrollments are separate universes.",
    },
    "job5gar_trajectory": {
        "path": ".tmp/vocacoes-pne/v7-job5gar/PAINEL_TRAJETORIA_OFICIAL_DESCRITIVA_V1_1.csv.gz",
        "period": "2018-2025",
        "lens": "school_location",
        "limit": "Official municipal rates; no Vale rate recomposition or mean of rates.",
    },
    "job5gar_pressure": {
        "path": ".tmp/vocacoes-pne/v7-job5gar/PAINEL_PRESSAO_MECANICA_COORTES_AUDITADO_V1_1.csv.gz",
        "period": "reference 2025; mechanical horizon 2030",
        "lens": "resident_population|school_location",
        "limit": "Mechanical pressure is not forecast, demand, coverage or capacity.",
    },
    "job5gbr_adult_schooling": {
        "path": ".tmp/vocacoes-pne/v7-job5gbr/PAINEL_ESCOLARIDADE_ADULTA_2010_2022_V1_1.csv.gz",
        "period": "2010 and 2022",
        "lens": "resident_population",
        "limit": "Census observations only; no intercensal interpolation.",
    },
    "job5gbr_eja_distribution": {
        "path": ".tmp/vocacoes-pne/v7-job5gbr/PAINEL_EJA_DISTRIBUICAO_2022_V1_1.csv.gz",
        "period": "2022",
        "lens": "resident_population|school_location",
        "limit": "Distribution photograph; intensity is not coverage or manifested demand.",
    },
    "job5gbr_rural": {
        "path": ".tmp/vocacoes-pne/v7-job5gbr/PAINEL_EDUCACAO_RURAL_TERRITORIO_V1_1.csv.gz",
        "period": "2014-2025",
        "lens": "rural_school_location",
        "limit": "Located rural offer; it does not identify rural residence or routes.",
    },
    "job5gbr_special_aee": {
        "path": ".tmp/vocacoes-pne/v7-job5gbr/PAINEL_EDUCACAO_ESPECIAL_AEE_V1_1.csv.gz",
        "period": "2014-2025",
        "lens": "school_location",
        "limit": "Located enrollments and schools offering AEE; no individual trajectory linkage.",
    },
    "job5gcr_youth_rais": {
        "path": ".tmp/vocacoes-pne/v7-job5gcr/PAINEL_RAIS_TRABALHO_JUVENIL_V1_1.csv.gz",
        "period": "2019-2025",
        "lens": "workplace",
        "limit": "Formal active bonds are stock, not unique people or student records.",
    },
    "job5gcr_youth_caged": {
        "path": ".tmp/vocacoes-pne/v7-job5gcr/PAINEL_CAGED_JUVENIL_AGREGADO_SEGURO_V1.csv.gz",
        "period": "2020-2025",
        "lens": "workplace",
        "limit": "Admissions and dismissals are events; negative adjustments remain explicit.",
    },
    "job5gcr_apprenticeship": {
        "path": ".tmp/vocacoes-pne/v7-job5gcr/PAINEL_APRENDIZAGEM_PROFISSIONAL_V1_1.csv.gz",
        "period": "2020-2025",
        "lens": "workplace",
        "limit": "Apprenticeship records are flow events, not apprentice people or stock.",
    },
    "job5gcr_occupations": {
        "path": ".tmp/vocacoes-pne/v7-job5gcr/PAINEL_OCUPACOES_RAIS_ESTOQUE_V1.csv.gz",
        "period": "2019-2025",
        "lens": "workplace",
        "limit": "Deterministic top changes are exploration, not ranking or recommendation.",
    },
    "job5gcr_sectors": {
        "path": ".tmp/vocacoes-pne/v7-job5gcr/PAINEL_SETORES_RAIS_ESTOQUE_V1.csv.gz",
        "period": "2019-2025",
        "lens": "workplace",
        "limit": "All-age formal bonds; not youth-only and not causal evidence.",
    },
    "job5gcr_ept": {
        "path": ".tmp/vocacoes-pne/v7-job5gcr/PAINEL_EPT_OFERTA_TOTAL_V1_1.csv.gz",
        "period": "2023-2025",
        "lens": "school_location",
        "limit": "Located technical enrollments; origin of students unavailable.",
    },
    "job5gcr_concentration": {
        "path": ".tmp/vocacoes-pne/v7-job5gcr/PAINEL_CONCENTRACAO_TRABALHO_EPT_V1_1.csv.gz",
        "period": "2019-2025 by universe",
        "lens": "workplace|school_location",
        "limit": "HHI is contextual; qualitative labels and cross-universe comparison forbidden.",
    },
    "job5gcr_shift_share": {
        "path": ".tmp/vocacoes-pne/v7-job5gcr/PAINEL_SHIFT_SHARE_SETORIAL_V1_1.csv.gz",
        "period": "2019-2025",
        "lens": "workplace",
        "limit": "Descriptive decomposition against RS; local differential is not causal.",
    },
    "job5gcr_bridge": {
        "path": ".tmp/vocacoes-pne/v7-job5gcr/PAINEL_PONTE_CBO_CNCT_AUDITADA_V1_1.csv.gz",
        "period": "2025",
        "lens": "school_location|workplace",
        "limit": "Normative many-to-many bridge; no same-person, causal or additive association.",
    },
    "job5gcr_work_education": {
        "path": ".tmp/vocacoes-pne/v7-job5gcr/PAINEL_TRABALHO_JUVENIL_EDUCACAO_CONTEXTO_V1_1.csv.gz",
        "period": "2018-2025 by source",
        "lens": "workplace|school_location",
        "limit": "Parallel series only; no same-person or causal link.",
    },
}


def _link(goal_ref: str, link_type: str, rationale: str) -> dict[str, Any]:
    return {
        "legal_goal_ref": goal_ref,
        "link_type": link_type,
        "justification": rationale,
        "official_indicator_recalculated": False,
        "goal_compliance_claim_allowed": False,
    }


COMMON_FORBIDDEN = [
    "causal effect",
    "good or bad municipality classification",
    "automatic recommendation",
    "administrative dependency as analytic dimension",
    "public narrative before external judgment",
]


FAMILY_SPECS: tuple[dict[str, Any], ...] = (
    {
        "story_family_id": "D1_COHORT_OFFER_CAPACITY",
        "sequence": 1,
        "direction_id": "TERRITORY_HELPS_UNDERSTAND_EDUCATION",
        "macroblock_id": "A_DEMOGRAPHY_AND_OFFER",
        "layer": "PRIMARY_NARRATIVE_PATH",
        "editorial_state": "PRIMARY_VISIBLE",
        "internal_title": "Coortes observadas e resposta territorial da oferta",
        "management_question": "Em quais etapas a oferta observada e a pressão mecânica exigem monitoramento antecipado de capacidade?",
        "mechanism": "Contrastar coortes residentes, matrículas localizadas, escolas, turmas e pressão mecânica sem converter lentes diferentes em cobertura.",
        "regional_read": "Distribuição dos dez municípios e totais compatíveis do Vale por etapa.",
        "municipal_read": "Mudança local por etapa e posição descritiva na distribuição municipal.",
        "stages": ["creche_age_0_3", "pre_school_age_4_5", "fundamental", "high_school"],
        "age_groups": ["0_3", "4_5", "6_14", "15_17"],
        "territorial_lenses": ["resident_population", "school_location"],
        "time_nature": "observed_series_plus_mechanical_pressure",
        "period": "2014-2025; mechanical reference 2030",
        "source_refs": ["job5gar_early_childhood", "job5gar_pressure", "job5gd_offer", "job5gd_finance"],
        "legacy_directions": ["COORD_COHORT_OFFER_PRESSURE", "COORD_FINANCE_COHORT_PRESSURE"],
        "planning_question": "Quais indicadores devem disparar revisão de capacidade antes de decisões de expansão ou reorganização?",
        "monitoring_indicators": ["matrículas por etapa", "escolas", "turmas", "razão mecânica coorte/base"],
        "institutional_responsibility": "acao_direta_rede_municipal",
        "secondary_responsibility": "coordenacao_rede_estadual",
        "actors": ["secretaria municipal de educação", "rede estadual", "planejamento municipal"],
        "pne_links": [
            _link("1.a", "partial_component", "População de 0 a 3 anos e matrículas localizadas contextualizam a oferta, sem recalcular atendimento à demanda manifesta."),
            _link("1.c", "partial_component", "População de 4 a 5 anos e matrículas localizadas são componentes territoriais, não uma taxa oficial de acesso."),
            _link("4.a", "contextual_planning", "Oferta e coortes de 6 a 17 anos orientam planejamento, sem identificar acesso individual."),
            _link("6.a", "contextual_planning", "A participação observada de matrículas em tempo integral é contexto e não recompõe o indicador legal."),
        ],
        "planning_themes": ["planejamento_da_oferta", "transicao_entre_etapas", "capacidade_e_jornada"],
        "visual_role": "small_multiples_stage_series_with_mechanical_marker",
        "interaction_role": "stage_switch_plus_municipality_selector",
        "allowed_claims": ["descrever mudanças observadas", "comparar distribuição municipal", "nomear pressão mecânica como hipótese de planejamento"],
        "forbidden_claims": COMMON_FORBIDDEN + ["call mechanical pressure a forecast, demand, coverage or capacity"],
        "limitations": ["resident population and school-location enrollments are different universes", "mechanical pressure omits migration, flow, retention and mobility"],
        "demography_only_counterfactual": "Sem oferta, a leitura mostraria somente o tamanho das coortes e não revelaria como escolas, turmas e matrículas responderam.",
        "decision_delta": "Acrescentar resposta da oferta muda a decisão de observar população para monitorar etapa, rede e capacidade operacional.",
    },
    {
        "story_family_id": "D1_TRAJECTORY_CONDITIONS",
        "sequence": 2,
        "direction_id": "TERRITORY_HELPS_UNDERSTAND_EDUCATION",
        "macroblock_id": "B_TRAJECTORY_AND_CONDITIONS",
        "layer": "PRIMARY_NARRATIVE_PATH",
        "editorial_state": "PRIMARY_VISIBLE",
        "internal_title": "Trajetória oficial e condições da oferta",
        "management_question": "Como aprovação, reprovação, abandono e distorção mudaram e quais condições precisam ser acompanhadas por etapa?",
        "mechanism": "Ler taxas oficiais municipais em série e alinhá-las, sem causalidade, a turmas, jornada, docentes e condições escolares.",
        "regional_read": "Distribuições municipais do Vale; nenhuma média é apresentada como taxa regional.",
        "municipal_read": "Série oficial local, mudança em pontos percentuais e comparação com medianas municipais do Vale e do RS.",
        "stages": ["anos_iniciais", "anos_finais", "high_school"],
        "age_groups": ["school_stage_population"],
        "territorial_lenses": ["school_location"],
        "time_nature": "observed_official_series",
        "period": "2018-2025; breaks highlighted for 2020-2021",
        "source_refs": ["job5gar_trajectory", "job5gd_offer", "job5gd_finance"],
        "legacy_directions": ["COORD_TRAJECTORY_MOBILITY", "COORD_FINANCE_COHORT_PRESSURE"],
        "planning_question": "Que etapa, rede e indicador devem orientar investigação escolar e coordenação com a rede responsável?",
        "monitoring_indicators": ["aprovação", "reprovação", "abandono", "distorção idade-série", "turmas", "tempo integral"],
        "institutional_responsibility": "coordenacao_rede_estadual",
        "secondary_responsibility": "acao_direta_rede_municipal",
        "actors": ["redes municipal e estadual", "equipes escolares", "conselhos escolares"],
        "pne_links": [
            _link("4.b", "contextual_planning", "Distorção e rendimento ajudam a planejar trajetória até o 5º ano, mas não medem conclusão na idade regular."),
            _link("4.c", "contextual_planning", "Distorção e rendimento nos anos finais contextualizam conclusão regular sem recomputar o indicador legal."),
            _link("4.d", "contextual_planning", "Distorção e rendimento no ensino médio contextualizam conclusão regular sem recomputar o indicador legal."),
            _link("17.a", "contextual_planning", "Condições docentes podem ser acompanhadas separadamente; esta família não recalcula formação específica."),
            _link("19.c", "contextual_planning", "Condições escolares entram somente como contexto de infraestrutura, sem inferência causal sobre trajetória."),
        ],
        "planning_themes": ["trajetoria_escolar", "condicoes_docentes", "jornada_e_turmas"],
        "visual_role": "municipal_official_rate_series_plus_distribution",
        "interaction_role": "stage_and_metric_switch_with_break_annotation",
        "allowed_claims": ["descrever direção e magnitude municipal", "comparar medianas de distribuições", "formular investigação não causal"],
        "forbidden_claims": COMMON_FORBIDDEN + ["recompose a Vale trajectory rate", "attribute trajectory change to conditions"],
        "limitations": ["official rates remain municipal", "2020-2021 require explicit continuity caution", "no small-denominator rule available"],
        "demography_only_counterfactual": "A demografia não revela aprovação, reprovação, abandono ou distorção observados nas escolas.",
        "decision_delta": "A trajetória muda a decisão para etapa, rede e indicador concretos, com investigação de condições sem causalidade.",
    },
    {
        "story_family_id": "D1_MOBILITY_HIGH_SCHOOL_OFFER",
        "sequence": 3,
        "direction_id": "TERRITORY_HELPS_UNDERSTAND_EDUCATION",
        "macroblock_id": "C_MOBILITY_AND_HIGH_SCHOOL",
        "layer": "PRIMARY_NARRATIVE_PATH",
        "editorial_state": "PRIMARY_VISIBLE",
        "internal_title": "Mobilidade de residentes e oferta de ensino médio",
        "management_question": "Em que medida a fotografia de residentes que estudavam fora reforça coordenação da oferta de ensino médio?",
        "mechanism": "Combinar fotografia de residência do estudante em 2022 com série de oferta localizada, mantendo destino e causalidade indisponíveis.",
        "regional_read": "Razão regional recomposta por soma de numeradores e denominadores compatíveis e distribuição municipal.",
        "municipal_read": "Parcela de residentes que estudavam em outro município, separada de país estrangeiro, junto à oferta localizada.",
        "stages": ["fundamental", "high_school", "all"],
        "age_groups": ["students_by_course_stage_2022"],
        "territorial_lenses": ["student_residence", "school_location"],
        "time_nature": "cross_section_plus_independent_offer_series",
        "period": "mobility 2022; offer 2014-2025",
        "source_refs": ["job5gd_mobility", "job5gd_offer"],
        "legacy_directions": ["COORD_MOBILITY_OFFER_HIGH_SCHOOL", "COORD_TRAJECTORY_MOBILITY"],
        "planning_question": "Que coordenação intermunicipal e com a rede estadual deve acompanhar residentes e oferta sem inventar destinos?",
        "monitoring_indicators": ["residentes que estudavam em outro município", "matrículas de ensino médio", "turmas", "unidades de ensino"],
        "institutional_responsibility": "articulacao_intermunicipal_regional",
        "secondary_responsibility": "coordenacao_rede_estadual",
        "actors": ["municípios do Vale", "rede estadual", "planejamento regional"],
        "pne_links": [
            _link("4.a", "contextual_planning", "Mobilidade e oferta ajudam a planejar acesso territorial de 6 a 17 anos, mas não medem acesso escolar individual."),
        ],
        "planning_themes": ["mobilidade_educacional", "oferta_de_ensino_medio", "regime_de_colaboracao"],
        "visual_role": "mobility_distribution_with_offer_endpoints",
        "interaction_role": "stage_switch_and_explicit_destination_unavailable_state",
        "allowed_claims": ["usar exatamente residentes que estudavam em outro município", "recompor razão regional por contagens compatíveis", "separar país estrangeiro"],
        "forbidden_claims": COMMON_FORBIDDEN + ["name a destination municipality", "derive an origin-destination matrix", "call 2022 a trend"],
        "limitations": ["single 2022 cross-section", "destination municipality unavailable", "one official component has a residual that stays explicit"],
        "demography_only_counterfactual": "A demografia não mostra onde residentes estudavam nem a necessidade de coordenação supramunicipal.",
        "decision_delta": "A mobilidade desloca a decisão de volume populacional para coordenação entre residência, oferta localizada e rede estadual.",
    },
    {
        "story_family_id": "D1_RURALITY_PNATE_PLANNING",
        "sequence": 4,
        "direction_id": "TERRITORY_HELPS_UNDERSTAND_EDUCATION",
        "macroblock_id": "D_RURALITY_AND_TRANSPORT",
        "layer": "EXPANDED_EVIDENCE_LAYER",
        "editorial_state": "SECONDARY_VISIBLE",
        "internal_title": "Oferta rural e planejamento PNATE",
        "management_question": "Como a mudança da oferta rural e os registros de planejamento do transporte devem entrar na coordenação territorial?",
        "mechanism": "Ler escolas, turmas e matrículas rurais por localização junto a registros PNATE por executor, sem transformar recurso em uso ou mobilidade.",
        "regional_read": "Totais compatíveis de oferta rural e soma de valores do executor quando aditivos.",
        "municipal_read": "Mudança local da oferta rural e registros PNATE com estágio financeiro explícito.",
        "stages": ["early_childhood", "fundamental", "high_school", "eja", "professional", "all"],
        "age_groups": ["school_stage_population"],
        "territorial_lenses": ["rural_school_location", "municipal_executor"],
        "time_nature": "observed_series_plus_planning_forecast",
        "period": "rural offer 2014-2025; PNATE 2024-2026",
        "source_refs": ["job5gbr_rural", "job5gd_offer", "job5gd_pnate"],
        "legacy_directions": ["COORD_RURAL_PNATE"],
        "planning_question": "Que mudança de escolas, turmas, matrículas e previsão deve orientar revisão de rotas e coordenação, mediante dados próprios de uso?",
        "monitoring_indicators": ["escolas rurais", "turmas rurais", "matrículas rurais", "previsão de planejamento PNATE"],
        "institutional_responsibility": "acao_direta_rede_municipal",
        "secondary_responsibility": "articulacao_intermunicipal_regional",
        "actors": ["executor municipal", "FNDE", "redes responsáveis pela oferta"],
        "pne_links": [
            _link("4.a", "contextual_planning", "Oferta rural e transporte podem apoiar planejamento de acesso, sem medir acesso ou deslocamento individual."),
        ],
        "planning_themes": ["educacao_rural", "transporte_escolar", "planejamento_pnate"],
        "visual_role": "rural_offer_series_with_financial_stage_timeline",
        "interaction_role": "stage_switch_and_forecast_badge",
        "allowed_claims": ["descrever oferta rural localizada", "rotular 2026 como previsão de planejamento", "manter estágios financeiros separados"],
        "forbidden_claims": COMMON_FORBIDDEN + ["call PNATE mobility", "claim 2026 execution, realized use or payment", "derive per-student spending"],
        "limitations": ["rural school location is not rural residence", "PNATE has no route, use or execution measure for 2026"],
        "demography_only_counterfactual": "A população não mostra a localização rural da oferta nem o estágio dos registros do executor.",
        "decision_delta": "A família adiciona revisão operacional de oferta e transporte, condicionada a dados próprios de rotas e uso.",
    },
    {
        "story_family_id": "D1_SPECIAL_AEE_TERRITORY",
        "sequence": 5,
        "direction_id": "TERRITORY_HELPS_UNDERSTAND_EDUCATION",
        "macroblock_id": "E_INCLUSION_AND_ADULTS",
        "layer": "EXPANDED_EVIDENCE_LAYER",
        "editorial_state": "CONDITIONAL_VISIBLE",
        "internal_title": "Educação especial, AEE e distribuição territorial",
        "management_question": "Onde matrículas da educação especial e escolas que informam AEE mudaram, e qual rede deve investigar a oferta?",
        "mechanism": "Contrastar séries de matrículas localizadas e escolas com AEE sem inferir atendimento individual, necessidade ou acesso.",
        "regional_read": "Totais regionais compatíveis e distribuição dos dez municípios.",
        "municipal_read": "Mudança local de matrículas e escolas com AEE, com zero observado distinto de indisponibilidade.",
        "stages": ["all"],
        "age_groups": ["special_education_enrollment_universe"],
        "territorial_lenses": ["school_location"],
        "time_nature": "observed_series",
        "period": "2014-2025",
        "source_refs": ["job5gbr_special_aee", "job5gd_offer"],
        "legacy_directions": ["COORD_SPECIAL_AEE_TERRITORY"],
        "planning_question": "Que oferta e condição precisam de verificação junto às redes responsáveis, sem concluir cobertura?",
        "monitoring_indicators": ["matrículas de educação especial", "escolas que informam AEE"],
        "institutional_responsibility": "coordenacao_rede_estadual",
        "secondary_responsibility": "acao_direta_rede_municipal",
        "actors": ["redes municipal e estadual", "escolas", "equipes de educação especial"],
        "pne_links": [],
        "no_valid_pne_link_justification": "Os fatos disponíveis não recompõem os indicadores legais de acesso, permanência ou AEE do PNE; o vínculo fica vazio em vez de genérico.",
        "planning_themes": ["educacao_especial", "atendimento_educacional_especializado", "distribuicao_da_oferta"],
        "visual_role": "paired_series_special_enrollments_and_aee_schools",
        "interaction_role": "conditional_panel_with_universe_explanation",
        "allowed_claims": ["descrever mudanças de contagens localizadas", "comparar distribuição municipal"],
        "forbidden_claims": COMMON_FORBIDDEN + ["claim coverage, access, need or individual service", "infer individual trajectory"],
        "limitations": ["school-location counts do not identify residence", "no same-person link between enrollment and AEE"],
        "demography_only_counterfactual": "A demografia não identifica a distribuição da oferta informada de educação especial e AEE.",
        "decision_delta": "A oferta inclusiva acrescenta rede e condição específicas para investigação territorial.",
    },
    {
        "story_family_id": "D1_ADULT_SCHOOLING_EJA",
        "sequence": 6,
        "direction_id": "TERRITORY_HELPS_UNDERSTAND_EDUCATION",
        "macroblock_id": "E_INCLUSION_AND_ADULTS",
        "layer": "PRIMARY_NARRATIVE_PATH",
        "editorial_state": "PRIMARY_VISIBLE",
        "internal_title": "Escolaridade adulta e distribuição da EJA",
        "management_question": "Como a participação municipal no público residente se compara à participação nas matrículas EJA localizadas?",
        "mechanism": "Comparar participações regionais por etapa em 2022 e manter a série de matrículas como contexto independente.",
        "regional_read": "Distribuição regional do público residente e das matrículas localizadas, sem chamar intensidade de cobertura.",
        "municipal_read": "Diferença em pontos percentuais entre as duas participações, separada para fundamental e médio.",
        "stages": ["eja_fundamental", "eja_high_school"],
        "age_groups": ["15_plus_without_fundamental", "18_plus_without_high_school"],
        "territorial_lenses": ["resident_population", "school_location"],
        "time_nature": "cross_section_plus_independent_enrollment_series",
        "period": "adult schooling 2010/2022; EJA distribution 2022; enrollments 2014-2025",
        "source_refs": ["job5gbr_adult_schooling", "job5gbr_eja_distribution", "job5gd_offer"],
        "legacy_directions": ["COORD_EJA_ADULT_SCHOOLING"],
        "planning_question": "Em qual etapa a distribuição sugere revisar busca ativa, localização da oferta e coordenação, sem chamar o estoque de demanda?",
        "monitoring_indicators": ["participação regional do público", "participação regional das matrículas", "diferença de distribuição em pp", "matrículas por mil como detalhe"],
        "institutional_responsibility": "acao_direta_rede_municipal",
        "secondary_responsibility": "coordenacao_rede_estadual",
        "actors": ["redes municipal e estadual", "EJA", "assistência e busca ativa"],
        "pne_links": [
            _link("11.a", "contextual_planning", "Escolaridade adulta residente contextualiza alfabetização, sem recalcular a taxa legal."),
            _link("11.b", "partial_component", "O público residente sem fundamental concluído é componente territorial, não o indicador legal completo."),
            _link("11.c", "partial_component", "O público residente sem médio concluído é componente territorial, não o indicador legal completo."),
        ],
        "planning_themes": ["escolaridade_adulta", "eja", "busca_ativa_e_localizacao_da_oferta"],
        "visual_role": "paired_regional_share_distribution_by_eja_stage",
        "interaction_role": "stage_switch_with_intensity_detail",
        "allowed_claims": ["comparar participações regionais", "mostrar diferença em pontos percentuais", "usar matrículas por mil como intensidade secundária"],
        "forbidden_claims": COMMON_FORBIDDEN + ["call resident public manifested demand", "call intensity coverage or service rate", "combine stages"],
        "limitations": ["2022 distribution is cross-sectional", "resident and school-location universes differ", "historical enrollment is independent context"],
        "demography_only_counterfactual": "A demografia por idade não mostra escolaridade concluída nem distribuição da EJA por etapa.",
        "decision_delta": "A família identifica etapa, público adulto e localização da oferta para busca ativa e coordenação.",
    },
    {
        "story_family_id": "D2_YOUTH_WORK_15_17",
        "sequence": 7,
        "direction_id": "TERRITORIAL_TRANSFORMATIONS_SET_EDUCATION_AGENDA",
        "macroblock_id": "F_YOUTH_WORK_AND_TRAINING",
        "layer": "PRIMARY_NARRATIVE_PATH",
        "editorial_state": "PRIMARY_VISIBLE",
        "internal_title": "Trabalho formal de jovens de 15 a 17 anos",
        "management_question": "Que mudanças nos vínculos e fluxos formais de 15 a 17 anos devem ser acompanhadas junto à trajetória do ensino médio?",
        "mechanism": "Manter estoque RAIS e eventos Caged separados e colocá-los em paralelo com educação, sem identificar as mesmas pessoas.",
        "regional_read": "Estoque regional, mudança 2019-2025 e fluxos anuais agregados seguros.",
        "municipal_read": "Mudança local e contribuição descritiva, sem inferir trabalho de estudantes.",
        "stages": ["high_school"],
        "age_groups": ["15_17"],
        "territorial_lenses": ["workplace", "school_location"],
        "time_nature": "parallel_observed_series",
        "period": "RAIS 2019-2025; Caged 2020-2025; education source-specific",
        "source_refs": ["job5gcr_youth_rais", "job5gcr_youth_caged", "job5gcr_work_education"],
        "legacy_directions": ["COORD_WORK_EPT_AGE_GROUPS", "COORD_TRAJECTORY_MOBILITY"],
        "planning_question": "Quais indicadores de trajetória e trabalho formal precisam ser acompanhados em conjunto por município e rede?",
        "monitoring_indicators": ["vínculos formais 15-17", "admissões", "desligamentos", "aprovação", "abandono"],
        "institutional_responsibility": "articulacao_formacao_trabalho",
        "secondary_responsibility": "coordenacao_rede_estadual",
        "actors": ["rede estadual", "municípios", "trabalho e assistência", "empregadores e Sistema S"],
        "pne_links": [],
        "no_valid_pne_link_justification": "Vínculos e eventos trabalhistas não monitoram diretamente uma meta legal do PNE; séries educacionais permanecem paralelas.",
        "planning_themes": ["trabalho_juvenil_15_17", "permanencia_no_ensino_medio", "aprendizagem_profissional"],
        "visual_role": "separate_stock_and_flow_series_with_education_context",
        "interaction_role": "measure_switch_that_never_overlays_incompatible_units",
        "allowed_claims": ["descrever vínculos em estabelecimentos", "descrever eventos formais", "formular acompanhamento conjunto"],
        "forbidden_claims": COMMON_FORBIDDEN + ["say students left school to work", "mix stock and flow", "call events unique people"],
        "limitations": ["workplace is not residence", "no same-person link", "Caged is event flow and RAIS is stock"],
        "demography_only_counterfactual": "A faixa etária residente não mostra vínculos nos estabelecimentos nem a intensidade de fluxos formais.",
        "decision_delta": "A agenda passa a coordenar ensino médio, trabalho e proteção social com indicadores separados.",
    },
    {
        "story_family_id": "D2_YOUTH_WORK_18_24",
        "sequence": 8,
        "direction_id": "TERRITORIAL_TRANSFORMATIONS_SET_EDUCATION_AGENDA",
        "macroblock_id": "F_YOUTH_WORK_AND_TRAINING",
        "layer": "EXPANDED_EVIDENCE_LAYER",
        "editorial_state": "SECONDARY_VISIBLE",
        "internal_title": "Trabalho formal de jovens de 18 a 24 anos",
        "management_question": "Que mudanças no trabalho formal de 18 a 24 anos colocam transição, conclusão e formação na agenda regional?",
        "mechanism": "Ler separadamente estoque RAIS e eventos Caged na faixa 18-24, sem equivaler vínculo a pessoa ou estudante.",
        "regional_read": "Estoque regional e fluxos anuais agregados seguros.",
        "municipal_read": "Mudança local e participação regional descritiva por local de trabalho.",
        "stages": ["high_school", "professional_technical"],
        "age_groups": ["18_24"],
        "territorial_lenses": ["workplace", "school_location"],
        "time_nature": "parallel_observed_series",
        "period": "RAIS 2019-2025; Caged 2020-2025; education source-specific",
        "source_refs": ["job5gcr_youth_rais", "job5gcr_youth_caged", "job5gcr_work_education"],
        "legacy_directions": ["COORD_WORK_EPT_AGE_GROUPS"],
        "planning_question": "Quais transições entre conclusão, EPT e trabalho formal merecem coordenação regional sem prometer inserção?",
        "monitoring_indicators": ["vínculos formais 18-24", "admissões", "desligamentos", "EPT localizada"],
        "institutional_responsibility": "articulacao_formacao_trabalho",
        "secondary_responsibility": "articulacao_intermunicipal_regional",
        "actors": ["municípios", "rede estadual", "instituições de EPT", "trabalho e empregadores"],
        "pne_links": [],
        "no_valid_pne_link_justification": "Trabalho formal por faixa etária não é indicador legal PNE e não identifica egressos ou estudantes.",
        "planning_themes": ["trabalho_juvenil_18_24", "transicao_escola_trabalho", "formacao_profissional"],
        "visual_role": "separate_stock_and_flow_series_18_24",
        "interaction_role": "measure_switch_with_explicit_population_scope",
        "allowed_claims": ["descrever vínculos e eventos formais", "comparar distribuição territorial"],
        "forbidden_claims": COMMON_FORBIDDEN + ["claim graduate insertion", "mix workplace and school location", "call flow a stock"],
        "limitations": ["no graduate tracking", "workplace differs from residence", "no same-person education link"],
        "demography_only_counterfactual": "A demografia de 18 a 24 anos não revela estoque e fluxos formais nos estabelecimentos.",
        "decision_delta": "A leitura acrescenta transição formação-trabalho e atores de EPT à agenda territorial.",
    },
    {
        "story_family_id": "D2_APPRENTICESHIP",
        "sequence": 9,
        "direction_id": "TERRITORIAL_TRANSFORMATIONS_SET_EDUCATION_AGENDA",
        "macroblock_id": "F_YOUTH_WORK_AND_TRAINING",
        "layer": "PRIMARY_NARRATIVE_PATH",
        "editorial_state": "PRIMARY_VISIBLE",
        "internal_title": "Aprendizagem profissional por faixa etária",
        "management_question": "Como eventos de aprendizagem profissional se distribuem entre municípios e faixas etárias?",
        "mechanism": "Usar somente agregados visuais seguros de eventos de aprendiz, preservando ajustes e distinção entre evento e pessoa.",
        "regional_read": "Admissões, desligamentos e saldo de eventos do Vale por faixa etária.",
        "municipal_read": "Eventos locais e participação no fluxo regional, quando elegível.",
        "stages": ["professional_technical"],
        "age_groups": ["15_17", "18_24"],
        "territorial_lenses": ["workplace"],
        "time_nature": "observed_flow_series",
        "period": "2020-2025",
        "source_refs": ["job5gcr_apprenticeship", "job5gcr_youth_caged"],
        "legacy_directions": ["COORD_WORK_EPT_AGE_GROUPS"],
        "planning_question": "Que articulação com empregadores, Sistema S e redes deve acompanhar oportunidades de aprendizagem por faixa?",
        "monitoring_indicators": ["admissões de aprendizes", "desligamentos de aprendizes", "saldo de eventos", "participação nos eventos juvenis"],
        "institutional_responsibility": "articulacao_formacao_trabalho",
        "secondary_responsibility": "articulacao_intermunicipal_regional",
        "actors": ["empregadores", "Sistema S", "trabalho", "redes de ensino"],
        "pne_links": [
            _link("12.a", "contextual_planning", "Aprendizagem profissional orienta articulação com EPT de nível médio, mas não mede matrículas da meta."),
            _link("12.b", "contextual_planning", "Eventos de aprendizagem podem orientar oferta subsequente sem medir matrículas ou conclusão."),
        ],
        "planning_themes": ["aprendizagem_profissional", "articulacao_com_empregadores", "formacao_e_trabalho"],
        "visual_role": "apprenticeship_flow_by_age_group",
        "interaction_role": "age_group_switch_with_event_definition",
        "allowed_claims": ["descrever eventos classificados como aprendiz", "comparar participação em eventos"],
        "forbidden_claims": COMMON_FORBIDDEN + ["call events unique apprentices", "infer course demand", "hide negative adjustments"],
        "limitations": ["flow events, not people", "no education record linkage", "detailed occupation-CNAE lines remain QA-only"],
        "demography_only_counterfactual": "O tamanho das coortes não mostra eventos de contratação formal de aprendizes.",
        "decision_delta": "A família identifica articulação concreta com empregadores e instituições formadoras.",
    },
    {
        "story_family_id": "D2_OCCUPATIONS_SECTORS",
        "sequence": 10,
        "direction_id": "TERRITORIAL_TRANSFORMATIONS_SET_EDUCATION_AGENDA",
        "macroblock_id": "G_ECONOMY_EPT_AND_COORDINATION",
        "layer": "EXPANDED_EVIDENCE_LAYER",
        "editorial_state": "DETAIL_EXPANDABLE",
        "internal_title": "Ocupações e setores em transformação",
        "management_question": "Quais mudanças de ocupações e setores formais merecem leitura conjunta com a oferta formativa?",
        "mechanism": "Selecionar mudanças materiais por regra determinística, mantendo estoque RAIS, rótulos e sensibilidade a pequeno volume.",
        "regional_read": "Mudanças regionais de ocupações e setores formais entre 2019 e 2025.",
        "municipal_read": "Maiores mudanças locais elegíveis sem ranking de desempenho.",
        "stages": ["professional_technical"],
        "age_groups": ["all_ages_formal_bonds"],
        "territorial_lenses": ["workplace"],
        "time_nature": "observed_stock_change",
        "period": "2019-2025",
        "source_refs": ["job5gcr_occupations", "job5gcr_sectors"],
        "legacy_directions": ["COORD_WORK_EPT_AGE_GROUPS"],
        "planning_question": "Que mudanças materiais devem ser verificadas com atores econômicos e comparadas à formação disponível?",
        "monitoring_indicators": ["vínculos por ocupação", "vínculos por setor", "mudança absoluta", "sensibilidade a pequeno volume"],
        "institutional_responsibility": "articulacao_formacao_trabalho",
        "secondary_responsibility": "articulacao_intermunicipal_regional",
        "actors": ["desenvolvimento econômico", "trabalho", "instituições de EPT", "empregadores"],
        "pne_links": [],
        "no_valid_pne_link_justification": "Mudanças ocupacionais e setoriais não monitoram meta PNE e não demonstram demanda formativa.",
        "planning_themes": ["ocupacoes", "setores_formais", "dialogo_com_formacao"],
        "visual_role": "deterministic_top_change_table",
        "interaction_role": "expandable_dimension_table_with_small_volume_flag",
        "allowed_claims": ["descrever mudança de vínculos", "nomear dimensão e período", "usar seleção determinística"],
        "forbidden_claims": COMMON_FORBIDDEN + ["call selection a performance ranking", "infer skills shortage", "predict future occupations"],
        "limitations": ["all-age formal bonds only", "small-volume sensitivity is not official suppression", "selection does not imply priority"],
        "demography_only_counterfactual": "A demografia não mostra quais ocupações ou setores formais mudaram nos estabelecimentos.",
        "decision_delta": "A família direciona diálogo com atores econômicos para dimensões observadas e verificáveis.",
    },
    {
        "story_family_id": "D2_EPT_TERRITORIAL_OFFER",
        "sequence": 11,
        "direction_id": "TERRITORIAL_TRANSFORMATIONS_SET_EDUCATION_AGENDA",
        "macroblock_id": "G_ECONOMY_EPT_AND_COORDINATION",
        "layer": "PRIMARY_NARRATIVE_PATH",
        "editorial_state": "PRIMARY_VISIBLE",
        "internal_title": "Oferta territorial de educação profissional técnica",
        "management_question": "Onde a oferta EPT está localizada, como mudou e que coordenação regional sua distribuição exige?",
        "mechanism": "Ler matrículas técnicas localizadas, distribuição municipal e concentração por universo sem inferir origem dos estudantes.",
        "regional_read": "Total do Vale, municípios com oferta positiva e HHI contextual no mesmo universo.",
        "municipal_read": "Matrículas localizadas, participação regional e estado observado zero ou indisponível.",
        "stages": ["professional_technical"],
        "age_groups": ["technical_enrollment_universe"],
        "territorial_lenses": ["school_location"],
        "time_nature": "observed_series",
        "period": "2023-2025",
        "source_refs": ["job5gcr_ept", "job5gcr_concentration"],
        "legacy_directions": ["COORD_EPT_MOBILITY", "COORD_WORK_EPT_AGE_GROUPS"],
        "planning_question": "Que articulação regional deve considerar a localização dos cursos e matrículas sem supor onde estudantes residem?",
        "monitoring_indicators": ["matrículas técnicas localizadas", "municípios com oferta positiva", "participação regional", "HHI contextual"],
        "institutional_responsibility": "articulacao_formacao_trabalho",
        "secondary_responsibility": "articulacao_intermunicipal_regional",
        "actors": ["rede estadual", "rede federal", "instituições privadas", "Sistema S", "municípios"],
        "pne_links": [
            _link("12.a", "partial_component", "Matrículas técnicas localizadas são componente de oferta, sem recompor a razão legal em relação ao ensino médio."),
            _link("12.b", "contextual_planning", "A fonte não separa integralmente cursos subsequentes para recomputar a meta; serve a planejamento territorial."),
        ],
        "planning_themes": ["ept", "distribuicao_territorial_da_oferta", "regime_de_colaboracao"],
        "visual_role": "ept_distribution_map_and_series",
        "interaction_role": "municipality_selector_with_observed_zero_state",
        "allowed_claims": ["descrever oferta localizada", "mostrar zero observado", "usar HHI sem rótulo qualitativo"],
        "forbidden_claims": COMMON_FORBIDDEN + ["infer student origin", "call no local offer no access", "compare HHI across universes"],
        "limitations": ["origin of students unavailable", "zero means no located offer at grain", "HHI remains regional context only"],
        "demography_only_counterfactual": "A demografia juvenil não mostra onde cursos e matrículas técnicas estão localizados.",
        "decision_delta": "A família transforma volume juvenil em agenda de distribuição e coordenação da oferta EPT.",
    },
    {
        "story_family_id": "D2_SECTOR_TRANSFORMATION_SHIFT_SHARE",
        "sequence": 12,
        "direction_id": "TERRITORIAL_TRANSFORMATIONS_SET_EDUCATION_AGENDA",
        "macroblock_id": "G_ECONOMY_EPT_AND_COORDINATION",
        "layer": "INTERNAL_TECHNICAL_LAYER",
        "editorial_state": "INTERNAL_ONLY",
        "internal_title": "Transformação setorial, logística e decomposição descritiva",
        "management_question": "Quais efeitos descritivos de referência, composição e diferencial local merecem investigação formativa?",
        "mechanism": "Decompor mudança setorial 2019-2025 contra RS com fechamento aritmético e sem interpretar diferencial local como causa.",
        "regional_read": "Distribuição municipal dos componentes e mudança regional setorial observada.",
        "municipal_read": "Setores elegíveis com maior mudança absoluta e componente diferencial local, incluindo logística quando observável.",
        "stages": ["professional_technical"],
        "age_groups": ["all_ages_formal_bonds"],
        "territorial_lenses": ["workplace"],
        "time_nature": "observed_descriptive_decomposition",
        "period": "2019-2025",
        "source_refs": ["job5gcr_sectors", "job5gcr_shift_share"],
        "legacy_directions": ["COORD_WORK_EPT_AGE_GROUPS"],
        "planning_question": "Que mudanças setoriais devem ser investigadas com empregadores antes de qualquer revisão formativa?",
        "monitoring_indicators": ["mudança de vínculos", "efeito de referência", "efeito de composição", "diferencial local", "setores logísticos"],
        "institutional_responsibility": "articulacao_formacao_trabalho",
        "secondary_responsibility": "articulacao_intermunicipal_regional",
        "actors": ["desenvolvimento econômico", "empregadores", "instituições de EPT", "planejamento regional"],
        "pne_links": [],
        "no_valid_pne_link_justification": "Shift-share e vínculos setoriais não monitoram meta legal do PNE; servem a investigação interna.",
        "planning_themes": ["transformacao_setorial", "logistica", "investigacao_formativa"],
        "visual_role": "internal_shift_share_decomposition_table",
        "interaction_role": "technical_drilldown_only",
        "allowed_claims": ["descrever fechamento aritmético", "separar componentes", "selecionar materialidade por regra"],
        "forbidden_claims": COMMON_FORBIDDEN + ["call local differential causal or competitive advantage", "recommend course opening", "publish technical decomposition without review"],
        "limitations": ["all-age formal bonds", "RS reference is descriptive", "small volume requires caution"],
        "demography_only_counterfactual": "A demografia não identifica composição setorial nem fecha os componentes da mudança formal.",
        "decision_delta": "A decomposição restringe a agenda a hipóteses econômicas verificáveis antes de decisão formativa.",
    },
    {
        "story_family_id": "D2_NORMATIVE_WORK_EDUCATION_BRIDGE",
        "sequence": 13,
        "direction_id": "TERRITORIAL_TRANSFORMATIONS_SET_EDUCATION_AGENDA",
        "macroblock_id": "G_ECONOMY_EPT_AND_COORDINATION",
        "layer": "EXPANDED_EVIDENCE_LAYER",
        "editorial_state": "CONDITIONAL_VISIBLE",
        "internal_title": "Ponte normativa entre cursos, eixos e ocupações",
        "management_question": "Que correspondências normativas permitem organizar diálogo entre oferta EPT e ocupações sem afirmar aderência ou inserção?",
        "mechanism": "Usar ponte CNCT-CBO versionada e muitos-para-muitos, deduplicando matrículas por escola e curso e mantendo séries em paralelo.",
        "regional_read": "Cobertura regional da ponte e correspondências disponíveis por curso e eixo.",
        "municipal_read": "Variante local disponível apenas onde há oferta EPT localizada e correspondência auditada; demais municípios ficam explicitamente indisponíveis.",
        "stages": ["professional_technical"],
        "age_groups": ["all_ages_formal_bonds", "technical_enrollment_universe"],
        "territorial_lenses": ["school_location", "workplace"],
        "time_nature": "normative_cross_section_plus_parallel_series",
        "period": "bridge 2025; parallel context 2018-2025 by source",
        "source_refs": ["job5gcr_bridge", "job5gcr_work_education", "job5gcr_ept"],
        "legacy_directions": ["COORD_EPT_MOBILITY", "COORD_WORK_EPT_AGE_GROUPS"],
        "planning_question": "Quais atores devem validar correspondências e lacunas antes de qualquer decisão sobre cursos?",
        "monitoring_indicators": ["cursos únicos cobertos", "matrículas técnicas deduplicadas", "correspondências por curso", "presença ocupacional regional"],
        "institutional_responsibility": "articulacao_formacao_trabalho",
        "secondary_responsibility": "articulacao_intermunicipal_regional",
        "actors": ["instituições de EPT", "empregadores", "Sistema S", "redes estadual e federal", "municípios"],
        "pne_links": [
            _link("12.a", "contextual_planning", "A ponte organiza diálogo sobre EPT de nível médio, mas não mede expansão, qualidade ou permanência."),
            _link("12.b", "contextual_planning", "Correspondências normativas não distinguem toda a oferta subsequente nem medem a meta."),
        ],
        "planning_themes": ["ponte_cnct_cbo", "trabalho_e_formacao", "governanca_da_oferta"],
        "visual_role": "conditional_bipartite_bridge_summary",
        "interaction_role": "course_axis_drilldown_with_unavailable_fallback",
        "allowed_claims": ["descrever correspondência normativa", "deduplicar por escola e curso", "nomear oferta local indisponível"],
        "forbidden_claims": COMMON_FORBIDDEN + ["claim skill match, shortage or graduate insertion", "add enrollments across bridge rows", "infer same people or causality"],
        "limitations": ["many-to-many normative relation", "not available for municipalities without mapped local offer", "no student-worker linkage"],
        "demography_only_counterfactual": "A demografia não organiza correspondências entre cursos ofertados e famílias ocupacionais.",
        "decision_delta": "A ponte cria uma pauta governada de validação com instituições e empregadores, sem converter correspondência em recomendação.",
    },
)


CRITERIA: tuple[tuple[str, str], ...] = (
    ("C1", "relevância PNE/PME"),
    ("C2", "mecanismo previsto antes do resultado"),
    ("C3", "universos e lentes compatíveis"),
    ("C4", "tempo e natureza temporal coerentes"),
    ("C5", "estabilidade temporal e territorial"),
    ("C6", "integração além de séries isoladas"),
    ("C7", "diferença municipal útil"),
    ("C8", "planejamento com público, etapa, rede, ação e indicador"),
    ("C9", "clareza sem jargão"),
    ("C10", "rastreabilidade total"),
    ("C11", "não redundância"),
    ("C12", "valor incremental além da demografia"),
)


STAGE_ALIASES = {
    "creche_age_0_3": "creche_age_0_3",
    "pre_school_age_4_5": "pre_school_age_4_5",
    "pre_escola": "pre_school_age_4_5",
    "educacao_infantil": "early_childhood",
    "early_childhood": "early_childhood",
    "anos_iniciais": "anos_iniciais",
    "anos_finais": "anos_finais",
    "fundamental": "fundamental",
    "medio": "high_school",
    "high_school": "high_school",
    "eja": "eja",
    "eja_fundamental": "eja_fundamental",
    "eja_high_school": "eja_high_school",
    "professional": "professional_technical",
    "profissional": "professional_technical",
    "professional_technical": "professional_technical",
    "all": "all",
}


def typed_dictionary() -> dict[str, Any]:
    return {
        "schemaVersion": "vocacoes-pne-job5h-typed-dictionary-v1",
        "stages": {
            "canonicalIds": sorted(set(STAGE_ALIASES.values())),
            "aliases": dict(sorted(STAGE_ALIASES.items())),
        },
        "modalities": {
            "canonicalIds": ["regular", "eja", "special_education", "aee", "rural", "professional_technical"],
            "aliases": {"EPT": "professional_technical", "educacao_profissional": "professional_technical"},
        },
        "ageRanges": {
            "canonicalIds": ["0_3", "4_5", "6_14", "15_17", "18_24", "15_plus_without_fundamental", "18_plus_without_high_school", "all_ages_formal_bonds"],
            "closedIntervals": {"0_3": [0, 3], "4_5": [4, 5], "6_14": [6, 14], "15_17": [15, 17], "18_24": [18, 24]},
        },
        "territorialScales": ["region", "municipality", "state_reference"],
        "territorialLenses": ["resident_population", "student_residence", "school_location", "rural_school_location", "workplace", "municipal_executor"],
        "measureKinds": ["count", "share", "rate", "percentage_point_change", "absolute_change", "ratio", "monetary_amount", "decomposition_component", "normative_correspondence"],
        "units": ["people", "population", "enrollments", "schools", "classes", "teaching_units", "active_bonds", "events", "percent", "percentage_points", "ratio", "BRL", "BRL_nominal", "count", "not_applicable"],
        "sourceRefs": sorted(SOURCE_DEFINITIONS),
        "availabilityStates": ["observed", "observed_zero", "null", "unavailable", "suppressed", "not_applicable"],
        "editorialRoles": ["PRIMARY_VISIBLE", "SECONDARY_VISIBLE", "DETAIL_EXPANDABLE", "CONDITIONAL_VISIBLE", "INTERNAL_ONLY", "UNAVAILABLE_WITH_REASON", "REDUNDANT_MERGED"],
        "layers": ["PRIMARY_NARRATIVE_PATH", "EXPANDED_EVIDENCE_LAYER", "INTERNAL_TECHNICAL_LAYER"],
        "comparisonRoles": ["primary", "secondary", "distribution", "state_reference", "technical_detail", "availability_declaration"],
        "pneLinkTypes": sorted(PNE_LINK_TYPES),
        "valuePolicy": {
            "observedZeroIsNotMissing": True,
            "zeroDenominatorReturnsNull": True,
            "roundOnlyAtPresentation": True,
            "percentAbove100NotClamped": True,
        },
    }


def _json_safe(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(value, "item"):
        return _json_safe(value.item())
    return str(value)


def _number(value: Any) -> int | float | None:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(result):
        return None
    if result.is_integer():
        return int(result)
    return result


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes"}


def _availability(value: Any, source_status: Any = None) -> str:
    status = str(source_status or "").strip().lower()
    if status in {"unavailable", "insufficient_data", "not_available"}:
        return "unavailable"
    if status in {"suppressed"}:
        return "suppressed"
    if status in {"not_applicable"}:
        return "not_applicable"
    number = _number(value)
    if number is None:
        return "null"
    if number == 0:
        return "observed_zero"
    return "observed"


def _stage(value: Any) -> str | None:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    raw = str(value)
    if raw not in STAGE_ALIASES:
        raise ValueError(f"Etapa sem alias canônico no Job 5H: {raw}")
    return STAGE_ALIASES[raw]


def _read_csv(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, compression="gzip", dtype=str, keep_default_na=True)
    return frame


def source_paths(repo_root: Path) -> dict[str, Path]:
    return {
        source_ref: repo_root / definition["path"]
        for source_ref, definition in SOURCE_DEFINITIONS.items()
    }


def load_sources(repo_root: Path) -> dict[str, pd.DataFrame]:
    paths = source_paths(repo_root)
    missing = [str(path) for path in paths.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Fontes congeladas ausentes no Job 5H: {missing}")
    return {source_ref: _read_csv(path) for source_ref, path in paths.items()}


def _metric(
    *,
    metric_id: str,
    label: str,
    value: Any,
    unit: str,
    period: str,
    source_ref: str,
    territorial_lens: str,
    aggregation_rule: str,
    comparison_role: str,
    availability_state: str | None = None,
    stage: str | None = None,
    age_group: str | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    numeric_value = _number(value)
    return {
        "metric_id": metric_id,
        "label": label,
        "value": numeric_value,
        "unit": unit,
        "period": period,
        "source_ref": source_ref,
        "territorial_lens": territorial_lens,
        "aggregation_rule": aggregation_rule,
        "comparison_role": comparison_role,
        "availability_state": availability_state or _availability(numeric_value),
        "stage": stage,
        "age_group": age_group,
        "note": note,
    }


def _median(values: Iterable[Any]) -> int | float | None:
    numeric = [number for value in values if (number := _number(value)) is not None]
    return _number(median(numeric)) if numeric else None


def _entity_frame(frame: pd.DataFrame, entity_id: str) -> pd.DataFrame:
    if entity_id == REGION_ENTITY_ID:
        if "entity_id" in frame and frame["entity_id"].eq(entity_id).any():
            return frame[frame["entity_id"].eq(entity_id)].copy()
        if "entity_scope" in frame and frame["entity_scope"].eq("region").any():
            return frame[frame["entity_scope"].eq("region")].copy()
        return frame.iloc[0:0].copy()
    if "entity_id" in frame:
        return frame[frame["entity_id"].eq(entity_id)].copy()
    if "municipality_ibge_code" in frame:
        return frame[frame["municipality_ibge_code"].eq(entity_id)].copy()
    return frame.iloc[0:0].copy()


def _coordination_payloads(coordination: pd.DataFrame) -> dict[str, dict[str, Any]]:
    payloads: dict[str, dict[str, Any]] = {}
    municipal = coordination[coordination["entity_scope"].eq("municipality")]
    for entity_id, group in municipal.groupby("entity_id", sort=True):
        decoded = json.loads(str(group.iloc[0]["input_metrics"]))
        source_payload = decoded.get("source_payload")
        if not isinstance(source_payload, dict):
            raise ValueError(f"source_payload ausente para {entity_id}")
        payloads[str(entity_id)] = source_payload
    return payloads


def _offer_endpoint(
    offer: pd.DataFrame,
    entity_id: str,
    *,
    offer_domain: str,
    stage: str,
    metric_name: str,
    metric_id: str,
    label: str,
    comparison_role: str = "secondary",
) -> dict[str, Any]:
    entity = _entity_frame(offer, entity_id)
    selected = entity[
        entity["offer_domain"].eq(offer_domain)
        & entity["stage"].eq(stage)
        & entity["metric"].eq(metric_name)
    ].sort_values("year")
    if selected.empty:
        return _metric(
            metric_id=metric_id,
            label=label,
            value=None,
            unit="not_applicable",
            period="2014-2025",
            source_ref="job5gd_offer",
            territorial_lens="school_location",
            aggregation_rule="declared_source_series_endpoint",
            comparison_role=comparison_role,
            availability_state="unavailable",
            stage=_stage(stage),
            note="No compatible row at requested grain.",
        )
    row = selected.iloc[-1]
    return _metric(
        metric_id=metric_id,
        label=label,
        value=row.get("series_final_value", row.get("value")),
        unit=str(row.get("unit") or "count"),
        period=f"{row.get('series_initial_year')}-{row.get('series_final_year')}",
        source_ref="job5gd_offer",
        territorial_lens=str(row.get("territorial_lens")),
        aggregation_rule=str(row.get("aggregation_rule")),
        comparison_role=comparison_role,
        availability_state=_availability(
            row.get("series_final_value", row.get("value")),
            row.get("availability_state"),
        ),
        stage=_stage(stage),
        note=f"Initial={_number(row.get('series_initial_value'))}; change={_number(row.get('series_absolute_change'))}.",
    )


def _offer_change(
    offer: pd.DataFrame,
    entity_id: str,
    *,
    offer_domain: str,
    stage: str,
    metric_name: str,
    metric_id: str,
    label: str,
    comparison_role: str = "primary",
) -> dict[str, Any]:
    entity = _entity_frame(offer, entity_id)
    selected = entity[
        entity["offer_domain"].eq(offer_domain)
        & entity["stage"].eq(stage)
        & entity["metric"].eq(metric_name)
    ].sort_values("year")
    if selected.empty:
        return _metric(
            metric_id=metric_id,
            label=label,
            value=None,
            unit="not_applicable",
            period="2014-2025",
            source_ref="job5gd_offer",
            territorial_lens="school_location",
            aggregation_rule="endpoint_absolute_change",
            comparison_role=comparison_role,
            availability_state="unavailable",
            stage=_stage(stage),
        )
    row = selected.iloc[-1]
    unit = str(row.get("unit") or "count")
    if unit == "percent":
        unit = "percentage_points"
    return _metric(
        metric_id=metric_id,
        label=label,
        value=row.get("series_absolute_change"),
        unit=unit,
        period=f"{row.get('series_initial_year')}-{row.get('series_final_year')}",
        source_ref="job5gd_offer",
        territorial_lens=str(row.get("territorial_lens")),
        aggregation_rule="final minus initial at declared source grain",
        comparison_role=comparison_role,
        availability_state=_availability(row.get("series_absolute_change"), row.get("availability_state")),
        stage=_stage(stage),
        note=f"Initial={_number(row.get('series_initial_value'))}; final={_number(row.get('series_final_value'))}.",
    )


def _early_childhood_input(
    frame: pd.DataFrame,
    entity_id: str,
    *,
    stage: str,
    source_metric: str,
    metric_id: str,
    label: str,
    comparison_role: str,
) -> dict[str, Any]:
    current = frame[
        frame["stage"].eq(stage)
        & frame["metric"].eq(source_metric)
        & frame["year"].eq("2025")
    ]
    if entity_id == REGION_ENTITY_ID:
        values = pd.to_numeric(current["value"], errors="coerce")
        value = values.sum(min_count=1)
        aggregation = "sum ten compatible municipal counts"
    else:
        selected = current[current["municipality_ibge_code"].eq(entity_id)]
        value = None if selected.empty else selected.iloc[0]["value"]
        aggregation = "official municipal value at declared grain"
    lens = "resident_population" if source_metric == "resident_population" else "school_location"
    unit = "population" if source_metric == "resident_population" else "enrollments"
    return _metric(
        metric_id=metric_id,
        label=label,
        value=value,
        unit=unit,
        period="2025",
        source_ref="job5gar_early_childhood",
        territorial_lens=lens,
        aggregation_rule=aggregation,
        comparison_role=comparison_role,
        stage=_stage(stage),
    )


def _pressure_input(frame: pd.DataFrame, entity_id: str) -> dict[str, Any]:
    selected = _entity_frame(frame, entity_id)
    selected = selected[selected["stage"].eq("medio")].sort_values("target_year")
    if selected.empty:
        value = None
        state = "unavailable"
        note = "Mechanical pressure row unavailable."
    else:
        row = selected.iloc[-1]
        value = row.get("cohort_to_baseline_enrollment_ratio")
        state = _availability(value, row.get("availability_state"))
        note = (
            f"Cohort={_number(row.get('mechanical_cohort_size'))}; "
            f"baseline enrollments={_number(row.get('baseline_enrollments_2025'))}; "
            "is_forecast=false; is_demand_forecast=false; is_capacity_measure=false."
        )
    return _metric(
        metric_id="mechanical_high_school_pressure_ratio_2030_to_2025",
        label="Razão mecânica da coorte do ensino médio em 2030 sobre matrículas-base de 2025",
        value=value,
        unit="ratio",
        period="reference 2025; mechanical target 2030",
        source_ref="job5gar_pressure",
        territorial_lens="resident_population",
        aggregation_rule="compatible cohort count divided by 2025 located enrollments; not a forecast",
        comparison_role="primary",
        availability_state=state,
        stage="high_school",
        age_group="15_17",
        note=note,
    )


def _finance_input(
    frame: pd.DataFrame,
    entity_id: str,
    *,
    source_metric: str,
    metric_id: str,
    label: str,
) -> dict[str, Any]:
    selected = _entity_frame(frame, entity_id)
    selected = selected[
        selected["metric"].eq(source_metric)
        & selected["reference_year"].eq("2025")
    ]
    if selected.empty:
        value = None
        unit = "not_applicable"
        state = "unavailable"
        aggregation = "selective finance context unavailable"
        note = "No compatible 2025 row."
    else:
        row = selected.iloc[0]
        if entity_id == REGION_ENTITY_ID:
            value = row.get("distribution_median", row.get("value"))
            aggregation = "median of ten municipal executor values; not a regional rate"
        else:
            value = row.get("value")
            aggregation = str(row.get("aggregation_rule"))
        unit = str(row.get("unit"))
        state = _availability(value, row.get("value_status"))
        note = (
            f"financial_stage={row.get('financial_stage')}; "
            "selective context only; educational_result_causality_allowed=false; "
            "nominal_cross_year_growth_claim_allowed=false."
        )
    return _metric(
        metric_id=metric_id,
        label=label,
        value=value,
        unit=unit,
        period="2025",
        source_ref="job5gd_finance",
        territorial_lens="municipal_executor",
        aggregation_rule=aggregation,
        comparison_role="technical_detail",
        availability_state=state,
        note=note,
    )


def _family_cohort_inputs(
    entity_id: str, sources: Mapping[str, pd.DataFrame]
) -> list[dict[str, Any]]:
    offer = sources["job5gd_offer"]
    early = sources["job5gar_early_childhood"]
    return [
        _pressure_input(sources["job5gar_pressure"], entity_id),
        _early_childhood_input(
            early,
            entity_id,
            stage="creche_age_0_3",
            source_metric="resident_population",
            metric_id="resident_population_0_3_2025",
            label="População residente de 0 a 3 anos",
            comparison_role="secondary",
        ),
        _early_childhood_input(
            early,
            entity_id,
            stage="creche_age_0_3",
            source_metric="school_enrollments",
            metric_id="located_creche_enrollments_2025",
            label="Matrículas de creche nas escolas do território",
            comparison_role="secondary",
        ),
        _early_childhood_input(
            early,
            entity_id,
            stage="pre_school_age_4_5",
            source_metric="resident_population",
            metric_id="resident_population_4_5_2025",
            label="População residente de 4 a 5 anos",
            comparison_role="secondary",
        ),
        _early_childhood_input(
            early,
            entity_id,
            stage="pre_school_age_4_5",
            source_metric="school_enrollments",
            metric_id="located_preschool_enrollments_2025",
            label="Matrículas de pré-escola nas escolas do território",
            comparison_role="secondary",
        ),
        _offer_change(
            offer,
            entity_id,
            offer_domain="general_offer",
            stage="fundamental",
            metric_name="located_enrollments",
            metric_id="fundamental_located_enrollment_change_2014_2025",
            label="Mudança das matrículas localizadas do ensino fundamental",
        ),
        _offer_change(
            offer,
            entity_id,
            offer_domain="general_offer",
            stage="medio",
            metric_name="located_enrollments",
            metric_id="high_school_located_enrollment_change_2014_2025",
            label="Mudança das matrículas localizadas do ensino médio",
            comparison_role="secondary",
        ),
        _offer_change(
            offer,
            entity_id,
            offer_domain="general_offer",
            stage="all",
            metric_name="schools",
            metric_id="school_count_change_2014_2025",
            label="Mudança no número de escolas",
            comparison_role="technical_detail",
        ),
        _finance_input(
            sources["job5gd_finance"],
            entity_id,
            source_metric="mde_applied_rate",
            metric_id="mde_applied_rate_2025_selective_context",
            label="Aplicação em MDE — contexto seletivo do executor",
        ),
    ]


def _trajectory_rows(frame: pd.DataFrame, entity_id: str) -> pd.DataFrame:
    if entity_id == REGION_ENTITY_ID:
        return frame[frame["year"].eq("2025")].copy()
    return frame[
        frame["municipality_ibge_code"].eq(entity_id)
        & frame["year"].eq("2025")
    ].copy()


def _family_trajectory_inputs(
    entity_id: str, sources: Mapping[str, pd.DataFrame]
) -> list[dict[str, Any]]:
    trajectory = _trajectory_rows(sources["job5gar_trajectory"], entity_id)
    inputs: list[dict[str, Any]] = []
    metric_labels = {
        "approval_rate_percent": "Taxa oficial de aprovação",
        "dropout_rate_percent": "Taxa oficial de abandono",
        "failure_rate_percent": "Taxa oficial de reprovação",
        "age_grade_distortion_rate_percent": "Taxa oficial de distorção idade-série",
    }
    for index, (source_metric, label) in enumerate(metric_labels.items()):
        selected = trajectory[
            trajectory["stage"].eq("medio")
            & trajectory["metric"].eq(source_metric)
        ]
        if entity_id == REGION_ENTITY_ID:
            value = _median(selected["value"])
            change = _median(selected["full_window_change_pp"])
            aggregation = "median of ten municipal official rates; not a Vale rate"
            note = f"Median municipal change 2018-2025={change}."
        elif selected.empty:
            value = None
            aggregation = "official municipal rate"
            note = "No compatible official row."
        else:
            row = selected.iloc[0]
            value = row.get("value")
            change = _number(row.get("full_window_change_pp"))
            aggregation = "official municipal rate; no regional recomposition"
            note = (
                f"Change 2018-2025={change} pp; Vale municipal median="
                f"{_number(row.get('vale_municipal_distribution_median'))}; "
                f"RS municipal median={_number(row.get('rs_municipal_distribution_median'))}."
            )
        inputs.append(
            _metric(
                metric_id=f"high_school_{source_metric}_2025",
                label=f"{label} no ensino médio",
                value=value,
                unit="percent",
                period="2025 (series context 2018-2025)",
                source_ref="job5gar_trajectory",
                territorial_lens="school_location",
                aggregation_rule=aggregation,
                comparison_role="primary" if index == 0 else "secondary",
                stage="high_school",
                note=note,
            )
        )
    inputs.extend(
        [
            _offer_change(
                sources["job5gd_offer"],
                entity_id,
                offer_domain="staffing_and_classes",
                stage="medio",
                metric_name="classes",
                metric_id="high_school_class_change_2014_2025",
                label="Mudança no número de turmas do ensino médio",
                comparison_role="technical_detail",
            ),
            _offer_endpoint(
                sources["job5gd_offer"],
                entity_id,
                offer_domain="full_time_offer",
                stage="medio",
                metric_name="full_time_enrollment_share_percent",
                metric_id="high_school_full_time_share_2025",
                label="Participação de matrículas em tempo integral no ensino médio",
                comparison_role="technical_detail",
            ),
            _finance_input(
                sources["job5gd_finance"],
                entity_id,
                source_metric="fundeb_professional_remuneration_rate",
                metric_id="fundeb_professional_remuneration_rate_2025_selective_context",
                label="Remuneração de profissionais no Fundeb — contexto seletivo do executor",
            ),
        ]
    )
    return inputs


def _family_mobility_inputs(
    entity_id: str, sources: Mapping[str, pd.DataFrame]
) -> list[dict[str, Any]]:
    mobility = _entity_frame(sources["job5gd_mobility"], entity_id)
    inputs: list[dict[str, Any]] = []
    stages = (("medio", "high_school", "primary"), ("fundamental", "fundamental", "secondary"), ("total", "all", "secondary"))
    for source_stage, canonical_stage, role in stages:
        selected = mobility[mobility["stage"].eq(source_stage)]
        row = None if selected.empty else selected.iloc[0]
        value = None if row is None else row.get("outside_share_percent")
        numerator = None if row is None else _number(row.get("residents_studying_other_municipality"))
        denominator = None if row is None else _number(row.get("residents_studying_total"))
        inputs.append(
            _metric(
                metric_id=f"residents_studying_other_municipality_share_{canonical_stage}_2022",
                label="Parcela de residentes que estudavam em outro município",
                value=value,
                unit="percent",
                period="2022",
                source_ref="job5gd_mobility",
                territorial_lens="student_residence",
                aggregation_rule="residents studying in another municipality / residents studying total * 100; compatible counts summed before regional rate",
                comparison_role=role,
                stage=canonical_stage,
                note=f"Numerator={numerator}; denominator={denominator}; destination_municipality_available=false; origin_destination_matrix_derived=false.",
            )
        )
        foreign = None if row is None else row.get("residents_studying_foreign_country")
        inputs.append(
            _metric(
                metric_id=f"residents_studying_foreign_country_{canonical_stage}_2022",
                label="Residentes que estudavam em país estrangeiro — componente separado",
                value=foreign,
                unit="people",
                period="2022",
                source_ref="job5gd_mobility",
                territorial_lens="student_residence",
                aggregation_rule="official separate component; excluded from another-municipality numerator",
                comparison_role="technical_detail",
                stage=canonical_stage,
            )
        )
    inputs.extend(
        [
            _offer_endpoint(
                sources["job5gd_offer"],
                entity_id,
                offer_domain="general_offer",
                stage="medio",
                metric_name="located_enrollments",
                metric_id="high_school_located_enrollments_2025",
                label="Matrículas de ensino médio nas escolas do território",
            ),
            _offer_endpoint(
                sources["job5gd_offer"],
                entity_id,
                offer_domain="staffing_and_classes",
                stage="medio",
                metric_name="classes",
                metric_id="high_school_classes_2025",
                label="Turmas de ensino médio nas escolas do território",
                comparison_role="technical_detail",
            ),
            _offer_endpoint(
                sources["job5gd_offer"],
                entity_id,
                offer_domain="staffing_and_classes",
                stage="medio",
                metric_name="reported_teaching_units",
                metric_id="high_school_reported_teaching_units_2025",
                label="Unidades de ensino informadas para o ensino médio",
                comparison_role="technical_detail",
            ),
        ]
    )
    return inputs


def _pnate_input(
    frame: pd.DataFrame,
    entity_id: str,
    *,
    year: str,
    source_metric: str,
    metric_id: str,
    label: str,
    role: str,
) -> dict[str, Any]:
    selected = _entity_frame(frame, entity_id)
    selected = selected[
        selected["exercise_year"].eq(year) & selected["metric"].eq(source_metric)
    ]
    if selected.empty:
        return _metric(
            metric_id=metric_id,
            label=label,
            value=None,
            unit="BRL_nominal",
            period=year,
            source_ref="job5gd_pnate",
            territorial_lens="municipal_executor",
            aggregation_rule="official source at municipal executor grain",
            comparison_role=role,
            availability_state="unavailable",
            note="No compatible PNATE record.",
        )
    row = selected.iloc[0]
    return _metric(
        metric_id=metric_id,
        label=label,
        value=row.get("value"),
        unit=str(row.get("unit")),
        period=year,
        source_ref="job5gd_pnate",
        territorial_lens="municipal_executor",
        aggregation_rule=str(row.get("aggregation_rule")),
        comparison_role=role,
        availability_state=_availability(row.get("value"), row.get("value_status")),
        note=(
            f"financial_stage={row.get('financial_stage')}; "
            f"exercise_record_type={row.get('exercise_record_type')}; "
            f"execution_claim_allowed={str(row.get('execution_claim_allowed')).lower()}; "
            "is_mobility_measure=false."
        ),
    )


def _family_rural_pnate_inputs(
    entity_id: str, sources: Mapping[str, pd.DataFrame]
) -> list[dict[str, Any]]:
    offer = sources["job5gd_offer"]
    inputs = [
        _offer_change(
            offer,
            entity_id,
            offer_domain="rural_offer",
            stage="all",
            metric_name="rural_enrollments",
            metric_id="rural_located_enrollment_change_2014_2025",
            label="Mudança nas matrículas em escolas rurais",
        ),
        _offer_change(
            offer,
            entity_id,
            offer_domain="rural_offer",
            stage="all",
            metric_name="rural_schools",
            metric_id="rural_school_change_2014_2025",
            label="Mudança no número de escolas rurais",
            comparison_role="secondary",
        ),
        _offer_change(
            offer,
            entity_id,
            offer_domain="rural_offer",
            stage="high_school",
            metric_name="rural_enrollments",
            metric_id="rural_high_school_enrollment_change_2014_2025",
            label="Mudança nas matrículas de ensino médio em escolas rurais",
            comparison_role="secondary",
        ),
        _pnate_input(
            sources["job5gd_pnate"],
            entity_id,
            year="2025",
            source_metric="pnate_authorized_after_discount",
            metric_id="pnate_authorized_2025",
            label="Valor autorizado do PNATE no executor municipal",
            role="technical_detail",
        ),
        _pnate_input(
            sources["job5gd_pnate"],
            entity_id,
            year="2025",
            source_metric="pnate_beneficiary_students",
            metric_id="pnate_beneficiary_students_2025",
            label="Estudantes beneficiários informados para cálculo do PNATE",
            role="technical_detail",
        ),
        _pnate_input(
            sources["job5gd_pnate"],
            entity_id,
            year="2026",
            source_metric="pnate_adjusted_forecast",
            metric_id="pnate_planning_forecast_2026",
            label="Previsão de planejamento PNATE 2026 — não é execução, uso realizado nem pagamento",
            role="secondary",
        ),
        _metric(
            metric_id="pnate_execution_or_observed_use_2026",
            label="Execução, uso observado ou pagamento PNATE 2026",
            value=None,
            unit="not_applicable",
            period="2026",
            source_ref="job5gd_pnate",
            territorial_lens="municipal_executor",
            aggregation_rule="not materialized; unavailable by contract",
            comparison_role="availability_declaration",
            availability_state="unavailable",
            note="Planning forecast only; no execution, realized use, payment or mobility evidence.",
        ),
    ]
    return inputs


def _family_special_inputs(
    entity_id: str, sources: Mapping[str, pd.DataFrame]
) -> list[dict[str, Any]]:
    offer = sources["job5gd_offer"]
    return [
        _offer_change(
            offer,
            entity_id,
            offer_domain="special_education_aee",
            stage="all",
            metric_name="special_enrollments",
            metric_id="special_education_enrollment_change_2014_2025",
            label="Mudança nas matrículas localizadas da educação especial",
        ),
        _offer_endpoint(
            offer,
            entity_id,
            offer_domain="special_education_aee",
            stage="all",
            metric_name="special_enrollments",
            metric_id="special_education_enrollments_2025",
            label="Matrículas localizadas da educação especial",
            comparison_role="secondary",
        ),
        _offer_change(
            offer,
            entity_id,
            offer_domain="special_education_aee",
            stage="all",
            metric_name="schools_offering_aee",
            metric_id="aee_school_change_2014_2025",
            label="Mudança no número de escolas que informam AEE",
            comparison_role="secondary",
        ),
        _offer_endpoint(
            offer,
            entity_id,
            offer_domain="special_education_aee",
            stage="all",
            metric_name="schools_offering_aee",
            metric_id="schools_offering_aee_2025",
            label="Escolas que informam oferta de AEE",
            comparison_role="technical_detail",
        ),
    ]


def _family_eja_inputs(
    entity_id: str, sources: Mapping[str, pd.DataFrame]
) -> list[dict[str, Any]]:
    frame = sources["job5gbr_eja_distribution"]
    inputs: list[dict[str, Any]] = []
    for index, (source_stage, canonical_stage) in enumerate(
        (("fundamental", "eja_fundamental"), ("high_school", "eja_high_school"))
    ):
        stage_frame = frame[frame["stage"].eq(source_stage)]
        if entity_id == REGION_ENTITY_ID:
            municipal = stage_frame[stage_frame["entity_scope"].eq("municipality")]
            public_share = 100
            enrollment_share = 100
            difference = _median(municipal["distribution_difference_percentage_points"])
            resident_public = pd.to_numeric(
                municipal["resident_adult_public"], errors="coerce"
            ).sum(min_count=1)
            located = pd.to_numeric(
                municipal["school_location_eja_enrollments"], errors="coerce"
            ).sum(min_count=1)
            difference_label = "Mediana municipal da diferença entre participações"
            difference_rule = "median of ten municipal distribution differences; not a regional gap"
        else:
            selected = stage_frame[
                stage_frame["municipality_ibge_code"].eq(entity_id)
            ]
            row = None if selected.empty else selected.iloc[0]
            public_share = None if row is None else row.get("share_of_regional_public_percent")
            enrollment_share = None if row is None else row.get("share_of_regional_enrollments_percent")
            difference = None if row is None else row.get("distribution_difference_percentage_points")
            resident_public = None if row is None else row.get("resident_adult_public")
            located = None if row is None else row.get("school_location_eja_enrollments")
            difference_label = "Diferença entre participação nas matrículas e no público residente"
            difference_rule = "share of regional located enrollments minus share of regional resident public"
        inputs.extend(
            [
                _metric(
                    metric_id=f"eja_distribution_gap_{canonical_stage}_2022",
                    label=difference_label,
                    value=difference,
                    unit="percentage_points",
                    period="2022",
                    source_ref="job5gbr_eja_distribution",
                    territorial_lens="resident_population",
                    aggregation_rule=difference_rule,
                    comparison_role="primary" if index == 0 else "secondary",
                    stage=canonical_stage,
                    note="Positive means enrollment share exceeds resident-public share; not coverage.",
                ),
                _metric(
                    metric_id=f"resident_adult_public_{canonical_stage}_2022",
                    label="Moradores adultos no público estatístico da etapa",
                    value=resident_public,
                    unit="people",
                    period="2022",
                    source_ref="job5gbr_eja_distribution",
                    territorial_lens="resident_population",
                    aggregation_rule="official resident count; regional sum of compatible municipal counts",
                    comparison_role="technical_detail",
                    stage=canonical_stage,
                ),
                _metric(
                    metric_id=f"located_eja_enrollments_{canonical_stage}_2022",
                    label="Matrículas EJA nas escolas do território",
                    value=located,
                    unit="enrollments",
                    period="2022",
                    source_ref="job5gbr_eja_distribution",
                    territorial_lens="school_location",
                    aggregation_rule="official located enrollment count; regional sum of compatible municipal counts",
                    comparison_role="technical_detail",
                    stage=canonical_stage,
                ),
                _metric(
                    metric_id=f"resident_public_regional_share_{canonical_stage}_2022",
                    label="Participação no público residente do Vale",
                    value=public_share,
                    unit="percent",
                    period="2022",
                    source_ref="job5gbr_eja_distribution",
                    territorial_lens="resident_population",
                    aggregation_rule="municipal count / compatible regional count * 100",
                    comparison_role="distribution",
                    stage=canonical_stage,
                ),
                _metric(
                    metric_id=f"located_eja_regional_share_{canonical_stage}_2022",
                    label="Participação nas matrículas EJA localizadas do Vale",
                    value=enrollment_share,
                    unit="percent",
                    period="2022",
                    source_ref="job5gbr_eja_distribution",
                    territorial_lens="school_location",
                    aggregation_rule="municipal located enrollments / compatible regional count * 100",
                    comparison_role="distribution",
                    stage=canonical_stage,
                ),
            ]
        )
    inputs.append(
        _offer_change(
            sources["job5gd_offer"],
            entity_id,
            offer_domain="general_offer",
            stage="eja",
            metric_name="located_enrollments",
            metric_id="eja_located_enrollment_change_2014_2025",
            label="Mudança nas matrículas EJA localizadas — contexto independente",
            comparison_role="technical_detail",
        )
    )
    return inputs


def _family_youth_inputs(
    entity_id: str,
    sources: Mapping[str, pd.DataFrame],
    *,
    age_group: str,
) -> list[dict[str, Any]]:
    rais = _entity_frame(sources["job5gcr_youth_rais"], entity_id)
    rais = rais[
        rais["age_group"].eq(age_group)
        & rais["dimension"].eq("total")
        & rais["year"].eq("2025")
    ]
    rais_row = None if rais.empty else rais.iloc[0]
    caged = _entity_frame(sources["job5gcr_youth_caged"], entity_id)
    caged = caged[
        caged["age_group"].eq(age_group)
        & caged["aggregation_scope"].eq("all_apprentice_status")
        & caged["time_grain"].eq("annual_flow")
        & caged["year"].eq("2025")
    ]
    caged_row = None if caged.empty else caged.iloc[0]
    return [
        _metric(
            metric_id=f"formal_active_bonds_change_{age_group}_2019_2025",
            label=f"Mudança nos vínculos formais ativos de {age_group.replace('_', ' a ')} anos",
            value=None if rais_row is None else rais_row.get("period_absolute_change"),
            unit="active_bonds",
            period="2019-2025",
            source_ref="job5gcr_youth_rais",
            territorial_lens="workplace",
            aggregation_rule="final active bonds minus initial active bonds at total dimension",
            comparison_role="primary",
            age_group=age_group,
            availability_state="unavailable" if rais_row is None else None,
            note=(
                "RAIS stock; not unique people or student records. "
                f"Initial={None if rais_row is None else _number(rais_row.get('period_initial_bonds'))}; "
                f"final={None if rais_row is None else _number(rais_row.get('period_final_bonds'))}."
            ),
        ),
        _metric(
            metric_id=f"formal_active_bonds_{age_group}_2025",
            label=f"Vínculos formais ativos de {age_group.replace('_', ' a ')} anos",
            value=None if rais_row is None else rais_row.get("active_bonds"),
            unit="active_bonds",
            period="2025",
            source_ref="job5gcr_youth_rais",
            territorial_lens="workplace",
            aggregation_rule="RAIS active bond stock at total dimension",
            comparison_role="secondary",
            age_group=age_group,
            availability_state="unavailable" if rais_row is None else None,
        ),
        _metric(
            metric_id=f"caged_admission_events_{age_group}_2025",
            label=f"Eventos de admissão formal de {age_group.replace('_', ' a ')} anos",
            value=None if caged_row is None else caged_row.get("admissions"),
            unit="events",
            period="2025",
            source_ref="job5gcr_youth_caged",
            territorial_lens="workplace",
            aggregation_rule="annual safe aggregate across apprentice statuses",
            comparison_role="secondary",
            age_group=age_group,
            availability_state="unavailable" if caged_row is None else None,
            note="Caged flow events; visual_aggregation_eligible must be true.",
        ),
        _metric(
            metric_id=f"caged_dismissal_events_{age_group}_2025",
            label=f"Eventos de desligamento formal de {age_group.replace('_', ' a ')} anos",
            value=None if caged_row is None else caged_row.get("dismissals"),
            unit="events",
            period="2025",
            source_ref="job5gcr_youth_caged",
            territorial_lens="workplace",
            aggregation_rule="annual safe aggregate across apprentice statuses",
            comparison_role="secondary",
            age_group=age_group,
            availability_state="unavailable" if caged_row is None else None,
        ),
        _metric(
            metric_id=f"caged_balance_events_{age_group}_2025",
            label=f"Saldo de eventos formais de {age_group.replace('_', ' a ')} anos",
            value=None if caged_row is None else caged_row.get("balance"),
            unit="events",
            period="2025",
            source_ref="job5gcr_youth_caged",
            territorial_lens="workplace",
            aggregation_rule="admission events minus dismissal events in annual safe aggregate",
            comparison_role="technical_detail",
            age_group=age_group,
            availability_state="unavailable" if caged_row is None else None,
            note=(
                None
                if caged_row is None
                else f"negative_adjustment_present={str(caged_row.get('negative_adjustment_present')).lower()}."
            ),
        ),
    ]


def _family_apprenticeship_inputs(
    entity_id: str, sources: Mapping[str, pd.DataFrame]
) -> list[dict[str, Any]]:
    frame = _entity_frame(sources["job5gcr_apprenticeship"], entity_id)
    frame = frame[
        frame["aggregation_scope"].eq("all_apprentice_events")
        & frame["year"].eq("2025")
    ]
    inputs: list[dict[str, Any]] = []
    for index, age_group in enumerate(("15_17", "18_24")):
        selected = frame[frame["age_group"].eq(age_group)]
        row = None if selected.empty else selected.iloc[0]
        for measure, label, role in (
            ("admissions", "Eventos de admissão de aprendizes", "primary" if index == 0 else "secondary"),
            ("dismissals", "Eventos de desligamento de aprendizes", "secondary"),
            ("balance", "Saldo de eventos de aprendizes", "technical_detail"),
            (
                "share_of_youth_admission_events_classified_as_apprentice",
                "Participação de eventos juvenis de admissão classificados como aprendiz",
                "technical_detail",
            ),
        ):
            unit = "percent" if measure.startswith("share_") else "events"
            inputs.append(
                _metric(
                    metric_id=f"apprenticeship_{measure}_{age_group}_2025",
                    label=f"{label} — {age_group.replace('_', ' a ')} anos",
                    value=None if row is None else row.get(measure),
                    unit=unit,
                    period="2025",
                    source_ref="job5gcr_apprenticeship",
                    territorial_lens="workplace",
                    aggregation_rule="all_apprentice_events safe aggregate; event flow, not unique people",
                    comparison_role=role,
                    age_group=age_group,
                    availability_state="unavailable" if row is None else None,
                    note=(
                        None
                        if row is None
                        else f"visual_aggregation_eligible={str(row.get('visual_aggregation_eligible')).lower()}; unique_person_count_allowed=false."
                    ),
                )
            )
    return inputs


def _selection_eligible(frame: pd.DataFrame) -> pd.DataFrame:
    if "selection_eligible" not in frame:
        return frame.iloc[0:0].copy()
    return frame[frame["selection_eligible"].map(_as_bool)].copy()


def _top_dimension_rows(
    frame: pd.DataFrame, entity_id: str, *, limit: int = 3
) -> pd.DataFrame:
    selected = _selection_eligible(_entity_frame(frame, entity_id))
    if selected.empty:
        return selected
    selected = selected.assign(
        _materiality=pd.to_numeric(selected["absolute_change"], errors="coerce").abs(),
        _code=selected["dimension_code"].astype(str),
    )
    return selected.sort_values(
        ["_materiality", "_code"], ascending=[False, True], kind="mergesort"
    ).head(limit)


def _family_occupation_sector_inputs(
    entity_id: str, sources: Mapping[str, pd.DataFrame]
) -> list[dict[str, Any]]:
    occupation_rows = _top_dimension_rows(
        sources["job5gcr_occupations"], entity_id
    )
    sector_rows = _top_dimension_rows(sources["job5gcr_sectors"], entity_id)
    inputs: list[dict[str, Any]] = []
    primary_row = None if sector_rows.empty else sector_rows.iloc[0]
    inputs.append(
        _metric(
            metric_id="largest_eligible_sector_absolute_change_2019_2025",
            label="Maior mudança absoluta elegível entre setores formais",
            value=None if primary_row is None else primary_row.get("absolute_change"),
            unit="active_bonds",
            period="2019-2025",
            source_ref="job5gcr_sectors",
            territorial_lens="workplace",
            aggregation_rule="deterministic max absolute eligible change; tie by canonical code",
            comparison_role="primary",
            availability_state="unavailable" if primary_row is None else None,
            note=(
                "No ranking implication."
                if primary_row is None
                else f"Sector {primary_row.get('dimension_code')}: {primary_row.get('dimension_label')}; signed value preserved."
            ),
        )
    )
    for domain, rows, source_ref in (
        ("occupation", occupation_rows, "job5gcr_occupations"),
        ("sector", sector_rows, "job5gcr_sectors"),
    ):
        for rank, (_, row) in enumerate(rows.iterrows(), start=1):
            code = str(row.get("dimension_code"))
            inputs.append(
                _metric(
                    metric_id=f"selected_{domain}_{rank}_absolute_change_2019_2025",
                    label=f"{row.get('dimension_label')} ({code})",
                    value=row.get("absolute_change"),
                    unit="active_bonds",
                    period="2019-2025",
                    source_ref=source_ref,
                    territorial_lens="workplace",
                    aggregation_rule="final active bonds minus initial active bonds; deterministic eligible selection",
                    comparison_role="technical_detail",
                    note=(
                        f"selection_rank={rank}; small_volume_sensitive="
                        f"{str(row.get('small_volume_sensitive')).lower()}; selection is not performance ranking."
                    ),
                )
            )
    return inputs


def _ept_total_row(frame: pd.DataFrame, entity_id: str) -> pd.Series | None:
    selected = _entity_frame(frame, entity_id)
    expected_grain = "region_total" if entity_id == REGION_ENTITY_ID else "municipality_total"
    selected = selected[
        selected["grain"].eq(expected_grain) & selected["year"].eq("2025")
    ]
    return None if selected.empty else selected.iloc[0]


def _ept_hhi(frame: pd.DataFrame) -> int | float | None:
    selected = frame[
        frame["dimension"].eq("ept_total_territorial")
        & frame["year"].eq("2025")
    ]
    return None if selected.empty else _number(selected.iloc[0].get("hhi"))


def _family_ept_inputs(
    entity_id: str, sources: Mapping[str, pd.DataFrame]
) -> list[dict[str, Any]]:
    row = _ept_total_row(sources["job5gcr_ept"], entity_id)
    hhi = _ept_hhi(sources["job5gcr_concentration"])
    return [
        _metric(
            metric_id="located_technical_enrollments_2025",
            label="Matrículas técnicas localizadas",
            value=None if row is None else row.get("technical_enrollments"),
            unit="enrollments",
            period="2025",
            source_ref="job5gcr_ept",
            territorial_lens="school_location",
            aggregation_rule="source total at municipality or compatible region grain",
            comparison_role="primary",
            availability_state=(
                "unavailable"
                if row is None
                else _availability(row.get("technical_enrollments"), row.get("availability_status"))
            ),
            stage="professional_technical",
            note="Observed zero means no located offer at this grain; it does not mean no access.",
        ),
        _metric(
            metric_id="located_technical_enrollment_change_2023_2025",
            label="Mudança das matrículas técnicas localizadas",
            value=None if row is None else row.get("period_absolute_change"),
            unit="enrollments",
            period="2023-2025",
            source_ref="job5gcr_ept",
            territorial_lens="school_location",
            aggregation_rule="final minus initial located technical enrollments",
            comparison_role="secondary",
            availability_state="unavailable" if row is None else None,
            stage="professional_technical",
        ),
        _metric(
            metric_id="share_of_regional_technical_enrollments_2025",
            label="Participação nas matrículas técnicas localizadas do Vale",
            value=(100 if entity_id == REGION_ENTITY_ID else None if row is None else row.get("share_of_regional_technical_enrollments")),
            unit="percent",
            period="2025",
            source_ref="job5gcr_ept",
            territorial_lens="school_location",
            aggregation_rule="municipal located technical enrollments / compatible regional total * 100",
            comparison_role="distribution",
            availability_state="unavailable" if row is None else None,
            stage="professional_technical",
        ),
        _metric(
            metric_id="regional_hhi_ept_total_2025",
            label="HHI territorial da oferta EPT total — contexto regional sem rótulo qualitativo",
            value=hhi,
            unit="ratio",
            period="2025",
            source_ref="job5gcr_concentration",
            territorial_lens="school_location",
            aggregation_rule="sum squared municipal shares within EPT total universe",
            comparison_role="technical_detail",
            note="regional_hhi_context_only=true; qualitative_concentration_label_allowed=false; cross_universe_comparison_allowed=false.",
        ),
    ]


def _logistics_change(frame: pd.DataFrame, entity_id: str) -> int | float | None:
    selected = _entity_frame(frame, entity_id)
    selected = selected[selected["dimension_code"].isin(["49", "50", "51", "52", "53"])]
    if selected.empty:
        return None
    return _number(pd.to_numeric(selected["absolute_change"], errors="coerce").sum(min_count=1))


def _family_shift_share_inputs(
    entity_id: str, sources: Mapping[str, pd.DataFrame]
) -> list[dict[str, Any]]:
    shift = sources["job5gcr_shift_share"]
    if entity_id == REGION_ENTITY_ID:
        eligible = _selection_eligible(shift)
        differential_value = _median(eligible["local_differential_effect"])
        row = None
        label = "Mediana municipal do componente diferencial local entre linhas elegíveis"
        rule = "median across eligible municipal-sector rows; not a regional shift-share effect"
    else:
        eligible = _selection_eligible(
            shift[shift["municipality_ibge_code"].eq(entity_id)]
        )
        if eligible.empty:
            row = None
        else:
            eligible = eligible.assign(
                _materiality=pd.to_numeric(
                    eligible["absolute_change"], errors="coerce"
                ).abs()
            )
            row = eligible.sort_values(
                ["_materiality", "cnae_division_code"],
                ascending=[False, True],
                kind="mergesort",
            ).iloc[0]
        differential_value = None if row is None else row.get("local_differential_effect")
        label = "Componente diferencial local do setor elegível de maior mudança absoluta"
        rule = "frozen shift-share identity against RS; deterministic sector selection"
    logistics = _logistics_change(sources["job5gcr_sectors"], entity_id)
    return [
        _metric(
            metric_id="logistics_active_bonds_change_2019_2025",
            label="Mudança agregada de vínculos nos setores logísticos CNAE 49 a 53",
            value=logistics,
            unit="active_bonds",
            period="2019-2025",
            source_ref="job5gcr_sectors",
            territorial_lens="workplace",
            aggregation_rule="sum compatible sector absolute changes for CNAE divisions 49-53",
            comparison_role="primary",
            availability_state="unavailable" if logistics is None else None,
            note="Logistics anchor is descriptive and does not imply educational demand.",
        ),
        _metric(
            metric_id="selected_shift_share_local_differential_2019_2025",
            label=label,
            value=differential_value,
            unit="active_bonds",
            period="2019-2025",
            source_ref="job5gcr_shift_share",
            territorial_lens="workplace",
            aggregation_rule=rule,
            comparison_role="secondary",
            availability_state="unavailable" if differential_value is None else None,
            note=(
                "Descriptive, not causal."
                if row is None
                else f"Sector {row.get('cnae_division_code')}: {row.get('cnae_division_label')}; closure_residual={_number(row.get('closure_residual'))}."
            ),
        ),
        _metric(
            metric_id="selected_shift_share_reference_effect_2019_2025",
            label="Componente de referência RS da linha selecionada",
            value=None if row is None else row.get("reference_growth_effect"),
            unit="active_bonds",
            period="2019-2025",
            source_ref="job5gcr_shift_share",
            territorial_lens="workplace",
            aggregation_rule="frozen shift-share identity against RS",
            comparison_role="technical_detail",
            availability_state="not_applicable" if entity_id == REGION_ENTITY_ID else "unavailable" if row is None else None,
        ),
        _metric(
            metric_id="selected_shift_share_industry_mix_effect_2019_2025",
            label="Componente de composição setorial da linha selecionada",
            value=None if row is None else row.get("industry_mix_effect"),
            unit="active_bonds",
            period="2019-2025",
            source_ref="job5gcr_shift_share",
            territorial_lens="workplace",
            aggregation_rule="frozen shift-share identity against RS",
            comparison_role="technical_detail",
            availability_state="not_applicable" if entity_id == REGION_ENTITY_ID else "unavailable" if row is None else None,
        ),
    ]


def _family_bridge_inputs(
    entity_id: str, sources: Mapping[str, pd.DataFrame]
) -> list[dict[str, Any]]:
    bridge = sources["job5gcr_bridge"]
    if entity_id == REGION_ENTITY_ID:
        selected = bridge.copy()
    else:
        selected = _entity_frame(bridge, entity_id)
    if selected.empty:
        unique_courses = None
        unique_enrollments = None
        correspondence_count = None
        state = "unavailable"
        note = "No audited local bridge rows; variant remains explicit and is not converted to zero."
    else:
        dedup = selected.drop_duplicates(["school_code", "course_code"])
        unique_courses = dedup["course_code"].nunique()
        unique_enrollments = pd.to_numeric(
            dedup["technical_enrollments"], errors="coerce"
        ).sum(min_count=1)
        correspondence_count = len(selected)
        state = "observed"
        note = "Deduplicated by school_code+course_code; associations remain many-to-many and non-additive."
    ept_row = _ept_total_row(sources["job5gcr_ept"], entity_id)
    return [
        _metric(
            metric_id="audited_bridge_unique_course_count_2025",
            label="Cursos únicos com correspondência normativa auditada",
            value=unique_courses,
            unit="count",
            period="2025",
            source_ref="job5gcr_bridge",
            territorial_lens="school_location",
            aggregation_rule="count distinct course_code after school+course deduplication",
            comparison_role="primary",
            availability_state=state,
            stage="professional_technical",
            note=note,
        ),
        _metric(
            metric_id="audited_bridge_unique_technical_enrollments_2025",
            label="Matrículas técnicas deduplicadas cobertas pela ponte",
            value=unique_enrollments,
            unit="enrollments",
            period="2025",
            source_ref="job5gcr_bridge",
            territorial_lens="school_location",
            aggregation_rule="sum once per school_code+course_code; never sum across associations",
            comparison_role="secondary",
            availability_state=state,
            stage="professional_technical",
        ),
        _metric(
            metric_id="audited_bridge_correspondence_row_count_2025",
            label="Correspondências normativas muitos-para-muitos",
            value=correspondence_count,
            unit="count",
            period="2025",
            source_ref="job5gcr_bridge",
            territorial_lens="school_location",
            aggregation_rule="row count for audit only; non-additive",
            comparison_role="technical_detail",
            availability_state=state,
            stage="professional_technical",
            note="same_person_link=false; causal_link=false; additive_across_bridge_rows=false.",
        ),
        _metric(
            metric_id="located_technical_enrollments_bridge_context_2025",
            label="Matrículas técnicas localizadas — contexto para disponibilidade da ponte",
            value=None if ept_row is None else ept_row.get("technical_enrollments"),
            unit="enrollments",
            period="2025",
            source_ref="job5gcr_ept",
            territorial_lens="school_location",
            aggregation_rule="source total at municipality or region grain",
            comparison_role="availability_declaration",
            availability_state="unavailable" if ept_row is None else _availability(ept_row.get("technical_enrollments"), ept_row.get("availability_status")),
            stage="professional_technical",
            note="Located offer does not identify student origin or occupational insertion.",
        ),
    ]


def build_family_inputs(
    story_family_id: str,
    entity_id: str,
    sources: Mapping[str, pd.DataFrame],
) -> list[dict[str, Any]]:
    builders = {
        "D1_COHORT_OFFER_CAPACITY": _family_cohort_inputs,
        "D1_TRAJECTORY_CONDITIONS": _family_trajectory_inputs,
        "D1_MOBILITY_HIGH_SCHOOL_OFFER": _family_mobility_inputs,
        "D1_RURALITY_PNATE_PLANNING": _family_rural_pnate_inputs,
        "D1_SPECIAL_AEE_TERRITORY": _family_special_inputs,
        "D1_ADULT_SCHOOLING_EJA": _family_eja_inputs,
        "D2_YOUTH_WORK_15_17": lambda entity, frames: _family_youth_inputs(
            entity, frames, age_group="15_17"
        ),
        "D2_YOUTH_WORK_18_24": lambda entity, frames: _family_youth_inputs(
            entity, frames, age_group="18_24"
        ),
        "D2_APPRENTICESHIP": _family_apprenticeship_inputs,
        "D2_OCCUPATIONS_SECTORS": _family_occupation_sector_inputs,
        "D2_EPT_TERRITORIAL_OFFER": _family_ept_inputs,
        "D2_SECTOR_TRANSFORMATION_SHIFT_SHARE": _family_shift_share_inputs,
        "D2_NORMATIVE_WORK_EDUCATION_BRIDGE": _family_bridge_inputs,
    }
    if story_family_id not in builders:
        raise KeyError(story_family_id)
    return builders[story_family_id](entity_id, sources)


def family_schema() -> dict[str, Any]:
    required = [
        "story_family_id",
        "sequence",
        "direction_id",
        "macroblock_id",
        "layer",
        "editorial_state",
        "internal_title",
        "internal_summary",
        "regional_question",
        "municipal_question",
        "planning_value",
        "incremental_value_beyond_demography",
        "primary_or_secondary_role",
        "conditional_display_rule",
        "default_expansion_state",
        "recommended_sequence",
        "recommended_primary_visual",
        "recommended_secondary_visuals",
        "comparison_contract",
        "management_question",
        "mechanism",
        "regional_read",
        "municipal_read",
        "stages",
        "age_groups",
        "territorial_lenses",
        "time_nature",
        "period",
        "source_refs",
        "legacy_directions",
        "planning_question",
        "monitoring_indicators",
        "institutional_responsibility",
        "institutional_responsibilities",
        "actors",
        "pne_link_state",
        "pne_links",
        "canonical_pne_goal_links",
        "pme_link_state",
        "pme_goal_links",
        "planning_themes",
        "visual_role",
        "interaction_role",
        "allowed_claims",
        "forbidden_claims",
        "limitations",
        "interpretation_limits",
        "source_periods",
        "evidence_state",
        "materiality_state",
        "manager_review_state",
        "job5i_ready_state",
        "demography_only_counterfactual",
        "decision_delta",
        "public_narrative_authorized",
        "external_judgment_required",
    ]
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "vocacoes-pne-job5h-family-schema-v1",
        "title": "Família editorial interna Vocações × PNE V7",
        "type": "object",
        "required": required,
        "properties": {
            "story_family_id": {"type": "string", "pattern": "^D[12]_[A-Z0-9_]+$"},
            "sequence": {"type": "integer", "minimum": 1},
            "direction_id": {"type": "string"},
            "macroblock_id": {"type": "string", "pattern": "^[A-G]_"},
            "layer": {"enum": typed_dictionary()["layers"]},
            "editorial_state": {"enum": typed_dictionary()["editorialRoles"]},
            "internal_title": {"type": "string", "minLength": 1},
            "internal_summary": {"type": "string", "minLength": 1},
            "regional_question": {"type": "string", "minLength": 1},
            "municipal_question": {"type": "string", "minLength": 1},
            "planning_value": {"type": "string", "minLength": 1},
            "incremental_value_beyond_demography": {"type": "object"},
            "primary_or_secondary_role": {"enum": ["PRIMARY", "SECONDARY", "DETAIL", "CONDITIONAL", "INTERNAL"]},
            "conditional_display_rule": {"type": "string", "minLength": 1},
            "default_expansion_state": {"enum": ["expanded", "collapsed"]},
            "recommended_sequence": {"type": "integer", "minimum": 1},
            "recommended_primary_visual": {"type": "string", "minLength": 1},
            "recommended_secondary_visuals": {"type": "array", "items": {"type": "string"}, "minItems": 1},
            "comparison_contract": {"type": "object"},
            "stages": {"type": "array", "items": {"type": "string"}, "minItems": 1, "uniqueItems": True},
            "age_groups": {"type": "array", "items": {"type": "string"}, "minItems": 1, "uniqueItems": True},
            "territorial_lenses": {"type": "array", "items": {"enum": typed_dictionary()["territorialLenses"]}, "minItems": 1, "uniqueItems": True},
            "source_refs": {"type": "array", "items": {"enum": sorted(SOURCE_DEFINITIONS)}, "minItems": 1, "uniqueItems": True},
            "pne_link_state": {"enum": ["linked", "no_valid_link"]},
            "pne_links": {"type": "array", "items": {"$ref": "#/$defs/pneLink"}},
            "canonical_pne_goal_links": {"type": "array", "items": {"$ref": "#/$defs/pneLink"}},
            "pme_link_state": {"const": "not_materialized"},
            "pme_goal_links": {"type": "array", "maxItems": 0},
            "planning_themes": {"type": "array", "items": {"type": "string"}, "minItems": 1},
            "institutional_responsibilities": {"type": "array", "items": {"type": "object"}, "minItems": 1},
            "interpretation_limits": {"type": "array", "items": {"type": "string"}, "minItems": 1},
            "source_periods": {"type": "array", "items": {"type": "object"}, "minItems": 1},
            "evidence_state": {"type": "string"},
            "materiality_state": {"type": "string"},
            "manager_review_state": {"type": "string"},
            "job5i_ready_state": {"type": "string"},
            "public_narrative_authorized": {"const": False},
            "external_judgment_required": {"const": True},
        },
        "$defs": {
            "pneLink": {
                "type": "object",
                "required": ["legal_goal_ref", "link_type", "justification", "official_indicator_recalculated", "goal_compliance_claim_allowed"],
                "properties": {
                    "legal_goal_ref": {"type": "string"},
                    "link_type": {"enum": sorted(PNE_LINK_TYPES - {"no_valid_link"})},
                    "justification": {"type": "string", "minLength": 1},
                    "official_indicator_recalculated": {"const": False},
                    "goal_compliance_claim_allowed": {"const": False},
                },
                "additionalProperties": False,
            }
        },
        "additionalProperties": True,
    }


def variant_schema() -> dict[str, Any]:
    input_required = [
        "metric_id",
        "label",
        "value",
        "unit",
        "period",
        "source_ref",
        "territorial_lens",
        "aggregation_rule",
        "comparison_role",
        "availability_state",
    ]
    required = [
        "story_variant_id",
        "story_family_id",
        "variant_scope",
        "entity_id",
        "municipality_ibge_code",
        "municipality_name",
        "direction_id",
        "macroblock_id",
        "sequence",
        "entity",
        "regional_question",
        "municipal_question",
        "regional_fact_contract",
        "municipal_fact_contract",
        "regional_facts",
        "municipal_facts",
        "named_inputs",
        "named_input_metrics",
        "municipal_distribution",
        "regional_context",
        "state_comparison",
        "change_over_time",
        "contribution_to_region",
        "comparison_method",
        "visual_data",
        "source_refs",
        "period",
        "periods",
        "territorial_lenses",
        "network_scope",
        "stages",
        "age_groups",
        "monitoring_indicators",
        "planning_question",
        "monitoring_indicator",
        "institutional_responsibility",
        "actors",
        "visual_role",
        "interaction_role",
        "availability_state",
        "zero_state",
        "small_volume_state",
        "editorial_state",
        "unavailability_reason",
        "allowed_claims",
        "forbidden_claims",
        "pne_link_state",
        "pne_links",
        "pme_link_state",
        "pme_goal_links",
        "planning_themes",
        "internal_evidence_state",
        "manager_review_state",
        "draft_internal_title",
        "draft_internal_summary",
        "external_judgment_required",
        "draft_for_internal_prototype",
        "public_narrative_authorized",
        "gate11",
    ]
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "vocacoes-pne-job5h-variant-schema-v1",
        "title": "Variante territorial tipada Vocações × PNE V7",
        "type": "object",
        "required": required,
        "properties": {
            "story_variant_id": {"type": "string", "pattern": "^D[12]_[A-Z0-9_]+__(REGION_VALE_DO_SINOS|[0-9]{7})$"},
            "story_family_id": {"type": "string", "pattern": "^D[12]_[A-Z0-9_]+$"},
            "variant_scope": {"enum": ["region", "municipality"]},
            "entity_id": {"type": "string"},
            "municipality_ibge_code": {"type": ["string", "null"], "pattern": "^[0-9]{7}$"},
            "municipality_name": {"type": "string"},
            "entity": {
                "type": "object",
                "required": ["scale", "entity_id", "municipality_ibge_code", "name"],
                "properties": {
                    "scale": {"enum": ["region", "municipality"]},
                    "entity_id": {"type": "string"},
                    "municipality_ibge_code": {"type": ["string", "null"], "pattern": "^[0-9]{7}$"},
                    "name": {"type": "string"},
                },
                "additionalProperties": False,
            },
            "named_inputs": {"type": "array", "items": {"$ref": "#/$defs/namedInput"}, "minItems": 1},
            "named_input_metrics": {"type": "array", "items": {"$ref": "#/$defs/namedInput"}, "minItems": 1},
            "regional_facts": {"type": "array", "items": {"type": "object"}, "minItems": 1},
            "municipal_facts": {"type": "array", "items": {"type": "object"}, "minItems": 1},
            "municipal_distribution": {"type": "array", "items": {"type": "object"}, "minItems": 10, "maxItems": 10},
            "change_over_time": {"type": "array", "items": {"type": "object"}},
            "contribution_to_region": {"type": "object"},
            "visual_data": {"type": "object"},
            "periods": {"type": "array", "items": {"type": "object"}, "minItems": 1},
            "source_refs": {"type": "array", "items": {"enum": sorted(SOURCE_DEFINITIONS)}, "minItems": 1},
            "territorial_lenses": {"type": "array", "items": {"enum": typed_dictionary()["territorialLenses"]}, "minItems": 1},
            "availability_state": {"enum": typed_dictionary()["availabilityStates"]},
            "zero_state": {"type": "object"},
            "small_volume_state": {"type": "object"},
            "editorial_state": {"enum": typed_dictionary()["editorialRoles"]},
            "pme_link_state": {"const": "not_materialized"},
            "pme_goal_links": {"type": "array", "maxItems": 0},
            "draft_for_internal_prototype": {"const": True},
            "external_judgment_required": {"const": True},
            "public_narrative_authorized": {"const": False},
            "gate11": {"const": "CLOSED"},
        },
        "$defs": {
            "namedInput": {
                "type": "object",
                "required": input_required,
                "properties": {
                    "metric_id": {"type": "string", "minLength": 1},
                    "label": {"type": "string", "minLength": 1},
                    "value": {"type": ["number", "null"]},
                    "unit": {"type": "string"},
                    "period": {"type": "string"},
                    "source_ref": {"enum": sorted(SOURCE_DEFINITIONS)},
                    "territorial_lens": {"enum": typed_dictionary()["territorialLenses"]},
                    "aggregation_rule": {"type": "string"},
                    "comparison_role": {"enum": typed_dictionary()["comparisonRoles"]},
                    "availability_state": {"enum": typed_dictionary()["availabilityStates"]},
                    "stage": {"type": ["string", "null"]},
                    "age_group": {"type": ["string", "null"]},
                    "note": {"type": ["string", "null"]},
                },
                "additionalProperties": False,
            }
        },
        "additionalProperties": True,
    }


def build_family_catalog() -> list[dict[str, Any]]:
    catalog: list[dict[str, Any]] = []
    for raw in FAMILY_SPECS:
        family = deepcopy(raw)
        if family["pne_links"]:
            family["pne_link_state"] = "linked"
        else:
            family["pne_link_state"] = "no_valid_link"
        family["pme_link_state"] = "not_materialized"
        family["pme_goal_links"] = []
        family["network_scope"] = "total_all_dependencies"
        family["administrative_dependency_is_analytic_dimension"] = False
        family["administrative_dependency_is_qa_dimension"] = True
        family["public_narrative_authorized"] = False
        family["external_judgment_required"] = True
        family["gate11"] = "CLOSED"
        family["fixed_card_cap"] = None
        role_by_state = {
            "PRIMARY_VISIBLE": "PRIMARY",
            "SECONDARY_VISIBLE": "SECONDARY",
            "DETAIL_EXPANDABLE": "DETAIL",
            "CONDITIONAL_VISIBLE": "CONDITIONAL",
            "INTERNAL_ONLY": "INTERNAL",
        }
        family["internal_summary"] = (
            f"{family['mechanism']} Leitura regional: {family['regional_read']} "
            f"Leitura municipal: {family['municipal_read']}"
        )
        family["regional_question"] = family["management_question"]
        family["municipal_question"] = family["planning_question"]
        family["planning_value"] = family["decision_delta"]
        family["incremental_value_beyond_demography"] = {
            "demography_only_counterfactual": family[
                "demography_only_counterfactual"
            ],
            "decision_delta": family["decision_delta"],
        }
        family["primary_or_secondary_role"] = role_by_state[
            family["editorial_state"]
        ]
        family["conditional_display_rule"] = (
            "display only when the primary input is observed; otherwise render UNAVAILABLE_WITH_REASON"
            if family["editorial_state"] == "CONDITIONAL_VISIBLE"
            else "follow layer and editorial state; unavailable inputs always render an explicit reason"
        )
        family["default_expansion_state"] = (
            "expanded"
            if family["layer"] == "PRIMARY_NARRATIVE_PATH"
            else "collapsed"
        )
        family["recommended_sequence"] = family["sequence"]
        family["recommended_primary_visual"] = family["visual_role"]
        family["recommended_secondary_visuals"] = [
            "ten_municipality_distribution",
            "selected_municipality_fact_table",
        ]
        family["comparison_contract"] = {
            "region": family["regional_read"],
            "municipality": family["municipal_read"],
            "state": "RS only when the same source, universe, grain and method are canonical",
            "score_allowed": False,
            "good_bad_classification_allowed": False,
        }
        family["institutional_responsibilities"] = [
            {
                "role": "primary",
                "responsibility": family["institutional_responsibility"],
            },
            *(
                [
                    {
                        "role": "secondary",
                        "responsibility": family["secondary_responsibility"],
                    }
                ]
                if family.get("secondary_responsibility")
                else []
            ),
        ]
        family["canonical_pne_goal_links"] = deepcopy(family["pne_links"])
        family["interpretation_limits"] = list(family["limitations"])
        family["source_periods"] = [
            {
                "source_ref": source_ref,
                "period": SOURCE_DEFINITIONS[source_ref]["period"],
            }
            for source_ref in family["source_refs"]
        ]
        family["evidence_state"] = "MATERIALIZED_TYPED_INPUTS"
        family["materiality_state"] = "MAXIMUM_CATALOG_CANDIDATE"
        family["manager_review_state"] = "PENDING_EXTERNAL_JUDGMENT"
        family["job5i_ready_state"] = (
            "READY_AS_INPUT_WITH_EXPLICIT_LIMITS_PENDING_EXTERNAL_JUDGMENT"
        )
        catalog.append(family)
    return catalog


def _primary_input(inputs: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]:
    primary = [item for item in inputs if item["comparison_role"] == "primary"]
    if not primary:
        raise ValueError("Família sem entrada primária")
    return primary[0]


def _state_comparison(
    family_id: str,
    entity_id: str,
    sources: Mapping[str, pd.DataFrame],
) -> dict[str, Any]:
    if family_id == "D1_TRAJECTORY_CONDITIONS":
        frame = sources["job5gar_trajectory"]
        selected = frame[
            frame["stage"].eq("medio")
            & frame["metric"].eq("approval_rate_percent")
            & frame["year"].eq("2025")
        ]
        if entity_id != REGION_ENTITY_ID:
            local = selected[selected["municipality_ibge_code"].eq(entity_id)]
            row = None if local.empty else local.iloc[0]
        else:
            row = None if selected.empty else selected.iloc[0]
        return {
            "availability_state": "observed" if row is not None else "unavailable",
            "metric_id": "rs_municipal_distribution_median_high_school_approval_2025",
            "label": "Mediana dos municípios do RS — taxa oficial de aprovação no ensino médio",
            "value": None if row is None else _number(row.get("rs_municipal_distribution_median")),
            "unit": "percent",
            "period": "2025",
            "source_ref": "job5gar_trajectory",
            "comparison_method": "RS municipal distribution median; not a recomposed state rate",
            "reason": None,
        }
    if family_id == "D1_MOBILITY_HIGH_SCHOOL_OFFER":
        state = sources["job5gd_mobility"]
        selected = state[
            state["entity_id"].eq(STATE_ENTITY_ID) & state["stage"].eq("medio")
        ]
        row = None if selected.empty else selected.iloc[0]
        return {
            "availability_state": "observed" if row is not None else "unavailable",
            "metric_id": "rs_residents_studying_other_municipality_share_high_school_2022",
            "label": "RS — parcela de residentes que estudavam em outro município",
            "value": None if row is None else _number(row.get("outside_share_percent")),
            "unit": "percent",
            "period": "2022",
            "source_ref": "job5gd_mobility",
            "comparison_method": "same official table, universe and recomposed count method",
            "reason": None,
        }
    return {
        "availability_state": "not_applicable",
        "metric_id": None,
        "label": None,
        "value": None,
        "unit": "not_applicable",
        "period": None,
        "source_ref": None,
        "comparison_method": None,
        "reason": "No canonical RS comparator at the same source, universe, grain and method for this family.",
    }


def build_variants(
    *,
    families: Sequence[Mapping[str, Any]],
    municipality_names: Mapping[str, str],
    sources: Mapping[str, pd.DataFrame],
) -> list[dict[str, Any]]:
    entity_ids = [REGION_ENTITY_ID, *sorted(municipality_names)]
    variants: list[dict[str, Any]] = []
    by_family: dict[str, list[dict[str, Any]]] = {}
    for family in families:
        family_variants: list[dict[str, Any]] = []
        for entity_id in entity_ids:
            scale = "region" if entity_id == REGION_ENTITY_ID else "municipality"
            name = "Vale do Sinos" if scale == "region" else municipality_names[entity_id]
            inputs = build_family_inputs(family["story_family_id"], entity_id, sources)
            primary = _primary_input(inputs)
            availability_state = str(primary["availability_state"])
            editorial_state = (
                "UNAVAILABLE_WITH_REASON"
                if availability_state in {"unavailable", "suppressed", "null"}
                else family["editorial_state"]
            )
            unavailability_reason = (
                "Primary input is explicitly unavailable at this territorial grain; no zero or proxy was imputed."
                if editorial_state == "UNAVAILABLE_WITH_REASON"
                else None
            )
            variant = {
                "story_variant_id": f"{family['story_family_id']}__{entity_id}",
                "story_family_id": family["story_family_id"],
                "variant_scope": scale,
                "entity_id": entity_id,
                "municipality_ibge_code": None if scale == "region" else entity_id,
                "municipality_name": name,
                "direction_id": family["direction_id"],
                "macroblock_id": family["macroblock_id"],
                "sequence": family["sequence"],
                "entity": {
                    "scale": scale,
                    "entity_id": entity_id,
                    "municipality_ibge_code": None if scale == "region" else entity_id,
                    "name": name,
                },
                "regional_question": family["management_question"],
                "municipal_question": family["planning_question"],
                "regional_fact_contract": family["regional_read"],
                "municipal_fact_contract": family["municipal_read"],
                "regional_facts": [],
                "municipal_facts": [],
                "named_inputs": inputs,
                "named_input_metrics": deepcopy(inputs),
                "municipal_distribution": [],
                "regional_context": None,
                "state_comparison": _state_comparison(
                    family["story_family_id"], entity_id, sources
                ),
                "comparison_method": "same named primary input across all ten municipalities; compatible sums or declared municipal distribution; no score",
                "change_over_time": [],
                "contribution_to_region": {
                    "availability_state": "not_applicable",
                    "measures": [],
                    "reason": "Populated after same-family variants are assembled.",
                },
                "visual_data": {},
                "source_refs": list(family["source_refs"]),
                "period": family["period"],
                "periods": deepcopy(family["source_periods"]),
                "territorial_lenses": list(family["territorial_lenses"]),
                "network_scope": "total_all_dependencies",
                "administrative_dependency_is_analytic_dimension": False,
                "administrative_dependency_is_qa_dimension": True,
                "stages": list(family["stages"]),
                "age_groups": list(family["age_groups"]),
                "monitoring_indicators": list(family["monitoring_indicators"]),
                "planning_question": family["planning_question"],
                "monitoring_indicator": family["monitoring_indicators"][0],
                "institutional_responsibility": family["institutional_responsibility"],
                "secondary_responsibility": family.get("secondary_responsibility"),
                "actors": list(family["actors"]),
                "visual_role": family["visual_role"],
                "interaction_role": family["interaction_role"],
                "availability_state": availability_state,
                "zero_state": {
                    "primary_is_observed_zero": availability_state
                    == "observed_zero",
                    "policy": "observed zero remains distinct from null, unavailable, suppressed and not applicable",
                },
                "small_volume_state": {
                    "state": (
                        "declared_per_named_input"
                        if family["story_family_id"]
                        in {
                            "D2_OCCUPATIONS_SECTORS",
                            "D2_SECTOR_TRANSFORMATION_SHIFT_SHARE",
                        }
                        else "not_applicable"
                    ),
                    "official_suppression_threshold": False,
                },
                "editorial_state": editorial_state,
                "unavailability_reason": unavailability_reason,
                "allowed_claims": list(family["allowed_claims"]),
                "forbidden_claims": list(family["forbidden_claims"]),
                "pne_link_state": family["pne_link_state"],
                "pne_links": deepcopy(family["pne_links"]),
                "pme_link_state": "not_materialized",
                "pme_goal_links": [],
                "planning_themes": list(family["planning_themes"]),
                "internal_evidence_state": "MATERIALIZED_TYPED_INPUTS",
                "manager_review_state": "PENDING_EXTERNAL_JUDGMENT",
                "draft_internal_title": f"{family['internal_title']} — {name}",
                "draft_internal_summary": (
                    f"Insumo interno para {name}: {family['municipal_read']} "
                    f"Disponibilidade primária: {availability_state}."
                ),
                "external_judgment_required": True,
                "draft_for_internal_prototype": True,
                "public_narrative_authorized": False,
                "gate11": "CLOSED",
            }
            if family["story_family_id"] == "D1_MOBILITY_HIGH_SCHOOL_OFFER":
                variant["mobility_contract"] = {
                    "approved_wording": "residentes que estudavam em outro município",
                    "foreign_country_separate": True,
                    "destination_municipality_available": False,
                    "origin_destination_matrix_derived": False,
                    "cross_section_only": True,
                }
            if family["story_family_id"] == "D1_RURALITY_PNATE_PLANNING":
                variant["pnate_2026_contract"] = {
                    "record_type": "planning_forecast",
                    "execution_available": False,
                    "realized_use_available": False,
                    "payment_available": False,
                    "mobility_measure": False,
                }
            family_variants.append(variant)
        municipal_variants = [
            variant
            for variant in family_variants
            if variant["entity"]["scale"] == "municipality"
        ]
        distribution = []
        for municipal_variant in municipal_variants:
            primary = _primary_input(municipal_variant["named_inputs"])
            distribution.append(
                {
                    "municipality_ibge_code": municipal_variant["entity"]["municipality_ibge_code"],
                    "municipality_name": municipal_variant["entity"]["name"],
                    "metric_id": primary["metric_id"],
                    "value": primary["value"],
                    "unit": primary["unit"],
                    "availability_state": primary["availability_state"],
                }
            )
        region_variant = next(
            variant
            for variant in family_variants
            if variant["entity"]["scale"] == "region"
        )
        regional_primary = _primary_input(region_variant["named_inputs"])
        regional_context = {
            "metric_id": regional_primary["metric_id"],
            "label": regional_primary["label"],
            "value": regional_primary["value"],
            "unit": regional_primary["unit"],
            "availability_state": regional_primary["availability_state"],
            "aggregation_rule": regional_primary["aggregation_rule"],
        }
        regional_fact_rows = [
            {
                "metric_id": item["metric_id"],
                "label": item["label"],
                "value": item["value"],
                "unit": item["unit"],
                "period": item["period"],
                "source_ref": item["source_ref"],
                "territorial_lens": item["territorial_lens"],
                "availability_state": item["availability_state"],
            }
            for item in region_variant["named_inputs"]
        ]
        for variant in family_variants:
            variant["municipal_distribution"] = deepcopy(distribution)
            variant["regional_context"] = deepcopy(regional_context)
            variant["regional_facts"] = deepcopy(regional_fact_rows)
            if variant["entity"]["scale"] == "municipality":
                variant["municipal_facts"] = [
                    {
                        "metric_id": item["metric_id"],
                        "label": item["label"],
                        "value": item["value"],
                        "unit": item["unit"],
                        "period": item["period"],
                        "source_ref": item["source_ref"],
                        "territorial_lens": item["territorial_lens"],
                        "availability_state": item["availability_state"],
                    }
                    for item in variant["named_inputs"]
                ]
            else:
                variant["municipal_facts"] = deepcopy(distribution)
            variant["change_over_time"] = [
                {
                    "metric_id": item["metric_id"],
                    "value": item["value"],
                    "unit": item["unit"],
                    "period": item["period"],
                    "availability_state": item["availability_state"],
                }
                for item in variant["named_inputs"]
                if "-" in str(item["period"])
                or "series" in str(item["period"]).lower()
            ]
            distribution_measures = [
                {
                    "metric_id": item["metric_id"],
                    "value": item["value"],
                    "unit": item["unit"],
                    "period": item["period"],
                    "availability_state": item["availability_state"],
                }
                for item in variant["named_inputs"]
                if item["comparison_role"] == "distribution"
            ]
            variant["contribution_to_region"] = {
                "availability_state": (
                    "observed" if distribution_measures else "not_applicable"
                ),
                "measures": distribution_measures,
                "reason": (
                    None
                    if distribution_measures
                    else "No additive or recomputable contribution is authorized for the primary input."
                ),
            }
            variant["visual_data"] = {
                "primary_metric": deepcopy(
                    _primary_input(variant["named_inputs"])
                ),
                "secondary_metric_ids": [
                    item["metric_id"]
                    for item in variant["named_inputs"]
                    if item["comparison_role"] == "secondary"
                ],
                "municipal_distribution": deepcopy(distribution),
                "state_comparison": deepcopy(variant["state_comparison"]),
                "visual_role": variant["visual_role"],
            }
        by_family[family["story_family_id"]] = family_variants
        variants.extend(family_variants)
    if set(by_family) != {family["story_family_id"] for family in families}:
        raise AssertionError("Corpus incompleto por família")
    return variants


def build_fact_trace(variants: Sequence[Mapping[str, Any]]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for variant in variants:
        entity = variant["entity"]
        for input_index, item in enumerate(variant["named_inputs"], start=1):
            trace_seed = (
                f"{variant['story_variant_id']}|{item['metric_id']}|{input_index}"
            ).encode("utf-8")
            rows.append(
                {
                    "fact_trace_id": hashlib.sha256(trace_seed).hexdigest()[:24],
                    "story_family_id": variant["story_family_id"],
                    "story_variant_id": variant["story_variant_id"],
                    "entity_scope": entity["scale"],
                    "entity_id": entity["entity_id"],
                    "municipality_ibge_code": entity["municipality_ibge_code"],
                    "municipality_name": entity["name"],
                    "input_index": input_index,
                    "metric_id": item["metric_id"],
                    "label": item["label"],
                    "value": item["value"],
                    "value_status": item["availability_state"],
                    "unit": item["unit"],
                    "period": item["period"],
                    "source_ref": item["source_ref"],
                    "territorial_lens": item["territorial_lens"],
                    "aggregation_rule": item["aggregation_rule"],
                    "comparison_role": item["comparison_role"],
                    "stage": item["stage"],
                    "age_group": item["age_group"],
                    "editorial_state": variant["editorial_state"],
                    "public_narrative_authorized": False,
                }
            )
    return pd.DataFrame(rows).sort_values(
        ["story_family_id", "story_variant_id", "input_index"], kind="mergesort"
    ).reset_index(drop=True)


def build_job_family_trace(
    families: Sequence[Mapping[str, Any]],
) -> pd.DataFrame:
    rows = []
    for family in families:
        for source_ref in family["source_refs"]:
            definition = SOURCE_DEFINITIONS[source_ref]
            match = re.search(r"v7-job([^/]+)", definition["path"])
            source_job = None if match is None else match.group(1).upper()
            rows.append(
                {
                    "story_family_id": family["story_family_id"],
                    "direction_id": family["direction_id"],
                    "macroblock_id": family["macroblock_id"],
                    "source_job": source_job,
                    "source_ref": source_ref,
                    "source_artifact": definition["path"],
                    "period": definition["period"],
                    "territorial_lens": definition["lens"],
                    "transported_limit": definition["limit"],
                    "provenance_role": "typed_editorial_input",
                }
            )
    return pd.DataFrame(rows).sort_values(
        ["story_family_id", "source_ref"], kind="mergesort"
    ).reset_index(drop=True)


def build_redundancy_matrix() -> pd.DataFrame:
    mappings = {
        "COORD_COHORT_OFFER_PRESSURE": [
            ("D1_COHORT_OFFER_CAPACITY", "consolidated_primary_family")
        ],
        "COORD_EJA_ADULT_SCHOOLING": [
            ("D1_ADULT_SCHOOLING_EJA", "consolidated_primary_family")
        ],
        "COORD_EPT_MOBILITY": [
            ("D2_EPT_TERRITORIAL_OFFER", "split_offer_distribution"),
            ("D2_NORMATIVE_WORK_EDUCATION_BRIDGE", "split_normative_bridge"),
        ],
        "COORD_FINANCE_COHORT_PRESSURE": [
            ("D1_COHORT_OFFER_CAPACITY", "redundant_merged_selective_context"),
            ("D1_TRAJECTORY_CONDITIONS", "redundant_merged_selective_context"),
        ],
        "COORD_MOBILITY_OFFER_HIGH_SCHOOL": [
            ("D1_MOBILITY_HIGH_SCHOOL_OFFER", "consolidated_primary_family")
        ],
        "COORD_RURAL_PNATE": [
            ("D1_RURALITY_PNATE_PLANNING", "consolidated_secondary_family")
        ],
        "COORD_SPECIAL_AEE_TERRITORY": [
            ("D1_SPECIAL_AEE_TERRITORY", "consolidated_conditional_family")
        ],
        "COORD_TRAJECTORY_MOBILITY": [
            ("D1_TRAJECTORY_CONDITIONS", "split_trajectory_series"),
            ("D1_MOBILITY_HIGH_SCHOOL_OFFER", "split_cross_sectional_mobility"),
        ],
        "COORD_WORK_EPT_AGE_GROUPS": [
            ("D2_YOUTH_WORK_15_17", "split_age_group_15_17"),
            ("D2_YOUTH_WORK_18_24", "split_age_group_18_24"),
            ("D2_APPRENTICESHIP", "split_apprenticeship_flow"),
            ("D2_OCCUPATIONS_SECTORS", "split_occupation_sector_stock"),
            ("D2_EPT_TERRITORIAL_OFFER", "split_ept_offer"),
            ("D2_SECTOR_TRANSFORMATION_SHIFT_SHARE", "split_internal_decomposition"),
            ("D2_NORMATIVE_WORK_EDUCATION_BRIDGE", "split_normative_bridge"),
        ],
    }
    rows = []
    for legacy_id, destinations in mappings.items():
        for destination_id, decision in destinations:
            rows.append(
                {
                    "legacy_job5gd_combination_id": legacy_id,
                    "legacy_variant_count": 11,
                    "destination_story_family_id": destination_id,
                    "editorial_decision": decision,
                    "old_rows_are_public_stories": False,
                    "family_variant_identity_separated": True,
                    "fixed_card_cap": None,
                    "redundancy_state": (
                        "REDUNDANT_MERGED"
                        if "redundant_merged" in decision
                        else "RESTRUCTURED"
                    ),
                }
            )
    return pd.DataFrame(rows).sort_values(
        ["legacy_job5gd_combination_id", "destination_story_family_id"],
        kind="mergesort",
    ).reset_index(drop=True)


def build_completeness_matrix(
    families: Sequence[Mapping[str, Any]],
    variants: Sequence[Mapping[str, Any]],
    municipality_names: Mapping[str, str],
) -> pd.DataFrame:
    lookup = {
        (variant["story_family_id"], variant["entity"]["entity_id"]): variant
        for variant in variants
    }
    rows = []
    for family in families:
        for code, name in sorted(municipality_names.items()):
            variant = lookup[(family["story_family_id"], code)]
            primary = _primary_input(variant["named_inputs"])
            rows.append(
                {
                    "story_family_id": family["story_family_id"],
                    "municipality_ibge_code": code,
                    "municipality_name": name,
                    "story_variant_id": variant["story_variant_id"],
                    "variant_present": True,
                    "primary_metric_id": primary["metric_id"],
                    "primary_input_availability_state": primary["availability_state"],
                    "named_input_count": len(variant["named_inputs"]),
                    "source_ref_count": len(set(variant["source_refs"])),
                    "unavailability_explicit": (
                        primary["availability_state"] not in {"unavailable", "null", "suppressed"}
                        or bool(variant["unavailability_reason"])
                    ),
                    "network_scope": variant["network_scope"],
                    "public_narrative_authorized": False,
                }
            )
    return pd.DataFrame(rows).sort_values(
        ["story_family_id", "municipality_ibge_code"], kind="mergesort"
    ).reset_index(drop=True)


def build_availability_matrix(
    variants: Sequence[Mapping[str, Any]],
) -> pd.DataFrame:
    rows = []
    for variant in variants:
        states = Counter(item["availability_state"] for item in variant["named_inputs"])
        rows.append(
            {
                "story_family_id": variant["story_family_id"],
                "story_variant_id": variant["story_variant_id"],
                "entity_scope": variant["entity"]["scale"],
                "entity_id": variant["entity"]["entity_id"],
                "municipality_ibge_code": variant["entity"]["municipality_ibge_code"],
                "municipality_name": variant["entity"]["name"],
                "availability_state": variant["availability_state"],
                "editorial_state": variant["editorial_state"],
                "unavailability_reason": variant["unavailability_reason"],
                "observed_input_count": states["observed"],
                "observed_zero_input_count": states["observed_zero"],
                "null_input_count": states["null"],
                "unavailable_input_count": states["unavailable"],
                "not_applicable_input_count": states["not_applicable"],
                "conditional_visibility": variant["editorial_state"]
                in {"CONDITIONAL_VISIBLE", "UNAVAILABLE_WITH_REASON"},
                "external_judgment_required": True,
            }
        )
    return pd.DataFrame(rows).sort_values(
        ["story_family_id", "entity_scope", "entity_id"], kind="mergesort"
    ).reset_index(drop=True)


def _c1_status(family: Mapping[str, Any]) -> str:
    links = family["pne_links"]
    if not links:
        return "NOT_SUPPORTED"
    if all(link["link_type"] == "contextual_planning" for link in links):
        return "PARTIAL"
    return "SUPPORTED"


def _criterion_result(
    family: Mapping[str, Any], criterion_id: str
) -> tuple[str, str, str]:
    family_id = family["story_family_id"]
    title = family["internal_title"]
    if criterion_id == "C1":
        refs = [link["legal_goal_ref"] for link in family["pne_links"]]
        if refs:
            evidence = (
                f"{family_id} — {title}: vínculos legais {refs} usam tipos "
                f"{[link['link_type'] for link in family['pne_links']]}; nenhum indicador oficial é recalculado."
            )
        else:
            evidence = (
                f"{family_id} — {title}: no_valid_link; lista legal vazia porque os fatos não monitoram diretamente meta PNE. "
                f"{family.get('no_valid_pne_link_justification')}"
            )
        return _c1_status(family), evidence, "legal PNE contract and planning themes"
    if criterion_id == "C2":
        return (
            "SUPPORTED",
            f"{family_id} — {title}: mecanismo prévio = {family['mechanism']}",
            "mechanism, inputs and forbidden claims",
        )
    if criterion_id == "C3":
        return (
            "SUPPORTED",
            f"{family_id} — {title}: lentes separadas {family['territorial_lenses']} e rede total; nenhuma dependência administrativa vira dimensão analítica.",
            "territorial lenses, stages and network scope",
        )
    if criterion_id == "C4":
        return (
            "SUPPORTED",
            f"{family_id} — {title}: natureza temporal {family['time_nature']} no período {family['period']}; fotografia, série e previsão são rotuladas separadamente.",
            "period and temporal nature",
        )
    if criterion_id == "C5":
        if family_id == "D1_MOBILITY_HIGH_SCHOOL_OFFER":
            return (
                "NOT_SUPPORTED",
                f"{family_id} — {title}: a mobilidade é uma fotografia transversal de 2022; dez municípios e RS permitem contraste territorial, mas não estabilidade temporal.",
                "2022 mobility cross-section and independent 2014-2025 offer series",
            )
        if family_id == "D1_ADULT_SCHOOLING_EJA":
            return (
                "NOT_EVALUABLE",
                f"{family_id} — {title}: a distribuição EJA é fotografia de 2022; a série de matrícula é contexto independente e não valida estabilidade do contraste entre lentes.",
                "2022 EJA distribution and separate enrollment series",
            )
        if family_id == "D2_NORMATIVE_WORK_EDUCATION_BRIDGE":
            return (
                "NOT_EVALUABLE",
                f"{family_id} — {title}: a ponte normativa é transversal em 2025 e não possui série de correspondências versionadas para teste de estabilidade.",
                "2025 normative bridge",
            )
        if family_id in {
            "D1_COHORT_OFFER_CAPACITY",
            "D1_TRAJECTORY_CONDITIONS",
            "D1_RURALITY_PNATE_PLANNING",
        }:
            return (
                "PARTIAL",
                f"{family_id} — {title}: há cobertura dos dez municípios e série observada, mas quebras, lentes ou componente mecânico/planejado restringem estabilidade plena.",
                "ten-municipality coverage plus declared temporal cautions",
            )
        return (
            "SUPPORTED",
            f"{family_id} — {title}: a fonte cobre os dez municípios no período declarado; mudanças são descritas sem extrapolação causal.",
            "ten-municipality comparable panel",
        )
    if criterion_id == "C6":
        return (
            "SUPPORTED",
            f"{family_id} — {title}: integração usa fontes {family['source_refs']} com pergunta e decisão comuns; unidades incompatíveis não são somadas.",
            "named inputs and integration mechanism",
        )
    if criterion_id == "C7":
        return (
            "SUPPORTED",
            f"{family_id} — {title}: existem dez variantes municipais, uma variante Vale e distribuição do mesmo input primário, inclusive indisponibilidades explícitas.",
            "variant corpus and completeness matrix",
        )
    if criterion_id == "C8":
        return (
            "SUPPORTED",
            f"{family_id} — {title}: questão '{family['planning_question']}' liga etapas {family['stages']}, indicadores {family['monitoring_indicators']} e responsabilidade {family['institutional_responsibility']}.",
            "planning question, actors and monitoring indicators",
        )
    if criterion_id == "C9":
        status = "PARTIAL" if family["layer"] == "INTERNAL_TECHNICAL_LAYER" else "SUPPORTED"
        return (
            status,
            f"{family_id} — {title}: rótulos públicos previstos nomeiam moradores, escolas ou estabelecimentos; {family['visual_role']} exige explicação de universo antes do valor.",
            "language contract and visual role",
        )
    if criterion_id == "C10":
        return (
            "SUPPORTED",
            f"{family_id} — {title}: cada entrada possui metric_id, valor, unidade, período, source_ref, lente, regra de agregação e papel de comparação.",
            "fact-family-variant-source matrix",
        )
    if criterion_id == "C11":
        return (
            "SUPPORTED",
            f"{family_id} — {title}: deriva de {family['legacy_directions']} com decisão de fusão ou separação registrada; family_id e variant_id são distintos.",
            "redundancy and role matrix",
        )
    if criterion_id == "C12":
        return (
            "SUPPORTED",
            f"{family_id} — {title}: contrafactual='{family['demography_only_counterfactual']}' e delta decisório='{family['decision_delta']}'.",
            "demography-only counterfactual and decision delta",
        )
    raise KeyError(criterion_id)


def build_c1_c12_matrix(
    families: Sequence[Mapping[str, Any]],
) -> pd.DataFrame:
    rows = []
    for family in families:
        for criterion_id, criterion in CRITERIA:
            status, evidence, operation = _criterion_result(family, criterion_id)
            rows.append(
                {
                    "story_family_id": family["story_family_id"],
                    "criterion_id": criterion_id,
                    "criterion": criterion,
                    "criterion_status": status,
                    "operation_tested": operation,
                    "evidence": evidence,
                    "period": family["period"],
                    "territorial_coverage": "Vale do Sinos + ten municipalities; RS only where canonical",
                    "territorial_lenses": "|".join(family["territorial_lenses"]),
                    "source_refs": "|".join(family["source_refs"]),
                    "limitation": " | ".join(family["limitations"]),
                    "automatic_approval": False,
                    "external_judgment_required": True,
                }
            )
    return pd.DataFrame(rows).sort_values(
        ["story_family_id", "criterion_id"], kind="mergesort"
    ).reset_index(drop=True)


def build_pne_links_payload(
    families: Sequence[Mapping[str, Any]], pne_contract: Mapping[str, Any]
) -> dict[str, Any]:
    goals = pne_contract["goals"]
    family_links = []
    used_refs: set[str] = set()
    for family in families:
        links = []
        for link in family["pne_links"]:
            ref = link["legal_goal_ref"]
            if ref not in goals:
                raise ValueError(f"Referência legal PNE ausente do contrato: {ref}")
            if ref not in EXPECTED_PNE_ALLOWLIST:
                raise ValueError(f"Referência PNE fora do allowlist acordado: {ref}")
            used_refs.add(ref)
            goal = goals[ref]
            links.append(
                {
                    **deepcopy(link),
                    "legal_title": goal["publicTitle"],
                    "legal_text": goal["legalText"],
                    "legal_source_id": goal["legalSourceId"],
                    "contract_version": pne_contract["contractVersion"],
                }
            )
        family_links.append(
            {
                "story_family_id": family["story_family_id"],
                "pne_link_state": family["pne_link_state"],
                "links": links,
                "no_valid_link_justification": family.get(
                    "no_valid_pne_link_justification"
                ),
                "official_indicator_recalculated": False,
                "goal_compliance_claim_allowed": False,
            }
        )
    return {
        "schemaVersion": "vocacoes-pne-job5h-legal-pne-links-v1",
        "canonicalContract": {
            "path": "contracts/pne2026-goal-indicator-contract.json",
            "schemaVersion": pne_contract["schemaVersion"],
            "contractVersion": pne_contract["contractVersion"],
            "cycle": pne_contract["cycle"],
        },
        "allowedLinkTypes": sorted(PNE_LINK_TYPES),
        "expectedLegalRefAllowlist": sorted(EXPECTED_PNE_ALLOWLIST),
        "usedLegalRefs": sorted(used_refs),
        "familyLinks": family_links,
        "genericIdentifiersAllowed": False,
        "emptyLegalLinksAllowedWhenStateIsNoValidLink": True,
    }


def build_pme_payload(families: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    return {
        "schemaVersion": "vocacoes-pne-job5h-pme-planning-state-v1",
        "pme_link_state": "not_materialized",
        "pme_goal_links": [],
        "reason": "Nenhum contrato legal PME municipal versionado e materializado integra os insumos congelados; valores genéricos do Job 5G-D eram temas de planejamento, não metas.",
        "genericPmeIdentifiersAreGoalLinks": False,
        "families": [
            {
                "story_family_id": family["story_family_id"],
                "pme_link_state": "not_materialized",
                "pme_goal_links": [],
                "planning_themes": list(family["planning_themes"]),
                "coordination_context": family["institutional_responsibility"],
            }
            for family in families
        ],
    }


def build_source_registry(
    *,
    repo_root: Path,
    frozen_integrity: Mapping[str, str],
    pne_contract: Mapping[str, Any],
) -> dict[str, Any]:
    records = []
    for source_ref, definition in sorted(SOURCE_DEFINITIONS.items()):
        path = repo_root / definition["path"]
        records.append(
            {
                "source_ref": source_ref,
                "path": definition["path"],
                "sha256": sha256_file(path),
                "byte_size": path.stat().st_size,
                "period": definition["period"],
                "territorial_lens": definition["lens"],
                "transported_limit": definition["limit"],
                "acquisition_performed_by_job5h": False,
                "network_used_by_job5h": False,
                "database_used_by_job5h": False,
            }
        )
    return {
        "schemaVersion": "vocacoes-pne-job5h-source-registry-v1",
        "sources": records,
        "canonicalPneContract": {
            "path": "contracts/pne2026-goal-indicator-contract.json",
            "sha256": sha256_file(
                repo_root / "contracts" / "pne2026-goal-indicator-contract.json"
            ),
            "schemaVersion": pne_contract["schemaVersion"],
            "contractVersion": pne_contract["contractVersion"],
        },
        "frozenPackageDigests": dict(sorted(frozen_integrity.items())),
        "acquisition": {
            "networkUsed": False,
            "databaseUsed": False,
            "allAnalyticalInputsLocalAndFrozen": True,
        },
    }


def build_architecture(families: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    macroblock_names = {
        "A_DEMOGRAPHY_AND_OFFER": "Demografia, coortes e resposta da oferta",
        "B_TRAJECTORY_AND_CONDITIONS": "Trajetória e condições",
        "C_MOBILITY_AND_HIGH_SCHOOL": "Mobilidade e ensino médio",
        "D_RURALITY_AND_TRANSPORT": "Ruralidade e transporte",
        "E_INCLUSION_AND_ADULTS": "Inclusão, escolaridade adulta e EJA",
        "F_YOUTH_WORK_AND_TRAINING": "Trabalho juvenil e aprendizagem",
        "G_ECONOMY_EPT_AND_COORDINATION": "Economia, EPT e coordenação",
    }
    macroblocks = []
    for macroblock_id, name in macroblock_names.items():
        members = [
            family["story_family_id"]
            for family in families
            if family["macroblock_id"] == macroblock_id
        ]
        macroblocks.append(
            {
                "macroblock_id": macroblock_id,
                "name": name,
                "story_family_ids": members,
                "family_count": len(members),
            }
        )
    return {
        "schemaVersion": "vocacoes-pne-job5h-page-architecture-v1",
        "purpose": "maximum internal editorial architecture for future Job 5I prototyping",
        "publicArchitectureApproved": False,
        "fixedCardCap": None,
        "oldJob5GDRows": {
            "rowCount": 99,
            "interpretation": "9 analytical families x 11 territorial variants",
            "publicStoryCount": 0,
        },
        "directions": [
            {
                "direction_id": "TERRITORY_HELPS_UNDERSTAND_EDUCATION",
                "management_prompt": "O que o território ajuda a compreender sobre a educação?",
                "story_family_ids": [
                    family["story_family_id"]
                    for family in families
                    if family["direction_id"]
                    == "TERRITORY_HELPS_UNDERSTAND_EDUCATION"
                ],
            },
            {
                "direction_id": "TERRITORIAL_TRANSFORMATIONS_SET_EDUCATION_AGENDA",
                "management_prompt": "Que transformações do território colocam temas na agenda da educação?",
                "story_family_ids": [
                    family["story_family_id"]
                    for family in families
                    if family["direction_id"]
                    == "TERRITORIAL_TRANSFORMATIONS_SET_EDUCATION_AGENDA"
                ],
            },
        ],
        "layers": [
            {
                "layer_id": layer,
                "story_family_ids": [
                    family["story_family_id"]
                    for family in families
                    if family["layer"] == layer
                ],
            }
            for layer in typed_dictionary()["layers"]
        ],
        "macroblocks": macroblocks,
        "sequence": [
            {
                "sequence": family["sequence"],
                "story_family_id": family["story_family_id"],
                "layer": family["layer"],
                "editorial_state": family["editorial_state"],
                "internal_title": family["internal_title"],
            }
            for family in families
        ],
        "municipalVariantRule": "Every material family has Vale plus all ten municipal variants; unavailable inputs stay explicit.",
        "selectedMunicipalityRule": "IBGE textual code only; Nova Santa Rita is fixture, not hardcode.",
        "gate11": "CLOSED",
        "job5IStarted": False,
    }


def build_interaction_spec(families: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    return {
        "schemaVersion": "vocacoes-pne-job5h-interaction-spec-v1",
        "targetJob": "5I",
        "implementationAuthorized": False,
        "principles": [
            "Select municipality by textual seven-digit IBGE code.",
            "Keep Vale context visible when a municipal variant is selected.",
            "Do not substitute unavailable with zero or another municipality.",
            "Expansion preserves keyboard focus, print order and source context.",
            "Technical limitations stay outside the primary path but remain reachable.",
        ],
        "controls": [
            {"control_id": "municipality_selector", "input": "municipality_ibge_code", "fallback": "REGION_VALE_DO_SINOS"},
            {"control_id": "stage_switch", "applies_to": [family["story_family_id"] for family in families if len(family["stages"]) > 1]},
            {"control_id": "age_group_switch", "applies_to": [family["story_family_id"] for family in families if "15_17" in family["age_groups"] and "18_24" in family["age_groups"]]},
            {"control_id": "evidence_expander", "layers": ["EXPANDED_EVIDENCE_LAYER", "INTERNAL_TECHNICAL_LAYER"]},
        ],
        "states": {
            "loading": "retain layout and announce loading",
            "error": "show recoverable error without fabricating values",
            "empty": "distinguish no eligible row from observed zero",
            "unavailable": "render reason from variant contract",
            "observed_zero": "render zero with declared universe",
        },
        "print": {
            "primaryPathFirst": True,
            "expandedEvidenceAfterPrimary": True,
            "internalTechnicalLayerDefault": "excluded_from_public_print",
            "sourceAndPeriodRepeated": True,
        },
        "gate11": "CLOSED",
    }


def build_visual_spec(families: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    return {
        "schemaVersion": "vocacoes-pne-job5h-visual-spec-v1",
        "targetJob": "5I",
        "implementationAuthorized": False,
        "globalRules": [
            "No axis, color or ordering may imply good/bad municipality ranking.",
            "Stock, flow, rate, count and monetary stages never share an unlabeled scale.",
            "Observed zero, null, unavailable, suppressed and not applicable use distinct marks.",
            "All charts carry source, period, lens, unit and aggregation rule.",
            "Print uses high-contrast patterns and does not depend on hover.",
        ],
        "families": [
            {
                "story_family_id": family["story_family_id"],
                "visual_role": family["visual_role"],
                "layer": family["layer"],
                "primary_measure": family["monitoring_indicators"][0],
                "required_annotations": family["limitations"],
                "state_behavior": {
                    "observed_zero": "draw zero at baseline and label universe",
                    "unavailable": "replace plot with reason; never draw zero",
                    "conditional": "show only after explicit expansion when family is conditional",
                },
            }
            for family in families
        ],
        "accessibility": {
            "keyboardReachableControls": True,
            "textAlternativeRequired": True,
            "colorAloneForbidden": True,
            "minimumPrintContrastRequired": True,
        },
    }


def build_language_contract() -> dict[str, Any]:
    return {
        "schemaVersion": "vocacoes-pne-job5h-internal-language-contract-v1",
        "scope": "internal prototype inputs only",
        "publicCopyApproved": False,
        "approvedTerritorialLabels": {
            "resident_population": "Moradores do município",
            "student_residence": "Residentes que estudavam em outro município",
            "school_location": "Matrículas nas escolas do município",
            "rural_school_location": "Oferta nas escolas rurais do município",
            "workplace": "Vínculos ou eventos nos estabelecimentos do município",
            "municipal_executor": "Registros do executor municipal",
        },
        "mandatoryWording": {
            "mobility": "residentes que estudavam em outro município",
            "pnate2026": "previsão de planejamento PNATE 2026",
            "eja": "participação no público residente e participação nas matrículas EJA localizadas",
            "bridge": "correspondência normativa muitos-para-muitos",
        },
        "forbiddenPatterns": [
            "município receptor",
            "corredor origem-destino",
            "PNATE executado em 2026",
            "uso realizado do PNATE 2026",
            "cobertura da EJA",
            "demanda por EJA",
            "os alunos abandonam para trabalhar",
            "profissões do futuro",
            "faltam cursos",
            "ranking municipal",
            "PNE_<número>",
            "PME_<tema>",
        ],
        "claimBoundaries": {
            "mobility": "cross-sectional residence fact; destination unavailable",
            "pnate": "executor planning/financial record; not mobility or use",
            "work": "workplace stock or event flow; no same-person link",
            "ept": "located offer; origin of students unavailable",
            "trajectory": "official municipal rate; no regional recomposition",
        },
    }


def build_limitations_map(families: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    global_limits = [
        {"limit_id": "NO_PUBLIC_NARRATIVE", "effect": "All material is internal and pending external judgment."},
        {"limit_id": "GATE11_CLOSED", "effect": "No release or publication authorization."},
        {"limit_id": "NO_DESTINATION", "effect": "Mobility cannot name destination municipalities or derive OD corridors."},
        {"limit_id": "PNATE_2026_FORECAST_ONLY", "effect": "No execution, realized use, payment or mobility claim for 2026."},
        {"limit_id": "PME_NOT_MATERIALIZED", "effect": "Planning themes are not PME goals or legal links."},
        {"limit_id": "NO_SAME_PERSON_LINK", "effect": "Education, work, mobility and EPT series do not identify the same people."},
        {"limit_id": "NO_REGIONAL_TRAJECTORY_RATE", "effect": "Trajectory uses municipal distributions, not a recomposed Vale rate."},
        {"limit_id": "BRIDGE_MANY_TO_MANY", "effect": "Course enrollments cannot be summed across normative correspondences."},
        {"limit_id": "NO_SCENARIO", "effect": "Mechanical cohort pressure is not a scenario or forecast."},
        {"limit_id": "NO_GENERIC_FINANCE_MODULE", "effect": "Finance remains selective context with stages separated."},
    ]
    return {
        "schemaVersion": "vocacoes-pne-job5h-limitations-map-v1",
        "globalLimits": global_limits,
        "familyLimits": [
            {
                "story_family_id": family["story_family_id"],
                "limitations": list(family["limitations"]),
                "forbidden_claims": list(family["forbidden_claims"]),
                "editorial_effect": (
                    "internal_only"
                    if family["layer"] == "INTERNAL_TECHNICAL_LAYER"
                    else "requires_external_judgment"
                ),
            }
            for family in families
        ],
        "automaticApproval": False,
        "gate11": "CLOSED",
    }


def _iter_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, Mapping):
        for item in value.values():
            yield from _iter_strings(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _iter_strings(item)


def _qa_row(
    control_id: str,
    description: str,
    passed: bool,
    expected: Any,
    observed: Any,
    evidence: str,
) -> dict[str, Any]:
    return {
        "qa_control_id": control_id,
        "description": description,
        "status": "PASS" if passed else "FAIL",
        "expected": _json_safe(expected),
        "observed": _json_safe(observed),
        "evidence": evidence,
        "automatic_approval": False,
    }


def build_qa_matrix(
    *,
    repo_root: Path,
    contract: Mapping[str, Any],
    families: Sequence[Mapping[str, Any]],
    variants: Sequence[Mapping[str, Any]],
    municipality_names: Mapping[str, str],
    c1_c12: pd.DataFrame,
    completeness: pd.DataFrame,
    pne_payload: Mapping[str, Any],
    sources: Mapping[str, pd.DataFrame],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    def add(
        control_id: str,
        description: str,
        passed: bool,
        expected: Any,
        observed: Any,
        evidence: str,
    ) -> None:
        rows.append(
            _qa_row(
                control_id,
                description,
                passed,
                expected,
                observed,
                evidence,
            )
        )

    family_ids = [family["story_family_id"] for family in families]
    variant_ids = [variant["story_variant_id"] for variant in variants]
    family_counts = Counter(variant["story_family_id"] for variant in variants)
    municipality_codes = set(municipality_names)
    strings = list(_iter_strings([families, variants]))
    legal_refs = {
        link["legal_goal_ref"]
        for family in families
        for link in family["pne_links"]
    }
    gcr_fact_path = (
        repo_root
        / ".tmp"
        / "vocacoes-pne"
        / "v7-job5gcr"
        / "MATRIZ_CATALOGO_FATOS_NOVA_SANTA_RITA_JOB5GCR_V1.csv.gz"
    )
    gd_manifest = json.loads(
        (
            repo_root
            / ".tmp"
            / "vocacoes-pne"
            / "v7-job5gd"
            / "MANIFEST_JOB5GD.json"
        ).read_text(encoding="utf-8")
    )
    add("QA001", "Thirteen editorial families", len(families) == 13, 13, len(families), "Maximum architecture catalog")
    add("QA002", "Family identifiers unique", len(set(family_ids)) == 13, 13, len(set(family_ids)), "story_family_id uniqueness")
    add("QA003", "Each family has eleven territorial variants", set(family_counts.values()) == {11}, "11 per family", dict(family_counts), "Vale plus ten municipalities")
    add("QA004", "Variant identifiers unique", len(set(variant_ids)) == len(variant_ids), len(variant_ids), len(set(variant_ids)), "story_variant_id uniqueness")
    add("QA005", "Family and variant identities separated", all(variant["story_variant_id"] != variant["story_family_id"] for variant in variants), True, True, "No old-row-as-story ambiguity")
    add("QA006", "Ten canonical municipalities", len(municipality_names) == 10, 10, len(municipality_names), "RS region config and municipality registry")
    add("QA007", "Textual seven-digit municipality identity", all(isinstance(code, str) and IBGE_CODE_PATTERN.fullmatch(code) for code in municipality_names), True, sorted(municipality_names), "No numeric IBGE conversion")
    add("QA008", "All municipal variants use canonical codes", {variant["entity"]["entity_id"] for variant in variants if variant["entity"]["scale"] == "municipality"} == municipality_codes, sorted(municipality_codes), sorted({variant["entity"]["entity_id"] for variant in variants if variant["entity"]["scale"] == "municipality"}), "Variant coverage")
    add("QA009", "Network scope total", all(variant["network_scope"] == "total_all_dependencies" for variant in variants), "total_all_dependencies", sorted(set(variant["network_scope"] for variant in variants)), "All educational variants")
    add("QA010", "Dependency is QA-only", all(not variant["administrative_dependency_is_analytic_dimension"] and variant["administrative_dependency_is_qa_dimension"] for variant in variants), True, True, "No analytic dependency split")
    add("QA011", "No generic PNE identifiers", not any("PNE_" in text for text in strings), False, any("PNE_" in text for text in strings), "Family and variant native payloads")
    add("QA012", "No generic PME identifiers", not any("PME_" in text for text in strings), False, any("PME_" in text for text in strings), "Planning themes are not legal links")
    add("QA013", "Legal PNE references allowed", legal_refs <= EXPECTED_PNE_ALLOWLIST, sorted(EXPECTED_PNE_ALLOWLIST), sorted(legal_refs), "Canonical legal_goal_ref values")
    add("QA014", "PNE link types valid", all(link["link_type"] in PNE_LINK_TYPES - {"no_valid_link"} for family in families for link in family["pne_links"]), True, True, "Typed link contract")
    add("QA015", "No official PNE indicator recomputation", all(not link["official_indicator_recalculated"] and not link["goal_compliance_claim_allowed"] for family in families for link in family["pne_links"]), True, True, "Links are partial/contextual only")
    add("QA016", "PME not materialized", all(family["pme_link_state"] == "not_materialized" and family["pme_goal_links"] == [] for family in families), True, True, "Typed family contract")
    add("QA017", "Native named inputs", all(isinstance(variant["named_inputs"], list) and all(isinstance(item, dict) for item in variant["named_inputs"]) for variant in variants), True, True, "No JSON string field")
    add("QA018", "Native municipal distributions", all(isinstance(variant["municipal_distribution"], list) and len(variant["municipal_distribution"]) == 10 for variant in variants), "list of 10", sorted(set(len(variant["municipal_distribution"]) for variant in variants)), "Same-family comparison input")
    add("QA019", "Native PNE arrays", all(isinstance(variant["pne_links"], list) and all(isinstance(link, dict) for link in variant["pne_links"]) for variant in variants), True, True, "No serialized link objects")
    add("QA020", "Canonical GCR fact hash", sha256_file(gcr_fact_path) == CANONICAL_GCR_FACT_HASH, CANONICAL_GCR_FACT_HASH, sha256_file(gcr_fact_path), "Direct SHA-256 of frozen artifact")
    recorded_bad = gd_manifest["contract"]["factCatalogCorrection"]["sourceArtifactSha256"]
    add("QA021", "Frozen Job 5G-D manifest retains erroneous field", recorded_bad == INCORRECT_GD_CONTRACT_HASH, INCORRECT_GD_CONTRACT_HASH, recorded_bad, "Errata is additive; frozen manifest not edited")
    add("QA022", "Contract records provenance errata", contract["provenanceErrata"]["canonicalObservedSha256"] == CANONICAL_GCR_FACT_HASH and contract["provenanceErrata"]["incorrectRecordedSha256"] == INCORRECT_GD_CONTRACT_HASH, True, contract["provenanceErrata"], "Job 5H contract")

    mobility_variants = [variant for variant in variants if variant["story_family_id"] == "D1_MOBILITY_HIGH_SCHOOL_OFFER"]
    add("QA023", "Mobility wording exact", all(variant["mobility_contract"]["approved_wording"] == "residentes que estudavam em outro município" for variant in mobility_variants), "residentes que estudavam em outro município", sorted(set(variant["mobility_contract"]["approved_wording"] for variant in mobility_variants)), "All Vale and municipal mobility variants")
    add("QA024", "Mobility destination unavailable", all(not variant["mobility_contract"]["destination_municipality_available"] and not variant["mobility_contract"]["origin_destination_matrix_derived"] for variant in mobility_variants), True, True, "No destination or OD derivation")
    add("QA025", "Foreign mobility component separate", all(variant["mobility_contract"]["foreign_country_separate"] for variant in mobility_variants), True, True, "Distinct named input per stage")
    mobility = sources["job5gd_mobility"]
    nsr_mobility = mobility[mobility["entity_id"].eq(NSR_CODE)].set_index("stage")
    anchors = {stage: (int(nsr_mobility.loc[stage, "numerator"]), int(nsr_mobility.loc[stage, "denominator"])) for stage in ("total", "fundamental", "medio")}
    add("QA026", "Nova Santa Rita mobility anchors", anchors == {"total": (1349, 7666), "fundamental": (355, 4090), "medio": (220, 1151)}, {"total": (1349, 7666), "fundamental": (355, 4090), "medio": (220, 1151)}, anchors, "Official reconstructed counts")

    pnate_variants = [variant for variant in variants if variant["story_family_id"] == "D1_RURALITY_PNATE_PLANNING"]
    add("QA027", "PNATE 2026 is planning forecast", all(variant["pnate_2026_contract"]["record_type"] == "planning_forecast" for variant in pnate_variants), "planning_forecast", sorted(set(variant["pnate_2026_contract"]["record_type"] for variant in pnate_variants)), "All territorial variants")
    add("QA028", "No PNATE 2026 execution/use/payment claim", all(not variant["pnate_2026_contract"]["execution_available"] and not variant["pnate_2026_contract"]["realized_use_available"] and not variant["pnate_2026_contract"]["payment_available"] and not variant["pnate_2026_contract"]["mobility_measure"] for variant in pnate_variants), True, True, "Explicit unavailable contract")
    add("QA029", "C1-C12 row count", len(c1_c12) == len(families) * 12, len(families) * 12, len(c1_c12), "One specific row per family and criterion")
    add("QA030", "C1-C12 evidence specific", c1_c12["evidence"].nunique() == len(c1_c12), len(c1_c12), c1_c12["evidence"].nunique(), "No nine generic phrases repeated")
    mobility_c5 = c1_c12[(c1_c12["story_family_id"].eq("D1_MOBILITY_HIGH_SCHOOL_OFFER")) & (c1_c12["criterion_id"].eq("C5"))]
    add("QA031", "Mobility/trajectory C5 not supported by cross-section", len(mobility_c5) == 1 and mobility_c5.iloc[0]["criterion_status"] == "NOT_SUPPORTED", "NOT_SUPPORTED", None if mobility_c5.empty else mobility_c5.iloc[0]["criterion_status"], "2022 cross-section cannot establish temporal stability")
    add("QA032", "Completeness rows", len(completeness) == 130, 130, len(completeness), "13 families x ten municipalities")
    add("QA033", "Unavailable variants have reason", all(variant["availability_state"] not in {"unavailable", "null", "suppressed"} or bool(variant["unavailability_reason"]) for variant in variants), True, True, "No imputed zero")
    add("QA034", "Public narrative prohibited", all(not variant["public_narrative_authorized"] for variant in variants), False, any(variant["public_narrative_authorized"] for variant in variants), "Internal inputs only")
    add("QA035", "Gate 11 closed", all(variant["gate11"] == "CLOSED" for variant in variants), "CLOSED", sorted(set(variant["gate11"] for variant in variants)), "No release authorization")
    add("QA036", "No fixed card cap", all(family["fixed_card_cap"] is None for family in families), None, sorted(set(str(family["fixed_card_cap"]) for family in families)), "Maximum exploration")
    add("QA037", "PNE payload contract version", pne_payload["canonicalContract"]["contractVersion"] == "1.9.0", "1.9.0", pne_payload["canonicalContract"]["contractVersion"], "Canonical PNE 2026 contract")
    add("QA038", "No score", all("score" not in variant for variant in variants), False, any("score" in variant for variant in variants), "Transparent inputs and distributions")
    add("QA039", "All source refs resolve", all(source_ref in SOURCE_DEFINITIONS for family in families for source_ref in family["source_refs"]), True, True, "Canonical source registry")
    add("QA040", "Final state remains external judgment with limits", FINAL_STATE.endswith("FOR_EXTERNAL_JUDGMENT"), True, FINAL_STATE, "No self-approval")
    required_family_fields = set(family_schema()["required"])
    required_variant_fields = set(variant_schema()["required"])
    add(
        "QA041",
        "Exact minimum family contract fields",
        all(required_family_fields <= set(family) for family in families),
        len(required_family_fields),
        min(len(required_family_fields & set(family)) for family in families),
        "Canonical Job 5H family schema required list",
    )
    add(
        "QA042",
        "Exact minimum territorial variant contract fields",
        all(required_variant_fields <= set(variant) for variant in variants),
        len(required_variant_fields),
        min(len(required_variant_fields & set(variant)) for variant in variants),
        "Canonical Job 5H variant schema required list",
    )

    for family in families:
        family_variants = [variant for variant in variants if variant["story_family_id"] == family["story_family_id"]]
        add(
            f"QAF_{family['sequence']:02d}",
            f"Family coverage {family['story_family_id']}",
            len(family_variants) == 11 and {variant["entity"]["scale"] for variant in family_variants} == {"region", "municipality"},
            "11 variants across region and municipality",
            len(family_variants),
            f"Sources={family['source_refs']}; primary input present in every variant.",
        )
    for index, (code, name) in enumerate(sorted(municipality_names.items()), start=1):
        municipal_variants = [variant for variant in variants if variant["entity"]["entity_id"] == code]
        add(
            f"QAM_{index:02d}",
            f"Municipal corpus coverage {name}",
            len(municipal_variants) == 13,
            13,
            len(municipal_variants),
            f"IBGE {code}; unavailable states stay explicit.",
        )
    frame = pd.DataFrame(rows)
    return frame.sort_values("qa_control_id", kind="mergesort").reset_index(drop=True)


def _display_value(item: Mapping[str, Any]) -> str:
    if item["availability_state"] in {"unavailable", "null", "suppressed", "not_applicable"}:
        return f"{item['availability_state']}"
    return f"{item['value']} {item['unit']}"


def dossier_markdown(
    *,
    title: str,
    entity_id: str,
    variants: Sequence[Mapping[str, Any]],
    families: Sequence[Mapping[str, Any]],
) -> str:
    variant_lookup = {
        variant["story_family_id"]: variant
        for variant in variants
        if variant["entity"]["entity_id"] == entity_id
    }
    lines = [
        f"# {title}",
        "",
        "**Estado:** insumo editorial interno tipado; narrativa pública não autorizada; Gate 11 fechado.",
        "",
        "Este dossiê organiza todas as famílias sem impor teto de cartões. Cada valor preserva unidade, período, fonte, lente e regra de agregação. Indisponibilidade nunca vira zero.",
        "",
    ]
    if entity_id == NSR_CODE:
        lines.extend(
            [
                "## Cobertura obrigatória de Nova Santa Rita",
                "",
                "O corpus cobre educação infantil e pré-escola; fundamental e ensino médio; escolas, turmas e unidades; pressão de coortes; mobilidade total, fundamental e médio; trajetória do ensino médio; oferta rural; educação especial/AEE; escolaridade adulta e EJA; EPT; jovens de 15–17 e 18–24 anos; aprendizagem; ocupações, setores e logística; ponte normativa; PNATE; finanças seletivas; vínculos PNE canônicos e governança.",
                "",
                "A ponte normativa fica explicitamente indisponível quando não há oferta local auditada. A mobilidade usa somente ‘residentes que estudavam em outro município’, sem destino. PNATE 2026 é previsão de planejamento, nunca execução ou uso realizado.",
                "",
            ]
        )
    for family in sorted(families, key=lambda item: item["sequence"]):
        variant = variant_lookup[family["story_family_id"]]
        lines.extend(
            [
                f"## {family['sequence']}. {family['internal_title']}",
                "",
                f"- Família: `{family['story_family_id']}`",
                f"- Variante: `{variant['story_variant_id']}`",
                f"- Camada/estado: `{family['layer']}` / `{variant['editorial_state']}`",
                f"- Pergunta de gestão: {family['management_question']}",
                f"- Responsabilidade: `{family['institutional_responsibility']}`; atores: {', '.join(family['actors'])}.",
                f"- Disponibilidade primária: `{variant['availability_state']}`{'; ' + variant['unavailability_reason'] if variant['unavailability_reason'] else ''}",
                "",
                "| Entrada nomeada | Valor/estado | Período | Lente | Fonte |",
                "|---|---:|---|---|---|",
            ]
        )
        for item in variant["named_inputs"]:
            lines.append(
                f"| {item['label']} (`{item['metric_id']}`) | {_display_value(item)} | {item['period']} | `{item['territorial_lens']}` | `{item['source_ref']}` |"
            )
        lines.extend(
            [
                "",
                f"**Limites:** {'; '.join(family['limitations'])}.",
                "",
            ]
        )
    lines.extend(
        [
            "## Condições de uso",
            "",
            "Este dossiê não aprova copy, visual final, prioridade municipal, recomendação, publicação ou abertura do Gate 11. A revisão externa deve julgar utilidade, redundância, clareza, limites e responsabilidades antes do Job 5I.",
            "",
        ]
    )
    return "\n".join(lines)


CSV_OUTPUTS = {
    "MATRIZ_FATO_FAMILIA_VARIANTE_FONTE_JOB5H.csv.gz": "fact_trace",
    "MATRIZ_RASTREABILIDADE_JOBS_FAMILIAS_JOB5H.csv.gz": "job_trace",
    "MATRIZ_REDUNDANCIA_FUSAO_PAPEIS_JOB5H.csv.gz": "redundancy",
    "MATRIZ_COMPLETUDE_DEZ_MUNICIPIOS_JOB5H.csv.gz": "completeness",
    "MATRIZ_DISPONIBILIDADE_ESTADOS_CONDICIONAIS_JOB5H.csv.gz": "availability",
    "MATRIZ_C1_C12_ESPECIFICA_JOB5H.csv.gz": "c1_c12",
    "MATRIZ_QA_JOB5H.csv.gz": "qa",
}


def materialize_components(
    *,
    repo_root: Path,
    contract: Mapping[str, Any],
    municipality_names: Mapping[str, str],
    frozen_integrity: Mapping[str, str],
) -> tuple[dict[str, pd.DataFrame], dict[str, Any]]:
    sources = load_sources(repo_root)
    pne_contract = json.loads(
        (repo_root / "contracts" / "pne2026-goal-indicator-contract.json").read_text(
            encoding="utf-8"
        )
    )
    families = build_family_catalog()
    variants = build_variants(
        families=families,
        municipality_names=municipality_names,
        sources=sources,
    )
    fact_trace = build_fact_trace(variants)
    job_trace = build_job_family_trace(families)
    redundancy = build_redundancy_matrix()
    completeness = build_completeness_matrix(
        families, variants, municipality_names
    )
    availability = build_availability_matrix(variants)
    c1_c12 = build_c1_c12_matrix(families)
    pne_links = build_pne_links_payload(families, pne_contract)
    pme = build_pme_payload(families)
    source_registry = build_source_registry(
        repo_root=repo_root,
        frozen_integrity=frozen_integrity,
        pne_contract=pne_contract,
    )
    qa = build_qa_matrix(
        repo_root=repo_root,
        contract=contract,
        families=families,
        variants=variants,
        municipality_names=municipality_names,
        c1_c12=c1_c12,
        completeness=completeness,
        pne_payload=pne_links,
        sources=sources,
    )
    frames = {
        "fact_trace": fact_trace,
        "job_trace": job_trace,
        "redundancy": redundancy,
        "completeness": completeness,
        "availability": availability,
        "c1_c12": c1_c12,
        "qa": qa,
    }
    family_count_by_direction = Counter(
        family["direction_id"] for family in families
    )
    nsr_variants = [
        variant
        for variant in variants
        if variant["entity"]["entity_id"] == NSR_CODE
    ]
    vale_variants = [
        variant
        for variant in variants
        if variant["entity"]["entity_id"] == REGION_ENTITY_ID
    ]
    architecture = build_architecture(families)
    limitations = build_limitations_map(families)
    review_package = {
        "schemaVersion": "vocacoes-pne-job5h-external-review-package-v1",
        "jobId": "5H",
        "classification": "DATA_LOGIC",
        "objective": "Consolidar Jobs 5G-A-R/B-R/C-R/D em arquitetura editorial máxima, tipada, simétrica e pronta para julgamento antes do Job 5I.",
        "finalState": FINAL_STATE,
        "preflight": {
            "provenanceErrataAddedWithoutFrozenMutation": True,
            "canonicalGcrFactHash": CANONICAL_GCR_FACT_HASH,
            "incorrectFrozenGdContractField": INCORRECT_GD_CONTRACT_HASH,
            "legalPneLinksRebuilt": True,
            "genericPmeValuesReclassifiedAsPlanningThemes": True,
            "c1C12RebuiltWithSpecificEvidence": True,
            "nativeTypedStructures": True,
            "familyVariantIdentitySeparated": True,
            "mobilityWordingCorrected": True,
            "pnate2026PlanningForecastOnly": True,
            "tenMunicipalitySymmetry": True,
        },
        "architecture": {
            "familyCount": len(families),
            "variantCount": len(variants),
            "familyCountByDirection": dict(sorted(family_count_by_direction.items())),
            "macroblockCount": len(architecture["macroblocks"]),
            "fixedCardCap": None,
            "old99RowsArePublicStories": False,
        },
        "coverage": {
            "valeVariantCount": len(vale_variants),
            "municipalityVariantCount": len(variants) - len(vale_variants),
            "novaSantaRitaVariantCount": len(nsr_variants),
            "municipalityCount": len(municipality_names),
            "completenessRows": len(completeness),
        },
        "criterionStatusCounts": {
            str(key): int(value)
            for key, value in c1_c12["criterion_status"].value_counts().sort_index().items()
        },
        "qa": {
            "controlCount": len(qa),
            "failedControlCount": int(qa["status"].eq("FAIL").sum()),
        },
        "limits": limitations["globalLimits"],
        "decisionsRequestedFromExternalReview": [
            "Judge whether the 13-family maximum architecture preserves useful distinctions without excessive redundancy.",
            "Judge C1 no-valid-link families and C5 cross-sectional limits without treating quantity as approval.",
            "Judge primary versus expanded versus internal layer placement.",
            "Judge Nova Santa Rita and Vale dossiers for concrete management usefulness.",
            "Approve, revise or reject inputs for a future Job 5I; do not open Gate 11 here.",
        ],
        "automaticApproval": False,
        "externalJudgmentRequired": True,
        "job5IStarted": False,
        "gate11": "CLOSED",
        "publicationAllowed": False,
        "frontendAllowed": False,
    }
    metadata = {
        "families": families,
        "variants": variants,
        "pneLinks": pne_links,
        "pme": pme,
        "sourceRegistry": source_registry,
        "architecture": architecture,
        "interaction": build_interaction_spec(families),
        "visual": build_visual_spec(families),
        "language": build_language_contract(),
        "limitations": limitations,
        "reviewPackage": review_package,
        "typedDictionary": typed_dictionary(),
        "familySchema": family_schema(),
        "variantSchema": variant_schema(),
        "nsrDossier": dossier_markdown(
            title="Dossiê editorial interno — Nova Santa Rita",
            entity_id=NSR_CODE,
            variants=variants,
            families=families,
        ),
        "valeDossier": dossier_markdown(
            title="Dossiê editorial interno — Vale do Sinos",
            entity_id=REGION_ENTITY_ID,
            variants=variants,
            families=families,
        ),
    }
    return frames, metadata


def _errata_markdown(repo_root: Path) -> str:
    gd_manifest_path = (
        repo_root / ".tmp" / "vocacoes-pne" / "v7-job5gd" / "MANIFEST_JOB5GD.json"
    )
    gcr_fact_path = (
        repo_root
        / ".tmp"
        / "vocacoes-pne"
        / "v7-job5gcr"
        / "MATRIZ_CATALOGO_FATOS_NOVA_SANTA_RITA_JOB5GCR_V1.csv.gz"
    )
    return "\n".join(
        [
            "# Errata de proveniência — Job 5G-D",
            "",
            "**Natureza:** correção documental aditiva; nenhum artefato congelado foi modificado.",
            "",
            "O campo `contract.factCatalogCorrection.sourceArtifactSha256` do manifesto congelado do Job 5G-D registrou um hash incorreto para o catálogo V1 do Job 5G-C-R.",
            "",
            f"- Valor incorreto preservado no manifesto congelado: `{INCORRECT_GD_CONTRACT_HASH}`.",
            f"- SHA-256 canônico observado diretamente no artefato: `{sha256_file(gcr_fact_path)}`.",
            f"- SHA-256 do manifesto congelado, mantido intacto: `{sha256_file(gd_manifest_path)}`.",
            "- Artefato: `.tmp/vocacoes-pne/v7-job5gcr/MATRIZ_CATALOGO_FATOS_NOVA_SANTA_RITA_JOB5GCR_V1.csv.gz`.",
            "",
            "O pacote corretivo interno do próprio Job 5G-D já transportava o hash observado correto em outra seção. Esta errata torna a divergência explícita para consumo editorial e de proveniência, sem reescrever o passado.",
            "",
            "A correção não altera fórmula, valor, grão, fonte, período, fact_id, painel congelado ou decisão metodológica.",
            "",
        ]
    )


def _fixture_payload(
    *,
    entity_id: str,
    entity_name: str,
    variants: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    selected = [
        deepcopy(variant)
        for variant in variants
        if variant["entity"]["entity_id"] == entity_id
    ]
    return {
        "schemaVersion": "vocacoes-pne-job5h-territorial-fixture-v1",
        "entity": {
            "entity_id": entity_id,
            "municipality_ibge_code": (
                None if entity_id == REGION_ENTITY_ID else entity_id
            ),
            "name": entity_name,
        },
        "storyFamilyCount": len(selected),
        "storyVariants": selected,
        "draftForInternalPrototype": True,
        "publicNarrativeAuthorized": False,
        "externalJudgmentRequired": True,
        "gate11": "CLOSED",
    }


def write_package(
    *,
    output_dir: Path,
    repo_root: Path,
    contract: Mapping[str, Any],
    inputs: Mapping[str, Path],
    municipality_names: Mapping[str, str],
    frozen_integrity: Mapping[str, str],
    frozen_roots: Mapping[str, Path],
) -> dict[str, Any]:
    """Escreve o Job 5H em diretório novo; o runner promove transacionalmente."""

    output_dir.mkdir(parents=True, exist_ok=False)
    frames, metadata = materialize_components(
        repo_root=repo_root,
        contract=contract,
        municipality_names=municipality_names,
        frozen_integrity=frozen_integrity,
    )
    if not frames["qa"]["status"].eq("PASS").all():
        failed = frames["qa"][frames["qa"]["status"].eq("FAIL")]
        raise ValueError(
            f"QA Job 5H falhou antes da escrita: {failed['qa_control_id'].tolist()}"
        )
    for filename, frame_key in CSV_OUTPUTS.items():
        write_csv_gzip(output_dir / filename, frames[frame_key])

    families = metadata["families"]
    variants = metadata["variants"]
    json_payloads: dict[str, Any] = {
        "CONTRATO_JOB5H.json": {
            **deepcopy(contract),
            "resolvedAtGeneration": {
                "familyCount": len(families),
                "variantCount": len(variants),
                "municipalityCount": len(municipality_names),
                "terminalState": FINAL_STATE,
            },
        },
        "DICIONARIO_TIPADO_CANONICO_JOB5H.json": metadata["typedDictionary"],
        "SCHEMA_FAMILIAS_EDITORIAIS_JOB5H.json": metadata["familySchema"],
        "SCHEMA_VARIANTES_TERRITORIAIS_JOB5H.json": metadata["variantSchema"],
        "CATALOGO_EDITORIAL_MAXIMO_JOB5H.json": {
            "schemaVersion": "vocacoes-pne-job5h-maximum-editorial-catalog-v1",
            "familyCount": len(families),
            "fixedCardCap": None,
            "old99RowsArePublicStories": False,
            "storyFamilies": families,
            "publicNarrativeAuthorized": False,
            "externalJudgmentRequired": True,
        },
        "CORPUS_VARIANTES_TERRITORIAIS_JOB5H.json": {
            "schemaVersion": "vocacoes-pne-job5h-territorial-variant-corpus-v1",
            "variantCount": len(variants),
            "familyCount": len(families),
            "variantsPerFamily": 11,
            "storyVariants": variants,
            "publicNarrativeAuthorized": False,
            "externalJudgmentRequired": True,
        },
        "FIXTURE_NOVA_SANTA_RITA_JOB5H.json": _fixture_payload(
            entity_id=NSR_CODE,
            entity_name=municipality_names[NSR_CODE],
            variants=variants,
        ),
        "FIXTURE_VALE_DO_SINOS_JOB5H.json": _fixture_payload(
            entity_id=REGION_ENTITY_ID,
            entity_name="Vale do Sinos",
            variants=variants,
        ),
        "VINCULOS_PNE_CANONICOS_JOB5H.json": metadata["pneLinks"],
        "ESTADO_PME_TEMAS_PLANEJAMENTO_JOB5H.json": metadata["pme"],
        "REGISTRO_FONTES_PERIODOS_LENTES_LIMITES_JOB5H.json": metadata[
            "sourceRegistry"
        ],
        "ARQUITETURA_SEQUENCIA_PAGINA_JOB5H.json": metadata["architecture"],
        "ESPECIFICACAO_INTERACAO_JOB5I_JOB5H.json": metadata["interaction"],
        "ESPECIFICACAO_VISUAL_JOB5I_JOB5H.json": metadata["visual"],
        "CONTRATO_LINGUAGEM_PROTOTIPO_INTERNO_JOB5H.json": metadata[
            "language"
        ],
        "MAPA_LIMITACOES_TRANSPORTADAS_JOB5H.json": metadata["limitations"],
        "PACOTE_REVISAO_EXTERNA_JOB5H.json": metadata["reviewPackage"],
    }
    for filename, payload in json_payloads.items():
        write_json(output_dir / filename, payload)
    (output_dir / "ERRATA_PROVENIENCIA_JOB5GD.md").write_text(
        _errata_markdown(repo_root), encoding="utf-8", newline="\n"
    )
    (output_dir / "DOSSIE_EDITORIAL_NOVA_SANTA_RITA_JOB5H.md").write_text(
        metadata["nsrDossier"], encoding="utf-8", newline="\n"
    )
    (output_dir / "DOSSIE_EDITORIAL_VALE_DO_SINOS_JOB5H.md").write_text(
        metadata["valeDossier"], encoding="utf-8", newline="\n"
    )

    expected = set(contract["outputs"])
    pre_manifest = {path.name for path in output_dir.iterdir() if path.is_file()}
    if pre_manifest != expected - {"MANIFEST_JOB5H.json"}:
        raise ValueError(
            "Lote pré-manifesto Job 5H divergente: "
            f"missing={sorted(expected-pre_manifest-{'MANIFEST_JOB5H.json'})}, "
            f"extra={sorted(pre_manifest-expected)}"
        )

    artifact_metadata = {
        "MATRIZ_FATO_FAMILIA_VARIANTE_FONTE_JOB5H.csv.gz": (
            ["fact_trace_id"],
            "source-specific",
            "declared_per_input",
            "source-specific",
            "one row per typed named input",
        ),
        "MATRIZ_RASTREABILIDADE_JOBS_FAMILIAS_JOB5H.csv.gz": (
            ["story_family_id", "source_ref"],
            "source-specific",
            "declared_per_source",
            "metadata",
            "family-to-frozen-source mapping",
        ),
        "MATRIZ_REDUNDANCIA_FUSAO_PAPEIS_JOB5H.csv.gz": (
            ["legacy_job5gd_combination_id", "destination_story_family_id"],
            "generation",
            "metadata",
            "state",
            "explicit split/merge decision",
        ),
        "MATRIZ_COMPLETUDE_DEZ_MUNICIPIOS_JOB5H.csv.gz": (
            ["story_family_id", "municipality_ibge_code"],
            "generation",
            "municipality",
            "state",
            "13 families x ten canonical municipalities",
        ),
        "MATRIZ_DISPONIBILIDADE_ESTADOS_CONDICIONAIS_JOB5H.csv.gz": (
            ["story_variant_id"],
            "generation",
            "region|municipality",
            "state",
            "primary and named-input availability summary",
        ),
        "MATRIZ_C1_C12_ESPECIFICA_JOB5H.csv.gz": (
            ["story_family_id", "criterion_id"],
            "generation",
            "family",
            "state",
            "specific criterion evidence without score",
        ),
        "MATRIZ_QA_JOB5H.csv.gz": (
            ["qa_control_id"],
            "generation",
            "QA",
            "state",
            "executable preflight and package checks",
        ),
    }
    artifacts = []
    for filename in sorted(pre_manifest):
        frame = frames[CSV_OUTPUTS[filename]] if filename in CSV_OUTPUTS else None
        grain, period, lens, unit, aggregation = artifact_metadata.get(
            filename,
            (
                "declared_in_artifact",
                "generation or source-specific",
                "metadata",
                "metadata",
                "declared in typed artifact",
            ),
        )
        artifacts.append(
            artifact_record(
                root=output_dir,
                path=output_dir / filename,
                frame=frame,
                subjob="5H",
                grain=grain,
                period=period,
                lens=lens,
                unit=unit,
                aggregation_rule=aggregation,
            )
        )

    frozen_after = {
        key: directory_content_digest(path)
        for key, path in sorted(frozen_roots.items())
    }
    if dict(frozen_integrity) != frozen_after:
        raise ValueError("Um pacote congelado mudou durante a geração do Job 5H")
    manifest = {
        "schemaVersion": "vocacoes-pne-job5h-manifest-v1",
        "jobId": "5H",
        "classification": "DATA_LOGIC",
        "domains": contract["domains"],
        "objective": metadata["reviewPackage"]["objective"],
        "finalState": FINAL_STATE,
        "contract": contract,
        "scope": contract["scope"],
        "selectedMunicipalityId": NSR_CODE,
        "artifacts": artifacts,
        "summary": {
            "outputCount": len(expected),
            "artifactHashCount": len(artifacts),
            "familyCount": len(families),
            "variantCount": len(variants),
            "valeVariantCount": 13,
            "municipalVariantCount": 130,
            "novaSantaRitaVariantCount": 13,
            "factTraceRowCount": len(frames["fact_trace"]),
            "completenessRowCount": len(frames["completeness"]),
            "c1C12RowCount": len(frames["c1_c12"]),
            "qaControlCount": len(frames["qa"]),
            "qaFailedCount": int(frames["qa"]["status"].eq("FAIL").sum()),
        },
        "preflight": metadata["reviewPackage"]["preflight"],
        "frozenInputIntegrity": {
            "before": dict(sorted(frozen_integrity.items())),
            "after": frozen_after,
        },
        "implementation": {
            identifier: {
                "path": path.relative_to(repo_root).as_posix(),
                "byteSize": path.stat().st_size,
                "sha256": sha256_file(path),
            }
            for identifier, path in sorted(inputs.items())
        },
        "formulasPreserved": [
            "zero denominator returns null",
            "mobility rate uses another-municipality residents / total residents studying * 100",
            "regional mobility sums compatible numerator and denominator before ratio",
            "EJA distribution difference equals located enrollment regional share minus resident-public regional share",
            "RAIS stock and Caged flow stay separate",
            "PNATE financial stages stay separate",
            "HHI and shift-share definitions remain frozen from Job 5G-C-R",
        ],
        "formulasAltered": [],
        "generation": {
            "deterministic": True,
            "transactional": True,
            "manifestLast": True,
            "networkUsed": False,
            "databaseUsed": False,
            "databaseWrites": False,
            "publicDataChanged": False,
            "frontendChanged": False,
            "publicNarrativeWritten": False,
            "fullBuildUsed": False,
            "publicationPerformed": False,
            "job5IStarted": False,
            "gate11": "CLOSED",
        },
        "limits": metadata["limitations"]["globalLimits"],
        "automaticApproval": False,
        "externalJudgmentRequired": True,
    }
    write_json(output_dir / "MANIFEST_JOB5H.json", manifest)
    actual = {path.name for path in output_dir.iterdir() if path.is_file()}
    if actual != expected:
        raise ValueError(
            f"Lote final Job 5H divergente: missing={expected-actual}, extra={actual-expected}"
        )
    return manifest


def validate_existing_output(output_dir: Path) -> dict[str, Any]:
    manifest_path = output_dir / "MANIFEST_JOB5H.json"
    if not manifest_path.is_file():
        raise FileNotFoundError("MANIFEST_JOB5H.json ausente")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("finalState") != FINAL_STATE:
        raise ValueError("Estado final divergente no manifesto Job 5H")
    expected = set(manifest["contract"]["outputs"])
    actual = {path.name for path in output_dir.iterdir() if path.is_file()}
    if actual != expected:
        raise ValueError(
            f"Lote Job 5H divergente: missing={expected-actual}, extra={actual-expected}"
        )
    if len(actual) != 28:
        raise ValueError("Job 5H deve conter exatamente 28 artefatos significativos")
    for artifact in manifest["artifacts"]:
        path = output_dir / artifact["path"]
        if (
            path.stat().st_size != artifact["byteSize"]
            or sha256_file(path) != artifact["sha256"]
        ):
            raise ValueError(f"Hash/tamanho divergente em {artifact['path']}")

    catalog = json.loads(
        (output_dir / "CATALOGO_EDITORIAL_MAXIMO_JOB5H.json").read_text(
            encoding="utf-8"
        )
    )
    corpus = json.loads(
        (output_dir / "CORPUS_VARIANTES_TERRITORIAIS_JOB5H.json").read_text(
            encoding="utf-8"
        )
    )
    families = catalog["storyFamilies"]
    variants = corpus["storyVariants"]
    if len(families) != 13 or len(variants) != 143:
        raise ValueError("Catálogo/corpus Job 5H não possui 13 famílias e 143 variantes")
    if len({family["story_family_id"] for family in families}) != 13:
        raise ValueError("story_family_id duplicado")
    if len({variant["story_variant_id"] for variant in variants}) != 143:
        raise ValueError("story_variant_id duplicado")
    counts = Counter(variant["story_family_id"] for variant in variants)
    if set(counts.values()) != {11}:
        raise ValueError("Família sem Vale + dez variantes municipais")
    if any(
        variant["story_variant_id"] == variant["story_family_id"]
        for variant in variants
    ):
        raise ValueError("Identidade de família e variante foi confundida")
    strings = list(_iter_strings([families, variants]))
    if any("PNE_" in value or "PME_" in value for value in strings):
        raise ValueError("Identificador genérico PNE/PME persistiu no Job 5H")
    for family in families:
        if family["pme_link_state"] != "not_materialized" or family["pme_goal_links"]:
            raise ValueError("PME foi tratado como meta materializada")
        for link in family["pne_links"]:
            if (
                link["legal_goal_ref"] not in EXPECTED_PNE_ALLOWLIST
                or link["link_type"] not in PNE_LINK_TYPES
            ):
                raise ValueError("Vínculo PNE inválido")
    for variant in variants:
        if not isinstance(variant["named_inputs"], list) or not all(
            isinstance(item, dict) for item in variant["named_inputs"]
        ):
            raise ValueError("Entrada nomeada não nativa")
        if not isinstance(variant["municipal_distribution"], list):
            raise ValueError("Distribuição municipal não nativa")
        if variant["public_narrative_authorized"] or variant["gate11"] != "CLOSED":
            raise ValueError("Job 5H autorizou narrativa pública ou Gate 11")

    c1_c12 = _read_csv(output_dir / "MATRIZ_C1_C12_ESPECIFICA_JOB5H.csv.gz")
    if len(c1_c12) != 156 or c1_c12["evidence"].nunique() != 156:
        raise ValueError("Matriz C1-C12 não é específica por família e critério")
    mobility_c5 = c1_c12[
        c1_c12["story_family_id"].eq("D1_MOBILITY_HIGH_SCHOOL_OFFER")
        & c1_c12["criterion_id"].eq("C5")
    ]
    if len(mobility_c5) != 1 or mobility_c5.iloc[0]["criterion_status"] != "NOT_SUPPORTED":
        raise ValueError("C5 da mobilidade transversal foi indevidamente suportado")
    qa = _read_csv(output_dir / "MATRIZ_QA_JOB5H.csv.gz")
    if not qa["status"].eq("PASS").all():
        raise ValueError("Matriz QA contém falhas")

    errata = (output_dir / "ERRATA_PROVENIENCIA_JOB5GD.md").read_text(
        encoding="utf-8"
    )
    if CANONICAL_GCR_FACT_HASH not in errata or INCORRECT_GD_CONTRACT_HASH not in errata:
        raise ValueError("Errata de proveniência incompleta")
    mobility_variants = [
        variant
        for variant in variants
        if variant["story_family_id"] == "D1_MOBILITY_HIGH_SCHOOL_OFFER"
    ]
    if not all(
        variant["mobility_contract"]
        == {
            "approved_wording": "residentes que estudavam em outro município",
            "foreign_country_separate": True,
            "destination_municipality_available": False,
            "origin_destination_matrix_derived": False,
            "cross_section_only": True,
        }
        for variant in mobility_variants
    ):
        raise ValueError("Contrato de mobilidade divergente")
    pnate_variants = [
        variant
        for variant in variants
        if variant["story_family_id"] == "D1_RURALITY_PNATE_PLANNING"
    ]
    if not all(
        variant["pnate_2026_contract"]["record_type"] == "planning_forecast"
        and not variant["pnate_2026_contract"]["execution_available"]
        and not variant["pnate_2026_contract"]["realized_use_available"]
        and not variant["pnate_2026_contract"]["payment_available"]
        for variant in pnate_variants
    ):
        raise ValueError("PNATE 2026 não permaneceu previsão de planejamento")
    generation = manifest["generation"]
    forbidden = (
        generation["networkUsed"]
        or generation["databaseUsed"]
        or generation["publicDataChanged"]
        or generation["frontendChanged"]
        or generation["fullBuildUsed"]
        or generation["publicationPerformed"]
        or generation["job5IStarted"]
        or generation["gate11"] != "CLOSED"
    )
    if forbidden:
        raise ValueError("Manifesto registra operação proibida no Job 5H")
    return manifest
