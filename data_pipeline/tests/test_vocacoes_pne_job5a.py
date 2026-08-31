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

from src.vocacoes_pne_job2 import safe_ratio, sha256_file  # noqa: E402
from src.vocacoes_pne_job5a import (  # noqa: E402
    JOB4B_HASHES,
    NOVA_SANTA_RITA_ID,
    normalize_dependency,
    normalize_stage,
    materialize,
    validate_existing_output,
)


@pytest.fixture(scope="module")
def job5a_output(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict, dict]:
    output = tmp_path_factory.mktemp("job5a") / "v7-job5a"
    first = materialize(output, write_release_manifest=False)
    first_manifest = sha256_file(output / "manifest.json")
    second = materialize(output, write_release_manifest=False)
    assert second["promotion"] == "unchanged"
    assert sha256_file(output / "manifest.json") == first_manifest
    return output, first, second


def test_canonical_normalization_and_zero_denominator() -> None:
    assert normalize_dependency("Total") == "total"
    assert normalize_dependency("Pública") == "publica"
    assert normalize_stage("taxa_distorcao_medio") == "medio"
    assert safe_ratio(1, 0) is None
    assert safe_ratio(0, 2, multiplier=100.0) == 0.0


def test_frozen_job4b_inputs_remain_byte_identical() -> None:
    for relative, expected in JOB4B_HASHES.items():
        assert sha256_file(REPO_ROOT / relative) == expected


def test_materialization_is_transactional_and_repeatable(job5a_output) -> None:
    output, first, second = job5a_output
    assert first["verdict"] == "JOB_5A_COMPLETED_FOR_EXTERNAL_JUDGMENT"
    assert second["verdict"] == first["verdict"]
    assert first["operationalManifestSha256"] == second["operationalManifestSha256"]
    checked = validate_existing_output(output)
    assert checked["operationalManifestSha256"] == first["operationalManifestSha256"]


def test_network_qa_uses_official_total_without_averaging(job5a_output) -> None:
    output, _, _ = job5a_output
    qa = pd.read_csv(
        output / "total_network_qa.csv.gz",
        dtype={"municipality_ibge_code": "string"},
    )
    assert len(qa) == 1240
    assert qa["municipality_ibge_code"].nunique() == 10
    assert NOVA_SANTA_RITA_ID in set(qa["municipality_ibge_code"])
    assert set(qa["qa_status"]) == {
        "OFFICIAL_TOTAL_ACCEPTED_COMPONENT_RECOMPOSITION_UNAVAILABLE"
    }
    assert qa["reconstructed_total_value"].isna().all()
    assert qa["absolute_difference"].isna().all()
    performance = qa[qa["indicator"] != "age_grade_distortion_rate_percent"]
    assert set(performance["closure_status"]) == {"closed"}
    assert performance["closure_residual_pp"].abs().max() <= 1e-9


def test_h2_preserves_grain_periods_and_external_judgment_state(job5a_output) -> None:
    output, _, _ = job5a_output
    h2 = pd.read_csv(
        output / "h2_factual_matrix.csv.gz",
        dtype={"municipality_ibge_code": "string"},
    )
    assert len(h2) == 1240
    assert not h2.duplicated(
        ["municipality_ibge_code", "year", "stage", "indicator"]
    ).any()
    distortion = h2[h2["indicator"] == "age_grade_distortion_rate_percent"]
    performance = h2[h2["indicator"] != "age_grade_distortion_rate_percent"]
    assert (distortion["year"].min(), distortion["year"].max()) == (2019, 2025)
    assert (performance["year"].min(), performance["year"].max()) == (2018, 2025)
    assert h2["vale_aggregate_rate_percent"].isna().all()
    assert h2["rs_aggregate_rate_percent"].isna().all()
    synthesis = json.loads((output / "h2_internal_synthesis.json").read_text("utf-8"))
    assert synthesis["resultState"] in {
        "PASS_RULE_MET_FOR_EXTERNAL_JUDGMENT",
        "PASS_RULE_NOT_MET",
        "NOT_EVALUABLE_DUE_TO_DATA_OR_QA_LIMIT",
    }
    assert synthesis["approvalDecisionReservedForExternalReviewer"] is True


def test_a4_recomputes_rates_and_keeps_destination_unavailable(job5a_output) -> None:
    output, _, _ = job5a_output
    a4 = pd.read_csv(
        output / "a4_factual_matrix.csv.gz",
        dtype={"municipality_ibge_code": "string"},
    )
    assert len(a4) == 30
    assert a4["municipality_ibge_code"].nunique() == 10
    assert a4["source_minus_recomputed_share_pp"].abs().max() <= 1e-9
    assert (a4["destination_available"].astype(str).str.lower() == "false").all()
    forbidden = {
        "destination_municipality",
        "route",
        "corridor",
        "receiving_school",
        "vacancy",
        "capacity",
        "responsible_administrative_dependency",
    }
    assert not (forbidden & set(a4.columns))
    nova = a4[a4["municipality_ibge_code"] == NOVA_SANTA_RITA_ID]
    assert set(nova["stage_universe"]) == {"total", "fundamental", "medio"}


def test_optional_a3_context_keeps_stock_flow_and_lenses_separate(job5a_output) -> None:
    output, _, _ = job5a_output
    context = json.loads(
        (output / "a3_optional_youth_context.json").read_text(encoding="utf-8")
    )
    assert context["createsCandidate"] is False
    assert context["sourceRoles"] == {
        "CAGED": "flow",
        "RAIS": "stock",
        "professionalEducation": "observed_total_school_supply",
    }
    assert context["resultState"] in {
        "USED_AS_OPTIONAL_A3_CONTEXT",
        "SILENTLY_DISCARDED",
    }
    assert context["approvalStateOfA3Changed"] is False
    assert context["youthWorkCardCreated"] is False
    assert context["maximumAbsoluteCagedMonthlyClosureDifference"] <= 1e-9


def test_manifest_counts_hashes_and_public_data_boundary(job5a_output) -> None:
    output, _, _ = job5a_output
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["summary"]["frozenInputCount"] == 61
    assert manifest["summary"]["networkQARowCount"] == 1240
    assert manifest["summary"]["h2RowCount"] == 1240
    assert manifest["summary"]["a4RowCount"] == 30
    assert manifest["summary"]["c1C12RowCount"] == 36
    assert manifest["generation"]["databaseUsed"] is False
    assert manifest["generation"]["networkUsed"] is False
    assert manifest["generation"]["publicDataChanged"] is False
    assert manifest["pilotGate11"] == "BLOCKED"
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
