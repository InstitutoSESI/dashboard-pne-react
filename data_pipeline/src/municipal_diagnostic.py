from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

from .pne.goal_indicator_contract import (
    CONTRACT,
    get_relation_context,
    get_relations_for_indicator,
)


SCHEMA_VERSION = "municipal-diagnostic-v2"
METHODOLOGY_VERSION = "municipal-diagnostic-p3c-v1"
ATTENTION_ORDER_METHOD = "legacy-relative-gap-v2"
EVIDENCE_METHODOLOGY_VERSION = "municipal-evidence-p3c-v1"
SELECTION_METHODOLOGY_VERSION = "municipal-decision-summary-p3c-v2"
EXPECTED_INDICATOR_COUNT = 54
STATE_EQUIVALENCE_TOLERANCE = 0.1
MINIMUM_STATE_COVERAGE_RATE = 0.8
MINIMUM_DISTRIBUTION_MUNICIPALITIES = 20
MINIMUM_PEER_MUNICIPALITIES = 20
TARGET_PEER_MUNICIPALITIES = 20
MAXIMUM_PEER_MUNICIPALITIES = 50
PEER_METHODOLOGY_VERSION = "municipal-peer-cohort-rs-v1"
INEQUALITY_PILOT_METHODOLOGY_VERSION = "municipal-inequality-p4b-v1"
INEQUALITY_PILOT_MINIMUM_CELL_SIZE = 10
GOVERNANCE_RULE_VERSION = "municipal-governance-p3c-v1"
EXPOSURE_RULE_VERSION = "municipal-network-exposure-p3b-v1"
TRAJECTORY_RULE_VERSION = "municipal-trajectory-p2-v1"
PNE_2026_CYCLE_ID = "pne_2026_2036"

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CATALOG_PATH = (
    REPO_ROOT / "src" / "data" / "diagnostic" / "indicatorCatalog.json"
)
PUBLIC_DIAGNOSTIC_CONFIG_PATH = (
    Path(__file__).resolve().parent / "data" / "pne2026_public_diagnostic_v1.json"
)

CATEGORY_ORDER = (
    "atendimento",
    "rendimento",
    "corpo_docente",
    "infraestrutura",
    "escolaridade_populacao",
)

CATEGORY_LABELS = {
    "atendimento": "Atendimento escolar",
    "rendimento": "Aprendizagem e desempenho",
    "corpo_docente": "Corpo docente",
    "infraestrutura": "Infraestrutura escolar",
    "escolaridade_populacao": "Escolaridade da população",
}

SOURCE_REGISTRY = {
    "ibge_censo_demografico_2010_2022": "IBGE — Censos Demográficos 2010 e 2022",
    "inep_censo_escolar": "INEP — Censo Escolar",
    "inep_saeb": "INEP — Saeb",
    "municipal_age_population_panel": "Base municipal de população por idade",
    "pipeline_alfabetizacao_provenance_pending": (
        "Fonte do indicador de alfabetização — proveniência pendente no pipeline"
    ),
    "pipeline_rendimento_professores_provenance_pending": (
        "Fonte do rendimento docente — proveniência pendente no pipeline"
    ),
}

LEGAL_VALIDATION = {
    "validationId": "pne-law-15388-2026-validation-v1",
    "validatedAt": "2026-07-19",
    "lawVersion": "Lei nº 15.388/2026 — texto vigente em 2026-07-19",
    "source": "https://www.planalto.gov.br/ccivil_03/_ato2023-2026/2026/lei/l15388.htm",
    "validatedGoalTexts": 73,
    "totalGoalTexts": 73,
}

MIXED_TERRITORIAL_BASIS_POLICY = (
    "allow_above_max_known_mixed_territorial_basis"
)
MIXED_TERRITORIAL_BASIS_NOTE = (
    "Indicador estimado com todas as matrículas localizadas no município e a "
    "população residente da faixa etária. Por mobilidade escolar e oferta "
    "regional, o resultado pode superar 100%."
)

SAEB_INDICATORS = {
    "saeb_matematica_anos_iniciais",
    "saeb_matematica_anos_finais",
    "saeb_matematica_ensino_medio",
    "saeb_portugues_anos_iniciais",
    "saeb_portugues_anos_finais",
    "saeb_portugues_ensino_medio",
}

SPECIAL_COMPARISON_BLOCKS = {
    "basico_15_17": {
        "code": "legacy_target_not_legal",
        "message": (
            "A referência legada de 85% não corresponde à universalização prevista "
            "na Meta 4.a; fórmula e alvo exigem correção formal."
        ),
        "status": "methodologically_incompatible",
        "dataStatus": "available",
    },
    "alfabetizacao": {
        "code": "applicable_milestone_pending",
        "message": (
            "O indicador ainda não seleciona de forma segura entre o marco de 80% "
            "em 2031 e o marco final de 100% em 2036."
        ),
        "status": "pending_official_definition",
        "dataStatus": "pending_official_definition",
    },
    "medio_tecnico_articulado_percentual": {
        "code": "incomplete_legal_numerator",
        "message": (
            "O numerador contém somente matrículas integradas; a meta legal inclui "
            "oferta integrada ou concomitante."
        ),
        "status": "methodologically_incompatible",
        "dataStatus": "methodologically_incompatible",
    },
    "fundamental_concluido_18_mais": {
        "code": "age_universe_proxy",
        "message": (
            "O indicador usa população de 18 anos ou mais, enquanto a referência "
            "legal usa população de 15 anos ou mais."
        ),
        "status": "methodologically_incompatible",
        "dataStatus": "available",
    },
    "aee": {
        "code": "ineligible_aee_denominator",
        "message": (
            "O denominador atual mede turmas de educação especial, não o público "
            "elegível ao atendimento educacional especializado."
        ),
        "status": "methodologically_incompatible",
        "dataStatus": "available",
    },
}


# ClassificaÃ§Ã£o explÃ­cita por indicador. O tema nÃ£o Ã© usado como atalho para
# atribuir responsabilidade institucional.
GOVERNANCE_CLASS_BY_INDICATOR = {
    "creche": "direct",
    "pre_escola": "direct",
    "basico_6_17": "shared",
    "basico_15_17": "state_led",
    "basico_integral": "shared",
    "escolas_integral": "shared",
    "aee": "shared",
    "eja_integrada_educacao_profissional_percentual": "shared",
    "medio_tecnico_articulado_percentual": "state_led",
    "medio_tecnico_participacao_publica": "state_led",
    "subsequente_expansao": "state_led",
    "alfabetizacao": "shared",
    "saeb_matematica_anos_iniciais": "shared",
    "saeb_matematica_anos_finais": "shared",
    "saeb_matematica_ensino_medio": "state_led",
    "saeb_portugues_anos_iniciais": "shared",
    "saeb_portugues_anos_finais": "shared",
    "saeb_portugues_ensino_medio": "state_led",
    "idade_regular_quinto": "shared",
    "idade_regular_nono": "shared",
    "idade_regular_medio": "state_led",
    "adequacao_ai": "shared",
    "adequacao_af": "shared",
    "adequacao_em": "state_led",
    "pos_graduacao": "shared",
    "rendimento_magisterio": "shared",
    "temporarios": "shared",
    "internet": "shared",
    "internet_alunos": "shared",
    "internet_aprendizagem": "shared",
    "internet_comunidade": "shared",
    "acesso_internet_computador": "shared",
    "acesso_internet_disp_pessoais": "shared",
    "rede_local": "shared",
    "rede_wireless": "shared",
    "banda_larga": "shared",
    "educacao_ambiental": "shared",
    "conselho_escolar": "shared",
    "proposta_pedagogica": "shared",
    "salas_climatizadas": "shared",
    "salas_acessiveis": "shared",
    "desktop_aluno": "shared",
    "comp_portatil_aluno": "shared",
    "tablet_aluno": "shared",
    "alfabetizacao_pop_15_mais": "territorial",
    "fundamental_concluido_18_mais": "territorial",
    "fundamental_concluido_15_29": "territorial",
    "medio_concluido_18_mais": "territorial",
    "medio_concluido_18_29": "territorial",
}


def _reason(code: str, message: str, *, source_field: str | None = None) -> dict[str, str]:
    value = {"code": code, "message": message}
    if source_field:
        value["sourceField"] = source_field
    return value


def _finite_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _integer(value: Any) -> int | None:
    number = _finite_number(value)
    return int(number) if number is not None else None


def load_indicator_catalog(path: Path | None = None) -> dict[str, Any]:
    catalog_path = path or DEFAULT_CATALOG_PATH
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    indicators = catalog.get("indicators", [])
    ids = [item.get("indicatorId") for item in indicators]
    expected_count = int(catalog.get("indicatorCount", EXPECTED_INDICATOR_COUNT))
    if expected_count != EXPECTED_INDICATOR_COUNT or len(indicators) != expected_count:
        raise ValueError(
            f"Catálogo deve conter {EXPECTED_INDICATOR_COUNT} indicadores; "
            f"encontrados {len(indicators)}."
        )
    if len(set(ids)) != len(ids) or any(not item_id for item_id in ids):
        raise ValueError("Catálogo contém identificadores ausentes ou duplicados.")
    return catalog


def load_pne_2026_public_diagnostic_config(
    path: Path | None = None,
) -> dict[str, Any]:
    config_path = path or PUBLIC_DIAGNOSTIC_CONFIG_PATH
    return json.loads(config_path.read_text(encoding="utf-8"))


def calculate_directional_distance(
    current_value: Any,
    target_value: Any,
    direction: str | None,
    *,
    comparison_allowed: bool = True,
    value_domain_status: str = "within_domain",
) -> dict[str, Any]:
    current = _finite_number(current_value)
    target = _finite_number(target_value)
    if not comparison_allowed:
        return {
            "goalAttained": None,
            "favorableDistance": None,
            "remainingGap": None,
        }
    if value_domain_status != "within_domain":
        return {
            "goalAttained": None,
            "favorableDistance": None,
            "remainingGap": None,
        }
    if current is None or target is None or direction not in {"at_least", "at_most"}:
        return {
            "goalAttained": None,
            "favorableDistance": None,
            "remainingGap": None,
        }

    favorable_distance = (
        current - target if direction == "at_least" else target - current
    )
    return {
        "goalAttained": favorable_distance >= 0,
        "favorableDistance": favorable_distance,
        "remainingGap": max(0.0, -favorable_distance),
    }


def calculate_state_favorable_difference(
    municipality_value: Any,
    state_value: Any,
    direction: str | None,
) -> float | None:
    municipality = _finite_number(municipality_value)
    state = _finite_number(state_value)
    if municipality is None or state is None:
        return None
    if direction == "at_least":
        return municipality - state
    if direction == "at_most":
        return state - municipality
    return None


def _quantile(sorted_values: Sequence[float], probability: float) -> float | None:
    if not sorted_values:
        return None
    if len(sorted_values) == 1:
        return float(sorted_values[0])
    position = (len(sorted_values) - 1) * probability
    lower_index = math.floor(position)
    upper_index = math.ceil(position)
    lower = float(sorted_values[lower_index])
    upper = float(sorted_values[upper_index])
    if lower_index == upper_index:
        return lower
    return lower + (upper - lower) * (position - lower_index)


def calculate_directional_percentile(
    values: Sequence[Any],
    municipality_value: Any,
    direction: str | None,
) -> float | None:
    current = _finite_number(municipality_value)
    valid_values = sorted(
        value
        for candidate in values
        if (value := _finite_number(candidate)) is not None
    )
    if current is None or not valid_values or direction not in {"at_least", "at_most"}:
        return None

    lower = sum(value < current for value in valid_values)
    higher = sum(value > current for value in valid_values)
    equal = len(valid_values) - lower - higher
    favorable_below = lower if direction == "at_least" else higher
    return 100.0 * (favorable_below + 0.5 * equal) / len(valid_values)


def _distribution_value_is_valid(
    value: Any,
    definition: Mapping[str, Any],
) -> bool:
    number = _finite_number(value)
    if number is None:
        return False
    valid_range = definition.get("validRange") or {}
    minimum = _finite_number(valid_range.get("minimum"))
    maximum = _finite_number(valid_range.get("maximum"))
    if minimum is not None and number < minimum:
        return False
    if maximum is not None and number > maximum:
        return definition.get("valueDomainPolicy") == MIXED_TERRITORIAL_BASIS_POLICY
    return True


def _coverage_rate(record: Mapping[str, Any]) -> float | None:
    rates = []
    for key in ("municipal_coverage_percent", "denominator_coverage_percent"):
        percentage = _finite_number(record.get(key))
        if percentage is not None:
            rates.append(max(0.0, min(1.0, percentage / 100.0)))
    if rates:
        return min(rates)
    valid = _finite_number(record.get("municipalities_valid"))
    expected = _finite_number(record.get("municipalities_expected"))
    if valid is not None and expected and expected > 0:
        return max(0.0, min(1.0, valid / expected))
    return None


def _municipal_series_by_year(
    result: Mapping[str, Any],
    definition: Mapping[str, Any],
) -> dict[int, float]:
    values: dict[int, float] = {}
    for point in result.get("series") or []:
        year = _integer(point.get("ano", point.get("year")))
        value = _finite_number(point.get("valor", point.get("value")))
        if (
            year is not None
            and value is not None
            and _distribution_value_is_valid(value, definition)
        ):
            values[year] = value

    end_year = _integer(result.get("end_year"))
    end_value = _finite_number(result.get("end_value"))
    if (
        end_year is not None
        and end_value is not None
        and _distribution_value_is_valid(end_value, definition)
    ):
        values[end_year] = end_value
    return values


def _detail_components_by_year(detail: Mapping[str, Any]) -> dict[int, Mapping[str, Any]]:
    by_cycle = detail.get("series_components_by_cycle") or {}
    series = by_cycle.get("pne_2026_2036") or detail.get("series_components") or []
    return {
        year: point
        for point in series
        if (year := _integer(point.get("ano", point.get("year")))) is not None
    }


def _detail_size_by_year(detail: Mapping[str, Any]) -> dict[int, float]:
    values: dict[int, float] = {}
    for year, point in _detail_components_by_year(detail).items():
        denominator = _finite_number(point.get("denominador", point.get("denominator")))
        if denominator is not None and denominator > 0:
            values[year] = denominator
    return values


