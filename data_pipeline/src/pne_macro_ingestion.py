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
from typing import Any, Mapping

from .config import DATA_PIPELINE_DIR
from .municipality_registry import (
    MunicipalityRegistryError,
    load_municipality_registry,
    normalize_municipality_name,
)
from .state_config import DEFAULT_STATE_CODE, load_state_config

DATA_ROOT = DATA_PIPELINE_DIR / "data" / "pne_macro_sources"
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
    """Alias de compatibilidade para a normalização municipal canônica."""

    return normalize_municipality_name(value)


def load_municipality_universe(
    state_code: str = DEFAULT_STATE_CODE,
) -> tuple[dict[str, str], dict[str, str]]:
    state_config = load_state_config(state_code)
    registry = load_municipality_registry(state_config)
    names_by_id = dict(sorted(registry.names_by_id.items()))
    ids_by_name: dict[str, str] = {}
    for normalized_name, municipality_ids in registry.ids_by_normalized_name.items():
        if len(municipality_ids) != 1:
            raise MunicipalityRegistryError(
                "O contrato legado de nomes do PNE exige resolução única; "
                f"nome normalizado ambíguo {normalized_name!r}."
            )
        ids_by_name[normalized_name] = municipality_ids[0]
    return names_by_id, ids_by_name


def normalized_snapshot(
    *,
    source_id: str,
    edition: str,
    records: Mapping[str, Mapping[str, Any]],
    municipality_names: Mapping[str, str],
    state_code: str = DEFAULT_STATE_CODE,
) -> dict[str, Any]:
    state_config = load_state_config(state_code)
    registry = load_municipality_registry(state_config)
    expected_names = dict(registry.names_by_id)
    if dict(municipality_names) != expected_names:
        missing = sorted(registry.ids - set(municipality_names))
        extra = sorted(set(municipality_names) - registry.ids)
        renamed = sorted(
            municipality_id
            for municipality_id in registry.ids & set(municipality_names)
            if municipality_names[municipality_id] != expected_names[municipality_id]
        )
        raise ValueError(
            f"{source_id}: universo municipal diverge do registro de {state_code}; "
            f"ausentes={missing[:5]}, extras={extra[:5]}, nomes={renamed[:5]}."
        )
    if set(records) != registry.ids:
        missing = sorted(registry.ids - set(records))
        extra = sorted(set(records) - registry.ids)
        raise ValueError(
            f"{source_id}: cobertura municipal inválida; "
            f"ausentes={missing[:5]}, extras={extra[:5]}."
        )
    normalized_records: dict[str, Any] = {}
    for municipality_id in sorted(records):
        record = dict(records[municipality_id])
        if record.get("municipalityId") != municipality_id:
            raise ValueError(f"{source_id}: identidade divergente em {municipality_id}.")
        expected_name = expected_names[municipality_id]
        if record.get("municipalityName") not in {None, expected_name}:
            raise ValueError(f"{source_id}: nome municipal divergente em {municipality_id}.")
        record.setdefault("municipalityName", expected_name)
        normalized_records[municipality_id] = record
    return {
        "schemaVersion": NORMALIZED_SCHEMA,
        "sourceId": source_id,
        "edition": edition,
        "municipalityCount": registry.municipality_count,
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
