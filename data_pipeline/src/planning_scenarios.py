"""Promote approved projection-v2 contracts to public planning scenarios."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Iterable

from src.pne.goal_indicator_contract import (
    CONTRACT,
    get_formula_for_indicator,
    get_indicator,
    get_indicator_reference_profile,
)

PUBLIC_CONTRACT_VERSION = "planning-scenarios-v1"
APPROVED_MODEL = "last_components"
CYCLE_END_YEAR = int(CONTRACT["cycle"]["endYear"])
INDICATOR_KEYS = (
    "basico_integral",
    "escolas_integral",
    "pos_graduacao",
    "temporarios",
)


def load_approved_planning_scenarios(
    artifact_root: Path,
    municipalities: Iterable[str],
) -> dict[str, Any]:
    """Build the canonical aggregate payload from the approved shadow run."""
    expected_municipalities = tuple(str(name) for name in municipalities)
    if len(expected_municipalities) != 497:
        raise ValueError(
            f"Expected 497 municipalities, found {len(expected_municipalities)}"
        )

    contracts_by_indicator: dict[str, dict[str, dict[str, Any]]] = {}
    experiment_version: str | None = None
    for indicator_key in INDICATOR_KEYS:
        artifact = _load_json(
            artifact_root / "shadow-projections" / f"{indicator_key}.json"
        )
        _validate_artifact_envelope(artifact, indicator_key)
        artifact_version = str(artifact.get("experimentVersion") or "")
        if experiment_version is None:
            experiment_version = artifact_version
        elif experiment_version != artifact_version:
            raise ValueError("Approved artifacts use different experiment versions")

        by_municipality: dict[str, dict[str, Any]] = {}
        for contract in artifact.get("projections", []):
            municipality = str(contract.get("municipality") or "")
            _validate_contract(contract, indicator_key, municipality)
            by_municipality[municipality] = _to_public_contract(contract)
        contracts_by_indicator[indicator_key] = by_municipality

    municipality_set = set(expected_municipalities)
    for indicator_key, contracts in contracts_by_indicator.items():
        missing = sorted(municipality_set - set(contracts))
        unexpected = sorted(set(contracts) - municipality_set)
        if missing or unexpected:
            raise ValueError(
                f"{indicator_key}: municipality mismatch; "
                f"missing={missing[:5]}, unexpected={unexpected[:5]}"
            )

    return {
        "contractVersion": PUBLIC_CONTRACT_VERSION,
        "sourceExperimentVersion": experiment_version,
        "publicationStatus": "published",
        "scenarioType": "maintenance",
        "municipalityCount": len(expected_municipalities),
        "indicatorKeys": list(INDICATOR_KEYS),
        "municipios": {
            municipality: {
                indicator_key: contracts_by_indicator[indicator_key][municipality]
                for indicator_key in INDICATOR_KEYS
            }
            for municipality in expected_municipalities
        },
    }


def build_reference_trajectory(
    contract: dict[str, Any],
) -> list[dict[str, float | int]]:
    historical = [
        point
        for point in contract.get("historical", [])
        if _is_number(point.get("year")) and _is_number(point.get("value"))
    ]
    targets = sorted(
        (target for target in contract.get("targets", []) if _is_number(target.get("year")) and _is_number(target.get("value"))),
        key=lambda point: point["year"],
    )
    if not historical or not targets:
        return []

    latest = max(historical, key=lambda point: point["year"])
    latest_year = int(latest["year"])
    required_value = float(latest["value"])
    waypoints = [{"year": latest_year, "value": required_value}]
    for target in targets:
        target_year = int(target["year"])
        if target_year <= latest_year:
            continue
        target_value = float(target["value"])
        required_value = (
            min(required_value, target_value)
            if contract.get("direction") == "at_most"
            else max(required_value, target_value)
        )
        waypoints.append({"year": target_year, "value": required_value})

    projection_end = max(
        CYCLE_END_YEAR,
        max(int(target["year"]) for target in targets),
    )
    if waypoints[-1]["year"] != projection_end:
        waypoints.append({"year": projection_end, "value": required_value})

    trajectory = []
    for year in range(latest_year, projection_end + 1):
        right_index = next(
            index for index, point in enumerate(waypoints) if point["year"] >= year
        )
        right = waypoints[right_index]
        left = waypoints[max(0, right_index - 1)]
        span = right["year"] - left["year"]
        progress = (year - left["year"]) / span if span > 0 else 0
        value = left["value"] + (right["value"] - left["value"]) * progress
        trajectory.append({"year": year, "value": round(value, 6)})
    return trajectory


def build_reference_targets(
    contract: dict[str, Any],
    trajectory: list[dict[str, float | int]],
) -> list[dict[str, Any]]:
    historical = [
        point
        for point in contract.get("historical", [])
        if _is_number(point.get("year")) and _is_number(point.get("value"))
    ]
    if not historical or not trajectory:
        return []

    latest = max(historical, key=lambda point: point["year"])
    previous_year = int(latest["year"])
    previous_value = float(latest["value"])
    trajectory_by_year = {int(point["year"]): float(point["value"]) for point in trajectory}
    targets = []
    for target in sorted(contract.get("targets", []), key=lambda point: point.get("year", 0)):
        target_year = int(target["year"])
        if target_year <= previous_year or target_year not in trajectory_by_year:
            continue
        required_value = trajectory_by_year[target_year]
        annual_pace = (required_value - previous_value) / (target_year - previous_year)
        targets.append(
            {
                "year": target_year,
                "value": float(target["value"]),
                "type": target.get("type", "configured_reference"),
                **(
                    {"referenceId": target["referenceId"]}
                    if target.get("referenceId")
                    else {}
                ),
                "requiredAnnualPacePp": round(annual_pace, 6),
            }
        )
        previous_year = target_year
        previous_value = required_value
    return targets


def _to_public_contract(contract: dict[str, Any]) -> dict[str, Any]:
    indicator_key = str(contract["indicatorKey"])
    observed_years = [
        int(point["year"])
        for point in contract.get("historical", [])
        if _is_number(point.get("year"))
    ]
    reference = get_indicator_reference_profile(
        indicator_key,
        max(observed_years) if observed_years else None,
    )
    reference_contract = dict(contract)
    if reference and reference["kind"] == "legal":
        reference_contract["direction"] = reference["direction"]
        reference_contract["targets"] = [
            {
                **milestone,
                "type": "official_law_reference",
                "referenceId": reference["referenceId"],
            }
            for milestone in reference["milestones"]
        ]
    trajectory = build_reference_trajectory(reference_contract)
    targets = build_reference_targets(reference_contract, trajectory)
    indicator = get_indicator(indicator_key) or {}
    formula = get_formula_for_indicator(indicator_key) or {}
    return {
        "contractVersion": PUBLIC_CONTRACT_VERSION,
        "indicatorKey": indicator_key,
        "strategy": contract["strategy"],
        "scenarioType": "maintenance",
        "status": contract["status"],
        "direction": reference_contract["direction"],
        "referenceKind": reference["kind"] if reference else "configured",
        "referenceId": reference["referenceId"] if reference else None,
        "targetValidationStatus": (
            reference["validationStatus"]
            if reference and reference["kind"] == "legal"
            else "configured_unvalidated"
        ),
        "formulaId": indicator.get("formulaId"),
        "formula": {
            key: formula[key]
            for key in (
                "implementationKey",
                "description",
                "numerator",
                "denominator",
            )
            if formula.get(key) is not None
        },
        "sourcePeriod": contract.get("sourcePeriod"),
        "projectionPeriod": contract.get("projectionPeriod"),
        "targets": targets,
        "historical": contract.get("historical", []),
        "projected": contract.get("projected", []),
        "referenceTrajectory": trajectory,
        "summary": contract.get("summary", {}),
        "diagnostics": contract.get("diagnostics", {}),
        "qualityEvidence": contract.get("qualityEvidence", {}),
        "model": APPROVED_MODEL,
    }


def _validate_artifact_envelope(artifact: dict[str, Any], indicator_key: str) -> None:
    if artifact.get("mode") != "shadow" or artifact.get("productionDecision") is not False:
        raise ValueError(f"{indicator_key}: source is not an approved shadow artifact")
    if artifact.get("selectedShadowModel") != APPROVED_MODEL:
        raise ValueError(f"{indicator_key}: approved model must be {APPROVED_MODEL}")


def _validate_contract(
    contract: dict[str, Any], indicator_key: str, municipality: str
) -> None:
    if not municipality:
        raise ValueError(f"{indicator_key}: contract without municipality")
    if contract.get("indicatorKey") != indicator_key:
        raise ValueError(f"{indicator_key}: mismatched contract key")
    if contract.get("model") != APPROVED_MODEL:
        raise ValueError(f"{indicator_key}/{municipality}: invalid approved model")
    if contract.get("targetValidationStatus") != "configured_unvalidated":
        raise ValueError(
            f"{indicator_key}/{municipality}: invalid target validation status"
        )
    if contract.get("strategy") != "ratio_of_counts":
        raise ValueError(f"{indicator_key}/{municipality}: invalid strategy")

    historical = contract.get("historical")
    projected = contract.get("projected")
    if not isinstance(historical, list) or not historical:
        raise ValueError(f"{indicator_key}/{municipality}: missing historical series")
    if not isinstance(projected, list) or not projected:
        raise ValueError(f"{indicator_key}/{municipality}: missing projected series")

    historical_years = [point.get("year") for point in historical]
    if not all(_is_number(year) and float(year).is_integer() for year in historical_years):
        raise ValueError(f"{indicator_key}/{municipality}: invalid historical year")
    historical_years = [int(year) for year in historical_years]
    if (
        historical_years != sorted(set(historical_years))
        or any(
            right - left != 1
            for left, right in zip(historical_years, historical_years[1:])
        )
    ):
        raise ValueError(
            f"{indicator_key}/{municipality}: historical years must be unique and consecutive"
        )

    source_period = contract.get("sourcePeriod") or {}
    if (
        source_period.get("startYear") != historical_years[0]
        or source_period.get("endYear") != historical_years[-1]
    ):
        raise ValueError(f"{indicator_key}/{municipality}: invalid source period")

    latest = historical[-1]
    latest_numerator = latest.get("numerator")
    latest_denominator = latest.get("denominator")
    if (
        not _is_number(latest_numerator)
        or not _is_number(latest_denominator)
        or float(latest_numerator) < 0
        or float(latest_denominator) <= 0
    ):
        raise ValueError(
            f"{indicator_key}/{municipality}: invalid latest components"
        )
    latest_numerator = float(latest_numerator)
    latest_denominator = float(latest_denominator)
    latest_value = 100.0 * latest_numerator / latest_denominator

    projection_period = contract.get("projectionPeriod") or {}
    projection_start = projection_period.get("startYear")
    projection_end = projection_period.get("endYear")
    if (
        not _is_number(projection_start)
        or not _is_number(projection_end)
        or not float(projection_start).is_integer()
        or not float(projection_end).is_integer()
    ):
        raise ValueError(f"{indicator_key}/{municipality}: invalid projection period")
    projection_start = int(projection_start)
    projection_end = int(projection_end)
    if (
        projection_start != historical_years[-1] + 1
        or projection_end != CYCLE_END_YEAR
    ):
        raise ValueError(
            f"{indicator_key}/{municipality}: projection period is not aligned to the cycle"
        )

    expected_years = list(range(projection_start, projection_end + 1))
    projected_years = [point.get("year") for point in projected]
    if projected_years != expected_years:
        raise ValueError(
            f"{indicator_key}/{municipality}: projected years must be complete and consecutive"
        )

    for point in projected:
        if point.get("status") != "available":
            raise ValueError(
                f"{indicator_key}/{municipality}: persistence point is unavailable"
            )
        for field, expected in (
            ("rawNumerator", latest_numerator),
            ("numerator", latest_numerator),
            ("rawDenominator", latest_denominator),
            ("denominator", latest_denominator),
            ("rawValue", latest_value),
            ("displayValue", latest_value),
        ):
            value = point.get(field)
            if not _is_number(value) or not math.isclose(
                float(value),
                expected,
                rel_tol=0,
                abs_tol=1e-5,
            ):
                raise ValueError(
                    f"{indicator_key}/{municipality}: {field} violates "
                    "last-components persistence"
                )
        if point.get("boundedValue") is not None or point.get("limitsApplied"):
            raise ValueError(
                f"{indicator_key}/{municipality}: persistence cannot apply hidden bounds"
            )


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)
