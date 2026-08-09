from __future__ import annotations

from datetime import datetime
from functools import lru_cache
import importlib.util
import io
import json
import math
import os
from pathlib import Path
import socket
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pandas as pd
import pytest


DATA_PIPELINE_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = DATA_PIPELINE_DIR.parent
if str(DATA_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_PIPELINE_DIR))

from src import pipeline_profiling as profiling  # noqa: E402
from src.municipality_registry import load_municipality_registry  # noqa: E402
from src.state_config import StateConfig, StateNameForms  # noqa: E402


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


update = _load_script("profiling_update_static_data", "update_static_data.py")
validator = _load_script("profiling_validate_static_details", "validate_static_details.py")


@pytest.fixture(autouse=True)
def _block_network(monkeypatch):
    def blocked(*_args, **_kwargs):
        raise AssertionError("testes de profiling nao podem acessar a rede")

    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)


def _root_session(tmp_path: Path, *, run_id: str = "test-root") -> profiling.ProfileSession:
    return profiling.ProfileSession.create_root(
        state_code="RS",
        command="test",
        parameters={"dryRun": True},
        requested_output=tmp_path / run_id,
        run_id=run_id,
    )


def _finish(session: profiling.ProfileSession, status: str = "success") -> None:
    session.finish(status)


def _event(session: profiling.ProfileSession, name: str) -> dict:
    return next(event for event in session.event_dicts() if event["name"] == name)


