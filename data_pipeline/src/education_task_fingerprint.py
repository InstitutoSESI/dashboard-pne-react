"""Fingerprint da tarefa principal de Educacao do Rio Grande do Sul.

O contrato atende ao modo shadow e ao modo incremental opt-in. A elegibilidade
so autoriza reutilizacao quando fontes, codigo executado e todos os outputs
administrados forem verificaveis. O estado local e uma prova de integridade e
nunca e usado como fonte analitica.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import sys
from typing import Any

import numpy as np
import pandas as pd
from pandas.api import types as pandas_types


TASK_SCHEMA_VERSION = "education-task-fingerprint-v1"
TASK_NAMESPACE = "education.core"
STATE_CODE = "RS"
TASK_ID = f"{TASK_NAMESPACE}.{STATE_CODE.lower()}"
SOURCE_DIGEST_ALGORITHM_VERSION = "education-source-digest-v1"
INPUT_FINGERPRINT_ALGORITHM_VERSION = "education-input-fingerprint-v1"
OUTPUT_MANIFEST_SCHEMA_VERSION = "education-output-manifest-v1"
OUTPUT_TREE_ALGORITHM_VERSION = "education-output-tree-sha256-v1"
SOURCE_DIGESTS_SCHEMA_VERSION = "education-source-digests-v1"
CONTRACT_DIGESTS_SCHEMA_VERSION = "education-contract-digests-v1"
CONTRACT_FILE_DIGEST_ALGORITHM_VERSION = "education-contract-file-sha256-v1"
NULL_POLICY = "pandas-isna-single-null-v1"
ROW_ORDER_POLICY = "multiset-row-hash-v1"
COLUMN_ORDER_POLICY = "contractual-column-order-v1"
FLOAT_NORMALIZATION_DECIMAL_PLACES = 12
FLOAT_POLICY = "round-float-to-12-decimal-places-v1"
MANAGED_ROOT_OUTPUT_FILES = ("index.json", "municipios_index.json")
MANAGED_ROOT_OUTPUT_COUNT = len(MANAGED_ROOT_OUTPUT_FILES)
DEFAULT_MANAGED_ROOT = "public/data/educacao"

_HASH_KEY_A = "pne-edu-hash-v1a"
_HASH_KEY_B = "pne-edu-hash-v1b"
_NULL_SENTINEL = "\x00<PNE-EDUCATION-NULL-V1>\x00"
_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
_MUNICIPAL_OUTPUT_PATTERN = re.compile(r"municipios/(\d{7})\.json")
_OPERATIONAL_COLUMN_NAMES = frozenset(
    {
        "data_exportacao",
        "data_carga",
        "updated_at",
        "generated_at",
        "runid",
        "run_id",
        "staging_path",
    }
)


@dataclass(frozen=True, slots=True)
class EducationSourceDefinition:
    source_id: str
    frame_key: str
    relation_id: str
    origin: str
    nature: str = "analytical"
    adapter_id: str = "utils_educacao.get_engine:sesi"


EDUCATION_SOURCE_DEFINITIONS = (
    EducationSourceDefinition(
        "education.municipalities",
        "municipalities",
        "municipios",
        "postgres_table",
    ),
    EducationSourceDefinition(
        "education.view.vw_educacao_matriculas",
        "matriculas",
        "vw_educacao_matriculas",
        "postgres_view",
    ),
    EducationSourceDefinition(
        "education.view.vw_educacao_visao_geral_municipal",
        "matriculas_educacao_basica",
        "vw_educacao_visao_geral_municipal",
        "postgres_view",
    ),
    EducationSourceDefinition(
        "education.view.vw_educacao_matriculas_faixa_etaria",
        "matriculas_faixa_etaria",
        "vw_educacao_matriculas_faixa_etaria",
        "postgres_view",
    ),
    EducationSourceDefinition(
        "education.view.vw_educacao_matriculas_cor_raca",
        "matriculas_cor_raca",
        "vw_educacao_matriculas_cor_raca",
        "postgres_view",
    ),
    EducationSourceDefinition(
        "education.view.vw_educacao_rede_escolar",
        "rede_escolar",
        "vw_educacao_rede_escolar",
        "postgres_view",
    ),
    EducationSourceDefinition(
        "education.view.vw_educacao_infraestrutura_escolar_ativa",
        "school_infrastructure",
        "vw_educacao_infraestrutura_escolar_ativa",
        "postgres_view",
    ),
    EducationSourceDefinition(
        "education.view.vw_educacao_rede_escolar_etapa",
        "rede_escolar_etapa",
        "vw_educacao_rede_escolar_etapa",
        "postgres_view",
    ),
    EducationSourceDefinition(
        "education.view.vw_educacao_turmas_docentes",
        "turmas",
        "vw_educacao_turmas_docentes",
        "postgres_view",
    ),
    EducationSourceDefinition(
        "education.view.vw_educacao_alunos_turma",
        "alunos_turma",
        "vw_educacao_alunos_turma",
        "postgres_view",
    ),
    EducationSourceDefinition(
        "education.view.vw_educacao_fluxo",
        "fluxo",
        "vw_educacao_fluxo",
        "postgres_view",
    ),
    EducationSourceDefinition(
        "education.view.vw_educacao_aprendizagem",
        "aprendizagem",
        "vw_educacao_aprendizagem",
        "postgres_view",
    ),
    EducationSourceDefinition(
        "education.view.vw_educacao_oferta_tecnica",
        "oferta",
        "vw_educacao_oferta_tecnica",
        "postgres_view",
    ),
    EducationSourceDefinition(
        "education.snapshot.educacao_indigena_municipal",
        "educacao_indigena",
        "educacao_indigena_municipal",
        "postgres_table_from_local_snapshot",
    ),
    EducationSourceDefinition(
        "education.snapshot.populacao_indigena_faixa_municipal",
        "populacao_indigena_faixas",
        "populacao_indigena_faixa_municipal",
        "postgres_table_from_local_snapshot",
    ),
    EducationSourceDefinition(
        "education.snapshot.populacao_indigena_idade_municipal",
        "populacao_indigena_idades",
        "populacao_indigena_idade_municipal",
        "postgres_table_from_local_snapshot",
    ),
    EducationSourceDefinition(
        "education.view.vw_educacao_sistema_s",
        "sistema_s",
        "vw_educacao_sistema_s",
        "postgres_view",
    ),
    EducationSourceDefinition(
        "education.view.vw_educacao_sistema_s_escolas",
        "sistema_s_escolas",
        "vw_educacao_sistema_s_escolas",
        "postgres_view",
    ),
    EducationSourceDefinition(
        "education.view.vw_vaar_municipio_dashboard",
        "vaar",
        "vw_vaar_municipio_dashboard",
        "postgres_view",
    ),
)


_STATE_CONTRACT_FILE_TEMPLATES = (
    "config/states/{uf}.json",
    "config/municipalities/{uf}.json",
    "config/compatibility/education-municipality-routes/{uf}.json",
)
_SHARED_CONTRACT_FILES = (
    "data_pipeline/scripts/export_education_indicators.py",
    "data_pipeline/scripts/update_static_data.py",
    "data_pipeline/src/config.py",
    "data_pipeline/src/data/repository.py",
    "data_pipeline/src/data_loader.py",
    "data_pipeline/src/education_municipality_routes.py",
    "data_pipeline/src/education_task_fingerprint.py",
    "data_pipeline/src/education_transactional_publication.py",
    "data_pipeline/src/indigenous_education_coverage.py",
    "data_pipeline/src/municipality_registry.py",
    "data_pipeline/src/pipeline_profiling.py",
    "data_pipeline/src/school_infrastructure.py",
    "data_pipeline/src/school_infrastructure_materialization.py",
    "data_pipeline/src/state_config.py",
    "data_pipeline/queries/school_infrastructure_source.sql",
    "data_pipeline/uv.lock",
)


class EducationFingerprintError(RuntimeError):
    """Erro fail-closed na construcao ou validacao do fingerprint."""


class EducationOutputIntegrityError(EducationFingerprintError):
    """Erro classificado de integridade dos outputs administrados."""

    def __init__(self, reason: str, message: str):
        self.reason = reason
        super().__init__(message)


def normalized_task_state_code(state_code: object) -> str:
    """Aceita somente UF textual de duas letras; nunca infere um estado."""
    if not isinstance(state_code, str):
        raise EducationFingerprintError(
            f"Codigo estadual deve ser texto de duas letras: {state_code!r}."
        )
    normalized = state_code.strip().upper()
    if re.fullmatch(r"[A-Z]{2}", normalized) is None:
        raise EducationFingerprintError(
            f"Codigo estadual invalido: {state_code!r}."
        )
    return normalized


def task_id_for_state(state_code: object) -> str:
    """A tarefa de Educacao e uma por estado; o id carrega a UF."""
    return f"{TASK_NAMESPACE}.{normalized_task_state_code(state_code).lower()}"


def education_contract_file_allowlist(
    state_code: object = STATE_CODE,
) -> tuple[str, ...]:
    """Contratos participantes: os da UF ativa mais os compartilhados."""
    uf = normalized_task_state_code(state_code).lower()
    return (
        *(template.format(uf=uf) for template in _STATE_CONTRACT_FILE_TEMPLATES),
        *_SHARED_CONTRACT_FILES,
    )


def expected_managed_output_count(expected_municipality_count: object) -> int:
    """Universo municipal do estado mais os dois artefatos de raiz."""
    if isinstance(expected_municipality_count, bool) or not isinstance(
        expected_municipality_count, int
    ):
        raise EducationFingerprintError(
            "Universo municipal esperado deve ser inteiro: "
            f"{expected_municipality_count!r}."
        )
    if expected_municipality_count <= 0:
        raise EducationFingerprintError(
            "Universo municipal esperado deve ser positivo: "
            f"{expected_municipality_count}."
        )
    return expected_municipality_count + MANAGED_ROOT_OUTPUT_COUNT


EDUCATION_CONTRACT_FILE_ALLOWLIST = education_contract_file_allowlist(STATE_CODE)


@dataclass(frozen=True, slots=True)
class TaskStateLoadResult:
    state: dict[str, Any] | None
    reason: str


@dataclass(frozen=True, slots=True)
class OutputIntegrityResult:
    valid: bool
    reason: str
    managed_outputs: int = 0
    output_bytes_verified: int = 0


@dataclass(frozen=True, slots=True)
class ResolvedPythonModuleContract:
    """Modulo Python importado cuja origem sera hashada sem serializar seu path."""

    contract_id: str
    module_name: str
    source_path: Path
    version: str | None = None


@dataclass(frozen=True, slots=True)
class ShadowDecision:
    would_skip: bool
    reason: str
    fingerprint_hit: bool
    manifest_invalid: bool
    output_integrity: OutputIntegrityResult


def canonical_json_bytes(value: Any) -> bytes:
    """Serializa um contrato sem depender de locale, horario ou ordem de dict."""
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _hash_file(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def _dtype_descriptor(series: pd.Series) -> dict[str, Any]:
    descriptor: dict[str, Any] = {
        "dtype": str(series.dtype),
        "inferredType": pd.api.types.infer_dtype(series, skipna=True),
    }
    if isinstance(series.dtype, pd.CategoricalDtype):
        categories = pd.Series(series.dtype.categories)
        category_hashes = pd.util.hash_pandas_object(
            categories,
            index=False,
            categorize=True,
            hash_key=_HASH_KEY_A,
        ).to_numpy(dtype="<u8", copy=False)
        descriptor.update(
            categoryCount=len(categories),
            categoryOrdered=bool(series.dtype.ordered),
            categoriesSha256=_sha256_bytes(category_hashes.tobytes()),
        )
    return descriptor


def _normalized_for_hashing(series: pd.Series, missing: pd.Series) -> pd.Series:
    if pandas_types.is_float_dtype(series.dtype):
        normalized = series.round(FLOAT_NORMALIZATION_DECIMAL_PLACES)
        return normalized.fillna(0) if bool(missing.any()) else normalized
    if not bool(missing.any()):
        return series
    if isinstance(series.dtype, pd.CategoricalDtype):
        normalized = series.astype(object)
        return normalized.mask(missing, _NULL_SENTINEL)
    if pandas_types.is_datetime64_any_dtype(series.dtype):
        normalized = series.copy()
        replacement: Any = pd.Timestamp(0)
        if isinstance(series.dtype, pd.DatetimeTZDtype):
            replacement = pd.Timestamp(0, tz=series.dtype.tz)
        return normalized.mask(missing, replacement)
    if pandas_types.is_timedelta64_dtype(series.dtype):
        return series.mask(missing, pd.Timedelta(0))
    if pandas_types.is_bool_dtype(series.dtype):
        return series.astype("boolean").fillna(False)
    if pandas_types.is_numeric_dtype(series.dtype):
        return series.fillna(0)
    normalized = series.astype(object)
    return normalized.mask(missing, _NULL_SENTINEL)


def _mix_hashes(accumulator: np.ndarray, values: np.ndarray, salt: int) -> None:
    constant = np.uint64(salt)
    accumulator ^= values + constant + (accumulator << np.uint64(6)) + (
        accumulator >> np.uint64(2)
    )


def digest_tabular_source(
    frame: pd.DataFrame,
    *,
    operational_columns: Iterable[str] = _OPERATIONAL_COLUMN_NAMES,
) -> dict[str, Any]:
    """Produz digest do multiconjunto de linhas de um DataFrame ja carregado.

    A ordem das linhas e deliberadamente nao semantica. A ordem e os dtypes das
    colunas sao contratuais. Todas as ausencias reconhecidas por ``pandas.isna``
    recebem a mesma identidade nula, sem confundir null com um valor preenchido.
    """
    if not isinstance(frame, pd.DataFrame):
        raise TypeError("Fonte tabular deve ser um pandas.DataFrame.")
    if not frame.columns.is_unique:
        raise EducationFingerprintError("Fonte tabular possui colunas duplicadas.")
    if any(not isinstance(column, str) for column in frame.columns):
        raise EducationFingerprintError("Nomes de colunas devem ser textos estaveis.")

    operational = {str(column).casefold() for column in operational_columns}
    excluded = [
        column for column in frame.columns if str(column).casefold() in operational
    ]
    included = [column for column in frame.columns if column not in excluded]
    row_count = len(frame)
    schema = [
        {"name": column, **_dtype_descriptor(frame[column])}
        for column in included
    ]
    schema_contract = {
        "columns": schema,
        "columnOrderPolicy": COLUMN_ORDER_POLICY,
        "floatPolicy": FLOAT_POLICY,
        "nullPolicy": NULL_POLICY,
        "rowOrderPolicy": ROW_ORDER_POLICY,
        "rowCount": row_count,
    }

    first = np.full(row_count, np.uint64(0x243F6A8885A308D3), dtype=np.uint64)
    second = np.full(row_count, np.uint64(0x13198A2E03707344), dtype=np.uint64)
    for position, column in enumerate(included):
        series = frame[column]
        missing = series.isna()
        normalized = _normalized_for_hashing(series, missing)
        value_a = pd.util.hash_pandas_object(
            normalized,
            index=False,
            categorize=True,
            hash_key=_HASH_KEY_A,
        ).to_numpy(dtype=np.uint64, copy=False)
        value_b = pd.util.hash_pandas_object(
            normalized,
            index=False,
            categorize=True,
            hash_key=_HASH_KEY_B,
        ).to_numpy(dtype=np.uint64, copy=False)
        null_hash = pd.util.hash_pandas_object(
            missing.astype("boolean"),
            index=False,
            categorize=True,
            hash_key=_HASH_KEY_A,
        ).to_numpy(dtype=np.uint64, copy=False)
        mixed_a = value_a ^ np.left_shift(null_hash, np.uint64(1))
        mixed_b = value_b ^ np.right_shift(null_hash, np.uint64(1))
        _mix_hashes(first, mixed_a, 0x9E3779B97F4A7C15 + position)
        _mix_hashes(second, mixed_b, 0xC2B2AE3D27D4EB4F + position)

    pairs = np.empty((row_count, 2), dtype="<u8")
    if row_count:
        order = np.lexsort((second, first))
        pairs[:, 0] = first[order]
        pairs[:, 1] = second[order]
    digest = hashlib.sha256()
    schema_bytes = canonical_json_bytes(schema_contract)
    digest.update(schema_bytes)
    digest.update(b"\x00")
    digest.update(pairs.tobytes())
    memory_bytes = int(
        frame[included].memory_usage(index=False, deep=True).sum()
        if included
        else 0
    )
    return {
        "algorithmVersion": SOURCE_DIGEST_ALGORITHM_VERSION,
        "digest": digest.hexdigest(),
        "rowCount": row_count,
        "columnCount": len(included),
        "columns": schema,
        "floatPolicy": FLOAT_POLICY,
        "nullPolicy": NULL_POLICY,
        "rowOrderPolicy": ROW_ORDER_POLICY,
        "columnOrderPolicy": COLUMN_ORDER_POLICY,
        "operationalColumnsExcluded": sorted(excluded),
        "bytesHashed": memory_bytes,
    }


def digest_education_sources(
    source_frames: Mapping[str, pd.DataFrame],
    *,
    definitions: Sequence[EducationSourceDefinition] = EDUCATION_SOURCE_DEFINITIONS,
) -> dict[str, Any]:
    expected_keys = {definition.frame_key for definition in definitions}
    observed_keys = set(source_frames)
    missing = sorted(expected_keys - observed_keys)
    extra = sorted(observed_keys - expected_keys)
    if missing or extra:
        raise EducationFingerprintError(
            "Conjunto de fontes educacionais incompleto; "
            f"ausentes={missing}, extras={extra}."
        )

    sources: dict[str, Any] = {}
    total_rows = total_columns = total_bytes = 0
    for definition in definitions:
        table_digest = digest_tabular_source(source_frames[definition.frame_key])
        total_rows += int(table_digest["rowCount"])
        total_columns += int(table_digest["columnCount"])
        total_bytes += int(table_digest["bytesHashed"])
        sources[definition.source_id] = {
            "sourceId": definition.source_id,
            "frameKey": definition.frame_key,
            "relationId": definition.relation_id,
            "origin": definition.origin,
            "nature": definition.nature,
            "adapterId": definition.adapter_id,
            **table_digest,
        }

    identity = {
        source_id: {
            key: value
            for key, value in source.items()
            if key not in {"bytesHashed", "operationalColumnsExcluded"}
        }
        for source_id, source in sorted(sources.items())
    }
    return {
        "schemaVersion": SOURCE_DIGESTS_SCHEMA_VERSION,
        "algorithmVersion": SOURCE_DIGEST_ALGORITHM_VERSION,
        "complete": True,
        "sourceCount": len(sources),
        "sourceIds": sorted(sources),
        "aggregateSha256": _sha256_bytes(canonical_json_bytes(identity)),
        "sources": sources,
        "stats": {
            "sources": len(sources),
            "rowsHashed": total_rows,
            "columnsHashed": total_columns,
            "bytesHashed": total_bytes,
        },
    }


def _validate_relative_contract_path(value: str) -> PurePosixPath:
    relative = PurePosixPath(value)
    if relative.is_absolute() or not relative.parts or ".." in relative.parts:
        raise EducationFingerprintError(
            f"Caminho de contrato deve ser relativo ao repositorio: {value!r}."
        )
    if any(part in {"*", "**"} for part in relative.parts):
        raise EducationFingerprintError(
            f"Allowlist de contrato nao aceita glob amplo: {value!r}."
        )
    return relative


def _python_module_candidates(
    module_name: str,
    search_paths: Sequence[str],
) -> set[Path]:
    parts = module_name.split(".")
    candidates: set[Path] = set()
    for raw_root in search_paths:
        try:
            root = Path(raw_root or os.curdir).resolve()
        except (OSError, RuntimeError):
            continue
        module_file = root.joinpath(*parts).with_suffix(".py")
        package_file = root.joinpath(*parts, "__init__.py")
        for candidate in (module_file, package_file):
            try:
                if candidate.is_file():
                    candidates.add(candidate.resolve(strict=True))
            except (OSError, RuntimeError):
                continue
    return candidates


def _normalized_module_version(module: Any) -> str | None:
    raw_version = getattr(module, "__version__", None)
    if raw_version is None:
        return None
    if isinstance(raw_version, tuple):
        raw_version = ".".join(str(part) for part in raw_version)
    if not isinstance(raw_version, (str, int, float)) or isinstance(
        raw_version, bool
    ):
        raise EducationFingerprintError(
            "Versao do modulo Python externo nao e verificavel."
        )
    version = str(raw_version)
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._+-]{0,63}", version) is None:
        raise EducationFingerprintError(
            "Versao do modulo Python externo possui formato inseguro."
        )
    return version


def resolve_imported_python_module_contract(
    module_name: str,
    *,
    contract_id: str,
    search_paths: Sequence[str] | None = None,
) -> ResolvedPythonModuleContract:
    """Resolve exatamente o arquivo fonte do modulo que ja foi importado.

    Nome, tamanho, mtime ou um path configurado isoladamente nunca autorizam o
    contrato. Modulo ausente, origem nao-fonte ou mais de um candidato importavel
    produzem erro fail-closed para que o chamador execute o fluxo integral.
    """

    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]*", module_name) is None:
        raise EducationFingerprintError("Nome de modulo Python externo invalido.")
    if re.fullmatch(r"[a-z0-9_.:-]+", contract_id) is None:
        raise EducationFingerprintError("Identificador de contrato externo invalido.")

    module = sys.modules.get(module_name)
    if module is None:
        raise EducationFingerprintError(
            f"Modulo Python externo ainda nao foi importado: {module_name}."
        )
    module_file = getattr(module, "__file__", None)
    spec = getattr(module, "__spec__", None)
    spec_origin = getattr(spec, "origin", None)
    if not isinstance(module_file, str) or not isinstance(spec_origin, str):
        raise EducationFingerprintError(
            f"Origem do modulo Python externo nao e verificavel: {module_name}."
        )
    try:
        resolved_origins = {
            Path(module_file).resolve(strict=True),
            Path(spec_origin).resolve(strict=True),
        }
    except (OSError, RuntimeError) as exc:
        raise EducationFingerprintError(
            f"Arquivo fonte do modulo Python externo indisponivel: {module_name}."
        ) from exc
    if len(resolved_origins) != 1:
        raise EducationFingerprintError(
            f"Import ambiguo para o modulo Python externo: {module_name}."
        )
    source_path = next(iter(resolved_origins))
    if source_path.suffix.casefold() != ".py" or not source_path.is_file():
        raise EducationFingerprintError(
            f"Modulo Python externo nao aponta para fonte .py: {module_name}."
        )

    candidates = _python_module_candidates(
        module_name,
        tuple(search_paths) if search_paths is not None else tuple(sys.path),
    )
    if candidates != {source_path}:
        raise EducationFingerprintError(
            f"Import ambiguo ou divergente para o modulo Python externo: {module_name}."
        )
    return ResolvedPythonModuleContract(
        contract_id=contract_id,
        module_name=module_name,
        source_path=source_path,
        version=_normalized_module_version(module),
    )


def digest_contract_files(
    repository_root: Path,
    *,
    allowlist: Sequence[str] = EDUCATION_CONTRACT_FILE_ALLOWLIST,
    external_contracts: Mapping[str, Path] | None = None,
    external_python_contracts: Sequence[ResolvedPythonModuleContract] = (),
) -> dict[str, Any]:
    root = Path(repository_root).resolve()
    if len(set(allowlist)) != len(allowlist):
        raise EducationFingerprintError("Allowlist de contratos possui duplicatas.")
    entries = []
    total_bytes = 0
    for value in allowlist:
        relative = _validate_relative_contract_path(value)
        path = root.joinpath(*relative.parts)
        if not path.is_file():
            raise EducationFingerprintError(
                f"Arquivo participante do contrato ausente: {relative.as_posix()}."
            )
        sha256, size = _hash_file(path)
        total_bytes += size
        entries.append(
            {
                "path": relative.as_posix(),
                "size": size,
                "sha256": sha256,
            }
        )
    entries.sort(key=lambda item: item["path"])
    external_entries = []
    external_ids: set[str] = set()
    for contract_id, path in sorted((external_contracts or {}).items()):
        if not re.fullmatch(r"[a-z0-9_.:-]+", contract_id):
            raise EducationFingerprintError(
                f"Identificador de contrato externo invalido: {contract_id!r}."
            )
        if contract_id in external_ids:
            raise EducationFingerprintError("Contrato externo duplicado.")
        external_ids.add(contract_id)
        external_path = Path(path)
        if not external_path.is_file():
            raise EducationFingerprintError(
                f"Contrato externo participante ausente: {contract_id}."
            )
        sha256, size = _hash_file(external_path)
        total_bytes += size
        external_entries.append(
            {"contractId": contract_id, "size": size, "sha256": sha256}
        )
    for contract in sorted(
        external_python_contracts,
        key=lambda item: (item.contract_id, item.module_name),
    ):
        if (
            re.fullmatch(r"[a-z0-9_.:-]+", contract.contract_id) is None
            or re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]*", contract.module_name) is None
        ):
            raise EducationFingerprintError("Contrato Python externo invalido.")
        if contract.contract_id in external_ids:
            raise EducationFingerprintError("Contrato externo duplicado.")
        external_ids.add(contract.contract_id)
        source_path = Path(contract.source_path)
        if source_path.suffix.casefold() != ".py" or not source_path.is_file():
            raise EducationFingerprintError(
                f"Fonte Python externa indisponivel: {contract.contract_id}."
            )
        sha256, size = _hash_file(source_path)
        total_bytes += size
        entry: dict[str, Any] = {
            "contractId": contract.contract_id,
            "moduleName": contract.module_name,
            "sourceKind": "python-module",
            "size": size,
            "sha256": sha256,
        }
        if contract.version is not None:
            entry["version"] = contract.version
        external_entries.append(entry)
    external_entries.sort(key=lambda item: str(item["contractId"]))
    aggregate = _sha256_bytes(
        canonical_json_bytes(
            {
                "algorithmVersion": CONTRACT_FILE_DIGEST_ALGORITHM_VERSION,
                "repositoryFiles": entries,
                "externalContracts": external_entries,
            }
        )
    )
    return {
        "schemaVersion": CONTRACT_DIGESTS_SCHEMA_VERSION,
        "algorithmVersion": CONTRACT_FILE_DIGEST_ALGORITHM_VERSION,
        "aggregateSha256": aggregate,
        "files": entries,
        "externalContracts": external_entries,
        "fileCount": len(entries) + len(external_entries),
        "bytesHashed": total_bytes,
    }


def runtime_contract() -> dict[str, str]:
    return {
        "python": platform.python_version(),
        "pythonImplementation": platform.python_implementation(),
        "pandas": pd.__version__,
        "numpy": np.__version__,
        "sourceDigestAlgorithm": SOURCE_DIGEST_ALGORITHM_VERSION,
    }


def build_input_fingerprint(
    source_digests: Mapping[str, Any],
    contract_digests: Mapping[str, Any],
    *,
    state_code: str = STATE_CODE,
    execution_parameters: Mapping[str, Any] | None = None,
    runtime: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    normalized_state = normalized_task_state_code(state_code)
    if source_digests.get("complete") is not True:
        raise EducationFingerprintError("Digests de fontes incompletos nao sao elegiveis.")
    source_ids = source_digests.get("sourceIds")
    if not isinstance(source_ids, list) or len(source_ids) != len(
        EDUCATION_SOURCE_DEFINITIONS
    ):
        raise EducationFingerprintError("Contrato de sourceIds incompleto.")
    parameters = dict(execution_parameters or {})
    identity = {
        "schemaVersion": TASK_SCHEMA_VERSION,
        "taskId": task_id_for_state(normalized_state),
        "stateCode": normalized_state,
        "algorithmVersion": INPUT_FINGERPRINT_ALGORITHM_VERSION,
        "sourceAlgorithmVersion": source_digests.get("algorithmVersion"),
        "sourceAggregateSha256": source_digests.get("aggregateSha256"),
        "sourceIds": source_ids,
        "contractAggregateSha256": contract_digests.get("aggregateSha256"),
        "runtime": dict(runtime or runtime_contract()),
        "executionParameters": parameters,
    }
    serialized = canonical_json_bytes(identity)
    return {
        "inputFingerprint": _sha256_bytes(serialized),
        "identity": identity,
        "bytesHashed": len(serialized),
    }


def expected_managed_output_paths(
    municipality_ids: Iterable[str],
    *,
    expected_municipality_count: int | None,
) -> tuple[str, ...]:
    """``expected_municipality_count`` vem de ``state_config``; ``None`` desliga
    a checagem de universo e existe apenas para fixtures."""
    identifiers = tuple(municipality_ids)
    invalid = sorted(
        {
            repr(value)
            for value in identifiers
            if not isinstance(value, str) or re.fullmatch(r"\d{7}", value) is None
        }
    )
    if invalid:
        raise EducationOutputIntegrityError(
            "manifest_invalid",
            f"Codigos IBGE devem permanecer texto com sete digitos: {invalid[:5]}.",
        )
    if len(set(identifiers)) != len(identifiers):
        raise EducationOutputIntegrityError(
            "manifest_invalid", "Universo municipal possui codigos duplicados."
        )
    if expected_municipality_count is not None:
        expected_total = expected_managed_output_count(expected_municipality_count)
        if len(identifiers) != expected_municipality_count:
            raise EducationOutputIntegrityError(
                "manifest_invalid",
                "Contrato estadual exige exatamente "
                f"{expected_municipality_count} municipios "
                f"({expected_total} outputs administrados); "
                f"recebeu {len(identifiers)}.",
            )
    return tuple(
        sorted(
            {
                *MANAGED_ROOT_OUTPUT_FILES,
                *(f"municipios/{identifier}.json" for identifier in identifiers),
            }
        )
    )


def _current_managed_paths(public_root: Path) -> set[str]:
    root = Path(public_root)
    observed = {
        name for name in ("index.json", "municipios_index.json") if (root / name).is_file()
    }
    municipal_root = root / "municipios"
    if municipal_root.is_dir():
        observed.update(
            f"municipios/{path.name}"
            for path in municipal_root.iterdir()
            if path.is_file() and re.fullmatch(r"\d{7}\.json", path.name)
        )
    return observed


def _output_tree_hash(entries: Sequence[Mapping[str, Any]]) -> str:
    digest = hashlib.sha256()
    for entry in sorted(entries, key=lambda item: str(item["path"])):
        digest.update(str(entry["path"]).encode("utf-8"))
        digest.update(b"\x00")
        digest.update(str(entry["sha256"]).encode("ascii"))
        digest.update(b"\x00")
        digest.update(str(entry["size"]).encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def build_output_manifest(
    public_root: Path,
    municipality_ids: Iterable[str],
    *,
    state_code: str = STATE_CODE,
    expected_municipality_count: int | None,
    managed_root: str = DEFAULT_MANAGED_ROOT,
) -> dict[str, Any]:
    normalized_state = normalized_task_state_code(state_code)
    if not isinstance(managed_root, str) or not managed_root.strip():
        raise EducationOutputIntegrityError(
            "manifest_invalid", "Raiz administrada deve ser texto nao vazio."
        )
    expected = set(
        expected_managed_output_paths(
            municipality_ids,
            expected_municipality_count=expected_municipality_count,
        )
    )
    observed = _current_managed_paths(public_root)
    missing = sorted(expected - observed)
    extra = sorted(observed - expected)
    if missing:
        raise EducationOutputIntegrityError(
            "output_missing", f"Outputs educacionais ausentes: {missing[:10]}."
        )
    if extra:
        raise EducationOutputIntegrityError(
            "output_extra", f"Outputs educacionais administrados extras: {extra[:10]}."
        )

    entries = []
    for relative in sorted(expected):
        sha256, size = _hash_file(Path(public_root) / Path(relative))
        entries.append({"path": relative, "size": size, "sha256": sha256})
    if expected_municipality_count is not None:
        expected_total = expected_managed_output_count(expected_municipality_count)
        if len(entries) != expected_total:
            raise EducationOutputIntegrityError(
                "manifest_invalid",
                f"Manifesto deve conter {expected_total} outputs.",
            )
    return {
        "schemaVersion": OUTPUT_MANIFEST_SCHEMA_VERSION,
        "stateCode": normalized_state,
        "managedRoot": managed_root,
        "managedOutputCount": len(entries),
        "treeAlgorithmVersion": OUTPUT_TREE_ALGORITHM_VERSION,
        "treeSha256": _output_tree_hash(entries),
        "totalBytes": sum(int(entry["size"]) for entry in entries),
        "files": entries,
    }


def _validate_output_manifest_structure(
    manifest: Any,
    municipality_ids: Iterable[str],
    *,
    state_code: str,
    expected_municipality_count: int | None,
    managed_root: str = DEFAULT_MANAGED_ROOT,
) -> tuple[dict[str, dict[str, Any]], tuple[str, ...]]:
    if not isinstance(manifest, dict):
        raise EducationOutputIntegrityError(
            "manifest_invalid", "outputManifest deve ser objeto."
        )
    if manifest.get("stateCode") != state_code:
        raise EducationOutputIntegrityError(
            "state_mismatch", "outputManifest pertence a outro estado."
        )
    if manifest.get("schemaVersion") != OUTPUT_MANIFEST_SCHEMA_VERSION:
        raise EducationOutputIntegrityError(
            "manifest_invalid", "Schema do outputManifest desconhecido."
        )
    if manifest.get("managedRoot") != managed_root:
        raise EducationOutputIntegrityError(
            "manifest_invalid", "Raiz administrada do outputManifest e invalida."
        )
    if manifest.get("treeAlgorithmVersion") != OUTPUT_TREE_ALGORITHM_VERSION:
        raise EducationOutputIntegrityError(
            "manifest_invalid", "Algoritmo da arvore de outputs e invalido."
        )
    expected = expected_managed_output_paths(
        municipality_ids,
        expected_municipality_count=expected_municipality_count,
    )
    files = manifest.get("files")
    if not isinstance(files, list):
        raise EducationOutputIntegrityError(
            "manifest_invalid", "Lista de outputs do manifesto e invalida."
        )
    by_path: dict[str, dict[str, Any]] = {}
    for entry in files:
        if not isinstance(entry, dict) or set(entry) != {"path", "size", "sha256"}:
            raise EducationOutputIntegrityError(
                "manifest_invalid", "Entrada do outputManifest e invalida."
            )
        relative = entry.get("path")
        size = entry.get("size")
        sha256 = entry.get("sha256")
        if not isinstance(relative, str) or relative in by_path:
            raise EducationOutputIntegrityError(
                "manifest_invalid", "Path ausente ou duplicado no outputManifest."
            )
        if relative not in {"index.json", "municipios_index.json"}:
            match = _MUNICIPAL_OUTPUT_PATTERN.fullmatch(relative)
            if match is None or not isinstance(match.group(1), str):
                raise EducationOutputIntegrityError(
                    "manifest_invalid", "Outro dominio entrou no outputManifest."
                )
        if isinstance(size, bool) or not isinstance(size, int) or size < 0:
            raise EducationOutputIntegrityError(
                "manifest_invalid", "Tamanho invalido no outputManifest."
            )
        if not isinstance(sha256, str) or _SHA256_PATTERN.fullmatch(sha256) is None:
            raise EducationOutputIntegrityError(
                "manifest_invalid", "SHA-256 invalido no outputManifest."
            )
        by_path[relative] = entry
    if tuple(sorted(by_path)) != expected:
        raise EducationOutputIntegrityError(
            "manifest_invalid", "Conjunto de paths do outputManifest diverge do contrato."
        )
    if manifest.get("managedOutputCount") != len(expected):
        raise EducationOutputIntegrityError(
            "manifest_invalid", "Contagem do outputManifest diverge do contrato."
        )
    if manifest.get("totalBytes") != sum(entry["size"] for entry in by_path.values()):
        raise EducationOutputIntegrityError(
            "manifest_invalid", "Total de bytes do outputManifest e invalido."
        )
    if manifest.get("treeSha256") != _output_tree_hash(list(by_path.values())):
        raise EducationOutputIntegrityError(
            "manifest_invalid", "Hash agregado do outputManifest e invalido."
        )
    return by_path, expected


def verify_output_manifest(
    public_root: Path,
    manifest: Any,
    municipality_ids: Iterable[str],
    *,
    state_code: str = STATE_CODE,
    expected_municipality_count: int | None,
    managed_root: str = DEFAULT_MANAGED_ROOT,
) -> OutputIntegrityResult:
    try:
        entries, expected = _validate_output_manifest_structure(
            manifest,
            municipality_ids,
            state_code=state_code,
            expected_municipality_count=expected_municipality_count,
            managed_root=managed_root,
        )
    except EducationOutputIntegrityError as exc:
        return OutputIntegrityResult(False, exc.reason)

    observed = _current_managed_paths(public_root)
    expected_set = set(expected)
    if expected_set - observed:
        return OutputIntegrityResult(False, "output_missing")
    if observed - expected_set:
        return OutputIntegrityResult(False, "output_extra")
    verified_bytes = 0
    for relative in expected:
        path = Path(public_root) / Path(relative)
        try:
            size = path.stat().st_size
        except OSError:
            return OutputIntegrityResult(False, "output_missing")
        expected_entry = entries[relative]
        if size != expected_entry["size"]:
            return OutputIntegrityResult(
                False,
                "output_changed",
                managed_outputs=len(expected),
                output_bytes_verified=verified_bytes,
            )
        sha256, hashed_size = _hash_file(path)
        verified_bytes += hashed_size
        if sha256 != expected_entry["sha256"]:
            return OutputIntegrityResult(
                False,
                "output_changed",
                managed_outputs=len(expected),
                output_bytes_verified=verified_bytes,
            )
    return OutputIntegrityResult(
        True,
        "eligible",
        managed_outputs=len(expected),
        output_bytes_verified=verified_bytes,
    )


def default_task_state_path(
    data_pipeline_directory: Path,
    state_code: object = STATE_CODE,
) -> Path:
    return (
        Path(data_pipeline_directory)
        / "export"
        / "task-state"
        / normalized_task_state_code(state_code)
        / "education-core.json"
    )


def _validate_task_state_structure(
    payload: Any,
    *,
    state_code: object | None = None,
) -> None:
    if not isinstance(payload, dict):
        raise EducationFingerprintError("Task state deve ser objeto JSON.")
    required = {
        "schemaVersion",
        "taskId",
        "stateCode",
        "algorithmVersion",
        "inputFingerprint",
        "sourceDigests",
        "contractDigests",
        "runtime",
        "executionParameters",
        "outputManifest",
        "eligibility",
        "createdAt",
    }
    if set(payload) != required:
        raise EducationFingerprintError("Campos do task state divergem do contrato.")
    if payload.get("schemaVersion") != TASK_SCHEMA_VERSION:
        raise EducationFingerprintError("Schema do task state desconhecido.")
    try:
        observed_state = normalized_task_state_code(payload.get("stateCode"))
    except EducationFingerprintError as exc:
        raise EducationOutputIntegrityError(
            "state_mismatch", f"Task state sem estado valido: {exc}"
        ) from exc
    if state_code is not None and observed_state != normalized_task_state_code(state_code):
        raise EducationOutputIntegrityError(
            "state_mismatch", "Task state pertence a outro estado."
        )
    if payload.get("taskId") != task_id_for_state(observed_state):
        raise EducationFingerprintError("Task state pertence a outra tarefa.")
    if payload.get("algorithmVersion") != INPUT_FINGERPRINT_ALGORITHM_VERSION:
        raise EducationFingerprintError("Algoritmo do task state desconhecido.")
    fingerprint = payload.get("inputFingerprint")
    if not isinstance(fingerprint, str) or _SHA256_PATTERN.fullmatch(fingerprint) is None:
        raise EducationFingerprintError("inputFingerprint invalido no task state.")
    for field in ("sourceDigests", "contractDigests", "runtime", "executionParameters"):
        if not isinstance(payload.get(field), dict):
            raise EducationFingerprintError(f"{field} invalido no task state.")
    eligibility = payload.get("eligibility")
    if (
        not isinstance(eligibility, dict)
        or set(eligibility) != {"wouldSkip", "reason"}
        or not isinstance(eligibility.get("wouldSkip"), bool)
        or not isinstance(eligibility.get("reason"), str)
    ):
        raise EducationFingerprintError("Elegibilidade invalida no task state.")
    created_at = payload.get("createdAt")
    if not isinstance(created_at, str) or not created_at:
        raise EducationFingerprintError("createdAt invalido no task state.")
    serialized = canonical_json_bytes(payload)
    lowered = serialized.lower()
    for forbidden in (b"password", b"credential", b"connectionurl", b"environment"):
        if forbidden in lowered:
            raise EducationFingerprintError("Task state contem campo privado proibido.")


def load_task_state(
    path: Path,
    *,
    state_code: object | None = None,
) -> TaskStateLoadResult:
    state_path = Path(path)
    if not state_path.is_file():
        return TaskStateLoadResult(None, "first_run")
    try:
        payload = json.loads(
            state_path.read_text(encoding="utf-8"),
            parse_constant=lambda value: (_ for _ in ()).throw(
                ValueError(f"Constante JSON nao finita: {value}")
            ),
        )
        if (
            isinstance(payload, dict)
            and "algorithmVersion" in payload
            and payload.get("algorithmVersion")
            != INPUT_FINGERPRINT_ALGORITHM_VERSION
        ):
            return TaskStateLoadResult(None, "algorithm_changed")
        _validate_task_state_structure(payload, state_code=state_code)
    except EducationOutputIntegrityError as exc:
        return TaskStateLoadResult(None, exc.reason)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError, EducationFingerprintError):
        return TaskStateLoadResult(None, "manifest_invalid")
    if payload.get("outputManifest") is None:
        return TaskStateLoadResult(None, "manifest_missing")
    return TaskStateLoadResult(payload, "loaded")


def evaluate_shadow_eligibility(
    previous: TaskStateLoadResult,
    current_input: Mapping[str, Any],
    current_contracts: Mapping[str, Any],
    public_root: Path,
    municipality_ids: Iterable[str],
    *,
    state_code: str = STATE_CODE,
    expected_municipality_count: int | None,
    managed_root: str = DEFAULT_MANAGED_ROOT,
) -> ShadowDecision:
    empty_integrity = OutputIntegrityResult(False, previous.reason)
    if previous.state is None:
        return ShadowDecision(
            False,
            previous.reason,
            False,
            previous.reason == "manifest_invalid",
            empty_integrity,
        )
    state = previous.state
    previous_contract = state.get("contractDigests", {}).get("aggregateSha256")
    if previous_contract != current_contracts.get("aggregateSha256"):
        return ShadowDecision(
            False,
            "contract_changed",
            False,
            False,
            OutputIntegrityResult(False, "contract_changed"),
        )
    fingerprint_hit = state.get("inputFingerprint") == current_input.get(
        "inputFingerprint"
    )
    if not fingerprint_hit:
        return ShadowDecision(
            False,
            "input_changed",
            False,
            False,
            OutputIntegrityResult(False, "input_changed"),
        )
    integrity = verify_output_manifest(
        public_root,
        state.get("outputManifest"),
        municipality_ids,
        state_code=state_code,
        expected_municipality_count=expected_municipality_count,
        managed_root=managed_root,
    )
    return ShadowDecision(
        integrity.valid,
        integrity.reason,
        True,
        integrity.reason == "manifest_invalid",
        integrity,
    )


def build_task_state(
    *,
    input_fingerprint: Mapping[str, Any],
    source_digests: Mapping[str, Any],
    contract_digests: Mapping[str, Any],
    output_manifest: Mapping[str, Any],
    decision: ShadowDecision,
    created_at: str | None = None,
) -> dict[str, Any]:
    identity = input_fingerprint.get("identity")
    if not isinstance(identity, dict):
        raise EducationFingerprintError("Identidade do input fingerprint ausente.")
    manifest_state = normalized_task_state_code(output_manifest.get("stateCode"))
    if manifest_state != normalized_task_state_code(identity.get("stateCode")):
        raise EducationOutputIntegrityError(
            "state_mismatch",
            "Manifesto de outputs e fingerprint pertencem a estados diferentes.",
        )
    payload = {
        "schemaVersion": TASK_SCHEMA_VERSION,
        "taskId": task_id_for_state(manifest_state),
        "stateCode": manifest_state,
        "algorithmVersion": INPUT_FINGERPRINT_ALGORITHM_VERSION,
        "inputFingerprint": input_fingerprint["inputFingerprint"],
        "sourceDigests": dict(source_digests),
        "contractDigests": dict(contract_digests),
        "runtime": dict(identity["runtime"]),
        "executionParameters": dict(identity["executionParameters"]),
        "outputManifest": dict(output_manifest),
        "eligibility": {
            "wouldSkip": decision.would_skip,
            "reason": decision.reason,
        },
        "createdAt": created_at
        or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    _validate_task_state_structure(payload, state_code=manifest_state)
    managed_output_count = payload["outputManifest"]["managedOutputCount"]
    _validate_output_manifest_structure(
        payload["outputManifest"],
        (
            entry["path"].split("/")[1].removesuffix(".json")
            for entry in payload["outputManifest"]["files"]
            if entry["path"].startswith("municipios/")
        ),
        state_code=manifest_state,
        expected_municipality_count=(
            managed_output_count - MANAGED_ROOT_OUTPUT_COUNT
            if isinstance(managed_output_count, int)
            and not isinstance(managed_output_count, bool)
            and managed_output_count > MANAGED_ROOT_OUTPUT_COUNT
            else None
        ),
        managed_root=payload["outputManifest"]["managedRoot"],
    )
    return payload


def write_task_state_atomic(path: Path, payload: Mapping[str, Any]) -> None:
    state = dict(payload)
    _validate_task_state_structure(state)
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.{os.getpid()}.tmp")
    if temporary.exists():
        raise EducationFingerprintError(
            f"Temporario de task state ja existe: {temporary.name}."
        )
    content = json.dumps(
        state,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        indent=2,
        separators=(",", ": "),
    ) + "\n"
    try:
        with temporary.open("w", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
    finally:
        if temporary.exists():
            temporary.unlink()


def source_audit_rows(source_digests: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Projecao sanitizada para relatorios; nunca inclui valores analiticos."""
    rows = []
    for source_id, source in sorted(source_digests.get("sources", {}).items()):
        rows.append(
            {
                "sourceId": source_id,
                "frameKey": source.get("frameKey"),
                "relationId": source.get("relationId"),
                "origin": source.get("origin"),
                "nature": source.get("nature"),
                "rows": source.get("rowCount"),
                "columns": source.get("columnCount"),
                "operationalColumnsExcluded": source.get(
                    "operationalColumnsExcluded", []
                ),
                "participatesInFingerprint": True,
            }
        )
    return rows


