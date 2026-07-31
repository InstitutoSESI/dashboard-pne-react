import logging
import math
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from src.config import POPULATION_PROJECTION_SOURCE_PATH
from src.data_loader import (
    load_basico_0_5_data,
    load_basico_4_17_data,
    load_basico_6_14_data,
    load_basico_6_17_data,
    load_basico_15_17_data,
    load_pne_data,
    load_pre_escola_data,
)
from src.education_attendance_projection_models import (
    MAX_ABS_ANNUAL_LOG_TREND,
    combine_municipal_state_log_trends,
    forecast_damped_log_value,
    theil_sen_log_slope,
)
from src.pne.goal_indicator_contract import (
    CONTRACT,
    get_formula_for_indicator,
    get_indicator_reference_profile,
)

warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

logger = logging.getLogger(__name__)

TARGET_YEARS = list(range(2026, 2037))
METHODOLOGY_VERSION = "pne2026-municipal-attendance-backtested-hybrid-v3"
MINIMUM_COMPARABLE_OBSERVATIONS = 5
REQUIRED_OBSERVATION_INTERVAL_YEARS = 1
TREND_COMPARISON_YEARS = 5
PERCENT_DISPLAY_CAP = 100.0

PERSISTENCE_NUMERATOR_MODEL = "last_observation_persistence"
STATE_DAMPED_HOLT_NUMERATOR_MODEL = "state_aggregate_damped_holt"
MUNICIPAL_SHRINK_NUMERATOR_MODEL = "municipal_state_shrunk_theil_sen_log"
PERSISTENCE_METHOD = "last_observed_numerator_with_state_age_denominator"
STATE_DAMPED_HOLT_METHOD = (
    "state_aggregate_damped_holt_enrollment_with_state_age_denominator"
)
MUNICIPAL_SHRINK_METHOD = (
    "municipal_state_shrunk_theil_sen_log_enrollment_with_state_age_denominator"
)

MODEL_VALIDATION_VALUE_POLICY = {
    "metric": (
        "100_abs_predicted_minus_observed_numerator_over_"
        "observed_target_population"
    ),
    "valuePolicy": "raw_without_display_cap",
    "displayCapApplied": False,
}

# Parâmetros definidos no conjunto de desenvolvimento (379 municípios) e
# aceitos somente quando o ganho permaneceu positivo no conjunto reservado de
# 118 municípios. A série agregada reduz o ruído municipal sem substituir o
# nível local: cada município parte do seu último numerador observado.
STATE_DAMPED_HOLT_PARAMETERS = {
    "pre_escola": {
        "alpha": 0.2,
        "beta": 0.05,
        "damping": 0.9,
        "transform": "log1p",
    },
    "basico_15_17": {
        "alpha": 0.4,
        "beta": 0.3,
        "damping": 0.9,
        "transform": "identity",
    },
}

MODEL_VALIDATION = {
    "creche": {
        "selectedModel": PERSISTENCE_NUMERATOR_MODEL,
        "heldOutMaePercentagePoints": 8.0221,
        "selectionReason": "trend_candidate_not_robust_out_of_sample",
    },
    "pre_escola": {
        "selectedModel": PERSISTENCE_NUMERATOR_MODEL,
        "previousModel": STATE_DAMPED_HOLT_NUMERATOR_MODEL,
        "heldOutMaePercentagePoints": 13.1760,
        "previousModelMaePercentagePoints": 15.8213,
        "improvementPercentagePoints": 2.6453,
        "improvementBootstrap95": [1.7792, 3.5227],
        "selectionReason": "lower_error_on_held_out_municipalities",
    },
    "basico_6_17": {
        "selectedModel": MUNICIPAL_SHRINK_NUMERATOR_MODEL,
        "selectedCandidate": "municipal_shrink_h2014_w5_d0.80_all_years_k4",
        "heldOutMaePercentagePoints": 4.7686,
        "persistenceMaePercentagePoints": 5.7106,
        "improvementPercentagePoints": 0.9420,
        "improvementBootstrap95": [0.5064, 1.3788],
        "selectionReason": "lower_error_on_held_out_municipalities",
    },
    "basico_15_17": {
        "selectedModel": STATE_DAMPED_HOLT_NUMERATOR_MODEL,
        "heldOutMaePercentagePoints": 11.1405,
        "persistenceMaePercentagePoints": 13.5504,
        "improvementPercentagePoints": 2.4099,
        "improvementBootstrap95": [2.0683, 2.7293],
        "selectionReason": "lower_error_on_held_out_municipalities",
    },
    "infantil_0_5": {
        "selectedModel": PERSISTENCE_NUMERATOR_MODEL,
        "heldOutMaePercentagePoints": 7.1552,
        "selectionReason": "trend_candidate_not_robust_out_of_sample",
    },
    "obrigatoria_4_17": {
        "selectedModel": MUNICIPAL_SHRINK_NUMERATOR_MODEL,
        "selectedCandidate": "municipal_shrink_h2014_w8_d0.80_all_years_k4",
        "heldOutMaePercentagePoints": 4.5609,
        "persistenceMaePercentagePoints": 5.3054,
        "improvementPercentagePoints": 0.7445,
        "improvementBootstrap95": [0.3456, 1.1358],
        "selectionReason": "lower_error_on_held_out_municipalities",
    },
    "escolar_6_14": {
        "selectedModel": PERSISTENCE_NUMERATOR_MODEL,
        "heldOutMaePercentagePoints": 5.5472,
        "selectionReason": "persistence_had_lower_development_error",
    },
}


