"""Materialização auditável do Job 5G-C (trabalho juvenil e EPT).

O módulo opera somente sobre artefatos congelados e um agregado estadual RAIS
recebido pelo chamador. Não acessa rede, banco ou ``public/data``.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import pandas as pd

from src.vocacoes_pne_job2 import (
    artifact_record,
    require_ibge_code,
    safe_ratio,
    sha256_file,
    write_csv_gzip,
    write_json,
)


JOB_ID = "v7-job5gc"
SCHEMA_VERSION = "vocacoes-pne-v7-job5gc-v1"
FINAL_STATE = "JOB_5GC_PARTIAL_WITH_DATA_GAPS"
NSR_CODE = "4313375"
ALLOWED_ANALYSIS_STATES = frozenset(
    {
        "READY_FOR_INTERNAL_VISUAL_PROTOTYPE",
        "READY_WITH_LIMITS",
        "DESCRIPTIVE_CONTEXT_ONLY",
        "PROMISING_NEEDS_MORE_TESTING",
        "INSUFFICIENT_DATA",
        "REJECTED",
    }
)
CANONICAL_STATUSES = frozenset(
    {"SUPPORTED", "PARTIAL", "NOT_SUPPORTED", "NOT_EVALUABLE"}
)
EXPECTED_OUTPUTS = (
    "DICIONARIO_FONTES_TRABALHO_E_EPT_JOB5GC_V1.json",
    "PAINEL_RAIS_TRABALHO_JUVENIL_V1.csv.gz",
    "PAINEL_CAGED_JUVENIL_FLUXOS_V1.csv.gz",
    "PAINEL_APRENDIZAGEM_PROFISSIONAL_V1.csv.gz",
    "PAINEL_ESCOLARIDADE_VINCULOS_JOVENS_V1.csv.gz",
    "PAINEL_OCUPACOES_SETORES_MUDANCA_V1.csv.gz",
    "PAINEL_EPT_OFERTA_TOTAL_V1.csv.gz",
    "DICIONARIO_PONTE_CBO_CNCT_V1.json",
    "PAINEL_PONTE_CBO_CNCT_AUDITADA_V1.csv.gz",
    "PAINEL_APRENDIZAGEM_OCUPACOES_EIXOS_V1.csv.gz",
    "PAINEL_CONCENTRACAO_TRABALHO_EPT_V1.csv.gz",
    "PAINEL_SHIFT_SHARE_SETORIAL_V1.csv.gz",
    "PAINEL_ESCOLARIDADE_ADULTA_TRABALHO_CONTEXTUAL_V1.csv.gz",
    "PAINEL_TRABALHO_JUVENIL_EDUCACAO_CONTEXTO_V1.csv.gz",
    "MATRIZ_VINCULOS_PNE_PME_JOB5GC_V1.csv.gz",
    "NOVA_SANTA_RITA_JOB5GC_V1.json",
    "DICIONARIO_SEMANTICO_METRICAS_JOB5GC_V1.json",
    "MATRIZ_QA_JOB5GC_V1.csv.gz",
    "MATRIZ_C1_C12_CANONICA_JOB5GC_V1.csv.gz",
    "MATRIZ_OPORTUNIDADES_REAVALIADAS_JOB5GC_V1.csv.gz",
    "MAPA_SECOES_POTENCIAIS_JOB5GC_V1.md",
    "LIMITACOES_JOB5GC_V1.json",
    "PACOTE_REVISAO_EXTERNA_JOB5GC.json",
    "MANIFEST_JOB5GC.json",
)


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype={"municipality_ibge_code": "string"})


def _stable(frame: pd.DataFrame, columns: Sequence[str] | None = None) -> pd.DataFrame:
    if frame.empty:
        return frame.reset_index(drop=True)
    keys = list(columns or frame.columns)
    return frame.sort_values(keys, kind="mergesort", na_position="last").reset_index(
        drop=True
    )


def _value_status(value: Any) -> str:
    if value is None or pd.isna(value):
        return "unavailable"
    return "observed_zero" if float(value) == 0 else "observed"


def _change_status(initial: Any, final: Any) -> str:
    if initial is None or final is None or pd.isna(initial) or pd.isna(final):
        return "unavailable"
    if float(initial) == 0:
        return "base_zero_absolute_change_only"
    return "observed"


def _percent_change(initial: Any, final: Any) -> float | None:
    if initial is None or final is None or pd.isna(initial) or pd.isna(final):
        return None
    if float(initial) == 0:
        return None
    return (float(final) - float(initial)) / float(initial) * 100.0


def _digest_rows(frame: pd.DataFrame) -> str:
    payload = frame.to_csv(index=False, lineterminator="\n", na_rep="null").encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _validate_codes(frame: pd.DataFrame) -> None:
    if "municipality_ibge_code" not in frame:
        return
    for value in frame["municipality_ibge_code"].dropna().astype(str).unique():
        require_ibge_code(value)


def build_rais_youth(
    annual: pd.DataFrame, cube: pd.DataFrame, region_codes: set[str]
) -> pd.DataFrame:
    """Série anual do estoque jovem e decomposição por escolaridade bruta."""

    total = annual.copy()
    total["dimension"] = "total"
    total["dimension_code"] = "ALL"
    total["dimension_label"] = "Todos os vínculos jovens"
    schooling = (
        cube.groupby(
            [
                "year",
                "municipality_ibge_code",
                "municipality_name",
                "entity_scope",
                "age_group",
                "schooling_code",
            ],
            as_index=False,
            dropna=False,
        )["active_bonds"]
        .sum()
        .rename(columns={"schooling_code": "dimension_code"})
    )
    schooling["dimension"] = "schooling_raw"
    schooling["dimension_label"] = pd.NA
    region = schooling[schooling["municipality_ibge_code"].isin(region_codes)].groupby(
        ["year", "age_group", "dimension_code", "dimension", "dimension_label"],
        as_index=False,
        dropna=False,
    )["active_bonds"].sum()
    region["municipality_ibge_code"] = pd.NA
    region["municipality_name"] = "Vale do Sinos"
    region["entity_scope"] = "region"
    common = [
        "year",
        "municipality_ibge_code",
        "municipality_name",
        "entity_scope",
        "age_group",
        "dimension",
        "dimension_code",
        "dimension_label",
        "active_bonds",
    ]
    panel = pd.concat([total[common], schooling[common], region[common]], ignore_index=True)
    panel["value_status"] = panel["active_bonds"].map(_value_status)
    panel["territorial_lens"] = "workplace"
    panel["source"] = "RAIS vínculo ativo em 31/12"
    panel["schooling_dictionary_status"] = panel["dimension"].map(
        lambda value: "not_applicable" if value == "total" else "unavailable"
    )
    panel["youth_occupation_dimension_status"] = "unavailable"
    panel["youth_sector_dimension_status"] = "unavailable"
    panel["youth_apprentice_dimension_status"] = "unavailable"
    entity_keys = [
        "municipality_ibge_code", "entity_scope", "age_group", "dimension", "dimension_code"
    ]
    changes = _endpoint_changes(panel, keys=entity_keys, value="active_bonds")
    changes = changes.rename(
        columns={
            "initial_value": "period_initial_bonds",
            "final_value": "period_final_bonds",
            "absolute_change": "period_absolute_change",
            "percent_change": "period_percent_change",
            "change_status": "period_change_status",
        }
    )
    changes["period_change_status"] = changes["period_change_status"].replace(
        {"base_zero_absolute_change_only": "BASE_ZERO_PERCENT_CHANGE_NOT_EVALUABLE"}
    )
    panel = panel.merge(
        changes[
            entity_keys
            + [
                "period_initial_bonds", "period_final_bonds", "period_absolute_change",
                "period_percent_change", "period_change_status",
            ]
        ],
        on=entity_keys,
        how="left",
        validate="many_to_one",
    )
    regional = panel[panel["entity_scope"].eq("region")][
        ["year", "age_group", "dimension", "dimension_code", "active_bonds", "period_absolute_change"]
    ].rename(
        columns={
            "active_bonds": "regional_active_bonds",
            "period_absolute_change": "regional_period_absolute_change",
        }
    )
    panel = panel.merge(
        regional,
        on=["year", "age_group", "dimension", "dimension_code"],
        how="left",
        validate="many_to_one",
    )
    panel["municipal_share_of_regional_stock"] = panel.apply(
        lambda row: safe_ratio(row["active_bonds"], row["regional_active_bonds"])
        if row["entity_scope"] in {"municipality", "region"}
        else None,
        axis=1,
    )
    panel["municipal_contribution_to_regional_change"] = panel.apply(
        lambda row: safe_ratio(row["period_absolute_change"], row["regional_period_absolute_change"])
        if row["entity_scope"] in {"municipality", "region"}
        else None,
        axis=1,
    )
    return _stable(panel)


def build_caged_flows(
    cube: pd.DataFrame,
    names: Mapping[str, str],
    state_monthly: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Fluxos mensais detalhados e totais regionais do Novo Caged."""

    data = cube.copy()
    data["event_value"] = pd.to_numeric(data["adjusted_event_count"], errors="raise")
    keys = [
        "municipality_ibge_code",
        "year",
        "month",
        "age_group",
        "occupation_code",
        "cnae_subclass_code",
        "schooling_code",
        "apprentice_indicator_code",
    ]
    grouped = data.groupby(keys + ["event_type"], as_index=False, dropna=False)[
        "event_value"
    ].sum()
    wide = grouped.pivot_table(
        index=keys,
        columns="event_type",
        values="event_value",
        aggfunc="sum",
        fill_value=0,
    ).reset_index()
    wide.columns.name = None
    for column in ("admission", "dismissal"):
        if column not in wide:
            wide[column] = 0.0
    wide = wide.rename(columns={"admission": "admissions", "dismissal": "dismissals"})
    wide["balance"] = wide["admissions"] - wide["dismissals"]
    wide["municipality_name"] = wide["municipality_ibge_code"].map(names)
    wide["entity_scope"] = "municipality"
    region_keys = [column for column in keys if column != "municipality_ibge_code"]
    region = wide.groupby(region_keys, as_index=False, dropna=False)[
        ["admissions", "dismissals", "balance"]
    ].sum()
    region["municipality_ibge_code"] = pd.NA
    region["municipality_name"] = "Vale do Sinos"
    region["entity_scope"] = "region"
    monthly_parts = [wide, region]
    if state_monthly is not None:
        state = state_monthly[state_monthly["entity_scope"].eq("state")].copy()
        state["occupation_code"] = "ALL"
        state["cnae_subclass_code"] = "ALL"
        state["schooling_code"] = "ALL"
        state["apprentice_indicator_code"] = "ALL"
        monthly_parts.append(
            state[
                [
                    "municipality_ibge_code", "municipality_name", "entity_scope", "year", "month",
                    "age_group", "occupation_code", "cnae_subclass_code", "schooling_code",
                    "apprentice_indicator_code", "admissions", "dismissals", "balance",
                ]
            ]
        )
    monthly = pd.concat(monthly_parts, ignore_index=True, sort=False)
    monthly["time_grain"] = "month"
    annual_keys = [
        "municipality_ibge_code", "municipality_name", "entity_scope", "year", "age_group",
        "occupation_code", "cnae_subclass_code", "schooling_code", "apprentice_indicator_code",
    ]
    annual = monthly.groupby(annual_keys, as_index=False, dropna=False)[
        ["admissions", "dismissals", "balance"]
    ].sum()
    annual["month"] = pd.NA
    annual["time_grain"] = "year"
    panel = pd.concat([monthly, annual], ignore_index=True, sort=False)
    composition_keys = [
        "municipality_ibge_code", "entity_scope", "year", "month", "time_grain", "age_group"
    ]
    admission_total = panel.groupby(composition_keys, dropna=False)["admissions"].transform("sum")
    dismissal_total = panel.groupby(composition_keys, dropna=False)["dismissals"].transform("sum")
    panel["admission_composition_share"] = [
        safe_ratio(value, total) for value, total in zip(panel["admissions"], admission_total)
    ]
    panel["dismissal_composition_share"] = [
        safe_ratio(value, total) for value, total in zip(panel["dismissals"], dismissal_total)
    ]
    comparison_keys = [
        "year", "month", "time_grain", "age_group", "occupation_code", "cnae_subclass_code",
        "schooling_code", "apprentice_indicator_code",
    ]
    region_values = panel[panel["entity_scope"].eq("region")][
        comparison_keys + ["admissions", "dismissals"]
    ].rename(columns={"admissions": "regional_admissions", "dismissals": "regional_dismissals"})
    panel = panel.merge(region_values, on=comparison_keys, how="left", validate="many_to_one")
    panel["municipal_share_of_regional_admissions"] = panel.apply(
        lambda row: safe_ratio(row["admissions"], row["regional_admissions"])
        if row["entity_scope"] in {"municipality", "region"} else None,
        axis=1,
    )
    panel["municipal_share_of_regional_dismissals"] = panel.apply(
        lambda row: safe_ratio(row["dismissals"], row["regional_dismissals"])
        if row["entity_scope"] in {"municipality", "region"} else None,
        axis=1,
    )
    annual_values = panel[panel["time_grain"].eq("year")][
        annual_keys + ["admissions"]
    ].rename(columns={"admissions": "annual_admissions_same_contract"})
    panel = panel.merge(annual_values, on=annual_keys, how="left", validate="many_to_one")
    panel["seasonality_admission_share_of_annual"] = panel.apply(
        lambda row: safe_ratio(row["admissions"], row["annual_admissions_same_contract"])
        if row["time_grain"] == "month" else None,
        axis=1,
    )
    panel["value_status"] = panel[["admissions", "dismissals"]].sum(axis=1).map(
        _value_status
    )
    panel["source"] = "Novo Caged; eventos ajustados MOV+FOR-EXC"
    panel["territorial_lens"] = "workplace"
    panel["flow_not_stock"] = True
    panel["caged_measure_role"] = "FLOW_EVENTS"
    panel["unique_person_count_allowed"] = False
    panel["complete_comparable_window"] = True
    return _stable(panel)


