from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Any, Iterable, Mapping


REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_PIPELINE_DIR = REPO_ROOT / "data_pipeline"
PUBLIC_DATA_DIR = (REPO_ROOT / "public" / "data").resolve()
PUBLIC_V3_DIR = (PUBLIC_DATA_DIR / "pne2026-diagnostic-v3").resolve()
if str(DATA_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_PIPELINE_DIR))

from src.pne2026_public_diagnostic_v3 import (  # noqa: E402
    CONTRACT,
    CONTRACT_HASH,
    CONTRACT_VERSION,
    PRESENTATION_POLICY_HASH,
    PRESENTATION_POLICY_VERSION,
    PUBLIC_V3_SCHEMA_VERSION,
    validate_pne2026_public_diagnostic_v3,
)
from src.pne_state_context import load_pne_state_context  # noqa: E402
from src.state_publication import resolve_public_data_dir  # noqa: E402


SOURCE_MANIFEST_SCHEMA = "pne2026-public-diagnostic-v3-manifest-v3"
RELEASE_MANIFEST_SCHEMA = "pne2026-public-diagnostic-v3-release-manifest-v3"
POINTER_SCHEMA = "pne2026-diagnostic-release-pointer-v1"
SOURCE_MUNICIPAL_DIR = "municipalities"
RELEASE_MUNICIPAL_DIR = "municipios"
RELEASE_MUNICIPAL_FILE_PATTERN = "municipios/{municipalityId}.json"
EXPECTED_MUNICIPALITIES = 497
CLASSIFICATION_KEYS = frozenset({"advance", "maintain", "unclassified"})
PRIORITY_KEYS = frozenset({"essential", "standard"})
DATA_STATUS_KEYS = frozenset(
    {"available", "unavailable", "not_applicable", "suppressed"}
)
SHA256_LENGTH = 64


def configure_state(state_code: str = "RS") -> None:
    """Configura o destino publicado e o universo da UF antes da promoção."""

    global EXPECTED_MUNICIPALITIES
    global PUBLIC_DATA_DIR
    global PUBLIC_V3_DIR

    state = load_pne_state_context(state_code)
    PUBLIC_DATA_DIR = resolve_public_data_dir(state.state_code).resolve()
    PUBLIC_V3_DIR = (PUBLIC_DATA_DIR / "pne2026-diagnostic-v3").resolve()
    EXPECTED_MUNICIPALITIES = state.expected_municipality_count

RELEASE_MANIFEST_FIELDS = frozenset(
    {
        "schemaVersion",
        "diagnosticSchemaVersion",
        "contractVersion",
        "contractHash",
        "presentationPolicyVersion",
        "presentationPolicyHash",
        "municipalityCount",
        "resultCount",
        "progressResultCount",
        "trackingResultCount",
        "complementaryResultCount",
        "legalReferenceResultCount",
        "monitoringReferenceResultCount",
        "dataStatusCounts",
        "classificationCounts",
        "presentationPriorityCounts",
        "minimumResultsPerMunicipality",
        "maximumResultsPerMunicipality",
        "percentValuesAbove100Count",
        "countValuesAbove100Count",
        "hiddenExcludedCount",
        "aggregateHash",
        "semanticHash",
        "municipalFilePattern",
    }
)
POINTER_FIELDS = frozenset(
    {
        "schemaVersion",
        "releaseId",
        "manifestPath",
        "aggregateHash",
        "contractVersion",
        "contractHash",
        "presentationPolicyVersion",
        "presentationPolicyHash",
    }
)


def _serialized(payload: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _canonical_bytes(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
        allow_nan=False,
    ).encode("utf-8")


def _load_json_bytes(content: bytes, label: str) -> dict[str, Any]:
    def reject_constant(value: str) -> None:
        raise ValueError(f"{label} contém constante JSON inválida: {value}.")

    payload = json.loads(content, parse_constant=reject_constant)
    if not isinstance(payload, dict):
        raise TypeError(f"{label} não contém objeto JSON.")
    return payload


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == SHA256_LENGTH
        and all(character in "0123456789abcdef" for character in value)
    )


def _aggregate_hash(blocks: Iterable[tuple[str, bytes]]) -> str:
    digest = hashlib.sha256()
    for relative_path, block in sorted(blocks):
        identifier = relative_path.replace("\\", "/").encode("utf-8")
        digest.update(len(identifier).to_bytes(4, "big"))
        digest.update(identifier)
        digest.update(len(block).to_bytes(8, "big"))
        digest.update(block)
    return digest.hexdigest()


