from __future__ import annotations

import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd


REPO_ROOT_FOR_IMPORT = Path(__file__).resolve().parents[2]
DATA_PIPELINE_DIR = REPO_ROOT_FOR_IMPORT / "data_pipeline"
if str(DATA_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_PIPELINE_DIR))

from src.vocacoes_pne_job5gbr import (  # noqa: E402
    CANONICAL_CRITERIA,
    DEFAULT_OUTPUT_ROOT,
    FINAL_STATE,
    NOVA_SANTA_RITA_ID,
    ORIGINAL_FILES,
    OUTPUT_FILES,
    SOURCE_ROOT,
    materialize,
    sha256_file,
    validate_existing_output,
)


def _read(name: str, root: Path = DEFAULT_OUTPUT_ROOT) -> pd.DataFrame:
    return pd.read_csv(
        root / name,
        dtype={"municipality_ibge_code": "string"},
        keep_default_na=False,
        na_values=["null"],
    )


def _truthy(series: pd.Series) -> pd.Series:
    return series.astype(str).str.casefold().isin({"true", "1"})


def test_package_is_complete_and_ready_for_external_judgment() -> None:
    report = validate_existing_output()
    assert report["finalState"] == FINAL_STATE
    assert report["outputCount"] == 18
    assert report["originalArtifactCount"] == len(ORIGINAL_FILES) == 15
    assert {path.name for path in DEFAULT_OUTPUT_ROOT.iterdir()} == set(OUTPUT_FILES)


def test_original_job5gb_hashes_remain_identical() -> None:
    manifest = json.loads((SOURCE_ROOT / "MANIFEST_JOB5GB.json").read_text(encoding="utf-8"))
    declared = {item["path"]: item for item in manifest["artifacts"]}
    for name in ORIGINAL_FILES:
        path = SOURCE_ROOT / name
        if name in declared:
            assert path.stat().st_size == declared[name]["byteSize"]
            assert sha256_file(path) == declared[name]["sha256"]


def test_adult_categories_are_guarded_and_count_only() -> None:
    panel = _read("PAINEL_ESCOLARIDADE_ADULTA_2010_2022_V1_1.csv.gz")
    assert panel["percentage_point_change_2010_2022"].isna().all()
    assert not _truthy(panel["intercensal_share_change_allowed"]).any()
    assert not _truthy(panel["improvement_claim_allowed"]).any()
    assert panel["municipal_contribution_to_vale_change_percent_role"].eq(
        "INTERNAL_NET_CHANGE_DECOMPOSITION_ONLY"
    ).all()
    category = panel.drop_duplicates("schooling_category").set_index("schooling_category")
    assert bool(category.loc["fundamental_completed_or_more", "is_cumulative"])
    assert category.loc["high_school_completed_or_more", "parent_category"] == (
        "fundamental_completed_or_more"
    )
    assert bool(category.loc["fundamental_completed_without_high_school", "is_derived"])
    assert category.loc["without_fundamental_completed", "category_role"] == (
        "exclusive_2022_only_band"
    )


def test_distribution_uses_stage_specific_contracts() -> None:
    panel = _read("PAINEL_EJA_DISTRIBUICAO_2022_V1_1.csv.gz")
    fundamental = panel[panel["stage"].eq("fundamental")]
    high_school = panel[panel["stage"].eq("high_school")]
    assert fundamental["source_contract"].eq(
        "JOB2C_ESTIMATED_18PLUS_TOTAL_MINUS_CENSUS_COMPLETION"
    ).all()
    assert fundamental["regional_count_difference_vs_adult_panel"].eq(18401).all()
    assert high_school["source_contract"].eq(
        "CENSUS_COMPLETION_COUNT_DIFFERENCE_2022"
    ).all()
    assert set(panel["distribution_object_id"]) == {
        "EJA_DISTRIBUICAO_FUNDAMENTAL_2022",
        "EJA_DISTRIBUICAO_MEDIO_2022",
    }
    assert not _truthy(panel["cross_stage_combination_allowed"]).any()


