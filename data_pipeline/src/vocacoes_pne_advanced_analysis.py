from __future__ import annotations

import gc
import hashlib
import itertools
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
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
import pandas as pd

from .vocacoes_pne_job2 import directory_content_digest, write_csv_gzip
from .vocacoes_pne_job3 import two_way_within


REPO_ROOT = Path(__file__).resolve().parents[2]
AA1_ROOT = REPO_ROOT / ".tmp" / "vocacoes-pne" / "advanced-analytics-v1" / "aa1"
PANEL_PATH = AA1_ROOT / "PAINEL_ANALITICO_ESTADUAL_AA1.csv.gz"
AA1_GATE_PATH = AA1_ROOT / "AA2_ENTRY_GATE_AA1.json"
AA1_MANIFEST_PATH = AA1_ROOT / "MANIFEST_AA1.json"
PREREGISTRATION_PATH = (
    REPO_ROOT / "docs" / "PRE_REGISTRO_AA2_AVANCO_ANALITICO_VOCACOES_PNE.json"
)
PREREGISTRATION_FREEZE_PATH = (
    REPO_ROOT
    / "data_pipeline"
    / "contracts"
    / "vocacoes-pne-aa2-preregistration-freeze.json"
)
CONTRACT_PATH = (
    REPO_ROOT
    / "data_pipeline"
    / "contracts"
    / "vocacoes-pne-advanced-analysis-v1.json"
)
REGIONS_PATH = REPO_ROOT / "config" / "regions" / "rs.json"
BRIDGE_PATH = (
    REPO_ROOT
    / ".tmp"
    / "vocacoes-pne"
    / "v7-job2"
    / "2d"
    / "cursos_cbo_2025.csv.gz"
)
PREREG_PROBE_ROOT = (
    REPO_ROOT
    / ".tmp"
    / "vocacoes-pne"
    / "advanced-analytics-v1"
    / "aa2-prereg"
)
PREREG_PROBE_PATH = PREREG_PROBE_ROOT / "AVAILABILITY_PROBE_AA2.json"
DEFAULT_OUTPUT_ROOT = (
    REPO_ROOT / ".tmp" / "vocacoes-pne" / "advanced-analytics-v1" / "aa2"
)
RUNNER_PATH = (
    REPO_ROOT
    / "data_pipeline"
    / "scripts"
    / "run_vocacoes_pne_advanced_analysis.py"
)

EXPECTED_AA1_PANEL_SHA256 = (
    "d6cadfec911863b93699b826da6ef340687db5c0f77350319a9eeefa0dfb652f"
)
EXPECTED_AA1_GATE_SHA256 = (
    "8baef0754bd6e7b5caa5428e9cf16d8ae3c01d3eace4de68d24d1e42ba286f02"
)
EXPECTED_AA1_ARTIFACT_SET_SHA256 = (
    "b5209061aff00ecae4b279165f3fd380b9324bcc845d1ad279a31a42f8bd3366"
)
EXPECTED_BRIDGE_SHA256 = (
    "cf60bb4cb49bbe15a35af728b83783418e67fc76c215838521ef14992047f867"
)
EXPECTED_PREREGISTRATION_SHA256 = (
    "aa931e75a8530bf0f9c22c48b937ef0b92b40210240da012bdb33ed16ff24a25"
)
EXPECTED_PREREGISTRATION_FREEZE_SHA256 = (
    "31a7e733b554f6230863e6cf3efbfa0f4e5389ecdc3a0b2ec359d914714e2c13"
)
EXPECTED_CONTRACT_SHA256 = (
    "9987c78041e6300322a4307693b757d7be6e136c7fbe78e482d5ca9956541403"
)
EXPECTED_PREREG_PROBE_SHA256 = (
    "070911de9c63c324318679e9cd91e7c065965ad1e934f3d518ad7ce219f3625c"
)
EXPECTED_PUBLIC_DATA_DIGEST = (
    "4a52e3891163cb3427c5c01f2ef5414c5fe7855dd491a9a125b509899dcc23e1"
)
GENERATED_AT = "2026-08-30T00:00:00-03:00"
NOVA_SANTA_RITA_CODE = "4313375"

RESULTS_FILE = "RESULTADOS_AA2.csv.gz"
ROBUSTNESS_FILE = "ROBUSTEZ_AA2.csv.gz"
HETEROGENEITY_FILE = "HETEROGENEIDADE_AA2.csv.gz"
SCOPE_COMPARISONS_FILE = "COMPARACOES_ESCOPO_AA2.csv.gz"
CLAIMS_FILE = "CLAIMS_AA2.json"
QA_FILE = "QA_SUMMARY_AA2.json"
MANIFEST_FILE = "MANIFEST_AA2.json"
NON_MANIFEST_FILES = (
    RESULTS_FILE,
    ROBUSTNESS_FILE,
    HETEROGENEITY_FILE,
    SCOPE_COMPARISONS_FILE,
    CLAIMS_FILE,
    QA_FILE,
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
    "google",
    "httpx",
    "requests",
    "urllib3",
}


class AdvancedAnalysisValidationError(ValueError):
    """Falha fechada do contrato ou da materialização AA2."""

PANEL_METADATA_COLUMNS = [
    "municipality_ibge_code",
    "year_or_reference_period",
    "stage_or_population_group",
    "metric_id",
    "dimension_id",
    "availability_state",
    "unavailability_reason",
    "territorial_lens",
    "network_scope",
    "coverage_scope",
    "coverage_reason",
    "reference_scope",
    "aggregation_guard",
]


def _selector(
    selector_id: str,
    question_id: str,
    metric_id: str,
    *,
    stage: str,
    periods: Iterable[str],
    coverage_scope: str,
    minimum_municipalities: int,
    minimum_periods: int,
    dimension_id: str = "ALL",
) -> dict[str, Any]:
    return {
        "selectorId": selector_id,
        "questionId": question_id,
        "metricId": metric_id,
        "stage": stage,
        "periods": list(periods),
        "coverageScope": coverage_scope,
        "minimumMunicipalities": minimum_municipalities,
        "minimumPeriods": minimum_periods,
        "dimensionId": dimension_id,
    }


YEARS_2014_2025 = tuple(str(year) for year in range(2014, 2026))
YEARS_2018_2025 = tuple(str(year) for year in range(2018, 2026))
YEARS_2019_2025 = tuple(str(year) for year in range(2019, 2026))

