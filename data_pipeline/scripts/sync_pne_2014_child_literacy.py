#!/usr/bin/env python3
"""Valida ou materializa o snapshot de alfabetização do PNE 2014–2024."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path


DATA_PIPELINE_DIR = Path(__file__).resolve().parents[1]
if str(DATA_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_PIPELINE_DIR))

from src.pne_2014_child_literacy import (  # noqa: E402
    SNAPSHOT_DIR,
    build_snapshot,
    snapshot_digest,
)
from src.pne_state_context import (  # noqa: E402
    load_pne_state_context,
    resolve_state_snapshot_dir,
)
from src.state_config import DEFAULT_STATE_CODE  # noqa: E402


def _source_dir(value: str | None) -> Path:
    configured = value or os.environ.get("PNE_CHILD_LITERACY_SOURCE_DIR")
    if not configured:
        raise ValueError(
            "Informe --source-dir ou PNE_CHILD_LITERACY_SOURCE_DIR."
        )
    path = Path(configured).resolve()
    if not path.is_dir():
        raise FileNotFoundError(path)
    return path


def _apply(output_dir: Path, files: dict[str, bytes]) -> None:
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(
        tempfile.mkdtemp(prefix=f".{output_dir.name}.tmp-", dir=output_dir.parent)
    )
    backup = output_dir.with_name(f".{output_dir.name}.previous")
    try:
        for filename, content in files.items():
            (temporary / filename).write_bytes(content)
        if backup.exists():
            shutil.rmtree(backup)
        if output_dir.exists():
            output_dir.replace(backup)
        temporary.replace(output_dir)
        if backup.exists():
            shutil.rmtree(backup)
    except Exception:
        if output_dir.exists() and backup.exists():
            shutil.rmtree(output_dir)
            backup.replace(output_dir)
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", default=DEFAULT_STATE_CODE)
    parser.add_argument("--source-dir")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--reference-date", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    state = load_pne_state_context(args.state)
    output = (
        args.output_dir.resolve()
        if args.output_dir is not None
        else resolve_state_snapshot_dir(SNAPSHOT_DIR, state.state_code).resolve()
    )

    files = build_snapshot(
        _source_dir(args.source_dir),
        reference_date=args.reference_date,
        state_code=state.state_code,
    )
    if args.apply:
        _apply(output, files)
    report = {
        "cycle": "pne_2014_2024",
        "digest": snapshot_digest(files),
        "mode": "apply" if args.apply else "check",
        "state": state.state_code,
        "output": str(output),
        "written": bool(args.apply),
    }
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