def _release_identity_block() -> tuple[str, bytes]:
    return (
        "__release_identity__.json",
        _serialized(
            {
                "sourceManifestSchema": SOURCE_MANIFEST_SCHEMA,
                "diagnosticSchemaVersion": PUBLIC_V3_SCHEMA_VERSION,
                "contractVersion": CONTRACT_VERSION,
                "contractHash": CONTRACT_HASH,
                "presentationPolicyVersion": PRESENTATION_POLICY_VERSION,
                "presentationPolicyHash": PRESENTATION_POLICY_HASH,
            }
        ),
    )


def validate_public_destination(destination: Path) -> Path:
    resolved = destination.expanduser().resolve()
    if resolved != PUBLIC_V3_DIR:
        raise ValueError(
            "Destino bloqueado: a promoção só pode escrever em "
            f"{PUBLIC_V3_DIR}."
        )
    return resolved


def _validate_common_manifest_fields(manifest: Mapping[str, Any]) -> None:
    expected = {
        "contractVersion": CONTRACT_VERSION,
        "contractHash": CONTRACT_HASH,
        "presentationPolicyVersion": PRESENTATION_POLICY_VERSION,
        "presentationPolicyHash": PRESENTATION_POLICY_HASH,
    }
    for field, value in expected.items():
        if manifest.get(field) != value:
            raise ValueError(
                f"Manifesto V3 divergente em {field}: "
                f"{manifest.get(field)!r}; esperado {value!r}."
            )


def normalized_manifest_semantics(
    manifest: Mapping[str, Any], *, source_kind: str
) -> dict[str, Any]:
    if source_kind == "staging":
        return {
            "diagnosticSchemaVersion": manifest.get("diagnosticSchemaVersion"),
            "contractVersion": manifest.get("contractVersion"),
            "contractHash": manifest.get("contractHash"),
            "presentationPolicyVersion": manifest.get(
                "presentationPolicyVersion"
            ),
            "presentationPolicyHash": manifest.get("presentationPolicyHash"),
            "municipalityCount": manifest.get("generatedMunicipalityCount"),
            "resultCount": manifest.get("totalResultCount"),
            "progressResultCount": manifest.get("modeCounts", {}).get(
                "progress"
            ),
            "trackingResultCount": manifest.get("modeCounts", {}).get(
                "tracking"
            ),
            "complementaryResultCount": manifest.get("modeCounts", {}).get(
                "complementary"
            ),
            "legalReferenceResultCount": manifest.get(
                "referenceKindCounts", {}
            ).get("legal"),
            "monitoringReferenceResultCount": manifest.get(
                "referenceKindCounts", {}
            ).get("monitoring"),
            "classificationCounts": manifest.get("classificationCounts"),
            "dataStatusCounts": manifest.get("dataStatusCounts"),
            "presentationPriorityCounts": manifest.get(
                "presentationPriorityCounts"
            ),
            "minimumResultsPerMunicipality": manifest.get(
                "minimumResultsPerMunicipality"
            ),
            "maximumResultsPerMunicipality": manifest.get(
                "maximumResultsPerMunicipality"
            ),
            "percentValuesAbove100Count": manifest.get(
                "percentValuesAbove100Count"
            ),
            "countValuesAbove100Count": manifest.get(
                "countValuesAbove100Count"
            ),
            "hiddenExcludedCount": manifest.get("hiddenExcludedCount"),
            "aggregateHash": manifest.get("generationHash"),
        }
    if source_kind == "release":
        return {
            field: manifest.get(field)
            for field in (
                "diagnosticSchemaVersion",
                "contractVersion",
                "contractHash",
                "presentationPolicyVersion",
                "presentationPolicyHash",
                "municipalityCount",
                "resultCount",
                "progressResultCount",
                "trackingResultCount",
                "complementaryResultCount",
                "legalReferenceResultCount",
                "monitoringReferenceResultCount",
                "classificationCounts",
                "dataStatusCounts",
                "presentationPriorityCounts",
                "minimumResultsPerMunicipality",
                "maximumResultsPerMunicipality",
                "percentValuesAbove100Count",
                "countValuesAbove100Count",
                "hiddenExcludedCount",
                "aggregateHash",
            )
        }
    raise ValueError(f"Tipo de manifesto desconhecido: {source_kind}.")


