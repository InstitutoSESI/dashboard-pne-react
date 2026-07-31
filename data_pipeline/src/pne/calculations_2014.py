"""Regras de neg?cio puras, sem depend?ncia da aplica??o Dash."""

import math

import time

from functools import lru_cache

import pandas as pd

from src.data_loader import load_adequacao_docente_data, load_atendimento_educacional_especializado_data, load_basico_15_17_data, load_basico_6_17_data, load_basico_integral_data, load_censo_populacao_alfabetizacao_data, load_censo_populacao_ensino_fundamental_6_14_data, load_censo_populacao_ensino_medio_15_17_data, load_censo_populacao_escolaridade_media_18_29_data, load_censo_populacao_escolaridade_media_18_29_racial_data, load_docentes_pos_graduacao_data, load_rendimento_professores_data, load_eja_integrada_educacao_profissional_data, load_ept_nivel_medio_data, load_escolas_integral_data, get_data_cache_ttl_seconds, load_pne_2014_2024_metricas_data, load_pne_data, load_pre_escola_data, load_saeb_ideb_data, load_taxa_alfabetizacao_data

from src.pne.common import GOAL_AT_LEAST, _build_eja_integrada_percentual_result, _build_ratio_result, _build_result, _build_value_result, _empty_result, _prepare_yearly_series, _safe_load, _select_reference_rows
from src.pne_2014_child_literacy import SOURCE_ID as ALFABETIZACAO_SOURCE_ID
from src.pne_2014_child_literacy import SOURCE_LABEL as ALFABETIZACAO_SOURCE_LABEL

TARGET_START_YEAR = 2014

TARGET_END_YEAR = 2024

META_CRECHE = 50.0

META_PRE_ESCOLA = 100.0

META_BASICO_6_17 = 100.0

META_BASICO_15_17 = 85.0

META_BASICO_INTEGRAL = 25.0

META_ESCOLAS_PUBLICAS_INTEGRAL = 50.0

META_EJA_INTEGRADA_EPT = 25.0

META_EPT_PARTICIPACAO_PUBLICA = 50.0

META_AEE = 80.0

META_ALFABETIZACAO = 100.0

META_ALFABETIZACAO_POPULACAO = 100.0

META_ENSINO_MEDIO_OU_BASICA_COMPLETA_POPULACAO = 85.0

META_ENSINO_FUNDAMENTAL_OU_COMPLETO_POPULACAO = 100.0

META_ESCOLARIDADE_MEDIA_18_29 = 12.0

META_RAZAO_ESCOLARIDADE_RACIAL_18_29 = 100.0

META_IDEB = {
    "anos_iniciais": 6.0,
    "anos_finais": 5.5,
    "ensino_medio": 5.2,
}

META_ADEQUACAO = 100.0

META_POS_GRADUACAO = 50.0

META_RENDIMENTO_MAGISTERIO = 100.0

IDEB_RESULT_GROUPS = {
    "ideb_anos_iniciais": ("anos_iniciais", META_IDEB["anos_iniciais"]),
    "ideb_anos_finais": ("anos_finais", META_IDEB["anos_finais"]),
    "ideb_ensino_medio": ("ensino_medio", META_IDEB["ensino_medio"]),
}

ADEQUACAO_RESULT_GROUPS = {
    "adequacao_ai": ("anos_iniciais", META_ADEQUACAO),
    "adequacao_af": ("anos_finais", META_ADEQUACAO),
    "adequacao_em": ("ensino_medio", META_ADEQUACAO),
}

BATCHED_RESULT_KEYS = set(IDEB_RESULT_GROUPS) | set(ADEQUACAO_RESULT_GROUPS)