def build_state_benchmark_registry(
    *,
    state_reference: Mapping[str, Any],
    municipal_results: Mapping[str, Mapping[str, Mapping[str, Any]]],
    municipal_details: Mapping[str, Mapping[str, Mapping[str, Any]]] | None = None,
    catalog: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Prepara referências e distribuições sem serializar valores de outros municípios."""

    resolved_catalog = dict(catalog or load_indicator_catalog())
    definitions = {
        definition["indicatorId"]: definition
        for definition in resolved_catalog.get("indicators", [])
    }
    state_indicators = state_reference.get("indicators") or {}
    expected_municipalities = _integer(state_reference.get("municipalities_expected"))
    if expected_municipalities is None:
        expected_municipalities = len(municipal_results)

    registry: dict[str, Any] = {}
    for indicator_id, definition in definitions.items():
        state_indicator = state_indicators.get(indicator_id) or {}
        compatibility = state_indicator.get("compatibility") or {}
        compatibility_valid = (
            state_indicator.get("indicator_id") == indicator_id
            and str(state_indicator.get("unit") or "percent")
            == str(definition.get("unit") or "percent")
            and compatibility.get("formulaStatus") == "curated_equivalent"
            and compatibility.get("yearRule") == "same_year_required"
            and compatibility.get("rangeStatus") == "curated_equivalent"
            and compatibility.get("stageStatus") == "curated_equivalent"
            and compatibility.get("universeStatus") == "curated_equivalent"
            and compatibility.get("administrativeDependenceStatus")
            == "registry_filters_required"
            and compatibility.get("aggregationRuleStatus")
            == "curated_equivalent"
            and compatibility.get("methodologyVersion")
            == state_indicator.get("methodology_version")
            and compatibility.get("territorialBasisStatus")
            == "curated_equivalent"
        )
        state_series = state_indicator.get("series") or []
        state_by_year = {
            year: record
            for record in state_series
            if (year := _integer(record.get("year"))) is not None
        }
        distribution_by_year: dict[int, list[float]] = {}
        peer_candidates_by_year: dict[int, list[dict[str, Any]]] = {}
        for municipality_name, results in municipal_results.items():
            result = results.get(indicator_id) or {}
            detail = (municipal_details or {}).get(municipality_name, {}).get(
                indicator_id, {}
            )
            size_by_year = _detail_size_by_year(detail)
            for year, value in _municipal_series_by_year(result, definition).items():
                distribution_by_year.setdefault(year, []).append(value)
                peer_candidates_by_year.setdefault(year, []).append(
                    {
                        "municipalityName": municipality_name,
                        "value": value,
                        "sizeValue": size_by_year.get(year),
                    }
                )

        years: dict[int, Any] = {}
        for year in sorted(set(state_by_year) | set(distribution_by_year)):
            values = sorted(distribution_by_year.get(year, []))
            years[year] = {
                "stateRecord": state_by_year.get(year),
                "distributionValues": values,
                "peerCandidates": peer_candidates_by_year.get(year, []),
                "distribution": {
                    "year": year,
                    "median": _quantile(values, 0.5),
                    "q1": _quantile(values, 0.25),
                    "q3": _quantile(values, 0.75),
                    "municipalityCount": len(values),
                    "coverageRate": (
                        len(values) / expected_municipalities
                        if expected_municipalities > 0
                        else None
                    ),
                },
            }

        registry[indicator_id] = {
            "indicatorId": indicator_id,
            "comparisonStatus": (
                state_indicator.get("comparison_status", "unavailable")
                if compatibility_valid
                else "methodology_pending"
            ),
            "method": state_indicator.get("aggregation_method"),
            "methodologyVersion": state_indicator.get("methodology_version"),
            "unit": definition.get("unit"),
            "compatibility": dict(compatibility),
            "years": years,
        }
    return registry


def _benchmark_unavailable(
    *,
    status: str,
    reason: Mapping[str, Any],
    year: int | None,
    method: str | None,
) -> dict[str, Any]:
    return {
        "state": {
            "status": status,
            "value": None,
            "year": year,
            "method": method,
            "coverageRate": None,
            "municipalityCount": None,
            "favorableDifference": None,
            "position": None,
            "reason": dict(reason),
        },
        "municipalDistribution": {
            "status": status,
            "year": year,
            "median": None,
            "q1": None,
            "q3": None,
            "performancePercentile": None,
            "municipalityCount": None,
            "coverageRate": None,
            "reason": dict(reason),
        },
    }


def _build_benchmarks(
    *,
    indicator_id: str,
    current_year: int | None,
    raw_value: float | None,
    direction: str | None,
    value_domain_status: str,
    municipal_series: Mapping[int, float],
    benchmark_registry: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if raw_value is None or current_year is None:
        return _benchmark_unavailable(
            status="unavailable",
            year=current_year,
            method=None,
            reason=_reason(
                "municipal_observation_unavailable",
                "Sem valor e ano municipais válidos, não há comparação estadual.",
            ),
        )
    if value_domain_status != "within_domain":
        return _benchmark_unavailable(
            status="unavailable",
            year=current_year,
            method=None,
            reason=_reason(
                "municipal_value_outside_domain",
                "O valor municipal está fora do domínio aceito para esta distribuição.",
            ),
        )

    entry = (benchmark_registry or {}).get(indicator_id)
    if not entry:
        return _benchmark_unavailable(
            status="unavailable",
            year=current_year,
            method=None,
            reason=_reason(
                "state_reference_not_loaded",
                "A referência estadual não foi carregada no pipeline municipal.",
            ),
        )

    method = entry.get("method")
    comparison_status = str(entry.get("comparisonStatus") or "unavailable")
    if comparison_status != "comparable":
        status = (
            "methodology_pending"
            if comparison_status == "methodology_pending"
            else "unavailable"
        )
        return _benchmark_unavailable(
            status=status,
            year=current_year,
            method=method,
            reason=_reason(
                "state_methodology_not_comparable",
                "A metodologia estadual ainda não é comparável à observação municipal.",
            ),
        )

    registry_years = entry.get("years") or {}
    benchmark_year = current_year
    benchmark_municipal_value = raw_value
    uses_latest_common_year = False
    year_entry = registry_years.get(current_year)
    current_state_record = (year_entry or {}).get("stateRecord") or {}
    current_state_is_comparable = (
        current_state_record.get("comparison_status") == "comparable"
        and _finite_number(current_state_record.get("value")) is not None
        and (_coverage_rate(current_state_record) or 0)
        >= MINIMUM_STATE_COVERAGE_RATE
    )
    if not current_state_is_comparable:
        common_years = []
        for year in municipal_series:
            candidate = registry_years.get(year) or {}
            state_candidate = candidate.get("stateRecord") or {}
            if (
                year <= current_year
                and state_candidate.get("comparison_status") == "comparable"
                and _finite_number(state_candidate.get("value")) is not None
                and (_coverage_rate(state_candidate) or 0) >= MINIMUM_STATE_COVERAGE_RATE
            ):
                common_years.append(year)
        if common_years:
            benchmark_year = max(common_years)
            benchmark_municipal_value = municipal_series[benchmark_year]
            year_entry = registry_years[benchmark_year]
            uses_latest_common_year = benchmark_year != current_year
        else:
            return _benchmark_unavailable(
                status="year_mismatch",
                year=current_year,
                method=method,
                reason=_reason(
                    "state_year_mismatch",
                    "Não existe último ano comum com referência estadual metodologicamente comparável.",
                ),
            )

    state_record = year_entry["stateRecord"]
    state_value = _finite_number(state_record.get("value"))
    state_status = str(state_record.get("comparison_status") or "unavailable")
    state_coverage = _coverage_rate(state_record)
    state_count = _integer(state_record.get("municipalities_valid"))
    if state_status != "comparable" or state_value is None:
        return _benchmark_unavailable(
            status=(
                "methodology_pending"
                if state_status == "methodology_pending"
                else "unavailable"
            ),
            year=benchmark_year,
            method=str(state_record.get("aggregation_method") or method or ""),
            reason=_reason(
                "state_value_unavailable",
                "O ponto estadual do mesmo ano não possui valor comparável.",
            ),
        )
    if state_coverage is None or state_coverage < MINIMUM_STATE_COVERAGE_RATE:
        return _benchmark_unavailable(
            status="insufficient_coverage",
            year=benchmark_year,
            method=str(state_record.get("aggregation_method") or method or ""),
            reason=_reason(
                "state_coverage_insufficient",
                "A cobertura do ponto estadual ficou abaixo do mínimo metodológico de 80%.",
            ),
        )

    distribution = dict(year_entry.get("distribution") or {})
    distribution_values = year_entry.get("distributionValues") or []
    distribution_count = int(distribution.get("municipalityCount") or 0)
    distribution_coverage = _finite_number(distribution.get("coverageRate"))
    distribution_available = (
        distribution_count >= MINIMUM_DISTRIBUTION_MUNICIPALITIES
        and distribution_coverage is not None
        and distribution_coverage >= MINIMUM_STATE_COVERAGE_RATE
    )

    favorable_difference = calculate_state_favorable_difference(
        benchmark_municipal_value, state_value, direction
    )
    if favorable_difference is None:
        position = "not_directional"
    elif abs(favorable_difference) <= STATE_EQUIVALENCE_TOLERANCE:
        position = "equivalent"
    elif favorable_difference > 0:
        position = "better"
    else:
        position = "worse"

    state_payload: dict[str, Any] = {
        "status": "comparable",
        "value": state_value,
        "year": benchmark_year,
        "municipalityValue": benchmark_municipal_value,
        "municipalityYear": benchmark_year,
        "municipalityLatestYear": current_year,
        "usesLatestCommonYear": uses_latest_common_year,
        "method": str(state_record.get("aggregation_method") or method or ""),
        "coverageRate": state_coverage,
        "municipalityCount": state_count,
        "favorableDifference": favorable_difference,
        "position": position,
    }
    if favorable_difference is None:
        state_payload["directionReason"] = _reason(
            "favorable_direction_unavailable",
            "O indicador não possui direção favorável declarada; a diferença direcional permanece nula.",
        )

    if not distribution_available:
        distribution_payload = {
            "status": "insufficient_coverage",
            "year": benchmark_year,
            "median": None,
            "q1": None,
            "q3": None,
            "performancePercentile": None,
            "municipalityCount": distribution_count,
            "coverageRate": distribution_coverage,
            "reason": _reason(
                "distribution_coverage_insufficient",
                "A distribuição municipal exige ao menos 20 municípios e cobertura de 80%.",
            ),
        }
    else:
        percentile = calculate_directional_percentile(
            distribution_values, benchmark_municipal_value, direction
        )
        distribution_payload = {
            "status": "available",
            "year": benchmark_year,
            "median": distribution.get("median"),
            "q1": distribution.get("q1"),
            "q3": distribution.get("q3"),
            "performancePercentile": percentile,
            "municipalityCount": distribution_count,
            "coverageRate": distribution_coverage,
        }
        if percentile is None:
            distribution_payload["directionReason"] = _reason(
                "performance_direction_unavailable",
                "A distribuição existe, mas o percentil de desempenho exige direção favorável declarada.",
            )

    return {
        "state": state_payload,
        "municipalDistribution": distribution_payload,
    }


def _select_trajectory_reference(
    *,
    definition: Mapping[str, Any],
    configured_reference: Mapping[str, Any],
    current_year: int | None,
    direction: str | None,
    comparison_status: str,
) -> dict[str, Any]:
    if comparison_status in {
        "methodologically_incompatible",
        "pending_official_definition",
        "outside_domain",
    }:
        return {
            "status": "pending",
            "year": None,
            "value": None,
            "direction": direction,
            "legalGoalRef": None,
        }

    applicable = []
    for milestone in definition.get("targets") or []:
        year = _integer(milestone.get("year"))
        value = _finite_number(milestone.get("value"))
        milestone_direction = milestone.get("direction", direction)
        if (
            year is not None
            and value is not None
            and milestone_direction == direction
            and milestone.get("validationStatus") == "official_law"
            and (current_year is None or year >= current_year)
        ):
            applicable.append((year, milestone, value))
    if applicable:
        _, milestone, value = min(applicable, key=lambda item: item[0])
        return {
            "status": "official",
            "year": _integer(milestone.get("year")),
            "value": value,
            "direction": direction,
            "legalGoalRef": milestone.get("legalGoalRef"),
        }

    value = _finite_number(configured_reference.get("value"))
    year = _integer(configured_reference.get("year"))
    if value is not None and direction in {"at_least", "at_most"}:
        return {
            "status": (
                "configured_planning_reference"
                if configured_reference.get("validationStatus") == "official_law"
                else "configured_unvalidated"
            ),
            "year": year,
            "value": value,
            "direction": direction,
            "legalGoalRef": None,
        }
    return {
        "status": "pending",
        "year": None,
        "value": None,
        "direction": direction,
        "legalGoalRef": None,
    }


def _projection_value_for_year(projection: Mapping[str, Any], year: int | None) -> float | None:
    if year is None:
        return None
    years = projection.get("years") or []
    values = projection.get("projected_percent") or projection.get(
        "projected_percent_raw"
    ) or []
    for candidate_year, value in zip(years, values):
        if _integer(candidate_year) == year:
            return _finite_number(value)
    return None


def _projected_achievement_year(
    points: Sequence[Mapping[str, Any]],
    *,
    target: float | None,
    direction: str | None,
) -> int | None:
    if target is None or direction not in {"at_least", "at_most"}:
        return None
    for point in points:
        year = _integer(point.get("year", point.get("ano")))
        value = _finite_number(
            point.get("rawValue", point.get("valor", point.get("value")))
        )
        if year is None or value is None:
            continue
        if (direction == "at_least" and value >= target) or (
            direction == "at_most" and value <= target
        ):
            return year
    return None


def _build_trajectory(
    *,
    definition: Mapping[str, Any],
    result: Mapping[str, Any],
    configured_reference: Mapping[str, Any],
    comparison_status: str,
    goal_attained: bool | None,
    remaining_gap: float | None,
    projections: Mapping[str, Any] | None,
    planning_scenarios: Mapping[str, Any] | None,
    allow_projection: bool = True,
) -> dict[str, Any]:
    indicator_id = str(definition["indicatorId"])
    current_year = _integer(result.get("end_year"))
    current_value = _finite_number(result.get("end_value"))
    direction = configured_reference.get("direction")
    reference = _select_trajectory_reference(
        definition=definition,
        configured_reference=configured_reference,
        current_year=current_year,
        direction=direction,
        comparison_status=comparison_status,
    )
    target_year = _integer(reference.get("year"))
    target_value = _finite_number(reference.get("value"))
    trend = result.get("trend") or {}
    slope = _finite_number(trend.get("slope"))
    observations = _integer(trend.get("observations")) or 0
    trend_status = str(trend.get("status") or "").lower()
    observed_pace = None
    if (
        slope is not None
        and observations >= 3
        and trend_status not in {"inconclusive", "unavailable"}
        and direction in {"at_least", "at_most"}
    ):
        observed_pace = slope if direction == "at_least" else -slope

    required_pace = None
    if goal_attained is True:
        required_pace = 0.0
    elif (
        remaining_gap is not None
        and current_year is not None
        and target_year is not None
        and target_year > current_year
    ):
        required_pace = remaining_gap / (target_year - current_year)

    if goal_attained is True:
        pace_status = "target_already_met"
    elif target_value is None or direction not in {"at_least", "at_most"}:
        pace_status = "not_applicable"
    elif trend_status == "inconclusive":
        pace_status = "inconclusive"
    elif observed_pace is None:
        pace_status = "insufficient_history"
    elif observed_pace < -1e-9:
        pace_status = "moving_away"
    elif abs(observed_pace) <= 1e-9:
        pace_status = "stable"
    elif required_pace is not None and observed_pace >= required_pace:
        pace_status = "sufficient"
    else:
        pace_status = "insufficient"

    projection = (projections or {}).get(indicator_id) or {}
    scenario = (planning_scenarios or {}).get(indicator_id) or {}
    scenario_type = "not_available"
    model = None
    horizon_year = None
    projected_value = None
    estimated_achievement_year = None
    quality = "not_assessed"
    warning_codes: list[str] = []
    source_codes = ["pne_trend"] if trend else []
    model_trend: dict[str, Any] | None = None
    denominator_model: dict[str, Any] | None = None
    uncertainty: dict[str, Any] = {
        "status": "not_estimated",
        "interval": None,
        "reason": (
            "O cenário é determinístico e não estima intervalo probabilístico."
        ),
        "interpretation": (
            "O resultado depende das premissas declaradas e não constitui "
            "previsão oficial."
        ),
    }

    if allow_projection and projection.get("available") is True:
        scenario_type = "trend_projection"
        model = str(projection.get("method") or "attendance_projection")
        horizon_year = _integer(
            projection.get("horizon_year", projection.get("target_year"))
        )
        projected_value = _projection_value_for_year(projection, target_year)
        if projected_value is None and target_year == horizon_year:
            projected_value = _finite_number(
                projection.get("projected_2036", projection.get("projected_2036_raw"))
            )
        points = [
            {"year": year, "rawValue": value}
            for year, value in zip(
                projection.get("years") or [],
                projection.get("projected_percent")
                or projection.get("projected_percent_raw")
                or [],
            )
        ]
        estimated_achievement_year = _projected_achievement_year(
            points, target=target_value, direction=direction
        )
        if isinstance(projection.get("trend"), Mapping):
            model_trend = dict(projection["trend"])
        if isinstance(projection.get("denominator_model"), Mapping):
            denominator_model = dict(projection["denominator_model"])
        if isinstance(projection.get("uncertainty"), Mapping):
            uncertainty = {
                **uncertainty,
                **dict(projection["uncertainty"]),
            }
        if model_trend and model_trend.get("diverges") is True:
            estimated_achievement_year = None
            warning_codes.append("attendance_projection_divergent_trends")
        quality = str(projection.get("quality") or "not_assessed")
        warning_codes.extend(
            f"attendance_projection_warning_{index + 1:02d}"
            for index, _ in enumerate(projection.get("warnings") or [])
        )
        source_codes.append("attendance_projection")
        if denominator_model:
            source_codes.append("population_projection")
    elif allow_projection and scenario.get("status") == "available":
        scenario_type = "component_maintenance"
        model = str(scenario.get("model") or "last_components")
        horizon_year = _integer((scenario.get("projectionPeriod") or {}).get("endYear"))
        projected_points = scenario.get("projected") or []
        point = next(
            (
                candidate
                for candidate in projected_points
                if _integer(candidate.get("year")) == target_year
            ),
            None,
        )
        projected_value = _finite_number(
            (point or {}).get("rawValue", (point or {}).get("displayValue"))
        )
        estimated_achievement_year = _projected_achievement_year(
            projected_points, target=target_value, direction=direction
        )
        quality = str(
            (scenario.get("qualityEvidence") or {}).get("provisionalLevel")
            or "not_assessed"
        )
        warning_codes.extend(
            f"maintenance_scenario_warning_{index + 1:02d}"
            for index, _ in enumerate((scenario.get("diagnostics") or {}).get("warnings") or [])
        )
        model_trend = {
            "method": model,
            "selectedBasis": "latest_observed_components_held_constant",
            "diverges": False,
        }
        denominator_model = {
            "method": model,
            "description": (
                "O cenário mantém os componentes mais recentes do numerador "
                "e do denominador, conforme o artefato de planejamento aprovado."
            ),
        }
        uncertainty["reason"] = (
            "O cenário de manutenção não estima intervalo probabilístico."
        )
        source_codes.append("approved_planning_scenario")
    elif allow_projection and target_value is not None and target_year is not None:
        scenario_type = "required_trajectory"
        model = "linear_required_pace"
        horizon_year = target_year
        projected_value = target_value
        uncertainty = {
            "status": "not_applicable",
            "interval": None,
            "reason": (
                "A trajetória representa o ritmo necessário até a referência, "
                "não uma projeção estatística."
            ),
            "interpretation": (
                "O valor informa esforço requerido e não probabilidade de alcance."
            ),
        }
        source_codes.append("legal_or_configured_reference")
    elif slope is not None and observations >= 3:
        scenario_type = "historical_trend_only"
        model = str(trend.get("method") or "theil_sen_v1")

    return {
        "status": "available" if current_value is not None else "not_available",
        "scenarioType": scenario_type,
        "model": model,
        "baseYear": current_year,
        "baseValue": current_value,
        "targetYear": target_year,
        "targetValue": target_value,
        "referenceStatus": reference["status"],
        "observedFavorableAnnualPace": observed_pace,
        "historyPointCount": observations,
        "requiredAnnualPace": required_pace,
        "paceStatus": pace_status,
        "horizonYear": horizon_year,
        "projectedValue": projected_value,
        "estimatedAchievementYear": estimated_achievement_year,
        "trendModel": model_trend,
        "denominatorModel": denominator_model,
        "uncertainty": uncertainty,
        "quality": quality,
        "sourceCodes": source_codes,
        "warningCodes": warning_codes,
        "ruleVersion": TRAJECTORY_RULE_VERSION,
    }


def _build_governance(
    indicator_id: str,
    exposure: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    classification = GOVERNANCE_CLASS_BY_INDICATOR.get(indicator_id, "informational")
    exposure_share = _finite_number(
        (exposure or {}).get("municipalDenominatorShare")
    )
    if (
        indicator_id in {"creche", "pre_escola"}
        and exposure_share is not None
        and exposure_share < 90.0
    ):
        classification = "shared"
    state_led = classification == "state_led"
    territorial = classification == "territorial"
    direct = classification == "direct"
    return {
        "classification": classification,
        "legalResponsibilityCodes": (
            ["municipality_early_childhood_priority", "common_education_duty"]
            if direct
            else ["state_secondary_priority", "common_education_duty"]
            if state_led
            else ["common_education_duty"]
        ),
        "operationalResponsibilityCodes": (
            ["municipal_network_execution"]
            if direct
            else ["state_network_lead", "municipal_coordination"]
            if state_led
            else ["territorial_multi_policy_coordination"]
            if territorial
            else ["network_specific_execution", "municipal_coordination"]
        ),
        "networkCodes": (
            ["municipal"] if direct else ["state", "municipal"] if state_led else ["municipal", "state", "federal"]
        ),
        "municipalActionCodes": (
            ["plan_and_execute_municipal_offer"]
            if direct
            else ["coordinate_access_and_pactuation"]
            if state_led or territorial
            else ["act_on_municipal_network", "coordinate_other_networks"]
        ),
        "pactuationRequired": not direct,
        "rationaleCode": (
            "municipal_exposure_indicates_mixed_offer"
            if indicator_id in {"creche", "pre_escola"}
            and exposure_share is not None
            and exposure_share < 90.0
            else f"governance_{classification}"
        ),
        "ruleVersion": GOVERNANCE_RULE_VERSION,
    }


def _build_municipal_exposure(
    detail: Mapping[str, Any], current_year: int | None
) -> dict[str, Any]:
    unavailable = {
        "status": "unavailable",
        "year": current_year,
        "municipalNumerator": None,
        "totalNumerator": None,
        "municipalDenominator": None,
        "totalDenominator": None,
        "municipalNumeratorShare": None,
        "municipalDenominatorShare": None,
        "reasonCode": "dependency_components_not_reconciled",
        "ruleVersion": EXPOSURE_RULE_VERSION,
    }
    if current_year is None:
        unavailable["reasonCode"] = "observation_year_unavailable"
        return unavailable
    rows = [
        row
        for row in detail.get("series_dependencia_components") or []
        if _integer(row.get("ano", row.get("year"))) == current_year
    ]
    if not rows:
        return unavailable
    municipal_row = next(
        (row for row in rows if row.get("dependencia") == "municipal"), None
    )
    if municipal_row is None:
        unavailable["reasonCode"] = "municipal_dependency_row_unavailable"
        return unavailable
    numerators = [_finite_number(row.get("numerador")) for row in rows]
    denominators = [_finite_number(row.get("denominador")) for row in rows]
    if any(value is None for value in numerators + denominators):
        unavailable["reasonCode"] = "dependency_component_contains_null"
        return unavailable
    total_numerator = sum(float(value) for value in numerators if value is not None)
    total_denominator = sum(float(value) for value in denominators if value is not None)
    municipal_numerator = _finite_number(municipal_row.get("numerador"))
    municipal_denominator = _finite_number(municipal_row.get("denominador"))
    overall = _detail_components_by_year(detail).get(current_year) or {}
    overall_numerator = _finite_number(overall.get("numerador"))
    overall_denominator = _finite_number(overall.get("denominador"))
    if (
        total_denominator <= 0
        or total_numerator < 0
        or municipal_numerator is None
        or municipal_denominator is None
        or overall_numerator is None
        or overall_denominator is None
        or abs(total_numerator - overall_numerator) > 1e-6
        or abs(total_denominator - overall_denominator) > 1e-6
    ):
        unavailable["reasonCode"] = "dependency_totals_do_not_reconcile"
        return unavailable
    return {
        "status": "available",
        "year": current_year,
        "municipalNumerator": municipal_numerator,
        "totalNumerator": total_numerator,
        "municipalDenominator": municipal_denominator,
        "totalDenominator": total_denominator,
        "municipalNumeratorShare": (
            100.0 * municipal_numerator / total_numerator
            if total_numerator > 0
            else 0.0
        ),
        "municipalDenominatorShare": 100.0 * municipal_denominator / total_denominator,
        "reasonCode": None,
        "ruleVersion": EXPOSURE_RULE_VERSION,
    }


def _build_similar_municipalities(
    *,
    indicator_id: str,
    municipality_name: str,
    current_year: int | None,
    raw_value: float | None,
    direction: str | None,
    detail: Mapping[str, Any],
    definition: Mapping[str, Any],
    comparison_status: str,
    benchmark_registry: Mapping[str, Any] | None,
) -> dict[str, Any]:
    base = {
        "status": "unavailable",
        "methodologyVersion": PEER_METHODOLOGY_VERSION,
        "indicatorId": indicator_id,
        "year": current_year,
        "cohortSize": 0,
        "members": [],
        "statistics": None,
        "performancePercentile": None,
        "coverageRate": None,
        "featuresUsed": [],
        "unavailableFeatureCodes": [
            "population",
            "rurality",
            "socioeconomic_level",
            "fiscal_capacity",
            "corede",
        ],
        "relaxationCodes": [],
        "reasonCode": "peer_inputs_unavailable",
    }
    if comparison_status != "eligible" or current_year is None or raw_value is None:
        base["reasonCode"] = "indicator_not_in_analyzed_universe"
        return base
    current_size = _detail_size_by_year(detail).get(current_year)
    entry = (benchmark_registry or {}).get(indicator_id) or {}
    year_entry = (entry.get("years") or {}).get(current_year) or {}
    all_candidates = year_entry.get("peerCandidates") or []
    candidates = [
        candidate
        for candidate in all_candidates
        if candidate.get("municipalityName") != municipality_name
        and _finite_number(candidate.get("value")) is not None
        and _finite_number(candidate.get("sizeValue")) is not None
        and _finite_number(candidate.get("sizeValue")) > 0
    ]
    if current_size is None or current_size <= 0:
        base["reasonCode"] = "municipal_offering_size_unavailable"
        return base
    if len(candidates) < MINIMUM_PEER_MUNICIPALITIES:
        base["reasonCode"] = "fewer_than_20_compatible_municipalities"
        base["coverageRate"] = (
            len(candidates) / max(1, len(all_candidates) - 1)
        )
        return base
    ranked = []
    for candidate in candidates:
        candidate_size = float(candidate["sizeValue"])
        distance = abs(math.log1p(candidate_size) - math.log1p(current_size))
        ranked.append((distance, str(candidate["municipalityName"]), candidate))
    ranked.sort(key=lambda item: (item[0], item[1]))
    selected = ranked[: min(TARGET_PEER_MUNICIPALITIES, MAXIMUM_PEER_MUNICIPALITIES)]
    values = sorted(float(item[2]["value"]) for item in selected)
    members = [
        {
            "municipalityName": name,
            "distance": round(distance, 6),
            "value": float(candidate["value"]),
            "offeringSize": float(candidate["sizeValue"]),
        }
        for distance, name, candidate in selected
    ]
    return {
        **base,
        "status": "available",
        "cohortSize": len(members),
        "members": members,
        "statistics": {
            "median": _quantile(values, 0.5),
            "q1": _quantile(values, 0.25),
            "q3": _quantile(values, 0.75),
        },
        "performancePercentile": calculate_directional_percentile(
            values, raw_value, direction
        ),
        "coverageRate": len(candidates) / max(1, len(all_candidates) - 1),
        "featuresUsed": ["offering_size"],
        "relaxationCodes": [
            "demographic_features_unavailable_use_offering_size_only"
        ],
        "compatibility": {
            "sameIndicator": True,
            "sameYear": True,
            "sameFormula": bool(definition.get("formula")),
            "sameUnit": True,
            "sameTerritorialBasis": True,
            "sameOfferBasis": True,
        },
        "reasonCode": None,
    }


def _build_evidence_level(
    *,
    raw_value: float | None,
    comparison_status: str,
    goal_attained: bool | None,
    legal_correspondence: str,
    operationalization_status: str,
    value_domain_status: str,
    trajectory: Mapping[str, Any],
    benchmarks: Mapping[str, Any],
    similar_municipalities: Mapping[str, Any],
    municipal_exposure: Mapping[str, Any],
) -> dict[str, Any]:
    blockers: list[str] = []
    if raw_value is None:
        blockers.append("DATA_UNAVAILABLE")
    if comparison_status == "methodologically_incompatible":
        blockers.append("METHODOLOGY_INCOMPATIBLE")
    elif comparison_status != "eligible":
        blockers.append("COMPARISON_NOT_ELIGIBLE")
    if operationalization_status == "proxy":
        blockers.append("PROXY_NOT_VALIDATED")
    elif operationalization_status == "informational":
        blockers.append("INFORMATIONAL_INDICATOR")
    if not value_domain_status.startswith("within_domain"):
        blockers.append("VALUE_DOMAIN_INCOMPATIBLE")

    if blockers:
        return {
            "level": "insufficient",
            "reasonCodes": list(dict.fromkeys(blockers))[:3],
            "methodologyVersion": EVIDENCE_METHODOLOGY_VERSION,
        }

    history_points = _integer(trajectory.get("historyPointCount")) or 0
    scenario_type = str(trajectory.get("scenarioType") or "not_available")
    scenario_quality = str(trajectory.get("quality") or "not_assessed").lower()
    state_available = (
        (benchmarks.get("state") or {}).get("status") == "comparable"
        and (benchmarks.get("state") or {}).get("position")
        in {"better", "worse", "equivalent"}
    )
    peers_available = similar_municipalities.get("status") == "available"
    exposure_available = municipal_exposure.get("status") == "available"
    scenario_available = scenario_type != "not_available"

    limitations: list[str] = []
    if legal_correspondence == "partial":
        limitations.append("LEGAL_CORRESPONDENCE_PARTIAL")
    if history_points < 3 and goal_attained is not True:
        limitations.append("INSUFFICIENT_HISTORY")
    if not scenario_available and goal_attained is not True:
        limitations.append("SCENARIO_UNAVAILABLE")
    if scenario_quality in {"low", "baixa"}:
        limitations.append("SCENARIO_QUALITY_LOW")

    positives: list[str] = []
    if state_available:
        positives.append("STATE_BENCHMARK_AVAILABLE")
    if peers_available:
        positives.append("PEER_BENCHMARK_AVAILABLE")
    if exposure_available:
        positives.append("MUNICIPAL_EXPOSURE_RECONCILED")
    if history_points >= 3:
        positives.append("SUFFICIENT_HISTORY")
    if scenario_available and scenario_quality not in {"low", "baixa"}:
        positives.append("SCENARIO_AVAILABLE")

    if (
        goal_attained is not True
        and (history_points < 3 or not scenario_available)
    ):
        level = "low"
    elif (
        legal_correspondence == "direct"
        and history_points >= 3
        and state_available
        and peers_available
        and scenario_available
        and scenario_quality not in {"low", "baixa"}
    ):
        level = "high"
    elif len(positives) >= 2:
        level = "medium"
    else:
        level = "low"

    ordered_reasons = (
        limitations + positives if level == "low" else limitations[:1] + positives
    )
    return {
        "level": level,
        "reasonCodes": list(dict.fromkeys(ordered_reasons))[:3],
        "methodologyVersion": EVIDENCE_METHODOLOGY_VERSION,
    }


def _decision_summary_collection(
    classification: str,
    governance: Mapping[str, Any],
    exposure: Mapping[str, Any],
) -> str:
    if classification == "municipal_direct_action":
        return "municipal_action"
    if classification == "municipal_action_with_coordination":
        municipal_share = _finite_number(exposure.get("municipalDenominatorShare"))
        if governance.get("classification") == "shared" and municipal_share is not None and municipal_share >= 50.0:
            return "municipal_action"
        return "coordination"
    if classification == "intergovernmental_coordination":
        return "coordination"
    if classification in {"investigate_data_or_supply", "insufficient_evidence"}:
        return "investigation"
    if classification == "preserve_result":
        return "preservation"
    return "monitoring"


def _build_decision_reading(
    *,
    comparison_status: str,
    goal_attained: bool | None,
    trajectory: Mapping[str, Any],
    governance: Mapping[str, Any],
    exposure: Mapping[str, Any],
    evidence: Mapping[str, Any],
) -> dict[str, Any]:
    reason_codes = []
    evidence_level = evidence.get("level")
    if evidence_level == "insufficient":
        classification = "insufficient_evidence"
        reason_codes.extend(evidence.get("reasonCodes") or [])
    elif evidence_level == "low":
        classification = "investigate_data_or_supply"
        reason_codes.extend(evidence.get("reasonCodes") or [])
    elif goal_attained is True and evidence_level == "high":
        classification = "preserve_result"
        reason_codes.append("quantitative_reference_attained")
    elif goal_attained is True:
        classification = "monitor"
        reason_codes.append("quantitative_reference_attained_with_caveats")
    elif comparison_status != "eligible" or goal_attained is not False:
        classification = "monitor"
        reason_codes.append("comparison_requires_monitoring")
    else:
        governance_class = governance.get("classification")
        if governance_class == "direct":
            classification = "municipal_direct_action"
        elif governance_class in {"state_led", "federal_led"}:
            classification = "intergovernmental_coordination"
        elif governance_class == "shared":
            classification = "municipal_action_with_coordination"
        elif governance_class == "territorial":
            classification = "intergovernmental_coordination"
        else:
            classification = "investigate_data_or_supply"
        reason_codes.append("comparable_gap")
    pace_status = trajectory.get("paceStatus")
    if pace_status in {"insufficient", "moving_away", "stable"}:
        reason_codes.append(f"pace_{pace_status}")
    elif pace_status == "insufficient_history":
        reason_codes.append("pace_insufficient_history")
    governance_class = governance.get("classification")
    if governance_class:
        reason_codes.append(f"governance_{governance_class}")
    if exposure.get("status") == "available":
        reason_codes.append("municipal_exposure_reconciled")
    summary_collection = _decision_summary_collection(
        classification, governance, exposure
    )
    return {
        "classification": classification,
        "reasonCodes": reason_codes[:3],
        "evidenceLevel": evidence_level,
        "summaryCollection": summary_collection,
        "financialEligibilityVerified": False,
        "changesAttentionOrder": False,
    }


def _display_value(
    raw_value: float | None,
    definition: Mapping[str, Any],
) -> float | None:
    if raw_value is None:
        return None
    if definition.get("displayPolicy") == "preserve_raw_value":
        return raw_value
    valid_range = definition.get("validRange") or {}
    minimum = _finite_number(valid_range.get("minimum"))
    maximum = _finite_number(valid_range.get("maximum"))
    display = raw_value
    if minimum is not None:
        display = max(minimum, display)
    if maximum is not None:
        display = min(maximum, display)
    return display


def _domain_status(
    indicator_id: str,
    raw_value: float | None,
    definition: Mapping[str, Any],
) -> tuple[str, str | None, list[dict[str, str]]]:
    if raw_value is None:
        return "not_applicable", None, []
    valid_range = definition.get("validRange") or {}
    minimum = _finite_number(valid_range.get("minimum"))
    maximum = _finite_number(valid_range.get("maximum"))
    below_minimum = minimum is not None and raw_value < minimum
    above_maximum = maximum is not None and raw_value > maximum
    domain_policy = str(definition.get("valueDomainPolicy") or "")

    if domain_policy == MIXED_TERRITORIAL_BASIS_POLICY and not below_minimum:
        flags = [
            _reason(
                "KNOWN_MIXED_TERRITORIAL_BASIS",
                MIXED_TERRITORIAL_BASIS_NOTE,
            )
        ]
        if above_maximum:
            flags.append(
                _reason(
                    "VALUE_ABOVE_100_ALLOWED_BY_METHOD",
                    "Valor acima de 100% válido segundo a definição operacional declarada.",
                )
            )
        return "within_domain", None, flags

    outside = below_minimum or above_maximum
    if not outside:
        return "within_domain", None, []
    if indicator_id == "pos_graduacao":
        return (
            "outside_domain_unverifiable",
            "unverifiable",
            [
                _reason(
                    "teacher_counts_require_reconciliation",
                    "Percentual docente acima de 100%; numerador, denominador e duplicidades precisam ser reconciliados.",
                )
            ],
        )
    return (
        "outside_domain_unverifiable",
        "unverifiable",
        [
            _reason(
                "value_outside_declared_domain",
                "O valor bruto está fora do domínio declarado e não possui regra oficial de tratamento.",
            )
        ],
    )


def _canonical_domain_status(
    raw_value: float | None,
    indicator: Mapping[str, Any],
) -> tuple[str, str | None, list[dict[str, str]]]:
    if raw_value is None:
        return "not_evaluated", None, []
    policy = CONTRACT["valuePolicies"][indicator["valuePolicyId"]]
    minimum = _finite_number(policy.get("expectedMinimum"))
    maximum = _finite_number(policy.get("expectedMaximum"))
    if minimum is not None and raw_value < minimum:
        return (
            "outside_domain_unverifiable",
            "unverifiable",
            [
                _reason(
                    "value_below_canonical_expected_minimum",
                    "O valor está abaixo do mínimo esperado pela política canônica.",
                    source_field="pne2026-goal-indicator-contract",
                )
            ],
        )
    flags: list[dict[str, str]] = []
    if maximum is not None and raw_value > maximum:
        flags.append(
            _reason(
                "value_above_canonical_expected_maximum",
                "O valor bruto foi preservado acima do máximo esperado e requer explicação.",
                source_field="pne2026-goal-indicator-contract",
            )
        )
    if indicator["conceptuallyMayExceed100"] and raw_value > 100:
        flags.append(
            _reason(
                "VALUE_ABOVE_100_ALLOWED_BY_METHOD",
                "Valor acima de 100% permitido pela política canônica do indicador.",
                source_field="pne2026-goal-indicator-contract",
            )
        )
    return "within_domain", None, flags


def _configured_reference(
    indicator_id: str,
    result: Mapping[str, Any],
    definition: Mapping[str, Any],
    null_reasons: dict[str, dict[str, str]],
    *,
    canonical_context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if canonical_context is not None:
        relation = canonical_context["relation"]
        legal_reference = canonical_context.get("legalReference") or {}
        milestone = legal_reference.get("milestone")
        if not relation["canDistance"] or milestone is None:
            reason = _reason(
                "canonical_reference_not_enabled",
                "O contrato canônico não autoriza referência quantitativa para esta relação.",
                source_field="pne2026-goal-indicator-contract",
            )
            null_reasons["configuredReference.value"] = reason
            null_reasons["configuredReference.year"] = reason
            null_reasons["configuredReference.direction"] = reason
            return {
                "value": None,
                "year": None,
                "direction": canonical_context["goal"]["direction"],
                "label": "Sem referência canônica aplicável",
                "kind": "not_applicable",
                "validationStatus": "not_applicable",
            }
        return {
            "value": _finite_number(milestone.get("value")),
            "year": _integer(milestone.get("year")),
            "direction": milestone.get("direction"),
            "label": str(canonical_context["goal"]["publicTitle"]),
            "kind": "official_law_reference",
            "validationStatus": legal_reference.get(
                "validationStatus", "official_law"
            ),
        }

    value = _finite_number(result.get("meta"))
    direction = result.get("direction") or definition.get("direction")
    milestones = definition.get("targets") or []
    matching_milestone = next(
        (
            milestone
            for milestone in milestones
            if _finite_number(milestone.get("value")) == value
            and milestone.get("direction", direction) == direction
        ),
        None,
    )
    year = _integer(matching_milestone.get("year")) if matching_milestone else None
    label = str(result.get("meta_label") or "Sem referência configurada")
    kind = "official_law_reference" if matching_milestone else "configured_reference"
    validation_status = (
        str(matching_milestone.get("validationStatus"))
        if matching_milestone
        else "configured_unvalidated"
    )

    if indicator_id == "basico_15_17" and value is not None:
        kind = "legacy_reference"
        validation_status = "legacy_not_legal_target"

    if value is None:
        null_reasons["configuredReference.value"] = _reason(
            "no_configured_reference",
            "O indicador não possui referência quantitativa configurada para comparação.",
            source_field="result.meta",
        )
    if year is None:
        null_reasons["configuredReference.year"] = _reason(
            "reference_year_not_resolved",
            "O ano da referência configurada não pôde ser associado de forma segura a um marco legal.",
            source_field="catalog.targets",
        )
    if direction not in {"at_least", "at_most"}:
        null_reasons["configuredReference.direction"] = _reason(
            "reference_direction_not_applicable",
            "Referência quantitativa sem direção aplicável.",
            source_field="catalog.direction",
        )

    return {
        "value": value,
        "year": year,
        "direction": direction,
        "label": label,
        "kind": kind,
        "validationStatus": validation_status,
    }


def _presentation_status(
    *,
    data_status: str,
    comparison_status: str,
    goal_attained: bool | None,
    operationalization_status: str,
) -> str:
    if data_status == "missing":
        return "missing"
    if data_status == "unverifiable":
        return "unverifiable"
    if comparison_status == "outside_domain":
        return "outside_domain"
    if operationalization_status == "proxy":
        return "proxy"
    if comparison_status == "pending_official_definition":
        return "pending_official_definition"
    if comparison_status == "methodologically_incompatible":
        return "methodologically_incompatible"
    if comparison_status == "not_applicable":
        return "informational"
    if goal_attained is True:
        return "goal_attained"
    if goal_attained is False:
        return "comparable_gap"
    return "unverifiable"


def _build_indicator(
    definition: Mapping[str, Any],
    result: Mapping[str, Any],
    catalog_index: int,
    benchmark_registry: Mapping[str, Any] | None = None,
    *,
    municipality_name: str,
    detail: Mapping[str, Any] | None = None,
    projections: Mapping[str, Any] | None = None,
    planning_scenarios: Mapping[str, Any] | None = None,
    cycle_id: str | None = None,
) -> dict[str, Any]:
    indicator_id = str(definition["indicatorId"])
    theme = str(definition["category"])
    current_year = _integer(result.get("end_year"))
    raw_value = _finite_number(result.get("end_value"))
    available = result.get("available") is True and raw_value is not None
    null_reasons: dict[str, dict[str, str]] = {}
    canonical_relations = (
        get_relations_for_indicator(indicator_id)
        if cycle_id == PNE_2026_CYCLE_ID
        else []
    )
    canonical_relation = (
        canonical_relations[0] if len(canonical_relations) == 1 else None
    )
    canonical_context = (
        get_relation_context(
            canonical_relation["goalId"],
            indicator_id,
            current_year,
        )
        if canonical_relation is not None
        else None
    )

    if current_year is None:
        null_reasons["currentYear"] = _reason(
            "current_year_unavailable",
            "Nenhuma observação municipal válida forneceu ano de referência.",
            source_field="result.end_year",
        )
    if raw_value is None:
        null_reasons["rawValue"] = _reason(
            "raw_value_unavailable",
            "Nenhuma observação municipal válida forneceu valor bruto; ausência não foi convertida em zero.",
            source_field="result.end_value",
        )
        null_reasons["displayValue"] = _reason(
            "display_value_unavailable",
            "Sem valor bruto, não existe valor numérico para apresentação.",
            source_field="rawValue",
        )

    if canonical_context is not None:
        domain_status, domain_data_status, domain_flags = (
            _canonical_domain_status(
                raw_value,
                canonical_context["indicator"],
            )
        )
    else:
        domain_status, domain_data_status, domain_flags = _domain_status(
            indicator_id, raw_value, definition
        )
    configured_reference = _configured_reference(
        indicator_id,
        result,
        definition,
        null_reasons,
        canonical_context=canonical_context,
    )
    direction = configured_reference.get("direction")
    if direction not in {"at_least", "at_most"}:
        direction = None
        null_reasons["direction"] = _reason(
            "direction_not_applicable",
            "Indicador informativo ou sem referência quantitativa aplicável.",
            source_field="configuredReference.direction",
        )

    if canonical_context is not None:
        relation = canonical_context["relation"]
        legal_goal_refs = [str(relation["goalId"])]
        legal_correspondence = (
            "direct" if relation["legacyCoverage"] == "direta" else "partial"
        )
        operationalization_status = legal_correspondence
    else:
        legal_goal_refs = [
            str(value) for value in definition.get("legalGoalRefs", [])
        ]
        legal_correspondence = str(
            definition.get("legalCorrespondence")
            or definition.get("correspondence")
            or "informational"
        )
        operationalization_status = str(
            definition.get("operationalizationStatus")
            or (
                legal_correspondence
                if legal_correspondence
                in {
                    "direct",
                    "partial",
                    "proxy",
                    "methodologically_incompatible",
                    "pending_official_definition",
                    "informational",
                }
                else "informational"
            )
        )

    data_status = "available" if available else "missing"
    if domain_data_status and available:
        data_status = domain_data_status

    exclusion_reasons: list[dict[str, str]] = []
    flags = [
        _reason(f"methodological_limit_{index + 1:02d}", str(message))
        for index, message in enumerate(definition.get("limits", []))
    ]
    flags.extend(domain_flags)
    if canonical_context is not None and canonical_context["relation"].get(
        "internalNote"
    ):
        flags.append(
            _reason(
                "canonical_relation_note",
                str(canonical_context["relation"]["internalNote"]),
                source_field="pne2026-goal-indicator-contract",
            )
        )

    comparison_status = "eligible"
    comparison_allowed = True
    if not available:
        comparison_status = "missing_data"
        comparison_allowed = False
        exclusion_reasons.append(
            _reason(
                "missing_observation",
                "Indicador sem resultado municipal disponível; o valor permanece nulo.",
            )
        )
    elif canonical_context is not None:
        relation = canonical_context["relation"]
        if domain_status != "within_domain":
            comparison_status = "outside_domain"
            comparison_allowed = False
            exclusion_reasons.append(
                (domain_flags[0] if domain_flags else None)
                or _reason(
                    "outside_domain",
                    "Valor fora do domínio declarado e sem regra oficial de tratamento.",
                )
            )
        elif (
            relation["mode"] != "progress"
            or not relation["canDistance"]
            or not relation["canStatus"]
        ):
            comparison_status = "not_applicable"
            comparison_allowed = False
            exclusion_reasons.append(
                _reason(
                    "canonical_relation_not_classifying",
                    "O contrato canônico não autoriza distância ou classificação para esta relação.",
                    source_field="pne2026-goal-indicator-contract",
                )
            )
        elif configured_reference["value"] is None or direction is None:
            comparison_status = "pending_official_definition"
            comparison_allowed = False
            exclusion_reasons.append(
                _reason(
                    "canonical_reference_unavailable",
                    "O contrato canônico não resolveu referência quantitativa aplicável.",
                    source_field="pne2026-goal-indicator-contract",
                )
            )
    elif indicator_id == "aee":
        block = SPECIAL_COMPARISON_BLOCKS[indicator_id]
        comparison_status = str(block["status"])
        comparison_allowed = False
        data_status = str(block["dataStatus"])
        exclusion_reasons.append(_reason(str(block["code"]), str(block["message"])))
    elif domain_status != "within_domain":
        comparison_status = "outside_domain"
        comparison_allowed = False
        exclusion_reasons.append(
            (domain_flags[0] if domain_flags else None)
            or _reason(
                "outside_domain",
                "Valor fora do domínio declarado e sem regra oficial de tratamento.",
            )
        )
    elif indicator_id in SAEB_INDICATORS:
        comparison_status = "methodologically_incompatible"
        comparison_allowed = False
        exclusion_reasons.append(
            _reason(
                "saeb_partial_dimension",
                "O valor principal representa apenas o nível adequado; a meta também exige o nível básico e não pode ser declarada globalmente atingida.",
            )
        )
    elif indicator_id in SPECIAL_COMPARISON_BLOCKS:
        block = SPECIAL_COMPARISON_BLOCKS[indicator_id]
        comparison_status = str(block["status"])
        comparison_allowed = False
        data_status = str(block["dataStatus"])
        exclusion_reasons.append(_reason(str(block["code"]), str(block["message"])))
    elif operationalization_status not in {"direct", "partial"}:
        comparison_status = "not_applicable"
        comparison_allowed = False
        exclusion_reasons.append(
            _reason(
                "operationalization_not_comparable",
                "A operacionalização é informativa, proxy ou ainda não comparável a uma referência legal.",
            )
        )
    elif legal_correspondence not in {"direct", "partial"}:
        comparison_status = "not_applicable"
        comparison_allowed = False
        exclusion_reasons.append(
            _reason(
                "legal_correspondence_not_comparable",
                "A correspondência legal não permite comparação quantitativa direta ou parcial.",
            )
        )
    elif configured_reference["value"] is None or direction is None:
        comparison_status = "pending_official_definition"
        comparison_allowed = False
        exclusion_reasons.append(
            _reason(
                "target_not_available",
                "Não existe alvo quantitativo e direção válidos para calcular distância.",
            )
        )

    distances = calculate_directional_distance(
        raw_value,
        configured_reference["value"],
        direction,
        comparison_allowed=comparison_allowed,
        value_domain_status=domain_status,
    )
    goal_attained = distances["goalAttained"]
    favorable_distance = distances["favorableDistance"]
    remaining_gap = distances["remainingGap"]

    if goal_attained is None:
        reason = exclusion_reasons[0] if exclusion_reasons else _reason(
            "comparison_unavailable", "Comparação indisponível."
        )
        null_reasons["goalAttained"] = reason
        null_reasons["favorableDistance"] = reason
        null_reasons["remainingGap"] = reason

    legacy_score = None
    if goal_attained is False:
        target = _finite_number(configured_reference["value"])
        if target is not None and target != 0 and remaining_gap is not None:
            legacy_score = remaining_gap / abs(target)
        else:
            exclusion_reasons.append(
                _reason(
                    "legacy_gap_score_unavailable",
                    "O alvo precisa ser finito e diferente de zero para a ordem transitória.",
                )
            )
    if legacy_score is None:
        null_reasons["legacyRelativeGapScore"] = _reason(
            "not_in_provisional_attention_order",
            "O indicador não integra a ordem provisória de atenção.",
        )
    null_reasons["priorityScore"] = _reason(
        "final_priority_deferred",
        "O escore aprofundado depende das etapas P2 a P6 e não é publicado nesta versão.",
    )

    if legal_correspondence == "partial" and comparison_allowed:
        flags.append(
            _reason(
                "partial_legal_correspondence",
                "A comparação representa somente a dimensão quantitativa declarada e não equivale ao cumprimento integral da meta legal.",
            )
        )

    display_value = _display_value(raw_value, definition)
    presentation: dict[str, Any] = {
        "statusCode": _presentation_status(
            data_status=data_status,
            comparison_status=comparison_status,
            goal_attained=goal_attained,
            operationalization_status=operationalization_status,
        )
    }
    source_ids = [
        str(value)
        for value in (
            canonical_context["indicator"]["sourceIds"]
            if canonical_context is not None
            else definition.get("sourceIds", [])
        )
    ]
    source: dict[str, Any] = {
        "sourceIds": source_ids,
        "labels": [SOURCE_REGISTRY.get(source_id, source_id) for source_id in source_ids],
        "periodicity": str(definition.get("periodicity") or "não declarada"),
    }
    if current_year is not None:
        source["latestYear"] = current_year

    benchmarks = _build_benchmarks(
        indicator_id=indicator_id,
        current_year=current_year,
        raw_value=raw_value,
        direction=direction,
        value_domain_status=domain_status,
        municipal_series=_municipal_series_by_year(result, definition),
        benchmark_registry=benchmark_registry,
    )
    resolved_detail = detail or {}
    trajectory = _build_trajectory(
        definition=definition,
        result=result,
        configured_reference=configured_reference,
        comparison_status=comparison_status,
        goal_attained=goal_attained,
        remaining_gap=remaining_gap,
        projections=projections,
        planning_scenarios=planning_scenarios,
        allow_projection=bool(
            canonical_context is None
            or canonical_context["relation"]["canProjection"]
        ),
    )
    municipal_exposure = _build_municipal_exposure(resolved_detail, current_year)
    governance = _build_governance(indicator_id, municipal_exposure)
    similar_municipalities = _build_similar_municipalities(
        indicator_id=indicator_id,
        municipality_name=municipality_name,
        current_year=current_year,
        raw_value=raw_value,
        direction=direction,
        detail=resolved_detail,
        definition=definition,
        comparison_status=comparison_status,
        benchmark_registry=benchmark_registry,
    )
    evidence = _build_evidence_level(
        raw_value=raw_value,
        comparison_status=comparison_status,
        goal_attained=goal_attained,
        legal_correspondence=legal_correspondence,
        operationalization_status=operationalization_status,
        value_domain_status=domain_status,
        trajectory=trajectory,
        benchmarks=benchmarks,
        similar_municipalities=similar_municipalities,
        municipal_exposure=municipal_exposure,
    )
    decision_reading = _build_decision_reading(
        comparison_status=comparison_status,
        goal_attained=goal_attained,
        trajectory=trajectory,
        governance=governance,
        exposure=municipal_exposure,
        evidence=evidence,
    )

    return {
        "indicatorId": indicator_id,
        "theme": theme,
        "themeLabel": CATEGORY_LABELS.get(theme, theme),
        "title": str(
            (
                canonical_context["relation"].get("publicLabelOverride")
                or canonical_context["indicator"]["publicTitle"]
            )
            if canonical_context is not None
            else definition.get("name") or indicator_id
        ),
        "currentYear": current_year,
        "rawValue": raw_value,
        "displayValue": display_value,
        "unit": str(definition.get("unit") or "percent"),
        "direction": direction,
        "dataStatus": data_status,
        "legalCorrespondence": legal_correspondence,
        "legalTextValidated": bool(legal_goal_refs),
        "legalValidation": {
            **LEGAL_VALIDATION,
            "status": "validated" if legal_goal_refs else "not_applicable",
            "legalGoalRefs": legal_goal_refs,
        },
        "operationalizationStatus": operationalization_status,
        "valueDomainStatus": domain_status,
        "targetComparisonStatus": comparison_status,
        "targetMilestones": (
            list(
                (canonical_context.get("legalReference") or {}).get(
                    "milestones", []
                )
            )
            if canonical_context is not None
            else list(definition.get("targets") or [])
        ),
        "configuredReference": configured_reference,
        "goalAttained": goal_attained,
        "favorableDistance": favorable_distance,
        "remainingGap": remaining_gap,
        "legacyRelativeGapScore": legacy_score,
        "priorityScore": None,
        "exclusionReasons": exclusion_reasons,
        "flags": flags,
        "source": source,
        "methodology": {
            "formula": str(definition.get("formula") or ""),
            "numerator": str(definition.get("numerator") or ""),
            "denominator": str(definition.get("denominator") or ""),
            "territorialBasis": dict(definition.get("territorialCut") or {}),
            "valueDomainPolicy": str(
                canonical_context["indicator"]["valuePolicyId"]
                if canonical_context is not None
                else definition.get("valueDomainPolicy") or ""
            ),
            **(
                {
                    "formulaId": canonical_context["indicator"]["formulaId"],
                    "implementationKey": CONTRACT["formulas"][
                        canonical_context["indicator"]["formulaId"]
                    ]["implementationKey"],
                    "contractTerritoriality": canonical_context["indicator"][
                        "territoriality"
                    ],
                }
                if canonical_context is not None
                else {}
            ),
            "displayPolicy": str(definition.get("displayPolicy") or ""),
        },
        "methodologyVersion": METHODOLOGY_VERSION,
        "benchmarks": benchmarks,
        "trajectory": trajectory,
        "governance": governance,
        "municipalExposure": municipal_exposure,
        "similarMunicipalities": similar_municipalities,
        "evidenceLevel": evidence["level"],
        "evidence": evidence,
        "decisionReading": decision_reading,
        "presentation": presentation,
        "nullReasons": null_reasons,
        "catalogOrder": catalog_index,
    }


def _scenario_is_below_reference(indicator: Mapping[str, Any]) -> bool:
    trajectory = indicator.get("trajectory") or {}
    if trajectory.get("scenarioType") not in {
        "trend_projection",
        "component_maintenance",
        "historical_trend_only",
    }:
        return False
    if (trajectory.get("trendModel") or {}).get("diverges") is True:
        return False
    if str(trajectory.get("quality") or "").lower() in {
        "baixa",
        "insuficiente",
        "not_assessed",
    }:
        return False
    projected = _finite_number(trajectory.get("projectedValue"))
    target = _finite_number((indicator.get("configuredReference") or {}).get("value"))
    if projected is None or target is None:
        return False
    direction = indicator.get("direction")
    return projected < target if direction == "at_least" else projected > target


def _additional_selection_evidence(indicator: Mapping[str, Any]) -> list[str]:
    trajectory = indicator.get("trajectory") or {}
    state = (indicator.get("benchmarks") or {}).get("state") or {}
    peers = indicator.get("similarMunicipalities") or {}
    exposure = indicator.get("municipalExposure") or {}
    codes: list[str] = []
    pace_status = trajectory.get("paceStatus")
    if pace_status == "moving_away":
        codes.append("PACE_MOVING_AWAY")
    elif pace_status == "insufficient":
        codes.append("PACE_INSUFFICIENT")
    elif pace_status == "stable":
        codes.append("TRAJECTORY_STABLE")
    if _scenario_is_below_reference(indicator):
        codes.append("SCENARIO_BELOW_REFERENCE")
    percentile = _finite_number(peers.get("performancePercentile"))
    if peers.get("status") == "available" and percentile is not None and percentile <= 25.0:
        codes.append("LOW_PEER_PERCENTILE")
    if state.get("status") == "comparable" and state.get("position") == "worse":
        codes.append("UNFAVORABLE_STATE_DIFFERENCE")
    exposure_share = max(
        (
            value
            for value in (
                _finite_number(exposure.get("municipalNumeratorShare")),
                _finite_number(exposure.get("municipalDenominatorShare")),
            )
            if value is not None
        ),
        default=None,
    )
    if exposure.get("status") == "available" and exposure_share is not None and exposure_share >= 50.0:
        codes.append("HIGH_MUNICIPAL_EXPOSURE")
    return codes


def _municipal_action_sort_key(indicator: Mapping[str, Any]) -> tuple[Any, ...]:
    trajectory = indicator.get("trajectory") or {}
    peers = indicator.get("similarMunicipalities") or {}
    state = (indicator.get("benchmarks") or {}).get("state") or {}
    exposure = indicator.get("municipalExposure") or {}
    pace = trajectory.get("paceStatus")
    percentile = _finite_number(peers.get("performancePercentile"))
    state_difference = (
        _finite_number(state.get("favorableDifference"))
        if state.get("status") == "comparable" and state.get("position") == "worse"
        else None
    )
    exposure_values = [
        value
        for value in (
            _finite_number(exposure.get("municipalNumeratorShare")),
            _finite_number(exposure.get("municipalDenominatorShare")),
        )
        if value is not None
    ]
    exposure_share = max(exposure_values) if exposure_values else None
    remaining_gap = _finite_number(indicator.get("remainingGap"))
    return (
        0 if pace == "moving_away" else 1,
        0 if pace == "insufficient" else 1,
        0 if _scenario_is_below_reference(indicator) else 1,
        percentile if percentile is not None else math.inf,
        state_difference if state_difference is not None else math.inf,
        -exposure_share if exposure_share is not None else math.inf,
        -remaining_gap if remaining_gap is not None else math.inf,
        str(indicator["indicatorId"]),
    )


def _coordination_sort_key(indicator: Mapping[str, Any]) -> tuple[Any, ...]:
    evidence_level = indicator.get("evidenceLevel")
    governance = (indicator.get("governance") or {}).get("classification")
    pace = (indicator.get("trajectory") or {}).get("paceStatus")
    peers = indicator.get("similarMunicipalities") or {}
    state = (indicator.get("benchmarks") or {}).get("state") or {}
    percentile = _finite_number(peers.get("performancePercentile"))
    state_difference = (
        _finite_number(state.get("favorableDifference"))
        if state.get("status") == "comparable" and state.get("position") == "worse"
        else None
    )
    remaining_gap = _finite_number(indicator.get("remainingGap"))
    return (
        0 if evidence_level == "high" else 1,
        {"shared": 0, "state_led": 1, "federal_led": 2}.get(str(governance), 3),
        {"moving_away": 0, "insufficient": 1, "stable": 2}.get(str(pace), 3),
        percentile if percentile is not None else math.inf,
        state_difference if state_difference is not None else math.inf,
        -remaining_gap if remaining_gap is not None else math.inf,
        str(indicator["indicatorId"]),
    )


def _decision_summary_reference(
    indicator: Mapping[str, Any],
    *,
    collection: str,
    position: int | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "indicatorId": indicator["indicatorId"],
        "theme": indicator["theme"],
        "collection": collection,
        "evidenceLevel": indicator["evidenceLevel"],
        "decisionClassification": indicator["decisionReading"]["classification"],
        "governanceClassification": indicator["governance"]["classification"],
        "selectionReasonCodes": _additional_selection_evidence(indicator)[:3]
        or list(indicator["evidence"]["reasonCodes"])[:3],
    }
    if position is not None:
        payload["selectionPosition"] = position
    return payload


def _build_decision_summary(
    indicators: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    by_collection: dict[str, list[Mapping[str, Any]]] = {
        "municipal_action": [],
        "coordination": [],
        "investigation": [],
        "monitoring": [],
        "preservation": [],
    }
    for indicator in indicators:
        collection = str(indicator["decisionReading"]["summaryCollection"])
        by_collection[collection].append(indicator)

    municipal_candidates = [
        indicator
        for indicator in by_collection["municipal_action"]
        if indicator["targetComparisonStatus"] == "eligible"
        and indicator["goalAttained"] is False
        and indicator["evidenceLevel"] in {"high", "medium"}
        and indicator["governance"]["classification"] in {"direct", "shared"}
        and indicator["decisionReading"]["classification"]
        in {"municipal_direct_action", "municipal_action_with_coordination"}
        and _additional_selection_evidence(indicator)
    ]
    municipal_candidates.sort(key=_municipal_action_sort_key)

    coordination_candidates = [
        indicator
        for indicator in by_collection["coordination"]
        if indicator["targetComparisonStatus"] == "eligible"
        and indicator["goalAttained"] is False
        and indicator["evidenceLevel"] in {"high", "medium"}
        and indicator["governance"]["classification"]
        in {"shared", "state_led", "federal_led"}
        and indicator["decisionReading"]["classification"]
        in {"municipal_action_with_coordination", "intergovernmental_coordination"}
    ]
    coordination_candidates.sort(key=_coordination_sort_key)

    return {
        "municipalActionCount": len(by_collection["municipal_action"]),
        "coordinationCount": len(by_collection["coordination"]),
        "investigationCount": len(by_collection["investigation"]),
        "monitoringCount": len(by_collection["monitoring"]),
        "preservationCount": len(by_collection["preservation"]),
        "municipalActionItems": [
            _decision_summary_reference(
                indicator, collection="municipal_action", position=position
            )
            for position, indicator in enumerate(municipal_candidates[:3], start=1)
        ],
        "coordinationItems": [
            _decision_summary_reference(
                indicator, collection="coordination", position=position
            )
            for position, indicator in enumerate(coordination_candidates[:2], start=1)
        ],
        "investigationItems": [
            _decision_summary_reference(indicator, collection="investigation")
            for indicator in by_collection["investigation"]
        ],
        "monitoringItems": [
            _decision_summary_reference(indicator, collection="monitoring")
            for indicator in by_collection["monitoring"]
        ],
        "preservationItems": [
            _decision_summary_reference(indicator, collection="preservation")
            for indicator in by_collection["preservation"]
        ],
        "selectionMethodologyVersion": SELECTION_METHODOLOGY_VERSION,
    }


def _theme_summary(
    theme: str,
    indicators: Sequence[Mapping[str, Any]],
    attention_items: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    theme_indicators = [item for item in indicators if item["theme"] == theme]
    theme_attention = [item for item in attention_items if item["theme"] == theme]
    valid_comparisons = [
        item for item in theme_indicators if item["targetComparisonStatus"] == "eligible"
    ]
    attained = [item for item in valid_comparisons if item["goalAttained"] is True]
    gaps = [item for item in valid_comparisons if item["goalAttained"] is False]
    available = [item for item in theme_indicators if item["rawValue"] is not None]
    excluded = [item for item in theme_indicators if item["targetComparisonStatus"] != "eligible"]
    decision_counts = {
        collection: sum(
            item["decisionReading"]["summaryCollection"] == collection
            for item in theme_indicators
        )
        for collection in (
            "municipal_action",
            "coordination",
            "investigation",
            "monitoring",
            "preservation",
        )
    }

    if not available:
        status_code = "no_data"
    elif not valid_comparisons:
        status_code = "no_comparable"
    elif gaps and attained:
        status_code = "mixed"
    elif gaps:
        status_code = "attention"
    else:
        status_code = "all_attained"

    payload: dict[str, Any] = {
        "theme": theme,
        "label": CATEGORY_LABELS.get(theme, theme),
        "totalIndicators": len(theme_indicators),
        "availableResults": len(available),
        "validLegalComparisons": len(valid_comparisons),
        "goalsAttained": len(attained),
        "comparableGaps": len(gaps),
        "excludedIndicators": len(excluded),
        "municipalActionIndicators": decision_counts["municipal_action"],
        "coordinationIndicators": decision_counts["coordination"],
        "investigationIndicators": decision_counts["investigation"],
        "monitoringIndicators": decision_counts["monitoring"],
        "preservationIndicators": decision_counts["preservation"],
        "statusCode": status_code,
    }
    if theme_attention:
        payload["focusIndicatorId"] = theme_attention[0]["indicatorId"]
    return payload


def _source_periods(indicators: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    periods: list[dict[str, Any]] = []
    source_ids = sorted(
        {
            source_id
            for indicator in indicators
            for source_id in indicator["source"]["sourceIds"]
        }
    )
    for source_id in source_ids:
        matching = [
            indicator
            for indicator in indicators
            if source_id in indicator["source"]["sourceIds"]
            and indicator["currentYear"] is not None
        ]
        if not matching:
            continue
        years = [int(indicator["currentYear"]) for indicator in matching]
        periods.append(
            {
                "sourceId": source_id,
                "label": SOURCE_REGISTRY.get(source_id, source_id),
                "minimumYear": min(years),
                "maximumYear": max(years),
                "indicatorIds": [indicator["indicatorId"] for indicator in matching],
            }
        )
    return periods


def _state_benchmark_summary(
    indicators: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    analyzed = [
        indicator
        for indicator in indicators
        if indicator["targetComparisonStatus"] == "eligible"
    ]
    comparable = [
        indicator
        for indicator in analyzed
        if indicator.get("benchmarks", {}).get("state", {}).get("status")
        == "comparable"
        and indicator.get("benchmarks", {}).get("state", {}).get("position")
        in {"better", "worse", "equivalent"}
    ]
    better = [
        indicator
        for indicator in comparable
        if indicator["benchmarks"]["state"]["position"] == "better"
    ]
    worse = [
        indicator
        for indicator in comparable
        if indicator["benchmarks"]["state"]["position"] == "worse"
    ]
    equivalent = [
        indicator
        for indicator in comparable
        if indicator["benchmarks"]["state"]["position"] == "equivalent"
    ]
    better.sort(
        key=lambda item: (
            -abs(float(item["benchmarks"]["state"]["favorableDifference"])),
            item["catalogOrder"],
        )
    )
    worse.sort(
        key=lambda item: (
            -abs(float(item["benchmarks"]["state"]["favorableDifference"])),
            item["catalogOrder"],
        )
    )
    return {
        "analyzedCount": len(analyzed),
        "eligibleAnalyzedCount": len(comparable),
        "betterCount": len(better),
        "worseCount": len(worse),
        "equivalentCount": len(equivalent),
        "unavailableCount": len(analyzed) - len(comparable),
        "largestUnfavorableIndicatorIds": [
            indicator["indicatorId"] for indicator in worse[:3]
        ],
        "largestFavorableIndicatorIds": [
            indicator["indicatorId"] for indicator in better[:2]
        ],
    }


def _state_benchmark_expanded_summary(
    indicators: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    analyzed = [indicator for indicator in indicators if indicator["rawValue"] is not None]
    comparable = [
        indicator
        for indicator in analyzed
        if indicator["benchmarks"]["state"]["status"] == "comparable"
        and indicator["benchmarks"]["state"]["position"]
        in {"better", "worse", "equivalent"}
    ]
    return {
        "analyzedCount": len(analyzed),
        "comparableCount": len(comparable),
        "unavailableCount": len(analyzed) - len(comparable),
        "universe": "all_available_municipal_results",
    }


def _inequality_number(value: Any) -> int | float | None:
    numeric = _finite_number(value)
    if numeric is None:
        return None
    return int(numeric) if numeric.is_integer() else numeric


def _empty_inequality_group(group_code: str, status: str) -> dict[str, Any]:
    return {
        "groupCode": group_code,
        "status": status,
        "publicationStatus": status,
        "year": None,
        "numerator": None,
        "denominator": None,
        "percentage": None,
        "coverage": "missing",
        "suppressionReasonCode": None,
    }


def build_urban_rural_integral_pilot(
    rows: Sequence[Mapping[str, Any]] | None,
) -> dict[str, Any]:
    """Build the isolated P4-B pilot from public-network location rows.

    The source already publishes the public-network aggregate. This builder never
    combines years, never imputes missing groups and applies complementary
    suppression whenever one location contains a small cell.
    """

    public_rows = [
        row
        for row in (rows or [])
        if str(row.get("dependencia") or "").strip().lower() == "publica"
        and str(row.get("localizacao") or "").strip().lower()
        in {"urbana", "rural"}
        and _finite_number(row.get("ano")) is not None
    ]
    available_years = sorted(
        {int(float(row["ano"])) for row in public_rows}, reverse=True
    )
    year = available_years[0] if available_years else None

    groups: list[dict[str, Any]] = []
    for group_code, source_code in (("urban", "urbana"), ("rural", "rural")):
        matching = [
            row
            for row in public_rows
            if int(float(row["ano"])) == year
            and str(row.get("localizacao") or "").strip().lower() == source_code
        ] if year is not None else []
        if not matching:
            group = _empty_inequality_group(group_code, "missing")
            group["year"] = year
            groups.append(group)
            continue
        if len(matching) != 1:
            group = _empty_inequality_group(group_code, "methodology_incompatible")
            group["year"] = year
            group["coverage"] = "municipality_public_network"
            groups.append(group)
            continue

        numerator = _inequality_number(matching[0].get("matriculas_integral"))
        denominator = _inequality_number(matching[0].get("matriculas"))
        if numerator is None or denominator is None:
            group = _empty_inequality_group(group_code, "missing")
            group["year"] = year
            groups.append(group)
            continue
        if denominator < 0 or numerator < 0 or numerator > denominator:
            group = _empty_inequality_group(group_code, "methodology_incompatible")
            group["year"] = year
            group["coverage"] = "municipality_public_network"
            groups.append(group)
            continue
        if denominator == 0:
            groups.append(
                {
                    "groupCode": group_code,
                    "status": "not_applicable",
                    "publicationStatus": "not_applicable",
                    "year": year,
                    "numerator": 0,
                    "denominator": 0,
                    "percentage": None,
                    "coverage": "municipality_public_network",
                    "suppressionReasonCode": None,
                }
            )
            continue

        complementary_count = denominator - numerator
        has_small_cell = (
            denominator < INEQUALITY_PILOT_MINIMUM_CELL_SIZE
            or 0 < numerator < INEQUALITY_PILOT_MINIMUM_CELL_SIZE
            or 0 < complementary_count < INEQUALITY_PILOT_MINIMUM_CELL_SIZE
        )
        if has_small_cell:
            group = _empty_inequality_group(group_code, "suppressed_small_cell")
            group["year"] = year
            group["coverage"] = "municipality_public_network"
            group["suppressionReasonCode"] = "small_cell"
            groups.append(group)
            continue

        groups.append(
            {
                "groupCode": group_code,
                "status": "available",
                "publicationStatus": "available",
                "year": year,
                "numerator": numerator,
                "denominator": denominator,
                "percentage": round(float(numerator) / float(denominator) * 100.0, 6),
                "coverage": "municipality_public_network",
                "suppressionReasonCode": None,
            }
        )

    if any(group["status"] == "suppressed_small_cell" for group in groups):
        for group in groups:
            if group["status"] in {"available", "not_applicable"}:
                group.update(
                    {
                        "status": "suppressed_small_cell",
                        "publicationStatus": "suppressed_small_cell",
                        "numerator": None,
                        "denominator": None,
                        "percentage": None,
                        "suppressionReasonCode": "complementary_suppression",
                    }
                )

    statuses = {group["status"] for group in groups}
    if "methodology_incompatible" in statuses:
        status = "methodology_incompatible"
    elif "suppressed_small_cell" in statuses:
        status = "suppressed_small_cell"
    elif "available" in statuses:
        status = "available"
    elif statuses == {"not_applicable"}:
        status = "not_applicable"
    else:
        status = "missing"

    group_by_code = {group["groupCode"]: group for group in groups}
    urban = group_by_code["urban"]
    rural = group_by_code["rural"]
    observed_difference = (
        round(float(urban["percentage"]) - float(rural["percentage"]), 6)
        if urban["status"] == rural["status"] == "available"
        else None
    )
    return {
        "status": status,
        "methodologyVersion": INEQUALITY_PILOT_METHODOLOGY_VERSION,
        "indicatorId": "basico_integral",
        "dimension": "urban_rural",
        "year": year,
        "universeCode": "public_basic_education_enrollments",
        "formulaCode": "integral_enrollments_over_eligible_enrollments",
        "minimumCellSize": INEQUALITY_PILOT_MINIMUM_CELL_SIZE,
        "observedDifferencePercentagePoints": observed_difference,
        "groups": groups,
    }


def _public_number(value: float) -> str:
    rounded = round(value, 1)
    formatted = f"{rounded:.1f}".rstrip("0").rstrip(".")
    return formatted.replace(".", ",")


def _public_unit_label(unit: str, value: float) -> str:
    if unit == "percent":
        return "ponto percentual" if abs(value) == 1 else "pontos percentuais"
    if unit == "years":
        return "ano" if abs(value) == 1 else "anos"
    return "unidade" if abs(value) == 1 else "unidades"


def _validate_public_directional_fields(indicator: Mapping[str, Any]) -> None:
    current = _finite_number(indicator.get("rawValue"))
    reference = indicator.get("configuredReference") or {}
    target = _finite_number(reference.get("value"))
    direction = indicator.get("direction")
    goal_attained = indicator.get("goalAttained")
    favorable = _finite_number(indicator.get("favorableDistance"))
    remaining = _finite_number(indicator.get("remainingGap"))
    if (
        current is None
        or target is None
        or direction not in {"at_least", "at_most"}
        or not isinstance(goal_attained, bool)
        or favorable is None
        or remaining is None
    ):
        return
    expected = calculate_directional_distance(current, target, str(direction))
    if (
        goal_attained is not expected["goalAttained"]
        or not math.isclose(
            favorable, float(expected["favorableDistance"]), abs_tol=1e-9
        )
        or not math.isclose(
            remaining, float(expected["remainingGap"]), abs_tol=1e-9
        )
    ):
        raise ValueError(
            "Campos direcionais divergentes no indicador "
            f"{indicator.get('indicatorId')}."
        )


def _public_target_reading(
    *,
    classification: str,
    favorable_difference: float,
    remaining_gap: float,
    direction: str,
    unit: str,
) -> str:
    if classification == "advance":
        value = _public_number(remaining_gap)
        unit_label = _public_unit_label(unit, remaining_gap)
        action = "reduzir o resultado até" if direction == "at_most" else "alcançar"
        return (
            f"Faltam {value} {unit_label} para {action} o valor previsto "
            "neste resultado."
        )
    if math.isclose(favorable_difference, 0.0, abs_tol=1e-9):
        return "O valor previsto neste resultado foi alcançado."
    value = _public_number(abs(favorable_difference))
    unit_label = _public_unit_label(unit, abs(favorable_difference))
    position = "abaixo" if direction == "at_most" else "acima"
    return (
        f"O resultado está {value} {unit_label} {position} do valor previsto "
        "para este resultado."
    )


def _public_state_comparison(
    indicator: Mapping[str, Any],
) -> dict[str, Any] | None:
    state = ((indicator.get("benchmarks") or {}).get("state") or {})
    if state.get("status") != "comparable":
        return None
    municipality_value = _finite_number(state.get("municipalityValue"))
    state_value = _finite_number(state.get("value"))
    year = _integer(state.get("year"))
    municipality_year = _integer(state.get("municipalityYear"))
    coverage = _finite_number(state.get("coverageRate"))
    direction = indicator.get("direction")
    method = str(state.get("method") or "")
    favorable = _finite_number(state.get("favorableDifference"))
    position = state.get("position")
    if (
        municipality_value is None
        or state_value is None
        or year is None
        or municipality_year != year
        or coverage is None
        or coverage < MINIMUM_STATE_COVERAGE_RATE
        or direction not in {"at_least", "at_most"}
        or not method
        or method == "not_available"
        or favorable is None
        or position not in {"better", "equivalent", "worse"}
    ):
        return None
    expected = calculate_state_favorable_difference(
        municipality_value, state_value, str(direction)
    )
    if expected is None or not math.isclose(favorable, expected, abs_tol=1e-9):
        raise ValueError(
            "Comparação estadual direcional divergente no indicador "
            f"{indicator.get('indicatorId')}."
        )
    expected_position = (
        "equivalent"
        if abs(expected) <= STATE_EQUIVALENCE_TOLERANCE
        else "better" if expected > 0 else "worse"
    )
    if position != expected_position:
        raise ValueError(
            "Posição estadual divergente no indicador "
            f"{indicator.get('indicatorId')}."
        )
    public_state = {
        "better": "above",
        "equivalent": "near",
        "worse": "below",
    }[str(position)]
    unit = str(indicator.get("unit") or "")
    if public_state == "near":
        reading = (
            "O resultado do município está próximo do resultado do Rio Grande "
            "do Sul."
        )
    else:
        value = _public_number(abs(favorable))
        unit_label = _public_unit_label(unit, abs(favorable))
        if direction == "at_least":
            numeric_position = "acima" if public_state == "above" else "abaixo"
            reading = (
                f"O resultado do município está {value} {unit_label} "
                f"{numeric_position} do resultado do Rio Grande do Sul."
            )
        elif public_state == "above":
            reading = (
                f"O resultado do município está {value} {unit_label} abaixo do "
                "valor do Rio Grande do Sul, em posição favorável."
            )
        else:
            reading = (
                f"O resultado do município está {value} {unit_label} acima do "
                "valor do Rio Grande do Sul e apresenta maior espaço para avançar."
            )
    return {
        "municipalityValue": municipality_value,
        "stateValue": state_value,
        "year": year,
        "favorableDifference": favorable,
        "state": public_state,
        "reading": reading,
    }


def _public_statewide_position(
    indicator: Mapping[str, Any],
) -> dict[str, str] | None:
    distribution = (
        (indicator.get("benchmarks") or {}).get("municipalDistribution") or {}
    )
    percentile = _finite_number(distribution.get("performancePercentile"))
    if (
        distribution.get("status") != "available"
        or percentile is None
        or percentile < 0
        or percentile > 100
    ):
        return None
    if percentile >= 75:
        return {
            "band": "top_quarter",
            "reading": (
                "O município está entre os 25% com resultados mais favoráveis "
                "do Rio Grande do Sul."
            ),
        }
    if percentile >= 25:
        return {
            "band": "middle",
            "reading": (
                "O resultado está na faixa intermediária entre os municípios "
                "do Rio Grande do Sul."
            ),
        }
    return {
        "band": "more_room_to_advance",
        "reading": (
            "O município está entre os que apresentam maior espaço para avançar "
            "neste resultado."
        ),
    }


def _public_similar_municipalities(
    indicator: Mapping[str, Any],
) -> dict[str, Any] | None:
    peers = indicator.get("similarMunicipalities") or {}
    compatibility = peers.get("compatibility") or {}
    required_compatibility = {
        "sameIndicator",
        "sameYear",
        "sameFormula",
        "sameUnit",
        "sameTerritorialBasis",
        "sameOfferBasis",
    }
    statistics = peers.get("statistics") or {}
    median = _finite_number(statistics.get("median"))
    current = _finite_number(indicator.get("rawValue"))
    year = _integer(peers.get("year"))
    direction = indicator.get("direction")
    if (
        peers.get("status") != "available"
        or peers.get("indicatorId") != indicator.get("indicatorId")
        or year != _integer(indicator.get("currentYear"))
        or median is None
        or current is None
        or direction not in {"at_least", "at_most"}
        or set(peers.get("featuresUsed") or []) != {"offering_size"}
        or not all(compatibility.get(key) is True for key in required_compatibility)
    ):
        return None
    favorable = calculate_state_favorable_difference(current, median, str(direction))
    if favorable is None:
        return None
    state = (
        "near"
        if abs(favorable) <= STATE_EQUIVALENCE_TOLERANCE
        else "above" if favorable > 0 else "below"
    )
    public_position = {
        "above": "acima",
        "near": "próximo",
        "below": "abaixo",
    }[state]
    return {
        "title": "Municípios com oferta educacional de tamanho semelhante",
        "median": median,
        "favorableDifference": favorable,
        "state": state,
        "reading": (
            "Entre municípios com oferta educacional de tamanho semelhante, "
            f"o resultado está {public_position} da mediana."
        ),
    }


def _public_trajectory(indicator: Mapping[str, Any]) -> dict[str, Any] | None:
    trajectory = indicator.get("trajectory") or {}
    pace = _finite_number(trajectory.get("observedFavorableAnnualPace"))
    scenario_type = str(trajectory.get("scenarioType") or "")
    if (
        indicator.get("targetComparisonStatus") != "eligible"
        or trajectory.get("status") != "available"
        or scenario_type not in {"component_maintenance", "trend_projection"}
        or str(trajectory.get("quality") or "not_assessed").lower()
        == "not_assessed"
        or pace is None
        or (_integer(trajectory.get("historyPointCount")) or 0) < 2
        or _finite_number(trajectory.get("projectedValue")) is None
    ):
        return None
    if pace > 1e-9:
        historical_state = "improved"
        historical_reading = "O resultado melhorou nos últimos anos."
    elif pace < -1e-9:
        historical_state = "declined"
        historical_reading = "O resultado recuou no período recente."
    else:
        historical_state = "stable"
        historical_reading = "O resultado permaneceu próximo do mesmo nível."
    trend_model = trajectory.get("trendModel") or {}
    selected_basis = str(trend_model.get("selectedBasis") or "")
    uses_municipal_state_trend = (
        selected_basis == "municipal_state_shrunk_theil_sen_log"
    )
    uses_state_enrollment_trend = (
        trajectory.get("model")
        == "state_aggregate_damped_holt_enrollment_with_state_age_denominator"
    )
    payload: dict[str, Any] = {
        "historicalState": historical_state,
        "historicalReading": historical_reading,
        "modelReading": (
            "Cenário modelado pela manutenção dos componentes observados mais recentes."
            if scenario_type == "component_maintenance"
            else (
                "Cenário que combina o histórico de matrículas do município e "
                "do Rio Grande do Sul com a evolução projetada da população."
                if uses_municipal_state_trend
                else (
                    "Cenário que parte do número mais recente de matrículas do "
                    "município, acompanha a evolução das matrículas no Rio "
                    "Grande do Sul e considera a evolução projetada da população."
                    if uses_state_enrollment_trend
                    else (
                        "Cenário que mantém o número mais recente de matrículas "
                        "e considera a evolução projetada da população."
                    )
                )
            )
        ),
        "denominatorReading": (
            "O denominador integra o cenário pelos componentes mais recentes aprovados."
            if scenario_type == "component_maintenance"
            else (
                "O denominador parte da população municipal observada e acompanha "
                "a variação etária projetada para o Rio Grande do Sul."
            )
        ),
    }
    if trend_model.get("diverges") is True:
        payload["uncertaintyReading"] = (
            "As evoluções recente e de longo prazo apontam direções opostas; "
            "o cenário deve ser lido com cautela e não divulga um ano exato de "
            "alcance. Não há intervalo probabilístico."
        )
    else:
        payload["uncertaintyReading"] = (
            "O teste retrospectivo cobre horizontes de um a cinco anos. O "
            "cenário não possui intervalo probabilístico até 2036 e não é uma "
            "previsão oficial."
        )
    estimated_year = _integer(trajectory.get("estimatedAchievementYear"))
    base_year = _integer(trajectory.get("baseYear"))
    if estimated_year is not None and (base_year is None or estimated_year >= base_year):
        payload["estimatedAchievementYear"] = estimated_year
        payload["achievementReading"] = (
            "No cenário modelado, o valor de referência seria alcançado em "
            f"{estimated_year}; esse ano não é uma previsão oficial."
        )
    return payload


def _combined_public_reading(
    classification: str, state_comparison: Mapping[str, Any] | None
) -> str:
    state = state_comparison.get("state") if state_comparison else None
    if classification == "maintain" and state in {"above", "near"}:
        return (
            "Resultado a manter. O valor previsto foi alcançado e o município "
            "está em posição favorável no Rio Grande do Sul."
        )
    if classification == "maintain" and state == "below":
        return (
            "O valor previsto foi alcançado. O resultado deve continuar sendo "
            "acompanhado em relação ao Rio Grande do Sul."
        )
    if classification == "advance" and state in {"above", "near"}:
        return (
            "Ponto para avançar. O valor previsto ainda não foi alcançado, embora "
            "o resultado esteja próximo ou acima do Rio Grande do Sul."
        )
    if classification == "advance" and state == "below":
        return (
            "Ponto para avançar. Há espaço para melhorar em relação à meta e ao "
            "resultado do Rio Grande do Sul."
        )
    if classification == "maintain":
        return "Resultado a manter. O valor previsto neste resultado foi alcançado."
    return "Ponto para avançar. O valor previsto neste resultado ainda não foi alcançado."


def _public_source_is_official(source: Mapping[str, Any]) -> bool:
    source_id = str(source.get("id") or "")
    official_url = str(source.get("officialUrl") or "")
    expected_prefix = {
        "inep_censo_escolar": "https://www.gov.br/inep/",
        "ibge_censo_demografico_2010_2022": "https://www.ibge.gov.br/",
    }.get(source_id)
    return bool(
        expected_prefix
        and official_url.startswith(expected_prefix)
        and source.get("organization")
        and source.get("publicTitle")
        and source.get("period")
    )


def _public_goal_sort_key(goal: Mapping[str, Any]) -> tuple[int, str]:
    goal_id = str(goal.get("goalId") or "")
    number, separator, letter = goal_id.partition(".")
    if not separator or not number.isdigit() or not letter.isalpha():
        raise ValueError(f"Identificador de meta pública inválido: {goal_id}")
    return int(number), letter.casefold()


def build_pne_2026_public_diagnostic(
    municipal_diagnostic_contract: Mapping[str, Any],
    *,
    config: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the closed presentation contract without mutating technical data."""

    resolved_config = dict(config or load_pne_2026_public_diagnostic_config())
    configured_goals = list(resolved_config.get("goals") or [])
    allowed_goal_ids = [str(goal["goalId"]) for goal in configured_goals]
    relationships = [
        (goal, relationship)
        for goal in configured_goals
        for relationship in goal.get("relationships") or []
    ]
    allowed_indicator_ids = [
        str(relationship["indicatorId"]) for _, relationship in relationships
    ]
    relationship_types = [
        str(relationship.get("relationship")) for _, relationship in relationships
    ]
    if (
        resolved_config.get("version") != "pne2026-public-diagnostic-v1"
        or resolved_config.get("cycleId") != "pne_2026_2036"
    ):
        raise ValueError("Versão ou ciclo público não reconhecido.")
    if len(allowed_goal_ids) != 24 or len(set(allowed_goal_ids)) != 24:
        raise ValueError("A configuração pública deve conter 24 metas únicas.")
    if len(allowed_indicator_ids) != 20 or len(set(allowed_indicator_ids)) != 20:
        raise ValueError("A configuração pública deve conter 20 indicadores únicos.")
    if (
        relationship_types.count("direct") != 11
        or relationship_types.count("partial_component") != 9
        or set(relationship_types) != {"direct", "partial_component"}
    ):
        raise ValueError(
            "A configuração pública deve conter 11 vínculos diretos e 9 parciais."
        )

    source_registry = {
        str(source["id"]): dict(source) for source in resolved_config.get("sources") or []
    }
    indicators = {
        str(indicator.get("indicatorId")): indicator
        for indicator in municipal_diagnostic_contract.get("indicators") or []
    }
    public_goals: list[dict[str, Any]] = []
    used_source_ids: list[str] = []

    for order, goal in enumerate(configured_goals, start=1):
        public_results: list[dict[str, Any]] = []
        for relationship in goal.get("relationships") or []:
            indicator_id = str(relationship["indicatorId"])
            indicator = indicators.get(indicator_id)
            if not indicator:
                continue
            _validate_public_directional_fields(indicator)
            current = _finite_number(indicator.get("rawValue"))
            current_year = _integer(indicator.get("currentYear"))
            unit = str(indicator.get("unit") or "")
            reference = indicator.get("configuredReference") or {}
            target = _finite_number(reference.get("value"))
            target_year = _integer(reference.get("year"))
            direction = indicator.get("direction")
            favorable = _finite_number(indicator.get("favorableDistance"))
            remaining = _finite_number(indicator.get("remainingGap"))
            goal_attained = indicator.get("goalAttained")
            source_ids = [
                str(source_id)
                for source_id in (indicator.get("source") or {}).get("sourceIds") or []
            ]
            sources_are_official = bool(source_ids) and all(
                source_id in source_registry
                and _public_source_is_official(source_registry[source_id])
                for source_id in source_ids
            )
            if (
                indicator.get("targetComparisonStatus") != "eligible"
                or current is None
                or current_year is None
                or unit not in {"percent", "index", "count", "years"}
                or not sources_are_official
                or target is None
                or target_year is None
                or direction not in {"at_least", "at_most"}
                or favorable is None
                or remaining is None
                or not isinstance(goal_attained, bool)
            ):
                continue
            classification = "maintain" if goal_attained else "advance"
            state_comparison = _public_state_comparison(indicator)
            result_payload: dict[str, Any] = {
                "indicatorId": indicator_id,
                "relationship": str(relationship["relationship"]),
                "theme": str(indicator.get("theme") or ""),
                "publicName": str(indicator.get("title") or indicator_id),
                "current": {
                    "value": current,
                    "displayValue": _finite_number(indicator.get("displayValue")),
                    "year": current_year,
                    "unit": unit,
                },
                "target": {
                    "value": target,
                    "displayValue": target,
                    "year": target_year,
                    "direction": direction,
                },
                "classification": classification,
                "targetReading": _public_target_reading(
                    classification=classification,
                    favorable_difference=favorable,
                    remaining_gap=remaining,
                    direction=str(direction),
                    unit=unit,
                ),
                "remainingGap": remaining,
                "favorableDifference": favorable,
                "publicReading": _combined_public_reading(
                    classification, state_comparison
                ),
                "sourceIds": source_ids,
            }
            if state_comparison is not None:
                result_payload["stateComparison"] = state_comparison
            statewide_position = _public_statewide_position(indicator)
            if statewide_position is not None:
                result_payload["statewidePosition"] = statewide_position
            similar = _public_similar_municipalities(indicator)
            if similar is not None:
                result_payload["similarMunicipalities"] = similar
            trajectory = _public_trajectory(indicator)
            if trajectory is not None:
                result_payload["trajectory"] = trajectory
            public_results.append(result_payload)
            for source_id in source_ids:
                if source_id not in used_source_ids:
                    used_source_ids.append(source_id)
        if not public_results:
            continue
        target_years = {result["target"]["year"] for result in public_results}
        public_goals.append(
            {
                "goalId": str(goal["goalId"]),
                "order": order,
                "publicTitle": str(goal["publicTitle"]),
                "publicDescription": str(goal["publicDescription"]),
                "targetYear": next(iter(target_years)) if len(target_years) == 1 else None,
                "results": public_results,
            }
        )

    flat_results = [
        result for goal in public_goals for result in goal.get("results") or []
    ]
    themes: list[dict[str, Any]] = []
    for result in flat_results:
        theme = result["theme"]
        existing = next((item for item in themes if item["theme"] == theme), None)
        if existing is None:
            existing = {
                "theme": theme,
                "publicTitle": CATEGORY_LABELS.get(theme, theme),
                "displayedResultsCount": 0,
                "maintainResultsCount": 0,
                "advanceResultsCount": 0,
                "goalIds": [],
            }
            themes.append(existing)
        existing["displayedResultsCount"] += 1
        existing[f"{result['classification']}ResultsCount"] += 1
        goal_id = next(
            goal["goalId"] for goal in public_goals if result in goal["results"]
        )
        if goal_id not in existing["goalIds"]:
            existing["goalIds"].append(goal_id)

    ordered_public_goals = sorted(public_goals, key=_public_goal_sort_key)
    for order, goal in enumerate(ordered_public_goals, start=1):
        goal["order"] = order

    return {
        "version": str(resolved_config["version"]),
        "cycleId": str(resolved_config["cycleId"]),
        "scope": {
            "allowedGoalIds": allowed_goal_ids,
            "allowedIndicatorIds": allowed_indicator_ids,
        },
        "summary": {
            "displayedResultsCount": len(flat_results),
            "reachedResultsCount": sum(
                result["classification"] == "maintain" for result in flat_results
            ),
            "advanceResultsCount": sum(
                result["classification"] == "advance" for result in flat_results
            ),
            "stateAboveOrNearCount": sum(
                result.get("stateComparison", {}).get("state") in {"above", "near"}
                for result in flat_results
            ),
            "stateBelowCount": sum(
                result.get("stateComparison", {}).get("state") == "below"
                for result in flat_results
            ),
        },
        "themes": themes,
        "goals": ordered_public_goals,
        "sources": [source_registry[source_id] for source_id in used_source_ids],
    }


def build_municipal_diagnostic_v2(
    *,
    municipality_name: str,
    results: Mapping[str, Mapping[str, Any]],
    generated_at: str,
    municipality_id: str | None = None,
    catalog: Mapping[str, Any] | None = None,
    benchmark_registry: Mapping[str, Any] | None = None,
    indicator_details: Mapping[str, Mapping[str, Any]] | None = None,
    projections: Mapping[str, Any] | None = None,
    planning_scenarios: Mapping[str, Any] | None = None,
    inequality_pilot_rows: Sequence[Mapping[str, Any]] | None = None,
    cycle_id: str | None = None,
) -> dict[str, Any]:
    resolved_catalog = dict(catalog or load_indicator_catalog())
    definitions = list(resolved_catalog.get("indicators", []))
    if len(definitions) != EXPECTED_INDICATOR_COUNT:
        raise ValueError(
            f"Contrato municipal exige {EXPECTED_INDICATOR_COUNT} indicadores."
        )

    indicators = [
        _build_indicator(
            definition,
            results.get(definition["indicatorId"], {}),
            index,
            benchmark_registry,
            municipality_name=municipality_name,
            detail=(indicator_details or {}).get(definition["indicatorId"], {}),
            projections=projections,
            planning_scenarios=planning_scenarios,
            cycle_id=cycle_id,
        )
        for index, definition in enumerate(definitions)
    ]

    attention_indicators = [
        indicator
        for indicator in indicators
        if indicator["goalAttained"] is False
        and indicator["legacyRelativeGapScore"] is not None
        and indicator["targetComparisonStatus"] == "eligible"
        and indicator["valueDomainStatus"] == "within_domain"
    ]
    attention_indicators.sort(
        key=lambda item: (-float(item["legacyRelativeGapScore"]), item["catalogOrder"])
    )
    attention_items = [
        {
            "indicatorId": indicator["indicatorId"],
            "theme": indicator["theme"],
            "rank": rank,
            "legacyRelativeGapScore": indicator["legacyRelativeGapScore"],
            "decisionReading": indicator["decisionReading"],
            "inclusionReasons": [
                _reason(
                    "eligible_comparable_gap",
                    "Dado dentro do domínio, comparação direta ou parcial elegível e lacuna remanescente disponível.",
                ),
                _reason(
                    "provisional_relative_gap_order",
                    "Ordem transitória calculada por remainingGap / abs(targetValue).",
                ),
            ],
        }
        for rank, indicator in enumerate(attention_indicators, start=1)
    ]

    preserved_indicators = [
        indicator
        for indicator in indicators
        if indicator["goalAttained"] is True
        and indicator["targetComparisonStatus"] == "eligible"
    ]
    preserved_items = [
        {
            "indicatorId": indicator["indicatorId"],
            "theme": indicator["theme"],
            "preservationReasons": [
                _reason(
                    "quantitative_reference_attained",
                    "O valor observado atinge a referência quantitativa comparável segundo a direção da meta.",
                )
            ],
        }
        for indicator in preserved_indicators
    ]

    excluded_indicators = [
        indicator
        for indicator in indicators
        if indicator["targetComparisonStatus"] != "eligible"
    ]
    excluded_items = [
        {
            "indicatorId": indicator["indicatorId"],
            "theme": indicator["theme"],
            "exclusionReasons": indicator["exclusionReasons"],
        }
        for indicator in excluded_indicators
    ]

    decision_summary = _build_decision_summary(indicators)
    themes = [
        _theme_summary(theme, indicators, attention_items)
        for theme in CATEGORY_ORDER
    ]
    outside_domain_ids = [
        indicator["indicatorId"]
        for indicator in indicators
        if indicator["valueDomainStatus"].startswith("outside_domain")
    ]
    mixed_territorial_basis_ids = [
        indicator["indicatorId"]
        for indicator in indicators
        if indicator["rawValue"] is not None
        and any(
            flag["code"] == "KNOWN_MIXED_TERRITORIAL_BASIS"
            for flag in indicator["flags"]
        )
    ]
    warnings = [
        {
            "code": "provisional_attention_order",
            "message": (
                "A ordem é transitória. A priorização aprofundada dependerá de trajetória, pares, governabilidade, desigualdade e qualidade da evidência."
            ),
            "indicatorIds": [item["indicatorId"] for item in attention_items],
        },
        {
            "code": "legal_text_not_operational_validation",
            "message": (
                "A validação dos 73 textos legais não valida automaticamente fórmulas, universos, alvos ou operacionalizações dos indicadores."
            ),
            "indicatorIds": [indicator["indicatorId"] for indicator in indicators],
        },
    ]
    if outside_domain_ids:
        warnings.append(
            {
                "code": "values_outside_domain",
                "message": (
                    "Valores brutos fora do domínio foram preservados e excluídos da ordem provisória; valores exibidos podem ser limitados apenas visualmente."
                ),
                "indicatorIds": outside_domain_ids,
            }
        )
    if mixed_territorial_basis_ids:
        warnings.append(
            {
                "code": "known_mixed_territorial_basis",
                "message": MIXED_TERRITORIAL_BASIS_NOTE,
                "indicatorIds": mixed_territorial_basis_ids,
            }
        )

    public_municipality_id = str(municipality_id or f"name:{municipality_name}")
    contract = {
        "schemaVersion": SCHEMA_VERSION,
        "methodologyVersion": METHODOLOGY_VERSION,
        "generatedAt": generated_at,
        "municipalityId": public_municipality_id,
        "municipalityName": municipality_name,
        "sourcePeriods": _source_periods(indicators),
        "summary": {
            "indicatorCount": len(indicators),
            "availableResults": sum(
                indicator["rawValue"] is not None for indicator in indicators
            ),
            "validLegalComparisons": len(attention_items) + len(preserved_items),
            "goalsAttained": len(preserved_items),
            "comparableGaps": len(attention_items),
            "excludedIndicators": len(excluded_items),
            "preservedIndicators": len(preserved_items),
            "themes": themes,
        },
        "stateBenchmarkSummary": _state_benchmark_summary(indicators),
        "stateBenchmarkExpandedSummary": _state_benchmark_expanded_summary(indicators),
        "decisionSummary": decision_summary,
        "inequalityPilot": build_urban_rural_integral_pilot(inequality_pilot_rows),
        "trajectoryScenarioInventory": {
            "attendance": [
                {
                    "indicatorId": indicator_id,
                    "scenarioType": "trend_projection",
                    "status": (
                        "available"
                        if scenario.get("available") is True
                        else "not_available"
                    ),
                }
                for indicator_id, scenario in (projections or {}).items()
            ],
            "maintenance": [
                {
                    "indicatorId": indicator_id,
                    "scenarioType": "component_maintenance",
                    "status": str(scenario.get("status") or "not_available"),
                }
                for indicator_id, scenario in (planning_scenarios or {}).items()
            ],
        },
        "indicators": [
            {key: value for key, value in indicator.items() if key != "catalogOrder"}
            for indicator in indicators
        ],
        "attentionItems": attention_items,
        "preservedItems": preserved_items,
        "excludedItems": excluded_items,
        "warnings": warnings,
        "generationMetadata": {
            "generator": "build_municipal_diagnostic_v2",
            "cycleContract": (
                "pne2026-goal-indicator-contract-v1"
                if cycle_id == PNE_2026_CYCLE_ID
                else "legacy-isolated"
            ),
            "catalogVersion": resolved_catalog.get("catalogVersion"),
            "attentionOrderingMethod": ATTENTION_ORDER_METHOD,
            "attentionOrderingStatus": "provisional",
            "deterministicIndicatorOrder": True,
            "deterministicTieBreak": "catalog_order",
            "municipalityIdentityStatus": (
                "official_id" if municipality_id else "name_fallback_pending_partition"
            ),
            "legacyFieldPreserved": False,
            "reactBusinessRulesAllowed": False,
            "finalPriorityScorePublished": False,
            "financialRecommendationPublished": False,
            "stateBenchmarkPublished": benchmark_registry is not None,
            "financingCatalogResolution": "global_versioned_catalogs",
            "decisionSummaryPublished": True,
            "decisionSummaryIsFinalRanking": False,
            "inequalityPilotPublished": inequality_pilot_rows is not None,
            "inequalityPilotAffectsDecisionSummary": False,
            "implementedSubstages": [
                "P2",
                "P3-A",
                "P3-B",
                "P3-C",
                "P4-A",
                "P4-B-pilot",
                "P5-A",
            ],
            "legalTextValidation": LEGAL_VALIDATION,
            "deferredStages": ["P4-remaining", "P5-B", "P6"],
        },
    }
    contract["pne2026PublicDiagnostic"] = build_pne_2026_public_diagnostic(contract)
    return contract


def apply_partitioned_municipality_id(
    contract: Mapping[str, Any], municipality_id: str | None
) -> dict[str, Any]:
    updated = dict(contract)
    metadata = dict(updated.get("generationMetadata") or {})
    if municipality_id:
        updated["municipalityId"] = str(municipality_id)
        metadata["municipalityIdentityStatus"] = "official_id"
    updated["generationMetadata"] = metadata
    return updated
