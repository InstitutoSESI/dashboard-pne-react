from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
import time
from pathlib import Path


DATA_PIPELINE_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = DATA_PIPELINE_DIR.parent
sys.path.insert(0, str(DATA_PIPELINE_DIR))

from src.config import MUNICIPAL_FINANCE_EXPORT_DIR  # noqa: E402
from src.municipal_finance import (  # noqa: E402
    DATA_VERSION,
    generate_contracts,
    load_municipality_registry,
    load_source_snapshot,
    refresh_source_snapshot,
    validate_generated_contracts,
    write_coverage_csv,
    write_reconciliation_sample_csv,
)
from src.municipal_finance_constitutional import (  # noqa: E402
    load_constitutional_snapshot,
    merge_constitutional_snapshot,
    refresh_annual_constitutional_snapshot,
    write_constitutional_reports,
)


DEFAULT_INDEX = REPO_ROOT / "public" / "data" / "municipios_index.json"
DEFAULT_SNAPSHOT = DATA_PIPELINE_DIR / "data" / "municipal_finance" / "source_snapshot.json"
DEFAULT_CONSTITUTIONAL_SNAPSHOT = (
    DATA_PIPELINE_DIR / "data" / "municipal_finance" / "constitutional_source_snapshot.json"
)
DEFAULT_CONSTITUTIONAL_CROSSWALK = (
    DATA_PIPELINE_DIR / "data" / "municipal_finance" / "siope_ibge_crosswalk_v1.json"
)
DEFAULT_RREO_REVISIONS = (
    DATA_PIPELINE_DIR / "data" / "municipal_finance" / "rreo_source_revisions.json"
)
DEFAULT_CHECKPOINT = DATA_PIPELINE_DIR / "export" / "debug" / "municipal_finance_dca_checkpoint.json"
DEFAULT_EXPORT_ROOT = MUNICIPAL_FINANCE_EXPORT_DIR
DEFAULT_PUBLIC_ROOT = REPO_ROOT / "public" / "data"
DEFAULT_COVERAGE_CSV = REPO_ROOT / "docs" / "data" / "diagnostico_financeiro_cobertura_497.csv"
DEFAULT_RECONCILIATION_CSV = REPO_ROOT / "docs" / "data" / "diagnostico_financeiro_reconciliacao_amostra.csv"
DEFAULT_CONSTITUTIONAL_COVERAGE_CSV = (
    REPO_ROOT / "docs" / "data" / "diagnostico_financeiro_constitucional_cobertura.csv"
)
DEFAULT_CONSTITUTIONAL_RECONCILIATION_CSV = (
    REPO_ROOT / "docs" / "data" / "diagnostico_financeiro_constitucional_reconciliacao.csv"
)
DEFAULT_CONSTITUTIONAL_REVISIONS_CSV = (
    REPO_ROOT / "docs" / "data" / "diagnostico_financeiro_retificacoes.csv"
)


def tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*.json")):
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def verify_determinism(municipalities: list[dict[str, str]], snapshot: dict) -> dict[str, str]:
    with tempfile.TemporaryDirectory(prefix="p5b1-a-") as first_dir, tempfile.TemporaryDirectory(prefix="p5b1-b-") as second_dir:
        first_root = Path(first_dir)
        second_root = Path(second_dir)
        generate_contracts(municipalities, snapshot, [first_root])
        generate_contracts(municipalities, snapshot, [second_root])
        first_hash = tree_hash(first_root)
        second_hash = tree_hash(second_root)
        if first_hash != second_hash:
            raise AssertionError("A geração financeira não é determinística.")
        return {"firstHash": first_hash, "secondHash": second_hash}


