from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pandas as pd
import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
PIPELINE_ROOT = REPO_ROOT / "data_pipeline"
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

from src.education_municipality_routes import (  # noqa: E402
    load_education_municipality_route_compatibility,
)
from src.education_task_fingerprint import (  # noqa: E402
    EDUCATION_CONTRACT_FILE_ALLOWLIST,
    EDUCATION_SOURCE_DEFINITIONS,
    EXPECTED_MANAGED_OUTPUT_COUNT,
    EducationFingerprintError,
    EducationSourceDefinition,
    OutputIntegrityResult,
    ShadowDecision,
    TaskStateLoadResult,
    build_input_fingerprint,
    build_output_manifest,
    build_task_state,
    default_task_state_path,
    digest_contract_files,
    digest_education_sources,
    digest_tabular_source,
    evaluate_shadow_eligibility,
    load_task_state,
    verify_output_manifest,
    write_task_state_atomic,
)
from src.education_transactional_publication import (  # noqa: E402
    EducationPromotionError,
    EducationValidationError,
)
from src.municipality_registry import load_municipality_registry  # noqa: E402
from src.state_config import load_state_config  # noqa: E402


def _load_exporter():
    spec = importlib.util.spec_from_file_location(
        "education_fingerprint_exporter",
        PIPELINE_ROOT / "scripts" / "export_education_indicators.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


EXPORTER = _load_exporter()


def _digest(frame: pd.DataFrame) -> str:
    return str(digest_tabular_source(frame)["digest"])


def _mixed_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "id_municipio": pd.Series(["4300034", "4300059"], dtype="string"),
            "inteiro": pd.Series([1, 2], dtype="Int64"),
            "decimal": pd.Series([1.5, np.nan], dtype="float64"),
            "flag": pd.Series([True, pd.NA], dtype="boolean"),
            "data": pd.to_datetime(["2025-01-01", None]),
            "texto": pd.Series(["a", None], dtype="object"),
        }
    )


def test_same_dataframe_produces_same_digest() -> None:
    frame = _mixed_frame()
    assert _digest(frame) == _digest(frame.copy(deep=True))


def test_row_reordering_preserves_digest() -> None:
    frame = _mixed_frame()
    assert _digest(frame) == _digest(frame.iloc[::-1].reset_index(drop=True))


def test_value_change_changes_digest() -> None:
    frame = _mixed_frame()
    changed = frame.copy()
    changed.loc[0, "inteiro"] = 9
    assert _digest(frame) != _digest(changed)


def test_float_representation_noise_is_canonicalized() -> None:
    value = 250.12345678901234
    same_analytical_value = np.nextafter(value, np.inf)
    first = pd.DataFrame({"valor": [value]})
    second = pd.DataFrame({"valor": [same_analytical_value]})
    assert 0 < same_analytical_value - value < 0.5e-12
    assert _digest(first) == _digest(second)
    assert digest_tabular_source(first)["floatPolicy"] == (
        "round-float-to-12-decimal-places-v1"
    )


def test_float_change_above_canonical_noise_changes_digest() -> None:
    value = 250.12345678901234
    first = pd.DataFrame({"valor": [value]})
    changed = pd.DataFrame({"valor": [value + 1e-9]})
    assert _digest(first) != _digest(changed)


def test_null_change_changes_digest() -> None:
    frame = _mixed_frame()
    changed = frame.copy()
    changed.loc[0, "texto"] = None
    assert _digest(frame) != _digest(changed)


def test_additional_row_changes_digest() -> None:
    frame = _mixed_frame()
    changed = pd.concat([frame, frame.iloc[[0]]], ignore_index=True)
    assert _digest(frame) != _digest(changed)


def test_additional_column_changes_digest() -> None:
    frame = _mixed_frame()
    changed = frame.assign(extra=1)
    assert _digest(frame) != _digest(changed)