LOADER_BY_KEY = {
    "pne": load_pne_data,
    "pre_escola": load_pre_escola_data,
    "basico_6_17": load_basico_6_17_data,
    "basico_15_17": load_basico_15_17_data,
}
CANONICAL_PROJECTION_INDICATORS = (
    "creche",
    "pre_escola",
    "basico_6_17",
    "basico_15_17",
)


def _canonical_projection_config(indicator_id):
    formula = get_formula_for_indicator(indicator_id) or {}
    runtime = formula.get("runtime") or {}
    projection = runtime.get("projection") or {}
    reference = get_indicator_reference_profile(indicator_id)
    return {
        "loader": LOADER_BY_KEY[runtime["loaderKey"]],
        "numerator": runtime["numeratorField"],
        "denominator": runtime["denominatorField"],
        "age_group": runtime["populationAgeGroup"],
        "ages": list(runtime["populationAges"]),
        "reference": reference,
        "target_percent": reference["value"] if reference else None,
        "target_year": reference["year"] if reference else None,
        "numerator_model": projection["numeratorModel"],
        "model_parameters": projection.get("parameters"),
        "denominator_model": projection["denominatorModel"],
        "minimum_observations": projection["minimumComparableObservations"],
        "required_interval_years": projection[
            "requiredObservationIntervalYears"
        ],
        "formula_id": formula["formulaId"],
    }


INDICATOR_CONFIGS = {
    **{
        indicator_id: _canonical_projection_config(indicator_id)
        for indicator_id in CANONICAL_PROJECTION_INDICATORS
    },
    "infantil_0_5": {
        "loader": load_basico_0_5_data,
        "numerator": "mat_basico_0_5",
        "denominator": "pop_0_5",
        "age_group": "0-5",
        "ages": list(range(0, 6)),
        "reference": None,
        "target_percent": None,
        "target_year": None,
        "numerator_model": PERSISTENCE_NUMERATOR_MODEL,
        "denominator_model": "municipal_base_times_rs_age_factor",
        "minimum_observations": MINIMUM_COMPARABLE_OBSERVATIONS,
        "required_interval_years": REQUIRED_OBSERVATION_INTERVAL_YEARS,
    },
    "obrigatoria_4_17": {
        "loader": load_basico_4_17_data,
        "numerator": "mat_basico_4_17",
        "denominator": "pop_4_17",
        "age_group": "4-17",
        "ages": list(range(4, 18)),
        "reference": None,
        "target_percent": None,
        "target_year": None,
        "numerator_model": MUNICIPAL_SHRINK_NUMERATOR_MODEL,
        "model_parameters": {
            "candidateId": "municipal_shrink_h2014_w8_d0.80_all_years_k4",
            "historyStartYear": 2014,
            "windowObservations": 8,
            "damping": 0.80,
            "shrinkage": 4.0,
            "excludedYears": [],
            "maximumAbsoluteAnnualLogTrend": MAX_ABS_ANNUAL_LOG_TREND,
        },
        "denominator_model": "municipal_base_times_rs_age_factor",
        "minimum_observations": MINIMUM_COMPARABLE_OBSERVATIONS,
        "required_interval_years": REQUIRED_OBSERVATION_INTERVAL_YEARS,
    },
    "escolar_6_14": {
        "loader": load_basico_6_14_data,
        "numerator": "mat_basico_6_14",
        "denominator": "pop_6_14",
        "age_group": "6-14",
        "ages": list(range(6, 15)),
        "reference": None,
        "target_percent": None,
        "target_year": None,
        "numerator_model": PERSISTENCE_NUMERATOR_MODEL,
        "denominator_model": "municipal_base_times_rs_age_factor",
        "minimum_observations": MINIMUM_COMPARABLE_OBSERVATIONS,
        "required_interval_years": REQUIRED_OBSERVATION_INTERVAL_YEARS,
    },
}


def load_rs_population_projection(path):
    df = pd.read_excel(
        path,
        sheet_name="1) POP_IDADE SIMPLES",
        header=5,
    )
    required_cols = {"IDADE", "SEXO", "SIGLA"}
    if not required_cols.issubset(df.columns):
        raise ValueError(
            f"Planilha deve conter colunas: {required_cols}. "
            f"Encontradas: {list(df.columns[:8])}"
        )

    df = df[df["SIGLA"] == "RS"].copy()
    df = df[df["SEXO"] == "Ambos"].copy()

    year_cols = [col for col in df.columns if isinstance(col, (int, float))]
    df = df[["IDADE"] + year_cols].copy()

    for col in year_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["IDADE"] = pd.to_numeric(df["IDADE"], errors="coerce")
    df = df.dropna(subset=["IDADE"])
    df["IDADE"] = df["IDADE"].astype(int)

    return df


def build_rs_population_by_age_group(df, age_groups):
    result = {}
    for group_key, ages in age_groups.items():
        subset = df[df["IDADE"].isin(ages)]
        year_cols = [col for col in df.columns if col != "IDADE"]
        if subset.empty:
            result[group_key] = pd.Series(dtype=float)
        else:
            result[group_key] = subset[year_cols].sum()
    return result


