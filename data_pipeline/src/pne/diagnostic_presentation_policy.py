"""Política exclusivamente editorial do Diagnóstico PNE 2026–2036."""

from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from .goal_indicator_contract import CONTRACT


POLICY_PATH = (
    Path(__file__).resolve().parents[3]
    / "contracts"
    / "pne2026-diagnostic-presentation-policy.json"
)
ALLOWED_SUMMARY_PRIORITIES = frozenset({"essential", "standard"})
ALLOWED_RELATION_FIELDS = frozenset(
    {
        "relationId",
        "themeId",
        "displayOrder",
        "summaryPriority",
        "displayGroup",
        "layoutHint",
        "narrativeTemplateId",
    }
)
FORBIDDEN_FIELDS = frozenset(
    {
        "goalId",
        "indicatorId",
        "mode",
        "tracksGoal",
        "tracks_goal",
        "hasDistance",
        "canDistance",
        "canStatus",
        "canProjection",
        "includeInDiagnostic",
        "includeInReferenceSummary",
        "target",
        "reference",
        "deadline",
        "direction",
        "formulaId",
        "sourceIds",
        "territoriality",
        "classificationPolicy",
        "missingPolicy",
        "valuePolicy",
    }
)


class Pne2026DiagnosticPresentationPolicyError(ValueError):
    """Erro estrutural ou referencial na política editorial."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise Pne2026DiagnosticPresentationPolicyError(
            f"Política visual do Diagnóstico PNE 2026 inválida: {message}"
        )


def _forbidden_paths(value: Any, path: str = "$") -> list[str]:
    paths: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if key in FORBIDDEN_FIELDS:
                paths.append(child_path)
            paths.extend(_forbidden_paths(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            paths.extend(_forbidden_paths(child, f"{path}[{index}]"))
    return paths


def validate_policy(
    candidate: dict[str, Any],
    contract: dict[str, Any] = CONTRACT,
) -> dict[str, Any]:
    _require(
        candidate.get("schemaVersion")
        == "pne2026-diagnostic-presentation-policy-v1",
        "schemaVersion não reconhecida",
    )
    _require(candidate.get("policyVersion") == "1.7.0", "policyVersion inválida")
    forbidden_paths = _forbidden_paths(candidate)
    _require(
        not forbidden_paths,
        f"campos metodológicos proibidos: {forbidden_paths}",
    )

    themes = candidate.get("themes")
    _require(isinstance(themes, list) and bool(themes), "themes deve ser uma lista")
    theme_ids: set[str] = set()
    theme_orders: set[int] = set()
    for theme in themes:
        _require(isinstance(theme, dict), "cada tema deve ser um objeto")
        theme_id = theme.get("themeId")
        display_order = theme.get("displayOrder")
        _require(
            isinstance(theme_id, str) and theme_id not in theme_ids,
            f"themeId inválido ou duplicado: {theme_id}",
        )
        _require(
            isinstance(display_order, int)
            and display_order > 0
            and display_order not in theme_orders,
            f"ordem de tema inválida ou duplicada: {display_order}",
        )
        _require(isinstance(theme.get("label"), str), f"{theme_id}.label ausente")
        theme_ids.add(theme_id)
        theme_orders.add(display_order)

    contract_relations = {
        relation["relationId"]: relation for relation in contract["relations"]
    }
    expected_relation_ids = {
        relation["relationId"]
        for relation in contract["relations"]
        if relation["includeInDiagnostic"] is True
        and relation["mode"] != "hidden"
    }
    entries = candidate.get("relations")
    _require(isinstance(entries, list), "relations deve ser uma lista")
    seen_relation_ids: set[str] = set()
    seen_theme_orders: set[tuple[str, int]] = set()
    for entry in entries:
        _require(isinstance(entry, dict), "cada relação visual deve ser um objeto")
        extra_fields = set(entry) - ALLOWED_RELATION_FIELDS
        _require(
            not extra_fields,
            f"relação visual contém campos não editoriais: {sorted(extra_fields)}",
        )
        forbidden_fields = set(entry) & FORBIDDEN_FIELDS
        _require(
            not forbidden_fields,
            f"relação visual contém campos metodológicos: {sorted(forbidden_fields)}",
        )
        relation_id = entry.get("relationId")
        _require(
            isinstance(relation_id, str) and relation_id in contract_relations,
            f"relationId inexistente: {relation_id}",
        )
        _require(
            relation_id not in seen_relation_ids,
            f"relationId duplicado: {relation_id}",
        )
        relation = contract_relations[relation_id]
        _require(
            relation["includeInDiagnostic"] is True,
            f"{relation_id} não é elegível ao Diagnóstico",
        )
        _require(relation["mode"] != "hidden", f"{relation_id} é hidden")
        theme_id = entry.get("themeId")
        _require(theme_id in theme_ids, f"themeId inexistente: {theme_id}")
        display_order = entry.get("displayOrder")
        _require(
            isinstance(display_order, int) and display_order > 0,
            f"{relation_id}.displayOrder inválido",
        )
        theme_order = (str(theme_id), display_order)
        _require(
            theme_order not in seen_theme_orders,
            f"ordem duplicada no tema: {theme_id}:{display_order}",
        )
        _require(
            entry.get("summaryPriority") in ALLOWED_SUMMARY_PRIORITIES,
            f"{relation_id}.summaryPriority inválida",
        )
        seen_relation_ids.add(relation_id)
        seen_theme_orders.add(theme_order)

    _require(
        seen_relation_ids == expected_relation_ids,
        "a política deve cobrir exatamente uma vez todas as relações elegíveis",
    )
    return candidate


with POLICY_PATH.open(encoding="utf-8") as policy_file:
    POLICY = validate_policy(json.load(policy_file))

_POLICY_BY_RELATION_ID = {
    entry["relationId"]: entry for entry in POLICY["relations"]
}


def get_presentation_entry(relation_id: str) -> dict[str, Any] | None:
    entry = _POLICY_BY_RELATION_ID.get(str(relation_id))
    return deepcopy(entry) if entry is not None else None


def load_policy() -> dict[str, Any]:
    return deepcopy(POLICY)


def normalize_policy(value: Any) -> Any:
    if isinstance(value, list):
        return [normalize_policy(item) for item in value]
    if isinstance(value, dict):
        return {
            key: normalize_policy(value[key])
            for key in sorted(value)
        }
    return value


def policy_hash(value: Any = None) -> str:
    normalized = normalize_policy(POLICY if value is None else value)
    serialized = json.dumps(
        normalized,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return sha256(serialized.encode("utf-8")).hexdigest()