def semantic_manifest_hash(
    manifest: Mapping[str, Any], *, source_kind: str
) -> str:
    return hashlib.sha256(
        _canonical_bytes(
            normalized_manifest_semantics(manifest, source_kind=source_kind)
        )
    ).hexdigest()


def _validate_semantics(semantics: Mapping[str, Any]) -> None:
    expected_identity = {
        "diagnosticSchemaVersion": PUBLIC_V3_SCHEMA_VERSION,
        "contractVersion": CONTRACT_VERSION,
        "contractHash": CONTRACT_HASH,
        "presentationPolicyVersion": PRESENTATION_POLICY_VERSION,
        "presentationPolicyHash": PRESENTATION_POLICY_HASH,
        "municipalityCount": EXPECTED_MUNICIPALITIES,
    }
    for field, expected in expected_identity.items():
        if semantics.get(field) != expected:
            raise ValueError(
                f"Semântica V3 divergente em {field}: "
                f"{semantics.get(field)!r}; esperado {expected!r}."
            )
    numeric_fields = (
        "resultCount",
        "progressResultCount",
        "trackingResultCount",
        "complementaryResultCount",
        "legalReferenceResultCount",
        "monitoringReferenceResultCount",
        "minimumResultsPerMunicipality",
        "maximumResultsPerMunicipality",
        "percentValuesAbove100Count",
        "countValuesAbove100Count",
        "hiddenExcludedCount",
    )
    if any(
        not isinstance(semantics.get(field), int)
        or isinstance(semantics.get(field), bool)
        or semantics[field] < 0
        for field in numeric_fields
    ):
        raise ValueError("Semântica V3 contém contagem inválida.")
    if (
        semantics["resultCount"]
        != semantics["progressResultCount"]
        + semantics["trackingResultCount"]
        + semantics["complementaryResultCount"]
    ):
        raise ValueError("Contagens de modo não reconciliam com resultCount.")
    if (
        semantics["legalReferenceResultCount"] > semantics["progressResultCount"]
        or semantics["monitoringReferenceResultCount"]
        > semantics["trackingResultCount"]
    ):
        raise ValueError("Contagens por tipo de referência excedem os modos.")
    classifications = semantics.get("classificationCounts")
    priorities = semantics.get("presentationPriorityCounts")
    data_statuses = semantics.get("dataStatusCounts")
    if (
        not isinstance(classifications, dict)
        or set(classifications) != CLASSIFICATION_KEYS
        or any(
            not isinstance(value, int)
            or isinstance(value, bool)
            or value < 0
            for value in classifications.values()
        )
        or sum(classifications.values())
        != semantics["legalReferenceResultCount"]
    ):
        raise ValueError("Contagens de classificação V3 inválidas.")
    if (
        not isinstance(priorities, dict)
        or set(priorities) != PRIORITY_KEYS
        or any(
            not isinstance(value, int)
            or isinstance(value, bool)
            or value < 0
            for value in priorities.values()
        )
        or sum(priorities.values()) != semantics["resultCount"]
    ):
        raise ValueError("Contagens de prioridade V3 inválidas.")
    if (
        not isinstance(data_statuses, dict)
        or set(data_statuses) != DATA_STATUS_KEYS
        or any(
            not isinstance(value, int)
            or isinstance(value, bool)
            or value < 0
            for value in data_statuses.values()
        )
        or sum(data_statuses.values()) != semantics["resultCount"]
    ):
        raise ValueError("Contagens de estado V3 inválidas.")
    if (
        semantics["minimumResultsPerMunicipality"]
        > semantics["maximumResultsPerMunicipality"]
    ):
        raise ValueError("Mínimo municipal é maior que o máximo.")
    if not _is_sha256(semantics.get("aggregateHash")):
        raise ValueError("aggregateHash semântico inválido.")


def _release_manifest(source_manifest: Mapping[str, Any]) -> dict[str, Any]:
    semantics = normalized_manifest_semantics(
        source_manifest, source_kind="staging"
    )
    semantic_hash = hashlib.sha256(_canonical_bytes(semantics)).hexdigest()
    return {
        "schemaVersion": RELEASE_MANIFEST_SCHEMA,
        **semantics,
        "semanticHash": semantic_hash,
        "municipalFilePattern": RELEASE_MUNICIPAL_FILE_PATTERN,
    }


