from __future__ import annotations

import json
from pathlib import Path
import socket
import sqlite3
import sys

import pandas as pd
import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_PIPELINE_ROOT = REPO_ROOT / "data_pipeline"
if str(DATA_PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(DATA_PIPELINE_ROOT))

from src.vocacoes_pne_advanced_panel import (
    AdvancedPanelValidationError,
    EXPECTED_PUBLIC_DATA_DIGEST,
    PACKAGE_FILES,
    REGIONAL_SOURCE_PATHS,
    STATE_SOURCE_ROOT,
    UNIQUE_KEY,
    _append_observation,
    _read_csv,
    blocked_external_io_guard,
    build_panel,
    build_source_inventory,
    materialize_twice_transactionally,
    validate_existing_output,
)


@pytest.fixture(scope="module")
def panel() -> pd.DataFrame:
    return build_panel()


def test_panel_has_stable_grain_and_exact_frozen_counts(panel: pd.DataFrame) -> None:
    assert len(panel) == 177_265
    assert panel["family_id"].nunique() == 6
    assert panel["metric_id"].nunique() == 96
    assert panel["municipality_ibge_code"].nunique() == 497
    assert not panel.duplicated(list(UNIQUE_KEY)).any()


def test_statewide_and_vale_coverage_remain_explicit(panel: pd.DataFrame) -> None:
    statewide = {
        "F1_EDUCATIONAL_TRAJECTORY_AND_CONDITIONS",
        "F2_DEMOGRAPHY_ENROLLMENT_AND_OFFER",
        "F5_ADULT_SCHOOLING_AND_EJA",
        "F6_VULNERABILITY_RURALITY_INCLUSION_AND_FINANCE",
    }
    for family_id in statewide:
        family = panel[panel["family_id"].eq(family_id)]
        assert family["municipality_ibge_code"].nunique() == 497

    for family_id in (
        "F3_YOUTH_WORK_AND_APPRENTICESHIP",
        "F4_OCCUPATIONS_SECTORS_AND_EPT",
    ):
        family = panel[panel["family_id"].eq(family_id)]
        assert family["municipality_ibge_code"].nunique() == 10

    for (_, _), metric in panel.groupby(["family_id", "metric_id"], sort=True):
        assert metric["coverage_scope"].nunique() == 1
        coverage_scope = metric["coverage_scope"].iat[0]
        assert metric["municipality_ibge_code"].nunique() == (
            497 if coverage_scope == "RS_497" else 10
        )
        assert metric["coverage_reason"].nunique() == 1
        assert metric["coverage_reason"].iat[0] == (
            "STATEWIDE_SOURCE_AVAILABLE"
            if coverage_scope == "RS_497"
            else "FROZEN_ANALYTICAL_SOURCE_RESTRICTED_TO_VALE_10"
        )


def test_availability_zero_and_lens_semantics(panel: pd.DataFrame) -> None:
    assert panel["availability_state"].value_counts().to_dict() == {
        "observed": 154_230,
        "observed_zero": 21_656,
        "unavailable": 1_379,
    }
    assert panel["unavailability_reason"].value_counts().to_dict() == {
        "VALUE_AVAILABLE": 175_886,
        "SOURCE_VALUE_MISSING": 653,
        "SOURCE_DECLARED_UNAVAILABLE": 570,
        "REFERENCE_COMPONENT_UNAVAILABLE_ZERO_BASE": 156,
    }
    observed = panel["availability_state"].isin(["observed", "observed_zero"])
    assert panel.loc[observed, "raw_value"].notna().all()
    assert panel.loc[~observed, "raw_value"].isna().all()
    assert panel.loc[panel["raw_value"].eq(0), "availability_state"].eq(
        "observed_zero"
    ).all()
    assert panel.loc[
        panel["family_id"].eq("F3_YOUTH_WORK_AND_APPRENTICESHIP"),
        "territorial_lens",
    ].eq("establishment_location_workplace").all()
    assert panel.loc[
        panel["metric_id"].eq("adult.fundamental_completion_share_percent"),
        "territorial_lens",
    ].eq("resident_population").all()


