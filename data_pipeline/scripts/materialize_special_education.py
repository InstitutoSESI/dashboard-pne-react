#!/usr/bin/env python3
"""Materializa e promove atomicamente o contrato special-education-v1."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path


DATA_PIPELINE_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = DATA_PIPELINE_DIR.parent
sys.path.insert(0, str(DATA_PIPELINE_DIR))

from src.data_loader import load_special_education_school_source_data  # noqa: E402
from src.special_education_materialization import (  # noqa: E402
    materialize,
    replace_directory_atomically,
    tree_hash,
)


PUBLIC_EDUCATION = REPO_ROOT / "public" / "data" / "educacao"
DEFAULT_OUTPUT = PUBLIC_EDUCATION / "educacao-especial"
MUNICIPAL_INDEX = PUBLIC_EDUCATION / "municipios_index.json"
OVERVIEW_MUNICIPALITIES = PUBLIC_EDUCATION / "visao-geral-municipal"


def municipalities() -> list[dict]:
    payload = json.loads(MUNICIPAL_INDEX.read_text(encoding="utf-8"))
    result = payload["municipios"]
    if len(result) != 497:
        raise ValueError(f"Cadastro municipal contém {len(result)} itens, não 497.")
    return result


def _new_2025_total(contract: dict) -> int | float | None:
    yearly = next(item for item in contract["years"] if item["year"] == 2025)
    return yearly["cuts"]["total"]["specialEducation"]["enrollments"]["value"]


def reconcile_overview(stage: Path, universe: list[dict]) -> dict:
    divergent = []
    compared = 0
    for municipality in universe:
        code = str(municipality["id_municipio"])
        overview_path = OVERVIEW_MUNICIPALITIES / f"{code}.json"
        if not overview_path.exists():
            continue
        overview = json.loads(overview_path.read_text(encoding="utf-8"))
        old_point = overview.get("specialEducation", {}).get("total")
        if isinstance(old_point, dict):
            old_value = old_point.get("value")
        else:
            old_value = old_point
        if old_value is None:
            continue
        compared += 1
        new = json.loads(
            (stage / "municipios" / f"{code}.json").read_text(encoding="utf-8")
        )
        new_value = _new_2025_total(new)
        if new_value != old_value:
            divergent.append({"code": code, "overview": old_value, "new": new_value})
    return {
        "comparedMunicipalities": compared,
        "divergenceCount": len(divergent),
        "divergences": divergent[:20],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    source = load_special_education_school_source_data()
    universe = municipalities()
    staging_root = DATA_PIPELINE_DIR / ".staging"
    staging_root.mkdir(parents=True, exist_ok=True)
    first = Path(tempfile.mkdtemp(prefix=".special-first-", dir=staging_root))
    second = Path(tempfile.mkdtemp(prefix=".special-second-", dir=staging_root))
    first_output = first / "educacao-especial"
    second_output = second / "educacao-especial"
    try:
        first_manifest = materialize(source, universe, first_output)
        second_manifest = materialize(source, universe, second_output)
        first_hash = tree_hash(first_output)
        second_hash = tree_hash(second_output)
        if first_hash != second_hash:
            raise ValueError("Duas materializações idênticas produziram hashes diferentes.")
        reconciliation = reconcile_overview(first_output, universe)
        if reconciliation["divergenceCount"]:
            raise ValueError(
                f"Snapshot 2025 diverge em {reconciliation['divergenceCount']} municípios."
            )
        replace_directory_atomically(first_output, args.output.resolve())
        first_output = None
        print(
            json.dumps(
                {
                    "schemaVersion": first_manifest["schemaVersion"],
                    "municipalityCount": first_manifest["municipalityCount"],
                    "contentHash": first_manifest["contentHash"],
                    "deterministic": first_hash == second_hash,
                    "overviewReconciliation": reconciliation,
                    "output": str(args.output.resolve()),
                },
                ensure_ascii=False,
            )
        )
        return 0
    finally:
        shutil.rmtree(first, ignore_errors=True)
        shutil.rmtree(second, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
