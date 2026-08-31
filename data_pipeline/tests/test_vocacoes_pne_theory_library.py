from __future__ import annotations

import json
import socket
import sqlite3
import sys
from pathlib import Path

import pandas as pd
import pytest


DATA_PIPELINE_DIR = Path(__file__).resolve().parents[1]
if str(DATA_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_PIPELINE_DIR))

from src.vocacoes_pne_theory_library import (  # noqa: E402
    BOUNDARIES_FILE,
    COVERAGE_FILE,
    DEFAULT_OUTPUT_ROOT,
    EXPECTED_CONTRACT_SHA256,
    EXPECTED_CEILING_POLICY,
    EXPECTED_UNUSED_REFERENCE_IDS,
    EVIDENCE_FILE,
    GAP_QUESTIONS,
    IDENTITY_QUESTIONS,
    LIBRARY_FILE,
    QUESTION_IDS,
    QA_FILE,
    SUPPORTED_QUESTIONS,
    TheoryLibraryValidationError,
    blocked_external_io_guard,
    build_theory_package,
    sha256_file,
    validate_existing_output,
    verify_frozen_inputs,
    CONTRACT_PATH,
)


def test_frozen_inputs_and_contract_are_hash_gated() -> None:
    hashes = verify_frozen_inputs()
    assert sha256_file(CONTRACT_PATH) == EXPECTED_CONTRACT_SHA256
    assert hashes["contractSha256"] == EXPECTED_CONTRACT_SHA256
    assert hashes["publicDataTreeDigestSha256"]
    assert hashes["opusReconciliationSha256"]


def test_external_io_guard_blocks_network_and_sqlite() -> None:
    with blocked_external_io_guard():
        with pytest.raises(TheoryLibraryValidationError, match="conexão externa bloqueada"):
            socket.create_connection(("127.0.0.1", 9), timeout=0.01)
        with pytest.raises(TheoryLibraryValidationError, match="conexão externa bloqueada"):
            sqlite3.connect(":memory:")


def test_library_preserves_eight_questions_and_claim_ceilings() -> None:
    bundle = build_theory_package()
    mechanisms = bundle["library"]["mechanisms"]
    assert [item["question_id"] for item in mechanisms] == list(QUESTION_IDS)
    assert all(item["theory_can_override_aa2_terminal"] is False for item in mechanisms)
    assert {item["record_type"] for item in mechanisms} == {
        "THEORY_MECHANISM",
        "ACCOUNTING_IDENTITY",
        "INTERPRETATION_BOUNDARY",
    }
    assert {item["question_id"] for item in mechanisms if item["reference_coverage_state"] == "SUPPORTED_WITH_STRICT_TRANSFER_LIMIT"} == SUPPORTED_QUESTIONS
    assert {item["question_id"] for item in mechanisms if item["reference_coverage_state"] == "IDENTITY_NO_MECHANISM_REFERENCE_REQUIRED"} == IDENTITY_QUESTIONS
    assert {item["question_id"] for item in mechanisms if "GAP" in item["reference_coverage_state"]} == GAP_QUESTIONS


