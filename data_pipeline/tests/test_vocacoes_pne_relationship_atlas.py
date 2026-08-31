from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_PIPELINE_ROOT = REPO_ROOT / "data_pipeline"
EXECUTION_CONTRACT_PATH = (
    DATA_PIPELINE_ROOT
    / "contracts/vocacoes-pne-relationship-atlas-execution-v1.json"
)
if str(DATA_PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(DATA_PIPELINE_ROOT))

from src.vocacoes_pne_relationship_atlas import (
    AVAILABILITY_STATES,
    PACKAGE_FILES,
    RelationshipAtlasValidationError,
    build_pretest_package,
    materialize_twice_and_freeze,
    validate_existing_output,
)


@pytest.fixture(scope="module")
def package() -> dict[str, object]:
    return build_pretest_package()


def test_source_universe_is_exhaustive_and_disposed_once(
    package: dict[str, object],
) -> None:
    quality = package["quality"]
    assert quality["state"] == "PASS"
    assert quality["sourceSignatureCount"] == 3_267
    assert quality["expectedSourceSignatureCount"] == 3_267
    assert quality["allSourceSignaturesDisposedExactlyOnce"] is True
    assert quality["unknownDispositionCount"] == 0
    assert sum(quality["dispositionCounts"].values()) == 3_267
    assert quality["aa1"]["signatureCount"] == 3_189
    assert quality["job5i"]["signatureCount"] == 78

    signatures = package["signatures"]
    signature_ids = [record["signatureId"] for record in signatures]
    assert len(signature_ids) == len(set(signature_ids)) == 3_267


def test_all_analytic_variables_resolve_to_real_source_signatures(
    package: dict[str, object],
) -> None:
    quality = package["quality"]
    variables = package["variables"]
    variable_ids = [record["variableId"] for record in variables]
    assert len(variable_ids) == len(set(variable_ids)) == 122
    assert quality["analyticVariableCount"] == 122
    assert quality["allAnalyticVariablesResolveToSourceSignatures"] is True
    assert quality["unmatchedAnalyticVariableIds"] == []
    assert set(quality["analyticVariableSignatureMatchCounts"]) == set(variable_ids)
    assert min(quality["analyticVariableSignatureMatchCounts"].values()) >= 1


def test_hypothesis_matrix_is_frozen_before_results_and_covers_all_families(
    package: dict[str, object],
) -> None:
    hypotheses = package["hypotheses"]
    contract = package["contract"]
    hypothesis_ids = [record["hypothesisId"] for record in hypotheses]
    family_ids = {record["familyId"] for record in hypotheses}
    contract_family_ids = {
        record["familyId"] for record in contract["familyRegistry"]
    }

    assert len(hypothesis_ids) == len(set(hypothesis_ids)) == 98
    assert family_ids == contract_family_ids
    assert len(family_ids) == 18
    assert {record["lane"] for record in hypotheses} == {
        "demography_network",
        "economy_work",
        "social_access",
    }
    assert all(record["resultKnowledgeState"] != "RESULT_KNOWN" for record in hypotheses)
    assert all(record["multiplicityFamily"] == record["familyId"] for record in hypotheses)
    assert all(record["causalEligible"] is False for record in hypotheses)


def test_availability_identity_regions_and_denominator_rules_are_explicit(
    package: dict[str, object],
) -> None:
    quality = package["quality"]
    availability = quality["availabilityStateContract"]
    assert availability["requiredStates"] == list(AVAILABILITY_STATES)
    assert set(availability["aa1Counts"]) == set(AVAILABILITY_STATES)
    assert set(availability["job5iCounts"]) == set(AVAILABILITY_STATES)
    assert availability["aa1Counts"]["suppressed"] == 0
    assert availability["aa1Counts"]["not_applicable"] == 0
    assert availability["job5iCounts"]["suppressed"] == 0
    assert availability["job5iCounts"]["not_applicable"] == 0
    assert availability["zeroCountStatesExplicit"] is True
    assert availability["denominatorZeroProducesNull"] is True
    assert quality["identity"] == {
        "aa1AllTextualSevenDigits": True,
        "job5iAllMunicipalTextualSevenDigits": True,
        "nameJoinUsedByThisStage": False,
    }
    assert quality["regions"]["municipalityCount"] == 497
    assert quality["regions"]["completeUniqueRs497Mapping"] is True
    assert quality["regions"]["leaveOneRegionOutAvailable"] is True


