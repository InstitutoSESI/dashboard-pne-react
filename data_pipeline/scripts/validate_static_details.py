from __future__ import annotations

import argparse
import json
import math
import sys
import time
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_PIPELINE_DIR = REPO_ROOT / "data_pipeline"
if str(DATA_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_PIPELINE_DIR))

from src.config import PUBLIC_DATA_DIR  # noqa: E402
from src.municipality_registry import (  # noqa: E402
    MunicipalityRecord,
    MunicipalityRegistry,
    MunicipalityRegistryError,
    load_municipality_registry,
)
from src.state_config import (  # noqa: E402
    DEFAULT_STATE_CODE,
    StateConfigError,
    load_state_config,
)
from src.pipeline_profiling import (  # noqa: E402
    get_active_profile_session,
    profile_operation,
    profiled_main_from_environment,
)
from src.school_infrastructure_materialization import (  # noqa: E402
    PNE_INTERNET_DETAIL_KEY,
    reconcile_pne_internet_details,
)


DEFAULT_DETAILS_GLOB = "municipios/*/details.json"

ALLOWED_TOP_LEVEL_FIELDS = {
    "calculation",
    "dependency_calculation",
    "dependency_unit",
    "dependency_value_type",
    "series_components",
    "series_components_by_cycle",
    "series_dependencia",
    "series_dependencia_components",
    "series_total",
    "series_auxiliares",
    "source",
    "methodology_note",
    "reference",
    "warning",
    "acima_de_100_anos",
    "subtitle",
    "title",
    "unit",
    "_shared",
}

FORBIDDEN_FIELDS = {"series_by_dependencia"}
EXPECTED_DEPENDENCIES = {"federal", "estadual", "municipal", "privada"}
AGGREGATE_DEPENDENCIES = {"publica"}
DEPENDENCY_META_FIELDS = {"ano"}
NUMERATOR_FIELDS = {"numerador", "numerator"}
DENOMINATOR_FIELDS = {"denominador", "denominator"}

# Compatibility warning for the current historical aggregate-plus-breakdown pattern.
LEGACY_MIXED_DEPENDENCY_WARNING_KEYS = {"temporarios"}
MUNICIPAL_INEQUALITY_STATUSES = {
    "available",
    "suppressed_small_cell",
    "missing",
    "not_applicable",
    "methodology_incompatible",
}
MUNICIPAL_INEQUALITY_GROUPS = {"urban", "rural"}


@dataclass
class Problem:
    severity: str
    path: Path
    message: str


def _record_profile_read(path: Path, started_ns: int, *, failed: bool = False) -> None:
    session = get_active_profile_session()
    if session is None:
        return
    session.accumulate_event(
        category="read",
        name="validation.file_reads",
        duration_ns=time.perf_counter_ns() - started_ns,
        counters={
            "filesRead": int(not failed),
            "bytesRead": path.stat().st_size if path.is_file() else 0,
            "errors": int(failed),
        },
        metadata={"format": "json"},
    )


def _warning_categories(problems: list[Problem]) -> dict[str, int]:
    categories: dict[str, int] = {}
    for problem in problems:
        if problem.severity != "WARNING":
            continue
        message = problem.message.casefold()
        category = (
            "dependency"
            if "depend" in message
            else "series"
            if "series" in message
            else "contract"
        )
        categories[category] = categories.get(category, 0) + 1
    return categories


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate static complementary details JSON files."
    )
    parser.add_argument(
        "--data-dir",
        default=str(PUBLIC_DATA_DIR),
        help="Directory containing the public static data tree.",
    )
    parser.add_argument(
        "--max-problems",
        type=int,
        default=80,
        help="Maximum number of individual problems to print.",
    )
    parser.add_argument(
        "--state",
        default=DEFAULT_STATE_CODE,
        help=f"Configured state code (default: {DEFAULT_STATE_CODE}).",
    )
    return parser.parse_args()


