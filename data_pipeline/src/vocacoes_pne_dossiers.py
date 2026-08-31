from __future__ import annotations

import gc
import hashlib
import json
import math
import os
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import pandas as pd

from .vocacoes_pne_job2 import directory_content_digest, write_csv_gzip


REPO_ROOT = Path(__file__).resolve().parents[2]
AA1_ROOT = REPO_ROOT / ".tmp" / "vocacoes-pne" / "advanced-analytics-v1" / "aa1"
AA2_ROOT = REPO_ROOT / ".tmp" / "vocacoes-pne" / "advanced-analytics-v1" / "aa2"
AA3_ROOT = REPO_ROOT / ".tmp" / "vocacoes-pne" / "advanced-analytics-v1" / "aa3"
CONTRACT_PATH = (
    REPO_ROOT
    / "data_pipeline"
    / "contracts"
    / "vocacoes-pne-aa4-dossiers-v1.json"
)
RUNNER_PATH = (
    REPO_ROOT / "data_pipeline" / "scripts" / "run_vocacoes_pne_dossiers.py"
)
PROGRAM_PLAN_PATH = (
    REPO_ROOT / "docs" / "PLANO_EXECUCAO_AVANCO_ANALITICO_VOCACOES_PNE.md"
)
DEFAULT_OUTPUT_ROOT = (
    REPO_ROOT / ".tmp" / "vocacoes-pne" / "advanced-analytics-v1" / "aa4"
)

AA1_MANIFEST_PATH = AA1_ROOT / "MANIFEST_AA1.json"
AA1_PANEL_PATH = AA1_ROOT / "PAINEL_ANALITICO_ESTADUAL_AA1.csv.gz"
AA1_CATALOG_PATH = AA1_ROOT / "CATALOGO_METRICAS_AA1.json"
AA2_MANIFEST_PATH = AA2_ROOT / "MANIFEST_AA2.json"
AA2_CLAIMS_PATH = AA2_ROOT / "CLAIMS_AA2.json"
AA2_RESULTS_PATH = AA2_ROOT / "RESULTADOS_AA2.csv.gz"
AA2_ROBUSTNESS_PATH = AA2_ROOT / "ROBUSTEZ_AA2.csv.gz"
AA2_SCOPE_PATH = AA2_ROOT / "COMPARACOES_ESCOPO_AA2.csv.gz"
AA2_HETEROGENEITY_PATH = AA2_ROOT / "HETEROGENEIDADE_AA2.csv.gz"
AA3_MANIFEST_PATH = AA3_ROOT / "MANIFEST_AA3.json"
AA3_LIBRARY_PATH = AA3_ROOT / "BIBLIOTECA_MECANISMOS_AA3.json"
AA3_BOUNDARIES_PATH = AA3_ROOT / "FRONTEIRAS_INTERPRETACAO_AA3.json"
AA3_EVIDENCE_PATH = AA3_ROOT / "EVIDENCIAS_COMPLEMENTARES_AA3.json"
AA3_QA_PATH = AA3_ROOT / "QA_SUMMARY_AA3.json"
AA4_OPUS_INITIAL_PATH = (
    REPO_ROOT
    / ".tmp"
    / "codex-analytics-program"
    / "aa4-opus-results"
    / "opus-result.json"
)
AA4_OPUS_REAUDIT_PATH = (
    REPO_ROOT
    / ".tmp"
    / "codex-analytics-program"
    / "aa4-opus-results-r2"
    / "opus-result.json"
)

EXPECTED_CONTRACT_SHA256 = (
    "3d052dd2397d4d83f68c8e2aa83809aea94d05dad04b40ccbc2637355128f198"
)
EXPECTED_INPUT_HASHES = {
    AA1_MANIFEST_PATH: "3e7870015bb501604a16d62dbcc730cc22c3131de15b8503c22cfc8c9815322b",
    AA1_PANEL_PATH: "d6cadfec911863b93699b826da6ef340687db5c0f77350319a9eeefa0dfb652f",
    AA1_CATALOG_PATH: "1d39b63a0bdf9e96eb997b1a66e960e20a38763d90c9ab29e0ddc60efa8ad027",
    AA2_MANIFEST_PATH: "e626762e37843673956c0aa27bcf0bbc099ffba2661cd413859f7ce433b75b2f",
    AA2_CLAIMS_PATH: "065f4f96d15591b4d239eebb5f18f0f6af0144daec47844dfae00d919fb09419",
    AA2_RESULTS_PATH: "fd0cabf0f487eefc724b506ddcbc8526d19b141fec42a63fdda24b7f281d971d",
    AA2_ROBUSTNESS_PATH: "4af1b3b83d6d4b7a0605df3078f03994da5896acf1360c8b5d8f8ea4ed09f68e",
    AA2_SCOPE_PATH: "2e1e0cdd8e6fd523f3f069a615d8a5f34d684ab45353aae5c573b7e2329b78e8",
    AA2_HETEROGENEITY_PATH: "2502a4572b6e7bca34a0930c8bc4093d8457684129a5dd82cc1f0b6c71692681",
    AA3_MANIFEST_PATH: "121eb0e0878f49dcde1c2c56e422fce27f4c96eaac889ad4c2a172282dba77ac",
    AA3_LIBRARY_PATH: "99e0177a71cc146c56331f79d1c72c82475524f8d87fc22cb0d889766fdf68b4",
    AA3_BOUNDARIES_PATH: "d8215995707c02e7e7324a2104819dc2142f5cf632eff5ef9b0806d09f3c1480",
    AA3_EVIDENCE_PATH: "03e8c0536b6f35a86daa3bd6c786d233c7e8381cf58969aa2a5d60ed48016f42",
    AA3_QA_PATH: "943424155b2773f6188c4c7520568e09c68a05c41f2f42626aabb1cd828140d1",
    PROGRAM_PLAN_PATH: "063e44ab88c763f8563b28a826c96a10585de8b92d9dc04b0b0cc04f1c465b71",
}
EXPECTED_AA1_ARTIFACT_SET_SHA256 = (
    "b5209061aff00ecae4b279165f3fd380b9324bcc845d1ad279a31a42f8bd3366"
)
EXPECTED_AA2_ARTIFACT_SET_SHA256 = (
    "b166cd6742cedb279a7c16316245e1ae08589b41c6e73b8cd3849c44fdd22879"
)
EXPECTED_AA3_ARTIFACT_SET_SHA256 = (
    "8fa9ed8d365873b2074b84ca49ca8fa0b6be9615b2d85771760fb3fb7ec5d464"
)
EXPECTED_PUBLIC_DATA_BASELINE_SHA256 = (
    "7efdf16f57a8e8da0c26fd27daa8e1331a427fa4376d8929c568ff471a0dafdd"
)
EXPECTED_AA4_OPUS_INITIAL_SHA256 = (
    "f6e2d22c2022331992e2e45d50d6e69178cdea26d8681c745d9361f15880d687"
)
EXPECTED_AA4_OPUS_REAUDIT_SHA256 = (
    "79c6144e02357e1b20dbf9c809b7f2f661a95e766464336a3af386b034bde300"
)

GENERATED_AT = "2026-08-30T19:27:00-03:00"
VALE_CODES = (
    "4303905",
    "4306403",
    "4307609",
    "4307708",
    "4310801",
    "4313375",
    "4313409",
    "4314803",
    "4318705",
    "4320008",
)
NSR_CODE = "4313375"
SCOPE_VALE = "VALE_10"
SCOPE_NSR = "MUNICIPALITY_4313375"

VALE_FILE = "DOSSIES_VALE_AA4.json"
NSR_FILE = "DOSSIES_NOVA_SANTA_RITA_AA4.json"
SCENARIOS_FILE = "CENARIOS_CONDICIONAIS_AA4.json"
AGENDAS_FILE = "AGENDAS_PLANEJAMENTO_AA4.json"
VISUALS_FILE = "MAPA_VISUAIS_AA4.json"
FACTS_FILE = "FATOS_RECONCILIADOS_AA4.csv.gz"
QA_FILE = "QA_SUMMARY_AA4.json"
MANIFEST_FILE = "MANIFEST_AA4.json"
NON_MANIFEST_FILES = (
    VALE_FILE,
    NSR_FILE,
    SCENARIOS_FILE,
    AGENDAS_FILE,
    VISUALS_FILE,
    FACTS_FILE,
    QA_FILE,
)

DOSSIER_IDS = (
    "D1_CONTEXT_AND_TRAJECTORY",
    "D2_DEMOGRAPHY_AND_NETWORK",
    "D3_YOUTH_WORK_AND_HIGH_SCHOOL",
    "D4_ECONOMIC_TRANSFORMATION_AND_EPT",
    "D5_ADULT_SCHOOLING_WORK_AND_EJA",
)
SCENARIO_IDS = (
    "SCN_DEMOGRAPHIC_PRESSURE_AND_NETWORK",
    "SCN_ECONOMIC_RECOMPOSITION_AND_REGIONAL_EPT",
    "SCN_ADULT_SCHOOLING_AND_EJA_COORDINATION",
)
AGENDA_IDS = (
    "AG1_TRAJECTORY_CONTEXT_MONITORING",
    "AG2_DEMOGRAPHY_NETWORK_COORDINATION",
    "AG3_YOUTH_WORK_EDUCATION_MONITORING",
    "AG4_REGIONAL_EPT_ACCESS_MAPPING",
    "AG5_EJA_BY_STAGE_REVIEW",
)

DATABASE_CLIENT_MODULE_ROOTS = {
    "duckdb",
    "mysql",
    "oracledb",
    "psycopg",
    "psycopg2",
    "pymongo",
    "pyodbc",
    "redis",
    "sqlalchemy",
}
NETWORK_CLIENT_MODULE_ROOTS = {
    "aiohttp",
    "boto3",
    "botocore",
    "ftplib",
    "httpx",
    "paramiko",
    "requests",
    "smtplib",
    "urllib3",
}


class DossierValidationError(RuntimeError):
    pass


def canonical_json_bytes(payload: Any) -> bytes:
    return (
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="wb", prefix=f".{path.name}.", suffix=".tmp", dir=path.parent, delete=False
    ) as stream:
        temporary = Path(stream.name)
        stream.write(canonical_json_bytes(payload))
        stream.flush()
        os.fsync(stream.fileno())
    try:
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


@contextmanager
def blocked_external_io_guard() -> Iterable[None]:
    original_socket_connect = socket.socket.connect
    original_create_connection = socket.create_connection
    original_sqlite_connect = sqlite3.connect

    def blocked(*_args: Any, **_kwargs: Any) -> Any:
        raise DossierValidationError(
            "AA4 usa somente artefatos locais congelados; conexão externa bloqueada"
        )

    socket.socket.connect = blocked  # type: ignore[method-assign]
    socket.create_connection = blocked
    sqlite3.connect = blocked  # type: ignore[assignment]
    try:
        yield
    finally:
        socket.socket.connect = original_socket_connect  # type: ignore[method-assign]
        socket.create_connection = original_create_connection
        sqlite3.connect = original_sqlite_connect  # type: ignore[assignment]


def _require_hash(path: Path, expected: str) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"Entrada congelada AA4 ausente: {path}")
    observed = sha256_file(path)
    if observed != expected:
        raise DossierValidationError(
            f"Hash divergente em {path.relative_to(REPO_ROOT).as_posix()}: "
            f"esperado {expected}, observado {observed}."
        )


def verify_frozen_inputs(*, verify_public_baseline: bool = True) -> dict[str, str]:
    _require_hash(CONTRACT_PATH, EXPECTED_CONTRACT_SHA256)
    for path, expected in EXPECTED_INPUT_HASHES.items():
        _require_hash(path, expected)

    contract = _load_json(CONTRACT_PATH)
    aa1_manifest = _load_json(AA1_MANIFEST_PATH)
    aa2_manifest = _load_json(AA2_MANIFEST_PATH)
    aa2_claims = _load_json(AA2_CLAIMS_PATH)
    aa3_manifest = _load_json(AA3_MANIFEST_PATH)
    aa3_library = _load_json(AA3_LIBRARY_PATH)
    aa3_qa = _load_json(AA3_QA_PATH)

    if contract.get("classification") != "DATA_LOGIC":
        raise DossierValidationError("Contrato AA4 perdeu a classificação DATA_LOGIC.")
    if contract.get("regionMunicipalityIbgeCodes") != list(VALE_CODES):
        raise DossierValidationError("Contrato AA4 perdeu o universo canônico do Vale.")
    if (
        contract.get("scope", {}).get("selectedMunicipalityIbgeCode") != NSR_CODE
        or contract.get("scope", {}).get("selectedMunicipalityContainedInRegion")
        is not True
        or contract.get("scope", {}).get("municipalityIdentity")
        != "textual_ibge_code_7_digits"
        or contract.get("scope", {}).get("educationNetworkScope")
        != "total_all_dependencies"
    ):
        raise DossierValidationError("Contrato AA4 perdeu identidade ou rede educacional.")
    if (
        len(contract.get("transversalDispositions", [])) != 4
        or contract.get("agendaSharingPolicy", {}).get("scopeVariantRequiredForEachAgenda")
        is not True
        or contract.get("scenarioPolicy", {}).get("aa5MayReduceBelowMinimum")
        is not False
        or set(contract.get("availabilityPolicy", {}))
        != {
            "observed",
            "observed_zero",
            "unavailable",
            "suppressed",
            "not_applicable",
            "row_absent",
        }
    ):
        raise DossierValidationError("Contrato AA4 perdeu reconciliações obrigatórias do Opus.")
    if aa1_manifest.get("artifactSetDigestSha256") != EXPECTED_AA1_ARTIFACT_SET_SHA256:
        raise DossierValidationError("Conjunto AA1 divergente.")
    if aa2_manifest.get("artifactSetDigestSha256") != EXPECTED_AA2_ARTIFACT_SET_SHA256:
        raise DossierValidationError("Conjunto AA2 divergente.")
    if aa3_manifest.get("artifactSetDigestSha256") != EXPECTED_AA3_ARTIFACT_SET_SHA256:
        raise DossierValidationError("Conjunto AA3 divergente.")
    if (
        aa3_manifest.get("finalState") != "AA3_COMPLETE_OPUS_REAUDIT_ON_TRACK"
        or aa3_manifest.get("opusReconciliation", {}).get("aa4Allowed") is not True
        or aa3_qa.get("failedCount") != 0
    ):
        raise DossierValidationError("AA3 não autorizou a entrada controlada do AA4.")
    if (
        aa2_claims.get("publicNarrativeAllowed") is not False
        or aa3_library.get("downstreamState")
        != "AA4_NARRATIVE_DOSSIER_INPUT_ONLY_NOT_PUBLIC"
    ):
        raise DossierValidationError("AA4 tentou promover diretamente insumo interno.")
    baseline = contract.get("publicDataBaseline", {})
    if (
        baseline.get("treeDigestSha256") != EXPECTED_PUBLIC_DATA_BASELINE_SHA256
        or baseline.get("consecutiveIdenticalChecks") != 2
        or baseline.get("automaticRebaselineAllowed") is not False
        or contract.get("generation", {}).get("publicDataWritesAllowed") is not False
    ):
        raise DossierValidationError("Baseline público explícito AA4 divergente.")
    if verify_public_baseline:
        public_digest = directory_content_digest(REPO_ROOT / "public/data")
        if public_digest != EXPECTED_PUBLIC_DATA_BASELINE_SHA256:
            raise DossierValidationError(
                "public/data divergiu do baseline explícito AA4; rebaseline automático é proibido."
            )
    else:
        public_digest = EXPECTED_PUBLIC_DATA_BASELINE_SHA256

    hashes = {
        "contractSha256": EXPECTED_CONTRACT_SHA256,
        **{
            path.relative_to(REPO_ROOT).as_posix(): expected
            for path, expected in EXPECTED_INPUT_HASHES.items()
        },
        "publicDataTreeDigestSha256": public_digest,
    }
    return hashes


def verify_opus_reconciliation() -> dict[str, Any]:
    _require_hash(AA4_OPUS_INITIAL_PATH, EXPECTED_AA4_OPUS_INITIAL_SHA256)
    _require_hash(AA4_OPUS_REAUDIT_PATH, EXPECTED_AA4_OPUS_REAUDIT_SHA256)
    initial = _load_json(AA4_OPUS_INITIAL_PATH)
    reaudit = _load_json(AA4_OPUS_REAUDIT_PATH)
    if initial.get("verdict") != "ON_TRACK" or reaudit.get("verdict") != "ON_TRACK":
        raise DossierValidationError("Parecer Opus AA4 não está ON_TRACK.")
    if "Permit AA5 to start" not in str(reaudit.get("recommended_next_action", "")):
        raise DossierValidationError("Releitura Opus AA4 não autorizou entrada controlada no AA5.")
    return {
        "initial": {
            "path": AA4_OPUS_INITIAL_PATH.relative_to(REPO_ROOT).as_posix(),
            "sha256": EXPECTED_AA4_OPUS_INITIAL_SHA256,
            "verdict": initial["verdict"],
            "confidence": initial["confidence"],
        },
        "reAudit": {
            "path": AA4_OPUS_REAUDIT_PATH.relative_to(REPO_ROOT).as_posix(),
            "sha256": EXPECTED_AA4_OPUS_REAUDIT_SHA256,
            "verdict": reaudit["verdict"],
            "confidence": reaudit["confidence"],
            "aa5EntryAllowed": True,
            "entryConditionsReconciled": True,
        },
    }


FACT_COLUMNS = (
    "fact_id",
    "dossier_id",
    "scope_id",
    "fact_type",
    "question_id",
    "result_id",
    "result_role",
    "metric_id",
    "dimension_id",
    "dimension_label",
    "period_start",
    "period_end",
    "value_start",
    "value_end",
    "absolute_change",
    "percent_change",
    "percent_change_state",
    "effect_estimate",
    "interval_lower",
    "interval_upper",
    "p_value_raw",
    "p_value_bh",
    "unit",
    "availability_state_start",
    "availability_state_end",
    "aggregation_method",
    "municipality_count",
    "universe",
    "territorial_lens",
    "network_scope",
    "source_ref",
    "claim_ceiling",
    "terminal_state",
    "manager_facing_eligible",
    "interpretation_guard",
)


def _blank_fact(**values: Any) -> dict[str, Any]:
    fact = {column: None for column in FACT_COLUMNS}
    unknown = set(values) - set(fact)
    if unknown:
        raise DossierValidationError(f"Campos de fato AA4 desconhecidos: {sorted(unknown)}")
    fact.update(values)
    return fact


def _load_sources() -> dict[str, Any]:
    panel = pd.read_csv(
        AA1_PANEL_PATH,
        dtype={
            "municipality_ibge_code": "string",
            "year_or_reference_period": "string",
            "source_period": "string",
        },
        low_memory=False,
    )
    results = pd.read_csv(AA2_RESULTS_PATH, low_memory=False)
    robustness = pd.read_csv(AA2_ROBUSTNESS_PATH, low_memory=False)
    comparisons = pd.read_csv(AA2_SCOPE_PATH, low_memory=False)
    heterogeneity = pd.read_csv(
        AA2_HETEROGENEITY_PATH,
        dtype={"municipality_ibge_code": "string"},
        low_memory=False,
    )
    if (
        panel["municipality_ibge_code"].isna().any()
        or not panel["municipality_ibge_code"].str.fullmatch(r"\d{7}").all()
        or heterogeneity["municipality_ibge_code"].isna().any()
        or not heterogeneity["municipality_ibge_code"].str.fullmatch(r"\d{7}").all()
    ):
        raise DossierValidationError("Código municipal deixou de ser texto IBGE com sete dígitos.")
    if set(VALE_CODES) - set(panel["municipality_ibge_code"].unique()):
        raise DossierValidationError("Painel AA1 não contém os dez municípios do Vale.")
    return {
        "panel": panel,
        "results": results,
        "robustness": robustness,
        "comparisons": comparisons,
        "heterogeneity": heterogeneity,
        "claims": _load_json(AA2_CLAIMS_PATH),
        "library": _load_json(AA3_LIBRARY_PATH),
        "boundaries": _load_json(AA3_BOUNDARIES_PATH),
    }


def _single_value(values: pd.Series, *, label: str) -> Any:
    unique = values.dropna().unique().tolist()
    if len(unique) != 1:
        raise DossierValidationError(f"{label} deveria ter um valor único; observados {unique}.")
    return unique[0]