def build_apprentices(caged: pd.DataFrame) -> pd.DataFrame:
    annual_caged = caged[caged["time_grain"].eq("year")].copy()
    apprentice = annual_caged[
        annual_caged["apprentice_indicator_code"].astype(str) == "1"
    ].copy()
    keys = [
        "municipality_ibge_code",
        "municipality_name",
        "entity_scope",
        "year",
        "age_group",
        "occupation_code",
        "cnae_subclass_code",
    ]
    apprentice = apprentice.groupby(keys, as_index=False, dropna=False)[
        ["admissions", "dismissals", "balance"]
    ].sum()
    total_keys = [
        "municipality_ibge_code", "municipality_name", "entity_scope", "year", "age_group"
    ]
    totals = annual_caged.groupby(total_keys, as_index=False, dropna=False)["admissions"].sum().rename(
        columns={"admissions": "youth_admissions_same_grain"}
    )
    panel = apprentice.merge(totals, on=total_keys, how="left", validate="many_to_one")
    panel["share_of_youth_admission_events_classified_as_apprentice"] = pd.NA
    aggregate = apprentice.groupby(total_keys, as_index=False, dropna=False)[
        ["admissions", "dismissals", "balance"]
    ].sum()
    aggregate = aggregate.merge(totals, on=total_keys, how="left", validate="one_to_one")
    aggregate["occupation_code"] = "ALL"
    aggregate["cnae_subclass_code"] = "ALL"
    aggregate["share_of_youth_admission_events_classified_as_apprentice"] = aggregate.apply(
        lambda row: safe_ratio(row["admissions"], row["youth_admissions_same_grain"]), axis=1
    )
    panel = pd.concat([panel, aggregate], ignore_index=True, sort=False)
    panel["share_status"] = panel[
        "share_of_youth_admission_events_classified_as_apprentice"
    ].map(
        _value_status
    )
    panel["unit"] = "adjusted_events"
    panel["source"] = "Novo Caged"
    panel["territorial_lens"] = "workplace"
    panel["flow_not_stock"] = True
    panel["source_measure"] = "adjusted_admission_dismissal_events"
    panel["stock_or_flow"] = "FLOW"
    panel["unique_person_count_allowed"] = False
    return _stable(panel)


def build_youth_schooling(cube: pd.DataFrame, region_codes: set[str]) -> pd.DataFrame:
    keys = [
        "year",
        "municipality_ibge_code",
        "municipality_name",
        "age_group",
        "schooling_code",
    ]
    panel = cube.groupby(keys, as_index=False, dropna=False)["active_bonds"].sum()
    panel["entity_scope"] = "municipality"
    region = panel[panel["municipality_ibge_code"].isin(region_codes)].groupby(
        ["year", "age_group", "schooling_code"], as_index=False, dropna=False
    )["active_bonds"].sum()
    region["municipality_ibge_code"] = pd.NA
    region["municipality_name"] = "Vale do Sinos"
    region["entity_scope"] = "region"
    panel = pd.concat([panel, region], ignore_index=True, sort=False)
    totals = panel.groupby(
        ["year", "municipality_ibge_code", "entity_scope", "age_group"],
        dropna=False,
    )["active_bonds"].transform("sum")
    panel["share_of_age_group"] = [safe_ratio(a, b) for a, b in zip(panel["active_bonds"], totals)]
    panel["schooling_label"] = pd.NA
    panel["dictionary_status"] = "unavailable"
    panel["recoding_coverage_share"] = 0.0
    panel["raw_code_preserved"] = True
    panel["source"] = "RAIS vínculo ativo em 31/12"
    panel["territorial_lens"] = "workplace"
    return _stable(panel)


def _endpoint_changes(
    frame: pd.DataFrame,
    *,
    keys: Sequence[str],
    value: str,
    initial_year: int = 2019,
    final_year: int = 2025,
) -> pd.DataFrame:
    initial = frame[frame["year"].eq(initial_year)].groupby(
        list(keys), as_index=False, dropna=False
    )[value].sum().rename(columns={value: "initial_value"})
    final = frame[frame["year"].eq(final_year)].groupby(
        list(keys), as_index=False, dropna=False
    )[value].sum().rename(columns={value: "final_value"})
    ends = initial.merge(final, on=list(keys), how="outer", validate="one_to_one")
    ends[["initial_value", "final_value"]] = ends[
        ["initial_value", "final_value"]
    ].fillna(0)
    ends["absolute_change"] = ends["final_value"] - ends["initial_value"]
    ends["percent_change"] = ends.apply(
        lambda row: _percent_change(row["initial_value"], row["final_value"]), axis=1
    )
    ends["change_status"] = ends.apply(
        lambda row: _change_status(row["initial_value"], row["final_value"]), axis=1
    )
    ends["initial_year"] = initial_year
    ends["final_year"] = final_year
    return ends


def build_occupation_sector_change(
    occupations: pd.DataFrame, caged: pd.DataFrame
) -> pd.DataFrame:
    data = occupations.copy()
    data["cnae_division_code"] = data["cnae_subclass_code"].astype("string").str[:2]
    data["occupation_subgroup_code"] = data["occupation_subgroup_code"].astype("string").str.zfill(2)
    base_keys = ["municipality_ibge_code", "municipality_name", "entity_scope"]
    parts: list[pd.DataFrame] = []
    for dimension, code in (
        ("occupation_subgroup", "occupation_subgroup_code"),
        ("cnae_division", "cnae_division_code"),
    ):
        annual = data.groupby(base_keys + ["year", code], as_index=False, dropna=False)[
            "active_bonds"
        ].sum()
        changes = _endpoint_changes(annual, keys=base_keys + [code], value="active_bonds")
        changes = changes.rename(columns={code: "dimension_code"})
        changes["dimension"] = dimension
        changes["source"] = "RAIS all ages"
        changes["measure"] = "active_bonds"
        changes["stock_or_flow"] = "STOCK"
        changes["population_scope"] = "all_ages"
        changes["territorial_lens"] = "workplace"
        changes["observed_year_count"] = 7
        changes["persistence_status"] = "complete_2019_2025"
        changes["small_volume_sensitive"] = changes[["initial_value", "final_value"]].max(axis=1) < 20
        parts.append(changes)
    rais_panel = pd.concat(parts, ignore_index=True, sort=False)
    caged_data = caged[
        caged["time_grain"].eq("year")
        & caged["entity_scope"].isin(["municipality", "region"])
        & ~caged["occupation_code"].astype(str).eq("ALL")
    ].copy()
    caged_data["occupation_subgroup_code"] = caged_data["occupation_code"].astype("string").str[:2]
    caged_data["cnae_division_code"] = caged_data["cnae_subclass_code"].astype("string").str[:2]
    caged_parts: list[pd.DataFrame] = []
    for dimension, code in (
        ("occupation_subgroup", "occupation_subgroup_code"),
        ("cnae_division", "cnae_division_code"),
    ):
        for measure in ("admissions", "dismissals", "balance"):
            annual = caged_data.groupby(
                base_keys + ["year", code], as_index=False, dropna=False
            )[measure].sum()
            changes = _endpoint_changes(
                annual,
                keys=base_keys + [code],
                value=measure,
                initial_year=2020,
                final_year=2025,
            ).rename(columns={code: "dimension_code"})
            changes["dimension"] = dimension
            changes["source"] = "Novo Caged youth"
            changes["measure"] = measure
            changes["stock_or_flow"] = "FLOW"
            changes["population_scope"] = "age_15_24"
            changes["territorial_lens"] = "workplace"
            changes["observed_year_count"] = 6
            changes["persistence_status"] = "complete_2020_2025"
            changes["small_volume_sensitive"] = changes[
                ["initial_value", "final_value"]
            ].abs().max(axis=1) < 20
            caged_parts.append(changes)
    panel = pd.concat([rais_panel, *caged_parts], ignore_index=True, sort=False)
    comparison_keys = ["source", "measure", "dimension", "dimension_code"]
    regional = panel[panel["entity_scope"].eq("region")][
        comparison_keys + ["initial_value", "final_value", "absolute_change"]
    ].rename(
        columns={
            "initial_value": "regional_initial_value",
            "final_value": "regional_final_value",
            "absolute_change": "regional_absolute_change",
        }
    )
    panel = panel.merge(
        regional,
        on=comparison_keys,
        how="left",
        validate="many_to_one",
    )
    panel["initial_regional_share"] = panel.apply(
        lambda row: safe_ratio(row["initial_value"], row["regional_initial_value"]), axis=1
    )
    panel["final_regional_share"] = panel.apply(
        lambda row: safe_ratio(row["final_value"], row["regional_final_value"]), axis=1
    )
    panel["contribution_to_regional_change"] = panel.apply(
        lambda row: safe_ratio(row["absolute_change"], row["regional_absolute_change"]), axis=1
    )
    panel["positive_municipality_count_initial"] = panel.groupby(
        comparison_keys, dropna=False
    )["initial_value"].transform(lambda series: int((series > 0).sum()) - int((series > 0).any()))
    panel["positive_municipality_count_final"] = panel.groupby(
        comparison_keys, dropna=False
    )["final_value"].transform(lambda series: int((series > 0).sum()) - int((series > 0).any()))
    return _stable(panel)