def test_relevant_dtype_change_changes_digest() -> None:
    integer = pd.DataFrame({"valor": pd.Series([1, 2], dtype="int64")})
    decimal = pd.DataFrame({"valor": pd.Series([1, 2], dtype="float64")})
    assert _digest(integer) != _digest(decimal)


def test_contractual_column_order_changes_digest() -> None:
    frame = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
    assert _digest(frame) != _digest(frame[["b", "a"]])


def test_none_and_nan_follow_the_same_documented_null_policy() -> None:
    none_frame = pd.DataFrame({"valor": pd.Series(["x", None], dtype=object)})
    nan_frame = pd.DataFrame({"valor": pd.Series(["x", np.nan], dtype=object)})
    assert _digest(none_frame) == _digest(nan_frame)


def test_bool_is_not_confused_with_integer() -> None:
    boolean = pd.DataFrame({"valor": pd.Series([True, False], dtype="bool")})
    integer = pd.DataFrame({"valor": pd.Series([1, 0], dtype="int64")})
    assert _digest(boolean) != _digest(integer)


def test_textual_ibge_is_not_confused_with_numeric_ibge() -> None:
    textual = pd.DataFrame(
        {"id_municipio": pd.Series(["4300034"], dtype="string")}
    )
    numeric = pd.DataFrame({"id_municipio": pd.Series([4300034], dtype="int64")})
    assert _digest(textual) != _digest(numeric)


def test_digest_is_stable_between_controlled_processes() -> None:
    code = (
        "import pandas as pd; "
        "from src.education_task_fingerprint import digest_tabular_source; "
        "f=pd.DataFrame({'id_municipio':pd.Series(['4300059','4300034'],"
        "dtype='string'),'valor':pd.Series([2,1],dtype='Int64')}); "
        "print(digest_tabular_source(f)['digest'])"
    )
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(PIPELINE_ROOT)
    first = subprocess.run(
        [sys.executable, "-c", code],
        cwd=REPO_ROOT,
        env=environment,
        check=True,
        text=True,
        capture_output=True,
    ).stdout.strip()
    second = subprocess.run(
        [sys.executable, "-c", code],
        cwd=REPO_ROOT,
        env=environment,
        check=True,
        text=True,
        capture_output=True,
    ).stdout.strip()
    assert first == second == _digest(
        pd.DataFrame(
            {
                "id_municipio": pd.Series(
                    ["4300034", "4300059"], dtype="string"
                ),
                "valor": pd.Series([1, 2], dtype="Int64"),
            }
        )
    )


CONTRACT_FIXTURES = (
    "config/states/rs.json",
    "config/municipalities/rs.json",
    "config/compatibility/education-municipality-routes/rs.json",
    "data_pipeline/src/education_module.py",
    "data_pipeline/queries/education_query.sql",
)


def _write_contract_fixture(root: Path) -> None:
    for position, relative in enumerate(CONTRACT_FIXTURES):
        path = root / Path(relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"contract-{position}\n", encoding="utf-8")


@pytest.mark.parametrize(
    "changed_path",
    CONTRACT_FIXTURES,
    ids=("state-config", "registry", "slug-overrides", "module", "query"),
)
def test_each_contract_class_invalidates_the_digest(
    tmp_path: Path,
    changed_path: str,
) -> None:
    _write_contract_fixture(tmp_path)
    before = digest_contract_files(tmp_path, allowlist=CONTRACT_FIXTURES)
    path = tmp_path / Path(changed_path)
    path.write_text(path.read_text(encoding="utf-8") + "changed\n", encoding="utf-8")
    after = digest_contract_files(tmp_path, allowlist=CONTRACT_FIXTURES)
    assert before["aggregateSha256"] != after["aggregateSha256"]


def test_personal_repository_root_does_not_affect_contract_digest(tmp_path: Path) -> None:
    first_root = tmp_path / "user-one" / "repo"
    second_root = tmp_path / "user-two" / "repo"
    _write_contract_fixture(first_root)
    _write_contract_fixture(second_root)
    assert digest_contract_files(
        first_root, allowlist=CONTRACT_FIXTURES
    ) == digest_contract_files(second_root, allowlist=CONTRACT_FIXTURES)


