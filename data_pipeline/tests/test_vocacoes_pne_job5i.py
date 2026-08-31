from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import re
import sys

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from data_pipeline.src.vocacoes_pne_job5i import (  # noqa: E402
    FALLBACK_MUNICIPALITY_IBGE_CODE,
    JOB5H_ROOT,
    Job5IValidationError,
    REGION_ID,
    build_bundle,
    validate_bundle,
)


@pytest.fixture(scope="module")
def bundle() -> dict:
    return build_bundle()


def _series(bundle: dict, family: str, entity: str, metric: str, **dimensions) -> dict:
    matches = [
        item
        for item in bundle["series"]
        if item["storyFamilyId"] == family
        and item["entityId"] == entity
        and item["metricId"] == metric
        and all(item[key] == value for key, value in dimensions.items())
    ]
    assert len(matches) == 1, (family, entity, metric, dimensions, len(matches))
    return matches[0]


def _point(series: dict, year: int) -> dict:
    return next(item for item in series["points"] if item["year"] == year)


def _fact(bundle: dict, fact_id: str) -> dict:
    return next(item for item in bundle["facts"] if item["factId"] == fact_id)


def test_topology_identity_network_and_internal_gate(bundle: dict) -> None:
    assert len(bundle["families"]) == 13
    assert len(bundle["macroblocks"]) == 7
    assert len(bundle["directions"]) == 2
    assert len(bundle["municipalities"]) == 10
    assert len(bundle["variants"]) == 143
    assert bundle["fallbackMunicipalityIbgeCode"] == FALLBACK_MUNICIPALITY_IBGE_CODE == "4313375"
    assert all(re.fullmatch(r"[0-9]{7}", item["ibgeCode"]) for item in bundle["municipalities"])
    assert all(item["networkScope"] == "total_all_dependencies" for item in bundle["families"])
    assert bundle["languageContract"]["administrativeDependencyAsAnalyticStratumAllowed"] is False
    assert bundle["meta"]["gate11"] == "CLOSED"
    assert bundle["meta"]["internalOnly"] is True
    assert bundle["meta"]["publicationAuthorized"] is False
    assert bundle["meta"]["publicNarrativeAuthorized"] is False
    assert bundle["meta"]["publicDataWritesAuthorized"] is False


def test_percent_scale_contract_and_required_anchors(bundle: dict) -> None:
    anchors = {
        "D2_APPRENTICESHIP.4313375.share.15_17.2025": (174, 219, 0.7945205479452054, 79.45205479452054),
        f"D2_APPRENTICESHIP.{REGION_ID}.share.15_17.2025": (3157, 5855, 0.5391972672929121, 53.91972672929121),
        f"D2_APPRENTICESHIP.{REGION_ID}.share.18_24.2025": (717, 38757, 0.0184998838919421, 1.84998838919421),
    }
    for fact_id, (numerator, denominator, ratio, percent) in anchors.items():
        fact = _fact(bundle, fact_id)
        assert fact["numerator"] == numerator
        assert fact["denominator"] == denominator
        assert math.isclose(fact["rawRatio"], ratio, abs_tol=1e-15)
        assert math.isclose(fact["displayValue"], percent, abs_tol=1e-12)
        assert fact["displayUnit"] == "percent"
        assert fact["scaleContract"] == "ratio_0_1_to_percent_0_100"

    novo = _fact(bundle, "D2_EPT_TERRITORIAL_OFFER.4313409.municipal_share.2025")
    assert (novo["numerator"], novo["denominator"]) == (5541, 13945)
    assert math.isclose(novo["rawRatio"], 0.397346719254213, abs_tol=1e-15)
    assert math.isclose(novo["displayValue"], 39.7346719254213, abs_tol=1e-12)

    proportions = [
        item for item in bundle["facts"]
        if item["unit"] == "percent" and item["availabilityState"] in {"observed", "observed_zero"}
    ]
    assert proportions
    for fact in proportions:
        assert fact["numerator"] is not None
        assert fact["denominator"] is not None
        assert fact["rawRatio"] is not None
        assert 0 <= fact["displayValue"] <= 100
        assert math.isclose(fact["displayValue"], fact["rawRatio"] * 100, abs_tol=1e-9)


def test_ept_municipal_shares_close_one_hundred_without_tautology(bundle: dict) -> None:
    for year in (2023, 2024, 2025):
        facts = [
            item for item in bundle["facts"]
            if item["metricId"] == "share_of_regional_technical_enrollments"
            and item["entityId"] != REGION_ID
            and item["period"] == str(year)
        ]
        assert len(facts) == 10
        assert math.isclose(sum(item["displayValue"] for item in facts), 100, abs_tol=1e-9)
    regional_self_shares = [
        item for item in bundle["facts"]
        if item["entityId"] == REGION_ID and item["metricId"].startswith("share_of_regional_")
    ]
    assert regional_self_shares
    assert all(item["availabilityState"] == "not_applicable" for item in regional_self_shares)
    assert all(item["value"] is None for item in regional_self_shares)


