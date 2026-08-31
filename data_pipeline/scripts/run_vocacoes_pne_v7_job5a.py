"""Executa o Job 5A V7 somente em staging interno e sem fontes externas."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_PIPELINE_DIR = REPO_ROOT / "data_pipeline"
if str(DATA_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_PIPELINE_DIR))

from src.vocacoes_pne_job5a import (  # noqa: E402
    DEFAULT_OUTPUT_ROOT,
    materialize,
    validate_existing_output,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--no-release-manifest", action="store_true")
    args = parser.parse_args()

    output_root = args.output_dir.resolve()
    if args.check:
        summary = validate_existing_output(output_root)
    else:
        summary = materialize(
            output_root,
            write_release_manifest=not args.no_release_manifest,
        )
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