def test_external_adapter_digest_omits_its_personal_path(tmp_path: Path) -> None:
    repository = tmp_path / "repo"
    _write_contract_fixture(repository)
    first_adapter = tmp_path / "person-one" / "utils_educacao.py"
    second_adapter = tmp_path / "person-two" / "utils_educacao.py"
    first_adapter.parent.mkdir()
    second_adapter.parent.mkdir()
    first_adapter.write_text("adapter-v1\n", encoding="utf-8")
    second_adapter.write_text("adapter-v1\n", encoding="utf-8")
    first = digest_contract_files(
        repository,
        allowlist=CONTRACT_FIXTURES,
        external_contracts={"utils_educacao": first_adapter},
    )
    second = digest_contract_files(
        repository,
        allowlist=CONTRACT_FIXTURES,
        external_contracts={"utils_educacao": second_adapter},
    )
    assert first == second
    assert str(first_adapter) not in json.dumps(first)


def test_operational_timestamp_does_not_affect_tabular_digest() -> None:
    first = pd.DataFrame(
        {"valor": [1], "updated_at": ["2026-08-02T10:00:00Z"]}
    )
    second = pd.DataFrame(
        {"valor": [1], "updated_at": ["2026-08-03T11:00:00Z"]}
    )
    assert _digest(first) == _digest(second)
    assert digest_tabular_source(first)["operationalColumnsExcluded"] == [
        "updated_at"
    ]


def test_source_load_timestamp_does_not_affect_tabular_digest() -> None:
    first = pd.DataFrame(
        {"valor": [1], "data_carga": ["2026-08-02T23:59:59Z"]}
    )
    second = pd.DataFrame(
        {"valor": [1], "data_carga": ["2026-08-03T00:00:01Z"]}
    )
    assert _digest(first) == _digest(second)
    assert digest_tabular_source(first)["operationalColumnsExcluded"] == [
        "data_carga"
    ]


def test_incomplete_source_set_is_never_digestible() -> None:
    definitions = (
        EducationSourceDefinition("one", "one", "one", "postgres_view"),
        EducationSourceDefinition("two", "two", "two", "postgres_view"),
    )
    with pytest.raises(EducationFingerprintError, match="incompleto"):
        digest_education_sources(
            {"one": pd.DataFrame({"value": [1]})},
            definitions=definitions,
        )


@pytest.fixture
def municipality_ids() -> tuple[str, ...]:
    return tuple(f"43{position:05d}" for position in range(497))


@pytest.fixture
def education_tree(
    tmp_path: Path,
    municipality_ids: tuple[str, ...],
) -> Path:
    root = tmp_path / "isolated" / "public" / "data" / "educacao"
    (root / "municipios").mkdir(parents=True)
    (root / "index.json").write_bytes(b"index-v1")
    (root / "municipios_index.json").write_bytes(b"municipalities-v1")
    for municipality_id in municipality_ids:
        (root / "municipios" / f"{municipality_id}.json").write_bytes(
            f"municipality:{municipality_id}".encode("ascii")
        )
    return root


def test_output_manifest_contains_exactly_499_files(
    education_tree: Path,
    municipality_ids: tuple[str, ...],
) -> None:
    manifest = build_output_manifest(education_tree, municipality_ids)
    assert manifest["managedOutputCount"] == EXPECTED_MANAGED_OUTPUT_COUNT == 499
    assert len(manifest["files"]) == 499


def test_missing_output_invalidates_manifest(
    education_tree: Path,
    municipality_ids: tuple[str, ...],
) -> None:
    manifest = build_output_manifest(education_tree, municipality_ids)
    (education_tree / "municipios" / f"{municipality_ids[0]}.json").unlink()
    assert verify_output_manifest(
        education_tree, manifest, municipality_ids
    ).reason == "output_missing"


