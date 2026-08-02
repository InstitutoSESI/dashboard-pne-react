import pandas as pd

from src.pipeline_profiling import profiled_aggregate_query_call

from src.data_loader import load_basico_15_17_data
from src.data_loader import load_basico_15_17_por_dependencia_data
from src.data_loader import load_basico_6_17_data
from src.data_loader import load_basico_6_17_por_dependencia_data
from src.data_loader import load_atendimento_educacional_especializado_data
from src.data_loader import load_basico_integral_por_dependencia_data
from src.data_loader import load_censo_populacao_alfabetizacao_data
from src.data_loader import load_censo_populacao_ensino_fundamental_6_14_data
from src.data_loader import load_censo_populacao_ensino_fundamental_concluido_15_29_data
from src.data_loader import load_censo_populacao_ensino_fundamental_concluido_15_mais_data
from src.data_loader import load_censo_populacao_ensino_fundamental_concluido_18_mais_data
from src.data_loader import load_censo_populacao_ensino_medio_15_17_data
from src.data_loader import load_censo_populacao_ensino_medio_concluido_18_29_data
from src.data_loader import load_censo_populacao_ensino_medio_concluido_18_mais_data
from src.data_loader import load_censo_populacao_escolaridade_media_18_29_data
from src.data_loader import load_censo_populacao_escolaridade_media_18_29_racial_data
from src.data_loader import load_creche_por_dependencia_data
from src.data_loader import load_adequacao_docente_data
from src.data_loader import load_docentes_pos_graduacao_data
from src.data_loader import load_docentes_temporarios_data
from src.data_loader import load_eja_integrada_educacao_profissional_data
from src.data_loader import load_ept_nivel_medio_data
from src.data_loader import load_escolas_integral_data
from src.data_loader import load_escolas_integral_por_dependencia_data
from src.data_loader import load_infraestrutura_escolar_data
from src.data_loader import load_infraestrutura_escolar_por_dependencia_data
from src.data_loader import load_school_infrastructure_contract
from src.data_loader import load_medio_tecnico_articulado_data
from src.data_loader import load_medio_tecnico_data
from src.data_loader import load_matriculas_privadas_conveniadas
from src.data_loader import load_pne_data
from src.data_loader import load_pre_escola_data
from src.data_loader import load_pre_escola_por_dependencia_data
from src.medio_tecnico_articulado import (
    MedioTecnicoArticuladoValidationError,
    calculate_medio_tecnico_articulado_series,
    calculate_public_expansion_series,
    calculate_subsequent_expansion_series,
)
from src.school_infrastructure_materialization import (
    REFERENCE_YEAR as SCHOOL_INFRASTRUCTURE_REFERENCE_YEAR,
    adapt_pne_internet_details,
)


_DEPENDENCIA_ORDER = ["municipal", "estadual", "privada", "federal"]


def _safe_load(loader):
    try:
        return loader()
    except Exception as exc:
        print(f"Erro ao carregar dados complementares: {exc}")
        return pd.DataFrame()


def _normalizar_dependencia(value):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    normalized = (
        str(value)
        .lower()
        .strip()
        .replace("á", "a")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ú", "u")
        .replace("ã", "a")
        .replace("õ", "o")
        .replace("ç", "c")
    )
    if normalized in {"publica", "pública"}:
        return None
    return normalized if normalized in _DEPENDENCIA_ORDER else None


def _build_column_based_dependency_series(df, municipio, column_map):
    if df.empty or "ano" not in df.columns:
        return []

    if "municipio" in df.columns:
        dff = df[df["municipio"] == municipio].copy()
    else:
        dff = df.copy()

    if dff.empty:
        return []

    dff["ano"] = pd.to_numeric(dff["ano"], errors="coerce")
    for dep_key, col_name in column_map.items():
        if col_name in dff.columns:
            dff[col_name] = pd.to_numeric(dff[col_name], errors="coerce")

    available_columns = [col for col in column_map.values() if col in dff.columns]
    if not available_columns:
        return []

    dff = dff.dropna(subset=["ano"] + available_columns).copy()
    if dff.empty:
        return []

    dff["ano"] = dff["ano"].astype(int)
    for col in available_columns:
        dff[col] = dff[col].clip(lower=0)

    agg_dict = {col: "sum" for col in available_columns}
    grouped = (
        dff.groupby("ano", as_index=False)
        .agg(agg_dict)
        .sort_values("ano")
    )

    series_dependencia = []
    for _, row in grouped.iterrows():
        entry = {"ano": int(row["ano"])}
        for dep_key, col_name in column_map.items():
            if col_name in grouped.columns:
                entry[dep_key] = int(row[col_name])
        series_dependencia.append(entry)

    return series_dependencia


def build_creche_details(municipio):
    df = _safe_load(load_creche_por_dependencia_data)
    if df.empty or "municipio" not in df.columns:
        return None

    dff = df[df["municipio"] == municipio].copy()
    if dff.empty:
        return None

    dff["ano"] = pd.to_numeric(dff["ano"], errors="coerce")
    dff["mat_infantil_creche"] = pd.to_numeric(
        dff["mat_infantil_creche"], errors="coerce"
    )
    dff["dependencia"] = dff["dependencia"].apply(_normalizar_dependencia)
    dff = dff.dropna(subset=["ano", "mat_infantil_creche", "dependencia"]).copy()
    if dff.empty:
        return None

    dff["ano"] = dff["ano"].astype(int)
    dff["mat_infantil_creche"] = dff["mat_infantil_creche"].clip(lower=0)

    grouped = (
        dff.groupby(["ano", "dependencia"], as_index=False)["mat_infantil_creche"]
        .sum()
        .sort_values(["ano", "dependencia"])
    )

    total_by_year = (
        grouped.groupby("ano", as_index=False)["mat_infantil_creche"]
        .sum()
        .rename(columns={"mat_infantil_creche": "valor"})
        .sort_values("ano")
    )
    total_by_year["valor"] = total_by_year["valor"].astype(int)
    series_total = [
        {"ano": int(row["ano"]), "valor": int(row["valor"])}
        for _, row in total_by_year.iterrows()
        if row["valor"] >= 0
    ]

    pivot = grouped.pivot(
        index="ano", columns="dependencia", values="mat_infantil_creche"
    ).fillna(0)
    for dep in _DEPENDENCIA_ORDER:
        if dep not in pivot.columns:
            pivot[dep] = 0
    pivot = pivot[_DEPENDENCIA_ORDER].reset_index().sort_values("ano")

    series_dependencia = [
        {
            "ano": int(row["ano"]),
            "municipal": int(row["municipal"]),
            "estadual": int(row["estadual"]),
            "privada": int(row["privada"]),
            "federal": int(row["federal"]),
        }
        for _, row in pivot.iterrows()
    ]

    if not series_total or not series_dependencia:
        return None

    payload = {
        "title": "Matrículas em creche",
        "subtitle": "Total de matrículas em creche e distribuição por dependência administrativa com dados do Censo Escolar. Os números usados no cálculo percentual seguem a base consolidada do indicador em cada ciclo.",
        "unit": "matrículas",
        "calculation": {
            "numerator_label": "Matrículas em creche",
            "denominator_label": "População de 0 a 3 anos",
        },
        "series_total": series_total,
        "series_dependencia": series_dependencia,
    }

    calculation_df = _safe_load(load_pne_data)
    required_columns = {"ano", "municipio", "mat_infantil_creche", "mat_basico_0_3", "pop_0_3"}
    if not calculation_df.empty and required_columns.issubset(calculation_df.columns):
        calculation_dff = calculation_df[calculation_df["municipio"] == municipio].copy()
        if not calculation_dff.empty:
            calculation_dff["ano"] = pd.to_numeric(calculation_dff["ano"], errors="coerce")
            calculation_dff["mat_infantil_creche"] = pd.to_numeric(
                calculation_dff["mat_infantil_creche"], errors="coerce"
            )
            calculation_dff["mat_basico_0_3"] = pd.to_numeric(
                calculation_dff["mat_basico_0_3"], errors="coerce"
            )
            calculation_dff["pop_0_3"] = pd.to_numeric(
                calculation_dff["pop_0_3"], errors="coerce"
            )
            calculation_dff = calculation_dff.dropna(subset=["ano", "pop_0_3"]).copy()

            components_by_cycle = {}
            cycle_numerators = {
                "pne_2014_2024": "mat_infantil_creche",
                "pne_2026_2036": "mat_basico_0_3",
            }
            for cycle, numerator_column in cycle_numerators.items():
                if numerator_column not in calculation_dff.columns:
                    continue
                yearly = (
                    calculation_dff.dropna(subset=[numerator_column])
                    .groupby("ano", as_index=False)
                    .agg({numerator_column: "sum", "pop_0_3": "max"})
                    .sort_values("ano")
                )
                components = []
                for _, row in yearly.iterrows():
                    numerador = row[numerator_column]
                    denominador = row["pop_0_3"]
                    if pd.isna(numerador) or pd.isna(denominador) or denominador <= 0:
                        continue
                    numerador = int(numerador)
                    denominador = int(denominador)
                    components.append(
                        {
                            "ano": int(row["ano"]),
                            "numerador": numerador,
                            "denominador": denominador,
                            "percentual": round((numerador / denominador) * 100, 1),
                        }
                    )

                if components:
                    components_by_cycle[cycle] = components

            if components_by_cycle:
                payload["series_components_by_cycle"] = components_by_cycle

    return payload


def build_pre_escola_details(municipio):
    df = _safe_load(load_pre_escola_por_dependencia_data)
    if df.empty or "municipio" not in df.columns:
        return None

    dff = df[df["municipio"] == municipio].copy()
    if dff.empty:
        return None

    dff["ano"] = pd.to_numeric(dff["ano"], errors="coerce")
    dff["mat_infantil_pre"] = pd.to_numeric(
        dff["mat_infantil_pre"], errors="coerce"
    )
    dff["dependencia"] = dff["dependencia"].apply(_normalizar_dependencia)
    dff = dff.dropna(subset=["ano", "mat_infantil_pre", "dependencia"]).copy()
    if dff.empty:
        return None

    dff["ano"] = dff["ano"].astype(int)
    dff["mat_infantil_pre"] = dff["mat_infantil_pre"].clip(lower=0)

    grouped = (
        dff.groupby(["ano", "dependencia"], as_index=False)["mat_infantil_pre"]
        .sum()
        .sort_values(["ano", "dependencia"])
    )

    total_by_year = (
        grouped.groupby("ano", as_index=False)["mat_infantil_pre"]
        .sum()
        .rename(columns={"mat_infantil_pre": "valor"})
        .sort_values("ano")
    )
    total_by_year["valor"] = total_by_year["valor"].astype(int)
    series_total = [
        {"ano": int(row["ano"]), "valor": int(row["valor"])}
        for _, row in total_by_year.iterrows()
        if row["valor"] > 0
    ]

    pivot = grouped.pivot(
        index="ano", columns="dependencia", values="mat_infantil_pre"
    ).fillna(0)
    for dep in _DEPENDENCIA_ORDER:
        if dep not in pivot.columns:
            pivot[dep] = 0
    pivot = pivot[_DEPENDENCIA_ORDER].reset_index().sort_values("ano")

    series_dependencia = [
        {
            "ano": int(row["ano"]),
            "municipal": int(row["municipal"]),
            "estadual": int(row["estadual"]),
            "privada": int(row["privada"]),
            "federal": int(row["federal"]),
        }
        for _, row in pivot.iterrows()
    ]

    if not series_total or not series_dependencia:
        return None

    payload = {
        "title": "Matrículas na pré-escola",
        "subtitle": "Total de matrículas de 4 a 5 anos na pré-escola e distribuição por dependência administrativa.",
        "unit": "matrículas",
        "series_total": series_total,
        "series_dependencia": series_dependencia,
    }

    pop_df = _safe_load(load_pre_escola_data)
    if not pop_df.empty and {"ano", "municipio", "pop_4_5"}.issubset(pop_df.columns):
        pop_dff = pop_df[pop_df["municipio"] == municipio].copy()
        if not pop_dff.empty:
            pop_dff["ano"] = pd.to_numeric(pop_dff["ano"], errors="coerce")
            pop_dff["pop_4_5"] = pd.to_numeric(pop_dff["pop_4_5"], errors="coerce")
            pop_by_year = (
                pop_dff.dropna(subset=["ano", "pop_4_5"])
                .groupby("ano", as_index=False)["pop_4_5"]
                .max()
                .sort_values("ano")
            )
            total_by_year_map = {
                int(row["ano"]): int(row["valor"])
                for _, row in total_by_year.iterrows()
                if pd.notna(row["ano"]) and pd.notna(row["valor"]) and row["valor"] > 0
            }
            series_components = []
            for _, row in pop_by_year.iterrows():
                ano = int(row["ano"])
                numerador = total_by_year_map.get(ano)
                denominador = row["pop_4_5"]
                if numerador is None or pd.isna(denominador) or denominador <= 0:
                    continue
                denominador = int(denominador)
                series_components.append(
                    {
                        "ano": ano,
                        "numerador": numerador,
                        "denominador": denominador,
                        "percentual": round((numerador / denominador) * 100, 1),
                    }
                )

            if series_components:
                payload["calculation"] = {
                    "numerator_label": "Matrículas na pré-escola",
                    "denominator_label": "População de 4 a 5 anos",
                }
                payload["series_components"] = series_components

    return payload


