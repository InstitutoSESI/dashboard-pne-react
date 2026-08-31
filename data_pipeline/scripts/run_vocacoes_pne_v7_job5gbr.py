"""CLI do Job 5G-B-R V7, sem banco, rede, publicação, frontend ou compilador."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_PIPELINE_DIR = REPO_ROOT / "data_pipeline"
if str(DATA_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_PIPELINE_DIR))

from src.vocacoes_pne_job5gbr import (  # noqa: E402
    DEFAULT_OUTPUT_ROOT,
    materialize,
    validate_existing_output,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
        help="Novo staging corrigido, obrigatoriamente fora de public/data, src e inputs.",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Valida pacote existente e hashes congelados sem escrever.",
    )
    args = parser.parse_args()
    output = args.output_dir.resolve()
    report = validate_existing_output(output) if args.validate_only else materialize(output)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
