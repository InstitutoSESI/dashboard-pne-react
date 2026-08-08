#!/usr/bin/env python3
"""Adquire, valida e materializa a cobertura educacional rural estimada.

Por padrão, cria e promove somente o snapshot auditável local. ``--apply``
também substitui as tabelas intermediárias do banco em uma única transação.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import bindparam, text


DATA_PIPELINE_DIR = Path(__file__).resolve().parents[1]
if str(DATA_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_PIPELINE_DIR))

from src.config import CENSO_ESCOLAR_SOURCE_DIR, SESI_DB_DIR  # noqa: E402
from src.municipality_registry import load_municipality_registry  # noqa: E402
from src.rural_education_snapshot import (  # noqa: E402
    RAW_FILENAMES,
    resolve_rural_education_snapshot_dir,
    snapshot_digest,
)
from src.rural_population_sidra import extract_to_directory  # noqa: E402
from src.rural_school_enrollment import (  # noqa: E402
    SUPPORTED_YEARS,
    aggregate_rural_enrollment_years,
)
from src.state_config import DEFAULT_STATE_CODE, StateConfig, load_state_config  # noqa: E402

sys.path.insert(0, str(SESI_DB_DIR))
from utils_educacao import get_engine  # noqa: E402


POPULATION_TABLE = "populacao_rural_estimada_4_17_municipal"
ENROLLMENT_TABLE = "matriculas_rurais_faixa_etaria_municipal"


def _json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def _load_reused_raw(output_dir: Path) -> dict[str, bytes]:
    missing = [filename for filename in RAW_FILENAMES if not (output_dir / filename).is_file()]
    if missing:
        raise FileNotFoundError(
            f"--reuse-raw exige snapshot anterior completo; ausentes: {missing}."
        )
    return {filename: (output_dir / filename).read_bytes() for filename in RAW_FILENAMES}


def _stage_snapshot(
    staging: Path,
    *,
    state_config: StateConfig,
    output_dir: Path,
    municipality_codes: set[str],
    years: tuple[int, ...],
    source_dir: Path,
    reuse_raw: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    raw = _load_reused_raw(output_dir) if reuse_raw else {}
    population_rows, population_manifest = extract_to_directory(
        staging,
        state_config=state_config,
        municipality_codes=municipality_codes,
        rural_metadata_content=raw.get("sidra_10089_metadata.json"),
        rural_data_content=raw.get("sidra_10089_response.json"),
        exact_metadata_content=raw.get("sidra_9606_metadata.json"),
        exact_data_content=raw.get("sidra_9606_response.json"),
    )
    enrollment_rows, enrollment_audits = aggregate_rural_enrollment_years(
        source_dir,
        years=years,
        state_code=state_config.state_code,
        municipality_codes=municipality_codes,
    )
    (staging / "rural_enrollments.json").write_bytes(_json_bytes(enrollment_rows))
    digest = snapshot_digest(staging)
    manifest = {
        "schemaVersion": 1,
        "generatedAt": population_manifest["generatedAt"],
        "state": state_config.state_code,
        "municipalityCount": len(municipality_codes),
        "years": list(years),
        "population": {
            "rows": len(population_rows),
            "available": sum(row["status_valor"] == "available" for row in population_rows),
            "sources": population_manifest["sourceMetadata"],
            "method": population_manifest["method"],
        },
        "enrollments": {
            "rows": len(enrollment_rows),
            "audits": enrollment_audits,
        },
        "snapshotSha256": digest,
    }
    (staging / "manifest.json").write_bytes(_json_bytes(manifest))
    return population_rows, enrollment_rows, manifest


def _promote_snapshot(staging: Path, output_dir: Path, manifest: dict[str, Any]) -> str:
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    if output_dir.is_dir():
        previous_manifest_path = output_dir / "manifest.json"
        if previous_manifest_path.is_file():
            previous_manifest = json.loads(previous_manifest_path.read_text(encoding="utf-8"))
            if previous_manifest.get("snapshotSha256") == manifest["snapshotSha256"]:
                shutil.rmtree(staging)
                return "unchanged"

    rollback = output_dir.parent / f".{output_dir.name}.rollback"
    if rollback.exists():
        raise FileExistsError(f"Rollback pendente impede promoção: {rollback}.")
    had_previous = output_dir.exists()
    if had_previous:
        os.replace(output_dir, rollback)
    try:
        os.replace(staging, output_dir)
    except Exception:
        if had_previous and rollback.exists() and not output_dir.exists():
            os.replace(rollback, output_dir)
        raise

    if had_previous and rollback.exists():
        previous_manifest_path = rollback / "manifest.json"
        previous_hash = "unknown"
        if previous_manifest_path.is_file():
            previous_hash = str(
                json.loads(previous_manifest_path.read_text(encoding="utf-8")).get(
                    "snapshotSha256", "unknown"
                )
            )
        history = output_dir.parent / f".{output_dir.name}.previous" / previous_hash
        history.parent.mkdir(parents=True, exist_ok=True)
        if history.exists():
            shutil.rmtree(rollback)
        else:
            os.replace(rollback, history)
    return "promoted"


def _database_frames(
    population_rows: list[dict[str, Any]], enrollment_rows: list[dict[str, Any]]
) -> tuple[pd.DataFrame, pd.DataFrame]:
    population = pd.DataFrame(population_rows).copy()
    enrollment = pd.DataFrame(enrollment_rows).copy()
    for frame in (population, enrollment):
        frame["metadados_fonte"] = frame["metadados_fonte"].map(
            lambda value: json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        )
    return population, enrollment


def replace_tables(
    population_rows: list[dict[str, Any]],
    enrollment_rows: list[dict[str, Any]],
    *,
    years: tuple[int, ...],
    municipality_codes: set[str],
) -> None:
    """Substitui ambos os retratos e valida contagens antes do commit."""

    population, enrollment = _database_frames(population_rows, enrollment_rows)
    municipality_ids = tuple(sorted(municipality_codes))
    engine = get_engine("sesi")
    with engine.begin() as connection:
        connection.execute(
            text(
                f"""
                CREATE TABLE IF NOT EXISTS {POPULATION_TABLE} (
                    ano_censo INTEGER NOT NULL,
                    id_municipio VARCHAR(7) NOT NULL,
                    populacao_rural_estimada_4_17 DOUBLE PRECISION NULL,
                    status_valor TEXT NOT NULL,
                    motivo_indisponibilidade TEXT NULL,
                    populacao_rural_0_4 INTEGER NULL,
                    populacao_rural_5_9 INTEGER NULL,
                    populacao_rural_10_14 INTEGER NULL,
                    populacao_rural_15_19 INTEGER NULL,
                    peso_idade_4_no_grupo_0_4 DOUBLE PRECISION NULL,
                    peso_idades_15_17_no_grupo_15_19 DOUBLE PRECISION NULL,
                    metodo_estimacao TEXT NOT NULL,
                    metadados_fonte TEXT NOT NULL,
                    PRIMARY KEY (ano_censo, id_municipio)
                )
                """
            )
        )
        connection.execute(
            text(
                f"""
                CREATE TABLE IF NOT EXISTS {ENROLLMENT_TABLE} (
                    ano INTEGER NOT NULL,
                    id_municipio VARCHAR(7) NOT NULL,
                    faixa_etaria TEXT NOT NULL,
                    matriculas INTEGER NOT NULL,
                    status_valor TEXT NOT NULL,
                    origem_valor TEXT NOT NULL,
                    metadados_fonte TEXT NOT NULL,
                    PRIMARY KEY (ano, id_municipio, faixa_etaria)
                )
                """
            )
        )
        population_delete = text(
            f"DELETE FROM {POPULATION_TABLE} "
            "WHERE ano_censo = 2022 AND id_municipio IN :municipality_ids"
        ).bindparams(bindparam("municipality_ids", expanding=True))
        connection.execute(
            population_delete,
            {"municipality_ids": municipality_ids},
        )
        enrollment_delete = text(
            f"DELETE FROM {ENROLLMENT_TABLE} "
            "WHERE ano = ANY(:years) AND id_municipio IN :municipality_ids"
        ).bindparams(bindparam("municipality_ids", expanding=True))
        connection.execute(
            enrollment_delete,
            {"years": list(years), "municipality_ids": municipality_ids},
        )
        population.to_sql(
            POPULATION_TABLE,
            connection,
            if_exists="append",
            index=False,
            method="multi",
            chunksize=1000,
        )
        enrollment.to_sql(
            ENROLLMENT_TABLE,
            connection,
            if_exists="append",
            index=False,
            method="multi",
            chunksize=1000,
        )
        population_count = connection.execute(
            text(
                f"SELECT count(*) FROM {POPULATION_TABLE} "
                "WHERE ano_censo = 2022 AND id_municipio IN :municipality_ids"
            ).bindparams(bindparam("municipality_ids", expanding=True)),
            {"municipality_ids": municipality_ids},
        ).scalar_one()
        enrollment_count = connection.execute(
            text(
                f"SELECT count(*) FROM {ENROLLMENT_TABLE} "
                "WHERE ano = ANY(:years) AND id_municipio IN :municipality_ids"
            ).bindparams(bindparam("municipality_ids", expanding=True)),
            {"years": list(years), "municipality_ids": municipality_ids},
        ).scalar_one()
        if population_count != len(population_rows) or enrollment_count != len(enrollment_rows):
            raise ValueError(
                "Validação pós-escrita falhou: "
                f"população={population_count}/{len(population_rows)}, "
                f"matrículas={enrollment_count}/{len(enrollment_rows)}."
            )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--state",
        default=DEFAULT_STATE_CODE,
        help=f"Código estadual configurado (padrão: {DEFAULT_STATE_CODE}).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Diretório estadual explícito; por padrão usa data/rural_education_coverage/<uf>.",
    )
    parser.add_argument("--source-dir", type=Path, default=CENSO_ESCOLAR_SOURCE_DIR)
    parser.add_argument("--years", nargs="+", type=int, default=list(SUPPORTED_YEARS))
    parser.add_argument(
        "--reuse-raw",
        action="store_true",
        help="Reusa as quatro respostas SIDRA do snapshot atual, sem rede.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help=f"Substitui {POPULATION_TABLE} e {ENROLLMENT_TABLE} no banco.",
    )
    args = parser.parse_args()

    years = tuple(sorted(set(args.years)))
    unsupported = sorted(set(years) - set(SUPPORTED_YEARS))
    if unsupported:
        raise ValueError(f"Anos não suportados: {unsupported}.")
    state_config = load_state_config(args.state)
    registry = load_municipality_registry(state_config)
    municipality_codes = set(registry.ids)
    output_dir = (
        args.output_dir
        if args.output_dir is not None
        else resolve_rural_education_snapshot_dir(state_config)
    ).resolve()
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=f".{output_dir.name}.staging-", dir=output_dir.parent)
    )
    try:
        population_rows, enrollment_rows, manifest = _stage_snapshot(
            staging,
            state_config=state_config,
            output_dir=output_dir,
            municipality_codes=municipality_codes,
            years=years,
            source_dir=args.source_dir.resolve(),
            reuse_raw=args.reuse_raw,
        )
        promotion = _promote_snapshot(staging, output_dir, manifest)
        if args.apply:
            replace_tables(
                population_rows,
                enrollment_rows,
                years=years,
                municipality_codes=municipality_codes,
            )
        result = {
            **manifest,
            "outputDirectory": str(output_dir),
            "promotion": promotion,
            "databaseWrite": "applied" if args.apply else "validated_only",
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    finally:
        if staging.exists():
            shutil.rmtree(staging)


if __name__ == "__main__":
    raise SystemExit(main())