def _build_matriculas_basico_details(
    municipio,
    *,
    loader,
    value_column,
    title,
    subtitle,
    component_loader=None,
    component_numerator_column=None,
    component_denominator_column=None,
    calculation=None,
):
    df = _safe_load(loader)
    if df.empty or "municipio" not in df.columns:
        return None

    dff = df[df["municipio"] == municipio].copy()
    if dff.empty:
        return None

    dff["ano"] = pd.to_numeric(dff["ano"], errors="coerce")
    dff[value_column] = pd.to_numeric(dff[value_column], errors="coerce")
    dff["dependencia"] = dff["dependencia"].apply(_normalizar_dependencia)
    dff = dff.dropna(subset=["ano", value_column, "dependencia"]).copy()
    if dff.empty:
        return None

    dff["ano"] = dff["ano"].astype(int)
    dff[value_column] = dff[value_column].clip(lower=0)

    grouped = (
        dff.groupby(["ano", "dependencia"], as_index=False)[value_column]
        .sum()
        .sort_values(["ano", "dependencia"])
    )

    total_by_year = (
        grouped.groupby("ano", as_index=False)[value_column]
        .sum()
        .rename(columns={value_column: "valor"})
        .sort_values("ano")
    )
    total_by_year["valor"] = total_by_year["valor"].astype(int)
    series_total = [
        {"ano": int(row["ano"]), "valor": int(row["valor"])}
        for _, row in total_by_year.iterrows()
        if row["valor"] > 0
    ]

    pivot = grouped.pivot(
        index="ano", columns="dependencia", values=value_column
    ).fillna(0)
    for dep in _DEPENDENCIA_ORDER:
        if dep not in pivot.columns:
            pivot[dep] = 0
    pivot = pivot[_DEPENDENCIA_ORDER].reset_index().sort_values("ano")

    series_dependencia = [
        {
            "ano": int(row["ano"]),
            "municipal": int(row["municipal"]),
            "estadual": int(row["estadual"]),
            "privada": int(row["privada"]),
            "federal": int(row["federal"]),
        }
        for _, row in pivot.iterrows()
    ]

    if not series_total or not series_dependencia:
        return None

    payload = {
        "title": title,
        "subtitle": subtitle,
        "unit": "matrículas",
        "series_total": series_total,
        "series_dependencia": series_dependencia,
    }

    if (
        component_loader is not None
        and component_numerator_column
        and component_denominator_column
        and calculation
    ):
        component_df = _safe_load(component_loader)
        required_columns = {
            "ano",
            "municipio",
            component_numerator_column,
            component_denominator_column,
        }
        if not component_df.empty and required_columns.issubset(component_df.columns):
            component_dff = component_df[component_df["municipio"] == municipio].copy()
            if not component_dff.empty:
                component_dff["ano"] = pd.to_numeric(
                    component_dff["ano"], errors="coerce"
                )
                component_dff[component_numerator_column] = pd.to_numeric(
                    component_dff[component_numerator_column], errors="coerce"
                )
                component_dff[component_denominator_column] = pd.to_numeric(
                    component_dff[component_denominator_column], errors="coerce"
                )
                component_dff = component_dff.dropna(
                    subset=[
                        "ano",
                        component_numerator_column,
                        component_denominator_column,
                    ]
                ).copy()

                yearly = (
                    component_dff.groupby("ano", as_index=False)
                    .agg(
                        {
                            component_numerator_column: "sum",
                            component_denominator_column: "max",
                        }
                    )
                    .sort_values("ano")
                )

                series_components = []
                for _, row in yearly.iterrows():
                    numerador = row[component_numerator_column]
                    denominador = row[component_denominator_column]
                    if pd.isna(numerador) or pd.isna(denominador) or denominador <= 0:
                        continue
                    numerador = int(numerador)
                    denominador = int(denominador)
                    series_components.append(
                        {
                            "ano": int(row["ano"]),
                            "numerador": numerador,
                            "denominador": denominador,
                            "percentual": round((numerador / denominador) * 100, 1),
                        }
                    )

                if series_components:
                    payload["calculation"] = calculation
                    payload["series_components"] = series_components

    return payload


def build_basico_6_17_details(municipio):
    return _build_matriculas_basico_details(
        municipio,
        loader=load_basico_6_17_por_dependencia_data,
        value_column="matriculas_basico_6_17",
        title="Matrículas na educação básica — 6 a 17 anos",
        subtitle="Total de matrículas de 6 a 17 anos na educação básica e distribuição por dependência administrativa. Os números usados no cálculo percentual seguem a base consolidada do indicador.",
        component_loader=load_basico_6_17_data,
        component_numerator_column="mat_basico_6_17",
        component_denominator_column="pop_6_17",
        calculation={
            "numerator_label": "Matrículas de 6 a 17 anos na educação básica",
            "denominator_label": "População de 6 a 17 anos",
        },
    )


def build_basico_15_17_details(municipio):
    return _build_matriculas_basico_details(
        municipio,
        loader=load_basico_15_17_por_dependencia_data,
        value_column="matriculas_basico_15_17",
        title="Matrículas na educação básica — 15 a 17 anos",
        subtitle="Total de matrículas de 15 a 17 anos na educação básica e distribuição por dependência administrativa. A distribuição por dependência vem do Censo Escolar e os componentes do cálculo vêm da base consolidada do indicador.",
        component_loader=load_basico_15_17_data,
        component_numerator_column="mat_basico_15_17",
        component_denominator_column="pop_15_17",
        calculation={
            "numerator_label": "Matrículas de 15 a 17 anos na educação básica",
            "denominator_label": "População de 15 a 17 anos",
        },
    )


def build_basico_integral_details(municipio):
    df = _safe_load(load_basico_integral_por_dependencia_data)
    required_columns = {
        "ano",
        "municipio",
        "dependencia",
        "mat_basico",
        "mat_basico_integral",
    }
    if df.empty or not required_columns.issubset(df.columns):
        return None

    dff = df[df["municipio"] == municipio].copy()
    if dff.empty:
        return None

    dff["ano"] = pd.to_numeric(dff["ano"], errors="coerce")
    dff["mat_basico"] = pd.to_numeric(dff["mat_basico"], errors="coerce")
    dff["mat_basico_integral"] = pd.to_numeric(
        dff["mat_basico_integral"], errors="coerce"
    )
    dff["dependencia"] = dff["dependencia"].apply(_normalizar_dependencia)
    dff = dff.dropna(
        subset=["ano", "mat_basico", "mat_basico_integral", "dependencia"]
    ).copy()
    if dff.empty:
        return None

    dff["ano"] = dff["ano"].astype(int)
    dff["mat_basico"] = dff["mat_basico"].clip(lower=0)
    dff["mat_basico_integral"] = dff["mat_basico_integral"].clip(lower=0)

    grouped = (
        dff.groupby(["ano", "dependencia"], as_index=False)
        .agg({"mat_basico_integral": "sum", "mat_basico": "sum"})
        .sort_values(["ano", "dependencia"])
    )

    total_by_year = (
        grouped.groupby("ano", as_index=False)
        .agg({"mat_basico_integral": "sum", "mat_basico": "sum"})
        .rename(columns={"mat_basico_integral": "valor"})
        .sort_values("ano")
    )
    total_by_year["valor"] = total_by_year["valor"].astype(int)
    total_by_year["mat_basico"] = total_by_year["mat_basico"].astype(int)

    series_total = [
        {"ano": int(row["ano"]), "valor": int(row["valor"])}
        for _, row in total_by_year.iterrows()
        if row["valor"] > 0
    ]

    series_components = []
    for _, row in total_by_year.iterrows():
        numerador = int(row["valor"])
        denominador = int(row["mat_basico"])
        if numerador <= 0 or denominador <= 0:
            continue
        series_components.append(
            {
                "ano": int(row["ano"]),
                "numerador": numerador,
                "denominador": denominador,
                "percentual": round((numerador / denominador) * 100, 1),
            }
        )

    pivot = grouped.pivot(
        index="ano", columns="dependencia", values="mat_basico_integral"
    ).fillna(0)
    for dep in _DEPENDENCIA_ORDER:
        if dep not in pivot.columns:
            pivot[dep] = 0
    pivot = pivot[_DEPENDENCIA_ORDER].reset_index().sort_values("ano")

    series_dependencia = [
        {
            "ano": int(row["ano"]),
            "municipal": int(row["municipal"]),
            "estadual": int(row["estadual"]),
            "privada": int(row["privada"]),
            "federal": int(row["federal"]),
        }
        for _, row in pivot.iterrows()
    ]

    if not series_total or not series_dependencia or not series_components:
        return None

    return {
        "title": "Matrículas em tempo integral na educação básica pública",
        "subtitle": "Total de matrículas em tempo integral na educação básica pública, total de matrículas da educação básica pública e distribuição por dependência administrativa.",
        "unit": "matrículas",
        "calculation": {
            "numerator_label": "Matrículas em tempo integral",
            "denominator_label": "Total de matrículas da educação básica pública",
        },
        "series_total": series_total,
        "series_dependencia": series_dependencia,
        "series_components": series_components,
    }


