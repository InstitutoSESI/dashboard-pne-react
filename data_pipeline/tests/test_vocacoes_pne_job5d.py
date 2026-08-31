from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
import sys

import pandas as pd
import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_PIPELINE_DIR = REPO_ROOT / "data_pipeline"
if str(DATA_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_PIPELINE_DIR))

from src.vocacoes_pne_job2 import sha256_file  # noqa: E402
from src.vocacoes_pne_job5d import (  # noqa: E402
    CHECKPOINT_HASHES,
    COVERAGE_COLUMNS,
    DEFAULT_OUTPUT_ROOT,
    FINAL_STATE,
    NOVA_SANTA_RITA_ID,
    OUTPUT_FILES,
    RECOMPUTATION_QA_COLUMNS,
    _resolve_checkpoint,
    materialize,
    validate_existing_output,
)


@pytest.fixture(scope="module")
def job5d_output(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict, dict]:
    output = tmp_path_factory.mktemp("job5d") / "v7-job5d"
    first = materialize(output)
    first_hash = sha256_file(output / "MANIFEST_JOB5D_V7.json")
    second = materialize(output)
    assert second["promotion"] == "unchanged"
    assert sha256_file(output / "MANIFEST_JOB5D_V7.json") == first_hash
    return output, first, second


def test_frozen_job4b_job5a_job5b_and_job5c_inputs_remain_byte_identical() -> None:
    for path_text, expected in CHECKPOINT_HASHES.items():
        assert sha256_file(_resolve_checkpoint(path_text)) == expected


def test_materialization_is_transactional_repeatable_and_exactly_ten_outputs(
    job5d_output,
) -> None:
    output, first, second = job5d_output
    assert first["finalState"] == FINAL_STATE
    assert second["finalState"] == FINAL_STATE
    assert sorted(path.name for path in output.iterdir() if path.is_file()) == sorted(
        OUTPUT_FILES
    )
    checked = validate_existing_output(output)
    assert checked["schemaValidation"] == "PASS"
    assert checked["operationalManifestSha256"] == first["operationalManifestSha256"]


def test_coverage_preserves_full_rs_grain_and_negative_finding(job5d_output) -> None:
    output, _, _ = job5d_output
    coverage = pd.read_csv(
        output / "COBERTURA_DENOMINADORES_H2_V7.csv.gz",
        dtype={"municipality_ibge_code": "string"},
    )
    assert list(coverage.columns) == list(COVERAGE_COLUMNS)
    assert len(coverage) == 61_628
    assert coverage["municipality_ibge_code"].nunique() == 497
    assert coverage["municipality_ibge_code"].map(
        lambda value: bool(re.fullmatch(r"[0-9]{7}", value))
    ).all()
    assert not coverage.duplicated(
        ["municipality_ibge_code", "year", "stage", "indicator", "network_scope"]
    ).any()
    assert set(coverage["network_scope"]) == {"total_all_dependencies"}
    assert int(coverage["coverage_state"].eq("OFFICIAL_RATE_ONLY").sum()) == 61_597
    assert int(coverage["coverage_state"].eq("SOURCE_UNAVAILABLE").sum()) == 31
    assert not coverage["coverage_state"].isin(
        ["EXACT_COMPONENTS_AVAILABLE", "PARTIAL_COMPONENT_COVERAGE"]
    ).any()
    assert coverage["numerator"].isna().all()
    assert coverage["denominator"].isna().all()
    assert coverage["recomputed_rate_percent"].isna().all()
    assert coverage["zero_denominator"].isna().all()
    assert not coverage["aggregate_rate_eligible"].astype(bool).any()
    assert coverage["component_dependencies_present"].eq("[]").all()
    observed_zero = coverage["official_rate_percent"].eq(0)
    assert observed_zero.any()
    assert coverage.loc[observed_zero, "availability_state"].eq("observed_zero").all()
    performance = coverage[coverage["indicator"].isin(
        ["approval_rate_percent", "failure_rate_percent", "dropout_rate_percent"]
    )]
    distortion = coverage[
        coverage["indicator"].eq("age_grade_distortion_rate_percent")
    ]
    assert len(performance) == 47_712
    assert set(performance["year"]) == set(range(2018, 2026))
    assert len(distortion) == 13_916
    assert set(distortion["year"]) == set(range(2019, 2026))
    assert set(coverage["stage"]) == {
        "fundamental",
        "fundamental_anos_iniciais",
        "fundamental_anos_finais",
        "medio",
    }

    region = json.loads(
        (REPO_ROOT / "config" / "regions" / "rs.json").read_text(encoding="utf-8")
    )
    vale_codes = next(
        item["municipalityIbgeCodes"]
        for item in region["regions"]
        if item["slug"] == "vale-do-sinos"
    )
    vale = coverage[coverage["municipality_ibge_code"].isin(vale_codes)]
    assert len(vale) == 1_240
    assert vale["municipality_ibge_code"].nunique() == 10


