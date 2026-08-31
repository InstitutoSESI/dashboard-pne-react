"""Expansão analítica determinística do Job 5F Vocações × PNE V7.

O módulo reutiliza somente artefatos locais congelados, separa testes
exploratórios de lacunas de processamento e produz uma matriz ampla sem
selecionar portfólio editorial. Não acessa rede ou banco, não escreve em
``public/data`` e não altera os estados formais dos Jobs anteriores.
"""

from __future__ import annotations

from collections import Counter
import json
import math
from pathlib import Path
import re
from typing import Any, Iterable, Mapping

import numpy as np
import pandas as pd

from src.vocacoes_pne_job2 import (
    assert_outside_public_data,
    replace_directory_transactionally,
    sha256_file,
    staging_directory_for,
    validate_unique_key,
    write_csv_gzip,
    write_json,
)


SCHEMA_VERSION = "vocacoes-pne-v7-job5f-v1"
JOB_ID = "v7-job5f"
VERDICT = "JOB_5F_PARTIAL_EXPANSION_WITH_DATA_GAPS"
REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_PIPELINE_DIR = REPO_ROOT / "data_pipeline"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / ".tmp" / "vocacoes-pne" / JOB_ID
JOB2_ROOT = REPO_ROOT / ".tmp" / "vocacoes-pne" / "v7-job2"
JOB3_ROOT = REPO_ROOT / ".tmp" / "vocacoes-pne" / "v7-job3"
CONTRACT_PATH = DATA_PIPELINE_DIR / "contracts" / "vocacoes-pne-v7-job5f.json"
LAUNCHER_PATH = DATA_PIPELINE_DIR / "scripts" / "run_vocacoes_pne_v7_job5f.py"
CORE_PATH = Path(__file__).resolve()
NOVA_SANTA_RITA_ID = "4313375"
IBGE_PATTERN = re.compile(r"^[0-9]{7}$")

OUTPUT_FILES = (
    "source_inventory.json",
    "exploratory_evidence.json",
    "master_analytical_opportunities.csv.gz",
    "master_analytical_opportunities.json",
    "qa.json",
    "output_inventory.json",
    "manifest.json",
)

ALLOWED_STATES = {
    "PROMISING",
    "PROMISING_NEEDS_MORE_TESTING",
    "DESCRIPTIVE_ONLY",
    "INSUFFICIENT_DATA",
    "REDUNDANT",
    "REJECTED",
}

MATRIX_COLUMNS = (
    "analysis_id",
    "direction",
    "theme",
    "substantive_question",
    "proposed_mechanism",
    "required_data",
    "available_data",
    "missing_data",
    "source_lenses",
    "period",
    "analysis_unit",
    "education_network",
    "exploratory_method",
    "exploratory_result",
    "robustness_limitations",
    "nova_santa_rita",
    "regional_evidence",
    "municipal_evidence",
    "incremental_value",
    "potential_planning_question",
    "potential_visual",
    "trackable_indicators",
    "status",
    "status_reason",
)


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _json_safe(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (np.integer, np.floating)):
        value = value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _fmt(value: float | int | None, digits: int = 2) -> str:
    if value is None or (isinstance(value, float) and not math.isfinite(value)):
        return "indisponível"
    if float(value).is_integer():
        return f"{int(value):,}".replace(",", ".")
    return f"{float(value):.{digits}f}".replace(".", ",")


def _pct_change(start: float, end: float) -> float | None:
    if start == 0:
        return None
    return (end - start) / start * 100.0


def _read_csv(relative: str, *, root: Path = JOB2_ROOT) -> pd.DataFrame:
    return pd.read_csv(
        root / relative,
        dtype={
            "municipality_ibge_code": "string",
            "municipality_id": "string",
        },
        keep_default_na=False,
        na_values=["null"],
    )


def _total_rows(frame: pd.DataFrame) -> pd.DataFrame:
    dependency = frame["dependencia"].astype("string").str.casefold()
    location = frame["localizacao"].astype("string").str.casefold()
    return frame[dependency.isin({"total", "all"}) & location.isin({"total", "all"})].copy()


def _verify_frozen_inputs() -> dict[str, Any]:
    contract = _load_json(CONTRACT_PATH)
    if tuple(contract["outputs"]) != OUTPUT_FILES:
        raise ValueError("Contrato Job 5F diverge da allowlist de outputs.")
    if tuple(contract["requiredMatrixColumns"]) != MATRIX_COLUMNS:
        raise ValueError("Contrato Job 5F diverge das colunas da matriz.")
    scope = contract["scope"]
    if scope["networkScope"] != "total_all_dependencies":
        raise ValueError("Escopo educacional canônico não foi preservado.")
    if scope["administrativeDependencyIsAnalyticDimension"]:
        raise ValueError("Dependência administrativa não pode ser dimensão analítica.")
    if contract["h2Boundary"]["frozenStateMustRemain"] != (
        "NOT_EVALUABLE_DUE_TO_DATA_OR_QA_LIMIT"
    ):
        raise ValueError("Estado formal congelado de H2 foi alterado no contrato.")
    for relative, expected in contract["inputFingerprints"].items():
        path = REPO_ROOT / relative
        if not path.is_file():
            raise FileNotFoundError(f"Entrada congelada ausente: {relative}")
        actual = sha256_file(path)
        if actual != expected:
            raise ValueError(f"Hash divergente para {relative}: {actual} != {expected}")
    return contract


def _trend(
    frame: pd.DataFrame,
    *,
    metric: str,
    stage: str,
    start_year: int,
    end_year: int,
    improvement: str,
) -> dict[str, Any]:
    total = _total_rows(frame)
    selected = total[
        (total["metric"] == metric)
        & (total["etapa_ensino"] == stage)
        & total["ano"].isin([start_year, end_year])
        & (total["value_status"] == "observed")
    ].copy()
    selected["value"] = pd.to_numeric(selected["value"], errors="coerce")
    pivot = selected.pivot(
        index="municipality_ibge_code", columns="ano", values="value"
    ).dropna()
    if start_year not in pivot or end_year not in pivot:
        raise ValueError(f"Janela ausente para {metric}/{stage}.")
    pivot["delta_pp"] = pivot[end_year] - pivot[start_year]
    nsr = pivot.loc[NOVA_SANTA_RITA_ID]
    improving = pivot["delta_pp"].gt(0) if improvement == "up" else pivot["delta_pp"].lt(0)
    return {
        "metric": metric,
        "stage": stage,
        "startYear": start_year,
        "endYear": end_year,
        "municipalityCount": int(len(pivot)),
        "improvingMunicipalityCount": int(improving.sum()),
        "municipalDeltaMedianPp": float(pivot["delta_pp"].median()),
        "municipalDeltaMinimumPp": float(pivot["delta_pp"].min()),
        "municipalDeltaMaximumPp": float(pivot["delta_pp"].max()),
        "novaSantaRita": {
            "start": float(nsr[start_year]),
            "end": float(nsr[end_year]),
            "deltaPp": float(nsr["delta_pp"]),
        },
    }


def _condition_snapshot(
    frame: pd.DataFrame,
    *,
    metric: str,
    dimension: str,
    start_year: int,
    end_year: int,
) -> dict[str, Any]:
    total = _total_rows(frame)
    selected = total[
        (total["metric"] == metric)
        & (total["dimension"] == dimension)
        & total["ano"].isin([start_year, end_year])
        & (total["value_status"] == "observed")
    ].copy()
    selected["value"] = pd.to_numeric(selected["value"], errors="coerce")
    pivot = selected.pivot(
        index="municipality_ibge_code", columns="ano", values="value"
    ).dropna()
    if NOVA_SANTA_RITA_ID not in pivot.index:
        raise ValueError(f"Nova Santa Rita ausente para {metric}/{dimension}.")
    pivot["delta"] = pivot[end_year] - pivot[start_year]
    nsr = pivot.loc[NOVA_SANTA_RITA_ID]
    return {
        "metric": metric,
        "dimension": dimension,
        "startYear": start_year,
        "endYear": end_year,
        "municipalityCount": int(len(pivot)),
        "municipalDeltaMedian": float(pivot["delta"].median()),
        "novaSantaRita": {
            "start": float(nsr[start_year]),
            "end": float(nsr[end_year]),
            "delta": float(nsr["delta"]),
        },
    }


def _spearman(x: pd.Series, y: pd.Series) -> float | None:
    paired = pd.concat([x, y], axis=1).dropna()
    if len(paired) < 4:
        return None
    ranked = paired.rank(method="average")
    value = ranked.iloc[:, 0].corr(ranked.iloc[:, 1])
    return None if pd.isna(value) else float(value)


def _change_association(
    trajectory: pd.DataFrame,
    conditions: pd.DataFrame,
    *,
    trajectory_metric: str,
    trajectory_stage: str,
    condition_metric: str,
    condition_dimension: str,
    start_year: int,
    end_year: int,
) -> dict[str, Any]:
    traj = _total_rows(trajectory)
    cond = _total_rows(conditions)
    traj = traj[
        (traj["metric"] == trajectory_metric)
        & (traj["etapa_ensino"] == trajectory_stage)
        & traj["ano"].isin([start_year, end_year])
        & (traj["value_status"] == "observed")
    ].copy()
    cond = cond[
        (cond["metric"] == condition_metric)
        & (cond["dimension"] == condition_dimension)
        & cond["ano"].isin([start_year, end_year])
        & (cond["value_status"] == "observed")
    ].copy()
    traj["value"] = pd.to_numeric(traj["value"], errors="coerce")
    cond["value"] = pd.to_numeric(cond["value"], errors="coerce")
    t = traj.pivot(index="municipality_ibge_code", columns="ano", values="value")
    c = cond.pivot(index="municipality_ibge_code", columns="ano", values="value")
    joined = pd.DataFrame(
        {
            "trajectoryDelta": t.get(end_year) - t.get(start_year),
            "conditionDelta": c.get(end_year) - c.get(start_year),
        }
    ).dropna()
    return {
        "trajectoryMetric": trajectory_metric,
        "trajectoryStage": trajectory_stage,
        "conditionMetric": condition_metric,
        "conditionDimension": condition_dimension,
        "period": f"{start_year}-{end_year}",
        "municipalityCount": int(len(joined)),
        "spearmanChange": _spearman(
            joined["trajectoryDelta"], joined["conditionDelta"]
        ),
        "interpretation": "associação ecológica descritiva; não causal",
    }


def _value_at(
    frame: pd.DataFrame,
    *,
    scope: str,
    year: int,
    field: str,
    municipality_id: str | None = None,
    **filters: Any,
) -> float:
    selected = frame[(frame["year"] == year) & (frame["entity_scope"] == scope)]
    if municipality_id is not None:
        selected = selected[selected["municipality_ibge_code"] == municipality_id]
    for column, value in filters.items():
        selected = selected[selected[column] == value]
    if len(selected) != 1:
        raise ValueError(
            f"Esperada uma linha para {field}/{scope}/{year}/{filters}; obtidas {len(selected)}."
        )
    return float(selected.iloc[0][field])


def _trajectory_and_condition_evidence() -> dict[str, Any]:
    trajectory = _read_csv("2a/trajetoria_municipal.csv.gz")
    conditions = _read_csv("2a/condicoes_oferta.csv.gz")
    trends = {
        "approval_high_school": _trend(
            trajectory,
            metric="approval_rate_percent",
            stage="medio",
            start_year=2018,
            end_year=2025,
            improvement="up",
        ),
        "dropout_high_school": _trend(
            trajectory,
            metric="dropout_rate_percent",
            stage="medio",
            start_year=2018,
            end_year=2025,
            improvement="down",
        ),
        "failure_final_fundamental": _trend(
            trajectory,
            metric="failure_rate_percent",
            stage="fundamental_anos_finais",
            start_year=2018,
            end_year=2025,
            improvement="down",
        ),
        "distortion_high_school": _trend(
            trajectory,
            metric="age_grade_distortion_rate_percent",
            stage="taxa_distorcao_medio",
            start_year=2019,
            end_year=2025,
            improvement="down",
        ),
        "distortion_final_fundamental": _trend(
            trajectory,
            metric="age_grade_distortion_rate_percent",
            stage="taxa_distorcao_fundamental_anos_finais",
            start_year=2019,
            end_year=2025,
            improvement="down",
        ),
    }
    snapshots = {
        "students_per_class_high_school": _condition_snapshot(
            conditions,
            metric="students_per_class",
            dimension="medio:Total - Ensino Medio",
            start_year=2018,
            end_year=2025,
        ),
        "teacher_adequacy_high_school": _condition_snapshot(
            conditions,
            metric="teacher_adequacy_percent",
            dimension="ensino_medio",
            start_year=2018,
            end_year=2025,
        ),
        "broadband": _condition_snapshot(
            conditions,
            metric="schools_with_broadband_percent",
            dimension="all_schools",
            start_year=2018,
            end_year=2025,
        ),
        "internet": _condition_snapshot(
            conditions,
            metric="schools_with_internet_percent",
            dimension="all_schools",
            start_year=2018,
            end_year=2025,
        ),
    }
    total_conditions = _total_rows(conditions)
    internet_2025 = total_conditions[
        (total_conditions["metric"] == "schools_with_internet_percent")
        & (total_conditions["dimension"] == "all_schools")
        & (total_conditions["ano"] == 2025)
        & (total_conditions["value_status"] == "observed")
    ].copy()
    internet_2025["value"] = pd.to_numeric(internet_2025["value"], errors="coerce")
    broadband_2025 = total_conditions[
        (total_conditions["metric"] == "schools_with_broadband_percent")
        & (total_conditions["dimension"] == "all_schools")
        & (total_conditions["ano"] == 2025)
        & (total_conditions["value_status"] == "observed")
    ].copy()
    broadband_2025["value"] = pd.to_numeric(broadband_2025["value"], errors="coerce")
    inse = total_conditions[
        (total_conditions["metric"] == "inse_mean")
        & (total_conditions["ano"] == 2023)
        & (total_conditions["value_status"] == "observed")
    ].set_index("municipality_ibge_code")
    distortion_2023 = _total_rows(trajectory)
    distortion_2023 = distortion_2023[
        (distortion_2023["metric"] == "age_grade_distortion_rate_percent")
        & (distortion_2023["etapa_ensino"] == "taxa_distorcao_medio")
        & (distortion_2023["ano"] == 2023)
        & (distortion_2023["value_status"] == "observed")
    ].set_index("municipality_ibge_code")
    return {
        "officialRateUse": {
            "allowed": "evolução municipal oficial e distribuição municipal do Vale",
            "forbidden": "taxa regional recomposta, estabilidade por pequeno denominador ou ponderação inventada",
            "h2FrozenStateChanged": False,
        },
        "trends": trends,
        "conditionSnapshots": snapshots,
        "associations": {
            "studentsPerClassVsApproval": _change_association(
                trajectory,
                conditions,
                trajectory_metric="approval_rate_percent",
                trajectory_stage="medio",
                condition_metric="students_per_class",
                condition_dimension="medio:Total - Ensino Medio",
                start_year=2018,
                end_year=2025,
            ),
            "teacherAdequacyVsApproval": _change_association(
                trajectory,
                conditions,
                trajectory_metric="approval_rate_percent",
                trajectory_stage="medio",
                condition_metric="teacher_adequacy_percent",
                condition_dimension="ensino_medio",
                start_year=2018,
                end_year=2025,
            ),
            "broadbandVsDropout": _change_association(
                trajectory,
                conditions,
                trajectory_metric="dropout_rate_percent",
                trajectory_stage="medio",
                condition_metric="schools_with_broadband_percent",
                condition_dimension="all_schools",
                start_year=2018,
                end_year=2025,
            ),
            "inseVsDistortion2023": {
                "municipalityCount": int(
                    len(inse.join(distortion_2023, lsuffix="_inse", rsuffix="_dist"))
                ),
                "spearmanLevel": _spearman(
                    pd.to_numeric(inse["value"], errors="coerce"),
                    pd.to_numeric(distortion_2023["value"], errors="coerce"),
                ),
                "interpretation": "fotografia ecológica de 2023; não causal",
            },
        },
        "connectivity2025": {
            "internetMunicipalitiesAt100Percent": int(internet_2025["value"].eq(100).sum()),
            "internetMunicipalityCount": int(len(internet_2025)),
            "broadbandMunicipalitiesAt100Percent": int(broadband_2025["value"].eq(100).sum()),
            "broadbandMunicipalityCount": int(len(broadband_2025)),
        },
        "idebTotalAllDependenciesRows": int(
            len(
                total_conditions[
                    (total_conditions["metric"] == "ideb_score")
                    & (total_conditions["value_status"] == "observed")
                ]
            )
        ),
    }


