#!/usr/bin/env python3
"""Rematerializa somente as projeções públicas de atendimento escolar."""

from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Any

import pandas as pd


DATA_PIPELINE_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = DATA_PIPELINE_DIR.parent
PUBLIC_DATA_DIR = REPO_ROOT / "public" / "data"
PLANNING_SCENARIOS_DIR = DATA_PIPELINE_DIR / "data" / "planning_scenarios"
if str(DATA_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_PIPELINE_DIR))

from src.education_attendance import (  # noqa: E402
    AGE_INDICATORS,
    CONTRACT_VERSION as ATTENDANCE_CONTRACT_VERSION,
    build_education_attendance_payload,
)
from src.planning_scenarios import (  # noqa: E402
    load_approved_planning_scenarios,
)
from src.pne_2026_projections import (  # noqa: E402
    INDICATOR_CONFIGS,
    METHODOLOGY_VERSION,
    MUNICIPAL_SHRINK_METHOD,
    MUNICIPAL_SHRINK_NUMERATOR_MODEL,
    PERSISTENCE_METHOD,
    STATE_DAMPED_HOLT_METHOD,
    build_all_projections,
)
from src.pne_state_context import (  # noqa: E402
    PneStateContext,
    load_pne_state_context,
)
from src.state_publication import resolve_public_data_dir  # noqa: E402


EXPECTED_INDICATORS = tuple(AGE_INDICATORS)
EXPECTED_METHODS = {
    "creche": PERSISTENCE_METHOD,
    "pre_escola": PERSISTENCE_METHOD,
    "basico_6_17": MUNICIPAL_SHRINK_METHOD,
    "basico_15_17": STATE_DAMPED_HOLT_METHOD,
    "infantil_0_5": PERSISTENCE_METHOD,
    "obrigatoria_4_17": MUNICIPAL_SHRINK_METHOD,
    "escolar_6_14": PERSISTENCE_METHOD,
}
EXPECTED_TREND_BASES = {
    indicator_key: (
        MUNICIPAL_SHRINK_NUMERATOR_MODEL
        if method == MUNICIPAL_SHRINK_METHOD
        else (
            "state_aggregate_damped_holt"
            if method == STATE_DAMPED_HOLT_METHOD
            else "last_observation_persistence"
        )
    )
    for indicator_key, method in EXPECTED_METHODS.items()
}
EXPECTED_HISTORICAL_YEARS = tuple(range(2014, 2026))
EXPECTED_PROJECTED_YEARS = tuple(range(2026, 2037))


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


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise ValueError(f"Objeto JSON esperado: {path}.")
    return value


def _municipality_entries(
    public_data_dir: Path,
    state: PneStateContext,
) -> list[dict[str, str]]:
    index_path = public_data_dir / "municipios_index.json"
    index = _load_json(index_path)
    raw_entries = index.get("municipios")
    if not isinstance(raw_entries, list):
        raise ValueError("Índice público sem lista de municípios.")
    if len(raw_entries) != state.expected_municipality_count:
        raise ValueError(
            "Cobertura municipal divergente no índice público: "
            f"{len(raw_entries)}."
        )

    entries: list[dict[str, str]] = []
    for raw in raw_entries:
        if not isinstance(raw, dict):
            raise ValueError("Entrada municipal inválida no índice público.")
        name = str(raw.get("nome") or "").strip()
        municipality_id = str(raw.get("id_municipio") or "").strip()
        if not name or len(municipality_id) != 7 or not municipality_id.isdigit():
            raise ValueError(f"Identidade municipal inválida: {raw}.")
        entries.append({"name": name, "id": municipality_id})

    names = [entry["name"] for entry in entries]
    municipality_ids = [entry["id"] for entry in entries]
    if len(set(names)) != state.expected_municipality_count:
        raise ValueError("Nomes municipais duplicados no índice público.")
    if len(set(municipality_ids)) != state.expected_municipality_count:
        raise ValueError("Códigos municipais duplicados no índice público.")
    if frozenset(municipality_ids) != state.municipality_ids:
        raise ValueError(
            f"Universo municipal diverge do registro de {state.state_code}."
        )
    return entries


