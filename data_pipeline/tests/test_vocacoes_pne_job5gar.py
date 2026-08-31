from __future__ import annotations

import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd


REPO_ROOT_FOR_IMPORT = Path(__file__).resolve().parents[2]
DATA_PIPELINE_DIR = REPO_ROOT_FOR_IMPORT / "data_pipeline"
if str(DATA_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_PIPELINE_DIR))

from src.vocacoes_pne_job5gar import (  # noqa: E402
    CRITERION_STATUSES,
    DEFAULT_OUTPUT_ROOT,
    IRD_METRICS,
    ORIGINAL_FILES,
    OUTPUT_FILES,
    ZERO_OBSERVATION_VISUAL_EXCLUSIONS,
    validate_existing_output,
)


def _read(name: str) -> pd.DataFrame:
    return pd.read_csv(
        DEFAULT_OUTPUT_ROOT / name,
        dtype={"municipality_ibge_code": "string"},
        keep_default_na=False,
        na_values=["null"],
    )


def _truthy(series: pd.Series) -> pd.Series:
    return series.astype(str).str.casefold().isin({"true", "1"})


def test_job5gar_package_is_complete_and_ready() -> None:
    report = validate_existing_output()
    assert report["finalState"] == "JOB_5GA_R_READY_FOR_EXTERNAL_JUDGMENT"
    assert report["outputCount"] == 13
    assert report["originalArtifactCount"] == len(ORIGINAL_FILES) == 12
    assert {path.name for path in DEFAULT_OUTPUT_ROOT.iterdir()} == set(OUTPUT_FILES)


def test_pressure_nulls_incomplete_preschool_2030_and_recomputes_horizons() -> None:
    panel = _read("PAINEL_PRESSAO_MECANICA_COORTES_AUDITADO_V1_1.csv.gz")
    complete = _truthy(panel["cohort_window_complete"])
    affected = panel["stage"].eq("pre_escola") & panel["target_year"].eq(2030) & ~complete
    assert affected.sum() == 11
    assert panel.loc[affected, "availability_state"].eq(
        "PARTIAL_COHORT_NOT_YET_OBSERVED_AT_REFERENCE_YEAR"
    ).all()
    numeric = [
        "mechanical_cohort_size",
        "cohort_to_baseline_enrollment_ratio",
        "recomputed_ratio",
        "position_low_to_high_among_ten",
        "percentile_low_to_high_among_ten",
        "vale_municipal_median_ratio",
        "difference_from_vale_municipal_median_ratio",
    ]
    assert panel.loc[affected, numeric].isna().all().all()
    pre_school = panel[panel["stage"].eq("pre_escola")]
    assert set(pre_school["required_source_age_window_width"]) == {2}
    assert set(pre_school.loc[affected, "observed_source_age_window_width"]) == {1}
    assert pre_school["horizon_complete_end_year"].eq(2029).all()
    assert panel["cohort_lens"].eq("resident_population").all()
    assert panel["baseline_enrollment_lens"].eq("school_location").all()
    assert _truthy(panel["mixed_lens_ratio"]).all()
    assert not _truthy(panel["is_coverage_rate"]).any()
    assert not _truthy(panel["is_demand_forecast"]).any()
    assert not _truthy(panel["is_capacity_measure"]).any()


def test_comparators_require_ten_of_ten_and_had_ied_are_local_only() -> None:
    teachers = _read("PAINEL_DOCENTES_TURMAS_JORNADA_V1_1.csv.gz")
    conditions = _read("PAINEL_CONDICOES_ESCOLARES_TOTAL_V1_1.csv.gz")
    for panel in (teachers, conditions):
        eligible = _truthy(panel["regional_distribution_eligible"])
        assert eligible.equals(panel["observed_municipality_count"].eq(10))
        assert panel["expected_municipality_count"].eq(10).all()
        comparison = [
            "vale_municipal_median",
            "vale_quartile_1",
            "vale_quartile_3",
            "position_low_to_high_among_observed_municipalities",
            "percentile_low_to_high_among_ten",
            "difference_from_vale_municipal_median",
        ]
        assert panel.loc[~eligible, comparison].isna().all().all()
    had_ied = teachers["metric"].astype(str).str.startswith(("had_", "ied_"))
    assert set(teachers.loc[had_ied, "observed_municipality_count"]) == {2}
    assert teachers.loc[had_ied, "regional_comparison_classification"].eq(
        "LOCAL_DESCRIPTIVE_ONLY"
    ).all()


def test_ird_is_school_distribution_and_closes() -> None:
    panel = _read("PAINEL_CONDICOES_ESCOLARES_TOTAL_V1_1.csv.gz")
    ird = panel[panel["metric"].isin(IRD_METRICS)]
    assert ird["municipality_ibge_code"].nunique() == 10
    assert set(ird["year"]) == {2025}
    assert ird["counting_unit"].eq("school").all()
    closure = ird.groupby("municipality_ibge_code")["value"].sum()
    assert np.allclose(closure, 100, atol=0.2)


