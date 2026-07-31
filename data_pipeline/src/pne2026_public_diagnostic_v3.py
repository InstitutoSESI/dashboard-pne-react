from __future__ import annotations

from collections import Counter
from copy import deepcopy
import math
from typing import Any, Iterable, Mapping

from .pne.diagnostic_presentation_policy import (
    POLICY,
    get_presentation_entry,
    policy_hash,
)
from .pne.goal_indicator_contract import (
    CONTRACT,
    CONTRACT_VERSION,
    contract_hash,
    resolve_comparison_reference,
    resolve_legal_reference,
)


PUBLIC_V3_SCHEMA_VERSION = "pne2026-public-diagnostic-v4"
PRESENTATION_POLICY_VERSION = str(POLICY["policyVersion"])
CONTRACT_HASH = contract_hash()
PRESENTATION_POLICY_HASH = policy_hash()

TOP_LEVEL_FIELDS = frozenset(
    {
        "schemaVersion",
        "contractVersion",
        "contractHash",
        "presentationPolicyVersion",
        "presentationPolicyHash",
        "municipality",
        "summary",
        "results",
    }
)
MUNICIPALITY_FIELDS = frozenset({"id", "name"})
SUMMARY_FIELDS = frozenset(
    {
        "visibleResultCount",
        "progressResultCount",
        "trackingResultCount",
        "complementaryResultCount",
        "legalReferenceResultCount",
        "monitoringReferenceResultCount",
        "dataStatusCounts",
        "classificationCounts",
        "presentationPriorityCounts",
    }
)
CLASSIFICATION_COUNT_FIELDS = frozenset({"advance", "maintain", "unclassified"})
PRESENTATION_PRIORITY_COUNT_FIELDS = frozenset({"essential", "standard"})
DATA_STATUS_COUNT_FIELDS = frozenset(
    {"available", "unavailable", "not_applicable", "suppressed"}
)
DATA_STATUSES = DATA_STATUS_COUNT_FIELDS
RESULT_FIELDS = frozenset(
    {
        "relationId",
        "goalId",
        "indicatorId",
        "dataStatus",
        "reasonCode",
        "year",
        "value",
        "numeratorField",
        "numeratorValue",
        "denominatorField",
        "denominatorValue",
        "resolvedReferenceId",
        "distance",
        "remainingGap",
        "favorableDifference",
        "status",
        "classification",
        "publicReading",
        "stateComparison",
        "statewidePosition",
        "similarMunicipalityComparison",
        "trend",
        "projection",
    }
)
STATE_COMPARISON_FIELDS = frozenset(
    {
        "state",
        "municipalityValue",
        "stateValue",
        "year",
        "unit",
        "difference",
        "favorableDifference",
        "reading",
        "valueReading",
    }
)
STATEWIDE_POSITION_FIELDS = frozenset({"reading"})
SIMILAR_COMPARISON_FIELDS = frozenset(
    {"title", "year", "median", "unit", "reading"}
)
TREND_FIELDS = frozenset({"historicalReading"})
PROJECTION_FIELDS = frozenset(
    {
        "estimatedAchievementYear",
        "achievementReading",
        "modelReading",
        "denominatorReading",
        "uncertaintyReading",
    }
)
_LEGACY_ATTENDANCE_PROJECTION_INDICATORS = frozenset(
    {"creche", "pre_escola", "basico_6_17"}
)

DEPRECATED_V2_RESULT_FIELDS = frozenset(
    {
        "tracksGoal",
        "tracks_goal",
        "hasDistance",
        "relationshipType",
        "linkType",
        "classificationPolicy",
        "valuePolicy",
        "tier",
        "priorityOrder",
        "summaryPriority",
        "displayOrder",
        "resultOrder",
        "themeId",
        "displayGroup",
        "mode",
        "canDistance",
        "canStatus",
        "canProjection",
        "includeInDiagnostic",
        "includeInReferenceSummary",
        "target",
        "meta",
        "metaLabel",
        "meta_label",
        "deadline",
        "direction",
        "formulaId",
        "sourceIds",
        "territoriality",
        "publicName",
        "publicDescription",
        "relationshipReading",
        "legalGoal",
        "indicatorReference",
        "finalReference",
        "methodology",
        "source",
        "current",
    }
)

_RELATIONS_BY_ID = {
    relation["relationId"]: relation for relation in CONTRACT["relations"]
}
_RELATIONS_BY_PAIR = {
    (relation["goalId"], relation["indicatorId"]): relation
    for relation in CONTRACT["relations"]
}
_POLICY_BY_RELATION_ID = {
    entry["relationId"]: entry for entry in POLICY["relations"]
}


class Pne2026PublicDiagnosticV3Error(ValueError):
    pass


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise Pne2026PublicDiagnosticV3Error(message)


