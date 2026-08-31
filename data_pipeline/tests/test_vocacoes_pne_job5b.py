from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pandas as pd
import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_PIPELINE_DIR = REPO_ROOT / "data_pipeline"
if str(DATA_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_PIPELINE_DIR))

from src.vocacoes_pne_job2 import sha256_file  # noqa: E402
from src.vocacoes_pne_job5b import (  # noqa: E402
    JOB5A_HASHES,
    JOB5A_ROOT,
    NOVA_SANTA_RITA_ID,
    OUTPUT_FILES,
    RESULT_STATE,
    materialize,
    validate_existing_output,
)


@pytest.fixture(scope="module")
def job5b_output(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict, dict]:
    output = tmp_path_factory.mktemp("job5b") / "v7-job5b"
    first = materialize(output)
    first_hash = sha256_file(output / "manifest_job5b.json")
    second = materialize(output)
    assert second["promotion"] == "unchanged"
    assert sha256_file(output / "manifest_job5b.json") == first_hash
    return output, first, second


def test_job5a_h2_inputs_remain_byte_identical() -> None:
    for relative, expected in JOB5A_HASHES.items():
        assert sha256_file(JOB5A_ROOT / relative) == expected


def test_materialization_is_transactional_repeatable_and_exactly_ten_outputs(
    job5b_output,
) -> None:
    output, first, second = job5b_output
    assert first["verdict"] == "JOB_5B_COMPLETED_FOR_EXTERNAL_JUDGMENT"
    assert second["verdict"] == first["verdict"]
    assert sorted(path.name for path in output.iterdir() if path.is_file()) == sorted(
        OUTPUT_FILES
    )
    checked = validate_existing_output(output)
    assert checked["operationalManifestSha256"] == first["operationalManifestSha256"]


def test_family_is_integrated_once_and_nova_high_school_values_are_exact(job5b_output) -> None:
    output, _, _ = job5b_output
    family = pd.read_csv(
        output / "h2_family_level_matrix.csv.gz",
        dtype={"municipality_ibge_code": "string"},
    )
    assert len(family) == 40
    assert not family.duplicated(
        ["municipality_ibge_code", "stage", "recent_period", "performance_family"]
    ).any()
    assert "indicator" not in family.columns
    assert family["planning_question"].nunique() == len(family)
    assert all(
        row.municipality_name in row.planning_question
        and "2023 e 2025" in row.planning_question
        for row in family.itertuples(index=False)
    )
    nova = family[
        (family["municipality_ibge_code"] == NOVA_SANTA_RITA_ID)
        & (family["stage"] == "medio")
    ].iloc[0]
    assert [nova[f"approval_{year}_percent"] for year in (2023, 2024, 2025)] == [
        74.8,
        79.6,
        81.1,
    ]
    assert [nova[f"dropout_{year}_percent"] for year in (2023, 2024, 2025)] == [
        15.7,
        5.8,
        3.2,
    ]
    assert [nova[f"failure_{year}_percent"] for year in (2023, 2024, 2025)] == [
        9.5,
        14.6,
        15.7,
    ]
    assert nova["joint_direction_classification"] == (
        "APPROVAL_INCREASE__FAILURE_INCREASE__DROPOUT_DECREASE"
    )
    assert nova["maximum_absolute_closure_residual_pp"] <= 1e-9
    assert "Nova Santa Rita" in nova["planning_question"]
    assert "ensino médio" in nova["planning_question"]
    assert "74,8%" in nova["planning_question"]
    assert "15,7% para 3,2%" in nova["planning_question"]
    assert "mesmos estudantes" in nova["planning_question"]
    assert family["automatic_series_approval_allowed"].eq(False).all()


def test_distortion_is_re_evaluated_without_performance_closure(job5b_output) -> None:
    output, _, _ = job5b_output
    distortion = pd.read_csv(
        output / "h2_distortion_corrected_matrix.csv.gz",
        dtype={"municipality_ibge_code": "string"},
    )
    assert len(distortion) == 40
    assert set(distortion["performance_family_closure_status"]) == {"NOT_APPLICABLE"}
    assert distortion["series_inclusion_status"].notna().all()
    assert distortion["series_inclusion_or_exclusion_reason"].notna().all()
    assert distortion["planning_question"].nunique() == len(distortion)
    assert all(
        row.municipality_name in row.planning_question
        and "2023 e 2025" in row.planning_question
        for row in distortion.itertuples(index=False)
    )
    assert distortion["automatic_series_approval_allowed"].eq(False).all()
    nova_final = distortion[
        (distortion["municipality_ibge_code"] == NOVA_SANTA_RITA_ID)
        & (distortion["stage"] == "fundamental_anos_finais")
    ].iloc[0]
    assert [nova_final[f"value_{year}_percent"] for year in (2023, 2024, 2025)] == [
        26.3,
        24.2,
        22.7,
    ]
    assert nova_final["series_inclusion_status"] == (
        "INTERNAL_FACT_RETAINED_STABILITY_NOT_VERIFIABLE"
    )
    assert distortion["vale_rs_direction_claim_allowed"].eq(False).all()


def test_stability_fails_closed_and_c5_is_not_fully_met(job5b_output) -> None:
    output, _, _ = job5b_output
    qa = json.loads((output / "h2_stability_qa.json").read_text(encoding="utf-8"))
    assert qa["auditRuleDeclaredBeforeCorrectedResultReading"] is True
    assert qa["exactDenominatorFound"] is False
    assert qa["smallDenominatorRule"] == "SMALL_DENOMINATOR_RULE_UNAVAILABLE"
    assert qa["stabilityStatus"] == "STABILITY_NOT_VERIFIABLE"
    assert qa["c5FullyMet"] is False
    c12 = pd.read_csv(output / "h2_corrected_c1_c12_evidence.csv.gz")
    c5 = c12[c12["criterion_id"] == "C5"].iloc[0]
    assert c5["status"] == "NOT_FULLY_MET"
    synthesis = json.loads(
        (output / "h2_corrected_internal_synthesis.json").read_text(encoding="utf-8")
    )
    assert synthesis["resultState"] == RESULT_STATE
    assert synthesis["automaticSeriesApprovalAllowed"] is False
    assert synthesis["approvalDecisionMade"] is False


def test_manifest_hashes_boundaries_and_no_public_data_change(job5b_output) -> None:
    output, _, _ = job5b_output
    manifest = json.loads((output / "manifest_job5b.json").read_text(encoding="utf-8"))
    assert manifest["summary"]["outputCount"] == 10
    assert manifest["summary"]["familyRowCount"] == 40
    assert manifest["summary"]["distortionSeriesCount"] == 40
    assert manifest["summary"]["c1C12RowCount"] == 12
    assert manifest["generation"]["databaseUsed"] is False
    assert manifest["generation"]["networkUsed"] is False
    assert manifest["generation"]["fullBuildUsed"] is False
    assert manifest["generation"]["publicDataChanged"] is False
    assert manifest["generation"]["a4OrA3Rerun"] is False
    for artifact in manifest["artifacts"]:
        path = output / artifact["path"]
        assert path.stat().st_size == artifact["byteSize"]
        assert sha256_file(path) == artifact["sha256"]
    public_status = subprocess.run(
        ["git", "status", "--short", "--untracked-files=all", "--", "public/data"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert public_status == ""