def test_negative_or_insufficient_aa2_findings_are_not_rescued() -> None:
    bundle = build_theory_package()
    mechanisms = {item["question_id"]: item for item in bundle["library"]["mechanisms"]}
    assert mechanisms["P3_SCHOOL_CONDITIONS_AND_TRAJECTORY"]["aa2_terminal_state"] == "NO_ROBUST_ASSOCIATION"
    assert mechanisms["P4_YOUTH_WORK_AND_HIGH_SCHOOL"]["aa2_terminal_state"] == "NO_ROBUST_ASSOCIATION"
    assert mechanisms["P6_ADULT_SCHOOLING_WORK_AND_EJA"]["aa2_terminal_state"] == "NO_ROBUST_ASSOCIATION"
    assert mechanisms["P7_RURALITY_INCLUSION_AND_ACCESS"]["aa2_terminal_state"] == "NO_ROBUST_ASSOCIATION"
    p8 = mechanisms["P8_FINANCING_OFFER_AND_CAPACITY"]
    assert p8["aa2_terminal_state"] == "INSUFFICIENT_DATA"
    assert p8["aa3_effective_claim_ceiling"] == "NOT_SUPPORTED_OR_UNAVAILABLE"
    assert p8["promotion_state"] == "BLOCKED_FROM_MANAGER_FACING"
    p4 = mechanisms["P4_YOUTH_WORK_AND_HIGH_SCHOOL"]
    p6 = mechanisms["P6_ADULT_SCHOOLING_WORK_AND_EJA"]
    assert p4["aa3_effective_claim_ceiling"] == (
        "NO_ROBUST_ASSOCIATION_LITERATURE_SUPPORTS_MONITORING_QUESTION_ONLY"
    )
    assert p6["aa3_effective_claim_ceiling"] == (
        "NO_ROBUST_ASSOCIATION_DESCRIPTIVE_DISTRIBUTIONS_ONLY"
    )
    assert p4["aa2_descriptive_basis"]["rule_passed"] is False
    assert p6["aa2_descriptive_basis"]["stable_primary_fit"] is None


def test_reference_usage_is_explicit_and_never_creates_local_effects() -> None:
    bundle = build_theory_package()
    references = bundle["library"]["references"]
    assert len(references) == 8
    unused = {item["refId"] for item in references if item["usageState"].startswith("UNUSED_")}
    assert unused == EXPECTED_UNUSED_REFERENCE_IDS
    assert all(item["localEffectAuthorized"] is False for item in references)
    assert all(item["municipalNumberAuthorized"] is False for item in references)
    for reference in references:
        if reference["refId"] in EXPECTED_UNUSED_REFERENCE_IDS:
            assert reference["usageConstraint"] == "NOT_USABLE_FOR_P3_P7_P8"
            assert set(reference["notUsableForQuestionIds"]) == GAP_QUESTIONS


def test_coverage_matrix_has_declared_grain_and_no_local_effect_authorization() -> None:
    coverage = build_theory_package()["coverage"]
    assert len(coverage) == 9
    assert coverage[["question_id", "reference_id"]].duplicated().sum() == 0
    assert set(coverage["question_id"]) == set(QUESTION_IDS)
    assert not coverage["local_effect_authorized"].astype(bool).any()
    assert not coverage["municipal_number_authorized"].astype(bool).any()


def test_every_mechanism_has_alternatives_boundary_and_forbidden_claims() -> None:
    mechanisms = build_theory_package()["library"]["mechanisms"]
    for mechanism in mechanisms:
        assert mechanism["alternative_explanations"]
        assert mechanism["falsification_or_boundary"]
        assert mechanism["transferability_notes"]
        assert len(mechanism["forbidden_interpretations"]) >= 3


def test_complementary_evidence_exposes_inputs_ceilings_and_specificity() -> None:
    bundle = build_theory_package()
    evidence = bundle["evidence"]
    assert evidence["inputHashCount"] == 11
    assert len(evidence["inputHashItems"]) == 11
    assert {
        item["inputHashKey"]: item["sha256OrContentDigest"]
        for item in evidence["inputHashItems"]
    } == bundle["input_hashes"]
    assert len(evidence["ceilingRows"]) == 8
    for row in evidence["ceilingRows"]:
        assert (
            row["aa2_claim_ceiling"],
            row["aa3_effective_claim_ceiling"],
        ) == EXPECTED_CEILING_POLICY[row["question_id"]]
        assert row["aa4_role"]
        assert row["ceilingRelation"] == (
            "NARROWER_OR_EQUAL_BY_EXPLICIT_QUESTION_POLICY"
        )
    assert len(evidence["reconciliationDecisionToRevisionCrosswalk"]) == 9
    assert {
        revision
        for item in evidence["reconciliationDecisionToRevisionCrosswalk"]
        for revision in item["revisionIds"]
    } == set("ABCDEFG")
    assert {
        item["question_id"]
        for item in evidence["technicalSpecificitySamples"]
    } == {
        "P1_CONTEXT_ADJUSTED_TRAJECTORY",
        "P4_YOUTH_WORK_AND_HIGH_SCHOOL",
        "P5_OCCUPATIONS_AND_EPT",
        "P6_ADULT_SCHOOLING_WORK_AND_EJA",
    }
    assert all(
        item["alternative_explanations"] and item["falsification_or_boundary"]
        for item in evidence["technicalSpecificitySamples"]
    )
    assert evidence["transactionalCommitPath"]["atomicPrimitive"] == "os.replace"
    assert evidence["transactionalCommitPath"]["failClosed"] is True
    assert evidence["inheritedLiteratureLimitation"][
        "newExternalResearchAuthorized"
    ] is False