def _is_finite_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def _copy_if_present(
    destination: dict[str, Any],
    source: Mapping[str, Any],
    source_field: str,
    destination_field: str | None = None,
) -> None:
    if source_field in source and source[source_field] is not None:
        destination[destination_field or source_field] = deepcopy(
            source[source_field]
        )


def _component_labels(relation: Mapping[str, Any]) -> tuple[str | None, str | None]:
    indicator = CONTRACT["indicators"][str(relation["indicatorId"])]
    formula = CONTRACT["formulas"][str(indicator["formulaId"])]
    catalog = formula.get("catalogProjection") or {}
    numerator = catalog.get("numerator")
    denominator = catalog.get("denominator")
    return (
        str(numerator) if numerator else None,
        str(denominator) if denominator else None,
    )


def _set_component_fields(
    projected: dict[str, Any],
    relation: Mapping[str, Any],
    *,
    numerator: Any = None,
    denominator: Any = None,
    numerator_field: Any = None,
    denominator_field: Any = None,
) -> None:
    canonical_numerator, canonical_denominator = _component_labels(relation)
    resolved_numerator_field = (
        str(numerator_field)
        if isinstance(numerator_field, str) and numerator_field.strip()
        else canonical_numerator
    )
    resolved_denominator_field = (
        str(denominator_field)
        if isinstance(denominator_field, str) and denominator_field.strip()
        else canonical_denominator
    )
    if resolved_numerator_field:
        projected["numeratorField"] = resolved_numerator_field
    if resolved_denominator_field:
        projected["denominatorField"] = resolved_denominator_field
    if _is_finite_number(numerator):
        projected["numeratorValue"] = float(numerator)
    if _is_finite_number(denominator):
        projected["denominatorValue"] = float(denominator)


def _normalize_result_for_relation(
    relation: Mapping[str, Any],
    projected: dict[str, Any],
) -> dict[str, Any]:
    legacy_numerator = projected.pop("numerator", None)
    legacy_denominator = projected.pop("denominator", None)
    _set_component_fields(
        projected,
        relation,
        numerator=projected.get("numeratorValue", legacy_numerator),
        denominator=projected.get("denominatorValue", legacy_denominator),
        numerator_field=(
            projected.get("numeratorField")
            if projected.get("numeratorField") is not None
            else legacy_numerator
        ),
        denominator_field=(
            projected.get("denominatorField")
            if projected.get("denominatorField") is not None
            else legacy_denominator
        ),
    )
    status = str(projected.get("dataStatus") or "available")
    projected["dataStatus"] = status
    if status != "available":
        for field in (
            "year",
            "value",
            "numeratorValue",
            "denominatorValue",
            "resolvedReferenceId",
            "distance",
            "remainingGap",
            "favorableDifference",
            "status",
            "classification",
            "publicReading",
            "stateComparison",
            "statewidePosition",
            "similarMunicipalityComparison",
            "trend",
            "projection",
        ):
            projected.pop(field, None)
        return projected
    if relation["mode"] == "complementary":
        for field in (
            "resolvedReferenceId",
            "distance",
            "remainingGap",
            "favorableDifference",
            "status",
            "classification",
            "trend",
            "projection",
        ):
            projected.pop(field, None)
        projected["publicReading"] = (
            "Resultado municipal disponível para consulta, sem referência "
            "municipal."
        )
        return projected
    if relation["mode"] == "progress" and _is_finite_number(
        projected.get("value")
    ):
        reference = resolve_legal_reference(
            str(relation["goalId"]),
            str(relation["indicatorId"]),
            projected.get("year"),
        )
        milestone = (reference or {}).get("milestone") or {}
        if _is_finite_number(milestone.get("value")):
            value = float(projected["value"])
            target = float(milestone["value"])
            direction = str(milestone.get("direction") or "at_least")
            projected["status"] = (
                "Dentro do limite"
                if direction == "at_most" and value <= target
                else "Acima do limite"
                if direction == "at_most"
                else "Referência alcançada"
                if value >= target
                else "Abaixo da referência"
            )
    return _apply_tracking_comparison(relation, projected)


def _resolve_relation(goal_id: str, result: Mapping[str, Any]) -> Mapping[str, Any]:
    relation_id = result.get("relationId")
    pair = (str(goal_id), str(result.get("indicatorId")))
    pair_relation = _RELATIONS_BY_PAIR.get(pair)
    if relation_id is not None:
        relation = _RELATIONS_BY_ID.get(str(relation_id))
        _require(relation is not None, f"relationId desconhecido: {relation_id}.")
        _require(
            pair_relation is not None
            and pair_relation["relationId"] == relation["relationId"],
            (
                f"{relation_id} não corresponde a "
                f"{goal_id} × {result.get('indicatorId')}."
            ),
        )
        return relation
    _require(
        pair_relation is not None,
        f"Relação ausente para {goal_id} × {result.get('indicatorId')}.",
    )
    return pair_relation


