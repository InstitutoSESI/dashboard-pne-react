from __future__ import annotations

import copy
import csv
import ftplib
import hashlib
import io
import json
import re
import shutil
import threading
import time
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from pypdf import PdfReader

from .municipal_finance_p5b2 import (
    ADAPTER_VERSION,
    RREO_LAYOUT_VERSION,
    RREO_PARSER_VERSION,
    SourceSchemaError,
    adapt_rreo_text,
    adapt_siope_rows,
    canonical_json,
    sha256_bytes,
)


CONSTITUTIONAL_SNAPSHOT_VERSION = "municipal-finance-constitutional-p5b2b1-v1"
CONSTITUTIONAL_DATA_VERSION = "p5b2b1-annual-fallback-v1-2026-07-23"
CROSSWALK_VERSION = "siope-ibge-rs-2024-v1"
REFERENCE_YEAR = 2024
REFERENCE_PERIOD = 6
EXPECTED_MUNICIPALITIES = 497
ACCESSED_AT = "2026-07-20"
GENERATED_AT = "2026-07-20T00:00:00-03:00"


@dataclass(frozen=True, slots=True)
class ConstitutionalState:
    state_code: str
    municipality_ibge_prefix: str
    expected_municipality_count: int

    @property
    def municipality_pattern(self) -> re.Pattern[str]:
        return re.compile(
            rf"{re.escape(self.municipality_ibge_prefix)}\d{{5}}"
        )

    @property
    def siope_code_pattern(self) -> re.Pattern[str]:
        return re.compile(
            rf"{re.escape(self.municipality_ibge_prefix)}\d{{4}}"
        )

    @property
    def crosswalk_version(self) -> str:
        return f"siope-ibge-{self.state_code.casefold()}-2024-v1"


RS_CONSTITUTIONAL_STATE = ConstitutionalState(
    "RS",
    "43",
    EXPECTED_MUNICIPALITIES,
)

SIOPE_SOURCE_ID = "fnde_siope_indicators_odata_2024_p6"
RREO_SOURCE_ID = "fnde_siope_rreo_annex8_2024_p6"
RECONCILIATION_SOURCE_ID = "siope_rreo_constitutional_reconciliation_2024_p6"
RREO_FTP_DIRECTORY = "ftp://ftp.fnde.gov.br/web/siope/RREO/"
RREO_FTP_HOST = "ftp.fnde.gov.br"
RREO_FTP_PATH = "/web/siope/RREO"

SIOPE_FIELDS = {
    "mde_applied_value": ("mdeAppliedAmount", "empenhado", "BRL"),
    "mde_application_rate": ("mdeAppliedRate", "calculated_indicator", "percent"),
    "fundeb_professionals_remuneration_rate": (
        "fundebProfessionalRemunerationRate",
        "calculated_indicator",
        "percent",
    ),
}
RREO_FIELDS = {
    "mde_applied_value": "mdeAppliedAmount",
    "mde_application_rate": "mdeAppliedRate",
    "fundeb_professionals_remuneration_rate": "fundebProfessionalRemunerationRate",
    "fundeb_total_received": "fundebRevenueReceivedDeclared",
}


def constitutional_source_ids(reference_year: int) -> tuple[str, str, str]:
    suffix = f"{reference_year}_p{REFERENCE_PERIOD}"
    return (
        f"fnde_siope_indicators_odata_{suffix}",
        f"fnde_siope_rreo_annex8_{suffix}",
        f"siope_rreo_constitutional_reconciliation_{suffix}",
    )


def siope_source_url(
    reference_year: int,
    state: ConstitutionalState = RS_CONSTITUTIONAL_STATE,
) -> str:
    query = urlencode(
        {
            "@Ano_Consulta": reference_year,
            "@Num_Peri": REFERENCE_PERIOD,
            "@Sig_UF": f"'{state.state_code}'",
        },
    )
    return (
        "https://www.fnde.gov.br/olinda-ide/servico/DADOS_ABERTOS_SIOPE/versao/v1/odata/"
        "Indicadores_Siope(Ano_Consulta=@Ano_Consulta,Num_Peri=@Num_Peri,Sig_UF=@Sig_UF)"
        f"?{query}"
    )


def _json_text(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False) + "\n"


