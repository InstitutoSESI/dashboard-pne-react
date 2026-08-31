"""Materializacao interna do Job 5G-D de Vocações da Região × PNE V7.

O módulo não publica, não toca o frontend e não acessa rede. Ele consome
snapshots oficiais e outputs congelados, produzindo um pacote determinístico
para julgamento externo.
"""

from __future__ import annotations

from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
import pandas as pd

from src.vocacoes_pne_job2 import (
    artifact_record,
    canonical_json_bytes,
    directory_content_digest,
    municipal_distribution,
    safe_ratio,
    sha256_file,
    write_csv_gzip,
    write_json,
)


NSR_CODE = "4313375"
REGION_ENTITY_ID = "REGION_VALE_DO_SINOS"
STATE_ENTITY_ID = "STATE_RS"
FINAL_STATE = "JOB_5GD_READY_WITH_EXPLICIT_LIMITS_FOR_EXTERNAL_JUDGMENT"
IBGE_CODE_PATTERN = re.compile(r"\d{7}")

ORIGINAL_FACT_COLUMNS = [
    "fact_id",
    "universe",
    "measure",
    "direction",
    "dimension_code",
    "dimension_label",
    "initial_value",
    "final_value",
    "absolute_change",
    "relative_change_percent",
    "regional_initial_value",
    "regional_final_value",
    "regional_concentration_share_final",
    "small_volume_sensitive",
    "negative_adjustment_present",
    "label_available",
    "selection_eligible",
    "selection_metric",
    "selection_metric_name",
    "selected_for_synthesis",
    "selection_rank",
    "selection_rule_version",
    "selection_rule",
    "physical_order_used",
    "code_order_used",
    "alphabetical_order_used",
    "exact_tie_content_digest_only",
]

NUMERIC_COMPATIBILITY_COLUMNS = {
    "initial_value",
    "final_value",
    "absolute_change",
    "relative_change_percent",
    "regional_initial_value",
    "regional_final_value",
    "regional_concentration_share_final",
    "selection_metric",
    "selection_rank",
}
BOOLEAN_COMPATIBILITY_COLUMNS = {
    "small_volume_sensitive",
    "negative_adjustment_present",
    "label_available",
    "selection_eligible",
    "selected_for_synthesis",
    "physical_order_used",
    "code_order_used",
    "alphabetical_order_used",
    "exact_tie_content_digest_only",
}

CRITERIA = (
    ("C1", "relevancia PNE/PME"),
    ("C2", "mecanismo anterior ao resultado"),
    ("C3", "universos e lentes compativeis"),
    ("C4", "periodo coerente"),
    ("C5", "estabilidade suficiente"),
    ("C6", "integracao dos fatos"),
    ("C7", "diferenca municipal util"),
    ("C8", "municipio, etapa, publico, indicador e questao"),
    ("C9", "comunicabilidade"),
    ("C10", "rastreabilidade"),
    ("C11", "nao redundancia"),
    ("C12", "valor alem da demografia"),
)


def _json_safe(value: Any) -> Any:
    if value is None or value is pd.NA:
        return None
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        if math.isnan(float(value)) or math.isinf(float(value)):
            return None
        return float(value)
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(value, "item"):
        try:
            return _json_safe(value.item())
        except (TypeError, ValueError):
            pass
    return value


def _records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    return [
        {key: _json_safe(value) for key, value in row.items()}
        for row in frame.to_dict("records")
    ]


def _as_bool(value: Any) -> bool:
    if value is None or value is pd.NA:
        return False
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "sim"}
    try:
        if pd.isna(value):
            return False
    except (TypeError, ValueError):
        pass
    return bool(value)


def _read_csv(path: Path) -> pd.DataFrame:
    identity_columns = (
        "municipality_ibge_code",
        "municipality_id",
        "entity_id",
        "dimension_code",
        "cnae_division_code",
        "cnae_subclass_code",
        "occupation_code",
        "fact_id",
    )
    frame = pd.read_csv(
        path,
        low_memory=False,
        dtype={column: "string" for column in identity_columns},
    )
    return frame


def _stable(frame: pd.DataFrame, columns: Sequence[str]) -> pd.DataFrame:
    usable = [column for column in columns if column in frame]
    if not usable:
        return frame.reset_index(drop=True)
    return frame.sort_values(usable, kind="mergesort", na_position="last").reset_index(
        drop=True
    )


def _sign_direction(value: Any) -> str:
    if value is None or pd.isna(value):
        return "not_available"
    number = float(value)
    if number > 0:
        return "positive"
    if number < 0:
        return "negative"
    return "zero"


def _legacy_direction(value: Any) -> str:
    direction = _sign_direction(value)
    return {"positive": "gain", "negative": "loss", "zero": "no_change"}.get(
        direction, "not_available"
    )


def _relative_change(initial: Any, final: Any) -> float | None:
    if initial is None or final is None or pd.isna(initial) or pd.isna(final):
        return None
    initial_number = float(initial)
    if initial_number == 0:
        return None
    return (float(final) - initial_number) / initial_number * 100.0