def _technical_index(
    diagnostic_contract: Mapping[str, Any],
) -> dict[str, Mapping[str, Any]]:
    return {
        str(item["indicatorId"]): item
        for item in diagnostic_contract.get("indicators") or []
        if item.get("indicatorId")
    }


def _tracking_public_reading(
    relation: Mapping[str, Any],
    value: float,
    status: str,
) -> str:
    relation_id = str(relation["relationId"])
    if relation_id == "relation.17.c.munic_planos_carreira_declarados":
        return (
            f"O município declarou {int(round(value))} de 2 requisitos "
            "de plano de carreira."
        )
    if relation_id == "relation.18.c.munic_forum_educacao_declarado":
        return (
            "O município declarou a existência formal do fórum de educação."
            if value >= 1
            else "O município não declarou a existência formal do fórum de educação."
        )
    return (
        "O valor municipal alcançou a referência de acompanhamento."
        if status in {"Referência alcançada", "Dentro do limite"}
        else "O valor municipal está abaixo da referência de acompanhamento."
        if status == "Abaixo da referência"
        else "O valor municipal está acima do limite de acompanhamento."
    )


def _apply_tracking_comparison(
    relation: Mapping[str, Any],
    projected: dict[str, Any],
) -> dict[str, Any]:
    if relation["mode"] != "tracking":
        return projected
    for field in (
        "resolvedReferenceId",
        "distance",
        "remainingGap",
        "favorableDifference",
        "status",
        "classification",
        "publicReading",
        "trend",
        "projection",
    ):
        projected.pop(field, None)
    if not _is_finite_number(projected.get("value")):
        return projected
    reference = resolve_comparison_reference(
        str(relation["goalId"]),
        str(relation["indicatorId"]),
        projected.get("year"),
    )
    _require(
        isinstance(reference, Mapping)
        and _is_finite_number(reference.get("value")),
        f"Referência municipal ausente: {relation['relationId']}.",
    )
    value = float(projected["value"])
    target = float(reference["value"])
    direction = str(reference.get("direction") or "at_least")
    distance = target - value if direction == "at_most" else value - target
    at_reference = distance >= 0
    status = (
        "Dentro do limite"
        if at_reference and direction == "at_most"
        else "Referência alcançada"
        if at_reference
        else "Acima do limite"
        if direction == "at_most"
        else "Abaixo da referência"
    )
    projected.update(
        {
            "resolvedReferenceId": str(reference["referenceId"]),
            "distance": distance,
            "remainingGap": max(0.0, -distance),
            "favorableDifference": distance,
            "status": status,
            "publicReading": _tracking_public_reading(relation, value, status),
        }
    )
    return projected


def _project_result(
    relation: Mapping[str, Any],
    result: Mapping[str, Any],
    technical: Mapping[str, Any] | None,
) -> dict[str, Any]:
    current = result.get("current") or {}
    data_status = str(result.get("dataStatus") or "available")
    projected: dict[str, Any] = {
        "relationId": relation["relationId"],
        "goalId": relation["goalId"],
        "indicatorId": relation["indicatorId"],
        "dataStatus": data_status,
    }
    if data_status == "available":
        projected["year"] = current.get("year")
        projected["value"] = current.get("value")
    if result.get("reasonCode"):
        projected["reasonCode"] = str(result["reasonCode"])

    methodology = (technical or {}).get("methodology") or {}
    _set_component_fields(
        projected,
        relation,
        numerator=(
            result.get("numerator")
            if _is_finite_number(result.get("numerator"))
            else current.get("numerator")
        ),
        denominator=(
            result.get("denominator")
            if _is_finite_number(result.get("denominator"))
            else current.get("denominator")
        ),
        numerator_field=methodology.get("numerator"),
        denominator_field=methodology.get("denominator"),
    )

    if (
        relation["mode"] == "progress"
        and relation.get("referenceId")
        and result.get("indicatorReference")
    ):
        projected["resolvedReferenceId"] = relation["referenceId"]
    if relation.get("canDistance"):
        for field in ("distance", "remainingGap", "favorableDifference"):
            _copy_if_present(projected, result, field)
    if relation.get("canStatus"):
        if "classification" in result:
            projected["classification"] = result.get("classification")
        _copy_if_present(projected, result, "status")
    _copy_if_present(projected, result, "publicReading")

    if relation.get("stateReferencePolicy") != "none":
        _copy_if_present(projected, result, "stateComparison")
        _copy_if_present(projected, result, "statewidePosition")
        _copy_if_present(
            projected,
            result,
            "similarMunicipalities",
            "similarMunicipalityComparison",
        )

    if relation.get("canProjection") and isinstance(
        result.get("trajectory"), Mapping
    ):
        trajectory = result["trajectory"]
        trend = {
            key: deepcopy(trajectory[key])
            for key in TREND_FIELDS
            if trajectory.get(key) is not None
        }
        projection = {
            key: deepcopy(trajectory[key])
            for key in PROJECTION_FIELDS
            if trajectory.get(key) is not None
        }
        if trend:
            projected["trend"] = trend
        if projection:
            projected["projection"] = projection
    return _normalize_result_for_relation(relation, projected)


