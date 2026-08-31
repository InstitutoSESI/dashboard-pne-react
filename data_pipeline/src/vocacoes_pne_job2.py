"""Primitivas auditáveis das materializações V7 Vocações × PNE — Job 2."""

from __future__ import annotations

import gzip
import hashlib
import io
import json
import math
import os
import re
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import pandas as pd


SCHEMA_VERSION = "vocacoes-pne-v7-job2-v1"
JOB_ID = "v7-job2"
FORBIDDEN_STOCK_TABLE = "estoque_emprego_faixa_etaria"
ALLOWED_STATUSES = frozenset(
    {"NOT_STARTED", "IN_PROGRESS", "READY", "BLOCKED_WITH_EVIDENCE"}
)
IBGE_CODE_PATTERN = re.compile(r"^[0-9]{7}$")
PUBLIC_DATA_PARTS = ("public", "data")


def require_ibge_code(value: Any) -> str:
    """Valida a identidade municipal sem coerção numérica."""

    if not isinstance(value, str) or not IBGE_CODE_PATTERN.fullmatch(value):
        raise ValueError(f"Código IBGE municipal inválido: {value!r}.")
    return value


def validate_ibge_codes(values: Iterable[Any]) -> list[str]:
    codes = [require_ibge_code(value) for value in values]
    if len(codes) != len(set(codes)):
        raise ValueError("O conjunto municipal contém códigos IBGE duplicados.")
    return codes


def safe_ratio(numerator: Any, denominator: Any, *, multiplier: float = 1.0) -> float | None:
    """Calcula uma razão preservando denominador zero como ``None``."""

    if numerator is None or denominator is None or pd.isna(numerator) or pd.isna(denominator):
        return None
    numeric_denominator = float(denominator)
    if numeric_denominator == 0:
        return None
    value = float(numerator) / numeric_denominator * multiplier
    if not math.isfinite(value):
        raise ValueError("A razão calculada não é finita.")
    return value


def eja_distribution_metrics(
    *,
    potential_public: Any,
    enrollments: Any,
    regional_potential_public: Any,
    regional_enrollments: Any,
) -> dict[str, float | None]:
    """Aplica literalmente as fórmulas canônicas do contrato V7 para EJA.

    ``diferenca_distribuicao_pp`` permanece em escala fracionária (0–1),
    conforme o contrato; a apresentação futura é responsável por converter a
    fração em pontos percentuais, se necessário.
    """

    public_share = safe_ratio(potential_public, regional_potential_public)
    enrollment_share = safe_ratio(enrollments, regional_enrollments)
    difference = (
        enrollment_share - public_share
        if enrollment_share is not None and public_share is not None
        else None
    )
    return {
        "participacao_publico_i": public_share,
        "participacao_matriculas_i": enrollment_share,
        "diferenca_distribuicao_pp": difference,
        "matriculas_por_mil": safe_ratio(enrollments, potential_public, multiplier=1000.0),
    }


def weighted_value(values: pd.Series, weights: pd.Series) -> float | None:
    """Recompõe indicador regional/estadual com numerador e denominador."""

    valid = values.notna() & weights.notna()
    if not valid.any():
        return None
    numeric_weights = pd.to_numeric(weights.loc[valid], errors="raise")
    denominator = float(numeric_weights.sum())
    if denominator == 0:
        return None
    numerator = float(
        (
            pd.to_numeric(values.loc[valid], errors="raise")
            * numeric_weights
        ).sum()
    )
    result = numerator / denominator
    if not math.isfinite(result):
        raise ValueError("A média ponderada recomposta não é finita.")
    return result


def municipal_distribution(values: pd.Series) -> dict[str, float | int | None]:
    """Resume comparações territoriais sem criar uma taxa regional por média simples."""

    numeric = pd.to_numeric(values, errors="coerce").dropna()
    if numeric.empty:
        return {
            "municipality_count": 0,
            "minimum": None,
            "quartile_1": None,
            "median": None,
            "quartile_3": None,
            "maximum": None,
        }
    return {
        "municipality_count": int(numeric.size),
        "minimum": float(numeric.min()),
        "quartile_1": float(numeric.quantile(0.25)),
        "median": float(numeric.median()),
        "quartile_3": float(numeric.quantile(0.75)),
        "maximum": float(numeric.max()),
    }


def canonical_json_bytes(payload: Any) -> bytes:
    return (
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path, *, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(payload))


def write_csv_gzip(path: Path, frame: pd.DataFrame) -> None:
    """Serializa CSV UTF-8/GZIP de modo determinístico (mtime do GZIP igual a zero)."""

    path.parent.mkdir(parents=True, exist_ok=True)
    buffer = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=buffer, mtime=0) as compressed:
        with io.TextIOWrapper(compressed, encoding="utf-8", newline="") as text_stream:
            frame.to_csv(
                text_stream,
                index=False,
                lineterminator="\n",
                na_rep="null",
            )
    path.write_bytes(buffer.getvalue())


def artifact_record(
    *,
    root: Path,
    path: Path,
    frame: pd.DataFrame | None,
    subjob: str,
    grain: Sequence[str] | str,
    period: str,
    lens: str,
    unit: str,
    aggregation_rule: str,
) -> dict[str, Any]:
    relative = path.relative_to(root).as_posix()
    return {
        "aggregationRule": aggregation_rule,
        "byteSize": path.stat().st_size,
        "columns": list(frame.columns) if frame is not None else None,
        "grain": list(grain) if not isinstance(grain, str) else grain,
        "lens": lens,
        "path": relative,
        "period": period,
        "rowCount": int(len(frame)) if frame is not None else None,
        "sha256": sha256_file(path),
        "subjob": subjob,
        "unit": unit,
    }


