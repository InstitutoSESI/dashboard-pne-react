from __future__ import annotations

import json
from pathlib import Path
import sys

import pandas as pd


REPO_ROOT_FOR_IMPORT = Path(__file__).resolve().parents[2]
DATA_PIPELINE_DIR = REPO_ROOT_FOR_IMPORT / "data_pipeline"
if str(DATA_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_PIPELINE_DIR))

from src.vocacoes_pne_job5ga import (
    ALLOWED_CLASSIFICATIONS,
    DEFAULT_OUTPUT_ROOT,
    NOVA_SANTA_RITA_ID,
    OUTPUT_FILES,
    REPO_ROOT,
    validate_existing_output,
)


def _read(name: str) -> pd.DataFrame:
    return pd.read_csv(
        DEFAULT_OUTPUT_ROOT / name,
        dtype={"municipality_ibge_code": "string"},
        keep_default_na=False,
        na_values=["null"],
    )


def test_job5ga_package_is_complete_and_valid() -> None:
    report = validate_existing_output()
    assert report["finalState"] == "JOB_5GA_PARTIAL_WITH_DATA_GAPS"
    assert report["outputCount"] == 12
    assert set(path.name for path in DEFAULT_OUTPUT_ROOT.iterdir()) == set(OUTPUT_FILES)


def test_trajectory_is_official_municipal_and_never_a_regional_rate() -> None:
    panel = _read("PAINEL_TRAJETORIA_OFICIAL_DESCRITIVA_V1.csv.gz")
    assert panel["network_scope"].eq("total_all_dependencies").all()
    assert panel["source_dependency_qa"].eq("total").all()
    assert panel["regional_rate_value"].isna().all()
    assert panel["regional_rate_method"].eq("not_computed").all()
    assert NOVA_SANTA_RITA_ID in set(panel["municipality_ibge_code"])
    assert not panel.duplicated(["municipality_ibge_code", "year", "stage", "metric"]).any()


def test_birth_gap_and_population_school_lenses_are_explicit() -> None:
    panel = _read("PAINEL_NASCIMENTOS_EDUCACAO_INFANTIL_V1.csv.gz")
    births = panel[panel["metric"].eq("births")]
    assert births["value"].isna().all()
    assert births["value_status"].eq("unavailable").all()
    assert set(panel["territorial_lens"]) == {"resident_population", "school_location"}
    assert births.loc[births["year"].eq(2015), "vale_births_endpoint_value"].eq(13004).all()
    assert births.loc[births["year"].eq(2024), "vale_births_endpoint_value"].eq(9276).all()


def test_conditions_are_context_only_and_have_no_correlation_insight() -> None:
    panel = _read("PAINEL_CONDICOES_ESCOLARES_TOTAL_V1.csv.gz")
    assert not panel["causal_interpretation_allowed"].astype(str).str.casefold().isin({"true", "1"}).any()
    assert not panel["correlation_used_as_insight"].astype(str).str.casefold().isin({"true", "1"}).any()
    assert "synthetic_index" not in set(panel["metric"])


def test_mechanical_pressure_closes_and_is_not_forecast() -> None:
    panel = _read("PAINEL_PRESSAO_MECANICA_COORTES_AUDITADO_V1.csv.gz")
    assert pd.to_numeric(panel["formula_closure_residual"], errors="raise").abs().max() <= 1e-12
    assert pd.to_numeric(panel["cohort_size_closure_residual"], errors="raise").abs().max() == 0
    assert not panel["is_forecast"].astype(str).str.casefold().isin({"true", "1"}).any()
    assert panel["classification"].eq("PRESSAO_MECANICA_TRANSPARENTE").all()


def test_nova_santa_rita_has_all_required_reconstructions() -> None:
    payload = json.loads((DEFAULT_OUTPUT_ROOT / "NOVA_SANTA_RITA_JOB5GA_V1.json").read_text(encoding="utf-8"))
    assert payload["municipalityIbgeCode"] == NOVA_SANTA_RITA_ID
    assert payload["sectionCount"] == 11
    assert {item["id"] for item in payload["sections"]} == {
        "educacao_infantil", "fundamental", "anos_iniciais", "anos_finais", "medio",
        "docentes", "jornada", "tempo_integral", "condicoes", "trajetoria_oficial",
        "pressao_mecanica",
    }
    assert all(item["series"] for item in payload["sections"])