def test_exact_panel_and_recomputation_qa_are_schema_only(job5d_output) -> None:
    output, _, _ = job5d_output
    exact = pd.read_csv(
        output / "PAINEL_COMPONENTES_EXATOS_H2_V7.csv.gz",
        dtype={"municipality_ibge_code": "string"},
    )
    qa = pd.read_csv(
        output / "QA_RECOMPUTACAO_TAXAS_H2_V7.csv.gz",
        dtype={"municipality_ibge_code": "string"},
    )
    assert exact.empty and list(exact.columns) == list(COVERAGE_COLUMNS)
    assert qa.empty and list(qa.columns) == list(RECOMPUTATION_QA_COLUMNS)


def test_dictionary_rejects_approximation_and_preserves_official_formulas(
    job5d_output,
) -> None:
    output, _, _ = job5d_output
    dictionary = json.loads(
        (output / "DICIONARIO_COMPONENTES_TAXAS_H2_V7.json").read_text(
            encoding="utf-8"
        )
    )
    definitions = dictionary["definitions"]
    assert definitions["approval_rate_percent"]["formula"] == (
        "APR / (APR + REP + ABA) * 100"
    )
    assert definitions["failure_rate_percent"]["formula"] == (
        "REP / (APR + REP + ABA) * 100"
    )
    assert definitions["dropout_rate_percent"]["formula"] == (
        "ABA / (APR + REP + ABA) * 100"
    )
    distortion = definitions["age_grade_distortion_rate_percent"]
    assert distortion["formula"] == "M_ks_i_sup / M_ks * 100"
    assert "cruzamento idade×série" in distortion["exclusions"][1]
    assert dictionary["reverseRoundingUsed"] is False
    assert dictionary["imputationUsed"] is False


def test_nova_santa_rita_and_stability_draft_fail_closed(job5d_output) -> None:
    output, _, _ = job5d_output
    nova = json.loads(
        (output / "NOVA_SANTA_RITA_COMPONENTES_H2_V7.json").read_text(
            encoding="utf-8"
        )
    )
    assert nova["municipalityIbgeCode"] == NOVA_SANTA_RITA_ID
    assert nova["coverageRowCount"] == 124
    assert nova["exactComponentRowCount"] == 0
    assert nova["officialRateOnlyRowCount"] + nova["sourceUnavailableRowCount"] == 124
    assert nova["trajectoryPatternSelected"] is False
    assert nova["c5Assessed"] is False
    assert nova["h2Approved"] is False
    draft = (output / "DRAFT_PRE_REGISTRO_ESTABILIDADE_H2_V7.yaml").read_text(
        encoding="utf-8"
    )
    assert "status: DRAFT_FOR_EXTERNAL_PREREGISTRATION_REVIEW" in draft
    assert "threshold: TBD_BY_EXTERNAL_PREREGISTRATION" in draft
    assert "applied_to_h2_in_this_job: false" in draft


def test_manifest_integrity_boundaries_and_launcher_check(job5d_output) -> None:
    output, _, _ = job5d_output
    manifest = json.loads(
        (output / "MANIFEST_JOB5D_V7.json").read_text(encoding="utf-8")
    )
    assert manifest["finalState"] == FINAL_STATE
    assert manifest["summary"]["outputCount"] == 10
    assert manifest["summary"]["coverageRowCount"] == 61_628
    assert manifest["summary"]["exactComponentRowCount"] == 0
    assert manifest["summary"]["recomputationQaRowCount"] == 0
    assert manifest["formulasAltered"] is False
    assert manifest["generation"]["databaseUsed"] is False
    assert manifest["generation"]["networkUsed"] is True
    assert manifest["generation"]["networkHosts"] == ["download.inep.gov.br"]
    assert manifest["generation"]["fullBuildUsed"] is False
    assert manifest["generation"]["publicDataChanged"] is False
    assert manifest["generation"]["job5bOrH2Rerun"] is False
    assert manifest["generation"]["job6Started"] is False
    assert manifest["generation"]["gate11Status"] == "BLOCKED"
    for artifact in manifest["artifacts"]:
        path = output / artifact["path"]
        assert path.stat().st_size == artifact["byteSize"]
        assert sha256_file(path) == artifact["sha256"]

    completed = subprocess.run(
        [
            sys.executable,
            str(DATA_PIPELINE_DIR / "scripts" / "run_vocacoes_pne_v7_job5d.py"),
            "--output-dir",
            str(output),
            "--check",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    summary = json.loads(completed.stdout)
    assert summary["schemaValidation"] == "PASS"
    assert summary["finalState"] == FINAL_STATE


def test_public_data_remains_unchanged() -> None:
    public_status = subprocess.run(
        ["git", "status", "--short", "--untracked-files=all", "--", "public/data"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert public_status == ""


def test_default_output_remains_outside_public_data() -> None:
    assert DEFAULT_OUTPUT_ROOT.resolve().is_relative_to((REPO_ROOT / ".tmp").resolve())