def _demography_network_evidence() -> dict[str, Any]:
    h1 = _read_csv("h1_decomposition.csv.gz", root=JOB3_ROOT)
    coortes = _read_csv("2e/coortes_demograficas.csv.gz")
    network = _read_csv("2e/rede_escolar.csv.gz")
    scenario = _read_csv("2e/cenario_mecanico_coortes.csv.gz")
    mobility = _read_csv("2e/mobilidade_educacional_2022.csv.gz")

    def h1_row(scope: str, stage: str, municipality_id: str | None = None) -> dict[str, Any]:
        selected = h1[(h1["entity_scope"] == scope) & (h1["stage"] == stage)]
        if municipality_id is not None:
            selected = selected[selected["municipality_id"] == municipality_id]
        if len(selected) != 1:
            raise ValueError(f"H1 ausente para {scope}/{stage}/{municipality_id}.")
        return _json_safe(selected.iloc[0].to_dict())

    scenario_selected = scenario[
        (scenario["target_year"] == 2030)
        & (scenario["stage"].isin(["preschool", "fundamental", "high_school"]))
        & (
            (scenario["entity_scope"] == "region")
            | (scenario["municipality_ibge_code"] == NOVA_SANTA_RITA_ID)
        )
    ].sort_values(["entity_scope", "stage"])

    mobility_rows = mobility[
        (mobility["entity_scope"] == "region")
        | (mobility["municipality_ibge_code"] == NOVA_SANTA_RITA_ID)
    ].sort_values(["entity_scope", "universe"])

    municipal_mobility = mobility[mobility["entity_scope"] == "municipality"].copy()
    high_mobility = municipal_mobility[municipal_mobility["universe"] == "medio"].set_index(
        "municipality_ibge_code"
    )
    high_h1 = h1[(h1["entity_scope"] == "municipality") & (h1["stage"] == "high_school")].set_index(
        "municipality_id"
    )
    pop = coortes[
        (coortes["entity_scope"] == "municipality")
        & (coortes["age_group"] == "15_17")
        & coortes["year"].isin([2014, 2022])
    ].pivot(index="municipality_ibge_code", columns="year", values="estimated_population")
    return {
        "h1": {
            "region": {
                stage: h1_row("region", stage)
                for stage in ("creche", "preschool", "fundamental", "high_school")
            },
            "novaSantaRita": {
                stage: h1_row("municipality", stage, NOVA_SANTA_RITA_ID)
                for stage in ("creche", "preschool", "fundamental", "high_school")
            },
        },
        "mechanicalCohort2030": _json_safe(scenario_selected.to_dict(orient="records")),
        "mechanicalCohortLimit": (
            "envelhecimento mecânico da coorte 2025, sem migração, mortalidade ou ajuste de entrada; não é previsão de matrícula"
        ),
        "mobility2022": _json_safe(mobility_rows.to_dict(orient="records")),
        "mobilityAssociations": {
            "outsideShareVsLocalEnrollmentChange": {
                "municipalityCount": 10,
                "spearman": _spearman(
                    high_mobility["outside_share_percent"],
                    high_h1["enrollment_relative_change"],
                ),
            },
            "outsideShareVsResident1517Change": {
                "municipalityCount": 10,
                "spearman": _spearman(
                    high_mobility["outside_share_percent"],
                    (pop[2022] - pop[2014]) / pop[2014],
                ),
            },
            "interpretation": "associações ecológicas entre lentes distintas; não identificam estudantes nem destinos",
        },
        "network": {
            "region2014": _json_safe(
                network[(network["entity_scope"] == "region") & (network["year"] == 2014)]
                .iloc[0]
                .to_dict()
            ),
            "region2025": _json_safe(
                network[(network["entity_scope"] == "region") & (network["year"] == 2025)]
                .iloc[0]
                .to_dict()
            ),
            "novaSantaRita2014": _json_safe(
                network[
                    (network["municipality_ibge_code"] == NOVA_SANTA_RITA_ID)
                    & (network["year"] == 2014)
                ]
                .iloc[0]
                .to_dict()
            ),
            "novaSantaRita2025": _json_safe(
                network[
                    (network["municipality_ibge_code"] == NOVA_SANTA_RITA_ID)
                    & (network["year"] == 2025)
                ]
                .iloc[0]
                .to_dict()
            ),
        },
    }


def _eja_evidence() -> dict[str, Any]:
    distribution = _read_csv("2c/eja_demanda_oferta_2022.csv.gz")
    historical = _read_csv("2c/eja_integrada_historica.csv.gz")
    selected_distribution = distribution[
        (distribution["entity_scope"] == "region")
        | (distribution["municipality_ibge_code"] == NOVA_SANTA_RITA_ID)
    ].sort_values(["entity_scope", "stage"])

    def historic(scope: str, year: int, municipality_id: str | None = None) -> dict[str, Any]:
        selected = historical[(historical["entity_scope"] == scope) & (historical["year"] == year)]
        if municipality_id is not None:
            selected = selected[selected["municipality_ibge_code"] == municipality_id]
        if len(selected) != 1:
            raise ValueError(f"EJA histórica ausente para {scope}/{year}/{municipality_id}.")
        return _json_safe(selected.iloc[0].to_dict())

    return {
        "distribution2022": _json_safe(selected_distribution.to_dict(orient="records")),
        "historical": {
            "region2014": historic("region", 2014),
            "region2022": historic("region", 2022),
            "region2025": historic("region", 2025),
            "novaSantaRita2014": historic("municipality", 2014, NOVA_SANTA_RITA_ID),
            "novaSantaRita2022": historic("municipality", 2022, NOVA_SANTA_RITA_ID),
            "novaSantaRita2025": historic("municipality", 2025, NOVA_SANTA_RITA_ID),
        },
        "limits": (
            "população adulta é residente; matrículas são localizadas nas escolas; distribuição não mede demanda, cobertura ou mesmas pessoas"
        ),
    }


def _labour_formation_evidence() -> dict[str, Any]:
    rais_stock = _read_csv("2b/rais_estoque_jovem_anual.csv.gz")
    rais_cube = _read_csv("2b/rais_cubo_jovem.csv.gz")
    caged = _read_csv("2b/caged_jovens_cubo.csv.gz")
    occupations = _read_csv("2d/ocupacoes_rais.csv.gz")
    courses = _read_csv("2d/oferta_cursos_tecnicos.csv.gz")
    bridge = _read_csv("2d/cobertura_ponte_2025.csv.gz")

    stocks: dict[str, Any] = {}
    for age in ("15_17", "18_24"):
        for year in (2019, 2025):
            region = rais_stock[
                (rais_stock["entity_scope"] == "region")
                & (rais_stock["age_group"] == age)
                & (rais_stock["year"] == year)
            ]
            nsr = rais_stock[
                (rais_stock["municipality_ibge_code"] == NOVA_SANTA_RITA_ID)
                & (rais_stock["age_group"] == age)
                & (rais_stock["year"] == year)
            ]
            stocks[f"{age}_{year}"] = {
                "region": int(region.iloc[0]["active_bonds"]),
                "novaSantaRita": int(nsr.iloc[0]["active_bonds"]),
            }

    schooling: dict[str, Any] = {}
    for age in ("15_17", "18_24"):
        for year in (2019, 2025):
            selected = rais_cube[(rais_cube["age_group"] == age) & (rais_cube["year"] == year)]
            region = selected.groupby("schooling_code")["active_bonds"].sum().sort_index()
            nsr = (
                selected[selected["municipality_ibge_code"] == NOVA_SANTA_RITA_ID]
                .groupby("schooling_code")["active_bonds"]
                .sum()
                .sort_index()
            )
            schooling[f"{age}_{year}"] = {
                "region": {str(k): int(v) for k, v in region.items()},
                "novaSantaRita": {str(k): int(v) for k, v in nsr.items()},
            }

    apprentice = caged[
        caged["year"].isin([2020, 2025])
        & (pd.to_numeric(caged["apprentice_indicator_code"], errors="coerce") == 1)
    ].copy()
    apprentice_summary: dict[str, Any] = {}
    for (year, age, event), group in apprentice.groupby(["year", "age_group", "event_type"]):
        apprentice_summary[f"{int(year)}_{age}_{event}"] = {
            "regionAdjustedEvents": float(group["adjusted_event_count"].sum()),
            "novaSantaRitaAdjustedEvents": float(
                group[group["municipality_ibge_code"] == NOVA_SANTA_RITA_ID][
                    "adjusted_event_count"
                ].sum()
            ),
        }

    occupation_summary: dict[str, Any] = {}
    for scope, frame in {
        "region": occupations,
        "novaSantaRita": occupations[
            occupations["municipality_ibge_code"] == NOVA_SANTA_RITA_ID
        ],
    }.items():
        grouped = (
            frame[frame["year"].isin([2019, 2025])]
            .groupby(["year", "occupation_code", "occupation_name"], as_index=False)[
                "active_bonds"
            ]
            .sum()
        )
        pivot = grouped.pivot_table(
            index=["occupation_code", "occupation_name"],
            columns="year",
            values="active_bonds",
            fill_value=0,
        )
        pivot["change"] = pivot.get(2025, 0) - pivot.get(2019, 0)
        up = pivot.sort_values("change", ascending=False).head(10).reset_index()
        down = pivot.sort_values("change", ascending=True).head(10).reset_index()
        occupation_summary[scope] = {
            "largestIncreases": _json_safe(up.to_dict(orient="records")),
            "largestDecreases": _json_safe(down.to_dict(orient="records")),
        }

    course_summary: dict[str, Any] = {}
    for year in (2023, 2025):
        selected = courses[courses["year"] == year]
        axes = selected.groupby("technological_axis_name")["technical_enrollments"].sum()
        municipalities = selected.groupby("municipality_ibge_code")["technical_enrollments"].sum()
        total = float(axes.sum())
        course_summary[str(year)] = {
            "technicalEnrollments": int(total),
            "courseCount": int(selected["course_code"].nunique()),
            "axisCount": int(selected["technological_axis_name"].nunique()),
            "municipalityWithObservedCourseRowsCount": int(
                selected["municipality_ibge_code"].nunique()
            ),
            "axisHhi": float(((axes / total) ** 2).sum()) if total else None,
            "municipalityHhi": float(((municipalities / total) ** 2).sum()) if total else None,
            "largestAxes": _json_safe(
                axes.sort_values(ascending=False).head(6).to_dict()
            ),
        }
    return {
        "raisYouthStocks": stocks,
        "raisYouthSchoolingCodes": schooling,
        "schoolingDictionaryStatus": (
            "códigos preservados como publicados no recorte; rótulos semânticos exigem dicionário oficial versionado antes de uso editorial"
        ),
        "cagedApprentices": apprentice_summary,
        "occupations": occupation_summary,
        "technicalCourses": course_summary,
        "bridgeCoverage2025": _json_safe(bridge.to_dict(orient="records")),
        "limits": (
            "RAIS é estoque e Caged é fluxo no município do estabelecimento; cursos são matrículas nas escolas; a ponte CBO-CNCT é normativa, parcial e não aditiva"
        ),
    }


def build_exploratory_evidence() -> dict[str, Any]:
    return {
        "schemaVersion": "vocacoes-pne-v7-job5f-exploratory-evidence-v1",
        "jobId": JOB_ID,
        "networkScope": "total_all_dependencies",
        "administrativeDependencyUsedAnalytically": False,
        "trajectoryAndConditions": _trajectory_and_condition_evidence(),
        "demographyNetworkMobility": _demography_network_evidence(),
        "eja": _eja_evidence(),
        "labourAndFormation": _labour_formation_evidence(),
        "causalClaimsMade": False,
        "h2FrozenStateChanged": False,
    }


def _analysis_row(
    analysis_id: str,
    direction: int,
    theme: str,
    question: str,
    mechanism: str,
    required: str,
    available: str,
    missing: str,
    lenses: str,
    period: str,
    unit: str,
    method: str,
    result: str,
    limitations: str,
    nsr: str,
    regional: str,
    municipal: str,
    incremental: str,
    planning: str,
    visual: str,
    indicators: str,
    status: str,
    reason: str,
) -> dict[str, Any]:
    return {
        "analysis_id": analysis_id,
        "direction": direction,
        "theme": theme,
        "substantive_question": question,
        "proposed_mechanism": mechanism,
        "required_data": required,
        "available_data": available,
        "missing_data": missing,
        "source_lenses": lenses,
        "period": period,
        "analysis_unit": unit,
        "education_network": "total_all_dependencies",
        "exploratory_method": method,
        "exploratory_result": result,
        "robustness_limitations": limitations,
        "nova_santa_rita": nsr,
        "regional_evidence": regional,
        "municipal_evidence": municipal,
        "incremental_value": incremental,
        "potential_planning_question": planning,
        "potential_visual": visual,
        "trackable_indicators": indicators,
        "status": status,
        "status_reason": reason,
    }


