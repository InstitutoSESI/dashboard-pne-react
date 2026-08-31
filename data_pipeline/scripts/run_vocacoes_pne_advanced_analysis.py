from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


DATA_PIPELINE_DIR = Path(__file__).resolve().parents[1]
if str(DATA_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_PIPELINE_DIR))

from src.vocacoes_pne_advanced_analysis import (  # noqa: E402
    DEFAULT_OUTPUT_ROOT,
    PREREG_PROBE_PATH,
    check_availability_probe,
    materialize_availability_probe,
    materialize_single_candidate,
    materialize_twice_transactionally,
    sha256_file,
    validate_existing_output,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--probe-only", action="store_true")
    mode.add_argument("--check-probe", action="store_true")
    mode.add_argument("--materialize", action="store_true")
    mode.add_argument("--single-candidate", action="store_true")
    mode.add_argument("--check", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_ROOT)
    arguments = parser.parse_args()
    if arguments.probe_only or arguments.check_probe:
        payload = (
            materialize_availability_probe()
            if arguments.probe_only
            else check_availability_probe()
        )
        receipt = {
            "state": payload["state"],
            "selectorCount": payload["selectorCount"],
            "failureCount": payload["failureCount"],
            "probePath": str(PREREG_PROBE_PATH),
            "probeSha256": sha256_file(PREREG_PROBE_PATH),
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
        }
    print(
        json.dumps(
            receipt,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
