"""Contrato canônico meta×indicador do PNE 2026–2036.

Este módulo carrega, valida e consulta o JSON compartilhado com o frontend.
Metas, prazos, fórmulas declarativas e parâmetros operacionais publicados
partem desse contrato; os módulos de cálculo apenas implementam as operações.
"""

from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from typing import Any


CONTRACT_PATH = (
    Path(__file__).resolve().parents[3]
    / "contracts"
    / "pne2026-goal-indicator-contract.json"
)

RELATIONSHIP_MODES = frozenset(
    {"progress", "tracking", "complementary", "hidden"}
)
COMPARABLE_MODES = frozenset({"progress", "tracking"})
REFERENCE_KINDS = frozenset({"legal", "monitoring"})
CLASSIFYING_CAPABILITIES = ("canDistance", "canStatus", "canProjection")
PUBLIC_CAPABILITIES = ("includeInDiagnostic", "includeInReferenceSummary")
RELATION_ELIGIBILITY_FLAGS = ("includeInCycleGoalRefs",)
ATTENDANCE_RUNTIME_FORMULA_IDS = frozenset(
    {
        "formula.creche",
        "formula.pre_escola",
        "formula.basico_6_17",
        "formula.basico_15_17",
        "formula.basico_integral",
    }
)
ATTENDANCE_PROJECTION_FORMULA_IDS = frozenset(
    {
        "formula.creche",
        "formula.pre_escola",
        "formula.basico_6_17",
        "formula.basico_15_17",
    }
)
ATTENDANCE_NUMERATOR_MODELS = frozenset(
    {
        "last_observation_persistence",
        "state_aggregate_damped_holt",
        "municipal_state_shrunk_theil_sen_log",
    }
)