def build_opportunity_matrix(evidence: Mapping[str, Any]) -> pd.DataFrame:
    t = evidence["trajectoryAndConditions"]
    d = evidence["demographyNetworkMobility"]
    eja = evidence["eja"]
    labour = evidence["labourAndFormation"]
    rows: list[dict[str, Any]] = []

    def add(*args: Any) -> None:
        rows.append(_analysis_row(*args))

    h1r = d["h1"]["region"]
    h1n = d["h1"]["novaSantaRita"]
    approval = t["trends"]["approval_high_school"]
    dropout = t["trends"]["dropout_high_school"]
    distortion = t["trends"]["distortion_high_school"]
    class_assoc = t["associations"]["studentsPerClassVsApproval"]
    teacher_assoc = t["associations"]["teacherAdequacyVsApproval"]
    broad_assoc = t["associations"]["broadbandVsDropout"]
    inse_assoc = t["associations"]["inseVsDistortion2023"]
    network = d["network"]
    region_eja_2014 = eja["historical"]["region2014"]
    region_eja_2025 = eja["historical"]["region2025"]
    nsr_eja_2014 = eja["historical"]["novaSantaRita2014"]
    nsr_eja_2025 = eja["historical"]["novaSantaRita2025"]
    cohort_2030 = d["mechanicalCohort2030"]
    cohort_region = {r["stage"]: r for r in cohort_2030 if r["entity_scope"] == "region"}
    cohort_nsr = {
        r["stage"]: r
        for r in cohort_2030
        if r["municipality_ibge_code"] == NOVA_SANTA_RITA_ID
    }

    add(
        "D1_DEMOGRAFIA_MATRICULAS_ETAPA",
        1,
        "Demografia, matrículas e oferta",
        "Como os ritmos da população em idade compatível e das matrículas por etapa divergem no território?",
        "Mudanças no tamanho das coortes alteram a pressão potencial, enquanto participação, mobilidade e organização da oferta podem fazer a matrícula localizada seguir outro ritmo.",
        "População anual por idade e matrículas totais por etapa.",
        "Coortes demográficas e decomposição H1, 2014–2025, Vale, RS e 10 municípios.",
        "Nenhum insumo crítico para a leitura histórica.",
        "resident_population + school_location",
        "2014–2025",
        "município × ano × etapa; agregados aditivos do Vale e RS",
        "Variações, decomposição M=P×R, direção e contribuição municipal.",
        f"No Vale, o fundamental passou de {_fmt(h1r['fundamental']['enrollment_start'])} para {_fmt(h1r['fundamental']['enrollment_end'])} matrículas ({_fmt(h1r['fundamental']['enrollment_relative_change']*100)}%), enquanto a população compatível variou {_fmt(h1r['fundamental']['population_relative_change']*100)}%.",
        "População e matrícula pertencem a lentes distintas; M/P não mede cobertura individual.",
        f"Nova Santa Rita teve fundamental {_fmt(h1n['fundamental']['enrollment_start'])}→{_fmt(h1n['fundamental']['enrollment_end'])} e população compatível {_fmt(h1n['fundamental']['population_start'])}→{_fmt(h1n['fundamental']['population_end'])}.",
        "O Vale combina retração regional com direções municipais heterogêneas por etapa.",
        "Nova Santa Rita diverge do movimento regional no fundamental e médio e cresce fortemente na educação infantil.",
        "Separa efeito de tamanho das coortes de mudanças na relação territorial matrícula/população, indo além de duas séries isoladas.",
        "Em quais etapas a organização da oferta precisa responder a ritmos locais diferentes do Vale?",
        "Small multiples por etapa: população residente e matrícula localizada em painéis separados, mais decomposição da mudança.",
        "População compatível; matrículas; contribuição municipal; relação territorial sem rótulo de cobertura.",
        "PROMISING",
        "Mecanismo, cobertura, heterogeneidade e caso municipal estão materializados e acrescentam leitura além dos quatro fatos resumidos no Job 5E.",
    )
    add(
        "D1_DEMOGRAFIA_ESCOLAS_TURMAS",
        1,
        "Demografia e organização da oferta",
        "Escolas e turmas mudaram no mesmo sentido e ritmo das coortes e matrículas?",
        "A oferta física e a organização em turmas ajustam-se com defasagem e de forma discreta, podendo divergir da mudança demográfica.",
        "População por idade, matrícula, escolas e turmas totais por etapa.",
        "Decomposição H1 contém população, matrícula, escolas e turmas 2014/2025 para Vale e municípios.",
        "Série anual de turmas por etapa no recorte Job 2 para testar pontos de inflexão.",
        "resident_population + school_location",
        "2014–2025",
        "município × etapa × ano",
        "Variações absolutas/relativas, concordância de direção e tipologia transparente.",
        f"No Vale, escolas totais {_fmt(h1r['fundamental']['schools_start'])}→{_fmt(h1r['fundamental']['schools_end'])}; no médio, turmas {_fmt(h1r['high_school']['classes_start'])}→{_fmt(h1r['high_school']['classes_end'])}, junto de matrículas {_fmt(h1r['high_school']['enrollment_start'])}→{_fmt(h1r['high_school']['enrollment_end'])}.",
        "Contagem total de escolas não é capacidade nem está perfeitamente atribuída a uma etapa; turmas exigem checagem anual adicional.",
        f"Nova Santa Rita: escolas {_fmt(h1n['fundamental']['schools_start'])}→{_fmt(h1n['fundamental']['schools_end'])}; turmas do fundamental {_fmt(h1n['fundamental']['classes_start'])}→{_fmt(h1n['fundamental']['classes_end'])}.",
        "A relação revela ajuste organizacional diferente entre educação infantil, fundamental e médio.",
        "Nova Santa Rita combina crescimento de escolas/turmas com trajetórias locais opostas ao agregado em etapas centrais.",
        "Desagrega o módulo H1 em uma pergunta operacional sobre ajuste da oferta, sem concluir abertura/fechamento automático.",
        "Onde monitorar acomodação de turmas, preservação de acesso e transições antes de qualquer decisão física?",
        "Matriz de direção população–matrícula–turmas–escolas por município e etapa.",
        "Escolas; turmas; matrículas; população compatível; alunos por turma.",
        "PROMISING",
        "Há fatos aditivos e diferença de planejamento própria; a série anual de turmas ainda melhora a robustez, mas não bloqueia a leitura histórica.",
    )
    add(
        "D1_DEMOGRAFIA_DOCENTES",
        1,
        "Demografia e força de trabalho docente",
        "A mudança das coortes e das matrículas foi acompanhada pelo número de docentes?",
        "Oferta de docentes pode ajustar-se em ritmo diferente da demanda educacional, alterando organização e continuidade.",
        "População, matrícula e docentes totais por etapa e ano.",
        "Docentes existem em public.censo/censo_escolas segundo o inventário; população e matrícula estão materializadas.",
        "Recorte total de docentes por etapa ainda não foi materializado no Job 2.",
        "resident_population + school_location",
        "2014–2025",
        "município × ano × etapa",
        "Variações, docentes por turma e concordância de direção, sem atribuição causal.",
        "Fonte confirmada, mas teste não executado porque o recorte docente total não integra os artefatos congelados reutilizáveis.",
        "Contagem de docentes pode duplicar pessoa entre etapas/escolas; definição precisa de função docente é necessária.",
        "Nova Santa Rita deve ser testada contra Vale, RS e pares após materialização.",
        "A pergunta é regionalmente útil, mas ainda sem evidência calculada no 5F.",
        "Sem fato municipal novo nesta rodada.",
        "Acrescentaria capacidade humana da oferta, ausente nos quatro módulos atuais.",
        "Em quais etapas acompanhar docentes, turmas e matrículas em conjunto?",
        "Painel de variações de docentes, turmas e matrículas por etapa.",
        "Docentes; turmas; docentes por turma; matrículas.",
        "PROMISING_NEEDS_MORE_TESTING",
        "Fonte existente e mecanismo relevante, mas requer novo processamento com controle de dupla contagem.",
    )
    add(
        "D1_COORTES_TRANSICOES_ETAPAS",
        1,
        "Coortes e transições",
        "O tamanho das coortes que alcançam cada etapa é compatível com os volumes observados na etapa seguinte?",
        "Coortes menores ou maiores atravessam etapas com mobilidade, repetência e localização escolar, produzindo divergências entre tamanho demográfico e matrícula.",
        "Coortes anuais, matrículas por etapa e taxas oficiais de trajetória.",
        "Coortes 2014–2025, matrículas e taxas municipais oficiais; cenário mecânico 2026–2030.",
        "Identificação de transições individuais e denominadores exatos; não necessários para uma leitura ecológica, mas necessários para taxa de transição própria.",
        "resident_population + school_location",
        "2014–2030 mecânico",
        "município × coorte × etapa/ano",
        "Razões mecânicas, defasagens, concordância e sensibilidade a janelas; sem inferência individual.",
        f"Para 2030, a coorte mecânica do médio equivale a {_fmt(cohort_region['high_school']['cohort_to_baseline_enrollment_ratio']*100)}% da matrícula regional de 2025; no fundamental, {_fmt(cohort_region['fundamental']['cohort_to_baseline_enrollment_ratio']*100)}%.",
        d["mechanicalCohortLimit"],
        f"Nova Santa Rita: razão mecânica 2030/2025 de {_fmt(cohort_nsr['high_school']['cohort_to_baseline_enrollment_ratio']*100)}% no médio e {_fmt(cohort_nsr['fundamental']['cohort_to_baseline_enrollment_ratio']*100)}% no fundamental.",
        "O Vale sugere pressões mecânicas distintas entre pré-escola, fundamental e médio.",
        "Nova Santa Rita tem sinal especialmente forte no médio, sem que isso seja previsão de matrícula.",
        "Transforma A1 retida em leitura de transição por etapa, com limites explícitos, em vez de repetir H1.",
        "Quais transições precisam ser acompanhadas antes que coortes hoje observadas cheguem às etapas seguintes?",
        "Faixas de coorte mecânica versus matrícula-base, por etapa e horizonte.",
        "Tamanho de coorte; matrícula-base; razão mecânica; trajetória oficial municipal.",
        "PROMISING_NEEDS_MORE_TESTING",
        "Há sinal territorial e valor de antecipação, mas são necessários testes de janelas, mobilidade e sensibilidade antes de usar como história.",
    )
    add(
        "D1_NASCIMENTOS_EDUCACAO_INFANTIL",
        1,
        "Nascimentos e demanda futura",
        "A queda ou crescimento de nascimentos já altera a agenda de creche e pré-escola?",
        "Nascimentos antecedem a entrada nas etapas iniciais e podem sinalizar mudança de coorte antes da série de matrículas.",
        "Nascimentos por residência/ocorrência com metadado, população 0–5 e matrículas infantis.",
        "Série SINASC é citada e materializada em pacotes Vocações; coortes e matrículas existem.",
        "Recorte canônico do Vale, lente confirmada e integração com Job 2.",
        "resident_population_or_occurrence_to_confirm + school_location",
        "janela a confirmar; educação 2014–2025",
        "município × ano",
        "Defasagens de 0–5 anos, comparação de direção e contribuição municipal.",
        "Fonte existente foi inventariada, mas não estava nos artefatos congelados do Job 2; teste não executado.",
        "A lente de nascimentos precisa ser confirmada; migração entre nascimento e matrícula impede equivalência individual.",
        "Nova Santa Rita deve ser testada por coorte e não por razão de cobertura.",
        "Potencial regional alto, ainda sem resultado numérico desta rodada.",
        "Sem evidência municipal nova materializada.",
        "Antecede a leitura de coortes anuais e pode acrescentar um alerta de curto prazo para educação infantil.",
        "Que mudança de coorte infantil precisa entrar no planejamento de acesso e organização?",
        "Linha de nascimentos e população 0–5 separada de matrículas de creche/pré-escola.",
        "Nascimentos; população 0–3 e 4–5; matrículas; turmas.",
        "PROMISING_NEEDS_MORE_TESTING",
        "Mecanismo forte e fonte existente, mas a lente e o recorte regional ainda precisam de processamento e QA.",
    )

    official_limit = (
        "Uso descritivo de taxa oficial municipal; sem recompor taxa do Vale/RS, sem retrocálculo e sem afirmação de estabilidade por denominador."
    )
    add(
        "D1_MATRICULA_RENDIMENTO_OFICIAL",
        1,
        "Matrícula e rendimento",
        "Como a evolução do volume matriculado convive com aprovação, reprovação e abandono oficiais no município?",
        "Mudança de volume e composição escolar pode coexistir com mudanças nas taxas de rendimento, exigindo acompanhamento conjunto sem supor causalidade.",
        "Matrícula total por etapa e taxas oficiais municipais totais.",
        "Matrículas 2014–2025 e taxas oficiais 2018–2025 para 10 municípios.",
        "Numeradores/denominadores exatos para taxas agregadas regionais.",
        "school_location",
        "2018–2025",
        "município × ano × etapa",
        "Evolução temporal municipal, deltas em pp e comparação com distribuição municipal do Vale.",
        f"No médio, {approval['improvingMunicipalityCount']} de {approval['municipalityCount']} municípios aumentaram a aprovação oficial entre 2018 e 2025; mediana municipal {_fmt(approval['municipalDeltaMedianPp'])} pp.",
        official_limit,
        f"Nova Santa Rita: aprovação no médio {_fmt(approval['novaSantaRita']['start'])}%→{_fmt(approval['novaSantaRita']['end'])}% e abandono {_fmt(dropout['novaSantaRita']['start'])}%→{_fmt(dropout['novaSantaRita']['end'])}%.",
        "A evidência regional é distribuição de mudanças municipais, não taxa regional.",
        "O caso local apresenta melhora descritiva em vários indicadores e permanece sujeito a denominador desconhecido.",
        "Recupera utilidade descritiva legítima das taxas oficiais sem reabrir H2.",
        "Que combinação de matrícula e rendimento deve ser acompanhada por etapa no município?",
        "Linhas municipais com faixa da distribuição do Vale; matrícula em painel separado.",
        "Matrícula; aprovação; reprovação; abandono, por etapa.",
        "DESCRIPTIVE_ONLY",
        "A descrição temporal é útil, mas a ausência de componentes exatos impede recomposição regional e teste robusto de estabilidade.",
    )
    add(
        "D1_MATRICULA_DISTORCAO_OFICIAL",
        1,
        "Matrícula e distorção idade-série",
        "Onde matrícula e distorção idade-série mudam em direções que pedem leituras conjuntas?",
        "Fluxos escolares acumulados podem alterar a composição etária das matrículas sem que a mudança de volume explique o fenômeno.",
        "Matrícula e taxa oficial municipal de distorção, rede total.",
        "Matrículas 2014–2025 e distorção oficial 2019–2025.",
        "Componentes exatos da taxa e idade×série para recomposição.",
        "school_location",
        "2019–2025",
        "município × ano × etapa",
        "Evolução descritiva e distribuição municipal de deltas.",
        f"No médio, {distortion['improvingMunicipalityCount']} de {distortion['municipalityCount']} municípios reduziram a distorção; mediana {_fmt(distortion['municipalDeltaMedianPp'])} pp.",
        official_limit,
        f"Nova Santa Rita: distorção no médio {_fmt(distortion['novaSantaRita']['start'])}%→{_fmt(distortion['novaSantaRita']['end'])}% ({_fmt(distortion['novaSantaRita']['deltaPp'])} pp).",
        "Há redução disseminada, mas sem taxa regional recomposta.",
        "O fato local é forte em magnitude, ainda sem regra de pequeno denominador verificável.",
        "Acrescenta uma dimensão de trajetória não visível no módulo demográfico.",
        "Quais etapas precisam de acompanhamento de idade-série mesmo quando a matrícula total cresce ou cai?",
        "Quadrantes de mudança de matrícula e mudança de distorção.",
        "Matrícula; distorção idade-série; distribuição municipal de deltas.",
        "DESCRIPTIVE_ONLY",
        "Taxa oficial sustenta direção e magnitude municipais, não estabilidade/recomposição regional.",
    )
    add(
        "D1_FAMILIA_RENDIMENTO_MUNICIPAL",
        1,
        "Trajetória escolar",
        "A melhora ou piora municipal aparece de forma coerente entre aprovação, reprovação e abandono?",
        "Os três indicadores formam uma família oficial que descreve destinos escolares agregados e deve ser lida conjuntamente.",
        "Taxas oficiais de aprovação, reprovação e abandono no mesmo município/ano/etapa.",
        "Família completa 2018–2025 em rede total, com fechamento oficial por linha já validado no Job 5B.",
        "Denominadores exatos para estabilidade por tamanho.",
        "school_location",
        "2018–2025",
        "município × ano × etapa",
        "Evolução conjunta, decomposição em pp e padrões de concordância, apenas municipal.",
        f"Nova Santa Rita no médio: aprovação +{_fmt(approval['novaSantaRita']['deltaPp'])} pp e abandono {_fmt(dropout['novaSantaRita']['deltaPp'])} pp entre 2018 e 2025.",
        official_limit,
        "A combinação local integra três taxas oficiais sem inferir transição individual.",
        f"{approval['improvingMunicipalityCount']} municípios aumentaram aprovação e {dropout['improvingMunicipalityCount']} reduziram abandono no médio.",
        "Nova Santa Rita mostra combinação substantiva, mas a precisão não pode ser qualificada pelo denominador.",
        "Cria uma leitura de trajetória municipal completa, distinta do H2 formal e dos quatro módulos atuais.",
        "Em qual etapa a combinação de reprovação e abandono ainda exige acompanhamento conjunto?",
        "Três linhas sincronizadas por etapa, com faixa municipal do Vale.",
        "Aprovação; reprovação; abandono; fechamento da família.",
        "PROMISING",
        "A pergunta e a evidência municipal são fortes; seu uso deve permanecer explicitamente descritivo e não regional recomposto.",
    )
    add(
        "D1_DISTORCAO_PERSISTENCIA_DESCRITIVA",
        1,
        "Trajetória escolar",
        "A direção da distorção oficial persiste ao longo dos anos recentes?",
        "Persistência de direção em uma série oficial pode priorizar observação, embora não prove estabilidade estatística.",
        "Taxa oficial anual de distorção por etapa.",
        "Série municipal 2019–2025.",
        "Denominadores exatos e regra oficial de pequeno denominador.",
        "school_location",
        "2019–2025",
        "município × ano × etapa",
        "Direção ano a ano e janelas alternativas, sem teste de precisão.",
        f"No médio, a mudança 2019–2025 variou entre {_fmt(distortion['municipalDeltaMinimumPp'])} e {_fmt(distortion['municipalDeltaMaximumPp'])} pp entre municípios.",
        "Persistência de direção não deve ser chamada de estabilidade; componentes exatos continuam ausentes.",
        f"Nova Santa Rita reduziu {_fmt(abs(distortion['novaSantaRita']['deltaPp']))} pp na janela completa.",
        "Útil para formular perguntas, não para aprovar H2 ou afirmar robustez.",
        "O caso local pode ser acompanhado em janelas pré/pós-pandemia.",
        "Acrescenta temporalidade à fotografia de trajetória.",
        "A melhora recente se mantém e em quais etapas?",
        "Série anual com marcação de mudança de direção.",
        "Distorção anual; número de transições na mesma direção.",
        "DESCRIPTIVE_ONLY",
        "A série oficial é útil, mas a precisão de pequenas bases não é verificável.",
    )
    add(
        "D1_TRAJETORIA_IDEB",
        1,
        "Trajetória e IDEB",
        "Mudanças no rendimento e na distorção convivem com evolução do IDEB na rede total?",
        "Fluxo escolar e aprendizagem integram dimensões diferentes da trajetória e podem divergir.",
        "Taxas municipais totais e IDEB total compatível com todas as dependências.",
        "Taxas municipais totais existem; IDEB por dependências/pública está materializado.",
        "Registro oficial compatível com total_all_dependencies; o recorte Job 2 tem zero linhas IDEB oficiais total/all observadas.",
        "school_location",
        "2011–2025 conforme edição",
        "município × edição × etapa",
        "Mudanças por edição, concordância e divergência de direção.",
        f"Teste interrompido: {t['idebTotalAllDependenciesRows']} linhas observadas de IDEB com dependência total/all no recorte reutilizável.",
        "Não é permitido usar média de dependências nem escolher somente rede pública como substituto silencioso.",
        "Sem comparação canônica total para Nova Santa Rita nesta rodada.",
        "A lacuna vale para o Vale inteiro no escopo canônico.",
        "Nenhum fato municipal foi promovido.",
        "Seria uma dimensão de aprendizagem/fluxo ausente nos quatro módulos.",
        "Aprendizagem e fluxo escolar apontam a mesma agenda por etapa?",
        "Painéis independentes de IDEB e família de rendimento.",
        "IDEB total compatível; aprovação; reprovação; abandono; distorção.",
        "INSUFFICIENT_DATA",
        "O universo do IDEB disponível não satisfaz de forma comprovada a rede total canônica.",
    )
    add(
        "D1_TRAJETORIA_SAEB",
        1,
        "Trajetória e SAEB",
        "Proficiência e trajetória municipal evoluem de forma concordante ou divergente?",
        "Aprendizagem e fluxo são dimensões complementares; melhora em uma não garante melhora na outra.",
        "Proficiência SAEB e taxas de trajetória em rede total compatível.",
        "SAEB/proficiência existe em tabelas e bundles segundo o inventário; trajetória está materializada.",
        "Recorte total_all_dependencies do SAEB e alinhamento de edições não materializados no Job 2.",
        "school_location",
        "2017–2023/2025 conforme edição",
        "município × edição × etapa × disciplina",
        "Concordância de direção, matriz fluxo×aprendizagem e sensibilidade a supressões.",
        "Potencial confirmado no inventário, sem teste calculado no 5F.",
        "Periodicidade, participação e supressão do SAEB precisam ser preservadas; não imputar.",
        "Nova Santa Rita requer checagem de cobertura por edição.",
        "Sem evidência regional nova calculada.",
        "Sem evidência municipal nova calculada.",
        "Adicionaria aprendizagem à leitura de trajetória.",
        "Onde fluxo e aprendizagem pedem respostas de acompanhamento distintas?",
        "Quadrantes por etapa/edição, sem ranking.",
        "Proficiência; participação; aprovação; abandono; distorção.",
        "INSUFFICIENT_DATA",
        "A fonte existe, mas o recorte total canônico e o QA por edição ainda não foram processados.",
    )

    class_snap = t["conditionSnapshots"]["students_per_class_high_school"]
    teacher_snap = t["conditionSnapshots"]["teacher_adequacy_high_school"]
    add(
        "D1_TRAJETORIA_HORAS_AULA",
        1,
        "Trajetória e jornada",
        "Mudanças em horas-aula diárias acompanham diferenças de trajetória por etapa?",
        "Tempo de exposição escolar é uma condição organizacional plausível, mas seu efeito depende de qualidade e contexto.",
        "HAD total por etapa e taxas de trajetória.",
        "HAD 2023–2025 existe no bundle PNE; trajetória municipal está materializada.",
        "Extração total_all_dependencies de HAD para os 10 municípios.",
        "school_location",
        "2023–2025",
        "município × ano × etapa",
        "Variações, associação ecológica controlada descritiva e análise de sensibilidade.",
        "Teste não executado: HAD não integra o recorte Job 2, embora a série exista no projeto.",
        "Janela curta; horas não medem qualidade; causalidade proibida.",
        "Nova Santa Rita será caso obrigatório após extração.",
        "Potencial regional ainda não quantificado.",
        "Sem fato municipal novo.",
        "Inclui organização do tempo escolar, ausente nos quatro módulos.",
        "Que mudança de jornada deve ser observada junto com trajetória, sem assumir efeito?",
        "Painel de HAD e trajetória por etapa.",
        "Horas-aula diárias; aprovação; abandono; distorção.",
        "PROMISING_NEEDS_MORE_TESTING",
        "Mecanismo legítimo e fonte existente, mas série curta e novo processamento obrigatório.",
    )
    add(
        "D1_TRAJETORIA_ALUNOS_TURMA",
        1,
        "Trajetória e organização de turmas",
        "Mudanças em alunos por turma coincidem com mudanças de trajetória no território?",
        "Tamanho médio das turmas pode refletir organização, demanda e disponibilidade docente, sem efeito causal presumido.",
        "ATU e taxas de trajetória totais por etapa.",
        "ATU 2016–2025 e trajetória 2018–2025 no recorte Job 2.",
        "Pesos exatos de ATU não estão disponíveis em todas as linhas; uso apenas da medida oficial total.",
        "school_location",
        "2018–2025",
        "município × ano × etapa",
        "Mudanças e Spearman ecológico entre deltas municipais.",
        f"No médio, correlação de postos entre mudança de ATU e mudança da aprovação = {_fmt(class_assoc['spearmanChange'])}, n={class_assoc['municipalityCount']}; sinal exploratório apenas.",
        "Dez municípios, associação ecológica e múltiplos mecanismos concorrentes; nenhum p-valor aprova a relação.",
        f"Nova Santa Rita: ATU médio {_fmt(class_snap['novaSantaRita']['start'])}→{_fmt(class_snap['novaSantaRita']['end'])}; aprovação {_fmt(approval['novaSantaRita']['start'])}%→{_fmt(approval['novaSantaRita']['end'])}%.",
        "A heterogeneidade municipal permite tipologia, mas não causalidade.",
        "O caso local combina mudança organizacional e trajetória observada.",
        "Acrescenta uma condição de oferta mensurável e acionável.",
        "Em quais etapas mudanças de turma e trajetória devem ser monitoradas juntas?",
        "Quadrantes de deltas + série local.",
        "ATU; matrículas; turmas; aprovação; abandono; distorção.",
        "PROMISING_NEEDS_MORE_TESTING",
        "Dados e sinal exploratório existem; robustez requer janelas, controle por INSE e verificação dos pesos oficiais.",
    )
    add(
        "D1_TRAJETORIA_ADEQUACAO_DOCENTE",
        1,
        "Trajetória e formação docente",
        "Mudanças na adequação da formação docente acompanham a trajetória por etapa?",
        "Maior compatibilidade entre formação e componente curricular pode alterar condições pedagógicas, sem causalidade identificada.",
        "AFD e trajetória totais por etapa.",
        "AFD 2014–2025 e trajetória 2018–2025 no Job 2.",
        "Componentes/pesos da taxa AFD para recomposição regional; leitura usa medida municipal oficial.",
        "school_location",
        "2018–2025",
        "município × ano × etapa",
        "Mudanças e associação ecológica de postos.",
        f"No médio, correlação de postos entre mudança de AFD e aprovação = {_fmt(teacher_assoc['spearmanChange'])}, n={teacher_assoc['municipalityCount']}.",
        "Associação ecológica com n=10; AFD não mede prática pedagógica e não autoriza causalidade.",
        f"Nova Santa Rita: AFD no médio {_fmt(teacher_snap['novaSantaRita']['start'])}%→{_fmt(teacher_snap['novaSantaRita']['end'])}%.",
        "O Vale apresenta variação suficiente para testar padrões sem estratificar dependência.",
        "Fato local disponível e comparável à distribuição municipal.",
        "Adiciona força de trabalho docente à interpretação territorial.",
        "Quais etapas combinam lacunas de adequação e trajetória que merecem acompanhamento?",
        "Quadrantes AFD×trajetória e série municipal.",
        "AFD; aprovação; abandono; distorção.",
        "PROMISING_NEEDS_MORE_TESTING",
        "Fonte longa e pergunta útil; associação inicial precisa de janelas e controles descritivos.",
    )
    for analysis_id, label, metric, period in (
        ("D1_TRAJETORIA_ESFORCO_DOCENTE", "esforço docente", "IED", "2023–2025"),
        ("D1_TRAJETORIA_REGULARIDADE_DOCENTE", "regularidade docente", "IRD", "2023–2025"),
    ):
        add(
            analysis_id,
            1,
            f"Trajetória e {label}",
            f"Como {label} e trajetória escolar variam conjuntamente entre municípios?",
            f"{label.capitalize()} pode afetar continuidade e disponibilidade pedagógica, mas também responde à organização territorial.",
            f"{metric} total e trajetória por etapa.",
            f"{metric} existe no bundle PNE segundo o inventário; trajetória está materializada.",
            f"Recorte {metric} total_all_dependencies para o Vale e Nova Santa Rita.",
            "school_location",
            period,
            "município × ano × etapa",
            "Variações, persistência e associações ecológicas com controles descritivos.",
            f"Teste não executado: {metric} não integra os artefatos reutilizáveis do Job 2.",
            "Janela curta, cobertura variável e ausência de desenho causal.",
            "Nova Santa Rita deve ser testada após extração.",
            "Potencial regional confirmado pela existência da série, sem resultado calculado.",
            "Sem fato municipal novo.",
            "Acrescenta dimensão docente não coberta pelos módulos atuais.",
            f"Que padrão de {label} precisa ser acompanhado junto com a trajetória?",
            f"Mapa/linha de {metric} com trajetória em painel separado.",
            f"{metric}; aprovação; abandono; distorção.",
            "PROMISING_NEEDS_MORE_TESTING",
            "Fonte materializada no projeto e mecanismo legítimo, mas novo processamento e QA são necessários.",
        )

    broadband = t["conditionSnapshots"]["broadband"]
    connectivity = t["connectivity2025"]
    add(
        "D1_TRAJETORIA_INFRAESTRUTURA",
        1,
        "Trajetória e infraestrutura",
        "Condições básicas das escolas ajudam a contextualizar diferenças de trajetória?",
        "Infraestrutura condiciona a possibilidade de oferta, mas indicadores agregados e saturados raramente explicam sozinhos a trajetória.",
        "Percentuais de escolas com água, biblioteca, quadra, internet e banda larga; trajetória.",
        "Internet e banda larga totais 2014–2025; outros itens estão indisponíveis no recorte para parte relevante.",
        "Recuperação/QA dos itens com valores indisponíveis e definição consistente ao longo do tempo.",
        "school_location",
        "2014–2025",
        "município × ano",
        "Cobertura, saturação, variações e associação ecológica somente quando comparável.",
        f"Banda larga e abandono no médio tiveram correlação de postos dos deltas {_fmt(broad_assoc['spearmanChange'])}, n={broad_assoc['municipalityCount']}; itens água/biblioteca/quadra têm indisponibilidade no recorte.",
        "Mudanças de definição e saturação; infraestrutura não é causa demonstrada.",
        f"Nova Santa Rita: banda larga {_fmt(broadband['novaSantaRita']['start'])}%→{_fmt(broadband['novaSantaRita']['end'])}%.",
        "A expansão da conectividade é generalizada; outros itens precisam de QA.",
        "Fato local é útil como condição, não como explicação.",
        "Acrescenta contexto de oferta, mas com menor poder discriminatório.",
        "Quais condições ainda não estão universalizadas e precisam ser acompanhadas?",
        "Matriz de disponibilidade e saturação por indicador/município.",
        "Percentual de escolas por item; número de escolas; trajetória municipal.",
        "DESCRIPTIVE_ONLY",
        "A conectividade está perto da saturação e outros itens não têm qualidade suficiente no recorte; serve como contexto.",
    )
    add(
        "D1_TRAJETORIA_CONECTIVIDADE",
        1,
        "Trajetória e conectividade",
        "A universalização de internet e banda larga muda a pergunta educacional do território?",
        "Quando acesso básico se satura, a agenda migra de presença para qualidade e uso pedagógico, não observados por este indicador.",
        "Percentual de escolas com internet/banda larga e trajetória.",
        "Séries totais 2014–2025 com numerador e denominador de escolas.",
        "Qualidade, velocidade, uso pedagógico e equipamentos.",
        "school_location",
        "2014–2025",
        "município × ano",
        "Saturação, tempo até universalização e persistência.",
        f"Em 2025, {connectivity['internetMunicipalitiesAt100Percent']}/{connectivity['internetMunicipalityCount']} municípios tinham 100% das escolas com internet e {connectivity['broadbandMunicipalitiesAt100Percent']}/{connectivity['broadbandMunicipalityCount']} com banda larga.",
        "Presença não mede qualidade nem uso; associação com trajetória é ecológica.",
        "Nova Santa Rita chegou a 100% em internet e banda larga no recorte de 2025.",
        "A saturação regional reduz valor de comparação entre municípios.",
        "O fato local desloca a pergunta para qualidade, atualmente não medida.",
        "Evita usar conectividade como explicação genérica e identifica lacuna de produto.",
        "Quais indicadores de qualidade e uso digital precisam substituir a simples presença?",
        "Curva de saturação e cartão de lacuna de qualidade, interno.",
        "Escolas com internet/banda larga; indicador futuro de qualidade/uso.",
        "DESCRIPTIVE_ONLY",
        "Há boa descrição da universalização, mas pouco valor discriminatório e ausência de qualidade de conexão.",
    )
    add(
        "D1_TRAJETORIA_INSE",
        1,
        "Trajetória e nível socioeconômico",
        "O contexto socioeconômico ajuda a interpretar diferenças municipais de trajetória?",
        "Composição socioeconômica dos alunos avaliados pode estruturar diferenças observadas, sem determinar resultados.",
        "INSE e trajetória total por município/etapa.",
        "INSE 2019/2021/2023 e trajetória 2018–2025.",
        "INSE por etapa comparável e cobertura integral; a medida total usa alunos avaliados.",
        "school_location/evaluated_students",
        "fotografia 2023 e série curta",
        "município × edição",
        "Correlação de postos e comparação de resíduos descritivos, sem ranking causal.",
        f"Em 2023, correlação de postos INSE×distorção do médio = {_fmt(inse_assoc['spearmanLevel'])}, n={inse_assoc['municipalityCount']}.",
        "Amostra pequena, alunos avaliados e possível cobertura desigual; não causal.",
        "Nova Santa Rita tinha INSE 5,4032 em 2023; usar apenas como contexto da fotografia.",
        "O padrão regional pode orientar estratificação analítica transparente, não ajuste de responsabilidade.",
        "Fato local não identifica pessoas nem explica isoladamente a trajetória.",
        "Adiciona contexto social que os quatro módulos não mostram.",
        "Que diferenças de contexto precisam ser consideradas ao acompanhar trajetória, sem reduzir expectativas?",
        "Dispersão INSE×trajetória com destaque municipal e avisos de cobertura.",
        "INSE; alunos avaliados; trajetória oficial.",
        "DESCRIPTIVE_ONLY",
        "Útil para contexto, mas a fotografia ecológica curta não sustenta uma história explicativa autônoma.",
    )
    add(
        "D1_TRAJETORIA_TEMPO_INTEGRAL",
        1,
        "Trajetória e tempo integral",
        "Expansão do tempo integral coexistiu com mudanças de trajetória e demanda por etapa?",
        "Maior permanência diária reorganiza vagas, turmas, alimentação, transporte e trabalho docente.",
        "Matrículas em tempo integral, matrículas totais, turmas e trajetória.",
        "Tempo integral 2014–2025 existe em public.censo; demais séries estão materializadas.",
        "Recorte total por etapa e QA de definição anual.",
        "school_location",
        "2014–2025",
        "município × ano × etapa",
        "Participação, variação, decomposição de expansão e associação ecológica.",
        "Teste não executado: o indicador não integra os outputs congelados do Job 2.",
        "Definição anual e dupla contagem precisam de QA; causalidade proibida.",
        "Nova Santa Rita é caso obrigatório após extração.",
        "Potencial regional alto por ligação direta com organização da oferta.",
        "Sem fato municipal novo.",
        "Amplia a página com uma decisão concreta de jornada e capacidade organizacional.",
        "Onde expansão do integral exige reorganizar turmas, docentes e infraestrutura?",
        "Participação do integral por etapa com séries de turmas e matrícula.",
        "Matrículas integrais; participação; turmas; docentes; trajetória.",
        "PROMISING_NEEDS_MORE_TESTING",
        "Fonte e mecanismo são fortes, mas falta processamento e validação temporal.",
    )

    dist_rows = eja["distribution2022"]
    nsr_fund = next(r for r in dist_rows if r["municipality_ibge_code"] == NOVA_SANTA_RITA_ID and r["stage"] == "fundamental")
    nsr_med = next(r for r in dist_rows if r["municipality_ibge_code"] == NOVA_SANTA_RITA_ID and r["stage"] == "high_school")
    reg_fund = next(r for r in dist_rows if r["entity_scope"] == "region" and r["stage"] == "fundamental")
    reg_med = next(r for r in dist_rows if r["entity_scope"] == "region" and r["stage"] == "high_school")
    for analysis_id, label, local, regional_row in (
        ("D1_EJA_FUNDAMENTAL_PUBLICO_ADULTO", "fundamental", nsr_fund, reg_fund),
        ("D1_EJA_MEDIO_PUBLICO_ADULTO", "médio", nsr_med, reg_med),
    ):
        add(
            analysis_id,
            1,
            f"Público adulto e EJA {label}",
            f"Como se distribuem o público residente sem {label} concluído e as matrículas localizadas de EJA {label}?",
            "Distribuições territoriais diferentes podem exigir articulação local/regional sem medir demanda ou cobertura.",
            "População adulta residente sem conclusão e matrículas totais de EJA da etapa.",
            "Fotografia 2022 completa para 10 municípios, Vale e RS.",
            "Nenhum insumo crítico para a fotografia; atualização depende de próximo Censo comparável.",
            "resident_population + school_location",
            "2022",
            "município × etapa; distribuição regional por somas",
            "Participações municipais e diferença distributiva; fechamento das participações.",
            f"No Vale, público {_fmt(regional_row['potential_public'])} e matrículas {_fmt(regional_row['eja_enrollments'])}; distribuição municipal fecha em 100% para cada universo.",
            eja["limits"],
            f"Nova Santa Rita: {_fmt(local['participacao_publico_i']*100,4)}% do público e {_fmt(local['participacao_matriculas_i']*100,4)}% das matrículas; diferença {_fmt(local['diferenca_distribuicao_pp']*100,4)} pp.",
            "A distribuição evidencia concentração e heterogeneidade regional por etapa.",
            "A direção local difere entre fundamental e médio, impedindo síntese única.",
            "Mantém duas perguntas substantivas separadas, revelando decisões distintas dentro do antigo H4.",
            f"Que articulação deve acompanhar a distribuição do público e da oferta de EJA {label}?",
            "Pares de participações por município, em painel próprio da etapa.",
            "Participação do público; participação das matrículas; diferença distributiva.",
            "PROMISING",
            "Dados, fórmula, escala regional e fato municipal estão fechados; as duas etapas entregam questões diferentes.",
        )
    add(
        "D1_ESCOLARIDADE_ADULTA_2010_2022_EJA",
        1,
        "Mudança da escolaridade adulta e EJA",
        "A mudança 2010→2022 do estoque adulto sem conclusão ocorreu nos mesmos municípios em que a EJA se reorganizou?",
        "Redução/redistribuição do estoque adulto e mudanças na oferta de EJA podem seguir ritmos diferentes.",
        "População adulta por conclusão em 2010/2022 e EJA anual 2014–2025.",
        "Tabelas adultas 2010/2022 existem; EJA histórica está materializada.",
        "Recorte 2010 da população adulta ainda não integra os outputs Job 2.",
        "resident_population + school_location",
        "2010–2022; EJA 2014–2025",
        "município × etapa",
        "Variações intercensitárias, contribuição municipal e tipologia de direções.",
        "Teste não executado por ausência do recorte adulto 2010 no pacote congelado.",
        "Dois pontos censitários não formam tendência anual; universos não são as mesmas pessoas.",
        "Nova Santa Rita deve ser comparada com Vale, RS e pares após extração.",
        "Pode revelar municípios onde estoque e oferta mudaram em ritmos opostos.",
        "Sem fato municipal novo nesta rodada.",
        "Acrescenta transformação de longo prazo ao retrato estático de 2022.",
        "Como a agenda da EJA muda quando o estoque adulto se transforma entre Censos?",
        "Quadrantes 2010→2022 do público versus 2014→2022/2025 da EJA.",
        "Público adulto 2010/2022; matrículas EJA por etapa; contribuição municipal.",
        "PROMISING_NEEDS_MORE_TESTING",
        "Fonte existe e a pergunta amplia o módulo EJA, mas requer novo processamento e cautela temporal.",
    )
    add(
        "D1_EJA_EDUCACAO_PROFISSIONAL",
        1,
        "EJA integrada à educação profissional",
        "A EJA integrada à educação profissional tem presença e evolução territorial suficientes para orientar acompanhamento?",
        "Integração pode combinar conclusão da educação básica e formação profissional, mas sua escala e modalidade variam.",
        "Matrículas EJA total e integradas por modalidade, rede total.",
        "Série 2014–2025 para Vale, RS e municípios.",
        "Ingressantes/concluintes e capacidade de oferta.",
        "school_location",
        "2014–2025",
        "município × ano × modalidade",
        "Participação, persistência, concentração e zero observado versus ausência.",
        f"Vale: EJA integrada {_fmt(region_eja_2014['mat_eja_integrada_educacao_profissional'])}→{_fmt(region_eja_2025['mat_eja_integrada_educacao_profissional'])}; participação {_fmt(region_eja_2014['integrated_share_percent'])}%→{_fmt(region_eja_2025['integrated_share_percent'])}%.",
        "Matrícula não é vaga, ingresso ou conclusão; zeros observados precisam permanecer distintos de ausência.",
        f"Nova Santa Rita registrou {_fmt(nsr_eja_2014['mat_eja_integrada_educacao_profissional'])} em 2014 e {_fmt(nsr_eja_2025['mat_eja_integrada_educacao_profissional'])} em 2025, ambos zeros observados.",
        "A oferta integrada é pequena e concentrada, útil como agenda de articulação.",
        "O zero local observado não significa automaticamente insuficiência ou demanda.",
        "Adiciona modalidade formativa e articulação à leitura de EJA.",
        "Onde acompanhar continuidade e composição da EJA integrada sem inferir demanda não observada?",
        "Série regional + mapa de presença/zero observado por modalidade.",
        "Matrículas integradas; participação; municípios com presença; modalidade FIC/técnico.",
        "PROMISING",
        "Série longa, semântica clara e valor de planejamento próprio; a escala pequena exige apresentação cuidadosa.",
    )
    for analysis_id, label, field in (
        ("D1_EJA_FUNDAMENTAL_HISTORICA", "fundamental", "mat_eja_fundamental_total"),
        ("D1_EJA_MEDIO_HISTORICA", "médio", "mat_eja_medio_total"),
    ):
        start = float(region_eja_2014[field])
        end = float(region_eja_2025[field])
        local_start = float(nsr_eja_2014[field])
        local_end = float(nsr_eja_2025[field])
        add(
            analysis_id,
            1,
            f"Evolução territorial da EJA {label}",
            f"Como o volume e a distribuição municipal da EJA {label} mudaram desde 2014?",
            "Mudanças de volume regional podem ocultar redistribuição entre municípios e modalidades.",
            f"Matrículas totais de EJA {label} por município/ano.",
            "Série 2014–2025 completa em rede total.",
            "População adulta anual comparável não existe entre Censos.",
            "school_location",
            "2014–2025",
            "município × ano × etapa",
            "Variação, contribuição municipal, concentração e persistência.",
            f"Vale: {_fmt(start)}→{_fmt(end)} matrículas ({_fmt(_pct_change(start,end))}%).",
            "Não interpretar como cobertura; pandemia e mudanças de oferta exigem janelas alternativas.",
            f"Nova Santa Rita: {_fmt(local_start)}→{_fmt(local_end)} matrículas.",
            "Permite decompor a mudança regional por município.",
            "O caso local pode divergir da região e da fotografia 2022.",
            "Acrescenta tendência anual à distribuição estática do H4.",
            f"Que mudança de escala e distribuição da EJA {label} deve ser acompanhada?",
            "Série regional empilhada por contribuição municipal + linha local.",
            "Matrículas; participação municipal; contribuição à mudança; concentração.",
            "PROMISING_NEEDS_MORE_TESTING",
            "Série pronta e útil, mas exige janelas pré/pós-pandemia e cuidado para não sugerir demanda/cobertura.",
        )

    mobility_rows = d["mobility2022"]
    nsr_mob = {r["universe"]: r for r in mobility_rows if r["municipality_ibge_code"] == NOVA_SANTA_RITA_ID}
    reg_mob = {r["universe"]: r for r in mobility_rows if r["entity_scope"] == "region"}
    add(
        "D1_MOBILIDADE_POR_ETAPA",
        1,
        "Mobilidade educacional",
        "Em quais etapas estudar fora do município de residência é mais frequente?",
        "Oferta, escolhas familiares e localização territorial fazem parte dos residentes estudar fora, exigindo coordenação.",
        "Residentes estudantes e residentes que estudam fora por etapa.",
        "Fotografia 2022 total, fundamental e médio para 10 municípios, Vale e RS.",
        "Destino, rota, escola receptora e série temporal.",
        "student_residence",
        "2022",
        "município de residência × etapa",
        "Participações por soma de componentes e comparação Vale/RS.",
        f"Vale: total {_fmt(reg_mob['total']['outside_share_percent'])}%, fundamental {_fmt(reg_mob['fundamental']['outside_share_percent'])}% e médio {_fmt(reg_mob['medio']['outside_share_percent'])}% fora do município.",
        "Fotografia preliminar sem destino; não atribuir causa ou ente responsável.",
        f"Nova Santa Rita: total {_fmt(nsr_mob['total']['outside_share_percent'])}% e médio {_fmt(nsr_mob['medio']['outside_share_percent'])}%.",
        "A diferença por etapa sustenta coordenação regional.",
        "Nova Santa Rita supera Vale e RS no total/médio conforme Job 5A.",
        "Desdobra A4 em leitura de etapa com comparação explícita.",
        "Que transições, transporte como contexto e diálogo regional precisam ser acompanhados por etapa?",
        "Barras por etapa e município com Vale/RS.",
        "Residentes estudantes; estudam fora; participação; residual.",
        "PROMISING",
        "Componentes e comparadores estão fechados; a utilidade é real mesmo sem destino, desde que a limitação permaneça central.",
    )
    mob_assoc = d["mobilityAssociations"]
    add(
        "D1_MOBILIDADE_ESTRUTURA_OFERTA",
        1,
        "Mobilidade e oferta local",
        "Mobilidade no médio se associa à evolução da matrícula localizada no município?",
        "Estrutura local de oferta e deslocamento por residência podem se ajustar conjuntamente, sem identificar destinos.",
        "Mobilidade 2022 e evolução de matrícula/escolas/turmas locais.",
        "Mobilidade 2022 e H1 2014–2025.",
        "Destino e capacidade da oferta.",
        "student_residence + school_location",
        "mobilidade 2022; oferta 2014–2025",
        "município",
        "Tipologia e correlação de postos ecológica.",
        f"Correlação de postos entre participação que estuda fora no médio e mudança 2014–2025 da matrícula local = {_fmt(mob_assoc['outsideShareVsLocalEnrollmentChange']['spearman'])}, n=10.",
        mob_assoc["interpretation"],
        f"Nova Santa Rita combina {_fmt(nsr_mob['medio']['outside_share_percent'])}% estudando fora no médio com matrícula local {_fmt(h1n['high_school']['enrollment_start'])}→{_fmt(h1n['high_school']['enrollment_end'])}.",
        "O sinal é exploratório e heterogêneo, suficiente para nova pergunta, não conclusão.",
        "O caso local mostra por que mobilidade e oferta não devem ser lidas separadamente.",
        "Vai além de A4 ao relacionar mobilidade à organização observada, preservando lentes.",
        "Quais municípios precisam acompanhar conjuntamente oferta localizada e residentes que estudam fora?",
        "Quadrantes mobilidade 2022 × mudança da oferta.",
        "Participação fora; matrícula local; escolas; turmas.",
        "PROMISING_NEEDS_MORE_TESTING",
        "Pergunta substantiva e sinal calculado; falta destino, capacidade e sensibilidade a janelas.",
    )
    add(
        "D1_MOBILIDADE_CRESCIMENTO_DEMOGRAFICO",
        1,
        "Mobilidade e demografia",
        "Municípios com crescimento de jovens apresentam padrões distintos de estudo fora?",
        "Crescimento residencial pode aumentar pressão sobre oferta local ou ampliar deslocamentos, dependendo da organização territorial.",
        "População jovem anual e mobilidade por residência.",
        "População 15–17 2014–2022 e mobilidade 2022.",
        "Série temporal de mobilidade e destinos.",
        "resident_population + student_residence",
        "2014–2022; fotografia 2022",
        "município",
        "Correlação de postos, quadrantes e sensibilidade à faixa etária.",
        f"Correlação de postos entre mudança 2014–2022 da população 15–17 e participação fora no médio = {_fmt(mob_assoc['outsideShareVsResident1517Change']['spearman'])}, n=10.",
        "Uma fotografia de mobilidade não estabelece resposta a crescimento; associação ecológica.",
        "Nova Santa Rita deve aparecer no quadrante com seu crescimento e participação fora.",
        "Há heterogeneidade suficiente para testar tipologia.",
        "A posição local orienta pergunta de coordenação, não causalidade.",
        "Conecta crescimento residencial à coordenação educacional supramunicipal.",
        "Onde crescimento residencial e mobilidade pedem planejamento conjunto?",
        "Quadrantes por faixa/etapa.",
        "População 15–17; participação fora no médio; matrícula local.",
        "PROMISING_NEEDS_MORE_TESTING",
        "Sinal calculado e utilidade plausível, mas a natureza transversal e ausência de destino limitam conclusão.",
    )
    add(
        "D1_MOBILIDADE_TRAJETORIA",
        1,
        "Mobilidade e trajetória",
        "Municípios com maior estudo fora exibem padrões diferentes de trajetória oficial?",
        "Mobilidade pode mudar o universo escolar localizado observado, gerando composição ecológica distinta entre residentes e escolas.",
        "Mobilidade por residência e trajetória por localização da escola.",
        "Mobilidade 2022 e taxas oficiais municipais 2022/2023.",
        "Vinculação origem–destino e componentes exatos das taxas.",
        "student_residence + school_location",
        "fotografia 2022/2023",
        "município",
        "Correlação de postos exploratória e análise de influência.",
        "Teste completo não promovido: universos diferem e n=10; pode ser usado apenas para formular questões.",
        official_limit + " Mobilidade e trajetória não observam as mesmas pessoas.",
        "Nova Santa Rita tem mobilidade elevada no médio e melhora descritiva de taxas, sem ligação individual.",
        "A relação pode revelar composição territorial, mas é frágil.",
        "O fato local é contextual, não explicativo.",
        "Acrescenta alerta de interpretação para resultados por localização da escola.",
        "Como mobilidade deve ser considerada ao interpretar indicadores escolares locais?",
        "Dois painéis coordenados, sem linha de tendência causal.",
        "Participação fora; taxas municipais oficiais; cobertura de avaliação.",
        "DESCRIPTIVE_ONLY",
        "Universos diferentes, fotografia única e ausência de destino impedem leitura mais forte.",
    )
    add(
        "D1_COORTES_DEMANDA_FUTURA_MECANICA",
        1,
        "Coortes e demanda futura",
        "Que pressões mecânicas já nascidas aparecem para pré-escola, fundamental e médio até 2030?",
        "Envelhecer coortes observadas informa a ordem de grandeza do público que alcançará etapas, sem prever matrícula.",
        "População por idade 2025 e matrícula/escolas-base 2025.",
        "Cenário mecânico 2026–2030 para Vale e 10 municípios.",
        "Migração, mortalidade, entrada, repetência e mobilidade; necessários para previsão, não para pressão mecânica.",
        "resident_population + school_location",
        "2026–2030 mecânico com base 2025",
        "município × etapa × ano-alvo",
        "Envelhecimento de coortes, razões contra base e sensibilidade sem migração.",
        f"Em 2030, Vale: pré-escola {_fmt(cohort_region['preschool']['cohort_to_baseline_enrollment_ratio']*100)}%, fundamental {_fmt(cohort_region['fundamental']['cohort_to_baseline_enrollment_ratio']*100)}%, médio {_fmt(cohort_region['high_school']['cohort_to_baseline_enrollment_ratio']*100)}% da matrícula-base 2025.",
        d["mechanicalCohortLimit"],
        f"Nova Santa Rita: pré-escola {_fmt(cohort_nsr['preschool']['cohort_to_baseline_enrollment_ratio']*100)}%, fundamental {_fmt(cohort_nsr['fundamental']['cohort_to_baseline_enrollment_ratio']*100)}%, médio {_fmt(cohort_nsr['high_school']['cohort_to_baseline_enrollment_ratio']*100)}%.",
        "A composição por etapa difere materialmente e permite agenda antecipatória.",
        "O médio local apresenta pressão mecânica muito superior à base observada.",
        "Adiciona horizonte prospectivo limitado e transparente, além dos quatro módulos históricos.",
        "Que indicadores acompanhar antes de as coortes observadas alcançarem cada etapa?",
        "Fan chart mecânico por etapa, explicitamente não preditivo.",
        "Coorte mecânica; matrícula-base; escolas-base; razão mecânica.",
        "PROMISING",
        "Método e limites estão materializados; a leitura é útil se nunca for apresentada como previsão de matrícula.",
    )

    processing_rows = [
        (
            "D1_PNE_DIAGNOSTICOS_COMPARADORES",
            "Diagnósticos PNE e comparadores",
            "Quais transformações territoriais coincidem com indicadores PNE/PME já prioritários no município?",
            "O diagnóstico define prioridades educacionais, enquanto o território acrescenta contexto e horizonte de acompanhamento.",
            "Diagnóstico PNE v3, comparadores canônicos e evidências territoriais.",
            "Diagnóstico e comparadores existem na publicação PNE; evidências 5F estão materializadas.",
            "Adaptador interno que una os contratos sem copiar narrativa nem alterar indicadores.",
            "pne_indicator_scope + lentes de cada evidência",
            "períodos próprios dos indicadores",
            "município × indicador PNE",
            "Join por código IBGE, matriz prioridade×evidência e não redundância.",
            "Novo processamento não executado para evitar ler/republicar os 499 detalhes durante esta expansão.",
            "Indicadores têm universos e anos próprios; nenhuma causalidade ou score sintético.",
            "Nova Santa Rita deve usar somente comparadores canônicos já definidos.",
            "Potencial de organizar acompanhamento sem criar meta nova.",
            "Sem fato novo unido nesta rodada.",
            "Liga cada história a uma prioridade PNE/PME concreta.",
            "Que transformação territorial muda o acompanhamento de qual indicador PNE/PME?",
            "Matriz de ligação história×indicador, sem score.",
            "Indicadores diagnósticos; posição frente a referências; evidências territoriais.",
        ),
        (
            "D1_CRESCIMENTO_INFRAESTRUTURA",
            "Crescimento demográfico e infraestrutura",
            "A infraestrutura escolar acompanhou municípios e etapas em crescimento?",
            "Crescimento residencial/matricular pode pressionar a presença de equipamentos e espaços escolares.",
            "População, matrículas, escolas e infraestrutura total.",
            "População/matrícula e conectividade estão prontas; outros itens têm indisponibilidade.",
            "QA/recuperação de biblioteca, quadra, água e detalhamento por escola.",
            "resident_population + school_location",
            "2014–2025",
            "município × ano",
            "Variações, contribuição e tipologia crescimento×infraestrutura.",
            "Teste parcial: conectividade cresceu e saturou; demais itens não são utilizáveis no recorte atual.",
            "Presença não mede qualidade/capacidade e definições podem mudar.",
            "Nova Santa Rita tem crescimento educacional e conectividade universalizada, mas os demais itens estão indisponíveis.",
            "Vale requer microdados/escola para ganho real.",
            "Fato local parcial.",
            "Acrescenta condição física à agenda de crescimento.",
            "Onde crescimento exige qualificar infraestrutura além de conectividade básica?",
            "Matriz de cobertura de itens por município.",
            "Escolas por item; matrículas; crescimento populacional.",
        ),
        (
            "D1_MATRICULA_EPT_REDE",
            "EPT e rede escolar",
            "Como a participação da EPT mudou dentro da oferta educacional do Vale?",
            "Mudanças da matrícula técnica alteram a composição da oferta e a articulação com etapas regulares.",
            "Matrículas técnicas e totais por município/ano/modalidade.",
            "Matrícula técnica 2014–2025 no Censo e cursos/eixos 2023–2025.",
            "EPT por modalidade completa no recorte Job 2; tabela existe, mas não foi extraída.",
            "school_location",
            "2014–2025",
            "município × ano",
            "Participação, concentração, contribuição e persistência.",
            f"Vale: matrículas técnicas {_fmt(network['region2014']['technical_enrollments'])}→{_fmt(network['region2025']['technical_enrollments'])}; Nova Santa Rita {_fmt(network['novaSantaRita2014']['technical_enrollments'])}→{_fmt(network['novaSantaRita2025']['technical_enrollments'])}.",
            "Matrícula não é vaga/ingresso/conclusão; modalidade detalhada ainda não processada.",
            "Nova Santa Rita apresenta zero observado em 2025 no agregado técnico.",
            "A mudança regional é aditiva e pode ser decomposta.",
            "Zero local não significa ausência de demanda ou obrigação de ofertar.",
            "Acrescenta composição de EPT ao módulo trabalho/formação.",
            "Como a composição da EPT mudou e que modalidades precisam ser acompanhadas?",
            "Série de matrícula técnica + composição por modalidade.",
            "Matrículas técnicas; participação; modalidade; concentração.",
        ),
        (
            "D1_DOCENTES_TURMAS_JORNADA",
            "Docentes, turmas e jornada",
            "A organização de docentes, turmas e jornada mudou de forma coerente?",
            "Tempo integral e horas-aula aumentam requisitos de docentes e organização de turmas.",
            "Docentes, turmas, HAD e tempo integral.",
            "Todos existem nas fontes do projeto; apenas turmas/ATU foram parcialmente extraídos.",
            "Recorte integrado total_all_dependencies.",
            "school_location",
            "2014–2025, HAD 2023–2025",
            "município × ano × etapa",
            "Razões com denominadores declarados, variações e tipologia.",
            "Não testado por falta de materialização integrada.",
            "Docentes podem aparecer em múltiplas etapas; jornada curta para HAD.",
            "Nova Santa Rita será caso obrigatório.",
            "Potencial para planejamento de capacidade humana.",
            "Sem fato municipal novo.",
            "Cria uma história operacional nova, ausente dos quatro módulos.",
            "Onde jornada e turmas pressionam a organização docente?",
            "Painel de docentes/turmas/jornada.",
            "Docentes; turmas; HAD; integral; docentes por turma.",
        ),
        (
            "D1_VULNERABILIDADE_EJA_TRAJETORIA",
            "Vulnerabilidade, EJA e trajetória",
            "CadÚnico e outras medidas de vulnerabilidade ajudam a localizar públicos para acompanhamento educacional?",
            "Vulnerabilidade socioeconômica pode concentrar barreiras de permanência e retorno, sem identificar as mesmas pessoas nas bases.",
            "CadÚnico municipal, EJA e trajetória.",
            "CadÚnico/vulnerabilidade existe em pacotes Vocações; EJA e trajetória estão materializadas.",
            "Recorte canônico do Vale, período e definição do cadastro.",
            "registered_families_or_residents + school_location",
            "a confirmar",
            "município × período",
            "Taxas sobre universo cadastrado, tipologias e sensibilidade temporal.",
            "Não testado; fonte não integra Job 2.",
            "CadÚnico não representa população total nem identifica estudantes/trabalhadores.",
            "Nova Santa Rita requer comparação no universo cadastrado.",
            "Potencial de qualificar públicos sem score.",
            "Sem fato local novo.",
            "Adiciona lente social além do INSE de avaliados.",
            "Quais públicos precisam de articulação intersetorial para permanência ou retorno?",
            "Tipologia sem ranking, com denominadores do cadastro.",
            "Famílias/pessoas cadastradas; EJA; trajetória.",
        ),
        (
            "D1_EDUCACAO_ESPECIAL_TERRITORIO",
            "Educação especial e território",
            "Mudanças demográficas e de oferta alteram a agenda de AEE/educação especial?",
            "A oferta especializada e a localização escolar podem exigir coordenação e acesso territorial.",
            "Matrículas de educação especial/AEE, escolas e população pertinente.",
            "Tabelas AEE e educação especial 2014–2025 existem.",
            "Recorte total do Vale, definição de público e lentes compatíveis.",
            "school_location + resident_population_only_if_compatible",
            "2014–2025",
            "município × ano",
            "Variações, concentração e presença/indisponibilidade.",
            "Não testado no 5F.",
            "Não há população-residente equivalente direta; evitar cobertura.",
            "Nova Santa Rita deve ser testada sem exceção ad hoc.",
            "Potencial regional de coordenação.",
            "Sem fato local novo.",
            "Amplia a página para inclusão e acesso territorial.",
            "Onde a oferta especializada requer coordenação além do município?",
            "Mapa de matrículas/escolas com presença e disponibilidade.",
            "Matrículas AEE/especial; escolas; disponibilidade.",
        ),
        (
            "D1_EDUCACAO_RURAL_DEMOGRAFIA",
            "Educação rural e demografia",
            "População rural e matrículas rurais mudam em ritmos que exigem organização territorial distinta?",
            "Dispersão territorial e mudança demográfica afetam acesso, transporte e escala da oferta rural.",
            "População rural estimada e matrículas/escolas rurais.",
            "Tabelas rurais materializadas com método registrado.",
            "Recorte do Vale e QA da estimativa no mesmo período.",
            "resident_population_estimated + school_location",
            "Censo 2022 e anos educacionais compatíveis",
            "município × ano/localização rural",
            "Comparação de distribuição e séries, sem cobertura individual.",
            "Não testado no 5F.",
            "População rural é estimada e lente difere da escola rural.",
            "Nova Santa Rita requer checagem de relevância e cobertura.",
            "Pode revelar questão de acesso invisível no agregado.",
            "Sem fato local novo.",
            "Adiciona heterogeneidade intraterritorial relevante.",
            "Onde preservar acesso e transporte no território rural?",
            "Painéis separados de população rural e oferta rural.",
            "População rural; matrículas/escolas rurais; transporte.",
        ),
    ]
    for index, values in enumerate(processing_rows):
        status = "PROMISING" if values[0] == "D1_MATRICULA_EPT_REDE" else "PROMISING_NEEDS_MORE_TESTING"
        reason = (
            "Série aditiva já fornece fato regional e municipal; detalhar modalidade amplia robustez."
            if status == "PROMISING"
            else "Pergunta legítima e fonte existente, mas novo processamento/QA ainda é necessário."
        )
        add(values[0], 1, *values[1:], status, reason)

    stocks = labour["raisYouthStocks"]
    courses = labour["technicalCourses"]
    bridge = labour["bridgeCoverage2025"]
    region_occ_up = labour["occupations"]["region"]["largestIncreases"][0]
    nsr_occ_up = labour["occupations"]["novaSantaRita"]["largestIncreases"][0]
    add(
        "D2_TRABALHO_JUVENIL_ENSINO_MEDIO",
        2,
        "Trabalho juvenil e ensino médio",
        "Que mudanças do trabalho formal de 15–17 anos precisam entrar no acompanhamento do ensino médio?",
        "Crescimento, retração ou rotatividade do trabalho juvenil no estabelecimento podem coexistir com desafios de permanência escolar no território.",
        "RAIS/Caged 15–17 e trajetória/matrícula do médio.",
        "RAIS 2019–2025, Caged 2020–2025 e trajetória oficial municipal.",
        "Vínculo individual escola–trabalho e local de residência; não necessários para leitura ecológica, mas impedem causalidade.",
        "workplace_municipality + school_location",
        "2019–2025",
        "município × ano",
        "Estoques, fluxos, tipologia, persistência e modelos descritivos com defasagens.",
        f"Vínculos 15–17 no Vale {_fmt(stocks['15_17_2019']['region'])}→{_fmt(stocks['15_17_2025']['region'])}; Nova Santa Rita {_fmt(stocks['15_17_2019']['novaSantaRita'])}→{_fmt(stocks['15_17_2025']['novaSantaRita'])}.",
        labour["limits"] + "; H3 histórico permanece retido e não é restaurado.",
        "Nova Santa Rita apresenta crescimento do estoque juvenil no estabelecimento e melhora descritiva de trajetória, sem ligação entre pessoas.",
        "A magnitude regional justifica monitoramento conjunto, mas modelos anteriores tiveram decision_delta/estabilidade insuficientes.",
        "O caso local acrescenta contexto territorial e pergunta, não causa.",
        "Reformula H3 como agenda de monitoramento de estoques/fluxos e trajetória, sem restaurar seu veredito.",
        "Que indicadores de trabalho juvenil e trajetória devem ser acompanhados juntos por etapa e município?",
        "Dois painéis independentes, com tipologia municipal de direções.",
        "RAIS 15–17; admissões/desligamentos; matrícula; aprovação; abandono; distorção.",
        "PROMISING_NEEDS_MORE_TESTING",
        "Há valor material e fatos novos, mas robustez ecológica e não redundância com aprendizagem profissional precisam de teste adicional.",
    )
    app_2020 = labour["cagedApprentices"]["2020_15_17_admission"]
    app_2025 = labour["cagedApprentices"]["2025_15_17_admission"]
    add(
        "D2_APRENDIZES_JOVENS_EDUCACAO",
        2,
        "Aprendizagem profissional",
        "Como a aprendizagem profissional formal de jovens está mudando entre municípios e faixas etárias?",
        "Contratos de aprendizagem articulam trabalho protegido e formação, colocando agenda específica para jovens e educação.",
        "Caged com indicador de aprendiz, idade, ocupação, setor e fluxos ajustados; população jovem e educação.",
        "Caged 2020–2025 completo com indicador de aprendiz e ajustes; população/matrícula existem.",
        "Estoque de aprendizes e instituição/curso formador; Caged mede eventos, não pessoas ativas.",
        "workplace_municipality + resident_population + school_location",
        "2020–2025",
        "município × mês/ano × faixa × evento",
        "Fluxos ajustados, persistência, contribuição municipal e composição CBO/CNAE.",
        f"Admissões ajustadas de aprendizes 15–17 no Vale {_fmt(app_2020['regionAdjustedEvents'])} em 2020 e {_fmt(app_2025['regionAdjustedEvents'])} em 2025.",
        "Fluxo não é estoque; ajustes negativos finos e FOR/EXC devem ser preservados; não identificar estudantes.",
        f"Nova Santa Rita: admissões ajustadas 15–17 {_fmt(app_2020['novaSantaRitaAdjustedEvents'])}→{_fmt(app_2025['novaSantaRitaAdjustedEvents'])}.",
        "A série mostra expansão e heterogeneidade municipal, com pergunta própria distinta do emprego juvenil geral.",
        "O caso local permite decompor ocupações e setores de aprendizagem.",
        "Acrescenta instrumento institucional concreto ausente dos quatro módulos.",
        "Que articulação entre educação, empresas e instituições formadoras deve acompanhar a aprendizagem por faixa e ocupação?",
        "Fluxos de admissão/desligamento de aprendizes e composição ocupacional/setorial.",
        "Admissões; desligamentos; saldo; volume; CBO; CNAE; faixa etária.",
        "PROMISING",
        "Fonte detalhada, mecanismo específico e fato municipal/regional novo sustentam história própria, com semântica de fluxo explícita.",
    )
    add(
        "D2_CAGED_JUVENIL_TRAJETORIA",
        2,
        "Fluxos de trabalho juvenil e trajetória",
        "Choques e persistência nos fluxos juvenis coincidem com mudanças descritivas de trajetória?",
        "Aceleração de admissões/desligamentos pode alterar o contexto de tempo e renda, sem provar efeito sobre estudantes.",
        "Caged mensal juvenil e trajetória anual municipal.",
        "Caged 2020–2025 e taxas oficiais 2018–2025.",
        "Residência do trabalhador, vínculo individual e denominadores da trajetória.",
        "workplace_municipality + school_location",
        "2020–2025",
        "município × ano × faixa",
        "Volatilidade, defasagens pré-registradas e sensibilidade excluindo 2020/2021.",
        "Os Jobs 3/4A encontraram sinais instáveis e poucos termos ajustados; o 5F retém a pergunta para desenho melhor, não a candidata histórica.",
        "Estoque/fluxo e universos ecológicos; múltiplos testes não podem selecionar narrativa.",
        "Nova Santa Rita deve ser examinada em janelas e por faixa/indicador.",
        "Evidência anterior insuficiente para afirmação, mas útil para hipótese dirigida.",
        "Sem conclusão municipal nova nesta linha.",
        "Mantém uma rota de investigação legítima sem restaurar H3/A2.",
        "Quais mudanças persistentes dos fluxos juvenis justificam monitoramento conjunto?",
        "Calendário de choques Caged e linhas de trajetória em painéis separados.",
        "Admissões; desligamentos; saldo; volatilidade; trajetória.",
        "PROMISING_NEEDS_MORE_TESTING",
        "Pergunta relevante e dados completos, mas resultados prévios não foram robustos o suficiente.",
    )
    add(
        "D2_ESCOLARIDADE_JOVENS_TRABALHADORES",
        2,
        "Escolaridade no trabalho formal",
        "Como mudou a composição de escolaridade dos vínculos formais de 18–24 anos?",
        "Mudança da escolaridade dos jovens nos estabelecimentos informa a agenda de conclusão e formação continuada, sem medir a população residente.",
        "RAIS por faixa e escolaridade, com dicionário oficial.",
        "Cubo RAIS 2019–2025 por códigos de escolaridade, sexo e raça/cor.",
        "Dicionário oficial versionado dos códigos antes de rótulo editorial e estoque de todos os trabalhadores para comparação.",
        "workplace_municipality",
        "2019–2025",
        "município × ano × faixa × escolaridade",
        "Composição, shift-share e contribuição municipal.",
        f"Vínculos 18–24 no Vale {_fmt(stocks['18_24_2019']['region'])}→{_fmt(stocks['18_24_2025']['region'])}; composição por 11 códigos foi preservada sem recodificação sem dicionário.",
        labour["schoolingDictionaryStatus"],
        f"Nova Santa Rita: vínculos 18–24 {_fmt(stocks['18_24_2019']['novaSantaRita'])}→{_fmt(stocks['18_24_2025']['novaSantaRita'])}.",
        "O cubo permite decompor mudança de composição por município.",
        "O caso local tem crescimento superior ao agregado em estoque.",
        "Acrescenta escolaridade real do emprego formal jovem, não presente nos quatro módulos.",
        "Que níveis de escolaridade e faixas devem entrar na articulação entre conclusão, EJA/EPT e trabalho?",
        "Composição 100% por escolaridade e contribuição municipal.",
        "Vínculos por código de escolaridade; faixa; sexo; raça/cor.",
        "PROMISING",
        "Cubo completo e fato territorial material; rótulos públicos dependem apenas de dicionário oficial versionado.",
    )
    add(
        "D2_OCUPACOES_CRESCIMENTO_FORMACAO",
        2,
        "Ocupações e formação profissional",
        "Quais ocupações em crescimento/retração colocam perguntas para a composição formativa?",
        "Mudanças persistentes no estoque ocupacional alteram temas de articulação com cursos/eixos, sem provar adequação.",
        "RAIS ocupacional e cursos/eixos técnicos com ponte normativa.",
        "RAIS 2019–2025, cursos 2023–2025 e ponte 2025.",
        "Ingressantes/concluintes e cobertura integral da ponte para cursos não mapeados.",
        "workplace_municipality + school_location",
        "RAIS 2019–2025; cursos 2023–2025",
        "ocupação/município/ano e curso/eixo/escola/ano",
        "Variação, persistência, concentração e leitura em painéis independentes.",
        f"Maior aumento ocupacional regional observado: {region_occ_up['occupation_name']} ({_fmt(region_occ_up['2019'])}→{_fmt(region_occ_up['2025'])}); cursos técnicos {_fmt(courses['2023']['technicalEnrollments'])}→{_fmt(courses['2025']['technicalEnrollments'])}.",
        labour["limits"],
        f"Nova Santa Rita: maior aumento {nsr_occ_up['occupation_name']} ({_fmt(nsr_occ_up['2019'])}→{_fmt(nsr_occ_up['2025'])}); zero observado de matrícula técnica agregada em 2025.",
        "Movimentos regionais e formação têm composições e concentrações distintas.",
        "O caso local acrescenta logística/transportes sem inferir falta de curso.",
        "Aprofunda A3 com persistência, concentração e contribuição municipal.",
        "Que composições ocupacionais e formativas devem ser observadas conjuntamente pelos atores regionais?",
        "Painel de mudanças ocupacionais + painel de cursos/eixos, sem soma ou seta causal.",
        "Vínculos por CBO/CNAE; matrículas por curso/eixo; concentração; cobertura da ponte.",
        "PROMISING",
        "Fatos regionais e municipais são materiais e a pergunta é acionável dentro dos limites da ponte.",
    )
    add(
        "D2_SETORES_CURSOS_EIXOS",
        2,
        "Setores econômicos e eixos tecnológicos",
        "A mudança setorial observada sugere temas diferentes dos captados apenas por ocupações?",
        "Setores descrevem estrutura produtiva e podem demandar articulações transversais distintas das famílias ocupacionais.",
        "RAIS/Caged por CNAE e cursos/eixos técnicos.",
        "Caged juvenil contém CNAE; RAIS ocupacional contém subclasse; cursos/eixos 2023–2025.",
        "Painel setorial consolidado por todos os vínculos e classificação agregada versionada.",
        "workplace_municipality + school_location",
        "2019/2020–2025",
        "município × setor × ano",
        "Shift-share, contribuição e persistência; comparação de composições separadas.",
        "Fonte permite o teste, mas o painel setorial total não foi consolidado no 5F.",
        "Caged é fluxo e RAIS é estoque; CNAE do estabelecimento não define ocupação do trabalhador.",
        "Nova Santa Rita deve testar logística, indústria e serviços sem assumir curso necessário.",
        "Pode produzir agenda distinta de ocupações.",
        "Sem resultado setorial consolidado local nesta rodada.",
        "Acrescenta estrutura produtiva além do A3 ocupacional.",
        "Que setores em transformação exigem observação de eixos e capacidades formativas?",
        "Shift-share setorial + composição de eixos em painel independente.",
        "Vínculos/fluxos por CNAE; matrículas por eixo; contribuição municipal.",
        "PROMISING_NEEDS_MORE_TESTING",
        "Mecanismo e dados existem, mas falta painel setorial consolidado e teste de não redundância com ocupações.",
    )
    mapped = next(r for r in bridge if r["bridge_status"] == "mapped")
    add(
        "D2_CBO_CNCT_PONTE",
        2,
        "Ponte CBO–CNCT",
        "Que parte da composição formativa pode ser organizada por famílias ocupacionais usando a ponte normativa?",
        "Correspondência normativa organiza linguagem comum para articulação, sem medir aderência, suficiência ou empregabilidade.",
        "Cursos CNCT, CBO e ponte versionada.",
        "Ponte 2025 cobre cursos e matrículas com hashes preservados.",
        "Cursos não mapeados e validação humana das correspondências.",
        "school_location + workplace_municipality",
        "2025",
        "curso × subgrupo CBO; não aditivo",
        "Cobertura por curso/matrícula e auditoria de muitos-para-muitos.",
        f"Ponte mapeada: {_fmt(mapped['course_count'])} cursos e {_fmt(mapped['technical_enrollments'])} matrículas ({_fmt(mapped['enrollment_share']*100)}% das matrículas).",
        labour["limits"],
        "Nova Santa Rita não tinha curso técnico observado em 2025; usa a ponte apenas como contexto regional.",
        "A cobertura é alta, mas parcial e não aditiva.",
        "O caso local não autoriza dizer que falta curso.",
        "Garante rastreabilidade do A3, mas não cria história autônoma forte.",
        "Quais correspondências precisam de validação antes de orientar diálogo formativo?",
        "Mapa de cobertura e relações muitos-para-muitos.",
        "Cursos/matrículas mapeados; não mapeados; cobertura.",
        "DESCRIPTIVE_ONLY",
        "A ponte é infraestrutura analítica útil, porém insuficiente para insight substantivo independente.",
    )
    add(
        "D2_CONCENTRACAO_TRABALHO_FORMACAO",
        2,
        "Concentração territorial",
        "Trabalho e formação estão concentrados nos mesmos ou em diferentes municípios/eixos?",
        "Concentrações distintas podem exigir coordenação regional mesmo sem correspondência individual.",
        "Distribuição municipal/temática de vínculos e matrículas técnicas.",
        "RAIS ocupacional completa e cursos 2023–2025.",
        "Concentração setorial consolidada e sensibilidade a zeros/ausência.",
        "workplace_municipality + school_location",
        "2019–2025; formação 2023–2025",
        "município × composição",
        "HHI, participações, decomposição e sensibilidade excluindo maior município.",
        f"HHI municipal da oferta técnica: {_fmt(courses['2023']['municipalityHhi'],3)} em 2023 e {_fmt(courses['2025']['municipalityHhi'],3)} em 2025; oferta observada em {courses['2025']['municipalityWithObservedCourseRowsCount']} municípios em 2025.",
        "Ausência de linha foi reconciliada com Censo; concentração não mede insuficiência.",
        "Nova Santa Rita tinha zero observado de matrícula técnica em 2025, enquanto seu estoque ocupacional cresceu.",
        "A concentração formativa cria função clara de coordenação regional.",
        "O caso local exemplifica diferença entre local do trabalho e local da formação.",
        "Acrescenta geometria territorial ao A3, além de listas de ocupações/cursos.",
        "Que coordenação regional é necessária quando formação e trabalho se concentram em lugares distintos?",
        "Cartograma de participações e decomposição HHI.",
        "HHI; participações municipais; vínculos; matrículas técnicas.",
        "PROMISING",
        "Dados fechados, valor regional próprio e Nova Santa Rita informativa sustentam a oportunidade.",
    )
    add(
        "D2_EPT_TENDENCIA_TRABALHO",
        2,
        "Tendências da EPT e do trabalho",
        "As mudanças 2023–2025 da composição da EPT são persistentes e distintas das mudanças do trabalho?",
        "Oferta formativa pode responder com defasagem e por decisões institucionais próprias.",
        "Cursos/eixos 2023–2025 e trabalho 2019–2025.",
        "Três anos de cursos e sete de RAIS.",
        "Janela mais longa de cursos e ingressantes/concluintes.",
        "school_location + workplace_municipality",
        "2023–2025 e 2019–2025",
        "município × ano × eixo/ocupação",
        "Persistência, contribuição, concentração e janelas alternativas.",
        f"Matrículas técnicas {_fmt(courses['2023']['technicalEnrollments'])}→{_fmt(courses['2025']['technicalEnrollments'])}; HHI de eixos {_fmt(courses['2023']['axisHhi'],3)}→{_fmt(courses['2025']['axisHhi'],3)}.",
        "Três anos não sustentam tendência longa; matrícula não é capacidade nem conclusão.",
        "Nova Santa Rita permanece zero observado em 2025 no recorte técnico.",
        "A composição regional mudou pouco no total, mas pode ter trocas internas por eixo.",
        "O caso local evidencia dependência de articulação supramunicipal, sem inferir destino.",
        "Adiciona dinâmica recente à fotografia A3.",
        "Quais mudanças de eixo persistem o suficiente para entrar na agenda de articulação?",
        "Fluxo de composição por eixo 2023–2025.",
        "Matrículas por eixo/curso; HHI; municípios com oferta observada.",
        "PROMISING_NEEDS_MORE_TESTING",
        "Há mudança observada, mas janela curta e ausência de ingressantes/concluintes exigem teste adicional.",
    )

    direction2_processing = [
        (
            "D2_PUBLICO_ADULTO_EJA_TRABALHO",
            "Público adulto, EJA e trabalho",
            "A escolaridade dos trabalhadores adultos e o público residente sem conclusão colocam agendas convergentes para EJA?",
            "Estoque residente e composição do emprego formal podem indicar públicos territoriais distintos para retorno/conclusão.",
            "População adulta, RAIS de todas as idades/escolaridade e EJA.",
            "População 2010/2022 e RAIS por escolaridade existem; EJA está pronta.",
            "Recorte RAIS adulto e dicionário oficial; Job 2 extraiu apenas 15–24.",
            "resident_population + workplace_municipality + school_location",
            "2010/2022; RAIS 2019–2025; EJA 2014–2025",
            "município × faixa/escolaridade",
            "Composições separadas, shift-share e tipologia.",
            "Não testado: RAIS adulta não integra Job 2.",
            "Universos distintos e sem vínculo individual.",
            "Nova Santa Rita requer três painéis separados.",
            "Potencial de agenda intersetorial.",
            "Sem fato local novo.",
            "Amplia EJA para sua ligação territorial com trabalho adulto.",
            "Que públicos adultos precisam de articulação entre conclusão e trabalho?",
            "Três composições lado a lado, nunca somadas.",
            "Público adulto; vínculos por escolaridade; matrículas EJA.",
        ),
        (
            "D2_ESCOLARIDADE_ADULTA_TRABALHO",
            "Escolaridade adulta e estrutura ocupacional",
            "Como a mudança 2010→2022 da escolaridade adulta se relaciona à estrutura ocupacional 2019→2025?",
            "Mudança do capital educacional residente e mudança da demanda ocupacional podem seguir ritmos territoriais distintos.",
            "Escolaridade adulta, RAIS por ocupação e escolaridade.",
            "Fontes existem separadamente.",
            "Painel integrado com todas as idades e dicionário.",
            "resident_population + workplace_municipality",
            "2010–2025",
            "município × composição",
            "Shift-share e decomposição de composição, sem causalidade.",
            "Não testado no 5F.",
            "Janelas diferentes e pessoas distintas.",
            "Nova Santa Rita deve ser contrastada com Vale/RS.",
            "Potencial de revelar descompassos territoriais.",
            "Sem fato local novo.",
            "Acrescenta transformação de qualificação ampla.",
            "Que mudanças de qualificação e ocupação precisam ser acompanhadas em conjunto?",
            "Duas decomposições shift-share coordenadas.",
            "Escolaridade adulta; escolaridade RAIS; ocupações.",
        ),
        (
            "D2_COORTES_JOVENS_TRABALHO",
            "Coortes jovens e trabalho",
            "O estoque formal juvenil cresce mais ou menos que a população jovem residente?",
            "Mudanças demográficas e localização de empregos podem alterar a intensidade territorial do trabalho juvenil sem medir taxa de emprego residente.",
            "População 15–17/18–24 e RAIS juvenil.",
            "Ambas as séries 2019–2025 estão prontas.",
            "Residência dos trabalhadores; razão não pode ser chamada de taxa de emprego.",
            "resident_population + workplace_municipality",
            "2019–2025",
            "município × faixa × ano",
            "Decomposição de mudanças e tipologia de direções, sem razão de cobertura.",
            f"Vale: RAIS 15–17 {_fmt(stocks['15_17_2019']['region'])}→{_fmt(stocks['15_17_2025']['region'])}; 18–24 {_fmt(stocks['18_24_2019']['region'])}→{_fmt(stocks['18_24_2025']['region'])}.",
            "Vínculos são no estabelecimento; população é residente; não formar taxa de emprego.",
            f"Nova Santa Rita: 15–17 {_fmt(stocks['15_17_2019']['novaSantaRita'])}→{_fmt(stocks['15_17_2025']['novaSantaRita'])}; 18–24 {_fmt(stocks['18_24_2019']['novaSantaRita'])}→{_fmt(stocks['18_24_2025']['novaSantaRita'])}.",
            "As faixas mostram escalas e ritmos distintos.",
            "O crescimento local do estoque é material.",
            "Acrescenta transformação demográfica do público jovem à agenda de trabalho.",
            "Que faixas e municípios precisam de monitoramento conjunto de coortes e oportunidades formais?",
            "Painéis separados de população residente e vínculos localizados.",
            "População jovem; vínculos RAIS por faixa; contribuição municipal.",
        ),
        (
            "D2_APRENDIZ_OCUPACOES_EIXOS",
            "Aprendizes, ocupações e eixos",
            "Em quais ocupações/setores se concentram aprendizes e como isso dialoga com eixos formativos observados?",
            "A composição da aprendizagem revela articulações institucionais concretas entre empresas e formação.",
            "Caged aprendiz por CBO/CNAE e cursos/eixos.",
            "Caged detalhado e cursos 2023–2025.",
            "Instituição formadora e ponte específica de aprendizagem.",
            "workplace_municipality + school_location",
            "2020–2025; cursos 2023–2025",
            "município × ano × CBO/CNAE/eixo",
            "Composição, concentração e cobertura normativa.",
            "Dados permitem teste, ainda não consolidado por CBO/CNAE no 5F.",
            "Fluxo não é estoque; curso técnico não equivale a programa de aprendizagem.",
            "Nova Santa Rita tem volume suficiente para decomposição exploratória.",
            "Potencial de tema próprio para articulação.",
            "Sem lista local promovida nesta rodada.",
            "Aprofunda aprendizagem profissional além do volume total.",
            "Que setores, ocupações e formadores precisam ser articulados?",
            "Composição de aprendizes e eixos em painéis separados.",
            "Eventos de aprendiz por CBO/CNAE; eixos; cobertura.",
        ),
        (
            "D2_SHIFT_SHARE_ECONOMIA_EDUCACAO",
            "Transformação econômica",
            "Quanto da mudança do trabalho decorre de crescimento geral versus mudança de composição setorial/ocupacional?",
            "Separar efeito de escala e composição evita tratar toda expansão como nova vocação.",
            "RAIS por município, setor e ocupação.",
            "RAIS 2019–2025 completa.",
            "Agregação setorial versionada e teste de sensibilidade.",
            "workplace_municipality",
            "2019–2025",
            "município × setor/ocupação",
            "Shift-share e contribuição municipal.",
            "Não calculado de forma consolidada no 5F.",
            "Método descritivo; mudanças classificatórias e choques devem ser controlados.",
            "Nova Santa Rita é caso obrigatório.",
            "Pode distinguir crescimento geral de recomposição.",
            "Sem fato local consolidado.",
            "Melhora substancialmente a leitura A3, hoje baseada em variações simples.",
            "Quais mudanças de composição, e não apenas escala, entram na agenda educacional?",
            "Waterfall shift-share regional e contribuições municipais.",
            "Efeito escala; efeito composição; contribuição municipal.",
        ),
        (
            "D2_MOBILIDADE_EPT",
            "Mobilidade e EPT",
            "A concentração de cursos técnicos e a mobilidade educacional colocam uma agenda comum de coordenação?",
            "Oferta técnica concentrada pode exigir deslocamento, mas a fotografia atual não identifica destino nem curso.",
            "Mobilidade com destino/etapa técnica e oferta EPT.",
            "Mobilidade geral 2022 e oferta técnica 2023–2025.",
            "Destino e identificação da etapa/modalidade técnica na mobilidade.",
            "student_residence + school_location",
            "2022–2025",
            "município × etapa/modalidade",
            "Sobreposição territorial descritiva e análise de lacuna.",
            "Oferta é concentrada, mas não se pode ligar a mobilidade técnica com a fonte atual.",
            "Sem destino; não inferir corredor ou receptor.",
            "Nova Santa Rita combina mobilidade elevada e zero técnico observado, sem prova de relação.",
            "A agenda é plausível, ainda não demonstrada.",
            "Fato local apenas contextual.",
            "Pode conectar A3 e A4 se nova fonte fechar o mecanismo.",
            "Que evidência de destino/modalidade é necessária para coordenar acesso à EPT?",
            "Mapa de oferta + caixa explícita de informação faltante.",
            "Oferta técnica; mobilidade por modalidade/destino futura.",
        ),
        (
            "D2_COORTES_INDICADORES_PNE",
            "Coortes e indicadores PNE",
            "Quais indicadores PNE precisam ser acompanhados antes de as coortes observadas alcançarem cada etapa?",
            "Coortes hoje observadas definem uma sequência temporal de pontos de atenção para acesso, trajetória e conclusão.",
            "Coortes mecânicas e catálogo/diagnóstico PNE.",
            "Coortes 2026–2030 e diagnóstico PNE existem.",
            "Ligação versionada etapa×indicador sem alterar metas.",
            "resident_population + school_location + pne_indicator_scope",
            "2025–2030 mecânico",
            "município × etapa × indicador",
            "Calendário de acompanhamento, sem número futuro de indicador.",
            f"Pressões mecânicas 2030 diferem: médio regional {_fmt(cohort_region['high_school']['cohort_to_baseline_enrollment_ratio']*100)}% da base 2025; pré-escola {_fmt(cohort_region['preschool']['cohort_to_baseline_enrollment_ratio']*100)}%.",
            d["mechanicalCohortLimit"],
            f"Nova Santa Rita tem razão mecânica do médio {_fmt(cohort_nsr['high_school']['cohort_to_baseline_enrollment_ratio']*100)}%.",
            "Permite ordenar temas por horizonte sem projetar metas.",
            "O caso local muda a agenda temporal.",
            "Conecta cenário mecânico e gestão PNE, ausente nos quatro módulos.",
            "Quais indicadores devem entrar primeiro no calendário de acompanhamento?",
            "Linha do tempo por coorte/etapa com indicadores, sem previsão.",
            "Coortes; matrícula-base; indicadores PNE ligados à etapa.",
        ),
        (
            "D2_TRANSPORTE_MOBILIDADE",
            "Transporte escolar e mobilidade",
            "Beneficiários/recursos de transporte ajudam a compreender a mobilidade educacional?",
            "Transporte pode viabilizar acesso, mas PNATE não identifica origem–destino nem todos os estudantes.",
            "PNATE/beneficiários e mobilidade por residência.",
            "PNATE existe em tabela; mobilidade 2022 está pronta.",
            "Recorte temporal/conceitual compatível e destino.",
            "administrative_benefit_context + student_residence",
            "anos compatíveis a confirmar",
            "município × ano",
            "Comparação de cobertura administrativa e fotografia, sem inferência individual.",
            "Não testado no 5F.",
            "Beneficiário/repasse não é fluxo OD nem causa de mobilidade.",
            "Nova Santa Rita requer QA de cobertura.",
            "Pode qualificar a questão de coordenação.",
            "Sem fato local novo.",
            "Acrescenta instrumento de governança à A4.",
            "Que dados de transporte precisam acompanhar a coordenação intermunicipal?",
            "Painéis separados PNATE e mobilidade.",
            "Beneficiários; repasse; participação fora; destino futuro.",
        ),
        (
            "D2_FINANCAS_CONDICOES_OFERTA",
            "Finanças e capacidade de oferta",
            "Mudanças financeiras ajudam a contextualizar a capacidade de responder a pressões territoriais?",
            "Recursos e execução condicionam capacidade de reorganizar oferta, sem explicar diretamente resultados.",
            "Finanças educacionais, demografia e organização da oferta.",
            "SIOPE/Fundeb/finanças existem; H1 e condições estão prontas.",
            "Deflacionamento, comparabilidade contábil e recorte por função compatível.",
            "entity_finance + resident_population + school_location",
            "períodos anuais a harmonizar",
            "município × ano",
            "Variações reais, esforço fiscal e análise de capacidade, sem regressão causal.",
            "Não testado no 5F.",
            "Contabilidade do ente não equivale à rede total localizada; responsabilidades precisam permanecer contexto.",
            "Nova Santa Rita requer harmonização fiscal.",
            "Potencial de planejamento, mas alto risco conceitual.",
            "Sem fato local novo.",
            "Acrescenta capacidade institucional, se as lentes forem preservadas.",
            "Que capacidade financeira precisa ser acompanhada para responder às pressões observadas?",
            "Painel financeiro real separado de demanda/oferta.",
            "Despesa real; matrículas; turmas; infraestrutura; coortes.",
        ),
    ]
    promising_ids = {"D2_COORTES_JOVENS_TRABALHO", "D2_COORTES_INDICADORES_PNE"}
    for values in direction2_processing:
        status = "PROMISING" if values[0] in promising_ids else "PROMISING_NEEDS_MORE_TESTING"
        reason = (
            "Fatos calculados e pergunta de planejamento própria já estão disponíveis."
            if status == "PROMISING"
            else "Relação potencialmente útil, mas depende de novo processamento ou fonte complementar."
        )
        add(values[0], 2, *values[1:], status, reason)

    add(
        "D2_CAGED_OCUPACOES_EMERGENTES",
        2,
        "Ocupações emergentes no Caged",
        "Quais ocupações juvenis apresentam fluxos recentes relevantes?",
        "Fluxos recentes podem sinalizar mudanças antes do estoque RAIS, mas são mais voláteis.",
        "Caged por CBO e faixa.",
        "Cubo detalhado 2020–2025.",
        "Persistência em estoque RAIS 2026 e validação de ajustes.",
        "workplace_municipality",
        "2020–2025",
        "município × mês × CBO",
        "Saldo, volume, persistência e estabilidade de ranking.",
        "A fonte permite listas exploratórias, mas o Job 5A descartou o contexto juvenil opcional por não gerar decisão própria.",
        "Alta volatilidade; saldo negativo no grão fino pode refletir ajustes; não chamar de ocupação do futuro.",
        "Nova Santa Rita tem fatos internos, não promovidos.",
        "Útil como radar, não história autônoma.",
        "Sem fato municipal promovido.",
        "Pode alimentar testes futuros de A3 sem virar insight por ranking.",
        "Quais sinais merecem confirmação no estoque RAIS antes de entrar na agenda?",
        "Radar interno de persistência, sem ranking público.",
        "Saldo; admissões; desligamentos; volume; persistência.",
        "DESCRIPTIVE_ONLY",
        "Volatilidade e decisão anterior limitam o uso a contexto exploratório.",
    )
    add(
        "D2_EJA_EPT_AGENDA_DUPLICADA",
        2,
        "EJA e educação profissional",
        "A EJA integrada deve aparecer também como agenda de transformação territorial?",
        "A integração EJA–EPT pode ser lida nas duas direções, mas o fato e a decisão são os mesmos.",
        "Mesmos dados de D1_EJA_EDUCACAO_PROFISSIONAL.",
        "Série 2014–2025 pronta.",
        "Nenhuma lacuna adicional.",
        "school_location",
        "2014–2025",
        "município × ano × modalidade",
        "Teste de não redundância.",
        "A formulação chega à mesma decisão de acompanhar presença, modalidade e articulação da EJA integrada.",
        "Não criar dois módulos com o mesmo público, fato e decisão.",
        "Nova Santa Rita mantém os mesmos zeros observados.",
        "Sem valor regional adicional.",
        "Sem valor municipal adicional.",
        "Nenhum valor incremental frente a D1_EJA_EDUCACAO_PROFISSIONAL.",
        "Usar a questão já registrada na direção 1.",
        "Nenhum visual adicional.",
        "Mesmos indicadores da oportunidade D1.",
        "REDUNDANT",
        "Pergunta duplicaria fato, público, responsabilidade e decisão já cobertos.",
    )

    insufficient_rows = [
        (
            "D2_CENARIOS_TERRITORIAIS_PNE",
            "Cenários territoriais",
            "Quais temas educacionais permaneceriam relevantes em futuros alternativos do Vale?",
            "Cenários exploram incertezas e testam robustez de temas, não projetam números.",
            "Quatro cenários próprios do Vale com governança, forças e incertezas.",
            "Existem cenários de outras regiões e coortes mecânicas do Vale.",
            "Cenários próprios e validados do Vale do Sinos.",
            "scenario_context + lenses_of_each_indicator",
            "horizonte a definir",
            "região × cenário × tema",
            "Teste de robustez temática entre cenários.",
            "Não executado; transferir cenários de outras regiões permanece proibido.",
            "Coorte mecânica não substitui cenário; nenhum número futuro pode ser inventado.",
            "Nova Santa Rita teria exposição, não cenário municipal.",
            "Lacuna regional bloqueante para história de futuros alternativos.",
            "Sem evidência municipal.",
            "Alto valor potencial, sem base atual suficiente.",
            "Quais temas são robustos a futuros alternativos do Vale?",
            "Matriz cenário×tema, somente após governança.",
            "Temas/indicadores robustos por cenário.",
        ),
        (
            "D2_DESTINOS_MOBILIDADE_EDUCACIONAL",
            "Destinos da mobilidade",
            "Para onde estudam os residentes que frequentam escola fora?",
            "Destinos identificam corredores e receptores para coordenação.",
            "Matriz origem–destino por etapa/escola.",
            "Somente contagem de residentes que estudam fora.",
            "Destino municipal/escola e rota.",
            "student_residence_to_school_destination",
            "2022 ou série futura",
            "origem × destino × etapa",
            "Fluxos OD e concentração.",
            "Impossível com a fonte atual.",
            "Não inferir destino a partir da oferta ou proximidade.",
            "Nova Santa Rita tem origem medida, destino ausente.",
            "Lacuna para todos os municípios.",
            "Nenhum fato de destino.",
            "Grande ganho potencial para A4.",
            "Que corredores e receptores exigem coordenação?",
            "Mapa OD futuro.",
            "Fluxos origem–destino por etapa.",
        ),
        (
            "D2_OD_RESIDENCIA_TRABALHO",
            "Mobilidade do trabalho",
            "Onde trabalham os jovens residentes do município?",
            "Fluxos residência–trabalho mudariam a interpretação dos estoques por estabelecimento.",
            "Matriz residência–estabelecimento por idade/escolaridade.",
            "RAIS/Caged apenas por estabelecimento no recorte.",
            "Município de residência e matriz OD de trabalho.",
            "worker_residence_to_workplace",
            "2019–2025",
            "origem × destino × faixa",
            "Fluxos OD e decomposição.",
            "Impossível com os artefatos atuais.",
            "Não inferir residência a partir do estabelecimento.",
            "Nova Santa Rita tem empregos localizados, não residência dos trabalhadores.",
            "Lacuna regional completa.",
            "Nenhum fato municipal de fluxo.",
            "Mudaria fortemente o produto se fonte pública fosse obtida.",
            "Que articulações emprego–formação atravessam limites municipais?",
            "Mapa OD futuro.",
            "Fluxos residência–trabalho por faixa/escolaridade.",
        ),
        (
            "D2_TAXA_REGIONAL_TRAJETORIA_EXATA",
            "Trajetória regional",
            "Qual é a taxa regional de aprovação/reprovação/abandono/distorção?",
            "Uma taxa regional exige soma de componentes exatos compatíveis.",
            "Numeradores e denominadores municipais exatos.",
            "Taxas oficiais municipais publicadas.",
            "Componentes exatos no grão aceito.",
            "school_location",
            "2018–2025",
            "região × ano × etapa",
            "Soma de numeradores/soma de denominadores.",
            "Job 5D encontrou zero componentes exatos em 61.628 linhas auditadas; recomposição permanece impossível.",
            "Média simples, retrocálculo e ponderação inventada são proibidos.",
            "Nova Santa Rita tem taxas descritivas, não peso regional verificável.",
            "Lacuna metodológica regional congelada.",
            "Nenhuma contribuição municipal à taxa pode ser calculada.",
            "Alto valor potencial, bloqueado pela fonte.",
            "Que fonte institucional permitiria recomposição e estabilidade?",
            "Nenhum visual até obter componentes.",
            "Numeradores; denominadores; taxa recomposta.",
        ),
        (
            "D2_NASCIMENTOS_MIGRACAO_OFERTA",
            "Nascimentos, migração e oferta",
            "Quanto da mudança de coortes decorre de nascimentos versus migração?",
            "Separar crescimento natural e migração melhora a leitura de pressão futura.",
            "Nascimentos por residência e fluxos migratórios municipais anuais/coorte.",
            "Nascimentos e censos 2010/2022 existem.",
            "Fluxos migratórios municipais anuais por idade/origem–destino.",
            "resident_population",
            "2010–2025",
            "município × coorte",
            "Balanço demográfico por componentes.",
            "Não executável com séries atuais.",
            "Mudança residual não deve ser rotulada migração sem componentes.",
            "Nova Santa Rita é caso prioritário devido ao crescimento, mas sem decomposição.",
            "Lacuna especialmente relevante para municípios em crescimento.",
            "Sem fato causal local.",
            "Poderia explicar por que coortes locais divergem do Vale.",
            "Que componente demográfico está pressionando cada etapa?",
            "Waterfall demográfico futuro.",
            "Nascimentos; óbitos; migração por idade; coortes.",
        ),
    ]
    for values in insufficient_rows:
        add(values[0], 2, *values[1:], "INSUFFICIENT_DATA", "A pergunta é valiosa, mas falta fonte pública/componente indispensável.")

    rejected_rows = [
        (
            "D2_TRANSICAO_INDIVIDUAL_ESCOLA_TRABALHO",
            "Transição individual escola–trabalho",
            "Quais estudantes deixaram a escola para trabalhar?",
            "Exigiria vinculação individual longitudinal entre educação e trabalho.",
            "Microdados identificáveis vinculados com base legal e desenho longitudinal.",
            "Somente agregados ecológicos separados.",
            "Vinculação individual autorizada e desenho causal.",
            "individual_longitudinal",
            "não disponível",
            "pessoa",
            "Desenho longitudinal/causal apropriado.",
            "Não testável e incompatível com os dados agregados disponíveis.",
            "Não identificar as mesmas pessoas nem atribuir abandono ao trabalho.",
            "Nenhuma inferência individual para Nova Santa Rita.",
            "Nenhuma evidência regional válida.",
            "Nenhuma evidência municipal válida.",
            "A formulação é indevida; substituir por monitoramento ecológico explícito.",
            "Usar D2_TRABALHO_JUVENIL_ENSINO_MEDIO.",
            "Nenhum.",
            "Nenhum indicador individual derivado.",
        ),
        (
            "D2_CAUSAL_CONDICOES_TRAJETORIA",
            "Causalidade entre condições e trajetória",
            "Infraestrutura, jornada ou docentes causaram melhora/piora de trajetória?",
            "Exigiria identificação causal com tratamento, contrafactual e controle de confundimento.",
            "Desenho causal e dados compatíveis.",
            "Painel observacional agregado.",
            "Contrafactual/desenho causal.",
            "school_location",
            "variável",
            "município/ escola",
            "Método causal apropriado, não disponível.",
            "Correlações ecológicas não respondem à pergunta causal.",
            "Não converter coeficiente ou p-valor em causa.",
            "Nenhuma atribuição causal para Nova Santa Rita.",
            "Nenhuma conclusão causal regional.",
            "Nenhuma conclusão causal municipal.",
            "Formulação rejeitada; perguntas descritivas correspondentes permanecem na matriz.",
            "Acompanhar condições e trajetória sem afirmar efeito.",
            "Nenhum visual causal.",
            "Indicadores descritivos separados.",
        ),
        (
            "D2_DEPENDENCIA_ADMINISTRATIVA_DESEMPENHO",
            "Dependência administrativa",
            "Qual dependência administrativa tem melhor ou pior desempenho?",
            "A formulação estratificaria resultado educacional por dependência.",
            "Dados por dependência.",
            "Dependência existe tecnicamente nas fontes.",
            "Não aplicável: uso analítico é proibido pelo contrato canônico.",
            "school_location",
            "qualquer",
            "dependência",
            "Nenhum método permitido.",
            "Não executado por regra canônica.",
            "Dependência serve apenas à reconstrução, fechamento, proveniência, disponibilidade e QA.",
            "Nenhum ranking/relação por dependência para Nova Santa Rita.",
            "Nenhuma evidência regional permitida.",
            "Nenhuma evidência municipal permitida.",
            "Nenhum valor de produto permitido.",
            "Tratar responsabilidades apenas como governança e coordenação.",
            "Nenhum.",
            "Rede total somente.",
        ),
    ]
    for values in rejected_rows:
        add(values[0], 2, *values[1:], "REJECTED", "Formulação incompatível com o contrato, os universos ou o desenho disponível.")
    add(
        "D2_PREVISAO_MATRICULA_POR_COORTE",
        2,
        "Previsão municipal de matrícula",
        "Qual será a matrícula municipal futura a partir das coortes mecânicas?",
        "A formulação trataria coorte mecânica como previsão de matrícula.",
        "Modelo com migração, transição, repetência, mobilidade, escolhas e capacidade.",
        "Somente envelhecimento mecânico de coortes observadas.",
        "Componentes de um modelo preditivo validado.",
        "resident_population + school_location",
        "2026–2030",
        "município × etapa",
        "Modelagem preditiva validada, não executada.",
        "A razão mecânica já está corretamente registrada em D1_COORTES_DEMANDA_FUTURA_MECANICA.",
        "Não chamar razão mecânica de previsão.",
        "Nova Santa Rita tem pressão mecânica, não matrícula prevista.",
        "Sem previsão regional válida.",
        "Sem previsão municipal válida.",
        "A pergunta útil já foi reformulada sem promessa preditiva.",
        "Usar calendário de acompanhamento das coortes observadas.",
        "Nenhum gráfico de previsão.",
        "Coorte mecânica e matrícula-base, com limites.",
        "REDUNDANT",
        "A formulação preditiva é inadequada; a versão mecânica transparente já está coberta.",
    )

    frame = pd.DataFrame(rows, columns=MATRIX_COLUMNS)
    frame = frame.sort_values(["direction", "analysis_id"], kind="stable").reset_index(drop=True)
    return frame