def _build_escolas_integral_dependency_payload(municipio):
    df = _safe_load(load_escolas_integral_por_dependencia_data)
    required_columns = {
        "ano",
        "municipio",
        "dependencia",
        "escolas_publicas_com_integral",
        "escolas_publicas_total",
        "percentual_escolas_publicas_com_integral",
    }
    if df.empty or not required_columns.issubset(df.columns):
        return {}

    dff = df[df["municipio"] == municipio].copy()
    if dff.empty:
        return {}

    dependency_order = ["federal", "estadual", "municipal"]
    dff["dependencia"] = dff["dependencia"].astype(str).str.lower().str.strip()
    dff = dff[dff["dependencia"].isin(dependency_order)].copy()
    if dff.empty:
        return {}

    dff["ano"] = pd.to_numeric(dff["ano"], errors="coerce")
    for column in [
        "escolas_publicas_com_integral",
        "escolas_publicas_total",
        "percentual_escolas_publicas_com_integral",
    ]:
        dff[column] = pd.to_numeric(dff[column], errors="coerce")
    dff = dff.dropna(
        subset=[
            "ano",
            "dependencia",
            "escolas_publicas_com_integral",
            "escolas_publicas_total",
            "percentual_escolas_publicas_com_integral",
        ]
    ).copy()
    if dff.empty:
        return {}

    dff["ano"] = dff["ano"].astype(int)
    for column in [
        "escolas_publicas_com_integral",
        "escolas_publicas_total",
        "percentual_escolas_publicas_com_integral",
    ]:
        dff[column] = dff[column].clip(lower=0)

    grouped = (
        dff.groupby(["ano", "dependencia"], as_index=False)
        .agg(
            {
                "escolas_publicas_com_integral": "sum",
                "escolas_publicas_total": "sum",
            }
        )
        .sort_values(["ano", "dependencia"])
    )
    grouped["percentual_escolas_publicas_com_integral"] = (
        100.0
        * grouped["escolas_publicas_com_integral"]
        / grouped["escolas_publicas_total"].replace(0, pd.NA)
    )

    pivot = grouped.pivot(
        index="ano",
        columns="dependencia",
        values="percentual_escolas_publicas_com_integral",
    ).reset_index()
    series_dependencia = []
    for _, row in pivot.iterrows():
        entry = {"ano": int(row["ano"])}
        for dependency in dependency_order:
            if dependency in pivot.columns and pd.notna(row[dependency]):
                entry[dependency] = round(float(row[dependency]), 1)
        if len(entry) > 1:
            series_dependencia.append(entry)

    series_dependencia_components = []
    for _, row in grouped.iterrows():
        numerador = row["escolas_publicas_com_integral"]
        denominador = row["escolas_publicas_total"]
        percentual = row["percentual_escolas_publicas_com_integral"]
        if (
            pd.isna(numerador)
            or pd.isna(denominador)
            or pd.isna(percentual)
            or denominador <= 0
        ):
            continue
        series_dependencia_components.append(
            {
                "ano": int(row["ano"]),
                "dependencia": row["dependencia"],
                "numerador": int(numerador),
                "denominador": int(denominador),
                "percentual": round(float(percentual), 1),
            }
        )

    if not series_dependencia:
        return {}

    payload = {
        "dependency_unit": "%",
        "dependency_value_type": "percent",
        "dependency_calculation": {
            "numerator_label": "Escolas publicas com jornada em tempo integral na rede",
            "denominator_label": "Total de escolas publicas da rede",
        },
        "series_dependencia": series_dependencia,
    }
    if series_dependencia_components:
        payload["series_dependencia_components"] = series_dependencia_components
    return payload


def build_escolas_integral_details(municipio):
    df = _safe_load(load_escolas_integral_data)
    required_columns = {
        "ano",
        "municipio",
        "escolas_publicas_com_integral",
        "escolas_publicas_total",
    }
    if df.empty or not required_columns.issubset(df.columns):
        return None

    dff = df[df["municipio"] == municipio].copy()
    if dff.empty:
        return None

    dff["ano"] = pd.to_numeric(dff["ano"], errors="coerce")
    dff["escolas_publicas_com_integral"] = pd.to_numeric(
        dff["escolas_publicas_com_integral"], errors="coerce"
    )
    dff["escolas_publicas_total"] = pd.to_numeric(
        dff["escolas_publicas_total"], errors="coerce"
    )
    dff = dff.dropna(
        subset=[
            "ano",
            "escolas_publicas_com_integral",
            "escolas_publicas_total",
        ]
    ).copy()
    if dff.empty:
        return None

    dff["ano"] = dff["ano"].astype(int)
    dff["escolas_publicas_com_integral"] = dff["escolas_publicas_com_integral"].clip(
        lower=0
    )
    dff["escolas_publicas_total"] = dff["escolas_publicas_total"].clip(lower=0)

    total_by_year = (
        dff.groupby("ano", as_index=False)["escolas_publicas_com_integral"]
        .sum()
        .rename(columns={"escolas_publicas_com_integral": "valor"})
        .sort_values("ano")
    )
    total_by_year["valor"] = total_by_year["valor"].astype(int)
    series_total = [
        {"ano": int(row["ano"]), "valor": int(row["valor"])}
        for _, row in total_by_year.iterrows()
        if row["valor"] > 0
    ]

    yearly = (
        dff.groupby("ano", as_index=False)
        .agg(
            {
                "escolas_publicas_com_integral": "sum",
                "escolas_publicas_total": "max",
            }
        )
        .sort_values("ano")
    )
    series_components = []
    for _, row in yearly.iterrows():
        numerador = row["escolas_publicas_com_integral"]
        denominador = row["escolas_publicas_total"]
        if pd.isna(numerador) or pd.isna(denominador) or denominador <= 0:
            continue
        numerador = int(numerador)
        denominador = int(denominador)
        series_components.append(
            {
                "ano": int(row["ano"]),
                "numerador": numerador,
                "denominador": denominador,
                "percentual": round((numerador / denominador) * 100, 1),
            }
        )

    if not series_total or not series_components:
        return None

    payload = {
        "title": "Escolas públicas com alunos em jornada de tempo integral",
        "subtitle": "Total de escolas públicas da educação básica que possuem, pelo menos, 25% dos alunos em jornada integral e o total de escolas públicas.",
        "unit": "escolas",
        "calculation": {
            "numerator_label": "Escolas públicas com jornada em tempo integral",
            "denominator_label": "Total de escolas públicas",
        },
        "series_total": series_total,
        "series_components": series_components,
    }

    payload.update(_build_escolas_integral_dependency_payload(municipio))
    return payload


def build_aee_details(municipio):
    df = _safe_load(load_atendimento_educacional_especializado_data)
    required_columns = {
        "ano",
        "municipio",
        "quantidade_aee",
        "total_turmas_educacao_especial",
    }
    if df.empty or not required_columns.issubset(df.columns):
        return None

    dff = df[df["municipio"] == municipio].copy()
    if dff.empty:
        return None

    dff["ano"] = pd.to_numeric(dff["ano"], errors="coerce")
    dff["quantidade_aee"] = pd.to_numeric(
        dff["quantidade_aee"], errors="coerce"
    )
    dff["total_turmas_educacao_especial"] = pd.to_numeric(
        dff["total_turmas_educacao_especial"], errors="coerce"
    )
    dff = dff.dropna(
        subset=[
            "ano",
            "quantidade_aee",
            "total_turmas_educacao_especial",
        ]
    ).copy()
    if dff.empty:
        return None

    dff["ano"] = dff["ano"].astype(int)
    dff["quantidade_aee"] = dff["quantidade_aee"].clip(lower=0)
    dff["total_turmas_educacao_especial"] = dff[
        "total_turmas_educacao_especial"
    ].clip(lower=0)

    total_by_year = (
        dff.groupby("ano", as_index=False)["quantidade_aee"]
        .sum()
        .rename(columns={"quantidade_aee": "valor"})
        .sort_values("ano")
    )
    total_by_year["valor"] = total_by_year["valor"].astype(int)
    series_total = [
        {"ano": int(row["ano"]), "valor": int(row["valor"])}
        for _, row in total_by_year.iterrows()
        if row["valor"] > 0
    ]

    yearly = (
        dff.groupby("ano", as_index=False)
        .agg(
            {
                "quantidade_aee": "sum",
                "total_turmas_educacao_especial": "max",
            }
        )
        .sort_values("ano")
    )
    series_components = []
    for _, row in yearly.iterrows():
        numerador = row["quantidade_aee"]
        denominador = row["total_turmas_educacao_especial"]
        if pd.isna(numerador) or pd.isna(denominador) or denominador <= 0:
            continue
        numerador = int(numerador)
        denominador = int(denominador)
        series_components.append(
            {
                "ano": int(row["ano"]),
                "numerador": numerador,
                "denominador": denominador,
                "percentual": round((numerador / denominador) * 100, 1),
            }
        )

    if not series_total or not series_components:
        return None

    return {
        "title": "Oferta de AEE na educação especial",
        "subtitle": "Total de turmas de Atendimento Educacional Especializado e o total de turmas de educação especial no município.",
        "unit": "turmas",
        "calculation": {
            "numerator_label": "Turmas de Atendimento Educacional Especializado",
            "denominator_label": "Total de turmas de educação especial",
        },
        "series_total": series_total,
        "series_components": series_components,
    }


def build_medio_tecnico_details(municipio):
    unavailable_payload = {
        "title": "Matriculas do ensino medio integradas a educacao profissional tecnica",
        "subtitle": (
            "Percentual de matriculas do ensino medio integradas a educacao "
            "profissional tecnica sobre o total de matriculas do ensino medio."
        ),
        "unit": "matriculas",
        "calculation": {
            "numerator_label": (
                "Matriculas do ensino medio integradas a educacao profissional tecnica"
            ),
            "denominator_label": "Total de matriculas do ensino medio",
        },
    }
    df = _safe_load(load_medio_tecnico_data)
    required_columns = {
        "ano",
        "municipio",
        "mat_medio",
        "mat_profissional_tecnico",
    }
    if df.empty or not required_columns.issubset(df.columns):
        return unavailable_payload

    dff = df[df["municipio"] == municipio].copy()
    if dff.empty:
        return unavailable_payload

    dff["ano"] = pd.to_numeric(dff["ano"], errors="coerce")
    dff["mat_medio"] = pd.to_numeric(dff["mat_medio"], errors="coerce")
    dff["mat_profissional_tecnico"] = pd.to_numeric(
        dff["mat_profissional_tecnico"], errors="coerce"
    )
    dff = dff.dropna(subset=["ano", "mat_medio", "mat_profissional_tecnico"]).copy()
    if dff.empty:
        return unavailable_payload

    dff["ano"] = dff["ano"].astype(int)
    dff["mat_medio"] = dff["mat_medio"].clip(lower=0)
    dff["mat_profissional_tecnico"] = dff["mat_profissional_tecnico"].clip(lower=0)

    yearly_2026 = (
        dff.groupby("ano", as_index=False)
        .agg(
            {
                "mat_profissional_tecnico": "sum",
                "mat_medio": "sum",
            }
        )
        .sort_values("ano")
    )
    if yearly_2026.empty:
        return unavailable_payload

    yearly_2026["mat_profissional_tecnico"] = yearly_2026[
        "mat_profissional_tecnico"
    ].astype(int)
    yearly_2026["mat_medio"] = yearly_2026["mat_medio"].astype(int)
    series_total = [
        {"ano": int(row["ano"]), "valor": int(row["mat_profissional_tecnico"])}
        for _, row in yearly_2026.iterrows()
        if row["mat_medio"] > 0
    ]
    components_2026 = []
    for _, row in yearly_2026.iterrows():
        numerador = row["mat_profissional_tecnico"]
        denominador = row["mat_medio"]
        if pd.isna(numerador) or pd.isna(denominador) or denominador <= 0:
            continue
        numerador = int(numerador)
        denominador = int(denominador)
        components_2026.append(
            {
                "ano": int(row["ano"]),
                "numerador": numerador,
                "denominador": denominador,
                "percentual": round((numerador / denominador) * 100, 1),
            }
        )

    series_components_by_cycle = {}
    if components_2026:
        series_components_by_cycle["pne_2026_2036"] = components_2026

    if not series_total or not series_components_by_cycle:
        return unavailable_payload

    payload = {
        "title": "Matrículas em EPT de nível médio",
        "subtitle": "Total de matrículas da Educação Profissional e Tecnológica de nível médio e, no ciclo 2026‑2036, o percentual integrado à educação profissional técnica.",
        "unit": "matrículas",
        "calculation": {
            "numerator_label": "Matrículas integradas à educação profissional técnica",
            "denominator_label": "Total de matrículas do ensino médio",
        },
        "series_total": series_total,
        "series_components_by_cycle": series_components_by_cycle,
    }
    payload["title"] = (
        "Matriculas do ensino medio integradas a educacao profissional tecnica"
    )
    payload["subtitle"] = (
        "Percentual de matriculas do ensino medio integradas a educacao "
        "profissional tecnica sobre o total de matriculas do ensino medio."
    )
    payload["unit"] = "matriculas"
    payload["calculation"] = {
        "numerator_label": (
            "Matriculas do ensino medio integradas a educacao profissional tecnica"
        ),
        "denominator_label": "Total de matriculas do ensino medio",
    }

    return payload