def _write_text_if_changed(path: Path, content: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = content.encode("utf-8")
    if path.exists() and path.read_bytes() == encoded:
        return "preserved"
    action = "updated" if path.exists() else "created"
    path.write_bytes(encoded)
    return action


def _write_json_if_changed(path: Path, payload: Any) -> str:
    return _write_text_if_changed(path, _json_text(payload))


def _csv_text(rows: list[dict[str, Any]], fieldnames: list[str]) -> str:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def _six_digit_code(
    value: Any,
    state: ConstitutionalState = RS_CONSTITUTIONAL_STATE,
) -> str:
    digits = re.sub(r"\D", "", str(value or ""))
    if state.siope_code_pattern.fullmatch(digits) is None:
        raise SourceSchemaError(f"Código municipal SIOPE/RREO inválido: {value!r}")
    return digits


def build_crosswalk(
    municipalities: list[dict[str, str]],
    registry_path: Path,
    state: ConstitutionalState = RS_CONSTITUTIONAL_STATE,
) -> dict[str, Any]:
    if len(municipalities) != state.expected_municipality_count:
        raise SourceSchemaError(
            f"Crosswalk recebeu {len(municipalities)} municípios; "
            f"esperado {state.expected_municipality_count}"
        )
    records = []
    for municipality in sorted(municipalities, key=lambda item: item["ibgeCode"]):
        ibge_code = str(municipality["ibgeCode"])
        if state.municipality_pattern.fullmatch(ibge_code) is None:
            raise SourceSchemaError(f"Código IBGE inválido no cadastro canônico: {ibge_code!r}")
        records.append(
            {
                "siopeRreoCode": _six_digit_code(ibge_code[:6], state),
                "ibgeCode": ibge_code,
                "municipality": municipality["name"],
            }
        )
    codes6 = [record["siopeRreoCode"] for record in records]
    codes7 = [record["ibgeCode"] for record in records]
    if (
        len(set(codes6)) != state.expected_municipality_count
        or len(set(codes7)) != state.expected_municipality_count
    ):
        raise SourceSchemaError("Crosswalk contém códigos SIOPE/RREO ou IBGE duplicados")
    registry_hash = hashlib.sha256(registry_path.read_bytes()).hexdigest()
    repository_root = Path(__file__).resolve().parents[2]
    try:
        source_path = registry_path.resolve().relative_to(repository_root).as_posix()
    except ValueError:
        source_path = registry_path.name
    return {
        "crosswalkVersion": state.crosswalk_version,
        "sourceId": (
            f"municipal_registry_ibge_{state.state_code.casefold()}_"
            f"{state.expected_municipality_count}"
        ),
        "sourcePath": source_path,
        "sourceSha256": registry_hash,
        "referenceYear": REFERENCE_YEAR,
        "municipalities": state.expected_municipality_count,
        "primaryKey": "siopeRreoCode",
        "targetKey": "ibgeCode",
        "nameMatchingAllowed": False,
        "records": records,
    }


def validate_crosswalk(
    payload: dict[str, Any],
    state: ConstitutionalState = RS_CONSTITUTIONAL_STATE,
) -> dict[str, dict[str, str]]:
    if payload.get("crosswalkVersion") != state.crosswalk_version:
        raise SourceSchemaError(f"Versão de crosswalk incompatível: {payload.get('crosswalkVersion')}")
    records = payload.get("records") or []
    if len(records) != state.expected_municipality_count:
        raise SourceSchemaError(f"Crosswalk contém {len(records)} registros")
    result: dict[str, dict[str, str]] = {}
    ibge_codes: set[str] = set()
    for record in records:
        code6 = _six_digit_code(record.get("siopeRreoCode"), state)
        code7 = str(record.get("ibgeCode"))
        if state.municipality_pattern.fullmatch(code7) is None:
            raise SourceSchemaError(f"Crosswalk contém código IBGE inválido: {code7!r}")
        if code6 in result or code7 in ibge_codes:
            raise SourceSchemaError("Crosswalk contém duplicidade")
        result[code6] = {"ibgeCode": code7, "name": str(record.get("municipality"))}
        ibge_codes.add(code7)
    return result


def _load_siope_rows(
    path: Path,
    state: ConstitutionalState = RS_CONSTITUTIONAL_STATE,
) -> tuple[dict[str, Any], list[dict[str, Any]], str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    pages = payload.get("pages")
    if not isinstance(pages, list) or not pages:
        raise SourceSchemaError("SIOPE: cache sem páginas OData")
    rows = [item for page in pages for item in page.get("response", {}).get("value", [])]
    if not rows:
        raise SourceSchemaError("SIOPE: cache sem registros")
    source_rows = rows
    for row in rows:
        if int(row.get("NUM_ANO", -1)) != REFERENCE_YEAR or int(row.get("NUM_PERI", -1)) != REFERENCE_PERIOD:
            raise SourceSchemaError("SIOPE: exercício ou bimestre incompatível no cache")
        if row.get("SIG_UF") != state.state_code:
            raise SourceSchemaError("SIOPE: UF incompatível no cache")
        if row.get("TIPO") not in {"Municipal", "Estadual"}:
            raise SourceSchemaError("SIOPE: esfera incompatível no cache")
        if row.get("TIPO") == "Estadual" and row.get("COD_MUNI") is not None:
            raise SourceSchemaError("SIOPE: registro estadual contém código municipal")
    rows = [row for row in rows if row.get("TIPO") == "Municipal"]
    normalized = canonical_json(
        sorted(source_rows, key=lambda row: (str(row.get("COD_MUNI")), str(row.get("COD_EXIB"))))
    )
    return payload, rows, sha256_bytes(normalized)


def build_siope_source(
    cache_path: Path,
    registry_by_siope_code: dict[str, dict[str, str]],
    state: ConstitutionalState = RS_CONSTITUTIONAL_STATE,
) -> dict[str, Any]:
    metadata, rows, normalized_hash = _load_siope_rows(cache_path, state)
    present_codes = {
        _six_digit_code(row["COD_MUNI"], state)
        for row in rows
        if row.get("COD_MUNI") is not None
    }
    expected_codes = set(registry_by_siope_code)
    if present_codes != expected_codes:
        missing = sorted(expected_codes.difference(present_codes))
        unexpected = sorted(present_codes.difference(expected_codes))
        raise SourceSchemaError(f"SIOPE: crosswalk incompleto; ausentes={missing[:5]}, inesperados={unexpected[:5]}")
    adapted = adapt_siope_rows(
        rows,
        registry_by_siope_code,
        source_url=siope_source_url(REFERENCE_YEAR, state),
        source_hash=normalized_hash,
        accessed_at=ACCESSED_AT,
        published_at=None,
        municipality_ibge_prefix=state.municipality_ibge_prefix,
        state_code=state.state_code,
    )
    records: dict[str, dict[str, Any]] = {}
    for record in adapted:
        definition = SIOPE_FIELDS.get(record["concept"])
        if definition is None:
            continue
        field, stage, unit = definition
        municipal_record = records.setdefault(record["ibgeCode"], {})
        if field in municipal_record:
            raise SourceSchemaError(f"SIOPE: campo duplicado {record['ibgeCode']}/{field}")
        municipal_record[field] = {
            "value": record["value"],
            "financialStage": stage,
            "amountNature": "municipal_declared",
            "unit": unit,
            "indicatorCode": record["dimensions"]["indicatorCode"],
            "displayCode": record["dimensions"]["displayCode"],
        }
    expected_fields = {definition[0] for definition in SIOPE_FIELDS.values()}
    for code7 in sorted(item["ibgeCode"] for item in registry_by_siope_code.values()):
        actual = set(records.get(code7, {}))
        if actual != expected_fields:
            raise SourceSchemaError(f"SIOPE: campos inválidos para {code7}: {sorted(actual)}")
    return {
        "sourceId": SIOPE_SOURCE_ID,
        "referenceYear": REFERENCE_YEAR,
        "period": REFERENCE_PERIOD,
        "accessedAt": ACCESSED_AT,
        "sourceUrl": siope_source_url(REFERENCE_YEAR, state),
        "rawSha256": normalized_hash,
        "adapterVersion": ADAPTER_VERSION,
        "generatedAtSource": metadata.get("generated_at"),
        "quality": {
            "municipalitiesExpected": state.expected_municipality_count,
            "municipalitiesFound": len(records),
            "municipalitiesNotFound": 0,
            "duplicateMunicipalityCodes": [],
            "incompatibleMunicipalityKeys": 0,
            "coverageRate": 1,
        },
        "records": dict(sorted(records.items())),
    }


def _ftp_metadata(codes6: Iterable[str]) -> dict[str, dict[str, Any]]:
    ftp = ftplib.FTP(RREO_FTP_HOST, timeout=180)
    ftp.login()
    ftp.cwd(RREO_FTP_PATH)
    result: dict[str, dict[str, Any]] = {}
    try:
        for code6 in sorted(codes6):
            filename = f"RREO_Municipal_{code6}_{REFERENCE_PERIOD}_{REFERENCE_YEAR}.pdf"
            modified_response = ftp.sendcmd(f"MDTM {filename}")
            size_response = ftp.sendcmd(f"SIZE {filename}")
            if not modified_response.startswith("213 ") or not size_response.startswith("213 "):
                raise SourceSchemaError(f"RREO: metadados FTP inválidos para {filename}")
            modified = datetime.strptime(modified_response[4:], "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
            result[code6] = {
                "lastModified": modified.isoformat().replace("+00:00", "Z"),
                "sizeBytes": int(size_response[4:]),
            }
    finally:
        try:
            ftp.quit()
        except OSError:
            ftp.close()
    return result


def _download_rreo_files(
    codes6: Iterable[str],
    metadata: dict[str, dict[str, Any]],
    cache_dir: Path,
    previous_records_by_code6: dict[str, dict[str, Any]],
    expected_municipality_count: int = EXPECTED_MUNICIPALITIES,
) -> dict[str, Path]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    ftp: ftplib.FTP | None = None

    def connect() -> ftplib.FTP:
        connection = ftplib.FTP(RREO_FTP_HOST, timeout=180)
        connection.login()
        connection.cwd(RREO_FTP_PATH)
        return connection

    try:
        for position, code6 in enumerate(sorted(codes6), start=1):
            filename = f"RREO_Municipal_{code6}_{REFERENCE_PERIOD}_{REFERENCE_YEAR}.pdf"
            path = cache_dir / filename
            previous = previous_records_by_code6.get(code6)
            if (
                previous is None
                and path.exists()
                and path.stat().st_size == metadata[code6]["sizeBytes"]
            ):
                paths[code6] = path
                continue
            last_error: Exception | None = None
            for attempt in range(4):
                try:
                    if ftp is None:
                        ftp = connect()
                    buffer = io.BytesIO()
                    ftp.retrbinary(f"RETR {filename}", buffer.write)
                    content = buffer.getvalue()
                    if len(content) != metadata[code6]["sizeBytes"]:
                        raise SourceSchemaError(
                            f"RREO: tamanho divergente para {filename}: "
                            f"{len(content)} != {metadata[code6]['sizeBytes']}"
                        )
                    current_hash = sha256_bytes(content)
                    if previous is not None and previous.get("sourceHash") != current_hash and path.exists():
                        previous_hash = sha256_bytes(path.read_bytes())
                        if previous_hash == previous.get("sourceHash"):
                            revision_path = (
                                cache_dir
                                / "revisions"
                                / f"{path.stem}-{previous_hash}.pdf"
                            )
                            revision_path.parent.mkdir(parents=True, exist_ok=True)
                            if not revision_path.exists():
                                shutil.copy2(path, revision_path)
                    path.write_bytes(content)
                    paths[code6] = path
                    last_error = None
                    break
                except (OSError, EOFError, ftplib.Error) as error:
                    last_error = error
                    if ftp is not None:
                        try:
                            ftp.close()
                        except OSError:
                            pass
                        ftp = None
                    time.sleep(2**attempt)
            if last_error is not None:
                raise RuntimeError(f"RREO: falha ao baixar {filename}") from last_error
            if position % 50 == 0 or position == expected_municipality_count:
                print(
                    "[municipal-finance] RREO PDFs "
                    f"{position}/{expected_municipality_count}",
                    flush=True,
                )
    finally:
        if ftp is not None:
            try:
                ftp.quit()
            except (OSError, EOFError, ftplib.Error):
                ftp.close()
    return paths


def _parse_rreo_record(
    code6: str,
    municipality: dict[str, str],
    metadata: dict[str, Any],
    path: Path,
    state: ConstitutionalState = RS_CONSTITUTIONAL_STATE,
) -> tuple[str, dict[str, Any]]:
    filename = f"RREO_Municipal_{code6}_{REFERENCE_PERIOD}_{REFERENCE_YEAR}.pdf"
    url = f"{RREO_FTP_DIRECTORY}{filename}"
    content = path.read_bytes()
    if len(content) != metadata["sizeBytes"]:
        raise SourceSchemaError(
            f"RREO: tamanho divergente para {filename}: {len(content)} != {metadata['sizeBytes']}"
        )
    source_hash = sha256_bytes(content)
    text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(content)).pages)
    adapted = adapt_rreo_text(
        text,
        municipality=municipality["name"],
        ibge_code=municipality["ibgeCode"],
        reference_year=REFERENCE_YEAR,
        bimester=REFERENCE_PERIOD,
        source_url=url,
        source_hash=source_hash,
        accessed_at=ACCESSED_AT,
        published_at=metadata["lastModified"],
        municipality_ibge_prefix=state.municipality_ibge_prefix,
        state_code=state.state_code,
    )
    values: dict[str, Any] = {}
    mappings: dict[str, Any] = {}
    for record in adapted:
        field = RREO_FIELDS.get(record["concept"])
        if field is None:
            continue
        values[field] = record["value"]
        mappings[field] = {
            "line": record["dimensions"]["line"],
            "column": record["dimensions"]["column"],
            "unit": record["dimensions"]["unit"],
            "financialStage": record["financialStage"],
        }
    if set(values) != set(RREO_FIELDS.values()):
        raise SourceSchemaError(f"RREO: campos incompletos para {municipality['ibgeCode']}: {sorted(values)}")
    return municipality["ibgeCode"], {
        **values,
        "sourceUrl": url,
        "sourceHash": source_hash,
        "lastModified": metadata["lastModified"],
        "sizeBytes": metadata["sizeBytes"],
        "accessedAt": ACCESSED_AT,
        "parserVersion": RREO_PARSER_VERSION,
        "layoutVersion": RREO_LAYOUT_VERSION,
        "mappings": mappings,
    }


def _field_differences(previous: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    differences = {}
    for field in RREO_FIELDS.values():
        if previous.get(field) != current.get(field):
            differences[field] = {"previous": previous.get(field), "current": current.get(field)}
    return differences


def _load_revision_history(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "revisionPolicyVersion": "municipal-finance-rreo-revisions-v1",
            "events": [],
        }
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("revisionPolicyVersion") != "municipal-finance-rreo-revisions-v1":
        raise SourceSchemaError("RREO: versão incompatível do histórico de retificações")
    return payload


def apply_rreo_revision_policy(
    previous_records: dict[str, dict[str, Any]],
    candidates: dict[str, dict[str, Any]],
    municipality_by_code: dict[str, dict[str, str]],
    revision_history: dict[str, Any],
    *,
    reference_year: int = REFERENCE_YEAR,
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    published_records: dict[str, dict[str, Any]] = {}
    new_events: list[dict[str, Any]] = []
    known_events = {
        (event.get("ibgeCode"), event.get("previousSha256"), event.get("detectedSha256"))
        for event in revision_history.get("events", [])
    }
    for code7, candidate in sorted(candidates.items()):
        previous = previous_records.get(code7)
        if previous is None or previous.get("sourceHash") == candidate["sourceHash"]:
            published_records[code7] = candidate
            continue
        event_key = (code7, previous.get("sourceHash"), candidate["sourceHash"])
        event = {
            "status": "source_revision_detected",
            "ibgeCode": code7,
            "municipality": municipality_by_code[code7]["name"],
            "referenceYear": reference_year,
            "period": REFERENCE_PERIOD,
            "sourceUrl": candidate["sourceUrl"],
            "previousSha256": previous.get("sourceHash"),
            "detectedSha256": candidate["sourceHash"],
            "previousLastModified": previous.get("lastModified"),
            "detectedLastModified": candidate.get("lastModified"),
            "previousSizeBytes": previous.get("sizeBytes"),
            "detectedSizeBytes": candidate.get("sizeBytes"),
            "detectedAt": ACCESSED_AT,
            "parserVersion": RREO_PARSER_VERSION,
            "fieldDifferences": _field_differences(previous, candidate),
            "publicationBlocked": True,
        }
        if event_key not in known_events:
            revision_history.setdefault("events", []).append(event)
            new_events.append(event)
            known_events.add(event_key)
        published_records[code7] = previous
    return published_records, new_events


def build_rreo_source(
    municipalities: list[dict[str, str]],
    crosswalk_by_siope_code: dict[str, dict[str, str]],
    previous_source: dict[str, Any] | None,
    revision_history: dict[str, Any],
    workers: int,
    cache_dir: Path,
    state: ConstitutionalState = RS_CONSTITUTIONAL_STATE,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if workers < 1:
        raise ValueError("RREO: workers deve ser positivo")
    metadata = _ftp_metadata(crosswalk_by_siope_code)
    previous_records = (previous_source or {}).get("records", {})
    previous_records_by_code6 = {
        code6: previous_records[municipality["ibgeCode"]]
        for code6, municipality in crosswalk_by_siope_code.items()
        if municipality["ibgeCode"] in previous_records
    }
    cached_paths = _download_rreo_files(
        crosswalk_by_siope_code,
        metadata,
        cache_dir,
        previous_records_by_code6,
        state.expected_municipality_count,
    )
    municipality_by_code = {municipality["ibgeCode"]: municipality for municipality in municipalities}
    candidates: dict[str, dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(
                _parse_rreo_record,
                code6,
                municipality_by_code[crosswalk_by_siope_code[code6]["ibgeCode"]],
                metadata[code6],
                cached_paths[code6],
                state,
            ): code6
            for code6 in sorted(crosswalk_by_siope_code)
        }
        for future in as_completed(futures):
            code7, record = future.result()
            candidates[code7] = record
    if len(candidates) != state.expected_municipality_count:
        raise SourceSchemaError(
            f"RREO: {len(candidates)} PDFs válidos; esperado "
            f"{state.expected_municipality_count}"
        )

    published_records, new_events = apply_rreo_revision_policy(
        previous_records,
        candidates,
        municipality_by_code,
        revision_history,
    )

    combined_hash = hashlib.sha256()
    for code7, record in sorted(published_records.items()):
        combined_hash.update(code7.encode("ascii"))
        combined_hash.update(record["sourceHash"].encode("ascii"))
    return {
        "sourceId": RREO_SOURCE_ID,
        "referenceYear": REFERENCE_YEAR,
        "period": REFERENCE_PERIOD,
        "accessedAt": ACCESSED_AT,
        "sourceUrl": RREO_FTP_DIRECTORY,
        "rawSha256": combined_hash.hexdigest(),
        "parserVersion": RREO_PARSER_VERSION,
        "layoutVersion": RREO_LAYOUT_VERSION,
        "quality": {
            "municipalitiesExpected": state.expected_municipality_count,
            "municipalitiesFound": len(published_records),
            "municipalitiesNotFound": 0,
            "duplicateMunicipalityCodes": [],
            "incompatibleMunicipalityKeys": 0,
            "coverageRate": 1,
            "sourceRevisionDetected": len(new_events),
        },
        "records": published_records,
        "pendingRevisionRecords": {
            event["ibgeCode"]: candidates[event["ibgeCode"]]
            for event in new_events
        },
    }, new_events


def collect_constitutional_snapshot(
    municipalities: list[dict[str, str]],
    *,
    registry_path: Path,
    siope_cache_path: Path,
    snapshot_path: Path,
    crosswalk_path: Path,
    revision_history_path: Path,
    rreo_cache_dir: Path,
    rreo_workers: int = 8,
    state: ConstitutionalState = RS_CONSTITUTIONAL_STATE,
) -> dict[str, Any]:
    crosswalk = build_crosswalk(municipalities, registry_path, state)
    crosswalk_by_siope_code = validate_crosswalk(crosswalk, state)
    previous_snapshot = None
    if snapshot_path.exists():
        previous_snapshot = load_constitutional_snapshot(snapshot_path, state)
    revision_history = _load_revision_history(revision_history_path)
    siope_source = build_siope_source(
        siope_cache_path,
        crosswalk_by_siope_code,
        state,
    )
    rreo_source, new_revision_events = build_rreo_source(
        municipalities,
        crosswalk_by_siope_code,
        (previous_snapshot or {}).get("sources", {}).get(RREO_SOURCE_ID),
        revision_history,
        rreo_workers,
        rreo_cache_dir,
        state,
    )
    snapshot = {
        "snapshotVersion": CONSTITUTIONAL_SNAPSHOT_VERSION,
        "dataVersion": CONSTITUTIONAL_DATA_VERSION,
        "generatedAt": GENERATED_AT,
        "stateCode": state.state_code,
        "referenceYear": REFERENCE_YEAR,
        "period": REFERENCE_PERIOD,
        "stageBasis": "empenhado",
        "municipalities": state.expected_municipality_count,
        "crosswalk": {
            "version": crosswalk["crosswalkVersion"],
            "sourceId": crosswalk["sourceId"],
            "sourceSha256": crosswalk["sourceSha256"],
            "records": state.expected_municipality_count,
        },
        "sources": {
            SIOPE_SOURCE_ID: siope_source,
            RREO_SOURCE_ID: rreo_source,
        },
        "revisionEventsDetected": new_revision_events,
    }
    _write_json_if_changed(crosswalk_path, crosswalk)
    _write_json_if_changed(revision_history_path, revision_history)
    _write_json_if_changed(snapshot_path, snapshot)
    return snapshot


def _fetch_siope_rows_for_year(
    reference_year: int,
    state: ConstitutionalState = RS_CONSTITUTIONAL_STATE,
) -> tuple[list[dict[str, Any]], str, str]:
    url = siope_source_url(reference_year, state)
    pages: list[dict[str, Any]] = []
    next_url: str | None = url
    while next_url:
        request = Request(next_url, headers={"User-Agent": "DASHBOARD-PNE-REACT/P5-B1"})
        with urlopen(request, timeout=180) as response:
            page = json.loads(response.read().decode("utf-8"))
        pages.append(page)
        next_url = page.get("@odata.nextLink") or page.get("odata.nextLink")
    rows = [item for page in pages for item in page.get("value", [])]
    if not rows:
        raise SourceSchemaError(f"SIOPE: resposta vazia para {reference_year}/P{REFERENCE_PERIOD}")
    for row in rows:
        if int(row.get("NUM_ANO", -1)) != reference_year or int(row.get("NUM_PERI", -1)) != REFERENCE_PERIOD:
            raise SourceSchemaError("SIOPE: exercício ou bimestre incompatível na consulta oficial")
        if row.get("SIG_UF") != state.state_code:
            raise SourceSchemaError("SIOPE: UF incompatível na consulta oficial")
    normalized = canonical_json(
        sorted(rows, key=lambda row: (str(row.get("COD_MUNI")), str(row.get("COD_EXIB"))))
    )
    return rows, url, sha256_bytes(normalized)


def build_siope_source_for_year(
    reference_year: int,
    registry_by_siope_code: dict[str, dict[str, str]],
    state: ConstitutionalState = RS_CONSTITUTIONAL_STATE,
) -> dict[str, Any]:
    rows, source_url, raw_hash = _fetch_siope_rows_for_year(
        reference_year,
        state,
    )
    adapted = adapt_siope_rows(
        rows,
        registry_by_siope_code,
        source_url=source_url,
        source_hash=raw_hash,
        accessed_at=ACCESSED_AT,
        published_at=None,
        municipality_ibge_prefix=state.municipality_ibge_prefix,
        state_code=state.state_code,
    )
    records: dict[str, dict[str, Any]] = {}
    for record in adapted:
        definition = SIOPE_FIELDS.get(record["concept"])
        if definition is None:
            continue
        field, stage, unit = definition
        municipal_record = records.setdefault(record["ibgeCode"], {})
        if field in municipal_record:
            raise SourceSchemaError(f"SIOPE: campo duplicado {record['ibgeCode']}/{field}")
        municipal_record[field] = {
            "value": record["value"],
            "financialStage": stage,
            "amountNature": "municipal_declared",
            "unit": unit,
            "indicatorCode": record["dimensions"]["indicatorCode"],
            "displayCode": record["dimensions"]["displayCode"],
        }
    expected_fields = {definition[0] for definition in SIOPE_FIELDS.values()}
    complete_codes = {
        code
        for code, record in records.items()
        if set(record) == expected_fields and all(value["value"] is not None for value in record.values())
    }
    source_id, _, _ = constitutional_source_ids(reference_year)
    return {
        "sourceId": source_id,
        "referenceYear": reference_year,
        "period": REFERENCE_PERIOD,
        "accessedAt": ACCESSED_AT,
        "sourceUrl": source_url,
        "rawSha256": raw_hash,
        "adapterVersion": ADAPTER_VERSION,
        "quality": {
            "municipalitiesExpected": state.expected_municipality_count,
            "municipalitiesFound": len(records),
            "municipalitiesWithRequiredFields": len(complete_codes),
            "municipalitiesNotFound": (
                state.expected_municipality_count - len(records)
            ),
            "duplicateMunicipalityCodes": [],
            "incompatibleMunicipalityKeys": 0,
            "coverageRate": round(
                len(complete_codes) / state.expected_municipality_count,
                6,
            ),
        },
        "records": dict(sorted(records.items())),
    }


def build_rreo_source_for_year(
    reference_year: int,
    municipalities: list[dict[str, str]],
    crosswalk_by_siope_code: dict[str, dict[str, str]],
    previous_source: dict[str, Any] | None,
    revision_history: dict[str, Any],
    workers: int,
    state: ConstitutionalState = RS_CONSTITUTIONAL_STATE,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if workers < 1:
        raise ValueError("RREO: workers deve ser positivo")
    municipality_by_code = {municipality["ibgeCode"]: municipality for municipality in municipalities}
    connection_state = threading.local()

    def close_connection() -> None:
        ftp = getattr(connection_state, "ftp", None)
        if ftp is not None:
            try:
                ftp.close()
            except OSError:
                pass
        connection_state.ftp = None

    def connection() -> ftplib.FTP:
        ftp = getattr(connection_state, "ftp", None)
        if ftp is None:
            ftp = ftplib.FTP(RREO_FTP_HOST, timeout=180)
            ftp.login()
            ftp.cwd(RREO_FTP_PATH)
            connection_state.ftp = ftp
        return ftp

    def fetch_one(code6: str) -> tuple[str, dict[str, Any] | None, str | None]:
        municipality = municipality_by_code[crosswalk_by_siope_code[code6]["ibgeCode"]]
        filename = f"RREO_Municipal_{code6}_{REFERENCE_PERIOD}_{reference_year}.pdf"
        try:
            ftp = connection()
            modified_response = ftp.sendcmd(f"MDTM {filename}")
            size_response = ftp.sendcmd(f"SIZE {filename}")
            if not modified_response.startswith("213 ") or not size_response.startswith("213 "):
                raise SourceSchemaError(f"RREO: metadados FTP inválidos para {filename}")
            content_buffer = io.BytesIO()
            ftp.retrbinary(f"RETR {filename}", content_buffer.write)
            content = content_buffer.getvalue()
            size = int(size_response[4:])
            if len(content) != size:
                raise SourceSchemaError(f"RREO: tamanho divergente para {filename}")
            source_hash = sha256_bytes(content)
            text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(content)).pages)
            adapted = adapt_rreo_text(
                text,
                municipality=municipality["name"],
                ibge_code=municipality["ibgeCode"],
                reference_year=reference_year,
                bimester=REFERENCE_PERIOD,
                source_url=f"{RREO_FTP_DIRECTORY}{filename}",
                source_hash=source_hash,
                accessed_at=ACCESSED_AT,
                published_at=modified_response[4:],
                municipality_ibge_prefix=state.municipality_ibge_prefix,
                state_code=state.state_code,
            )
            values: dict[str, Any] = {}
            mappings: dict[str, Any] = {}
            for record in adapted:
                field = RREO_FIELDS.get(record["concept"])
                if field is None:
                    continue
                values[field] = record["value"]
                mappings[field] = {
                    "line": record["dimensions"]["line"],
                    "column": record["dimensions"]["column"],
                    "unit": record["dimensions"]["unit"],
                    "financialStage": record["financialStage"],
                }
            if set(values) != set(RREO_FIELDS.values()):
                raise SourceSchemaError(f"RREO: campos incompletos para {municipality['ibgeCode']}")
            modified = datetime.strptime(modified_response[4:], "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
            return municipality["ibgeCode"], {
                **values,
                "sourceUrl": f"{RREO_FTP_DIRECTORY}{filename}",
                "sourceHash": source_hash,
                "lastModified": modified.isoformat().replace("+00:00", "Z"),
                "sizeBytes": size,
                "accessedAt": ACCESSED_AT,
                "parserVersion": RREO_PARSER_VERSION,
                "layoutVersion": RREO_LAYOUT_VERSION,
                "mappings": mappings,
            }, None
        except Exception as error:  # pragma: no cover - network variability
            close_connection()
            return municipality["ibgeCode"], None, f"{type(error).__name__}: {error}"

    candidates: dict[str, dict[str, Any]] = {}
    errors: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(fetch_one, code6) for code6 in sorted(crosswalk_by_siope_code)]
        for future in as_completed(futures):
            code7, record, error = future.result()
            if record is None:
                errors[code7] = error or "RREO: falha sem detalhe"
            else:
                candidates[code7] = record

    previous_records = (previous_source or {}).get("records", {})
    published_records, new_events = apply_rreo_revision_policy(
        previous_records,
        candidates,
        municipality_by_code,
        revision_history,
        reference_year=reference_year,
    )
    combined_hash = hashlib.sha256()
    for code7, record in sorted(published_records.items()):
        combined_hash.update(code7.encode("ascii"))
        combined_hash.update(record["sourceHash"].encode("ascii"))
    _, source_id, _ = constitutional_source_ids(reference_year)
    return {
        "sourceId": source_id,
        "referenceYear": reference_year,
        "period": REFERENCE_PERIOD,
        "accessedAt": ACCESSED_AT,
        "sourceUrl": RREO_FTP_DIRECTORY,
        "rawSha256": combined_hash.hexdigest(),
        "parserVersion": RREO_PARSER_VERSION,
        "layoutVersion": RREO_LAYOUT_VERSION,
        "quality": {
            "municipalitiesExpected": state.expected_municipality_count,
            "municipalitiesFound": len(published_records),
            "municipalitiesWithRequiredFields": len(published_records),
            "municipalitiesNotFound": (
                state.expected_municipality_count - len(published_records)
            ),
            "duplicateMunicipalityCodes": [],
            "incompatibleMunicipalityKeys": 0,
            "coverageRate": round(
                len(published_records) / state.expected_municipality_count,
                6,
            ),
            "sourceRevisionDetected": len(new_events),
            "requestOrParseErrors": len(errors),
            "requestOrParseErrorCodes": sorted(errors),
        },
        "records": dict(sorted(published_records.items())),
        "pendingRevisionRecords": {
            event["ibgeCode"]: candidates[event["ibgeCode"]]
            for event in new_events
        },
    }, new_events


def refresh_annual_constitutional_snapshot(
    municipalities: list[dict[str, str]],
    *,
    registry_path: Path,
    snapshot_path: Path,
    crosswalk_path: Path,
    revision_history_path: Path,
    reference_year: int,
    rreo_workers: int = 8,
    state: ConstitutionalState = RS_CONSTITUTIONAL_STATE,
) -> dict[str, Any]:
    if reference_year < 2000:
        raise ValueError("O exercício constitucional deve ter quatro dígitos.")
    crosswalk = build_crosswalk(municipalities, registry_path, state)
    crosswalk_by_siope_code = validate_crosswalk(crosswalk, state)
    previous_snapshot = (
        load_constitutional_snapshot(snapshot_path, state)
        if snapshot_path.exists()
        else None
    )
    revision_history = _load_revision_history(revision_history_path)
    siope_source_id, rreo_source_id, _ = constitutional_source_ids(reference_year)
    siope_source = build_siope_source_for_year(
        reference_year,
        crosswalk_by_siope_code,
        state,
    )
    rreo_source, new_events = build_rreo_source_for_year(
        reference_year,
        municipalities,
        crosswalk_by_siope_code,
        (previous_snapshot or {}).get("sources", {}).get(rreo_source_id),
        revision_history,
        rreo_workers,
        state,
    )
    sources = copy.deepcopy((previous_snapshot or {}).get("sources", {}))
    sources[siope_source_id] = siope_source
    sources[rreo_source_id] = rreo_source
    available_years = sorted(
        {
            int(source["referenceYear"])
            for source in sources.values()
            if source.get("referenceYear") is not None
        }
    )
    snapshot = {
        "snapshotVersion": CONSTITUTIONAL_SNAPSHOT_VERSION,
        "dataVersion": CONSTITUTIONAL_DATA_VERSION,
        "generatedAt": GENERATED_AT,
        "stateCode": state.state_code,
        "referenceYear": max(available_years),
        "referenceYears": available_years,
        "period": REFERENCE_PERIOD,
        "stageBasis": "empenhado",
        "municipalities": state.expected_municipality_count,
        "crosswalk": {
            "version": crosswalk["crosswalkVersion"],
            "sourceId": crosswalk["sourceId"],
            "sourceSha256": crosswalk["sourceSha256"],
            "records": state.expected_municipality_count,
        },
        "sources": sources,
        "revisionEventsDetected": new_events,
    }
    _write_json_if_changed(crosswalk_path, crosswalk)
    _write_json_if_changed(revision_history_path, revision_history)
    _write_json_if_changed(snapshot_path, snapshot)
    return snapshot


def load_constitutional_snapshot(
    path: Path,
    state: ConstitutionalState = RS_CONSTITUTIONAL_STATE,
) -> dict[str, Any]:
    if not path.exists():
        raise RuntimeError(f"Snapshot constitucional ausente: {path}. Execute com --refresh-constitutional.")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("snapshotVersion") != CONSTITUTIONAL_SNAPSHOT_VERSION:
        raise RuntimeError(f"Versão do snapshot constitucional incompatível: {payload.get('snapshotVersion')}")
    if payload.get("period") != REFERENCE_PERIOD:
        raise RuntimeError("Snapshot constitucional fora do sexto bimestre")
    snapshot_state = payload.get("stateCode", "RS")
    if snapshot_state != state.state_code:
        raise RuntimeError(
            f"Snapshot constitucional de {snapshot_state}, esperado "
            f"{state.state_code}."
        )
    if payload.get("municipalities") != state.expected_municipality_count:
        raise RuntimeError(
            "Snapshot constitucional com universo municipal divergente: "
            f"{payload.get('municipalities')}, esperado "
            f"{state.expected_municipality_count}."
        )
    sources = payload.get("sources", {})
    siope_years = {
        source.get("referenceYear")
        for source_id, source in sources.items()
        if source_id.startswith("fnde_siope_indicators_odata_")
    }
    rreo_years = {
        source.get("referenceYear")
        for source_id, source in sources.items()
        if source_id.startswith("fnde_siope_rreo_annex8_")
    }
    if not siope_years or not rreo_years or not siope_years.intersection(rreo_years):
        raise RuntimeError(
            "Snapshot constitucional sem par anual SIOPE/RREO."
        )
    return payload


def merge_constitutional_snapshot(
    base_snapshot: dict[str, Any],
    constitutional_snapshot: dict[str, Any],
    state: ConstitutionalState = RS_CONSTITUTIONAL_STATE,
) -> dict[str, Any]:
    merged = copy.deepcopy(base_snapshot)
    merged["snapshotVersion"] = f"{base_snapshot['snapshotVersion']}+{CONSTITUTIONAL_SNAPSHOT_VERSION}"
    merged["dataVersion"] = CONSTITUTIONAL_DATA_VERSION
    merged["generatedAt"] = GENERATED_AT
    merged["stateCode"] = state.state_code
    merged["municipalities"] = state.expected_municipality_count
    merged.setdefault("sources", {}).update(copy.deepcopy(constitutional_snapshot["sources"]))
    merged["constitutionalSnapshotSha256"] = sha256_bytes(canonical_json(constitutional_snapshot))
    merged["constitutionalCrosswalk"] = copy.deepcopy(constitutional_snapshot["crosswalk"])
    return merged


def constitutional_coverage_rows(contracts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts = {
        "reconciled": 0,
        "partial": 0,
        "source_missing": 0,
        "divergent": 0,
        "unavailable": 0,
    }
    for contract in contracts:
        status = contract["dataQuality"]["coverageByDimension"]["constitutionalApplication"]["status"]
        normalized = "divergent" if status == "divergent" else status
        if normalized == "complete":
            counts["reconciled"] += 1
        elif normalized in counts:
            counts[normalized] += 1
        else:
            counts["partial"] += 1
    total = len(contracts)
    source_rows = []
    for source_id in (SIOPE_SOURCE_ID, RREO_SOURCE_ID):
        covered = sum(
            source_id
            in contract["dataQuality"]["coverageByDimension"]["constitutionalApplication"]["availableSourceIds"]
            for contract in contracts
        )
        source_rows.append(
            {
                "reference_year": REFERENCE_YEAR,
                "period": REFERENCE_PERIOD,
                "source_id": source_id,
                "municipalities_expected": total,
                "municipalities_covered": covered,
                "coverage_rate": round(covered / total, 6),
                "municipalities_reconciled": counts["reconciled"],
                "municipalities_partial": counts["partial"],
                "municipalities_source_missing": counts["source_missing"],
                "municipalities_divergent": counts["divergent"],
                "municipalities_unavailable": counts["unavailable"],
            }
        )
    return source_rows


def constitutional_reconciliation_rows(contracts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for contract in sorted(contracts, key=lambda item: item["municipality"]["ibgeCode"]):
        constitutional = contract["constitutionalApplication"]
        for field in (
            "mdeAppliedAmount",
            "mdeAppliedRate",
            "fundebProfessionalRemunerationRate",
        ):
            metric = constitutional[field]
            reconciliation = metric["reconciliation"]
            rows.append(
                {
                    "ibge_code": contract["municipality"]["ibgeCode"],
                    "municipality": contract["municipality"]["name"],
                    "reference_year": constitutional["referenceYear"],
                    "period": constitutional["period"],
                    "concept": field,
                    "financial_stage": metric["siope"]["financialStage"],
                    "unit": metric["siope"]["unit"],
                    "siope_value": metric["siope"]["value"],
                    "rreo_value": metric["rreo"]["value"],
                    "canonical_value": metric["canonical"]["value"],
                    "absolute_difference": reconciliation["absoluteDifference"],
                    "percentage_difference": reconciliation["percentageDifference"],
                    "status": reconciliation["status"],
                    "tolerance_rule_id": reconciliation["toleranceRuleId"],
                }
            )
    return rows


def revision_rows(revision_history_path: Path) -> list[dict[str, Any]]:
    history = _load_revision_history(revision_history_path)
    rows = []
    for event in history.get("events", []):
        rows.append(
            {
                "status": event["status"],
                "ibge_code": event["ibgeCode"],
                "municipality": event["municipality"],
                "reference_year": event["referenceYear"],
                "period": event["period"],
                "source_url": event["sourceUrl"],
                "previous_sha256": event["previousSha256"],
                "detected_sha256": event["detectedSha256"],
                "previous_last_modified": event.get("previousLastModified"),
                "detected_last_modified": event.get("detectedLastModified"),
                "previous_size_bytes": event.get("previousSizeBytes"),
                "detected_size_bytes": event.get("detectedSizeBytes"),
                "detected_at": event["detectedAt"],
                "parser_version": event["parserVersion"],
                "publication_blocked": event["publicationBlocked"],
                "field_differences_json": json.dumps(event["fieldDifferences"], ensure_ascii=False, sort_keys=True),
            }
        )
    return rows


def write_constitutional_reports(
    *,
    coverage_path: Path,
    reconciliation_path: Path,
    revisions_csv_path: Path,
    revision_history_path: Path,
    contracts: list[dict[str, Any]],
) -> dict[str, str]:
    coverage_rows = constitutional_coverage_rows(contracts)
    reconciliation_rows = constitutional_reconciliation_rows(contracts)
    revisions = revision_rows(revision_history_path)
    return {
        "coverage": _write_text_if_changed(
            coverage_path,
            _csv_text(coverage_rows, list(coverage_rows[0])),
        ),
        "reconciliation": _write_text_if_changed(
            reconciliation_path,
            _csv_text(reconciliation_rows, list(reconciliation_rows[0])),
        ),
        "revisions": _write_text_if_changed(
            revisions_csv_path,
            _csv_text(
                revisions,
                [
                    "status",
                    "ibge_code",
                    "municipality",
                    "reference_year",
                    "period",
                    "source_url",
                    "previous_sha256",
                    "detected_sha256",
                    "previous_last_modified",
                    "detected_last_modified",
                    "previous_size_bytes",
                    "detected_size_bytes",
                    "detected_at",
                    "parser_version",
                    "publication_blocked",
                    "field_differences_json",
                ],
            ),
        ),
    }