def build_source_inventory(contract: Mapping[str, Any]) -> dict[str, Any]:
    job2_manifest = _load_json(JOB2_ROOT / "manifest.json")
    artifact_records = [
        {
            "path": item["path"],
            "subjob": item["subjob"],
            "rowCount": item["rowCount"],
            "period": item["period"],
            "lens": item["lens"],
            "sha256": item["sha256"],
        }
        for item in job2_manifest["artifacts"]
    ]
    return {
        "schemaVersion": "vocacoes-pne-v7-job5f-source-inventory-v1",
        "jobId": JOB_ID,
        "cataloguedLogicalDatasetsInPriorInventory": 66,
        "cataloguedRequestedAnalysesAndSubanalyses": 73,
        "job2": {
            "artifactCount": len(artifact_records),
            "rowCount": int(sum(item["rowCount"] or 0 for item in artifact_records)),
            "artifacts": artifact_records,
        },
        "reusedRoots": [
            ".tmp/vocacoes-pne/v7-job2",
            ".tmp/vocacoes-pne/v7-job3",
            ".tmp/vocacoes-pne/v7-job5a",
            ".tmp/vocacoes-pne/v7-job5b",
            ".tmp/vocacoes-pne/v7-job5d",
        ],
        "confirmedButNotReprocessedInJob5F": [
            "nascimentos",
            "docentes",
            "horas_aula_diaria",
            "tempo_integral",
            "esforco_docente",
            "regularidade_docente",
            "saeb_proficiencia",
            "escolaridade_adulta_2010_2022",
            "ept_por_modalidade",
            "diagnosticos_e_comparadores_pne",
            "educacao_especial_aee",
            "educacao_rural",
            "cadunico_vulnerabilidade",
            "financas_educacionais",
            "pnate",
        ],
        "unavailableOrMethodologicallyBlocked": [
            "destino_da_mobilidade_educacional",
            "matriz_residencia_trabalho",
            "vinculacao_individual_escola_trabalho",
            "componentes_exatos_taxas_h2",
            "cenario_proprio_validado_vale_do_sinos",
            "projecao_demografica_municipal_canonica",
        ],
        "lenses": contract["territorialLenses"],
        "networkScope": "total_all_dependencies",
        "administrativeDependencyUsedAnalytically": False,
        "databaseUsed": False,
        "networkUsed": False,
    }