def _validate_payload_collection(
    municipal_files: Mapping[str, bytes], *, physical_directory: str
) -> dict[str, Any]:
    if len(municipal_files) != EXPECTED_MUNICIPALITIES:
        raise ValueError(
            f"Pacote V3 contém {len(municipal_files)} arquivos municipais; "
            f"esperados {EXPECTED_MUNICIPALITIES}."
        )

    result_counts: list[int] = []
    progress = 0
    tracking = 0
    complementary = 0
    classifications: Counter[str] = Counter()
    priorities: Counter[str] = Counter()
    data_statuses: Counter[str] = Counter()
    legal_references = 0
    monitoring_references = 0
    above_100_by_unit: Counter[str] = Counter()
    seen_municipalities: set[str] = set()
    logical_blocks: list[tuple[str, bytes]] = []
    for relative_path, content in sorted(municipal_files.items()):
        path = Path(relative_path)
        if (
            len(path.parts) != 2
            or path.parts[0] != physical_directory
            or path.suffix != ".json"
            or not path.stem.isdigit()
        ):
            raise ValueError(f"Nome municipal V3 inválido: {relative_path}.")
        payload = validate_pne2026_public_diagnostic_v3(
            _load_json_bytes(content, relative_path)
        )
        municipality_id = str(payload["municipality"]["id"])
        if municipality_id != path.stem:
            raise ValueError(
                f"{relative_path}: id municipal {municipality_id} divergente."
            )
        if municipality_id in seen_municipalities:
            raise ValueError(f"Município V3 duplicado: {municipality_id}.")
        seen_municipalities.add(municipality_id)
        summary = payload["summary"]
        result_counts.append(summary["visibleResultCount"])
        progress += summary["progressResultCount"]
        tracking += summary["trackingResultCount"]
        complementary += summary["complementaryResultCount"]
        classifications.update(summary["classificationCounts"])
        priorities.update(summary["presentationPriorityCounts"])
        data_statuses.update(summary["dataStatusCounts"])
        legal_references += summary["legalReferenceResultCount"]
        monitoring_references += summary["monitoringReferenceResultCount"]
        for result in payload["results"]:
            if (
                isinstance(result.get("value"), (int, float))
                and not isinstance(result.get("value"), bool)
                and result["value"] > 100
            ):
                unit = CONTRACT["indicators"][result["indicatorId"]]["unit"]
                above_100_by_unit[unit] += 1
        logical_blocks.append(
            (f"{SOURCE_MUNICIPAL_DIR}/{path.name}", content)
        )

    return {
        "municipalityCount": len(seen_municipalities),
        "resultCount": sum(result_counts),
        "progressResultCount": progress,
        "trackingResultCount": tracking,
        "complementaryResultCount": complementary,
        "legalReferenceResultCount": legal_references,
        "monitoringReferenceResultCount": monitoring_references,
        "dataStatusCounts": {
            key: data_statuses[key]
            for key in ("available", "unavailable", "not_applicable", "suppressed")
        },
        "classificationCounts": {
            key: classifications[key]
            for key in ("advance", "maintain", "unclassified")
        },
        "presentationPriorityCounts": {
            key: priorities[key] for key in ("essential", "standard")
        },
        "minimumResultsPerMunicipality": min(result_counts, default=0),
        "maximumResultsPerMunicipality": max(result_counts, default=0),
        "percentValuesAbove100Count": above_100_by_unit["percent"],
        "countValuesAbove100Count": above_100_by_unit["count"],
        "aggregateHash": _aggregate_hash(
            [*logical_blocks, _release_identity_block()]
        ),
    }