def build_medio_tecnico_articulado_percentual_details(municipio):
    df = _safe_load(load_medio_tecnico_articulado_data)
    required_columns = {
        "ano",
        "id_municipio",
        "municipio",
        "mat_integrado_total",
        "mat_concomitante_total",
        "mat_medio",
    }
    if df.empty or not required_columns.issubset(df.columns):
        return None

    dff = df[df["municipio"] == municipio].copy()
    if dff.empty:
        return None

    try:
        calculated = calculate_medio_tecnico_articulado_series(dff)
    except MedioTecnicoArticuladoValidationError as exc:
        print(f"Dados complementares indisponíveis para {municipio}: {exc}")
        return None

    calculated = calculated[
        calculated["ano"].between(2015, 2025)
    ].copy()
    if calculated.empty:
        return None

    valid_ratio = calculated.dropna(subset=["percentual_calculado"]).copy()
    if valid_ratio.empty:
        return None

    series_total = [
        {
            "ano": int(row["ano"]),
            "valor": int(row["mat_articulado_total"]),
        }
        for _, row in valid_ratio.iterrows()
    ]
    series_components = [
        {
            "ano": int(row["ano"]),
            "numerador": int(row["mat_articulado_total"]),
            "denominador": int(row["mat_medio"]),
            "percentual": float(row["percentual_calculado"]),
            "integrado": int(row["mat_integrado_total"]),
            "concomitante": int(row["mat_concomitante_total"]),
            "articulado": int(row["mat_articulado_total"]),
            "percentual_articulado": float(row["percentual_articulado_total"]),
            "acima_de_100": bool(row["acima_de_100"]),
        }
        for _, row in valid_ratio.dropna(
            subset=[
                "mat_concomitante_total",
                "mat_articulado_total",
                "percentual_articulado_total",
            ]
        ).iterrows()
    ]

    series_auxiliares = {}
    for key, column in (
        ("integrado", "mat_integrado_total"),
        ("concomitante", "mat_concomitante_total"),
        ("articulado", "mat_articulado_total"),
        ("medio", "mat_medio"),
    ):
        series_auxiliares[key] = [
            {"ano": int(row["ano"]), "valor": int(row[column])}
            for _, row in calculated.dropna(subset=[column]).iterrows()
        ]

    dependency_columns = {
        "federal": ("mat_integrado_federal", "mat_concomitante_federal"),
        "estadual": ("mat_integrado_estadual", "mat_concomitante_estadual"),
        "municipal": ("mat_integrado_municipal", "mat_concomitante_municipal"),
        "privada": ("mat_integrado_privada", "mat_concomitante_privada"),
    }
    dependency_fields = [column for columns in dependency_columns.values() for column in columns]
    series_dependencia = []
    if all(column in calculated.columns for column in dependency_fields):
        for _, row in valid_ratio.iterrows():
            if any(pd.isna(row[column]) for column in dependency_fields):
                continue
            entry = {"ano": int(row["ano"])}
            for dependency, columns in dependency_columns.items():
                entry[dependency] = int(row[columns[0]]) + int(row[columns[1]])
            if sum(entry[dependency] for dependency in dependency_columns) == int(
                row["mat_articulado_total"]
            ):
                series_dependencia.append(entry)

    above_100_years = [
        int(row["ano"]) for _, row in valid_ratio.iterrows() if bool(row["acima_de_100"])
    ]
    payload = {
        "title": (
            "Matrículas em cursos técnicos integrados ou concomitantes "
            "em relação às matrículas do ensino médio"
        ),
        "subtitle": (
            "Percentual das matrículas em cursos técnicos integrados ou concomitantes "
            "em relação ao total de matrículas do ensino médio."
        ),
        "unit": "%",
        "calculation": {
            "numerator_label": "Matrículas em cursos técnicos integrados ou concomitantes",
            "denominator_label": "Total de matrículas do ensino médio",
        },
        "series_total": series_total,
        "series_components_by_cycle": {
            "pne_2026_2036": series_components,
        },
        "series_auxiliares": series_auxiliares,
        "source": "INEP — Sinopse Estatística da Educação Básica.",
        "methodology_note": (
            "Indicador calculado pela soma das matrículas em cursos técnicos integrados "
            "e concomitantes, dividida pelo total de matrículas do ensino médio. A fonte "
            "não identifica estudantes únicos, por isso a relação permanece complementar."
        ),
        "reference": {
            "year": 2036,
            "value": 50,
            "label": "Meta PNE 2036",
        },
        "acima_de_100_anos": above_100_years,
    }
    if series_dependencia:
        payload["series_dependencia"] = series_dependencia
        payload["dependency_unit"] = "Matrículas"
        payload["dependency_value_type"] = "count"
    if above_100_years:
        payload["warning"] = (
            "Valores acima de 100% podem ocorrer porque a medida usa matrículas e não "
            "estudantes únicos."
        )
    return payload


def build_medio_tecnico_total_details(municipio):
    df = _safe_load(load_ept_nivel_medio_data)
    required_columns = {
        "ano",
        "municipio",
        "mat_ept_nivel_medio_total",
    }
    if df.empty or not required_columns.issubset(df.columns):
        return None

    dff = df[df["municipio"] == municipio].copy()
    if dff.empty:
        return None

    dff["ano"] = pd.to_numeric(dff["ano"], errors="coerce")
    dff["mat_ept_nivel_medio_total"] = pd.to_numeric(
        dff["mat_ept_nivel_medio_total"], errors="coerce"
    )
    dff = dff.dropna(subset=["ano", "mat_ept_nivel_medio_total"]).copy()
    if dff.empty:
        return None

    dff["ano"] = dff["ano"].astype(int)
    dff["mat_ept_nivel_medio_total"] = dff["mat_ept_nivel_medio_total"].clip(lower=0)

    total_by_year = (
        dff.groupby("ano", as_index=False)["mat_ept_nivel_medio_total"]
        .sum()
        .rename(columns={"mat_ept_nivel_medio_total": "valor"})
        .sort_values("ano")
    )
    total_by_year["valor"] = total_by_year["valor"].astype(int)
    series_total = [
        {"ano": int(row["ano"]), "valor": int(row["valor"])}
        for _, row in total_by_year.iterrows()
        if row["valor"] > 0
    ]

    if not series_total:
        return None

    series_dependencia = _build_column_based_dependency_series(df, municipio, {
        "federal": "mat_ept_nivel_medio_federal",
        "estadual": "mat_ept_nivel_medio_estadual",
        "municipal": "mat_ept_nivel_medio_municipal",
        "privada": "mat_ept_nivel_medio_privada",
    })

    payload = {
        "title": "Número absoluto de matrículas em EPT de nível médio",
        "subtitle": "Total de matrículas da Educação Profissional e Tecnológica de nível médio no município.",
        "unit": "matrículas",
        "series_total": series_total,
    }

    if series_dependencia:
        payload["series_dependencia"] = series_dependencia

    return payload


def build_medio_tecnico_participacao_publica_details(municipio):
    df = _safe_load(load_ept_nivel_medio_data)
    if df.empty or "municipio" not in df.columns:
        return None
    dff = df[df["municipio"] == municipio].copy()
    if dff.empty:
        return None
    try:
        calculated = calculate_public_expansion_series(dff)
    except MedioTecnicoArticuladoValidationError:
        return None
    available = calculated[calculated["data_status"] == "available"]
    if available.empty:
        return None
    return {
        "title": "Participação pública na expansão da EPT de nível médio desde 2025",
        "subtitle": "Participação da expansão líquida pública na expansão líquida total desde a base fixa de 2025.",
        "unit": "%",
        "calculation": {
            "numerator_label": "Expansão líquida pública",
            "denominator_label": "Expansão líquida total",
        },
        "series_components": [
            {
                "ano": int(row["ano"]),
                "numerador": float(row["numerador"]),
                "denominador": float(row["denominador"]),
                "percentual": float(row["valor"]),
            }
            for _, row in available.iterrows()
        ],
        "source": "INEP — Sinopse Estatística da Educação Básica.",
        "methodology_note": (
            "Base fixa em 2025; rede pública federal, estadual e municipal. "
            "Expansões negativas e valores acima de 100% são preservados."
        ),
    }


def build_subsequente_expansao_details(municipio):
    df = _safe_load(load_ept_nivel_medio_data)
    if df.empty or "municipio" not in df.columns:
        return None
    dff = df[df["municipio"] == municipio].copy()
    if dff.empty:
        return None
    try:
        calculated = calculate_subsequent_expansion_series(dff)
    except MedioTecnicoArticuladoValidationError:
        return None
    available = calculated[calculated["data_status"] == "available"]
    if available.empty:
        return None
    return {
        "title": "Expansão das matrículas em cursos técnicos subsequentes desde 2025",
        "subtitle": "Expansão percentual em relação à base fixa de 2025.",
        "unit": "%",
        "calculation": {
            "numerator_label": "Variação absoluta desde 2025",
            "denominator_label": "Matrículas subsequentes em 2025",
        },
        "series_components": [
            {
                "ano": int(row["ano"]),
                "numerador": float(row["numerador"]),
                "denominador": float(row["denominador"]),
                "percentual": float(row["valor"]),
            }
            for _, row in available.iterrows()
        ],
        "source": "INEP — Sinopse Estatística da Educação Básica.",
        "methodology_note": (
            "Base fixa em 2025; base zero é não aplicável. Retrações e expansões "
            "acima de 100% são preservadas."
        ),
    }


def build_eja_integrada_educacao_profissional_details(municipio):
    df = _safe_load(load_eja_integrada_educacao_profissional_data)
    required_columns = {
        "ano",
        "municipio",
        "mat_eja_denominador_calculado",
        "mat_eja_integrada_educacao_profissional_calculada",
    }
    if df.empty or not required_columns.issubset(df.columns):
        return None

    dff = df[df["municipio"] == municipio].copy()
    if dff.empty:
        return None

    dff["ano"] = pd.to_numeric(dff["ano"], errors="coerce")
    dff["mat_eja_denominador_calculado"] = pd.to_numeric(
        dff["mat_eja_denominador_calculado"], errors="coerce"
    )
    dff["mat_eja_integrada_educacao_profissional_calculada"] = pd.to_numeric(
        dff["mat_eja_integrada_educacao_profissional_calculada"], errors="coerce"
    )
    dff = dff.dropna(
        subset=[
            "ano",
            "mat_eja_denominador_calculado",
            "mat_eja_integrada_educacao_profissional_calculada",
        ]
    ).copy()
    if dff.empty:
        return None

    dff["ano"] = dff["ano"].astype(int)
    dff["mat_eja_denominador_calculado"] = dff[
        "mat_eja_denominador_calculado"
    ].clip(lower=0)
    dff["mat_eja_integrada_educacao_profissional_calculada"] = dff[
        "mat_eja_integrada_educacao_profissional_calculada"
    ].clip(lower=0)

    total_by_year = (
        dff.groupby("ano", as_index=False)["mat_eja_integrada_educacao_profissional_calculada"]
        .sum()
        .rename(
            columns={
                "mat_eja_integrada_educacao_profissional_calculada": "valor"
            }
        )
        .sort_values("ano")
    )
    total_by_year["valor"] = total_by_year["valor"].astype(int)
    series_total = [
        {"ano": int(row["ano"]), "valor": int(row["valor"])}
        for _, row in total_by_year.iterrows()
        if row["valor"] > 0
    ]

    yearly = (
        dff.groupby("ano", as_index=False)
        .agg(
            {
                "mat_eja_integrada_educacao_profissional_calculada": "sum",
                "mat_eja_denominador_calculado": "max",
            }
        )
        .sort_values("ano")
    )
    components = []
    for _, row in yearly.iterrows():
        numerador = row["mat_eja_integrada_educacao_profissional_calculada"]
        denominador = row["mat_eja_denominador_calculado"]
        if pd.isna(numerador) or pd.isna(denominador) or denominador <= 0:
            continue
        numerador = int(numerador)
        denominador = int(denominador)
        components.append(
            {
                "ano": int(row["ano"]),
                "numerador": numerador,
                "denominador": denominador,
                "percentual": round((numerador / denominador) * 100, 1),
            }
        )

    series_components_by_cycle = {}
    if components:
        series_components_by_cycle["pne_2014_2024"] = [
            row for row in components if row["ano"] <= 2024
        ]
        series_components_by_cycle["pne_2026_2036"] = components

    dependencia_columns = {
        "federal": "mat_eja_integrada_educacao_profissional_federal",
        "estadual": "mat_eja_integrada_educacao_profissional_estadual",
        "municipal": "mat_eja_integrada_educacao_profissional_municipal",
        "privada": "mat_eja_integrada_educacao_profissional_privada",
    }
    series_by_dependencia = None
    if all(col in dff.columns for col in dependencia_columns.values()):
        dep_rows = []
        for _, row in dff.iterrows():
            entry = {"ano": int(row["ano"])}
            has_value = False
            for dep, col in dependencia_columns.items():
                val = int(row[col]) if pd.notna(row[col]) and row[col] >= 0 else 0
                if val > 0:
                    entry[dep] = val
                    has_value = True
            if has_value:
                dep_rows.append(entry)
        if dep_rows:
            series_by_dependencia = dep_rows

    if not series_total:
        return None

    result = {
        "title": "Matrículas do EJA integradas à educação profissional",
        "subtitle": "Número absoluto de matrículas do EJA integradas à educação profissional no município. No ciclo 2014‑2024 também é apresentado o percentual em relação ao total de matrículas do EJA.",
        "unit": "matrículas",
        "calculation": {
            "numerator_label": "Matrículas do EJA integradas à educação profissional",
            "denominator_label": "EJA fundamental + EJA médio",
        },
        "series_total": series_total,
        "series_components_by_cycle": series_components_by_cycle,
        "source": "INEP — Sinopse Estatística da Educação Básica, tabelas EJA 1.35 e Educação Profissional 1.30/1.42.",
    }
    if series_by_dependencia is not None:
        result["series_dependencia"] = series_by_dependencia

    return result


