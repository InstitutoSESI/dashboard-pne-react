from __future__ import annotations

import copy
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

from src.vocacoes_pne_dossiers import (  # noqa: E402
    AGENDAS_FILE,
    CONTRACT_PATH,
    DEFAULT_OUTPUT_ROOT,
    DOSSIER_IDS,
    EXPECTED_CONTRACT_SHA256,
    FACTS_FILE,
    NSR_FILE,
    QA_FILE,
    SCENARIO_IDS,
    SCOPE_NSR,
    SCOPE_VALE,
    VALE_FILE,
    VISUALS_FILE,
    DossierValidationError,
    blocked_external_io_guard,
    build_dossier_package,
    _quality_checks,
    sha256_file,
    validate_existing_output,
    verify_frozen_inputs,
)


@pytest.fixture(scope="module")
def bundle() -> dict:
    return build_dossier_package()


def test_frozen_inputs_and_contract_are_hash_gated() -> None:
    hashes = verify_frozen_inputs()
    assert sha256_file(CONTRACT_PATH) == EXPECTED_CONTRACT_SHA256
    assert hashes["contractSha256"] == EXPECTED_CONTRACT_SHA256
    assert len(hashes) == 17


def test_external_io_guard_blocks_network_and_sqlite() -> None:
    with blocked_external_io_guard():
        with pytest.raises(DossierValidationError, match="conexão externa bloqueada"):
            socket.create_connection(("127.0.0.1", 9), timeout=0.01)
        with pytest.raises(DossierValidationError, match="conexão externa bloqueada"):
            sqlite3.connect(":memory:")


def test_exactly_five_bidirectional_dossiers_per_scope(bundle: dict) -> None:
    for scope_key, scope_id in (("vale", SCOPE_VALE), ("nsr", SCOPE_NSR)):
        payload = bundle[scope_key]
        assert payload["scope"]["scopeId"] == scope_id
        assert payload["scope"]["selectedMunicipalityContainedInRegion"] is True
        assert [item["dossierId"] for item in payload["dossiers"]] == list(DOSSIER_IDS)
        assert all("pneToTerritory" in item for item in payload["dossiers"])
        assert all("territoryToPne" in item for item in payload["dossiers"])


def test_p4_and_p6_remain_non_robust_and_coefficients_collapsed(bundle: dict) -> None:
    for payload in (bundle["vale"], bundle["nsr"]):
        selected = [
            item
            for item in payload["dossiers"]
            if item["primaryQuestionId"]
            in {
                "P4_YOUTH_WORK_AND_HIGH_SCHOOL",
                "P6_ADULT_SCHOOLING_WORK_AND_EJA",
            }
        ]
        assert len(selected) == 2
        for item in selected:
            assert "NO_ROBUST_ASSOCIATION" in item["relationshipState"]
            assert item["technicalEvidence"]["terminalState"] == "NO_ROBUST_ASSOCIATION"
            assert item["technicalEvidence"]["standaloneCoefficientAllowed"] is False
            assert item["technicalEvidence"]["displayMode"] == "COLLAPSED_TECHNICAL_NOTE"


def test_demographic_accounting_identity_closes_exactly(bundle: dict) -> None:
    facts = bundle["facts"].set_index("fact_id")
    for tag in ("NSR", "VALE"):
        total = facts.loc[f"F_D2_{tag}_HS_ENROLL_CHANGE_2018_2025", "absolute_change"]
        components = sum(
            facts.loc[f"F_D2_{tag}_{suffix}_2018_2025", "effect_estimate"]
            for suffix in ("POP_COMPONENT", "RELATION_COMPONENT")
        )
        assert total == pytest.approx(components, abs=1e-9)
    assert all(
        "migração" in next(
            item
            for item in payload["dossiers"]
            if item["dossierId"] == "D2_DEMOGRAPHY_AND_NETWORK"
        )["forbiddenConclusion"]
        for payload in (bundle["vale"], bundle["nsr"])
    )