__all__ = [
    "COLUMN_ORDER_POLICY",
    "CONTRACT_FILE_DIGEST_ALGORITHM_VERSION",
    "CONTRACT_DIGESTS_SCHEMA_VERSION",
    "EDUCATION_CONTRACT_FILE_ALLOWLIST",
    "EDUCATION_SOURCE_DEFINITIONS",
    "EducationFingerprintError",
    "EducationOutputIntegrityError",
    "EducationSourceDefinition",
    "DEFAULT_MANAGED_ROOT",
    "MANAGED_ROOT_OUTPUT_COUNT",
    "MANAGED_ROOT_OUTPUT_FILES",
    "TASK_NAMESPACE",
    "education_contract_file_allowlist",
    "expected_managed_output_count",
    "normalized_task_state_code",
    "task_id_for_state",
    "FLOAT_NORMALIZATION_DECIMAL_PLACES",
    "FLOAT_POLICY",
    "INPUT_FINGERPRINT_ALGORITHM_VERSION",
    "NULL_POLICY",
    "OUTPUT_MANIFEST_SCHEMA_VERSION",
    "ROW_ORDER_POLICY",
    "ResolvedPythonModuleContract",
    "SOURCE_DIGEST_ALGORITHM_VERSION",
    "STATE_CODE",
    "ShadowDecision",
    "TASK_ID",
    "TASK_SCHEMA_VERSION",
    "TaskStateLoadResult",
    "build_input_fingerprint",
    "build_output_manifest",
    "build_task_state",
    "canonical_json_bytes",
    "default_task_state_path",
    "digest_contract_files",
    "digest_education_sources",
    "digest_tabular_source",
    "evaluate_shadow_eligibility",
    "expected_managed_output_paths",
    "load_task_state",
    "runtime_contract",
    "resolve_imported_python_module_contract",
    "source_audit_rows",
    "verify_output_manifest",
    "write_task_state_atomic",
]
