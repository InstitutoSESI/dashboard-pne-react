"""Shared statistical primitives for education-attendance projections.

The production pipeline and the shadow experiment import these functions so
that slope estimation, municipal/state shrinkage and damped extrapolation do
not drift apart.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from statistics import median
from typing import Iterable, Sequence


MINIMUM_TREND_OBSERVATIONS = 5
MAX_ABS_ANNUAL_LOG_TREND = 0.15


@dataclass(frozen=True)
class ShrunkLogTrend:
    """Result of shrinking a municipal log trend toward the state trend."""

    slope: float | None
    municipal_weight: float
    state_weight: float
    fallback: str | None


def damped_effect(damping: float, horizon: int) -> float:
    """Return the cumulative damped effect for a positive integer horizon."""

    damping = float(damping)
    if not math.isfinite(damping) or not 0 < damping < 1:
        raise ValueError("damping deve estar estritamente entre zero e um")
    if isinstance(horizon, bool):
        raise ValueError("horizon deve ser um inteiro positivo")
    numeric_horizon = float(horizon)
    if (
        not math.isfinite(numeric_horizon)
        or not numeric_horizon.is_integer()
        or numeric_horizon <= 0
    ):
        raise ValueError("horizon deve ser um inteiro positivo")
    return float(
        damping
        * (1 - damping ** int(numeric_horizon))
        / (1 - damping)
    )


def theil_sen_log_slope(
    years: Sequence[object] | Iterable[object],
    values: Sequence[object] | Iterable[object],
    *,
    window: int | None,
    excluded_years: Iterable[int] = (),
    minimum_observations: int = MINIMUM_TREND_OBSERVATIONS,
    max_abs_slope: float = MAX_ABS_ANNUAL_LOG_TREND,
) -> tuple[float | None, int]:
    """Estimate a clipped Theil-Sen slope over ``log1p(values)``.

    Invalid points and negative values are ignored. Duplicate years or fewer
    than ``minimum_observations`` valid points make the trend unavailable.
    Zero is a valid enrollment count.
    """

    raw_years = list(years)
    raw_values = list(values)
    if len(raw_years) != len(raw_values):
        return None, 0
    if isinstance(minimum_observations, bool) or minimum_observations < 2:
        raise ValueError("minimum_observations deve ser pelo menos dois")
    if window is not None and (
        isinstance(window, bool) or not isinstance(window, int) or window < 1
    ):
        raise ValueError("window deve ser nulo ou um inteiro positivo")
    max_abs_slope = float(max_abs_slope)
    if not math.isfinite(max_abs_slope) or max_abs_slope <= 0:
        raise ValueError("max_abs_slope deve ser positivo e finito")

    excluded = {int(year) for year in excluded_years}
    points: list[tuple[int, float]] = []
    for raw_year, raw_value in zip(raw_years, raw_values, strict=True):
        try:
            year = float(raw_year)
            value = float(raw_value)
        except (TypeError, ValueError):
            continue
        if (
            not math.isfinite(year)
            or not year.is_integer()
            or int(year) in excluded
            or not math.isfinite(value)
            or value < 0
        ):
            continue
        points.append((int(year), value))

    points.sort(key=lambda point: point[0])
    if window is not None and len(points) > window:
        points = points[-window:]
    count = len(points)
    point_years = [year for year, _ in points]
    if count < minimum_observations or len(set(point_years)) != count:
        return None, count

    slopes: list[float] = []
    logged = [math.log1p(value) for _, value in points]
    for left in range(count):
        for right in range(left + 1, count):
            year_delta = point_years[right] - point_years[left]
            if year_delta <= 0:
                continue
            slopes.append((logged[right] - logged[left]) / year_delta)
    if not slopes:
        return None, count

    slope = float(median(slopes))
    return max(-max_abs_slope, min(max_abs_slope, slope)), count


def combine_municipal_state_log_trends(
    state_slope: float | None,
    municipal_slope: float | None,
    municipal_observations: int,
    shrinkage: float,
) -> ShrunkLogTrend:
    """Shrink a municipal slope toward the state slope deterministically."""

    shrinkage = float(shrinkage)
    if not math.isfinite(shrinkage) or shrinkage <= 0:
        raise ValueError("shrinkage deve ser positivo e finito")
    if (
        state_slope is None
        or not math.isfinite(float(state_slope))
    ):
        return ShrunkLogTrend(
            slope=None,
            municipal_weight=0.0,
            state_weight=0.0,
            fallback="persistence_missing_state_trend",
        )
    if (
        municipal_slope is None
        or not math.isfinite(float(municipal_slope))
        or municipal_observations <= 0
    ):
        return ShrunkLogTrend(
            slope=float(state_slope),
            municipal_weight=0.0,
            state_weight=1.0,
            fallback="state_only_missing_municipal_trend",
        )

    municipal_weight = float(
        municipal_observations / (municipal_observations + shrinkage)
    )
    state_weight = 1.0 - municipal_weight
    return ShrunkLogTrend(
        slope=(
            municipal_weight * float(municipal_slope)
            + state_weight * float(state_slope)
        ),
        municipal_weight=municipal_weight,
        state_weight=state_weight,
        fallback=None,
    )


def forecast_damped_log_value(
    base_value: float,
    annual_log_slope: float,
    damping: float,
    horizon: int,
) -> float | None:
    """Forecast a non-negative count from a damped annual log trend."""

    try:
        base_value = float(base_value)
        annual_log_slope = float(annual_log_slope)
    except (TypeError, ValueError):
        return None
    if (
        not math.isfinite(base_value)
        or base_value < 0
        or not math.isfinite(annual_log_slope)
    ):
        return None
    try:
        modeled_value = math.expm1(
            math.log1p(base_value)
            + annual_log_slope * damped_effect(damping, horizon)
        )
    except (OverflowError, ValueError):
        return None
    if not math.isfinite(modeled_value):
        return None
    return max(0.0, float(modeled_value))