def get_population_factors_for_base_year(rs_by_group, age_group, base_year, target_years):
    series = rs_by_group.get(age_group)
    if series is None or series.empty:
        return None

    base_val = series.get(base_year)
    if base_val is None or pd.isna(base_val) or float(base_val) <= 0:
        return None

    factors = {}
    for year in target_years:
        val = series.get(year)
        if val is None or pd.isna(val) or float(val) <= 0:
            return None
        factors[int(year)] = float(val) / float(base_val)

    return {
        "base_year_efetivo": int(base_year),
        "factors": factors,
    }


def theil_sen_slope(points):
    if len(points) < 2:
        return 0.0
    x_vals = np.array([p[0] for p in points], dtype=float)
    y_vals = np.array([p[1] for p in points], dtype=float)
    slopes = []
    for i in range(len(points)):
        for j in range(i + 1, len(points)):
            dx = x_vals[j] - x_vals[i]
            if abs(dx) > 1e-9:
                slopes.append((y_vals[j] - y_vals[i]) / dx)
    if not slopes:
        return 0.0
    return float(np.median(slopes))


def _estimate_slope(points):
    if len(points) >= 5:
        return theil_sen_slope(points)
    if len(points) >= 3:
        x_vals = np.array([p[0] for p in points], dtype=float)
        y_vals = np.array([p[1] for p in points], dtype=float)
        coeffs = np.polyfit(x_vals, y_vals, 1)
        return float(coeffs[0])
    return 0.0


def _state_aggregate_damped_holt_projection(
    state_series,
    *,
    base_year,
    target_years,
    parameters,
):
    valid = []
    for row in state_series or []:
        try:
            year = float(row.get("ano"))
            value = float(row.get("valor"))
        except (TypeError, ValueError):
            continue
        if (
            not math.isfinite(year)
            or not year.is_integer()
            or not math.isfinite(value)
            or value < 0
        ):
            continue
        valid.append((int(year), value))
    valid.sort(key=lambda item: item[0])

    years = [year for year, _ in valid]
    if (
        len(valid) < MINIMUM_COMPARABLE_OBSERVATIONS
        or len(years) != len(set(years))
        or years[-1] != base_year
        or any(right - left != 1 for left, right in zip(years, years[1:]))
    ):
        return {
            "available": False,
            "reason": "Série estadual agregada incompatível com o modelo Holt",
        }

    alpha = float(parameters["alpha"])
    beta = float(parameters["beta"])
    damping = float(parameters["damping"])
    transform = str(parameters["transform"])
    if not (
        0 < alpha <= 1
        and 0 <= beta <= 1
        and 0 < damping < 1
        and transform in {"identity", "log1p"}
    ):
        return {"available": False, "reason": "Parâmetros Holt inválidos"}

    raw_values = np.asarray([value for _, value in valid], dtype=float)
    modeled_values = np.log1p(raw_values) if transform == "log1p" else raw_values
    level = float(modeled_values[0])
    initial_index = min(2, len(modeled_values) - 1)
    trend = float(
        (modeled_values[initial_index] - modeled_values[0]) / initial_index
    )
    for observation in modeled_values[1:]:
        previous_level = level
        level = alpha * float(observation) + (1 - alpha) * (
            level + damping * trend
        )
        trend = beta * (level - previous_level) + (1 - beta) * damping * trend

    state_base = float(raw_values[-1])
    if state_base <= 0:
        return {"available": False, "reason": "Numerador estadual agregado não positivo"}

    projected = []
    for target_year in target_years:
        horizon = int(target_year) - int(base_year)
        if horizon <= 0:
            return {"available": False, "reason": "Horizonte Holt inválido"}
        damped_effect = damping * (1 - damping**horizon) / (1 - damping)
        transformed_forecast = float(modeled_values[-1]) + trend * damped_effect
        forecast = (
            math.expm1(transformed_forecast)
            if transform == "log1p"
            else transformed_forecast
        )
        if not math.isfinite(forecast):
            return {"available": False, "reason": "Projeção Holt não finita"}
        projected.append({"ano": int(target_year), "valor": max(0.0, forecast)})

    return {
        "available": True,
        "projected": projected,
        "stateBaseValue": state_base,
        "stateSmoothedLevel": (
            math.expm1(level) if transform == "log1p" else level
        ),
        "stateDampedTrend": trend,
        "parameters": {
            "alpha": alpha,
            "beta": beta,
            "damping": damping,
            "transform": transform,
            "anchoredAtLastObservation": True,
        },
    }


