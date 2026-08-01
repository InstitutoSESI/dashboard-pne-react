from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
import traceback
from collections.abc import Mapping, Sequence
from contextlib import contextmanager
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
EXPORT_DIR = BASE_DIR / "export" / "data"

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.municipal_inequality import (  # noqa: E402
    DOCUMENT_SCHEMA_VERSION as INEQUALITY_SCHEMA_VERSION,
    build_urban_rural_integral_pilot,
)


def _generated_at() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _safe_timestamp() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y%m%d_%H%M%S")


def _is_nullish(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float):
        return math.isnan(value) or math.isinf(value)
    try:
        result = pd.isna(value)
    except (TypeError, ValueError):
        return False
    return isinstance(result, bool) and result


def _json_safe(value: Any) -> Any:
    if _is_nullish(value):
        return None

    if isinstance(value, (str, bool, int)):
        return value

    if isinstance(value, float):
        return value if math.isfinite(value) else None

    if isinstance(value, (datetime, date)):
        return value.isoformat()

    if hasattr(value, "item") and not isinstance(value, (str, bytes, bytearray)):
        try:
            return _json_safe(value.item())
        except (TypeError, ValueError):
            pass

    if isinstance(value, Mapping):
        return {
            str(key): _json_safe(child)
            for key, child in value.items()
            if not callable(child)
        }

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_json_safe(child) for child in value]

    if callable(value):
        return None

    return str(value)


class TimingProfile:
    """Collects in-process timings without changing the export behavior."""

    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled
        self.durations: dict[str, float] = {}

    @contextmanager
    def measure(self, name: str):
        if not self.enabled:
            yield
            return
        start = time.perf_counter()
        try:
            yield
        finally:
            self.durations[name] = self.durations.get(name, 0.0) + (
                time.perf_counter() - start
            )

    def print_summary(self) -> None:
        if not self.enabled:
            return
        print("\nPerfil de desempenho")
        for name, duration in sorted(
            self.durations.items(), key=lambda item: item[1], reverse=True
        ):
            print(f"  - {name}: {duration:.3f}s")


class ResultsCache:
    """Execution-local cache shared by result and ranking exporters.

    The view modules also cache database-backed work, but that cache can be disabled
    in development. Keeping this small cache here guarantees that rankings reuse the
    exact result map already calculated for the same cycle and municipality.
    """

    def __init__(self) -> None:
        self._results: dict[tuple[str, str, tuple[str, ...] | None], Mapping[str, Any]] = {}

    def get(
        self,
        *,
        cycle_key: str,
        cycle_module: Any,
        municipio: str,
        indicator_keys: tuple[str, ...] | None,
    ) -> Mapping[str, Any]:
        cache_key = (cycle_key, municipio, indicator_keys)
        if cache_key not in self._results:
            if indicator_keys is None:
                self._results[cache_key] = cycle_module._calculate_results(municipio)
            else:
                self._results[cache_key] = cycle_module._calculate_results_for_indicators(
                    municipio, indicator_keys
                )
        return self._results[cache_key]