def validate_source_package(source: Path) -> dict[str, Any]:
    root = source.expanduser().resolve()
    if root == PUBLIC_DATA_DIR or PUBLIC_DATA_DIR in root.parents:
        raise ValueError("A origem da promoção deve estar fora de public/data.")
    if not root.is_dir():
        raise FileNotFoundError(root)

    files = {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }
    manifest_bytes = files.pop("manifest.json", None)
    if manifest_bytes is None:
        raise ValueError("Manifesto de staging V3 ausente.")
    manifest = _load_json_bytes(manifest_bytes, "manifest.json")
    if manifest.get("schemaVersion") != SOURCE_MANIFEST_SCHEMA:
        raise ValueError("Schema do manifesto de staging V3 divergente.")
    _validate_common_manifest_fields(manifest)
    if manifest.get("diagnosticSchemaVersion") != PUBLIC_V3_SCHEMA_VERSION:
        raise ValueError("Schema diagnóstico do staging V3 divergente.")
    for field in (
        "invalidFileCount",
        "duplicateRelationCount",
        "orphanFileCount",
    ):
        if manifest.get(field) != 0:
            raise ValueError(f"Manifesto de staging divergente em {field}.")

    observed = _validate_payload_collection(
        files, physical_directory=SOURCE_MUNICIPAL_DIR
    )
    aggregate_hash = observed["aggregateHash"]
    if manifest.get("generationHash") != aggregate_hash:
        raise ValueError("Hash agregado do staging V3 diverge dos payloads.")
    semantics = normalized_manifest_semantics(
        manifest, source_kind="staging"
    )
    _validate_semantics(semantics)
    if observed != {field: semantics[field] for field in observed}:
        raise ValueError("Manifesto de staging V3 diverge dos payloads.")
    release_manifest = _release_manifest(manifest)
    if (
        semantic_manifest_hash(manifest, source_kind="staging")
        != release_manifest["semanticHash"]
    ):
        raise AssertionError("Hash semântico do staging não foi preservado.")
    return {
        "source": root,
        "municipalFiles": files,
        "sourceManifest": manifest,
        "sourceManifestSha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "releaseManifest": release_manifest,
        "releaseId": aggregate_hash,
    }


def _read_release_files(release_root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(release_root).as_posix(): path.read_bytes()
        for path in sorted(release_root.rglob("*"))
        if path.is_file()
    }


def validate_release_package(
    release_root: Path, *, expected_release_id: str | None = None
) -> dict[str, Any]:
    root = release_root.expanduser().resolve()
    if not root.is_dir():
        raise FileNotFoundError(root)
    release_id = expected_release_id or root.name
    if not _is_sha256(release_id):
        raise ValueError(f"Diretório de release inválido: {release_id}.")
    files = _read_release_files(root)
    manifest_bytes = files.pop("manifest.json", None)
    if manifest_bytes is None:
        raise ValueError("Manifesto do release V3 ausente.")
    manifest = _load_json_bytes(manifest_bytes, "manifest.json")
    if set(manifest) != RELEASE_MANIFEST_FIELDS:
        raise ValueError("Allowlist do manifesto do release V3 divergente.")
    if manifest.get("schemaVersion") != RELEASE_MANIFEST_SCHEMA:
        raise ValueError("Schema do manifesto do release V3 divergente.")
    _validate_common_manifest_fields(manifest)
    if manifest.get("aggregateHash") != release_id:
        raise ValueError("Manifesto do release diverge do nome do diretório.")
    if manifest.get("municipalFilePattern") != RELEASE_MUNICIPAL_FILE_PATTERN:
        raise ValueError("Padrão de arquivo municipal do release divergente.")

    observed = _validate_payload_collection(
        files, physical_directory=RELEASE_MUNICIPAL_DIR
    )
    semantics = normalized_manifest_semantics(
        manifest, source_kind="release"
    )
    _validate_semantics(semantics)
    if observed != {
        field: semantics[field]
        for field in observed
    }:
        raise ValueError("Manifesto do release diverge dos payloads.")
    computed_semantic_hash = semantic_manifest_hash(
        manifest, source_kind="release"
    )
    if manifest.get("semanticHash") != computed_semantic_hash:
        raise ValueError("Hash semântico do manifesto do release divergente.")
    return {
        "releaseRoot": str(root),
        "releaseId": release_id,
        "manifest": manifest,
        "manifestSha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "semanticHash": computed_semantic_hash,
        "fileCount": len(files) + 1,
    }


def build_current_pointer(release_manifest: Mapping[str, Any]) -> dict[str, Any]:
    release_id = release_manifest.get("aggregateHash")
    if not _is_sha256(release_id):
        raise ValueError("Release sem aggregateHash válido.")
    return {
        "schemaVersion": POINTER_SCHEMA,
        "releaseId": release_id,
        "manifestPath": f"releases/{release_id}/manifest.json",
        "aggregateHash": release_id,
        "contractVersion": release_manifest["contractVersion"],
        "contractHash": release_manifest["contractHash"],
        "presentationPolicyVersion": release_manifest[
            "presentationPolicyVersion"
        ],
        "presentationPolicyHash": release_manifest[
            "presentationPolicyHash"
        ],
    }


