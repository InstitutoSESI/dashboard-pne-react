"""Primitivas reproduzíveis do laboratório analítico V7 — Job 3."""

from __future__ import annotations

import math
import re
from typing import Any, Iterable, Sequence

import numpy as np
import pandas as pd


SCHEMA_VERSION = "vocacoes-pne-v7-job3-v1"
JOB_ID = "v7-job3"
IBGE_CODE_PATTERN = re.compile(r"^[0-9]{7}$")
CANDIDATE_IDS = (
    "H1_DEMOGRAFIA_REDE",
    "H2_TRAJETORIA_PERMANENCIA",
    "H3_TRABALHO_JUVENIL_MEDIO",
    "H4_EJA_DISTRIBUICAO",
    "A1_COORTES_REDE",
    "A2_TRABALHO_PERMANENCIA",
    "A3_OCUPACOES_FORMACAO",
)
FINAL_STATUSES = frozenset(
    {
        "ANALYTICALLY_ELIGIBLE",
        "REVIEW_REQUIRED",
        "RETAINED",
        "BLOCKED_WITH_EVIDENCE",
    }
)
CHECK_STATES = frozenset({"APPROVED", "REVIEW_REQUIRED", "FAILED", "PENDING_EDITORIAL"})


def require_ibge_code(value: Any) -> str:
    if not isinstance(value, str) or not IBGE_CODE_PATTERN.fullmatch(value):
        raise ValueError(f"Código IBGE municipal inválido: {value!r}.")
    return value


def validate_ibge_codes(values: Iterable[Any], *, expected_count: int | None = None) -> list[str]:
    codes = [require_ibge_code(value) for value in values]
    if len(codes) != len(set(codes)):
        raise ValueError("O conjunto municipal contém códigos IBGE duplicados.")
    if expected_count is not None and len(codes) != expected_count:
        raise ValueError(
            f"Contagem municipal inválida: {len(codes)}; esperado {expected_count}."
        )
    return codes