def test_extra_managed_output_invalidates_manifest(
    education_tree: Path,
    municipality_ids: tuple[str, ...],
) -> None:
    manifest = build_output_manifest(education_tree, municipality_ids)
    (education_tree / "municipios" / "4399999.json").write_bytes(b"extra")
    assert verify_output_manifest(
        education_tree, manifest, municipality_ids
    ).reason == "output_extra"


def test_changed_byte_invalidates_manifest(
    education_tree: Path,
    municipality_ids: tuple[str, ...],
) -> None:
    manifest = build_output_manifest(education_tree, municipality_ids)
    target = education_tree / "municipios" / f"{municipality_ids[0]}.json"
    payload = bytearray(target.read_bytes())
    payload[-1] = ord("9") if payload[-1] != ord("9") else ord("8")
    target.write_bytes(payload)
    assert verify_output_manifest(
        education_tree, manifest, municipality_ids
    ).reason == "output_changed"


def test_changed_size_invalidates_manifest(
    education_tree: Path,
    municipality_ids: tuple[str, ...],
) -> None:
    manifest = build_output_manifest(education_tree, municipality_ids)
    target = education_tree / "municipios" / f"{municipality_ids[0]}.json"
    target.write_bytes(target.read_bytes() + b"x")
    assert verify_output_manifest(
        education_tree, manifest, municipality_ids
    ).reason == "output_changed"


def test_other_domain_never_enters_output_manifest(
    education_tree: Path,
    municipality_ids: tuple[str, ...],
) -> None:
    manifest = build_output_manifest(education_tree, municipality_ids)
    unrelated = education_tree / "educacao-especial" / "index.json"
    unrelated.parent.mkdir()
    unrelated.write_bytes(b"other-domain")
    assert all(not entry["path"].startswith("educacao-especial/") for entry in manifest["files"])
    assert verify_output_manifest(education_tree, manifest, municipality_ids).valid


def test_corrupt_task_state_is_a_safe_miss(tmp_path: Path) -> None:
    path = tmp_path / "task-state.json"
    path.write_text("{broken", encoding="utf-8")
    loaded = load_task_state(path)
    assert loaded.state is None
    assert loaded.reason == "manifest_invalid"


def test_manifest_from_another_state_is_a_safe_miss(
    education_tree: Path,
    municipality_ids: tuple[str, ...],
) -> None:
    manifest = build_output_manifest(education_tree, municipality_ids)
    manifest["stateCode"] = "AL"
    assert verify_output_manifest(
        education_tree, manifest, municipality_ids
    ).reason == "state_mismatch"


def test_output_manifest_is_deterministic_and_ignores_mtime(
    education_tree: Path,
    municipality_ids: tuple[str, ...],
) -> None:
    first = build_output_manifest(education_tree, municipality_ids)
    os.utime(education_tree / "index.json", None)
    second = build_output_manifest(education_tree, municipality_ids)
    assert first == second


def _full_source_report() -> dict:
    frames = {
        definition.frame_key: pd.DataFrame(
            {
                "id_municipio": pd.Series(["4300034"], dtype="string"),
                "value": pd.Series([1], dtype="Int64"),
            }
        )
        for definition in EDUCATION_SOURCE_DEFINITIONS
    }
    return digest_education_sources(frames)


def _input_and_contracts() -> tuple[dict, dict, dict]:
    sources = _full_source_report()
    contracts = {
        "schemaVersion": "education-contract-digests-v1",
        "aggregateSha256": "a" * 64,
        "files": [],
        "fileCount": 0,
        "bytesHashed": 0,
    }
    fingerprint = build_input_fingerprint(
        sources,
        contracts,
        execution_parameters={
            "municipalityCount": 497,
            "publicationContract": "transactional-full-v1",
            "outputCount": 499,
        },
        runtime={"python": "3.test", "pandas": "test", "numpy": "test"},
    )
    return sources, contracts, fingerprint


