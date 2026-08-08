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
from src.state_config import load_state_config  # noqa: E402

sys.path.insert(0, str(SESI_DB_DIR))
from utils_educacao import get_engine  # noqa: E402


LONG_TABLE = "populacao_indigena_idade_municipal"
GROUP_TABLE = "populacao_indigena_faixa_municipal"


def canonical_municipality_codes(state_config) -> set[str]:
    engine = get_engine("sesi")
    frame = pd.read_sql_query(
        "SELECT id_municipio FROM municipios "
        "WHERE sigla_uf = %(state)s ORDER BY id_municipio",
        engine,
        params={"state": state_config.state_code},
    )
    codes = set(frame["id_municipio"].astype(str))
    if len(codes) != state_config.expected_municipality_count or any(
        len(code) != 7 or not code.startswith(state_config.municipality_ibge_prefix)
        for code in codes
    ):
        raise ValueError(
            f"Cadastro municipal canônico inválido: {len(codes)} códigos do RS."
        )
    return codes


def replace_tables(rows: list[dict], age_groups: list[dict], state_code: str) -> None:
    engine = get_engine("sesi")
    long_frame = pd.DataFrame(rows).copy()
    long_frame["metadados_fonte"] = long_frame["metadados_fonte"].map(
        lambda value: json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    )
    group_frame = pd.DataFrame(age_groups)
    long_frame["sigla_uf"] = state_code
    group_frame["sigla_uf"] = state_code
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
                    sigla_uf VARCHAR(2),
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
                    sigla_uf VARCHAR(2),
                    PRIMARY KEY (ano_censo, id_municipio, faixa_etaria)
                )
                """
            )
        )
        for table in (LONG_TABLE, GROUP_TABLE):
            connection.execute(
                text(
                    f"ALTER TABLE {table} "
                    "ADD COLUMN IF NOT EXISTS sigla_uf VARCHAR(2)"
                )
            )
            connection.execute(
                text(f"UPDATE {table} SET sigla_uf = 'RS' WHERE sigla_uf IS NULL")
            )
        connection.execute(
            text(
                f"DELETE FROM {LONG_TABLE} "
                "WHERE sigla_uf = :state AND ano_censo = :year"
            ),
            {"state": state_code, "year": CENSUS_YEAR},
        )
        connection.execute(
            text(
                f"DELETE FROM {GROUP_TABLE} "
                "WHERE sigla_uf = :state AND ano_censo = :year"
            ),
            {"state": state_code, "year": CENSUS_YEAR},
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
    parser.add_argument("--state", default="RS", help="UF da carga (RS ou AL).")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Diretório do cache bruto, normalizado e do manifesto.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help=f"Substitui o Censo 2022 nas tabelas {LONG_TABLE} e {GROUP_TABLE}.",
    )
    args = parser.parse_args()

    state_config = load_state_config(args.state)
    base_output_dir = DATA_PIPELINE_DIR / "data" / "indigenous_population_sidra"
    output_dir = args.output_dir or (
        base_output_dir
        if state_config.state_code == "RS"
        else base_output_dir / state_config.state_code.lower()
    )
    municipality_codes = canonical_municipality_codes(state_config)
    rows, age_groups, manifest = extract_to_directory(
        output_dir.resolve(),
        municipality_codes=municipality_codes,
        state_code=state_config.state_code,
        state_id=state_config.municipality_ibge_prefix,
    )
    if args.apply:
        replace_tables(rows, age_groups, state_config.state_code)
        manifest["databaseWrite"] = "applied"
    else:
        manifest["databaseWrite"] = "validated_only"
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
