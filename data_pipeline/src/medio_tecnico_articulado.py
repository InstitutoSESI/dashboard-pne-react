"""Validated calculations for PNE goals 12.a and 12.b.

The source grain is one aggregate row per municipality and year. Integrated
and concomitant enrolments are distinct columns in the same official table;
they are added without attempting to deduplicate students that the aggregate
does not identify.
"""

from __future__ import annotations

from typing import Iterable

import pandas as pd


BASELINE_YEAR = 2025
REQUIRED_COLUMNS = (
    "ano",
    "id_municipio",
    "mat_integrado_total",
    "mat_concomitante_total",
    "mat_medio",
)
DEPENDENCY_COLUMNS = {
    "integrado": {
        "total": "mat_integrado_total",
        "federal": "mat_integrado_federal",
        "estadual": "mat_integrado_estadual",
        "municipal": "mat_integrado_municipal",
        "privada": "mat_integrado_privada",
    },
    "concomitante": {
        "total": "mat_concomitante_total",
        "federal": "mat_concomitante_federal",
        "estadual": "mat_concomitante_estadual",
        "municipal": "mat_concomitante_municipal",
        "privada": "mat_concomitante_privada",
    },
}
NUMERIC_COLUMNS = tuple(
    dict.fromkeys(
        [*REQUIRED_COLUMNS[2:], *[column for mode in DEPENDENCY_COLUMNS.values() for column in mode.values()]]
    )
)


class MedioTecnicoArticuladoValidationError(ValueError):
    """Raised when the curated indicator contract is violated."""


def _coerce_numeric(frame: pd.DataFrame, columns: Iterable[str]) -> pd.DataFrame:
    result = frame.copy()
    for column in columns:
        if column not in result.columns:
            continue
        original = result[column]
        converted = pd.to_numeric(original, errors="coerce")
        unexpected = original.notna() & converted.isna()
        if unexpected.any():
            sample = original.loc[unexpected].iloc[0]
            raise MedioTecnicoArticuladoValidationError(
                f"Valor não numérico em {column}: {sample!r}."
            )
        result[column] = converted
    return result


def validate_dependency_reconciliation(frame: pd.DataFrame) -> None:
    """Validate total = federal + estadual + municipal + privada when present."""

    if frame.empty:
        return

    for mode, columns in DEPENDENCY_COLUMNS.items():
        required = tuple(columns.values())
        if not all(column in frame.columns for column in required):
            continue
        values = frame[list(required)].apply(pd.to_numeric, errors="coerce")
        values = values.rename(columns={column: name for name, column in columns.items()})
        complete = values.notna().all(axis=1)
        if not complete.any():
            continue
        dependency_sum = values.loc[complete, ["federal", "estadual", "municipal", "privada"]].sum(axis=1)
        mismatch = dependency_sum != values.loc[complete, "total"]
        if mismatch.any():
            sample_index = mismatch.index[mismatch][0]
            raise MedioTecnicoArticuladoValidationError(
                f"Reconciliação inconsistente para {mode} na linha {sample_index}."
            )