def build_eja_integrada_educacao_profissional_percentual_details(municipio):
    result = build_eja_integrada_educacao_profissional_details(municipio)
    if result is None:
        return None
    return {
        **result,
        "title": "Percentual das matrículas da EJA articuladas à educação profissional",
        "subtitle": (
            "Percentual recalculado pela soma do curso técnico integrado à EJA, "
            "FIC integrado à EJA fundamental e FIC integrado à EJA médio, dividido "
            "pelas matrículas da EJA fundamental e médio."
        ),
        "unit": "%",
        "calculation": {
            "numerator_label": "Curso técnico integrado à EJA + FIC integrado à EJA fundamental + FIC integrado à EJA médio",
            "denominator_label": "Matrículas da EJA fundamental + matrículas da EJA médio",
        },
    }


def _build_infra_details(municipio, *, count_column, denominator_column, numerator_label, denominator_label, title, unit, include_public_dependency=False, exclude_year=None):
    df = _safe_load(load_infraestrutura_escolar_data)
    required_columns = {"ano", "municipio", count_column, denominator_column}
    if df.empty or not required_columns.issubset(df.columns):
        return None

    dff = df[df["municipio"] == municipio].copy()
    if dff.empty:
        return None

    dff["ano"] = pd.to_numeric(dff["ano"], errors="coerce")
    dff[count_column] = pd.to_numeric(dff[count_column], errors="coerce")
    dff[denominator_column] = pd.to_numeric(dff[denominator_column], errors="coerce")
    dff = dff.dropna(subset=["ano", count_column, denominator_column]).copy()
    if dff.empty:
        return None

    dff["ano"] = dff["ano"].astype(int)
    if exclude_year is not None:
        dff = dff[dff["ano"].ne(int(exclude_year))].copy()
    dff[count_column] = dff[count_column].clip(lower=0)
    dff[denominator_column] = dff[denominator_column].clip(lower=0)

    total_by_year = (
        dff.groupby("ano", as_index=False)[count_column]
        .sum()
        .rename(columns={count_column: "valor"})
        .sort_values("ano")
    )
    total_by_year["valor"] = total_by_year["valor"].astype(int)
    series_total = [
        {"ano": int(row["ano"]), "valor": int(row["valor"])}
        for _, row in total_by_year.iterrows()
        if row["valor"] > 0
    ]

    yearly = (
        dff.groupby("ano", as_index=False)
        .agg({count_column: "sum", denominator_column: "max"})
        .sort_values("ano")
    )
    series_components = []
    for _, row in yearly.iterrows():
        numerador = row[count_column]
        denominador = row[denominator_column]
        if pd.isna(numerador) or pd.isna(denominador) or denominador <= 0:
            continue
        numerador = int(numerador)
        denominador = int(denominador)
        series_components.append(
            {
                "ano": int(row["ano"]),
                "numerador": numerador,
                "denominador": denominador,
                "percentual": round((numerador / denominador) * 100, 1),
            }
        )

    series_dependencia = []
    if include_public_dependency:
        series_dependencia = [
            {"ano": int(row["ano"]), "publica": int(row["valor"])}
            for _, row in total_by_year.iterrows()
            if row["valor"] > 0
        ]

    if not series_total or not series_components:
        return None

    payload = {
        "title": title,
        "subtitle": f"Total de {unit} com a característica e total de {unit} no município.",
        "unit": unit,
        "calculation": {
            "numerator_label": numerator_label,
            "denominator_label": denominator_label,
        },
        "series_total": series_total,
        "series_components": series_components,
    }

    if series_dependencia:
        payload["series_dependencia"] = series_dependencia

    return payload


def _build_infra_dependency_series(df, municipio, count_column, exclude_year=None):
    if df.empty or "ano" not in df.columns:
        return []

    dff = df[df["municipio"] == municipio].copy()
    if dff.empty:
        return []

    dff = dff[dff["dependencia"].notna()].copy()
    dff["dependencia"] = dff["dependencia"].str.strip().str.lower()
    dff = dff[dff["dependencia"] != ""].copy()
    if dff.empty:
        return []

    dff["ano"] = pd.to_numeric(dff["ano"], errors="coerce")
    dff[count_column] = pd.to_numeric(dff[count_column], errors="coerce")
    dff = dff.dropna(subset=["ano", count_column]).copy()
    if dff.empty:
        return []

    dff["ano"] = dff["ano"].astype(int)
    if exclude_year is not None:
        dff = dff[dff["ano"].ne(int(exclude_year))].copy()
    dff[count_column] = dff[count_column].clip(lower=0)

    grouped = (
        dff.groupby(["ano", "dependencia"], as_index=False)[count_column]
        .sum()
        .sort_values(["ano", "dependencia"])
    )

    pivot = grouped.pivot(
        index="ano", columns="dependencia", values=count_column
    ).fillna(0)

    series_dependencia = []
    for index, row in pivot.iterrows():
        entry = {"ano": int(index)}
        for dep in pivot.columns:
            value = int(row[dep])
            entry[dep] = value
        series_dependencia.append(entry)

    return series_dependencia


def build_internet_details(municipio):
    payload = _build_infra_details(
        municipio,
        count_column="escolas_com_internet",
        denominator_column="qntd_escolas",
        numerator_label="Escolas com internet",
        denominator_label="Total de escolas",
        title="Escolas da educação básica com acesso à internet",
        unit="escolas",
        exclude_year=SCHOOL_INFRASTRUCTURE_REFERENCE_YEAR,
    )

    if payload is not None:
        dep_df = _safe_load(load_infraestrutura_escolar_por_dependencia_data)
        if not dep_df.empty:
            series_dependencia = _build_infra_dependency_series(
                dep_df,
                municipio,
                "escolas_com_internet",
                exclude_year=SCHOOL_INFRASTRUCTURE_REFERENCE_YEAR,
            )
            if series_dependencia:
                payload["series_dependencia"] = series_dependencia

    contract = _safe_load(lambda: load_school_infrastructure_contract(municipio))
    if isinstance(contract, dict):
        payload = adapt_pne_internet_details(payload, contract)
    return payload


def build_internet_alunos_details(municipio):
    payload = _build_infra_details(
        municipio,
        count_column="escolas_com_internet_alunos",
        denominator_column="qntd_escolas",
        numerator_label="Escolas com internet para alunos",
        denominator_label="Total de escolas",
        title="Escolas com internet disponível para os alunos",
        unit="escolas",
    )

    if payload is not None:
        dep_df = _safe_load(load_infraestrutura_escolar_por_dependencia_data)
        if not dep_df.empty:
            series_dependencia = _build_infra_dependency_series(
                dep_df, municipio, "escolas_com_internet_alunos"
            )
            if series_dependencia:
                payload["series_dependencia"] = series_dependencia

    return payload


def build_internet_aprendizagem_details(municipio):
    payload = _build_infra_details(
        municipio,
        count_column="escolas_com_internet_aprendizagem",
        denominator_column="qntd_escolas",
        numerator_label="Escolas com internet para aprendizagem",
        denominator_label="Total de escolas",
        title="Escolas com internet usada na aprendizagem",
        unit="escolas",
    )

    if payload is not None:
        dep_df = _safe_load(load_infraestrutura_escolar_por_dependencia_data)
        if not dep_df.empty:
            series_dependencia = _build_infra_dependency_series(
                dep_df, municipio, "escolas_com_internet_aprendizagem"
            )
            if series_dependencia:
                payload["series_dependencia"] = series_dependencia

    return payload


def build_internet_comunidade_details(municipio):
    payload = _build_infra_details(
        municipio,
        count_column="escolas_com_internet_comunidade",
        denominator_column="qntd_escolas",
        numerator_label="Escolas com internet para comunidade",
        denominator_label="Total de escolas",
        title="Escolas com internet aberta à comunidade",
        unit="escolas",
    )

    if payload is not None:
        dep_df = _safe_load(load_infraestrutura_escolar_por_dependencia_data)
        if not dep_df.empty:
            series_dependencia = _build_infra_dependency_series(
                dep_df, municipio, "escolas_com_internet_comunidade"
            )
            if series_dependencia:
                payload["series_dependencia"] = series_dependencia

    return payload


def build_acesso_internet_computador_details(municipio):
    payload = _build_infra_details(
        municipio,
        count_column="escolas_com_acesso_internet_computador",
        denominator_column="qntd_escolas",
        numerator_label="Escolas com acesso à internet por computador",
        denominator_label="Total de escolas",
        title="Escolas com acesso dos alunos à internet por computador",
        unit="escolas",
    )

    if payload is not None:
        dep_df = _safe_load(load_infraestrutura_escolar_por_dependencia_data)
        if not dep_df.empty:
            series_dependencia = _build_infra_dependency_series(
                dep_df, municipio, "escolas_com_acesso_internet_computador"
            )
            if series_dependencia:
                payload["series_dependencia"] = series_dependencia

    return payload


def build_acesso_internet_disp_pessoais_details(municipio):
    payload = _build_infra_details(
        municipio,
        count_column="escolas_com_acesso_internet_disp_pessoais",
        denominator_column="qntd_escolas",
        numerator_label="Escolas com acesso à internet por dispositivos pessoais",
        denominator_label="Total de escolas",
        title="Escolas com acesso dos alunos à internet por dispositivos pessoais",
        unit="escolas",
    )

    if payload is not None:
        dep_df = _safe_load(load_infraestrutura_escolar_por_dependencia_data)
        if not dep_df.empty:
            series_dependencia = _build_infra_dependency_series(
                dep_df, municipio, "escolas_com_acesso_internet_disp_pessoais"
            )
            if series_dependencia:
                payload["series_dependencia"] = series_dependencia

    return payload


def build_rede_local_details(municipio):
    payload = _build_infra_details(
        municipio,
        count_column="escolas_com_rede_local",
        denominator_column="qntd_escolas",
        numerator_label="Escolas com rede local",
        denominator_label="Total de escolas",
        title="Escolas com rede local de computadores",
        unit="escolas",
    )

    if payload is not None:
        dep_df = _safe_load(load_infraestrutura_escolar_por_dependencia_data)
        if not dep_df.empty:
            series_dependencia = _build_infra_dependency_series(
                dep_df, municipio, "escolas_com_rede_local"
            )
            if series_dependencia:
                payload["series_dependencia"] = series_dependencia

    return payload