def _results_cache_bucket():
    ttl_seconds = get_data_cache_ttl_seconds()
    if ttl_seconds <= 0:
        return None
    return int(time.time() // ttl_seconds)

def _load_precomputed_metric_frame(cache_bucket):
    return _safe_load(load_pne_2014_2024_metricas_data)

def _precomputed_metric_frame():
    cache_bucket = _results_cache_bucket()
    if cache_bucket is None:
        return _safe_load(load_pne_2014_2024_metricas_data)
    return _load_precomputed_metric_frame(cache_bucket)

def _build_precomputed_result(
    municipio,
    indicador,
    *,
    meta,
    meta_label="Meta de referência",
    direction=GOAL_AT_LEAST,
    target_start_year=TARGET_START_YEAR,
    target_end_year=TARGET_END_YEAR,
    tracks_goal=True,
):
    df = _precomputed_metric_frame()
    if df.empty or "municipio" not in df.columns or "indicador" not in df.columns:
        return None

    if "ano" not in df.columns or "valor" not in df.columns:
        return None

    dff = df[(df["municipio"] == municipio) & (df["indicador"] == indicador)].copy()
    if dff.empty:
        return None

    dff["ano"] = pd.to_numeric(dff["ano"], errors="coerce")
    dff["valor"] = pd.to_numeric(dff["valor"], errors="coerce")
    dff = dff.dropna(subset=["ano", "valor"])
    if dff.empty:
        return None

    return _build_result(
        dff[["ano", "valor"]],
        meta,
        direction=direction,
        meta_label=meta_label,
        target_start_year=target_start_year,
        target_end_year=target_end_year,
        tracks_goal=tracks_goal,
    )

def _build_grouped_precomputed_fallback_results(
    loader,
    municipio,
    *,
    result_groups,
    precomputed_meta_label,
    fallback_meta_label,
    group_column,
    value_column,
    filters=None,
    use_precomputed=True,
    target_start_year,
    target_end_year,
    direction=GOAL_AT_LEAST,
):
    results = {}
    pending_groups = {}

    for result_key, (group_value, meta) in result_groups.items():
        precomputed = None
        if use_precomputed:
            precomputed = _build_precomputed_result(
                municipio,
                result_key,
                meta=meta,
                meta_label=precomputed_meta_label,
                direction=direction,
                target_start_year=target_start_year,
                target_end_year=target_end_year,
            )
        if precomputed is not None:
            results[result_key] = precomputed
            continue

        results[result_key] = _empty_result(
            meta,
            direction=direction,
            meta_label=fallback_meta_label,
        )
        pending_groups[result_key] = (group_value, meta)

    if not pending_groups:
        return results

    df = _safe_load(loader)
    if (
        df.empty
        or "municipio" not in df.columns
        or "ano" not in df.columns
        or group_column not in df.columns
        or value_column not in df.columns
    ):
        return results

    dff = df[df["municipio"] == municipio].copy()
    if filters:
        for column, value in filters.items():
            if column not in dff.columns:
                return results
            dff = dff[dff[column] == value]
    if dff.empty:
        return results

    dff = dff.loc[:, ["ano", group_column, value_column]].copy()
    dff["ano"] = pd.to_numeric(dff["ano"], errors="coerce")
    dff[value_column] = pd.to_numeric(dff[value_column], errors="coerce")
    dff = dff.dropna(subset=["ano", value_column]).copy()
    if dff.empty:
        return results

    dff["ano"] = dff["ano"].astype(int)
    yearly = (
        dff.groupby([group_column, "ano"], as_index=False)[value_column]
        .mean()
        .rename(columns={value_column: "valor"})
    )

    for result_key, (group_value, meta) in pending_groups.items():
        yearly_slice = yearly[yearly[group_column] == group_value][["ano", "valor"]]
        if yearly_slice.empty:
            continue
        results[result_key] = _build_result(
            yearly_slice,
            meta,
            direction=direction,
            meta_label=fallback_meta_label,
            target_start_year=target_start_year,
            target_end_year=target_end_year,
        )

    return results

def _calculate_ideb_results(municipio):
    return _build_grouped_precomputed_fallback_results(
        load_saeb_ideb_data,
        municipio,
        result_groups=IDEB_RESULT_GROUPS,
        precomputed_meta_label="Meta PNE 2024",
        fallback_meta_label="Meta PNE 2024",
        group_column="categoria",
        value_column="ideb",
        filters={"dependencia": "publica"},
        target_start_year=2013,
        target_end_year=2023,
    )

def _calculate_adequacao_results(municipio):
    return _build_grouped_precomputed_fallback_results(
        load_adequacao_docente_data,
        municipio,
        result_groups=ADEQUACAO_RESULT_GROUPS,
        precomputed_meta_label="Meta PNE 2024",
        fallback_meta_label="Meta PNE 2024",
        group_column="etapa",
        value_column="percentual_adequacao",
        filters={"dependencia": "total"},
        use_precomputed=False,
        target_start_year=TARGET_START_YEAR,
        target_end_year=TARGET_END_YEAR,
    )

def _calc_creche(municipio):
    precomputed = _build_precomputed_result(
        municipio,
        "creche",
        meta=META_CRECHE,
        meta_label="Meta PNE 2024",
    )
    if precomputed is not None:
        return precomputed

    return _build_ratio_result(
        load_pne_data,
        municipio,
        numerator="mat_infantil_creche",
        denominator="pop_0_3",
        meta=META_CRECHE,
        meta_label="Meta PNE 2024",
        den_agg="max",
        target_start_year=TARGET_START_YEAR,
        target_end_year=TARGET_END_YEAR,
    )

def _calc_pre_escola(municipio):
    precomputed = _build_precomputed_result(
        municipio,
        "pre_escola",
        meta=META_PRE_ESCOLA,
        meta_label="Meta PNE 2024",
    )
    if precomputed is not None:
        return precomputed

    return _build_ratio_result(
        load_pre_escola_data,
        municipio,
        numerator="mat_infantil_pre",
        denominator="pop_4_5",
        meta=META_PRE_ESCOLA,
        meta_label="Meta PNE 2024",
        den_agg="max",
        target_start_year=TARGET_START_YEAR,
        target_end_year=TARGET_END_YEAR,
    )

def _calc_basico_6_17(municipio):
    precomputed = _build_precomputed_result(
        municipio,
        "basico_6_17",
        meta=META_BASICO_6_17,
        meta_label="Meta PNE 2024",
    )
    if precomputed is not None:
        return precomputed

    return _build_ratio_result(
        load_basico_6_17_data,
        municipio,
        numerator="mat_basico_6_17",
        denominator="pop_6_17",
        meta=META_BASICO_6_17,
        meta_label="Meta PNE 2024",
        den_agg="max",
        target_start_year=TARGET_START_YEAR,
        target_end_year=TARGET_END_YEAR,
    )

def _calc_basico_15_17(municipio):
    precomputed = _build_precomputed_result(
        municipio,
        "basico_15_17",
        meta=META_BASICO_15_17,
        meta_label="Meta PNE 2024",
    )
    if precomputed is not None:
        return precomputed

    return _build_ratio_result(
        load_basico_15_17_data,
        municipio,
        numerator="mat_basico_15_17",
        denominator="pop_15_17",
        meta=META_BASICO_15_17,
        meta_label="Meta PNE 2024",
        den_agg="max",
        target_start_year=TARGET_START_YEAR,
        target_end_year=TARGET_END_YEAR,
    )

def _calc_basico_integral(municipio):
    precomputed = _build_precomputed_result(
        municipio,
        "basico_integral",
        meta=META_BASICO_INTEGRAL,
        meta_label="Meta PNE 2024",
    )
    if precomputed is not None:
        return precomputed

    return _build_ratio_result(
        load_basico_integral_data,
        municipio,
        numerator="mat_basico_integral",
        denominator="mat_basico",
        meta=META_BASICO_INTEGRAL,
        meta_label="Meta PNE 2024",
        filters={"dependencia": "publica"},
        target_start_year=TARGET_START_YEAR,
        target_end_year=TARGET_END_YEAR,
    )

def _calc_escolas_integral(municipio):
    precomputed = _build_precomputed_result(
        municipio,
        "escolas_integral",
        meta=META_ESCOLAS_PUBLICAS_INTEGRAL,
        meta_label="Meta PNE 2024",
    )
    if precomputed is not None:
        return precomputed

    return _build_ratio_result(
        load_escolas_integral_data,
        municipio,
        numerator="escolas_publicas_com_integral",
        denominator="escolas_publicas_total",
        meta=META_ESCOLAS_PUBLICAS_INTEGRAL,
        meta_label="Meta PNE 2024",
        target_start_year=TARGET_START_YEAR,
        target_end_year=TARGET_END_YEAR,
    )

def _calc_eja_integrada_educacao_profissional(municipio):
    return _build_eja_integrada_percentual_result(
        load_eja_integrada_educacao_profissional_data,
        municipio,
        meta=META_EJA_INTEGRADA_EPT,
        meta_label="Meta PNE 2024",
        target_start_year=2014,
        target_end_year=2024,
    )

def _calc_medio_tecnico(municipio):
    result = _build_series_change_result(
        load_ept_nivel_medio_data,
        municipio,
        value_column="mat_ept_nivel_medio_publica",
        meta_label="Visualização informativa",
        target_start_year=2013,
        target_end_year=2024,
    )
    if result.get("available"):
        result["base_year"] = result["start_year"]
    result["tracks_goal"] = False
    result["meta"] = None
    return result

def _calc_medio_tecnico_total(municipio):
    return _ept_total_result(municipio)

def _calc_medio_tecnico_participacao_publica(municipio):
    df = _safe_load(load_ept_nivel_medio_data)
    if (
        df.empty
        or "municipio" not in df.columns
        or "mat_ept_nivel_medio_total" not in df.columns
        or "mat_ept_nivel_medio_publica" not in df.columns
    ):
        return _empty_result(
            META_EPT_PARTICIPACAO_PUBLICA,
            meta_label="Meta PNE 2024",
        )

    dff = df[df["municipio"] == municipio].copy()
    if dff.empty:
        return _empty_result(
            META_EPT_PARTICIPACAO_PUBLICA,
            meta_label="Meta PNE 2024",
        )

    yearly = (
        dff.groupby("ano", as_index=False)[
            ["mat_ept_nivel_medio_total", "mat_ept_nivel_medio_publica"]
        ]
        .sum()
        .copy()
    )
    yearly["mat_ept_nivel_medio_total"] = pd.to_numeric(
        yearly["mat_ept_nivel_medio_total"], errors="coerce"
    )
    yearly["mat_ept_nivel_medio_publica"] = pd.to_numeric(
        yearly["mat_ept_nivel_medio_publica"], errors="coerce"
    )
    yearly = (
        yearly.dropna(
            subset=["mat_ept_nivel_medio_total", "mat_ept_nivel_medio_publica"]
        )
        .loc[lambda frame: frame["ano"] <= TARGET_END_YEAR]
        .sort_values("ano")
        .reset_index(drop=True)
    )
    if yearly.empty:
        return _empty_result(
            META_EPT_PARTICIPACAO_PUBLICA,
            meta_label="Meta PNE 2024",
        )

    base_rows = yearly[
        (yearly["ano"] >= 2013) & (yearly["mat_ept_nivel_medio_publica"] > 0)
    ]
    if base_rows.empty:
        base_rows = yearly[yearly["mat_ept_nivel_medio_publica"] > 0]
    if base_rows.empty:
        return _empty_result(
            META_EPT_PARTICIPACAO_PUBLICA,
            meta_label="Meta PNE 2024",
        )

    base_row = base_rows.head(1).iloc[0]
    base_total = float(base_row["mat_ept_nivel_medio_total"])
    base_publica = float(base_row["mat_ept_nivel_medio_publica"])
    if base_total <= 0:
        return _empty_result(
            META_EPT_PARTICIPACAO_PUBLICA,
            meta_label="Meta PNE 2024",
        )

    base_year = int(base_row["ano"])
    yearly = yearly[yearly["ano"] >= base_year].copy().sort_values("ano")
    yearly["mat_ept_nivel_medio_privada"] = (
        yearly["mat_ept_nivel_medio_total"] - yearly["mat_ept_nivel_medio_publica"]
    )
    yearly["exp_publica"] = yearly["mat_ept_nivel_medio_publica"].diff().fillna(0.0)
    yearly["exp_privada"] = yearly["mat_ept_nivel_medio_privada"].diff().fillna(0.0)
    yearly["exp_publica_positiva"] = yearly["exp_publica"].clip(lower=0.0)
    yearly["exp_privada_positiva"] = yearly["exp_privada"].clip(lower=0.0)
    yearly["exp_publica_acumulada"] = yearly["exp_publica_positiva"].cumsum()
    yearly["exp_privada_acumulada"] = yearly["exp_privada_positiva"].cumsum()
    yearly["exp_total_acumulada"] = (
        yearly["exp_publica_acumulada"] + yearly["exp_privada_acumulada"]
    )
    yearly["valor"] = 0.0
    expansion_mask = yearly["exp_total_acumulada"] > 0
    yearly.loc[expansion_mask, "valor"] = (
        yearly.loc[expansion_mask, "exp_publica_acumulada"]
        .div(yearly.loc[expansion_mask, "exp_total_acumulada"])
        .mul(100.0)
    )
    yearly = yearly[yearly["ano"] > base_year].copy()
    yearly = yearly.replace([math.inf, -math.inf], pd.NA).dropna(subset=["valor"])
    if yearly.empty:
        return _empty_result(
            META_EPT_PARTICIPACAO_PUBLICA,
            meta_label="Meta PNE 2024",
        )

    result = _build_result(
        yearly[["ano", "valor"]],
        META_EPT_PARTICIPACAO_PUBLICA,
        meta_label="Meta PNE 2024",
        target_start_year=base_year + 1,
        target_end_year=2024,
    )
    result["base_year"] = base_year
    result["base_total"] = base_total
    result["base_publica"] = base_publica
    return result

def _calc_aee(municipio):
    precomputed = _build_precomputed_result(
        municipio,
        "aee",
        meta=META_AEE,
        meta_label="Meta definida 2026-2036",
    )
    if precomputed is not None:
        return precomputed

    return _build_ratio_result(
        load_atendimento_educacional_especializado_data,
        municipio,
        numerator="quantidade_aee",
        denominator="total_turmas_educacao_especial",
        meta=META_AEE,
        meta_label="Meta definida 2026-2036",
        target_start_year=TARGET_START_YEAR,
        target_end_year=TARGET_END_YEAR,
    )

def _calc_alfabetizacao(municipio):
    empty = _empty_result(
        None,
        meta_label="Resultado observado",
        tracks_goal=False,
    )
    empty["atingida"] = None
    df = _safe_load(
        lambda: load_taxa_alfabetizacao_data(cycle="pne_2014_2024")
    )
    required = {"ano", "municipio", "rede", "taxa_alfabetizacao"}
    if df.empty or not required.issubset(df.columns):
        return empty

    dff = df[
        (df["municipio"] == municipio)
        & (df["rede"] == "municipal")
    ].copy()
    dff["ano"] = pd.to_numeric(dff["ano"], errors="coerce")
    dff = dff[
        (dff["ano"] >= TARGET_START_YEAR)
        & (dff["ano"] <= TARGET_END_YEAR)
    ]
    if dff.duplicated(subset=["ano", "rede"], keep=False).any():
        print(
            "Erro de validação do indicador alfabetizacao: "
            f"chave ano × rede duplicada para {municipio}."
        )
        return empty

    dff["valor"] = pd.to_numeric(
        dff["taxa_alfabetizacao"],
        errors="coerce",
    )
    yearly = dff.dropna(subset=["ano", "valor"])[["ano", "valor"]]
    if yearly.empty:
        return empty

    result = _build_result(
        yearly,
        None,
        meta_label="Resultado observado",
        target_start_year=TARGET_START_YEAR,
        target_end_year=TARGET_END_YEAR,
        tracks_goal=False,
    )
    result.update(
        {
            "source": ALFABETIZACAO_SOURCE_LABEL,
            "source_id": ALFABETIZACAO_SOURCE_ID,
            "network": "municipal",
            "origin_files": sorted(
                {
                    str(value)
                    for value in dff.get("arquivo_origem", pd.Series(dtype="object"))
                    if pd.notna(value)
                }
            ),
            "updated_at": next(
                (
                    str(value)
                    for value in reversed(
                        dff.get(
                            "data_atualizacao",
                            pd.Series(dtype="object"),
                        ).dropna().tolist()
                    )
                ),
                None,
            ),
        }
    )
    return result

def _calc_alfabetizacao_pop_15_mais(municipio):
    precomputed = _build_precomputed_result(
        municipio,
        "alfabetizacao_pop_15_mais",
        meta=META_ALFABETIZACAO_POPULACAO,
        meta_label="Meta PNE 2024",
        target_start_year=2010,
        target_end_year=2022,
    )
    if precomputed is not None:
        return precomputed

    return _build_value_result(
        load_censo_populacao_alfabetizacao_data,
        municipio,
        value_column="taxa_alfabetizacao_15_mais",
        meta=META_ALFABETIZACAO_POPULACAO,
        meta_label="Meta PNE 2024",
        target_start_year=2010,
        target_end_year=2022,
    )

def _calc_escolaridade_media_18_29(municipio):
    precomputed = _build_precomputed_result(
        municipio,
        "escolaridade_media_18_29",
        meta=META_ESCOLARIDADE_MEDIA_18_29,
        meta_label="Meta PNE 2024",
        target_start_year=2022,
        target_end_year=2022,
    )
    if precomputed is not None:
        return precomputed

    return _build_value_result(
        load_censo_populacao_escolaridade_media_18_29_data,
        municipio,
        value_column="escolaridade_media_18_29",
        meta=META_ESCOLARIDADE_MEDIA_18_29,
        meta_label="Meta PNE 2024",
        target_start_year=2022,
        target_end_year=2022,
    )

def _calc_razao_escolaridade_racial_18_29(municipio):
    precomputed = _build_precomputed_result(
        municipio,
        "razao_escolaridade_racial_18_29",
        meta=META_RAZAO_ESCOLARIDADE_RACIAL_18_29,
        meta_label="Meta PNE 2024",
        target_start_year=2022,
        target_end_year=2022,
    )
    if precomputed is not None:
        return precomputed

    return _build_value_result(
        load_censo_populacao_escolaridade_media_18_29_racial_data,
        municipio,
        value_column="razao_percentual_escolaridade_negros_nao_negros_18_29",
        meta=META_RAZAO_ESCOLARIDADE_RACIAL_18_29,
        meta_label="Meta PNE 2024",
        target_start_year=2022,
        target_end_year=2022,
    )

def _calc_ensino_medio_ou_basica_completa_pop_15_17(municipio):
    precomputed = _build_precomputed_result(
        municipio,
        "ensino_medio_ou_basica_completa_pop_15_17",
        meta=META_ENSINO_MEDIO_OU_BASICA_COMPLETA_POPULACAO,
        meta_label="Meta PNE 2024",
        target_start_year=2010,
        target_end_year=2022,
    )
    if precomputed is not None:
        return precomputed

    return _build_value_result(
        load_censo_populacao_ensino_medio_15_17_data,
        municipio,
        value_column="percentual_15_17_ensino_medio_ou_basica_completa",
        meta=META_ENSINO_MEDIO_OU_BASICA_COMPLETA_POPULACAO,
        meta_label="Meta PNE 2024",
        target_start_year=2010,
        target_end_year=2022,
    )

def _calc_ensino_fundamental_ou_completo_pop_6_14(municipio):
    precomputed = _build_precomputed_result(
        municipio,
        "ensino_fundamental_ou_completo_pop_6_14",
        meta=META_ENSINO_FUNDAMENTAL_OU_COMPLETO_POPULACAO,
        meta_label="Meta PNE 2024",
        target_start_year=2010,
        target_end_year=2022,
    )
    if precomputed is not None:
        return precomputed

    result = _build_value_result(
        load_censo_populacao_ensino_fundamental_6_14_data,
        municipio,
        value_column="percentual_6_14_ensino_fundamental_ou_completo",
        meta=META_ENSINO_FUNDAMENTAL_OU_COMPLETO_POPULACAO,
        meta_label="Meta PNE 2024",
        target_start_year=2010,
        target_end_year=2022,
    )
    return result

def _calc_ideb(municipio, etapa_key):
    precomputed = _build_precomputed_result(
        municipio,
        f"ideb_{etapa_key}",
        meta=META_IDEB[etapa_key],
        meta_label="Meta PNE 2024",
        target_start_year=2013,
        target_end_year=2023,
    )
    if precomputed is not None:
        return precomputed

    return _build_value_result(
        load_saeb_ideb_data,
        municipio,
        value_column="ideb",
        meta=META_IDEB[etapa_key],
        meta_label="Meta PNE 2024",
        filters={
            "categoria": etapa_key,
            "dependencia": "publica",
        },
        target_start_year=2013,
        target_end_year=2023,
    )

def _calc_adequacao(municipio, etapa_key):
    precomputed_key = {
        "anos_iniciais": "adequacao_ai",
        "anos_finais": "adequacao_af",
        "ensino_medio": "adequacao_em",
    }[etapa_key]
    precomputed = _build_precomputed_result(
        municipio,
        precomputed_key,
        meta=META_ADEQUACAO,
        meta_label="Meta PNE 2024",
    )
    if precomputed is not None:
        return precomputed

    return _build_value_result(
        load_adequacao_docente_data,
        municipio,
        value_column="percentual_adequacao",
        meta=META_ADEQUACAO,
        meta_label="Meta PNE 2024",
        filters={"etapa": etapa_key, "dependencia": "total"},
        target_start_year=TARGET_START_YEAR,
        target_end_year=TARGET_END_YEAR,
    )

def _calc_pos_graduacao(municipio):
    precomputed = _build_precomputed_result(
        municipio,
        "pos_graduacao",
        meta=META_POS_GRADUACAO,
        meta_label="Meta PNE 2024",
    )
    if precomputed is not None:
        return precomputed

    return _build_value_result(
        load_docentes_pos_graduacao_data,
        municipio,
        value_column="percentual_pos_graduacao",
        meta=META_POS_GRADUACAO,
        meta_label="Meta PNE 2024",
        filters={"dependencia": "total"},
        target_start_year=TARGET_START_YEAR,
        target_end_year=TARGET_END_YEAR,
    )

def _calc_rendimento_magisterio(municipio):
    return _build_value_result(
        load_rendimento_professores_data,
        municipio,
        value_column="razao_percentual_remuneracao_media",
        meta=META_RENDIMENTO_MAGISTERIO,
        meta_label="Meta PNE 2024",
        target_start_year=TARGET_START_YEAR,
        target_end_year=TARGET_END_YEAR,
    )

INDICADORES = {
    "atendimento": {
        "label": "Atendimento Escolar",
        "icon": "🎓",
        "accent": "#4f46e5",
        "items": [
            {
                "key": "creche",
                "label": "População de 0 a 3 anos que frequenta a escola/creche",
                "sub": "",
                "desc": "Percentual da população de 0 a 3 anos que frequenta a escola ou creche.",
                "meta_label": "Meta PNE 2024",
                "compute": _calc_creche,
            },
            {
                "key": "pre_escola",
                "label": "População de 4 a 5 anos que frequenta a escola/creche",
                "sub": "",
                "desc": "Percentual da população de 4 a 5 anos que frequenta a escola ou creche.",
                "meta_label": "Meta PNE 2024",
                "compute": _calc_pre_escola,
            },
            {
                "key": "basico_6_17",
                "label": "População de 6 a 17 anos que frequenta a educação básica",
                "sub": "",
                "desc": "Percentual da população de 6 a 17 anos que frequenta a educação básica.",
                "meta_label": "Meta PNE 2024",
                "compute": _calc_basico_6_17,
            },
            {
                "key": "basico_15_17",
                "label": "População de 15 a 17 anos que frequenta a escola ou já concluiu a educação básica",
                "sub": "",
                "desc": "Percentual da população de 15 a 17 anos que frequenta a escola ou já concluiu a educação básica.",
                "meta_label": "Meta PNE 2024",
                "compute": _calc_basico_15_17,
            },
            {
                "key": "basico_integral",
                "label": "Alunos do público-alvo da ETI em jornada integral na rede pública",
                "sub": "",
                "desc": "Percentual de alunos da educação básica pública que pertencem ao público-alvo da Educação em Tempo Integral (ETI) e estão em jornada de tempo integral.",
                "meta_label": "Meta PNE 2024",
                "compute": _calc_basico_integral,
            },
            {
                "key": "escolas_integral",
                "label": "Escolas públicas com alunos em jornada de tempo integral",
                "sub": "",
                "desc": "Percentual de escolas públicas da educação básica que possuem, pelo menos, 25% dos alunos da educação básica em jornada integral.",
                "meta_label": "Meta PNE 2024",
                "compute": _calc_escolas_integral,
            },
            {
                "key": "eja_integrada_educacao_profissional_percentual",
                "label": "Percentual das matrículas da EJA articuladas à educação profissional",
                "sub": "",
                "desc": "Percentual das matrículas da EJA articuladas à educação profissional no município.",
                "meta_label": "Meta PNE 2024",
                "compute": _calc_eja_integrada_educacao_profissional,
                "tracks_goal": True,
                "value_mode": "percent",
            },
            {
                "key": "medio_tecnico_total",
                "label": "Número absoluto de matrículas em EPT de nível médio",
                "sub": "",
                "desc": "Evolução do número absoluto de matrículas da Educação Profissional e Tecnológica de nível médio no município, entre 2014 e 2024.",
                "meta_label": "Visualização informativa",
                "compute": _calc_medio_tecnico_total,
                "tracks_goal": False,
            },
            {
                "key": "medio_tecnico_participacao_publica",
                "label": "Participação acumulada do segmento público na expansão da EPT de nível médio",
                "sub": "",
                "desc": "Participação acumulada do segmento público nas expansões anuais positivas da Educação Profissional e Tecnológica de nível médio no município, com base na evolução observada até 2024.",
                "meta_label": "Meta PNE 2024",
                "compute": _calc_medio_tecnico_participacao_publica,
            },
            {
                "key": "medio_tecnico",
                "label": "Expansão acumulada da EPT de médio público",
                "sub": "",
                "desc": "Número de matrículas acumuladas da Educação Profissional e Tecnológica de médio público, a partir de 2013.",
                "meta_label": "Visualização informativa",
                "compute": _calc_medio_tecnico,
                "tracks_goal": False,
                "value_mode": "count",
            },
            {
                "key": "aee",
                "label": "Oferta de AEE na educação especial",
                "sub": "",
                "desc": "Participação das turmas ou salas de AEE em relação ao total da educação especial no município.",
                "meta_label": "Meta definida 2026-2036",
                "compute": _calc_aee,
            },
        ],
    },
    "rendimento": {
        "label": "Rendimento Escolar",
        "icon": "📈",
        "accent": "#10b981",
        "items": [
            {
                "key": "alfabetizacao",
                "label": "Crianças alfabetizadas na rede municipal",
                "sub": "",
                "desc": "Percentual de estudantes da rede municipal considerados alfabetizados ao final do 2º ano do ensino fundamental. O indicador utiliza o padrão nacional da Avaliação da Alfabetização e não corresponde exatamente ao critério da Meta 5 do PNE 2014–2024, que previa alfabetização até o final do 3º ano.",
                "meta_label": "Resultado observado",
                "compute": _calc_alfabetizacao,
                "tracks_goal": False,
            },
            {
                "key": "ideb_anos_iniciais",
                "label": "IDEB da rede pública nos anos iniciais do ensino fundamental",
                "sub": "",
                "desc": "Resultado do IDEB da rede pública nos anos iniciais do ensino fundamental.",
                "meta_label": "Meta PNE 2024",
                "value_mode": "index",
                "compute": lambda municipio: _calc_ideb(municipio, "anos_iniciais"),
            },
            {
                "key": "ideb_anos_finais",
                "label": "IDEB da rede pública nos anos finais do ensino fundamental",
                "sub": "",
                "desc": "Resultado do IDEB da rede pública nos anos finais do ensino fundamental.",
                "meta_label": "Meta PNE 2024",
                "value_mode": "index",
                "compute": lambda municipio: _calc_ideb(municipio, "anos_finais"),
            },
            {
                "key": "ideb_ensino_medio",
                "label": "IDEB da rede pública no ensino médio",
                "sub": "",
                "desc": "Resultado do IDEB da rede pública no ensino médio.",
                "meta_label": "Meta PNE 2024",
                "value_mode": "index",
                "compute": lambda municipio: _calc_ideb(municipio, "ensino_medio"),
            },
        ],
    },
    "corpo_docente": {
        "label": "Corpo Docente",
        "icon": "👩‍🏫",
        "accent": "#f59e0b",
        "items": [
            {
                "key": "adequacao_ai",
                "label": "Docentes com formação adequada nos anos iniciais",
                "sub": "",
                "desc": "Percentual de docentes com formação adequada nos anos iniciais do ensino fundamental.",
                "meta_label": "Meta PNE 2024",
                "compute": lambda municipio: _calc_adequacao(
                    municipio, "anos_iniciais"
                ),
            },
            {
                "key": "adequacao_af",
                "label": "Docentes com formação adequada nos anos finais",
                "sub": "",
                "desc": "Percentual de docentes com formação adequada nos anos finais do ensino fundamental.",
                "meta_label": "Meta PNE 2024",
                "compute": lambda municipio: _calc_adequacao(municipio, "anos_finais"),
            },
            {
                "key": "adequacao_em",
                "label": "Docentes com formação adequada no ensino médio",
                "sub": "",
                "desc": "Percentual de docentes com formação adequada no ensino médio.",
                "meta_label": "Meta PNE 2024",
                "compute": lambda municipio: _calc_adequacao(municipio, "ensino_medio"),
            },
            {
                "key": "pos_graduacao",
                "label": "Docentes da educação básica com pós-graduação",
                "sub": "",
                "desc": "Percentual de docentes da educação básica com especialização, mestrado ou doutorado.",
                "meta_label": "Meta PNE 2024",
                "compute": _calc_pos_graduacao,
            },
            {
                "key": "rendimento_magisterio",
                "label": "Rendimento do magistério em relação a outros profissionais com nível superior",
                "sub": "",
                "desc": "Relação percentual entre o rendimento bruto médio mensal dos profissionais do magistério da educação básica, com nível superior completo, e o rendimento bruto médio mensal dos demais profissionais assalariados, com nível superior completo.",
                "meta_label": "Meta PNE 2024",
                "compute": _calc_rendimento_magisterio,
            },
        ],
    },
    "escolaridade_populacao": {
        "label": "Escolaridade da População",
        "icon": "👥",
        "accent": "#2563eb",
        "items": [
            {
                "key": "alfabetizacao_pop_15_mais",
                "label": "População de 15 anos ou mais alfabetizada",
                "sub": "",
                "desc": "Percentual da população de 15 anos ou mais de idade alfabetizada no município, com base nos Censos Demográficos.",
                "meta_label": "Meta PNE 2024",
                "compute": _calc_alfabetizacao_pop_15_mais,
            },
            {
                "key": "ensino_medio_ou_basica_completa_pop_15_17",
                "label": "População de 15 a 17 anos que frequenta o ensino médio ou concluiu a educação básica",
                "sub": "",
                "desc": "Percentual da população de 15 a 17 anos que frequenta o ensino médio ou possui educação básica completa, com base nos Censos Demográficos.",
                "meta_label": "Meta PNE 2024",
                "compute": _calc_ensino_medio_ou_basica_completa_pop_15_17,
            },
            {
                "key": "ensino_fundamental_ou_completo_pop_6_14",
                "label": "População de 6 a 14 anos que frequenta ou concluiu o ensino fundamental",
                "sub": "",
                "desc": "Percentual de pessoas de 6 a 14 anos que frequentam ou que já concluíram o ensino fundamental, com base nos Censos Demográficos.",
                "meta_label": "Meta PNE 2024",
                "compute": _calc_ensino_fundamental_ou_completo_pop_6_14,
            },
            {
                "key": "escolaridade_media_18_29",
                "label": "Escolaridade média da população de 18 a 29 anos",
                "sub": "",
                "desc": "Escolaridade média, em anos de estudo, da população de 18 a 29 anos de idade no município.",
                "meta_label": "Meta PNE 2024",
                "value_mode": "years",
                "compute": _calc_escolaridade_media_18_29,
            },
            {
                "key": "razao_escolaridade_racial_18_29",
                "label": "Razão entre escolaridade média de negros e não negros de 18 a 29 anos",
                "sub": "",
                "desc": "Razão percentual entre a escolaridade média de negros e não negros na faixa etária de 18 a 29 anos no município.",
                "meta_label": "Meta PNE 2024",
                "compute": _calc_razao_escolaridade_racial_18_29,
            },
        ],
    },
}

CATEGORY_ORDER = list(INDICADORES.keys())

def _build_series_change_result(
    loader,
    municipio,
    *,
    value_column,
    filters=None,
    value_agg="sum",
    meta_label=None,
    target_start_year=TARGET_START_YEAR,
    target_end_year=TARGET_END_YEAR,
):
    df = _safe_load(loader)
    if df.empty or "municipio" not in df.columns or value_column not in df.columns:
        return {"available": False, "tracks_goal": False}

    dff = df[df["municipio"] == municipio].copy()
    if filters:
        for column, value in filters.items():
            if column not in dff.columns:
                return {"available": False, "tracks_goal": False}
            if isinstance(value, (list, tuple, set, frozenset)):
                dff = dff[dff[column].isin(value)]
            else:
                dff = dff[dff[column] == value]

    if dff.empty:
        return {"available": False, "tracks_goal": False}

    yearly = dff.groupby("ano", as_index=False).agg({value_column: value_agg}).copy()
    yearly[value_column] = pd.to_numeric(yearly[value_column], errors="coerce")
    yearly = yearly.dropna(subset=[value_column]).rename(
        columns={value_column: "valor"}
    )
    series = _prepare_yearly_series(yearly[["ano", "valor"]])
    start_row, end_row = _select_reference_rows(
        series,
        target_start_year=target_start_year,
        target_end_year=target_end_year,
    )
    if start_row is None or end_row is None:
        return {"available": False, "tracks_goal": False}

    start_value = float(start_row["valor"])
    end_value = float(end_row["valor"])
    raw_delta = end_value - start_value
    percent_change = (
        None if start_value == 0 else ((end_value / start_value) - 1.0) * 100.0
    )

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
        "start_year": int(start_row["ano"]),
        "end_year": int(end_row["ano"]),
        "start_value": start_value,
        "end_value": end_value,
        "raw_delta": raw_delta,
        "percent_change": percent_change,
        "series": series_points,
        "meta": None,
        "meta_label": meta_label,
        "tracks_goal": False,
    }