def test_identification_audit_blocks_causal_language_for_every_family(
    package: dict[str, object],
) -> None:
    audit = package["identification"]
    assert audit["causalFamilyCount"] == 0
    assert len(audit["records"]) == 18
    assert all(record["causalClaimAllowed"] is False for record in audit["records"])
    assert all(
        record["identificationState"] == "NO_DEFENSIBLE_CAUSAL_IDENTIFICATION"
        for record in audit["records"]
    )


def test_nominal_values_and_current_public_readings_have_pre_result_fences(
    package: dict[str, object],
) -> None:
    policy = package["contract"]["nominalValuePolicy"]
    assert policy["deflatorInstalled"] is False
    assert policy["crossYearNominalLevelComparisonAllowed"] is False

    promotions = package["currentPromotions"]
    assert promotions["auditTiming"] == "BEFORE_NEW_MODEL_RESULTS"
    assert promotions["readingCount"] == 5
    assert promotions["primaryRetentionCount"] == 1
    assert promotions["demotionCount"] == 4
    assert all(record["causalLanguageAllowed"] is False for record in promotions["records"])


def test_materialization_is_deterministic_hash_locked_and_fail_closed(
    tmp_path: Path,
) -> None:
    output = tmp_path / "preregistration"
    first = materialize_twice_and_freeze(output)
    second = materialize_twice_and_freeze(output)
    checked = validate_existing_output(output)

    assert first == second == checked
    assert first["state"] == "PRETEST_UNIVERSE_AND_HYPOTHESES_FROZEN"
    assert first["counts"] == {
        "sourceSignatureCount": 3_267,
        "analyticVariableCount": 122,
        "hypothesisCount": 98,
        "familyCount": 18,
        "currentPromotionAuditCount": 5,
        "causalFamilyCount": 0,
    }
    assert {path.name for path in output.iterdir()} == set(PACKAGE_FILES)

    freeze = json.loads((output / "FREEZE.json").read_text(encoding="utf-8"))
    assert freeze["state"] == "FROZEN_BEFORE_NEW_MODEL_RESULTS"
    assert freeze["postResultAdjustmentAllowed"] is False

    qa_path = output / "QA_SUMMARY.json"
    qa_path.write_text(qa_path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    with pytest.raises(RelationshipAtlasValidationError, match="Hashes"):
        validate_existing_output(output)


def test_execution_release_binds_lanes_to_freeze_and_fable_mitigations() -> None:
    contract = json.loads(EXECUTION_CONTRACT_PATH.read_text(encoding="utf-8"))
    assert contract["state"] == "FROZEN_BEFORE_MODEL_EXECUTION"
    assert (
        contract["parentFreeze"]["artifactSetDigestSha256"]
        == "6f0994b2cc3b563e0709cc8cd04f4d14382ef9ec2ddc089feeae88f9bf2e8a81"
    )
    assert contract["parentFreeze"]["postResultAdjustmentAllowed"] is False
    assert contract["releaseGate"]["failClosedOnAnyMismatch"] is True
    assert sum(lane["expectedHypothesisCount"] for lane in contract["lanes"]) == 98

    feasibility = contract["feasibilityRules"]
    assert feasibility["invalidFitPValueForMultiplicity"] == 1.0
    assert feasibility["requiredRobustnessInfeasible"].endswith(
        "INSUFFICIENT_DATA_P_EQUALS_ONE"
    )
    assert feasibility["shortPanelVale"]["leadOnePlaceboRequired"] is True
    assert feasibility["shortPanelVale"]["minimumPeriodsAfterLeadShift"] == 3

    multiplicity = contract["multiplicityProtocol"]
    assert multiplicity["familyDenominatorFrozen"] is True
    assert multiplicity["globalExploratoryQAcrossAll98Required"] is True
    assert multiplicity["statewideMaximumQ"] == 0.05
    assert multiplicity["valeMaximumQ"] == 0.1

    assert contract["lensProtocol"]["crossLensNeverMeansSamePeopleLinked"] is True
    assert contract["lensProtocol"]["promotionRequiresExplicitScopeLensNetworkAudit"] is True
    assert contract["nominalValueProtocol"]["crossYearNominalLevelComparisonAllowed"] is False
    assert contract["nominalValueProtocol"]["municipalFinanceRelationalFitAllowed"] is False
    assert contract["resultContract"]["causalClaimAllowedAlways"] is False
    assert contract["operationalConstraints"]["nameJoinAllowed"] is False
