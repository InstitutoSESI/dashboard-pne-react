from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import re

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_ROOT = REPO_ROOT / ".tmp" / "vocacoes-pne" / "v7-job5h"
GCR_ROOT = REPO_ROOT / ".tmp" / "vocacoes-pne" / "v7-job5gcr"
GD_ROOT = REPO_ROOT / ".tmp" / "vocacoes-pne" / "v7-job5gd"
CANONICAL_HASH = "cd19af79a375b07390c7a2fde10135f9293a999bb3a3848a65ede678b74f3ed6"
INCORRECT_GD_HASH = "cd19af3cf951349cff06c9bb048f9f195e30b756fa309cda95b106810e85b149"
EXPECTED_PNE_ALLOWLIST = {
    "1.a",
    "1.c",
    "3.a",
    "4.a",
    "4.b",
    "4.c",
    "4.d",
    "5.a",
    "5.b",
    "5.d",
    "6.a",
    "8.b",
    "8.c",
    "11.a",
    "11.b",
    "11.c",
    "12.a",
    "12.b",
    "17.a",
    "17.b",
    "17.d",
    "17.f",
    "18.b",
    "19.c",
}


def _json(name: str) -> dict:
    return json.loads((OUTPUT_ROOT / name).read_text(encoding="utf-8"))


def _csv(name: str) -> pd.DataFrame:
    return pd.read_csv(OUTPUT_ROOT / name, compression="gzip", dtype=str)


def _sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _iter_strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _iter_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_strings(item)


def test_catalog_separates_thirteen_families_from_143_variants() -> None:
    catalog = _json("CATALOGO_EDITORIAL_MAXIMO_JOB5H.json")
    corpus = _json("CORPUS_VARIANTES_TERRITORIAIS_JOB5H.json")
    families = catalog["storyFamilies"]
    variants = corpus["storyVariants"]

    assert catalog["fixedCardCap"] is None
    assert catalog["old99RowsArePublicStories"] is False
    assert len(families) == len({item["story_family_id"] for item in families}) == 13
    assert len(variants) == len({item["story_variant_id"] for item in variants}) == 143
    assert set(Counter(item["story_family_id"] for item in variants).values()) == {11}
    assert all(item["story_variant_id"] != item["story_family_id"] for item in variants)
    assert all(item["gate11"] == "CLOSED" for item in variants)
    assert all(item["public_narrative_authorized"] is False for item in variants)


