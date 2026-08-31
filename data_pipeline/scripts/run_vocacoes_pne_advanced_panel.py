"""Executa ou valida o painel analítico alinhado AA1."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


DATA_PIPELINE_ROOT = Path(__file__).resolve().parents[1]
if str(DATA_PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(DATA_PIPELINE_ROOT))

from src.vocacoes_pne_advanced_panel import (  # noqa: E402
    DEFAULT_OUTPUT_ROOT,
    blocked_external_io_guard,
    materialize_single_candidate,
    materialize_twice_transactionally,
    validate_existing_output,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Materializa duas vezes ou valida o pacote AA1 Vocações × PNE."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
        help="Diretório do pacote AA1.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Valida o pacote e todas as fontes sem reescrever artefatos.",
    )
    parser.add_argument(
        "--single-candidate",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.check and args.single_candidate:
        raise ValueError("--check e --single-candidate são mutuamente exclusivos")
    with blocked_external_io_guard():
        if args.single_candidate:
            result = materialize_single_candidate(args.output_dir)
        elif args.check:
            result = validate_existing_output(args.output_dir)
        else:
            result = materialize_twice_transactionally(args.output_dir)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