def _aggregate_panel_series(
    panel: pd.DataFrame,
    *,
    codes: Sequence[str],
    metric_id: str,
    stage: str,
    dimension_id: str,
    aggregation: str,
) -> list[dict[str, Any]]:
    selected = panel.loc[
        panel["municipality_ibge_code"].isin(codes)
        & panel["metric_id"].eq(metric_id)
        & panel["stage_or_population_group"].eq(stage)
        & panel["dimension_id"].astype("string").eq(dimension_id)
    ].copy()
    if selected.empty:
        raise DossierValidationError(
            f"Série AA1 ausente: {metric_id}/{stage}/{dimension_id}."
        )
    if selected.duplicated(
        ["municipality_ibge_code", "year_or_reference_period"]
    ).any():
        raise DossierValidationError(f"Série AA1 duplicada: {metric_id}/{stage}.")
    if not selected["availability_state"].isin(["observed", "observed_zero"]).all():
        states = sorted(selected["availability_state"].unique())
        raise DossierValidationError(
            f"Série AA1 selecionada contém indisponibilidade: {metric_id} {states}."
        )
    selected["raw_value"] = pd.to_numeric(selected["raw_value"], errors="raise")
    if selected["raw_value"].isna().any():
        raise DossierValidationError(f"Série AA1 observada contém nulo: {metric_id}.")
    expected_count = len(codes)
    counts = selected.groupby("year_or_reference_period")[
        "municipality_ibge_code"
    ].nunique()
    if not counts.eq(expected_count).all():
        raise DossierValidationError(
            f"Cobertura temporal incompleta em {metric_id}: {counts.to_dict()}."
        )
    if aggregation == "sum_municipalities":
        grouped = selected.groupby("year_or_reference_period", sort=True)[
            "raw_value"
        ].sum()
    elif aggregation == "median_municipalities":
        grouped = selected.groupby("year_or_reference_period", sort=True)[
            "raw_value"
        ].median()
    elif aggregation == "identity_municipality" and expected_count == 1:
        grouped = selected.set_index("year_or_reference_period")["raw_value"].sort_index()
    else:
        raise DossierValidationError(f"Agregação AA4 inválida: {aggregation}.")
    source_refs = "|".join(sorted(selected["source_ref"].dropna().unique()))
    metadata = {
        "unit": str(_single_value(selected["unit"], label=f"unidade {metric_id}")),
        "universe": str(
            _single_value(selected["universe"], label=f"universo {metric_id}")
        ),
        "territorial_lens": str(
            _single_value(
                selected["territorial_lens"], label=f"lente {metric_id}"
            )
        ),
        "network_scope": str(
            _single_value(
                selected["network_scope"], label=f"rede {metric_id}"
            )
        ),
        "source_ref": source_refs,
        "municipality_count": expected_count,
        "aggregation_method": aggregation,
    }
    return [
        {
            "period": str(period),
            "value": float(value),
            "availability_state": "observed_zero" if float(value) == 0.0 else "observed",
            **metadata,
        }
        for period, value in grouped.items()
    ]


def _append_series_facts(
    facts: list[dict[str, Any]],
    *,
    prefix: str,
    dossier_id: str,
    scope_id: str,
    question_id: str | None,
    metric_id: str,
    dimension_id: str,
    dimension_label: str,
    series: Sequence[Mapping[str, Any]],
    claim_ceiling: str,
    terminal_state: str,
    interpretation_guard: str,
    manager_facing_eligible: bool = True,
) -> list[str]:
    fact_ids: list[str] = []
    for item in series:
        fact_id = f"{prefix}_{item['period']}"
        fact_ids.append(fact_id)
        facts.append(
            _blank_fact(
                fact_id=fact_id,
                dossier_id=dossier_id,
                scope_id=scope_id,
                fact_type="AA1_TIME_SERIES_POINT",
                question_id=question_id,
                metric_id=metric_id,
                dimension_id=dimension_id,
                dimension_label=dimension_label,
                period_start=item["period"],
                period_end=item["period"],
                value_start=item["value"],
                value_end=item["value"],
                unit=item["unit"],
                availability_state_start=item["availability_state"],
                availability_state_end=item["availability_state"],
                aggregation_method=item["aggregation_method"],
                municipality_count=item["municipality_count"],
                universe=item["universe"],
                territorial_lens=item["territorial_lens"],
                network_scope=item["network_scope"],
                source_ref=item["source_ref"],
                claim_ceiling=claim_ceiling,
                terminal_state=terminal_state,
                manager_facing_eligible=manager_facing_eligible,
                interpretation_guard=interpretation_guard,
            )
        )
    return fact_ids


def _append_change_fact(
    facts: list[dict[str, Any]],
    *,
    fact_id: str,
    dossier_id: str,
    scope_id: str,
    question_id: str | None,
    metric_id: str,
    dimension_id: str,
    dimension_label: str,
    series: Sequence[Mapping[str, Any]],
    period_start: str,
    period_end: str,
    claim_ceiling: str,
    terminal_state: str,
    interpretation_guard: str,
    manager_facing_eligible: bool = True,
) -> str:
    by_period = {str(item["period"]): item for item in series}
    if period_start not in by_period or period_end not in by_period:
        raise DossierValidationError(
            f"Períodos ausentes para mudança {fact_id}: {period_start}/{period_end}."
        )
    start = by_period[period_start]
    end = by_period[period_end]
    value_start = float(start["value"])
    value_end = float(end["value"])
    absolute_change = value_end - value_start
    if value_start == 0.0:
        percent_change = None
        percent_state = "NOT_APPLICABLE_ZERO_START"
    else:
        percent_change = (absolute_change / value_start) * 100.0
        percent_state = "COMPUTED_FROM_OBSERVED_VALUES"
    facts.append(
        _blank_fact(
            fact_id=fact_id,
            dossier_id=dossier_id,
            scope_id=scope_id,
            fact_type="AA1_OBSERVED_CHANGE",
            question_id=question_id,
            metric_id=metric_id,
            dimension_id=dimension_id,
            dimension_label=dimension_label,
            period_start=period_start,
            period_end=period_end,
            value_start=value_start,
            value_end=value_end,
            absolute_change=absolute_change,
            percent_change=percent_change,
            percent_change_state=percent_state,
            unit=start["unit"],
            availability_state_start=start["availability_state"],
            availability_state_end=end["availability_state"],
            aggregation_method=start["aggregation_method"],
            municipality_count=start["municipality_count"],
            universe=start["universe"],
            territorial_lens=start["territorial_lens"],
            network_scope=start["network_scope"],
            source_ref=start["source_ref"],
            claim_ceiling=claim_ceiling,
            terminal_state=terminal_state,
            manager_facing_eligible=manager_facing_eligible,
            interpretation_guard=interpretation_guard,
        )
    )
    return fact_id


def _comparison_fact(
    comparisons: pd.DataFrame,
    *,
    fact_id: str,
    dossier_id: str,
    question_id: str,
    measure_id: str,
    scope_id: str,
    claim_ceiling: str,
    terminal_state: str,
    interpretation_guard: str,
    manager_facing_eligible: bool = True,
) -> dict[str, Any]:
    selected = comparisons.loc[
        comparisons["question_id"].eq(question_id)
        & comparisons["measure_id"].eq(measure_id)
        & comparisons["scope_id"].eq(scope_id)
    ]
    if len(selected) != 1:
        raise DossierValidationError(
            f"Comparação AA2 não única: {question_id}/{measure_id}/{scope_id}."
        )
    row = selected.iloc[0]
    state = str(row["scope_state"])
    value = None if pd.isna(row["value"]) else float(row["value"])
    return _blank_fact(
        fact_id=fact_id,
        dossier_id=dossier_id,
        scope_id=scope_id,
        fact_type="AA2_SCOPE_COMPARISON",
        question_id=question_id,
        metric_id=measure_id,
        dimension_id="AA2_SCOPE_MEASURE",
        dimension_label=measure_id,
        period_start="AA2_DECLARED_PERIOD",
        period_end="AA2_DECLARED_PERIOD",
        value_start=value,
        value_end=value,
        unit=str(row["unit"]),
        availability_state_start=state,
        availability_state_end=state,
        aggregation_method="AA2_SCOPE_CONTRACT",
        municipality_count=int(row["municipality_count"]),
        universe=str(row["coverage_scope"]),
        territorial_lens="AS_DECLARED_IN_AA2_SOURCE_MEASURE",
        network_scope="AS_DECLARED_IN_AA2_SOURCE_MEASURE",
        source_ref=(
            f"{AA2_SCOPE_PATH.relative_to(REPO_ROOT).as_posix()}#"
            f"{question_id}/{measure_id}/{scope_id}"
        ),
        claim_ceiling=claim_ceiling,
        terminal_state=terminal_state,
        manager_facing_eligible=manager_facing_eligible and state == "AVAILABLE",
        interpretation_guard=interpretation_guard,
    )


def _result_fact(
    results: pd.DataFrame,
    *,
    fact_id: str,
    dossier_id: str,
    result_id: str,
    manager_facing_eligible: bool,
    interpretation_guard: str | None = None,
) -> dict[str, Any]:
    selected = results.loc[results["result_id"].eq(result_id)]
    if len(selected) != 1:
        raise DossierValidationError(f"Resultado AA2 não único: {result_id}.")
    row = selected.iloc[0]

    def number(column: str) -> float | None:
        return None if pd.isna(row[column]) else float(row[column])

    return _blank_fact(
        fact_id=fact_id,
        dossier_id=dossier_id,
        scope_id=str(row["coverage_scope"]),
        fact_type="AA2_ANALYTICAL_RESULT",
        question_id=str(row["question_id"]),
        result_id=str(row["result_id"]),
        result_role=str(row["result_role"]),
        metric_id=str(row["numerator_metric_id"]),
        dimension_id=str(row["method_id"]),
        dimension_label=str(row["method_id"]),
        period_start="AA2_PREREGISTERED_WINDOW",
        period_end="AA2_PREREGISTERED_WINDOW",
        value_start=number("effect_estimate"),
        value_end=number("effect_estimate"),
        effect_estimate=number("effect_estimate"),
        interval_lower=number("interval_lower"),
        interval_upper=number("interval_upper"),
        p_value_raw=number("p_value_raw"),
        p_value_bh=number("p_value_bh"),
        unit=str(row["effect_unit"]),
        availability_state_start=str(row["interval_state"]),
        availability_state_end=str(row["interval_state"]),
        aggregation_method=str(row["method_id"]),
        municipality_count=int(row["analytic_municipality_count"]),
        universe=str(row["coverage_scope"]),
        territorial_lens=str(row["numerator_territorial_lens"]),
        network_scope="AS_DECLARED_IN_AA2_RESULT",
        source_ref=(
            f"{AA2_RESULTS_PATH.relative_to(REPO_ROOT).as_posix()}#{result_id}"
        ),
        claim_ceiling=str(row["claim_ceiling"]),
        terminal_state=str(row["terminal_state"]),
        manager_facing_eligible=manager_facing_eligible,
        interpretation_guard=(
            interpretation_guard
            if interpretation_guard is not None
            else str(row["interpretation_guard"])
        ),
    )


PRESENTATION_LABELS = {
    "47": "Comércio varejista",
    "52": "Armazenamento e atividades auxiliares dos transportes",
    "78": "Seleção, agenciamento e locação de mão de obra",
    "49": "Transporte terrestre",
    "45": "Comércio e reparação de veículos",
    "82": "Serviços de escritório e apoio administrativo",
    "62": "Serviços de tecnologia da informação",
    "28": "Fabricação de máquinas e equipamentos",
    "86": "Atenção à saúde humana",
    "414140": "Auxiliar de logística",
    "782510": "Motorista de caminhão",
    "414215": "Conferente de carga e descarga",
    "782220": "Operador de empilhadeira",
    "782515": "Motorista operacional de guincho",
    "422310": "Operador de telemarketing ativo e receptivo",
    "411010": "Assistente administrativo",
    "231210": "Professor do ensino fundamental — anos iniciais",
    "521140": "Atendente de lojas e mercados",
}


def _top_change_facts(
    panel: pd.DataFrame,
    *,
    facts: list[dict[str, Any]],
    prefix: str,
    scope_id: str,
    codes: Sequence[str],
    metric_id: str,
    top_n: int,
) -> list[str]:
    selected = panel.loc[
        panel["municipality_ibge_code"].isin(codes)
        & panel["metric_id"].eq(metric_id)
        & panel["year_or_reference_period"].isin(["2019", "2025"])
        & panel["availability_state"].isin(["observed", "observed_zero"])
    ].copy()
    if selected.empty:
        raise DossierValidationError(f"Mudanças econômicas ausentes: {metric_id}.")
    selected["raw_value"] = pd.to_numeric(selected["raw_value"], errors="raise")
    coverage = selected.groupby(
        ["dimension_id", "year_or_reference_period"]
    )["municipality_ibge_code"].nunique()
    complete_dimensions = {
        dimension
        for dimension in selected["dimension_id"].unique()
        if coverage.get((dimension, "2019"), 0) == len(codes)
        and coverage.get((dimension, "2025"), 0) == len(codes)
    }
    selected = selected.loc[selected["dimension_id"].isin(complete_dimensions)]
    grouped = (
        selected.groupby(
            ["dimension_id", "dimension_label", "year_or_reference_period"],
            sort=True,
        )["raw_value"]
        .sum()
        .unstack("year_or_reference_period")
        .dropna(subset=["2019", "2025"])
    )
    grouped["change"] = grouped["2025"] - grouped["2019"]
    top = grouped.loc[grouped["change"] > 0].sort_values(
        ["change", "2025"], ascending=[False, False], kind="stable"
    ).head(top_n)
    if len(top) != top_n:
        raise DossierValidationError(
            f"Mudança econômica {metric_id} não produziu {top_n} dimensões completas."
        )
    source_ref = "|".join(sorted(selected["source_ref"].dropna().unique()))
    unit = str(_single_value(selected["unit"], label=f"unidade {metric_id}"))
    universe = str(
        _single_value(selected["universe"], label=f"universo {metric_id}")
    )
    lens = str(
        _single_value(selected["territorial_lens"], label=f"lente {metric_id}")
    )
    fact_ids: list[str] = []
    for (dimension_id, source_label), row in top.iterrows():
        dimension_text = str(dimension_id)
        fact_id = f"{prefix}_{dimension_text}"
        fact_ids.append(fact_id)
        value_start = float(row["2019"])
        value_end = float(row["2025"])
        absolute_change = float(row["change"])
        percent_change = (
            None
            if value_start == 0.0
            else (absolute_change / value_start) * 100.0
        )
        facts.append(
            _blank_fact(
                fact_id=fact_id,
                dossier_id="D4_ECONOMIC_TRANSFORMATION_AND_EPT",
                scope_id=scope_id,
                fact_type="AA1_TOP_OBSERVED_ECONOMIC_CHANGE",
                question_id="P5_OCCUPATIONS_AND_EPT",
                metric_id=metric_id,
                dimension_id=dimension_text,
                dimension_label=PRESENTATION_LABELS.get(
                    dimension_text, str(source_label)
                ),
                period_start="2019",
                period_end="2025",
                value_start=value_start,
                value_end=value_end,
                absolute_change=absolute_change,
                percent_change=percent_change,
                percent_change_state=(
                    "NOT_APPLICABLE_ZERO_START"
                    if value_start == 0.0
                    else "COMPUTED_FROM_OBSERVED_VALUES"
                ),
                unit=unit,
                availability_state_start=(
                    "observed_zero" if value_start == 0.0 else "observed"
                ),
                availability_state_end=(
                    "observed_zero" if value_end == 0.0 else "observed"
                ),
                aggregation_method=(
                    "sum_municipalities" if len(codes) > 1 else "identity_municipality"
                ),
                municipality_count=len(codes),
                universe=universe,
                territorial_lens=lens,
                network_scope="not_applicable",
                source_ref=source_ref,
                claim_ceiling="OBSERVED_FACT",
                terminal_state="DESCRIPTIVE_ECONOMIC_CHANGE_ONLY",
                manager_facing_eligible=True,
                interpretation_guard=(
                    "RANKED_AMONG_DIMENSIONS_OBSERVED_IN_BOTH_2019_AND_2025; "
                    "NOT_DEMAND_NOT_FORECAST_NOT_SAME_PERSON_AS_EDUCATION"
                ),
            )
        )
    return fact_ids