def _ept_total_result(municipio):
    return _build_series_change_result(
        load_ept_nivel_medio_data,
        municipio,
        value_column="mat_ept_nivel_medio_total",
        target_start_year=2014,
        target_end_year=2024,
    )

def _calculate_results_cached(municipio, cache_bucket):
    results = {}
    for category in INDICADORES.values():
        for item in category["items"]:
            if item["key"] in BATCHED_RESULT_KEYS:
                continue
            try:
                results[item["key"]] = item["compute"](municipio)
            except Exception as exc:
                print(f"Erro ao calcular indicador {item['key']}: {exc}")
                results[item["key"]] = _empty_result(
                    meta=0,
                    meta_label=item.get("meta_label", "Meta de referência"),
                    tracks_goal=item.get("tracks_goal", True),
                )

    for label, calculator, groups in (
        ("ideb", _calculate_ideb_results, IDEB_RESULT_GROUPS),
        ("adequacao", _calculate_adequacao_results, ADEQUACAO_RESULT_GROUPS),
    ):
        try:
            results.update(calculator(municipio))
        except Exception as exc:
            print(f"Erro ao calcular grupo {label}: {exc}")
            for result_key, (_, meta) in groups.items():
                results[result_key] = _empty_result(
                    meta=meta,
                    meta_label="Meta PNE 2024",
                )

    return results