def test_history_closes_and_flags_context_without_cause() -> None:
    panel = _read("PAINEL_EJA_HISTORICA_2014_2025_V1_1.csv.gz")
    pivot = panel.pivot_table(
        index=["entity_scope", "municipality_ibge_code", "municipality_name", "year"],
        columns="stage",
        values="eja_enrollments",
        aggfunc="first",
        dropna=False,
    ).dropna(how="all")
    assert np.allclose(pivot["fundamental"] + pivot["high_school"], pivot["total_context"])
    required = panel[
        panel["entity_scope"].eq("region")
        & panel["stage"].eq("high_school")
        & panel["year"].eq(2018)
    ]
    assert required["series_context_status"].eq(
        "ABRUPT_REGIONAL_MOVEMENT_REQUIRES_CONTEXT"
    ).all()
    novo_hamburgo = panel[
        panel["municipality_name"].eq("Novo Hamburgo")
        & panel["stage"].eq("high_school")
        & panel["year"].eq(2018)
    ]
    assert novo_hamburgo["series_context_status"].eq(
        "MUNICIPAL_CONCENTRATION_IN_ABRUPT_REGIONAL_MOVEMENT"
    ).all()
    assert not _truthy(panel["definition_metadata_available"]).any()
    assert not _truthy(panel["institutional_explanation_allowed"]).any()


def test_integrated_modalities_close_and_observed_zeros_are_guarded() -> None:
    panel = _read("PAINEL_EJA_INTEGRADA_EPT_V1_1.csv.gz")
    pivot = panel.pivot_table(
        index=["entity_scope", "municipality_ibge_code", "municipality_name", "year"],
        columns="modality",
        values="integrated_eja_enrollments",
        aggfunc="first",
        dropna=False,
    ).dropna(how="all")
    assert np.allclose(
        pivot["technical_integrated"] + pivot["fic_fundamental"] + pivot["fic_high_school"],
        pivot["integrated_total"],
    )
    zeros = pd.to_numeric(panel["integrated_eja_enrollments"], errors="raise").eq(0)
    assert panel.loc[zeros, "observation_semantics"].eq("observed_zero").all()
    assert not _truthy(panel.loc[zeros, "zero_headline_allowed"]).any()
    structural = panel["modality"].eq("fic_high_school") & panel["year"].ge(2023)
    assert panel.loc[structural, "period_context_status"].eq(
        "STRUCTURAL_SERIES_CHANGE_REQUIRES_CONTEXT"
    ).all()


def test_vulnerability_and_indigenous_are_separate_objects() -> None:
    vulnerability = _read("PAINEL_VULNERABILIDADE_EDUCACIONAL_V1_1.csv.gz")
    indigenous = _read("PAINEL_EDUCACAO_INDIGENA_V1.csv.gz")
    assert len(vulnerability) == 121
    assert len(indigenous) == 132
    assert set(vulnerability["object_id"]) == {"E_VULNERABILIDADE"}
    assert set(indigenous["object_id"]) == {"E2_EDUCACAO_INDIGENA"}
    assert not vulnerability["metric"].str.contains("indigenous").any()
    nsr = indigenous[indigenous["municipality_ibge_code"].eq(NOVA_SANTA_RITA_ID)]
    assert pd.to_numeric(nsr["value"], errors="raise").eq(0).all()
    assert not _truthy(nsr["municipal_card_eligible"]).any()
    assert set(
        indigenous.loc[_truthy(indigenous["municipal_card_eligible"]), "municipality_ibge_code"]
    ) == {"4318705"}


def test_special_and_rural_non_additivity_guardrails() -> None:
    special = _read("PAINEL_EDUCACAO_ESPECIAL_AEE_V1_1.csv.gz")
    inclusion = special[special["metric"].isin(
        ["special_enrollments", "common_class_enrollments", "exclusive_class_enrollments"]
    )]
    pivot = inclusion.pivot_table(
        index=["entity_scope", "municipality_ibge_code", "municipality_name", "year", "stage"],
        columns="metric",
        values="value",
        aggfunc="first",
        dropna=False,
    ).dropna(how="all")
    assert np.allclose(
        pivot["common_class_enrollments"] + pivot["exclusive_class_enrollments"],
        pivot["special_enrollments"],
    )
    assert not _truthy(special["stage_breakdown_additive"]).any()
    schools = special["metric_family"].eq("SCHOOLS")
    assert not _truthy(special.loc[schools, "stacking_allowed"]).any()

    rural = _read("PAINEL_EDUCACAO_RURAL_TERRITORIO_V1_1.csv.gz")
    rural_schools = rural["metric"].eq("rural_schools")
    assert not _truthy(rural.loc[rural_schools, "stage_sum_closure_validated"]).any()
    assert _truthy(rural.loc[rural["stage"].eq("all"), "total_context_only"]).all()
    assert not _truthy(rural.loc[rural["stage"].eq("all"), "stacking_allowed"]).any()


