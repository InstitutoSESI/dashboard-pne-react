"""Infraestrutura comum das ingestões isoladas da macro-rodada do PNE.

Este módulo só é usado na preparação offline. A aplicação e o build consomem
exclusivamente os snapshots normalizados já materializados.
"""

from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import tempfile
import unicodedata
from typing import Any, Mapping


REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = REPO_ROOT / "data_pipeline" / "data" / "pne_macro_sources"
MUNICIPALITY_INDEX = REPO_ROOT / "public" / "data" / "municipios_index.json"
EXPECTED_MUNICIPALITIES = 497
NORMALIZED_SCHEMA = "pne-macro-source-normalized-v1"
MANIFEST_SCHEMA = "pne-macro-source-manifest-v1"


def file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_bytes(value: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def normalize_name(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return " ".join(
        "".join(char if char.isalnum() else " " for char in text.casefold()).split()
    )


def load_municipality_universe(
    index_path: Path = MUNICIPALITY_INDEX,
) -> tuple[dict[str, str], dict[str, str]]:
    payload = json.loads(index_path.read_text(encoding="utf-8"))
    entries = payload.get("municipios") or []
    if len(entries) != EXPECTED_MUNICIPALITIES:
        raise ValueError(
            "O universo municipal deve conter exatamente "
            f"{EXPECTED_MUNICIPALITIES} municípios."
        )
    names_by_id: dict[str, str] = {}
    ids_by_name: dict[str, str] = {}
    for entry in entries:
        municipality_id = str(entry.get("id_municipio") or "")
        name = str(entry.get("nome") or "")
        normalized_name = normalize_name(name)
        if (
            len(municipality_id) != 7
            or not municipality_id.isdigit()
            or not normalized_name
        ):
            raise ValueError(f"Município inválido no universo: {entry!r}")
        if municipality_id in names_by_id or normalized_name in ids_by_name:
            raise ValueError(f"Município duplicado no universo: {entry!r}")
        names_by_id[municipality_id] = name
        ids_by_name[normalized_name] = municipality_id
    return dict(sorted(names_by_id.items())), ids_by_name


def normalized_snapshot(
    *,
    source_id: str,
    edition: str,
    records: Mapping[str, Mapping[str, Any]],
    municipality_names: Mapping[str, str],
) -> dict[str, Any]:
    if len(municipality_names) != EXPECTED_MUNICIPALITIES:
        raise ValueError(
            f"{source_id}: universo deve conter {EXPECTED_MUNICIPALITIES} municípios."
        )
    if set(records) != set(municipality_names):
        missing = sorted(set(municipality_names) - set(records))
        extra = sorted(set(records) - set(municipality_names))
        raise ValueError(
            f"{source_id}: cobertura municipal inválida; "
            f"ausentes={missing[:5]}, extras={extra[:5]}."
        )
    normalized_records: dict[str, Any] = {}
    for municipality_id in sorted(records):
        record = dict(records[municipality_id])
        if record.get("municipalityId") != municipality_id:
            raise ValueError(f"{source_id}: identidade divergente em {municipality_id}.")
        record.setdefault("municipalityName", municipality_names[municipality_id])
        normalized_records[municipality_id] = record
    return {
        "schemaVersion": NORMALIZED_SCHEMA,
        "sourceId": source_id,
        "edition": edition,
        "municipalityCount": EXPECTED_MUNICIPALITIES,
        "records": normalized_records,
    }


def write_source_snapshot(
    *,
    destination: Path,
    raw_files: Mapping[str, Path],
    normalized: Mapping[str, Any] | None,
    manifest: Mapping[str, Any],
) -> Path:
    """Promove a fonte de forma transacional, preservando apenas o lote completo."""

    destination = destination.resolve()
    data_root = DATA_ROOT.resolve()
    if destination != data_root and data_root not in destination.parents:
        raise ValueError(f"Destino fora de {data_root}: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(
        tempfile.mkdtemp(
            prefix=f".{destination.name}.tmp-",
            dir=destination.parent,
        )
    )
    try:
        raw_root = stage / "raw"
        raw_root.mkdir(parents=True)
        for relative_name, source in sorted(raw_files.items()):
            source_path = source.resolve()
            if not source_path.is_file():
                raise FileNotFoundError(source_path)
            target = raw_root / relative_name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, target)
        if normalized is not None:
            (stage / "normalized.json").write_bytes(canonical_json_bytes(normalized))
        (stage / "manifest.json").write_bytes(canonical_json_bytes(manifest))

        backup = destination.with_name(f".{destination.name}.previous")
        if backup.exists():
            shutil.rmtree(backup)
        if destination.exists():
            os.replace(destination, backup)
        os.replace(stage, destination)
        if backup.exists():
            shutil.rmtree(backup)
        return destination
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise


def raw_file_entry(
    *,
    logical_name: str,
    path: Path,
    official_url: str,
) -> dict[str, Any]:
    return {
        "logicalName": logical_name,
        "fileName": path.name,
        "officialUrl": official_url,
        "size": path.stat().st_size,
        "sha256": file_sha256(path),
    }