def _calculate_results(municipio):
    cache_bucket = _results_cache_bucket()
    if cache_bucket is None:
        return _calculate_results_cached.__wrapped__(municipio, None)

    cached = _calculate_results_cached(municipio, cache_bucket)
    return {key: value.copy() for key, value in cached.items()}

def _calculate_results_for_indicators_cached(municipio, indicator_keys, cache_bucket):
    """Calcula somente os indicadores solicitados na exportação rápida.

    IDEB e adequação continuam agrupados porque cada consulta compartilha a fonte
    entre várias chaves; o resultado é filtrado antes de ser devolvido.
    """

    selected_keys = set(indicator_keys)
    results = {}
    for category in INDICADORES.values():
        for item in category["items"]:
            if item["key"] not in selected_keys or item["key"] in BATCHED_RESULT_KEYS:
                continue
            try:
                results[item["key"]] = item["compute"](municipio)
            except Exception as exc:
                print(f"Erro ao calcular indicador {item['key']}: {exc}")
                results[item["key"]] = _empty_result(
                    meta=0,
                    meta_label=item.get("meta_label", "Meta de referência"),
                    tracks_goal=item.get("tracks_goal", True),
                )

    for label, calculator, groups in (
        ("ideb", _calculate_ideb_results, IDEB_RESULT_GROUPS),
        ("adequacao", _calculate_adequacao_results, ADEQUACAO_RESULT_GROUPS),
    ):
        group_keys = set(groups)
        if not selected_keys & group_keys:
            continue
        try:
            results.update(calculator(municipio))
        except Exception as exc:
            print(f"Erro ao calcular grupo {label}: {exc}")
            for result_key, (_, meta) in groups.items():
                if result_key in selected_keys:
                    results[result_key] = _empty_result(
                        meta=meta,
                        meta_label="Meta PNE 2024",
                    )

    return {key: value for key, value in results.items() if key in selected_keys}

def _calculate_results_for_indicators(municipio, indicator_keys):
    normalized_keys = tuple(dict.fromkeys(indicator_keys))
    cache_bucket = _results_cache_bucket()
    if cache_bucket is None:
        return _calculate_results_for_indicators_cached.__wrapped__(
            municipio, normalized_keys, None
        )
    cached = _calculate_results_for_indicators_cached(
        municipio, normalized_keys, cache_bucket
    )
    return {key: value.copy() for key, value in cached.items()}