def calculate_medio_tecnico_articulado_series(frame: pd.DataFrame) -> pd.DataFrame:
    """Return one validated observed row per municipality and year.

    ``mat_medio == 0`` is a valid source observation but has no calculable
    percentage. The resulting ``percentual_calculado`` remains null. Integrated
    and concomitant components must both be observed; two zero components with a
    positive denominator remain a valid 0% result.
    """

    if not isinstance(frame, pd.DataFrame):
        raise MedioTecnicoArticuladoValidationError("A fonte precisa ser um DataFrame.")

    missing = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    if missing:
        raise MedioTecnicoArticuladoValidationError(
            f"Colunas obrigatórias ausentes: {', '.join(missing)}."
        )

    result = _coerce_numeric(frame, NUMERIC_COLUMNS)
    result["ano"] = pd.to_numeric(result["ano"], errors="coerce")
    if result["ano"].isna().any():
        raise MedioTecnicoArticuladoValidationError("Ano ausente ou inválido.")
    result["ano"] = result["ano"].astype(int)
    result["id_municipio"] = result["id_municipio"].astype("string").str.strip()
    if result["id_municipio"].isna().any() or (result["id_municipio"] == "").any():
        raise MedioTecnicoArticuladoValidationError("Código IBGE ausente.")

    if result.duplicated(subset=["ano", "id_municipio"]).any():
        raise MedioTecnicoArticuladoValidationError(
            "Há mais de uma linha para o mesmo ano e código IBGE."
        )

    for column in NUMERIC_COLUMNS:
        if column not in result.columns:
            continue
        negative = result[column].notna() & (result[column] < 0)
        if negative.any():
            raise MedioTecnicoArticuladoValidationError(
                f"Valor negativo em {column}; a carga foi rejeitada."
            )

    validate_dependency_reconciliation(result)

    result["mat_articulado_total"] = result[
        ["mat_integrado_total", "mat_concomitante_total"]
    ].sum(axis=1, min_count=2)
    valid_denominator = result["mat_medio"] > 0
    valid_ratio = valid_denominator & result["mat_articulado_total"].notna()
    result["percentual_calculado"] = pd.NA
    result.loc[valid_ratio, "percentual_calculado"] = (
        100.0
        * result.loc[valid_ratio, "mat_articulado_total"]
        / result.loc[valid_ratio, "mat_medio"]
    )
    result["percentual_calculado"] = pd.to_numeric(
        result["percentual_calculado"], errors="coerce"
    )
    valid_articulated_ratio = valid_denominator & result["mat_articulado_total"].notna()
    result["percentual_articulado_total"] = pd.NA
    result.loc[valid_articulated_ratio, "percentual_articulado_total"] = (
        100.0
        * result.loc[valid_articulated_ratio, "mat_articulado_total"]
        / result.loc[valid_articulated_ratio, "mat_medio"]
    )
    result["percentual_articulado_total"] = pd.to_numeric(
        result["percentual_articulado_total"], errors="coerce"
    )
    result["acima_de_100"] = result["percentual_calculado"] > 100.0
    result["articulado_acima_de_100"] = result["percentual_articulado_total"] > 100.0
    return result.sort_values(["id_municipio", "ano"]).reset_index(drop=True)


def _prepare_cycle_frame(
    frame: pd.DataFrame,
    required_value_columns: tuple[str, ...],
) -> pd.DataFrame:
    if not isinstance(frame, pd.DataFrame):
        raise MedioTecnicoArticuladoValidationError(
            "A fonte precisa ser um DataFrame."
        )
    required = ("ano", "id_municipio", *required_value_columns)
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise MedioTecnicoArticuladoValidationError(
            f"Colunas obrigatórias ausentes: {', '.join(missing)}."
        )

    result = _coerce_numeric(frame, required_value_columns)
    result["ano"] = pd.to_numeric(result["ano"], errors="coerce")
    if result["ano"].isna().any():
        raise MedioTecnicoArticuladoValidationError("Ano ausente ou inválido.")
    result["ano"] = result["ano"].astype(int)
    result["id_municipio"] = result["id_municipio"].astype("string").str.strip()
    if result["id_municipio"].isna().any() or (
        result["id_municipio"] == ""
    ).any():
        raise MedioTecnicoArticuladoValidationError("Código IBGE ausente.")
    if result.duplicated(subset=["ano", "id_municipio"]).any():
        raise MedioTecnicoArticuladoValidationError(
            "Há mais de uma linha para o mesmo ano e código IBGE."
        )
    for column in required_value_columns:
        negative = result[column].notna() & (result[column] < 0)
        if negative.any():
            raise MedioTecnicoArticuladoValidationError(
                f"Valor negativo em {column}; a carga foi rejeitada."
            )
    return result


