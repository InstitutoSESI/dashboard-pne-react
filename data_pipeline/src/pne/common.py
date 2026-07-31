"""Regras de neg?cio puras, sem depend?ncia da aplica??o Dash."""

import pandas as pd

from src.eja_integrada_indicator import EjaIndicatorValidationError, calculate_eja_integrada_series

GOAL_AT_LEAST = "at_least"

GOAL_AT_MOST = "at_most"

DISPLAY_DECIMALS = 1

def _display_rounded(value):
    if value is None or pd.isna(value):
        return None
    rounded = round(float(value), DISPLAY_DECIMALS)
    return 0.0 if rounded == 0 else rounded

def _goal_achieved(distance):
    if distance is None or pd.isna(distance):
        return False
    return float(distance) >= 0

def _fmt_number(value, pattern=",.1f"):
    if value is None or pd.isna(value):
        return "-"
    formatted = f"{float(value):{pattern}}"
    if formatted.startswith("-") and set(
        formatted[1:].replace(",", "").replace(".", "")
    ) <= {"0"}:
        formatted = formatted[1:]
    return formatted.replace(",", "X").replace(".", ",").replace("X", ".")

def _fmt_percent(value):
    if value is None or pd.isna(value):
        return "-"
    return f"{_fmt_number(value)}%"

def _fmt_signed_pp(value):
    if value is None or pd.isna(value):
        return "-"
    prefix = "+" if float(value) > 0 else ""
    return f"{prefix}{_fmt_number(value)} p.p."

def _fmt_signed_number(value):
    if value is None or pd.isna(value):
        return "-"
    prefix = "+" if float(value) > 0 else ""
    return f"{prefix}{_fmt_number(value)}"

def _fmt_years(value):
    if value is None or pd.isna(value):
        return "-"
    return f"{_fmt_number(value)} anos"

def _fmt_signed_years(value):
    if value is None or pd.isna(value):
        return "-"
    prefix = "+" if float(value) > 0 else ""
    return f"{prefix}{_fmt_number(value)} anos"

def _value_mode(item):
    return item.get("value_mode", "percent")

def _format_metric_value(item, value):
    mode = _value_mode(item)
    if mode == "count":
        return _fmt_number(value, ",.0f")
    if mode == "index":
        return _fmt_number(value)
    if mode == "years":
        return _fmt_years(value)
    return _fmt_percent(value)

def _format_metric_distance(item, value):
    mode = _value_mode(item)
    if mode == "count":
        return _fmt_number(value, ",.0f")
    if mode == "index":
        return _fmt_signed_number(value)
    if mode == "years":
        return _fmt_signed_years(value)
    return _fmt_signed_pp(value)

def _empty_result(
    meta,
    direction=GOAL_AT_LEAST,
    meta_label="Meta de referência",
    tracks_goal=True,
):
    return {
        "available": False,
        "meta": meta,
        "meta_label": meta_label,
        "direction": direction,
        "start_year": None,
        "end_year": None,
        "start_value": None,
        "end_value": None,
        "raw_delta": None,
        "progress_delta": None,
        "distance": None,
        "atingida": False,
        "tracks_goal": tracks_goal,
    }

def _safe_load(loader):
    try:
        return loader()
    except Exception as exc:
        print(f"Erro ao carregar dados do painel PNE: {exc}")
        return pd.DataFrame()

def _prepare_yearly_series(df):
    if df.empty or "ano" not in df.columns or "valor" not in df.columns:
        return pd.DataFrame(columns=["ano", "valor"])

    dff = df.copy()
    dff["ano"] = pd.to_numeric(dff["ano"], errors="coerce")
    dff["valor"] = pd.to_numeric(dff["valor"], errors="coerce")
    dff = dff.dropna(subset=["ano", "valor"]).copy()
    if dff.empty:
        return pd.DataFrame(columns=["ano", "valor"])

    dff["ano"] = dff["ano"].astype(int)
    dff = (
        dff.groupby("ano", as_index=False)["valor"]
        .mean()
        .sort_values("ano")
        .reset_index(drop=True)
    )
    return dff

def _select_reference_rows(df, target_start_year, target_end_year):
    if df.empty:
        return None, None

    start_row = df[df["ano"] == target_start_year]
    if start_row.empty:
        start_row = df[df["ano"] >= target_start_year]
    if start_row.empty:
        start_row = df.head(1)
    else:
        start_row = start_row.head(1)

    end_row = df[df["ano"] == target_end_year]
    if end_row.empty:
        end_row = df[df["ano"] <= target_end_year]
    if not end_row.empty:
        end_row = end_row.tail(1)

    if start_row.empty or end_row.empty:
        return None, None

    if int(start_row.iloc[0]["ano"]) > int(end_row.iloc[0]["ano"]):
        return None, None

    return start_row.iloc[0], end_row.iloc[0]

