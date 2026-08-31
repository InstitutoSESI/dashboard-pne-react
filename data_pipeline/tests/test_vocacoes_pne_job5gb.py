from __future__ import annotations

import json
from pathlib import Path
import sys

import pandas as pd


REPO_ROOT_FOR_IMPORT = Path(__file__).resolve().parents[2]
DATA_PIPELINE_DIR = REPO_ROOT_FOR_IMPORT / "data_pipeline"
if str(DATA_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_PIPELINE_DIR))

from src.vocacoes_pne_job5gb import (  # noqa: E402
    ALLOWED_CLASSIFICATIONS,
    DEFAULT_OUTPUT_ROOT,
    FINAL_STATE,
    NOVA_SANTA_RITA_ID,
    OUTPUT_FILES,
    validate_existing_output,
)


def _read(name: str) -> pd.DataFrame:
    return pd.read_csv(
        DEFAULT_OUTPUT_ROOT / name,
        dtype={"municipality_ibge_code": "string"},
        keep_default_na=False,
        na_values=["null"],
    )


def test_package_is_complete_and_stopped_for_external_judgment() -> None:
    report = validate_existing_output()
    assert report["finalState"] == FINAL_STATE
    assert report["outputCount"] == 15
    assert set(path.name for path in DEFAULT_OUTPUT_ROOT.iterdir()) == set(OUTPUT_FILES)


def test_eja_stages_and_nova_santa_rita_directions_are_preserved() -> None:
    distribution = _read("PAINEL_EJA_DISTRIBUICAO_2022_V1.csv.gz")
    assert "matriculas_por_mil" not in distribution.columns
    assert set(distribution["stage"]) == {"fundamental", "high_school"}
    nsr = distribution[distribution["municipality_ibge_code"].eq(NOVA_SANTA_RITA_ID)].set_index("stage")
    assert nsr.loc["fundamental", "distribution_direction"] == "above_public_share"
    assert nsr.loc["high_school", "distribution_direction"] == "below_public_share"
    assert distribution["network_scope"].eq("total_all_dependencies").all()
    assert not distribution["administrative_dependency_is_analytic_dimension"].astype(bool).any()


def test_adult_denominator_gap_is_explicit_and_not_imputed() -> None:
    dictionary = json.loads((DEFAULT_OUTPUT_ROOT / OUTPUT_FILES[0]).read_text(encoding="utf-8"))
    assert dictionary["denominatorAudit"]["2010"] == "SOURCE_UNAVAILABLE"
    panel = _read("PAINEL_ESCOLARIDADE_ADULTA_2010_2022_V1.csv.gz")
    assert panel.loc[panel["year"].eq(2010), "adult_population_denominator"].isna().all()
    assert panel.loc[panel["year"].eq(2010), "share_percent"].isna().all()


def test_historical_closure_and_integrated_zero_semantics() -> None:
    historical = _read("PAINEL_EJA_HISTORICA_2014_2025_V1.csv.gz")
    pivot = historical.pivot_table(
        index=["entity_scope", "municipality_ibge_code", "year"],
        columns="stage",
        values="eja_enrollments",
        aggfunc="first",
    )
    assert (pivot["total_context"] == pivot["fundamental"] + pivot["high_school"]).all()
    integrated = _read("PAINEL_EJA_INTEGRADA_EPT_V1.csv.gz")
    zeros = integrated[pd.to_numeric(integrated["integrated_eja_enrollments"], errors="raise").eq(0)]
    assert not zeros.empty
    assert zeros["value_status"].eq("observed").all()


def test_vulnerability_is_aggregated_context_without_micro_linkage() -> None:
    panel = _read("PAINEL_VULNERABILIDADE_EDUCACIONAL_V1.csv.gz")
    cadunico = panel[
        panel["context_domain"].eq("registered_vulnerability_context")
    ]
    assert cadunico["reference_period"].eq("2024-12").all()
    assert not panel["micro_linkage_performed"].astype(bool).any()
    assert cadunico["educational_profile_compatibility"].eq("context_only_no_adult_schooling_fields").all()
    assert NOVA_SANTA_RITA_ID in set(panel["municipality_ibge_code"].dropna())


def test_indigenous_specific_public_preserves_lens_and_observed_zeros() -> None:
    panel = _read("PAINEL_VULNERABILIDADE_EDUCACIONAL_V1.csv.gz")
    indigenous = panel[
        panel["context_domain"].eq("indigenous_education_specific_public")
    ]
    assert len(indigenous[indigenous["entity_scope"].eq("municipality")]) == 120
    assert len(indigenous[indigenous["entity_scope"].eq("region")]) == 12
    assert indigenous["territorial_lens"].eq("school_location").all()
    assert indigenous["network_scope"].eq("total_all_dependencies").all()
    nsr = indigenous[indigenous["municipality_ibge_code"].eq(NOVA_SANTA_RITA_ID)]
    assert len(nsr) == 12
    assert pd.to_numeric(nsr["value"], errors="raise").eq(0).all()
    assert nsr["value_status"].eq("observed").all()


def test_special_and_rural_are_school_location_total_network() -> None:
    for name in ("PAINEL_EDUCACAO_ESPECIAL_AEE_V1.csv.gz", "PAINEL_EDUCACAO_RURAL_TERRITORIO_V1.csv.gz"):
        panel = _read(name)
        assert panel["network_scope"].eq("total_all_dependencies").all()
        assert not panel["administrative_dependency_is_analytic_dimension"].astype(bool).any()
        assert panel["administrative_dependency_is_QA_dimension"].astype(bool).all()
        assert NOVA_SANTA_RITA_ID in set(panel["municipality_ibge_code"].dropna())


def test_c1_c12_do_not_approve_automatically() -> None:
    panel = _read("MATRIZ_OPORTUNIDADES_REAVALIADAS_JOB5GB_V1.csv.gz")
    assert set(panel["classification"]).issubset(ALLOWED_CLASSIFICATIONS)
    assert panel["score"].isna().all()
    assert not panel["automatic_approval"].astype(bool).any()
    assert panel["external_judgment_required"].astype(bool).all()
    for index in range(1, 13):
        assert f"c{index}_meaning" in panel
        assert f"c{index}_status" in panel
        assert f"c{index}_evidence" in panel


def test_manifest_proves_no_publication_frontend_network_or_compiler() -> None:
    manifest = json.loads((DEFAULT_OUTPUT_ROOT / OUTPUT_FILES[-1]).read_text(encoding="utf-8"))
    generation = manifest["generation"]
    assert generation["databaseReadOnly"] is True
    assert generation["networkUsed"] is False
    assert generation["publicDataChanged"] is False
    assert generation["frontendChanged"] is False
    assert generation["compilerUsed"] is False
    assert generation["published"] is False
    assert generation["job5gcStarted"] is False
    assert generation["job5hStarted"] is False
    assert manifest["stopForExternalJudgment"] is True
