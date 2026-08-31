from __future__ import annotations

import json
import math
from pathlib import Path
import re
import sys

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from data_pipeline.src.vocacoes_pne_job2 import directory_content_digest  # noqa: E402
from data_pipeline.src.vocacoes_pne_job5k import (  # noqa: E402
    FINAL_STATE,
    JOB5GCR_ROOT,
    JOB5I_ROOT,
    JOB5J_ROOT,
    NON_SCREENSHOT_FILES,
    NSR_CODE,
    PUBLIC_DATA_ROOT,
    REGION_ID,
    REQUIRED_STORY_FIELDS,
    SCREENSHOT_FILES,
    build_bundle,
    validate_existing_output,
    write_package,
)


@pytest.fixture(scope="module")
def bundle() -> dict:
    return build_bundle()


def _story(bundle: dict, story_id: str) -> dict:
    return next(item for item in bundle["stories"] if item["story_id"] == story_id)


def _variant(story: dict, entity_id: str) -> dict:
    return next(
        item
        for item in story["selected_municipality_read"]["variants"]
        if item["entity_id"] == entity_id
    )


def _entity_evidence(story: dict, layer: str, entity_id: str) -> dict:
    return next(
        item for item in story[layer]["by_entity"] if item["entity_id"] == entity_id
    )


def test_topology_promotion_and_internal_gate(bundle: dict) -> None:
    assert bundle["counts"] == {
        "direction_count": 2,
        "primary_story_count": 4,
        "story_variant_count": 44,
        "conditional_context_count": 2,
        "conditional_variant_count": 22,
        "municipality_count": 10,
        "relation_count": 8,
    }
    assert bundle["meta"]["gate11"] == "CLOSED"
    assert bundle["meta"]["internal_only"] is True
    assert bundle["meta"]["public_narrative_authorized"] is False
    assert bundle["meta"]["publication_authorized"] is False
    assert bundle["meta"]["public_data_writes_authorized"] is False
    assert bundle["meta"]["manager_validation_started"] is False
    assert bundle["external_judgment"]["job5j_rerun_required"] is False
    promotion = {
        item["relation_id"]: item for item in bundle["editorial_promotion_contract"]
    }
    assert set(promotion) == {f"R{index}" for index in range(1, 9)}
    assert promotion["R1"]["editorial_story_state"] == "PRIMARY_INSIGHT"
    assert promotion["R2"]["editorial_story_state"] == "NOT_STANDALONE"
    assert promotion["R3"]["analytical_relation_state"] == "NOT_SUPPORTED"
    assert promotion["R4"]["editorial_story_state"] == "PRIMARY_INSIGHT"
    assert promotion["R5"]["editorial_story_state"] == "PRIMARY_INSIGHT"
    assert promotion["R6"]["editorial_story_state"] == "SECONDARY_CONTEXT"
    assert promotion["R7"]["editorial_story_state"] == "CONDITIONAL_EXPANDED"
    assert promotion["R8"]["editorial_story_state"] == "DESCRIPTIVE_CONTEXT_ONLY"


def test_story_contracts_are_complete_normalized_and_not_autoapproved(bundle: dict) -> None:
    entities = {REGION_ID, *[item["ibgeCode"] for item in bundle["municipalities"]]}
    assert bundle["normalization"] == {
        "regional_evidence_stored_once": True,
        "municipal_variants_generated_by_rules": True,
        "manual_municipality_profiles": False,
        "canonical_code_used_for_identity_only": True,
        "ranking_used": False,
        "opaque_materiality_threshold_used": False,
        "json_encoded_inside_strings": False,
    }
    for story in bundle["stories"]:
        assert REQUIRED_STORY_FIELDS <= set(story)
        assert story["network_scope"] == "total_all_dependencies"
        assert story["manager_review_state"] == "pending"
        assert story["public_narrative_authorized"] is False
        assert story["selected_municipality_read"]["municipality_overrides"] is False
        variants = story["selected_municipality_read"]["variants"]
        assert {item["entity_id"] for item in variants} == entities
        assert len(variants) == 11
        if story["story_id"] == "STORY_EJA_TERRITORY":
            assert story["primary_evidence"]["distribution_id"] == (
                "EJA_RESIDENT_LOCATED_SHARES_2022"
            )
        else:
            assert len(story["primary_evidence"]["by_entity"]) == 11


