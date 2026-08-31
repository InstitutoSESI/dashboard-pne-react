"""Materializa ou valida o freeze pré-teste do Atlas Educação × Território."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


DATA_PIPELINE_ROOT = Path(__file__).resolve().parents[1]
if str(DATA_PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(DATA_PIPELINE_ROOT))

from src.vocacoes_pne_relationship_atlas import (  # noqa: E402
    DEFAULT_OUTPUT_ROOT,
    materialize_twice_and_freeze,
    validate_existing_output,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    manifest = (
        validate_existing_output(args.output_dir)
        if args.check
        else materialize_twice_and_freeze(args.output_dir)
    )
    print(
        json.dumps(
            {
                "state": manifest["state"],
                "outputDir": str(args.output_dir.resolve()),
                "artifactSetDigestSha256": manifest["artifactSetDigestSha256"],
                **manifest["counts"],
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
