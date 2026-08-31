"""Execute the frozen Vocações × PNE relationship atlas without source refresh.

This module is deliberately downstream from the immutable preregistration.  It
reads only the frozen AA1/Job5i artifacts, preserves availability and territorial
lenses, estimates every preregistered hypothesis exactly once, and writes only to
the task-owned ``.tmp`` result root.  Statistical association never becomes a
causal claim.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import csv
import hashlib
import itertools
import json
import math
import os
from pathlib import Path
import re
import shutil
import tempfile
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
import pandas as pd

from src.vocacoes_pne_advanced_panel import (
    blocked_external_io_guard,
    directory_content_digest,
)
from src.vocacoes_pne_relationship_atlas import (
    DEFAULT_OUTPUT_ROOT as PREREGISTRATION_ROOT,
    validate_existing_output as validate_preregistration,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = Path(__file__).resolve()
EXECUTION_CONTRACT_PATH = (
    REPO_ROOT
    / "data_pipeline/contracts/vocacoes-pne-relationship-atlas-execution-v1.json"
)
AA1_PANEL_PATH = (
    REPO_ROOT
    / ".tmp/vocacoes-pne/advanced-analytics-v1/aa1/PAINEL_ANALITICO_ESTADUAL_AA1.csv.gz"
)
JOB5I_SERIES_PATH = (
    REPO_ROOT
    / "src/features/vocacoes-pne-internal/generated/vocacoesPneJob5iSeries.json"
)
REGION_REGISTRY_PATH = REPO_ROOT / "config/regions/rs.json"
DEFAULT_RESULTS_ROOT = REPO_ROOT / ".tmp/vocacoes-pne/relationship-atlas-v1/results"
PUBLIC_DATA_ROOT = REPO_ROOT / "public/data"

EXPECTED_PARENT_DIGEST = (
    "6f0994b2cc3b563e0709cc8cd04f4d14382ef9ec2ddc089feeae88f9bf2e8a81"
)
EXPECTED_EXECUTION_CONTRACT_SHA256 = (
    "3243b529f2da96e8af061c727a4d25861fbfdb9cc10360482cb3aea10ccaa7b0"
)
GENERATED_AT = "2026-08-31T00:00:00-03:00"
IBGE_RE = re.compile(r"^[0-9]{7}$")
NUMERIC_AVAILABILITY = {"observed", "observed_zero"}
LANE_COUNTS = {
    "demography_network": 45,
    "economy_work": 31,
    "social_access": 22,
}
NOVA_SANTA_RITA_IBGE_CODE = "4313375"
VALE_REGION_SLUG = "vale-do-sinos"
RESULT_FILES = (
    "RESULTS.json",
    "RESULTS.csv",
    "ROBUSTNESS.json",
    "DATA_QUALITY.json",
    "REPORT.md",
    "MANIFEST.json",
)
COMBINED_FILES = (
    "ALL_RESULTS.json",
    "ALL_RESULTS.csv",
    "PROMOTION_LEDGER.json",
    "NEGATIVE_LEDGER.json",
    "QA_SUMMARY.json",
    "MANIFEST.json",
)


class RelationshipExecutionError(RuntimeError):
    """Raised whenever frozen inputs, methods, or outputs diverge."""


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_ready(item) for item in value]
    if isinstance(value, np.ndarray):
        return json_ready(value.tolist())
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        number = float(value)
        return number if math.isfinite(number) else None
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if value is pd.NA or (not isinstance(value, (str, bytes)) and pd.isna(value)):
        return None
    return value


def serialized_json(payload: Any) -> str:
    return (
        json.dumps(
            json_ready(payload),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n"
    )


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    except Exception:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def write_json(path: Path, payload: Any) -> None:
    atomic_write_text(path, serialized_json(payload))


def write_csv(path: Path, records: Sequence[Mapping[str, Any]]) -> None:
    if not records:
        raise RelationshipExecutionError(f"CSV vazio recusado: {path}")
    fieldnames: list[str] = []
    for record in records:
        for key in record:
            if key not in fieldnames:
                fieldnames.append(key)
    output: list[str] = []
    from io import StringIO

    buffer = StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    for record in records:
        row: dict[str, Any] = {}
        for key in fieldnames:
            value = json_ready(record.get(key))
            row[key] = (
                json.dumps(value, ensure_ascii=False, sort_keys=True)
                if isinstance(value, (list, dict))
                else "null"
                if value is None
                else value
            )
        writer.writerow(row)
    output.append(buffer.getvalue())
    atomic_write_text(path, "".join(output))


def year_from_period(value: Any) -> int | None:
    years = re.findall(r"(?:19|20)\d{2}", str(value))
    return int(years[-1]) if years else None


def selector_matches_frame(
    frame: pd.DataFrame,
    selector: Mapping[str, Any],
    *,
    source: str,
) -> pd.Series:
    if source == "AA1":
        mappings = (
            ("metricId", "metric_id"),
            ("stage", "stage_or_population_group"),
            ("dimension", "dimension_id"),
            ("coverageScope", "coverage_scope"),
            ("territorialLens", "territorial_lens"),
            ("networkScope", "network_scope"),
        )
    else:
        mappings = (
            ("metricId", "metricId"),
            ("ageGroup", "ageGroup"),
            ("coverageScope", "coverageScope"),
            ("territorialLens", "territorialLens"),
            ("networkScope", "networkScope"),
        )
    mask = pd.Series(True, index=frame.index)
    for selector_key, column in mappings:
        expected = selector.get(selector_key)
        if expected is None or expected == "*":
            continue
        if column not in frame.columns:
            mask &= False
            continue
        if isinstance(expected, list):
            mask &= frame[column].isin([str(item) for item in expected])
        else:
            mask &= frame[column].eq(str(expected))
    return mask


def load_frozen_sources() -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    aa1_columns = [
        "municipality_ibge_code",
        "municipality_name",
        "year_or_reference_period",
        "stage_or_population_group",
        "metric_id",
        "dimension_id",
        "raw_value",
        "unit",
        "availability_state",
        "territorial_lens",
        "network_scope",
        "coverage_scope",
        "source_ref",
    ]
    aa1 = pd.read_csv(
        AA1_PANEL_PATH,
        compression="gzip",
        dtype=str,
        keep_default_na=False,
        usecols=aa1_columns,
    )
    aa1["entityId"] = aa1["municipality_ibge_code"].astype(str)
    aa1["year"] = aa1["year_or_reference_period"].map(year_from_period)
    aa1["numericValue"] = pd.to_numeric(aa1["raw_value"], errors="coerce")
    aa1.loc[
        ~aa1["availability_state"].isin(NUMERIC_AVAILABILITY), "numericValue"
    ] = np.nan
    if not aa1["entityId"].str.fullmatch(IBGE_RE).all():
        raise RelationshipExecutionError("AA1 contém identidade municipal inválida")

    payload = read_json(JOB5I_SERIES_PATH)
    job_rows: list[dict[str, Any]] = []
    for series in payload["series"]:
        entity_id = str(series["entityId"])
        if not IBGE_RE.fullmatch(entity_id):
            continue
        for point in series["points"]:
            state = point["availabilityState"]
            job_rows.append(
                {
                    "entityId": entity_id,
                    "metricId": str(series["metricId"]),
                    "ageGroup": str(series.get("ageGroup", "")),
                    "coverageScope": str(series.get("coverageScope", "")),
                    "territorialLens": str(series.get("territorialLens", "")),
                    "networkScope": str(series.get("networkScope", "")),
                    "year": int(point["year"]),
                    "value": (
                        float(point["value"])
                        if state in NUMERIC_AVAILABILITY
                        and point.get("value") is not None
                        else np.nan
                    ),
                    "availabilityState": state,
                    "sourceRef": str(point.get("sourceRef", "")),
                }
            )
    job5i = pd.DataFrame(job_rows)
    quality = {
        "aa1Rows": int(len(aa1)),
        "aa1Municipalities": int(aa1["entityId"].nunique()),
        "aa1Availability": {
            key: int(value)
            for key, value in aa1["availability_state"].value_counts().items()
        },
        "job5iRows": int(len(job5i)),
        "job5iMunicipalities": int(job5i["entityId"].nunique()),
        "job5iAvailability": {
            key: int(value)
            for key, value in job5i["availabilityState"].value_counts().items()
        },
    }
    return aa1, job5i, quality


def component_frame(
    selector: Mapping[str, Any],
    aa1: pd.DataFrame,
    job5i: pd.DataFrame,
) -> pd.DataFrame:
    source = selector["source"]
    if source == "AA1":
        selected = aa1[selector_matches_frame(aa1, selector, source=source)].copy()
        if selected.empty:
            return pd.DataFrame(columns=["entityId", "year", "value"])
        selected = selected[selected["year"].notna()].copy()
        selected["year"] = selected["year"].astype(int)
        grouped = (
            selected.groupby(["entityId", "year"], as_index=False, sort=True)[
                "numericValue"
            ]
            .sum(min_count=1)
            .rename(columns={"numericValue": "value"})
        )
        return grouped
    if source == "JOB5I":
        selected = job5i[
            selector_matches_frame(job5i, selector, source=source)
        ].copy()
        if selected.empty:
            return pd.DataFrame(columns=["entityId", "year", "value"])
        return (
            selected.groupby(["entityId", "year"], as_index=False, sort=True)[
                "value"
            ]
            .sum(min_count=1)
        )
    raise RelationshipExecutionError(f"Fonte de seletor desconhecida: {source}")


def merge_components(frames: Sequence[pd.DataFrame]) -> pd.DataFrame:
    merged: pd.DataFrame | None = None
    for index, frame in enumerate(frames):
        piece = frame.rename(columns={"value": f"component{index}"})
        merged = (
            piece
            if merged is None
            else merged.merge(
                piece, on=["entityId", "year"], how="outer", validate="one_to_one"
            )
        )
    if merged is None:
        return pd.DataFrame(columns=["entityId", "year"])
    return merged


def industry_share_change(
    selector: Mapping[str, Any], aa1: pd.DataFrame
) -> pd.DataFrame:
    selected = aa1[selector_matches_frame(aa1, selector, source="AA1")].copy()
    selected = selected[selected["year"].isin([2019, 2025])].copy()
    selected["division"] = pd.to_numeric(selected["dimension_id"], errors="coerce")
    selected["industryValue"] = selected["numericValue"].where(
        selected["division"].between(5, 33), 0.0
    )
    grouped = selected.groupby(["entityId", "year"], as_index=False).agg(
        total=("numericValue", lambda values: values.sum(min_count=1)),
        industry=("industryValue", lambda values: values.sum(min_count=1)),
    )
    grouped["share"] = np.where(
        grouped["total"] > 0,
        100.0 * grouped["industry"] / grouped["total"],
        np.nan,
    )
    wide = grouped.pivot(index="entityId", columns="year", values="share")
    if 2019 not in wide or 2025 not in wide:
        return pd.DataFrame(columns=["entityId", "year", "value"])
    result = (wide[2025] - wide[2019]).rename("value").reset_index()
    result["year"] = 2025
    return result[["entityId", "year", "value"]]


def materialize_variables(
    variable_contracts: Sequence[Mapping[str, Any]],
    aa1: pd.DataFrame,
    job5i: pd.DataFrame,
) -> tuple[dict[str, pd.DataFrame], dict[str, Any]]:
    frames: dict[str, pd.DataFrame] = {}
    audit: dict[str, Any] = {}
    for variable in variable_contracts:
        variable_id = variable["variableId"]
        selector = variable.get("selector")
        components = variable.get("components", [])
        formula = variable["formula"]
        denominator_zero_count = 0
        if selector:
            result = component_frame(selector, aa1, job5i)
        elif variable_id == "INDUSTRY_SHARE_CHANGE":
            result = industry_share_change(components[0], aa1)
        else:
            component_frames = [
                component_frame(component, aa1, job5i) for component in components
            ]
            merged = merge_components(component_frames)
            component_columns = [
                column for column in merged.columns if column.startswith("component")
            ]
            if not component_columns:
                result = pd.DataFrame(columns=["entityId", "year", "value"])
            elif " / " in formula and len(component_columns) == 2:
                denominator = merged["component1"]
                denominator_zero_count = int(denominator.eq(0).sum())
                factor = 100.0 if formula.strip().startswith("100 *") else 1.0
                merged["value"] = np.where(
                    denominator.ne(0)
                    & denominator.notna()
                    & merged["component0"].notna(),
                    factor * merged["component0"] / denominator,
                    np.nan,
                )
                result = merged[["entityId", "year", "value"]]
            else:
                merged["value"] = merged[component_columns].sum(
                    axis=1, min_count=len(component_columns)
                )
                result = merged[["entityId", "year", "value"]]
        result = result.copy()
        if result.duplicated(["entityId", "year"]).any():
            raise RelationshipExecutionError(
                f"Variável {variable_id} duplicou município-ano"
            )
        result["value"] = pd.to_numeric(result["value"], errors="coerce")
        result = result.sort_values(["entityId", "year"]).reset_index(drop=True)
        frames[variable_id] = result
        audit[variable_id] = {
            "rowCount": int(len(result)),
            "availableCount": int(result["value"].notna().sum()),
            "municipalityCount": int(result.loc[result["value"].notna(), "entityId"].nunique()),
            "periods": sorted(
                int(year)
                for year in result.loc[result["value"].notna(), "year"].unique()
            ),
            "denominatorZeroCount": denominator_zero_count,
            "territorialLens": variable["territorialLens"],
            "unit": variable["unit"],
            "formula": formula,
        }
    return frames, audit


def load_region_map() -> dict[str, str]:
    payload = read_json(REGION_REGISTRY_PATH)
    mapping: dict[str, str] = {}
    for region in payload["regions"]:
        for code in region["municipalityIbgeCodes"]:
            if code in mapping:
                raise RelationshipExecutionError(f"Município repetido em regiões: {code}")
            mapping[code] = region["slug"]
    if len(mapping) != 497 or not all(IBGE_RE.fullmatch(code) for code in mapping):
        raise RelationshipExecutionError("Mapa regional não cobre os 497 códigos canônicos")
    return mapping


def stable_seed(identifier: str, base: int = 4_313_375) -> int:
    """Return a deterministic seed without relying on Python's randomized hash."""

    suffix = int(hashlib.sha256(identifier.encode("utf-8")).hexdigest()[:8], 16)
    return (base + suffix) % (2**32 - 1)


