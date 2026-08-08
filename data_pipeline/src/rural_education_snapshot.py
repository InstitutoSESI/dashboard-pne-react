"""Leitura fail-closed dos snapshots estaduais de cobertura educacional rural."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from typing import Any

from src.config import DATA_PIPELINE_DIR
from src.municipality_registry import MunicipalityRegistry
from src.state_config import StateConfig


SNAPSHOT_ROOT = DATA_PIPELINE_DIR / "data" / "rural_education_coverage"
RAW_FILENAMES = (
    "sidra_10089_metadata.json",
    "sidra_10089_response.json",
    "sidra_9606_metadata.json",
    "sidra_9606_response.json",
)
ANALYTICAL_FILENAMES = (
    *RAW_FILENAMES,
    "population_estimates.json",
    "rural_enrollments.json",
)
ENROLLMENT_AGE_GROUPS = ("4_5", "6_10", "11_14", "15_17", "4_17")
SNAPSHOT_SCHEMA_VERSION = 1


class RuralEducationSnapshotError(ValueError):
    """Indica snapshot rural incompleto, misto ou incompatível com a UF."""


def resolve_rural_education_snapshot_dir(
    state_config: StateConfig,
    *,
    snapshot_root: Path = SNAPSHOT_ROOT,
) -> Path:
    return Path(snapshot_root) / state_config.state_code.lower()


def snapshot_digest(directory: Path) -> str:
    digest = hashlib.sha256()
    for filename in ANALYTICAL_FILENAMES:
        path = Path(directory) / filename
        if not path.is_file():
            raise FileNotFoundError(f"Snapshot rural incompleto: {path}.")
        digest.update(filename.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _load_json(path: Path, expected_type: type) -> Any:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuralEducationSnapshotError(
            f"Snapshot rural inválido em {path}: JSON malformado: {exc}."
        ) from exc
    if not isinstance(payload, expected_type):
        raise RuralEducationSnapshotError(
            f"Snapshot rural inválido em {path}: esperado {expected_type.__name__}."
        )
    return payload


def _validate_manifest(
    manifest: dict[str, Any],
    *,
    directory: Path,
    state_config: StateConfig,
    expected_years: tuple[int, ...],
) -> None:
    if manifest.get("schemaVersion") != SNAPSHOT_SCHEMA_VERSION:
        raise RuralEducationSnapshotError("Snapshot rural possui schemaVersion desconhecido.")
    if manifest.get("state") != state_config.state_code:
        raise RuralEducationSnapshotError(
            "Snapshot rural diverge da UF solicitada: "
            f"manifesto={manifest.get('state')!r}, esperado={state_config.state_code!r}."
        )
    if manifest.get("municipalityCount") != state_config.expected_municipality_count:
        raise RuralEducationSnapshotError(
            "Snapshot rural diverge da contagem municipal configurada."
        )
    if manifest.get("years") != list(expected_years):
        raise RuralEducationSnapshotError(
            f"Snapshot rural diverge dos anos esperados: {list(expected_years)}."
        )
    declared_digest = manifest.get("snapshotSha256")
    observed_digest = snapshot_digest(directory)
    if not isinstance(declared_digest, str) or declared_digest != observed_digest:
        raise RuralEducationSnapshotError(
            "Snapshot rural falhou na verificação de integridade SHA-256."
        )

    sources = (manifest.get("population") or {}).get("sources") or {}
    marker = f"N3[{state_config.municipality_ibge_prefix}]"
    for source_key in ("ruralGroups", "exactAgeWeights"):
        query_url = (sources.get(source_key) or {}).get("queryUrl")
        if not isinstance(query_url, str) or marker not in query_url:
            raise RuralEducationSnapshotError(
                f"Snapshot rural não comprova o recorte estadual em {source_key}."
            )


def _validate_population_rows(
    rows: list[dict[str, Any]],
    registry: MunicipalityRegistry,
) -> None:
    ids = [row.get("id_municipio") for row in rows]
    if any(not isinstance(value, str) or re.fullmatch(r"\d{7}", value) is None for value in ids):
        raise RuralEducationSnapshotError(
            "Snapshot rural contém código municipal inválido na população."
        )
    if len(ids) != len(set(ids)) or set(ids) != registry.ids:
        raise RuralEducationSnapshotError(
            "Snapshot rural possui universo municipal inválido na população."
        )


def _validate_enrollment_rows(
    rows: list[dict[str, Any]],
    registry: MunicipalityRegistry,
    expected_years: tuple[int, ...],
) -> None:
    expected = {
        (year, municipality_id, age_group)
        for year in expected_years
        for municipality_id in registry.ids
        for age_group in ENROLLMENT_AGE_GROUPS
    }
    observed: list[tuple[int, str, str]] = []
    for row in rows:
        municipality_id = row.get("id_municipio")
        year = row.get("ano")
        age_group = row.get("faixa_etaria")
        if (
            isinstance(year, bool)
            or not isinstance(year, int)
            or not isinstance(municipality_id, str)
            or not isinstance(age_group, str)
        ):
            raise RuralEducationSnapshotError(
                "Snapshot rural contém chave inválida nas matrículas."
            )
        observed.append((year, municipality_id, age_group))
    if len(observed) != len(set(observed)) or set(observed) != expected:
        raise RuralEducationSnapshotError(
            "Snapshot rural possui conjunto inválido de anos, municípios ou faixas."
        )


def load_rural_education_snapshot(
    state_config: StateConfig,
    registry: MunicipalityRegistry,
    *,
    expected_years: tuple[int, ...],
    snapshot_dir: Path | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]] | None:
    """Retorna as duas fontes rurais quando o snapshot estadual existe e é íntegro."""

    directory = Path(snapshot_dir) if snapshot_dir is not None else (
        resolve_rural_education_snapshot_dir(state_config)
    )
    if not directory.exists():
        return None
    required = ("manifest.json", *ANALYTICAL_FILENAMES)
    missing = [filename for filename in required if not (directory / filename).is_file()]
    if missing:
        raise RuralEducationSnapshotError(
            f"Snapshot rural estadual incompleto em {directory}: ausentes={missing}."
        )

    manifest = _load_json(directory / "manifest.json", dict)
    population_rows = _load_json(directory / "population_estimates.json", list)
    enrollment_rows = _load_json(directory / "rural_enrollments.json", list)
    if not all(isinstance(row, dict) for row in (*population_rows, *enrollment_rows)):
        raise RuralEducationSnapshotError("Snapshot rural contém linha que não é objeto.")

    _validate_manifest(
        manifest,
        directory=directory,
        state_config=state_config,
        expected_years=expected_years,
    )
    _validate_population_rows(population_rows, registry)
    _validate_enrollment_rows(enrollment_rows, registry, expected_years)
    if (manifest.get("population") or {}).get("rows") != len(population_rows):
        raise RuralEducationSnapshotError("Manifesto rural diverge das linhas de população.")
    if (manifest.get("enrollments") or {}).get("rows") != len(enrollment_rows):
        raise RuralEducationSnapshotError("Manifesto rural diverge das linhas de matrículas.")
    return population_rows, enrollment_rows, manifest