def build_rede_wireless_details(municipio):
    payload = _build_infra_details(
        municipio,
        count_column="escolas_com_rede_wireless",
        denominator_column="qntd_escolas",
        numerator_label="Escolas com rede sem fio",
        denominator_label="Total de escolas",
        title="Escolas com rede local sem fio",
        unit="escolas",
    )

    if payload is not None:
        dep_df = _safe_load(load_infraestrutura_escolar_por_dependencia_data)
        if not dep_df.empty:
            series_dependencia = _build_infra_dependency_series(
                dep_df, municipio, "escolas_com_rede_wireless"
            )
            if series_dependencia:
                payload["series_dependencia"] = series_dependencia

    return payload


def build_banda_larga_details(municipio):
    payload = _build_infra_details(
        municipio,
        count_column="escolas_com_banda_larga",
        denominator_column="qntd_escolas",
        numerator_label="Escolas com banda larga",
        denominator_label="Total de escolas",
        title="Escolas com internet banda larga",
        unit="escolas",
    )

    if payload is not None:
        dep_df = _safe_load(load_infraestrutura_escolar_por_dependencia_data)
        if not dep_df.empty:
            series_dependencia = _build_infra_dependency_series(
                dep_df, municipio, "escolas_com_banda_larga"
            )
            if series_dependencia:
                payload["series_dependencia"] = series_dependencia

    return payload


def build_educacao_ambiental_details(municipio):
    payload = _build_infra_details(
        municipio,
        count_column="escolas_com_educacao_ambiental",
        denominator_column="qntd_escolas",
        numerator_label="Escolas com educação ambiental",
        denominator_label="Total de escolas",
        title="Escolas que promovem educação ambiental",
        unit="escolas",
    )

    if payload is not None:
        dep_df = _safe_load(load_infraestrutura_escolar_por_dependencia_data)
        if not dep_df.empty:
            series_dependencia = _build_infra_dependency_series(
                dep_df, municipio, "escolas_com_educacao_ambiental"
            )
            if series_dependencia:
                payload["series_dependencia"] = series_dependencia

    return payload


def build_conselho_escolar_details(municipio):
    return _build_infra_details(
        municipio,
        count_column="escolas_publicas_com_orgao_conselho_escolar",
        denominator_column="escolas_publicas_total",
        numerator_label="Escolas públicas com conselho escolar",
        denominator_label="Total de escolas públicas",
        title="Escolas públicas que declararam possuir conselho escolar",
        unit="escolas públicas",
        include_public_dependency=True,
    )


def build_proposta_pedagogica_details(municipio):
    return _build_infra_details(
        municipio,
        count_column="escolas_publicas_com_proposta_pedagogica",
        denominator_column="escolas_publicas_total",
        numerator_label="Escolas públicas com proposta pedagógica",
        denominator_label="Total de escolas públicas",
        title="Escolas públicas com projeto político pedagógico",
        unit="escolas públicas",
        include_public_dependency=True,
    )


def build_salas_climatizadas_details(municipio):
    payload = _build_infra_details(
        municipio,
        count_column="qt_salas_utiliza_climatizadas",
        denominator_column="qt_salas_utilizadas",
        numerator_label="Salas climatizadas",
        denominator_label="Total de salas utilizadas",
        title="Salas de aula climatizadas",
        unit="salas",
    )

    if payload is not None:
        dep_df = _safe_load(load_infraestrutura_escolar_por_dependencia_data)
        if not dep_df.empty:
            series_dependencia = _build_infra_dependency_series(
                dep_df, municipio, "qt_salas_utiliza_climatizadas"
            )
            if series_dependencia:
                payload["series_dependencia"] = series_dependencia

    return payload


def build_salas_acessiveis_details(municipio):
    payload = _build_infra_details(
        municipio,
        count_column="qt_salas_utilizadas_acessiveis",
        denominator_column="qt_salas_utilizadas",
        numerator_label="Salas acessíveis",
        denominator_label="Total de salas utilizadas",
        title="Salas de aula com acessibilidade",
        unit="salas",
    )

    if payload is not None:
        dep_df = _safe_load(load_infraestrutura_escolar_por_dependencia_data)
        if not dep_df.empty:
            series_dependencia = _build_infra_dependency_series(
                dep_df, municipio, "qt_salas_utilizadas_acessiveis"
            )
            if series_dependencia:
                payload["series_dependencia"] = series_dependencia

    return payload


def build_desktop_aluno_details(municipio):
    payload = _build_infra_details(
        municipio,
        count_column="escolas_com_desktop_aluno",
        denominator_column="qntd_escolas",
        numerator_label="Escolas com desktop para aluno",
        denominator_label="Total de escolas",
        title="Escolas com computadores de mesa para alunos",
        unit="escolas",
    )

    if payload is not None:
        dep_df = _safe_load(load_infraestrutura_escolar_por_dependencia_data)
        if not dep_df.empty:
            series_dependencia = _build_infra_dependency_series(
                dep_df, municipio, "escolas_com_desktop_aluno"
            )
            if series_dependencia:
                payload["series_dependencia"] = series_dependencia

    return payload


def build_comp_portatil_aluno_details(municipio):
    payload = _build_infra_details(
        municipio,
        count_column="escolas_com_comp_portatil_aluno",
        denominator_column="qntd_escolas",
        numerator_label="Escolas com computador portátil para aluno",
        denominator_label="Total de escolas",
        title="Escolas com computadores portáteis para alunos",
        unit="escolas",
    )

    if payload is not None:
        dep_df = _safe_load(load_infraestrutura_escolar_por_dependencia_data)
        if not dep_df.empty:
            series_dependencia = _build_infra_dependency_series(
                dep_df, municipio, "escolas_com_comp_portatil_aluno"
            )
            if series_dependencia:
                payload["series_dependencia"] = series_dependencia

    return payload


def build_tablet_aluno_details(municipio):
    payload = _build_infra_details(
        municipio,
        count_column="escolas_com_tablet_aluno",
        denominator_column="qntd_escolas",
        numerator_label="Escolas com tablet para aluno",
        denominator_label="Total de escolas",
        title="Escolas com tablets para alunos",
        unit="escolas",
    )

    if payload is not None:
        dep_df = _safe_load(load_infraestrutura_escolar_por_dependencia_data)
        if not dep_df.empty:
            series_dependencia = _build_infra_dependency_series(
                dep_df, municipio, "escolas_com_tablet_aluno"
            )
            if series_dependencia:
                payload["series_dependencia"] = series_dependencia

    return payload


def _build_censo_percentual_details(
    municipio,
    *,
    loader,
    numerator_column,
    denominator_column,
    title,
    unit,
    numerator_label,
    denominator_label,
):
    df = _safe_load(loader)
    required_columns = {"ano", "municipio", numerator_column, denominator_column}
    if df.empty or not required_columns.issubset(df.columns):
        return None

    dff = df[df["municipio"] == municipio].copy()
    if dff.empty:
        return None

    dff["ano"] = pd.to_numeric(dff["ano"], errors="coerce")
    dff[numerator_column] = pd.to_numeric(dff[numerator_column], errors="coerce")
    dff[denominator_column] = pd.to_numeric(dff[denominator_column], errors="coerce")
    dff = dff.dropna(subset=["ano", numerator_column, denominator_column]).copy()
    if dff.empty:
        return None

    dff["ano"] = dff["ano"].astype(int)
    dff[numerator_column] = dff[numerator_column].clip(lower=0)
    dff[denominator_column] = dff[denominator_column].clip(lower=0)

    total_by_year = (
        dff.groupby("ano", as_index=False)[numerator_column]
        .sum()
        .rename(columns={numerator_column: "valor"})
        .sort_values("ano")
    )
    total_by_year["valor"] = total_by_year["valor"].astype(int)
    series_total = [
        {"ano": int(row["ano"]), "valor": int(row["valor"])}
        for _, row in total_by_year.iterrows()
        if row["valor"] > 0
    ]

    yearly = (
        dff.groupby("ano", as_index=False)
        .agg({numerator_column: "sum", denominator_column: "max"})
        .sort_values("ano")
    )
    series_components = []
    for _, row in yearly.iterrows():
        numerador = row[numerator_column]
        denominador = row[denominator_column]
        if pd.isna(numerador) or pd.isna(denominador) or denominador <= 0:
            continue
        numerador = int(numerador)
        denominador = int(denominador)
        series_components.append(
            {
                "ano": int(row["ano"]),
                "numerador": numerador,
                "denominador": denominador,
                "percentual": round((numerador / denominador) * 100, 1),
            }
        )

    if not series_total or not series_components:
        return None

    return {
        "title": title,
        "subtitle": f"Total de pessoas na condição e total de {unit} no município.",
        "unit": unit,
        "calculation": {
            "numerator_label": numerator_label,
            "denominator_label": denominator_label,
        },
        "series_total": series_total,
        "series_components": series_components,
    }


def build_alfabetizacao_pop_15_mais_details(municipio):
    return _build_censo_percentual_details(
        municipio,
        loader=load_censo_populacao_alfabetizacao_data,
        numerator_column="alfabetizadas_15_mais",
        denominator_column="total_15_mais",
        title="Pessoas de 15 anos ou mais alfabetizadas",
        unit="pessoas",
        numerator_label="Pessoas de 15 anos ou mais alfabetizadas",
        denominator_label="População de 15 anos ou mais",
    )


def build_ensino_medio_ou_basica_completa_pop_15_17_details(municipio):
    return _build_censo_percentual_details(
        municipio,
        loader=load_censo_populacao_ensino_medio_15_17_data,
        numerator_column="populacao_15_17_ensino_medio_ou_basica_completa",
        denominator_column="populacao_15_17_total",
        title="População de 15 a 17 anos com ensino médio ou educação básica completa",
        unit="pessoas",
        numerator_label="População de 15 a 17 anos com ensino médio ou educação básica completa",
        denominator_label="População de 15 a 17 anos",
    )


def build_ensino_fundamental_ou_completo_pop_6_14_details(municipio):
    return _build_censo_percentual_details(
        municipio,
        loader=load_censo_populacao_ensino_fundamental_6_14_data,
        numerator_column="populacao_6_14_ensino_fundamental_ou_completo",
        denominator_column="populacao_6_14_total",
        title="População de 6 a 14 anos no ensino fundamental ou com fundamental completo",
        unit="pessoas",
        numerator_label="População de 6 a 14 anos no ensino fundamental ou com fundamental completo",
        denominator_label="População de 6 a 14 anos",
    )


def build_fundamental_concluido_18_mais_details(municipio):
    return _build_censo_percentual_details(
        municipio,
        loader=load_censo_populacao_ensino_fundamental_concluido_18_mais_data,
        numerator_column="populacao_18_mais_ensino_fundamental_concluido",
        denominator_column="populacao_18_mais_total",
        title="População de 18 anos ou mais com ensino fundamental concluído",
        unit="pessoas",
        numerator_label="População de 18 anos ou mais com ensino fundamental concluído",
        denominator_label="População de 18 anos ou mais",
    )


def build_fundamental_concluido_15_29_details(municipio):
    return _build_censo_percentual_details(
        municipio,
        loader=load_censo_populacao_ensino_fundamental_concluido_15_29_data,
        numerator_column="populacao_15_29_ensino_fundamental_concluido",
        denominator_column="populacao_15_29_total",
        title="População de 15 a 29 anos com ensino fundamental concluído",
        unit="pessoas",
        numerator_label="População de 15 a 29 anos com ensino fundamental concluído",
        denominator_label="População de 15 a 29 anos",
    )


def build_fundamental_concluido_15_mais_details(municipio):
    return _build_censo_percentual_details(
        municipio,
        loader=load_censo_populacao_ensino_fundamental_concluido_15_mais_data,
        numerator_column="populacao_15_mais_ensino_fundamental_concluido",
        denominator_column="populacao_15_mais_total",
        title="População de 15 anos ou mais com ensino fundamental concluído",
        unit="pessoas",
        numerator_label="População de 15 anos ou mais com ensino fundamental concluído",
        denominator_label="População de 15 anos ou mais",
    )


def build_medio_concluido_18_mais_details(municipio):
    return _build_censo_percentual_details(
        municipio,
        loader=load_censo_populacao_ensino_medio_concluido_18_mais_data,
        numerator_column="populacao_18_mais_ensino_medio_concluido",
        denominator_column="populacao_18_mais_total",
        title="População de 18 anos ou mais com ensino médio concluído",
        unit="pessoas",
        numerator_label="População de 18 anos ou mais com ensino médio concluído",
        denominator_label="População de 18 anos ou mais",
    )