def _require_finite(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} deve ser numérico.")
    numeric = float(value)
    if not math.isfinite(numeric):
        raise ValueError(f"{label} deve ser finito.")
    return numeric


def _projection_frames_from_public(
    entries: list[dict[str, str]],
    public_root: Path,
) -> dict[str, pd.DataFrame]:
    """Rebuild the seven source frames from versioned projection components.

    This keeps the targeted rematerialization independent from the operational
    database without treating the versioned public files as hand-edited input.
    """

    rows: dict[str, list[dict[str, Any]]] = {
        indicator_key: [] for indicator_key in EXPECTED_INDICATORS
    }
    for entry in entries:
        municipality = entry["name"]
        source_path = (
            public_root
            / "municipios"
            / entry["id"]
            / "index.json"
        )
        source = _load_json(source_path)
        projections = (
            source.get("pne_2026_2036", {}).get("projecoes") or {}
        )
        for indicator_key in EXPECTED_INDICATORS:
            projection = projections.get(indicator_key) or {}
            years = projection.get("historical_years") or []
            numerators = projection.get("historical_numerator") or []
            denominators = projection.get("historical_population") or []
            if not (
                len(years)
                == len(numerators)
                == len(denominators)
                == len(EXPECTED_HISTORICAL_YEARS)
            ):
                raise ValueError(
                    f"{municipality}/{indicator_key}: componentes históricos "
                    "indisponíveis para rematerialização."
                )
            cfg = INDICATOR_CONFIGS[indicator_key]
            for year, numerator, denominator in zip(
                years,
                numerators,
                denominators,
                strict=True,
            ):
                rows[indicator_key].append(
                    {
                        "municipio": municipality,
                        "ano": int(year),
                        cfg["numerator"]: _require_finite(
                            numerator,
                            f"{municipality}/{indicator_key}/{year}.numerator",
                        ),
                        cfg["denominator"]: _require_finite(
                            denominator,
                            f"{municipality}/{indicator_key}/{year}.denominator",
                        ),
                    }
                )
    return {
        indicator_key: pd.DataFrame(indicator_rows)
        for indicator_key, indicator_rows in rows.items()
    }