def test_high_school_history_is_separate_from_2030_pressure(bundle: dict) -> None:
    story = _story(bundle, "STORY_HIGH_SCHOOL_TRAJECTORY")
    nsr = _variant(story, NSR_CODE)
    region = _variant(story, REGION_ID)
    assert "ampliou matrículas e turmas" in nsr["title_conclusion"]
    assert nsr["key_figures"][0]["value"] == "+41"
    assert region["key_figures"][0]["value"] == "−4.878"
    evidence = _entity_evidence(story, "primary_evidence", NSR_CODE)
    assert evidence["high_school"]["initial_value"] == 799
    assert evidence["high_school"]["final_value"] == 840
    assert evidence["classes"]["absolute_change"] == 2
    secondary = _entity_evidence(story, "secondary_evidence", NSR_CODE)
    assert math.isclose(
        secondary["mechanical_pressure_2030"]["value"],
        1.6416666666666666,
        abs_tol=1e-15,
    )
    assert secondary["mechanical_pressure_2030"]["editorial_visibility"] == (
        "secondary_non_predictive_detail"
    )
    assert "fotografia de mobilidade de 2022 não mostrou um padrão consistente" in story[
        "interpretation_boundary"
    ]
    assert "mobilidade não explica" not in json.dumps(story, ensure_ascii=False).lower()


def test_eja_keeps_stages_and_required_distances_separate(bundle: dict) -> None:
    story = _story(bundle, "STORY_EJA_TERRITORY")
    distances = story["primary_evidence"]["regional_distance_percentage_points"]
    assert math.isclose(distances["fundamental"], 21.678314751208454, abs_tol=1e-12)
    assert math.isclose(distances["high_school"], 51.813592394463804, abs_tol=1e-12)
    nsr = next(
        item
        for item in story["ten_municipality_distribution"]
        if item["municipality_ibge_code"] == NSR_CODE
    )
    assert math.isclose(
        nsr["fundamental"]["difference_percentage_points"],
        2.64826314439351,
        abs_tol=1e-12,
    )
    assert math.isclose(
        nsr["high_school"]["difference_percentage_points"],
        -2.60509457510993,
        abs_tol=1e-12,
    )
    history = next(
        item["eja_history"]
        for item in story["secondary_evidence"]["by_entity"]
        if item["entity_id"] == NSR_CODE
    )
    assert (history["initial_value"], history["final_value"]) == (309, 208)
    assert "as duas etapas não são somadas" in story["interpretation_boundary"]


def test_logistics_ept_materializes_all_required_shares_and_zero(bundle: dict) -> None:
    story = _story(bundle, "STORY_LOGISTICS_EPT")
    distribution = story["ten_municipality_distribution"]
    assert distribution["positive_change_denominator"] == 1821
    assert distribution["regional_ept_denominator"] == 13945
    assert len(distribution["rows"]) == 10
    assert all(item["cbo_414140_absolute_change"] > 0 for item in distribution["rows"])
    assert math.isclose(
        sum(item["share_of_positive_regional_change_percent"] for item in distribution["rows"]),
        100,
        abs_tol=1e-9,
    )
    assert math.isclose(
        sum(item["share_of_regional_ept_percent"] for item in distribution["rows"]),
        100,
        abs_tol=1e-9,
    )
    nsr_row = next(
        item for item in distribution["rows"] if item["municipality_ibge_code"] == NSR_CODE
    )
    assert (nsr_row["cbo_414140_initial_value"], nsr_row["cbo_414140_final_value"]) == (
        17,
        722,
    )
    assert math.isclose(
        nsr_row["share_of_positive_regional_change_percent"],
        38.715,
        abs_tol=0.0005,
    )
    assert nsr_row["technical_enrollments_2025"] == 0
    assert nsr_row["technical_enrollments_availability_state"] == "observed_zero"
    nsr = _entity_evidence(story, "secondary_evidence", NSR_CODE)
    assert (
        nsr["youth_work_18_24"]["initial_value"],
        nsr["youth_work_18_24"]["final_value"],
    ) == (1117, 1638)
    assert math.isclose(
        nsr["youth_regional_change_contribution_percent"],
        45.582,
        abs_tol=0.0005,
    )
    assert nsr["bridge"]["additiveAcrossBridgeRows"] is False
    assert "mesmas pessoas" in story["interpretation_boundary"]
    forbidden_visible = json.dumps(
        {
            "title": _variant(story, NSR_CODE)["title_conclusion"],
            "summary": _variant(story, NSR_CODE)["integrated_summary"],
            "boundary": story["interpretation_boundary"],
        },
        ensure_ascii=False,
    ).lower()
    assert "curso necessário" not in forbidden_visible
    assert "falta de acesso" not in forbidden_visible