def normal_p_two_sided(statistic: float) -> float:
    return math.erfc(abs(float(statistic)) / math.sqrt(2.0))


T_CRITICAL_95 = {
    1: 12.706,
    2: 4.303,
    3: 3.182,
    4: 2.776,
    5: 2.571,
    6: 2.447,
    7: 2.365,
    8: 2.306,
    9: 2.262,
    10: 2.228,
    11: 2.201,
    12: 2.179,
    13: 2.160,
    14: 2.145,
    15: 2.131,
    16: 2.120,
    17: 2.110,
    18: 2.101,
    19: 2.093,
    20: 2.086,
    21: 2.080,
    22: 2.074,
    23: 2.069,
    24: 2.064,
    25: 2.060,
    26: 2.056,
    27: 2.052,
    28: 2.048,
    29: 2.045,
    30: 2.042,
}


def t_critical_95(degrees_of_freedom: int) -> float:
    if degrees_of_freedom in T_CRITICAL_95:
        return T_CRITICAL_95[degrees_of_freedom]
    if degrees_of_freedom <= 40:
        return 2.021
    if degrees_of_freedom <= 60:
        return 2.000
    if degrees_of_freedom <= 120:
        return 1.980
    return 1.959963984540054


def bh_adjust(p_values: Sequence[float]) -> list[float]:
    values = np.asarray(p_values, dtype=float)
    if not np.isfinite(values).all() or np.any((values < 0) | (values > 1)):
        raise RelationshipExecutionError("BH recebeu p-valor fora de [0,1]")
    order = np.argsort(values, kind="mergesort")
    ranked = values[order]
    count = len(ranked)
    adjusted_sorted = ranked * count / np.arange(1, count + 1, dtype=float)
    adjusted_sorted = np.minimum.accumulate(adjusted_sorted[::-1])[::-1]
    adjusted_sorted = np.minimum(adjusted_sorted, 1.0)
    adjusted = np.empty(count, dtype=float)
    adjusted[order] = adjusted_sorted
    return [float(value) for value in adjusted]


def alternating_two_way_demean(
    values: np.ndarray, entities: np.ndarray, periods: np.ndarray
) -> tuple[np.ndarray, int, float]:
    residual = np.asarray(values, dtype=float).copy()
    entity_codes, entity_levels = pd.factorize(entities, sort=True)
    period_codes, period_levels = pd.factorize(periods, sort=True)
    convergence = math.inf
    for iteration in range(1, 1001):
        previous = residual.copy()
        for codes, level_count in (
            (entity_codes, len(entity_levels)),
            (period_codes, len(period_levels)),
        ):
            counts = np.bincount(codes, minlength=level_count).astype(float)
            sums = np.zeros((level_count, residual.shape[1]), dtype=float)
            np.add.at(sums, codes, residual)
            residual -= (sums / counts[:, None])[codes]
        convergence = float(np.max(np.abs(residual - previous)))
        if convergence < 1e-12:
            return residual, iteration, convergence
    raise RelationshipExecutionError(
        f"Resíduo TWFE não convergiu; mudança máxima={convergence}"
    )


def cluster_covariance(
    design: np.ndarray,
    residuals: np.ndarray,
    clusters: np.ndarray,
    *,
    effective_parameter_count: int | None = None,
) -> np.ndarray:
    observation_count, parameter_count = design.shape
    unique_clusters = np.unique(clusters)
    cluster_count = len(unique_clusters)
    degrees_parameter_count = effective_parameter_count or parameter_count
    if cluster_count < 3 or observation_count <= degrees_parameter_count:
        raise RelationshipExecutionError("Inferência clusterizada sem graus de liberdade")
    bread = np.linalg.pinv(design.T @ design, hermitian=True)
    meat = np.zeros((parameter_count, parameter_count), dtype=float)
    for cluster in unique_clusters:
        mask = clusters == cluster
        score = design[mask].T @ residuals[mask]
        meat += np.outer(score, score)
    correction = (cluster_count / (cluster_count - 1.0)) * (
        (observation_count - 1.0)
        / (observation_count - degrees_parameter_count)
    )
    return correction * (bread @ meat @ bread)


def exact_rademacher_p_value(
    design: np.ndarray,
    outcome: np.ndarray,
    clusters: np.ndarray,
    target_index: int,
    observed_estimate: float,
) -> tuple[float, int, float]:
    unique_clusters = np.unique(clusters)
    cluster_count = len(unique_clusters)
    if cluster_count > 12:
        raise RelationshipExecutionError(
            "Enumeração exata Rademacher limitada a doze clusters"
        )
    restricted_design = np.delete(design, target_index, axis=1)
    restricted_coefficient = np.linalg.pinv(restricted_design) @ outcome
    restricted_fit = restricted_design @ restricted_coefficient
    restricted_residual = outcome - restricted_fit
    sign_matrix = np.asarray(
        list(itertools.product((-1.0, 1.0), repeat=cluster_count)), dtype=float
    )
    cluster_positions = {value: index for index, value in enumerate(unique_clusters)}
    observation_positions = np.asarray(
        [cluster_positions[value] for value in clusters], dtype=int
    )
    bootstrap_outcomes = restricted_fit[:, None] + restricted_residual[:, None] * (
        sign_matrix[:, observation_positions].T
    )
    bootstrap_coefficients = np.linalg.pinv(design) @ bootstrap_outcomes
    distribution = bootstrap_coefficients[target_index]
    draw_count = len(sign_matrix)
    attainable_floor = 1.0 / draw_count
    extreme_count = int(
        np.sum(np.abs(distribution) >= abs(observed_estimate) - 1e-12)
    )
    return max(extreme_count / draw_count, attainable_floor), draw_count, attainable_floor


def fit_twfe(
    frame: pd.DataFrame,
    *,
    wild_cluster: bool,
) -> dict[str, Any]:
    work = frame[["entityId", "year", "outcome", "exposure", *[
        column for column in frame.columns if column.startswith("control")
    ]]].replace([np.inf, -np.inf], np.nan).dropna().copy()
    control_columns = [
        column for column in work.columns if column.startswith("control")
    ]
    matrix, iterations, convergence = alternating_two_way_demean(
        work[["outcome", "exposure", *control_columns]].to_numpy(dtype=float),
        work["entityId"].to_numpy(),
        work["year"].to_numpy(),
    )
    outcome = matrix[:, 0]
    design = matrix[:, 1:]
    if design.shape[1] == 0 or np.linalg.matrix_rank(design) < design.shape[1]:
        raise RelationshipExecutionError("Modelo TWFE sem variação identificável")
    coefficients = np.linalg.lstsq(design, outcome, rcond=None)[0]
    residuals = outcome - design @ coefficients
    clusters = work["entityId"].astype(str).to_numpy()
    cluster_count = int(work["entityId"].nunique())
    period_count = int(work["year"].nunique())
    covariance = cluster_covariance(
        design,
        residuals,
        clusters,
        effective_parameter_count=(
            design.shape[1] + cluster_count + period_count - 1
        ),
    )
    standard_error = float(math.sqrt(max(float(covariance[0, 0]), 0.0)))
    if not math.isfinite(standard_error) or standard_error <= 0:
        raise RelationshipExecutionError("Erro-padrão clusterizado inválido")
    estimate = float(coefficients[0])
    critical = t_critical_95(cluster_count - 1) if wild_cluster else 1.959963984540054
    if wild_cluster:
        p_value, draw_count, attainable_floor = exact_rademacher_p_value(
            design, outcome, clusters, 0, estimate
        )
        inference = "exact_rademacher_wild_cluster"
    else:
        p_value = normal_p_two_sided(estimate / standard_error)
        draw_count = None
        attainable_floor = None
        inference = "municipality_cluster_cr1_normal_reference"
    leverage = np.einsum(
        "ij,jk,ik->i", design, np.linalg.pinv(design.T @ design), design
    )
    outcome_ss = float(np.dot(outcome, outcome))
    return {
        "estimate": estimate,
        "standardError": standard_error,
        "intervalLow": estimate - critical * standard_error,
        "intervalHigh": estimate + critical * standard_error,
        "pValue": float(p_value),
        "nObservations": int(len(work)),
        "nMunicipalities": cluster_count,
        "nPeriods": int(work["year"].nunique()),
        "periods": sorted(int(value) for value in work["year"].unique()),
        "inference": inference,
        "wildClusterDrawCount": draw_count,
        "attainablePValueFloor": attainable_floor,
        "withinR2": (
            None
            if outcome_ss <= 0
            else 1.0 - float(np.dot(residuals, residuals)) / outcome_ss
        ),
        "maxLeverage": float(np.max(leverage)),
        "maxAbsoluteStandardizedResidual": float(
            np.max(np.abs(residuals)) / max(float(np.std(residuals, ddof=1)), 1e-12)
        ),
        "residualizationIterations": iterations,
        "residualizationConvergence": convergence,
    }


