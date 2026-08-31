"""Executa o Job 5G-C em staging, valida e promove o diretório atomicamente."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
from typing import Any, Iterator, Mapping

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, URL


REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_PIPELINE_DIR = REPO_ROOT / "data_pipeline"
if str(DATA_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_PIPELINE_DIR))

from src.vocacoes_pne_job2 import (  # noqa: E402
    assert_outside_public_data,
    directory_content_digest,
    sha256_file,
    staging_directory_for,
)
from src.vocacoes_pne_job5gc import write_package  # noqa: E402


DEFAULT_OUTPUT = REPO_ROOT / ".tmp" / "vocacoes-pne" / "v7-job5gc"
CONTRACT_PATH = DATA_PIPELINE_DIR / "contracts" / "vocacoes-pne-v7-job5gc.json"
REGION_PATH = REPO_ROOT / "config" / "regions" / "rs.json"
REGISTRY_PATH = REPO_ROOT / "config" / "municipalities" / "rs.json"
HISTORICAL_DIRS = (
    "v7-job2", "v7-job3", "v7-job5a", "v7-job5b", "v7-job5d",
    "v7-job5f", "v7-job5ga", "v7-job5gar", "v7-job5gb", "v7-job5gbr",
)
EXPECTED_HISTORICAL_DIGEST = "090a56f2dee66520e87a72aec36067d9394799c913f70455a70a3073dd5c6b49"


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _inputs() -> dict[str, Path]:
    root = REPO_ROOT / ".tmp" / "vocacoes-pne" / "v7-job2"
    return {
        "rais_youth_cube": root / "2b" / "rais_cubo_jovem.csv.gz",
        "rais_youth_annual": root / "2b" / "rais_estoque_jovem_anual.csv.gz",
        "caged_youth_cube": root / "2b" / "caged_jovens_cubo.csv.gz",
        "caged_youth_monthly": root / "2b" / "caged_jovens_mensal.csv.gz",
        "rais_occupations": root / "2d" / "ocupacoes_rais.csv.gz",
        "ept_offer": root / "2d" / "oferta_cursos_tecnicos.csv.gz",
        "ept_coverage": root / "2d" / "cobertura_oferta_municipal.csv.gz",
        "course_cbo_bridge": root / "2d" / "cursos_cbo_2025.csv.gz",
        "bridge_coverage": root / "2d" / "cobertura_ponte_2025.csv.gz",
        "bridge_contract": DATA_PIPELINE_DIR / "contracts" / "vocacoes-pne-course-cbo-rs-v1-projection.json",
        "trajectory": REPO_ROOT / ".tmp" / "vocacoes-pne" / "v7-job5gar" / "PAINEL_TRAJETORIA_OFICIAL_DESCRITIVA_V1_1.csv.gz",
        "job5f_manifest": REPO_ROOT / ".tmp" / "vocacoes-pne" / "v7-job5f" / "manifest.json",
        "job5gar_manifest": REPO_ROOT / ".tmp" / "vocacoes-pne" / "v7-job5gar" / "MANIFEST_JOB5GAR.json",
        "job5gbr_manifest": REPO_ROOT / ".tmp" / "vocacoes-pne" / "v7-job5gbr" / "MANIFEST_JOB5GBR.json",
    }


def _load_municipalities() -> dict[str, str]:
    region_payload = _json(REGION_PATH)
    region = next(item for item in region_payload["regions"] if item["slug"] == "vale-do-sinos")
    codes = region["municipalityIbgeCodes"]
    if region["municipalityCount"] != 10 or len(codes) != 10:
        raise ValueError("O Vale do Sinos não contém os dez municípios contratados.")
    registry = _json(REGISTRY_PATH)
    names = {
        item["ibgeCode"]: item["name"]
        for item in registry["municipalities"]
        if item["ibgeCode"] in codes
    }
    if set(names) != set(codes) or names.get("4313375") != "Nova Santa Rita":
        raise ValueError("O registro municipal canônico divergiu do recorte contratado.")
    return names


def _verify_inputs(inputs: Mapping[str, Path], contract: Mapping[str, Any]) -> None:
    missing = [str(path) for path in inputs.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Entradas congeladas ausentes: {missing}")
    for relative, expected in contract["checkpoints"].items():
        path = REPO_ROOT / relative
        actual = sha256_file(path)
        if actual != expected:
            raise ValueError(f"Checkpoint divergente em {relative}: {actual} != {expected}")


def _historical_digest() -> dict[str, Any]:
    base = REPO_ROOT / ".tmp" / "vocacoes-pne"
    rows: list[tuple[str, int, str]] = []
    by_directory: dict[str, dict[str, int]] = {}
    for name in HISTORICAL_DIRS:
        directory = base / name
        files = sorted(path for path in directory.rglob("*") if path.is_file())
        by_directory[name] = {
            "fileCount": len(files),
            "byteSize": sum(path.stat().st_size for path in files),
        }
        for path in files:
            relative = path.relative_to(REPO_ROOT).as_posix()
            rows.append((relative, path.stat().st_size, sha256_file(path)))
    lines = [f"{path}\t{size}\t{digest}" for path, size, digest in sorted(rows)]
    digest = hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()
    return {
        "sha256": digest,
        "expectedSha256": EXPECTED_HISTORICAL_DIGEST,
        "fileCount": len(rows),
        "byteSize": sum(row[1] for row in rows),
        "directories": by_directory,
    }


def _database_url() -> URL:
    missing = [key for key in ("DB_USUARIO", "DB_SENHA", "DB_HOST") if not os.getenv(key)]
    if missing:
        raise RuntimeError(f"Variáveis locais ausentes: {', '.join(missing)}")
    return URL.create(
        "postgresql+psycopg2",
        username=os.environ["DB_USUARIO"],
        password=os.environ["DB_SENHA"],
        host=os.environ["DB_HOST"],
        port=int(os.getenv("DB_PORT", "5432")),
        database="cei",
    )


@contextmanager
def _read_only_connection() -> Iterator[Connection]:
    engine = create_engine(
        _database_url(),
        connect_args={"options": "-c default_transaction_read_only=on -c statement_timeout=180000"},
    )
    try:
        with engine.connect() as connection:
            transaction = connection.begin()
            try:
                connection.execute(text("SET TRANSACTION READ ONLY"))
                mode = connection.execute(text("SELECT current_setting('transaction_read_only')")).scalar_one()
                if mode != "on":
                    raise RuntimeError("A conexão CEI não está em modo somente leitura.")
                yield connection
            finally:
                transaction.rollback()
    finally:
        engine.dispose()


def _state_sector_totals() -> pd.DataFrame:
    query = text(
        """
        WITH source_rows AS (
            SELECT ano AS year,
                   LEFT(LPAD(CAST(cnae_2_subclasse AS text), 7, '0'), 2) AS cnae_division_code,
                   vinculos_ativos AS active_bonds
            FROM public.rais_vinculos_ocupacao
            WHERE ano = 2019
            UNION ALL
            SELECT ano AS year,
                   LEFT(LPAD(CAST(cnae_2_subclasse AS text), 7, '0'), 2) AS cnae_division_code,
                   vinculos_ativos AS active_bonds
            FROM public.rais_ocupacoes_rs_25
            WHERE ano = 2025
        )
        SELECT year, cnae_division_code, SUM(active_bonds)::bigint AS active_bonds
        FROM source_rows
        GROUP BY year, cnae_division_code
        ORDER BY year, cnae_division_code
        """
    )
    with _read_only_connection() as connection:
        frame = pd.read_sql_query(query, connection)
    if set(frame["year"].astype(int)) != {2019, 2025}:
        raise ValueError("O agregado estadual não contém os dois anos congelados.")
    return frame


def _promote(stage: Path, target: Path) -> str:
    if target.exists() and directory_content_digest(stage) == directory_content_digest(target):
        shutil.rmtree(stage)
        return "unchanged"
    backup = target.parent / f".{target.name}.job5gc-backup"
    if backup.exists():
        raise FileExistsError(f"Backup residual exige inspeção: {backup}")
    moved_old = False
    try:
        if target.exists():
            os.replace(target, backup)
            moved_old = True
        os.replace(stage, target)
        if moved_old:
            shutil.rmtree(backup)
        return "replaced"
    except Exception:
        if target.exists() and target != stage:
            shutil.rmtree(target)
        if moved_old and backup.exists():
            os.replace(backup, target)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output = args.output.resolve()
    assert_outside_public_data(output, REPO_ROOT)
    allowed_root = (REPO_ROOT / ".tmp" / "vocacoes-pne").resolve()
    if allowed_root not in output.parents:
        raise ValueError("A saída do Job 5G-C deve permanecer em .tmp/vocacoes-pne.")
    load_dotenv(DATA_PIPELINE_DIR / ".env")
    contract = _json(CONTRACT_PATH)
    inputs = _inputs()
    _verify_inputs(inputs, contract)
    before = _historical_digest()
    if before["sha256"] != EXPECTED_HISTORICAL_DIGEST:
        raise ValueError(f"O conjunto histórico congelado divergiu: {before['sha256']}")
    names = _load_municipalities()
    state_totals = _state_sector_totals()
    stage = staging_directory_for(output)
    # write_package requer diretório inexistente; o helper cria um diretório vazio.
    stage.rmdir()
    try:
        manifest = write_package(
            output_dir=stage,
            inputs=inputs,
            state_sector_totals=state_totals,
            municipality_names=names,
            contract=contract,
            historical_checkpoint={"before": before, "afterExpected": before},
        )
        after_generation = _historical_digest()
        if after_generation != before:
            raise ValueError("Algum artefato histórico congelado foi alterado durante o Job 5G-C.")
        promotion = _promote(stage, output)
    except Exception:
        if stage.exists():
            shutil.rmtree(stage)
        raise
    print(
        json.dumps(
            {
                "finalState": manifest["finalState"],
                "output": str(output),
                "promotion": promotion,
                "outputCount": manifest["summary"]["outputCount"],
                "historicalSha256": before["sha256"],
                "databaseAggregateSha256": manifest["databaseAggregate"]["sha256"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
