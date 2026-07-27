#!/usr/bin/env python3
"""Baixa e materializa a população indígena municipal do Censo 2022.

A execução é explícita e sempre grava o cache auditável em ``data_pipeline/data``.
Use ``--apply`` para substituir as tabelas intermediárias do banco em uma
transação; o build do frontend nunca executa este comando.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import text

DATA_PIPELINE_DIR = Path(__file__).resolve().parents[1]
if str(DATA_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_PIPELINE_DIR))

from src.config import SESI_DB_DIR  # noqa: E402
from src.indigenous_population_sidra import (  # noqa: E402
    CENSUS_YEAR,
    extract_to_directory,
)

sys.path.insert(0, str(SESI_DB_DIR))
from utils_educacao import get_engine  # noqa: E402


LONG_TABLE = "populacao_indigena_idade_municipal"
GROUP_TABLE = "populacao_indigena_faixa_municipal"


def canonical_municipality_codes() -> set[str]:
    engine = get_engine("sesi")
    frame = pd.read_sql_query(
        "SELECT id_municipio FROM municipios "
        "WHERE sigla_uf = 'RS' ORDER BY id_municipio",
        engine,
    )
    codes = set(frame["id_municipio"].astype(str))
    if len(codes) != 497 or any(len(code) != 7 for code in codes):
        raise ValueError(
            f"Cadastro municipal canônico inválido: {len(codes)} códigos do RS."
        )
    return codes


def replace_tables(rows: list[dict], age_groups: list[dict]) -> None:
    engine = get_engine("sesi")
    long_frame = pd.DataFrame(rows).copy()
    long_frame["metadados_fonte"] = long_frame["metadados_fonte"].map(
        lambda value: json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    )
    group_frame = pd.DataFrame(age_groups)
    with engine.begin() as connection:
        connection.execute(
            text(
                f"""
                CREATE TABLE IF NOT EXISTS {LONG_TABLE} (
                    ano_censo INTEGER NOT NULL,
                    id_municipio VARCHAR(7) NOT NULL,
                    idade INTEGER NOT NULL,
                    pessoas_indigenas INTEGER NULL,
                    status_valor TEXT NOT NULL,
                    valor_original TEXT NOT NULL,
                    tabela_origem TEXT NOT NULL,
                    metadados_fonte TEXT NOT NULL,
                    PRIMARY KEY (ano_censo, id_municipio, idade)
                )
                """
            )
        )
        connection.execute(
            text(
                f"""
                CREATE TABLE IF NOT EXISTS {GROUP_TABLE} (
                    ano_censo INTEGER NOT NULL,
                    id_municipio VARCHAR(7) NOT NULL,
                    faixa_etaria TEXT NOT NULL,
                    idade_de INTEGER NOT NULL,
                    idade_ate INTEGER NOT NULL,
                    rotulo TEXT NOT NULL,
                    pessoas_indigenas INTEGER NULL,
                    status_valor TEXT NOT NULL,
                    tabela_origem TEXT NOT NULL,
                    PRIMARY KEY (ano_censo, id_municipio, faixa_etaria)
                )
                """
            )
        )
        connection.execute(
            text(f"DELETE FROM {LONG_TABLE} WHERE ano_censo = :year"),
            {"year": CENSUS_YEAR},
        )
        connection.execute(
            text(f"DELETE FROM {GROUP_TABLE} WHERE ano_censo = :year"),
            {"year": CENSUS_YEAR},
        )
        long_frame.to_sql(
            LONG_TABLE,
            connection,
            if_exists="append",
            index=False,
            method="multi",
            chunksize=2000,
        )
        group_frame.to_sql(
            GROUP_TABLE,
            connection,
            if_exists="append",
            index=False,
            method="multi",
            chunksize=2000,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DATA_PIPELINE_DIR / "data" / "indigenous_population_sidra",
        help="Diretório do cache bruto, normalizado e do manifesto.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help=f"Substitui o Censo 2022 nas tabelas {LONG_TABLE} e {GROUP_TABLE}.",
    )
    args = parser.parse_args()

    municipality_codes = canonical_municipality_codes()
    rows, age_groups, manifest = extract_to_directory(
        args.output_dir.resolve(),
        municipality_codes=municipality_codes,
    )
    if args.apply:
        replace_tables(rows, age_groups)
        manifest["databaseWrite"] = "applied"
    else:
        manifest["databaseWrite"] = "validated_only"
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