def finite_or_none(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    numeric = float(value)
    if not math.isfinite(numeric):
        raise ValueError(f"Valor não finito: {value!r}.")
    return numeric


def safe_ratio(numerator: Any, denominator: Any, *, multiplier: float = 1.0) -> float | None:
    num = finite_or_none(numerator)
    den = finite_or_none(denominator)
    if num is None or den is None or den == 0:
        return None
    return finite_or_none(num / den * multiplier)


def relative_change(start: Any, end: Any) -> float | None:
    start_value = finite_or_none(start)
    end_value = finite_or_none(end)
    if start_value is None or end_value is None or start_value == 0:
        return None
    return (end_value - start_value) / start_value


def direction(start: Any, end: Any, *, relative_tolerance: float = 0.005) -> str:
    start_value = finite_or_none(start)
    end_value = finite_or_none(end)
    if start_value is None or end_value is None:
        return "unavailable"
    scale = max(abs(start_value), 1.0)
    change = end_value - start_value
    if abs(change) <= relative_tolerance * scale:
        return "stable"
    return "increase" if change > 0 else "decrease"


def direction_vs_region(local_change: Any, regional_change: Any) -> str:
    local = finite_or_none(local_change)
    regional = finite_or_none(regional_change)
    if local is None or regional is None:
        return "unavailable"
    local_sign = 0 if abs(local) < 1e-12 else (1 if local > 0 else -1)
    regional_sign = 0 if abs(regional) < 1e-12 else (1 if regional > 0 else -1)
    if local_sign == regional_sign:
        return "same_direction"
    if local_sign == 0:
        return "local_stable_region_changed"
    if regional_sign == 0:
        return "local_changed_region_stable"
    return "opposite_direction"


def shapley_m_equals_p_times_r(
    *, population_start: Any, population_end: Any, enrollment_start: Any, enrollment_end: Any
) -> dict[str, float | None]:
    """Decompõe exatamente delta M em parcela população e parcela relação M/P."""

    p0 = finite_or_none(population_start)
    p1 = finite_or_none(population_end)
    m0 = finite_or_none(enrollment_start)
    m1 = finite_or_none(enrollment_end)
    if None in (p0, p1, m0, m1) or p0 == 0 or p1 == 0:
        return {
            "relation_start": None,
            "relation_end": None,
            "enrollment_change": None,
            "population_component": None,
            "relation_component": None,
            "closure_residual": None,
        }
    assert p0 is not None and p1 is not None and m0 is not None and m1 is not None
    r0 = m0 / p0
    r1 = m1 / p1
    population_component = (p1 - p0) * (r0 + r1) / 2.0
    relation_component = (r1 - r0) * (p0 + p1) / 2.0
    enrollment_change = m1 - m0
    return {
        "relation_start": r0,
        "relation_end": r1,
        "enrollment_change": enrollment_change,
        "population_component": population_component,
        "relation_component": relation_component,
        "closure_residual": enrollment_change - population_component - relation_component,
    }


def leave_one_out_directions(
    frame: pd.DataFrame,
    *,
    municipality_column: str,
    year_column: str,
    value_column: str,
    start_year: int,
    end_year: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    municipalities = sorted(frame[municipality_column].dropna().astype(str).unique())
    for municipality in municipalities:
        subset = frame[frame[municipality_column].astype(str).ne(municipality)]
        values = subset.groupby(year_column)[value_column].sum(min_count=1)
        start = values.get(start_year)
        end = values.get(end_year)
        rows.append(
            {
                "excluded_municipality_id": municipality,
                "start_value": finite_or_none(start),
                "end_value": finite_or_none(end),
                "relative_change": relative_change(start, end),
                "direction": direction(start, end),
            }
        )
    return rows


def bh_adjust(p_values: Sequence[float | None]) -> list[float | None]:
    valid = [(index, float(value)) for index, value in enumerate(p_values) if value is not None]
    result: list[float | None] = [None] * len(p_values)
    if not valid:
        return result
    ordered = sorted(valid, key=lambda item: item[1])
    count = len(ordered)
    adjusted = [0.0] * count
    running = 1.0
    for position in range(count - 1, -1, -1):
        _, p_value = ordered[position]
        candidate = min(1.0, p_value * count / (position + 1))
        running = min(running, candidate)
        adjusted[position] = running
    for (index, _), value in zip(ordered, adjusted, strict=True):
        result[index] = value
    return result


def _weighted_group_mean(
    matrix: np.ndarray, groups: np.ndarray, weights: np.ndarray
) -> np.ndarray:
    result = np.zeros_like(matrix, dtype=float)
    for group in np.unique(groups):
        mask = groups == group
        group_weights = weights[mask]
        denominator = group_weights.sum()
        if denominator <= 0:
            raise ValueError("Ponderador de grupo não positivo.")
        mean = (matrix[mask] * group_weights[:, None]).sum(axis=0) / denominator
        result[mask] = mean
    return result


def two_way_within(
    matrix: np.ndarray,
    municipalities: Sequence[Any],
    years: Sequence[Any],
    weights: Sequence[float] | None = None,
    *,
    tolerance: float = 1e-11,
    maximum_iterations: int = 500,
) -> tuple[np.ndarray, int]:
    values = np.asarray(matrix, dtype=float)
    if values.ndim == 1:
        values = values[:, None]
    municipality_groups = np.asarray(municipalities)
    year_groups = np.asarray(years)
    observation_weights = (
        np.ones(len(values), dtype=float)
        if weights is None
        else np.asarray(weights, dtype=float)
    )
    transformed = values.copy()
    for iteration in range(1, maximum_iterations + 1):
        previous = transformed.copy()
        transformed -= _weighted_group_mean(
            transformed, municipality_groups, observation_weights
        )
        transformed -= _weighted_group_mean(transformed, year_groups, observation_weights)
        if np.max(np.abs(transformed - previous)) <= tolerance:
            return transformed, iteration
    raise RuntimeError("Desmediação em dois sentidos não convergiu.")


def _normal_two_sided_p(statistic: float) -> float:
    return math.erfc(abs(statistic) / math.sqrt(2.0))


def fit_clustered_panel(
    frame: pd.DataFrame,
    *,
    outcome: str,
    factors: Sequence[str],
    municipality: str,
    year: str,
    weights: str | None = None,
    fixed_effects: bool = True,
) -> dict[str, Any]:
    required = [outcome, *factors, municipality, year]
    if weights is not None:
        required.append(weights)
    sample = frame[required].copy()
    for column in [outcome, *factors] + ([weights] if weights else []):
        sample[column] = pd.to_numeric(sample[column], errors="coerce")
    sample = sample.dropna()
    if weights is None:
        sample["_weight"] = 1.0
    else:
        sample["_weight"] = sample[weights]
        sample = sample[sample["_weight"].gt(0)]
    if len(sample) < 20 or sample[municipality].nunique() < 5 or sample[year].nunique() < 2:
        raise ValueError("Cobertura insuficiente para o modelo em painel.")

    y = sample[[outcome]].to_numpy(dtype=float)
    x = sample[list(factors)].to_numpy(dtype=float)
    w = sample["_weight"].to_numpy(dtype=float)
    if fixed_effects:
        joined = np.column_stack([y, x])
        transformed, iterations = two_way_within(
            joined,
            sample[municipality].to_numpy(),
            sample[year].to_numpy(),
            w,
        )
        y_work = transformed[:, 0]
        x_work = transformed[:, 1:]
        design_labels = list(factors)
    else:
        y_work = y[:, 0]
        x_work = np.column_stack([np.ones(len(sample)), x])
        design_labels = ["intercept", *factors]
        iterations = 0

    sqrt_w = np.sqrt(w)
    x_weighted = x_work * sqrt_w[:, None]
    y_weighted = y_work * sqrt_w
    xtx = x_weighted.T @ x_weighted
    if np.linalg.matrix_rank(xtx) < xtx.shape[0]:
        raise ValueError("Matriz singular no modelo.")
    xtx_inverse = np.linalg.inv(xtx)
    coefficients = xtx_inverse @ (x_weighted.T @ y_weighted)
    residuals = y_work - x_work @ coefficients

    meat = np.zeros_like(xtx)
    group_values = sample[municipality].to_numpy()
    for group in np.unique(group_values):
        mask = group_values == group
        score = x_work[mask].T @ (w[mask] * residuals[mask])
        meat += np.outer(score, score)
    municipality_count = int(sample[municipality].nunique())
    observation_count = int(len(sample))
    parameter_count = int(len(coefficients))
    correction = municipality_count / (municipality_count - 1)
    correction *= (observation_count - 1) / max(observation_count - parameter_count, 1)
    covariance = correction * xtx_inverse @ meat @ xtx_inverse
    standard_errors = np.sqrt(np.maximum(np.diag(covariance), 0.0))

    coefficient_rows = []
    for label, coefficient, standard_error in zip(
        design_labels, coefficients, standard_errors, strict=True
    ):
        statistic = (
            float(coefficient / standard_error) if standard_error > 0 else float("inf")
        )
        coefficient_rows.append(
            {
                "term": label,
                "coefficient": float(coefficient),
                "standard_error_clustered": float(standard_error),
                "z_statistic": statistic,
                "p_value_raw": _normal_two_sided_p(statistic),
            }
        )
    return {
        "outcome": outcome,
        "factors": list(factors),
        "fixed_effects": fixed_effects,
        "standard_errors": "clustered_by_municipality",
        "weight": weights or "unweighted",
        "observations": observation_count,
        "municipalities": municipality_count,
        "years": sorted(int(value) for value in sample[year].unique()),
        "within_iterations": iterations,
        "null_treatment": "complete_cases_for_declared_specification",
        "coefficients": coefficient_rows,
    }


def standardized_distance_comparators(
    frame: pd.DataFrame,
    *,
    municipality_column: str,
    target: str,
    variables: Sequence[str],
    count: int = 3,
) -> dict[str, Any]:
    sample = frame[[municipality_column, *variables]].copy()
    for variable in variables:
        sample[variable] = pd.to_numeric(sample[variable], errors="coerce")
        sample[variable] = sample[variable].fillna(sample[variable].median())
        standard_deviation = sample[variable].std(ddof=0)
        if standard_deviation == 0 or pd.isna(standard_deviation):
            sample[f"z_{variable}"] = 0.0
        else:
            sample[f"z_{variable}"] = (
                sample[variable] - sample[variable].mean()
            ) / standard_deviation
    target_rows = sample[sample[municipality_column].eq(target)]
    if len(target_rows) != 1:
        raise ValueError("Município-alvo ausente ou duplicado no comparador.")
    z_columns = [f"z_{variable}" for variable in variables]
    target_vector = target_rows[z_columns].iloc[0].to_numpy(dtype=float)
    sample["distance"] = np.sqrt(
        ((sample[z_columns].to_numpy(dtype=float) - target_vector) ** 2).sum(axis=1)
    )
    selected = (
        sample[sample[municipality_column].ne(target)]
        .sort_values(["distance", municipality_column], kind="mergesort")
        .head(count)
    )
    return {
        "variables": list(variables),
        "selected": [
            {
                "municipality_id": row[municipality_column],
                "distance": float(row["distance"]),
            }
            for _, row in selected.iterrows()
        ],
    }


def validate_candidate_registry(payload: dict[str, Any]) -> None:
    entries = payload.get("candidates")
    if not isinstance(entries, list) or len(entries) != 7:
        raise ValueError("O registro deve conter exatamente sete candidatas.")
    ids = [entry.get("id") for entry in entries]
    if tuple(ids) != CANDIDATE_IDS:
        raise ValueError(f"Ordem/identidade de candidatas inválida: {ids!r}.")
    required = {
        "id", "direction", "question", "status", "mechanism", "local_references",
        "data_inputs", "grain", "lenses", "period", "temporal_nature",
        "education_fact_ids", "territorial_fact_ids", "regional_result",
        "municipal_distribution", "nova_santa_rita", "state_comparison",
        "similar_municipalities", "models", "robustness",
        "demography_only_counterfactual", "decision_delta", "planning_components",
        "institutional_responsibility", "monitoring_indicators",
        "maximum_supported_claim", "prohibited_claims", "checks",
        "retention_or_block_reason", "recommended_visual_data", "traceability",
    }
    for entry in entries:
        missing = required - set(entry)
        if missing:
            raise ValueError(f"{entry.get('id')}: campos ausentes {sorted(missing)}.")
        if entry["status"] not in FINAL_STATUSES:
            raise ValueError(f"{entry['id']}: estado final inválido.")
        checks = entry["checks"]
        if set(checks) != {f"C{index}" for index in range(1, 13)}:
            raise ValueError(f"{entry['id']}: matriz C1-C12 incompleta.")
        if checks["C9"] != "PENDING_EDITORIAL":
            raise ValueError(f"{entry['id']}: C9 deve permanecer PENDING_EDITORIAL.")
        if any(value not in CHECK_STATES for value in checks.values()):
            raise ValueError(f"{entry['id']}: estado de check inválido.")