def _validate_projection(
    municipality: str,
    indicator_key: str,
    projection: dict[str, Any],
) -> None:
    prefix = f"{municipality}/{indicator_key}"
    if projection.get("available") is not True:
        raise ValueError(f"{prefix}: projeção indisponível.")
    if projection.get("methodology_version") != METHODOLOGY_VERSION:
        raise ValueError(f"{prefix}: versão metodológica divergente.")
    expected_method = EXPECTED_METHODS[indicator_key]
    if projection.get("method") != expected_method:
        raise ValueError(f"{prefix}: método de projeção divergente.")
    if (projection.get("trend") or {}).get("selectedBasis") != (
        EXPECTED_TREND_BASES[indicator_key]
    ):
        raise ValueError(f"{prefix}: premissa de matrículas divergente.")
    if tuple(projection.get("historical_years") or ()) != EXPECTED_HISTORICAL_YEARS:
        raise ValueError(f"{prefix}: histórico anual incompleto.")
    if tuple(projection.get("years") or ()) != EXPECTED_PROJECTED_YEARS:
        raise ValueError(f"{prefix}: horizonte projetado divergente.")

    historical_numerator = projection.get("historical_numerator") or []
    projected_numerator = projection.get("projected_numerator") or []
    projected_population = projection.get("projected_population") or []
    projected_percent_raw = projection.get("projected_percent_raw") or []
    projected_percent = projection.get("projected_percent") or []
    if not historical_numerator:
        raise ValueError(f"{prefix}: numerador histórico ausente.")
    if not (
        len(projected_numerator)
        == len(projected_population)
        == len(projected_percent_raw)
        == len(projected_percent)
        == len(EXPECTED_PROJECTED_YEARS)
    ):
        raise ValueError(f"{prefix}: componentes projetados desalinhados.")

    last_numerator = _require_finite(
        historical_numerator[-1],
        f"{prefix}.historical_numerator[-1]",
    )
    for index, (numerator, denominator, percentage) in enumerate(
        zip(
            projected_numerator,
            projected_population,
            projected_percent_raw,
            strict=True,
        )
    ):
        year = EXPECTED_PROJECTED_YEARS[index]
        numeric_numerator = _require_finite(
            numerator,
            f"{prefix}.{year}.numerator",
        )
        numeric_denominator = _require_finite(
            denominator,
            f"{prefix}.{year}.denominator",
        )
        numeric_percentage = _require_finite(
            percentage,
            f"{prefix}.{year}.percentage",
        )
        if (
            expected_method == PERSISTENCE_METHOD
            and numeric_numerator != last_numerator
        ):
            raise ValueError(f"{prefix}: numerador não persiste em {year}.")
        if numeric_denominator <= 0:
            raise ValueError(f"{prefix}: denominador inválido em {year}.")
        # O percentual é calculado antes de numerador e denominador serem
        # arredondados para uma casa na camada pública. Validamos o intervalo
        # compatível com esse arredondamento, em vez de recompor a razão a
        # partir dos componentes já arredondados.
        numerator_min = max(0.0, numeric_numerator - 0.0500001)
        numerator_max = numeric_numerator + 0.0500001
        denominator_min = max(1e-12, numeric_denominator - 0.0500001)
        denominator_max = numeric_denominator + 0.0500001
        percentage_min = numerator_min / denominator_max * 100
        percentage_max = numerator_max / denominator_min * 100
        if not (
            percentage_min - 0.0051
            <= numeric_percentage
            <= percentage_max + 0.0051
        ):
            raise ValueError(f"{prefix}: percentual inconsistente em {year}.")
        display_percentage = _require_finite(
            projected_percent[index],
            f"{prefix}.{year}.displayPercentage",
        )
        if display_percentage != min(100.0, numeric_percentage):
            raise ValueError(f"{prefix}: teto público inconsistente em {year}.")

    historical_raw = projection.get("historical_percent_raw") or []
    historical_display = projection.get("historical_percent") or []
    if not (
        len(historical_raw)
        == len(historical_display)
        == len(EXPECTED_HISTORICAL_YEARS)
    ):
        raise ValueError(f"{prefix}: percentuais históricos desalinhados.")
    for index, raw_value in enumerate(historical_raw):
        raw_percentage = _require_finite(
            raw_value,
            f"{prefix}.historicalRaw[{index}]",
        )
        display_percentage = _require_finite(
            historical_display[index],
            f"{prefix}.historicalDisplay[{index}]",
        )
        if display_percentage != min(100.0, raw_percentage):
            raise ValueError(f"{prefix}: teto histórico inconsistente.")

    uncertainty = projection.get("uncertainty") or {}
    if (
        uncertainty.get("status") != "backtested_no_probability_interval"
        or uncertainty.get("interval") is not None
        or not isinstance(uncertainty.get("backtest"), dict)
    ):
        raise ValueError(f"{prefix}: incerteza não declarada corretamente.")


def _validate_attendance_contract(
    municipality: str,
    contract: dict[str, Any],
) -> int:
    if contract.get("contractVersion") != ATTENDANCE_CONTRACT_VERSION:
        raise ValueError(f"{municipality}: contrato de atendimento divergente.")
    if contract.get("municipality") != municipality:
        raise ValueError(f"{municipality}: identidade divergente no atendimento.")
    age_coverage = contract.get("ageCoverage")
    if not isinstance(age_coverage, dict):
        raise ValueError(f"{municipality}: ageCoverage ausente.")
    if tuple(age_coverage) != EXPECTED_INDICATORS:
        raise ValueError(f"{municipality}: indicadores de atendimento divergentes.")

    displayable_count = 0
    for indicator_key, indicator in age_coverage.items():
        scenario = indicator.get("scenario") or {}
        if scenario.get("type") != "conditional_projection":
            raise ValueError(
                f"{municipality}/{indicator_key}: tipo de cenário divergente."
            )
        if scenario.get("status") != "available":
            raise ValueError(
                f"{municipality}/{indicator_key}: cenário indisponível."
            )
        if scenario.get("method") != EXPECTED_METHODS[indicator_key]:
            raise ValueError(
                f"{municipality}/{indicator_key}: método público divergente."
            )
        projected = scenario.get("projected") or []
        if tuple(point.get("year") for point in projected) != EXPECTED_PROJECTED_YEARS:
            raise ValueError(
                f"{municipality}/{indicator_key}: horizonte público divergente."
            )
        observed = indicator.get("observed") or {}
        observed_value = _require_finite(
            observed.get("rawValue"),
            f"{municipality}/{indicator_key}.observed.rawValue",
        )
        future_values = []
        for point in projected:
            raw_value = _require_finite(
                point.get("rawValue"),
                f"{municipality}/{indicator_key}.{point.get('year')}.rawValue",
            )
            display_value = _require_finite(
                point.get("displayValue"),
                f"{municipality}/{indicator_key}.{point.get('year')}.displayValue",
            )
            if display_value != min(100.0, raw_value):
                raise ValueError(
                    f"{municipality}/{indicator_key}: teto público divergente."
                )
            future_values.append(raw_value)
        if any(value != observed_value for value in future_values):
            displayable_count += 1

    return displayable_count