def _canonical_row_payload(row: Mapping[str, Any], fields: Iterable[str]) -> str:
    return json.dumps(
        {field: _json_safe(row.get(field)) for field in fields},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _compatibility_value(column: str, value: Any) -> Any:
    if value is None or value is pd.NA:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if column in NUMERIC_COMPATIBILITY_COLUMNS:
        return float(value)
    if column in BOOLEAN_COMPATIBILITY_COLUMNS:
        return _as_bool(value)
    return str(value)


def _compatibility_counter(frame: pd.DataFrame) -> Counter[str]:
    counter: Counter[str] = Counter()
    for row in frame[ORIGINAL_FACT_COLUMNS].to_dict("records"):
        payload = {
            column: _compatibility_value(column, row.get(column))
            for column in ORIGINAL_FACT_COLUMNS
        }
        counter[
            json.dumps(
                payload,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
        ] += 1
    return counter


def _counter_digest(counter: Counter[str]) -> str:
    serialized = json.dumps(
        sorted(counter.items()),
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


def _origin_key(row: Mapping[str, Any], fields: Sequence[str]) -> tuple[str, str]:
    payload = _canonical_row_payload(row, fields)
    return payload, hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_corrected_gcr_fact_catalog(
    *,
    gcr_root: Path,
    source_v1: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Reconstrói o catálogo v2 diretamente dos painéis congelados de origem."""

    source_specs = [
        (
            "RAIS_OCCUPATION_STOCK_ALL_AGES",
            "PAINEL_OCUPACOES_RAIS_ESTOQUE_V1.csv.gz",
            False,
        ),
        (
            "RAIS_SECTOR_STOCK_ALL_AGES",
            "PAINEL_SETORES_RAIS_ESTOQUE_V1.csv.gz",
            False,
        ),
        (
            "CAGED_OCCUPATION_YOUTH_FLOW",
            "PAINEL_OCUPACOES_CAGED_FLUXOS_V1.csv.gz",
            True,
        ),
        (
            "CAGED_SECTOR_YOUTH_FLOW",
            "PAINEL_SETORES_CAGED_FLUXOS_V1.csv.gz",
            True,
        ),
    ]
    rows: list[dict[str, Any]] = []

    for universe, filename, is_caged in source_specs:
        frame = _read_csv(gcr_root / filename)
        local = frame[frame["entity_id"].eq(NSR_CODE)].copy()
        grain_fields = [
            "entity_scope",
            "entity_id",
            *( ["age_group"] if is_caged else [] ),
            "measure",
            "dimension_code",
            "initial_year",
            "final_year",
        ]
        if local.duplicated(grain_fields).any():
            raise ValueError(f"Grão de origem duplicado em {filename}: {grain_fields}")
        for source_row in local.to_dict("records"):
            age_group = str(source_row["age_group"]) if is_caged else "all_ages"
            compatibility_fact_id = (
                f"{universe}|{source_row.get('measure')}|{source_row['dimension_code']}"
            )
            canonical_fact_id = "|".join(
                [
                    universe,
                    str(source_row["entity_scope"]),
                    str(source_row["entity_id"]),
                    age_group,
                    str(source_row.get("measure")),
                    str(source_row["dimension_code"]),
                    str(int(source_row["initial_year"])),
                    str(int(source_row["final_year"])),
                ]
            )
            origin_payload, origin_digest = _origin_key(source_row, grain_fields)
            absolute_change = source_row["absolute_change"]
            selection_eligible = _as_bool(source_row.get("selection_eligible"))
            small_volume = _as_bool(source_row.get("small_volume_sensitive"))
            negative_adjustment = _as_bool(
                source_row.get("negative_adjustment_present")
            )
            rows.append(
                {
                    "fact_id": canonical_fact_id,
                    "compatibility_fact_id_v1": compatibility_fact_id,
                    "fact_id_version": "job5gcr-grain-v2",
                    "universe": universe,
                    "measure": source_row.get("measure"),
                    "direction": _legacy_direction(absolute_change),
                    "numeric_direction": _sign_direction(absolute_change),
                    "observed_change_direction": _sign_direction(absolute_change),
                    "local_differential_direction": "not_applicable",
                    "direction_semantics": (
                        "sign_of_observed_measure_only_never_improvement_or_worsening"
                    ),
                    "dimension_code": source_row["dimension_code"],
                    "dimension_label": source_row.get("dimension_label"),
                    "age_group": age_group,
                    "initial_year": int(source_row["initial_year"]),
                    "final_year": int(source_row["final_year"]),
                    "initial_value": source_row["initial_value"],
                    "final_value": source_row["final_value"],
                    "absolute_change": absolute_change,
                    "relative_change_percent": source_row.get("percent_change"),
                    "regional_initial_value": source_row.get("regional_initial_value"),
                    "regional_final_value": source_row.get("regional_final_value"),
                    "regional_concentration_share_final": source_row.get(
                        "final_regional_share"
                    ),
                    "small_volume_sensitive": small_volume,
                    "negative_adjustment_present": negative_adjustment,
                    "label_available": _as_bool(source_row.get("label_available")),
                    "selection_eligible": selection_eligible,
                    "selection_metric": absolute_change,
                    "selection_metric_name": "absolute_change",
                    "source": source_row.get("source"),
                    "territorial_lens": source_row.get("territorial_lens"),
                    "stock_or_flow": source_row.get("stock_or_flow"),
                    "population_scope": source_row.get("population_scope"),
                    "entity_scope": source_row.get("entity_scope"),
                    "entity_id": source_row.get("entity_id"),
                    "origin_artifact": filename,
                    "origin_grain_fields": json.dumps(
                        grain_fields, ensure_ascii=False, separators=(",", ":")
                    ),
                    "origin_grain_key": origin_payload,
                    "origin_grain_sha256": origin_digest,
                    "origin_match_count": 1,
                    "visual_aggregation_eligible": selection_eligible,
                    "detailed_caged_line_visual_use_allowed": False,
                    "source_detail_visual_aggregation_eligible": False,
                    "specific_eligibility_flags_used": True,
                    "global_share_status_used_in_isolation": False,
                    "maximum_exploration_eligible": (
                        selection_eligible
                        and not small_volume
                        and not negative_adjustment
                        and _legacy_direction(absolute_change) in {"gain", "loss"}
                    ),
                    "maximum_exploration_age_pool": age_group,
                }
            )

    shift_filename = "PAINEL_SHIFT_SHARE_SETORIAL_V1_1.csv.gz"
    shift = _read_csv(gcr_root / shift_filename)
    shift_local = shift[shift["municipality_ibge_code"].eq(NSR_CODE)].copy()
    shift_grain = [
        "municipality_ibge_code",
        "cnae_division_code",
        "initial_year",
        "final_year",
    ]
    if shift_local.duplicated(shift_grain).any():
        raise ValueError("O painel shift-share contém grão municipal duplicado")
    for source_row in shift_local.to_dict("records"):
        metric = source_row.get("local_differential_effect")
        compatibility_fact_id = (
            "SHIFT_SHARE_LOCAL_DIFFERENTIAL|"
            f"{source_row['cnae_division_code']}"
        )
        fact_id = "|".join(
            [
                "SHIFT_SHARE_LOCAL_DIFFERENTIAL",
                "municipality",
                NSR_CODE,
                "all_ages",
                "local_differential_effect",
                str(source_row["cnae_division_code"]),
                str(int(source_row["initial_year"])),
                str(int(source_row["final_year"])),
            ]
        )
        origin_payload, origin_digest = _origin_key(source_row, shift_grain)
        small_volume = _as_bool(source_row.get("small_volume_sensitive"))
        selection_eligible = _as_bool(source_row.get("selection_eligible"))
        rows.append(
            {
                "fact_id": fact_id,
                "compatibility_fact_id_v1": compatibility_fact_id,
                "fact_id_version": "job5gcr-grain-v2",
                "universe": "SHIFT_SHARE_LOCAL_DIFFERENTIAL",
                "measure": "local_differential_effect",
                "direction": "no_change" if pd.isna(metric) else _legacy_direction(metric),
                "numeric_direction": _sign_direction(metric),
                "observed_change_direction": _sign_direction(
                    source_row.get("absolute_change")
                ),
                "local_differential_direction": _sign_direction(metric),
                "direction_semantics": (
                    "direction_is_sign_of_local_differential_measure; observed_change_direction_is_separate; "
                    "neither_means_improvement_or_worsening"
                ),
                "dimension_code": source_row["cnae_division_code"],
                "dimension_label": source_row.get("cnae_division_label"),
                "age_group": "all_ages",
                "initial_year": int(source_row["initial_year"]),
                "final_year": int(source_row["final_year"]),
                "initial_value": source_row["initial_value"],
                "final_value": source_row["final_value"],
                "absolute_change": source_row["absolute_change"],
                "relative_change_percent": source_row.get("percent_change"),
                "regional_initial_value": source_row.get("state_sector_initial"),
                "regional_final_value": source_row.get("state_sector_final"),
                "regional_concentration_share_final": None,
                "small_volume_sensitive": small_volume,
                "negative_adjustment_present": False,
                "label_available": _as_bool(source_row.get("label_available")),
                "selection_eligible": selection_eligible,
                "selection_metric": metric,
                "selection_metric_name": "local_differential_effect",
                "source": source_row.get("source"),
                "territorial_lens": source_row.get("territorial_lens"),
                "stock_or_flow": "stock_change_decomposition",
                "population_scope": source_row.get("population_scope"),
                "entity_scope": "municipality",
                "entity_id": NSR_CODE,
                "origin_artifact": shift_filename,
                "origin_grain_fields": json.dumps(
                    shift_grain, ensure_ascii=False, separators=(",", ":")
                ),
                "origin_grain_key": origin_payload,
                "origin_grain_sha256": origin_digest,
                "origin_match_count": 1,
                "visual_aggregation_eligible": selection_eligible,
                "detailed_caged_line_visual_use_allowed": False,
                "source_detail_visual_aggregation_eligible": False,
                "specific_eligibility_flags_used": True,
                "global_share_status_used_in_isolation": False,
                "maximum_exploration_eligible": (
                    selection_eligible
                    and not small_volume
                    and _legacy_direction(metric) in {"gain", "loss"}
                ),
                "maximum_exploration_age_pool": "all_ages",
            }
        )

    catalog = pd.DataFrame(rows)
    catalog["selected_for_synthesis"] = False
    catalog["selection_rank"] = pd.Series(pd.NA, index=catalog.index, dtype="Int64")
    eligible = catalog[
        catalog["selection_eligible"]
        & catalog["direction"].isin(["gain", "loss"])
    ].copy()
    eligible["absolute_selection_metric"] = pd.to_numeric(
        eligible["selection_metric"], errors="coerce"
    ).abs()
    eligible["regional_tiebreak"] = pd.to_numeric(
        eligible["regional_final_value"], errors="coerce"
    ).fillna(-1)
    eligible["absolute_final_value_tiebreak"] = pd.to_numeric(
        eligible["final_value"], errors="coerce"
    ).abs().fillna(-1)
    eligible["absolute_initial_value_tiebreak"] = pd.to_numeric(
        eligible["initial_value"], errors="coerce"
    ).abs().fillna(-1)
    eligible["regional_concentration_tiebreak"] = pd.to_numeric(
        eligible["regional_concentration_share_final"], errors="coerce"
    ).fillna(-1)
    eligible["absolute_relative_change_tiebreak"] = pd.to_numeric(
        eligible["relative_change_percent"], errors="coerce"
    ).abs().fillna(-1)
    exact_tie_fields = [
        "universe",
        "measure",
        "direction",
        "dimension_code",
        "dimension_label",
        "initial_value",
        "final_value",
        "absolute_change",
        "relative_change_percent",
        "regional_initial_value",
        "regional_final_value",
        "regional_concentration_share_final",
    ]
    eligible["exact_tie_content_digest"] = eligible.apply(
        lambda row: hashlib.sha256(
            _canonical_row_payload(row, exact_tie_fields).encode("utf-8")
        ).hexdigest(),
        axis=1,
    )
    for (_, _), group in eligible.groupby(["universe", "direction"], sort=True):
        selected = group.sort_values(
            [
                "absolute_selection_metric",
                "regional_tiebreak",
                "absolute_final_value_tiebreak",
                "absolute_initial_value_tiebreak",
                "regional_concentration_tiebreak",
                "absolute_relative_change_tiebreak",
                "exact_tie_content_digest",
            ],
            ascending=[False, False, False, False, False, False, True],
            kind="mergesort",
        ).head(3)
        catalog.loc[selected.index, "selected_for_synthesis"] = True
        catalog.loc[selected.index, "selection_rank"] = range(1, len(selected) + 1)
    catalog["selection_rule_version"] = "job5gcr-materiality-v1"
    catalog["selection_rule"] = (
        "eligible non-small labeled facts; gains/losses separated; descending absolute substantive metric; "
        "regional volume, endpoint magnitudes, regional concentration and relative change as substantive tie-breakers; "
        "cryptographic content digest only for exact ties; maximum three per universe/direction"
    )
    catalog["physical_order_used"] = False
    catalog["code_order_used"] = False
    catalog["alphabetical_order_used"] = False
    catalog["exact_tie_content_digest_only"] = True
    catalog["compact_selection_compatibility_v1"] = catalog[
        "selected_for_synthesis"
    ]
    catalog["compact_selection_is_editorial_ceiling"] = False
    catalog["external_judgment_required"] = True

    if catalog["fact_id"].duplicated().any():
        duplicates = catalog.loc[catalog["fact_id"].duplicated(False), "fact_id"]
        raise ValueError(f"fact_id v2 duplicado: {duplicates.head(5).tolist()}")

    compatibility_view = catalog.copy()
    compatibility_view["fact_id"] = compatibility_view["compatibility_fact_id_v1"]
    source_counter = _compatibility_counter(source_v1)
    corrected_counter = _compatibility_counter(compatibility_view)
    if source_counter != corrected_counter:
        removed = source_counter - corrected_counter
        added = corrected_counter - source_counter
        raise ValueError(
            "A correção de grão alterou conteúdo substantivo: "
            f"removidos={sum(removed.values())}, adicionados={sum(added.values())}"
        )

    duplicate_v1 = source_v1[source_v1["fact_id"].duplicated(False)]
    caged = catalog[catalog["universe"].str.startswith("CAGED_")]
    maximum_by_age = (
        caged[caged["maximum_exploration_eligible"]]
        .groupby("age_group")
        .size()
        .astype(int)
        .to_dict()
    )
    correction = {
        "sourceRowCount": int(len(source_v1)),
        "correctedRowCount": int(len(catalog)),
        "sourceUniqueFactIdCount": int(source_v1["fact_id"].nunique()),
        "sourceDuplicateFactIdCount": int(duplicate_v1["fact_id"].nunique()),
        "correctedUniqueFactIdCount": int(catalog["fact_id"].nunique()),
        "correctedDuplicateFactIdCount": 0,
        "sourceCompatibilityMultisetSha256": _counter_digest(source_counter),
        "correctedCompatibilityMultisetSha256": _counter_digest(corrected_counter),
        "numericAndSelectionContentPreserved": True,
        "ageGroupNonNullForCaged": bool(caged["age_group"].notna().all()),
        "maximumExplorationEligibleByAgeGroup": maximum_by_age,
        "maximumExplorationKeeps1517": maximum_by_age.get("15_17", 0) > 0,
        "maximumExplorationKeeps1824": maximum_by_age.get("18_24", 0) > 0,
        "compactSelectionCompatibilityRowCount": int(
            catalog["selected_for_synthesis"].sum()
        ),
        "compactSelectionIsEditorialCeiling": False,
        "originMatchCountIsOneForAllFacts": bool(catalog["origin_match_count"].eq(1).all()),
        "directionSemantics": (
            "gain/loss and positive/negative describe numeric sign only, never improvement/worsening"
        ),
        "shiftShareDirectionsSeparated": True,
        "detailedCagedVisualUseAllowed": False,
    }
    return (
        _stable(
            catalog,
            [
                "universe",
                "age_group",
                "direction",
                "selected_for_synthesis",
                "selection_rank",
                "fact_id",
            ],
        ),
        correction,
    )


def _sidra_value(value: Any) -> int:
    lexeme = str(value)
    if lexeme == "-":
        return 0
    if re.fullmatch(r"\d+", lexeme) is None:
        raise ValueError(f"Valor SIDRA indisponível/suprimido não pode ser convertido: {lexeme}")
    return int(lexeme)


def _sidra_cells(path: Path, table_id: str) -> dict[tuple[str, str, str], int]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    result: dict[tuple[str, str, str], int] = {}
    for row in rows:
        code = str(row["D1C"])
        location = str(row["D4C"])
        course = str(row["D7C"]) if table_id == "10324" else "ALL"
        key = (code, location, course)
        if key in result:
            raise ValueError(f"Célula SIDRA duplicada: {key}")
        result[key] = _sidra_value(row["V"])
    return result


def build_mobility_panel(
    *,
    source_root: Path,
    municipality_names: Mapping[str, str],
    frozen_job2_panel: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    source_manifest = json.loads(
        (source_root / "MANIFEST_SOURCE_MOBILITY_SIDRA_JOB5GD.json").read_text(
            encoding="utf-8"
        )
    )
    municipal_cells = {
        table: _sidra_cells(
            source_root / f"values_{table}_vale_municipalities.json", table
        )
        for table in ("10321", "10324")
    }
    state_cells = {
        table: _sidra_cells(source_root / f"values_{table}_rs.json", table)
        for table in ("10321", "10324")
    }
    stage_specs = {
        "total": ("10321", "ALL"),
        "fundamental": ("10324", "12121"),
        "medio": ("10324", "12122"),
    }

    def make_row(
        *,
        code: str,
        name: str,
        entity_scope: str,
        entity_id: str,
        stage: str,
        table: str,
        course: str,
        cells: Mapping[tuple[str, str, str], int],
        aggregation_method: str,
    ) -> dict[str, Any]:
        own = cells[(code, "12163", course)]
        other = cells[(code, "12164", course)]
        foreign = cells[(code, "12165", course)]
        total = cells[(code, "79174", course)]
        component_residual = total - own - other - foreign
        # O indicador congelado do Job 2 usa literalmente a categoria oficial
        # "Outro município". País estrangeiro permanece separado. O total
        # oficial pode diferir da soma dos componentes publicados (estimativas
        # amostrais e categorias residuais); essa diferença é auditada, nunca
        # redistribuída entre os componentes.
        outside = other
        return {
            "year": 2022,
            "entity_scope": entity_scope,
            "entity_id": entity_id,
            "municipality_ibge_code": code if entity_scope == "municipality" else None,
            "municipality_name": name if entity_scope == "municipality" else None,
            "territory_name": name,
            "stage": stage,
            "residents_studying_total": total,
            "residents_studying_own_municipality": own,
            "residents_studying_other_municipality": other,
            "residents_studying_foreign_country": foreign,
            "residents_studying_outside_municipality": outside,
            "study_location_component_residual": component_residual,
            "study_location_components_close_total_exactly": component_residual == 0,
            "outside_share_percent": safe_ratio(outside, total, multiplier=100.0),
            "numerator": outside,
            "denominator": total,
            "value_status": "observed",
            "source_table": table,
            "source_variable": "13631" if table == "10321" else "2021",
            "source": "SIDRA/IBGE - Censo Demográfico 2022",
            "source_snapshot_manifest_sha256": sha256_file(
                source_root / "MANIFEST_SOURCE_MOBILITY_SIDRA_JOB5GD.json"
            ),
            "territorial_lens": "student_residence",
            "population_scope": (
                "residents_attending_school_or_daycare_table_10321"
                if table == "10321"
                else "residents_attending_school_or_daycare_by_course_table_10324"
            ),
            "network_scope": "not_applicable",
            "aggregation_method": aggregation_method,
            "destination_municipality_available": False,
            "origin_destination_matrix_derived": False,
            "foreign_country_included_in_outside": False,
            "outside_numerator_category": "Outro município (SIDRA classification 468 code 12164)",
            "official_preliminary_result": True,
            "state_comparison_contract_compatible": True,
            "causal_interpretation_allowed": False,
        }

    municipal_rows: list[dict[str, Any]] = []
    for code, name in municipality_names.items():
        for stage, (table, course) in stage_specs.items():
            municipal_rows.append(
                make_row(
                    code=code,
                    name=name,
                    entity_scope="municipality",
                    entity_id=code,
                    stage=stage,
                    table=table,
                    course=course,
                    cells=municipal_cells[table],
                    aggregation_method="official_municipal_cell_closure",
                )
            )
    municipal = pd.DataFrame(municipal_rows)
    region_rows: list[dict[str, Any]] = []
    for stage, (table, _course) in stage_specs.items():
        group = municipal[municipal["stage"].eq(stage)]
        row = {
            column: None
            for column in municipal.columns
        }
        row.update(
            {
                "year": 2022,
                "entity_scope": "region",
                "entity_id": REGION_ENTITY_ID,
                "territory_name": "Vale do Sinos",
                "stage": stage,
                "residents_studying_total": int(group["residents_studying_total"].sum()),
                "residents_studying_own_municipality": int(
                    group["residents_studying_own_municipality"].sum()
                ),
                "residents_studying_other_municipality": int(
                    group["residents_studying_other_municipality"].sum()
                ),
                "residents_studying_foreign_country": int(
                    group["residents_studying_foreign_country"].sum()
                ),
                "residents_studying_outside_municipality": int(
                    group["residents_studying_outside_municipality"].sum()
                ),
                "study_location_component_residual": int(
                    group["study_location_component_residual"].sum()
                ),
                "study_location_components_close_total_exactly": bool(
                    group["study_location_components_close_total_exactly"].all()
                ),
                "source_table": table,
                "source_variable": "13631" if table == "10321" else "2021",
                "source": "SIDRA/IBGE - Censo Demográfico 2022",
                "source_snapshot_manifest_sha256": sha256_file(
                    source_root / "MANIFEST_SOURCE_MOBILITY_SIDRA_JOB5GD.json"
                ),
                "territorial_lens": "student_residence",
                "population_scope": group.iloc[0]["population_scope"],
                "network_scope": "not_applicable",
                "aggregation_method": "sum_compatible_municipal_counts_then_ratio",
                "destination_municipality_available": False,
                "origin_destination_matrix_derived": False,
                "foreign_country_included_in_outside": False,
                "outside_numerator_category": "Outro município (SIDRA classification 468 code 12164)",
                "official_preliminary_result": True,
                "state_comparison_contract_compatible": True,
                "causal_interpretation_allowed": False,
                "value_status": "observed",
            }
        )
        row["numerator"] = row["residents_studying_outside_municipality"]
        row["denominator"] = row["residents_studying_total"]
        row["outside_share_percent"] = safe_ratio(
            row["numerator"], row["denominator"], multiplier=100.0
        )
        region_rows.append(row)

    state_rows: list[dict[str, Any]] = []
    for stage, (table, course) in stage_specs.items():
        state_rows.append(
            make_row(
                code="43",
                name="Rio Grande do Sul",
                entity_scope="state",
                entity_id=STATE_ENTITY_ID,
                stage=stage,
                table=table,
                course=course,
                cells=state_cells[table],
                aggregation_method="official_state_cell_closure",
            )
        )
    panel = pd.concat(
        [municipal, pd.DataFrame(region_rows), pd.DataFrame(state_rows)],
        ignore_index=True,
    )

    comparable = panel[panel["entity_scope"].isin(["municipality", "region"])].copy()
    frozen = frozen_job2_panel.copy()
    frozen["entity_id"] = np.where(
        frozen["entity_scope"].eq("municipality"),
        frozen["municipality_ibge_code"].astype("string"),
        REGION_ENTITY_ID,
    )
    check = comparable.merge(
        frozen[
            [
                "entity_id",
                "universe",
                "students_total",
                "students_outside_municipality",
                "outside_share_percent",
            ]
        ].rename(columns={"universe": "stage"}),
        on=["entity_id", "stage"],
        how="outer",
        validate="one_to_one",
        suffixes=("", "_frozen"),
        indicator=True,
    )
    if not check["_merge"].eq("both").all():
        raise ValueError("O recorte SIDRA atual não corresponde ao painel congelado do Job 2")
    for current, frozen_column in (
        ("residents_studying_total", "students_total"),
        (
            "residents_studying_outside_municipality",
            "students_outside_municipality",
        ),
        ("outside_share_percent", "outside_share_percent_frozen"),
    ):
        difference = (
            pd.to_numeric(check[current], errors="coerce")
            - pd.to_numeric(check[frozen_column], errors="coerce")
        ).abs()
        if (difference > 1e-10).any():
            raise ValueError(f"Âncora SIDRA divergiu do Job 2 em {current}")

    nsr = panel[
        panel["entity_scope"].eq("municipality")
        & panel["entity_id"].eq(NSR_CODE)
    ].set_index("stage")
    anchors = {
        stage: {
            "numerator": int(nsr.loc[stage, "numerator"]),
            "denominator": int(nsr.loc[stage, "denominator"]),
            "outsideSharePercent": float(nsr.loc[stage, "outside_share_percent"]),
        }
        for stage in ("total", "fundamental", "medio")
    }
    audit = {
        "sourceManifestSha256": sha256_file(
            source_root / "MANIFEST_SOURCE_MOBILITY_SIDRA_JOB5GD.json"
        ),
        "sourceAcquiredAtUtc": source_manifest["acquiredAtUtc"],
        "municipalityCount": len(municipality_names),
        "rowCount": int(len(panel)),
        "municipalToRegionClosure": True,
        "frozenJob2Parity": True,
        "novaSantaRitaAnchors": anchors,
        "destinationMunicipalityAvailable": False,
        "originDestinationMatrixDerived": False,
        "outsideNumeratorCategory": "Outro município (classification 468 code 12164)",
        "foreignCountryIncludedInOutside": False,
        "maximumAbsolutePublishedComponentResidual": int(
            panel["study_location_component_residual"].abs().max()
        ),
    }
    return (
        _stable(panel, ["entity_scope", "entity_id", "stage"]),
        audit,
    )


def _entity_id_from_row(row: Mapping[str, Any]) -> str:
    scope = str(row.get("entity_scope"))
    if scope == "municipality":
        code = str(row.get("municipality_ibge_code"))
        if IBGE_CODE_PATTERN.fullmatch(code) is None:
            raise ValueError(f"Código IBGE municipal inválido: {code!r}")
        return code
    if scope == "region":
        return REGION_ENTITY_ID
    if scope == "state":
        return STATE_ENTITY_ID
    raise ValueError(f"Escopo territorial desconhecido: {scope!r}")


def _with_series_endpoints(panel: pd.DataFrame) -> pd.DataFrame:
    keys = ["entity_id", "offer_domain", "stage", "metric", "source_artifact"]
    panel = panel.copy()
    panel["year"] = pd.to_numeric(panel["year"], errors="raise").astype(int)
    panel["value"] = pd.to_numeric(panel["value"], errors="coerce")
    endpoint_rows: list[dict[str, Any]] = []
    for group_key, group in panel.groupby(keys, dropna=False, sort=True):
        observed = group[group["value"].notna()].sort_values("year", kind="mergesort")
        if observed.empty:
            summary = {
                "series_initial_year": None,
                "series_final_year": None,
                "series_initial_value": None,
                "series_final_value": None,
                "series_absolute_change": None,
                "series_relative_change_percent": None,
                "series_change_status": "unavailable",
                "series_observed_year_count": 0,
            }
        else:
            initial = observed.iloc[0]
            final = observed.iloc[-1]
            initial_value = float(initial["value"])
            final_value = float(final["value"])
            summary = {
                "series_initial_year": int(initial["year"]),
                "series_final_year": int(final["year"]),
                "series_initial_value": initial_value,
                "series_final_value": final_value,
                "series_absolute_change": final_value - initial_value,
                "series_relative_change_percent": _relative_change(
                    initial_value, final_value
                ),
                "series_change_status": (
                    "base_zero_absolute_change_only"
                    if initial_value == 0
                    else "relative_change_available"
                ),
                "series_observed_year_count": int(observed["year"].nunique()),
            }
        endpoint_rows.append(
            {
                **{key: value for key, value in zip(keys, group_key, strict=True)},
                **summary,
            }
        )
    endpoints = pd.DataFrame(endpoint_rows)
    return panel.merge(endpoints, on=keys, how="left", validate="many_to_one")


def build_territorial_offer_panel(
    *,
    job2_root: Path,
    gar_root: Path,
    gbr_root: Path,
    gcr_root: Path,
    municipality_names: Mapping[str, str],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    def append(
        *,
        year: Any,
        entity_scope: str,
        entity_id: str,
        municipality_code: str | None,
        municipality_name: str | None,
        territory_name: str,
        domain: str,
        stage: str,
        metric: str,
        value: Any,
        value_status: str,
        unit: str,
        counting_unit: str,
        source: str,
        source_artifact: str,
        lens: str,
        population_scope: str,
        aggregation_rule: str,
        person_unique: bool,
        availability_state: str = "available",
        zero_access_conclusion_allowed: bool = False,
    ) -> None:
        rows.append(
            {
                "year": int(year),
                "entity_scope": entity_scope,
                "entity_id": entity_id,
                "municipality_ibge_code": municipality_code,
                "municipality_name": municipality_name,
                "territory_name": territory_name,
                "offer_domain": domain,
                "stage": stage,
                "metric": metric,
                "value": _json_safe(value),
                "value_status": value_status,
                "availability_state": availability_state,
                "unit": unit,
                "counting_unit": counting_unit,
                "source": source,
                "source_artifact": source_artifact,
                "territorial_lens": lens,
                "network_scope": "total_all_dependencies",
                "population_scope": population_scope,
                "aggregation_rule": aggregation_rule,
                "person_unique": person_unique,
                "administrative_dependency_is_analytic_dimension": False,
                "administrative_dependency_is_QA_dimension": True,
                "dependency_breakdown_exposed_for_analysis": False,
                "zero_observed_means_no_located_offer_only": True,
                "zero_access_conclusion_allowed": zero_access_conclusion_allowed,
                "causal_interpretation_allowed": False,
            }
        )

    network = _read_csv(job2_root / "2e" / "rede_escolar.csv.gz")
    network_metrics = {
        "schools": ("all", "schools", "schools", "school"),
        "preschool_enrollments": (
            "pre_escola",
            "located_enrollments",
            "enrollments",
            "enrollment",
        ),
        "fundamental_enrollments": (
            "fundamental",
            "located_enrollments",
            "enrollments",
            "enrollment",
        ),
        "high_school_enrollments": (
            "medio",
            "located_enrollments",
            "enrollments",
            "enrollment",
        ),
        "eja_enrollments": (
            "eja",
            "located_enrollments",
            "enrollments",
            "enrollment",
        ),
    }
    for source_row in network.to_dict("records"):
        scope = str(source_row["entity_scope"])
        entity_id = _entity_id_from_row(source_row)
        code = (
            str(source_row["municipality_ibge_code"])
            if scope == "municipality"
            else None
        )
        name = str(source_row.get("municipality_name")) if scope == "municipality" else None
        territory_name = (
            name
            if scope == "municipality"
            else "Vale do Sinos" if scope == "region" else "Rio Grande do Sul"
        )
        for source_column, (stage, metric, unit, counting_unit) in network_metrics.items():
            append(
                year=source_row["year"],
                entity_scope=scope,
                entity_id=entity_id,
                municipality_code=code,
                municipality_name=name,
                territory_name=territory_name,
                domain="general_offer",
                stage=stage,
                metric=metric,
                value=source_row[source_column],
                value_status="observed",
                unit=unit,
                counting_unit=counting_unit,
                source="INEP/Censo Escolar via Job 2 congelado",
                source_artifact="v7-job2/2e/rede_escolar.csv.gz",
                lens="school_location",
                population_scope="located_school_offer",
                aggregation_rule=(
                    "sum_compatible_municipal_counts"
                    if scope == "region"
                    else "official_or_frozen_count"
                ),
                person_unique=False,
            )

    staffing = _read_csv(
        gar_root / "PAINEL_DOCENTES_TURMAS_JORNADA_V1_1.csv.gz"
    )
    staffing = staffing[
        staffing["metric"].isin(["docentes", "turmas"])
        & staffing["stage"].isin(
            ["educacao_infantil", "fundamental", "medio", "eja", "profissional"]
        )
    ].copy()
    for source_row in staffing.to_dict("records"):
        code = str(source_row["municipality_ibge_code"])
        metric = "reported_teaching_units" if source_row["metric"] == "docentes" else "classes"
        append(
            year=source_row["year"],
            entity_scope="municipality",
            entity_id=code,
            municipality_code=code,
            municipality_name=municipality_names[code],
            territory_name=municipality_names[code],
            domain="staffing_and_classes",
            stage=str(source_row["stage"]),
            metric=metric,
            value=source_row["value"],
            value_status=str(source_row["value_status"]),
            unit=str(source_row["unit"]),
            counting_unit=str(source_row["counting_unit"]),
            source=str(source_row["source_table"]),
            source_artifact="v7-job5gar/PAINEL_DOCENTES_TURMAS_JORNADA_V1_1.csv.gz",
            lens="school_location",
            population_scope="reported_school_units",
            aggregation_rule="municipal_reported_count",
            person_unique=False,
        )
    staffing_municipal = pd.DataFrame(
        [
            row
            for row in rows
            if row["offer_domain"] == "staffing_and_classes"
            and row["entity_scope"] == "municipality"
        ]
    )
    for (year, stage, metric), group in staffing_municipal.groupby(
        ["year", "stage", "metric"], sort=True
    ):
        observed = pd.to_numeric(group["value"], errors="coerce")
        append(
            year=year,
            entity_scope="region",
            entity_id=REGION_ENTITY_ID,
            municipality_code=None,
            municipality_name=None,
            territory_name="Vale do Sinos",
            domain="staffing_and_classes",
            stage=stage,
            metric=metric,
            value=observed.sum(min_count=len(municipality_names)),
            value_status="observed" if observed.notna().sum() == 10 else "unavailable",
            unit=str(group.iloc[0]["unit"]),
            counting_unit=str(group.iloc[0]["counting_unit"]),
            source=str(group.iloc[0]["source"]),
            source_artifact="v7-job5gar/PAINEL_DOCENTES_TURMAS_JORNADA_V1_1.csv.gz",
            lens="school_location",
            population_scope="sum_of_municipal_reported_units_not_unique_people",
            aggregation_rule="sum_compatible_municipal_reported_units",
            person_unique=False,
            availability_state=(
                "available" if observed.notna().sum() == 10 else "incomplete_municipal_coverage"
            ),
        )

    rural = _read_csv(
        gbr_root / "PAINEL_EDUCACAO_RURAL_TERRITORIO_V1_1.csv.gz"
    )
    rural = rural[
        rural["stage"].eq("all")
        | (
            rural["metric"].eq("rural_enrollments")
            & rural["stage"].isin(
                ["early_childhood", "fundamental", "high_school", "eja", "professional"]
            )
        )
    ]
    for source_row in rural.to_dict("records"):
        scope = str(source_row["entity_scope"])
        entity_id = _entity_id_from_row(source_row)
        code = str(source_row["municipality_ibge_code"]) if scope == "municipality" else None
        name = municipality_names[code] if code else None
        append(
            year=source_row["year"],
            entity_scope=scope,
            entity_id=entity_id,
            municipality_code=code,
            municipality_name=name,
            territory_name=name or ("Vale do Sinos" if scope == "region" else "Rio Grande do Sul"),
            domain="rural_offer",
            stage=str(source_row["stage"]),
            metric=str(source_row["metric"]),
            value=source_row["value"],
            value_status=str(source_row["value_status"]),
            unit=str(source_row["unit"]),
            counting_unit=str(source_row["metric_family"]).lower(),
            source=str(source_row["source"]),
            source_artifact="v7-job5gbr/PAINEL_EDUCACAO_RURAL_TERRITORIO_V1_1.csv.gz",
            lens="rural_school_location",
            population_scope="located_rural_school_offer",
            aggregation_rule=(
                "source_validated_regional_sum"
                if scope == "region"
                else "source_observed_count"
            ),
            person_unique=False,
        )

    ept = _read_csv(gcr_root / "PAINEL_EPT_OFERTA_TOTAL_V1_1.csv.gz")
    ept = ept[ept["grain"].isin(["municipality_total", "region_total"])]
    for source_row in ept.to_dict("records"):
        scope = str(source_row["entity_scope"])
        entity_id = str(source_row["entity_id"])
        code = str(source_row["municipality_ibge_code"]) if scope == "municipality" else None
        name = municipality_names[code] if code else None
        append(
            year=source_row["year"],
            entity_scope=scope,
            entity_id=entity_id,
            municipality_code=code,
            municipality_name=name,
            territory_name=name or "Vale do Sinos",
            domain="ept_offer",
            stage="professional_technical",
            metric="located_technical_enrollments",
            value=source_row["technical_enrollments"],
            value_status="observed",
            availability_state=str(source_row["availability_status"]),
            unit="enrollments",
            counting_unit="enrollment",
            source=str(source_row["source"]),
            source_artifact="v7-job5gcr/PAINEL_EPT_OFERTA_TOTAL_V1_1.csv.gz",
            lens="school_location",
            population_scope="located_technical_offer",
            aggregation_rule="source_total_at_declared_grain",
            person_unique=False,
        )

    integrated = _read_csv(
        gbr_root / "PAINEL_EJA_INTEGRADA_EPT_V1_1.csv.gz"
    )
    integrated = integrated[integrated["modality"].eq("integrated_total")]
    for source_row in integrated.to_dict("records"):
        scope = str(source_row["entity_scope"])
        entity_id = _entity_id_from_row(source_row)
        code = str(source_row["municipality_ibge_code"]) if scope == "municipality" else None
        name = municipality_names[code] if code else None
        append(
            year=source_row["year"],
            entity_scope=scope,
            entity_id=entity_id,
            municipality_code=code,
            municipality_name=name,
            territory_name=name or ("Vale do Sinos" if scope == "region" else "Rio Grande do Sul"),
            domain="eja_integrated_ept",
            stage="eja_integrated_ept",
            metric="located_integrated_eja_enrollments",
            value=source_row["integrated_eja_enrollments"],
            value_status=str(source_row["value_status"]),
            unit="enrollments",
            counting_unit="enrollment",
            source=str(source_row["source"]),
            source_artifact="v7-job5gbr/PAINEL_EJA_INTEGRADA_EPT_V1_1.csv.gz",
            lens="school_location",
            population_scope="located_integrated_eja_offer",
            aggregation_rule="source_total_at_declared_grain",
            person_unique=False,
        )

    special = _read_csv(
        gbr_root / "PAINEL_EDUCACAO_ESPECIAL_AEE_V1_1.csv.gz"
    )
    special = special[
        special["metric"].isin(["special_enrollments", "schools_offering_aee"])
        & special["stage"].eq("all")
    ]
    for source_row in special.to_dict("records"):
        scope = str(source_row["entity_scope"])
        entity_id = _entity_id_from_row(source_row)
        code = str(source_row["municipality_ibge_code"]) if scope == "municipality" else None
        name = municipality_names[code] if code else None
        append(
            year=source_row["year"],
            entity_scope=scope,
            entity_id=entity_id,
            municipality_code=code,
            municipality_name=name,
            territory_name=name or ("Vale do Sinos" if scope == "region" else "Rio Grande do Sul"),
            domain="special_education_aee",
            stage="all",
            metric=str(source_row["metric"]),
            value=source_row["value"],
            value_status=str(source_row["value_status"]),
            unit=str(source_row["unit"]),
            counting_unit=str(source_row["metric_family"]).lower(),
            source=str(source_row["source"]),
            source_artifact="v7-job5gbr/PAINEL_EDUCACAO_ESPECIAL_AEE_V1_1.csv.gz",
            lens="school_location",
            population_scope="located_special_education_offer",
            aggregation_rule="source_total_at_declared_grain",
            person_unique=False,
        )

    full_time_municipal = staffing = _read_csv(
        gar_root / "PAINEL_DOCENTES_TURMAS_JORNADA_V1_1.csv.gz"
    )
    full_time_municipal = full_time_municipal[
        full_time_municipal["metric"].eq("percentual_tempo_integral")
        & full_time_municipal["stage"].isin(
            ["educacao_infantil", "fundamental", "medio"]
        )
    ]
    for source_row in full_time_municipal.to_dict("records"):
        code = str(source_row["municipality_ibge_code"])
        append(
            year=source_row["year"],
            entity_scope="municipality",
            entity_id=code,
            municipality_code=code,
            municipality_name=municipality_names[code],
            territory_name=municipality_names[code],
            domain="full_time_offer",
            stage=str(source_row["stage"]),
            metric="full_time_enrollment_share_percent",
            value=source_row["value"],
            value_status=str(source_row["value_status"]),
            unit="percent",
            counting_unit="enrollment",
            source=str(source_row["source_table"]),
            source_artifact="v7-job5gar/PAINEL_DOCENTES_TURMAS_JORNADA_V1_1.csv.gz",
            lens="school_location",
            population_scope="located_enrollments_in_declared_stage",
            aggregation_rule="official_municipal_ratio",
            person_unique=False,
        )
    full_time_region = _read_csv(
        gar_root / "PAINEL_TEMPO_INTEGRAL_REGIONAL_V1.csv.gz"
    )
    full_time_region = full_time_region[
        full_time_region["stage"].isin(["educacao_infantil", "fundamental", "medio"])
    ]
    for source_row in full_time_region.to_dict("records"):
        append(
            year=source_row["year"],
            entity_scope="region",
            entity_id=REGION_ENTITY_ID,
            municipality_code=None,
            municipality_name=None,
            territory_name="Vale do Sinos",
            domain="full_time_offer",
            stage=str(source_row["stage"]),
            metric="full_time_enrollment_share_percent",
            value=source_row["regional_integral_share"],
            value_status=(
                "observed"
                if _as_bool(source_row["regional_integral_share_eligible"])
                else "unavailable"
            ),
            availability_state=str(source_row["availability_state"]),
            unit="percent",
            counting_unit="enrollment",
            source="INEP/Censo Escolar via Job 5G-A-R",
            source_artifact="v7-job5gar/PAINEL_TEMPO_INTEGRAL_REGIONAL_V1.csv.gz",
            lens="school_location",
            population_scope="located_enrollments_in_declared_stage",
            aggregation_rule=str(source_row["regional_percentage_method"]),
            person_unique=False,
        )

    panel = _with_series_endpoints(pd.DataFrame(rows))
    key = ["entity_id", "year", "offer_domain", "stage", "metric", "source_artifact"]
    if panel.duplicated(key).any():
        raise ValueError("O painel territorial de oferta contém chave duplicada")
    observed_codes = set(
        panel.loc[panel["entity_scope"].eq("municipality"), "entity_id"].astype(str)
    )
    if observed_codes != set(municipality_names):
        raise ValueError("O painel territorial não cobre exatamente os dez municípios")
    if not panel["administrative_dependency_is_analytic_dimension"].eq(False).all():
        raise ValueError("Dependência administrativa entrou como dimensão analítica")
    return _stable(panel, key)


def build_transport_pnate_panel(
    *,
    pnate_source: pd.DataFrame,
    municipality_names: Mapping[str, str],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    source = pnate_source.copy()
    source["id_municipio"] = source["id_municipio"].astype("string")
    source["ano"] = pd.to_numeric(source["ano"], errors="raise").astype(int)
    expected_codes = set(municipality_names)
    if set(source["id_municipio"].astype(str)) != expected_codes:
        raise ValueError("Snapshot PNATE não cobre exatamente os dez municípios")
    if set(source["ano"]) != {2024, 2025, 2026}:
        raise ValueError("Snapshot PNATE não cobre os exercícios 2024–2026")
    if source.duplicated(["id_municipio", "ano"]).any() or len(source) != 30:
        raise ValueError("Snapshot PNATE não possui grão município × exercício único")

    dependency_closures = []
    for row in source.to_dict("records"):
        code = str(row["id_municipio"])
        if municipality_names[code] != str(row["municipio"]):
            raise ValueError(f"Nome PNATE diverge do registro canônico em {code}")
        total = int(row["total_alunos"])
        municipal_component = int(row["total_alunos_rede_municipal"])
        state_component = int(row["total_alunos_rede_estadual"])
        dependency_closures.append(total == municipal_component + state_component)
    if not all(dependency_closures):
        raise ValueError("Componentes de dependência PNATE não fecham no total QA")

    metric_specs = {
        "total_alunos": (
            "pnate_beneficiary_students",
            "students",
            "beneficiary_count",
            "observed_source_count",
        ),
        "repasse_total": (
            "pnate_source_reported_repasse",
            "BRL_nominal",
            "source_reported_repasse",
            "official_nominal",
        ),
        "repasse_autorizado_apos_desconto": (
            "pnate_authorized_after_discount",
            "BRL_nominal",
            "authorized",
            "official_nominal",
        ),
        "previsao_repasse_ajustado": (
            "pnate_adjusted_forecast",
            "BRL_nominal",
            "forecast",
            "official_nominal",
        ),
        "saldo_ano_anterior": (
            "pnate_prior_year_balance",
            "BRL_nominal",
            "balance",
            "official_nominal",
        ),
        "desconto": (
            "pnate_discount_adjustment",
            "BRL_nominal",
            "adjustment",
            "official_nominal",
        ),
    }
    rows: list[dict[str, Any]] = []

    def record_type(source_row: Mapping[str, Any]) -> str:
        sheet = str(source_row.get("aba_origem") or "")
        if "Atendimento Anual" in sheet:
            return "annual_attendance_report"
        if int(source_row["ano"]) == 2026:
            return "planning_forecast"
        return "general_program_record"

    for source_row in source.to_dict("records"):
        code = str(source_row["id_municipio"])
        for source_field, (metric, unit, stage, nature) in metric_specs.items():
            value = source_row.get(source_field)
            rows.append(
                {
                    "exercise_year": int(source_row["ano"]),
                    "entity_scope": "municipality",
                    "entity_id": code,
                    "municipality_ibge_code": code,
                    "municipality_name": municipality_names[code],
                    "territory_name": municipality_names[code],
                    "metric": metric,
                    "value": _json_safe(value),
                    "value_status": "observed" if _json_safe(value) is not None else "unavailable",
                    "unit": unit,
                    "financial_stage": stage,
                    "amount_nature": nature,
                    "exercise_record_type": record_type(source_row),
                    "executor_scope": "municipality_executor",
                    "territorial_lens": "municipal_executor",
                    "source": str(source_row["fonte"]),
                    "source_file": str(source_row["arquivo_origem"]),
                    "source_sheet": str(source_row["aba_origem"]),
                    "aggregation_rule": "official_source_value_at_municipal_executor_grain",
                    "administrative_dependency_is_analytic_dimension": False,
                    "administrative_dependency_is_QA_dimension": True,
                    "dependency_components_close_total_qa": True,
                    "dependency_breakdown_exposed_for_analysis": False,
                    "is_mobility_measure": False,
                    "is_origin_destination_matrix": False,
                    "is_school_transport_usage_census_count": False,
                    "derived_per_student_rate": False,
                    "execution_claim_allowed": False,
                    "causal_interpretation_allowed": False,
                }
            )
        for metric, unit, stage, reason in (
            (
                "school_transport_students_observed",
                "students",
                "usage_observation",
                "compatible_ten_municipality_observation_not_materialized",
            ),
            (
                "pnate_executed_amount",
                "BRL_nominal",
                "executed",
                "execution_not_present_in_source_table",
            ),
        ):
            rows.append(
                {
                    "exercise_year": int(source_row["ano"]),
                    "entity_scope": "municipality",
                    "entity_id": code,
                    "municipality_ibge_code": code,
                    "municipality_name": municipality_names[code],
                    "territory_name": municipality_names[code],
                    "metric": metric,
                    "value": None,
                    "value_status": "unavailable",
                    "unit": unit,
                    "financial_stage": stage,
                    "amount_nature": "unavailable",
                    "exercise_record_type": record_type(source_row),
                    "executor_scope": "municipality_executor",
                    "territorial_lens": "municipal_executor",
                    "source": str(source_row["fonte"]),
                    "source_file": str(source_row["arquivo_origem"]),
                    "source_sheet": str(source_row["aba_origem"]),
                    "aggregation_rule": "not_available",
                    "unavailability_reason": reason,
                    "administrative_dependency_is_analytic_dimension": False,
                    "administrative_dependency_is_QA_dimension": True,
                    "dependency_components_close_total_qa": True,
                    "dependency_breakdown_exposed_for_analysis": False,
                    "is_mobility_measure": False,
                    "is_origin_destination_matrix": False,
                    "is_school_transport_usage_census_count": metric.startswith("school_transport"),
                    "derived_per_student_rate": False,
                    "execution_claim_allowed": False,
                    "causal_interpretation_allowed": False,
                }
            )
    municipal = pd.DataFrame(rows)
    region_rows: list[dict[str, Any]] = []
    for (year, metric), group in municipal.groupby(
        ["exercise_year", "metric"], sort=True
    ):
        values = pd.to_numeric(group["value"], errors="coerce")
        first = group.iloc[0].to_dict()
        complete = values.notna().sum() == len(municipality_names)
        first.update(
            {
                "entity_scope": "region",
                "entity_id": REGION_ENTITY_ID,
                "municipality_ibge_code": None,
                "municipality_name": None,
                "territory_name": "Vale do Sinos",
                "value": float(values.sum()) if complete else None,
                "value_status": "observed" if complete else "unavailable",
                "aggregation_rule": (
                    "sum_compatible_municipal_executor_values"
                    if complete
                    else "unavailable_due_to_missing_municipal_values"
                ),
                "unavailability_reason": (
                    None if complete else first.get("unavailability_reason")
                ),
            }
        )
        region_rows.append(first)
    panel = pd.DataFrame(
        [*municipal.to_dict("records"), *region_rows], columns=municipal.columns
    )
    key = ["entity_id", "exercise_year", "metric"]
    if panel.duplicated(key).any():
        raise ValueError("Painel PNATE contém chave duplicada")
    audit = {
        "sourceRowCount": int(len(source)),
        "municipalityCount": int(source["id_municipio"].nunique()),
        "periods": sorted(int(year) for year in source["ano"].unique()),
        "dependencyClosureQARowCount": int(sum(dependency_closures)),
        "dependencyAnalyticDimensionUsed": False,
        "schoolTransportUsageAvailable": False,
        "executionAmountAvailable": False,
        "mobilityProxyUsed": False,
        "derivedPerStudentRateUsed": False,
        "databaseLoadTimestampMinimum": str(source["data_carga"].min()),
        "databaseLoadTimestampMaximum": str(source["data_carga"].max()),
    }
    return _stable(panel, key), audit


def _nested(payload: Mapping[str, Any], *path: str) -> Any:
    current: Any = payload
    for key in path:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current


def build_contextual_finance_panel(
    *,
    finance_root: Path,
    municipality_names: Mapping[str, str],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    input_hashes: dict[str, str] = {}

    metric_specs = [
        (
            "mde_applied_rate",
            ("constitutionalApplication", "mdeAppliedRate", "canonical"),
            "percent",
            "calculated_indicator",
            False,
            "constitutional_application_context",
        ),
        (
            "mde_margin_from_minimum",
            ("constitutionalApplication", "mdeMarginFromMinimum"),
            "percentage_points",
            "calculated_indicator",
            False,
            "constitutional_application_context",
        ),
        (
            "fundeb_professional_remuneration_rate",
            (
                "constitutionalApplication",
                "fundebProfessionalRemunerationRate",
                "canonical",
            ),
            "percent",
            "calculated_indicator",
            False,
            "staffing_finance_context",
        ),
        (
            "fundeb_revenue_received_declared",
            ("constitutionalApplication", "fundebRevenueReceivedDeclared"),
            "BRL_nominal",
            "received",
            True,
            "offer_organization_context",
        ),
        (
            "education_committed",
            ("execution", "dcaEducation", "committed"),
            "BRL_nominal",
            "empenhado",
            True,
            "execution_capacity_context",
        ),
        (
            "education_liquidated",
            ("execution", "dcaEducation", "liquidated"),
            "BRL_nominal",
            "liquidado",
            True,
            "execution_capacity_context",
        ),
        (
            "education_paid",
            ("execution", "dcaEducation", "paid"),
            "BRL_nominal",
            "paid",
            True,
            "execution_capacity_context",
        ),
        (
            "education_outstanding_non_processed",
            ("execution", "dcaEducation", "outstandingNonProcessed"),
            "BRL_nominal",
            "balance",
            True,
            "execution_capacity_context",
        ),
        (
            "education_outstanding_processed",
            ("execution", "dcaEducation", "outstandingProcessed"),
            "BRL_nominal",
            "balance",
            True,
            "execution_capacity_context",
        ),
        (
            "qse_distributed_closed_year",
            ("amounts", "qseDistributedClosedYear"),
            "BRL_nominal",
            "transferred",
            True,
            "general_mde_context",
        ),
        (
            "fundeb_total_annual_forecast",
            ("amounts", "fundebTotalAnnualForecast"),
            "BRL_nominal",
            "forecast",
            True,
            "future_offer_pressure_context",
        ),
        (
            "fundeb_vaar_annual_forecast",
            ("amounts", "fundebVaarAnnualForecast"),
            "BRL_nominal",
            "forecast",
            True,
            "conditional_support_context",
        ),
    ]

    for code, name in municipality_names.items():
        path = finance_root / code / "financeiro.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        if str(_nested(payload, "municipality", "ibgeCode")) != code:
            raise ValueError(f"Contrato financeiro com identidade divergente: {path}")
        if str(_nested(payload, "municipality", "name")) != name:
            raise ValueError(f"Contrato financeiro com nome divergente: {path}")
        input_hashes[code] = sha256_file(path)
        for metric, object_path, default_unit, default_stage, additive, relevance in metric_specs:
            value_object = _nested(payload, *object_path)
            if not isinstance(value_object, Mapping):
                value_object = {}
            value = value_object.get("value")
            reference_year = value_object.get("referenceYear")
            rows.append(
                {
                    "entity_scope": "municipality",
                    "entity_id": code,
                    "municipality_ibge_code": code,
                    "municipality_name": name,
                    "territory_name": name,
                    "metric": metric,
                    "value": _json_safe(value),
                    "value_status": "observed" if _json_safe(value) is not None else "unavailable",
                    "unit": str(value_object.get("unit") or default_unit),
                    "reference_year": int(reference_year) if reference_year is not None else None,
                    "financial_stage": str(value_object.get("financialStage") or default_stage),
                    "amount_nature": str(value_object.get("amountNature") or "unavailable"),
                    "source_id": value_object.get("sourceId"),
                    "source_artifact": f"data_pipeline/export/municipal_finance/municipios/{code}/financeiro.json",
                    "source_artifact_sha256": input_hashes[code],
                    "territorial_lens": "municipal_executor",
                    "aggregation_rule": "municipal_contract_value",
                    "additive_across_municipal_executors": additive,
                    "context_relevance": relevance,
                    "selected_for_contextual_consumption": True,
                    "generic_finance_module_duplicate": False,
                    "nominal_cross_year_growth_claim_allowed": False,
                    "educational_result_causality_allowed": False,
                    "network_scope": "not_applicable_financial_executor",
                    "administrative_dependency_is_analytic_dimension": False,
                    "administrative_dependency_is_QA_dimension": True,
                    "distribution_municipality_count": None,
                    "distribution_minimum": None,
                    "distribution_median": None,
                    "distribution_maximum": None,
                }
            )
        committed = _nested(payload, "execution", "dcaEducation", "committed", "value")
        paid = _nested(payload, "execution", "dcaEducation", "paid", "value")
        year = _nested(payload, "execution", "dcaEducation", "referenceYear")
        paid_rate = safe_ratio(paid, committed, multiplier=100.0)
        rows.append(
            {
                "entity_scope": "municipality",
                "entity_id": code,
                "municipality_ibge_code": code,
                "municipality_name": name,
                "territory_name": name,
                "metric": "education_paid_to_committed_rate",
                "value": paid_rate,
                "value_status": "observed" if paid_rate is not None else "unavailable",
                "unit": "percent",
                "reference_year": int(year) if year is not None else None,
                "financial_stage": "calculated_indicator",
                "amount_nature": "local_calculation",
                "source_id": _nested(payload, "execution", "dcaEducation", "sourceId"),
                "source_artifact": f"data_pipeline/export/municipal_finance/municipios/{code}/financeiro.json",
                "source_artifact_sha256": input_hashes[code],
                "territorial_lens": "municipal_executor",
                "aggregation_rule": "paid / committed * 100; denominator_zero_returns_null",
                "additive_across_municipal_executors": False,
                "context_relevance": "execution_capacity_context",
                "selected_for_contextual_consumption": True,
                "generic_finance_module_duplicate": False,
                "nominal_cross_year_growth_claim_allowed": False,
                "educational_result_causality_allowed": False,
                "network_scope": "not_applicable_financial_executor",
                "administrative_dependency_is_analytic_dimension": False,
                "administrative_dependency_is_QA_dimension": True,
                "distribution_municipality_count": None,
                "distribution_minimum": None,
                "distribution_median": None,
                "distribution_maximum": None,
            }
        )

    municipal = pd.DataFrame(rows)
    region_rows: list[dict[str, Any]] = []
    for (metric, year), group in municipal.groupby(
        ["metric", "reference_year"], dropna=False, sort=True
    ):
        values = pd.to_numeric(group["value"], errors="coerce")
        first = group.iloc[0].to_dict()
        distribution = municipal_distribution(values)
        additive = _as_bool(first["additive_across_municipal_executors"])
        complete = int(values.notna().sum()) == len(municipality_names)
        if additive and complete:
            region_value = float(values.sum())
            status = "observed"
            aggregation = "sum_compatible_municipal_executor_values"
        else:
            region_value = None
            status = "municipal_distribution_only" if values.notna().any() else "unavailable"
            aggregation = "municipal_distribution_not_regional_rate_or_total"
        first.update(
            {
                "entity_scope": "region",
                "entity_id": REGION_ENTITY_ID,
                "municipality_ibge_code": None,
                "municipality_name": None,
                "territory_name": "Vale do Sinos",
                "value": region_value,
                "value_status": status,
                "source_artifact": "ten_canonical_municipal_finance_contracts",
                "source_artifact_sha256": hashlib.sha256(
                    json.dumps(input_hashes, sort_keys=True).encode("utf-8")
                ).hexdigest(),
                "aggregation_rule": aggregation,
                "distribution_municipality_count": distribution["municipality_count"],
                "distribution_minimum": distribution["minimum"],
                "distribution_median": distribution["median"],
                "distribution_maximum": distribution["maximum"],
            }
        )
        region_rows.append(first)
    panel = pd.DataFrame(
        [*municipal.to_dict("records"), *region_rows], columns=municipal.columns
    )
    key = ["entity_id", "metric", "reference_year"]
    if panel.duplicated(key).any():
        raise ValueError("Painel financeiro contextual contém chave duplicada")
    audit = {
        "municipalityCount": len(municipality_names),
        "inputHashes": input_hashes,
        "metricCount": int(panel["metric"].nunique()),
        "municipalRowCount": int(len(municipal)),
        "regionalRowCount": int(len(region_rows)),
        "nominalCrossYearGrowthClaims": 0,
        "genericFinanceModuleCreated": False,
        "financialStagesSeparated": True,
        "educationalResultCausalityUsed": False,
    }
    return _stable(panel, key), audit


def _offer_series_summary(
    panel: pd.DataFrame,
    *,
    entity_id: str,
    metric: str,
    stage: str,
    domain: str | None = None,
) -> dict[str, Any]:
    selected = panel[
        panel["entity_id"].eq(entity_id)
        & panel["metric"].eq(metric)
        & panel["stage"].eq(stage)
    ]
    if domain is not None:
        selected = selected[selected["offer_domain"].eq(domain)]
    if selected.empty:
        return {
            "initial_year": None,
            "final_year": None,
            "initial_value": None,
            "final_value": None,
            "absolute_change": None,
            "relative_change_percent": None,
            "availability_state": "unavailable",
        }
    row = selected.sort_values("year", kind="mergesort").iloc[-1]
    return {
        "initial_year": _json_safe(row["series_initial_year"]),
        "final_year": _json_safe(row["series_final_year"]),
        "initial_value": _json_safe(row["series_initial_value"]),
        "final_value": _json_safe(row["series_final_value"]),
        "absolute_change": _json_safe(row["series_absolute_change"]),
        "relative_change_percent": _json_safe(
            row["series_relative_change_percent"]
        ),
        "availability_state": str(row["availability_state"]),
        "source_artifact": str(row["source_artifact"]),
        "territorial_lens": str(row["territorial_lens"]),
    }


def _panel_value(
    panel: pd.DataFrame,
    *,
    entity_id: str,
    metric: str,
    year_column: str,
    year: int,
    value_column: str = "value",
) -> float | None:
    selected = panel[
        panel["entity_id"].eq(entity_id)
        & panel["metric"].eq(metric)
        & pd.to_numeric(panel[year_column], errors="coerce").eq(year)
    ]
    if len(selected) != 1:
        return None
    value = selected.iloc[0][value_column]
    if value is None or pd.isna(value):
        return None
    return float(value)


def _relative_position(value: float | None, median: float | None) -> str:
    if value is None or median is None:
        return "not_available"
    return "at_or_above_ten_municipality_median" if value >= median else "below_ten_municipality_median"


def build_coordination_matrix(
    *,
    mobility: pd.DataFrame,
    offer: pd.DataFrame,
    transport: pd.DataFrame,
    finance: pd.DataFrame,
    gar_root: Path,
    gbr_root: Path,
    gcr_root: Path,
    municipality_names: Mapping[str, str],
) -> pd.DataFrame:
    cohort = _read_csv(
        gar_root / "PAINEL_PRESSAO_MECANICA_COORTES_AUDITADO_V1_1.csv.gz"
    )
    trajectory = _read_csv(
        gar_root / "PAINEL_TRAJETORIA_OFICIAL_DESCRITIVA_V1_1.csv.gz"
    )
    eja_distribution = _read_csv(
        gbr_root / "PAINEL_EJA_DISTRIBUICAO_2022_V1_1.csv.gz"
    )
    rais = _read_csv(gcr_root / "PAINEL_RAIS_TRABALHO_JUVENIL_V1_1.csv.gz")

    municipal_inputs: dict[str, dict[str, Any]] = {}
    for code, name in municipality_names.items():
        mobility_row = mobility[
            mobility["entity_id"].eq(code) & mobility["stage"].eq("medio")
        ]
        if len(mobility_row) != 1:
            raise ValueError(f"Mobilidade do ensino médio ausente para {code}")
        mobility_rate = float(mobility_row.iloc[0]["outside_share_percent"])
        enrollment = _offer_series_summary(
            offer,
            entity_id=code,
            metric="located_enrollments",
            stage="medio",
            domain="general_offer",
        )
        schools = _offer_series_summary(
            offer,
            entity_id=code,
            metric="schools",
            stage="all",
            domain="general_offer",
        )
        classes = _offer_series_summary(
            offer,
            entity_id=code,
            metric="classes",
            stage="medio",
            domain="staffing_and_classes",
        )
        teachers = _offer_series_summary(
            offer,
            entity_id=code,
            metric="reported_teaching_units",
            stage="medio",
            domain="staffing_and_classes",
        )
        cohort_row = cohort[
            cohort["entity_scope"].eq("municipality")
            & cohort["municipality_ibge_code"].eq(code)
            & cohort["stage"].eq("medio")
            & pd.to_numeric(cohort["target_year"], errors="coerce").eq(2030)
        ]
        cohort_ratio = (
            float(cohort_row.iloc[0]["cohort_to_baseline_enrollment_ratio"])
            if len(cohort_row) == 1
            and str(cohort_row.iloc[0]["availability_state"]).startswith("AVAILABLE")
            else None
        )
        rural_enrollments = _offer_series_summary(
            offer,
            entity_id=code,
            metric="rural_enrollments",
            stage="all",
            domain="rural_offer",
        )
        rural_schools = _offer_series_summary(
            offer,
            entity_id=code,
            metric="rural_schools",
            stage="all",
            domain="rural_offer",
        )
        ept = _offer_series_summary(
            offer,
            entity_id=code,
            metric="located_technical_enrollments",
            stage="professional_technical",
            domain="ept_offer",
        )
        special = _offer_series_summary(
            offer,
            entity_id=code,
            metric="special_enrollments",
            stage="all",
            domain="special_education_aee",
        )
        aee = _offer_series_summary(
            offer,
            entity_id=code,
            metric="schools_offering_aee",
            stage="all",
            domain="special_education_aee",
        )
        pnate_beneficiaries = _panel_value(
            transport,
            entity_id=code,
            metric="pnate_beneficiary_students",
            year_column="exercise_year",
            year=2025,
        )
        pnate_authorized = _panel_value(
            transport,
            entity_id=code,
            metric="pnate_authorized_after_discount",
            year_column="exercise_year",
            year=2025,
        )
        finance_paid_rate = _panel_value(
            finance,
            entity_id=code,
            metric="education_paid_to_committed_rate",
            year_column="reference_year",
            year=2025,
        )
        mde_rate = _panel_value(
            finance,
            entity_id=code,
            metric="mde_applied_rate",
            year_column="reference_year",
            year=2025,
        )
        trajectory_rows = trajectory[
            trajectory["municipality_ibge_code"].eq(code)
            & trajectory["stage"].eq("medio")
            & pd.to_numeric(trajectory["year"], errors="coerce").eq(2022)
        ]
        trajectory_values = {
            str(row["metric"]): _json_safe(row["value"])
            for row in trajectory_rows.to_dict("records")
        }
        eja_rows = eja_distribution[
            eja_distribution["entity_scope"].eq("municipality")
            & eja_distribution["municipality_ibge_code"].eq(code)
        ]
        eja_values = {
            str(row["stage"]): {
                "resident_adult_public": _json_safe(row["resident_adult_public"]),
                "located_eja_enrollments": _json_safe(
                    row["school_location_eja_enrollments"]
                ),
                "public_regional_share_percent": _json_safe(
                    row["share_of_regional_public_percent"]
                ),
                "enrollment_regional_share_percent": _json_safe(
                    row["share_of_regional_enrollments_percent"]
                ),
            }
            for row in eja_rows.to_dict("records")
        }
        work_values: dict[str, dict[str, float | None]] = {}
        for age_group in ("15_17", "18_24"):
            selected = rais[
                rais["entity_scope"].eq("municipality")
                & rais["entity_id"].eq(code)
                & rais["dimension"].eq("total")
                & rais["age_group"].eq(age_group)
            ].sort_values("year", kind="mergesort")
            work_values[age_group] = {
                "initial": (
                    float(selected.iloc[0]["active_bonds"]) if not selected.empty else None
                ),
                "final": (
                    float(selected.iloc[-1]["active_bonds"]) if not selected.empty else None
                ),
                "absolute_change": (
                    float(selected.iloc[-1]["active_bonds"])
                    - float(selected.iloc[0]["active_bonds"])
                    if not selected.empty
                    else None
                ),
            }
        municipal_inputs[code] = {
            "municipality_name": name,
            "mobility_high_school_share_percent": mobility_rate,
            "high_school_enrollment": enrollment,
            "schools": schools,
            "high_school_classes": classes,
            "high_school_teaching_units": teachers,
            "mechanical_high_school_pressure_2030_ratio": cohort_ratio,
            "rural_enrollments": rural_enrollments,
            "rural_schools": rural_schools,
            "pnate_beneficiaries_2025": pnate_beneficiaries,
            "pnate_authorized_2025": pnate_authorized,
            "ept_enrollments": ept,
            "trajectory_high_school_2022": trajectory_values,
            "eja_distribution_2022": eja_values,
            "finance_paid_to_committed_rate_2025": finance_paid_rate,
            "mde_applied_rate_2025": mde_rate,
            "work_youth_by_age_group": work_values,
            "special_enrollments": special,
            "schools_offering_aee": aee,
        }

    def median(path: Sequence[str]) -> float | None:
        values: list[float] = []
        for payload in municipal_inputs.values():
            current: Any = payload
            for key in path:
                current = current.get(key) if isinstance(current, Mapping) else None
            if current is not None and not pd.isna(current):
                values.append(float(current))
        return float(pd.Series(values).median()) if values else None

    templates = [
        {
            "combination_id": "COORD_MOBILITY_OFFER_HIGH_SCHOOL",
            "input_paths": [
                ("mobility_high_school_share_percent",),
                ("high_school_enrollment", "absolute_change"),
            ],
            "regional_question": "Como a mobilidade do ensino médio varia junto da oferta localizada?",
            "planning_question": "Que mudanças de oferta e que informação de destino precisam ser acompanhadas em conjunto?",
            "monitoring_indicator": "participação fora no médio + matrículas localizadas no médio",
            "responsibility": "municípios, Estado e articulação regional",
            "period": "mobilidade 2022; oferta 2014-2025",
            "lenses": ["student_residence", "school_location"],
            "limit": "Universos distintos; não identifica destino nem causa da mobilidade.",
        },
        {
            "combination_id": "COORD_COHORT_OFFER_PRESSURE",
            "input_paths": [
                ("mechanical_high_school_pressure_2030_ratio",),
                ("high_school_enrollment", "absolute_change"),
            ],
            "regional_question": "Como a pressão mecânica das coortes se combina com a evolução observada da oferta?",
            "planning_question": "Quais indicadores devem disparar revisão de capacidade antes de 2030?",
            "monitoring_indicator": "razão mecânica 2030/base 2025 + matrículas, escolas, turmas e docências",
            "responsibility": "planejamento municipal e regime de colaboração",
            "period": "oferta 2014-2025; pressão mecânica 2030",
            "lenses": ["resident_population", "school_location"],
            "limit": "Pressão mecânica não é previsão, cobertura, demanda nem capacidade.",
        },
        {
            "combination_id": "COORD_RURAL_PNATE",
            "input_paths": [
                ("rural_enrollments", "final_value"),
                ("pnate_beneficiaries_2025",),
            ],
            "regional_question": "Como a oferta rural localizada e o PNATE aparecem nos dez municípios?",
            "planning_question": "Que informações de transporte, distância e execução faltam para planejar com segurança?",
            "monitoring_indicator": "escolas/matrículas rurais + beneficiários e autorização PNATE",
            "responsibility": "município executor, FNDE e coordenação estadual",
            "period": "oferta rural 2014-2025; PNATE 2024-2026",
            "lenses": ["rural_school_location", "municipal_executor"],
            "limit": "PNATE não mede deslocamento, distância, execução ou resultado educacional.",
        },
        {
            "combination_id": "COORD_EPT_MOBILITY",
            "input_paths": [
                ("ept_enrollments", "final_value"),
                ("mobility_high_school_share_percent",),
            ],
            "regional_question": "Como a concentração da EPT e a mobilidade educacional coexistem no território?",
            "planning_question": "Que evidência de destino e modalidade é necessária antes de discutir cooperação de oferta?",
            "monitoring_indicator": "matrículas EPT localizadas + mobilidade por residência",
            "responsibility": "redes ofertantes e articulação intermunicipal/estadual",
            "period": "mobilidade 2022; EPT 2023-2025",
            "lenses": ["school_location", "student_residence"],
            "limit": "Zero localizado não prova ausência de acesso; não há destino nem modalidade na mobilidade.",
        },
        {
            "combination_id": "COORD_TRAJECTORY_MOBILITY",
            "input_paths": [
                ("mobility_high_school_share_percent",),
                ("trajectory_high_school_2022", "approval_rate_percent"),
            ],
            "regional_question": "Como considerar mobilidade ao interpretar a trajetória escolar localizada?",
            "planning_question": "Que composição territorial deve acompanhar a leitura municipal dos indicadores?",
            "monitoring_indicator": "mobilidade 2022 + taxas oficiais municipais do ensino médio",
            "responsibility": "gestão municipal e estadual com leitura de universos",
            "period": "2022",
            "lenses": ["student_residence", "school_location"],
            "limit": "As fontes não observam as mesmas pessoas; nenhuma associação é causal.",
        },
        {
            "combination_id": "COORD_EJA_ADULT_SCHOOLING",
            "input_paths": [
                ("eja_distribution_2022", "high_school", "resident_adult_public"),
                ("eja_distribution_2022", "high_school", "located_eja_enrollments"),
            ],
            "regional_question": "Como o público adulto residente e a EJA localizada se distribuem entre municípios?",
            "planning_question": "Onde a distribuição, sem virar taxa de cobertura, pede coordenação da oferta?",
            "monitoring_indicator": "distribuição do público adulto + matrículas EJA por etapa",
            "responsibility": "municípios, Estado e pactuação da EJA",
            "period": "2022; histórico EJA 2014-2025",
            "lenses": ["resident_population", "school_location"],
            "limit": "Distribuições por etapa não são taxa de atendimento, acesso ou capacidade.",
        },
        {
            "combination_id": "COORD_FINANCE_COHORT_PRESSURE",
            "input_paths": [
                ("mechanical_high_school_pressure_2030_ratio",),
                ("finance_paid_to_committed_rate_2025",),
            ],
            "regional_question": "Quais condições financeiras acompanhar junto das pressões mecânicas observadas?",
            "planning_question": "Que revisão de capacidade e pactuação deve ser disparada por indicadores separados?",
            "monitoring_indicator": "pressão mecânica + execução educacional + MDE",
            "responsibility": "gestão fiscal/educacional municipal e controle social",
            "period": "finanças 2025/2026; pressão 2030",
            "lenses": ["municipal_executor", "resident_population", "school_location"],
            "limit": "Gasto, execução e financiamento não causam nem medem resultado educacional.",
        },
        {
            "combination_id": "COORD_WORK_EPT_AGE_GROUPS",
            "input_paths": [
                ("work_youth_by_age_group", "15_17", "absolute_change"),
                ("work_youth_by_age_group", "18_24", "absolute_change"),
            ],
            "regional_question": "Como transformações do trabalho juvenil por idade coexistem com a oferta EPT?",
            "planning_question": "Que sinais por faixa etária merecem monitoramento sem inferir demanda futura?",
            "monitoring_indicator": "RAIS/Caged separados em 15-17 e 18-24 + EPT localizada",
            "responsibility": "educação, trabalho e articulação regional",
            "period": "RAIS 2019-2025; EPT 2023-2025",
            "lenses": ["workplace", "school_location"],
            "limit": "Estabelecimentos e escolas não identificam as mesmas pessoas; sinal não é demanda.",
        },
        {
            "combination_id": "COORD_SPECIAL_AEE_TERRITORY",
            "input_paths": [
                ("special_enrollments", "final_value"),
                ("schools_offering_aee", "final_value"),
            ],
            "regional_question": "Como matrículas de educação especial e oferta de AEE se distribuem territorialmente?",
            "planning_question": "Que condições locais e articulações precisam ser acompanhadas sem inferir cobertura?",
            "monitoring_indicator": "matrículas especiais + escolas que declaram AEE",
            "responsibility": "redes educacionais e coordenação intersetorial",
            "period": "2014-2025",
            "lenses": ["school_location"],
            "limit": "Contagens localizadas não são prevalência, cobertura ou acesso da população residente.",
        },
    ]

    rows: list[dict[str, Any]] = []
    for template in templates:
        medians = [median(path) for path in template["input_paths"]]
        municipal_values_for_distribution: list[dict[str, Any]] = []
        for code, payload in municipal_inputs.items():
            values: list[float | None] = []
            for path in template["input_paths"]:
                current: Any = payload
                for key in path:
                    current = current.get(key) if isinstance(current, Mapping) else None
                values.append(None if current is None or pd.isna(current) else float(current))
            positions = [
                _relative_position(value, reference)
                for value, reference in zip(values, medians, strict=True)
            ]
            profile = (
                "not_available"
                if all(position == "not_available" for position in positions)
                else "same_side_of_municipal_medians"
                if len(set(position for position in positions if position != "not_available")) == 1
                else "mixed_relative_position"
            )
            input_payload = {
                "values": values,
                "ten_municipality_medians": medians,
                "relative_positions": positions,
                "source_payload": payload,
            }
            municipal_values_for_distribution.append(
                {"municipality_ibge_code": code, "values": values}
            )
            rows.append(
                {
                    "combination_id": template["combination_id"],
                    "entity_scope": "municipality",
                    "entity_id": code,
                    "municipality_ibge_code": code,
                    "municipality_name": payload["municipality_name"],
                    "regional_question": template["regional_question"],
                    "municipal_question": template["planning_question"],
                    "regional_fact": "See regional distribution row; no municipal mean is called a Vale rate.",
                    "municipal_fact": (
                        f"Internal seed for {payload['municipality_name']}: transparent inputs {values}; "
                        f"positions {positions}."
                    ),
                    "input_metrics": json.dumps(
                        input_payload,
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    ),
                    "municipal_distribution": None,
                    "comparison_method": (
                        "transparent comparison with the ten-municipality median for each input; no combined score"
                    ),
                    "profile_state": profile,
                    "combined_score": None,
                    "score_used": False,
                    "good_bad_classification_used": False,
                    "source": "frozen Job 2/5G-A-R/5G-B-R/5G-C-R panels and canonical finance/PNATE",
                    "period": template["period"],
                    "territorial_lenses": json.dumps(template["lenses"], ensure_ascii=False),
                    "network_scope": "total_all_dependencies",
                    "monitoring_indicator": template["monitoring_indicator"],
                    "planning_question": template["planning_question"],
                    "institutional_responsibility": template["responsibility"],
                    "allowed_claims": json.dumps(
                        [
                            "describe each observed input and its declared lens",
                            "formulate a specific planning question",
                            "compare municipal distribution without evaluation",
                        ],
                        ensure_ascii=False,
                    ),
                    "forbidden_claims": json.dumps(
                        [
                            "causal effect",
                            "automatic recommendation to open or close school, course, class or route",
                            "good or bad municipality classification",
                            "origin-destination corridor without official source",
                        ],
                        ensure_ascii=False,
                    ),
                    "interpretation_limit": template["limit"],
                    "external_judgment_required": True,
                }
            )
        distributions = []
        for index, reference in enumerate(medians):
            values = [
                item["values"][index]
                for item in municipal_values_for_distribution
                if item["values"][index] is not None
            ]
            distributions.append(
                {
                    "inputIndex": index,
                    "median": reference,
                    "minimum": min(values) if values else None,
                    "maximum": max(values) if values else None,
                    "municipalityCount": len(values),
                }
            )
        rows.append(
            {
                "combination_id": template["combination_id"],
                "entity_scope": "region",
                "entity_id": REGION_ENTITY_ID,
                "municipality_ibge_code": None,
                "municipality_name": None,
                "regional_question": template["regional_question"],
                "municipal_question": template["planning_question"],
                "regional_fact": (
                    f"Vale do Sinos: distribution of ten municipalities for {template['combination_id']}; "
                    f"inputs summarized as {distributions}."
                ),
                "municipal_fact": "All ten municipal rows are retained; Nova Santa Rita is reconstructed separately.",
                "input_metrics": json.dumps(
                    {"regional_distribution": distributions},
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ),
                "municipal_distribution": json.dumps(
                    municipal_values_for_distribution,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ),
                "comparison_method": "ten-municipality distribution; not a Vale rate or score",
                "profile_state": "regional_distribution_summary",
                "combined_score": None,
                "score_used": False,
                "good_bad_classification_used": False,
                "source": "frozen Job 2/5G-A-R/5G-B-R/5G-C-R panels and canonical finance/PNATE",
                "period": template["period"],
                "territorial_lenses": json.dumps(template["lenses"], ensure_ascii=False),
                "network_scope": "total_all_dependencies",
                "monitoring_indicator": template["monitoring_indicator"],
                "planning_question": template["planning_question"],
                "institutional_responsibility": template["responsibility"],
                "allowed_claims": json.dumps(
                    [
                        "describe the ten-municipality distribution",
                        "state compatible regional sums or recomposed rates only where separately materialized",
                    ],
                    ensure_ascii=False,
                ),
                "forbidden_claims": json.dumps(
                    [
                        "call the municipal median a Vale rate",
                        "causal effect",
                        "automatic recommendation",
                        "good or bad classification",
                    ],
                    ensure_ascii=False,
                ),
                "interpretation_limit": template["limit"],
                "external_judgment_required": True,
            }
        )
    result = pd.DataFrame(rows)
    key = ["combination_id", "entity_id"]
    if result.duplicated(key).any():
        raise ValueError("Matriz de coordenação contém chave duplicada")
    if result["score_used"].any() or result["combined_score"].notna().any():
        raise ValueError("Matriz de coordenação usou score combinado")
    return _stable(result, key)


def build_complete_fact_catalog(
    *,
    corrected_gcr: pd.DataFrame,
    mobility: pd.DataFrame,
    offer: pd.DataFrame,
    transport: pd.DataFrame,
    finance: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    def add(row: dict[str, Any]) -> None:
        rows.append(row)

    for source_row in corrected_gcr.to_dict("records"):
        add(
            {
                "fact_id": source_row["fact_id"],
                "domain": "work_and_ept_preflight_correction",
                "entity_scope": source_row["entity_scope"],
                "entity_id": source_row["entity_id"],
                "municipality_name": "Nova Santa Rita",
                "metric": source_row["measure"],
                "dimension": source_row["dimension_code"],
                "age_group": source_row["age_group"],
                "initial_year": source_row["initial_year"],
                "final_year": source_row["final_year"],
                "initial_value": source_row["initial_value"],
                "final_value": source_row["final_value"],
                "absolute_change": source_row["absolute_change"],
                "relative_change_percent": source_row["relative_change_percent"],
                "current_value": source_row["final_value"],
                "numerator": None,
                "denominator": None,
                "unit": source_row["stock_or_flow"],
                "source": source_row["source"],
                "source_artifact": source_row["origin_artifact"],
                "period": f"{source_row['initial_year']}-{source_row['final_year']}",
                "territorial_lens": source_row["territorial_lens"],
                "network_scope": "not_applicable",
                "stock_or_flow": source_row["stock_or_flow"],
                "population_scope": source_row["population_scope"],
                "aggregation_rule": "canonical_origin_aggregate",
                "value_status": "observed",
                "materiality_state": (
                    "MATERIAL_CANDIDATE"
                    if _as_bool(source_row["maximum_exploration_eligible"])
                    else "RETAINED_NOT_MAXIMUM_ELIGIBLE"
                ),
                "visual_aggregation_eligible": source_row[
                    "visual_aggregation_eligible"
                ],
                "maximum_exploration_eligible": source_row[
                    "maximum_exploration_eligible"
                ],
                "selected_compact_compatibility": source_row[
                    "selected_for_synthesis"
                ],
                "numeric_direction": source_row["numeric_direction"],
                "direction_semantics": source_row["direction_semantics"],
                "allowed_claims": "numeric sign and observed magnitude at declared grain",
                "forbidden_claims": "improvement/worsening; future demand; causal effect",
                "origin_grain_key": source_row["origin_grain_key"],
                "external_judgment_required": True,
            }
        )

    for source_row in mobility.to_dict("records"):
        fact_id = "|".join(
            [
                "MOBILITY_OUTSIDE_SHARE_2022",
                str(source_row["entity_scope"]),
                str(source_row["entity_id"]),
                str(source_row["stage"]),
            ]
        )
        add(
            {
                "fact_id": fact_id,
                "domain": "educational_mobility",
                "entity_scope": source_row["entity_scope"],
                "entity_id": source_row["entity_id"],
                "municipality_name": source_row.get("municipality_name"),
                "metric": "outside_municipality_share_percent",
                "dimension": source_row["stage"],
                "age_group": "not_applicable",
                "initial_year": 2022,
                "final_year": 2022,
                "initial_value": source_row["outside_share_percent"],
                "final_value": source_row["outside_share_percent"],
                "absolute_change": None,
                "relative_change_percent": None,
                "current_value": source_row["outside_share_percent"],
                "numerator": source_row["numerator"],
                "denominator": source_row["denominator"],
                "unit": "percent",
                "source": source_row["source"],
                "source_artifact": f"SIDRA table {source_row['source_table']}",
                "period": "2022",
                "territorial_lens": "student_residence",
                "network_scope": "not_applicable",
                "stock_or_flow": "census_stock",
                "population_scope": source_row["population_scope"],
                "aggregation_rule": source_row["aggregation_method"],
                "value_status": source_row["value_status"],
                "materiality_state": (
                    "MATERIAL_CANDIDATE"
                    if int(source_row["numerator"]) >= 20
                    else "SMALL_VOLUME_CONTEXT_ONLY"
                ),
                "visual_aggregation_eligible": int(source_row["numerator"]) >= 20,
                "maximum_exploration_eligible": int(source_row["numerator"]) >= 20,
                "selected_compact_compatibility": False,
                "numeric_direction": "not_applicable_cross_section",
                "direction_semantics": "cross-sectional level, not gain/loss",
                "allowed_claims": "share of residents studying outside at same official universe",
                "forbidden_claims": "destination corridor; access; transport use; causality",
                "origin_grain_key": f"{source_row['entity_id']}|{source_row['stage']}|2022",
                "external_judgment_required": True,
            }
        )

    endpoint_keys = [
        "entity_scope",
        "entity_id",
        "municipality_name",
        "offer_domain",
        "stage",
        "metric",
        "source_artifact",
        "territorial_lens",
        "network_scope",
        "population_scope",
        "unit",
        "aggregation_rule",
        "series_initial_year",
        "series_final_year",
        "series_initial_value",
        "series_final_value",
        "series_absolute_change",
        "series_relative_change_percent",
        "series_change_status",
        "availability_state",
    ]
    endpoints = _offer_endpoints(offer)[endpoint_keys].drop_duplicates()
    for source_row in endpoints.to_dict("records"):
        fact_id = "|".join(
            [
                "OFFER",
                str(source_row["offer_domain"]),
                str(source_row["entity_id"]),
                str(source_row["stage"]),
                str(source_row["metric"]),
                str(source_row["series_initial_year"]),
                str(source_row["series_final_year"]),
            ]
        )
        change = source_row["series_absolute_change"]
        unit = str(source_row["unit"])
        threshold = 2.0 if unit == "percent" else 20.0
        material = change is not None and not pd.isna(change) and abs(float(change)) >= threshold
        zero_ept = (
            source_row["offer_domain"] == "ept_offer"
            and source_row["series_final_value"] is not None
            and float(source_row["series_final_value"]) == 0
        )
        add(
            {
                "fact_id": fact_id,
                "domain": "territorial_offer",
                "entity_scope": source_row["entity_scope"],
                "entity_id": source_row["entity_id"],
                "municipality_name": source_row.get("municipality_name"),
                "metric": source_row["metric"],
                "dimension": source_row["stage"],
                "age_group": "not_applicable",
                "initial_year": source_row["series_initial_year"],
                "final_year": source_row["series_final_year"],
                "initial_value": source_row["series_initial_value"],
                "final_value": source_row["series_final_value"],
                "absolute_change": change,
                "relative_change_percent": source_row[
                    "series_relative_change_percent"
                ],
                "current_value": source_row["series_final_value"],
                "numerator": None,
                "denominator": None,
                "unit": unit,
                "source": "canonical frozen educational panels",
                "source_artifact": source_row["source_artifact"],
                "period": f"{source_row['series_initial_year']}-{source_row['series_final_year']}",
                "territorial_lens": source_row["territorial_lens"],
                "network_scope": source_row["network_scope"],
                "stock_or_flow": "located_offer_stock",
                "population_scope": source_row["population_scope"],
                "aggregation_rule": source_row["aggregation_rule"],
                "value_status": source_row["availability_state"],
                "materiality_state": (
                    "MATERIAL_CANDIDATE"
                    if material or zero_ept
                    else "COMPLETE_CATALOG_CONTEXT"
                ),
                "visual_aggregation_eligible": bool(material or zero_ept),
                "maximum_exploration_eligible": bool(material or zero_ept),
                "selected_compact_compatibility": False,
                "numeric_direction": _sign_direction(change),
                "direction_semantics": "sign of observed series change, never improvement/worsening",
                "allowed_claims": "observed located offer and change at declared grain",
                "forbidden_claims": "access or coverage from located enrollment alone; causality",
                "origin_grain_key": (
                    f"{source_row['entity_id']}|{source_row['offer_domain']}|"
                    f"{source_row['stage']}|{source_row['metric']}"
                ),
                "external_judgment_required": True,
            }
        )

    for source_row in transport.to_dict("records"):
        fact_id = "|".join(
            [
                "PNATE",
                str(source_row["entity_id"]),
                str(source_row["exercise_year"]),
                str(source_row["metric"]),
            ]
        )
        value = source_row["value"]
        observed = value is not None and not pd.isna(value)
        material = observed and abs(float(value)) >= (
            20.0 if source_row["unit"] == "students" else 0.01
        )
        add(
            {
                "fact_id": fact_id,
                "domain": "transport_and_pnate",
                "entity_scope": source_row["entity_scope"],
                "entity_id": source_row["entity_id"],
                "municipality_name": source_row.get("municipality_name"),
                "metric": source_row["metric"],
                "dimension": source_row["financial_stage"],
                "age_group": "not_applicable",
                "initial_year": source_row["exercise_year"],
                "final_year": source_row["exercise_year"],
                "initial_value": value,
                "final_value": value,
                "absolute_change": None,
                "relative_change_percent": None,
                "current_value": value,
                "numerator": None,
                "denominator": None,
                "unit": source_row["unit"],
                "source": source_row["source"],
                "source_artifact": source_row["source_file"],
                "period": str(source_row["exercise_year"]),
                "territorial_lens": "municipal_executor",
                "network_scope": "not_applicable",
                "stock_or_flow": source_row["financial_stage"],
                "population_scope": "pnate_program_record",
                "aggregation_rule": source_row["aggregation_rule"],
                "value_status": source_row["value_status"],
                "materiality_state": (
                    "MATERIAL_CANDIDATE" if material else "UNAVAILABLE_OR_CONTEXT_ONLY"
                ),
                "visual_aggregation_eligible": material,
                "maximum_exploration_eligible": material,
                "selected_compact_compatibility": False,
                "numeric_direction": "not_applicable_cross_section",
                "direction_semantics": "exercise level, not gain/loss",
                "allowed_claims": "program beneficiary/resource context at executor grain",
                "forbidden_claims": "mobility corridor; transport usage; execution when unavailable; causal effect",
                "origin_grain_key": f"{source_row['entity_id']}|{source_row['exercise_year']}|{source_row['metric']}",
                "external_judgment_required": True,
            }
        )

    for source_row in finance.to_dict("records"):
        fact_id = "|".join(
            [
                "FINANCE",
                str(source_row["entity_id"]),
                str(source_row["reference_year"]),
                str(source_row["metric"]),
            ]
        )
        value = source_row["value"]
        observed = value is not None and not pd.isna(value)
        add(
            {
                "fact_id": fact_id,
                "domain": "contextual_finance",
                "entity_scope": source_row["entity_scope"],
                "entity_id": source_row["entity_id"],
                "municipality_name": source_row.get("municipality_name"),
                "metric": source_row["metric"],
                "dimension": source_row["financial_stage"],
                "age_group": "not_applicable",
                "initial_year": source_row["reference_year"],
                "final_year": source_row["reference_year"],
                "initial_value": value,
                "final_value": value,
                "absolute_change": None,
                "relative_change_percent": None,
                "current_value": value,
                "numerator": None,
                "denominator": None,
                "unit": source_row["unit"],
                "source": source_row["source_id"],
                "source_artifact": source_row["source_artifact"],
                "period": str(source_row["reference_year"]),
                "territorial_lens": "municipal_executor",
                "network_scope": "not_applicable_financial_executor",
                "stock_or_flow": source_row["financial_stage"],
                "population_scope": source_row["context_relevance"],
                "aggregation_rule": source_row["aggregation_rule"],
                "value_status": source_row["value_status"],
                "materiality_state": (
                    "SELECTABLE_CONTEXT" if observed else "UNAVAILABLE_CONTEXT"
                ),
                "visual_aggregation_eligible": observed,
                "maximum_exploration_eligible": observed,
                "selected_compact_compatibility": False,
                "numeric_direction": "not_applicable_cross_section",
                "direction_semantics": "financial stage level, not gain/loss or result quality",
                "allowed_claims": "nominal financial context with explicit stage and year",
                "forbidden_claims": "real growth across years; educational causal effect; mixing stages",
                "origin_grain_key": f"{source_row['entity_id']}|{source_row['reference_year']}|{source_row['metric']}",
                "external_judgment_required": True,
            }
        )

    catalog = pd.DataFrame(rows)
    if catalog["fact_id"].duplicated().any():
        duplicates = catalog.loc[
            catalog["fact_id"].duplicated(False), "fact_id"
        ].head(10)
        raise ValueError(f"Catálogo completo contém fact_id duplicado: {duplicates.tolist()}")
    catalog["physical_order_used"] = False
    catalog["alphabetical_order_used"] = False
    catalog["code_order_used"] = False
    catalog["opaque_score_used"] = False
    return _stable(catalog, ["domain", "entity_scope", "entity_id", "fact_id"])


PNE_LINKS = {
    "COORD_MOBILITY_OFFER_HIGH_SCHOOL": ("PNE_3", "PME_transicao_ensino_medio"),
    "COORD_COHORT_OFFER_PRESSURE": ("PNE_1|PNE_2|PNE_3", "PME_planejamento_da_oferta"),
    "COORD_RURAL_PNATE": ("PNE_7", "PME_transporte_e_territorio"),
    "COORD_EPT_MOBILITY": ("PNE_11", "PME_EPT_e_regime_de_colaboracao"),
    "COORD_TRAJECTORY_MOBILITY": ("PNE_3|PNE_7", "PME_trajetoria_e_territorio"),
    "COORD_EJA_ADULT_SCHOOLING": ("PNE_9|PNE_10", "PME_EJA"),
    "COORD_FINANCE_COHORT_PRESSURE": ("PNE_20", "PME_financiamento_e_capacidade"),
    "COORD_WORK_EPT_AGE_GROUPS": ("PNE_8|PNE_10|PNE_11", "PME_trabalho_e_formacao"),
    "COORD_SPECIAL_AEE_TERRITORY": ("PNE_4", "PME_educacao_especial_AEE"),
}

MACROBLOCKS = {
    "COORD_MOBILITY_OFFER_HIGH_SCHOOL": "MOBILIDADE_E_OFERTA",
    "COORD_COHORT_OFFER_PRESSURE": "COORTES_E_ORGANIZACAO_DA_OFERTA",
    "COORD_RURAL_PNATE": "RURALIDADE_TRANSPORTE_E_PNATE",
    "COORD_EPT_MOBILITY": "EPT_E_COORDENACAO_TERRITORIAL",
    "COORD_TRAJECTORY_MOBILITY": "TRAJETORIA_E_MOBILIDADE",
    "COORD_EJA_ADULT_SCHOOLING": "EJA_ESCOLARIDADE_E_TERRITORIO",
    "COORD_FINANCE_COHORT_PRESSURE": "FINANCAS_E_CONDICOES_DA_OFERTA",
    "COORD_WORK_EPT_AGE_GROUPS": "TRABALHO_JUVENIL_E_FORMACAO",
    "COORD_SPECIAL_AEE_TERRITORY": "EDUCACAO_ESPECIAL_AEE_E_TERRITORIO",
}


def build_pne_pme_links(coordination: pd.DataFrame) -> pd.DataFrame:
    """Materializa vínculos como metadados, sem recalcular contrato legal."""

    rows: list[dict[str, Any]] = []
    for combination_id in sorted(coordination["combination_id"].unique()):
        pne, pme = PNE_LINKS[combination_id]
        regional = coordination[
            coordination["combination_id"].eq(combination_id)
            & coordination["entity_scope"].eq("region")
        ].iloc[0]
        rows.append(
            {
                "combination_id": combination_id,
                "macroblock_id": MACROBLOCKS[combination_id],
                "pne_goal_links": pne,
                "pme_link": pme,
                "link_type": "internal_editorial_metadata",
                "monitoring_indicator": regional["monitoring_indicator"],
                "period": regional["period"],
                "source": regional["source"],
                "territorial_lenses": regional["territorial_lenses"],
                "contract_recalculated": False,
                "indicator_definition_changed": False,
                "public_narrative_authorized": False,
                "standalone_visual_module": False,
                "external_judgment_required": True,
                "limitation": regional["interpretation_limit"],
            }
        )
    return pd.DataFrame(rows).sort_values("combination_id", kind="mergesort").reset_index(drop=True)


def build_story_catalog(
    *,
    coordination: pd.DataFrame,
    municipality_names: Mapping[str, str],
    selected_municipality_id: str,
) -> dict[str, Any]:
    """Forma o corpus máximo: uma variante regional e dez municipais por direção."""

    if selected_municipality_id not in municipality_names:
        raise ValueError("Município selecionado não pertence ao Vale do Sinos")
    stories: list[dict[str, Any]] = []
    for row in coordination.to_dict("records"):
        combination_id = str(row["combination_id"])
        entity_id = str(row["entity_id"])
        profile = str(row["profile_state"])
        availability = "UNAVAILABLE" if profile == "not_available" else "AVAILABLE_INTERNAL"
        materiality = (
            "POTENTIAL_MATERIAL_STORY"
            if availability == "AVAILABLE_INTERNAL"
            else "RETAINED_WITH_GAP"
        )
        pne, pme = PNE_LINKS[combination_id]
        entity_role = (
            "vale_do_sinos"
            if row["entity_scope"] == "region"
            else "nova_santa_rita"
            if entity_id == NSR_CODE
            else "selected_municipality"
            if entity_id == selected_municipality_id
            else "municipal_corpus"
        )
        stories.append(
            {
                "story_id": f"STORY|{combination_id}|{entity_id}",
                "macroblock_id": MACROBLOCKS[combination_id],
                "direction_id": combination_id,
                "entity_scope": row["entity_scope"],
                "entity_id": entity_id,
                "municipality_name": _json_safe(row.get("municipality_name")),
                "scale_role": entity_role,
                "regional_question": row["regional_question"],
                "municipal_question": row["municipal_question"],
                "regional_fact": row["regional_fact"],
                "municipal_fact": row["municipal_fact"],
                "municipal_distribution": _json_safe(row.get("municipal_distribution")),
                "comparison_method": row["comparison_method"],
                "source": row["source"],
                "period": row["period"],
                "territorial_lens": row["territorial_lenses"],
                "network_scope": row["network_scope"],
                "population_or_stage": row["monitoring_indicator"],
                "monitoring_indicator": row["monitoring_indicator"],
                "planning_question": row["planning_question"],
                "institutional_responsibility": row["institutional_responsibility"],
                "visual_role": "maximum_prototype_internal_candidate",
                "availability_state": availability,
                "materiality_state": materiality,
                "allowed_claims": row["allowed_claims"],
                "forbidden_claims": row["forbidden_claims"],
                "PNE_PME_links": f"{pne}|{pme}",
                "internal_evidence_state": "MATERIALIZED_AND_TRACEABLE",
                "manager_review_state": "PENDING_EXTERNAL_JUDGMENT",
                "internal_title_seed": f"{MACROBLOCKS[combination_id]} — {entity_id}",
                "public_narrative": None,
                "public_narrative_authorized": False,
                "fixed_card_cap_applied": False,
                "automatic_selection": False,
                "external_judgment_required": True,
            }
        )
    required = {
        "story_id",
        "macroblock_id",
        "direction_id",
        "regional_question",
        "municipal_question",
        "regional_fact",
        "municipal_fact",
        "municipal_distribution",
        "comparison_method",
        "source",
        "period",
        "territorial_lens",
        "network_scope",
        "population_or_stage",
        "monitoring_indicator",
        "planning_question",
        "institutional_responsibility",
        "visual_role",
        "availability_state",
        "materiality_state",
        "allowed_claims",
        "forbidden_claims",
        "PNE_PME_links",
        "internal_evidence_state",
        "manager_review_state",
    }
    if any(not required.issubset(story) for story in stories):
        raise ValueError("Catálogo de histórias não cumpre o contrato mínimo")
    if len({story["story_id"] for story in stories}) != len(stories):
        raise ValueError("story_id duplicado")
    return {
        "schemaVersion": "catalogo-maximo-historias-job5gd-v1",
        "catalogRole": "internal_editorial_input_for_external_judgment",
        "publicNarrativeFinal": False,
        "fixedCardCap": None,
        "selectionCompactCompatibilityIsCeiling": False,
        "storyCount": len(stories),
        "directionCount": len({story["direction_id"] for story in stories}),
        "municipalityCount": len(municipality_names),
        "selectedMunicipalityId": selected_municipality_id,
        "novaSantaRitaId": NSR_CODE,
        "stories": sorted(stories, key=lambda item: item["story_id"]),
    }


def build_availability_materiality(
    *, coordination: pd.DataFrame, stories: Mapping[str, Any]
) -> pd.DataFrame:
    story_rows = pd.DataFrame(stories["stories"])
    rows: list[dict[str, Any]] = []
    for combination_id, group in coordination.groupby("combination_id", sort=True):
        municipal = group[group["entity_scope"].eq("municipality")]
        related_stories = story_rows[story_rows["direction_id"].eq(combination_id)]
        available = ~municipal["profile_state"].eq("not_available")
        rows.append(
            {
                "direction_id": combination_id,
                "macroblock_id": MACROBLOCKS[str(combination_id)],
                "municipality_expected_count": 10,
                "municipality_available_count": int(available.sum()),
                "regional_distribution_available": bool(
                    group["entity_scope"].eq("region").any()
                ),
                "nova_santa_rita_available": bool(
                    municipal.loc[municipal["entity_id"].eq(NSR_CODE), "profile_state"]
                    .ne("not_available")
                    .any()
                ),
                "story_count": int(len(related_stories)),
                "material_story_count": int(
                    related_stories["materiality_state"].eq("POTENTIAL_MATERIAL_STORY").sum()
                ),
                "availability_state": (
                    "AVAILABLE_ALL_SCALES" if int(available.sum()) == 10 else "AVAILABLE_WITH_GAPS"
                ),
                "materiality_method": "transparent input availability, magnitude and planning relevance; no combined score",
                "fixed_card_cap_applied": False,
                "opaque_score_used": False,
                "external_judgment_required": True,
                "interpretation_limit": group.iloc[0]["interpretation_limit"],
            }
        )
    return pd.DataFrame(rows).sort_values("direction_id", kind="mergesort").reset_index(drop=True)


def build_c1_c12_matrix(availability: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    partial_criteria = {
        "COORD_MOBILITY_OFFER_HIGH_SCHOOL": {"C2", "C5"},
        "COORD_RURAL_PNATE": {"C2", "C5", "C8"},
        "COORD_EPT_MOBILITY": {"C2", "C5"},
        "COORD_FINANCE_COHORT_PRESSURE": {"C2", "C5"},
        "COORD_WORK_EPT_AGE_GROUPS": {"C2", "C5"},
    }
    for row in availability.to_dict("records"):
        direction_id = str(row["direction_id"])
        for criterion_id, criterion in CRITERIA:
            status = (
                "PARTIAL"
                if criterion_id in partial_criteria.get(direction_id, set())
                or row["availability_state"] == "AVAILABLE_WITH_GAPS"
                else "SUPPORTED"
            )
            rows.append(
                {
                    "analysis_id": direction_id,
                    "criterion_id": criterion_id,
                    "criterion": criterion,
                    "criterion_status": status,
                    "evidence": (
                        f"{row['municipality_available_count']}/10 municípios; "
                        f"{row['story_count']} variantes; {row['interpretation_limit']}"
                    ),
                    "score": None,
                    "automatic_approval": False,
                    "manager_review_state": "PENDING_EXTERNAL_JUDGMENT",
                    "public_consumption_authorized": False,
                }
            )
    result = pd.DataFrame(rows)
    if not result.groupby("analysis_id").size().eq(12).all():
        raise ValueError("Matriz C1–C12 incompleta")
    if result["score"].notna().any() or result["automatic_approval"].any():
        raise ValueError("Matriz C1–C12 não pode pontuar ou aprovar")
    return _stable(result, ["analysis_id", "criterion_id"])


def build_qa_matrix(
    *,
    corrected: pd.DataFrame,
    correction: Mapping[str, Any],
    mobility: pd.DataFrame,
    mobility_audit: Mapping[str, Any],
    offer: pd.DataFrame,
    transport: pd.DataFrame,
    transport_audit: Mapping[str, Any],
    finance: pd.DataFrame,
    coordination: pd.DataFrame,
    facts: pd.DataFrame,
    stories: Mapping[str, Any],
    municipality_names: Mapping[str, str],
) -> pd.DataFrame:
    """Registra verificações executáveis e limites honestos do lote."""

    caged = corrected[corrected["universe"].str.startswith("CAGED_")]
    municipal_ids = set(municipality_names)
    mobility_municipal = mobility[mobility["entity_scope"].eq("municipality")]
    offer_municipal = offer[offer["entity_scope"].eq("municipality")]
    story_frame = pd.DataFrame(stories["stories"])

    controls: list[tuple[str, str, bool, str, str]] = [
        ("QA01", "IBGE textual de sete dígitos", all(IBGE_CODE_PATTERN.fullmatch(code) for code in municipal_ids), "PASS", ",".join(sorted(municipal_ids))),
        ("QA02", "exatamente dez municípios", len(municipal_ids) == 10, "PASS", str(len(municipal_ids))),
        ("QA03", "Nova Santa Rita canônica", municipality_names.get(NSR_CODE) == "Nova Santa Rita", "PASS", NSR_CODE),
        ("QA04", "fact_id V2 único", not corrected["fact_id"].duplicated().any(), "PASS", f"{len(corrected)}/{corrected['fact_id'].nunique()}"),
        ("QA05", "age_group Caged não nulo", caged["age_group"].notna().all(), "PASS", ",".join(sorted(caged["age_group"].unique()))),
        ("QA06", "faixas 15–17 e 18–24 separadas", set(caged["age_group"]) == {"15_17", "18_24"}, "PASS", str(correction["maximumExplorationEligibleByAgeGroup"])),
        ("QA07", "paridade numérica da correção", bool(correction["numericAndSelectionContentPreserved"]), "PASS", str(correction["sourceCompatibilityMultisetSha256"])),
        ("QA08", "fato resolve em um grão de origem", corrected["origin_match_count"].eq(1).all(), "PASS", str(len(corrected))),
        ("QA09", "pequeno volume permanece inelegível", not corrected.loc[corrected["small_volume_sensitive"], "maximum_exploration_eligible"].any(), "PASS", str(int(corrected["small_volume_sensitive"].sum()))),
        ("QA10", "ajuste negativo permanece inelegível", not corrected.loc[corrected["negative_adjustment_present"], "maximum_exploration_eligible"].any(), "PASS", str(int(corrected["negative_adjustment_present"].sum()))),
        ("QA11", "nenhuma seleção por ordem", not corrected[["physical_order_used", "alphabetical_order_used", "code_order_used"]].any().any(), "PASS", "all_false"),
        ("QA12", "Caged detalhado não visual", not corrected["detailed_caged_line_visual_use_allowed"].any(), "PASS", "all_false"),
        ("QA13", "direções shift-share separadas", bool(correction["shiftShareDirectionsSeparated"]), "PASS", "observed_change_direction != local_differential_direction semantics"),
        ("QA14", "fechamento mobilidade município→Vale", bool(mobility_audit["municipalToRegionClosure"]), "PASS", str(mobility_audit["rowCount"])),
        ("QA15", "paridade com Job 2", bool(mobility_audit["frozenJob2Parity"]), "PASS", "numerators_denominators_rates"),
        ("QA16", "âncoras Nova Santa Rita reconstruídas", set(mobility_audit["novaSantaRitaAnchors"]) == {"total", "fundamental", "medio"}, "PASS", json.dumps(mobility_audit["novaSantaRitaAnchors"], sort_keys=True)),
        ("QA17", "destino municipal não inferido", not mobility["destination_municipality_available"].any(), "PASS_WITH_EXPLICIT_LIMIT", "official tables do not name destination"),
        ("QA18", "cobertura municipal mobilidade", set(mobility_municipal["entity_id"]) == municipal_ids and len(mobility_municipal) == 30, "PASS", str(len(mobility_municipal))),
        ("QA19", "rede total na oferta", set(offer_municipal["network_scope"]) == {"total_all_dependencies"}, "PASS", "total_all_dependencies"),
        ("QA20", "dependência apenas QA", not offer["administrative_dependency_is_analytic_dimension"].any(), "PASS", "analytic=false; QA=true"),
        ("QA21", "zero de oferta não vira ausência de acesso", not offer["zero_access_conclusion_allowed"].any(), "PASS", "all_false"),
        ("QA22", "PNATE fecha dependências em QA", int(transport_audit["dependencyClosureQARowCount"]) == 30, "PASS", "30/30"),
        ("QA23", "PNATE não é proxy de mobilidade", not transport["is_mobility_measure"].any(), "PASS", "all_false"),
        ("QA24", "uso de transporte indisponível é explícito", not bool(transport_audit["schoolTransportUsageAvailable"]), "PASS_WITH_EXPLICIT_LIMIT", "compatible observation not materialized"),
        ("QA25", "execução PNATE indisponível é explícita", not bool(transport_audit["executionAmountAvailable"]), "PASS_WITH_EXPLICIT_LIMIT", "source has transfer/authorization, not execution"),
        ("QA26", "nenhuma taxa PNATE por estudante derivada", not transport["derived_per_student_rate"].any(), "PASS", "all_false"),
        ("QA27", "estágios financeiros separados", finance["financial_stage"].notna().all(), "PASS", ",".join(sorted(finance["financial_stage"].astype(str).unique()))),
        ("QA28", "sem crescimento monetário real inferido", not finance["nominal_cross_year_growth_claim_allowed"].any(), "PASS", "all_false"),
        ("QA29", "sem causalidade financeira", not finance["educational_result_causality_allowed"].any(), "PASS", "all_false"),
        ("QA30", "coordenação sem score", not coordination["score_used"].any() and coordination["combined_score"].isna().all(), "PASS", str(len(coordination))),
        ("QA31", "coordenação sem bom/ruim", not coordination["good_bad_classification_used"].any(), "PASS", "all_false"),
        ("QA32", "catálogo completo de fatos único", not facts["fact_id"].duplicated().any(), "PASS", f"{len(facts)}/{facts['fact_id'].nunique()}"),
        ("QA33", "histórias cobrem 9 direções × 11 escalas", len(story_frame) == 99 and story_frame["direction_id"].nunique() == 9, "PASS", str(len(story_frame))),
        ("QA34", "Nova Santa Rita em todas as direções", story_frame[story_frame["entity_id"].eq(NSR_CODE)]["direction_id"].nunique() == 9, "PASS", "9"),
        ("QA35", "sem narrativa pública", not story_frame["public_narrative_authorized"].any() and story_frame["public_narrative"].isna().all(), "PASS", "internal seeds only"),
        ("QA36", "sem teto editorial fixo", not story_frame["fixed_card_cap_applied"].any(), "PASS", "all_false"),
        ("QA37", "sem dupla contagem região/município", set(mobility["entity_scope"]) == {"municipality", "region", "state"}, "PASS", "scopes explicit"),
        ("QA38", "resíduo dos componentes publicados de mobilidade auditado sem redistribuição", mobility["study_location_component_residual"].notna().all(), "PASS_WITH_EXPLICIT_LIMIT", f"max_abs={int(mobility['study_location_component_residual'].abs().max())}"),
    ]
    rows = []
    failures = []
    for control_id, control, passed, pass_status, evidence in controls:
        status = pass_status if passed else "FAIL"
        if not passed:
            failures.append(control_id)
        rows.append(
            {
                "qa_control_id": control_id,
                "control": control,
                "status": status,
                "evidence": evidence,
                "blocking": status == "FAIL",
                "external_judgment_required": True,
            }
        )
    if failures:
        raise ValueError(f"Falhas QA Job 5G-D: {failures}")
    return pd.DataFrame(rows)


def build_source_registry(
    *,
    inputs: Mapping[str, Path],
    mobility_source_root: Path,
    pnate_audit: Mapping[str, Any],
    finance_audit: Mapping[str, Any],
) -> dict[str, Any]:
    mobility_manifest = json.loads(
        (mobility_source_root / "MANIFEST_SOURCE_MOBILITY_SIDRA_JOB5GD.json").read_text(
            encoding="utf-8"
        )
    )
    local_inputs = []
    for identifier, path in sorted(inputs.items()):
        local_inputs.append(
            {
                "inputId": identifier,
                "path": path.as_posix(),
                "byteSize": path.stat().st_size,
                "sha256": sha256_file(path),
                "frozen": True,
            }
        )
    return {
        "schemaVersion": "registro-fontes-aquisicoes-job5gd-v1",
        "officialAcquisitions": [
            {
                "institution": "IBGE",
                "system": "SIDRA",
                "tables": ["10321", "10324"],
                "period": 2022,
                "landingPage": mobility_manifest["landingPage"],
                "rawSnapshotManifest": (
                    "data_pipeline/data/vocacoes_pne_v7_job5gd/mobility_sidra/"
                    "MANIFEST_SOURCE_MOBILITY_SIDRA_JOB5GD.json"
                ),
                "rawSnapshotManifestSha256": sha256_file(
                    mobility_source_root / "MANIFEST_SOURCE_MOBILITY_SIDRA_JOB5GD.json"
                ),
                "acquiredAtUtc": mobility_manifest["acquiredAtUtc"],
                "licenseAndProvenance": mobility_manifest["licenseAndProvenance"],
                "destinationMunicipalityAvailable": False,
                "originDestinationMatrixDerived": False,
            }
        ],
        "databaseSources": [
            {
                "institution": "FNDE",
                "table": "public.fnde_pnate_municipio_dashboard",
                "mode": "read_only_transaction",
                "databaseWrites": False,
                "rowCount": pnate_audit["sourceRowCount"],
                "periods": pnate_audit["periods"],
                "materializedSnapshot": "FONTE_PNATE_VALE_2024_2026_JOB5GD_V1.csv.gz",
            }
        ],
        "canonicalFinance": {
            "municipalityCount": finance_audit["municipalityCount"],
            "inputHashes": finance_audit["inputHashes"],
            "sourceSnapshots": [
                "data_pipeline/data/municipal_finance/source_snapshot.json",
                "data_pipeline/data/municipal_finance/constitutional_source_snapshot.json",
            ],
        },
        "frozenLocalInputs": local_inputs,
        "nonOfficialSourcesUsed": False,
        "networkUsedDuringMaterialization": False,
    }


def _offer_endpoints(offer: pd.DataFrame) -> pd.DataFrame:
    year = pd.to_numeric(offer["year"], errors="raise")
    final_year = pd.to_numeric(offer["series_final_year"], errors="raise")
    return offer[year.eq(final_year)].copy()


def _heterogeneity_summary(
    *, mobility: pd.DataFrame, offer: pd.DataFrame, coordination: pd.DataFrame
) -> dict[str, Any]:
    summaries: list[dict[str, Any]] = []
    municipal_mobility = mobility[mobility["entity_scope"].eq("municipality")]
    for stage, group in municipal_mobility.groupby("stage", sort=True):
        values = pd.to_numeric(group["outside_share_percent"], errors="coerce")
        low = group.loc[values.idxmin()]
        high = group.loc[values.idxmax()]
        summaries.append(
            {
                "metric": "outside_share_percent",
                "stage": stage,
                "minimum": float(low["outside_share_percent"]),
                "minimumMunicipalityId": low["entity_id"],
                "minimumMunicipalityName": low["municipality_name"],
                "maximum": float(high["outside_share_percent"]),
                "maximumMunicipalityId": high["entity_id"],
                "maximumMunicipalityName": high["municipality_name"],
                "comparisonType": "ten_municipality_distribution_not_good_bad_ranking",
            }
        )
    endpoints = _offer_endpoints(offer)
    for domain, metric, stage in (
        ("general_offer", "located_enrollments", "medio"),
        ("rural_offer", "rural_enrollments", "all"),
        ("ept_offer", "located_technical_enrollments", "professional_technical"),
    ):
        selected = endpoints[
            endpoints["entity_scope"].eq("municipality")
            & endpoints["offer_domain"].eq(domain)
            & endpoints["metric"].eq(metric)
            & endpoints["stage"].eq(stage)
        ]
        summaries.append(
            {
                "metric": metric,
                "stage": stage,
                "municipalityCount": int(len(selected)),
                "zeroObservedCount": int(pd.to_numeric(selected["value"], errors="coerce").eq(0).sum()),
                "distribution": municipal_distribution(selected["value"]),
                "comparisonType": "school_location_distribution_not_resident_access",
            }
        )
    return {
        "summaries": summaries,
        "coordinationProfileCounts": coordination[
            coordination["entity_scope"].eq("municipality")
        ]["profile_state"].value_counts().sort_index().to_dict(),
        "goodBadClassification": False,
    }


def build_dossiers(
    *,
    municipality_names: Mapping[str, str],
    selected_municipality_id: str,
    mobility: pd.DataFrame,
    offer: pd.DataFrame,
    transport: pd.DataFrame,
    finance: pd.DataFrame,
    coordination: pd.DataFrame,
    facts: pd.DataFrame,
    stories: Mapping[str, Any],
    mobility_audit: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    endpoints = _offer_endpoints(offer)
    story_rows = pd.DataFrame(stories["stories"])

    def municipality_dossier(code: str) -> dict[str, Any]:
        return {
            "municipalityIbgeCode": code,
            "municipalityName": municipality_names[code],
            "isSelectedMunicipality": code == selected_municipality_id,
            "isMandatoryReconstruction": code == NSR_CODE,
            "networkScope": "total_all_dependencies",
            "mobility": _records(mobility[mobility["entity_id"].eq(code)]),
            "territorialOfferEndpoints": _records(endpoints[endpoints["entity_id"].eq(code)]),
            "transportAndPnate": _records(transport[transport["entity_id"].eq(code)]),
            "contextualFinance": _records(finance[finance["entity_id"].eq(code)]),
            "coordination": _records(coordination[coordination["entity_id"].eq(code)]),
            "facts": _records(facts[facts["entity_id"].eq(code)]),
            "stories": _records(story_rows[story_rows["entity_id"].eq(code)]),
            "publicNarrativeFinal": False,
            "externalJudgmentRequired": True,
        }

    municipal_dossiers = [
        municipality_dossier(code) for code in sorted(municipality_names)
    ]
    corpus = {
        "schemaVersion": "corpus-dossies-municipais-job5gd-v1",
        "municipalityCount": len(municipal_dossiers),
        "selectedMunicipalityId": selected_municipality_id,
        "reconstructibleByTextualIbgeCode": True,
        "dossiers": municipal_dossiers,
    }
    region_dossier = {
        "schemaVersion": "dossie-vale-do-sinos-job5gd-v1",
        "entityId": REGION_ENTITY_ID,
        "municipalityCount": len(municipality_names),
        "municipalityIds": sorted(municipality_names),
        "mobility": _records(mobility[mobility["entity_scope"].eq("region")]),
        "territorialOfferEndpoints": _records(
            endpoints[endpoints["entity_scope"].eq("region")]
        ),
        "transportAndPnate": _records(transport[transport["entity_scope"].eq("region")]),
        "contextualFinance": _records(finance[finance["entity_scope"].eq("region")]),
        "coordination": _records(coordination[coordination["entity_scope"].eq("region")]),
        "facts": _records(facts[facts["entity_scope"].eq("region")]),
        "stories": _records(story_rows[story_rows["entity_scope"].eq("region")]),
        "heterogeneity": _heterogeneity_summary(
            mobility=mobility, offer=offer, coordination=coordination
        ),
        "regionAggregationRule": "compatible counts are summed; rates are recomposed; otherwise municipal distribution",
        "municipalMedianCalledValeRate": False,
        "publicNarrativeFinal": False,
    }
    nsr = next(
        dossier
        for dossier in municipal_dossiers
        if dossier["municipalityIbgeCode"] == NSR_CODE
    )
    nsr_dossier = {
        "schemaVersion": "nova-santa-rita-job5gd-v1",
        **nsr,
        "mobilityAnchorsReconstructedFromOfficialSource": mobility_audit[
            "novaSantaRitaAnchors"
        ],
        "integrationRequirements": [
            "school-age population growth kept separate from located enrollment growth",
            "high-school trajectory kept separate from residence mobility",
            "EPT offer uses school location",
            "youth work uses workplace and preserves 15-17 vs 18-24",
            "logistics transformation remains non-causal context",
        ],
    }
    return region_dossier, nsr_dossier, corpus


def limitations_payload() -> dict[str, Any]:
    return {
        "schemaVersion": "limitacoes-job5gd-v1",
        "finalState": FINAL_STATE,
        "limits": [
            {
                "id": "LIM_MOBILITY_DESTINATION",
                "state": "NOT_AVAILABLE",
                "scope": "educational_mobility",
                "detail": "SIDRA 10321/10324 distinguish own/other municipality/foreign country but do not name the destination municipality.",
                "forbidden": "corridors, receiving municipalities or route proposals",
            },
            {
                "id": "LIM_CENSUS_SAMPLE_MICRODATA",
                "state": "OFFICIAL_RELEASE_POSTPONED_AT_VERIFICATION_DATE",
                "scope": "origin_destination",
                "detail": "Official Census 2022 sample microdata remained postponed on 2026-08-29.",
                "forbidden": "derive an origin-destination matrix from unavailable microdata",
            },
            {
                "id": "LIM_TRANSPORT_USAGE",
                "state": "NOT_MATERIALIZED_COMPATIBLY_FOR_TEN_MUNICIPALITIES",
                "scope": "school_transport",
                "detail": "No compatible canonical ten-municipality observation of students using school transport was found.",
                "forbidden": "treat PNATE beneficiaries as observed transport users",
            },
            {
                "id": "LIM_PNATE_EXECUTION",
                "state": "NOT_IN_SOURCE_TABLE",
                "scope": "pnate",
                "detail": "The canonical table supplies beneficiaries, transfers, authorization, forecasts, balances and adjustments, not executed expenditure.",
                "forbidden": "call transfers or authorization execution",
            },
            {
                "id": "LIM_PNATE_NOT_MOBILITY",
                "state": "SEMANTIC_GUARDRAIL",
                "scope": "pnate",
                "detail": "PNATE is a support program/transfer at executor grain.",
                "forbidden": "use PNATE as origin-destination, distance, access, result or regional-dependence proxy",
            },
            {
                "id": "LIM_FINANCE_NOMINAL",
                "state": "NOMINAL_ONLY",
                "scope": "contextual_finance",
                "detail": "Financial stages and exercises remain separate; no deflation contract was introduced.",
                "forbidden": "claim real growth or causal educational effect",
            },
            {
                "id": "LIM_OFFER_LOCATION",
                "state": "LENS_GUARDRAIL",
                "scope": "territorial_offer",
                "detail": "Schools, enrollments, classes, teaching units, EJA and EPT use school location.",
                "forbidden": "infer resident coverage or access from located offer, including observed zero",
            },
            {
                "id": "LIM_LENS_LINKAGE",
                "state": "NO_MICROLINK",
                "scope": "integrated_coordination",
                "detail": "Residence, school location, workplace and municipal executor are separate lenses.",
                "forbidden": "infer that sources observe the same people or assert causality",
            },
            {
                "id": "LIM_ADMIN_DEPENDENCY",
                "state": "QA_ONLY",
                "scope": "all_educational_analysis",
                "detail": "Administrative dependency is retained only for reconstruction, provenance and closure QA.",
                "forbidden": "filter, card, ranking, comparison, selection or narrative by dependency",
            },
            {
                "id": "LIM_CAGED_DETAIL",
                "state": "INTERNAL_NON_VISUAL",
                "scope": "caged",
                "detail": "Detailed Caged remains outside visual consumption; specific eligibility flags govern aggregate facts.",
                "forbidden": "authorize detailed lines or interpret global share_status alone",
            },
            {
                "id": "LIM_CENSUS_PRELIMINARY",
                "state": "OFFICIAL_PRELIMINARY_RESULT",
                "scope": "mobility",
                "detail": "Mobility tables are official preliminary results for 2022 and preserve their source status.",
                "forbidden": "erase the evidence class or mix incompatible denominators",
            },
            {
                "id": "LIM_MOBILITY_PUBLISHED_COMPONENT_RESIDUAL",
                "state": "AUDITED_NOT_REDISTRIBUTED",
                "scope": "mobility",
                "detail": "The official total can differ from the sum of the published own-municipality, other-municipality and foreign-country components; numerator and denominator remain the direct official cells.",
                "forbidden": "force closure by reallocating the residual or add foreign-country counts to the frozen other-municipality numerator",
            },
            {
                "id": "LIM_EDITORIAL_REVIEW",
                "state": "EXTERNAL_JUDGMENT_REQUIRED",
                "scope": "stories",
                "detail": "All titles and story seeds are internal inputs; no fixed card cap or public narrative was approved.",
                "forbidden": "automatic approval or publication",
            },
        ],
        "localizedGapsDoNotBlockOtherFronts": True,
        "substantiveIndicatorChange": False,
        "causalInferenceUsed": False,
    }


def section_map(stories: Mapping[str, Any], availability: pd.DataFrame) -> str:
    lines = [
        "# Mapa de seções potenciais — Job 5G-D",
        "",
        "> Uso interno. Nenhuma seção, ordem ou quantidade de cartões está aprovada para publicação.",
        "",
        "## Regras de consumo",
        "",
        "- preservar residência, localização da escola, local do estabelecimento e executor como lentes distintas;",
        "- usar rede `total_all_dependencies`; dependência administrativa aparece apenas no QA;",
        "- usar o catálogo máximo antes de qualquer corte editorial;",
        "- não transformar mediana municipal em taxa do Vale nem perfis em recomendação automática;",
        "- manter toda narrativa como seed interno até julgamento externo.",
        "",
        "## Macroblocos candidatos",
        "",
    ]
    story_rows = pd.DataFrame(stories["stories"])
    for row in availability.to_dict("records"):
        direction_id = str(row["direction_id"])
        lines.extend(
            [
                f"### {row['macroblock_id']}",
                "",
                f"- Direção: `{direction_id}`.",
                f"- Variantes preservadas: {int(row['story_count'])} (Vale + dez municípios).",
                f"- Disponibilidade: `{row['availability_state']}`.",
                f"- Limite: {row['interpretation_limit']}",
                f"- Stories materiais internos: {int((story_rows['direction_id'].eq(direction_id) & story_rows['materiality_state'].eq('POTENTIAL_MATERIAL_STORY')).sum())}.",
                "",
            ]
        )
    lines.extend(
        [
            "## Fora do consumo visual",
            "",
            "- linhas detalhadas do Caged;",
            "- decomposição por dependência administrativa;",
            "- matriz origem–destino ou rotas, pois não foram observadas;",
            "- execução PNATE e uso observado de transporte escolar, indisponíveis no contrato atual;",
            "- qualquer narrativa pública definitiva.",
            "",
        ]
    )
    return "\n".join(lines)


CSV_OUTPUTS = {
    "MATRIZ_CATALOGO_FATOS_NOVA_SANTA_RITA_JOB5GCR_V2.csv.gz": "corrected_gcr",
    "FONTE_PNATE_VALE_2024_2026_JOB5GD_V1.csv.gz": "pnate_source",
    "PAINEL_MOBILIDADE_EDUCACIONAL_POR_ETAPA_JOB5GD_V1.csv.gz": "mobility",
    "PAINEL_ESTRUTURA_TERRITORIAL_OFERTA_JOB5GD_V1.csv.gz": "offer",
    "PAINEL_TRANSPORTE_ESCOLAR_PNATE_JOB5GD_V1.csv.gz": "transport",
    "PAINEL_FINANCEIRO_CONTEXTUAL_SELECIONAVEL_JOB5GD_V1.csv.gz": "finance",
    "MATRIZ_COORDENACAO_REGIONAL_JOB5GD_V1.csv.gz": "coordination",
    "CATALOGO_COMPLETO_FATOS_JOB5GD_V1.csv.gz": "facts",
    "MATRIZ_VINCULOS_PNE_PME_JOB5GD_V1.csv.gz": "pne_links",
    "MATRIZ_DISPONIBILIDADE_MATERIALIDADE_JOB5GD_V1.csv.gz": "availability",
    "MATRIZ_QA_JOB5GD_V1.csv.gz": "qa",
    "MATRIZ_C1_C12_CANONICA_JOB5GD_V1.csv.gz": "c1_c12",
}


def materialize_components(
    *,
    job2_root: Path,
    gar_root: Path,
    gbr_root: Path,
    gcr_root: Path,
    mobility_source_root: Path,
    finance_root: Path,
    pnate_source: pd.DataFrame,
    municipality_names: Mapping[str, str],
    selected_municipality_id: str,
    inputs: Mapping[str, Path],
) -> tuple[dict[str, pd.DataFrame], dict[str, Any]]:
    source_v1 = _read_csv(
        gcr_root / "MATRIZ_CATALOGO_FATOS_NOVA_SANTA_RITA_JOB5GCR_V1.csv.gz"
    )
    corrected, correction = build_corrected_gcr_fact_catalog(
        gcr_root=gcr_root, source_v1=source_v1
    )
    mobility, mobility_audit = build_mobility_panel(
        source_root=mobility_source_root,
        municipality_names=municipality_names,
        frozen_job2_panel=_read_csv(
            job2_root / "2e" / "mobilidade_educacional_2022.csv.gz"
        ),
    )
    offer = build_territorial_offer_panel(
        job2_root=job2_root,
        gar_root=gar_root,
        gbr_root=gbr_root,
        gcr_root=gcr_root,
        municipality_names=municipality_names,
    )
    transport, transport_audit = build_transport_pnate_panel(
        pnate_source=pnate_source, municipality_names=municipality_names
    )
    finance, finance_audit = build_contextual_finance_panel(
        finance_root=finance_root, municipality_names=municipality_names
    )
    coordination = build_coordination_matrix(
        mobility=mobility,
        offer=offer,
        transport=transport,
        finance=finance,
        gar_root=gar_root,
        gbr_root=gbr_root,
        gcr_root=gcr_root,
        municipality_names=municipality_names,
    )
    facts = build_complete_fact_catalog(
        corrected_gcr=corrected,
        mobility=mobility,
        offer=offer,
        transport=transport,
        finance=finance,
    )
    stories = build_story_catalog(
        coordination=coordination,
        municipality_names=municipality_names,
        selected_municipality_id=selected_municipality_id,
    )
    pne_links = build_pne_pme_links(coordination)
    availability = build_availability_materiality(
        coordination=coordination, stories=stories
    )
    c1_c12 = build_c1_c12_matrix(availability)
    qa = build_qa_matrix(
        corrected=corrected,
        correction=correction,
        mobility=mobility,
        mobility_audit=mobility_audit,
        offer=offer,
        transport=transport,
        transport_audit=transport_audit,
        finance=finance,
        coordination=coordination,
        facts=facts,
        stories=stories,
        municipality_names=municipality_names,
    )
    vale_dossier, nsr_dossier, municipal_corpus = build_dossiers(
        municipality_names=municipality_names,
        selected_municipality_id=selected_municipality_id,
        mobility=mobility,
        offer=offer,
        transport=transport,
        finance=finance,
        coordination=coordination,
        facts=facts,
        stories=stories,
        mobility_audit=mobility_audit,
    )
    pnate_stable = _stable(pnate_source.copy(), ["id_municipio", "ano"])
    frames = {
        "corrected_gcr": corrected,
        "pnate_source": pnate_stable,
        "mobility": mobility,
        "offer": offer,
        "transport": transport,
        "finance": finance,
        "coordination": coordination,
        "facts": facts,
        "pne_links": pne_links,
        "availability": availability,
        "qa": qa,
        "c1_c12": c1_c12,
    }
    metadata = {
        "correction": correction,
        "mobilityAudit": mobility_audit,
        "transportAudit": transport_audit,
        "financeAudit": finance_audit,
        "stories": stories,
        "valeDossier": vale_dossier,
        "nsrDossier": nsr_dossier,
        "municipalCorpus": municipal_corpus,
        "limitations": limitations_payload(),
        "sourceRegistry": build_source_registry(
            inputs=inputs,
            mobility_source_root=mobility_source_root,
            pnate_audit=transport_audit,
            finance_audit=finance_audit,
        ),
    }
    return frames, metadata


def write_package(
    *,
    output_dir: Path,
    contract: Mapping[str, Any],
    inputs: Mapping[str, Path],
    job2_root: Path,
    gar_root: Path,
    gbr_root: Path,
    gcr_root: Path,
    mobility_source_root: Path,
    finance_root: Path,
    pnate_source: pd.DataFrame,
    municipality_names: Mapping[str, str],
    selected_municipality_id: str,
    frozen_integrity: Mapping[str, str],
) -> dict[str, Any]:
    """Escreve o lote em diretório novo; o chamador promove transacionalmente."""

    output_dir.mkdir(parents=True, exist_ok=False)
    frames, metadata = materialize_components(
        job2_root=job2_root,
        gar_root=gar_root,
        gbr_root=gbr_root,
        gcr_root=gcr_root,
        mobility_source_root=mobility_source_root,
        finance_root=finance_root,
        pnate_source=pnate_source,
        municipality_names=municipality_names,
        selected_municipality_id=selected_municipality_id,
        inputs=inputs,
    )
    for filename, key in CSV_OUTPUTS.items():
        write_csv_gzip(output_dir / filename, frames[key])

    source_v1_path = (
        gcr_root / "MATRIZ_CATALOGO_FATOS_NOVA_SANTA_RITA_JOB5GCR_V1.csv.gz"
    )
    corrected_v2_path = (
        output_dir / "MATRIZ_CATALOGO_FATOS_NOVA_SANTA_RITA_JOB5GCR_V2.csv.gz"
    )
    correction_package = {
        "schemaVersion": "pacote-correcao-catalogo-job5gcr-v2",
        "correctionType": "grain_identity_and_consumption_non_substantive",
        "sourceFrozenArtifact": source_v1_path.as_posix(),
        "sourceFrozenArtifactSha256": sha256_file(source_v1_path),
        "correctedArtifact": corrected_v2_path.name,
        "correctedArtifactSha256": sha256_file(corrected_v2_path),
        "sourceFrozenArtifactModified": False,
        "indicatorDefinitionChanged": False,
        "numericValueChanged": False,
        "canonicalCagedFactIdIncludesAgeGroup": True,
        "compactSelectionPreservedAsCompatibilityOnly": True,
        "maximumExplorationHasFixedCap": False,
        "correctionAudit": metadata["correction"],
        "externalJudgmentRequired": True,
    }
    review_package = {
        "schemaVersion": "pacote-revisao-externa-job5gd-v1",
        "jobId": "5G-D",
        "classification": "DATA_LOGIC + INTERNAL_EDITORIAL_INPUTS",
        "finalState": FINAL_STATE,
        "objective": "Materializar mobilidade, oferta territorial, PNATE, finanças contextuais e coordenação regional após corrigir o grão Caged.",
        "preflightCorrection": correction_package,
        "fronts": {
            "mobility": {
                "state": "MATERIALIZED_WITH_DESTINATION_LIMIT",
                "audit": metadata["mobilityAudit"],
            },
            "territorialOffer": {
                "state": "MATERIALIZED",
                "rowCount": len(frames["offer"]),
            },
            "transportAndPnate": {
                "state": "MATERIALIZED_WITH_USAGE_AND_EXECUTION_LIMITS",
                "audit": metadata["transportAudit"],
            },
            "contextualFinance": {
                "state": "MATERIALIZED_SELECTABLE_CONTEXT_ONLY",
                "audit": metadata["financeAudit"],
            },
            "regionalCoordination": {
                "state": "MATERIALIZED_NO_SCORE",
                "rowCount": len(frames["coordination"]),
                "directionCount": int(frames["coordination"]["combination_id"].nunique()),
            },
        },
        "catalogs": {
            "factCount": len(frames["facts"]),
            "storyCount": metadata["stories"]["storyCount"],
            "fixedCardCap": None,
            "publicNarrativeFinal": False,
        },
        "limits": metadata["limitations"]["limits"],
        "automaticApproval": False,
        "externalJudgmentRequired": True,
        "publicationAllowed": False,
        "frontendAllowed": False,
        "gate11": "CLOSED",
    }
    json_payloads = {
        "PACOTE_CORRECAO_CATALOGO_JOB5GCR_V2.json": correction_package,
        "REGISTRO_FONTES_E_AQUISICOES_JOB5GD_V1.json": metadata["sourceRegistry"],
        "CATALOGO_MAXIMO_HISTORIAS_POTENCIAIS_JOB5GD_V1.json": metadata["stories"],
        "DOSSIE_VALE_DO_SINOS_JOB5GD_V1.json": metadata["valeDossier"],
        "NOVA_SANTA_RITA_JOB5GD_V1.json": metadata["nsrDossier"],
        "CORPUS_DOSSIES_MUNICIPAIS_JOB5GD_V1.json": metadata["municipalCorpus"],
        "LIMITACOES_JOB5GD_V1.json": metadata["limitations"],
        "PACOTE_REVISAO_EXTERNA_JOB5GD.json": review_package,
    }
    for filename, payload in json_payloads.items():
        write_json(output_dir / filename, payload)
    (output_dir / "MAPA_SECOES_POTENCIAIS_JOB5GD_V1.md").write_text(
        section_map(metadata["stories"], frames["availability"]),
        encoding="utf-8",
        newline="\n",
    )

    expected = set(contract["outputs"])
    pre_manifest = {path.name for path in output_dir.iterdir() if path.is_file()}
    if pre_manifest != expected - {"MANIFEST_JOB5GD.json"}:
        raise ValueError(
            "Lote pré-manifesto divergente: "
            f"missing={sorted(expected-pre_manifest-{'MANIFEST_JOB5GD.json'})}, "
            f"extra={sorted(pre_manifest-expected)}"
        )

    artifact_metadata = {
        "MATRIZ_CATALOGO_FATOS_NOVA_SANTA_RITA_JOB5GCR_V2.csv.gz": (
            ["fact_id"], "2019-2025", "workplace", "source-specific", "canonical fact grain including age_group for Caged"
        ),
        "FONTE_PNATE_VALE_2024_2026_JOB5GD_V1.csv.gz": (
            ["id_municipio", "ano"], "2024-2026", "municipal_executor", "source-specific", "read-only source snapshot"
        ),
        "PAINEL_MOBILIDADE_EDUCACIONAL_POR_ETAPA_JOB5GD_V1.csv.gz": (
            ["entity_id", "stage"], "2022", "student_residence", "people|percent", "sum compatible counts and recompose ratio"
        ),
        "PAINEL_ESTRUTURA_TERRITORIAL_OFERTA_JOB5GD_V1.csv.gz": (
            ["entity_id", "year", "offer_domain", "stage", "metric"], "2014-2025 or source-specific", "school_location", "source-specific", "total network compatible counts or declared municipal distribution"
        ),
        "PAINEL_TRANSPORTE_ESCOLAR_PNATE_JOB5GD_V1.csv.gz": (
            ["entity_id", "exercise_year", "metric"], "2024-2026", "municipal_executor", "students|BRL_nominal", "sum compatible executor values; unavailable fields stay unavailable"
        ),
        "PAINEL_FINANCEIRO_CONTEXTUAL_SELECIONAVEL_JOB5GD_V1.csv.gz": (
            ["entity_id", "metric", "reference_year"], "source-specific", "municipal_executor", "BRL_nominal|percent", "stage-preserving sum or municipal distribution"
        ),
        "MATRIZ_COORDENACAO_REGIONAL_JOB5GD_V1.csv.gz": (
            ["combination_id", "entity_id"], "source-specific", "multiple_separate_lenses", "internal profile", "transparent inputs and municipal distributions; no score"
        ),
        "CATALOGO_COMPLETO_FATOS_JOB5GD_V1.csv.gz": (
            ["fact_id"], "source-specific", "declared_per_fact", "source-specific", "complete catalog before editorial selection"
        ),
        "MATRIZ_VINCULOS_PNE_PME_JOB5GD_V1.csv.gz": (
            ["combination_id"], "source-specific", "metadata", "metadata", "no legal indicator recalculation"
        ),
        "MATRIZ_DISPONIBILIDADE_MATERIALIDADE_JOB5GD_V1.csv.gz": (
            ["direction_id"], "source-specific", "metadata", "state", "transparent availability and materiality"
        ),
        "MATRIZ_QA_JOB5GD_V1.csv.gz": (
            ["qa_control_id"], "generation", "QA", "state", "executable checks"
        ),
        "MATRIZ_C1_C12_CANONICA_JOB5GD_V1.csv.gz": (
            ["analysis_id", "criterion_id"], "generation", "QA", "state", "criterion evidence without score"
        ),
    }
    artifacts: list[dict[str, Any]] = []
    for filename in sorted(pre_manifest):
        frame = frames[CSV_OUTPUTS[filename]] if filename in CSV_OUTPUTS else None
        grain, period, lens, unit, aggregation = artifact_metadata.get(
            filename,
            ("declared_in_artifact", "source-specific", "metadata", "metadata", "declared in artifact"),
        )
        artifacts.append(
            artifact_record(
                root=output_dir,
                path=output_dir / filename,
                frame=frame,
                subjob="5G-D",
                grain=grain,
                period=period,
                lens=lens,
                unit=unit,
                aggregation_rule=aggregation,
            )
        )

    frozen_after = {
        key: directory_content_digest(Path(path))
        for key, path in {
            "job2": job2_root,
            "job5gar": gar_root,
            "job5gbr": gbr_root,
            "job5gcr": gcr_root,
        }.items()
    }
    if dict(frozen_integrity) != frozen_after:
        raise ValueError("Um pacote congelado mudou durante a geração 5G-D")
    manifest = {
        "schemaVersion": "manifest-job5gd-v1",
        "jobId": "5G-D",
        "classification": "DATA_LOGIC",
        "domains": contract["domains"],
        "objective": review_package["objective"],
        "finalState": FINAL_STATE,
        "contract": contract,
        "scope": contract["scope"],
        "selectedMunicipalityId": selected_municipality_id,
        "artifacts": artifacts,
        "summary": {
            "outputCount": len(expected),
            "artifactHashCount": len(artifacts),
            "rowCounts": {filename: len(frames[key]) for filename, key in CSV_OUTPUTS.items()},
            "storyCount": metadata["stories"]["storyCount"],
            "directionCount": int(frames["coordination"]["combination_id"].nunique()),
            "municipalityCount": len(municipality_names),
        },
        "preflightCorrection": correction_package,
        "audits": {
            "mobility": metadata["mobilityAudit"],
            "transportPnate": metadata["transportAudit"],
            "finance": metadata["financeAudit"],
        },
        "frozenInputIntegrity": {"before": dict(frozen_integrity), "after": frozen_after},
        "implementation": {
            identifier: {
                "path": path.as_posix(),
                "byteSize": path.stat().st_size,
                "sha256": sha256_file(path),
            }
            for identifier, path in sorted(inputs.items())
        },
        "formulasPreserved": [
            "mobility_rate=numerator/denominator*100; zero denominator returns null",
            "regional compatible counts summed before rate recomposition",
            "relative change uses valid nonzero base only",
            "financial stages remain separate",
            "Caged balance, HHI and shift-share definitions frozen from Job 5G-C-R",
        ],
        "formulasAltered": [],
        "generation": {
            "deterministic": True,
            "transactional": True,
            "manifestLast": True,
            "networkUsed": False,
            "officialNetworkAcquisitionPerformedSeparately": True,
            "databaseUsed": True,
            "databaseMode": "read_only_transaction",
            "databaseWrites": False,
            "publicDataChanged": False,
            "frontendChanged": False,
            "publicNarrativeWritten": False,
            "fullBuildUsed": False,
            "publicationPerformed": False,
            "gate11": "CLOSED",
        },
        "limits": metadata["limitations"]["limits"],
        "automaticApproval": False,
        "externalJudgmentRequired": True,
    }
    write_json(output_dir / "MANIFEST_JOB5GD.json", manifest)
    if {path.name for path in output_dir.iterdir() if path.is_file()} != expected:
        raise ValueError("O lote final 5G-D não contém exatamente as saídas contratadas")
    return manifest


def validate_existing_output(output_dir: Path) -> dict[str, Any]:
    manifest_path = output_dir / "MANIFEST_JOB5GD.json"
    if not manifest_path.is_file():
        raise FileNotFoundError("MANIFEST_JOB5GD.json ausente")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("finalState") != FINAL_STATE:
        raise ValueError("Estado final divergente no manifesto 5G-D")
    expected = set(manifest["contract"]["outputs"])
    actual = {path.name for path in output_dir.iterdir() if path.is_file()}
    if actual != expected:
        raise ValueError(f"Lote 5G-D divergente: missing={expected-actual}, extra={actual-expected}")
    for artifact in manifest["artifacts"]:
        path = output_dir / artifact["path"]
        if path.stat().st_size != artifact["byteSize"] or sha256_file(path) != artifact["sha256"]:
            raise ValueError(f"Hash/tamanho divergente em {artifact['path']}")

    corrected = _read_csv(
        output_dir / "MATRIZ_CATALOGO_FATOS_NOVA_SANTA_RITA_JOB5GCR_V2.csv.gz"
    )
    if len(corrected) != 1364 or corrected["fact_id"].nunique() != 1364:
        raise ValueError("Catálogo corretivo não possui 1.364 fact_id únicos")
    caged = corrected[corrected["universe"].str.startswith("CAGED_")]
    if caged["age_group"].isna().any() or set(caged["age_group"]) != {"15_17", "18_24"}:
        raise ValueError("Faixas Caged ausentes ou misturadas")
    if not corrected["origin_match_count"].eq(1).all():
        raise ValueError("Fato corretivo sem origem unívoca")
    if corrected["detailed_caged_line_visual_use_allowed"].any():
        raise ValueError("Linha Caged detalhada foi autorizada visualmente")

    mobility = _read_csv(
        output_dir / "PAINEL_MOBILIDADE_EDUCACIONAL_POR_ETAPA_JOB5GD_V1.csv.gz"
    )
    if len(mobility) != 36 or mobility.duplicated(["entity_id", "stage"]).any():
        raise ValueError("Painel de mobilidade não possui grão 36 único")
    nsr = mobility[mobility["entity_id"].eq(NSR_CODE)].set_index("stage")
    expected_anchors = {
        "total": (1349, 7666),
        "fundamental": (355, 4090),
        "medio": (220, 1151),
    }
    for stage, (expected_numerator, expected_denominator) in expected_anchors.items():
        observed_numerator = int(nsr.loc[stage, "numerator"])
        observed_denominator = int(nsr.loc[stage, "denominator"])
        expected_value = expected_numerator / expected_denominator * 100.0
        if (
            observed_numerator != expected_numerator
            or observed_denominator != expected_denominator
            or abs(float(nsr.loc[stage, "outside_share_percent"]) - expected_value) > 1e-10
        ):
            raise ValueError(f"Âncora de Nova Santa Rita divergiu em {stage}")

    pnate = _read_csv(output_dir / "FONTE_PNATE_VALE_2024_2026_JOB5GD_V1.csv.gz")
    if len(pnate) != 30 or pnate.duplicated(["id_municipio", "ano"]).any():
        raise ValueError("Snapshot PNATE não possui 30 grãos únicos")
    transport = _read_csv(
        output_dir / "PAINEL_TRANSPORTE_ESCOLAR_PNATE_JOB5GD_V1.csv.gz"
    )
    if transport["is_mobility_measure"].map(_as_bool).any() or transport["derived_per_student_rate"].map(_as_bool).any():
        raise ValueError("PNATE foi convertido indevidamente em mobilidade/taxa")
    coordination = _read_csv(
        output_dir / "MATRIZ_COORDENACAO_REGIONAL_JOB5GD_V1.csv.gz"
    )
    if len(coordination) != 99 or coordination["score_used"].map(_as_bool).any() or coordination["combined_score"].notna().any():
        raise ValueError("Matriz de coordenação não preservou 9 × 11 sem score")
    facts = _read_csv(output_dir / "CATALOGO_COMPLETO_FATOS_JOB5GD_V1.csv.gz")
    if facts["fact_id"].duplicated().any():
        raise ValueError("Catálogo completo contém fact_id duplicado")
    stories = json.loads(
        (output_dir / "CATALOGO_MAXIMO_HISTORIAS_POTENCIAIS_JOB5GD_V1.json").read_text(encoding="utf-8")
    )
    if stories["storyCount"] != 99 or stories["fixedCardCap"] is not None:
        raise ValueError("Catálogo máximo de histórias foi reduzido ou limitado")
    qa = _read_csv(output_dir / "MATRIZ_QA_JOB5GD_V1.csv.gz")
    if qa["status"].eq("FAIL").any():
        raise ValueError("Matriz QA contém falha")
    canonical = _read_csv(
        output_dir / "MATRIZ_C1_C12_CANONICA_JOB5GD_V1.csv.gz"
    )
    if not canonical.groupby("analysis_id").size().eq(12).all():
        raise ValueError("Matriz C1–C12 incompleta")
    if canonical["score"].notna().any() or canonical["automatic_approval"].map(_as_bool).any():
        raise ValueError("Matriz C1–C12 pontuou ou aprovou automaticamente")
    return {
        "finalState": FINAL_STATE,
        "outputCount": len(actual),
        "artifactHashCount": len(manifest["artifacts"]),
        "manifestSha256": sha256_file(manifest_path),
        "correctedFactCount": len(corrected),
        "completeFactCount": len(facts),
        "storyCount": stories["storyCount"],
        "qaControlCount": len(qa),
        "validationOnly": True,
    }