def fit_ols_hc3(
    frame: pd.DataFrame,
    *,
    include_period_effects: bool,
) -> dict[str, Any]:
    control_columns = [
        column for column in frame.columns if column.startswith("control")
    ]
    required = ["outcome", "exposure", *control_columns]
    work = frame[["entityId", "year", *required]].replace(
        [np.inf, -np.inf], np.nan
    ).dropna().copy()
    columns: list[np.ndarray] = [np.ones(len(work)), work["exposure"].to_numpy(float)]
    names = ["intercept", "exposure"]
    for control in control_columns:
        columns.append(work[control].to_numpy(float))
        names.append(control)
    if include_period_effects:
        periods = sorted(int(value) for value in work["year"].unique())
        for period in periods[1:]:
            columns.append((work["year"].to_numpy(int) == period).astype(float))
            names.append(f"period_{period}")
    design = np.column_stack(columns)
    if np.linalg.matrix_rank(design) < design.shape[1] or len(work) <= design.shape[1]:
        raise RelationshipExecutionError("Modelo OLS-HC3 sem graus de liberdade ou posto")
    outcome = work["outcome"].to_numpy(float)
    coefficients = np.linalg.lstsq(design, outcome, rcond=None)[0]
    residuals = outcome - design @ coefficients
    bread = np.linalg.pinv(design.T @ design, hermitian=True)
    leverage = np.einsum("ij,jk,ik->i", design, bread, design)
    adjusted = residuals / np.maximum(1.0 - leverage, 1e-8)
    meat = design.T @ ((adjusted**2)[:, None] * design)
    covariance = bread @ meat @ bread
    standard_error = float(math.sqrt(max(float(covariance[1, 1]), 0.0)))
    if not math.isfinite(standard_error) or standard_error <= 0:
        raise RelationshipExecutionError("Erro-padrão HC3 inválido")
    estimate = float(coefficients[1])
    p_value = normal_p_two_sided(estimate / standard_error)
    return {
        "estimate": estimate,
        "standardError": standard_error,
        "intervalLow": estimate - 1.959963984540054 * standard_error,
        "intervalHigh": estimate + 1.959963984540054 * standard_error,
        "pValue": p_value,
        "nObservations": int(len(work)),
        "nMunicipalities": int(work["entityId"].nunique()),
        "nPeriods": int(work["year"].nunique()),
        "periods": sorted(int(value) for value in work["year"].unique()),
        "inference": "ols_hc3_normal_reference",
        "maxLeverage": float(np.max(leverage)),
        "maxAbsoluteStandardizedResidual": float(
            np.max(np.abs(residuals)) / max(float(np.std(residuals, ddof=1)), 1e-12)
        ),
    }


def rank_residuals(values: np.ndarray, controls: np.ndarray | None) -> np.ndarray:
    ranked = pd.Series(values).rank(method="average").to_numpy(dtype=float)
    if controls is None or controls.size == 0:
        return ranked - ranked.mean()
    control_columns = [np.ones(len(ranked))]
    for index in range(controls.shape[1]):
        control_columns.append(
            pd.Series(controls[:, index]).rank(method="average").to_numpy(dtype=float)
        )
    design = np.column_stack(control_columns)
    return ranked - design @ (np.linalg.pinv(design) @ ranked)


def spearman_from_residuals(x_residual: np.ndarray, y_residual: np.ndarray) -> float:
    denominator = math.sqrt(
        float(np.dot(x_residual, x_residual) * np.dot(y_residual, y_residual))
    )
    if denominator <= 0:
        raise RelationshipExecutionError("Spearman indefinido para postos constantes")
    return float(np.dot(x_residual, y_residual) / denominator)


def partial_spearman(
    x: np.ndarray, y: np.ndarray, controls: np.ndarray | None = None
) -> float:
    return spearman_from_residuals(
        rank_residuals(x, controls), rank_residuals(y, controls)
    )


def permutation_spearman_p_value(
    x: np.ndarray,
    y: np.ndarray,
    controls: np.ndarray | None,
    *,
    seed: int,
    repetitions: int = 99_999,
) -> tuple[float, float]:
    x_residual = rank_residuals(x, controls)
    y_residual = rank_residuals(y, controls)
    observed = abs(spearman_from_residuals(x_residual, y_residual))
    denominator = math.sqrt(
        float(np.dot(x_residual, x_residual) * np.dot(y_residual, y_residual))
    )
    rng = np.random.default_rng(seed)
    extreme = 0
    for _ in range(repetitions):
        permuted = rng.permutation(y_residual)
        if abs(float(np.dot(x_residual, permuted) / denominator)) >= observed - 1e-15:
            extreme += 1
    return (extreme + 1.0) / (repetitions + 1.0), 1.0 / (repetitions + 1.0)


def bootstrap_spearman_interval(
    x: np.ndarray,
    y: np.ndarray,
    controls: np.ndarray | None,
    *,
    seed: int,
    repetitions: int = 10_000,
) -> tuple[float, float, int]:
    rng = np.random.default_rng(seed)
    estimates: list[float] = []
    observation_count = len(x)
    for _ in range(repetitions):
        indices = rng.integers(0, observation_count, size=observation_count)
        sampled_controls = None if controls is None else controls[indices]
        try:
            estimates.append(
                partial_spearman(x[indices], y[indices], sampled_controls)
            )
        except RelationshipExecutionError:
            continue
    if len(estimates) < int(repetitions * 0.8):
        raise RelationshipExecutionError("Bootstrap Spearman excessivamente degenerado")
    lower, upper = np.quantile(np.asarray(estimates), [0.025, 0.975])
    return float(lower), float(upper), len(estimates)


def fit_cross_section_spearman(
    frame: pd.DataFrame,
    *,
    hypothesis_id: str,
) -> dict[str, Any]:
    control_columns = [
        column for column in frame.columns if column.startswith("control")
    ]
    required = ["outcome", "exposure", *control_columns]
    work = frame[["entityId", "year", *required]].replace(
        [np.inf, -np.inf], np.nan
    ).dropna().copy()
    x = work["exposure"].to_numpy(float)
    y = work["outcome"].to_numpy(float)
    controls = (
        work[control_columns].to_numpy(float) if control_columns else None
    )
    estimate = partial_spearman(x, y, controls)
    seed = stable_seed(hypothesis_id)
    p_value, attainable_floor = permutation_spearman_p_value(
        x, y, controls, seed=seed
    )
    interval_low, interval_high, bootstrap_count = bootstrap_spearman_interval(
        x, y, controls, seed=seed + 1
    )
    return {
        "estimate": estimate,
        "standardError": None,
        "intervalLow": interval_low,
        "intervalHigh": interval_high,
        "pValue": p_value,
        "nObservations": int(len(work)),
        "nMunicipalities": int(work["entityId"].nunique()),
        "nPeriods": int(work["year"].nunique()),
        "periods": sorted(int(value) for value in work["year"].unique()),
        "inference": "spearman_99999_deterministic_permutations",
        "permutationDrawCount": 99_999,
        "bootstrapDrawCount": bootstrap_count,
        "attainablePValueFloor": attainable_floor,
    }


COUNT_LIKE_VARIABLES = {
    "ENROLL_FF",
    "ENROLL_FI",
    "ENROLL_HS",
    "SCHOOL_COUNT",
    "EJA_HS",
    "EPT_ENROLLMENTS",
    "RURAL_CLASSES_ALL",
    "RURAL_SCHOOLS_ALL",
    "RURAL_ENROLL_ALL",
    "RURAL_CLASSES_EJA",
    "RURAL_SCHOOLS_EJA",
    "RURAL_ENROLL_EJA",
    "RURAL_CLASSES_FUNDAMENTAL",
    "RURAL_SCHOOLS_FUNDAMENTAL",
    "RURAL_ENROLL_FUNDAMENTAL",
    "RURAL_CLASSES_HIGH_SCHOOL",
    "RURAL_SCHOOLS_HIGH_SCHOOL",
    "RURAL_ENROLL_HIGH_SCHOOL",
    "AEE_RESOURCE_ROOMS",
    "AEE_SCHOOLS",
    "AEE_COMMON",
    "AEE_EXCLUSIVE",
    "AEE_SPECIAL",
}
POPULATION_VARIABLES = {
    "POP_FF",
    "POP_FI",
    "POP_HS",
    "POP_TOTAL",
    "POP_18_24",
}
PER_TEN_POINT_EXPOSURES = {
    "FULLTIME_SHARE_FF",
    "FULLTIME_SHARE_FI",
    "FULLTIME_SHARE_HS",
    "INTERNET_SHARE",
    "TEACHER_FF",
    "TEACHER_FI",
    "TEACHER_HS",
    "ADULT_HS_COMPLETION",
    "RURAL_SHARE_STATE",
    "WORKER_HS_INCOMPLETE_SHARE_18_24",
}
STANDARDIZED_EXPOSURE_FAMILIES = {
    "R05_INSE_TRAJECTORY",
    "R07_YOUTH_WORK_TRAJECTORY",
    "R08_WORK_STUDY_COMPATIBILITY",
    "R17_EDUCATION_WAGE_SIGNAL",
    "R18_APPRENTICESHIP_EPT_HIGH_SCHOOL",
}