def assert_outside_public_data(path: Path, repo_root: Path) -> None:
    resolved = path.resolve()
    public_root = (repo_root / "public" / "data").resolve()
    if resolved == public_root or public_root in resolved.parents:
        raise ValueError("As materializações de pesquisa não podem atingir public/data.")


def replace_directory_transactionally(staging: Path, target: Path) -> str:
    """Promove pesquisa com no-op, manifesto por último e rollback local.

    O Windows pode bloquear o rename de diretórios recém-varridos por Pandas.
    Cada arquivo é, portanto, copiado para um nome parcial e promovido por
    ``os.replace``; ``manifest.json`` é sempre o último arquivo, funcionando
    como marcador de lote integralmente pronto.
    """

    if target.exists() and directory_content_digest(staging) == directory_content_digest(target):
        shutil.rmtree(staging)
        return "unchanged"

    target.parent.mkdir(parents=True, exist_ok=True)
    backup = target.parent / f".{target.name}.backup"
    candidate = Path(
        tempfile.mkdtemp(prefix=f".{target.name}.promotion-", dir=target.parent)
    )
    if backup.exists():
        shutil.rmtree(backup)
    try:
        # Alguns leitores C/Pandas mantêm um handle transitório no diretório de
        # staging no Windows. A cópia validada não herda esses handles e ainda
        # pode ser promovida por rename atômico no mesmo volume.
        shutil.copytree(staging, candidate, dirs_exist_ok=True)
        if directory_content_digest(candidate) != directory_content_digest(staging):
            raise RuntimeError("A cópia candidata diverge do staging validado.")
        if target.exists():
            _copy_directory_manifest_last(target, backup)
            if directory_content_digest(backup) != directory_content_digest(target):
                raise RuntimeError("O backup diverge do destino anterior.")
            shutil.rmtree(target)
        _copy_directory_manifest_last(candidate, target)
        if directory_content_digest(target) != directory_content_digest(candidate):
            raise RuntimeError("O destino promovido diverge da cópia candidata.")
        if backup.exists():
            shutil.rmtree(backup)
        if candidate.exists():
            shutil.rmtree(candidate)
        shutil.rmtree(staging)
    except Exception:
        if target.exists():
            shutil.rmtree(target)
        if backup.exists():
            _copy_directory_manifest_last(backup, target)
            shutil.rmtree(backup)
        if candidate.exists():
            shutil.rmtree(candidate)
        raise
    return "replaced"


def _copy_directory_manifest_last(source: Path, target: Path) -> None:
    if target.exists():
        raise FileExistsError(f"O destino da cópia já existe: {target}")
    target.mkdir(parents=True)
    files = sorted(item for item in source.rglob("*") if item.is_file())
    files.sort(
        key=lambda item: (
            item.relative_to(source).as_posix() == "manifest.json",
            item.relative_to(source).as_posix(),
        )
    )
    for source_path in files:
        relative = source_path.relative_to(source)
        target_path = target / relative
        target_path.parent.mkdir(parents=True, exist_ok=True)
        partial_path = target_path.with_name(f".{target_path.name}.partial")
        shutil.copy2(source_path, partial_path)
        _replace_path_with_retry(partial_path, target_path)


def _replace_path_with_retry(source: Path, target: Path) -> None:
    """Tolera bloqueios transitórios de antivírus/indexadores no Windows."""

    delays = (0.1, 0.2, 0.4, 0.8, 1.6, 3.2)
    for delay in (*delays, None):
        try:
            os.replace(source, target)
            return
        except PermissionError:
            if delay is None:
                raise
            time.sleep(delay)


def directory_content_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        payload_hash = bytes.fromhex(sha256_file(path))
        digest.update(payload_hash)
    return digest.hexdigest()


def staging_directory_for(target: Path) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix=f".{target.name}.stage-", dir=target.parent))


def validate_unique_key(frame: pd.DataFrame, columns: Sequence[str], *, label: str) -> None:
    missing = set(columns) - set(frame.columns)
    if missing:
        raise ValueError(f"{label}: colunas de chave ausentes: {sorted(missing)}.")
    duplicated = frame.duplicated(list(columns), keep=False)
    if duplicated.any():
        raise ValueError(f"{label}: {int(duplicated.sum())} linhas têm chave duplicada.")


def validate_nonnegative(frame: pd.DataFrame, columns: Sequence[str], *, label: str) -> None:
    for column in columns:
        numeric = pd.to_numeric(frame[column], errors="coerce")
        if numeric.lt(0).any():
            raise ValueError(f"{label}: valor negativo em {column}.")


def subjob_state(
    subjob_id: str,
    *,
    status: str,
    reason: str,
    artifacts: Sequence[str],
    validations: Mapping[str, Any],
) -> dict[str, Any]:
    if status not in ALLOWED_STATUSES:
        raise ValueError(f"Status inválido para {subjob_id}: {status}.")
    return {
        "artifacts": list(artifacts),
        "id": subjob_id,
        "reason": reason,
        "status": status,
        "validations": dict(validations),
    }
