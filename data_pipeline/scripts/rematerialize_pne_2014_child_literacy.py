#!/usr/bin/env python3
"""Rematerializa alfabetizacao nos 497 contratos públicos do ciclo encerrado."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any


DATA_PIPELINE_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = DATA_PIPELINE_DIR.parent
PUBLIC_DATA_DIR = REPO_ROOT / "public" / "data"
if str(DATA_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_PIPELINE_DIR))

from scripts.export_static_data import (  # noqa: E402
    _serialize_item,
    _serialize_result,
)
from src.pne import calculations_2014, common  # noqa: E402
from src.pne_2014_child_literacy import (  # noqa: E402
    SOURCE_LABEL,
    load_snapshot,
)
from src.pne_2014_state_reference import (  # noqa: E402
    build_alfabetizacao_state_reference_entry,
)


EXPECTED_MUNICIPALITIES = 497
TARGET_INDICATOR = "alfabetizacao"
SAO_LEOPOLDO_ID = "4318705"
SAO_LEOPOLDO_VALUES = {2023: 57.01, 2024: 37.2}


def _json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _target_item() -> dict[str, Any]:
    matches = [
        item
        for category in calculations_2014.INDICADORES.values()
        for item in category.get("items", [])
        if item.get("key") == TARGET_INDICATOR
    ]
    if len(matches) != 1:
        raise ValueError("Catálogo de cálculo sem alfabetizacao única.")
    return matches[0]


def _catalog_payload(path: Path, item: dict[str, Any]) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    categories = payload["cycles"]["pne_2014_2024"]["categories"]
    matches = [
        (items, index)
        for category in categories
        for items in [category.get("items", [])]
        for index, current in enumerate(items)
        if current.get("key") == TARGET_INDICATOR
    ]
    if len(matches) != 1:
        raise ValueError("Catálogo público sem alfabetizacao única.")
    items, index = matches[0]
    items[index] = _serialize_item(item)
    total = sum(len(category.get("items", [])) for category in categories)
    if total != 24:
        raise ValueError(f"Catálogo encerrado deve manter 24 itens, não {total}.")
    return payload


def _state_reference_payload(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    metadata, indicator = build_alfabetizacao_state_reference_entry()
    payload["registry"][TARGET_INDICATOR] = metadata
    payload["indicators"][TARGET_INDICATOR] = indicator
    payload["blocked_indicators"] = sorted(
        set(payload.get("blocked_indicators", [])) - {TARGET_INDICATOR}
    )
    payload["enabled_indicators"] = sorted(
        set(payload.get("enabled_indicators", [])) | {TARGET_INDICATOR}
    )
    payload["unavailable_indicators"] = sorted(
        set(payload.get("unavailable_indicators", [])) - {TARGET_INDICATOR}
    )
    return payload


def _municipal_payload(
    path: Path,
    *,
    item: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    municipality_name = str(payload["municipio"])
    result = calculations_2014._calc_alfabetizacao(municipality_name)
    errors: list[dict[str, Any]] = []
    serialized = _serialize_result(
        result=result,
        item=item,
        shared=common,
        municipio=municipality_name,
        cycle_key="pne_2014_2024",
        indicator_key=TARGET_INDICATOR,
        errors=errors,
    )
    if errors:
        raise ValueError(
            f"{payload['id_municipio']}: erros de serialização: {errors}."
        )
    previous_2026 = payload.get("pne_2026_2036")
    previous_population_literacy = payload["pne_2014_2024"]["indicadores"].get(
        "alfabetizacao_pop_15_mais"
    )
    payload["pne_2014_2024"]["indicadores"][TARGET_INDICATOR] = serialized
    if payload.get("pne_2026_2036") != previous_2026:
        raise ValueError("O contrato do PNE 2026–2036 foi alterado.")
    if (
        payload["pne_2014_2024"]["indicadores"].get(
            "alfabetizacao_pop_15_mais"
        )
        != previous_population_literacy
    ):
        raise ValueError("alfabetizacao_pop_15_mais foi alterado.")
    return payload, serialized


def prepare_stage(public_data_dir: Path) -> dict[str, Any]:
    public_root = public_data_dir.resolve()
    snapshot_rows, _state_rows, snapshot_manifest = load_snapshot()
    expected_available = len(
        {
            str(row["id_municipio"])
            for row in snapshot_rows
            if row.get("taxa_alfabetizacao") is not None
        }
    )
    municipality_root = public_root / "municipios"
    municipality_paths = sorted(municipality_root.glob("*/index.json"))
    if len(municipality_paths) != EXPECTED_MUNICIPALITIES:
        raise ValueError(
            f"Esperados 497 contratos municipais; encontrados "
            f"{len(municipality_paths)}."
        )

    item = _target_item()
    staged: dict[Path, bytes] = {}
    catalog_path = public_root / "indicadores.json"
    state_path = public_root / "pne_2014_2024" / "referencia_estadual.json"
    staged[catalog_path] = _json_bytes(_catalog_payload(catalog_path, item))
    staged[state_path] = _json_bytes(_state_reference_payload(state_path))

    status_counts = {"available": 0, "unavailable": 0}
    sao_leopoldo: dict[str, Any] | None = None
    for path in municipality_paths:
        payload, result = _municipal_payload(path, item=item)
        staged[path] = _json_bytes(payload)
        status = "available" if result.get("available") else "unavailable"
        status_counts[status] += 1
        if str(payload["id_municipio"]) == SAO_LEOPOLDO_ID:
            sao_leopoldo = result

    _validate_stage(
        staged,
        public_root=public_root,
        sao_leopoldo=sao_leopoldo,
        status_counts=status_counts,
        expected_available=expected_available,
    )
    return {
        "files": staged,
        "snapshotCoverage": snapshot_manifest["availableByYear"],
        "statusCounts": status_counts,
        "saoLeopoldo": sao_leopoldo,
    }


def _validate_stage(
    staged: dict[Path, bytes],
    *,
    public_root: Path,
    sao_leopoldo: dict[str, Any] | None,
    status_counts: dict[str, int],
    expected_available: int,
) -> None:
    if len(staged) != EXPECTED_MUNICIPALITIES + 2:
        raise ValueError("Stage não contém todos os contratos esperados.")
    if status_counts["available"] != expected_available:
        raise ValueError(
            "Cobertura final divergente: o último resultado disponível deve "
            f"existir para {expected_available} municípios."
        )
    if sao_leopoldo is None:
        raise ValueError("São Leopoldo ausente do stage.")
    if sao_leopoldo.get("tracks_goal") is not False:
        raise ValueError("São Leopoldo não foi classificado como observado.")
    for field in ("meta", "distance", "atingida"):
        if sao_leopoldo.get(field) is not None:
            raise ValueError(f"São Leopoldo recebeu conclusão indevida em {field}.")
    series = {
        int(point["ano"]): float(point["valor"])
        for point in sao_leopoldo.get("series", [])
    }
    if series != SAO_LEOPOLDO_VALUES:
        raise ValueError(
            f"Série de São Leopoldo divergente: {series}."
        )
    if int(sao_leopoldo.get("end_year") or 0) != 2024:
        raise ValueError("São Leopoldo não usa 2024 como último ano do ciclo.")
    if any(year > 2024 for year in series):
        raise ValueError("Ano posterior a 2024 materializado no ciclo encerrado.")

    catalog = json.loads(
        staged[public_root / "indicadores.json"].decode("utf-8")
    )
    item = next(
        current
        for category in catalog["cycles"]["pne_2014_2024"]["categories"]
        for current in category["items"]
        if current["key"] == TARGET_INDICATOR
    )
    if item["label"] != "Crianças alfabetizadas na rede municipal":
        raise ValueError("Título público divergente.")
    if item.get("tracks_goal") is not False:
        raise ValueError("Catálogo público ainda permite conclusão da Meta 5.")

    state = json.loads(
        staged[
            public_root / "pne_2014_2024" / "referencia_estadual.json"
        ].decode("utf-8")
    )
    state_values = {
        int(point["year"]): float(point["value"])
        for point in state["indicators"][TARGET_INDICATOR]["series"]
    }
    if state_values != {2023: 63.55, 2024: 44.23}:
        raise ValueError(f"Referência estadual oficial divergente: {state_values}.")


def promote_transactionally(staged: dict[Path, bytes]) -> None:
    stage_root = Path(
        tempfile.mkdtemp(prefix=".pne-2014-alfabetizacao-stage-", dir=PUBLIC_DATA_DIR)
    )
    backup_root = Path(
        tempfile.mkdtemp(prefix=".pne-2014-alfabetizacao-backup-", dir=PUBLIC_DATA_DIR)
    )
    promoted: list[tuple[Path, Path]] = []
    try:
        stage_paths: dict[Path, Path] = {}
        for target, content in staged.items():
            relative = target.resolve().relative_to(PUBLIC_DATA_DIR.resolve())
            stage_path = stage_root / relative
            stage_path.parent.mkdir(parents=True, exist_ok=True)
            stage_path.write_bytes(content)
            if _sha256(stage_path.read_bytes()) != _sha256(content):
                raise ValueError(f"Falha de integridade no stage: {relative}.")
            stage_paths[target] = stage_path

        for target in sorted(staged, key=lambda path: str(path)):
            relative = target.resolve().relative_to(PUBLIC_DATA_DIR.resolve())
            backup = backup_root / relative
            backup.parent.mkdir(parents=True, exist_ok=True)
            os.replace(target, backup)
            try:
                os.replace(stage_paths[target], target)
            except Exception:
                os.replace(backup, target)
                raise
            promoted.append((target, backup))
    except Exception:
        for target, backup in reversed(promoted):
            if target.exists():
                target.unlink()
            if backup.exists():
                os.replace(backup, target)
        raise
    finally:
        shutil.rmtree(stage_root, ignore_errors=True)
        shutil.rmtree(backup_root, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--public-data-dir",
        type=Path,
        default=PUBLIC_DATA_DIR,
    )
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    prepared = prepare_stage(args.public_data_dir)
    if args.apply:
        promote_transactionally(prepared["files"])
    report = {
        "cycle": "pne_2014_2024",
        "filesPrepared": len(prepared["files"]),
        "mode": "apply" if args.apply else "check",
        "source": SOURCE_LABEL,
        "snapshotCoverage": prepared["snapshotCoverage"],
        "statusCounts": prepared["statusCounts"],
        "saoLeopoldo": {
            "endYear": prepared["saoLeopoldo"]["end_year"],
            "endValue": prepared["saoLeopoldo"]["end_value"],
            "series": prepared["saoLeopoldo"]["series"],
        },
        "written": bool(args.apply),
    }
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
