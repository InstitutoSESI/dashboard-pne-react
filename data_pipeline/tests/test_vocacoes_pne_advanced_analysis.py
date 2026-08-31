from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


DATA_PIPELINE_DIR = Path(__file__).resolve().parents[1]
if str(DATA_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_PIPELINE_DIR))

from src.vocacoes_pne_advanced_analysis import (  # noqa: E402
    DEFAULT_OUTPUT_ROOT,
    EXPECTED_PREREGISTRATION_FREEZE_SHA256,
    EXPECTED_PREREGISTRATION_SHA256,
    FAMILY_FITS,
    HETEROGENEITY_FILE,
    NOVA_SANTA_RITA_CODE,
    PREREGISTRATION_FREEZE_PATH,
    PREREGISTRATION_PATH,
    RESULTS_FILE,
    CLAIMS_FILE,
    _require_hash,
    _safe_positive_denominator_ratio,
    _decompose_enrollment_change,
    _fit_seed,
    _fold_number,
    bh_adjust_fixed_family,
    check_availability_probe,
    fit_fixed_effect_panel,
    fit_ols_hc3,
    permutation_correlation,
    sha256_file,
    validate_existing_output,
    verify_preresult_inputs,
)


def test_registered_preresult_gate_and_probe_are_frozen() -> None:
    hashes = verify_preresult_inputs()
    probe = check_availability_probe()
    registration = json.loads(PREREGISTRATION_FREEZE_PATH.read_text(encoding="utf-8"))
    assert hashes["preregistrationSha256"] == EXPECTED_PREREGISTRATION_SHA256
    assert sha256_file(PREREGISTRATION_PATH) == EXPECTED_PREREGISTRATION_SHA256
    assert (
        sha256_file(PREREGISTRATION_FREEZE_PATH)
        == EXPECTED_PREREGISTRATION_FREEZE_SHA256
    )
    assert registration["state"] == "FROZEN_PRE_RESULT"
    assert registration["firstResultInspected"] is False
    assert probe["state"] == "FROZEN_PRE_RESULT_PROBE"
    assert probe["coefficientOrRawValueInspected"] is False


def test_hash_gate_fails_closed_on_any_byte_mismatch(tmp_path: Path) -> None:
    artifact = tmp_path / "frozen-input.bin"
    artifact.write_bytes(b"registered")
    with pytest.raises(ValueError, match="SHA-256 divergente"):
        _require_hash(artifact, "0" * 64)


def test_safe_ratio_preserves_observed_zero_and_rejects_zero_denominator() -> None:
    result = _safe_positive_denominator_ratio(
        pd.Series([0.0, 10.0, 5.0, np.nan]),
        pd.Series([4.0, 0.0, -1.0, 2.0]),
        multiplier=100.0,
    )
    assert result.iloc[0] == 0.0
    assert result.iloc[1:].isna().all()


def test_bh_uses_fixed_family_denominator_and_keeps_invalid_fit_null() -> None:
    fit_ids = ("a", "b", "c", "d")
    adjusted = bh_adjust_fixed_family(
        fit_ids,
        {"a": 0.01, "b": 0.02, "c": None, "d": 0.20},
    )
    assert adjusted["a"] == pytest.approx(0.04)
    assert adjusted["b"] == pytest.approx(0.04)
    assert adjusted["c"] is None
    assert adjusted["d"] == pytest.approx(0.8 / 3.0)
    assert sum(len(fits) for fits in FAMILY_FITS.values()) == 27


def test_symmetric_decomposition_closes_exactly_with_relative_tolerance() -> None:
    result = _decompose_enrollment_change(1000.0, 920.0, 1100.0, 1000.0)
    reconstructed = result["population_component"] + result[
        "relationship_component"
    ]
    assert reconstructed == pytest.approx(result["total_change"])
    assert abs(result["closure_residual"]) <= result["closure_tolerance"]
    with pytest.raises(ValueError, match="População de referência não positiva"):
        _decompose_enrollment_change(10.0, 12.0, 0.0, 100.0)


def test_fold_and_random_seed_are_deterministic_without_numeric_ibge_identity() -> None:
    assert _fold_number(NOVA_SANTA_RITA_CODE, 5) == _fold_number(
        NOVA_SANTA_RITA_CODE, 5
    )
    assert 0 <= _fold_number(NOVA_SANTA_RITA_CODE, 10) < 10
    assert _fit_seed("P6_EJA_SPEARMAN", "permutation_99999") == _fit_seed(
        "P6_EJA_SPEARMAN", "permutation_99999"
    )


def test_exact_cluster_sign_fit_uses_declared_grid() -> None:
    rows = []
    for municipality_index in range(9):
        code = f"43{municipality_index:05d}"
        for year_index, year in enumerate(range(2018, 2024)):
            exposure = (
                math.sin((municipality_index + 1) * (year_index + 1))
                + 0.1 * municipality_index
                + 0.2 * year_index
            )
            outcome = (
                0.45 * exposure
                + 0.07 * math.cos((municipality_index + 2) * (year_index + 1))
                + municipality_index
                + year_index
            )
            rows.append(
                {
                    "municipality_ibge_code": code,
                    "year_or_reference_period": str(year),
                    "outcome": outcome,
                    "exposure": exposure,
                }
            )
    fit = fit_fixed_effect_panel(
        pd.DataFrame(rows),
        outcome="outcome",
        exposure="exposure",
        exact_cluster_sign_p=True,
    )
    assert fit["resampling"]["clusterCount"] == 9
    assert fit["resampling"]["denominator"] == 512
    assert fit["p_value"] >= 1 / 512
    assert fit["municipality_count"] == 9