def test_seven_frozen_mechanisms_are_reconciled_to_eight_question_records() -> None:
    library = build_theory_package()["library"]
    reconciliation = library["frozenMechanismReconciliation"]
    assert reconciliation["frozenSourceMechanismCount"] == 7
    assert reconciliation["aa3QuestionRecordCount"] == 8
    assert reconciliation["recordTypeCounts"] == {
        "THEORY_MECHANISM": 4,
        "ACCOUNTING_IDENTITY": 1,
        "INTERPRETATION_BOUNDARY": 3,
    }
    without_source = {
        item["question_id"]
        for item in reconciliation["questionRecordsWithoutSourceMechanism"]
    }
    assert without_source == {
        "P2_DEMOGRAPHY_ENROLLMENT_DECOMPOSITION",
        "P3_SCHOOL_CONDITIONS_AND_TRAJECTORY",
        "P7_RURALITY_INCLUSION_AND_ACCESS",
        "P8_FINANCING_OFFER_AND_CAPACITY",
    }


def test_p5_is_nomenclatural_cbo2_only() -> None:
    mechanisms = build_theory_package()["library"]["mechanisms"]
    p5 = next(item for item in mechanisms if item["question_id"] == "P5_OCCUPATIONS_AND_EPT")
    assert p5["aa3_effective_claim_ceiling"] == (
        "DESCRIPTIVE_NOMENCLATURE_CORRESPONDENCE_CBO_2_DIGIT_ONLY"
    )
    forbidden = " ".join(p5["forbidden_interpretations"]).lower()
    for token in ("demanda", "empreg", "egress", "ponte"):
        assert token in forbidden


def test_qa_is_fail_closed_and_counts_match_contract() -> None:
    qa = build_theory_package()["qa"]
    assert qa["failedCount"] == 0
    assert qa["counts"]["questionCount"] == 8
    assert qa["counts"]["referenceCount"] == 8
    assert qa["counts"]["usedReferenceCount"] == 5
    assert qa["counts"]["unusedReferenceCount"] == 3
    assert qa["counts"]["coverageMatrixRowCount"] == 9
    assert qa["counts"]["theoryOverrideAllowedCount"] == 0
    assert qa["counts"]["sourceMechanismCount"] == 7
    assert qa["counts"]["theoryMechanismRecordCount"] == 4
    assert qa["counts"]["accountingIdentityRecordCount"] == 1
    assert qa["counts"]["interpretationBoundaryRecordCount"] == 3
    check_ids = {check["checkId"] for check in qa["checks"]}
    assert {
        "AA3_CLASSIFICATION_DATA_LOGIC",
        "AA3_MUNICIPALITY_IDENTITY_TEXTUAL_7_DIGITS",
        "AA3_EDUCATION_SCOPE_TOTAL_ALL_DEPENDENCIES",
        "AA3_SOURCE_MECHANISM_MAPPING_COMPLETE",
        "AA3_P4_P6_NON_AFFIRMATIVE_CEILINGS_AND_AA2_BASIS",
        "AA3_EFFECTIVE_CLAIM_CEILING_NEVER_WIDENS_AA2",
        "AA3_PUBLIC_SENTINEL_DEVIATION_FORMALLY_RECONCILED",
        "AA3_OPUS_REAUDIT_ON_TRACK_AND_RESIDUAL_ACTION_BOUND",
    }.issubset(check_ids)


