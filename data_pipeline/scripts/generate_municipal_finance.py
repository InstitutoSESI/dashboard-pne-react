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
    FinanceState,
    generate_contracts,
    load_municipality_registry,
    load_source_snapshot,
    refresh_source_snapshot,
    validate_generated_contracts,
    write_coverage_csv,
    write_reconciliation_sample_csv,
)
from src.municipal_finance_constitutional import (  # noqa: E402
    ConstitutionalState,
    load_constitutional_snapshot,
    merge_constitutional_snapshot,
    refresh_annual_constitutional_snapshot,
    write_constitutional_reports,
)
from src.municipal_finance_icms_education import (  # noqa: E402
    load_icms_education_source,
    merge_icms_education_source,
)
from src.publication_transaction import promote_files_atomically  # noqa: E402
from src.state_config import (  # noqa: E402
    DEFAULT_STATE_CODE,
    load_state_config,
)
from src.state_publication import resolve_public_data_dir  # noqa: E402


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
DEFAULT_ICMS_EDUCATION_SOURCE = (
    DATA_PIPELINE_DIR / "data" / "municipal_finance" / "icms_education" / "rs"
)
DEFAULT_RS_MUNICIPALITY_REGISTRY = REPO_ROOT / "config" / "municipalities" / "rs.json"
DEFAULT_CHECKPOINT = DATA_PIPELINE_DIR / "export" / "debug" / "municipal_finance_dca_checkpoint.json"
DEFAULT_EXPORT_ROOT = MUNICIPAL_FINANCE_EXPORT_DIR
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