def test_permutation_and_hc3_estimators_return_finite_effects() -> None:
    x = np.arange(10, dtype=float)
    y = np.array([0, 2, 1, 4, 3, 5, 7, 6, 9, 8], dtype=float)
    effect, p_value, extreme = permutation_correlation(
        x,
        y,
        method="spearman",
        seed=123,
        permutations=999,
    )
    assert math.isfinite(effect)
    assert 0 < p_value <= 1
    assert 0 <= extreme <= 999

    frame = pd.DataFrame(
        {
            "municipality_ibge_code": [f"43{index:05d}" for index in range(30)],
            "outcome": 2.0 + 0.5 * x.repeat(3)[:30] + np.linspace(-0.2, 0.2, 30),
            "exposure": x.repeat(3)[:30],
            "control": np.tile([1.0, 2.0, 3.0], 10),
        }
    )
    fit = fit_ols_hc3(
        frame,
        outcome="outcome",
        exposure="exposure",
        controls=("control",),
    )
    assert math.isfinite(fit["coefficient"])
    assert fit["municipality_count"] == 30


def test_materialized_package_contract_when_available() -> None:
    if not DEFAULT_OUTPUT_ROOT.exists():
        pytest.skip("Pacote AA2 ainda não materializado nesta execução em camadas.")
    manifest = validate_existing_output(DEFAULT_OUTPUT_ROOT)
    assert manifest["counts"]["questionCount"] == 8
    assert manifest["independentMaterializationVerification"]["equal"] is True
    verification = manifest["independentMaterializationVerification"]
    assert verification["comparisonScope"] == "NON_MANIFEST_ANALYTICAL_ARTIFACT_SET"
    assert verification["candidateManifestEqualityRequired"] is False
    assert verification["finalManifestNormalization"] == "MULTI_PROCESS_COMMON_EVIDENCE"

    results = pd.read_csv(
        DEFAULT_OUTPUT_ROOT / RESULTS_FILE,
        dtype={"municipality_ibge_code": str},
        keep_default_na=False,
    )
    assert results["analytic_sample_n"].astype(int).ge(0).all()
    assert results["minimum_detectable_effect_state"].eq(
        "NOT_PREREGISTERED_NOT_COMPUTED"
    ).all()
    p7_valid = results[
        results["question_id"].eq("P7_RURALITY_INCLUSION_AND_ACCESS")
        & results["effect_estimate"].ne("null")
    ]
    assert pd.to_numeric(p7_valid["cluster_count"]).eq(10).all()
    assert p7_valid["interval_primary_state"].eq(
        "APPROXIMATE_NON_PRIMARY_EXACT_SIGN_P_PRIMARY"
    ).all()
    p8_per_enrollment = results[
        results["result_id"].eq("P8_ALT_2025_PER_ENROLLMENT")
    ].iloc[0]
    assert (
        p8_per_enrollment["promotion_state"]
        == "BLOCKED_DENOMINATOR_CONSTRUCTION_AND_TERMINAL_INSUFFICIENT"
    )

    heterogeneity = pd.read_csv(
        DEFAULT_OUTPUT_ROOT / HETEROGENEITY_FILE,
        dtype={"municipality_ibge_code": str},
        keep_default_na=False,
    )
    assert heterogeneity["claim_ceiling"].eq("EXPLORATORY_NO_INFERENCE").all()
    assert heterogeneity["promotion_state"].eq(
        "BLOCKED_FROM_MANAGER_FACING"
    ).all()

    claims = json.loads(
        (DEFAULT_OUTPUT_ROOT / CLAIMS_FILE).read_text(encoding="utf-8")
    )
    assert claims["promotionPolicy"]["heterogeneityPromotionState"] == (
        "BLOCKED_FROM_MANAGER_FACING"
    )
    p1 = next(
        claim
        for claim in claims["claims"]
        if claim["questionId"] == "P1_CONTEXT_ADJUSTED_TRAJECTORY"
    )
    assert p1["effectSummary"]["nonFlaggingIsEvidenceOfTypicality"] is False


def test_aa2_report_keeps_mandatory_interpretation_guards_literal() -> None:
    report = (
        DATA_PIPELINE_DIR.parent
        / "docs"
        / "RELATORIO_AA2_AVANCO_ANALITICO_VOCACOES_PNE.md"
    ).read_text(encoding="utf-8")
    assert "não demonstra que o município seja típico" in report
    assert "não significativo após o ajuste familiar" in report
    assert "não “ausência de relação”" in report
    assert "BLOCKED_DENOMINATOR_CONSTRUCTION_AND_TERMINAL_INSUFFICIENT" in report