def _without_projection_targets(payload: dict[str, Any]) -> dict[str, Any]:
    comparable = deepcopy(payload)
    cycle = comparable.get("pne_2026_2036")
    if isinstance(cycle, dict):
        cycle.pop("projecoes", None)
    education = comparable.get("educacao")
    if isinstance(education, dict):
        education.pop("atendimento_cenarios", None)
    return comparable


def prepare_stage(
    public_data_dir: Path,
    state_code: str = "RS",
) -> dict[str, Any]:
    state = load_pne_state_context(state_code)
    public_root = public_data_dir.resolve()
    entries = _municipality_entries(public_root, state)
    municipality_names = [entry["name"] for entry in entries]

    frames = _projection_frames_from_public(entries, public_root)
    projections = build_all_projections(
        municipality_names,
        dataframes=frames,
        state_code=state.state_code,
    )
    if set(projections) != set(municipality_names):
        raise ValueError("Cobertura municipal divergente nas projeções.")
    planning = load_approved_planning_scenarios(
        PLANNING_SCENARIOS_DIR,
        municipality_names,
        state_code=state.state_code,
    )
    attendance = build_education_attendance_payload(
        {"municipios": projections},
        planning,
        municipality_names,
    )
    attendance_by_municipality = attendance.get("municipios") or {}
    if set(attendance_by_municipality) != set(municipality_names):
        raise ValueError("Cobertura municipal divergente no atendimento.")

    staged: dict[Path, bytes] = {}
    changed_files = 0
    displayable_scenarios = 0
    above_100_scenarios = 0
    aggregate_hash = hashlib.sha256()
    municipality_summaries: dict[str, Any] = {}

    for entry in entries:
        municipality = entry["name"]
        municipality_id = entry["id"]
        target = (
            public_root
            / "municipios"
            / municipality_id
            / "index.json"
        )
        target.resolve().relative_to(public_root)
        original = _load_json(target)
        if (
            str(original.get("id_municipio") or "") != municipality_id
            or str(original.get("municipio") or "") != municipality
        ):
            raise ValueError(
                f"{municipality_id}: identidade divergente no arquivo municipal."
            )

        municipal_projections = projections[municipality]
        if tuple(municipal_projections) != EXPECTED_INDICATORS:
            raise ValueError(
                f"{municipality}: indicadores projetados divergentes."
            )
        for indicator_key, projection in municipal_projections.items():
            _validate_projection(municipality, indicator_key, projection)

        attendance_contract = attendance_by_municipality[municipality]
        municipal_displayable = _validate_attendance_contract(
            municipality,
            attendance_contract,
        )
        if municipal_displayable == 0:
            raise ValueError(
                f"{municipality}: nenhum cenário produziria trajetória "
                "publicável."
            )
        displayable_scenarios += municipal_displayable
        above_100_scenarios += sum(
            any(
                float(point["rawValue"]) > 100
                for point in indicator["scenario"]["projected"]
            )
            for indicator in attendance_contract["ageCoverage"].values()
        )

        updated = deepcopy(original)
        updated.setdefault("pne_2026_2036", {})["projecoes"] = (
            municipal_projections
        )
        updated.setdefault("educacao", {})["atendimento_cenarios"] = (
            attendance_contract
        )
        if _without_projection_targets(original) != _without_projection_targets(
            updated
        ):
            raise AssertionError(
                f"{municipality}: rematerialização alterou campos fora do escopo."
            )

        content = _json_bytes(updated)
        original_content = target.read_bytes()
        if content != original_content:
            changed_files += 1
        staged[target] = content
        aggregate_hash.update(municipality_id.encode("ascii"))
        aggregate_hash.update(b"\0")
        aggregate_hash.update(content)
        aggregate_hash.update(b"\0")
        sample_ids = {"RS": ("4318705", "saoLeopoldo"), "AL": ("2704302", "maceio")}
        sample_id, sample_key = sample_ids.get(
            state.state_code, (next(iter(sorted(state.municipality_ids))), "sample")
        )
        if municipality_id == sample_id:
            municipality_summaries[sample_key] = {
                "displayableScenarios": municipal_displayable,
                "projected2036": {
                    indicator_key: {
                        "displayValue": indicator["scenario"]["projected"][-1][
                            "displayValue"
                        ],
                        "rawValue": indicator["scenario"]["projected"][-1][
                            "rawValue"
                        ],
                    }
                    for indicator_key, indicator in attendance_contract[
                        "ageCoverage"
                    ].items()
                },
            }

    if len(staged) != state.expected_municipality_count:
        raise ValueError("Quantidade de arquivos preparados divergente.")
    return {
        "files": staged,
        "summary": {
            "municipalityCount": len(entries),
            "indicatorCount": len(EXPECTED_INDICATORS),
            "displayableScenarioCount": displayable_scenarios,
            "above100ScenarioCount": above_100_scenarios,
            "changedFileCount": changed_files,
            "methods": {
                indicator_key: EXPECTED_METHODS[indicator_key]
                for indicator_key in EXPECTED_INDICATORS
            },
            "methodologyVersion": METHODOLOGY_VERSION,
            "aggregateSha256": aggregate_hash.hexdigest(),
            **municipality_summaries,
        },
    }


