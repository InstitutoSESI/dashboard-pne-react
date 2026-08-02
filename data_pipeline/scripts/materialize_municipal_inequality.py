from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import time
from typing import Any, Mapping


DATA_PIPELINE_DIR = Path(__file__).resolve().parents[1]
if str(DATA_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_PIPELINE_DIR))

from src.config import (  # noqa: E402
    PUBLIC_DATA_DIR,
    STATIC_PARTITIONED_DATA_DIR,
)
from src.municipality_registry import (  # noqa: E402
    MunicipalityRecord,
    MunicipalityRegistry,
    MunicipalityRegistryError,
    load_municipality_registry,
)
from src.municipal_inequality import build_document  # noqa: E402
from src.state_config import (  # noqa: E402
    DEFAULT_STATE_CODE,
    StateConfigError,
    load_state_config,
)
from src.pipeline_profiling import (  # noqa: E402
    get_active_profile_session,
    profile_operation,
    profiled_aggregate_operation,
    profiled_main_from_environment,
)


PUBLIC_MUNICIPAL_ROOT = PUBLIC_DATA_DIR / "municipios"
ALLOWED_OUTPUT_ROOTS = frozenset(
    {
        (STATIC_PARTITIONED_DATA_DIR / "municipios").resolve(),
        (PUBLIC_DATA_DIR / "municipios").resolve(),
    }
)


def _read_json(path: Path) -> dict[str, Any]:
    session = get_active_profile_session()
    started_ns = time.perf_counter_ns() if session is not None else 0
    failed = False
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except BaseException:
        failed = True
        raise
    finally:
        if session is not None:
            source_kind = (
                "details"
                if path.name == "details.json"
                else "index"
                if path.name == "index.json"
                else "education"
            )
            session.accumulate_event(
                category="read",
                name="inequality.document_reads",
                duration_ns=time.perf_counter_ns() - started_ns,
                counters={
                    "filesRead": int(not failed),
                    "bytesRead": path.stat().st_size if path.is_file() else 0,
                    "errors": int(failed),
                },
                metadata={"sourceKind": source_kind},
            )
    if not isinstance(payload, dict):
        raise TypeError(f"{path} não contém um objeto JSON.")
    return payload


def _serialized(payload: Mapping[str, Any]) -> bytes:
    session = get_active_profile_session()
    started_ns = time.perf_counter_ns() if session is not None else 0
    content = (
        json.dumps(payload, ensure_ascii=False, allow_nan=False, indent=2) + "\n"
    ).encode("utf-8")
    if session is not None:
        session.accumulate_event(
            category="serialization",
            name="inequality.render_json",
            duration_ns=time.perf_counter_ns() - started_ns,
            counters={"payloads": 1, "bytesRendered": len(content)},
            metadata={"format": "json"},
        )
    return content