PROBE_SELECTORS = (
    _selector("P1_OUTCOME", "P1_CONTEXT_ADJUSTED_TRAJECTORY", "education.dropout_rate_percent", stage="medio", periods=["2025"], coverage_scope="RS_497", minimum_municipalities=450, minimum_periods=1),
    _selector("P1_BASELINE", "P1_CONTEXT_ADJUSTED_TRAJECTORY", "education.dropout_rate_percent", stage="medio", periods=["2019"], coverage_scope="RS_497", minimum_municipalities=450, minimum_periods=1),
    _selector("P1_POPULATION", "P1_CONTEXT_ADJUSTED_TRAJECTORY", "demography.population_age_15_17", stage="age_15_17", periods=["2019", "2025"], coverage_scope="RS_497", minimum_municipalities=497, minimum_periods=2),
    _selector("P1_ENROLLMENT", "P1_CONTEXT_ADJUSTED_TRAJECTORY", "education.enrollments", stage="medio", periods=["2019", "2025"], coverage_scope="RS_497", minimum_municipalities=497, minimum_periods=2),
    _selector("P1_ADEQUACY", "P1_CONTEXT_ADJUSTED_TRAJECTORY", "education.teacher_adequacy_percent", stage="medio", periods=["2025"], coverage_scope="RS_497", minimum_municipalities=497, minimum_periods=1),
    _selector("P2_ENROLLMENT", "P2_DEMOGRAPHY_ENROLLMENT_DECOMPOSITION", "education.enrollments", stage="medio", periods=["2018", "2019", "2022", "2025"], coverage_scope="RS_497", minimum_municipalities=497, minimum_periods=4),
    _selector("P2_POPULATION", "P2_DEMOGRAPHY_ENROLLMENT_DECOMPOSITION", "demography.population_age_15_17", stage="age_15_17", periods=["2018", "2019", "2022", "2025"], coverage_scope="RS_497", minimum_municipalities=497, minimum_periods=4),
    _selector("P3_DROPOUT", "P3_SCHOOL_CONDITIONS_AND_TRAJECTORY", "education.dropout_rate_percent", stage="medio", periods=YEARS_2018_2025, coverage_scope="RS_497", minimum_municipalities=450, minimum_periods=8),
    _selector("P3_FAILURE", "P3_SCHOOL_CONDITIONS_AND_TRAJECTORY", "education.failure_rate_percent", stage="medio", periods=YEARS_2018_2025, coverage_scope="RS_497", minimum_municipalities=450, minimum_periods=8),
    _selector("P3_ADEQUACY", "P3_SCHOOL_CONDITIONS_AND_TRAJECTORY", "education.teacher_adequacy_percent", stage="medio", periods=YEARS_2018_2025, coverage_scope="RS_497", minimum_municipalities=497, minimum_periods=8),
    _selector("P4_DROPOUT", "P4_YOUTH_WORK_AND_HIGH_SCHOOL", "education.dropout_rate_percent", stage="medio", periods=YEARS_2019_2025, coverage_scope="RS_497", minimum_municipalities=450, minimum_periods=7),
    _selector("P4_BONDS", "P4_YOUTH_WORK_AND_HIGH_SCHOOL", "labor.youth_rais.active_bonds", stage="age_15_17", periods=YEARS_2019_2025, coverage_scope="VALE_10", minimum_municipalities=10, minimum_periods=7),
    _selector("P4_POPULATION", "P4_YOUTH_WORK_AND_HIGH_SCHOOL", "demography.population_age_15_17", stage="age_15_17", periods=YEARS_2019_2025, coverage_scope="RS_497", minimum_municipalities=497, minimum_periods=7),
    _selector("P5_OCCUPATIONS", "P5_OCCUPATIONS_AND_EPT", "labor.occupation_active_bonds", stage="all_ages", periods=["2025"], coverage_scope="VALE_10", minimum_municipalities=10, minimum_periods=1, dimension_id="ANY_NON_ALL"),
    _selector("P5_EPT", "P5_OCCUPATIONS_AND_EPT", "education.ept_technical_enrollments", stage="professional_technical", periods=["2025"], coverage_scope="VALE_10", minimum_municipalities=10, minimum_periods=1, dimension_id="ANY"),
    _selector("P6_ADULT_SHARE", "P6_ADULT_SCHOOLING_WORK_AND_EJA", "adult.high_school_completion_share_percent", stage="adult_18_or_more", periods=["2022"], coverage_scope="RS_497", minimum_municipalities=497, minimum_periods=1),
    _selector("P6_ADULT_POPULATION", "P6_ADULT_SCHOOLING_WORK_AND_EJA", "adult.population_count", stage="adult_18_or_more", periods=["2022"], coverage_scope="RS_497", minimum_municipalities=497, minimum_periods=1),
    _selector("P6_EJA_FUNDAMENTAL", "P6_ADULT_SCHOOLING_WORK_AND_EJA", "education.eja_enrollments", stage="eja_fundamental", periods=["2022"], coverage_scope="VALE_10", minimum_municipalities=10, minimum_periods=1),
    _selector("P6_EJA_HIGH_SCHOOL", "P6_ADULT_SCHOOLING_WORK_AND_EJA", "education.eja_enrollments", stage="eja_high_school", periods=["2022"], coverage_scope="VALE_10", minimum_municipalities=10, minimum_periods=1),
    _selector("P6_WORK_SCHOOLING", "P6_ADULT_SCHOOLING_WORK_AND_EJA", "labor.youth_rais.schooling_composition_share_percent", stage="age_18_24", periods=["2022"], coverage_scope="VALE_10", minimum_municipalities=10, minimum_periods=1, dimension_id="high_school_incomplete"),
    _selector("P7_RURAL_ENROLLMENTS", "P7_RURALITY_INCLUSION_AND_ACCESS", "education.rural.rural_enrollments", stage="all", periods=YEARS_2014_2025, coverage_scope="VALE_10", minimum_municipalities=10, minimum_periods=12),
    _selector("P7_RURAL_SCHOOLS", "P7_RURALITY_INCLUSION_AND_ACCESS", "education.rural.rural_schools", stage="all", periods=YEARS_2014_2025, coverage_scope="VALE_10", minimum_municipalities=10, minimum_periods=12),
    _selector("P7_AEE_ENROLLMENTS", "P7_RURALITY_INCLUSION_AND_ACCESS", "education.special_aee.special_enrollments", stage="all", periods=YEARS_2014_2025, coverage_scope="VALE_10", minimum_municipalities=10, minimum_periods=12),
    _selector("P7_AEE_SCHOOLS", "P7_RURALITY_INCLUSION_AND_ACCESS", "education.special_aee.schools_offering_aee", stage="all", periods=YEARS_2014_2025, coverage_scope="VALE_10", minimum_municipalities=10, minimum_periods=12),
    _selector("P8_FULL_TIME", "P8_FINANCING_OFFER_AND_CAPACITY", "education.full_time_enrollments", stage="education_basic", periods=["2024", "2025"], coverage_scope="RS_497", minimum_municipalities=497, minimum_periods=2),
    _selector("P8_ENROLLMENTS", "P8_FINANCING_OFFER_AND_CAPACITY", "education.enrollments", stage="education_basic", periods=["2024", "2025"], coverage_scope="RS_497", minimum_municipalities=497, minimum_periods=2),
    _selector("P8_MDE", "P8_FINANCING_OFFER_AND_CAPACITY", "finance.mde_applied_amount", stage="municipal_education_finance", periods=["2024", "2025"], coverage_scope="RS_497", minimum_municipalities=497, minimum_periods=2, dimension_id="empenhado"),
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_bytes(payload: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    temporary.write_bytes(canonical_json_bytes(payload))
    os.replace(temporary, path)


@contextmanager
def blocked_external_io_guard() -> Iterable[None]:
    """Bloqueia rede e SQLite durante cada materialização AA2."""

    original_socket_connect = socket.socket.connect
    original_create_connection = socket.create_connection
    original_sqlite_connect = sqlite3.connect

    def blocked(*_args: Any, **_kwargs: Any) -> Any:
        raise AdvancedAnalysisValidationError(
            "AA2 permite somente entradas locais congeladas; conexão externa bloqueada"
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


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON raiz deve ser objeto: {path}")
    return payload


def _require_hash(path: Path, expected: str) -> None:
    actual = sha256_file(path)
    if actual != expected:
        raise ValueError(f"SHA-256 divergente para {path}: {actual} != {expected}")


def verify_preresult_inputs() -> dict[str, str]:
    _require_hash(PANEL_PATH, EXPECTED_AA1_PANEL_SHA256)
    _require_hash(AA1_GATE_PATH, EXPECTED_AA1_GATE_SHA256)
    _require_hash(BRIDGE_PATH, EXPECTED_BRIDGE_SHA256)
    _require_hash(PREREGISTRATION_PATH, EXPECTED_PREREGISTRATION_SHA256)
    _require_hash(
        PREREGISTRATION_FREEZE_PATH,
        EXPECTED_PREREGISTRATION_FREEZE_SHA256,
    )
    _require_hash(CONTRACT_PATH, EXPECTED_CONTRACT_SHA256)
    _require_hash(PREREG_PROBE_PATH, EXPECTED_PREREG_PROBE_SHA256)
    gate = _load_json(AA1_GATE_PATH)
    manifest = _load_json(AA1_MANIFEST_PATH)
    preregistration = _load_json(PREREGISTRATION_PATH)
    registration = _load_json(PREREGISTRATION_FREEZE_PATH)
    contract = _load_json(CONTRACT_PATH)
    probe = _load_json(PREREG_PROBE_PATH)
    if gate.get("modeAllowedBeforeGatePass") != "PREREGISTRATION_ONLY":
        raise ValueError("Gate AA1 não preserva modo PREREGISTRATION_ONLY.")
    if gate.get("resultInspectionAllowedBeforeGatePass") is not False:
        raise ValueError("Gate AA1 permite inspeção prematura de resultados.")
    if gate.get("panelFile") != PANEL_PATH.name:
        raise ValueError("Gate AA1 não está vinculado ao painel esperado.")
    if manifest.get("artifactSetDigestSha256") != EXPECTED_AA1_ARTIFACT_SET_SHA256:
        raise ValueError("Digest do conjunto AA1 diverge do pré-registro.")
    if preregistration.get("status") != "FROZEN_PRE_RESULT":
        raise AdvancedAnalysisValidationError("Pré-registro AA2 não está congelado.")
    if preregistration.get("firstResultInspected") is not False:
        raise AdvancedAnalysisValidationError(
            "Pré-registro AA2 declara inspeção prematura de resultado."
        )
    if registration.get("state") != "FROZEN_PRE_RESULT":
        raise AdvancedAnalysisValidationError(
            "Registro externo AA2 não está em FROZEN_PRE_RESULT."
        )
    if registration.get("firstResultInspected") is not False:
        raise AdvancedAnalysisValidationError(
            "Registro externo AA2 não preserva o estado pré-resultado."
        )
    registered_preregistration = registration.get("preregistration", {})
    if registered_preregistration.get("sha256") != EXPECTED_PREREGISTRATION_SHA256:
        raise AdvancedAnalysisValidationError(
            "Registro externo não vincula o pré-registro AA2 esperado."
        )
    registered_probe = registration.get("availabilityProbe", {})
    if (
        registered_probe.get("sha256") != EXPECTED_PREREG_PROBE_SHA256
        or registered_probe.get("coefficientOrRawValueInspected") is not False
        or registered_probe.get("failureCount") != 0
    ):
        raise AdvancedAnalysisValidationError(
            "Registro externo não vincula o probe pré-resultado aprovado."
        )
    if (
        probe.get("state") != "FROZEN_PRE_RESULT_PROBE"
        or probe.get("coefficientOrRawValueInspected") is not False
        or probe.get("failureCount") != 0
    ):
        raise AdvancedAnalysisValidationError(
            "Probe AA2 não está em estado pré-resultado aprovado."
        )
    frozen_contract = contract.get("frozenPreregistration", {})
    if (
        frozen_contract.get("sha256") != EXPECTED_PREREGISTRATION_SHA256
        or frozen_contract.get("statusRequired") != "FROZEN_PRE_RESULT"
    ):
        raise AdvancedAnalysisValidationError(
            "Contrato AA2 diverge do pré-registro congelado."
        )
    public_digest = directory_content_digest(REPO_ROOT / "public/data")
    if public_digest != EXPECTED_PUBLIC_DATA_DIGEST:
        raise AdvancedAnalysisValidationError(
            "public/data divergiu antes da primeira leitura analítica AA2."
        )
    return {
        "aa1PanelSha256": EXPECTED_AA1_PANEL_SHA256,
        "aa1GateSha256": EXPECTED_AA1_GATE_SHA256,
        "aa1ArtifactSetDigestSha256": EXPECTED_AA1_ARTIFACT_SET_SHA256,
        "p5AuxiliaryBridgeSha256": EXPECTED_BRIDGE_SHA256,
        "preregistrationSha256": EXPECTED_PREREGISTRATION_SHA256,
        "preregistrationFreezeSha256": EXPECTED_PREREGISTRATION_FREEZE_SHA256,
        "contractSha256": EXPECTED_CONTRACT_SHA256,
        "availabilityProbeSha256": EXPECTED_PREREG_PROBE_SHA256,
        "publicDataTreeDigestSha256": public_digest,
    }


def _filter_selector(frame: pd.DataFrame, selector: Mapping[str, Any]) -> pd.DataFrame:
    subset = frame[
        frame["metric_id"].eq(selector["metricId"])
        & frame["stage_or_population_group"].eq(selector["stage"])
        & frame["year_or_reference_period"].isin(selector["periods"])
        & frame["coverage_scope"].eq(selector["coverageScope"])
    ]
    dimension_id = selector["dimensionId"]
    if dimension_id == "ANY":
        return subset
    if dimension_id == "ANY_NON_ALL":
        return subset[subset["dimension_id"].ne("ALL")]
    return subset[subset["dimension_id"].eq(dimension_id)]


def build_availability_probe() -> dict[str, Any]:
    verified_hashes = verify_preresult_inputs()
    # O probe é um artefato congelado anterior ao registro externo. Mantemos a
    # projeção original de quatro hashes; as novas evidências do gate são
    # verificadas acima, mas não reescrevem retroativamente o probe registrado.
    input_hashes = {
        key: verified_hashes[key]
        for key in (
            "aa1PanelSha256",
            "aa1GateSha256",
            "aa1ArtifactSetDigestSha256",
            "p5AuxiliaryBridgeSha256",
        )
    }
    preregistration = _load_json(PREREGISTRATION_PATH)
    if preregistration.get("firstResultInspected") is not False:
        raise ValueError("Pré-registro não está em estado pré-resultado.")
    frame = pd.read_csv(
        PANEL_PATH,
        usecols=PANEL_METADATA_COLUMNS,
        dtype=str,
        keep_default_na=False,
    )
    selector_rows = []
    for selector in PROBE_SELECTORS:
        subset = _filter_selector(frame, selector)
        municipality_count = int(subset["municipality_ibge_code"].nunique())
        nova_santa_rita_present = bool(
            subset["municipality_ibge_code"].eq("4313375").any()
        )
        period_count = int(subset["year_or_reference_period"].nunique())
        periods_present = sorted(subset["year_or_reference_period"].unique().tolist())
        required_periods = sorted(selector["periods"])
        state = (
            "AVAILABLE"
            if municipality_count >= selector["minimumMunicipalities"]
            and period_count >= selector["minimumPeriods"]
            and periods_present == required_periods
            and nova_santa_rita_present
            else "MISSING_OR_INCOMPLETE"
        )
        network_scopes = sorted(subset["network_scope"].unique().tolist())
        if selector["metricId"].startswith("education.") and network_scopes != [
            "total_all_dependencies"
        ]:
            state = "INVALID_NETWORK_SCOPE"
        selector_rows.append(
            {
                **selector,
                "rowCount": int(len(subset)),
                "municipalityCount": municipality_count,
                "novaSantaRitaPresent": nova_santa_rita_present,
                "periodCount": period_count,
                "periodsPresent": periods_present,
                "availabilityStateCounts": {
                    key: int(value)
                    for key, value in sorted(
                        subset["availability_state"].value_counts().to_dict().items()
                    )
                },
                "unavailabilityReasonCounts": {
                    key: int(value)
                    for key, value in sorted(
                        subset["unavailability_reason"].value_counts().to_dict().items()
                    )
                },
                "networkScopes": network_scopes,
                "territorialLenses": sorted(
                    subset["territorial_lens"].unique().tolist()
                ),
                "probeState": state,
            }
        )

    bridge_columns = pd.read_csv(BRIDGE_PATH, nrows=0).columns.tolist()
    required_bridge_columns = [
        "municipality_ibge_code",
        "school_code",
        "course_code",
        "occupation_subgroup_code",
        "bridge_status",
        "technical_enrollments",
    ]
    bridge_missing = sorted(set(required_bridge_columns) - set(bridge_columns))
    bridge_frame = pd.read_csv(
        BRIDGE_PATH,
        usecols=[
            "municipality_ibge_code",
            "school_code",
            "course_code",
            "occupation_subgroup_code",
            "bridge_status",
        ],
        dtype=str,
        keep_default_na=False,
    )
    bridge_probe = {
        "path": BRIDGE_PATH.relative_to(REPO_ROOT).as_posix(),
        "sha256": EXPECTED_BRIDGE_SHA256,
        "requiredColumns": required_bridge_columns,
        "missingRequiredColumns": bridge_missing,
        "rowCount": int(len(bridge_frame)),
        "municipalityCount": int(
            bridge_frame["municipality_ibge_code"].nunique()
        ),
        "bridgeStatusCounts": {
            key: int(value)
            for key, value in sorted(
                bridge_frame["bridge_status"].value_counts().to_dict().items()
            )
        },
        "probeState": "AVAILABLE" if not bridge_missing else "INVALID_SCHEMA",
    }
    failures = [
        row["selectorId"]
        for row in selector_rows
        if row["probeState"] != "AVAILABLE"
    ]
    if bridge_probe["probeState"] != "AVAILABLE":
        failures.append("P5_AUXILIARY_BRIDGE")
    return {
        "schemaVersion": "vocacoes-pne-aa2-coefficient-free-availability-probe-v1",
        "programId": "vocacoes-pne-advanced-analytics-v1",
        "stage": "AA2_PRE_RESULT",
        "generatedAt": "2026-08-30T00:00:00-03:00",
        "coefficientOrRawValueInspected": False,
        "inputHashes": input_hashes,
        "preregistrationPath": PREREGISTRATION_PATH.relative_to(REPO_ROOT).as_posix(),
        "selectorCount": len(selector_rows),
        "selectors": selector_rows,
        "bridge": bridge_probe,
        "failureCount": len(failures),
        "failures": failures,
        "state": "FROZEN_PRE_RESULT_PROBE" if not failures else "BLOCKED_BEFORE_FREEZE",
    }


def materialize_availability_probe() -> dict[str, Any]:
    payload = build_availability_probe()
    if payload["failureCount"]:
        raise ValueError(f"Probe de disponibilidade falhou: {payload['failures']}")
    atomic_write_json(PREREG_PROBE_PATH, payload)
    return payload


def check_availability_probe() -> dict[str, Any]:
    expected = canonical_json_bytes(build_availability_probe())
    if not PREREG_PROBE_PATH.exists():
        raise FileNotFoundError(PREREG_PROBE_PATH)
    actual = PREREG_PROBE_PATH.read_bytes()
    if actual != expected:
        raise ValueError("Probe de disponibilidade AA2 diverge da recomposição atual.")
    return _load_json(PREREG_PROBE_PATH)


QUESTION_IDS = (
    "P1_CONTEXT_ADJUSTED_TRAJECTORY",
    "P2_DEMOGRAPHY_ENROLLMENT_DECOMPOSITION",
    "P3_SCHOOL_CONDITIONS_AND_TRAJECTORY",
    "P4_YOUTH_WORK_AND_HIGH_SCHOOL",
    "P5_OCCUPATIONS_AND_EPT",
    "P6_ADULT_SCHOOLING_WORK_AND_EJA",
    "P7_RURALITY_INCLUSION_AND_ACCESS",
    "P8_FINANCING_OFFER_AND_CAPACITY",
)

FAMILY_FITS: dict[str, tuple[str, ...]] = {
    "MF_P3_SCHOOL_CONDITIONS": (
        "P3_MAIN_DROPOUT_L0",
        "P3_ALT_FAILURE_L0",
        "P3_ALT_DROPOUT_L1",
        "P3_SENS_EXCLUDE_2020_2021",
        "P3_SENS_WINDOW_2022_2025",
        "P3_PLACEBO_LEAD1",
        "P3_SENS_EXCLUDE_VALE_10",
    ),
    "MF_P4_YOUTH_WORK": (
        "P4_MAIN_L0",
        "P4_ALT_L1",
        "P4_ALT_L2",
        "P4_SENS_EXCLUDE_2020_2021",
        "P4_PLACEBO_LEAD1",
        "P4_REVERSE_DIRECTION",
    ),
    "MF_P6_ADULT_EJA_WORK": (
        "P6_EJA_SPEARMAN",
        "P6_WORK_SPEARMAN",
        "P6_EJA_PEARSON",
        "P6_WORK_PEARSON",
    ),
    "MF_P7_RURALITY_INCLUSION": (
        "P7_RURAL_MAIN",
        "P7_RURAL_EXCLUDE_2020_2021",
        "P7_RURAL_LAG1",
        "P7_AEE_MAIN",
        "P7_AEE_EXCLUDE_2020_2021",
        "P7_AEE_LAG1",
    ),
    "MF_P8_FINANCING_CAPACITY": (
        "P8_MAIN_2025_SIZE_ADJUSTED",
        "P8_ALT_2024_SIZE_ADJUSTED",
        "P8_ALT_2025_PER_ENROLLMENT",
        "P8_SENS_2025_TRIMMED_1_PERCENT",
    ),
}

FAMILY_ALPHA = {
    "MF_P3_SCHOOL_CONDITIONS": 0.05,
    "MF_P4_YOUTH_WORK": 0.10,
    "MF_P6_ADULT_EJA_WORK": 0.10,
    "MF_P7_RURALITY_INCLUSION": 0.10,
    "MF_P8_FINANCING_CAPACITY": 0.05,
}

RESULT_REQUIRED_FIELDS = (
    "question_id",
    "result_id",
    "result_role",
    "method_id",
    "coverage_scope",
    "analytic_municipality_count",
    "analytic_period_count",
    "analytic_sample_n",
    "cluster_count",
    "cluster_count_state",
    "effect_estimate",
    "effect_unit",
    "interval_state",
    "interval_primary_state",
    "interval_lower",
    "interval_upper",
    "p_value_state",
    "p_value_raw",
    "multiplicity_family",
    "multiplicity_family_members",
    "p_value_bh",
    "robustness_state",
    "claim_ceiling",
    "power_statement",
    "minimum_detectable_effect_state",
    "promotion_state",
    "interpretation_guard",
    "terminal_state",
    "numerator_metric_id",
    "numerator_territorial_lens",
    "denominator_metric_id",
    "denominator_territorial_lens",
    "composite_qualifier",
    "availability_reason",
    "source_refs",
)

PANEL_SOURCE_REF = (
    ".tmp/vocacoes-pne/advanced-analytics-v1/aa1/"
    "PAINEL_ANALITICO_ESTADUAL_AA1.csv.gz"
)
BRIDGE_SOURCE_REF = ".tmp/vocacoes-pne/v7-job2/2d/cursos_cbo_2025.csv.gz"
POPULATION_SOURCE_PROVENANCE = {
    "metricId": "demography.population_age_15_17",
    "upstreamTable": "public.populacao_idade",
    "upstreamValueField": "pop_estimada",
    "upstreamAttribution": "IBGE/DATASUS conforme o pipeline local documentado",
    "localSnapshot": (
        ".tmp/vocacoes-pne/v7-job5l/sources/database/"
        "population_context.csv.gz#population_15_17"
    ),
    "localSnapshotSha256": (
        "8188b99061e0fb8ef220c2a295b9d0ef2903009091d8bc937c83976e1aadcc92"
    ),
    "coverage": "2018-2025; 497 municípios do RS em cada ano",
    "vintageState": "UNRESOLVED_IN_FROZEN_LOCAL_SNAPSHOT",
    "rebaseSensitivityState": "NOT_IDENTIFIABLE_FROM_FROZEN_LOCAL_METADATA",
}


def _finite_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _safe_positive_denominator_ratio(
    numerator: pd.Series,
    denominator: pd.Series,
    *,
    multiplier: float = 1.0,
) -> pd.Series:
    """Preserva zero observado e converte denominador não positivo em indisponível."""

    numeric_numerator = pd.to_numeric(numerator, errors="coerce")
    numeric_denominator = pd.to_numeric(denominator, errors="coerce")
    valid = numeric_denominator.gt(0) & numeric_numerator.notna()
    result = pd.Series(np.nan, index=numerator.index, dtype=float)
    result.loc[valid] = (
        multiplier
        * numeric_numerator.loc[valid]
        / numeric_denominator.loc[valid]
    )
    return result


def _json_cell(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _normal_two_sided_p(statistic: float) -> float:
    return math.erfc(abs(statistic) / math.sqrt(2.0))


def _vale_codes() -> tuple[str, ...]:
    payload = _load_json(REGIONS_PATH)
    matching = [
        region
        for region in payload.get("regions", [])
        if region.get("slug") == "vale-do-sinos"
    ]
    if len(matching) != 1:
        raise AdvancedAnalysisValidationError(
            "Configuração regional do Vale do Sinos ausente ou ambígua."
        )
    codes = tuple(sorted(str(code) for code in matching[0]["municipalityIbgeCodes"]))
    if len(codes) != 10 or NOVA_SANTA_RITA_CODE not in codes:
        raise AdvancedAnalysisValidationError(
            "Recorte canônico do Vale do Sinos não contém os dez municípios esperados."
        )
    if any(len(code) != 7 or not code.isdigit() for code in codes):
        raise AdvancedAnalysisValidationError("Código IBGE regional inválido.")
    return codes


def load_registered_panel_values() -> tuple[pd.DataFrame, dict[str, str]]:
    """Primeiro ponto autorizado a ler ``raw_value`` após o gate congelado."""

    input_hashes = verify_preresult_inputs()
    check_availability_probe()
    frame = pd.read_csv(
        PANEL_PATH,
        dtype=str,
        keep_default_na=False,
    )
    required = set(PANEL_METADATA_COLUMNS) | {
        "raw_value",
        "source_ref",
        "unit",
        "municipality_name",
    }
    missing = sorted(required - set(frame.columns))
    if missing:
        raise AdvancedAnalysisValidationError(
            f"Painel AA1 sem colunas requeridas pelo AA2: {missing}"
        )
    codes = frame["municipality_ibge_code"]
    if not codes.map(lambda value: len(value) == 7 and value.isdigit()).all():
        raise AdvancedAnalysisValidationError(
            "Identidade municipal deixou de ser código IBGE textual de sete dígitos."
        )
    observed = frame["availability_state"].isin(["observed", "observed_zero"])
    numeric = pd.to_numeric(frame["raw_value"], errors="coerce")
    if numeric[observed].isna().any():
        raise AdvancedAnalysisValidationError(
            "Valor observado/zero observado sem raw_value numérico no AA1."
        )
    frame["value"] = numeric
    return frame, input_hashes


def _metric_rows(
    frame: pd.DataFrame,
    metric_id: str,
    *,
    stage: str,
    periods: Sequence[str] | None = None,
    coverage_scope: str,
    dimension_id: str = "ALL",
) -> pd.DataFrame:
    subset = frame[
        frame["metric_id"].eq(metric_id)
        & frame["stage_or_population_group"].eq(stage)
        & frame["coverage_scope"].eq(coverage_scope)
    ].copy()
    if periods is not None:
        subset = subset[subset["year_or_reference_period"].isin(periods)]
    if dimension_id != "ANY":
        subset = subset[subset["dimension_id"].eq(dimension_id)]
    subset["analysis_value"] = subset["value"].where(
        subset["availability_state"].isin(["observed", "observed_zero"])
    )
    return subset


def _metric_wide(
    frame: pd.DataFrame,
    metric_id: str,
    *,
    stage: str,
    periods: Sequence[str],
    coverage_scope: str,
    dimension_id: str = "ALL",
    prefix: str,
) -> pd.DataFrame:
    subset = _metric_rows(
        frame,
        metric_id,
        stage=stage,
        periods=periods,
        coverage_scope=coverage_scope,
        dimension_id=dimension_id,
    )
    key = ["municipality_ibge_code", "year_or_reference_period"]
    if subset.duplicated(key).any():
        raise AdvancedAnalysisValidationError(
            f"Grão duplicado para {metric_id}/{stage}/{dimension_id}."
        )
    wide = subset.pivot(
        index="municipality_ibge_code",
        columns="year_or_reference_period",
        values="analysis_value",
    )
    wide = wide.rename(columns={period: f"{prefix}_{period}" for period in periods})
    return wide.reset_index()


def _metric_panel_column(
    frame: pd.DataFrame,
    metric_id: str,
    *,
    stage: str,
    periods: Sequence[str],
    coverage_scope: str,
    column: str,
    dimension_id: str = "ALL",
) -> pd.DataFrame:
    subset = _metric_rows(
        frame,
        metric_id,
        stage=stage,
        periods=periods,
        coverage_scope=coverage_scope,
        dimension_id=dimension_id,
    )
    key = ["municipality_ibge_code", "year_or_reference_period"]
    if subset.duplicated(key).any():
        raise AdvancedAnalysisValidationError(f"Grão duplicado para {metric_id}.")
    return subset[key + ["analysis_value"]].rename(columns={"analysis_value": column})


def _result_row(
    *,
    question_id: str,
    result_id: str,
    result_role: str,
    method_id: str,
    coverage_scope: str,
    municipality_count: int,
    period_count: int,
    effect: float | None,
    effect_unit: str,
    interval_state: str,
    interval_lower: float | None,
    interval_upper: float | None,
    p_value_state: str,
    p_value_raw: float | None,
    multiplicity_family: str | None,
    robustness_state: str,
    claim_ceiling: str,
    numerator_metric_id: str,
    numerator_lens: str,
    denominator_metric_id: str = "",
    denominator_lens: str = "",
    composite_qualifier: str = "",
    availability_reason: str = "",
    source_refs: Sequence[str] = (PANEL_SOURCE_REF,),
    **diagnostics: Any,
) -> dict[str, Any]:
    row = {
        "question_id": question_id,
        "result_id": result_id,
        "result_role": result_role,
        "method_id": method_id,
        "coverage_scope": coverage_scope,
        "analytic_municipality_count": municipality_count,
        "analytic_period_count": period_count,
        "effect_estimate": _finite_or_none(effect),
        "effect_unit": effect_unit,
        "interval_state": interval_state,
        "interval_lower": _finite_or_none(interval_lower),
        "interval_upper": _finite_or_none(interval_upper),
        "p_value_state": p_value_state,
        "p_value_raw": _finite_or_none(p_value_raw),
        "multiplicity_family": multiplicity_family or "",
        "p_value_bh": None,
        "robustness_state": robustness_state,
        "claim_ceiling": claim_ceiling,
        "terminal_state": "PENDING_TERMINAL_RULE",
        "numerator_metric_id": numerator_metric_id,
        "numerator_territorial_lens": numerator_lens,
        "denominator_metric_id": denominator_metric_id,
        "denominator_territorial_lens": denominator_lens,
        "composite_qualifier": composite_qualifier,
        "availability_reason": availability_reason,
        "source_refs": _json_cell(list(source_refs)),
    }
    row.update(diagnostics)
    return row


def _insufficient_result(
    *,
    question_id: str,
    result_id: str,
    method_id: str,
    coverage_scope: str,
    claim_ceiling: str,
    family: str | None,
    reason: str,
    numerator_metric_id: str,
    numerator_lens: str,
    denominator_metric_id: str = "",
    denominator_lens: str = "",
    composite_qualifier: str = "",
) -> dict[str, Any]:
    return _result_row(
        question_id=question_id,
        result_id=result_id,
        result_role="PREDECLARED_FIT",
        method_id=method_id,
        coverage_scope=coverage_scope,
        municipality_count=0,
        period_count=0,
        effect=None,
        effect_unit="unavailable",
        interval_state="UNAVAILABLE",
        interval_lower=None,
        interval_upper=None,
        p_value_state="INSUFFICIENT_DATA" if family else "NOT_APPLICABLE_PREDECLARED",
        p_value_raw=None,
        multiplicity_family=family,
        robustness_state="INSUFFICIENT_DATA",
        claim_ceiling=claim_ceiling,
        numerator_metric_id=numerator_metric_id,
        numerator_lens=numerator_lens,
        denominator_metric_id=denominator_metric_id,
        denominator_lens=denominator_lens,
        composite_qualifier=composite_qualifier,
        availability_reason=reason,
    )


def bh_adjust_fixed_family(
    ordered_fit_ids: Sequence[str],
    p_values_by_fit: Mapping[str, float | None],
) -> dict[str, float | None]:
    """BH com denominador fixo; fit inválido ocupa o slot com p=1 internamente."""

    if set(p_values_by_fit) - set(ordered_fit_ids):
        raise AdvancedAnalysisValidationError("Fit não pré-registrado entrou na família BH.")
    padded = [
        1.0 if p_values_by_fit.get(fit_id) is None else float(p_values_by_fit[fit_id])
        for fit_id in ordered_fit_ids
    ]
    if any(value < 0 or value > 1 for value in padded):
        raise AdvancedAnalysisValidationError("p-valor fora do intervalo [0,1].")
    ordered = sorted(enumerate(padded), key=lambda item: (item[1], item[0]))
    adjusted_sorted = [1.0] * len(ordered)
    running = 1.0
    m = len(ordered_fit_ids)
    for position in range(m - 1, -1, -1):
        _, p_value = ordered[position]
        running = min(running, min(1.0, p_value * m / (position + 1)))
        adjusted_sorted[position] = running
    adjusted_by_index = [1.0] * m
    for (original_index, _), adjusted in zip(
        ordered, adjusted_sorted, strict=True
    ):
        adjusted_by_index[original_index] = adjusted
    return {
        fit_id: (
            None
            if p_values_by_fit.get(fit_id) is None
            else adjusted_by_index[index]
        )
        for index, fit_id in enumerate(ordered_fit_ids)
    }


def _clustered_fit_arrays(
    y: np.ndarray,
    x: np.ndarray,
    groups: np.ndarray,
) -> dict[str, Any]:
    design = np.asarray(x, dtype=float)
    outcome = np.asarray(y, dtype=float)
    if design.ndim == 1:
        design = design[:, None]
    xtx = design.T @ design
    if np.linalg.matrix_rank(xtx) < xtx.shape[0]:
        raise AdvancedAnalysisValidationError("Matriz singular no ajuste em painel.")
    inverse = np.linalg.inv(xtx)
    coefficients = inverse @ (design.T @ outcome)
    residuals = outcome - design @ coefficients
    meat = np.zeros_like(xtx)
    unique_groups = np.unique(groups)
    for group in unique_groups:
        mask = groups == group
        score = design[mask].T @ residuals[mask]
        meat += np.outer(score, score)
    n = len(outcome)
    k = design.shape[1]
    g = len(unique_groups)
    if g <= 1 or n <= k:
        raise AdvancedAnalysisValidationError("Graus de liberdade insuficientes.")
    correction = g / (g - 1) * (n - 1) / (n - k)
    covariance = correction * inverse @ meat @ inverse
    standard_errors = np.sqrt(np.maximum(np.diag(covariance), 0.0))
    if standard_errors[0] <= 0:
        raise AdvancedAnalysisValidationError("Erro-padrão degenerado.")
    return {
        "coefficient": float(coefficients[0]),
        "standard_error": float(standard_errors[0]),
        "statistic": float(coefficients[0] / standard_errors[0]),
        "residuals": residuals,
    }


def fit_fixed_effect_panel(
    frame: pd.DataFrame,
    *,
    outcome: str,
    exposure: str,
    exact_cluster_sign_p: bool,
) -> dict[str, Any]:
    sample = frame[
        ["municipality_ibge_code", "year_or_reference_period", outcome, exposure]
    ].copy()
    sample[outcome] = pd.to_numeric(sample[outcome], errors="coerce")
    sample[exposure] = pd.to_numeric(sample[exposure], errors="coerce")
    sample = sample.dropna().sort_values(
        ["municipality_ibge_code", "year_or_reference_period"]
    )
    municipalities = sample["municipality_ibge_code"].to_numpy(dtype=str)
    years = sample["year_or_reference_period"].to_numpy(dtype=str)
    joined = sample[[outcome, exposure]].to_numpy(dtype=float)
    transformed, iterations = two_way_within(joined, municipalities, years)
    y_within = transformed[:, 0]
    x_within = transformed[:, 1]
    within_variance = float(np.var(x_within))
    if within_variance <= 1e-12:
        raise AdvancedAnalysisValidationError("Variância within da exposição insuficiente.")
    fit = _clustered_fit_arrays(y_within, x_within, municipalities)
    outcome_sd = float(np.std(y_within, ddof=0))
    exposure_sd = float(np.std(x_within, ddof=0))
    standardized = (
        fit["coefficient"] * exposure_sd / outcome_sd if outcome_sd > 0 else None
    )
    p_value = _normal_two_sided_p(fit["statistic"])
    resampling: dict[str, Any] = {
        "method": "clustered_normal_approximation",
        "clusterCount": int(sample["municipality_ibge_code"].nunique()),
    }
    if exact_cluster_sign_p:
        groups = sorted(sample["municipality_ibge_code"].unique().tolist())
        g = len(groups)
        if g not in {9, 10}:
            raise AdvancedAnalysisValidationError(
                "Enumeração exata exige exatamente nove ou dez clusters."
            )
        observed_abs = abs(fit["statistic"])
        extreme = 0
        denominator = 2**g
        for signs in itertools.product((-1.0, 1.0), repeat=g):
            sign_by_group = dict(zip(groups, signs, strict=True))
            signed_y = y_within * np.array(
                [sign_by_group[group] for group in municipalities], dtype=float
            )
            signed_y_within, _ = two_way_within(
                signed_y, municipalities, years
            )
            signed_fit = _clustered_fit_arrays(
                signed_y_within[:, 0], x_within, municipalities
            )
            if abs(signed_fit["statistic"]) + 1e-15 >= observed_abs:
                extreme += 1
        p_value = extreme / denominator
        resampling = {
            "method": "exhaustive_Rademacher_cluster_sign_studentized_t",
            "clusterCount": g,
            "denominator": denominator,
            "extremeCount": extreme,
            "minimumPValue": 1 / denominator,
        }
    return {
        **fit,
        "p_value": p_value,
        "interval_lower": fit["coefficient"] - 1.96 * fit["standard_error"],
        "interval_upper": fit["coefficient"] + 1.96 * fit["standard_error"],
        "standardized_effect": standardized,
        "municipality_count": int(sample["municipality_ibge_code"].nunique()),
        "period_count": int(sample["year_or_reference_period"].nunique()),
        "observation_count": int(len(sample)),
        "within_iterations": iterations,
        "within_exposure_variance": within_variance,
        "resampling": resampling,
    }


def fit_ols_hc3(
    frame: pd.DataFrame,
    *,
    outcome: str,
    exposure: str,
    controls: Sequence[str] = (),
) -> dict[str, Any]:
    columns = [outcome, exposure, *controls]
    sample = frame[["municipality_ibge_code", *columns]].copy()
    for column in columns:
        sample[column] = pd.to_numeric(sample[column], errors="coerce")
    sample = sample.dropna().sort_values("municipality_ibge_code")
    y = sample[outcome].to_numpy(dtype=float)
    x = np.column_stack(
        [
            np.ones(len(sample)),
            sample[exposure].to_numpy(dtype=float),
            *[sample[column].to_numpy(dtype=float) for column in controls],
        ]
    )
    if len(sample) <= x.shape[1] or np.linalg.matrix_rank(x) < x.shape[1]:
        raise AdvancedAnalysisValidationError("Ajuste HC3 singular ou insuficiente.")
    inverse = np.linalg.inv(x.T @ x)
    coefficients = inverse @ (x.T @ y)
    residuals = y - x @ coefficients
    leverages = np.einsum("ij,jk,ik->i", x, inverse, x)
    if np.any(leverages >= 1 - 1e-12):
        raise AdvancedAnalysisValidationError("Alavancagem unitária no ajuste HC3.")
    scaled = residuals / (1 - leverages)
    meat = x.T @ ((scaled**2)[:, None] * x)
    covariance = inverse @ meat @ inverse
    standard_errors = np.sqrt(np.maximum(np.diag(covariance), 0.0))
    if standard_errors[1] <= 0:
        raise AdvancedAnalysisValidationError("Erro-padrão HC3 degenerado.")
    statistic = float(coefficients[1] / standard_errors[1])
    return {
        "coefficient": float(coefficients[1]),
        "standard_error": float(standard_errors[1]),
        "p_value": _normal_two_sided_p(statistic),
        "interval_lower": float(coefficients[1] - 1.96 * standard_errors[1]),
        "interval_upper": float(coefficients[1] + 1.96 * standard_errors[1]),
        "municipality_count": int(len(sample)),
        "period_count": 1,
        "observation_count": int(len(sample)),
        "coefficients": [float(value) for value in coefficients],
        "residuals_by_municipality": {
            code: float(residual)
            for code, residual in zip(
                sample["municipality_ibge_code"], residuals, strict=True
            )
        },
    }


def _correlation(x: np.ndarray, y: np.ndarray, *, method: str) -> float:
    left = np.asarray(x, dtype=float)
    right = np.asarray(y, dtype=float)
    if method == "spearman":
        left = pd.Series(left).rank(method="average").to_numpy(dtype=float)
        right = pd.Series(right).rank(method="average").to_numpy(dtype=float)
    if np.std(left) <= 0 or np.std(right) <= 0:
        raise AdvancedAnalysisValidationError("Correlação com variável degenerada.")
    return float(np.corrcoef(left, right)[0, 1])


def permutation_correlation(
    x: np.ndarray,
    y: np.ndarray,
    *,
    method: str,
    seed: int,
    permutations: int = 99_999,
) -> tuple[float, float, int]:
    left = np.asarray(x, dtype=float)
    right = np.asarray(y, dtype=float)
    if method == "spearman":
        left = pd.Series(left).rank(method="average").to_numpy(dtype=float)
        right = pd.Series(right).rank(method="average").to_numpy(dtype=float)
    left = left - left.mean()
    right = right - right.mean()
    denominator = float(np.sqrt(np.dot(left, left) * np.dot(right, right)))
    if denominator <= 0:
        raise AdvancedAnalysisValidationError("Correlação com variável degenerada.")
    observed = float(np.dot(left, right) / denominator)
    generator = np.random.Generator(np.random.PCG64(seed))
    extreme = 0
    for _ in range(permutations):
        permuted = generator.permutation(right)
        statistic = float(np.dot(left, permuted) / denominator)
        if abs(statistic) + 1e-15 >= abs(observed):
            extreme += 1
    return observed, (extreme + 1) / (permutations + 1), extreme


def bootstrap_correlation_interval(
    x: np.ndarray,
    y: np.ndarray,
    *,
    method: str,
    seed: int,
    resamples: int = 10_000,
) -> tuple[float, float, int]:
    generator = np.random.Generator(np.random.PCG64(seed))
    values: list[float] = []
    size = len(x)
    for _ in range(resamples):
        indices = generator.integers(0, size, size=size)
        try:
            values.append(_correlation(x[indices], y[indices], method=method))
        except AdvancedAnalysisValidationError:
            continue
    if len(values) < int(0.8 * resamples):
        raise AdvancedAnalysisValidationError(
            "Menos de 80% dos reamostramentos bootstrap foram válidos."
        )
    lower, upper = np.quantile(np.asarray(values), [0.025, 0.975])
    return float(lower), float(upper), len(values)


def _fold_number(code: str, fold_count: int) -> int:
    digest = hashlib.sha256(code.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], byteorder="big", signed=False) % fold_count


def _oof_prediction(
    sample: pd.DataFrame,
    *,
    outcome: str,
    features: Sequence[str],
    fold_count: int,
) -> np.ndarray:
    predictions = np.full(len(sample), np.nan, dtype=float)
    folds = np.array(
        [_fold_number(code, fold_count) for code in sample["municipality_ibge_code"]],
        dtype=int,
    )
    for fold in range(fold_count):
        test_mask = folds == fold
        train_mask = ~test_mask
        if not test_mask.any():
            raise AdvancedAnalysisValidationError(
                f"Fold determinístico vazio no ajuste de {fold_count} folds."
            )
        x_train = np.column_stack(
            [
                np.ones(int(train_mask.sum())),
                sample.loc[train_mask, list(features)].to_numpy(dtype=float),
            ]
        )
        if np.linalg.matrix_rank(x_train) < x_train.shape[1]:
            raise AdvancedAnalysisValidationError(
                f"Matriz de treino singular no fold {fold}/{fold_count}."
            )
        coefficients = np.linalg.lstsq(
            x_train,
            sample.loc[train_mask, outcome].to_numpy(dtype=float),
            rcond=None,
        )[0]
        x_test = np.column_stack(
            [
                np.ones(int(test_mask.sum())),
                sample.loc[test_mask, list(features)].to_numpy(dtype=float),
            ]
        )
        predictions[test_mask] = x_test @ coefficients
    if not np.isfinite(predictions).all():
        raise AdvancedAnalysisValidationError("Predição fora da amostra não finita.")
    return predictions


def _prediction_fit(
    sample: pd.DataFrame,
    *,
    features: Sequence[str],
    fold_count: int,
) -> dict[str, Any]:
    predictions = _oof_prediction(
        sample,
        outcome="dropout_2025",
        features=features,
        fold_count=fold_count,
    )
    observed = sample["dropout_2025"].to_numpy(dtype=float)
    residuals = observed - predictions
    calibration_mask = sample["municipality_ibge_code"].ne(
        NOVA_SANTA_RITA_CODE
    ).to_numpy()
    absolute_calibration = np.abs(residuals[calibration_mask])
    conformal_bound = float(
        np.quantile(absolute_calibration, 0.95, method="higher")
    )
    coverage = float(
        np.mean(absolute_calibration <= conformal_bound + 1e-15)
    )
    rmse = float(np.sqrt(np.mean(residuals**2)))
    nsr_index = int(
        np.flatnonzero(
            sample["municipality_ibge_code"].eq(NOVA_SANTA_RITA_CODE).to_numpy()
        )[0]
    )
    return {
        "predictions": predictions,
        "residuals": residuals,
        "conformal_bound": conformal_bound,
        "coverage": coverage,
        "rmse": rmse,
        "nsr_effect": float(residuals[nsr_index]),
        "nsr_prediction": float(predictions[nsr_index]),
        "nsr_observed": float(observed[nsr_index]),
        "fold_count": fold_count,
    }


def analyze_p1(frame: pd.DataFrame) -> dict[str, Any]:
    question_id = "P1_CONTEXT_ADJUSTED_TRAJECTORY"
    parts = [
        _metric_wide(
            frame,
            "education.dropout_rate_percent",
            stage="medio",
            periods=["2019", "2025"],
            coverage_scope="RS_497",
            prefix="dropout",
        ),
        _metric_wide(
            frame,
            "demography.population_age_15_17",
            stage="age_15_17",
            periods=["2019", "2025"],
            coverage_scope="RS_497",
            prefix="population",
        ),
        _metric_wide(
            frame,
            "education.enrollments",
            stage="medio",
            periods=["2019", "2025"],
            coverage_scope="RS_497",
            prefix="enrollment",
        ),
        _metric_wide(
            frame,
            "education.teacher_adequacy_percent",
            stage="medio",
            periods=["2025"],
            coverage_scope="RS_497",
            prefix="adequacy",
        ),
    ]
    sample = parts[0]
    for part in parts[1:]:
        sample = sample.merge(part, on="municipality_ibge_code", how="inner")
    sample["population_change"] = np.log1p(sample["population_2025"]) - np.log1p(
        sample["population_2019"]
    )
    sample["enrollment_change"] = np.log1p(sample["enrollment_2025"]) - np.log1p(
        sample["enrollment_2019"]
    )
    sample = sample.dropna().sort_values("municipality_ibge_code").reset_index(drop=True)
    full_features = (
        "dropout_2019",
        "population_change",
        "enrollment_change",
        "adequacy_2025",
    )
    baseline_features = (
        "dropout_2019",
        "population_change",
        "enrollment_change",
    )
    valid = len(sample) >= 450 and sample["municipality_ibge_code"].eq(
        NOVA_SANTA_RITA_CODE
    ).any()
    results: list[dict[str, Any]] = []
    robustness: list[dict[str, Any]] = []
    heterogeneity: list[dict[str, Any]] = []
    scope_rows: list[dict[str, Any]] = []
    fits: dict[str, dict[str, Any]] = {}
    if valid:
        try:
            fits = {
                "P1_MAIN_5F_FULL": _prediction_fit(
                    sample, features=full_features, fold_count=5
                ),
                "P1_ALT_10F_FULL": _prediction_fit(
                    sample, features=full_features, fold_count=10
                ),
                "P1_ALT_5F_BASELINE_ONLY": _prediction_fit(
                    sample, features=baseline_features, fold_count=5
                ),
            }
        except (AdvancedAnalysisValidationError, np.linalg.LinAlgError) as error:
            valid = False
            failure_reason = str(error)
    else:
        failure_reason = "fewer_than_450_complete_municipalities_or_nsr_missing"
    if not valid:
        results.append(
            _insufficient_result(
                question_id=question_id,
                result_id="P1_MAIN_5F_FULL",
                method_id="DETERMINISTIC_OOF_OLS_CONFORMAL",
                coverage_scope="RS_497",
                claim_ceiling="CONTEXT_ADJUSTED_COMPARISON",
                family=None,
                reason=failure_reason,
                numerator_metric_id="education.dropout_rate_percent",
                numerator_lens="school_location",
            )
        )
        terminal = "INSUFFICIENT_DATA"
        interpretation = "WITHIN_OR_INCONCLUSIVE_CONTEXT"
    else:
        main = fits["P1_MAIN_5F_FULL"]
        baseline = fits["P1_ALT_5F_BASELINE_ONLY"]
        calibration_pass = (
            0.92 <= main["coverage"] <= 0.98
            and main["rmse"] <= 1.05 * baseline["rmse"]
        )
        terminal = (
            "CONTEXT_COMPARISON_COMPLETE" if calibration_pass else "INSUFFICIENT_DATA"
        )
        effects = [fit["nsr_effect"] for fit in fits.values()]
        interpretation = "WITHIN_OR_INCONCLUSIVE_CONTEXT"
        if main["nsr_effect"] > main["conformal_bound"] and all(
            effect > 0 for effect in effects
        ):
            interpretation = "ABOVE_CONTEXT"
        elif main["nsr_effect"] < -main["conformal_bound"] and all(
            effect < 0 for effect in effects
        ):
            interpretation = "BELOW_CONTEXT"
        for fit_id, fit in fits.items():
            role = "PRIMARY" if fit_id == "P1_MAIN_5F_FULL" else "ALTERNATIVE"
            results.append(
                _result_row(
                    question_id=question_id,
                    result_id=fit_id,
                    result_role=role,
                    method_id="DETERMINISTIC_OOF_OLS_CONFORMAL",
                    coverage_scope="RS_497",
                    municipality_count=len(sample),
                    period_count=2,
                    effect=fit["nsr_effect"],
                    effect_unit="percentage_points_observed_minus_held_out_predicted",
                    interval_state="PREDICTION_BAND",
                    interval_lower=-fit["conformal_bound"],
                    interval_upper=fit["conformal_bound"],
                    p_value_state="NOT_APPLICABLE_PREDECLARED",
                    p_value_raw=None,
                    multiplicity_family=None,
                    robustness_state=(
                        "CALIBRATED" if calibration_pass else "CALIBRATION_FAILED"
                    ),
                    claim_ceiling="CONTEXT_ADJUSTED_COMPARISON",
                    numerator_metric_id="education.dropout_rate_percent",
                    numerator_lens="school_location",
                    held_out_rmse=fit["rmse"],
                    empirical_interval_coverage=fit["coverage"],
                    nsr_observed=fit["nsr_observed"],
                    nsr_predicted=fit["nsr_prediction"],
                    fold_count=fit["fold_count"],
                    signed_log_ratio_formula="log1p(end)-log1p(start)",
                )
            )
            robustness.append(
                {
                    "question_id": question_id,
                    "robustness_id": fit_id,
                    "state": "VALID",
                    "value": fit["nsr_effect"],
                    "unit": "percentage_points",
                    "detail": _json_cell(
                        {
                            "foldCount": fit["fold_count"],
                            "rmse": fit["rmse"],
                            "coverage": fit["coverage"],
                            "conformalBound": fit["conformal_bound"],
                        }
                    ),
                }
            )
        main_residuals = main["residuals"]
        vale = set(_vale_codes())
        for code, residual in zip(
            sample["municipality_ibge_code"], main_residuals, strict=True
        ):
            heterogeneity.append(
                {
                    "question_id": question_id,
                    "heterogeneity_id": "P1_HELD_OUT_RESIDUAL",
                    "municipality_ibge_code": code,
                    "scope_id": "VALE_10" if code in vale else "RS_NON_VALE",
                    "value": float(residual),
                    "unit": "percentage_points",
                    "state": "OBSERVED",
                }
            )
        residual_by_code = dict(
            zip(sample["municipality_ibge_code"], main_residuals, strict=True)
        )
        for scope_id, codes in (
            ("RS_497", sample["municipality_ibge_code"].tolist()),
            ("VALE_10", list(_vale_codes())),
            ("MUNICIPALITY_4313375", [NOVA_SANTA_RITA_CODE]),
        ):
            values = [residual_by_code[code] for code in codes if code in residual_by_code]
            scope_rows.append(
                {
                    "question_id": question_id,
                    "measure_id": "HELD_OUT_DROPOUT_RESIDUAL_MEDIAN",
                    "scope_id": scope_id,
                    "scope_state": "AVAILABLE" if values else "UNAVAILABLE",
                    "value": float(np.median(values)) if values else None,
                    "unit": "percentage_points",
                    "municipality_count": len(values),
                    "coverage_scope": "RS_497",
                    "unavailability_reason": "" if values else "NO_COMPLETE_CASES",
                }
            )
    for row in results:
        row["terminal_state"] = terminal
    return {
        "results": results,
        "robustness": robustness,
        "heterogeneity": heterogeneity,
        "scope": scope_rows,
        "terminal": terminal,
        "claim_ceiling": "CONTEXT_ADJUSTED_COMPARISON",
        "claim_detail": {
            "interpretation": interpretation,
            "completeMunicipalityCount": int(len(sample)),
            "calibration": {
                key: {
                    "rmse": value["rmse"],
                    "coverage": value["coverage"],
                    "conformalBound": value["conformal_bound"],
                }
                for key, value in fits.items()
            },
        },
    }


def _decompose_enrollment_change(
    enrollment_start: float,
    enrollment_end: float,
    population_start: float,
    population_end: float,
) -> dict[str, float]:
    if population_start <= 0 or population_end <= 0:
        raise AdvancedAnalysisValidationError(
            "População de referência não positiva na decomposição."
        )
    relationship_start = enrollment_start / population_start
    relationship_end = enrollment_end / population_end
    population_component = (
        0.5
        * (relationship_start + relationship_end)
        * (population_end - population_start)
    )
    relationship_component = (
        0.5
        * (population_start + population_end)
        * (relationship_end - relationship_start)
    )
    total_change = enrollment_end - enrollment_start
    residual = total_change - population_component - relationship_component
    tolerance = 1e-9 * max(1.0, abs(total_change))
    return {
        "population_component": float(population_component),
        "relationship_component": float(relationship_component),
        "total_change": float(total_change),
        "closure_residual": float(residual),
        "closure_tolerance": float(tolerance),
        "relationship_start": float(relationship_start),
        "relationship_end": float(relationship_end),
    }


def analyze_p2(frame: pd.DataFrame) -> dict[str, Any]:
    question_id = "P2_DEMOGRAPHY_ENROLLMENT_DECOMPOSITION"
    periods = ["2018", "2019", "2022", "2025"]
    enrollment = _metric_wide(
        frame,
        "education.enrollments",
        stage="medio",
        periods=periods,
        coverage_scope="RS_497",
        prefix="enrollment",
    )
    population = _metric_wide(
        frame,
        "demography.population_age_15_17",
        stage="age_15_17",
        periods=periods,
        coverage_scope="RS_497",
        prefix="population",
    )
    sample = enrollment.merge(population, on="municipality_ibge_code", how="inner")
    windows = (("2018", "2025"), ("2019", "2025"), ("2022", "2025"))
    scope_map = {
        "RS_497": sorted(sample["municipality_ibge_code"].tolist()),
        "VALE_10": list(_vale_codes()),
        "MUNICIPALITY_4313375": [NOVA_SANTA_RITA_CODE],
    }
    results: list[dict[str, Any]] = []
    robustness: list[dict[str, Any]] = []
    heterogeneity: list[dict[str, Any]] = []
    scope_rows: list[dict[str, Any]] = []
    valid = True
    main_components: dict[str, dict[str, float]] = {}
    for start, end in windows:
        required = [
            f"enrollment_{start}",
            f"enrollment_{end}",
            f"population_{start}",
            f"population_{end}",
        ]
        complete = sample.dropna(subset=required)
        for scope_id, codes in scope_map.items():
            scoped = complete[complete["municipality_ibge_code"].isin(codes)]
            expected_count = len(codes)
            try:
                if len(scoped) != expected_count:
                    raise AdvancedAnalysisValidationError(
                        f"endpoint_missing_for_{scope_id}_{start}_{end}"
                    )
                decomposition = _decompose_enrollment_change(
                    float(scoped[f"enrollment_{start}"].sum()),
                    float(scoped[f"enrollment_{end}"].sum()),
                    float(scoped[f"population_{start}"].sum()),
                    float(scoped[f"population_{end}"].sum()),
                )
                if abs(decomposition["closure_residual"]) > decomposition[
                    "closure_tolerance"
                ]:
                    raise AdvancedAnalysisValidationError(
                        f"closure_failed_for_{scope_id}_{start}_{end}"
                    )
            except AdvancedAnalysisValidationError:
                valid = False
                continue
            if (start, end) == ("2018", "2025"):
                main_components[scope_id] = decomposition
            for component_id, component_key in (
                ("POPULATION_COMPONENT", "population_component"),
                ("TERRITORIAL_RELATION_COMPONENT", "relationship_component"),
            ):
                effect = decomposition[component_key]
                results.append(
                    _result_row(
                        question_id=question_id,
                        result_id=f"P2_{start}_{end}_{scope_id}_{component_id}",
                        result_role=(
                            "PRIMARY_COMPONENT"
                            if (start, end) == ("2018", "2025")
                            else "ALTERNATIVE_WINDOW_COMPONENT"
                        ),
                        method_id="EXACT_SYMMETRIC_SHAPLEY_M_EQUALS_P_TIMES_R",
                        coverage_scope=scope_id,
                        municipality_count=len(scoped),
                        period_count=2,
                        effect=effect,
                        effect_unit="enrollments_absolute_change_component",
                        interval_state="DETERMINISTIC_EXACT",
                        interval_lower=effect,
                        interval_upper=effect,
                        p_value_state="NOT_APPLICABLE_PREDECLARED",
                        p_value_raw=None,
                        multiplicity_family=None,
                        robustness_state="EXACT_CLOSURE_VERIFIED",
                        claim_ceiling="ACCOUNTING_DECOMPOSITION",
                        numerator_metric_id="education.enrollments",
                        numerator_lens="school_location",
                        denominator_metric_id="demography.population_age_15_17",
                        denominator_lens="resident_population",
                        composite_qualifier=(
                            "school_location_enrollments_per_resident_age_group_"
                            "context_not_coverage"
                        ),
                        closure_residual=decomposition["closure_residual"],
                        closure_tolerance=decomposition["closure_tolerance"],
                        total_enrollment_change=decomposition["total_change"],
                    )
                )
        for _, municipality in complete.iterrows():
            decomposition = _decompose_enrollment_change(
                float(municipality[f"enrollment_{start}"]),
                float(municipality[f"enrollment_{end}"]),
                float(municipality[f"population_{start}"]),
                float(municipality[f"population_{end}"]),
            )
            for component_id, component_key in (
                ("POPULATION_COMPONENT", "population_component"),
                ("TERRITORIAL_RELATION_COMPONENT", "relationship_component"),
            ):
                heterogeneity.append(
                    {
                        "question_id": question_id,
                        "heterogeneity_id": f"P2_{start}_{end}_{component_id}",
                        "municipality_ibge_code": municipality[
                            "municipality_ibge_code"
                        ],
                        "scope_id": "MUNICIPALITY",
                        "value": decomposition[component_key],
                        "unit": "enrollments_absolute_change_component",
                        "state": "OBSERVED",
                    }
                )
    vale_codes = set(_vale_codes())
    for excluded in sorted(vale_codes):
        remaining = sample[
            sample["municipality_ibge_code"].isin(vale_codes - {excluded})
        ]
        decomposition = _decompose_enrollment_change(
            float(remaining["enrollment_2018"].sum()),
            float(remaining["enrollment_2025"].sum()),
            float(remaining["population_2018"].sum()),
            float(remaining["population_2025"].sum()),
        )
        robustness.append(
            {
                "question_id": question_id,
                "robustness_id": "P2_VALE_LEAVE_ONE_OUT",
                "state": "VALID",
                "value": decomposition["population_component"],
                "unit": "population_component_enrollments",
                "detail": _json_cell(
                    {
                        "excludedMunicipalityIbgeCode": excluded,
                        "territorialRelationComponent": decomposition[
                            "relationship_component"
                        ],
                        "closureResidual": decomposition["closure_residual"],
                    }
                ),
            }
        )
    for component_id, component_key in (
        ("POPULATION_COMPONENT_2018_2025", "population_component"),
        ("TERRITORIAL_RELATION_COMPONENT_2018_2025", "relationship_component"),
    ):
        for scope_id in ("RS_497", "VALE_10", "MUNICIPALITY_4313375"):
            decomposition = main_components.get(scope_id)
            scope_rows.append(
                {
                    "question_id": question_id,
                    "measure_id": component_id,
                    "scope_id": scope_id,
                    "scope_state": "AVAILABLE" if decomposition else "UNAVAILABLE",
                    "value": decomposition.get(component_key) if decomposition else None,
                    "unit": "enrollments_absolute_change_component",
                    "municipality_count": len(scope_map[scope_id]) if decomposition else 0,
                    "coverage_scope": "RS_497",
                    "unavailability_reason": "" if decomposition else "ENDPOINT_OR_CLOSURE_FAILURE",
                }
            )
    terminal = (
        "ACCOUNTING_DECOMPOSITION_COMPLETE"
        if valid and len(main_components) == 3
        else "NOT_SUPPORTED_OR_UNAVAILABLE"
    )
    if not results:
        results.append(
            _insufficient_result(
                question_id=question_id,
                result_id="P2_NO_VALID_SCOPE",
                method_id="EXACT_SYMMETRIC_SHAPLEY_M_EQUALS_P_TIMES_R",
                coverage_scope="RS_497",
                claim_ceiling="ACCOUNTING_DECOMPOSITION",
                family=None,
                reason="NO_VALID_DECOMPOSITION",
                numerator_metric_id="education.enrollments",
                numerator_lens="school_location",
                denominator_metric_id="demography.population_age_15_17",
                denominator_lens="resident_population",
                composite_qualifier=(
                    "school_location_enrollments_per_resident_age_group_"
                    "context_not_coverage"
                ),
            )
        )
    for row in results:
        row["terminal_state"] = terminal
    return {
        "results": results,
        "robustness": robustness,
        "heterogeneity": heterogeneity,
        "scope": scope_rows,
        "terminal": terminal,
        "claim_ceiling": "ACCOUNTING_DECOMPOSITION",
        "claim_detail": {"mainComponents": main_components},
    }


def _apply_bh_to_question_rows(
    rows: list[dict[str, Any]], family: str
) -> dict[str, float | None]:
    fit_ids = FAMILY_FITS[family]
    by_id = {row["result_id"]: row for row in rows if row["multiplicity_family"] == family}
    if set(by_id) != set(fit_ids):
        raise AdvancedAnalysisValidationError(
            f"Família {family} não materializou exatamente os fits pré-registrados."
        )
    raw = {fit_id: by_id[fit_id]["p_value_raw"] for fit_id in fit_ids}
    adjusted = bh_adjust_fixed_family(fit_ids, raw)
    for fit_id, value in adjusted.items():
        by_id[fit_id]["p_value_bh"] = value
    return adjusted


def _sign(value: float | None) -> int:
    if value is None or value == 0:
        return 0
    return 1 if value > 0 else -1


def _interval_excludes_zero(row: Mapping[str, Any]) -> bool:
    lower = _finite_or_none(row.get("interval_lower"))
    upper = _finite_or_none(row.get("interval_upper"))
    return lower is not None and upper is not None and (lower > 0 or upper < 0)


def _observed_scope_rows(
    *,
    question_id: str,
    measure_id: str,
    values_by_code: Mapping[str, float],
    unit: str,
    coverage_scope: str,
    rs_available: bool = True,
) -> list[dict[str, Any]]:
    vale_codes = _vale_codes()
    scope_codes = {
        "RS_497": sorted(values_by_code),
        "VALE_10": list(vale_codes),
        "MUNICIPALITY_4313375": [NOVA_SANTA_RITA_CODE],
    }
    rows = []
    for scope_id, codes in scope_codes.items():
        if scope_id == "RS_497" and not rs_available:
            values: list[float] = []
            reason = "JOINT_METRIC_COVERAGE_RESTRICTED_TO_VALE_10"
        else:
            values = [values_by_code[code] for code in codes if code in values_by_code]
            reason = "" if values else "NO_OBSERVED_VALUES"
        rows.append(
            {
                "question_id": question_id,
                "measure_id": measure_id,
                "scope_id": scope_id,
                "scope_state": "AVAILABLE" if values else "UNAVAILABLE",
                "value": float(np.median(values)) if values else None,
                "unit": unit,
                "municipality_count": len(values),
                "coverage_scope": coverage_scope,
                "unavailability_reason": reason,
            }
        )
    return rows


def _panel_result_row(
    *,
    question_id: str,
    fit_id: str,
    fit: Mapping[str, Any],
    role: str,
    family: str,
    coverage_scope: str,
    effect_unit: str,
    claim_ceiling: str,
    numerator_metric_id: str,
    numerator_lens: str,
    denominator_metric_id: str = "",
    denominator_lens: str = "",
    composite_qualifier: str = "",
    interval_label: str = "CONFIDENCE_INTERVAL",
) -> dict[str, Any]:
    return _result_row(
        question_id=question_id,
        result_id=fit_id,
        result_role=role,
        method_id=(
            "TWO_WAY_FIXED_EFFECTS_EXACT_CLUSTER_SIGN_T"
            if fit["resampling"]["method"].startswith("exhaustive")
            else "TWO_WAY_FIXED_EFFECTS_CLUSTERED_SE"
        ),
        coverage_scope=coverage_scope,
        municipality_count=fit["municipality_count"],
        period_count=fit["period_count"],
        effect=fit["coefficient"],
        effect_unit=effect_unit,
        interval_state=interval_label,
        interval_lower=fit["interval_lower"],
        interval_upper=fit["interval_upper"],
        p_value_state="INFERENTIAL",
        p_value_raw=fit["p_value"],
        multiplicity_family=family,
        robustness_state="VALID_FIT",
        claim_ceiling=claim_ceiling,
        numerator_metric_id=numerator_metric_id,
        numerator_lens=numerator_lens,
        denominator_metric_id=denominator_metric_id,
        denominator_lens=denominator_lens,
        composite_qualifier=composite_qualifier,
        coefficient_standard_error=fit["standard_error"],
        standardized_effect=fit["standardized_effect"],
        observation_count=fit["observation_count"],
        within_exposure_variance=fit["within_exposure_variance"],
        resampling_detail=_json_cell(fit["resampling"]),
    )


def analyze_p3(frame: pd.DataFrame) -> dict[str, Any]:
    question_id = "P3_SCHOOL_CONDITIONS_AND_TRAJECTORY"
    family = "MF_P3_SCHOOL_CONDITIONS"
    periods = [str(year) for year in range(2018, 2026)]
    dropout = _metric_panel_column(
        frame,
        "education.dropout_rate_percent",
        stage="medio",
        periods=periods,
        coverage_scope="RS_497",
        column="dropout",
    )
    failure = _metric_panel_column(
        frame,
        "education.failure_rate_percent",
        stage="medio",
        periods=periods,
        coverage_scope="RS_497",
        column="failure",
    )
    adequacy = _metric_panel_column(
        frame,
        "education.teacher_adequacy_percent",
        stage="medio",
        periods=periods,
        coverage_scope="RS_497",
        column="adequacy",
    )
    panel = dropout.merge(
        failure,
        on=["municipality_ibge_code", "year_or_reference_period"],
        how="outer",
    ).merge(
        adequacy,
        on=["municipality_ibge_code", "year_or_reference_period"],
        how="outer",
    )
    panel = panel.sort_values(
        ["municipality_ibge_code", "year_or_reference_period"]
    )
    panel["adequacy_scaled"] = panel["adequacy"] / 10.0
    panel["adequacy_lag1"] = panel.groupby("municipality_ibge_code")[
        "adequacy_scaled"
    ].shift(1)
    panel["adequacy_lead1"] = panel.groupby("municipality_ibge_code")[
        "adequacy_scaled"
    ].shift(-1)
    vale_codes = set(_vale_codes())
    specifications = {
        "P3_MAIN_DROPOUT_L0": (panel, "dropout", "adequacy_scaled", 6),
        "P3_ALT_FAILURE_L0": (panel, "failure", "adequacy_scaled", 6),
        "P3_ALT_DROPOUT_L1": (panel, "dropout", "adequacy_lag1", 6),
        "P3_SENS_EXCLUDE_2020_2021": (
            panel[~panel["year_or_reference_period"].isin(["2020", "2021"])],
            "dropout",
            "adequacy_scaled",
            6,
        ),
        "P3_SENS_WINDOW_2022_2025": (
            panel[panel["year_or_reference_period"].isin(["2022", "2023", "2024", "2025"])],
            "dropout",
            "adequacy_scaled",
            4,
        ),
        "P3_PLACEBO_LEAD1": (panel, "dropout", "adequacy_lead1", 6),
        "P3_SENS_EXCLUDE_VALE_10": (
            panel[~panel["municipality_ibge_code"].isin(vale_codes)],
            "dropout",
            "adequacy_scaled",
            6,
        ),
    }
    results: list[dict[str, Any]] = []
    robustness: list[dict[str, Any]] = []
    fits: dict[str, dict[str, Any] | None] = {}
    for fit_id in FAMILY_FITS[family]:
        specification, outcome, exposure, minimum_periods = specifications[fit_id]
        try:
            fit = fit_fixed_effect_panel(
                specification,
                outcome=outcome,
                exposure=exposure,
                exact_cluster_sign_p=False,
            )
            if fit["municipality_count"] < 450 or fit["period_count"] < minimum_periods:
                raise AdvancedAnalysisValidationError("Cobertura abaixo do pré-registro.")
            fits[fit_id] = fit
            results.append(
                _panel_result_row(
                    question_id=question_id,
                    fit_id=fit_id,
                    fit=fit,
                    role="PRIMARY" if fit_id == "P3_MAIN_DROPOUT_L0" else "ALTERNATIVE_OR_SENSITIVITY",
                    family=family,
                    coverage_scope="RS_497",
                    effect_unit="percentage_points_per_10pp_teacher_adequacy",
                    claim_ceiling="ROBUST_ASSOCIATION",
                    numerator_metric_id=(
                        "education.failure_rate_percent"
                        if outcome == "failure"
                        else "education.dropout_rate_percent"
                    ),
                    numerator_lens="school_location",
                    denominator_metric_id="education.teacher_adequacy_percent",
                    denominator_lens="school_location",
                )
            )
            if fit_id.startswith("P3_SENS") or fit_id == "P3_PLACEBO_LEAD1":
                robustness.append(
                    {
                        "question_id": question_id,
                        "robustness_id": fit_id,
                        "state": "VALID",
                        "value": fit["coefficient"],
                        "unit": "percentage_points_per_10pp_teacher_adequacy",
                        "detail": _json_cell(
                            {
                                "standardizedEffect": fit["standardized_effect"],
                                "municipalityCount": fit["municipality_count"],
                                "periodCount": fit["period_count"],
                            }
                        ),
                    }
                )
        except (AdvancedAnalysisValidationError, np.linalg.LinAlgError) as error:
            fits[fit_id] = None
            results.append(
                _insufficient_result(
                    question_id=question_id,
                    result_id=fit_id,
                    method_id="TWO_WAY_FIXED_EFFECTS_CLUSTERED_SE",
                    coverage_scope="RS_497",
                    claim_ceiling="ROBUST_ASSOCIATION",
                    family=family,
                    reason=str(error),
                    numerator_metric_id="education.dropout_rate_percent",
                    numerator_lens="school_location",
                    denominator_metric_id="education.teacher_adequacy_percent",
                    denominator_lens="school_location",
                )
            )
    adjusted = _apply_bh_to_question_rows(results, family)
    all_valid = all(fit is not None for fit in fits.values())
    main = fits["P3_MAIN_DROPOUT_L0"]
    robust = False
    if all_valid and main is not None:
        main_row = next(row for row in results if row["result_id"] == "P3_MAIN_DROPOUT_L0")
        sensitivity_ids = (
            "P3_SENS_EXCLUDE_2020_2021",
            "P3_SENS_WINDOW_2022_2025",
            "P3_SENS_EXCLUDE_VALE_10",
        )
        placebo = fits["P3_PLACEBO_LEAD1"]
        robust = bool(
            abs(main["coefficient"]) >= 0.20
            and adjusted["P3_MAIN_DROPOUT_L0"] is not None
            and adjusted["P3_MAIN_DROPOUT_L0"] <= FAMILY_ALPHA[family]
            and _interval_excludes_zero(main_row)
            and all(
                _sign(fits[fit_id]["coefficient"]) == _sign(main["coefficient"])  # type: ignore[index]
                for fit_id in sensitivity_ids
            )
            and placebo is not None
            and abs(placebo["standardized_effect"]) < abs(main["standardized_effect"])
        )
    terminal = (
        "INSUFFICIENT_DATA"
        if not all_valid
        else "ROBUST_ASSOCIATION"
        if robust
        else "NO_ROBUST_ASSOCIATION"
    )
    for row in results:
        row["terminal_state"] = terminal
        row["robustness_state"] = (
            "ROBUST_ASSOCIATION_RULE_PASSED" if robust else row["robustness_state"]
        )
    latest = panel[panel["year_or_reference_period"].eq("2025")]
    dropout_by_code = latest.dropna(subset=["dropout"]).set_index(
        "municipality_ibge_code"
    )["dropout"].to_dict()
    adequacy_by_code = latest.dropna(subset=["adequacy"]).set_index(
        "municipality_ibge_code"
    )["adequacy"].to_dict()
    scope_rows = _observed_scope_rows(
        question_id=question_id,
        measure_id="MUNICIPAL_MEDIAN_DROPOUT_RATE_2025",
        values_by_code=dropout_by_code,
        unit="percent",
        coverage_scope="RS_497",
    ) + _observed_scope_rows(
        question_id=question_id,
        measure_id="MUNICIPAL_MEDIAN_TEACHER_ADEQUACY_2025",
        values_by_code=adequacy_by_code,
        unit="percent",
        coverage_scope="RS_497",
    )
    heterogeneity = []
    for code in sorted(set(dropout_by_code) | set(adequacy_by_code)):
        for measure, values in (
            ("DROPOUT_RATE_2025", dropout_by_code),
            ("TEACHER_ADEQUACY_2025", adequacy_by_code),
        ):
            heterogeneity.append(
                {
                    "question_id": question_id,
                    "heterogeneity_id": measure,
                    "municipality_ibge_code": code,
                    "scope_id": "VALE_10" if code in vale_codes else "RS_NON_VALE",
                    "value": values.get(code),
                    "unit": "percent",
                    "state": "OBSERVED" if code in values else "UNAVAILABLE",
                }
            )
    return {
        "results": results,
        "robustness": robustness,
        "heterogeneity": heterogeneity,
        "scope": scope_rows,
        "terminal": terminal,
        "claim_ceiling": "ROBUST_ASSOCIATION",
        "claim_detail": {
            "mainEffect": main["coefficient"] if main else None,
            "mainBhPValue": adjusted["P3_MAIN_DROPOUT_L0"],
            "rulePassed": robust,
        },
    }


def analyze_p4(frame: pd.DataFrame) -> dict[str, Any]:
    question_id = "P4_YOUTH_WORK_AND_HIGH_SCHOOL"
    family = "MF_P4_YOUTH_WORK"
    periods = [str(year) for year in range(2019, 2026)]
    vale_codes = set(_vale_codes())
    dropout_all = _metric_panel_column(
        frame,
        "education.dropout_rate_percent",
        stage="medio",
        periods=periods,
        coverage_scope="RS_497",
        column="dropout",
    )
    dropout = dropout_all[dropout_all["municipality_ibge_code"].isin(vale_codes)]
    bonds = _metric_panel_column(
        frame,
        "labor.youth_rais.active_bonds",
        stage="age_15_17",
        periods=periods,
        coverage_scope="VALE_10",
        column="bonds",
    )
    population = _metric_panel_column(
        frame,
        "demography.population_age_15_17",
        stage="age_15_17",
        periods=periods,
        coverage_scope="RS_497",
        column="population",
    )
    population = population[population["municipality_ibge_code"].isin(vale_codes)]
    panel = dropout.merge(
        bonds,
        on=["municipality_ibge_code", "year_or_reference_period"],
        how="outer",
    ).merge(
        population,
        on=["municipality_ibge_code", "year_or_reference_period"],
        how="outer",
    )
    panel["work_intensity"] = _safe_positive_denominator_ratio(
        panel["bonds"], panel["population"], multiplier=100.0
    )
    panel = panel.sort_values(
        ["municipality_ibge_code", "year_or_reference_period"]
    )
    panel["work_lag1"] = panel.groupby("municipality_ibge_code")[
        "work_intensity"
    ].shift(1)
    panel["work_lag2"] = panel.groupby("municipality_ibge_code")[
        "work_intensity"
    ].shift(2)
    panel["work_lead1"] = panel.groupby("municipality_ibge_code")[
        "work_intensity"
    ].shift(-1)
    specifications = {
        "P4_MAIN_L0": (panel, "dropout", "work_intensity"),
        "P4_ALT_L1": (panel, "dropout", "work_lag1"),
        "P4_ALT_L2": (panel, "dropout", "work_lag2"),
        "P4_SENS_EXCLUDE_2020_2021": (
            panel[~panel["year_or_reference_period"].isin(["2020", "2021"])],
            "dropout",
            "work_intensity",
        ),
        "P4_PLACEBO_LEAD1": (panel, "dropout", "work_lead1"),
        "P4_REVERSE_DIRECTION": (panel, "work_intensity", "dropout"),
    }
    results: list[dict[str, Any]] = []
    robustness: list[dict[str, Any]] = []
    fits: dict[str, dict[str, Any] | None] = {}
    for fit_id in FAMILY_FITS[family]:
        specification, outcome, exposure = specifications[fit_id]
        try:
            fit = fit_fixed_effect_panel(
                specification,
                outcome=outcome,
                exposure=exposure,
                exact_cluster_sign_p=True,
            )
            if fit["municipality_count"] < 9 or fit["period_count"] < 5:
                raise AdvancedAnalysisValidationError("Cobertura abaixo do pré-registro.")
            fits[fit_id] = fit
            results.append(
                _panel_result_row(
                    question_id=question_id,
                    fit_id=fit_id,
                    fit=fit,
                    role="PRIMARY" if fit_id == "P4_MAIN_L0" else "ALTERNATIVE_OR_DIAGNOSTIC",
                    family=family,
                    coverage_scope="VALE_10",
                    effect_unit=(
                        "dropout_pp_per_workplace_bond_per_100_residents_context"
                        if outcome == "dropout"
                        else "workplace_bonds_per_100_context_per_dropout_pp"
                    ),
                    claim_ceiling="PLANNING_SIGNAL",
                    numerator_metric_id=(
                        "education.dropout_rate_percent"
                        if outcome == "dropout"
                        else "labor.youth_rais.active_bonds"
                    ),
                    numerator_lens=(
                        "school_location"
                        if outcome == "dropout"
                        else "establishment_location_workplace"
                    ),
                    denominator_metric_id="demography.population_age_15_17",
                    denominator_lens="resident_population",
                    composite_qualifier=(
                        "workplace_bonds_per_resident_age_group_context_not_employment_rate"
                    ),
                )
            )
            robustness.append(
                {
                    "question_id": question_id,
                    "robustness_id": fit_id,
                    "state": "VALID",
                    "value": fit["coefficient"],
                    "unit": "coefficient",
                    "detail": _json_cell(fit["resampling"]),
                }
            )
        except (AdvancedAnalysisValidationError, np.linalg.LinAlgError) as error:
            fits[fit_id] = None
            results.append(
                _insufficient_result(
                    question_id=question_id,
                    result_id=fit_id,
                    method_id="TWO_WAY_FIXED_EFFECTS_EXACT_CLUSTER_SIGN_T",
                    coverage_scope="VALE_10",
                    claim_ceiling="PLANNING_SIGNAL",
                    family=family,
                    reason=str(error),
                    numerator_metric_id="education.dropout_rate_percent",
                    numerator_lens="school_location",
                    denominator_metric_id="demography.population_age_15_17",
                    denominator_lens="resident_population",
                    composite_qualifier=(
                        "workplace_bonds_per_resident_age_group_context_not_employment_rate"
                    ),
                )
            )
    loo_coefficients: list[float] = []
    for excluded in sorted(vale_codes):
        try:
            loo = fit_fixed_effect_panel(
                panel[panel["municipality_ibge_code"].ne(excluded)],
                outcome="dropout",
                exposure="work_intensity",
                exact_cluster_sign_p=False,
            )
            loo_coefficients.append(loo["coefficient"])
            state = "VALID"
            value = loo["coefficient"]
            detail = ""
        except (AdvancedAnalysisValidationError, np.linalg.LinAlgError) as error:
            state = "INSUFFICIENT_DATA"
            value = None
            detail = str(error)
        robustness.append(
            {
                "question_id": question_id,
                "robustness_id": "P4_LEAVE_ONE_MUNICIPALITY_OUT",
                "state": state,
                "value": value,
                "unit": "dropout_pp_per_workplace_bond_per_100_context",
                "detail": _json_cell(
                    {
                        "excludedMunicipalityIbgeCode": excluded,
                        "failureReason": detail,
                    }
                ),
            }
        )
    adjusted = _apply_bh_to_question_rows(results, family)
    all_valid = all(fit is not None for fit in fits.values()) and len(loo_coefficients) >= 9
    main = fits["P4_MAIN_L0"]
    signal = False
    if all_valid and main is not None:
        main_row = next(row for row in results if row["result_id"] == "P4_MAIN_L0")
        alternate_ids = (
            "P4_ALT_L1",
            "P4_ALT_L2",
            "P4_SENS_EXCLUDE_2020_2021",
        )
        preserved_alternates = sum(
            _sign(fits[fit_id]["coefficient"]) == _sign(main["coefficient"])  # type: ignore[index]
            for fit_id in alternate_ids
        )
        preserved_loo = sum(
            _sign(value) == _sign(main["coefficient"]) for value in loo_coefficients
        )
        placebo = fits["P4_PLACEBO_LEAD1"]
        signal = bool(
            abs(main["coefficient"]) >= 0.10
            and adjusted["P4_MAIN_L0"] is not None
            and adjusted["P4_MAIN_L0"] <= FAMILY_ALPHA[family]
            and _interval_excludes_zero(main_row)
            and preserved_alternates >= 2
            and preserved_loo >= 8
            and placebo is not None
            and abs(placebo["standardized_effect"]) < abs(main["standardized_effect"])
        )
    terminal = (
        "INSUFFICIENT_DATA"
        if not all_valid
        else "PLANNING_SIGNAL_ONLY"
        if signal
        else "NO_ROBUST_ASSOCIATION"
    )
    for row in results:
        row["terminal_state"] = terminal
    latest_all_dropout = dropout_all[
        dropout_all["year_or_reference_period"].eq("2025")
    ].dropna(subset=["dropout"])
    dropout_by_code = latest_all_dropout.set_index("municipality_ibge_code")[
        "dropout"
    ].to_dict()
    latest_vale = panel[panel["year_or_reference_period"].eq("2025")]
    work_by_code = latest_vale.dropna(subset=["work_intensity"]).set_index(
        "municipality_ibge_code"
    )["work_intensity"].to_dict()
    scope_rows = _observed_scope_rows(
        question_id=question_id,
        measure_id="MUNICIPAL_MEDIAN_DROPOUT_RATE_2025",
        values_by_code=dropout_by_code,
        unit="percent",
        coverage_scope="RS_497",
    ) + _observed_scope_rows(
        question_id=question_id,
        measure_id="MUNICIPAL_MEDIAN_WORKPLACE_BONDS_PER_100_RESIDENTS_15_17_2025",
        values_by_code=work_by_code,
        unit="workplace_bonds_per_100_resident_age_group_context",
        coverage_scope="VALE_10",
        rs_available=False,
    )
    heterogeneity = []
    for code in sorted(vale_codes):
        for measure, values, unit in (
            ("DROPOUT_RATE_2025", dropout_by_code, "percent"),
            (
                "WORKPLACE_BONDS_PER_100_RESIDENTS_15_17_2025",
                work_by_code,
                "workplace_bonds_per_100_resident_age_group_context",
            ),
        ):
            heterogeneity.append(
                {
                    "question_id": question_id,
                    "heterogeneity_id": measure,
                    "municipality_ibge_code": code,
                    "scope_id": "VALE_10",
                    "value": values.get(code),
                    "unit": unit,
                    "state": "OBSERVED" if code in values else "UNAVAILABLE",
                }
            )
    return {
        "results": results,
        "robustness": robustness,
        "heterogeneity": heterogeneity,
        "scope": scope_rows,
        "terminal": terminal,
        "claim_ceiling": "PLANNING_SIGNAL",
        "claim_detail": {
            "mainEffect": main["coefficient"] if main else None,
            "mainBhPValue": adjusted["P4_MAIN_L0"],
            "validLeaveOneOutCount": len(loo_coefficients),
            "rulePassed": signal,
            "lowPowerCaveatRequired": True,
        },
    }


def _fit_seed(fit_id: str, procedure_id: str) -> int:
    payload = f"4313375|{fit_id}|{procedure_id}".encode("utf-8")
    return int.from_bytes(
        hashlib.sha256(payload).digest()[:8], byteorder="big", signed=False
    )


def analyze_p5(frame: pd.DataFrame) -> dict[str, Any]:
    question_id = "P5_OCCUPATIONS_AND_EPT"
    vale_codes = set(_vale_codes())
    occupation = _metric_rows(
        frame,
        "labor.occupation_active_bonds",
        stage="all_ages",
        periods=["2025"],
        coverage_scope="VALE_10",
        dimension_id="ANY",
    )
    occupation = occupation[
        occupation["dimension_id"].ne("ALL")
        & occupation["municipality_ibge_code"].isin(vale_codes)
    ].copy()
    occupation = occupation.dropna(subset=["analysis_value"])
    occupation["occupation_subgroup_code"] = occupation["dimension_id"].str[:2]
    if not occupation["occupation_subgroup_code"].str.fullmatch(r"\d{2}").all():
        raise AdvancedAnalysisValidationError(
            "Dimensão ocupacional não permite agregação declarada no prefixo CBO de dois dígitos."
        )
    occupation_by_subgroup = (
        occupation.groupby(
            ["municipality_ibge_code", "occupation_subgroup_code"], as_index=False
        )["analysis_value"]
        .sum(min_count=1)
        .rename(columns={"analysis_value": "active_bonds"})
    )
    bridge = pd.read_csv(BRIDGE_PATH, dtype=str, keep_default_na=False)
    bridge = bridge[bridge["municipality_ibge_code"].isin(vale_codes)].copy()
    bridge["technical_enrollments_value"] = pd.to_numeric(
        bridge["technical_enrollments"], errors="coerce"
    )
    if bridge["technical_enrollments_value"].isna().any():
        raise AdvancedAnalysisValidationError(
            "Matrícula técnica não numérica na ponte normativa."
        )
    bridge["valid_subgroup"] = bridge["occupation_subgroup_code"].str.fullmatch(
        r"\d{2}"
    )
    offer_key = ["municipality_ibge_code", "school_code", "course_code"]
    offer_value_counts = bridge.groupby(offer_key)[
        "technical_enrollments_value"
    ].nunique(dropna=False)
    if offer_value_counts.gt(1).any():
        raise AdvancedAnalysisValidationError(
            "Uma unidade de oferta possui totais técnicos divergentes entre links CBO."
        )
    offer_coverage = (
        bridge.groupby(offer_key, as_index=False)
        .agg(
            technical_enrollments=("technical_enrollments_value", "first"),
            mapped=("valid_subgroup", "max"),
        )
        .sort_values(offer_key)
    )
    ept_total_rows = _metric_rows(
        frame,
        "education.ept_technical_enrollments",
        stage="professional_technical",
        periods=["2025"],
        coverage_scope="VALE_10",
        dimension_id="grain=municipality_total|school=ALL|axis=ALL|course=ALL",
    )
    if ept_total_rows.duplicated("municipality_ibge_code").any():
        raise AdvancedAnalysisValidationError("Total municipal EPT duplicado no AA1.")
    ept_by_code = ept_total_rows.set_index("municipality_ibge_code")[
        "analysis_value"
    ].to_dict()
    offer_enrollments_by_code = offer_coverage.groupby("municipality_ibge_code")[
        "technical_enrollments"
    ].sum().to_dict()
    reconciliation = {
        code: {
            "panelTotal": _finite_or_none(ept_by_code.get(code)),
            "bridgeOfferTotal": float(offer_enrollments_by_code.get(code, 0.0)),
        }
        for code in sorted(vale_codes)
    }
    reconciliation_failures = [
        code
        for code, values in reconciliation.items()
        if values["panelTotal"] is None
        or abs(values["panelTotal"] - values["bridgeOfferTotal"]) > 1e-9
    ]
    if reconciliation_failures:
        raise AdvancedAnalysisValidationError(
            "Ponte curso-CBO não reconcilia com o total municipal EPT: "
            + ", ".join(reconciliation_failures)
        )
    links = bridge[bridge["valid_subgroup"]].drop_duplicates(
        ["municipality_ibge_code", "course_code", "occupation_subgroup_code"]
    )
    local_subgroups = {
        code: set(
            links.loc[
                links["municipality_ibge_code"].eq(code),
                "occupation_subgroup_code",
            ].tolist()
        )
        for code in sorted(vale_codes)
    }
    vale_subgroups = set(links["occupation_subgroup_code"].tolist())
    municipality_rows: list[dict[str, Any]] = []
    for code in sorted(vale_codes):
        bonds = occupation_by_subgroup[
            occupation_by_subgroup["municipality_ibge_code"].eq(code)
        ]
        total = float(bonds["active_bonds"].sum())
        if total <= 0:
            municipality_rows.append(
                {
                    "municipality_ibge_code": code,
                    "total_bonds": total,
                    "local_share": None,
                    "vale_share": None,
                    "state": "UNAVAILABLE",
                }
            )
            continue
        local = float(
            bonds.loc[
                bonds["occupation_subgroup_code"].isin(local_subgroups[code]),
                "active_bonds",
            ].sum()
        )
        accessible = float(
            bonds.loc[
                bonds["occupation_subgroup_code"].isin(vale_subgroups),
                "active_bonds",
            ].sum()
        )
        municipality_rows.append(
            {
                "municipality_ibge_code": code,
                "total_bonds": total,
                "local_matched_bonds": local,
                "vale_matched_bonds": accessible,
                "local_share": 100.0 * local / total,
                "vale_share": 100.0 * accessible / total,
                "state": "OBSERVED",
            }
        )
    correspondence = pd.DataFrame(municipality_rows)
    valid_correspondence = correspondence[
        correspondence["state"].eq("OBSERVED")
    ]
    total_offer_enrollments = float(offer_coverage["technical_enrollments"].sum())
    mapped_offer_enrollments = float(
        offer_coverage.loc[
            offer_coverage["mapped"], "technical_enrollments"
        ].sum()
    )
    mapped_enrollment_share = (
        mapped_offer_enrollments / total_offer_enrollments
        if total_offer_enrollments > 0
        else None
    )
    total_bonds = float(valid_correspondence["total_bonds"].sum())
    local_matched = float(valid_correspondence["local_matched_bonds"].sum())
    vale_matched = float(valid_correspondence["vale_matched_bonds"].sum())
    local_share = 100.0 * local_matched / total_bonds if total_bonds > 0 else None
    vale_share = 100.0 * vale_matched / total_bonds if total_bonds > 0 else None
    supported = bool(
        mapped_enrollment_share is not None
        and mapped_enrollment_share >= 0.70
        and total_bonds > 0
        and len(valid_correspondence) == 10
    )
    terminal = (
        "DISTRIBUTIONAL_PATTERN_COMPLETE"
        if supported
        else "NOT_SUPPORTED_OR_UNAVAILABLE"
    )
    results = [
        _result_row(
            question_id=question_id,
            result_id="P5_VALE_LOCAL_TO_ACCESSIBLE_CORRESPONDENCE_BOUND",
            result_role="PRIMARY_BOUND",
            method_id="DEDUPLICATED_NORMATIVE_COURSE_CBO_CORRESPONDENCE",
            coverage_scope="VALE_10",
            municipality_count=len(valid_correspondence),
            period_count=1,
            effect=local_share,
            effect_unit="percent_of_active_bonds_in_normatively_connected_subgroups",
            interval_state="IDENTIFICATION_BOUND",
            interval_lower=local_share,
            interval_upper=vale_share,
            p_value_state="NOT_APPLICABLE_PREDECLARED",
            p_value_raw=None,
            multiplicity_family=None,
            robustness_state=(
                "COVERAGE_FLOOR_PASSED" if supported else "COVERAGE_OR_DENOMINATOR_FAILED"
            ),
            claim_ceiling="DISTRIBUTIONAL_PATTERN",
            numerator_metric_id="labor.occupation_active_bonds",
            numerator_lens="establishment_location_workplace",
            denominator_metric_id="labor.occupation_active_bonds",
            denominator_lens="establishment_location_workplace",
            availability_reason=(
                "" if supported else "MAPPED_EPT_COVERAGE_BELOW_FLOOR_OR_DENOMINATOR_INVALID"
            ),
            source_refs=(PANEL_SOURCE_REF, BRIDGE_SOURCE_REF),
            mapped_technical_enrollment_share=mapped_enrollment_share,
            unique_offer_unit_count=int(len(offer_coverage)),
            mapped_offer_unit_share=float(offer_coverage["mapped"].mean())
            if len(offer_coverage)
            else None,
            active_bond_share_outside_local_mapped_subgroups=(
                100.0 - local_share if local_share is not None else None
            ),
        )
    ]
    for row in results:
        row["terminal_state"] = terminal
    robustness = [
        {
            "question_id": question_id,
            "robustness_id": "P5_BRIDGE_COVERAGE",
            "state": "VALID" if mapped_enrollment_share is not None else "UNAVAILABLE",
            "value": mapped_enrollment_share,
            "unit": "share_0_to_1",
            "detail": _json_cell(
                {
                    "coverageFloor": 0.70,
                    "uniqueOfferUnitCount": int(len(offer_coverage)),
                    "mappedOfferUnitCount": int(offer_coverage["mapped"].sum()),
                    "mappedTechnicalEnrollments": mapped_offer_enrollments,
                    "totalTechnicalEnrollments": total_offer_enrollments,
                    "normativeLinkCount": int(len(links)),
                }
            ),
        },
        {
            "question_id": question_id,
            "robustness_id": "P5_EPT_PANEL_BRIDGE_RECONCILIATION",
            "state": "VALID",
            "value": 0.0,
            "unit": "maximum_absolute_enrollment_difference",
            "detail": _json_cell(reconciliation),
        },
        {
            "question_id": question_id,
            "robustness_id": "P5_LOCAL_VS_VALE_ACCESSIBLE_OFFER",
            "state": "VALID" if total_bonds > 0 else "UNAVAILABLE",
            "value": (vale_share - local_share)
            if vale_share is not None and local_share is not None
            else None,
            "unit": "percentage_points_bound_width",
            "detail": _json_cell(
                {"localShare": local_share, "valeAccessibleShare": vale_share}
            ),
        },
    ]
    heterogeneity = []
    for row in municipality_rows:
        for measure, key in (
            ("LOCAL_OFFER_CORRESPONDENCE_SHARE_2025", "local_share"),
            ("VALE_ACCESSIBLE_OFFER_CORRESPONDENCE_SHARE_2025", "vale_share"),
        ):
            heterogeneity.append(
                {
                    "question_id": question_id,
                    "heterogeneity_id": measure,
                    "municipality_ibge_code": row["municipality_ibge_code"],
                    "scope_id": "VALE_10",
                    "value": row.get(key),
                    "unit": "percent_of_active_bonds",
                    "state": row["state"],
                }
            )
    nsr = correspondence[
        correspondence["municipality_ibge_code"].eq(NOVA_SANTA_RITA_CODE)
    ]
    nsr_local = (
        _finite_or_none(nsr.iloc[0]["local_share"]) if len(nsr) == 1 else None
    )
    scope_rows = []
    for scope_id, value, count, reason in (
        (
            "RS_497",
            None,
            0,
            "DETAILED_EPT_AND_OCCUPATION_COVERAGE_RESTRICTED_TO_VALE_10",
        ),
        ("VALE_10", local_share, len(valid_correspondence), ""),
        (
            "MUNICIPALITY_4313375",
            nsr_local,
            1 if nsr_local is not None else 0,
            "" if nsr_local is not None else "MUNICIPALITY_DENOMINATOR_UNAVAILABLE",
        ),
    ):
        scope_rows.append(
            {
                "question_id": question_id,
                "measure_id": "LOCAL_OFFER_CORRESPONDENCE_SHARE_2025",
                "scope_id": scope_id,
                "scope_state": "AVAILABLE" if value is not None else "UNAVAILABLE",
                "value": value,
                "unit": "percent_of_active_bonds",
                "municipality_count": count,
                "coverage_scope": "VALE_10",
                "unavailability_reason": reason,
            }
        )
    return {
        "results": results,
        "robustness": robustness,
        "heterogeneity": heterogeneity,
        "scope": scope_rows,
        "terminal": terminal,
        "claim_ceiling": "DISTRIBUTIONAL_PATTERN",
        "claim_detail": {
            "valeLocalShare": local_share,
            "valeAccessibleShare": vale_share,
            "novaSantaRitaLocalShare": nsr_local,
            "novaSantaRitaObservedEptEnrollmentTotal": _finite_or_none(
                ept_by_code.get(NOVA_SANTA_RITA_CODE)
            ),
            "mappedTechnicalEnrollmentShare": mapped_enrollment_share,
            "coverageFloorPassed": supported,
        },
    }


def analyze_p6(frame: pd.DataFrame) -> dict[str, Any]:
    question_id = "P6_ADULT_SCHOOLING_WORK_AND_EJA"
    family = "MF_P6_ADULT_EJA_WORK"
    vale_codes = set(_vale_codes())
    adult_share_all = _metric_panel_column(
        frame,
        "adult.high_school_completion_share_percent",
        stage="adult_18_or_more",
        periods=["2022"],
        coverage_scope="RS_497",
        column="adult_completion",
    )
    adult_population_all = _metric_panel_column(
        frame,
        "adult.population_count",
        stage="adult_18_or_more",
        periods=["2022"],
        coverage_scope="RS_497",
        column="adult_population",
    )
    eja_fundamental = _metric_panel_column(
        frame,
        "education.eja_enrollments",
        stage="eja_fundamental",
        periods=["2022"],
        coverage_scope="VALE_10",
        column="eja_fundamental",
    )
    eja_high_school = _metric_panel_column(
        frame,
        "education.eja_enrollments",
        stage="eja_high_school",
        periods=["2022"],
        coverage_scope="VALE_10",
        column="eja_high_school",
    )
    work = _metric_panel_column(
        frame,
        "labor.youth_rais.schooling_composition_share_percent",
        stage="age_18_24",
        periods=["2022"],
        coverage_scope="VALE_10",
        column="young_worker_hs_incomplete",
        dimension_id="high_school_incomplete",
    )
    adult_share = adult_share_all[
        adult_share_all["municipality_ibge_code"].isin(vale_codes)
    ]
    adult_population = adult_population_all[
        adult_population_all["municipality_ibge_code"].isin(vale_codes)
    ]
    key = ["municipality_ibge_code", "year_or_reference_period"]
    sample = adult_share.merge(adult_population, on=key, how="outer")
    for part in (eja_fundamental, eja_high_school, work):
        sample = sample.merge(part, on=key, how="outer")
    sample["eja_per_1000_adults"] = _safe_positive_denominator_ratio(
        sample["eja_fundamental"] + sample["eja_high_school"],
        sample["adult_population"],
        multiplier=1000.0,
    )
    sample = sample.sort_values("municipality_ibge_code")
    definitions = {
        "P6_EJA_SPEARMAN": ("eja_per_1000_adults", "spearman"),
        "P6_WORK_SPEARMAN": ("young_worker_hs_incomplete", "spearman"),
        "P6_EJA_PEARSON": ("eja_per_1000_adults", "pearson"),
        "P6_WORK_PEARSON": ("young_worker_hs_incomplete", "pearson"),
    }
    results: list[dict[str, Any]] = []
    robustness: list[dict[str, Any]] = []
    fits: dict[str, dict[str, Any] | None] = {}
    bootstrap_by_fit: dict[str, tuple[float, float] | None] = {}
    for fit_id in FAMILY_FITS[family]:
        outcome, method = definitions[fit_id]
        fit_sample = sample.dropna(subset=["adult_completion", outcome])
        x = fit_sample["adult_completion"].to_numpy(dtype=float)
        y = fit_sample[outcome].to_numpy(dtype=float)
        try:
            if (
                len(fit_sample) < 8
                or len(np.unique(pd.Series(x).rank(method="average"))) < 4
                or len(np.unique(pd.Series(y).rank(method="average"))) < 4
            ):
                raise AdvancedAnalysisValidationError(
                    "Cobertura ou diversidade de postos abaixo do pré-registro."
                )
            effect, p_value, extreme = permutation_correlation(
                x,
                y,
                method=method,
                seed=_fit_seed(fit_id, "permutation_99999"),
            )
            interval_lower = None
            interval_upper = None
            interval_state = "UNAVAILABLE"
            valid_bootstrap = None
            if method == "spearman":
                interval_lower, interval_upper, valid_bootstrap = (
                    bootstrap_correlation_interval(
                        x,
                        y,
                        method=method,
                        seed=_fit_seed(fit_id, "bootstrap_10000"),
                    )
                )
                interval_state = "DESCRIPTIVE_BOOTSTRAP"
                bootstrap_by_fit[fit_id] = (interval_lower, interval_upper)
            else:
                bootstrap_by_fit[fit_id] = None
            fit = {
                "effect": effect,
                "p_value": p_value,
                "interval_lower": interval_lower,
                "interval_upper": interval_upper,
                "municipality_count": len(fit_sample),
                "extreme_count": extreme,
                "valid_bootstrap": valid_bootstrap,
                "outcome": outcome,
                "method": method,
            }
            fits[fit_id] = fit
            results.append(
                _result_row(
                    question_id=question_id,
                    result_id=fit_id,
                    result_role="PRIMARY" if method == "spearman" else "ALTERNATIVE",
                    method_id=f"{method.upper()}_PCG64_PERMUTATION_99999",
                    coverage_scope="VALE_10",
                    municipality_count=len(fit_sample),
                    period_count=1,
                    effect=effect,
                    effect_unit=f"{method}_correlation",
                    interval_state=interval_state,
                    interval_lower=interval_lower,
                    interval_upper=interval_upper,
                    p_value_state="INFERENTIAL",
                    p_value_raw=p_value,
                    multiplicity_family=family,
                    robustness_state="VALID_FIT",
                    claim_ceiling="DISTRIBUTIONAL_PATTERN",
                    numerator_metric_id="adult.high_school_completion_share_percent",
                    numerator_lens="resident_population",
                    denominator_metric_id=(
                        "education.eja_enrollments"
                        if outcome == "eja_per_1000_adults"
                        else "labor.youth_rais.schooling_composition_share_percent"
                    ),
                    denominator_lens=(
                        "school_location"
                        if outcome == "eja_per_1000_adults"
                        else "establishment_location_workplace"
                    ),
                    resampling_detail=_json_cell(
                        {
                            "generator": "PCG64",
                            "permutations": 99_999,
                            "extremeCount": extreme,
                            "pValueEstimator": "(k+1)/(B+1)",
                            "attainablePValueFloor": 0.00001,
                            "seed": _fit_seed(fit_id, "permutation_99999"),
                            "validBootstrapResamples": valid_bootstrap,
                        }
                    ),
                )
            )
        except (AdvancedAnalysisValidationError, np.linalg.LinAlgError) as error:
            fits[fit_id] = None
            bootstrap_by_fit[fit_id] = None
            results.append(
                _insufficient_result(
                    question_id=question_id,
                    result_id=fit_id,
                    method_id=f"{method.upper()}_PCG64_PERMUTATION_99999",
                    coverage_scope="VALE_10",
                    claim_ceiling="DISTRIBUTIONAL_PATTERN",
                    family=family,
                    reason=str(error),
                    numerator_metric_id="adult.high_school_completion_share_percent",
                    numerator_lens="resident_population",
                    denominator_metric_id=(
                        "education.eja_enrollments"
                        if outcome == "eja_per_1000_adults"
                        else "labor.youth_rais.schooling_composition_share_percent"
                    ),
                    denominator_lens=(
                        "school_location"
                        if outcome == "eja_per_1000_adults"
                        else "establishment_location_workplace"
                    ),
                )
            )
    loo_by_primary: dict[str, list[float]] = {
        "P6_EJA_SPEARMAN": [],
        "P6_WORK_SPEARMAN": [],
    }
    valid_loo_count = 0
    for fit_id, outcome in (
        ("P6_EJA_SPEARMAN", "eja_per_1000_adults"),
        ("P6_WORK_SPEARMAN", "young_worker_hs_incomplete"),
    ):
        fit_sample = sample.dropna(subset=["adult_completion", outcome])
        for excluded in sorted(vale_codes):
            loo_sample = fit_sample[
                fit_sample["municipality_ibge_code"].ne(excluded)
            ]
            try:
                value = _correlation(
                    loo_sample["adult_completion"].to_numpy(dtype=float),
                    loo_sample[outcome].to_numpy(dtype=float),
                    method="spearman",
                )
                loo_by_primary[fit_id].append(value)
                valid_loo_count += 1
                state = "VALID"
                reason = ""
            except AdvancedAnalysisValidationError as error:
                value = None
                state = "INSUFFICIENT_DATA"
                reason = str(error)
            robustness.append(
                {
                    "question_id": question_id,
                    "robustness_id": f"{fit_id}_LEAVE_ONE_OUT",
                    "state": state,
                    "value": value,
                    "unit": "spearman_rho",
                    "detail": _json_cell(
                        {
                            "excludedMunicipalityIbgeCode": excluded,
                            "failureReason": reason,
                        }
                    ),
                }
            )
    adjusted = _apply_bh_to_question_rows(results, family)
    all_valid = all(fit is not None for fit in fits.values()) and valid_loo_count >= 16
    stable_fit: str | None = None
    if all_valid:
        for fit_id in ("P6_EJA_SPEARMAN", "P6_WORK_SPEARMAN"):
            fit = fits[fit_id]
            interval = bootstrap_by_fit[fit_id]
            if fit is None or interval is None:
                continue
            preserved = sum(
                _sign(value) == _sign(fit["effect"])
                for value in loo_by_primary[fit_id]
            )
            if (
                abs(fit["effect"]) >= 0.40
                and adjusted[fit_id] is not None
                and adjusted[fit_id] <= FAMILY_ALPHA[family]
                and (interval[0] > 0 or interval[1] < 0)
                and preserved >= 8
            ):
                stable_fit = fit_id
                break
    terminal = (
        "INSUFFICIENT_DATA"
        if not all_valid
        else "DISTRIBUTIONAL_PATTERN_COMPLETE"
        if stable_fit is not None
        else "NO_ROBUST_ASSOCIATION"
    )
    for row in results:
        row["terminal_state"] = terminal
    adult_by_code = adult_share_all.dropna(subset=["adult_completion"]).set_index(
        "municipality_ibge_code"
    )["adult_completion"].to_dict()
    eja_by_code = sample.dropna(subset=["eja_per_1000_adults"]).set_index(
        "municipality_ibge_code"
    )["eja_per_1000_adults"].to_dict()
    work_by_code = sample.dropna(subset=["young_worker_hs_incomplete"]).set_index(
        "municipality_ibge_code"
    )["young_worker_hs_incomplete"].to_dict()
    scope_rows = _observed_scope_rows(
        question_id=question_id,
        measure_id="MUNICIPAL_MEDIAN_ADULT_HS_COMPLETION_SHARE_2022",
        values_by_code=adult_by_code,
        unit="percent",
        coverage_scope="RS_497",
    )
    scope_rows += _observed_scope_rows(
        question_id=question_id,
        measure_id="MUNICIPAL_MEDIAN_EJA_ENROLLMENTS_PER_1000_ADULTS_2022",
        values_by_code=eja_by_code,
        unit="enrollments_per_1000_adults",
        coverage_scope="VALE_10",
        rs_available=False,
    )
    scope_rows += _observed_scope_rows(
        question_id=question_id,
        measure_id="MUNICIPAL_MEDIAN_YOUNG_WORKER_HS_INCOMPLETE_SHARE_2022",
        values_by_code=work_by_code,
        unit="percent",
        coverage_scope="VALE_10",
        rs_available=False,
    )
    heterogeneity = []
    for code in sorted(vale_codes):
        for measure, values, unit in (
            ("ADULT_HS_COMPLETION_SHARE_2022", adult_by_code, "percent"),
            ("EJA_PER_1000_ADULTS_2022", eja_by_code, "enrollments_per_1000_adults"),
            ("YOUNG_WORKER_HS_INCOMPLETE_SHARE_2022", work_by_code, "percent"),
        ):
            heterogeneity.append(
                {
                    "question_id": question_id,
                    "heterogeneity_id": measure,
                    "municipality_ibge_code": code,
                    "scope_id": "VALE_10",
                    "value": values.get(code),
                    "unit": unit,
                    "state": "OBSERVED" if code in values else "UNAVAILABLE",
                }
            )
    return {
        "results": results,
        "robustness": robustness,
        "heterogeneity": heterogeneity,
        "scope": scope_rows,
        "terminal": terminal,
        "claim_ceiling": "DISTRIBUTIONAL_PATTERN",
        "claim_detail": {
            "stablePrimaryFit": stable_fit,
            "validLeaveOneOutCount": valid_loo_count,
            "lowPowerCaveatRequired": True,
            "primaryEffects": {
                fit_id: fits[fit_id]["effect"] if fits[fit_id] else None
                for fit_id in ("P6_EJA_SPEARMAN", "P6_WORK_SPEARMAN")
            },
        },
    }


def analyze_p7(frame: pd.DataFrame) -> dict[str, Any]:
    question_id = "P7_RURALITY_INCLUSION_AND_ACCESS"
    family = "MF_P7_RURALITY_INCLUSION"
    periods = [str(year) for year in range(2014, 2026)]
    vale_codes = set(_vale_codes())
    component_specs = {
        "RURAL": (
            "education.rural.rural_enrollments",
            "education.rural.rural_schools",
        ),
        "AEE": (
            "education.special_aee.special_enrollments",
            "education.special_aee.schools_offering_aee",
        ),
    }
    panels: dict[str, pd.DataFrame] = {}
    for component, (outcome_metric, exposure_metric) in component_specs.items():
        outcome = _metric_panel_column(
            frame,
            outcome_metric,
            stage="all",
            periods=periods,
            coverage_scope="VALE_10",
            column="outcome_raw",
        )
        exposure = _metric_panel_column(
            frame,
            exposure_metric,
            stage="all",
            periods=periods,
            coverage_scope="VALE_10",
            column="exposure_raw",
        )
        panel = outcome.merge(
            exposure,
            on=["municipality_ibge_code", "year_or_reference_period"],
            how="outer",
        ).sort_values(["municipality_ibge_code", "year_or_reference_period"])
        panel["outcome_log1p"] = np.log1p(panel["outcome_raw"])
        panel["exposure_log1p"] = np.log1p(panel["exposure_raw"])
        panel["exposure_lag1"] = panel.groupby("municipality_ibge_code")[
            "exposure_log1p"
        ].shift(1)
        panels[component] = panel
    specifications: dict[str, tuple[pd.DataFrame, str]] = {}
    for component, panel in panels.items():
        specifications[f"P7_{component}_MAIN"] = (panel, "exposure_log1p")
        specifications[f"P7_{component}_EXCLUDE_2020_2021"] = (
            panel[~panel["year_or_reference_period"].isin(["2020", "2021"])],
            "exposure_log1p",
        )
        specifications[f"P7_{component}_LAG1"] = (panel, "exposure_lag1")
    results: list[dict[str, Any]] = []
    robustness: list[dict[str, Any]] = []
    fits: dict[str, dict[str, Any] | None] = {}
    for fit_id in FAMILY_FITS[family]:
        specification, exposure = specifications[fit_id]
        component = "RURAL" if "RURAL" in fit_id else "AEE"
        try:
            fit = fit_fixed_effect_panel(
                specification,
                outcome="outcome_log1p",
                exposure=exposure,
                exact_cluster_sign_p=True,
            )
            if fit["municipality_count"] < 9 or fit["period_count"] < 8:
                raise AdvancedAnalysisValidationError("Cobertura abaixo do pré-registro.")
            fits[fit_id] = fit
            results.append(
                _panel_result_row(
                    question_id=question_id,
                    fit_id=fit_id,
                    fit=fit,
                    role="PRIMARY" if fit_id.endswith("_MAIN") else "SENSITIVITY",
                    family=family,
                    coverage_scope="VALE_10",
                    effect_unit="within_log1p_elasticity",
                    claim_ceiling="PLANNING_SIGNAL",
                    numerator_metric_id=component_specs[component][0],
                    numerator_lens="school_location",
                    denominator_metric_id=component_specs[component][1],
                    denominator_lens="school_location",
                )
            )
            robustness.append(
                {
                    "question_id": question_id,
                    "robustness_id": fit_id,
                    "state": "VALID",
                    "value": fit["coefficient"],
                    "unit": "within_log1p_elasticity",
                    "detail": _json_cell(fit["resampling"]),
                }
            )
        except (AdvancedAnalysisValidationError, np.linalg.LinAlgError) as error:
            fits[fit_id] = None
            results.append(
                _insufficient_result(
                    question_id=question_id,
                    result_id=fit_id,
                    method_id="TWO_WAY_FIXED_EFFECTS_EXACT_CLUSTER_SIGN_T",
                    coverage_scope="VALE_10",
                    claim_ceiling="PLANNING_SIGNAL",
                    family=family,
                    reason=str(error),
                    numerator_metric_id=component_specs[component][0],
                    numerator_lens="school_location",
                    denominator_metric_id=component_specs[component][1],
                    denominator_lens="school_location",
                )
            )
    loo_by_component: dict[str, list[float]] = {"RURAL": [], "AEE": []}
    for component, panel in panels.items():
        for excluded in sorted(vale_codes):
            try:
                fit = fit_fixed_effect_panel(
                    panel[panel["municipality_ibge_code"].ne(excluded)],
                    outcome="outcome_log1p",
                    exposure="exposure_log1p",
                    exact_cluster_sign_p=False,
                )
                loo_by_component[component].append(fit["coefficient"])
                state = "VALID"
                value = fit["coefficient"]
                failure_reason = ""
            except (AdvancedAnalysisValidationError, np.linalg.LinAlgError) as error:
                state = "INSUFFICIENT_DATA"
                value = None
                failure_reason = str(error)
            robustness.append(
                {
                    "question_id": question_id,
                    "robustness_id": f"P7_{component}_LEAVE_ONE_OUT",
                    "state": state,
                    "value": value,
                    "unit": "within_log1p_elasticity",
                    "detail": _json_cell(
                        {
                            "excludedMunicipalityIbgeCode": excluded,
                            "failureReason": failure_reason,
                        }
                    ),
                }
            )
    adjusted = _apply_bh_to_question_rows(results, family)
    component_validity: dict[str, bool] = {}
    stable_component: str | None = None
    for component in ("RURAL", "AEE"):
        component_fit_ids = (
            f"P7_{component}_MAIN",
            f"P7_{component}_EXCLUDE_2020_2021",
            f"P7_{component}_LAG1",
        )
        component_validity[component] = bool(
            all(fits[fit_id] is not None for fit_id in component_fit_ids)
            and len(loo_by_component[component]) >= 9
        )
        if not component_validity[component]:
            continue
        main_id = f"P7_{component}_MAIN"
        main = fits[main_id]
        main_row = next(row for row in results if row["result_id"] == main_id)
        if main is None:
            continue
        preserved_sensitivities = all(
            _sign(fits[fit_id]["coefficient"]) == _sign(main["coefficient"])  # type: ignore[index]
            for fit_id in component_fit_ids[1:]
        )
        preserved_loo = sum(
            _sign(value) == _sign(main["coefficient"])
            for value in loo_by_component[component]
        )
        if (
            abs(main["coefficient"]) >= 0.10
            and adjusted[main_id] is not None
            and adjusted[main_id] <= FAMILY_ALPHA[family]
            and _interval_excludes_zero(main_row)
            and preserved_sensitivities
            and preserved_loo >= 8
        ):
            stable_component = component
            break
    terminal = (
        "INSUFFICIENT_DATA"
        if not any(component_validity.values())
        else "PLANNING_SIGNAL_ONLY"
        if stable_component is not None
        else "NO_ROBUST_ASSOCIATION"
    )
    for row in results:
        row["terminal_state"] = terminal
    scope_rows: list[dict[str, Any]] = []
    heterogeneity: list[dict[str, Any]] = []
    for component, panel in panels.items():
        latest = panel[panel["year_or_reference_period"].eq("2025")]
        outcome_values = latest.dropna(subset=["outcome_raw"]).set_index(
            "municipality_ibge_code"
        )["outcome_raw"].to_dict()
        exposure_values = latest.dropna(subset=["exposure_raw"]).set_index(
            "municipality_ibge_code"
        )["exposure_raw"].to_dict()
        for label, values in (
            (f"{component}_ENROLLMENTS_2025", outcome_values),
            (f"{component}_SCHOOL_OR_SERVICE_COUNT_2025", exposure_values),
        ):
            scope_rows += _observed_scope_rows(
                question_id=question_id,
                measure_id=f"MUNICIPAL_MEDIAN_{label}",
                values_by_code=values,
                unit="count",
                coverage_scope="VALE_10",
                rs_available=False,
            )
            for code in sorted(vale_codes):
                heterogeneity.append(
                    {
                        "question_id": question_id,
                        "heterogeneity_id": label,
                        "municipality_ibge_code": code,
                        "scope_id": "VALE_10",
                        "value": values.get(code),
                        "unit": "count",
                        "state": "OBSERVED" if code in values else "UNAVAILABLE",
                    }
                )
    return {
        "results": results,
        "robustness": robustness,
        "heterogeneity": heterogeneity,
        "scope": scope_rows,
        "terminal": terminal,
        "claim_ceiling": "PLANNING_SIGNAL",
        "claim_detail": {
            "stableComponent": stable_component,
            "componentValidity": component_validity,
            "validLeaveOneOutCount": sum(len(values) for values in loo_by_component.values()),
            "lowPowerCaveatRequired": True,
        },
    }


def _p8_result_row(
    *,
    fit_id: str,
    fit: Mapping[str, Any],
    role: str,
) -> dict[str, Any]:
    multiplier = math.log(1.1)
    effect = fit["coefficient"] * multiplier
    return _result_row(
        question_id="P8_FINANCING_OFFER_AND_CAPACITY",
        result_id=fit_id,
        result_role=role,
        method_id="CROSS_SECTIONAL_OLS_HC3",
        coverage_scope="RS_497",
        municipality_count=fit["municipality_count"],
        period_count=1,
        effect=effect,
        effect_unit="full_time_share_pp_per_10_percent_higher_mde",
        interval_state="CONFIDENCE_INTERVAL",
        interval_lower=fit["interval_lower"] * multiplier,
        interval_upper=fit["interval_upper"] * multiplier,
        p_value_state="INFERENTIAL",
        p_value_raw=fit["p_value"],
        multiplicity_family="MF_P8_FINANCING_CAPACITY",
        robustness_state="VALID_FIT",
        claim_ceiling="CONTEXT_ADJUSTED_COMPARISON",
        numerator_metric_id="education.full_time_enrollments",
        numerator_lens="school_location",
        denominator_metric_id="finance.mde_applied_amount",
        denominator_lens="municipal_executor",
        coefficient_per_log_unit=fit["coefficient"],
        coefficient_standard_error_per_log_unit=fit["standard_error"],
        observation_count=fit["observation_count"],
        exact_effect_multiplier=multiplier,
    )


def analyze_p8(frame: pd.DataFrame) -> dict[str, Any]:
    question_id = "P8_FINANCING_OFFER_AND_CAPACITY"
    family = "MF_P8_FINANCING_CAPACITY"
    periods = ["2024", "2025"]
    full_time = _metric_panel_column(
        frame,
        "education.full_time_enrollments",
        stage="education_basic",
        periods=periods,
        coverage_scope="RS_497",
        column="full_time_enrollments",
    )
    enrollment = _metric_panel_column(
        frame,
        "education.enrollments",
        stage="education_basic",
        periods=periods,
        coverage_scope="RS_497",
        column="total_enrollments",
    )
    finance = _metric_panel_column(
        frame,
        "finance.mde_applied_amount",
        stage="municipal_education_finance",
        periods=periods,
        coverage_scope="RS_497",
        column="mde_amount",
        dimension_id="empenhado",
    )
    key = ["municipality_ibge_code", "year_or_reference_period"]
    panel = full_time.merge(enrollment, on=key, how="outer").merge(
        finance, on=key, how="outer"
    )
    panel["full_time_share"] = _safe_positive_denominator_ratio(
        panel["full_time_enrollments"],
        panel["total_enrollments"],
        multiplier=100.0,
    )
    panel["log_mde"] = np.where(panel["mde_amount"].gt(0), np.log(panel["mde_amount"]), np.nan)
    panel["log_enrollment"] = np.where(
        panel["total_enrollments"].gt(0), np.log(panel["total_enrollments"]), np.nan
    )
    panel["mde_per_enrollment"] = _safe_positive_denominator_ratio(
        panel["mde_amount"], panel["total_enrollments"]
    )
    panel["log_mde_per_enrollment"] = np.where(
        panel["mde_per_enrollment"].gt(0),
        np.log(panel["mde_per_enrollment"]),
        np.nan,
    )
    panel_2025 = panel[panel["year_or_reference_period"].eq("2025")].copy()
    panel_2024 = panel[panel["year_or_reference_period"].eq("2024")].copy()
    complete_2025 = panel_2025.dropna(
        subset=["full_time_share", "log_mde", "log_enrollment"]
    )
    lower_trim = complete_2025["log_mde"].quantile(0.01)
    upper_trim = complete_2025["log_mde"].quantile(0.99)
    trimmed_2025 = complete_2025[
        complete_2025["log_mde"].between(lower_trim, upper_trim, inclusive="both")
    ]
    specifications = {
        "P8_MAIN_2025_SIZE_ADJUSTED": (
            panel_2025,
            "log_mde",
            ("log_enrollment",),
        ),
        "P8_ALT_2024_SIZE_ADJUSTED": (
            panel_2024,
            "log_mde",
            ("log_enrollment",),
        ),
        "P8_ALT_2025_PER_ENROLLMENT": (
            panel_2025,
            "log_mde_per_enrollment",
            (),
        ),
        "P8_SENS_2025_TRIMMED_1_PERCENT": (
            trimmed_2025,
            "log_mde",
            ("log_enrollment",),
        ),
    }
    results: list[dict[str, Any]] = []
    robustness: list[dict[str, Any]] = []
    fits: dict[str, dict[str, Any] | None] = {}
    for fit_id in FAMILY_FITS[family]:
        specification, exposure, controls = specifications[fit_id]
        try:
            fit = fit_ols_hc3(
                specification,
                outcome="full_time_share",
                exposure=exposure,
                controls=controls,
            )
            if fit["municipality_count"] < 400:
                raise AdvancedAnalysisValidationError("Cobertura abaixo do pré-registro.")
            fits[fit_id] = fit
            results.append(
                _p8_result_row(
                    fit_id=fit_id,
                    fit=fit,
                    role="PRIMARY" if fit_id == "P8_MAIN_2025_SIZE_ADJUSTED" else "ALTERNATIVE_OR_SENSITIVITY",
                )
            )
            robustness.append(
                {
                    "question_id": question_id,
                    "robustness_id": fit_id,
                    "state": "VALID",
                    "value": fit["coefficient"] * math.log(1.1),
                    "unit": "full_time_share_pp_per_10_percent_higher_mde",
                    "detail": _json_cell(
                        {"municipalityCount": fit["municipality_count"]}
                    ),
                }
            )
        except (AdvancedAnalysisValidationError, np.linalg.LinAlgError) as error:
            fits[fit_id] = None
            results.append(
                _insufficient_result(
                    question_id=question_id,
                    result_id=fit_id,
                    method_id="CROSS_SECTIONAL_OLS_HC3",
                    coverage_scope="RS_497",
                    claim_ceiling="CONTEXT_ADJUSTED_COMPARISON",
                    family=family,
                    reason=str(error),
                    numerator_metric_id="education.full_time_enrollments",
                    numerator_lens="school_location",
                    denominator_metric_id="finance.mde_applied_amount",
                    denominator_lens="municipal_executor",
                )
            )
    main = fits["P8_MAIN_2025_SIZE_ADJUSTED"]
    nsr_residual = (
        main["residuals_by_municipality"].get(NOVA_SANTA_RITA_CODE)
        if main is not None
        else None
    )
    robustness.append(
        {
            "question_id": question_id,
            "robustness_id": "P8_NSR_CONTEXT_RESIDUAL_WITHOUT_P_VALUE",
            "state": "VALID" if nsr_residual is not None else "UNAVAILABLE",
            "value": nsr_residual,
            "unit": "full_time_share_percentage_points",
            "detail": _json_cell(
                {
                    "pValueState": "NOT_APPLICABLE_PREDECLARED",
                    "interpretation": "context_residual_not_inferential",
                }
            ),
        }
    )
    adjusted = _apply_bh_to_question_rows(results, family)
    all_valid = all(fit is not None for fit in fits.values()) and nsr_residual is not None
    supported = False
    if all_valid and main is not None:
        main_row = next(
            row for row in results if row["result_id"] == "P8_MAIN_2025_SIZE_ADJUSTED"
        )
        main_effect = main["coefficient"] * math.log(1.1)
        preserved = sum(
            _sign(fits[fit_id]["coefficient"]) == _sign(main["coefficient"])  # type: ignore[index]
            for fit_id in (
                "P8_ALT_2024_SIZE_ADJUSTED",
                "P8_ALT_2025_PER_ENROLLMENT",
                "P8_SENS_2025_TRIMMED_1_PERCENT",
            )
        )
        supported = bool(
            abs(main_effect) >= 0.10
            and adjusted["P8_MAIN_2025_SIZE_ADJUSTED"] is not None
            and adjusted["P8_MAIN_2025_SIZE_ADJUSTED"] <= FAMILY_ALPHA[family]
            and _interval_excludes_zero(main_row)
            and preserved >= 2
        )
    terminal = (
        "INSUFFICIENT_DATA"
        if not all_valid
        else "CONTEXT_COMPARISON_COMPLETE"
        if supported
        else "NO_ROBUST_ASSOCIATION"
    )
    for row in results:
        row["terminal_state"] = terminal
    latest = panel_2025
    full_time_by_code = latest.dropna(subset=["full_time_share"]).set_index(
        "municipality_ibge_code"
    )["full_time_share"].to_dict()
    finance_by_code = latest.dropna(subset=["mde_per_enrollment"]).set_index(
        "municipality_ibge_code"
    )["mde_per_enrollment"].to_dict()
    scope_rows = _observed_scope_rows(
        question_id=question_id,
        measure_id="MUNICIPAL_MEDIAN_FULL_TIME_ENROLLMENT_SHARE_2025",
        values_by_code=full_time_by_code,
        unit="percent",
        coverage_scope="RS_497",
    ) + _observed_scope_rows(
        question_id=question_id,
        measure_id="MUNICIPAL_MEDIAN_NOMINAL_MDE_PER_ENROLLMENT_2025",
        values_by_code=finance_by_code,
        unit="nominal_brl_per_enrollment",
        coverage_scope="RS_497",
    )
    vale_codes = set(_vale_codes())
    heterogeneity = []
    for code in sorted(set(full_time_by_code) | set(finance_by_code)):
        for measure, values, unit in (
            ("FULL_TIME_ENROLLMENT_SHARE_2025", full_time_by_code, "percent"),
            (
                "NOMINAL_MDE_PER_ENROLLMENT_2025",
                finance_by_code,
                "nominal_brl_per_enrollment",
            ),
        ):
            heterogeneity.append(
                {
                    "question_id": question_id,
                    "heterogeneity_id": measure,
                    "municipality_ibge_code": code,
                    "scope_id": "VALE_10" if code in vale_codes else "RS_NON_VALE",
                    "value": values.get(code),
                    "unit": unit,
                    "state": "OBSERVED" if code in values else "UNAVAILABLE",
                }
            )
    return {
        "results": results,
        "robustness": robustness,
        "heterogeneity": heterogeneity,
        "scope": scope_rows,
        "terminal": terminal,
        "claim_ceiling": "CONTEXT_ADJUSTED_COMPARISON",
        "claim_detail": {
            "mainEffect": (
                main["coefficient"] * math.log(1.1) if main is not None else None
            ),
            "mainBhPValue": adjusted["P8_MAIN_2025_SIZE_ADJUSTED"],
            "nsrContextResidual": nsr_residual,
            "rulePassed": supported,
            "endogeneityCaveatRequired": True,
            "invalidFitIds": [
                fit_id for fit_id, fit in fits.items() if fit is None
            ],
        },
    }


def _artifact_records(output_dir: Path) -> list[dict[str, Any]]:
    return [
        {
            "path": name,
            "byteSize": (output_dir / name).stat().st_size,
            "sha256": sha256_file(output_dir / name),
        }
        for name in NON_MANIFEST_FILES
    ]


def _sha256_payload(payload: Any) -> str:
    encoded = (
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _artifact_set_digest(output_dir: Path) -> str:
    return _sha256_payload(_artifact_records(output_dir))


def _ordered_frame(
    rows: Sequence[Mapping[str, Any]],
    *,
    leading_columns: Sequence[str],
    sort_columns: Sequence[str],
) -> pd.DataFrame:
    frame = pd.DataFrame(rows)
    for column in leading_columns:
        if column not in frame.columns:
            frame[column] = None
    remaining = sorted(set(frame.columns) - set(leading_columns))
    frame = frame[[*leading_columns, *remaining]]
    if len(frame):
        frame = frame.sort_values(list(sort_columns), kind="mergesort").reset_index(
            drop=True
        )
    return frame


def _promotion_state_for_result(
    question_id: str,
    terminal_state: str,
    row: Mapping[str, Any],
) -> str:
    result_id = str(row["result_id"])
    if question_id == "P8_FINANCING_OFFER_AND_CAPACITY":
        if result_id == "P8_ALT_2025_PER_ENROLLMENT":
            return "BLOCKED_DENOMINATOR_CONSTRUCTION_AND_TERMINAL_INSUFFICIENT"
        return "BLOCKED_QUESTION_TERMINAL_INSUFFICIENT"
    if terminal_state in {"INSUFFICIENT_DATA", "NOT_SUPPORTED_OR_UNAVAILABLE"}:
        return "BLOCKED_QUESTION_TERMINAL_STATE"
    role = str(row["result_role"])
    if role.startswith("PRIMARY"):
        if terminal_state == "NO_ROBUST_ASSOCIATION":
            return "ELIGIBLE_ONLY_AS_NEGATIVE_OR_UNCERTAIN_FINDING"
        return "ELIGIBLE_WITH_CLAIM_CEILING"
    return "SUPPORTING_ONLY_NOT_INDEPENDENTLY_PROMOTABLE"


def _apply_interpretation_and_promotion_guards(
    analyses: Mapping[str, dict[str, Any]],
) -> None:
    """Acrescenta guardas pós-resultado sem alterar estimadores ou estados terminais."""

    clustered_questions = {
        "P3_SCHOOL_CONDITIONS_AND_TRAJECTORY",
        "P4_YOUTH_WORK_AND_HIGH_SCHOOL",
        "P7_RURALITY_INCLUSION_AND_ACCESS",
    }
    small_sample_questions = {
        "P4_YOUTH_WORK_AND_HIGH_SCHOOL",
        "P6_ADULT_SCHOOLING_WORK_AND_EJA",
        "P7_RURALITY_INCLUSION_AND_ACCESS",
    }
    negative_states = {
        "NO_ROBUST_ASSOCIATION",
        "NOT_SUPPORTED_OR_UNAVAILABLE",
        "INSUFFICIENT_DATA",
    }
    for question_id, analysis in analyses.items():
        terminal_state = str(analysis["terminal"])
        for row in analysis["results"]:
            observation_count = _finite_or_none(row.get("observation_count"))
            municipality_count = int(row["analytic_municipality_count"])
            row["analytic_sample_n"] = (
                int(observation_count)
                if observation_count is not None
                else municipality_count
            )
            if question_id in clustered_questions:
                row["cluster_count"] = municipality_count or None
                row["cluster_count_state"] = (
                    "OBSERVED" if municipality_count > 0 else "UNAVAILABLE"
                )
            else:
                row["cluster_count"] = None
                row["cluster_count_state"] = "NOT_APPLICABLE_TO_ESTIMATOR"

            if row["interval_state"] == "UNAVAILABLE":
                row["interval_primary_state"] = "UNAVAILABLE"
            elif question_id in {
                "P4_YOUTH_WORK_AND_HIGH_SCHOOL",
                "P7_RURALITY_INCLUSION_AND_ACCESS",
            }:
                row["interval_primary_state"] = (
                    "APPROXIMATE_NON_PRIMARY_EXACT_SIGN_P_PRIMARY"
                )
            elif question_id == "P6_ADULT_SCHOOLING_WORK_AND_EJA":
                row["interval_primary_state"] = (
                    "DESCRIPTIVE_NON_PRIMARY_PERMUTATION_P_PRIMARY"
                )
            else:
                row["interval_primary_state"] = "PRIMARY_WITHIN_PREREGISTERED_DESIGN"

            family = str(row["multiplicity_family"])
            row["multiplicity_family_members"] = _json_cell(
                list(FAMILY_FITS.get(family, ()))
            )
            if question_id in small_sample_questions:
                row["power_statement"] = "LOW_POWER_NO_ABSENCE_CLAIM"
            elif terminal_state in negative_states:
                row["power_statement"] = (
                    "NON_REJECTION_IS_NOT_EVIDENCE_OF_ABSENCE"
                )
            else:
                row["power_statement"] = "NOT_APPLICABLE_TO_DESIGN"
            row["minimum_detectable_effect_state"] = (
                "NOT_PREREGISTERED_NOT_COMPUTED"
            )
            row["promotion_state"] = _promotion_state_for_result(
                question_id, terminal_state, row
            )
            if question_id == "P1_CONTEXT_ADJUSTED_TRAJECTORY":
                row["interpretation_guard"] = (
                    "NON_FLAGGING_IS_NOT_EVIDENCE_OF_TYPICALITY"
                )
            elif question_id == "P7_RURALITY_INCLUSION_AND_ACCESS":
                row["interpretation_guard"] = (
                    "REPORT_RAW_EXACT_P_AND_CONSERVATIVE_PREREGISTERED_BH_TOGETHER"
                )
            elif row["result_id"] == "P8_ALT_2025_PER_ENROLLMENT":
                row["interpretation_guard"] = (
                    "SHARED_DENOMINATOR_AND_SIZE_CONFOUNDING_NO_INDEPENDENT_CLAIM"
                )
            elif question_id == "P8_FINANCING_OFFER_AND_CAPACITY":
                row["interpretation_guard"] = (
                    "QUESTION_TERMINAL_INSUFFICIENT_NO_INDEPENDENT_CLAIM"
                )
            else:
                row["interpretation_guard"] = (
                    "CLAIM_CEILING_AND_NO_AUTOMATIC_CAUSALITY"
                )

        for row in analysis["heterogeneity"]:
            row["claim_ceiling"] = "EXPLORATORY_NO_INFERENCE"
            row["promotion_state"] = "BLOCKED_FROM_MANAGER_FACING"
            row["inference_state"] = "NOT_APPLICABLE_EXPLORATORY"
            row["interpretation_guard"] = (
                "MUNICIPAL_HETEROGENEITY_REQUIRES_SEPARATE_PREREGISTRATION"
            )

        eligible = [
            row["result_id"]
            for row in analysis["results"]
            if str(row["promotion_state"]).startswith("ELIGIBLE")
        ]
        blocked = [
            row["result_id"]
            for row in analysis["results"]
            if str(row["promotion_state"]).startswith("BLOCKED")
        ]
        supporting = [
            row["result_id"]
            for row in analysis["results"]
            if str(row["promotion_state"]).startswith("SUPPORTING")
        ]
        analysis["promotion_policy"] = {
            "eligibleResultIds": eligible,
            "supportingOnlyResultIds": supporting,
            "blockedResultIds": blocked,
            "heterogeneityPromotionState": "BLOCKED_FROM_MANAGER_FACING",
            "downstreamClaimRegistryRequired": True,
        }

    p1 = analyses["P1_CONTEXT_ADJUSTED_TRAJECTORY"]
    p1_rows = {row["result_id"]: row for row in p1["results"]}
    p1_main = p1_rows.get("P1_MAIN_5F_FULL")
    p1_baseline = p1_rows.get("P1_ALT_5F_BASELINE_ONLY")
    if p1_main and p1_baseline and p1_main["effect_estimate"] is not None:
        main_rmse = float(p1_main["held_out_rmse"])
        baseline_rmse = float(p1_baseline["held_out_rmse"])
        band = max(
            abs(float(p1_main["interval_lower"])),
            abs(float(p1_main["interval_upper"])),
        )
        effects = [
            float(row["effect_estimate"])
            for row in p1_rows.values()
            if row["effect_estimate"] is not None
        ]
        p1["claim_detail"].update(
            {
                "incrementalOutOfSampleSkill": main_rmse < baseline_rmse,
                "fullMinusBaselineRmse": main_rmse - baseline_rmse,
                "mainResidualToPredictionBandRatio": (
                    abs(float(p1_main["effect_estimate"])) / band if band else None
                ),
                "registeredResidualSigns": [_sign(value) for value in effects],
                "allRegisteredResidualSignsPositive": all(value > 0 for value in effects),
                "nonFlaggingIsEvidenceOfTypicality": False,
                "interpretationGuard": (
                    "O resíduo municipal é positivo nos três ajustes, mas permanece "
                    "dentro de uma banda ampla; o modelo completo não melhora o RMSE "
                    "do baseline. Não ser sinalizado não demonstra tipicidade."
                ),
            }
        )

    p2 = analyses["P2_DEMOGRAPHY_ENROLLMENT_DECOMPOSITION"]
    p2["claim_detail"].update(
        {
            "populationSeriesProvenance": dict(POPULATION_SOURCE_PROVENANCE),
            "relationshipComponentGuard": (
                "Resíduo da identidade contábil; pode absorver organização territorial, "
                "mobilidade, cobertura e revisões ou rebases da série populacional."
            ),
            "behavioralEffectInterpretationAllowed": False,
        }
    )

    p5 = analyses["P5_OCCUPATIONS_AND_EPT"]
    p5["claim_detail"].update(
        {
            "occupationMappingGranularity": "CBO_TWO_DIGIT_SUBGROUP",
            "fourDigitSensitivityState": "NOT_SUPPORTED_BY_FROZEN_BRIDGE",
            "granularityGuard": (
                "A granularidade de dois dígitos impõe um teto de correspondência; "
                "não autoriza inferência ocupacional fina."
            ),
        }
    )

    p7 = analyses["P7_RURALITY_INCLUSION_AND_ACCESS"]
    p7_rows = {row["result_id"]: row for row in p7["results"]}
    rural_ids = (
        "P7_RURAL_MAIN",
        "P7_RURAL_EXCLUDE_2020_2021",
        "P7_RURAL_LAG1",
    )
    if all(result_id in p7_rows for result_id in rural_ids):
        rural_rows = [p7_rows[result_id] for result_id in rural_ids]
        main = p7_rows["P7_RURAL_MAIN"]
        p7["claim_detail"].update(
            {
                "multiplicityFamilyId": "MF_P7_RURALITY_INCLUSION",
                "multiplicityFamilyMembers": list(
                    FAMILY_FITS["MF_P7_RURALITY_INCLUSION"]
                ),
                "ruralMainRawExactPValue": main["p_value_raw"],
                "ruralMainBhPValue": main["p_value_bh"],
                "familyDecisionAlpha": FAMILY_ALPHA["MF_P7_RURALITY_INCLUSION"],
                "ruralSensitivitySignsMatchMain": all(
                    _sign(row["effect_estimate"])
                    == _sign(main["effect_estimate"])
                    for row in rural_rows[1:]
                ),
                "adjustmentInterpretation": (
                    "NOT_SIGNIFICANT_AFTER_CONSERVATIVE_PREREGISTERED_FAMILY_ADJUSTMENT"
                ),
                "absenceClaimAllowed": False,
            }
        )

    p8 = analyses["P8_FINANCING_OFFER_AND_CAPACITY"]
    p8["claim_detail"].update(
        {
            "perEnrollmentAlternativeIndependentPromotionAllowed": False,
            "perEnrollmentAlternativeGuard": (
                "O denominador de matrículas também participa do desfecho e captura "
                "escala; a associação alternativa não pode ser promovida isoladamente."
            ),
            "nominalFinanceCrossYearComparisonAllowed": False,
            "allIndependentPromotionBlocked": True,
        }
    )


def _claim_caveats(question_id: str) -> list[str]:
    common = "Associação territorial/ecológica não identifica causalidade individual."
    return {
        "P1_CONTEXT_ADJUSTED_TRAJECTORY": [
            common,
            "A comparação depende de calibração fora da amostra e não atribui causa aos fatores contextuais.",
            "O modelo completo não melhorou o RMSE do baseline; permanecer dentro de uma banda ampla não demonstra que o município seja típico.",
        ],
        "P2_DEMOGRAPHY_ENROLLMENT_DECOMPOSITION": [
            "A razão entre matrícula por local da escola e população residente é contexto territorial, não taxa de cobertura ou frequência.",
            "A vintage e a sensibilidade a rebase não são recuperáveis do snapshot congelado; o componente residual também pode absorver revisões da série populacional.",
        ],
        "P3_SCHOOL_CONDITIONS_AND_TRAJECTORY": [
            common,
            "Efeitos fixos removem fatores invariantes e choques anuais comuns, mas não eliminam confundimento variável no tempo.",
        ],
        "P4_YOUTH_WORK_AND_HIGH_SCHOOL": [
            common,
            "Com dez municípios, não rejeitar a hipótese nula não distingue ausência de relação de baixa potência estatística.",
            "Vínculos por local de trabalho e população residente não formam uma taxa individual de emprego.",
        ],
        "P5_OCCUPATIONS_AND_EPT": [
            "A correspondência normativa curso-CBO não mede empregabilidade, demanda futura, suficiência nem qualidade da oferta.",
            "O mapeamento está no subgrupo CBO de dois dígitos; a ponte congelada não sustenta sensibilidade ocupacional a quatro dígitos.",
        ],
        "P6_ADULT_SCHOOLING_WORK_AND_EJA": [
            common,
            "Com até dez municípios, intervalos bootstrap são descritivos e não rejeição pode refletir baixa potência.",
        ],
        "P7_RURALITY_INCLUSION_AND_ACCESS": [
            common,
            "Contagens de escolas ou serviços não medem suficiência, distância, capacidade ou qualidade do acesso.",
            "Com dez municípios, não rejeição pode refletir baixa potência.",
            "O p exato rural bruto é reportado junto do BH conservador pré-registrado; o resultado não foi significativo após esse ajuste familiar.",
        ],
        "P8_FINANCING_OFFER_AND_CAPACITY": [
            "Financiamento e oferta são determinados conjuntamente; causalidade reversa e necessidades omitidas permanecem plausíveis.",
            "Valores financeiros são nominais; comparação entre anos é proibida e os coeficientes de 2024 e 2025 são estimados separadamente.",
            "A alternativa por matrícula compartilha o denominador com o desfecho e captura escala; ela não pode ser promovida isoladamente.",
        ],
    }[question_id]


def _build_claims(
    analyses: Mapping[str, Mapping[str, Any]],
    scope_rows: pd.DataFrame,
) -> dict[str, Any]:
    claims = []
    negative_states = {
        "NO_ROBUST_ASSOCIATION",
        "NOT_SUPPORTED_OR_UNAVAILABLE",
        "INSUFFICIENT_DATA",
    }
    for question_id in QUESTION_IDS:
        analysis = analyses[question_id]
        question_scope = scope_rows[scope_rows["question_id"].eq(question_id)]
        scope_availability = {
            scope_id: {
                row["measure_id"]: row["scope_state"]
                for _, row in question_scope[
                    question_scope["scope_id"].eq(scope_id)
                ].iterrows()
            }
            for scope_id in ("RS_497", "VALE_10", "MUNICIPALITY_4313375")
        }
        caveats = _claim_caveats(question_id)
        rs_valid_counts = [
            int(row["analytic_municipality_count"])
            for row in analysis["results"]
            if row["coverage_scope"] == "RS_497"
            and row["effect_estimate"] is not None
            and 0 < int(row["analytic_municipality_count"]) < 497
        ]
        if rs_valid_counts:
            caveats.append(
                "A cobertura de origem é RS_497, mas a amostra analítica válida não é "
                f"exaustiva (entre {min(rs_valid_counts)} e {max(rs_valid_counts)} "
                "municípios conforme o ajuste); não representa todos os 497 casos."
            )
        claims.append(
            {
                "questionId": question_id,
                "terminalState": analysis["terminal"],
                "claimCeiling": analysis["claim_ceiling"],
                "effectSummary": analysis["claim_detail"],
                "uncertaintySummary": {
                    "source": RESULTS_FILE,
                    "rule": "effect_and_interval_or_bound_before_p_value",
                },
                "robustnessSummary": {
                    "source": ROBUSTNESS_FILE,
                    "terminalRuleApplied": True,
                },
                "promotionPolicy": analysis["promotion_policy"],
                "scopeAvailability": scope_availability,
                "negativeFinding": analysis["terminal"] in negative_states,
                "mandatoryCaveats": caveats,
            }
        )
    return {
        "schemaVersion": "vocacoes-pne-aa2-claims-v1",
        "programId": "vocacoes-pne-advanced-analytics-v1",
        "stage": "AA2",
        "generatedAt": GENERATED_AT,
        "publicNarrativeAllowed": False,
        "promotionPolicy": {
            "managerFacingPromotionRequiresDownstreamClaimRegistry": True,
            "heterogeneityArtifact": HETEROGENEITY_FILE,
            "heterogeneityPromotionState": "BLOCKED_FROM_MANAGER_FACING",
            "nonPrimaryResultsIndependentPromotionAllowed": False,
            "multiplicityFamilyRegistry": {
                family: list(fit_ids) for family, fit_ids in FAMILY_FITS.items()
            },
        },
        "questionCount": len(claims),
        "claims": claims,
    }


def _quality_checks(
    results: pd.DataFrame,
    robustness: pd.DataFrame,
    heterogeneity: pd.DataFrame,
    scope: pd.DataFrame,
    claims: Mapping[str, Any],
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []

    def record(control_id: str, passed: bool, detail: Any) -> None:
        checks.append(
            {
                "controlId": control_id,
                "passed": bool(passed),
                "detail": detail,
            }
        )

    record(
        "AA2_QUESTION_COUNT_EXACT",
        set(results["question_id"]) == set(QUESTION_IDS),
        sorted(results["question_id"].unique().tolist()),
    )
    record(
        "AA2_RESULT_REQUIRED_FIELDS",
        set(RESULT_REQUIRED_FIELDS).issubset(results.columns),
        sorted(set(RESULT_REQUIRED_FIELDS) - set(results.columns)),
    )
    valid_results = results[results["effect_estimate"].notna()]
    clustered_results = valid_results[
        valid_results["cluster_count_state"].eq("OBSERVED")
    ]
    record(
        "AA2_EXPLICIT_SAMPLE_CLUSTER_AND_INTERVAL_PRIMACY",
        valid_results["analytic_sample_n"].gt(0).all()
        and clustered_results["cluster_count"].gt(0).all()
        and results["interval_primary_state"].ne("").all(),
        {
            "validResultCount": int(len(valid_results)),
            "clusteredResultCount": int(len(clustered_results)),
        },
    )
    terminal_counts = results.groupby("question_id")["terminal_state"].nunique()
    record(
        "AA2_ONE_TERMINAL_STATE_PER_QUESTION",
        len(terminal_counts) == 8 and terminal_counts.eq(1).all(),
        terminal_counts.to_dict(),
    )
    family_rows = results[results["multiplicity_family"].ne("")]
    family_counts = family_rows.groupby("multiplicity_family")["result_id"].nunique()
    record(
        "AA2_FIXED_MULTIPLICITY_FAMILIES",
        all(
            family_counts.get(family, 0) == len(fit_ids)
            for family, fit_ids in FAMILY_FITS.items()
        )
        and len(family_rows) == 27,
        family_counts.to_dict(),
    )
    inferential = results[results["p_value_state"].eq("INFERENTIAL")]
    record(
        "AA2_ALL_INFERENTIAL_P_VALUES_BH_ADJUSTED",
        inferential["p_value_raw"].notna().all()
        and inferential["p_value_bh"].notna().all(),
        {"inferentialRowCount": int(len(inferential))},
    )
    insufficient_p = family_rows[family_rows["p_value_state"].eq("INSUFFICIENT_DATA")]
    record(
        "AA2_INVALID_FITS_KEEP_NULL_P_VALUES",
        insufficient_p["p_value_raw"].isna().all()
        and insufficient_p["p_value_bh"].isna().all(),
        {"invalidFitCount": int(len(insufficient_p))},
    )
    record(
        "AA2_EFFECT_AND_INTERVAL_OR_BOUND_PER_QUESTION",
        all(
            results.loc[results["question_id"].eq(question_id), "effect_estimate"]
            .notna()
            .any()
            and results.loc[
                results["question_id"].eq(question_id), "interval_state"
            ]
            .ne("UNAVAILABLE")
            .any()
            for question_id in QUESTION_IDS
        ),
        "checked_all_questions",
    )
    scope_counts = scope.groupby(["question_id", "measure_id"])["scope_id"].agg(
        lambda values: sorted(set(values))
    )
    required_scopes = ["MUNICIPALITY_4313375", "RS_497", "VALE_10"]
    record(
        "AA2_SCOPE_TRIAD_PER_MEASURE",
        len(scope_counts) > 0
        and all(value == required_scopes for value in scope_counts.tolist()),
        {"measureCount": int(len(scope_counts))},
    )
    record(
        "AA2_NOVA_SANTA_RITA_EVERY_QUESTION",
        set(
            scope.loc[
                scope["scope_id"].eq("MUNICIPALITY_4313375"), "question_id"
            ]
        )
        == set(QUESTION_IDS),
        "scope_rows_checked",
    )
    record(
        "AA2_UNAVAILABLE_SCOPE_MATERIALIZED",
        scope["scope_state"].isin(["AVAILABLE", "UNAVAILABLE"]).all()
        and (
            scope["scope_state"].eq("UNAVAILABLE")
            == scope["value"].isna()
        ).all(),
        scope["scope_state"].value_counts().to_dict(),
    )
    record(
        "AA2_CLAIMS_EXACT_AND_TECHNICAL",
        claims.get("questionCount") == 8
        and claims.get("publicNarrativeAllowed") is False
        and len(claims.get("claims", [])) == 8,
        {"questionCount": claims.get("questionCount")},
    )
    promotion_policy = claims.get("promotionPolicy", {})
    record(
        "AA2_MULTIPLICITY_REGISTRY_EXPLICIT",
        promotion_policy.get("multiplicityFamilyRegistry")
        == {family: list(fit_ids) for family, fit_ids in FAMILY_FITS.items()},
        sorted(promotion_policy.get("multiplicityFamilyRegistry", {})),
    )
    claim_rows = claims.get("claims", [])
    negative_states = {
        "NO_ROBUST_ASSOCIATION",
        "NOT_SUPPORTED_OR_UNAVAILABLE",
        "INSUFFICIENT_DATA",
    }
    record(
        "AA2_NEGATIVE_FLAG_MATCHES_TERMINAL_STATE",
        all(
            claim["negativeFinding"]
            == (claim["terminalState"] in negative_states)
            for claim in claim_rows
        ),
        {
            claim["questionId"]: claim["negativeFinding"]
            for claim in claim_rows
        },
    )
    attrition_questions = {
        question_id
        for question_id, group in results[
            results["coverage_scope"].eq("RS_497")
            & results["effect_estimate"].notna()
            & results["analytic_municipality_count"].between(1, 496)
        ].groupby("question_id")
        if len(group)
    }
    claims_by_question = {
        claim["questionId"]: claim for claim in claim_rows
    }
    record(
        "AA2_RS_ATTRITION_CAVEAT_WHEN_NONEXHAUSTIVE",
        all(
            any("não é exaustiva" in caveat for caveat in claims_by_question[q]["mandatoryCaveats"])
            for q in attrition_questions
        ),
        sorted(attrition_questions),
    )
    record(
        "AA2_ROBUSTNESS_EVERY_QUESTION",
        set(robustness["question_id"]) == set(QUESTION_IDS),
        sorted(robustness["question_id"].unique().tolist()),
    )
    record(
        "AA2_P5_EPT_BRIDGE_RECONCILED",
        bool(
            (
                robustness["robustness_id"]
                == "P5_EPT_PANEL_BRIDGE_RECONCILIATION"
            ).any()
        )
        and float(
            robustness.loc[
                robustness["robustness_id"]
                == "P5_EPT_PANEL_BRIDGE_RECONCILIATION",
                "value",
            ].iloc[0]
        )
        <= 1e-9,
        "municipal_EPT_totals_equal_bridge_offer_totals",
    )
    record(
        "AA2_HETEROGENEITY_EVERY_QUESTION",
        set(heterogeneity["question_id"]) == set(QUESTION_IDS),
        sorted(heterogeneity["question_id"].unique().tolist()),
    )
    record(
        "AA2_HETEROGENEITY_EXPLORATORY_AND_PROMOTION_BLOCKED",
        heterogeneity["claim_ceiling"].eq("EXPLORATORY_NO_INFERENCE").all()
        and heterogeneity["promotion_state"]
        .eq("BLOCKED_FROM_MANAGER_FACING")
        .all()
        and heterogeneity["inference_state"]
        .eq("NOT_APPLICABLE_EXPLORATORY")
        .all(),
        {"rowCount": int(len(heterogeneity))},
    )
    p8_per_enrollment = results[
        results["result_id"].eq("P8_ALT_2025_PER_ENROLLMENT")
    ]
    record(
        "AA2_P8_PER_ENROLLMENT_INDEPENDENT_PROMOTION_BLOCKED",
        len(p8_per_enrollment) == 1
        and p8_per_enrollment["promotion_state"]
        .eq("BLOCKED_DENOMINATOR_CONSTRUCTION_AND_TERMINAL_INSUFFICIENT")
        .all(),
        p8_per_enrollment["promotion_state"].tolist(),
    )
    p1_claim = next(
        claim
        for claim in claims["claims"]
        if claim["questionId"] == "P1_CONTEXT_ADJUSTED_TRAJECTORY"
    )
    record(
        "AA2_P1_NON_FLAGGING_NOT_PROMOTED_AS_TYPICALITY",
        p1_claim["effectSummary"].get("nonFlaggingIsEvidenceOfTypicality") is False
        and p1_claim["effectSummary"].get("incrementalOutOfSampleSkill") is False,
        {
            "nonFlaggingIsEvidenceOfTypicality": p1_claim["effectSummary"].get(
                "nonFlaggingIsEvidenceOfTypicality"
            ),
            "incrementalOutOfSampleSkill": p1_claim["effectSummary"].get(
                "incrementalOutOfSampleSkill"
            ),
        },
    )
    p7_claim = next(
        claim
        for claim in claims["claims"]
        if claim["questionId"] == "P7_RURALITY_INCLUSION_AND_ACCESS"
    )
    record(
        "AA2_P7_CONSERVATIVE_FAMILY_ADJUSTMENT_DISCLOSED",
        p7_claim["effectSummary"].get("adjustmentInterpretation")
        == "NOT_SIGNIFICANT_AFTER_CONSERVATIVE_PREREGISTERED_FAMILY_ADJUSTMENT"
        and p7_claim["effectSummary"].get("absenceClaimAllowed") is False,
        p7_claim["effectSummary"].get("multiplicityFamilyMembers"),
    )
    p2_claim = next(
        claim
        for claim in claims["claims"]
        if claim["questionId"] == "P2_DEMOGRAPHY_ENROLLMENT_DECOMPOSITION"
    )
    record(
        "AA2_P2_POPULATION_VINTAGE_LIMIT_DISCLOSED",
        p2_claim["effectSummary"]
        .get("populationSeriesProvenance", {})
        .get("vintageState")
        == "UNRESOLVED_IN_FROZEN_LOCAL_SNAPSHOT"
        and p2_claim["effectSummary"].get("behavioralEffectInterpretationAllowed")
        is False,
        p2_claim["effectSummary"].get("populationSeriesProvenance", {}),
    )
    record(
        "AA2_NO_NUMERIC_IBGE_COERCION",
        heterogeneity["municipality_ibge_code"]
        .astype(str)
        .map(lambda value: len(value) == 7 and value.isdigit())
        .all(),
        {"rowCount": int(len(heterogeneity))},
    )
    forbidden = ("taxa de cobertura", "coverage rate", "taxa de emprego", "employment rate")
    composite_text = " ".join(results["composite_qualifier"].fillna("").astype(str)).lower()
    record(
        "AA2_DUAL_LENS_FORBIDDEN_LABELS_ABSENT",
        not any(token in composite_text for token in forbidden),
        "composite_qualifier_checked",
    )
    record(
        "AA2_NEGATIVE_OR_UNAVAILABLE_RETAINED",
        any(
            claim["negativeFinding"] is True
            for claim in claims.get("claims", [])
        )
        or results["availability_reason"].ne("").any(),
        "negative_and_unavailable_outputs_not_filtered",
    )
    return checks


def build_analysis_package() -> dict[str, Any]:
    panel, input_hashes = load_registered_panel_values()
    analyzers = (
        analyze_p1,
        analyze_p2,
        analyze_p3,
        analyze_p4,
        analyze_p5,
        analyze_p6,
        analyze_p7,
        analyze_p8,
    )
    analyses: dict[str, dict[str, Any]] = {}
    for analyzer in analyzers:
        analysis = analyzer(panel)
        question_id = analysis["results"][0]["question_id"]
        if question_id in analyses:
            raise AdvancedAnalysisValidationError(
                f"Pergunta AA2 duplicada no executor: {question_id}"
            )
        analyses[question_id] = analysis
    if set(analyses) != set(QUESTION_IDS):
        raise AdvancedAnalysisValidationError("Executor AA2 não produziu as oito perguntas.")
    _apply_interpretation_and_promotion_guards(analyses)
    results = _ordered_frame(
        [row for analysis in analyses.values() for row in analysis["results"]],
        leading_columns=RESULT_REQUIRED_FIELDS,
        sort_columns=("question_id", "result_id"),
    )
    robustness = _ordered_frame(
        [row for analysis in analyses.values() for row in analysis["robustness"]],
        leading_columns=(
            "question_id",
            "robustness_id",
            "state",
            "value",
            "unit",
            "detail",
        ),
        sort_columns=("question_id", "robustness_id", "detail"),
    )
    heterogeneity = _ordered_frame(
        [row for analysis in analyses.values() for row in analysis["heterogeneity"]],
        leading_columns=(
            "question_id",
            "heterogeneity_id",
            "municipality_ibge_code",
            "scope_id",
            "value",
            "unit",
            "state",
            "claim_ceiling",
            "promotion_state",
            "inference_state",
            "interpretation_guard",
        ),
        sort_columns=(
            "question_id",
            "heterogeneity_id",
            "municipality_ibge_code",
        ),
    )
    scope = _ordered_frame(
        [row for analysis in analyses.values() for row in analysis["scope"]],
        leading_columns=(
            "question_id",
            "measure_id",
            "scope_id",
            "scope_state",
            "value",
            "unit",
            "municipality_count",
            "coverage_scope",
            "unavailability_reason",
        ),
        sort_columns=("question_id", "measure_id", "scope_id"),
    )
    claims = _build_claims(analyses, scope)
    checks = _quality_checks(results, robustness, heterogeneity, scope, claims)
    failures = [check for check in checks if check["passed"] is not True]
    qa = {
        "schemaVersion": "vocacoes-pne-aa2-qa-v1",
        "programId": "vocacoes-pne-advanced-analytics-v1",
        "stage": "AA2",
        "generatedAt": GENERATED_AT,
        "controlCount": len(checks),
        "failedCount": len(failures),
        "checks": checks,
        "counts": {
            "questionCount": len(analyses),
            "resultRowCount": len(results),
            "robustnessRowCount": len(robustness),
            "heterogeneityRowCount": len(heterogeneity),
            "scopeComparisonRowCount": len(scope),
            "inferentialPValueCount": int(
                results["p_value_state"].eq("INFERENTIAL").sum()
            ),
            "predeclaredPValueSlotCount": int(
                results["multiplicity_family"].ne("").sum()
            ),
            "terminalStateCounts": results.drop_duplicates("question_id")[
                "terminal_state"
            ].value_counts().to_dict(),
        },
        "inputHashes": input_hashes,
    }
    if failures:
        raise AdvancedAnalysisValidationError(
            "Controles AA2 falharam: "
            + ", ".join(check["controlId"] for check in failures)
        )
    return {
        "results": results,
        "robustness": robustness,
        "heterogeneity": heterogeneity,
        "scope": scope,
        "claims": claims,
        "qa": qa,
        "input_hashes": input_hashes,
    }


def materialize_package(
    output_dir: Path,
    *,
    external_io_guarded: bool,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=False)
    bundle = build_analysis_package()
    write_csv_gzip(output_dir / RESULTS_FILE, bundle["results"])
    write_csv_gzip(output_dir / ROBUSTNESS_FILE, bundle["robustness"])
    write_csv_gzip(output_dir / HETEROGENEITY_FILE, bundle["heterogeneity"])
    write_csv_gzip(output_dir / SCOPE_COMPARISONS_FILE, bundle["scope"])
    atomic_write_json(output_dir / CLAIMS_FILE, bundle["claims"])
    atomic_write_json(output_dir / QA_FILE, bundle["qa"])
    artifacts = _artifact_records(output_dir)
    implementation_paths = [
        CONTRACT_PATH,
        PREREGISTRATION_PATH,
        PREREGISTRATION_FREEZE_PATH,
        Path(__file__).resolve(),
        RUNNER_PATH,
    ]
    manifest = {
        "schemaVersion": "vocacoes-pne-aa2-manifest-v1",
        "programId": "vocacoes-pne-advanced-analytics-v1",
        "stage": "AA2",
        "generatedAt": GENERATED_AT,
        "finalState": "AA2_ANALYTICAL_RESULTS_READY_FOR_VALIDATION",
        "classification": "DATA_LOGIC",
        "artifacts": artifacts,
        "artifactSetDigestSha256": _sha256_payload(artifacts),
        "inputHashes": bundle["input_hashes"],
        "implementationFiles": [
            {
                "path": path.relative_to(REPO_ROOT).as_posix(),
                "byteSize": path.stat().st_size,
                "sha256": sha256_file(path),
            }
            for path in implementation_paths
        ],
        "runtime": {
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "pythonHashSeed": os.environ.get("PYTHONHASHSEED", "UNSET"),
        },
        "counts": bundle["qa"]["counts"],
        "publicDataIntegrity": {
            "beforeTreeDigestSha256": EXPECTED_PUBLIC_DATA_DIGEST,
            "afterTreeDigestSha256": EXPECTED_PUBLIC_DATA_DIGEST,
            "unchanged": True,
        },
        "generation": {
            "deterministic": True,
            "transactional": True,
            "manifestLast": True,
            "networkGuardEnabled": external_io_guarded,
            "databaseGuardEnabled": external_io_guarded,
            "networkUsed": False,
            "databaseUsed": False,
            "publicDataChanged": False,
            "fullBuildUsed": False,
        },
        "independentMaterializationVerification": {
            "state": "PENDING_RUNNER_COMPARISON",
            "equal": None,
            "artifactSetDigestSha256": None,
        },
    }
    atomic_write_json(output_dir / MANIFEST_FILE, manifest)
    return manifest


def materialize_single_candidate(output_dir: Path) -> dict[str, Any]:
    public_before = directory_content_digest(REPO_ROOT / "public/data")
    if public_before != EXPECTED_PUBLIC_DATA_DIGEST:
        raise AdvancedAnalysisValidationError(
            "public/data divergiu antes da materialização candidata AA2."
        )
    with blocked_external_io_guard():
        materialize_package(output_dir, external_io_guarded=True)
    gc.collect()
    public_after = directory_content_digest(REPO_ROOT / "public/data")
    if public_after != public_before:
        raise AdvancedAnalysisValidationError(
            "public/data mudou durante a materialização candidata AA2."
        )
    loaded_roots = {name.partition(".")[0] for name in sys.modules}
    return {
        "outputDir": output_dir.resolve().as_posix(),
        "artifactSetDigestSha256": _artifact_set_digest(output_dir),
        "candidateTreeDigestSha256": directory_content_digest(output_dir),
        "implementationSha256": sha256_file(Path(__file__).resolve()),
        "networkGuardEnabled": True,
        "databaseGuardEnabled": True,
        "loadedDatabaseClientModules": sorted(
            loaded_roots & DATABASE_CLIENT_MODULE_ROOTS
        ),
        "loadedNetworkClientModules": sorted(
            loaded_roots & NETWORK_CLIENT_MODULE_ROOTS
        ),
        "publicDataBeforeTreeDigestSha256": public_before,
        "publicDataAfterTreeDigestSha256": public_after,
    }


def _run_candidate_process(
    output_dir: Path, *, python_hash_seed: str
) -> dict[str, Any]:
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
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise AdvancedAnalysisValidationError(
            "Processo candidato AA2 falhou "
            f"(seed={python_hash_seed}, exit={completed.returncode}): "
            f"{completed.stderr.strip()}"
        )
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise AdvancedAnalysisValidationError(
            f"Saída candidata AA2 inválida (seed={python_hash_seed})."
        ) from error
    payload["pythonHashSeed"] = python_hash_seed
    payload["processMode"] = "FRESH_OS_PROCESS"
    return payload


def _finalize_determinism(
    output_dir: Path,
    digest: str,
    *,
    process_evidence: Sequence[Mapping[str, Any]],
) -> None:
    path = output_dir / MANIFEST_FILE
    manifest = _load_json(path)
    manifest["runtime"]["pythonHashSeed"] = "MULTI_PROCESS_FINALIZED"
    manifest["runtime"]["pythonHashSeeds"] = ["101", "202"]
    manifest["independentMaterializationVerification"] = {
        "state": "VERIFIED_IDENTICAL",
        "equal": True,
        "artifactSetDigestSha256": digest,
        "comparisonScope": "NON_MANIFEST_ANALYTICAL_ARTIFACT_SET",
        "candidateManifestEqualityRequired": False,
        "candidateManifestDifferenceReason": (
            "Cada manifesto candidato registra seu PYTHONHASHSEED operacional; "
            "o manifesto final normaliza os dois processos em evidência comum."
        ),
        "finalManifestNormalization": "MULTI_PROCESS_COMMON_EVIDENCE",
        "processIsolation": "TWO_FRESH_OPERATING_SYSTEM_PROCESSES",
        "processCount": len(process_evidence),
        "processEvidence": list(process_evidence),
    }
    atomic_write_json(path, manifest)


def _replace_directory_transactionally(staging: Path, target: Path) -> bool:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and directory_content_digest(staging) == directory_content_digest(target):
        return False
    rollback = target.with_name(f".{target.name}.rollback-aa2")
    if rollback.exists():
        shutil.rmtree(rollback)
    moved_existing = False
    try:
        if target.exists():
            os.replace(target, rollback)
            moved_existing = True
        os.replace(staging, target)
    except Exception:
        if moved_existing and rollback.exists() and not target.exists():
            os.replace(rollback, target)
        raise
    else:
        if rollback.exists():
            shutil.rmtree(rollback)
    return True


def validate_existing_output(
    output_dir: Path = DEFAULT_OUTPUT_ROOT,
    *,
    verify_sources: bool = True,
) -> dict[str, Any]:
    if not output_dir.is_dir():
        raise FileNotFoundError(f"Pacote AA2 ausente: {output_dir}")
    manifest = _load_json(output_dir / MANIFEST_FILE)
    if manifest.get("artifactSetDigestSha256") != _artifact_set_digest(output_dir):
        raise AdvancedAnalysisValidationError("Digest do conjunto AA2 divergente.")
    expected_names = list(NON_MANIFEST_FILES)
    if [artifact["path"] for artifact in manifest.get("artifacts", [])] != expected_names:
        raise AdvancedAnalysisValidationError("Lista de artefatos AA2 divergente.")
    for artifact in manifest["artifacts"]:
        path = output_dir / artifact["path"]
        if (
            path.stat().st_size != artifact["byteSize"]
            or sha256_file(path) != artifact["sha256"]
        ):
            raise AdvancedAnalysisValidationError(
                f"Artefato AA2 divergente: {artifact['path']}"
            )
    qa = _load_json(output_dir / QA_FILE)
    if qa.get("failedCount") != 0:
        raise AdvancedAnalysisValidationError("QA_SUMMARY_AA2 contém falhas.")
    claims = _load_json(output_dir / CLAIMS_FILE)
    if claims.get("questionCount") != 8:
        raise AdvancedAnalysisValidationError("CLAIMS_AA2 não contém oito perguntas.")
    verification = manifest.get("independentMaterializationVerification", {})
    if verification.get("state") != "VERIFIED_IDENTICAL":
        raise AdvancedAnalysisValidationError(
            "Pacote AA2 não comprova duas materializações idênticas."
        )
    if verify_sources:
        verify_preresult_inputs()
        if directory_content_digest(REPO_ROOT / "public/data") != EXPECTED_PUBLIC_DATA_DIGEST:
            raise AdvancedAnalysisValidationError("public/data divergiu na validação AA2.")
    return manifest


def materialize_twice_transactionally(
    output_dir: Path = DEFAULT_OUTPUT_ROOT,
) -> dict[str, Any]:
    public_before = directory_content_digest(REPO_ROOT / "public/data")
    if public_before != EXPECTED_PUBLIC_DATA_DIGEST:
        raise AdvancedAnalysisValidationError(
            "public/data divergiu antes da materialização AA2."
        )
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    first = Path(tempfile.mkdtemp(prefix=".aa2-first-", dir=output_dir.parent))
    second = Path(tempfile.mkdtemp(prefix=".aa2-second-", dir=output_dir.parent))
    shutil.rmtree(first)
    shutil.rmtree(second)
    try:
        first_result = _run_candidate_process(first, python_hash_seed="101")
        second_result = _run_candidate_process(second, python_hash_seed="202")
        first_digest = _artifact_set_digest(first)
        second_digest = _artifact_set_digest(second)
        if first_digest != second_digest:
            raise AdvancedAnalysisValidationError(
                "As duas materializações AA2 produziram conjuntos divergentes."
            )
        implementation_sha = sha256_file(Path(__file__).resolve())
        for candidate in (first_result, second_result):
            if candidate["implementationSha256"] != implementation_sha:
                raise AdvancedAnalysisValidationError(
                    "Processo candidato AA2 usou implementação divergente."
                )
            if (
                candidate["networkGuardEnabled"] is not True
                or candidate["databaseGuardEnabled"] is not True
                or candidate["loadedDatabaseClientModules"]
                or candidate["loadedNetworkClientModules"]
            ):
                raise AdvancedAnalysisValidationError(
                    "Processo candidato AA2 não preservou as guardas externas."
                )
            if (
                candidate["publicDataBeforeTreeDigestSha256"] != public_before
                or candidate["publicDataAfterTreeDigestSha256"] != public_before
            ):
                raise AdvancedAnalysisValidationError(
                    "Processo candidato AA2 observou public/data divergente."
                )
        evidence = [
            {
                "processMode": candidate["processMode"],
                "pythonHashSeed": candidate["pythonHashSeed"],
                "implementationSha256": candidate["implementationSha256"],
                "candidateArtifactSetDigestSha256": candidate[
                    "artifactSetDigestSha256"
                ],
                "networkGuardEnabled": candidate["networkGuardEnabled"],
                "databaseGuardEnabled": candidate["databaseGuardEnabled"],
                "loadedDatabaseClientModules": candidate[
                    "loadedDatabaseClientModules"
                ],
                "loadedNetworkClientModules": candidate[
                    "loadedNetworkClientModules"
                ],
                "publicDataBeforeTreeDigestSha256": candidate[
                    "publicDataBeforeTreeDigestSha256"
                ],
                "publicDataAfterTreeDigestSha256": candidate[
                    "publicDataAfterTreeDigestSha256"
                ],
            }
            for candidate in (first_result, second_result)
        ]
        _finalize_determinism(first, first_digest, process_evidence=evidence)
        _finalize_determinism(second, second_digest, process_evidence=evidence)
        first_tree = directory_content_digest(first)
        second_tree = directory_content_digest(second)
        if first_tree != second_tree:
            raise AdvancedAnalysisValidationError(
                "As duas árvores AA2 divergiram após o manifesto final."
            )
        validate_existing_output(first, verify_sources=False)
        changed = _replace_directory_transactionally(first, output_dir)
        return {
            "outputDir": output_dir.resolve().as_posix(),
            "artifactSetDigestSha256": first_digest,
            "fullTreeDigestSha256": first_tree,
            "independentMaterializationsEqual": True,
            "processIsolation": "TWO_FRESH_OPERATING_SYSTEM_PROCESSES",
            "pythonHashSeeds": ["101", "202"],
            "networkGuardEnabled": True,
            "databaseGuardEnabled": True,
            "loadedDatabaseClientModules": [],
            "loadedNetworkClientModules": [],
            "publicDataTreeDigestSha256": public_before,
            "targetChanged": changed,
        }
    finally:
        if first.exists():
            shutil.rmtree(first)
        if second.exists():
            shutil.rmtree(second)
