from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


DATA_PIPELINE_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = DATA_PIPELINE_DIR.parent
sys.path.insert(0, str(DATA_PIPELINE_DIR))

from src.municipal_finance_icms_education import (  # noqa: E402
    ARTIFACT_PATHS,
    build_icms_education_manifest,
    canonical_manifest_json,
    load_icms_education_registry,
    load_icms_education_source,
    parse_icms_education_csv,
)
from src.publication_transaction import promote_files_atomically  # noqa: E402


DEFAULT_REGISTRY = REPO_ROOT / "config" / "municipalities" / "rs.json"
DEFAULT_TARGET_ROOT = (
    DATA_PIPELINE_DIR / "data" / "municipal_finance" / "icms_education" / "rs"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Valida e preserva transacionalmente o CSV e a documentação oficial "
            "do IMERS/PRE baixados do IMERSVis."
        )
    )
    parser.add_argument("--csv", required=True, type=Path)
    parser.add_argument("--data-dictionary", required=True, type=Path)
    parser.add_argument("--methodology-note", required=True, type=Path)
    parser.add_argument("--results-presentation", required=True, type=Path)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--target-root", type=Path, default=DEFAULT_TARGET_ROOT)
    parser.add_argument("--accessed-at")
    parser.add_argument("--apply", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    inputs = {
        "raw_data": args.csv,
        "data_dictionary": args.data_dictionary,
        "methodology_note": args.methodology_note,
        "results_presentation": args.results_presentation,
    }
    for role, path in inputs.items():
        if not path.is_file():
            raise RuntimeError(f"Arquivo de entrada ausente ({role}): {path}.")

    municipalities = load_icms_education_registry(args.registry)
    artifacts = {role: path.read_bytes() for role, path in inputs.items()}
    _, quality = parse_icms_education_csv(artifacts["raw_data"], municipalities)
    accessed_at = args.accessed_at or datetime.now(
        ZoneInfo("America/Sao_Paulo")
    ).isoformat(timespec="seconds")
    manifest = build_icms_education_manifest(artifacts, quality, accessed_at)

    target_root = args.target_root.resolve()
    target_root.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=f".{target_root.name}-source-stage-",
        dir=target_root.parent,
    ) as stage_directory:
        stage_root = Path(stage_directory)
        for role, relative_path in ARTIFACT_PATHS.items():
            destination = stage_root / relative_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(inputs[role], destination)
        (stage_root / "manifest.json").write_text(
            canonical_manifest_json(manifest),
            encoding="utf-8",
            newline="\n",
        )

        validated = load_icms_education_source(stage_root, args.registry)
        publication_paths = [*ARTIFACT_PATHS.values(), Path("manifest.json")]
        changed_paths = [
            relative_path
            for relative_path in publication_paths
            if not (target_root / relative_path).is_file()
            or (target_root / relative_path).read_bytes()
            != (stage_root / relative_path).read_bytes()
        ]
        if args.apply and changed_paths:
            promote_files_atomically(stage_root, target_root, changed_paths)

    print(
        json.dumps(
            {
                "validated": True,
                "applied": bool(args.apply),
                "changedFiles": [path.as_posix() for path in changed_paths],
                "sourceId": validated["sourceId"],
                "rawSha256": validated["rawSha256"],
                "manifestSha256": validated["manifestSha256"],
                "quality": validated["quality"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
