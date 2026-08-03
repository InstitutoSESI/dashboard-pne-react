from __future__ import annotations

from contextlib import nullcontext
import hashlib
import importlib.util
import json
from pathlib import Path
import socket
import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pandas as pd
import pytest


DATA_PIPELINE_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = DATA_PIPELINE_DIR.parent
if str(DATA_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_PIPELINE_DIR))

from src.education_municipality_routes import (  # noqa: E402
    load_education_municipality_route_compatibility,
)
from src.education_task_fingerprint import (  # noqa: E402
    EducationFingerprintError,
    OutputIntegrityResult,
    ShadowDecision,
    TaskStateLoadResult,
    build_output_manifest,
    digest_contract_files,
    digest_tabular_source,
    evaluate_shadow_eligibility,
    load_task_state,
    resolve_imported_python_module_contract,
)
from src.education_transactional_publication import (  # noqa: E402
    EducationPublicationError,
)
from src.municipality_registry import load_municipality_registry  # noqa: E402
from src.pipeline_profiling import (  # noqa: E402
    ProfileSession,
    activate_profile_session,
)
from src.state_config import load_state_config  # noqa: E402


def _load_script(module_name: str, filename: str):
    spec = importlib.util.spec_from_file_location(
        module_name,
        DATA_PIPELINE_DIR / "scripts" / filename,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


EXPORTER = _load_script(
    "education_fingerprint_skip_exporter",
    "export_education_indicators.py",
)
UPDATE = _load_script(
    "education_fingerprint_skip_orchestrator",
    "update_static_data.py",
)


@pytest.fixture(autouse=True)
def _block_network(monkeypatch: pytest.MonkeyPatch):
    def blocked(*_args, **_kwargs):
        raise AssertionError("testes 5D2B nao podem acessar rede")

    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)


def _decision(reason: str, *, eligible: bool = False) -> ShadowDecision:
    return ShadowDecision(
        would_skip=eligible,
        reason=reason,
        fingerprint_hit=eligible,
        manifest_invalid=reason == "manifest_invalid",
        output_integrity=OutputIntegrityResult(
            eligible,
            reason,
            managed_outputs=499 if eligible else 0,
            output_bytes_verified=123 if eligible else 0,
        ),
    )


def _inputs(registry) -> dict:
    municipalities = pd.DataFrame(
        {
            "id_municipio": [record.ibge_code for record in registry.ordered_records],
            "municipio": [record.name for record in registry.ordered_records],
            "regiao_senai": [None] * registry.municipality_count,
        }
    )
    frames = {
        key: pd.DataFrame({"id_municipio": pd.Series(dtype="string")})
        for _view_name, key in EXPORTER.EDUCATION_VIEWS
    }
    return {
        "municipalities": municipalities,
        "municipalityIds": municipalities["id_municipio"].tolist(),
        "frames": frames,
        "availableYears": {},
    }


