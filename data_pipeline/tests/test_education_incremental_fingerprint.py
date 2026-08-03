from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pandas as pd

from data_pipeline.src.education_task_fingerprint import (
    EDUCATION_SOURCE_DEFINITIONS,
    OutputIntegrityResult,
    ShadowDecision,
    TaskStateLoadResult,
    build_output_manifest,
    build_task_state,
    default_task_state_path,
    digest_contract_files,
    digest_tabular_source,
    evaluate_shadow_eligibility,
    load_task_state,
    verify_output_manifest,
    write_task_state_atomic,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
EXPORTER_SPEC = importlib.util.spec_from_file_location(
    "education_incremental_exporter",
    REPO_ROOT / "data_pipeline" / "scripts" / "export_education_indicators.py",
)
EXPORTER = importlib.util.module_from_spec(EXPORTER_SPEC)
assert EXPORTER_SPEC.loader is not None
sys.modules[EXPORTER_SPEC.name] = EXPORTER
EXPORTER_SPEC.loader.exec_module(EXPORTER)


def _municipality_ids() -> tuple[str, ...]:
    return tuple(f"43{index:05d}" for index in range(497))


def _education_tree(root: Path, municipality_ids: tuple[str, ...]) -> Path:
    root.mkdir(parents=True)
    (root / "index.json").write_text('{"schema":"education"}\n', encoding="utf-8")
    (root / "municipios_index.json").write_text(
        '{"municipalities":497}\n', encoding="utf-8"
    )
    municipal_root = root / "municipios"
    municipal_root.mkdir()
    for municipality_id in municipality_ids:
        (municipal_root / f"{municipality_id}.json").write_text(
            json.dumps({"id_municipio": municipality_id}) + "\n",
            encoding="utf-8",
        )
    return root


def _fingerprint_contracts() -> tuple[dict, dict]:
    contracts = {"aggregateSha256": "b" * 64}
    fingerprint = {
        "inputFingerprint": "a" * 64,
        "identity": {
            "runtime": {"python": "test"},
            "executionParameters": {"outputCount": 499},
        },
    }
    return fingerprint, contracts


def _state_for_tree(
    education_tree: Path,
    municipality_ids: tuple[str, ...],
) -> tuple[dict, dict, dict]:
    fingerprint, contracts = _fingerprint_contracts()
    manifest = build_output_manifest(education_tree, municipality_ids)
    decision = ShadowDecision(
        would_skip=False,
        reason="first_run",
        fingerprint_hit=False,
        manifest_invalid=False,
        output_integrity=OutputIntegrityResult(False, "first_run"),
    )
    state = build_task_state(
        input_fingerprint=fingerprint,
        source_digests={"complete": True},
        contract_digests=contracts,
        output_manifest=manifest,
        decision=decision,
        created_at="2026-08-03T00:00:00Z",
    )
    return state, contracts, fingerprint


def test_tabular_digest_ignores_row_order_but_detects_value_change() -> None:
    source = pd.DataFrame(
        {
            "id_municipio": ["4300034", "4300059", "4300109"],
            "ano": [2023, 2024, 2025],
            "valor": [10.0, None, 30.0],
        }
    )

    original = digest_tabular_source(source)["digest"]
    reordered = digest_tabular_source(source.iloc[::-1].reset_index(drop=True))["digest"]
    changed = source.copy()
    changed.loc[0, "valor"] = 11.0

    assert reordered == original
    assert digest_tabular_source(changed)["digest"] != original


def test_operational_timestamp_does_not_change_source_digest() -> None:
    first = pd.DataFrame(
        {"id_municipio": ["4300034"], "valor": [1], "generated_at": ["a"]}
    )
    second = first.copy()
    second["generated_at"] = "b"

    assert digest_tabular_source(first)["digest"] == digest_tabular_source(second)[
        "digest"
    ]


def test_contract_allowlist_is_present_in_this_checkout() -> None:
    contracts = digest_contract_files(REPO_ROOT)

    assert contracts["fileCount"] == len(contracts["files"])
    assert contracts["aggregateSha256"]


def test_source_contract_matches_every_frame_loaded_by_the_exporter() -> None:
    expected = {"municipalities", *(key for _view, key in EXPORTER.EDUCATION_VIEWS)}
    observed = {definition.frame_key for definition in EDUCATION_SOURCE_DEFINITIONS}

    assert observed == expected


def test_identical_input_and_intact_outputs_are_eligible(tmp_path: Path) -> None:
    municipality_ids = _municipality_ids()
    tree = _education_tree(tmp_path / "educacao", municipality_ids)
    state, contracts, fingerprint = _state_for_tree(tree, municipality_ids)

    decision = evaluate_shadow_eligibility(
        TaskStateLoadResult(state, "loaded"),
        fingerprint,
        contracts,
        tree,
        municipality_ids,
    )

    assert decision.would_skip
    assert decision.reason == "eligible"
    assert decision.output_integrity.managed_outputs == 499


def test_changed_input_never_skips_even_with_intact_outputs(tmp_path: Path) -> None:
    municipality_ids = _municipality_ids()
    tree = _education_tree(tmp_path / "educacao", municipality_ids)
    state, contracts, fingerprint = _state_for_tree(tree, municipality_ids)
    changed = {**fingerprint, "inputFingerprint": "c" * 64}

    decision = evaluate_shadow_eligibility(
        TaskStateLoadResult(state, "loaded"),
        changed,
        contracts,
        tree,
        municipality_ids,
    )

    assert not decision.would_skip
    assert decision.reason == "input_changed"


def test_changed_missing_or_extra_output_never_skips(tmp_path: Path) -> None:
    municipality_ids = _municipality_ids()
    tree = _education_tree(tmp_path / "educacao", municipality_ids)
    state, contracts, fingerprint = _state_for_tree(tree, municipality_ids)
    target = tree / "municipios" / f"{municipality_ids[0]}.json"
    target.write_text("changed\n", encoding="utf-8")

    changed = evaluate_shadow_eligibility(
        TaskStateLoadResult(state, "loaded"),
        fingerprint,
        contracts,
        tree,
        municipality_ids,
    )
    assert not changed.would_skip
    assert changed.reason == "output_changed"

    target.unlink()
    missing = verify_output_manifest(
        tree, state["outputManifest"], municipality_ids
    )
    assert not missing.valid
    assert missing.reason == "output_missing"

    target.write_text("restored\n", encoding="utf-8")
    (tree / "municipios" / "4399999.json").write_text("{}\n", encoding="utf-8")
    extra = verify_output_manifest(tree, state["outputManifest"], municipality_ids)
    assert not extra.valid
    assert extra.reason == "output_extra"


def test_corrupt_state_is_a_safe_miss(tmp_path: Path) -> None:
    state_path = tmp_path / "education-core.json"
    state_path.write_text("{not-json", encoding="utf-8")

    loaded = load_task_state(state_path)

    assert loaded.state is None
    assert loaded.reason == "manifest_invalid"


def test_task_state_write_is_atomic_and_uses_ignored_export_root(
    tmp_path: Path,
) -> None:
    municipality_ids = _municipality_ids()
    tree = _education_tree(tmp_path / "educacao", municipality_ids)
    state, _contracts, _fingerprint = _state_for_tree(tree, municipality_ids)
    state_path = tmp_path / "task-state" / "RS" / "education-core.json"

    write_task_state_atomic(state_path, state)

    assert json.loads(state_path.read_text(encoding="utf-8")) == state
    assert not list(state_path.parent.glob(".*.tmp"))
    assert default_task_state_path(REPO_ROOT / "data_pipeline") == (
        REPO_ROOT
        / "data_pipeline"
        / "export"
        / "task-state"
        / "RS"
        / "education-core.json"
    )


def _mock_exporter_flow(monkeypatch, *, eligible: bool):
    municipality_ids = _municipality_ids()
    municipalities = pd.DataFrame(
        {
            "id_municipio": municipality_ids,
            "municipio": [f"Municipio {index}" for index in range(497)],
        }
    )
    state_config = SimpleNamespace(state_code="RS")
    registry = SimpleNamespace(
        municipality_count=497,
        ordered_records=tuple(
            SimpleNamespace(ibge_code=municipality_id)
            for municipality_id in municipality_ids
        ),
    )
    export = Mock(return_value=(497, [], [], []))
    state_write = Mock()
    source_digest = Mock(return_value={"complete": True})

    monkeypatch.setattr(EXPORTER, "normalize_state_code", lambda value: value.upper())
    monkeypatch.setattr(EXPORTER, "load_state_config", lambda _state: state_config)
    monkeypatch.setattr(
        EXPORTER, "load_municipality_registry", lambda _state: registry
    )
    monkeypatch.setattr(
        EXPORTER,
        "load_education_municipality_route_compatibility",
        lambda *_args: object(),
    )
    monkeypatch.setattr(EXPORTER, "_get_education_engine", lambda: object())
    monkeypatch.setattr(
        EXPORTER, "carregar_municipios", lambda *_args: municipalities
    )
    monkeypatch.setattr(EXPORTER, "carregar_view", lambda *_args: pd.DataFrame())
    monkeypatch.setattr(EXPORTER, "digest_education_sources", source_digest)
    monkeypatch.setattr(
        EXPORTER,
        "digest_contract_files",
        lambda *_args, **_kwargs: {"aggregateSha256": "b" * 64},
    )
    monkeypatch.setattr(
        EXPORTER,
        "build_input_fingerprint",
        lambda *_args, **_kwargs: {
            "inputFingerprint": "a" * 64,
            "identity": {"runtime": {}, "executionParameters": {}},
        },
    )
    monkeypatch.setattr(
        EXPORTER,
        "default_task_state_path",
        lambda _root: Path("task-state.json"),
    )
    monkeypatch.setattr(
        EXPORTER,
        "load_task_state",
        lambda _path: TaskStateLoadResult(None, "first_run"),
    )
    monkeypatch.setattr(
        EXPORTER,
        "evaluate_shadow_eligibility",
        lambda *_args, **_kwargs: ShadowDecision(
            would_skip=eligible,
            reason="eligible" if eligible else "first_run",
            fingerprint_hit=eligible,
            manifest_invalid=False,
            output_integrity=OutputIntegrityResult(
                eligible, "eligible" if eligible else "first_run", 499, 123
            ),
        ),
    )
    monkeypatch.setattr(EXPORTER, "exportar_municipios", export)
    monkeypatch.setattr(EXPORTER, "gerar_municipios_index", Mock())
    monkeypatch.setattr(EXPORTER, "gerar_index", Mock())
    monkeypatch.setattr(EXPORTER, "validar_jsons", Mock())
    monkeypatch.setattr(
        EXPORTER,
        "build_output_manifest",
        lambda *_args, **_kwargs: {"managedOutputCount": 499},
    )
    monkeypatch.setattr(EXPORTER, "build_task_state", lambda **_kwargs: {})
    monkeypatch.setattr(EXPORTER, "write_task_state_atomic", state_write)
    return export, state_write, source_digest


def test_incremental_mode_returns_before_materialization_when_eligible(
    monkeypatch,
) -> None:
    export, state_write, source_digest = _mock_exporter_flow(
        monkeypatch, eligible=True
    )

    assert EXPORTER.main(["--state", "RS", "--fingerprint-incremental"]) == 0

    source_digest.assert_called_once()
    export.assert_not_called()
    state_write.assert_not_called()


def test_shadow_mode_executes_full_materialization_even_when_eligible(
    monkeypatch,
) -> None:
    export, state_write, source_digest = _mock_exporter_flow(
        monkeypatch, eligible=True
    )

    assert EXPORTER.main(["--state", "RS", "--fingerprint-shadow"]) == 0

    source_digest.assert_called_once()
    export.assert_called_once()
    state_write.assert_called_once()


def test_incremental_miss_executes_full_materialization_and_records_state(
    monkeypatch,
) -> None:
    export, state_write, source_digest = _mock_exporter_flow(
        monkeypatch, eligible=False
    )

    assert EXPORTER.main(["--state", "RS", "--fingerprint-incremental"]) == 0

    source_digest.assert_called_once()
    export.assert_called_once()
    state_write.assert_called_once()


def test_traditional_mode_never_reads_or_writes_fingerprint_state(monkeypatch) -> None:
    export, state_write, source_digest = _mock_exporter_flow(
        monkeypatch, eligible=True
    )

    assert EXPORTER.main(["--state", "RS"]) == 0

    source_digest.assert_not_called()
    export.assert_called_once()
    state_write.assert_not_called()