def test_regional_integral_share_uses_component_sums() -> None:
    panel = _read("PAINEL_TEMPO_INTEGRAL_REGIONAL_V1.csv.gz")
    exact = panel[_truthy(panel["regional_integral_share_eligible"])]
    assert len(exact) == 36
    assert set(exact["stage"]) == {"educacao_infantil", "fundamental", "medio"}
    recomputed = exact["regional_integral_enrollments"] / exact["regional_total_enrollments"] * 100
    assert np.allclose(recomputed, exact["regional_integral_share"], atol=1e-12)
    unavailable = panel[~_truthy(panel["regional_integral_share_eligible"])]
    assert len(unavailable) == 24
    assert set(unavailable["stage"]) == {"anos_iniciais", "anos_finais"}
    assert unavailable["regional_integral_share"].isna().all()


def test_trajectory_preserves_rates_and_contextualizes_2020_2021() -> None:
    panel = _read("PAINEL_TRAJETORIA_OFICIAL_DESCRITIVA_V1_1.csv.gz")
    atypical = panel["year"].isin([2020, 2021])
    assert panel.loc[atypical, "period_context_flag"].eq(
        "ATYPICAL_SERIES_DISCONTINUITY_REQUIRES_CONTEXT"
    ).all()
    assert not _truthy(panel.loc[atypical, "public_line_continuity_allowed"]).any()
    assert panel["regional_rate_value"].isna().all()
    assert "vale_median" not in panel
    assert "rs_median" not in panel
    assert panel["vale_distribution_public_label"].eq(
        "Mediana dos municípios do Vale do Sinos"
    ).all()
    assert panel["rs_distribution_public_label"].eq("Mediana dos municípios do RS").all()
    family = panel[panel["metric"].isin([
        "approval_rate_percent", "failure_rate_percent", "dropout_rate_percent"
    ])]
    closure = family.pivot_table(
        index=["municipality_ibge_code", "year", "stage"],
        columns="metric",
        values="value",
        aggfunc="first",
    )
    assert np.allclose(closure.sum(axis=1), 100, atol=1e-9)


def test_infant_objects_and_visual_allowlist_are_separated() -> None:
    infant = _read("PAINEL_EDUCACAO_INFANTIL_OBSERVADA_V1.csv.gz")
    assert len(infant) == 600
    assert "births" not in set(infant["metric"])
    assert infant["object_state"].eq("READY_FOR_INTERNAL_VISUAL_PROTOTYPE").all()
    assert infant["births_object_state"].eq("INSUFFICIENT_DATA").all()
    conditions = _read("PAINEL_CONDICOES_ESCOLARES_TOTAL_V1_1.csv.gz")
    for metric in ZERO_OBSERVATION_VISUAL_EXCLUSIONS:
        rows = conditions[conditions["metric"].eq(metric)]
        assert rows["metric_observation_count"].eq(0).all()
        assert not _truthy(rows["visual_metric_allowlisted"]).any()
    assert not _truthy(conditions["correlation_used_as_insight"]).any()


def test_matrix_has_specific_c1_c12_evidence_without_score() -> None:
    panel = _read("MATRIZ_OPORTUNIDADES_REAVALIADAS_JOB5GA_V1_1.csv.gz")
    assert len(panel) == 20
    assert panel["score"].isna().all()
    assert not _truthy(panel["automatic_approval"]).any()
    for criterion in range(1, 13):
        assert set(panel[f"c{criterion}_status"]).issubset(CRITERION_STATUSES)
        assert panel[f"c{criterion}_evidence"].nunique() == len(panel)
    for analysis_id in ("D1_TRAJETORIA_ESFORCO_DOCENTE", "D1_TRAJETORIA_HORAS_AULA"):
        row = panel[panel["analysis_id"].eq(analysis_id)].iloc[0]
        assert row["c7_status"] != "SUPPORTED"
        assert row["c9_status"] != "SUPPORTED"


def test_nova_santa_rita_has_six_groups_and_no_trajectory_duplication() -> None:
    payload = json.loads(
        (DEFAULT_OUTPUT_ROOT / "NOVA_SANTA_RITA_JOB5GA_V1_1.json").read_text(encoding="utf-8")
    )
    assert payload["municipalityIbgeCode"] == "4313375"
    assert payload["organizationGroupCount"] == 6
    assert payload["trajectoryUniqueRecordCount"] == 124
    trajectory = next(
        group for group in payload["evidenceGroups"] if group["id"] == "trajetoria_oficial"
    )
    records = [record for tab in trajectory["tabs"] for record in tab["series"]]
    grains = {
        (record["municipality_ibge_code"], record["year"], record["stage"], record["metric"])
        for record in records
    }
    assert len(records) == len(grains) == 124
    assert len(payload["compactSynthesis"]) == 6


def test_manifest_records_stop_and_forbidden_operations_absent() -> None:
    manifest = json.loads(
        (DEFAULT_OUTPUT_ROOT / "MANIFEST_JOB5GAR.json").read_text(encoding="utf-8")
    )
    generation = manifest["generation"]
    assert manifest["finalState"] == "JOB_5GA_R_READY_FOR_EXTERNAL_JUDGMENT"
    assert manifest["h2FrozenUnchanged"] is True
    assert manifest["stopForExternalJudgment"] is True
    assert generation["sourceJobArtifactsChanged"] is False
    assert generation["publicDataChanged"] is False
    assert generation["frontendChanged"] is False
    assert generation["networkUsed"] is False
    assert generation["databaseUsed"] is False
    assert generation["fullBuildUsed"] is False
    assert generation["compilerUsed"] is False
    assert generation["job5fReexecuted"] is False
    assert generation["job5gBStarted"] is False
    assert generation["job5hStarted"] is False
    assert generation["job6Started"] is False