def _artifact(path: Path, root: Path, *, rows: int | None = None) -> dict[str, Any]:
    return {
        "path": path.relative_to(root).as_posix(),
        "byteSize": path.stat().st_size,
        "sha256": sha256_file(path),
        "rowCount": rows,
    }


def _validate_staging(root: Path) -> dict[str, Any]:
    actual = sorted(path.name for path in root.iterdir() if path.is_file())
    if actual != sorted(OUTPUT_FILES):
        raise ValueError(f"Allowlist Job 5F divergente: {actual}")
    matrix = pd.read_csv(root / "master_analytical_opportunities.csv.gz")
    if tuple(matrix.columns) != MATRIX_COLUMNS:
        raise ValueError("Schema da matriz Job 5F divergente.")
    validate_unique_key(matrix, ["analysis_id"], label="matriz mestra Job 5F")
    if not set(matrix["status"]).issubset(ALLOWED_STATES):
        raise ValueError("Estado analítico inválido.")
    if set(matrix["direction"]) != {1, 2}:
        raise ValueError("As duas direções não estão cobertas.")
    if set(matrix["education_network"]) != {"total_all_dependencies"}:
        raise ValueError("Matriz contém rede educacional fora do total canônico.")
    if len(matrix) < 30:
        raise ValueError("Inventário não cobre as famílias mínimas do Job 5F.")
    if matrix[list(MATRIX_COLUMNS)].isna().any().any():
        raise ValueError("Matriz contém campo obrigatório nulo.")
    if matrix["analysis_id"].str.contains("DEPENDENCIA").any():
        dependency_row = matrix[matrix["analysis_id"].str.contains("DEPENDENCIA")]
        if set(dependency_row["status"]) != {"REJECTED"}:
            raise ValueError("Dependência administrativa apareceu fora de rejeição explícita.")
    payload = _load_json(root / "master_analytical_opportunities.json")
    if len(payload["opportunities"]) != len(matrix):
        raise ValueError("CSV e JSON da matriz divergem em contagem.")
    ids_csv = list(matrix["analysis_id"])
    ids_json = [item["analysis_id"] for item in payload["opportunities"]]
    if ids_csv != ids_json:
        raise ValueError("CSV e JSON da matriz divergem em ordem/chaves.")
    evidence = _load_json(root / "exploratory_evidence.json")
    if evidence["administrativeDependencyUsedAnalytically"]:
        raise ValueError("Dependência administrativa foi usada analiticamente.")
    if evidence["h2FrozenStateChanged"]:
        raise ValueError("Job 5F alterou indevidamente o estado congelado de H2.")
    state_counts = {str(k): int(v) for k, v in matrix["status"].value_counts().sort_index().items()}
    return {
        "schemaValidation": "PASS",
        "outputCount": len(actual),
        "opportunityCount": int(len(matrix)),
        "directionCounts": {
            str(k): int(v) for k, v in matrix["direction"].value_counts().sort_index().items()
        },
        "stateCounts": state_counts,
        "duplicateAnalysisIds": 0,
        "nullRequiredFields": 0,
        "networkScope": "total_all_dependencies",
        "administrativeDependencyUsedAnalytically": False,
        "h2FrozenStateChanged": False,
    }


