"""Matrículas por idade em escolas rurais ativas do Censo Escolar."""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from src.censo_escolar_panel import find_annual_source, sha256_file


SUPPORTED_YEARS = (2023, 2024, 2025)
SOURCE_ENCODING = "latin1"
SOURCE_SEPARATOR = ";"
DEFAULT_CHUNK_SIZE = 75_000
OFFICIAL_URL_TEMPLATE = (
    "https://download.inep.gov.br/dados_abertos/microdados_censo_escolar_{year}.zip"
)

AGE_COLUMNS = {
    "4_5": "QT_MAT_BAS_4_5",
    "6_10": "QT_MAT_BAS_6_10",
    "11_14": "QT_MAT_BAS_11_14",
    "15_17": "QT_MAT_BAS_15_17",
}
REQUIRED_COLUMNS = (
    "NU_ANO_CENSO",
    "SG_UF",
    "CO_MUNICIPIO",
    "TP_SITUACAO_FUNCIONAMENTO",
    "TP_LOCALIZACAO",
    *AGE_COLUMNS.values(),
)
ACTIVE_STATUS = "1"
RURAL_LOCATION = "2"
_MUNICIPAL_CODE_PATTERN = re.compile(r"^\d{7}$")


def _normalise_text_series(series: pd.Series) -> pd.Series:
    return series.astype("string").str.strip()


def _validate_header(path: Path) -> None:
    with path.open("r", encoding=SOURCE_ENCODING) as source:
        header = source.readline().rstrip("\r\n").split(SOURCE_SEPARATOR)
    missing = sorted(set(REQUIRED_COLUMNS) - set(header))
    if missing:
        raise ValueError(f"{path.name}: colunas canônicas ausentes: {missing}.")


def _numeric_age_frame(frame: pd.DataFrame, *, path: Path) -> tuple[pd.DataFrame, pd.Series]:
    numeric = pd.DataFrame(index=frame.index)
    for column in AGE_COLUMNS.values():
        raw = _normalise_text_series(frame[column])
        converted = pd.to_numeric(raw, errors="coerce")
        invalid = raw.notna() & raw.ne("") & converted.isna()
        if invalid.any():
            examples = raw[invalid].drop_duplicates().head(5).tolist()
            raise ValueError(f"{path.name}/{column}: valores não numéricos: {examples}.")
        if converted.lt(0).fillna(False).any():
            raise ValueError(f"{path.name}/{column}: matrículas negativas.")
        if converted.dropna().mod(1).ne(0).any():
            raise ValueError(f"{path.name}/{column}: matrículas fracionárias.")
        numeric[column] = converted
    all_null = numeric.isna().all(axis=1)
    partial_null = numeric.isna().any(axis=1) & ~all_null
    if partial_null.any():
        examples = frame.loc[partial_null, "CO_MUNICIPIO"].head(5).tolist()
        raise ValueError(
            f"{path.name}: {int(partial_null.sum())} escolas rurais ativas possuem "
            f"campos etários parcialmente nulos; exemplos={examples}."
        )
    return numeric, all_null