def family_year_bounds(hypothesis: Mapping[str, Any]) -> set[int]:
    family = hypothesis["familyId"]
    exposure = hypothesis["exposureVariableId"]
    outcome = hypothesis["outcomeVariableId"]
    if family in {"R01_DEMOGRAPHY_STAGE_ENROLLMENT", "R02_DEMOGRAPHY_OFFER_RESPONSE"}:
        return set(range(2018, 2026))
    if family in {
        "R03_TERRITORIAL_PRESSURE_TRAJECTORY",
        "R04_SCHOOL_CONDITIONS_TRAJECTORY",
    }:
        return set(range(2019 if "DISTORTION" in outcome else 2018, 2026))
    if family == "R05_INSE_TRAJECTORY":
        return {2019, 2021, 2023}
    if family == "R06_ADULT_SCHOOLING_TRAJECTORY":
        return {2022}
    if family == "R07_YOUTH_WORK_TRAJECTORY":
        return set(range(2020 if exposure.startswith("CAGED") else 2019, 2026))
    if family == "R08_WORK_STUDY_COMPATIBILITY":
        return set(
            range(
                2020 if exposure.startswith("APPRENTICE_ADMISSION") else 2019,
                2026,
            )
        )
    if family == "R09_WORKER_SCHOOLING_EJA_EPT":
        if hypothesis["methodPreset"] == "CROSS_SECTION_VALE":
            return {2022}
        return set(range(2023 if outcome == "EPT_ENROLLMENTS" else 2019, 2026))
    if family == "R10_ECONOMIC_STRUCTURE_EPT":
        return {2025}
    if family == "R11_VULNERABILITY_EDUCATION":
        return {2024}
    if family == "R12_RURALITY_ACCESS":
        if hypothesis["methodPreset"] == "PANEL_RS":
            return set(range(2019 if "DISTORTION" in outcome else 2018, 2026))
        return set(range(2014, 2026))
    if family == "R13_AEE_CAPACITY_INCLUSION":
        return set(range(2014, 2026))
    if family == "R14_EDUCATIONAL_MOBILITY_OFFER":
        return {2022}
    if family == "R15_FINANCE_CAPACITY":
        return {2024, 2025}
    if family == "R16_PNATE_RURAL_CONTEXT":
        return {2024, 2025, 2026}
    if family == "R17_EDUCATION_WAGE_SIGNAL":
        return set(range(2023 if outcome == "EPT_ENROLLMENTS" else 2019, 2026))
    if family == "R18_APPRENTICESHIP_EPT_HIGH_SCHOOL":
        return {2023, 2024, 2025}
    raise RelationshipExecutionError(f"Família sem janela operacional: {family}")


def merge_hypothesis_variables(
    hypothesis: Mapping[str, Any], frames: Mapping[str, pd.DataFrame]
) -> pd.DataFrame:
    variable_ids = [
        hypothesis["outcomeVariableId"],
        hypothesis["exposureVariableId"],
        *hypothesis["controls"],
    ]
    names = ["outcome", "exposure", *[
        f"control{index}" for index in range(len(hypothesis["controls"]))
    ]]
    merged: pd.DataFrame | None = None
    for variable_id, name in zip(variable_ids, names, strict=True):
        piece = frames[variable_id].rename(columns={"value": name})
        merged = (
            piece
            if merged is None
            else merged.merge(
                piece, on=["entityId", "year"], how="outer", validate="one_to_one"
            )
        )
    if merged is None:
        raise RelationshipExecutionError("Hipótese sem variáveis")
    return merged[merged["year"].isin(family_year_bounds(hypothesis))].copy()


def positive_log(series: pd.Series) -> pd.Series:
    result = pd.Series(np.nan, index=series.index, dtype=float)
    mask = series > 0
    result.loc[mask] = np.log(series.loc[mask].astype(float))
    return result


def nonnegative_log1p(series: pd.Series) -> pd.Series:
    result = pd.Series(np.nan, index=series.index, dtype=float)
    mask = series >= 0
    result.loc[mask] = np.log1p(series.loc[mask].astype(float))
    return result


def transform_variable(
    series: pd.Series,
    variable_id: str,
    *,
    family_id: str,
    role: str,
) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    if variable_id in POPULATION_VARIABLES:
        return positive_log(values)
    if variable_id in COUNT_LIKE_VARIABLES:
        return nonnegative_log1p(values)
    if variable_id.startswith("PRESSURE_"):
        return positive_log(values)
    if role == "exposure" and variable_id in PER_TEN_POINT_EXPOSURES:
        return values / 10.0
    if role == "control" and variable_id in PER_TEN_POINT_EXPOSURES:
        return values / 10.0
    return values.astype(float)


def standardize(series: pd.Series) -> pd.Series:
    mean = float(series.mean())
    deviation = float(series.std(ddof=1))
    if not math.isfinite(deviation) or deviation <= 1e-12:
        return pd.Series(np.nan, index=series.index, dtype=float)
    return (series - mean) / deviation


def first_difference(frame: pd.DataFrame, columns: Sequence[str]) -> pd.DataFrame:
    work = frame.sort_values(["entityId", "year"]).copy()
    previous_year = work.groupby("entityId", sort=False)["year"].shift(1)
    consecutive = work["year"] - previous_year == 1
    for column in columns:
        work[column] = work.groupby("entityId", sort=False)[column].diff()
    return work[consecutive].copy()


def assemble_model_frame(
    hypothesis: Mapping[str, Any], frames: Mapping[str, pd.DataFrame]
) -> tuple[pd.DataFrame, dict[str, Any]]:
    family = hypothesis["familyId"]
    if hypothesis["methodPreset"] == "CHANGE_CROSS_SECTION_VALE":
        outcome = frames[hypothesis["outcomeVariableId"]]
        control = frames[hypothesis["controls"][0]]
        exposure = frames[hypothesis["exposureVariableId"]]
        outcome_wide = outcome[outcome["year"].isin([2023, 2025])].pivot(
            index="entityId", columns="year", values="value"
        )
        control_wide = control[control["year"].isin([2023, 2025])].pivot(
            index="entityId", columns="year", values="value"
        )
        if not {2023, 2025}.issubset(outcome_wide.columns) or not {
            2023,
            2025,
        }.issubset(control_wide.columns):
            return pd.DataFrame(), {"transformation": "2023_to_2025_change"}
        changes = pd.DataFrame(
            {
                "outcome": nonnegative_log1p(outcome_wide[2025])
                - nonnegative_log1p(outcome_wide[2023]),
                "control0": positive_log(control_wide[2025])
                - positive_log(control_wide[2023]),
            }
        ).reset_index()
        changes["year"] = 2025
        work = changes.merge(
            exposure[exposure["year"] == 2025].rename(columns={"value": "exposure"}),
            on=["entityId", "year"],
            how="outer",
            validate="one_to_one",
        )
        work["exposure"] = standardize(work["exposure"])
        work["control0"] = standardize(work["control0"])
        return work, {
            "transformation": "exposure_2019_2025_and_log_outcome_change_2023_2025",
            "firstDifferenced": True,
            "standardizedExposure": True,
        }

    work = merge_hypothesis_variables(hypothesis, frames)
    variable_ids = [
        hypothesis["outcomeVariableId"],
        hypothesis["exposureVariableId"],
        *hypothesis["controls"],
    ]
    columns = ["outcome", "exposure", *[
        f"control{index}" for index in range(len(hypothesis["controls"]))
    ]]
    roles = ["outcome", "exposure", *(["control"] * len(hypothesis["controls"]))]
    for column, variable_id, role in zip(columns, variable_ids, roles, strict=True):
        work[column] = transform_variable(
            work[column], variable_id, family_id=family, role=role
        )
    first_differenced = family in {
        "R01_DEMOGRAPHY_STAGE_ENROLLMENT",
        "R02_DEMOGRAPHY_OFFER_RESPONSE",
    }
    if first_differenced:
        work = first_difference(work, columns)
    if family in STANDARDIZED_EXPOSURE_FAMILIES:
        work["exposure"] = standardize(work["exposure"])
    for control_column in [column for column in columns if column.startswith("control")]:
        work[control_column] = standardize(work[control_column])
    work = work.sort_values(["entityId", "year"]).reset_index(drop=True)
    return work, {
        "transformation": "preregistered_family_scale",
        "firstDifferenced": first_differenced,
        "standardizedExposure": family in STANDARDIZED_EXPOSURE_FAMILIES,
        "outcomeVariable": hypothesis["outcomeVariableId"],
        "exposureVariable": hypothesis["exposureVariableId"],
        "controlVariables": list(hypothesis["controls"]),
    }


def minimums_for_method(
    method_preset: str, method_presets: Mapping[str, Mapping[str, Any]]
) -> tuple[int, int]:
    preset = method_presets[method_preset]
    return int(preset["minimumMunicipalities"]), int(preset["minimumPeriods"])


