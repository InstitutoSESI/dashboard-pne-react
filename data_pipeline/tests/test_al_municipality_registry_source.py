from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

import pytest

from data_pipeline.src.municipality_registry import load_municipality_registry
from data_pipeline.src.municipality_registry_source import (
    MUNICIPALITY_REGISTRY_CANDIDATE_ALGORITHM,
    MunicipalityRegistrySourceError,
    build_municipality_registry_candidate,
    load_source_json_with_textual_numbers,
)
from data_pipeline.src.state_config import load_state_config


REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = (
    REPO_ROOT / "data_pipeline" / "data" / "municipality_registry_sources" / "al"
)
RAW_PATH = SOURCE_ROOT / "raw" / "ibge_localidades_municipios_27.json"
MANIFEST_PATH = SOURCE_ROOT / "manifest.json"
ACTIVE_STATE_DIR = REPO_ROOT / "config" / "states"
ACTIVE_REGISTRY_DIR = REPO_ROOT / "config" / "municipalities"
ACTIVE_STATE_PATH = ACTIVE_STATE_DIR / "al.json"
ACTIVE_REGISTRY_PATH = ACTIVE_REGISTRY_DIR / "al.json"
ACTIVE_PUBLICATION_PATH = REPO_ROOT / "config" / "publications" / "al.json"
CANDIDATE_ROOT = REPO_ROOT / "config" / "candidates"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_al_source_snapshot_and_manifest_are_reconciled() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    raw_bytes = RAW_PATH.read_bytes()
    response_body = raw_bytes[:-1]

    assert raw_bytes.endswith(b"\n")
    assert manifest["schemaVersion"] == "municipality-registry-source-v1"
    assert manifest["stateCode"] == "AL"
    assert manifest["stateIbgeCode"] == "27"
    assert manifest["provider"] == "IBGE"
    assert manifest["http"]["status"] == 200
    assert re.fullmatch(r"[0-9a-f]{64}", manifest["http"]["transportSha256"])
    assert manifest["http"]["responseBodyByteCount"] == len(response_body)
    assert manifest["http"]["responseBodySha256"] == hashlib.sha256(
        response_body
    ).hexdigest()
    assert manifest["rawSnapshot"]["byteCount"] == len(raw_bytes)
    assert manifest["rawSnapshot"]["snapshotSha256"] == hashlib.sha256(
        raw_bytes
    ).hexdigest()
    assert manifest["rawSnapshot"]["recordCount"] == 102


def test_al_official_source_materializes_the_exact_candidate_registry() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    state = load_state_config("AL", config_dir=ACTIVE_STATE_DIR)
    registry = load_municipality_registry(
        state,
        registry_dir=ACTIVE_REGISTRY_DIR,
    )
    source_payload = load_source_json_with_textual_numbers(RAW_PATH.read_bytes())
    materialized = build_municipality_registry_candidate(
        source_payload,
        state_config=state,
    )
    versioned = json.loads(ACTIVE_REGISTRY_PATH.read_text(encoding="utf-8"))

    assert materialized == versioned
    assert registry.municipality_count == 102
    assert len(registry.ids) == 102
    assert all(code.startswith("27") and len(code) == 7 for code in registry.ids)
    assert registry.get_by_id("2700102").name == "Água Branca"
    assert registry.get_by_id("2705705").slug == "olho-d-agua-das-flores"
    assert registry.get_by_id("2709400").slug == "vicosa"
    assert manifest["normalization"]["algorithm"] == (
        MUNICIPALITY_REGISTRY_CANDIDATE_ALGORITHM
    )
    assert manifest["normalization"]["normalizerSha256"] == _sha256(
        REPO_ROOT / manifest["normalization"]["normalizerPath"]
    )
    assert manifest["normalization"]["stateConfigPath"] == "config/states/al.json"
    assert manifest["normalization"]["municipalityRegistryPath"] == (
        "config/municipalities/al.json"
    )
    assert manifest["normalization"]["stateConfigSha256"] == _sha256(
        ACTIVE_STATE_PATH
    )
    assert manifest["normalization"]["municipalityRegistrySha256"] == _sha256(
        ACTIVE_REGISTRY_PATH
    )
    assert manifest["coverage"] == {
        "expectedMunicipalities": 102,
        "observedMunicipalities": 102,
        "uniqueIbgeCodes": 102,
        "uniqueNames": 102,
        "uniqueSlugs": 102,
        "ibgePrefix": "27",
    }


def test_al_configs_are_promoted_with_education_as_the_only_analytics_product() -> None:
    """Fase 1: configuração, registro e Educação ativos de forma fail-closed."""
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    publication = json.loads(ACTIVE_PUBLICATION_PATH.read_text(encoding="utf-8"))

    assert manifest["lifecycle"]["status"] == "product-identity-only"
    assert manifest["lifecycle"]["productPublicationActive"] is True
    assert manifest["lifecycle"]["pipelineActive"] is False
    assert manifest["lifecycle"]["productPublicationPath"] == (
        "config/publications/al.json"
    )
    assert ACTIVE_STATE_PATH.is_file()
    assert ACTIVE_REGISTRY_PATH.is_file()
    assert not CANDIDATE_ROOT.exists()
    assert publication["schemaVersion"] == "state-publication-v3"
    assert publication["stateCode"] == "AL"
    assert publication["analyticsStatus"] == "partial"
    assert publication["enabledProducts"] == ["educacao", "financiamento"]
    assert publication["stateConfigPath"] == "config/states/al.json"
    assert publication["municipalityRegistryPath"] == (
        "config/municipalities/al.json"
    )


def test_al_normalizer_rejects_numeric_identity_before_materialization() -> None:
    state = load_state_config("AL", config_dir=ACTIVE_STATE_DIR)
    source_payload = load_source_json_with_textual_numbers(RAW_PATH.read_bytes())
    assert isinstance(source_payload, list)
    source_payload[0]["id"] = 2700102

    with pytest.raises(
        MunicipalityRegistrySourceError,
        match="texto com sete dígitos",
    ):
        build_municipality_registry_candidate(source_payload, state_config=state)