def test_materialized_package_contract_when_available() -> None:
    if not DEFAULT_OUTPUT_ROOT.exists():
        pytest.skip("Pacote AA3 ainda não materializado nesta execução em camadas.")
    manifest = validate_existing_output(DEFAULT_OUTPUT_ROOT)
    assert manifest["finalState"] == "AA3_COMPLETE_OPUS_REAUDIT_ON_TRACK"
    assert manifest["counts"]["questionCount"] == 8
    assert manifest["counts"]["referenceCount"] == 8
    verification = manifest["independentMaterializationVerification"]
    assert verification["state"] == "VERIFIED_IDENTICAL"
    assert verification["comparisonScope"] == (
        "PRE_NORMALIZATION_NON_MANIFEST_AND_POST_NORMALIZATION_FULL_TREE"
    )
    assert verification["processCount"] == 2
    assert len(verification["preNormalizationCandidateManifestDigests"]) == 2
    assert len(verification["preNormalizationCandidateTreeDigests"]) == 2
    assert verification["postNormalizationFinalTreeEqualityVerifiedByParent"] is True
    assert manifest["generation"]["manifestLast"] is True
    assert manifest["publicDataIntegrity"]["notWrittenByAa3"] is True
    assert manifest["opusReconciliation"]["aa4Allowed"] is True
    assert manifest["opusReconciliation"]["reAudit"]["verdict"] == "ON_TRACK"
    coverage = pd.read_csv(DEFAULT_OUTPUT_ROOT / COVERAGE_FILE, keep_default_na=False)
    assert len(coverage) == 9
    library = json.loads((DEFAULT_OUTPUT_ROOT / LIBRARY_FILE).read_text(encoding="utf-8"))
    boundaries = json.loads((DEFAULT_OUTPUT_ROOT / BOUNDARIES_FILE).read_text(encoding="utf-8"))
    qa = json.loads((DEFAULT_OUTPUT_ROOT / QA_FILE).read_text(encoding="utf-8"))
    evidence = json.loads((DEFAULT_OUTPUT_ROOT / EVIDENCE_FILE).read_text(encoding="utf-8"))
    assert library["claimPolicy"]["theoryCanOverrideAa2Terminal"] is False
    assert boundaries["theoryCanOverrideAa2Terminal"] is False
    assert qa["failedCount"] == 0
    determinism = evidence["determinismEvidence"]
    assert determinism["state"] == "PRE_NORMALIZATION_CANDIDATES_RECORDED"
    assert determinism["processCount"] == 2
    assert len(determinism["preNormalizationCandidateManifestDigests"]) == 2
    assert len(determinism["preNormalizationCandidateTreeDigests"]) == 2
    assert determinism["normalizedManifestFields"] == [
        "artifacts",
        "artifactSetDigestSha256",
        "runtime.pythonHashSeed",
        "runtime.pythonHashSeeds",
        "independentMaterializationVerification",
    ]
    gzip_payload = (DEFAULT_OUTPUT_ROOT / COVERAGE_FILE).read_bytes()
    assert gzip_payload[:3] == b"\x1f\x8b\x08"
    assert int.from_bytes(gzip_payload[4:8], "little") == 0


def test_aa3_report_and_opus_review_preserve_mandatory_guards() -> None:
    report = (
        DATA_PIPELINE_DIR.parent
        / "docs"
        / "RELATORIO_AA3_BIBLIOTECA_TEORICA_VOCACOES_PNE.md"
    ).read_text(encoding="utf-8")
    review = (
        DATA_PIPELINE_DIR.parent
        / "docs"
        / "REVISAO_OPUS_AA3_BIBLIOTECA_TEORICA_VOCACOES_PNE.md"
    ).read_text(encoding="utf-8")
    assert "P4 e P6 permanecem `NO_ROBUST_ASSOCIATION`" in report
    assert "`NOT_USABLE_FOR_P3_P7_P8`" in report
    assert "CBO de dois dígitos" in report
    assert "INVARIANT_WITHIN_AND_EQUAL_ACROSS_TWO_CANDIDATE_MATERIALIZATIONS" in report
    assert "AT_RISK" in review
    assert "Nenhum achado foi rejeitado" in review