def test_links_matrices_and_nsr_dossier_have_correct_roles() -> None:
    links = _read("MATRIZ_VINCULOS_PNE_PME_JOB5GB_V1_1.csv.gz")
    assert links["page_role"].eq("INTERNAL_METADATA_LAYER").all()
    assert not _truthy(links["standalone_visual_module"]).any()
    teachers = links["analysis_id"].str.startswith("teacher_")
    assert teachers.sum() == 4
    assert not _truthy(links.loc[teachers, "materialized_fact_available"]).any()
    assert not _truthy(links.loc[teachers, "adds_concrete_decision"]).any()

    qa = _read("MATRIZ_QA_JOB5GB_V1_1.csv.gz")
    canonical = _read("MATRIZ_C1_C12_CANONICA_JOB5GB_V1_1.csv.gz")
    opportunities = _read("MATRIZ_OPORTUNIDADES_REAVALIADAS_JOB5GB_V1_1.csv.gz")
    assert set(qa["qa_control_id"]) == {f"QA{i}_JOB5GB" for i in range(1, 13)}
    assert set(canonical["criterion_id"]) == set(CANONICAL_CRITERIA)
    assert len(qa) == len(canonical) == 108
    assert len(opportunities) == 9
    for frame in (qa, canonical, opportunities):
        assert frame["score"].isna().all()
        assert not _truthy(frame["automatic_approval"]).any()
    assert not canonical.loc[canonical["criterion_id"].eq("C5"), "criterion_status"].eq(
        "SUPPORTED"
    ).any()

    dossier = json.loads(
        (DEFAULT_OUTPUT_ROOT / "NOVA_SANTA_RITA_JOB5GB_V1_1.json").read_text(encoding="utf-8")
    )
    assert dossier["technicalGroupCount"] == 9
    assert dossier["compactMacroGroupCount"] == 4
    assert dossier["technicalGroupsAreMandatoryCards"] is False
    indigenous_group = next(
        group for group in dossier["technicalGroups"] if group["id"] == "educacao_indigena"
    )
    assert indigenous_group["futureDisplayEligibility"] == (
        "INELIGIBLE_NO_POSITIVE_MUNICIPAL_SCHOOL_FACT"
    )


def test_generation_is_byte_reproducible(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    materialize(first)
    materialize(second)
    assert {path.name for path in first.iterdir()} == set(OUTPUT_FILES)
    assert {path.name for path in second.iterdir()} == set(OUTPUT_FILES)
    first_hashes = {path.name: sha256_file(path) for path in first.iterdir()}
    second_hashes = {path.name: sha256_file(path) for path in second.iterdir()}
    assert first_hashes == second_hashes


def test_manifest_records_all_forbidden_operations_as_false() -> None:
    manifest = json.loads(
        (DEFAULT_OUTPUT_ROOT / "MANIFEST_JOB5GBR.json").read_text(encoding="utf-8")
    )
    assert manifest["finalState"] == FINAL_STATE
    assert manifest["stopForExternalJudgment"] is True
    generation = manifest["generation"]
    for key in (
        "sourceJobArtifactsChanged",
        "job5garArtifactsChanged",
        "job5garReexecuted",
        "databaseUsed",
        "networkUsed",
        "externalAcquisitionUsed",
        "publicDataChanged",
        "frontendChanged",
        "compilerUsed",
        "fullBuildUsed",
        "published",
        "publicNarrativeProduced",
        "job5gcStarted",
        "job5hStarted",
        "job6Started",
    ):
        assert generation[key] is False
