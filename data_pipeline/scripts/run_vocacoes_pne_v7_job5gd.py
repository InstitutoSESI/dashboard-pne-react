"""Materializa o Job 5G-D em staging local, transacional e determinístico."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import shutil
import sys
from typing import Any, Iterator, Mapping

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import bindparam, create_engine, text
from sqlalchemy.engine import Connection, URL


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
from src.vocacoes_pne_job5gd import (  # noqa: E402
    FINAL_STATE,
    IBGE_CODE_PATTERN,
    validate_existing_output,
    write_package,
)


DEFAULT_OUTPUT = REPO_ROOT / ".tmp" / "vocacoes-pne" / "v7-job5gd"
CONTRACT_PATH = DATA_PIPELINE_DIR / "contracts" / "vocacoes-pne-v7-job5gd.json"
REGION_PATH = REPO_ROOT / "config" / "regions" / "rs.json"
REGISTRY_PATH = REPO_ROOT / "config" / "municipalities" / "rs.json"
JOB2_ROOT = REPO_ROOT / ".tmp" / "vocacoes-pne" / "v7-job2"
GAR_ROOT = REPO_ROOT / ".tmp" / "vocacoes-pne" / "v7-job5gar"
GBR_ROOT = REPO_ROOT / ".tmp" / "vocacoes-pne" / "v7-job5gbr"
GCR_ROOT = REPO_ROOT / ".tmp" / "vocacoes-pne" / "v7-job5gcr"
MOBILITY_SOURCE_ROOT = (
    DATA_PIPELINE_DIR / "data" / "vocacoes_pne_v7_job5gd" / "mobility_sidra"
)
FINANCE_ROOT = DATA_PIPELINE_DIR / "export" / "municipal_finance" / "municipios"


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _inputs() -> dict[str, Path]:
    return {
        "job5gd_contract": CONTRACT_PATH,
        "job5gd_generator": DATA_PIPELINE_DIR / "src" / "vocacoes_pne_job5gd.py",
        "job5gd_runner": Path(__file__).resolve(),
        "job5gd_acquisition": DATA_PIPELINE_DIR
        / "scripts"
        / "acquire_vocacoes_pne_v7_job5gd_mobility.py",
        "job2_manifest": JOB2_ROOT / "manifest.json",
        "job5gar_manifest": GAR_ROOT / "MANIFEST_JOB5GAR.json",
        "job5gbr_manifest": GBR_ROOT / "MANIFEST_JOB5GBR.json",
        "job5gcr_manifest": GCR_ROOT / "MANIFEST_JOB5GCR.json",
        "mobility_source_manifest": MOBILITY_SOURCE_ROOT
        / "MANIFEST_SOURCE_MOBILITY_SIDRA_JOB5GD.json",
        "finance_source_snapshot": DATA_PIPELINE_DIR
        / "data"
        / "municipal_finance"
        / "source_snapshot.json",
        "finance_constitutional_source_snapshot": DATA_PIPELINE_DIR
        / "data"
        / "municipal_finance"
        / "constitutional_source_snapshot.json",
        "region_config": REGION_PATH,
        "municipality_registry": REGISTRY_PATH,
    }


def _load_municipalities() -> dict[str, str]:
    region_payload = _json(REGION_PATH)
    region = next(
        item for item in region_payload["regions"] if item["slug"] == "vale-do-sinos"
    )
    codes = [str(code) for code in region["municipalityIbgeCodes"]]
    if region["municipalityCount"] != 10 or len(codes) != 10 or len(set(codes)) != 10:
        raise ValueError("O Vale do Sinos não contém os dez municípios únicos contratados")
    if any(not IBGE_CODE_PATTERN.fullmatch(code) for code in codes):
        raise ValueError("Código municipal inválido no recorte canônico")
    registry = _json(REGISTRY_PATH)
    registry_names = {
        str(item["ibgeCode"]): str(item["name"])
        for item in registry["municipalities"]
        if str(item["ibgeCode"]) in set(codes)
    }
    if set(registry_names) != set(codes):
        raise ValueError("Registro municipal não cobre exatamente o recorte")
    if registry_names.get("4313375") != "Nova Santa Rita":
        raise ValueError("Nova Santa Rita divergiu do registro canônico")
    return {code: registry_names[code] for code in codes}


def _verify_inputs(inputs: Mapping[str, Path]) -> None:
    missing = [path.as_posix() for path in inputs.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Entradas locais ausentes: {missing}")


def _verify_checkpoints(contract: Mapping[str, Any]) -> None:
    for relative, expected in contract["checkpoints"].items():
        path = REPO_ROOT / relative
        if not path.is_file():
            raise FileNotFoundError(f"Checkpoint ausente: {relative}")
        observed = sha256_file(path)
        if observed != expected:
            raise ValueError(f"Checkpoint divergiu: {relative}: {observed} != {expected}")


def _frozen_integrity() -> dict[str, str]:
    return {
        "job2": directory_content_digest(JOB2_ROOT),
        "job5gar": directory_content_digest(GAR_ROOT),
        "job5gbr": directory_content_digest(GBR_ROOT),
        "job5gcr": directory_content_digest(GCR_ROOT),
    }


def _database_url() -> URL:
    required = ("DB_USUARIO", "DB_SENHA", "DB_HOST", "DB_BANCO")
    missing = [key for key in required if not os.getenv(key)]
    if missing:
        raise RuntimeError(f"Variáveis locais ausentes: {', '.join(missing)}")
    return URL.create(
        "postgresql+psycopg2",
        username=os.environ["DB_USUARIO"],
        password=os.environ["DB_SENHA"],
        host=os.environ["DB_HOST"],
        port=int(os.getenv("DB_PORT", "5432")),
        database=os.environ["DB_BANCO"],
    )


@contextmanager
def _read_only_connection() -> Iterator[Connection]:
    engine = create_engine(
        _database_url(),
        connect_args={
            "options": "-c default_transaction_read_only=on -c statement_timeout=180000"
        },
    )
    try:
        with engine.connect() as connection:
            transaction = connection.begin()
            try:
                connection.execute(text("SET TRANSACTION READ ONLY"))
                mode = connection.execute(
                    text("SELECT current_setting('transaction_read_only')")
                ).scalar_one()
                if mode != "on":
                    raise RuntimeError("A conexão PNATE não está em modo somente leitura")
                yield connection
            finally:
                transaction.rollback()
    finally:
        engine.dispose()


def _load_pnate(municipality_names: Mapping[str, str]) -> pd.DataFrame:
    query = text(
        """
        SELECT CAST(id_municipio AS text) AS id_municipio,
               municipio,
               ano,
               uf,
               regiao,
               total_alunos_rede_municipal,
               total_alunos_rede_estadual,
               total_alunos,
               repasse_total,
               saldo_ano_anterior,
               desconto,
               repasse_autorizado_apos_desconto,
               previsao_repasse_ajustado,
               fonte,
               arquivo_origem,
               aba_origem,
               data_carga
        FROM public.fnde_pnate_municipio_dashboard
        WHERE CAST(id_municipio AS text) IN :municipality_codes
          AND ano IN (2024, 2025, 2026)
        ORDER BY CAST(id_municipio AS text), ano
        """
    ).bindparams(bindparam("municipality_codes", expanding=True))
    with _read_only_connection() as connection:
        frame = pd.read_sql_query(
            query,
            connection,
            params={"municipality_codes": tuple(municipality_names)},
        )
    frame["id_municipio"] = frame["id_municipio"].astype("string")
    if len(frame) != 30 or frame.duplicated(["id_municipio", "ano"]).any():
        raise ValueError("Extração PNATE não possui 30 grãos município × exercício")
    if set(frame["id_municipio"].astype(str)) != set(municipality_names):
        raise ValueError("Extração PNATE não cobre exatamente os dez códigos")
    return frame.sort_values(["id_municipio", "ano"], kind="mergesort").reset_index(drop=True)


def _validate_output_path(output: Path) -> None:
    assert_outside_public_data(output, REPO_ROOT)
    allowed_root = (REPO_ROOT / ".tmp" / "vocacoes-pne").resolve()
    resolved = output.resolve()
    if resolved == allowed_root or allowed_root not in resolved.parents:
        raise ValueError("A saída 5G-D deve ser subdiretório de .tmp/vocacoes-pne")
    frozen_roots = {root.resolve() for root in (JOB2_ROOT, GAR_ROOT, GBR_ROOT, GCR_ROOT)}
    if resolved in frozen_roots:
        raise ValueError("A saída 5G-D não pode substituir pacote congelado")


def _new_empty_stage(output: Path) -> Path:
    stage = staging_directory_for(output)
    stage.rmdir()
    return stage


def _remove_stage(stage: Path) -> None:
    resolved = stage.resolve()
    allowed_root = (REPO_ROOT / ".tmp" / "vocacoes-pne").resolve()
    if allowed_root not in resolved.parents or not resolved.name.startswith(".v7-job5gd"):
        raise ValueError(f"Recusa de remover staging fora do escopo: {resolved}")
    if resolved.exists():
        shutil.rmtree(resolved)


def _generate(
    *,
    output: Path,
    contract: Mapping[str, Any],
    inputs: Mapping[str, Path],
    municipality_names: Mapping[str, str],
    selected_municipality_id: str,
    pnate_source: pd.DataFrame,
    frozen_integrity: Mapping[str, str],
) -> dict[str, Any]:
    stages = [_new_empty_stage(output), _new_empty_stage(output)]
    manifests = []
    validations = []
    try:
        for stage in stages:
            manifests.append(
                write_package(
                    output_dir=stage,
                    contract=contract,
                    inputs=inputs,
                    job2_root=JOB2_ROOT,
                    gar_root=GAR_ROOT,
                    gbr_root=GBR_ROOT,
                    gcr_root=GCR_ROOT,
                    mobility_source_root=MOBILITY_SOURCE_ROOT,
                    finance_root=FINANCE_ROOT,
                    pnate_source=pnate_source,
                    municipality_names=municipality_names,
                    selected_municipality_id=selected_municipality_id,
                    frozen_integrity=frozen_integrity,
                )
            )
            validations.append(validate_existing_output(stage))
        first_digest = directory_content_digest(stages[0])
        second_digest = directory_content_digest(stages[1])
        if first_digest != second_digest:
            raise ValueError(
                f"Materialização não determinística: {first_digest} != {second_digest}"
            )
        _remove_stage(stages[1])
        activation = replace_directory_transactionally(stages[0], output)
        final_validation = validate_existing_output(output)
        return {
            "manifest": manifests[0],
            "validation": final_validation,
            "replicateValidations": validations,
            "determinismSha256": first_digest,
            "stagingActivation": activation,
        }
    except Exception:
        for stage in stages:
            if stage.exists():
                _remove_stage(stage)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--selected-municipality", default="4313375")
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()

    output = args.output.resolve()
    _validate_output_path(output)
    contract = _json(CONTRACT_PATH)
    inputs = _inputs()
    _verify_inputs(inputs)
    _verify_checkpoints(contract)
    municipality_names = _load_municipalities()
    selected = str(args.selected_municipality)
    if not IBGE_CODE_PATTERN.fullmatch(selected) or selected not in municipality_names:
        raise ValueError("Município selecionado deve ser código IBGE textual do Vale")
    frozen_before = _frozen_integrity()

    if args.validate_only:
        validation = validate_existing_output(output)
        if _frozen_integrity() != frozen_before:
            raise ValueError("Pacote congelado mudou durante validate-only")
        print(
            json.dumps(
                {
                    **validation,
                    "output": str(output),
                    "frozenInputIntegrity": frozen_before,
                    "validationOnly": True,
                    "networkUsed": False,
                    "databaseUsed": False,
                    "publicDataChanged": False,
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 0

    load_dotenv(DATA_PIPELINE_DIR / ".env")
    pnate_source = _load_pnate(municipality_names)
    result = _generate(
        output=output,
        contract=contract,
        inputs=inputs,
        municipality_names=municipality_names,
        selected_municipality_id=selected,
        pnate_source=pnate_source,
        frozen_integrity=frozen_before,
    )
    _verify_checkpoints(contract)
    frozen_after = _frozen_integrity()
    if frozen_after != frozen_before:
        raise ValueError("Pacote congelado mudou durante o Job 5G-D")
    manifest = result["manifest"]
    print(
        json.dumps(
            {
                "finalState": FINAL_STATE,
                "output": str(output),
                "outputCount": manifest["summary"]["outputCount"],
                "artifactHashCount": manifest["summary"]["artifactHashCount"],
                "manifestSha256": result["validation"]["manifestSha256"],
                "determinismSha256": result["determinismSha256"],
                "stagingActivation": result["stagingActivation"],
                "selectedMunicipalityId": selected,
                "databaseMode": "read_only_transaction",
                "databaseWrites": False,
                "networkUsed": False,
                "publicDataChanged": False,
                "frontendChanged": False,
                "publicationPerformed": False,
                "gate11": "CLOSED",
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
