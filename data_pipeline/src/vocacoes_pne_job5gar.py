"""Correção dirigida e reprodutível do pacote analítico Job 5G-A-R V7.

O módulo lê somente os doze artefatos congelados do Job 5G-A, verifica seus
hashes, materializa um pacote novo em staging e nunca acessa banco, rede,
``public/data`` ou frontend.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / ".tmp" / "vocacoes-pne" / "v7-job5ga"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / ".tmp" / "vocacoes-pne" / "v7-job5gar"

ORIGINAL_FILES = (
    "CONTRATO_TRAJETORIA_OFICIAL_DESCRITIVA_V1.json",
    "PAINEL_TRAJETORIA_OFICIAL_DESCRITIVA_V1.csv.gz",
    "PAINEL_NASCIMENTOS_EDUCACAO_INFANTIL_V1.csv.gz",
    "PAINEL_DOCENTES_TURMAS_JORNADA_V1.csv.gz",
    "PAINEL_CONDICOES_ESCOLARES_TOTAL_V1.csv.gz",
    "PAINEL_PRESSAO_MECANICA_COORTES_AUDITADO_V1.csv.gz",
    "NOVA_SANTA_RITA_JOB5GA_V1.json",
    "MATRIZ_OPORTUNIDADES_REAVALIADAS_JOB5GA.csv.gz",
    "MAPA_SECOES_POTENCIAIS_JOB5GA.md",
    "LIMITACOES_JOB5GA.json",
    "PACOTE_REVISAO_EXTERNA_JOB5GA.json",
    "MANIFEST_JOB5GA.json",
)

OUTPUT_FILES = (
    "ERRATA_METODOLOGICA_JOB5GA_V7.md",
    "CONTRATO_TRAJETORIA_OFICIAL_DESCRITIVA_V1_1.json",
    "PAINEL_TRAJETORIA_OFICIAL_DESCRITIVA_V1_1.csv.gz",
    "PAINEL_EDUCACAO_INFANTIL_OBSERVADA_V1.csv.gz",
    "PAINEL_DOCENTES_TURMAS_JORNADA_V1_1.csv.gz",
    "PAINEL_CONDICOES_ESCOLARES_TOTAL_V1_1.csv.gz",
    "PAINEL_TEMPO_INTEGRAL_REGIONAL_V1.csv.gz",
    "PAINEL_PRESSAO_MECANICA_COORTES_AUDITADO_V1_1.csv.gz",
    "NOVA_SANTA_RITA_JOB5GA_V1_1.json",
    "MATRIZ_OPORTUNIDADES_REAVALIADAS_JOB5GA_V1_1.csv.gz",
    "MAPA_SECOES_POTENCIAIS_JOB5GA_V1_1.md",
    "PACOTE_REVISAO_EXTERNA_JOB5GAR.json",
    "MANIFEST_JOB5GAR.json",
)

EXPECTED_CODES = (
    "4303905",
    "4306403",
    "4307609",
    "4307708",
    "4310801",
    "4313375",
    "4313409",
    "4314803",
    "4318705",
    "4320008",
)
NOVA_SANTA_RITA_ID = "4313375"

CRITERION_MEANINGS = {
    "C1": "relevância PNE/PME",
    "C2": "mecanismo anterior ao resultado",
    "C3": "universos e lentes compatíveis",
    "C4": "período coerente",
    "C5": "estabilidade suficiente",
    "C6": "integração dos fatos",
    "C7": "diferença municipal útil",
    "C8": "município, etapa, público, indicador e questão",
    "C9": "comunicabilidade",
    "C10": "rastreabilidade",
    "C11": "não redundância",
    "C12": "valor além da demografia",
}
CRITERION_STATUSES = {"SUPPORTED", "PARTIAL", "NOT_SUPPORTED", "NOT_EVALUABLE"}

HAD_IED_PREFIXES = ("had_", "ied_")
IRD_METRICS = {
    "regularidade_docente_faixa_ate_2",
    "regularidade_docente_faixa_2_a_3",
    "regularidade_docente_faixa_3_a_4",
    "regularidade_docente_faixa_4_a_5",
}
ZERO_OBSERVATION_VISUAL_EXCLUSIONS = {
    "schools_with_drinking_water_percent",
    "schools_with_sports_court_percent",
    "schools_with_library_percent",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    if isinstance(value, np.generic):
        value = value.item()
    if value is pd.NA or value is None:
        return None
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    return value


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(
        path,
        dtype={"municipality_ibge_code": "string"},
        keep_default_na=False,
        na_values=["null"],
    )


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(_json_safe(payload), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _write_csv_gzip(path: Path, frame: pd.DataFrame) -> None:
    text = frame.to_csv(index=False, na_rep="null", lineterminator="\n")
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, compresslevel=9, mtime=0) as compressed:
            compressed.write(text.encode("utf-8"))


def _records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    return [_json_safe(record) for record in frame.to_dict(orient="records")]


def _truthy(series: pd.Series) -> pd.Series:
    return series.astype(str).str.casefold().isin({"true", "1"})


def _verify_originals(source_root: Path = SOURCE_ROOT) -> dict[str, dict[str, Any]]:
    manifest_path = source_root / "MANIFEST_JOB5GA.json"
    manifest = _load_json(manifest_path)
    declared = {item["path"]: item for item in manifest["artifacts"]}
    expected_declared = set(ORIGINAL_FILES) - {"MANIFEST_JOB5GA.json"}
    if set(declared) != expected_declared:
        raise ValueError("O manifesto original não declara exatamente os onze artefatos anteriores a ele.")

    result: dict[str, dict[str, Any]] = {}
    for name in ORIGINAL_FILES:
        path = source_root / name
        if not path.is_file():
            raise FileNotFoundError(path)
        actual = {"byteSize": path.stat().st_size, "sha256": sha256_file(path)}
        if name in declared:
            if actual["byteSize"] != declared[name]["byteSize"]:
                raise ValueError(f"Tamanho original divergente: {name}")
            if actual["sha256"] != declared[name]["sha256"]:
                raise ValueError(f"Hash original divergente: {name}")
        result[name] = actual
    return result


def _trajectory_contract() -> dict[str, Any]:
    return {
        "schemaVersion": "contrato-trajetoria-oficial-descritiva-v1.1",
        "objectId": "D1_TRAJETORIA_OFICIAL_DESCRITIVA_V1_1",
        "classification": "READY_WITH_PERIOD_AND_LABEL_GUARDRAILS",
        "networkScope": "total_all_dependencies",
        "territorialLens": "school_location",
        "administrativeDependencyRole": "qa_only",
        "isH2": False,
        "h2FrozenState": "NOT_EVALUABLE_DUE_TO_DATA_OR_QA_LIMIT",
        "grain": ["municipality_ibge_code", "year", "stage", "metric"],
        "officialMetrics": [
            "age_grade_distortion_rate_percent",
            "approval_rate_percent",
            "dropout_rate_percent",
            "failure_rate_percent",
        ],
        "periodGuardrails": {
            "contextYears": [2020, 2021],
            "contextFlag": "ATYPICAL_SERIES_DISCONTINUITY_REQUIRES_CONTEXT",
            "publicLineContinuityAllowed": False,
            "officialLocalExplanationAvailable": False,
            "causeAttributionAllowed": False,
            "smoothingAllowed": False,
            "allowedSegments": ["2018–2019", "2022–2025"],
            "fullSeriesAllowedWithVisualHighlight": True,
            "delta2018To2025Allowed": True,
        },
        "distributionLabels": {
            "vale": "Mediana dos municípios do Vale do Sinos",
            "rs": "Mediana dos municípios do RS",
            "positionSemantics": "distribution_order_not_performance_ranking",
        },
        "regionalComparison": {
            "method": "municipal_distribution_not_regional_rate",
            "regionalRateComputed": False,
            "meanOfRatesComputed": False,
            "officialRsRateAvailableInSameContract": False,
        },
        "allowedOperations": [
            "municipal_time_series_with_2020_2021_highlight",
            "change_in_percentage_points_2018_to_2025",
            "auxiliary_segment_2018_2019",
            "auxiliary_segment_2022_2025",
            "joint_movement_of_approval_failure_dropout",
            "age_grade_distortion_as_separate_series",
            "municipal_distribution_with_exact_public_label",
        ],
        "prohibitedOperations": [
            "linear_narrative_through_2020_2021",
            "cause_attribution_without_official_note",
            "smoothing",
            "denominator_dependent_stability_claim",
            "persistent_pattern_claim",
            "regional_rate_by_mean_or_sum",
            "state_rate_from_municipal_distribution",
            "performance_ranking_from_distribution_position",
            "H2_state_change_or_reopening",
        ],
        "valueStatePolicy": {
            "observedZero": "observed",
            "zeroDenominator": "null",
            "missing": "unavailable",
            "suppressed": "suppressed",
            "notApplicable": "not_applicable",
        },
        "finalNarrative": False,
        "potentialPublicEnvelopeOnly": True,
    }


def _trajectory_panel(source_root: Path = SOURCE_ROOT) -> pd.DataFrame:
    panel = _read_csv(source_root / "PAINEL_TRAJETORIA_OFICIAL_DESCRITIVA_V1.csv.gz")
    panel = panel.rename(
        columns={
            "vale_median": "vale_municipal_distribution_median",
            "rs_median": "rs_municipal_distribution_median",
        }
    )
    atypical = panel["year"].isin([2020, 2021])
    panel["period_context_flag"] = np.where(
        atypical,
        "ATYPICAL_SERIES_DISCONTINUITY_REQUIRES_CONTEXT",
        "STANDARD_OBSERVED_PERIOD",
    )
    panel["period_comparability_note"] = np.where(
        atypical,
        "Ruptura observada; a documentação oficial local é insuficiente para atribuir causa. Não ligar linearmente a série através de 2020–2021.",
        "Observação oficial municipal; comparações devem respeitar o destaque de 2020–2021 e os segmentos auxiliares autorizados.",
    )
    panel["public_line_continuity_allowed"] = ~atypical
    panel["trajectory_segment"] = np.select(
        [panel["year"].le(2019), atypical, panel["year"].ge(2022)],
        ["2018_2019", "2020_2021_CONTEXT_REQUIRED", "2022_2025"],
        default="OUTSIDE_AUTHORIZED_SEGMENTS",
    )
    panel["vale_distribution_public_label"] = "Mediana dos municípios do Vale do Sinos"
    panel["rs_distribution_public_label"] = "Mediana dos municípios do RS"
    panel["position_semantics"] = "distribution_order_not_performance_ranking"
    panel["h2_state"] = "NOT_EVALUABLE_DUE_TO_DATA_OR_QA_LIMIT"
    panel["regional_rate_value"] = np.nan
    panel["regional_rate_status"] = "not_computed"
    panel["regional_rate_method"] = "not_computed"
    return panel.sort_values(["municipality_ibge_code", "year", "stage", "metric"], kind="mergesort").reset_index(drop=True)


def _infant_observed_panel(source_root: Path = SOURCE_ROOT) -> pd.DataFrame:
    panel = _read_csv(source_root / "PAINEL_NASCIMENTOS_EDUCACAO_INFANTIL_V1.csv.gz")
    panel = panel[~panel["metric"].eq("births")].copy()
    drop_columns = [
        "birth_window_min_lag_years",
        "birth_window_max_lag_years",
        "birth_window_start_year",
        "birth_window_end_year",
        "migration_limitation",
        "vale_births_endpoint_value",
        "vale_births_endpoint_status",
        "vale_births_series_completeness",
        "rs_comparison_status",
    ]
    panel = panel.drop(columns=[column for column in drop_columns if column in panel])
    keys = ["year", "stage", "metric"]
    observed = (
        panel[panel["value_status"].eq("observed")]
        .groupby(keys)["municipality_ibge_code"]
        .nunique()
        .rename("observed_municipality_count")
        .reset_index()
    )
    panel = panel.merge(observed, how="left", on=keys)
    panel["observed_municipality_count"] = panel["observed_municipality_count"].fillna(0).astype(int)
    panel["expected_municipality_count"] = 10
    panel["coverage_fraction"] = panel["observed_municipality_count"] / 10
    panel["regional_distribution_eligible"] = panel["observed_municipality_count"].eq(10)
    panel["object_id"] = "D1_EDUCACAO_INFANTIL_OBSERVADA_V1"
    panel["object_state"] = "READY_FOR_INTERNAL_VISUAL_PROTOTYPE"
    panel["births_object_id"] = "D1_NASCIMENTOS_EDUCACAO_INFANTIL"
    panel["births_object_state"] = "INSUFFICIENT_DATA"
    panel["comparison_scope"] = "municipality_and_vale_municipal_distribution"
    return panel.sort_values(["municipality_ibge_code", "year", "stage", "metric"], kind="mergesort").reset_index(drop=True)


def _apply_comparator_coverage(panel: pd.DataFrame) -> pd.DataFrame:
    result = panel.copy()
    keys = ["year", "stage", "metric"]
    counts = (
        result[result["value_status"].eq("observed")]
        .groupby(keys)["municipality_ibge_code"]
        .nunique()
        .rename("observed_municipality_count")
        .reset_index()
    )
    result = result.merge(counts, how="left", on=keys)
    result["observed_municipality_count"] = result["observed_municipality_count"].fillna(0).astype(int)
    result["expected_municipality_count"] = 10
    result["coverage_fraction"] = result["observed_municipality_count"] / 10
    result["regional_distribution_eligible"] = result["observed_municipality_count"].eq(10)
    result["regional_comparison_classification"] = np.select(
        [
            result["regional_distribution_eligible"],
            result["observed_municipality_count"].gt(0),
        ],
        ["REGIONAL_DISTRIBUTION_ELIGIBLE", "LOCAL_DESCRIPTIVE_ONLY"],
        default="QA_AVAILABILITY_ONLY",
    )

    if "position_low_to_high_among_ten" in result:
        result = result.rename(
            columns={
                "position_low_to_high_among_ten": "position_low_to_high_among_observed_municipalities"
            }
        )

    ineligible = ~result["regional_distribution_eligible"]
    vale_fields = [
        "vale_minimum",
        "vale_quartile_1",
        "vale_municipal_median",
        "vale_quartile_3",
        "vale_maximum",
        "difference_from_vale_municipal_median",
        "position_low_to_high_among_observed_municipalities",
        "percentile_low_to_high_among_ten",
    ]
    for column in vale_fields:
        if column in result:
            result.loc[ineligible, column] = np.nan
    if "vale_municipality_count" in result:
        result["vale_municipality_count"] = result["observed_municipality_count"]

    if "regional_indicator_value" in result:
        result.loc[ineligible, "regional_indicator_value"] = np.nan
    if "regional_indicator_status" in result:
        result.loc[ineligible, "regional_indicator_status"] = "unavailable_ineligible_coverage"
    if "regional_context_method" in result:
        result.loc[ineligible & result["observed_municipality_count"].gt(0), "regional_context_method"] = "LOCAL_DESCRIPTIVE_ONLY"
        result.loc[ineligible & result["observed_municipality_count"].eq(0), "regional_context_method"] = "QA_AVAILABILITY_ONLY"

    had_ied = result["metric"].astype(str).str.startswith(HAD_IED_PREFIXES)
    for column in [
        "rs_minimum",
        "rs_quartile_1",
        "rs_municipal_median",
        "rs_quartile_3",
        "rs_maximum",
        "difference_from_rs_municipal_median",
    ]:
        if column in result:
            result.loc[had_ied, column] = np.nan
    return result


def _teachers_panel(source_root: Path = SOURCE_ROOT) -> pd.DataFrame:
    panel = _read_csv(source_root / "PAINEL_DOCENTES_TURMAS_JORNADA_V1.csv.gz")
    panel = _apply_comparator_coverage(panel)
    return panel.sort_values(["municipality_ibge_code", "year", "stage", "metric"], kind="mergesort").reset_index(drop=True)


def _semantic_limit(metric: str) -> str:
    if metric in IRD_METRICS:
        return "Fotografia 2025 da distribuição de escolas por faixa; não é distribuição de docentes."
    if metric.startswith("ied_"):
        return "IED 2025 com cobertura local 2/10; sem comparação do Vale ou comparação pré-2025."
    if metric in {"matriculas_tempo_integral", "percentual_tempo_integral"}:
        return "Matrículas por localização da escola; não mede capacidade, procura efetiva ou cobertura populacional."
    if metric == "inse_mean":
        return "O universo são alunos avaliados, não a população residente do município."
    if metric in {"students_per_class", "estudantes_por_docente"}:
        return "Razão descritiva de organização escolar; não demonstra capacidade nem efeito causal."
    if metric.startswith("schools_with_"):
        return "Condição declarada por escola; não mede qualidade de uso nem efeito sobre trajetória."
    if metric == "teacher_adequacy_percent":
        return "Adequação por docência em período próprio; associação não implica efeito causal."
    return "Métrica contextual descritiva, sem causalidade, correlação como insight ou índice sintético."


def _metric_definition(metric: str) -> str:
    definitions = {
        "schools_with_broadband_percent": "Percentual de escolas com banda larga no recorte declarado.",
        "schools_with_drinking_water_percent": "Percentual de escolas com água potável no recorte declarado.",
        "schools_with_internet_percent": "Percentual de escolas com internet no recorte declarado.",
        "schools_with_library_percent": "Percentual de escolas com biblioteca no recorte declarado.",
        "schools_with_sports_court_percent": "Percentual de escolas com quadra esportiva no recorte declarado.",
        "students_per_class": "Média declarada de estudantes por turma.",
        "estudantes_por_docente": "Razão declarada de estudantes por docente.",
        "teacher_adequacy_percent": "Percentual de docências no grupo de adequação informado.",
        "inse_mean": "Média do INSE dos alunos avaliados.",
        "matriculas_tempo_integral": "Contagem de matrículas em tempo integral.",
        "percentual_tempo_integral": "Percentual municipal de matrículas em tempo integral.",
    }
    if metric in definitions:
        return definitions[metric]
    if metric.startswith("ied_"):
        return "Percentual de docentes na faixa declarada do Indicador de Esforço Docente."
    if metric in IRD_METRICS:
        return "Percentual de escolas na faixa declarada do Indicador de Regularidade Docente."
    return f"Métrica oficial preservada no contrato de origem: {metric}."


def _conditions_panel(source_root: Path = SOURCE_ROOT) -> pd.DataFrame:
    panel = _read_csv(source_root / "PAINEL_CONDICOES_ESCOLARES_TOTAL_V1.csv.gz")
    panel = _apply_comparator_coverage(panel)
    panel["causal_interpretation_allowed"] = False
    panel["correlation_used_as_insight"] = False

    metric_counts = (
        panel[panel["value_status"].eq("observed")]
        .groupby("metric")
        .size()
        .to_dict()
    )
    panel["metric_observation_count"] = panel["metric"].map(metric_counts).fillna(0).astype(int)
    panel["metric_definition"] = panel["metric"].map(_metric_definition)
    panel["definition_and_unit_validated"] = panel["metric_definition"].notna() & panel["unit"].notna()
    panel["period_explicit"] = panel["year"].notna()
    panel["lens_declared"] = panel["territorial_lens"].notna() & panel["territorial_lens"].astype(str).ne("")
    panel["visual_semantic_limit"] = panel["metric"].map(_semantic_limit)
    panel["absence_of_causality"] = True
    panel["visual_metric_allowlisted"] = (
        panel["metric_observation_count"].gt(0)
        & panel["definition_and_unit_validated"]
        & panel["period_explicit"]
        & panel["lens_declared"]
        & panel["coverage_fraction"].notna()
        & panel["visual_semantic_limit"].notna()
        & panel["absence_of_causality"]
        & ~panel["metric"].isin(ZERO_OBSERVATION_VISUAL_EXCLUSIONS)
    )
    panel["visual_allowlist_state"] = np.where(
        panel["visual_metric_allowlisted"],
        "VISUAL_PROFILE_ALLOWLISTED",
        "QA_AVAILABILITY_ONLY_ZERO_OBSERVATIONS",
    )
    panel["visual_row_eligible"] = panel["visual_metric_allowlisted"] & panel["value_status"].eq("observed")

    ird = panel["metric"].isin(IRD_METRICS)
    panel.loc[ird, "counting_unit"] = "school"
    closure = (
        panel[ird & panel["value_status"].eq("observed")]
        .groupby(["municipality_ibge_code", "year"])["value"]
        .sum()
        .rename("ird_four_band_sum_percent")
        .reset_index()
    )
    panel = panel.merge(closure, how="left", on=["municipality_ibge_code", "year"])
    panel["ird_four_band_closure_ok"] = pd.NA
    panel.loc[ird, "ird_four_band_closure_ok"] = (
        panel.loc[ird, "ird_four_band_sum_percent"].sub(100).abs().le(0.2)
    )
    return panel.sort_values(["municipality_ibge_code", "year", "stage", "metric"], kind="mergesort").reset_index(drop=True)


def _regional_integral_panel(teachers: pd.DataFrame) -> pd.DataFrame:
    stages = ("educacao_infantil", "fundamental", "medio", "anos_iniciais", "anos_finais")
    rows: list[dict[str, Any]] = []
    for year in range(2014, 2026):
        for stage in stages:
            numerator = teachers[
                teachers["year"].eq(year)
                & teachers["stage"].eq(stage)
                & teachers["metric"].eq("matriculas_tempo_integral")
                & teachers["value_status"].eq("observed")
            ]
            denominator = teachers[
                teachers["year"].eq(year)
                & teachers["stage"].eq(stage)
                & teachers["metric"].eq("matriculas")
                & teachers["value_status"].eq("observed")
            ]
            shares = teachers[
                teachers["year"].eq(year)
                & teachers["stage"].eq(stage)
                & teachers["metric"].eq("percentual_tempo_integral")
                & teachers["value_status"].eq("observed")
            ]
            numerator_codes = set(numerator["municipality_ibge_code"].dropna())
            denominator_codes = set(denominator["municipality_ibge_code"].dropna())
            share_codes = set(shares["municipality_ibge_code"].dropna())
            exact_components = (
                numerator_codes == set(EXPECTED_CODES)
                and denominator_codes == set(EXPECTED_CODES)
                and share_codes == set(EXPECTED_CODES)
            )
            denominator_total = float(pd.to_numeric(denominator["value"], errors="coerce").sum()) if exact_components else None
            numerator_total = float(pd.to_numeric(numerator["value"], errors="coerce").sum()) if len(numerator) else None
            weighted = (
                numerator_total / denominator_total * 100
                if exact_components and denominator_total is not None and denominator_total > 0
                else None
            )
            municipal_median = (
                float(pd.to_numeric(shares["value"], errors="coerce").median())
                if share_codes == set(EXPECTED_CODES)
                else None
            )
            rows.append(
                {
                    "year": year,
                    "region_id": "vale_do_sinos",
                    "region_name": "Vale do Sinos",
                    "stage": stage,
                    "regional_integral_enrollments": numerator_total,
                    "regional_total_enrollments": denominator_total,
                    "regional_integral_share": weighted,
                    "municipal_integral_share_median": municipal_median,
                    "observed_municipality_count": len(share_codes),
                    "expected_municipality_count": 10,
                    "coverage_fraction": len(share_codes) / 10,
                    "regional_distribution_eligible": share_codes == set(EXPECTED_CODES),
                    "regional_integral_share_eligible": exact_components and denominator_total is not None and denominator_total > 0,
                    "exact_component_contract_compatible": exact_components,
                    "availability_state": (
                        "AVAILABLE_EXACT_COMPONENT_SUM"
                        if exact_components and denominator_total is not None and denominator_total > 0
                        else "UNAVAILABLE_EXACT_COMPATIBLE_DENOMINATOR"
                    ),
                    "numerator_metric": "matriculas_tempo_integral",
                    "denominator_metric": "matriculas" if len(denominator) else None,
                    "municipal_share_metric": "percentual_tempo_integral",
                    "formula": "sum(matriculas_tempo_integral) / sum(matriculas_totais) * 100",
                    "regional_percentage_method": "sum_exact_components" if exact_components else "not_computed",
                    "municipal_distribution_method": "median_of_ten_municipal_percentages",
                    "numerator_source_table": "public.vw_educacao_matriculas",
                    "denominator_source_table": "public.vw_educacao_turmas_docentes" if len(denominator) else None,
                    "component_contract": "municipality_year_stage|total_all_dependencies|school_location|matricula",
                    "network_scope": "total_all_dependencies",
                    "source_dependency_qa": "total",
                    "source_location_qa": "total",
                    "territorial_lens": "school_location",
                    "counting_unit": "matricula",
                    "unit": "percent",
                    "is_coverage_rate": False,
                    "is_demand_forecast": False,
                    "is_capacity_measure": False,
                }
            )
    return pd.DataFrame(rows).sort_values(["year", "stage"], kind="mergesort").reset_index(drop=True)


def _pressure_panel(source_root: Path = SOURCE_ROOT) -> pd.DataFrame:
    panel = _read_csv(source_root / "PAINEL_PRESSAO_MECANICA_COORTES_AUDITADO_V1.csv.gz")
    required = panel["stage"].map({"pre_escola": 2, "fundamental": 9, "medio": 3})
    if required.isna().any():
        raise ValueError("Etapa sem largura obrigatória de janela etária.")
    observed_min = pd.to_numeric(panel["source_age_min"], errors="raise").clip(lower=0)
    observed_max = pd.to_numeric(panel["source_age_max"], errors="raise")
    observed_width = (observed_max - observed_min + 1).clip(lower=0).astype(int)
    panel["required_source_age_window_width"] = required.astype(int)
    panel["observed_source_age_window_width"] = observed_width
    panel["cohort_window_complete"] = (
        pd.to_numeric(panel["source_age_min"], errors="raise").ge(0)
        & observed_width.ge(required)
    )
    panel["availability_state"] = np.where(
        panel["cohort_window_complete"],
        "AVAILABLE_COMPLETE_COHORT_WINDOW",
        "PARTIAL_COHORT_NOT_YET_OBSERVED_AT_REFERENCE_YEAR",
    )

    incomplete = ~panel["cohort_window_complete"]
    null_when_incomplete = [
        "mechanical_cohort_size",
        "cohort_to_baseline_enrollment_ratio",
        "audited_mechanical_cohort_size",
        "cohort_size_closure_residual",
        "recomputed_ratio",
        "formula_closure_residual",
        "mechanical_difference_from_baseline_enrollments",
        "position_low_to_high_among_ten",
        "percentile_low_to_high_among_ten",
        "vale_municipal_median_ratio",
        "difference_from_vale_municipal_median_ratio",
    ]
    for column in null_when_incomplete:
        panel.loc[incomplete, column] = np.nan

    panel["_entity_key"] = panel["municipality_ibge_code"].fillna("__REGION__")
    valid = panel[panel["cohort_window_complete"] & panel["cohort_to_baseline_enrollment_ratio"].notna()]
    horizon = (
        valid.groupby(["entity_scope", "_entity_key", "stage"])["cohort_to_baseline_enrollment_ratio"]
        .agg(
            horizon_min_ratio="min",
            horizon_max_ratio="max",
            horizon_observed_complete_year_count="count",
        )
        .reset_index()
    )
    horizon["horizon_ratio_range"] = horizon["horizon_max_ratio"] - horizon["horizon_min_ratio"]
    bounds = (
        valid.groupby(["entity_scope", "_entity_key", "stage"])["target_year"]
        .agg(horizon_complete_start_year="min", horizon_complete_end_year="max")
        .reset_index()
    )
    panel = panel.drop(columns=["horizon_min_ratio", "horizon_max_ratio", "horizon_ratio_range"])
    panel = panel.merge(horizon, how="left", on=["entity_scope", "_entity_key", "stage"])
    panel = panel.merge(bounds, how="left", on=["entity_scope", "_entity_key", "stage"])

    for column in [
        "position_low_to_high_among_ten",
        "percentile_low_to_high_among_ten",
        "vale_municipal_median_ratio",
        "difference_from_vale_municipal_median_ratio",
    ]:
        panel[column] = np.nan
    for (target_year, stage), group in panel.groupby(["target_year", "stage"], sort=False):
        municipal = group[
            group["entity_scope"].eq("municipality")
            & group["cohort_window_complete"]
            & group["cohort_to_baseline_enrollment_ratio"].notna()
        ]
        if len(municipal) != 10:
            continue
        positions = municipal["cohort_to_baseline_enrollment_ratio"].rank(method="min")
        median = float(municipal["cohort_to_baseline_enrollment_ratio"].median())
        panel.loc[municipal.index, "position_low_to_high_among_ten"] = positions.to_numpy()
        panel.loc[municipal.index, "percentile_low_to_high_among_ten"] = ((positions - 1) / 9 * 100).to_numpy()
        complete_group = (
            panel["target_year"].eq(target_year)
            & panel["stage"].eq(stage)
            & panel["cohort_window_complete"]
        )
        panel.loc[complete_group, "vale_municipal_median_ratio"] = median
        panel.loc[complete_group, "difference_from_vale_municipal_median_ratio"] = (
            panel.loc[complete_group, "cohort_to_baseline_enrollment_ratio"] - median
        )

    panel["cohort_lens"] = "resident_population"
    panel["baseline_enrollment_lens"] = "school_location"
    panel["mixed_lens_ratio"] = True
    panel["is_coverage_rate"] = False
    panel["is_demand_forecast"] = False
    panel["is_capacity_measure"] = False
    panel = panel.drop(columns=["_entity_key"])
    return panel.sort_values(["entity_scope", "municipality_ibge_code", "stage", "target_year"], kind="mergesort", na_position="last").reset_index(drop=True)


MATRIX_PROFILES: dict[str, dict[str, Any]] = {
    "D1_TRAJETORIA_OFICIAL_DESCRITIVA_V1": {"subject": "taxas oficiais municipais de trajetória", "mechanism": "As taxas são resultados escolares observados, não mecanismo anterior ao resultado.", "lenses": "Rede total e localização da escola são constantes; a dependência administrativa aparece apenas em QA.", "period": "2018–2025 é preservado, com 2020–2021 destacados e segmentos 2018–2019 e 2022–2025.", "stability": "Sem denominadores exatos, não há condição para afirmar estabilidade ou padrão persistente.", "integration": "Aprovação, reprovação e abandono fecham 100%; distorção permanece série separada.", "difference": "Os dez municípios sustentam distribuição municipal, nunca taxa do Vale.", "communication": "A linha exige ruptura visual em 2020–2021 e posição sem sentido de desempenho.", "source": "Inep, taxas oficiais municipais, grão município × ano × etapa × indicador.", "distinct": "Substitui a duplicação editorial por quatro abas de etapa com uma única evidência técnica.", "beyond": "Acrescenta trajetória escolar oficial, além do tamanho das coortes.", "question": "Como aprovação, reprovação, abandono e distorção se moveram em cada etapa?", "statuses": ("SUPPORTED", "NOT_SUPPORTED", "SUPPORTED", "PARTIAL", "NOT_EVALUABLE", "SUPPORTED", "SUPPORTED", "SUPPORTED", "SUPPORTED", "SUPPORTED", "SUPPORTED", "SUPPORTED")},
    "D2_TAXA_REGIONAL_TRAJETORIA_EXATA": {"subject": "taxa regional exata de trajetória", "mechanism": "O objeto exigiria componentes regionais, ausentes no contrato congelado.", "lenses": "Não existe numerador e denominador regional no mesmo contrato.", "period": "Nenhuma janela regional comparável pode ser construída com médias municipais.", "stability": "Sem taxa regional, estabilidade regional não é avaliável.", "integration": "As taxas municipais não podem ser agregadas como substituto dos componentes faltantes.", "difference": "Distribuição municipal não mede um valor regional exato.", "communication": "Qualquer número regional seria enganoso; H2 permanece congelada.", "source": "A ausência é rastreada no contrato v1.1 e no painel municipal oficial.", "distinct": "Mantido apenas como lacuna metodológica, sem nova história.", "beyond": "Não há valor analítico adicional enquanto os componentes seguirem ausentes.", "question": "É possível calcular uma taxa do Vale com componentes exatos?", "statuses": ("SUPPORTED", "NOT_SUPPORTED", "NOT_EVALUABLE", "NOT_EVALUABLE", "NOT_EVALUABLE", "NOT_EVALUABLE", "NOT_EVALUABLE", "SUPPORTED", "NOT_SUPPORTED", "SUPPORTED", "PARTIAL", "NOT_SUPPORTED")},
    "D1_EDUCACAO_INFANTIL_OBSERVADA_V1": {"subject": "educação infantil observada", "mechanism": "População por idade e organização da oferta antecedem decisões de planejamento, sem inferir fluxo causal.", "lenses": "População residente e localização da escola ficam declaradas e não são fundidas em cobertura.", "period": "População, matrículas, turmas e escolas cobrem 2014–2025 nos dez municípios.", "stability": "Há série longa, mas nenhuma regra formal de estabilidade foi aplicada.", "integration": "Cinco medidas observadas são mantidas no mesmo objeto, com lente própria por medida.", "difference": "A cobertura 10/10 permite distribuição municipal do Vale.", "communication": "O objeto é visualmente utilizável se não for chamado de cobertura ou demanda.", "source": "Painel congelado do Job 5G-A, sem linhas municipais de nascimentos.", "distinct": "Separa evidência observada da lacuna de nascimentos.", "beyond": "Combina demografia observada com oferta escolar sem confundir universos.", "question": "Como população 0–3 e 4–5, matrículas, turmas e escolas evoluíram?", "statuses": ("SUPPORTED", "PARTIAL", "PARTIAL", "SUPPORTED", "PARTIAL", "SUPPORTED", "SUPPORTED", "SUPPORTED", "SUPPORTED", "SUPPORTED", "SUPPORTED", "PARTIAL")},
    "D1_NASCIMENTOS_EDUCACAO_INFANTIL": {"subject": "nascimentos e educação infantil", "mechanism": "Nascimentos poderiam anteceder demanda, mas a série municipal está ausente.", "lenses": "Endpoints regionais não são substitutos da residência materna municipal nem da localização escolar.", "period": "Somente 2015 e 2024 existem como endpoints regionais; não há série municipal contínua.", "stability": "A ausência da série impede qualquer avaliação de estabilidade.", "integration": "População e rede são observadas, mas não podem ser ligadas aos nascimentos faltantes.", "difference": "Sem nascimentos municipais, não há diferença municipal comparável.", "communication": "O objeto deve aparecer apenas como insuficiência de dados.", "source": "Endpoints congelados do Vale e 100 linhas municipais explicitamente indisponíveis no original.", "distinct": "Registra a lacuna sem rebaixar a educação infantil observada.", "beyond": "Sem série de nascimentos, não acrescenta evidência além da demografia já observada.", "question": "Nascimentos municipais ajudam a antecipar a educação infantil?", "statuses": ("SUPPORTED", "PARTIAL", "NOT_SUPPORTED", "PARTIAL", "NOT_EVALUABLE", "PARTIAL", "NOT_SUPPORTED", "SUPPORTED", "NOT_SUPPORTED", "SUPPORTED", "SUPPORTED", "NOT_SUPPORTED")},
    "D2_NASCIMENTOS_MIGRACAO_OFERTA": {"subject": "nascimentos, migração e oferta", "mechanism": "Migração é um mecanismo plausível, porém não observado no pacote.", "lenses": "Residência, migração e localização da escola não podem ser juntadas sem uma fonte de mobilidade.", "period": "Não existe janela temporal municipal comum para nascimentos e migração.", "stability": "Não há variável de migração para testar estabilidade.", "integration": "A ligação entre os fatos dependeria de uma variável ausente.", "difference": "Diferença municipal de migração não é mensurável.", "communication": "Uma história de fluxo seria especulativa e permanece proibida.", "source": "A indisponibilidade está registrada na errata e no pacote de revisão.", "distinct": "Mantém migração como limite, não como nova análise.", "beyond": "Não produz valor além da demografia observada sem mobilidade medida.", "question": "Migração explica a relação entre coortes residentes e oferta escolar?", "statuses": ("SUPPORTED", "NOT_SUPPORTED", "NOT_SUPPORTED", "NOT_EVALUABLE", "NOT_EVALUABLE", "NOT_SUPPORTED", "NOT_SUPPORTED", "SUPPORTED", "NOT_SUPPORTED", "SUPPORTED", "SUPPORTED", "NOT_SUPPORTED")},
    "D1_DOCENTES_TURMAS_JORNADA": {"subject": "docentes, turmas e jornada", "mechanism": "Organização docente e jornada são condições anteriores, mas HAD/IED têm cobertura parcial.", "lenses": "Rede total e localização da escola são compatíveis; HAD/IED são locais 2/10.", "period": "Séries de 2014–2025 coexistem com indicadores de fotografia 2025 explicitamente separados.", "stability": "A série longa não recebeu teste formal de estabilidade e os indicadores 2025 não têm histórico comparável.", "integration": "Docentes, turmas, matrículas e tempo integral podem ser lidos juntos, com HAD/IED local-only.", "difference": "Comparações do Vale só permanecem nos grãos 10/10.", "communication": "O painel é utilizável com badges de cobertura e sem frases ‘entre os dez’ nos grãos parciais.", "source": "Censo Escolar e indicadores Inep preservados com fonte, unidade, lente e período.", "distinct": "Organiza oferta e trabalho docente sem duplicar o perfil de condições.", "beyond": "Acrescenta estrutura de oferta, não apenas demografia.", "question": "Como docentes, turmas e jornada organizam a oferta municipal?", "statuses": ("SUPPORTED", "SUPPORTED", "PARTIAL", "SUPPORTED", "PARTIAL", "SUPPORTED", "SUPPORTED", "SUPPORTED", "SUPPORTED", "SUPPORTED", "PARTIAL", "SUPPORTED")},
    "D1_TRAJETORIA_ADEQUACAO_DOCENTE": {"subject": "adequação da formação docente", "mechanism": "Adequação é condição escolar anterior, sem identificação de efeito sobre resultados.", "lenses": "A unidade é docência e o recorte escolar é declarado.", "period": "O período próprio do indicador é preservado sem interpolação.", "stability": "Há observações repetidas, mas não foi aplicado gate formal de estabilidade.", "integration": "Pode compor o perfil docente, não uma explicação causal de trajetória.", "difference": "Cobertura completa nos grãos elegíveis permite distribuição municipal.", "communication": "Percentual deve ser rotulado por docência e sem linguagem causal.", "source": "Indicador oficial de adequação docente, com unidade e grão preservados.", "distinct": "É dimensão específica da qualificação docente.", "beyond": "Adiciona contexto de formação à leitura demográfica.", "question": "Qual é a adequação docente observada por etapa?", "statuses": ("SUPPORTED", "SUPPORTED", "SUPPORTED", "SUPPORTED", "PARTIAL", "PARTIAL", "SUPPORTED", "SUPPORTED", "SUPPORTED", "SUPPORTED", "PARTIAL", "SUPPORTED")},
    "D1_TRAJETORIA_ALUNOS_TURMA": {"subject": "estudantes por turma", "mechanism": "Tamanho de turma é condição organizacional, não efeito causal demonstrado.", "lenses": "A razão usa turma e matrícula na localização escolar declarada.", "period": "A série 2014–2025 mantém anos e etapas próprios.", "stability": "Nenhum limiar de estabilidade foi pré-registrado.", "integration": "A métrica pode acompanhar turmas e matrículas, sem correlação como insight.", "difference": "Grãos 10/10 permitem comparação distributiva municipal.", "communication": "A razão é descritiva e não deve ser chamada de capacidade.", "source": "Censo Escolar no painel docentes/turmas e no perfil de condições.", "distinct": "Resume organização de turmas sem criar índice sintético.", "beyond": "Acrescenta intensidade organizacional à demografia.", "question": "Quantos estudantes por turma são observados por etapa?", "statuses": ("SUPPORTED", "PARTIAL", "SUPPORTED", "SUPPORTED", "PARTIAL", "PARTIAL", "SUPPORTED", "SUPPORTED", "SUPPORTED", "SUPPORTED", "PARTIAL", "SUPPORTED")},
    "D1_TRAJETORIA_ESFORCO_DOCENTE": {"subject": "Indicador de Esforço Docente", "mechanism": "Esforço docente é condição anterior, mas somente dois municípios têm observação normalizada.", "lenses": "A unidade e as faixas são válidas localmente; a distribuição do Vale é inelegível.", "period": "A fotografia 2025 não pode ser comparada com anos anteriores por quebra metodológica.", "stability": "Uma fotografia com cobertura 2/10 não permite estabilidade.", "integration": "IED pode integrar fatos locais de Nova Santa Rita e São Leopoldo, sem síntese regional.", "difference": "Cobertura 2/10 proíbe C7 regional, posição e mediana do Vale.", "communication": "Somente ficha local descritiva é comunicável.", "source": "Indicador Inep normalizado, com cobertura observada explicitamente 2/10.", "distinct": "Mantém esforço separado de adequação e regularidade.", "beyond": "Oferece contexto docente local além da demografia.", "question": "Como se distribuem as faixas de esforço docente onde há observação?", "statuses": ("SUPPORTED", "SUPPORTED", "PARTIAL", "SUPPORTED", "NOT_EVALUABLE", "PARTIAL", "NOT_SUPPORTED", "SUPPORTED", "NOT_SUPPORTED", "SUPPORTED", "SUPPORTED", "SUPPORTED")},
    "D1_TRAJETORIA_HORAS_AULA": {"subject": "Horas-Aula Diária", "mechanism": "Jornada declarada é condição de oferta, observada apenas em dois municípios.", "lenses": "A métrica local é válida; a distribuição regional não tem 10/10.", "period": "HAD é fotografia 2025 e não forma trajetória histórica neste pacote.", "stability": "Uma única fotografia 2/10 não permite estabilidade.", "integration": "HAD pode acompanhar a jornada local, sem equivaler a tempo efetivo.", "difference": "Cobertura 2/10 proíbe posição, percentil e mediana do Vale.", "communication": "O rótulo obrigatório é LOCAL_DESCRIPTIVE_ONLY.", "source": "Indicador Inep HAD para Nova Santa Rita e São Leopoldo.", "distinct": "Distingue jornada declarada de matrícula em tempo integral.", "beyond": "Acrescenta organização temporal local à demografia.", "question": "Qual jornada declarada aparece por etapa nos municípios observados?", "statuses": ("SUPPORTED", "SUPPORTED", "PARTIAL", "SUPPORTED", "NOT_EVALUABLE", "PARTIAL", "NOT_SUPPORTED", "SUPPORTED", "NOT_SUPPORTED", "SUPPORTED", "SUPPORTED", "SUPPORTED")},
    "D1_TRAJETORIA_REGULARIDADE_DOCENTE": {"subject": "Indicador de Regularidade Docente", "mechanism": "Regularidade é condição organizacional, mas o indicador mede escolas, não docentes.", "lenses": "As quatro faixas usam escola como unidade e cobrem os dez municípios.", "period": "Há somente fotografia 2025.", "stability": "Uma fotografia não permite avaliar estabilidade temporal.", "integration": "As quatro faixas fecham 100% por município e podem compor o perfil docente.", "difference": "A cobertura 10/10 permite distribuição municipal da fotografia.", "communication": "O gráfico deve dizer ‘escolas por faixa’, nunca ‘docentes’.", "source": "IRD_MUNICIPIOS_2025, quatro faixas auditadas por código IBGE.", "distinct": "Regularidade é distinta de esforço e adequação.", "beyond": "Acrescenta continuidade organizacional escolar à demografia.", "question": "Como as escolas se distribuem nas quatro faixas de regularidade?", "statuses": ("SUPPORTED", "PARTIAL", "SUPPORTED", "NOT_EVALUABLE", "NOT_EVALUABLE", "PARTIAL", "SUPPORTED", "SUPPORTED", "SUPPORTED", "SUPPORTED", "SUPPORTED", "SUPPORTED")},
    "D1_TRAJETORIA_TEMPO_INTEGRAL": {"subject": "tempo integral", "mechanism": "Jornada integral é condição de oferta anterior, sem equivaler a capacidade ou procura.", "lenses": "Numerador e denominador usam rede total, localização escolar e etapa compatíveis.", "period": "Educação infantil, fundamental e médio têm componentes completos de 2014–2025.", "stability": "A série é longa, mas estabilidade formal não foi testada.", "integration": "O percentual regional é soma de componentes; a mediana municipal fica separada.", "difference": "Os dez municípios permitem distribuição e agregado ponderado nas etapas compatíveis.", "communication": "O percentual do Vale nunca é a mediana municipal.", "source": "Censo Escolar: matrículas totais, integrais e percentuais municipais reconciliados.", "distinct": "Separa agregado regional ponderado da distribuição municipal.", "beyond": "Acrescenta organização de jornada à demografia.", "question": "Qual parcela ponderada das matrículas do Vale está em tempo integral?", "statuses": ("SUPPORTED", "SUPPORTED", "SUPPORTED", "SUPPORTED", "PARTIAL", "SUPPORTED", "SUPPORTED", "SUPPORTED", "SUPPORTED", "SUPPORTED", "SUPPORTED", "SUPPORTED")},
    "D1_PERFIL_CONDICOES_ESCOLARES_TOTAL_V1": {"subject": "perfil de condições escolares", "mechanism": "Condições são contexto anterior, sem causalidade identificada.", "lenses": "Cada métrica preserva unidade, período e lente; cobertura regional é avaliada por grão.", "period": "Períodos próprios são explícitos e não são comprimidos em uma única data.", "stability": "As séries não receberam um gate uniforme de estabilidade.", "integration": "A allowlist combina apenas métricas observadas e mantém indisponibilidades em QA.", "difference": "Distribuição do Vale aparece somente quando 10/10 estão observados.", "communication": "Sem cartões vazios, índice sintético ou correlação como história.", "source": "Painel de condições com fonte, unidade, cobertura e limite semântico por linha.", "distinct": "Concentra contexto visual sem duplicar todas as histórias temáticas.", "beyond": "Acrescenta condições concretas da oferta à demografia.", "question": "Quais condições escolares observadas merecem acompanhamento municipal?", "statuses": ("SUPPORTED", "PARTIAL", "SUPPORTED", "SUPPORTED", "PARTIAL", "SUPPORTED", "SUPPORTED", "SUPPORTED", "SUPPORTED", "SUPPORTED", "SUPPORTED", "SUPPORTED")},
    "D1_TRAJETORIA_CONECTIVIDADE": {"subject": "conectividade escolar", "mechanism": "Conectividade é condição de oferta, não causa demonstrada de trajetória.", "lenses": "Percentuais referem-se a escolas na lente declarada.", "period": "A série anual mantém o período explícito do Censo Escolar.", "stability": "Não foi aplicado limiar formal de estabilidade.", "integration": "Internet e banda larga entram no perfil apenas onde observadas.", "difference": "Cobertura elegível permite distribuição municipal.", "communication": "Disponibilidade não deve ser narrada como qualidade de uso.", "source": "Indicadores de escolas com internet e banda larga no painel de condições.", "distinct": "Conectividade é subdimensão reconhecível do perfil.", "beyond": "Adiciona infraestrutura digital à demografia.", "question": "Qual conectividade é declarada pelas escolas do município?", "statuses": ("SUPPORTED", "PARTIAL", "SUPPORTED", "SUPPORTED", "PARTIAL", "PARTIAL", "SUPPORTED", "SUPPORTED", "SUPPORTED", "SUPPORTED", "PARTIAL", "SUPPORTED")},
    "D1_TRAJETORIA_INFRAESTRUTURA": {"subject": "infraestrutura escolar", "mechanism": "Infraestrutura é condição contextual, não medida de capacidade ou causa.", "lenses": "A unidade é escola e a cobertura é explícita por indicador.", "period": "Cada indicador conserva seu ano de referência.", "stability": "Não há teste de estabilidade comum e três métricas têm zero observações.", "integration": "Água, quadra e biblioteca ficam somente em QA enquanto vazias.", "difference": "Só métricas com 10/10 podem usar distribuição regional.", "communication": "A allowlist impede cartões vazios e conclusões de capacidade.", "source": "Painel de condições e estados de disponibilidade do Job 5G-A.", "distinct": "Infraestrutura permanece dimensão do perfil, não índice autônomo.", "beyond": "Quando observada, acrescenta condição física à demografia.", "question": "Quais itens de infraestrutura têm observação utilizável?", "statuses": ("SUPPORTED", "PARTIAL", "SUPPORTED", "SUPPORTED", "PARTIAL", "PARTIAL", "SUPPORTED", "SUPPORTED", "SUPPORTED", "SUPPORTED", "PARTIAL", "SUPPORTED")},
    "D1_TRAJETORIA_INSE": {"subject": "INSE", "mechanism": "Contexto socioeconômico é anterior, sem efeito causal estimado.", "lenses": "O universo são alunos avaliados, diferente da população residente.", "period": "As três observações preservam seus anos próprios.", "stability": "Poucos pontos não sustentam estabilidade suficiente.", "integration": "INSE pode contextualizar o perfil se sua população for explicitada.", "difference": "A cobertura observada por grão define se a distribuição é elegível.", "communication": "O rótulo deve mencionar alunos avaliados.", "source": "Indicador INSE preservado com fonte e lente de avaliação.", "distinct": "É contexto socioeconômico, não demografia residente.", "beyond": "Acrescenta perfil dos avaliados com caveat de universo.", "question": "Que contexto socioeconômico aparece entre os alunos avaliados?", "statuses": ("SUPPORTED", "PARTIAL", "PARTIAL", "SUPPORTED", "PARTIAL", "PARTIAL", "SUPPORTED", "SUPPORTED", "SUPPORTED", "SUPPORTED", "SUPPORTED", "SUPPORTED")},
    "D2_CAUSAL_CONDICOES_TRAJETORIA": {"subject": "efeito causal das condições sobre trajetória", "mechanism": "O desenho descritivo não identifica efeito causal.", "lenses": "Condições e resultados têm universos distintos que exigiriam desenho causal próprio.", "period": "As janelas observacionais não constituem exposição e resultado comparáveis.", "stability": "Estabilidade não resolve confusão nem identificação causal.", "integration": "Juntar painéis descritivos não cria contrafactual.", "difference": "Diferenças municipais podem refletir composição e não efeito.", "communication": "A afirmação causal permanece proibida.", "source": "A proibição é rastreada no contrato, na allowlist e na errata.", "distinct": "Mantido como exclusão metodológica, não como história.", "beyond": "Não há valor causal adicional sem desenho identificador.", "question": "As condições escolares causam mudanças na trajetória?", "statuses": ("SUPPORTED", "NOT_SUPPORTED", "PARTIAL", "PARTIAL", "NOT_EVALUABLE", "NOT_SUPPORTED", "NOT_SUPPORTED", "SUPPORTED", "NOT_SUPPORTED", "SUPPORTED", "SUPPORTED", "NOT_SUPPORTED")},
    "D1_COORTES_DEMANDA_FUTURA_MECANICA": {"subject": "pressão mecânica de coortes", "mechanism": "Tamanho de coorte antecede a etapa, mas não incorpora migração, fluxo ou escolha escolar.", "lenses": "População residente no numerador e matrícula por localização no denominador formam razão de lentes mistas.", "period": "Referência 2025 e horizontes 2026–2030; pré-escola 2030 é não avaliável por janela 1/2.", "stability": "Quatro ou cinco horizontes completos permitem faixa mecânica, não estabilidade estrutural.", "integration": "Coorte e matrícula-base são integradas somente pela fórmula mecânica explícita.", "difference": "Dez municípios permitem distribuição apenas nas janelas completas.", "communication": "Deve ser chamada pressão mecânica, nunca previsão, cobertura, demanda ou capacidade.", "source": "População por idade e matrícula-base congeladas; 11 linhas incompletas anuladas.", "distinct": "A razão mecânica é separada do painel de educação infantil e da trajetória.", "beyond": "Combina demografia com base escolar sem extrapolar para previsão.", "question": "Como coortes completas se comparam mecanicamente à matrícula-base de 2025?", "statuses": ("SUPPORTED", "SUPPORTED", "PARTIAL", "PARTIAL", "PARTIAL", "SUPPORTED", "SUPPORTED", "SUPPORTED", "PARTIAL", "SUPPORTED", "SUPPORTED", "SUPPORTED")},
    "D1_COORTES_TRANSICOES_ETAPAS": {"subject": "transições mecânicas entre etapas", "mechanism": "A janela etária desloca-se mecanicamente, sem modelar fluxo escolar.", "lenses": "As coortes residentes e as matrículas escolares são lentes diferentes declaradas.", "period": "Horizontes 2026–2030 têm larguras 2, 9 e 3; a pré-escola 2030 está incompleta.", "stability": "Sem fluxo, retenção e migração, estabilidade de transição não é avaliável.", "integration": "A sobreposição de janelas é auditada, mas não estima passagem entre etapas.", "difference": "Janelas completas permitem diferenças municipais descritivas.", "communication": "A visualização deve destacar indisponibilidade, não preencher a coorte parcial.", "source": "Painel auditado v1.1 com larguras requerida e observada.", "distinct": "Explicita janelas e não duplica a razão como previsão.", "beyond": "Acrescenta calendário mecânico, com valor limitado além da demografia.", "question": "Quais janelas etárias completas alimentam cada horizonte de etapa?", "statuses": ("SUPPORTED", "SUPPORTED", "PARTIAL", "PARTIAL", "NOT_EVALUABLE", "PARTIAL", "SUPPORTED", "SUPPORTED", "PARTIAL", "SUPPORTED", "PARTIAL", "PARTIAL")},
    "D2_PREVISAO_MATRICULA_POR_COORTE": {"subject": "previsão de matrícula por coorte", "mechanism": "A pressão mecânica não observa migração, retenção, mobilidade ou escolha de escola.", "lenses": "Razão de população residente e matrícula por localização não é taxa de conversão.", "period": "Uma base 2025 e horizontes mecânicos não formam modelo temporal validado.", "stability": "Não há janela de validação fora da amostra nem erro de previsão.", "integration": "Componentes faltantes impedem transformar a razão em forecast.", "difference": "Diferenças mecânicas municipais não são diferenças de demanda prevista.", "communication": "Previsão, demanda e capacidade permanecem termos proibidos.", "source": "A negativa é rastreada nos flags is_demand_forecast=false e is_capacity_measure=false.", "distinct": "Mantido como exclusão para impedir reinterpretação da pressão mecânica.", "beyond": "A formulação de previsão não acrescenta valor suportado.", "question": "A coorte mecânica permite prever matrículas futuras?", "statuses": ("SUPPORTED", "NOT_SUPPORTED", "NOT_SUPPORTED", "NOT_SUPPORTED", "NOT_EVALUABLE", "NOT_SUPPORTED", "NOT_SUPPORTED", "SUPPORTED", "NOT_SUPPORTED", "SUPPORTED", "SUPPORTED", "PARTIAL")},
}


def _opportunity_matrix(source_root: Path = SOURCE_ROOT) -> pd.DataFrame:
    original = _read_csv(source_root / "MATRIZ_OPORTUNIDADES_REAVALIADAS_JOB5GA.csv.gz")
    base = original[["analysis_id", "front", "classification", "classification_reason", "primary_limitation"]].copy()
    observed_row = pd.DataFrame(
        [
            {
                "analysis_id": "D1_EDUCACAO_INFANTIL_OBSERVADA_V1",
                "front": "B",
                "classification": "READY_FOR_INTERNAL_VISUAL_PROTOTYPE",
                "classification_reason": "População 0–3 e 4–5, matrículas, turmas e escolas preservadas em objeto próprio.",
                "primary_limitation": "RESIDENT_AND_SCHOOL_LOCATION_LENSES_REMAIN_SEPARATE",
            }
        ]
    )
    base = pd.concat([base, observed_row], ignore_index=True)
    base.loc[base["analysis_id"].eq("D1_COORTES_DEMANDA_FUTURA_MECANICA"), "classification"] = "PROMISING_NEEDS_MORE_TESTING"
    base.loc[base["analysis_id"].eq("D1_COORTES_DEMANDA_FUTURA_MECANICA"), "classification_reason"] = "Janelas completas corrigidas; pré-escola 2030 anulada e frente mantida para novo julgamento."
    base["score"] = pd.NA
    base["automatic_approval"] = False
    base["external_judgment_required"] = True

    rows: list[dict[str, Any]] = []
    for record in base.to_dict(orient="records"):
        analysis_id = str(record["analysis_id"])
        profile = MATRIX_PROFILES.get(analysis_id)
        if profile is None:
            raise ValueError(f"Perfil C1–C12 ausente: {analysis_id}")
        row = dict(record)
        evidence = (
            f"{profile['subject']}: {profile['subject']} tem vínculo explícito com planejamento e monitoramento municipal.",
            f"{profile['subject']}: {profile['mechanism']}",
            f"{profile['subject']}: {profile['lenses']}",
            f"{profile['subject']}: {profile['period']}",
            f"{profile['subject']}: {profile['stability']}",
            f"{profile['subject']}: {profile['integration']}",
            f"{profile['subject']}: {profile['difference']}",
            f"Pergunta delimitada — {profile['question']}",
            f"{profile['subject']}: {profile['communication']}",
            f"{profile['subject']}: {profile['source']}",
            f"{profile['subject']}: {profile['distinct']}",
            f"{profile['subject']}: {profile['beyond']}",
        )
        statuses = profile["statuses"]
        if len(statuses) != 12 or len(evidence) != 12:
            raise ValueError(f"Matriz incompleta: {analysis_id}")
        for index in range(1, 13):
            code = f"C{index}"
            row[f"c{index}_meaning"] = CRITERION_MEANINGS[code]
            row[f"c{index}_status"] = statuses[index - 1]
            row[f"c{index}_evidence"] = evidence[index - 1]
        rows.append(row)
    columns = [
        "analysis_id", "front", "classification", "classification_reason", "primary_limitation",
        "score", "automatic_approval", "external_judgment_required",
    ]
    for index in range(1, 13):
        columns.extend([f"c{index}_meaning", f"c{index}_status", f"c{index}_evidence"])
    return pd.DataFrame(rows)[columns].sort_values(["front", "analysis_id"], kind="mergesort").reset_index(drop=True)


def _dossier(
    trajectory: pd.DataFrame,
    infant: pd.DataFrame,
    teachers: pd.DataFrame,
    conditions: pd.DataFrame,
    regional_integral: pd.DataFrame,
    pressure: pd.DataFrame,
) -> dict[str, Any]:
    municipality_filter = lambda frame: frame[frame["municipality_ibge_code"].eq(NOVA_SANTA_RITA_ID)].copy()
    trajectory_local = municipality_filter(trajectory)
    infant_local = municipality_filter(infant)
    teachers_local = municipality_filter(teachers)
    conditions_local = municipality_filter(conditions)
    pressure_local = municipality_filter(pressure)

    teacher_metrics = {
        "docentes", "turmas", "alunos_por_turma", "estudantes_por_docente",
        "teacher_adequacy_percent",
    }
    teacher_metrics.update(metric for metric in teachers_local["metric"].unique() if str(metric).startswith("ied_"))
    jornada_metrics = {"matriculas_tempo_integral", "percentual_tempo_integral"}
    jornada_metrics.update(metric for metric in teachers_local["metric"].unique() if str(metric).startswith("had_"))

    trajectory_tabs = []
    for stage in ("fundamental", "anos_iniciais", "anos_finais", "medio"):
        tab = trajectory_local[trajectory_local["stage"].eq(stage)]
        trajectory_tabs.append(
            {
                "id": stage,
                "classification": "READY_WITH_PERIOD_AND_LABEL_GUARDRAILS",
                "series": _records(tab),
            }
        )

    condition_visual = conditions_local[conditions_local["visual_row_eligible"]]
    condition_qa = conditions_local[~conditions_local["visual_row_eligible"]]
    groups = [
        {
            "id": "educacao_infantil_observada",
            "classification": "READY_FOR_INTERNAL_VISUAL_PROTOTYPE",
            "period": "2014–2025",
            "series": _records(infant_local),
            "birthsDataGap": {
                "objectId": "D1_NASCIMENTOS_EDUCACAO_INFANTIL",
                "state": "INSUFFICIENT_DATA",
                "municipalBirthsAvailable": False,
                "regionalEndpoints": {"2015": 13004, "2024": 9276},
                "migrationObserved": False,
            },
        },
        {
            "id": "trajetoria_oficial",
            "classification": "READY_WITH_PERIOD_AND_LABEL_GUARDRAILS",
            "period": "2018–2025 ou 2019–2025 conforme indicador",
            "tabs": trajectory_tabs,
            "seriesStoredOnce": True,
        },
        {
            "id": "docentes_e_organizacao_da_oferta",
            "classification": "PARTIAL_COMPONENT_APPROVAL",
            "series": _records(teachers_local[teachers_local["metric"].isin(teacher_metrics)]),
            "irdSeries": _records(conditions_local[conditions_local["metric"].isin(IRD_METRICS)]),
            "hadIedCoverageState": "LOCAL_DESCRIPTIVE_ONLY_WHEN_2_OF_10",
        },
        {
            "id": "jornada_e_tempo_integral",
            "classification": "READY_WITH_REGIONAL_COMPONENT_FORMULA",
            "series": _records(teachers_local[teachers_local["metric"].isin(jornada_metrics)]),
            "regionalSeries": _records(regional_integral),
            "regionalShareIsMunicipalMedian": False,
        },
        {
            "id": "perfil_de_condicoes",
            "classification": "READY_WITH_METRIC_ALLOWLIST_AND_COVERAGE_GATE",
            "visualSeries": _records(condition_visual),
            "qaAvailability": _records(condition_qa),
            "visualMetricAllowlist": sorted(condition_visual["metric"].unique().tolist()),
            "excludedEmptyMetrics": sorted(ZERO_OBSERVATION_VISUAL_EXCLUSIONS),
            "correlationUsedAsInsight": False,
            "syntheticIndexCreated": False,
        },
        {
            "id": "pressao_mecanica_corrigida",
            "classification": "REVIEW_REQUIRED_AFTER_INCOMPLETE_COHORT_WINDOW_CORRECTION",
            "series": _records(pressure_local),
            "mixedLensRatio": True,
            "isDemandForecast": False,
            "isCapacityMeasure": False,
        },
    ]
    compact = [
        {"id": group["id"], "classification": group["classification"], "editorialUse": "future_internal_only"}
        for group in groups
    ]
    return {
        "schemaVersion": "nova-santa-rita-job5ga-v1.1",
        "jobId": "v7-job5gar",
        "municipalityIbgeCode": NOVA_SANTA_RITA_ID,
        "municipalityName": "Nova Santa Rita",
        "networkScope": "total_all_dependencies",
        "administrativeDependencyIsAnalyticDimension": False,
        "administrativeDependencyIsQADimension": True,
        "organizationGroupCount": 6,
        "evidenceGroups": groups,
        "compactSynthesis": compact,
        "completeTechnicalEvidencePreserved": True,
        "trajectoryEvidenceStoredOnce": True,
        "trajectoryUniqueRecordCount": len(trajectory_local),
        "h2State": "NOT_EVALUABLE_DUE_TO_DATA_OR_QA_LIMIT",
        "h2FrozenUnchanged": True,
        "publicNarrative": False,
    }


def _map_markdown(matrix: pd.DataFrame) -> str:
    return "\n".join(
        [
            "# Mapa de seções potenciais — Job 5G-A-R V7",
            "",
            "> Inventário interno corrigido para julgamento externo. Não é narrativa pública, interface ou publicação.",
            "",
            "| Ordem | Grupo interno | Objeto(s) | Estado após correção | Guardrail |",
            "|---:|---|---|---|---|",
            "| 1 | Educação infantil observada | D1_EDUCACAO_INFANTIL_OBSERVADA_V1 | READY_FOR_INTERNAL_VISUAL_PROTOTYPE | Nascimentos ficam em objeto separado e insuficiente; lentes residente e escolar não são cobertura. |",
            "| 2 | Trajetória oficial | D1_TRAJETORIA_OFICIAL_DESCRITIVA_V1_1 | READY_WITH_PERIOD_AND_LABEL_GUARDRAILS | Quatro abas; 2020–2021 com ruptura visual; sem taxa do Vale/RS ou ranking de desempenho. |",
            "| 3 | Docentes e organização da oferta | D1_DOCENTES_TURMAS_JORNADA | PARTIAL_COMPONENT_APPROVAL | HAD/IED 2/10 são LOCAL_DESCRIPTIVE_ONLY; IRD é distribuição de escolas em 2025. |",
            "| 4 | Jornada e tempo integral | D1_TRAJETORIA_TEMPO_INTEGRAL | READY_WITH_REGIONAL_COMPONENT_FORMULA | Percentual regional por soma de componentes; mediana municipal separada. |",
            "| 5 | Perfil de condições | D1_PERFIL_CONDICOES_ESCOLARES_TOTAL_V1 | READY_WITH_METRIC_ALLOWLIST_AND_COVERAGE_GATE | Métricas vazias somente em QA; sem causalidade, correlação-insight ou índice sintético. |",
            "| 6 | Pressão mecânica corrigida | D1_COORTES_DEMANDA_FUTURA_MECANICA | REVIEW_REQUIRED_AFTER_INCOMPLETE_COHORT_WINDOW_CORRECTION | Pré-escola 2030 não avaliável; razão de lentes mistas não é previsão, cobertura, demanda ou capacidade. |",
            "",
            "## Separação obrigatória na educação infantil",
            "",
            "- `D1_EDUCACAO_INFANTIL_OBSERVADA_V1`: evidência observada 2014–2025, pronta para protótipo visual interno.",
            "- `D1_NASCIMENTOS_EDUCACAO_INFANTIL`: nascimentos municipais e migração indisponíveis; estado `INSUFFICIENT_DATA`.",
            "",
            "## Limites de continuidade",
            "",
            "Job 5G-B, Job 5H, Job 6, compilador, interface, publicação, aquisição externa e narrativa pública permanecem fora do escopo.",
            "",
            f"Matriz corrigida: {len(matrix)} análises; C1–C12 usam somente SUPPORTED, PARTIAL, NOT_SUPPORTED ou NOT_EVALUABLE, sem score ou aprovação automática.",
            "",
        ]
    )


def _qa_summary(
    trajectory: pd.DataFrame,
    infant: pd.DataFrame,
    teachers: pd.DataFrame,
    conditions: pd.DataFrame,
    regional_integral: pd.DataFrame,
    pressure: pd.DataFrame,
    dossier: Mapping[str, Any],
    matrix: pd.DataFrame,
) -> dict[str, Any]:
    incomplete = ~pressure["cohort_window_complete"]
    complete_regional = regional_integral["regional_integral_share_eligible"]
    unavailable_regional = ~regional_integral["regional_integral_share_eligible"]
    return {
        "originalArtifactCount": 12,
        "preschool2030NonEvaluableRows": int(
            (
                pressure["stage"].eq("pre_escola")
                & pressure["target_year"].eq(2030)
                & incomplete
            ).sum()
        ),
        "incompleteCohortRowsWithNumericRatio": int(
            pressure.loc[incomplete, "cohort_to_baseline_enrollment_ratio"].notna().sum()
        ),
        "regionalComparatorIneligibleRows": int((~teachers["regional_distribution_eligible"]).sum() + (~conditions["regional_distribution_eligible"]).sum()),
        "hadIedObservedMunicipalityCount": sorted(
            set(
                teachers.loc[
                    teachers["metric"].astype(str).str.startswith(HAD_IED_PREFIXES),
                    "observed_municipality_count",
                ].astype(int)
            )
        ),
        "irdMunicipalityCount": int(
            conditions.loc[conditions["metric"].isin(IRD_METRICS), "municipality_ibge_code"].nunique()
        ),
        "regionalIntegralExactRows": int(complete_regional.sum()),
        "regionalIntegralUnavailableRows": int(unavailable_regional.sum()),
        "trajectory2020And2021RowsFlagged": int(
            trajectory["period_context_flag"].eq("ATYPICAL_SERIES_DISCONTINUITY_REQUIRES_CONTEXT").sum()
        ),
        "trajectoryRegionalRatesComputed": int(trajectory["regional_rate_value"].notna().sum()),
        "infantObservedRows": len(infant),
        "visualAllowlistMetricCount": int(conditions.loc[conditions["visual_metric_allowlisted"], "metric"].nunique()),
        "emptyMetricsExcludedFromVisualAllowlist": sorted(ZERO_OBSERVATION_VISUAL_EXCLUSIONS),
        "matrixAnalysisCount": len(matrix),
        "dossierOrganizationGroupCount": dossier["organizationGroupCount"],
        "dossierTrajectoryUniqueRecordCount": dossier["trajectoryUniqueRecordCount"],
        "h2FrozenUnchanged": dossier["h2FrozenUnchanged"],
    }


def _errata_markdown(originals: Mapping[str, Mapping[str, Any]], qa: Mapping[str, Any]) -> str:
    original_lines = [
        f"| `{name}` | {item['byteSize']} | `{item['sha256']}` |"
        for name, item in sorted(originals.items())
    ]
    return "\n".join(
        [
            "# Errata metodológica — Job 5G-A-R V7",
            "",
            "Documento interno de correção dirigida. Não constitui narrativa pública, interface, publicação ou reabertura de H2.",
            "",
            "## Estado de entrada",
            "",
            "`JOB_5GA_EXECUTION = APPROVED_WITH_REQUIRED_CORRECTIONS`. O objeto H2 permanece `NOT_EVALUABLE_DUE_TO_DATA_OR_QA_LIMIT` e congelado.",
            "",
            "## Correções aplicadas",
            "",
            "1. **Pressão mecânica:** larguras 2/9/3 são obrigatórias. As 11 linhas de pré-escola 2030 têm janela observada 1/2, estado `PARTIAL_COHORT_NOT_YET_OBSERVED_AT_REFERENCE_YEAR` e nenhuma razão numérica. Horizontes foram recalculados somente com janelas completas.",
            "2. **Cobertura de comparadores:** docentes, jornada e condições recebem contagem observada, expectativa 10, fração e gate 10/10. HAD/IED preservam Nova Santa Rita e São Leopoldo como `LOCAL_DESCRIPTIVE_ONLY`, sem mediana, quartil, posição ou percentil do Vale.",
            "3. **IRD:** fotografia 2025 preservada para dez municípios, `counting_unit=school`; as quatro faixas fecham 100% por município e não representam distribuição de docentes.",
            "4. **Tempo integral:** o percentual regional é `sum(matriculas_tempo_integral) / sum(matriculas_totais) * 100`; a mediana dos percentuais municipais fica em campo separado. Anos iniciais e finais permanecem indisponíveis para o agregado ponderado sem denominador exato.",
            "5. **Trajetória:** taxas oficiais foram preservadas. 2020–2021 recebem flag contextual e bloqueio de continuidade linear. A busca local não encontrou nota oficial suficiente; nenhuma causa foi atribuída e nenhuma suavização foi aplicada.",
            "6. **Educação infantil:** `D1_EDUCACAO_INFANTIL_OBSERVADA_V1` fica pronto para protótipo interno; `D1_NASCIMENTOS_EDUCACAO_INFANTIL` permanece `INSUFFICIENT_DATA`.",
            "7. **Condições:** allowlist visual exige observação, definição/unidade, período, lente, cobertura e limite semântico. Água potável, quadra e biblioteca permanecem somente em QA por zero observações.",
            "8. **Matriz:** C1–C12 usam evidência específica e vocabulário fechado; `score` permanece vazio e `automatic_approval=false`.",
            "9. **Nova Santa Rita:** seis grupos internos substituem onze histórias; as 124 linhas de trajetória são armazenadas uma única vez em quatro abas e uma síntese compacta é adicionada.",
            "",
            "## Lentes e limites",
            "",
            "A pressão mecânica declara `cohort_lens=resident_population`, `baseline_enrollment_lens=school_location` e `mixed_lens_ratio=true`. Ela não é taxa de cobertura, previsão de demanda nem medida de capacidade.",
            "",
            "## QA consolidado",
            "",
            f"- Linhas inválidas de pré-escola 2030: {qa['preschool2030NonEvaluableRows']}.",
            f"- Agregados ponderados de tempo integral válidos: {qa['regionalIntegralExactRows']}; indisponíveis por denominador incompatível: {qa['regionalIntegralUnavailableRows']}.",
            f"- Linhas de trajetória 2020–2021 com flag: {qa['trajectory2020And2021RowsFlagged']}.",
            f"- Métricas na allowlist visual: {qa['visualAllowlistMetricCount']}.",
            "",
            "## Baseline byte a byte do Job 5G-A",
            "",
            "| Artefato original | Bytes | SHA-256 |",
            "|---|---:|---|",
            *original_lines,
            "",
            "Os doze arquivos acima são somente leitura e são revalidados antes e depois da materialização.",
            "",
        ]
    )


def _review_package(qa: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schemaVersion": "pacote-revisao-externa-job5gar-v1",
        "jobId": "v7-job5gar",
        "checkpoint": "post_external_judgment_job5ga",
        "inputDecision": "APPROVED_WITH_REQUIRED_CORRECTIONS",
        "finalState": "JOB_5GA_R_READY_FOR_EXTERNAL_JUDGMENT",
        "externalReviewer": "GPT-5.6 Pro",
        "frontClassifications": {
            "A": "READY_WITH_PERIOD_AND_LABEL_GUARDRAILS",
            "B_births": "INSUFFICIENT_DATA",
            "B_observed_infant": "READY_FOR_INTERNAL_VISUAL_PROTOTYPE",
            "C": "PARTIAL_COMPONENT_APPROVAL",
            "D": "READY_WITH_METRIC_ALLOWLIST_AND_COVERAGE_GATE",
            "E": "REVIEW_REQUIRED_AFTER_INCOMPLETE_COHORT_WINDOW_CORRECTION",
        },
        "educationInfantObjects": {
            "D1_EDUCACAO_INFANTIL_OBSERVADA_V1": "READY_FOR_INTERNAL_VISUAL_PROTOTYPE",
            "D1_NASCIMENTOS_EDUCACAO_INFANTIL": "INSUFFICIENT_DATA",
        },
        "h2State": "NOT_EVALUABLE_DUE_TO_DATA_OR_QA_LIMIT",
        "h2FrozenUnchanged": True,
        "job5fReexecuted": False,
        "job5gBStarted": False,
        "job5hStarted": False,
        "job6Started": False,
        "frontendChanged": False,
        "compilerUsed": False,
        "publicDataChanged": False,
        "publicNarrativeWritten": False,
        "networkUsed": False,
        "databaseUsed": False,
        "externalAcquisitionUsed": False,
        "qa": dict(qa),
        "outputs": list(OUTPUT_FILES),
        "stopForExternalJudgment": True,
        "nextAuthorizedAnalyticalJobAfterJudgment": "Job 5G-B",
    }


def _artifact(path: Path, root: Path, rows: int | None = None) -> dict[str, Any]:
    return {
        "path": path.relative_to(root).as_posix(),
        "byteSize": path.stat().st_size,
        "sha256": sha256_file(path),
        "rowCount": rows,
    }


def _manifest(
    staging: Path,
    originals: Mapping[str, Mapping[str, Any]],
    qa: Mapping[str, Any],
    row_counts: Mapping[str, int],
) -> dict[str, Any]:
    artifacts = [
        _artifact(staging / name, staging, row_counts.get(name))
        for name in OUTPUT_FILES
        if name != "MANIFEST_JOB5GAR.json"
    ]
    return {
        "schemaVersion": "manifest-job5gar-v1",
        "jobId": "v7-job5gar",
        "classification": "DATA_LOGIC",
        "domains": ["DATA_CORRECTION", "QA", "DOCUMENTATION"],
        "objective": "Corrigir de forma dirigida o pacote de demografia, trajetória e condições escolares do Job 5G-A.",
        "finalState": "JOB_5GA_R_READY_FOR_EXTERNAL_JUDGMENT",
        "scope": {
            "sourceJob": "v7-job5ga",
            "state": "RS",
            "region": "Vale do Sinos",
            "municipalityCount": 10,
            "municipalityIdentity": "textual_ibge_code_7_digits",
            "networkScope": "total_all_dependencies",
            "administrativeDependencyIsAnalyticDimension": False,
            "administrativeDependencyIsQADimension": True,
            "publicNarrativeAllowed": False,
            "frontendAllowed": False,
            "publicationAllowed": False,
        },
        "formulas": {
            "trajectoryOfficialRates": "preserved_byte_values_from_job5ga_panel",
            "trajectoryClosure": "approval + failure + dropout = 100",
            "regionalIntegralShare": "sum(matriculas_tempo_integral) / sum(matriculas_totais) * 100",
            "municipalIntegralShareMedian": "median(percentual_tempo_integral_municipal)",
            "mechanicalPressure": "mechanical_cohort_size / baseline_enrollments_2025 only_when_cohort_window_complete",
            "regionalTrajectoryRate": "not_computed",
        },
        "formulasPreserved": ["official_trajectory_rates", "complete_window_mechanical_ratio"],
        "formulasCorrected": ["incomplete_cohort_nullification", "horizon_excludes_incomplete_windows", "weighted_regional_integral_share"],
        "originalArtifacts": [
            {"path": name, **dict(item)} for name, item in sorted(originals.items())
        ],
        "qa": dict(qa),
        "generation": {
            "deterministic": True,
            "transactional": True,
            "manifestLast": True,
            "partialPromotionAllowed": False,
            "sourceJobArtifactsChanged": False,
            "publicDataChanged": False,
            "frontendChanged": False,
            "fullBuildUsed": False,
            "compilerUsed": False,
            "networkUsed": False,
            "databaseUsed": False,
            "externalAcquisitionUsed": False,
            "job5fReexecuted": False,
            "job5gBStarted": False,
            "job5hStarted": False,
            "job6Started": False,
            "publicNarrativeWritten": False,
        },
        "artifacts": artifacts,
        "summary": {
            "outputCount": len(OUTPUT_FILES),
            "manifestSelfExcludedFromArtifactHashes": True,
            **{key: int(value) for key, value in row_counts.items()},
        },
        "h2State": "NOT_EVALUABLE_DUE_TO_DATA_OR_QA_LIMIT",
        "h2FrozenUnchanged": True,
        "stopForExternalJudgment": True,
    }


def _validate_unique(frame: pd.DataFrame, columns: Sequence[str], label: str) -> None:
    duplicates = frame.duplicated(list(columns), keep=False)
    if duplicates.any():
        raise ValueError(f"Grão duplicado em {label}: {int(duplicates.sum())} linhas")


def _validate_outputs(root: Path, *, verify_originals: bool = True) -> dict[str, Any]:
    if verify_originals:
        _verify_originals()
    actual = {path.name for path in root.iterdir() if path.is_file()}
    if actual != set(OUTPUT_FILES):
        raise ValueError(f"Conjunto de outputs divergente: {sorted(actual ^ set(OUTPUT_FILES))}")

    trajectory = _read_csv(root / OUTPUT_FILES[2])
    infant = _read_csv(root / OUTPUT_FILES[3])
    teachers = _read_csv(root / OUTPUT_FILES[4])
    conditions = _read_csv(root / OUTPUT_FILES[5])
    regional_integral = _read_csv(root / OUTPUT_FILES[6])
    pressure = _read_csv(root / OUTPUT_FILES[7])
    dossier = _load_json(root / OUTPUT_FILES[8])
    matrix = _read_csv(root / OUTPUT_FILES[9])
    review = _load_json(root / OUTPUT_FILES[11])
    manifest = _load_json(root / OUTPUT_FILES[12])
    contract = _load_json(root / OUTPUT_FILES[1])

    _validate_unique(trajectory, ["municipality_ibge_code", "year", "stage", "metric"], "trajectory")
    _validate_unique(infant, ["municipality_ibge_code", "year", "stage", "metric"], "infant")
    _validate_unique(teachers, ["municipality_ibge_code", "year", "stage", "metric"], "teachers")
    _validate_unique(conditions, ["municipality_ibge_code", "year", "stage", "metric"], "conditions")
    _validate_unique(pressure, ["entity_scope", "municipality_ibge_code", "stage", "target_year"], "pressure")
    _validate_unique(regional_integral, ["year", "stage"], "regional_integral")
    _validate_unique(matrix, ["analysis_id"], "matrix")

    incomplete = ~_truthy(pressure["cohort_window_complete"])
    affected = pressure["stage"].eq("pre_escola") & pressure["target_year"].eq(2030) & incomplete
    if int(affected.sum()) != 11:
        raise ValueError("A correção deve afetar exatamente 11 linhas de pré-escola 2030.")
    forbidden_numeric = [
        "mechanical_cohort_size", "cohort_to_baseline_enrollment_ratio", "recomputed_ratio",
        "position_low_to_high_among_ten", "percentile_low_to_high_among_ten",
        "vale_municipal_median_ratio", "difference_from_vale_municipal_median_ratio",
    ]
    if pressure.loc[incomplete, forbidden_numeric].notna().any().any():
        raise ValueError("Janela incompleta ainda contém razão, coorte parcial ou comparação numérica.")
    for _, group in pressure.groupby(["entity_scope", "municipality_ibge_code", "stage"], dropna=False):
        valid = group[_truthy(group["cohort_window_complete"])]
        expected_min = pd.to_numeric(valid["cohort_to_baseline_enrollment_ratio"], errors="coerce").min()
        expected_max = pd.to_numeric(valid["cohort_to_baseline_enrollment_ratio"], errors="coerce").max()
        if not np.allclose(pd.to_numeric(group["horizon_min_ratio"], errors="coerce"), expected_min, equal_nan=True):
            raise ValueError("horizon_min_ratio não exclui janelas incompletas.")
        if not np.allclose(pd.to_numeric(group["horizon_max_ratio"], errors="coerce"), expected_max, equal_nan=True):
            raise ValueError("horizon_max_ratio não exclui janelas incompletas.")
    if not pressure["cohort_lens"].eq("resident_population").all():
        raise ValueError("Lente da coorte ausente.")
    if not pressure["baseline_enrollment_lens"].eq("school_location").all():
        raise ValueError("Lente da matrícula-base ausente.")
    if not _truthy(pressure["mixed_lens_ratio"]).all():
        raise ValueError("Razão de lentes mistas não declarada.")
    for flag in ("is_coverage_rate", "is_demand_forecast", "is_capacity_measure"):
        if _truthy(pressure[flag]).any():
            raise ValueError(f"Flag proibido verdadeiro: {flag}")

    for label, panel in (("teachers", teachers), ("conditions", conditions)):
        ineligible = ~_truthy(panel["regional_distribution_eligible"])
        comparison_columns = [
            "vale_municipal_median", "vale_quartile_1", "vale_quartile_3",
            "position_low_to_high_among_observed_municipalities",
            "percentile_low_to_high_among_ten", "difference_from_vale_municipal_median",
        ]
        columns = [column for column in comparison_columns if column in panel]
        if panel.loc[ineligible, columns].notna().any().any():
            raise ValueError(f"Comparação regional sem 10/10 em {label}.")
    had_ied = teachers["metric"].astype(str).str.startswith(HAD_IED_PREFIXES)
    if set(pd.to_numeric(teachers.loc[had_ied, "observed_municipality_count"], errors="raise")) != {2}:
        raise ValueError("HAD/IED devem preservar cobertura 2/10.")
    if not teachers.loc[had_ied, "regional_comparison_classification"].eq("LOCAL_DESCRIPTIVE_ONLY").all():
        raise ValueError("HAD/IED sem classificação LOCAL_DESCRIPTIVE_ONLY.")

    ird = conditions[conditions["metric"].isin(IRD_METRICS)]
    if ird["municipality_ibge_code"].nunique() != 10 or set(pd.to_numeric(ird["year"], errors="raise")) != {2025}:
        raise ValueError("IRD não preserva dez municípios em 2025.")
    if not ird["counting_unit"].eq("school").all():
        raise ValueError("IRD deve usar school como unidade de contagem.")
    closure = ird.groupby(["municipality_ibge_code", "year"])["value"].sum()
    if not np.allclose(closure, 100, atol=0.2):
        raise ValueError("As quatro faixas do IRD não fecham aproximadamente 100%.")

    exact = regional_integral[_truthy(regional_integral["regional_integral_share_eligible"])]
    if len(exact) != 36:
        raise ValueError("Tempo integral deve ter 36 agregados ponderados exatos.")
    recomputed = (
        pd.to_numeric(exact["regional_integral_enrollments"], errors="raise")
        / pd.to_numeric(exact["regional_total_enrollments"], errors="raise")
        * 100
    )
    if not np.allclose(recomputed, pd.to_numeric(exact["regional_integral_share"], errors="raise"), atol=1e-12):
        raise ValueError("Percentual regional de tempo integral não fecha por soma de componentes.")
    unavailable = regional_integral[~_truthy(regional_integral["regional_integral_share_eligible"])]
    if len(unavailable) != 24 or unavailable["regional_integral_share"].notna().any():
        raise ValueError("Anos iniciais/finais não preservam indisponibilidade.")

    family = trajectory[trajectory["metric"].isin(["approval_rate_percent", "failure_rate_percent", "dropout_rate_percent"])]
    closure = family.pivot_table(
        index=["municipality_ibge_code", "year", "stage"], columns="metric", values="value", aggfunc="first"
    )
    if not np.allclose(closure.sum(axis=1), 100, atol=1e-9):
        raise ValueError("Aprovação + reprovação + abandono não fecha 100%.")
    atypical = trajectory["year"].isin([2020, 2021])
    if not trajectory.loc[atypical, "period_context_flag"].eq("ATYPICAL_SERIES_DISCONTINUITY_REQUIRES_CONTEXT").all():
        raise ValueError("2020–2021 sem flag contextual.")
    if _truthy(trajectory.loc[atypical, "public_line_continuity_allowed"]).any():
        raise ValueError("Continuidade pública indevida em 2020–2021.")
    if trajectory["regional_rate_value"].notna().any():
        raise ValueError("Taxa regional de trajetória foi calculada.")
    if "vale_median" in trajectory or "rs_median" in trajectory:
        raise ValueError("Labels semânticos antigos ainda presentes.")

    if set(infant["metric"]) != {"resident_population", "school_enrollments", "school_classes", "schools"}:
        raise ValueError("Educação infantil observada não foi separada de nascimentos.")
    if len(infant) != 600 or not infant["value_status"].eq("observed").all():
        raise ValueError("Painel observado de educação infantil divergente.")
    for metric in ZERO_OBSERVATION_VISUAL_EXCLUSIONS:
        rows = conditions[conditions["metric"].eq(metric)]
        if _truthy(rows["visual_metric_allowlisted"]).any():
            raise ValueError(f"Métrica vazia entrou na allowlist: {metric}")
    if _truthy(conditions["correlation_used_as_insight"]).any():
        raise ValueError("Correlação foi usada como insight.")

    for index in range(1, 13):
        if set(matrix[f"c{index}_status"]) - CRITERION_STATUSES:
            raise ValueError(f"Vocabulário inválido em C{index}.")
        if matrix[f"c{index}_evidence"].nunique() != len(matrix):
            raise ValueError(f"Evidência repetida mecanicamente em C{index}.")
        if not matrix[f"c{index}_meaning"].eq(CRITERION_MEANINGS[f"C{index}"]).all():
            raise ValueError(f"Significado canônico divergente em C{index}.")
    if matrix["score"].notna().any() or _truthy(matrix["automatic_approval"]).any():
        raise ValueError("Score ou aprovação automática indevidos.")
    for analysis_id in ("D1_TRAJETORIA_ESFORCO_DOCENTE", "D1_TRAJETORIA_HORAS_AULA"):
        row = matrix[matrix["analysis_id"].eq(analysis_id)].iloc[0]
        if row["c7_status"] == "SUPPORTED" or row["c9_status"] == "SUPPORTED":
            raise ValueError("C7/C9 não podem ser suportados com cobertura 2/10.")

    if dossier["organizationGroupCount"] != 6 or dossier["trajectoryUniqueRecordCount"] != 124:
        raise ValueError("Dossiê de Nova Santa Rita não foi reorganizado corretamente.")
    trajectory_group = next(group for group in dossier["evidenceGroups"] if group["id"] == "trajetoria_oficial")
    trajectory_records = [record for tab in trajectory_group["tabs"] for record in tab["series"]]
    grains = {
        (record["municipality_ibge_code"], record["year"], record["stage"], record["metric"])
        for record in trajectory_records
    }
    if len(trajectory_records) != 124 or len(grains) != 124:
        raise ValueError("Trajetória de Nova Santa Rita foi duplicada.")
    if contract["h2FrozenState"] != "NOT_EVALUABLE_DUE_TO_DATA_OR_QA_LIMIT":
        raise ValueError("H2 foi alterada no contrato.")
    if not review["h2FrozenUnchanged"] or not manifest["h2FrozenUnchanged"]:
        raise ValueError("H2 não está congelada no pacote.")

    allowed_states = {"observed", "null", "unavailable", "suppressed", "not_applicable"}
    for label, panel in (("trajectory", trajectory), ("infant", infant), ("teachers", teachers), ("conditions", conditions)):
        if set(panel["value_status"].dropna()) - allowed_states:
            raise ValueError(f"Estado de valor inválido em {label}.")
        zero_rows = panel[pd.to_numeric(panel["value"], errors="coerce").eq(0)]
        if not zero_rows.empty and not zero_rows["value_status"].eq("observed").all():
            raise ValueError(f"Zero observado reclassificado em {label}.")

    declared = {item["path"]: item for item in manifest["artifacts"]}
    expected_declared = set(OUTPUT_FILES) - {"MANIFEST_JOB5GAR.json"}
    if set(declared) != expected_declared:
        raise ValueError("Manifesto não declara exatamente os doze artefatos anteriores.")
    for name, item in declared.items():
        path = root / name
        if path.stat().st_size != item["byteSize"] or sha256_file(path) != item["sha256"]:
            raise ValueError(f"Integridade de output divergente: {name}")

    return {
        "finalState": "JOB_5GA_R_READY_FOR_EXTERNAL_JUDGMENT",
        "promotion": "validated_existing",
        "outputCount": len(OUTPUT_FILES),
        "manifestSha256": sha256_file(root / "MANIFEST_JOB5GAR.json"),
        "preschool2030NonEvaluableRows": int(affected.sum()),
        "regionalIntegralExactRows": len(exact),
        "matrixAnalysisCount": len(matrix),
        "originalArtifactCount": len(ORIGINAL_FILES),
    }


def _promote(staging: Path, target: Path) -> str:
    target.parent.mkdir(parents=True, exist_ok=True)
    backup: Path | None = None
    if target.exists():
        backup = target.parent / f".{target.name}.backup-{os.getpid()}"
        if backup.exists():
            raise FileExistsError(backup)
        target.rename(backup)
    try:
        staging.rename(target)
    except Exception:
        if backup is not None and backup.exists() and not target.exists():
            backup.rename(target)
        raise
    if backup is not None:
        shutil.rmtree(backup)
        return "replaced_transactionally"
    return "created_transactionally"


def materialize(output_root: Path = DEFAULT_OUTPUT_ROOT) -> dict[str, Any]:
    output_root = output_root.resolve()
    public_root = (REPO_ROOT / "public" / "data").resolve()
    if output_root == public_root or public_root in output_root.parents:
        raise ValueError("Job 5G-A-R não pode escrever em public/data.")
    if (REPO_ROOT / "src").resolve() in output_root.parents:
        raise ValueError("Job 5G-A-R não pode escrever no frontend.")

    originals_before = _verify_originals()
    trajectory = _trajectory_panel()
    infant = _infant_observed_panel()
    teachers = _teachers_panel()
    conditions = _conditions_panel()
    regional_integral = _regional_integral_panel(teachers)
    pressure = _pressure_panel()
    matrix = _opportunity_matrix()
    dossier = _dossier(trajectory, infant, teachers, conditions, regional_integral, pressure)
    qa = _qa_summary(trajectory, infant, teachers, conditions, regional_integral, pressure, dossier, matrix)

    output_root.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output_root.name}-staging-", dir=output_root.parent))
    try:
        _write_json(staging / OUTPUT_FILES[1], _trajectory_contract())
        _write_csv_gzip(staging / OUTPUT_FILES[2], trajectory)
        _write_csv_gzip(staging / OUTPUT_FILES[3], infant)
        _write_csv_gzip(staging / OUTPUT_FILES[4], teachers)
        _write_csv_gzip(staging / OUTPUT_FILES[5], conditions)
        _write_csv_gzip(staging / OUTPUT_FILES[6], regional_integral)
        _write_csv_gzip(staging / OUTPUT_FILES[7], pressure)
        _write_json(staging / OUTPUT_FILES[8], dossier)
        _write_csv_gzip(staging / OUTPUT_FILES[9], matrix)
        (staging / OUTPUT_FILES[10]).write_text(_map_markdown(matrix), encoding="utf-8", newline="\n")
        _write_json(staging / OUTPUT_FILES[11], _review_package(qa))
        (staging / OUTPUT_FILES[0]).write_text(_errata_markdown(originals_before, qa), encoding="utf-8", newline="\n")

        row_counts = {
            OUTPUT_FILES[2]: len(trajectory),
            OUTPUT_FILES[3]: len(infant),
            OUTPUT_FILES[4]: len(teachers),
            OUTPUT_FILES[5]: len(conditions),
            OUTPUT_FILES[6]: len(regional_integral),
            OUTPUT_FILES[7]: len(pressure),
            OUTPUT_FILES[9]: len(matrix),
        }
        _write_json(staging / OUTPUT_FILES[12], _manifest(staging, originals_before, qa, row_counts))
        _validate_outputs(staging)
        originals_after_generation = _verify_originals()
        if originals_before != originals_after_generation:
            raise ValueError("Artefatos originais foram alterados durante a geração.")
        promotion = _promote(staging, output_root)
        report = _validate_outputs(output_root)
        originals_after_promotion = _verify_originals()
        if originals_before != originals_after_promotion:
            raise ValueError("Artefatos originais foram alterados durante a promoção.")
        report["promotion"] = promotion
        return report
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def validate_existing_output(output_root: Path = DEFAULT_OUTPUT_ROOT) -> dict[str, Any]:
    return _validate_outputs(output_root.resolve())