def _write_json(path: Path, payload: Any, profile: TimingProfile | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if profile is None:
        path.write_text(
            json.dumps(_json_safe(payload), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    else:
        with profile.measure("serialização"):
            path.write_text(
                json.dumps(_json_safe(payload), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
    try:
        display_path = path.relative_to(BASE_DIR)
    except ValueError:
        display_path = path
    print(f"  arquivo gerado: {display_path}")


def _build_item_lookup(cycle_module: Any) -> dict[str, dict[str, Any]]:
    return {
        item["key"]: item
        for category_key in cycle_module.CATEGORY_ORDER
        for item in cycle_module.INDICADORES[category_key]["items"]
    }


def _serialize_item(item: Mapping[str, Any]) -> dict[str, Any]:
    return {
        str(key): _json_safe(value)
        for key, value in item.items()
        if key != "compute" and not callable(value)
    }


def _serialize_categories(
    cycle_module: Any, indicator_keys: set[str] | None = None
) -> list[dict[str, Any]]:
    categories = []
    for category_key in cycle_module.CATEGORY_ORDER:
        category = cycle_module.INDICADORES[category_key]
        category_payload = {
            str(key): _json_safe(value)
            for key, value in category.items()
            if key != "items" and not callable(value)
        }
        category_payload["key"] = category_key
        category_payload["items"] = [
            _serialize_item(item)
            for item in category.get("items", [])
            if indicator_keys is None or item["key"] in indicator_keys
        ]
        if indicator_keys is not None and not category_payload["items"]:
            continue
        categories.append(category_payload)
    return categories


def _safe_display(
    *,
    item: Mapping[str, Any],
    result: Mapping[str, Any],
    shared: Any,
    municipio: str,
    cycle_key: str,
    indicator_key: str,
    errors: list[dict[str, Any]],
) -> dict[str, Any]:
    display: dict[str, Any] = {}
    tracks_goal = shared._tracks_goal(item, result)

    def assign(field: str, fn: Any) -> None:
        try:
            display[field] = fn()
        except Exception as exc:  # noqa: BLE001 - export should continue per item.
            errors.append(
                {
                    "cycle": cycle_key,
                    "municipio": municipio,
                    "indicator": indicator_key,
                    "stage": f"display.{field}",
                    "error": str(exc),
                }
            )
            display[field] = None

    assign(
        "start_value",
        lambda: shared._format_metric_value(item, result.get("start_value")),
    )
    assign("end_value", lambda: shared._format_metric_value(item, result.get("end_value")))
    assign("variation", lambda: shared._variation_text(result, item))
    if tracks_goal:
        assign(
            "distance",
            lambda: shared._format_metric_distance(item, result.get("distance")),
        )
    custom_status = (result.get("display") or {}).get("status")
    assign("status", lambda: custom_status or shared._status_theme(result).get("text"))
    custom_reference = (result.get("display") or {}).get("reference")
    if custom_reference:
        display["reference"] = custom_reference
    custom_warning = (result.get("display") or {}).get("warning")
    if custom_warning:
        display["warning"] = custom_warning
    assign("interpretation", lambda: shared._interpretation(item, result))

    return display


def _serialize_result(
    *,
    result: Mapping[str, Any],
    item: Mapping[str, Any] | None,
    shared: Any,
    municipio: str,
    cycle_key: str,
    indicator_key: str,
    errors: list[dict[str, Any]],
) -> dict[str, Any]:
    fields = (
        "available",
        "start_year",
        "end_year",
        "start_value",
        "end_value",
        "raw_delta",
        "progress_delta",
        "meta",
        "meta_label",
        "direction",
        "distance",
        "atingida",
        "tracks_goal",
        "monitoring_mode",
        "show_in_cycle",
        "include_in_cycle_summary",
        "coverage",
        "value_mode",
        "reference_year",
        "reference_value",
        "reference_label",
        "reference_difference",
        "acima_de_100",
        "acima_de_100_anos",
        "series",
        "trend",
        "meta_references",
        "source",
        "source_id",
        "network",
        "origin_files",
        "updated_at",
    )
    payload = {field: result.get(field) for field in fields if field in result}
    if item is not None and not shared._tracks_goal(item, result):
        payload.pop("distance", None)

    if item is not None:
        payload["display"] = _safe_display(
            item=item,
            result=result,
            shared=shared,
            municipio=municipio,
            cycle_key=cycle_key,
            indicator_key=indicator_key,
            errors=errors,
        )

    return _json_safe(payload)


def _export_cycle_results(
    *,
    cycle_key: str,
    cycle_module: Any,
    municipios: list[str],
    shared: Any,
    errors: list[dict[str, Any]],
    results_cache: ResultsCache,
    indicator_keys: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    item_lookup = _build_item_lookup(cycle_module)
    exported = 0
    municipio_payloads: dict[str, Any] = {}

    print(f"\nProcessando ciclo {cycle_key}...")
    for index, municipio in enumerate(municipios, start=1):
        print(f"  [{index}/{len(municipios)}] {municipio}")
        try:
            results = results_cache.get(
                cycle_key=cycle_key,
                cycle_module=cycle_module,
                municipio=municipio,
                indicator_keys=indicator_keys,
            )
        except Exception as exc:  # noqa: BLE001 - export should continue per city.
            errors.append(
                {
                    "cycle": cycle_key,
                    "municipio": municipio,
                    "stage": "calculate_results",
                    "error": str(exc),
                    "traceback": traceback.format_exc(limit=4),
                }
            )
            municipio_payloads[municipio] = {"results": {}, "error": str(exc)}
            continue

        serialized_results = {}
        for indicator_key, result in results.items():
            try:
                serialized_results[indicator_key] = _serialize_result(
                    result=result,
                    item=item_lookup.get(indicator_key),
                    shared=shared,
                    municipio=municipio,
                    cycle_key=cycle_key,
                    indicator_key=indicator_key,
                    errors=errors,
                )
            except Exception as exc:  # noqa: BLE001 - export should continue per item.
                errors.append(
                    {
                        "cycle": cycle_key,
                        "municipio": municipio,
                        "indicator": indicator_key,
                        "stage": "serialize_result",
                        "error": str(exc),
                        "traceback": traceback.format_exc(limit=4),
                    }
                )
                serialized_results[indicator_key] = {"error": str(exc)}

        municipio_payloads[municipio] = {"results": serialized_results}
        exported += 1

    return {
        "generated_at": _generated_at(),
        "cycle": cycle_key,
        "total_municipios": len(municipios),
        "municipios_exportados": exported,
        "municipios": municipio_payloads,
    }


def _export_indicator_details(
    *,
    municipios: list[str],
    shared: Any,
    errors: list[dict[str, Any]],
) -> dict[str, Any]:
    exported = 0
    municipio_payloads: dict[str, Any] = {}

    print("\nProcessando dados complementares...")
    for index, municipio in enumerate(municipios, start=1):
        try:
            details = shared._build_indicator_details(municipio)
            municipio_payloads[municipio] = {"indicator_details": details}
            exported += 1
        except Exception as exc:  # noqa: BLE001 - export should continue per city.
            errors.append(
                {
                    "cycle": "indicator_details",
                    "municipio": municipio,
                    "stage": "indicator_details",
                    "error": str(exc),
                    "traceback": traceback.format_exc(limit=4),
                }
            )
            municipio_payloads[municipio] = {"indicator_details": {}, "error": str(exc)}

    return {
        "generated_at": _generated_at(),
        "total_municipios": len(municipios),
        "municipios_exportados": exported,
        "municipios": municipio_payloads,
    }


def _ranking_display(
    *,
    item: Mapping[str, Any],
    result: Mapping[str, Any],
    shared: Any,
    municipio: str,
    cycle_key: str,
    indicator_key: str,
    errors: list[dict[str, Any]],
) -> dict[str, Any]:
    return _safe_display(
        item=item,
        result=result,
        shared=shared,
        municipio=municipio,
        cycle_key=cycle_key,
        indicator_key=indicator_key,
        errors=errors,
    )


def _ranking_row(
    *,
    category_key: str,
    item: Mapping[str, Any],
    result: Mapping[str, Any],
    shared: Any,
    municipio: str,
    cycle_key: str,
    errors: list[dict[str, Any]],
) -> dict[str, Any]:
    indicator_key = item["key"]
    return {
        "indicator_key": indicator_key,
        "label": item.get("label"),
        "sub": item.get("sub"),
        "category": category_key,
        "progress_delta": result.get("progress_delta"),
        "distance": result.get("distance"),
        "atingida": result.get("atingida"),
        "available": result.get("available"),
        "value_mode": shared._value_mode(item),
        "start_year": result.get("start_year"),
        "end_year": result.get("end_year"),
        "start_value": result.get("start_value"),
        "end_value": result.get("end_value"),
        "display": _ranking_display(
            item=item,
            result=result,
            shared=shared,
            municipio=municipio,
            cycle_key=cycle_key,
            indicator_key=indicator_key,
            errors=errors,
        ),
    }


def _sort_number(value: Any, default: float = 0.0) -> float:
    if _is_nullish(value):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _build_rankings_payload_for_municipio(
    *,
    cycle_key: str,
    cycle_module: Any,
    municipio: str,
    results: Mapping[str, Mapping[str, Any]],
    shared: Any,
    errors: list[dict[str, Any]],
) -> dict[str, Any]:
    categories_payload: dict[str, Any] = {}

    for category_key in cycle_module.CATEGORY_ORDER:
        category = cycle_module.INDICADORES[category_key]

        if cycle_key == "pne_2026_2036":
            progress_rows = []
            attention_rows = []
            for item in category["items"]:
                result = results.get(item["key"], {})
                if not result.get("available") or not shared._tracks_goal(item, result):
                    continue
                row = _ranking_row(
                    category_key=category_key,
                    item=item,
                    result=result,
                    shared=shared,
                    municipio=municipio,
                    cycle_key=cycle_key,
                    errors=errors,
                )
                if item["key"] == "subsequente_expansao":
                    row["distance"] = -cycle_module._subsequente_distance_value(result)
                    row["value_mode"] = "growth_percent"
                if shared._has_time_comparison(result):
                    progress_rows.append(row)
                if result.get("distance") is not None:
                    attention_rows.append(row)

            top_avancos = sorted(
                progress_rows,
                key=lambda row: _sort_number(row.get("progress_delta")),
                reverse=True,
            )[:3]
            top_atencao = sorted(
                [row for row in attention_rows if not row.get("atingida")],
                key=lambda row: _sort_number(row.get("distance")),
            )[:3]
        else:
            ranking_rows = []
            for item in category["items"]:
                result = results.get(item["key"], {})
                if (
                    not result.get("available")
                    or not shared._tracks_goal(item, result)
                    or not shared._has_time_comparison(result)
                ):
                    continue
                ranking_rows.append(
                    _ranking_row(
                        category_key=category_key,
                        item=item,
                        result=result,
                        shared=shared,
                        municipio=municipio,
                        cycle_key=cycle_key,
                        errors=errors,
                    )
                )

            top_avancos = sorted(
                ranking_rows,
                key=lambda row: _sort_number(row.get("progress_delta")),
                reverse=True,
            )[:3]
            top_atencao = sorted(
                [row for row in ranking_rows if not row.get("atingida")],
                key=lambda row: _sort_number(row.get("distance")),
            )[:3]

        categories_payload[category_key] = {
            "label": category.get("label"),
            "accent": category.get("accent"),
            "top_avancos": top_avancos,
            "top_atencao": top_atencao,
        }

    return {"categories": categories_payload}


def _export_cycle_rankings(
    *,
    cycle_key: str,
    cycle_module: Any,
    municipios: list[str],
    shared: Any,
    errors: list[dict[str, Any]],
    results_cache: ResultsCache,
) -> dict[str, Any]:
    exported = 0
    municipio_payloads: dict[str, Any] = {}

    print(f"\nProcessando rankings {cycle_key}...")
    for index, municipio in enumerate(municipios, start=1):
        print(f"  [{index}/{len(municipios)}] {municipio}")
        try:
            results = results_cache.get(
                cycle_key=cycle_key,
                cycle_module=cycle_module,
                municipio=municipio,
                indicator_keys=None,
            )
            municipio_payloads[municipio] = _build_rankings_payload_for_municipio(
                cycle_key=cycle_key,
                cycle_module=cycle_module,
                municipio=municipio,
                results=results,
                shared=shared,
                errors=errors,
            )
            exported += 1
        except Exception as exc:  # noqa: BLE001 - export should continue per city.
            errors.append(
                {
                    "cycle": cycle_key,
                    "municipio": municipio,
                    "stage": "rankings",
                    "error": str(exc),
                    "traceback": traceback.format_exc(limit=4),
                }
            )
            municipio_payloads[municipio] = {"categories": {}, "error": str(exc)}

    return {
        "generated_at": _generated_at(),
        "cycle": cycle_key,
        "total_municipios": len(municipios),
        "municipios_exportados": exported,
        "municipios": municipio_payloads,
    }


def _export_inequality_documents(
    *, municipios: list[str], generated_at: str
) -> dict[str, Any]:
    """Gera o envelope mínimo; os recortes são materializados após Educação."""

    return {
        "schemaVersion": INEQUALITY_SCHEMA_VERSION,
        "generated_at": generated_at,
        "total_municipios": len(municipios),
        "municipios": {
            municipio: {
                "schemaVersion": INEQUALITY_SCHEMA_VERSION,
                "generatedAt": generated_at,
                "municipalityName": municipio,
                "inequalityPilot": build_urban_rural_integral_pilot(None),
            }
            for municipio in municipios
        },
    }


def _export_fundeb_data(
    municipios: list[str],
    errors: list[dict[str, Any]],
) -> dict[str, Any]:
    from src.data_loader import load_fundeb_data
    from src import fundeb_export

    exported = 0
    municipio_payloads: dict[str, Any] = {}

    print("\nProcessando FUNDEB...")
    try:
        fundeb_df = load_fundeb_data()
    except Exception as exc:  # noqa: BLE001
        errors.append({"stage": "load_fundeb_data", "error": str(exc)})
        return {
            "generated_at": _generated_at(),
            "total_municipios": len(municipios),
            "municipios_exportados": 0,
            "municipios": {},
        }

    if "municipio" not in fundeb_df.columns:
        errors.append({"stage": "load_fundeb_data", "error": "Coluna 'municipio' ausente."})
        return {
            "generated_at": _generated_at(),
            "total_municipios": len(municipios),
            "municipios_exportados": 0,
            "municipios": {},
        }

    fundeb_df["municipio"] = fundeb_df["municipio"].astype(str).str.strip()

    for index, municipio in enumerate(municipios, start=1):
        print(f"  [{index}/{len(municipios)}] {municipio}")
        try:
            data = fundeb_export.extract_fundeb_for_municipio(municipio, fundeb_df)
            municipio_payloads[municipio] = {"fundeb": data} if data is not None else {"fundeb": None}
            if data is not None:
                exported += 1
        except Exception as exc:  # noqa: BLE001
            errors.append(
                {
                    "stage": "fundeb",
                    "municipio": municipio,
                    "error": str(exc),
                }
            )
            municipio_payloads[municipio] = {"fundeb": None}

    return {
        "generated_at": _generated_at(),
        "total_municipios": len(municipios),
        "municipios_exportados": exported,
        "municipios": municipio_payloads,
    }


def _export_pnate_data(
    municipios: list[str],
    errors: list[dict[str, Any]],
) -> dict[str, Any]:
    from src.data_loader import load_pnate_data
    from src import pnate_export

    exported = 0
    municipio_payloads: dict[str, Any] = {}

    print("\nProcessando PNATE...")
    try:
        pnate_df = load_pnate_data()
    except Exception as exc:  # noqa: BLE001
        errors.append({"stage": "load_pnate_data", "error": str(exc)})
        return {
            "generated_at": _generated_at(),
            "total_municipios": len(municipios),
            "municipios_exportados": 0,
            "municipios": {},
        }

    if "municipio" not in pnate_df.columns:
        errors.append({"stage": "load_pnate_data", "error": "Coluna 'municipio' ausente."})
        return {
            "generated_at": _generated_at(),
            "total_municipios": len(municipios),
            "municipios_exportados": 0,
            "municipios": {},
        }

    pnate_df["municipio"] = pnate_df["municipio"].astype(str).str.strip()

    for index, municipio in enumerate(municipios, start=1):
        print(f"  [{index}/{len(municipios)}] {municipio}")
        try:
            data = pnate_export.extract_pnate_for_municipio(municipio, pnate_df)
            municipio_payloads[municipio] = {"pnate": data} if data is not None else {"pnate": None}
            if data is not None:
                exported += 1
        except Exception as exc:  # noqa: BLE001
            errors.append(
                {
                    "stage": "pnate",
                    "municipio": municipio,
                    "error": str(exc),
                }
            )
            municipio_payloads[municipio] = {"pnate": None}

    return {
        "generated_at": _generated_at(),
        "total_municipios": len(municipios),
        "municipios_exportados": exported,
        "municipios": municipio_payloads,
    }


def _export_projections(
    *,
    municipios: list[str],
    municipio_ids: dict[str, str] | None,
    errors: list[dict[str, Any]],
) -> dict[str, Any]:
    from src.pne_2026_projections import build_all_projections

    print("\nProcessando linhas de base de persistência...")
    try:
        projections = build_all_projections(municipios)
    except Exception as exc:
        errors.append({"stage": "projections", "error": str(exc), "traceback": traceback.format_exc(limit=6)})
        return {
            "generated_at": _generated_at(),
            "cycle": "pne_2026_2036",
            "total_municipios": len(municipios),
            "municipios_exportados": 0,
            "municipios": {},
        }

    exported = sum(1 for p in projections.values() if any(v.get("available") for v in p.values()))
    return {
        "generated_at": _generated_at(),
        "cycle": "pne_2026_2036",
        "total_municipios": len(municipios),
        "municipios_exportados": exported,
        "municipios": _json_safe(projections),
    }


def _export_planning_scenarios(*, municipios: list[str]) -> dict[str, Any]:
    from src.planning_scenarios import load_approved_planning_scenarios

    print("\nProcessando cenários de planejamento aprovados...")
    artifact_root = BASE_DIR / "data" / "planning_scenarios"
    return load_approved_planning_scenarios(artifact_root, municipios)


def _export_education_attendance(
    *,
    municipios: list[str],
    projections_payload: dict[str, Any],
    planning_scenarios_payload: dict[str, Any],
) -> dict[str, Any]:
    from src.education_attendance import build_education_attendance_payload

    print("\nProcessando contrato de atendimento e cenários...")
    return build_education_attendance_payload(
        projections_payload,
        planning_scenarios_payload,
        municipios,
    )


def _export_state_reference(
    cycle: str,
    errors: list[dict[str, Any]],
) -> dict[str, Any]:
    """Exporta a referência do RS sempre sobre o universo estadual completo."""

    if cycle == "pne_2014_2024":
        from src.pne_2014_state_reference import build_state_reference

        methodology_version = "pne2014-rs-reference-v1"
    else:
        from src.pne_state_reference import build_state_reference

        methodology_version = "pne2026-rs-reference-v3"

    try:
        payload = build_state_reference()
    except Exception as exc:  # noqa: BLE001 - preserve a valid artifact for diagnosis.
        errors.append(
            {
                "stage": f"state_reference:{cycle}",
                "error": str(exc),
                "traceback": traceback.format_exc(limit=6),
            }
        )
        payload = {
            "cycle": cycle,
            "state": "RS",
            "state_name": "Rio Grande do Sul",
            "municipalities_expected": 497,
            "methodology_version": methodology_version,
            "registry": {},
            "indicators": {},
            "projections": {},
            "totals_audit": [],
            "source_load_errors": {"state_reference": str(exc)},
            "notes": "Falha ao construir a referência estadual; comparação indisponível.",
        }
    payload["generated_at"] = _generated_at()
    return payload


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Exporta os dados calculados da plataforma para JSON estático."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limita a quantidade de municípios exportados, útil para validação.",
    )
    parser.add_argument(
        "--municipio",
        action="append",
        default=None,
        help="Exporta apenas o município informado. Pode ser usado mais de uma vez.",
    )
    parser.add_argument(
        "--check-connection",
        action="store_true",
        help="Testa backend, variáveis de ambiente e load_municipios sem exportar.",
    )
    parser.add_argument(
        "--include-derived",
        action="store_true",
        help="Exporta também rankings por município e diagnóstico.",
    )
    parser.add_argument(
        "--cycle",
        action="append",
        default=None,
        help="Restringe a exportação ao ciclo informado. Pode ser usado mais de uma vez.",
    )
    parser.add_argument(
        "--indicator",
        action="append",
        default=None,
        help="Restringe a exportação aos indicadores informados; requer --cycle.",
    )
    parser.add_argument(
        "--profile",
        action="store_true",
        help="Mostra os tempos das etapas executadas.",
    )
    return parser.parse_args()


def _select_cycles_and_indicators(
    *,
    requested_cycles: list[str] | None,
    requested_indicators: list[str] | None,
    cycle_modules: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, tuple[str, ...] | None]]:
    """Validates target flags before any JSON is written."""

    if requested_indicators and not requested_cycles:
        raise ValueError("--indicator requer ao menos um --cycle.")

    cycle_keys = requested_cycles or list(cycle_modules)
    unknown_cycles = sorted(set(cycle_keys) - set(cycle_modules))
    if unknown_cycles:
        raise ValueError(f"Ciclo inexistente: {', '.join(unknown_cycles)}.")

    selected_modules = {cycle_key: cycle_modules[cycle_key] for cycle_key in cycle_keys}
    selected_indicators: dict[str, tuple[str, ...] | None] = {}
    for cycle_key, cycle_module in selected_modules.items():
        if not requested_indicators:
            selected_indicators[cycle_key] = None
            continue
        available = set(_build_item_lookup(cycle_module))
        missing = sorted(set(requested_indicators) - available)
        if missing:
            raise ValueError(
                f"Indicador inexistente no ciclo {cycle_key}: {', '.join(missing)}."
            )
        selected_indicators[cycle_key] = tuple(dict.fromkeys(requested_indicators))

    return selected_modules, selected_indicators


def _validate_targeted_export(
    *,
    export_dir: Path,
    cycle_indicators: Mapping[str, tuple[str, ...] | None],
    municipios: list[str],
) -> list[str]:
    """Performs the lightweight contract check needed by the targeted workflow."""

    problems: list[str] = []
    for cycle_key, indicator_keys in cycle_indicators.items():
        path = export_dir / cycle_key / "indicadores_por_municipio.json"
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            problems.append(f"Não foi possível ler {path.name}: {exc}")
            continue
        exported = payload.get("municipios", {})
        for municipio in municipios:
            results = exported.get(municipio, {}).get("results", {})
            for indicator_key in indicator_keys or ():
                if indicator_key not in results:
                    problems.append(
                        f"Indicador {indicator_key} ausente para {municipio} no ciclo {cycle_key}."
                    )
    return problems


def _select_municipios(
    *,
    available: list[str],
    requested: list[str] | None,
    limit: int | None,
    strict: bool,
) -> tuple[list[str], list[str]]:
    """Applies municipality filters and keeps legacy partial exports permissive."""

    municipios = available
    missing: list[str] = []
    if requested:
        requested_set = set(requested)
        municipios = [municipio for municipio in municipios if municipio in requested_set]
        missing = sorted(requested_set - set(municipios))
        if missing and strict:
            raise ValueError(f"Município inexistente: {', '.join(missing)}.")
    if limit is not None:
        municipios = municipios[: max(limit, 0)]
    return municipios, missing


def _check_connection(load_municipios: Any) -> int:
    from src.data import repository

    repository.load_environment()
    backend = repository.get_data_backend()
    env_path = BASE_DIR / ".env"

    print("\nDiagnóstico de conexão")
    print(f"  .env da raiz encontrado: {'sim' if env_path.exists() else 'não'}")
    print(f"  backend usado: {backend}")

    if backend == "supabase":
        print(f"  SUPABASE_URL configurado: {'sim' if os.getenv('SUPABASE_URL') else 'não'}")
        print(
            "  chave Supabase configurada: "
            f"{'sim' if (os.getenv('SUPABASE_SERVICE_KEY') or os.getenv('SUPABASE_KEY')) else 'não'}"
        )
    else:
        print(f"  DB_HOST: {os.getenv('DB_HOST') or '(não definido)'}")
        print(f"  DB_PORT: {os.getenv('DB_PORT') or '5432'}")
        print(f"  DB_BANCO: {os.getenv('DB_BANCO') or '(não definido)'}")
        print(f"  DB_USUARIO: {os.getenv('DB_USUARIO') or '(não definido)'}")
        print("  DB_SENHA: (oculta)")

    try:
        municipios = load_municipios()
    except Exception as exc:  # noqa: BLE001 - diagnostic command should explain.
        print("\nResultado: falha ao carregar municípios.")
        print(f"  erro: {exc}")
        return 1

    print("\nResultado: conexão OK.")
    print(f"  municípios encontrados: {len(municipios)}")
    if municipios:
        print(f"  primeiro município: {municipios[0]}")
    return 0


def main() -> int:
    global EXPORT_DIR

    args = _parse_args()
    profile = TimingProfile(args.profile)
    is_targeted_export = bool(args.cycle or args.indicator)
    is_partial_export = args.limit is not None or bool(args.municipio) or is_targeted_export
    if is_partial_export:
        EXPORT_DIR = BASE_DIR / "export" / "debug" / f"static_data_partial_{_safe_timestamp()}"
    print("Iniciando exportação estática do Dashboard PNE...")
    print(f"Projeto Python: {BASE_DIR}")
    print(f"Destino JSON: {EXPORT_DIR}")
    if is_partial_export:
        print(
            "Export parcial detectado (--limit/--municipio): "
            "arquivos serao gravados em export/debug e nao sobrescreverao a base final."
        )
    stale_error_file = EXPORT_DIR / "export_errors.json"
    if stale_error_file.exists():
        stale_error_file.unlink()

    from src import fundeb_export
    from src.data_loader import load_municipios
    from src.pne import calculations_2014, calculations_2026, common

    cycle_modules = {
        "pne_2014_2024": calculations_2014,
        "pne_2026_2036": calculations_2026,
    }
    try:
        selected_cycle_modules, selected_indicators = _select_cycles_and_indicators(
            requested_cycles=args.cycle,
            requested_indicators=args.indicator,
            cycle_modules=cycle_modules,
        )
    except ValueError as exc:
        print(f"Erro de seleção: {exc}")
        return 2

    if args.check_connection:
        return _check_connection(load_municipios)

    errors: list[dict[str, Any]] = []
    generated_at = _generated_at()
    try:
        with profile.measure("carregamento das fontes"):
            municipios = load_municipios()
    except Exception as exc:  # noqa: BLE001 - report a clean export failure.
        EXPORT_DIR.mkdir(parents=True, exist_ok=True)
        errors.append(
            {
                "stage": "load_municipios",
                "error": str(exc),
                "traceback": traceback.format_exc(limit=6),
            }
        )
        _write_json(
            EXPORT_DIR / "export_errors.json",
            {
                "generated_at": _generated_at(),
                "total_errors": len(errors),
                "errors": errors,
            },
            profile,
        )
        print("\nResumo da exportação")
        print("  municípios exportados: 0")
        print(f"  erros registrados: {len(errors)}")
        print(f"  falha ao carregar municípios; veja {EXPORT_DIR / 'export_errors.json'}")
        return 1

    try:
        municipios, missing = _select_municipios(
            available=municipios,
            requested=args.municipio,
            limit=args.limit,
            strict=is_targeted_export,
        )
    except ValueError as exc:
        print(exc)
        return 2

    if args.municipio:
        for municipio in missing:
            errors.append(
                {
                    "stage": "filter_municipio",
                    "municipio": municipio,
                    "error": "Município não encontrado na lista carregada.",
                }
            )

    if is_targeted_export and not municipios:
        print("Nenhum município selecionado para a exportação rápida.")
        return 2

    print(f"Municípios carregados para exportação: {len(municipios)}")
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    municipios_payload = {
        "generated_at": generated_at,
        "total_municipios": len(municipios),
        "municipios": municipios,
    }
    _write_json(EXPORT_DIR / "municipios.json", municipios_payload, profile)

    indicadores_payload = {
        "generated_at": generated_at,
        "cycles": {
            cycle_key: {
                "label": (
                    "PNE 2014-2024"
                    if cycle_key == "pne_2014_2024"
                    else "PNE 2026-2036"
                ),
                "categories": _serialize_categories(
                    cycle_module,
                    set(selected_indicators[cycle_key])
                    if is_targeted_export and selected_indicators[cycle_key] is not None
                    else None,
                ),
            }
            for cycle_key, cycle_module in selected_cycle_modules.items()
        },
    }
    _write_json(EXPORT_DIR / "indicadores.json", indicadores_payload, profile)

    results_cache = ResultsCache()
    generated_files = [
        EXPORT_DIR / "municipios.json",
        EXPORT_DIR / "indicadores.json",
    ]

    for cycle_key, cycle_module in selected_cycle_modules.items():
        with profile.measure(f"cálculo do ciclo {cycle_key}"):
            cycle_payload = _export_cycle_results(
                cycle_key=cycle_key,
                cycle_module=cycle_module,
                municipios=municipios,
                shared=common,
                errors=errors,
                results_cache=results_cache,
                indicator_keys=selected_indicators[cycle_key]
                if is_targeted_export
                else None,
            )
        output_path = EXPORT_DIR / cycle_key / "indicadores_por_municipio.json"
        _write_json(output_path, cycle_payload, profile)
        generated_files.append(output_path)

    if is_targeted_export:
        with profile.measure("validação"):
            validation_errors = _validate_targeted_export(
                export_dir=EXPORT_DIR,
                cycle_indicators=selected_indicators,
                municipios=municipios,
            )
        if validation_errors:
            print("Falha na validação da exportação rápida:")
            for error in validation_errors:
                print(f"  - {error}")
            profile.print_summary()
            return 1
        print("\nValidação rápida concluída sem alterar public/data.")
        profile.print_summary()
        return 0

    with profile.measure("detalhes complementares"):
        indicator_details_payload = _export_indicator_details(
            municipios=municipios,
            shared=common,
            errors=errors,
        )
    indicator_details_path = EXPORT_DIR / "indicator_details_por_municipio.json"
    _write_json(indicator_details_path, indicator_details_payload, profile)
    generated_files.append(indicator_details_path)

    state_reference_payloads: dict[str, dict[str, Any]] = {}
    for state_reference_cycle in ("pne_2014_2024", "pne_2026_2036"):
        with profile.measure(f"referência estadual {state_reference_cycle}"):
            state_reference_payload = _export_state_reference(
                state_reference_cycle,
                errors,
            )
        state_reference_path = (
            EXPORT_DIR / state_reference_cycle / "referencia_estadual.json"
        )
        _write_json(state_reference_path, state_reference_payload, profile)
        generated_files.append(state_reference_path)
        state_reference_payloads[state_reference_cycle] = state_reference_payload

    with profile.measure("projeções"):
        projections_payload = _export_projections(
            municipios=municipios,
            municipio_ids=None,
            errors=errors,
        )
    projections_path = EXPORT_DIR / "pne_2026_2036" / "projecoes_por_municipio.json"
    _write_json(projections_path, projections_payload, profile)
    generated_files.append(projections_path)

    with profile.measure("cenários de planejamento"):
        planning_scenarios_payload = _export_planning_scenarios(municipios=municipios)
    planning_scenarios_path = (
        EXPORT_DIR
        / "pne_2026_2036"
        / "cenarios_planejamento_por_municipio.json"
    )
    _write_json(planning_scenarios_path, planning_scenarios_payload, profile)
    generated_files.append(planning_scenarios_path)

    with profile.measure("atendimento e cenários"):
        education_attendance_payload = _export_education_attendance(
            municipios=municipios,
            projections_payload=projections_payload,
            planning_scenarios_payload=planning_scenarios_payload,
        )
    education_attendance_path = (
        EXPORT_DIR
        / "pne_2026_2036"
        / "atendimento_cenarios_por_municipio.json"
    )
    _write_json(education_attendance_path, education_attendance_payload, profile)
    generated_files.append(education_attendance_path)

    with profile.measure("FUNDEB"):
        fundeb_payload = _export_fundeb_data(
            municipios=municipios,
            errors=errors,
        )
    fundeb_path = EXPORT_DIR / "fundeb_por_municipio.json"
    _write_json(fundeb_path, fundeb_payload, profile)
    generated_files.append(fundeb_path)

    with profile.measure("PNATE"):
        pnate_payload = _export_pnate_data(
            municipios=municipios,
            errors=errors,
        )
    pnate_path = EXPORT_DIR / "pnate_por_municipio.json"
    _write_json(pnate_path, pnate_payload, profile)
    generated_files.append(pnate_path)

    if args.include_derived:
        for cycle_key, cycle_module in cycle_modules.items():
            with profile.measure(f"rankings {cycle_key}"):
                rankings_payload = _export_cycle_rankings(
                    cycle_key=cycle_key,
                    cycle_module=cycle_module,
                    municipios=municipios,
                    shared=common,
                    errors=errors,
                    results_cache=results_cache,
                )
            rankings_path = EXPORT_DIR / cycle_key / "rankings_por_municipio.json"
            _write_json(rankings_path, rankings_payload, profile)
            generated_files.append(rankings_path)

        with profile.measure("diagnóstico"):
            inequality_payload = _export_inequality_documents(
                municipios=municipios,
                generated_at=generated_at,
            )
        inequality_path = (
            EXPORT_DIR / "pne_2026_2036" / "desigualdade_por_municipio.json"
        )
        _write_json(inequality_path, inequality_payload, profile)
        generated_files.append(inequality_path)

    if errors:
        _write_json(
            EXPORT_DIR / "export_errors.json",
            {
                "generated_at": _generated_at(),
                "total_errors": len(errors),
                "errors": errors,
            },
            profile,
        )
        generated_files.append(EXPORT_DIR / "export_errors.json")

    print("\nResumo da exportação")
    print(f"  municípios exportados: {len(municipios)}")
    print(f"  erros registrados: {len(errors)}")
    print("  arquivos gerados:")
    for path in generated_files:
        print(f"    - {path}")

    profile.print_summary()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
