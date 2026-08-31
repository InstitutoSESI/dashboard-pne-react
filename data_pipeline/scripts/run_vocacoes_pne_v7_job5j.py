"""Executa o laboratório Job 5J em staging local, determinístico e transacional."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys
from typing import Any


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
from src.vocacoes_pne_job5j import (  # noqa: E402
    CONTRACT_PATH,
    DEFAULT_OUTPUT_ROOT,
    FINAL_STATE,
    SOURCE_ROOTS,
    _source_inventory,
    validate_existing_output,
    write_package,
)


PUBLIC_DATA_ROOT = REPO_ROOT / "public" / "data"


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_contract() -> dict[str, Any]:
    contract = _json(CONTRACT_PATH)
    if contract["terminalState"] != FINAL_STATE:
        raise ValueError("Estado terminal divergente no contrato Job 5J")
    if len(contract["packageFiles"]) != 12:
        raise ValueError("Contrato Job 5J deve declarar exatamente 12 arquivos curados")
    if contract["gate11"] != "CLOSED" or not contract["internalOnly"]:
        raise ValueError("Contrato Job 5J abriu escopo proibido")
    return contract


def _validate_output_path(output: Path) -> None:
    resolved = output.resolve()
    allowed_root = (REPO_ROOT / ".tmp" / "vocacoes-pne").resolve()
    if resolved == allowed_root or allowed_root not in resolved.parents:
        raise ValueError(f"Saída deve estar abaixo de {allowed_root}: {resolved}")
    if any(
        resolved == root.resolve() or root.resolve() in resolved.parents
        for root in SOURCE_ROOTS.values()
    ):
        raise ValueError("Saída Job 5J não pode ficar dentro de raiz congelada")
    assert_outside_public_data(resolved, REPO_ROOT)


def _frozen_integrity() -> dict[str, str]:
    missing = [str(path) for path in SOURCE_ROOTS.values() if not path.is_dir()]
    if missing:
        raise FileNotFoundError(f"Raízes congeladas ausentes: {missing}")
    return {
        key: directory_content_digest(path)
        for key, path in sorted(SOURCE_ROOTS.items())
    }


def _new_empty_stage(output: Path) -> Path:
    stage = staging_directory_for(output)
    resolved = stage.resolve()
    allowed_root = (REPO_ROOT / ".tmp" / "vocacoes-pne").resolve()
    if allowed_root not in resolved.parents:
        raise ValueError("Staging fora da raiz local autorizada")
    shutil.rmtree(stage)
    return stage


def _remove_stage(stage: Path) -> None:
    if not stage.exists():
        return
    resolved = stage.resolve()
    allowed_root = (REPO_ROOT / ".tmp" / "vocacoes-pne").resolve()
    if (
        allowed_root not in resolved.parents
        or not stage.name.startswith(".v7-job5j.stage-")
    ):
        raise ValueError(f"Recusa de remoção de staging inesperado: {resolved}")
    shutil.rmtree(stage)


def _generate_twice(
    *,
    output: Path,
    inventory: dict[str, Any],
    frozen_integrity: dict[str, str],
    public_data_digest: str,
) -> tuple[Path, str]:
    first = _new_empty_stage(output)
    second = _new_empty_stage(output)
    try:
        write_package(
            output_dir=first,
            inventory=inventory,
            frozen_integrity=frozen_integrity,
            public_data_digest=public_data_digest,
        )
        validate_existing_output(first)
        first_digest = directory_content_digest(first)
        write_package(
            output_dir=second,
            inventory=inventory,
            frozen_integrity=frozen_integrity,
            public_data_digest=public_data_digest,
        )
        validate_existing_output(second)
        second_digest = directory_content_digest(second)
        if first_digest != second_digest:
            raise ValueError(
                f"Job 5J não determinístico: first={first_digest}, second={second_digest}"
            )
        _remove_stage(second)
        return first, first_digest
    except Exception:
        _remove_stage(first)
        _remove_stage(second)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
        help="Raiz local transacional do Job 5J.",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Valida o pacote existente sem materializar.",
    )
    args = parser.parse_args()
    output = args.output if args.output.is_absolute() else REPO_ROOT / args.output
    _validate_output_path(output)
    _validate_contract()
    if args.validate_only:
        manifest = validate_existing_output(output)
        print(
            json.dumps(
                {
                    "status": "valid",
                    "output": str(output),
                    "finalState": manifest["finalState"],
                    "counts": manifest["counts"],
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 0

    inventory = _source_inventory()
    frozen_before = _frozen_integrity()
    public_before = directory_content_digest(PUBLIC_DATA_ROOT)
    stage, deterministic_digest = _generate_twice(
        output=output,
        inventory=inventory,
        frozen_integrity=frozen_before,
        public_data_digest=public_before,
    )
    promotion = replace_directory_transactionally(stage, output)
    manifest = validate_existing_output(output)
    frozen_after = _frozen_integrity()
    public_after = directory_content_digest(PUBLIC_DATA_ROOT)
    if frozen_after != frozen_before:
        raise RuntimeError("Uma raiz congelada mudou durante o Job 5J")
    if public_after != public_before:
        raise RuntimeError("public/data mudou durante o Job 5J")
    if manifest["finalState"] != FINAL_STATE:
        raise RuntimeError("Estado terminal inesperado")
    print(
        json.dumps(
            {
                "status": "ok",
                "output": str(output),
                "promotion": promotion,
                "deterministicDigest": deterministic_digest,
                "publicDataDigest": public_after,
                "frozenIntegrity": frozen_after,
                "finalState": manifest["finalState"],
                "counts": manifest["counts"],
                "networkUsed": False,
                "databaseUsed": False,
                "fullBuildUsed": False,
                "publicDataChanged": False,
                "frontendChanged": False,
                "publicationPerformed": False,
                "gate11": "CLOSED",
                "job5KStarted": False,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
