from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import statistics
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping


REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_PIPELINE_DIR = REPO_ROOT / "data_pipeline"
PUBLIC_DATA_DIR = REPO_ROOT / "public" / "data"
if str(DATA_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_PIPELINE_DIR))

from src.pne2026_public_diagnostic_v2 import (  # noqa: E402
    CATALOG_VERSION,
    PUBLIC_SCHEMA_VERSION,
    PUBLIC_VERSION,
    audit_pne2026_public_diagnostic_v2,
    build_pne2026_public_diagnostic_v2,
)


PROPERTY_NAME = "pne2026PublicDiagnosticV2"
V1_PROPERTY_NAME = "pne2026PublicDiagnostic"
EXPECTED_MUNICIPALITIES = 497
EXPECTED_PHYSICAL_FILES = 497
EXPECTED_V2_OCCURRENCES = 15_114
EXPECTED_V2_ABSENCES = 293
EXPECTED_V1_OCCURRENCES = 9_119


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Propriedade JSON duplicada: {key}")
        result[key] = value
    return result


def _loads(content: bytes, path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(
            content.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise RuntimeError(f"JSON inválido em {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"Contrato deve ser um objeto JSON: {path}")
    return payload


def _serialized(payload: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    ).encode("utf-8")


def _property_value_bytes(content: bytes, property_name: str) -> bytes:
    text = content.decode("utf-8")
    marker = f'  "{property_name}": '
    start = text.find(marker)
    if start < 0 or text.find(marker, start + len(marker)) >= 0:
        raise RuntimeError(
            f"Esperada exatamente uma ocorrência de {property_name} no nível superior."
        )
    value_start = start + len(marker)
    _, value_length = json.JSONDecoder().raw_decode(text[value_start:])
    return text[value_start : value_start + value_length].encode("utf-8")


def _flatten(public_contract: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return [
        result
        for goal in public_contract.get("goals") or []
        for result in goal.get("results") or []
    ]


def _aggregate_hash(blocks: Iterable[tuple[str, bytes]]) -> str:
    digest = hashlib.sha256()
    for municipality_id, block in sorted(blocks):
        identifier = municipality_id.encode("utf-8")
        digest.update(len(identifier).to_bytes(4, "big"))
        digest.update(identifier)
        digest.update(len(block).to_bytes(8, "big"))
        digest.update(block)
    return digest.hexdigest()


def _v1_audit(
    contracts: Iterable[tuple[str, Mapping[str, Any], bytes]],
) -> dict[str, Any]:
    result_counts: list[int] = []
    classifications: Counter[Any] = Counter()
    versions: Counter[str] = Counter()
    comparison_count = 0
    trajectory_count = 0
    source_occurrences = 0
    blocks: list[tuple[str, bytes]] = []
    municipality_count = 0
    for municipality_id, contract, content in contracts:
        municipality_count += 1
        public_v1 = contract.get(V1_PROPERTY_NAME)
        if not isinstance(public_v1, Mapping):
            raise RuntimeError(f"{municipality_id}: bloco v1 ausente.")
        blocks.append(
            (municipality_id, _property_value_bytes(content, V1_PROPERTY_NAME))
        )
        versions[str(public_v1.get("version"))] += 1
        results = _flatten(public_v1)
        result_counts.append(len(results))
        for result in results:
            classifications[result.get("classification")] += 1
            comparison_count += any(
                field in result
                for field in (
                    "stateComparison",
                    "statewidePosition",
                    "similarMunicipalities",
                )
            )
            trajectory_count += "trajectory" in result
        source_occurrences += len(public_v1.get("sources") or [])
    distribution = Counter(result_counts)
    return {
        "municipalityCount": municipality_count,
        "aggregateSha256": _aggregate_hash(blocks),
        "versions": dict(sorted(versions.items())),
        "resultCount": sum(result_counts),
        "classificationCounts": {
            "advance": classifications["advance"],
            "maintain": classifications["maintain"],
            "unclassified": classifications[None],
        },
        "minimum": min(result_counts, default=0),
        "maximum": max(result_counts, default=0),
        "mean": statistics.fmean(result_counts) if result_counts else 0,
        "median": statistics.median(result_counts) if result_counts else 0,
        "distribution": {
            str(count): distribution[count] for count in sorted(distribution)
        },
        "comparisonResultCount": comparison_count,
        "trajectoryCount": trajectory_count,
        "sourceOccurrences": source_occurrences,
    }


def _registry(public_data_dir: Path) -> list[dict[str, Any]]:
    path = public_data_dir / "municipios_index.json"
    payload = _loads(path.read_bytes(), path)
    entries = list(payload.get("municipios") or [])
    if payload.get("total_municipios") != EXPECTED_MUNICIPALITIES:
        raise RuntimeError("Registro municipal não declara 497 municípios.")
    if len(entries) != EXPECTED_MUNICIPALITIES:
        raise RuntimeError(f"Esperados 497 municípios; encontrados {len(entries)}.")
    slugs = {str(entry.get("slug")) for entry in entries}
    ids = {str(entry.get("id_municipio")) for entry in entries}
    if len(slugs) != EXPECTED_MUNICIPALITIES or len(ids) != EXPECTED_MUNICIPALITIES:
        raise RuntimeError("Slugs e códigos IBGE precisam ser únicos nos 497 municípios.")
    if not all(identifier.isdigit() for identifier in ids):
        raise RuntimeError("Todos os aliases municipais devem usar código IBGE numérico.")
    return entries


def _expected_paths(
    public_data_dir: Path, entry: Mapping[str, Any]
) -> tuple[Path, Path]:
    municipality_id = str(entry["id_municipio"])
    diagnostic = public_data_dir / "municipios" / municipality_id / "diagnostico.json"
    pne = public_data_dir / "municipios" / municipality_id / "index.json"
    for path in (diagnostic, pne):
        if not path.is_file():
            raise RuntimeError(f"Arquivo municipal ausente: {path}")
    return diagnostic, pne


def _insert_parallel_v2(
    contract: Mapping[str, Any], public_v2: Mapping[str, Any]
) -> dict[str, Any]:
    if V1_PROPERTY_NAME not in contract:
        raise RuntimeError("O bloco v1 precisa existir antes da materialização v2.")
    output: dict[str, Any] = {}
    for key, value in contract.items():
        if key == PROPERTY_NAME:
            continue
        if key == V1_PROPERTY_NAME:
            output[PROPERTY_NAME] = public_v2
        output[key] = value
    return output


def _assert_v1_baseline(v1: Mapping[str, Any]) -> None:
    if v1["municipalityCount"] != EXPECTED_MUNICIPALITIES:
        raise RuntimeError("Auditoria v1 não encontrou os 497 municípios.")
    if v1["versions"] != {"pne2026-public-diagnostic-v1": 497}:
        raise RuntimeError(f"Versões v1 inesperadas: {v1['versions']}")
    if v1["resultCount"] != EXPECTED_V1_OCCURRENCES:
        raise RuntimeError(f"Resultados v1 inesperados: {v1['resultCount']}")
    expected = {"advance": 7_759, "maintain": 1_360, "unclassified": 0}
    if v1["classificationCounts"] != expected:
        raise RuntimeError(
            f"Classificações v1 inesperadas: {v1['classificationCounts']}"
        )


def _assert_v2_audit(audit: Mapping[str, Any]) -> None:
    expected_scalars = {
        "municipalityCount": 497,
        "authorizedPairCount": 34,
        "goalCount": 22,
        "indicatorCount": 31,
        "essentialCount": 7,
        "complementaryCount": 10,
        "pneAvailableOccurrences": EXPECTED_V2_OCCURRENCES,
        "v2AvailableOccurrences": EXPECTED_V2_OCCURRENCES,
        "pneAbsentOccurrences": EXPECTED_V2_ABSENCES,
        "duplicateResultCount": 0,
        "outOfCatalogResultCount": 0,
    }
    for key, expected in expected_scalars.items():
        if audit.get(key) != expected:
            raise RuntimeError(f"Auditoria v2: {key}={audit.get(key)}; esperado {expected}.")
    if audit.get("publicationReady") is not True:
        raise RuntimeError("Auditoria v2 não aprovou publicação.")
    divergences = audit.get("pneV2Divergences") or {}
    if any(divergences.values()):
        raise RuntimeError(f"Divergências PNE × v2: {divergences}")
    if audit.get("classificationCounts") != {
        "advance": 8_166,
        "maintain": 1_492,
        "unclassified": 5_456,
    }:
        raise RuntimeError("Contagens de classificação v2 divergentes.")
    if audit.get("directionCounts") != {"at_least": 14_617, "at_most": 497}:
        raise RuntimeError("Contagens de direção v2 divergentes.")
    if audit.get("relationshipCounts") != {
        "contextual_proxy": 497,
        "direct": 5_308,
        "partial_component": 9_309,
    }:
        raise RuntimeError("Contagens de vínculo v2 divergentes.")
    if sum((audit.get("v2NegativeValuesByIndicator") or {}).values()) != 0:
        raise RuntimeError("A auditoria v2 publicou valor negativo inesperado.")
    if sum((audit.get("v2ValuesAbove100ByIndicator") or {}).values()) != 412:
        raise RuntimeError("A auditoria v2 não preservou os 412 valores acima de 100%.")


def _validate_materialized_contract(
    municipality_id: str,
    contract: Mapping[str, Any],
    expected_v2: Mapping[str, Any],
) -> None:
    if contract.get("schemaVersion") != PUBLIC_SCHEMA_VERSION:
        raise RuntimeError(f"{municipality_id}: schema municipal inesperado.")
    public_v2 = contract.get(PROPERTY_NAME)
    if public_v2 != expected_v2:
        raise RuntimeError(f"{municipality_id}: propriedade v2 diverge do builder.")
    if public_v2.get("version") != PUBLIC_VERSION:
        raise RuntimeError(f"{municipality_id}: versão interna v2 inesperada.")
    if public_v2.get("presentationCatalogVersion") != CATALOG_VERSION:
        raise RuntimeError(f"{municipality_id}: catálogo v2 inesperado.")
    scope = public_v2.get("scope") or {}
    if len(scope.get("resultPairs") or []) != 31:
        raise RuntimeError(f"{municipality_id}: catálogo v2 incompleto.")
    if len(scope.get("essentialIndicatorIds") or []) != 9:
        raise RuntimeError(f"{municipality_id}: metadata dos essenciais incompleta.")
    if len(scope.get("complementaryIndicatorIds") or []) != 22:
        raise RuntimeError(f"{municipality_id}: metadata dos complementares incompleta.")
    results = _flatten(public_v2)
    if len(results) != len({result["indicatorId"] for result in results}):
        raise RuntimeError(f"{municipality_id}: resultado v2 duplicado.")
    for result in results:
        if result.get("relationshipType") == "contextual_proxy" and result.get(
            "classification"
        ) is not None:
            raise RuntimeError(f"{municipality_id}: proxy contextual classificado.")
        if result.get("indicatorId") == "medio_tecnico_articulado_percentual" and result.get(
            "classification"
        ) not in {None, "maintain"}:
            raise RuntimeError(f"{municipality_id}: regra maintain-only violada.")


def prepare_materialization(public_data_dir: Path = PUBLIC_DATA_DIR) -> dict[str, Any]:
    entries = _registry(public_data_dir)
    contents: dict[Path, bytes] = {}
    canonical_before: list[tuple[str, Mapping[str, Any], bytes]] = []
    canonical_after: list[tuple[str, Mapping[str, Any], bytes]] = []
    audit_inputs: list[tuple[Mapping[str, Any], Mapping[str, Any]]] = []
    existing_v2_count = 0

    physical_paths = list((public_data_dir / "municipios").glob("*/diagnostico.json"))
    if len(physical_paths) != EXPECTED_PHYSICAL_FILES:
        raise RuntimeError(
            f"Esperados {EXPECTED_PHYSICAL_FILES} diagnostico.json; encontrados {len(physical_paths)}."
        )

    for entry in entries:
        municipality_id = str(entry["id_municipio"])
        canonical_path, pne_path = _expected_paths(public_data_dir, entry)
        canonical_content = canonical_path.read_bytes()
        contract = _loads(canonical_content, canonical_path)
        if str(contract.get("municipalityId")) != municipality_id:
            raise RuntimeError(f"{municipality_id}: identidade municipal divergente.")
        if contract.get("schemaVersion") != PUBLIC_SCHEMA_VERSION:
            raise RuntimeError(f"{municipality_id}: schema municipal inesperado.")
        if PROPERTY_NAME in contract:
            existing_v2_count += 1
        pne_payload = _loads(pne_path.read_bytes(), pne_path).get("pne_2026_2036")
        if not isinstance(pne_payload, Mapping):
            raise RuntimeError(f"{municipality_id}: fluxo PNE municipal ausente.")
        public_v2 = build_pne2026_public_diagnostic_v2(contract, pne_payload)
        output_contract = _insert_parallel_v2(contract, public_v2)
        output_content = _serialized(output_contract)
        _validate_materialized_contract(municipality_id, output_contract, public_v2)
        if _property_value_bytes(canonical_content, V1_PROPERTY_NAME) != _property_value_bytes(
            output_content, V1_PROPERTY_NAME
        ):
            raise RuntimeError(f"{municipality_id}: bytes do bloco v1 seriam alterados.")
        original_without_v2 = dict(contract)
        original_without_v2.pop(PROPERTY_NAME, None)
        output_without_v2 = dict(output_contract)
        output_without_v2.pop(PROPERTY_NAME, None)
        if output_without_v2 != original_without_v2:
            raise RuntimeError(f"{municipality_id}: propriedade preexistente seria alterada.")
        contents[canonical_path] = output_content
        canonical_before.append((municipality_id, contract, canonical_content))
        canonical_after.append((municipality_id, output_contract, output_content))
        audit_inputs.append((contract, pne_payload))

    if len(contents) != EXPECTED_PHYSICAL_FILES:
        raise RuntimeError(
            f"Conteúdos preparados: {len(contents)}; esperados {EXPECTED_PHYSICAL_FILES}."
        )
    v1_before = _v1_audit(canonical_before)
    v1_after = _v1_audit(canonical_after)
    _assert_v1_baseline(v1_before)
    if v1_after != v1_before:
        raise RuntimeError("A auditoria em memória detectou alteração no bloco v1.")
    v2_audit = audit_pne2026_public_diagnostic_v2(audit_inputs)
    _assert_v2_audit(v2_audit)
    aggregate = _aggregate_hash(
        (str(path.relative_to(public_data_dir)), content)
        for path, content in contents.items()
    )
    changed_paths = [path for path, content in contents.items() if path.read_bytes() != content]
    return {
        "contents": contents,
        "changedPaths": changed_paths,
        "existingV2ContractCount": existing_v2_count,
        "canonicalCount": len(entries),
        "physicalFileCount": len(contents),
        "aggregateSha256": aggregate,
        "v1Before": v1_before,
        "v1After": v1_after,
        "v2Audit": v2_audit,
    }


def _transactional_write(contents: Mapping[Path, bytes]) -> int:
    changed = [(path, content) for path, content in contents.items() if path.read_bytes() != content]
    if not changed:
        return 0
    transaction_parent = PUBLIC_DATA_DIR.parent
    with tempfile.TemporaryDirectory(
        prefix="pne2026-diagnostic-v2-", dir=transaction_parent
    ) as temporary:
        transaction_dir = Path(temporary)
        staged_dir = transaction_dir / "staged"
        backup_dir = transaction_dir / "backup"
        staged_dir.mkdir()
        backup_dir.mkdir()
        staged: list[tuple[Path, Path, Path]] = []
        for index, (target, content) in enumerate(changed):
            staged_path = staged_dir / f"{index:04d}.json"
            backup_path = backup_dir / f"{index:04d}.json"
            staged_path.write_bytes(content)
            if staged_path.read_bytes() != content:
                raise RuntimeError(f"Falha ao validar staging de {target}.")
            _loads(content, target)
            shutil.copy2(target, backup_path)
            staged.append((target, staged_path, backup_path))
        replaced: list[tuple[Path, Path]] = []
        try:
            for target, staged_path, backup_path in staged:
                os.replace(staged_path, target)
                replaced.append((target, backup_path))
        except Exception:
            for target, backup_path in reversed(replaced):
                shutil.copy2(backup_path, target)
            raise
    return len(changed)


def audit_materialized(public_data_dir: Path = PUBLIC_DATA_DIR) -> dict[str, Any]:
    prepared = prepare_materialization(public_data_dir)
    if prepared["existingV2ContractCount"] != EXPECTED_MUNICIPALITIES:
        raise RuntimeError(
            "A camada materializada não está presente nos 497 contratos canônicos."
        )
    if prepared["changedPaths"]:
        raise RuntimeError(
            f"{len(prepared['changedPaths'])} arquivos divergem da geração determinística."
        )
    return prepared


def _public_report(prepared: Mapping[str, Any], written: int) -> dict[str, Any]:
    return {
        "property": PROPERTY_NAME,
        "version": PUBLIC_VERSION,
        "schemaVersion": PUBLIC_SCHEMA_VERSION,
        "canonicalContracts": prepared["canonicalCount"],
        "physicalFiles": prepared["physicalFileCount"],
        "writtenFiles": written,
        "aggregateSha256": prepared["aggregateSha256"],
        "v1": prepared["v1After"],
        "v2": prepared["v2Audit"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Materializa transacionalmente o Diagnóstico municipal público v2."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Valida os contratos materializados sem escrever arquivos.",
    )
    args = parser.parse_args()
    if args.check:
        prepared = audit_materialized()
        written = 0
    else:
        prepared = prepare_materialization()
        written = _transactional_write(prepared["contents"])
        prepared = audit_materialized()
    print(json.dumps(_public_report(prepared, written), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