def test_nova_santa_rita_is_present_in_all_six_families(panel: pd.DataFrame) -> None:
    nsr = panel[panel["municipality_ibge_code"].eq("4313375")]
    assert nsr["municipality_name"].eq("Nova Santa Rita").all()
    assert nsr["family_id"].nunique() == 6
    assert {
        "education.approval_rate_percent",
        "demography.population_age_15_17",
        "labor.youth_rais.active_bonds",
        "education.ept_technical_enrollments",
        "adult.high_school_completion_share_percent",
        "finance.education_paid",
    }.issubset(set(nsr["metric_id"]))
    assert nsr.groupby("family_id").size().to_dict() == {
        "F1_EDUCATIONAL_TRAJECTORY_AND_CONDITIONS": 123,
        "F2_DEMOGRAPHY_ENROLLMENT_AND_OFFER": 128,
        "F3_YOUTH_WORK_AND_APPRENTICESHIP": 1_130,
        "F4_OCCUPATIONS_SECTORS_AND_EPT": 1_569,
        "F5_ADULT_SCHOOLING_AND_EJA": 41,
        "F6_VULNERABILITY_RURALITY_INCLUSION_AND_FINANCE": 383,
    }


def test_education_network_scope_is_total_without_dependency_strata(
    panel: pd.DataFrame,
) -> None:
    education = panel["metric_id"].str.startswith("education.")
    assert panel.loc[education, "network_scope"].eq("total_all_dependencies").all()
    assert not panel.loc[~education, "network_scope"].eq(
        "total_all_dependencies"
    ).any()
    assert not any(
        "dependency" in column and column != "network_scope"
        for column in panel.columns
    )


def test_rs_shift_share_reference_is_fenced_from_municipal_values(
    panel: pd.DataFrame,
) -> None:
    shift = panel["metric_id"].str.startswith("labor.shift_share.")
    referenced = panel["reference_scope"].ne("NO_EXTERNAL_REFERENCE")
    assert (referenced == shift).all()
    assert panel.loc[shift, "coverage_scope"].eq("VALE_10").all()
    assert panel.loc[shift, "reference_scope"].eq(
        "RS_SAME_VERSION_COMPONENT_BENCHMARK"
    ).all()
    assert panel.loc[shift, "aggregation_guard"].eq(
        "DO_NOT_AGGREGATE_AS_RS_TOTAL"
    ).all()
    assert set(
        panel.loc[shift, "source_ref"].str.rsplit("#", n=1).str[-1]
    ) == {
        "absolute_change",
        "reference_growth_effect",
        "industry_mix_effect",
        "local_differential_effect",
        "closure_residual",
    }
    assert not panel["source_ref"].str.contains(
        r"state_sector|reference_total|rs_total", case=False, regex=True
    ).any()


def test_rais_is_active_bond_stock_and_never_caged_flow(panel: pd.DataFrame) -> None:
    rais = panel[panel["family_id"].eq("F3_YOUTH_WORK_AND_APPRENTICESHIP")]
    assert rais["universe"].str.fullmatch(
        r"active_formal_bonds_age_(15_17|18_24)_at_31_12"
    ).all()
    assert rais["territorial_lens"].eq(
        "establishment_location_workplace"
    ).all()
    assert set(rais["unit"]) <= {
        "active_bonds",
        "percent",
        "months",
        "hours_per_week",
        "BRL_nominal",
    }
    f4_stock = panel[
        panel["family_id"].eq("F4_OCCUPATIONS_SECTORS_AND_EPT")
        & panel["metric_id"].str.startswith("labor.")
    ]
    assert len(f4_stock) == 22_141
    assert f4_stock["universe"].eq(
        "active_formal_bonds_all_ages_at_31_12"
    ).all()
    assert f4_stock["territorial_lens"].eq("workplace").all()
    assert f4_stock["unit"].eq("active_bonds").all()
    semantic_fields = panel[
        ["metric_id", "universe", "source_ref", "source_id", "formula_id"]
    ].astype(str)
    assert not semantic_fields.apply(
        lambda column: column.str.contains("caged", case=False, regex=False)
    ).any(axis=1).any()


def test_sparse_row_policy_distinguishes_absence_from_availability_states() -> None:
    contract = json.loads(
        (REPO_ROOT / "data_pipeline/contracts/vocacoes-pne-advanced-panel-v1.json")
        .read_text(encoding="utf-8")
    )
    observation = contract["observationContract"]
    assert observation["rowEmissionPolicy"] == "SOURCE_OBSERVATION_SPARSE"
    assert observation["absentRowMeaning"] == "row_absent_outside_source_or_grain"
    assert set(observation["absenceNeverImplies"]) == {
        "observed_zero",
        "unavailable",
        "suppressed",
        "not_applicable",
    }
    assert observation["sourceToOutputReconciliationRequired"] is True
    assert observation["temporalAuditRequired"] is True


