from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
UPDATE_PATH = REPO_ROOT / "data_pipeline" / "scripts" / "update_static_data.py"
UPDATE_SPEC = importlib.util.spec_from_file_location(
    "update_static_data_build_decoupling",
    UPDATE_PATH,
)
assert UPDATE_SPEC is not None and UPDATE_SPEC.loader is not None
update = importlib.util.module_from_spec(UPDATE_SPEC)
sys.modules[UPDATE_SPEC.name] = update
UPDATE_SPEC.loader.exec_module(update)


def _args(**overrides):
    values = {
        "dry_run": False,
        "skip_export": False,
        "skip_partition": False,
        "skip_education": False,
        "education_only": False,
        "build": False,
        "skip_build": False,
        "validate_only": False,
        "no_include_derived": False,
        "profile": False,
        "state": "RS",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


@pytest.fixture(autouse=True)
def isolate_data_roots(monkeypatch, tmp_path):
    monkeypatch.setattr(update, "PUBLIC_DATA_DIR", tmp_path / "public" / "data")
    monkeypatch.setattr(
        update,
        "STATIC_PARTITIONED_DATA_DIR",
        tmp_path / "pipeline" / "static_partitioned",
    )


def _run(monkeypatch, args, *, fail_at=None):
    events = []
    commands = {}
    state_config = SimpleNamespace(state_code="RS")
    registry = object()

    monkeypatch.setattr(update, "parse_args", lambda: args)
    monkeypatch.setattr(update, "load_state_config", lambda _state: state_config)
    monkeypatch.setattr(
        update,
        "load_municipality_registry",
        lambda _state_config: registry,
    )
    monkeypatch.setattr(update, "run_git_status", lambda: "")
    monkeypatch.setattr(update, "ensure_git_update_safe", lambda *_args: None)

    def run_command(name, command, results):
        events.append(name)
        commands[name] = command
        if name == fail_at:
            results.append(update.StepResult(name, "erro", 0.0))
            raise SystemExit(9)
        results.append(update.StepResult(name, "ok", 0.0))

    def sync(results, **_kwargs):
        events.append("sync")
        if fail_at == "sync":
            raise RuntimeError("falha de sincronizacao injetada")
        results.append(update.StepResult("sync", "ok", 0.0))

    monkeypatch.setattr(update, "run_command", run_command)
    monkeypatch.setattr(update, "sync_partitioned_to_public", sync)
    return events, commands


def test_default_update_never_executes_build(monkeypatch, capsys):
    events, _commands = _run(monkeypatch, _args())

    assert update.main() == 0
    assert events == [
        "export",
        "partition",
        "education",
        "inequality",
        "sync",
        "validate",
    ]
    assert "build: não solicitado" in capsys.readouterr().out


def test_build_flag_executes_the_complete_build_only_after_validation(
    monkeypatch,
    capsys,
):
    events, commands = _run(monkeypatch, _args(build=True))

    assert update.main() == 0
    assert events[-2:] == ["validate", "build"]
    assert commands["build"] == [update.NPM, "run", "build"]
    assert "build: concluído" in capsys.readouterr().out


def test_skip_build_is_accepted_as_a_legacy_no_build_alias(monkeypatch, capsys):
    args = update.parse_args(["--skip-build"])
    events, _commands = _run(monkeypatch, args)

    assert update.main() == 0
    assert "build" not in events
    output = capsys.readouterr().out
    assert "--skip-build e legado" in output
    assert "build: não solicitado" in output


def test_build_and_skip_build_are_mutually_exclusive():
    with pytest.raises(SystemExit) as error:
        update.parse_args(["--build", "--skip-build"])

    assert error.value.code == 2


def test_package_scripts_keep_update_and_build_responsibilities_separate():
    package = json.loads((REPO_ROOT / "package.json").read_text(encoding="utf-8"))
    scripts = package["scripts"]

    assert scripts["update:data"].endswith("update_static_data.py")
    assert "--build" not in scripts["update:data"].split()
    assert scripts["update:data:skip-build"].endswith(
        "update_static_data.py --skip-build"
    )
    assert scripts["update:data:and-build"].endswith(
        "update_static_data.py --build"
    )
    assert scripts["update:education-data"].endswith(
        "update_static_data.py --education-only"
    )
    assert "--build" not in scripts["update:education-data"].split()
    assert scripts["update:education-data:and-build"].endswith(
        "update_static_data.py --education-only --build"
    )
    assert scripts["check:fast"] == (
        "npm run typecheck && npm run lint && npm run build:app"
    )
    assert scripts["build"] == "vite build"
    assert scripts["build:app"] == (
        "vite build --mode app-only --outDir dist/app-only"
    )

    vite = (REPO_ROOT / "vite.config.js").read_text(encoding="utf-8")
    assert "copyPublicDir: false" in vite
    assert "statePublicAssetsPlugin(profile)" in vite


def test_package_lock_root_contract_matches_the_unchanged_dependencies():
    package = json.loads((REPO_ROOT / "package.json").read_text(encoding="utf-8"))
    lock = json.loads(
        (REPO_ROOT / "package-lock.json").read_text(encoding="utf-8")
    )
    root_contract = lock["packages"][""]

    assert root_contract["dependencies"] == package["dependencies"]
    assert root_contract["devDependencies"] == package["devDependencies"]


def test_default_dry_run_does_not_list_build(monkeypatch, capsys):
    events, _commands = _run(monkeypatch, _args(dry_run=True))

    assert update.main() == 0
    output = capsys.readouterr().out
    assert "Rodaria validate" in output
    assert "Rodaria build" not in output
    assert "[update-data] build:" not in output
    assert events == []


def test_dry_run_with_build_lists_the_complete_build_last(monkeypatch, capsys):
    events, _commands = _run(monkeypatch, _args(dry_run=True, build=True))

    assert update.main() == 0
    output = capsys.readouterr().out
    assert output.index("Rodaria validate") < output.index("Rodaria build")
    assert "build: planejado, não executado por dry-run" in output
    assert events == []


@pytest.mark.parametrize(
    ("build", "expected"),
    (
        (False, ["education", "inequality", "validate"]),
        (True, ["education", "inequality", "validate", "build"]),
    ),
)
def test_education_only_build_is_explicit(monkeypatch, build, expected):
    events, _commands = _run(
        monkeypatch,
        _args(education_only=True, build=build),
    )

    assert update.main() == 0
    assert events == expected


def test_validate_only_never_builds(monkeypatch):
    events, _commands = _run(monkeypatch, _args(validate_only=True))

    assert update.main() == 0
    assert events == ["validate"]


def test_validate_only_with_build_is_rejected_by_argparse():
    with pytest.raises(SystemExit) as error:
        update.parse_args(["--validate-only", "--build"])

    assert error.value.code == 2


@pytest.mark.parametrize(
    "fail_at",
    ("export", "education", "inequality", "sync", "validate"),
)
def test_any_data_failure_prevents_the_requested_build(
    monkeypatch,
    capsys,
    fail_at,
):
    events, _commands = _run(
        monkeypatch,
        _args(build=True),
        fail_at=fail_at,
    )

    expected_error = RuntimeError if fail_at == "sync" else SystemExit
    with pytest.raises(expected_error):
        update.main()
    assert "build" not in events
    assert "build: não alcançado por falha anterior" in capsys.readouterr().out


def test_tests_replace_every_pipeline_and_build_effect_with_mocks(
    monkeypatch,
    tmp_path,
):
    events, commands = _run(monkeypatch, _args(build=True))

    before = list(tmp_path.rglob("*"))
    assert update.main() == 0
    after = list(tmp_path.rglob("*"))

    assert events[-1] == "build"
    assert commands["build"] == [update.NPM, "run", "build"]
    assert after == before