def test_recovered_offer_ept_and_nova_santa_rita_facts(bundle: dict) -> None:
    pre_nsr = _series(
        bundle,
        "D1_COHORT_OFFER_CAPACITY",
        "4313375",
        "located_enrollments",
        educationalStage="pre_school_age_4_5",
    )
    pre_vale = _series(
        bundle,
        "D1_COHORT_OFFER_CAPACITY",
        REGION_ID,
        "located_enrollments",
        educationalStage="pre_school_age_4_5",
    )
    fundamental = _series(bundle, "D1_COHORT_OFFER_CAPACITY", "4313375", "located_enrollments", educationalStage="fundamental")
    high_school = _series(bundle, "D1_COHORT_OFFER_CAPACITY", "4313375", "located_enrollments", educationalStage="high_school")
    schools = _series(bundle, "D1_COHORT_OFFER_CAPACITY", "4313375", "schools", educationalStage="all")
    ept_vale = _series(bundle, "D2_EPT_TERRITORIAL_OFFER", REGION_ID, "technical_enrollments")
    assert (_point(pre_nsr, 2014)["value"], _point(pre_nsr, 2025)["value"]) == (459, 823)
    assert (_point(pre_vale, 2014)["value"], _point(pre_vale, 2025)["value"]) == (17251, 20716)
    assert (_point(fundamental, 2014)["value"], _point(fundamental, 2025)["value"]) == (3873, 3957)
    assert (_point(high_school, 2014)["value"], _point(high_school, 2025)["value"]) == (799, 840)
    assert (_point(schools, 2014)["value"], _point(schools, 2025)["value"]) == (24, 28)
    assert (_point(ept_vale, 2023)["value"], _point(ept_vale, 2025)["value"]) == (13474, 13945)


def test_series_are_real_and_temporal_nature_is_explicit(bundle: dict) -> None:
    assert bundle["counts"]["seriesCount"] == 832
    assert bundle["counts"]["seriesPointCount"] == 7284
    continuous_periods = {
        ("D1_COHORT_OFFER_CAPACITY", "located_enrollments"): (2014, 2025),
        ("D1_ADULT_SCHOOLING_EJA", "total_context"): (2014, 2025),
        ("D1_RURALITY_PNATE_PLANNING", "rural_enrollments"): (2014, 2025),
        ("D2_YOUTH_WORK_15_17", "total"): (2019, 2025),
        ("D2_YOUTH_WORK_15_17", "caged_youth_admissions"): (2020, 2025),
        ("D2_EPT_TERRITORIAL_OFFER", "technical_enrollments"): (2023, 2025),
    }
    for (family, metric), (start, end) in continuous_periods.items():
        samples = [item for item in bundle["series"] if item["storyFamilyId"] == family and item["metricId"] == metric]
        assert samples
        assert all(item["points"][0]["year"] == start and item["points"][-1]["year"] == end for item in samples)
    mobility = [item for item in bundle["series"] if item["storyFamilyId"] == "D1_MOBILITY_HIGH_SCHOOL_OFFER"]
    assert mobility and all(item["temporalNature"] == "single_year_snapshot" for item in mobility)
    assert all([point["year"] for point in item["points"]] == [2022] for item in mobility)
    endpoints = [item for item in bundle["occupationEvidence"] if item["temporalNature"] == "observed_endpoints"]
    assert endpoints and all(len(item["points"]) == 2 for item in endpoints)


def test_regional_semantics_use_distributions_and_label_medians(bundle: dict) -> None:
    trajectory_metrics = {
        "approval_rate_percent",
        "failure_rate_percent",
        "dropout_rate_percent",
        "age_grade_distortion_rate_percent",
    }
    assert not any(
        item["entityId"] == REGION_ID and item["metricId"] in trajectory_metrics
        for item in bundle["series"]
    )
    assert len(bundle["distributions"]) == 124
    for distribution in bundle["distributions"]:
        assert len(distribution["municipalValues"]) == 10
        assert len({item["municipalityIbgeCode"] for item in distribution["municipalValues"]}) == 10
        assert "Mediana" in distribution["valeMedianLabel"]
        assert "distribui" in distribution["comparisonRule"].lower()
    visible_strings = json.dumps({
        "directions": bundle["directions"],
        "macroblocks": bundle["macroblocks"],
        "visualContracts": bundle["visualContracts"],
    }, ensure_ascii=False)
    assert "taxa do Vale" not in visible_strings


