"""Materializa o Job 5H em staging local, transacional e determinístico."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys
from typing import Any, Mapping


REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_PIPELINE_DIR = REPO_ROOT / "data_pipeline"
if str(DATA_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_PIPELINE_DIR))

from src.vocacoes_pne_job2 import (  # noqa: E402
    assert_outside_public_data,
    directory_content_digest,
    replace_directory_transactionally,
    sha256_file,
    staging_directory_for,
)
from src.vocacoes_pne_job5h import (  # noqa: E402
    FINAL_STATE,
    IBGE_CODE_PATTERN,
    validate_existing_output,
    write_package,
)


DEFAULT_OUTPUT = REPO_ROOT / ".tmp" / "vocacoes-pne" / "v7-job5h"
CONTRACT_PATH = DATA_PIPELINE_DIR / "contracts" / "vocacoes-pne-v7-job5h.json"
REGION_PATH = REPO_ROOT / "config" / "regions" / "rs.json"
REGISTRY_PATH = REPO_ROOT / "config" / "municipalities" / "rs.json"
PNE_CONTRACT_PATH = REPO_ROOT / "contracts" / "pne2026-goal-indicator-contract.json"
FROZEN_ROOTS = {
    "job5gar": REPO_ROOT / ".tmp" / "vocacoes-pne" / "v7-job5gar",
    "job5gbr": REPO_ROOT / ".tmp" / "vocacoes-pne" / "v7-job5gbr",
    "job5gcr": REPO_ROOT / ".tmp" / "vocacoes-pne" / "v7-job5gcr",
    "job5gd": REPO_ROOT / ".tmp" / "vocacoes-pne" / "v7-job5gd",
}


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _inputs() -> dict[str, Path]:
    return {
        "job5h_contract": CONTRACT_PATH,
        "job5h_generator": DATA_PIPELINE_DIR / "src" / "vocacoes_pne_job5h.py",
        "job5h_runner": Path(__file__).resolve(),
        "pne2026_contract": PNE_CONTRACT_PATH,
        "region_config": REGION_PATH,
        "municipality_registry": REGISTRY_PATH,
        "job5gar_manifest": FROZEN_ROOTS["job5gar"] / "MANIFEST_JOB5GAR.json",
        "job5gbr_manifest": FROZEN_ROOTS["job5gbr"] / "MANIFEST_JOB5GBR.json",
        "job5gcr_manifest": FROZEN_ROOTS["job5gcr"] / "MANIFEST_JOB5GCR.json",
        "job5gd_manifest": FROZEN_ROOTS["job5gd"] / "MANIFEST_JOB5GD.json",
        "job5gcr_nsr_fact_catalog_v1": FROZEN_ROOTS["job5gcr"]
        / "MATRIZ_CATALOGO_FATOS_NOVA_SANTA_RITA_JOB5GCR_V1.csv.gz",
    }


def _load_municipalities() -> dict[str, str]:
    region_payload = _json(REGION_PATH)
    region = next(
        item for item in region_payload["regions"] if item["slug"] == "vale-do-sinos"
    )
    codes = [str(code) for code in region["municipalityIbgeCodes"]]
    if region["municipalityCount"] != 10 or len(codes) != 10 or len(set(codes)) != 10:
        raise ValueError("Vale do Sinos não possui exatamente dez códigos canônicos")
    if any(not IBGE_CODE_PATTERN.fullmatch(code) for code in codes):
        raise ValueError("Código IBGE municipal inválido na configuração regional")
    registry = _json(REGISTRY_PATH)
    names = {
        str(item["ibgeCode"]): str(item["name"])
        for item in registry["municipalities"]
    }
    missing = sorted(set(codes) - set(names))
    if missing:
        raise ValueError(f"Municípios do Vale ausentes do registro canônico: {missing}")
    return {code: names[code] for code in sorted(codes)}


def _verify_inputs(inputs: Mapping[str, Path]) -> None:
    missing = [str(path) for path in inputs.values() if not path.is_file()]
    missing.extend(
        str(path) for path in FROZEN_ROOTS.values() if not path.is_dir()
    )
    if missing:
        raise FileNotFoundError(f"Entradas obrigatórias ausentes: {missing}")


def _verify_checkpoints(contract: Mapping[str, Any]) -> None:
    failures = []
    for relative, expected_hash in sorted(contract["checkpoints"].items()):
        path = REPO_ROOT / relative
        if not path.is_file():
            failures.append(f"missing:{relative}")
            continue
        observed = sha256_file(path)
        if observed != expected_hash:
            failures.append(
                f"hash:{relative}:expected={expected_hash}:observed={observed}"
            )
    if failures:
        raise ValueError(f"Checkpoints Job 5H divergentes: {failures}")


def _frozen_integrity() -> dict[str, str]:
    return {
        key: directory_content_digest(path)
        for key, path in sorted(FROZEN_ROOTS.items())
    }


def _validate_output_path(output: Path) -> None:
    resolved = output.resolve()
    allowed_root = (REPO_ROOT / ".tmp" / "vocacoes-pne").resolve()
    if resolved == allowed_root or allowed_root not in resolved.parents:
        raise ValueError(
            f"Saída Job 5H deve estar abaixo de {allowed_root}, recebido {resolved}"
        )
    if any(
        resolved == frozen.resolve() or frozen.resolve() in resolved.parents
        for frozen in FROZEN_ROOTS.values()
    ):
        raise ValueError("Saída Job 5H não pode ficar dentro de pacote congelado")
    assert_outside_public_data(resolved, REPO_ROOT)


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
    if allowed_root not in resolved.parents or not stage.name.startswith(".v7-job5h.stage-"):
        raise ValueError(f"Recusa de remoção de staging inesperado: {resolved}")
    shutil.rmtree(stage)


def _generate(
    *,
    output: Path,
    contract: Mapping[str, Any],
    inputs: Mapping[str, Path],
    municipality_names: Mapping[str, str],
    frozen_integrity: Mapping[str, str],
) -> tuple[Path, str]:
    first = _new_empty_stage(output)
    second = _new_empty_stage(output)
    try:
        write_package(
            output_dir=first,
            repo_root=REPO_ROOT,
            contract=contract,
            inputs=inputs,
            municipality_names=municipality_names,
            frozen_integrity=frozen_integrity,
            frozen_roots=FROZEN_ROOTS,
        )
        validate_existing_output(first)
        first_digest = directory_content_digest(first)
        write_package(
            output_dir=second,
            repo_root=REPO_ROOT,
            contract=contract,
            inputs=inputs,
            municipality_names=municipality_names,
            frozen_integrity=frozen_integrity,
            frozen_roots=FROZEN_ROOTS,
        )
        validate_existing_output(second)
        second_digest = directory_content_digest(second)
        if first_digest != second_digest:
            raise ValueError(
                f"Job 5H não determinístico: first={first_digest}, second={second_digest}"
            )
        _remove_stage(second)
        second = Path()
        return first, first_digest
    except Exception:
        _remove_stage(first)
        if second != Path():
            _remove_stage(second)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Raiz local transacional do Job 5H.",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Valida o pacote existente sem materializar.",
    )
    args = parser.parse_args()
    output = args.output if args.output.is_absolute() else REPO_ROOT / args.output
    _validate_output_path(output)
    if args.validate_only:
        manifest = validate_existing_output(output)
        print(
            json.dumps(
                {
                    "status": "valid",
                    "output": str(output),
                    "finalState": manifest["finalState"],
                    "summary": manifest["summary"],
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 0

    contract = _json(CONTRACT_PATH)
    inputs = _inputs()
    _verify_inputs(inputs)
    _verify_checkpoints(contract)
    municipality_names = _load_municipalities()
    frozen_before = _frozen_integrity()
    stage, deterministic_digest = _generate(
        output=output,
        contract=contract,
        inputs=inputs,
        municipality_names=municipality_names,
        frozen_integrity=frozen_before,
    )
    promotion = replace_directory_transactionally(stage, output)
    manifest = validate_existing_output(output)
    frozen_after = _frozen_integrity()
    if frozen_after != frozen_before:
        raise RuntimeError("Pacote congelado mudou depois da promoção Job 5H")
    print(
        json.dumps(
            {
                "status": "ok",
                "promotion": promotion,
                "output": str(output),
                "deterministicDigest": deterministic_digest,
                "finalState": manifest["finalState"],
                "summary": manifest["summary"],
                "networkUsed": False,
                "databaseUsed": False,
                "publicDataChanged": False,
                "frontendChanged": False,
                "fullBuildUsed": False,
                "publicationPerformed": False,
                "gate11": "CLOSED",
                "job5IStarted": False,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    if manifest["finalState"] != FINAL_STATE:
        raise RuntimeError("Estado terminal inesperado")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