def validate_public_dependency_reconciliation(frame: pd.DataFrame) -> None:
    """Validate public = federal + state + municipal and total = public + private."""

    public_columns = (
        "mat_ept_nivel_medio_publica",
        "mat_ept_nivel_medio_federal",
        "mat_ept_nivel_medio_estadual",
        "mat_ept_nivel_medio_municipal",
    )
    if all(column in frame.columns for column in public_columns):
        values = frame[list(public_columns)].apply(pd.to_numeric, errors="coerce")
        complete = values.notna().all(axis=1)
        expected = values.loc[
            complete,
            [
                "mat_ept_nivel_medio_federal",
                "mat_ept_nivel_medio_estadual",
                "mat_ept_nivel_medio_municipal",
            ],
        ].sum(axis=1)
        mismatch = expected != values.loc[
            complete, "mat_ept_nivel_medio_publica"
        ]
        if mismatch.any():
            raise MedioTecnicoArticuladoValidationError(
                "A rede pública não reconcilia federal + estadual + municipal."
            )

    total_columns = (
        "mat_ept_nivel_medio_total",
        "mat_ept_nivel_medio_publica",
        "mat_ept_nivel_medio_privada",
    )
    if all(column in frame.columns for column in total_columns):
        values = frame[list(total_columns)].apply(pd.to_numeric, errors="coerce")
        complete = values.notna().all(axis=1)
        mismatch = (
            values.loc[complete, "mat_ept_nivel_medio_publica"]
            + values.loc[complete, "mat_ept_nivel_medio_privada"]
            != values.loc[complete, "mat_ept_nivel_medio_total"]
        )
        if mismatch.any():
            raise MedioTecnicoArticuladoValidationError(
                "O total de EPT não reconcilia rede pública + privada."
            )


def _cycle_identity(row: pd.Series) -> dict[str, object]:
    identity: dict[str, object] = {
        "id_municipio": str(row["id_municipio"]),
    }
    if "municipio" in row.index and pd.notna(row["municipio"]):
        identity["municipio"] = str(row["municipio"])
    return identity


def calculate_public_expansion_series(
    frame: pd.DataFrame,
    *,
    baseline_year: int = BASELINE_YEAR,
) -> pd.DataFrame:
    """Calculate the public share of net EPT expansion from a fixed baseline."""

    total_column = "mat_ept_nivel_medio_total"
    public_column = "mat_ept_nivel_medio_publica"
    prepared = _prepare_cycle_frame(frame, (total_column, public_column))
    validate_public_dependency_reconciliation(prepared)
    baseline = prepared[prepared["ano"] == baseline_year].set_index(
        "id_municipio", drop=False
    )
    post_years = sorted(
        int(year) for year in prepared.loc[prepared["ano"] > baseline_year, "ano"].unique()
    )
    municipality_ids = sorted(str(value) for value in prepared["id_municipio"].unique())
    rows: list[dict[str, object]] = []

    if not post_years:
        for municipality_id in municipality_ids:
            candidates = prepared[prepared["id_municipio"] == municipality_id]
            identity = _cycle_identity(candidates.sort_values("ano").iloc[-1])
            rows.append(
                {
                    **identity,
                    "ano": baseline_year,
                    "valor": pd.NA,
                    "numerador": pd.NA,
                    "denominador": pd.NA,
                    "data_status": "unavailable",
                    "reason_code": "no_post_baseline_observation",
                }
            )
        return pd.DataFrame(rows)

    for year in post_years:
        current = prepared[prepared["ano"] == year].set_index(
            "id_municipio", drop=False
        )
        for municipality_id in municipality_ids:
            identity_row = (
                current.loc[municipality_id]
                if municipality_id in current.index
                else baseline.loc[municipality_id]
                if municipality_id in baseline.index
                else prepared[prepared["id_municipio"] == municipality_id].iloc[-1]
            )
            row: dict[str, object] = {
                **_cycle_identity(identity_row),
                "ano": year,
                "valor": pd.NA,
                "numerador": pd.NA,
                "denominador": pd.NA,
                "data_status": "unavailable",
                "reason_code": None,
            }
            if municipality_id not in baseline.index:
                row["reason_code"] = "baseline_observation_unavailable"
            elif municipality_id not in current.index:
                row["reason_code"] = "current_observation_unavailable"
            else:
                base_row = baseline.loc[municipality_id]
                current_row = current.loc[municipality_id]
                required = (
                    base_row[total_column],
                    base_row[public_column],
                    current_row[total_column],
                    current_row[public_column],
                )
                if any(pd.isna(value) for value in required):
                    row["reason_code"] = "required_component_unavailable"
                else:
                    total_expansion = float(
                        current_row[total_column] - base_row[total_column]
                    )
                    public_expansion = float(
                        current_row[public_column] - base_row[public_column]
                    )
                    row["numerador"] = public_expansion
                    row["denominador"] = total_expansion
                    if total_expansion <= 0:
                        row["data_status"] = "not_applicable"
                        row["reason_code"] = "non_positive_total_expansion"
                    else:
                        row["valor"] = 100.0 * public_expansion / total_expansion
                        row["data_status"] = "available"
            rows.append(row)
    return pd.DataFrame(rows).sort_values(
        ["id_municipio", "ano"]
    ).reset_index(drop=True)