def _municipal_state_shrunk_projection(
    local_points,
    state_series,
    *,
    base_year,
    base_value,
    target_years,
    parameters,
):
    """Project counts from municipal/state robust log trends.

    Missing state trend falls back to persistence, matching the validated
    experiment. If only the municipal trend is unavailable, the state trend is
    used alone. Both fallbacks are explicit and deterministic.
    """

    try:
        history_start = int(parameters["historyStartYear"])
        window = int(parameters["windowObservations"])
        damping = float(parameters["damping"])
        shrinkage = float(parameters["shrinkage"])
        excluded_years = tuple(int(year) for year in parameters["excludedYears"])
        max_abs_slope = float(parameters["maximumAbsoluteAnnualLogTrend"])
        candidate_id = str(parameters["candidateId"])
    except (KeyError, TypeError, ValueError):
        return {
            "available": False,
            "reason": "Parâmetros da tendência municipal e estadual inválidos",
        }
    if (
        history_start > int(base_year)
        or window < MINIMUM_COMPARABLE_OBSERVATIONS
        or not 0 < damping < 1
        or not math.isfinite(shrinkage)
        or shrinkage <= 0
        or not math.isfinite(max_abs_slope)
        or max_abs_slope <= 0
        or not candidate_id
    ):
        return {
            "available": False,
            "reason": "Parâmetros da tendência municipal e estadual inválidos",
        }

    local_training = [
        (year, value)
        for year, value in local_points
        if history_start <= int(year) <= int(base_year)
    ]
    local_slope, local_n = theil_sen_log_slope(
        [year for year, _ in local_training],
        [value for _, value in local_training],
        window=window,
        excluded_years=excluded_years,
        max_abs_slope=max_abs_slope,
    )

    state_training = []
    for row in state_series or []:
        if not isinstance(row, dict):
            continue
        try:
            year = float(row.get("ano"))
            value = float(row.get("valor"))
        except (TypeError, ValueError):
            continue
        if (
            not math.isfinite(year)
            or not year.is_integer()
            or not history_start <= int(year) <= int(base_year)
            or not math.isfinite(value)
            or value < 0
        ):
            continue
        state_training.append((int(year), value))
    state_slope, state_n = theil_sen_log_slope(
        [year for year, _ in state_training],
        [value for _, value in state_training],
        window=window,
        excluded_years=excluded_years,
        max_abs_slope=max_abs_slope,
    )
    combined = combine_municipal_state_log_trends(
        state_slope,
        local_slope,
        local_n,
        shrinkage,
    )

    projected = []
    fallback = combined.fallback
    for target_year in target_years:
        horizon = int(target_year) - int(base_year)
        forecast = (
            forecast_damped_log_value(
                base_value,
                combined.slope,
                damping,
                horizon,
            )
            if combined.slope is not None
            else None
        )
        if forecast is None:
            forecast = float(base_value)
            fallback = fallback or "persistence_non_finite_forecast"
        projected.append({"ano": int(target_year), "valor": forecast})

    return {
        "available": True,
        "projected": projected,
        "parameters": {
            "candidateId": candidate_id,
            "historyStartYear": history_start,
            "windowObservations": window,
            "damping": damping,
            "shrinkage": shrinkage,
            "excludedYears": list(excluded_years),
            "maximumAbsoluteAnnualLogTrend": max_abs_slope,
        },
        "municipalSlope": local_slope,
        "stateSlope": state_slope,
        "selectedSlope": combined.slope,
        "municipalObservationCount": local_n,
        "stateObservationCount": state_n,
        "municipalWeight": combined.municipal_weight,
        "stateWeight": combined.state_weight,
        "fallback": fallback,
    }