def _project_methodology_result(
    relation: Mapping[str, Any],
    result: Mapping[str, Any],
) -> dict[str, Any]:
    data_status = str(result.get("dataStatus") or "unavailable")
    projected: dict[str, Any] = {
        "relationId": relation["relationId"],
        "goalId": relation["goalId"],
        "indicatorId": relation["indicatorId"],
        "dataStatus": data_status,
    }
    if result.get("reasonCode"):
        projected["reasonCode"] = str(result["reasonCode"])
    if data_status != "available":
        return _normalize_result_for_relation(relation, projected)
    _require(
        _is_finite_number(result.get("value"))
        and isinstance(result.get("year"), int),
        f"Resultado available inválido: {relation['relationId']}.",
    )
    projected["year"] = int(result["year"])
    projected["value"] = float(result["value"])
    _set_component_fields(
        projected,
        relation,
        numerator=result.get("numerator"),
        denominator=result.get("denominator"),
    )
    if relation["mode"] == "progress" and relation.get("referenceId"):
        projected["resolvedReferenceId"] = relation["referenceId"]
    if relation.get("canDistance") and _is_finite_number(result.get("distance")):
        projected["distance"] = float(result["distance"])
    if relation.get("canStatus"):
        if result.get("classification") in {"advance", "maintain"}:
            projected["classification"] = result["classification"]
        if result.get("status"):
            projected["status"] = str(result["status"])
    if result.get("publicReading"):
        projected["publicReading"] = str(result["publicReading"])
    if relation.get("stateReferencePolicy") != "none":
        for field in (
            "stateComparison",
            "statewidePosition",
            "similarMunicipalityComparison",
        ):
            if isinstance(result.get(field), Mapping):
                projected[field] = deepcopy(result[field])
    return _normalize_result_for_relation(relation, projected)


def _missing_result(relation: Mapping[str, Any]) -> dict[str, Any]:
    reason_code = (
        "no_post_baseline_observation"
        if relation["indicatorId"]
        in {"medio_tecnico_participacao_publica", "subsequente_expansao"}
        else "no_observation"
    )
    return _normalize_result_for_relation(
        relation,
        {
            "relationId": relation["relationId"],
            "goalId": relation["goalId"],
            "indicatorId": relation["indicatorId"],
            "dataStatus": "unavailable",
            "reasonCode": reason_code,
        },
    )


def _append_missing_eligible_results(
    results: list[dict[str, Any]],
    seen: set[str],
) -> None:
    for relation in CONTRACT["relations"]:
        relation_id = str(relation["relationId"])
        if (
            relation_id in seen
            or relation["mode"] == "hidden"
            or relation.get("includeInDiagnostic") is not True
            or relation_id not in _POLICY_BY_RELATION_ID
        ):
            continue
        results.append(_missing_result(relation))
        seen.add(relation_id)


