#!/usr/bin/env python3
"""Audita ou adquire os microdados oficiais do Censo Escolar.

Sem ``--download`` o script somente registra os arquivos completos já
extraídos no diretório compartilhado do SESI. O download usa staging, valida o
ZIP e o CSV, preserva a versão anterior e só então promove a nova fonte.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import sys


DATA_PIPELINE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DATA_PIPELINE_DIR))

from src.config import CENSO_ESCOLAR_SOURCE_DIR  # noqa: E402


MANIFEST_PATH = (
    DATA_PIPELINE_DIR / "data" / "censo_escolar_acquisition" / "manifest.json"
)
URL_TEMPLATE = (
    "https://download.inep.gov.br/dados_abertos/"
    "microdados_censo_escolar_{year}.zip"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_csv(year: int) -> Path:
    candidates = [
        path
        for path in CENSO_ESCOLAR_SOURCE_DIR.iterdir()
        if path.is_file()
        and path.name.lower() == f"microdados_ed_basica_{year}.csv"
    ]
    if len(candidates) != 1:
        raise FileNotFoundError(
            f"Esperado um CSV canônico para {year}; encontrados {len(candidates)}."
        )
    return candidates[0]


def validate_csv(path: Path, year: int) -> None:
    if path.stat().st_size < 1_000_000:
        raise ValueError(f"{path.name}: arquivo menor que o esperado.")
    header = path.open("r", encoding="latin1").readline().rstrip("\r\n").split(";")
    required = {
        "NU_ANO_CENSO",
        "CO_ENTIDADE",
        "CO_MUNICIPIO",
        "TP_SITUACAO_FUNCIONAMENTO",
        "TP_DEPENDENCIA",
        "TP_LOCALIZACAO",
        "QT_MAT_ESP",
    }
    missing = sorted(required - set(header))
    if missing:
        raise ValueError(f"{path.name}: colunas obrigatórias ausentes: {missing}")
    if year >= 2025 and "QT_MAT_BAS_LIBRAS" not in header:
        raise ValueError(f"{path.name}: leiaute 2025 sem QT_MAT_BAS_LIBRAS.")


def find_extracted_csv(root: Path, year: int) -> Path:
    matches = [
        path
        for path in root.rglob("*")
        if path.is_file()
        and path.name.lower() == f"microdados_ed_basica_{year}.csv"
    ]
    if len(matches) != 1:
        raise ValueError(
            f"ZIP {year}: esperado um CSV principal; encontrados {len(matches)}."
        )
    return matches[0]


def download_year(year: int) -> Path:
    CENSO_ESCOLAR_SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(
            prefix=f".censo-escolar-{year}-",
            dir=CENSO_ESCOLAR_SOURCE_DIR,
        )
    )
    try:
        archive = staging / f"microdados_censo_escolar_{year}.zip"
        request = urllib.request.Request(
            URL_TEMPLATE.format(year=year),
            headers={"User-Agent": "dashboard-pne-data-pipeline/1.0"},
        )
        with urllib.request.urlopen(request, timeout=120) as response, archive.open(
            "wb"
        ) as destination:
            shutil.copyfileobj(response, destination)
        if not zipfile.is_zipfile(archive):
            raise ValueError(f"{archive.name}: resposta não é um ZIP válido.")
        with zipfile.ZipFile(archive) as package:
            corrupt = package.testzip()
            if corrupt:
                raise ValueError(f"{archive.name}: item corrompido: {corrupt}")
            package.extractall(staging / "extracted")

        extracted = find_extracted_csv(staging / "extracted", year)
        validate_csv(extracted, year)
        destination = (
            CENSO_ESCOLAR_SOURCE_DIR / f"microdados_ed_basica_{year}.csv"
        )
        if destination.exists() and sha256(destination) == sha256(extracted):
            return destination
        if destination.exists():
            previous = (
                CENSO_ESCOLAR_SOURCE_DIR
                / ".previous"
                / str(year)
                / sha256(destination)
                / destination.name
            )
            previous.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(destination, previous)
        temporary = destination.with_suffix(".csv.new")
        shutil.copy2(extracted, temporary)
        validate_csv(temporary, year)
        os.replace(temporary, destination)

        extracted_root = (
            CENSO_ESCOLAR_SOURCE_DIR / f"microdados_censo_escolar_{year}"
        )
        if not extracted_root.exists():
            promoted = staging / "extracted"
            os.replace(promoted, extracted_root)
        return destination
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def load_manifest() -> dict:
    if not MANIFEST_PATH.exists():
        return {"schemaVersion": 1, "sources": {}}
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def write_manifest(payload: dict) -> None:
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = MANIFEST_PATH.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, MANIFEST_PATH)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--years", nargs="+", type=int, default=[2022, 2023, 2024])
    parser.add_argument("--download", action="store_true")
    args = parser.parse_args()

    manifest = load_manifest()
    for year in sorted(set(args.years)):
        path = download_year(year) if args.download else canonical_csv(year)
        validate_csv(path, year)
        stat = path.stat()
        checksum = sha256(path)
        existing = manifest["sources"].get(str(year), {})
        entry = {
            "year": year,
            "officialUrl": URL_TEMPLATE.format(year=year),
            "acquiredAt": datetime.fromtimestamp(
                stat.st_mtime, tz=timezone.utc
            ).isoformat(),
            "file": str(path),
            "size": stat.st_size,
            "sha256": checksum,
            "status": "validated",
        }
        if all(existing.get(key) == value for key, value in entry.items()):
            entry["auditedAt"] = existing["auditedAt"]
        else:
            entry["auditedAt"] = datetime.now(timezone.utc).isoformat()
        manifest["sources"][str(year)] = entry
    write_manifest(manifest)
    print(
        json.dumps(
            {
                "years": sorted(int(year) for year in manifest["sources"]),
                "manifest": str(MANIFEST_PATH),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