def _build_facts(sources: Mapping[str, Any]) -> tuple[pd.DataFrame, dict[str, list[str]]]:
    panel: pd.DataFrame = sources["panel"]
    results: pd.DataFrame = sources["results"]
    comparisons: pd.DataFrame = sources["comparisons"]
    facts: list[dict[str, Any]] = []
    groups: dict[str, list[str]] = {}

    claim_state = {
        claim["questionId"]: (claim["claimCeiling"], claim["terminalState"])
        for claim in sources["claims"]["claims"]
    }

    def add_comparison(
        fact_id: str,
        dossier_id: str,
        question_id: str,
        measure_id: str,
        scope_id: str,
        guard: str,
        *,
        eligible: bool = True,
    ) -> None:
        ceiling, terminal = claim_state[question_id]
        facts.append(
            _comparison_fact(
                comparisons,
                fact_id=fact_id,
                dossier_id=dossier_id,
                question_id=question_id,
                measure_id=measure_id,
                scope_id=scope_id,
                claim_ceiling=ceiling,
                terminal_state=terminal,
                interpretation_guard=guard,
                manager_facing_eligible=eligible,
            )
        )

    for scope_id in (SCOPE_NSR, SCOPE_VALE, "RS_497"):
        scope_tag = {
            SCOPE_NSR: "NSR",
            SCOPE_VALE: "VALE",
            "RS_497": "RS",
        }[scope_id]
        add_comparison(
            f"F_D1_{scope_tag}_P1_RESIDUAL",
            "D1_CONTEXT_AND_TRAJECTORY",
            "P1_CONTEXT_ADJUSTED_TRAJECTORY",
            "HELD_OUT_DROPOUT_RESIDUAL_MEDIAN",
            scope_id,
            "CONTEXT_COMPARISON_WITH_PREDICTION_UNCERTAINTY; NON_FLAGGING_IS_NOT_TYPICALITY",
        )
        for measure in (
            "MUNICIPAL_MEDIAN_DROPOUT_RATE_2025",
            "MUNICIPAL_MEDIAN_TEACHER_ADEQUACY_2025",
        ):
            add_comparison(
                f"F_D1_{scope_tag}_P3_{measure}",
                "D1_CONTEXT_AND_TRAJECTORY",
                "P3_SCHOOL_CONDITIONS_AND_TRAJECTORY",
                measure,
                scope_id,
                "OBSERVED_CONTEXT_ONLY; P3_TERMINAL_NO_ROBUST_ASSOCIATION",
            )
    facts.append(
        _result_fact(
            results,
            fact_id="F_D1_P1_MAIN_CONTEXT_RESULT",
            dossier_id="D1_CONTEXT_AND_TRAJECTORY",
            result_id="P1_MAIN_5F_FULL",
            manager_facing_eligible=True,
            interpretation_guard=(
                "WITHIN_OR_INCONCLUSIVE_CONTEXT; MODEL_FULL_DOES_NOT_IMPROVE_BASELINE; "
                "NON_FLAGGING_IS_NOT_TYPICALITY"
            ),
        )
    )
    facts.append(
        _result_fact(
            results,
            fact_id="F_D1_P3_MAIN_TECHNICAL_NEGATIVE",
            dossier_id="D1_CONTEXT_AND_TRAJECTORY",
            result_id="P3_MAIN_DROPOUT_L0",
            manager_facing_eligible=False,
            interpretation_guard=(
                "TECHNICAL_ONLY_ADJACENT_TO_NO_ROBUST_ASSOCIATION; NOT_CAUSAL"
            ),
        )
    )

    for scope_id, scope_tag, codes, aggregation in (
        (SCOPE_NSR, "NSR", [NSR_CODE], "identity_municipality"),
        (SCOPE_VALE, "VALE", VALE_CODES, "sum_municipalities"),
    ):
        population = _aggregate_panel_series(
            panel,
            codes=codes,
            metric_id="demography.population_age_15_17",
            stage="age_15_17",
            dimension_id="ALL",
            aggregation=aggregation,
        )
        enrollments = _aggregate_panel_series(
            panel,
            codes=codes,
            metric_id="education.enrollments",
            stage="medio",
            dimension_id="ALL",
            aggregation=aggregation,
        )
        groups[f"D2_{scope_tag}_POP_TS"] = _append_series_facts(
            facts,
            prefix=f"TS_D2_{scope_tag}_POP_15_17",
            dossier_id="D2_DEMOGRAPHY_AND_NETWORK",
            scope_id=scope_id,
            question_id="P2_DEMOGRAPHY_ENROLLMENT_DECOMPOSITION",
            metric_id="demography.population_age_15_17",
            dimension_id="ALL",
            dimension_label="População residente de 15 a 17 anos",
            series=population,
            claim_ceiling="OBSERVED_FACT",
            terminal_state="ACCOUNTING_DECOMPOSITION_COMPLETE",
            interpretation_guard="RESIDENT_POPULATION_LENS_ONLY",
        )
        groups[f"D2_{scope_tag}_ENROLL_TS"] = _append_series_facts(
            facts,
            prefix=f"TS_D2_{scope_tag}_HS_ENROLL",
            dossier_id="D2_DEMOGRAPHY_AND_NETWORK",
            scope_id=scope_id,
            question_id="P2_DEMOGRAPHY_ENROLLMENT_DECOMPOSITION",
            metric_id="education.enrollments",
            dimension_id="ALL",
            dimension_label="Matrículas do ensino médio por localização da escola",
            series=enrollments,
            claim_ceiling="OBSERVED_FACT",
            terminal_state="ACCOUNTING_DECOMPOSITION_COMPLETE",
            interpretation_guard="SCHOOL_LOCATION_NOT_STUDENT_RESIDENCE",
        )
        groups[f"D2_{scope_tag}_CHANGES"] = [
            _append_change_fact(
                facts,
                fact_id=f"F_D2_{scope_tag}_POP_CHANGE_2018_2025",
                dossier_id="D2_DEMOGRAPHY_AND_NETWORK",
                scope_id=scope_id,
                question_id="P2_DEMOGRAPHY_ENROLLMENT_DECOMPOSITION",
                metric_id="demography.population_age_15_17",
                dimension_id="ALL",
                dimension_label="População residente de 15 a 17 anos",
                series=population,
                period_start="2018",
                period_end="2025",
                claim_ceiling="OBSERVED_FACT",
                terminal_state="ACCOUNTING_DECOMPOSITION_COMPLETE",
                interpretation_guard="RESIDENT_POPULATION_LENS_ONLY",
            ),
            _append_change_fact(
                facts,
                fact_id=f"F_D2_{scope_tag}_HS_ENROLL_CHANGE_2018_2025",
                dossier_id="D2_DEMOGRAPHY_AND_NETWORK",
                scope_id=scope_id,
                question_id="P2_DEMOGRAPHY_ENROLLMENT_DECOMPOSITION",
                metric_id="education.enrollments",
                dimension_id="ALL",
                dimension_label="Matrículas do ensino médio",
                series=enrollments,
                period_start="2018",
                period_end="2025",
                claim_ceiling="OBSERVED_FACT",
                terminal_state="ACCOUNTING_DECOMPOSITION_COMPLETE",
                interpretation_guard="SCHOOL_LOCATION_NOT_COVERAGE_RATE",
            ),
        ]
        result_scope = scope_id
        for component, suffix in (
            ("POPULATION_COMPONENT", "POP_COMPONENT"),
            ("TERRITORIAL_RELATION_COMPONENT", "RELATION_COMPONENT"),
        ):
            result_id = f"P2_2018_2025_{result_scope}_{component}"
            fact_id = f"F_D2_{scope_tag}_{suffix}_2018_2025"
            facts.append(
                _result_fact(
                    results,
                    fact_id=fact_id,
                    dossier_id="D2_DEMOGRAPHY_AND_NETWORK",
                    result_id=result_id,
                    manager_facing_eligible=True,
                    interpretation_guard=(
                        "EXACT_ACCOUNTING_COMPONENT; RELATION_COMPONENT_IS_NOT_BEHAVIOR_OR_MIGRATION"
                    ),
                )
            )
            groups.setdefault(f"D2_{scope_tag}_COMPONENTS", []).append(fact_id)
    for component, suffix in (
        ("POPULATION_COMPONENT", "POP_COMPONENT"),
        ("TERRITORIAL_RELATION_COMPONENT", "RELATION_COMPONENT"),
    ):
        result_id = f"P2_2018_2025_RS_497_{component}"
        fact_id = f"F_D2_RS_{suffix}_2018_2025"
        facts.append(
            _result_fact(
                results,
                fact_id=fact_id,
                dossier_id="D2_DEMOGRAPHY_AND_NETWORK",
                result_id=result_id,
                manager_facing_eligible=True,
                interpretation_guard="EXACT_ACCOUNTING_COMPONENT_RS_REFERENCE",
            )
        )
        groups.setdefault("D2_RS_COMPONENTS", []).append(fact_id)

    for scope_id, scope_tag, codes, count_aggregation, rate_aggregation in (
        (SCOPE_NSR, "NSR", [NSR_CODE], "identity_municipality", "identity_municipality"),
        (SCOPE_VALE, "VALE", VALE_CODES, "sum_municipalities", "median_municipalities"),
    ):
        bonds = _aggregate_panel_series(
            panel,
            codes=codes,
            metric_id="labor.youth_rais.active_bonds",
            stage="age_15_17",
            dimension_id="ALL",
            aggregation=count_aggregation,
        )
        dropout = _aggregate_panel_series(
            panel,
            codes=codes,
            metric_id="education.dropout_rate_percent",
            stage="medio",
            dimension_id="ALL",
            aggregation=rate_aggregation,
        )
        groups[f"D3_{scope_tag}_BONDS_TS"] = _append_series_facts(
            facts,
            prefix=f"TS_D3_{scope_tag}_YOUTH_BONDS",
            dossier_id="D3_YOUTH_WORK_AND_HIGH_SCHOOL",
            scope_id=scope_id,
            question_id="P4_YOUTH_WORK_AND_HIGH_SCHOOL",
            metric_id="labor.youth_rais.active_bonds",
            dimension_id="ALL",
            dimension_label="Vínculos formais ativos de 15 a 17 anos",
            series=bonds,
            claim_ceiling="OBSERVED_FACT",
            terminal_state="NO_ROBUST_ASSOCIATION",
            interpretation_guard="WORKPLACE_BONDS_NOT_RESIDENT_YOUTH_NOT_UNIQUE_PEOPLE",
        )
        groups[f"D3_{scope_tag}_DROPOUT_TS"] = _append_series_facts(
            facts,
            prefix=f"TS_D3_{scope_tag}_HS_DROPOUT",
            dossier_id="D3_YOUTH_WORK_AND_HIGH_SCHOOL",
            scope_id=scope_id,
            question_id="P4_YOUTH_WORK_AND_HIGH_SCHOOL",
            metric_id="education.dropout_rate_percent",
            dimension_id="ALL",
            dimension_label="Abandono no ensino médio",
            series=dropout,
            claim_ceiling="OBSERVED_FACT",
            terminal_state="NO_ROBUST_ASSOCIATION",
            interpretation_guard="SCHOOL_LOCATION_SERIES_SEPARATE_FROM_WORKPLACE_SERIES",
        )
        groups[f"D3_{scope_tag}_CHANGES"] = [
            _append_change_fact(
                facts,
                fact_id=f"F_D3_{scope_tag}_YOUTH_BONDS_CHANGE_2019_2025",
                dossier_id="D3_YOUTH_WORK_AND_HIGH_SCHOOL",
                scope_id=scope_id,
                question_id="P4_YOUTH_WORK_AND_HIGH_SCHOOL",
                metric_id="labor.youth_rais.active_bonds",
                dimension_id="ALL",
                dimension_label="Vínculos formais ativos de 15 a 17 anos",
                series=bonds,
                period_start="2019",
                period_end="2025",
                claim_ceiling="OBSERVED_FACT",
                terminal_state="NO_ROBUST_ASSOCIATION",
                interpretation_guard="SIMULTANEITY_DOES_NOT_ESTABLISH_RELATIONSHIP",
            ),
            _append_change_fact(
                facts,
                fact_id=f"F_D3_{scope_tag}_HS_DROPOUT_CHANGE_2019_2025",
                dossier_id="D3_YOUTH_WORK_AND_HIGH_SCHOOL",
                scope_id=scope_id,
                question_id="P4_YOUTH_WORK_AND_HIGH_SCHOOL",
                metric_id="education.dropout_rate_percent",
                dimension_id="ALL",
                dimension_label="Abandono no ensino médio",
                series=dropout,
                period_start="2019",
                period_end="2025",
                claim_ceiling="OBSERVED_FACT",
                terminal_state="NO_ROBUST_ASSOCIATION",
                interpretation_guard="SIMULTANEITY_DOES_NOT_ESTABLISH_RELATIONSHIP",
            ),
        ]
    facts.append(
        _result_fact(
            results,
            fact_id="F_D3_P4_MAIN_TECHNICAL_NEGATIVE",
            dossier_id="D3_YOUTH_WORK_AND_HIGH_SCHOOL",
            result_id="P4_MAIN_L0",
            manager_facing_eligible=False,
            interpretation_guard=(
                "TECHNICAL_ONLY_ADJACENT_TO_NO_ROBUST_ASSOCIATION_AND_LOW_POWER; "
                "NO_STANDALONE_COEFFICIENT"
            ),
        )
    )

    for scope_id, scope_tag, codes, aggregation in (
        (SCOPE_NSR, "NSR", [NSR_CODE], "identity_municipality"),
        (SCOPE_VALE, "VALE", VALE_CODES, "sum_municipalities"),
    ):
        ept = _aggregate_panel_series(
            panel,
            codes=codes,
            metric_id="education.ept_technical_enrollments",
            stage="professional_technical",
            dimension_id="grain=municipality_total|school=ALL|axis=ALL|course=ALL",
            aggregation=aggregation,
        )
        groups[f"D4_{scope_tag}_EPT_TS"] = _append_series_facts(
            facts,
            prefix=f"TS_D4_{scope_tag}_EPT_ENROLL",
            dossier_id="D4_ECONOMIC_TRANSFORMATION_AND_EPT",
            scope_id=scope_id,
            question_id="P5_OCCUPATIONS_AND_EPT",
            metric_id="education.ept_technical_enrollments",
            dimension_id="grain=municipality_total|school=ALL|axis=ALL|course=ALL",
            dimension_label="Matrículas técnicas localizadas",
            series=ept,
            claim_ceiling="OBSERVED_FACT",
            terminal_state="DISTRIBUTIONAL_PATTERN_COMPLETE",
            interpretation_guard="OFFER_AT_SCHOOL_LOCATION_NOT_ACCESS_NOT_DEMAND",
        )
        groups[f"D4_{scope_tag}_EPT_CHANGE"] = [
            _append_change_fact(
                facts,
                fact_id=f"F_D4_{scope_tag}_EPT_CHANGE_2023_2025",
                dossier_id="D4_ECONOMIC_TRANSFORMATION_AND_EPT",
                scope_id=scope_id,
                question_id="P5_OCCUPATIONS_AND_EPT",
                metric_id="education.ept_technical_enrollments",
                dimension_id="grain=municipality_total|school=ALL|axis=ALL|course=ALL",
                dimension_label="Matrículas técnicas localizadas",
                series=ept,
                period_start="2023",
                period_end="2025",
                claim_ceiling="OBSERVED_FACT",
                terminal_state="DISTRIBUTIONAL_PATTERN_COMPLETE",
                interpretation_guard="ZERO_OBSERVED_IS_PRESERVED; NOT_DEMAND_NOT_ACCESS",
            )
        ]
        groups[f"D4_{scope_tag}_TOP_SECTORS"] = _top_change_facts(
            panel,
            facts=facts,
            prefix=f"F_D4_{scope_tag}_TOP_SECTOR",
            scope_id=scope_id,
            codes=codes,
            metric_id="labor.sector_active_bonds",
            top_n=5,
        )
        groups[f"D4_{scope_tag}_TOP_OCCUPATIONS"] = _top_change_facts(
            panel,
            facts=facts,
            prefix=f"F_D4_{scope_tag}_TOP_OCCUPATION",
            scope_id=scope_id,
            codes=codes,
            metric_id="labor.occupation_active_bonds",
            top_n=5,
        )
    for scope_id, scope_tag in ((SCOPE_NSR, "NSR"), (SCOPE_VALE, "VALE")):
        add_comparison(
            f"F_D4_{scope_tag}_LOCAL_CORRESPONDENCE",
            "D4_ECONOMIC_TRANSFORMATION_AND_EPT",
            "P5_OCCUPATIONS_AND_EPT",
            "LOCAL_OFFER_CORRESPONDENCE_SHARE_2025",
            scope_id,
            "NOMENCLATURAL_CBO_TWO_DIGIT_ONLY; NOT_DEMAND_NOT_EMPLOYABILITY_NOT_SUFFICIENCY",
        )
    facts.append(
        _result_fact(
            results,
            fact_id="F_D4_P5_VALE_LOCAL_ACCESSIBLE_BOUND",
            dossier_id="D4_ECONOMIC_TRANSFORMATION_AND_EPT",
            result_id="P5_VALE_LOCAL_TO_ACCESSIBLE_CORRESPONDENCE_BOUND",
            manager_facing_eligible=True,
            interpretation_guard=(
                "NOMENCLATURAL_CBO_TWO_DIGIT_ONLY; INTERVAL_IS_LOCAL_TO_REGION_ACCESSIBLE_BOUND; "
                "NOT_DEMAND_NOT_EMPLOYABILITY_NOT_GRADUATES_NOT_BRIDGE_VALIDATION"
            ),
        )
    )

    d5_measures = (
        "MUNICIPAL_MEDIAN_ADULT_HS_COMPLETION_SHARE_2022",
        "MUNICIPAL_MEDIAN_EJA_ENROLLMENTS_PER_1000_ADULTS_2022",
        "MUNICIPAL_MEDIAN_YOUNG_WORKER_HS_INCOMPLETE_SHARE_2022",
    )
    for scope_id in (SCOPE_NSR, SCOPE_VALE, "RS_497"):
        scope_tag = {
            SCOPE_NSR: "NSR",
            SCOPE_VALE: "VALE",
            "RS_497": "RS",
        }[scope_id]
        for measure in d5_measures:
            add_comparison(
                f"F_D5_{scope_tag}_{measure}",
                "D5_ADULT_SCHOOLING_WORK_AND_EJA",
                "P6_ADULT_SCHOOLING_WORK_AND_EJA",
                measure,
                scope_id,
                "DESCRIPTIVE_DISTRIBUTION_ONLY; RESIDENCE_SCHOOL_AND_WORKPLACE_LENSES_REMAIN_DISTINCT",
            )
    for scope_id, scope_tag, codes, aggregation in (
        (SCOPE_NSR, "NSR", [NSR_CODE], "identity_municipality"),
        (SCOPE_VALE, "VALE", VALE_CODES, "sum_municipalities"),
    ):
        for stage, stage_tag, label in (
            ("eja_fundamental", "FUND", "Matrículas EJA — ensino fundamental"),
            ("eja_high_school", "HS", "Matrículas EJA — ensino médio"),
        ):
            series = _aggregate_panel_series(
                panel,
                codes=codes,
                metric_id="education.eja_enrollments",
                stage=stage,
                dimension_id="ALL",
                aggregation=aggregation,
            )
            groups[f"D5_{scope_tag}_{stage_tag}_TS"] = _append_series_facts(
                facts,
                prefix=f"TS_D5_{scope_tag}_EJA_{stage_tag}",
                dossier_id="D5_ADULT_SCHOOLING_WORK_AND_EJA",
                scope_id=scope_id,
                question_id="P6_ADULT_SCHOOLING_WORK_AND_EJA",
                metric_id="education.eja_enrollments",
                dimension_id="ALL",
                dimension_label=label,
                series=series,
                claim_ceiling="OBSERVED_FACT",
                terminal_state="NO_ROBUST_ASSOCIATION",
                interpretation_guard="SCHOOL_LOCATION_BY_STAGE; NOT_DEMAND_NOT_COVERAGE",
            )
            groups[f"D5_{scope_tag}_{stage_tag}_CHANGE"] = [
                _append_change_fact(
                    facts,
                    fact_id=f"F_D5_{scope_tag}_EJA_{stage_tag}_CHANGE_2014_2025",
                    dossier_id="D5_ADULT_SCHOOLING_WORK_AND_EJA",
                    scope_id=scope_id,
                    question_id="P6_ADULT_SCHOOLING_WORK_AND_EJA",
                    metric_id="education.eja_enrollments",
                    dimension_id="ALL",
                    dimension_label=label,
                    series=series,
                    period_start="2014",
                    period_end="2025",
                    claim_ceiling="OBSERVED_FACT",
                    terminal_state="NO_ROBUST_ASSOCIATION",
                    interpretation_guard="SCHOOL_LOCATION_BY_STAGE; NOT_DEMAND_NOT_COVERAGE",
                )
            ]
    for result_id, fact_id in (
        ("P6_EJA_SPEARMAN", "F_D5_P6_EJA_TECHNICAL_NEGATIVE"),
        ("P6_WORK_SPEARMAN", "F_D5_P6_WORK_TECHNICAL_NEGATIVE"),
    ):
        facts.append(
            _result_fact(
                results,
                fact_id=fact_id,
                dossier_id="D5_ADULT_SCHOOLING_WORK_AND_EJA",
                result_id=result_id,
                manager_facing_eligible=False,
                interpretation_guard=(
                    "TECHNICAL_ONLY_ADJACENT_TO_NO_ROBUST_ASSOCIATION_AND_LOW_POWER; "
                    "DESCRIPTIVE_DISTRIBUTIONS_ONLY"
                ),
            )
        )

    for scope_id, scope_tag, codes, count_aggregation in (
        (SCOPE_NSR, "NSR", [NSR_CODE], "identity_municipality"),
        (SCOPE_VALE, "VALE", VALE_CODES, "sum_municipalities"),
    ):
        for metric_id, stage, metric_tag, label in (
            (
                "education.rural.rural_enrollments",
                "all",
                "RURAL_ENROLL",
                "Matrículas localizadas em escolas rurais",
            ),
            (
                "education.rural.rural_schools",
                "all",
                "RURAL_SCHOOLS",
                "Escolas rurais com oferta localizada",
            ),
            (
                "education.special_aee.special_enrollments",
                "all",
                "SPECIAL_ENROLL",
                "Matrículas da educação especial",
            ),
            (
                "education.special_aee.schools_offering_aee",
                "all",
                "AEE_SCHOOLS",
                "Escolas que oferecem AEE",
            ),
        ):
            series = _aggregate_panel_series(
                panel,
                codes=codes,
                metric_id=metric_id,
                stage=stage,
                dimension_id="ALL",
                aggregation=count_aggregation,
            )
            groups[f"T1_{scope_tag}_{metric_tag}_TS"] = _append_series_facts(
                facts,
                prefix=f"TS_T1_{scope_tag}_{metric_tag}",
                dossier_id="TRANSVERSAL_ACCESS_INCLUSION",
                scope_id=scope_id,
                question_id="P7_RURALITY_INCLUSION_AND_ACCESS",
                metric_id=metric_id,
                dimension_id="ALL",
                dimension_label=label,
                series=series,
                claim_ceiling="OBSERVED_FACT",
                terminal_state="NO_ROBUST_ASSOCIATION",
                interpretation_guard=(
                    "CONTEXT_ONLY; COUNTS_DO_NOT_MEASURE_DISTANCE_CAPACITY_ACCESS_SUFFICIENCY_OR_QUALITY"
                ),
            )
            groups[f"T1_{scope_tag}_{metric_tag}_CHANGE"] = [
                _append_change_fact(
                    facts,
                    fact_id=f"F_T1_{scope_tag}_{metric_tag}_CHANGE_2014_2025",
                    dossier_id="TRANSVERSAL_ACCESS_INCLUSION",
                    scope_id=scope_id,
                    question_id="P7_RURALITY_INCLUSION_AND_ACCESS",
                    metric_id=metric_id,
                    dimension_id="ALL",
                    dimension_label=label,
                    series=series,
                    period_start="2014",
                    period_end="2025",
                    claim_ceiling="OBSERVED_FACT",
                    terminal_state="NO_ROBUST_ASSOCIATION",
                    interpretation_guard=(
                        "CONTEXT_ONLY; CHANGE_DOES_NOT_ESTABLISH_ACCESS_OR_EDUCATIONAL_EFFECT"
                    ),
                )
            ]
        for metric_id, metric_tag, label in (
            (
                "social.vulnerability.registered_people",
                "REGISTERED_PEOPLE",
                "Pessoas registradas no contexto de vulnerabilidade",
            ),
            (
                "social.vulnerability.low_income_registered_people",
                "LOW_INCOME_REGISTERED_PEOPLE",
                "Pessoas de baixa renda registradas",
            ),
            (
                "social.vulnerability.registered_people_age_0_15",
                "REGISTERED_PEOPLE_0_15",
                "Pessoas registradas de 0 a 15 anos",
            ),
        ):
            series = _aggregate_panel_series(
                panel,
                codes=codes,
                metric_id=metric_id,
                stage="registered_vulnerability_context",
                dimension_id="E_VULNERABILIDADE",
                aggregation=count_aggregation,
            )
            groups[f"T1_{scope_tag}_{metric_tag}"] = _append_series_facts(
                facts,
                prefix=f"F_T1_{scope_tag}_{metric_tag}",
                dossier_id="TRANSVERSAL_ACCESS_INCLUSION",
                scope_id=scope_id,
                question_id=None,
                metric_id=metric_id,
                dimension_id="E_VULNERABILIDADE",
                dimension_label=label,
                series=series,
                claim_ceiling="OBSERVED_FACT_CONTEXT_ONLY",
                terminal_state="RELATIONSHIP_NOT_TESTED_IN_AA2",
                interpretation_guard=(
                    "REGISTERED_SOURCE_CONTEXT; NOT_POPULATION_PREVALENCE_NOT_CAUSAL_EXPLANATION"
                ),
            )

    frame = pd.DataFrame(facts, columns=FACT_COLUMNS)
    if frame["fact_id"].duplicated().any():
        duplicates = frame.loc[frame["fact_id"].duplicated(), "fact_id"].tolist()
        raise DossierValidationError(f"Fatos AA4 duplicados: {duplicates}.")
    if frame["fact_id"].isna().any():
        raise DossierValidationError("Fato AA4 sem identidade.")
    frame = frame.sort_values("fact_id", kind="stable").reset_index(drop=True)
    return frame, groups


def _fact_index(facts: pd.DataFrame) -> dict[str, dict[str, Any]]:
    return {
        str(row["fact_id"]): {
            key: (None if pd.isna(value) else value)
            for key, value in row.to_dict().items()
        }
        for _, row in facts.iterrows()
    }


def _mechanism_index(sources: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(item["question_id"]): dict(item)
        for item in sources["library"]["mechanisms"]
    }


def _display_number(value: Any, digits: int = 1) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "indisponível"
    rounded = round(float(value), digits)
    if rounded == 0:
        rounded = 0.0
    text = f"{rounded:,.{digits}f}"
    return text.replace(",", "§").replace(".", ",").replace("§", ".")