def aggregate_rural_enrollment_year(
    path: Path,
    *,
    year: int,
    municipality_codes: set[str],
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Agrega as matrículas 4–17 de escolas rurais ativas para um ano."""

    if year not in SUPPORTED_YEARS:
        raise ValueError(f"Ano não suportado: {year}.")
    _validate_header(path)
    totals: defaultdict[str, dict[str, int]] = defaultdict(
        lambda: {key: 0 for key in AGE_COLUMNS}
    )
    observed_municipalities: set[str] = set()
    source_rows = 0
    rs_rows = 0
    active_rural_rows = 0
    all_null_rows = 0

    for chunk in pd.read_csv(
        path,
        sep=SOURCE_SEPARATOR,
        encoding=SOURCE_ENCODING,
        usecols=list(REQUIRED_COLUMNS),
        dtype={column: "string" for column in REQUIRED_COLUMNS},
        chunksize=chunk_size,
        low_memory=False,
    ):
        source_rows += len(chunk)
        year_values = _normalise_text_series(chunk["NU_ANO_CENSO"])
        if not year_values.eq(str(year)).all():
            unexpected = sorted(year_values.dropna().unique().tolist())[:10]
            raise ValueError(
                f"{path.name}: NU_ANO_CENSO divergente de {year}: {unexpected}."
            )
        uf = _normalise_text_series(chunk["SG_UF"]).str.upper()
        rs = chunk.loc[uf.eq("RS")].copy()
        rs_rows += len(rs)
        if rs.empty:
            continue

        codes = _normalise_text_series(rs["CO_MUNICIPIO"])
        invalid_code = ~codes.str.fullmatch(_MUNICIPAL_CODE_PATTERN, na=False)
        if invalid_code.any():
            examples = codes[invalid_code].head(5).tolist()
            raise ValueError(f"{path.name}: códigos IBGE municipais inválidos: {examples}.")
        unexpected_codes = set(codes.dropna().tolist()) - municipality_codes
        if unexpected_codes:
            raise ValueError(
                f"{path.name}: municípios fora do registro canônico: {sorted(unexpected_codes)}."
            )
        rs["CO_MUNICIPIO"] = codes
        status = _normalise_text_series(rs["TP_SITUACAO_FUNCIONAMENTO"])
        location = _normalise_text_series(rs["TP_LOCALIZACAO"])
        selected = rs.loc[status.eq(ACTIVE_STATUS) & location.eq(RURAL_LOCATION)].copy()
        active_rural_rows += len(selected)
        if selected.empty:
            continue
        numeric, all_null = _numeric_age_frame(selected, path=path)
        all_null_rows += int(all_null.sum())
        selected = selected.loc[~all_null].copy()
        numeric = numeric.loc[~all_null]
        if selected.empty:
            continue
        selected_codes = selected["CO_MUNICIPIO"].astype("string")
        observed_municipalities.update(selected_codes.tolist())
        for key, column in AGE_COLUMNS.items():
            grouped = numeric[column].groupby(selected_codes).sum()
            for municipality_id, value in grouped.items():
                totals[str(municipality_id)][key] += int(value)

    source_metadata = {
        "provider": "INEP",
        "survey": "Censo Escolar da Educação Básica",
        "year": year,
        "officialUrl": OFFICIAL_URL_TEMPLATE.format(year=year),
        "sourceFile": path.name,
        "sourceSize": path.stat().st_size,
        "sourceSha256": sha256_file(path),
        "filters": {
            "state": "SG_UF == 'RS'",
            "schoolStatus": "TP_SITUACAO_FUNCIONAMENTO == 1",
            "schoolLocation": "TP_LOCALIZACAO == 2",
        },
        "ageColumns": AGE_COLUMNS,
    }
    rows: list[dict[str, Any]] = []
    for municipality_id in sorted(municipality_codes):
        values = totals[municipality_id]
        origin_status = (
            "observed" if municipality_id in observed_municipalities else "derived_zero"
        )
        for age_group in AGE_COLUMNS:
            rows.append(
                {
                    "ano": year,
                    "id_municipio": municipality_id,
                    "faixa_etaria": age_group,
                    "matriculas": values[age_group],
                    "status_valor": "available",
                    "origem_valor": origin_status,
                    "metadados_fonte": source_metadata,
                }
            )
        rows.append(
            {
                "ano": year,
                "id_municipio": municipality_id,
                "faixa_etaria": "4_17",
                "matriculas": sum(values.values()),
                "status_valor": "available",
                "origem_valor": origin_status,
                "metadados_fonte": source_metadata,
            }
        )
    audit = {
        "year": year,
        "sourceRows": source_rows,
        "rsRows": rs_rows,
        "activeRuralSchoolRows": active_rural_rows,
        "allAgeFieldsNullRowsExcluded": all_null_rows,
        "municipalitiesWithObservedRows": len(observed_municipalities),
        "municipalityRows": len(rows),
        "source": source_metadata,
    }
    return rows, audit


def aggregate_rural_enrollment_years(
    source_dir: Path,
    *,
    years: Iterable[int],
    municipality_codes: set[str],
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Localiza e agrega os arquivos anuais canônicos selecionados."""

    rows: list[dict[str, Any]] = []
    audits: list[dict[str, Any]] = []
    for year in sorted(set(years)):
        path = find_annual_source(source_dir, year)
        annual_rows, audit = aggregate_rural_enrollment_year(
            path,
            year=year,
            municipality_codes=municipality_codes,
            chunk_size=chunk_size,
        )
        rows.extend(annual_rows)
        audits.append(audit)
    expected = len(municipality_codes) * len(set(years)) * 5
    if len(rows) != expected:
        raise ValueError(f"Cobertura anual inválida: esperadas {expected}, obtidas {len(rows)} linhas.")
    return rows, audits