def _state_for_tree(
    education_tree: Path,
    municipality_ids: tuple[str, ...],
    *,
    decision: ShadowDecision | None = None,
) -> tuple[dict, dict, dict]:
    sources, contracts, fingerprint = _input_and_contracts()
    manifest = build_output_manifest(education_tree, municipality_ids)
    effective_decision = decision or ShadowDecision(
        False,
        "first_run",
        False,
        False,
        OutputIntegrityResult(False, "first_run"),
    )
    state = build_task_state(
        input_fingerprint=fingerprint,
        source_digests=sources,
        contract_digests=contracts,
        output_manifest=manifest,
        decision=effective_decision,
        created_at="2026-08-03T00:00:00Z",
    )
    return state, contracts, fingerprint


def test_task_state_write_is_atomic(
    tmp_path: Path,
    education_tree: Path,
    municipality_ids: tuple[str, ...],
) -> None:
    state, _contracts, _fingerprint = _state_for_tree(
        education_tree, municipality_ids
    )
    path = tmp_path / "task-state" / "RS" / "education-core.json"
    write_task_state_atomic(path, state)
    assert json.loads(path.read_text(encoding="utf-8")) == state
    assert list(path.parent.glob(".*.tmp")) == []


def test_first_run_reports_would_skip_false(
    education_tree: Path,
    municipality_ids: tuple[str, ...],
) -> None:
    _sources, contracts, fingerprint = _input_and_contracts()
    decision = evaluate_shadow_eligibility(
        TaskStateLoadResult(None, "first_run"),
        fingerprint,
        contracts,
        education_tree,
        municipality_ids,
    )
    assert not decision.would_skip
    assert decision.reason == "first_run"


def test_second_identical_input_and_intact_outputs_reports_would_skip_true(
    education_tree: Path,
    municipality_ids: tuple[str, ...],
) -> None:
    state, contracts, fingerprint = _state_for_tree(education_tree, municipality_ids)
    decision = evaluate_shadow_eligibility(
        TaskStateLoadResult(state, "loaded"),
        fingerprint,
        contracts,
        education_tree,
        municipality_ids,
    )
    assert decision.would_skip
    assert decision.reason == "eligible"
    assert decision.output_integrity.managed_outputs == 499


