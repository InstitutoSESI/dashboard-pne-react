from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from data_pipeline.scripts.materialize_state_identity_publication import (
    materialize_identity_publication,
)
from data_pipeline.src.identity_publication import (
    IdentityPublicationError,
    build_identity_publication_files,
    promote_staged_publication,
    validate_identity_publication,
    write_staged_publication,
)
from data_pipeline.src.municipality_registry import load_municipality_registry
from data_pipeline.src.state_config import load_state_config
from data_pipeline.src.state_publication import load_state_publication


def _legacy_identity_inputs():
    """Mantém os testes unitários do publicador legado após AL virar complete."""
    active = load_state_publication("AL")
    publication = replace(
        active,
        analytics_status="identity-only",
        analytics_message="Indicadores ainda não publicados.",
    )
    state = load_state_config("AL", config_dir=publication.state_config_path.parent)
    registry = load_municipality_registry(
        state,
        registry_path=publication.municipality_registry_path,
    )
    source = {
        "generatedAt": "2026-08-07T16:03:54Z",
        "sourceManifestPath": (
            "data_pipeline/data/municipality_registry_sources/al/manifest.json"
        ),
        "sourceManifestSha256": "0" * 64,
        "responseBodySha256": "1" * 64,
    }
    return publication, state, registry, source


def _publication_validator(publication, state, registry, source):
    return lambda root: validate_identity_publication(
        root,
        publication=publication,
        state_config=state,
        registry=registry,
        generated_at=source["generatedAt"],
        source_manifest_path=source["sourceManifestPath"],
        source_manifest_sha256=source["sourceManifestSha256"],
        response_body_sha256=source["responseBodySha256"],
    )


def test_legacy_identity_inputs_build_the_exact_file_set(tmp_path: Path) -> None:
    publication, state, registry, source = _legacy_identity_inputs()
    files = build_identity_publication_files(
        publication=publication,
        state_config=state,
        registry=registry,
        generated_at=source["generatedAt"],
        source_manifest_path=source["sourceManifestPath"],
        source_manifest_sha256=source["sourceManifestSha256"],
        response_body_sha256=source["responseBodySha256"],
    )

    assert len(files) == 104
    assert all(
        path.as_posix() in {"publication.json", "municipios_index.json"}
        or path.as_posix().startswith("municipios/27")
        for path in files
    )
    write_staged_publication(files, tmp_path)
    validate_identity_publication(
        tmp_path,
        publication=publication,
        state_config=state,
        registry=registry,
        generated_at=source["generatedAt"],
        source_manifest_path=source["sourceManifestPath"],
        source_manifest_sha256=source["sourceManifestSha256"],
        response_body_sha256=source["responseBodySha256"],
    )
    municipal = json.loads((tmp_path / "municipios" / "2700102" / "index.json").read_text(encoding="utf-8"))
    assert municipal["id_municipio"] == "2700102"
    assert isinstance(municipal["id_municipio"], str)
    assert municipal["analytics"]["status"] == "unavailable"

    manifest_path = tmp_path / "publication.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["source"]["manifestSha256"] = "2" * 64
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(IdentityPublicationError, match="proveniência"):
        _publication_validator(publication, state, registry, source)(tmp_path)


def test_promotion_preserves_identical_files_and_mtime(tmp_path: Path) -> None:
    publication, state, registry, source = _legacy_identity_inputs()
    files = build_identity_publication_files(
        publication=publication,
        state_config=state,
        registry=registry,
        generated_at=source["generatedAt"],
        source_manifest_path=source["sourceManifestPath"],
        source_manifest_sha256=source["sourceManifestSha256"],
        response_body_sha256=source["responseBodySha256"],
    )
    target = tmp_path / "target"
    first_stage = tmp_path / "first-stage"
    second_stage = tmp_path / "second-stage"
    validator = _publication_validator(publication, state, registry, source)
    write_staged_publication(files, first_stage)
    first = promote_staged_publication(first_stage, target, validate_target=validator)
    index = target / "municipios_index.json"
    mtime = index.stat().st_mtime_ns
    write_staged_publication(files, second_stage)
    second = promote_staged_publication(second_stage, target, validate_target=validator)

    assert first.changed_files == 104
    assert second.publication_noop is True
    assert second.preserved_files == 104
    assert index.stat().st_mtime_ns == mtime


def test_failed_target_validation_rolls_back_every_changed_file(tmp_path: Path) -> None:
    publication, state, registry, source = _legacy_identity_inputs()
    files = build_identity_publication_files(
        publication=publication,
        state_config=state,
        registry=registry,
        generated_at=source["generatedAt"],
        source_manifest_path=source["sourceManifestPath"],
        source_manifest_sha256=source["sourceManifestSha256"],
        response_body_sha256=source["responseBodySha256"],
    )
    target = tmp_path / "target"
    initial_stage = tmp_path / "initial-stage"
    write_staged_publication(files, initial_stage)
    valid = _publication_validator(publication, state, registry, source)
    promote_staged_publication(initial_stage, target, validate_target=valid)
    before = {path.relative_to(target): path.read_bytes() for path in target.rglob("*") if path.is_file()}

    altered = dict(files)
    altered[next(path for path in altered if path.as_posix().endswith("2700102/index.json"))] = b"{}\n"
    failed_stage = tmp_path / "failed-stage"
    write_staged_publication(altered, failed_stage)
    with pytest.raises(IdentityPublicationError):
        promote_staged_publication(failed_stage, target, validate_target=valid)
    after = {path.relative_to(target): path.read_bytes() for path in target.rglob("*") if path.is_file()}
    assert after == before


def test_real_al_complete_publication_rejects_identity_materialization() -> None:
    with pytest.raises(ValueError, match="identity-only"):
        materialize_identity_publication("AL", check=True)