def test_youth_work_preserves_facts_and_negative_association_boundary(bundle: dict) -> None:
    story = _story(bundle, "STORY_YOUTH_WORK_APPRENTICESHIP")
    assert story["analytical_relation_states"] == {"R3": "NOT_SUPPORTED"}
    nsr = _entity_evidence(story, "primary_evidence", NSR_CODE)
    assert (nsr["rais_15_17"]["initial_value"], nsr["rais_15_17"]["final_value"]) == (
        104,
        172,
    )
    share = nsr["apprenticeship_share_2025"]
    assert (share["numerator"], share["denominator"]) == (174, 219)
    assert math.isclose(share["percent"], 79.45205479452055, abs_tol=1e-12)
    assert "não mostraram uma relação estável" in story["interpretation_boundary"]
    assert "não existe relação" not in story["interpretation_boundary"]
    assert "estoques e eventos não equivalem a pessoas únicas" in story[
        "interpretation_boundary"
    ].lower()


def test_conditional_contexts_render_stability_and_reclassify_special_aee(bundle: dict) -> None:
    rural = next(
        item
        for item in bundle["conditional_contexts"]
        if item["context_id"] == "CONTEXT_RURALITY_TRANSPORT"
    )
    nsr = next(item for item in rural["variants"] if item["entity_id"] == NSR_CODE)
    assert nsr["rural_enrollments"]["absolute_change"] == 55
    assert nsr["rural_schools"]["absolute_change"] == 0
    assert nsr["rural_high_school_enrollments"]["absolute_change"] == -90
    assert "escolas rurais permaneceu estável" in nsr["summary"]
    assert "zero escolas" not in nsr["summary"]
    assert nsr["pnate_2026"]["planning_only"] is True
    special = next(
        item
        for item in bundle["conditional_contexts"]
        if item["context_id"] == "CONTEXT_SPECIAL_AEE"
    )
    assert special["editorial_story_state"] == "DESCRIPTIVE_CONTEXT_ONLY"
    assert not any(
        story["story_id"] == "CONTEXT_SPECIAL_AEE" for story in bundle["stories"]
    )
    special_nsr = next(
        item for item in special["variants"] if item["entity_id"] == NSR_CODE
    )
    assert "não medem cobertura nem atendimento das mesmas pessoas" in special_nsr[
        "interpretation_boundary"
    ]