class Pne2026GoalIndicatorContractError(ValueError):
    """Erro estrutural ou referencial do contrato canônico."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise Pne2026GoalIndicatorContractError(
            f"Contrato PNE 2026–2036 inválido: {message}"
        )


def _validate_keyed_ids(
    collection: Any,
    label: str,
    id_field: str,
) -> None:
    _require(isinstance(collection, dict), f"{label} deve ser um objeto")
    for key, value in collection.items():
        _require(isinstance(value, dict), f"{label}.{key} deve ser um objeto")
        _require(
            value.get(id_field) == key,
            f"{label}.{key}.{id_field} deve coincidir com a chave",
        )


def validate_contract(candidate: dict[str, Any]) -> dict[str, Any]:
    """Valida esquema, referências cruzadas e invariantes metodológicas."""

    _require(
        candidate.get("schemaVersion") == "pne2026-goal-indicator-contract-v1",
        "schemaVersion não reconhecida",
    )
    _require(bool(candidate.get("contractVersion")), "contractVersion ausente")
    cycle = candidate.get("cycle") or {}
    _require(cycle.get("cycleId") == "pne_2026_2036", "cycleId inválido")
    _require(cycle.get("startYear") == 2026, "startYear deve ser 2026")
    _require(cycle.get("endYear") == 2036, "endYear deve ser 2036")

    for label, id_field in (
        ("goals", "goalId"),
        ("indicators", "indicatorId"),
        ("sources", "sourceId"),
        ("formulas", "formulaId"),
        ("valuePolicies", "valuePolicyId"),
        ("missingPolicies", "missingPolicyId"),
        ("projectionPolicies", "projectionPolicyId"),
        ("monitoringReferences", "referenceId"),
    ):
        _validate_keyed_ids(candidate.get(label), label, id_field)

    raw_relations = candidate.get("relations")
    _require(
        isinstance(raw_relations, list),
        "relations deve ser uma lista ordenada",
    )
    relation_ids: set[str] = set()
    for relation in raw_relations:
        _require(isinstance(relation, dict), "cada relação deve ser um objeto")
        relation_id = relation.get("relationId")
        _require(
            isinstance(relation_id, str),
            "cada relação deve declarar relationId",
        )
        _require(
            relation_id not in relation_ids,
            f"relationId duplicado: {relation_id}",
        )
        relation_ids.add(relation_id)

    goals = candidate["goals"]
    indicators = candidate["indicators"]
    relations = candidate["relations"]
    sources = candidate["sources"]
    formulas = candidate["formulas"]
    value_policies = candidate["valuePolicies"]
    missing_policies = candidate["missingPolicies"]
    projection_policies = candidate["projectionPolicies"]
    monitoring_references = candidate["monitoringReferences"]

    attendance_projection_policy = projection_policies.get(
        "attendance_backtested_hybrid_minimum_five_consecutive"
    ) or {}
    _require(
        attendance_projection_policy.get("selectionMetric")
        == (
            "100_abs_predicted_minus_observed_numerator_over_"
            "observed_target_population"
        ),
        "política de projeção deve declarar a métrica bruta de seleção",
    )
    _require(
        attendance_projection_policy.get(
            "selectionAndValidationValuePolicy"
        )
        == "raw_without_display_cap",
        "seleção e validação de projeções devem usar valores brutos",
    )
    _require(
        attendance_projection_policy.get("displayPolicy")
        == "cap_at_100_preserve_raw_for_audit",
        "teto de 100% deve ser exclusivamente uma política de apresentação",
    )

    _require(len(goals) == 73, "o ciclo deve conter exatamente 73 metas legais")

    references: dict[str, tuple[str, dict[str, Any]]] = {}
    for goal_id, goal in goals.items():
        _require(
            isinstance(goal.get("legalOrder"), int) and goal["legalOrder"] > 0,
            f"goals.{goal_id}.legalOrder inválida",
        )
        _require(
            goal.get("legalSourceId") in sources,
            f"goals.{goal_id}.legalSourceId inexistente",
        )
        for reference in goal.get("legalReferences", []):
            reference_id = reference.get("referenceId")
            _require(
                isinstance(reference_id, str) and reference_id not in references,
                f"referência legal duplicada em {goal_id}",
            )
            milestones = reference.get("milestones")
            _require(
                isinstance(milestones, list) and bool(milestones),
                f"{reference_id} sem marcos",
            )
            milestone_keys: set[tuple[int, str]] = set()
            for milestone in milestones:
                year = milestone.get("year")
                _require(
                    isinstance(year, int),
                    f"{reference_id} tem marco com ano inválido",
                )
                _require(
                    (year, milestone.get("dimension", "overall"))
                    not in milestone_keys,
                    (
                        f"{reference_id}:{year}:"
                        f"{milestone.get('dimension', 'overall')} está duplicado"
                    ),
                )
                _require(
                    milestone.get("unit") == reference.get("unit"),
                    f"{reference_id}:{year} tem unidade incompatível",
                )
                milestone_keys.add(
                    (year, milestone.get("dimension", "overall"))
                )
            references[reference_id] = (goal_id, reference)

    for indicator_id, indicator in indicators.items():
        _require(
            indicator.get("formulaId") in formulas,
            f"indicators.{indicator_id}.formulaId inexistente",
        )
        _require(
            indicator.get("valuePolicyId") in value_policies,
            f"indicators.{indicator_id}.valuePolicyId inexistente",
        )
        _require(
            indicator.get("missingPolicyId") in missing_policies,
            f"indicators.{indicator_id}.missingPolicyId inexistente",
        )
        source_ids = indicator.get("sourceIds")
        _require(
            isinstance(source_ids, list) and bool(source_ids),
            f"indicators.{indicator_id}.sourceIds vazio",
        )
        for source_id in source_ids:
            _require(
                source_id in sources,
                f"indicators.{indicator_id} referencia fonte inexistente {source_id}",
            )

    for formula_id, formula in formulas.items():
        _require(
            bool(formula.get("implementationKey")),
            f"formulas.{formula_id}.implementationKey ausente",
        )
        _require(
            formula.get("status")
            in {"registered_existing", "blocked_pending_methodology"},
            f"formulas.{formula_id}.status não reconhecido",
        )
        if formula_id.endswith(".v2"):
            for field in (
                "description",
                "sourceId",
                "universe",
                "numerator",
                "denominator",
                "zeroPolicy",
                "missingPolicy",
                "negativePolicy",
                "above100Policy",
                "statePolicy",
            ):
                _require(
                    bool(formula.get(field)),
                    f"formulas.{formula_id}.{field} ausente",
                )
            _require(
                formula["sourceId"] in sources,
                f"formulas.{formula_id}.sourceId inexistente",
            )
            _require(
                isinstance(formula.get("catalogProjection"), dict),
                f"formulas.{formula_id}.catalogProjection ausente",
            )
        if formula_id in ATTENDANCE_RUNTIME_FORMULA_IDS:
            runtime = formula.get("runtime")
            _require(
                isinstance(runtime, dict),
                f"formulas.{formula_id}.runtime ausente",
            )
            for field in (
                "strategy",
                "loaderKey",
                "numeratorField",
                "denominatorField",
                "denominatorAggregation",
            ):
                _require(
                    bool(runtime.get(field)),
                    f"formulas.{formula_id}.runtime.{field} ausente",
                )
            _require(
                isinstance(formula.get("catalogProjection"), dict),
                f"formulas.{formula_id}.catalogProjection ausente",
            )
            if formula_id in ATTENDANCE_PROJECTION_FORMULA_IDS:
                projection = runtime.get("projection")
                _require(
                    isinstance(projection, dict),
                    f"formulas.{formula_id}.runtime.projection ausente",
                )
                _require(
                    projection.get("numeratorModel")
                    in ATTENDANCE_NUMERATOR_MODELS,
                    (
                        f"formulas.{formula_id}.runtime.projection."
                        "numeratorModel inválido"
                    ),
                )
                _require(
                    projection.get("denominatorModel")
                    == "municipal_base_times_rs_age_factor",
                    (
                        f"formulas.{formula_id}.runtime.projection."
                        "denominatorModel inválido"
                    ),
                )
                _require(
                    projection.get("minimumComparableObservations") == 5,
                    (
                        f"formulas.{formula_id}.runtime.projection."
                        "minimumComparableObservations deve ser 5"
                    ),
                )
                _require(
                    projection.get("requiredObservationIntervalYears") == 1,
                    (
                        f"formulas.{formula_id}.runtime.projection."
                        "requiredObservationIntervalYears deve ser 1"
                    ),
                )
                if (
                    projection.get("numeratorModel")
                    == "municipal_state_shrunk_theil_sen_log"
                ):
                    parameters = projection.get("parameters")
                    _require(
                        isinstance(parameters, dict),
                        (
                            f"formulas.{formula_id}.runtime.projection."
                            "parameters ausente"
                        ),
                    )
                    _require(
                        parameters.get("historyStartYear") == 2014,
                        f"formulas.{formula_id}: historyStartYear deve ser 2014",
                    )
                    _require(
                        parameters.get("windowObservations") in {5, 8},
                        f"formulas.{formula_id}: janela inválida",
                    )
                    _require(
                        parameters.get("damping") == 0.8,
                        f"formulas.{formula_id}: damping deve ser 0.8",
                    )
                    _require(
                        parameters.get("shrinkage") == 4,
                        f"formulas.{formula_id}: shrinkage deve ser 4",
                    )
                    _require(
                        parameters.get("excludedYears") == [],
                        f"formulas.{formula_id}: excludedYears deve ser vazio",
                    )
                    _require(
                        parameters.get("maximumAbsoluteAnnualLogTrend") == 0.15,
                        f"formulas.{formula_id}: limite de tendência inválido",
                    )

    for source_id, source in sources.items():
        _require(bool(source.get("kind")), f"sources.{source_id}.kind ausente")
        _require(
            bool(source.get("publicTitle")),
            f"sources.{source_id}.publicTitle ausente",
        )
        lineage = source.get("lineage")
        if lineage is not None:
            _require(
                isinstance(lineage, dict) and bool(lineage),
                f"sources.{source_id}.lineage inválida",
            )
            _require(
                bool(source.get("officialUrl")),
                f"sources.{source_id}.officialUrl ausente para fonte com linhagem",
            )
            serialized_lineage = json.dumps(lineage, ensure_ascii=False)
            _require(
                not any(
                    marker in serialized_lineage
                    for marker in ("C:\\\\Users\\\\", "C:/Users/", "/home/")
                ),
                f"sources.{source_id}.lineage contém caminho local absoluto",
            )

    for reference_id, reference in monitoring_references.items():
        _require(
            reference.get("goalId") in goals,
            f"monitoringReferences.{reference_id}.goalId inexistente",
        )
        _require(
            reference.get("referenceKind") == "monitoring",
            f"monitoringReferences.{reference_id}.referenceKind inválido",
        )
        _require(
            reference.get("unit") in {"percent", "index", "count", "years"},
            f"monitoringReferences.{reference_id}.unit inválida",
        )
        value = reference.get("value")
        _require(
            isinstance(value, (int, float)) and not isinstance(value, bool),
            f"monitoringReferences.{reference_id}.value inválido",
        )
        _require(
            reference.get("direction") in {"at_least", "at_most"},
            f"monitoringReferences.{reference_id}.direction inválida",
        )

    relation_pairs: set[str] = set()
    for relation in relations:
        relation_id = relation["relationId"]
        goal_id = relation.get("goalId")
        indicator_id = relation.get("indicatorId")
        _require(goal_id in goals, f"{relation_id} referencia meta inexistente")
        _require(
            indicator_id in indicators,
            f"{relation_id} referencia indicador inexistente",
        )
        _require(
            relation.get("mode") in RELATIONSHIP_MODES,
            f"{relation_id}.mode inválido",
        )

        pair = f"{goal_id}:{indicator_id}"
        _require(pair not in relation_pairs, f"par meta×indicador duplicado: {pair}")
        relation_pairs.add(pair)

        for capability in (
            *CLASSIFYING_CAPABILITIES,
            *PUBLIC_CAPABILITIES,
            *RELATION_ELIGIBILITY_FLAGS,
        ):
            _require(
                isinstance(relation.get(capability), bool),
                f"{relation_id}.{capability} deve ser booleano",
            )
        reference_dimension = relation.get("referenceDimension")
        _require(
            reference_dimension is None or isinstance(reference_dimension, str),
            f"{relation_id}.referenceDimension deve ser texto ou nulo",
        )

        reference_id = relation.get("referenceId")
        if reference_id is not None:
            _require(
                reference_id in references,
                f"{relation_id}.referenceId inexistente",
            )
            reference_goal_id, reference = references[reference_id]
            _require(
                reference_goal_id == goal_id,
                f"{relation_id}.referenceId pertence a outra meta",
            )
            _require(
                reference.get("unit") == indicators[indicator_id].get("unit"),
                f"{relation_id}.referenceId usa unidade incompatível",
            )
            if reference_dimension is not None:
                reference_years = {
                    milestone["year"] for milestone in reference["milestones"]
                }
                dimension_years = {
                    milestone["year"]
                    for milestone in reference["milestones"]
                    if milestone.get("dimension") == reference_dimension
                }
                _require(
                    reference_years == dimension_years,
                    (
                        f"{relation_id}.referenceDimension não cobre "
                        "todos os marcos da referência"
                    ),
                )
        else:
            _require(
                reference_dimension is None,
                f"{relation_id}.referenceDimension exige referenceId",
            )

        reference_kind = relation.get("referenceKind")
        comparison_reference_id = relation.get("comparisonReferenceId")
        comparison_direction = relation.get("comparisonDirection")
        include_in_cycle_summary = relation.get("includeInCycleSummary")
        include_in_legal_summary = relation.get("includeInLegalSummary")
        for field, value in (
            ("includeInCycleSummary", include_in_cycle_summary),
            ("includeInLegalSummary", include_in_legal_summary),
        ):
            if value is not None:
                _require(
                    isinstance(value, bool),
                    f"{relation_id}.{field} deve ser booleano",
                )

        if relation["mode"] == "tracking":
            _require(
                reference_kind == "monitoring",
                f"{relation_id}.referenceKind deve ser monitoring",
            )
            _require(
                comparison_reference_id in monitoring_references,
                f"{relation_id}.comparisonReferenceId inexistente",
            )
            monitoring_reference = monitoring_references[
                comparison_reference_id
            ]
            _require(
                monitoring_reference["goalId"] == goal_id,
                f"{relation_id}.comparisonReferenceId pertence a outra meta",
            )
            _require(
                monitoring_reference["unit"]
                == indicators[indicator_id].get("unit"),
                f"{relation_id}.comparisonReferenceId usa unidade incompatível",
            )
            _require(
                comparison_direction == monitoring_reference["direction"],
                f"{relation_id}.comparisonDirection diverge da referência",
            )
            _require(
                relation["canDistance"] and relation["canStatus"],
                f"{relation_id} deve calcular distância e situação",
            )
            _require(
                not relation["canProjection"]
                and relation.get("projectionPolicyId") is None,
                f"{relation_id} tracking não pode projetar",
            )
            _require(
                include_in_cycle_summary is True,
                f"{relation_id}.includeInCycleSummary deve ser verdadeiro",
            )
            _require(
                include_in_legal_summary is False,
                f"{relation_id}.includeInLegalSummary deve ser falso",
            )
        elif reference_kind is not None:
            _require(
                reference_kind in REFERENCE_KINDS,
                f"{relation_id}.referenceKind inválido",
            )

        projection_policy_id = relation.get("projectionPolicyId")
        if projection_policy_id is not None:
            _require(
                projection_policy_id in projection_policies,
                f"{relation_id}.projectionPolicyId inexistente",
            )
            _require(
                relation["canProjection"],
                f"{relation_id} tem política sem capacidade de projeção",
            )

        if relation["mode"] not in COMPARABLE_MODES:
            for capability in CLASSIFYING_CAPABILITIES:
                _require(
                    not relation[capability],
                    f"{relation_id}.{capability} deve ser falso em {relation['mode']}",
                )
            _require(
                reference_id is None,
                f"{relation_id}.referenceId deve ser nulo em {relation['mode']}",
            )
            _require(
                reference_dimension is None,
                (
                    f"{relation_id}.referenceDimension deve ser nulo "
                    f"em {relation['mode']}"
                ),
            )
            _require(
                not relation["includeInReferenceSummary"],
                (
                    f"{relation_id}.includeInReferenceSummary deve ser falso "
                    f"em {relation['mode']}"
                ),
            )

        if relation["mode"] == "progress":
            _require(
                include_in_legal_summary in {None, relation["includeInReferenceSummary"]},
                f"{relation_id}.includeInLegalSummary diverge do resumo legal",
            )
        elif include_in_legal_summary is not None:
            _require(
                include_in_legal_summary is False,
                f"{relation_id}.includeInLegalSummary deve ser falso",
            )

        if relation["mode"] == "hidden":
            for capability in PUBLIC_CAPABILITIES:
                _require(
                    not relation[capability],
                    f"{relation_id}.{capability} deve ser falso em hidden",
                )

    return candidate


def _load_contract() -> dict[str, Any]:
    with CONTRACT_PATH.open(encoding="utf-8") as contract_file:
        candidate = json.load(contract_file)
    return validate_contract(candidate)


CONTRACT = _load_contract()
CONTRACT_VERSION = CONTRACT["contractVersion"]

_RELATIONS_BY_PAIR = {
    (relation["goalId"], relation["indicatorId"]): relation
    for relation in CONTRACT["relations"]
}


def get_goal(goal_id: str) -> dict[str, Any] | None:
    return CONTRACT["goals"].get(str(goal_id))


def get_indicator(indicator_id: str) -> dict[str, Any] | None:
    return CONTRACT["indicators"].get(str(indicator_id))


def get_formula(formula_id: str) -> dict[str, Any] | None:
    return CONTRACT["formulas"].get(str(formula_id))


def get_formula_for_indicator(indicator_id: str) -> dict[str, Any] | None:
    indicator = get_indicator(indicator_id)
    return get_formula(indicator["formulaId"]) if indicator is not None else None


def get_relation(
    goal_id: str,
    indicator_id: str,
) -> dict[str, Any] | None:
    return _RELATIONS_BY_PAIR.get((str(goal_id), str(indicator_id)))


def get_relations_for_goal(goal_id: str) -> list[dict[str, Any]]:
    normalized_goal_id = str(goal_id)
    return [
        relation
        for relation in CONTRACT["relations"]
        if relation["goalId"] == normalized_goal_id
    ]


def get_relations_for_indicator(indicator_id: str) -> list[dict[str, Any]]:
    normalized_indicator_id = str(indicator_id)
    return [
        relation
        for relation in CONTRACT["relations"]
        if relation["indicatorId"] == normalized_indicator_id
    ]


def get_public_relations_for_goal(goal_id: str) -> list[dict[str, Any]]:
    return [
        relation
        for relation in get_relations_for_goal(goal_id)
        if relation["mode"] != "hidden"
    ]


def get_relation_capabilities(
    goal_id: str,
    indicator_id: str,
) -> dict[str, Any] | None:
    relation = get_relation(goal_id, indicator_id)
    if relation is None:
        return None
    return {
        capability: relation[capability]
        for capability in (
            *CLASSIFYING_CAPABILITIES,
            *RELATION_ELIGIBILITY_FLAGS,
            *PUBLIC_CAPABILITIES,
            "referenceDimension",
        )
    } | {
        "referenceKind": relation_reference_kind(relation),
        "comparisonReferenceId": relation_comparison_reference_id(relation),
        "comparisonDirection": relation_comparison_direction(relation),
        "includeInCycleSummary": relation_include_in_cycle_summary(relation),
        "includeInLegalSummary": relation_include_in_legal_summary(relation),
    }


def relation_reference_kind(relation: dict[str, Any]) -> str | None:
    if relation.get("referenceKind") in REFERENCE_KINDS:
        return str(relation["referenceKind"])
    return "legal" if relation.get("referenceId") else None


def relation_comparison_reference_id(
    relation: dict[str, Any],
) -> str | None:
    return relation.get("comparisonReferenceId") or relation.get("referenceId")


def relation_comparison_direction(
    relation: dict[str, Any],
) -> str | None:
    explicit = relation.get("comparisonDirection")
    if explicit:
        return str(explicit)
    if relation.get("referenceId"):
        resolved = resolve_legal_reference(
            relation["goalId"],
            relation["referenceId"],
        )
        return resolved.get("milestone", {}).get("direction") if resolved else None
    return None


def relation_include_in_cycle_summary(relation: dict[str, Any]) -> bool:
    if isinstance(relation.get("includeInCycleSummary"), bool):
        return bool(relation["includeInCycleSummary"])
    return bool(
        relation["mode"] == "progress"
        and relation.get("includeInCycleGoalRefs")
        and relation.get("canDistance")
        and relation.get("canStatus")
    )


def relation_include_in_legal_summary(relation: dict[str, Any]) -> bool:
    if isinstance(relation.get("includeInLegalSummary"), bool):
        return bool(relation["includeInLegalSummary"])
    return bool(
        relation["mode"] == "progress"
        and relation.get("includeInReferenceSummary")
    )


def resolve_legal_reference(
    goal_id: str,
    reference_or_indicator_id: str,
    observed_year: int | None = None,
) -> dict[str, Any] | None:
    goal = get_goal(goal_id)
    relation = get_relation(goal_id, reference_or_indicator_id)
    if relation is None:
        relation = next(
            (
                item
                for item in get_relations_for_goal(goal_id)
                if item["referenceId"] == reference_or_indicator_id
            ),
            None,
        )
    reference_id = (
        relation["referenceId"]
        if relation is not None
        else reference_or_indicator_id
    )
    if reference_id is None:
        return None
    reference = next(
        (
            item
            for item in goal.get("legalReferences", [])
            if item["referenceId"] == reference_id
        ),
        None,
    )
    if reference is None:
        return None

    milestones = sorted(reference["milestones"], key=lambda item: item["year"])
    target_year = milestones[-1]["year"]
    if observed_year is not None:
        target_year = next(
            (
                item["year"]
                for item in milestones
                if item["year"] >= int(observed_year)
            ),
            milestones[-1]["year"],
        )
    milestones_at_year = [
        item for item in milestones if item["year"] == target_year
    ]
    resolved = {
        **reference,
        "targetYear": target_year,
        "milestonesAtYear": milestones_at_year,
    }
    if len(milestones_at_year) == 1:
        resolved["milestone"] = milestones_at_year[0]
    return resolved


def resolve_comparison_reference(
    goal_id: str,
    reference_or_indicator_id: str,
    observed_year: int | None = None,
) -> dict[str, Any] | None:
    relation = get_relation(goal_id, reference_or_indicator_id)
    if relation is None:
        relation = next(
            (
                item
                for item in get_relations_for_goal(goal_id)
                if relation_comparison_reference_id(item)
                == reference_or_indicator_id
            ),
            None,
        )
    if relation is None:
        return resolve_legal_reference(
            goal_id,
            reference_or_indicator_id,
            observed_year,
        )
    if relation_reference_kind(relation) == "legal":
        return resolve_legal_reference(
            relation["goalId"],
            relation["indicatorId"],
            observed_year,
        )
    reference_id = relation_comparison_reference_id(relation)
    reference = CONTRACT["monitoringReferences"].get(reference_id)
    return deepcopy(reference) if reference is not None else None


def get_relation_context(
    goal_id: str,
    indicator_id: str,
    observed_year: int | None = None,
) -> dict[str, Any] | None:
    relation = get_relation(goal_id, indicator_id)
    if relation is None:
        indicator_relations = get_relations_for_indicator(indicator_id)
        relation = (
            indicator_relations[0]
            if len(indicator_relations) == 1
            else None
        )
    if relation is None:
        return None
    comparison_reference = resolve_comparison_reference(
        relation["goalId"],
        relation["indicatorId"],
        observed_year,
    )
    legal_reference = (
        comparison_reference
        if relation_reference_kind(relation) == "legal"
        else None
    )
    reference_dimension = relation.get("referenceDimension")
    if legal_reference is not None and reference_dimension:
        milestones_at_year = [
            milestone
            for milestone in legal_reference["milestonesAtYear"]
            if milestone.get("dimension") == reference_dimension
        ]
        legal_reference = {
            **legal_reference,
            "milestonesAtYear": milestones_at_year,
        }
        legal_reference.pop("milestone", None)
        if len(milestones_at_year) == 1:
            legal_reference["milestone"] = milestones_at_year[0]
    return {
        "goal": get_goal(relation["goalId"]),
        "indicator": get_indicator(relation["indicatorId"]),
        "relation": relation,
        "legalReference": legal_reference,
        "comparisonReference": comparison_reference,
    }


def get_relation_context_for_indicator(
    indicator_id: str,
    observed_year: int | None = None,
) -> dict[str, Any] | None:
    relations = get_relations_for_indicator(indicator_id)
    if len(relations) != 1:
        return None
    relation = relations[0]
    return get_relation_context(
        relation["goalId"],
        relation["indicatorId"],
        observed_year,
    )


def get_indicator_reference_profile(
    indicator_id: str,
    observed_year: int | None = None,
) -> dict[str, Any] | None:
    """Resolve a referência comparável sem confundir meta legal e acompanhamento."""

    context = get_relation_context_for_indicator(indicator_id, observed_year)
    if context is None:
        return None
    relation = context["relation"]
    reference_kind = relation_reference_kind(relation)
    reference = context["comparisonReference"]
    if reference_kind not in REFERENCE_KINDS or reference is None:
        return None

    if reference_kind == "legal":
        milestone = reference.get("milestone")
        if milestone is None:
            return None
        return {
            "kind": "legal",
            "label": "Meta do PNE",
            "referenceId": reference["referenceId"],
            "value": milestone["value"],
            "year": milestone["year"],
            "unit": milestone["unit"],
            "direction": milestone["direction"],
            "validationStatus": reference["validationStatus"],
            "milestones": deepcopy(reference["milestones"]),
        }

    return {
        "kind": "monitoring",
        "label": "Referência de acompanhamento",
        "referenceId": reference["referenceId"],
        "value": reference["value"],
        "year": None,
        "unit": reference["unit"],
        "direction": reference["direction"],
        "validationStatus": reference["validationStatus"],
        "milestones": [],
    }


def is_progress_relation(goal_id: str, indicator_id: str) -> bool:
    relation = get_relation(goal_id, indicator_id)
    return relation is not None and relation["mode"] == "progress"


def is_complementary_relation(goal_id: str, indicator_id: str) -> bool:
    relation = get_relation(goal_id, indicator_id)
    return relation is not None and relation["mode"] == "complementary"


def is_tracking_relation(goal_id: str, indicator_id: str) -> bool:
    relation = get_relation(goal_id, indicator_id)
    return relation is not None and relation["mode"] == "tracking"


def is_hidden_relation(goal_id: str, indicator_id: str) -> bool:
    relation = get_relation(goal_id, indicator_id)
    return relation is not None and relation["mode"] == "hidden"


def can_relation_project(goal_id: str, indicator_id: str) -> bool:
    relation = get_relation(goal_id, indicator_id)
    return relation is not None and relation["canProjection"]


def can_relation_enter_diagnostic(goal_id: str, indicator_id: str) -> bool:
    relation = get_relation(goal_id, indicator_id)
    return relation is not None and relation["includeInDiagnostic"]


_UNSET = object()


def normalize_contract(value: Any = _UNSET) -> Any:
    """Ordena chaves recursivamente sem alterar a ordem dos arrays."""

    if value is _UNSET:
        value = CONTRACT
    if isinstance(value, list):
        return [normalize_contract(item) for item in value]
    if isinstance(value, dict):
        return {
            key: normalize_contract(value[key])
            for key in sorted(value)
        }
    return value


def stable_contract_json(value: Any = _UNSET) -> str:
    return json.dumps(
        normalize_contract(CONTRACT if value is _UNSET else value),
        ensure_ascii=False,
        separators=(",", ":"),
    )


def contract_hash(value: Any = _UNSET) -> str:
    return sha256(stable_contract_json(value).encode("utf-8")).hexdigest()


if __name__ == "__main__":
    print(contract_hash())