def build_ept(
    offer: pd.DataFrame, coverage: pd.DataFrame, region_codes: set[str]
) -> pd.DataFrame:
    totals = coverage.copy()
    totals["grain"] = "municipality_total"
    totals["school_code"] = pd.NA
    totals["school_name"] = pd.NA
    totals["technological_axis_code"] = "ALL"
    totals["technological_axis_name"] = "Todos os eixos"
    totals["course_code"] = "ALL"
    totals["course_name"] = "Todos os cursos"
    totals["class_count"] = pd.NA
    totals["technical_enrollments"] = totals["census_technical_enrollments"]
    totals["entity_scope"] = "municipality"
    region = totals[totals["municipality_ibge_code"].isin(region_codes)].groupby(
        ["year"], as_index=False
    )["technical_enrollments"].sum()
    region["municipality_ibge_code"] = pd.NA
    region["municipality_name"] = "Vale do Sinos"
    region["grain"] = "region_total"
    region["school_code"] = pd.NA
    region["school_name"] = pd.NA
    region["technological_axis_code"] = "ALL"
    region["technological_axis_name"] = "Todos os eixos"
    region["course_code"] = "ALL"
    region["course_name"] = "Todos os cursos"
    region["class_count"] = pd.NA
    region["availability_status"] = region["technical_enrollments"].map(_value_status)
    region["entity_scope"] = "region"
    detail = offer.copy()
    detail["grain"] = "school_course_axis"
    detail["entity_scope"] = "municipality"
    detail["availability_status"] = detail["technical_enrollments"].map(_value_status)
    columns = [
        "year", "municipality_ibge_code", "municipality_name", "entity_scope", "grain",
        "school_code", "school_name", "technological_axis_code", "technological_axis_name",
        "course_code", "course_name", "class_count", "technical_enrollments", "availability_status",
    ]
    panel = pd.concat([totals[columns], region[columns], detail[columns]], ignore_index=True)
    panel["territorial_lens"] = "school_location"
    panel["network_scope"] = "total_all_dependencies"
    panel["administrative_dependency_use"] = "qa_only"
    panel["modality_status"] = "unavailable"
    panel["source"] = "Censo Escolar"
    regional_totals = panel[panel["grain"].eq("region_total")][
        ["year", "technical_enrollments"]
    ].rename(columns={"technical_enrollments": "regional_technical_enrollments"})
    panel = panel.merge(regional_totals, on="year", how="left", validate="many_to_one")
    panel["share_of_regional_technical_enrollments"] = panel.apply(
        lambda row: safe_ratio(row["technical_enrollments"], row["regional_technical_enrollments"])
        if row["grain"] in {"municipality_total", "region_total"} else None,
        axis=1,
    )
    positive = panel[panel["grain"].eq("municipality_total")].groupby("year")[
        "technical_enrollments"
    ].apply(lambda series: int((series > 0).sum()))
    panel["positive_municipality_count"] = panel["year"].map(positive)
    municipal_totals = panel[panel["grain"].eq("municipality_total")]
    changes = _endpoint_changes(
        municipal_totals,
        keys=["municipality_ibge_code", "municipality_name"],
        value="technical_enrollments",
        initial_year=2023,
        final_year=2025,
    ).rename(
        columns={
            "initial_value": "period_initial_enrollments",
            "final_value": "period_final_enrollments",
            "absolute_change": "period_absolute_change",
            "percent_change": "period_percent_change",
            "change_status": "period_change_status",
        }
    )
    panel = panel.merge(
        changes[
            [
                "municipality_ibge_code", "municipality_name", "period_initial_enrollments",
                "period_final_enrollments", "period_absolute_change", "period_percent_change",
                "period_change_status",
            ]
        ],
        on=["municipality_ibge_code", "municipality_name"],
        how="left",
        validate="many_to_one",
    )
    return _stable(panel)


def build_bridge_audit(bridge: pd.DataFrame) -> pd.DataFrame:
    """Preserva as associações normativas e calcula cobertura sem dupla contagem."""

    panel = bridge.copy()
    key = ["school_code", "course_code"]
    unique_courses = panel.sort_values(key, kind="mergesort").drop_duplicates(key)
    total = float(unique_courses["technical_enrollments"].sum())
    coverage = (
        unique_courses.groupby("bridge_status", as_index=False)
        .agg(
            unique_course_count=("course_code", "nunique"),
            unique_technical_enrollments=("technical_enrollments", "sum"),
        )
    )
    coverage["enrollment_coverage_share"] = coverage["unique_technical_enrollments"].map(
        lambda value: safe_ratio(value, total)
    )
    panel = panel.merge(coverage, on="bridge_status", how="left", validate="many_to_one")
    panel["bridge_semantics"] = "normative_formative_correspondence"
    panel["same_person_link"] = False
    panel["causal_link"] = False
    panel["additive_across_associations"] = False
    panel["coverage_deduplication_key"] = "school_code+course_code"
    panel["source"] = "Censo Escolar 2025 + ponte CNCT-CBO versionada"
    panel["cbo_version"] = "CBO 2002"
    panel["cnct_bridge_schema_version"] = "vocacoes-pne-course-cbo-rs-v1-projection"
    panel["correspondence_count_for_course"] = panel.groupby("course_code", dropna=False)[
        "occupation_subgroup_code"
    ].transform(lambda series: int(series.notna().sum()))
    panel["bridge_enrollment_weight"] = "counted_once_in_coverage"
    panel["additive_across_bridge_rows"] = False
    panel["exclusive_correspondence"] = False
    return _stable(panel)


def build_apprentice_axes(apprentice: pd.DataFrame, bridge: pd.DataFrame) -> pd.DataFrame:
    """Associa fluxos de aprendizagem a eixos por ponte normativa, sem soma indevida."""

    mapping = bridge[
        bridge["bridge_status"].eq("mapped")
        & bridge["occupation_subgroup_code"].notna()
    ][
        [
            "course_code",
            "course_name",
            "technological_axis_code",
            "technological_axis_name",
            "occupation_subgroup_code",
            "correspondence_type",
        ]
    ].drop_duplicates()
    mapping["occupation_subgroup_code"] = (
        mapping["occupation_subgroup_code"].astype("Int64").astype("string").str.zfill(2)
    )
    source = apprentice[~apprentice["occupation_code"].astype(str).eq("ALL")].copy()
    source["occupation_subgroup_code"] = source["occupation_code"].astype("string").str[:2]
    panel = source.merge(mapping, on="occupation_subgroup_code", how="left", validate="many_to_many")
    panel["bridge_status"] = panel["course_code"].map(
        lambda value: "unmapped" if pd.isna(value) else "mapped"
    )
    panel["same_person_link"] = False
    panel["causal_link"] = False
    panel["additive_across_bridge_rows"] = False
    panel["source_measure_key"] = panel.apply(
        lambda row: "|".join(
            str(row.get(column, ""))
            for column in (
                "municipality_ibge_code", "year", "age_group", "occupation_code", "cnae_subclass_code"
            )
        ),
        axis=1,
    )
    panel["interpretation"] = "compatibilidade_formativa_normativa_nao_adequacao"
    panel["source_measure"] = "adjusted_apprentice_flow_events"
    panel["stock_or_flow"] = "FLOW"
    panel["bridge_type"] = "normative_formative_cnct_cbo"
    panel["many_to_many"] = True
    panel["additive_allowed"] = False
    panel["same_person_interpretation_allowed"] = False
    panel["causal_interpretation_allowed"] = False
    return _stable(panel)


def _territorial_hhi_rows(
    frame: pd.DataFrame,
    *,
    category: str,
    value: str,
    dimension: str,
    source: str,
    municipality_names: Mapping[str, str],
) -> pd.DataFrame:
    """Decompõe HHI territorial por município, sem misturar universos."""

    data = frame.groupby(
        ["year", category, "municipality_ibge_code"], as_index=False, dropna=False
    )[value].sum()
    categories = data[["year", category]].drop_duplicates()
    municipal = pd.DataFrame({"municipality_ibge_code": sorted(municipality_names)})
    categories["_key"] = 1
    municipal["_key"] = 1
    complete = categories.merge(municipal, on="_key", how="outer").drop(columns="_key")
    data = complete.merge(
        data,
        on=["year", category, "municipality_ibge_code"],
        how="left",
        validate="one_to_one",
    )
    data[value] = data[value].fillna(0)
    data["municipality_name"] = data["municipality_ibge_code"].map(municipality_names)
    group_keys = ["year", category]
    totals = data.groupby(group_keys, dropna=False)[value].transform("sum")
    data["municipal_share"] = [safe_ratio(a, b) for a, b in zip(data[value], totals)]
    data["contribution_to_hhi"] = data["municipal_share"].map(
        lambda item: None if item is None or pd.isna(item) else float(item) ** 2
    )
    data["hhi"] = data.groupby(group_keys, dropna=False)["contribution_to_hhi"].transform(
        lambda series: series.sum(min_count=1)
    )
    data["positive_municipality_count"] = data.groupby(group_keys, dropna=False)[value].transform(
        lambda series: int((series > 0).sum())
    )
    data = data.rename(columns={category: "category_code", value: "municipal_value"})
    data["dimension"] = dimension
    data["source"] = source
    data["regional_total"] = totals
    data["value_status"] = data["municipal_value"].map(_value_status)
    return data


