"""Shadow experiment for municipal education-attendance projections.

The module deliberately does not change the production projection contract. It
uses the compact Censo Escolar panel to compare transparent numerator models,
while keeping the population denominator used by the platform. All percentages
remain uncapped internally; the public 100% display cap is outside this study.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from sqlalchemy import text

from src.education_attendance_projection_models import (
    combine_municipal_state_log_trends,
    forecast_damped_log_value,
    theil_sen_log_slope,
)
from src.pne_2026_projections import (
    STATE_DAMPED_HOLT_PARAMETERS,
    _state_aggregate_damped_holt_projection,
    build_rs_population_by_age_group,
    load_rs_population_projection,
)


EXPERIMENT_VERSION = "education-attendance-shadow-v1.0.0"
DEFAULT_SEED = 20260731
DEFAULT_HOLDOUT_MUNICIPALITIES = 118
PRIMARY_HORIZONS = (1, 2, 3, 4, 5)
SUPPORTING_HORIZONS = (8, 11)
DEVELOPMENT_TARGET_YEARS = (2019, 2020, 2021, 2022)
VALIDATION_TARGET_YEARS = (2023, 2024, 2025)
MINIMUM_COMMON_DEVELOPMENT_ORIGIN_YEAR = 2018
SPLIT_STRATIFICATION_YEAR = 2018
TERRITORIAL_BREAK_CODES = {"4302105", "4314548"}
TERRITORIAL_BREAK_YEAR = 2013
PANDEMIC_YEARS = {2020, 2021, 2022}


INDICATORS = {
    "creche": {
        "population": "pop_0_3",
        "ages": list(range(0, 4)),
        "population_group": "0-3",
        "current_model": "persistence",
    },
    "pre_escola": {
        "population": "pop_4_5",
        "ages": list(range(4, 6)),
        "population_group": "4-5",
        "current_model": "state_damped_holt",
    },
    "basico_6_17": {
        "population": "pop_6_17",
        "ages": list(range(6, 18)),
        "population_group": "6-17",
        "current_model": "persistence",
    },
    "basico_15_17": {
        "population": "pop_15_17",
        "ages": list(range(15, 18)),
        "population_group": "15-17",
        "current_model": "state_damped_holt",
    },
    "infantil_0_5": {
        "population": "pop_0_5",
        "ages": list(range(0, 6)),
        "population_group": "0-5",
        "current_model": "persistence",
    },
    "obrigatoria_4_17": {
        "population": "pop_4_17",
        "ages": list(range(4, 18)),
        "population_group": "4-17",
        "current_model": "persistence",
    },
    "escolar_6_14": {
        "population": "pop_6_14",
        "ages": list(range(6, 15)),
        "population_group": "6-14",
        "current_model": "persistence",
    },
}


POPULATION_PANEL_QUERY = """
SELECT
    ano,
    id_municipio::text AS codigo_municipio,
    SUM(CASE WHEN idade BETWEEN 0 AND 3 THEN pop_estimada ELSE 0 END) AS pop_0_3,
    SUM(CASE WHEN idade BETWEEN 4 AND 5 THEN pop_estimada ELSE 0 END) AS pop_4_5,
    SUM(CASE WHEN idade BETWEEN 6 AND 17 THEN pop_estimada ELSE 0 END) AS pop_6_17,
    SUM(CASE WHEN idade BETWEEN 15 AND 17 THEN pop_estimada ELSE 0 END) AS pop_15_17,
    SUM(CASE WHEN idade BETWEEN 0 AND 5 THEN pop_estimada ELSE 0 END) AS pop_0_5,
    SUM(CASE WHEN idade BETWEEN 4 AND 17 THEN pop_estimada ELSE 0 END) AS pop_4_17,
    SUM(CASE WHEN idade BETWEEN 6 AND 14 THEN pop_estimada ELSE 0 END) AS pop_6_14