def is_number(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return math.isfinite(float(value))
    return False


def has_real_number(value: Any) -> bool:
    return is_number(value) and float(value) > 0


def rel(path: Path) -> Path:
    try:
        return path.relative_to(REPO_ROOT)
    except ValueError:
        return path


def walk_fields(value: Any, prefix: str = "") -> Iterable[str]:
    if isinstance(value, dict):
        for key, child in value.items():
            key_path = f"{prefix}.{key}" if prefix else str(key)
            yield key_path
            yield from walk_fields(child, key_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from walk_fields(child, f"{prefix}[{index}]")


def add_problem(
    problems: list[Problem], severity: str, path: Path, message: str
) -> None:
    problems.append(Problem(severity=severity, path=path, message=message))


def validate_series_components(
    value: Any,
    *,
    path: Path,
    field_name: str,
    problems: list[Problem],
) -> None:
    if not isinstance(value, list):
        add_problem(problems, "ERROR", path, f"{field_name} must be a list.")
        return

    if not value:
        add_problem(problems, "WARNING", path, f"{field_name} is empty.")
        return

    valid_rows = 0
    for index, row in enumerate(value):
        if not isinstance(row, dict):
            add_problem(
                problems,
                "ERROR",
                path,
                f"{field_name}[{index}] must be an object.",
            )
            continue

        numerator = next((row.get(key) for key in NUMERATOR_FIELDS if key in row), None)
        denominator = next(
            (row.get(key) for key in DENOMINATOR_FIELDS if key in row), None
        )

        if not is_number(numerator) or not is_number(denominator):
            add_problem(
                problems,
                "ERROR",
                path,
                f"{field_name}[{index}] must contain numeric numerator and denominator.",
            )
            continue

        if float(denominator) <= 0:
            add_problem(
                problems,
                "ERROR",
                path,
                f"{field_name}[{index}] denominator must be greater than zero.",
            )
            continue

        valid_rows += 1

    if valid_rows == 0:
        add_problem(problems, "ERROR", path, f"{field_name} has no valid rows.")


def validate_components_by_cycle(
    value: Any, *, path: Path, problems: list[Problem]
) -> None:
    if not isinstance(value, dict):
        add_problem(problems, "ERROR", path, "series_components_by_cycle must be an object.")
        return

    if not value:
        add_problem(problems, "WARNING", path, "series_components_by_cycle is empty.")
        return

    for cycle, rows in value.items():
        validate_series_components(
            rows,
            path=path,
            field_name=f"series_components_by_cycle.{cycle}",
            problems=problems,
        )


def validate_series_dependencia(
    value: Any,
    *,
    path: Path,
    problems: list[Problem],
    detail_key: str,
    detail_payload: Mapping[str, Any],
) -> None:
    if not isinstance(value, list):
        add_problem(problems, "ERROR", path, "series_dependencia must be a list.")
        return

    if not value:
        add_problem(problems, "ERROR", path, "series_dependencia is empty.")
        return

    has_valid_point = False
    has_positive_value = False
    mixes_publica_with_breakdown = False

    for index, point in enumerate(value):
        if not isinstance(point, dict):
            add_problem(
                problems,
                "ERROR",
                path,
                f"series_dependencia[{index}] must be an object.",
            )
            continue

        dependency_keys = set(point) - DEPENDENCY_META_FIELDS
        expected_keys = dependency_keys & EXPECTED_DEPENDENCIES
        aggregate_keys = dependency_keys & AGGREGATE_DEPENDENCIES
        unknown_keys = dependency_keys - EXPECTED_DEPENDENCIES - AGGREGATE_DEPENDENCIES

        uses_reconciled_internet_policy = (
            detail_key == PNE_INTERNET_DETAIL_KEY
            and bool(expected_keys)
            and bool(aggregate_keys)
        )
        if unknown_keys and not uses_reconciled_internet_policy:
            add_problem(
                problems,
                "ERROR",
                path,
                f"series_dependencia[{index}] has unexpected dependencies: "
                f"{', '.join(sorted(unknown_keys))}.",
            )

        if expected_keys and aggregate_keys:
            mixes_publica_with_breakdown = True

        numeric_values = [
            point.get(key)
            for key in sorted(expected_keys | aggregate_keys)
            if is_number(point.get(key))
        ]
        if numeric_values:
            has_valid_point = True
        if any(has_real_number(value) for value in numeric_values):
            has_positive_value = True

    if not has_valid_point:
        add_problem(
            problems,
            "ERROR",
            path,
            "series_dependencia has no point with numeric dependency values.",
        )
    elif not has_positive_value:
        add_problem(
            problems,
            "WARNING",
            path,
            "series_dependencia exists, but all dependency values are zero or null.",
        )

    if mixes_publica_with_breakdown:
        if detail_key in LEGACY_MIXED_DEPENDENCY_WARNING_KEYS:
            add_problem(
                problems,
                "WARNING",
                path,
                "series_dependencia mixes 'publica' with federal/estadual/"
                "municipal/privada under an explicitly allowed current pattern.",
            )
        elif detail_key == PNE_INTERNET_DETAIL_KEY:
            for message in reconcile_pne_internet_details(detail_payload):
                add_problem(problems, "ERROR", path, message)
        else:
            add_problem(
                problems,
                "ERROR",
                path,
                "series_dependencia mixes 'publica' with federal/estadual/"
                "municipal/privada.",
            )


def validate_detail_payload(
    payload: Any,
    *,
    path: Path,
    problems: list[Problem],
    detail_key: str,
) -> bool:
    if not isinstance(payload, dict):
        add_problem(problems, "ERROR", path, f"{detail_key} payload must be an object.")
        return True

    for field_path in walk_fields(payload):
        field_name = field_path.rsplit(".", 1)[-1]
        field_name = field_name.split("[", 1)[0]
        if field_name in FORBIDDEN_FIELDS:
            add_problem(
                problems,
                "ERROR",
                path,
                f"{detail_key}: forbidden field found: {field_path}.",
            )

    unknown_fields = sorted(set(payload) - ALLOWED_TOP_LEVEL_FIELDS)
    if unknown_fields:
        add_problem(
            problems,
            "WARNING",
            path,
            f"{detail_key}: unknown top-level fields: {', '.join(unknown_fields)}.",
        )

    if "series_dependencia" in payload:
        validate_series_dependencia(
            payload["series_dependencia"],
            path=path,
            problems=problems,
            detail_key=detail_key,
            detail_payload=payload,
        )

    if "series_components" in payload:
        validate_series_components(
            payload["series_components"],
            path=path,
            field_name="series_components",
            problems=problems,
        )

    if "series_components_by_cycle" in payload:
        validate_components_by_cycle(
            payload["series_components_by_cycle"], path=path, problems=problems
        )

    if "series_dependencia_components" in payload:
        validate_series_components(
            payload["series_dependencia_components"],
            path=path,
            field_name="series_dependencia_components",
            problems=problems,
        )

    return True


def validate_shared_privadas_conveniadas(
    payload: Any, *, path: Path, problems: list[Problem]
) -> None:
    if not isinstance(payload, dict):
        add_problem(problems, "ERROR", path, "_shared.privadas_conveniadas must be an object.")
        return

    expected_keys = {
        "ultimo_ano", "resumo", "por_secao", "por_categoria", "fonte", "disponivel_desde"
    }
    missing = expected_keys - set(payload)
    if missing:
        add_problem(
            problems, "ERROR", path,
            f"_shared.privadas_conveniadas missing keys: {', '.join(sorted(missing))}."
        )

    ultimo_ano = payload.get("ultimo_ano")
    if not isinstance(ultimo_ano, int) or ultimo_ano != 2025:
        add_problem(
            problems, "ERROR", path,
            f"_shared.privadas_conveniadas.ultimo_ano should be 2025, got {ultimo_ano}."
        )

    disponivel_desde = payload.get("disponivel_desde")
    if not isinstance(disponivel_desde, int) or disponivel_desde != 2025:
        add_problem(
            problems, "ERROR", path,
            f"_shared.privadas_conveniadas.disponivel_desde should be 2025, got {disponivel_desde}."
        )

    resumo = payload.get("resumo")
    if not isinstance(resumo, dict):
        add_problem(
            problems, "ERROR", path,
            "_shared.privadas_conveniadas.resumo must be an object."
        )
    elif resumo:
        for key in ("total_conveniado", "municipio", "estado_municipio", "municipal_total"):
            val = resumo.get(key)
            if val is not None and not is_number(val):
                add_problem(
                    problems, "ERROR", path,
                    f"_shared.privadas_conveniadas.resumo.{key} must be number or null."
                )

    por_secao = payload.get("por_secao")
    if not isinstance(por_secao, list):
        add_problem(
            problems, "ERROR", path,
            "_shared.privadas_conveniadas.por_secao must be a list."
        )
    else:
        _validate_por_list(
            por_secao, "por_secao", {"secao": str},
            ["total_conveniado", "municipio", "estado_municipio", "municipal_total"],
            path, problems,
        )

    por_categoria = payload.get("por_categoria")
    if not isinstance(por_categoria, list):
        add_problem(
            problems, "ERROR", path,
            "_shared.privadas_conveniadas.por_categoria must be a list."
        )
    else:
        _validate_por_list(
            por_categoria, "por_categoria", {"categoria": str},
            ["total_conveniado", "municipal_total"],
            path, problems,
        )


def _validate_por_list(
    items: list, field: str, str_fields: dict,
    numeric_fields: list[str], path: Path, problems: list[Problem],
) -> None:
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            add_problem(
                problems, "ERROR", path,
                f"_shared.privadas_conveniadas.{field}[{idx}] must be an object."
            )
            continue
        for key, expected_type in str_fields.items():
            val = item.get(key)
            if not isinstance(val, expected_type):
                add_problem(
                    problems, "ERROR", path,
                    f"_shared.privadas_conveniadas.{field}[{idx}].{key} "
                    f"must be a {expected_type.__name__}."
                )
        for key in numeric_fields:
            val = item.get(key)
            if val is not None and not is_number(val):
                add_problem(
                    problems, "ERROR", path,
                    f"_shared.privadas_conveniadas.{field}[{idx}].{key} "
                    f"must be number or null."
                )


def validate_shared_municipal_inequality(
    payload: Any,
    *,
    municipality_id: str,
    municipality_name: str | None = None,
    path: Path,
    problems: list[Problem],
) -> None:
    field = "_shared.municipal_inequality"
    if not isinstance(payload, dict):
        add_problem(problems, "ERROR", path, f"{field} must be an object.")
        return

    expected_document_keys = {
        "schemaVersion", "generatedAt", "municipality", "inequalityPilot"
    }
    if set(payload) != expected_document_keys:
        add_problem(
            problems,
            "ERROR",
            path,
            f"{field} must contain exactly the municipal-inequality-v1 fields.",
        )
    if payload.get("schemaVersion") != "municipal-inequality-v1":
        add_problem(problems, "ERROR", path, f"{field}.schemaVersion is invalid.")
    if not isinstance(payload.get("generatedAt"), str) or not payload["generatedAt"].strip():
        add_problem(problems, "ERROR", path, f"{field}.generatedAt must be filled.")

    municipality = payload.get("municipality")
    if not isinstance(municipality, dict):
        add_problem(problems, "ERROR", path, f"{field}.municipality must be an object.")
    else:
        if str(municipality.get("id") or "") != municipality_id:
            add_problem(
                problems,
                "ERROR",
                path,
                f"{field}.municipality.id must match directory {municipality_id}.",
            )
        if not isinstance(municipality.get("name"), str) or not municipality["name"].strip():
            add_problem(problems, "ERROR", path, f"{field}.municipality.name must be filled.")
        elif municipality_name is not None and municipality["name"] != municipality_name:
            add_problem(
                problems,
                "ERROR",
                path,
                f"{field}.municipality.name must equal registry name {municipality_name!r}.",
            )

    pilot = payload.get("inequalityPilot")
    if not isinstance(pilot, dict):
        add_problem(problems, "ERROR", path, f"{field}.inequalityPilot must be an object.")
        return

    expected_identity = {
        "methodologyVersion": "municipal-inequality-p4b-v1",
        "indicatorId": "basico_integral",
        "dimension": "urban_rural",
        "universeCode": "public_basic_education_enrollments",
        "formulaCode": "integral_enrollments_over_eligible_enrollments",
        "minimumCellSize": 10,
    }
    for key, expected in expected_identity.items():
        if pilot.get(key) != expected:
            add_problem(
                problems,
                "ERROR",
                path,
                f"{field}.inequalityPilot.{key} must be {expected!r}.",
            )

    pilot_status = pilot.get("status")
    if pilot_status not in MUNICIPAL_INEQUALITY_STATUSES:
        add_problem(problems, "ERROR", path, f"{field}.inequalityPilot.status is invalid.")
    pilot_year = pilot.get("year")
    if pilot_year is not None and (
        isinstance(pilot_year, bool) or not isinstance(pilot_year, int)
    ):
        add_problem(problems, "ERROR", path, f"{field}.inequalityPilot.year is invalid.")
    difference = pilot.get("observedDifferencePercentagePoints")
    if difference is not None and not is_number(difference):
        add_problem(
            problems,
            "ERROR",
            path,
            f"{field}.inequalityPilot.observedDifferencePercentagePoints is invalid.",
        )

    groups = pilot.get("groups")
    if not isinstance(groups, list):
        add_problem(problems, "ERROR", path, f"{field}.inequalityPilot.groups must be a list.")
        return
    group_codes = [
        group.get("groupCode") for group in groups if isinstance(group, dict)
    ]
    if len(groups) != 2 or set(group_codes) != MUNICIPAL_INEQUALITY_GROUPS:
        add_problem(
            problems,
            "ERROR",
            path,
            f"{field}.inequalityPilot.groups must contain urban and rural exactly once.",
        )

    group_statuses: set[str] = set()
    available_groups: dict[str, dict[str, Any]] = {}
    for index, group in enumerate(groups):
        group_field = f"{field}.inequalityPilot.groups[{index}]"
        if not isinstance(group, dict):
            add_problem(problems, "ERROR", path, f"{group_field} must be an object.")
            continue
        status = group.get("status")
        if status not in MUNICIPAL_INEQUALITY_STATUSES:
            add_problem(problems, "ERROR", path, f"{group_field}.status is invalid.")
            continue
        group_statuses.add(status)
        if group.get("publicationStatus") != status:
            add_problem(
                problems,
                "ERROR",
                path,
                f"{group_field}.publicationStatus must equal status.",
            )
        group_year = group.get("year")
        if group_year is not None and (
            isinstance(group_year, bool) or not isinstance(group_year, int)
        ):
            add_problem(problems, "ERROR", path, f"{group_field}.year is invalid.")
        if pilot_year is not None and group_year is not None and group_year != pilot_year:
            add_problem(problems, "ERROR", path, f"{group_field}.year conflicts with pilot year.")
        if group.get("coverage") not in {"municipality_public_network", "missing"}:
            add_problem(problems, "ERROR", path, f"{group_field}.coverage is invalid.")
        if group.get("suppressionReasonCode") not in {
            None, "small_cell", "complementary_suppression"
        }:
            add_problem(
                problems, "ERROR", path, f"{group_field}.suppressionReasonCode is invalid."
            )

        numerator = group.get("numerator")
        denominator = group.get("denominator")
        percentage = group.get("percentage")
        if status == "available":
            if not all(is_number(value) for value in (numerator, denominator, percentage)):
                add_problem(
                    problems, "ERROR", path, f"{group_field} available values must be numeric."
                )
            elif float(denominator) <= 0 or not 0 <= float(numerator) <= float(denominator):
                add_problem(problems, "ERROR", path, f"{group_field} has invalid components.")
            else:
                available_groups[str(group.get("groupCode"))] = group
        elif status == "not_applicable":
            if numerator != 0 or denominator != 0 or percentage is not None:
                add_problem(
                    problems,
                    "ERROR",
                    path,
                    f"{group_field} not_applicable values must be 0, 0 and null.",
                )
        elif any(value is not None for value in (numerator, denominator, percentage)):
            add_problem(
                problems, "ERROR", path, f"{group_field} unavailable values must remain null."
            )

    if "methodology_incompatible" in group_statuses:
        expected_status = "methodology_incompatible"
    elif "suppressed_small_cell" in group_statuses:
        expected_status = "suppressed_small_cell"
    elif "available" in group_statuses:
        expected_status = "available"
    elif group_statuses == {"not_applicable"}:
        expected_status = "not_applicable"
    else:
        expected_status = "missing"
    if pilot_status in MUNICIPAL_INEQUALITY_STATUSES and pilot_status != expected_status:
        add_problem(problems, "ERROR", path, f"{field}.inequalityPilot.status conflicts with groups.")

    if set(available_groups) == MUNICIPAL_INEQUALITY_GROUPS:
        expected_difference = round(
            float(available_groups["urban"]["percentage"])
            - float(available_groups["rural"]["percentage"]),
            6,
        )
        if not is_number(difference) or not math.isclose(
            float(difference), expected_difference, abs_tol=1e-9
        ):
            add_problem(
                problems,
                "ERROR",
                path,
                f"{field}.inequalityPilot observed difference conflicts with groups.",
            )
    elif difference is not None:
        add_problem(
            problems,
            "ERROR",
            path,
            f"{field}.inequalityPilot observed difference must be null when groups are unavailable.",
        )


def validate_detail_file(
    path: Path,
    problems: list[Problem],
    *,
    municipality_name: str | None = None,
) -> int:
    session = get_active_profile_session()
    started_ns = time.perf_counter_ns() if session is not None else 0
    try:
        with path.open("r", encoding="utf-8") as file:
            payload = json.load(file)
    except json.JSONDecodeError as exc:
        _record_profile_read(path, started_ns, failed=True)
        add_problem(problems, "ERROR", path, f"invalid JSON: {exc}")
        return 0
    except OSError as exc:
        _record_profile_read(path, started_ns, failed=True)
        add_problem(problems, "ERROR", path, f"could not read file: {exc}")
        return 0
    _record_profile_read(path, started_ns)

    if not isinstance(payload, dict):
        add_problem(problems, "ERROR", path, "top-level payload must be an object.")
        return 0

    if "municipal_inequality" in payload:
        add_problem(
            problems,
            "ERROR",
            path,
            "municipal_inequality conflicts with shared content outside _shared.",
        )
    shared = payload.get("_shared")
    if not isinstance(shared, dict):
        add_problem(problems, "ERROR", path, "top-level _shared must be an object.")
    else:
        privadas = shared.get("privadas_conveniadas")
        if privadas is not None:
            validate_shared_privadas_conveniadas(
                privadas, path=path, problems=problems
            )
        validate_shared_municipal_inequality(
            shared.get("municipal_inequality"),
            municipality_id=path.parent.name,
            municipality_name=municipality_name,
            path=path,
            problems=problems,
        )

    total_details = 0
    for indicator_key, detail_payload in payload.items():
        if indicator_key == "_shared":
            continue
        total_details += 1
        validate_detail_payload(
            detail_payload,
            path=path,
            problems=problems,
            detail_key=str(indicator_key),
        )

    return total_details


def print_summary(total_files: int, problems: list[Problem], max_problems: int) -> None:
    errors = [problem for problem in problems if problem.severity == "ERROR"]
    warnings = [problem for problem in problems if problem.severity == "WARNING"]

    print("Static details validation")
    print(f"  files analyzed: {total_files}")
    print(f"  errors: {len(errors)}")
    print(f"  warnings: {len(warnings)}")

    if problems:
        print("\nProblems:")
        for problem in problems[:max_problems]:
            print(f"  [{problem.severity}] {rel(problem.path)}: {problem.message}")
        if len(problems) > max_problems:
            print(f"  ... {len(problems) - max_problems} more problem(s) omitted.")


def _validate_shared_coverage(
    detail_files: list[Path],
    data_dir: Path,
    problems: list[Problem],
    registry: MunicipalityRegistry,
) -> None:
    seen_ids: set[str] = set()
    ids_with_privadas: set[str] = set()
    ids_with_inequality: set[str] = set()

    for path in detail_files:
        parent_name = path.parent.name
        seen_ids.add(parent_name)

        session = get_active_profile_session()
        started_ns = time.perf_counter_ns() if session is not None else 0
        try:
            with path.open("r", encoding="utf-8") as f:
                payload = json.load(f)
        except (json.JSONDecodeError, OSError):
            _record_profile_read(path, started_ns, failed=True)
            continue
        _record_profile_read(path, started_ns)

        shared = payload.get("_shared") if isinstance(payload, dict) else None
        if isinstance(shared, dict):
            if shared.get("privadas_conveniadas") is not None:
                ids_with_privadas.add(parent_name)
            if shared.get("municipal_inequality") is not None:
                ids_with_inequality.add(parent_name)

    if seen_ids != registry.ids:
        missing = sorted(registry.ids - seen_ids)
        extra = sorted(seen_ids - registry.ids)
        add_problem(
            problems, "ERROR", data_dir,
            "Municipal details set diverges from registry; "
            f"missing={missing[:5]}, extra={extra[:5]}."
        )

    ids_without_privadas = registry.ids - ids_with_privadas
    if ids_without_privadas:
        exemplos = sorted(ids_without_privadas)[:5]
        add_problem(
            problems, "ERROR", data_dir,
            f"{len(ids_without_privadas)} municipio(s) sem "
            f"_shared.privadas_conveniadas: {', '.join(exemplos)}"
            + ("..." if len(ids_without_privadas) > 5 else "")
        )

    if ids_with_privadas != registry.ids:
        add_problem(
            problems, "ERROR", data_dir,
            f"Expected {registry.municipality_count} municipios with "
            f"_shared.privadas_conveniadas, found {len(ids_with_privadas)}."
        )

    ids_without_inequality = registry.ids - ids_with_inequality
    if ids_without_inequality:
        exemplos = sorted(ids_without_inequality)[:5]
        add_problem(
            problems, "ERROR", data_dir,
            f"{len(ids_without_inequality)} municipio(s) sem "
            f"_shared.municipal_inequality: {', '.join(exemplos)}"
            + ("..." if len(ids_without_inequality) > 5 else "")
        )

    if ids_with_inequality != registry.ids:
        add_problem(
            problems, "ERROR", data_dir,
            f"Expected {registry.municipality_count} municipios with "
            f"_shared.municipal_inequality, found {len(ids_with_inequality)}."
        )


def validate_municipal_index_identity(
    data_dir: Path,
    record: MunicipalityRecord,
    problems: list[Problem],
) -> None:
    path = data_dir / "municipios" / record.ibge_code / "index.json"
    session = get_active_profile_session()
    started_ns = time.perf_counter_ns() if session is not None else 0
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        _record_profile_read(path, started_ns, failed=True)
        add_problem(problems, "ERROR", path, "municipal index.json is missing.")
        return
    except (json.JSONDecodeError, OSError) as exc:
        _record_profile_read(path, started_ns, failed=True)
        add_problem(problems, "ERROR", path, f"could not read municipal index: {exc}")
        return
    _record_profile_read(path, started_ns)
    if not isinstance(payload, dict):
        add_problem(problems, "ERROR", path, "municipal index must be an object.")
        return
    expected = {
        "id_municipio": record.ibge_code,
        "municipio": record.name,
        "slug": record.slug,
    }
    observed = {field: payload.get(field) for field in expected}
    if observed != expected:
        add_problem(
            problems,
            "ERROR",
            path,
            f"municipal identity diverges from registry: {observed!r}.",
        )


@profiled_main_from_environment("validate")
def main() -> int:
    args = parse_args()
    try:
        with profile_operation(
            "validation",
            "validation.configuration",
            metadata={"state": args.state},
        ) as configuration_event:
            state_config = load_state_config(args.state)
            registry = load_municipality_registry(state_config)
            configuration_event.add_counter(
                "municipalities", registry.municipality_count
            )
    except (FileNotFoundError, StateConfigError, MunicipalityRegistryError) as exc:
        print(f"State configuration validation failed: {exc}", file=sys.stderr)
        return 2
    data_dir = Path(args.data_dir).resolve()
    problems: list[Problem] = []
    municipal_root = data_dir / "municipios"
    with profile_operation(
        "validation",
        "validation.municipal_identity",
    ) as identity_event:
        physical_directories = (
            {path.name for path in municipal_root.iterdir() if path.is_dir()}
            if municipal_root.is_dir()
            else set()
        )
        if physical_directories != registry.ids:
            missing = sorted(registry.ids - physical_directories)
            extra = sorted(physical_directories - registry.ids)
            add_problem(
                problems,
                "ERROR",
                municipal_root,
                "municipal directory set diverges from registry; "
                f"missing={missing[:5]}, extra={extra[:5]}.",
            )

        detail_files: list[Path] = []
        for record in registry.ordered_records:
            validate_municipal_index_identity(data_dir, record, problems)
            details_path = municipal_root / record.ibge_code / "details.json"
            if details_path.is_file():
                detail_files.append(details_path)
            else:
                add_problem(problems, "ERROR", details_path, "details.json is missing.")
        identity_event.add_counter("directories", len(physical_directories))
        identity_event.add_counter("detailFiles", len(detail_files))

    if not detail_files:
        add_problem(
            problems,
            "ERROR",
            data_dir,
            f"no details JSON files found with glob {DEFAULT_DETAILS_GLOB!r}.",
        )
        print_summary(0, problems, args.max_problems)
        with profile_operation(
            "validation",
            "validation.result",
            counters={
                "filesRead": 0,
                "payloadsVerified": 0,
                "errors": sum(problem.severity == "ERROR" for problem in problems),
                "warnings": sum(problem.severity == "WARNING" for problem in problems),
            },
            metadata={"warningCategories": _warning_categories(problems)},
        ):
            pass
        return 1

    total_files = 0
    with profile_operation(
        "validation",
        "validation.detail_contracts",
        metadata={"eventGranularity": "aggregate"},
    ) as details_event:
        for path in detail_files:
            record = registry.get_by_id(path.parent.name)
            total_files += validate_detail_file(
                path,
                problems,
                municipality_name=record.name,
            )
        details_event.add_counter("files", len(detail_files))
        details_event.add_counter("payloadsVerified", total_files)

    with profile_operation(
        "validation",
        "validation.shared_coverage",
    ):
        _validate_shared_coverage(detail_files, data_dir, problems, registry)

    print_summary(total_files, problems, args.max_problems)
    errors = sum(problem.severity == "ERROR" for problem in problems)
    warnings = sum(problem.severity == "WARNING" for problem in problems)
    with profile_operation(
        "validation",
        "validation.result",
        counters={
            "files": len(detail_files),
            "payloadsVerified": total_files,
            "errors": errors,
            "warnings": warnings,
        },
        metadata={"warningCategories": _warning_categories(problems)},
    ):
        pass
    return 1 if any(problem.severity == "ERROR" for problem in problems) else 0


if __name__ == "__main__":
    raise SystemExit(main())
