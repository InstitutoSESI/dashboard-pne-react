from __future__ import annotations

import json
from pathlib import Path

import pytest

from data_pipeline.src.state_publication import (
    StatePublicationError,
    load_state_publication,
)


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_real_state_publications_resolve_distinct_contracts() -> None:
    rs = load_state_publication("rs")
    al = load_state_publication("AL")

    assert rs.analytics_status == "complete"
    assert rs.analytics_message is None
    assert rs.public_data_directory == REPO_ROOT / "public" / "data"
    assert al.analytics_status == "identity-only"
    assert al.state_config_path == REPO_ROOT / "config" / "candidates" / "states" / "al.json"
    assert al.municipality_registry_path == (
        REPO_ROOT / "config" / "candidates" / "municipalities" / "al.json"
    )
    assert al.public_data_directory == REPO_ROOT / "state-publications" / "al" / "data"


def _write_manifest(repo_root: Path, payload: object) -> None:
    path = repo_root / "config" / "publications" / "al.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _valid_manifest() -> dict[str, object]:
    return {
        "schemaVersion": "state-publication-v2",
        "stateCode": "AL",
        "stateConfigPath": "config/candidates/states/al.json",
        "municipalityRegistryPath": "config/candidates/municipalities/al.json",
        "publicDataDirectory": "state-publications/al/data",
        "analyticsStatus": "identity-only",
        "analyticsMessage": "Indicadores ainda não publicados.",
    }


@pytest.mark.parametrize(
    ("field", "value", "match"),
    (
        ("stateConfigPath", "../outside.json", "escapa do repositório"),
        ("publicDataDirectory", "dist/al", "árvore operacional proibida"),
        ("analyticsMessage", None, "exige analyticsMessage"),
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