FROM populacao_idade_rs
WHERE ano BETWEEN :start_year AND :end_year
GROUP BY ano, id_municipio
ORDER BY ano, codigo_municipio
""".strip()


@dataclass(frozen=True)
class Candidate:
    candidate_id: str
    family: str
    complexity: int
    history_start: int | None = None
    window: int | None = None
    damping: float | None = None
    shrinkage: float | None = None
    exclude_pandemic: bool = False


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _normalize_code(series: pd.Series) -> pd.Series:
    values = series.astype("string").str.replace(r"\.0$", "", regex=True).str.zfill(7)
    if values.isna().any() or (~values.str.fullmatch(r"\d{7}")).any():
        raise ValueError("Código municipal inválido no painel experimental.")
    return values


def load_enrollment_panel(path: Path) -> pd.DataFrame:
    raw = pd.read_csv(path, compression="gzip", dtype={"codigo_municipio": "string"})
    required = {
        "ano",
        "codigo_municipio",
        "mat_infantil_pre",
        "mat_basico_0_3",
        "mat_basico_4_5",
        "mat_basico_6_10",
        "mat_basico_11_14",
        "mat_basico_15_17",
    }
    missing = sorted(required - set(raw.columns))
    if missing:
        raise ValueError(f"Painel de matrículas sem colunas obrigatórias: {missing}")
    result = raw[["ano", "codigo_municipio"]].copy()
    result["ano"] = pd.to_numeric(raw["ano"], errors="raise").astype("int64")
    result["codigo_municipio"] = _normalize_code(raw["codigo_municipio"])
    numeric = raw[list(required - {"ano", "codigo_municipio"})].apply(
        pd.to_numeric, errors="coerce"
    )
    if numeric.isna().any().any() or (numeric < 0).any().any():
        raise ValueError("Painel de matrículas contém valor ausente ou negativo.")
    result["creche"] = numeric["mat_basico_0_3"]
    result["pre_escola"] = numeric["mat_infantil_pre"]
    result["basico_6_17"] = numeric[
        ["mat_basico_6_10", "mat_basico_11_14", "mat_basico_15_17"]
    ].sum(axis=1)
    result["basico_15_17"] = numeric["mat_basico_15_17"]
    result["infantil_0_5"] = numeric[["mat_basico_0_3", "mat_basico_4_5"]].sum(
        axis=1
    )
    result["obrigatoria_4_17"] = numeric[
        [
            "mat_basico_4_5",
            "mat_basico_6_10",
            "mat_basico_11_14",
            "mat_basico_15_17",
        ]
    ].sum(axis=1)
    result["escolar_6_14"] = numeric[
        ["mat_basico_6_10", "mat_basico_11_14"]
    ].sum(axis=1)
    if result.duplicated(["ano", "codigo_municipio"]).any():
        raise ValueError("Painel de matrículas contém chaves ano/município duplicadas.")
    return result.sort_values(["codigo_municipio", "ano"]).reset_index(drop=True)


def load_population_panel(engine, *, start_year: int = 2014, end_year: int = 2025) -> pd.DataFrame:
    frame = pd.read_sql_query(
        text(POPULATION_PANEL_QUERY),
        engine,
        params={"start_year": int(start_year), "end_year": int(end_year)},
    )
    frame["ano"] = pd.to_numeric(frame["ano"], errors="raise").astype("int64")
    frame["codigo_municipio"] = _normalize_code(frame["codigo_municipio"])
    population_columns = [cfg["population"] for cfg in INDICATORS.values()]
    for column in population_columns:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    if frame[population_columns].isna().any().any():
        raise ValueError("Painel populacional contém valores ausentes.")
    if (frame[population_columns] <= 0).any().any():
        raise ValueError("Painel populacional contém denominador não positivo.")
    expected_rows = (end_year - start_year + 1) * 497
    if len(frame) != expected_rows or frame.duplicated(["ano", "codigo_municipio"]).any():
        raise ValueError(
            f"Painel populacional fora do contrato: {len(frame)} linhas; esperado {expected_rows}."
        )
    return frame.sort_values(["codigo_municipio", "ano"]).reset_index(drop=True)


def load_rs_age_series(path: Path) -> dict[str, pd.Series]:
    source = load_rs_population_projection(str(path))
    groups = {
        cfg["population_group"]: cfg["ages"] for cfg in INDICATORS.values()
    }
    series = build_rs_population_by_age_group(source, groups)
    required_years = set(range(2014, 2037))
    for group, values in series.items():
        available = {int(year) for year in values.index if pd.notna(values.loc[year])}
        if not required_years.issubset(available):
            raise ValueError(f"Projeção estadual incompleta para a faixa {group}.")
    return series


def deterministic_split(
    enrollment: pd.DataFrame,
    *,
    seed: int = DEFAULT_SEED,
    holdout_count: int = DEFAULT_HOLDOUT_MUNICIPALITIES,
    stratification_year: int = SPLIT_STRATIFICATION_YEAR,
) -> pd.DataFrame:
    latest = enrollment.loc[
        enrollment["ano"].eq(int(stratification_year)),
        ["codigo_municipio", "obrigatoria_4_17"],
    ].copy()
    if len(latest) != 497:
        raise ValueError(
            f"Ano de estratificação {stratification_year} não possui 497 municípios."
        )
    if latest["codigo_municipio"].nunique() != len(latest):
        raise ValueError("Não foi possível construir o split municipal sem duplicidades.")
    ranked = latest["obrigatoria_4_17"].rank(method="first")
    latest["size_stratum"] = pd.qcut(ranked, 4, labels=False).astype(int) + 1
    counts = latest.groupby("size_stratum").size().sort_index()
    exact = counts * (holdout_count / len(latest))
    allocation = np.floor(exact).astype(int)
    remainder = holdout_count - int(allocation.sum())
    for stratum in (exact - allocation).sort_values(ascending=False).index[:remainder]:
        allocation.loc[stratum] += 1
    latest["split_hash"] = latest["codigo_municipio"].map(
        lambda code: hashlib.sha256(f"{seed}:{code}".encode("utf-8")).hexdigest()
    )
    latest["role"] = "development"
    for stratum, count in allocation.items():
        selected = (
            latest.loc[latest["size_stratum"].eq(stratum)]
            .sort_values(["split_hash", "codigo_municipio"])
            .head(int(count))
            .index
        )
        latest.loc[selected, "role"] = "heldout"
    if int(latest["role"].eq("heldout").sum()) != holdout_count:
        raise AssertionError("O split determinístico não produziu 118 municípios reservados.")
    return latest[["codigo_municipio", "role", "size_stratum"]].sort_values(
        "codigo_municipio"
    ).reset_index(drop=True)


def candidate_grid() -> list[Candidate]:
    candidates = [
        Candidate("persistence", "persistence", 0),
        Candidate("production_current", "production_current", 1),
    ]
    for history_start in (2007, 2014):
        for window in (5, 8, None):
            window_label = "all" if window is None else str(window)
            for damping in (0.8, 0.9, 0.95):
                for exclude_pandemic in (False, True):
                    pandemic_label = "exclude2020_2022" if exclude_pandemic else "all_years"
                    prefix = (
                        f"h{history_start}_w{window_label}_d{damping:.2f}_{pandemic_label}"
                    )
                    candidates.append(
                        Candidate(
                            f"state_robust_{prefix}",
                            "state_robust",
                            2,
                            history_start,
                            window,
                            damping,
                            None,
                            exclude_pandemic,
                        )
                    )
                    for shrinkage in (4.0, 12.0, 30.0):
                        candidates.append(
                            Candidate(
                                f"municipal_shrink_{prefix}_k{int(shrinkage)}",
                                "municipal_shrink",
                                3,
                                history_start,
                                window,
                                damping,
                                shrinkage,
                                exclude_pandemic,
                            )
                        )
    return candidates


def _theil_sen_log_slope(
    years: np.ndarray,
    values: np.ndarray,
    *,
    window: int | None,
    exclude_pandemic: bool,
) -> tuple[float | None, int]:
    return theil_sen_log_slope(
        years,
        values,
        window=window,
        excluded_years=(PANDEMIC_YEARS if exclude_pandemic else ()),
    )


def build_backtest_points(
    enrollment: pd.DataFrame,
    population: pd.DataFrame,
    split: pd.DataFrame,
    rs_age_series: dict[str, pd.Series],
    indicator: str,
    *,
    horizons: Iterable[int] = PRIMARY_HORIZONS,
    target_years: Iterable[int] = VALIDATION_TARGET_YEARS,
) -> pd.DataFrame:
    cfg = INDICATORS[indicator]
    numerator = enrollment.pivot(
        index="codigo_municipio", columns="ano", values=indicator
    )
    denominator = population.pivot(
        index="codigo_municipio", columns="ano", values=cfg["population"]
    )
    rows: list[dict] = []
    state_population = rs_age_series[cfg["population_group"]]
    for target_year in target_years:
        for horizon in horizons:
            origin_year = int(target_year) - int(horizon)
            common_codes = numerator.index.intersection(denominator.index)
            for code in common_codes:
                if origin_year not in numerator.columns or target_year not in numerator.columns:
                    continue
                origin_num = numerator.at[code, origin_year]
                actual_num = numerator.at[code, target_year]
                origin_pop = (
                    denominator.at[code, origin_year]
                    if origin_year in denominator.columns
                    else np.nan
                )
                actual_pop = (
                    denominator.at[code, target_year]
                    if target_year in denominator.columns
                    else np.nan
                )
                if pd.isna(origin_num) or pd.isna(actual_num):
                    continue
                predicted_pop = np.nan
                if (
                    pd.notna(origin_pop)
                    and float(origin_pop) > 0
                    and origin_year in state_population.index
                    and target_year in state_population.index
                ):
                    predicted_pop = float(origin_pop) * float(
                        state_population.loc[target_year]
                    ) / float(state_population.loc[origin_year])
                actual_coverage = (
                    float(actual_num) / float(actual_pop) * 100
                    if pd.notna(actual_pop) and float(actual_pop) > 0
                    else np.nan
                )
                rows.append(
                    {
                        "codigo_municipio": str(code),
                        "origin_year": origin_year,
                        "target_year": int(target_year),
                        "horizon": int(horizon),
                        "origin_numerator": float(origin_num),
                        "actual_numerator": float(actual_num),
                        "predicted_population": predicted_pop,
                        "actual_population": float(actual_pop)
                        if pd.notna(actual_pop)
                        else np.nan,
                        "actual_coverage_raw": actual_coverage,
                    }
                )
    points = pd.DataFrame(rows)
    return points.merge(split, on="codigo_municipio", how="inner", validate="many_to_one")


class ForecastEngine:
    def __init__(self, enrollment: pd.DataFrame, indicator: str):
        self.indicator = indicator
        self.series = {
            str(code): group.sort_values("ano")[["ano", indicator]].reset_index(drop=True)
            for code, group in enrollment.groupby("codigo_municipio")
        }
        self.state = (
            enrollment.groupby("ano", as_index=False)[indicator]
            .sum()
            .sort_values("ano")
            .reset_index(drop=True)
        )
        self._state_slope_cache: dict[tuple, tuple[float | None, int]] = {}
        self._local_slope_cache: dict[tuple, tuple[float | None, int]] = {}
        self._current_ratio_cache: dict[tuple[int, int], float] = {}

    def _training_frame(
        self, code: str | None, origin_year: int, history_start: int
    ) -> pd.DataFrame:
        frame = self.state if code is None else self.series[code]
        value_col = self.indicator
        effective_start = int(history_start)
        if code in TERRITORIAL_BREAK_CODES:
            effective_start = max(effective_start, TERRITORIAL_BREAK_YEAR)
        return frame.loc[
            frame["ano"].between(effective_start, int(origin_year)), ["ano", value_col]
        ]

    def state_slope(self, candidate: Candidate, origin_year: int) -> tuple[float | None, int]:
        key = (
            origin_year,
            candidate.history_start,
            candidate.window,
            candidate.exclude_pandemic,
        )
        if key not in self._state_slope_cache:
            frame = self._training_frame(None, origin_year, int(candidate.history_start))
            self._state_slope_cache[key] = _theil_sen_log_slope(
                frame["ano"].to_numpy(dtype=float),
                frame[self.indicator].to_numpy(dtype=float),
                window=candidate.window,
                exclude_pandemic=candidate.exclude_pandemic,
            )
        return self._state_slope_cache[key]

    def local_slope(
        self, candidate: Candidate, code: str, origin_year: int
    ) -> tuple[float | None, int]:
        key = (
            code,
            origin_year,
            candidate.history_start,
            candidate.window,
            candidate.exclude_pandemic,
        )
        if key not in self._local_slope_cache:
            frame = self._training_frame(code, origin_year, int(candidate.history_start))
            self._local_slope_cache[key] = _theil_sen_log_slope(
                frame["ano"].to_numpy(dtype=float),
                frame[self.indicator].to_numpy(dtype=float),
                window=candidate.window,
                exclude_pandemic=candidate.exclude_pandemic,
            )
        return self._local_slope_cache[key]

    def current_state_ratio(self, origin_year: int, target_year: int) -> float:
        key = (int(origin_year), int(target_year))
        if key in self._current_ratio_cache:
            return self._current_ratio_cache[key]
        if self.indicator not in STATE_DAMPED_HOLT_PARAMETERS:
            self._current_ratio_cache[key] = 1.0
            return 1.0
        frame = self.state.loc[self.state["ano"].between(2014, origin_year)]
        state_series = [
            {"ano": int(row.ano), "valor": float(getattr(row, self.indicator))}
            for row in frame.itertuples(index=False)
        ]
        result = _state_aggregate_damped_holt_projection(
            state_series,
            base_year=int(origin_year),
            target_years=[int(target_year)],
            parameters=STATE_DAMPED_HOLT_PARAMETERS[self.indicator],
        )
        if not result.get("available"):
            raise ValueError(
                f"Modelo atual indisponível para {self.indicator}/{origin_year}/{target_year}: "
                f"{result.get('reason')}"
            )
        base = float(result["stateBaseValue"])
        ratio = float(result["projected"][0]["valor"]) / base if base > 0 else 1.0
        self._current_ratio_cache[key] = ratio
        return ratio

    def predict(self, candidate: Candidate, points: pd.DataFrame) -> np.ndarray:
        origin_values = points["origin_numerator"].to_numpy(dtype=float)
        if candidate.family == "persistence":
            return origin_values.copy()
        predictions = np.empty(len(points), dtype=float)
        if candidate.family == "production_current":
            for index, row in enumerate(points.itertuples(index=False)):
                predictions[index] = max(
                    0.0,
                    float(row.origin_numerator)
                    * self.current_state_ratio(row.origin_year, row.target_year),
                )
            return predictions
        for index, row in enumerate(points.itertuples(index=False)):
            state_slope, _ = self.state_slope(candidate, row.origin_year)
            if state_slope is None:
                predictions[index] = float(row.origin_numerator)
                continue
            slope = state_slope
            if candidate.family == "municipal_shrink":
                local_slope, local_n = self.local_slope(
                    candidate, row.codigo_municipio, row.origin_year
                )
                slope = combine_municipal_state_log_trends(
                    state_slope,
                    local_slope,
                    local_n,
                    float(candidate.shrinkage),
                ).slope
            forecast = (
                forecast_damped_log_value(
                    float(row.origin_numerator),
                    slope,
                    float(candidate.damping),
                    int(row.horizon),
                )
                if slope is not None
                else None
            )
            predictions[index] = (
                float(row.origin_numerator) if forecast is None else forecast
            )
        return predictions


def prediction_detail(
    points: pd.DataFrame, predictions: np.ndarray, candidate_id: str
) -> pd.DataFrame:
    result = points.copy()
    result["candidate_id"] = candidate_id
    result["predicted_numerator"] = predictions
    result["numerator_absolute_error"] = (
        result["predicted_numerator"] - result["actual_numerator"]
    ).abs()
    result["numerator_model_absolute_error_pp"] = (
        result["numerator_absolute_error"] / result["actual_population"] * 100
    )
    result["predicted_coverage_raw"] = (
        result["predicted_numerator"] / result["predicted_population"] * 100
    )
    result["coverage_absolute_error_pp"] = (
        result["predicted_coverage_raw"] - result["actual_coverage_raw"]
    ).abs()
    result["display_capped_absolute_error_pp"] = (
        result["predicted_coverage_raw"].clip(upper=100)
        - result["actual_coverage_raw"].clip(upper=100)
    ).abs()
    result["population_absolute_percentage_error"] = (
        (result["predicted_population"] - result["actual_population"]).abs()
        / result["actual_population"]
    )
    return result


def summarize_detail(detail: pd.DataFrame) -> dict:
    primary_error = detail["numerator_model_absolute_error_pp"].dropna()
    scenario_error = detail["coverage_absolute_error_pp"].dropna()
    display_error = detail["display_capped_absolute_error_pp"].dropna()
    actual_total = float(detail["actual_numerator"].sum())
    municipality_errors = detail.groupby("codigo_municipio")[
        "numerator_model_absolute_error_pp"
    ].mean()
    return {
        "points": int(len(detail)),
        "primary_metric_points": int(len(primary_error)),
        "coverage_points": int(len(scenario_error)),
        "municipalities": int(detail["codigo_municipio"].nunique()),
        # Alias kept compact for model selection; it is explicitly the raw
        # numerator error divided by the observed target population.
        "mae_percentage_points": float(primary_error.mean()),
        "numerator_model_mae_pp": float(primary_error.mean()),
        "p90_absolute_error_pp": float(primary_error.quantile(0.9)),
        "scenario_mae_pp": float(scenario_error.mean()) if len(scenario_error) else np.nan,
        "scenario_p90_pp": float(scenario_error.quantile(0.9))
        if len(scenario_error)
        else np.nan,
        "display_capped_mae_pp": float(display_error.mean())
        if len(display_error)
        else np.nan,
        "population_mape": float(detail["population_absolute_percentage_error"].mean()),
        "numerator_wape": float(detail["numerator_absolute_error"].sum() / actual_total)
        if actual_total > 0
        else np.nan,
        "cluster_standard_error": float(
            municipality_errors.std(ddof=1) / math.sqrt(len(municipality_errors))
        )
        if len(municipality_errors) > 1
        else 0.0,
    }


def paired_municipality_bootstrap(
    current_detail: pd.DataFrame,
    candidate_detail: pd.DataFrame,
    *,
    iterations: int = 5000,
    seed: int = DEFAULT_SEED,
) -> dict:
    keys = ["codigo_municipio", "origin_year", "target_year", "horizon"]
    left = current_detail[keys + ["numerator_model_absolute_error_pp"]].rename(
        columns={"numerator_model_absolute_error_pp": "current_error"}
    )
    right = candidate_detail[keys + ["numerator_model_absolute_error_pp"]].rename(
        columns={"numerator_model_absolute_error_pp": "candidate_error"}
    )
    paired = left.merge(right, on=keys, how="inner", validate="one_to_one").dropna()
    by_municipality = paired.groupby("codigo_municipio").agg(
        current_error=("current_error", "mean"),
        candidate_error=("candidate_error", "mean"),
    )
    improvements = (
        by_municipality["current_error"] - by_municipality["candidate_error"]
    ).to_numpy(dtype=float)
    if not len(improvements):
        raise ValueError("Bootstrap sem municípios comparáveis.")
    rng = np.random.default_rng(seed)
    samples = rng.choice(improvements, size=(iterations, len(improvements)), replace=True).mean(
        axis=1
    )
    return {
        "municipalities": int(len(improvements)),
        "iterations": int(iterations),
        "mean_improvement_pp": float(improvements.mean()),
        "ci95_low_pp": float(np.quantile(samples, 0.025)),
        "ci95_high_pp": float(np.quantile(samples, 0.975)),
    }


def _stratum_guardrail(current: pd.DataFrame, candidate: pd.DataFrame) -> dict:
    current_metrics = current.groupby("size_stratum")[
        "numerator_model_absolute_error_pp"
    ].mean()
    candidate_metrics = candidate.groupby("size_stratum")[
        "numerator_model_absolute_error_pp"
    ].mean()
    delta = (candidate_metrics - current_metrics).dropna()
    return {
        "worst_stratum_delta_pp": float(delta.max()) if len(delta) else np.nan,
        "stratum_deltas_pp": {str(int(key)): float(value) for key, value in delta.items()},
    }


def select_one_standard_error(candidate_summary: pd.DataFrame) -> tuple[str, str, float]:
    working = candidate_summary.copy()
    history_start = (
        pd.to_numeric(working["history_start"], errors="coerce")
        if "history_start" in working.columns
        else pd.Series(np.nan, index=working.index, dtype=float)
    )
    # If a short window produces the exact same score with 2007 and 2014,
    # prefer the later start: the older observations did not add information.
    working["_history_penalty"] = (2014 - history_start).clip(lower=0).fillna(0)
    ordered = working.sort_values(
        ["mae_percentage_points", "complexity", "_history_penalty", "candidate_id"]
    )
    best = ordered.iloc[0]
    threshold = float(best["mae_percentage_points"] + best["cluster_standard_error"])
    eligible = ordered.loc[ordered["mae_percentage_points"].le(threshold)].sort_values(
        ["complexity", "mae_percentage_points", "_history_penalty", "candidate_id"]
    )
    return str(best["candidate_id"]), str(eligible.iloc[0]["candidate_id"]), threshold


def _final_projection_points(
    enrollment: pd.DataFrame,
    population: pd.DataFrame,
    split: pd.DataFrame,
    rs_age_series: dict[str, pd.Series],
    indicator: str,
    years: Iterable[int] = (2030, 2036),
) -> pd.DataFrame:
    cfg = INDICATORS[indicator]
    latest_num = enrollment.loc[
        enrollment["ano"].eq(2025), ["codigo_municipio", indicator]
    ].rename(columns={indicator: "origin_numerator"})
    latest_pop = population.loc[
        population["ano"].eq(2025), ["codigo_municipio", cfg["population"]]
    ].rename(columns={cfg["population"]: "origin_population"})
    base = latest_num.merge(latest_pop, on="codigo_municipio", validate="one_to_one")
    state_population = rs_age_series[cfg["population_group"]]
    rows = []
    for target_year in years:
        part = base.copy()
        part["origin_year"] = 2025
        part["target_year"] = int(target_year)
        part["horizon"] = int(target_year) - 2025
        part["predicted_population"] = part["origin_population"] * float(
            state_population.loc[target_year]
        ) / float(state_population.loc[2025])
        part["actual_numerator"] = np.nan
        part["actual_population"] = np.nan
        part["actual_coverage_raw"] = np.nan
        rows.append(part.drop(columns="origin_population"))
    return pd.concat(rows, ignore_index=True).merge(
        split, on="codigo_municipio", how="left", validate="many_to_one"
    )


def run_experiment(
    enrollment: pd.DataFrame,
    population: pd.DataFrame,
    rs_age_series: dict[str, pd.Series],
    *,
    output_dir: Path,
    seed: int = DEFAULT_SEED,
    bootstrap_iterations: int = 5000,
) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    split = deterministic_split(enrollment, seed=seed)
    candidates = candidate_grid()
    candidate_by_id = {candidate.candidate_id: candidate for candidate in candidates}
    all_candidate_rows: list[dict] = []
    selected_rows: list[dict] = []
    heldout_rows: list[dict] = []
    bootstrap_rows: list[dict] = []
    primary_horizon_rows: list[dict] = []
    horizon_rows: list[dict] = []
    history_rows: list[dict] = []
    projection_rows: list[pd.DataFrame] = []
    projection_summary_rows: list[dict] = []

    for indicator in INDICATORS:
        engine = ForecastEngine(enrollment, indicator)
        development_points = build_backtest_points(
            enrollment,
            population,
            split,
            rs_age_series,
            indicator,
            target_years=DEVELOPMENT_TARGET_YEARS,
        )
        development = development_points.loc[
            development_points["role"].eq("development")
            & development_points["origin_year"].ge(
                MINIMUM_COMMON_DEVELOPMENT_ORIGIN_YEAR
            )
        ].reset_index(drop=True)
        primary_points = build_backtest_points(
            enrollment, population, split, rs_age_series, indicator
        )
        heldout = primary_points.loc[primary_points["role"].eq("heldout")].reset_index(drop=True)
        dev_predictions: dict[str, np.ndarray] = {}
        for candidate in candidates:
            predictions = engine.predict(candidate, development)
            dev_predictions[candidate.candidate_id] = predictions
            metrics = summarize_detail(
                prediction_detail(development, predictions, candidate.candidate_id)
            )
            all_candidate_rows.append(
                {"indicator": indicator, **asdict(candidate), **metrics}
            )
        indicator_summary = pd.DataFrame(
            [row for row in all_candidate_rows if row["indicator"] == indicator]
        )
        best_id, one_se_id, one_se_threshold = select_one_standard_error(indicator_summary)

        history_best: dict[int, str] = {}
        for history_start in (2007, 2014):
            subset = indicator_summary.loc[
                indicator_summary["history_start"].eq(history_start)
            ].sort_values(["mae_percentage_points", "complexity", "candidate_id"])
            history_best[history_start] = str(subset.iloc[0]["candidate_id"])

        evaluated_ids = list(
            dict.fromkeys(
                [
                    "persistence",
                    "production_current",
                    best_id,
                    one_se_id,
                    history_best[2007],
                    history_best[2014],
                ]
            )
        )
        heldout_details: dict[str, pd.DataFrame] = {}
        for candidate_id in evaluated_ids:
            candidate = candidate_by_id[candidate_id]
            predictions = engine.predict(candidate, heldout)
            detail = prediction_detail(heldout, predictions, candidate_id)
            heldout_details[candidate_id] = detail
            metrics = summarize_detail(detail)
            heldout_rows.append(
                {"indicator": indicator, **asdict(candidate), **metrics}
            )

        current_detail = heldout_details["production_current"]
        one_se_detail = heldout_details[one_se_id]
        for candidate_id, detail in heldout_details.items():
            for horizon, group in detail.groupby("horizon"):
                primary_horizon_rows.append(
                    {
                        "indicator": indicator,
                        "candidate_id": candidate_id,
                        "horizon": int(horizon),
                        **summarize_detail(group),
                    }
                )
        bootstrap = paired_municipality_bootstrap(
            current_detail,
            one_se_detail,
            iterations=bootstrap_iterations,
            seed=seed + list(INDICATORS).index(indicator),
        )
        guardrail = _stratum_guardrail(current_detail, one_se_detail)
        current_metrics = summarize_detail(current_detail)
        candidate_metrics = summarize_detail(one_se_detail)
        p90_ok = candidate_metrics["p90_absolute_error_pp"] <= (
            current_metrics["p90_absolute_error_pp"] * 1.10 + 0.10
        )
        strata_ok = guardrail["worst_stratum_delta_pp"] <= 0.50
        current_by_horizon = current_detail.groupby("horizon")[
            "numerator_model_absolute_error_pp"
        ].mean()
        candidate_by_horizon = one_se_detail.groupby("horizon")[
            "numerator_model_absolute_error_pp"
        ].mean()
        horizon_deltas = (candidate_by_horizon - current_by_horizon).dropna()
        worst_horizon_delta = float(horizon_deltas.max())
        horizon_ok = worst_horizon_delta <= 0.25
        robust_gain = (
            one_se_id != "production_current"
            and bootstrap["ci95_low_pp"] > 0
            and p90_ok
            and strata_ok
            and horizon_ok
        )
        recommended_id = one_se_id if robust_gain else "production_current"
        bootstrap_rows.append(
            {
                "indicator": indicator,
                "candidate_id": one_se_id,
                **bootstrap,
                **guardrail,
                "p90_guardrail_ok": bool(p90_ok),
                "strata_guardrail_ok": bool(strata_ok),
                "worst_horizon_delta_pp": worst_horizon_delta,
                "horizon_deltas_pp": {
                    str(int(key)): float(value) for key, value in horizon_deltas.items()
                },
                "horizon_guardrail_ok": bool(horizon_ok),
                "robust_gain": bool(robust_gain),
            }
        )
        selected_rows.append(
            {
                "indicator": indicator,
                "best_development_candidate": best_id,
                "one_se_candidate": one_se_id,
                "one_se_threshold_pp": one_se_threshold,
                "production_candidate": "production_current",
                "recommended_candidate": recommended_id,
                "recommendation": "replace" if robust_gain else "keep_current",
            }
        )

        for history_start, candidate_id in history_best.items():
            dev_row = indicator_summary.loc[
                indicator_summary["candidate_id"].eq(candidate_id)
            ].iloc[0]
            held_row = summarize_detail(heldout_details[candidate_id])
            history_rows.append(
                {
                    "indicator": indicator,
                    "history_start": history_start,
                    "candidate_id": candidate_id,
                    "development_mae_pp": float(dev_row["mae_percentage_points"]),
                    "heldout_mae_pp": float(held_row["mae_percentage_points"]),
                    "heldout_scenario_mae_pp": float(held_row["scenario_mae_pp"]),
                    "heldout_display_capped_mae_pp": float(
                        held_row["display_capped_mae_pp"]
                    ),
                    "heldout_p90_pp": float(held_row["p90_absolute_error_pp"]),
                    "heldout_numerator_wape": float(held_row["numerator_wape"]),
                }
            )

        supporting_points = build_backtest_points(
            enrollment,
            population,
            split,
            rs_age_series,
            indicator,
            horizons=SUPPORTING_HORIZONS,
        )
        supporting_heldout = supporting_points.loc[
            supporting_points["role"].eq("heldout")
        ].reset_index(drop=True)
        for candidate_id in dict.fromkeys(
            ["persistence", "production_current", best_id, one_se_id, recommended_id]
        ):
            try:
                predictions = engine.predict(
                    candidate_by_id[candidate_id], supporting_heldout
                )
            except ValueError:
                # Holt de produção parte de 2014 e, portanto, não possui cinco
                # observações nos anos-base mais antigos dos horizontes 8/11.
                # O ponto é indisponível, não substituído silenciosamente.
                continue
            detail = prediction_detail(supporting_heldout, predictions, candidate_id)
            for horizon, group in detail.groupby("horizon"):
                metrics = summarize_detail(group)
                horizon_rows.append(
                    {
                        "indicator": indicator,
                        "candidate_id": candidate_id,
                        "horizon": int(horizon),
                        **metrics,
                    }
                )

        future_points = _final_projection_points(
            enrollment, population, split, rs_age_series, indicator
        )
        current_predictions = engine.predict(
            candidate_by_id["production_current"], future_points
        )
        selected_predictions = engine.predict(candidate_by_id[one_se_id], future_points)
        recommended_predictions = engine.predict(
            candidate_by_id[recommended_id], future_points
        )
        future = future_points[
            [
                "codigo_municipio",
                "target_year",
                "predicted_population",
                "size_stratum",
            ]
        ].copy()
        future.insert(1, "indicator", indicator)
        future["current_candidate"] = "production_current"
        future["selected_candidate"] = one_se_id
        future["recommended_candidate"] = recommended_id
        future["current_numerator"] = current_predictions
        future["selected_numerator"] = selected_predictions
        future["recommended_numerator"] = recommended_predictions
        for prefix in ("current", "selected", "recommended"):
            future[f"{prefix}_coverage_raw"] = (
                future[f"{prefix}_numerator"] / future["predicted_population"] * 100
            )
            future[f"{prefix}_coverage_display"] = future[
                f"{prefix}_coverage_raw"
            ].clip(upper=100)
        future["selected_minus_current_pp"] = (
            future["selected_coverage_raw"] - future["current_coverage_raw"]
        )
        future["selected_minus_current_display_pp"] = (
            future["selected_coverage_display"]
            - future["current_coverage_display"]
        )
        future["recommended_minus_current_pp"] = (
            future["recommended_coverage_raw"] - future["current_coverage_raw"]
        )
        future["recommended_minus_current_display_pp"] = (
            future["recommended_coverage_display"]
            - future["current_coverage_display"]
        )
        projection_rows.append(future)
        for target_year, group in future.groupby("target_year"):
            changes = group["selected_minus_current_pp"]
            display_changes = group["selected_minus_current_display_pp"]
            recommended_changes = group["recommended_minus_current_pp"]
            recommended_display_changes = group[
                "recommended_minus_current_display_pp"
            ]
            projection_summary_rows.append(
                {
                    "indicator": indicator,
                    "target_year": int(target_year),
                    "selected_candidate": one_se_id,
                    "recommended_candidate": recommended_id,
                    "median_change_pp": float(changes.median()),
                    "median_absolute_change_pp": float(changes.abs().median()),
                    "p90_absolute_change_pp": float(changes.abs().quantile(0.9)),
                    "municipalities_change_over_2pp": int(changes.abs().gt(2).sum()),
                    "median_display_change_pp": float(display_changes.median()),
                    "median_absolute_display_change_pp": float(
                        display_changes.abs().median()
                    ),
                    "p90_absolute_display_change_pp": float(
                        display_changes.abs().quantile(0.9)
                    ),
                    "municipalities_display_change_over_2pp": int(
                        display_changes.abs().gt(2).sum()
                    ),
                    "recommended_median_change_pp": float(
                        recommended_changes.median()
                    ),
                    "recommended_p90_absolute_change_pp": float(
                        recommended_changes.abs().quantile(0.9)
                    ),
                    "recommended_municipalities_change_over_2pp": int(
                        recommended_changes.abs().gt(2).sum()
                    ),
                    "recommended_median_display_change_pp": float(
                        recommended_display_changes.median()
                    ),
                    "recommended_p90_absolute_display_change_pp": float(
                        recommended_display_changes.abs().quantile(0.9)
                    ),
                    "recommended_municipalities_display_change_over_2pp": int(
                        recommended_display_changes.abs().gt(2).sum()
                    ),
                    "state_current_coverage_raw": float(
                        group["current_numerator"].sum()
                        / group["predicted_population"].sum()
                        * 100
                    ),
                    "state_selected_coverage_raw": float(
                        group["selected_numerator"].sum()
                        / group["predicted_population"].sum()
                        * 100
                    ),
                }
            )

    candidate_summary = pd.DataFrame(all_candidate_rows)
    selected_models = pd.DataFrame(selected_rows)
    heldout_metrics = pd.DataFrame(heldout_rows)
    bootstrap_summary = pd.DataFrame(bootstrap_rows)
    primary_horizon_metrics = pd.DataFrame(primary_horizon_rows)
    horizon_metrics = pd.DataFrame(horizon_rows)
    history_comparison = pd.DataFrame(history_rows)
    projection_shadow = pd.concat(projection_rows, ignore_index=True)
    projection_summary = pd.DataFrame(projection_summary_rows)

    artifacts = {
        "municipality_split.csv": split,
        "candidate_summary.csv": candidate_summary,
        "selected_models.csv": selected_models,
        "heldout_metrics.csv": heldout_metrics,
        "bootstrap_summary.csv": bootstrap_summary,
        "primary_horizon_metrics.csv": primary_horizon_metrics,
        "history_length_comparison.csv": history_comparison,
        "supporting_horizon_metrics.csv": horizon_metrics,
        "projection_impact_summary.csv": projection_summary,
    }
    for name, frame in artifacts.items():
        frame.to_csv(output_dir / name, index=False, encoding="utf-8")
    projection_shadow.to_csv(
        output_dir / "projection_shadow.csv.gz",
        index=False,
        compression={"method": "gzip", "compresslevel": 9, "mtime": 0},
        encoding="utf-8",
    )
    manifest = {
        "experiment_version": EXPERIMENT_VERSION,
        "generated_at_utc": utc_now(),
        "seed": seed,
        "bootstrap_iterations": bootstrap_iterations,
        "primary_horizons": list(PRIMARY_HORIZONS),
        "supporting_horizons": list(SUPPORTING_HORIZONS),
        "development_target_years": list(DEVELOPMENT_TARGET_YEARS),
        "validation_target_years": list(VALIDATION_TARGET_YEARS),
        "minimum_common_development_origin_year": MINIMUM_COMMON_DEVELOPMENT_ORIGIN_YEAR,
        "split_stratification_year": SPLIT_STRATIFICATION_YEAR,
        "development_municipalities": int(split["role"].eq("development").sum()),
        "heldout_municipalities": int(split["role"].eq("heldout").sum()),
        "candidate_count": len(candidates),
        "indicators": list(INDICATORS),
        "production_changed": False,
        "published_data_changed": False,
        "limitations": [
            "A revisão 2024 da projeção etária do IBGE é usada retrospectivamente em todos os modelos; o backtest mede uma simulação com denominador comum, não informação disponível em cada ano passado.",
            "Matrículas são registradas no município da escola e o denominador é a população residente; razões brutas acima de 100% são válidas para auditoria.",
            "O horizonte de 11 anos possui cobertura populacional histórica comparável apenas para origem 2014/alvo 2025; os demais pontos desse horizonte avaliam somente o numerador.",
        ],
        "selection_metric": {
            "name": "mean_absolute_numerator_error_as_raw_percentage_points",
            "formula": "100 × abs(numerador projetado - numerador observado) / população observada no ano-alvo",
            "reason": "isola o modelo de matrículas da revisão populacional e não deixa o teto visual de 100% apagar erros do numerador",
        },
        "secondary_metrics": [
            "end_to_end_raw_scenario_mae_pp_with_projected_population",
            "display_capped_mae_pp_diagnostic_only",
            "numerator_wape",
            "population_mape",
        ],
        "artifacts": [*artifacts, "projection_shadow.csv.gz"],
    }
    (output_dir / "experiment_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    render_internal_report(
        output_dir / "internal_statistical_report.md",
        selected_models,
        heldout_metrics,
        bootstrap_summary,
        history_comparison,
        projection_summary,
    )
    return manifest


def render_internal_report(
    path: Path,
    selected: pd.DataFrame,
    heldout: pd.DataFrame,
    bootstrap: pd.DataFrame,
    history: pd.DataFrame,
    projection: pd.DataFrame,
) -> None:
    decision = selected[
        [
            "indicator",
            "one_se_candidate",
            "recommended_candidate",
            "recommendation",
        ]
    ].copy()
    boot = bootstrap[
        [
            "indicator",
            "mean_improvement_pp",
            "ci95_low_pp",
            "ci95_high_pp",
            "p90_guardrail_ok",
            "strata_guardrail_ok",
        ]
    ]
    decision = decision.merge(boot, on="indicator", how="left")
    def text_table(frame: pd.DataFrame) -> str:
        return "```text\n" + frame.to_string(index=False) + "\n```"

    text_report = f"""# Experimento interno — projeções de atendimento escolar