def test_identity_pne_network_and_public_side_effects_are_preserved(bundle: dict) -> None:
    codes = [item["ibgeCode"] for item in bundle["municipalities"]]
    assert len(codes) == len(set(codes)) == 10
    assert all(isinstance(code, str) and re.fullmatch(r"[0-9]{7}", code) for code in codes)
    assert bundle["pne_contract"]["official_indicator_recalculated"] is False
    assert bundle["pne_contract"]["goal_compliance_claim_allowed"] is False
    assert bundle["pme_contract"]["state"] == "not_materialized"
    assert bundle["pme_contract"]["goal_refs"] == []
    assert bundle["preflight"]["digests"]["job5gcrTreeDigestSha256"] == (
        "4d04b0c9cb6d95432dcf51c7ab5e16253ebafcbd9ec10e4bba254928f8af1c2f"
    )
    assert bundle["preflight"]["digests"]["job5iTreeDigestSha256"] == (
        "e25c34c6f0dcdae29f73129a403ee3bf785caf6acdee0c967dd594123daf0eba"
    )
    assert bundle["preflight"]["digests"]["job5jTreeDigestSha256"] == (
        "f31b230fb9268ca57c15f1e322ef9317d841288f7408a9638b0042343a5fb57c"
    )
    assert bundle["preflight"]["digests"]["publicDataTreeDigestSha256"] == (
        "4a52e3891163cb3427c5c01f2ef5414c5fe7855dd491a9a125b509899dcc23e1"
    )


def test_generation_is_byte_reproducible_and_draft_has_eleven_files(
    bundle: dict, tmp_path: Path
) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    write_package(output_dir=first, bundle=bundle)
    write_package(output_dir=second, bundle=bundle)
    assert directory_content_digest(first) == directory_content_digest(second)
    assert {path.name for path in first.iterdir() if path.is_file()} == set(
        NON_SCREENSHOT_FILES
    )
    manifest = validate_existing_output(first, require_screenshots=False)
    assert manifest["finalState"] is None
    assert manifest["gate11"] == "CLOSED"
    assert manifest["formulasAltered"] == []
    assert manifest["generation"]["networkUsed"] is False
    assert manifest["generation"]["databaseUsed"] is False
    assert manifest["generation"]["publicationPerformed"] is False


def test_draft_accepts_exactly_four_captures_only_during_finalization(
    bundle: dict, tmp_path: Path
) -> None:
    draft = tmp_path / "draft-with-screenshots"
    write_package(output_dir=draft, bundle=bundle)
    for index, name in enumerate(SCREENSHOT_FILES, start=1):
        (draft / name).write_bytes(f"screenshot-{index}".encode("ascii"))
    with pytest.raises(Exception, match="topologia Job 5K divergente"):
        validate_existing_output(draft, require_screenshots=False)
    manifest = validate_existing_output(
        draft,
        require_screenshots=False,
        allow_draft_screenshots=True,
    )
    assert manifest["finalState"] is None
    assert manifest["counts"]["shared_file_count"] == 11


def test_final_package_validation_accepts_shared_draft_screenshot_option(
    bundle: dict, tmp_path: Path
) -> None:
    screenshot_root = tmp_path / "screenshots"
    screenshot_root.mkdir()
    for index, name in enumerate(SCREENSHOT_FILES, start=1):
        (screenshot_root / name).write_bytes(f"screenshot-{index}".encode("ascii"))
    final = tmp_path / "final"
    write_package(
        output_dir=final,
        bundle=bundle,
        finalized=True,
        screenshot_source_root=screenshot_root,
        validation_evidence={"requiredChecksPassed": True, "commands": []},
    )
    manifest = validate_existing_output(final, allow_draft_screenshots=True)
    assert manifest["finalState"] == FINAL_STATE
    assert manifest["counts"]["shared_file_count"] == 15


def test_frozen_roots_remain_bytewise_equal_after_bundle_and_package(bundle: dict) -> None:
    assert directory_content_digest(JOB5GCR_ROOT) == bundle["preflight"]["digests"][
        "job5gcrTreeDigestSha256"
    ]
    assert directory_content_digest(JOB5I_ROOT) == bundle["preflight"]["digests"][
        "job5iTreeDigestSha256"
    ]
    assert directory_content_digest(JOB5J_ROOT) == bundle["preflight"]["digests"][
        "job5jTreeDigestSha256"
    ]
    assert directory_content_digest(PUBLIC_DATA_ROOT) == bundle["preflight"]["digests"][
        "publicDataTreeDigestSha256"
    ]
    assert FINAL_STATE == "JOB_5K_READY_WITH_EXPLICIT_LIMITS_FOR_EXTERNAL_JUDGMENT"