def _run_exporter_shadow(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    shadow: bool = True,
    decision_reason: str = "eligible",
    would_skip: bool = True,
    failure: str | None = None,
) -> tuple[int | None, list[str], Mock]:
    state = load_state_config("RS")
    registry = load_municipality_registry(state)
    compatibility = load_education_municipality_route_compatibility(state, registry)
    public_root = tmp_path / "public" / "data" / "educacao"
    public_root.mkdir(parents=True)
    calls: list[str] = []
    municipalities = pd.DataFrame(
        [
            {
                "id_municipio": record.ibge_code,
                "municipio": record.name,
                "regiao_senai": None,
            }
            for record in registry.ordered_records
        ]
    )

    monkeypatch.setattr(EXPORTER, "default_public_root", lambda: public_root)
    monkeypatch.setattr(EXPORTER, "_get_education_engine", lambda: object())
    monkeypatch.setattr(
        EXPORTER,
        "resolve_imported_python_module_contract",
        lambda *_args, **_kwargs: object(),
    )
    monkeypatch.setattr(EXPORTER, "carregar_municipios", lambda *_args: municipalities)
    monkeypatch.setattr(
        EXPORTER,
        "carregar_view",
        lambda *_args: pd.DataFrame(
            {"id_municipio": pd.Series(dtype="string")}
        ),
    )

    def materialize_outputs(*_args, **_kwargs):
        calls.append("materialization")
        if failure == "materialization":
            raise OSError("controlled materialization failure")
        return registry.municipality_count, [], []

    monkeypatch.setattr(EXPORTER, "materialize_education_outputs", materialize_outputs)
    monkeypatch.setattr(EXPORTER, "validar_jsons", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(
        EXPORTER,
        "digest_education_sources",
        lambda _frames: {
            "stats": {"sources": 19, "rowsHashed": 0, "columnsHashed": 0, "bytesHashed": 0}
        },
    )
    monkeypatch.setattr(
        EXPORTER,
        "digest_contract_files",
        lambda _root, **_kwargs: {
            "fileCount": 1,
            "bytesHashed": 1,
            "aggregateSha256": "a" * 64,
        },
    )
    monkeypatch.setattr(
        EXPORTER,
        "build_input_fingerprint",
        lambda *_args, **_kwargs: {
            "inputFingerprint": "b" * 64,
            "bytesHashed": 1,
            "identity": {"runtime": {}, "executionParameters": {}},
        },
    )
    monkeypatch.setattr(
        EXPORTER,
        "default_task_state_path",
        lambda _root: tmp_path / "task-state.json",
    )
    monkeypatch.setattr(
        EXPORTER,
        "load_task_state",
        lambda _path: TaskStateLoadResult({}, "loaded"),
    )

    decision = ShadowDecision(
        would_skip,
        decision_reason,
        would_skip,
        False,
        OutputIntegrityResult(would_skip, decision_reason, 499, 123),
    )

    def decide(*_args, **_kwargs):
        calls.append("decision")
        return decision

    monkeypatch.setattr(EXPORTER, "evaluate_shadow_eligibility", decide)

    def publication(*, materialize, **_kwargs):
        materialize(tmp_path / "staging" / "output")
        calls.append("validation")
        if failure == "validation":
            raise EducationValidationError("controlled validation failure")
        calls.append("promotion")
        if failure == "promotion":
            raise EducationPromotionError("controlled promotion failure")
        return SimpleNamespace(
            validation=SimpleNamespace(
                municipality_count=registry.municipality_count,
                files=tuple(range(499)),
            ),
            stats=SimpleNamespace(created=0, updated=0, preserved=499, removed=0),
            staged_output=None,
        )

    monkeypatch.setattr(EXPORTER, "publish_education_transactionally", publication)
    monkeypatch.setattr(
        EXPORTER,
        "build_output_manifest",
        lambda *_args, **_kwargs: {"managedOutputCount": 499, "totalBytes": 123, "files": []},
    )
    monkeypatch.setattr(EXPORTER, "build_task_state", lambda **_kwargs: {"valid": True})
    state_write = Mock(side_effect=lambda *_args: calls.append("state_write"))
    monkeypatch.setattr(EXPORTER, "write_task_state_atomic", state_write)

    arguments = ["--state", "RS"]
    if shadow:
        arguments.append("--fingerprint-shadow")
    if failure == "materialization":
        with pytest.raises(OSError, match="controlled materialization"):
            EXPORTER.main(arguments)
        return None, calls, state_write
    return EXPORTER.main(arguments), calls, state_write


@pytest.mark.parametrize("stage", ("materialization", "validation", "promotion"))
def test_eligible_shadow_continues_the_complete_flow(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    stage: str,
) -> None:
    result, calls, _state_write = _run_exporter_shadow(monkeypatch, tmp_path)
    assert result == 0
    assert calls.index("decision") < calls.index(stage) < calls.index("state_write")


def test_changed_input_remains_ineligible() -> None:
    _sources, contracts, fingerprint = _input_and_contracts()
    previous = {
        "contractDigests": contracts,
        "inputFingerprint": "0" * 64,
        "outputManifest": {},
    }
    decision = evaluate_shadow_eligibility(
        TaskStateLoadResult(previous, "loaded"),
        fingerprint,
        contracts,
        Path("unused"),
        (),
        enforce_rs_contract=False,
    )
    assert not decision.would_skip
    assert decision.reason == "input_changed"


def test_tampered_output_remains_ineligible(
    education_tree: Path,
    municipality_ids: tuple[str, ...],
) -> None:
    state, contracts, fingerprint = _state_for_tree(education_tree, municipality_ids)
    target = education_tree / "municipios" / f"{municipality_ids[0]}.json"
    target.write_bytes(b"tampered")
    decision = evaluate_shadow_eligibility(
        TaskStateLoadResult(state, "loaded"),
        fingerprint,
        contracts,
        education_tree,
        municipality_ids,
    )
    assert not decision.would_skip
    assert decision.reason == "output_changed"


@pytest.mark.parametrize("failure", ("materialization", "validation", "promotion"))
def test_pipeline_failure_never_writes_task_state(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    failure: str,
) -> None:
    result, calls, state_write = _run_exporter_shadow(
        monkeypatch,
        tmp_path,
        failure=failure,
    )
    if failure != "materialization":
        assert result == 1
    assert "state_write" not in calls
    state_write.assert_not_called()


def test_successful_public_noop_writes_valid_task_state(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    result, calls, state_write = _run_exporter_shadow(monkeypatch, tmp_path)
    assert result == 0
    assert calls[-1] == "state_write"
    state_write.assert_called_once()


def test_without_flag_no_fingerprint_state_is_read_or_written(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    result, calls, state_write = _run_exporter_shadow(
        monkeypatch,
        tmp_path,
        shadow=False,
    )
    assert result == 0
    assert "decision" not in calls
    assert "state_write" not in calls
    state_write.assert_not_called()


def test_dry_run_with_shadow_does_not_calculate_real_fingerprint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = Mock(side_effect=AssertionError("database"))
    digest = Mock(side_effect=AssertionError("digest"))
    state_read = Mock(side_effect=AssertionError("task state"))
    monkeypatch.setattr(EXPORTER, "_get_education_engine", engine)
    monkeypatch.setattr(EXPORTER, "digest_education_sources", digest)
    monkeypatch.setattr(EXPORTER, "load_task_state", state_read)
    assert EXPORTER.main(
        ["--state", "RS", "--dry-run", "--fingerprint-shadow"]
    ) == 0
    engine.assert_not_called()
    digest.assert_not_called()
    state_read.assert_not_called()


def test_unknown_state_fails_before_task_state_or_database(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = Mock(side_effect=AssertionError("database"))
    state_read = Mock(side_effect=AssertionError("task state"))
    monkeypatch.setattr(EXPORTER, "_get_education_engine", engine)
    monkeypatch.setattr(EXPORTER, "load_task_state", state_read)
    assert EXPORTER.main(["--state", "AL", "--fingerprint-shadow"]) == 2
    engine.assert_not_called()
    state_read.assert_not_called()


def test_tests_never_target_real_public_data(tmp_path: Path) -> None:
    candidate = (tmp_path / "public" / "data").resolve()
    assert REPO_ROOT.resolve() not in candidate.parents
    assert candidate != (REPO_ROOT / "public" / "data").resolve()


def test_contract_allowlist_is_explicit_relative_and_complete() -> None:
    required = {
        "config/states/rs.json",
        "config/municipalities/rs.json",
        "config/compatibility/education-municipality-routes/rs.json",
        "data_pipeline/src/education_transactional_publication.py",
        "data_pipeline/src/education_municipality_routes.py",
        "data_pipeline/src/school_infrastructure.py",
        "data_pipeline/src/school_infrastructure_materialization.py",
        "data_pipeline/src/data/repository.py",
        "data_pipeline/src/data_loader.py",
        "data_pipeline/queries/school_infrastructure_source.sql",
        "data_pipeline/uv.lock",
    }
    assert required <= set(EDUCATION_CONTRACT_FILE_ALLOWLIST)
    assert all("*" not in path and not Path(path).is_absolute() for path in EDUCATION_CONTRACT_FILE_ALLOWLIST)


def test_default_task_state_is_ignored_and_outside_data_roots() -> None:
    path = default_task_state_path(PIPELINE_ROOT)
    assert path == PIPELINE_ROOT / "export" / "task-state" / "RS" / "education-core.json"
    assert (REPO_ROOT / "public" / "data").resolve() not in path.resolve().parents
    assert (PIPELINE_ROOT / "data").resolve() not in path.resolve().parents
    check = subprocess.run(
        ["git", "check-ignore", "-q", str(path)],
        cwd=REPO_ROOT,
        check=False,
    )
    assert check.returncode == 0