def test_denominator_zero_is_normalized_to_null() -> None:
    rows: list[dict[str, object]] = []
    _append_observation(
        rows,
        names={"4313375": "Nova Santa Rita"},
        family_id="F3_YOUTH_WORK_AND_APPRENTICESHIP",
        code="4313375",
        period="2025",
        group="age_18_24",
        metric_id="labor.youth_rais.synthetic_ratio",
        value=0,
        unit="percent",
        source_state="observed",
        universe="active_formal_bonds_age_18_24_at_31_12",
        territorial_lens="establishment_location_workplace",
        network_scope="not_applicable",
        source_ref="synthetic#value",
        source_period="2025",
        method_state="synthetic_contract_probe",
        source_id="SYNTHETIC",
        numerator=0,
        denominator=0,
    )
    assert rows[0]["raw_value"] is None
    assert rows[0]["availability_state"] == "unavailable"
    assert rows[0]["unavailability_reason"] == "DENOMINATOR_ZERO"


def test_external_io_guard_blocks_socket_and_database_connections() -> None:
    with blocked_external_io_guard():
        with pytest.raises(AdvancedPanelValidationError):
            sqlite3.connect(":memory:")
        probe = socket.socket()
        try:
            with pytest.raises(AdvancedPanelValidationError):
                probe.connect(("127.0.0.1", 9))
        finally:
            probe.close()


def test_source_inventory_is_local_hashed_and_public_data_frozen() -> None:
    inventory = build_source_inventory(EXPECTED_PUBLIC_DATA_DIGEST)
    assert inventory["sourceCount"] == 518
    assert inventory["financeSourceCount"] == 497
    assert inventory["databaseUsed"] is False
    assert inventory["networkUsed"] is False
    assert inventory["publicDataTreeDigestSha256"] == EXPECTED_PUBLIC_DATA_DIGEST
    assert all(len(record["sha256"]) == 64 for record in inventory["records"])


def test_manual_source_row_spot_checks_match_emitted_panel(panel: pd.DataFrame) -> None:
    population = _read_csv(STATE_SOURCE_ROOT / "population_context.csv.gz")
    demographic = panel[
        panel["family_id"].eq("F2_DEMOGRAPHY_ENROLLMENT_AND_OFFER")
        & panel["metric_id"].str.startswith("demography.")
    ]
    assert len(population) == 3_976
    assert len(demographic) == len(population) * 5 == 19_880

    shift_source = _read_csv(
        REGIONAL_SOURCE_PATHS["JOB5GCR_SHIFT_SHARE_VALE_RS"]
    )
    shift_output = panel["metric_id"].str.startswith("labor.shift_share.").sum()
    assert len(shift_source) == 661
    assert shift_output == len(shift_source) * 5 == 3_305