def _run_exporter(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    mode: str = "skip",
    reason: str = "eligible",
    eligible: bool = True,
    fingerprint_error: str | None = None,
    publication_noop: bool = False,
    publication_failure: bool = False,
    session: ProfileSession | None = None,
):
    state_config = load_state_config("RS")
    registry = load_municipality_registry(state_config)
    compatibility = load_education_municipality_route_compatibility(
        state_config,
        registry,
    )
    public_root = tmp_path / "public" / "data" / "educacao"
    public_root.mkdir(parents=True, exist_ok=True)
    inputs = _inputs(registry)
    calls: list[str] = []
    emitted: list[dict] = []

    load_inputs = Mock(return_value=inputs)
    monkeypatch.setattr(EXPORTER, "default_public_root", lambda: public_root)
    monkeypatch.setattr(EXPORTER, "load_education_inputs", load_inputs)
    monkeypatch.setattr(
        EXPORTER,
        "digest_education_sources",
        Mock(
            side_effect=(
                EducationFingerprintError("fonte incompleta")
                if fingerprint_error == "source"
                else None
            ),
            return_value={
                "stats": {
                    "sources": 19,
                    "rowsHashed": 0,
                    "columnsHashed": 0,
                    "bytesHashed": 0,
                }
            },
        ),
    )
    resolver = Mock(return_value=object())
    if fingerprint_error == "utils":
        resolver.side_effect = EducationFingerprintError("utils nao verificavel")
    monkeypatch.setattr(
        EXPORTER,
        "resolve_imported_python_module_contract",
        resolver,
    )
    monkeypatch.setattr(
        EXPORTER,
        "digest_contract_files",
        lambda *_args, **_kwargs: {
            "fileCount": 1,
            "bytesHashed": 1,
            "aggregateSha256": "b" * 64,
        },
    )
    monkeypatch.setattr(
        EXPORTER,
        "build_input_fingerprint",
        lambda *_args, **_kwargs: {
            "inputFingerprint": "a" * 64,
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
    decision = _decision(reason, eligible=eligible)
    monkeypatch.setattr(
        EXPORTER,
        "evaluate_shadow_eligibility",
        lambda *_args, **_kwargs: decision,
    )

    materialize_outputs = Mock(
        side_effect=lambda *_args, **_kwargs: (
            calls.append("materialization") or (497, [], [])
        )
    )
    staging_validation = Mock(
        side_effect=lambda *_args, **_kwargs: calls.append("staging_validation")
        or True
    )
    monkeypatch.setattr(
        EXPORTER,
        "materialize_education_outputs",
        materialize_outputs,
    )
    monkeypatch.setattr(EXPORTER, "validar_jsons", staging_validation)

    stats = SimpleNamespace(
        created=0 if publication_noop else 1,
        updated=0,
        preserved=499 if publication_noop else 498,
        removed=0,
    )

    def publish(*, materialize, **_kwargs):
        calls.append("staging")
        if publication_failure:
            raise EducationPublicationError("falha controlada")
        materialize(tmp_path / "staging" / "output")
        calls.append("transactional_validation")
        calls.append("promotion")
        return SimpleNamespace(
            validation=SimpleNamespace(
                municipality_count=497,
                files=tuple(range(499)),
            ),
            stats=stats,
            staged_output=None,
        )

    publication = Mock(side_effect=publish)
    monkeypatch.setattr(EXPORTER, "publish_education_transactionally", publication)
    monkeypatch.setattr(
        EXPORTER,
        "build_output_manifest",
        lambda *_args, **_kwargs: {
            "managedOutputCount": 499,
            "totalBytes": 123,
            "files": [],
        },
    )
    monkeypatch.setattr(EXPORTER, "build_task_state", lambda **_kwargs: {})
    state_write = Mock(side_effect=lambda *_args: calls.append("state_write"))
    monkeypatch.setattr(EXPORTER, "write_task_state_atomic", state_write)
    monkeypatch.setattr(
        EXPORTER,
        "emit_education_result",
        lambda **payload: emitted.append(payload) or payload,
    )

    arguments = ["--state", "RS"]
    if mode == "skip":
        arguments.append("--fingerprint-skip")
    elif mode == "shadow":
        arguments.append("--fingerprint-shadow")
    context = activate_profile_session(session) if session is not None else nullcontext()
    with context:
        result = EXPORTER.main(arguments)
    return SimpleNamespace(
        result=result,
        calls=calls,
        emitted=emitted,
        load_inputs=load_inputs,
        publication=publication,
        materialize=materialize_outputs,
        staging_validation=staging_validation,
        state_write=state_write,
        public_root=public_root,
    )


def test_default_mode_remains_integral_and_has_no_fingerprint(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run = _run_exporter(monkeypatch, tmp_path, mode="integral")
    assert run.result == 0
    assert run.calls[:4] == [
        "staging",
        "materialization",
        "staging_validation",
        "transactional_validation",
    ]
    run.state_write.assert_not_called()


def test_shadow_eligible_still_executes_integral_transaction(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run = _run_exporter(monkeypatch, tmp_path, mode="shadow")
    assert run.result == 0
    assert "staging" in run.calls
    assert "materialization" in run.calls
    assert "staging_validation" in run.calls
    assert "promotion" in run.calls
    run.state_write.assert_called_once()


def test_eligible_skip_returns_reused_before_transaction(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run = _run_exporter(monkeypatch, tmp_path)
    assert run.result == 0
    assert run.emitted == [
        {
            "reused": True,
            "publication_noop": False,
            "reason": "eligible",
            "staging_created": 0,
            "municipalities_materialized": 0,
            "files_rendered": 0,
            "bytes_rendered": 0,
            "files_validated": 0,
            "promoted": False,
            "state_written": False,
        }
    ]


@pytest.mark.parametrize(
    "forbidden_call",
    (
        "staging",
        "materialization",
        "staging_validation",
        "transactional_validation",
        "promotion",
        "state_write",
    ),
)
def test_hit_avoids_every_transactional_effect(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    forbidden_call: str,
) -> None:
    run = _run_exporter(monkeypatch, tmp_path)
    assert forbidden_call not in run.calls


def test_hit_preserves_task_state_bytes_and_mtime(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_path = tmp_path / "task-state.json"
    state_path.write_bytes(b'{"stable":true}\n')
    before = (state_path.read_bytes(), state_path.stat().st_mtime_ns)
    run = _run_exporter(monkeypatch, tmp_path)
    after = (state_path.read_bytes(), state_path.stat().st_mtime_ns)
    assert run.result == 0
    assert after == before


def test_hit_preserves_output_bytes_and_mtimes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    output = tmp_path / "public" / "data" / "educacao" / "index.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(b'{"stable":true}\n')
    before = (output.read_bytes(), output.stat().st_mtime_ns)
    run = _run_exporter(monkeypatch, tmp_path)
    after = (output.read_bytes(), output.stat().st_mtime_ns)
    assert run.result == 0
    assert after == before


def test_reused_result_is_distinct_from_integral_publication_noop(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    reused = _run_exporter(monkeypatch, tmp_path / "reused")
    noop = _run_exporter(
        monkeypatch,
        tmp_path / "noop",
        eligible=False,
        reason="first_run",
        publication_noop=True,
    )
    assert reused.emitted[0]["reused"] is True
    assert reused.emitted[0]["publication_noop"] is False
    assert noop.emitted[0]["reused"] is False
    assert noop.emitted[0]["publication_noop"] is True


@pytest.mark.parametrize(
    "reason",
    (
        "first_run",
        "manifest_missing",
        "manifest_invalid",
        "input_changed",
        "contract_changed",
        "output_missing",
        "output_changed",
        "output_extra",
        "state_mismatch",
        "algorithm_changed",
    ),
)
def test_every_classified_miss_executes_full_transaction_and_writes_state(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    reason: str,
) -> None:
    run = _run_exporter(
        monkeypatch,
        tmp_path,
        eligible=False,
        reason=reason,
    )
    assert run.result == 0
    assert run.calls.index("staging") < run.calls.index("materialization")
    assert run.calls.index("promotion") < run.calls.index("state_write")


@pytest.mark.parametrize("fingerprint_error", ("source", "utils"))
def test_unverifiable_fingerprint_executes_full_without_replacing_state(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    fingerprint_error: str,
) -> None:
    run = _run_exporter(
        monkeypatch,
        tmp_path,
        fingerprint_error=fingerprint_error,
    )
    assert run.result == 0
    assert "materialization" in run.calls
    run.state_write.assert_not_called()


def test_relevant_float_change_invalidates_digest() -> None:
    baseline = pd.DataFrame({"valor": [100.123456789012]})
    changed = pd.DataFrame({"valor": [100.123456790012]})
    assert digest_tabular_source(baseline)["digest"] != digest_tabular_source(changed)[
        "digest"
    ]


def test_successful_integral_miss_writes_state_after_promotion(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run = _run_exporter(
        monkeypatch,
        tmp_path,
        eligible=False,
        reason="first_run",
    )
    assert run.calls.index("promotion") < run.calls.index("state_write")


def test_successful_integral_noop_still_writes_state(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run = _run_exporter(
        monkeypatch,
        tmp_path,
        eligible=False,
        reason="input_changed",
        publication_noop=True,
    )
    assert run.emitted[0]["publication_noop"] is True
    run.state_write.assert_called_once()


def test_failed_integral_miss_never_replaces_state(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_path = tmp_path / "task-state.json"
    state_path.write_bytes(b"previous\n")
    before = (state_path.read_bytes(), state_path.stat().st_mtime_ns)
    run = _run_exporter(
        monkeypatch,
        tmp_path,
        eligible=False,
        reason="first_run",
        publication_failure=True,
    )
    assert run.result == 1
    assert (state_path.read_bytes(), state_path.stat().st_mtime_ns) == before
    run.state_write.assert_not_called()


def test_exporter_argparse_rejects_shadow_with_skip_before_effects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    effect = Mock(side_effect=AssertionError("effect"))
    monkeypatch.setattr(EXPORTER, "load_state_config", effect)
    with pytest.raises(SystemExit) as exc:
        EXPORTER.main(["--fingerprint-shadow", "--fingerprint-skip"])
    assert exc.value.code == 2
    effect.assert_not_called()


def test_exporter_argparse_rejects_skip_with_no_promote_before_effects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    effect = Mock(side_effect=AssertionError("effect"))
    monkeypatch.setattr(EXPORTER, "load_state_config", effect)
    with pytest.raises(SystemExit) as exc:
        EXPORTER.main(["--fingerprint-skip", "--no-promote"])
    assert exc.value.code == 2
    effect.assert_not_called()


def test_orchestrator_argparse_rejects_shadow_with_skip() -> None:
    with pytest.raises(SystemExit) as exc:
        UPDATE.parse_args(
            ["--education-fingerprint-shadow", "--education-fingerprint-skip"]
        )
    assert exc.value.code == 2


def test_help_has_no_state_database_digest_or_staging_effect(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    effects = Mock(side_effect=AssertionError("effect"))
    monkeypatch.setattr(EXPORTER, "load_state_config", effects)
    monkeypatch.setattr(EXPORTER, "load_education_inputs", effects)
    with pytest.raises(SystemExit) as exc:
        EXPORTER.main(["--help"])
    assert exc.value.code == 0
    effects.assert_not_called()


def test_skip_dry_run_has_no_database_digest_state_or_staging(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    effects = Mock(side_effect=AssertionError("effect"))
    monkeypatch.setattr(EXPORTER, "load_education_inputs", effects)
    monkeypatch.setattr(EXPORTER, "digest_education_sources", effects)
    monkeypatch.setattr(EXPORTER, "load_task_state", effects)
    monkeypatch.setattr(EXPORTER, "publish_education_transactionally", effects)
    assert EXPORTER.main(["--state", "RS", "--dry-run", "--fingerprint-skip"]) == 0
    effects.assert_not_called()


def test_unknown_state_fails_before_state_database_or_digest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    effects = Mock(side_effect=AssertionError("effect"))
    monkeypatch.setattr(EXPORTER, "load_education_inputs", effects)
    monkeypatch.setattr(EXPORTER, "load_task_state", effects)
    assert EXPORTER.main(["--state", "AL", "--fingerprint-skip"]) == 2
    effects.assert_not_called()


@pytest.mark.parametrize("partial", (["--limit", "1"], ["--municipios", "4300034"]))
def test_partial_batches_are_rejected_before_database_state_or_staging(
    monkeypatch: pytest.MonkeyPatch,
    partial: list[str],
) -> None:
    effects = Mock(side_effect=AssertionError("effect"))
    monkeypatch.setattr(EXPORTER, "load_education_inputs", effects)
    monkeypatch.setattr(EXPORTER, "load_task_state", effects)
    monkeypatch.setattr(EXPORTER, "publish_education_transactionally", effects)
    assert EXPORTER.main(["--state", "RS", "--fingerprint-skip", *partial]) == 2
    effects.assert_not_called()


def _orchestrator_args(**overrides):
    values = {
        "dry_run": False,
        "skip_export": False,
        "skip_partition": False,
        "skip_education": False,
        "education_only": True,
        "education_fingerprint_shadow": False,
        "education_fingerprint_skip": True,
        "skip_build": False,
        "build": False,
        "validate_only": False,
        "no_include_derived": False,
        "profile": False,
        "profile_output": None,
        "state": "RS",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_orchestrator_propagates_only_the_skip_flag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    planned = Mock()
    monkeypatch.setattr(UPDATE, "print_dry_run", planned)
    assert UPDATE.run_pipeline(_orchestrator_args(dry_run=True)) == 0
    commands = dict(planned.call_args.args[0])
    assert commands["education"][-1] == "--fingerprint-skip"
    assert "--fingerprint-shadow" not in commands["education"]


def test_traditional_package_commands_contain_no_skip_flag() -> None:
    scripts = json.loads((REPO_ROOT / "package.json").read_text(encoding="utf-8"))[
        "scripts"
    ]
    for name in ("update:education-data", "update:data", "update:data:and-build"):
        assert "fingerprint-skip" not in scripts[name]
    assert "update:data:incremental" not in scripts


def test_explicit_incremental_package_commands_are_scoped_to_education() -> None:
    scripts = json.loads((REPO_ROOT / "package.json").read_text(encoding="utf-8"))[
        "scripts"
    ]
    assert scripts["update:education-data:incremental"].endswith(
        "--education-only --education-fingerprint-skip"
    )
    assert scripts["update:data:education-incremental"].endswith(
        "--education-fingerprint-skip"
    )


def _run_orchestrator(
    monkeypatch: pytest.MonkeyPatch,
    *,
    education_only: bool,
    build: bool = False,
    education_error: bool = False,
    later_error: str | None = None,
):
    calls: list[str] = []
    monkeypatch.setattr(UPDATE, "ensure_git_update_safe", lambda: None)
    monkeypatch.setattr(UPDATE, "print_summary", lambda *_args, **_kwargs: None)

    def education(_command, results):
        calls.append("education")
        if education_error:
            raise SystemExit(7)
        results.append(UPDATE.StepResult("education", "ok", reused=True, reason="eligible"))

    def command(name, _command, results):
        calls.append(name)
        if later_error == name:
            raise SystemExit(9)
        results.append(UPDATE.StepResult(name, "ok"))

    def sync(results, *, registry):
        del registry
        calls.append("sync")
        results.append(UPDATE.StepResult("sync", "ok"))
        return UPDATE.SyncStats(0, 0, 0, 0)

    monkeypatch.setattr(UPDATE, "run_education_command", education)
    monkeypatch.setattr(UPDATE, "run_command", command)
    monkeypatch.setattr(UPDATE, "sync_partitioned_to_public", sync)
    args = _orchestrator_args(education_only=education_only, build=build)
    return calls, lambda: UPDATE.run_pipeline(args)


@pytest.mark.parametrize("later_step", ("inequality", "validate"))
def test_reuse_allows_education_only_later_steps(
    monkeypatch: pytest.MonkeyPatch,
    later_step: str,
) -> None:
    calls, invoke = _run_orchestrator(monkeypatch, education_only=True)
    assert invoke() == 0
    assert calls.index("education") < calls.index(later_step)


def test_reuse_allows_full_pipeline_sync(monkeypatch: pytest.MonkeyPatch) -> None:
    calls, invoke = _run_orchestrator(monkeypatch, education_only=False)
    assert invoke() == 0
    assert calls.index("education") < calls.index("sync") < calls.index("validate")


def test_reuse_allows_explicit_build(monkeypatch: pytest.MonkeyPatch) -> None:
    calls, invoke = _run_orchestrator(
        monkeypatch,
        education_only=True,
        build=True,
    )
    assert invoke() == 0
    assert calls.index("validate") < calls.index("build")


def test_education_error_stops_all_later_steps(monkeypatch: pytest.MonkeyPatch) -> None:
    calls, invoke = _run_orchestrator(
        monkeypatch,
        education_only=True,
        education_error=True,
    )
    with pytest.raises(SystemExit) as exc:
        invoke()
    assert exc.value.code == 7
    assert calls == ["education"]


def test_error_after_reuse_remains_an_error(monkeypatch: pytest.MonkeyPatch) -> None:
    calls, invoke = _run_orchestrator(
        monkeypatch,
        education_only=True,
        later_error="validate",
    )
    with pytest.raises(SystemExit) as exc:
        invoke()
    assert exc.value.code == 9
    assert calls.index("education") < calls.index("validate")


def test_summary_explicitly_shows_reused(capsys, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(UPDATE, "run_git_status", lambda: "")
    UPDATE.print_summary(
        [UPDATE.StepResult("education", "ok", 0.1, reused=True, reason="eligible")],
        [],
        validate_ok=True,
        build_status="nao solicitado",
    )
    output = capsys.readouterr().out
    assert "reused=true" in output
    assert "reason=eligible" in output


def _profile_session(tmp_path: Path, name: str) -> ProfileSession:
    return ProfileSession.create_root(
        state_code="RS",
        command="test",
        parameters={"mode": name},
        requested_output=tmp_path / name,
        run_id=name,
    )


def _profile_event(session: ProfileSession, name: str) -> dict:
    return next(event for event in session.event_dicts() if event["name"] == name)


def test_profiling_hit_has_required_zero_work_counters(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    session = _profile_session(tmp_path, "hit")
    run = _run_exporter(monkeypatch, tmp_path, session=session)
    assert run.result == 0
    event = _profile_event(session, "education.result")
    assert event["counters"] == {
        "actuallySkipped": 1,
        "bytesRendered": 0,
        "filesRendered": 0,
        "filesValidated": 0,
        "fingerprintHit": 1,
        "municipalitiesMaterialized": 0,
        "stagingCreated": 0,
        "wouldSkip": 1,
    }


def test_profiling_miss_records_integral_work(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    session = _profile_session(tmp_path, "miss")
    run = _run_exporter(
        monkeypatch,
        tmp_path,
        eligible=False,
        reason="first_run",
        session=session,
    )
    assert run.result == 0
    counters = _profile_event(session, "education.result")["counters"]
    assert counters["actuallySkipped"] == 0
    assert counters["stagingCreated"] == 1
    assert counters["municipalitiesMaterialized"] == 497
    assert counters["filesRendered"] == 499


def test_profiling_shadow_never_records_actual_skip(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    session = _profile_session(tmp_path, "shadow")
    run = _run_exporter(monkeypatch, tmp_path, mode="shadow", session=session)
    assert run.result == 0
    decision = _profile_event(session, "education.fingerprint.shadow_decision")
    result = _profile_event(session, "education.result")
    assert decision["counters"]["wouldSkip"] == 1
    assert decision["counters"]["actuallySkipped"] == 0
    assert result["counters"]["actuallySkipped"] == 0


def test_without_flags_emits_no_fingerprint_profile_event(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    session = _profile_session(tmp_path, "integral")
    run = _run_exporter(
        monkeypatch,
        tmp_path,
        mode="integral",
        session=session,
    )
    assert run.result == 0
    assert not any(
        event["name"].startswith("education.fingerprint")
        for event in session.event_dicts()
    )


def _small_tree(root: Path) -> tuple[Path, tuple[str, ...], dict, dict, dict]:
    municipality_ids = ("4300034",)
    root.mkdir(parents=True)
    (root / "index.json").write_text("{}\n", encoding="utf-8")
    (root / "municipios_index.json").write_text("{}\n", encoding="utf-8")
    (root / "municipios").mkdir()
    (root / "municipios" / "4300034.json").write_text("{}\n", encoding="utf-8")
    manifest = build_output_manifest(
        root,
        municipality_ids,
        enforce_rs_contract=False,
    )
    contracts = {"aggregateSha256": "b" * 64}
    fingerprint = {"inputFingerprint": "a" * 64}
    state = {
        "contractDigests": contracts,
        "inputFingerprint": fingerprint["inputFingerprint"],
        "outputManifest": manifest,
    }
    return root, municipality_ids, state, contracts, fingerprint


@pytest.mark.parametrize("mutation", ("changed", "missing", "extra"))
def test_output_mutations_are_real_safe_misses(
    tmp_path: Path,
    mutation: str,
) -> None:
    root, municipality_ids, state, contracts, fingerprint = _small_tree(
        tmp_path / mutation
    )
    target = root / "municipios" / "4300034.json"
    if mutation == "changed":
        target.write_text('{"changed":true}\n', encoding="utf-8")
    elif mutation == "missing":
        target.unlink()
    else:
        (root / "municipios" / "4300059.json").write_text("{}\n", encoding="utf-8")
    decision = evaluate_shadow_eligibility(
        TaskStateLoadResult(state, "loaded"),
        fingerprint,
        contracts,
        root,
        municipality_ids,
        enforce_rs_contract=False,
    )
    assert not decision.would_skip
    expected_reason = "output_changed" if mutation == "changed" else f"output_{mutation}"
    assert decision.reason == expected_reason


@pytest.mark.parametrize(
    "relative",
    (
        "config/states/rs.json",
        "config/compatibility/education-municipality-routes/rs.json",
        "data_pipeline/scripts/export_education_indicators.py",
    ),
    ids=("config", "slug-override", "python-module"),
)
def test_contract_mutations_change_content_hash(
    tmp_path: Path,
    relative: str,
) -> None:
    target = tmp_path / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("before\n", encoding="utf-8")
    before = digest_contract_files(tmp_path, allowlist=(relative,))
    target.write_text("after\n", encoding="utf-8")
    after = digest_contract_files(tmp_path, allowlist=(relative,))
    assert before["aggregateSha256"] != after["aggregateSha256"]


def test_source_value_mutation_changes_content_digest() -> None:
    source = pd.DataFrame({"id_municipio": ["4300034"], "valor": [1.0]})
    changed = source.copy()
    changed.loc[0, "valor"] = 2.0
    assert digest_tabular_source(source)["digest"] != digest_tabular_source(changed)[
        "digest"
    ]


def _import_utils_module(
    monkeypatch: pytest.MonkeyPatch,
    source: Path,
):
    spec = importlib.util.spec_from_file_location("utils_educacao", source)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    monkeypatch.setitem(sys.modules, "utils_educacao", module)
    spec.loader.exec_module(module)
    return module


def test_resolved_utils_contract_hashes_actual_source_and_explicit_version(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source = tmp_path / "one" / "utils_educacao.py"
    source.parent.mkdir()
    source.write_text('__version__ = "2.3.4"\n', encoding="utf-8")
    _import_utils_module(monkeypatch, source)
    contract = resolve_imported_python_module_contract(
        "utils_educacao",
        contract_id="utils_educacao",
        search_paths=(str(source.parent),),
    )
    digests = digest_contract_files(
        tmp_path,
        allowlist=(),
        external_python_contracts=(contract,),
    )
    entry = digests["externalContracts"][0]
    assert entry["sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert entry["version"] == "2.3.4"
    assert "path" not in entry


def test_ambiguous_utils_import_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    first = tmp_path / "one" / "utils_educacao.py"
    second = tmp_path / "two" / "utils_educacao.py"
    first.parent.mkdir()
    second.parent.mkdir()
    first.write_text("VALUE = 1\n", encoding="utf-8")
    second.write_text("VALUE = 2\n", encoding="utf-8")
    _import_utils_module(monkeypatch, first)
    with pytest.raises(EducationFingerprintError, match="ambiguo"):
        resolve_imported_python_module_contract(
            "utils_educacao",
            contract_id="utils_educacao",
            search_paths=(str(first.parent), str(second.parent)),
        )


def test_unverifiable_utils_import_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(
        sys.modules,
        "utils_educacao",
        SimpleNamespace(__file__="utils_educacao.py", __spec__=None),
    )
    with pytest.raises(EducationFingerprintError, match="nao e verificavel"):
        resolve_imported_python_module_contract(
            "utils_educacao",
            contract_id="utils_educacao",
            search_paths=(),
        )


def test_changed_utils_source_invalidates_contract_digest(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source = tmp_path / "utils_educacao.py"
    source.write_text("VALUE = 1\n", encoding="utf-8")
    _import_utils_module(monkeypatch, source)
    contract = resolve_imported_python_module_contract(
        "utils_educacao",
        contract_id="utils_educacao",
        search_paths=(str(tmp_path),),
    )
    before = digest_contract_files(
        tmp_path,
        allowlist=(),
        external_python_contracts=(contract,),
    )
    source.write_text("VALUE = 2\n", encoding="utf-8")
    after = digest_contract_files(
        tmp_path,
        allowlist=(),
        external_python_contracts=(contract,),
    )
    assert before["aggregateSha256"] != after["aggregateSha256"]


def test_algorithm_mismatch_is_classified_as_safe_miss(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    path.write_text(
        json.dumps({"algorithmVersion": "education-input-fingerprint-v0"}),
        encoding="utf-8",
    )
    loaded = load_task_state(path)
    assert loaded.state is None
    assert loaded.reason == "algorithm_changed"


def test_corrupt_state_is_a_real_safe_miss(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    path.write_text("{broken", encoding="utf-8")
    assert load_task_state(path).reason == "manifest_invalid"


def test_test_roots_never_target_real_public_or_pipeline_data(tmp_path: Path) -> None:
    candidate = (tmp_path / "public" / "data").resolve()
    assert candidate != (REPO_ROOT / "public" / "data").resolve()
    assert (DATA_PIPELINE_DIR / "data").resolve() not in candidate.parents


def test_skip_fixture_never_calls_database(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    database = Mock(side_effect=AssertionError("database"))
    monkeypatch.setattr(EXPORTER, "_get_education_engine", database)
    run = _run_exporter(monkeypatch, tmp_path)
    assert run.result == 0
    database.assert_not_called()


def test_task_state_contract_contains_no_paths_credentials_urls_or_source_content(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source = tmp_path / "personal" / "utils_educacao.py"
    source.parent.mkdir()
    source.write_text("SECRET_SOURCE_CONTENT = 1\n", encoding="utf-8")
    _import_utils_module(monkeypatch, source)
    contract = resolve_imported_python_module_contract(
        "utils_educacao",
        contract_id="utils_educacao",
        search_paths=(str(source.parent),),
    )
    digests = digest_contract_files(
        tmp_path,
        allowlist=(),
        external_python_contracts=(contract,),
    )
    serialized = json.dumps(digests, sort_keys=True).lower()
    assert str(tmp_path).lower() not in serialized
    assert "sesi_db_dir" not in serialized
    assert "secret_source_content" not in serialized
    assert "password" not in serialized
    assert "http://" not in serialized and "https://" not in serialized


def test_operational_result_sidecar_rejects_public_data_target(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    unsafe = (REPO_ROOT / "public" / "data" / "education-result.json").resolve()
    monkeypatch.setenv(EXPORTER.EDUCATION_RESULT_ENV, str(unsafe))
    with pytest.raises(EducationPublicationError, match="inseguro"):
        EXPORTER.emit_education_result(reused=True)


def test_network_block_is_active() -> None:
    with pytest.raises(AssertionError, match="rede"):
        socket.create_connection(("example.invalid", 443))
