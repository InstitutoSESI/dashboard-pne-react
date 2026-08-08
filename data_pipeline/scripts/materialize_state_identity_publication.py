from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Any


DATA_PIPELINE_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = DATA_PIPELINE_DIR.parent
if str(DATA_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_PIPELINE_DIR))

from src.identity_publication import (  # noqa: E402
    IdentityPublicationError,
    build_identity_publication_files,
    promote_staged_publication,
    validate_identity_publication,
    write_staged_publication,
)
from src.municipality_registry import (  # noqa: E402
    MunicipalityRegistry,
    MunicipalityRegistryError,
    load_municipality_registry,
)
from src.state_config import StateConfig, StateConfigError, load_state_config  # noqa: E402
from src.state_publication import (  # noqa: E402
    StatePublication,
    StatePublicationError,
    load_state_publication,
)


SOURCE_SCHEMA_VERSION = "municipality-registry-source-v1"
STAGING_PARENT = DATA_PIPELINE_DIR / ".staging" / "identity-publication"


class SourceManifestError(ValueError):
    """Indica que a proveniência do cadastro municipal não foi comprovada."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _repo_relative_path(path: Path) -> str:
    resolved_root = REPO_ROOT.resolve()
    resolved = path.resolve()
    if resolved_root not in resolved.parents:
        raise SourceManifestError(f"Fonte fora do repositório: {resolved}.")
    return resolved.relative_to(resolved_root).as_posix()


def _read_source_manifest(state_code: str) -> tuple[Path, dict[str, Any]]:
    path = (
        DATA_PIPELINE_DIR
        / "data"
        / "municipality_registry_sources"
        / state_code.lower()
        / "manifest.json"
    )
    if not path.is_file():
        raise FileNotFoundError(f"Manifesto de origem ausente: {path}.")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SourceManifestError(f"Manifesto de origem malformado em {path}: {exc}.") from exc
    if not isinstance(payload, dict):
        raise SourceManifestError("Manifesto de origem deve ser um objeto JSON.")
    return path, payload


def _validate_source_manifest(
    manifest_path: Path,
    manifest: dict[str, Any],
    *,
    publication: StatePublication,
    state_config: StateConfig,
    registry: MunicipalityRegistry,
) -> dict[str, str]:
    if manifest.get("schemaVersion") != SOURCE_SCHEMA_VERSION:
        raise SourceManifestError("Schema do manifesto de origem desconhecido.")
    expected = {
        "stateCode": state_config.state_code,
        "stateIbgeCode": state_config.municipality_ibge_prefix,
        "provider": "IBGE",
    }
    for field, value in expected.items():
        if manifest.get(field) != value:
            raise SourceManifestError(
                f"Manifesto de origem diverge em {field}: {manifest.get(field)!r}."
            )

    coverage = manifest.get("coverage")
    if not isinstance(coverage, dict) or coverage.get("expectedMunicipalities") != registry.municipality_count:
        raise SourceManifestError("Cobertura do manifesto diverge do registro municipal.")
    for field in ("observedMunicipalities", "uniqueIbgeCodes", "uniqueNames", "uniqueSlugs"):
        if coverage.get(field) != registry.municipality_count:
            raise SourceManifestError(f"Cobertura municipal inválida em {field}.")
    if coverage.get("ibgePrefix") != state_config.municipality_ibge_prefix:
        raise SourceManifestError("Prefixo IBGE da cobertura diverge da configuração estadual.")

    normalization = manifest.get("normalization")
    if not isinstance(normalization, dict):
        raise SourceManifestError("Bloco de normalização ausente no manifesto.")
    configured_paths = {
        "stateConfigPath": publication.state_config_path,
        "municipalityRegistryPath": publication.municipality_registry_path,
    }
    configured_hashes = {
        "stateConfigSha256": publication.state_config_path,
        "municipalityRegistrySha256": publication.municipality_registry_path,
    }
    for field, path in configured_paths.items():
        if normalization.get(field) != _repo_relative_path(path):
            raise SourceManifestError(f"Manifesto aponta {field} diferente da publicação.")
    for field, path in configured_hashes.items():
        if normalization.get(field) != _sha256(path):
            raise SourceManifestError(f"Hash divergente no manifesto: {field}.")

    raw_snapshot = manifest.get("rawSnapshot")
    http = manifest.get("http")
    if not isinstance(raw_snapshot, dict) or not isinstance(http, dict):
        raise SourceManifestError("Evidência bruta ou HTTP ausente no manifesto.")
    raw_path_value = raw_snapshot.get("path")
    if not isinstance(raw_path_value, str) or not raw_path_value:
        raise SourceManifestError("Path do snapshot bruto ausente.")
    raw_path = (REPO_ROOT / raw_path_value).resolve()
    _repo_relative_path(raw_path)
    if not raw_path.is_file():
        raise FileNotFoundError(f"Snapshot bruto ausente: {raw_path}.")
    raw_bytes = raw_path.read_bytes()
    if raw_snapshot.get("byteCount") != len(raw_bytes):
        raise SourceManifestError("Tamanho do snapshot bruto diverge do manifesto.")
    if raw_snapshot.get("snapshotSha256") != hashlib.sha256(raw_bytes).hexdigest():
        raise SourceManifestError("Hash do snapshot bruto diverge do manifesto.")
    if raw_snapshot.get("recordCount") != registry.municipality_count:
        raise SourceManifestError("Contagem do snapshot bruto diverge do registro.")

    generated_at = manifest.get("acquiredAt")
    response_body_sha256 = http.get("responseBodySha256")
    if not isinstance(generated_at, str) or not generated_at.strip():
        raise SourceManifestError("Instante de aquisição ausente no manifesto.")
    if not isinstance(response_body_sha256, str):
        raise SourceManifestError("Hash do corpo HTTP ausente no manifesto.")
    return {
        "generatedAt": generated_at,
        "sourceManifestPath": _repo_relative_path(manifest_path),
        "sourceManifestSha256": _sha256(manifest_path),
        "responseBodySha256": response_body_sha256,
        "rawSnapshotSha256": str(raw_snapshot["snapshotSha256"]),
    }


def load_identity_publication_inputs(
    state_code: str,
) -> tuple[StatePublication, StateConfig, MunicipalityRegistry, dict[str, str]]:
    publication = load_state_publication(state_code)
    if publication.analytics_status != "identity-only":
        raise IdentityPublicationError(
            f"A publicação de {publication.state_code} não é identity-only."
        )
    expected_output = (
        REPO_ROOT
        / "state-publications"
        / publication.state_code.lower()
        / "data"
    ).resolve()
    if publication.public_data_directory != expected_output:
        raise IdentityPublicationError(
            "Publicação identity-only deve usar a raiz estadual dedicada "
            f"{expected_output}."
        )
    state_config = load_state_config(
        publication.state_code,
        config_dir=publication.state_config_path.parent,
    )
    registry = load_municipality_registry(
        state_config,
        registry_path=publication.municipality_registry_path,
    )
    manifest_path, manifest = _read_source_manifest(publication.state_code)
    source = _validate_source_manifest(
        manifest_path,
        manifest,
        publication=publication,
        state_config=state_config,
        registry=registry,
    )
    return publication, state_config, registry, source


def materialize_identity_publication(
    state_code: str,
    *,
    apply: bool = False,
    check: bool = False,
) -> dict[str, Any]:
    if apply and check:
        raise ValueError("--apply e --check são mutuamente exclusivos.")
    publication, state_config, registry, source = load_identity_publication_inputs(
        state_code
    )

    validator = lambda root: validate_identity_publication(
        root,
        publication=publication,
        state_config=state_config,
        registry=registry,
        generated_at=source["generatedAt"],
        source_manifest_path=source["sourceManifestPath"],
        source_manifest_sha256=source["sourceManifestSha256"],
        response_body_sha256=source["responseBodySha256"],
    )
    if check:
        validator(publication.public_data_directory)
        return {
            "mode": "check",
            "stateCode": publication.state_code,
            "publicationStatus": publication.analytics_status,
            "municipalityCount": registry.municipality_count,
            "fileCount": registry.municipality_count + 2,
            "output": _repo_relative_path(publication.public_data_directory),
            "sourceManifestSha256": source["sourceManifestSha256"],
        }

    files = build_identity_publication_files(
        publication=publication,
        state_config=state_config,
        registry=registry,
        generated_at=source["generatedAt"],
        source_manifest_path=source["sourceManifestPath"],
        source_manifest_sha256=source["sourceManifestSha256"],
        response_body_sha256=source["responseBodySha256"],
    )
    STAGING_PARENT.mkdir(parents=True, exist_ok=True)
    staging_root = Path(
        tempfile.mkdtemp(
            prefix=f"{publication.state_code.lower()}-",
            dir=STAGING_PARENT,
        )
    )
    try:
        write_staged_publication(files, staging_root)
        validator(staging_root)
        if not apply:
            return {
                "mode": "dry-run",
                "stateCode": publication.state_code,
                "publicationStatus": publication.analytics_status,
                "municipalityCount": registry.municipality_count,
                "fileCount": len(files),
                "output": _repo_relative_path(publication.public_data_directory),
                "sourceManifestSha256": source["sourceManifestSha256"],
            }
        promotion = promote_staged_publication(
            staging_root,
            publication.public_data_directory,
            validate_target=validator,
        )
        return {
            "mode": "apply",
            "stateCode": publication.state_code,
            "publicationStatus": publication.analytics_status,
            "municipalityCount": registry.municipality_count,
            "fileCount": len(files),
            "output": _repo_relative_path(publication.public_data_directory),
            "sourceManifestSha256": source["sourceManifestSha256"],
            "changedFiles": promotion.changed_files,
            "preservedFiles": promotion.preserved_files,
            "removedFiles": promotion.removed_files,
            "publicationNoop": promotion.publication_noop,
        }
    finally:
        if staging_root.exists():
            shutil.rmtree(staging_root)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Materializa e valida uma publicação estadual somente de identidade, "
            "sem banco ou rede."
        )
    )
    parser.add_argument("--state", required=True, help="UF textual com duas letras.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true", help="Promove após validação integral.")
    mode.add_argument("--check", action="store_true", help="Valida a publicação existente.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = materialize_identity_publication(
            args.state,
            apply=args.apply,
            check=args.check,
        )
    except (
        FileNotFoundError,
        IdentityPublicationError,
        MunicipalityRegistryError,
        SourceManifestError,
        StateConfigError,
        StatePublicationError,
        ValueError,
    ) as exc:
        print(f"Publicação de identidade inválida: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
