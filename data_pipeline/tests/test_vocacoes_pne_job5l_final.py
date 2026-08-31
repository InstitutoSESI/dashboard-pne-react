from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from src.vocacoes_pne_job5l import _select_rais_columns, build_f1_context
from src.vocacoes_pne_job5l_final import (
    CANDIDATE_REQUIRED_FIELDS,
    CENSO_URLS,
    CONTRACT_PATH,
    DEFAULT_OUTPUT_ROOT,
    FINAL_STATE,
    HISTORY_FEATURES,
    INTERNAL_FILES,
    PACKAGE_FILES,
    SERVICE_LENS_AUDIT,
    _bounded_conformal_scores,
    _bounded_interval,
    build_eja_final,
    build_f2_f5_unavailable,
    empirical_logit_percent,
    fit_f1_final,
    inverse_logit_percent,
    validate_existing_output,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
PREVIOUS_DATABASE = (
    REPO_ROOT / ".tmp" / "vocacoes-pne" / "v7-job5l" / "sources" / "database"
)


def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_contract_closes_scope_and_declares_exact_topology() -> None:
    contract = _json(CONTRACT_PATH)
    assert contract["packageFiles"] == list(PACKAGE_FILES)
    assert contract["internalSupportingArtifacts"] == list(INTERNAL_FILES)
    assert len(PACKAGE_FILES) == 12
    assert len(INTERNAL_FILES) == 11
    assert contract["gate11"] == "CLOSED"
    assert contract["job5MAllowed"] is False
    assert contract["generation"]["publicDataWritesAllowed"] is False
    assert contract["censo"]["announcementAloneCountsAsAvailability"] is False
    assert contract["rais"]["activeRaisAndCagedAdmissionsInterchangeable"] is False
    assert contract["eja"]["distributionDifferencePercentagePointsPreserved"] is True
    assert len(contract["catalog"]["requiredInsightIds"]) == 6
    assert "official_calendar" in CENSO_URLS
    assert "sample_documentation_expected_root" in CENSO_URLS
    assert len(CANDIDATE_REQUIRED_FIELDS) == 32
    assert FINAL_STATE in contract["allowedFinalStates"]


def test_rate_transformation_and_intervals_are_bounded_without_clipping() -> None:
    observed = np.asarray([0.0, 1.0, 50.0, 99.0, 100.0])
    modeled = inverse_logit_percent(empirical_logit_percent(observed))
    assert np.all(modeled > 0)
    assert np.all(modeled < 100)
    assert modeled[2] == pytest.approx(50.0)

    lower_scores, upper_scores = _bounded_conformal_scores(
        np.asarray([0.0, 20.0, 90.0, 100.0]),
        np.asarray([20.0, 20.0, 80.0, 80.0]),
    )
    assert lower_scores.tolist() == pytest.approx([1.0, 0.0, 0.0, 0.0])
    assert upper_scores.tolist() == pytest.approx([0.0, 0.0, 0.5, 1.0])
    lower, upper = _bounded_interval(
        np.asarray([20.0, 80.0]), lower_quantile=1.0, upper_quantile=0.5
    )
    assert lower.tolist() == pytest.approx([0.0, 0.0])
    assert upper.tolist() == pytest.approx([60.0, 90.0])


def test_rais_establishment_lens_is_explicit_and_legacy_default_is_preserved() -> None:
    common = [
        "Vínculo Ativo 31/12",
        "Idade",
        "Escolaridade após 2005",
        "Qtd Hora Contr",
        "Vl Remun Média Nom",
        "Tempo Emprego",
        "Tipo Vínculo",
        "CBO Ocupação 2002",
        "IBGE Subsetor",
        "Tamanho Estabelecimento",
    ]
    header = [*common, "Mun Trab", "Município"]
    legacy = _select_rais_columns(header)
    canonical = _select_rais_columns(
        header, municipality_lens="establishment_location"
    )
    assert legacy["municipality"] == "Mun Trab"
    assert canonical["municipality"] == "Município"
    assert sum(item["establishmentLocationExactCells"] for item in SERVICE_LENS_AUDIT) == 80
    assert sum(item["serviceLocationExactCells"] for item in SERVICE_LENS_AUDIT) == 0


def test_eja_final_preserves_distribution_contrast_without_per_thousand_proxy() -> None:
    panel = build_eja_final()
    assert len(panel) == 22
    assert set(panel["stage"]) == {"fundamental", "high_school"}
    assert not panel["per_thousand_rate_materialized"].any()
    assert not panel["coverage_demand_or_deficit_claim_allowed"].any()
    assert "eja_enrollments_per_thousand_resident_public_2022" not in panel.columns
    required = {
        "resident_adult_public",
        "school_location_eja_enrollments",
        "share_of_regional_public_percent",
        "share_of_regional_enrollments_percent",
        "distribution_difference_percentage_points",
        "adult_panel_compatibility",
    }
    assert required <= set(panel.columns)
    nsr = panel[panel["entity_id"].astype(str).eq("4313375")].set_index("stage")
    assert nsr.loc[
        "fundamental", "distribution_difference_percentage_points"
    ] == pytest.approx(2.6482631443935167)
    assert nsr.loc[
        "high_school", "distribution_difference_percentage_points"
    ] == pytest.approx(-2.6050945751099364)
    assert nsr.loc["fundamental", "eja_enrollments_2025"] == pytest.approx(152)
    assert nsr.loc["high_school", "eja_enrollments_2025"] == pytest.approx(56)
    assert nsr.loc["fundamental", "adult_panel_compatibility"] == (
        "DEFINITION_INCOMPATIBLE_POPULATION_TOTAL_SOURCE"
    )


def test_f2_f5_unavailable_do_not_materialize_same_person_estimates() -> None:
    panel = build_f2_f5_unavailable(
        {"state": "OFFICIAL_SAMPLE_MICRODATA_NOT_AVAILABLE_AS_OF_2026_08_30"}
    )
    assert len(panel) == 33
    assert panel["value"].isna().all()
    assert panel["same_person_required"].all()
    assert not panel["same_person_materialized"].any()
    assert panel["front_state"].eq(
        "NOT_EXECUTED_OFFICIAL_SOURCE_UNAVAILABLE"
    ).all()


@pytest.mark.skipif(
    not (PREVIOUS_DATABASE / "manifest.json").is_file(),
    reason="snapshots congelados do Job 5L não estão disponíveis",
)
def test_f1_real_snapshots_compare_history_context_and_keep_expected_gate() -> None:
    _, analysis = build_f1_context(PREVIOUS_DATABASE)
    results, validation, _ = fit_f1_final(analysis)
    assert len(results) == 497 * 3 * 4
    assert len(validation) == 12
    eligible = validation["validation_eligible"].astype(bool)
    assert int(eligible.sum()) == 11
    assert set(
        zip(
            validation.loc[~eligible, "outcome_id"],
            validation.loc[~eligible, "stage"],
            strict=True,
        )
    ) == {("dropout_rate_percent", "fundamental_anos_iniciais")}
    assert validation["history_only_group_holdout_mae"].notna().all()
    assert validation["history_plus_context_group_holdout_mae"].notna().all()
    assert validation["context_covariates_added_value_oos"].any()
    assert set(validation["selected_comparison_basis"]) == {
        "HISTORY_ONLY",
        "HISTORY_PLUS_CONTEXT",
    }
    assert set(validation["selected_method"]) <= {
        "ridge_empirical_logit",
        "nearest_context_peers",
    }
    for column in (
        "expected_value",
        "expected_interval_lower",
        "expected_interval_upper",
    ):
        assert results[column].dropna().between(0, 100, inclusive="both").all()
    assert results["bounded_by_construction"].all()
    assert not results["post_prediction_clipping_applied"].any()
    assert HISTORY_FEATURES[0] == "lagged_outcome_value"


@pytest.mark.skipif(
    not (DEFAULT_OUTPUT_ROOT / "MANIFEST_JOB5L_FINAL.json").is_file(),
    reason="pacote Job 5L-final ainda não foi materializado",
)
def test_materialized_package_validates() -> None:
    manifest = validate_existing_output(
        DEFAULT_OUTPUT_ROOT,
        source_root=DEFAULT_OUTPUT_ROOT / "sources",
        verify_sources=False,
    )
    assert manifest["finalState"] == FINAL_STATE
    assert manifest["counts"]["packageFileCount"] == 12
    assert manifest["counts"]["raisReconciliationExactCellCount"] == 140
