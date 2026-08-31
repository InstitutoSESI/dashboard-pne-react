from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import re
import sys

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_PIPELINE_DIR = REPO_ROOT / "data_pipeline"
if str(DATA_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_PIPELINE_DIR))

from src.vocacoes_pne_job2 import directory_content_digest  # noqa: E402
from src.vocacoes_pne_job5j import (  # noqa: E402
    ALLOWED_CLASSIFICATIONS,
    DEFAULT_OUTPUT_ROOT,
    FINAL_STATE,
    INSIGHT_REQUIRED_FIELDS,
    INTERNAL_FILES,
    NSR_CODE,
    OUTPUT_FILES,
    PACKAGE_FILES,
    SOURCE_ROOTS,
    _source_inventory,
    validate_existing_output,
    write_package,
)


def _json(name: str) -> dict:
    return json.loads((DEFAULT_OUTPUT_ROOT / name).read_text(encoding="utf-8"))


def _csv(name: str) -> pd.DataFrame:
    return pd.read_csv(
        DEFAULT_OUTPUT_ROOT / name,
        dtype={"municipality_ibge_code": "string"},
        keep_default_na=False,
        na_values=["null"],
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_package_is_complete_curated_and_ready_with_limits() -> None:
    manifest = validate_existing_output()
    assert manifest["finalState"] == FINAL_STATE == (
        "JOB_5J_READY_WITH_EXPLICIT_LIMITS_FOR_EXTERNAL_JUDGMENT"
    )
    assert manifest["gate11"] == "CLOSED"
    assert manifest["packageFiles"] == list(PACKAGE_FILES)
    assert len(PACKAGE_FILES) == 12
    assert manifest["internalSupportingArtifacts"] == list(INTERNAL_FILES)
    assert {path.name for path in DEFAULT_OUTPUT_ROOT.iterdir() if path.is_file()} == set(
        OUTPUT_FILES
    )
    assert manifest["counts"]["candidateInsightCount"] == 8
    assert manifest["counts"]["testOrContrastCount"] == 33
    assert manifest["counts"]["alignedPanelRowCount"] == 170
    assert manifest["counts"]["heterogeneityRowCount"] == 90


def test_preregistration_covers_r1_r8_before_models() -> None:
    prereg = _json("PRE_ESPECIFICACAO_R1_R8_JOB5J.json")
    assert prereg["materializedBeforeJob5JModelExecution"] is True
    assert {item["relation_id"] for item in prereg["relations"]} == {
        f"R{index}" for index in range(1, 9)
    }
    for item in prereg["relations"]:
        assert item["primary_estimand"]
        assert item["primary_method"]
        assert item["robustness"]
        assert item["claim_ceiling"] in ALLOWED_CLASSIFICATIONS
        assert item["forbidden_claims"]


def test_insight_contracts_are_complete_and_never_auto_approve() -> None:
    catalog = _json("CATALOGO_INSIGHTS_CANDIDATOS_JOB5J.json")
    assert catalog["candidateInsightCount"] == len(catalog["insights"]) == 8
    assert catalog["automaticApproval"] is False
    assert catalog["externalJudgmentRequired"] is True
    expected = {
        "JOB5J_R1_DEMOGRAPHY_OFFER": "STRUCTURAL_CONTRAST",
        "JOB5J_R2_MOBILITY_TRAJECTORY": "NOT_SUPPORTED",
        "JOB5J_R3_YOUTH_WORK_TRAJECTORY": "NOT_SUPPORTED",
        "JOB5J_R4_OCCUPATIONS_EPT": "TERRITORIAL_MISMATCH",
        "JOB5J_R5_ADULT_SCHOOLING_EJA": "TERRITORIAL_MISMATCH",
        "JOB5J_R6_SOCIOECONOMIC_TRAJECTORY": "PLANNING_SIGNAL",
        "JOB5J_R7_RURALITY_PNATE": "PLANNING_SIGNAL",
        "JOB5J_R8_SPECIAL_AEE": "PLANNING_SIGNAL",
    }
    assert {item["insight_id"]: item["classification"] for item in catalog["insights"]} == expected
    for item in catalog["insights"]:
        assert INSIGHT_REQUIRED_FIELDS <= set(item)
        assert item["classification"] in ALLOWED_CLASSIFICATIONS
        assert item["external_judgment_required"] is True
        assert item["allowed_claims"] and item["forbidden_claims"]


def test_matrices_preserve_identity_lenses_and_noncausal_contract() -> None:
    tests = _csv("MATRIZ_RELACOES_TESTADAS_JOB5J.csv.gz")
    heterogeneity = _csv("MATRIZ_HETEROGENEIDADE_10_MUNICIPIOS_JOB5J.csv.gz")
    aligned = _csv("PAINEL_ANALITICO_ALINHADO_JOB5J.csv.gz")
    assert set(tests["relation_id"]) == {f"R{index}" for index in range(1, 9)}
    assert len(tests) == 33
    assert not tests["causal_interpretation_allowed"].astype(str).str.casefold().isin(
        {"true", "1"}
    ).any()
    assert not tests["same_person_link"].astype(str).str.casefold().isin(
        {"true", "1"}
    ).any()
    codes = set(heterogeneity["municipality_ibge_code"].astype(str))
    assert len(codes) == 10 and NSR_CODE in codes
    assert all(re.fullmatch(r"[0-9]{7}", code) for code in codes)
    assert aligned["network_scope"].eq("total_all_dependencies").all()
    assert aligned["administrative_dependency_role"].eq("qa_only").all()
    assert not aligned["x_lens"].eq("merged_population").any()


def test_multiplicity_models_and_negative_results_are_explicit() -> None:
    tests = _csv("MATRIZ_RELACOES_TESTADAS_JOB5J.csv.gz")
    with_p = tests[tests["p_value_raw"].notna()]
    assert with_p["p_value_bh"].notna().all()
    assert tests[tests["relation_id"].eq("R3")]["test_id"].nunique() == 8
    r3 = tests[tests["test_id"].isin(
        ["R3_FE_RAIS15_DROPOUT_CURRENT", "R3_FE_RAIS15_DROPOUT_WEIGHTED"]
    )].set_index("test_id")
    assert r3.loc["R3_FE_RAIS15_DROPOUT_CURRENT", "estimate"] < 0
    assert r3.loc["R3_FE_RAIS15_DROPOUT_WEIGHTED", "estimate"] > 0
    context = tests[tests["test_id"].eq("R7_PNATE_CONTEXT_ONLY")].iloc[0]
    assert pd.isna(context["estimate"])
    assert context["availability_state"] == "not_evaluable_cross_lens_period_contract"


def test_required_nova_santa_rita_anchors_and_states() -> None:
    catalog = _json("CATALOGO_INSIGHTS_CANDIDATOS_JOB5J.json")
    by_id = {item["insight_id"]: item for item in catalog["insights"]}
    r1 = by_id["JOB5J_R1_DEMOGRAPHY_OFFER"]["nova_santa_rita_result"]
    assert "+41" in r1 and "+2" in r1
    r3 = by_id["JOB5J_R3_YOUTH_WORK_TRAJECTORY"]["nova_santa_rita_result"]
    assert "104→172" in r3 and "1.117→1.638" in r3 and "174/219" in r3
    r4 = by_id["JOB5J_R4_OCCUPATIONS_EPT"]["main_effect_or_contrast"]
    assert "303→2.124" in r4 and "17→722" in r4 and "zero observado" in r4
    r5 = by_id["JOB5J_R5_ADULT_SCHOOLING_EJA"]["nova_santa_rita_result"]
    assert "6.068" in r5 and "298" in r5 and "4.447" in r5 and "82" in r5
    limits = _json("LIMITACOES_E_CLAIMS_JOB5J.json")
    assert any("PNATE 2026" in item for item in limits["globalLimits"])
    assert any("EPT zero observado" in item for item in limits["globalLimits"])


def test_apprenticeship_scale_eja_distance_and_zero_are_exact() -> None:
    models = _json("MODELOS_E_ROBUSTEZ_DETALHADOS_JOB5J.json")
    assert models["multipleTesting"]["automaticInsightApproval"] is False
    tests = _csv("MATRIZ_RELACOES_TESTADAS_JOB5J.csv.gz").set_index("test_id")
    assert math.isclose(
        tests.loc["R5_TERRITORIAL_DISTRIBUTION_TVD_FUNDAMENTAL", "estimate"],
        21.678314751208454,
        abs_tol=1e-12,
    )
    assert math.isclose(
        tests.loc["R5_TERRITORIAL_DISTRIBUTION_TVD_HIGH_SCHOOL", "estimate"],
        51.813592394463804,
        abs_tol=1e-12,
    )
    dossier = (
        DEFAULT_OUTPUT_ROOT / "DOSSIE_ANALITICO_NOVA_SANTA_RITA_JOB5J.md"
    ).read_text(encoding="utf-8")
    assert "174 / 219 = 79,452%" in dossier
    assert "EPT local com zero observado" in dossier


def test_inventory_hashes_and_manifest_are_complete() -> None:
    inventory = _json("INVENTARIO_E_HASHES_INPUTS_JOB5J.json")
    assert inventory["networkUsed"] is False
    assert inventory["databaseUsed"] is False
    for item in inventory["sources"]:
        path = Path(item["path"])
        if not path.is_absolute():
            path = REPO_ROOT / path
        assert path.is_file()
        assert path.stat().st_size == item["byte_size"]
        assert _sha256(path) == item["sha256"]
    manifest = _json("MANIFEST_JOB5J.json")
    declared = {item["path"]: item for item in manifest["artifacts"]}
    assert set(declared) == set(OUTPUT_FILES) - {"MANIFEST_JOB5J.json"}
    for name, item in declared.items():
        path = DEFAULT_OUTPUT_ROOT / name
        assert path.stat().st_size == item["byteSize"]
        assert _sha256(path) == item["sha256"]


def test_qa_side_effects_and_terminal_stop_are_fail_closed() -> None:
    qa = _json("QA_SUMMARY_JOB5J.json")
    assert qa["result"] == "PASS_WITH_EXPLICIT_LIMITS"
    assert qa["failedCount"] == 0
    assert all(item["status"] == "PASS" for item in qa["controls"])
    manifest = _json("MANIFEST_JOB5J.json")
    generation = manifest["generation"]
    for key in (
        "networkUsed",
        "databaseUsed",
        "newAcquisitionPerformed",
        "publicDataChanged",
        "frontendChanged",
        "navigationChanged",
        "fullBuildUsed",
        "publicationPerformed",
    ):
        assert generation[key] is False
    assert manifest["gate11"] == "CLOSED"
    assert manifest["job5KStarted"] is False
    assert manifest["formulasAltered"] == []


def test_generation_is_byte_reproducible(tmp_path: Path) -> None:
    inventory = _source_inventory()
    manifest = _json("MANIFEST_JOB5J.json")
    frozen = {
        key: directory_content_digest(path)
        for key, path in sorted(SOURCE_ROOTS.items())
    }
    public_digest = manifest["publicDataIntegrity"]["beforeTreeDigestSha256"]
    first = tmp_path / "first"
    second = tmp_path / "second"
    write_package(
        output_dir=first,
        inventory=inventory,
        frozen_integrity=frozen,
        public_data_digest=public_digest,
    )
    write_package(
        output_dir=second,
        inventory=inventory,
        frozen_integrity=frozen,
        public_data_digest=public_digest,
    )
    assert directory_content_digest(first) == directory_content_digest(second)
