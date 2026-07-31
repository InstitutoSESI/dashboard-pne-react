"""Trend classification for municipal PNE indicator series.

The public artifact intentionally keeps the audit fields produced here.  The
React application only presents the already-classified direction.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping, Sequence
from statistics import median
from typing import Any


TREND_METHOD_VERSION = "theil_sen_v1"
PERCENT_THRESHOLD_VERSION = "percent_tau_mad_v1"
ABSOLUTE_THRESHOLD_VERSION = "absolute_tau_mad_v1"
WINDOW_YEARS = 5
MIN_OBSERVATIONS = 3
BASE_PERCENT_THRESHOLD = 0.5
MIN_CONSISTENCY = 2 / 3

TREND_LABELS = {
    "up": "Alta",
    "stable": "Estável",
    "down": "Queda",
}

_BREAK_MARKER_KEYS = (
    "methodology_break",
    "methodological_break",
    "metodologia_break",
    "quebra_metodologica",
)


def _empty_trend(reason: str, *, observations: int = 0) -> dict[str, Any]:
    return {
        "status": "unavailable",
        "label": None,
        "start_year": None,
        "end_year": None,
        "observations": observations,
        "method": TREND_METHOD_VERSION,
        "slope": None,
        "threshold": None,
        "consistency": None,
        "unavailable_reason": reason,
        "threshold_method": PERCENT_THRESHOLD_VERSION,
    }


def _finite_number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _integer_year(value: Any) -> int | None:
    number = _finite_number(value)
    if number is None or not number.is_integer():
        return None
    return int(number)


def _point_values(point: Mapping[str, Any]) -> tuple[int | None, float | None]:
    year = point.get("ano", point.get("year"))
    value = point.get("valor", point.get("value"))
    return _integer_year(year), _finite_number(value)


def _has_break_marker(point: Mapping[str, Any]) -> bool:
    return any(bool(point.get(key)) for key in _BREAK_MARKER_KEYS)


def _normalize_break_years(break_years: Iterable[Any] | None) -> set[int]:
    if break_years is None:
        return set()
    normalized = set()
    for year in break_years:
        parsed = _integer_year(year)
        if parsed is not None:
            normalized.add(parsed)
    return normalized


def _annualized_deltas(points: Sequence[tuple[int, float]]) -> list[float]:
    return [
        (right_value - left_value) / (right_year - left_year)
        for (left_year, left_value), (right_year, right_value) in zip(
            points,
            points[1:],
        )
        if right_year > left_year
    ]


def _theil_sen_slope(points: Sequence[tuple[int, float]]) -> float | None:
    slopes = [
        (right_value - left_value) / (right_year - left_year)
        for index, (left_year, left_value) in enumerate(points)
        for right_year, right_value in points[index + 1 :]
        if right_year > left_year
    ]
    if not slopes:
        return None
    slope = float(median(slopes))
    return slope if math.isfinite(slope) else None


def _mad(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    center = float(median(values))
    return float(median([abs(value - center) for value in values]))


def _consistency(slope: float, deltas: Sequence[float]) -> float:
    if not deltas:
        return 0.0

    if slope > 0:
        matching = sum(delta > 0 for delta in deltas)
        return matching / len(deltas)
    if slope < 0:
        matching = sum(delta < 0 for delta in deltas)
        return matching / len(deltas)

    non_zero = [delta for delta in deltas if delta != 0]
    if not non_zero:
        return 1.0
    positive = sum(delta > 0 for delta in non_zero)
    negative = sum(delta < 0 for delta in non_zero)
    return max(positive, negative) / len(non_zero)


def _is_oscillating(deltas: Sequence[float]) -> bool:
    signs = [1 if delta > 0 else -1 for delta in deltas if delta != 0]
    return bool(signs and 1 in signs and -1 in signs)


def _threshold(deltas: Sequence[float], value_type: str) -> tuple[float, str]:
    mad = _mad(deltas)
    if value_type == "count":
        return max(BASE_PERCENT_THRESHOLD, 0.5 * mad), ABSOLUTE_THRESHOLD_VERSION
    return max(BASE_PERCENT_THRESHOLD, 0.5 * mad), PERCENT_THRESHOLD_VERSION


def calculate_trend(
    series: Iterable[Mapping[str, Any]] | None,
    card_end_year: Any,
    *,
    value_type: str = "percent",
    methodology_break_years: Iterable[Any] | None = None,
    observation_interval_years: int = 1,
) -> dict[str, Any]:
    """Classify the latest five calendar years ending at ``card_end_year``.

    Invalid observations are ignored, never imputed.  A three-observation
    window is eligible only when its years are consecutive.  Four or five
    valid observations may contain gaps; Theil–Sen and annualized deltas use
    the actual year distance in that case.
    """

    end_year = _integer_year(card_end_year)
    if end_year is None:
        return _empty_trend("invalid_card_end_year")
    if series is None or isinstance(series, (str, bytes, bytearray)):
        return _empty_trend("missing_history")

    try:
        raw_points = list(series)
    except TypeError:
        return _empty_trend("invalid_history")

    points: list[tuple[int, float]] = []
    break_years = _normalize_break_years(methodology_break_years)
    for raw_point in raw_points:
        if not isinstance(raw_point, Mapping):
            continue
        year, value = _point_values(raw_point)
        if _has_break_marker(raw_point) and year is not None:
            break_years.add(year)
        if year is None or value is None:
            continue
        points.append((year, value))

    if not points:
        return _empty_trend("missing_history")

    years = [year for year, _ in points]
    if len(years) != len(set(years)):
        return _empty_trend("duplicate_year", observations=len(points))

    points.sort(key=lambda point: point[0])
    window_start = end_year - WINDOW_YEARS + 1
    window_points = [
        point for point in points if window_start <= point[0] <= end_year
    ]

    if not window_points or window_points[-1][0] != end_year:
        return _empty_trend("history_does_not_end_at_card_year", observations=len(window_points))

    if any(window_start <= year <= end_year for year in break_years):
        return _empty_trend("methodology_break", observations=len(window_points))

    observations = len(window_points)
    if observations < MIN_OBSERVATIONS:
        return _empty_trend("insufficient_observations", observations=observations)
    if (
        not isinstance(observation_interval_years, int)
        or isinstance(observation_interval_years, bool)
        or observation_interval_years < 1
    ):
        return _empty_trend("invalid_observation_interval", observations=observations)
    if observations == MIN_OBSERVATIONS:
        consecutive = all(
            right_year - left_year == observation_interval_years
            for (left_year, _), (right_year, _) in zip(
                window_points,
                window_points[1:],
            )
        )
        if not consecutive:
            return _empty_trend(
                "three_observations_not_frequency_compatible",
                observations=observations,
            )

    deltas = _annualized_deltas(window_points)
    slope = _theil_sen_slope(window_points)
    if slope is None or not deltas:
        return _empty_trend("insufficient_variation", observations=observations)

    threshold, threshold_method = _threshold(deltas, value_type)
    consistency = _consistency(slope, deltas)
    absolute_slope = abs(slope)

    # Stable is reserved for histories without opposing annual directions.
    # This guard keeps a genuinely oscillating history from being presented as
    # stable merely because its robust slope is close to zero.
    if absolute_slope <= threshold:
        status = "inconclusive" if _is_oscillating(deltas) else "stable"
    elif slope > 0:
        status = "up" if consistency >= MIN_CONSISTENCY else "inconclusive"
    else:
        status = "down" if consistency >= MIN_CONSISTENCY else "inconclusive"

    return {
        "status": status,
        "label": TREND_LABELS.get(status),
        "start_year": window_points[0][0],
        "end_year": end_year,
        "observations": observations,
        "method": TREND_METHOD_VERSION,
        "slope": slope,
        "threshold": threshold,
        "consistency": consistency,
        "unavailable_reason": None,
        "threshold_method": threshold_method,
    }


def attach_trend(
    result: Mapping[str, Any] | None,
    *,
    value_type: str = "percent",
    methodology_break_years: Iterable[Any] | None = None,
    observation_interval_years: int = 1,
) -> dict[str, Any]:
    """Return a result copy with a pipeline-owned trend audit object."""

    if not isinstance(result, Mapping):
        return {"trend": _empty_trend("invalid_result")}

    updated = dict(result)
    if result.get("available") is False:
        updated["trend"] = _empty_trend("indicator_unavailable")
        return updated

    updated["trend"] = calculate_trend(
        result.get("series"),
        result.get("end_year"),
        value_type=value_type,
        methodology_break_years=methodology_break_years,
        observation_interval_years=observation_interval_years,
    )
    return updated
