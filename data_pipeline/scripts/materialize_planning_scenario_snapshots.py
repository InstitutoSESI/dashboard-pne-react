#!/usr/bin/env python3
"""Materializa os cenários aprovados de persistência para uma UF configurada."""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Any, Callable

import pandas as pd


DATA_PIPELINE_DIR = Path(__file__).resolve().parents[1]
if str(DATA_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_PIPELINE_DIR))

from src.data_loader import (  # noqa: E402
    load_basico_integral_data,
    load_docentes_pos_graduacao_data,
    load_docentes_temporarios_data,
    load_escolas_integral_data,
)
from src.planning_scenarios import (  # noqa: E402
    APPROVED_MODEL,
    INDICATOR_KEYS,
    load_approved_planning_scenarios,
)
from src.pne_state_context import (  # noqa: E402
    load_pne_state_context,
    resolve_state_snapshot_dir,
)
from src.state_config import PIPELINE_STATE_ENV_VAR  # noqa: E402


ROOT = DATA_PIPELINE_DIR / "data" / "planning_scenarios"
EXPERIMENT_VERSION = "projection-engine-v2-shadow-1"
HISTORICAL_YEARS = tuple(range(2015, 2026))
PROJECTED_YEARS = tuple(range(2026, 2037))

Loader = Callable[[], pd.DataFrame]
SPECS: dict[str, tuple[Loader, str, str, str | None]] = {
    "basico_integral": (
        load_basico_integral_data,
        "mat_basico_integral",
        "mat_basico",
        "publica",
    ),
    "escolas_integral": (
        load_escolas_integral_data,
        "escolas_publicas_com_integral",
        "escolas_publicas_total",
        None,
    ),
    "pos_graduacao": (
        load_docentes_pos_graduacao_data,
        "docentes_pos_graduacao",
        "total_docentes",
        "total",
    ),
    "temporarios": (
        load_docentes_temporarios_data,
        "docentes_temporarios",
        "total_docentes",
        "publica",
    ),
}