def promote_transactionally(
    staged: dict[Path, bytes],
    public_data_dir: Path,
) -> None:
    public_root = public_data_dir.resolve()
    stage_root = Path(
        tempfile.mkdtemp(
            prefix=".attendance-projections-stage-",
            dir=public_root,
        )
    )
    backup_root = Path(
        tempfile.mkdtemp(
            prefix=".attendance-projections-backup-",
            dir=public_root,
        )
    )
    promoted: list[tuple[Path, Path]] = []
    try:
        stage_paths: dict[Path, Path] = {}
        for target, content in staged.items():
            relative = target.resolve().relative_to(public_root)
            if (
                len(relative.parts) != 3
                or relative.parts[0] != "municipios"
                or relative.parts[2] != "index.json"
            ):
                raise ValueError(f"Destino fora do escopo: {relative}.")
            stage_path = stage_root / relative
            stage_path.parent.mkdir(parents=True, exist_ok=True)
            stage_path.write_bytes(content)
            if _sha256(stage_path.read_bytes()) != _sha256(content):
                raise ValueError(f"Falha de integridade no stage: {relative}.")
            stage_paths[target] = stage_path

        for target in sorted(staged, key=lambda path: str(path)):
            relative = target.resolve().relative_to(public_root)
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
    parser = argparse.ArgumentParser(
        description=(
            "Recalcula, valida e rematerializa somente as projeções de "
            "atendimento nos arquivos municipais da UF selecionada."
        )
    )
    parser.add_argument("--state", default="RS")
    parser.add_argument(
        "--public-data-dir",
        type=Path,
        default=None,
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Promove transacionalmente os arquivos validados.",
    )
    args = parser.parse_args()

    public_data_dir = args.public_data_dir or resolve_public_data_dir(args.state)
    prepared = prepare_stage(public_data_dir, state_code=args.state)
    if args.apply:
        promote_transactionally(
            prepared["files"],
            public_data_dir,
        )
    print(
        json.dumps(
            {
                **prepared["summary"],
                "mode": "apply" if args.apply else "check",
                "written": bool(args.apply),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