def frame_feasibility(
    frame: pd.DataFrame,
    *,
    method_preset: str,
    method_presets: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    columns = [
        "outcome",
        "exposure",
        *[column for column in frame.columns if column.startswith("control")],
    ]
    if not set(["entityId", "year", *columns]).issubset(frame.columns):
        complete = pd.DataFrame(columns=["entityId", "year", *columns])
    else:
        complete = frame[["entityId", "year", *columns]].replace(
            [np.inf, -np.inf], np.nan
        ).dropna().copy()
    municipality_count = int(complete["entityId"].nunique())
    period_count = int(complete["year"].nunique())
    minimum_municipalities, minimum_periods = minimums_for_method(
        method_preset, method_presets
    )
    reasons: list[str] = []
    if municipality_count < minimum_municipalities:
        reasons.append(
            f"municipalities={municipality_count}<minimum={minimum_municipalities}"
        )
    if period_count < minimum_periods:
        reasons.append(f"periods={period_count}<minimum={minimum_periods}")
    if len(complete) == 0 or complete["exposure"].nunique(dropna=True) < 2:
        reasons.append("constant_or_unavailable_exposure")
    if len(complete) == 0 or complete["outcome"].nunique(dropna=True) < 2:
        reasons.append("constant_or_unavailable_outcome")
    return {
        "feasible": not reasons,
        "reasons": reasons,
        "completeFrame": complete,
        "nObservations": int(len(complete)),
        "nMunicipalities": municipality_count,
        "nPeriods": period_count,
        "periods": sorted(int(value) for value in complete["year"].unique()),
        "minimumMunicipalities": minimum_municipalities,
        "minimumPeriods": minimum_periods,
    }


def direction_of(value: float | None) -> str:
    if value is None or not math.isfinite(float(value)) or float(value) == 0:
        return "null_or_zero"
    return "positive" if float(value) > 0 else "negative"


def expected_direction_matches(value: float | None, expected: str) -> bool:
    if value is None or not math.isfinite(float(value)) or float(value) == 0:
        return False
    if expected == "ambiguous":
        return True
    return direction_of(value) == expected


def rescale_effect(
    hypothesis: Mapping[str, Any], fit: Mapping[str, Any]
) -> dict[str, Any]:
    result = dict(fit)
    family = hypothesis["familyId"]
    if family == "R01_DEMOGRAPHY_STAGE_ENROLLMENT" or (
        family == "R02_DEMOGRAPHY_OFFER_RESPONSE"
        and hypothesis["outcomeVariableId"] == "SCHOOL_COUNT"
    ):
        transform = lambda value: 100.0 * math.expm1(float(value) * math.log(1.1))
    elif family in {
        "R02_DEMOGRAPHY_OFFER_RESPONSE",
        "R03_TERRITORIAL_PRESSURE_TRAJECTORY",
    }:
        transform = lambda value: float(value) * math.log(1.1)
    else:
        transform = lambda value: float(value)
    nonlinear = family == "R01_DEMOGRAPHY_STAGE_ENROLLMENT" or (
        family == "R02_DEMOGRAPHY_OFFER_RESPONSE"
        and hypothesis["outcomeVariableId"] == "SCHOOL_COUNT"
    )
    for key in ("estimate", "intervalLow", "intervalHigh"):
        if result.get(key) is not None:
            result[key] = transform(result[key])
    if nonlinear:
        result["standardError"] = None
    elif result.get("standardError") is not None and family in {
        "R02_DEMOGRAPHY_OFFER_RESPONSE",
        "R03_TERRITORIAL_PRESSURE_TRAJECTORY",
    }:
        result["standardError"] = float(result["standardError"]) * math.log(1.1)
    result["effectScale"] = hypothesis["effectScale"]
    return result


def fit_by_method(
    frame: pd.DataFrame,
    *,
    hypothesis: Mapping[str, Any],
    exact_inference: bool = True,
) -> dict[str, Any]:
    method = hypothesis["methodPreset"]
    if method == "PANEL_RS":
        return fit_twfe(frame, wild_cluster=False)
    if method in {"PANEL_VALE", "SHORT_PANEL_VALE"}:
        return fit_twfe(frame, wild_cluster=exact_inference)
    if method == "REPEATED_CROSS_SECTION_RS":
        return fit_ols_hc3(frame, include_period_effects=True)
    if method == "CROSS_SECTION_RS":
        return fit_ols_hc3(frame, include_period_effects=False)
    if method in {"CROSS_SECTION_VALE", "CHANGE_CROSS_SECTION_VALE"}:
        if exact_inference:
            return fit_cross_section_spearman(
                frame, hypothesis_id=hypothesis["hypothesisId"]
            )
        control_columns = [
            column for column in frame.columns if column.startswith("control")
        ]
        complete = frame[["entityId", "year", "outcome", "exposure", *control_columns]].dropna()
        controls = (
            complete[control_columns].to_numpy(float) if control_columns else None
        )
        estimate = partial_spearman(
            complete["exposure"].to_numpy(float),
            complete["outcome"].to_numpy(float),
            controls,
        )
        return {
            "estimate": estimate,
            "standardError": None,
            "intervalLow": None,
            "intervalHigh": None,
            "pValue": None,
            "nObservations": int(len(complete)),
            "nMunicipalities": int(complete["entityId"].nunique()),
            "nPeriods": int(complete["year"].nunique()),
            "periods": sorted(int(value) for value in complete["year"].unique()),
            "inference": "spearman_coefficient_only_robustness",
        }
    raise RelationshipExecutionError(f"Método não ajustável: {method}")


def shifted_exposure_frame(frame: pd.DataFrame, shift: int) -> pd.DataFrame:
    work = frame.sort_values(["entityId", "year"]).copy()
    grouped = work.groupby("entityId", sort=False)
    work["sourceYear"] = grouped["year"].shift(shift)
    work["exposure"] = grouped["exposure"].shift(shift)
    expected_gap = shift
    return work[(work["year"] - work["sourceYear"]) == expected_gap].copy()


def rank_sensitivity(frame: pd.DataFrame, *, include_period: bool) -> float | None:
    control_columns = [
        column for column in frame.columns if column.startswith("control")
    ]
    complete = frame[["outcome", "exposure", "year", *control_columns]].dropna()
    if len(complete) < 3:
        return None
    controls: list[np.ndarray] = [
        complete[column].to_numpy(float) for column in control_columns
    ]
    if include_period:
        controls.append(complete["year"].to_numpy(float))
    control_matrix = np.column_stack(controls) if controls else None
    try:
        return partial_spearman(
            complete["exposure"].to_numpy(float),
            complete["outcome"].to_numpy(float),
            control_matrix,
        )
    except RelationshipExecutionError:
        return None


def fit_diagnostic_variant(
    frame: pd.DataFrame,
    *,
    hypothesis: Mapping[str, Any],
    method_presets: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    feasibility = frame_feasibility(
        frame,
        method_preset=hypothesis["methodPreset"],
        method_presets=method_presets,
    )
    if not feasibility["feasible"]:
        return {
            "state": "INFEASIBLE",
            "reasons": feasibility["reasons"],
            "nObservations": feasibility["nObservations"],
            "nMunicipalities": feasibility["nMunicipalities"],
            "nPeriods": feasibility["nPeriods"],
        }
    try:
        fit = fit_by_method(
            feasibility["completeFrame"],
            hypothesis=hypothesis,
            exact_inference=False,
        )
    except RelationshipExecutionError as error:
        return {
            "state": "INFEASIBLE",
            "reasons": [f"fit_error:{error}"],
            "nObservations": feasibility["nObservations"],
            "nMunicipalities": feasibility["nMunicipalities"],
            "nPeriods": feasibility["nPeriods"],
        }
    return {
        "state": "FIT",
        "estimate": fit["estimate"],
        "observedDirection": direction_of(fit["estimate"]),
        "nObservations": fit["nObservations"],
        "nMunicipalities": fit["nMunicipalities"],
        "nPeriods": fit["nPeriods"],
        "periods": fit["periods"],
    }


def leave_one_out_diagnostic(
    frame: pd.DataFrame,
    *,
    hypothesis: Mapping[str, Any],
    method_presets: Mapping[str, Mapping[str, Any]],
    region_map: Mapping[str, str],
    primary_estimate: float,
) -> dict[str, Any]:
    method = hypothesis["methodPreset"]
    work = frame.copy()
    if method in {"PANEL_RS", "REPEATED_CROSS_SECTION_RS", "CROSS_SECTION_RS"}:
        work["leaveGroup"] = work["entityId"].map(region_map)
        grouping = "region"
    else:
        work["leaveGroup"] = work["entityId"]
        grouping = "municipality"
    groups = sorted(value for value in work["leaveGroup"].dropna().unique())
    variants: list[dict[str, Any]] = []
    estimates: list[float] = []
    for group in groups:
        variant = fit_diagnostic_variant(
            work[work["leaveGroup"] != group].drop(columns="leaveGroup"),
            hypothesis=hypothesis,
            method_presets=method_presets,
        )
        variant["omitted"] = str(group)
        variants.append(variant)
        if variant["state"] == "FIT":
            estimates.append(float(variant["estimate"]))
    if not groups or len(estimates) != len(groups):
        sign_share = None
        state = "INFEASIBLE"
    else:
        primary_sign = 1 if primary_estimate > 0 else -1
        sign_share = sum(
            1 for estimate in estimates if (1 if estimate > 0 else -1) == primary_sign
        ) / len(estimates)
        state = "COMPLETE"
    return {
        "state": state,
        "grouping": grouping,
        "variantCount": len(groups),
        "fitCount": len(estimates),
        "signShare": sign_share,
        "minimumEstimate": min(estimates) if estimates else None,
        "maximumEstimate": max(estimates) if estimates else None,
        "variants": variants,
    }


def panel_robustness(
    frame: pd.DataFrame,
    *,
    hypothesis: Mapping[str, Any],
    method_presets: Mapping[str, Mapping[str, Any]],
    region_map: Mapping[str, str],
    primary_fit: Mapping[str, Any],
) -> dict[str, Any]:
    if hypothesis["methodPreset"] == "SHORT_PANEL_VALE":
        lag = {"state": "NOT_APPLICABLE_PREDECLARED"}
    else:
        lag = fit_diagnostic_variant(
            shifted_exposure_frame(frame, 1),
            hypothesis=hypothesis,
            method_presets=method_presets,
        )
    lead = fit_diagnostic_variant(
        shifted_exposure_frame(frame, -1),
        hypothesis=hypothesis,
        method_presets=method_presets,
    )
    primary_estimate = float(primary_fit["estimate"])
    if lead["state"] != "FIT":
        placebo_state = "INFEASIBLE"
    elif abs(float(lead["estimate"])) < abs(primary_estimate):
        placebo_state = "WEAKER_THAN_PRIMARY"
    else:
        placebo_state = "NOT_WEAKER_THAN_PRIMARY"
    if hypothesis["methodPreset"] == "SHORT_PANEL_VALE":
        pandemic = {"state": "NOT_APPLICABLE_PREDECLARED"}
        pandemic_state = "NOT_APPLICABLE_PREDECLARED"
    elif hypothesis["pandemicSensitivity"] == "APPLICABLE":
        pandemic = fit_diagnostic_variant(
            frame[~frame["year"].isin([2020, 2021])],
            hypothesis=hypothesis,
            method_presets=method_presets,
        )
        if pandemic["state"] != "FIT":
            pandemic_state = "INFEASIBLE"
        elif direction_of(pandemic["estimate"]) == direction_of(primary_estimate):
            pandemic_state = "PASSED_SAME_SIGN"
        else:
            pandemic_state = "FAILED_SIGN_REVERSAL"
    else:
        pandemic = {"state": "NOT_APPLICABLE_PREDECLARED"}
        pandemic_state = "NOT_APPLICABLE_PREDECLARED"
    leave_one_out = leave_one_out_diagnostic(
        frame,
        hypothesis=hypothesis,
        method_presets=method_presets,
        region_map=region_map,
        primary_estimate=primary_estimate,
    )
    lag_feasible = lag["state"] in {"FIT", "NOT_APPLICABLE_PREDECLARED"}
    required_feasible = (
        lag_feasible
        and lead["state"] == "FIT"
        and leave_one_out["state"] == "COMPLETE"
        and pandemic_state not in {"INFEASIBLE"}
    )
    return {
        "lagOne": lag,
        "leadOnePlacebo": lead,
        "pandemicExclusion": pandemic,
        "leaveOneOut": leave_one_out,
        "placeboState": placebo_state,
        "pandemicSensitivityState": pandemic_state,
        "requiredDiagnosticsFeasible": required_feasible,
    }


def nonpanel_robustness(
    frame: pd.DataFrame,
    *,
    hypothesis: Mapping[str, Any],
    method_presets: Mapping[str, Mapping[str, Any]],
    region_map: Mapping[str, str],
    primary_fit: Mapping[str, Any],
) -> dict[str, Any]:
    method = hypothesis["methodPreset"]
    leave_one_out = leave_one_out_diagnostic(
        frame,
        hypothesis=hypothesis,
        method_presets=method_presets,
        region_map=region_map,
        primary_estimate=float(primary_fit["estimate"]),
    )
    rank_value = (
        rank_sensitivity(
            frame, include_period=method == "REPEATED_CROSS_SECTION_RS"
        )
        if method in {"REPEATED_CROSS_SECTION_RS", "CROSS_SECTION_RS"}
        else None
    )
    alternative_endpoint = None
    required_feasible = leave_one_out["state"] == "COMPLETE"
    if method == "CHANGE_CROSS_SECTION_VALE":
        alternative_endpoint = {
            "state": "INFEASIBLE_FROZEN_EXPOSURE_HAS_NO_ALTERNATIVE_ENDPOINT",
            "reason": (
                "The frozen 2019-2025 structural exposure cannot be redefined "
                "after preregistration."
            ),
        }
        required_feasible = False
    return {
        "leaveOneOut": leave_one_out,
        "rankSensitivityEstimate": rank_value,
        "alternativeEndpoint": alternative_endpoint,
        "placeboState": "NOT_APPLICABLE",
        "pandemicSensitivityState": "NOT_APPLICABLE",
        "requiredDiagnosticsFeasible": required_feasible,
    }


def base_result_record(
    hypothesis: Mapping[str, Any],
    variable_lookup: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    exposure_lens = variable_lookup[hypothesis["exposureVariableId"]][
        "territorialLens"
    ]
    outcome_lens = variable_lookup[hypothesis["outcomeVariableId"]][
        "territorialLens"
    ]
    lens_state = (
        "SAME_LENS_AGGREGATE_COMPARISON"
        if exposure_lens == outcome_lens
        else "EXPLICIT_CROSS_LENS_ECOLOGICAL_COMPARISON"
    )
    return {
        "hypothesisId": hypothesis["hypothesisId"],
        "familyId": hypothesis["familyId"],
        "multiplicityFamily": hypothesis["multiplicityFamily"],
        "lane": hypothesis["lane"],
        "methodPreset": hypothesis["methodPreset"],
        "priority": hypothesis["priority"],
        "resultKnowledgeState": hypothesis["resultKnowledgeState"],
        "entryClaimCeiling": hypothesis["entryClaimCeiling"],
        "exposureVariableId": hypothesis["exposureVariableId"],
        "outcomeVariableId": hypothesis["outcomeVariableId"],
        "controlVariableIds": list(hypothesis["controls"]),
        "status": None,
        "evidenceClass": None,
        "nObservations": 0,
        "nMunicipalities": 0,
        "nPeriods": 0,
        "estimate": None,
        "standardError": None,
        "intervalLow": None,
        "intervalHigh": None,
        "pValueRaw": None,
        "pValueForMultiplicity": 1.0,
        "qValueFamily": None,
        "qValueGlobal": None,
        "expectedDirection": hypothesis["expectedDirection"],
        "observedDirection": "not_estimated",
        "leaveOneOutSignShare": None,
        "placeboState": "NOT_APPLICABLE",
        "pandemicSensitivityState": "NOT_APPLICABLE",
        "exposureLens": exposure_lens,
        "outcomeLens": outcome_lens,
        "lensComparisonState": lens_state,
        "causalClaimAllowed": False,
        "promotionEligible": False,
        "limitation": None,
        "effectScale": hypothesis["effectScale"],
    }


def execute_hypothesis(
    hypothesis: Mapping[str, Any],
    *,
    frames: Mapping[str, pd.DataFrame],
    variable_lookup: Mapping[str, Mapping[str, Any]],
    method_presets: Mapping[str, Mapping[str, Any]],
    region_map: Mapping[str, str],
) -> tuple[dict[str, Any], dict[str, Any]]:
    result = base_result_record(hypothesis, variable_lookup)
    frame, transformation = assemble_model_frame(hypothesis, frames)
    if hypothesis["priority"] in {"BLOCKED", "DESCRIPTIVE"}:
        available = frame.dropna(
            subset=[
                column
                for column in ("exposure", "outcome")
                if column in frame.columns
            ]
        )
        result.update(
            {
                "status": (
                    "BLOCKED_NOT_COMPARABLE"
                    if hypothesis["priority"] == "BLOCKED"
                    else "DESCRIPTIVE_ONLY"
                ),
                "evidenceClass": (
                    "BOUNDARY_NOT_COMPARABLE"
                    if hypothesis["priority"] == "BLOCKED"
                    else "DESCRIPTIVE_CONTEXT"
                ),
                "nObservations": int(len(available)),
                "nMunicipalities": int(available["entityId"].nunique())
                if "entityId" in available
                else 0,
                "nPeriods": int(available["year"].nunique())
                if "year" in available
                else 0,
                "limitation": (
                    "Executor-network and total-network scopes are not comparable."
                    if hypothesis["priority"] == "BLOCKED"
                    else "Normative or accounting correspondence; no relational fit."
                ),
            }
        )
        return result, {
            "hypothesisId": hypothesis["hypothesisId"],
            "transformation": transformation,
            "primaryFeasibility": "NOT_APPLICABLE_DESCRIPTIVE",
        }

    feasibility = frame_feasibility(
        frame,
        method_preset=hypothesis["methodPreset"],
        method_presets=method_presets,
    )
    result.update(
        {
            "nObservations": feasibility["nObservations"],
            "nMunicipalities": feasibility["nMunicipalities"],
            "nPeriods": feasibility["nPeriods"],
        }
    )
    robustness_record: dict[str, Any] = {
        "hypothesisId": hypothesis["hypothesisId"],
        "transformation": transformation,
        "primaryFeasibility": {
            key: value for key, value in feasibility.items() if key != "completeFrame"
        },
    }
    if not feasibility["feasible"]:
        result.update(
            {
                "status": "INSUFFICIENT_DATA",
                "evidenceClass": "INSUFFICIENT_EVIDENCE",
                "limitation": "; ".join(feasibility["reasons"]),
            }
        )
        return result, robustness_record

    try:
        primary_fit_raw = fit_by_method(
            feasibility["completeFrame"], hypothesis=hypothesis, exact_inference=True
        )
    except RelationshipExecutionError as error:
        result.update(
            {
                "status": "INSUFFICIENT_DATA",
                "evidenceClass": "INSUFFICIENT_EVIDENCE",
                "limitation": f"primary_fit_error:{error}",
            }
        )
        robustness_record["primaryFitError"] = str(error)
        return result, robustness_record

    primary_fit = rescale_effect(hypothesis, primary_fit_raw)
    result.update(
        {
            "estimate": primary_fit["estimate"],
            "standardError": primary_fit.get("standardError"),
            "intervalLow": primary_fit["intervalLow"],
            "intervalHigh": primary_fit["intervalHigh"],
            "pValueRaw": primary_fit["pValue"],
            "observedDirection": direction_of(primary_fit["estimate"]),
            "attainablePValueFloor": primary_fit.get("attainablePValueFloor"),
            "inference": primary_fit["inference"],
        }
    )
    if hypothesis["methodPreset"] in {
        "PANEL_RS",
        "PANEL_VALE",
        "SHORT_PANEL_VALE",
    }:
        diagnostics = panel_robustness(
            feasibility["completeFrame"],
            hypothesis=hypothesis,
            method_presets=method_presets,
            region_map=region_map,
            primary_fit=primary_fit_raw,
        )
    else:
        diagnostics = nonpanel_robustness(
            feasibility["completeFrame"],
            hypothesis=hypothesis,
            method_presets=method_presets,
            region_map=region_map,
            primary_fit=primary_fit,
        )
    robustness_record["primaryFit"] = primary_fit
    robustness_record["diagnostics"] = diagnostics
    result.update(
        {
            "leaveOneOutSignShare": diagnostics["leaveOneOut"]["signShare"],
            "placeboState": diagnostics["placeboState"],
            "pandemicSensitivityState": diagnostics[
                "pandemicSensitivityState"
            ],
        }
    )
    if not diagnostics["requiredDiagnosticsFeasible"]:
        result.update(
            {
                "status": "INSUFFICIENT_DATA",
                "evidenceClass": "INSUFFICIENT_EVIDENCE",
                "pValueForMultiplicity": 1.0,
                "limitation": "One or more preregistered robustness checks were infeasible.",
            }
        )
    else:
        result.update(
            {
                "status": "ESTIMATED_PENDING_MULTIPLICITY",
                "evidenceClass": "EXPLORATORY_ASSOCIATION",
                "pValueForMultiplicity": float(primary_fit["pValue"]),
                "limitation": (
                    "Aggregate ecological association; not a causal or same-person link."
                ),
            }
        )
    return result, robustness_record


def contextualize_hypothesis(
    hypothesis: Mapping[str, Any],
    *,
    frames: Mapping[str, pd.DataFrame],
    region_map: Mapping[str, str],
) -> dict[str, Any]:
    exposure = frames[hypothesis["exposureVariableId"]].rename(
        columns={"value": "exposureRaw"}
    )
    outcome = frames[hypothesis["outcomeVariableId"]].rename(
        columns={"value": "outcomeRaw"}
    )
    common = exposure.merge(
        outcome, on=["entityId", "year"], how="inner", validate="one_to_one"
    )
    common = common[
        common["year"].isin(family_year_bounds(hypothesis))
        & common[["exposureRaw", "outcomeRaw"]].notna().all(axis=1)
    ].copy()
    common["regionSlug"] = common["entityId"].map(region_map)
    vale = common[common["regionSlug"] == VALE_REGION_SLUG].copy()
    if vale.empty:
        return {
            "state": "UNAVAILABLE",
            "reason": "No common Vale observation in the frozen window.",
            "mechanismId": hypothesis["mechanismId"],
        }
    latest_year = int(vale["year"].max())
    latest = vale[vale["year"] == latest_year]
    nova = latest[latest["entityId"] == NOVA_SANTA_RITA_IBGE_CODE]
    return {
        "state": "AVAILABLE" if len(nova) == 1 else "NOVA_SANTA_RITA_UNAVAILABLE",
        "year": latest_year,
        "valeMunicipalitiesWithBothValues": int(latest["entityId"].nunique()),
        "valeExposureMedian": float(latest["exposureRaw"].median()),
        "valeOutcomeMedian": float(latest["outcomeRaw"].median()),
        "novaSantaRitaExposure": (
            float(nova.iloc[0]["exposureRaw"]) if len(nova) == 1 else None
        ),
        "novaSantaRitaOutcome": (
            float(nova.iloc[0]["outcomeRaw"]) if len(nova) == 1 else None
        ),
        "mechanismId": hypothesis["mechanismId"],
        "alternativeExplanations": [
            "reverse_direction_or_simultaneity",
            "unmeasured_time_varying_territorial_factors",
            "aggregation_and_territorial_lens_difference",
        ],
        "interpretationBoundary": (
            "Vale and Nova Santa Rita values are aggregate contexts; they do not "
            "identify the same people across education and territorial sources."
        ),
    }


def interval_supports_direction(result: Mapping[str, Any]) -> bool:
    low = result.get("intervalLow")
    high = result.get("intervalHigh")
    if low is None or high is None:
        return False
    expected = result["expectedDirection"]
    if expected == "positive":
        return float(low) > 0
    if expected == "negative":
        return float(high) < 0
    if expected == "ambiguous":
        return float(low) > 0 or float(high) < 0
    return False


def finalize_multiplicity_and_promotions(
    results: list[dict[str, Any]],
    contexts: Mapping[str, Mapping[str, Any]],
) -> None:
    family_positions: dict[str, list[int]] = defaultdict(list)
    for index, result in enumerate(results):
        family_positions[result["multiplicityFamily"]].append(index)
    for positions in family_positions.values():
        adjusted = bh_adjust(
            [float(results[position]["pValueForMultiplicity"]) for position in positions]
        )
        for position, q_value in zip(positions, adjusted, strict=True):
            results[position]["qValueFamily"] = q_value
    global_adjusted = bh_adjust(
        [float(result["pValueForMultiplicity"]) for result in results]
    )
    for result, q_value in zip(results, global_adjusted, strict=True):
        result["qValueGlobal"] = q_value
        context = contexts[result["hypothesisId"]]
        result["contextState"] = context["state"]
        result["mechanismId"] = context.get("mechanismId")
        if result["status"] != "ESTIMATED_PENDING_MULTIPLICITY":
            continue
        is_rs = result["methodPreset"] in {
            "PANEL_RS",
            "REPEATED_CROSS_SECTION_RS",
            "CROSS_SECTION_RS",
        }
        threshold = 0.05 if is_rs else 0.10
        failures: list[str] = []
        if float(result["qValueFamily"]) > threshold:
            failures.append(f"family_q_above_{threshold}")
        if not expected_direction_matches(
            result["estimate"], result["expectedDirection"]
        ):
            failures.append("observed_direction_does_not_match_preregistration")
        if not interval_supports_direction(result):
            failures.append("interval_does_not_exclude_zero_in_supported_direction")
        if (
            result["leaveOneOutSignShare"] is None
            or float(result["leaveOneOutSignShare"]) < 0.8
        ):
            failures.append("leave_one_out_sign_share_below_0.8")
        if result["methodPreset"] in {
            "PANEL_RS",
            "PANEL_VALE",
            "SHORT_PANEL_VALE",
        } and result["placeboState"] != "WEAKER_THAN_PRIMARY":
            failures.append("lead_one_placebo_not_weaker")
        if result["pandemicSensitivityState"] not in {
            "PASSED_SAME_SIGN",
            "NOT_APPLICABLE",
            "NOT_APPLICABLE_PREDECLARED",
        }:
            failures.append("pandemic_sensitivity_not_passed")
        if not is_rs and result.get("attainablePValueFloor") is None:
            failures.append("vale_attainable_p_value_floor_missing")
        if context["state"] != "AVAILABLE":
            failures.append("nova_santa_rita_and_vale_context_unavailable")
        if not context.get("mechanismId") or not context.get(
            "alternativeExplanations"
        ):
            failures.append("mechanism_or_alternatives_missing")
        result["promotionGateFailures"] = failures
        if failures:
            result.update(
                {
                    "status": "NO_ROBUST_ASSOCIATION",
                    "evidenceClass": "EXPLORATORY_NOT_PROMOTED",
                    "promotionEligible": False,
                }
            )
        else:
            result.update(
                {
                    "status": "ROBUST_ASSOCIATION",
                    "evidenceClass": "ROBUST_ASSOCIATION",
                    "promotionEligible": True,
                }
            )


def artifact_records(root: Path, names: Sequence[str]) -> list[dict[str, Any]]:
    return [
        {
            "path": name,
            "sha256": sha256_file(root / name),
            "byteSize": (root / name).stat().st_size,
        }
        for name in names
    ]


def artifact_set_digest(records: Sequence[Mapping[str, Any]]) -> str:
    canonical = "\n".join(
        f"{record['path']}\t{record['sha256']}\t{record['byteSize']}"
        for record in records
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def lane_report_markdown(lane: str, results: Sequence[Mapping[str, Any]]) -> str:
    statuses = Counter(result["status"] for result in results)
    lines = [
        f"# Faixa analítica — {lane}",
        "",
        "Execução reproduzível do atlas congelado. Associação estatística não é causalidade.",
        "",
        f"- Hipóteses: {len(results)}",
        f"- Associações robustas: {statuses.get('ROBUST_ASSOCIATION', 0)}",
        f"- Associações não robustas: {statuses.get('NO_ROBUST_ASSOCIATION', 0)}",
        f"- Dados/robustez insuficientes: {statuses.get('INSUFFICIENT_DATA', 0)}",
        f"- Descritivas ou bloqueadas: {statuses.get('DESCRIPTIVE_ONLY', 0) + statuses.get('BLOCKED_NOT_COMPARABLE', 0)}",
        "",
        "## Resultado por hipótese",
        "",
    ]
    for result in results:
        estimate = (
            "indisponível"
            if result["estimate"] is None
            else f"{float(result['estimate']):.6g}"
        )
        lines.append(
            f"- `{result['hypothesisId']}` — {result['status']}; estimativa {estimate}; "
            f"q família {float(result['qValueFamily']):.6g}."
        )
    lines.extend(
        [
            "",
            "## Fronteira de interpretação",
            "",
            "Nenhum resultado liga as mesmas pessoas entre bases, identifica um desenho causal ou autoriza atribuição automática a Nova Santa Rita.",
            "",
        ]
    )
    return "\n".join(lines)


def write_lane_package(
    root: Path,
    *,
    lane: str,
    results: Sequence[Mapping[str, Any]],
    robustness: Sequence[Mapping[str, Any]],
    variable_audit: Mapping[str, Any],
    source_quality: Mapping[str, Any],
    parent_digest: str,
    public_digest: str,
) -> dict[str, Any]:
    lane_root = root / lane
    lane_root.mkdir(parents=True, exist_ok=True)
    write_json(lane_root / "RESULTS.json", list(results))
    write_csv(lane_root / "RESULTS.csv", list(results))
    write_json(lane_root / "ROBUSTNESS.json", list(robustness))
    lane_variable_ids = sorted(
        {
            variable_id
            for result in results
            for variable_id in (
                result["exposureVariableId"],
                result["outcomeVariableId"],
                *result["controlVariableIds"],
            )
        }
    )
    quality = {
        "schemaVersion": "vocacoes-pne-relationship-atlas-data-quality-v1",
        "state": "PASS",
        "lane": lane,
        "sourceQuality": source_quality,
        "variables": {
            variable_id: variable_audit[variable_id]
            for variable_id in lane_variable_ids
        },
        "availabilityStatesNumericOnly": sorted(NUMERIC_AVAILABILITY),
        "denominatorZeroProducesNull": True,
        "identity": "textual_ibge_code_7_digits",
    }
    write_json(lane_root / "DATA_QUALITY.json", quality)
    atomic_write_text(lane_root / "REPORT.md", lane_report_markdown(lane, results))
    records = artifact_records(lane_root, RESULT_FILES[:-1])
    manifest = {
        "schemaVersion": "vocacoes-pne-relationship-atlas-lane-manifest-v1",
        "state": "COMPLETE",
        "generatedAt": GENERATED_AT,
        "lane": lane,
        "hypothesisCount": len(results),
        "verifiedParentArtifactSetDigestSha256": parent_digest,
        "executionContractSha256": sha256_file(EXECUTION_CONTRACT_PATH),
        "executionModuleSha256": sha256_file(MODULE_PATH),
        "publicDataTreeDigestBeforeAndAfter": public_digest,
        "artifacts": records,
        "artifactSetDigestSha256": artifact_set_digest(records),
        "operationalConstraints": {
            "networkUsed": False,
            "databaseUsed": False,
            "publicDataWritten": False,
            "fullBuildUsed": False,
            "sourceRefreshUsed": False,
        },
    }
    write_json(lane_root / "MANIFEST.json", manifest)
    return manifest


def write_reconciliation_package(
    root: Path,
    *,
    results: Sequence[Mapping[str, Any]],
    contexts: Mapping[str, Mapping[str, Any]],
    lane_manifests: Sequence[Mapping[str, Any]],
    source_quality: Mapping[str, Any],
    public_digest: str,
) -> dict[str, Any]:
    reconciliation_root = root / "reconciliation"
    reconciliation_root.mkdir(parents=True, exist_ok=True)
    write_json(reconciliation_root / "ALL_RESULTS.json", list(results))
    write_csv(reconciliation_root / "ALL_RESULTS.csv", list(results))
    promoted = [
        {"result": result, "context": contexts[result["hypothesisId"]]}
        for result in results
        if result["promotionEligible"]
    ]
    negative = [
        {
            "result": result,
            "context": contexts[result["hypothesisId"]],
            "publicUse": (
                "BOUNDARY_CANDIDATE"
                if result["priority"] == "PRIMARY"
                and result["status"]
                in {"NO_ROBUST_ASSOCIATION", "INSUFFICIENT_DATA"}
                else "TECHNICAL_ATLAS_ONLY"
            ),
        }
        for result in results
        if not result["promotionEligible"]
    ]
    write_json(reconciliation_root / "PROMOTION_LEDGER.json", promoted)
    write_json(reconciliation_root / "NEGATIVE_LEDGER.json", negative)
    status_counts = Counter(result["status"] for result in results)
    quality = {
        "schemaVersion": "vocacoes-pne-relationship-atlas-results-qa-v1",
        "state": "PASS",
        "resultCount": len(results),
        "expectedResultCount": 98,
        "uniqueHypothesisCount": len(
            {result["hypothesisId"] for result in results}
        ),
        "statusCounts": dict(sorted(status_counts.items())),
        "promotionCount": len(promoted),
        "negativeOrBoundaryCount": len(negative),
        "allCausalClaimsBlocked": all(
            result["causalClaimAllowed"] is False for result in results
        ),
        "allPValuesPresentForMultiplicity": all(
            result["pValueForMultiplicity"] is not None for result in results
        ),
        "allFamilyAndGlobalQValuesPresent": all(
            result["qValueFamily"] is not None
            and result["qValueGlobal"] is not None
            for result in results
        ),
        "sourceQuality": source_quality,
        "publicDataTreeDigestBeforeAndAfter": public_digest,
        "networkUsed": False,
        "databaseUsed": False,
        "fullBuildUsed": False,
        "sourceRefreshUsed": False,
    }
    write_json(reconciliation_root / "QA_SUMMARY.json", quality)
    records = artifact_records(reconciliation_root, COMBINED_FILES[:-1])
    manifest = {
        "schemaVersion": "vocacoes-pne-relationship-atlas-reconciliation-manifest-v1",
        "state": "COMPLETE",
        "generatedAt": GENERATED_AT,
        "parentArtifactSetDigestSha256": EXPECTED_PARENT_DIGEST,
        "executionContractSha256": sha256_file(EXECUTION_CONTRACT_PATH),
        "hypothesisMatrixSha256": sha256_file(
            PREREGISTRATION_ROOT / "HYPOTHESIS_MATRIX.json"
        ),
        "laneManifests": [
            {
                "lane": manifest["lane"],
                "hypothesisCount": manifest["hypothesisCount"],
                "artifactSetDigestSha256": manifest["artifactSetDigestSha256"],
            }
            for manifest in lane_manifests
        ],
        "artifacts": records,
        "artifactSetDigestSha256": artifact_set_digest(records),
        "publicDataTreeDigestBeforeAndAfter": public_digest,
    }
    write_json(reconciliation_root / "MANIFEST.json", manifest)
    return manifest


def load_frozen_program() -> tuple[
    list[dict[str, Any]], list[dict[str, Any]], dict[str, Any], str
]:
    parent_manifest = validate_preregistration(PREREGISTRATION_ROOT)
    parent_digest = parent_manifest["artifactSetDigestSha256"]
    if parent_digest != EXPECTED_PARENT_DIGEST:
        raise RelationshipExecutionError(
            f"Freeze parental divergiu: {parent_digest} != {EXPECTED_PARENT_DIGEST}"
        )
    execution_hash = sha256_file(EXECUTION_CONTRACT_PATH)
    if execution_hash != EXPECTED_EXECUTION_CONTRACT_SHA256:
        raise RelationshipExecutionError(
            "Contrato de execução mudou após auditoria do Fable"
        )
    hypotheses_payload = read_json(PREREGISTRATION_ROOT / "HYPOTHESIS_MATRIX.json")
    variables_payload = read_json(PREREGISTRATION_ROOT / "ANALYTIC_VARIABLES.json")
    if sha256_file(PREREGISTRATION_ROOT / "HYPOTHESIS_MATRIX.json") != (
        "3dc0b9d75d175280da009b7972980606d4d8ae05e2b71713892cdcf08054fe12"
    ):
        raise RelationshipExecutionError("Matriz de hipóteses mudou após freeze")
    hypotheses = hypotheses_payload["hypotheses"]
    variables = variables_payload["variables"]
    if len(hypotheses) != 98 or len(variables) != 122:
        raise RelationshipExecutionError("Contagens congeladas divergiram")
    return hypotheses, variables, hypotheses_payload["methodPresets"], parent_digest


def materialize_candidate(output_root: Path) -> dict[str, Any]:
    output_root.mkdir(parents=True, exist_ok=False)
    public_digest_before = directory_content_digest(PUBLIC_DATA_ROOT)
    with blocked_external_io_guard():
        hypotheses, variables, method_presets, parent_digest = load_frozen_program()
        aa1, job5i, source_quality = load_frozen_sources()
        frames, variable_audit = materialize_variables(variables, aa1, job5i)
        variable_lookup = {
            variable["variableId"]: variable for variable in variables
        }
        region_map = load_region_map()
        results: list[dict[str, Any]] = []
        robustness: list[dict[str, Any]] = []
        contexts: dict[str, dict[str, Any]] = {}
        for hypothesis in hypotheses:
            result, diagnostic = execute_hypothesis(
                hypothesis,
                frames=frames,
                variable_lookup=variable_lookup,
                method_presets=method_presets,
                region_map=region_map,
            )
            results.append(result)
            robustness.append(diagnostic)
            contexts[hypothesis["hypothesisId"]] = contextualize_hypothesis(
                hypothesis, frames=frames, region_map=region_map
            )
        finalize_multiplicity_and_promotions(results, contexts)
        lane_manifests: list[dict[str, Any]] = []
        for lane, expected_count in LANE_COUNTS.items():
            lane_results = [result for result in results if result["lane"] == lane]
            lane_hypothesis_ids = {
                result["hypothesisId"] for result in lane_results
            }
            lane_robustness = [
                record
                for record in robustness
                if record["hypothesisId"] in lane_hypothesis_ids
            ]
            if len(lane_results) != expected_count:
                raise RelationshipExecutionError(
                    f"Faixa {lane}: {len(lane_results)} != {expected_count}"
                )
            lane_manifests.append(
                write_lane_package(
                    output_root,
                    lane=lane,
                    results=lane_results,
                    robustness=lane_robustness,
                    variable_audit=variable_audit,
                    source_quality=source_quality,
                    parent_digest=parent_digest,
                    public_digest=public_digest_before,
                )
            )
        reconciliation_manifest = write_reconciliation_package(
            output_root,
            results=results,
            contexts=contexts,
            lane_manifests=lane_manifests,
            source_quality=source_quality,
            public_digest=public_digest_before,
        )
    public_digest_after = directory_content_digest(PUBLIC_DATA_ROOT)
    if public_digest_after != public_digest_before:
        raise RelationshipExecutionError("Executor alterou public/data")
    validate_results_output(output_root)
    return reconciliation_manifest


def validate_results_output(output_root: Path = DEFAULT_RESULTS_ROOT) -> dict[str, Any]:
    output_root = output_root.resolve()
    contract = read_json(EXECUTION_CONTRACT_PATH)
    required_fields = set(contract["resultContract"]["requiredFields"])
    all_results: list[dict[str, Any]] = []
    for lane, expected_count in LANE_COUNTS.items():
        lane_root = output_root / lane
        missing = [name for name in RESULT_FILES if not (lane_root / name).is_file()]
        if missing:
            raise RelationshipExecutionError(f"Faixa {lane} incompleta: {missing}")
        manifest = read_json(lane_root / "MANIFEST.json")
        if manifest["verifiedParentArtifactSetDigestSha256"] != EXPECTED_PARENT_DIGEST:
            raise RelationshipExecutionError(f"Faixa {lane} não verificou o freeze")
        if manifest["executionContractSha256"] != EXPECTED_EXECUTION_CONTRACT_SHA256:
            raise RelationshipExecutionError(f"Faixa {lane} usou contrato divergente")
        records = artifact_records(lane_root, RESULT_FILES[:-1])
        if records != manifest["artifacts"] or artifact_set_digest(records) != manifest[
            "artifactSetDigestSha256"
        ]:
            raise RelationshipExecutionError(f"Hashes divergentes na faixa {lane}")
        lane_results = read_json(lane_root / "RESULTS.json")
        if len(lane_results) != expected_count:
            raise RelationshipExecutionError(f"Contagem divergente na faixa {lane}")
        all_results.extend(lane_results)
    reconciliation_root = output_root / "reconciliation"
    missing = [
        name for name in COMBINED_FILES if not (reconciliation_root / name).is_file()
    ]
    if missing:
        raise RelationshipExecutionError(f"Reconciliação incompleta: {missing}")
    combined = read_json(reconciliation_root / "ALL_RESULTS.json")
    combined_by_id = {row["hypothesisId"]: row for row in combined}
    lane_by_id = {row["hypothesisId"]: row for row in all_results}
    if combined_by_id != lane_by_id:
        raise RelationshipExecutionError("Reconciliação diverge das três faixas")
    if len(combined) != 98 or len({row["hypothesisId"] for row in combined}) != 98:
        raise RelationshipExecutionError("Resultado não contém 98 hipóteses únicas")
    for row in combined:
        missing_fields = sorted(required_fields - set(row))
        if missing_fields:
            raise RelationshipExecutionError(
                f"{row['hypothesisId']} sem campos: {missing_fields}"
            )
        if row["causalClaimAllowed"] is not False:
            raise RelationshipExecutionError("Resultado causal indevido")
        if row["status"] == "ESTIMATED_PENDING_MULTIPLICITY":
            raise RelationshipExecutionError("Multiplicidade não finalizada")
        if not 0 <= float(row["pValueForMultiplicity"]) <= 1:
            raise RelationshipExecutionError("p para multiplicidade inválido")
        if not 0 <= float(row["qValueFamily"]) <= 1 or not 0 <= float(
            row["qValueGlobal"]
        ) <= 1:
            raise RelationshipExecutionError("q-valor inválido")
    manifest = read_json(reconciliation_root / "MANIFEST.json")
    records = artifact_records(reconciliation_root, COMBINED_FILES[:-1])
    if records != manifest["artifacts"] or artifact_set_digest(records) != manifest[
        "artifactSetDigestSha256"
    ]:
        raise RelationshipExecutionError("Hashes divergentes na reconciliação")
    if manifest["executionContractSha256"] != EXPECTED_EXECUTION_CONTRACT_SHA256:
        raise RelationshipExecutionError("Reconciliação usou contrato divergente")
    if directory_content_digest(PUBLIC_DATA_ROOT) != manifest[
        "publicDataTreeDigestBeforeAndAfter"
    ]:
        raise RelationshipExecutionError("public/data mudou após a execução")
    return manifest


def materialize_twice_transactionally(
    output_root: Path = DEFAULT_RESULTS_ROOT,
) -> dict[str, Any]:
    output_root = output_root.resolve()
    expected_parent = (REPO_ROOT / ".tmp/vocacoes-pne/relationship-atlas-v1").resolve()
    if output_root.parent != expected_parent:
        raise RelationshipExecutionError(
            f"Raiz de resultados fora do diretório controlado: {output_root}"
        )
    output_root.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="relationship-atlas-execution-", dir=output_root.parent
    ) as temporary:
        temporary_root = Path(temporary)
        first = temporary_root / "first"
        second = temporary_root / "second"
        first_manifest = materialize_candidate(first)
        second_manifest = materialize_candidate(second)
        first_digest = directory_content_digest(first)
        second_digest = directory_content_digest(second)
        if first_digest != second_digest:
            raise RelationshipExecutionError(
                "Duas execuções independentes produziram resultados diferentes"
            )
        if output_root.exists():
            try:
                existing_manifest = validate_results_output(output_root)
                if directory_content_digest(output_root) == first_digest:
                    return existing_manifest
            except RelationshipExecutionError:
                pass
            backup = output_root.parent / f".{output_root.name}.rollback"
            if backup.exists():
                raise RelationshipExecutionError(f"Rollback preexistente recusado: {backup}")
            os.replace(output_root, backup)
            try:
                shutil.move(str(first), str(output_root))
                promoted = validate_results_output(output_root)
            except Exception:
                if output_root.exists():
                    shutil.rmtree(output_root)
                os.replace(backup, output_root)
                raise
            shutil.rmtree(backup)
            return promoted
        shutil.move(str(first), str(output_root))
    return validate_results_output(output_root)


__all__ = [
    "DEFAULT_RESULTS_ROOT",
    "RelationshipExecutionError",
    "bh_adjust",
    "materialize_candidate",
    "materialize_twice_transactionally",
    "validate_results_output",
]
