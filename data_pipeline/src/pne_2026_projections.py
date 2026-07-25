import logging
import math
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from src.data_loader import (
    load_basico_0_5_data,
    load_basico_4_17_data,
    load_basico_6_14_data,
    load_basico_6_17_data,
    load_basico_15_17_data,
    load_pne_data,
    load_pre_escola_data,
)

warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

logger = logging.getLogger(__name__)

TARGET_YEARS = list(range(2026, 2037))
BASE_YEAR_PREFERRED = 2025
MAX_ANNUAL_NUMERATOR_VARIATION = 0.08
TREND_COMPARISON_YEARS = 5


INDICATOR_CONFIGS = {
    "creche": {
        "loader": load_pne_data,
        "numerator": "mat_basico_0_3",
        "denominator": "pop_0_3",
        "age_group": "0-3",
        "ages": [0, 1, 2, 3],
        "target_percent": 60.0,
        "max_annual_pp": 3.0,
        "slope_damping": 0.30,
        "plausible_cap": 85.0,
    },
    "pre_escola": {
        "loader": load_pre_escola_data,
        "numerator": "mat_infantil_pre",
        "denominator": "pop_4_5",
        "age_group": "4-5",
        "ages": [4, 5],
        "target_percent": 100.0,
        "max_annual_pp": 2.0,
        "slope_damping": 0.35,
        "plausible_cap": 100.0,
    },
    "basico_6_17": {
        "loader": load_basico_6_17_data,
        "numerator": "mat_basico_6_17",
        "denominator": "pop_6_17",
        "age_group": "6-17",
        "ages": list(range(6, 18)),
        "target_percent": 100.0,
        "max_annual_pp": 2.0,
        "slope_damping": 0.35,
        "plausible_cap": 100.0,
    },
    "basico_15_17": {
        "loader": load_basico_15_17_data,
        "numerator": "mat_basico_15_17",
        "denominator": "pop_15_17",
        "age_group": "15-17",
        "ages": [15, 16, 17],
        "target_percent": 85.0,
        "max_annual_pp": 2.0,
        "slope_damping": 0.35,
        "plausible_cap": 100.0,
    },
    "infantil_0_5": {
        "loader": load_basico_0_5_data,
        "numerator": "mat_basico_0_5",
        "denominator": "pop_0_5",
        "age_group": "0-5",
        "ages": list(range(0, 6)),
        "target_percent": None,
        "max_annual_pp": 3.0,
        "slope_damping": 0.30,
        "plausible_cap": 100.0,
    },
    "obrigatoria_4_17": {
        "loader": load_basico_4_17_data,
        "numerator": "mat_basico_4_17",
        "denominator": "pop_4_17",
        "age_group": "4-17",
        "ages": list(range(4, 18)),
        "target_percent": None,
        "max_annual_pp": 2.0,
        "slope_damping": 0.35,
        "plausible_cap": 100.0,
    },
    "escolar_6_14": {
        "loader": load_basico_6_14_data,
        "numerator": "mat_basico_6_14",
        "denominator": "pop_6_14",
        "age_group": "6-14",
        "ages": list(range(6, 15)),
        "target_percent": None,
        "max_annual_pp": 2.0,
        "slope_damping": 0.35,
        "plausible_cap": 100.0,
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
    if base_val is None or pd.isna(base_val) or base_val == 0:
        available = series.dropna()
        if available.empty:
            return None
        base_year_actual = available.index[-1]
        base_val = available.iloc[-1]
    else:
        base_year_actual = base_year

    if base_val is None or pd.isna(base_val) or base_val == 0:
        return None

    factors = {}
    for year in target_years:
        val = series.get(year)
        if val is not None and not pd.isna(val) and val > 0:
            factors[int(year)] = float(val) / float(base_val)

    return {
        "base_year_efetivo": int(base_year_actual),
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


def project_numerator(series, slope_damping=0.5):
    valid = [(int(row["ano"]), float(row["valor"])) for row in series
             if row["valor"] is not None and not (
                 isinstance(row["valor"], float) and math.isnan(row["valor"]))]
    valid.sort(key=lambda x: x[0])

    n = len(valid)
    warnings_list = []
    quality = "media"

    if n >= 3:
        slope_long = _estimate_slope(valid)
        recent = valid[-TREND_COMPARISON_YEARS:] if n >= TREND_COMPARISON_YEARS else valid
        slope_recent = _estimate_slope(recent)
        if slope_long > 0 and slope_recent > slope_long * 1.5:
            slope = min(slope_long, slope_recent)
        elif slope_recent < 0 and slope_long > 0:
            slope = slope_long
        else:
            slope = slope_recent if abs(slope_recent) < abs(slope_long) else slope_long
        slope *= slope_damping
        last_year = valid[-1][0]
    elif n >= 1:
        slope = 0.0
        last_year = valid[-1][0]
        quality = "baixa"
        warnings_list.append("Serie historica insuficiente para tendencia")
    else:
        return {"available": False, "reason": "Sem dados historicos", "warnings": []}

    last_vals = [v for _, v in valid[-3:]]
    base_val = float(np.median(last_vals)) if len(last_vals) >= 2 else last_vals[-1]

    projected = []
    current_val = base_val
    for year in TARGET_YEARS:
        raw_next = current_val + slope
        raw_next = max(0, raw_next)
        if current_val > 0:
            variation = (raw_next - current_val) / current_val
            clamped_variation = max(-MAX_ANNUAL_NUMERATOR_VARIATION,
                                    min(MAX_ANNUAL_NUMERATOR_VARIATION, variation))
            if abs(variation) > MAX_ANNUAL_NUMERATOR_VARIATION:
                warnings_list.append(
                    f"Variacao anual de {variation*100:.1f}% em {year} "
                    f"limitada a {MAX_ANNUAL_NUMERATOR_VARIATION*100:.0f}%"
                )
            next_val = current_val * (1 + clamped_variation)
        else:
            next_val = raw_next

        projected.append({"ano": year, "valor": round(next_val, 1)})
        current_val = next_val

    series_vals = [v[1] for v in valid]
    if series_vals:
        cv = np.std(series_vals) / np.mean(series_vals) if np.mean(series_vals) > 0 else 0
        if cv > 0.5:
            warnings_list.append("Serie historica com alta volatilidade")
            if quality != "baixa":
                quality = "baixa"

    return {
        "available": True,
        "projected": projected,
        "historical": [{"ano": y, "valor": v} for y, v in valid],
        "quality": quality,
        "warnings": warnings_list,
        "slope": slope,
    }


def build_indicator_projection(municipio, config, rs_by_group):
    indicator_key = config["key"]
    cfg = INDICATOR_CONFIGS[indicator_key]

    loader = cfg["loader"]
    df = loader()
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

    slope_damping = cfg.get("slope_damping", 0.5)
    plausible_cap = cfg.get("plausible_cap", 100.0)
    display_cap = 100.0

    num_result = project_numerator(
        [{"ano": r["ano"], "valor": r[num_col]} for r in series],
        slope_damping=slope_damping,
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

    if pop_base_year != BASE_YEAR_PREFERRED:
        all_warnings.append(
            f"Populacao municipal usou ano-base {pop_base_year} por ausencia "
            f"de dado valido em {BASE_YEAR_PREFERRED}; "
            f"fatores RS recalculados para o mesmo ano-base"
        )

    factors = pop_factor_info["factors"]
    rs_base_year = pop_factor_info["base_year_efetivo"]

    max_annual_pp = cfg.get("max_annual_pp", 10.0)

    historical_pop_years = []
    historical_pop_values = []
    for r in series:
        historical_pop_years.append(int(r["ano"]))
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

    historical_percent_capped = [
        max(0.0, min(100.0, v)) if v is not None else None
        for v in historical_percent_raw
    ]

    projected_pop = []
    projected_num = []
    projected_pct_raw = []

    for proj in num_result["projected"]:
        year = proj["ano"]
        pop_factor = factors.get(year)
        if pop_factor is None:
            all_warnings.append(f"Fator populacional indisponivel para {year}, mantendo constante")
            proj_pop = pop_base_value
        else:
            proj_pop = pop_base_value * pop_factor

        proj_num = proj["valor"]
        pct_val = (proj_num / proj_pop * 100) if proj_pop > 0 else None

        projected_pop.append(round(proj_pop, 1))
        projected_num.append(round(proj_num, 1))
        projected_pct_raw.append(round(pct_val, 2) if pct_val is not None else None)

    projected_pct_final = []
    valid_historical_percent = [
        value for value in historical_percent_capped if value is not None
    ]
    prev_pct = valid_historical_percent[-1] if valid_historical_percent else 0.0
    for raw_pct in projected_pct_raw:
        if raw_pct is None:
            projected_pct_final.append(None)
            continue
        capped = max(0.0, min(display_cap, raw_pct))
        diff = capped - prev_pct
        if diff > max_annual_pp:
            capped = prev_pct + max_annual_pp
            all_warnings.append(
                f"Variacao anual do percentual projetado limitada a {max_annual_pp:.0f} p.p. "
                f"(raw era {raw_pct:.1f}%)"
            )
        elif diff < -max_annual_pp:
            capped = prev_pct - max_annual_pp
            all_warnings.append(
                f"Variacao anual do percentual projetado limitada a {max_annual_pp:.0f} p.p. "
                f"(raw era {raw_pct:.1f}%)"
            )
        final_val = max(0.0, min(plausible_cap, capped))
        projected_pct_final.append(round(final_val, 2))
        prev_pct = capped

    projected_2036_raw = projected_pct_raw[-1] if len(projected_pct_raw) >= 11 else None
    projected_2036_final = projected_pct_final[-1] if len(projected_pct_final) >= 11 else None
    target = cfg["target_percent"]

    if projected_2036_final is not None and target is not None:
        distance_to_target = round(projected_2036_final - target, 2)
        status_2036 = "tende_a_atingir" if projected_2036_final >= target else "risco_de_nao_atingir"
    else:
        distance_to_target = None
        status_2036 = None

    return {
        "available": True,
        "base_year": pop_base_year,
        "target_year": 2036,
        "method": (
            "Tendencia suavizada com limite plausivel por indicador "
            "para reduzir extrapolacoes excessivas"
        ),
        "population_age_group": age_group,
        "historical_years": historical_num_years,
        "historical_numerator": historical_num_values,
        "historical_population": historical_pop_values,
        "historical_percent_raw": historical_percent_raw,
        "historical_percent": historical_percent_capped,
        "years": TARGET_YEARS,
        "projected_population": projected_pop,
        "projected_numerator": projected_num,
        "projected_percent_raw": projected_pct_raw,
        "projected_percent": projected_pct_final,
        "target_percent": target,
        "projected_2036": projected_2036_final,
        "projected_2036_raw": projected_2036_raw,
        "distance_to_target_2036": distance_to_target,
        "status_2036": status_2036,
        "quality": quality,
        "warnings": all_warnings,
    }


def build_all_projections(municipios):
    rs_path = (
        Path(__file__).resolve().parents[3]
        / ".."
        / ".."
        / "SESI"
        / "DB"
        / "data"
        / "projecao_populacao"
        / "projecao_pop.xlsx"
    )
    if not rs_path.exists():
        alt_path = Path(
            "C:/Users/rnbirck/PROJETOS/SESI/DB/data/projecao_populacao/projecao_pop.xlsx"
        )
        if alt_path.exists():
            rs_path = alt_path
        else:
            logger.error("Arquivo de projecao populacional nao encontrado")
            return {}

    rs_df = load_rs_population_projection(str(rs_path))

    age_groups = {cfg["age_group"]: cfg["ages"] for cfg in INDICATOR_CONFIGS.values()}
    rs_by_group = build_rs_population_by_age_group(rs_df, age_groups)

    results = {}
    for municipio in municipios:
        municipio_projections = {}
        for indicator_key in INDICATOR_CONFIGS:
            config = {"key": indicator_key}
            try:
                proj = build_indicator_projection(municipio, config, rs_by_group)
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
