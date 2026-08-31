from __future__ import annotations

from collections import defaultdict
import argparse
import csv
from dataclasses import dataclass, field
import gzip
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import tempfile
from typing import Any, Iterable, Mapping, Sequence


REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_ROOT = REPO_ROOT / ".tmp" / "vocacoes-pne" / "v7-job5i"
FRONTEND_GENERATED_ROOT = (
    REPO_ROOT
    / "src"
    / "features"
    / "vocacoes-pne-internal"
    / "generated"
)
FRONTEND_CORE_BUNDLE = FRONTEND_GENERATED_ROOT / "vocacoesPneJob5iCore.json"
FRONTEND_SERIES_BUNDLE = FRONTEND_GENERATED_ROOT / "vocacoesPneJob5iSeries.json"
FRONTEND_TECHNICAL_BUNDLE = FRONTEND_GENERATED_ROOT / "vocacoesPneJob5iTechnical.json"
JOB5H_ROOT = REPO_ROOT / ".tmp" / "vocacoes-pne" / "v7-job5h"
JOB5GAR_ROOT = REPO_ROOT / ".tmp" / "vocacoes-pne" / "v7-job5gar"
JOB5GBR_ROOT = REPO_ROOT / ".tmp" / "vocacoes-pne" / "v7-job5gbr"
JOB5GCR_ROOT = REPO_ROOT / ".tmp" / "vocacoes-pne" / "v7-job5gcr"
JOB5GD_ROOT = REPO_ROOT / ".tmp" / "vocacoes-pne" / "v7-job5gd"

REGION_ID = "REGION_VALE_DO_SINOS"
REGION_NAME = "Vale do Sinos"
FALLBACK_MUNICIPALITY_IBGE_CODE = "4313375"
NETWORK_SCOPE = "total_all_dependencies"
GENERATED_AT = "2026-08-29T00:00:00-03:00"

AVAILABILITY_STATES = {
    "observed",
    "observed_zero",
    "unavailable",
    "not_applicable",
    "suppressed",
}
TERRITORIAL_LENSES = {
    "resident_population",
    "student_residence",
    "school_location",
    "rural_school_location",
    "workplace",
    "municipal_executor",
}

DIRECTION_DEFINITIONS = [
    {
        "directionId": "TERRITORY_HELPS_UNDERSTAND_EDUCATION",
        "sequence": 1,
        "title": "O que o território ajuda a compreender sobre a educação?",
        "summary": (
            "Oferta observada, trajetória, mobilidade, ruralidade e inclusão são "
            "lidas com lentes territoriais separadas."
        ),
    },
    {
        "directionId": "TERRITORIAL_TRANSFORMATIONS_SET_EDUCATION_AGENDA",
        "sequence": 2,
        "title": "Que transformações do território colocam temas na agenda da educação?",
        "summary": (
            "Trabalho formal, aprendizagem profissional, economia e oferta EPT são "
            "acompanhados em paralelo, sem inferência automática."
        ),
    },
]

MACROBLOCK_DEFINITIONS = [
    {
        "macroblockId": "A_DEMOGRAPHY_AND_OFFER",
        "directionId": "TERRITORY_HELPS_UNDERSTAND_EDUCATION",
        "sequence": 1,
        "title": "Demografia, coortes e resposta da oferta",
        "summary": "A oferta observada vem primeiro; a pressão mecânica aparece como marcador não preditivo.",
        "primaryQuestion": "Como matrículas, escolas e turmas mudaram por etapa?",
        "familyIds": ["D1_COHORT_OFFER_CAPACITY"],
    },
    {
        "macroblockId": "B_TRAJECTORY_AND_CONDITIONS",
        "directionId": "TERRITORY_HELPS_UNDERSTAND_EDUCATION",
        "sequence": 2,
        "title": "Trajetória e condições",
        "summary": "Taxas municipais e distribuições compatíveis, com condições da oferta em evidência expandida.",
        "primaryQuestion": "Que etapa e indicador, com articulação entre as redes responsáveis, precisam de acompanhamento?",
        "familyIds": ["D1_TRAJECTORY_CONDITIONS"],
    },
    {
        "macroblockId": "C_MOBILITY_AND_HIGH_SCHOOL",
        "directionId": "TERRITORY_HELPS_UNDERSTAND_EDUCATION",
        "sequence": 3,
        "title": "Mobilidade e ensino médio",
        "summary": "Fotografia de 2022 dos residentes que estudavam em outro município, sem destinos ou rotas.",
        "primaryQuestion": "Que coordenação da oferta de ensino médio a fotografia municipal ajuda a organizar?",
        "familyIds": ["D1_MOBILITY_HIGH_SCHOOL_OFFER"],
    },
    {
        "macroblockId": "D_RURALITY_AND_TRANSPORT",
        "directionId": "TERRITORY_HELPS_UNDERSTAND_EDUCATION",
        "sequence": 4,
        "title": "Ruralidade e transporte",
        "summary": "Oferta rural observada e registros do PNATE separados por estágio administrativo.",
        "primaryQuestion": "Como planejamento e coordenação do transporte se relacionam à oferta rural observada?",
        "familyIds": ["D1_RURALITY_PNATE_PLANNING"],
    },
    {
        "macroblockId": "E_INCLUSION_AND_ADULTS",
        "directionId": "TERRITORY_HELPS_UNDERSTAND_EDUCATION",
        "sequence": 5,
        "title": "Inclusão, escolaridade adulta e EJA",
        "summary": "Público residente e matrículas localizadas permanecem em universos distintos.",
        "primaryQuestion": "Que diferenças de distribuição e oferta precisam permanecer visíveis?",
        "familyIds": ["D1_ADULT_SCHOOLING_EJA", "D1_SPECIAL_AEE_TERRITORY"],
    },
    {
        "macroblockId": "F_YOUTH_WORK_AND_TRAINING",
        "directionId": "TERRITORIAL_TRANSFORMATIONS_SET_EDUCATION_AGENDA",
        "sequence": 6,
        "title": "Trabalho juvenil e aprendizagem",
        "summary": "Estoque RAIS, fluxo Caged, aprendizagem e ensino médio são séries separadas.",
        "primaryQuestion": "Que sinais de 15 a 17 e de 18 a 24 anos precisam ser acompanhados em paralelo?",
        "familyIds": ["D2_YOUTH_WORK_15_17", "D2_APPRENTICESHIP", "D2_YOUTH_WORK_18_24"],
    },
    {
        "macroblockId": "G_ECONOMY_EPT_AND_COORDINATION",
        "directionId": "TERRITORIAL_TRANSFORMATIONS_SET_EDUCATION_AGENDA",
        "sequence": 7,
        "title": "Economia, EPT e coordenação",
        "summary": "Mudanças materiais, oferta EPT e cobertura da ponte chegam a uma pergunta de planejamento.",
        "primaryQuestion": "Que diálogo regional a oferta observada e as correspondências disponíveis permitem organizar?",
        "familyIds": [
            "D2_OCCUPATIONS_SECTORS",
            "D2_EPT_TERRITORIAL_OFFER",
            "D2_NORMATIVE_WORK_EDUCATION_BRIDGE",
            "D2_SECTOR_TRANSFORMATION_SHIFT_SHARE",
        ],
    },
]

VISUAL_CONTRACTS = [
    {
        "visualContractId": f"visual-{item['macroblockId'].lower().replace('_', '-')}",
        "macroblockId": item["macroblockId"],
        "title": item["title"],
        "measure": {
            "A_DEMOGRAPHY_AND_OFFER": "matrículas, escolas, turmas e marcador mecânico",
            "B_TRAJECTORY_AND_CONDITIONS": "taxas municipais e distribuição municipal",
            "C_MOBILITY_AND_HIGH_SCHOOL": "residentes que estudavam em outro município e oferta localizada",
            "D_RURALITY_AND_TRANSPORT": "oferta rural e registros PNATE por estágio",
            "E_INCLUSION_AND_ADULTS": "contagens, composição e matrículas localizadas",
            "F_YOUTH_WORK_AND_TRAINING": "estoque de vínculos e fluxos de eventos separados",
            "G_ECONOMY_EPT_AND_COORDINATION": "mudanças de estoque, oferta EPT e cobertura da ponte",
        }[item["macroblockId"]],
        "unit": "declarada em cada série ou fato; percentuais sempre em escala 0–100",
        "period": {
            "A_DEMOGRAPHY_AND_OFFER": "2014–2025; marcador mecânico com referência 2025",
            "B_TRAJECTORY_AND_CONDITIONS": "2018–2025; condições conforme disponibilidade",
            "C_MOBILITY_AND_HIGH_SCHOOL": "fotografia 2022; oferta 2014–2025",
            "D_RURALITY_AND_TRANSPORT": "2014–2025; PNATE 2024–2026",
            "E_INCLUSION_AND_ADULTS": "2010 e 2022; EJA e inclusão 2014–2025",
            "F_YOUTH_WORK_AND_TRAINING": "RAIS 2019–2025; Caged e aprendizagem 2020–2025",
            "G_ECONOMY_EPT_AND_COORDINATION": "mudanças 2019–2025; EPT 2023–2025; ponte 2025",
        }[item["macroblockId"]],
        "sourceRefs": [],
        "territorialLenses": [],
        "comparisonRule": (
            "Vale e município selecionado; distribuição dos dez municípios quando a medida não é aditiva; "
            "RS somente sob contrato compatível."
        ),
        "tooltip": "Mostra medida, unidade, período, fonte, lente e cautela do ponto focalizado.",
        "zeroState": "Zero observado é exibido como valor e identificado explicitamente.",
        "absentState": "Ausência, indisponibilidade e não aplicabilidade são estados distintos com motivo.",
        "mobileFallback": "Resumo textual e lista de pontos; nenhuma rolagem horizontal é necessária.",
        "printBehavior": "Controles e camada técnica são omitidos; fontes, períodos e cautelas permanecem.",
    }
    for item in MACROBLOCK_DEFINITIONS
]

LANGUAGE_REPLACEMENTS = {
    "residentes que estudavam fora": "residentes que estudavam em outro município",
    "revisão de rotas": "planejamento e coordenação do transporte",
    "oportunidades de aprendizagem": "eventos ou registros de aprendizagem profissional",
    "transições entre conclusão, EPT e trabalho formal": (
        "indicadores de conclusão, oferta EPT e trabalho formal acompanhados em paralelo"
    ),
    "correspondências e lacunas": "correspondências disponíveis e áreas não cobertas pela ponte",
    "etapa, rede e indicador": "etapa e indicador, com articulação entre as redes responsáveis",
    "sem causalidade": "sem inferir relação de causa e efeito",
    "causalidade": "relação de causa e efeito",
}

BLOCKED_LANGUAGE = [
    {"id": "receiver-municipality", "pattern": r"\bmunic[ií]pio receptor\b"},
    {"id": "origin-destination-corridor", "pattern": r"\bcorredor origem[- ]destino\b"},
    {"id": "inferred-route", "pattern": r"\brota inferida\b"},
    {"id": "pnate-2026-executed", "pattern": r"\bPNATE executad[oa] em 2026\b"},
    {"id": "apprentice-opportunity", "pattern": r"\b(?:oportunidade|vaga)s? de aprendiz\b"},
    {"id": "dropout-for-work", "pattern": r"\balunos? abandonam? para trabalhar\b"},
    {"id": "courses-missing", "pattern": r"\bfaltam cursos\b"},
    {"id": "course-demand", "pattern": r"\bdemanda por curso\b"},
    {"id": "professional-deficit", "pattern": r"\bd[eé]ficit de profissionais\b"},
    {"id": "future-professions", "pattern": r"\bprofiss[oõ]es do futuro\b"},
    {"id": "municipal-ranking", "pattern": r"\branking municipal\b"},
    {"id": "vale-trajectory-rate", "pattern": r"\btaxa do Vale\b"},
    {"id": "causality-jargon", "pattern": r"\bcausalidade\b"},
    {"id": "pne-internal-token", "pattern": r"\bPNE_[0-9]+\b"},
    {"id": "pme-internal-token", "pattern": r"\bPME_[A-Za-z0-9_]+\b"},
]