def test_contracts_use_native_typed_structures_and_canonical_aliases() -> None:
    catalog = _json("CATALOGO_EDITORIAL_MAXIMO_JOB5H.json")
    corpus = _json("CORPUS_VARIANTES_TERRITORIAIS_JOB5H.json")
    dictionary = _json("DICIONARIO_TIPADO_CANONICO_JOB5H.json")

    assert dictionary["stages"]["aliases"]["medio"] == "high_school"
    assert dictionary["stages"]["aliases"]["pre_escola"] == "pre_school_age_4_5"
    assert set(dictionary["territorialLenses"]) == {
        "resident_population",
        "student_residence",
        "school_location",
        "rural_school_location",
        "workplace",
        "municipal_executor",
    }
    required_family_fields = {
        "story_family_id",
        "direction_id",
        "macroblock_id",
        "internal_title",
        "internal_summary",
        "regional_question",
        "municipal_question",
        "planning_value",
        "incremental_value_beyond_demography",
        "primary_or_secondary_role",
        "conditional_display_rule",
        "default_expansion_state",
        "recommended_sequence",
        "recommended_primary_visual",
        "recommended_secondary_visuals",
        "comparison_contract",
        "monitoring_indicators",
        "institutional_responsibilities",
        "canonical_pne_goal_links",
        "pme_goal_links",
        "planning_themes",
        "allowed_claims",
        "forbidden_claims",
        "interpretation_limits",
        "source_refs",
        "source_periods",
        "territorial_lenses",
        "network_scope",
        "evidence_state",
        "materiality_state",
        "manager_review_state",
        "job5i_ready_state",
    }
    required_variant_fields = {
        "story_variant_id",
        "story_family_id",
        "variant_scope",
        "entity_id",
        "municipality_ibge_code",
        "municipality_name",
        "regional_facts",
        "municipal_facts",
        "municipal_distribution",
        "state_comparison",
        "change_over_time",
        "contribution_to_region",
        "comparison_method",
        "named_input_metrics",
        "visual_data",
        "source_refs",
        "periods",
        "territorial_lenses",
        "availability_state",
        "zero_state",
        "small_volume_state",
        "allowed_claims",
        "forbidden_claims",
        "planning_question",
        "monitoring_indicator",
        "institutional_responsibility",
        "draft_internal_title",
        "draft_internal_summary",
        "external_judgment_required",
    }
    for family in catalog["storyFamilies"]:
        assert required_family_fields <= set(family)
        assert isinstance(family["pne_links"], list)
        assert isinstance(family["pme_goal_links"], list)
        assert isinstance(family["planning_themes"], list)
        assert all(isinstance(link, dict) for link in family["pne_links"])
    for variant in corpus["storyVariants"]:
        assert required_variant_fields <= set(variant)
        assert isinstance(variant["named_inputs"], list)
        assert isinstance(variant["named_input_metrics"], list)
        assert variant["named_input_metrics"] == variant["named_inputs"]
        assert isinstance(variant["regional_facts"], list)
        assert isinstance(variant["municipal_facts"], list)
        assert isinstance(variant["visual_data"], dict)
        assert isinstance(variant["change_over_time"], list)
        assert isinstance(variant["contribution_to_region"], dict)
        assert isinstance(variant["municipal_distribution"], list)
        assert isinstance(variant["pne_links"], list)
        assert len(variant["municipal_distribution"]) == 10
        assert all(isinstance(item, dict) for item in variant["named_inputs"])
        required = {
            "metric_id",
            "label",
            "value",
            "unit",
            "period",
            "source_ref",
            "territorial_lens",
            "aggregation_rule",
            "comparison_role",
            "availability_state",
        }
        assert all(required <= set(item) for item in variant["named_inputs"])


def test_provenance_errata_records_both_hashes_without_mutating_frozen_manifest() -> None:
    gcr_fact = GCR_ROOT / "MATRIZ_CATALOGO_FATOS_NOVA_SANTA_RITA_JOB5GCR_V1.csv.gz"
    gd_manifest = json.loads((GD_ROOT / "MANIFEST_JOB5GD.json").read_text(encoding="utf-8"))
    errata = (OUTPUT_ROOT / "ERRATA_PROVENIENCIA_JOB5GD.md").read_text(encoding="utf-8")
    manifest = _json("MANIFEST_JOB5H.json")

    assert _sha256(gcr_fact) == CANONICAL_HASH
    assert (
        gd_manifest["contract"]["factCatalogCorrection"]["sourceArtifactSha256"]
        == INCORRECT_GD_HASH
    )
    assert CANONICAL_HASH in errata
    assert INCORRECT_GD_HASH in errata
    assert manifest["frozenInputIntegrity"]["before"] == manifest["frozenInputIntegrity"]["after"]


def test_pne_links_are_legal_and_pme_is_not_materialized() -> None:
    catalog = _json("CATALOGO_EDITORIAL_MAXIMO_JOB5H.json")
    links = _json("VINCULOS_PNE_CANONICOS_JOB5H.json")
    pme = _json("ESTADO_PME_TEMAS_PLANEJAMENTO_JOB5H.json")
    canonical = json.loads(
        (REPO_ROOT / "contracts" / "pne2026-goal-indicator-contract.json").read_text(
            encoding="utf-8"
        )
    )

    used_refs = {
        link["legal_goal_ref"]
        for family in catalog["storyFamilies"]
        for link in family["pne_links"]
    }
    assert used_refs <= EXPECTED_PNE_ALLOWLIST
    assert used_refs <= set(canonical["goals"])
    assert links["canonicalContract"]["contractVersion"] == "1.9.0"
    assert set(links["usedLegalRefs"]) == used_refs
    assert pme["pme_link_state"] == "not_materialized"
    assert pme["pme_goal_links"] == []
    assert all(item["pme_goal_links"] == [] for item in pme["families"])
    strings = list(_iter_strings([catalog, links, pme]))
    assert not any(re.search(r"\bPNE_", value) for value in strings)
    assert not any(re.search(r"\bPME_", value) for value in strings)


