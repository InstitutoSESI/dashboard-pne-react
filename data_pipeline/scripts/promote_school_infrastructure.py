#!/usr/bin/env python3
"""Promove o staging aprovado da INFRA-3 com rollback automático."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


DATA_PIPELINE_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = DATA_PIPELINE_DIR.parent
sys.path.insert(0, str(DATA_PIPELINE_DIR))

from src.school_infrastructure_materialization import (  # noqa: E402
    promote_municipal_documents,
)


DEFAULT_STAGE = DATA_PIPELINE_DIR / ".staging" / "school-infrastructure-v2"
PUBLIC_ROOT = REPO_ROOT / "public" / "data" / "educacao"
PUBLIC_INDEX = PUBLIC_ROOT / "municipios_index.json"


def official_codes() -> list[str]:
    payload = json.loads(PUBLIC_INDEX.read_text(encoding="utf-8"))
    return [str(item["id_municipio"]) for item in payload["municipios"]]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", type=Path, default=DEFAULT_STAGE)
    args = parser.parse_args()
    result = promote_municipal_documents(
        args.stage,
        PUBLIC_ROOT,
        official_codes(),
    )
    print(
        json.dumps(
            {
                "promotedFileCount": result["promotedFileCount"],
                "contentHash": result["contentHash"],
                "valid": result["validation"]["valid"],
                "postPromotionUnexpectedChangeCount": result[
                    "postPromotionDiff"
                ]["unexpectedChangeCount"],
                "remainingDifferences": len(
                    result["postPromotionDiff"]["changesByPath"]
                ),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