def _write_if_changed(
    path: Path, payload: Mapping[str, Any], *, check: bool
) -> str:
    session = get_active_profile_session()
    if path.exists() and _read_json(path) == payload:
        if session is not None:
            session.accumulate_event(
                category="write",
                name="inequality.outputs",
                counters={"preserved": 1},
            )
        return "preserved"
    status = "updated" if path.exists() else "created"
    if check:
        if session is not None:
            session.accumulate_event(
                category="validation",
                name="inequality.planned_outputs",
                counters={status: 1},
                metadata={"checkOnly": True},
            )
        return status
    content = _serialized(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    if temporary.exists():
        raise FileExistsError(temporary)
    started_ns = time.perf_counter_ns() if session is not None else 0
    temporary.write_bytes(content)
    try:
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()
    if session is not None:
        session.accumulate_event(
            category="write",
            name="inequality.outputs",
            duration_ns=time.perf_counter_ns() - started_ns,
            counters={status: 1, "bytesWritten": len(content)},
        )
    return status


def _education_rows(document: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = (
        (((document.get("blocos") or {}).get("matriculas") or {})
        .get("detalhamentos", {}))
        .get("por_rede_localizacao", [])
    )
    if not isinstance(rows, list):
        raise TypeError("Recorte educacional por rede/localização inválido.")
    return [dict(row) for row in rows if isinstance(row, Mapping)]


@profiled_aggregate_operation(
    "validation",
    "inequality.embedded_contract_validation",
)
def _validate_embedded_document(
    document: Any,
    *,
    municipality_id: str,
    municipality_name: str,
    source: Path,
) -> dict[str, Any]:
    if not isinstance(document, Mapping):
        raise RuntimeError(f"Documento municipal de desigualdade inválido: {source}.")
    municipality = document.get("municipality")
    pilot = document.get("inequalityPilot")
    if (
        document.get("schemaVersion") != "municipal-inequality-v1"
        or not isinstance(municipality, Mapping)
        or str(municipality.get("id") or "") != municipality_id
        or str(municipality.get("name") or "").strip() != municipality_name
        or not isinstance(pilot, Mapping)
    ):
        raise RuntimeError(
            f"Identidade do documento municipal de desigualdade divergente: {source}."
        )
    validated = build_document(
        municipality_id=municipality_id,
        municipality_name=municipality_name,
        generated_at=str(document.get("generatedAt") or ""),
        inequality_pilot=pilot,
    )
    if dict(document) != validated:
        raise RuntimeError(
            f"Documento municipal de desigualdade fora do contrato atual: {source}."
        )
    return dict(document)


def _embedded_document(
    details: Mapping[str, Any],
    *,
    municipality_id: str,
    municipality_name: str,
    source: Path,
) -> dict[str, Any] | None:
    shared = details.get("_shared")
    if shared is None:
        return None
    if not isinstance(shared, Mapping):
        raise RuntimeError(f"_shared inválido em {source}.")
    document = shared.get("municipal_inequality")
    if document is None:
        return None
    return _validate_embedded_document(
        document,
        municipality_id=municipality_id,
        municipality_name=municipality_name,
        source=source,
    )


def _merge_document(
    details: Mapping[str, Any], document: Mapping[str, Any], *, source: Path
) -> dict[str, Any]:
    shared = details.get("_shared")
    if shared is None:
        shared = {}
    if not isinstance(shared, Mapping):
        raise RuntimeError(f"_shared inválido em {source}.")
    merged = dict(details)
    merged_shared = dict(shared)
    merged_shared["municipal_inequality"] = dict(document)
    merged["_shared"] = merged_shared
    return merged


def _supports_recalculation(
    rows_by_municipality: Mapping[str, list[dict[str, Any]]],
) -> bool:
    return any(
        "matriculas_integral" in row
        and str(row.get("dependencia") or "").strip().lower() == "publica"
        for rows in rows_by_municipality.values()
        for row in rows
    )


def validate_output_root(output_root: Path) -> Path:
    resolved = output_root.expanduser().resolve()
    if resolved not in ALLOWED_OUTPUT_ROOTS:
        allowed = ", ".join(str(path) for path in sorted(ALLOWED_OUTPUT_ROOTS))
        raise ValueError(f"Saída bloqueada: {resolved}. Permitidas: {allowed}.")
    if not resolved.is_dir():
        raise FileNotFoundError(resolved)
    return resolved


@profiled_aggregate_operation(
    "validation",
    "inequality.identity_validation",
)
def _validate_index_identity(
    target: Path,
    record: MunicipalityRecord,
) -> None:
    path = target / record.ibge_code / "index.json"
    payload = _read_json(path)
    expected = {
        "id_municipio": record.ibge_code,
        "municipio": record.name,
        "slug": record.slug,
    }
    observed = {field: payload.get(field) for field in expected}
    if observed != expected:
        raise RuntimeError(
            f"Identidade municipal divergente em {path}: {observed!r}."
        )


def _materialize_impl(
    output_root: Path,
    *,
    education_root: Path | None = None,
    registry_path: Path | None = None,
    registry: MunicipalityRegistry | None = None,
    state_code: str = DEFAULT_STATE_CODE,
    published_root: Path = PUBLIC_MUNICIPAL_ROOT,
    check: bool = False,
) -> dict[str, Any]:
    if registry is None:
        state_config = load_state_config(state_code)
        registry = load_municipality_registry(
            state_config,
            registry_path=registry_path,
        )
    target = validate_output_root(output_root)
    source_root = (
        education_root or target.parent / "educacao" / "municipios"
    ).expanduser().resolve()
    if not source_root.is_dir():
        raise FileNotFoundError(source_root)

    physical_directories = {
        path.name for path in target.iterdir() if path.is_dir()
    }
    if physical_directories != registry.ids:
        missing = sorted(registry.ids - physical_directories)
        extra = sorted(physical_directories - registry.ids)
        raise RuntimeError(
            f"Conjunto físico divergente; ausentes={missing[:5]}, extras={extra[:5]}."
        )
    education_ids = {path.stem for path in source_root.glob("*.json")}
    if education_ids != registry.ids:
        missing = sorted(registry.ids - education_ids)
        extra = sorted(education_ids - registry.ids)
        raise RuntimeError(
            "Conjunto educacional divergente; "
            f"ausentes={missing[:5]}, extras={extra[:5]}."
        )

    rows_by_municipality: dict[str, list[dict[str, Any]]] = {}
    education_by_municipality: dict[str, dict[str, Any]] = {}
    for record in registry.ordered_records:
        _validate_index_identity(target, record)
        education = _read_json(source_root / f"{record.ibge_code}.json")
        if education.get("id_municipio") != record.ibge_code:
            raise RuntimeError(
                f"Identidade educacional divergente para {record.ibge_code}."
            )
        education_by_municipality[record.ibge_code] = education
        rows_by_municipality[record.ibge_code] = _education_rows(education)

    fallback_root = published_root.expanduser().resolve()
    physical_details = {path.parent.name for path in target.glob("*/details.json")}
    if physical_details != registry.ids:
        missing = sorted(registry.ids - physical_details)
        extra = sorted(physical_details - registry.ids)
        raise RuntimeError(
            f"Conjunto físico divergente; ausentes={missing[:5]}, extras={extra[:5]}."
        )

    planned: list[tuple[Path, dict[str, Any]]] = []
    preserved_pilot_count = 0
    recalculated_count = 0
    for record in registry.ordered_records:
        municipality_id = record.ibge_code
        municipality_name = record.name
        education = education_by_municipality[municipality_id]
        details_path = target / municipality_id / "details.json"
        details = _read_json(details_path)
        existing_document = _embedded_document(
            details,
            municipality_id=municipality_id,
            municipality_name=municipality_name,
            source=details_path,
        )
        can_recalculate = _supports_recalculation(
            {municipality_id: rows_by_municipality[municipality_id]}
        )
        if can_recalculate:
            generated_at = str(
                education.get("updated_at")
                or (existing_document or {}).get("generatedAt")
                or ""
            )
            if not generated_at:
                raise RuntimeError(
                    f"Timestamp de origem ausente para {municipality_id}."
                )
            document = build_document(
                municipality_id=municipality_id,
                municipality_name=municipality_name,
                generated_at=generated_at,
                rows=rows_by_municipality[municipality_id],
            )
            recalculated_count += 1
        else:
            fallback_path = fallback_root / municipality_id / "details.json"
            fallback_document = existing_document
            if fallback_document is None and fallback_path.resolve() != details_path.resolve():
                if fallback_path.is_file():
                    fallback_details = _read_json(fallback_path)
                    fallback_document = _embedded_document(
                        fallback_details,
                        municipality_id=municipality_id,
                        municipality_name=municipality_name,
                        source=fallback_path,
                    )
            if fallback_document is None:
                raise RuntimeError(
                    "A fonte educacional não permite recalcular o piloto e não "
                    f"há publicação anterior para {municipality_id}: {fallback_path}."
                )
            document = fallback_document
            preserved_pilot_count += 1
        planned.append(
            (
                details_path,
                _merge_document(details, document, source=details_path),
            )
        )

    stats = {"created": 0, "updated": 0, "preserved": 0}
    for path, payload in planned:
        status = _write_if_changed(path, payload, check=check)
        stats[status] += 1

    physical = {path.parent.name for path in target.glob("*/details.json")}
    if physical != registry.ids:
        missing = sorted(registry.ids - physical)
        extra = sorted(physical - registry.ids)
        raise RuntimeError(
            f"Conjunto físico divergente; ausentes={missing[:5]}, extras={extra[:5]}."
        )
    return {
        "mode": "check" if check else "write",
        "output": str(target),
        "educationSource": str(source_root),
        "pilotSource": (
            "education"
            if recalculated_count == registry.municipality_count
            else "published"
            if preserved_pilot_count == registry.municipality_count
            else "mixed"
        ),
        "recalculatedPilotCount": recalculated_count,
        "preservedPublishedPilotCount": preserved_pilot_count,
        "municipalityCount": registry.municipality_count,
        **stats,
    }


def materialize(
    output_root: Path,
    *,
    education_root: Path | None = None,
    registry_path: Path | None = None,
    registry: MunicipalityRegistry | None = None,
    state_code: str = DEFAULT_STATE_CODE,
    published_root: Path = PUBLIC_MUNICIPAL_ROOT,
    check: bool = False,
) -> dict[str, Any]:
    with profile_operation(
        "compute",
        "inequality.materialization",
        metadata={
            "checkOnly": check,
            "outputRoot": output_root,
            "educationRoot": education_root,
        },
    ) as operation:
        result = _materialize_impl(
            output_root,
            education_root=education_root,
            registry_path=registry_path,
            registry=registry,
            state_code=state_code,
            published_root=published_root,
            check=check,
        )
        operation.add_counters(
            municipalities=int(result["municipalityCount"]),
            recalculated=int(result["recalculatedPilotCount"]),
            preservedPilots=int(result["preservedPublishedPilotCount"]),
            created=int(result["created"]),
            updated=int(result["updated"]),
            preserved=int(result["preserved"]),
        )
        operation.add_metadata(pilotSource=result["pilotSource"])
        return result


@profiled_main_from_environment("inequality")
def main() -> int:
    parser = argparse.ArgumentParser(
        description="Incorpora o documento municipal de desigualdade em details.json."
    )
    parser.add_argument("--output-root", type=Path, default=PUBLIC_MUNICIPAL_ROOT)
    parser.add_argument("--education-root", type=Path)
    parser.add_argument(
        "--state",
        default=DEFAULT_STATE_CODE,
        help=f"Código estadual configurado (padrão: {DEFAULT_STATE_CODE}).",
    )
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        with profile_operation(
            "validation",
            "inequality.configuration",
            metadata={"state": args.state},
        ) as configuration_event:
            state_config = load_state_config(args.state)
            registry = load_municipality_registry(state_config)
            configuration_event.add_counter(
                "municipalities", registry.municipality_count
            )
    except (FileNotFoundError, StateConfigError, MunicipalityRegistryError) as exc:
        print(f"Configuração estadual inválida: {exc}", file=sys.stderr)
        return 2
    print(
        json.dumps(
            materialize(
                args.output_root,
                education_root=args.education_root,
                registry=registry,
                check=args.check,
            ),
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