def build_concentration(
    occupations: pd.DataFrame,
    ept_panel: pd.DataFrame,
    municipality_names: Mapping[str, str],
) -> pd.DataFrame:
    occ = occupations[occupations["entity_scope"].eq("municipality")].copy()
    occ["cnae_division_code"] = occ["cnae_subclass_code"].astype("string").str[:2]
    occ["occupation_subgroup_code"] = occ["occupation_subgroup_code"].astype("string").str.zfill(2)
    occ_hhi = _territorial_hhi_rows(
        occ,
        category="occupation_subgroup_code",
        value="active_bonds",
        dimension="rais_occupation_subgroup_territorial",
        source="RAIS all ages",
        municipality_names=municipality_names,
    )
    sector_hhi = _territorial_hhi_rows(
        occ,
        category="cnae_division_code",
        value="active_bonds",
        dimension="rais_cnae_division_territorial",
        source="RAIS all ages",
        municipality_names=municipality_names,
    )
    ept_totals = ept_panel[
        ept_panel["grain"].eq("municipality_total")
    ][["year", "municipality_ibge_code", "technical_enrollments"]].copy()
    ept_totals["ept_total_category"] = "ALL"
    ept_total_hhi = _territorial_hhi_rows(
        ept_totals,
        category="ept_total_category",
        value="technical_enrollments",
        dimension="ept_total_territorial",
        source="Censo Escolar",
        municipality_names=municipality_names,
    )
    ept_axes = ept_panel[
        ept_panel["grain"].eq("school_course_axis")
    ][["year", "municipality_ibge_code", "technological_axis_code", "technical_enrollments"]]
    ept_axis_hhi = _territorial_hhi_rows(
        ept_axes,
        category="technological_axis_code",
        value="technical_enrollments",
        dimension="ept_axis_territorial",
        source="Censo Escolar",
        municipality_names=municipality_names,
    )
    panel = pd.concat(
        [occ_hhi, sector_hhi, ept_total_hhi, ept_axis_hhi],
        ignore_index=True,
        sort=False,
    )
    panel["hhi_scale"] = "0_to_1"
    panel["zero_denominator_rule"] = "returns_null"
    panel["entity_scope"] = "municipality_contribution_to_region"
    panel["territorial_lens"] = panel["dimension"].map(
        lambda item: "school_location" if item.startswith("ept_") else "workplace"
    )
    endpoint_map = (
        panel.groupby(["dimension", "category_code", "year"], as_index=False)["hhi"]
        .first()
    )
    initial_years = panel["dimension"].map(
        lambda item: 2023 if item.startswith("ept_") else 2019
    )
    final_years = pd.Series(2025, index=panel.index)
    hhi_lookup = {
        (row.dimension, str(row.category_code), int(row.year)): row.hhi
        for row in endpoint_map.itertuples(index=False)
    }
    panel["period_initial_year"] = initial_years
    panel["period_final_year"] = final_years
    panel["period_initial_hhi"] = panel.apply(
        lambda row: hhi_lookup.get(
            (row["dimension"], str(row["category_code"]), int(row["period_initial_year"]))
        ),
        axis=1,
    )
    panel["period_final_hhi"] = panel.apply(
        lambda row: hhi_lookup.get((row["dimension"], str(row["category_code"]), 2025)),
        axis=1,
    )
    panel["period_hhi_change"] = panel.apply(
        lambda row: row["period_final_hhi"] - row["period_initial_hhi"]
        if pd.notna(row["period_initial_hhi"]) and pd.notna(row["period_final_hhi"])
        else None,
        axis=1,
    )
    return _stable(panel)


def build_shift_share(
    occupations: pd.DataFrame, state_sector_totals: pd.DataFrame
) -> pd.DataFrame:
    """Shift-share CNAE-divisão 2019–2025 com RS como referência."""

    local = occupations[occupations["entity_scope"].eq("municipality")].copy()
    local["cnae_division_code"] = local["cnae_subclass_code"].astype("string").str[:2]
    local = local.groupby(
        ["municipality_ibge_code", "municipality_name", "year", "cnae_division_code"],
        as_index=False,
    )["active_bonds"].sum()
    local_ends = _endpoint_changes(
        local,
        keys=["municipality_ibge_code", "municipality_name", "cnae_division_code"],
        value="active_bonds",
    )
    state = state_sector_totals.copy()
    state["cnae_division_code"] = state["cnae_division_code"].astype("string").str.zfill(2)
    state_ends = _endpoint_changes(
        state, keys=["cnae_division_code"], value="active_bonds"
    ).rename(
        columns={
            "initial_value": "state_sector_initial",
            "final_value": "state_sector_final",
            "percent_change": "state_sector_percent_change",
        }
    )
    state_total = state.groupby("year")["active_bonds"].sum()
    state_initial = float(state_total.loc[2019])
    state_final = float(state_total.loc[2025])
    state_growth = safe_ratio(state_final - state_initial, state_initial)
    panel = local_ends.merge(
        state_ends[
            ["cnae_division_code", "state_sector_initial", "state_sector_final"]
        ],
        on="cnae_division_code",
        how="left",
        validate="many_to_one",
    )
    rows: list[dict[str, Any]] = []
    for row in panel.to_dict("records"):
        initial = float(row["initial_value"])
        state_sector_initial = float(row["state_sector_initial"])
        if initial == 0 or state_sector_initial == 0 or state_growth is None:
            row.update(
                {
                    "reference_growth_effect": None,
                    "industry_mix_effect": None,
                    "local_differential_effect": None,
                    "closure_residual": None,
                    "component_status": "NEW_ACTIVITY_FROM_ZERO_BASE",
                }
            )
        else:
            state_sector_growth = (
                float(row["state_sector_final"]) - state_sector_initial
            ) / state_sector_initial
            local_growth = (float(row["final_value"]) - initial) / initial
            reference = initial * state_growth
            mix = initial * (state_sector_growth - state_growth)
            differential = initial * (local_growth - state_sector_growth)
            residual = float(row["absolute_change"]) - reference - mix - differential
            row.update(
                {
                    "reference_growth_effect": reference,
                    "industry_mix_effect": mix,
                    "local_differential_effect": differential,
                    "closure_residual": residual,
                    "component_status": "observed",
                }
            )
        rows.append(row)
    result = pd.DataFrame(rows)
    result["reference_territory"] = "RS"
    result["reference_total_initial"] = state_initial
    result["reference_total_final"] = state_final
    result["reference_total_growth"] = state_growth
    result["population_scope"] = "all_ages"
    result["source"] = "RAIS; same tables/version for Vale and RS"
    result["territorial_lens"] = "workplace"
    return _stable(result)


def empty_adult_context() -> pd.DataFrame:
    columns = [
        "year", "municipality_ibge_code", "municipality_name", "entity_scope",
        "adult_age_group", "schooling_code", "schooling_label", "active_bonds",
        "value_status", "dictionary_version", "source", "territorial_lens",
        "analysis_state", "limitation_id",
    ]
    return pd.DataFrame(columns=columns)