def _signed_number(value: Any, digits: int = 1) -> str:
    number = float(value)
    prefix = "+" if number > 0 else ""
    return f"{prefix}{_display_number(number, digits)}"


def _value(fact_by_id: Mapping[str, Mapping[str, Any]], fact_id: str, field: str) -> float:
    if fact_id not in fact_by_id:
        raise DossierValidationError(f"Fato AA4 não resolvido: {fact_id}.")
    value = fact_by_id[fact_id].get(field)
    if value is None:
        raise DossierValidationError(f"Fato AA4 {fact_id} sem {field}.")
    return float(value)


def _theory_block(
    mechanism_by_question: Mapping[str, Mapping[str, Any]], question_id: str
) -> dict[str, Any]:
    mechanism = mechanism_by_question[question_id]
    return {
        "questionId": question_id,
        "recordType": mechanism["record_type"],
        "allowedInterpretation": mechanism["allowed_interpretation"],
        "expectedObservablePattern": mechanism["expected_observable_pattern"],
        "alternativeExplanations": mechanism["alternative_explanations"],
        "falsificationOrBoundary": mechanism["falsification_or_boundary"],
        "transferabilityNotes": mechanism["transferability_notes"],
        "referenceIds": mechanism["primary_official_or_academic_refs"],
        "referenceCoverageState": mechanism["reference_coverage_state"],
        "theoryCanOverrideAa2Terminal": False,
    }


def _technical_evidence(
    *,
    fact_ids: Sequence[str],
    terminal_state: str,
    collapsed: bool = True,
) -> dict[str, Any]:
    return {
        "displayMode": "COLLAPSED_TECHNICAL_NOTE" if collapsed else "VISIBLE_WITH_CAVEAT",
        "factIds": list(fact_ids),
        "terminalState": terminal_state,
        "standaloneCoefficientAllowed": False,
        "adjacencyRule": (
            "Qualquer coeficiente, intervalo ou p-valor deve aparecer no mesmo bloco que "
            "o estado terminal e suas limitações."
        ),
    }


def _scope_metadata(scope_id: str) -> dict[str, Any]:
    if scope_id == SCOPE_NSR:
        return {
            "scopeId": scope_id,
            "scopeLabel": "Nova Santa Rita",
            "municipalityIbgeCode": NSR_CODE,
            "municipalityCount": 1,
            "selectedMunicipalityContainedInRegion": True,
            "comparisonDisclosure": (
                "Nova Santa Rita integra os dez municípios do Vale; município e região são "
                "recortes aninhados, não grupos independentes."
            ),
        }
    if scope_id == SCOPE_VALE:
        return {
            "scopeId": scope_id,
            "scopeLabel": "Vale do Rio dos Sinos — 10 municípios",
            "municipalityIbgeCodes": list(VALE_CODES),
            "municipalityCount": 10,
            "selectedMunicipalityIbgeCode": NSR_CODE,
            "selectedMunicipalityContainedInRegion": True,
            "regionalAggregationDisclosure": (
                "Contagens regionais são somas dos dez municípios e taxas regionais usadas nos "
                "dossiês são medianas municipais quando indicado; a síntese não substitui a "
                "heterogeneidade municipal preservada no AA2."
            ),
        }
    raise DossierValidationError(f"Escopo editorial AA4 inválido: {scope_id}.")