def test_two_materializations_are_identical_and_transactional(tmp_path: Path) -> None:
    output_dir = tmp_path / "aa1"
    result = materialize_twice_transactionally(output_dir)
    assert result["independentMaterializationsEqual"] is True
    assert result["processIsolation"] == "TWO_FRESH_OPERATING_SYSTEM_PROCESSES"
    assert result["pythonHashSeeds"] == ["101", "202"]
    assert result["networkGuardEnabled"] is True
    assert result["databaseGuardEnabled"] is True
    assert result["loadedDatabaseClientModules"] == []
    assert result["loadedNetworkClientModules"] == []
    assert result["publicDataTreeDigestSha256"] == EXPECTED_PUBLIC_DATA_DIGEST
    assert sorted(path.name for path in output_dir.iterdir()) == sorted(PACKAGE_FILES)
    coverage = json.loads(
        (output_dir / "COBERTURA_FAMILIAS_AA1.json").read_text(encoding="utf-8")
    )
    assert coverage["rowEmissionPolicy"] == "SOURCE_OBSERVATION_SPARSE"
    assert coverage["panelFile"] == "PAINEL_ANALITICO_ESTADUAL_AA1.csv.gz"
    assert coverage["panelScopeLabel"] == "RS_ALIGNED_WITH_VALE_DEEP_DIVES"
    assert all(family["coverageScopes"] for family in coverage["families"])
    assert all(family["coverageReasons"] for family in coverage["families"])
    assert all(family["networkScopeCounts"] for family in coverage["families"])
    assert len(
        coverage["valeMunicipalityRegistry"]["municipalityIbgeCodes"]
    ) == 10

    grain = json.loads(
        (output_dir / "RECONCILIACAO_GRAO_AA1.json").read_text(encoding="utf-8")
    )
    assert grain["expectedTotalRows"] == 177_265
    assert grain["emittedTotalRows"] == 177_265
    assert grain["totalDeltaRows"] == 0
    assert grain["allSourceLedgersReconciled"] is True
    assert grain["allMetricsReconciled"] is True
    assert grain["metricCount"] == 96

    temporal = json.loads(
        (output_dir / "AUDITORIA_TEMPORAL_AA1.json").read_text(encoding="utf-8")
    )
    assert temporal["metricCount"] == 96
    assert temporal["unresolvedTemporalPatternCount"] == 0
    assert temporal["temporalDefinitionBreakCount"] == 0
    assert temporal["multipleDefinitionSignatureMetricCount"] == 23
    assert all(
        metric_id.startswith("labor.youth_rais.")
        for metric_id in temporal["multipleDefinitionSignatureMetricIds"]
    )
    assert sum(temporal["auditStateCounts"].values()) == 96
    assert {
        "SINGLE_PERIOD_SNAPSHOT",
        "CONTIGUOUS_ANNUAL_SERIES",
        "OFFICIAL_NON_ANNUAL_SOURCE_SCHEDULE",
        "ENDPOINT_ONLY_SOURCE_DESIGN",
        "INTERVAL_DECOMPOSITION",
        "REFERENCE_MONTH_SNAPSHOT",
    } == set(temporal["auditStateCounts"])

    aa2_gate = json.loads(
        (output_dir / "AA2_ENTRY_GATE_AA1.json").read_text(encoding="utf-8")
    )
    assert aa2_gate["modeAllowedBeforeGatePass"] == "PREREGISTRATION_ONLY"
    assert aa2_gate["resultInspectionAllowedBeforeGatePass"] is False
    assert aa2_gate["statewideInferencePolicy"] == {
        "allowedOnlyWhenCoverageScope": "RS_497",
        "vale10NeverRepresentsStatewide": True,
    }
    assert set(aa2_gate["failClosedRequiredRowFields"]) == {
        "coverage_scope",
        "coverage_reason",
        "reference_scope",
        "aggregation_guard",
        "unavailability_reason",
    }

    summary = validate_existing_output(output_dir, verify_sources=False)
    assert summary["state"] == "AA1_PANEL_READY_WITH_EXPLICIT_PARTIAL_COVERAGE"
    assert summary["rowCount"] == 177_265
    assert summary["familyCount"] == 6
    assert summary["metricCount"] == 96
    assert summary["municipalityCount"] == 497
    assert summary["artifactSetDigestSha256"] == result["artifactSetDigestSha256"]
    assert len(summary["sourceInventoryDigestSha256"]) == 64
    assert summary["publicDataUnchanged"] is True

    qa = json.loads(
        (output_dir / "QA_SUMMARY_AA1.json").read_text(encoding="utf-8")
    )
    assert qa["controlCount"] == 41
    census = qa["availabilityCensus"]
    assert census["unavailableRowsReconciled"] is True
    assert census["unavailabilityReasonCounts"] == {
        "DENOMINATOR_ZERO": 0,
        "REFERENCE_COMPONENT_UNAVAILABLE_ZERO_BASE": 156,
        "SOURCE_DECLARED_UNAVAILABLE": 570,
        "SOURCE_NOT_APPLICABLE": 0,
        "SOURCE_SUPPRESSED": 0,
        "SOURCE_VALUE_MISSING": 653,
        "VALUE_AVAILABLE": 175_886,
    }
    manifest = json.loads(
        (output_dir / "MANIFEST_AA1.json").read_text(encoding="utf-8")
    )
    assert manifest["analyticalContinuity"]["equal"] is True
    assert manifest["analyticalContinuity"][
        "preAddendumPanelSha256"
    ] == "1f500c731acecc52ceb2beaee1884a48607ec2f102220b956e5846cc3674fb0a"