def project_numerator(
    series,
    *,
    target_years=None,
    minimum_observations=MINIMUM_COMPARABLE_OBSERVATIONS,
    required_interval_years=REQUIRED_OBSERVATION_INTERVAL_YEARS,
    model=PERSISTENCE_NUMERATOR_MODEL,
    state_series=None,
    model_parameters=None,
):
    """Project a regular annual numerator with a backtested model.

    Local historical slopes remain diagnostics. The selected model is applied
    to the enrollment numerator; the population denominator is handled later.
    """

    projection_years = list(TARGET_YEARS if target_years is None else target_years)
    if any(
        row.get("methodology_break")
        or row.get("methodological_break")
        or row.get("quebra_metodologica")
        for row in series
    ):
        return {
            "available": False,
            "reason": "Quebra metodologica na serie historica",
            "warnings": [],
        }

    valid = []
    for row in series:
        year = row.get("ano")
        value = row.get("valor")
        if value is None or (isinstance(value, float) and math.isnan(value)):
            continue
        try:
            numeric_year = float(year)
            numeric_value = float(value)
        except (TypeError, ValueError):
            continue
        if (
            not math.isfinite(numeric_year)
            or not numeric_year.is_integer()
            or not math.isfinite(numeric_value)
        ):
            continue
        valid.append((int(numeric_year), numeric_value))
    valid.sort(key=lambda x: x[0])

    years = [year for year, _ in valid]
    if len(years) != len(set(years)):
        return {
            "available": False,
            "reason": "Anos duplicados na serie historica",
            "warnings": [],
        }

    n = len(valid)
    warnings_list = []

    if n < minimum_observations:
        return {
            "available": False,
            "reason": (
                "Serie historica insuficiente: minimo de "
                f"{minimum_observations} observacoes comparaveis"
            ),
            "warnings": ["Serie historica insuficiente para cenario de persistencia"],
        }
    if any(value < 0 for _, value in valid):
        return {
            "available": False,
            "reason": "Serie historica contem numerador negativo",
            "warnings": [],
        }

    intervals = {
        right_year - left_year
        for (left_year, _), (right_year, _) in zip(valid, valid[1:])
    }
    if intervals != {required_interval_years}:
        return {
            "available": False,
            "reason": "Frequencia historica incompativel",
            "warnings": [],
        }

    if (
        not projection_years
        or projection_years != sorted(set(projection_years))
        or projection_years[0] != valid[-1][0] + required_interval_years
        or any(
            right - left != required_interval_years
            for left, right in zip(projection_years, projection_years[1:])
        )
    ):
        return {
            "available": False,
            "reason": "Horizonte de projecao nao sucede a serie historica",
            "warnings": [],
        }

    slope_long = _estimate_slope(valid)
    recent = valid[-TREND_COMPARISON_YEARS:]
    slope_recent = _estimate_slope(recent)
    trends_diverge = (
        abs(slope_long) > 1e-9
        and abs(slope_recent) > 1e-9
        and (slope_long > 0) != (slope_recent > 0)
    )
    if trends_diverge and model == PERSISTENCE_NUMERATOR_MODEL:
        warnings_list.append(
            "Tendencias recente e de longo prazo apontam direcoes opostas; "
            "a linha de base de persistencia nao extrapola nenhuma delas."
        )

    last_year, base_val = valid[-1]
    aggregate_model = None
    municipal_state_model = None
    if model == PERSISTENCE_NUMERATOR_MODEL:
        projected = [
            {"ano": int(year), "valor": round(float(base_val), 1)}
            for year in projection_years
        ]
        selected_basis = "last_observation_persistence"
        selected_method = "last_observation_persistence_baseline"
        damping_factor = None
    elif model == STATE_DAMPED_HOLT_NUMERATOR_MODEL:
        aggregate_model = _state_aggregate_damped_holt_projection(
            state_series,
            base_year=last_year,
            target_years=projection_years,
            parameters=model_parameters or {},
        )
        if not aggregate_model.get("available"):
            return {
                "available": False,
                "reason": aggregate_model.get("reason") or "Modelo Holt indisponível",
                "warnings": warnings_list,
            }
        state_base = float(aggregate_model["stateBaseValue"])
        projected = [
            {
                "ano": point["ano"],
                "valor": round(
                    float(base_val) * float(point["valor"]) / state_base,
                    1,
                ),
            }
            for point in aggregate_model["projected"]
        ]
        selected_basis = "state_aggregate_damped_holt"
        selected_method = "state_aggregate_damped_holt_v1"
        damping_factor = float(model_parameters["damping"])
        if trends_diverge:
            warnings_list.append(
                "As tendências municipais recente e longa divergem; o cenário "
                "usa a evolução agregada das matrículas no Rio Grande do Sul."
            )
    elif model == MUNICIPAL_SHRINK_NUMERATOR_MODEL:
        municipal_state_model = _municipal_state_shrunk_projection(
            valid,
            state_series,
            base_year=last_year,
            base_value=base_val,
            target_years=projection_years,
            parameters=model_parameters or {},
        )
        if not municipal_state_model.get("available"):
            return {
                "available": False,
                "reason": (
                    municipal_state_model.get("reason")
                    or "Tendência de matrículas indisponível"
                ),
                "warnings": warnings_list,
            }
        projected = [
            {
                "ano": point["ano"],
                "valor": round(float(point["valor"]), 1),
            }
            for point in municipal_state_model["projected"]
        ]
        selected_basis = MUNICIPAL_SHRINK_NUMERATOR_MODEL
        selected_method = f"{MUNICIPAL_SHRINK_NUMERATOR_MODEL}_v1"
        damping_factor = float(model_parameters["damping"])
        fallback = municipal_state_model.get("fallback")
        if fallback == "persistence_missing_state_trend":
            warnings_list.append(
                "A evolução das matrículas não pôde ser estimada; o cenário "
                "mantém o último valor observado."
            )
        elif fallback == "state_only_missing_municipal_trend":
            warnings_list.append(
                "O histórico municipal não sustenta uma tendência própria; "
                "o cenário usa a evolução agregada das matrículas."
            )
        elif fallback == "persistence_non_finite_forecast":
            warnings_list.append(
                "A trajetória calculada não foi válida; o cenário mantém o "
                "último valor observado."
            )
        if trends_diverge:
            warnings_list.append(
                "As evoluções recente e de longo prazo das matrículas apontam "
                "direções opostas; o cenário combina o histórico municipal e "
                "o estadual."
            )
    else:
        return {
            "available": False,
            "reason": f"Modelo de numerador não suportado: {model}",
            "warnings": warnings_list,
        }

    first_projected_change = (
        float(projected[0]["valor"]) - float(base_val) if projected else 0.0
    )
    quality = "media" if n >= 8 else "baixa"
    if quality == "baixa":
        warnings_list.append(
            "A serie atende ao minimo, mas tem menos de 8 observacoes anuais."
        )

    return {
        "available": True,
        "projected": projected,
        "historical": [{"ano": y, "valor": v} for y, v in valid],
        "quality": quality,
        "warnings": warnings_list,
        "slope": round(first_projected_change, 6),
        "trend": {
            "method": selected_method,
            "historicalDiagnosticMethod": "theil_sen",
            "longTermAnnualChange": round(slope_long, 6),
            "recentAnnualChange": round(slope_recent, 6),
            "selectedAnnualChangeBeforeDamping": round(first_projected_change, 6),
            "selectedAnnualChange": round(first_projected_change, 6),
            "selectedBasis": selected_basis,
            "dampingFactor": damping_factor,
            "diverges": trends_diverge,
            "observationCount": n,
            "recentWindowObservationCount": len(recent),
            "baseYear": last_year,
            "baseValue": round(float(base_val), 6),
            **(
                {
                    "aggregateModel": {
                        "territory": "Rio Grande do Sul",
                        **aggregate_model["parameters"],
                        "stateBaseValue": round(
                            float(aggregate_model["stateBaseValue"]), 6
                        ),
                    }
                }
                if aggregate_model is not None
                else {}
            ),
            **(
                {
                    "municipalStateModel": {
                        **municipal_state_model["parameters"],
                        "municipalAnnualLogTrend": municipal_state_model[
                            "municipalSlope"
                        ],
                        "stateAnnualLogTrend": municipal_state_model[
                            "stateSlope"
                        ],
                        "selectedAnnualLogTrend": municipal_state_model[
                            "selectedSlope"
                        ],
                        "municipalObservationCount": municipal_state_model[
                            "municipalObservationCount"
                        ],
                        "stateObservationCount": municipal_state_model[
                            "stateObservationCount"
                        ],
                        "municipalWeight": municipal_state_model[
                            "municipalWeight"
                        ],
                        "stateWeight": municipal_state_model["stateWeight"],
                        "fallback": municipal_state_model.get("fallback"),
                        "territory": "Rio Grande do Sul",
                    }
                }
                if municipal_state_model is not None
                else {}
            ),
        },
    }


