"""Adquire snapshots oficiais SIDRA usados pela frente de mobilidade do Job 5G-D.

Este comando e o unico passo do Job 5G-D que usa rede. Ele consulta apenas o
host oficial ``apisidra.ibge.gov.br`` e preserva as respostas byte a byte. A
materializacao analitica posterior nunca acessa a rede.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import urllib.error
import urllib.request
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = (
    REPO_ROOT
    / "data_pipeline"
    / "data"
    / "vocacoes_pne_v7_job5gd"
    / "mobility_sidra"
)
MANIFEST_PATH = SOURCE_ROOT / "MANIFEST_SOURCE_MOBILITY_SIDRA_JOB5GD.json"
BASE_URL = "https://apisidra.ibge.gov.br"
USER_AGENT = "pne-react-vocacoes-pne-v7-job5gd/1.0"

MUNICIPALITY_CODES = (
    "4303905",
    "4306403",
    "4307609",
    "4307708",
    "4310801",
    "4313375",
    "4313409",
    "4314803",
    "4318705",
    "4320008",
)
LOCATION_CATEGORIES = ("12163", "12164", "12165", "79174")
COURSE_CATEGORIES = ("12121", "12122")

TABLES: dict[str, dict[str, Any]] = {
    "10321": {
        "variable": "13631",
        "segments": (
            "c468/12163,12164,12165,79174",
            "c2/6794",
            "c86/95251",
            "c386/9680",
        ),
        "expectedMunicipalityRows": len(MUNICIPALITY_CODES) * 4,
        "expectedStateRows": 4,
    },
    "10324": {
        "variable": "2021",
        "segments": (
            "c468/12163,12164,12165,79174",
            "c2/6794",
            "c58/95253",
            "c11322/12121,12122",
        ),
        "expectedMunicipalityRows": len(MUNICIPALITY_CODES) * 4 * 2,
        "expectedStateRows": 4 * 2,
    },
}


def _sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_bytes_atomic(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    if temporary.exists():
        raise FileExistsError(f"Arquivo temporario residual: {temporary}")
    try:
        with temporary.open("wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except Exception:
        if temporary.exists():
            temporary.unlink()
        raise


def _write_json_atomic(path: Path, payload: Any) -> None:
    content = (
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")
    _write_bytes_atomic(path, content)


def _requests() -> list[dict[str, Any]]:
    municipality_segment = ",".join(MUNICIPALITY_CODES)
    requests: list[dict[str, Any]] = []
    for table_id, spec in sorted(TABLES.items()):
        segments = "/".join(spec["segments"])
        requests.extend(
            [
                {
                    "file": f"descriptor_{table_id}.json",
                    "kind": "descriptor",
                    "table": table_id,
                    "url": f"{BASE_URL}/DescritoresTabela/t/{table_id}",
                },
                {
                    "file": f"values_{table_id}_vale_municipalities.json",
                    "kind": "values",
                    "level": "municipality",
                    "table": table_id,
                    "url": (
                        f"{BASE_URL}/values/t/{table_id}/n6/{municipality_segment}"
                        f"/v/{spec['variable']}/p/2022/{segments}/f/a/h/n"
                    ),
                },
                {
                    "file": f"values_{table_id}_rs.json",
                    "kind": "values",
                    "level": "state",
                    "table": table_id,
                    "url": (
                        f"{BASE_URL}/values/t/{table_id}/n3/43"
                        f"/v/{spec['variable']}/p/2022/{segments}/f/a/h/n"
                    ),
                },
            ]
        )
    return requests


def _download(url: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept-Encoding": "identity"},
    )
    try:
        with urllib.request.urlopen(request, timeout=240) as response:
            status = getattr(response, "status", 200)
            content = response.read()
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise RuntimeError(f"Falha na fonte oficial {url}: {type(exc).__name__}") from exc
    if status != 200 or not content:
        raise RuntimeError(f"Resposta oficial invalida: HTTP {status}, {len(content)} bytes")
    return content


def _validate_descriptor(content: bytes, table_id: str) -> dict[str, Any]:
    payload = json.loads(content.decode("utf-8"))
    serialized = json.dumps(payload, ensure_ascii=False)
    spec = TABLES[table_id]
    required_codes = {
        "2022",
        spec["variable"],
        "468",
        "2",
        *LOCATION_CATEGORIES,
    }
    if table_id == "10324":
        required_codes.update({"58", "11322", *COURSE_CATEGORIES})
    missing = sorted(code for code in required_codes if code not in serialized)
    if missing:
        raise ValueError(f"Descritor {table_id} sem codigos esperados: {missing}")
    return {"jsonRootType": type(payload).__name__, "requiredCodesPresent": True}


def _validate_values(
    content: bytes, table_id: str, level: str
) -> dict[str, Any]:
    rows = json.loads(content.decode("utf-8"))
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"Resposta {table_id}/{level} nao e lista nao vazia")
    expected_rows = TABLES[table_id][
        "expectedMunicipalityRows" if level == "municipality" else "expectedStateRows"
    ]
    if len(rows) != expected_rows:
        raise ValueError(
            f"Resposta {table_id}/{level}: {len(rows)} linhas, esperadas {expected_rows}"
        )
    codes = {str(row.get("D1C")) for row in rows}
    expected_codes = set(MUNICIPALITY_CODES) if level == "municipality" else {"43"}
    if codes != expected_codes:
        raise ValueError(
            f"Resposta {table_id}/{level}: codigos {sorted(codes)} divergentes"
        )
    keys: set[tuple[str, ...]] = set()
    special_lexemes: dict[str, int] = {key: 0 for key in ("-", "..", "...", "X")}
    for row in rows:
        code = str(row.get("D1C"))
        if level == "municipality" and re.fullmatch(r"\d{7}", code) is None:
            raise ValueError(f"Codigo municipal nao textual IBGE7: {code!r}")
        if str(row.get("D3C")) != "2022":
            raise ValueError(f"Periodo inesperado em {table_id}/{level}")
        location = str(row.get("D4C"))
        if location not in LOCATION_CATEGORIES:
            raise ValueError(f"Categoria de local inesperada: {location}")
        course = str(row.get("D7C")) if table_id == "10324" else "ALL"
        if table_id == "10324" and course not in COURSE_CATEGORIES:
            raise ValueError(f"Categoria de curso inesperada: {course}")
        key = (code, location, course)
        if key in keys:
            raise ValueError(f"Celula SIDRA duplicada: {key}")
        keys.add(key)
        lexeme = str(row.get("V"))
        if lexeme in special_lexemes:
            special_lexemes[lexeme] += 1
        elif re.fullmatch(r"\d+", lexeme) is None:
            raise ValueError(f"Lexema SIDRA inesperado: {lexeme!r}")
    return {
        "rowCount": len(rows),
        "localityCount": len(codes),
        "uniqueCellCount": len(keys),
        "specialLexemeCounts": special_lexemes,
    }


def _validate(request: dict[str, Any], content: bytes) -> dict[str, Any]:
    if request["kind"] == "descriptor":
        return _validate_descriptor(content, request["table"])
    return _validate_values(content, request["table"], request["level"])


def acquire() -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    acquired_at = datetime.now(timezone.utc).isoformat()
    for request in _requests():
        content = _download(request["url"])
        validation = _validate(request, content)
        path = SOURCE_ROOT / request["file"]
        _write_bytes_atomic(path, content)
        entries.append(
            {
                **request,
                "acquiredAtUtc": acquired_at,
                "byteSize": len(content),
                "sha256": _sha256_bytes(content),
                "validation": validation,
            }
        )
    manifest = {
        "schemaVersion": "vocacoes-pne-v7-job5gd-mobility-source-v1",
        "sourceInstitution": "IBGE",
        "sourceSystem": "SIDRA",
        "officialApiHost": BASE_URL,
        "landingPage": (
            "https://www.ibge.gov.br/estatisticas/sociais/populacao/22827-"
            "censo-demografico-2022.html?edicao=44665"
        ),
        "period": 2022,
        "tables": ["10321", "10324"],
        "municipalityCodes": list(MUNICIPALITY_CODES),
        "municipalityIdentity": "textual_ibge_code_7_digits",
        "territorialLens": "student_residence",
        "licenseAndProvenance": (
            "Official IBGE statistical dissemination; preserve source attribution and raw response."
        ),
        "acquiredAtUtc": acquired_at,
        "files": entries,
        "originDestinationAvailability": {
            "state": "NOT_AVAILABLE_IN_TABLES_10321_10324",
            "reason": (
                "The official tables distinguish own municipality, another municipality and foreign country, "
                "but do not identify the destination municipality."
            ),
            "originDestinationMatrixDerived": False,
            "destinationMunicipalityNamed": False,
            "officialMicrodataStatusVerificationUrl": (
                "https://www.ibge.gov.br/novo-portal-erramos/45278-adiamento-das-"
                "divulgacoes-censo-demografico-2022-microdados-da-amostra-e-censo-"
                "demografico-2022-areas-de-ponderacao.html"
            ),
            "verificationDate": "2026-08-29",
        },
    }
    _write_json_atomic(MANIFEST_PATH, manifest)
    return manifest


def check() -> dict[str, Any]:
    if not MANIFEST_PATH.is_file():
        raise FileNotFoundError(MANIFEST_PATH)
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    requests = {item["file"]: item for item in _requests()}
    entries = {item["file"]: item for item in manifest.get("files", [])}
    if set(entries) != set(requests):
        raise ValueError("Manifesto de mobilidade nao cobre as seis respostas esperadas")
    for name, request in requests.items():
        path = SOURCE_ROOT / name
        entry = entries[name]
        if not path.is_file():
            raise FileNotFoundError(path)
        content = path.read_bytes()
        if entry.get("url") != request["url"]:
            raise ValueError(f"URL divergente em {name}")
        if entry.get("byteSize") != len(content) or entry.get("sha256") != _sha256_file(path):
            raise ValueError(f"Hash/tamanho divergente em {name}")
        if entry.get("validation") != _validate(request, content):
            raise ValueError(f"Validacao divergente em {name}")
    return {
        "ok": True,
        "manifest": str(MANIFEST_PATH.relative_to(REPO_ROOT)).replace("\\", "/"),
        "manifestSha256": _sha256_file(MANIFEST_PATH),
        "fileCount": len(entries),
        "networkUsed": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--acquire", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    payload = acquire() if args.acquire else check()
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