class Job5IValidationError(ValueError):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _rows(path: Path) -> list[dict[str, str]]:
    with gzip.open(path, "rt", encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def _clean(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, str) and value.strip().lower() in {"", "null", "nan", "none"}:
        return None
    return value


def _float(value: Any) -> float | None:
    value = _clean(value)
    if value is None:
        return None
    number = float(value)
    if not math.isfinite(number):
        return None
    return number


def _int(value: Any) -> int | None:
    number = _float(value)
    if number is None:
        return None
    if not number.is_integer():
        raise Job5IValidationError(f"inteiro esperado, recebido {value!r}")
    return int(number)


def _bool(value: Any) -> bool:
    return str(value).strip().lower() == "true"


def _availability(value: float | None, raw_state: Any = None) -> str:
    state = str(_clean(raw_state) or "").strip().lower()
    if state in {"suppressed"}:
        return "suppressed"
    if state in {"not_applicable", "not applicable"}:
        return "not_applicable"
    if state in {"unavailable", "null", "missing", "not_materialized"} or value is None:
        return "unavailable"
    if value == 0:
        return "observed_zero"
    return "observed"


def _normalize_stage(value: Any) -> str:
    stage = str(_clean(value) or "")
    return {
        "medio": "high_school",
        "pre_escola": "pre_school_age_4_5",
        "pre-school": "pre_school_age_4_5",
        "educacao_infantil": "early_childhood",
        "infantil:creche": "creche_age_0_3",
        "infantil:pre-escola": "pre_school_age_4_5",
        "anos_iniciais": "fundamental_initial_years",
        "anos_finais": "fundamental_final_years",
        "all_schools": "all",
        "all_students": "all",
    }.get(stage, stage)


def _normalize_unit(unit: Any, metric: str = "") -> str:
    raw = str(_clean(unit) or "count")
    if raw == "students":
        return "beneficiaries"
    if raw == "count":
        if "class" in metric or metric in {"turmas", "school_classes", "rural_classes"}:
            return "classes"
        if "docent" in metric or "teacher" in metric:
            return "teachers"
        if "teaching_units" in metric:
            return "teaching_units"
    return {
        "matriculas": "enrollments",
        "school_enrollments": "enrollments",
        "active_bonds_count": "active_bonds",
        "people": "persons",
    }.get(raw, raw)


def _correct_language(text: str) -> str:
    result = text
    for old, new in LANGUAGE_REPLACEMENTS.items():
        result = re.sub(re.escape(old), new, result, flags=re.IGNORECASE)
    return result


def _entity_id(row: Mapping[str, Any]) -> str:
    explicit = str(_clean(row.get("entity_id")) or "")
    if explicit:
        return explicit
    scope = str(_clean(row.get("entity_scope")) or "municipality")
    if scope == "region":
        return REGION_ID
    if scope == "state":
        return "STATE_RS"
    return str(_clean(row.get("municipality_ibge_code")) or "")


def _point(
    *,
    year: int,
    value: float | None,
    unit: str,
    source_ref: str,
    territorial_lens: str,
    aggregation_rule: str,
    raw_state: Any = None,
    caution: str = "none",
    numerator: float | None = None,
    denominator: float | None = None,
    raw_ratio: float | None = None,
) -> dict[str, Any]:
    state = _availability(value, raw_state)
    display_value = value if state in {"observed", "observed_zero"} else None
    scale_contract = "absolute"
    display_unit = unit
    if unit == "percent":
        scale_contract = "ratio_0_1_to_percent_0_100" if raw_ratio is not None else "source_percent_0_100"
        if raw_ratio is None and display_value is not None:
            raw_ratio = display_value / 100
        if display_value is not None and numerator is None and denominator is None:
            # A fonte publicou a taxa, mas não os eventos subjacentes. Estes
            # componentes descrevem a escala (pontos percentuais / 100) sem
            # inventar contagens que não foram materializadas.
            numerator = display_value
            denominator = 100.0
    elif unit == "ratio":
        scale_contract = "ratio_0_1"
        raw_ratio = display_value if raw_ratio is None else raw_ratio
    return {
        "year": year,
        "value": display_value,
        "availabilityState": state,
        "unit": unit,
        "sourceRef": source_ref,
        "territorialLens": territorial_lens,
        "breakOrCautionState": caution,
        "aggregationRule": aggregation_rule,
        "numerator": numerator,
        "denominator": denominator,
        "rawRatio": raw_ratio,
        "displayValue": display_value,
        "displayUnit": display_unit,
        "scaleContract": scale_contract,
    }


@dataclass
class BundleBuilder:
    municipalities: list[dict[str, str]]
    families: list[dict[str, Any]]
    macroblocks: list[dict[str, Any]]
    facts: list[dict[str, Any]] = field(default_factory=list)
    series: list[dict[str, Any]] = field(default_factory=list)
    distributions: list[dict[str, Any]] = field(default_factory=list)
    occupation_evidence: list[dict[str, Any]] = field(default_factory=list)
    bridge_summaries: list[dict[str, Any]] = field(default_factory=list)
    bridge_correspondences: list[dict[str, Any]] = field(default_factory=list)
    technical_shift_share: list[dict[str, Any]] = field(default_factory=list)
    summary_blueprint: list[dict[str, Any]] = field(default_factory=list)
    _fact_ids: set[str] = field(default_factory=set)
    _series_ids: set[str] = field(default_factory=set)
    _distribution_ids: set[str] = field(default_factory=set)

    def add_fact(
        self,
        *,
        fact_id: str,
        family_id: str,
        entity_id: str,
        metric_id: str,
        label: str,
        value: float | None,
        unit: str,
        period: str,
        source_ref: str,
        territorial_lens: str,
        aggregation_rule: str,
        comparison_role: str,
        raw_state: Any = None,
        numerator: float | None = None,
        denominator: float | None = None,
        raw_ratio: float | None = None,
        scale_contract: str | None = None,
        age_group: str = "",
        population_scope: str = "",
        educational_stage: str = "",
        offer_universe: str = "",
        note: str = "",
    ) -> str:
        if fact_id in self._fact_ids:
            raise Job5IValidationError(f"factId duplicado: {fact_id}")
        self._fact_ids.add(fact_id)
        state = _availability(value, raw_state)
        display_value = value if state in {"observed", "observed_zero"} else None
        display_unit = unit
        resolved_scale = scale_contract or "absolute"
        if unit == "percent":
            if raw_ratio is None and display_value is not None:
                raw_ratio = display_value / 100
            if display_value is not None and numerator is None and denominator is None:
                numerator = display_value
                denominator = 100.0
            resolved_scale = scale_contract or "source_percent_0_100"
        elif unit == "ratio":
            raw_ratio = display_value if raw_ratio is None else raw_ratio
            resolved_scale = scale_contract or "ratio_0_1"
        self.facts.append(
            {
                "factId": fact_id,
                "storyFamilyId": family_id,
                "entityId": entity_id,
                "metricId": metric_id,
                "label": label,
                "value": display_value,
                "availabilityState": state,
                "unit": unit,
                "numerator": numerator,
                "denominator": denominator,
                "rawRatio": raw_ratio,
                "displayValue": display_value,
                "displayUnit": display_unit,
                "scaleContract": resolved_scale,
                "period": period,
                "sourceRef": source_ref,
                "territorialLens": territorial_lens,
                "aggregationRule": aggregation_rule,
                "comparisonRole": comparison_role,
                "ageGroup": age_group,
                "populationScope": population_scope,
                "educationalStage": educational_stage,
                "offerUniverse": offer_universe,
                "networkScope": NETWORK_SCOPE,
                "note": note,
            }
        )
        return fact_id

    def add_series(
        self,
        *,
        series_id: str,
        family_id: str,
        entity_id: str,
        metric_id: str,
        title: str,
        unit: str,
        territorial_lens: str,
        temporal_nature: str,
        points: Sequence[dict[str, Any]],
        age_group: str = "",
        population_scope: str = "",
        educational_stage: str = "",
        offer_universe: str = "",
    ) -> str:
        if series_id in self._series_ids:
            raise Job5IValidationError(f"seriesId duplicado: {series_id}")
        if not points:
            return series_id
        self._series_ids.add(series_id)
        ordered = sorted(points, key=lambda point: point["year"])
        self.series.append(
            {
                "seriesId": series_id,
                "storyFamilyId": family_id,
                "entityId": entity_id,
                "metricId": metric_id,
                "title": title,
                "unit": unit,
                "period": f"{ordered[0]['year']}–{ordered[-1]['year']}",
                "territorialLens": territorial_lens,
                "networkScope": NETWORK_SCOPE,
                "ageGroup": age_group,
                "populationScope": population_scope,
                "educationalStage": educational_stage,
                "offerUniverse": offer_universe,
                "temporalNature": temporal_nature,
                "points": ordered,
            }
        )
        return series_id

    def add_distribution(self, distribution: dict[str, Any]) -> None:
        distribution_id = distribution["distributionId"]
        if distribution_id in self._distribution_ids:
            raise Job5IValidationError(f"distributionId duplicado: {distribution_id}")
        self._distribution_ids.add(distribution_id)
        self.distributions.append(distribution)


def _load_municipalities() -> list[dict[str, str]]:
    regions = _json(REPO_ROOT / "config" / "regions" / "rs.json")
    region = next(item for item in regions["regions"] if item["slug"] == "vale-do-sinos")
    codes = list(region["municipalityIbgeCodes"])
    canonical = _json(REPO_ROOT / "config" / "municipalities" / "rs.json")["municipalities"]
    by_code = {item["ibgeCode"]: item for item in canonical}
    if len(codes) != 10 or len(set(codes)) != 10:
        raise Job5IValidationError("o recorte canônico do Vale deve conter dez códigos únicos")
    municipalities = []
    for code in codes:
        if not re.fullmatch(r"[0-9]{7}", code):
            raise Job5IValidationError(f"código IBGE textual inválido: {code!r}")
        item = by_code[code]
        municipalities.append(
            {
                "ibgeCode": code,
                "name": item["name"],
                "slug": item["slug"],
                "stateCode": "RS",
            }
        )
    return municipalities


def _load_families() -> list[dict[str, Any]]:
    catalog = _json(JOB5H_ROOT / "CATALOGO_EDITORIAL_MAXIMO_JOB5H.json")
    families = []
    materialized_inputs = {
        "D1_COHORT_OFFER_CAPACITY": [
            "enrollments_by_stage",
            "schools",
            "classes",
            "full_time",
            "mechanical_pressure_marker",
        ],
        "D1_TRAJECTORY_CONDITIONS": [
            "municipal_trajectory",
            "municipal_distributions",
            "classes",
            "teachers",
            "full_time",
            "teacher_adequacy",
            "teacher_regularity",
            "school_infrastructure",
        ],
        "D1_MOBILITY_HIGH_SCHOOL_OFFER": ["mobility_2022_snapshot", "high_school_offer"],
        "D1_RURALITY_PNATE_PLANNING": ["rural_offer_series", "pnate_stages"],
        "D1_SPECIAL_AEE_TERRITORY": ["special_education_series", "aee_school_series"],
        "D1_ADULT_SCHOOLING_EJA": [
            "adult_schooling_counts",
            "adult_schooling_2022_composition",
            "eja_stage_series",
            "eja_integrated_ept_series",
        ],
        "D2_YOUTH_WORK_15_17": ["rais_youth_stock", "caged_safe_flow", "high_school_parallel_series"],
        "D2_YOUTH_WORK_18_24": ["rais_youth_stock", "caged_safe_flow", "ept_parallel_series"],
        "D2_APPRENTICESHIP": ["apprenticeship_events", "youth_admission_events", "apprenticeship_ratio"],
        "D2_OCCUPATIONS_SECTORS": ["occupation_endpoints", "sector_endpoints"],
        "D2_EPT_TERRITORIAL_OFFER": ["ept_series", "municipal_ept_participation"],
        "D2_SECTOR_TRANSFORMATION_SHIFT_SHARE": ["technical_shift_share"],
        "D2_NORMATIVE_WORK_EDUCATION_BRIDGE": ["bridge_coverage", "bridge_correspondences"],
    }
    ui_source_refs = {
        "D1_COHORT_OFFER_CAPACITY": ["job5gar_early_childhood", "job5gar_pressure", "job5gd_offer", "job5gar_conditions"],
        "D1_TRAJECTORY_CONDITIONS": ["job5gar_trajectory", "job5gar_staffing", "job5gar_conditions"],
        "D1_MOBILITY_HIGH_SCHOOL_OFFER": ["job5gd_mobility", "job5gd_offer"],
        "D1_RURALITY_PNATE_PLANNING": ["job5gbr_rural", "job5gd_pnate"],
        "D1_SPECIAL_AEE_TERRITORY": ["job5gbr_special_aee"],
        "D1_ADULT_SCHOOLING_EJA": ["job5gbr_adult_schooling", "job5gbr_eja_distribution", "job5gbr_eja_history", "job5gbr_eja_integrated_ept"],
        "D2_YOUTH_WORK_15_17": ["job5gcr_rais_youth", "job5gcr_caged_safe", "job5gcr_work_education"],
        "D2_YOUTH_WORK_18_24": ["job5gcr_rais_youth", "job5gcr_caged_safe", "job5gcr_ept_offer"],
        "D2_APPRENTICESHIP": ["job5gcr_apprenticeship"],
        "D2_OCCUPATIONS_SECTORS": ["job5gcr_occupation_endpoints", "job5gcr_sector_endpoints"],
        "D2_EPT_TERRITORIAL_OFFER": ["job5gcr_ept_offer"],
        "D2_SECTOR_TRANSFORMATION_SHIFT_SHARE": ["job5gcr_shift_share"],
        "D2_NORMATIVE_WORK_EDUCATION_BRIDGE": ["job5gcr_bridge", "job5gcr_ept_offer"],
    }
    for source in catalog["storyFamilies"]:
        family_id = source["story_family_id"]
        links = source.get("canonical_pne_goal_links") or source.get("pne_links") or []
        visible_refs = sorted(
            {
                link["legal_goal_ref"]
                for link in links
                if re.fullmatch(r"[0-9]+\.[a-z]", str(link.get("legal_goal_ref", "")))
                and link.get("link_type") != "no_valid_link"
            }
        )
        families.append(
            {
                "storyFamilyId": family_id,
                "directionId": source["direction_id"],
                "macroblockId": source["macroblock_id"],
                "layer": source["layer"],
                "title": _correct_language(source["internal_title"]),
                "summary": _correct_language(source["internal_summary"]),
                "regionalQuestion": _correct_language(source["regional_question"]),
                "municipalQuestion": _correct_language(source["municipal_question"]),
                "planningQuestion": _correct_language(source["planning_question"]),
                "primaryVisual": source["recommended_primary_visual"],
                "sourceRefs": ui_source_refs[family_id],
                "territorialLenses": sorted(set(source["territorial_lenses"])),
                "networkScope": NETWORK_SCOPE,
                "materializedInputs": materialized_inputs[family_id],
                "visiblePneGoalRefs": visible_refs,
                "hiddenPneLinkJustifications": [],
                "pmeGoalRefs": [],
            }
        )
    return families


def _macroblocks() -> list[dict[str, Any]]:
    return [
        {
            **item,
            "visualContractId": f"visual-{item['macroblockId'].lower().replace('_', '-')}",
        }
        for item in MACROBLOCK_DEFINITIONS
    ]


def _series_id(family_id: str, entity_id: str, metric: str, stage: str = "", age: str = "") -> str:
    parts = [family_id, entity_id, metric, stage, age]
    return ".".join(part for part in parts if part)


def _add_grouped_series(
    builder: BundleBuilder,
    *,
    rows: Iterable[Mapping[str, Any]],
    family_id: str,
    source_ref: str,
    metric_field: str,
    value_field: str,
    title_by_metric: Mapping[str, str],
    unit_field: str | None = "unit",
    fixed_unit: str | None = None,
    state_field: str | None = "value_status",
    stage_field: str | None = "stage",
    age_field: str | None = None,
    lens_field: str | None = "territorial_lens",
    fixed_lens: str | None = None,
    aggregation_rule: str = "source_contract",
    temporal_nature: str = "observed_series",
    caution_years: set[int] | None = None,
    population_scope: str = "",
    offer_universe: str = "",
) -> None:
    grouped: dict[tuple[str, str, str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        entity = _entity_id(row)
        metric = str(_clean(row.get(metric_field)) or "")
        stage = _normalize_stage(row.get(stage_field)) if stage_field else ""
        age = str(_clean(row.get(age_field)) or "") if age_field else ""
        if entity and metric:
            grouped[(entity, metric, stage, age)].append(row)
    for (entity, metric, stage, age), items in sorted(grouped.items()):
        points = []
        resolved_unit = fixed_unit
        resolved_lens = fixed_lens
        for row in sorted(items, key=lambda item: int(item.get("year") or item.get("exercise_year"))):
            year = int(row.get("year") or row.get("exercise_year"))
            value = _float(row.get(value_field))
            unit = fixed_unit or _normalize_unit(row.get(unit_field) if unit_field else None, metric)
            lens = fixed_lens or str(_clean(row.get(lens_field)) or "school_location")
            resolved_unit = unit
            resolved_lens = lens
            caution = "continuity_caution" if caution_years and year in caution_years else "none"
            points.append(
                _point(
                    year=year,
                    value=value,
                    unit=unit,
                    source_ref=source_ref,
                    territorial_lens=lens,
                    aggregation_rule=aggregation_rule,
                    raw_state=row.get(state_field) if state_field else None,
                    caution=caution,
                )
            )
        builder.add_series(
            series_id=_series_id(family_id, entity, metric, stage, age),
            family_id=family_id,
            entity_id=entity,
            metric_id=metric,
            title=title_by_metric.get(metric, metric.replace("_", " ").capitalize()),
            unit=resolved_unit or "count",
            territorial_lens=resolved_lens or "school_location",
            temporal_nature=temporal_nature,
            points=points,
            age_group=age,
            population_scope=population_scope,
            educational_stage=stage,
            offer_universe=offer_universe,
        )


def _build_demography_offer(builder: BundleBuilder, vale_codes: set[str]) -> None:
    family_id = "D1_COHORT_OFFER_CAPACITY"
    early = _rows(JOB5GAR_ROOT / "PAINEL_EDUCACAO_INFANTIL_OBSERVADA_V1.csv.gz")
    early = [
        row
        for row in early
        if row["municipality_ibge_code"] in vale_codes
        and (
            (
                row["stage"] == "educacao_infantil"
                and row["metric"] in {"school_enrollments", "schools", "school_classes"}
            )
            or (
                row["stage"] in {"creche_age_0_3", "pre_school_age_4_5"}
                and row["metric"] == "resident_population"
            )
        )
    ]
    regional: dict[tuple[str, str, str], float] = defaultdict(float)
    regional_template: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in early:
        key = (row["year"], row["stage"], row["metric"])
        value = _float(row["value"])
        if value is not None:
            regional[key] += value
        regional_template[key] = row
    for (year, stage, metric), value in regional.items():
        template = regional_template[(year, stage, metric)]
        early.append(
            {
                **template,
                "municipality_ibge_code": "",
                "municipality_name": REGION_NAME,
                "entity_scope": "region",
                "entity_id": REGION_ID,
                "value": str(value),
                "value_status": "observed",
                "aggregation_rule": "sum_of_ten_municipalities",
            }
        )
    _add_grouped_series(
        builder,
        rows=early,
        family_id=family_id,
        source_ref="job5gar_early_childhood",
        metric_field="metric",
        value_field="value",
        title_by_metric={
            "school_enrollments": "Matrículas localizadas",
            "schools": "Escolas com oferta localizada",
            "school_classes": "Turmas",
            "resident_population": "População residente da coorte",
        },
        state_field="value_status",
        aggregation_rule="municipal observation; regional sum of ten municipalities",
        offer_universe="all_networks_school_location",
    )

    offer = _rows(JOB5GD_ROOT / "PAINEL_ESTRUTURA_TERRITORIAL_OFERTA_JOB5GD_V1.csv.gz")
    offer = [
        row
        for row in offer
        if _entity_id(row) in vale_codes | {REGION_ID}
        and (
            (
                row["offer_domain"] == "general_offer"
                and row["metric"] in {"located_enrollments", "schools"}
                and row["stage"] in {"pre_escola", "fundamental", "medio", "all"}
            )
            or (
                row["offer_domain"] == "staffing_and_classes"
                and row["metric"] in {"classes", "reported_teaching_units"}
                and row["stage"] in {"fundamental", "medio"}
            )
        )
    ]
    _add_grouped_series(
        builder,
        rows=offer,
        family_id=family_id,
        source_ref="job5gd_offer",
        metric_field="metric",
        value_field="value",
        title_by_metric={
            "located_enrollments": "Matrículas localizadas",
            "schools": "Escolas",
            "classes": "Turmas",
            "reported_teaching_units": "Unidades de docência informadas",
        },
        state_field="availability_state",
        aggregation_rule="source regional total or municipal observation",
        offer_universe="all_networks_school_location",
    )

    for entity in sorted(vale_codes | {REGION_ID}):
        builder.add_fact(
            fact_id=f"{family_id}.{entity}.creche_located_enrollments.unavailable",
            family_id=family_id,
            entity_id=entity,
            metric_id="creche_located_enrollments",
            label="Matrículas de creche localizadas por faixa 0–3",
            value=None,
            unit="enrollments",
            period="2014–2025",
            source_ref="job5gar_early_childhood",
            territorial_lens="school_location",
            aggregation_rule="not materialized separately by the frozen source panel",
            comparison_role="explicit_unavailability",
            raw_state="unavailable",
            educational_stage="creche_age_0_3",
            offer_universe="all_networks_school_location",
            note="A fonte congelada materializa a população da coorte e a oferta total da educação infantil, mas não matrículas localizadas de creche isoladas.",
        )

    pressure = _rows(
        JOB5GAR_ROOT / "PAINEL_PRESSAO_MECANICA_COORTES_AUDITADO_V1_1.csv.gz"
    )
    for row in pressure:
        entity = _entity_id(row)
        if entity not in vale_codes | {REGION_ID} or str(row["target_year"]) != "2030":
            continue
        ratio = _float(row.get("recomputed_ratio"))
        builder.add_fact(
            fact_id=f"{family_id}.{entity}.mechanical_pressure.{_normalize_stage(row['stage'])}.2030",
            family_id=family_id,
            entity_id=entity,
            metric_id="mechanical_cohort_to_2025_enrollment_ratio",
            label="Razão mecânica coorte/base observada — marcador não preditivo",
            value=ratio,
            unit="ratio",
            period="referência 2025; horizonte mecânico 2030",
            source_ref="job5gar_pressure",
            territorial_lens="resident_population",
            aggregation_rule="audited mechanical cohort divided by 2025 located enrollments",
            comparison_role="complementary_marker_not_forecast",
            raw_state=row.get("availability_state"),
            numerator=_float(row.get("audited_mechanical_cohort_size")),
            denominator=_float(row.get("baseline_enrollments_2025")),
            raw_ratio=ratio,
            scale_contract="ratio_unbounded_no_percent_symbol",
            educational_stage=_normalize_stage(row["stage"]),
            population_scope="resident_age_cohort",
            offer_universe="school_location_enrollments_baseline",
            note="Não é previsão, demanda, cobertura nem capacidade.",
        )


def _build_trajectory_conditions(builder: BundleBuilder, vale_codes: set[str]) -> None:
    family_id = "D1_TRAJECTORY_CONDITIONS"
    trajectory = _rows(
        JOB5GAR_ROOT / "PAINEL_TRAJETORIA_OFICIAL_DESCRITIVA_V1_1.csv.gz"
    )
    trajectory = [
        row
        for row in trajectory
        if row["municipality_ibge_code"] in vale_codes
        and row["metric"] in {
            "approval_rate_percent",
            "failure_rate_percent",
            "dropout_rate_percent",
            "age_grade_distortion_rate_percent",
        }
    ]
    _add_grouped_series(
        builder,
        rows=trajectory,
        family_id=family_id,
        source_ref="job5gar_trajectory",
        metric_field="metric",
        value_field="value",
        title_by_metric={
            "approval_rate_percent": "Aprovação",
            "failure_rate_percent": "Reprovação",
            "dropout_rate_percent": "Abandono",
            "age_grade_distortion_rate_percent": "Distorção idade-série",
        },
        fixed_unit="percent",
        state_field="value_status",
        caution_years={2020, 2021},
        aggregation_rule="official municipal rate; never recomposed as a Vale rate",
        offer_universe="all_networks_school_location",
    )

    grouped: dict[tuple[str, str, int], list[dict[str, str]]] = defaultdict(list)
    for row in trajectory:
        grouped[(row["stage"], row["metric"], int(row["year"]))].append(row)
    for (raw_stage, metric, year), items in sorted(grouped.items()):
        by_code = {row["municipality_ibge_code"]: row for row in items}
        if set(by_code) != vale_codes:
            raise Job5IValidationError(
                f"distribuição de trajetória incompleta: {raw_stage}/{metric}/{year}"
            )
        first = items[0]
        stage = _normalize_stage(raw_stage)
        builder.add_distribution(
            {
                "distributionId": f"trajectory.{stage}.{metric}.{year}",
                "storyFamilyId": family_id,
                "metricId": metric,
                "educationalStage": stage,
                "year": year,
                "unit": "percent",
                "label": "Distribuição dos dez municípios",
                "municipalValues": [
                    {
                        "municipalityIbgeCode": code,
                        "value": _float(by_code[code]["value"]),
                        "availabilityState": _availability(
                            _float(by_code[code]["value"]), by_code[code]["value_status"]
                        ),
                        "numerator": _float(by_code[code]["value"]),
                        "denominator": 100.0,
                        "rawRatio": (
                            _float(by_code[code]["value"]) / 100
                            if _float(by_code[code]["value"]) is not None
                            else None
                        ),
                        "displayValue": _float(by_code[code]["value"]),
                        "displayUnit": "percent",
                        "scaleContract": "source_percent_0_100",
                    }
                    for code in sorted(vale_codes)
                ],
                "valeMunicipalMedian": _float(first["vale_municipal_distribution_median"]),
                "valeMedianLabel": "Mediana dos dez municípios",
                "rsMunicipalDistribution": {
                    "minimum": _float(first["rs_minimum"]),
                    "quartile1": _float(first["rs_quartile_1"]),
                    "median": _float(first["rs_municipal_distribution_median"]),
                    "quartile3": _float(first["rs_quartile_3"]),
                    "maximum": _float(first["rs_maximum"]),
                    "municipalityCount": _int(first["rs_municipality_count"]),
                    "label": "Distribuição municipal do RS",
                },
                "sourceRef": "job5gar_trajectory",
                "territorialLens": "school_location",
                "comparisonRule": "distribuições municipais; nenhuma taxa regional é calculada",
                "breakOrCautionState": (
                    "continuity_caution" if year in {2020, 2021} else "none"
                ),
            }
        )

    conditions = _rows(
        JOB5GAR_ROOT / "PAINEL_CONDICOES_ESCOLARES_TOTAL_V1_1.csv.gz"
    )
    selected_condition_metrics = {
        "percentual_tempo_integral",
        "teacher_adequacy_percent",
        "schools_with_broadband_percent",
        "schools_with_internet_percent",
        "regularidade_docente_faixa_ate_2",
        "regularidade_docente_faixa_2_a_3",
        "regularidade_docente_faixa_3_a_4",
        "regularidade_docente_faixa_4_a_5",
    }
    conditions = [
        row
        for row in conditions
        if row["municipality_ibge_code"] in vale_codes
        and row["metric"] in selected_condition_metrics
        and _bool(row["visual_row_eligible"])
        and row["stage"] in {"fundamental", "medio", "all_schools"}
    ]
    _add_grouped_series(
        builder,
        rows=conditions,
        family_id=family_id,
        source_ref="job5gar_conditions",
        metric_field="metric",
        value_field="value",
        title_by_metric={
            "percentual_tempo_integral": "Matrículas em tempo integral",
            "teacher_adequacy_percent": "Adequação docente",
            "schools_with_broadband_percent": "Escolas com banda larga",
            "schools_with_internet_percent": "Escolas com internet",
            "regularidade_docente_faixa_ate_2": "Regularidade docente — faixa até 2",
            "regularidade_docente_faixa_2_a_3": "Regularidade docente — faixa 2 a 3",
            "regularidade_docente_faixa_3_a_4": "Regularidade docente — faixa 3 a 4",
            "regularidade_docente_faixa_4_a_5": "Regularidade docente — faixa 4 a 5",
        },
        state_field="value_status",
        aggregation_rule="municipal observation; distribution comparison only",
        offer_universe="all_networks_school_location",
    )

    staffing = _rows(
        JOB5GAR_ROOT / "PAINEL_DOCENTES_TURMAS_JORNADA_V1_1.csv.gz"
    )
    staffing = [
        row
        for row in staffing
        if row["municipality_ibge_code"] in vale_codes
        and row["metric"] in {"turmas", "docentes", "matriculas_tempo_integral"}
        and row["stage"] in {"fundamental", "medio"}
    ]
    _add_grouped_series(
        builder,
        rows=staffing,
        family_id=family_id,
        source_ref="job5gar_staffing",
        metric_field="metric",
        value_field="value",
        title_by_metric={
            "turmas": "Turmas",
            "docentes": "Docentes ou unidades de docência",
            "matriculas_tempo_integral": "Matrículas em tempo integral",
        },
        state_field="value_status",
        aggregation_rule="municipal total across all administrative dependencies",
        offer_universe="all_networks_school_location",
    )


def _build_mobility(builder: BundleBuilder, vale_codes: set[str]) -> None:
    family_id = "D1_MOBILITY_HIGH_SCHOOL_OFFER"
    rows = _rows(
        JOB5GD_ROOT / "PAINEL_MOBILIDADE_EDUCACIONAL_POR_ETAPA_JOB5GD_V1.csv.gz"
    )
    rows = [row for row in rows if _entity_id(row) in vale_codes | {REGION_ID, "STATE_RS"}]
    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[(_entity_id(row), _normalize_stage(row["stage"]))].append(row)
    for (entity, stage), items in sorted(grouped.items()):
        row = items[0]
        ratio = _float(row["outside_share_percent"])
        point = _point(
            year=2022,
            value=ratio,
            unit="percent",
            source_ref="job5gd_mobility",
            territorial_lens="student_residence",
            aggregation_rule="residents studying in another municipality divided by residents studying",
            raw_state=row["value_status"],
            caution="snapshot_only",
            numerator=_float(row["numerator"]),
            denominator=_float(row["denominator"]),
            raw_ratio=(ratio / 100 if ratio is not None else None),
        )
        builder.add_series(
            series_id=_series_id(family_id, entity, "other_municipality_share", stage),
            family_id=family_id,
            entity_id=entity,
            metric_id="residents_studying_other_municipality_share",
            title="Residentes que estudavam em outro município",
            unit="percent",
            territorial_lens="student_residence",
            temporal_nature="single_year_snapshot",
            points=[point],
            population_scope="residents_who_studied",
            educational_stage=stage,
            offer_universe="residence_reported_study_location",
        )


def _build_rurality_transport(builder: BundleBuilder, vale_codes: set[str]) -> None:
    family_id = "D1_RURALITY_PNATE_PLANNING"
    rural = _rows(
        JOB5GBR_ROOT / "PAINEL_EDUCACAO_RURAL_TERRITORIO_V1_1.csv.gz"
    )
    rural = [
        row
        for row in rural
        if _entity_id(row) in vale_codes | {REGION_ID}
        and row["stage"] in {"all", "high_school"}
        and row["metric"] in {"rural_enrollments", "rural_schools", "rural_classes"}
    ]
    _add_grouped_series(
        builder,
        rows=rural,
        family_id=family_id,
        source_ref="job5gbr_rural",
        metric_field="metric",
        value_field="value",
        title_by_metric={
            "rural_enrollments": "Matrículas rurais localizadas",
            "rural_schools": "Escolas rurais",
            "rural_classes": "Turmas rurais",
        },
        state_field="value_status",
        aggregation_rule="source regional total or municipal observation; stages not stacked",
        offer_universe="rural_school_location_all_networks",
    )

    pnate = _rows(
        JOB5GD_ROOT / "PAINEL_TRANSPORTE_ESCOLAR_PNATE_JOB5GD_V1.csv.gz"
    )
    pnate = [
        row
        for row in pnate
        if _entity_id(row) in vale_codes | {REGION_ID}
        and row["metric"]
        in {
            "pnate_adjusted_forecast",
            "pnate_authorized_after_discount",
            "pnate_beneficiary_students",
            "pnate_executed_amount",
            "school_transport_students_observed",
        }
    ]
    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in pnate:
        grouped[(_entity_id(row), row["metric"])].append(row)
    title_by_metric = {
        "pnate_adjusted_forecast": "Previsão de planejamento PNATE",
        "pnate_authorized_after_discount": "Valor autorizado após ajustes",
        "pnate_beneficiary_students": "Beneficiários informados para o cálculo",
        "pnate_executed_amount": "Valor executado informado",
        "school_transport_students_observed": "Registros administrativos de transporte escolar",
    }
    for (entity, metric), items in sorted(grouped.items()):
        points = []
        unit = "count"
        for row in sorted(items, key=lambda item: int(item["exercise_year"])):
            year = int(row["exercise_year"])
            value = _float(row["value"])
            unit = _normalize_unit(row["unit"], metric)
            caution = "planning_forecast" if year == 2026 else "none"
            raw_state = row["value_status"]
            if year == 2026 and metric != "pnate_adjusted_forecast":
                value = None
                raw_state = "unavailable"
            points.append(
                _point(
                    year=year,
                    value=value,
                    unit=unit,
                    source_ref="job5gd_pnate",
                    territorial_lens="municipal_executor",
                    aggregation_rule=row["aggregation_rule"],
                    raw_state=raw_state,
                    caution=caution,
                )
            )
        builder.add_series(
            series_id=_series_id(family_id, entity, metric),
            family_id=family_id,
            entity_id=entity,
            metric_id=metric,
            title=title_by_metric[metric],
            unit=unit,
            territorial_lens="municipal_executor",
            temporal_nature="planning_stages",
            points=points,
            population_scope="administrative_program_record",
            offer_universe="pnate_executor_records",
        )


def _build_inclusion_adults(builder: BundleBuilder, vale_codes: set[str]) -> None:
    adult_family = "D1_ADULT_SCHOOLING_EJA"
    adult = _rows(
        JOB5GBR_ROOT / "PAINEL_ESCOLARIDADE_ADULTA_2010_2022_V1_1.csv.gz"
    )
    adult = [row for row in adult if _entity_id(row) in vale_codes | {REGION_ID}]
    grouped_adult: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in adult:
        grouped_adult[(_entity_id(row), row["schooling_category"])].append(row)
    adult_titles = {
        "without_fundamental_completed": "Sem ensino fundamental concluído",
        "fundamental_completed_without_high_school": "Fundamental concluído sem ensino médio",
        "fundamental_completed_or_more": "Fundamental concluído ou mais",
        "high_school_completed_or_more": "Ensino médio concluído ou mais",
    }
    for (entity, category), items in sorted(grouped_adult.items()):
        points = []
        for row in sorted(items, key=lambda item: int(item["year"])):
            points.append(
                _point(
                    year=int(row["year"]),
                    value=_float(row["count_value"]),
                    unit="persons",
                    source_ref="job5gbr_adult_schooling",
                    territorial_lens="resident_population",
                    aggregation_rule=row["aggregation_rule"],
                    raw_state=row["count_value_status"],
                )
            )
        builder.add_series(
            series_id=_series_id(adult_family, entity, category),
            family_id=adult_family,
            entity_id=entity,
            metric_id=category,
            title=adult_titles[category],
            unit="persons",
            territorial_lens="resident_population",
            temporal_nature="observed_endpoints",
            points=points,
            age_group="18_or_more",
            population_scope="resident_population_age_18_or_more",
            offer_universe="not_applicable",
        )
        latest = next((row for row in items if row["year"] == "2022"), None)
        if latest:
            share = _float(latest["share_percent"])
            builder.add_fact(
                fact_id=f"{adult_family}.{entity}.{category}.share.2022",
                family_id=adult_family,
                entity_id=entity,
                metric_id=f"{category}_share",
                label=f"{adult_titles[category]} — composição de 2022",
                value=share,
                unit="percent",
                period="2022",
                source_ref="job5gbr_adult_schooling",
                territorial_lens="resident_population",
                aggregation_rule=latest["aggregation_rule"],
                comparison_role="resident_composition",
                raw_state=latest["share_status"],
                numerator=_float(latest["count_value"]),
                denominator=_float(latest["adult_population_denominator"]),
                raw_ratio=(share / 100 if share is not None else None),
                scale_contract="source_percent_0_100",
                age_group="18_or_more",
                population_scope="resident_population_age_18_or_more",
                note=(
                    "O denominador de 2010 não está disponível para recompor variação intercensitária de participação."
                    if not _bool(latest.get("denominator_2010_available"))
                    else ""
                ),
            )

    distribution = _rows(
        JOB5GBR_ROOT / "PAINEL_EJA_DISTRIBUICAO_2022_V1_1.csv.gz"
    )
    regional_distribution_denominators = {
        (_normalize_stage(row["stage"]), field): _float(row[field])
        for row in distribution
        if _entity_id(row) == REGION_ID
        for field in ("resident_adult_public", "school_location_eja_enrollments")
    }
    for row in distribution:
        entity = _entity_id(row)
        if entity not in vale_codes | {REGION_ID}:
            continue
        stage = _normalize_stage(row["stage"])
        if entity == REGION_ID:
            # A região é o próprio denominador regional. As participações de 100%
            # são tautologias e ficam explicitamente não aplicáveis ao visual.
            for metric in ("share_of_regional_public", "share_of_regional_eja"):
                builder.add_fact(
                    fact_id=f"{adult_family}.{entity}.{metric}.{stage}.2022",
                    family_id=adult_family,
                    entity_id=entity,
                    metric_id=metric,
                    label="Participação regional tautológica suprimida",
                    value=None,
                    unit="percent",
                    period="2022",
                    source_ref="job5gbr_eja_distribution",
                    territorial_lens=(
                        "resident_population" if metric.endswith("public") else "school_location"
                    ),
                    aggregation_rule="not applicable because region equals its own denominator",
                    comparison_role="not_applicable_tautology",
                    raw_state="not_applicable",
                    educational_stage=stage,
                    note="Use o total regional e a distribuição dos dez municípios.",
                )
            continue
        for metric, value_field, lens, numerator_field in (
            (
                "share_of_regional_resident_adult_public",
                "share_of_regional_public_percent",
                "resident_population",
                "resident_adult_public",
            ),
            (
                "share_of_regional_eja_enrollments",
                "share_of_regional_enrollments_percent",
                "school_location",
                "school_location_eja_enrollments",
            ),
        ):
            value = _float(row[value_field])
            builder.add_fact(
                fact_id=f"{adult_family}.{entity}.{metric}.{stage}.2022",
                family_id=adult_family,
                entity_id=entity,
                metric_id=metric,
                label=(
                    "Participação municipal no público residente regional"
                    if lens == "resident_population"
                    else "Participação municipal nas matrículas EJA localizadas no Vale"
                ),
                value=value,
                unit="percent",
                period="2022",
                source_ref="job5gbr_eja_distribution",
                territorial_lens=lens,
                aggregation_rule="municipal numerator divided by compatible regional total",
                comparison_role="municipal_share",
                raw_state=row["value_status"],
                numerator=_float(row[numerator_field]),
                denominator=regional_distribution_denominators[(stage, numerator_field)],
                raw_ratio=(value / 100 if value is not None else None),
                scale_contract="source_percent_0_100",
                educational_stage=stage,
                population_scope=(
                    "resident_adult_public" if lens == "resident_population" else "eja_enrollments"
                ),
            )

    eja = _rows(JOB5GBR_ROOT / "PAINEL_EJA_HISTORICA_2014_2025_V1_1.csv.gz")
    eja = [
        row
        for row in eja
        if _entity_id(row) in vale_codes | {REGION_ID}
        and row["stage"] in {"fundamental", "high_school", "total_context"}
    ]
    _add_grouped_series(
        builder,
        rows=eja,
        family_id=adult_family,
        source_ref="job5gbr_eja_history",
        metric_field="stage",
        value_field="eja_enrollments",
        title_by_metric={
            "fundamental": "EJA fundamental",
            "high_school": "EJA ensino médio",
            "total_context": "EJA — total contextual",
        },
        fixed_unit="enrollments",
        state_field="value_status",
        stage_field="stage",
        caution_years={2020, 2021},
        aggregation_rule="stage-specific located enrollments; stages remain separate",
        offer_universe="eja_school_location_all_networks",
    )

    integrated = _rows(JOB5GBR_ROOT / "PAINEL_EJA_INTEGRADA_EPT_V1_1.csv.gz")
    integrated = [
        row
        for row in integrated
        if _entity_id(row) in vale_codes | {REGION_ID}
        and row["modality"] in {"integrated_total", "technical_integrated"}
    ]
    _add_grouped_series(
        builder,
        rows=integrated,
        family_id=adult_family,
        source_ref="job5gbr_eja_integrated_ept",
        metric_field="modality",
        value_field="integrated_eja_enrollments",
        title_by_metric={
            "integrated_total": "EJA integrada à EPT — total contratado",
            "technical_integrated": "EJA técnica integrada",
        },
        fixed_unit="enrollments",
        state_field="value_status",
        stage_field=None,
        caution_years={2020, 2021},
        aggregation_rule="modality-specific located enrollments; zeros remain observed zeros",
        offer_universe="eja_integrated_ept_school_location",
    )

    special_family = "D1_SPECIAL_AEE_TERRITORY"
    special = _rows(JOB5GBR_ROOT / "PAINEL_EDUCACAO_ESPECIAL_AEE_V1_1.csv.gz")
    special = [
        row
        for row in special
        if _entity_id(row) in vale_codes | {REGION_ID}
        and row["metric"]
        in {
            "special_enrollments",
            "schools_offering_aee",
            "schools_with_aee_resource_room",
            "schools_with_special_enrollment",
        }
        and row["stage"] == "all"
    ]
    _add_grouped_series(
        builder,
        rows=special,
        family_id=special_family,
        source_ref="job5gbr_special_aee",
        metric_field="metric",
        value_field="value",
        title_by_metric={
            "special_enrollments": "Matrículas localizadas da educação especial",
            "schools_offering_aee": "Escolas que informam oferta de AEE",
            "schools_with_aee_resource_room": "Escolas com sala de recursos para AEE",
            "schools_with_special_enrollment": "Escolas com matrícula da educação especial",
        },
        state_field="value_status",
        aggregation_rule="school-location observation; no coverage or access conclusion",
        offer_universe="special_education_school_location_all_networks",
    )


def _build_youth_work(builder: BundleBuilder, vale_codes: set[str]) -> None:
    rais = _rows(JOB5GCR_ROOT / "PAINEL_RAIS_TRABALHO_JUVENIL_V1_1.csv.gz")
    rais = [
        row
        for row in rais
        if _entity_id(row) in vale_codes | {REGION_ID}
        and row["dimension"] == "total"
        and row["dimension_code"] == "ALL"
        and row["age_group"] in {"15_17", "18_24"}
    ]
    for age, family_id in (
        ("15_17", "D2_YOUTH_WORK_15_17"),
        ("18_24", "D2_YOUTH_WORK_18_24"),
    ):
        _add_grouped_series(
            builder,
            rows=[row for row in rais if row["age_group"] == age],
            family_id=family_id,
            source_ref="job5gcr_rais_youth",
            metric_field="dimension",
            value_field="active_bonds",
            title_by_metric={"total": "Vínculos formais ativos — estoque RAIS"},
            fixed_unit="active_bonds",
            state_field="value_status",
            stage_field=None,
            age_field="age_group",
            fixed_lens="workplace",
            aggregation_rule="annual stock of active formal bonds; not unique students",
            population_scope="formal_bonds_youth",
            offer_universe="not_applicable",
        )

    caged = _rows(
        JOB5GCR_ROOT / "PAINEL_CAGED_JUVENIL_AGREGADO_SEGURO_V1.csv.gz"
    )
    caged = [
        row
        for row in caged
        if _entity_id(row) in vale_codes | {REGION_ID}
        and row["time_grain"] == "annual_flow"
        and row["aggregation_scope"] == "all_apprentice_status"
        and row["age_group"] in {"15_17", "18_24"}
    ]
    for age, family_id in (
        ("15_17", "D2_YOUTH_WORK_15_17"),
        ("18_24", "D2_YOUTH_WORK_18_24"),
    ):
        age_rows = [row for row in caged if row["age_group"] == age]
        for value_field, metric, title in (
            ("admissions", "caged_youth_admissions", "Admissões — fluxo Caged"),
            ("balance", "caged_youth_balance", "Saldo de eventos — fluxo Caged"),
        ):
            transformed = [{**row, "metric": metric} for row in age_rows]
            _add_grouped_series(
                builder,
                rows=transformed,
                family_id=family_id,
                source_ref="job5gcr_caged_safe",
                metric_field="metric",
                value_field=value_field,
                title_by_metric={metric: title},
                fixed_unit="adjusted_events",
                state_field=None,
                stage_field=None,
                age_field="age_group",
                fixed_lens="workplace",
                aggregation_rule="annual adjusted events; flow is never merged with RAIS stock",
                population_scope="formal_labor_events_youth",
                offer_universe="not_applicable",
            )

    context = _rows(
        JOB5GCR_ROOT / "PAINEL_TRABALHO_JUVENIL_EDUCACAO_CONTEXTO_V1_1.csv.gz"
    )
    context = [
        row
        for row in context
        if _entity_id(row) in vale_codes
        and row["metric"] in {"education_approval_rate_percent", "education_dropout_rate_percent"}
        and row["education_stage"] == "high_school"
    ]
    _add_grouped_series(
        builder,
        rows=context,
        family_id="D2_YOUTH_WORK_15_17",
        source_ref="job5gcr_work_education",
        metric_field="metric",
        value_field="value",
        title_by_metric={
            "education_approval_rate_percent": "Aprovação no ensino médio — série paralela",
            "education_dropout_rate_percent": "Abandono no ensino médio — série paralela",
        },
        fixed_unit="percent",
        state_field="value_status",
        stage_field="education_stage",
        fixed_lens="school_location",
        caution_years={2020, 2021},
        aggregation_rule="parallel municipal education series; no same-person linkage",
        population_scope="school_trajectory_indicators",
        offer_universe="all_networks_school_location",
    )

    apprenticeship = _rows(
        JOB5GCR_ROOT / "PAINEL_APRENDIZAGEM_PROFISSIONAL_V1_1.csv.gz"
    )
    apprenticeship = [
        row
        for row in apprenticeship
        if _entity_id(row) in vale_codes | {REGION_ID}
        and row["aggregation_scope"] == "all_apprentice_events"
        and row["age_group"] in {"15_17", "18_24"}
        and _bool(row["visual_aggregation_eligible"])
    ]
    transformed = [{**row, "metric": "apprentice_admissions"} for row in apprenticeship]
    _add_grouped_series(
        builder,
        rows=transformed,
        family_id="D2_APPRENTICESHIP",
        source_ref="job5gcr_apprenticeship",
        metric_field="metric",
        value_field="admissions",
        title_by_metric={"apprentice_admissions": "Admissões em aprendizagem profissional"},
        fixed_unit="adjusted_events",
        state_field=None,
        stage_field=None,
        age_field="age_group",
        fixed_lens="workplace",
        aggregation_rule="annual adjusted apprentice admission events; not unique people",
        population_scope="apprenticeship_events",
        offer_universe="not_applicable",
    )
    for row in apprenticeship:
        if row["year"] != "2025":
            continue
        entity = _entity_id(row)
        age = row["age_group"]
        numerator = _float(row["admissions"])
        denominator = _float(row["youth_admissions_same_grain"])
        raw_ratio = _float(row["share_of_youth_admission_events_classified_as_apprentice"])
        display = raw_ratio * 100 if raw_ratio is not None else None
        builder.add_fact(
            fact_id=f"D2_APPRENTICESHIP.{entity}.share.{age}.2025",
            family_id="D2_APPRENTICESHIP",
            entity_id=entity,
            metric_id="apprenticeship_share_of_youth_admission_events",
            label="Parcela dos eventos de admissão classificados como aprendizagem profissional",
            value=display,
            unit="percent",
            period="2025",
            source_ref="job5gcr_apprenticeship",
            territorial_lens="workplace",
            aggregation_rule="apprentice admission events divided by youth admission events at the same grain",
            comparison_role="event_composition",
            raw_state=("observed" if raw_ratio is not None else "unavailable"),
            numerator=numerator,
            denominator=denominator,
            raw_ratio=raw_ratio,
            scale_contract="ratio_0_1_to_percent_0_100",
            age_group=age,
            population_scope="formal_labor_admission_events",
            note="Eventos ou registros de aprendizagem profissional não equivalem a pessoas únicas.",
        )


def _content_digest(row: Mapping[str, Any]) -> str:
    content = "|".join(
        str(_clean(row.get(field)) or "")
        for field in (
            "dimension_label",
            "initial_value",
            "final_value",
            "absolute_change",
            "percent_change",
            "initial_year",
            "final_year",
            "source",
            "territorial_lens",
        )
    )
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _substantive_evidence_key(row: Mapping[str, Any]) -> tuple[float, ...] | tuple[Any, ...]:
    initial = abs(_float(row.get("initial_value")) or 0)
    final = abs(_float(row.get("final_value")) or 0)
    change = abs(_float(row.get("absolute_change")) or 0)
    regional_change = abs(_float(row.get("regional_absolute_change")) or 0)
    contribution = change / regional_change if regional_change > 0 else 0
    observed_years = _float(row.get("observed_year_count")) or 0
    complete = 1 if str(row.get("period_coverage_status", "")).startswith("complete") else 0
    not_small = 0 if _bool(row.get("small_volume_sensitive")) else 1
    eligible = 1 if _bool(row.get("selection_eligible")) else 0
    # O código canônico não participa da seleção. O digest sem código aparece
    # somente depois de todos os critérios substantivos.
    return (
        eligible,
        max(initial, final),
        change,
        contribution,
        observed_years,
        complete,
        not_small,
        _content_digest(row),
    )


def _select_material_changes(rows: Sequence[Mapping[str, Any]], limit_each_direction: int = 8) -> list[Mapping[str, Any]]:
    positive = [row for row in rows if (_float(row.get("absolute_change")) or 0) > 0]
    negative = [row for row in rows if (_float(row.get("absolute_change")) or 0) < 0]
    positive.sort(key=_substantive_evidence_key, reverse=True)
    negative.sort(key=_substantive_evidence_key, reverse=True)
    return positive[:limit_each_direction] + negative[:limit_each_direction]


def _evidence_record(row: Mapping[str, Any], kind: str, selection_role: str) -> dict[str, Any]:
    initial = _float(row["initial_value"])
    final = _float(row["final_value"])
    return {
        "evidenceId": f"{kind}.{_entity_id(row)}.{row['dimension_code']}",
        "entityId": _entity_id(row),
        "kind": kind,
        "dimensionCode": str(row["dimension_code"]),
        "label": str(row["dimension_label"]),
        "initialYear": int(row["initial_year"]),
        "finalYear": int(row["final_year"]),
        "initialValue": initial,
        "finalValue": final,
        "absoluteChange": _float(row["absolute_change"]),
        "relativeChangePercent": _float(row["percent_change"]),
        "relativeChangeState": str(row["change_status"]),
        "observedYearCount": _int(row["observed_year_count"]),
        "volume": max(abs(initial or 0), abs(final or 0)),
        "regionalContributionContext": {
            "regionalInitialValue": _float(row.get("regional_initial_value")),
            "regionalFinalValue": _float(row.get("regional_final_value")),
            "regionalAbsoluteChange": _float(row.get("regional_absolute_change")),
        },
        "coverageState": str(row["period_coverage_status"]),
        "smallVolumeSensitive": _bool(row["small_volume_sensitive"]),
        "selectionRole": selection_role,
        "selectionIsPriorityOrRanking": False,
        "sourceRef": "job5gcr_occupation_endpoints" if kind == "occupation" else "job5gcr_sector_endpoints",
        "territorialLens": "workplace",
        "unit": "active_bonds",
        "temporalNature": "observed_endpoints",
        "points": [
            {
                "year": int(row["initial_year"]),
                "value": initial,
                "availabilityState": _availability(initial, "observed"),
            },
            {
                "year": int(row["final_year"]),
                "value": final,
                "availabilityState": _availability(final, "observed"),
            },
        ],
        "note": "Seleção descritiva de mudanças materiais; não é prioridade nem ranking.",
    }


def _build_economy_ept_bridge(builder: BundleBuilder, vale_codes: set[str]) -> None:
    evidence_family = "D2_OCCUPATIONS_SECTORS"
    for filename, kind in (
        ("PAINEL_OCUPACOES_RAIS_ESTOQUE_V1.csv.gz", "occupation"),
        ("PAINEL_SETORES_RAIS_ESTOQUE_V1.csv.gz", "sector"),
    ):
        rows = _rows(JOB5GCR_ROOT / filename)
        rows = [
            row
            for row in rows
            if _entity_id(row) in vale_codes | {REGION_ID}
            and _bool(row["selection_eligible"])
        ]
        by_entity: dict[str, list[dict[str, str]]] = defaultdict(list)
        for row in rows:
            by_entity[_entity_id(row)].append(row)
        for entity, entity_rows in sorted(by_entity.items()):
            selected = list(_select_material_changes(entity_rows))
            anchor = next(
                (
                    row
                    for row in entity_rows
                    if kind == "occupation" and row["dimension_code"] == "414140"
                ),
                None,
            )
            selected_ids = {id(row) for row in selected}
            for row in selected:
                role = "substantive_selection"
                if anchor is row:
                    role = "substantive_selection_and_reconciliation_anchor"
                builder.occupation_evidence.append(_evidence_record(row, kind, role))
            if anchor is not None and id(anchor) not in selected_ids:
                builder.occupation_evidence.append(
                    _evidence_record(anchor, kind, "reconciliation_anchor_not_headline")
                )

    ept_family = "D2_EPT_TERRITORIAL_OFFER"
    ept = _rows(JOB5GCR_ROOT / "PAINEL_EPT_OFERTA_TOTAL_V1_1.csv.gz")
    ept_totals = [
        row
        for row in ept
        if _entity_id(row) in vale_codes | {REGION_ID}
        and row["grain"] in {"municipality_total", "region_total"}
    ]
    transformed = [{**row, "metric": "technical_enrollments"} for row in ept_totals]
    _add_grouped_series(
        builder,
        rows=transformed,
        family_id=ept_family,
        source_ref="job5gcr_ept_offer",
        metric_field="metric",
        value_field="technical_enrollments",
        title_by_metric={"technical_enrollments": "Matrículas EPT localizadas"},
        fixed_unit="enrollments",
        state_field="availability_status",
        stage_field=None,
        fixed_lens="school_location",
        aggregation_rule="regional total or municipality total; all administrative dependencies",
        offer_universe="technical_education_school_location",
    )
    ept_total_index = {
        (_entity_id(row), int(row["year"])): _float(row["technical_enrollments"])
        for row in ept_totals
    }
    for row in ept_totals:
        year = int(row["year"])
        entity = _entity_id(row)
        if entity == REGION_ID:
            builder.add_fact(
                fact_id=f"{ept_family}.{entity}.municipal_share.{year}",
                family_id=ept_family,
                entity_id=entity,
                metric_id="share_of_regional_technical_enrollments",
                label="Participação regional tautológica suprimida",
                value=None,
                unit="percent",
                period=str(year),
                source_ref="job5gcr_ept_offer",
                territorial_lens="school_location",
                aggregation_rule="not applicable because region equals its own denominator",
                comparison_role="not_applicable_tautology",
                raw_state="not_applicable",
                educational_stage="professional_technical",
                offer_universe="technical_education_school_location",
                note="Use total regional, distribuição dos dez municípios e participação do município selecionado.",
            )
            continue
        numerator = _float(row["technical_enrollments"])
        denominator = _float(row["regional_technical_enrollments"])
        raw_ratio = _float(row["share_of_regional_technical_enrollments"])
        display = raw_ratio * 100 if raw_ratio is not None else None
        builder.add_fact(
            fact_id=f"{ept_family}.{entity}.municipal_share.{year}",
            family_id=ept_family,
            entity_id=entity,
            metric_id="share_of_regional_technical_enrollments",
            label="Participação municipal nas matrículas EPT localizadas no Vale",
            value=display,
            unit="percent",
            period=str(year),
            source_ref="job5gcr_ept_offer",
            territorial_lens="school_location",
            aggregation_rule="municipal located enrollments divided by regional located enrollments",
            comparison_role="municipal_share",
            raw_state=row["availability_status"],
            numerator=numerator,
            denominator=denominator,
            raw_ratio=raw_ratio,
            scale_contract="ratio_0_1_to_percent_0_100",
            educational_stage="professional_technical",
            offer_universe="technical_education_school_location",
        )

    bridge_family = "D2_NORMATIVE_WORK_EDUCATION_BRIDGE"
    dictionary = _json(JOB5GCR_ROOT / "DICIONARIO_PONTE_CBO_CNCT_V1_1.json")
    regional_offer = dictionary["courseOfferScope"]
    state_contract = dictionary["bridgeContractScope"]
    builder.bridge_summaries.append(
        {
            "entityId": REGION_ID,
            "availabilityState": "observed",
            "year": 2025,
            "observedCourses": regional_offer["observedCourses"],
            "mappedCourses": regional_offer["mappedCourses"],
            "unmappedCourses": regional_offer["unmappedCourses"],
            "mappedEnrollments": regional_offer["mappedEnrollments"],
            "unmappedEnrollments": regional_offer["unmappedEnrollments"],
            "correspondenceCount": state_contract["courseOccupationSubgroupPairs"],
            "stateContractCoverage": {
                "processedCourses": state_contract["processedCourses"],
                "mappedCourses": state_contract["mappedCourses"],
                "unmappedCourses": state_contract["unmappedCourses"],
            },
            "observedValeOfferCoverage": {
                "observedCourses": regional_offer["observedCourses"],
                "mappedCourses": regional_offer["mappedCourses"],
                "unmappedCourses": regional_offer["unmappedCourses"],
            },
            "additiveAcrossBridgeRows": False,
            "samePersonLink": False,
            "causalLink": False,
            "sourceRef": "job5gcr_bridge",
            "territorialLens": "school_location",
            "note": "Matrículas são deduplicadas por escola e curso antes da cobertura; nunca somadas por correspondência.",
        }
    )

    bridge_rows = _rows(
        JOB5GCR_ROOT / "PAINEL_PONTE_CBO_CNCT_AUDITADA_V1_1.csv.gz"
    )
    by_entity_bridge: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in bridge_rows:
        by_entity_bridge[_entity_id(row)].append(row)
        builder.bridge_correspondences.append(
            {
                "correspondenceId": hashlib.sha256(
                    "|".join(
                        [
                            row["school_code"],
                            row["course_code"],
                            row["occupation_subgroup_code"],
                            row["bridge_status"],
                        ]
                    ).encode("utf-8")
                ).hexdigest()[:20],
                "sourceMunicipalityIbgeCode": row["municipality_ibge_code"],
                "courseCode": row["course_code"],
                "courseName": row["course_name"],
                "technologicalAxisCode": row["technological_axis_code"],
                "technologicalAxisName": row["technological_axis_name"],
                "occupationSubgroupCode": _clean(row["occupation_subgroup_code"]),
                "occupationSubgroupName": _clean(row["occupation_subgroup_name"]),
                "bridgeStatus": row["bridge_status"],
                "correspondenceType": _clean(row["correspondence_type"]),
                "technicalEnrollmentsInformational": _float(row["technical_enrollments"]),
                "additiveAcrossBridgeRows": False,
            }
        )

    for municipality in builder.municipalities:
        entity = municipality["ibgeCode"]
        total = ept_total_index.get((entity, 2025))
        local_rows = by_entity_bridge.get(entity, [])
        if not local_rows:
            builder.bridge_summaries.append(
                {
                    "entityId": entity,
                    "availabilityState": "unavailable",
                    "year": 2025,
                    "observedCourses": 0 if total == 0 else None,
                    "mappedCourses": None,
                    "unmappedCourses": None,
                    "mappedEnrollments": None,
                    "unmappedEnrollments": None,
                    "correspondenceCount": None,
                    "stateContractCoverage": None,
                    "observedValeOfferCoverage": None,
                    "additiveAcrossBridgeRows": False,
                    "samePersonLink": False,
                    "causalLink": False,
                    "sourceRef": "job5gcr_bridge",
                    "territorialLens": "school_location",
                    "note": (
                        "Oferta EPT localizada igual a zero observado; a ponte local não é aplicável como cobertura."
                        if total == 0
                        else "A fonte congelada não materializou correspondências locais."
                    ),
                }
            )
            continue
        unique_offer: dict[tuple[str, str], dict[str, str]] = {}
        for row in local_rows:
            key = (row["school_code"], row["course_code"])
            current = unique_offer.get(key)
            if current is None or current["bridge_status"] == "unmapped":
                unique_offer[key] = row
        mapped = [row for row in unique_offer.values() if row["bridge_status"] == "mapped"]
        unmapped = [row for row in unique_offer.values() if row["bridge_status"] == "unmapped"]
        builder.bridge_summaries.append(
            {
                "entityId": entity,
                "availabilityState": "observed",
                "year": 2025,
                "observedCourses": len({row["course_code"] for row in unique_offer.values()}),
                "mappedCourses": len({row["course_code"] for row in mapped}),
                "unmappedCourses": len({row["course_code"] for row in unmapped}),
                "mappedEnrollments": sum(_float(row["technical_enrollments"]) or 0 for row in mapped),
                "unmappedEnrollments": sum(_float(row["technical_enrollments"]) or 0 for row in unmapped),
                "correspondenceCount": len(local_rows),
                "stateContractCoverage": None,
                "observedValeOfferCoverage": None,
                "additiveAcrossBridgeRows": False,
                "samePersonLink": False,
                "causalLink": False,
                "sourceRef": "job5gcr_bridge",
                "territorialLens": "school_location",
                "note": "Cursos e matrículas deduplicados; correspondências não são linhas aditivas.",
            }
        )

    shift = _rows(JOB5GCR_ROOT / "PAINEL_SHIFT_SHARE_SETORIAL_V1_1.csv.gz")
    by_entity_shift: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in shift:
        code = row["municipality_ibge_code"]
        if code in vale_codes and _bool(row["selection_eligible"]):
            by_entity_shift[code].append(row)
    for entity, rows in sorted(by_entity_shift.items()):
        rows.sort(
            key=lambda row: (
                abs(_float(row["absolute_change"]) or 0),
                0 if _bool(row["small_volume_sensitive"]) else 1,
                hashlib.sha256(
                    "|".join(
                        [
                            row["cnae_division_label"],
                            row["initial_value"],
                            row["final_value"],
                            row["source"],
                        ]
                    ).encode("utf-8")
                ).hexdigest(),
            ),
            reverse=True,
        )
        for row in rows[:10]:
            builder.technical_shift_share.append(
                {
                    "entityId": entity,
                    "sectorCode": row["cnae_division_code"],
                    "sectorLabel": row["cnae_division_label"],
                    "initialValue": _float(row["initial_value"]),
                    "finalValue": _float(row["final_value"]),
                    "absoluteChange": _float(row["absolute_change"]),
                    "referenceGrowthEffect": _float(row["reference_growth_effect"]),
                    "industryMixEffect": _float(row["industry_mix_effect"]),
                    "localDifferentialEffect": _float(row["local_differential_effect"]),
                    "closureResidual": _float(row["closure_residual"]),
                    "causalLink": False,
                    "sourceRef": "job5gcr_shift_share",
                }
            )


SOURCE_DEFINITIONS = [
    ("job5gar_early_childhood", JOB5GAR_ROOT / "PAINEL_EDUCACAO_INFANTIL_OBSERVADA_V1.csv.gz", "Censo Escolar", "2014–2025", ["school_location"]),
    ("job5gar_pressure", JOB5GAR_ROOT / "PAINEL_PRESSAO_MECANICA_COORTES_AUDITADO_V1_1.csv.gz", "Coortes residentes e Censo Escolar", "referência 2025; horizonte mecânico 2026–2030", ["resident_population", "school_location"]),
    ("job5gar_trajectory", JOB5GAR_ROOT / "PAINEL_TRAJETORIA_OFICIAL_DESCRITIVA_V1_1.csv.gz", "Indicadores Educacionais/INEP", "2018–2025", ["school_location"]),
    ("job5gar_staffing", JOB5GAR_ROOT / "PAINEL_DOCENTES_TURMAS_JORNADA_V1_1.csv.gz", "Censo Escolar e indicadores docentes", "2014–2025 ou período específico", ["school_location"]),
    ("job5gar_conditions", JOB5GAR_ROOT / "PAINEL_CONDICOES_ESCOLARES_TOTAL_V1_1.csv.gz", "Censo Escolar e indicadores educacionais", "2014–2025 ou período específico", ["school_location"]),
    ("job5gd_offer", JOB5GD_ROOT / "PAINEL_ESTRUTURA_TERRITORIAL_OFERTA_JOB5GD_V1.csv.gz", "Censo Escolar", "2014–2025; EPT 2023–2025", ["school_location"]),
    ("job5gd_mobility", JOB5GD_ROOT / "PAINEL_MOBILIDADE_EDUCACIONAL_POR_ETAPA_JOB5GD_V1.csv.gz", "Censo Demográfico 2022", "2022", ["student_residence"]),
    ("job5gd_pnate", JOB5GD_ROOT / "PAINEL_TRANSPORTE_ESCOLAR_PNATE_JOB5GD_V1.csv.gz", "FNDE/PNATE — snapshots congelados", "2024–2026 por estágio", ["municipal_executor"]),
    ("job5gbr_adult_schooling", JOB5GBR_ROOT / "PAINEL_ESCOLARIDADE_ADULTA_2010_2022_V1_1.csv.gz", "Censos Demográficos 2010 e 2022", "2010 e 2022", ["resident_population"]),
    ("job5gbr_eja_distribution", JOB5GBR_ROOT / "PAINEL_EJA_DISTRIBUICAO_2022_V1_1.csv.gz", "Censo Demográfico 2022 e Censo Escolar", "2022", ["resident_population", "school_location"]),
    ("job5gbr_eja_history", JOB5GBR_ROOT / "PAINEL_EJA_HISTORICA_2014_2025_V1_1.csv.gz", "Censo Escolar", "2014–2025", ["school_location"]),
    ("job5gbr_eja_integrated_ept", JOB5GBR_ROOT / "PAINEL_EJA_INTEGRADA_EPT_V1_1.csv.gz", "Censo Escolar", "2014–2025", ["school_location"]),
    ("job5gbr_rural", JOB5GBR_ROOT / "PAINEL_EDUCACAO_RURAL_TERRITORIO_V1_1.csv.gz", "Censo Escolar", "2014–2025", ["rural_school_location"]),
    ("job5gbr_special_aee", JOB5GBR_ROOT / "PAINEL_EDUCACAO_ESPECIAL_AEE_V1_1.csv.gz", "Censo Escolar", "2014–2025", ["school_location"]),
    ("job5gcr_rais_youth", JOB5GCR_ROOT / "PAINEL_RAIS_TRABALHO_JUVENIL_V1_1.csv.gz", "RAIS", "2019–2025", ["workplace"]),
    ("job5gcr_caged_safe", JOB5GCR_ROOT / "PAINEL_CAGED_JUVENIL_AGREGADO_SEGURO_V1.csv.gz", "Novo Caged", "2020–2025", ["workplace"]),
    ("job5gcr_work_education", JOB5GCR_ROOT / "PAINEL_TRABALHO_JUVENIL_EDUCACAO_CONTEXTO_V1_1.csv.gz", "INEP, RAIS, Novo Caged e Censo Escolar", "2018–2025", ["school_location", "workplace"]),
    ("job5gcr_apprenticeship", JOB5GCR_ROOT / "PAINEL_APRENDIZAGEM_PROFISSIONAL_V1_1.csv.gz", "Novo Caged", "2020–2025", ["workplace"]),
    ("job5gcr_occupation_endpoints", JOB5GCR_ROOT / "PAINEL_OCUPACOES_RAIS_ESTOQUE_V1.csv.gz", "RAIS", "2019 e 2025; cobertura temporal declarada", ["workplace"]),
    ("job5gcr_sector_endpoints", JOB5GCR_ROOT / "PAINEL_SETORES_RAIS_ESTOQUE_V1.csv.gz", "RAIS", "2019 e 2025; cobertura temporal declarada", ["workplace"]),
    ("job5gcr_ept_offer", JOB5GCR_ROOT / "PAINEL_EPT_OFERTA_TOTAL_V1_1.csv.gz", "Censo Escolar", "2023–2025", ["school_location"]),
    ("job5gcr_bridge", JOB5GCR_ROOT / "PAINEL_PONTE_CBO_CNCT_AUDITADA_V1_1.csv.gz", "Censo Escolar e ponte CNCT–CBO versionada", "2025", ["school_location", "workplace"]),
    ("job5gcr_shift_share", JOB5GCR_ROOT / "PAINEL_SHIFT_SHARE_SETORIAL_V1_1.csv.gz", "RAIS — mesma versão para município e RS", "2019–2025", ["workplace"]),
]


def _source_registry() -> list[dict[str, Any]]:
    registry = []
    for source_ref, path, label, period, lenses in SOURCE_DEFINITIONS:
        if not path.is_file():
            raise Job5IValidationError(f"fonte congelada ausente: {path}")
        registry.append(
            {
                "sourceRef": source_ref,
                "label": label,
                "period": period,
                "territorialLenses": lenses,
                "relativePath": path.relative_to(REPO_ROOT).as_posix(),
                "sha256": _sha256(path),
                "byteSize": path.stat().st_size,
                "officialOrCanonical": True,
                "frozenInput": True,
                "networkUsedByJob5I": False,
            }
        )
    return registry


def _limit_registry() -> list[dict[str, Any]]:
    return [
        {
            "limitId": "separate-territorial-lenses",
            "appliesTo": "all",
            "statement": "População residente, residência de estudantes, localização da oferta, local de trabalho e executor municipal não são fundidos.",
        },
        {
            "limitId": "mechanical-pressure-not-prediction",
            "appliesTo": "D1_COHORT_OFFER_CAPACITY",
            "statement": "A razão mecânica não é previsão, demanda, cobertura ou medida de capacidade.",
        },
        {
            "limitId": "trajectory-no-regional-rate",
            "appliesTo": "D1_TRAJECTORY_CONDITIONS",
            "statement": "A leitura regional usa distribuição municipal e mediana identificada; nenhuma taxa regional é criada.",
        },
        {
            "limitId": "trajectory-2020-2021-caution",
            "appliesTo": "D1_TRAJECTORY_CONDITIONS",
            "statement": "Os anos 2020 e 2021 mantêm anotação explícita de continuidade e comparabilidade.",
        },
        {
            "limitId": "mobility-snapshot-no-destination",
            "appliesTo": "D1_MOBILITY_HIGH_SCHOOL_OFFER",
            "statement": "A mobilidade é fotografia de 2022; destino municipal, corredor e rota não estão disponíveis.",
        },
        {
            "limitId": "pnate-2026-planning-only",
            "appliesTo": "D1_RURALITY_PNATE_PLANNING",
            "statement": "Em 2026, somente a previsão de planejamento é materializada; execução e uso observado permanecem indisponíveis.",
        },
        {
            "limitId": "adult-2010-denominator",
            "appliesTo": "D1_ADULT_SCHOOLING_EJA",
            "statement": "A limitação do denominador de 2010 impede inferências intercensitárias não contratadas sobre participação.",
        },
        {
            "limitId": "work-education-parallel-only",
            "appliesTo": "F_YOUTH_WORK_AND_TRAINING",
            "statement": "Indicadores de conclusão, oferta EPT e trabalho formal são acompanhados em paralelo, sem vínculo de mesma pessoa, teste associativo ou escore combinado.",
        },
        {
            "limitId": "stock-flow-separated",
            "appliesTo": "F_YOUTH_WORK_AND_TRAINING",
            "statement": "Estoque RAIS e fluxos Caged permanecem medidas separadas; eventos não são pessoas únicas.",
        },
        {
            "limitId": "occupation-selection-not-ranking",
            "appliesTo": "D2_OCCUPATIONS_SECTORS",
            "statement": "A seleção evidencia mudanças materiais positivas e negativas; não é prioridade, qualidade ou ranking.",
        },
        {
            "limitId": "bridge-non-additive",
            "appliesTo": "D2_NORMATIVE_WORK_EDUCATION_BRIDGE",
            "statement": "Matrículas não são somadas por linha de correspondência; a ponte é normativa e condicional.",
        },
        {
            "limitId": "pne-context-no-compliance",
            "appliesTo": "all",
            "statement": "Metas oficiais não são recalculadas e nenhum cumprimento é afirmado; PME permanece não materializado.",
        },
    ]


def _family_source_refs(families: Sequence[Mapping[str, Any]], macroblock_id: str) -> list[str]:
    return sorted(
        {
            ref
            for family in families
            if family["macroblockId"] == macroblock_id
            for ref in family["sourceRefs"]
        }
    )


def _build_variants(builder: BundleBuilder) -> list[dict[str, Any]]:
    variants = []
    entities = [
        {"entityId": REGION_ID, "scope": "region", "code": None, "name": None},
        *[
            {
                "entityId": municipality["ibgeCode"],
                "scope": "municipality",
                "code": municipality["ibgeCode"],
                "name": municipality["name"],
            }
            for municipality in builder.municipalities
        ],
    ]
    for family in builder.families:
        family_id = family["storyFamilyId"]
        for entity in entities:
            entity_id = entity["entityId"]
            fact_ids = sorted(
                fact["factId"]
                for fact in builder.facts
                if fact["storyFamilyId"] == family_id and fact["entityId"] == entity_id
            )
            series_ids = sorted(
                series["seriesId"]
                for series in builder.series
                if series["storyFamilyId"] == family_id and series["entityId"] == entity_id
            )
            distribution_ids = sorted(
                distribution["distributionId"]
                for distribution in builder.distributions
                if distribution["storyFamilyId"] == family_id
                and entity_id == REGION_ID
            )
            evidence_ids = []
            if family_id == "D2_OCCUPATIONS_SECTORS":
                evidence_ids = sorted(
                    item["evidenceId"]
                    for item in builder.occupation_evidence
                    if item["entityId"] == entity_id
                )
            elif family_id == "D2_NORMATIVE_WORK_EDUCATION_BRIDGE":
                evidence_ids = [
                    f"bridge-summary.{entity_id}"
                    for item in builder.bridge_summaries
                    if item["entityId"] == entity_id
                ]
            elif family_id == "D2_SECTOR_TRANSFORMATION_SHIFT_SHARE":
                evidence_ids = [
                    f"shift-share.{entity_id}.{item['sectorCode']}"
                    for item in builder.technical_shift_share
                    if item["entityId"] == entity_id
                ]
            referenced_series = [
                series for series in builder.series if series["seriesId"] in set(series_ids)
            ]
            all_points = [point for series in referenced_series for point in series["points"]]
            observed = [
                point for point in all_points if point["availabilityState"] in {"observed", "observed_zero"}
            ]
            nonzero = any(point["availabilityState"] == "observed" for point in observed)
            zero = any(point["availabilityState"] == "observed_zero" for point in observed)
            zero_state = "mixed" if zero and nonzero else "observed_zero" if zero else "not_zero"
            source_refs = sorted(
                {
                    *(
                        fact["sourceRef"]
                        for fact in builder.facts
                        if fact["factId"] in set(fact_ids)
                    ),
                    *(
                        point["sourceRef"]
                        for series in referenced_series
                        for point in series["points"]
                    ),
                }
            )
            availability = (
                "observed"
                if fact_ids or series_ids or distribution_ids or evidence_ids
                else "unavailable"
            )
            bridge_summary = next(
                (item for item in builder.bridge_summaries if item["entityId"] == entity_id),
                None,
            )
            if family_id == "D2_NORMATIVE_WORK_EDUCATION_BRIDGE" and bridge_summary:
                availability = bridge_summary["availabilityState"]
                if availability == "unavailable":
                    zero_state = "not_applicable"
            variants.append(
                {
                    "variantId": f"{family_id}.{entity_id}",
                    "storyFamilyId": family_id,
                    "variantScope": entity["scope"],
                    "entityId": entity_id,
                    "municipalityIbgeCode": entity["code"],
                    "municipalityName": entity["name"],
                    "localFactIds": fact_ids,
                    "seriesIds": series_ids,
                    "distributionIds": distribution_ids,
                    "evidenceIds": evidence_ids,
                    "availabilityState": availability,
                    "zeroState": zero_state,
                    "sourceRefs": source_refs or family["sourceRefs"],
                }
            )
    return variants


def _build_indices(bundle: Mapping[str, Any]) -> dict[str, Any]:
    family_entries = []
    for family in bundle["families"]:
        key = family["storyFamilyId"]
        family_entries.append(
            {
                "key": key,
                "variantIds": [v["variantId"] for v in bundle["variants"] if v["storyFamilyId"] == key],
                "factIds": [f["factId"] for f in bundle["facts"] if f["storyFamilyId"] == key],
                "seriesIds": [s["seriesId"] for s in bundle["series"] if s["storyFamilyId"] == key],
                "distributionIds": [d["distributionId"] for d in bundle["distributions"] if d["storyFamilyId"] == key],
            }
        )
    municipality_entries = []
    for municipality in bundle["municipalities"]:
        key = municipality["ibgeCode"]
        municipality_entries.append(
            {
                "key": key,
                "variantIds": [v["variantId"] for v in bundle["variants"] if v["entityId"] == key],
                "factIds": [f["factId"] for f in bundle["facts"] if f["entityId"] == key],
                "seriesIds": [s["seriesId"] for s in bundle["series"] if s["entityId"] == key],
                "evidenceIds": [e["evidenceId"] for e in bundle["occupationEvidence"] if e["entityId"] == key],
            }
        )
    return {"byStoryFamily": family_entries, "byMunicipalityIbgeCode": municipality_entries}


def _summary_blueprint() -> list[dict[str, Any]]:
    return [
        {"summaryItemId": "pre-school", "sourceKind": "series", "familyId": "D1_COHORT_OFFER_CAPACITY", "metricId": "located_enrollments", "educationalStage": "pre_school_age_4_5", "ageGroup": "", "label": "Pré-escola", "presentation": "observed_endpoints"},
        {"summaryItemId": "fundamental", "sourceKind": "series", "familyId": "D1_COHORT_OFFER_CAPACITY", "metricId": "located_enrollments", "educationalStage": "fundamental", "ageGroup": "", "label": "Ensino fundamental", "presentation": "observed_endpoints"},
        {"summaryItemId": "high-school", "sourceKind": "series", "familyId": "D1_COHORT_OFFER_CAPACITY", "metricId": "located_enrollments", "educationalStage": "high_school", "ageGroup": "", "label": "Ensino médio", "presentation": "observed_endpoints"},
        {"summaryItemId": "schools", "sourceKind": "series", "familyId": "D1_COHORT_OFFER_CAPACITY", "metricId": "schools", "educationalStage": "all", "ageGroup": "", "label": "Escolas", "presentation": "observed_endpoints"},
        {"summaryItemId": "mechanical-pressure", "sourceKind": "fact", "familyId": "D1_COHORT_OFFER_CAPACITY", "metricId": "mechanical_cohort_to_2025_enrollment_ratio", "educationalStage": "high_school", "ageGroup": "", "label": "Razão mecânica — marcador não preditivo", "presentation": "latest"},
        {"summaryItemId": "mobility-high-school", "sourceKind": "series", "familyId": "D1_MOBILITY_HIGH_SCHOOL_OFFER", "metricId": "residents_studying_other_municipality_share", "educationalStage": "high_school", "ageGroup": "", "label": "Residentes do ensino médio que estudavam em outro município", "presentation": "snapshot"},
        {"summaryItemId": "approval", "sourceKind": "series", "familyId": "D1_TRAJECTORY_CONDITIONS", "metricId": "approval_rate_percent", "educationalStage": "high_school", "ageGroup": "", "label": "Aprovação", "presentation": "latest"},
        {"summaryItemId": "failure", "sourceKind": "series", "familyId": "D1_TRAJECTORY_CONDITIONS", "metricId": "failure_rate_percent", "educationalStage": "high_school", "ageGroup": "", "label": "Reprovação", "presentation": "latest"},
        {"summaryItemId": "dropout", "sourceKind": "series", "familyId": "D1_TRAJECTORY_CONDITIONS", "metricId": "dropout_rate_percent", "educationalStage": "high_school", "ageGroup": "", "label": "Abandono", "presentation": "latest"},
        {"summaryItemId": "distortion", "sourceKind": "series", "familyId": "D1_TRAJECTORY_CONDITIONS", "metricId": "age_grade_distortion_rate_percent", "educationalStage": "high_school", "ageGroup": "", "label": "Distorção idade-série", "presentation": "latest"},
        {"summaryItemId": "rural-high-school", "sourceKind": "series", "familyId": "D1_RURALITY_PNATE_PLANNING", "metricId": "rural_enrollments", "educationalStage": "high_school", "ageGroup": "", "label": "Ensino médio rural", "presentation": "observed_endpoints"},
        {"summaryItemId": "eja-total", "sourceKind": "series", "familyId": "D1_ADULT_SCHOOLING_EJA", "metricId": "total_context", "educationalStage": "total_context", "ageGroup": "", "label": "EJA", "presentation": "observed_endpoints"},
        {"summaryItemId": "ept", "sourceKind": "series", "familyId": "D2_EPT_TERRITORIAL_OFFER", "metricId": "technical_enrollments", "educationalStage": "", "ageGroup": "", "label": "EPT localizada", "presentation": "observed_endpoints"},
        {"summaryItemId": "rais-15-17", "sourceKind": "series", "familyId": "D2_YOUTH_WORK_15_17", "metricId": "total", "educationalStage": "", "ageGroup": "15_17", "label": "Vínculos formais de 15 a 17 anos", "presentation": "observed_endpoints"},
        {"summaryItemId": "rais-18-24", "sourceKind": "series", "familyId": "D2_YOUTH_WORK_18_24", "metricId": "total", "educationalStage": "", "ageGroup": "18_24", "label": "Vínculos formais de 18 a 24 anos", "presentation": "observed_endpoints"},
        {"summaryItemId": "apprenticeship-15-17", "sourceKind": "series", "familyId": "D2_APPRENTICESHIP", "metricId": "apprentice_admissions", "educationalStage": "", "ageGroup": "15_17", "label": "Admissões em aprendizagem profissional — 15 a 17", "presentation": "latest"},
        {"summaryItemId": "logistics-anchor", "sourceKind": "evidence", "familyId": "D2_OCCUPATIONS_SECTORS", "metricId": "414140", "educationalStage": "", "ageGroup": "", "label": "Auxiliar de logística", "presentation": "observed_endpoints"},
        {"summaryItemId": "pnate-2026", "sourceKind": "series", "familyId": "D1_RURALITY_PNATE_PLANNING", "metricId": "pnate_adjusted_forecast", "educationalStage": "", "ageGroup": "", "label": "PNATE 2026 — previsão de planejamento", "presentation": "latest"},
    ]


def build_bundle() -> dict[str, Any]:
    municipalities = _load_municipalities()
    vale_codes = {item["ibgeCode"] for item in municipalities}
    families = _load_families()
    macroblocks = _macroblocks()
    builder = BundleBuilder(
        municipalities=municipalities,
        families=families,
        macroblocks=macroblocks,
    )
    _build_demography_offer(builder, vale_codes)
    _build_trajectory_conditions(builder, vale_codes)
    _build_mobility(builder, vale_codes)
    _build_rurality_transport(builder, vale_codes)
    _build_inclusion_adults(builder, vale_codes)
    _build_youth_work(builder, vale_codes)
    _build_economy_ept_bridge(builder, vale_codes)

    source_registry = _source_registry()
    source_lenses = {
        item["sourceRef"]: set(item["territorialLenses"]) for item in source_registry
    }
    visual_contracts = []
    for contract in VISUAL_CONTRACTS:
        source_refs = _family_source_refs(families, contract["macroblockId"])
        visual_contracts.append(
            {
                **contract,
                "sourceRefs": source_refs,
                "territorialLenses": sorted(
                    {lens for ref in source_refs for lens in source_lenses.get(ref, set())}
                ),
            }
        )

    c1_c12 = _rows(JOB5H_ROOT / "MATRIZ_C1_C12_ESPECIFICA_JOB5H.csv.gz")
    qa = _rows(JOB5H_ROOT / "MATRIZ_QA_JOB5H.csv.gz")
    bundle: dict[str, Any] = {
        "schemaVersion": "vocacoes-pne-ui-bundle-v2",
        "contractVersion": "2.0.0-internal-job5i",
        "meta": {
            "jobId": "v7-job5i",
            "generatedAt": GENERATED_AT,
            "internalOnly": True,
            "featureFlag": "VITE_ENABLE_VOCACOES_PNE_INTERNAL",
            "publicNarrativeAuthorized": False,
            "publicationAuthorized": False,
            "publicDataWritesAuthorized": False,
            "gate11": "CLOSED",
            "externalJudgmentRequired": True,
            "managerValidationStarted": False,
            "networkUsed": False,
            "databaseUsed": False,
        },
        "region": {
            "entityId": REGION_ID,
            "name": REGION_NAME,
            "slug": "vale-do-sinos",
            "stateCode": "RS",
            "municipalityCount": 10,
        },
        "fallbackMunicipalityIbgeCode": FALLBACK_MUNICIPALITY_IBGE_CODE,
        "municipalities": municipalities,
        "directions": DIRECTION_DEFINITIONS,
        "macroblocks": macroblocks,
        "families": families,
        "variants": [],
        "facts": sorted(builder.facts, key=lambda item: item["factId"]),
        "distributions": sorted(
            builder.distributions, key=lambda item: item["distributionId"]
        ),
        "series": sorted(builder.series, key=lambda item: item["seriesId"]),
        "occupationEvidence": sorted(
            builder.occupation_evidence, key=lambda item: item["evidenceId"]
        ),
        "bridgeSummaries": sorted(
            builder.bridge_summaries, key=lambda item: item["entityId"]
        ),
        "bridgeCorrespondences": sorted(
            builder.bridge_correspondences, key=lambda item: item["correspondenceId"]
        ),
        "sourceRegistry": source_registry,
        "limitRegistry": _limit_registry(),
        "visualContracts": visual_contracts,
        "languageContract": {
            "schemaVersion": "vocacoes-pne-internal-language-v2",
            "replacements": [
                {"from": source, "to": target}
                for source, target in LANGUAGE_REPLACEMENTS.items()
            ],
            "blockedPatterns": BLOCKED_LANGUAGE,
            "administrativeDependencyAsAnalyticStratumAllowed": False,
            "publicNarrativeAuthorized": False,
        },
        "parallelSeriesContract": {
            "samePersonLink": False,
            "causalLink": False,
            "associationTest": False,
            "combinedScore": False,
            "stockAndFlowMerged": False,
        },
        "occupationSelectionContract": {
            "selectionIsPriorityOrRanking": False,
            "criteriaInOrder": [
                "selection eligibility and family relevance",
                "initial and final volume",
                "absolute magnitude",
                "regional contribution context",
                "temporal coverage",
                "small-volume sensitivity",
                "content digest only after exact substantive tie",
            ],
            "canonicalCodeUsedAsTieBreak": False,
            "expandedPositiveLimit": 8,
            "expandedNegativeLimit": 8,
            "silentThreeItemCap": False,
        },
        "bridgeContract": {
            "additiveAcrossBridgeRows": False,
            "samePersonLink": False,
            "causalLink": False,
            "coverageDeduplicationKey": "school_code+course_code",
        },
        "pneContract": {
            "officialIndicatorRecalculated": False,
            "goalComplianceClaimAllowed": False,
            "legalGoalRefsRemainCanonical": True,
        },
        "pmeContract": {
            "state": "not_materialized",
            "goalRefs": [],
            "planningThemesAreNotGoals": True,
        },
        "summaryBlueprint": _summary_blueprint(),
        "technicalEvidence": {
            "visibleByDefault": False,
            "printedForManager": False,
            "c1C12": c1_c12,
            "qa": qa,
            "shiftShare": builder.technical_shift_share,
            "frozenJob5hManifestSha256": _sha256(JOB5H_ROOT / "MANIFEST_JOB5H.json"),
            "rawCagedDetailExposed": False,
        },
        "indices": {"byStoryFamily": [], "byMunicipalityIbgeCode": []},
        "counts": {},
    }
    bundle["variants"] = _build_variants(builder)
    bundle["indices"] = _build_indices(bundle)
    bundle["counts"] = {
        "directionCount": len(bundle["directions"]),
        "macroblockCount": len(bundle["macroblocks"]),
        "familyCount": len(bundle["families"]),
        "variantCount": len(bundle["variants"]),
        "municipalityCount": len(bundle["municipalities"]),
        "factCount": len(bundle["facts"]),
        "distributionCount": len(bundle["distributions"]),
        "seriesCount": len(bundle["series"]),
        "seriesPointCount": sum(len(item["points"]) for item in bundle["series"]),
        "occupationEvidenceCount": len(bundle["occupationEvidence"]),
        "bridgeCorrespondenceCount": len(bundle["bridgeCorrespondences"]),
    }
    validate_bundle(bundle)
    return bundle


def _find_series(
    bundle: Mapping[str, Any],
    *,
    family_id: str,
    entity_id: str,
    metric_id: str,
    stage: str = "",
    age: str = "",
) -> Mapping[str, Any]:
    matches = [
        item
        for item in bundle["series"]
        if item["storyFamilyId"] == family_id
        and item["entityId"] == entity_id
        and item["metricId"] == metric_id
        and (not stage or item["educationalStage"] == stage)
        and (not age or item["ageGroup"] == age)
    ]
    if len(matches) != 1:
        raise Job5IValidationError(
            f"série única esperada para {family_id}/{entity_id}/{metric_id}/{stage}/{age}: {len(matches)}"
        )
    return matches[0]


def _point_value(series: Mapping[str, Any], year: int) -> float | None:
    point = next((item for item in series["points"] if item["year"] == year), None)
    if point is None:
        raise Job5IValidationError(f"ano {year} ausente em {series['seriesId']}")
    return point["value"]


def _language_targets(bundle: Mapping[str, Any]) -> list[str]:
    values = []
    for direction in bundle["directions"]:
        values.extend([direction["title"], direction["summary"]])
    for macroblock in bundle["macroblocks"]:
        values.extend(
            [macroblock["title"], macroblock["summary"], macroblock["primaryQuestion"]]
        )
    for family in bundle["families"]:
        values.extend(
            [
                family["title"],
                family["summary"],
                family["regionalQuestion"],
                family["municipalQuestion"],
                family["planningQuestion"],
            ]
        )
    for visual in bundle["visualContracts"]:
        values.extend([visual["title"], visual["measure"], visual["comparisonRule"]])
    return values


def validate_bundle(bundle: Mapping[str, Any]) -> None:
    if bundle["meta"]["gate11"] != "CLOSED":
        raise Job5IValidationError("Gate 11 deve permanecer fechado")
    if bundle["meta"]["publicNarrativeAuthorized"] or bundle["meta"]["publicationAuthorized"]:
        raise Job5IValidationError("narrativa pública e publicação devem permanecer desautorizadas")
    if len(bundle["families"]) != 13 or len(bundle["macroblocks"]) != 7:
        raise Job5IValidationError("o bundle deve preservar 13 famílias e sete macroblocos")
    if len(bundle["municipalities"]) != 10 or len(bundle["variants"]) != 143:
        raise Job5IValidationError("o bundle deve preservar dez municípios e 143 variantes")
    codes = [item["ibgeCode"] for item in bundle["municipalities"]]
    if len(set(codes)) != 10 or any(not re.fullmatch(r"[0-9]{7}", code) for code in codes):
        raise Job5IValidationError("identidades municipais devem ser dez códigos IBGE textuais únicos")
    if FALLBACK_MUNICIPALITY_IBGE_CODE not in codes:
        raise Job5IValidationError("Nova Santa Rita 4313375 deve integrar o recorte")
    if any(item["networkScope"] != NETWORK_SCOPE for item in bundle["families"]):
        raise Job5IValidationError("todas as famílias educacionais devem usar rede total")
    if bundle["pmeContract"]["goalRefs"]:
        raise Job5IValidationError("PME deve permanecer não materializado")
    if any(bundle["parallelSeriesContract"].values()):
        raise Job5IValidationError("os quatro vínculos de séries paralelas devem permanecer falsos")

    fact_ids = [item["factId"] for item in bundle["facts"]]
    series_ids = [item["seriesId"] for item in bundle["series"]]
    if len(fact_ids) != len(set(fact_ids)) or len(series_ids) != len(set(series_ids)):
        raise Job5IValidationError("fatos e séries devem possuir identidades únicas")
    for fact in bundle["facts"]:
        state = fact["availabilityState"]
        value = fact["value"]
        if state not in AVAILABILITY_STATES:
            raise Job5IValidationError(f"estado inválido em {fact['factId']}")
        if state == "observed_zero" and value != 0:
            raise Job5IValidationError(f"zero observado inválido em {fact['factId']}")
        if state in {"unavailable", "not_applicable", "suppressed"} and value is not None:
            raise Job5IValidationError(f"estado sem valor contém número em {fact['factId']}")
        if fact["unit"] == "percent" and value is not None and not (0 <= value <= 100):
            raise Job5IValidationError(f"percentual fora de 0–100 em {fact['factId']}: {value}")
        if fact["unit"] == "percent" and value is not None:
            if fact["numerator"] is None or fact["denominator"] is None or fact["rawRatio"] is None:
                raise Job5IValidationError(f"componentes proporcionais ausentes em {fact['factId']}")
            if not math.isclose(fact["displayValue"], fact["rawRatio"] * 100, rel_tol=0, abs_tol=1e-9):
                raise Job5IValidationError(f"escala duplicada ou ausente em {fact['factId']}")
        if fact["territorialLens"] not in TERRITORIAL_LENSES:
            raise Job5IValidationError(f"lente inválida em {fact['factId']}")
    for series in bundle["series"]:
        years = [point["year"] for point in series["points"]]
        if years != sorted(set(years)):
            raise Job5IValidationError(f"anos duplicados ou desordenados em {series['seriesId']}")
        for point in series["points"]:
            state = point["availabilityState"]
            value = point["value"]
            if state == "observed_zero" and value != 0:
                raise Job5IValidationError(f"zero observado inválido em {series['seriesId']}")
            if state in {"unavailable", "not_applicable", "suppressed"} and value is not None:
                raise Job5IValidationError(f"ausência com valor em {series['seriesId']}")
            if series["unit"] == "percent" and value is not None and not (0 <= value <= 100):
                raise Job5IValidationError(f"percentual de série fora de 0–100 em {series['seriesId']}")
            if series["unit"] == "percent" and value is not None:
                if point["numerator"] is None or point["denominator"] is None or point["rawRatio"] is None:
                    raise Job5IValidationError(f"componentes proporcionais ausentes em {series['seriesId']}")
                if not math.isclose(point["displayValue"], point["rawRatio"] * 100, rel_tol=0, abs_tol=1e-9):
                    raise Job5IValidationError(f"escala percentual inválida em {series['seriesId']}")
    for distribution in bundle["distributions"]:
        distribution_codes = [
            item["municipalityIbgeCode"] for item in distribution["municipalValues"]
        ]
        if len(distribution_codes) != 10 or set(distribution_codes) != set(codes):
            raise Job5IValidationError(
                f"distribuição municipal incompleta em {distribution['distributionId']}"
            )
        for municipal_value in distribution["municipalValues"]:
            value = municipal_value["value"]
            if value is None:
                continue
            if (
                municipal_value["numerator"] is None
                or municipal_value["denominator"] is None
                or municipal_value["rawRatio"] is None
            ):
                raise Job5IValidationError(
                    f"componentes proporcionais ausentes em {distribution['distributionId']}"
                )
            if not math.isclose(
                municipal_value["displayValue"],
                municipal_value["rawRatio"] * 100,
                rel_tol=0,
                abs_tol=1e-9,
            ):
                raise Job5IValidationError(
                    f"escala proporcional inválida em {distribution['distributionId']}"
                )
        if "Mediana" not in distribution["valeMedianLabel"]:
            raise Job5IValidationError("medianas devem ser identificadas como medianas")
    if any(
        item["storyFamilyId"] == "D1_TRAJECTORY_CONDITIONS" and item["entityId"] == REGION_ID
        for item in bundle["series"]
    ):
        raise Job5IValidationError("nenhuma taxa regional de trajetória pode ser materializada")

    apprenticeship = {
        item["factId"]: item
        for item in bundle["facts"]
        if item["metricId"] == "apprenticeship_share_of_youth_admission_events"
    }
    anchors = {
        "D2_APPRENTICESHIP.4313375.share.15_17.2025": (174, 219, 79.45205479452054),
        f"D2_APPRENTICESHIP.{REGION_ID}.share.15_17.2025": (3157, 5855, 53.91972672929121),
        f"D2_APPRENTICESHIP.{REGION_ID}.share.18_24.2025": (717, 38757, 1.84998838919421),
    }
    for fact_id, (numerator, denominator, display) in anchors.items():
        fact = apprenticeship[fact_id]
        if fact["numerator"] != numerator or fact["denominator"] != denominator:
            raise Job5IValidationError(f"componentes de aprendizagem divergentes em {fact_id}")
        if not math.isclose(fact["displayValue"], display, rel_tol=0, abs_tol=1e-12):
            raise Job5IValidationError(f"percentual de aprendizagem divergente em {fact_id}")

    ept_shares = [
        item
        for item in bundle["facts"]
        if item["metricId"] == "share_of_regional_technical_enrollments"
        and item["entityId"] != REGION_ID
    ]
    for year in (2023, 2024, 2025):
        values = [item["displayValue"] for item in ept_shares if item["period"] == str(year)]
        if len(values) != 10 or not math.isclose(sum(values), 100, rel_tol=0, abs_tol=1e-9):
            raise Job5IValidationError(f"participações EPT não fecham 100% em {year}")
    novo = next(
        item for item in ept_shares if item["entityId"] == "4313409" and item["period"] == "2025"
    )
    if not math.isclose(novo["displayValue"], 39.7346719254213, rel_tol=0, abs_tol=1e-12):
        raise Job5IValidationError("participação EPT de Novo Hamburgo está fora da escala")

    pre_nsr = _find_series(bundle, family_id="D1_COHORT_OFFER_CAPACITY", entity_id="4313375", metric_id="located_enrollments", stage="pre_school_age_4_5")
    pre_vale = _find_series(bundle, family_id="D1_COHORT_OFFER_CAPACITY", entity_id=REGION_ID, metric_id="located_enrollments", stage="pre_school_age_4_5")
    ept_vale = _find_series(bundle, family_id="D2_EPT_TERRITORIAL_OFFER", entity_id=REGION_ID, metric_id="technical_enrollments")
    if (_point_value(pre_nsr, 2014), _point_value(pre_nsr, 2025)) != (459, 823):
        raise Job5IValidationError("pré-escola de Nova Santa Rita divergente")
    if (_point_value(pre_vale, 2014), _point_value(pre_vale, 2025)) != (17251, 20716):
        raise Job5IValidationError("pré-escola do Vale divergente")
    if (_point_value(ept_vale, 2023), _point_value(ept_vale, 2025)) != (13474, 13945):
        raise Job5IValidationError("EPT do Vale divergente")
    anchors_evidence = [
        item
        for item in bundle["occupationEvidence"]
        if item["dimensionCode"] == "414140" and item["entityId"] in {REGION_ID, "4313375"}
    ]
    anchor_values = {item["entityId"]: (item["initialValue"], item["finalValue"]) for item in anchors_evidence}
    if anchor_values != {REGION_ID: (303, 2124), "4313375": (17, 722)}:
        raise Job5IValidationError("anchor Auxiliar de logística divergente")
    bridge = next(item for item in bundle["bridgeSummaries"] if item["entityId"] == REGION_ID)
    if (
        bridge["observedCourses"],
        bridge["mappedCourses"],
        bridge["unmappedCourses"],
        bridge["mappedEnrollments"],
        bridge["unmappedEnrollments"],
    ) != (44, 39, 5, 12664, 1281):
        raise Job5IValidationError("cobertura da ponte no Vale divergente")
    if bridge["additiveAcrossBridgeRows"]:
        raise Job5IValidationError("a ponte não pode ser aditiva")

    trajectory = [
        item for item in bundle["series"] if item["storyFamilyId"] == "D1_TRAJECTORY_CONDITIONS"
        and item["metricId"] in {
            "approval_rate_percent",
            "failure_rate_percent",
            "dropout_rate_percent",
            "age_grade_distortion_rate_percent",
        }
    ]
    for series in trajectory:
        caution = {
            point["year"]: point["breakOrCautionState"]
            for point in series["points"]
            if point["year"] in {2020, 2021}
        }
        if caution and set(caution.values()) != {"continuity_caution"}:
            raise Job5IValidationError(f"cautela 2020–2021 ausente em {series['seriesId']}")
    for series in bundle["series"]:
        if series["metricId"] == "pnate_executed_amount":
            point_2026 = next(item for item in series["points"] if item["year"] == 2026)
            if point_2026["availabilityState"] != "unavailable" or point_2026["value"] is not None:
                raise Job5IValidationError("PNATE 2026 não pode ser execução")
        if series["metricId"] == "pnate_adjusted_forecast":
            point_2026 = next(item for item in series["points"] if item["year"] == 2026)
            if point_2026["breakOrCautionState"] != "planning_forecast":
                raise Job5IValidationError("PNATE 2026 deve ser previsão de planejamento")

    legal = _json(REPO_ROOT / "contracts" / "pne2026-goal-indicator-contract.json")
    legal_refs = set(legal["goals"])
    visible_refs = {ref for family in bundle["families"] for ref in family["visiblePneGoalRefs"]}
    if not visible_refs <= legal_refs:
        raise Job5IValidationError("vínculo PNE visível não existe no contrato legal")
    if not {"6.a", "17.a", "19.c"} <= visible_refs:
        raise Job5IValidationError("inputs recuperados devem manter 6.a, 17.a e 19.c visíveis")
    for text in _language_targets(bundle):
        for rule in BLOCKED_LANGUAGE:
            if re.search(rule["pattern"], text, flags=re.IGNORECASE):
                raise Job5IValidationError(
                    f"linguagem bloqueada {rule['id']} em texto visível: {text!r}"
                )
    if bundle["occupationSelectionContract"]["canonicalCodeUsedAsTieBreak"]:
        raise Job5IValidationError("código canônico não pode desempatar seleção")
    if len(bundle["technicalEvidence"]["c1C12"]) != 156:
        raise Job5IValidationError("matriz C1–C12 congelada deve preservar 156 linhas")


def _preflight_report(bundle: Mapping[str, Any]) -> dict[str, Any]:
    percent_facts = [item for item in bundle["facts"] if item["unit"] == "percent"]
    percent_points = [
        point
        for series in bundle["series"]
        if series["unit"] == "percent"
        for point in series["points"]
    ]
    return {
        "schemaVersion": "vocacoes-pne-job5i-preflight-v1",
        "jobId": "v7-job5i",
        "result": "PASSED",
        "directReactConsumptionOfJob5hCorpus": False,
        "frozenInputsModified": False,
        "publicDataModified": False,
        "newSourcesUsed": False,
        "networkUsed": False,
        "databaseUsed": False,
        "scaleCorrections": [
            {
                "metric": "apprenticeship_share_of_youth_admission_events",
                "rawProblem": "ratio 0–1 labeled as percent",
                "resolution": "numerator + denominator + rawRatio 0–1 + displayValue 0–100",
            },
            {
                "metric": "share_of_regional_technical_enrollments",
                "rawProblem": "municipal values sum 1 while labeled as percent",
                "resolution": "rawRatio 0–1 retained and displayValue materialized in 0–100",
            },
            {
                "metric": "regional self shares",
                "rawProblem": "100% tautologies for EJA and EPT regional variants",
                "resolution": "not_applicable; regional totals and municipal distributions retained",
            },
        ],
        "percentValidation": {
            "factCount": len(percent_facts),
            "seriesPointCount": len(percent_points),
            "allDisplayValuesWithinZeroToOneHundred": True,
            "doubleMultiplicationDetected": False,
            "reactScaleHeuristicRequired": False,
        },
        "recoveredFacts": {
            "preSchoolNovaSantaRita": {"2014": 459, "2025": 823, "change": 364},
            "preSchoolVale": {"2014": 17251, "2025": 20716, "change": 3465},
            "eptVale": {"2023": 13474, "2025": 13945, "change": 471},
            "adultSchooling": "2010 and 2022 counts, 2022 composition and denominator limit",
            "eja": "stage series, integrated EPT and zero-versus-absence states",
            "conditions": "classes, teachers, full time, adequacy, regularity and infrastructure",
            "workEducation": "parallel education and labor series with all four link flags false",
            "bridge": {"observedCourses": 44, "mappedCourses": 39, "unmappedCourses": 5, "mappedEnrollments": 12664, "unmappedEnrollments": 1281},
        },
        "seriesMaterialization": {
            "seriesCount": bundle["counts"]["seriesCount"],
            "pointCount": bundle["counts"]["seriesPointCount"],
            "interpolationUsed": False,
            "smoothingUsed": False,
            "endpointPairsPresentedAsContinuousSeries": False,
            "mobilityTemporalNature": "single_year_snapshot",
        },
        "normalization": {
            "familyCount": bundle["counts"]["familyCount"],
            "variantCount": bundle["counts"]["variantCount"],
            "macroblockCount": bundle["counts"]["macroblockCount"],
            "namedInputMetricsDuplicateRemoved": True,
            "familiesStoredOnce": True,
            "regionalFactsStoredOnce": True,
            "municipalDistributionsStoredOnce": True,
            "seriesStoredSeparately": True,
            "sourceAndLimitRegistriesPresent": True,
        },
        "gate11": "CLOSED",
        "publicNarrativeAuthorized": False,
        "publicationPerformed": False,
    }


def _json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def _compact_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")


def _compiler_outputs(bundle: Mapping[str, Any]) -> dict[Path, bytes]:
    contract = _json(
        REPO_ROOT / "data_pipeline" / "contracts" / "vocacoes-pne-v7-job5i.json"
    )
    contract = {
        **contract,
        "executionState": {
            "preflight": "PASSED",
            "uiCompilation": "PASSED",
            "frontendImplementation": "AUTHORIZED_INTERNAL_ONLY",
            "externalJudgment": "PENDING",
            "managerValidation": "NOT_STARTED",
            "gate11": "CLOSED",
        },
    }
    coverage = {
        "schemaVersion": "vocacoes-pne-job5i-data-coverage-v1",
        "familyCount": bundle["counts"]["familyCount"],
        "macroblockCount": bundle["counts"]["macroblockCount"],
        "municipalityCount": bundle["counts"]["municipalityCount"],
        "rows": [
            {
                "macroblockId": macroblock["macroblockId"],
                "familyIds": macroblock["familyIds"],
                "seriesCount": sum(
                    1
                    for series in bundle["series"]
                    if series["storyFamilyId"] in set(macroblock["familyIds"])
                ),
                "factCount": sum(
                    1
                    for fact in bundle["facts"]
                    if fact["storyFamilyId"] in set(macroblock["familyIds"])
                ),
                "sourceRefs": next(
                    item["sourceRefs"]
                    for item in bundle["visualContracts"]
                    if item["macroblockId"] == macroblock["macroblockId"]
                ),
                "status": "covered",
            }
            for macroblock in bundle["macroblocks"]
        ],
    }
    frontend_core = {
        key: value
        for key, value in bundle.items()
        if key not in {"series", "technicalEvidence"}
    }
    frontend_core["seriesBundle"] = {
        "schemaVersion": "vocacoes-pne-ui-series-bundle-v2",
        "dynamicImport": "./vocacoesPneJob5iSeries.json",
        "seriesCount": bundle["counts"]["seriesCount"],
        "seriesPointCount": bundle["counts"]["seriesPointCount"],
    }
    frontend_core["technicalBundle"] = {
        "schemaVersion": "vocacoes-pne-ui-technical-bundle-v2",
        "dynamicImport": "./vocacoesPneJob5iTechnical.json",
        "visibleByDefault": False,
        "printedForManager": False,
    }
    frontend_series = {
        "schemaVersion": "vocacoes-pne-ui-series-bundle-v2",
        "series": bundle["series"],
    }
    frontend_technical = {
        "schemaVersion": "vocacoes-pne-ui-technical-bundle-v2",
        "technicalEvidence": bundle["technicalEvidence"],
    }
    outputs = {
        OUTPUT_ROOT / "CONTRATO_JOB5I.json": _json_bytes(contract),
        OUTPUT_ROOT / "RELATORIO_PREFLIGHT_CONSUMO_JOB5I.json": _json_bytes(
            _preflight_report(bundle)
        ),
        OUTPUT_ROOT / "BUNDLE_UI_V2_JOB5I.json": _json_bytes(bundle),
        OUTPUT_ROOT / "REGISTRO_FONTES_E_LIMITES_JOB5I.json": _json_bytes(
            {
                "schemaVersion": "vocacoes-pne-job5i-source-limit-registry-v1",
                "sources": bundle["sourceRegistry"],
                "limits": bundle["limitRegistry"],
            }
        ),
        OUTPUT_ROOT / "CONTRATO_VISUAL_MACROBLOCOS_JOB5I.json": _json_bytes(
            {
                "schemaVersion": "vocacoes-pne-job5i-visual-contract-v1",
                "directions": bundle["directions"],
                "macroblocks": bundle["macroblocks"],
                "visualContracts": bundle["visualContracts"],
                "layers": [
                    "PRIMARY_NARRATIVE_PATH",
                    "EXPANDED_EVIDENCE_LAYER",
                    "INTERNAL_TECHNICAL_LAYER",
                ],
            }
        ),
        OUTPUT_ROOT / "CONTRATO_LINGUAGEM_PROTOTIPO_INTERNO_JOB5I.json": _json_bytes(
            bundle["languageContract"]
        ),
        OUTPUT_ROOT / "MATRIZ_COBERTURA_DADOS_JOB5I.json": _json_bytes(coverage),
        FRONTEND_CORE_BUNDLE: _compact_json_bytes(frontend_core),
        FRONTEND_SERIES_BUNDLE: _compact_json_bytes(frontend_series),
        FRONTEND_TECHNICAL_BUNDLE: _compact_json_bytes(frontend_technical),
    }
    for filename in (
        "vocacoes-pne-ui-v2-family.schema.json",
        "vocacoes-pne-ui-v2-macroblock.schema.json",
        "vocacoes-pne-ui-v2-variant.schema.json",
        "vocacoes-pne-ui-v2-series.schema.json",
    ):
        source = REPO_ROOT / "data_pipeline" / "contracts" / filename
        outputs[OUTPUT_ROOT / filename] = source.read_bytes()
    return outputs


def _promote_transactional(outputs: Mapping[Path, bytes]) -> int:
    changed = {
        path: content
        for path, content in outputs.items()
        if not path.is_file() or path.read_bytes() != content
    }
    if not changed:
        return 0
    staged: list[tuple[Path, Path]] = []
    journal: list[tuple[Path, Path | None]] = []
    try:
        for path, content in changed.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_name(f".{path.name}.job5i-staging")
            temporary.write_bytes(content)
            staged.append((path, temporary))
        for path, temporary in staged:
            backup = path.with_name(f".{path.name}.job5i-backup") if path.exists() else None
            if backup is not None:
                if backup.exists():
                    backup.unlink()
                path.replace(backup)
            journal.append((path, backup))
            temporary.replace(path)
    except Exception as error:
        rollback_errors = []
        for path, backup in reversed(journal):
            try:
                if path.exists():
                    path.unlink()
                if backup is not None and backup.exists():
                    backup.replace(path)
            except Exception as rollback_error:  # pragma: no cover - emergency path
                rollback_errors.append(rollback_error)
        if rollback_errors:
            raise Job5IValidationError(
                "promoção falhou e o rollback ficou incompleto; backups foram preservados"
            ) from ExceptionGroup("rollback incompleto", [error, *rollback_errors])
        raise Job5IValidationError("promoção transacional dos artefatos Job 5I falhou") from error
    finally:
        for _, temporary in staged:
            if temporary.exists():
                temporary.unlink()
    for _, backup in journal:
        if backup is not None and backup.exists():
            backup.unlink()
    return len(changed)


def compile_job5i(*, check: bool = False) -> dict[str, Any]:
    bundle = build_bundle()
    outputs = _compiler_outputs(bundle)
    if check:
        divergent = [
            path
            for path, content in outputs.items()
            if not path.is_file() or path.read_bytes() != content
        ]
        if divergent:
            raise Job5IValidationError(
                "artefatos do compilador divergentes: "
                + ", ".join(path.relative_to(REPO_ROOT).as_posix() for path in divergent)
            )
        changed = 0
    else:
        changed = _promote_transactional(outputs)
    return {"bundle": bundle, "outputs": outputs, "changed": changed}


EXPECTED_SCREENSHOTS = [
    ("01-nova-santa-rita-desktop.png", "Página completa — Nova Santa Rita — desktop"),
    ("02-vale-do-sinos-desktop.png", "Página completa — Vale do Sinos"),
    ("03-nova-santa-rita-1024.png", "Nova Santa Rita — 1024 px"),
    ("04-nova-santa-rita-390.png", "Nova Santa Rita — 390 px"),
    ("05-impressao.png", "Impressão"),
    ("06-demografia-oferta.png", "Macrobloco demografia e oferta"),
    ("07-trajetoria-mobilidade.png", "Trajetória e mobilidade"),
    ("08-trabalho-aprendizagem.png", "Trabalho juvenil e aprendizagem"),
    ("09-economia-ept.png", "Economia e EPT"),
    ("10-ept-zero-observado.png", "Estado EPT zero observado"),
    ("11-ponte-indisponivel.png", "Ponte indisponível"),
    ("12-ruralidade-zero.png", "Município com ruralidade zero"),
    ("13-ept-positiva.png", "Município com oferta EPT positiva"),
    ("14-evidencia-expandida.png", "Evidência expandida"),
    ("15-modo-tecnico.png", "Modo técnico separado"),
]


def _final_preservation() -> dict[str, Any]:
    baseline = _json(OUTPUT_ROOT / "PRESERVATION_BASELINE.json")
    frozen_files = []
    for path in sorted(JOB5H_ROOT.rglob("*")):
        if path.is_file():
            frozen_files.append(
                {
                    "path": path.relative_to(JOB5H_ROOT).as_posix(),
                    "size": path.stat().st_size,
                    "sha256": _sha256(path),
                }
            )
    expected = baseline["frozenJob5h"]["files"]
    frozen_unchanged = frozen_files == expected
    return {
        "schemaVersion": "vocacoes-pne-job5i-preservation-final-v1",
        "baselineCapturedAt": baseline["capturedAt"],
        "checkedAt": GENERATED_AT,
        "frozenJob5h": {
            "beforeTreeDigestSha256": baseline["frozenJob5h"]["treeDigestSha256"],
            "beforeFileCount": baseline["frozenJob5h"]["fileCount"],
            "afterFileCount": len(frozen_files),
            "afterTotalBytes": sum(item["size"] for item in frozen_files),
            "filesBytewiseEqualToBaseline": frozen_unchanged,
            "files": frozen_files,
        },
        "publicData": {
            "beforeTreeDigestSha256": baseline["publicData"]["treeDigestSha256"],
            "beforeFileCount": baseline["publicData"]["fileCount"],
            "beforeTotalBytes": baseline["publicData"]["totalBytes"],
            "afterVerification": "git diff -- public/data and final tree digest recorded by validation report",
        },
        "frozenInputsModified": not frozen_unchanged,
    }


def _dossier_markdown(bundle: Mapping[str, Any], entity_id: str, title: str) -> str:
    municipality = next(
        (item for item in bundle["municipalities"] if item["ibgeCode"] == entity_id), None
    )
    name = municipality["name"] if municipality else REGION_NAME
    lines = [
        f"# Dossiê visual interno — {title}",
        "",
        "> Protótipo interno para avaliação — conteúdo ainda não publicado.",
        "",
        f"A leitura mantém {REGION_NAME} visível e usa {name} como "
        + ("município selecionado." if municipality else "visão regional."),
        "",
        "## Evidências de reconstrução",
        "",
    ]
    if entity_id == "4313375":
        lines.extend(
            [
                "- Pré-escola: 459 matrículas localizadas em 2014 e 823 em 2025.",
                "- Ensino fundamental: 3.873 em 2014 e 3.957 em 2025; ensino médio: 799 e 840.",
                "- Escolas: 24 em 2014 e 28 em 2025.",
                "- Razão mecânica do ensino médio em 2030: 1,641666…, como marcador não preditivo.",
                "- Fotografia de mobilidade do ensino médio em 2022: 19,1138%.",
                "- EPT localizada em 2025: zero observado.",
                "- Vínculos formais: 104 → 172 (15–17) e 1.117 → 1.638 (18–24).",
                "- Aprendizagem em 2025: 174 eventos de admissão na faixa de 15–17.",
                "- Auxiliar de logística: 17 → 722 vínculos formais ativos.",
                "- PNATE 2026 aparece somente como previsão de planejamento.",
            ]
        )
    else:
        lines.extend(
            [
                "- Pré-escola: 17.251 matrículas localizadas em 2014 e 20.716 em 2025.",
                "- EPT: 13.474 matrículas localizadas em 2023 e 13.945 em 2025.",
                "- Ponte em 2025: 44 cursos observados, 39 mapeados e cinco não mapeados.",
                "- Cobertura deduplicada: 12.664 matrículas mapeadas e 1.281 não mapeadas.",
                "- Auxiliar de logística: 303 → 2.124 vínculos formais ativos.",
                "- Trajetória regional é mostrada por distribuição e mediana dos dez municípios.",
            ]
        )
    lines.extend(
        [
            "",
            "## Limites preservados",
            "",
            "- Nenhuma meta oficial foi recalculada e PME permanece não materializado.",
            "- Estoques, fluxos, pessoas, eventos e lentes territoriais não são fundidos.",
            "- A seleção de ocupações e setores não representa prioridade ou ranking.",
            "- Gate 11 permanece fechado; não houve publicação.",
            "",
        ]
    )
    return "\n".join(lines)


def finalize_job5i() -> dict[str, Any]:
    bundle = _json(OUTPUT_ROOT / "BUNDLE_UI_V2_JOB5I.json")
    validate_bundle(bundle)
    observations_path = OUTPUT_ROOT / "VISUAL_QA_OBSERVATIONS_JOB5I.json"
    if not observations_path.is_file():
        raise Job5IValidationError("observações de QA visual ausentes")
    observations = _json(observations_path)
    screenshots_root = OUTPUT_ROOT / "screenshots"
    coverage_rows = []
    for filename, label in EXPECTED_SCREENSHOTS:
        path = screenshots_root / filename
        if not path.is_file():
            raise Job5IValidationError(f"screenshot obrigatório ausente: {filename}")
        coverage_rows.append(
            {
                "screenshot": f"screenshots/{filename}",
                "label": label,
                "byteSize": path.stat().st_size,
                "sha256": _sha256(path),
                "status": "captured_and_inspected",
            }
        )
    preservation = _final_preservation()
    if preservation["frozenInputsModified"]:
        raise Job5IValidationError("outputs congelados do Job 5H foram alterados")
    visual_matrix = {
        "schemaVersion": "vocacoes-pne-job5i-visual-coverage-v1",
        "requiredScreenshotCount": len(EXPECTED_SCREENSHOTS),
        "capturedScreenshotCount": len(coverage_rows),
        "rows": coverage_rows,
    }
    qa_matrix = {
        "schemaVersion": "vocacoes-pne-job5i-visual-qa-v1",
        "result": observations["result"],
        "criteria": observations["criteria"],
        "issuesFoundAndFixed": observations["issuesFoundAndFixed"],
        "remainingLimits": observations["remainingLimits"],
    }
    package = {
        "schemaVersion": "vocacoes-pne-job5i-external-review-package-v1",
        "jobId": "v7-job5i",
        "state": "JOB_5I_READY_WITH_EXPLICIT_LIMITS_FOR_EXTERNAL_JUDGMENT",
        "externalJudgmentRequired": True,
        "managerValidationStarted": False,
        "gate11": "CLOSED",
        "publicNarrativeAuthorized": False,
        "publicationPerformed": False,
        "artifacts": [
            "CONTRATO_JOB5I.json",
            "RELATORIO_PREFLIGHT_CONSUMO_JOB5I.json",
            "BUNDLE_UI_V2_JOB5I.json",
            "CONTRATO_VISUAL_MACROBLOCOS_JOB5I.json",
            "CONTRATO_LINGUAGEM_PROTOTIPO_INTERNO_JOB5I.json",
            "MATRIZ_COBERTURA_VISUAL_JOB5I.json",
            "MATRIZ_QA_VISUAL_JOB5I.json",
            "DOSSIE_VISUAL_NOVA_SANTA_RITA_JOB5I.md",
            "DOSSIE_VISUAL_VALE_DO_SINOS_JOB5I.md",
            "screenshots",
        ],
        "explicitLimits": observations["remainingLimits"],
    }
    outputs = {
        OUTPUT_ROOT / "PRESERVATION_FINAL.json": _json_bytes(preservation),
        OUTPUT_ROOT / "MATRIZ_COBERTURA_VISUAL_JOB5I.json": _json_bytes(visual_matrix),
        OUTPUT_ROOT / "MATRIZ_QA_VISUAL_JOB5I.json": _json_bytes(qa_matrix),
        OUTPUT_ROOT / "DOSSIE_VISUAL_NOVA_SANTA_RITA_JOB5I.md": _dossier_markdown(bundle, "4313375", "Nova Santa Rita").encode("utf-8"),
        OUTPUT_ROOT / "DOSSIE_VISUAL_VALE_DO_SINOS_JOB5I.md": _dossier_markdown(bundle, REGION_ID, "Vale do Sinos").encode("utf-8"),
        OUTPUT_ROOT / "PACOTE_REVISAO_EXTERNA_JOB5I.json": _json_bytes(package),
    }
    _promote_transactional(outputs)

    artifact_files = [
        path
        for path in sorted(OUTPUT_ROOT.rglob("*"))
        if path.is_file() and path.name != "MANIFEST_JOB5I.json"
    ]
    implementation_roots = [
        REPO_ROOT / "data_pipeline" / "contracts",
        REPO_ROOT / "data_pipeline" / "src",
        REPO_ROOT / "data_pipeline" / "scripts",
        REPO_ROOT / "data_pipeline" / "tests",
        REPO_ROOT / "src" / "features" / "vocacoes-pne-internal",
        REPO_ROOT / "scripts" / "checks",
    ]
    implementation_names = {
        "vocacoes-pne-v7-job5i.json",
        "vocacoes-pne-ui-v2-family.schema.json",
        "vocacoes-pne-ui-v2-macroblock.schema.json",
        "vocacoes-pne-ui-v2-variant.schema.json",
        "vocacoes-pne-ui-v2-series.schema.json",
        "vocacoes_pne_job5i.py",
        "run_vocacoes_pne_v7_job5i.py",
        "test_vocacoes_pne_job5i.py",
        "vocacoes-pne-job5i-data.test.mjs",
        "vocacoes-pne-job5i-page.test.mjs",
        "vocacoes-pne-job5i-e2e.test.cjs",
    }
    implementation_files = []
    for root in implementation_roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if root.name == "vocacoes-pne-internal" or path.name in implementation_names:
                implementation_files.append(path)
    for path in (
        REPO_ROOT / "src" / "config" / "vocacoesPneInternalFlag.ts",
        REPO_ROOT / "src" / "app" / "appRoutes.ts",
        REPO_ROOT / "src" / "app" / "AppPageRouter.tsx",
        REPO_ROOT / "src" / "types" / "app.ts",
        REPO_ROOT / "src" / "styles" / "vocacoes-pne-internal.css",
    ):
        if path.is_file():
            implementation_files.append(path)
    manifest = {
        "schemaVersion": "vocacoes-pne-job5i-manifest-v1",
        "jobId": "v7-job5i",
        "generatedAt": GENERATED_AT,
        "finalState": "JOB_5I_READY_WITH_EXPLICIT_LIMITS_FOR_EXTERNAL_JUDGMENT",
        "gate11": "CLOSED",
        "publicationPerformed": False,
        "publicNarrativeAuthorized": False,
        "publicDataWritesPerformed": False,
        "networkUsed": False,
        "databaseUsed": False,
        "artifacts": [
            {
                "path": path.relative_to(OUTPUT_ROOT).as_posix(),
                "byteSize": path.stat().st_size,
                "sha256": _sha256(path),
            }
            for path in artifact_files
        ],
        "implementationFiles": [
            {
                "path": path.relative_to(REPO_ROOT).as_posix(),
                "byteSize": path.stat().st_size,
                "sha256": _sha256(path),
            }
            for path in sorted(set(implementation_files))
        ],
        "sourceProvenance": bundle["sourceRegistry"],
        "counts": bundle["counts"],
        "visualQa": {
            "result": observations["result"],
            "screenshotCount": len(coverage_rows),
        },
        "preservation": preservation,
        "explicitLimits": observations["remainingLimits"],
    }
    manifest_path = OUTPUT_ROOT / "MANIFEST_JOB5I.json"
    _promote_transactional({manifest_path: _json_bytes(manifest)})
    return manifest


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compila a camada UI V2 interna do Job 5I.")
    parser.add_argument("--check", action="store_true", help="Valida sem alterar artefatos.")
    parser.add_argument("--finalize", action="store_true", help="Fecha QA visual e manifesto final.")
    args = parser.parse_args(argv)
    if args.finalize:
        manifest = finalize_job5i()
        print(
            "OK: pacote Job 5I finalizado com "
            f"{len(manifest['artifacts'])} artefatos e Gate 11 fechado."
        )
        return 0
    result = compile_job5i(check=args.check)
    print(
        "OK: preflight e compilação UI V2 passaram; "
        f"{result['changed']} arquivo(s) alterado(s), "
        f"{result['bundle']['counts']['seriesCount']} séries."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