def _build_dossier_1(
    *,
    scope_id: str,
    fact_by_id: Mapping[str, Mapping[str, Any]],
    mechanism_by_question: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    tag = "NSR" if scope_id == SCOPE_NSR else "VALE"
    residual_id = f"F_D1_{tag}_P1_RESIDUAL"
    dropout_id = f"F_D1_{tag}_P3_MUNICIPAL_MEDIAN_DROPOUT_RATE_2025"
    adequacy_id = f"F_D1_{tag}_P3_MUNICIPAL_MEDIAN_TEACHER_ADEQUACY_2025"
    residual = _value(fact_by_id, residual_id, "value_end")
    dropout = _value(fact_by_id, dropout_id, "value_end")
    adequacy = _value(fact_by_id, adequacy_id, "value_end")
    rs_dropout = _value(
        fact_by_id, "F_D1_RS_P3_MUNICIPAL_MEDIAN_DROPOUT_RATE_2025", "value_end"
    )
    rs_adequacy = _value(
        fact_by_id,
        "F_D1_RS_P3_MUNICIPAL_MEDIAN_TEACHER_ADEQUACY_2025",
        "value_end",
    )
    place = "Nova Santa Rita" if scope_id == SCOPE_NSR else "o conjunto do Vale"
    manager_takeaway = (
        f"Em 2025, {place} registrou abandono mediano de {_display_number(dropout)}% "
        f"no ensino médio, ante {_display_number(rs_dropout)}% no RS. A adequação docente "
        f"foi {_display_number(adequacy)}%, acima dos {_display_number(rs_adequacy)}% estaduais; "
        "a análise ajustada, porém, permaneceu inconclusiva e não autoriza atribuir o abandono "
        "à adequação docente nem classificar o território como típico."
    )
    containment_disclosure = (
        "Nova Santa Rita integra o próprio Vale; as referências municipal e regional são aninhadas "
        "e não devem ser interpretadas como grupos independentes."
    )
    return {
        "dossierId": "D1_CONTEXT_AND_TRAJECTORY",
        "title": "Trajetória escolar à luz do contexto territorial",
        "userQuestion": "O desempenho observado permanece diferente quando o contexto entra na comparação?",
        "primaryQuestionId": "P1_CONTEXT_ADJUSTED_TRAJECTORY",
        "boundaryQuestionIds": ["P3_SCHOOL_CONDITIONS_AND_TRAJECTORY"],
        "relationshipState": "CONTEXT_COMPARISON_COMPLETE_WITH_P3_NO_ROBUST_ASSOCIATION",
        "claimCeiling": "CONTEXT_ADJUSTED_COMPARISON_WITH_INTERPRETATION_BOUNDARY",
        "managerTakeaway": manager_takeaway,
        "containmentDisclosure": containment_disclosure,
        "pneToTerritory": {
            "question": "Quais características observadas do contexto ajudam a qualificar o diagnóstico de trajetória?",
            "reading": (
                f"O resíduo mediano observado menos previsto foi {_signed_number(residual, 2)} ponto "
                "percentual. Ele deve ser lido dentro da banda de predição e junto dos comparadores, "
                "não como contribuição isolada do território."
            ),
            "factIds": [
                residual_id,
                "F_D1_RS_P1_RESIDUAL",
                "F_D1_P1_MAIN_CONTEXT_RESULT",
                dropout_id,
                adequacy_id,
                "F_D1_RS_P3_MUNICIPAL_MEDIAN_DROPOUT_RATE_2025",
                "F_D1_RS_P3_MUNICIPAL_MEDIAN_TEACHER_ADEQUACY_2025",
            ],
        },
        "territoryToPne": {
            "question": "Que monitoramento o contexto exige do planejamento educacional?",
            "reading": (
                "A diferença entre resultado bruto e comparação ajustada recomenda monitorar a "
                "trajetória por coorte, escola e perfil discente, preservando composição e mobilidade "
                "como explicações alternativas."
            ),
            "planningImplication": (
                "Vincular metas de permanência a uma rotina de diagnóstico contextual, sem transformar "
                "um único fator de oferta em causa presumida."
            ),
            "agendaId": "AG1_TRAJECTORY_CONTEXT_MONITORING",
        },
        "temporalReading": (
            "A fotografia de 2025 é comparativa; a relação entre adequação docente e abandono foi testada "
            "no painel e terminou sem associação robusta."
        ),
        "theoryAndBoundaries": [
            _theory_block(mechanism_by_question, "P1_CONTEXT_ADJUSTED_TRAJECTORY"),
            _theory_block(mechanism_by_question, "P3_SCHOOL_CONDITIONS_AND_TRAJECTORY"),
        ],
        "technicalEvidence": _technical_evidence(
            fact_ids=["F_D1_P3_MAIN_TECHNICAL_NEGATIVE"],
            terminal_state="NO_ROBUST_ASSOCIATION",
        ),
        "visualIds": [f"V_D1_{tag}_CONTEXT_BENCHMARK"],
        "incrementalValue": (
            "Separa resultado bruto, comparação contextual e teste de relação, evitando que um indicador "
            "de oferta seja usado como explicação automática."
        ),
        "forbiddenConclusion": "Adequação docente causou o nível de abandono observado.",
    }


def _build_dossier_2(
    *, scope_id: str, fact_by_id: Mapping[str, Mapping[str, Any]],
    mechanism_by_question: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    tag = "NSR" if scope_id == SCOPE_NSR else "VALE"
    pop_change_id = f"F_D2_{tag}_POP_CHANGE_2018_2025"
    enroll_change_id = f"F_D2_{tag}_HS_ENROLL_CHANGE_2018_2025"
    pop_component_id = f"F_D2_{tag}_POP_COMPONENT_2018_2025"
    relation_component_id = f"F_D2_{tag}_RELATION_COMPONENT_2018_2025"
    pop_change = _value(fact_by_id, pop_change_id, "absolute_change")
    enroll_change = _value(fact_by_id, enroll_change_id, "absolute_change")
    pop_component = _value(fact_by_id, pop_component_id, "effect_estimate")
    relation_component = _value(fact_by_id, relation_component_id, "effect_estimate")
    place = "Nova Santa Rita" if scope_id == SCOPE_NSR else "o Vale"
    return {
        "dossierId": "D2_DEMOGRAPHY_AND_NETWORK",
        "title": "Demografia, matrículas e organização da rede",
        "userQuestion": "Quanto da mudança de matrículas acompanha a população e quanto fica no componente territorial residual?",
        "primaryQuestionId": "P2_DEMOGRAPHY_ENROLLMENT_DECOMPOSITION",
        "boundaryQuestionIds": [],
        "relationshipState": "EXACT_ACCOUNTING_DECOMPOSITION_COMPLETE",
        "claimCeiling": "ACCOUNTING_DECOMPOSITION_ONLY",
        "cohortDefinition": "População residente de 15 a 17 anos observada anualmente; não é projeção de coorte futura.",
        "managerTakeaway": (
            f"Entre 2018 e 2025, a população residente de 15 a 17 anos em {place} mudou "
            f"{_signed_number(pop_change, 0)}, enquanto as matrículas de ensino médio localizadas "
            f"mudaram {_signed_number(enroll_change, 0)}. Na identidade contábil, o componente "
            f"populacional foi {_signed_number(pop_component, 1)} matrícula e o componente residual "
            f"da relação territorial foi {_signed_number(relation_component, 1)}, fechando exatamente "
            "a mudança total."
        ),
        "pneToTerritory": {
            "question": "A demografia basta para explicar a trajetória das matrículas?",
            "reading": (
                "Não. A decomposição separa aritmeticamente a parcela associada à mudança populacional "
                "da parcela residual da relação entre matrículas localizadas e população residente."
            ),
            "factIds": [
                pop_change_id,
                enroll_change_id,
                pop_component_id,
                relation_component_id,
            ],
        },
        "territoryToPne": {
            "question": "Como a rede deve se preparar se população e matrículas continuarem se movendo de modo distinto?",
            "reading": (
                "A divergência observada torna relevante revisar fluxos residência–escola, distribuição "
                "de oferta e capacidade, sem presumir a origem do componente residual."
            ),
            "planningImplication": (
                "Usar a decomposição como sinal de investigação para organização da rede, e não como "
                "projeção ou estimativa de migração."
            ),
            "agendaId": "AG2_DEMOGRAPHY_NETWORK_COORDINATION",
        },
        "temporalReading": "Série anual comum de 2018 a 2025 e identidade exata M = P × R.",
        "theoryAndBoundaries": [
            _theory_block(
                mechanism_by_question, "P2_DEMOGRAPHY_ENROLLMENT_DECOMPOSITION"
            )
        ],
        "technicalEvidence": _technical_evidence(
            fact_ids=[pop_component_id, relation_component_id],
            terminal_state="ACCOUNTING_DECOMPOSITION_COMPLETE",
            collapsed=False,
        ),
        "visualIds": [f"V_D2_{tag}_ACCOUNTING_WATERFALL"],
        "incrementalValue": (
            "Mostra por que uma queda ou alta de matrículas não pode ser atribuída somente à demografia."
        ),
        "forbiddenConclusion": (
            "O componente residual mede migração, frequência, cobertura ou resposta institucional."
        ),
    }


def _build_dossier_3(
    *, scope_id: str, fact_by_id: Mapping[str, Mapping[str, Any]],
    mechanism_by_question: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    tag = "NSR" if scope_id == SCOPE_NSR else "VALE"
    bonds_id = f"F_D3_{tag}_YOUTH_BONDS_CHANGE_2019_2025"
    dropout_id = f"F_D3_{tag}_HS_DROPOUT_CHANGE_2019_2025"
    bonds_start = _value(fact_by_id, bonds_id, "value_start")
    bonds_end = _value(fact_by_id, bonds_id, "value_end")
    dropout_start = _value(fact_by_id, dropout_id, "value_start")
    dropout_end = _value(fact_by_id, dropout_id, "value_end")
    place = "Nova Santa Rita" if scope_id == SCOPE_NSR else "o Vale"
    return {
        "dossierId": "D3_YOUTH_WORK_AND_HIGH_SCHOOL",
        "title": "Trabalho formal juvenil e permanência no ensino médio",
        "userQuestion": "As mudanças no trabalho formal juvenil acompanharam a trajetória de abandono?",
        "primaryQuestionId": "P4_YOUTH_WORK_AND_HIGH_SCHOOL",
        "boundaryQuestionIds": [],
        "relationshipState": "NO_ROBUST_ASSOCIATION",
        "claimCeiling": "MONITORING_QUESTION_ONLY",
        "managerTakeaway": (
            f"Em {place}, os vínculos formais ativos de 15 a 17 anos passaram de "
            f"{_display_number(bonds_start, 0)} para {_display_number(bonds_end, 0)} entre 2019 e "
            f"2025, enquanto o abandono no ensino médio foi de {_display_number(dropout_start)}% "
            f"para {_display_number(dropout_end)}%. As séries mudaram simultaneamente, mas o teste "
            "pré-registrado não encontrou associação robusta."
        ),
        "pneToTerritory": {
            "question": "O mercado formal ajuda a explicar o abandono observado?",
            "reading": (
                "Os movimentos temporais justificam uma pergunta de monitoramento, não uma explicação: "
                "vínculos por estabelecimento não identificam os mesmos jovens matriculados e não cobrem "
                "informalidade, desemprego ou deslocamento."
            ),
            "factIds": [bonds_id, dropout_id],
        },
        "territoryToPne": {
            "question": "Que coordenação o crescimento do trabalho juvenil pede à educação?",
            "reading": (
                "Planejamento pode acompanhar horários, trajetórias e busca ativa em articulação com "
                "trabalho e assistência, sempre testando se o mesmo padrão reaparece em dados individuais."
            ),
            "planningImplication": "Criar rotina intersetorial de monitoramento, sem meta baseada no coeficiente estimado.",
            "agendaId": "AG3_YOUTH_WORK_EDUCATION_MONITORING",
        },
        "temporalReading": "Comparação de movimentos observados; unidades separadas e nenhuma sobreposição individual presumida.",
        "theoryAndBoundaries": [
            _theory_block(mechanism_by_question, "P4_YOUTH_WORK_AND_HIGH_SCHOOL")
        ],
        "technicalEvidence": _technical_evidence(
            fact_ids=["F_D3_P4_MAIN_TECHNICAL_NEGATIVE"],
            terminal_state="NO_ROBUST_ASSOCIATION",
        ),
        "visualIds": [f"V_D3_{tag}_SEPARATE_UNIT_CHANGE"],
        "incrementalValue": "Transforma simultaneidade em hipótese testável e agenda, sem promover correlação frágil.",
        "forbiddenConclusion": "O aumento do trabalho formal juvenil causou abandono ou permanência.",
    }


def _build_dossier_4(
    *, scope_id: str, fact_by_id: Mapping[str, Mapping[str, Any]],
    groups: Mapping[str, Sequence[str]],
    mechanism_by_question: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    tag = "NSR" if scope_id == SCOPE_NSR else "VALE"
    ept_id = f"F_D4_{tag}_EPT_CHANGE_2023_2025"
    local_id = f"F_D4_{tag}_LOCAL_CORRESPONDENCE"
    sector_ids = list(groups[f"D4_{tag}_TOP_SECTORS"])
    occupation_ids = list(groups[f"D4_{tag}_TOP_OCCUPATIONS"])
    ept_start = _value(fact_by_id, ept_id, "value_start")
    ept_end = _value(fact_by_id, ept_id, "value_end")
    local = _value(fact_by_id, local_id, "value_end")
    top_sector = fact_by_id[sector_ids[0]]
    place = "Nova Santa Rita" if scope_id == SCOPE_NSR else "o Vale"
    if scope_id == SCOPE_NSR:
        correspondence_text = (
            "A lente municipal registrou 0% de correspondência local e zero matrículas técnicas "
            "localizadas em 2023–2025; zero observado não prova ausência de acesso regional nem demanda."
        )
    else:
        lower = _value(
            fact_by_id, "F_D4_P5_VALE_LOCAL_ACCESSIBLE_BOUND", "interval_lower"
        )
        upper = _value(
            fact_by_id, "F_D4_P5_VALE_LOCAL_ACCESSIBLE_BOUND", "interval_upper"
        )
        correspondence_text = (
            f"A correspondência nomenclatural foi {_display_number(local)}% na oferta local e o "
            f"limite local–regional acessível variou de {_display_number(lower)}% a "
            f"{_display_number(upper)}%."
        )
    fact_ids = [ept_id, local_id, *sector_ids, *occupation_ids]
    if scope_id == SCOPE_VALE:
        fact_ids.append("F_D4_P5_VALE_LOCAL_ACCESSIBLE_BOUND")
    return {
        "dossierId": "D4_ECONOMIC_TRANSFORMATION_AND_EPT",
        "title": "Transformação econômica e educação profissional",
        "userQuestion": "O que a recomposição de setores e ocupações torna relevante mapear na oferta técnica?",
        "primaryQuestionId": "P5_OCCUPATIONS_AND_EPT",
        "boundaryQuestionIds": [],
        "relationshipState": "DISTRIBUTIONAL_PATTERN_COMPLETE",
        "claimCeiling": "DESCRIPTIVE_NOMENCLATURE_CORRESPONDENCE_CBO_2_DIGIT_ONLY",
        "managerTakeaway": (
            f"Em {place}, o maior aumento absoluto entre os setores completos de 2019 e 2025 foi "
            f"{top_sector['dimension_label']} ({_signed_number(top_sector['absolute_change'], 0)} "
            f"vínculos). As matrículas técnicas localizadas passaram de {_display_number(ept_start, 0)} "
            f"para {_display_number(ept_end, 0)} entre 2023 e 2025. {correspondence_text}"
        ),
        "pneToTerritory": {
            "question": "Como a estrutura econômica qualifica a leitura da EPT existente?",
            "reading": (
                "Mudanças de setores e ocupações mostram onde o trabalho formal se recompôs. A ponte "
                "CBO–curso indica apenas conexão normativa em dois dígitos, mantendo separadas oferta "
                "escolar, estabelecimento de trabalho, conclusão e inserção."
            ),
            "factIds": fact_ids,
        },
        "territoryToPne": {
            "question": "Que questões econômicas devem entrar na agenda educacional futura?",
            "reading": (
                "Priorizar um mapa regional de cursos, deslocamentos, vagas, conclusões e empregadores "
                "antes de decidir expansão, retração ou desenho curricular."
            ),
            "planningImplication": (
                "Tratar as mudanças observadas como sinal para investigação de acessibilidade e aderência, "
                "não como previsão de demanda ou garantia de emprego."
            ),
            "agendaId": "AG4_REGIONAL_EPT_ACCESS_MAPPING",
        },
        "temporalReading": "Mudanças econômicas 2019–2025 e fotografia de EPT/correspondência em janelas próprias.",
        "theoryAndBoundaries": [
            _theory_block(mechanism_by_question, "P5_OCCUPATIONS_AND_EPT")
        ],
        "technicalEvidence": _technical_evidence(
            fact_ids=(
                ["F_D4_P5_VALE_LOCAL_ACCESSIBLE_BOUND"]
                if scope_id == SCOPE_VALE
                else [local_id]
            ),
            terminal_state="DISTRIBUTIONAL_PATTERN_COMPLETE",
            collapsed=False,
        ),
        "visualIds": [
            f"V_D4_{tag}_ECONOMIC_CHANGE",
            f"V_D4_{tag}_EPT_CORRESPONDENCE",
        ],
        "incrementalValue": "Liga recomposição econômica a uma agenda verificável de oferta e acesso, sem inventar demanda.",
        "forbiddenConclusion": "A correspondência normativa prova demanda, empregabilidade, suficiência ou efeito do curso.",
    }


def _build_dossier_5(
    *, scope_id: str, fact_by_id: Mapping[str, Mapping[str, Any]],
    groups: Mapping[str, Sequence[str]],
    mechanism_by_question: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    tag = "NSR" if scope_id == SCOPE_NSR else "VALE"
    completion_id = f"F_D5_{tag}_MUNICIPAL_MEDIAN_ADULT_HS_COMPLETION_SHARE_2022"
    rate_id = f"F_D5_{tag}_MUNICIPAL_MEDIAN_EJA_ENROLLMENTS_PER_1000_ADULTS_2022"
    work_id = f"F_D5_{tag}_MUNICIPAL_MEDIAN_YOUNG_WORKER_HS_INCOMPLETE_SHARE_2022"
    fund_change_id = f"F_D5_{tag}_EJA_FUND_CHANGE_2014_2025"
    hs_change_id = f"F_D5_{tag}_EJA_HS_CHANGE_2014_2025"
    completion = _value(fact_by_id, completion_id, "value_end")
    eja_rate = _value(fact_by_id, rate_id, "value_end")
    work_incomplete = _value(fact_by_id, work_id, "value_end")
    fund_start = _value(fact_by_id, fund_change_id, "value_start")
    fund_end = _value(fact_by_id, fund_change_id, "value_end")
    hs_start = _value(fact_by_id, hs_change_id, "value_start")
    hs_end = _value(fact_by_id, hs_change_id, "value_end")
    place = "Nova Santa Rita" if scope_id == SCOPE_NSR else "o Vale"
    manager_fact_ids = [completion_id, rate_id, work_id, fund_change_id, hs_change_id]
    return {
        "dossierId": "D5_ADULT_SCHOOLING_WORK_AND_EJA",
        "title": "Escolaridade adulta, trabalho e trajetórias da EJA",
        "userQuestion": "Como escolaridade adulta, inserção formal e oferta da EJA se distribuem no território?",
        "primaryQuestionId": "P6_ADULT_SCHOOLING_WORK_AND_EJA",
        "boundaryQuestionIds": [],
        "relationshipState": "NO_ROBUST_ASSOCIATION_DESCRIPTIVE_DISTRIBUTIONS_ONLY",
        "claimCeiling": "DESCRIPTIVE_DISTRIBUTIONS_ONLY",
        "managerTakeaway": (
            f"Em {place}, {_display_number(completion)}% dos adultos tinham ensino médio completo "
            f"na medida de 2022; havia {_display_number(eja_rate)} matrículas de EJA por mil adultos "
            f"e {_display_number(work_incomplete)}% dos trabalhadores jovens formais estavam sem "
            f"ensino médio completo. Entre 2014 e 2025, a EJA fundamental mudou de "
            f"{_display_number(fund_start, 0)} para {_display_number(fund_end, 0)} matrículas e a EJA "
            f"média de {_display_number(hs_start, 0)} para {_display_number(hs_end, 0)}. As relações "
            "estatísticas testadas não foram robustas."
        ),
        "pneToTerritory": {
            "question": "O perfil de trabalho e escolaridade explica a matrícula da EJA?",
            "reading": (
                "Os três agregados descrevem universos diferentes — residentes, matrículas por escola e "
                "vínculos por estabelecimento. A baixa potência e a instabilidade impedem afirmar efeito."
            ),
            "factIds": manager_fact_ids,
        },
        "territoryToPne": {
            "question": "Que mudança na composição da EJA precisa entrar no planejamento?",
            "reading": (
                "A mudança distinta entre etapas recomenda investigar busca potencial, horários, cuidado, "
                "deslocamento e oferta regional com dados de procura e fluxo que hoje não estão integrados."
            ),
            "planningImplication": "Revisar metas e estratégias de EJA por etapa, turno e território de acesso.",
            "agendaId": "AG5_EJA_BY_STAGE_REVIEW",
        },
        "temporalReading": "Duas séries anuais de 12 pontos, preservadas separadamente por etapa entre 2014 e 2025.",
        "theoryAndBoundaries": [
            _theory_block(
                mechanism_by_question, "P6_ADULT_SCHOOLING_WORK_AND_EJA"
            )
        ],
        "technicalEvidence": _technical_evidence(
            fact_ids=[
                "F_D5_P6_EJA_TECHNICAL_NEGATIVE",
                "F_D5_P6_WORK_TECHNICAL_NEGATIVE",
            ],
            terminal_state="NO_ROBUST_ASSOCIATION",
        ),
        "visualIds": [f"V_D5_{tag}_EJA_STAGE_TRENDS"],
        "incrementalValue": "Separa composição da oferta, escolaridade e trabalho e converte a lacuna em agenda de evidência.",
        "forbiddenConclusion": "Trabalho ou escolaridade causaram a matrícula, o retorno ou a evasão da EJA.",
    }


def _build_transversal_context(
    *, scope_id: str, fact_by_id: Mapping[str, Mapping[str, Any]],
    groups: Mapping[str, Sequence[str]],
    mechanism_by_question: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    tag = "NSR" if scope_id == SCOPE_NSR else "VALE"
    change_ids = [
        f"F_T1_{tag}_RURAL_ENROLL_CHANGE_2014_2025",
        f"F_T1_{tag}_RURAL_SCHOOLS_CHANGE_2014_2025",
        f"F_T1_{tag}_SPECIAL_ENROLL_CHANGE_2014_2025",
        f"F_T1_{tag}_AEE_SCHOOLS_CHANGE_2014_2025",
    ]
    social_ids = [
        *groups[f"T1_{tag}_REGISTERED_PEOPLE"],
        *groups[f"T1_{tag}_LOW_INCOME_REGISTERED_PEOPLE"],
        *groups[f"T1_{tag}_REGISTERED_PEOPLE_0_15"],
    ]
    return {
        "layerId": "TRANSVERSAL_ACCESS_INCLUSION_AND_SOCIAL_CONTEXT",
        "title": "Acesso, inclusão, ruralidade e contexto social registrado",
        "relationshipState": "P7_NO_ROBUST_ASSOCIATION_AND_SOCIAL_RELATIONSHIP_NOT_TESTED",
        "axisDispositions": [
            {
                "axisId": "RURALITY",
                "disposition": "INCLUDED_TRANSVERSAL_P7_CONTEXT_ONLY",
                "reason": "Acrescenta organização territorial sem repetir um dossiê causal.",
            },
            {
                "axisId": "INCLUSION_AEE",
                "disposition": "INCLUDED_TRANSVERSAL_P7_CONTEXT_ONLY",
                "reason": "Acrescenta dimensão de inclusão, preservando contagem como contexto.",
            },
            {
                "axisId": "SOCIAL_REGISTERED_CONTEXT",
                "disposition": "INCLUDED_TRANSVERSAL_NOT_TESTED",
                "reason": "Ajuda a orientar investigação, sem prevalência ou relação educacional testada.",
            },
            {
                "axisId": "FINANCING_CAPACITY",
                "disposition": "BLOCKED_MANAGER_FACING",
                "reason": "P8 terminou em dados insuficientes e não acrescenta evidência gerencial válida.",
            },
        ],
        "managerTakeaway": (
            "As contagens de matrículas rurais, escolas rurais, educação especial e escolas com AEE "
            "ajudam a dimensionar a organização territorial, mas não medem distância, capacidade, "
            "suficiência, qualidade ou efeito educacional. As contagens sociais de 2024-12 descrevem "
            "pessoas registradas na fonte e não prevalência populacional; sua relação com educação não "
            "foi testada no AA2."
        ),
        "factIds": [*change_ids, *social_ids],
        "ruralityAndInclusion": {
            "questionId": "P7_RURALITY_INCLUSION_AND_ACCESS",
            "terminalState": "NO_ROBUST_ASSOCIATION",
            "theoryAndBoundary": _theory_block(
                mechanism_by_question, "P7_RURALITY_INCLUSION_AND_ACCESS"
            ),
        },
        "socialContext": {
            "terminalState": "RELATIONSHIP_NOT_TESTED_IN_AA2",
            "claimCeiling": "OBSERVED_REGISTERED_COUNTS_CONTEXT_ONLY",
            "prevalenceAllowed": False,
            "causalInterpretationAllowed": False,
        },
        "forbiddenConclusions": [
            "Contagem de escola ou serviço mede acesso, capacidade, suficiência ou qualidade.",
            "Mais escolas ou serviços causaram mais matrículas.",
            "Contagens sociais registradas representam prevalência populacional ou efeito educacional.",
        ],
        "visualIds": [f"V_T1_{tag}_ACCESS_CONTEXT"],
    }


def _build_scope_dossiers(
    *, scope_id: str, facts: pd.DataFrame, groups: Mapping[str, Sequence[str]],
    sources: Mapping[str, Any]
) -> dict[str, Any]:
    fact_by_id = _fact_index(facts)
    mechanisms = _mechanism_index(sources)
    dossiers = [
        _build_dossier_1(
            scope_id=scope_id,
            fact_by_id=fact_by_id,
            mechanism_by_question=mechanisms,
        ),
        _build_dossier_2(
            scope_id=scope_id,
            fact_by_id=fact_by_id,
            mechanism_by_question=mechanisms,
        ),
        _build_dossier_3(
            scope_id=scope_id,
            fact_by_id=fact_by_id,
            mechanism_by_question=mechanisms,
        ),
        _build_dossier_4(
            scope_id=scope_id,
            fact_by_id=fact_by_id,
            groups=groups,
            mechanism_by_question=mechanisms,
        ),
        _build_dossier_5(
            scope_id=scope_id,
            fact_by_id=fact_by_id,
            groups=groups,
            mechanism_by_question=mechanisms,
        ),
    ]
    for dossier in dossiers:
        dossier["incrementalValueAssessment"] = {
            "integratesEducationAndTerritory": True,
            "hasBothReadingDirections": (
                "pneToTerritory" in dossier and "territoryToPne" in dossier
            ),
            "hasTemporalOrComparativeLens": bool(dossier.get("temporalReading")),
            "linksEvidenceToPlanningDecision": bool(
                dossier.get("territoryToPne", {}).get("planningImplication")
            ),
            "exposesInterpretationBoundary": bool(
                dossier.get("forbiddenConclusion")
                and dossier.get("theoryAndBoundaries")
            ),
            "valueBeyondSeparateCharts": True,
            "justification": dossier["incrementalValue"],
        }
    return {
        "schemaVersion": "vocacoes-pne-aa4-scope-dossiers-v1",
        "programId": "vocacoes-pne-advanced-analytics-v1",
        "stage": "AA4",
        "generatedAt": GENERATED_AT,
        "scope": _scope_metadata(scope_id),
        "educationNetworkScope": "total_all_dependencies",
        "availabilityPolicy": {
            "observed": "MATERIALIZE_NUMERIC_FACT",
            "observed_zero": "MATERIALIZE_ZERO_WITH_EXPLICIT_STATE",
            "unavailable": "DO_NOT_COERCE_TO_ZERO_OR_NUMERIC_FACT",
            "suppressed": "DO_NOT_COERCE_TO_ZERO_OR_NUMERIC_FACT",
            "not_applicable": "NULL_WITH_EXPLICIT_STATE",
            "row_absent": "NO_FACT_AND_NEVER_ZERO",
        },
        "managerFacingPublicationAllowed": False,
        "readingDirections": {
            "pneToTerritory": "O território ajuda a qualificar o diagnóstico educacional.",
            "territoryToPne": "As transformações territoriais ajudam a definir perguntas e prioridades educacionais.",
        },
        "dossierCount": len(dossiers),
        "dossiers": dossiers,
        "transversalContext": _build_transversal_context(
            scope_id=scope_id,
            fact_by_id=fact_by_id,
            groups=groups,
            mechanism_by_question=mechanisms,
        ),
        "blockedManagerFacingRelations": [
            {
                "questionId": "P8_FINANCING_OFFER_AND_CAPACITY",
                "terminalState": "INSUFFICIENT_DATA",
                "reason": "AA2 não sustentou desenho válido; AA3 bloqueou promoção gerencial.",
            }
        ],
        "downstreamState": "AA5_SELECTION_INPUT_ONLY_NOT_PUBLIC",
    }


def _build_scenarios() -> dict[str, Any]:
    scenarios = [
        {
            "scenarioId": "SCN_DEMOGRAPHIC_PRESSURE_AND_NETWORK",
            "title": "Pressão demográfica e recomposição da rede",
            "scenarioType": "CONDITIONAL_NOT_FORECAST",
            "decisionDomain": "NETWORK_CAPACITY_AND_RESIDENCE_SCHOOL_FLOWS",
            "primaryIndicatorFamilies": ["DEMOGRAPHY_AGE_15_17", "HIGH_SCHOOL_ENROLLMENTS"],
            "exposedPopulation": "População de 15 a 17 anos e estudantes do ensino médio, em universos territoriais distintos.",
            "ifCondition": (
                "Se população de 15 a 17 anos e matrículas continuarem apresentando direções ou "
                "intensidades diferentes nas próximas atualizações..."
            ),
            "thenPlanningQuestion": (
                "...quais fluxos residência–escola, capacidades e arranjos intermunicipais precisam ser "
                "investigados antes de alterar a oferta?"
            ),
            "residualInterpretationGuard": (
                "O componente residual é termo da identidade contábil: não é atribuído a migração, "
                "cobertura, comportamento ou resposta institucional. Fluxos residência–escola são "
                "dados adicionais a investigar, não significado do residual."
            ),
            "evidenceBasisFactIds": [
                "F_D2_NSR_POP_CHANGE_2018_2025",
                "F_D2_NSR_HS_ENROLL_CHANGE_2018_2025",
                "F_D2_VALE_POP_CHANGE_2018_2025",
                "F_D2_VALE_HS_ENROLL_CHANGE_2018_2025",
            ],
            "strengthenIf": [
                "A divergência reaparecer em novas safras com definições estáveis.",
                "Dados de residência–escola confirmarem mudança de fluxos ou cobertura territorial.",
            ],
            "weakenIf": [
                "Revisões populacionais ou de registro eliminarem a divergência.",
                "A relação territorial voltar ao padrão anterior em várias safras.",
            ],
            "relatedDossierIds": ["D2_DEMOGRAPHY_AND_NETWORK"],
            "relatedAgendaIds": ["AG2_DEMOGRAPHY_NETWORK_COORDINATION"],
            "notInterchangeableWith": [
                "SCN_ECONOMIC_RECOMPOSITION_AND_REGIONAL_EPT",
                "SCN_ADULT_SCHOOLING_AND_EJA_COORDINATION",
            ],
        },
        {
            "scenarioId": "SCN_ECONOMIC_RECOMPOSITION_AND_REGIONAL_EPT",
            "title": "Recomposição econômica e acesso regional à EPT",
            "scenarioType": "CONDITIONAL_NOT_FORECAST",
            "decisionDomain": "REGIONAL_EPT_ACCESS_AND_OFFER_MAPPING",
            "primaryIndicatorFamilies": ["FORMAL_SECTORS_OCCUPATIONS", "EPT_OFFER_AND_ACCESS"],
            "exposedPopulation": "Estudantes e trabalhadores em universos não pareados de formação e emprego formal.",
            "ifCondition": (
                "Se a recomposição dos vínculos formais permanecer concentrada em novos setores e "
                "ocupações enquanto a oferta técnica local ou acessível não for bem mapeada..."
            ),
            "thenPlanningQuestion": (
                "...que evidências de vagas, conclusão, deslocamento e inserção devem anteceder decisões "
                "sobre itinerários e cursos?"
            ),
            "evidenceBasisFactIds": [
                "F_D4_NSR_EPT_CHANGE_2023_2025",
                "F_D4_VALE_EPT_CHANGE_2023_2025",
                "F_D4_NSR_LOCAL_CORRESPONDENCE",
                "F_D4_P5_VALE_LOCAL_ACCESSIBLE_BOUND",
            ],
            "strengthenIf": [
                "As mesmas famílias setoriais e ocupacionais crescerem em novas safras.",
                "Dados de vagas, concluintes e fluxos confirmarem acesso e conexão formativa.",
            ],
            "weakenIf": [
                "O crescimento observado se mostrar temporário ou concentrado em poucos estabelecimentos.",
                "A correspondência normativa não se confirmar em dados de curso e egresso mais granulares.",
            ],
            "relatedDossierIds": ["D4_ECONOMIC_TRANSFORMATION_AND_EPT"],
            "relatedAgendaIds": ["AG4_REGIONAL_EPT_ACCESS_MAPPING"],
            "notInterchangeableWith": [
                "SCN_DEMOGRAPHIC_PRESSURE_AND_NETWORK",
                "SCN_ADULT_SCHOOLING_AND_EJA_COORDINATION",
            ],
        },
        {
            "scenarioId": "SCN_ADULT_SCHOOLING_AND_EJA_COORDINATION",
            "title": "Escolaridade adulta e coordenação da EJA",
            "scenarioType": "CONDITIONAL_NOT_FORECAST",
            "decisionDomain": "EJA_STAGE_TURN_AND_TERRITORIAL_COORDINATION",
            "primaryIndicatorFamilies": ["ADULT_SCHOOLING", "EJA_BY_STAGE", "REGISTERED_SOCIAL_CONTEXT"],
            "exposedPopulation": "Jovens e adultos sem conclusão da educação básica, sem presumir demanda a partir de matrícula.",
            "ifCondition": (
                "Se as matrículas de EJA continuarem mudando de forma distinta por etapa enquanto "
                "persistirem grupos adultos e trabalhadores jovens sem ensino médio completo..."
            ),
            "thenPlanningQuestion": (
                "...como redes e municípios devem ajustar busca ativa, turnos, deslocamento e oferta sem "
                "confundir matrícula observada com demanda?"
            ),
            "evidenceBasisFactIds": [
                "F_D5_NSR_EJA_FUND_CHANGE_2014_2025",
                "F_D5_NSR_EJA_HS_CHANGE_2014_2025",
                "F_D5_VALE_EJA_FUND_CHANGE_2014_2025",
                "F_D5_VALE_EJA_HS_CHANGE_2014_2025",
                "F_T1_NSR_LOW_INCOME_REGISTERED_PEOPLE_2024-12",
                "F_T1_VALE_LOW_INCOME_REGISTERED_PEOPLE_2024-12",
            ],
            "relationshipBoundary": (
                "As contagens sociais são contexto registrado, não prevalência; a relação com EJA não "
                "foi testada no AA2 e não pode ser usada como efeito ou projeção."
            ),
            "strengthenIf": [
                "Busca ativa e dados de procura confirmarem barreiras por etapa e turno.",
                "O padrão persistir após separar residência, escola e estabelecimento de trabalho.",
            ],
            "weakenIf": [
                "Mudanças de registro ou reorganização da oferta explicarem a série.",
                "Dados individuais mostrarem procura e acesso em direção diferente da hipótese."
            ],
            "relatedDossierIds": ["D5_ADULT_SCHOOLING_WORK_AND_EJA"],
            "relatedAgendaIds": ["AG5_EJA_BY_STAGE_REVIEW"],
            "notInterchangeableWith": [
                "SCN_DEMOGRAPHIC_PRESSURE_AND_NETWORK",
                "SCN_ECONOMIC_RECOMPOSITION_AND_REGIONAL_EPT",
            ],
        },
    ]
    return {
        "schemaVersion": "vocacoes-pne-aa4-conditional-scenarios-v1",
        "programId": "vocacoes-pne-advanced-analytics-v1",
        "stage": "AA4",
        "scenarioCount": len(scenarios),
        "aa4MinimumScenarioCount": 3,
        "aa5MayReduceBelowAa4Minimum": False,
        "futureNumericProjectionAllowed": False,
        "scenariosAreMutuallyNonInterchangeable": True,
        "nonInterchangeabilityReason": (
            "Cada cenário possui condição, mecanismo, evidência e decisão distinta: rede escolar, "
            "oferta técnica regional ou EJA."
        ),
        "scenarios": scenarios,
    }


def _build_agendas() -> dict[str, Any]:
    common = {
        "status": "PLANNING_AGENDA_NOT_AUTOMATIC_PRIORITY",
        "reviewRule": "Reavaliar quando o gatilho ocorrer ou na cadência definida.",
    }
    agendas = [
        {
            **common,
            "agendaId": "AG1_TRAJECTORY_CONTEXT_MONITORING",
            "title": "Monitorar trajetória com contexto e composição",
            "observedCondition": "Abandono de 2025 acima da referência estadual, com comparação ajustada inconclusiva.",
            "exposedPopulation": "Estudantes do ensino médio e coortes em transição para a etapa.",
            "educationStage": "Ensino médio",
            "territoryExposed": [SCOPE_NSR, SCOPE_VALE],
            "concreteAction": "Instituir leitura semestral por escola/coorte com composição e mobilidade documentadas.",
            "responsibilityLevel": "municipal",
            "leadResponsibility": "Secretaria Municipal de Educação — planejamento e ensino médio",
            "contributors": ["Escolas", "Coordenadoria regional", "Assistência social"],
            "indicators": ["abandono", "adequação docente", "composição discente", "mobilidade escolar"],
            "baselineFactIds": [
                "F_D1_NSR_P1_RESIDUAL",
                "F_D1_NSR_P3_MUNICIPAL_MEDIAN_DROPOUT_RATE_2025",
                "F_D1_NSR_P3_MUNICIPAL_MEDIAN_TEACHER_ADEQUACY_2025",
                "F_D1_VALE_P1_RESIDUAL",
            ],
            "triggerDefinition": "Mudança persistente de abandono ou saída da banda contextual em nova estimação válida.",
            "cadence": "Semestral para gestão; anual para revisão analítica.",
            "strengthenIf": "Padrão reaparecer por escola/coorte e sobreviver a ajuste de composição.",
            "weakenIf": "Mudança decorrer de registro, composição ou mobilidade não controlada.",
        },
        {
            **common,
            "agendaId": "AG2_DEMOGRAPHY_NETWORK_COORDINATION",
            "title": "Coordenar demografia, matrículas e capacidade da rede",
            "observedCondition": "População de 15–17 anos e matrículas variaram com intensidades distintas entre 2018 e 2025.",
            "exposedPopulation": "População residente de 15 a 17 anos e estudantes do ensino médio.",
            "educationStage": "Ensino médio",
            "territoryExposed": [SCOPE_NSR, SCOPE_VALE],
            "concreteAction": "Cruzar residência–escola, capacidade, vagas e transporte antes da programação anual da rede.",
            "responsibilityLevel": "regional/shared",
            "leadResponsibility": "Secretaria Municipal de Educação — planejamento de rede",
            "contributors": ["Planejamento municipal", "Estado", "Municípios do Vale"],
            "indicators": ["população 15–17", "matrículas de ensino médio", "componentes da decomposição", "fluxos residência–escola"],
            "baselineFactIds": [
                "F_D2_NSR_POP_CHANGE_2018_2025",
                "F_D2_NSR_HS_ENROLL_CHANGE_2018_2025",
                "F_D2_NSR_POP_COMPONENT_2018_2025",
                "F_D2_NSR_RELATION_COMPONENT_2018_2025",
                "F_D2_VALE_POP_CHANGE_2018_2025",
                "F_D2_VALE_HS_ENROLL_CHANGE_2018_2025",
            ],
            "triggerDefinition": "Divergência por duas atualizações entre população e matrícula ou mudança material de capacidade.",
            "cadence": "Anual, antes da programação de vagas e transporte.",
            "strengthenIf": "Fluxos residência–escola e capacidade confirmarem a hipótese operacional.",
            "weakenIf": "Rebase populacional ou correção de registro explicar a divergência.",
        },
        {
            **common,
            "agendaId": "AG3_YOUTH_WORK_EDUCATION_MONITORING",
            "title": "Monitorar trabalho juvenil e permanência sem inferência automática",
            "observedCondition": "Vínculos juvenis e abandono mudaram simultaneamente, sem associação robusta no teste pré-registrado.",
            "exposedPopulation": "Jovens de 15 a 17 anos, matriculados ou vinculados formalmente em universos distintos.",
            "educationStage": "Ensino médio",
            "territoryExposed": [SCOPE_NSR, SCOPE_VALE],
            "concreteAction": "Integrar busca ativa, turno e vínculo individual somente mediante base legal e pareamento validado.",
            "responsibilityLevel": "municipal",
            "leadResponsibility": "Secretaria Municipal de Educação — permanência e busca ativa",
            "contributors": ["Trabalho e renda", "Assistência social", "Escolas", "Conselho tutelar"],
            "indicators": ["abandono do ensino médio", "vínculos formais 15–17", "turno", "busca ativa"],
            "baselineFactIds": [
                "F_D3_NSR_YOUTH_BONDS_CHANGE_2019_2025",
                "F_D3_NSR_HS_DROPOUT_CHANGE_2019_2025",
                "F_D3_VALE_YOUTH_BONDS_CHANGE_2019_2025",
                "F_D3_VALE_HS_DROPOUT_CHANGE_2019_2025",
            ],
            "triggerDefinition": "Mudança simultânea persistente acompanhada por evidência individual ou escolar adicional.",
            "cadence": "Trimestral operacional; anual analítica.",
            "strengthenIf": "Dados individuais e temporalidade confirmarem exposição antes do desfecho.",
            "weakenIf": "Informalidade, deslocamento ou composição explicarem o padrão agregado.",
        },
        {
            **common,
            "agendaId": "AG4_REGIONAL_EPT_ACCESS_MAPPING",
            "title": "Mapear acesso regional, oferta e trajetórias da EPT",
            "observedCondition": "Setores e ocupações se recompuseram enquanto a oferta técnica local e a conexão normativa mostram cobertura parcial.",
            "exposedPopulation": "Jovens e adultos em trajetórias de formação técnica; estudantes e trabalhadores não são presumidos como as mesmas pessoas.",
            "educationStage": "Educação profissional e tecnológica",
            "territoryExposed": [SCOPE_NSR, SCOPE_VALE],
            "concreteAction": "Construir mapa regional de cursos, vagas, conclusão, deslocamento e egressos antes de pactuar expansão.",
            "responsibilityLevel": "regional/shared",
            "leadResponsibility": "Secretaria Municipal de Educação — articulação de EPT",
            "contributors": ["Municípios do Vale", "Estado", "Institutos e escolas técnicas", "Trabalho e desenvolvimento"],
            "indicators": ["matrículas", "vagas", "conclusões", "deslocamento", "setores e ocupações", "egressos"],
            "baselineFactIds": [
                "F_D4_NSR_EPT_CHANGE_2023_2025",
                "F_D4_NSR_LOCAL_CORRESPONDENCE",
                "F_D4_P5_VALE_LOCAL_ACCESSIBLE_BOUND",
                "F_D4_VALE_EPT_CHANGE_2023_2025",
            ],
            "triggerDefinition": "Persistência da recomposição econômica e evidência de barreira de acesso ou lacuna validada de oferta.",
            "cadence": "Anual, antes da pactuação regional de cursos.",
            "strengthenIf": "Vagas, conclusão, deslocamento e egressos confirmarem conexão além da nomenclatura.",
            "weakenIf": "Mudança for transitória ou conexão CBO–curso não se sustentar em dados granulares.",
        },
        {
            **common,
            "agendaId": "AG5_EJA_BY_STAGE_REVIEW",
            "title": "Revisar a EJA por etapa, turno e território de acesso",
            "observedCondition": "Matrículas de EJA fundamental e média seguiram trajetórias distintas, sem relação robusta com escolaridade ou trabalho.",
            "exposedPopulation": "Jovens e adultos sem conclusão da educação básica, com atenção a barreiras de turno e deslocamento.",
            "educationStage": "EJA fundamental e EJA ensino médio",
            "territoryExposed": [SCOPE_NSR, SCOPE_VALE],
            "concreteAction": "Registrar procura, turno, etapa e barreira de acesso e revisar a oferta semestralmente.",
            "responsibilityLevel": "regional/shared",
            "leadResponsibility": "Secretaria Municipal de Educação — EJA",
            "contributors": ["Escolas", "Assistência social", "Trabalho e renda", "Municípios do Vale"],
            "indicators": ["matrículas EJA fundamental", "matrículas EJA médio", "procura", "turnos", "escolaridade adulta"],
            "baselineFactIds": [
                "F_D5_NSR_EJA_FUND_CHANGE_2014_2025",
                "F_D5_NSR_EJA_HS_CHANGE_2014_2025",
                "F_D5_NSR_MUNICIPAL_MEDIAN_ADULT_HS_COMPLETION_SHARE_2022",
                "F_D5_VALE_EJA_FUND_CHANGE_2014_2025",
                "F_D5_VALE_EJA_HS_CHANGE_2014_2025",
            ],
            "triggerDefinition": "Mudança persistente por etapa ou procura registrada não atendida por turno/território.",
            "cadence": "Semestral operacional; anual para revisão do PME.",
            "strengthenIf": "Busca ativa e procura confirmarem barreiras e perfil por etapa.",
            "weakenIf": "Reorganização de registro ou deslocamento explicar a série de matrículas.",
        },
    ]
    agenda_dossier_map = {
        "AG1_TRAJECTORY_CONTEXT_MONITORING": "D1_CONTEXT_AND_TRAJECTORY",
        "AG2_DEMOGRAPHY_NETWORK_COORDINATION": "D2_DEMOGRAPHY_AND_NETWORK",
        "AG3_YOUTH_WORK_EDUCATION_MONITORING": "D3_YOUTH_WORK_AND_HIGH_SCHOOL",
        "AG4_REGIONAL_EPT_ACCESS_MAPPING": "D4_ECONOMIC_TRANSFORMATION_AND_EPT",
        "AG5_EJA_BY_STAGE_REVIEW": "D5_ADULT_SCHOOLING_WORK_AND_EJA",
    }
    scope_baselines = {
        "AG1_TRAJECTORY_CONTEXT_MONITORING": {
            SCOPE_NSR: [
                "F_D1_NSR_P1_RESIDUAL",
                "F_D1_NSR_P3_MUNICIPAL_MEDIAN_DROPOUT_RATE_2025",
                "F_D1_NSR_P3_MUNICIPAL_MEDIAN_TEACHER_ADEQUACY_2025",
            ],
            SCOPE_VALE: [
                "F_D1_VALE_P1_RESIDUAL",
                "F_D1_VALE_P3_MUNICIPAL_MEDIAN_DROPOUT_RATE_2025",
                "F_D1_VALE_P3_MUNICIPAL_MEDIAN_TEACHER_ADEQUACY_2025",
            ],
        },
        "AG2_DEMOGRAPHY_NETWORK_COORDINATION": {
            SCOPE_NSR: [
                "F_D2_NSR_POP_CHANGE_2018_2025",
                "F_D2_NSR_HS_ENROLL_CHANGE_2018_2025",
                "F_D2_NSR_POP_COMPONENT_2018_2025",
                "F_D2_NSR_RELATION_COMPONENT_2018_2025",
            ],
            SCOPE_VALE: [
                "F_D2_VALE_POP_CHANGE_2018_2025",
                "F_D2_VALE_HS_ENROLL_CHANGE_2018_2025",
                "F_D2_VALE_POP_COMPONENT_2018_2025",
                "F_D2_VALE_RELATION_COMPONENT_2018_2025",
            ],
        },
        "AG3_YOUTH_WORK_EDUCATION_MONITORING": {
            SCOPE_NSR: [
                "F_D3_NSR_YOUTH_BONDS_CHANGE_2019_2025",
                "F_D3_NSR_HS_DROPOUT_CHANGE_2019_2025",
            ],
            SCOPE_VALE: [
                "F_D3_VALE_YOUTH_BONDS_CHANGE_2019_2025",
                "F_D3_VALE_HS_DROPOUT_CHANGE_2019_2025",
            ],
        },
        "AG4_REGIONAL_EPT_ACCESS_MAPPING": {
            SCOPE_NSR: [
                "F_D4_NSR_EPT_CHANGE_2023_2025",
                "F_D4_NSR_LOCAL_CORRESPONDENCE",
            ],
            SCOPE_VALE: [
                "F_D4_VALE_EPT_CHANGE_2023_2025",
                "F_D4_VALE_LOCAL_CORRESPONDENCE",
                "F_D4_P5_VALE_LOCAL_ACCESSIBLE_BOUND",
            ],
        },
        "AG5_EJA_BY_STAGE_REVIEW": {
            SCOPE_NSR: [
                "F_D5_NSR_EJA_FUND_CHANGE_2014_2025",
                "F_D5_NSR_EJA_HS_CHANGE_2014_2025",
                "F_D5_NSR_MUNICIPAL_MEDIAN_ADULT_HS_COMPLETION_SHARE_2022",
            ],
            SCOPE_VALE: [
                "F_D5_VALE_EJA_FUND_CHANGE_2014_2025",
                "F_D5_VALE_EJA_HS_CHANGE_2014_2025",
                "F_D5_VALE_MUNICIPAL_MEDIAN_ADULT_HS_COMPLETION_SHARE_2022",
            ],
        },
    }
    for agenda in agendas:
        agenda_id = agenda["agendaId"]
        dossier_id = agenda_dossier_map[agenda_id]
        agenda["sharedAcrossScopes"] = True
        agenda["dossierMappings"] = [
            {"scopeId": SCOPE_NSR, "dossierId": dossier_id},
            {"scopeId": SCOPE_VALE, "dossierId": dossier_id},
        ]
        agenda["scopeVariants"] = [
            {
                "scopeId": SCOPE_NSR,
                "territoryRole": "MUNICIPAL_FOCUS_CONTAINED_IN_REGION",
                "baselineFactIds": scope_baselines[agenda_id][SCOPE_NSR],
                "triggerDefinition": (
                    f"Nova Santa Rita: {agenda['triggerDefinition']}"
                ),
            },
            {
                "scopeId": SCOPE_VALE,
                "territoryRole": "REGIONAL_AGGREGATE_10_MUNICIPALITIES",
                "baselineFactIds": scope_baselines[agenda_id][SCOPE_VALE],
                "triggerDefinition": (
                    f"Vale dos dez municípios: {agenda['triggerDefinition']}"
                ),
            },
        ]
    return {
        "schemaVersion": "vocacoes-pne-aa4-planning-agendas-v1",
        "programId": "vocacoes-pne-advanced-analytics-v1",
        "stage": "AA4",
        "agendaCount": len(agendas),
        "sharingPolicy": {
            "sharedAcrossScopes": True,
            "scopeVariantRequired": True,
            "dossierToAgendaMappingRequired": True,
            "antiComparisonRule": (
                "Cada baseline e gatilho deve ser lido dentro de sua variante; Nova Santa Rita "
                "compõe o Vale e as variantes não são grupos independentes."
            ),
        },
        "agendas": agendas,
    }


def _visual_contract(
    *, visual_id: str, dossier_id: str, scope_id: str, family: str,
    form: str, question: str, takeaway: str, fact_ids: Sequence[str],
    data_sufficiency: str, fallback: str, units: Sequence[str],
    non_color: str, additive_identity: bool = False,
    terminal_state: str | None = None,
    forbidden_conclusion: str | None = None,
) -> dict[str, Any]:
    return {
        "visualId": visual_id,
        "dossierId": dossier_id,
        "scopeId": scope_id,
        "family": family,
        "recommendedForm": form,
        "question": question,
        "takeaway": takeaway,
        "factIds": list(fact_ids),
        "dataSufficiency": data_sufficiency,
        "fallback": fallback,
        "units": list(units),
        "palette": {
            "rootColors": ["education_blue", "territory_orange"],
            "neutralsAllowed": True,
            "rootColorCount": 2,
        },
        "nonColorDistinction": non_color,
        "zeroBaselineRequired": family in {"COMPARISON", "DECOMPOSITION_AND_PROGRESSION"},
        "additiveIdentityVerified": additive_identity,
        "terminalState": terminal_state,
        "forbiddenConclusion": forbidden_conclusion,
        "managerFacing": True,
    }


def _build_visual_map(groups: Mapping[str, Sequence[str]]) -> dict[str, Any]:
    visuals: list[dict[str, Any]] = []
    for scope_id, tag, label in (
        (SCOPE_NSR, "NSR", "Nova Santa Rita"),
        (SCOPE_VALE, "VALE", "Vale do Rio dos Sinos"),
    ):
        visuals.extend(
            [
                _visual_contract(
                    visual_id=f"V_D1_{tag}_CONTEXT_BENCHMARK",
                    dossier_id="D1_CONTEXT_AND_TRAJECTORY",
                    scope_id=scope_id,
                    family="UNCERTAINTY_AND_BENCHMARK",
                    form="DOT_AND_PREDICTION_INTERVAL_WITH_BENCHMARKS",
                    question=f"O resultado de {label} se distingue após considerar o contexto?",
                    takeaway="A comparação ajustada é inconclusiva; o gráfico deve tornar a incerteza dominante.",
                    fact_ids=[
                        f"F_D1_{tag}_P1_RESIDUAL",
                        "F_D1_RS_P1_RESIDUAL",
                        "F_D1_P1_MAIN_CONTEXT_RESULT",
                    ],
                    data_sufficiency="Intervalo e três referências disponíveis; sem alegação de tipicidade.",
                    fallback="Cartão textual com ponto, banda e aviso de inconclusão.",
                    units=["pontos percentuais: observado menos previsto"],
                    non_color="Forma do marcador, linha de zero e rótulos diretos.",
                    terminal_state="CONTEXT_COMPARISON_COMPLETE_WITH_P3_NO_ROBUST_ASSOCIATION",
                    forbidden_conclusion=(
                        "A banda é meta, previsão municipal, padrão esperado de desempenho ou prova "
                        "de associação entre adequação docente e abandono."
                    ),
                ),
                _visual_contract(
                    visual_id=f"V_D2_{tag}_ACCOUNTING_WATERFALL",
                    dossier_id="D2_DEMOGRAPHY_AND_NETWORK",
                    scope_id=scope_id,
                    family="DECOMPOSITION_AND_PROGRESSION",
                    form="ADDITIVE_WATERFALL",
                    question=f"Como os dois componentes fecham a mudança de matrículas em {label}?",
                    takeaway="O componente populacional e o residual territorial somam exatamente a mudança observada.",
                    fact_ids=[
                        f"F_D2_{tag}_POP_COMPONENT_2018_2025",
                        f"F_D2_{tag}_RELATION_COMPONENT_2018_2025",
                        f"F_D2_{tag}_HS_ENROLL_CHANGE_2018_2025",
                    ],
                    data_sufficiency="Identidade contábil exata validada no AA2.",
                    fallback="Tabela aditiva de três linhas com soma explícita.",
                    units=["matrículas"],
                    non_color="Sinais +/−, hachura distinta e rótulos de valor.",
                    additive_identity=True,
                ),
                _visual_contract(
                    visual_id=f"V_D3_{tag}_SEPARATE_UNIT_CHANGE",
                    dossier_id="D3_YOUTH_WORK_AND_HIGH_SCHOOL",
                    scope_id=scope_id,
                    family="COMPARISON",
                    form="SEPARATE_UNIT_START_END_BARS",
                    question=f"Como trabalho formal juvenil e abandono mudaram em {label}, sem misturar unidades?",
                    takeaway="Os dois movimentos são simultâneos, mas a associação testada não foi robusta.",
                    fact_ids=[
                        f"F_D3_{tag}_YOUTH_BONDS_CHANGE_2019_2025",
                        f"F_D3_{tag}_HS_DROPOUT_CHANGE_2019_2025",
                    ],
                    data_sufficiency="Extremos comuns disponíveis; série de vínculos tem sete pontos, abaixo do mínimo para linha principal.",
                    fallback="Dois cartões início–fim, um por unidade.",
                    units=["vínculos formais ativos", "percentual de abandono"],
                    non_color="Painéis separados, títulos de unidade e padrões distintos; sem eixo duplo.",
                ),
                _visual_contract(
                    visual_id=f"V_D4_{tag}_ECONOMIC_CHANGE",
                    dossier_id="D4_ECONOMIC_TRANSFORMATION_AND_EPT",
                    scope_id=scope_id,
                    family="DISTRIBUTION",
                    form="RANKED_HORIZONTAL_CHANGE_BARS_SMALL_MULTIPLES",
                    question=f"Quais setores e ocupações tiveram maiores aumentos absolutos em {label}?",
                    takeaway="A recomposição é descritiva e serve para selecionar perguntas formativas, não para prever demanda.",
                    fact_ids=[
                        *groups[f"D4_{tag}_TOP_SECTORS"],
                        *groups[f"D4_{tag}_TOP_OCCUPATIONS"],
                    ],
                    data_sufficiency="Cinco setores e cinco ocupações com cobertura completa em 2019 e 2025.",
                    fallback="Tabela ranqueada com valores inicial, final e mudança absoluta.",
                    units=["vínculos formais ativos por estabelecimento"],
                    non_color="Painéis separados, rótulos diretos e ícones setor/ocupação.",
                ),
                _visual_contract(
                    visual_id=f"V_D4_{tag}_EPT_CORRESPONDENCE",
                    dossier_id="D4_ECONOMIC_TRANSFORMATION_AND_EPT",
                    scope_id=scope_id,
                    family="COMPARISON",
                    form="EPT_STATUS_AND_NOMENCLATURE_RANGE",
                    question=f"O que a oferta técnica localizada e a correspondência normativa mostram em {label}?",
                    takeaway="Oferta localizada e limite de correspondência são lentes diferentes; nenhuma mede demanda ou empregabilidade.",
                    fact_ids=(
                        [f"F_D4_{tag}_EPT_CHANGE_2023_2025", f"F_D4_{tag}_LOCAL_CORRESPONDENCE"]
                        + (["F_D4_P5_VALE_LOCAL_ACCESSIBLE_BOUND"] if tag == "VALE" else [])
                    ),
                    data_sufficiency="Três anos de EPT: insuficiente para tendência; usar estado início–fim e faixa descritiva.",
                    fallback="Cartões de zero/valor observado e nota metodológica da ponte CBO2.",
                    units=["matrículas técnicas localizadas", "percentual de vínculos em subgrupos conectados"],
                    non_color="Componentes em blocos separados e faixa com extremos rotulados.",
                ),
                _visual_contract(
                    visual_id=f"V_D5_{tag}_EJA_STAGE_TRENDS",
                    dossier_id="D5_ADULT_SCHOOLING_WORK_AND_EJA",
                    scope_id=scope_id,
                    family="TREND",
                    form="SMALL_MULTIPLE_LINES_BY_STAGE",
                    question=f"Como a composição da EJA mudou por etapa em {label}?",
                    takeaway="Fundamental e ensino médio seguiram trajetórias diferentes; matrícula não equivale a demanda.",
                    fact_ids=[*groups[f"D5_{tag}_FUND_TS"], *groups[f"D5_{tag}_HS_TS"]],
                    data_sufficiency="Doze pontos anuais completos por etapa, acima do mínimo de oito.",
                    fallback="Tabela anual por etapa com estados de zero preservados.",
                    units=["matrículas por localização da escola"],
                    non_color="Painéis/tipos de linha distintos e rótulos diretos.",
                ),
                _visual_contract(
                    visual_id=f"V_T1_{tag}_ACCESS_CONTEXT",
                    dossier_id="TRANSVERSAL_ACCESS_INCLUSION",
                    scope_id=scope_id,
                    family="COMPARISON",
                    form="START_END_CONTEXT_CARDS",
                    question=f"Como contagens de ruralidade e inclusão mudaram em {label}?",
                    takeaway="As contagens dimensionam oferta registrada, mas não medem acesso, suficiência ou efeito.",
                    fact_ids=[
                        f"F_T1_{tag}_RURAL_ENROLL_CHANGE_2014_2025",
                        f"F_T1_{tag}_RURAL_SCHOOLS_CHANGE_2014_2025",
                        f"F_T1_{tag}_SPECIAL_ENROLL_CHANGE_2014_2025",
                        f"F_T1_{tag}_AEE_SCHOOLS_CHANGE_2014_2025",
                    ],
                    data_sufficiency="Extremos observados de quatro contagens; relações não robustas ou não testadas.",
                    fallback="Lista de fatos com período, lente e limite interpretativo.",
                    units=["matrículas", "escolas"],
                    non_color="Cartões separados por indicador, pictogramas e rótulos de unidade.",
                ),
            ]
        )
    regional_aggregation_disclosures = {
        "D1_CONTEXT_AND_TRAJECTORY": (
            "O ponto do Vale é mediana municipal do residual; não é taxa regional ponderada "
            "pela população nem grupo independente de Nova Santa Rita."
        ),
        "D2_DEMOGRAPHY_AND_NETWORK": (
            "População e matrículas do Vale são somas dos dez municípios; os componentes fecham "
            "a mudança dessas somas."
        ),
        "D3_YOUTH_WORK_AND_HIGH_SCHOOL": (
            "Vínculos do Vale são soma municipal; abandono é mediana das taxas municipais e "
            "não é taxa regional ponderada pela população."
        ),
        "D4_ECONOMIC_TRANSFORMATION_AND_EPT": (
            "Vínculos, mudanças econômicas e matrículas EPT do Vale são somas municipais; a "
            "correspondência segue a distribuição regional declarada no AA2."
        ),
        "D5_ADULT_SCHOOLING_WORK_AND_EJA": (
            "As linhas de EJA do Vale são somas de matrículas localizadas nos dez municípios."
        ),
        "TRANSVERSAL_ACCESS_INCLUSION": (
            "As contagens transversais do Vale são somas dos dez municípios e não formam taxas."
        ),
    }
    for visual in visuals:
        if visual["scopeId"] == SCOPE_VALE:
            visual["aggregationDisclosure"] = regional_aggregation_disclosures[
                visual["dossierId"]
            ]
        else:
            visual["aggregationDisclosure"] = (
                "Recorte municipal por identidade; nenhum agregado regional é atribuído a "
                "Nova Santa Rita."
            )
    return {
        "schemaVersion": "vocacoes-pne-aa4-visual-map-v1",
        "programId": "vocacoes-pne-advanced-analytics-v1",
        "stage": "AA4",
        "visualCount": len(visuals),
        "policy": {
            "questionAndTakeawayRequired": True,
            "underpoweredScatterAllowed": False,
            "p4Rule": "SEPARATE_UNITS_NO_SCATTER_NO_DUAL_AXIS",
            "trendMinimumTemporalPoints": 8,
            "paletteRootMaximum": 2,
            "nonColorDistinctionRequired": True,
        },
        "visuals": visuals,
    }


def _collect_fact_ids(payload: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(payload, Mapping):
        for key, value in payload.items():
            if key in {"factIds", "baselineFactIds", "evidenceBasisFactIds"}:
                found.update(str(item) for item in value)
            else:
                found.update(_collect_fact_ids(value))
    elif isinstance(payload, list):
        for value in payload:
            found.update(_collect_fact_ids(value))
    return found


def _collect_manager_fact_ids(payload: Any) -> set[str]:
    """Coleta evidência exibível, excluindo notas técnicas recolhidas por contrato."""
    found: set[str] = set()
    if isinstance(payload, Mapping):
        for key, value in payload.items():
            if key == "technicalEvidence":
                continue
            if key in {"factIds", "baselineFactIds", "evidenceBasisFactIds"}:
                found.update(str(item) for item in value)
            else:
                found.update(_collect_manager_fact_ids(value))
    elif isinstance(payload, list):
        for value in payload:
            found.update(_collect_manager_fact_ids(value))
    return found


def _quality_checks(
    *, contract: Mapping[str, Any], facts: pd.DataFrame,
    vale: Mapping[str, Any], nsr: Mapping[str, Any],
    scenarios: Mapping[str, Any], agendas: Mapping[str, Any],
    visuals: Mapping[str, Any], input_hashes: Mapping[str, str],
    source_availability_counts: Mapping[str, int],
    opus_reconciliation: Mapping[str, Any],
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    def check(check_id: str, passed: bool, evidence: Any) -> None:
        checks.append({"checkId": check_id, "passed": bool(passed), "evidence": evidence})

    fact_ids = set(facts["fact_id"].astype(str))
    manager_refs = _collect_fact_ids([vale, nsr, scenarios, agendas, visuals])
    manager_visible_refs = _collect_manager_fact_ids(
        [vale, nsr, scenarios, agendas, visuals]
    )
    technical_refs = {
        str(fact_id)
        for payload in (vale, nsr)
        for dossier in payload["dossiers"]
        for fact_id in dossier["technicalEvidence"]["factIds"]
    }
    technical_only_refs = technical_refs - manager_visible_refs
    unreferenced_supporting = fact_ids - manager_refs
    missing_refs = sorted(manager_refs - fact_ids)
    eligible = set(
        facts.loc[facts["manager_facing_eligible"].eq(True), "fact_id"].astype(str)
    )
    dossier_refs = _collect_manager_fact_ids([vale, nsr])
    ineligible_manager_refs = sorted(dossier_refs - eligible)
    check("AA4_CLASSIFICATION_DATA_LOGIC", contract["classification"] == "DATA_LOGIC", contract["classification"])
    check("AA4_EXACT_SCOPES", {vale["scope"]["scopeId"], nsr["scope"]["scopeId"]} == {SCOPE_VALE, SCOPE_NSR}, [vale["scope"], nsr["scope"]])
    check("AA4_TEXTUAL_IBGE_IDENTITY", all(isinstance(code, str) and len(code) == 7 and code.isdigit() for code in VALE_CODES) and nsr["scope"]["municipalityIbgeCode"] == NSR_CODE, list(VALE_CODES))
    check("AA4_NSR_CONTAINED_IN_VALE_DISCLOSED", NSR_CODE in VALE_CODES and vale["scope"]["selectedMunicipalityContainedInRegion"] is True and nsr["scope"]["selectedMunicipalityContainedInRegion"] is True and all("aninhad" in item["containmentDisclosure"] for payload in (vale, nsr) for item in payload["dossiers"] if item["dossierId"] == "D1_CONTEXT_AND_TRAJECTORY"), {"selectedCode": NSR_CODE, "regionCodes": list(VALE_CODES)})
    check("AA4_EDUCATION_SCOPE", vale["educationNetworkScope"] == nsr["educationNetworkScope"] == "total_all_dependencies", "total_all_dependencies")
    check("AA4_FIVE_DOSSIERS_PER_SCOPE", len(vale["dossiers"]) == len(nsr["dossiers"]) == 5 and [d["dossierId"] for d in vale["dossiers"]] == list(DOSSIER_IDS) and [d["dossierId"] for d in nsr["dossiers"]] == list(DOSSIER_IDS), {"vale": len(vale["dossiers"]), "nsr": len(nsr["dossiers"])})
    check("AA4_BIDIRECTIONAL_READING", all("pneToTerritory" in item and "territoryToPne" in item for payload in (vale, nsr) for item in payload["dossiers"]), "10/10 dossiers")
    check("AA4_INCREMENTAL_VALUE_RUBRIC", all(all(value is True for key, value in item["incrementalValueAssessment"].items() if key != "justification") and item["incrementalValueAssessment"]["justification"] for payload in (vale, nsr) for item in payload["dossiers"]), "10/10 integrate two directions, time/comparison, boundary and planning")
    check("AA4_MANAGER_FACT_REFERENCES_RESOLVE", not missing_refs, missing_refs)
    check("AA4_MANAGER_DOSSIER_FACTS_ELIGIBLE", not ineligible_manager_refs, ineligible_manager_refs)
    p4_p6 = [item for payload in (vale, nsr) for item in payload["dossiers"] if item["primaryQuestionId"] in {"P4_YOUTH_WORK_AND_HIGH_SCHOOL", "P6_ADULT_SCHOOLING_WORK_AND_EJA"}]
    check("AA4_P4_P6_TERMINALS_PRESERVED", all("NO_ROBUST_ASSOCIATION" in item["relationshipState"] and item["technicalEvidence"]["terminalState"] == "NO_ROBUST_ASSOCIATION" for item in p4_p6), [item["relationshipState"] for item in p4_p6])
    check("AA4_P4_P6_COEFFICIENTS_NOT_STANDALONE", all(item["technicalEvidence"]["standaloneCoefficientAllowed"] is False and item["technicalEvidence"]["displayMode"] == "COLLAPSED_TECHNICAL_NOTE" for item in p4_p6), [item["technicalEvidence"] for item in p4_p6])
    check("AA4_P5_CBO2_NOMENCLATURE_ONLY", all("CBO_2_DIGIT_ONLY" in item["claimCeiling"] and all(token in item["forbiddenConclusion"].lower() for token in ("demanda", "empreg")) for payload in (vale, nsr) for item in payload["dossiers"] if item["primaryQuestionId"] == "P5_OCCUPATIONS_AND_EPT"), "P5 scopes=2")
    check("AA4_P8_BLOCKED", all(payload["blockedManagerFacingRelations"] == [{"questionId": "P8_FINANCING_OFFER_AND_CAPACITY", "terminalState": "INSUFFICIENT_DATA", "reason": "AA2 não sustentou desenho válido; AA3 bloqueou promoção gerencial."}] for payload in (vale, nsr)), "blocked in both scopes")
    check("AA4_SOCIAL_CONTEXT_NOT_TESTED", all(payload["transversalContext"]["socialContext"]["terminalState"] == "RELATIONSHIP_NOT_TESTED_IN_AA2" and payload["transversalContext"]["socialContext"]["prevalenceAllowed"] is False for payload in (vale, nsr)), "context-only")
    expected_dispositions = {
        "RURALITY": "INCLUDED_TRANSVERSAL_P7_CONTEXT_ONLY",
        "INCLUSION_AEE": "INCLUDED_TRANSVERSAL_P7_CONTEXT_ONLY",
        "SOCIAL_REGISTERED_CONTEXT": "INCLUDED_TRANSVERSAL_NOT_TESTED",
        "FINANCING_CAPACITY": "BLOCKED_MANAGER_FACING",
    }
    check("AA4_TRANSVERSAL_AXES_DISPOSITIONED", all({item["axisId"]: item["disposition"] for item in payload["transversalContext"]["axisDispositions"]} == expected_dispositions for payload in (vale, nsr)), expected_dispositions)
    d2_rows = [item for payload in (vale, nsr) for item in payload["dossiers"] if item["dossierId"] == "D2_DEMOGRAPHY_AND_NETWORK"]
    decomposition_closes = True
    closure_evidence: dict[str, float] = {}
    for tag in ("NSR", "VALE"):
        total = _value(_fact_index(facts), f"F_D2_{tag}_HS_ENROLL_CHANGE_2018_2025", "absolute_change")
        components = sum(_value(_fact_index(facts), f"F_D2_{tag}_{suffix}_2018_2025", "effect_estimate") for suffix in ("POP_COMPONENT", "RELATION_COMPONENT"))
        closure_evidence[tag] = abs(total - components)
        decomposition_closes = decomposition_closes and math.isclose(total, components, abs_tol=1e-9)
    check("AA4_D2_ACCOUNTING_IDENTITY_CLOSES", decomposition_closes, closure_evidence)
    check("AA4_D2_NO_BEHAVIORAL_RESIDUAL_LABEL", all("não como projeção ou estimativa de migração" in item["territoryToPne"]["planningImplication"] for item in d2_rows), "residual guarded")
    zero_rows = facts.loc[(facts["availability_state_start"].eq("observed_zero")) | (facts["availability_state_end"].eq("observed_zero"))]
    check("AA4_ZERO_STATE_PRESERVED", not zero_rows.empty and all((row["value_start"] == 0 if row["availability_state_start"] == "observed_zero" else True) and (row["value_end"] == 0 if row["availability_state_end"] == "observed_zero" else True) for _, row in zero_rows.iterrows()), {"rowCount": len(zero_rows)})
    check("AA4_PERCENT_CHANGE_ZERO_DENOMINATOR_NULL", facts.loc[facts["percent_change_state"].eq("NOT_APPLICABLE_ZERO_START"), "percent_change"].isna().all(), int(facts["percent_change_state"].eq("NOT_APPLICABLE_ZERO_START").sum()))
    check("AA4_THREE_CONDITIONAL_SCENARIOS", len(scenarios["scenarios"]) >= 3 and set(item["scenarioId"] for item in scenarios["scenarios"]) == set(SCENARIO_IDS) and all(item["scenarioType"] == "CONDITIONAL_NOT_FORECAST" for item in scenarios["scenarios"]), [item["scenarioId"] for item in scenarios["scenarios"]])
    check("AA4_SCENARIOS_NON_INTERCHANGEABLE", scenarios["scenariosAreMutuallyNonInterchangeable"] is True and len({tuple(item["relatedDossierIds"]) for item in scenarios["scenarios"]}) == 3, scenarios["nonInterchangeabilityReason"])
    scenario_domains = [item["decisionDomain"] for item in scenarios["scenarios"]]
    indicator_signatures = [tuple(item["primaryIndicatorFamilies"]) for item in scenarios["scenarios"]]
    check("AA4_SCENARIO_DIFFERENTIATION_MECHANICAL", len(set(scenario_domains)) == len(scenario_domains) == 3 and len(set(indicator_signatures)) == 3 and all(len(item["notInterchangeableWith"]) == 2 for item in scenarios["scenarios"]), {"decisionDomains": scenario_domains, "indicatorSignatures": indicator_signatures})
    p2_scenario = next(item for item in scenarios["scenarios"] if item["scenarioId"] == "SCN_DEMOGRAPHIC_PRESSURE_AND_NETWORK")
    check("AA4_P2_SCENARIO_RESIDUAL_GUARD", all(token in p2_scenario["residualInterpretationGuard"].lower() for token in ("migração", "cobertura", "comportamento", "resposta institucional")), p2_scenario["residualInterpretationGuard"])
    check("AA4_AA5_SCENARIO_FLOOR", scenarios["aa4MinimumScenarioCount"] == 3 and scenarios["aa5MayReduceBelowAa4Minimum"] is False, "AA5 cannot reduce below three without reopening AA4")
    scenario_keys = {
        str(key).lower()
        for item in scenarios["scenarios"]
        for key in item
    }
    check(
        "AA4_NO_FUTURE_NUMERIC_PROJECTIONS",
        scenarios["futureNumericProjectionAllowed"] is False
        and not scenario_keys.intersection(
            {"numericprojection", "futurevalue", "forecastvalue", "projectedvalue"}
        ),
        "Nenhum valor futuro é produzido; números citados pertencem às definições e aos fatos históricos.",
    )
    required_agenda_fields = {
        "observedCondition", "exposedPopulation", "educationStage", "territoryExposed",
        "concreteAction", "responsibilityLevel", "leadResponsibility", "contributors",
        "indicators", "baselineFactIds", "triggerDefinition", "cadence", "strengthenIf",
        "weakenIf",
    }
    check("AA4_FIVE_COMPLETE_AGENDAS", len(agendas["agendas"]) == 5 and [item["agendaId"] for item in agendas["agendas"]] == list(AGENDA_IDS) and all(required_agenda_fields.issubset(item) and all(item[field] for field in required_agenda_fields) for item in agendas["agendas"]), {"agendaCount": len(agendas["agendas"])})
    check("AA4_AGENDA_RESPONSIBILITY_LEVELS", all(item["responsibilityLevel"] in {"municipal", "regional/shared", "external"} for item in agendas["agendas"]), [item["responsibilityLevel"] for item in agendas["agendas"]])
    check("AA4_AGENDA_SHARED_SCOPE_VARIANTS", all(item["sharedAcrossScopes"] is True and {variant["scopeId"] for variant in item["scopeVariants"]} == {SCOPE_NSR, SCOPE_VALE} and all(variant["baselineFactIds"] and variant["triggerDefinition"] and variant["territoryRole"] for variant in item["scopeVariants"]) and {mapping["scopeId"] for mapping in item["dossierMappings"]} == {SCOPE_NSR, SCOPE_VALE} for item in agendas["agendas"]), "5 thematic agendas × 2 explicit scope variants")
    check("AA4_VISUAL_QUESTION_TAKEAWAY", all(item["question"] and item["takeaway"] for item in visuals["visuals"]), visuals["visualCount"])
    check("AA4_VISUAL_NO_SCATTER_OR_DUAL_AXIS", all("SCATTER" not in item["recommendedForm"] and "DUAL_AXIS" not in item["recommendedForm"] for item in visuals["visuals"]), [item["recommendedForm"] for item in visuals["visuals"]])
    check("AA4_P4_SEPARATE_UNITS", all(item["recommendedForm"] == "SEPARATE_UNIT_START_END_BARS" and len(item["units"]) == 2 for item in visuals["visuals"] if item["dossierId"] == "D3_YOUTH_WORK_AND_HIGH_SCHOOL"), "two panels")
    check("AA4_D5_TREND_SUFFICIENCY", all(len(item["factIds"]) == 24 and "Doze pontos" in item["dataSufficiency"] for item in visuals["visuals"] if item["dossierId"] == "D5_ADULT_SCHOOLING_WORK_AND_EJA"), "12 points per stage")
    check("AA4_D1_VISUAL_BOUNDARY_ADJACENT", all(item["terminalState"] == "CONTEXT_COMPARISON_COMPLETE_WITH_P3_NO_ROBUST_ASSOCIATION" and all(token in item["forbiddenConclusion"].lower() for token in ("meta", "previsão", "associação")) for item in visuals["visuals"] if item["dossierId"] == "D1_CONTEXT_AND_TRAJECTORY"), "D1 interval is not target, forecast or P3 association")
    vale_rate_visuals = [
        item
        for item in visuals["visuals"]
        if item["scopeId"] == SCOPE_VALE
        and item["dossierId"]
        in {"D1_CONTEXT_AND_TRAJECTORY", "D3_YOUTH_WORK_AND_HIGH_SCHOOL"}
    ]
    check("AA4_REGIONAL_AGGREGATION_LABELS", all(item.get("aggregationDisclosure") for item in visuals["visuals"]) and all("mediana" in item["aggregationDisclosure"].lower() and "não é taxa regional ponderada" in item["aggregationDisclosure"].lower() for item in vale_rate_visuals), [item["aggregationDisclosure"] for item in vale_rate_visuals])
    check("AA4_VISUAL_TWO_ROOT_PALETTE", all(item["palette"]["rootColorCount"] <= 2 and item["nonColorDistinction"] for item in visuals["visuals"]), "hard cap=2")
    check("AA4_WATERFALL_ONLY_ADDITIVE", all(item["additiveIdentityVerified"] is True for item in visuals["visuals"] if item["recommendedForm"] == "ADDITIVE_WATERFALL"), "D2 only")
    check("AA4_FACT_GRAIN_UNIQUE", not facts["fact_id"].duplicated().any(), len(facts))
    check("AA4_FACT_STATES_DISTINCT", {"observed", "observed_zero"}.issubset(set(facts["availability_state_start"].dropna())), sorted(set(facts["availability_state_start"].dropna())))
    expected_availability_policy = {
        "observed": "MATERIALIZE_NUMERIC_FACT",
        "observed_zero": "MATERIALIZE_ZERO_WITH_EXPLICIT_STATE",
        "unavailable": "DO_NOT_COERCE_TO_ZERO_OR_NUMERIC_FACT",
        "suppressed": "DO_NOT_COERCE_TO_ZERO_OR_NUMERIC_FACT",
        "not_applicable": "NULL_WITH_EXPLICIT_STATE",
        "row_absent": "NO_FACT_AND_NEVER_ZERO",
    }
    check("AA4_AVAILABILITY_DISPOSITION_EXPLICIT", all(payload["availabilityPolicy"] == expected_availability_policy for payload in (vale, nsr)) and source_availability_counts.get("observed", 0) > 0 and source_availability_counts.get("observed_zero", 0) > 0 and source_availability_counts.get("unavailable", 0) > 0, {"sourceStateCounts": dict(source_availability_counts), "policy": expected_availability_policy})
    check("AA4_UNREFERENCED_FACTS_ACCOUNTED", manager_refs.issubset(fact_ids) and technical_refs.issubset(manager_refs) and len(manager_refs) + len(unreferenced_supporting) == len(facts), {"managerVisible": len(manager_visible_refs), "technicalOnly": len(technical_only_refs), "allReferenced": len(manager_refs), "unreferencedSupporting": len(unreferenced_supporting), "rationale": "Séries intermediárias completas, pontos não escolhidos por suficiência visual e trilha técnica permanecem auditáveis sem redundância gerencial."})
    check("AA4_PUBLICATION_BLOCKED_UNTIL_AA5", all(payload["managerFacingPublicationAllowed"] is False and payload["downstreamState"] == "AA5_SELECTION_INPUT_ONLY_NOT_PUBLIC" for payload in (vale, nsr)), "not public")
    check("AA4_FROZEN_INPUT_HASH_COUNT", len(input_hashes) == 17, len(input_hashes))
    check("AA4_GENERATION_GUARDS", contract["generation"] == {"deterministic": True, "pythonHashSeeds": [505, 606], "networkUsed": False, "databaseUsed": False, "publicDataWritesAllowed": False, "fullBuildAllowed": False}, contract["generation"])
    check("AA4_OPUS_REAUDIT_ON_TRACK_AND_AA5_ENTRY_ALLOWED", opus_reconciliation["initial"]["verdict"] == "ON_TRACK" and opus_reconciliation["reAudit"]["verdict"] == "ON_TRACK" and opus_reconciliation["reAudit"]["aa5EntryAllowed"] is True and opus_reconciliation["reAudit"]["entryConditionsReconciled"] is True, opus_reconciliation)
    failed = [item for item in checks if not item["passed"]]
    qa = {
        "schemaVersion": "vocacoes-pne-aa4-qa-v1",
        "programId": "vocacoes-pne-advanced-analytics-v1",
        "stage": "AA4",
        "generatedAt": GENERATED_AT,
        "state": "PASS" if not failed else "FAIL",
        "checkCount": len(checks),
        "passedCount": len(checks) - len(failed),
        "failedCount": len(failed),
        "checks": checks,
        "counts": {
            "factCount": len(facts),
            "managerReferencedFactCount": len(manager_refs),
            "managerVisibleFactCount": len(manager_visible_refs),
            "technicalOnlyReferencedFactCount": len(technical_only_refs),
            "unreferencedSupportingFactCount": len(unreferenced_supporting),
            "dossierCount": len(vale["dossiers"]) + len(nsr["dossiers"]),
            "scenarioCount": len(scenarios["scenarios"]),
            "agendaCount": len(agendas["agendas"]),
            "visualCount": len(visuals["visuals"]),
        },
    }
    if failed:
        raise DossierValidationError(
            "QA AA4 falhou: " + ", ".join(item["checkId"] for item in failed)
        )
    return qa


def build_dossier_package(
    *, expected_public_digest: str | None = None
) -> dict[str, Any]:
    if expected_public_digest is not None and expected_public_digest != EXPECTED_PUBLIC_DATA_BASELINE_SHA256:
        raise DossierValidationError("Digest público esperado não corresponde ao baseline explícito AA4.")
    input_hashes = verify_frozen_inputs(verify_public_baseline=expected_public_digest is not None)
    opus_reconciliation = verify_opus_reconciliation()
    contract = _load_json(CONTRACT_PATH)
    sources = _load_sources()
    facts, groups = _build_facts(sources)
    vale = _build_scope_dossiers(scope_id=SCOPE_VALE, facts=facts, groups=groups, sources=sources)
    nsr = _build_scope_dossiers(scope_id=SCOPE_NSR, facts=facts, groups=groups, sources=sources)
    scenarios = _build_scenarios()
    agendas = _build_agendas()
    visuals = _build_visual_map(groups)
    source_availability_counts = {
        str(state): int(count)
        for state, count in sources["panel"]["availability_state"]
        .value_counts(dropna=False)
        .items()
    }
    qa = _quality_checks(
        contract=contract,
        facts=facts,
        vale=vale,
        nsr=nsr,
        scenarios=scenarios,
        agendas=agendas,
        visuals=visuals,
        input_hashes=input_hashes,
        source_availability_counts=source_availability_counts,
        opus_reconciliation=opus_reconciliation,
    )
    return {
        "contract": contract,
        "input_hashes": input_hashes,
        "facts": facts,
        "vale": vale,
        "nsr": nsr,
        "scenarios": scenarios,
        "agendas": agendas,
        "visuals": visuals,
        "qa": qa,
        "source_availability_counts": source_availability_counts,
        "opus_reconciliation": opus_reconciliation,
    }


def _artifact_records(output_dir: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for filename in NON_MANIFEST_FILES:
        path = output_dir / filename
        if not path.is_file():
            raise DossierValidationError(f"Artefato AA4 ausente: {path}.")
        records.append(
            {
                "path": filename,
                "sha256": sha256_file(path),
                "byteSize": path.stat().st_size,
            }
        )
    return records


def _artifact_set_digest(output_dir: Path) -> str:
    return hashlib.sha256(canonical_json_bytes(_artifact_records(output_dir))).hexdigest()


def _directory_digest(path: Path) -> str:
    return directory_content_digest(path)


def materialize_package(
    output_dir: Path,
    *,
    entry_public_digest: str,
) -> dict[str, Any]:
    if entry_public_digest != EXPECTED_PUBLIC_DATA_BASELINE_SHA256:
        raise DossierValidationError("Materialização AA4 iniciou fora do baseline público explícito.")
    if output_dir.exists() and any(output_dir.iterdir()):
        raise DossierValidationError(f"Diretório candidato AA4 não está vazio: {output_dir}.")
    output_dir.mkdir(parents=True, exist_ok=True)
    bundle = build_dossier_package(expected_public_digest=entry_public_digest)
    atomic_write_json(output_dir / VALE_FILE, bundle["vale"])
    atomic_write_json(output_dir / NSR_FILE, bundle["nsr"])
    atomic_write_json(output_dir / SCENARIOS_FILE, bundle["scenarios"])
    atomic_write_json(output_dir / AGENDAS_FILE, bundle["agendas"])
    atomic_write_json(output_dir / VISUALS_FILE, bundle["visuals"])
    write_csv_gzip(output_dir / FACTS_FILE, bundle["facts"])
    atomic_write_json(output_dir / QA_FILE, bundle["qa"])
    public_after_nonmanifest = directory_content_digest(REPO_ROOT / "public/data")
    if public_after_nonmanifest != entry_public_digest:
        raise DossierValidationError("public/data mudou durante a geração não manifesta AA4.")
    artifacts = _artifact_records(output_dir)
    artifact_set_digest = _artifact_set_digest(output_dir)
    manifest = {
        "schemaVersion": "vocacoes-pne-aa4-manifest-v1",
        "programId": "vocacoes-pne-advanced-analytics-v1",
        "stage": "AA4",
        "generatedAt": GENERATED_AT,
        "classification": "DATA_LOGIC",
        "finalState": "AA4_COMPLETE_OPUS_REAUDIT_ON_TRACK",
        "scope": {
            "state": "RS",
            "regionId": "REGION_VALE_DO_SINOS",
            "regionMunicipalityIbgeCodes": list(VALE_CODES),
            "selectedMunicipalityIbgeCode": NSR_CODE,
            "selectedMunicipalityContainedInRegion": True,
            "municipalityIdentity": "textual_ibge_code_7_digits",
            "educationNetworkScope": "total_all_dependencies",
        },
        "counts": bundle["qa"]["counts"],
        "availabilityIntegrity": {
            "sourceStateCounts": bundle["source_availability_counts"],
            "dispositionPolicy": bundle["contract"]["availabilityPolicy"],
            "unavailableSuppressedOrAbsentNeverCoercedToZero": True,
        },
        "qa": {
            "state": bundle["qa"]["state"],
            "checkCount": bundle["qa"]["checkCount"],
            "failedCount": bundle["qa"]["failedCount"],
        },
        "opusReconciliation": bundle["opus_reconciliation"],
        "inputHashes": bundle["input_hashes"],
        "artifacts": artifacts,
        "artifactSetDigestSha256": artifact_set_digest,
        "contentPolicy": {
            "twoReadingDirections": True,
            "theoryMayCreateLocalEffect": False,
            "futureNumericProjectionAllowed": False,
            "p4AndP6TerminalState": "NO_ROBUST_ASSOCIATION",
            "p5Interpretation": "NOMENCLATURAL_CBO_TWO_DIGIT_ONLY",
            "p8ManagerFacingAllowed": False,
            "socialRelationshipState": "RELATIONSHIP_NOT_TESTED_IN_AA2",
        },
        "runtime": {
            "pythonExecutable": sys.executable,
            "pythonVersion": sys.version.split()[0],
            "pythonHashSeed": os.environ.get("PYTHONHASHSEED", "UNSET"),
        },
        "generation": {
            "deterministic": True,
            "manifestLast": True,
            "transactionalPromotion": True,
            "networkGuardEnabled": True,
            "networkUsed": False,
            "databaseUsed": False,
            "publicDataWritten": False,
            "fullBuildUsed": False,
        },
        "publicDataIntegrity": {
            "baselineRole": "WRITE_INTEGRITY_BASELINE_ONLY_NOT_ANALYTICAL_INPUT",
            "automaticRebaselineAllowed": False,
            "beforeTreeDigestSha256": entry_public_digest,
            "afterTreeDigestSha256": public_after_nonmanifest,
            "notWrittenByAa4": True,
        },
        "independentMaterializationVerification": {
            "state": "PENDING_PARENT_VERIFICATION",
            "processCount": 1,
        },
        "downstreamState": "AA5_SELECTION_INPUT_ONLY_NOT_PUBLIC",
    }
    atomic_write_json(output_dir / MANIFEST_FILE, manifest)
    return manifest


def materialize_single_candidate(output_dir: Path) -> dict[str, Any]:
    public_before = directory_content_digest(REPO_ROOT / "public/data")
    if public_before != EXPECTED_PUBLIC_DATA_BASELINE_SHA256:
        raise DossierValidationError("Candidato AA4 observou baseline público divergente.")
    modules_before = set(sys.modules)
    with blocked_external_io_guard():
        manifest = materialize_package(
            output_dir,
            entry_public_digest=public_before,
        )
    public_after = directory_content_digest(REPO_ROOT / "public/data")
    if public_after != public_before:
        raise DossierValidationError("public/data mudou durante a materialização candidata AA4.")
    loaded_roots = {
        module.split(".", 1)[0]
        for module in set(sys.modules) - modules_before
    }
    loaded_network = sorted(loaded_roots & NETWORK_CLIENT_MODULE_ROOTS)
    loaded_database = sorted(loaded_roots & DATABASE_CLIENT_MODULE_ROOTS)
    if loaded_network or loaded_database:
        raise DossierValidationError(
            f"Cliente externo carregado no AA4: rede={loaded_network}; banco={loaded_database}."
        )
    return {
        "state": "AA4_SINGLE_CANDIDATE_COMPLETE",
        "outputDir": str(output_dir.resolve()),
        "artifactSetDigestSha256": manifest["artifactSetDigestSha256"],
        "manifestSha256": sha256_file(output_dir / MANIFEST_FILE),
        "treeDigestSha256": _directory_digest(output_dir),
        "nonManifestDigests": {
            item["path"]: item["sha256"] for item in manifest["artifacts"]
        },
        "networkGuardEnabled": True,
        "databaseGuardEnabled": True,
        "loadedNetworkClientModules": loaded_network,
        "loadedDatabaseClientModules": loaded_database,
        "publicDataBeforeTreeDigestSha256": public_before,
        "publicDataAfterTreeDigestSha256": public_after,
    }


def _run_candidate_process(output_dir: Path, *, python_hash_seed: str) -> dict[str, Any]:
    environment = os.environ.copy()
    environment["PYTHONHASHSEED"] = python_hash_seed
    completed = subprocess.run(
        [
            sys.executable,
            str(RUNNER_PATH),
            "--single-candidate",
            "--output-dir",
            str(output_dir),
        ],
        cwd=REPO_ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if completed.returncode != 0:
        raise DossierValidationError(
            f"Processo candidato AA4 falhou (seed={python_hash_seed}, exit={completed.returncode}): "
            f"{completed.stderr.strip() or completed.stdout.strip()}"
        )
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise DossierValidationError(
            f"Saída candidata AA4 inválida (seed={python_hash_seed})."
        ) from error
    payload["pythonHashSeed"] = python_hash_seed
    return payload


def _normalize_candidate_manifests(
    candidates: Sequence[Path],
    receipts: Sequence[Mapping[str, Any]],
) -> None:
    pre_manifest_digests = [
        sha256_file(candidate / MANIFEST_FILE) for candidate in candidates
    ]
    pre_tree_digests = [_directory_digest(candidate) for candidate in candidates]
    shared_verification = {
        "state": "VERIFIED_IDENTICAL",
        "processCount": 2,
        "pythonHashSeeds": ["505", "606"],
        "comparisonScope": "PRE_NORMALIZATION_NON_MANIFEST_AND_POST_NORMALIZATION_FULL_TREE",
        "preNormalizationCandidateManifestDigests": pre_manifest_digests,
        "preNormalizationCandidateTreeDigests": pre_tree_digests,
        "nonManifestArtifactSetDigestSha256": receipts[0]["artifactSetDigestSha256"],
        "nonManifestEqualityVerifiedByParent": True,
        "postNormalizationFinalTreeEqualityVerifiedByParent": True,
    }
    for candidate in candidates:
        manifest = _load_json(candidate / MANIFEST_FILE)
        manifest["runtime"]["pythonHashSeed"] = "MULTI_PROCESS_FINALIZED"
        manifest["runtime"]["pythonHashSeeds"] = ["505", "606"]
        manifest["independentMaterializationVerification"] = shared_verification
        atomic_write_json(candidate / MANIFEST_FILE, manifest)


def _replace_directory_transactionally(staging: Path, target: Path) -> bool:
    target.parent.mkdir(parents=True, exist_ok=True)
    backup = target.parent / f".{target.name}.backup-aa4"
    if backup.exists():
        raise DossierValidationError(f"Backup transacional AA4 preexistente: {backup}.")
    had_target = target.exists()
    try:
        if had_target:
            os.replace(target, backup)
        os.replace(staging, target)
    except Exception:
        if target.exists() and not had_target:
            shutil.rmtree(target)
        if backup.exists():
            os.replace(backup, target)
        raise
    if backup.exists():
        shutil.rmtree(backup)
    return had_target


def validate_existing_output(
    output_dir: Path = DEFAULT_OUTPUT_ROOT,
    *,
    verify_rebuild: bool = True,
) -> dict[str, Any]:
    if not output_dir.is_dir():
        raise DossierValidationError(f"Pacote AA4 ausente: {output_dir}.")
    expected_files = set(NON_MANIFEST_FILES) | {MANIFEST_FILE}
    observed_files = {path.name for path in output_dir.iterdir() if path.is_file()}
    if observed_files != expected_files:
        raise DossierValidationError(
            f"Conjunto de arquivos AA4 divergente: {sorted(observed_files)}."
        )
    manifest = _load_json(output_dir / MANIFEST_FILE)
    if manifest.get("artifactSetDigestSha256") != _artifact_set_digest(output_dir):
        raise DossierValidationError("Digest do conjunto AA4 divergente.")
    artifacts = _artifact_records(output_dir)
    if artifacts != manifest.get("artifacts"):
        raise DossierValidationError("Registros de artefatos AA4 divergentes.")
    if [item["path"] for item in artifacts] != list(NON_MANIFEST_FILES):
        raise DossierValidationError("Ordem contratual de artefatos AA4 divergente.")
    input_hashes = verify_frozen_inputs(verify_public_baseline=True)
    if manifest.get("inputHashes") != input_hashes:
        raise DossierValidationError("Hashes de entrada do manifesto AA4 divergentes.")
    qa = _load_json(output_dir / QA_FILE)
    if qa.get("state") != "PASS" or qa.get("failedCount") != 0:
        raise DossierValidationError("QA materializado AA4 não está aprovado.")
    vale = _load_json(output_dir / VALE_FILE)
    nsr = _load_json(output_dir / NSR_FILE)
    scenarios = _load_json(output_dir / SCENARIOS_FILE)
    agendas = _load_json(output_dir / AGENDAS_FILE)
    visuals = _load_json(output_dir / VISUALS_FILE)
    facts = pd.read_csv(
        output_dir / FACTS_FILE,
        dtype={"fact_id": "string", "scope_id": "string", "dimension_id": "string"},
        keep_default_na=False,
        na_values=["null"],
    )
    if len(facts) != manifest["counts"]["factCount"]:
        raise DossierValidationError("Contagem de fatos AA4 divergente.")
    if len(vale.get("dossiers", [])) != 5 or len(nsr.get("dossiers", [])) != 5:
        raise DossierValidationError("Dossiês materializados AA4 incompletos.")
    if len(scenarios.get("scenarios", [])) != 3 or len(agendas.get("agendas", [])) != 5:
        raise DossierValidationError("Cenários ou agendas AA4 incompletos.")
    if not visuals.get("visuals") or visuals.get("visualCount") != len(visuals["visuals"]):
        raise DossierValidationError("Mapa visual AA4 incompleto.")
    verification = manifest.get("independentMaterializationVerification", {})
    if (
        verification.get("state") != "VERIFIED_IDENTICAL"
        or verification.get("processCount") != 2
        or verification.get("pythonHashSeeds") != ["505", "606"]
        or verification.get("nonManifestEqualityVerifiedByParent") is not True
        or verification.get("postNormalizationFinalTreeEqualityVerifiedByParent") is not True
    ):
        raise DossierValidationError("Verificação determinística AA4 incompleta.")
    if (
        manifest.get("generation", {}).get("manifestLast") is not True
        or manifest.get("generation", {}).get("networkUsed") is not False
        or manifest.get("generation", {}).get("databaseUsed") is not False
        or manifest.get("generation", {}).get("publicDataWritten") is not False
        or manifest.get("publicDataIntegrity", {}).get("notWrittenByAa4") is not True
        or manifest.get("opusReconciliation", {}).get("reAudit", {}).get("verdict")
        != "ON_TRACK"
        or manifest.get("opusReconciliation", {}).get("reAudit", {}).get(
            "aa5EntryAllowed"
        )
        is not True
    ):
        raise DossierValidationError("Guardas de geração AA4 divergentes.")
    if verify_rebuild:
        rebuilt = build_dossier_package(
            expected_public_digest=EXPECTED_PUBLIC_DATA_BASELINE_SHA256
        )
        if rebuilt["qa"]["counts"] != manifest["counts"]:
            raise DossierValidationError("Reconstrução pura AA4 divergiu nas contagens.")
    return manifest


def materialize_twice_transactionally(
    output_dir: Path = DEFAULT_OUTPUT_ROOT,
) -> dict[str, Any]:
    public_before = directory_content_digest(REPO_ROOT / "public/data")
    if public_before != EXPECTED_PUBLIC_DATA_BASELINE_SHA256:
        raise DossierValidationError(
            "public/data divergiu antes do AA4; reconciliação explícita é obrigatória."
        )
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="vocacoes-pne-aa4-candidates-") as temporary:
        temp_root = Path(temporary)
        first = temp_root / "candidate-505"
        second = temp_root / "candidate-606"
        first_receipt = _run_candidate_process(first, python_hash_seed="505")
        second_receipt = _run_candidate_process(second, python_hash_seed="606")
        receipts = [first_receipt, second_receipt]
        for receipt in receipts:
            if (
                receipt["networkGuardEnabled"] is not True
                or receipt["databaseGuardEnabled"] is not True
                or receipt["loadedNetworkClientModules"]
                or receipt["loadedDatabaseClientModules"]
                or receipt["publicDataBeforeTreeDigestSha256"] != public_before
                or receipt["publicDataAfterTreeDigestSha256"] != public_before
            ):
                raise DossierValidationError("Guarda candidata AA4 divergente.")
        if first_receipt["nonManifestDigests"] != second_receipt["nonManifestDigests"]:
            raise DossierValidationError("Artefatos não manifestos AA4 divergiram entre processos.")
        if first_receipt["artifactSetDigestSha256"] != second_receipt["artifactSetDigestSha256"]:
            raise DossierValidationError("Digest de conjunto AA4 divergiu entre processos.")
        _normalize_candidate_manifests([first, second], receipts)
        first_tree = _directory_digest(first)
        second_tree = _directory_digest(second)
        if first_tree != second_tree:
            raise DossierValidationError("Árvores AA4 divergiram após normalização do manifesto.")
        staging = Path(
            tempfile.mkdtemp(
                prefix=f".{output_dir.name}.staging-",
                dir=output_dir.parent,
            )
        )
        try:
            shutil.copytree(first, staging, dirs_exist_ok=True)
            if _directory_digest(staging) != first_tree:
                raise DossierValidationError("Cópia de staging AA4 divergiu do candidato validado.")
            had_target = _replace_directory_transactionally(staging, output_dir)
        finally:
            if staging.exists():
                shutil.rmtree(staging)
    public_after = directory_content_digest(REPO_ROOT / "public/data")
    if public_after != public_before:
        raise DossierValidationError("public/data mudou durante a promoção transacional AA4.")
    manifest = validate_existing_output(output_dir)
    return {
        "state": manifest["finalState"],
        "outputDir": str(output_dir.resolve()),
        "artifactSetDigestSha256": manifest["artifactSetDigestSha256"],
        "fullTreeDigestSha256": _directory_digest(output_dir),
        "candidateTreeDigestSha256": first_tree,
        "pythonHashSeeds": ["505", "606"],
        "independentMaterializationState": "VERIFIED_IDENTICAL",
        "replacedExistingTarget": had_target,
        "publicDataTreeDigestSha256": public_after,
        "networkUsed": False,
        "databaseUsed": False,
        "fullBuildUsed": False,
    }