def _build_result(
    df,
    meta,
    *,
    direction=GOAL_AT_LEAST,
    meta_label="Meta de referência",
    target_start_year,
    target_end_year,
    tracks_goal=True,
):
    result = _empty_result(
        meta,
        direction=direction,
        meta_label=meta_label,
        tracks_goal=tracks_goal,
    )
    series = _prepare_yearly_series(df)
    start_row, end_row = _select_reference_rows(
        series,
        target_start_year=target_start_year,
        target_end_year=target_end_year,
    )

    if start_row is None or end_row is None:
        return result

    start_value = float(start_row["valor"])
    end_value = float(end_row["valor"])
    raw_delta = end_value - start_value
    progress_delta = raw_delta if direction == GOAL_AT_LEAST else -raw_delta
    if meta is None:
        distance = None
        atingida = None
    else:
        distance = end_value - meta if direction == GOAL_AT_LEAST else meta - end_value
        atingida = _goal_achieved(distance)
    series_window = (
        series[
            (series["ano"] >= int(start_row["ano"]))
            & (series["ano"] <= int(end_row["ano"]))
        ]
        .copy()
        .reset_index(drop=True)
    )
    series_points = [
        {"ano": int(row["ano"]), "valor": float(row["valor"])}
        for _, row in series_window.iterrows()
    ]

    return {
        "available": True,
        "meta": meta,
        "meta_label": meta_label,
        "direction": direction,
        "start_year": int(start_row["ano"]),
        "end_year": int(end_row["ano"]),
        "start_value": start_value,
        "end_value": end_value,
        "raw_delta": raw_delta,
        "progress_delta": progress_delta,
        "distance": distance,
        "atingida": atingida,
        "series": series_points,
        "tracks_goal": tracks_goal,
    }

def _build_ratio_result(
    loader,
    municipio,
    *,
    numerator,
    denominator,
    meta,
    meta_label="Meta de referência",
    direction=GOAL_AT_LEAST,
    num_agg="sum",
    den_agg="sum",
    filters=None,
    target_start_year,
    target_end_year,
):
    df = _safe_load(loader)
    if df.empty or "municipio" not in df.columns:
        return _empty_result(meta, direction=direction, meta_label=meta_label)

    dff = df[df["municipio"] == municipio].copy()
    if filters:
        for column, value in filters.items():
            if column not in dff.columns:
                return _empty_result(meta, direction=direction, meta_label=meta_label)
            dff = dff[dff[column] == value]

    if dff.empty or numerator not in dff.columns or denominator not in dff.columns:
        return _empty_result(meta, direction=direction, meta_label=meta_label)

    dff[numerator] = pd.to_numeric(dff[numerator], errors="coerce")
    dff[denominator] = pd.to_numeric(dff[denominator], errors="coerce")
    dff = dff.dropna(subset=[numerator, denominator]).copy()
    if dff.empty:
        return _empty_result(meta, direction=direction, meta_label=meta_label)

    yearly = (
        dff.groupby("ano", as_index=False)
        .agg({numerator: num_agg, denominator: den_agg})
        .copy()
    )
    yearly["valor"] = (
        yearly[numerator]
        .div(yearly[denominator].where(yearly[denominator] != 0, pd.NA))
        .mul(100)
    )
    yearly = yearly.dropna(subset=["valor"]).copy()
    if yearly.empty:
        return _empty_result(meta, direction=direction, meta_label=meta_label)
    return _build_result(
        yearly[["ano", "valor"]],
        meta,
        direction=direction,
        meta_label=meta_label,
        target_start_year=target_start_year,
        target_end_year=target_end_year,
    )