def test_p5_is_nomenclatural_only_and_p8_is_blocked(bundle: dict) -> None:
    for payload in (bundle["vale"], bundle["nsr"]):
        p5 = next(
            item
            for item in payload["dossiers"]
            if item["dossierId"] == "D4_ECONOMIC_TRANSFORMATION_AND_EPT"
        )
        assert "CBO_2_DIGIT_ONLY" in p5["claimCeiling"]
        forbidden = p5["forbiddenConclusion"].lower()
        assert "demanda" in forbidden and "empreg" in forbidden
        assert payload["blockedManagerFacingRelations"][0]["questionId"] == (
            "P8_FINANCING_OFFER_AND_CAPACITY"
        )
        assert payload["blockedManagerFacingRelations"][0]["terminalState"] == (
            "INSUFFICIENT_DATA"
        )


def test_social_context_is_counts_only_and_not_tested(bundle: dict) -> None:
    for payload in (bundle["vale"], bundle["nsr"]):
        social = payload["transversalContext"]["socialContext"]
        assert social["terminalState"] == "RELATIONSHIP_NOT_TESTED_IN_AA2"
        assert social["prevalenceAllowed"] is False
        assert social["causalInterpretationAllowed"] is False


def test_zero_null_and_not_applicable_remain_distinct(bundle: dict) -> None:
    facts: pd.DataFrame = bundle["facts"]
    zeros = facts.loc[facts["availability_state_start"].eq("observed_zero")]
    assert not zeros.empty
    assert zeros["value_start"].eq(0).all()
    zero_denominator = facts.loc[
        facts["percent_change_state"].eq("NOT_APPLICABLE_ZERO_START")
    ]
    assert not zero_denominator.empty
    assert zero_denominator["percent_change"].isna().all()


def test_scenarios_are_conditional_and_non_interchangeable(bundle: dict) -> None:
    scenarios = bundle["scenarios"]
    assert [item["scenarioId"] for item in scenarios["scenarios"]] == list(
        SCENARIO_IDS
    )
    assert scenarios["futureNumericProjectionAllowed"] is False
    assert scenarios["scenariosAreMutuallyNonInterchangeable"] is True
    assert scenarios["aa5MayReduceBelowAa4Minimum"] is False
    assert len({item["decisionDomain"] for item in scenarios["scenarios"]}) == 3
    assert len(
        {tuple(item["primaryIndicatorFamilies"]) for item in scenarios["scenarios"]}
    ) == 3
    assert all(
        item["scenarioType"] == "CONDITIONAL_NOT_FORECAST"
        for item in scenarios["scenarios"]
    )


def test_agendas_have_responsibility_baseline_trigger_and_cadence(bundle: dict) -> None:
    agendas = bundle["agendas"]["agendas"]
    assert len(agendas) == 5
    required = {
        "observedCondition",
        "exposedPopulation",
        "educationStage",
        "territoryExposed",
        "concreteAction",
        "responsibilityLevel",
        "leadResponsibility",
        "contributors",
        "indicators",
        "baselineFactIds",
        "triggerDefinition",
        "cadence",
        "strengthenIf",
        "weakenIf",
    }
    assert all(required.issubset(item) for item in agendas)
    assert all(all(item[field] for field in required) for item in agendas)
    assert all(
        item["responsibilityLevel"] in {"municipal", "regional/shared", "external"}
        for item in agendas
    )
    assert all(item["sharedAcrossScopes"] is True for item in agendas)
    assert all(
        {variant["scopeId"] for variant in item["scopeVariants"]}
        == {SCOPE_NSR, SCOPE_VALE}
        for item in agendas
    )


def test_visual_contracts_are_question_first_and_honest(bundle: dict) -> None:
    visuals = bundle["visuals"]["visuals"]
    assert len(visuals) == 14
    assert all(item["question"] and item["takeaway"] for item in visuals)
    assert all(item["palette"]["rootColorCount"] <= 2 for item in visuals)
    assert all(item["nonColorDistinction"] for item in visuals)
    assert not any("SCATTER" in item["recommendedForm"] for item in visuals)
    p4 = [item for item in visuals if item["dossierId"] == "D3_YOUTH_WORK_AND_HIGH_SCHOOL"]
    assert all(item["recommendedForm"] == "SEPARATE_UNIT_START_END_BARS" for item in p4)
    assert all(len(item["units"]) == 2 for item in p4)
    d5 = [item for item in visuals if item["dossierId"] == "D5_ADULT_SCHOOLING_WORK_AND_EJA"]
    assert all(len(item["factIds"]) == 24 for item in d5)
    d1 = [item for item in visuals if item["dossierId"] == "D1_CONTEXT_AND_TRAJECTORY"]
    assert all("NO_ROBUST_ASSOCIATION" in item["terminalState"] for item in d1)
    assert all("previsão" in item["forbiddenConclusion"].lower() for item in d1)


