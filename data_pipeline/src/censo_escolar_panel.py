"""Constrói e audita um painel municipal compacto do Censo Escolar.

O agregado municipal reproduz a regra histórica do projeto SESI: selecionar
somente ``SG_UF == 'RS'`` e agregar todas as linhas por ano e município. A
situação de funcionamento é lida para auditoria, mas não é usada como filtro
porque a carga municipal histórica também não a filtra. A deduplicação por
entidade continua restrita ao diagnóstico de qualidade; nunca altera o
numerador municipal.
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
import os
import re
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from src.pipeline_profiling import profiled_query_call
from typing import Any, Iterable

import pandas as pd


GENERATOR_VERSION = "censo-escolar-panel-v2.0.0"
CANONICAL_PANEL_NAME = "censo_escolar_municipal_2007_2025.csv.gz"
FIRST_YEAR = 2007
LAST_YEAR = 2025
HISTORICAL_FIRST_YEAR = 2014
HISTORICAL_LAST_YEAR = 2025
EXPECTED_MUNICIPALITIES_PER_YEAR = 497
EXPECTED_MUNICIPALITIES_2007_2012 = 496
EXPECTED_MUNICIPALITIES_2013_2025 = 497
EXPECTED_PANEL_ROWS_LEGACY_497 = 9_443
EXPECTED_PANEL_ROWS = 9_437
EXPECTED_HISTORICAL_ROWS = 5_964
EXPECTED_RECONCILIATION_POINTS = 41_748
SOURCE_ENCODING = "latin1"
SOURCE_SEPARATOR = ";"
DEFAULT_CHUNK_SIZE = 100_000
UF_FILTER = "RS"
PINTO_BANDEIRA_CODE = "4314548"
BENTO_GONCALVES_CODE = "4302105"

MUNICIPAL_UNIVERSE_BY_YEAR = {
    year: (
        EXPECTED_MUNICIPALITIES_2007_2012
        if year <= 2012
        else EXPECTED_MUNICIPALITIES_2013_2025
    )
    for year in range(FIRST_YEAR, LAST_YEAR + 1)
}
TERRITORIAL_BREAKS_FOR_BACKTESTING = [
    {
        "year": 2013,
        "municipalities": [
            {"codigo_municipio": BENTO_GONCALVES_CODE, "nome": "Bento Gonçalves"},
            {"codigo_municipio": PINTO_BANDEIRA_CODE, "nome": "Pinto Bandeira"},
        ],
        "note": "Possível quebra territorial; não aplicar ajuste nesta rodada.",
    }
]

REQUIRED_SOURCE_COLUMNS = [
    "NU_ANO_CENSO",
    "SG_UF",
    "CO_MUNICIPIO",
    "CO_ENTIDADE",
    "TP_SITUACAO_FUNCIONAMENTO",
    "QT_MAT_INF_PRE",
    "QT_MAT_BAS_0_3",
    "QT_MAT_BAS_4_5",
    "QT_MAT_BAS_6_10",
    "QT_MAT_BAS_11_14",
    "QT_MAT_BAS_15_17",
]
VALUE_SOURCE_COLUMNS = [
    "QT_MAT_INF_PRE",
    "QT_MAT_BAS_0_3",
    "QT_MAT_BAS_4_5",
    "QT_MAT_BAS_6_10",
    "QT_MAT_BAS_11_14",
    "QT_MAT_BAS_15_17",
]
PANEL_VALUE_COLUMNS = [
    "mat_infantil_pre",
    "mat_basico_0_3",
    "mat_basico_4_5",
    "mat_basico_6_10",
    "mat_basico_11_14",
    "mat_basico_15_17",
]
PANEL_COLUMNS = [
    "ano",
    "codigo_municipio",
    *PANEL_VALUE_COLUMNS,
]
INDICATOR_NAMES = [
    "creche",
    "pre_escola",
    "basico_6_17",
    "basico_15_17",
    "basico_0_5",
    "basico_4_17",
    "basico_6_14",
]
INDICATOR_FORMULAS = {
    "creche": {
        "columns": ["mat_basico_0_3"],
        "expression": "mat_basico_0_3",
    },
    "pre_escola": {
        "columns": ["mat_infantil_pre"],
        "expression": "mat_infantil_pre",
    },
    "basico_6_17": {
        "columns": ["mat_basico_6_10", "mat_basico_11_14", "mat_basico_15_17"],
        "expression": "mat_basico_6_10 + mat_basico_11_14 + mat_basico_15_17",
    },
    "basico_15_17": {
        "columns": ["mat_basico_15_17"],
        "expression": "mat_basico_15_17",
    },
    "basico_0_5": {
        "columns": ["mat_basico_0_3", "mat_basico_4_5"],
        "expression": "mat_basico_0_3 + mat_basico_4_5",
    },
    "basico_4_17": {
        "columns": [
            "mat_basico_4_5",
            "mat_basico_6_10",
            "mat_basico_11_14",
            "mat_basico_15_17",
        ],
        "expression": "mat_basico_4_5 + mat_basico_6_10 + mat_basico_11_14 + mat_basico_15_17",
    },
    "basico_6_14": {
        "columns": ["mat_basico_6_10", "mat_basico_11_14"],
        "expression": "mat_basico_6_10 + mat_basico_11_14",
    },
}

_MUNICIPAL_CODE_PATTERN = re.compile(r"^43\d{5}$")


def utc_now() -> str:
    """Return a stable, explicit UTC timestamp for manifests."""

    return datetime.now(timezone.utc).isoformat()


def normalize_code_series(series: pd.Series) -> pd.Series:
    """Normalize IBGE/entity codes without converting them to floating point."""

    normalized = series.astype("string").str.strip()
    normalized = normalized.str.replace(r"\.0+$", "", regex=True)
    normalized = normalized.replace({"": pd.NA, "nan": pd.NA, "None": pd.NA})
    return normalized


def normalize_source_chunk(chunk: pd.DataFrame, expected_year: int) -> pd.DataFrame:
    """Select canonical fields and normalize their types.

    The function deliberately does not look for ``*_REF_31_03`` aliases. The
    canonical fields are required in every annual file, including 2025.
    """

    missing = sorted(set(REQUIRED_SOURCE_COLUMNS) - set(chunk.columns))
    if missing:
        raise ValueError(f"Colunas canônicas ausentes: {missing}")

    result = chunk[REQUIRED_SOURCE_COLUMNS].copy()
    year = pd.to_numeric(result["NU_ANO_CENSO"], errors="coerce")
    if year.isna().any() or not year.eq(expected_year).all():
        values = sorted(
            str(value)
            for value in result.loc[year.notna(), "NU_ANO_CENSO"].astype("string").unique()
        )
        raise ValueError(
            f"NU_ANO_CENSO divergente em {expected_year}: valores={values[:10]}"
        )
    result["NU_ANO_CENSO"] = year.astype("int64")
    result["SG_UF"] = result["SG_UF"].astype("string").str.strip().str.upper()
    result["CO_MUNICIPIO"] = normalize_code_series(result["CO_MUNICIPIO"])
    result["CO_ENTIDADE"] = normalize_code_series(result["CO_ENTIDADE"])
    result["TP_SITUACAO_FUNCIONAMENTO"] = normalize_code_series(
        result["TP_SITUACAO_FUNCIONAMENTO"]
    )

    for column in VALUE_SOURCE_COLUMNS:
        raw = result[column].astype("string").str.strip()
        numeric = pd.to_numeric(raw, errors="coerce")
        invalid = raw.notna() & raw.ne("") & numeric.isna()
        if invalid.any():
            examples = raw[invalid].drop_duplicates().head(5).tolist()
            raise ValueError(f"{column} contém valores não numéricos: {examples}")
        if numeric.lt(0).fillna(False).any():
            examples = numeric[numeric.lt(0).fillna(False)].head(5).tolist()
            raise ValueError(f"{column} contém valores negativos: {examples}")
        result[column] = numeric

    return result


def read_source_header(path: Path) -> list[str]:
    """Read only the annual CSV header."""

    with path.open("r", encoding=SOURCE_ENCODING, newline="") as source:
        header = next(csv.reader(source, delimiter=SOURCE_SEPARATOR))
    if len(header) != len(set(header)):
        duplicates = sorted(
            column for column, count in Counter(header).items() if count > 1
        )
        raise ValueError(f"Cabeçalho duplicado em {path.name}: {duplicates}")
    return header


def find_annual_source(source_dir: Path, year: int) -> Path:
    """Find exactly one canonical annual CSV, case-insensitively."""

    candidates = sorted(
        path
        for path in source_dir.iterdir()
        if path.is_file()
        and path.name.lower() == f"microdados_ed_basica_{year}.csv"
    )
    if len(candidates) != 1:
        raise FileNotFoundError(
            f"Esperado exatamente um CSV canônico para {year}; encontrados {len(candidates)}."
        )
    return candidates[0]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def schema_change(previous: list[str] | None, current: list[str]) -> dict[str, Any]:
    """Describe annual schema drift relative to the previous file."""

    if previous is None:
        return {
            "comparison": "baseline",
            "added_columns": current,
            "removed_columns": [],
        }
    previous_set = set(previous)
    current_set = set(current)
    return {
        "comparison": "previous_year",
        "added_columns": sorted(current_set - previous_set),
        "removed_columns": sorted(previous_set - current_set),
    }


def _counter_from_series(series: pd.Series) -> Counter[str]:
    values = series.astype("string").fillna("<NA>")
    return Counter({str(key): int(value) for key, value in values.value_counts().items()})


def _add_counter(target: Counter[str], source: Counter[str]) -> None:
    target.update(source)


def _entity_audit_update(
    frame: pd.DataFrame,
    entity_counts: Counter[str],
    first_signatures: dict[str, int],
    signatures: dict[str, set[int]],
) -> None:
    """Track duplicate entities without changing the municipal aggregate."""

    usable = frame["CO_ENTIDADE"].notna()
    if not usable.any():
        return
    subset = frame.loc[
        usable,
        [
            "CO_ENTIDADE",
            "CO_MUNICIPIO",
            "TP_SITUACAO_FUNCIONAMENTO",
            *VALUE_SOURCE_COLUMNS,
        ],
    ].astype("string").fillna("<NA>")
    row_hashes = pd.util.hash_pandas_object(subset, index=False)
    for entity, row_hash in zip(subset["CO_ENTIDADE"].tolist(), row_hashes.tolist()):
        entity_key = str(entity)
        signature = int(row_hash)
        entity_counts[entity_key] += 1
        if entity_key not in first_signatures:
            first_signatures[entity_key] = signature
            continue
        if entity_counts[entity_key] == 2:
            signatures[entity_key] = {first_signatures[entity_key], signature}
        else:
            signatures.setdefault(entity_key, set()).add(signature)


def _validate_integer_counts(frame: pd.DataFrame, columns: Iterable[str]) -> None:
    for column in columns:
        values = pd.to_numeric(frame[column], errors="coerce")
        if values.isna().any():
            raise ValueError(f"{column} contém valores nulos no painel agregado.")
        if values.lt(0).any():
            raise ValueError(f"{column} contém valores negativos no painel agregado.")
        if values.mod(1).ne(0).any():
            raise ValueError(f"{column} contém valores fracionários no painel agregado.")


def validate_panel(
    panel: pd.DataFrame,
    *,
    expected_years: Iterable[int] = range(FIRST_YEAR, LAST_YEAR + 1),
    expected_municipalities: int | None = None,
    expected_municipalities_by_year: dict[int, int] | None = None,
) -> dict[str, Any]:
    """Validate grain, coverage, identifiers and count domains."""

    expected_year_values = sorted(int(year) for year in expected_years)
    if not expected_year_values:
        raise ValueError("O painel precisa conter pelo menos um ano esperado.")
    if expected_municipalities is not None and expected_municipalities_by_year is not None:
        raise ValueError("Informe expected_municipalities ou expected_municipalities_by_year, não ambos.")
    if expected_municipalities_by_year is None:
        expected_municipalities_by_year = {
            year: (
                int(expected_municipalities)
                if expected_municipalities is not None
                else int(MUNICIPAL_UNIVERSE_BY_YEAR.get(year, EXPECTED_MUNICIPALITIES_PER_YEAR))
            )
            for year in expected_year_values
        }
    else:
        expected_municipalities_by_year = {
            int(year): int(count)
            for year, count in expected_municipalities_by_year.items()
            if int(year) in expected_year_values
        }
        missing_expected_counts = sorted(
            set(expected_year_values) - set(expected_municipalities_by_year)
        )
        if missing_expected_counts:
            raise ValueError(
                f"Sem expectativa municipal para os anos: {missing_expected_counts}"
            )

    missing_columns = sorted(set(PANEL_COLUMNS) - set(panel.columns))
    if missing_columns:
        raise ValueError(f"Colunas ausentes no painel: {missing_columns}")

    result = panel.copy()
    result["ano"] = pd.to_numeric(result["ano"], errors="coerce")
    result["codigo_municipio"] = normalize_code_series(result["codigo_municipio"])
    if result["ano"].isna().any():
        raise ValueError("O painel contém ano nulo ou inválido.")
    if result["codigo_municipio"].isna().any():
        raise ValueError("O painel contém código municipal nulo ou inválido.")

    invalid_codes = sorted(
        result.loc[
            ~result["codigo_municipio"].str.fullmatch(_MUNICIPAL_CODE_PATTERN.pattern),
            "codigo_municipio",
        ]
        .drop_duplicates()
        .astype(str)
        .tolist()
    )
    if invalid_codes:
        raise ValueError(f"Códigos municipais inválidos: {invalid_codes[:10]}")

    duplicate_keys = result.duplicated(["ano", "codigo_municipio"], keep=False)
    if duplicate_keys.any():
        examples = (
            result.loc[duplicate_keys, ["ano", "codigo_municipio"]]
            .drop_duplicates()
            .head(10)
            .to_dict("records")
        )
        raise ValueError(f"Duplicidade no grão ano/município: {examples}")

    _validate_integer_counts(result, PANEL_VALUE_COLUMNS)
    actual_years = sorted(int(year) for year in result["ano"].unique())
    missing_years = sorted(set(expected_year_values) - set(actual_years))
    extra_years = sorted(set(actual_years) - set(expected_year_values))
    universe = sorted(result["codigo_municipio"].unique().tolist())
    coverage = result.groupby("ano")["codigo_municipio"].nunique().to_dict()
    coverage = {str(int(year)): int(count) for year, count in coverage.items()}
    structural_absences = {
        str(year): [PINTO_BANDEIRA_CODE]
        for year in expected_year_values
        if year < 2013 and PINTO_BANDEIRA_CODE in universe
    }
    missing_municipalities = {
        str(year): sorted(
            (
                set(universe)
                - set(result.loc[result["ano"].eq(year), "codigo_municipio"].tolist())
            )
            - set(structural_absences.get(str(year), []))
        )
        for year in expected_year_values
        if year in set(actual_years)
        and (
            set(universe)
            - set(result.loc[result["ano"].eq(year), "codigo_municipio"].tolist())
            - set(structural_absences.get(str(year), []))
        )
    }
    expected_coverage = {
        str(year): int(expected_municipalities_by_year[year])
        for year in expected_year_values
    }
    coverage_mismatches = {
        year: {
            "expected": expected_coverage[year],
            "actual": coverage.get(year, 0),
        }
        for year in expected_coverage
        if coverage.get(year, 0) != expected_coverage[year]
    }
    expected_rows = sum(expected_coverage.values())
    row_count_mismatch = len(result) != expected_rows
    legacy_row_delta = int(len(result) - EXPECTED_PANEL_ROWS_LEGACY_497)
    return {
        "status": "ok"
        if not missing_years
        and not extra_years
        and not coverage_mismatches
        and not row_count_mismatch
        else "warning",
        "expected_years": expected_year_values,
        "actual_years": actual_years,
        "missing_years": missing_years,
        "extra_years": extra_years,
        "expected_municipalities_per_year": expected_coverage,
        "expected_municipalities_by_year": expected_coverage,
        "municipality_universe_count": len(universe),
        "coverage_by_year": coverage,
        "coverage_mismatches_by_year": coverage_mismatches,
        "missing_municipalities_by_year": missing_municipalities,
        "structural_absences_by_year": structural_absences,
        "expected_rows": expected_rows,
        "legacy_expected_rows_497": EXPECTED_PANEL_ROWS_LEGACY_497,
        "actual_rows": int(len(result)),
        "row_delta": int(len(result) - expected_rows),
        "legacy_row_delta_497": legacy_row_delta,
        "invalid_code_count": len(invalid_codes),
    }


def _aggregate_year(
    path: Path,
    year: int,
    *,
    chunk_size: int,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    header = read_source_header(path)
    missing = sorted(set(REQUIRED_SOURCE_COLUMNS) - set(header))
    if missing:
        aliases = sorted(
            column for column in header if column.endswith("_REF_31_03")
        )
        suffix_note = f"; aliases _REF_31_03 presentes: {aliases[:10]}" if aliases else ""
        raise ValueError(
            f"{path.name}: colunas canônicas ausentes: {missing}{suffix_note}"
        )

    grouped_parts: list[pd.DataFrame] = []
    rows_read = 0
    rows_rs = 0
    rows_without_municipality = 0
    missing_value_counts: Counter[str] = Counter()
    status_counts: Counter[str] = Counter()
    empty_value_audit_by_status: dict[str, Counter[str]] = {}
    entity_counts: Counter[str] = Counter()
    first_signatures: dict[str, int] = {}
    signatures: dict[str, set[int]] = {}

    for chunk in pd.read_csv(
        path,
        sep=SOURCE_SEPARATOR,
        encoding=SOURCE_ENCODING,
        usecols=REQUIRED_SOURCE_COLUMNS,
        dtype="string",
        chunksize=chunk_size,
        low_memory=False,
    ):
        rows_read += len(chunk)
        normalized = normalize_source_chunk(chunk, year)
        rs = normalized.loc[normalized["SG_UF"].eq(UF_FILTER)].copy()
        rows_rs += len(rs)
        _add_counter(status_counts, _counter_from_series(rs["TP_SITUACAO_FUNCIONAMENTO"]))
        _entity_audit_update(rs, entity_counts, first_signatures, signatures)

        missing_cells = rs[VALUE_SOURCE_COLUMNS].isna()
        status_values = rs["TP_SITUACAO_FUNCIONAMENTO"].astype("string").fillna("<NA>")
        for status in status_values.drop_duplicates().tolist():
            status_key = str(status)
            status_rows = status_values.eq(status)
            status_missing = missing_cells.loc[status_rows]
            status_audit = empty_value_audit_by_status.setdefault(
                status_key,
                Counter(
                    {
                        "lines_six_empty": 0,
                        "lines_partial_empty": 0,
                        "lines_complete": 0,
                    }
                ),
            )
            six_empty = status_missing.all(axis=1)
            partial_empty = status_missing.any(axis=1) & ~six_empty
            status_audit["lines_six_empty"] += int(six_empty.sum())
            status_audit["lines_partial_empty"] += int(partial_empty.sum())
            status_audit["lines_complete"] += int((~status_missing.any(axis=1)).sum())

        for column in VALUE_SOURCE_COLUMNS:
            missing_value_counts[column] += int(rs[column].isna().sum())

        usable = rs["CO_MUNICIPIO"].notna()
        rows_without_municipality += int((~usable).sum())
        if not usable.any():
            continue

        selected = rs.loc[usable, ["CO_MUNICIPIO", *VALUE_SOURCE_COLUMNS]].copy()
        invalid_codes = selected.loc[
            ~selected["CO_MUNICIPIO"].str.fullmatch(_MUNICIPAL_CODE_PATTERN.pattern),
            "CO_MUNICIPIO",
        ].dropna()
        if not invalid_codes.empty:
            examples = sorted(invalid_codes.drop_duplicates().astype(str).tolist())[:10]
            raise ValueError(f"{path.name}: códigos municipais inválidos: {examples}")

        values = (
            selected.groupby("CO_MUNICIPIO", as_index=False)[VALUE_SOURCE_COLUMNS]
            .sum(min_count=1)
            .rename(
                columns={
                    "CO_MUNICIPIO": "codigo_municipio",
                    "QT_MAT_INF_PRE": "mat_infantil_pre",
                    "QT_MAT_BAS_0_3": "mat_basico_0_3",
                    "QT_MAT_BAS_4_5": "mat_basico_4_5",
                    "QT_MAT_BAS_6_10": "mat_basico_6_10",
                    "QT_MAT_BAS_11_14": "mat_basico_11_14",
                    "QT_MAT_BAS_15_17": "mat_basico_15_17",
                }
            )
        )
        grouped_parts.append(values)

    if not grouped_parts:
        aggregate = pd.DataFrame(columns=["codigo_municipio", *PANEL_VALUE_COLUMNS])
    else:
        aggregate = pd.concat(grouped_parts, ignore_index=True)
        aggregate = (
            aggregate.groupby("codigo_municipio", as_index=False)[
                PANEL_VALUE_COLUMNS
            ]
            .sum(min_count=1)
        )
    aggregate.insert(0, "ano", year)

    duplicate_keys = sorted(
        entity for entity, count in entity_counts.items() if count > 1
    )
    conflicting_keys = sorted(
        entity for entity in duplicate_keys if len(signatures.get(entity, set())) > 1
    )
    empty_audit = {
        status: dict(sorted(counts.items()))
        for status, counts in sorted(empty_value_audit_by_status.items())
    }
    source_metadata = {
        "path": f"external/censo_escolar/{path.name}",
        "name": path.name,
        "expected_year": year,
        "detected_years": [year],
        "size_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "rows_read": rows_read,
        "rows_rs": rows_rs,
        "rows_without_municipality": rows_without_municipality,
        "rows_used": rows_rs - rows_without_municipality,
        "columns_used": REQUIRED_SOURCE_COLUMNS,
        "header_columns_count": len(header),
        "status_filter": None,
        "included_situacao_funcionamento": dict(sorted(status_counts.items())),
        "missing_value_cells_in_rs": dict(sorted(missing_value_counts.items())),
        "empty_value_audit_by_status": empty_audit,
        "empty_value_audit_totals": {
            key: int(sum(entry.get(key, 0) for entry in empty_audit.values()))
            for key in ["lines_six_empty", "lines_partial_empty", "lines_complete"]
        },
        "entity_count_audit": {
            "panel_column": None,
            "semantics": "CO_ENTIDADE distinta auditada; não usada para deduplicar o SUM municipal.",
            "distinct_co_entidade_in_rs": len(entity_counts),
            "rows_with_co_entidade_in_rs": int(sum(entity_counts.values())),
        },
        "duplicate_entity_keys_count": len(duplicate_keys),
        "duplicate_entity_rows_excess_count": int(
            sum(entity_counts[entity] - 1 for entity in duplicate_keys)
        ),
        "conflicting_duplicate_entity_keys_count": len(conflicting_keys),
        "duplicate_entity_examples": duplicate_keys[:10],
        "conflicting_duplicate_entity_examples": conflicting_keys[:10],
        "header": header,
    }
    return aggregate, source_metadata


def _atomic_write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, suffix=".tmp", delete=False) as temporary:
        temporary.write(payload)
        temporary_path = Path(temporary.name)
    os.replace(temporary_path, path)


def write_panel_csv_gzip(panel: pd.DataFrame, path: Path) -> None:
    """Write a compact UTF-8 CSV.gz atomically without adding a dependency."""

    csv_bytes = panel[PANEL_COLUMNS].to_csv(index=False).encode("utf-8")
    _atomic_write_bytes(path, gzip.compress(csv_bytes, mtime=0))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    encoded = (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )
    _atomic_write_bytes(path, encoded)


def write_csv(path: Path, frame: pd.DataFrame) -> None:
    _atomic_write_bytes(path, frame.to_csv(index=False).encode("utf-8"))


def read_panel(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, compression="gzip", dtype={"codigo_municipio": "string"})


def portable_manifest_path(path: Path, repo_root: Path | None = None) -> str:
    """Return a versionable relative path without leaking the local machine."""

    root = (repo_root or Path(__file__).resolve().parents[2]).resolve()
    candidate = path.resolve()
    try:
        return candidate.relative_to(root).as_posix()
    except ValueError:
        return path.name


def validate_manifest(
    manifest: dict[str, Any],
    *,
    panel_path: Path | None = None,
) -> dict[str, Any]:
    """Validate the portable manifest and, when supplied, its panel artifact."""

    required = {"generator_version", "generated_at_utc", "panel", "sources", "schema_changes"}
    missing = sorted(required - set(manifest))
    if missing:
        raise ValueError(f"Manifesto sem campos: {missing}")
    panel_metadata = manifest["panel"]
    if panel_metadata.get("columns") != PANEL_COLUMNS:
        raise ValueError("Manifesto não descreve as colunas canônicas do painel.")
    if "qtd_entidades" in panel_metadata.get("columns", []):
        raise ValueError("qtd_entidades não pode aparecer no painel compacto.")

    def check_portable_paths(value: Any, key: str = "") -> None:
        if isinstance(value, dict):
            for child_key, child_value in value.items():
                check_portable_paths(child_value, str(child_key))
        elif isinstance(value, list):
            for child_value in value:
                check_portable_paths(child_value, key)
        elif isinstance(value, str) and (
            key == "path"
            or key.endswith("_path")
            or key in {"manifest", "directory", "audit_report", "reconciliation_status"}
        ):
            if Path(value).is_absolute() or re.match(r"^[A-Za-z]:[\\/]", value):
                raise ValueError(f"Caminho absoluto no manifesto: {value}")

    check_portable_paths(manifest)
    expected_source_years = sorted(
        int(year) for year in panel_metadata.get("validation", {}).get("expected_years", [])
    )
    source_years = sorted(int(source.get("expected_year")) for source in manifest["sources"])
    if source_years != expected_source_years:
        raise ValueError(
            f"Anos das fontes divergem da validação do painel: fontes={source_years}, "
            f"painel={expected_source_years}"
        )
    if len(source_years) != len(set(source_years)):
        raise ValueError("Há anos de fonte duplicados no manifesto.")
    for source in manifest["sources"]:
        for key in ["name", "path", "expected_year", "size_bytes", "sha256", "columns_used"]:
            if key not in source:
                raise ValueError(f"Fonte do manifesto sem {key}: {source.get('name')}")
        if Path(str(source["path"])).is_absolute() or re.match(r"^[A-Za-z]:[\\/]", str(source["path"])):
            raise ValueError(f"Caminho absoluto na fonte do manifesto: {source['path']}")
        if len(str(source["sha256"])) != 64:
            raise ValueError(f"SHA-256 inválido na fonte {source['name']}.")
        if source["columns_used"] != REQUIRED_SOURCE_COLUMNS:
            raise ValueError(f"Colunas usadas divergentes na fonte {source['name']}.")
        if int(source["size_bytes"]) <= 0:
            raise ValueError(f"Tamanho inválido na fonte {source['name']}.")
        if int(source["expected_year"]) not in [
            int(year) for year in source.get("detected_years", [])
        ]:
            raise ValueError(f"Ano não detectado na fonte {source['name']}.")
    for key in ["path", "name"]:
        if key not in panel_metadata:
            raise ValueError(f"Metadado do painel sem {key}.")
    checks = {"sources": len(manifest["sources"]), "panel_artifact_checked": panel_path is not None}
    if panel_path is not None:
        if not panel_path.exists():
            raise ValueError(f"Painel do manifesto não existe: {panel_path.name}")
        actual_size = panel_path.stat().st_size
        actual_hash = sha256_file(panel_path)
        actual_rows = len(read_panel(panel_path))
        if int(panel_metadata["size_bytes"]) != actual_size:
            raise ValueError("Tamanho do painel diverge do manifesto.")
        if panel_metadata["sha256"] != actual_hash:
            raise ValueError("SHA-256 do painel diverge do manifesto.")
        if int(panel_metadata["rows"]) != actual_rows:
            raise ValueError("Número de linhas do painel diverge do manifesto.")
        checks.update({"panel_rows": actual_rows, "panel_size_bytes": actual_size})
    return checks


def load_sync_provenance(
    repo_root: Path,
    source_entries: list[dict[str, Any]],
) -> dict[str, Any]:
    """Attach safe, portable provenance from the microdata sync manifest."""

    manifest_path = repo_root / "data_pipeline" / "data" / "censo_escolar_acquisition" / "manifest.json"
    result: dict[str, Any] = {
        "script": "data_pipeline/scripts/sync_censo_escolar_microdata.py",
        "manifest": "data_pipeline/data/censo_escolar_acquisition/manifest.json",
        "status": "not_found",
        "entries": {},
    }
    if not manifest_path.exists():
        return result
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    result["status"] = "loaded"
    for source in source_entries:
        year_key = str(source["expected_year"])
        registered = payload.get("sources", {}).get(year_key)
        if not registered:
            result["entries"][year_key] = {"status": "not_registered"}
            continue
        registered_file = str(registered.get("file", "")).replace("\\", "/")
        result["entries"][year_key] = {
            "status": registered.get("status", "unknown"),
            "file_name": registered_file.rsplit("/", 1)[-1],
            "official_url": registered.get("officialUrl"),
            "acquired_at": registered.get("acquiredAt"),
            "audited_at": registered.get("auditedAt"),
            "size_bytes": registered.get("size"),
            "sha256": registered.get("sha256"),
            "matches_source": (
                registered.get("size") == source.get("size_bytes")
                and registered.get("sha256") == source.get("sha256")
            ),
        }
    return result


def derive_indicators(panel: pd.DataFrame) -> pd.DataFrame:
    """Derive the seven current numerators without filling missing values."""

    missing = sorted(set(PANEL_VALUE_COLUMNS) - set(panel.columns))
    if missing:
        raise ValueError(f"Colunas de matrícula ausentes para derivação: {missing}")
    result = panel[["ano", "codigo_municipio"]].copy()
    for column in PANEL_VALUE_COLUMNS:
        result[column] = pd.to_numeric(panel[column], errors="coerce")
    result["creche"] = result["mat_basico_0_3"]
    result["pre_escola"] = result["mat_infantil_pre"]
    result["basico_6_17"] = result[
        ["mat_basico_6_10", "mat_basico_11_14", "mat_basico_15_17"]
    ].sum(axis=1, min_count=3)
    result["basico_15_17"] = result["mat_basico_15_17"]
    result["basico_0_5"] = result[["mat_basico_0_3", "mat_basico_4_5"]].sum(
        axis=1, min_count=2
    )
    result["basico_4_17"] = result[
        [
            "mat_basico_4_5",
            "mat_basico_6_10",
            "mat_basico_11_14",
            "mat_basico_15_17",
        ]
    ].sum(axis=1, min_count=4)
    result["basico_6_14"] = result[["mat_basico_6_10", "mat_basico_11_14"]].sum(
        axis=1, min_count=2
    )
    return result[["ano", "codigo_municipio", *INDICATOR_NAMES]]


def build_panel(
    source_dir: Path,
    output_path: Path,
    *,
    years: Iterable[int] = range(FIRST_YEAR, LAST_YEAR + 1),
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Build the compact panel and return it with source audit metadata."""

    if chunk_size <= 0:
        raise ValueError("chunk_size deve ser positivo")
    source_dir = source_dir.resolve()
    selected_year_values = sorted(set(int(value) for value in years))
    if output_path.name == CANONICAL_PANEL_NAME and selected_year_values != list(
        range(FIRST_YEAR, LAST_YEAR + 1)
    ):
        raise ValueError(
            f"{CANONICAL_PANEL_NAME} só pode ser gerado com os 19 anos completos."
        )
    panel_parts: list[pd.DataFrame] = []
    source_entries: list[dict[str, Any]] = []
    schema_entries: list[dict[str, Any]] = []
    previous_header: list[str] | None = None

    for year in selected_year_values:
        path = find_annual_source(source_dir, year)
        aggregate, metadata = _aggregate_year(path, year, chunk_size=chunk_size)
        change = schema_change(previous_header, metadata.pop("header"))
        metadata["schema_change"] = change
        schema_entries.append(
            {
                "year": year,
                "header_columns_count": metadata["header_columns_count"],
                **change,
            }
        )
        source_entries.append(metadata)
        panel_parts.append(aggregate)
        previous_header = read_source_header(path)

    if not panel_parts:
        raise ValueError("Nenhum ano foi selecionado para o painel.")
    panel = pd.concat(panel_parts, ignore_index=True)
    panel = panel.sort_values(["ano", "codigo_municipio"]).reset_index(drop=True)
    panel["ano"] = pd.to_numeric(panel["ano"], errors="raise").astype("int64")
    panel["codigo_municipio"] = normalize_code_series(panel["codigo_municipio"])
    for column in PANEL_VALUE_COLUMNS:
        panel[column] = pd.to_numeric(panel[column], errors="raise")
    validation = validate_panel(panel, expected_years=selected_year_values)
    write_panel_csv_gzip(panel, output_path)

    panel_metadata = {
        "path": output_path.name,
        "name": output_path.name,
        "format": "csv.gz",
        "size_bytes": output_path.stat().st_size,
        "sha256": sha256_file(output_path),
        "columns": PANEL_COLUMNS,
        "rows": int(len(panel)),
        "validation": validation,
    }
    metadata = {
        "generator_version": GENERATOR_VERSION,
        "generated_at_utc": utc_now(),
        "source_directory": "external:censo_escolar",
        "source_filter": {
            "SG_UF": UF_FILTER,
            "TP_SITUACAO_FUNCIONAMENTO": "all values included; audit only",
            "aggregation_grain": ["NU_ANO_CENSO", "CO_MUNICIPIO"],
            "municipal_history_note": "The current municipal load does not filter operating status and aggregates all RS rows.",
            "sum_semantics": "SUM over source rows after SG_UF == 'RS'; missing values are not imputed and pandas sum(min_count=1) preserves an all-empty group as null before validation.",
        },
        "municipal_universe": {
            "expected_municipalities_by_year": {
                str(year): count
                for year, count in MUNICIPAL_UNIVERSE_BY_YEAR.items()
                if year in set(int(value) for value in years)
            },
            "expected_rows_for_selected_years": validation["expected_rows"],
            "legacy_497_rows_for_full_period": EXPECTED_PANEL_ROWS_LEGACY_497,
            "pinto_bandeira": {
                "codigo_municipio": PINTO_BANDEIRA_CODE,
                "nome": "Pinto Bandeira",
                "starts_in_year": 2013,
                "prior_years_not_imputed": True,
            },
            "territorial_breaks_for_future_backtesting": TERRITORIAL_BREAKS_FOR_BACKTESTING,
        },
        "panel": panel_metadata,
        "sources": source_entries,
        "schema_changes": schema_entries,
        "indicator_formulas": INDICATOR_FORMULAS,
        "source_format": {
            "separator": SOURCE_SEPARATOR,
            "encoding": SOURCE_ENCODING,
            "read_in_chunks": True,
            "usecols": REQUIRED_SOURCE_COLUMNS,
            "chunk_size": chunk_size,
        },
    }
    return panel, metadata


