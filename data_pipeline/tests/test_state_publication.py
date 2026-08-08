from __future__ import annotations

import json
from pathlib import Path

import pytest

from data_pipeline.src.state_publication import (
    StatePublicationError,
    load_state_publication,
    resolve_education_data_dir,
    resolve_public_data_dir,
)


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_real_state_publications_resolve_distinct_contracts() -> None:
    rs = load_state_publication("rs")
    al = load_state_publication("AL")

    assert rs.schema_version == "state-publication-v3"
    assert al.schema_version == "state-publication-v3"
    assert rs.analytics_status == "complete"
    assert rs.analytics_message is None
    assert rs.enabled_products is None
    assert rs.public_data_directory == REPO_ROOT / "public" / "data"
    assert al.analytics_status == "partial"
    assert al.enabled_products == ("educacao",)
    assert al.state_config_path == REPO_ROOT / "config" / "states" / "al.json"
    assert al.municipality_registry_path == (
        REPO_ROOT / "config" / "municipalities" / "al.json"
    )
    assert al.public_data_directory == REPO_ROOT / "state-publications" / "al" / "data"


def test_public_roots_are_resolved_per_state_without_fallback() -> None:
    assert resolve_public_data_dir("RS") == REPO_ROOT / "public" / "data"
    assert resolve_public_data_dir("al") == (
        REPO_ROOT / "state-publications" / "al" / "data"
    )
    assert resolve_education_data_dir("AL") == (
        REPO_ROOT / "state-publications" / "al" / "data" / "educacao"
    )
    with pytest.raises(FileNotFoundError):
        resolve_public_data_dir("SP")


def test_complete_publication_enables_every_product() -> None:
    rs = load_state_publication("RS")
    for product in ("pne", "educacao", "financiamento"):
        assert rs.product_enabled(product) is True


def test_partial_al_publication_enables_only_education() -> None:
    al = load_state_publication("AL")
    assert al.product_enabled("educacao") is True
    assert al.product_enabled("pne") is False
    assert al.product_enabled("financiamento") is False


def _write_manifest(repo_root: Path, payload: object) -> None:
    path = repo_root / "config" / "publications" / "al.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _valid_manifest(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "schemaVersion": "state-publication-v3",
        "stateCode": "AL",
        "stateConfigPath": "config/states/al.json",
        "municipalityRegistryPath": "config/municipalities/al.json",
        "publicDataDirectory": "state-publications/al/data",
        "analyticsStatus": "identity-only",
        "analyticsMessage": "Indicadores ainda não publicados.",
        "enabledProducts": None,
    }
    payload.update(overrides)
    return payload


@pytest.mark.parametrize(
    ("field", "value", "match"),
    (
        ("stateConfigPath", "../outside.json", "escapa do repositório"),
        ("publicDataDirectory", "dist/al", "árvore operacional proibida"),
        ("analyticsMessage", None, "exige analyticsMessage"),
        ("schemaVersion", "state-publication-v2", "schemaVersion deve ser"),
    ),
)
def test_publication_rejects_unsafe_or_incomplete_contracts(
    tmp_path: Path,
    field: str,
    value: object,
    match: str,
) -> None:
    payload = _valid_manifest()
    payload[field] = value
    _write_manifest(tmp_path, payload)

    with pytest.raises(StatePublicationError, match=match):
        load_state_publication("AL", repo_root=tmp_path)


def test_publication_rejects_unexpected_fields(tmp_path: Path) -> None:
    payload = _valid_manifest()
    payload["fallbackState"] = "RS"
    _write_manifest(tmp_path, payload)

    with pytest.raises(StatePublicationError, match="inesperados"):
        load_state_publication("AL", repo_root=tmp_path)


def test_partial_publication_enables_only_declared_products(tmp_path: Path) -> None:
    _write_manifest(
        tmp_path,
        _valid_manifest(
            analyticsStatus="partial",
            analyticsMessage="Somente Educação foi publicada para Alagoas.",
            enabledProducts=["educacao"],
        ),
    )

    publication = load_state_publication("AL", repo_root=tmp_path)

    assert publication.analytics_status == "partial"
    assert publication.enabled_products == ("educacao",)
    assert publication.product_enabled("educacao") is True
    assert publication.product_enabled("pne") is False
    assert publication.product_enabled("financiamento") is False


@pytest.mark.parametrize(
    ("overrides", "match"),
    (
        (
            {"analyticsStatus": "partial", "analyticsMessage": "x"},
            "exige enabledProducts como lista não vazia",
        ),
        (
            {
                "analyticsStatus": "partial",
                "analyticsMessage": "x",
                "enabledProducts": [],
            },
            "exige enabledProducts como lista não vazia",
        ),
        (
            {
                "analyticsStatus": "partial",
                "analyticsMessage": "x",
                "enabledProducts": ["saude"],
            },
            "Produto analítico desconhecido",
        ),
        (
            {
                "analyticsStatus": "partial",
                "analyticsMessage": "x",
                "enabledProducts": ["educacao", "educacao"],
            },
            "Produto analítico duplicado",
        ),
        (
            {
                "analyticsStatus": "partial",
                "analyticsMessage": "x",
                "enabledProducts": ["pne", "educacao", "financiamento"],
            },
            "deve declarar\nanalyticsStatus complete|analyticsStatus complete",
        ),
        (
            {
                "analyticsStatus": "partial",
                "analyticsMessage": "   ",
                "enabledProducts": ["pne"],
            },
            "Publicação partial exige analyticsMessage",
        ),
        (
            {"enabledProducts": ["pne"]},
            "identity-only deve declarar enabledProducts null",
        ),
        (
            {
                "analyticsStatus": "complete",
                "analyticsMessage": None,
                "enabledProducts": ["pne"],
            },
            "complete deve declarar enabledProducts null",
        ),
    ),
)
def test_partial_contract_is_fail_closed(
    tmp_path: Path,
    overrides: dict[str, object],
    match: str,
) -> None:
    _write_manifest(tmp_path, _valid_manifest(**overrides))

    with pytest.raises(StatePublicationError, match=match):
        load_state_publication("AL", repo_root=tmp_path)
