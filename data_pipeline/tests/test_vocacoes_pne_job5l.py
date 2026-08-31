from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from src.vocacoes_pne_job5l import (
    CONTRACT_PATH,
    DEFAULT_OUTPUT_ROOT,
    FINAL_STATE,
    INTERNAL_FILES,
    NSR_CODE,
    PACKAGE_FILES,
    _region_codes,
    _select_rais_columns,
    build_conditional_fronts,
    build_f6_panel,
    validate_database_sources,
    validate_existing_output,
    verify_frozen_integrity,
)


SOURCE_ROOT = DEFAULT_OUTPUT_ROOT / "sources"


def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(
        path,
        compression="gzip",
        dtype={"municipality_ibge_code": "string", "entity_id": "string"},
        keep_default_na=True,
    )


def test_contract_has_exact_shared_package_and_closed_gate() -> None:
    contract = _json(CONTRACT_PATH)
    assert contract["packageFiles"] == list(PACKAGE_FILES)
    assert len(PACKAGE_FILES) == 12
    assert len(INTERNAL_FILES) == 17
    assert contract["gate11"] == "CLOSED"
    assert contract["internalOnly"] is True
    assert contract["job5MAllowed"] is False
    assert FINAL_STATE in contract["allowedFinalStates"]


def test_rais_municipality_field_changes_with_reprocessed_layout() -> None:
    common = [
        "Ind Vínculo Ativo 31/12 - Código",
        "Idade",
        "Escolaridade Após 2005 - Código",
        "Qtd Hora Contr",
        "Vl Rem Média Nom",
        "Tempo Emprego",
        "Tipo Vínculo - Código",
        "CBO 2002 Ocupação - Código",
        "IBGE Subsetor - Código",
        "Tamanho Estabelecimento - Código",
    ]
    legacy = _select_rais_columns([*common, "Mun Trab", "Município"])
    reprocessed = _select_rais_columns(
        [*common, "Município Trab - Código", "Município - Código"]
    )
    assert legacy["municipality"] == "Mun Trab"
    assert reprocessed["municipality"] == "Município - Código"


def test_database_snapshot_is_read_only_and_complete() -> None:
    manifest = validate_database_sources(SOURCE_ROOT / "database")
    assert manifest["transactionReadOnly"] is True
    assert manifest["rollbackPerformed"] is True
    assert len(manifest["artifacts"]) == 7
    assert {item["rowCount"] for item in manifest["artifacts"]} >= {497}


def test_conditional_fronts_do_not_fabricate_same_person_estimates() -> None:
    f2, f5 = build_conditional_fronts()
    assert len(f2) == 22
    assert len(f5) == 11
    assert f2["front_state"].eq("WAITING_OFFICIAL_RELEASE").all()
    assert f5["front_state"].eq("WAITING_OFFICIAL_RELEASE").all()
    assert f2[
        [
            "weighted_estimate",
            "standard_error",
            "confidence_interval_lower",
            "confidence_interval_upper",
            "coefficient_of_variation",
            "unweighted_n",
        ]
    ].isna().all().all()
    assert f5["estimate"].isna().all()


def test_f6_keeps_stages_and_lenses_separate() -> None:
    panel = build_f6_panel()
    assert len(panel) == 22
    assert set(panel["stage"]) == {"fundamental", "high_school"}
    assert panel["network_scope"].eq("total_all_dependencies").all()
    assert not panel["same_person"].any()
    assert not panel["resident_population_is_manifest_demand"].any()
    assert not panel["cross_stage_combination_allowed"].any()
    nsr = panel[panel["municipality_ibge_code"].eq(NSR_CODE)].set_index("stage")
    assert nsr.loc["fundamental", "distribution_difference_percentage_points"] == pytest.approx(2.648263, abs=1e-6)
    assert nsr.loc["high_school", "distribution_difference_percentage_points"] == pytest.approx(-2.605095, abs=1e-6)


def test_frozen_inputs_remain_at_preflight_digests() -> None:
    preflight = verify_frozen_integrity()
    assert preflight["frozenRootDigests"]["job5j"] == "f31b230fb9268ca57c15f1e322ef9317d841288f7408a9638b0042343a5fb57c"
    assert preflight["frozenRootDigests"]["job5k"] == "75e5b1ce06d77de7a6e99a6e4f64b040110d8961ea857efc0f5a2e89cbcc52ff"
    assert preflight["publicDataTreeDigestSha256"] == "4a52e3891163cb3427c5c01f2ef5414c5fe7855dd491a9a125b509899dcc23e1"


def test_generated_package_contract_and_analytical_boundaries() -> None:
    if not (DEFAULT_OUTPUT_ROOT / "MANIFEST_JOB5L.json").is_file():
        pytest.skip("pacote Job 5L ainda não materializado")
    manifest = validate_existing_output(
        DEFAULT_OUTPUT_ROOT,
        source_root=SOURCE_ROOT,
        verify_sources=False,
    )
    assert manifest["finalState"] == FINAL_STATE
    assert manifest["counts"]["stateMunicipalityCount"] == 497
    assert manifest["counts"]["regionMunicipalityCount"] == 10
    assert manifest["counts"]["f1EligibleModelCount"] == 11
    assert manifest["counts"]["candidateInsightCount"] <= 8
    assert manifest["generation"]["publicDataChanged"] is False
    assert manifest["generation"]["frontendChanged"] is False
    assert manifest["generation"]["publicationPerformed"] is False

    f1 = _csv(DEFAULT_OUTPUT_ROOT / "internal" / "RESULTADOS_AJUSTADOS_F1_JOB5L.csv.gz")
    assert len(f1) == 497 * 3 * 4
    assert f1["municipality_ibge_code"].nunique() == 497
    assert f1["administrative_dependency_role"].eq("qa_only").all()
    assert not f1["causal_interpretation_allowed"].any()
    assert not f1["ranking_allowed"].any()

    f3 = _csv(DEFAULT_OUTPUT_ROOT / "internal" / "PAINEL_RAIS_COMPOSICAO_JOVEM_F3_JOB5L.csv.gz")
    assert set(pd.to_numeric(f3["year"]).astype(int)) == set(range(2019, 2026))
    assert set(f3["age_group"]) == {"15_17", "18_24"}
    assert f3["unit_of_analysis"].eq("active_formal_bond_at_31_12").all()
    assert not f3["same_person"].any()
    assert not f3["real_value_materialized"].any()

    heterogeneity = _csv(
        DEFAULT_OUTPUT_ROOT / "MATRIZ_HETEROGENEIDADE_10_MUNICIPIOS_JOB5L.csv.gz"
    )
    assert set(heterogeneity["municipality_ibge_code"].dropna()) == set(_region_codes())
    assert NSR_CODE in set(heterogeneity["municipality_ibge_code"].dropna())

    qa = _json(DEFAULT_OUTPUT_ROOT / "QA_SUMMARY_JOB5L.json")
    assert qa["result"] == "PASS_WITH_EXPLICIT_LIMITS"
    assert qa["failedCount"] == 0
