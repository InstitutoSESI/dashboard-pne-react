#!/usr/bin/env python3
"""Audita a viabilidade municipal do critério de acesso ao cargo de diretor."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
import sys

import openpyxl


DATA_PIPELINE_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(DATA_PIPELINE_DIR))

from src.pne_macro_ingestion import (  # noqa: E402
    DATA_ROOT,
    MANIFEST_SCHEMA,
    canonical_json_bytes,
    file_sha256,
    raw_file_entry,
    write_source_snapshot,
)


SOURCE_ID = "inep_censo_escolar_gestor_2025"
SOURCE_PAGE = (
    "https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/"
    "microdados/censo-escolar"
)
OFFICIAL_URL = (
    "https://download.inep.gov.br/dados_abertos/"
    "microdados_censo_escolar_2025_.zip"
)
DESTINATION = DATA_ROOT / "director_selection"
REQUIRED_COLUMNS = {
    "QT_GEST_BAS_DIRETOR",
    "QT_GEST_BAS_ACESSO_CARGO_SEL",
    "QT_GEST_BAS_ACESSO_CARGO_P_SEL",
}


def audit(csv_path: Path, dictionary_path: Path) -> dict:
    with csv_path.open(
        "r",
        encoding="latin1",
        errors="strict",
        newline="",
    ) as source:
        headers = next(csv.reader(source, delimiter=";"))
    available_columns = sorted(REQUIRED_COLUMNS & set(headers))
    missing_columns = sorted(REQUIRED_COLUMNS - set(headers))

    workbook = openpyxl.load_workbook(
        dictionary_path,
        read_only=True,
        data_only=True,
    )
    try:
        manager_sheet = next(
            (sheet for sheet in workbook.worksheets if sheet.title == "Tabela_de_Gestor"),
            None,
        )
        dictionary_variables = []
        if manager_sheet is not None:
            for row in manager_sheet.iter_rows(values_only=True):
                code = str(row[1] or "") if len(row) > 1 else ""
                if code in REQUIRED_COLUMNS or "ACESSO_CARGO" in code:
                    dictionary_variables.append(
                        {
                            "code": code,
                            "description": str(row[2] or "") if len(row) > 2 else "",
                        }
                    )
    finally:
        workbook.close()
    status = "blocked" if missing_columns else "eligible_for_materialization"
    return {
        "schemaVersion": MANIFEST_SCHEMA,
        "sourceId": SOURCE_ID,
        "sourceTitle": "Censo Escolar da Educação Básica — Gestor",
        "organization": "Instituto Nacional de Estudos e Pesquisas Educacionais Anísio Teixeira",
        "edition": "2025",
        "sourcePageUrl": SOURCE_PAGE,
        "rawFiles": [
            {
                "logicalName": "microdadosEdBasica2025",
                "fileName": csv_path.name,
                "officialUrl": OFFICIAL_URL,
                "externalSnapshotPath": str(csv_path.resolve()),
                "size": csv_path.stat().st_size,
                "sha256": file_sha256(csv_path),
            },
            raw_file_entry(
                logical_name="officialDictionary2025",
                path=dictionary_path,
                official_url=OFFICIAL_URL,
            ),
        ],
        "dictionary": {
            "requiredVariables": sorted(REQUIRED_COLUMNS),
            "documentedVariables": dictionary_variables,
        },
        "coverage": {
            "municipalityCount": 0,
            "reason": "Tabela de gestor ausente do CSV público disponível.",
        },
        "audit": {
            "csvColumnCount": len(headers),
            "availableRequiredColumns": available_columns,
            "missingRequiredColumns": missing_columns,
        },
        "status": status,
        "blockedReason": (
            "O dicionário oficial documenta a tabela de gestor, mas o único "
            "CSV do pacote público contém apenas a tabela de escola e não "
            "publica as contagens municipais necessárias. Campo ausente não "
            "foi classificado como não atendimento."
            if missing_columns
            else None
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True, type=Path)
    parser.add_argument("--dictionary", required=True, type=Path)
    args = parser.parse_args()
    manifest = audit(args.csv, args.dictionary)
    write_source_snapshot(
        destination=DESTINATION,
        raw_files={args.dictionary.name: args.dictionary},
        normalized=None,
        manifest=manifest,
    )
    print(canonical_json_bytes(manifest).decode("utf-8"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
