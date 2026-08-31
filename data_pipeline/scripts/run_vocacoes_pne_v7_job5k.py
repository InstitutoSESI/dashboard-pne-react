"""Compila, valida ou finaliza o checkpoint interno do Job 5K."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_PIPELINE_DIR = REPO_ROOT / "data_pipeline"
if str(DATA_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_PIPELINE_DIR))

from src.vocacoes_pne_job2 import (  # noqa: E402
    assert_outside_public_data,
    directory_content_digest,
    replace_directory_transactionally,
    staging_directory_for,
)
from src.vocacoes_pne_job5k import (  # noqa: E402
    DEFAULT_OUTPUT_ROOT,
    FINAL_STATE,
    FRONTEND_BUNDLE,
    JOB5GCR_ROOT,
    JOB5I_ROOT,
    JOB5J_ROOT,
    PENDING_STATE,
    PUBLIC_DATA_ROOT,
    VALIDATION_EVIDENCE_PATH,
    build_bundle,
    frontend_bundle_bytes,
    validate_existing_output,
    verify_frozen_integrity,
    write_package,
)


def _validate_output_path(output: Path) -> None:
    resolved = output.resolve()
    allowed = (REPO_ROOT / ".tmp" / "vocacoes-pne").resolve()
    if resolved == allowed or allowed not in resolved.parents:
        raise ValueError(f"saída Job 5K deve ficar abaixo de {allowed}")
    if resolved in {JOB5I_ROOT.resolve(), JOB5J_ROOT.resolve()}:
        raise ValueError("saída Job 5K não pode substituir raiz congelada")
    assert_outside_public_data(resolved, REPO_ROOT)


def _new_stage(output: Path) -> Path:
    stage = staging_directory_for(output)
    if stage.exists():
        shutil.rmtree(stage)
    return stage


def _promote_frontend(content: bytes) -> tuple[str, Path | None]:
    FRONTEND_BUNDLE.parent.mkdir(parents=True, exist_ok=True)
    if FRONTEND_BUNDLE.is_file() and FRONTEND_BUNDLE.read_bytes() == content:
        return "unchanged", None
    temporary = FRONTEND_BUNDLE.with_name(f".{FRONTEND_BUNDLE.name}.job5k-staging")
    backup = FRONTEND_BUNDLE.with_name(f".{FRONTEND_BUNDLE.name}.job5k-backup") if FRONTEND_BUNDLE.exists() else None
    temporary.write_bytes(content)
    if backup is not None:
        if backup.exists():
            backup.unlink()
        FRONTEND_BUNDLE.replace(backup)
    temporary.replace(FRONTEND_BUNDLE)
    return "replaced", backup


def _finish_frontend_promotion(backup: Path | None) -> None:
    if backup is not None and backup.exists():
        backup.unlink()


def _rollback_frontend(backup: Path | None) -> None:
    if FRONTEND_BUNDLE.exists():
        FRONTEND_BUNDLE.unlink()
    if backup is not None and backup.exists():
        backup.replace(FRONTEND_BUNDLE)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--finalize", action="store_true")
    parser.add_argument("--validation-evidence", type=Path, default=VALIDATION_EVIDENCE_PATH)
    args = parser.parse_args()
    output = args.output if args.output.is_absolute() else REPO_ROOT / args.output
    _validate_output_path(output)
    if args.validate_only:
        manifest = validate_existing_output(output, allow_draft_screenshots=True)
        print(json.dumps({"status": "valid", "state": manifest["generationState"], "counts": manifest["counts"]}, ensure_ascii=False, sort_keys=True))
        return 0

    preflight = verify_frozen_integrity()
    public_before = preflight["digests"]["publicDataTreeDigestSha256"]
    frozen_before = {
        "job5gcr": preflight["digests"]["job5gcrTreeDigestSha256"],
        "job5i": preflight["digests"]["job5iTreeDigestSha256"],
        "job5j": preflight["digests"]["job5jTreeDigestSha256"],
    }
    bundle = build_bundle(preflight)
    frontend = frontend_bundle_bytes(bundle)
    if args.check:
        if not FRONTEND_BUNDLE.is_file() or FRONTEND_BUNDLE.read_bytes() != frontend:
            raise RuntimeError("bundle frontend Job 5K divergente")
        manifest = validate_existing_output(output, allow_draft_screenshots=True)
        print(json.dumps({"status": "current", "state": manifest["generationState"]}, ensure_ascii=False, sort_keys=True))
        return 0

    evidence = None
    if args.finalize:
        evidence_path = args.validation_evidence if args.validation_evidence.is_absolute() else REPO_ROOT / args.validation_evidence
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        validate_existing_output(
            output,
            allow_draft_screenshots=True,
        )
    first = _new_stage(output)
    second = _new_stage(output)
    try:
        write_package(
            output_dir=first,
            bundle=bundle,
            finalized=args.finalize,
            screenshot_source_root=output if args.finalize else None,
            validation_evidence=evidence,
        )
        write_package(
            output_dir=second,
            bundle=bundle,
            finalized=args.finalize,
            screenshot_source_root=output if args.finalize else None,
            validation_evidence=evidence,
        )
        if directory_content_digest(first) != directory_content_digest(second):
            raise RuntimeError("geração Job 5K não determinística")
        shutil.rmtree(second)
        frontend_status, backup = _promote_frontend(frontend)
        try:
            promotion = replace_directory_transactionally(first, output)
        except Exception:
            _rollback_frontend(backup)
            raise
        _finish_frontend_promotion(backup)
    finally:
        if first.exists():
            shutil.rmtree(first)
        if second.exists():
            shutil.rmtree(second)
    manifest = validate_existing_output(output, require_screenshots=args.finalize)
    public_after = directory_content_digest(PUBLIC_DATA_ROOT)
    frozen_after = {
        "job5gcr": directory_content_digest(JOB5GCR_ROOT),
        "job5i": directory_content_digest(JOB5I_ROOT),
        "job5j": directory_content_digest(JOB5J_ROOT),
    }
    if public_after != public_before:
        raise RuntimeError("public/data mudou durante o Job 5K")
    if frozen_after != frozen_before:
        raise RuntimeError("Job 5G-C-R, Job 5I ou Job 5J mudou durante o Job 5K")
    print(
        json.dumps(
            {
                "status": "ok",
                "output": str(output),
                "promotion": promotion,
                "frontendPromotion": frontend_status,
                "generationState": manifest["generationState"],
                "finalState": manifest["finalState"],
                "counts": manifest["counts"],
                "publicDataDigest": public_after,
                "frozenIntegrity": frozen_after,
                "networkUsed": False,
                "databaseUsed": False,
                "publicationPerformed": False,
                "gate11": "CLOSED",
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    if args.finalize and manifest["finalState"] != FINAL_STATE:
        raise RuntimeError("estado final Job 5K divergente")
    if not args.finalize and manifest["generationState"] != PENDING_STATE:
        raise RuntimeError("estado preliminar Job 5K divergente")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