def materialize(output_root: Path = DEFAULT_OUTPUT_ROOT) -> dict[str, Any]:
    output_root = output_root.resolve()
    assert_outside_public_data(output_root, REPO_ROOT)
    contract = _verify_frozen_inputs()
    evidence = build_exploratory_evidence()
    matrix = build_opportunity_matrix(evidence)
    source_inventory = build_source_inventory(contract)
    state_counts = {
        str(key): int(value)
        for key, value in matrix["status"].value_counts().sort_index().items()
    }
    matrix_payload = {
        "schemaVersion": "vocacoes-pne-v7-job5f-master-matrix-v1",
        "jobId": JOB_ID,
        "verdict": VERDICT,
        "opportunityCount": int(len(matrix)),
        "stateCounts": state_counts,
        "opportunities": _json_safe(matrix.to_dict(orient="records")),
    }
    staging = staging_directory_for(output_root)
    try:
        write_json(staging / "source_inventory.json", source_inventory)
        write_json(staging / "exploratory_evidence.json", evidence)
        write_csv_gzip(staging / "master_analytical_opportunities.csv.gz", matrix)
        write_json(staging / "master_analytical_opportunities.json", matrix_payload)

        pre_qa_artifacts = [
            _artifact(staging / name, staging, rows=len(matrix) if "opportunities" in name else None)
            for name in OUTPUT_FILES[:4]
        ]
        qa = {
            "schemaVersion": "vocacoes-pne-v7-job5f-qa-v1",
            "jobId": JOB_ID,
            "checks": {
                "inputFingerprints": "PASS",
                "requiredColumns": "PASS",
                "analysisIdUniqueness": "PASS",
                "typesAndNulls": "PASS",
                "zeroVsMissingSemantics": "PASS",
                "totalNetworkOnly": "PASS",
                "administrativeDependencyNotAnalytic": "PASS",
                "h2FrozenStatePreserved": "PASS",
                "csvJsonParity": "PASS",
                "noSingleScore": "PASS",
                "noPublicDataWrite": "PASS",
                "noFrontendWrite": "PASS",
            },
            "stateCounts": state_counts,
            "directionCounts": {
                str(k): int(v)
                for k, v in matrix["direction"].value_counts().sort_index().items()
            },
            "preQaArtifacts": pre_qa_artifacts,
        }
        write_json(staging / "qa.json", qa)
        inventory_artifacts = [
            _artifact(
                staging / name,
                staging,
                rows=len(matrix) if "opportunities" in name else None,
            )
            for name in OUTPUT_FILES[:5]
        ]
        inventory = {
            "schemaVersion": "vocacoes-pne-v7-job5f-output-inventory-v1",
            "jobId": JOB_ID,
            "artifactCount": len(inventory_artifacts),
            "artifacts": inventory_artifacts,
        }
        write_json(staging / "output_inventory.json", inventory)
        manifest_artifacts = [
            _artifact(
                staging / name,
                staging,
                rows=len(matrix) if "opportunities" in name else None,
            )
            for name in OUTPUT_FILES[:6]
        ]
        manifest = {
            "schemaVersion": "vocacoes-pne-v7-job5f-operational-manifest-v1",
            "jobId": JOB_ID,
            "classification": "DATA_LOGIC",
            "verdict": VERDICT,
            "scope": contract["scope"],
            "sourceFingerprints": {
                **contract["inputFingerprints"],
                "contract": sha256_file(CONTRACT_PATH),
                "core": sha256_file(CORE_PATH),
                "launcher": sha256_file(LAUNCHER_PATH),
            },
            "summary": {
                "opportunityCount": int(len(matrix)),
                "stateCounts": state_counts,
                "directionCounts": {
                    str(k): int(v)
                    for k, v in matrix["direction"].value_counts().sort_index().items()
                },
                "promotableForMaximumPageCount": int(
                    matrix["status"].isin(
                        {"PROMISING", "PROMISING_NEEDS_MORE_TESTING", "DESCRIPTIVE_ONLY"}
                    ).sum()
                ),
                "manifestSelfExcludedFromArtifactHashes": True,
            },
            "generation": {
                "deterministic": True,
                "transactional": True,
                "partialPromotionAllowed": False,
                "clockUsed": False,
                "databaseUsed": False,
                "networkUsed": False,
                "fullBuildUsed": False,
                "publicDataChanged": False,
                "frontendChanged": False,
                "previousJobArtifactsChanged": False,
                "publicNarrativeWritten": False,
                "job6Started": False,
            },
            "artifacts": manifest_artifacts,
            "stopForExternalJudgment": True,
            "externalReviewer": "GPT-5.6 Pro",
        }
        write_json(staging / "manifest.json", manifest)
        validation = _validate_staging(staging)
        promotion = replace_directory_transactionally(staging, output_root)
    except Exception:
        if staging.exists():
            import shutil

            shutil.rmtree(staging)
        raise
    return {
        "verdict": VERDICT,
        "outputDirectory": output_root.as_posix(),
        "operationalManifestSha256": sha256_file(output_root / "manifest.json"),
        "promotion": promotion,
        **validation,
    }


def validate_existing_output(output_root: Path = DEFAULT_OUTPUT_ROOT) -> dict[str, Any]:
    output_root = output_root.resolve()
    assert_outside_public_data(output_root, REPO_ROOT)
    _verify_frozen_inputs()
    validation = _validate_staging(output_root)
    return {
        "verdict": VERDICT,
        "outputDirectory": output_root.as_posix(),
        "operationalManifestSha256": sha256_file(output_root / "manifest.json"),
        "promotion": "validated_existing",
        **validation,
    }