def build_medio_concluido_18_29_details(municipio):
    return _build_censo_percentual_details(
        municipio,
        loader=load_censo_populacao_ensino_medio_concluido_18_29_data,
        numerator_column="populacao_18_29_ensino_medio_concluido",
        denominator_column="populacao_18_29_total",
        title="População de 18 a 29 anos com ensino médio concluído",
        unit="pessoas",
        numerator_label="População de 18 a 29 anos com ensino médio concluído",
        denominator_label="População de 18 a 29 anos",
    )


def build_escolaridade_media_18_29_details(municipio):
    df = _safe_load(load_censo_populacao_escolaridade_media_18_29_data)
    required_columns = {"ano", "municipio", "escolaridade_media_18_29"}
    if df.empty or not required_columns.issubset(df.columns):
        return None

    dff = df[df["municipio"] == municipio].copy()
    if dff.empty:
        return None

    dff["ano"] = pd.to_numeric(dff["ano"], errors="coerce")
    dff["escolaridade_media_18_29"] = pd.to_numeric(
        dff["escolaridade_media_18_29"], errors="coerce"
    )
    dff = dff.dropna(subset=["ano", "escolaridade_media_18_29"]).copy()
    if dff.empty:
        return None

    dff["ano"] = dff["ano"].astype(int)
    dff["escolaridade_media_18_29"] = dff["escolaridade_media_18_29"].clip(lower=0)

    total_by_year = (
        dff.groupby("ano", as_index=False)["escolaridade_media_18_29"]
        .mean()
        .rename(columns={"escolaridade_media_18_29": "valor"})
        .sort_values("ano")
    )
    total_by_year["valor"] = total_by_year["valor"].astype(float)
    series_total = [
        {"ano": int(row["ano"]), "valor": float(row["valor"])}
        for _, row in total_by_year.iterrows()
        if row["valor"] is not None
    ]

    if not series_total:
        return None

    return {
        "title": "Escolaridade média da população de 18 a 29 anos",
        "subtitle": "Média de anos de estudo da população de 18 a 29 anos no município.",
        "unit": "anos",
        "series_total": series_total,
    }


def _build_adequacao_docente_details(municipio, *, etapa, title):
    df = _safe_load(load_adequacao_docente_data)
    required_columns = {
        "ano",
        "municipio",
        "dependencia",
        "etapa",
        "percentual_adequacao",
    }
    if df.empty or not required_columns.issubset(df.columns):
        return None

    dff = df[(df["municipio"] == municipio) & (df["etapa"] == etapa)].copy()
    if dff.empty:
        return None

    dff["dependencia"] = (
        dff["dependencia"]
        .astype(str)
        .str.lower()
        .str.strip()
        .replace({"pÃºblica": "publica", "pública": "publica"})
    )

    dff["ano"] = pd.to_numeric(dff["ano"], errors="coerce")
    dff["percentual_adequacao"] = pd.to_numeric(
        dff["percentual_adequacao"], errors="coerce"
    )
    dff = dff.dropna(subset=["ano", "percentual_adequacao"]).copy()
    if dff.empty:
        return None

    dff["ano"] = dff["ano"].astype(int)
    dff["percentual_adequacao"] = dff["percentual_adequacao"].clip(lower=0)

    total_df = dff[dff["dependencia"] == "total"].copy()
    if total_df.empty:
        return None

    total_by_year = (
        total_df.groupby("ano", as_index=False)["percentual_adequacao"]
        .mean()
        .rename(columns={"percentual_adequacao": "valor"})
        .sort_values("ano")
    )
    series_total = [
        {"ano": int(row["ano"]), "valor": round(float(row["valor"]), 1)}
        for _, row in total_by_year.iterrows()
        if row["valor"] > 0
    ]

    if not series_total:
        return None

    dependency_order = ["federal", "estadual", "municipal", "privada"]
    dependency_df = dff[dff["dependencia"].isin(dependency_order)].copy()
    series_dependencia = []
    if not dependency_df.empty:
        dependency_by_year = (
            dependency_df.groupby(["ano", "dependencia"], as_index=False)[
                "percentual_adequacao"
            ]
            .mean()
            .sort_values(["ano", "dependencia"])
        )
        pivot = dependency_by_year.pivot(
            index="ano", columns="dependencia", values="percentual_adequacao"
        ).reset_index()
        for _, row in pivot.iterrows():
            entry = {"ano": int(row["ano"])}
            for dependency in dependency_order:
                if dependency in pivot.columns and pd.notna(row[dependency]):
                    entry[dependency] = round(float(row[dependency]), 1)
            if len(entry) > 1:
                series_dependencia.append(entry)

    payload = {
        "title": title,
        "subtitle": "Historico do percentual de docentes com formacao adequada no municipio, com abertura por dependencia administrativa quando disponivel.",
        "unit": "%",
        "dependency_unit": "%",
        "dependency_value_type": "percent",
        "series_total": series_total,
    }

    if series_dependencia:
        payload["series_dependencia"] = series_dependencia

    return payload


def build_adequacao_ai_details(municipio):
    return _build_adequacao_docente_details(
        municipio,
        etapa="anos_iniciais",
        title="Docentes com formacao adequada nos anos iniciais",
    )


def build_adequacao_af_details(municipio):
    return _build_adequacao_docente_details(
        municipio,
        etapa="anos_finais",
        title="Docentes com formacao adequada nos anos finais",
    )


def build_adequacao_em_details(municipio):
    return _build_adequacao_docente_details(
        municipio,
        etapa="ensino_medio",
        title="Docentes com formacao adequada no ensino medio",
    )


def build_pos_graduacao_details(municipio):
    df = _safe_load(load_docentes_pos_graduacao_data)
    required_columns = {
        "ano",
        "municipio",
        "percentual_pos_graduacao",
        "docentes_pos_graduacao",
        "total_docentes",
    }
    if df.empty or not required_columns.issubset(df.columns):
        return None

    dff = df[df["municipio"] == municipio].copy()
    if dff.empty:
        return None

    numeric_columns = [
        "ano",
        "percentual_pos_graduacao",
        "docentes_pos_graduacao",
        "total_docentes",
    ]
    for column in numeric_columns:
        dff[column] = pd.to_numeric(dff[column], errors="coerce")

    dff = dff.dropna(
        subset=[
            "ano",
            "percentual_pos_graduacao",
            "docentes_pos_graduacao",
            "total_docentes",
        ]
    ).copy()
    if dff.empty:
        return None

    dff["ano"] = dff["ano"].astype(int)
    dff["percentual_pos_graduacao"] = dff["percentual_pos_graduacao"].clip(lower=0)
    dff["docentes_pos_graduacao"] = dff["docentes_pos_graduacao"].clip(lower=0)
    dff["total_docentes"] = dff["total_docentes"].clip(lower=0)

    yearly = (
        dff.groupby("ano", as_index=False)
        .agg(
            {
                "percentual_pos_graduacao": "mean",
                "docentes_pos_graduacao": "sum",
                "total_docentes": "sum",
            }
        )
        .sort_values("ano")
    )

    series_total = [
        {
            "ano": int(row["ano"]),
            "valor": round(float(row["percentual_pos_graduacao"]), 1),
        }
        for _, row in yearly.iterrows()
        if row["percentual_pos_graduacao"] > 0
    ]

    series_components = []
    for _, row in yearly.iterrows():
        numerador = row["docentes_pos_graduacao"]
        denominador = row["total_docentes"]
        if pd.isna(numerador) or pd.isna(denominador) or denominador <= 0:
            continue
        series_components.append(
            {
                "ano": int(row["ano"]),
                "numerador": int(numerador),
                "denominador": int(denominador),
                "percentual": round(float(row["percentual_pos_graduacao"]), 1),
            }
        )

    if not series_total or not series_components:
        return None

    return {
        "title": "Docentes da educacao basica com pos-graduacao",
        "subtitle": "Percentual de docentes da educacao basica com especializacao, mestrado ou doutorado no municipio.",
        "unit": "%",
        "calculation": {
            "numerator_label": "Docentes com pos-graduacao",
            "denominator_label": "Total de docentes",
        },
        "series_total": series_total,
        "series_components": series_components,
    }


def build_temporarios_details(municipio):
    df = _safe_load(load_docentes_temporarios_data)
    required_columns = {
        "ano",
        "municipio",
        "dependencia",
        "percentual_temporarios",
        "docentes_temporarios",
        "total_docentes",
    }
    if df.empty or not required_columns.issubset(df.columns):
        return None

    dff = df[df["municipio"] == municipio].copy()
    if dff.empty:
        return None

    allowed_dependencies = ["publica", "federal", "estadual", "municipal"]
    dff["dependencia"] = (
        dff["dependencia"]
        .astype(str)
        .str.lower()
        .str.strip()
        .replace({"pÃºblica": "publica"})
    )
    dff = dff[dff["dependencia"].isin(allowed_dependencies)].copy()
    if dff.empty:
        return None

    numeric_columns = [
        "ano",
        "percentual_temporarios",
        "docentes_temporarios",
        "total_docentes",
    ]
    for column in numeric_columns:
        dff[column] = pd.to_numeric(dff[column], errors="coerce")

    dff = dff.dropna(
        subset=[
            "ano",
            "dependencia",
            "percentual_temporarios",
            "docentes_temporarios",
            "total_docentes",
        ]
    ).copy()
    if dff.empty:
        return None

    dff["ano"] = dff["ano"].astype(int)
    dff["percentual_temporarios"] = dff["percentual_temporarios"].clip(lower=0)
    dff["docentes_temporarios"] = dff["docentes_temporarios"].clip(lower=0)
    dff["total_docentes"] = dff["total_docentes"].clip(lower=0)

    public_df = dff[dff["dependencia"] == "publica"].copy()
    if public_df.empty:
        return None

    yearly_public = (
        public_df.groupby("ano", as_index=False)
        .agg(
            {
                "percentual_temporarios": "mean",
                "docentes_temporarios": "sum",
                "total_docentes": "sum",
            }
        )
        .sort_values("ano")
    )

    series_total = [
        {
            "ano": int(row["ano"]),
            "valor": round(float(row["percentual_temporarios"]), 1),
        }
        for _, row in yearly_public.iterrows()
        if row["percentual_temporarios"] > 0
    ]

    series_components = []
    for _, row in yearly_public.iterrows():
        numerador = row["docentes_temporarios"]
        denominador = row["total_docentes"]
        if pd.isna(numerador) or pd.isna(denominador) or denominador <= 0:
            continue
        series_components.append(
            {
                "ano": int(row["ano"]),
                "numerador": int(numerador),
                "denominador": int(denominador),
                "percentual": round(float(row["percentual_temporarios"]), 1),
            }
        )

    dependency_df = (
        dff.groupby(["ano", "dependencia"], as_index=False)["docentes_temporarios"]
        .sum()
        .sort_values(["ano", "dependencia"])
    )
    series_dependencia = []
    for ano, group in dependency_df.groupby("ano", sort=True):
        entry = {"ano": int(ano)}
        for dependency in allowed_dependencies:
            dep_rows = group[group["dependencia"] == dependency]
            if dep_rows.empty:
                continue
            value = dep_rows["docentes_temporarios"].sum()
            if pd.isna(value):
                continue
            entry[dependency] = int(value)
        if any(key != "ano" and value > 0 for key, value in entry.items()):
            series_dependencia.append(entry)

    if not series_total or not series_components:
        return None

    payload = {
        "title": "Docentes da rede publica com vinculo temporario",
        "subtitle": "Percentual de docentes da rede publica com contrato temporario no municipio.",
        "unit": "%",
        "calculation": {
            "numerator_label": "Docentes temporarios da rede publica",
            "denominator_label": "Total de docentes da rede publica",
        },
        "series_total": series_total,
        "series_components": series_components,
    }

    if series_dependencia:
        payload["series_dependencia"] = series_dependencia

    return payload