def calculate_subsequent_expansion_series(
    frame: pd.DataFrame,
    *,
    baseline_year: int = BASELINE_YEAR,
) -> pd.DataFrame:
    """Calculate subsequent-course growth from the fixed 2025 baseline."""

    value_column = (
        "mat_profissional_tecnico_subsequente"
        if "mat_profissional_tecnico_subsequente" in frame.columns
        else "mat_subsequente_total"
    )
    prepared = _prepare_cycle_frame(frame, (value_column,))
    baseline = prepared[prepared["ano"] == baseline_year].set_index(
        "id_municipio", drop=False
    )
    post_years = sorted(
        int(year) for year in prepared.loc[prepared["ano"] > baseline_year, "ano"].unique()
    )
    municipality_ids = sorted(str(value) for value in prepared["id_municipio"].unique())
    rows: list[dict[str, object]] = []

    if not post_years:
        for municipality_id in municipality_ids:
            candidates = prepared[prepared["id_municipio"] == municipality_id]
            identity = _cycle_identity(candidates.sort_values("ano").iloc[-1])
            rows.append(
                {
                    **identity,
                    "ano": baseline_year,
                    "valor": pd.NA,
                    "numerador": pd.NA,
                    "denominador": pd.NA,
                    "reference_value": pd.NA,
                    "data_status": "unavailable",
                    "reason_code": "no_post_baseline_observation",
                }
            )
        return pd.DataFrame(rows)

    for year in post_years:
        current = prepared[prepared["ano"] == year].set_index(
            "id_municipio", drop=False
        )
        for municipality_id in municipality_ids:
            identity_row = (
                current.loc[municipality_id]
                if municipality_id in current.index
                else baseline.loc[municipality_id]
                if municipality_id in baseline.index
                else prepared[prepared["id_municipio"] == municipality_id].iloc[-1]
            )
            row: dict[str, object] = {
                **_cycle_identity(identity_row),
                "ano": year,
                "valor": pd.NA,
                "numerador": pd.NA,
                "denominador": pd.NA,
                "reference_value": pd.NA,
                "data_status": "unavailable",
                "reason_code": None,
            }
            if municipality_id not in baseline.index:
                row["reason_code"] = "baseline_observation_unavailable"
            elif municipality_id not in current.index:
                row["reason_code"] = "current_observation_unavailable"
            else:
                base_value = baseline.loc[municipality_id, value_column]
                current_value = current.loc[municipality_id, value_column]
                if pd.isna(base_value):
                    row["reason_code"] = "baseline_observation_unavailable"
                elif pd.isna(current_value):
                    row["reason_code"] = "current_observation_unavailable"
                else:
                    base_value = float(base_value)
                    current_value = float(current_value)
                    row["numerador"] = current_value - base_value
                    row["denominador"] = base_value
                    row["reference_value"] = base_value * 1.60
                    if base_value == 0:
                        row["data_status"] = "not_applicable"
                        row["reason_code"] = "baseline_zero"
                    else:
                        row["valor"] = 100.0 * (current_value - base_value) / base_value
                        row["data_status"] = "available"
            rows.append(row)
    return pd.DataFrame(rows).sort_values(
        ["id_municipio", "ano"]
    ).reset_index(drop=True)


__all__ = [
    "BASELINE_YEAR",
    "DEPENDENCY_COLUMNS",
    "MedioTecnicoArticuladoValidationError",
    "calculate_medio_tecnico_articulado_series",
    "calculate_public_expansion_series",
    "calculate_subsequent_expansion_series",
    "validate_dependency_reconciliation",
    "validate_public_dependency_reconciliation",
]
