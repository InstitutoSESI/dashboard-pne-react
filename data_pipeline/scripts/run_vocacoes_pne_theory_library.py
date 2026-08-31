from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


DATA_PIPELINE_DIR = Path(__file__).resolve().parents[1]
if str(DATA_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_PIPELINE_DIR))

from src.vocacoes_pne_theory_library import (  # noqa: E402
    DEFAULT_OUTPUT_ROOT,
    materialize_single_candidate,
    materialize_twice_transactionally,
    validate_existing_output,
    verify_frozen_inputs,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--verify-inputs", action="store_true")
    mode.add_argument("--materialize", action="store_true")
    mode.add_argument("--single-candidate", action="store_true")
    mode.add_argument("--check", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_ROOT)
    arguments = parser.parse_args()
    if arguments.verify_inputs:
        hashes = verify_frozen_inputs()
        receipt = {
            "state": "AA3_FROZEN_INPUTS_VERIFIED",
            "inputCount": len(hashes),
            "inputHashes": hashes,
        }
    elif arguments.single_candidate:
        receipt = materialize_single_candidate(arguments.output_dir)
    elif arguments.materialize:
        receipt = materialize_twice_transactionally(arguments.output_dir)
    else:
        manifest = validate_existing_output(arguments.output_dir)
        receipt = {
            "state": manifest["finalState"],
            "outputDir": str(arguments.output_dir.resolve()),
            "artifactSetDigestSha256": manifest["artifactSetDigestSha256"],
            "questionCount": manifest["counts"]["questionCount"],
            "referenceCount": manifest["counts"]["referenceCount"],
        }
    print(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