def test_mobility_wording_anchors_and_destination_limits_are_exact() -> None:
    corpus = _json("CORPUS_VARIANTES_TERRITORIAIS_JOB5H.json")
    variants = [
        item
        for item in corpus["storyVariants"]
        if item["story_family_id"] == "D1_MOBILITY_HIGH_SCHOOL_OFFER"
    ]
    nsr = next(item for item in variants if item["entity"]["entity_id"] == "4313375")
    source = _csv("MATRIZ_FATO_FAMILIA_VARIANTE_FONTE_JOB5H.csv.gz")

    assert len(variants) == 11
    assert all(
        item["mobility_contract"]["approved_wording"]
        == "residentes que estudavam em outro município"
        for item in variants
    )
    assert all(item["mobility_contract"]["foreign_country_separate"] for item in variants)
    assert all(
        item["mobility_contract"]["destination_municipality_available"] is False
        and item["mobility_contract"]["origin_destination_matrix_derived"] is False
        for item in variants
    )
    inputs = {item["metric_id"]: item for item in nsr["named_inputs"]}
    assert inputs["residents_studying_other_municipality_share_all_2022"]["value"] == 1349 / 7666 * 100
    assert inputs["residents_studying_other_municipality_share_fundamental_2022"]["value"] == 355 / 4090 * 100
    assert inputs["residents_studying_other_municipality_share_high_school_2022"]["value"] == 220 / 1151 * 100
    mobility_rows = source[source["story_family_id"].eq("D1_MOBILITY_HIGH_SCHOOL_OFFER")]
    assert mobility_rows["label"].str.contains("outro município|país estrangeiro|ensino médio|Turmas|Unidades", regex=True).all()


def test_pnate_2026_is_forecast_and_never_execution_use_payment_or_mobility() -> None:
    corpus = _json("CORPUS_VARIANTES_TERRITORIAIS_JOB5H.json")
    variants = [
        item
        for item in corpus["storyVariants"]
        if item["story_family_id"] == "D1_RURALITY_PNATE_PLANNING"
    ]
    assert len(variants) == 11
    for variant in variants:
        contract = variant["pnate_2026_contract"]
        assert contract == {
            "record_type": "planning_forecast",
            "execution_available": False,
            "realized_use_available": False,
            "payment_available": False,
            "mobility_measure": False,
        }
        forecast = next(
            item
            for item in variant["named_inputs"]
            if item["metric_id"] == "pnate_planning_forecast_2026"
        )
        unavailable = next(
            item
            for item in variant["named_inputs"]
            if item["metric_id"] == "pnate_execution_or_observed_use_2026"
        )
        assert "Previsão de planejamento" in forecast["label"]
        assert unavailable["value"] is None
        assert unavailable["availability_state"] == "unavailable"


def test_c1_c12_evidence_is_specific_and_cross_section_c5_is_not_supported() -> None:
    matrix = _csv("MATRIZ_C1_C12_ESPECIFICA_JOB5H.csv.gz")
    assert len(matrix) == 13 * 12
    assert matrix[["story_family_id", "criterion_id"]].duplicated().sum() == 0
    assert matrix["evidence"].nunique() == len(matrix)
    assert set(matrix["criterion_id"]) == {f"C{index}" for index in range(1, 13)}
    mobility_c5 = matrix[
        matrix["story_family_id"].eq("D1_MOBILITY_HIGH_SCHOOL_OFFER")
        & matrix["criterion_id"].eq("C5")
    ].iloc[0]
    assert mobility_c5["criterion_status"] == "NOT_SUPPORTED"
    assert "2022" in mobility_c5["evidence"]
    assert "não estabilidade temporal" in mobility_c5["evidence"]


def test_symmetry_completeness_and_explicit_unavailability_cover_all_ten() -> None:
    completeness = _csv("MATRIZ_COMPLETUDE_DEZ_MUNICIPIOS_JOB5H.csv.gz")
    availability = _csv("MATRIZ_DISPONIBILIDADE_ESTADOS_CONDICIONAIS_JOB5H.csv.gz")
    registry = json.loads(
        (REPO_ROOT / "config" / "regions" / "rs.json").read_text(encoding="utf-8")
    )
    region = next(item for item in registry["regions"] if item["slug"] == "vale-do-sinos")

    assert len(completeness) == 130
    assert completeness[["story_family_id", "municipality_ibge_code"]].duplicated().sum() == 0
    assert set(completeness["municipality_ibge_code"]) == set(region["municipalityIbgeCodes"])
    assert set(completeness.groupby("story_family_id").size()) == {10}
    assert completeness["unavailability_explicit"].eq("True").all()
    assert len(availability) == 143
    unavailable = availability[availability["availability_state"].isin(["unavailable", "null", "suppressed"])]
    assert unavailable["unavailability_reason"].notna().all()