def _json_bytes(payload: dict[str, Any]) -> bytes:
    return (
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _finite(value: Any, *, context: str) -> float:
    numeric = float(value)
    if not math.isfinite(numeric) or numeric < 0:
        raise ValueError(f"Componente inválido em {context}: {value!r}.")
    return numeric


def _template(indicator_key: str) -> dict[str, Any]:
    path = ROOT / "shadow-projections" / f"{indicator_key}.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    projections = payload.get("projections") or []
    if not projections:
        raise ValueError(f"Template aprovado vazio para {indicator_key}.")
    first = projections[0]
    return {
        "direction": first["direction"],
        "targets": first["targets"],
    }


def _frame_for_indicator(indicator_key: str) -> pd.DataFrame:
    loader, numerator, denominator, dependence = SPECS[indicator_key]
    frame = loader().copy()
    required = {"ano", "municipio", numerator, denominator}
    if not required.issubset(frame.columns):
        raise ValueError(
            f"{indicator_key}: colunas ausentes: {sorted(required - set(frame.columns))}."
        )
    if dependence is not None:
        if "dependencia" not in frame.columns:
            raise ValueError(f"{indicator_key}: dependência administrativa ausente.")
        frame = frame[frame["dependencia"] == dependence].copy()
    frame["ano"] = pd.to_numeric(frame["ano"], errors="coerce")
    frame[numerator] = pd.to_numeric(frame[numerator], errors="coerce")
    frame[denominator] = pd.to_numeric(frame[denominator], errors="coerce")
    frame = frame[frame["ano"].isin(HISTORICAL_YEARS)].copy()
    frame = (
        frame.groupby(["municipio", "ano"], as_index=False)
        .agg({numerator: "sum", denominator: "sum"})
        .sort_values(["municipio", "ano"])
    )
    return frame


def _contract(
    indicator_key: str,
    municipality: str,
    frame: pd.DataFrame,
    template: dict[str, Any],
) -> dict[str, Any]:
    _loader, numerator, denominator, _dependence = SPECS[indicator_key]
    rows = frame[frame["municipio"] == municipality]
    years = tuple(int(value) for value in rows["ano"].tolist())
    if years != HISTORICAL_YEARS:
        raise ValueError(
            f"{indicator_key}/{municipality}: série histórica não cobre 2015–2025."
        )
    historical = []
    for row in rows.itertuples(index=False):
        year = int(getattr(row, "ano"))
        numerator_value = _finite(
            getattr(row, numerator), context=f"{indicator_key}/{municipality}/{year}"
        )
        denominator_value = _finite(
            getattr(row, denominator), context=f"{indicator_key}/{municipality}/{year}"
        )
        if denominator_value <= 0 or numerator_value > denominator_value:
            raise ValueError(
                f"{indicator_key}/{municipality}/{year}: razão inválida."
            )
        historical.append(
            {
                "year": year,
                "numerator": numerator_value,
                "denominator": denominator_value,
                "value": round(100.0 * numerator_value / denominator_value, 6),
            }
        )
    latest = historical[-1]
    projected = [
        {
            "year": year,
            "rawNumerator": latest["numerator"],
            "rawDenominator": latest["denominator"],
            "numerator": latest["numerator"],
            "denominator": latest["denominator"],
            "rawValue": latest["value"],
            "boundedValue": None,
            "displayValue": latest["value"],
            "status": "available",
            "domainViolations": [],
            "limitsApplied": [],
        }
        for year in PROJECTED_YEARS
    ]
    return {
        "indicatorKey": indicator_key,
        "municipality": municipality,
        "strategy": "ratio_of_counts",
        "model": APPROVED_MODEL,
        "status": "available",
        "direction": template["direction"],
        "targetValidationStatus": "configured_unvalidated",
        "sourcePeriod": {"startYear": 2015, "endYear": 2025},
        "projectionPeriod": {"startYear": 2026, "endYear": 2036},
        "targets": template["targets"],
        "historical": historical,
        "projected": projected,
        "summary": {
            "latestObservedYear": 2025,
            "latestObservedValue": latest["value"],
            "projected2036": latest["value"],
            "differenceTo2036": 0.0,
        },
        "diagnostics": {
            "validPointCount": len(historical),
            "missingYearCount": 0,
            "latestDataGap": 0,
            "longestGap": 0,
            "consecutiveYearCount": len(historical),
            "warnings": [],
        },
        "qualityEvidence": {
            "selectedShadowModel": APPROVED_MODEL,
            "validPointCount": len(historical),
            "consecutiveYearCount": len(historical),
            "missingYearCount": 0,
            "latestDataGap": 0,
            "longestGap": 0,
        },
    }


def build_artifacts(state_code: str) -> dict[str, bytes]:
    state = load_pne_state_context(state_code)
    names = tuple(state.municipality_names[code] for code in sorted(state.municipality_ids))
    artifacts: dict[str, bytes] = {}
    for indicator_key in INDICATOR_KEYS:
        frame = _frame_for_indicator(indicator_key)
        contracts = [
            _contract(indicator_key, municipality, frame, _template(indicator_key))
            for municipality in names
        ]
        payload = {
            "experimentVersion": EXPERIMENT_VERSION,
            "mode": "shadow",
            "productionDecision": False,
            "indicatorKey": indicator_key,
            "selectedShadowModel": APPROVED_MODEL,
            "municipalityCount": state.expected_municipality_count,
            "projections": contracts,
        }
        artifacts[f"shadow-projections/{indicator_key}.json"] = _json_bytes(payload)
    return artifacts


def promote(output_dir: Path, artifacts: dict[str, bytes], state_code: str) -> None:
    target = output_dir.resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{target.name}.tmp-", dir=target.parent))
    backup = target.with_name(f".{target.name}.previous")
    try:
        for relative_path, content in sorted(artifacts.items()):
            destination = stage / relative_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(content)
        if backup.exists():
            shutil.rmtree(backup)
        if target.exists():
            os.replace(target, backup)
        os.replace(stage, target)
        state = load_pne_state_context(state_code)
        load_approved_planning_scenarios(
            ROOT,
            tuple(state.municipality_names[code] for code in sorted(state.municipality_ids)),
            state_code=state.state_code,
        )
        if backup.exists():
            shutil.rmtree(backup)
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        if target.exists() and backup.exists():
            shutil.rmtree(target)
            os.replace(backup, target)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", default="RS")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    state = load_pne_state_context(args.state)
    os.environ[PIPELINE_STATE_ENV_VAR] = state.state_code
    artifacts = build_artifacts(state.state_code)
    output = resolve_state_snapshot_dir(ROOT, state.state_code)
    if args.apply:
        promote(output, artifacts, state.state_code)
    print(
        json.dumps(
            {
                "state": state.state_code,
                "municipalityCount": state.expected_municipality_count,
                "fileCount": len(artifacts),
                "output": str(output),
                "mode": "apply" if args.apply else "check",
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