def build_razao_escolaridade_racial_18_29_details(municipio):
    df = _safe_load(load_censo_populacao_escolaridade_media_18_29_racial_data)
    required_columns = {
        "ano",
        "municipio",
        "escolaridade_media_negros_18_29",
        "escolaridade_media_nao_negros_18_29",
        "razao_percentual_escolaridade_negros_nao_negros_18_29",
    }
    if df.empty or not required_columns.issubset(df.columns):
        return None

    dff = df[df["municipio"] == municipio].copy()
    if dff.empty:
        return None

    dff["ano"] = pd.to_numeric(dff["ano"], errors="coerce")
    dff["escolaridade_media_negros_18_29"] = pd.to_numeric(
        dff["escolaridade_media_negros_18_29"], errors="coerce"
    )
    dff["escolaridade_media_nao_negros_18_29"] = pd.to_numeric(
        dff["escolaridade_media_nao_negros_18_29"], errors="coerce"
    )
    dff["razao_percentual_escolaridade_negros_nao_negros_18_29"] = pd.to_numeric(
        dff["razao_percentual_escolaridade_negros_nao_negros_18_29"],
        errors="coerce",
    )
    dff = dff.dropna(
        subset=[
            "ano",
            "escolaridade_media_negros_18_29",
            "escolaridade_media_nao_negros_18_29",
            "razao_percentual_escolaridade_negros_nao_negros_18_29",
        ]
    ).copy()
    if dff.empty:
        return None

    dff["ano"] = dff["ano"].astype(int)
    dff["escolaridade_media_negros_18_29"] = dff["escolaridade_media_negros_18_29"].clip(lower=0)
    dff["escolaridade_media_nao_negros_18_29"] = dff["escolaridade_media_nao_negros_18_29"].clip(lower=0)

    total_by_year = (
        dff.groupby("ano", as_index=False)["razao_percentual_escolaridade_negros_nao_negros_18_29"]
        .mean()
        .rename(
            columns={
                "razao_percentual_escolaridade_negros_nao_negros_18_29": "valor"
            }
        )
        .sort_values("ano")
    )
    total_by_year["valor"] = total_by_year["valor"].astype(float)
    series_total = [
        {"ano": int(row["ano"]), "valor": int(row["valor"])}
        for _, row in total_by_year.iterrows()
        if row["valor"] > 0
    ]

    yearly = (
        dff.groupby("ano", as_index=False)
        .agg(
            {
                "escolaridade_media_negros_18_29": "mean",
                "escolaridade_media_nao_negros_18_29": "mean",
            }
        )
        .sort_values("ano")
    )
    series_components = []
    for _, row in yearly.iterrows():
        numerador = row["escolaridade_media_negros_18_29"]
        denominador = row["escolaridade_media_nao_negros_18_29"]
        if pd.isna(numerador) or pd.isna(denominador) or denominador <= 0:
            continue
        numerador = float(numerador)
        denominador = float(denominador)
        percentual = round((numerador / denominador) * 100, 1)
        series_components.append(
            {
                "ano": int(row["ano"]),
                "numerador": numerador,
                "denominador": denominador,
                "percentual": percentual,
            }
        )

    if not series_total or not series_components:
        return None

    return {
        "title": "Razão entre escolaridade média de negros e não negros de 18 a 29 anos",
        "subtitle": "Razão percentual entre a média de anos de estudo da população negra e da não negra de 18 a 29 anos no município.",
        "unit": "razão (%)",
        "calculation": {
            "numerator_label": "Média de anos de estudo da população negra de 18 a 29 anos",
            "denominator_label": "Média de anos de estudo da população não negra de 18 a 29 anos",
        },
        "series_total": series_total,
        "series_components": series_components,
    }


def _load_municipio_id_map():
    from src.data.repository import get_local_postgres_engine
    query = "SELECT id_municipio::text, municipio FROM municipios WHERE municipio IS NOT NULL"
    df = profiled_aggregate_query_call(
        "indicator_details.municipality_id_map",
        lambda: pd.read_sql_query(query, get_local_postgres_engine()),
        metadata={
            "datasetId": "municipality_id_map",
            "backend": "postgres_local",
            "broadQuery": True,
            "municipalityFilter": "local_after_query",
        },
    )
    if df.empty:
        return {}
    return {nome.strip(): id_mun for nome, id_mun in zip(df["municipio"], df["id_municipio"])}


def build_privadas_conveniadas_shared(municipio):
    df = _safe_load(load_matriculas_privadas_conveniadas)
    if df.empty or "id_municipio" not in df.columns:
        return None

    id_map = _load_municipio_id_map()
    mun_id = id_map.get(municipio.strip())
    if mun_id is None:
        return None

    dff = df[df["id_municipio"].astype(str) == mun_id].copy()
    if dff.empty:
        return None

    colunas_num = [
        "matriculas_conveniadas_total", "matriculas_resp_municipio",
        "matriculas_resp_estado", "matriculas_resp_estado_municipio",
        "matriculas_resp_municipal_total",
    ]
    for col in colunas_num:
        dff[col] = pd.to_numeric(dff[col], errors="coerce")

    ultimo_ano = int(dff["ano"].max())

    total_eb = dff[
        (dff["secao_sinopse"] == "educacao_basica")
        & (dff["categoria_escola_privada"] == "total")
    ]
    resumo = None
    if not total_eb.empty:
        row = total_eb.iloc[0]
        resumo = {
            "total_conveniado": _int_or_none(row["matriculas_conveniadas_total"]),
            "municipio": _int_or_none(row["matriculas_resp_municipio"]),
            "estado_municipio": _int_or_none(row["matriculas_resp_estado_municipio"]),
            "municipal_total": _int_or_none(row["matriculas_resp_municipal_total"]),
        }

    por_secao_raw = dff[dff["categoria_escola_privada"] == "total"]
    if por_secao_raw.empty:
        por_secao = []
    else:
        ordem_secao = [
            "educacao_basica", "educacao_infantil", "creche", "pre_escola",
            "ensino_fundamental", "anos_iniciais", "anos_finais",
            "ensino_medio", "educacao_profissional", "eja",
            "educacao_especial", "classes_comuns", "classes_exclusivas",
        ]
        por_secao_raw = por_secao_raw.copy()
        por_secao_raw["_ordem"] = por_secao_raw["secao_sinopse"].map(
            {s: i for i, s in enumerate(ordem_secao)}
        )
        por_secao_raw = por_secao_raw.dropna(subset=["_ordem"]).sort_values("_ordem")
        por_secao = [
            {
                "secao": row["secao_sinopse"],
                "total_conveniado": _int_or_none(row["matriculas_conveniadas_total"]),
                "municipio": _int_or_none(row["matriculas_resp_municipio"]),
                "estado_municipio": _int_or_none(row["matriculas_resp_estado_municipio"]),
                "municipal_total": _int_or_none(row["matriculas_resp_municipal_total"]),
            }
            for _, row in por_secao_raw.iterrows()
        ]

    por_categoria_raw = dff[dff["secao_sinopse"] == "educacao_basica"]
    if por_categoria_raw.empty:
        por_categoria = []
    else:
        ordem_categoria = ["total", "particular", "comunitaria", "confessional", "filantropica"]
        por_categoria_raw = por_categoria_raw.copy()
        por_categoria_raw["_ordem"] = por_categoria_raw["categoria_escola_privada"].map(
            {c: i for i, c in enumerate(ordem_categoria)}
        )
        por_categoria_raw = por_categoria_raw.dropna(subset=["_ordem"]).sort_values("_ordem")
        por_categoria = [
            {
                "categoria": row["categoria_escola_privada"],
                "total_conveniado": _int_or_none(row["matriculas_conveniadas_total"]),
                "municipal_total": _int_or_none(row["matriculas_resp_municipal_total"]),
            }
            for _, row in por_categoria_raw.iterrows()
        ]

    fonte_eb = dff[
        (dff["secao_sinopse"] == "educacao_basica")
        & (dff["categoria_escola_privada"] == "total")
    ]
    if not fonte_eb.empty:
        fonte = str(fonte_eb.iloc[0]["fonte"])
    else:
        fonte = "INEP - Sinopse Estatística do Censo Escolar 2025, tabela 1.3"

    return {
        "ultimo_ano": ultimo_ano,
        "resumo": resumo,
        "por_secao": por_secao,
        "por_categoria": por_categoria,
        "fonte": fonte,
        "disponivel_desde": 2025,
    }


def _int_or_none(val):
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    try:
        v = int(val)
        return v if v >= 0 else None
    except (ValueError, TypeError):
        return None


DETAIL_BUILDERS = {
    "creche": build_creche_details,
    "pre_escola": build_pre_escola_details,
    "basico_6_17": build_basico_6_17_details,
    "basico_15_17": build_basico_15_17_details,
    "basico_integral": build_basico_integral_details,
    "escolas_integral": build_escolas_integral_details,
    "aee": build_aee_details,
    "medio_tecnico": build_medio_tecnico_details,
    "medio_tecnico_articulado_percentual": build_medio_tecnico_articulado_percentual_details,
    "medio_tecnico_total": build_medio_tecnico_total_details,
    "medio_tecnico_participacao_publica": build_medio_tecnico_participacao_publica_details,
    "subsequente_expansao": build_subsequente_expansao_details,
    "eja_integrada_educacao_profissional": build_eja_integrada_educacao_profissional_details,
    "eja_integrada_educacao_profissional_percentual": build_eja_integrada_educacao_profissional_percentual_details,
    "internet": build_internet_details,
    "internet_alunos": build_internet_alunos_details,
    "internet_aprendizagem": build_internet_aprendizagem_details,
    "internet_comunidade": build_internet_comunidade_details,
    "acesso_internet_computador": build_acesso_internet_computador_details,
    "acesso_internet_disp_pessoais": build_acesso_internet_disp_pessoais_details,
    "rede_local": build_rede_local_details,
    "rede_wireless": build_rede_wireless_details,
    "banda_larga": build_banda_larga_details,
    "educacao_ambiental": build_educacao_ambiental_details,
    "conselho_escolar": build_conselho_escolar_details,
    "proposta_pedagogica": build_proposta_pedagogica_details,
    "salas_climatizadas": build_salas_climatizadas_details,
    "salas_acessiveis": build_salas_acessiveis_details,
    "desktop_aluno": build_desktop_aluno_details,
    "comp_portatil_aluno": build_comp_portatil_aluno_details,
    "tablet_aluno": build_tablet_aluno_details,
    "alfabetizacao_pop_15_mais": build_alfabetizacao_pop_15_mais_details,
    "ensino_medio_ou_basica_completa_pop_15_17": build_ensino_medio_ou_basica_completa_pop_15_17_details,
    "ensino_fundamental_ou_completo_pop_6_14": build_ensino_fundamental_ou_completo_pop_6_14_details,
    "fundamental_concluido_18_mais": build_fundamental_concluido_18_mais_details,
    "fundamental_concluido_15_29": build_fundamental_concluido_15_29_details,
    "fundamental_concluido_15_mais": build_fundamental_concluido_15_mais_details,
    "medio_concluido_18_mais": build_medio_concluido_18_mais_details,
    "medio_concluido_18_29": build_medio_concluido_18_29_details,
    "escolaridade_media_18_29": build_escolaridade_media_18_29_details,
    "razao_escolaridade_racial_18_29": build_razao_escolaridade_racial_18_29_details,
    "adequacao_ai": build_adequacao_ai_details,
    "adequacao_af": build_adequacao_af_details,
    "adequacao_em": build_adequacao_em_details,
    "pos_graduacao": build_pos_graduacao_details,
    "temporarios": build_temporarios_details,
}


def build_indicator_details(municipio):
    details = {}
    for indicator_key, builder in DETAIL_BUILDERS.items():
        try:
            data = builder(municipio)
            if data is not None and isinstance(data, dict) and data:
                details[indicator_key] = data
        except Exception as exc:
            print(
                f"Aviso: erro ao construir dados complementares para "
                f"'{indicator_key}' ({municipio}): {exc}"
            )
            continue

    privadas = build_privadas_conveniadas_shared(municipio)
    if privadas is not None:
        details["_shared"] = {"privadas_conveniadas": privadas}

    return details