def test_zero_absence_caution_and_pnate_planning_are_distinct(bundle: dict) -> None:
    ept_nsr = _series(bundle, "D2_EPT_TERRITORIAL_OFFER", "4313375", "technical_enrollments")
    assert _point(ept_nsr, 2025)["availabilityState"] == "observed_zero"
    assert _point(ept_nsr, 2025)["value"] == 0
    creche = _fact(bundle, "D1_COHORT_OFFER_CAPACITY.4313375.creche_located_enrollments.unavailable")
    assert creche["availabilityState"] == "unavailable" and creche["value"] is None
    for series in bundle["series"]:
        for point in series["points"]:
            if point["availabilityState"] in {"unavailable", "not_applicable", "suppressed"}:
                assert point["value"] is None
    trajectories = [item for item in bundle["series"] if item["metricId"] in {"approval_rate_percent", "failure_rate_percent", "dropout_rate_percent", "age_grade_distortion_rate_percent"}]
    for series in trajectories:
        cautions = [point for point in series["points"] if point["year"] in {2020, 2021}]
        assert all(point["breakOrCautionState"] == "continuity_caution" for point in cautions)
    pnate_execution = [item for item in bundle["series"] if item["metricId"] == "pnate_executed_amount"]
    pnate_forecast = [item for item in bundle["series"] if item["metricId"] == "pnate_adjusted_forecast"]
    assert all(_point(item, 2026)["availabilityState"] == "unavailable" for item in pnate_execution)
    assert all(_point(item, 2026)["breakOrCautionState"] == "planning_forecast" for item in pnate_forecast)


def test_work_education_occupation_and_bridge_contracts(bundle: dict) -> None:
    assert all(value is False for value in bundle["parallelSeriesContract"].values())
    selection = bundle["occupationSelectionContract"]
    assert selection["canonicalCodeUsedAsTieBreak"] is False
    assert selection["selectionIsPriorityOrRanking"] is False
    assert selection["silentThreeItemCap"] is False
    logistics = {
        item["entityId"]: (item["initialValue"], item["finalValue"])
        for item in bundle["occupationEvidence"]
        if item["dimensionCode"] == "414140" and item["entityId"] in {REGION_ID, "4313375"}
    }
    assert logistics == {REGION_ID: (303, 2124), "4313375": (17, 722)}
    assert all(item["selectionIsPriorityOrRanking"] is False for item in bundle["occupationEvidence"])
    bridge = next(item for item in bundle["bridgeSummaries"] if item["entityId"] == REGION_ID)
    assert (
        bridge["observedCourses"], bridge["mappedCourses"], bridge["unmappedCourses"],
        bridge["mappedEnrollments"], bridge["unmappedEnrollments"],
    ) == (44, 39, 5, 12664, 1281)
    assert bridge["additiveAcrossBridgeRows"] is False
    assert all(item["additiveAcrossBridgeRows"] is False for item in bundle["bridgeCorrespondences"])


def test_pne_is_canonical_pme_empty_and_units_normalized(bundle: dict) -> None:
    legal = json.loads((REPO_ROOT / "contracts" / "pne2026-goal-indicator-contract.json").read_text(encoding="utf-8"))
    legal_refs = set(legal["goals"])
    visible_refs = {ref for family in bundle["families"] for ref in family["visiblePneGoalRefs"]}
    assert visible_refs <= legal_refs
    assert {"6.a", "17.a", "19.c"} <= visible_refs
    assert bundle["pneContract"]["officialIndicatorRecalculated"] is False
    assert bundle["pneContract"]["goalComplianceClaimAllowed"] is False
    assert bundle["pmeContract"] == {
        "state": "not_materialized",
        "goalRefs": [],
        "planningThemesAreNotGoals": True,
    }
    assert all(item["unit"] != "students" for item in bundle["facts"])
    assert all(item["unit"] != "students" for item in bundle["series"])


def test_runtime_validation_fails_closed_on_scale_and_gate_mutation(bundle: dict) -> None:
    gate_mutation = json.loads(json.dumps(bundle))
    gate_mutation["meta"]["gate11"] = "OPEN"
    with pytest.raises(Job5IValidationError):
        validate_bundle(gate_mutation)
    scale_mutation = json.loads(json.dumps(bundle))
    fact = next(item for item in scale_mutation["facts"] if item["unit"] == "percent" and item["rawRatio"] is not None)
    fact["displayValue"] *= 100
    fact["value"] = fact["displayValue"]
    with pytest.raises(Job5IValidationError):
        validate_bundle(scale_mutation)


def test_job5h_files_match_the_bytewise_preservation_baseline() -> None:
    baseline_path = REPO_ROOT / ".tmp" / "vocacoes-pne" / "v7-job5i" / "PRESERVATION_BASELINE.json"
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))["frozenJob5h"]
    actual_paths = sorted(path for path in JOB5H_ROOT.iterdir() if path.is_file())
    assert len(actual_paths) == baseline["fileCount"] == 28
    expected = {item["path"]: item for item in baseline["files"]}
    assert set(expected) == {path.name for path in actual_paths}
    for path in actual_paths:
        raw = path.read_bytes()
        assert len(raw) == expected[path.name]["size"]
        assert hashlib.sha256(raw).hexdigest() == expected[path.name]["sha256"]