def measure_local_loading(root: Path, municipalities: list[dict[str, str]]) -> float:
    started = time.perf_counter()
    for municipality in municipalities:
        path = root / "municipios" / municipality["ibgeCode"] / "financeiro.json"
        json.loads(path.read_text(encoding="utf-8"))
    return round((time.perf_counter() - started) * 1000, 3)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gera os contratos financeiros municipais P5-B1.")
    parser.add_argument("--municipality-index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--source-snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument("--constitutional-snapshot", type=Path, default=DEFAULT_CONSTITUTIONAL_SNAPSHOT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_EXPORT_ROOT)
    parser.add_argument("--refresh-sources", action="store_true")
    parser.add_argument("--refresh-constitutional", action="store_true")
    parser.add_argument("--annual-reference-year", type=int, default=2025)
    parser.add_argument("--rreo-workers", type=int, default=8)
    parser.add_argument("--dca-delay", type=float, default=1.05)
    parser.add_argument("--dca-workers", type=int, default=1)
    parser.add_argument("--sync-public", action="store_true")
    parser.add_argument("--write-reports", action="store_true")
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--check-determinism", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    municipalities = load_municipality_registry(args.municipality_index)

    if args.refresh_sources:
        snapshot = refresh_source_snapshot(
            municipalities,
            snapshot_path=args.source_snapshot,
            checkpoint_path=DEFAULT_CHECKPOINT,
            annual_reference_year=args.annual_reference_year,
            dca_delay_seconds=args.dca_delay,
            dca_workers=args.dca_workers,
        )
    else:
        snapshot = load_source_snapshot(args.source_snapshot)

    if args.refresh_constitutional:
        constitutional_snapshot = refresh_annual_constitutional_snapshot(
            municipalities,
            registry_path=args.municipality_index,
            snapshot_path=args.constitutional_snapshot,
            crosswalk_path=DEFAULT_CONSTITUTIONAL_CROSSWALK,
            revision_history_path=DEFAULT_RREO_REVISIONS,
            reference_year=args.annual_reference_year,
            rreo_workers=args.rreo_workers,
        )
    else:
        constitutional_snapshot = load_constitutional_snapshot(args.constitutional_snapshot)
    snapshot = merge_constitutional_snapshot(snapshot, constitutional_snapshot)

    output_roots = [args.output_root]
    if args.sync_public and args.output_root.resolve() != DEFAULT_PUBLIC_ROOT.resolve():
        output_roots.append(DEFAULT_PUBLIC_ROOT)

    generation_started = time.perf_counter()
    result = generate_contracts(municipalities, snapshot, output_roots)
    generation_seconds = round(time.perf_counter() - generation_started, 3)

    if args.write_reports:
        write_coverage_csv(DEFAULT_COVERAGE_CSV, result["coverageRows"])
        write_reconciliation_sample_csv(DEFAULT_RECONCILIATION_CSV, result["contracts"])
        write_constitutional_reports(
            coverage_path=DEFAULT_CONSTITUTIONAL_COVERAGE_CSV,
            reconciliation_path=DEFAULT_CONSTITUTIONAL_RECONCILIATION_CSV,
            revisions_csv_path=DEFAULT_CONSTITUTIONAL_REVISIONS_CSV,
            revision_history_path=DEFAULT_RREO_REVISIONS,
            contracts=result["contracts"],
        )

    validation = None
    if args.validate:
        validation_root = DEFAULT_PUBLIC_ROOT if args.sync_public else args.output_root
        validation = validate_generated_contracts(
            validation_root,
            municipalities,
            municipal_index_root=args.municipality_index.parent,
        )

    determinism = None
    if args.check_determinism:
        determinism = verify_determinism(municipalities, snapshot)

    load_root = DEFAULT_PUBLIC_ROOT if args.sync_public else args.output_root
    local_load_ms = measure_local_loading(load_root, municipalities)
    print(
        json.dumps(
            {
                "dataVersion": DATA_VERSION,
                "generationSeconds": generation_seconds,
                "localLoadAllContractsMs": local_load_ms,
                "writeStats": result["stats"],
                "validation": validation,
                "determinism": determinism,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