def test_nova_santa_rita_fixture_is_full_and_bridge_limit_is_explicit() -> None:
    fixture = _json("FIXTURE_NOVA_SANTA_RITA_JOB5H.json")
    variants = fixture["storyVariants"]
    family_ids = {item["story_family_id"] for item in variants}
    expected = {
        "D1_COHORT_OFFER_CAPACITY",
        "D1_TRAJECTORY_CONDITIONS",
        "D1_MOBILITY_HIGH_SCHOOL_OFFER",
        "D1_RURALITY_PNATE_PLANNING",
        "D1_SPECIAL_AEE_TERRITORY",
        "D1_ADULT_SCHOOLING_EJA",
        "D2_YOUTH_WORK_15_17",
        "D2_YOUTH_WORK_18_24",
        "D2_APPRENTICESHIP",
        "D2_OCCUPATIONS_SECTORS",
        "D2_EPT_TERRITORIAL_OFFER",
        "D2_SECTOR_TRANSFORMATION_SHIFT_SHARE",
        "D2_NORMATIVE_WORK_EDUCATION_BRIDGE",
    }
    assert fixture["entity"]["municipality_ibge_code"] == "4313375"
    assert fixture["storyFamilyCount"] == 13
    assert family_ids == expected
    bridge = next(
        item
        for item in variants
        if item["story_family_id"] == "D2_NORMATIVE_WORK_EDUCATION_BRIDGE"
    )
    assert bridge["availability_state"] == "unavailable"
    assert bridge["editorial_state"] == "UNAVAILABLE_WITH_REASON"
    assert bridge["unavailability_reason"]
    dossier = (OUTPUT_ROOT / "DOSSIE_EDITORIAL_NOVA_SANTA_RITA_JOB5H.md").read_text(
        encoding="utf-8"
    )
    for required in (
        "educação infantil",
        "ensino médio",
        "mobilidade",
        "educação especial/AEE",
        "aprendizagem",
        "logística",
        "PNATE",
        "finanças seletivas",
    ):
        assert required in dossier


def test_manifest_is_hash_complete_deterministic_and_records_no_side_effects() -> None:
    manifest = _json("MANIFEST_JOB5H.json")
    actual = {path.name for path in OUTPUT_ROOT.iterdir() if path.is_file()}
    assert actual == set(manifest["contract"]["outputs"])
    assert len(actual) == 28
    assert len(manifest["artifacts"]) == 27
    for artifact in manifest["artifacts"]:
        path = OUTPUT_ROOT / artifact["path"]
        assert path.stat().st_size == artifact["byteSize"]
        assert _sha256(path) == artifact["sha256"]
    assert manifest["summary"] == {
        "outputCount": 28,
        "artifactHashCount": 27,
        "familyCount": 13,
        "variantCount": 143,
        "valeVariantCount": 13,
        "municipalVariantCount": 130,
        "novaSantaRitaVariantCount": 13,
        "factTraceRowCount": 924,
        "completenessRowCount": 130,
        "c1C12RowCount": 156,
        "qaControlCount": 65,
        "qaFailedCount": 0,
    }
    generation = manifest["generation"]
    assert generation["deterministic"] is True
    assert generation["transactional"] is True
    assert generation["manifestLast"] is True
    assert generation["networkUsed"] is False
    assert generation["databaseUsed"] is False
    assert generation["publicDataChanged"] is False
    assert generation["frontendChanged"] is False
    assert generation["fullBuildUsed"] is False
    assert generation["publicationPerformed"] is False
    assert generation["job5IStarted"] is False
    assert generation["gate11"] == "CLOSED"
    assert manifest["finalState"] == "JOB_5H_READY_WITH_EXPLICIT_LIMITS_FOR_EXTERNAL_JUDGMENT"