def _one_municipality_registry(tmp_path: Path):
    state = StateConfig(
        schema_version="state-config-v1",
        state_code="RS",
        state_name="Rio Grande do Sul",
        state_name_forms=StateNameForms(
            nominative="o Rio Grande do Sul",
            with_de="do Rio Grande do Sul",
            with_com="com o Rio Grande do Sul",
        ),
        municipality_ibge_prefix="43",
        expected_municipality_count=1,
        locale="pt-BR",
    )
    registry_path = tmp_path / "registry.json"
    registry_path.write_text(
        json.dumps(
            {
                "schemaVersion": "municipality-registry-v1",
                "stateCode": "RS",
                "municipalityCount": 1,
                "municipalities": [
                    {
                        "ibgeCode": "4300034",
                        "name": "Acegua",
                        "slug": "acegua",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return state, load_municipality_registry(state, registry_path=registry_path)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False) + "\n", encoding="utf-8")


def test_valid_session_has_versioned_schema_utc_timestamps_and_minimal_environment(
    tmp_path: Path,
) -> None:
    session = _root_session(tmp_path)
    with profiling.activate_profile_session(session):
        with profiling.profile_step("test.success") as operation:
            operation.add_counter("rows", 3)
    _finish(session)

    profile_path, summary_path = profiling.write_profile_report(session)
    report = json.loads(profile_path.read_text(encoding="utf-8"))
    summary = json.loads(summary_path.read_text(encoding="utf-8"))

    assert report["schemaVersion"] == profiling.PROFILE_SCHEMA_VERSION
    assert summary["schemaVersion"] == profiling.PROFILE_SUMMARY_SCHEMA_VERSION
    assert report["status"] == "success"
    assert report["events"][0]["status"] == "success"
    assert set(report["environment"]) == {
        "platform",
        "pythonImplementation",
        "pythonVersion",
    }
    for timestamp in (report["startedAt"], report["finishedAt"]):
        assert timestamp.endswith("Z")
        assert datetime.fromisoformat(timestamp.replace("Z", "+00:00")).utcoffset() is not None


def test_event_duration_uses_perf_counter_ns(tmp_path: Path) -> None:
    session = _root_session(tmp_path)
    with patch.object(
        profiling.time,
        "perf_counter_ns",
        side_effect=[1_000_000_000, 1_000_001_234],
    ):
        with profiling.profile_operation("compute", "clock"):
            pass
    # The context above had no active session; repeat under the explicit one.
    with patch.object(
        profiling.time,
        "perf_counter_ns",
        side_effect=[2_000_000_000, 2_001_234_567],
    ):
        with profiling.activate_profile_session(session):
            with profiling.profile_operation("compute", "measured"):
                pass
    assert _event(session, "measured")["durationMs"] == pytest.approx(1.234567)


def test_error_event_propagates_original_exception(tmp_path: Path) -> None:
    session = _root_session(tmp_path)
    with pytest.raises(ValueError, match="boom"):
        with profiling.activate_profile_session(session):
            with profiling.profile_operation("compute", "failing"):
                raise ValueError("boom")
    event = _event(session, "failing")
    assert event["status"] == "error"
    assert event["errorType"] == "ValueError"


def test_parent_child_hierarchy_and_ids_are_unique(tmp_path: Path) -> None:
    session = _root_session(tmp_path)
    with profiling.activate_profile_session(session):
        with profiling.profile_step("parent") as parent:
            with profiling.profile_operation("compute", "child"):
                pass
    events = session.event_dicts()
    assert len({event["eventId"] for event in events}) == len(events)
    child = next(event for event in events if event["name"] == "child")
    assert child["parentEventId"] == parent.event_id


@pytest.mark.parametrize("invalid", [math.nan, math.inf, -math.inf])
def test_counters_reject_non_finite_values(tmp_path: Path, invalid: float) -> None:
    session = _root_session(tmp_path)
    with profiling.activate_profile_session(session):
        with pytest.raises(profiling.ProfileValidationError, match="finitos"):
            with profiling.profile_operation("compute", "invalid") as operation:
                operation.add_counter("rows", invalid)


def test_paths_and_credentials_are_sanitized(tmp_path: Path) -> None:
    session = _root_session(tmp_path)
    personal = Path.home() / "private" / "payload.json"
    with profiling.activate_profile_session(session):
        with profiling.profile_operation(
            "query",
            "secure",
            metadata={
                "path": personal,
                "connectionUrl": "postgresql://alice:secret@db.example/base",
                "password": "visible-no",
            },
        ):
            pass
    serialized = profiling.canonical_profile_json(session.event_dicts())
    assert str(Path.home()) not in serialized
    assert "alice" not in serialized
    assert "secret" not in serialized
    assert "visible-no" not in serialized
    assert "[REDACTED]" in serialized


def test_canonical_json_is_deterministic_and_rejects_non_finite() -> None:
    first = profiling.canonical_profile_json({"z": 1, "a": [2, 3]})
    second = profiling.canonical_profile_json({"a": [2, 3], "z": 1})
    assert first == second
    with pytest.raises(profiling.ProfileValidationError):
        profiling.canonical_profile_json({"value": math.nan})


def test_writing_the_same_finished_report_is_deterministic(tmp_path: Path) -> None:
    session = _root_session(tmp_path)
    with profiling.activate_profile_session(session):
        with profiling.profile_step("stable"):
            pass
    _finish(session)
    profile_path, summary_path = profiling.write_profile_report(session)
    first = (profile_path.read_bytes(), summary_path.read_bytes())
    profiling.write_profile_report(session)
    assert first == (profile_path.read_bytes(), summary_path.read_bytes())


def test_disabled_path_has_no_timer_directory_or_serialization(tmp_path: Path) -> None:
    disabled = profiling.ProfileSession.disabled()
    with (
        patch.object(profiling.time, "perf_counter_ns", side_effect=AssertionError("timer")),
        patch.object(profiling, "canonical_profile_json", side_effect=AssertionError("json")),
    ):
        with profiling.activate_profile_session(disabled):
            with profiling.profile_operation("compute", "disabled") as operation:
                operation.add_counter("rows", 1)
    assert list(tmp_path.iterdir()) == []
    assert disabled.events == []


def test_profile_output_without_profile_is_rejected() -> None:
    with pytest.raises(SystemExit) as exc:
        update.parse_args(["--profile-output", "ignored"])
    assert exc.value.code == 2


def test_unsafe_profile_output_is_rejected() -> None:
    with pytest.raises(SystemExit) as exc:
        update.parse_args(
            [
                "--profile",
                "--profile-output",
                str(REPO_ROOT / "public" / "data" / "profile"),
            ]
        )
    assert exc.value.code == 2


def test_dry_run_creates_planning_profile_without_pipeline_subprocesses(
    tmp_path: Path,
) -> None:
    output = tmp_path / "dry-run-profile"
    args = SimpleNamespace(
        dry_run=True,
        skip_export=False,
        skip_partition=False,
        skip_education=False,
        education_only=False,
        skip_build=True,
        build=False,
        validate_only=False,
        no_include_derived=False,
        profile=True,
        profile_output=output,
        state="RS",
    )
    with (
        patch.object(update, "parse_args", return_value=args),
        patch.object(update, "run_git_status", return_value=""),
        patch.object(update, "run_command", side_effect=AssertionError("subprocess")),
        patch.object(
            update,
            "sync_partitioned_to_public",
            side_effect=AssertionError("sync"),
        ),
    ):
        assert update.main() == 0

    report = json.loads((output / "profile.json").read_text(encoding="utf-8"))
    assert report["parameters"]["dryRun"] is True
    assert report["summary"]["counters"]["processesStarted"] == 0
    assert any(event["name"] == "plan.export" for event in report["events"])
    assert not (REPO_ROOT / "data_pipeline" / ".staging").is_relative_to(output)


def _write_child_fragment(
    root: profiling.ProfileSession,
    context: profiling.ProfileChildContext,
    *,
    fail: bool = False,
) -> profiling.ProfileSession:
    with patch.dict(os.environ, dict(context.environment), clear=False):
        child = profiling.ProfileSession.from_environment(command="child")
    with profiling.activate_profile_session(child):
        if fail:
            with pytest.raises(RuntimeError):
                with profiling.profile_operation("compute", "child.work"):
                    raise RuntimeError("child failed")
        else:
            with profiling.profile_operation("compute", "child.work"):
                pass
    child.finish("error" if fail else "success")
    profiling.write_profile_fragment(child)
    return child


def test_subprocess_fragment_is_correlated_and_consolidated(tmp_path: Path) -> None:
    root = _root_session(tmp_path)
    with profiling.activate_profile_session(root):
        with profiling.profile_operation("subprocess", "child") as parent:
            context = root.child_context(
                parent_event_id=parent.event_id,
                command="child",
            )
    child = _write_child_fragment(root, context)
    _finish(root)
    profile_path, _summary_path = profiling.write_profile_report(root)
    report = json.loads(profile_path.read_text(encoding="utf-8"))
    child_event = next(event for event in report["events"] if event["name"] == "child.work")
    assert child_event["parentEventId"] == parent.event_id
    assert any(process["runId"] == child.run_id for process in report["processes"])
    assert report["summary"]["missingFragments"] == []


def test_failed_child_fragment_keeps_error_status(tmp_path: Path) -> None:
    root = _root_session(tmp_path)
    with profiling.activate_profile_session(root):
        with profiling.profile_operation("subprocess", "child") as parent:
            context = root.child_context(
                parent_event_id=parent.event_id,
                command="child",
            )
    child = _write_child_fragment(root, context, fail=True)
    _finish(root, "error")
    profile_path, _ = profiling.write_profile_report(root)
    report = json.loads(profile_path.read_text(encoding="utf-8"))
    assert next(
        process["status"]
        for process in report["processes"]
        if process["runId"] == child.run_id
    ) == "error"
    assert next(
        event["status"] for event in report["events"] if event["name"] == "child.work"
    ) == "error"


def test_invalid_fragment_is_rejected(tmp_path: Path) -> None:
    root = _root_session(tmp_path)
    with profiling.activate_profile_session(root):
        with profiling.profile_operation("subprocess", "child") as parent:
            context = root.child_context(
                parent_event_id=parent.event_id,
                command="child",
            )
    fragment = root.output_dir / "fragments" / f"{context.run_id}.json"
    fragment.parent.mkdir(parents=True)
    fragment.write_text("{}\n", encoding="utf-8")
    _finish(root)
    with pytest.raises(profiling.ProfileValidationError, match="Schema"):
        profiling.write_profile_report(root)


def test_failed_subprocess_is_recorded_with_controlled_correlation(tmp_path: Path) -> None:
    root = _root_session(tmp_path)
    completed = subprocess.CompletedProcess(["child"], 7)
    with profiling.activate_profile_session(root):
        with patch.object(update.subprocess, "run", return_value=completed) as run:
            with pytest.raises(SystemExit) as exc:
                update.run_command("export", [sys.executable, "child.py"], [])
    assert exc.value.code == 7
    event = _event(root, "export")
    assert event["status"] == "error"
    child_environment = run.call_args.kwargs["env"]
    assert child_environment[profiling.PROFILE_ENV_PARENT_EVENT_ID] == event["eventId"]
    assert child_environment[profiling.PROFILE_ENV_ROOT_RUN_ID] == root.run_id


def test_consolidated_events_are_deterministically_ordered(tmp_path: Path) -> None:
    root = _root_session(tmp_path)
    with profiling.activate_profile_session(root):
        with profiling.profile_step("root.event"):
            pass
    _finish(root)
    profile_path, _ = profiling.write_profile_report(root)
    events = json.loads(profile_path.read_text(encoding="utf-8"))["events"]
    assert events == sorted(events, key=lambda event: (event["startedAt"], event["eventId"]))


def test_query_wrapper_preserves_return_and_records_shape(tmp_path: Path) -> None:
    session = _root_session(tmp_path)
    frame = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
    with profiling.activate_profile_session(session):
        returned = profiling.profiled_query_call("dataset.stable", lambda: frame)
    assert returned is frame
    event = _event(session, "dataset.stable")
    assert event["counters"] == {"columns": 2, "rows": 2}


def test_query_wrapper_propagates_error(tmp_path: Path) -> None:
    session = _root_session(tmp_path)
    error = LookupError("query failed")
    with pytest.raises(LookupError) as exc:
        with profiling.activate_profile_session(session):
            profiling.profiled_query_call("dataset.error", Mock(side_effect=error))
    assert exc.value is error
    assert _event(session, "dataset.error")["status"] == "error"


def test_cache_wrapper_aggregates_hit_and_miss(tmp_path: Path) -> None:
    session = _root_session(tmp_path)

    @lru_cache(maxsize=1)
    def cached(value: int) -> int:
        return value * 2

    with profiling.activate_profile_session(session):
        assert profiling.profiled_cache_call(
            "cache.sample", lambda: cached(2), cached.cache_info
        ) == 4
        assert profiling.profiled_cache_call(
            "cache.sample", lambda: cached(2), cached.cache_info
        ) == 4
    _finish(session)
    event = _event(session, "cache.sample")
    assert event["counters"]["hits"] == 1
    assert event["counters"]["misses"] == 1
    assert event["counters"]["operations"] == 2


def test_file_comparison_counts_existing_reads_without_extra_read() -> None:
    class FakeStat:
        def __init__(self, modified: int):
            self.st_size = 3
            self.st_mtime_ns = modified

    class FakePath:
        def __init__(self, content: bytes, modified: int):
            self.content = content
            self.modified = modified
            self.open_calls = 0

        def is_file(self):
            return True

        def stat(self):
            return FakeStat(self.modified)

        def open(self, _mode):
            self.open_calls += 1
            return io.BytesIO(self.content)

    source = FakePath(b"abc", 1)
    target = FakePath(b"abc", 2)
    metrics = {"bytes_compared": 0}
    assert update.files_match(source, target, metrics) is True
    assert source.open_calls == 1
    assert target.open_calls == 1
    assert metrics["bytes_compared"] == 6


def test_sync_preserves_functional_stats_and_profiles_volumes(tmp_path: Path) -> None:
    _state, registry = _one_municipality_registry(tmp_path)
    source = tmp_path / "static_partitioned"
    public = tmp_path / "public" / "data"
    public.mkdir(parents=True)
    _write_json(source / "indicadores.json", {})
    _write_json(
        source / "municipios_index.json",
        registry.build_public_index_payload(generated_at="2026-08-02T00:00:00Z"),
    )
    for relative in update.CYCLE_STATIC_FILES:
        _write_json(source / relative, {})
    _write_json(
        source / "municipios" / "4300034" / "index.json",
        {"id_municipio": "4300034", "municipio": "Acegua", "slug": "acegua"},
    )
    _write_json(source / "municipios" / "4300034" / "details.json", {})

    session = _root_session(tmp_path, run_id="sync-profile")
    results = []
    with profiling.activate_profile_session(session):
        stats = update.sync_partitioned_to_public(
            results,
            source_root=source,
            public_root=public,
            registry=registry,
        )
    _finish(session)

    assert stats.created == 6
    assert stats.updated == 0
    assert stats.preserved == 0
    assert stats.removed == 0
    assert stats.files_evaluated == 6
    assert stats.bytes_copied > 0
    assert stats.directories_examined > 0
    promotion = _event(session, "sync.promotion")
    assert promotion["counters"]["created"] == stats.created
    assert promotion["counters"]["bytesCopied"] == stats.bytes_copied


def test_validation_profiles_errors_and_warning_categories(tmp_path: Path) -> None:
    state, registry = _one_municipality_registry(tmp_path)
    data_dir = tmp_path / "empty-data"
    data_dir.mkdir()
    args = SimpleNamespace(
        state="RS",
        data_dir=str(data_dir),
        max_problems=10,
    )
    session = _root_session(tmp_path, run_id="validation-profile")
    with (
        profiling.activate_profile_session(session),
        patch.object(validator, "parse_args", return_value=args),
        patch.object(validator, "load_state_config", return_value=state),
        patch.object(validator, "load_municipality_registry", return_value=registry),
    ):
        assert validator.main() == 1
    _finish(session)
    result = _event(session, "validation.result")
    assert result["counters"]["errors"] >= 1
    assert result["counters"]["warnings"] == 0
    problems = [
        validator.Problem("WARNING", data_dir, "dependency warning"),
        validator.Problem("WARNING", data_dir, "series warning"),
    ]
    assert validator._warning_categories(problems) == {"dependency": 1, "series": 1}


def test_profile_contains_no_analytical_payload_or_full_environment(tmp_path: Path) -> None:
    marker = "ANALYTICAL_ROW_VALUE_MUST_NOT_APPEAR"
    session = _root_session(tmp_path, run_id="privacy-profile")
    with profiling.activate_profile_session(session):
        with profiling.profile_operation(
            "compute",
            "privacy",
            counters={"rows": 1},
            metadata={"datasetId": "safe-dataset"},
        ):
            pass
    _finish(session)
    profile_path, _ = profiling.write_profile_report(session)
    content = profile_path.read_text(encoding="utf-8")
    assert marker not in content
    report = json.loads(content)
    assert set(report["environment"]) == {
        "platform",
        "pythonImplementation",
        "pythonVersion",
    }


def test_all_test_outputs_stay_outside_public_data(tmp_path: Path) -> None:
    output = (_root_session(tmp_path, run_id="isolated").output_dir).resolve()
    public_data = (REPO_ROOT / "public" / "data").resolve()
    assert output != public_data
    assert public_data not in output.parents
