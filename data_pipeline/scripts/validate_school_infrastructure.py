#!/usr/bin/env python3
"""Valida os JSONs da infraestrutura escolar já materializados."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


DATA_PIPELINE_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = DATA_PIPELINE_DIR.parent
sys.path.insert(0, str(DATA_PIPELINE_DIR))

from src.school_infrastructure_materialization import validate_stage  # noqa: E402


DEFAULT_STAGE = DATA_PIPELINE_DIR / ".staging" / "school-infrastructure-v2"
PUBLIC_INDEX = REPO_ROOT / "public" / "data" / "educacao" / "municipios_index.json"


def official_codes() -> list[str]:
    payload = json.loads(PUBLIC_INDEX.read_text(encoding="utf-8"))
    return [str(item["id_municipio"]) for item in payload["municipios"]]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", nargs="?", type=Path, default=DEFAULT_STAGE)
    args = parser.parse_args()
    report = validate_stage(args.stage.resolve(), official_codes())
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