def verify_determinism(
    municipalities: list[dict[str, str]],
    snapshot: dict,
    state: FinanceState,
) -> dict[str, str]:
    with tempfile.TemporaryDirectory(prefix="p5b1-a-") as first_dir, tempfile.TemporaryDirectory(prefix="p5b1-b-") as second_dir:
        first_root = Path(first_dir)
        second_root = Path(second_dir)
        generate_contracts(municipalities, snapshot, [first_root], state)
        generate_contracts(municipalities, snapshot, [second_root], state)
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
    parser.add_argument(
        "--state",
        default=DEFAULT_STATE_CODE,
        help=f"Código estadual configurado (padrão: {DEFAULT_STATE_CODE}).",
    )
    parser.add_argument("--municipality-index", type=Path)
    parser.add_argument("--source-snapshot", type=Path)
    parser.add_argument("--constitutional-snapshot", type=Path)
    parser.add_argument("--icms-education-source", type=Path)
    parser.add_argument("--output-root", type=Path)
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
    state_config = load_state_config(args.state)
    finance_state = FinanceState(
        state_config.state_code,
        state_config.municipality_ibge_prefix,
        state_config.expected_municipality_count,
    )
    constitutional_state = ConstitutionalState(
        state_config.state_code,
        state_config.municipality_ibge_prefix,
        state_config.expected_municipality_count,
    )
    public_root = resolve_public_data_dir(state_config.state_code)
    state_suffix = state_config.state_code.casefold()
    municipality_index = args.municipality_index or public_root / "municipios_index.json"
    source_snapshot = args.source_snapshot or (
        DEFAULT_SNAPSHOT
        if state_config.state_code == DEFAULT_STATE_CODE
        else DEFAULT_SNAPSHOT.with_name(f"source_snapshot_{state_suffix}.json")
    )
    constitutional_snapshot_path = args.constitutional_snapshot or (
        DEFAULT_CONSTITUTIONAL_SNAPSHOT
        if state_config.state_code == DEFAULT_STATE_CODE
        else DEFAULT_CONSTITUTIONAL_SNAPSHOT.with_name(
            f"constitutional_source_snapshot_{state_suffix}.json"
        )
    )
    output_root = args.output_root or (
        DEFAULT_EXPORT_ROOT
        if state_config.state_code == DEFAULT_STATE_CODE
        else public_root
    )
    crosswalk_path = (
        DEFAULT_CONSTITUTIONAL_CROSSWALK
        if state_config.state_code == DEFAULT_STATE_CODE
        else DEFAULT_CONSTITUTIONAL_CROSSWALK.with_name(
            f"siope_ibge_crosswalk_{state_suffix}_v1.json"
        )
    )
    revision_history_path = (
        DEFAULT_RREO_REVISIONS
        if state_config.state_code == DEFAULT_STATE_CODE
        else DEFAULT_RREO_REVISIONS.with_name(
            f"rreo_source_revisions_{state_suffix}.json"
        )
    )
    checkpoint_path = (
        DEFAULT_CHECKPOINT
        if state_config.state_code == DEFAULT_STATE_CODE
        else DEFAULT_CHECKPOINT.with_name(
            f"{DEFAULT_CHECKPOINT.stem}_{state_suffix}{DEFAULT_CHECKPOINT.suffix}"
        )
    )
    municipalities = load_municipality_registry(municipality_index, finance_state)

    if args.refresh_sources:
        snapshot = refresh_source_snapshot(
            municipalities,
            snapshot_path=source_snapshot,
            checkpoint_path=checkpoint_path,
            annual_reference_year=args.annual_reference_year,
            dca_delay_seconds=args.dca_delay,
            dca_workers=args.dca_workers,
            state=finance_state,
        )
    else:
        snapshot = load_source_snapshot(source_snapshot, finance_state)

    if args.refresh_constitutional:
        constitutional_snapshot = refresh_annual_constitutional_snapshot(
            municipalities,
            registry_path=municipality_index,
            snapshot_path=constitutional_snapshot_path,
            crosswalk_path=crosswalk_path,
            revision_history_path=revision_history_path,
            reference_year=args.annual_reference_year,
            rreo_workers=args.rreo_workers,
            state=constitutional_state,
        )
    else:
        constitutional_snapshot = load_constitutional_snapshot(
            constitutional_snapshot_path,
            constitutional_state,
        )
    snapshot = merge_constitutional_snapshot(
        snapshot,
        constitutional_snapshot,
        constitutional_state,
    )
    if state_config.state_code == "RS":
        icms_education_source = load_icms_education_source(
            args.icms_education_source or DEFAULT_ICMS_EDUCATION_SOURCE,
            DEFAULT_RS_MUNICIPALITY_REGISTRY,
        )
        snapshot = merge_icms_education_source(
            snapshot,
            icms_education_source,
            municipalities,
        )
    elif args.icms_education_source is not None:
        raise RuntimeError(
            "A fonte configurada de ICMS Educação é exclusiva do Rio Grande do Sul."
        )

    output_roots = [output_root]
    if args.sync_public and output_root.resolve() != public_root.resolve():
        output_roots.append(public_root)

    generation_started = time.perf_counter()
    for root in output_roots:
        root.parent.mkdir(parents=True, exist_ok=True)
    stage_contexts = [
        tempfile.TemporaryDirectory(
            prefix=f".{root.name}-finance-stage-",
            dir=root.parent,
        )
        for root in output_roots
    ]
    stage_roots = [Path(context.name) for context in stage_contexts]
    try:
        result = generate_contracts(
            municipalities,
            snapshot,
            stage_roots,
            finance_state,
        )
        validation = validate_generated_contracts(
            stage_roots[-1],
            municipalities,
            municipal_index_root=municipality_index.parent,
        )
        publication_paths = [
            Path("financeiro") / name
            for name in ("catalogos.json", "cobertura.json", "manifest.json")
        ] + [
            Path("municipios") / municipality["ibgeCode"] / "financeiro.json"
            for municipality in municipalities
        ]
        for stage_root, target_root in zip(stage_roots, output_roots, strict=True):
            promote_files_atomically(stage_root, target_root, publication_paths)
    finally:
        for context in stage_contexts:
            context.cleanup()
    generation_seconds = round(time.perf_counter() - generation_started, 3)

    if args.write_reports:
        write_coverage_csv(DEFAULT_COVERAGE_CSV, result["coverageRows"])
        write_reconciliation_sample_csv(DEFAULT_RECONCILIATION_CSV, result["contracts"])
        write_constitutional_reports(
            coverage_path=DEFAULT_CONSTITUTIONAL_COVERAGE_CSV,
            reconciliation_path=DEFAULT_CONSTITUTIONAL_RECONCILIATION_CSV,
            revisions_csv_path=DEFAULT_CONSTITUTIONAL_REVISIONS_CSV,
            revision_history_path=revision_history_path,
            contracts=result["contracts"],
        )

    if args.validate:
        validation_root = public_root if args.sync_public else output_root
        validation = validate_generated_contracts(
            validation_root,
            municipalities,
            municipal_index_root=municipality_index.parent,
        )

    determinism = None
    if args.check_determinism:
        determinism = verify_determinism(municipalities, snapshot, finance_state)

    load_root = public_root if args.sync_public else output_root
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