def _build_eja_integrada_percentual_result(
    loader,
    municipio,
    *,
    meta,
    meta_label,
    target_start_year,
    target_end_year,
):
    """Calcula o indicador legal a partir dos cinco componentes brutos."""

    df = _safe_load(loader)
    if df.empty or "municipio" not in df.columns:
        return _empty_result(meta, meta_label=meta_label)
    dff = df[df["municipio"] == municipio].copy()
    if dff.empty:
        return _empty_result(meta, meta_label=meta_label)
    try:
        validated = calculate_eja_integrada_series(dff)
    except EjaIndicatorValidationError as exc:
        print(f"Erro de validação do indicador de EJA em {municipio}: {exc}")
        return _empty_result(meta, meta_label=meta_label)

    yearly = validated.dropna(subset=["percentual_calculado"])[
        ["ano", "percentual_calculado"]
    ].rename(columns={"percentual_calculado": "valor"})
    yearly = yearly[
        (yearly["ano"] >= target_start_year)
        & (yearly["ano"] <= target_end_year)
    ].copy()
    if yearly.empty:
        return _empty_result(meta, meta_label=meta_label)
    return _build_result(
        yearly,
        meta,
        direction=GOAL_AT_LEAST,
        meta_label=meta_label,
        target_start_year=target_start_year,
        target_end_year=target_end_year,
        tracks_goal=True,
    )

def _build_value_result(
    loader,
    municipio,
    *,
    value_column,
    meta,
    meta_label="Meta de referência",
    direction=GOAL_AT_LEAST,
    filters=None,
    target_start_year,
    target_end_year,
):
    df = _safe_load(loader)
    if df.empty or "municipio" not in df.columns or value_column not in df.columns:
        return _empty_result(meta, direction=direction, meta_label=meta_label)

    dff = df[df["municipio"] == municipio].copy()
    if filters:
        for column, value in filters.items():
            if column not in dff.columns:
                return _empty_result(meta, direction=direction, meta_label=meta_label)
            dff = dff[dff[column] == value]

    if dff.empty:
        return _empty_result(meta, direction=direction, meta_label=meta_label)

    dff[value_column] = pd.to_numeric(dff[value_column], errors="coerce")
    dff = dff.dropna(subset=[value_column]).copy()
    if dff.empty:
        return _empty_result(meta, direction=direction, meta_label=meta_label)

    yearly = (
        dff.groupby("ano", as_index=False)[value_column]
        .mean()
        .rename(columns={value_column: "valor"})
    )
    return _build_result(
        yearly,
        meta,
        direction=direction,
        meta_label=meta_label,
        target_start_year=target_start_year,
        target_end_year=target_end_year,
    )

def _build_accumulated_growth_result(
    loader,
    municipio,
    *,
    value_column,
    meta,
    meta_label="Meta de referência",
    direction=GOAL_AT_LEAST,
    filters=None,
    value_agg="sum",
    base_year,
    target_start_year,
    target_end_year,
):
    df = _safe_load(loader)
    if df.empty or "municipio" not in df.columns or value_column not in df.columns:
        return _empty_result(meta, direction=direction, meta_label=meta_label)

    dff = df[df["municipio"] == municipio].copy()
    if filters:
        for column, value in filters.items():
            if column not in dff.columns:
                return _empty_result(meta, direction=direction, meta_label=meta_label)
            if isinstance(value, (list, tuple, set, frozenset)):
                dff = dff[dff[column].isin(value)]
            else:
                dff = dff[dff[column] == value]

    if dff.empty:
        return _empty_result(meta, direction=direction, meta_label=meta_label)

    yearly = dff.groupby("ano", as_index=False).agg({value_column: value_agg}).copy()
    yearly[value_column] = pd.to_numeric(yearly[value_column], errors="coerce")
    yearly = (
        yearly.dropna(subset=[value_column]).sort_values("ano").reset_index(drop=True)
    )
    if yearly.empty:
        return _empty_result(meta, direction=direction, meta_label=meta_label)

    base_rows = yearly[(yearly["ano"] >= base_year) & (yearly[value_column] > 0)].copy()
    if base_rows.empty:
        base_rows = yearly[yearly[value_column] > 0].copy()
    if base_rows.empty:
        base_rows = yearly.head(1)

    base_value = float(base_rows.iloc[0][value_column]) if not base_rows.empty else 0.0
    if base_value <= 0:
        return _empty_result(meta, direction=direction, meta_label=meta_label)

    base_reference_year = int(base_rows.iloc[0]["ano"])
    yearly = yearly[yearly["ano"] >= base_reference_year].copy()
    yearly["valor"] = yearly[value_column].div(base_value).sub(1.0).mul(100.0)
    result = _build_result(
        yearly[["ano", "valor"]],
        meta,
        direction=direction,
        meta_label=meta_label,
        target_start_year=base_reference_year,
        target_end_year=target_end_year,
    )
    result["base_year"] = base_reference_year
    return result

