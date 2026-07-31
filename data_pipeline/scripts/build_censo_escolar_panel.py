#!/usr/bin/env python3
"""Gera, audita e promove o painel municipal anual do Censo Escolar."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
import uuid
from pathlib import Path


DATA_PIPELINE_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = DATA_PIPELINE_DIR.parent
if str(DATA_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_PIPELINE_DIR))

from src.censo_escolar_panel import (  # noqa: E402
    CANONICAL_PANEL_NAME,
    DEFAULT_CHUNK_SIZE,
    FIRST_YEAR,
    GENERATOR_VERSION,
    HISTORICAL_FIRST_YEAR,
    HISTORICAL_LAST_YEAR,
    LAST_YEAR,
    build_panel,
    load_historical_csv,
    load_historical_from_postgres,
    load_sync_provenance,
    portable_manifest_path,
    reconcile,
    render_audit_report,
    sha256_file,
    validate_manifest,
    write_json,
)
from src.config import CENSO_ESCOLAR_SOURCE_DIR  # noqa: E402


DEFAULT_OUTPUT_DIR = DATA_PIPELINE_DIR / "data" / "censo_escolar_panel"
DEFAULT_REPORT_DIR = DATA_PIPELINE_DIR / "export" / "censo_escolar_panel"
DEFAULT_PANEL_NAME = CANONICAL_PANEL_NAME
RECONCILIATION_FILE_NAMES = (
    "reconciliation_summary.csv",
    "reconciliation_divergences.csv",
    "reconciliation_examples.json",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, default=CENSO_ESCOLAR_SOURCE_DIR)
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Destino do painel e manifesto; obrigatório para execução parcial.",
    )
    parser.add_argument(
        "--report-dir",
        type=Path,
        help="Destino dos relatórios regeneráveis; por padrão fica em data_pipeline/export.",
    )
    parser.add_argument("--panel-name", help="Nome explícito para o CSV.gz parcial.")
    parser.add_argument("--chunksize", type=int, default=DEFAULT_CHUNK_SIZE)
    parser.add_argument("--historical-csv", type=Path)
    parser.add_argument("--skip-reconciliation", action="store_true")
    parser.add_argument(
        "--years",
        nargs="+",
        type=int,
        default=list(range(FIRST_YEAR, LAST_YEAR + 1)),
    )
    return parser.parse_args()


def selected_years(values: list[int]) -> list[int]:
    years = sorted(set(int(value) for value in values))
    if not years:
        raise ValueError("Informe ao menos um ano.")
    outside = [year for year in years if year < FIRST_YEAR or year > LAST_YEAR]
    if outside:
        raise ValueError(f"Anos fora do intervalo {FIRST_YEAR}–{LAST_YEAR}: {outside}")
    return years


def resolve_artifact_paths(
    years: list[int],
    output_dir: Path | None,
    report_dir: Path | None,
    panel_name: str | None,
) -> tuple[Path, Path, str]:
    """Resolve destinations and prevent a subset from targeting the canonical panel."""

    years = selected_years(years)
    complete = years == list(range(FIRST_YEAR, LAST_YEAR + 1))
    if not complete and output_dir is None:
        raise ValueError(
            "Execução parcial exige --output-dir explícito; o painel canônico não será usado."
        )

    resolved_output = (output_dir or DEFAULT_OUTPUT_DIR).resolve()
    if not complete and resolved_output == DEFAULT_OUTPUT_DIR.resolve():
        raise ValueError(
            "Execução parcial não pode usar data_pipeline/data/censo_escolar_panel."
        )

    if complete:
        resolved_name = panel_name or DEFAULT_PANEL_NAME
    else:
        resolved_name = panel_name or (
            f"censo_escolar_municipal_{years[0]}_{years[-1]}.csv.gz"
        )
    if resolved_name == DEFAULT_PANEL_NAME and not complete:
        raise ValueError(
            f"{DEFAULT_PANEL_NAME} só é permitido com os 19 anos completos."
        )
    if not resolved_name.endswith(".csv.gz"):
        raise ValueError("O nome do painel deve terminar em .csv.gz.")

    if report_dir is not None:
        resolved_report = report_dir.resolve()
    elif complete and resolved_output == DEFAULT_OUTPUT_DIR.resolve():
        resolved_report = DEFAULT_REPORT_DIR.resolve()
    else:
        resolved_report = resolved_output.parent / f"{resolved_output.name}_reports"
    resolved_report = resolved_report.resolve()
    if resolved_report == resolved_output:
        raise ValueError("Painel e relatórios precisam de destinos distintos.")
    return resolved_output, resolved_report, resolved_name


def _remove_path(path: Path) -> None:
    """Remove one generated path during rollback/cleanup."""

    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    elif path.exists() or path.is_symlink():
        path.unlink()


def promote_artifact_set(
    staged_panel_dir: Path,
    destination_panel_dir: Path,
    staged_report_dir: Path,
    destination_report_dir: Path,
) -> None:
    """Promote both output directories with rollback if either rename fails."""

    staged_panel_dir = staged_panel_dir.resolve()
    destination_panel_dir = destination_panel_dir.resolve()
    staged_report_dir = staged_report_dir.resolve()
    destination_report_dir = destination_report_dir.resolve()
    if destination_panel_dir == destination_report_dir:
        raise ValueError("Destinos de painel e relatório não podem coincidir.")
    if not staged_panel_dir.is_dir() or not staged_report_dir.is_dir():
        raise ValueError("Staging incompleto: diretório de painel ou relatório ausente.")

    token = uuid.uuid4().hex
    backups: dict[Path, Path] = {}
    promoted: list[Path] = []
    destinations = [
        (destination_panel_dir, staged_panel_dir),
        (destination_report_dir, staged_report_dir),
    ]
    try:
        for destination, _staged in destinations:
            destination.parent.mkdir(parents=True, exist_ok=True)
            if destination.exists() or destination.is_symlink():
                backup = destination.parent / f".{destination.name}.rollback-{token}"
                destination.rename(backup)
                backups[destination] = backup
        for destination, staged in destinations:
            staged.rename(destination)
            promoted.append(destination)
    except Exception:
        for destination in reversed(promoted):
            if destination.exists() or destination.is_symlink():
                _remove_path(destination)
        for destination, backup in backups.items():
            if backup.exists() or backup.is_symlink():
                backup.rename(destination)
        raise
    else:
        for backup in backups.values():
            if backup.exists() or backup.is_symlink():
                _remove_path(backup)


def _render_skipped_report(path: Path, generated_at: str) -> None:
    content = "\n".join(
        [
            "# Auditoria do painel municipal do Censo Escolar",
            "",
            f"Gerado em `{generated_at}`; reconciliação não executada (`--skip-reconciliation`).",
            "",
            "Os relatórios de reconciliação da versão anterior foram removidos da promoção desta execução.",
            "A ausência de `reconciliation_summary.csv`, `reconciliation_divergences.csv` e `reconciliation_examples.json` é intencional.",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _relative_report_paths(report_dir: Path) -> dict[str, str]:
    return {
        "directory": portable_manifest_path(report_dir, REPO_ROOT),
        "audit_report": portable_manifest_path(report_dir / "audit_report.md", REPO_ROOT),
        "reconciliation_summary": portable_manifest_path(
            report_dir / "reconciliation_summary.csv", REPO_ROOT
        ),
        "reconciliation_divergences": portable_manifest_path(
            report_dir / "reconciliation_divergences.csv", REPO_ROOT
        ),
        "reconciliation_examples": portable_manifest_path(
            report_dir / "reconciliation_examples.json", REPO_ROOT
        ),
    }


def _run(args: argparse.Namespace) -> dict:
    years = selected_years(args.years)
    output_dir, report_dir, panel_name = resolve_artifact_paths(
        years, args.output_dir, args.report_dir, args.panel_name
    )
    if args.chunksize <= 0:
        raise ValueError("chunksize deve ser positivo")
    if args.historical_csv and args.skip_reconciliation:
        raise ValueError("--historical-csv não pode ser usado com --skip-reconciliation.")

    stage_parent = output_dir.parent
    stage_parent.mkdir(parents=True, exist_ok=True)
    stage_root = Path(
        tempfile.mkdtemp(prefix=".censo-escolar-panel-", dir=str(stage_parent))
    )
    staged_panel_dir = stage_root / "panel"
    staged_report_dir = stage_root / "reports"
    staged_panel_path = staged_panel_dir / panel_name
    staged_manifest_path = staged_panel_dir / "manifest.json"
    try:
        panel, metadata = build_panel(
            args.source_dir,
            staged_panel_path,
            years=years,
            chunk_size=args.chunksize,
        )
        metadata["panel"]["path"] = portable_manifest_path(
            output_dir / panel_name, REPO_ROOT
        )
        metadata["manifest_path"] = portable_manifest_path(
            output_dir / "manifest.json", REPO_ROOT
        )
        metadata["provenance"] = load_sync_provenance(REPO_ROOT, metadata["sources"])
        metadata["reports"] = _relative_report_paths(report_dir)

        if args.skip_reconciliation:
            metadata["historical_source"] = None
            metadata["reconciliation"] = {
                "status": "skipped",
                "strict_contract": False,
                "reason": "--skip-reconciliation",
                "reports_current": False,
            }
            staged_report_dir.mkdir(parents=True, exist_ok=True)
            _render_skipped_report(
                staged_report_dir / "audit_report.md", metadata["generated_at_utc"]
            )
            write_json(
                staged_report_dir / "reconciliation_status.json",
                {
                    "status": "skipped",
                    "reason": "--skip-reconciliation",
                    "generated_at_utc": metadata["generated_at_utc"],
                    "reports_current": False,
                },
            )
            metadata["reports"] = {
                "directory": portable_manifest_path(report_dir, REPO_ROOT),
                "audit_report": portable_manifest_path(
                    report_dir / "audit_report.md", REPO_ROOT
                ),
                "reconciliation_status": portable_manifest_path(
                    report_dir / "reconciliation_status.json", REPO_ROOT
                ),
                "reconciliation_files": [],
            }
        else:
            if years != list(range(FIRST_YEAR, LAST_YEAR + 1)):
                raise ValueError(
                    "A reconciliação oficial 2014–2025 exige o painel completo; use --skip-reconciliation em execução parcial."
                )
            if args.historical_csv:
                history, historical_metadata = load_historical_csv(
                    args.historical_csv.resolve()
                )
            else:
                history, historical_metadata = load_historical_from_postgres(
                    DATA_PIPELINE_DIR / ".env",
                    start_year=HISTORICAL_FIRST_YEAR,
                    end_year=HISTORICAL_LAST_YEAR,
                )
            reconciliation = reconcile(
                panel,
                history,
                staged_report_dir,
                source_metadata=metadata["sources"],
                historical_metadata=historical_metadata,
            )
            metadata["historical_source"] = historical_metadata
            metadata["reconciliation"] = {
                key: value for key, value in reconciliation.items() if key != "summary"
            }
            metadata["reconciliation"].update(
                {
                    "summary_path": metadata["reports"]["reconciliation_summary"],
                    "divergences_path": metadata["reports"]["reconciliation_divergences"],
                    "examples_path": metadata["reports"]["reconciliation_examples"],
                }
            )
            render_audit_report(
                staged_report_dir / "audit_report.md",
                metadata,
                reconciliation,
                historical_metadata,
            )

        metadata["reports"]["files"] = sorted(
            portable_manifest_path(report_dir / path.name, REPO_ROOT)
            for path in staged_report_dir.iterdir()
            if path.is_file()
        )
        validate_manifest(metadata, panel_path=staged_panel_path)
        write_json(staged_manifest_path, metadata)
        written_manifest = json.loads(staged_manifest_path.read_text(encoding="utf-8"))
        validate_manifest(written_manifest, panel_path=staged_panel_path)
        promote_artifact_set(
            staged_panel_dir,
            output_dir,
            staged_report_dir,
            report_dir,
        )
        return {
            "generator_version": GENERATOR_VERSION,
            "panel": metadata["panel"],
            "reconciliation": metadata["reconciliation"],
            "manifest": metadata["manifest_path"],
            "reports": metadata["reports"],
        }
    finally:
        if stage_root.exists():
            shutil.rmtree(stage_root, ignore_errors=True)


def main() -> int:
    args = parse_args()
    try:
        result = _run(args)
    except Exception as error:  # pragma: no cover - exercised by CLI failures
        print(
            json.dumps(
                {
                    "generator_version": GENERATOR_VERSION,
                    "status": "failed",
                    "error": str(error),
                },
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 1
    print(json.dumps(result, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