def test_c1_c12_are_evidence_without_score_or_auto_approval() -> None:
    panel = _read("MATRIZ_OPORTUNIDADES_REAVALIADAS_JOB5GA.csv.gz")
    assert set(panel["classification"]).issubset(ALLOWED_CLASSIFICATIONS)
    assert panel["score"].isna().all()
    assert not panel["automatic_approval"].astype(str).str.casefold().isin({"true", "1"}).any()
    for criterion in range(1, 13):
        assert f"c{criterion}_meaning" in panel.columns
        assert f"c{criterion}_status" in panel.columns
        assert f"c{criterion}_evidence" in panel.columns


def test_manifest_records_stop_and_no_public_or_frontend_writes() -> None:
    payload = json.loads((DEFAULT_OUTPUT_ROOT / "MANIFEST_JOB5GA.json").read_text(encoding="utf-8"))
    assert payload["stopForExternalJudgment"] is True
    assert payload["generation"]["publicDataChanged"] is False
    assert payload["generation"]["frontendChanged"] is False
    assert payload["generation"]["networkUsed"] is False
    assert payload["generation"]["databaseReadOnly"] is True
    assert payload["generation"]["compilerUsed"] is False
    assert payload["generation"]["job6Started"] is False
    assert DEFAULT_OUTPUT_ROOT.resolve() != (REPO_ROOT / "public" / "data").resolve()


def test_all_panel_grains_units_value_states_and_municipal_universe() -> None:
    expected_codes = {
        "4303905", "4306403", "4307609", "4307708", "4310801",
        "4313375", "4313409", "4314803", "4318705", "4320008",
    }
    allowed_states = {"observed", "null", "unavailable", "suppressed", "not_applicable"}
    specifications = {
        "PAINEL_TRAJETORIA_OFICIAL_DESCRITIVA_V1.csv.gz": ["municipality_ibge_code", "year", "stage", "metric"],
        "PAINEL_NASCIMENTOS_EDUCACAO_INFANTIL_V1.csv.gz": ["municipality_ibge_code", "year", "stage", "metric"],
        "PAINEL_DOCENTES_TURMAS_JORNADA_V1.csv.gz": ["municipality_ibge_code", "year", "stage", "metric"],
        "PAINEL_CONDICOES_ESCOLARES_TOTAL_V1.csv.gz": ["municipality_ibge_code", "year", "stage", "metric"],
    }
    for name, grain in specifications.items():
        panel = _read(name)
        assert not panel.duplicated(grain).any(), name
        assert set(panel["municipality_ibge_code"].dropna()) == expected_codes, name
        assert set(panel["value_status"].dropna()).issubset(allowed_states), name
        assert panel["unit"].notna().all(), name
    pressure = _read("PAINEL_PRESSAO_MECANICA_COORTES_AUDITADO_V1.csv.gz")
    assert not pressure.duplicated(["entity_scope", "municipality_ibge_code", "stage", "target_year"]).any()
    assert set(pressure.loc[pressure["entity_scope"].eq("municipality"), "municipality_ibge_code"]) == expected_codes


def test_explicit_zero_is_observed_and_frozen_inputs_remain_verified() -> None:
    zero_rows = []
    for name in (
        "PAINEL_TRAJETORIA_OFICIAL_DESCRITIVA_V1.csv.gz",
        "PAINEL_DOCENTES_TURMAS_JORNADA_V1.csv.gz",
        "PAINEL_CONDICOES_ESCOLARES_TOTAL_V1.csv.gz",
    ):
        panel = _read(name)
        rows = panel[pd.to_numeric(panel["value"], errors="coerce").eq(0)]
        zero_rows.append(len(rows))
        assert rows["value_status"].eq("observed").all(), name
    assert sum(zero_rows) > 0
    # validate_existing_output() also verifies every frozen fingerprint from Jobs 2/5A–5F.
    assert validate_existing_output()["promotion"] == "validated_existing"