def _status_theme(result):
    if not result.get("available"):
        return {
            "text": "Sem dados suficientes",
            "fg": "#64748b",
            "bg": "#e2e8f0",
        }

    if result.get("monitoring_mode") == "approximate_reference":
        return {
            "text": "Indicador aproximado",
            "fg": "#2563eb",
            "bg": "#93c5fd",
        }

    if not result.get("tracks_goal", True):
        return {
            "text": "Visualização informativa",
            "fg": "#2563eb",
            "bg": "#93c5fd",
        }

    if result["atingida"]:
        return {
            "text": "Meta atingida",
            "fg": "#10b981",
            "bg": "#10b981",
        }

    return {
        "text": "Meta não atingida",
        "fg": "#f59e0b",
        "bg": "#f59e0b",
    }

def _tracks_goal(item, result=None):
    if result is not None and "tracks_goal" in result:
        return bool(result.get("tracks_goal", True))
    return bool(item.get("tracks_goal", True))

def _has_time_comparison(result):
    if not result or not result.get("available"):
        return False
    start_year = result.get("start_year")
    end_year = result.get("end_year")
    if start_year is None or end_year is None:
        return False
    return int(start_year) != int(end_year)

def _variation_text(result, item=None):
    delta = result.get("raw_delta")
    if delta is None:
        return "-"
    if item is not None and _value_mode(item) == "count":
        if delta > 0:
            return f"Alta de {_fmt_number(delta, ',.0f')}"
        if delta < 0:
            return f"Queda de {_fmt_number(abs(delta), ',.0f')}"
        return "Sem variação"
    if item is not None and _value_mode(item) == "years":
        if delta > 0:
            return f"Alta de {_fmt_number(delta)} anos"
        if delta < 0:
            return f"Queda de {_fmt_number(abs(delta))} anos"
        return "Sem variação"
    if item is not None and _value_mode(item) == "index":
        if delta > 0:
            return f"Alta de {_fmt_number(delta)}"
        if delta < 0:
            return f"Queda de {_fmt_number(abs(delta))}"
        return "Sem variaÃ§Ã£o"
    if delta > 0:
        return f"Alta de {_fmt_number(delta)} p.p."
    if delta < 0:
        return f"Queda de {_fmt_number(abs(delta))} p.p."
    return "Sem variação"

def _interpretation(item, result):
    if not result.get("available"):
        return (
            "Não foi possível montar a comparação desse indicador com os dados "
            "disponíveis para o município selecionado."
        )

    start_value = _format_metric_value(item, result["start_value"])
    end_value = _format_metric_value(item, result["end_value"])
    end_year = result["end_year"]
    start_year = result["start_year"]

    if not _tracks_goal(item, result):
        if _has_time_comparison(result):
            return (
                f"Entre {start_year} e {end_year}, o indicador passou de {start_value} "
                f"para {end_value}. "
                f"A variação no período foi de {_variation_text(result, item).lower()}."
            )
        return f"Em {end_year}, o indicador registrou {end_value}."

    meta_value = _format_metric_value(item, result["meta"])
    distance = _format_metric_distance(item, result["distance"])

    if _value_mode(item) == "years":
        if result["atingida"]:
            return (
                f"Em {end_year}, o município alcançou {end_value} e superou a meta definida "
                f"({meta_value}). O desempenho ficou {distance} acima da referência."
            )
        return (
            f"Em {end_year}, o município chegou a {end_value}, mas não alcançou a "
            f"meta definida ({meta_value}). A distância atual para a referência é de {distance}."
        )

    if result["atingida"]:
        if result["direction"] == GOAL_AT_MOST:
            return (
                f"Em {end_year}, o indicador ficou em {end_value}, abaixo do limite de "
                f"{meta_value}. Em relação a {start_year}, houve melhora no controle do indicador."
            )
        return (
            f"Em {end_year}, o município alcançou {end_value} e superou a meta definida "
            f"({meta_value}). O desempenho ficou {distance} acima da referência."
        )

    if result["direction"] == GOAL_AT_MOST:
        excesso = _format_metric_distance(item, abs(float(result["distance"]))).replace(
            "+", ""
        )
        return (
            f"Em {end_year}, o indicador ficou em {end_value}, acima do limite de "
            f"{meta_value}. E preciso reduzir {excesso} para enquadrar o resultado na meta."
        )

    return (
        f"Em {end_year}, o município chegou a {end_value}, mas não alcançou a "
        f"meta definida ({meta_value}). A distância atual para a referência é de {distance}."
    )
