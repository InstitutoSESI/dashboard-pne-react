#!/usr/bin/env python3
"""Valida ou materializa o snapshot agregado Criança Alfabetizada."""

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

from src.child_literacy import SNAPSHOT_DIR, build_snapshot, sha256_bytes  # noqa: E402


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
    try:
        for filename, content in files.items():
            (temporary / filename).write_bytes(content)
        if output_dir.exists():
            backup = output_dir.with_name(f".{output_dir.name}.previous")
            if backup.exists():
                shutil.rmtree(backup)
            output_dir.replace(backup)
            temporary.replace(output_dir)
            shutil.rmtree(backup)
        else:
            temporary.replace(output_dir)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir")
    parser.add_argument("--output-dir", type=Path, default=SNAPSHOT_DIR)
    parser.add_argument("--reference-date", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    files = build_snapshot(
        _source_dir(args.source_dir),
        reference_date=args.reference_date,
    )
    output = args.output_dir.resolve()
    if args.apply:
        _apply(output, files)
    report = {
        "mode": "apply" if args.apply else "check",
        "output": str(output),
        "files": {
            filename: sha256_bytes(content)
            for filename, content in sorted(files.items())
        },
        "written": bool(args.apply),
    }
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
