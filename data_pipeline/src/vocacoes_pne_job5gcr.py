"""Correção dirigida do Job 5G-C: códigos, consumo seguro e seleção substantiva.

O módulo lê os 24 artefatos congelados do Job 5G-C e as fontes locais já
materializadas. Banco e rede não são acessados aqui; agregados estaduais e
catálogos locais são recebidos pelo chamador. Nenhuma função conhece ou escreve
``public/data``.
"""

from __future__ import annotations

from collections import Counter
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
from src.vocacoes_pne_job5gc import (
    _endpoint_changes,
    build_apprentice_axes,
    build_bridge_audit,
    build_concentration,
    build_ept,
    build_rais_youth,
    build_shift_share,
    build_youth_schooling,
    empty_adult_context,
)


JOB_ID = "v7-job5gcr"
SCHEMA_VERSION = "vocacoes-pne-v7-job5gcr-v1"
FINAL_STATE = "JOB_5GC_R_READY_FOR_EXTERNAL_JUDGMENT"
NSR_CODE = "4313375"
REGION_ENTITY_ID = "REGION_VALE_DO_SINOS"
STATE_ENTITY_ID = "STATE_RS"
SOURCE_JOB5GC_OUTPUTS = (
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
EXPECTED_OUTPUTS = (
    "ERRATA_METODOLOGICA_JOB5GC_V7.md",
    "ERRATA_ANCHOR_AUXILIAR_LOGISTICA_JOB5F_V7.md",
    "DICIONARIO_FONTES_TRABALHO_E_EPT_JOB5GC_V1_1.json",
    "DICIONARIO_CODIGOS_TRABALHO_JOB5GCR_V1.json",
    "DICIONARIO_SEMANTICO_METRICAS_JOB5GC_V1_1.json",
    "PAINEL_RAIS_TRABALHO_JUVENIL_V1_1.csv.gz",
    "PAINEL_CAGED_JUVENIL_FLUXOS_V1_1.csv.gz",
    "PAINEL_CAGED_JUVENIL_AGREGADO_SEGURO_V1.csv.gz",
    "PAINEL_APRENDIZAGEM_PROFISSIONAL_V1_1.csv.gz",
    "PAINEL_ESCOLARIDADE_VINCULOS_JOVENS_V1_1.csv.gz",
    "PAINEL_OCUPACOES_RAIS_ESTOQUE_V1.csv.gz",
    "PAINEL_SETORES_RAIS_ESTOQUE_V1.csv.gz",
    "PAINEL_OCUPACOES_CAGED_FLUXOS_V1.csv.gz",
    "PAINEL_SETORES_CAGED_FLUXOS_V1.csv.gz",
    "PAINEL_CAGED_SALDO_LIQUIDO_INTERNO_V1.csv.gz",
    "PAINEL_EPT_OFERTA_TOTAL_V1_1.csv.gz",
    "DICIONARIO_PONTE_CBO_CNCT_V1_1.json",
    "PAINEL_PONTE_CBO_CNCT_AUDITADA_V1_1.csv.gz",
    "PAINEL_APRENDIZAGEM_OCUPACOES_EIXOS_V1_1.csv.gz",
    "PAINEL_CONCENTRACAO_TRABALHO_EPT_V1_1.csv.gz",
    "PAINEL_SHIFT_SHARE_SETORIAL_V1_1.csv.gz",
    "PAINEL_ESCOLARIDADE_ADULTA_TRABALHO_CONTEXTUAL_V1_1.csv.gz",
    "PAINEL_TRABALHO_JUVENIL_EDUCACAO_CONTEXTO_V1_1.csv.gz",
    "MATRIZ_VINCULOS_PNE_PME_JOB5GC_V1_1.csv.gz",
    "NOVA_SANTA_RITA_JOB5GC_V1_1.json",
    "MATRIZ_CATALOGO_FATOS_NOVA_SANTA_RITA_JOB5GCR_V1.csv.gz",
    "MATRIZ_QA_JOB5GC_V1_1.csv.gz",
    "MATRIZ_C1_C12_CANONICA_JOB5GC_V1_1.csv.gz",
    "MATRIZ_OPORTUNIDADES_REAVALIADAS_JOB5GC_V1_1.csv.gz",
    "MAPA_SECOES_POTENCIAIS_JOB5GC_V1_1.md",
    "LIMITACOES_JOB5GC_V1_1.json",
    "PACOTE_REVISAO_EXTERNA_JOB5GCR.json",
    "MANIFEST_JOB5GCR.json",
)
CANONICAL_CRITERION_STATUSES = frozenset(
    {"SUPPORTED", "PARTIAL", "NOT_SUPPORTED", "NOT_EVALUABLE"}
)
CODE_DTYPES = {
    "municipality_ibge_code": "string",
    "occupation_code": "string",
    "occupation_subgroup_code": "string",
    "cnae_subclass_code": "string",
    "cnae_subclass_code_raw": "string",
    "cnae_division_code": "string",
    "schooling_code": "string",
    "course_code": "string",
    "technological_axis_code": "string",
    "school_code": "string",
    "apprentice_indicator_code": "string",
}


def _read_csv(path: Path) -> pd.DataFrame:
    """Lê códigos como texto antes de qualquer inferência numérica."""

    header = pd.read_csv(path, nrows=0).columns
    dtypes = {key: value for key, value in CODE_DTYPES.items() if key in header}
    return pd.read_csv(path, dtype=dtypes)


def _stable(frame: pd.DataFrame, keys: Sequence[str] | None = None) -> pd.DataFrame:
    if frame.empty:
        return frame.reset_index(drop=True)
    actual = list(keys or frame.columns)
    return frame.sort_values(actual, kind="mergesort", na_position="last").reset_index(
        drop=True
    )


def _numeric(frame: pd.DataFrame, columns: Iterable[str]) -> pd.DataFrame:
    result = frame.copy()
    for column in columns:
        if column in result:
            result[column] = pd.to_numeric(result[column], errors="raise")
    return result


def normalize_numeric_code(
    value: Any, *, width: int, allow_all: bool = True, nullable: bool = False
) -> Any:
    """Normaliza um código textual sem aceitar representação float."""

    if value is None or pd.isna(value):
        if nullable:
            return pd.NA
        raise ValueError("Código obrigatório ausente.")
    text = str(value).strip()
    if allow_all and text == "ALL":
        return "ALL"
    if not text:
        if nullable:
            return pd.NA
        raise ValueError("Código obrigatório vazio.")
    if text.endswith(".0") or not text.isdigit():
        raise ValueError(f"Código não inteiro textual: {text!r}.")
    if len(text) > width:
        raise ValueError(f"Código {text!r} excede largura {width}.")
    return text.zfill(width)


def _normalize_series(
    series: pd.Series, *, width: int, allow_all: bool = True, nullable: bool = False
) -> pd.Series:
    return series.map(
        lambda value: normalize_numeric_code(
            value, width=width, allow_all=allow_all, nullable=nullable
        )
    ).astype("string")


def _entity_id(scope: Any, municipality_code: Any) -> str:
    if scope == "municipality":
        code = normalize_numeric_code(
            municipality_code, width=7, allow_all=False, nullable=False
        )
        require_ibge_code(code)
        return code
    if scope == "region":
        return REGION_ENTITY_ID
    if scope == "state":
        return STATE_ENTITY_ID
    raise ValueError(f"entity_scope não reconhecido: {scope!r}.")


def add_entity_id(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    result["entity_id"] = [
        _entity_id(scope, code)
        for scope, code in zip(
            result["entity_scope"], result.get("municipality_ibge_code", pd.NA)
        )
    ]
    return result


def _safe_ratio_series(
    numerator: pd.Series, denominator: pd.Series, eligible: pd.Series
) -> pd.Series:
    num = pd.to_numeric(numerator, errors="coerce")
    den = pd.to_numeric(denominator, errors="coerce")
    mask = eligible.fillna(False) & num.ge(0) & den.gt(0)
    result = pd.Series(pd.NA, index=numerator.index, dtype="Float64")
    result.loc[mask] = (num.loc[mask] / den.loc[mask]).astype(float)
    return result


def _content_digest(frame: pd.DataFrame) -> str:
    payload = frame.to_csv(index=False, lineterminator="\n", na_rep="null").encode(
        "utf-8"
    )
    return hashlib.sha256(payload).hexdigest()


def verify_original_job5gc(
    source_root: Path, expected_manifest_sha256: str
) -> dict[str, Any]:
    """Lê e verifica integralmente os 24 outputs congelados do Job 5G-C."""

    manifest_path = source_root / "MANIFEST_JOB5GC.json"
    if sha256_file(manifest_path) != expected_manifest_sha256:
        raise ValueError("O manifesto congelado do Job 5G-C divergiu do checkpoint.")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected = {item["path"]: item for item in manifest["artifacts"]}
    actual_names = {path.name for path in source_root.iterdir() if path.is_file()}
    if actual_names != set(SOURCE_JOB5GC_OUTPUTS):
        raise ValueError(
            f"O Job 5G-C não contém os 24 arquivos exatos: {sorted(actual_names)}."
        )
    records: list[dict[str, Any]] = []
    for name in sorted(SOURCE_JOB5GC_OUTPUTS):
        path = source_root / name
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if name in expected:
            item = expected[name]
            if len(raw) != item["byteSize"] or digest != item["sha256"]:
                raise ValueError(f"Artefato congelado divergente: {name}.")
        records.append({"path": name, "byteSize": len(raw), "sha256": digest})
    lines = [f"{row['path']}\t{row['byteSize']}\t{row['sha256']}" for row in records]
    return {
        "fileCount": len(records),
        "byteSize": sum(row["byteSize"] for row in records),
        "sha256": hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest(),
        "manifestSha256": expected_manifest_sha256,
        "files": records,
    }


def verify_checkpoints(repo_root: Path, contract: Mapping[str, Any]) -> None:
    for relative, expected in contract["checkpoints"].items():
        path = repo_root / relative
        if not path.is_file():
            raise FileNotFoundError(f"Checkpoint ausente: {relative}.")
        actual = sha256_file(path)
        if actual != expected:
            raise ValueError(f"Checkpoint divergente em {relative}: {actual} != {expected}.")


def build_corrected_caged_detailed(original: pd.DataFrame) -> pd.DataFrame:
    """Preserva a camada detalhada, normaliza códigos e invalida shares inseguros."""

    panel = _numeric(
        original,
        [
            "year",
            "month",
            "admissions",
            "dismissals",
            "balance",
            "regional_admissions",
            "regional_dismissals",
            "annual_admissions_same_contract",
        ],
    )
    panel["cnae_subclass_code_raw"] = panel["cnae_subclass_code"].astype("string")
    panel["cnae_subclass_code"] = _normalize_series(
        panel["cnae_subclass_code_raw"], width=7
    )
    panel["cnae_division_code"] = panel["cnae_subclass_code"].map(
        lambda value: "ALL" if value == "ALL" else str(value)[:2]
    ).astype("string")
    panel["occupation_code_raw"] = panel["occupation_code"].astype("string")
    panel["occupation_code"] = _normalize_series(panel["occupation_code_raw"], width=6)
    panel["occupation_subgroup_code"] = panel["occupation_code"].map(
        lambda value: "ALL" if value == "ALL" else str(value)[:2]
    ).astype("string")
    municipal = panel["municipality_ibge_code"].notna()
    panel.loc[municipal, "municipality_ibge_code"] = _normalize_series(
        panel.loc[municipal, "municipality_ibge_code"],
        width=7,
        allow_all=False,
    )
    panel = add_entity_id(panel)
    panel["time_grain"] = panel["time_grain"].replace(
        {"month": "monthly_flow", "year": "annual_flow"}
    )
    negative_row = panel["admissions"].lt(0) | panel["dismissals"].lt(0)
    panel["negative_adjustment_present"] = negative_row
    detailed_keys = [
        "entity_id",
        "year",
        "age_group",
        "occupation_code",
        "cnae_subclass_code",
        "schooling_code",
        "apprentice_indicator_code",
    ]
    monthly = panel[panel["time_grain"].eq("monthly_flow")]
    annual_negative = (
        monthly.groupby(detailed_keys, dropna=False)["negative_adjustment_present"]
        .any()
        .rename("annual_negative_adjustment_present")
        .reset_index()
    )
    panel = panel.merge(annual_negative, on=detailed_keys, how="left", validate="many_to_one")
    annual_mask = panel["time_grain"].eq("annual_flow")
    panel.loc[annual_mask, "negative_adjustment_present"] = panel.loc[
        annual_mask, "annual_negative_adjustment_present"
    ].fillna(panel.loc[annual_mask, "negative_adjustment_present"])
    comparison_keys = [
        "year",
        "month",
        "time_grain",
        "age_group",
        "occupation_code",
        "cnae_subclass_code",
        "schooling_code",
        "apprentice_indicator_code",
    ]
    # A linha regional já é agregada e pode ocultar uma célula municipal
    # ajustada negativa. Propague a presença do componente antes de calcular
    # qualquer razão regional ou composição do próprio Vale.
    regional_member_negative = (
        panel[panel["entity_scope"].eq("municipality")]
        .groupby(comparison_keys, as_index=False, dropna=False)[
            "negative_adjustment_present"
        ]
        .any()
        .rename(
            columns={
                "negative_adjustment_present": (
                    "regional_member_negative_adjustment_present"
                )
            }
        )
    )
    panel = panel.merge(
        regional_member_negative,
        on=comparison_keys,
        how="left",
        validate="many_to_one",
    )
    region_mask = panel["entity_scope"].eq("region")
    panel.loc[region_mask, "negative_adjustment_present"] = (
        panel.loc[region_mask, "negative_adjustment_present"].fillna(False).astype(bool)
        | panel.loc[
            region_mask, "regional_member_negative_adjustment_present"
        ].fillna(False).astype(bool)
    )
    composition_keys = [
        "entity_id",
        "year",
        "month",
        "time_grain",
        "age_group",
    ]
    group_negative = panel.groupby(composition_keys, dropna=False)[
        "negative_adjustment_present"
    ].transform("any")
    admission_total = panel.groupby(composition_keys, dropna=False)["admissions"].transform(
        "sum"
    )
    dismissal_total = panel.groupby(composition_keys, dropna=False)["dismissals"].transform(
        "sum"
    )
    base_eligible = ~group_negative
    panel["admission_composition_share"] = _safe_ratio_series(
        panel["admissions"], admission_total, base_eligible
    )
    panel["dismissal_composition_share"] = _safe_ratio_series(
        panel["dismissals"], dismissal_total, base_eligible
    )
    panel["admission_composition_share_eligible"] = (
        base_eligible & panel["admissions"].ge(0) & admission_total.gt(0)
    )
    panel["dismissal_composition_share_eligible"] = (
        base_eligible & panel["dismissals"].ge(0) & dismissal_total.gt(0)
    )
    region = (
        panel[panel["entity_scope"].eq("municipality")]
        .groupby(comparison_keys, as_index=False, dropna=False)
        .agg(
            safe_regional_admissions=("admissions", "sum"),
            safe_regional_dismissals=("dismissals", "sum"),
            regional_negative_adjustment_present=(
                "negative_adjustment_present",
                "any",
            ),
        )
    )
    panel = panel.merge(region, on=comparison_keys, how="left", validate="many_to_one")
    regional_eligible = (
        panel["entity_scope"].eq("municipality")
        & ~panel["negative_adjustment_present"]
        & ~panel["regional_negative_adjustment_present"].fillna(True)
    )
    panel["municipal_share_of_regional_admissions"] = _safe_ratio_series(
        panel["admissions"], panel["safe_regional_admissions"], regional_eligible
    )
    panel["municipal_share_of_regional_dismissals"] = _safe_ratio_series(
        panel["dismissals"], panel["safe_regional_dismissals"], regional_eligible
    )
    panel["municipal_share_of_regional_admissions_eligible"] = (
        regional_eligible
        & panel["admissions"].ge(0)
        & panel["safe_regional_admissions"].gt(0)
    )
    panel["municipal_share_of_regional_dismissals_eligible"] = (
        regional_eligible
        & panel["dismissals"].ge(0)
        & panel["safe_regional_dismissals"].gt(0)
    )
    annual_values = panel[panel["time_grain"].eq("annual_flow")][
        detailed_keys + ["admissions", "negative_adjustment_present"]
    ].rename(
        columns={
            "admissions": "safe_annual_admissions_same_contract",
            "negative_adjustment_present": "annual_negative_for_share",
        }
    )
    panel = panel.merge(annual_values, on=detailed_keys, how="left", validate="many_to_one")
    seasonality_eligible = (
        panel["time_grain"].eq("monthly_flow")
        & ~panel["negative_adjustment_present"]
        & ~panel["annual_negative_for_share"].fillna(True)
    )
    panel["seasonality_admission_share_of_annual"] = _safe_ratio_series(
        panel["admissions"],
        panel["safe_annual_admissions_same_contract"],
        seasonality_eligible,
    )
    panel["seasonality_admission_share_of_annual_eligible"] = (
        seasonality_eligible
        & panel["admissions"].ge(0)
        & panel["safe_annual_admissions_same_contract"].gt(0)
    )
    eligibility_columns = [
        "admission_composition_share_eligible",
        "dismissal_composition_share_eligible",
        "municipal_share_of_regional_admissions_eligible",
        "municipal_share_of_regional_dismissals_eligible",
        "seasonality_admission_share_of_annual_eligible",
    ]
    panel["share_eligible"] = panel[eligibility_columns].any(axis=1)
    panel["share_status"] = panel["share_eligible"].map(
        lambda value: (
            "ELIGIBLE" if value else "ADJUSTED_CELL_NOT_SHARE_ELIGIBLE"
        )
    )
    panel["adjusted_component_status"] = "NONNEGATIVE_ADJUSTED_COMPONENTS"
    panel.loc[
        panel["negative_adjustment_present"], "adjusted_component_status"
    ] = "NEGATIVE_ADJUSTED_COMPONENT"
    panel["visual_aggregation_eligible"] = False
    panel["aggregation_scope"] = "detailed_cross_classification_qa_only"
    drop_columns = [
        "annual_negative_adjustment_present",
        "regional_member_negative_adjustment_present",
        "safe_regional_admissions",
        "safe_regional_dismissals",
        "regional_negative_adjustment_present",
        "safe_annual_admissions_same_contract",
        "annual_negative_for_share",
    ]
    panel = panel.drop(columns=drop_columns)
    return _stable(
        panel,
        [
            "entity_scope",
            "entity_id",
            "year",
            "time_grain",
            "month",
            "age_group",
            "occupation_code",
            "cnae_subclass_code",
            "schooling_code",
            "apprentice_indicator_code",
        ],
    )


def build_safe_caged_aggregate(detailed: pd.DataFrame) -> pd.DataFrame:
    """Agrega fluxos em grãos exclusivos e seguros para consumo visual."""

    monthly = detailed[
        detailed["time_grain"].eq("monthly_flow")
        & detailed["entity_scope"].eq("municipality")
    ].copy()
    keys = [
        "entity_scope",
        "entity_id",
        "municipality_ibge_code",
        "municipality_name",
        "year",
        "month",
        "age_group",
        "apprentice_indicator_code",
    ]
    municipal = monthly.groupby(keys, as_index=False, dropna=False).agg(
        admissions=("admissions", "sum"),
        dismissals=("dismissals", "sum"),
        negative_adjustment_present=("negative_adjustment_present", "any"),
    )
    municipal["aggregation_scope"] = "apprentice_status"
    region_keys = [
        "year", "month", "age_group", "apprentice_indicator_code"
    ]
    region = municipal.groupby(region_keys, as_index=False, dropna=False).agg(
        admissions=("admissions", "sum"),
        dismissals=("dismissals", "sum"),
        negative_adjustment_present=("negative_adjustment_present", "any"),
    )
    region["entity_scope"] = "region"
    region["entity_id"] = REGION_ENTITY_ID
    region["municipality_ibge_code"] = pd.NA
    region["municipality_name"] = "Vale do Sinos"
    region["aggregation_scope"] = "apprentice_status"
    state = detailed[
        detailed["time_grain"].eq("monthly_flow")
        & detailed["entity_scope"].eq("state")
    ].groupby(["year", "month", "age_group"], as_index=False, dropna=False).agg(
        admissions=("admissions", "sum"),
        dismissals=("dismissals", "sum"),
        negative_adjustment_present=("negative_adjustment_present", "any"),
    )
    state["entity_scope"] = "state"
    state["entity_id"] = STATE_ENTITY_ID
    state["municipality_ibge_code"] = pd.NA
    state["municipality_name"] = "Rio Grande do Sul"
    state["apprentice_indicator_code"] = "ALL"
    state["aggregation_scope"] = "all_apprentice_status"
    category = pd.concat([municipal, region], ignore_index=True, sort=False)
    total_keys = [
        "entity_scope",
        "entity_id",
        "municipality_ibge_code",
        "municipality_name",
        "year",
        "month",
        "age_group",
    ]
    totals = category.groupby(total_keys, as_index=False, dropna=False).agg(
        admissions=("admissions", "sum"),
        dismissals=("dismissals", "sum"),
        negative_adjustment_present=("negative_adjustment_present", "any"),
    )
    totals["apprentice_indicator_code"] = "ALL"
    totals["aggregation_scope"] = "all_apprentice_status"
    monthly_safe = pd.concat([category, totals, state], ignore_index=True, sort=False)
    monthly_safe["time_grain"] = "monthly_flow"
    annual_keys = [
        "entity_scope",
        "entity_id",
        "municipality_ibge_code",
        "municipality_name",
        "year",
        "age_group",
        "apprentice_indicator_code",
        "aggregation_scope",
    ]
    annual = monthly_safe.groupby(annual_keys, as_index=False, dropna=False).agg(
        admissions=("admissions", "sum"),
        dismissals=("dismissals", "sum"),
        negative_adjustment_present=("negative_adjustment_present", "any"),
    )
    annual["month"] = pd.NA
    annual["time_grain"] = "annual_flow"
    panel = pd.concat([monthly_safe, annual], ignore_index=True, sort=False)
    panel["balance"] = panel["admissions"] - panel["dismissals"]
    if panel[["admissions", "dismissals"]].lt(0).any().any():
        raise ValueError("O painel Caged seguro contém componente agregado negativo.")
    total_lookup = panel[panel["aggregation_scope"].eq("all_apprentice_status")][
        [
            "entity_id",
            "year",
            "month",
            "time_grain",
            "age_group",
            "admissions",
            "dismissals",
            "negative_adjustment_present",
        ]
    ].rename(
        columns={
            "admissions": "all_admissions",
            "dismissals": "all_dismissals",
            "negative_adjustment_present": "all_negative_adjustment_present",
        }
    )
    join_keys = ["entity_id", "year", "month", "time_grain", "age_group"]
    panel = panel.merge(total_lookup, on=join_keys, how="left", validate="many_to_one")
    composition_eligible = (
        panel["aggregation_scope"].eq("apprentice_status")
        & ~panel["negative_adjustment_present"]
        & ~panel["all_negative_adjustment_present"].fillna(True)
    )
    panel["admission_composition_share"] = _safe_ratio_series(
        panel["admissions"], panel["all_admissions"], composition_eligible
    )
    panel["dismissal_composition_share"] = _safe_ratio_series(
        panel["dismissals"], panel["all_dismissals"], composition_eligible
    )
    comparison_keys = [
        "year",
        "month",
        "time_grain",
        "age_group",
        "apprentice_indicator_code",
        "aggregation_scope",
    ]
    region_lookup = panel[panel["entity_scope"].eq("region")][
        comparison_keys
        + ["admissions", "dismissals", "negative_adjustment_present"]
    ].rename(
        columns={
            "admissions": "regional_admissions",
            "dismissals": "regional_dismissals",
            "negative_adjustment_present": "regional_negative_adjustment_present",
        }
    )
    panel = panel.merge(region_lookup, on=comparison_keys, how="left", validate="many_to_one")
    regional_eligible = (
        panel["entity_scope"].eq("municipality")
        & ~panel["negative_adjustment_present"]
        & ~panel["regional_negative_adjustment_present"].fillna(True)
    )
    panel["municipal_share_of_regional_admissions"] = _safe_ratio_series(
        panel["admissions"], panel["regional_admissions"], regional_eligible
    )
    panel["municipal_share_of_regional_dismissals"] = _safe_ratio_series(
        panel["dismissals"], panel["regional_dismissals"], regional_eligible
    )
    panel["share_eligible"] = composition_eligible | regional_eligible
    panel["share_status"] = panel["share_eligible"].map(
        lambda value: "ELIGIBLE" if value else "NOT_APPLICABLE_OR_ADJUSTED_CELL_NOT_SHARE_ELIGIBLE"
    )
    panel["adjusted_component_status"] = panel[
        "negative_adjustment_present"
    ].map(
        lambda value: "CONTAINS_NEGATIVE_ADJUSTED_COMPONENT"
        if value
        else "NONNEGATIVE_AGGREGATE"
    )
    panel["visual_aggregation_eligible"] = ~panel["negative_adjustment_present"]
    panel["source"] = "Novo Caged; eventos ajustados MOV+FOR-EXC"
    panel["territorial_lens"] = "workplace"
    panel["flow_not_stock"] = True
    panel = panel.drop(
        columns=[
            "all_admissions",
            "all_dismissals",
            "all_negative_adjustment_present",
            "regional_negative_adjustment_present",
        ]
    )
    return _stable(
        panel,
        [
            "entity_scope",
            "entity_id",
            "year",
            "time_grain",
            "month",
            "age_group",
            "aggregation_scope",
            "apprentice_indicator_code",
        ],
    )


def _label_available(value: Any) -> bool:
    return value is not None and not pd.isna(value) and bool(str(value).strip()) and "�" not in str(value)


def _lookup(frame: pd.DataFrame, code_column: str, label_column: str) -> dict[str, Any]:
    if frame.empty:
        return {}
    pairs = frame[[code_column, label_column]].drop_duplicates()
    conflicts = pairs.groupby(code_column, dropna=False)[label_column].nunique(dropna=False)
    if (conflicts > 1).any():
        codes = conflicts[conflicts > 1].index.astype(str).tolist()[:10]
        raise ValueError(f"Rótulos conflitantes para {code_column}: {codes}.")
    return {
        str(row[code_column]): row[label_column]
        for row in pairs.to_dict("records")
    }


def build_apprentice_panel(
    detailed: pd.DataFrame, safe: pd.DataFrame
) -> pd.DataFrame:
    annual = detailed[
        detailed["time_grain"].eq("annual_flow")
        & detailed["apprentice_indicator_code"].eq("1")
    ].copy()
    detail_keys = [
        "entity_scope",
        "entity_id",
        "municipality_ibge_code",
        "municipality_name",
        "year",
        "age_group",
        "occupation_code",
        "occupation_subgroup_code",
        "cnae_subclass_code_raw",
        "cnae_subclass_code",
        "cnae_division_code",
    ]
    panel = annual.groupby(detail_keys, as_index=False, dropna=False).agg(
        admissions=("admissions", "sum"),
        dismissals=("dismissals", "sum"),
        negative_adjustment_present=("negative_adjustment_present", "any"),
    )
    panel["aggregation_scope"] = "occupation_cnae_detail_qa_only"
    totals = safe[
        safe["time_grain"].eq("annual_flow")
        & safe["aggregation_scope"].eq("apprentice_status")
        & safe["apprentice_indicator_code"].eq("1")
    ][
        [
            "entity_scope",
            "entity_id",
            "municipality_ibge_code",
            "municipality_name",
            "year",
            "age_group",
            "admissions",
            "dismissals",
            "negative_adjustment_present",
        ]
    ].copy()
    totals["occupation_code"] = "ALL"
    totals["occupation_subgroup_code"] = "ALL"
    totals["cnae_subclass_code_raw"] = "ALL"
    totals["cnae_subclass_code"] = "ALL"
    totals["cnae_division_code"] = "ALL"
    totals["aggregation_scope"] = "all_apprentice_events"
    panel = pd.concat([panel, totals], ignore_index=True, sort=False)
    panel["balance"] = panel["admissions"] - panel["dismissals"]
    youth_totals = safe[
        safe["time_grain"].eq("annual_flow")
        & safe["aggregation_scope"].eq("all_apprentice_status")
    ][
        [
            "entity_id",
            "year",
            "age_group",
            "admissions",
            "negative_adjustment_present",
        ]
    ].rename(
        columns={
            "admissions": "youth_admissions_same_grain",
            "negative_adjustment_present": "youth_negative_adjustment_present",
        }
    )
    panel = panel.merge(
        youth_totals,
        on=["entity_id", "year", "age_group"],
        how="left",
        validate="many_to_one",
    )
    total_row = panel["aggregation_scope"].eq("all_apprentice_events")
    share_eligible = (
        total_row
        & ~panel["negative_adjustment_present"]
        & ~panel["youth_negative_adjustment_present"].fillna(True)
    )
    panel["share_of_youth_admission_events_classified_as_apprentice"] = _safe_ratio_series(
        panel["admissions"], panel["youth_admissions_same_grain"], share_eligible
    )
    panel["share_eligible"] = share_eligible
    panel["share_status"] = share_eligible.map(
        lambda value: "ELIGIBLE" if value else "ADJUSTED_CELL_NOT_SHARE_ELIGIBLE"
    )
    panel["adjusted_component_status"] = panel[
        "negative_adjustment_present"
    ].map(
        lambda value: "CONTAINS_NEGATIVE_ADJUSTED_COMPONENT"
        if value
        else "NONNEGATIVE_ADJUSTED_COMPONENTS"
    )
    panel["visual_aggregation_eligible"] = total_row & ~panel[
        "negative_adjustment_present"
    ]
    panel["unit"] = "adjusted_events"
    panel["source"] = "Novo Caged"
    panel["territorial_lens"] = "workplace"
    panel["flow_not_stock"] = True
    panel["source_measure"] = "adjusted_admission_dismissal_events"
    panel["stock_or_flow"] = "FLOW"
    panel["unique_person_count_allowed"] = False
    return _stable(
        panel,
        [
            "entity_scope",
            "entity_id",
            "year",
            "age_group",
            "aggregation_scope",
            "occupation_code",
            "cnae_subclass_code",
        ],
    )


def build_schooling_panel(
    cube: pd.DataFrame, region_codes: set[str], schooling_catalog: pd.DataFrame
) -> pd.DataFrame:
    cube = _numeric(cube, ["year", "active_bonds"])
    cube.loc[cube["municipality_ibge_code"].notna(), "municipality_ibge_code"] = _normalize_series(
        cube.loc[cube["municipality_ibge_code"].notna(), "municipality_ibge_code"],
        width=7,
        allow_all=False,
    )
    panel = build_youth_schooling(cube, region_codes)
    panel = add_entity_id(panel)
    local_labels = _lookup(
        schooling_catalog, "schooling_code", "schooling_label"
    )
    panel["schooling_code_raw"] = panel["schooling_code"].astype("string")
    panel["local_unversioned_schooling_label"] = panel["schooling_code"].map(
        local_labels
    )
    panel["schooling_label"] = pd.NA
    panel["dictionary_status"] = "TECHNICAL_RAW_CODE_ONLY"
    panel["visual_eligible"] = False
    panel["recoding_coverage_share"] = 0.0
    panel["raw_code_preserved"] = True
    return _stable(
        panel,
        [
            "entity_scope",
            "entity_id",
            "year",
            "age_group",
            "schooling_code",
        ],
    )


def _change_panel(
    data: pd.DataFrame,
    *,
    code_column: str,
    value_column: str,
    label_map: Mapping[str, Any],
    initial_year: int,
    final_year: int,
    source: str,
    measure: str,
    stock_or_flow: str,
    population_scope: str,
    extra_keys: Sequence[str] = (),
    negative_column: str | None = None,
) -> pd.DataFrame:
    base_keys = [
        "entity_scope",
        "entity_id",
        "municipality_ibge_code",
        "municipality_name",
        *extra_keys,
        code_column,
    ]
    annual = data.groupby(base_keys + ["year"], as_index=False, dropna=False).agg(
        value=(value_column, "sum"),
        negative_adjustment_present=(
            negative_column or value_column,
            "any" if negative_column else "size",
        ),
    )
    if negative_column is None:
        annual["negative_adjustment_present"] = False
    observed = annual.groupby(base_keys, as_index=False, dropna=False)["year"].nunique().rename(
        columns={"year": "observed_year_count"}
    )
    changes = _endpoint_changes(
        annual,
        keys=base_keys,
        value="value",
        initial_year=initial_year,
        final_year=final_year,
    )
    negative = annual.groupby(base_keys, as_index=False, dropna=False)[
        "negative_adjustment_present"
    ].any()
    changes = changes.merge(observed, on=base_keys, how="left", validate="one_to_one")
    changes = changes.merge(negative, on=base_keys, how="left", validate="one_to_one")
    changes = changes.rename(columns={code_column: "dimension_code"})
    changes["dimension_label"] = changes["dimension_code"].astype(str).map(label_map)
    changes["label_available"] = changes["dimension_label"].map(_label_available)
    changes["source"] = source
    changes["measure"] = measure
    changes["stock_or_flow"] = stock_or_flow
    changes["population_scope"] = population_scope
    changes["territorial_lens"] = "workplace"
    changes["period_coverage_status"] = changes["observed_year_count"].map(
        lambda count: f"complete_{initial_year}_{final_year}"
        if int(count) == final_year - initial_year + 1
        else f"partial_{initial_year}_{final_year}"
    )
    changes["small_volume_sensitive"] = (
        changes["initial_value"].abs().lt(20)
        & changes["final_value"].abs().lt(20)
    )
    regional_keys = [*extra_keys, "dimension_code"]
    region = changes[changes["entity_scope"].eq("region")][
        regional_keys + ["initial_value", "final_value", "absolute_change"]
    ].rename(
        columns={
            "initial_value": "regional_initial_value",
            "final_value": "regional_final_value",
            "absolute_change": "regional_absolute_change",
        }
    )
    changes = changes.merge(region, on=regional_keys, how="left", validate="many_to_one")
    changes["initial_regional_share"] = [
        safe_ratio(value, total)
        for value, total in zip(
            changes["initial_value"], changes["regional_initial_value"]
        )
    ]
    changes["final_regional_share"] = [
        safe_ratio(value, total)
        for value, total in zip(
            changes["final_value"], changes["regional_final_value"]
        )
    ]
    changes["selection_eligible"] = (
        ~changes["small_volume_sensitive"]
        & changes["label_available"]
        & ~changes["negative_adjustment_present"].fillna(False)
    )
    return changes


def build_rais_stock_panels(
    occupations: pd.DataFrame,
    cnae_catalog: pd.DataFrame,
    occupation_catalog: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    data = _numeric(occupations, ["year", "active_bonds"])
    municipal = data["municipality_ibge_code"].notna()
    data.loc[municipal, "municipality_ibge_code"] = _normalize_series(
        data.loc[municipal, "municipality_ibge_code"],
        width=7,
        allow_all=False,
    )
    data["cnae_subclass_code_raw"] = data["cnae_subclass_code"].astype("string")
    data["cnae_subclass_code"] = _normalize_series(
        data["cnae_subclass_code_raw"], width=7
    )
    data["cnae_division_code"] = data["cnae_subclass_code"].str[:2]
    data["occupation_code_raw"] = data["occupation_code"].astype("string")
    # A fonte contém poucas linhas sem CBO. ``null`` significa classificação
    # ocupacional indisponível: permanece no universo setorial, não recebe um
    # código inventado e fica inelegível para seleção ocupacional.
    data["occupation_code"] = _normalize_series(
        data["occupation_code_raw"], width=6, nullable=True
    )
    data["occupation_subgroup_code"] = data["occupation_code"].str[:2]
    data = add_entity_id(data)
    occupation_labels = _lookup(
        occupation_catalog, "occupation_code", "occupation_label"
    )
    division_labels = _lookup(
        cnae_catalog, "cnae_division_code", "cnae_division_label"
    )
    occupation_panel = _change_panel(
        data,
        code_column="occupation_code",
        value_column="active_bonds",
        label_map=occupation_labels,
        initial_year=2019,
        final_year=2025,
        source="RAIS all ages",
        measure="active_bonds",
        stock_or_flow="STOCK",
        population_scope="all_ages",
    )
    occupation_panel["occupation_code"] = occupation_panel["dimension_code"]
    occupation_panel["occupation_subgroup_code"] = occupation_panel[
        "occupation_code"
    ].str[:2]
    occupation_panel["analysis_id"] = "D2_OCUPACOES_RAIS_ESTOQUE_TODAS_IDADES_V1"
    sector_panel = _change_panel(
        data,
        code_column="cnae_division_code",
        value_column="active_bonds",
        label_map=division_labels,
        initial_year=2019,
        final_year=2025,
        source="RAIS all ages",
        measure="active_bonds",
        stock_or_flow="STOCK",
        population_scope="all_ages",
    )
    sector_panel["cnae_division_code"] = sector_panel["dimension_code"]
    sector_panel["analysis_id"] = "D2_SETORES_RAIS_ESTOQUE_TODAS_IDADES_V1"
    return (
        _stable(occupation_panel, ["entity_scope", "entity_id", "dimension_code"]),
        _stable(sector_panel, ["entity_scope", "entity_id", "dimension_code"]),
        data,
    )


def build_caged_flow_panels(
    detailed: pd.DataFrame,
    cnae_catalog: pd.DataFrame,
    occupation_catalog: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    annual = detailed[
        detailed["time_grain"].eq("annual_flow")
        & detailed["entity_scope"].isin(["municipality", "region"])
        & ~detailed["occupation_code"].eq("ALL")
    ].copy()
    occupation_labels = _lookup(
        occupation_catalog, "occupation_code", "occupation_label"
    )
    division_labels = _lookup(
        cnae_catalog, "cnae_division_code", "cnae_division_label"
    )
    occupation_parts = []
    sector_parts = []
    for measure in ("admissions", "dismissals"):
        occupation_parts.append(
            _change_panel(
                annual,
                code_column="occupation_code",
                value_column=measure,
                label_map=occupation_labels,
                initial_year=2020,
                final_year=2025,
                source="Novo Caged youth",
                measure=measure,
                stock_or_flow="FLOW",
                population_scope="age_15_24",
                extra_keys=["age_group"],
                negative_column="negative_adjustment_present",
            )
        )
        sector_parts.append(
            _change_panel(
                annual,
                code_column="cnae_division_code",
                value_column=measure,
                label_map=division_labels,
                initial_year=2020,
                final_year=2025,
                source="Novo Caged youth",
                measure=measure,
                stock_or_flow="FLOW",
                population_scope="age_15_24",
                extra_keys=["age_group"],
                negative_column="negative_adjustment_present",
            )
        )
    occupations = pd.concat(occupation_parts, ignore_index=True, sort=False)
    occupations["occupation_code"] = occupations["dimension_code"]
    occupations["occupation_subgroup_code"] = occupations[
        "occupation_code"
    ].str[:2]
    occupations["analysis_id"] = "D2_OCUPACOES_CAGED_FLUXOS_JUVENIS_V1"
    sectors = pd.concat(sector_parts, ignore_index=True, sort=False)
    sectors["cnae_division_code"] = sectors["dimension_code"]
    sectors["analysis_id"] = "D2_SETORES_CAGED_FLUXOS_JUVENIS_V1"
    balance_parts: list[pd.DataFrame] = []
    for universe, frame in (("occupation", occupations), ("sector", sectors)):
        index = [
            "entity_scope",
            "entity_id",
            "municipality_ibge_code",
            "municipality_name",
            "age_group",
            "dimension_code",
            "dimension_label",
            "label_available",
        ]
        pivot = frame.pivot_table(
            index=index,
            columns="measure",
            values=["initial_value", "final_value"],
            aggfunc="first",
        ).reset_index()
        pivot.columns = [
            "_".join(str(part) for part in column if part)
            if isinstance(column, tuple)
            else str(column)
            for column in pivot.columns
        ]
        pivot["initial_value"] = (
            pivot["initial_value_admissions"] - pivot["initial_value_dismissals"]
        )
        pivot["final_value"] = (
            pivot["final_value_admissions"] - pivot["final_value_dismissals"]
        )
        pivot["absolute_change"] = pivot["final_value"] - pivot["initial_value"]
        pivot["percent_change"] = pd.NA
        pivot["dimension"] = universe
        pivot["measure"] = "balance"
        pivot["source"] = "Novo Caged youth"
        pivot["stock_or_flow"] = "FLOW_NET_BALANCE_INTERNAL_ONLY"
        pivot["regional_share_allowed"] = False
        pivot["composition_share_allowed"] = False
        pivot["hhi_allowed"] = False
        pivot["net_change_decomposition_internal_only"] = True
        pivot["share_eligible"] = False
        pivot["visual_aggregation_eligible"] = False
        pivot["analysis_id"] = "D2_CAGED_SALDO_LIQUIDO_INTERNO_V1"
        balance_parts.append(pivot)
    balance = pd.concat(balance_parts, ignore_index=True, sort=False)
    return (
        _stable(
            occupations,
            ["entity_scope", "entity_id", "age_group", "measure", "dimension_code"],
        ),
        _stable(
            sectors,
            ["entity_scope", "entity_id", "age_group", "measure", "dimension_code"],
        ),
        _stable(
            balance,
            ["entity_scope", "entity_id", "age_group", "dimension", "dimension_code"],
        ),
    )


def build_ept_panel(
    offer: pd.DataFrame, coverage: pd.DataFrame, region_codes: set[str]
) -> pd.DataFrame:
    offer = _numeric(offer, ["year", "class_count", "technical_enrollments"])
    coverage = _numeric(
        coverage,
        ["year", "census_technical_enrollments"],
    )
    for frame in (offer, coverage):
        mask = frame["municipality_ibge_code"].notna()
        frame.loc[mask, "municipality_ibge_code"] = _normalize_series(
            frame.loc[mask, "municipality_ibge_code"],
            width=7,
            allow_all=False,
        )
    panel = build_ept(offer, coverage, region_codes)
    panel = add_entity_id(panel)
    panel["course_code"] = panel["course_code"].astype("string")
    panel["technological_axis_code"] = panel["technological_axis_code"].astype(
        "string"
    )
    panel["origin_of_student_available"] = False
    panel["same_person_link"] = False
    panel["causal_link"] = False
    return _stable(
        panel,
        [
            "entity_scope",
            "entity_id",
            "year",
            "grain",
            "school_code",
            "course_code",
        ],
    )


def build_bridge_panels(
    bridge_source: pd.DataFrame,
    apprentice: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    bridge_source = _numeric(
        bridge_source,
        ["year", "class_count", "technical_enrollments", "regional_active_bonds_2025"],
    )
    mask = bridge_source["municipality_ibge_code"].notna()
    bridge_source.loc[mask, "municipality_ibge_code"] = _normalize_series(
        bridge_source.loc[mask, "municipality_ibge_code"],
        width=7,
        allow_all=False,
    )
    subgroup_mask = bridge_source["occupation_subgroup_code"].notna()
    bridge_source.loc[subgroup_mask, "occupation_subgroup_code"] = _normalize_series(
        bridge_source.loc[subgroup_mask, "occupation_subgroup_code"],
        width=2,
        allow_all=False,
    )
    bridge_source["course_code"] = bridge_source["course_code"].astype("string")
    bridge_source["technological_axis_code"] = bridge_source[
        "technological_axis_code"
    ].astype("string")
    bridge = build_bridge_audit(bridge_source)
    bridge["bridge_contract_scope"] = "BRIDGE_CONTRACT_RS"
    bridge["course_offer_scope"] = "VALE_OFFER_2025"
    bridge["course_offer_reference_year"] = 2025
    bridge["local_course_offer_observed"] = bridge[
        "municipality_ibge_code"
    ].eq(NSR_CODE)
    bridge["regional_course_offer_observed"] = True
    bridge["origin_of_student_available"] = False
    bridge["same_person_link"] = False
    bridge["causal_link"] = False
    bridge["additive_across_bridge_rows"] = False
    bridge["entity_scope"] = "municipality"
    bridge = add_entity_id(bridge)
    axes = build_apprentice_axes(apprentice, bridge_source)
    axes["bridge_contract_scope"] = "BRIDGE_CONTRACT_RS"
    axes["course_offer_scope"] = "VALE_OFFER_2025"
    axes["course_offer_reference_year"] = 2025
    axes["local_course_offer_observed"] = axes["municipality_ibge_code"].eq(
        NSR_CODE
    ) & axes["course_code"].notna()
    axes["regional_course_offer_observed"] = axes["course_code"].notna()
    axes["origin_of_student_available"] = False
    axes["same_person_link"] = False
    axes["causal_link"] = False
    axes["additive_across_bridge_rows"] = False
    axes["source_event_preserved"] = True
    return _stable(bridge), _stable(axes)


def build_concentration_panel(
    normalized_occupations: pd.DataFrame,
    ept: pd.DataFrame,
    municipality_names: Mapping[str, str],
    cnae_catalog: pd.DataFrame,
) -> pd.DataFrame:
    panel = build_concentration(normalized_occupations, ept, municipality_names)
    division_labels = _lookup(
        cnae_catalog, "cnae_division_code", "cnae_division_label"
    )
    sector = panel["dimension"].eq("rais_cnae_division_territorial")
    panel["category_label"] = pd.NA
    panel.loc[sector, "category_label"] = panel.loc[sector, "category_code"].astype(
        str
    ).map(division_labels)
    universe = {
        "rais_occupation_subgroup_territorial": "RAIS_STOCK_ALL_AGES_WORKPLACE",
        "rais_cnae_division_territorial": "RAIS_STOCK_ALL_AGES_WORKPLACE",
        "ept_total_territorial": "EPT_ENROLLMENTS_ALL_DEPENDENCIES_SCHOOL_LOCATION",
        "ept_axis_territorial": "EPT_ENROLLMENTS_ALL_DEPENDENCIES_SCHOOL_LOCATION",
    }
    levels = {
        "rais_occupation_subgroup_territorial": "CBO_SUBGROUP",
        "rais_cnae_division_territorial": "CNAE_DIVISION",
        "ept_total_territorial": "EPT_TOTAL",
        "ept_axis_territorial": "CNCT_TECHNOLOGICAL_AXIS",
    }
    panel["hhi_universe"] = panel["dimension"].map(universe)
    panel["hhi_category_level"] = panel["dimension"].map(levels)
    panel["cross_universe_comparison_allowed"] = False
    panel["qualitative_concentration_label_allowed"] = False
    panel["regional_hhi_context_only"] = True
    panel["additive_across_municipality_rows"] = False
    return _stable(
        panel, ["dimension", "category_code", "year", "municipality_ibge_code"]
    )


def build_shift_panel(
    normalized_occupations: pd.DataFrame,
    state_sector_totals: pd.DataFrame,
    state_sector_audit: Mapping[str, Any],
    cnae_catalog: pd.DataFrame,
) -> pd.DataFrame:
    panel = build_shift_share(normalized_occupations, state_sector_totals)
    division_labels = _lookup(
        cnae_catalog, "cnae_division_code", "cnae_division_label"
    )
    panel["cnae_division_label"] = panel["cnae_division_code"].astype(str).map(
        division_labels
    )
    panel["label_available"] = panel["cnae_division_label"].map(_label_available)
    panel["reference_total_scope"] = state_sector_audit["referenceTotalScope"]
    panel["analyzed_sector_scope"] = state_sector_audit["analyzedSectorScope"]
    panel["excluded_sector_codes"] = json.dumps(
        state_sector_audit["excludedSectorCodes"], ensure_ascii=False, sort_keys=True
    )
    panel["excluded_sector_bonds"] = json.dumps(
        state_sector_audit["excludedSectorBonds"], ensure_ascii=False, sort_keys=True
    )
    panel["small_volume_sensitive"] = (
        panel["initial_value"].abs().lt(20) & panel["final_value"].abs().lt(20)
    )
    panel["selection_eligible"] = (
        panel["initial_value"].gt(0)
        & panel["component_status"].eq("observed")
        & ~panel["small_volume_sensitive"]
        & panel["label_available"]
        & panel["closure_residual"].abs().le(1e-7)
    )
    panel["causal_link"] = False
    return _stable(panel, ["municipality_ibge_code", "cnae_division_code"])


def build_parallel_context_panel(
    rais_annual: pd.DataFrame,
    safe_caged: pd.DataFrame,
    apprentice: pd.DataFrame,
    trajectory: pd.DataFrame,
    ept: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    rais = _numeric(rais_annual, ["year", "active_bonds"])
    mask = rais["municipality_ibge_code"].notna()
    rais.loc[mask, "municipality_ibge_code"] = _normalize_series(
        rais.loc[mask, "municipality_ibge_code"], width=7, allow_all=False
    )
    rais = add_entity_id(rais)
    rais = rais.rename(columns={"active_bonds": "value"})
    rais["metric"] = "rais_active_youth_bonds"
    rais["unit"] = "active_bonds"
    rais["source"] = "RAIS"
    rais["education_stage"] = "not_applicable"
    rows.append(rais)
    caged = safe_caged[
        safe_caged["time_grain"].eq("annual_flow")
        & safe_caged["aggregation_scope"].eq("all_apprentice_status")
    ].copy()
    for measure in ("admissions", "dismissals", "balance"):
        part = caged.rename(columns={measure: "value"}).copy()
        part["metric"] = f"caged_youth_{measure}"
        part["unit"] = "adjusted_events"
        part["source"] = "Novo Caged"
        part["education_stage"] = "not_applicable"
        rows.append(part)
    app = apprentice[
        apprentice["aggregation_scope"].eq("all_apprentice_events")
    ].rename(columns={"admissions": "value"}).copy()
    app["metric"] = "caged_apprentice_admissions"
    app["unit"] = "adjusted_events"
    app["source"] = "Novo Caged"
    app["education_stage"] = "not_applicable"
    rows.append(app)
    traj = trajectory[
        trajectory["metric"].isin(["approval_rate_percent", "dropout_rate_percent"])
        & trajectory["stage"].eq("medio")
    ].copy()
    traj["entity_scope"] = "municipality"
    traj["entity_id"] = _normalize_series(
        traj["municipality_ibge_code"], width=7, allow_all=False
    )
    traj["municipality_ibge_code"] = traj["entity_id"]
    traj["age_group"] = pd.NA
    traj["metric"] = "education_" + traj["metric"].astype(str)
    traj["unit"] = "percent"
    traj["source"] = "Indicadores Educacionais/INEP"
    traj["education_stage"] = "high_school"
    rows.append(traj)
    ept_total = ept[ept["grain"].isin(["municipality_total", "region_total"])].copy()
    ept_total = ept_total.rename(columns={"technical_enrollments": "value"})
    ept_total["age_group"] = pd.NA
    ept_total["metric"] = "ept_technical_enrollments"
    ept_total["unit"] = "enrollments"
    ept_total["source"] = "Censo Escolar"
    ept_total["education_stage"] = "technical_education"
    rows.append(ept_total)
    common = [
        "year",
        "entity_scope",
        "entity_id",
        "municipality_ibge_code",
        "municipality_name",
        "age_group",
        "education_stage",
        "value",
        "metric",
        "unit",
        "source",
    ]
    optional = [
        "period_context_flag",
        "period_comparability_note",
        "public_line_continuity_allowed",
    ]
    prepared = []
    for frame in rows:
        current = frame.copy()
        for column in [*common, *optional]:
            if column not in current:
                current[column] = pd.NA
        prepared.append(current[[*common, *optional]])
    panel = pd.concat(prepared, ignore_index=True, sort=False)
    educational = panel["source"].eq("Indicadores Educacionais/INEP")
    atypical = educational & panel["year"].isin([2020, 2021])
    panel.loc[
        atypical, "period_context_flag"
    ] = "ATYPICAL_SERIES_DISCONTINUITY_REQUIRES_CONTEXT"
    panel.loc[
        atypical, "public_line_continuity_allowed"
    ] = False
    panel.loc[
        atypical, "period_comparability_note"
    ] = "2020 e 2021 permanecem anos atípicos; não suavizar nem inferir estabilidade."
    panel["parallel_series_only"] = True
    panel["same_person_link"] = False
    panel["causal_link"] = False
    panel["association_test"] = False
    panel["combined_score"] = False
    panel["territorial_lens"] = panel["source"].map(
        lambda value: "school_location"
        if value in {"Indicadores Educacionais/INEP", "Censo Escolar"}
        else "workplace"
    )
    panel["value_status"] = panel["value"].map(
        lambda value: "unavailable"
        if value is None or pd.isna(value)
        else ("observed_zero" if float(value) == 0 else "observed")
    )
    if panel["entity_id"].isna().any():
        raise ValueError("O contexto paralelo contém identidade territorial nula.")
    return _stable(
        panel, ["entity_scope", "entity_id", "year", "metric", "age_group"]
    )


def _json_safe(value: Any) -> Any:
    if value is None or value is pd.NA:
        return None
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    if hasattr(value, "item"):
        return _json_safe(value.item())
    return value


def _records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    return [_json_safe(row) for row in frame.to_dict("records")]


def analysis_catalog() -> list[dict[str, Any]]:
    rows = [
        ("D2_TRABALHO_JUVENIL_RAIS_DESCRITIVO_V1_1", "Estoque formal juvenil", "READY_WITH_LIMITS", "Como evoluiu o estoque formal juvenil por faixa etária?"),
        ("D2_CAGED_JUVENIL_FLUXOS_DETALHADOS_QA_V1_1", "Fluxos Caged detalhados para QA", "NOT_AUTHORIZED_FOR_VISUAL_USE", "Que ajustes precisam permanecer auditáveis sem virar composição visual?"),
        ("D2_CAGED_JUVENIL_AGREGADO_SEGURO_V1", "Fluxos Caged agregados seguros", "READY_WITH_LIMITS", "Como admissões e desligamentos juvenis evoluem em grãos compatíveis?"),
        ("D2_APRENDIZAGEM_PROFISSIONAL_DESCRITIVA_V1_1", "Aprendizagem profissional", "READY_WITH_LIMITS", "Como os eventos de aprendizagem evoluem por faixa etária?"),
        ("D2_ESCOLARIDADE_VINCULOS_JOVENS_V1_1", "Escolaridade técnica bruta dos vínculos jovens", "TECHNICAL_RAW_CODE_ONLY", "Quais códigos brutos existem e que dicionário oficial ainda falta?"),
        ("D2_OCUPACOES_RAIS_ESTOQUE_TODAS_IDADES_V1", "Ocupações RAIS — estoque de todas as idades", "READY_WITH_LIMITS", "Quais ocupações ganharam ou perderam estoque formal?"),
        ("D2_SETORES_RAIS_ESTOQUE_TODAS_IDADES_V1", "Setores RAIS — estoque de todas as idades", "READY_WITH_LIMITS", "Quais divisões CNAE mudaram no estoque formal?"),
        ("D2_OCUPACOES_CAGED_FLUXOS_JUVENIS_V1", "Ocupações Caged — fluxos juvenis", "READY_WITH_LIMITS", "Quais ocupações mudaram em admissões e desligamentos juvenis?"),
        ("D2_SETORES_CAGED_FLUXOS_JUVENIS_V1", "Setores Caged — fluxos juvenis", "READY_WITH_LIMITS", "Quais divisões CNAE mudaram nos fluxos juvenis?"),
        ("D2_CAGED_SALDO_LIQUIDO_INTERNO_V1", "Saldo líquido Caged interno", "INTERNAL_ONLY", "Que saldo complementa admissões e desligamentos sem virar share comum?"),
        ("D2_EPT_OFERTA_TOTAL_OBSERVADA_V1_1", "Oferta EPT observada", "READY_WITH_LIMITS", "Como se distribui a oferta técnica observada por localização da escola?"),
        ("D2_PONTE_CBO_CNCT_AUDITADA_V1_1", "Ponte normativa CBO–CNCT", "READY_WITH_LIMITS", "Que correspondências normativas existem sem vínculo de pessoas ou causalidade?"),
        ("D2_APRENDIZAGEM_OCUPACOES_EIXOS_V1_1", "Aprendizagem, ocupações e eixos", "READY_WITH_LIMITS", "Que associações normativas podem orientar investigação sem somar a ponte?"),
        ("D2_CONCENTRACAO_TRABALHO_EPT_V1_1", "Concentração do trabalho e da EPT", "READY_WITH_LIMITS", "Como a concentração varia dentro de cada universo, sem comparação cruzada?"),
        ("D2_SHIFT_SHARE_SETORIAL_DESCRITIVO_V1_1", "Shift-share setorial", "READY_WITH_LIMITS", "Quais diferenciais locais merecem investigação descritiva?"),
        ("D2_ESCOLARIDADE_ADULTA_TRABALHO_CONTEXTUAL_V1_1", "Escolaridade adulta no trabalho", "INSUFFICIENT_DATA", "Que integração ainda não pode ser avaliada?"),
        ("D2_TRABALHO_JUVENIL_EDUCACAO_CONTEXTO_V1_1", "Trabalho e educação em paralelo", "DESCRIPTIVE_CONTEXT_ONLY", "Que séries devem ser acompanhadas sem microvínculo, teste ou causalidade?"),
    ]
    return [
        {
            "analysis_id": analysis_id,
            "title": title,
            "state": state,
            "substantive_question": question,
            "page_role": "INTERNAL_METADATA_LAYER",
            "standalone_visual_module": False,
            "automatic_approval": False,
            "external_judgment_required": True,
        }
        for analysis_id, title, state, question in rows
    ]


def build_pne_links() -> pd.DataFrame:
    monitored = {
        "D2_APRENDIZAGEM_PROFISSIONAL_DESCRITIVA_V1_1": "11.b|11.c",
        "D2_EPT_OFERTA_TOTAL_OBSERVADA_V1_1": "11.b|11.c",
        "D2_PONTE_CBO_CNCT_AUDITADA_V1_1": "11.b|11.c",
        "D2_APRENDIZAGEM_OCUPACOES_EIXOS_V1_1": "11.b|11.c",
        "D2_TRABALHO_JUVENIL_EDUCACAO_CONTEXTO_V1_1": "3|7|11",
    }
    rows = []
    for item in analysis_catalog():
        applies = item["analysis_id"] in monitored
        rows.append(
            {
                "analysis_id": item["analysis_id"],
                "title": item["title"],
                "state": item["state"],
                "goal_id": monitored.get(item["analysis_id"], "not_applicable"),
                "indicator_id": "not_materialized" if applies else "not_applicable",
                "mode": "metadata_only_no_recalculation",
                "link_type": "planning_context" if applies else "not_applicable",
                "monitoring_indicator": "not_materialized" if applies else "not_applicable",
                "monitoring_indicator_status": "NOT_MATERIALIZED" if applies else "NOT_APPLICABLE",
                "materialized_value_available": False,
                "materialized_fact_available": item["state"] != "INSUFFICIENT_DATA",
                "page_role": "INTERNAL_METADATA_LAYER",
                "standalone_visual_module": False,
                "recalculates_official_indicator": False,
                "official_target_claim": False,
                "automatic_approval": False,
                "external_judgment_required": True,
            }
        )
    return pd.DataFrame(rows)


QA_CONTROLS = (
    ("QA1_JOB5GC", "question"),
    ("QA2_JOB5GC", "mechanism"),
    ("QA3_JOB5GC", "universe"),
    ("QA4_JOB5GC", "territorial_lens"),
    ("QA5_JOB5GC", "source"),
    ("QA6_JOB5GC", "period"),
    ("QA7_JOB5GC", "completeness"),
    ("QA8_JOB5GC", "formula"),
    ("QA9_JOB5GC", "semantics"),
    ("QA10_JOB5GC", "nova_santa_rita"),
    ("QA11_JOB5GC", "non_redundancy"),
    ("QA12_JOB5GC", "planning_question"),
)


def build_qa_matrix() -> pd.DataFrame:
    rows = []
    for item in analysis_catalog():
        for code, dimension in QA_CONTROLS:
            status = "PASS"
            evidence = f"{item['analysis_id']} declara {dimension} no contrato v1.1."
            if item["state"] in {"INSUFFICIENT_DATA", "TECHNICAL_RAW_CODE_ONLY"} and code in {
                "QA7_JOB5GC",
                "QA9_JOB5GC",
            }:
                status = "PASS_WITH_EXPLICIT_LIMIT"
                evidence = (
                    f"{item['state']}: a lacuna permanece materializada e não foi convertida em PASS substantivo."
                )
            if item["state"] in {"NOT_AUTHORIZED_FOR_VISUAL_USE", "INTERNAL_ONLY"} and code == "QA9_JOB5GC":
                status = "PASS_WITH_EXPLICIT_CONSUMPTION_BLOCK"
                evidence = "O artefato preserva QA, mas visual_aggregation_eligible/standalone_visual_module permanecem falsos."
            rows.append(
                {
                    "analysis_id": item["analysis_id"],
                    "qa_control_id": code,
                    "original_control_id": code,
                    "qa_control_meaning": dimension,
                    "qa_control_status": status,
                    "qa_control_evidence": evidence,
                    "score": pd.NA,
                    "automatic_approval": False,
                    "external_judgment_required": True,
                }
            )
    return pd.DataFrame(rows)


CRITERIA = (
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
)


def _criterion_status(item: Mapping[str, Any], code: str) -> tuple[str, str]:
    state = item["state"]
    if state == "INSUFFICIENT_DATA":
        return "NOT_EVALUABLE", "Sem linha materializada; a lacuna é explícita."
    if code == "C5":
        return "PARTIAL", "Cobertura temporal completa não prova estabilidade; denominadores e quebras permanecem guardrails."
    if code == "C9" and state in {
        "NOT_AUTHORIZED_FOR_VISUAL_USE",
        "TECHNICAL_RAW_CODE_ONLY",
        "INTERNAL_ONLY",
    }:
        return "NOT_SUPPORTED", "Consumo editorial bloqueado por célula ajustada, código sem rótulo oficial ou saldo interno."
    if code == "C3" and item["analysis_id"].endswith("CONTEXTO_V1_1"):
        return "PARTIAL", "As lentes permanecem paralelas; não identificam as mesmas pessoas."
    if code == "C1" and state in {"INTERNAL_ONLY", "NOT_AUTHORIZED_FOR_VISUAL_USE"}:
        return "PARTIAL", "Relevância apenas como camada QA/interna."
    if code in {"C6", "C8", "C9", "C12"} and state in {
        "READY_WITH_LIMITS",
        "DESCRIPTIVE_CONTEXT_ONLY",
    }:
        return "PARTIAL", "Há evidência material, mas o limite semântico impede apoio integral."
    return "SUPPORTED", "Contrato, fonte, grão e limitação estão materializados e rastreáveis."


def build_canonical_matrix() -> pd.DataFrame:
    rows = []
    for item in analysis_catalog():
        for code, meaning in CRITERIA:
            status, evidence = _criterion_status(item, code)
            rows.append(
                {
                    "analysis_id": item["analysis_id"],
                    "substantive_question": item["substantive_question"],
                    "classification": item["state"],
                    "criterion_id": code,
                    "criterion_meaning": meaning,
                    "criterion_status": status,
                    "criterion_evidence": evidence,
                    "score": pd.NA,
                    "automatic_approval": False,
                    "external_judgment_required": True,
                }
            )
    return pd.DataFrame(rows)


def build_opportunity_matrix(canonical: pd.DataFrame) -> pd.DataFrame:
    pivot = canonical.pivot(
        index="analysis_id", columns="criterion_id", values="criterion_status"
    ).reset_index()
    catalog = pd.DataFrame(analysis_catalog())
    result = catalog.merge(pivot, on="analysis_id", how="left", validate="one_to_one")
    result = result.rename(columns={code: f"{code.lower()}_status" for code, _ in CRITERIA})
    result["score"] = pd.NA
    result["automatic_approval"] = False
    result["external_judgment_required"] = True
    result["canonical_matrix_path"] = "MATRIZ_C1_C12_CANONICA_JOB5GC_V1_1.csv.gz"
    result["qa_matrix_path"] = "MATRIZ_QA_JOB5GC_V1_1.csv.gz"
    return result


def build_fact_catalog(
    occupation_stock: pd.DataFrame,
    sector_stock: pd.DataFrame,
    occupation_flow: pd.DataFrame,
    sector_flow: pd.DataFrame,
    shift: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    def append_change(frame: pd.DataFrame, universe: str) -> None:
        local = frame[
            frame["entity_id"].eq(NSR_CODE)
        ]
        for row in local.to_dict("records"):
            direction = "gain" if float(row["absolute_change"]) > 0 else (
                "loss" if float(row["absolute_change"]) < 0 else "no_change"
            )
            rows.append(
                {
                    "fact_id": f"{universe}|{row.get('measure')}|{row['dimension_code']}",
                    "universe": universe,
                    "measure": row.get("measure"),
                    "direction": direction,
                    "dimension_code": row["dimension_code"],
                    "dimension_label": row.get("dimension_label"),
                    "initial_value": row["initial_value"],
                    "final_value": row["final_value"],
                    "absolute_change": row["absolute_change"],
                    "relative_change_percent": row.get("percent_change"),
                    "regional_initial_value": row.get("regional_initial_value"),
                    "regional_final_value": row.get("regional_final_value"),
                    "regional_concentration_share_final": row.get("final_regional_share"),
                    "small_volume_sensitive": bool(row["small_volume_sensitive"]),
                    "negative_adjustment_present": bool(row.get("negative_adjustment_present", False)),
                    "label_available": bool(row.get("label_available", False)),
                    "selection_eligible": bool(row.get("selection_eligible", False)),
                    "selection_metric": row["absolute_change"],
                    "selection_metric_name": "absolute_change",
                }
            )

    append_change(occupation_stock, "RAIS_OCCUPATION_STOCK_ALL_AGES")
    append_change(sector_stock, "RAIS_SECTOR_STOCK_ALL_AGES")
    append_change(occupation_flow, "CAGED_OCCUPATION_YOUTH_FLOW")
    append_change(sector_flow, "CAGED_SECTOR_YOUTH_FLOW")
    for row in shift[shift["municipality_ibge_code"].eq(NSR_CODE)].to_dict("records"):
        metric = row.get("local_differential_effect")
        direction = "gain" if metric is not None and metric > 0 else (
            "loss" if metric is not None and metric < 0 else "no_change"
        )
        rows.append(
            {
                "fact_id": f"SHIFT_SHARE_LOCAL_DIFFERENTIAL|{row['cnae_division_code']}",
                "universe": "SHIFT_SHARE_LOCAL_DIFFERENTIAL",
                "measure": "local_differential_effect",
                "direction": direction,
                "dimension_code": row["cnae_division_code"],
                "dimension_label": row.get("cnae_division_label"),
                "initial_value": row["initial_value"],
                "final_value": row["final_value"],
                "absolute_change": row["absolute_change"],
                "relative_change_percent": row.get("percent_change"),
                "regional_initial_value": row.get("state_sector_initial"),
                "regional_final_value": row.get("state_sector_final"),
                "regional_concentration_share_final": None,
                "small_volume_sensitive": bool(row["small_volume_sensitive"]),
                "negative_adjustment_present": False,
                "label_available": bool(row.get("label_available", False)),
                "selection_eligible": bool(row.get("selection_eligible", False)),
                "selection_metric": metric,
                "selection_metric_name": "local_differential_effect",
            }
        )
    catalog = pd.DataFrame(rows)
    catalog["selected_for_synthesis"] = False
    catalog["selection_rank"] = pd.Series(pd.NA, index=catalog.index, dtype="Int64")
    eligible = catalog[
        catalog["selection_eligible"]
        & catalog["direction"].isin(["gain", "loss"])
    ].copy()
    eligible["absolute_selection_metric"] = eligible["selection_metric"].abs()
    eligible["regional_tiebreak"] = pd.to_numeric(
        eligible["regional_final_value"], errors="coerce"
    ).fillna(-1)
    eligible["absolute_final_value_tiebreak"] = pd.to_numeric(
        eligible["final_value"], errors="coerce"
    ).abs().fillna(-1)
    eligible["absolute_initial_value_tiebreak"] = pd.to_numeric(
        eligible["initial_value"], errors="coerce"
    ).abs().fillna(-1)
    eligible["regional_concentration_tiebreak"] = pd.to_numeric(
        eligible["regional_concentration_share_final"], errors="coerce"
    ).fillna(-1)
    eligible["absolute_relative_change_tiebreak"] = pd.to_numeric(
        eligible["relative_change_percent"], errors="coerce"
    ).abs().fillna(-1)
    exact_tie_fields = [
        "universe",
        "measure",
        "direction",
        "dimension_code",
        "dimension_label",
        "initial_value",
        "final_value",
        "absolute_change",
        "relative_change_percent",
        "regional_initial_value",
        "regional_final_value",
        "regional_concentration_share_final",
    ]
    eligible["exact_tie_content_digest"] = eligible.apply(
        lambda row: hashlib.sha256(
            json.dumps(
                _json_safe({field: row.get(field) for field in exact_tie_fields}),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest(),
        axis=1,
    )
    for (_, _), group in eligible.groupby(["universe", "direction"], sort=True):
        selected = group.sort_values(
            [
                "absolute_selection_metric",
                "regional_tiebreak",
                "absolute_final_value_tiebreak",
                "absolute_initial_value_tiebreak",
                "regional_concentration_tiebreak",
                "absolute_relative_change_tiebreak",
                "exact_tie_content_digest",
            ],
            ascending=[False, False, False, False, False, False, True],
            kind="mergesort",
        ).head(3)
        catalog.loc[selected.index, "selected_for_synthesis"] = True
        catalog.loc[selected.index, "selection_rank"] = range(1, len(selected) + 1)
    catalog["selection_rule_version"] = "job5gcr-materiality-v1"
    catalog["selection_rule"] = (
        "eligible non-small labeled facts; gains/losses separated; descending absolute substantive metric; "
        "regional volume, endpoint magnitudes, regional concentration and relative change as substantive tie-breakers; "
        "cryptographic content digest only for exact ties; maximum three per universe/direction"
    )
    catalog["physical_order_used"] = False
    catalog["code_order_used"] = False
    catalog["alphabetical_order_used"] = False
    catalog["exact_tie_content_digest_only"] = True
    return _stable(
        catalog, ["universe", "direction", "selected_for_synthesis", "selection_rank", "fact_id"]
    )


def build_nsr_payload(
    panels: Mapping[str, pd.DataFrame], fact_catalog: pd.DataFrame
) -> dict[str, Any]:
    rais_anchor = panels["rais"][
        panels["rais"]["dimension"].eq("total")
        & panels["rais"]["age_group"].isin(["15_17", "18_24"])
        & panels["rais"]["entity_id"].isin([NSR_CODE, REGION_ENTITY_ID, STATE_ENTITY_ID])
    ]
    caged_anchor = panels["caged_safe"][
        panels["caged_safe"]["time_grain"].eq("annual_flow")
        & panels["caged_safe"]["aggregation_scope"].eq("all_apprentice_status")
        & panels["caged_safe"]["entity_id"].isin([NSR_CODE, REGION_ENTITY_ID, STATE_ENTITY_ID])
    ]
    apprentice_anchor = panels["apprentice"][
        panels["apprentice"]["aggregation_scope"].eq("all_apprentice_events")
        & panels["apprentice"]["entity_id"].isin([NSR_CODE, REGION_ENTITY_ID, STATE_ENTITY_ID])
    ]
    ept_anchor = panels["ept"][
        panels["ept"]["grain"].isin(["municipality_total", "region_total"])
        & panels["ept"]["entity_id"].isin([NSR_CODE, REGION_ENTITY_ID])
    ]
    ept_hhi = panels["concentration"][
        panels["concentration"]["dimension"].eq("ept_total_territorial")
    ].sort_values(["year", "municipality_ibge_code"], kind="mergesort")
    ept_hhi_context = (
        ept_hhi.groupby("year", as_index=False)
        .first()[["year", "hhi", "regional_total", "positive_municipality_count"]]
    )
    logistics = panels["rais_occupations"][
        panels["rais_occupations"]["occupation_code"].eq("414140")
        & panels["rais_occupations"]["entity_id"].isin([NSR_CODE, REGION_ENTITY_ID])
    ]
    if len(logistics) != 2:
        raise ValueError("A âncora 414140 não contém município e Vale exatamente uma vez.")
    values = {
        row["entity_id"]: (int(row["initial_value"]), int(row["final_value"]))
        for row in logistics.to_dict("records")
    }
    if values.get(REGION_ENTITY_ID) != (303, 2124) or values.get(NSR_CODE) != (17, 722):
        raise ValueError(f"A âncora 414140 divergiu: {values}.")
    labels = set(logistics["dimension_label"].dropna().astype(str))
    if labels != {"Auxiliar de logistica"}:
        raise ValueError(f"Rótulo local da CBO 414140 divergente: {labels}.")
    subgroup = panels["rais_occupations"][
        panels["rais_occupations"]["occupation_subgroup_code"].eq("41")
        & panels["rais_occupations"]["entity_id"].eq(REGION_ENTITY_ID)
    ]
    return {
        "schemaVersion": "nova-santa-rita-job5gc-v1-1",
        "municipalityIbgeCode": NSR_CODE,
        "municipalityName": "Nova Santa Rita",
        "selectionRuleDeclaredBeforeSynthesis": True,
        "selectionRuleVersion": "job5gcr-materiality-v1",
        "mandatoryAnchors": {
            "raisYouthStock": _records(rais_anchor),
            "cagedAdmissionsDismissals": _records(caged_anchor),
            "apprenticeship": _records(apprentice_anchor),
            "eptMunicipalRegional": _records(ept_anchor),
            "eptConcentration": _records(ept_hhi_context),
            "lensLimits": [
                "work and Caged use establishment location",
                "EPT and trajectory use school location",
                "population uses residence",
                "student mobility uses student residence",
                "no source combination identifies the same people",
            ],
        },
        "selectedFacts": _records(
            fact_catalog[fact_catalog["selected_for_synthesis"]]
        ),
        "completeFactCatalogPath": "MATRIZ_CATALOGO_FATOS_NOVA_SANTA_RITA_JOB5GCR_V1.csv.gz",
        "auxiliarLogisticaReconciliationAnchor": {
            "occupationCode": "414140",
            "validatedLocalLabel": "Auxiliar de logistica",
            "classificationContinuity2019To2025": True,
            "vale": {"2019": 303, "2025": 2124},
            "novaSantaRita": {"2019": 17, "2025": 722},
            "occupationSubgroupCode": "41",
            "subgroupComparison": _records(subgroup),
            "establishmentConcentrationAvailable": False,
            "headlineForced": False,
            "interpretation": "observed movement; never future demand",
        },
        "smallVolumeRule": "abs(initial_value) < 20 and abs(final_value) < 20",
        "smallVolumeFactsRetainedInCatalog": True,
        "smallVolumeFactsEligibleForMainSelection": False,
        "publicNarrativeApproved": False,
        "automaticApproval": False,
        "externalJudgmentRequired": True,
    }


def build_code_dictionary(
    *,
    cnae_catalog: pd.DataFrame,
    occupation_catalog: pd.DataFrame,
    schooling_catalog: pd.DataFrame,
    bridge_contract: Mapping[str, Any],
    offer: pd.DataFrame,
) -> dict[str, Any]:
    cnae_subclasses = cnae_catalog[
        [
            "cnae_subclass_code",
            "cnae_subclass_label",
            "cnae_division_code",
            "cnae_division_label",
        ]
    ].drop_duplicates()
    divisions = cnae_catalog[
        ["cnae_division_code", "cnae_division_label"]
    ].drop_duplicates()
    occupations = occupation_catalog[
        ["occupation_code", "occupation_label"]
    ].drop_duplicates()
    occupations["occupation_subgroup_code"] = occupations["occupation_code"].str[:2]
    subgroup_labels = {
        normalize_numeric_code(key, width=2, allow_all=False): value
        for key, value in bridge_contract["occupationSubgroups"].items()
    }
    subgroups = pd.DataFrame(
        {
            "occupation_subgroup_code": sorted(
                set(occupations["occupation_subgroup_code"]) | set(subgroup_labels)
            )
        }
    )
    subgroups["occupation_subgroup_label"] = subgroups[
        "occupation_subgroup_code"
    ].map(subgroup_labels)
    subgroups["label_status"] = subgroups["occupation_subgroup_label"].map(
        lambda value: "LOCAL_BRIDGE_LABEL_PRESENT"
        if _label_available(value)
        else "LABEL_UNAVAILABLE_OR_ENCODING_DEGRADED"
    )
    observed_offer = offer.copy()
    observed_offer["course_code"] = observed_offer["course_code"].astype("string")
    observed_offer["technological_axis_code"] = observed_offer[
        "technological_axis_code"
    ].astype("string")
    course_labels = (
        observed_offer[["course_code", "course_name"]]
        .drop_duplicates()
        .set_index("course_code")["course_name"]
        .to_dict()
    )
    processed_course_codes = sorted(
        {str(row["courseCode"]) for row in bridge_contract["mappings"]}
        | {str(code) for code in bridge_contract["unmappedCourseCodes"]}
    )
    courses = [
        {
            "course_code": code,
            "course_label": course_labels.get(code),
            "observed_in_vale_offer_2025": code in course_labels,
            "bridge_contract_scope": "BRIDGE_CONTRACT_RS",
        }
        for code in processed_course_codes
    ]
    axes = observed_offer[
        ["technological_axis_code", "technological_axis_name"]
    ].drop_duplicates()
    schooling = schooling_catalog.copy()
    schooling["dictionary_status"] = "LOCAL_UNVERSIONED_NOT_VISUAL_AUTHORIZED"
    schooling["visual_eligible"] = False
    return {
        "schemaVersion": "work-code-dictionary-job5gcr-v1",
        "codePolicies": {
            "cnaeSubclass": "7 numeric characters; raw and normalized values preserved",
            "cnaeDivision": "2 numeric characters derived from normalized subclass",
            "cboOccupation": "6 numeric characters",
            "cboSubgroup": "2 numeric characters",
            "municipalityIbge": "7 numeric characters",
            "courseAndAxis": "source strings without undocumented padding",
        },
        "cnae": {
            "declaredVersion": "CNAE 2.0 (local CEI catalog; content-hash versioned)",
            "subclasses": _records(cnae_subclasses),
            "divisions": _records(divisions),
        },
        "cbo": {
            "declaredVersion": "CBO 2002 (local CEI catalog; content-hash versioned)",
            "occupations": _records(occupations),
            "subgroups": _records(subgroups),
        },
        "raisSchooling": {
            "officialVersionedDictionaryAvailable": False,
            "panelState": "TECHNICAL_RAW_CODE_ONLY",
            "entries": _records(schooling),
        },
        "cnct": {
            "bridgeContractStatistics": bridge_contract["statistics"],
            "courses": courses,
            "axesObservedInVale": _records(axes),
        },
        "networkUsed": False,
        "externalAcquisitions": [],
    }


def semantic_dictionary() -> dict[str, Any]:
    return {
        "schemaVersion": "semantic-dictionary-job5gc-v1-1",
        "identity": {
            "municipality": "textual IBGE code with seven digits",
            "region": REGION_ENTITY_ID,
            "state": STATE_ENTITY_ID,
            "slugIsIdentity": False,
        },
        "workMeasures": {
            "D2_OCUPACOES_RAIS_ESTOQUE_TODAS_IDADES_V1": "annual stock of active bonds; all ages",
            "D2_SETORES_RAIS_ESTOQUE_TODAS_IDADES_V1": "annual stock of active bonds; all ages",
            "D2_OCUPACOES_CAGED_FLUXOS_JUVENIS_V1": "adjusted youth admission/dismissal events",
            "D2_SETORES_CAGED_FLUXOS_JUVENIS_V1": "adjusted youth admission/dismissal events",
            "D2_CAGED_SALDO_LIQUIDO_INTERNO_V1": "admissions minus dismissals; internal complement; never stock",
        },
        "smallVolumeSensitive": {
            "formula": "abs(initial_value) < 20 and abs(final_value) < 20",
            "officialConfidentialityThreshold": False,
            "mainFactSelectionAllowed": False,
        },
        "shares": {
            "formula": "numerator / denominator",
            "eligibleOnlyWhen": "numerator >= 0; denominator > 0; compatible grain/entity/period/age/contract; no negative adjusted component",
            "ineligibleStatus": "ADJUSTED_CELL_NOT_SHARE_ELIGIBLE",
            "ineligibleValue": None,
        },
        "hhi": {
            "formula": "sum(category_share^2)",
            "range": [0, 1],
            "crossUniverseComparisonAllowed": False,
            "qualitativeLabelAllowed": False,
        },
        "shiftShare": {
            "formula": "reference_growth_effect + industry_mix_effect + local_differential_effect",
            "reference": "RS",
            "causal": False,
        },
        "parallelContext": {
            "parallelSeriesOnly": True,
            "samePersonLink": False,
            "causalLink": False,
            "associationTest": False,
            "combinedScore": False,
        },
        "rounding": "serialization or presentation only; decisions use raw values",
        "networkScope": "total_all_dependencies",
    }


def limitations_payload() -> dict[str, Any]:
    return {
        "schemaVersion": "limitations-job5gc-v1-1",
        "finalState": FINAL_STATE,
        "items": [
            {"id": "L1", "severity": "structural", "dimension": "Caged detailed", "status": "qa_only", "effect": "Negative adjusted cells remain; detailed visual use is not authorized."},
            {"id": "L2", "severity": "material", "dimension": "RAIS schooling", "status": "TECHNICAL_RAW_CODE_ONLY", "effect": "Local labels lack an upstream official version; visual use remains false."},
            {"id": "L3", "severity": "structural", "dimension": "RAIS/Caged", "status": "separate_measures", "effect": "RAIS stock, Caged admissions/dismissals and Caged balance are not interchangeable."},
            {"id": "L4", "severity": "structural", "dimension": "CBO-CNCT bridge", "status": "normative_many_to_many", "effect": "No person linkage, causality, adequacy, sufficiency or additive summation."},
            {"id": "L5", "severity": "interpretive", "dimension": "HHI", "status": "within_universe_only", "effect": "No automatic high/low/efficient/insufficient labels."},
            {"id": "L6", "severity": "interpretive", "dimension": "shift-share", "status": "descriptive_decomposition", "effect": "Accounting decomposition is not causal attribution."},
            {"id": "L7", "severity": "interpretive", "dimension": "parallel education-work context", "status": "descriptive_only", "effect": "2020-2021 trajectory flags remain; no smoothing, stability or causal claim."},
            {"id": "L8", "severity": "interpretive", "dimension": "small volumes", "status": "retained_not_selected", "effect": "The threshold is a consumption rule, not official statistical confidentiality."},
        ],
        "automaticApproval": False,
        "externalJudgmentRequired": True,
    }


def source_dictionary(
    *,
    inputs: Mapping[str, Path],
    original_integrity: Mapping[str, Any],
    catalog_digests: Mapping[str, str],
    state_sector_digest: str,
) -> dict[str, Any]:
    sources = [
        {
            "id": identifier,
            "path": path.as_posix(),
            "byteSize": path.stat().st_size,
            "sha256": sha256_file(path),
            "access": "local_read_only",
        }
        for identifier, path in sorted(inputs.items())
    ]
    sources.extend(
        [
            {
                "id": "cei_cnae_local_catalog",
                "path": "database:cei/public.cnae",
                "byteSize": None,
                "sha256": catalog_digests["cnae"],
                "access": "postgresql_read_only_transaction",
            },
            {
                "id": "cei_cbo_local_catalog",
                "path": "database:cei/public.ocupacao",
                "byteSize": None,
                "sha256": catalog_digests["occupation"],
                "access": "postgresql_read_only_transaction",
            },
            {
                "id": "cei_rais_schooling_local_catalog",
                "path": "database:cei/public.grau_instrucao",
                "byteSize": None,
                "sha256": catalog_digests["schooling"],
                "access": "postgresql_read_only_transaction",
                "officialVersionDeclared": False,
            },
            {
                "id": "rais_rs_shift_share_aggregate",
                "path": "database:cei/read_only/rais_2019_2025_aggregate",
                "byteSize": None,
                "sha256": state_sector_digest,
                "access": "postgresql_read_only_transaction",
            },
        ]
    )
    return {
        "schemaVersion": "source-dictionary-job5gc-v1-1",
        "sources": sources,
        "originalJob5GCIntegrity": original_integrity,
        "networkUsed": False,
        "databaseMode": "read_only_aggregates_and_local_code_catalogs",
        "databaseWrites": False,
        "officialSchoolingDictionaryFound": False,
        "sourceRefreshPerformed": False,
        "externalAcquisitions": [],
    }


def normalization_audit(
    *,
    original_caged: pd.DataFrame,
    corrected_caged: pd.DataFrame,
    original_occ_sector: pd.DataFrame,
    rais_sectors: pd.DataFrame,
    normalized_occupations: pd.DataFrame,
    caged_sectors: pd.DataFrame,
    apprentice: pd.DataFrame,
) -> dict[str, Any]:
    corrected = corrected_caged[corrected_caged["cnae_subclass_code"].ne("ALL")].copy()
    affected = corrected[
        corrected["cnae_subclass_code_raw"].ne(corrected["cnae_subclass_code"])
    ]
    moves = (
        affected.assign(
            before_division=affected["cnae_subclass_code_raw"].str[:2],
            after_division=affected["cnae_subclass_code"].str[:2],
        )
        .groupby(["before_division", "after_division"], as_index=False)
        .agg(
            row_count=("cnae_subclass_code", "size"),
            admission_events=("admissions", "sum"),
            dismissal_events=("dismissals", "sum"),
        )
    )
    raw_counts = Counter(affected["cnae_subclass_code_raw"].astype(str))
    original_total = original_caged[["admissions", "dismissals"]].apply(
        pd.to_numeric, errors="raise"
    ).sum()
    corrected_total = corrected_caged[["admissions", "dismissals"]].sum()
    original_rais_sector = original_occ_sector[
        original_occ_sector["source"].eq("RAIS all ages")
        & original_occ_sector["dimension"].eq("cnae_division")
    ].copy()
    before_divisions = sorted(
        original_rais_sector["dimension_code"].dropna().astype(str).unique()
    )
    after_divisions = sorted(
        rais_sectors["cnae_division_code"].dropna().astype(str).unique()
    )
    low_divisions = sorted(code for code in after_divisions if "01" <= code <= "09")
    apprenticed = apprentice[
        apprentice["cnae_subclass_code"].ne("ALL")
        & apprentice["cnae_subclass_code_raw"].ne(apprentice["cnae_subclass_code"])
    ]
    nsr = affected[affected["entity_id"].eq(NSR_CODE)]
    municipal_impact = (
        affected[affected["entity_scope"].eq("municipality")]
        .groupby(
            ["municipality_ibge_code", "municipality_name", "year"],
            as_index=False,
            dropna=False,
        )
        .agg(
            row_count=("cnae_subclass_code", "size"),
            admission_events=("admissions", "sum"),
            dismissal_events=("dismissals", "sum"),
        )
    )
    nsr_impact = (
        nsr.groupby(
            [
                "year",
                "cnae_subclass_code_raw",
                "cnae_subclass_code",
                "cnae_division_code",
            ],
            as_index=False,
            dropna=False,
        )
        .agg(
            row_count=("cnae_subclass_code", "size"),
            admission_events=("admissions", "sum"),
            dismissal_events=("dismissals", "sum"),
        )
    )

    rais_source = (
        normalized_occupations[
            normalized_occupations["year"].isin([2019, 2025])
        ]
        .groupby(
            ["entity_scope", "entity_id", "cnae_division_code", "year"],
            as_index=False,
            dropna=False,
        )["active_bonds"]
        .sum()
        .pivot(
            index=["entity_scope", "entity_id", "cnae_division_code"],
            columns="year",
            values="active_bonds",
        )
        .fillna(0)
        .reset_index()
        .rename(columns={2019: "source_initial", 2025: "source_final"})
    )
    rais_observed = rais_sectors[
        [
            "entity_scope",
            "entity_id",
            "cnae_division_code",
            "initial_value",
            "final_value",
        ]
    ].rename(
        columns={
            "initial_value": "division_initial",
            "final_value": "division_final",
        }
    )
    rais_reconciliation = rais_source.merge(
        rais_observed,
        on=["entity_scope", "entity_id", "cnae_division_code"],
        how="outer",
        validate="one_to_one",
    ).fillna(
        {
            "source_initial": 0,
            "source_final": 0,
            "division_initial": 0,
            "division_final": 0,
        }
    )
    rais_reconciliation["initial_residual"] = (
        rais_reconciliation["source_initial"]
        - rais_reconciliation["division_initial"]
    )
    rais_reconciliation["final_residual"] = (
        rais_reconciliation["source_final"] - rais_reconciliation["division_final"]
    )
    rais_max_residual = float(
        rais_reconciliation[["initial_residual", "final_residual"]]
        .abs()
        .max()
        .max()
    )
    if rais_max_residual > 1e-9:
        raise ValueError("A reconciliação CNAE subclasse→divisão da RAIS falhou.")

    caged_source = corrected_caged[
        corrected_caged["time_grain"].eq("annual_flow")
        & corrected_caged["entity_scope"].isin(["municipality", "region"])
        & ~corrected_caged["occupation_code"].eq("ALL")
        & corrected_caged["year"].isin([2020, 2025])
    ]
    caged_source = (
        caged_source.groupby(
            [
                "entity_scope",
                "entity_id",
                "age_group",
                "cnae_division_code",
                "year",
            ],
            as_index=False,
            dropna=False,
        )[["admissions", "dismissals"]]
        .sum()
        .melt(
            id_vars=[
                "entity_scope",
                "entity_id",
                "age_group",
                "cnae_division_code",
                "year",
            ],
            value_vars=["admissions", "dismissals"],
            var_name="measure",
            value_name="source_value",
        )
        .pivot(
            index=[
                "entity_scope",
                "entity_id",
                "age_group",
                "cnae_division_code",
                "measure",
            ],
            columns="year",
            values="source_value",
        )
        .fillna(0)
        .reset_index()
        .rename(columns={2020: "source_initial", 2025: "source_final"})
    )
    caged_observed = caged_sectors[
        [
            "entity_scope",
            "entity_id",
            "age_group",
            "cnae_division_code",
            "measure",
            "initial_value",
            "final_value",
        ]
    ].rename(
        columns={
            "initial_value": "division_initial",
            "final_value": "division_final",
        }
    )
    caged_reconciliation = caged_source.merge(
        caged_observed,
        on=[
            "entity_scope",
            "entity_id",
            "age_group",
            "cnae_division_code",
            "measure",
        ],
        how="outer",
        validate="one_to_one",
    ).fillna(
        {
            "source_initial": 0,
            "source_final": 0,
            "division_initial": 0,
            "division_final": 0,
        }
    )
    caged_reconciliation["initial_residual"] = (
        caged_reconciliation["source_initial"]
        - caged_reconciliation["division_initial"]
    )
    caged_reconciliation["final_residual"] = (
        caged_reconciliation["source_final"]
        - caged_reconciliation["division_final"]
    )
    caged_max_residual = float(
        caged_reconciliation[["initial_residual", "final_residual"]]
        .abs()
        .max()
        .max()
    )
    if caged_max_residual > 1e-9:
        raise ValueError("A reconciliação CNAE subclasse→divisão do Caged falhou.")

    apprentice_detail = (
        apprentice[
            apprentice["aggregation_scope"].eq("occupation_cnae_detail_qa_only")
            & apprentice["entity_scope"].isin(["municipality", "region"])
        ]
        .groupby(
            ["entity_scope", "entity_id", "year", "age_group"],
            as_index=False,
            dropna=False,
        )[["admissions", "dismissals"]]
        .sum()
        .rename(
            columns={
                "admissions": "detail_admissions",
                "dismissals": "detail_dismissals",
            }
        )
    )
    apprentice_total = apprentice[
        apprentice["aggregation_scope"].eq("all_apprentice_events")
        & apprentice["entity_scope"].isin(["municipality", "region"])
    ][
        [
            "entity_scope",
            "entity_id",
            "year",
            "age_group",
            "admissions",
            "dismissals",
        ]
    ].rename(
        columns={
            "admissions": "total_admissions",
            "dismissals": "total_dismissals",
        }
    )
    apprentice_reconciliation = apprentice_detail.merge(
        apprentice_total,
        on=["entity_scope", "entity_id", "year", "age_group"],
        how="outer",
        validate="one_to_one",
    ).fillna(0)
    apprentice_reconciliation["admission_residual"] = (
        apprentice_reconciliation["detail_admissions"]
        - apprentice_reconciliation["total_admissions"]
    )
    apprentice_reconciliation["dismissal_residual"] = (
        apprentice_reconciliation["detail_dismissals"]
        - apprentice_reconciliation["total_dismissals"]
    )
    apprentice_max_residual = float(
        apprentice_reconciliation[
            ["admission_residual", "dismissal_residual"]
        ]
        .abs()
        .max()
        .max()
    )
    if apprentice_max_residual > 1e-9:
        raise ValueError("O detalhe de aprendizagem não reconcilia com o total seguro.")

    rais_by_scope = (
        rais_reconciliation.groupby("entity_scope", as_index=False)[
            [
                "source_initial",
                "division_initial",
                "source_final",
                "division_final",
            ]
        ]
        .sum()
    )
    caged_by_scope_measure = (
        caged_reconciliation.groupby(
            ["entity_scope", "measure"], as_index=False
        )[
            [
                "source_initial",
                "division_initial",
                "source_final",
                "division_final",
            ]
        ]
        .sum()
    )
    apprentice_by_scope = (
        apprentice_reconciliation.groupby("entity_scope", as_index=False)[
            [
                "detail_admissions",
                "total_admissions",
                "detail_dismissals",
                "total_dismissals",
            ]
        ]
        .sum()
    )
    return {
        "normalizationIsSubstantiveClassificationChange": False,
        "mandatoryExamples": {
            "111301": {"normalized": "0111301", "division": "01"},
            "142300": {"normalized": "0142300", "division": "01"},
            "161099": {"normalized": "0161099", "division": "01"},
            "810009": {"normalized": "0810009", "division": "08"},
            "899199": {"normalized": "0899199", "division": "08"},
        },
        "caged": {
            "affectedRows": len(affected),
            "affectedRawCodeCount": len(raw_counts),
            "affectedRawCodes": [
                {"raw": code, "normalized": code.zfill(7), "rows": count}
                for code, count in sorted(raw_counts.items())
            ],
            "divisionMoves": _records(moves),
            "affectedMunicipalities": sorted(
                affected["municipality_ibge_code"].dropna().astype(str).unique()
            ),
            "affectedYears": sorted(int(value) for value in affected["year"].unique()),
            "novaSantaRitaAffectedRows": len(nsr),
            "impactByMunicipalityYear": _records(municipal_impact),
            "novaSantaRitaImpactByYearAndCode": _records(nsr_impact),
            "totalsBefore": {key: float(value) for key, value in original_total.items()},
            "totalsAfter": {key: float(value) for key, value in corrected_total.items()},
        },
        "raisSectors": {
            "beforeDivisionCodes": before_divisions,
            "afterDivisionCodes": after_divisions,
            "restoredDivisions01To09": low_divisions,
            "affectedEntityRows": int(
                rais_sectors[rais_sectors["cnae_division_code"].isin(low_divisions)].shape[0]
            ),
        },
        "apprenticeship": {
            "affectedRows": len(apprenticed),
            "affectedRawCodes": sorted(
                apprenticed["cnae_subclass_code_raw"].dropna().astype(str).unique()
            ),
        },
        "sectorReconciliation": {
            "raisSubclassToDivision": {
                "keyCount": len(rais_reconciliation),
                "maxAbsResidual": rais_max_residual,
                "byEntityScope": _records(rais_by_scope),
            },
            "cagedSubclassToDivision": {
                "keyCount": len(caged_reconciliation),
                "maxAbsResidual": caged_max_residual,
                "byEntityScopeAndMeasure": _records(caged_by_scope_measure),
            },
            "apprenticeshipDetailToSafeTotal": {
                "keyCount": len(apprentice_reconciliation),
                "maxAbsResidual": apprentice_max_residual,
                "byEntityScope": _records(apprentice_by_scope),
            },
        },
    }


def _errata_methodology(audit: Mapping[str, Any], qa: Mapping[str, Any]) -> str:
    caged = audit["caged"]
    rais = audit["raisSectors"]
    reconciliation = audit["sectorReconciliation"]
    return f"""# Errata metodológica — Job 5G-C — V7

## Escopo

Esta errata corrige somente códigos, contratos de consumo e seleções do Job 5G-C.
Os 24 outputs originais permanecem congelados. Não houve publicação, narrativa
pública, frontend, compilador, build completo ou alteração de `public/data`.

## CNAE

O leitor anterior deixou o Pandas inferir CNAE como número e perdeu zeros à
esquerda. A versão 1.1 preserva `cnae_subclass_code_raw`, normaliza códigos
numéricos para sete caracteres e deriva a divisão pelos dois primeiros.

- linhas Caged afetadas: {caged['affectedRows']};
- códigos brutos afetados: {caged['affectedRawCodeCount']};
- municípios afetados: {len(caged['affectedMunicipalities'])};
- anos afetados: {', '.join(str(value) for value in caged['affectedYears'])};
- linhas afetadas em Nova Santa Rita: {caged['novaSantaRitaAffectedRows']};
- divisões 01–09 restauradas no painel RAIS: {', '.join(rais['restoredDivisions01To09']) or 'nenhuma'}.
- resíduo máximo subclasse→divisão RAIS: {reconciliation['raisSubclassToDivision']['maxAbsResidual']};
- resíduo máximo subclasse→divisão Caged: {reconciliation['cagedSubclassToDivision']['maxAbsResidual']};
- resíduo máximo detalhe→total seguro de aprendizagem: {reconciliation['apprenticeshipDetailToSafeTotal']['maxAbsResidual']}.

Exemplos bloqueantes validados: `111301→0111301→01`,
`142300→0142300→01`, `161099→0161099→01`,
`810009→0810009→08` e `899199→0899199→08`.

## Novo Caged

As células ajustadas negativas permanecem no painel detalhado de QA. Shares
dessas células ou de denominadores tornados não proporcionais ficam nulos com
`ADJUSTED_CELL_NOT_SHARE_ELIGIBLE`. O painel adicional seguro separa
`monthly_flow` de `annual_flow` e município, Vale e RS por `entity_id`.

- admissões negativas preservadas: {qa['negativeAdmissionRows']};
- desligamentos negativos preservados: {qa['negativeDismissalRows']};
- linhas do agregado seguro: {qa['safeCagedRowCount']}.

## Materialidade e medidas

`small_volume_sensitive` continua sendo exatamente
`abs(initial_value) < 20 and abs(final_value) < 20`. É regra de consumo, não
sigilo estatístico oficial. RAIS é estoque anual de todas as idades nos painéis
ocupacionais/setoriais; Novo Caged é fluxo juvenil; saldo é interno e não aceita
share comum. `persistence_status` foi substituído por
`period_coverage_status`.

## Ponte, HHI, contexto e PNE/PME

A ponte separa o contrato RS (113/91/22 cursos; 115 pares) da oferta observada
no Vale em 2025 (44 cursos, 39/5; 12.664/1.281 matrículas). Ela permanece
muitos-para-muitos e não aditiva. HHI não recebe rótulo qualitativo nem permite
comparação entre universos. O contexto trabalho–educação preserva as flags de
2020–2021 e identidades explícitas. `monitoring_indicator` deixou de ser
booleano e não recalcula meta ou indicador.

Estado: `{FINAL_STATE}`.
"""


def _errata_job5f() -> str:
    return """# Errata — âncora Auxiliar de logística — Job 5F — V7

## Valores superados

- Vale do Sinos: 606 vínculos em 2019 → 4.248 em 2025.

## Valores canônicos

- CBO `414140`, Auxiliar de logistica, Vale do Sinos: 303 → 2.124;
- CBO `414140`, Auxiliar de logistica, Nova Santa Rita (`4313375`): 17 → 722.

## Causa

O Job 5F somou a linha regional agregada e as dez linhas municipais do mesmo
artefato, duplicando o Vale. O valor canônico usa exclusivamente
`entity_scope=region`; município e região nunca são somados entre si.

Os arquivos históricos do Job 5F não foram alterados. Job 5H e qualquer mapa
futuro devem consumir somente os valores canônicos acima. O movimento é
observado; não equivale a demanda futura.
"""


def _section_map() -> str:
    return f"""# Mapa de seções potenciais — Job 5G-C v1.1

Material técnico para julgamento externo. Nenhuma seção, card ou narrativa está aprovada para publicação.

| Ordem | Camada | Artefato seguro | Estado |
|---:|---|---|---|
| 1 | Estoque juvenil | `PAINEL_RAIS_TRABALHO_JUVENIL_V1_1.csv.gz` | limites preservados |
| 2 | Fluxos juvenis | `PAINEL_CAGED_JUVENIL_AGREGADO_SEGURO_V1.csv.gz` | consumo seguro; detalhe só QA |
| 3 | Aprendizagem | `PAINEL_APRENDIZAGEM_PROFISSIONAL_V1_1.csv.gz` | fluxo, não estoque |
| 4 | Ocupações e setores | quatro painéis RAIS/Caged separados | seleção por materialidade |
| 5 | EPT e ponte | oferta + ponte auditada | localização da escola; não aditivo |
| 6 | Concentração e shift-share | HHI + decomposição | sem rótulo qualitativo ou causalidade |
| 7 | Trabalho e educação | séries paralelas | 2020–2021 com contexto obrigatório |

Estado permitido: `{FINAL_STATE}`. Parar para julgamento externo; não iniciar Job 5G-D, 5H ou 6.
"""


def validate_panels(
    panels: Mapping[str, pd.DataFrame],
    *,
    original_caged: pd.DataFrame,
    original_concentration: pd.DataFrame,
    municipality_codes: set[str],
    bridge_contract: Mapping[str, Any],
) -> dict[str, Any]:
    for key, frame in panels.items():
        if "municipality_ibge_code" in frame:
            for value in frame["municipality_ibge_code"].dropna().astype(str).unique():
                require_ibge_code(value)
        for column, width in (
            ("cnae_subclass_code", 7),
            ("cnae_division_code", 2),
            ("occupation_code", 6),
            ("occupation_subgroup_code", 2),
        ):
            if column not in frame:
                continue
            values = frame[column].dropna().astype(str)
            values = values[values.ne("ALL")]
            invalid = values[~values.str.fullmatch(rf"\d{{{width}}}")]
            if not invalid.empty:
                raise ValueError(f"{key}.{column} contém códigos inválidos: {invalid.head().tolist()}.")
    caged = panels["caged"]
    if len(caged) != len(original_caged):
        raise ValueError("A camada Caged detalhada perdeu ou ganhou linhas.")
    if not caged["cnae_subclass_code_raw"].astype("string").equals(
        original_caged["cnae_subclass_code"].astype("string").reindex(caged.index)
    ):
        # A ordenação canônica pode divergir; compare multiconjuntos por chave bruta.
        if Counter(caged["cnae_subclass_code_raw"].astype(str)) != Counter(
            original_caged["cnae_subclass_code"].astype(str)
        ):
            raise ValueError("Os códigos CNAE brutos do Caged não foram preservados.")
    residual = caged["admissions"] - caged["dismissals"] - caged["balance"]
    if residual.abs().max() > 1e-9:
        raise ValueError("O fechamento admissions-dismissals=balance falhou.")
    negative_admissions = int(caged["admissions"].lt(0).sum())
    negative_dismissals = int(caged["dismissals"].lt(0).sum())
    if (negative_admissions, negative_dismissals) != (67, 68):
        raise ValueError("Os componentes ajustados negativos deixaram de ser preservados.")
    share_contracts = {
        "admission_composition_share": "admission_composition_share_eligible",
        "dismissal_composition_share": "dismissal_composition_share_eligible",
        "municipal_share_of_regional_admissions": (
            "municipal_share_of_regional_admissions_eligible"
        ),
        "municipal_share_of_regional_dismissals": (
            "municipal_share_of_regional_dismissals_eligible"
        ),
        "seasonality_admission_share_of_annual": (
            "seasonality_admission_share_of_annual_eligible"
        ),
    }
    for share_column, eligibility_column in share_contracts.items():
        eligible = caged[eligibility_column].fillna(False).astype(bool)
        if caged.loc[~eligible, share_column].notna().any():
            raise ValueError(
                f"{share_column} contém valor fora da elegibilidade declarada."
            )
        if caged.loc[eligible, share_column].isna().any():
            raise ValueError(
                f"{share_column} está nulo apesar da elegibilidade declarada."
            )
        values = caged.loc[eligible, share_column].astype(float)
        if ((values < -1e-12) | (values > 1 + 1e-12)).any():
            raise ValueError(f"{share_column} elegível está fora de 0–1.")
    share_columns = list(share_contracts)
    negative_rows = caged["negative_adjustment_present"].fillna(False).astype(bool)
    if caged.loc[negative_rows, share_columns].notna().any().any():
        raise ValueError("Célula Caged ajustada negativa ainda contém share.")
    safe = panels["caged_safe"]
    if safe[["admissions", "dismissals"]].lt(0).any().any():
        raise ValueError("O agregado Caged seguro contém componente negativo.")
    monthly = safe[safe["time_grain"].eq("monthly_flow")]
    annual = safe[safe["time_grain"].eq("annual_flow")]
    annual_keys = [
        "entity_scope", "entity_id", "year", "age_group",
        "apprentice_indicator_code", "aggregation_scope",
    ]
    monthly_sum = monthly.groupby(annual_keys, as_index=False, dropna=False)[
        ["admissions", "dismissals", "balance"]
    ].sum()
    annual_compare = annual[annual_keys + ["admissions", "dismissals", "balance"]]
    merged = monthly_sum.merge(
        annual_compare,
        on=annual_keys,
        how="outer",
        suffixes=("_monthly", "_annual"),
        validate="one_to_one",
    )
    for measure in ("admissions", "dismissals", "balance"):
        if (merged[f"{measure}_monthly"] - merged[f"{measure}_annual"]).abs().max() > 1e-9:
            raise ValueError(f"Caged mensal não reconcilia com anual em {measure}.")
    if set(safe["entity_scope"]) != {"municipality", "region", "state"}:
        raise ValueError("O agregado Caged não separa município, região e Estado.")
    if safe["entity_id"].isna().any():
        raise ValueError("O agregado Caged contém entity_id nulo.")
    schooling = panels["schooling"]
    if schooling["visual_eligible"].any() or schooling["schooling_label"].notna().any():
        raise ValueError("Escolaridade sem dicionário oficial versionado entrou no visual.")
    bridge = panels["bridge"]
    coverage = bridge[
        ["bridge_status", "unique_course_count", "unique_technical_enrollments"]
    ].drop_duplicates().set_index("bridge_status")
    if (
        int(coverage.loc["mapped", "unique_course_count"]) != 39
        or int(coverage.loc["unmapped", "unique_course_count"]) != 5
        or int(coverage.loc["mapped", "unique_technical_enrollments"]) != 12664
        or int(coverage.loc["unmapped", "unique_technical_enrollments"]) != 1281
    ):
        raise ValueError("A cobertura 39/5 e 12.664/1.281 da oferta do Vale divergiu.")
    if bridge_contract["statistics"] != {
        "courseOccupationSubgroupPairs": 115,
        "mappedCourses": 91,
        "processedCourses": 113,
        "unmappedCourses": 22,
    }:
        raise ValueError("O contrato RS da ponte não reproduz 113/91/22/115.")
    if bridge["additive_across_bridge_rows"].any() or bridge["same_person_link"].any() or bridge["causal_link"].any():
        raise ValueError("A ponte muitos-para-muitos perdeu guardrails.")
    concentration = panels["concentration"]
    hhi = concentration["hhi"].dropna().astype(float)
    if ((hhi < -1e-12) | (hhi > 1 + 1e-12)).any():
        raise ValueError("HHI fora de 0–1.")
    old_ept = original_concentration[
        original_concentration["dimension"].astype(str).str.startswith("ept_")
    ][["year", "dimension", "category_code", "municipality_ibge_code", "hhi"]].copy()
    new_ept = concentration[
        concentration["dimension"].astype(str).str.startswith("ept_")
    ][["year", "dimension", "category_code", "municipality_ibge_code", "hhi"]].copy()
    for frame in (old_ept, new_ept):
        frame["category_code"] = frame["category_code"].astype("string")
        frame["municipality_ibge_code"] = frame["municipality_ibge_code"].astype("string")
    compare = old_ept.merge(
        new_ept,
        on=["year", "dimension", "category_code", "municipality_ibge_code"],
        suffixes=("_old", "_new"),
        how="outer",
        validate="one_to_one",
    )
    if len(compare) != len(old_ept) or (compare["hhi_old"] - compare["hhi_new"]).abs().max() > 1e-12:
        raise ValueError("O HHI EPT validado foi alterado.")
    shift = panels["shift"]
    observed = shift[shift["component_status"].eq("observed")]
    if not observed.empty and observed["closure_residual"].abs().max() > 1e-7:
        raise ValueError("O shift-share recalculado não fechou.")
    if not {"01", "02", "08"}.issubset(set(shift["cnae_division_code"])):
        raise ValueError("Divisões baixas esperadas não foram restauradas no shift-share.")
    links = panels["pne_links"]
    if links["monitoring_indicator"].map(type).eq(bool).any():
        raise ValueError("monitoring_indicator ainda contém booleano.")
    qa = panels["qa"]
    canonical = panels["canonical"]
    expected_matrix_rows = len(analysis_catalog()) * 12
    if len(qa) != expected_matrix_rows or len(canonical) != expected_matrix_rows:
        raise ValueError("QA ou C1–C12 não contém doze controles por análise.")
    if "qa_control_evidence" not in qa or qa["qa_control_evidence"].isna().any():
        raise ValueError("A matriz QA não contém evidência em todas as linhas.")
    if not set(canonical["criterion_status"]).issubset(CANONICAL_CRITERION_STATUSES):
        raise ValueError("Status não canônico na matriz C1–C12.")
    if canonical["score"].notna().any() or canonical["automatic_approval"].any():
        raise ValueError("A matriz C1–C12 pontuou ou aprovou automaticamente.")
    c5 = canonical[canonical["criterion_id"].eq("C5")]
    if c5["criterion_status"].eq("SUPPORTED").any():
        raise ValueError("C5 foi suportado apenas por cobertura temporal.")
    facts = panels["fact_catalog"]
    if facts.loc[facts["small_volume_sensitive"], "selected_for_synthesis"].any():
        raise ValueError("Fato de pequeno volume entrou na síntese principal.")
    if (
        facts["physical_order_used"].any()
        or facts["code_order_used"].any()
        or facts["alphabetical_order_used"].any()
        or not facts["exact_tie_content_digest_only"].all()
    ):
        raise ValueError("A seleção municipal ainda depende de ordem proibida.")
    context = panels["parallel"]
    if context["entity_id"].isna().any() or "education_stage" not in context:
        raise ValueError("O contexto paralelo não contém identidade/etapa.")
    atypical = context[
        context["source"].eq("Indicadores Educacionais/INEP")
        & context["year"].isin([2020, 2021])
    ]
    if atypical.empty or not atypical["period_context_flag"].eq(
        "ATYPICAL_SERIES_DISCONTINUITY_REQUIRES_CONTEXT"
    ).all() or atypical["public_line_continuity_allowed"].astype("boolean").any():
        raise ValueError("As flags de contexto 2020–2021 não foram preservadas.")
    observed_codes = set(
        panels["ept"].loc[
            panels["ept"]["entity_scope"].eq("municipality"), "municipality_ibge_code"
        ].dropna().astype(str)
    )
    if observed_codes != municipality_codes:
        raise ValueError("O universo municipal EPT divergiu dos dez códigos canônicos.")
    return {
        "municipalityCount": len(observed_codes),
        "negativeAdmissionRows": negative_admissions,
        "negativeDismissalRows": negative_dismissals,
        "safeCagedRowCount": len(safe),
        "safeCagedMonthlyRows": len(monthly),
        "safeCagedAnnualRows": len(annual),
        "cagedDetailedRowCount": len(caged),
        "bridgeContract": bridge_contract["statistics"],
        "valeOffer": {
            "mappedCourses": 39,
            "unmappedCourses": 5,
            "mappedEnrollments": 12664,
            "unmappedEnrollments": 1281,
        },
        "hhiMinimum": float(hhi.min()),
        "hhiMaximum": float(hhi.max()),
        "shiftMaxAbsClosureResidual": float(observed["closure_residual"].abs().max()) if not observed.empty else None,
        "qaRows": len(qa),
        "canonicalRows": len(canonical),
        "selectedFactCount": int(facts["selected_for_synthesis"].sum()),
    }


def materialize_frames(
    *,
    source_job5gc_root: Path,
    inputs: Mapping[str, Path],
    state_sector_totals: pd.DataFrame,
    state_sector_audit: Mapping[str, Any],
    municipality_names: Mapping[str, str],
    cnae_catalog: pd.DataFrame,
    occupation_catalog: pd.DataFrame,
    schooling_catalog: pd.DataFrame,
    bridge_contract: Mapping[str, Any],
) -> tuple[dict[str, pd.DataFrame], dict[str, Any]]:
    region_codes = set(municipality_names)
    original_caged = _read_csv(
        source_job5gc_root / "PAINEL_CAGED_JUVENIL_FLUXOS_V1.csv.gz"
    )
    original_occ_sector = _read_csv(
        source_job5gc_root / "PAINEL_OCUPACOES_SETORES_MUDANCA_V1.csv.gz"
    )
    original_concentration = _read_csv(
        source_job5gc_root / "PAINEL_CONCENTRACAO_TRABALHO_EPT_V1.csv.gz"
    )
    rais_cube = _read_csv(inputs["rais_youth_cube"])
    rais_annual = _read_csv(inputs["rais_youth_annual"])
    occupations_source = _read_csv(inputs["rais_occupations"])
    offer = _read_csv(inputs["ept_offer"])
    coverage = _read_csv(inputs["ept_coverage"])
    bridge_source = _read_csv(inputs["course_cbo_bridge"])
    trajectory = _read_csv(inputs["trajectory"])
    for frame in (rais_cube, rais_annual):
        mask = frame["municipality_ibge_code"].notna()
        frame.loc[mask, "municipality_ibge_code"] = _normalize_series(
            frame.loc[mask, "municipality_ibge_code"], width=7, allow_all=False
        )
    rais_cube = _numeric(rais_cube, ["year", "active_bonds"])
    rais_annual = _numeric(rais_annual, ["year", "active_bonds"])
    rais = build_rais_youth(rais_annual, rais_cube, region_codes)
    rais = add_entity_id(rais)
    rais["network_scope"] = "not_applicable_workplace_source"
    caged = build_corrected_caged_detailed(original_caged)
    caged_safe = build_safe_caged_aggregate(caged)
    apprentice = build_apprentice_panel(caged, caged_safe)
    schooling = build_schooling_panel(rais_cube, region_codes, schooling_catalog)
    rais_occupations, rais_sectors, normalized_occupations = build_rais_stock_panels(
        occupations_source, cnae_catalog, occupation_catalog
    )
    caged_occupations, caged_sectors, caged_balance = build_caged_flow_panels(
        caged, cnae_catalog, occupation_catalog
    )
    ept = build_ept_panel(offer, coverage, region_codes)
    bridge, apprentice_axes = build_bridge_panels(bridge_source, apprentice)
    concentration = build_concentration_panel(
        normalized_occupations, ept, municipality_names, cnae_catalog
    )
    shift = build_shift_panel(
        normalized_occupations,
        state_sector_totals,
        state_sector_audit,
        cnae_catalog,
    )
    adult = empty_adult_context()
    adult["dictionary_status"] = pd.Series(dtype="string")
    adult["visual_eligible"] = pd.Series(dtype="boolean")
    parallel = build_parallel_context_panel(
        rais_annual, caged_safe, apprentice, trajectory, ept
    )
    pne_links = build_pne_links()
    qa = build_qa_matrix()
    canonical = build_canonical_matrix()
    opportunities = build_opportunity_matrix(canonical)
    fact_catalog = build_fact_catalog(
        rais_occupations,
        rais_sectors,
        caged_occupations,
        caged_sectors,
        shift,
    )
    panels = {
        "rais": rais,
        "caged": caged,
        "caged_safe": caged_safe,
        "apprentice": apprentice,
        "schooling": schooling,
        "rais_occupations": rais_occupations,
        "rais_sectors": rais_sectors,
        "caged_occupations": caged_occupations,
        "caged_sectors": caged_sectors,
        "caged_balance": caged_balance,
        "ept": ept,
        "bridge": bridge,
        "apprentice_axes": apprentice_axes,
        "concentration": concentration,
        "shift": shift,
        "adult": adult,
        "parallel": parallel,
        "pne_links": pne_links,
        "fact_catalog": fact_catalog,
        "qa": qa,
        "canonical": canonical,
        "opportunities": opportunities,
    }
    panels["nsr"] = pd.DataFrame()
    qa_summary = validate_panels(
        panels,
        original_caged=original_caged,
        original_concentration=original_concentration,
        municipality_codes=region_codes,
        bridge_contract=bridge_contract,
    )
    audit = normalization_audit(
        original_caged=original_caged,
        corrected_caged=caged,
        original_occ_sector=original_occ_sector,
        rais_sectors=rais_sectors,
        normalized_occupations=normalized_occupations,
        caged_sectors=caged_sectors,
        apprentice=apprentice,
    )
    nsr = build_nsr_payload(panels, fact_catalog)
    metadata = {
        "qaSummary": qa_summary,
        "normalizationAudit": audit,
        "nsr": nsr,
        "bridgeContract": bridge_contract,
        "offerSource": offer,
    }
    return panels, metadata


CSV_OUTPUTS = {
    "PAINEL_RAIS_TRABALHO_JUVENIL_V1_1.csv.gz": "rais",
    "PAINEL_CAGED_JUVENIL_FLUXOS_V1_1.csv.gz": "caged",
    "PAINEL_CAGED_JUVENIL_AGREGADO_SEGURO_V1.csv.gz": "caged_safe",
    "PAINEL_APRENDIZAGEM_PROFISSIONAL_V1_1.csv.gz": "apprentice",
    "PAINEL_ESCOLARIDADE_VINCULOS_JOVENS_V1_1.csv.gz": "schooling",
    "PAINEL_OCUPACOES_RAIS_ESTOQUE_V1.csv.gz": "rais_occupations",
    "PAINEL_SETORES_RAIS_ESTOQUE_V1.csv.gz": "rais_sectors",
    "PAINEL_OCUPACOES_CAGED_FLUXOS_V1.csv.gz": "caged_occupations",
    "PAINEL_SETORES_CAGED_FLUXOS_V1.csv.gz": "caged_sectors",
    "PAINEL_CAGED_SALDO_LIQUIDO_INTERNO_V1.csv.gz": "caged_balance",
    "PAINEL_EPT_OFERTA_TOTAL_V1_1.csv.gz": "ept",
    "PAINEL_PONTE_CBO_CNCT_AUDITADA_V1_1.csv.gz": "bridge",
    "PAINEL_APRENDIZAGEM_OCUPACOES_EIXOS_V1_1.csv.gz": "apprentice_axes",
    "PAINEL_CONCENTRACAO_TRABALHO_EPT_V1_1.csv.gz": "concentration",
    "PAINEL_SHIFT_SHARE_SETORIAL_V1_1.csv.gz": "shift",
    "PAINEL_ESCOLARIDADE_ADULTA_TRABALHO_CONTEXTUAL_V1_1.csv.gz": "adult",
    "PAINEL_TRABALHO_JUVENIL_EDUCACAO_CONTEXTO_V1_1.csv.gz": "parallel",
    "MATRIZ_VINCULOS_PNE_PME_JOB5GC_V1_1.csv.gz": "pne_links",
    "MATRIZ_CATALOGO_FATOS_NOVA_SANTA_RITA_JOB5GCR_V1.csv.gz": "fact_catalog",
    "MATRIZ_QA_JOB5GC_V1_1.csv.gz": "qa",
    "MATRIZ_C1_C12_CANONICA_JOB5GC_V1_1.csv.gz": "canonical",
    "MATRIZ_OPORTUNIDADES_REAVALIADAS_JOB5GC_V1_1.csv.gz": "opportunities",
}


def write_package(
    *,
    output_dir: Path,
    source_job5gc_root: Path,
    inputs: Mapping[str, Path],
    state_sector_totals: pd.DataFrame,
    state_sector_audit: Mapping[str, Any],
    municipality_names: Mapping[str, str],
    cnae_catalog: pd.DataFrame,
    occupation_catalog: pd.DataFrame,
    schooling_catalog: pd.DataFrame,
    bridge_contract: Mapping[str, Any],
    contract: Mapping[str, Any],
    original_integrity: Mapping[str, Any],
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=False)
    panels, metadata = materialize_frames(
        source_job5gc_root=source_job5gc_root,
        inputs=inputs,
        state_sector_totals=state_sector_totals,
        state_sector_audit=state_sector_audit,
        municipality_names=municipality_names,
        cnae_catalog=cnae_catalog,
        occupation_catalog=occupation_catalog,
        schooling_catalog=schooling_catalog,
        bridge_contract=bridge_contract,
    )
    for filename, key in CSV_OUTPUTS.items():
        write_csv_gzip(output_dir / filename, panels[key])
    catalog_digests = {
        "cnae": _content_digest(cnae_catalog),
        "occupation": _content_digest(occupation_catalog),
        "schooling": _content_digest(schooling_catalog),
    }
    state_sector_digest = _content_digest(state_sector_totals)
    code_dictionary = build_code_dictionary(
        cnae_catalog=cnae_catalog,
        occupation_catalog=occupation_catalog,
        schooling_catalog=schooling_catalog,
        bridge_contract=bridge_contract,
        offer=metadata["offerSource"],
    )
    code_dictionary["catalogContentSha256"] = dict(catalog_digests)
    code_dictionary["cnct"]["bridgeContractSha256"] = sha256_file(
        inputs["bridge_contract"]
    )
    bridge_dictionary = {
        "schemaVersion": "bridge-dictionary-job5gc-v1-1",
        "bridgeContractScope": {
            "id": "BRIDGE_CONTRACT_RS",
            **bridge_contract["statistics"],
        },
        "courseOfferScope": {
            "id": "VALE_OFFER_2025",
            "courseOfferReferenceYear": 2025,
            "observedCourses": 44,
            "mappedCourses": 39,
            "unmappedCourses": 5,
            "mappedEnrollments": 12664,
            "unmappedEnrollments": 1281,
        },
        "sourceContract": bridge_contract,
        "originOfStudentAvailable": False,
        "samePersonLink": False,
        "causalLink": False,
        "additiveAcrossBridgeRows": False,
        "coursesAreObservedInValeNotNecessarilyMunicipality": True,
    }
    json_payloads = {
        "DICIONARIO_FONTES_TRABALHO_E_EPT_JOB5GC_V1_1.json": source_dictionary(
            inputs=inputs,
            original_integrity=original_integrity,
            catalog_digests=catalog_digests,
            state_sector_digest=state_sector_digest,
        ),
        "DICIONARIO_CODIGOS_TRABALHO_JOB5GCR_V1.json": code_dictionary,
        "DICIONARIO_SEMANTICO_METRICAS_JOB5GC_V1_1.json": semantic_dictionary(),
        "DICIONARIO_PONTE_CBO_CNCT_V1_1.json": bridge_dictionary,
        "NOVA_SANTA_RITA_JOB5GC_V1_1.json": metadata["nsr"],
        "LIMITACOES_JOB5GC_V1_1.json": limitations_payload(),
        "PACOTE_REVISAO_EXTERNA_JOB5GCR.json": {
            "schemaVersion": "external-review-package-job5gcr-v1",
            "jobId": JOB_ID,
            "finalState": FINAL_STATE,
            "objective": "Corrigir códigos, recomputar setores e estabelecer consumo/seleção seguros sem publicação.",
            "analysisCatalog": analysis_catalog(),
            "qaSummary": metadata["qaSummary"],
            "normalizationAudit": metadata["normalizationAudit"],
            "selectionRule": metadata["nsr"]["selectionRuleVersion"],
            "automaticApproval": False,
            "externalJudgmentRequired": True,
            "stopAfterDelivery": True,
        },
    }
    for filename, payload in json_payloads.items():
        write_json(output_dir / filename, payload)
    (output_dir / "ERRATA_METODOLOGICA_JOB5GC_V7.md").write_text(
        _errata_methodology(metadata["normalizationAudit"], metadata["qaSummary"]),
        encoding="utf-8",
        newline="\n",
    )
    (output_dir / "ERRATA_ANCHOR_AUXILIAR_LOGISTICA_JOB5F_V7.md").write_text(
        _errata_job5f(), encoding="utf-8", newline="\n"
    )
    (output_dir / "MAPA_SECOES_POTENCIAIS_JOB5GC_V1_1.md").write_text(
        _section_map(), encoding="utf-8", newline="\n"
    )
    pre_manifest = {path.name for path in output_dir.iterdir() if path.is_file()}
    expected_pre_manifest = set(EXPECTED_OUTPUTS) - {"MANIFEST_JOB5GCR.json"}
    if pre_manifest != expected_pre_manifest:
        raise ValueError(
            f"Lote pré-manifesto divergente: missing={expected_pre_manifest-pre_manifest}, extra={pre_manifest-expected_pre_manifest}."
        )
    artifacts = []
    for filename in sorted(pre_manifest):
        key = CSV_OUTPUTS.get(filename)
        artifacts.append(
            artifact_record(
                root=output_dir,
                path=output_dir / filename,
                frame=panels[key] if key else None,
                subjob="5G-C-R",
                grain="declared_in_artifact",
                period="2019-2025 or source-specific",
                lens="workplace|school_location|metadata",
                unit="source-specific",
                aggregation_rule="declared in semantic dictionary v1.1",
            )
        )
    original_after_generation = verify_original_job5gc(
        source_job5gc_root, str(original_integrity["manifestSha256"])
    )
    if original_after_generation != dict(original_integrity):
        raise ValueError("O Job 5G-C original mudou durante a geração do lote corrigido.")
    manifest = {
        "schemaVersion": "manifest-job5gcr-v1",
        "jobId": JOB_ID,
        "classification": "DATA_LOGIC",
        "domains": contract["domains"],
        "objective": "Correção dirigida do pacote Trabalho, Aprendizagem e EPT.",
        "finalState": FINAL_STATE,
        "contract": contract,
        "scope": contract["scope"],
        "artifacts": artifacts,
        "summary": {
            "outputCount": 33,
            "artifactHashCount": 32,
            "rowCounts": {
                filename: len(panels[key]) for filename, key in CSV_OUTPUTS.items()
            },
        },
        "inputIntegrity": {
            "before": original_integrity,
            "after": original_after_generation,
        },
        "qa": metadata["qaSummary"],
        "normalizationAudit": metadata["normalizationAudit"],
        "stateSectorAudit": state_sector_audit,
        "catalogDigests": catalog_digests,
        "databaseAggregate": {
            "used": True,
            "mode": "read_only",
            "grain": "RS/year/CNAE_division",
            "sha256": state_sector_digest,
            "rowCount": len(state_sector_totals),
        },
        "implementation": {
            identifier: {
                "path": inputs[identifier].as_posix(),
                "byteSize": inputs[identifier].stat().st_size,
                "sha256": sha256_file(inputs[identifier]),
            }
            for identifier in (
                "job5gcr_contract",
                "job5gcr_generator",
                "job5gcr_runner",
            )
        },
        "formulasPreserved": [
            "caged_balance",
            "safe_ratio_zero_denominator_null",
            "percent_change_zero_base_null",
            "hhi",
            "shift_share_closure",
        ],
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
            "compilerUsed": False,
            "fullBuildUsed": False,
            "publicNarrativeWritten": False,
            "automaticApproval": False,
        },
        "externalJudgmentRequired": True,
        "stopForExternalJudgment": True,
    }
    write_json(output_dir / "MANIFEST_JOB5GCR.json", manifest)
    if {path.name for path in output_dir.iterdir() if path.is_file()} != set(EXPECTED_OUTPUTS):
        raise ValueError("O lote final não contém exatamente as 33 saídas contratadas.")
    return manifest


def validate_existing_output(output_dir: Path) -> dict[str, Any]:
    manifest_path = output_dir / "MANIFEST_JOB5GCR.json"
    if not manifest_path.is_file():
        raise FileNotFoundError("MANIFEST_JOB5GCR.json ausente.")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("finalState") != FINAL_STATE:
        raise ValueError("Estado final divergente no manifesto 5G-C-R.")
    actual = {path.name for path in output_dir.iterdir() if path.is_file()}
    if actual != set(EXPECTED_OUTPUTS):
        raise ValueError("O output 5G-C-R não contém os 33 arquivos exatos.")
    for item in manifest["artifacts"]:
        path = output_dir / item["path"]
        if path.stat().st_size != item["byteSize"] or sha256_file(path) != item["sha256"]:
            raise ValueError(f"Hash/tamanho divergente em {item['path']}.")
    return {
        "finalState": FINAL_STATE,
        "outputCount": len(actual),
        "artifactHashCount": len(manifest["artifacts"]),
        "manifestSha256": sha256_file(manifest_path),
        "qa": manifest["qa"],
    }