HISTORICAL_NUMERATOR_QUERY = """
SELECT
    ano,
    id_municipio::text AS codigo_municipio,
    SUM(mat_basico_0_3) AS creche,
    SUM(mat_infantil_pre) AS pre_escola,
    SUM(mat_basico_6_10) AS basico_6_10,
    SUM(mat_basico_11_14) AS basico_11_14,
    SUM(mat_basico_15_17) AS basico_15_17,
    SUM(mat_basico_4_5) AS basico_4_5
FROM censo
WHERE ano BETWEEN :start_year AND :end_year
GROUP BY ano, id_municipio
ORDER BY ano, codigo_municipio
""".strip()


def load_historical_from_postgres(
    env_path: Path,
    *,
    start_year: int = HISTORICAL_FIRST_YEAR,
    end_year: int = HISTORICAL_LAST_YEAR,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Read the current platform's municipal history without mutating the DB."""

    from dotenv import load_dotenv
    from sqlalchemy import create_engine, text
    from sqlalchemy.engine import URL

    load_dotenv(env_path)
    required = ["DB_HOST", "DB_PORT", "DB_BANCO", "DB_USUARIO", "DB_SENHA"]
    missing = [key for key in required if not os.environ.get(key)]
    if missing:
        raise RuntimeError(f"Variáveis de conexão ausentes: {missing}")
    url = URL.create(
        "postgresql+psycopg2",
        username=os.environ["DB_USUARIO"],
        password=os.environ["DB_SENHA"],
        host=os.environ["DB_HOST"],
        port=int(os.environ["DB_PORT"]),
        database=os.environ["DB_BANCO"],
    )
    engine = create_engine(url, pool_pre_ping=True)
    try:
        history = profiled_query_call(
            "censo_escolar.historical_numerators",
            lambda: pd.read_sql_query(
                text(HISTORICAL_NUMERATOR_QUERY),
                engine,
                params={"start_year": start_year, "end_year": end_year},
            ),
            metadata={
                "datasetId": "censo_escolar_historical_numerators",
                "backend": "postgres_local",
                "parametersBound": True,
            },
        )
    finally:
        engine.dispose()

    history["ano"] = pd.to_numeric(history["ano"], errors="raise").astype("int64")
    history["codigo_municipio"] = normalize_code_series(history["codigo_municipio"])
    for column in [
        "creche",
        "pre_escola",
        "basico_6_10",
        "basico_11_14",
        "basico_15_17",
        "basico_4_5",
    ]:
        history[column] = pd.to_numeric(history[column], errors="coerce")
    history["basico_6_17"] = history[
        ["basico_6_10", "basico_11_14", "basico_15_17"]
    ].sum(axis=1, min_count=3)
    history["basico_0_5"] = history[["creche", "basico_4_5"]].sum(axis=1, min_count=2)
    history["basico_4_17"] = history[
        ["basico_4_5", "basico_6_10", "basico_11_14", "basico_15_17"]
    ].sum(axis=1, min_count=4)
    history["basico_6_14"] = history[["basico_6_10", "basico_11_14"]].sum(
        axis=1, min_count=2
    )
    history = history[["ano", "codigo_municipio", *INDICATOR_NAMES]]
    duplicate_count = int(history.duplicated(["ano", "codigo_municipio"]).sum())
    if duplicate_count:
        raise ValueError(f"Histórico atual tem {duplicate_count} chaves duplicadas.")
    return history, {
        "kind": "postgres_local",
        "table": "censo",
        "query": HISTORICAL_NUMERATOR_QUERY,
        "filter": f"ano BETWEEN {start_year} AND {end_year}",
        "aggregation": "same municipal queries: SUM by ano and id_municipio; no operating-status filter",
        "rows": int(len(history)),
    }


def load_historical_csv(path: Path) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Load a controlled historical extract for offline tests or reruns."""

    history = pd.read_csv(path)
    required = {"ano", "codigo_municipio", *INDICATOR_NAMES}
    missing = sorted(required - set(history.columns))
    if missing:
        raise ValueError(f"Histórico CSV sem colunas: {missing}")
    history = history[["ano", "codigo_municipio", *INDICATOR_NAMES]].copy()
    history["ano"] = pd.to_numeric(history["ano"], errors="raise").astype("int64")
    history["codigo_municipio"] = normalize_code_series(history["codigo_municipio"])
    for column in INDICATOR_NAMES:
        history[column] = pd.to_numeric(history[column], errors="coerce")
    if history.duplicated(["ano", "codigo_municipio"]).any():
        raise ValueError("Histórico CSV tem chaves ano/código duplicadas.")
    return history, {
        "kind": "csv",
        "path": f"external/historical/{path.name}",
        "name": path.name,
        "size_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "rows": int(len(history)),
    }


def _divergence_cause(
    row: pd.Series,
    duplicate_rows_by_year: dict[int, int] | None,
) -> str:
    if pd.isna(row["novo_numerador"]):
        return "ponto ausente no painel novo"
    if pd.isna(row["historico_numerador"]):
        return "ponto ausente no histórico atual"
    year = int(row["ano"])
    if duplicate_rows_by_year and duplicate_rows_by_year.get(year, 0) > 0:
        return "diferença potencialmente relacionada a entidades duplicadas; a regra municipal não deduplica"
    return "diferença de versão da fonte ou carga histórica; causa não identificada"


class ReconciliationContractError(ValueError):
    """Raised when the official reconciliation cardinality contract is broken."""


def _reconciliation_contract(
    new_indicators: pd.DataFrame,
    history: pd.DataFrame,
    years: list[int],
) -> dict[str, Any]:
    """Return cardinality evidence for the official 497 x 12 contract."""

    expected_by_year = {str(year): EXPECTED_MUNICIPALITIES_PER_YEAR for year in years}
    issues: list[str] = []
    origins: dict[str, Any] = {}
    code_sets_by_origin: dict[str, dict[int, set[str]]] = {}
    for origin, frame in [("novo_painel", new_indicators), ("historico_atual", history)]:
        selected = frame.loc[frame["ano"].isin(years)].copy()
        duplicates = int(selected.duplicated(["ano", "codigo_municipio"]).sum())
        counts = selected.groupby("ano")["codigo_municipio"].nunique().to_dict()
        counts = {str(int(year)): int(count) for year, count in counts.items()}
        code_sets = {
            int(year): set(
                selected.loc[selected["ano"].eq(year), "codigo_municipio"].dropna().astype(str)
            )
            for year in years
        }
        code_sets_by_origin[origin] = code_sets
        origins[origin] = {
            "rows": int(len(selected)),
            "expected_rows": EXPECTED_HISTORICAL_ROWS,
            "rows_by_year": counts,
            "expected_municipalities_by_year": expected_by_year,
            "duplicate_grain_rows": duplicates,
        }
        if len(selected) != EXPECTED_HISTORICAL_ROWS:
            issues.append(
                f"{origin}: esperado {EXPECTED_HISTORICAL_ROWS} linhas, encontrado {len(selected)}"
            )
        if duplicates:
            issues.append(f"{origin}: {duplicates} linhas duplicadas no grão ano/código")
        for year in years:
            actual = len(code_sets[year])
            if actual != EXPECTED_MUNICIPALITIES_PER_YEAR:
                issues.append(
                    f"{origin}/{year}: esperado {EXPECTED_MUNICIPALITIES_PER_YEAR} municípios, encontrado {actual}"
                )

    for year in years:
        new_codes = code_sets_by_origin["novo_painel"][year]
        history_codes = code_sets_by_origin["historico_atual"][year]
        if new_codes != history_codes:
            missing_in_new = sorted(history_codes - new_codes)
            missing_in_history = sorted(new_codes - history_codes)
            issues.append(
                f"{year}: universos municipais diferentes; ausentes no novo={missing_in_new[:10]}, "
                f"ausentes no histórico={missing_in_history[:10]}"
            )

    return {
        "valid": not issues,
        "issues": issues,
        "expected_municipalities": EXPECTED_MUNICIPALITIES_PER_YEAR,
        "expected_rows_per_origin": EXPECTED_HISTORICAL_ROWS,
        "expected_points": EXPECTED_RECONCILIATION_POINTS,
        "origins": origins,
    }


def reconcile(
    panel: pd.DataFrame,
    history: pd.DataFrame,
    output_dir: Path,
    *,
    source_metadata: list[dict[str, Any]] | None = None,
    historical_metadata: dict[str, Any] | None = None,
    start_year: int = HISTORICAL_FIRST_YEAR,
    end_year: int = HISTORICAL_LAST_YEAR,
    strict_contract: bool | None = None,
) -> dict[str, Any]:
    """Compare all seven numerators and enforce the official contract by default."""

    if start_year > end_year:
        raise ValueError("O primeiro ano da reconciliação não pode ser maior que o último.")
    if strict_contract is None:
        strict_contract = (
            start_year == HISTORICAL_FIRST_YEAR and end_year == HISTORICAL_LAST_YEAR
        )

    new_indicators = derive_indicators(panel)
    new_indicators["ano"] = pd.to_numeric(new_indicators["ano"], errors="raise").astype("int64")
    new_indicators["codigo_municipio"] = normalize_code_series(new_indicators["codigo_municipio"])
    history = history.copy()
    history["ano"] = pd.to_numeric(history["ano"], errors="raise").astype("int64")
    history["codigo_municipio"] = normalize_code_series(history["codigo_municipio"])

    years = list(range(start_year, end_year + 1))
    contract = (
        _reconciliation_contract(new_indicators, history, years)
        if strict_contract
        else {
            "valid": True,
            "issues": [],
            "expected_municipalities": EXPECTED_MUNICIPALITIES_PER_YEAR,
            "expected_rows_per_origin": EXPECTED_HISTORICAL_ROWS,
            "expected_points": EXPECTED_RECONCILIATION_POINTS,
            "origins": {},
        }
    )
    new_codes = set(
        new_indicators.loc[new_indicators["ano"].isin(years), "codigo_municipio"].dropna()
    )
    history_codes = set(
        history.loc[history["ano"].isin(years), "codigo_municipio"].dropna()
    )
    codes = sorted(new_codes | history_codes)
    grid = pd.MultiIndex.from_product(
        [years, codes, INDICATOR_NAMES], names=["ano", "codigo_municipio", "indicador"]
    ).to_frame(index=False)
    new_long = new_indicators.loc[new_indicators["ano"].isin(years)].melt(
        id_vars=["ano", "codigo_municipio"],
        value_vars=INDICATOR_NAMES,
        var_name="indicador",
        value_name="novo_numerador",
    )
    history_long = history.loc[history["ano"].isin(years)].melt(
        id_vars=["ano", "codigo_municipio"],
        value_vars=INDICATOR_NAMES,
        var_name="indicador",
        value_name="historico_numerador",
    )
    comparison = grid.merge(
        new_long, on=["ano", "codigo_municipio", "indicador"], how="left"
    ).merge(
        history_long, on=["ano", "codigo_municipio", "indicador"], how="left"
    )
    comparison["novo_numerador"] = pd.to_numeric(comparison["novo_numerador"], errors="coerce")
    comparison["historico_numerador"] = pd.to_numeric(
        comparison["historico_numerador"], errors="coerce"
    )
    both = comparison["novo_numerador"].notna() & comparison["historico_numerador"].notna()
    comparison["diferenca"] = comparison["novo_numerador"] - comparison["historico_numerador"]
    comparison["correspondencia_exata"] = both & comparison["diferenca"].eq(0)
    comparison["causa"] = comparison.apply(
        _divergence_cause,
        axis=1,
        duplicate_rows_by_year={
            int(entry["expected_year"]): int(entry["duplicate_entity_rows_excess_count"])
            for entry in (source_metadata or [])
        },
    )

    exact_total = int(comparison["correspondencia_exata"].sum())
    compared_total = int(both.sum())
    if strict_contract:
        contract["actual_points"] = int(len(grid))
        contract["compared_points"] = compared_total
        contract["exact_points"] = exact_total
        if len(grid) != EXPECTED_RECONCILIATION_POINTS:
            contract["issues"].append(
                f"grade: esperado {EXPECTED_RECONCILIATION_POINTS} pontos, encontrado {len(grid)}"
            )
        if compared_total != EXPECTED_RECONCILIATION_POINTS:
            contract["issues"].append(
                f"comparação: esperado {EXPECTED_RECONCILIATION_POINTS} pontos, encontrado {compared_total}"
            )
        if contract["issues"]:
            raise ReconciliationContractError(
                "Contrato oficial de reconciliação não atendido: "
                + "; ".join(contract["issues"])
            )

    summary_rows: list[dict[str, Any]] = []
    expected_per_year_indicator = (
        EXPECTED_MUNICIPALITIES_PER_YEAR if strict_contract else len(codes)
    )
    for year in years:
        for indicator in INDICATOR_NAMES:
            subset = comparison.loc[
                comparison["ano"].eq(year) & comparison["indicador"].eq(indicator)
            ]
            compared = subset["novo_numerador"].notna() & subset["historico_numerador"].notna()
            exact = subset["correspondencia_exata"]
            differences = subset.loc[compared & ~exact, "diferenca"].abs()
            exact_count = int(exact.sum())
            compared_count = int(compared.sum())
            summary_rows.append(
                {
                    "ano": year,
                    "indicador": indicator,
                    "pontos_esperados": expected_per_year_indicator,
                    "pontos_comparados": compared_count,
                    "correspondencias_exatas": exact_count,
                    "percentual_exato": round(100 * exact_count / compared_count, 6)
                    if compared_count
                    else 0.0,
                    "percentual_exato_do_esperado": round(
                        100 * exact_count / expected_per_year_indicator, 6
                    )
                    if expected_per_year_indicator
                    else 0.0,
                    "pontos_ausentes": int((~compared).sum()),
                    "diferenca_maxima": float(differences.max()) if not differences.empty else 0.0,
                    "soma_absoluta_diferencas": float(differences.sum()) if not differences.empty else 0.0,
                }
            )
    summary = pd.DataFrame(summary_rows)
    divergences = comparison.loc[
        ~comparison["correspondencia_exata"],
        [
            "ano",
            "codigo_municipio",
            "indicador",
            "novo_numerador",
            "historico_numerador",
            "diferenca",
            "causa",
        ],
    ].sort_values(["ano", "codigo_municipio", "indicador"])
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "reconciliation_summary.csv"
    divergences_path = output_dir / "reconciliation_divergences.csv"
    examples_path = output_dir / "reconciliation_examples.json"
    write_csv(summary_path, summary)
    write_csv(divergences_path, divergences)
    examples = {
        "generated_at_utc": utc_now(),
        "expected_points": int(len(grid)),
        "divergence_points": int(len(divergences)),
        "examples_by_indicator": {
            indicator: divergences.loc[
                divergences["indicador"].eq(indicator)
            ].head(5).to_dict("records")
            for indicator in INDICATOR_NAMES
        },
        "reproduction": {
            "panel_grain": "ano + codigo_municipio",
            "indicator_formulas": INDICATOR_FORMULAS,
            "historical_source": historical_metadata or {},
            "source_filter": "SG_UF == 'RS'; all TP_SITUACAO_FUNCIONAMENTO values included",
        },
    }
    write_json(examples_path, examples)
    causes = {
        str(key): int(value)
        for key, value in divergences["causa"].value_counts().to_dict().items()
    }
    return {
        "status": (
            "reconciled"
            if strict_contract and len(divergences) == 0
            else "divergent"
            if len(divergences) > 0
            else "reconciled_non_strict"
        ),
        "strict_contract": bool(strict_contract),
        "contract": contract,
        "expected_municipalities": EXPECTED_MUNICIPALITIES_PER_YEAR,
        "municipality_codes_compared": len(codes),
        "years_compared": years,
        "indicators_compared": INDICATOR_NAMES,
        "expected_points": int(len(grid)),
        "expected_points_contract": EXPECTED_RECONCILIATION_POINTS,
        "compared_points": compared_total,
        "exact_points": exact_total,
        "divergence_points": int(len(divergences)),
        "percentual_exato": round(100 * exact_total / compared_total, 6)
        if compared_total
        else 0.0,
        "causes": causes,
        "summary_path": summary_path.name,
        "divergences_path": divergences_path.name,
        "examples_path": examples_path.name,
        "summary": summary,
    }


def render_audit_report(
    path: Path,
    panel_metadata: dict[str, Any],
    reconciliation_metadata: dict[str, Any],
    historical_metadata: dict[str, Any] | None,
) -> None:
    """Write a compact, human-readable audit handoff beside the data files."""

    validation = panel_metadata["panel"]["validation"]
    summary: pd.DataFrame = reconciliation_metadata["summary"]
    indicator_summary = (
        summary.groupby("indicador", as_index=False)
        .agg(
            pontos_esperados=("pontos_esperados", "sum"),
            pontos_comparados=("pontos_comparados", "sum"),
            correspondencias_exatas=("correspondencias_exatas", "sum"),
            diferenca_maxima=("diferenca_maxima", "max"),
            soma_absoluta_diferencas=("soma_absoluta_diferencas", "sum"),
        )
    )
    indicator_lines = [
        "| indicador | esperados | comparados | exatos | % exato | diferença máxima | soma abs. diferenças |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in indicator_summary.to_dict("records"):
        percent = (
            100 * row["correspondencias_exatas"] / row["pontos_comparados"]
            if row["pontos_comparados"]
            else 0
        )
        indicator_lines.append(
            f"| {row['indicador']} | {row['pontos_esperados']} | {row['pontos_comparados']} | "
            f"{row['correspondencias_exatas']} | {percent:.3f}% | {row['diferenca_maxima']:.0f} | "
            f"{row['soma_absoluta_diferencas']:.0f} |"
        )
    coverage_lines = [
        "| ano | municípios | ausentes no universo observado |",
        "| ---: | ---: | --- |",
    ]
    missing_by_year = validation["missing_municipalities_by_year"]
    for year, count in validation["coverage_by_year"].items():
        missing = ", ".join(missing_by_year.get(year, [])) or "—"
        coverage_lines.append(f"| {year} | {count} | {missing} |")
    empty_audit_lines = [
        "| ano | TP_SITUACAO_FUNCIONAMENTO | seis campos vazios | vazio parcial | completos |",
        "| ---: | --- | ---: | ---: | ---: |",
    ]
    for source in panel_metadata["sources"]:
        year = source["expected_year"]
        for status, counts in source.get("empty_value_audit_by_status", {}).items():
            empty_audit_lines.append(
                f"| {year} | {status} | {counts.get('lines_six_empty', 0)} | "
                f"{counts.get('lines_partial_empty', 0)} | {counts.get('lines_complete', 0)} |"
            )
    divergence_note = (
        "Nenhuma divergência numérica foi encontrada."
        if reconciliation_metadata["divergence_points"] == 0
        else (
            f"Há {reconciliation_metadata['divergence_points']} divergências; consulte "
            f"`{Path(reconciliation_metadata['divergences_path']).name}`. Os números não foram ajustados."
        )
    )
    historical_note = historical_metadata or {"kind": "not loaded"}
    content = "\n".join(
        [
            "# Auditoria do painel municipal do Censo Escolar",
            "",
            f"Gerador: `{GENERATOR_VERSION}`; gerado em `{panel_metadata['generated_at_utc']}`.",
            "",
            "## Regra reproduzida",
            "",
            "- Fonte: CSV anual oficial, separador `;`, codificação `latin1`, leitura em chunks e `usecols`.",
            "- Filtro municipal: `SG_UF == 'RS'`.",
            "- `TP_SITUACAO_FUNCIONAMENTO`: todos os valores são incluídos; a coluna é auditada, não filtrada.",
            "- Grão: uma linha por `NU_ANO_CENSO` e `CO_MUNICIPIO`; a carga histórica municipal também não deduplica entidades.",
            "- Campos canônicos usados inclusive em 2025; aliases `_REF_31_03` não são usados.",
            "- A situação de funcionamento não é filtro: todos os valores observados entram no `SUM` municipal.",
            "- Valores vazios não são imputados; a soma municipal mantém a semântica `SUM` atual (`min_count=1`).",
            "",
            "## Painel e cobertura",
            "",
            f"Arquivo: `{Path(panel_metadata['panel']['path']).name}`; {panel_metadata['panel']['rows']} linhas; "
            f"{panel_metadata['panel']['size_bytes']} bytes comprimidos.",
            "",
            f"Validação: `{validation['status']}`; expectativa de {validation['expected_rows']} linhas; "
            f"delta observado {validation['row_delta']}.",
            f"A regra de universo é 496 municípios em 2007–2012 e 497 em 2013–2025; "
            f"a expectativa legada de 497 em todos os anos seria {validation['legacy_expected_rows_497']} linhas.",
            "",
            *coverage_lines,
            "",
            "Pinto Bandeira (`4314548`) inicia em 2013; os anos anteriores não foram preenchidos com zero.",
            "Bento Gonçalves (`4302105`) e Pinto Bandeira estão registrados como possível quebra territorial em 2013 para backtesting futuro; nenhum ajuste foi aplicado.",
            "",
            "## Auditoria de valores vazios por situação de funcionamento",
            "",
            *empty_audit_lines,
            "",
            "## Reconciliação",
            "",
            f"Histórico: `{historical_note.get('kind')}`; pontos esperados {reconciliation_metadata['expected_points']}; "
            f"comparados {reconciliation_metadata['compared_points']}; exatos {reconciliation_metadata['exact_points']}.",
            f"Contrato estrito: `{reconciliation_metadata.get('strict_contract', False)}`; status `{reconciliation_metadata.get('status')}`.",
            "",
            *indicator_lines,
            "",
            divergence_note,
            "",
            "Arquivos: "
            f"`{Path(reconciliation_metadata['summary_path']).name}`, "
            f"`{Path(reconciliation_metadata['divergences_path']).name}` e "
            f"`{Path(reconciliation_metadata['examples_path']).name}`.",
            "",
            "## Decisões e riscos",
            "",
            "- A diferença entre a expectativa legada de 497 municípios por ano e o universo territorial variável não foi preenchida silenciosamente.",
            "- Divergências de numerador, se existirem, permanecem no arquivo detalhado para decisão sobre versão da fonte ou carga histórica.",
            "- `qtd_entidades` não faz parte do painel compacto; a auditoria de CO_ENTIDADE permanece no manifesto sem alterar o numerador.",
            "- O formato é CSV gzip porque o projeto não declara `pyarrow`/`fastparquet`; não foi introduzida dependência pesada.",
            "",
        ]
    )
    _atomic_write_bytes(path, content.encode("utf-8"))