def _aggregate_state_numerator_series(dataframe, numerator_column):
    """Aggregate one numerator per municipality/year before the state total."""

    required = {"municipio", "ano", numerator_column}
    if dataframe is None or not required.issubset(dataframe.columns):
        return []

    state_frame = dataframe[["municipio", "ano", numerator_column]].copy()
    state_frame["ano"] = pd.to_numeric(state_frame["ano"], errors="coerce")
    state_frame[numerator_column] = pd.to_numeric(
        state_frame[numerator_column], errors="coerce"
    )
    state_frame = state_frame.dropna(
        subset=["municipio", "ano", numerator_column]
    )
    state_by_municipality = state_frame.groupby(
        ["municipio", "ano"], as_index=False
    )[numerator_column].sum()
    state_yearly = (
        state_by_municipality.groupby("ano", as_index=False)[numerator_column]
        .sum()
        .sort_values("ano")
    )
    return [
        {"ano": row["ano"], "valor": row[numerator_column]}
        for row in state_yearly.to_dict("records")
    ]


def build_indicator_projection(
    municipio,
    config,
    rs_by_group,
    dataframe=None,
    state_series=None,
):
    indicator_key = config["key"]
    cfg = INDICATOR_CONFIGS[indicator_key]
    numerator_model = cfg.get("numerator_model")
    if (
        numerator_model
        not in {
            PERSISTENCE_NUMERATOR_MODEL,
            STATE_DAMPED_HOLT_NUMERATOR_MODEL,
            MUNICIPAL_SHRINK_NUMERATOR_MODEL,
        }
        or cfg.get("denominator_model") != "municipal_base_times_rs_age_factor"
    ):
        return {
            "available": False,
            "reason": "Configuracao de cenario nao suportada",
            "warnings": [],
        }

    loader = cfg["loader"]
    df = dataframe if dataframe is not None else loader()
    if df.empty or "municipio" not in df.columns:
        return {"available": False, "reason": "Dados do carregador vazios", "warnings": []}

    dff = df[df["municipio"] == municipio].copy()
    if dff.empty:
        return {"available": False, "reason": "Municipio sem dados", "warnings": []}

    num_col = cfg["numerator"]
    den_col = cfg["denominator"]
    if num_col not in dff.columns or den_col not in dff.columns:
        return {"available": False, "reason": "Colunas necessarias ausentes", "warnings": []}

    dff["ano"] = pd.to_numeric(dff["ano"], errors="coerce")
    dff[num_col] = pd.to_numeric(dff[num_col], errors="coerce")
    dff[den_col] = pd.to_numeric(dff[den_col], errors="coerce")
    dff = dff.dropna(subset=["ano", num_col, den_col])
    if dff.empty:
        return {"available": False, "reason": "Sem dados numericos validos", "warnings": []}

    yearly = dff.groupby("ano", as_index=False).agg(
        {num_col: "sum", den_col: "max"}
    ).sort_values("ano")

    series = yearly.to_dict("records")

    if (
        numerator_model
        in {
            STATE_DAMPED_HOLT_NUMERATOR_MODEL,
            MUNICIPAL_SHRINK_NUMERATOR_MODEL,
        }
        and state_series is None
    ):
        state_series = _aggregate_state_numerator_series(df, num_col)

    num_result = project_numerator(
        [{"ano": r["ano"], "valor": r[num_col]} for r in series],
        minimum_observations=cfg.get(
            "minimum_observations", MINIMUM_COMPARABLE_OBSERVATIONS
        ),
        required_interval_years=cfg.get(
            "required_interval_years", REQUIRED_OBSERVATION_INTERVAL_YEARS
        ),
        model=numerator_model,
        state_series=state_series,
        model_parameters=(
            cfg.get("model_parameters")
            if numerator_model == MUNICIPAL_SHRINK_NUMERATOR_MODEL
            else STATE_DAMPED_HOLT_PARAMETERS.get(indicator_key)
        ),
    )
    if not num_result["available"]:
        return {"available": False, "reason": num_result["reason"], "warnings": []}

    municipio_pop_series = yearly[[den_col, "ano"]].copy()

    last_pop_row = municipio_pop_series.iloc[-1]
    pop_base_year = int(last_pop_row["ano"])
    pop_base_value = float(last_pop_row[den_col])

    age_group = cfg["age_group"]

    pop_factor_info = get_population_factors_for_base_year(
        rs_by_group, age_group, pop_base_year, TARGET_YEARS
    )

    all_warnings = list(num_result.get("warnings", []))
    quality = num_result.get("quality", "media")

    if pop_factor_info is None:
        all_warnings.append(
            f"Fator populacional do RS indisponivel para faixa {age_group} "
            f"com ano-base {pop_base_year}"
        )
        return {
            "available": False,
            "reason": "Fator populacional do RS indisponivel para o ano-base efetivo",
            "warnings": all_warnings,
        }

    factors = pop_factor_info["factors"]
    rs_base_year = pop_factor_info["base_year_efetivo"]

    historical_pop_values = []
    for r in series:
        historical_pop_values.append(float(r[den_col]))

    historical_num_years = []
    historical_num_values = []
    historical_percent_raw = []
    for r in series:
        pct = (
            float(r[num_col]) / float(r[den_col]) * 100
            if float(r[den_col]) > 0
            else None
        )
        historical_num_years.append(int(r["ano"]))
        historical_num_values.append(float(r[num_col]))
        historical_percent_raw.append(round(pct, 2) if pct is not None else None)

    projected_pop = []
    projected_num = []
    projected_pct_raw = []

    for proj in num_result["projected"]:
        year = proj["ano"]
        pop_factor = factors.get(year)
        if pop_factor is None:
            return {
                "available": False,
                "reason": f"Fator populacional indisponivel para {year}",
                "warnings": all_warnings,
            }
        proj_pop = pop_base_value * pop_factor

        proj_num = proj["valor"]
        pct_val = (proj_num / proj_pop * 100) if proj_pop > 0 else None

        projected_pop.append(round(proj_pop, 1))
        projected_num.append(round(proj_num, 1))
        projected_pct_raw.append(round(pct_val, 2) if pct_val is not None else None)

    projected_pct_final = [
        min(PERCENT_DISPLAY_CAP, value) if value is not None else None
        for value in projected_pct_raw
    ]
    if any(
        value is not None and value > PERCENT_DISPLAY_CAP
        for value in projected_pct_raw
    ):
        all_warnings.append(
            "A razão bruta superou 100%; a apresentação pública foi limitada "
            "a 100%, e o valor bruto foi preservado para auditoria."
        )

    projected_2036_raw = projected_pct_raw[-1] if len(projected_pct_raw) >= 11 else None
    projected_2036_final = projected_pct_final[-1] if len(projected_pct_final) >= 11 else None
    target = cfg["target_percent"]
    target_year = cfg.get("target_year")
    target_index = (
        TARGET_YEARS.index(target_year)
        if target_year in TARGET_YEARS
        else None
    )
    projected_at_target_raw = (
        projected_pct_raw[target_index]
        if target_index is not None
        else None
    )
    projected_at_target = (
        projected_pct_final[target_index]
        if target_index is not None
        else None
    )

    if projected_at_target is not None and target is not None:
        distance_to_target = round(projected_at_target - target, 2)
        status_at_target = (
            "tende_a_atingir"
            if projected_at_target >= target
            else "risco_de_nao_atingir"
        )
    else:
        distance_to_target = None
        status_at_target = None

    projection_source = CONTRACT["sources"]["ibge_population_projection_2024"]
    projection_lineage = projection_source.get("lineage") or {}
    validation = MODEL_VALIDATION[indicator_key]
    uses_state_holt = numerator_model == STATE_DAMPED_HOLT_NUMERATOR_MODEL
    uses_municipal_state_trend = (
        numerator_model == MUNICIPAL_SHRINK_NUMERATOR_MODEL
    )
    uncertainty = {
        "status": "backtested_no_probability_interval",
        "interval": None,
        "reason": (
            "A comparação retrospectiva cobre períodos de um a cinco anos, "
            "mas não há intervalo probabilístico para todo o cenário até 2036."
        ),
        "interpretation": (
            (
                "O cenário combina o histórico de matrículas do município e "
                "do Rio Grande do Sul com a evolução projetada da população."
            )
            if uses_municipal_state_trend
            else (
                (
                    "O cenário parte do número mais recente de matrículas do "
                    "município, acompanha a evolução das matrículas no Rio "
                    "Grande do Sul e considera a evolução projetada da população."
                )
                if uses_state_holt
                else (
                    "O cenário mantém o número mais recente de matrículas e "
                    "considera a evolução projetada da população."
                )
            )
        ),
        "backtest": {
            "method": "rolling_origin_with_held_out_municipalities",
            **MODEL_VALIDATION_VALUE_POLICY,
            "unit": "percentage_points",
            "validatedHorizonsYears": [1, 2, 3, 4, 5],
            "developmentMunicipalities": 379,
            "heldOutMunicipalities": 118,
            "heldOutPeriod": [2023, 2025],
            **validation,
        },
    }
    denominator_model = {
        "method": "municipal_base_scaled_by_rs_age_group_change",
        "methodCode": "municipal_base_times_rs_age_factor",
        "formula": (
            "população municipal no ano-base × "
            "(população projetada do RS na faixa e ano / "
            "população projetada do RS na faixa e ano-base)"
        ),
        "historicalPopulationSourceId": "municipal_age_population_panel",
        "projectionSourceId": "ibge_population_projection_2024",
        "projectionRevision": "2024",
        "projectionSourceSha256": projection_lineage.get("sourceSha256"),
        "populationAgeGroup": age_group,
        "municipalBaseYear": pop_base_year,
        "stateProjectionBaseYear": rs_base_year,
        "territorialBasis": "população residente municipal",
    }

    if uses_municipal_state_trend:
        method = MUNICIPAL_SHRINK_METHOD
        method_label = (
            "Cenário baseado no histórico de matrículas do município e do "
            "Rio Grande do Sul, combinado à evolução projetada da população."
        )
    elif uses_state_holt:
        method = STATE_DAMPED_HOLT_METHOD
        method_label = (
            "Cenário baseado na evolução das matrículas no Rio Grande do Sul "
            "e na evolução projetada da população do município."
        )
    else:
        method = PERSISTENCE_METHOD
        method_label = (
            "Cenário baseado no número mais recente de matrículas e na "
            "evolução projetada da população."
        )

    return {
        "available": True,
        "base_year": pop_base_year,
        "horizon_year": TARGET_YEARS[-1],
        "target_year": target_year,
        "methodology_version": METHODOLOGY_VERSION,
        "method": method,
        "method_label": method_label,
        "formula_id": cfg.get("formula_id"),
        "reference": cfg.get("reference"),
        "population_age_group": age_group,
        "historical_years": historical_num_years,
        "historical_numerator": historical_num_values,
        "historical_population": historical_pop_values,
        "historical_percent_raw": historical_percent_raw,
        "historical_percent": [
            min(PERCENT_DISPLAY_CAP, value) if value is not None else None
            for value in historical_percent_raw
        ],
        "years": TARGET_YEARS,
        "projected_population": projected_pop,
        "projected_numerator": projected_num,
        "projected_percent_raw": projected_pct_raw,
        "projected_percent": projected_pct_final,
        "target_percent": target,
        "projected_2036": projected_2036_final,
        "projected_2036_raw": projected_2036_raw,
        "projected_at_target": projected_at_target,
        "projected_at_target_raw": projected_at_target_raw,
        "distance_to_target": distance_to_target,
        "status_at_target": status_at_target,
        "distance_to_target_2036": (
            distance_to_target if target_year == 2036 else None
        ),
        "status_2036": status_at_target if target_year == 2036 else None,
        "trend": num_result.get("trend"),
        "denominator_model": denominator_model,
        "uncertainty": uncertainty,
        "quality": quality,
        "warnings": all_warnings,
    }