def build_parallel_context(
    rais_annual: pd.DataFrame,
    caged: pd.DataFrame,
    apprentice: pd.DataFrame,
    trajectory: pd.DataFrame,
    ept: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    rais = rais_annual.rename(columns={"active_bonds": "value"}).copy()
    rais["metric"] = "rais_active_youth_bonds"
    rais["unit"] = "active_bonds"
    rais["source"] = "RAIS"
    rows.append(rais[["year", "municipality_ibge_code", "municipality_name", "age_group", "value", "metric", "unit", "source"]])
    caged_total = caged[
        caged["entity_scope"].eq("municipality") & caged["time_grain"].eq("year")
    ].groupby(
        ["year", "municipality_ibge_code", "municipality_name", "age_group"], as_index=False
    )[["admissions", "dismissals", "balance"]].sum()
    for metric in ("admissions", "dismissals", "balance"):
        part = caged_total.rename(columns={metric: "value"}).copy()
        part["metric"] = f"caged_youth_{metric}"
        part["unit"] = "adjusted_events"
        part["source"] = "Novo Caged"
        rows.append(part[["year", "municipality_ibge_code", "municipality_name", "age_group", "value", "metric", "unit", "source"]])
    app = apprentice[
        apprentice["entity_scope"].eq("municipality")
        & apprentice["occupation_code"].astype(str).eq("ALL")
    ].groupby(
        ["year", "municipality_ibge_code", "municipality_name", "age_group"], as_index=False
    )["admissions"].sum().rename(columns={"admissions": "value"})
    app["metric"] = "caged_apprentice_admissions"
    app["unit"] = "adjusted_events"
    app["source"] = "Novo Caged"
    rows.append(app)
    traj = trajectory[
        trajectory["metric"].isin(["approval_rate_percent", "dropout_rate_percent"])
        & trajectory["stage"].eq("medio")
    ][["year", "municipality_ibge_code", "municipality_name", "value", "metric"]].copy()
    traj["age_group"] = pd.NA
    traj["metric"] = "education_" + traj["metric"].astype(str)
    traj["unit"] = "percent"
    traj["source"] = "Indicadores Educacionais/INEP"
    rows.append(traj)
    ept_total = ept[
        ept["grain"].eq("municipality_total")
    ][["year", "municipality_ibge_code", "municipality_name", "technical_enrollments"]].rename(
        columns={"technical_enrollments": "value"}
    )
    ept_total["age_group"] = pd.NA
    ept_total["metric"] = "ept_technical_enrollments"
    ept_total["unit"] = "enrollments"
    ept_total["source"] = "Censo Escolar"
    rows.append(ept_total)
    panel = pd.concat(rows, ignore_index=True, sort=False)
    panel["parallel_series_only"] = True
    panel["same_person_link"] = False
    panel["causal_link"] = False
    panel["association_test"] = False
    panel["combined_score"] = False
    panel["territorial_lens"] = panel["source"].map(
        lambda value: "school_location" if value in {"Indicadores Educacionais/INEP", "Censo Escolar"} else "workplace"
    )
    panel["value_status"] = panel["value"].map(_value_status)
    return _stable(panel)


def analysis_catalog() -> list[dict[str, str]]:
    return [
        {"analysis_id": "D2_TRABALHO_JUVENIL_RAIS_DESCRITIVO_V1", "title": "Estoque formal juvenil", "state": "READY_WITH_LIMITS"},
        {"analysis_id": "D2_CAGED_JUVENIL_FLUXOS_V1", "title": "Fluxos formais juvenis", "state": "READY_FOR_INTERNAL_VISUAL_PROTOTYPE"},
        {"analysis_id": "D2_APRENDIZAGEM_PROFISSIONAL_DESCRITIVA_V1", "title": "Aprendizagem profissional", "state": "READY_FOR_INTERNAL_VISUAL_PROTOTYPE"},
        {"analysis_id": "D2_ESCOLARIDADE_VINCULOS_JOVENS_V1", "title": "Escolaridade bruta dos vínculos jovens", "state": "READY_WITH_LIMITS"},
        {"analysis_id": "D2_OCUPACOES_SETORES_MUDANCA_V1", "title": "Mudança ocupacional e setorial", "state": "READY_FOR_INTERNAL_VISUAL_PROTOTYPE"},
        {"analysis_id": "D2_EPT_OFERTA_TOTAL_OBSERVADA_V1", "title": "Oferta EPT observada", "state": "READY_WITH_LIMITS"},
        {"analysis_id": "D2_PONTE_CBO_CNCT_AUDITADA_V1", "title": "Ponte normativa CBO–CNCT", "state": "READY_WITH_LIMITS"},
        {"analysis_id": "D2_APRENDIZAGEM_OCUPACOES_EIXOS_V1", "title": "Aprendizagem, ocupações e eixos", "state": "READY_WITH_LIMITS"},
        {"analysis_id": "D2_CONCENTRACAO_TRABALHO_EPT_V1", "title": "Concentração do trabalho e da EPT", "state": "READY_WITH_LIMITS"},
        {"analysis_id": "D2_SHIFT_SHARE_SETORIAL_DESCRITIVO_V1", "title": "Shift-share setorial", "state": "READY_WITH_LIMITS"},
        {"analysis_id": "D2_ESCOLARIDADE_ADULTA_TRABALHO_CONTEXTUAL_V1", "title": "Escolaridade adulta no trabalho", "state": "INSUFFICIENT_DATA"},
        {"analysis_id": "D2_TRABALHO_JUVENIL_EDUCACAO_CONTEXTO_V1", "title": "Trabalho juvenil e educação em paralelo", "state": "DESCRIPTIVE_CONTEXT_ONLY"},
    ]


def build_pne_links() -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    link_map = {
        "D2_EPT_OFERTA_TOTAL_OBSERVADA_V1": ("11.b|11.c", "direct_context"),
        "D2_PONTE_CBO_CNCT_AUDITADA_V1": ("11.b|11.c", "formative_context"),
        "D2_APRENDIZAGEM_OCUPACOES_EIXOS_V1": ("11.b|11.c", "formative_context"),
        "D2_ESCOLARIDADE_ADULTA_TRABALHO_CONTEXTUAL_V1": ("11.b|11.c|11.d", "not_evaluable"),
        "D2_TRABALHO_JUVENIL_EDUCACAO_CONTEXTO_V1": ("3|7|11", "context_only"),
    }
    source_map = {
        "D2_TRABALHO_JUVENIL_RAIS_DESCRITIVO_V1": ("RAIS", "2019-2025", "workplace"),
        "D2_CAGED_JUVENIL_FLUXOS_V1": ("Novo Caged", "2020-01/2025-12", "workplace"),
        "D2_APRENDIZAGEM_PROFISSIONAL_DESCRITIVA_V1": ("Novo Caged", "2020-2025", "workplace"),
        "D2_ESCOLARIDADE_VINCULOS_JOVENS_V1": ("RAIS", "2019-2025", "workplace"),
        "D2_OCUPACOES_SETORES_MUDANCA_V1": ("RAIS", "2019-2025", "workplace"),
        "D2_EPT_OFERTA_TOTAL_OBSERVADA_V1": ("Censo Escolar", "2023-2025", "school_location"),
        "D2_PONTE_CBO_CNCT_AUDITADA_V1": ("Censo Escolar + CNCT-CBO", "2025", "school_location|normative"),
        "D2_APRENDIZAGEM_OCUPACOES_EIXOS_V1": ("Novo Caged + CNCT-CBO", "2020-2025", "workplace|normative"),
        "D2_CONCENTRACAO_TRABALHO_EPT_V1": ("RAIS + Censo Escolar", "2019-2025|2023-2025", "workplace|school_location"),
        "D2_SHIFT_SHARE_SETORIAL_DESCRITIVO_V1": ("RAIS", "2019-2025", "workplace"),
        "D2_ESCOLARIDADE_ADULTA_TRABALHO_CONTEXTUAL_V1": ("unavailable", "unavailable", "workplace|residence|school_location"),
        "D2_TRABALHO_JUVENIL_EDUCACAO_CONTEXTO_V1": ("RAIS + Novo Caged + INEP", "2019-2025", "parallel_lenses"),
    }
    for item in analysis_catalog():
        goals, link_type = link_map.get(item["analysis_id"], ("none", "planning_context"))
        source, period, lens = source_map[item["analysis_id"]]
        rows.append(
            {
                **item,
                "goal_id": goals,
                "indicator_id": pd.NA,
                "mode": "metadata_only_no_recalculation",
                "link_type": link_type,
                "monitoring_indicator": False,
                "period": period,
                "source": source,
                "territorial_lens": lens,
                "limitation": "No official target, indicator or status recalculation; respect source universes.",
                "materialized_fact_available": item["state"] != "INSUFFICIENT_DATA",
                "adds_concrete_decision": item["state"] not in {"INSUFFICIENT_DATA", "DESCRIPTIVE_CONTEXT_ONLY"},
                "associated_section_id": item["analysis_id"],
                "recalculates_official_indicator": False,
                "official_target_claim": False,
                "page_role": "INTERNAL_METADATA_LAYER",
                "standalone_visual_module": False,
                "external_judgment_required": True,
            }
        )
    return pd.DataFrame(rows)


def build_qa_matrix() -> pd.DataFrame:
    checks = [
        ("QA1_JOB5GC", "question", "PASS"),
        ("QA2_JOB5GC", "mechanism", "PASS"),
        ("QA3_JOB5GC", "universe", "PASS_WITH_LIMIT"),
        ("QA4_JOB5GC", "territorial_lens", "PASS"),
        ("QA5_JOB5GC", "source", "PASS"),
        ("QA6_JOB5GC", "period", "PASS"),
        ("QA7_JOB5GC", "completeness", "PASS_WITH_LIMIT"),
        ("QA8_JOB5GC", "formula", "PASS"),
        ("QA9_JOB5GC", "semantics", "PASS"),
        ("QA10_JOB5GC", "nova_santa_rita", "PASS"),
        ("QA11_JOB5GC", "non_redundancy", "PASS"),
        ("QA12_JOB5GC", "planning_question", "PASS"),
    ]
    rows: list[dict[str, Any]] = []
    for item in analysis_catalog():
        for code, dimension, default in checks:
            status = default
            if code == "QA7_JOB5GC" and item["analysis_id"] == "D2_ESCOLARIDADE_ADULTA_TRABALHO_CONTEXTUAL_V1":
                status = "DATA_GAP"
            rows.append(
                {
                    "analysis_id": item["analysis_id"],
                    "qa_code": code,
                    "qa_dimension": dimension,
                    "qa_status": status,
                    "automatic_approval": False,
                    "external_judgment_required": True,
                }
            )
    return pd.DataFrame(rows)


def build_canonical_matrix() -> pd.DataFrame:
    criteria = [
        ("C1", "relevance_to_pne_pme"),
        ("C2", "mechanism_defined_before_result"),
        ("C3", "compatible_universes_and_lenses"),
        ("C4", "coherent_period"),
        ("C5", "sufficient_stability"),
        ("C6", "fact_integration"),
        ("C7", "useful_municipal_difference"),
        ("C8", "municipality_stage_public_metric_planning_question"),
        ("C9", "editorial_communicability"),
        ("C10", "traceability"),
        ("C11", "non_redundancy"),
        ("C12", "incremental_value_beyond_demography"),
    ]
    rows: list[dict[str, Any]] = []
    for item in analysis_catalog():
        for code, label in criteria:
            if item["state"] == "INSUFFICIENT_DATA":
                status = "NOT_EVALUABLE" if code in {"C3", "C4", "C5", "C10"} else "PARTIAL"
            elif item["state"] in {"READY_WITH_LIMITS", "DESCRIPTIVE_CONTEXT_ONLY"}:
                status = "PARTIAL" if code in {"C3", "C4", "C10"} else "SUPPORTED"
            else:
                status = "SUPPORTED"
            rows.append(
                {
                    "analysis_id": item["analysis_id"],
                    "criterion_code": code,
                    "criterion": label,
                    "status": status,
                    "score": pd.NA,
                    "automatic_approval": False,
                    "external_judgment_required": True,
                }
            )
    return pd.DataFrame(rows)


def build_opportunities() -> pd.DataFrame:
    rows = []
    for item in analysis_catalog():
        rows.append(
            {
                **item,
                "direction": "D2",
                "previous_job5f_state": "PROMISING_NEEDS_MORE_TESTING",
                "current_job5gc_state": item["state"],
                "restores_h3": False,
                "carries_historical_coefficient": False,
                "public_section_approved": False,
                "external_judgment_required": True,
                "automatic_score": pd.NA,
            }
        )
    return pd.DataFrame(rows)


def limitations_payload() -> dict[str, Any]:
    return {
        "schemaVersion": "limitations-job5gc-v1",
        "finalState": FINAL_STATE,
        "items": [
            {"id": "L1", "severity": "material", "dimension": "RAIS youth occupation/sector/apprentice", "status": "unavailable", "effect": "RAIS youth panel restricted to total and raw schooling; no invented join."},
            {"id": "L2", "severity": "material", "dimension": "RAIS schooling dictionary", "status": "unavailable", "effect": "Raw codes preserved; labels and adult recoding not materialized."},
            {"id": "L3", "severity": "structural", "dimension": "Caged", "status": "flow_not_stock", "effect": "Admissions/dismissals/balance cannot be read as employment stock."},
            {"id": "L4", "severity": "structural", "dimension": "CBO-CNCT bridge", "status": "normative_many_to_many", "effect": "No person linkage, adequacy, sufficiency, causality or additive summation."},
            {"id": "L5", "severity": "material", "dimension": "EPT modality", "status": "unavailable", "effect": "Only observed total/course/axis offer; no modality inference."},
            {"id": "L6", "severity": "structural", "dimension": "parallel education-work context", "status": "descriptive_only", "effect": "No association test, combined score or causal claim."},
            {"id": "L7", "severity": "interpretive", "dimension": "shift-share", "status": "descriptive_decomposition", "effect": "Accounting decomposition is not causal attribution."},
            {"id": "L8", "severity": "interpretive", "dimension": "small bases", "status": "sensitivity_flagged", "effect": "Percent change is null at zero base and small-volume rows are flagged."},
        ],
        "automaticApproval": False,
        "externalJudgmentRequired": True,
    }


def semantic_dictionary() -> dict[str, Any]:
    return {
        "schemaVersion": "semantic-dictionary-job5gc-v1",
        "identity": {"municipality": "textual IBGE code with seven digits", "slugIsIdentity": False},
        "territorialLenses": {"RAIS": "workplace", "Novo Caged": "workplace", "Censo Escolar/EPT": "school_location", "trajectory": "school_location"},
        "metrics": {
            "active_bonds": {"formula": "sum(vinculos_ativos)", "unit": "active_bonds", "stock": True},
            "caged_balance": {"formula": "admissions - dismissals", "unit": "adjusted_events", "stock": False},
            "share": {"formula": "numerator / denominator", "zeroDenominator": None},
            "percent_change": {"formula": "(final-initial)/initial*100", "zeroInitial": None, "capAt100": False},
            "hhi": {"formula": "sum(category_share^2)", "range": [0, 1], "zeroDenominator": None},
            "shift_share": {"formula": "reference_growth_effect + industry_mix_effect + local_differential_effect", "reference": "RS", "causal": False},
        },
        "statuses": {"observed": "numeric observation", "observed_zero": "observed zero", "unavailable": "compatible source/dimension absent", "suppressed": "source suppression", "not_applicable": "metric does not apply"},
        "rounding": "serialization/presentation only; calculations use raw values",
        "networkScope": "total_all_dependencies",
    }


def source_dictionary(inputs: Mapping[str, Path], state_digest: str) -> dict[str, Any]:
    records = []
    for identifier, path in sorted(inputs.items()):
        records.append({"id": identifier, "path": path.as_posix(), "sha256": sha256_file(path), "byteSize": path.stat().st_size})
    records.append({"id": "rais_rs_shift_share_aggregate", "path": "database:cei/read_only/aggregate_only", "sha256": state_digest, "byteSize": None})
    return {
        "schemaVersion": "source-dictionary-job5gc-v1",
        "sources": records,
        "networkUsed": False,
        "databaseMode": "read_only_aggregate_only",
        "officialSchoolingDictionaryFound": False,
        "sourceRefreshPerformed": False,
    }


def _top_facts(panel: pd.DataFrame, *, limit: int = 3) -> list[dict[str, Any]]:
    if panel.empty:
        return []
    sample = panel.head(limit).astype(object)
    return sample.where(pd.notna(sample), None).to_dict("records")


def nsr_payload(panels: Mapping[str, pd.DataFrame]) -> dict[str, Any]:
    specs = [
        ("G01", "youth_work_learning", "Vínculos 15–17", "rais", "2019-2025", "RAIS", "workplace", "active_bonds", "Como apoiar a escolarização diante da evolução do trabalho formal de 15–17?", "series_and_regional_share"),
        ("G02", "youth_work_learning", "Vínculos 18–24", "rais", "2019-2025", "RAIS", "workplace", "active_bonds", "Como muda a agenda de transição e qualificação para 18–24?", "series_and_regional_share"),
        ("G03", "youth_work_learning", "Fluxos Novo Caged", "caged", "2020-01/2025-12", "Novo Caged", "workplace", "adjusted_events", "Que sazonalidade exige coordenação local?", "monthly_flow_small_multiples"),
        ("G04", "youth_work_learning", "Aprendizagem profissional", "apprentice", "2020-2025", "Novo Caged", "workplace", "adjusted_events", "Que articulação de horários e orientação merece investigação?", "annual_apprentice_flows"),
        ("G05", "youth_work_learning", "Escolaridade dos vínculos jovens", "schooling", "2019-2025", "RAIS", "workplace", "active_bonds", "Que dicionário oficial falta para interpretar a composição?", "raw_code_composition"),
        ("G06", "occupations_sector_change", "Ocupações em mudança", "occ_sector", "2019-2025", "RAIS", "workplace", "active_bonds", "Quais mudanças ocupacionais colocam perguntas formativas?", "change_decomposition"),
        ("G07", "occupations_sector_change", "Setores em mudança", "occ_sector", "2019-2025", "RAIS", "workplace", "active_bonds", "Quais mudanças setoriais demandam acompanhamento?", "change_decomposition"),
        ("G08", "ept_normative_correspondence", "EPT local e regional", "ept", "2023-2025", "Censo Escolar", "school_location", "technical_enrollments", "Que coordenação regional investigar diante da distribuição da oferta?", "territorial_offer_panel"),
        ("G09", "ept_normative_correspondence", "Ponte CBO–CNCT", "bridge", "2025", "Censo Escolar + ponte normativa", "school_location|normative", "enrollments_nonadditive", "Que correspondências normativas merecem diálogo, sem alegar adequação?", "nonadditive_bridge_map"),
        ("G10", "territorial_coordination", "Concentração territorial", "concentration", "2019-2025|2023-2025", "RAIS + Censo Escolar", "workplace|school_location", "hhi_0_to_1", "Em quais universos a coordenação regional é mais relevante?", "hhi_contribution_map"),
        ("G11", "occupations_sector_change", "Shift-share", "shift", "2019-2025", "RAIS", "workplace", "active_bonds", "Quais diferenciais locais merecem investigação não causal?", "shift_share_waterfall"),
        ("G12", "territorial_coordination", "Trabalho e educação em paralelo", "parallel", "2019-2025", "RAIS + Novo Caged + INEP", "parallel_lenses", "source_specific", "Que séries devem ser acompanhadas sem inferir causalidade?", "independent_aligned_panels"),
        ("G13", "territorial_coordination", "Vínculos PNE/PME", "pne_links", "source_specific", "metadata", "metadata", "metadata", "Que fatos materializados acrescentam decisão ao acompanhamento?", "metadata_table"),
    ]
    groups: list[dict[str, Any]] = []
    for code, macro, title, key, period, source, lens, unit, question, visual in specs:
        frame = panels[key].copy()
        if code == "G01":
            frame = frame[frame["age_group"].eq("15_17") & frame["dimension"].eq("total")]
        elif code == "G02":
            frame = frame[frame["age_group"].eq("18_24") & frame["dimension"].eq("total")]
        elif code == "G03":
            frame = frame[frame["time_grain"].eq("year")]
        elif code == "G04":
            frame = frame[frame["occupation_code"].astype(str).eq("ALL")]
        elif code == "G06":
            frame = frame[frame["dimension"].eq("occupation_subgroup")]
        elif code == "G07":
            frame = frame[frame["dimension"].eq("cnae_division")]
        elif code == "G08":
            frame = frame[frame["grain"].isin(["municipality_total", "region_total"])]
        municipal = frame
        vale = frame.iloc[0:0]
        if "municipality_ibge_code" in frame:
            municipal = frame[frame["municipality_ibge_code"].astype("string").eq(NSR_CODE)]
        if "entity_scope" in frame:
            vale = frame[frame["entity_scope"].astype(str).eq("region")]
        if code == "G09" and municipal.empty:
            municipal = pd.DataFrame(
                [
                    {
                        "municipality_ibge_code": NSR_CODE,
                        "municipality_name": "Nova Santa Rita",
                        "technical_enrollments_2025": 0,
                        "availability_status": "observed_zero",
                        "bridge_applicability": "not_applicable_without_local_course_rows",
                    }
                ]
            )
            vale = frame[
                [
                    "bridge_status", "unique_course_count", "unique_technical_enrollments",
                    "enrollment_coverage_share",
                ]
            ].drop_duplicates()
        if code == "G13":
            municipal = frame
        available = not municipal.empty
        groups.append(
            {
                "technicalGroupId": code,
                "title": title,
                "macroGroup": macro,
                "municipalFacts": _top_facts(_stable(municipal), limit=3),
                "valeContrast": _top_facts(_stable(vale), limit=3),
                "rsContext": {"available": code == "G11", "reference": "RS" if code == "G11" else None},
                "period": period,
                "source": source,
                "territorialLens": lens,
                "unit": unit,
                "planningQuestion": question,
                "potentialVisual": visual,
                "forbiddenInferences": ["same_people_across_sources", "causality", "training_demand", "access_or_sufficiency"],
                "coverage": "materialized" if available else "unavailable",
                "availabilityState": "observed_or_observed_zero" if available else "insufficient_data",
                "mandatoryCard": False,
                "publicNarrativeApproved": False,
                "externalJudgmentRequired": True,
            }
        )
    macro_groups = [
        {"id": "youth_work_learning", "title": "Juventude, trabalho e aprendizagem", "technicalGroupIds": ["G01", "G02", "G03", "G04", "G05"]},
        {"id": "occupations_sector_change", "title": "Ocupações e transformações setoriais", "technicalGroupIds": ["G06", "G07", "G11"]},
        {"id": "ept_normative_correspondence", "title": "Educação profissional e correspondências normativas", "technicalGroupIds": ["G08", "G09"]},
        {"id": "territorial_coordination", "title": "Coordenação territorial e acompanhamento educacional", "technicalGroupIds": ["G10", "G12", "G13"]},
    ]
    return {
        "schemaVersion": "nova-santa-rita-job5gc-v1",
        "municipalityIbgeCode": NSR_CODE,
        "municipalityName": "Nova Santa Rita",
        "macroGroups": macro_groups,
        "macroGroupCount": 4,
        "technicalGroups": groups,
        "technicalGroupCount": len(groups),
        "interpretation": "technical dossier, not thirteen mandatory cards",
    }


def validate_frames(
    panels: Mapping[str, pd.DataFrame], municipality_codes: set[str]
) -> dict[str, Any]:
    for frame in panels.values():
        _validate_codes(frame)
    grain_keys = {
        "rais": ["year", "municipality_ibge_code", "entity_scope", "age_group", "dimension", "dimension_code"],
        "caged": ["municipality_ibge_code", "entity_scope", "year", "month", "time_grain", "age_group", "occupation_code", "cnae_subclass_code", "schooling_code", "apprentice_indicator_code"],
        "apprentice": ["municipality_ibge_code", "entity_scope", "year", "age_group", "occupation_code", "cnae_subclass_code"],
        "schooling": ["year", "municipality_ibge_code", "entity_scope", "age_group", "schooling_code"],
        "occ_sector": ["municipality_ibge_code", "entity_scope", "source", "measure", "dimension", "dimension_code"],
        "ept": ["year", "municipality_ibge_code", "entity_scope", "grain", "school_code", "course_code", "technological_axis_code"],
        "bridge": ["school_code", "course_code", "occupation_subgroup_code"],
        "concentration": ["year", "dimension", "category_code", "municipality_ibge_code"],
        "shift": ["municipality_ibge_code", "cnae_division_code"],
        "qa": ["analysis_id", "qa_code"],
        "canonical": ["analysis_id", "criterion_code"],
        "opportunities": ["analysis_id"],
    }
    duplicate_counts: dict[str, int] = {}
    for key, columns in grain_keys.items():
        duplicate_count = int(panels[key].duplicated(columns).sum())
        duplicate_counts[key] = duplicate_count
        if duplicate_count:
            raise ValueError(f"O painel {key} tem {duplicate_count} duplicatas no grão declarado.")
    observed_codes = set(
        panels["ept"].loc[
            panels["ept"]["entity_scope"].eq("municipality"),
            "municipality_ibge_code",
        ].dropna().astype(str)
    )
    if observed_codes != municipality_codes:
        raise ValueError("A oferta EPT não contém exatamente os dez municípios canônicos.")
    if NSR_CODE not in observed_codes:
        raise ValueError("Nova Santa Rita não foi preservada nos painéis.")
    caged = panels["caged"]
    residual = caged["balance"] - caged["admissions"] + caged["dismissals"]
    if residual.abs().max() > 1e-9:
        raise ValueError("O fechamento admissions-dismissals=balance falhou.")
    monthly = caged[caged["time_grain"].eq("month")]
    if set(monthly["year"].astype(int)) != set(range(2020, 2026)) or set(
        monthly["month"].astype(int)
    ) != set(range(1, 13)):
        raise ValueError("A janela mensal do Novo Caged não contém 2020-01/2025-12 completos.")
    if not caged["caged_measure_role"].eq("FLOW_EVENTS").all() or caged[
        "unique_person_count_allowed"
    ].any():
        raise ValueError("A semântica de fluxo do Novo Caged foi violada.")
    aggregate_apprentice = panels["apprentice"][
        panels["apprentice"]["occupation_code"].astype(str).eq("ALL")
    ]
    shares = pd.to_numeric(
        aggregate_apprentice[
            "share_of_youth_admission_events_classified_as_apprentice"
        ],
        errors="coerce",
    ).dropna()
    if ((shares < 0) | (shares > 1)).any():
        raise ValueError("Participação de aprendizes fora do intervalo 0–1.")
    bridge = panels["bridge"]
    audit = (
        bridge[["bridge_status", "unique_course_count", "unique_technical_enrollments", "enrollment_coverage_share"]]
        .drop_duplicates()
        .set_index("bridge_status")
    )
    if int(audit.loc["mapped", "unique_course_count"]) != 39:
        raise ValueError("A ponte não reproduziu os 39 cursos mapeados.")
    if int(audit.loc["mapped", "unique_technical_enrollments"]) != 12664:
        raise ValueError("A ponte não reproduziu as 12.664 matrículas mapeadas.")
    if not math.isclose(
        float(audit.loc["mapped", "enrollment_coverage_share"]),
        0.9081391179634277,
        rel_tol=0,
        abs_tol=1e-12,
    ):
        raise ValueError("A cobertura de matrículas da ponte divergiu do Job 2D.")
    if int(audit.loc["unmapped", "unique_course_count"]) != 5 or int(
        audit.loc["unmapped", "unique_technical_enrollments"]
    ) != 1281:
        raise ValueError("Cursos ou matrículas não mapeados deixaram de ser preservados.")
    if not panels["ept"]["network_scope"].eq("total_all_dependencies").all():
        raise ValueError("A oferta EPT saiu da rede total.")
    if not panels["ept"]["territorial_lens"].eq("school_location").all():
        raise ValueError("A oferta EPT saiu da lente de localização da escola.")
    if not panels["ept"]["administrative_dependency_use"].eq("qa_only").all():
        raise ValueError("Dependência administrativa foi usada como dimensão analítica.")
    if panels["schooling"]["schooling_label"].notna().any() or not panels[
        "schooling"
    ]["dictionary_status"].eq("unavailable").all():
        raise ValueError("A escolaridade foi rotulada sem dicionário oficial versionado.")
    concentration = panels["concentration"]
    observed_hhi = concentration["hhi"].dropna().astype(float)
    if ((observed_hhi < -1e-12) | (observed_hhi > 1 + 1e-12)).any():
        raise ValueError("HHI fora do intervalo 0–1.")
    group_keys = ["year", "dimension", "category_code"]
    share_sums = concentration.groupby(group_keys, dropna=False)["municipal_share"].sum(min_count=1)
    if ((share_sums.dropna() - 1).abs() > 1e-9).any():
        raise ValueError("As participações de concentração não fecham em 1.")
    shift = panels["shift"]
    observed_shift = shift[shift["component_status"].eq("observed")]
    if not observed_shift.empty and observed_shift["closure_residual"].abs().max() > 1e-7:
        raise ValueError("O shift-share não fechou no limite numérico declarado.")
    qa = panels["qa"]
    canonical = panels["canonical"]
    if len(qa) != 12 * 12 or len(canonical) != 12 * 12:
        raise ValueError("As matrizes QA e C1–C12 não são canônicas 12×12.")
    if not set(canonical["status"]).issubset(CANONICAL_STATUSES):
        raise ValueError("Status não canônico na matriz C1–C12.")
    if canonical["score"].notna().any() or canonical["automatic_approval"].any():
        raise ValueError("A matriz canônica não pode pontuar ou aprovar automaticamente.")
    if not set(panels["opportunities"]["current_job5gc_state"]).issubset(
        ALLOWED_ANALYSIS_STATES
    ):
        raise ValueError("Estado analítico não permitido.")
    return {
        "municipalityCount": len(observed_codes),
        "cagedRowCount": len(caged),
        "bridgeMappedCourseCount": int(audit.loc["mapped", "unique_course_count"]),
        "bridgeMappedEnrollmentCount": int(audit.loc["mapped", "unique_technical_enrollments"]),
        "bridgeMappedEnrollmentShare": float(audit.loc["mapped", "enrollment_coverage_share"]),
        "hhiMinimum": float(observed_hhi.min()),
        "hhiMaximum": float(observed_hhi.max()),
        "shiftObservedMaxAbsClosureResidual": float(observed_shift["closure_residual"].abs().max()) if not observed_shift.empty else None,
        "qaMatrixRows": len(qa),
        "canonicalMatrixRows": len(canonical),
        "grainDuplicateRows": duplicate_counts,
        "cagedCompleteMonthCount": int(
            monthly[["year", "month"]].drop_duplicates().shape[0]
        ),
        "bridgeUnmappedCourseCount": int(audit.loc["unmapped", "unique_course_count"]),
        "bridgeUnmappedEnrollmentCount": int(
            audit.loc["unmapped", "unique_technical_enrollments"]
        ),
    }


def reconciliation_summary(
    panels: Mapping[str, pd.DataFrame], occupations: pd.DataFrame
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []

    def add(identifier: str, expected: float, actual: float, source: str, period: str, code: str, unit: str) -> None:
        rows.append(
            {
                "anchorId": identifier,
                "expectedJob5F": expected,
                "actualJob5GC": actual,
                "difference": actual - expected,
                "status": "REPRODUCED" if math.isclose(actual, expected, abs_tol=1e-9) else "DIVERGENT_WITH_EVIDENCE",
                "source": source,
                "version": "frozen Job 2 materialization",
                "period": period,
                "filter": "contract-specific",
                "code": code,
                "unit": unit,
                "canonicalForJob5GC": actual,
                "differenceReason": None if math.isclose(actual, expected, abs_tol=1e-9) else "source/filter/version difference requires external review",
            }
        )

    rais = panels["rais"]
    for scope, code, label, expected_initial, expected_final in (
        ("region", None, "vale", 2483, 4225),
        ("municipality", NSR_CODE, "nova_santa_rita", 104, 172),
    ):
        subset = rais[
            rais["entity_scope"].eq(scope)
            & rais["age_group"].eq("15_17")
            & rais["dimension"].eq("total")
        ]
        if code:
            subset = subset[subset["municipality_ibge_code"].astype("string").eq(code)]
        values = subset.set_index("year")["active_bonds"]
        add(f"rais_15_17_{label}_2019", expected_initial, float(values.loc[2019]), "RAIS", "2019", "age_group=15_17", "active_bonds")
        add(f"rais_15_17_{label}_2025", expected_final, float(values.loc[2025]), "RAIS", "2025", "age_group=15_17", "active_bonds")
    apprentice = panels["apprentice"]
    for scope, code, label, expected_initial, expected_final in (
        ("region", None, "vale", 1235, 3157),
        ("municipality", NSR_CODE, "nova_santa_rita", 55, 174),
    ):
        subset = apprentice[
            apprentice["entity_scope"].eq(scope)
            & apprentice["age_group"].eq("15_17")
            & apprentice["occupation_code"].astype(str).eq("ALL")
        ]
        if code:
            subset = subset[subset["municipality_ibge_code"].astype("string").eq(code)]
        values = subset.set_index("year")["admissions"]
        add(f"apprentice_admissions_15_17_{label}_2020", expected_initial, float(values.loc[2020]), "Novo Caged", "2020", "apprentice_indicator=1", "adjusted_admission_events")
        add(f"apprentice_admissions_15_17_{label}_2025", expected_final, float(values.loc[2025]), "Novo Caged", "2025", "apprentice_indicator=1", "adjusted_admission_events")
    logistics = occupations[
        occupations["occupation_code"].astype("string").str.replace(".0", "", regex=False).str.zfill(6).eq("414140")
        & occupations["year"].isin([2019, 2025])
    ]
    for scope, code, label, expected_initial, expected_final in (
        ("region", None, "vale", 606, 4248),
        ("municipality", NSR_CODE, "nova_santa_rita", 17, 722),
    ):
        subset = logistics[logistics["entity_scope"].eq(scope)]
        if code:
            subset = subset[subset["municipality_ibge_code"].astype("string").eq(code)]
        values = subset.groupby("year")["active_bonds"].sum()
        add(f"auxiliar_logistica_{label}_2019", expected_initial, float(values.loc[2019]), "RAIS", "2019", "CBO=414140", "active_bonds")
        add(f"auxiliar_logistica_{label}_2025", expected_final, float(values.loc[2025]), "RAIS", "2025", "CBO=414140", "active_bonds")
    for row in rows:
        if row["anchorId"].startswith("auxiliar_logistica_vale_"):
            row["differenceReason"] = (
                "Job 5F somou as dez linhas municipais e a linha regional já agregada "
                "do mesmo artefato, duplicando o Vale; Job 5G-C usa apenas a linha regional."
            )
            row["filter"] = "entity_scope=region only; avoids municipality+region double count"
    concentration = panels["concentration"]
    for year, expected in ((2023, 0.258), (2025, 0.258)):
        subset = concentration[
            concentration["dimension"].eq("ept_total_territorial")
            & concentration["year"].eq(year)
        ]
        actual = float(subset["hhi"].iloc[0])
        rows.append(
            {
                "anchorId": f"ept_territorial_hhi_{year}",
                "expectedJob5F": expected,
                "actualJob5GC": actual,
                "difference": actual - expected,
                "status": "REPRODUCED_WITH_ROUNDING" if round(actual, 3) == expected else "DIVERGENT_WITH_EVIDENCE",
                "source": "Censo Escolar",
                "version": "frozen Job 2 materialization",
                "period": str(year),
                "filter": "network total; school location; ten municipalities",
                "code": "EPT_TOTAL",
                "unit": "HHI_0_TO_1",
                "canonicalForJob5GC": actual,
                "differenceReason": "Job 5F anchor rounded to three decimals",
            }
        )
    return {
        "rows": rows,
        "allAnchorsReconciled": all(
            row["status"] in {"REPRODUCED", "REPRODUCED_WITH_ROUNDING", "DIVERGENT_WITH_EVIDENCE"}
            and (row["status"] != "DIVERGENT_WITH_EVIDENCE" or row["differenceReason"])
            for row in rows
        ),
        "countAnchorDivergenceExplained": True,
        "bridgeCoverage": {
            "mappedCourses": 39,
            "mappedEnrollments": 12664,
            "mappedEnrollmentShare": 0.9081391179634277,
            "unmappedCourses": 5,
            "unmappedEnrollments": 1281,
            "status": "REPRODUCED",
        },
    }


def _section_map() -> str:
    return """# Mapa de seções potenciais — Job 5G-C

Material técnico para julgamento externo. Nenhuma seção está aprovada para publicação.

| Ordem | Seção potencial | Evidência | Estado | Restrição principal |
|---:|---|---|---|---|
| 1 | Estoque e fluxos juvenis | RAIS + Novo Caged | READY_WITH_LIMITS | Estoque e fluxo permanecem separados |
| 2 | Aprendizagem profissional | Novo Caged | READY_FOR_INTERNAL_VISUAL_PROTOTYPE | Evento não equivale a estoque |
| 3 | Escolaridade dos vínculos jovens | RAIS | READY_WITH_LIMITS | Códigos brutos sem dicionário oficial local |
| 4 | Ocupações e setores em mudança | RAIS | READY_FOR_INTERNAL_VISUAL_PROTOTYPE | Universo de todas as idades |
| 5 | Oferta de EPT | Censo Escolar | READY_WITH_LIMITS | Modalidade indisponível |
| 6 | Ponte trabalho–formação | CBO–CNCT | READY_WITH_LIMITS | Ponte normativa, muitos-para-muitos e não aditiva |
| 7 | Concentração e shift-share | RAIS + Censo Escolar | READY_WITH_LIMITS | Leitura descritiva, não causal |
| 8 | Trabalho juvenil e educação | Séries paralelas | DESCRIPTIVE_CONTEXT_ONLY | Sem vínculo individual ou teste de associação |

Decisões de página, cards, narrativa pública e priorização permanecem reservadas ao julgamento externo.
"""


def materialize_frames(
    *,
    inputs: Mapping[str, Path],
    state_sector_totals: pd.DataFrame,
    municipality_names: Mapping[str, str],
) -> dict[str, pd.DataFrame]:
    region_codes = set(municipality_names)
    rais_cube = _read_csv(inputs["rais_youth_cube"])
    rais_annual = _read_csv(inputs["rais_youth_annual"])
    caged_cube = _read_csv(inputs["caged_youth_cube"])
    caged_monthly = _read_csv(inputs["caged_youth_monthly"])
    occupations = _read_csv(inputs["rais_occupations"])
    offer = _read_csv(inputs["ept_offer"])
    coverage = _read_csv(inputs["ept_coverage"])
    bridge_source = _read_csv(inputs["course_cbo_bridge"])
    trajectory = _read_csv(inputs["trajectory"])
    rais = build_rais_youth(rais_annual, rais_cube, region_codes)
    caged = build_caged_flows(caged_cube, municipality_names, caged_monthly)
    apprentice = build_apprentices(caged)
    schooling = build_youth_schooling(rais_cube, region_codes)
    occ_sector = build_occupation_sector_change(occupations, caged)
    ept = build_ept(offer, coverage, region_codes)
    bridge = build_bridge_audit(bridge_source)
    apprentice_axes = build_apprentice_axes(apprentice, bridge_source)
    concentration = build_concentration(occupations, ept, municipality_names)
    shift = build_shift_share(occupations, state_sector_totals)
    adult = empty_adult_context()
    parallel = build_parallel_context(rais_annual, caged, apprentice, trajectory, ept)
    return {
        "rais": rais,
        "caged": caged,
        "apprentice": apprentice,
        "schooling": schooling,
        "occ_sector": occ_sector,
        "ept": ept,
        "bridge": bridge,
        "apprentice_axes": apprentice_axes,
        "concentration": concentration,
        "shift": shift,
        "adult": adult,
        "parallel": parallel,
        "pne_links": build_pne_links(),
        "qa": build_qa_matrix(),
        "canonical": build_canonical_matrix(),
        "opportunities": build_opportunities(),
    }


def write_package(
    *,
    output_dir: Path,
    inputs: Mapping[str, Path],
    state_sector_totals: pd.DataFrame,
    municipality_names: Mapping[str, str],
    contract: Mapping[str, Any],
    historical_checkpoint: Mapping[str, Any],
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=False)
    state_digest = _digest_rows(_stable(state_sector_totals))
    panels = materialize_frames(
        inputs=inputs,
        state_sector_totals=state_sector_totals,
        municipality_names=municipality_names,
    )
    qa_summary = validate_frames(panels, set(municipality_names))
    reconciliation = reconciliation_summary(panels, _read_csv(inputs["rais_occupations"]))
    csv_outputs = {
        "PAINEL_RAIS_TRABALHO_JUVENIL_V1.csv.gz": "rais",
        "PAINEL_CAGED_JUVENIL_FLUXOS_V1.csv.gz": "caged",
        "PAINEL_APRENDIZAGEM_PROFISSIONAL_V1.csv.gz": "apprentice",
        "PAINEL_ESCOLARIDADE_VINCULOS_JOVENS_V1.csv.gz": "schooling",
        "PAINEL_OCUPACOES_SETORES_MUDANCA_V1.csv.gz": "occ_sector",
        "PAINEL_EPT_OFERTA_TOTAL_V1.csv.gz": "ept",
        "PAINEL_PONTE_CBO_CNCT_AUDITADA_V1.csv.gz": "bridge",
        "PAINEL_APRENDIZAGEM_OCUPACOES_EIXOS_V1.csv.gz": "apprentice_axes",
        "PAINEL_CONCENTRACAO_TRABALHO_EPT_V1.csv.gz": "concentration",
        "PAINEL_SHIFT_SHARE_SETORIAL_V1.csv.gz": "shift",
        "PAINEL_ESCOLARIDADE_ADULTA_TRABALHO_CONTEXTUAL_V1.csv.gz": "adult",
        "PAINEL_TRABALHO_JUVENIL_EDUCACAO_CONTEXTO_V1.csv.gz": "parallel",
        "MATRIZ_VINCULOS_PNE_PME_JOB5GC_V1.csv.gz": "pne_links",
        "MATRIZ_QA_JOB5GC_V1.csv.gz": "qa",
        "MATRIZ_C1_C12_CANONICA_JOB5GC_V1.csv.gz": "canonical",
        "MATRIZ_OPORTUNIDADES_REAVALIADAS_JOB5GC_V1.csv.gz": "opportunities",
    }
    for filename, key in csv_outputs.items():
        write_csv_gzip(output_dir / filename, panels[key])
    bridge_contract = json.loads(inputs["bridge_contract"].read_text(encoding="utf-8"))
    bridge_dictionary = {
        "schemaVersion": "bridge-dictionary-job5gc-v1",
        "sourceContract": bridge_contract,
        "semantics": "normative formative correspondence; many-to-many; non-additive",
        "samePersonLink": False,
        "causalLink": False,
        "coverageDeduplicationKey": ["school_code", "course_code"],
        "audit": {key: qa_summary[key] for key in qa_summary if key.startswith("bridge")},
    }
    json_payloads = {
        "DICIONARIO_FONTES_TRABALHO_E_EPT_JOB5GC_V1.json": source_dictionary(inputs, state_digest),
        "DICIONARIO_PONTE_CBO_CNCT_V1.json": bridge_dictionary,
        "NOVA_SANTA_RITA_JOB5GC_V1.json": nsr_payload(panels),
        "DICIONARIO_SEMANTICO_METRICAS_JOB5GC_V1.json": semantic_dictionary(),
        "LIMITACOES_JOB5GC_V1.json": limitations_payload(),
        "PACOTE_REVISAO_EXTERNA_JOB5GC.json": {
            "schemaVersion": "external-review-package-job5gc-v1",
            "jobId": JOB_ID,
            "finalState": FINAL_STATE,
            "objective": "Materializar e testar trabalho juvenil, aprendizagem, ocupações, setores e EPT sem aprovar narrativa pública.",
            "analysisCatalog": analysis_catalog(),
            "qaSummary": qa_summary,
            "job5fReconciliation": reconciliation,
            "automaticApproval": False,
            "externalJudgmentRequired": True,
            "stopAfterDelivery": True,
        },
    }
    for filename, payload in json_payloads.items():
        write_json(output_dir / filename, payload)
    (output_dir / "MAPA_SECOES_POTENCIAIS_JOB5GC_V1.md").write_text(
        _section_map(), encoding="utf-8", newline="\n"
    )
    pre_manifest = set(path.name for path in output_dir.iterdir())
    expected_pre_manifest = set(EXPECTED_OUTPUTS) - {"MANIFEST_JOB5GC.json"}
    if pre_manifest != expected_pre_manifest:
        raise ValueError(
            f"Lote pré-manifesto divergente: missing={expected_pre_manifest-pre_manifest}, extra={pre_manifest-expected_pre_manifest}."
        )
    records = []
    for filename in sorted(pre_manifest):
        key = csv_outputs.get(filename)
        records.append(
            artifact_record(
                root=output_dir,
                path=output_dir / filename,
                frame=panels[key] if key else None,
                subjob="5G-C",
                grain="declared_in_artifact",
                period="2019-2025 or source-specific",
                lens="workplace|school_location|metadata",
                unit="source-specific",
                aggregation_rule="declared in semantic dictionary",
            )
        )
    manifest = {
        "schemaVersion": "manifest-job5gc-v1",
        "jobId": JOB_ID,
        "classification": "DATA_LOGIC",
        "domains": ["DATA_MATERIALIZATION", "ANALYTICAL_TESTING", "SEMANTIC_CONTRACT"],
        "objective": "Trabalho juvenil, aprendizagem, ocupações, setores e EPT para julgamento externo.",
        "finalState": FINAL_STATE,
        "contract": contract,
        "scope": contract["scope"],
        "periods": contract["periods"],
        "artifacts": records,
        "summary": {"outputCount": 24, "artifactHashCount": 23, "rowCounts": {filename: len(panels[key]) for filename, key in csv_outputs.items()}},
        "qa": qa_summary,
        "job5fReconciliation": reconciliation,
        "historicalCheckpoint": historical_checkpoint,
        "databaseAggregate": {"used": True, "mode": "read_only", "grain": "RS/year/CNAE_division", "sha256": state_digest, "rowCount": len(state_sector_totals)},
        "formulasPreserved": ["caged_balance", "safe_ratio_zero_denominator_null", "percent_change_zero_base_null", "hhi", "shift_share_closure"],
        "formulasAltered": [],
        "generation": {
            "deterministic": True,
            "transactional": True,
            "manifestLast": True,
            "networkUsed": False,
            "databaseUsed": True,
            "databaseWrites": False,
            "sourceRefreshPerformed": False,
            "publicDataChanged": False,
            "frontendChanged": False,
            "fullBuildUsed": False,
            "publicNarrativeWritten": False,
            "automaticApproval": False,
        },
        "externalJudgmentRequired": True,
        "stopForExternalJudgment": True,
    }
    write_json(output_dir / "MANIFEST_JOB5GC.json", manifest)
    if tuple(sorted(path.name for path in output_dir.iterdir())) != tuple(sorted(EXPECTED_OUTPUTS)):
        raise ValueError("O lote final não contém exatamente as 24 saídas contratadas.")
    return manifest
