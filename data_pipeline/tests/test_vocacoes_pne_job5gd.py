from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src.vocacoes_pne_job5gd import (
    FINAL_STATE,
    NSR_CODE,
    REGION_ENTITY_ID,
    _read_csv,
    build_corrected_gcr_fact_catalog,
    build_mobility_panel,
    validate_existing_output,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
GCR_ROOT = REPO_ROOT / ".tmp" / "vocacoes-pne" / "v7-job5gcr"
OUTPUT_ROOT = REPO_ROOT / ".tmp" / "vocacoes-pne" / "v7-job5gd"
MOBILITY_SOURCE = (
    REPO_ROOT
    / "data_pipeline"
    / "data"
    / "vocacoes_pne_v7_job5gd"
    / "mobility_sidra"
)


def _municipality_names() -> dict[str, str]:
    regions = json.loads(
        (REPO_ROOT / "config" / "regions" / "rs.json").read_text(encoding="utf-8")
    )
    codes = next(
        item["municipalityIbgeCodes"]
        for item in regions["regions"]
        if item["slug"] == "vale-do-sinos"
    )
    registry = json.loads(
        (REPO_ROOT / "config" / "municipalities" / "rs.json").read_text(
            encoding="utf-8"
        )
    )
    names = {item["ibgeCode"]: item["name"] for item in registry["municipalities"]}
    return {code: names[code] for code in codes}


def test_preflight_correction_restores_caged_grain_without_value_change() -> None:
    source = _read_csv(
        GCR_ROOT / "MATRIZ_CATALOGO_FATOS_NOVA_SANTA_RITA_JOB5GCR_V1.csv.gz"
    )
    corrected, audit = build_corrected_gcr_fact_catalog(
        gcr_root=GCR_ROOT, source_v1=source
    )
    assert len(source) == len(corrected) == 1364
    assert source["fact_id"].nunique() == 1230
    assert corrected["fact_id"].nunique() == 1364
    assert audit["sourceDuplicateFactIdCount"] == 134
    assert audit["numericAndSelectionContentPreserved"]
    assert (
        audit["sourceCompatibilityMultisetSha256"]
        == audit["correctedCompatibilityMultisetSha256"]
    )
    caged = corrected[corrected["universe"].str.startswith("CAGED_")]
    assert caged["age_group"].notna().all()
    assert set(caged["age_group"]) == {"15_17", "18_24"}
    assert audit["maximumExplorationEligibleByAgeGroup"]["15_17"] > 0
    assert audit["maximumExplorationEligibleByAgeGroup"]["18_24"] > 0
    assert corrected["origin_match_count"].eq(1).all()
    assert not corrected.loc[
        corrected["small_volume_sensitive"], "maximum_exploration_eligible"
    ].any()
    assert not corrected.loc[
        corrected["negative_adjustment_present"], "maximum_exploration_eligible"
    ].any()
    assert not corrected["detailed_caged_line_visual_use_allowed"].any()
    assert not corrected[
        ["physical_order_used", "alphabetical_order_used", "code_order_used"]
    ].any().any()


def test_shift_share_keeps_observed_and_local_differential_directions_separate() -> None:
    source = _read_csv(
        GCR_ROOT / "MATRIZ_CATALOGO_FATOS_NOVA_SANTA_RITA_JOB5GCR_V1.csv.gz"
    )
    corrected, _ = build_corrected_gcr_fact_catalog(
        gcr_root=GCR_ROOT, source_v1=source
    )
    shift = corrected[corrected["universe"].eq("SHIFT_SHARE_LOCAL_DIFFERENTIAL")]
    assert not shift.empty
    assert shift["observed_change_direction"].notna().all()
    assert shift["local_differential_direction"].notna().all()
    assert shift["direction_semantics"].str.contains(
        "neither_means_improvement_or_worsening", regex=False
    ).all()


def test_mobility_reconstructs_official_numerators_denominators_and_anchors() -> None:
    panel, audit = build_mobility_panel(
        source_root=MOBILITY_SOURCE,
        municipality_names=_municipality_names(),
        frozen_job2_panel=_read_csv(
            REPO_ROOT
            / ".tmp"
            / "vocacoes-pne"
            / "v7-job2"
            / "2e"
            / "mobilidade_educacional_2022.csv.gz"
        ),
    )
    assert len(panel) == 36
    assert audit["municipalToRegionClosure"]
    assert audit["frozenJob2Parity"]
    assert not panel["destination_municipality_available"].any()
    assert not panel["origin_destination_matrix_derived"].any()
    assert not panel["foreign_country_included_in_outside"].any()
    nsr = panel[panel["entity_id"].eq(NSR_CODE)].set_index("stage")
    assert (int(nsr.loc["total", "numerator"]), int(nsr.loc["total", "denominator"])) == (1349, 7666)
    assert (int(nsr.loc["fundamental", "numerator"]), int(nsr.loc["fundamental", "denominator"])) == (355, 4090)
    assert (int(nsr.loc["medio", "numerator"]), int(nsr.loc["medio", "denominator"])) == (220, 1151)
    municipal = panel[panel["entity_scope"].eq("municipality")]
    for stage, group in municipal.groupby("stage"):
        region = panel[
            panel["entity_id"].eq(REGION_ENTITY_ID) & panel["stage"].eq(stage)
        ].iloc[0]
        assert int(region["numerator"]) == int(group["numerator"].sum())
        assert int(region["denominator"]) == int(group["denominator"].sum())


def test_materialized_package_preserves_network_lenses_and_noncausal_guards() -> None:
    report = validate_existing_output(OUTPUT_ROOT)
    assert report["finalState"] == FINAL_STATE
    assert report["outputCount"] == 22
    assert report["correctedFactCount"] == 1364
    assert report["storyCount"] == 99

    offer = _read_csv(
        OUTPUT_ROOT / "PAINEL_ESTRUTURA_TERRITORIAL_OFERTA_JOB5GD_V1.csv.gz"
    )
    municipal_offer = offer[offer["entity_scope"].eq("municipality")]
    assert set(municipal_offer["network_scope"]) == {"total_all_dependencies"}
    assert not offer["administrative_dependency_is_analytic_dimension"].any()
    assert not offer["zero_access_conclusion_allowed"].any()
    assert not offer["causal_interpretation_allowed"].any()

    transport = _read_csv(
        OUTPUT_ROOT / "PAINEL_TRANSPORTE_ESCOLAR_PNATE_JOB5GD_V1.csv.gz"
    )
    assert not transport["is_mobility_measure"].any()
    assert not transport["is_origin_destination_matrix"].any()
    assert not transport["derived_per_student_rate"].any()
    assert not transport["execution_claim_allowed"].any()
    assert transport.loc[
        transport["metric"].isin(
            ["school_transport_students_observed", "pnate_executed_amount"]
        ),
        "value_status",
    ].eq("unavailable").all()

    finance = _read_csv(
        OUTPUT_ROOT / "PAINEL_FINANCEIRO_CONTEXTUAL_SELECIONAVEL_JOB5GD_V1.csv.gz"
    )
    assert not finance["nominal_cross_year_growth_claim_allowed"].any()
    assert not finance["educational_result_causality_allowed"].any()
    assert finance["financial_stage"].notna().all()


def test_maximum_story_corpus_covers_vale_ten_municipalities_and_nsr() -> None:
    stories = json.loads(
        (
            OUTPUT_ROOT / "CATALOGO_MAXIMO_HISTORIAS_POTENCIAIS_JOB5GD_V1.json"
        ).read_text(encoding="utf-8")
    )
    frame = pd.DataFrame(stories["stories"])
    assert stories["fixedCardCap"] is None
    assert not frame["fixed_card_cap_applied"].any()
    assert not frame["automatic_selection"].any()
    assert not frame["public_narrative_authorized"].any()
    assert frame["public_narrative"].isna().all()
    assert frame["direction_id"].nunique() == 9
    assert set(frame["entity_id"]) == set(_municipality_names()) | {REGION_ENTITY_ID}
    assert frame[frame["entity_id"].eq(NSR_CODE)]["direction_id"].nunique() == 9
    assert frame[frame["entity_id"].eq(REGION_ENTITY_ID)]["direction_id"].nunique() == 9

    corpus = json.loads(
        (OUTPUT_ROOT / "CORPUS_DOSSIES_MUNICIPAIS_JOB5GD_V1.json").read_text(
            encoding="utf-8"
        )
    )
    assert corpus["municipalityCount"] == 10
    assert {item["municipalityIbgeCode"] for item in corpus["dossiers"]} == set(
        _municipality_names()
    )
    nsr = json.loads(
        (OUTPUT_ROOT / "NOVA_SANTA_RITA_JOB5GD_V1.json").read_text(encoding="utf-8")
    )
    assert nsr["municipalityIbgeCode"] == NSR_CODE
    assert nsr["isSelectedMunicipality"]
    assert nsr["isMandatoryReconstruction"]


def test_manifest_records_determinism_read_only_database_and_no_publication() -> None:
    manifest = json.loads(
        (OUTPUT_ROOT / "MANIFEST_JOB5GD.json").read_text(encoding="utf-8")
    )
    assert manifest["frozenInputIntegrity"]["before"] == manifest["frozenInputIntegrity"]["after"]
    assert manifest["generation"]["deterministic"]
    assert manifest["generation"]["transactional"]
    assert manifest["generation"]["databaseMode"] == "read_only_transaction"
    assert not manifest["generation"]["databaseWrites"]
    assert not manifest["generation"]["publicDataChanged"]
    assert not manifest["generation"]["frontendChanged"]
    assert not manifest["generation"]["publicationPerformed"]
    assert manifest["generation"]["gate11"] == "CLOSED"
    assert manifest["formulasAltered"] == []
    assert not manifest["automaticApproval"]