def build_all_projections(
    municipios,
    population_projection_path: str | Path | None = None,
    dataframes: dict[str, pd.DataFrame] | None = None,
):
    rs_path = Path(
        population_projection_path or POPULATION_PROJECTION_SOURCE_PATH
    ).resolve()
    if not rs_path.is_file():
        raise FileNotFoundError(
            "Arquivo de projeção populacional do IBGE não encontrado. "
            "Configure POPULATION_PROJECTION_SOURCE_PATH com o caminho do "
            "snapshot projecao_pop.xlsx documentado no contrato."
        )

    rs_df = load_rs_population_projection(str(rs_path))

    age_groups = {cfg["age_group"]: cfg["ages"] for cfg in INDICATOR_CONFIGS.values()}
    rs_by_group = build_rs_population_by_age_group(rs_df, age_groups)

    frames = dict(dataframes or {})
    load_errors = {}
    for indicator_key, cfg in INDICATOR_CONFIGS.items():
        if indicator_key in frames:
            continue
        try:
            frames[indicator_key] = cfg["loader"]()
        except Exception as exc:
            logger.error("Erro ao carregar %s: %s", indicator_key, exc)
            load_errors[indicator_key] = str(exc)

    state_series_by_indicator = {
        indicator_key: _aggregate_state_numerator_series(
            frames[indicator_key], cfg["numerator"]
        )
        for indicator_key, cfg in INDICATOR_CONFIGS.items()
        if (
            indicator_key not in load_errors
            and cfg.get("numerator_model")
            in {
                STATE_DAMPED_HOLT_NUMERATOR_MODEL,
                MUNICIPAL_SHRINK_NUMERATOR_MODEL,
            }
        )
    }

    results = {}
    for municipio in municipios:
        municipio_projections = {}
        for indicator_key in INDICATOR_CONFIGS:
            if indicator_key in load_errors:
                municipio_projections[indicator_key] = {
                    "available": False,
                    "reason": f"Erro no carregamento: {load_errors[indicator_key]}",
                    "warnings": [],
                }
                continue
            config = {"key": indicator_key}
            try:
                proj = build_indicator_projection(
                    municipio,
                    config,
                    rs_by_group,
                    dataframe=frames[indicator_key],
                    state_series=state_series_by_indicator.get(indicator_key),
                )
                municipio_projections[indicator_key] = proj
            except Exception as exc:
                logger.error("Erro ao projetar %s para %s: %s", indicator_key, municipio, exc)
                municipio_projections[indicator_key] = {
                    "available": False,
                    "reason": f"Erro no calculo: {exc}",
                    "warnings": [],
                }
        results[municipio] = municipio_projections
    return results