def validate_current_pointer(
    candidate: Mapping[str, Any], destination: Path
) -> dict[str, Any]:
    if set(candidate) != POINTER_FIELDS:
        raise ValueError("Allowlist de current.json divergente.")
    if candidate.get("schemaVersion") != POINTER_SCHEMA:
        raise ValueError("Schema de current.json divergente.")
    release_id = candidate.get("releaseId")
    if not _is_sha256(release_id):
        raise ValueError("releaseId de current.json inválido.")
    if candidate.get("aggregateHash") != release_id:
        raise ValueError("aggregateHash de current.json divergente.")
    expected_path = f"releases/{release_id}/manifest.json"
    manifest_path = candidate.get("manifestPath")
    if (
        manifest_path != expected_path
        or ".." in manifest_path
        or manifest_path.startswith(("/", "\\"))
        or ":" in manifest_path
    ):
        raise ValueError("manifestPath de current.json não está confinado.")
    _validate_common_manifest_fields(candidate)
    release = validate_release_package(
        destination / "releases" / release_id
    )
    if release["manifest"] != _load_json_bytes(
        (destination / manifest_path).read_bytes(), manifest_path
    ):
        raise ValueError("Manifesto apontado diverge do release validado.")
    return {
        "pointer": dict(candidate),
        "release": release,
    }


def validate_public_package(destination: Path) -> dict[str, Any]:
    root = validate_public_destination(destination)
    current_path = root / "current.json"
    if not current_path.is_file():
        raise FileNotFoundError(current_path)
    current_bytes = current_path.read_bytes()
    current = _load_json_bytes(current_bytes, "current.json")
    validated = validate_current_pointer(current, root)
    return {
        "destination": str(root),
        "currentSha256": hashlib.sha256(current_bytes).hexdigest(),
        **validated["release"],
    }


def _write_release(
    prepared: Mapping[str, Any], destination: Path
) -> dict[str, Any]:
    release_id = prepared["releaseId"]
    release_root = destination / "releases" / release_id
    release_manifest_bytes = _serialized(prepared["releaseManifest"])
    if release_root.exists():
        validated = validate_release_package(release_root)
        existing = _read_release_files(release_root)
        expected = {
            f"{RELEASE_MUNICIPAL_DIR}/{Path(path).name}": content
            for path, content in prepared["municipalFiles"].items()
        }
        expected["manifest.json"] = release_manifest_bytes
        if existing != expected:
            raise ValueError(
                "Release existente com o mesmo hash contém bytes divergentes."
            )
        return validated

    destination.mkdir(parents=True, exist_ok=True)
    releases_root = destination / "releases"
    releases_root.mkdir(exist_ok=True)
    temporary = Path(
        tempfile.mkdtemp(prefix=f".{release_id}.tmp-", dir=releases_root)
    )
    created_final = False
    try:
        for relative_path, content in sorted(
            prepared["municipalFiles"].items()
        ):
            output = temporary / RELEASE_MUNICIPAL_DIR / Path(relative_path).name
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(content)
        (temporary / "manifest.json").write_bytes(release_manifest_bytes)

        temporary_validation_root = releases_root / release_id
        validate_release_package(
            temporary, expected_release_id=release_id
        )
        # Não dependemos de mover uma árvore não vazia para o nome final: o
        # diretório final é criado vazio e recebe arquivos já validados, com o
        # manifesto por último. O release ainda não está ativo nessa fase.
        temporary_validation_root.mkdir()
        created_final = True
        (temporary_validation_root / RELEASE_MUNICIPAL_DIR).mkdir()
        for source_file in sorted(
            (temporary / RELEASE_MUNICIPAL_DIR).glob("*.json")
        ):
            shutil.copyfile(
                source_file,
                temporary_validation_root
                / RELEASE_MUNICIPAL_DIR
                / source_file.name,
            )
        shutil.copyfile(
            temporary / "manifest.json",
            temporary_validation_root / "manifest.json",
        )
        validated = validate_release_package(temporary_validation_root)
        shutil.rmtree(temporary)
        return validated
    except Exception:
        if temporary.exists():
            shutil.rmtree(temporary)
        if created_final and release_root.exists():
            shutil.rmtree(release_root)
        raise


