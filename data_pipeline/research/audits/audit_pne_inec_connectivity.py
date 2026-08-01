#!/usr/bin/env python3
"""Registra a auditoria bloqueada da conectividade adequada do INEC/ENEC."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
import tempfile

import requests


DATA_PIPELINE_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(DATA_PIPELINE_DIR))

from src.pne_macro_ingestion import (  # noqa: E402
    DATA_ROOT,
    MANIFEST_SCHEMA,
    canonical_json_bytes,
    raw_file_entry,
    write_source_snapshot,
)


SOURCE_ID = "mec_inec"
NOTE_URL = "https://www.gov.br/mec/pt-br/escolas-conectadas/documentos/NotaTcnica.pdf"
SOURCE_PAGE = "https://www.gov.br/mec/pt-br/escolas-conectadas"
DESTINATION = DATA_ROOT / "inec_connectivity"


def _download(destination: Path) -> Path:
    response = requests.get(NOTE_URL, timeout=180)
    response.raise_for_status()
    destination.write_bytes(response.content)
    return destination


def materialize(note_path: Path) -> dict:
    manifest = {
        "schemaVersion": MANIFEST_SCHEMA,
        "sourceId": SOURCE_ID,
        "sourceTitle": "Indicador Escolas Conectadas (INEC)",
        "organization": "Ministério da Educação",
        "edition": "metodologia vigente consultada em 2026",
        "sourcePageUrl": SOURCE_PAGE,
        "rawFiles": [
            raw_file_entry(
                logical_name="technicalNote",
                path=note_path,
                official_url=NOTE_URL,
            )
        ],
        "dictionary": {
            "documentedComponents": [
                "energia elétrica",
                "conexão de internet",
                "velocidade adequada",
                "rede interna wi-fi",
                "escola monitorada",
            ],
        },
        "coverage": {
            "municipalityCount": 0,
            "reason": (
                "Não foi localizada base pública estruturada por escola com "
                "identificador estável e estado de monitoramento."
            ),
        },
        "absencePolicy": {
            "unmonitoredSchool": "unknown",
            "municipalityWithoutPublicSchool": "not_applicable",
        },
        "status": "blocked",
        "blockedReason": (
            "A nota técnica homologa a definição do INEC, mas a página oficial "
            "não oferece snapshot estruturado por escola com energia, conexão, "
            "velocidade, wi-fi e não monitoradas. Presença de internet do "
            "Censo Escolar não foi usada como conectividade adequada."
        ),
    }
    write_source_snapshot(
        destination=DESTINATION,
        raw_files={note_path.name: note_path},
        normalized=None,
        manifest=manifest,
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--note-file", type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="pne-inec-") as temporary:
        note = args.note_file or _download(Path(temporary) / "NotaTecnica.pdf")
        manifest = materialize(note)
    print(canonical_json_bytes(manifest).decode("utf-8"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
