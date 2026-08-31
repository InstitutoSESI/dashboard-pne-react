"""Conclusão analítica final do Job 5L, sem publicação ou autorização do Job 5M."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import tempfile
from typing import Any

import numpy as np
import pandas as pd
import requests

from src.vocacoes_pne_job2 import (
    directory_content_digest,
    sha256_file,
    write_csv_gzip,
    write_json,
)
import src.vocacoes_pne_job5l as job5l


REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = (
    REPO_ROOT / "data_pipeline" / "contracts" / "vocacoes-pne-v7-job5l-final.json"
)
DEFAULT_OUTPUT_ROOT = REPO_ROOT / ".tmp" / "vocacoes-pne" / "v7-job5l-final"
PREVIOUS_JOB5L_ROOT = REPO_ROOT / ".tmp" / "vocacoes-pne" / "v7-job5l"
JOB5J_ROOT = REPO_ROOT / ".tmp" / "vocacoes-pne" / "v7-job5j"
JOB5K_ROOT = REPO_ROOT / ".tmp" / "vocacoes-pne" / "v7-job5k"

GENERATED_AT = "2026-08-30T00:00:00-03:00"
FINAL_STATE = "JOB_5L_FINAL_READY_WITH_EXPLICIT_LIMITS_FOR_EXTERNAL_JUDGMENT"
NSR_CODE = "4313375"
REGION_ID = job5l.REGION_ID
IBGE_CODE_PATTERN = re.compile(r"^[0-9]{7}$")
INTERVAL_LEVEL = 0.90

PACKAGE_FILES = (
    "CHECKPOINT_JOB5L_FINAL_FOR_PRO.md",
    "CATALOGO_INSIGHTS_FINAIS_JOB5L.json",
    "MATRIZ_RESULTADOS_FINAIS_JOB5L.csv.gz",
    "MATRIZ_HETEROGENEIDADE_10_MUNICIPIOS_JOB5L_FINAL.csv.gz",
    "DOSSIE_FINAL_NOVA_SANTA_RITA_JOB5L.md",
    "DOSSIE_FINAL_VALE_DO_SINOS_JOB5L.md",
    "METODOS_VALIDACAO_PRECISAO_RECONCILIACAO_JOB5L_FINAL.md",
    "FONTES_CENSO_RAIS_E_LITERATURA_JOB5L_FINAL.json",
    "LIMITACOES_E_CLAIMS_JOB5L_FINAL.json",
    "QA_SUMMARY_JOB5L_FINAL.json",
    "ARTIFACT_INDEX_JOB5L_FINAL.json",
    "MANIFEST_JOB5L_FINAL.json",
)

INTERNAL_FILES = (
    "internal/CONTRATO_JOB5L_FINAL.json",
    "internal/EXECPLAN_JOB5L_FINAL.md",
    "internal/CENSO_2022_STATUS_ATUAL_JOB5L_FINAL.json",
    "internal/RESULTADOS_F1_JOB5L_FINAL.csv.gz",
    "internal/VALIDACAO_F1_JOB5L_FINAL.csv.gz",
    "internal/MODELOS_F1_JOB5L_FINAL.json",
    "internal/PAINEL_RAIS_JOB5L_FINAL.csv.gz",
    "internal/AUDITORIA_RAIS_JOB5L_FINAL.json",
    "internal/PAINEL_EJA_JOB5L_FINAL.csv.gz",
    "internal/PAINEL_F2_F5_JOB5L_FINAL.csv.gz",
    "internal/PROVA_ENTRADAS_CONGELADAS_JOB5L_FINAL.json",
)

HISTORY_FEATURES = (
    "lagged_outcome_value",
    "year_centered",
    "pandemic_caution_indicator",
)
CONTEXT_FEATURES = (
    *HISTORY_FEATURES,
    "log_total_population",
    "log_located_stage_enrollments",
    "population_15_17_share_percent",
    "rural_basic_enrollment_share_percent",
    "full_time_stage_share_percent",
    "average_basic_school_size",
    "internet_school_share_percent",
    "teacher_adequacy_percent",
    "inse_latest_available",
    "adult_fundamental_completion_share_2022",
    "adult_high_school_completion_share_2022",
)

CENSO_URLS = {
    "ftp_root": "https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/",
    "sample_microdata_expected_root": (
        "https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/Microdados/"
    ),
    "weighting_areas_expected_root": (
        "https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/Areas_de_Ponderacao/"
    ),
    "sample_documentation_expected_root": (
        "https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/Microdados/Documentacao/"
    ),
    "official_postponement_notice": (
        "https://www.ibge.gov.br/novo-portal-erramos/45278-adiamento-das-divulgacoes-"
        "censo-demografico-2022-microdados-da-amostra-e-censo-demografico-2022-"
        "areas-de-ponderacao.html"
    ),
    "official_updated_announcement": (
        "https://www.ibge.gov.br/pt/novo-portal-destaques/44938-ibge-divulgara-em-"
        "04-de-dezembro-censo-demografico-2022-microdados-da-amostra-e-censo-"
        "demografico-2022-areas-de-ponderacao.html?lang=pt-BR"
    ),
    "official_calendar": "https://www.ibge.gov.br/calendario/mensal.html",
    "official_censo_landing": (
        "https://www.ibge.gov.br/censos/censo-demografico/censo-2022.html"
    ),
    "official_product_landing": (
        "https://www.ibge.gov.br/estatisticas/sociais/trabalho/"
        "22827-censo-demografico-2022.html"
    ),
    "official_terms_of_use": (
        "https://www.ibge.gov.br/acesso-informacao/acoes-e-programas/"
        "politica-de-privacidade.html"
    ),
}

CENSO_SOURCE_ROLES = {
    "ftp_root": "official_download_index",
    "sample_microdata_expected_root": "expected_official_microdata_download_root",
    "weighting_areas_expected_root": "expected_official_weighting_areas_download_root",
    "sample_documentation_expected_root": "expected_official_package_documentation_root",
    "official_postponement_notice": "latest_official_postponement_notice",
    "official_updated_announcement": "latest_official_release_announcement",
    "official_calendar": "current_official_release_calendar",
    "official_censo_landing": "official_census_landing_page",
    "official_product_landing": "official_census_product_and_methodology_landing",
    "official_terms_of_use": "official_portal_terms_and_provenance_context",
}

CANDIDATE_REQUIRED_FIELDS = (
    "insight_id",
    "manager_question",
    "evidence_level",
    "analytical_state",
    "editorial_state",
    "education_outcome",
    "territorial_or_socioeconomic_dimension",
    "same_record",
    "same_person",
    "unit_of_analysis",
    "territorial_lens",
    "period",
    "universe",
    "method",
    "validation",
    "regional_result",
    "ten_municipality_heterogeneity",
    "selected_municipality_result",
    "nova_santa_rita_result",
    "context_adjusted_result",
    "precision_state",
    "literature_mechanism",
    "integrated_conclusion",
    "incremental_value_beyond_separate_charts",
    "planning_implication",
    "monitoring_indicators",
    "institutional_coordination",
    "allowed_claims",
    "forbidden_claims",
    "limitations",
    "recommended_visual",
    "manager_review_state",
)

SERVICE_LENS_AUDIT = (
    {
        "year": 2019,
        "scannedRows": 12_284_030,
        "frozenTotal": 39_225,
        "serviceLocationTotal": 26_300,
        "serviceLocationExactCells": 0,
        "establishmentLocationTotal": 39_225,
        "establishmentLocationExactCells": 20,
    },
    {
        "year": 2020,
        "scannedRows": 12_161_310,
        "frozenTotal": 37_995,
        "serviceLocationTotal": 26_584,
        "serviceLocationExactCells": 0,
        "establishmentLocationTotal": 37_995,
        "establishmentLocationExactCells": 20,
    },
    {
        "year": 2021,
        "scannedRows": 13_238_715,
        "frozenTotal": 44_667,
        "serviceLocationTotal": 31_682,
        "serviceLocationExactCells": 0,
        "establishmentLocationTotal": 44_667,
        "establishmentLocationExactCells": 20,
    },
    {
        "year": 2022,
        "scannedRows": 14_349_520,
        "frozenTotal": 46_407,
        "serviceLocationTotal": 47_327,
        "serviceLocationExactCells": 0,
        "establishmentLocationTotal": 46_407,
        "establishmentLocationExactCells": 20,
    },
)


class Job5LFinalValidationError(ValueError):
    """Falha fechada de contrato, fonte, análise ou pacote do Job 5L-final."""


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(
        path,
        compression="gzip" if path.suffix == ".gz" else "infer",
        dtype={
            "municipality_ibge_code": "string",
            "entity_id": "string",
            "municipality_code": "string",
        },
        low_memory=False,
    )


def _stable_frame(frame: pd.DataFrame, keys: Sequence[str]) -> pd.DataFrame:
    available = [key for key in keys if key in frame.columns]
    if not available:
        return frame.reset_index(drop=True)
    return frame.sort_values(available, kind="mergesort", na_position="last").reset_index(
        drop=True
    )


def _finite(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _safe_ratio(numerator: Any, denominator: Any, multiplier: float = 1.0) -> float | None:
    left = _finite(numerator)
    right = _finite(denominator)
    if left is None or right is None or right == 0:
        return None
    return left / right * multiplier


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return float(value) if math.isfinite(float(value)) else None
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if value is pd.NA:
        return None
    return value


def _atomic_write_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def acquire_censo_source_snapshot(source_dir: Path) -> dict[str, Any]:
    """Captura uma prova atual, oficial e imutável para o gate Censo."""

    source_dir.mkdir(parents=True, exist_ok=True)
    observed_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    records: list[dict[str, Any]] = []
    headers = {
        "User-Agent": "PNE-Municipal-source-audit/1.0 (+official-source-verification)",
        "Accept": "text/html,application/xhtml+xml,application/octet-stream;q=0.9,*/*;q=0.5",
    }
    for source_id, url in CENSO_URLS.items():
        response = requests.get(url, headers=headers, timeout=60, allow_redirects=True)
        body = response.content
        body_name = f"{source_id}.response.bin"
        body_path = source_dir / body_name
        _atomic_write_bytes(body_path, body)
        records.append(
            {
                "sourceId": source_id,
                "sourceRole": CENSO_SOURCE_ROLES[source_id],
                "requestedUrl": url,
                "finalUrl": response.url,
                "statusCode": int(response.status_code),
                "contentType": response.headers.get("Content-Type"),
                "httpDate": response.headers.get("Date"),
                "bodyFile": body_name,
                "bodyByteSize": len(body),
                "bodySha256": hashlib.sha256(body).hexdigest(),
            }
        )
    manifest = {
        "schemaVersion": "vocacoes-pne-job5l-final-censo-live-source-manifest-v2",
        "observedAtUtc": observed_at,
        "authority": "IBGE",
        "officialDomainsOnly": True,
        "availabilityPolicy": (
            "announcement_is_insufficient; data files, weighting areas and package "
            "documentation must all be directly accessible"
        ),
        "records": records,
    }
    write_json(source_dir / "manifest.json", manifest)
    return manifest


def validate_censo_source_snapshot(source_dir: Path) -> dict[str, Any]:
    manifest_path = source_dir / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Manifesto Censo atual ausente: {manifest_path}")
    manifest = _json(manifest_path)
    if not manifest.get("officialDomainsOnly"):
        raise Job5LFinalValidationError("Snapshot Censo contém autoridade não oficial")
    expected_ids = set(CENSO_URLS)
    records = {record["sourceId"]: record for record in manifest["records"]}
    if set(records) != expected_ids:
        raise Job5LFinalValidationError("Snapshot Censo não cobre todos os endpoints oficiais")
    for source_id, record in records.items():
        if record["requestedUrl"] != CENSO_URLS[source_id]:
            raise Job5LFinalValidationError(f"URL Censo divergente: {source_id}")
        if record.get("sourceRole") != CENSO_SOURCE_ROLES[source_id]:
            raise Job5LFinalValidationError(f"Papel da fonte Censo divergente: {source_id}")
        path = source_dir / record["bodyFile"]
        if not path.is_file():
            raise FileNotFoundError(f"Resposta Censo ausente: {path}")
        if path.stat().st_size != record["bodyByteSize"]:
            raise Job5LFinalValidationError(f"Tamanho Censo divergente: {source_id}")
        if sha256_file(path) != record["bodySha256"]:
            raise Job5LFinalValidationError(f"Hash Censo divergente: {source_id}")
    return manifest


def build_censo_status(source_dir: Path) -> dict[str, Any]:
    manifest = validate_censo_source_snapshot(source_dir)
    records = {record["sourceId"]: record for record in manifest["records"]}
    ftp_body = (source_dir / records["ftp_root"]["bodyFile"]).read_bytes().decode(
        "utf-8", errors="replace"
    )
    root_has_candidate_entry = bool(re.search(r"microdad|pondera", ftp_body, re.I))
    micro_status = records["sample_microdata_expected_root"]["statusCode"]
    weight_status = records["weighting_areas_expected_root"]["statusCode"]
    documentation_status = records["sample_documentation_expected_root"]["statusCode"]
    def response_text(source_id: str) -> str:
        record = records[source_id]
        return (source_dir / record["bodyFile"]).read_bytes().decode(
            "utf-8", errors="replace"
        )

    micro_body = response_text("sample_microdata_expected_root")
    weight_body = response_text("weighting_areas_expected_root")
    documentation_body = response_text("sample_documentation_expected_root")
    data_files_listed = bool(re.search(r"\.(zip|7z|csv|txt|sav)(?:[\"'<\s]|$)", micro_body, re.I))
    weighting_files_listed = bool(
        re.search(r"\.(zip|7z|shp|gpkg|csv)(?:[\"'<\s]|$)", weight_body, re.I)
    )
    documentation_files_listed = bool(
        re.search(r"\.(pdf|xlsx|xls|ods|txt|zip)(?:[\"'<\s]|$)", documentation_body, re.I)
    )
    requirements = {
        "officialDownloadIndexAccessible": records["ftp_root"]["statusCode"] == 200,
        "sampleMicrodataRootAccessible": micro_status == 200,
        "sampleDataFilesListed": data_files_listed,
        "weightingAreasRootAccessible": weight_status == 200,
        "weightingAreaFilesListed": weighting_files_listed,
        "packageDocumentationRootAccessible": documentation_status == 200,
        "packageDocumentationFilesListed": documentation_files_listed,
    }
    available = bool(
        all(requirements.values()) and root_has_candidate_entry
    )
    if available:
        raise Job5LFinalValidationError(
            "Fonte Censo aparenta disponível; execução F2/F5 exige novo contrato de layout e pesos"
        )
    return {
        "schemaVersion": "vocacoes-pne-job5l-final-censo-status-v2",
        "verifiedAtUtc": manifest["observedAtUtc"],
        "state": "OFFICIAL_SAMPLE_MICRODATA_NOT_AVAILABLE_AS_OF_2026_08_30",
        "sampleMicrodataAvailable": False,
        "weightingAreasAvailable": False,
        "packageDocumentationAvailable": False,
        "officialPackageAvailable": False,
        "ftpRootStatusCode": records["ftp_root"]["statusCode"],
        "sampleMicrodataExpectedRootStatusCode": micro_status,
        "weightingAreasExpectedRootStatusCode": weight_status,
        "sampleDocumentationExpectedRootStatusCode": documentation_status,
        "ftpRootContainsMicrodataOrWeightingCandidateEntry": root_has_candidate_entry,
        "availabilityRequirements": requirements,
        "availabilityDecision": "NOT_AVAILABLE_REQUIREMENTS_NOT_ALL_SATISFIED",
        "announcementAloneCountsAsAvailability": False,
        "officialPostponementNotice": CENSO_URLS["official_postponement_notice"],
        "officialUpdatedAnnouncement": CENSO_URLS["official_updated_announcement"],
        "officialCalendar": CENSO_URLS["official_calendar"],
        "officialCensoLanding": CENSO_URLS["official_censo_landing"],
        "officialProductLanding": CENSO_URLS["official_product_landing"],
        "expectedDownloadUrls": {
            "sampleMicrodata": CENSO_URLS["sample_microdata_expected_root"],
            "weightingAreas": CENSO_URLS["weighting_areas_expected_root"],
        },
        "expectedDocumentationUrl": CENSO_URLS[
            "sample_documentation_expected_root"
        ],
        "filesState": "OFFICIAL_SAMPLE_AND_WEIGHTING_FILES_NOT_LISTED",
        "documentationState": "OFFICIAL_PACKAGE_DOCUMENTATION_NOT_ACCESSIBLE",
        "licenseAndProvenance": {
            "authority": "IBGE",
            "officialTermsUrl": CENSO_URLS["official_terms_of_use"],
            "packageLicenseState": "NOT_OBSERVED_BECAUSE_PACKAGE_IS_ABSENT",
            "provenance": (
                "direct official-domain HTTP responses preserved byte-for-byte with "
                "timestamp, final URL, HTTP metadata and SHA-256"
            ),
        },
        "sourceAccess": {
            source_id: {
                "role": record["sourceRole"],
                "statusCode": record["statusCode"],
                "finalUrl": record["finalUrl"],
                "bodySha256": record["bodySha256"],
                "bodyByteSize": record["bodyByteSize"],
            }
            for source_id, record in sorted(records.items())
        },
        "officialStateInterpretation": (
            "O comunicado oficial foi alterado para data oportuna a definir e o aviso oficial "
            "adiou a divulgação; calendário, landing pages, downloads e documentação foram "
            "reverificados. A raiz geral responde, mas arquivos, áreas de ponderação e a "
            "documentação do pacote não satisfazem conjuntamente o gate de disponibilidade."
        ),
        "f2Executed": False,
        "f5Executed": False,
        "samePersonEstimateMaterialized": False,
        "definitiveJob5MAuthorizationAllowed": False,
        "substantiveDecision": (
            "AWAIT_OFFICIAL_SOURCE_OR_MANAGER_APPROVED_VERSION_WITHOUT_SAME_PERSON_LENS"
        ),
        "sourceManifestSha256": sha256_file(source_dir / "manifest.json"),
        "sourceManifest": manifest,
    }


def _verify_declared_artifacts(root: Path, manifest_name: str) -> dict[str, Any]:
    manifest_path = root / manifest_name
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Manifesto congelado ausente: {manifest_path}")
    manifest = _json(manifest_path)
    verified = 0
    for record in manifest.get("artifacts", []):
        relative = record["path"]
        path = root / relative
        if not path.is_file():
            raise FileNotFoundError(f"Artefato congelado ausente: {path}")
        if path.stat().st_size != record["byteSize"] or sha256_file(path) != record["sha256"]:
            raise Job5LFinalValidationError(f"Artefato congelado divergente: {path}")
        verified += 1
    return {
        "root": root.relative_to(REPO_ROOT).as_posix(),
        "manifest": manifest_name,
        "manifestByteSize": manifest_path.stat().st_size,
        "manifestSha256": sha256_file(manifest_path),
        "declaredArtifactCountVerified": verified,
        "finalState": manifest.get("finalState"),
    }


def verify_frozen_inputs() -> dict[str, Any]:
    base_preflight = job5l.verify_frozen_integrity()
    job5j = _verify_declared_artifacts(JOB5J_ROOT, "MANIFEST_JOB5J.json")
    job5k = _verify_declared_artifacts(JOB5K_ROOT, "MANIFEST_JOB5K.json")
    job5l.validate_existing_output(
        PREVIOUS_JOB5L_ROOT,
        source_root=PREVIOUS_JOB5L_ROOT / "sources",
        verify_sources=False,
    )
    previous = _verify_declared_artifacts(PREVIOUS_JOB5L_ROOT, "MANIFEST_JOB5L.json")
    return {
        "schemaVersion": "vocacoes-pne-job5l-final-frozen-input-proof-v1",
        "verifiedAt": GENERATED_AT,
        "job5J": job5j,
        "job5K": job5k,
        "job5L": previous,
        "baseFrozenRootDigests": base_preflight["frozenRootDigests"],
        "publicDataTreeDigestSha256": base_preflight["publicDataTreeDigestSha256"],
        "municipalityRegistrySha256": base_preflight["controlHashes"][
            "municipalityRegistrySha256"
        ],
        "regionRegistrySha256": base_preflight["controlHashes"][
            "regionRegistrySha256"
        ],
    }


def empirical_logit_percent(values: Sequence[Any] | pd.Series | np.ndarray) -> np.ndarray:
    rates = np.asarray(values, dtype=float)
    finite = np.isfinite(rates)
    if np.any(finite & ((rates < 0) | (rates > 100))):
        raise Job5LFinalValidationError("Taxa observada fora de 0–100 antes da transformação")
    result = np.full(rates.shape, np.nan, dtype=float)
    probability = (rates[finite] + 0.5) / 101.0
    result[finite] = np.log(probability / (1.0 - probability))
    return result


def inverse_logit_percent(values: Sequence[Any] | np.ndarray) -> np.ndarray:
    logits = np.asarray(values, dtype=float)
    result = np.full(logits.shape, np.nan, dtype=float)
    finite = np.isfinite(logits)
    finite_values = logits[finite]
    probability = np.empty(finite_values.shape, dtype=float)
    positive = finite_values >= 0
    probability[positive] = 1.0 / (1.0 + np.exp(-finite_values[positive]))
    exponential = np.exp(finite_values[~positive])
    probability[~positive] = exponential / (1.0 + exponential)
    result[finite] = probability * 100.0
    return result


def _ridge_logit_predict(
    train: pd.DataFrame,
    test: pd.DataFrame,
    *,
    features: Sequence[str],
    alpha: float,
) -> tuple[np.ndarray, dict[str, Any]]:
    x_train, x_test, metadata = job5l._matrix_fit(train, test, features)
    target = pd.to_numeric(train["target_logit"], errors="coerce").to_numpy(float)
    if not np.isfinite(target).all():
        raise Job5LFinalValidationError("Target logit não finito no ajuste F1")
    design = np.column_stack([np.ones(len(x_train)), x_train])
    penalty = np.eye(design.shape[1])
    penalty[0, 0] = 0.0
    coefficients = np.linalg.pinv(design.T @ design + alpha * penalty) @ design.T @ target
    predictions = np.column_stack([np.ones(len(x_test)), x_test]) @ coefficients
    metadata.update(
        {
            "alpha": alpha,
            "interceptLogit": float(coefficients[0]),
            "standardizedCoefficientsLogit": {
                name: float(value)
                for name, value in zip(metadata["featureNames"], coefficients[1:], strict=True)
            },
        }
    )
    return predictions, metadata


def _oof_logit_predictions(
    frame: pd.DataFrame,
    *,
    features: Sequence[str],
    alpha: float,
) -> np.ndarray:
    predictions = np.full(len(frame), np.nan, dtype=float)
    folds = frame["municipality_ibge_code"].astype(str).map(job5l._fold).to_numpy(int)
    for fold in range(5):
        train_mask = folds != fold
        test_mask = folds == fold
        values, _ = _ridge_logit_predict(
            frame.loc[train_mask],
            frame.loc[test_mask],
            features=features,
            alpha=alpha,
        )
        predictions[np.flatnonzero(test_mask)] = values
    return predictions


def _mae(observed: np.ndarray, predicted: np.ndarray) -> float | None:
    valid = np.isfinite(observed) & np.isfinite(predicted)
    if not valid.any():
        return None
    return float(np.mean(np.abs(observed[valid] - predicted[valid])))


def _conformal_quantile(residuals: np.ndarray, level: float = INTERVAL_LEVEL) -> float | None:
    residuals = residuals[np.isfinite(residuals)]
    if not len(residuals):
        return None
    probability = min(1.0, math.ceil((len(residuals) + 1) * level) / len(residuals))
    return float(np.quantile(residuals, probability, method="higher"))


def _bounded_conformal_scores(
    observed: np.ndarray, predicted: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Produz scores inferiores e superiores normalizados pelas fronteiras."""

    observed = np.asarray(observed, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    lower_scores = np.full(observed.shape, np.nan, dtype=float)
    upper_scores = np.full(observed.shape, np.nan, dtype=float)
    valid = np.isfinite(observed) & np.isfinite(predicted)
    lower_scores[valid] = 0.0
    upper_scores[valid] = 0.0
    below = valid & (observed < predicted)
    above = valid & (observed > predicted)
    lower_scores[below] = (predicted[below] - observed[below]) / predicted[below]
    upper_scores[above] = (observed[above] - predicted[above]) / (
        100.0 - predicted[above]
    )
    if np.any(
        np.isfinite(lower_scores) & ((lower_scores < 0) | (lower_scores > 1))
    ) or np.any(
        np.isfinite(upper_scores) & ((upper_scores < 0) | (upper_scores > 1))
    ):
        raise Job5LFinalValidationError("Score conformal limitado fora de 0–1")
    return lower_scores, upper_scores


def _bounded_interval(
    predicted: np.ndarray,
    lower_quantile: float | None,
    upper_quantile: float | None,
) -> tuple[np.ndarray, np.ndarray]:
    predicted = np.asarray(predicted, dtype=float)
    if lower_quantile is None or upper_quantile is None:
        return np.full(predicted.shape, np.nan), np.full(predicted.shape, np.nan)
    if not 0 <= lower_quantile <= 1 or not 0 <= upper_quantile <= 1:
        raise Job5LFinalValidationError("Quantil conformal limitado fora de 0–1")
    lower = predicted * (1.0 - lower_quantile)
    upper = predicted + (100.0 - predicted) * upper_quantile
    return lower, upper


def _interval_state(observed: Any, lower: Any, upper: Any) -> str:
    value = _finite(observed)
    low = _finite(lower)
    high = _finite(upper)
    if value is None or low is None or high is None:
        return "NOT_EVALUABLE"
    if value < low:
        return "BELOW_EXPECTED_INTERVAL"
    if value > high:
        return "ABOVE_EXPECTED_INTERVAL"
    return "WITHIN_EXPECTED_INTERVAL"


def _top_coefficients(details: Mapping[str, Any], count: int = 4) -> str:
    coefficients = details.get("standardizedCoefficientsLogit", {})
    selected = sorted(coefficients.items(), key=lambda item: (-abs(item[1]), item[0]))[:count]
    return "|".join(f"{name}:{value:.6g}" for name, value in selected)


def fit_f1_final(
    analysis: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """Compara histórico e contexto fora da amostra em uma escala limitada."""

    prepared = analysis.copy()
    prepared["target_logit"] = empirical_logit_percent(prepared["observed_value"])
    alphas = (0.1, 1.0, 10.0, 100.0)
    peer_k_values = (10, 20, 30)
    result_rows: list[dict[str, Any]] = []
    validation_rows: list[dict[str, Any]] = []
    model_details: dict[str, Any] = {}

    for outcome_id in job5l.OUTCOME_LABELS:
        for stage in job5l.STAGE_CONTEXT:
            model_id = f"F1_FINAL_{outcome_id}_{stage}"
            subset = prepared[
                prepared["outcome_id"].eq(outcome_id) & prepared["stage"].eq(stage)
            ].copy()
            subset["observed_value"] = pd.to_numeric(
                subset["observed_value"], errors="coerce"
            )
            training = subset[subset["year"].between(2019, 2024)].dropna(
                subset=["observed_value", "target_logit"]
            )
            temporal = subset[subset["year"].eq(2025)].copy()
            observed_training = training["observed_value"].to_numpy(float)
            family_results: dict[str, dict[str, Any]] = {}
            for family, features in (
                ("HISTORY_ONLY", HISTORY_FEATURES),
                ("HISTORY_PLUS_CONTEXT", CONTEXT_FEATURES),
            ):
                ridge_scores: dict[float, float] = {}
                ridge_oof_rates: dict[float, np.ndarray] = {}
                for alpha in alphas:
                    predicted_logit = _oof_logit_predictions(
                        training, features=features, alpha=alpha
                    )
                    predicted_rate = inverse_logit_percent(predicted_logit)
                    ridge_scores[alpha] = float(
                        _mae(observed_training, predicted_rate) or math.inf
                    )
                    ridge_oof_rates[alpha] = predicted_rate
                peer_scores: dict[int, float] = {}
                peer_oof_rates: dict[int, np.ndarray] = {}
                for k in peer_k_values:
                    predicted_rate = job5l._oof_predictions(
                        training,
                        method="nearest_context_peers",
                        parameter=k,
                        features=features,
                    )
                    peer_scores[k] = float(
                        _mae(observed_training, predicted_rate) or math.inf
                    )
                    peer_oof_rates[k] = predicted_rate
                best_alpha = min(
                    ridge_scores, key=lambda value: (ridge_scores[value], value)
                )
                best_k = min(peer_scores, key=lambda value: (peer_scores[value], value))
                if ridge_scores[best_alpha] <= peer_scores[best_k] * 0.99:
                    selected_method = "ridge_empirical_logit"
                    selected_parameter: float | int = best_alpha
                    selected_mae = ridge_scores[best_alpha]
                    selected_oof_rate = ridge_oof_rates[best_alpha]
                else:
                    selected_method = "nearest_context_peers"
                    selected_parameter = best_k
                    selected_mae = peer_scores[best_k]
                    selected_oof_rate = peer_oof_rates[best_k]
                family_results[family] = {
                    "features": features,
                    "ridgeScores": ridge_scores,
                    "peerScores": peer_scores,
                    "bestAlpha": best_alpha,
                    "bestK": best_k,
                    "selectedMethod": selected_method,
                    "selectedParameter": selected_parameter,
                    "bestMae": selected_mae,
                    "bestOofRate": selected_oof_rate,
                }

            naive_rate = job5l._oof_predictions(
                training,
                method="year_median_baseline",
                parameter=0,
                features=HISTORY_FEATURES,
            )
            naive_mae = float(_mae(observed_training, naive_rate) or math.inf)
            history_mae = float(family_results["HISTORY_ONLY"]["bestMae"])
            context_mae = float(family_results["HISTORY_PLUS_CONTEXT"]["bestMae"])
            context_improvement_percent = _safe_ratio(
                history_mae - context_mae, history_mae, multiplier=100
            )
            context_adds_value = bool(
                context_mae <= history_mae * 0.99 and context_mae <= naive_mae * 0.995
            )
            selected_family = (
                "HISTORY_PLUS_CONTEXT" if context_adds_value else "HISTORY_ONLY"
            )
            selected = family_results[selected_family]
            selected_method = str(selected["selectedMethod"])
            selected_parameter = selected["selectedParameter"]
            selected_mae = float(selected["bestMae"])
            selected_features = tuple(selected["features"])
            selected_oof_rate = np.asarray(selected["bestOofRate"], dtype=float)
            validation_eligible = bool(
                len(training) >= 1_000
                and int(temporal["observed_value"].notna().sum()) >= 490
                and math.isfinite(selected_mae)
                and selected_mae < naive_mae * 0.995
            )

            lower_scores, upper_scores = _bounded_conformal_scores(
                observed_training, selected_oof_rate
            )
            one_sided_level = 1.0 - (1.0 - INTERVAL_LEVEL) / 2.0
            conformal_lower_quantile = _conformal_quantile(
                lower_scores, level=one_sided_level
            )
            conformal_upper_quantile = _conformal_quantile(
                upper_scores, level=one_sided_level
            )
            supports: list[str] = [""] * len(temporal)
            if selected_method == "ridge_empirical_logit":
                temporal_logit, fit_details = _ridge_logit_predict(
                    training,
                    temporal,
                    features=selected_features,
                    alpha=float(selected_parameter),
                )
                temporal_expected = inverse_logit_percent(temporal_logit)
                bounding_technique = "empirical_logit_inverse_logistic"
            else:
                temporal_expected, supports = job5l._peer_predict(
                    training,
                    temporal,
                    features=selected_features,
                    k=int(selected_parameter),
                    return_support=True,
                )
                fit_details = {
                    "method": "inverse_distance_weighted_convex_average",
                    "k": int(selected_parameter),
                }
                bounding_technique = "convex_average_of_observed_rates"
            lower, upper = _bounded_interval(
                temporal_expected,
                conformal_lower_quantile,
                conformal_upper_quantile,
            )
            temporal_observed = pd.to_numeric(
                temporal["observed_value"], errors="coerce"
            ).to_numpy(float)
            valid_interval = (
                np.isfinite(temporal_observed) & np.isfinite(lower) & np.isfinite(upper)
            )
            temporal_coverage = (
                float(
                    np.mean(
                        (temporal_observed[valid_interval] >= lower[valid_interval])
                        & (temporal_observed[valid_interval] <= upper[valid_interval])
                    )
                )
                if valid_interval.any()
                else None
            )
            if temporal_coverage is None or temporal_coverage < 0.80:
                validation_eligible = False
            temporal_mae = _mae(temporal_observed, temporal_expected)

            sensitivity_training = training[~training["year"].isin([2020, 2021])]
            if selected_method == "ridge_empirical_logit":
                sensitivity_oof_logit = _oof_logit_predictions(
                    sensitivity_training,
                    features=selected_features,
                    alpha=float(selected_parameter),
                )
                sensitivity_oof_rate = inverse_logit_percent(sensitivity_oof_logit)
            else:
                sensitivity_oof_rate = job5l._oof_predictions(
                    sensitivity_training,
                    method="nearest_context_peers",
                    parameter=int(selected_parameter),
                    features=selected_features,
                )
            sensitivity_lower_scores, sensitivity_upper_scores = (
                _bounded_conformal_scores(
                    sensitivity_training["observed_value"].to_numpy(float),
                    sensitivity_oof_rate,
                )
            )
            sensitivity_lower_quantile = _conformal_quantile(
                sensitivity_lower_scores, level=one_sided_level
            )
            sensitivity_upper_quantile = _conformal_quantile(
                sensitivity_upper_scores, level=one_sided_level
            )
            if selected_method == "ridge_empirical_logit":
                sensitivity_logit, _ = _ridge_logit_predict(
                    sensitivity_training,
                    temporal,
                    features=selected_features,
                    alpha=float(selected_parameter),
                )
                sensitivity_expected = inverse_logit_percent(sensitivity_logit)
            else:
                sensitivity_expected, _ = job5l._peer_predict(
                    sensitivity_training,
                    temporal,
                    features=selected_features,
                    k=int(selected_parameter),
                )
            sensitivity_difference = _mae(temporal_expected, sensitivity_expected)

            primary_states: list[str] = []
            sensitivity_states: list[str] = []
            for position, row in enumerate(temporal.itertuples(index=False)):
                expected = _finite(temporal_expected[position])
                low = _finite(lower[position])
                high = _finite(upper[position])
                primary_state = (
                    _interval_state(row.observed_value, low, high)
                    if validation_eligible
                    else "NOT_EVALUABLE"
                )
                if (
                    sensitivity_lower_quantile is None
                    or sensitivity_upper_quantile is None
                ):
                    sensitivity_state = "NOT_EVALUABLE"
                else:
                    sensitivity_low, sensitivity_high = _bounded_interval(
                        np.asarray([sensitivity_expected[position]]),
                        sensitivity_lower_quantile,
                        sensitivity_upper_quantile,
                    )
                    sensitivity_state = _interval_state(
                        row.observed_value,
                        sensitivity_low[0],
                        sensitivity_high[0],
                    )
                primary_states.append(primary_state)
                sensitivity_states.append(sensitivity_state)
                result_rows.append(
                    {
                        "front_id": "F1",
                        "model_id": model_id,
                        "municipality_ibge_code": row.municipality_ibge_code,
                        "municipality_name": row.municipality_name,
                        "comparison_year": 2025,
                        "stage": stage,
                        "outcome_id": outcome_id,
                        "observed_value": _finite(row.observed_value),
                        "expected_value": expected if validation_eligible else None,
                        "expected_interval_lower": low if validation_eligible else None,
                        "expected_interval_upper": high if validation_eligible else None,
                        "interval_level": INTERVAL_LEVEL if validation_eligible else None,
                        "context_adjusted_state": primary_state,
                        "uncertainty_state": (
                            "TEMPORAL_COVERAGE_AT_LEAST_80_PERCENT"
                            if validation_eligible
                            else "NOT_EVALUABLE_VALIDATION_GATE"
                        ),
                        "selected_comparison_basis": selected_family,
                        "context_covariates_added_value_oos": context_adds_value,
                        "history_group_holdout_mae": history_mae,
                        "history_plus_context_group_holdout_mae": context_mae,
                        "context_incremental_mae_improvement_percent": (
                            context_improvement_percent
                        ),
                        "selected_method": selected_method,
                        "selected_parameter": selected_parameter,
                        "bounding_technique": bounding_technique,
                        "bounded_by_construction": True,
                        "post_prediction_clipping_applied": False,
                        "supporting_context": (
                            _top_coefficients(fit_details)
                            if selected_method == "ridge_empirical_logit"
                            else supports[position]
                        ),
                        "comparison_language": (
                            "historico_recente_e_contexto_observado"
                            if context_adds_value
                            else "historico_recente_sem_ganho_adicional_contextual"
                        ),
                        "same_record": True,
                        "same_person": False,
                        "unit_of_analysis": "municipality_year_stage_outcome",
                        "territorial_lens": (
                            "school_location|resident_population_context_kept_separate"
                        ),
                        "network_scope": "total_all_dependencies",
                        "administrative_dependency_role": "qa_only",
                        "ranking_allowed": False,
                        "causal_interpretation_allowed": False,
                        "sensitivity_without_2020_2021_state": sensitivity_state,
                    }
                )

            comparable_states = [
                left == right
                for left, right in zip(primary_states, sensitivity_states, strict=True)
                if left != "NOT_EVALUABLE" and right != "NOT_EVALUABLE"
            ]
            state_agreement = (
                float(np.mean(comparable_states)) if comparable_states else None
            )
            validation_rows.append(
                {
                    "front_id": "F1",
                    "model_id": model_id,
                    "outcome_id": outcome_id,
                    "stage": stage,
                    "training_row_count": len(training),
                    "training_municipality_count": training[
                        "municipality_ibge_code"
                    ].nunique(),
                    "temporal_holdout_year": 2025,
                    "temporal_holdout_observed_count": int(
                        np.isfinite(temporal_observed).sum()
                    ),
                    "history_only_group_holdout_mae": history_mae,
                    "history_plus_context_group_holdout_mae": context_mae,
                    "context_incremental_mae_improvement_percent": (
                        context_improvement_percent
                    ),
                    "context_covariates_added_value_oos": context_adds_value,
                    "naive_year_median_group_holdout_mae": naive_mae,
                    "selected_comparison_basis": selected_family,
                    "selected_method": selected_method,
                    "selected_parameter": selected_parameter,
                    "bounding_technique": bounding_technique,
                    "selected_group_holdout_mae": selected_mae,
                    "temporal_holdout_mae": temporal_mae,
                    "prediction_interval_level": INTERVAL_LEVEL,
                    "prediction_interval_lower_boundary_quantile": conformal_lower_quantile,
                    "prediction_interval_upper_boundary_quantile": conformal_upper_quantile,
                    "temporal_interval_coverage": temporal_coverage,
                    "validation_eligible": validation_eligible,
                    "selection_rule": (
                        "context_requires_1pct_oos_mae_gain_and_selected_model_requires_"
                        "0_5pct_gain_over_year_median"
                    ),
                    "bounded_by_construction": True,
                    "post_prediction_clipping_applied": False,
                    "sensitivity_without_2020_2021_expected_mean_abs_difference": (
                        sensitivity_difference
                    ),
                    "sensitivity_without_2020_2021_state_agreement": state_agreement,
                    "municipality_holdout_folds": 5,
                    "causal_interpretation_allowed": False,
                    "ranking_allowed": False,
                }
            )
            model_details[model_id] = {
                "outcomeId": outcome_id,
                "stage": stage,
                "historyFeatures": list(HISTORY_FEATURES),
                "historyPlusContextFeatures": list(CONTEXT_FEATURES),
                "historyRidgeScores": {
                    str(key): value
                    for key, value in family_results["HISTORY_ONLY"][
                        "ridgeScores"
                    ].items()
                },
                "historyPeerScores": {
                    str(key): value
                    for key, value in family_results["HISTORY_ONLY"][
                        "peerScores"
                    ].items()
                },
                "historyPlusContextRidgeScores": {
                    str(key): value
                    for key, value in family_results["HISTORY_PLUS_CONTEXT"][
                        "ridgeScores"
                    ].items()
                },
                "historyPlusContextPeerScores": {
                    str(key): value
                    for key, value in family_results["HISTORY_PLUS_CONTEXT"][
                        "peerScores"
                    ].items()
                },
                "naiveMae": naive_mae,
                "selectedComparisonBasis": selected_family,
                "selectedMethod": selected_method,
                "selectedParameter": selected_parameter,
                "boundingTechnique": bounding_technique,
                "contextAddsValueOutOfSample": context_adds_value,
                "validationEligible": validation_eligible,
                "fitDetails": fit_details,
                "calibration": {
                    "method": "group_municipality_out_of_fold_boundary_normalized_scores",
                    "intervalLevel": INTERVAL_LEVEL,
                    "lowerBoundaryNormalizedQuantile": conformal_lower_quantile,
                    "upperBoundaryNormalizedQuantile": conformal_upper_quantile,
                    "temporalCoverage": temporal_coverage,
                    "boundedByDistanceToZeroAndOneHundred": True,
                    "postPredictionClippingApplied": False,
                },
            }

    results = _stable_frame(
        pd.DataFrame(result_rows),
        ["outcome_id", "stage", "municipality_ibge_code"],
    )
    validation = _stable_frame(
        pd.DataFrame(validation_rows), ["outcome_id", "stage"]
    )
    bounded_columns = [
        "expected_value",
        "expected_interval_lower",
        "expected_interval_upper",
    ]
    for column in bounded_columns:
        values = pd.to_numeric(results[column], errors="coerce").dropna()
        if not values.between(0, 100, inclusive="both").all():
            raise Job5LFinalValidationError(f"F1 fora do suporte 0–100: {column}")
    return results, validation, model_details


def build_rais_final(raw_dir: Path) -> tuple[pd.DataFrame, dict[str, Any]]:
    panel, details = job5l.build_rais_panel(
        raw_dir, municipality_lens="establishment_location"
    )
    reconciliation = details["reconciliationWithFrozenAggregate"]
    by_year = reconciliation["byYear"]
    exact_cells = int(reconciliation["exactMatchCount"])
    mismatches = int(reconciliation["mismatchCount"])
    if exact_cells != 140 or mismatches != 0:
        raise Job5LFinalValidationError(
            "RAIS final não reconciliou 140/140 células município × faixa × ano"
        )
    if any(int(record["exactMatchCellCount"]) != 20 for record in by_year):
        raise Job5LFinalValidationError("RAIS final não conciliou 20/20 células em cada ano")
    if not panel["territorial_lens"].eq("establishment_location_workplace").all():
        raise Job5LFinalValidationError("RAIS final misturou lentes municipais")

    reconciliation.update(
        {
            "validationState": "EXACT_MATCH",
            "terminalState": "RAIS_2019_2025_CANONICAL_RECONCILED",
            "causeIdentified": True,
            "identifiedCause": (
                "Job 5L usou Mun Trab nos layouts 2019–2022, enquanto o agregado "
                "congelado e os layouts 2023–2025 usam o município de localização do "
                "estabelecimento. A reconstrução usa MUNICIPIO/Municipio-Codigo em toda a série."
            ),
            "differenceMustRemainVisible": False,
            "exactMatchRequiredForQA": True,
            "trend2019To2025Eligible": True,
        }
    )
    details["terminalState"] = "RAIS_2019_2025_CANONICAL_RECONCILED"
    details["serviceVersusEstablishmentLocationAudit"] = list(SERVICE_LENS_AUDIT)
    details["auditContract"] = {
        "rawRecordGrain": "one_declared_formal_bond_record",
        "universe": "public_nonidentified_RAIS_bond_microdata_South_region",
        "filter": "active_indicator_equals_1_and_age_between_15_and_24_inclusive",
        "municipalityLens": "establishment_location_workplace",
        "legacyMunicipalityField": "MUNICIPIO",
        "reprocessedMunicipalityField": "Municipio_Codigo",
        "serviceLocationField": "Mun_Trab_or_Municipio_Trab_Codigo_audit_only",
        "deduplication": "none_because_unit_is_bond_not_unique_worker",
        "establishmentType": (
            "all_official_establishment_types_included; Tipo_Estab is not a filter"
        ),
        "bondType": (
            "all_official_bond_types_included; type is an analytical composition dimension"
        ),
        "establishmentLocationDocumentedInOfficialLayout": True,
        "serviceLocationDocumentedSeparatelyInOfficialLayout": True,
        "officialTotalsReference": (
            "frozen_database_aggregate_public_rais_vinculos_by_establishment_municipality"
        ),
        "uniquePersonInterpretationAllowed": False,
    }
    return panel, details


def build_eja_final() -> pd.DataFrame:
    previous = _read_csv(
        PREVIOUS_JOB5L_ROOT / "internal" / "PAINEL_EJA_APROFUNDADO_F6_JOB5L.csv.gz"
    )
    selected = previous[
        [
            "entity_scope",
            "entity_id",
            "municipality_ibge_code",
            "municipality_name",
            "stage",
            "resident_adult_public",
            "school_location_eja_enrollments",
            "share_of_regional_public_percent",
            "share_of_regional_enrollments_percent",
            "distribution_difference_percentage_points",
            "distribution_direction",
            "eja_enrollments_2014",
            "eja_enrollments_2025",
            "territorial_lens",
            "network_scope",
            "resident_public_population_source",
            "adult_panel_compatibility",
            "source",
        ]
    ].copy()
    numeric_columns = (
        "resident_adult_public",
        "school_location_eja_enrollments",
        "share_of_regional_public_percent",
        "share_of_regional_enrollments_percent",
        "distribution_difference_percentage_points",
        "eja_enrollments_2014",
        "eja_enrollments_2025",
    )
    for column in numeric_columns:
        selected[column] = pd.to_numeric(selected[column], errors="coerce")
    selected["absolute_change_2014_2025"] = (
        selected["eja_enrollments_2025"] - selected["eja_enrollments_2014"]
    )
    selected["percent_change_2014_2025"] = [
        _safe_ratio(final - initial, initial, multiplier=100)
        for initial, final in zip(
            selected["eja_enrollments_2014"],
            selected["eja_enrollments_2025"],
            strict=True,
        )
    ]
    selected["value_status"] = np.where(
        selected["eja_enrollments_2014"].notna()
        & selected["eja_enrollments_2025"].notna(),
        "observed",
        "unavailable",
    )
    selected["front_id"] = "F6"
    selected["front_state"] = (
        "AGGREGATE_STAGE_SEPARATED_DISTRIBUTION_AND_ENROLLMENT_TRAJECTORY"
    )
    selected["unit"] = (
        "resident_adult_and_school_location_eja_aggregate_counts_with_regional_shares"
    )
    selected["same_person"] = False
    selected["cross_stage_combination_allowed"] = False
    selected["per_thousand_rate_materialized"] = False
    selected["coverage_demand_or_deficit_claim_allowed"] = False
    selected["resident_population_is_manifest_demand"] = False
    selected["distribution_contrast_materialized"] = True
    selected["distribution_contrast_interpretation"] = np.where(
        selected["adult_panel_compatibility"].eq(
            "DEFINITION_INCOMPATIBLE_POPULATION_TOTAL_SOURCE"
        ),
        "PRESERVED_WITH_DEFINITION_INCOMPATIBILITY_NOT_FULLY_COMPARABLE_ADULT_PANEL",
        "PRESERVED_COMPARABLE_AGGREGATE_DISTRIBUTION_CONTRAST",
    )
    if set(selected["stage"]) != {"fundamental", "high_school"}:
        raise Job5LFinalValidationError("EJA final perdeu a separação de etapas")
    forbidden_columns = {
        "eja_enrollments_per_thousand_resident_public_2022",
    }
    if forbidden_columns & set(selected.columns):
        raise Job5LFinalValidationError("EJA final preservou taxa por mil proibida")
    nsr = selected[selected["entity_id"].astype(str).eq(NSR_CODE)].set_index("stage")
    required_nsr = {
        "fundamental": (2.6482631443935167, 152.0),
        "high_school": (-2.6050945751099364, 56.0),
    }
    for stage, (difference, enrollments_2025) in required_nsr.items():
        if stage not in nsr.index or not math.isclose(
            float(nsr.loc[stage, "distribution_difference_percentage_points"]),
            difference,
            rel_tol=0,
            abs_tol=1e-9,
        ) or not math.isclose(
            float(nsr.loc[stage, "eja_enrollments_2025"]),
            enrollments_2025,
            rel_tol=0,
            abs_tol=1e-9,
        ):
            raise Job5LFinalValidationError(
                f"Âncora EJA de Nova Santa Rita divergente: {stage}"
            )
    return _stable_frame(selected, ["entity_scope", "entity_id", "stage"])


def build_f2_f5_unavailable(censo_status: Mapping[str, Any]) -> pd.DataFrame:
    region_codes = job5l._region_codes()
    _, names = job5l._municipalities()
    entities = [(REGION_ID, "Vale do Sinos", "region")] + [
        (code, names[code], "municipality") for code in region_codes
    ]
    rows: list[dict[str, Any]] = []
    reason = censo_status["state"]
    for entity_id, name, scope in entities:
        for age_group in ("15_17", "18_24"):
            rows.append(
                {
                    "front_id": "F2",
                    "front_state": "NOT_EXECUTED_OFFICIAL_SOURCE_UNAVAILABLE",
                    "entity_scope": scope,
                    "entity_id": entity_id,
                    "municipality_ibge_code": entity_id if scope == "municipality" else None,
                    "municipality_name": name,
                    "age_group": age_group,
                    "measure": "study_work_same_person_composition",
                    "value": None,
                    "unit": "weighted_person_estimate",
                    "value_status": "unavailable",
                    "same_person_required": True,
                    "same_person_materialized": False,
                    "territorial_lens": "person_residence_same_record",
                    "availability_reason": reason,
                    "causal_interpretation_allowed": False,
                }
            )
        rows.append(
            {
                "front_id": "F5",
                "front_state": "NOT_EXECUTED_OFFICIAL_SOURCE_UNAVAILABLE",
                "entity_scope": scope,
                "entity_id": entity_id,
                "municipality_ibge_code": entity_id if scope == "municipality" else None,
                "municipality_name": name,
                "age_group": None,
                "measure": "migration_school_offer_same_person_context",
                "value": None,
                "unit": "weighted_person_estimate",
                "value_status": "unavailable",
                "same_person_required": True,
                "same_person_materialized": False,
                "territorial_lens": "person_residence_same_record",
                "availability_reason": reason,
                "causal_interpretation_allowed": False,
            }
        )
    return _stable_frame(
        pd.DataFrame(rows), ["front_id", "entity_scope", "entity_id", "age_group"]
    )


def _rais_value(
    panel: pd.DataFrame,
    *,
    entity_id: str,
    year: int,
    age_group: str,
    metric_id: str,
    dimension_code: str | None = None,
) -> float | None:
    selected = panel[
        panel["entity_id"].astype(str).eq(entity_id)
        & pd.to_numeric(panel["year"], errors="coerce").eq(year)
        & panel["age_group"].eq(age_group)
        & panel["metric_id"].eq(metric_id)
    ]
    if dimension_code is not None:
        selected = selected[selected["dimension_code"].astype(str).eq(dimension_code)]
    if len(selected) != 1:
        raise Job5LFinalValidationError(
            f"Métrica RAIS não singular: {entity_id}/{year}/{age_group}/{metric_id}/{dimension_code}"
        )
    return _finite(selected.iloc[0]["value"])


def _fmt(value: Any, decimals: int = 1) -> str:
    number = _finite(value)
    if number is None:
        return "indisponível"
    return f"{number:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def build_candidate_catalog(
    *,
    f1_results: pd.DataFrame,
    f1_validation: pd.DataFrame,
    rais_panel: pd.DataFrame,
    eja_panel: pd.DataFrame,
    censo_status: Mapping[str, Any],
) -> dict[str, Any]:
    eligible = f1_validation["validation_eligible"].astype(bool)
    context_value = f1_validation["context_covariates_added_value_oos"].astype(bool)
    eligible_count = int(eligible.sum())
    context_count = int((eligible & context_value).sum())
    history_count = int((eligible & ~context_value).sum())
    not_evaluable = f1_validation.loc[~eligible, ["outcome_id", "stage"]].to_dict(
        "records"
    )
    region_codes = set(job5l._region_codes())
    nsr_f1 = f1_results[f1_results["municipality_ibge_code"].astype(str).eq(NSR_CODE)]
    vale_f1 = f1_results[
        f1_results["municipality_ibge_code"].astype(str).isin(region_codes)
    ]
    f1_result_columns = [
        "outcome_id",
        "stage",
        "observed_value",
        "expected_value",
        "expected_interval_lower",
        "expected_interval_upper",
        "selected_comparison_basis",
        "context_adjusted_state",
    ]
    nsr_f1_result = _json_safe(
        nsr_f1[f1_result_columns]
        .sort_values(["stage", "outcome_id"], kind="mergesort")
        .to_dict("records")
    )

    def rais_profile(entity_id: str) -> dict[str, Any]:
        def value(
            age_group: str, metric_id: str, dimension_code: str | None = None
        ) -> float | None:
            return _rais_value(
                rais_panel,
                entity_id=entity_id,
                year=2025,
                age_group=age_group,
                metric_id=metric_id,
                dimension_code=dimension_code,
            )

        return {
            "age15To17": {
                "activeBondCount": value("15_17", "active_bonds", "ALL"),
                "activeApprenticeshipBondSharePercent": value(
                    "15_17",
                    "bond_type_composition_share_percent",
                    "apprentice_contract",
                ),
                "contractedWeeklyHoursMean": value(
                    "15_17", "contracted_weekly_hours_mean", "ALL"
                ),
                "top4OccupationConcentrationSharePercent": value(
                    "15_17", "top4_occupation_concentration_share_percent"
                ),
                "top4SectorConcentrationSharePercent": value(
                    "15_17", "top4_sector_concentration_share_percent"
                ),
            },
            "age18To24": {
                "activeBondCount": value("18_24", "active_bonds", "ALL"),
                "highSchoolCompleteSharePercent": value(
                    "18_24",
                    "schooling_composition_share_percent",
                    "high_school_complete",
                ),
                "contractedWeeklyHoursMean": value(
                    "18_24", "contracted_weekly_hours_mean", "ALL"
                ),
                "bondTenureMedianMonths": value(
                    "18_24", "bond_tenure_median", "ALL"
                ),
                "top4OccupationConcentrationSharePercent": value(
                    "18_24", "top4_occupation_concentration_share_percent"
                ),
                "top4SectorConcentrationSharePercent": value(
                    "18_24", "top4_sector_concentration_share_percent"
                ),
                "nominalAverageMonthlyRemunerationMedianBRL": value(
                    "18_24",
                    "nominal_average_monthly_remuneration_median",
                    "ALL",
                ),
            },
            "trend2019To2025": {
                age_group: {
                    "initialActiveBondCount": _rais_value(
                        rais_panel,
                        entity_id=entity_id,
                        year=2019,
                        age_group=age_group,
                        metric_id="active_bonds",
                        dimension_code="ALL",
                    ),
                    "finalActiveBondCount": _rais_value(
                        rais_panel,
                        entity_id=entity_id,
                        year=2025,
                        age_group=age_group,
                        metric_id="active_bonds",
                        dimension_code="ALL",
                    ),
                }
                for age_group in ("15_17", "18_24")
            },
        }

    def rais_range(
        age_group: str, metric_id: str, dimension_code: str | None = None
    ) -> dict[str, Any]:
        selected = rais_panel[
            rais_panel["entity_id"].astype(str).isin(region_codes)
            & pd.to_numeric(rais_panel["year"], errors="coerce").eq(2025)
            & rais_panel["age_group"].eq(age_group)
            & rais_panel["metric_id"].eq(metric_id)
        ]
        if dimension_code is not None:
            selected = selected[
                selected["dimension_code"].astype(str).eq(dimension_code)
            ]
        values = pd.to_numeric(selected["value"], errors="coerce").dropna()
        return {
            "municipalityCount": int(selected["entity_id"].astype(str).nunique()),
            "minimum": float(values.min()),
            "maximum": float(values.max()),
        }

    nsr_rais = rais_profile(NSR_CODE)
    vale_rais = rais_profile(REGION_ID)
    rais_heterogeneity = {
        "activeBondCount15To17": rais_range("15_17", "active_bonds", "ALL"),
        "activeApprenticeshipBondSharePercent": rais_range(
            "15_17",
            "bond_type_composition_share_percent",
            "apprentice_contract",
        ),
        "top4OccupationShare18To24": rais_range(
            "18_24", "top4_occupation_concentration_share_percent"
        ),
        "top4SectorShare18To24": rais_range(
            "18_24", "top4_sector_concentration_share_percent"
        ),
    }

    eja_result_columns = [
        "entity_scope",
        "entity_id",
        "municipality_ibge_code",
        "municipality_name",
        "stage",
        "resident_adult_public",
        "school_location_eja_enrollments",
        "share_of_regional_public_percent",
        "share_of_regional_enrollments_percent",
        "distribution_difference_percentage_points",
        "distribution_direction",
        "eja_enrollments_2014",
        "eja_enrollments_2025",
        "adult_panel_compatibility",
        "distribution_contrast_interpretation",
    ]
    nsr_eja = eja_panel[eja_panel["entity_id"].astype(str).eq(NSR_CODE)]
    vale_eja = eja_panel[eja_panel["entity_id"].astype(str).eq(REGION_ID)]
    nsr_eja_result = _json_safe(nsr_eja[eja_result_columns].to_dict("records"))
    vale_eja_result = _json_safe(vale_eja[eja_result_columns].to_dict("records"))
    eja_municipal = eja_panel[eja_panel["entity_scope"].eq("municipality")]
    eja_heterogeneity = [
        {
            "stage": stage,
            "minimumDistributionDifferencePercentagePoints": float(
                group["distribution_difference_percentage_points"].min()
            ),
            "maximumDistributionDifferencePercentagePoints": float(
                group["distribution_difference_percentage_points"].max()
            ),
        }
        for stage, group in eja_municipal.groupby("stage", sort=True)
    ]

    def insight_list(path: Path) -> list[dict[str, Any]]:
        document = _json(path)
        if isinstance(document, list):
            return document
        for key in ("insights", "candidates", "candidateInsights"):
            if isinstance(document.get(key), list):
                return document[key]
        raise Job5LFinalValidationError(f"Catálogo congelado sem candidatas: {path}")

    frozen_i4 = next(
        item
        for item in insight_list(
            PREVIOUS_JOB5L_ROOT / "CATALOGO_INSIGHTS_APROFUNDADOS_JOB5L.json"
        )
        if item["insight_id"] == "I4_FUNCTIONAL_TERRITORIAL_BALANCE"
    )
    frozen_r4 = next(
        item
        for item in insight_list(JOB5J_ROOT / "CATALOGO_INSIGHTS_CANDIDATOS_JOB5J.json")
        if item["insight_id"] == "JOB5J_R4_OCCUPATIONS_EPT"
    )
    job5k_bundle = _json(JOB5K_ROOT / "BUNDLE_INSIGHTS_UI_JOB5K.json")
    job5k_youth_work = next(
        story
        for story in job5k_bundle["stories"]
        if any(
            record.get("entity_id") == NSR_CODE
            and "apprenticeship_15_17" in record
            for record in story.get("primary_evidence", {}).get("by_entity", [])
        )
    )
    job5k_nsr = next(
        record
        for record in job5k_youth_work["primary_evidence"]["by_entity"]
        if record.get("entity_id") == NSR_CODE
        and "apprenticeship_15_17" in record
    )
    if float(job5k_nsr["rais_15_17"]["final_value"]) != float(
        nsr_rais["age15To17"]["activeBondCount"]
    ):
        raise Job5LFinalValidationError(
            "Estoque RAIS de Nova Santa Rita divergiu do apoio congelado do Job 5K"
        )

    common_forbidden = [
        "atribuir causalidade",
        "classificar municípios em ranking",
        "tratar lentes territoriais distintas como a mesma população",
        "inferir a mesma pessoa cruzando fontes",
        "criar score, índice sintético ou prioridade automática",
    ]
    active_vs_admissions = {
        "raisActiveApprenticeshipBonds": (
            "estoque de vínculos ativos de aprendizagem em 31/12, localizado pelo "
            "estabelecimento"
        ),
        "cagedApprenticeAdmissions": (
            "eventos de admissão classificados como aprendizagem ao longo do ano; "
            "medida de fluxo preservada apenas como distinção semântica"
        ),
        "novaSantaRita2025": {
            "raisActiveBondStock15To17": nsr_rais["age15To17"]["activeBondCount"],
            "raisActiveApprenticeshipBondSharePercent": nsr_rais["age15To17"][
                "activeApprenticeshipBondSharePercent"
            ],
            "cagedApprenticeAdmissionEvents": job5k_nsr["apprenticeship_share_2025"][
                "numerator"
            ],
            "cagedYouthAdmissionEvents": job5k_nsr["apprenticeship_share_2025"][
                "denominator"
            ],
            "cagedApprenticeAdmissionEventSharePercent": job5k_nsr[
                "apprenticeship_share_2025"
            ]["percent"],
            "cagedSeriesId": job5k_nsr["apprenticeship_15_17"]["series_id"],
            "cagedFactId": job5k_nsr["apprenticeship_share_2025"]["fact_id"],
        },
        "labelsInterchangeable": False,
        "stocksAndEventsInterchangeable": False,
    }

    insights: list[dict[str, Any]] = [
        {
            "insight_id": "I1_CONTEXT_ADJUSTED_EDUCATIONAL_TRAJECTORY",
            "manager_question": (
                "A trajetória educacional de 2025 ficou dentro da faixa associada ao "
                "histórico recente e, quando validado, ao contexto observado?"
            ),
            "evidence_level": "E2_CONTEXT_ADJUSTED_COMPARISON",
            "analytical_state": "ELIGIBLE_WITH_MODEL_SPECIFIC_BASIS",
            "editorial_state": "SECONDARY_CONTEXT_FOR_TRAJECTORY",
            "education_outcome": "aprovação, reprovação, abandono e distorção por etapa",
            "territorial_or_socioeconomic_dimension": (
                "histórico recente e contexto socioeconômico/escolar adicional validado"
            ),
            "same_record": False,
            "same_person": False,
            "unit_of_analysis": "municipality_year_stage_outcome",
            "territorial_lens": (
                "school_location_with_resident_context_kept_as_separate_covariates"
            ),
            "period": "training_2019_2024; comparison_2025",
            "universe": "497 municípios do RS; rede total",
            "method": (
                "bounded empirical-logit ridge or convex nearest-peer average; five-fold "
                "municipality holdout; history-only versus history-plus-context; 2025 temporal "
                "holdout; directional boundary-normalized conformal interval"
            ),
            "validation": {
                "eligibleModelCount": eligible_count,
                "contextAddsValueModelCount": context_count,
                "historyOnlySelectedModelCount": history_count,
                "notEvaluableCombinations": not_evaluable,
                "allExpectedValuesAndIntervalsWithinZeroAndOneHundred": True,
                "postPredictionClippingApplied": False,
            },
            "regional_result": {
                "valeDoSinosStateCounts": vale_f1[
                    "context_adjusted_state"
                ].value_counts().to_dict()
            },
            "ten_municipality_heterogeneity": vale_f1[
                "context_adjusted_state"
            ].value_counts().to_dict(),
            "selected_municipality_result": nsr_f1_result,
            "nova_santa_rita_result": nsr_f1_result,
            "context_adjusted_result": {
                "novaSantaRitaStateCounts": nsr_f1[
                    "context_adjusted_state"
                ].value_counts().to_dict(),
                "contextAddsValueModelCount": context_count,
                "historyOnlySelectedModelCount": history_count,
            },
            "precision_state": (
                "PREDICTION_INTERVAL_90_PERCENT_BOUNDED_BY_CONSTRUCTION_WITH_TEMPORAL_GATE"
            ),
            "literature_mechanism": "M1_CONTEXT_AND_TRAJECTORY",
            "integrated_conclusion": (
                "Os desfechos avaliáveis de Nova Santa Rita em 2025 ficaram dentro da faixa "
                "observada para municípios com histórico recente e contexto semelhante. "
                f"O contexto adicional acrescentou valor fora da amostra em {context_count} "
                "das 11 combinações elegíveis; abandono nos anos iniciais não é avaliável."
            ),
            "incremental_value_beyond_separate_charts": (
                "Distingue uma taxa isolada de uma comparação preditiva validada e mostra "
                "quando o contexto realmente acrescenta informação além do histórico."
            ),
            "planning_implication": (
                "Usar saídas fora da faixa como pergunta diagnóstica específica; quando "
                "dentro, manter monitoramento sem converter o resultado em nota."
            ),
            "monitoring_indicators": [
                "observed_value",
                "expected_interval",
                "selected_comparison_basis",
                "temporal_coverage",
                "pandemic_sensitivity",
            ],
            "institutional_coordination": [
                "gestão municipal",
                "rede estadual",
                "equipes de dados educacionais",
            ],
            "allowed_claims": [
                "dizer dentro/acima/abaixo da faixa quando o modelo específico é elegível",
                "mencionar contexto apenas onde houve ganho fora da amostra",
                "descrever incerteza e sensibilidade a 2020–2021",
            ],
            "forbidden_claims": [
                *common_forbidden,
                "chamar diferença preditiva de efeito escolar ou valor agregado",
            ],
            "limitations": [
                "covariáveis observadas não esgotam diferenças municipais",
                "intervalo preditivo não é intervalo causal",
                "o holdout temporal cobre somente 2025",
            ],
            "recommended_visual": "compact_interval_context_detail_not_opening_story",
            "manager_review_state": "REQUIRES_EXTERNAL_JUDGMENT",
            "main_candidate": False,
            "observed": True,
            "relationship_class": "CONTEXT_ADJUSTED_PREDICTIVE_COMPARISON",
            "claim_ceiling": "PREDICTIVE_ASSOCIATION_WITH_MODEL_SPECIFIC_BASIS",
            "editorial_role": "CONTEXT",
        },
        {
            "insight_id": "I2_MERGED_YOUTH_WORK_COMPOSITION",
            "manager_question": (
                "Como mudou e como se compõe o estoque de vínculos formais jovens nos "
                "estabelecimentos do município e da região?"
            ),
            "evidence_level": "E1_OFFICIAL_DESCRIPTIVE_RECONCILED_SERIES",
            "analytical_state": "ELIGIBLE_CURRENT_PROFILE_AND_2019_2025_TREND",
            "editorial_state": "PRIMARY_STORY_RECONCILED",
            "education_outcome": "contexto de inserção formal jovem, sem desfecho escolar ligado",
            "territorial_or_socioeconomic_dimension": (
                "trabalho formal jovem por localização do estabelecimento"
            ),
            "same_record": True,
            "same_person": False,
            "unit_of_analysis": "active_formal_bond_at_31_12",
            "territorial_lens": "establishment_location_workplace",
            "period": "2019-2025; current profile 2025",
            "universe": (
                "vínculos RAIS ativos em 31/12, idades 15–17 e 18–24, Vale e dez municípios"
            ),
            "method": (
                "streaming RAIS microdata; active=1; ages 15–24; establishment municipality; "
                "exact reconciliation in 140 cells"
            ),
            "validation": {
                "terminalState": "RAIS_2019_2025_CANONICAL_RECONCILED",
                "exactCellCount": 140,
                "mismatchCellCount": 0,
                "legacyAlternativeServiceLocationExactCellCount": 0,
                "measurementDistinction": active_vs_admissions,
            },
            "regional_result": vale_rais,
            "ten_municipality_heterogeneity": rais_heterogeneity,
            "selected_municipality_result": nsr_rais,
            "nova_santa_rita_result": nsr_rais,
            "context_adjusted_result": None,
            "precision_state": "EXACT_ADMINISTRATIVE_BOND_COUNTS_NO_PERSON_DEDUPLICATION",
            "literature_mechanism": "M3_YOUTH_WORK_AND_M4_EPT_AND_WORK",
            "integrated_conclusion": (
                "Nos estabelecimentos de Nova Santa Rita, o trabalho formal jovem é mais "
                "concentrado na aprendizagem entre 15 e 17 anos e em poucos setores e "
                "ocupações entre 18 e 24 anos do que no conjunto do Vale. A aprendizagem "
                "aqui é estoque de vínculos ativos RAIS; admissões de aprendizes no Caged "
                "são eventos de fluxo distintos e não recebem o mesmo rótulo."
            ),
            "incremental_value_beyond_separate_charts": (
                "Integra escolaridade declarada, aprendizagem ativa, jornada, permanência, "
                "remuneração e concentração em um único contrato de vínculo reconciliado."
            ),
            "planning_implication": (
                "Pautar coordenação entre educação, trabalho e empregadores sobre composição "
                "e concentração, sem inferir residência ou trajetória escolar individual."
            ),
            "monitoring_indicators": [
                "active_bonds",
                "active_apprenticeship_bond_share",
                "declared_schooling",
                "contracted_hours",
                "bond_tenure",
                "nominal_pay_2025",
                "top4_occupation_share",
                "top4_sector_share",
                "caged_admission_events_kept_separate",
            ],
            "institutional_coordination": [
                "educação",
                "trabalho",
                "empregadores",
                "Sistema S",
                "municípios do Vale",
            ],
            "allowed_claims": [
                "descrever estoque, composição e mudança de vínculos por estabelecimento",
                "comparar município e região mantendo unidade e faixa etária",
                "mostrar remuneração de 2025 somente em valores nominais",
                "distinguir estoque RAIS de eventos de admissão Caged",
            ],
            "forbidden_claims": [
                *common_forbidden,
                "interpretar vínculos como pessoas únicas ou residentes",
                "atribuir mudanças da RAIS a trajetórias escolares",
                "usar remuneração nominal histórica como ganho real",
                "tratar vínculo ativo de aprendizagem e admissão de aprendiz como a mesma medida",
            ],
            "limitations": [
                "um trabalhador pode ter mais de um vínculo",
                "a transição integral ao eSocial desde 2023 exige cautela estrutural",
                "não há ligação individual com Censo Escolar ou Censo Demográfico",
            ],
            "recommended_visual": "two_age_group_composition_with_explicit_bond_stock_labels",
            "manager_review_state": "REQUIRES_EXTERNAL_JUDGMENT",
            "main_candidate": True,
            "observed": True,
            "relationship_class": "DIRECT_RECONCILED_ADMINISTRATIVE_DESCRIPTION",
            "claim_ceiling": "DESCRIPTIVE_ACTIVE_BOND_STOCK_BY_ESTABLISHMENT",
            "editorial_role": "STORY",
            "measurement_distinction": active_vs_admissions,
        },
        {
            "insight_id": "I4_FUNCTIONAL_TERRITORIAL_GRAMMAR",
            "manager_question": (
                "Como residência, oferta educacional e trabalho se distribuem no território "
                "quando cada lente permanece explicitamente distinta?"
            ),
            "evidence_level": "E3_CROSS_LENS_TERRITORIAL_CONTRAST",
            "analytical_state": "APPROVED_AS_CROSS_CUTTING_GRAMMAR",
            "editorial_state": "CROSS_CUTTING_GRAMMAR_NOT_STANDALONE_STORY",
            "education_outcome": "oferta localizada, EJA e EPT como componentes de contexto",
            "territorial_or_socioeconomic_dimension": "organização funcional territorial",
            "same_record": False,
            "same_person": False,
            "unit_of_analysis": "municipal_share_of_regional_component",
            "territorial_lens": "multiple_declared_lenses_not_merged",
            "period": "2019-2025; 2022; 2025 conforme comparação",
            "universe": "Vale do Sinos e dez municípios",
            "method": (
                "diferenças entre participações regionais por componente, sem soma de "
                "universos, sem índice sintético e sem inferência de mesma pessoa"
            ),
            "validation": {
                "standaloneStory": False,
                "syntheticIndex": False,
                "comparisonCount": frozen_i4["regional_result"]["comparisonCount"],
                "transformationOccupationEptFrozenJob5JClassification": frozen_r4[
                    "classification"
                ],
                "activeApprenticeshipVsCagedAdmissions": active_vs_admissions,
            },
            "regional_result": {
                "functionalComparisonCount": frozen_i4["regional_result"][
                    "comparisonCount"
                ],
                "transformationOccupationEpt": frozen_r4["vale_result"],
            },
            "ten_municipality_heterogeneity": frozen_i4[
                "ten_municipality_heterogeneity"
            ],
            "selected_municipality_result": frozen_i4[
                "selected_municipality_result"
            ],
            "nova_santa_rita_result": {
                "functionalComparisons": frozen_i4["nova_santa_rita_result"],
                "transformationOccupationEpt": frozen_r4["nova_santa_rita_result"],
            },
            "context_adjusted_result": None,
            "precision_state": "DIRECT_AGGREGATE_COMPONENTS_WITH_DECLARED_LENSES",
            "literature_mechanism": "M4_EPT_AND_WORK|M6_EJA_PARTICIPATION",
            "integrated_conclusion": (
                "As participações são comparadas dimensão a dimensão; em Nova Santa Rita, "
                "a transformação da CBO 414140 convive com oferta EPT local zero observado, "
                "um desencontro territorial para coordenação regional, não prova de déficit "
                "curricular, falta de acesso ou ineficiência municipal."
            ),
            "incremental_value_beyond_separate_charts": (
                "Fornece a gramática que conecta histórias de trabalho, EPT e EJA sem "
                "apagar a diferença entre residência, escola e estabelecimento."
            ),
            "planning_implication": (
                "Usar os contrastes para formular perguntas de coordenação intermunicipal "
                "sobre acesso regional, itinerários e localização antes de decidir nova oferta."
            ),
            "monitoring_indicators": [
                "municipal_share",
                "reference_share",
                "difference_percentage_points",
                "territorial_lens",
                "CBO_414140",
                "EPT_localizada",
            ],
            "institutional_coordination": [
                "municípios do Vale",
                "educação",
                "trabalho",
                "instituições EPT",
                "desenvolvimento econômico",
            ],
            "allowed_claims": [
                "descrever participação maior, menor ou próxima da referência declarada",
                "descrever desencontro territorial observado",
                "dizer que EPT zero é ausência de oferta localizada observada",
            ],
            "forbidden_claims": [
                *common_forbidden,
                "afirmar déficit, excesso, eficiência, falta de acesso ou aderência curricular",
                "tratar ponte normativa ocupação–curso como correspondência causal ou aditiva",
                "usar o mesmo rótulo para aprendizagem ativa RAIS e admissão Caged",
            ],
            "limitations": [
                "períodos variam por componente",
                "lentes não representam pessoas comuns",
                "origem dos estudantes e residência dos trabalhadores não são observadas",
                "ponte ocupação–EPT é muitos-para-muitos",
            ],
            "recommended_visual": "lens_labeled_paired_shares_embedded_in_other_stories",
            "manager_review_state": "REQUIRES_EXTERNAL_JUDGMENT",
            "main_candidate": False,
            "observed": True,
            "relationship_class": "TERRITORIAL_CROSS_LENS_CONTRAST",
            "claim_ceiling": "DESCRIPTIVE_TERRITORIAL_ORGANIZATION_ONLY",
            "editorial_role": "DETAIL_GRAMMAR",
        },
        {
            "insight_id": "I5_ADULT_SCHOOLING_AND_EJA_DISTRIBUTION",
            "manager_question": (
                "Como se relacionam, por etapa, a distribuição do público adulto residente, "
                "a matrícula EJA localizada e sua trajetória?"
            ),
            "evidence_level": "E3_AGGREGATE_TERRITORIAL_CONTRAST",
            "analytical_state": "SUPPORTED_AGGREGATE_WITH_EXPLICIT_LIMITS",
            "editorial_state": "PRIMARY_STORY_WITH_STAGE_SEPARATION",
            "education_outcome": "EJA fundamental e ensino médio separados",
            "territorial_or_socioeconomic_dimension": "escolaridade adulta e EJA",
            "same_record": False,
            "same_person": False,
            "unit_of_analysis": "resident_population_vs_located_eja_enrollments",
            "territorial_lens": "resident_population|school_location_kept_distinct",
            "period": "distribuição 2022; história EJA 2014-2025",
            "universe": "Vale do Sinos e dez municípios; rede total",
            "method": (
                "contraste entre participações regionais do público adulto e das matrículas "
                "localizadas, mais contagens 2014 e 2025; etapas separadas; sem taxa por mil"
            ),
            "validation": {
                "rowCount": len(eja_panel),
                "stagesKeptSeparate": True,
                "perThousandRateMaterialized": False,
                "coverageDemandOrDeficitClaimAllowed": False,
                "fundamentalAdultPanelCompatibility": (
                    "DEFINITION_INCOMPATIBLE_POPULATION_TOTAL_SOURCE"
                ),
                "novaSantaRitaFundamentalDifferencePercentagePoints": 2.6482631443935167,
                "novaSantaRitaHighSchoolDifferencePercentagePoints": -2.6050945751099364,
                "novaSantaRita2025Enrollments": {
                    "fundamental": 152,
                    "highSchool": 56,
                },
            },
            "regional_result": vale_eja_result,
            "ten_municipality_heterogeneity": eja_heterogeneity,
            "selected_municipality_result": nsr_eja_result,
            "nova_santa_rita_result": nsr_eja_result,
            "context_adjusted_result": None,
            "precision_state": "AGGREGATE_COUNTS_NO_SAMPLE_PRECISION",
            "literature_mechanism": "M6_EJA_PARTICIPATION",
            "integrated_conclusion": (
                "Em Nova Santa Rita, a participação da matrícula localizada ficou 2,648 p.p. "
                "acima da participação do público no fundamental e 2,605 p.p. abaixo no "
                "ensino médio em 2022; em 2025 havia 152 e 56 matrículas, respectivamente. "
                "O denominador do fundamental tem incompatibilidade de definição e não forma "
                "um painel adulto plenamente comparável."
            ),
            "incremental_value_beyond_separate_charts": (
                "Relaciona distribuição territorial e trajetória da matrícula por etapa, "
                "preservando a incompatibilidade do denominador fundamental."
            ),
            "planning_implication": (
                "Investigar horários, localização e coordenação regional separadamente por "
                "etapa, sem chamar público residente de demanda manifesta."
            ),
            "monitoring_indicators": [
                "resident_adult_public",
                "school_location_eja_enrollments",
                "share_of_regional_public_percent",
                "share_of_regional_enrollments_percent",
                "distribution_difference_percentage_points",
                "eja_enrollments_2014",
                "eja_enrollments_2025",
                "adult_panel_compatibility",
            ],
            "institutional_coordination": [
                "EJA municipal e estadual",
                "assistência social",
                "trabalho",
                "transporte",
            ],
            "allowed_claims": [
                "descrever contraste entre distribuições por etapa",
                "descrever contagens e mudanças separadas por etapa",
                "explicitar que o fundamental não é painel adulto plenamente comparável",
            ],
            "forbidden_claims": [
                *common_forbidden,
                "usar matrículas por mil no percurso principal",
                "chamar matrícula de cobertura, demanda atendida ou déficit",
                "confirmar barreira de trabalho",
            ],
            "limitations": [
                "matrícula localizada não identifica residência do estudante",
                "fundamental usa fonte de população agregada incompatível com painel adulto",
                "contagens agregadas não identificam barreiras individuais",
            ],
            "recommended_visual": "two_stage_distribution_contrast_plus_enrollment_trajectory",
            "manager_review_state": "REQUIRES_EXTERNAL_JUDGMENT",
            "main_candidate": True,
            "observed": True,
            "relationship_class": "TERRITORIAL_AGGREGATE_CONTRAST_AND_DIRECT_TRAJECTORY",
            "claim_ceiling": "DESCRIPTIVE_DISTRIBUTION_CONTRAST_WITH_STAGE_SPECIFIC_LIMITS",
            "editorial_role": "STORY",
        },
    ]

    def negative_candidate(
        *,
        insight_id: str,
        manager_question: str,
        education_outcome: str,
        dimension: str,
        method: str,
        conclusion: str,
        dependency: str,
        forbidden: str,
    ) -> dict[str, Any]:
        unavailable = {
            "state": censo_status["state"],
            "officialPackageAvailable": censo_status["officialPackageAvailable"],
            "substantiveDecision": censo_status["substantiveDecision"],
        }
        return {
            "insight_id": insight_id,
            "manager_question": manager_question,
            "evidence_level": "E0_UNAVAILABLE_OFFICIAL_SOURCE",
            "analytical_state": "NOT_EXECUTED_OFFICIAL_SOURCE_UNAVAILABLE",
            "editorial_state": "NEGATIVE_RESULT_SOURCE_DEPENDENT",
            "education_outcome": education_outcome,
            "territorial_or_socioeconomic_dimension": dimension,
            "same_record": False,
            "same_person": False,
            "unit_of_analysis": "weighted_resident_person_record_not_materialized",
            "territorial_lens": "person_residence_same_record_required_not_materialized",
            "period": "Censo 2022 sample pending",
            "universe": "target populations not materialized",
            "method": method,
            "validation": unavailable,
            "regional_result": unavailable,
            "ten_municipality_heterogeneity": unavailable,
            "selected_municipality_result": unavailable,
            "nova_santa_rita_result": unavailable,
            "context_adjusted_result": None,
            "precision_state": "NO_ESTIMATE_NO_PRECISION_FABRICATED",
            "literature_mechanism": "NOT_APPLIED_WITHOUT_OFFICIAL_PERSON_RECORDS",
            "integrated_conclusion": conclusion,
            "incremental_value_beyond_separate_charts": (
                "Preserva uma lacuna substantiva e impede que agregados incompatíveis sejam "
                "apresentados como relação na mesma pessoa."
            ),
            "planning_implication": (
                "Aguardar a fonte oficial ou obter decisão gerencial explícita para uma versão "
                "sem lente de mesma pessoa."
            ),
            "monitoring_indicators": [
                "official_release_calendar",
                "official_download_files",
                "official_weighting_areas",
                "official_package_documentation",
            ],
            "institutional_coordination": ["IBGE", "gestão analítica", "julgamento externo"],
            "allowed_claims": [
                "informar indisponibilidade, evidência de fonte e decisão substantiva pendente"
            ],
            "forbidden_claims": [*common_forbidden, forbidden],
            "limitations": [dependency],
            "recommended_visual": "explicit_unavailable_state_no_estimate",
            "manager_review_state": "AWAIT_SOURCE_OR_SCOPE_DECISION",
            "main_candidate": False,
            "observed": False,
            "relationship_class": "UNAVAILABLE_CONDITIONAL_SAME_PERSON_RELATION",
            "claim_ceiling": "OFFICIAL_SOURCE_STATUS_ONLY",
            "editorial_role": "DETAIL",
            "same_person_required": True,
        }

    insights.extend(
        [
            negative_candidate(
                insight_id="NEG_F2_SAME_PERSON_STUDY_WORK_UNAVAILABLE",
                manager_question="Como estudo e trabalho coexistem na mesma pessoa jovem?",
                education_outcome="situação de estudo na mesma pessoa",
                dimension="situação de trabalho e residência",
                method="not executed; official sample, weights and documentation unavailable",
                conclusion=(
                    "Os microdados oficiais da amostra, as áreas de ponderação e a "
                    "documentação do pacote não satisfazem o gate; nenhuma estimativa "
                    "municipal de estudo–trabalho na mesma pessoa foi criada."
                ),
                dependency="depende da fonte oficial completa, documentação e pesos amostrais",
                forbidden="substituir vínculo RAIS por pessoa estudante",
            ),
            negative_candidate(
                insight_id="NEG_F5_MIGRATION_SCHOOL_SAME_PERSON_UNAVAILABLE",
                manager_question=(
                    "Migração recente e reorganização da oferta coexistem na mesma pessoa?"
                ),
                education_outcome="situação escolar na mesma pessoa",
                dimension="migração, residência e oferta escolar",
                method="not executed because F5 depends on the unavailable official F2 source",
                conclusion=(
                    "A frente permanece indisponível e não autoriza inferência municipal "
                    "sobre migração, residência e oferta escolar na mesma pessoa."
                ),
                dependency="depende da mesma fonte oficial completa ainda indisponível",
                forbidden="inferir migração ou acesso comparando agregados territoriais",
            ),
        ]
    )
    for item in insights:
        missing = sorted(set(CANDIDATE_REQUIRED_FIELDS) - set(item))
        if missing:
            raise Job5LFinalValidationError(
                f"Candidata {item.get('insight_id')} sem campos obrigatórios: {missing}"
            )
    return {
        "schemaVersion": "vocacoes-pne-job5l-final-insight-catalog-v2",
        "generatedAt": GENERATED_AT,
        "state": FINAL_STATE,
        "externalInputVerdict": "JOB_5L_ANALYTICALLY_USEFUL_BUT_NOT_READY_FOR_JOB_5M",
        "candidateInsightCount": len(insights),
        "mainCandidateCount": sum(bool(item["main_candidate"]) for item in insights),
        "maximumCandidateCount": 8,
        "automaticApproval": False,
        "externalJudgmentRequired": True,
        "crossCuttingI4Grammar": {
            "standaloneInsight": False,
            "catalogRecord": "I4_FUNCTIONAL_TERRITORIAL_GRAMMAR",
            "rule": (
                "população residente, matrícula por localização escolar e vínculo por "
                "localização do estabelecimento são lentes complementares e não equivalentes"
            ),
            "syntheticIndexMaterialized": False,
            "editorialRole": "DETAIL_GRAMMAR",
        },
        "requiredCandidateFields": list(CANDIDATE_REQUIRED_FIELDS),
        "insights": insights,
    }


def build_result_matrix(
    *,
    f1_results: pd.DataFrame,
    rais_panel: pd.DataFrame,
    eja_panel: pd.DataFrame,
    f2_f5: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    grammar = (
        "resident_population|school_location|establishment_location_workplace_"
        "kept_distinct"
    )
    for row in f1_results.itertuples(index=False):
        rows.append(
            {
                "insight_id": "I1_CONTEXT_ADJUSTED_EDUCATIONAL_TRAJECTORY",
                "front_id": "F1",
                "entity_scope": "municipality",
                "entity_id": row.municipality_ibge_code,
                "municipality_ibge_code": row.municipality_ibge_code,
                "municipality_name": row.municipality_name,
                "period": str(row.comparison_year),
                "stage": row.stage,
                "age_group": None,
                "metric_id": row.outcome_id,
                "dimension_code": "ALL",
                "dimension_label": "Todos os registros da etapa",
                "value": row.observed_value,
                "expected_value": row.expected_value,
                "expected_interval_lower": row.expected_interval_lower,
                "expected_interval_upper": row.expected_interval_upper,
                "period_initial_value": None,
                "period_final_value": row.observed_value,
                "period_absolute_change": None,
                "period_percent_change": None,
                "unit": "percent",
                "numerator": None,
                "denominator": None,
                "value_status": (
                    "unavailable" if _finite(row.observed_value) is None else "observed"
                ),
                "analytical_state": row.context_adjusted_state,
                "evidence_level": "E2_CONTEXT_ADJUSTED_COMPARISON",
                "comparison_basis": row.selected_comparison_basis,
                "bounded_by_construction": row.bounded_by_construction,
                "same_person": False,
                "unit_of_analysis": row.unit_of_analysis,
                "territorial_lens": row.territorial_lens,
                "source": (
                    "frozen_Job5L_official_database_snapshots_total_network_trajectory"
                ),
                "cross_cutting_lens_grammar": grammar,
                "ranking_allowed": False,
                "causal_interpretation_allowed": False,
            }
        )

    for _, row in rais_panel.iterrows():
        rows.append(
            {
                "insight_id": "I2_MERGED_YOUTH_WORK_COMPOSITION",
                "front_id": "F3",
                "entity_scope": row["entity_scope"],
                "entity_id": row["entity_id"],
                "municipality_ibge_code": row["municipality_ibge_code"],
                "municipality_name": row["municipality_name"],
                "period": str(int(row["year"])),
                "stage": None,
                "age_group": row["age_group"],
                "metric_id": row["metric_id"],
                "dimension_code": row["dimension_code"],
                "dimension_label": row["dimension_label"],
                "value": row["value"],
                "expected_value": None,
                "expected_interval_lower": None,
                "expected_interval_upper": None,
                "period_initial_value": row.get("period_initial_value_2019"),
                "period_final_value": row.get("period_final_value_2025"),
                "period_absolute_change": row.get("period_absolute_change_2019_2025"),
                "period_percent_change": row.get("period_percent_change_2019_2025"),
                "unit": row["unit"],
                "numerator": row["numerator"],
                "denominator": row["denominator"],
                "value_status": row["value_status"],
                "analytical_state": "OFFICIAL_OBSERVED_RECONCILED",
                "evidence_level": "E1_OFFICIAL_DESCRIPTIVE_RECONCILED_SERIES",
                "comparison_basis": "establishment_location_workplace",
                "bounded_by_construction": None,
                "same_person": False,
                "unit_of_analysis": "active_formal_bond_at_31_12",
                "territorial_lens": row["territorial_lens"],
                "source": row["source"],
                "cross_cutting_lens_grammar": grammar,
                "ranking_allowed": False,
                "causal_interpretation_allowed": False,
            }
        )

    frozen_i4 = _read_csv(
        PREVIOUS_JOB5L_ROOT / "MATRIZ_HETEROGENEIDADE_10_MUNICIPIOS_JOB5L.csv.gz"
    )
    frozen_i4 = frozen_i4[frozen_i4["front_id"].eq("F4")]
    for row in frozen_i4.itertuples(index=False):
        direct_value = _finite(row.direct_value)
        reference_value = _finite(row.comparison_value)
        rows.append(
            {
                "insight_id": "I4_FUNCTIONAL_TERRITORIAL_GRAMMAR",
                "front_id": "F4",
                "entity_scope": "municipality",
                "entity_id": row.municipality_ibge_code,
                "municipality_ibge_code": row.municipality_ibge_code,
                "municipality_name": row.municipality_name,
                "period": str(row.period),
                "stage": None,
                "age_group": None,
                "metric_id": row.dimension,
                "dimension_code": row.dimension,
                "dimension_label": row.dimension,
                "value": direct_value,
                "expected_value": None,
                "expected_interval_lower": None,
                "expected_interval_upper": None,
                "period_initial_value": None,
                "period_final_value": None,
                "period_absolute_change": None,
                "period_percent_change": None,
                "reference_value": reference_value,
                "difference_percentage_points": (
                    direct_value - reference_value
                    if direct_value is not None and reference_value is not None
                    else None
                ),
                "comparison_state": row.comparison_state,
                "unit": "percent_share_of_regional_component",
                "numerator": None,
                "denominator": None,
                "value_status": "observed" if direct_value is not None else "unavailable",
                "analytical_state": "CROSS_CUTTING_GRAMMAR_COMPONENT",
                "evidence_level": "E3_CROSS_LENS_TERRITORIAL_CONTRAST",
                "comparison_basis": "declared_lens_regional_component_share",
                "bounded_by_construction": None,
                "same_person": False,
                "unit_of_analysis": "municipal_share_of_regional_component",
                "territorial_lens": row.territorial_lens,
                "source": "frozen_Job5L_F4_cross_lens_components",
                "cross_cutting_lens_grammar": grammar,
                "ranking_allowed": False,
                "causal_interpretation_allowed": False,
            }
        )

    for row in eja_panel.itertuples(index=False):
        rows.append(
            {
                "insight_id": "I5_ADULT_SCHOOLING_AND_EJA_DISTRIBUTION",
                "front_id": "F6",
                "entity_scope": row.entity_scope,
                "entity_id": row.entity_id,
                "municipality_ibge_code": row.municipality_ibge_code,
                "municipality_name": row.municipality_name,
                "period": "2014_2025",
                "stage": row.stage,
                "age_group": None,
                "metric_id": "eja_stage_enrollment_trajectory",
                "dimension_code": row.stage,
                "dimension_label": row.stage,
                "value": row.eja_enrollments_2025,
                "expected_value": None,
                "expected_interval_lower": None,
                "expected_interval_upper": None,
                "period_initial_value": row.eja_enrollments_2014,
                "period_final_value": row.eja_enrollments_2025,
                "period_absolute_change": row.absolute_change_2014_2025,
                "period_percent_change": row.percent_change_2014_2025,
                "reference_value": row.share_of_regional_public_percent,
                "difference_percentage_points": (
                    row.distribution_difference_percentage_points
                ),
                "comparison_state": row.distribution_direction,
                "resident_adult_public_2022": row.resident_adult_public,
                "school_location_eja_enrollments_2022": (
                    row.school_location_eja_enrollments
                ),
                "share_of_regional_public_percent": (
                    row.share_of_regional_public_percent
                ),
                "share_of_regional_enrollments_percent": (
                    row.share_of_regional_enrollments_percent
                ),
                "adult_panel_compatibility": row.adult_panel_compatibility,
                "unit": row.unit,
                "numerator": None,
                "denominator": None,
                "value_status": row.value_status,
                "analytical_state": row.front_state,
                "evidence_level": "E3_AGGREGATE_TERRITORIAL_CONTRAST",
                "comparison_basis": (
                    "stage_separated_distribution_contrast_and_enrollment_counts"
                ),
                "bounded_by_construction": None,
                "same_person": False,
                "unit_of_analysis": "resident_population_vs_located_eja_enrollments",
                "territorial_lens": row.territorial_lens,
                "source": row.source,
                "cross_cutting_lens_grammar": grammar,
                "ranking_allowed": False,
                "causal_interpretation_allowed": False,
            }
        )

    for row in f2_f5.itertuples(index=False):
        insight_id = (
            "NEG_F2_SAME_PERSON_STUDY_WORK_UNAVAILABLE"
            if row.front_id == "F2"
            else "NEG_F5_MIGRATION_SCHOOL_SAME_PERSON_UNAVAILABLE"
        )
        rows.append(
            {
                "insight_id": insight_id,
                "front_id": row.front_id,
                "entity_scope": row.entity_scope,
                "entity_id": row.entity_id,
                "municipality_ibge_code": row.municipality_ibge_code,
                "municipality_name": row.municipality_name,
                "period": "2022_sample_pending",
                "stage": None,
                "age_group": row.age_group,
                "metric_id": row.measure,
                "dimension_code": "NOT_AVAILABLE",
                "dimension_label": "Fonte oficial indisponível",
                "value": row.value,
                "expected_value": None,
                "expected_interval_lower": None,
                "expected_interval_upper": None,
                "period_initial_value": None,
                "period_final_value": None,
                "period_absolute_change": None,
                "period_percent_change": None,
                "unit": row.unit,
                "numerator": None,
                "denominator": None,
                "value_status": row.value_status,
                "analytical_state": row.front_state,
                "evidence_level": "E0_UNAVAILABLE_OFFICIAL_SOURCE",
                "comparison_basis": "not_executed",
                "bounded_by_construction": None,
                "same_person": True,
                "unit_of_analysis": "weighted_resident_person_record_not_materialized",
                "territorial_lens": row.territorial_lens,
                "source": "IBGE_Censo_2022_sample_microdata_not_available",
                "cross_cutting_lens_grammar": grammar,
                "ranking_allowed": False,
                "causal_interpretation_allowed": False,
            }
        )
    return _stable_frame(
        pd.DataFrame(rows),
        [
            "insight_id",
            "front_id",
            "period",
            "entity_scope",
            "entity_id",
            "stage",
            "age_group",
            "metric_id",
            "dimension_code",
        ],
    )


def build_heterogeneity_matrix(result_matrix: pd.DataFrame) -> pd.DataFrame:
    codes = set(job5l._region_codes())
    municipal = result_matrix[
        result_matrix["municipality_ibge_code"].astype("string").isin(codes)
    ].copy()
    f1 = municipal[municipal["front_id"].eq("F1")]
    rais_metrics = {
        "active_bonds",
        "bond_type_composition_share_percent",
        "schooling_composition_share_percent",
        "contracted_weekly_hours_mean",
        "bond_tenure_median",
        "nominal_average_monthly_remuneration_median",
        "top4_occupation_concentration_share_percent",
        "top4_sector_concentration_share_percent",
    }
    rais = municipal[
        municipal["front_id"].eq("F3")
        & municipal["period"].eq("2025")
        & municipal["metric_id"].isin(rais_metrics)
    ].copy()
    rais = rais[
        ~rais["metric_id"].eq("bond_type_composition_share_percent")
        | rais["dimension_code"].eq("apprentice_contract")
    ]
    rais = rais[
        ~rais["metric_id"].eq("schooling_composition_share_percent")
        | rais["dimension_code"].eq("high_school_complete")
    ]
    functional = municipal[municipal["front_id"].eq("F4")]
    eja = municipal[municipal["front_id"].eq("F6")]
    selected = pd.concat([f1, rais, functional, eja], ignore_index=True, sort=False)
    selected["heterogeneity_selection"] = np.select(
        [
            selected["front_id"].eq("F1"),
            selected["front_id"].eq("F3"),
            selected["front_id"].eq("F4"),
            selected["front_id"].eq("F6"),
        ],
        [
            "all_2025_bounded_trajectory_comparisons",
            "selected_2025_youth_work_composition_metrics",
            "cross_cutting_declared_lens_comparisons",
            "stage_separated_eja_2014_2025_counts",
        ],
        default="not_selected",
    )
    actual_codes = set(
        selected["municipality_ibge_code"].dropna().astype(str).unique().tolist()
    )
    if actual_codes != codes or NSR_CODE not in actual_codes:
        raise Job5LFinalValidationError("Heterogeneidade final não cobre os 10 municípios")
    return _stable_frame(
        selected,
        [
            "municipality_ibge_code",
            "front_id",
            "stage",
            "age_group",
            "metric_id",
            "dimension_code",
        ],
    )


def build_source_registry(
    *,
    censo_status: Mapping[str, Any],
    rais_details: Mapping[str, Any],
    frozen_inputs: Mapping[str, Any],
) -> dict[str, Any]:
    documentation_root = PREVIOUS_JOB5L_ROOT / "sources" / "rais" / "documentation"
    documentation = [
        {
            "path": path.relative_to(REPO_ROOT).as_posix(),
            "byteSize": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for path in sorted(documentation_root.rglob("*"))
        if path.is_file()
    ]
    database_manifest = _json(
        PREVIOUS_JOB5L_ROOT / "sources" / "database" / "manifest.json"
    )
    literature = _json(PREVIOUS_JOB5L_ROOT / "LITERATURA_E_MECANISMOS_JOB5L.json")
    frozen_cross_lens_paths = [
        PREVIOUS_JOB5L_ROOT / "CATALOGO_INSIGHTS_APROFUNDADOS_JOB5L.json",
        PREVIOUS_JOB5L_ROOT / "MATRIZ_HETEROGENEIDADE_10_MUNICIPIOS_JOB5L.csv.gz",
        JOB5J_ROOT / "CATALOGO_INSIGHTS_CANDIDATOS_JOB5J.json",
        JOB5K_ROOT / "BUNDLE_INSIGHTS_UI_JOB5K.json",
    ]
    return {
        "schemaVersion": "vocacoes-pne-job5l-final-source-registry-v2",
        "generatedAt": GENERATED_AT,
        "officialSourcesOnlyForNewAcquisition": True,
        "networkUsed": True,
        "networkPurpose": "current_official_IBGE_source_state_verification_only",
        "databaseUsedDuringJob5LFinal": False,
        "databaseWritePerformed": False,
        "censo2022Sample": censo_status,
        "rais": {
            "terminalState": rais_details["terminalState"],
            "sourceValidation": rais_details["sourceValidation"],
            "reconciliation": rais_details["reconciliationWithFrozenAggregate"],
            "auditContract": rais_details["auditContract"],
            "serviceVersusEstablishmentLocationAudit": rais_details[
                "serviceVersusEstablishmentLocationAudit"
            ],
            "officialDocumentationFiles": documentation,
            "measurementDistinction": {
                "activeRaisApprenticeship": (
                    "stock of active apprenticeship bonds at 31 December"
                ),
                "cagedApprenticeAdmissions": (
                    "admission events classified as apprenticeship during the year"
                ),
                "interchangeable": False,
            },
        },
        "frozenCrossLensAndCagedSupport": [
            {
                "path": path.relative_to(REPO_ROOT).as_posix(),
                "byteSize": path.stat().st_size,
                "sha256": sha256_file(path),
                "readOnly": True,
            }
            for path in frozen_cross_lens_paths
        ],
        "f1FrozenDatabaseSnapshots": {
            "source": "read_only_snapshots_materialized_by_frozen_Job5L",
            "manifest": database_manifest,
            "liveDatabaseAccessPerformed": False,
            "officialIndicatorFormulaChanged": False,
        },
        "ipca": {
            "state": "NOT_MATERIALIZED",
            "reason": (
                "O insight final usa remuneração nominal somente no perfil corrente de 2025; "
                "nenhuma tendência de remuneração real é afirmada. A aquisição opcional não "
                "foi usada para atrasar os bloqueios substantivos."
            ),
            "historicalNominalPayTrendClaimAllowed": False,
        },
        "literature": literature,
        "frozenInputProof": frozen_inputs,
    }


def build_limits(
    *,
    censo_status: Mapping[str, Any],
    f1_validation: pd.DataFrame,
    rais_details: Mapping[str, Any],
) -> dict[str, Any]:
    context_models = int(
        (
            f1_validation["validation_eligible"].astype(bool)
            & f1_validation["context_covariates_added_value_oos"].astype(bool)
        ).sum()
    )
    return {
        "schemaVersion": "vocacoes-pne-job5l-final-limits-claims-v2",
        "generatedAt": GENERATED_AT,
        "finalState": FINAL_STATE,
        "externalJudgmentRequired": True,
        "automaticApproval": False,
        "job5MAllowed": False,
        "gate11": "CLOSED",
        "frontStates": {
            "F1": "BOUNDED_HISTORY_CONTEXT_COMPARISON_MATERIALIZED",
            "F2": "NOT_EXECUTED_OFFICIAL_SOURCE_UNAVAILABLE",
            "F3": rais_details["terminalState"],
            "F4": "CROSS_CUTTING_LENS_GRAMMAR_COMPONENTS_PRESERVED_NOT_STANDALONE_STORY",
            "F5": "NOT_EXECUTED_OFFICIAL_SOURCE_UNAVAILABLE",
            "F6": (
                "STAGE_SEPARATED_AGGREGATE_DISTRIBUTION_AND_ENROLLMENT_TRAJECTORY"
            ),
        },
        "f1": {
            "contextAddsValueModelCount": context_models,
            "contextLanguageAllowedOnlyWhereOutOfSampleGainPasses": True,
            "ratesAndIntervalsBoundedZeroToOneHundredByConstruction": True,
            "postPredictionClippingApplied": False,
            "allowed": [
                "dentro/acima/abaixo do intervalo para combinações elegíveis",
                "histórico recente",
                "contexto observado somente quando acrescenta valor fora da amostra",
            ],
            "forbidden": ["efeito escolar", "causalidade", "valor agregado", "ranking"],
        },
        "censo": {
            "state": censo_status["state"],
            "samePersonClaimAllowed": False,
            "definitiveJob5MAuthorizationAllowed": False,
            "substantiveDecision": censo_status["substantiveDecision"],
            "availabilityRequirements": censo_status["availabilityRequirements"],
            "announcementAloneCountsAsAvailability": False,
        },
        "rais": {
            "unit": "active_formal_bond_at_31_12",
            "uniquePersonClaimAllowed": False,
            "residentYouthClaimAllowed": False,
            "trend2019To2025Allowed": True,
            "realPayTrendClaimAllowed": False,
            "current2025NominalPayDescriptionAllowed": True,
            "activeApprenticeshipMeasure": (
                "active_apprenticeship_bond_stock_at_31_12"
            ),
            "cagedApprenticeshipMeasure": "apprentice_admission_event_flow_during_year",
            "activeRaisAndCagedAdmissionsInterchangeable": False,
        },
        "eja": {
            "stagesMustRemainSeparate": True,
            "residentAdultAndLocatedEnrollmentCountsPreserved": True,
            "regionalDistributionDifferencePercentagePointsPreserved": True,
            "fundamentalAdultPanelCompatibility": (
                "DEFINITION_INCOMPATIBLE_POPULATION_TOTAL_SOURCE"
            ),
            "fundamentalFullyComparableAdultPanelClaimAllowed": False,
            "perThousandRateAllowed": False,
            "coverageDemandOrDeficitClaimAllowed": False,
            "samePersonClaimAllowed": False,
        },
        "crossCuttingI4Grammar": {
            "standaloneStoryAllowed": False,
            "syntheticIndexAllowed": False,
            "componentsPreserved": [
                "active_bonds_15_17_vs_resident_population_15_17",
                "active_bonds_18_24_vs_resident_population_18_24",
                "active_apprenticeship_bonds_vs_resident_population_15_17",
                "located_high_school_offer_vs_resident_population_15_17",
                "occupational_transformation_vs_located_EPT",
                "resident_adult_public_vs_located_EJA",
            ],
            "lensesMustRemainDistinct": [
                "resident_population",
                "school_location",
                "establishment_location_workplace",
            ],
        },
        "globalForbiddenClaims": [
            "causalidade local",
            "ranking de municípios",
            "ligação individual entre fontes",
            "vínculo RAIS como pessoa única",
            "matrícula EJA como demanda ou déficit",
            "estoque RAIS de aprendizagem como evento de admissão Caged",
            "autorização automática do Job 5M",
        ],
        "pne": {
            "officialIndicatorRecalculated": False,
            "formulaChanged": False,
            "sourceChanged": False,
            "yearChanged": False,
        },
        "pme": {"state": "not_materialized"},
    }


def build_qa(analysis: Mapping[str, Any]) -> dict[str, Any]:
    controls: list[dict[str, Any]] = []

    def record(control_id: str, passed: bool, evidence: Any) -> None:
        controls.append(
            {
                "controlId": control_id,
                "status": "PASS" if passed else "FAIL",
                "evidence": _json_safe(evidence),
            }
        )

    f1 = analysis["f1_results"]
    validation = analysis["f1_validation"]
    eligible = validation["validation_eligible"].astype(bool)
    noneligible = set(
        zip(
            validation.loc[~eligible, "outcome_id"],
            validation.loc[~eligible, "stage"],
            strict=True,
        )
    )
    bound_columns = [
        "expected_value",
        "expected_interval_lower",
        "expected_interval_upper",
    ]
    bounded = all(
        pd.to_numeric(f1[column], errors="coerce")
        .dropna()
        .between(0, 100, inclusive="both")
        .all()
        for column in bound_columns
    )
    comparable = f1.dropna(
        subset=[
            "expected_value",
            "expected_interval_lower",
            "expected_interval_upper",
        ]
    )
    ordered = (
        (
            pd.to_numeric(comparable["expected_interval_lower"], errors="coerce")
            <= pd.to_numeric(comparable["expected_value"], errors="coerce")
        )
        & (
            pd.to_numeric(comparable["expected_value"], errors="coerce")
            <= pd.to_numeric(comparable["expected_interval_upper"], errors="coerce")
        )
    ).all()
    record("shared_file_contract", len(PACKAGE_FILES) == 12, len(PACKAGE_FILES))
    record(
        "f1_complete_grid",
        len(f1) == 497 * 3 * 4
        and f1["municipality_ibge_code"].astype(str).nunique() == 497,
        {"rows": len(f1), "municipalities": f1["municipality_ibge_code"].nunique()},
    )
    record(
        "f1_model_gates",
        len(validation) == 12
        and int(eligible.sum()) == 11
        and noneligible
        == {("dropout_rate_percent", "fundamental_anos_iniciais")},
        {"eligible": int(eligible.sum()), "notEvaluable": sorted(noneligible)},
    )
    record(
        "f1_history_context_comparison",
        validation["history_only_group_holdout_mae"].notna().all()
        and validation["history_plus_context_group_holdout_mae"].notna().all(),
        {
            "contextAddsValue": int(
                validation["context_covariates_added_value_oos"].astype(bool).sum()
            )
        },
    )
    record(
        "f1_bounded_by_construction",
        bool(bounded and ordered)
        and f1["bounded_by_construction"].astype(bool).all()
        and not f1["post_prediction_clipping_applied"].astype(bool).any(),
        {"bounded": bounded, "ordered": bool(ordered)},
    )
    reconciliation = analysis["rais_details"]["reconciliationWithFrozenAggregate"]
    record(
        "rais_exact_reconciliation",
        reconciliation["terminalState"] == "RAIS_2019_2025_CANONICAL_RECONCILED"
        and reconciliation["exactMatchCount"] == 140
        and reconciliation["mismatchCount"] == 0,
        reconciliation,
    )
    record(
        "rais_single_territorial_lens",
        analysis["rais_panel"]["territorial_lens"]
        .eq("establishment_location_workplace")
        .all(),
        analysis["rais_panel"]["territorial_lens"].value_counts().to_dict(),
    )
    censo = analysis["censo_status"]
    record(
        "censo_current_state",
        not censo["sampleMicrodataAvailable"]
        and not censo["weightingAreasAvailable"]
        and not censo["packageDocumentationAvailable"]
        and not censo["officialPackageAvailable"]
        and not all(censo["availabilityRequirements"].values())
        and set(censo["sourceAccess"]) == set(CENSO_URLS),
        {
            "state": censo["state"],
            "requirements": censo["availabilityRequirements"],
            "sourceIds": sorted(censo["sourceAccess"]),
        },
    )
    f2_f5 = analysis["f2_f5"]
    record(
        "f2_f5_no_fabricated_estimates",
        f2_f5["value"].isna().all()
        and f2_f5["front_state"].eq(
            "NOT_EXECUTED_OFFICIAL_SOURCE_UNAVAILABLE"
        ).all(),
        f2_f5.groupby("front_id").size().to_dict(),
    )
    eja = analysis["eja_panel"]
    nsr_eja = eja[eja["entity_id"].astype(str).eq(NSR_CODE)].set_index("stage")
    eja_anchor_ok = (
        math.isclose(
            float(
                nsr_eja.loc[
                    "fundamental", "distribution_difference_percentage_points"
                ]
            ),
            2.6482631443935167,
            rel_tol=0,
            abs_tol=1e-9,
        )
        and math.isclose(
            float(
                nsr_eja.loc[
                    "high_school", "distribution_difference_percentage_points"
                ]
            ),
            -2.6050945751099364,
            rel_tol=0,
            abs_tol=1e-9,
        )
        and float(nsr_eja.loc["fundamental", "eja_enrollments_2025"]) == 152
        and float(nsr_eja.loc["high_school", "eja_enrollments_2025"]) == 56
        and nsr_eja.loc["fundamental", "adult_panel_compatibility"]
        == "DEFINITION_INCOMPATIBLE_POPULATION_TOTAL_SOURCE"
    )
    record(
        "eja_stage_separation_and_claim_ceiling",
        set(eja["stage"]) == {"fundamental", "high_school"}
        and not eja["per_thousand_rate_materialized"].astype(bool).any()
        and not eja["coverage_demand_or_deficit_claim_allowed"].astype(bool).any()
        and eja["distribution_contrast_materialized"].astype(bool).all()
        and "eja_enrollments_per_thousand_resident_public_2022" not in eja.columns
        and eja_anchor_ok,
        {
            "stages": sorted(eja["stage"].unique().tolist()),
            "rows": len(eja),
            "novaSantaRitaAnchorsPreserved": bool(eja_anchor_ok),
        },
    )
    catalog = analysis["catalog"]
    ids = [item["insight_id"] for item in catalog["insights"]]
    required_ids = {
        "I1_CONTEXT_ADJUSTED_EDUCATIONAL_TRAJECTORY",
        "I2_MERGED_YOUTH_WORK_COMPOSITION",
        "I4_FUNCTIONAL_TERRITORIAL_GRAMMAR",
        "I5_ADULT_SCHOOLING_AND_EJA_DISTRIBUTION",
        "NEG_F2_SAME_PERSON_STUDY_WORK_UNAVAILABLE",
        "NEG_F5_MIGRATION_SCHOOL_SAME_PERSON_UNAVAILABLE",
    }
    missing_fields = {
        item["insight_id"]: sorted(set(CANDIDATE_REQUIRED_FIELDS) - set(item))
        for item in catalog["insights"]
        if set(CANDIDATE_REQUIRED_FIELDS) - set(item)
    }
    catalog_by_id = {item["insight_id"]: item for item in catalog["insights"]}
    record(
        "candidate_catalog_contract",
        len(ids) <= 8
        and set(ids) == required_ids
        and not any(value in ids for value in ("I2", "I3", "I4"))
        and not catalog["crossCuttingI4Grammar"]["standaloneInsight"]
        and not missing_fields
        and catalog_by_id["I1_CONTEXT_ADJUSTED_EDUCATIONAL_TRAJECTORY"][
            "editorial_role"
        ]
        == "CONTEXT"
        and catalog_by_id["I4_FUNCTIONAL_TERRITORIAL_GRAMMAR"][
            "editorial_role"
        ]
        == "DETAIL_GRAMMAR"
        and not catalog_by_id["I4_FUNCTIONAL_TERRITORIAL_GRAMMAR"][
            "main_candidate"
        ],
        {"ids": ids, "missingFields": missing_fields},
    )
    distinction = catalog_by_id["I2_MERGED_YOUTH_WORK_COMPOSITION"][
        "measurement_distinction"
    ]
    record(
        "rais_active_apprenticeship_distinct_from_caged_admissions",
        not distinction["labelsInterchangeable"]
        and not distinction["stocksAndEventsInterchangeable"]
        and distinction["novaSantaRita2025"]["raisActiveBondStock15To17"] == 172
        and distinction["novaSantaRita2025"]["cagedApprenticeAdmissionEvents"] == 174,
        distinction,
    )
    result_matrix = analysis["result_matrix"]
    record(
        "final_matrix_preserves_i4_and_i5_components",
        result_matrix["insight_id"].eq(
            "I4_FUNCTIONAL_TERRITORIAL_GRAMMAR"
        ).any()
        and result_matrix["insight_id"].eq(
            "I5_ADULT_SCHOOLING_AND_EJA_DISTRIBUTION"
        ).any()
        and result_matrix.loc[
            result_matrix["front_id"].eq("F6"),
            "difference_percentage_points",
        ].notna().all(),
        result_matrix["insight_id"].value_counts().to_dict(),
    )
    heterogeneity_codes = set(
        analysis["heterogeneity"]["municipality_ibge_code"].dropna().astype(str)
    )
    record(
        "ten_municipality_heterogeneity",
        heterogeneity_codes == set(job5l._region_codes())
        and NSR_CODE in heterogeneity_codes,
        sorted(heterogeneity_codes),
    )
    record(
        "municipality_identity_textual",
        all(IBGE_CODE_PATTERN.fullmatch(code) for code in heterogeneity_codes),
        "seven_digit_textual_IBGE_codes",
    )
    record(
        "frozen_and_public_input_proof",
        bool(analysis["frozen_inputs"]["publicDataTreeDigestSha256"]),
        analysis["frozen_inputs"],
    )
    failed = [item for item in controls if item["status"] == "FAIL"]
    return {
        "schemaVersion": "vocacoes-pne-job5l-final-qa-v2",
        "generatedAt": GENERATED_AT,
        "result": "PASS_WITH_EXPLICIT_LIMITS" if not failed else "FAIL_CLOSED",
        "controlCount": len(controls),
        "passedCount": len(controls) - len(failed),
        "failedCount": len(failed),
        "controls": controls,
        "finalState": FINAL_STATE,
        "externalJudgmentRequired": True,
        "job5MStarted": False,
    }


def assemble_analysis(
    *,
    source_root: Path,
    frozen_inputs: Mapping[str, Any],
) -> dict[str, Any]:
    censo_status = build_censo_status(source_root / "ibge-censo-2022")
    context, f1_grid = job5l.build_f1_context(
        PREVIOUS_JOB5L_ROOT / "sources" / "database"
    )
    f1_results, f1_validation, f1_models = fit_f1_final(f1_grid)
    rais_panel, rais_details = build_rais_final(
        PREVIOUS_JOB5L_ROOT / "sources" / "rais" / "raw"
    )
    eja_panel = build_eja_final()
    f2_f5 = build_f2_f5_unavailable(censo_status)
    catalog = build_candidate_catalog(
        f1_results=f1_results,
        f1_validation=f1_validation,
        rais_panel=rais_panel,
        eja_panel=eja_panel,
        censo_status=censo_status,
    )
    result_matrix = build_result_matrix(
        f1_results=f1_results,
        rais_panel=rais_panel,
        eja_panel=eja_panel,
        f2_f5=f2_f5,
    )
    heterogeneity = build_heterogeneity_matrix(result_matrix)
    sources = build_source_registry(
        censo_status=censo_status,
        rais_details=rais_details,
        frozen_inputs=frozen_inputs,
    )
    limits = build_limits(
        censo_status=censo_status,
        f1_validation=f1_validation,
        rais_details=rais_details,
    )
    analysis: dict[str, Any] = {
        "context": context,
        "f1_results": f1_results,
        "f1_validation": f1_validation,
        "f1_models": f1_models,
        "rais_panel": rais_panel,
        "rais_details": rais_details,
        "eja_panel": eja_panel,
        "f2_f5": f2_f5,
        "censo_status": censo_status,
        "catalog": catalog,
        "result_matrix": result_matrix,
        "heterogeneity": heterogeneity,
        "sources": sources,
        "limits": limits,
        "frozen_inputs": frozen_inputs,
    }
    analysis["qa"] = build_qa(analysis)
    if analysis["qa"]["failedCount"]:
        failed = [
            item["controlId"]
            for item in analysis["qa"]["controls"]
            if item["status"] == "FAIL"
        ]
        raise Job5LFinalValidationError(f"QA analítico falhou: {failed}")
    return analysis


def checkpoint_markdown(analysis: Mapping[str, Any]) -> str:
    validation = analysis["f1_validation"]
    eligible = validation["validation_eligible"].astype(bool)
    context_count = int(
        (
            eligible
            & validation["context_covariates_added_value_oos"].astype(bool)
        ).sum()
    )
    reconciliation = analysis["rais_details"]["reconciliationWithFrozenAggregate"]
    censo = analysis["censo_status"]
    return f"""# Checkpoint Job 5L-final para julgamento externo

## Veredito de saída

`{FINAL_STATE}`

O Job 5L-final concluiu o que era analiticamente executável, mas **não autoriza o Job 5M**. A série RAIS foi reconciliada integralmente; F1 foi reconstruída com limites naturais e comparação explícita entre histórico e contexto; o Censo 2022 Amostra continua indisponível na fonte oficial verificada, portanto F2 e F5 não foram executadas.

## Resposta aos três bloqueios

1. **Censo 2022 Amostra:** a raiz oficial geral respondeu `{censo['ftpRootStatusCode']}`; Microdados, Áreas de Ponderação e documentação esperada responderam, respectivamente, `{censo['sampleMicrodataExpectedRootStatusCode']}`, `{censo['weightingAreasExpectedRootStatusCode']}` e `{censo['sampleDocumentationExpectedRootStatusCode']}`. Comunicado, calendário, landing pages, downloads, documentação, arquivos, data/hora, hashes e licença/proveniência foram registrados. Nenhuma estimativa mesma-pessoa foi criada. Decisão pendente: `{censo['substantiveDecision']}`.
2. **RAIS 2019–2025:** `{reconciliation['terminalState']}`, com `{reconciliation['exactMatchCount']}/140` células exatas e `{reconciliation['mismatchCount']}` divergências. A causa foi a mistura anterior de `Mun Trab` com o município do estabelecimento.
3. **F1:** `{int(eligible.sum())}/12` combinações elegíveis; o contexto acrescentou valor fora da amostra em `{context_count}` delas. Todas as previsões e os intervalos estão em `[0,100]` por inversa logística ou média convexa de taxas observadas; nenhum truncamento pós-modelo foi aplicado.

## Catálogo final

- `I1_CONTEXT_ADJUSTED_EDUCATIONAL_TRAJECTORY`: contexto editorial secundário, com base específica por modelo — histórico recente ou histórico + contexto quando o ganho fora da amostra passou.
- `I2_MERGED_YOUTH_WORK_COMPOSITION`: história principal; perfil corrente e tendência 2019–2025 liberados após reconciliação canônica. Estoque ativo RAIS e eventos de admissão Caged permanecem medidas distintas.
- `I4_FUNCTIONAL_TERRITORIAL_GRAMMAR`: gramática transversal de lentes, incluindo transformação ocupacional × EPT; não é história autônoma nem índice sintético.
- `I5_ADULT_SCHOOLING_AND_EJA_DISTRIBUTION`: história principal; contrastes de distribuição e contagens por etapa separada, com incompatibilidade explícita no fundamental e sem taxa por mil, cobertura, demanda ou déficit.
- F2 e F5: indisponibilidades explícitas, mantidas no catálogo para impedir substituições indevidas.

## O que não foi feito

- nenhuma mudança em frontend, navegação ou `public/data`;
- nenhum build completo, deploy ou publicação;
- nenhum acesso ou escrita em banco no Job 5L-final;
- nenhuma ligação individual entre fontes;
- nenhuma autoaprovação, Gate 11 ou início do Job 5M.

## Próxima decisão legítima

Julgamento externo das duas histórias principais, do contexto I1 e da gramática I4, além da decisão substantiva sobre aguardar a fonte oficial do Censo ou aprovar uma versão gerencial sem a lente mesma-pessoa. O pacote não toma essa decisão automaticamente.
"""


def _f1_table(rows: pd.DataFrame) -> str:
    lines = [
        "| Etapa | Indicador | Observado | Esperado | Intervalo 90% | Base | Estado |",
        "|---|---|---:|---:|---:|---|---|",
    ]
    for row in rows.sort_values(["stage", "outcome_id"], kind="mergesort").itertuples(
        index=False
    ):
        interval = (
            f"{_fmt(row.expected_interval_lower, 2)}–{_fmt(row.expected_interval_upper, 2)}"
            if _finite(row.expected_interval_lower) is not None
            else "não avaliável"
        )
        lines.append(
            f"| {row.stage} | {row.outcome_id} | {_fmt(row.observed_value, 2)} | "
            f"{_fmt(row.expected_value, 2)} | {interval} | "
            f"{row.selected_comparison_basis} | {row.context_adjusted_state} |"
        )
    return "\n".join(lines)


def _rais_profile_table(panel: pd.DataFrame, entity_id: str) -> str:
    metrics = [
        ("active_bonds", "ALL", "Vínculos ativos", 0),
        (
            "bond_type_composition_share_percent",
            "apprentice_contract",
            "Aprendizagem (%)",
            2,
        ),
        (
            "schooling_composition_share_percent",
            "high_school_complete",
            "Ensino médio completo (%)",
            2,
        ),
        ("contracted_weekly_hours_mean", "ALL", "Horas semanais médias", 2),
        ("bond_tenure_median", "ALL", "Tempo mediano (meses)", 2),
        (
            "top4_occupation_concentration_share_percent",
            None,
            "Concentração top 4 ocupações (%)",
            2,
        ),
        (
            "top4_sector_concentration_share_percent",
            None,
            "Concentração top 4 setores (%)",
            2,
        ),
        (
            "nominal_average_monthly_remuneration_median",
            "ALL",
            "Remuneração mediana nominal 2025 (R$)",
            2,
        ),
    ]
    lines = [
        "| Métrica | 15–17 | 18–24 |",
        "|---|---:|---:|",
    ]
    for metric_id, dimension, label, decimals in metrics:
        values = [
            _rais_value(
                panel,
                entity_id=entity_id,
                year=2025,
                age_group=age_group,
                metric_id=metric_id,
                dimension_code=dimension,
            )
            for age_group in ("15_17", "18_24")
        ]
        lines.append(
            f"| {label} | {_fmt(values[0], decimals)} | {_fmt(values[1], decimals)} |"
        )
    return "\n".join(lines)


def _eja_table(panel: pd.DataFrame, entity_id: str) -> str:
    selected = panel[panel["entity_id"].astype(str).eq(entity_id)]
    lines = [
        "| Etapa | Público adulto 2022 | EJA localizada 2022 | Part. público regional | Part. matrícula regional | Diferença | Compatibilidade | EJA 2014 | EJA 2025 |",
        "|---|---:|---:|---:|---:|---:|---|---:|---:|",
    ]
    for row in selected.sort_values("stage", kind="mergesort").itertuples(index=False):
        lines.append(
            f"| {row.stage} | {_fmt(row.resident_adult_public, 0)} | "
            f"{_fmt(row.school_location_eja_enrollments, 0)} | "
            f"{_fmt(row.share_of_regional_public_percent, 3)}% | "
            f"{_fmt(row.share_of_regional_enrollments_percent, 3)}% | "
            f"{_fmt(row.distribution_difference_percentage_points, 3)} p.p. | "
            f"{row.adult_panel_compatibility} | "
            f"{_fmt(row.eja_enrollments_2014, 0)} | "
            f"{_fmt(row.eja_enrollments_2025, 0)} |"
        )
    return "\n".join(lines)


def nsr_dossier_markdown(analysis: Mapping[str, Any]) -> str:
    f1 = analysis["f1_results"]
    nsr = f1[f1["municipality_ibge_code"].astype(str).eq(NSR_CODE)]
    high_school = nsr[nsr["stage"].eq("medio")]
    rais = analysis["rais_panel"]
    active_2019_15 = _rais_value(
        rais,
        entity_id=NSR_CODE,
        year=2019,
        age_group="15_17",
        metric_id="active_bonds",
        dimension_code="ALL",
    )
    active_2025_15 = _rais_value(
        rais,
        entity_id=NSR_CODE,
        year=2025,
        age_group="15_17",
        metric_id="active_bonds",
        dimension_code="ALL",
    )
    active_2019_18 = _rais_value(
        rais,
        entity_id=NSR_CODE,
        year=2019,
        age_group="18_24",
        metric_id="active_bonds",
        dimension_code="ALL",
    )
    active_2025_18 = _rais_value(
        rais,
        entity_id=NSR_CODE,
        year=2025,
        age_group="18_24",
        metric_id="active_bonds",
        dimension_code="ALL",
    )
    return f"""# Dossiê final — Nova Santa Rita

## Leitura gerencial

Nova Santa Rita combina três sinais descritivos que merecem leitura conjunta, mas não fusão de universos: trajetória educacional municipal em 2025, composição dos vínculos jovens localizados em estabelecimentos do município e trajetória das matrículas EJA por localização escolar. Nenhum desses blocos identifica a mesma pessoa entre fontes.

## I1 — Trajetória educacional de 2025

O quadro abaixo restringe a abertura ao ensino médio; o painel interno mantém as 12 combinações para auditoria. “Contexto” só aparece como base quando reduziu o erro fora da amostra em pelo menos 1%.

{_f1_table(high_school)}

No conjunto das 12 combinações municipais, os estados de Nova Santa Rita foram: {json.dumps(nsr['context_adjusted_state'].value_counts().to_dict(), ensure_ascii=False, sort_keys=True)}. Isso é uma comparação preditiva, não uma estimativa de efeito escolar.

## I2 — Composição do trabalho jovem, série reconciliada

Entre 15–17 anos, o estoque de vínculos ativos em estabelecimentos de Nova Santa Rita passou de {_fmt(active_2019_15, 0)} em 2019 para {_fmt(active_2025_15, 0)} em 2025. Entre 18–24, passou de {_fmt(active_2019_18, 0)} para {_fmt(active_2025_18, 0)}. A série está liberada porque as 140 células de reconciliação foram exatas.

{_rais_profile_table(rais, NSR_CODE)}

Remuneração é apresentada apenas em reais nominais de 2025. Vínculos não são pessoas únicas e a lente é a localização do estabelecimento, não a residência do jovem. “Aprendizagem” nesta tabela é estoque de vínculos ativos RAIS em 31/12; os eventos de admissão de aprendizes do Caged são fluxo anual, não entram nesses percentuais e não recebem o mesmo rótulo.

## I5 — Matrículas EJA por etapa

{_eja_table(analysis['eja_panel'], NSR_CODE)}

Fundamental e ensino médio permanecem separados. Em 2022, Nova Santa Rita registrou contraste de +2,648 p.p. no fundamental e −2,605 p.p. no médio; em 2025, 152 e 56 matrículas, respectivamente. O contraste do fundamental é preservado com `DEFINITION_INCOMPATIBLE_POPULATION_TOTAL_SOURCE` e não constitui painel adulto plenamente comparável. Não há taxa por mil, demanda, atendimento, cobertura ou déficit.

## I4 — Gramática funcional transversal

As comparações de vínculos, residentes, oferta, EPT e EJA permanecem componentes rotulados por lente. No contraste congelado transformação ocupacional × EPT, a CBO 414140 passou de 17 para 722 vínculos em Nova Santa Rita entre 2019 e 2025, enquanto a oferta EPT localizada em 2025 foi zero observado. Isso orienta pergunta de coordenação regional; não prova déficit curricular, falta de acesso ou eficiência.

## Ausências substantivas

F2 (estudo e trabalho na mesma pessoa) e F5 (migração e oferta na mesma pessoa) não foram executadas: o pacote oficial da Amostra do Censo 2022 e suas áreas de ponderação não estão disponíveis no estado oficial verificado em 30 de agosto de 2026.

## Teto de linguagem

É permitido descrever compatibilidade com o intervalo preditivo, composição de vínculos e trajetória de matrículas por etapa. Não é permitido atribuir causalidade, inferir residentes a partir da RAIS, tratar matrícula como demanda nem autorizar o Job 5M.
"""


def vale_dossier_markdown(analysis: Mapping[str, Any]) -> str:
    rais = analysis["rais_panel"]
    f1 = analysis["f1_results"]
    region_codes = set(job5l._region_codes())
    vale_f1 = f1[f1["municipality_ibge_code"].astype(str).isin(region_codes)]
    states = vale_f1["context_adjusted_state"].value_counts().to_dict()
    active_2019_15 = _rais_value(
        rais,
        entity_id=REGION_ID,
        year=2019,
        age_group="15_17",
        metric_id="active_bonds",
        dimension_code="ALL",
    )
    active_2025_15 = _rais_value(
        rais,
        entity_id=REGION_ID,
        year=2025,
        age_group="15_17",
        metric_id="active_bonds",
        dimension_code="ALL",
    )
    active_2019_18 = _rais_value(
        rais,
        entity_id=REGION_ID,
        year=2019,
        age_group="18_24",
        metric_id="active_bonds",
        dimension_code="ALL",
    )
    active_2025_18 = _rais_value(
        rais,
        entity_id=REGION_ID,
        year=2025,
        age_group="18_24",
        metric_id="active_bonds",
        dimension_code="ALL",
    )
    return f"""# Dossiê final — Vale do Sinos

## Leitura gerencial

O Vale do Sinos é referência territorial descritiva para os dez municípios, não benchmark causal nem ranking. População residente, matrículas por localização escolar e vínculos por localização do estabelecimento permanecem como lentes distintas.

## I1 — Heterogeneidade das trajetórias

Nos dez municípios e 12 combinações de etapa × indicador, os estados de 2025 foram: {json.dumps(states, ensure_ascii=False, sort_keys=True)}. Cada combinação usa histórico recente; covariáveis contextuais só integram a linguagem quando passaram o gate de ganho fora da amostra. A matriz de heterogeneidade preserva todas as observações municipais sem ordená-las.

## I2 — Trabalho jovem localizado na região

O estoque regional de 15–17 anos passou de {_fmt(active_2019_15, 0)} vínculos ativos em 2019 para {_fmt(active_2025_15, 0)} em 2025; o de 18–24 passou de {_fmt(active_2019_18, 0)} para {_fmt(active_2025_18, 0)}. A mudança é descritiva e deve ser lida com a cautela estrutural da captação integral pelo eSocial desde 2023.

{_rais_profile_table(rais, REGION_ID)}

“Aprendizagem” acima é estoque ativo RAIS em 31/12. Eventos de admissão de aprendizes do Caged são fluxo anual distinto e não são usados como substituto desse estoque.

## I5 — EJA regional por etapa

{_eja_table(analysis['eja_panel'], REGION_ID)}

As etapas não são somadas. Os contrastes de participações territoriais são preservados sem taxa por mil; o fundamental mantém incompatibilidade explícita de definição e as contagens não são convertidas em cobertura, demanda ou déficit.

## I4 — Gramática funcional regional

Os contrastes entre residência, trabalho, oferta e formação estruturam as demais histórias sem formar cartão autônomo. A transformação da CBO 414140 no Vale (303 → 2.124 vínculos) é lida ao lado de 13.945 matrículas EPT localizadas em 2025; a correlação municipal exploratória não foi sustentada, mas o desencontro territorial observado permanece útil para coordenação, sem inferência de mesma pessoa ou déficit curricular.

## Frentes não executadas

F2 e F5 permanecem indisponíveis. Sem o microdado oficial da Amostra do Censo 2022 e as áreas de ponderação, o pacote não pode sustentar composição estudo–trabalho ou migração–oferta na mesma pessoa e não pode autorizar uma versão definitiva do Job 5M.

## Limites

Nenhum resultado é causal, nenhum vínculo é pessoa única, nenhuma lente territorial substitui outra e nenhuma candidata está automaticamente aprovada para publicação.
"""


def methods_markdown(analysis: Mapping[str, Any]) -> str:
    validation = analysis["f1_validation"]
    f1_lines = [
        "| Indicador | Etapa | MAE histórico | MAE + contexto | Ganho contexto % | Base selecionada | Cobertura 2025 | Elegível |",
        "|---|---|---:|---:|---:|---|---:|---|",
    ]
    for row in validation.itertuples(index=False):
        f1_lines.append(
            f"| {row.outcome_id} | {row.stage} | "
            f"{_fmt(row.history_only_group_holdout_mae, 4)} | "
            f"{_fmt(row.history_plus_context_group_holdout_mae, 4)} | "
            f"{_fmt(row.context_incremental_mae_improvement_percent, 2)} | "
            f"{row.selected_comparison_basis} | {_fmt(row.temporal_interval_coverage, 4)} | "
            f"{'sim' if row.validation_eligible else 'não'} |"
        )
    rais_lines = [
        "| Ano | Total congelado | Total reconstruído | Células exatas | Diferença |",
        "|---:|---:|---:|---:|---:|",
    ]
    for row in analysis["rais_details"]["reconciliationWithFrozenAggregate"]["byYear"]:
        rais_lines.append(
            f"| {row['year']} | {_fmt(row['frozenAggregateTotal'], 0)} | "
            f"{_fmt(row['currentOfficialRawActiveAtYearEndTotal'], 0)} | "
            f"{row['exactMatchCellCount']}/20 | {_fmt(row['differenceCurrentMinusFrozen'], 0)} |"
        )
    return f"""# Métodos, validação, precisão e reconciliação — Job 5L-final

## Escopo e identidade

- Universo F1: 497 municípios do Rio Grande do Sul, códigos IBGE textuais de sete dígitos, rede total e dependência administrativa apenas como QA.
- Região analítica: Vale do Sinos, dez municípios; fixture: Nova Santa Rita (`4313375`).
- Nenhuma fórmula, ano, fonte ou indicador oficial PNE foi recalculado ou alterado.
- O Job cria métodos analíticos auxiliares; não cria indicadores oficiais.

## F1 — histórico versus contexto com suporte limitado

### Transformação

Para uma taxa observada `y` em `[0,100]`, o candidato ridge usa a transformação empírica `p=(y+0,5)/101` e `z=log(p/(1-p))`; sua previsão retorna por `100/(1+exp(-z))`. A correção de meia unidade torna 0 e 100 finitos. O candidato por pares usa média convexa ponderada pela distância entre taxas observadas, também dentro de `[0,100]`. Não há corte, `clip` ou truncamento posterior.

### Famílias e seleção pré-especificada

- `HISTORY_ONLY`: logit do resultado defasado, tendência anual e indicador 2020–2021.
- `HISTORY_PLUS_CONTEXT`: histórico mais população, matrícula localizada, composição etária, ruralidade, tempo integral, porte escolar, internet, adequação docente, INSE e escolaridade adulta agregada.
- Dentro de cada família, ridge compete com pares ponderados; ridge só vence quando reduz o MAE em pelo menos 1% sobre os pares.
- Cinco folds determinísticos por código IBGE impedem que um município apareça simultaneamente em treino e validação.
- O contexto é selecionado somente com MAE pelo menos 1% menor que o histórico e modelo pelo menos 0,5% melhor que a mediana anual.
- 2025 é holdout temporal, não entra na seleção de família ou hiperparâmetro.
- Intervalos de 90% usam score conformal fora da amostra normalizado pela distância do previsto até a fronteira pertinente: erro inferior dividido pela distância até 0 e erro superior dividido pela distância até 100. O quantil expande cada lado proporcionalmente e mantém os limites no suporte sem truncamento; cobertura temporal mínima de 80%.
- Sensibilidade exclui 2020 e 2021.

{chr(10).join(f1_lines)}

Combinação não avaliável preservada: abandono nos anos iniciais. Comparações elegíveis são preditivas, não causais.

## RAIS — reconciliação canônica

### Universo e filtros

- Fonte: microdados públicos não identificados da RAIS, MTE/PDET, 2019–2025.
- Grão: um registro de vínculo declarado; não há deduplicação por trabalhador porque a unidade é vínculo.
- Filtro: indicador de vínculo ativo em 31/12 igual a 1; idade entre 15 e 24 anos, inclusive.
- Faixas: 15–17 e 18–24.
- Todos os tipos de estabelecimento e de vínculo permanecem no universo; tipo de vínculo é dimensão analítica, não filtro.
- Município canônico: localização do estabelecimento — `MUNICIPIO` nos layouts legados e `Município - Código` nos reprocessados.
- `MUN TRAB`/`Município Trab - Código` representa local de prestação do serviço e foi usado apenas para provar a causa da divergência.

Os layouts oficiais distinguem explicitamente os dois campos. Em 2019–2022, a lente de estabelecimento reproduziu 80/80 células e a lente de prestação, 0/80. Somadas às 60/60 células já exatas de 2023–2025, o estado terminal é `RAIS_2019_2025_CANONICAL_RECONCILED`.

{chr(10).join(rais_lines)}

A série 2019–2025 de composição é elegível. Mudanças que cruzam 2023 mantêm cautela estrutural pela transição integral ao eSocial. Remuneração corrente é nominal de 2025; tendência real não foi materializada.

## Censo 2022 Amostra — gate de disponibilidade

A reverificação preservou respostas e hashes do comunicado mais recente, calendário, landing pages, índices de download, documentação esperada e termo oficial. A raiz geral respondeu 200; arquivos da Amostra, Áreas de Ponderação e documentação do pacote não satisfizeram conjuntamente o gate. Anúncio não conta como disponibilidade. F2 e F5 foram materializadas somente como indisponibilidade, com valores nulos e sem precisão inventada.

## EJA

São preservados, por etapa, o público adulto residente agregado de 2022, a matrícula EJA localizada, suas participações no total regional, a diferença em pontos percentuais e as contagens de 2014 e 2025. Fundamental e ensino médio permanecem separados. O fundamental usa fonte de população com incompatibilidade de definição e não pode ser apresentado como painel adulto plenamente comparável. Não há taxa por mil nem linguagem de atendimento, cobertura, demanda ou déficit.

## Gramática transversal I4

População residente, matrícula por localização escolar e vínculo por localização do estabelecimento podem ser lidos lado a lado, mas não são somados, divididos ou fundidos num índice. Os componentes congelados — inclusive transformação ocupacional × EPT — são preservados na matriz, enquanto I4 permanece gramática editorial transversal e não história autônoma. Estoque ativo de aprendizagem RAIS e eventos de admissão Caged continuam medidas distintas.

## Precisão e interpretação

- F1: incerteza preditiva validada no tempo e por município.
- RAIS/EJA: contagens administrativas; não recebem erro amostral fictício.
- Censo F2/F5: nenhuma estimativa sem microdados, pesos e áreas de ponderação oficiais.
- Literatura: fornece mecanismos e alternativas, nunca números municipais nem autorização causal.
"""


def _artifact_role(path: str) -> str:
    roles = {
        "CHECKPOINT_JOB5L_FINAL_FOR_PRO.md": "checkpoint executivo para julgamento externo",
        "CATALOGO_INSIGHTS_FINAIS_JOB5L.json": "catálogo final de candidatas e indisponibilidades",
        "MATRIZ_RESULTADOS_FINAIS_JOB5L.csv.gz": "matriz analítica integrada final",
        "MATRIZ_HETEROGENEIDADE_10_MUNICIPIOS_JOB5L_FINAL.csv.gz": "heterogeneidade sem ranking dos dez municípios",
        "DOSSIE_FINAL_NOVA_SANTA_RITA_JOB5L.md": "dossiê final da fixture municipal",
        "DOSSIE_FINAL_VALE_DO_SINOS_JOB5L.md": "dossiê final regional",
        "METODOS_VALIDACAO_PRECISAO_RECONCILIACAO_JOB5L_FINAL.md": "métodos, precisão e reconciliação",
        "FONTES_CENSO_RAIS_E_LITERATURA_JOB5L_FINAL.json": "fontes oficiais, hashes e literatura",
        "LIMITACOES_E_CLAIMS_JOB5L_FINAL.json": "tetos de linguagem e decisões pendentes",
        "QA_SUMMARY_JOB5L_FINAL.json": "controles de qualidade finais",
        "ARTIFACT_INDEX_JOB5L_FINAL.json": "índice de artefatos",
        "MANIFEST_JOB5L_FINAL.json": "manifesto final",
    }
    return roles.get(path, "artefato interno de reconstrução e auditoria")


def build_artifact_index(output_dir: Path) -> dict[str, Any]:
    records = []
    for relative in [*PACKAGE_FILES, *INTERNAL_FILES]:
        path = output_dir / relative
        self_or_manifest = relative in {
            "ARTIFACT_INDEX_JOB5L_FINAL.json",
            "MANIFEST_JOB5L_FINAL.json",
        }
        available = path.is_file() and not self_or_manifest
        records.append(
            {
                "path": relative,
                "role": _artifact_role(relative),
                "packageFile": relative in PACKAGE_FILES,
                "internalSupportingArtifact": relative in INTERNAL_FILES,
                "byteSize": path.stat().st_size if available else None,
                "sha256": sha256_file(path) if available else None,
                "hashStatus": (
                    "recorded"
                    if available
                    else "self_or_manifest_hashed_by_final_manifest"
                ),
            }
        )
    return {
        "schemaVersion": "vocacoes-pne-job5l-final-artifact-index-v1",
        "generatedAt": GENERATED_AT,
        "packageFileCount": len(PACKAGE_FILES),
        "internalSupportingArtifactCount": len(INTERNAL_FILES),
        "artifacts": records,
    }


def _implementation_records() -> list[dict[str, Any]]:
    paths = [
        CONTRACT_PATH,
        Path(__file__).resolve(),
        REPO_ROOT / "data_pipeline" / "scripts" / "run_vocacoes_pne_v7_job5l_final.py",
        REPO_ROOT / "data_pipeline" / "tests" / "test_vocacoes_pne_job5l_final.py",
        REPO_ROOT / "data_pipeline" / "src" / "vocacoes_pne_job5l.py",
    ]
    return [
        {
            "path": path.relative_to(REPO_ROOT).as_posix(),
            "byteSize": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for path in paths
        if path.is_file()
    ]


def write_package(
    *,
    output_dir: Path,
    source_root: Path,
    analysis: Mapping[str, Any],
    execplan_text: str,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=False)
    (output_dir / "internal").mkdir()

    write_json(output_dir / "internal" / "CONTRATO_JOB5L_FINAL.json", _json(CONTRACT_PATH))
    (output_dir / "internal" / "EXECPLAN_JOB5L_FINAL.md").write_text(
        execplan_text.rstrip() + "\n", encoding="utf-8", newline="\n"
    )
    write_json(
        output_dir / "internal" / "CENSO_2022_STATUS_ATUAL_JOB5L_FINAL.json",
        _json_safe(analysis["censo_status"]),
    )
    write_csv_gzip(
        output_dir / "internal" / "RESULTADOS_F1_JOB5L_FINAL.csv.gz",
        analysis["f1_results"],
    )
    write_csv_gzip(
        output_dir / "internal" / "VALIDACAO_F1_JOB5L_FINAL.csv.gz",
        analysis["f1_validation"],
    )
    write_json(
        output_dir / "internal" / "MODELOS_F1_JOB5L_FINAL.json",
        _json_safe(analysis["f1_models"]),
    )
    write_csv_gzip(
        output_dir / "internal" / "PAINEL_RAIS_JOB5L_FINAL.csv.gz",
        analysis["rais_panel"],
    )
    write_json(
        output_dir / "internal" / "AUDITORIA_RAIS_JOB5L_FINAL.json",
        _json_safe(analysis["rais_details"]),
    )
    write_csv_gzip(
        output_dir / "internal" / "PAINEL_EJA_JOB5L_FINAL.csv.gz",
        analysis["eja_panel"],
    )
    write_csv_gzip(
        output_dir / "internal" / "PAINEL_F2_F5_JOB5L_FINAL.csv.gz",
        analysis["f2_f5"],
    )
    write_json(
        output_dir / "internal" / "PROVA_ENTRADAS_CONGELADAS_JOB5L_FINAL.json",
        _json_safe(analysis["frozen_inputs"]),
    )

    write_json(
        output_dir / "CATALOGO_INSIGHTS_FINAIS_JOB5L.json",
        _json_safe(analysis["catalog"]),
    )
    write_csv_gzip(
        output_dir / "MATRIZ_RESULTADOS_FINAIS_JOB5L.csv.gz",
        analysis["result_matrix"],
    )
    write_csv_gzip(
        output_dir / "MATRIZ_HETEROGENEIDADE_10_MUNICIPIOS_JOB5L_FINAL.csv.gz",
        analysis["heterogeneity"],
    )
    (output_dir / "DOSSIE_FINAL_NOVA_SANTA_RITA_JOB5L.md").write_text(
        nsr_dossier_markdown(analysis), encoding="utf-8", newline="\n"
    )
    (output_dir / "DOSSIE_FINAL_VALE_DO_SINOS_JOB5L.md").write_text(
        vale_dossier_markdown(analysis), encoding="utf-8", newline="\n"
    )
    (output_dir / "METODOS_VALIDACAO_PRECISAO_RECONCILIACAO_JOB5L_FINAL.md").write_text(
        methods_markdown(analysis), encoding="utf-8", newline="\n"
    )
    write_json(
        output_dir / "FONTES_CENSO_RAIS_E_LITERATURA_JOB5L_FINAL.json",
        _json_safe(analysis["sources"]),
    )
    write_json(
        output_dir / "LIMITACOES_E_CLAIMS_JOB5L_FINAL.json",
        _json_safe(analysis["limits"]),
    )
    write_json(
        output_dir / "QA_SUMMARY_JOB5L_FINAL.json", _json_safe(analysis["qa"])
    )
    (output_dir / "CHECKPOINT_JOB5L_FINAL_FOR_PRO.md").write_text(
        checkpoint_markdown(analysis), encoding="utf-8", newline="\n"
    )
    write_json(
        output_dir / "ARTIFACT_INDEX_JOB5L_FINAL.json",
        build_artifact_index(output_dir),
    )

    declared_paths = [
        relative
        for relative in [*PACKAGE_FILES, *INTERNAL_FILES]
        if relative != "MANIFEST_JOB5L_FINAL.json"
    ]
    validation = analysis["f1_validation"]
    reconciliation = analysis["rais_details"]["reconciliationWithFrozenAggregate"]
    manifest = {
        "schemaVersion": "vocacoes-pne-job5l-final-manifest-v1",
        "jobId": "v7-job5l-final",
        "generatedAt": GENERATED_AT,
        "classification": "SOURCE_REFRESH",
        "domains": [
            "DATA_LOGIC",
            "OFFICIAL_SOURCE_REVERIFICATION",
            "RAIS_CANONICAL_RECONCILIATION",
            "BOUNDED_CONTEXT_ADJUSTED_TRAJECTORIES",
        ],
        "finalState": FINAL_STATE,
        "externalInputVerdict": "JOB_5L_ANALYTICALLY_USEFUL_BUT_NOT_READY_FOR_JOB_5M",
        "externalJudgmentRequired": True,
        "automaticApproval": False,
        "gate11": "CLOSED",
        "job5MStarted": False,
        "packageFiles": list(PACKAGE_FILES),
        "internalSupportingArtifacts": list(INTERNAL_FILES),
        "artifacts": [
            {
                "path": relative,
                "byteSize": (output_dir / relative).stat().st_size,
                "sha256": sha256_file(output_dir / relative),
            }
            for relative in declared_paths
        ],
        "implementationFiles": _implementation_records(),
        "sourceCache": {
            "root": source_root.resolve().relative_to(REPO_ROOT.resolve()).as_posix(),
            "treeDigestSha256": directory_content_digest(source_root),
            "censoManifestSha256": analysis["censo_status"]["sourceManifestSha256"],
        },
        "frozenInputIntegrity": {
            "before": analysis["frozen_inputs"],
            "after": analysis["frozen_inputs"],
            "unchanged": True,
        },
        "publicDataIntegrity": {
            "beforeTreeDigestSha256": analysis["frozen_inputs"][
                "publicDataTreeDigestSha256"
            ],
            "afterTreeDigestSha256": analysis["frozen_inputs"][
                "publicDataTreeDigestSha256"
            ],
            "unchanged": True,
        },
        "counts": {
            "stateMunicipalityCount": 497,
            "regionMunicipalityCount": 10,
            "f1ResultRowCount": len(analysis["f1_results"]),
            "f1ModelCount": len(validation),
            "f1EligibleModelCount": int(validation["validation_eligible"].astype(bool).sum()),
            "f1ContextAddsValueModelCount": int(
                validation["context_covariates_added_value_oos"].astype(bool).sum()
            ),
            "raisPanelRowCount": len(analysis["rais_panel"]),
            "raisReconciliationExactCellCount": reconciliation["exactMatchCount"],
            "raisReconciliationMismatchCellCount": reconciliation["mismatchCount"],
            "ejaRowCount": len(analysis["eja_panel"]),
            "f2F5UnavailableRowCount": len(analysis["f2_f5"]),
            "candidateInsightCount": analysis["catalog"]["candidateInsightCount"],
            "mainCandidateCount": analysis["catalog"]["mainCandidateCount"],
            "integratedResultRowCount": len(analysis["result_matrix"]),
            "heterogeneityRowCount": len(analysis["heterogeneity"]),
            "qaControlCount": analysis["qa"]["controlCount"],
            "qaFailedCount": analysis["qa"]["failedCount"],
            "packageFileCount": len(PACKAGE_FILES),
            "internalSupportingArtifactCount": len(INTERNAL_FILES),
        },
        "frontStates": analysis["limits"]["frontStates"],
        "officialFormulasAltered": [],
        "officialSourcesYearsIndicatorsSchemasOrMethodologiesAltered": [],
        "analyticalMethodsAdded": [
            "bounded_empirical_logit_ridge",
            "bounded_nearest_context_peer_convex_average",
            "history_only_vs_history_plus_context_oos_comparison",
            "five_fold_municipality_holdout",
            "temporal_holdout_2025",
            "boundary_normalized_conformal_intervals",
            "sensitivity_excluding_2020_2021",
            "canonical_establishment_location_RAIS_reconciliation",
        ],
        "generation": {
            "deterministic": True,
            "twoIndependentMaterializationsRequired": True,
            "transactional": True,
            "manifestLast": True,
            "networkUsed": True,
            "networkUse": "official_IBGE_current_state_verification",
            "databaseUsed": False,
            "databaseWritePerformed": False,
            "newOfficialAcquisitionPerformed": True,
            "publicDataChanged": False,
            "frontendChanged": False,
            "navigationChanged": False,
            "fullBuildUsed": False,
            "publicationPerformed": False,
        },
    }
    write_json(output_dir / "MANIFEST_JOB5L_FINAL.json", _json_safe(manifest))
    validate_existing_output(
        output_dir, source_root=source_root, verify_sources=False
    )
    return manifest


def validate_existing_output(
    output_dir: Path = DEFAULT_OUTPUT_ROOT,
    *,
    source_root: Path | None = None,
    verify_sources: bool = True,
) -> dict[str, Any]:
    if not output_dir.is_dir():
        raise Job5LFinalValidationError(f"Pacote Job 5L-final ausente: {output_dir}")
    root_files = {path.name for path in output_dir.iterdir() if path.is_file()}
    if root_files != set(PACKAGE_FILES):
        raise Job5LFinalValidationError(
            "Topologia compartilhada divergente: "
            f"faltam={sorted(set(PACKAGE_FILES) - root_files)}, "
            f"extras={sorted(root_files - set(PACKAGE_FILES))}"
        )
    internal_root = output_dir / "internal"
    internal_actual = {
        path.relative_to(output_dir).as_posix()
        for path in internal_root.rglob("*")
        if path.is_file()
    }
    if internal_actual != set(INTERNAL_FILES):
        raise Job5LFinalValidationError(
            "Topologia interna divergente: "
            f"faltam={sorted(set(INTERNAL_FILES) - internal_actual)}, "
            f"extras={sorted(internal_actual - set(INTERNAL_FILES))}"
        )

    manifest = _json(output_dir / "MANIFEST_JOB5L_FINAL.json")
    if manifest["finalState"] != FINAL_STATE or manifest["gate11"] != "CLOSED":
        raise Job5LFinalValidationError("Estado terminal ou Gate 11 divergente")
    if manifest["job5MStarted"] or not manifest["externalJudgmentRequired"]:
        raise Job5LFinalValidationError("Job 5M ou autoaprovação indevida")
    if manifest["packageFiles"] != list(PACKAGE_FILES) or len(root_files) != 12:
        raise Job5LFinalValidationError("Pacote não contém exatamente os 12 compartilhados")
    if manifest["internalSupportingArtifacts"] != list(INTERNAL_FILES):
        raise Job5LFinalValidationError("Suportes internos divergem do contrato")
    declared = {record["path"]: record for record in manifest["artifacts"]}
    expected_declared = set(PACKAGE_FILES + INTERNAL_FILES) - {
        "MANIFEST_JOB5L_FINAL.json"
    }
    if set(declared) != expected_declared:
        raise Job5LFinalValidationError("Manifesto não cobre todos os artefatos")
    for relative, record in declared.items():
        path = output_dir / relative
        if path.stat().st_size != record["byteSize"] or sha256_file(path) != record["sha256"]:
            raise Job5LFinalValidationError(f"Hash/tamanho divergente: {relative}")

    contract = _json(output_dir / "internal" / "CONTRATO_JOB5L_FINAL.json")
    if contract["packageFiles"] != list(PACKAGE_FILES):
        raise Job5LFinalValidationError("Contrato interno diverge da topologia")
    if contract["job5MAllowed"] or contract["gate11"] != "CLOSED":
        raise Job5LFinalValidationError("Contrato abriu Job 5M ou Gate 11")

    f1 = _read_csv(output_dir / "internal" / "RESULTADOS_F1_JOB5L_FINAL.csv.gz")
    if len(f1) != 497 * 3 * 4:
        raise Job5LFinalValidationError("F1 final não cobre 497 × 3 × 4")
    codes = set(f1["municipality_ibge_code"].dropna().astype(str))
    if len(codes) != 497 or any(not IBGE_CODE_PATTERN.fullmatch(code) for code in codes):
        raise Job5LFinalValidationError("Identidade municipal F1 divergente")
    for column in (
        "expected_value",
        "expected_interval_lower",
        "expected_interval_upper",
    ):
        values = pd.to_numeric(f1[column], errors="coerce").dropna()
        if not values.between(0, 100, inclusive="both").all():
            raise Job5LFinalValidationError(f"F1 fora de 0–100: {column}")
    comparable = f1.dropna(
        subset=[
            "expected_value",
            "expected_interval_lower",
            "expected_interval_upper",
        ]
    )
    if not (
        pd.to_numeric(comparable["expected_interval_lower"], errors="raise")
        <= pd.to_numeric(comparable["expected_value"], errors="raise")
    ).all() or not (
        pd.to_numeric(comparable["expected_value"], errors="raise")
        <= pd.to_numeric(comparable["expected_interval_upper"], errors="raise")
    ).all():
        raise Job5LFinalValidationError("F1 contém intervalo desordenado")
    if not f1["bounded_by_construction"].astype(bool).all():
        raise Job5LFinalValidationError("F1 perdeu suporte limitado por construção")
    if f1["post_prediction_clipping_applied"].astype(bool).any():
        raise Job5LFinalValidationError("F1 aplicou truncamento pós-modelo")

    validation = _read_csv(
        output_dir / "internal" / "VALIDACAO_F1_JOB5L_FINAL.csv.gz"
    )
    eligible = validation["validation_eligible"].astype(str).str.casefold().isin(
        {"true", "1"}
    )
    noneligible = set(
        zip(
            validation.loc[~eligible, "outcome_id"],
            validation.loc[~eligible, "stage"],
            strict=True,
        )
    )
    if len(validation) != 12 or int(eligible.sum()) != 11:
        raise Job5LFinalValidationError("Gates F1 finais divergentes")
    if noneligible != {("dropout_rate_percent", "fundamental_anos_iniciais")}:
        raise Job5LFinalValidationError("Combinação F1 não avaliável divergente")
    if validation[
        [
            "history_only_group_holdout_mae",
            "history_plus_context_group_holdout_mae",
        ]
    ].isna().any().any():
        raise Job5LFinalValidationError("F1 não comparou histórico e contexto")

    censo = _json(
        output_dir / "internal" / "CENSO_2022_STATUS_ATUAL_JOB5L_FINAL.json"
    )
    if (
        censo["sampleMicrodataAvailable"]
        or censo["weightingAreasAvailable"]
        or censo["packageDocumentationAvailable"]
        or censo["officialPackageAvailable"]
    ):
        raise Job5LFinalValidationError("Censo final registrou disponibilidade não validada")
    if set(censo["sourceAccess"]) != set(CENSO_URLS) or all(
        censo["availabilityRequirements"].values()
    ):
        raise Job5LFinalValidationError("Censo final perdeu topologia ou gate fail-closed")
    if censo["definitiveJob5MAuthorizationAllowed"]:
        raise Job5LFinalValidationError("Censo final autorizou Job 5M")
    f2_f5 = _read_csv(
        output_dir / "internal" / "PAINEL_F2_F5_JOB5L_FINAL.csv.gz"
    )
    if f2_f5["value"].notna().any() or not f2_f5["front_state"].eq(
        "NOT_EXECUTED_OFFICIAL_SOURCE_UNAVAILABLE"
    ).all():
        raise Job5LFinalValidationError("F2/F5 fabricaram estimativa")

    rais_audit = _json(
        output_dir / "internal" / "AUDITORIA_RAIS_JOB5L_FINAL.json"
    )
    reconciliation = rais_audit["reconciliationWithFrozenAggregate"]
    if (
        reconciliation["terminalState"]
        != "RAIS_2019_2025_CANONICAL_RECONCILED"
        or reconciliation["exactMatchCount"] != 140
        or reconciliation["mismatchCount"] != 0
    ):
        raise Job5LFinalValidationError("RAIS final não está canonicamente reconciliada")
    rais_panel = _read_csv(output_dir / "internal" / "PAINEL_RAIS_JOB5L_FINAL.csv.gz")
    if not rais_panel["territorial_lens"].eq(
        "establishment_location_workplace"
    ).all():
        raise Job5LFinalValidationError("Painel RAIS misturou lentes")

    eja = _read_csv(output_dir / "internal" / "PAINEL_EJA_JOB5L_FINAL.csv.gz")
    if set(eja["stage"]) != {"fundamental", "high_school"}:
        raise Job5LFinalValidationError("EJA perdeu separação por etapa")
    if eja["per_thousand_rate_materialized"].astype(str).str.casefold().isin(
        {"true", "1"}
    ).any():
        raise Job5LFinalValidationError("EJA materializou taxa por mil")
    if eja["coverage_demand_or_deficit_claim_allowed"].astype(str).str.casefold().isin(
        {"true", "1"}
    ).any():
        raise Job5LFinalValidationError("EJA autorizou claim de cobertura/demanda/déficit")
    required_eja_columns = {
        "resident_adult_public",
        "school_location_eja_enrollments",
        "share_of_regional_public_percent",
        "share_of_regional_enrollments_percent",
        "distribution_difference_percentage_points",
        "adult_panel_compatibility",
    }
    if not required_eja_columns <= set(eja) or (
        "eja_enrollments_per_thousand_resident_public_2022" in eja
    ):
        raise Job5LFinalValidationError("EJA perdeu contraste ou preservou taxa por mil")
    nsr_eja = eja[eja["entity_id"].astype(str).eq(NSR_CODE)].set_index("stage")
    if not math.isclose(
        float(
            nsr_eja.loc[
                "fundamental", "distribution_difference_percentage_points"
            ]
        ),
        2.6482631443935167,
        rel_tol=0,
        abs_tol=1e-9,
    ) or not math.isclose(
        float(
            nsr_eja.loc[
                "high_school", "distribution_difference_percentage_points"
            ]
        ),
        -2.6050945751099364,
        rel_tol=0,
        abs_tol=1e-9,
    ):
        raise Job5LFinalValidationError("EJA perdeu âncoras de Nova Santa Rita")
    if (
        float(nsr_eja.loc["fundamental", "eja_enrollments_2025"]) != 152
        or float(nsr_eja.loc["high_school", "eja_enrollments_2025"]) != 56
        or nsr_eja.loc["fundamental", "adult_panel_compatibility"]
        != "DEFINITION_INCOMPATIBLE_POPULATION_TOTAL_SOURCE"
    ):
        raise Job5LFinalValidationError("EJA perdeu contagens ou incompatibilidade explícita")

    catalog = _json(output_dir / "CATALOGO_INSIGHTS_FINAIS_JOB5L.json")
    ids = [item["insight_id"] for item in catalog["insights"]]
    if catalog["candidateInsightCount"] != len(ids) or len(ids) > 8:
        raise Job5LFinalValidationError("Catálogo excede limite ou contagem")
    required_ids = {
        "I1_CONTEXT_ADJUSTED_EDUCATIONAL_TRAJECTORY",
        "I2_MERGED_YOUTH_WORK_COMPOSITION",
        "I4_FUNCTIONAL_TERRITORIAL_GRAMMAR",
        "I5_ADULT_SCHOOLING_AND_EJA_DISTRIBUTION",
        "NEG_F2_SAME_PERSON_STUDY_WORK_UNAVAILABLE",
        "NEG_F5_MIGRATION_SCHOOL_SAME_PERSON_UNAVAILABLE",
    }
    if set(ids) != required_ids or any(value in ids for value in ("I2", "I3", "I4")):
        raise Job5LFinalValidationError("Catálogo não fundiu I2/I3 ou enquadrou I4")
    for item in catalog["insights"]:
        missing = set(CANDIDATE_REQUIRED_FIELDS) - set(item)
        if missing:
            raise Job5LFinalValidationError(
                f"Candidata final incompleta {item['insight_id']}: {sorted(missing)}"
            )
    if catalog["crossCuttingI4Grammar"]["standaloneInsight"]:
        raise Job5LFinalValidationError("I4 foi materializado como insight autônomo")
    by_id = {item["insight_id"]: item for item in catalog["insights"]}
    if by_id["I1_CONTEXT_ADJUSTED_EDUCATIONAL_TRAJECTORY"]["editorial_role"] != "CONTEXT":
        raise Job5LFinalValidationError("I1 perdeu papel editorial secundário")
    i4 = by_id["I4_FUNCTIONAL_TERRITORIAL_GRAMMAR"]
    if i4["main_candidate"] or i4["editorial_role"] != "DETAIL_GRAMMAR":
        raise Job5LFinalValidationError("I4 virou história autônoma")
    distinction = by_id["I2_MERGED_YOUTH_WORK_COMPOSITION"][
        "measurement_distinction"
    ]
    if distinction["labelsInterchangeable"] or distinction[
        "stocksAndEventsInterchangeable"
    ]:
        raise Job5LFinalValidationError("RAIS ativa e admissões Caged foram fundidas")

    result_matrix = _read_csv(
        output_dir / "MATRIZ_RESULTADOS_FINAIS_JOB5L.csv.gz"
    )
    if not {
        "I4_FUNCTIONAL_TERRITORIAL_GRAMMAR",
        "I5_ADULT_SCHOOLING_AND_EJA_DISTRIBUTION",
    } <= set(result_matrix["insight_id"]):
        raise Job5LFinalValidationError("Matriz final perdeu componentes I4/I5")

    heterogeneity = _read_csv(
        output_dir / "MATRIZ_HETEROGENEIDADE_10_MUNICIPIOS_JOB5L_FINAL.csv.gz"
    )
    heterogeneity_codes = set(
        heterogeneity["municipality_ibge_code"].dropna().astype(str)
    )
    if heterogeneity_codes != set(job5l._region_codes()) or NSR_CODE not in heterogeneity_codes:
        raise Job5LFinalValidationError("Matriz final não cobre Vale/NSR")

    qa = _json(output_dir / "QA_SUMMARY_JOB5L_FINAL.json")
    if qa["failedCount"] != 0 or qa["result"] != "PASS_WITH_EXPLICIT_LIMITS":
        raise Job5LFinalValidationError("QA final não passou com limites")
    limits = _json(output_dir / "LIMITACOES_E_CLAIMS_JOB5L_FINAL.json")
    if limits["pne"]["officialIndicatorRecalculated"] or limits["job5MAllowed"]:
        raise Job5LFinalValidationError("PNE/Job 5M alterado indevidamente")
    if any(
        manifest["generation"][key]
        for key in (
            "databaseWritePerformed",
            "publicDataChanged",
            "frontendChanged",
            "navigationChanged",
            "fullBuildUsed",
            "publicationPerformed",
        )
    ):
        raise Job5LFinalValidationError("Manifesto registra mutação proibida")

    resolved_sources = source_root or output_dir / "sources"
    if directory_content_digest(resolved_sources) != manifest["sourceCache"][
        "treeDigestSha256"
    ]:
        raise Job5LFinalValidationError("Cache de fontes Censo divergiu do manifesto")
    if verify_sources:
        validate_censo_source_snapshot(resolved_sources / "ibge-censo-2022")
        job5l.validate_rais_sources(
            PREVIOUS_JOB5L_ROOT / "sources" / "rais" / "raw",
            municipality_lens="establishment_location",
        )
    return manifest