def _write_current_atomically(
    destination: Path, pointer: Mapping[str, Any]
) -> dict[str, Any]:
    validate_current_pointer(pointer, destination)
    destination.mkdir(parents=True, exist_ok=True)
    current_path = destination / "current.json"
    previous = current_path.read_bytes() if current_path.exists() else None
    temporary = destination / f".current.{os.getpid()}.tmp"
    if temporary.exists():
        raise FileExistsError(temporary)
    temporary.write_bytes(_serialized(pointer))
    try:
        _load_json_bytes(temporary.read_bytes(), temporary.name)
        os.replace(temporary, current_path)
    except Exception:
        if temporary.exists():
            temporary.unlink()
        observed = current_path.read_bytes() if current_path.exists() else None
        if observed != previous:
            raise RuntimeError(
                "Falha atômica alterou current.json inesperadamente."
            )
        raise
    return validate_public_package(destination)


def prune_inactive_releases(
    destination: Path,
    *,
    check: bool = False,
) -> dict[str, Any]:
    target = validate_public_destination(destination)
    active = validate_public_package(target)
    active_release_id = active["releaseId"]
    releases_root = (target / "releases").resolve()
    if releases_root.parent != target or not releases_root.is_dir():
        raise ValueError("Diretório de releases inválido.")
    inactive = [
        path
        for path in sorted(releases_root.iterdir())
        if path.is_dir()
        and _is_sha256(path.name)
        and path.name != active_release_id
        and path.resolve().parent == releases_root
    ]
    file_count = sum(
        1 for root in inactive for path in root.rglob("*") if path.is_file()
    )
    byte_count = sum(
        path.stat().st_size
        for root in inactive
        for path in root.rglob("*")
        if path.is_file()
    )
    report = {
        "mode": "check-prune" if check else "prune",
        "destination": str(target),
        "releaseId": active_release_id,
        "inactiveReleaseCount": len(inactive),
        "removedFileCount": file_count,
        "removedBytes": byte_count,
    }
    if not check:
        for root in inactive:
            shutil.rmtree(root)
        remaining = [path for path in releases_root.iterdir() if path.is_dir()]
        if [path.name for path in remaining] != [active_release_id]:
            raise RuntimeError("A limpeza não preservou exclusivamente a release ativa.")
    return report


def promote(
    source: Path,
    destination: Path,
    *,
    check: bool = False,
) -> dict[str, Any]:
    target = validate_public_destination(destination)
    prepared = validate_source_package(source)
    release_id = prepared["releaseId"]
    report = {
        "mode": "check" if check else "promote",
        "source": str(prepared["source"]),
        "destination": str(target),
        "sourceManifestSha256": prepared["sourceManifestSha256"],
        "releaseId": release_id,
        "semanticHash": prepared["releaseManifest"]["semanticHash"],
        "municipalityCount": prepared["releaseManifest"]["municipalityCount"],
        "resultCount": prepared["releaseManifest"]["resultCount"],
    }
    release_root = target / "releases" / release_id
    if check:
        if release_root.exists():
            release = validate_release_package(release_root)
            if release["semanticHash"] != report["semanticHash"]:
                raise ValueError("Release existente diverge semanticamente.")
        if (target / "current.json").exists():
            current = _load_json_bytes(
                (target / "current.json").read_bytes(), "current.json"
            )
            active_release_id = current.get("releaseId")
            if not _is_sha256(active_release_id):
                raise ValueError("releaseId ativo inválido.")
            report["activeReleaseId"] = active_release_id
        return report

    release = _write_release(prepared, target)
    activated = _write_current_atomically(
        target, build_current_pointer(release["manifest"])
    )
    cleanup = prune_inactive_releases(target)
    return {
        **report,
        **activated,
        "inactiveReleaseCount": cleanup["inactiveReleaseCount"],
        "removedFileCount": cleanup["removedFileCount"],
        "removedBytes": cleanup["removedBytes"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Valida, publica e ativa releases imutáveis do diagnóstico PNE V3."
        )
    )
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--source-dir", type=Path)
    action.add_argument("--prune-inactive", action="store_true")
    parser.add_argument("--destination-dir", required=True, type=Path)
    parser.add_argument("--state", default="RS")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Valida sem criar release nem alterar current.json.",
    )
    args = parser.parse_args()
    configure_state(args.state)
    if args.source_dir:
        report = promote(
            args.source_dir, args.destination_dir, check=args.check
        )
    else:
        report = prune_inactive_releases(
            args.destination_dir, check=args.check
        )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