def test_qa_is_fail_closed_and_complete(bundle: dict) -> None:
    qa = bundle["qa"]
    assert qa["state"] == "PASS"
    assert qa["failedCount"] == 0
    assert qa["checkCount"] >= 40
    assert qa["counts"] == {
        "factCount": 292,
        "managerReferencedFactCount": 123,
        "managerVisibleFactCount": 119,
        "technicalOnlyReferencedFactCount": 4,
        "unreferencedSupportingFactCount": 169,
        "dossierCount": 10,
        "scenarioCount": 3,
        "agendaCount": 5,
        "visualCount": 14,
    }


def _rerun_qa(bundle: dict, **overrides: dict) -> dict:
    arguments = {
        "contract": bundle["contract"],
        "facts": bundle["facts"],
        "vale": bundle["vale"],
        "nsr": bundle["nsr"],
        "scenarios": bundle["scenarios"],
        "agendas": bundle["agendas"],
        "visuals": bundle["visuals"],
        "input_hashes": bundle["input_hashes"],
        "source_availability_counts": bundle["source_availability_counts"],
        "opus_reconciliation": bundle["opus_reconciliation"],
    }
    arguments.update(overrides)
    return _quality_checks(**arguments)


def test_negative_control_rejects_interchangeable_scenarios(bundle: dict) -> None:
    mutated = copy.deepcopy(bundle["scenarios"])
    mutated["scenarios"][1]["decisionDomain"] = mutated["scenarios"][0][
        "decisionDomain"
    ]
    mutated["scenarios"][1]["primaryIndicatorFamilies"] = mutated["scenarios"][0][
        "primaryIndicatorFamilies"
    ]
    with pytest.raises(
        DossierValidationError, match="AA4_SCENARIO_DIFFERENTIATION_MECHANICAL"
    ):
        _rerun_qa(bundle, scenarios=mutated)


def test_negative_control_rejects_vacuous_incremental_value(bundle: dict) -> None:
    mutated = copy.deepcopy(bundle["nsr"])
    mutated["dossiers"][0]["incrementalValueAssessment"][
        "valueBeyondSeparateCharts"
    ] = False
    mutated["dossiers"][0]["incrementalValueAssessment"]["justification"] = ""
    with pytest.raises(DossierValidationError, match="AA4_INCREMENTAL_VALUE_RUBRIC"):
        _rerun_qa(bundle, nsr=mutated)


def test_materialized_package_contract_when_available() -> None:
    if not DEFAULT_OUTPUT_ROOT.exists():
        pytest.skip("Pacote AA4 ainda não materializado nesta execução em camadas.")
    manifest = validate_existing_output(DEFAULT_OUTPUT_ROOT)
    assert manifest["finalState"] == (
        "AA4_COMPLETE_OPUS_REAUDIT_ON_TRACK"
    )
    assert manifest["independentMaterializationVerification"]["state"] == (
        "VERIFIED_IDENTICAL"
    )
    assert manifest["independentMaterializationVerification"]["pythonHashSeeds"] == [
        "505",
        "606",
    ]
    assert manifest["generation"]["manifestLast"] is True
    assert manifest["publicDataIntegrity"]["notWrittenByAa4"] is True
    assert manifest["opusReconciliation"]["reAudit"]["aa5EntryAllowed"] is True
    for filename in (
        VALE_FILE,
        NSR_FILE,
        AGENDAS_FILE,
        VISUALS_FILE,
        FACTS_FILE,
        QA_FILE,
    ):
        assert (DEFAULT_OUTPUT_ROOT / filename).is_file()
    scenarios = json.loads(
        (DEFAULT_OUTPUT_ROOT / "CENARIOS_CONDICIONAIS_AA4.json").read_text(
            encoding="utf-8"
        )
    )
    assert scenarios["futureNumericProjectionAllowed"] is False
