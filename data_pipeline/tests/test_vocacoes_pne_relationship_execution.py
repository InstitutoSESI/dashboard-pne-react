from __future__ import annotations

import json

import numpy as np
import pandas as pd

from src.vocacoes_pne_relationship_execution import (
    EXECUTION_CONTRACT_PATH,
    EXPECTED_EXECUTION_CONTRACT_SHA256,
    EXPECTED_PARENT_DIGEST,
    PREREGISTRATION_ROOT,
    base_result_record,
    bh_adjust,
    frame_feasibility,
    sha256_file,
    shifted_exposure_frame,
)


def test_execution_contract_remains_frozen() -> None:
    assert sha256_file(EXECUTION_CONTRACT_PATH) == EXPECTED_EXECUTION_CONTRACT_SHA256
    manifest = json.loads(
        (PREREGISTRATION_ROOT / "MANIFEST.json").read_text(encoding="utf-8")
    )
    assert manifest["artifactSetDigestSha256"] == EXPECTED_PARENT_DIGEST


def test_fixed_denominator_bh_keeps_invalid_placeholders() -> None:
    assert bh_adjust([0.01, 0.04, 1.0, 1.0]) == [0.04, 0.08, 1.0, 1.0]


def test_three_period_short_panel_lead_is_infeasible_without_relaxation() -> None:
    rows = []
    for municipality in range(9):
        code = f"43{municipality:05d}"
        for year in (2023, 2024, 2025):
            rows.append(
                {
                    "entityId": code,
                    "year": year,
                    "outcome": municipality + year / 1000,
                    "exposure": municipality * 2 + year / 1000,
                    "control0": municipality + 1,
                }
            )
    frame = pd.DataFrame(rows)
    method_presets = {
        "SHORT_PANEL_VALE": {
            "minimumMunicipalities": 9,
            "minimumPeriods": 3,
        }
    }
    primary = frame_feasibility(
        frame,
        method_preset="SHORT_PANEL_VALE",
        method_presets=method_presets,
    )
    lead = frame_feasibility(
        shifted_exposure_frame(frame, -1),
        method_preset="SHORT_PANEL_VALE",
        method_presets=method_presets,
    )
    assert primary["feasible"] is True
    assert lead["feasible"] is False
    assert "periods=2<minimum=3" in lead["reasons"]


def test_result_contract_never_allows_causal_claim() -> None:
    hypothesis = {
        "hypothesisId": "H",
        "familyId": "F",
        "multiplicityFamily": "F",
        "lane": "demography_network",
        "methodPreset": "PANEL_RS",
        "priority": "PRIMARY",
        "resultKnowledgeState": "NEW_PRETEST",
        "entryClaimCeiling": "ROBUST_ASSOCIATION",
        "exposureVariableId": "X",
        "outcomeVariableId": "Y",
        "controls": [],
        "expectedDirection": "positive",
        "effectScale": "unit",
    }
    variables = {
        "X": {"territorialLens": "resident_population"},
        "Y": {"territorialLens": "school_location"},
    }
    result = base_result_record(hypothesis, variables)
    assert result["causalClaimAllowed"] is False
    assert result["lensComparisonState"] == (
        "EXPLICIT_CROSS_LENS_ECOLOGICAL_COMPARISON"
    )


def test_no_number_conversion_is_needed_for_ibge_identity() -> None:
    codes = np.asarray(["4303905", "4313375", "4320008"], dtype=str)
    assert all(len(code) == 7 and code.isdigit() for code in codes)