def build_v3_summary(results: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    result_list = list(results)
    mode_counts: Counter[str] = Counter()
    data_status_counts: Counter[str] = Counter()
    classification_counts: Counter[str] = Counter()
    priority_counts: Counter[str] = Counter()
    for result in result_list:
        relation = _RELATIONS_BY_ID[str(result["relationId"])]
        policy = _POLICY_BY_RELATION_ID[str(result["relationId"])]
        mode = str(relation["mode"])
        mode_counts[mode] += 1
        data_status = str(result["dataStatus"])
        data_status_counts[data_status] += 1
        priority_counts[str(policy["summaryPriority"])] += 1
        if mode == "progress" and data_status == "available":
            classification = result.get("classification")
            classification_counts[
                classification
                if classification in {"advance", "maintain"}
                else "unclassified"
            ] += 1
    return {
        "visibleResultCount": len(result_list),
        "progressResultCount": mode_counts["progress"],
        "trackingResultCount": mode_counts["tracking"],
        "complementaryResultCount": mode_counts["complementary"],
        "legalReferenceResultCount": sum(
            result["dataStatus"] == "available"
            and _RELATIONS_BY_ID[str(result["relationId"])]["mode"] == "progress"
            and bool(result.get("resolvedReferenceId"))
            for result in result_list
        ),
        "monitoringReferenceResultCount": sum(
            result["dataStatus"] == "available"
            and _RELATIONS_BY_ID[str(result["relationId"])]["mode"] == "tracking"
            and bool(result.get("resolvedReferenceId"))
            for result in result_list
        ),
        "dataStatusCounts": {
            key: data_status_counts[key]
            for key in ("available", "unavailable", "not_applicable", "suppressed")
        },
        "classificationCounts": {
            key: classification_counts[key]
            for key in ("advance", "maintain", "unclassified")
        },
        "presentationPriorityCounts": {
            key: priority_counts[key] for key in ("essential", "standard")
        },
    }


def build_pne2026_public_diagnostic_v3(
    diagnostic_contract: Mapping[str, Any],
    *,
    methodology_results: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    public_v2 = diagnostic_contract.get("pne2026PublicDiagnosticV2")
    _require(isinstance(public_v2, Mapping), "Bloco municipal V2 ausente.")
    technical_by_indicator = _technical_index(diagnostic_contract)
    results: list[dict[str, Any]] = []
    seen: set[str] = set()
    methodology_results = dict(methodology_results or {})
    for goal in public_v2.get("goals") or []:
        goal_id = str(goal.get("goalId"))
        for raw_result in goal.get("results") or []:
            relation = _resolve_relation(goal_id, raw_result)
            if relation["relationId"] in methodology_results:
                continue
            if (
                relation["mode"] == "hidden"
                or relation.get("includeInDiagnostic") is not True
            ):
                continue
            policy = get_presentation_entry(relation["relationId"])
            _require(
                policy is not None,
                f"Política editorial ausente: {relation['relationId']}.",
            )
            _require(
                relation["relationId"] not in seen,
                f"relationId duplicado: {relation['relationId']}.",
            )
            seen.add(relation["relationId"])
            results.append(
                _project_result(
                    relation,
                    raw_result,
                    technical_by_indicator.get(relation["indicatorId"]),
                )
            )
    for relation_id, methodology_result in methodology_results.items():
        relation = _RELATIONS_BY_ID.get(str(relation_id))
        _require(relation is not None, f"relationId desconhecido: {relation_id}.")
        if (
            relation["mode"] == "hidden"
            or relation.get("includeInDiagnostic") is not True
        ):
            continue
        policy = get_presentation_entry(relation["relationId"])
        _require(
            policy is not None,
            f"Política editorial ausente: {relation['relationId']}.",
        )
        _require(
            relation["relationId"] not in seen,
            f"relationId duplicado: {relation['relationId']}.",
        )
        projected = _project_methodology_result(relation, methodology_result)
        seen.add(relation["relationId"])
        results.append(projected)
    _append_missing_eligible_results(results, seen)
    results.sort(
        key=lambda result: _POLICY_BY_RELATION_ID[result["relationId"]][
            "displayOrder"
        ]
    )
    payload = {
        "schemaVersion": PUBLIC_V3_SCHEMA_VERSION,
        "contractVersion": CONTRACT_VERSION,
        "contractHash": contract_hash(),
        "presentationPolicyVersion": str(POLICY["policyVersion"]),
        "presentationPolicyHash": policy_hash(),
        "municipality": {
            "id": str(
                public_v2.get("municipalityId")
                or diagnostic_contract.get("municipalityId")
            ),
            "name": str(
                public_v2.get("municipalityName")
                or diagnostic_contract.get("municipalityName")
            ),
        },
        "summary": build_v3_summary(results),
        "results": results,
    }
    return validate_pne2026_public_diagnostic_v3(payload)


def rebase_pne2026_public_diagnostic_v3(
    active_payload: Mapping[str, Any],
    *,
    methodology_results: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Preserva registros ativos e acrescenta resultados metodológicos novos.

    A função é usada em rodadas incrementais nas quais o contrato muda, mas as
    relações fora do pacote precisam permanecer idênticas registro a registro.
    A identidade do payload e o resumo são sempre reconstruídos com o contrato
    e a política correntes.
    """

    municipality = active_payload.get("municipality") or {}
    _require(
        isinstance(municipality, Mapping)
        and str(municipality.get("id") or "").isdigit()
        and bool(str(municipality.get("name") or "").strip()),
        "Identidade municipal da release ativa inválida.",
    )
    base_results = active_payload.get("results")
    _require(
        isinstance(base_results, list),
        "Release ativa sem lista de resultados.",
    )

    results: list[dict[str, Any]] = []
    seen: set[str] = set()
    methodology_relation_ids = {
        str(relation_id) for relation_id in methodology_results
    }
    for raw_result in base_results:
        _require(
            isinstance(raw_result, Mapping),
            "Release ativa contém resultado inválido.",
        )
        relation_id = str(raw_result.get("relationId") or "")
        relation = _RELATIONS_BY_ID.get(relation_id)
        _require(
            relation is not None,
            f"Relação da release ativa ausente no contrato corrente: {relation_id}.",
        )
        _require(
            raw_result.get("goalId") == relation["goalId"]
            and raw_result.get("indicatorId") == relation["indicatorId"],
            f"Identidade divergente na release ativa: {relation_id}.",
        )
        _require(
            relation_id not in seen,
            f"Relação duplicada na release ativa: {relation_id}.",
        )
        if (
            relation["mode"] == "hidden"
            or relation.get("includeInDiagnostic") is not True
        ):
            continue
        if relation_id in methodology_relation_ids:
            # A ampliação é uma substituição determinística do pacote. Isso
            # permite rematerializar a release ativa sem duplicar relações e
            # também remove um valor anterior quando a nova fonte passa a
            # classificá-lo como unavailable/not_applicable.
            continue
        _require(
            get_presentation_entry(relation_id) is not None,
            f"Política editorial ausente: {relation_id}.",
        )
        seen.add(relation_id)
        migrated_result = _upgrade_legacy_attendance_projection(raw_result)
        results.append(
            _normalize_result_for_relation(
                relation,
                migrated_result,
            )
        )

    for relation_id, methodology_result in methodology_results.items():
        relation = _RELATIONS_BY_ID.get(str(relation_id))
        _require(relation is not None, f"relationId desconhecido: {relation_id}.")
        if (
            relation["mode"] == "hidden"
            or relation.get("includeInDiagnostic") is not True
        ):
            continue
        projected = _project_methodology_result(relation, methodology_result)
        seen.add(relation["relationId"])
        results.append(projected)

    _append_missing_eligible_results(results, seen)
    results.sort(
        key=lambda result: _POLICY_BY_RELATION_ID[result["relationId"]][
            "displayOrder"
        ]
    )
    payload = {
        "schemaVersion": PUBLIC_V3_SCHEMA_VERSION,
        "contractVersion": CONTRACT_VERSION,
        "contractHash": contract_hash(),
        "presentationPolicyVersion": str(POLICY["policyVersion"]),
        "presentationPolicyHash": policy_hash(),
        "municipality": {
            "id": str(municipality["id"]),
            "name": str(municipality["name"]),
        },
        "summary": build_v3_summary(results),
        "results": results,
    }
    return validate_pne2026_public_diagnostic_v3(payload)


def _upgrade_legacy_attendance_projection(
    raw_result: Mapping[str, Any],
) -> dict[str, Any]:
    result = deepcopy(dict(raw_result))
    projection = result.get("projection")
    if (
        result.get("indicatorId") not in _LEGACY_ATTENDANCE_PROJECTION_INDICATORS
        or not isinstance(projection, Mapping)
    ):
        return result
    uses_state_enrollment_trend = result.get("indicatorId") == "pre_escola"
    result["projection"] = {
        "modelReading": (
            (
                "Cenário em que o nível municipal parte da última matrícula e "
                "acompanha a tendência estadual amortecida das matrículas, "
                "selecionada por validação fora da amostra."
            )
            if uses_state_enrollment_trend
            else (
                "Linha de base que mantém o número de matrículas observado mais "
                "recente; alternativas tendenciais foram testadas, mas não "
                "reduziram o erro de forma robusta."
            )
        ),
        "denominatorReading": (
            "O denominador parte da população municipal observada e acompanha "
            "a variação etária projetada para o Rio Grande do Sul."
        ),
        "uncertaintyReading": (
            "O teste retrospectivo cobre horizontes de um a cinco anos. O "
            "cenário não possui intervalo probabilístico até 2036 e não é uma "
            "previsão oficial; por isso, não é divulgado um ano exato de alcance."
        ),
    }
    return result


def _validate_exact_fields(
    value: Any,
    allowed: frozenset[str],
    path: str,
    *,
    required: frozenset[str] | None = None,
) -> Mapping[str, Any]:
    _require(isinstance(value, Mapping), f"{path} deve ser objeto.")
    keys = set(value)
    unknown = keys - allowed
    _require(not unknown, f"{path} contém campos desconhecidos: {sorted(unknown)}.")
    if required is not None:
        missing = required - keys
        _require(not missing, f"{path} não contém campos obrigatórios: {sorted(missing)}.")
    return value


def _validate_finite_tree(value: Any, path: str = "$") -> None:
    if isinstance(value, float):
        _require(math.isfinite(value), f"{path} contém NaN ou Infinity.")
    elif isinstance(value, Mapping):
        for key, child in value.items():
            _validate_finite_tree(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _validate_finite_tree(child, f"{path}[{index}]")


def _validate_nested_result_fields(
    result: Mapping[str, Any],
    path: str,
) -> None:
    nested_allowlists = {
        "stateComparison": STATE_COMPARISON_FIELDS,
        "statewidePosition": STATEWIDE_POSITION_FIELDS,
        "similarMunicipalityComparison": SIMILAR_COMPARISON_FIELDS,
        "trend": TREND_FIELDS,
        "projection": PROJECTION_FIELDS,
    }
    for field, allowlist in nested_allowlists.items():
        if field in result:
            _validate_exact_fields(result[field], allowlist, f"{path}.{field}")


def _validate_result(
    result: Any,
    path: str,
    seen: set[str],
) -> None:
    result = _validate_exact_fields(
        result,
        RESULT_FIELDS,
        path,
        required=frozenset(
            {
                "relationId",
                "goalId",
                "indicatorId",
                "dataStatus",
            }
        ),
    )
    relation_id = str(result["relationId"])
    relation = _RELATIONS_BY_ID.get(relation_id)
    _require(relation is not None, f"{path}.relationId desconhecido.")
    _require(
        result["goalId"] == relation["goalId"]
        and result["indicatorId"] == relation["indicatorId"],
        f"{path} diverge da identidade canônica de {relation_id}.",
    )
    _require(relation_id not in seen, f"{path}.relationId duplicado.")
    seen.add(relation_id)
    _require(
        relation["mode"] != "hidden"
        and relation.get("includeInDiagnostic") is True,
        f"{path} referencia relação oculta.",
    )
    _require(
        relation_id in _POLICY_BY_RELATION_ID,
        f"{path} não possui política editorial.",
    )
    _require(result["dataStatus"] in DATA_STATUSES, f"{path}.dataStatus inválido.")
    if result["dataStatus"] == "available":
        _require(
            isinstance(result.get("year"), int)
            and not isinstance(result.get("year"), bool),
            f"{path}.year inválido.",
        )
        _require(_is_finite_number(result.get("value")), f"{path}.value inválido.")
    else:
        forbidden_negative = {
            "year",
            "value",
            "numeratorValue",
            "denominatorValue",
            "resolvedReferenceId",
            "distance",
            "remainingGap",
            "favorableDifference",
            "status",
            "classification",
            "publicReading",
            "stateComparison",
            "statewidePosition",
            "similarMunicipalityComparison",
            "trend",
            "projection",
        } & set(result)
        _require(
            not forbidden_negative,
            f"{path} com estado negativo contém resultado: {sorted(forbidden_negative)}.",
        )
        _require(
            isinstance(result.get("reasonCode"), str)
            and bool(result.get("reasonCode")),
            f"{path}.reasonCode obrigatório em estado negativo.",
        )
    for field in ("numeratorField", "denominatorField"):
        if field in result:
            _require(
                isinstance(result[field], str) and bool(result[field].strip()),
                f"{path}.{field} inválido.",
            )
    for field in ("numeratorValue", "denominatorValue"):
        if field in result:
            _require(
                _is_finite_number(result[field]),
                f"{path}.{field} deve ser numérico.",
            )

    if "resolvedReferenceId" in result:
        reference = resolve_comparison_reference(
            str(relation["goalId"]),
            str(relation["indicatorId"]),
            result.get("year"),
        )
        _require(
            relation["mode"] in {"progress", "tracking"}
            and reference is not None
            and result["resolvedReferenceId"] == reference.get("referenceId"),
            f"{path}.resolvedReferenceId não autorizado.",
        )
    for field in ("distance", "remainingGap", "favorableDifference"):
        if field in result:
            _require(
                relation.get("canDistance") is True,
                f"{path}.{field} não autorizado.",
            )
            _require(
                _is_finite_number(result[field]),
                f"{path}.{field} deve ser finito.",
            )
    for field in ("status", "classification"):
        if field in result:
            _require(
                relation.get("canStatus") is True,
                f"{path}.{field} não autorizado.",
            )
    if "classification" in result:
        _require(
            relation["mode"] == "progress"
            and
            result["classification"] in {"advance", "maintain", None},
            f"{path}.classification inválida.",
        )
    if relation["mode"] == "tracking" and result["dataStatus"] == "available":
        _require(
            "resolvedReferenceId" in result
            and "distance" in result
            and "status" in result
            and "classification" not in result
            and "trend" not in result
            and "projection" not in result,
            f"{path} não contém a comparação municipal canônica.",
        )
    if "projection" in result or "trend" in result:
        _require(
            relation.get("canProjection") is True,
            f"{path} contém projeção/tendência não autorizada.",
        )
    if any(
        field in result
        for field in (
            "stateComparison",
            "statewidePosition",
            "similarMunicipalityComparison",
        )
    ):
        _require(
            relation.get("stateReferencePolicy") != "none",
            f"{path} contém comparação estadual não autorizada.",
        )
    if relation["mode"] == "complementary":
        forbidden = {
            "distance",
            "remainingGap",
            "favorableDifference",
            "status",
            "classification",
            "trend",
            "projection",
            "resolvedReferenceId",
        } & set(result)
        _require(
            not forbidden,
            f"{path} complementar contém campos classificatórios: {sorted(forbidden)}.",
        )
    _validate_nested_result_fields(result, path)


def validate_pne2026_public_diagnostic_v3(
    candidate: Any,
) -> dict[str, Any]:
    candidate = _validate_exact_fields(
        candidate,
        TOP_LEVEL_FIELDS,
        "$",
        required=TOP_LEVEL_FIELDS,
    )
    _require(
        candidate["schemaVersion"] == PUBLIC_V3_SCHEMA_VERSION,
        "schemaVersion V3 inválida.",
    )
    _require(
        candidate["contractVersion"] == CONTRACT_VERSION,
        "contractVersion V3 inválida.",
    )
    _require(
        candidate["contractHash"] == contract_hash() == CONTRACT_HASH,
        "contractHash V3 inválido.",
    )
    _require(
        candidate["presentationPolicyVersion"]
        == POLICY["policyVersion"]
        == PRESENTATION_POLICY_VERSION,
        "presentationPolicyVersion V3 inválida.",
    )
    _require(
        candidate["presentationPolicyHash"]
        == policy_hash()
        == PRESENTATION_POLICY_HASH,
        "presentationPolicyHash V3 inválido.",
    )
    municipality = _validate_exact_fields(
        candidate["municipality"],
        MUNICIPALITY_FIELDS,
        "$.municipality",
        required=MUNICIPALITY_FIELDS,
    )
    _require(
        isinstance(municipality["id"], str)
        and municipality["id"].isdigit(),
        "$.municipality.id inválido.",
    )
    _require(
        isinstance(municipality["name"], str)
        and bool(municipality["name"].strip()),
        "$.municipality.name inválido.",
    )
    _require(isinstance(candidate["results"], list), "$.results deve ser lista.")
    seen: set[str] = set()
    for index, result in enumerate(candidate["results"]):
        _validate_result(result, f"$.results[{index}]", seen)

    summary = _validate_exact_fields(
        candidate["summary"],
        SUMMARY_FIELDS,
        "$.summary",
        required=SUMMARY_FIELDS,
    )
    _validate_exact_fields(
        summary["classificationCounts"],
        CLASSIFICATION_COUNT_FIELDS,
        "$.summary.classificationCounts",
        required=CLASSIFICATION_COUNT_FIELDS,
    )
    _validate_exact_fields(
        summary["presentationPriorityCounts"],
        PRESENTATION_PRIORITY_COUNT_FIELDS,
        "$.summary.presentationPriorityCounts",
        required=PRESENTATION_PRIORITY_COUNT_FIELDS,
    )
    _validate_exact_fields(
        summary["dataStatusCounts"],
        DATA_STATUS_COUNT_FIELDS,
        "$.summary.dataStatusCounts",
        required=DATA_STATUS_COUNT_FIELDS,
    )
    expected_summary = build_v3_summary(candidate["results"])
    _require(
        summary == expected_summary,
        "$.summary diverge da lista final de resultados.",
    )
    _validate_finite_tree(candidate)
    return deepcopy(dict(candidate))


def flatten_v2_results(public_v2: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        {"goalId": str(goal["goalId"]), **dict(result)}
        for goal in public_v2.get("goals") or []
        for result in goal.get("results") or []
    ]


def v2_result_field_inventory(
    public_payloads: Iterable[Mapping[str, Any]],
) -> dict[str, list[str]]:
    top: set[str] = set()
    summary: set[str] = set()
    result: set[str] = set()
    current: set[str] = set()
    for public_v2 in public_payloads:
        top.update(public_v2)
        summary.update((public_v2.get("summary") or {}).keys())
        for item in flatten_v2_results(public_v2):
            result.update(item)
            current.update((item.get("current") or {}).keys())
    return {
        "topLevel": sorted(top),
        "summary": sorted(summary),
        "result": sorted(result),
        "current": sorted(current),
        "deprecatedResultFieldsPresent": sorted(
            result & DEPRECATED_V2_RESULT_FIELDS
        ),
    }


__all__ = [
    "CONTRACT_HASH",
    "DEPRECATED_V2_RESULT_FIELDS",
    "PRESENTATION_POLICY_HASH",
    "PRESENTATION_POLICY_VERSION",
    "PUBLIC_V3_SCHEMA_VERSION",
    "Pne2026PublicDiagnosticV3Error",
    "RESULT_FIELDS",
    "TOP_LEVEL_FIELDS",
    "build_pne2026_public_diagnostic_v3",
    "build_v3_summary",
    "flatten_v2_results",
    "rebase_pne2026_public_diagnostic_v3",
    "validate_pne2026_public_diagnostic_v3",
    "v2_result_field_inventory",
]
