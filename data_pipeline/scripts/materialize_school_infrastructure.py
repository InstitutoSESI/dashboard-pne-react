#!/usr/bin/env python3
"""Materializa a INFRA-2 em staging, sem escrever em public/data."""

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

from src.data_loader import load_school_infrastructure_source_data  # noqa: E402
from src.school_infrastructure_materialization import (  # noqa: E402
    adapt_legacy_document,
    build_contracts,
    build_manifest,
    compare_trees,
    compare_with_public,
    replace_directory_atomically,
    validate_stage,
    write_json_atomic,
)


DEFAULT_STAGE = DATA_PIPELINE_DIR / ".staging" / "school-infrastructure-v2"
PUBLIC_MUNICIPALITIES = REPO_ROOT / "public" / "data" / "educacao" / "municipios"
PUBLIC_INDEX = REPO_ROOT / "public" / "data" / "educacao" / "municipios_index.json"


def load_universe() -> list[dict]:
    payload = json.loads(PUBLIC_INDEX.read_text(encoding="utf-8"))
    municipalities = payload["municipios"]
    if len(municipalities) != 497:
        raise ValueError(
            f"Cadastro oficial deve ter 497 municípios; contém {len(municipalities)}"
        )
    return municipalities


def build_stage(
    destination: Path,
    contracts: dict[str, dict],
    municipalities: list[dict],
    *,
    expected_diff: dict | None = None,
) -> dict:
    codes = [str(item["id_municipio"]) for item in municipalities]
    municipal_directory = destination / "municipios"
    municipal_directory.mkdir(parents=True, exist_ok=True)
    for code in sorted(codes):
        public_path = PUBLIC_MUNICIPALITIES / f"{code}.json"
        document = json.loads(public_path.read_text(encoding="utf-8"))
        staged = adapt_legacy_document(document, contracts[code])
        write_json_atomic(municipal_directory / f"{code}.json", staged)

    validation = validate_stage(destination, codes)
    write_json_atomic(destination / "validation-report.json", validation)
    diff = (
        compare_with_public(destination, PUBLIC_MUNICIPALITIES)
        if expected_diff is None
        else expected_diff
    )
    write_json_atomic(destination / "diff-report.json", diff)
    manifest = build_manifest(destination, codes)
    write_json_atomic(destination / "index.json", manifest)
    if not validation["valid"]:
        raise ValueError(f"Validação falhou: {validation['errors'][:5]}")
    if diff["unexpectedChangeCount"]:
        raise ValueError(
            f"Diff contém {diff['unexpectedChangeCount']} mudanças inesperadas"
        )
    return {"validation": validation, "diff": diff, "manifest": manifest}


def materialize(destination: Path = DEFAULT_STAGE) -> dict:
    destination = destination.resolve()
    staging_root = (DATA_PIPELINE_DIR / ".staging").resolve()
    if destination != staging_root and staging_root not in destination.parents:
        raise ValueError(f"Destino deve permanecer em {staging_root}")
    staging_root.mkdir(parents=True, exist_ok=True)
    municipalities = load_universe()
    source = load_school_infrastructure_source_data()
    codes = [str(item["id_municipio"]) for item in municipalities]
    contracts = build_contracts(source, codes)
    first = Path(tempfile.mkdtemp(prefix=".school-infra-first-", dir=staging_root))
    second = Path(tempfile.mkdtemp(prefix=".school-infra-second-", dir=staging_root))
    try:
        first_result = build_stage(first, contracts, municipalities)
        build_stage(
            second,
            contracts,
            municipalities,
            expected_diff=first_result["diff"],
        )
        deterministic = compare_trees(first, second)
        if not deterministic["identical"]:
            raise ValueError(f"Materializações divergentes: {deterministic}")
        replace_directory_atomically(first, destination)
        first = None
        return {
            "stage": destination,
            "manifest": first_result["manifest"],
            "validation": first_result["validation"],
            "diff": first_result["diff"],
            "determinism": deterministic,
        }
    finally:
        for temporary in (first, second):
            if temporary is not None and temporary.exists():
                shutil.rmtree(temporary)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_STAGE)
    args = parser.parse_args()
    result = materialize(args.output)
    print(
        json.dumps(
            {
                "municipalityCount": result["manifest"]["municipalityCount"],
                "contentHash": result["manifest"]["contentHash"],
                "valid": result["validation"]["valid"],
                "unexpectedChangeCount": result["diff"]["unexpectedChangeCount"],
                "deterministic": result["determinism"]["identical"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