Gerado em {utc_now()}. Este relatório é de auditoria interna e não deve ser exibido na interface.

## Resumo executivo

{text_table(decision)}

## Comparação do tamanho do histórico

{text_table(history)}

## Métricas no conjunto municipal reservado

{text_table(heldout)}

## Impacto das trajetórias shadow

{text_table(projection)}

## Leitura correta

- A seleção usa alvos de 2019–2022 em 379 municípios; a confirmação usa alvos de 2023–2025 em 118 municípios nunca usados na escolha.
- O porte usado na estratificação é medido em 2018, antes dos alvos de desenvolvimento e validação.
- O erro principal isola o numerador: `100 × |matrículas projetadas - observadas| ÷ população observada no alvo`, sem limite de 100%.
- O erro do cenário completo, já com a população projetada, é mantido como métrica secundária.
- O erro após limitar a exibição a 100% é apenas diagnóstico e nunca escolhe o modelo.
- O bootstrap é pareado por município, preservando juntos os vários anos e horizontes de cada local.
- A população municipal do ano de origem é escalada pela variação etária projetada para o RS, igual para todos os modelos de matrícula.
- Nenhuma decisão deste relatório altera automaticamente o modelo ou os dados publicados.
"""
    path.write_text(text_report, encoding="utf-8")
