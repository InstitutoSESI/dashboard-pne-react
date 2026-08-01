from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Any, Mapping


DATA_PIPELINE_DIR = Path(__file__).resolve().parents[1]
if str(DATA_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_PIPELINE_DIR))

from src.config import (  # noqa: E402
    PUBLIC_DATA_DIR,
    STATIC_PARTITIONED_DATA_DIR,
)
from src.municipal_inequality import build_document  # noqa: E402


EXPECTED_MUNICIPALITIES = 497
PUBLIC_MUNICIPAL_ROOT = PUBLIC_DATA_DIR / "municipios"
ALLOWED_OUTPUT_ROOTS = frozenset(
    {
        (STATIC_PARTITIONED_DATA_DIR / "municipios").resolve(),
        (PUBLIC_DATA_DIR / "municipios").resolve(),
    }
)


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"{path} não contém um objeto JSON.")
    return payload


def _serialized(payload: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=False, allow_nan=False, indent=2) + "\n"
    ).encode("utf-8")


def _write_if_changed(
    path: Path, payload: Mapping[str, Any], *, check: bool
) -> str:
    if path.exists() and _read_json(path) == payload:
        return "preserved"
    status = "updated" if path.exists() else "created"
    if check:
        return status
    content = _serialized(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    if temporary.exists():
        raise FileExistsError(temporary)
    temporary.write_bytes(content)
    try:
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()
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


def materialize(
    output_root: Path,
    *,
    education_root: Path | None = None,
    registry_path: Path | None = None,
    published_root: Path = PUBLIC_MUNICIPAL_ROOT,
    check: bool = False,
) -> dict[str, Any]:
    target = validate_output_root(output_root)
    source_root = (
        education_root or target.parent / "educacao" / "municipios"
    ).expanduser().resolve()
    if not source_root.is_dir():
        raise FileNotFoundError(source_root)
    registry = _read_json(
        registry_path or target.parent / "municipios_index.json"
    )
    entries = list(registry.get("municipios") or [])
    if (
        registry.get("total_municipios") != EXPECTED_MUNICIPALITIES
        or len(entries) != EXPECTED_MUNICIPALITIES
    ):
        raise RuntimeError("Registro municipal não contém os 497 municípios.")

    rows_by_municipality: dict[str, list[dict[str, Any]]] = {}
    education_by_municipality: dict[str, dict[str, Any]] = {}
    observed: set[str] = set()
    for entry in sorted(entries, key=lambda item: str(item["id_municipio"])):
        municipality_id = str(entry.get("id_municipio") or "")
        municipality_name = str(entry.get("nome") or "").strip()
        if len(municipality_id) != 7 or not municipality_id.isdigit():
            raise RuntimeError(f"Código municipal inválido no registro: {municipality_id!r}.")
        if not municipality_name:
            raise RuntimeError(f"Nome municipal ausente para {municipality_id}.")
        if municipality_id in observed:
            raise RuntimeError(f"Código municipal duplicado: {municipality_id}.")
        observed.add(municipality_id)

        education = _read_json(source_root / f"{municipality_id}.json")
        if str(education.get("id_municipio")) != municipality_id:
            raise RuntimeError(
                f"Identidade educacional divergente para {municipality_id}."
            )
        education_by_municipality[municipality_id] = education
        rows_by_municipality[municipality_id] = _education_rows(education)

    fallback_root = published_root.expanduser().resolve()
    physical_details = {
        path.parent.name
        for path in target.glob("*/details.json")
        if len(path.parent.name) == 7 and path.parent.name.isdigit()
    }
    if physical_details != observed:
        missing = sorted(observed - physical_details)
        extra = sorted(physical_details - observed)
        raise RuntimeError(
            f"Conjunto físico divergente; ausentes={missing[:5]}, extras={extra[:5]}."
        )

    planned: list[tuple[Path, dict[str, Any]]] = []
    preserved_pilot_count = 0
    recalculated_count = 0
    for entry in sorted(entries, key=lambda item: str(item["id_municipio"])):
        municipality_id = str(entry["id_municipio"])
        municipality_name = str(entry.get("nome") or "").strip()
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
                or registry.get("generated_at")
                or ""
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

    physical = {
        path.parent.name
        for path in target.glob("*/details.json")
        if len(path.parent.name) == 7 and path.parent.name.isdigit()
    }
    if physical != observed:
        missing = sorted(observed - physical)
        extra = sorted(physical - observed)
        raise RuntimeError(
            f"Conjunto físico divergente; ausentes={missing[:5]}, extras={extra[:5]}."
        )
    return {
        "mode": "check" if check else "write",
        "output": str(target),
        "educationSource": str(source_root),
        "pilotSource": (
            "education"
            if recalculated_count == len(observed)
            else "published"
            if preserved_pilot_count == len(observed)
            else "mixed"
        ),
        "recalculatedPilotCount": recalculated_count,
        "preservedPublishedPilotCount": preserved_pilot_count,
        "municipalityCount": len(observed),
        **stats,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Incorpora o documento municipal de desigualdade em details.json."
    )
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--education-root", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    print(
        json.dumps(
            materialize(
                args.output_root,
                education_root=args.education_root,
                check=args.check,
            ),
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
