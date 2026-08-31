from __future__ import annotations

import gc
import hashlib
import json
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
AA2_ROOT = REPO_ROOT / ".tmp" / "vocacoes-pne" / "advanced-analytics-v1" / "aa2"
AA2_MANIFEST_PATH = AA2_ROOT / "MANIFEST_AA2.json"
AA2_CLAIMS_PATH = AA2_ROOT / "CLAIMS_AA2.json"
LITERATURE_PATH = (
    REPO_ROOT
    / ".tmp"
    / "vocacoes-pne"
    / "v7-job5l"
    / "LITERATURA_E_MECANISMOS_JOB5L.json"
)
LOCAL_MECHANISM_LIBRARY_PATH = (
    REPO_ROOT / "docs" / "BIBLIOTECA_MECANISMOS_JOB_3_V7.md"
)
ANALYTICAL_GUIDELINE_PATH = (
    REPO_ROOT / "docs" / "ADENDO_DIRETRIZ_ANALITICA_VOCACOES_PNE_V7.md"
)
COURSE_CBO_BRIDGE_PATH = (
    REPO_ROOT
    / "data_pipeline"
    / "contracts"
    / "vocacoes-pne-course-cbo-rs-v1-projection.json"
)
PROGRAM_PLAN_PATH = (
    REPO_ROOT / "docs" / "PLANO_EXECUCAO_AVANCO_ANALITICO_VOCACOES_PNE.md"
)
OPUS_RECONCILIATION_PATH = (
    REPO_ROOT
    / "docs"
    / "RECONCILIACAO_OPUS_AA3_BIBLIOTECA_TEORICA_VOCACOES_PNE.json"
)
OPUS_REAUDIT_PATH = (
    REPO_ROOT
    / ".tmp"
    / "codex-analytics-program"
    / "aa3-opus-results-r2"
    / "opus-result.json"
)
CONTRACT_PATH = (
    REPO_ROOT
    / "data_pipeline"
    / "contracts"
    / "vocacoes-pne-aa3-theory-library-v1.json"
)
RUNNER_PATH = (
    REPO_ROOT
    / "data_pipeline"
    / "scripts"
    / "run_vocacoes_pne_theory_library.py"
)
DEFAULT_OUTPUT_ROOT = (
    REPO_ROOT / ".tmp" / "vocacoes-pne" / "advanced-analytics-v1" / "aa3"
)

EXPECTED_CONTRACT_SHA256 = (
    "cd5a468ba8889c311e13aaad4b2e9ed737016d5d9053fc7180baa4152ac2fc81"
)
EXPECTED_AA2_MANIFEST_SHA256 = (
    "e626762e37843673956c0aa27bcf0bbc099ffba2661cd413859f7ce433b75b2f"
)
EXPECTED_AA2_CLAIMS_SHA256 = (
    "065f4f96d15591b4d239eebb5f18f0f6af0144daec47844dfae00d919fb09419"
)
EXPECTED_AA2_ARTIFACT_SET_SHA256 = (
    "b166cd6742cedb279a7c16316245e1ae08589b41c6e73b8cd3849c44fdd22879"
)
EXPECTED_LITERATURE_SHA256 = (
    "efa00b16995fe3be90b6d23c0a9a983c7c4c42ef6d8692a4947cd5c3706b4b18"
)
EXPECTED_LOCAL_MECHANISM_LIBRARY_SHA256 = (
    "5b0edb5ad0a6cb61d4a3d6b7d6f66a801e9f8179be6ed84412c2d1e17c1a5a91"
)
EXPECTED_ANALYTICAL_GUIDELINE_SHA256 = (
    "0cf88d3f405e5274072327b5560a34db58bfbdf0d4a88569654f52e3fe385b25"
)
EXPECTED_COURSE_CBO_BRIDGE_SHA256 = (
    "bb3d437efda4f067e1ebb4a3bb05927aaf751ce14294f4fc4800efd321ee97e0"
)
EXPECTED_PROGRAM_PLAN_SHA256 = (
    "063e44ab88c763f8563b28a826c96a10585de8b92d9dc04b0b0cc04f1c465b71"
)
EXPECTED_OPUS_RECONCILIATION_SHA256 = (
    "a61b1a0d824dcf215f927f8a37d9e1890c4208cf04f26f25ac9085d007cc7119"
)
EXPECTED_OPUS_REAUDIT_SHA256 = (
    "fea8c9d55711dcdc9326248259b6c997c370b4dead7f26a8f1408bbe247f5f67"
)
AA2_HISTORICAL_PUBLIC_DATA_DIGEST = (
    "4a52e3891163cb3427c5c01f2ef5414c5fe7855dd491a9a125b509899dcc23e1"
)

GENERATED_AT = "2026-08-30T00:00:00-03:00"
LIBRARY_FILE = "BIBLIOTECA_MECANISMOS_AA3.json"
COVERAGE_FILE = "MATRIZ_COBERTURA_TEORICA_AA3.csv.gz"
BOUNDARIES_FILE = "FRONTEIRAS_INTERPRETACAO_AA3.json"
EVIDENCE_FILE = "EVIDENCIAS_COMPLEMENTARES_AA3.json"
QA_FILE = "QA_SUMMARY_AA3.json"
MANIFEST_FILE = "MANIFEST_AA3.json"
NON_MANIFEST_FILES = (
    LIBRARY_FILE,
    COVERAGE_FILE,
    BOUNDARIES_FILE,
    EVIDENCE_FILE,
    QA_FILE,
)

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
SUPPORTED_QUESTIONS = {
    "P1_CONTEXT_ADJUSTED_TRAJECTORY",
    "P4_YOUTH_WORK_AND_HIGH_SCHOOL",
    "P5_OCCUPATIONS_AND_EPT",
    "P6_ADULT_SCHOOLING_WORK_AND_EJA",
}
IDENTITY_QUESTIONS = {"P2_DEMOGRAPHY_ENROLLMENT_DECOMPOSITION"}
GAP_QUESTIONS = {
    "P3_SCHOOL_CONDITIONS_AND_TRAJECTORY",
    "P7_RURALITY_INCLUSION_AND_ACCESS",
    "P8_FINANCING_OFFER_AND_CAPACITY",
}
EXPECTED_UNUSED_REFERENCE_IDS = {
    "LIT_DESLOCAMENTO_ESCOLA_ADOLESCENTES",
    "LIT_IBGE_CENSO_DESLOCAMENTOS_2022",
    "LIT_MIGRACAO_FLUXO_ESCOLAR",
}
EXPECTED_CEILING_POLICY = {
    "P1_CONTEXT_ADJUSTED_TRAJECTORY": (
        "CONTEXT_ADJUSTED_COMPARISON",
        "CONTEXT_ADJUSTED_COMPARISON_WITH_NO_TYPICALITY_CLAIM",
    ),
    "P2_DEMOGRAPHY_ENROLLMENT_DECOMPOSITION": (
        "ACCOUNTING_DECOMPOSITION",
        "ACCOUNTING_DECOMPOSITION_ONLY",
    ),
    "P3_SCHOOL_CONDITIONS_AND_TRAJECTORY": (
        "ROBUST_ASSOCIATION",
        "INTERPRETATION_BOUNDARY_NO_ROBUST_ASSOCIATION",
    ),
    "P4_YOUTH_WORK_AND_HIGH_SCHOOL": (
        "PLANNING_SIGNAL",
        "NO_ROBUST_ASSOCIATION_LITERATURE_SUPPORTS_MONITORING_QUESTION_ONLY",
    ),
    "P5_OCCUPATIONS_AND_EPT": (
        "DISTRIBUTIONAL_PATTERN",
        "DESCRIPTIVE_NOMENCLATURE_CORRESPONDENCE_CBO_2_DIGIT_ONLY",
    ),
    "P6_ADULT_SCHOOLING_WORK_AND_EJA": (
        "DISTRIBUTIONAL_PATTERN",
        "NO_ROBUST_ASSOCIATION_DESCRIPTIVE_DISTRIBUTIONS_ONLY",
    ),
    "P7_RURALITY_INCLUSION_AND_ACCESS": (
        "PLANNING_SIGNAL",
        "INTERPRETATION_BOUNDARY_NO_ROBUST_ASSOCIATION",
    ),
    "P8_FINANCING_OFFER_AND_CAPACITY": (
        "CONTEXT_ADJUSTED_COMPARISON",
        "NOT_SUPPORTED_OR_UNAVAILABLE",
    ),
}

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


class TheoryLibraryValidationError(ValueError):
    """Falha fechada do contrato ou da materialização AA3."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_bytes(payload: Any) -> bytes:
    return (
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    temporary.write_bytes(canonical_json_bytes(payload))
    os.replace(temporary, path)


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TheoryLibraryValidationError(f"JSON raiz deve ser objeto: {path}")
    return payload


def _require_hash(path: Path, expected: str) -> None:
    actual = sha256_file(path)
    if actual != expected:
        raise TheoryLibraryValidationError(
            f"SHA-256 divergente para {path}: {actual} != {expected}"
        )


def _last_write_time_utc(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


@contextmanager
def blocked_external_io_guard() -> Iterable[None]:
    """Bloqueia rede e SQLite durante cada materialização AA3."""

    original_socket_connect = socket.socket.connect
    original_create_connection = socket.create_connection
    original_sqlite_connect = sqlite3.connect

    def blocked(*_args: Any, **_kwargs: Any) -> Any:
        raise TheoryLibraryValidationError(
            "AA3 permite somente entradas locais congeladas; conexão externa bloqueada"
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


def verify_frozen_inputs(*, expected_public_digest: str | None = None) -> dict[str, str]:
    expected_paths = {
        CONTRACT_PATH: EXPECTED_CONTRACT_SHA256,
        AA2_MANIFEST_PATH: EXPECTED_AA2_MANIFEST_SHA256,
        AA2_CLAIMS_PATH: EXPECTED_AA2_CLAIMS_SHA256,
        LITERATURE_PATH: EXPECTED_LITERATURE_SHA256,
        LOCAL_MECHANISM_LIBRARY_PATH: EXPECTED_LOCAL_MECHANISM_LIBRARY_SHA256,
        ANALYTICAL_GUIDELINE_PATH: EXPECTED_ANALYTICAL_GUIDELINE_SHA256,
        COURSE_CBO_BRIDGE_PATH: EXPECTED_COURSE_CBO_BRIDGE_SHA256,
        PROGRAM_PLAN_PATH: EXPECTED_PROGRAM_PLAN_SHA256,
        OPUS_RECONCILIATION_PATH: EXPECTED_OPUS_RECONCILIATION_SHA256,
    }
    for path, expected in expected_paths.items():
        _require_hash(path, expected)
    _require_hash(OPUS_REAUDIT_PATH, EXPECTED_OPUS_REAUDIT_SHA256)

    contract = _load_json(CONTRACT_PATH)
    manifest = _load_json(AA2_MANIFEST_PATH)
    claims = _load_json(AA2_CLAIMS_PATH)
    literature = _load_json(LITERATURE_PATH)
    bridge = _load_json(COURSE_CBO_BRIDGE_PATH)
    reconciliation = _load_json(OPUS_RECONCILIATION_PATH)
    opus_reaudit = _load_json(OPUS_REAUDIT_PATH)

    if contract.get("questionIds") != list(QUESTION_IDS):
        raise TheoryLibraryValidationError("Contrato AA3 não preserva as oito perguntas.")
    scope = contract.get("scope", {})
    if (
        scope.get("externalResearchAuthorized") is not False
        or scope.get("localFrozenReferencesOnly") is not True
        or scope.get("literatureMayCreateLocalEffect") is not False
        or scope.get("literatureMayCreateMunicipalNumber") is not False
    ):
        raise TheoryLibraryValidationError("Contrato AA3 ampliou indevidamente a literatura.")
    if manifest.get("artifactSetDigestSha256") != EXPECTED_AA2_ARTIFACT_SET_SHA256:
        raise TheoryLibraryValidationError("Digest analítico AA2 divergente.")
    if claims.get("publicNarrativeAllowed") is not False:
        raise TheoryLibraryValidationError("AA2 não deveria autorizar narrativa pública direta.")
    claim_ids = [claim.get("questionId") for claim in claims.get("claims", [])]
    if claim_ids != list(QUESTION_IDS):
        raise TheoryLibraryValidationError("Claims AA2 não preservam ordem e universo AA3.")
    if (
        literature.get("literatureAuthorizesLocalEffects") is not False
        or literature.get("literatureProvidesMunicipalNumbers") is not False
        or literature.get("referenceCount") != 8
        or literature.get("mechanismCount") != 7
    ):
        raise TheoryLibraryValidationError("Fonte literária congelada viola o teto AA3.")
    if any(
        reference.get("localNumberProvider") is not False
        for reference in literature.get("references", [])
    ):
        raise TheoryLibraryValidationError("Referência externa marcada como número local.")
    if bridge.get("scope", {}).get("grain") != "courseCode x occupationSubgroupCode":
        raise TheoryLibraryValidationError("Ponte curso-CBO não preserva grão de dois dígitos.")
    if (
        reconciliation.get("status")
        != "CORRECTIONS_ACCEPTED_PENDING_REMATERIALIZATION_AND_REAUDIT"
        or reconciliation.get("aa4Allowed") is not False
        or reconciliation.get("initialAudit", {}).get("verdict") != "AT_RISK"
    ):
        raise TheoryLibraryValidationError("Reconciliação Opus inicial AA3 divergente.")
    if (
        opus_reaudit.get("verdict") != "ON_TRACK"
        or opus_reaudit.get("confidence") != 0.78
    ):
        raise TheoryLibraryValidationError("Reauditoria Opus AA3 divergente.")

    sentinel = contract.get("publicDataSentinel", {})
    if (
        sentinel.get("gateRule")
        != "PUBLIC_DATA_NOT_WRITTEN_BY_AA3_INVARIANT_WITHIN_AND_EQUAL_ACROSS_TWO_CANDIDATE_MATERIALIZATIONS"
        or sentinel.get("aa2HistoricalDigestPreserved") is not True
        or sentinel.get("aa2HistoricalDigestSha256")
        != AA2_HISTORICAL_PUBLIC_DATA_DIGEST
        or sentinel.get("publicDataModifiedByAa3") is not False
        or sentinel.get("fixedDigestIsAnalyticalInput") is not False
        or sentinel.get("futureBaselinePolicy", {}).get("automaticRebaselineAllowed")
        is not False
        or sentinel.get("futureBaselinePolicy", {}).get("aa4EntryBaseline")
        != "CAPTURE_EXPLICITLY_AFTER_CONCURRENT_PUBLICATIONS_SETTLE"
        or contract.get("generation", {}).get("publicDataFixedDigestRequired")
        is not False
        or contract.get("generation", {}).get("publicDataIntegrityMode")
        != "INVARIANT_WITHIN_AND_EQUAL_ACROSS_TWO_CANDIDATE_MATERIALIZATIONS"
    ):
        raise TheoryLibraryValidationError("Sentinela público AA3 não está formalmente reconciliado.")
    changed_paths = sentinel.get("observedChangedPaths", [])
    if len(changed_paths) != 11:
        raise TheoryLibraryValidationError("Registro do desvio público AA3 não contém 11 caminhos.")
    regional_root = (REPO_ROOT / "public" / "data" / "regioes").resolve()
    for record in changed_paths:
        path = (REPO_ROOT / record["path"]).resolve()
        try:
            path.relative_to(regional_root)
        except ValueError as error:
            raise TheoryLibraryValidationError(
                f"Caminho fora da raiz regional no desvio AA3: {path}"
            ) from error
        if (
            not path.is_file()
            or path.stat().st_size != record["byteSize"]
            or sha256_file(path) != record["sha256"]
            or _last_write_time_utc(path) != record["lastWriteTimeUtc"]
        ):
            raise TheoryLibraryValidationError(
                f"Evidência de atribuição do desvio público divergente: {record['path']}"
            )
    producer = sentinel.get("producerAttribution", {})
    producer_manifest = _load_json(REPO_ROOT / producer["producerManifest"])
    if (
        producer.get("canonicalCommand") != "npm run generate:regioes"
        or not (REPO_ROOT / producer["generatorScript"]).is_file()
        or not (REPO_ROOT / producer["generatorLibrary"]).is_file()
        or producer_manifest.get("schemaVersion")
        != producer.get("producerManifestSchemaVersion")
        or producer_manifest.get("generatorVersion")
        != producer.get("producerGeneratorVersion")
        or producer.get("regionalFilesLastWriteTimeUtc")
        >= producer.get("firstAa3CandidateArtifactCreationTimeUtc")
        or producer.get("firstAa3CandidateArtifactCreationTimeUtc")
        >= producer.get("finalAa3ManifestWriteTimeUtc")
    ):
        raise TheoryLibraryValidationError("Atribuição temporal do desvio público AA3 divergiu.")
    subsequent = sentinel.get("subsequentExternalPublication", {})
    subsequent_root = (REPO_ROOT / subsequent["root"]).resolve()
    subsequent_manifest_path = (REPO_ROOT / subsequent["manifestPath"]).resolve()
    subsequent_manifest = _load_json(subsequent_manifest_path)
    if (
        subsequent.get("municipalityFileCount")
        != len(list((subsequent_root / "municipios").glob("*.json")))
        or directory_content_digest(subsequent_root)
        != subsequent.get("rootDigestSha256")
        or sha256_file(subsequent_manifest_path)
        != subsequent.get("manifestSha256")
        or subsequent_manifest.get("schemaVersion")
        != subsequent.get("manifestSchemaVersion")
        or subsequent_manifest.get("generatorVersion")
        != subsequent.get("generatorVersion")
        or _last_write_time_utc(subsequent_manifest_path)
        != subsequent.get("lastWriteTimeUtc")
        or not (REPO_ROOT / subsequent["canonicalGeneratorScript"]).is_file()
        or subsequent.get("aa3Authorship") is not False
    ):
        raise TheoryLibraryValidationError(
            "Evidência da publicação externa pne2026-matriz divergiu."
        )
    public_digest = directory_content_digest(REPO_ROOT / "public/data")
    if expected_public_digest is not None and public_digest != expected_public_digest:
        raise TheoryLibraryValidationError(
            "public/data divergiu dentro da janela protegida do AA3."
        )

    return {
        "aa2ManifestSha256": EXPECTED_AA2_MANIFEST_SHA256,
        "aa2ClaimsSha256": EXPECTED_AA2_CLAIMS_SHA256,
        "aa2ArtifactSetDigestSha256": EXPECTED_AA2_ARTIFACT_SET_SHA256,
        "literatureSha256": EXPECTED_LITERATURE_SHA256,
        "localMechanismLibrarySha256": EXPECTED_LOCAL_MECHANISM_LIBRARY_SHA256,
        "analyticalGuidelineSha256": EXPECTED_ANALYTICAL_GUIDELINE_SHA256,
        "courseCboBridgeSha256": EXPECTED_COURSE_CBO_BRIDGE_SHA256,
        "programPlanSha256": EXPECTED_PROGRAM_PLAN_SHA256,
        "opusReconciliationSha256": EXPECTED_OPUS_RECONCILIATION_SHA256,
        "contractSha256": EXPECTED_CONTRACT_SHA256,
        "publicDataTreeDigestSha256": public_digest,
    }


def _reference(
    ref_id: str,
    support_type: str,
    attributed_support: str,
    does_not_support: str,
) -> dict[str, Any]:
    return {
        "ref_id": ref_id,
        "support_type": support_type,
        "directly_supports_attributed_mechanism": True,
        "attributed_support": attributed_support,
        "does_not_support": does_not_support,
        "local_effect_authorized": False,
        "municipal_number_authorized": False,
    }


def _mechanism_definitions(claims_by_id: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    definitions: list[dict[str, Any]] = [
        {
            "mechanism_id": "M_AA3_P1_CONTEXT_AND_TRAJECTORY",
            "record_type": "THEORY_MECHANISM",
            "source_mechanism_ids": ["M1_CONTEXT_AND_TRAJECTORY"],
            "question_id": "P1_CONTEXT_ADJUSTED_TRAJECTORY",
            "manager_question": "O resultado educacional observado é compatível com municípios de contexto mensurável semelhante?",
            "primary_official_or_academic_refs": [
                _reference(
                    "LIT_INEP_INSE_2023",
                    "OFFICIAL_CONTEXT_MEASUREMENT_SUPPORT_ONLY",
                    "Sustenta que o nível socioeconômico é uma dimensão oficial de contexto educacional observável e requer interpretação metodológica própria.",
                    "Não demonstra efeito causal do contexto, não valida o modelo AA2 e não torna Nova Santa Rita um caso típico.",
                )
            ],
            "reference_coverage_state": "SUPPORTED_WITH_STRICT_TRANSFER_LIMIT",
            "expected_observable_pattern": "Resultados podem variar sistematicamente com contexto socioeconômico, porte, composição etária e condições escolares, mas o ganho preditivo fora da amostra precisa ser demonstrado.",
            "local_variables": [
                {"metric_id": "education.dropout_rate_percent", "role": "outcome", "lens": "school_location"},
                {"metric_id": "context.inse_latest_available", "role": "context", "lens": "school_context"},
                {"metric_id": "demography.population_age_15_17", "role": "context", "lens": "resident_population"},
                {"metric_id": "education.teacher_adequacy_percent", "role": "context", "lens": "school_location"},
            ],
            "alternative_explanations": [
                "Composição não observada dos estudantes e das redes.",
                "Mobilidade residencial ou educacional entre municípios.",
                "Mudanças de registro, cobertura ou composição das escolas.",
                "Choques de período não capturados pelos preditores.",
            ],
            "falsification_or_boundary": {
                "evidence_condition": "O modelo completo precisaria melhorar o desempenho fora da amostra e produzir banda informativa para apoiar leitura contextual forte.",
                "observed_boundary": "No AA2, o modelo completo não melhorou o RMSE do baseline e o resíduo municipal permaneceu dentro de banda ampla.",
                "response": "Manter comparação contextual; proibir tipicidade, contribuição isolada ou causalidade.",
            },
            "aa3_effective_claim_ceiling": "CONTEXT_ADJUSTED_COMPARISON_WITH_NO_TYPICALITY_CLAIM",
            "theory_can_override_aa2_terminal": False,
            "allowed_interpretation": "Usar o contexto para qualificar a comparação e mostrar a incerteza; a não sinalização não demonstra tipicidade.",
            "forbidden_interpretations": [
                "O território causou o resultado educacional.",
                "Nova Santa Rita é típica porque não foi sinalizada.",
                "O INSE mede contribuição da escola ou da família no município.",
            ],
            "transferability_notes": "A referência é metodológica e nacional; sustenta a dimensão de contexto, não o efeito local, a especificação do modelo ou sua calibração municipal.",
            "aa4_role": "DOSSIER_1_PRIMARY",
            "promotion_state": "ELIGIBLE_WITH_AA2_AND_AA3_GUARDS",
        },
        {
            "mechanism_id": "M_AA3_P2_COHORT_ACCOUNTING",
            "record_type": "ACCOUNTING_IDENTITY",
            "source_mechanism_ids": [],
            "question_id": "P2_DEMOGRAPHY_ENROLLMENT_DECOMPOSITION",
            "manager_question": "Quanto da mudança observada nas matrículas decorre aritmeticamente da coorte residente e quanto permanece no componente da relação territorial matrícula/população?",
            "primary_official_or_academic_refs": [],
            "reference_coverage_state": "IDENTITY_NO_MECHANISM_REFERENCE_REQUIRED",
            "expected_observable_pattern": "A mudança total de matrículas fecha exatamente como soma do componente populacional e do componente residual da relação territorial.",
            "local_variables": [
                {"metric_id": "education.enrollments", "role": "accounting_total", "lens": "school_location"},
                {"metric_id": "demography.population_age_15_17", "role": "accounting_scale", "lens": "resident_population"},
                {"metric_id": "enrollment_population_relationship", "role": "accounting_residual", "lens": "mixed_explicit"},
            ],
            "alternative_explanations": [
                "Mobilidade educacional entre residência e escola.",
                "Mudança de cobertura ou organização territorial da oferta.",
                "Revisões ou rebases da série populacional.",
                "Mudanças de registro e composição por rede.",
            ],
            "falsification_or_boundary": {
                "evidence_condition": "A identidade deve fechar dentro da tolerância numérica pré-definida em cada recorte.",
                "observed_boundary": "O componente da relação é residual contábil; não identifica comportamento, cobertura, migração ou resposta institucional.",
                "response": "Bloquear qualquer rótulo causal ou comportamental mesmo quando a identidade fecha.",
            },
            "aa3_effective_claim_ceiling": "ACCOUNTING_DECOMPOSITION_ONLY",
            "theory_can_override_aa2_terminal": False,
            "allowed_interpretation": "Descrever a parcela aritmética ligada à coorte e o restante da identidade territorial, com lentes e proveniência explícitas.",
            "forbidden_interpretations": [
                "O componente residual mede migração.",
                "A razão é taxa de cobertura ou frequência.",
                "A decomposição prevê matrículas futuras.",
            ],
            "transferability_notes": "A validade decorre da identidade matemática e das séries locais congeladas, não de transferência de efeito externo. Vintage e rebase populacional permanecem não identificáveis.",
            "aa4_role": "DOSSIER_2_PRIMARY",
            "promotion_state": "ELIGIBLE_AS_ACCOUNTING_IDENTITY_ONLY",
        },
        {
            "mechanism_id": "M_AA3_P3_SCHOOL_CONDITIONS",
            "record_type": "INTERPRETATION_BOUNDARY",
            "source_mechanism_ids": [],
            "question_id": "P3_SCHOOL_CONDITIONS_AND_TRAJECTORY",
            "manager_question": "Mudanças nas condições escolares acompanham de modo robusto mudanças de permanência no ensino médio?",
            "primary_official_or_academic_refs": [],
            "reference_coverage_state": "LOCAL_PRIMARY_REFERENCE_GAP_CEILING_REDUCED",
            "expected_observable_pattern": "Se a condição observada contribuísse de forma estável para a trajetória agregada, o sinal deveria persistir entre especificações, janelas, defasagens e exclusões relevantes.",
            "local_variables": [
                {"metric_id": "education.teacher_adequacy_percent", "role": "exposure", "lens": "school_location"},
                {"metric_id": "education.dropout_rate_percent", "role": "outcome", "lens": "school_location"},
                {"metric_id": "education.failure_rate_percent", "role": "alternative_outcome", "lens": "school_location"},
            ],
            "alternative_explanations": [
                "Composição discente e socioeconômica variável no tempo.",
                "Outras condições de oferta e gestão não observadas.",
                "Mudanças de rede, mobilidade ou seleção escolar.",
                "Erro de mensuração e defasagem diferente da registrada.",
            ],
            "falsification_or_boundary": {
                "evidence_condition": "Associação deveria sobreviver ao ajuste familiar e às sensibilidades pré-registradas com sinal e magnitude interpretáveis.",
                "observed_boundary": "AA2 terminou em NO_ROBUST_ASSOCIATION; a base local não contém referência primária diretamente adequada ao mecanismo específico.",
                "response": "Usar apenas como fronteira interpretativa e agenda de monitoramento, sem explicação positiva.",
            },
            "aa3_effective_claim_ceiling": "INTERPRETATION_BOUNDARY_NO_ROBUST_ASSOCIATION",
            "theory_can_override_aa2_terminal": False,
            "allowed_interpretation": "Informar que a relação testada não apresentou associação robusta no desenho registrado e que outras condições permanecem hipóteses não testadas.",
            "forbidden_interpretations": [
                "Adequação docente causou ou não causou abandono.",
                "Ausência de significância prova ausência de relação.",
                "Prosa teórica substitui a lacuna de referência primária.",
            ],
            "transferability_notes": "Sem referência primária localmente congelada para o mecanismo específico; o teto foi reduzido e não pode ser elevado por analogia genérica.",
            "aa4_role": "DOSSIER_1_INTERPRETATION_BOUNDARY",
            "promotion_state": "BOUNDARY_ONLY_REFERENCE_GAP",
        },
        {
            "mechanism_id": "M_AA3_P4_YOUTH_WORK",
            "record_type": "THEORY_MECHANISM",
            "source_mechanism_ids": ["M2_STUDY_AND_WORK", "M3_APPRENTICESHIP"],
            "question_id": "P4_YOUTH_WORK_AND_HIGH_SCHOOL",
            "manager_question": "Mudanças no trabalho formal juvenil devem entrar no monitoramento conjunto da permanência no ensino médio?",
            "primary_official_or_academic_refs": [
                _reference(
                    "LIT_JUVENTUDE_EDUCACAO_TRABALHO_2012_2022",
                    "PRIMARY_NATIONAL_MECHANISM_SUPPORT",
                    "Sustenta que estudo e trabalho coexistem de formas socialmente heterogêneas entre jovens no Brasil.",
                    "Não liga os mesmos jovens aos registros locais de escola e emprego nem estima efeito municipal do trabalho sobre abandono.",
                ),
                _reference(
                    "LIT_APRENDIZAGEM_IPEA",
                    "OFFICIAL_LABOR_INSTITUTION_SUPPORT",
                    "Sustenta que aprendizagem é modalidade contratual regulada e distinta de emprego jovem genérico.",
                    "Não transforma vínculos RAIS agregados em trajetória escolar, informalidade, desemprego ou primeiro emprego local.",
                ),
            ],
            "reference_coverage_state": "SUPPORTED_WITH_STRICT_TRANSFER_LIMIT",
            "expected_observable_pattern": "Se a pressão do trabalho formal juvenil acompanhasse sistematicamente a permanência, sinais deveriam ser coerentes entre contemporâneo, defasagens, placebo e direção reversa.",
            "local_variables": [
                {"metric_id": "labor.youth_rais.active_bonds", "role": "exposure", "lens": "work_establishment"},
                {"metric_id": "demography.population_age_15_17", "role": "scale", "lens": "resident_population"},
                {"metric_id": "education.dropout_rate_percent", "role": "outcome", "lens": "school_location"},
            ],
            "alternative_explanations": [
                "Ciclo econômico e composição setorial.",
                "Seleção de jovens que entram no trabalho formal.",
                "Informalidade e desemprego não observados.",
                "Mobilidade entre residência, escola e estabelecimento.",
            ],
            "falsification_or_boundary": {
                "evidence_condition": "Sinal, magnitude e temporalidade deveriam permanecer coerentes nas especificações pré-registradas e superar o ajuste familiar.",
                "observed_boundary": "AA2 terminou em NO_ROBUST_ASSOCIATION; literatura torna o mecanismo plausível, mas não altera o resultado local.",
                "response": "Permitir somente sinal de planejamento e monitoramento intersetorial, nunca efeito local.",
            },
            "aa2_descriptive_basis": {
                "artifact": "CLAIMS_AA2.json#P4_YOUTH_WORK_AND_HIGH_SCHOOL",
                "eligible_result_ids": ["P4_MAIN_L0"],
                "main_effect": 0.02113722016085356,
                "main_bh_p_value": 0.888671875,
                "rule_passed": False,
                "low_power_caveat_required": True,
                "use": "Apenas valores e disponibilidade descritivos; não existe sinal empírico local promovido.",
                "association_terminal_remains_primary": "NO_ROBUST_ASSOCIATION",
            },
            "aa3_effective_claim_ceiling": "NO_ROBUST_ASSOCIATION_LITERATURE_SUPPORTS_MONITORING_QUESTION_ONLY",
            "theory_can_override_aa2_terminal": False,
            "allowed_interpretation": "A literatura justifica acompanhar estudo e trabalho em conjunto; o teste local não encontrou associação robusta no desenho registrado.",
            "forbidden_interpretations": [
                "Trabalho formal juvenil causou abandono.",
                "Vínculos agregados representam as mesmas pessoas matriculadas.",
                "RAIS mede todo trabalho juvenil, desemprego ou informalidade.",
                "O resultado empírico continua NO_ROBUST_ASSOCIATION; a literatura não gera sinal local nem padrão positivo.",
            ],
            "transferability_notes": "As referências são nacionais e gerais; sustentam plausibilidade e distinções institucionais, não efeito, magnitude ou trajetória individual em Nova Santa Rita ou no Vale.",
            "aa4_role": "DOSSIER_3_BOUNDARY_AND_PLANNING",
            "promotion_state": "ELIGIBLE_AS_MONITORING_QUESTION_WITH_NEGATIVE_RESULT_ONLY",
        },
        {
            "mechanism_id": "M_AA3_P5_EPT_OCCUPATIONS",
            "record_type": "THEORY_MECHANISM",
            "source_mechanism_ids": ["M4_EPT_AND_WORK"],
            "question_id": "P5_OCCUPATIONS_AND_EPT",
            "manager_question": "Como a oferta técnica observada se distribui em relação a famílias ocupacionais formalmente associadas pelo catálogo normativo?",
            "primary_official_or_academic_refs": [
                _reference(
                    "LIT_EPT_PERMANENCIA_ABANDONO",
                    "PRIMARY_GENERAL_EPT_WORK_MECHANISM_SUPPORT",
                    "Sustenta que permanência e abandono na EPT podem envolver condições escolares e de trabalho.",
                    "Não valida a ponte curso-CBO, não mede demanda ocupacional, empregabilidade, conclusão ou inserção de egressos.",
                )
            ],
            "reference_coverage_state": "SUPPORTED_WITH_STRICT_TRANSFER_LIMIT",
            "expected_observable_pattern": "A composição territorial de matrículas técnicas pode ser comparada à estrutura ocupacional somente por correspondência normativa reproduzível, com cobertura parcial e não aditividade explícitas.",
            "local_variables": [
                {"metric_id": "education.ept_technical_enrollments", "role": "formative_offer", "lens": "school_location"},
                {"metric_id": "labor.occupation_active_bonds", "role": "occupational_structure", "lens": "work_establishment"},
                {"metric_id": "course_cbo_normative_bridge", "role": "normative_correspondence", "lens": "CNCT_to_CBO_2_digit"},
            ],
            "alternative_explanations": [
                "Cursos e trabalho localizados fora do município ou da região.",
                "Ocupações exercidas por pessoas sem conclusão do curso correspondente.",
                "Cobertura parcial e muitos-para-muitos da ponte normativa.",
                "Diferença entre matrícula, conclusão, vaga e capacidade.",
            ],
            "falsification_or_boundary": {
                "evidence_condition": "Toda correspondência deve ser reproduzível no contrato CNCT-CBO congelado e manter separadas as lentes de escola e estabelecimento.",
                "observed_boundary": "A ponte opera em subgrupo CBO de dois dígitos e não oferece sensibilidade em quatro dígitos nem ligação com egressos.",
                "response": "Promover somente composição e cobertura da correspondência normativa.",
            },
            "aa3_effective_claim_ceiling": "DESCRIPTIVE_NOMENCLATURE_CORRESPONDENCE_CBO_2_DIGIT_ONLY",
            "theory_can_override_aa2_terminal": False,
            "allowed_interpretation": "Mostrar como oferta observada e famílias ocupacionais se organizam na ponte normativa e quais lacunas precisam de investigação.",
            "forbidden_interpretations": [
                "O curso garante emprego ou responde à demanda futura.",
                "Correspondência normativa é adequação, suficiência ou qualidade.",
                "Ausência de matrícula observada prova ausência de oferta acessível.",
                "A ponte não mede egressos, empregabilidade, validação ocupacional ou inserção profissional.",
            ],
            "transferability_notes": "A literatura sustenta mecanismos gerais de permanência em EPT; a comparação local deriva da ponte normativa congelada, não da referência acadêmica.",
            "aa4_role": "DOSSIER_4_PRIMARY",
            "promotion_state": "ELIGIBLE_AS_DISTRIBUTIONAL_NORMATIVE_PATTERN",
        },
        {
            "mechanism_id": "M_AA3_P6_ADULT_EJA",
            "record_type": "THEORY_MECHANISM",
            "source_mechanism_ids": ["M6_EJA_PARTICIPATION"],
            "question_id": "P6_ADULT_SCHOOLING_WORK_AND_EJA",
            "manager_question": "A distribuição territorial da escolaridade adulta, do trabalho juvenil e da EJA indica uma agenda de coordenação regional?",
            "primary_official_or_academic_refs": [
                _reference(
                    "LIT_EJA_REPRESENTACOES_PRATICAS",
                    "PRIMARY_GENERAL_EJA_PARTICIPATION_SUPPORT",
                    "Sustenta que trabalho, retorno à escolarização e motivações sociais aparecem como mecanismos plausíveis na participação em EJA.",
                    "Não estima demanda, cobertura, barreira ou efeito municipal da oferta de EJA.",
                )
            ],
            "reference_coverage_state": "SUPPORTED_WITH_STRICT_TRANSFER_LIMIT",
            "expected_observable_pattern": "Distribuições municipais podem divergir entre escolaridade adulta, matrícula EJA localizada e composição de vínculos formais, sem representar as mesmas pessoas.",
            "local_variables": [
                {"metric_id": "adult.high_school_completion_share_percent", "role": "resident_context", "lens": "resident_population"},
                {"metric_id": "education.eja_enrollments", "role": "located_offer", "lens": "school_location"},
                {"metric_id": "labor.youth_rais.schooling_composition_share_percent", "role": "formal_work_context", "lens": "work_establishment"},
            ],
            "alternative_explanations": [
                "Oferta regional e deslocamento para estudar.",
                "Horários, cuidado familiar e outras barreiras não observadas.",
                "Motivações de retorno não observadas.",
                "Universos distintos entre residentes, matrículas e vínculos.",
            ],
            "falsification_or_boundary": {
                "evidence_condition": "Padrões deveriam ser estáveis a exclusões municipais e não depender de uma única observação no universo de dez municípios.",
                "observed_boundary": "AA2 terminou em NO_ROBUST_ASSOCIATION e a baixa potência impede transformar não rejeição em ausência.",
                "response": "Permitir fotografia distributiva e hipótese de coordenação; proibir efeito e demanda.",
            },
            "aa2_descriptive_basis": {
                "artifact": "CLAIMS_AA2.json#P6_ADULT_SCHOOLING_WORK_AND_EJA",
                "eligible_result_ids": ["P6_EJA_SPEARMAN", "P6_WORK_SPEARMAN"],
                "primary_effects": {
                    "P6_EJA_SPEARMAN": -0.6363636363636364,
                    "P6_WORK_SPEARMAN": 0.006060606060606061,
                },
                "stable_primary_fit": None,
                "low_power_caveat_required": True,
                "use": "Apenas distribuições e estimativas descritivas; nenhum padrão associativo estável é promovido.",
                "association_terminal_remains_primary": "NO_ROBUST_ASSOCIATION",
            },
            "aa3_effective_claim_ceiling": "NO_ROBUST_ASSOCIATION_DESCRIPTIVE_DISTRIBUTIONS_ONLY",
            "theory_can_override_aa2_terminal": False,
            "allowed_interpretation": "Usar diferenças de distribuição para orientar perguntas de coordenação territorial, com baixa potência e lentes distintas explícitas.",
            "forbidden_interpretations": [
                "Matrículas por população medem cobertura ou demanda efetiva.",
                "Trabalho impede ou provoca retorno à EJA no município.",
                "Os três agregados representam as mesmas pessoas.",
                "O resultado empírico continua NO_ROBUST_ASSOCIATION; a literatura não cria padrão distributivo local nem efeito.",
            ],
            "transferability_notes": "A referência sustenta mecanismos gerais de participação, não magnitude, efeito ou suficiência da oferta em Nova Santa Rita e no Vale.",
            "aa4_role": "DOSSIER_5_PRIMARY_WITH_BOUNDARY",
            "promotion_state": "ELIGIBLE_AS_DESCRIPTIVE_DISTRIBUTION_WITH_NEGATIVE_RESULT_ONLY",
        },
        {
            "mechanism_id": "M_AA3_P7_RURAL_INCLUSION",
            "record_type": "INTERPRETATION_BOUNDARY",
            "source_mechanism_ids": [],
            "question_id": "P7_RURALITY_INCLUSION_AND_ACCESS",
            "manager_question": "A distribuição de matrículas e pontos de oferta rural e de AEE sugere questões territoriais de acesso a investigar?",
            "primary_official_or_academic_refs": [],
            "reference_coverage_state": "LOCAL_PRIMARY_REFERENCE_GAP_CEILING_REDUCED",
            "expected_observable_pattern": "Se contagens de oferta acompanhassem matrículas de modo estável, sinais deveriam persistir entre janela principal, exclusão pandêmica e defasagem.",
            "local_variables": [
                {"metric_id": "education.rural.rural_enrollments", "role": "outcome", "lens": "school_location"},
                {"metric_id": "education.rural.rural_schools", "role": "offer_count", "lens": "school_location"},
                {"metric_id": "education.special_aee.special_enrollments", "role": "outcome", "lens": "school_location"},
                {"metric_id": "education.special_aee.schools_offering_aee", "role": "offer_count", "lens": "school_location"},
            ],
            "alternative_explanations": [
                "Distância e tempo de deslocamento não observados.",
                "Capacidade, qualidade e tipo de serviço não observados.",
                "Transporte escolar e escolha entre municípios.",
                "Mudanças de registro, organização e escala da rede.",
            ],
            "falsification_or_boundary": {
                "evidence_condition": "O resultado deveria sobreviver ao ajuste familiar pré-registrado e manter sinal nas sensibilidades.",
                "observed_boundary": "O p rural bruto foi 0,039, mas o BH familiar conservador foi 0,117; AA2 terminou em NO_ROBUST_ASSOCIATION e falta referência primária direta congelada.",
                "response": "Tratar como fronteira e pergunta de acesso, nunca como evidência de suficiência ou ausência.",
            },
            "aa3_effective_claim_ceiling": "INTERPRETATION_BOUNDARY_NO_ROBUST_ASSOCIATION",
            "theory_can_override_aa2_terminal": False,
            "allowed_interpretation": "Apresentar a instabilidade após ajuste familiar e indicar dados de distância, capacidade e transporte necessários para testar acesso.",
            "forbidden_interpretations": [
                "Mais escolas causaram mais matrículas.",
                "Contagem de escola ou serviço mede acesso, suficiência ou qualidade.",
                "Não significância ajustada prova ausência de relação.",
            ],
            "transferability_notes": "Sem referência primária direta congelada para ruralidade/AEE e acesso; as referências de deslocamento não foram reaproveitadas por não sustentarem o mecanismo específico testado.",
            "aa4_role": "TRANSVERSAL_OPTIONAL_BOUNDARY",
            "promotion_state": "BOUNDARY_ONLY_REFERENCE_GAP",
        },
        {
            "mechanism_id": "M_AA3_P8_FINANCING_OFFER",
            "record_type": "INTERPRETATION_BOUNDARY",
            "source_mechanism_ids": [],
            "question_id": "P8_FINANCING_OFFER_AND_CAPACITY",
            "manager_question": "Os dados financeiros disponíveis sustentam relacionar capacidade de gasto e oferta educacional em tempo integral?",
            "primary_official_or_academic_refs": [],
            "reference_coverage_state": "LOCAL_PRIMARY_REFERENCE_GAP_CEILING_REDUCED",
            "expected_observable_pattern": "Uma relação interpretável exigiria medida financeira comparável, especificação não endógena, amostra válida e robustez a escala e valores extremos.",
            "local_variables": [
                {"metric_id": "finance.mde_applied_amount", "role": "financial_context", "lens": "municipal_finance_nominal"},
                {"metric_id": "education.full_time_enrollments", "role": "offer_outcome", "lens": "school_location"},
                {"metric_id": "education.enrollments", "role": "shared_scale_and_denominator", "lens": "school_location"},
            ],
            "alternative_explanations": [
                "Causalidade reversa entre necessidade, oferta e financiamento.",
                "Escala municipal e denominador compartilhado.",
                "Composição da despesa e da rede não observada.",
                "Inflação e incomparabilidade nominal entre anos.",
            ],
            "falsification_or_boundary": {
                "evidence_condition": "A especificação principal e alternativas válidas deveriam produzir resultado robusto sem depender de denominador compartilhado ou comparação nominal entre anos.",
                "observed_boundary": "AA2 terminou em INSUFFICIENT_DATA; uma alternativa 2024 é inválida e a razão por matrícula não pode ser promovida isoladamente.",
                "response": "Bloquear integralmente a promoção gerencial desta relação até novo desenho e evidência.",
            },
            "aa3_effective_claim_ceiling": "NOT_SUPPORTED_OR_UNAVAILABLE",
            "theory_can_override_aa2_terminal": False,
            "allowed_interpretation": "Explicar por que a relação não está pronta e quais condições metodológicas seriam necessárias para reabri-la.",
            "forbidden_interpretations": [
                "Mais gasto causou mais oferta em tempo integral.",
                "Valores nominais de anos distintos são comparáveis.",
                "A alternativa por matrícula é evidência independente.",
            ],
            "transferability_notes": "Não há referência primária direta congelada e o AA2 é insuficiente; teoria geral de financiamento não pode preencher a falha empírica nem elevar o teto.",
            "aa4_role": "TECHNICAL_ONLY_BLOCKED",
            "promotion_state": "BLOCKED_FROM_MANAGER_FACING",
        },
    ]

    for mechanism in definitions:
        claim = claims_by_id[mechanism["question_id"]]
        mechanism["aa2_terminal_state"] = claim["terminalState"]
        mechanism["aa2_claim_ceiling"] = claim["claimCeiling"]
        mechanism["aa2_negative_finding"] = claim["negativeFinding"]
    return definitions


def _augment_references(
    frozen_references: Sequence[Mapping[str, Any]],
    mechanisms: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    usage: dict[str, list[str]] = {}
    attribution: dict[str, list[dict[str, Any]]] = {}
    for mechanism in mechanisms:
        for reference in mechanism["primary_official_or_academic_refs"]:
            ref_id = reference["ref_id"]
            usage.setdefault(ref_id, []).append(mechanism["question_id"])
            attribution.setdefault(ref_id, []).append(
                {
                    "question_id": mechanism["question_id"],
                    "support_type": reference["support_type"],
                    "attributed_support": reference["attributed_support"],
                    "does_not_support": reference["does_not_support"],
                }
            )

    augmented = []
    for frozen in frozen_references:
        ref_id = frozen["refId"]
        item = dict(frozen)
        item["usedInQuestionIds"] = sorted(usage.get(ref_id, []))
        item["usageState"] = (
            "USED_WITH_STRICT_TRANSFER_LIMIT"
            if item["usedInQuestionIds"]
            else "UNUSED_FOR_CURRENT_AA2_QUESTIONS_RETAINED_EXPLICITLY"
        )
        item["attributions"] = attribution.get(ref_id, [])
        item["localEffectAuthorized"] = False
        item["municipalNumberAuthorized"] = False
        if not item["usedInQuestionIds"]:
            item["unusedReason"] = (
                "A referência permanece congelada, mas não sustenta diretamente o mecanismo "
                "específico de nenhuma das oito perguntas AA2; não foi reutilizada por analogia."
            )
            item["notUsableForQuestionIds"] = sorted(GAP_QUESTIONS)
            item["usageConstraint"] = "NOT_USABLE_FOR_P3_P7_P8"
        else:
            item["notUsableForQuestionIds"] = []
            item["usageConstraint"] = "ONLY_FOR_EXPLICIT_ATTRIBUTIONS_LISTED"
        augmented.append(item)
    return sorted(augmented, key=lambda item: item["refId"])


def _source_mechanism_reconciliation(
    literature: Mapping[str, Any],
    mechanisms: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    source_to_questions: dict[str, list[str]] = {}
    for mechanism in mechanisms:
        for source_id in mechanism["source_mechanism_ids"]:
            source_to_questions.setdefault(source_id, []).append(mechanism["question_id"])
    mapping = []
    for source in literature["mechanisms"]:
        source_id = source["mechanism_id"]
        question_ids = sorted(source_to_questions.get(source_id, []))
        mapping.append(
            {
                "source_mechanism_id": source_id,
                "source_eligible_for_page": source["eligible_for_page"],
                "mapped_question_ids": question_ids,
                "mapping_state": (
                    "MAPPED_WITH_STRICT_TRANSFER_LIMIT"
                    if question_ids
                    else "RETAINED_UNUSED_FOR_CURRENT_AA2_QUESTIONS"
                ),
            }
        )
    without_source = [
        {
            "question_id": mechanism["question_id"],
            "record_type": mechanism["record_type"],
            "reason": (
                "A identidade contábil deriva da fórmula e das séries locais."
                if mechanism["record_type"] == "ACCOUNTING_IDENTITY"
                else "Registro de fronteira criado para preservar a lacuna e o estado terminal AA2; não é mecanismo teórico novo."
            ),
        }
        for mechanism in mechanisms
        if not mechanism["source_mechanism_ids"]
    ]
    return {
        "sourceSchemaVersion": literature["schemaVersion"],
        "frozenSourceMechanismCount": literature["mechanismCount"],
        "aa3QuestionRecordCount": len(mechanisms),
        "oneToOneMappingExpected": False,
        "explanation": (
            "Os sete mecanismos Job5L não correspondem um a um às oito perguntas: "
            "P4 combina dois mecanismos; P2 é identidade contábil; P3, P7 e P8 são "
            "fronteiras interpretativas; M5 e M7 permanecem sem uso nas perguntas atuais."
        ),
        "recordTypeCounts": {
            record_type: sum(
                mechanism["record_type"] == record_type for mechanism in mechanisms
            )
            for record_type in (
                "THEORY_MECHANISM",
                "ACCOUNTING_IDENTITY",
                "INTERPRETATION_BOUNDARY",
            )
        },
        "sourceMechanismMappings": sorted(
            mapping, key=lambda item: item["source_mechanism_id"]
        ),
        "questionRecordsWithoutSourceMechanism": without_source,
    }


def _coverage_frame(mechanisms: Sequence[Mapping[str, Any]]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for mechanism in mechanisms:
        references = mechanism["primary_official_or_academic_refs"]
        if not references:
            rows.append(
                {
                    "question_id": mechanism["question_id"],
                    "mechanism_id": mechanism["mechanism_id"],
                    "record_type": mechanism["record_type"],
                    "source_mechanism_ids": "|".join(mechanism["source_mechanism_ids"]),
                    "reference_id": "NOT_APPLICABLE_IDENTITY" if mechanism["question_id"] in IDENTITY_QUESTIONS else "LOCAL_PRIMARY_REFERENCE_GAP",
                    "reference_coverage_state": mechanism["reference_coverage_state"],
                    "support_type": "ACCOUNTING_IDENTITY" if mechanism["question_id"] in IDENTITY_QUESTIONS else "NO_DIRECT_PRIMARY_REFERENCE_IN_FROZEN_LOCAL_LIBRARY",
                    "directly_supports_attributed_mechanism": mechanism["question_id"] in IDENTITY_QUESTIONS,
                    "local_effect_authorized": False,
                    "municipal_number_authorized": False,
                    "attributed_support": "Identidade matemática verificável nas séries locais." if mechanism["question_id"] in IDENTITY_QUESTIONS else "Nenhum apoio primário direto atribuído.",
                    "unsupported_inference": "Componente residual como comportamento ou causa." if mechanism["question_id"] in IDENTITY_QUESTIONS else "Prosa genérica como substituta de referência primária.",
                    "aa2_terminal_state": mechanism["aa2_terminal_state"],
                    "aa3_effective_claim_ceiling": mechanism["aa3_effective_claim_ceiling"],
                    "aa4_role": mechanism["aa4_role"],
                    "promotion_state": mechanism["promotion_state"],
                    "aa2_descriptive_artifact": mechanism.get("aa2_descriptive_basis", {}).get("artifact", ""),
                    "gap_reason": "" if mechanism["question_id"] in IDENTITY_QUESTIONS else mechanism["transferability_notes"],
                }
            )
            continue
        for reference in references:
            rows.append(
                {
                    "question_id": mechanism["question_id"],
                    "mechanism_id": mechanism["mechanism_id"],
                    "record_type": mechanism["record_type"],
                    "source_mechanism_ids": "|".join(mechanism["source_mechanism_ids"]),
                    "reference_id": reference["ref_id"],
                    "reference_coverage_state": mechanism["reference_coverage_state"],
                    "support_type": reference["support_type"],
                    "directly_supports_attributed_mechanism": reference["directly_supports_attributed_mechanism"],
                    "local_effect_authorized": reference["local_effect_authorized"],
                    "municipal_number_authorized": reference["municipal_number_authorized"],
                    "attributed_support": reference["attributed_support"],
                    "unsupported_inference": reference["does_not_support"],
                    "aa2_terminal_state": mechanism["aa2_terminal_state"],
                    "aa3_effective_claim_ceiling": mechanism["aa3_effective_claim_ceiling"],
                    "aa4_role": mechanism["aa4_role"],
                    "promotion_state": mechanism["promotion_state"],
                    "aa2_descriptive_artifact": mechanism.get("aa2_descriptive_basis", {}).get("artifact", ""),
                    "gap_reason": "",
                }
            )
    return pd.DataFrame(rows).sort_values(
        ["question_id", "reference_id"], kind="stable"
    ).reset_index(drop=True)


def _build_boundaries(mechanisms: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    return {
        "schemaVersion": "vocacoes-pne-aa3-interpretation-boundaries-v1",
        "programId": "vocacoes-pne-advanced-analytics-v1",
        "stage": "AA3",
        "generatedAt": GENERATED_AT,
        "globalRules": [
            {
                "rule_id": "AA3_THEORY_NEVER_OVERRIDES_AA2",
                "rule": "Literatura não altera estado terminal, significância, robustez, disponibilidade ou teto empírico do AA2.",
            },
            {
                "rule_id": "AA3_NO_EXTERNAL_NUMBER_AS_LOCAL_ESTIMATE",
                "rule": "Nenhum número externo pode ser apresentado como estimativa municipal ou regional.",
            },
            {
                "rule_id": "AA3_REFERENCE_GAP_REDUCES_CEILING",
                "rule": "Ausência de referência primária direta reduz o teto; prosa genérica não preenche a lacuna.",
            },
            {
                "rule_id": "AA3_ASSOCIATION_IS_NOT_CAUSATION",
                "rule": "Associação territorial ou compatibilidade teórica não identifica causalidade individual ou municipal.",
            },
            {
                "rule_id": "AA3_LENSES_REMAIN_DISTINCT",
                "rule": "Residência, localização da escola e estabelecimento de trabalho permanecem lentes distintas e não ligam as mesmas pessoas.",
            },
            {
                "rule_id": "AA3_UNUSED_REFERENCES_BLOCKED_FOR_GAP_QUESTIONS",
                "rule": "As referências congeladas não usadas são NOT_USABLE_FOR_P3_P7_P8 e não podem preencher essas lacunas no AA4.",
            },
            {
                "rule_id": "AA3_P4_P6_NEGATIVE_TERMINAL_REMAINS_PRIMARY",
                "rule": "P4 e P6 permanecem NO_ROBUST_ASSOCIATION; a literatura justifica a pergunta, não cria sinal ou padrão local.",
            },
        ],
        "questionBoundaries": [
            {
                "question_id": mechanism["question_id"],
                "mechanism_id": mechanism["mechanism_id"],
                "record_type": mechanism["record_type"],
                "source_mechanism_ids": mechanism["source_mechanism_ids"],
                "reference_coverage_state": mechanism["reference_coverage_state"],
                "aa2_terminal_state": mechanism["aa2_terminal_state"],
                "aa3_effective_claim_ceiling": mechanism["aa3_effective_claim_ceiling"],
                "allowed_interpretation": mechanism["allowed_interpretation"],
                "forbidden_interpretations": mechanism["forbidden_interpretations"],
                "falsification_or_boundary": mechanism["falsification_or_boundary"],
                "alternative_explanations": mechanism["alternative_explanations"],
                "transferability_notes": mechanism["transferability_notes"],
                "aa2_descriptive_basis": mechanism.get("aa2_descriptive_basis"),
                "aa4_role": mechanism["aa4_role"],
                "promotion_state": mechanism["promotion_state"],
            }
            for mechanism in mechanisms
        ],
        "referenceGapQuestionIds": sorted(GAP_QUESTIONS),
        "identityQuestionIds": sorted(IDENTITY_QUESTIONS),
        "unusedReferenceIdsBlockedForGapQuestions": sorted(
            EXPECTED_UNUSED_REFERENCE_IDS
        ),
        "unusedReferenceRestriction": "NOT_USABLE_FOR_P3_P7_P8",
        "theoryCanOverrideAa2Terminal": False,
    }


def _build_evidence_appendix(
    *,
    input_hashes: Mapping[str, str],
    mechanisms: Sequence[Mapping[str, Any]],
    qa: Mapping[str, Any],
    contract: Mapping[str, Any],
) -> dict[str, Any]:
    input_descriptors = {
        "aa2ManifestSha256": (
            "FILE_SHA256",
            "Manifesto congelado do AA2.",
        ),
        "aa2ClaimsSha256": (
            "FILE_SHA256",
            "Claims e estados terminais congelados do AA2.",
        ),
        "aa2ArtifactSetDigestSha256": (
            "ARTIFACT_SET_CONTENT_DIGEST",
            "Digest canônico do conjunto analítico AA2; não é hash de um arquivo isolado.",
        ),
        "literatureSha256": (
            "FILE_SHA256",
            "Fonte literária local congelada do Job5L.",
        ),
        "localMechanismLibrarySha256": (
            "FILE_SHA256",
            "Biblioteca local de mecanismos.",
        ),
        "analyticalGuidelineSha256": (
            "FILE_SHA256",
            "Diretriz analítica local.",
        ),
        "courseCboBridgeSha256": (
            "FILE_SHA256",
            "Projeção normativa curso–CBO em grão de dois dígitos.",
        ),
        "programPlanSha256": (
            "FILE_SHA256",
            "Plano de execução AA0–AA6.",
        ),
        "opusReconciliationSha256": (
            "FILE_SHA256",
            "Reconciliação imutável do primeiro parecer Opus AA3.",
        ),
        "contractSha256": (
            "FILE_SHA256",
            "Contrato executável AA3.",
        ),
        "publicDataTreeDigestSha256": (
            "DIRECTORY_CONTENT_DIGEST_WRITE_SENTINEL",
            "Digest de conteúdo da árvore public/data no início protegido da materialização; não é insumo analítico.",
        ),
    }
    if set(input_hashes) != set(input_descriptors):
        raise TheoryLibraryValidationError(
            "Apêndice AA3 não reconhece exatamente os onze vínculos de entrada."
        )

    reconciliation_crosswalk = [
        {
            "findingId": "AA3_OPUS_PUBLIC_SENTINEL_FORMALIZATION",
            "decision": "ACCEPTED",
            "revisionIds": ["A"],
            "appliedEvidence": "Gate de ausência de escrita, invariância por candidato, igualdade entre candidatos e política sem rebaseline automático.",
        },
        {
            "findingId": "AA3_OPUS_P4_P6_NON_AFFIRMATIVE_CEILINGS",
            "decision": "ACCEPTED",
            "revisionIds": ["B"],
            "appliedEvidence": "Tetos não afirmativos, artefatos AA2 literais e NO_ROBUST_ASSOCIATION preservado como resultado primário.",
        },
        {
            "findingId": "AA3_OPUS_SEVEN_TO_EIGHT_RECONCILIATION",
            "decision": "ACCEPTED",
            "revisionIds": ["C"],
            "appliedEvidence": "Sete mecanismos de origem reconciliados com oito registros tipados.",
        },
        {
            "findingId": "AA3_OPUS_NAMED_QA_INVARIANTS",
            "decision": "ACCEPTED",
            "revisionIds": ["D"],
            "appliedEvidence": "QA nomeado para completude, DATA_LOGIC, IBGE textual, rede total, fonte e sentinela.",
        },
        {
            "findingId": "AA3_OPUS_UNUSED_REFERENCE_RESTRICTION",
            "decision": "ACCEPTED_AS_PREVENTIVE_GUARD",
            "revisionIds": ["E"],
            "appliedEvidence": "Três referências preservadas com NOT_USABLE_FOR_P3_P7_P8.",
        },
        {
            "findingId": "AA3_OPUS_P5_NOMENCLATURAL_BOUNDARY",
            "decision": "ACCEPTED_AS_PREVENTIVE_GUARD",
            "revisionIds": ["F"],
            "appliedEvidence": "P5 limitado a correspondência descritiva CBO dois dígitos, sem demanda, empregabilidade, egressos ou validação da ponte.",
        },
        {
            "findingId": "AA3_OPUS_MANIFEST_LAST_AND_CANDIDATE_DIFFERENCE",
            "decision": "CLARIFIED_WITH_EXISTING_IMPLEMENTATION_AND_NEW_QA",
            "revisionIds": ["D", "G"],
            "appliedEvidence": "Manifesto gravado por último; digests pré-normalização e campos normalizados registrados no próprio pacote.",
        },
        {
            "findingId": "AA3_OPUS_GZIP_DETERMINISM",
            "decision": "CLARIFIED_WITH_EXISTING_IMPLEMENTATION",
            "revisionIds": ["D"],
            "appliedEvidence": "CSV.GZ serializado com mtime=0 e comparado entre processos independentes.",
        },
        {
            "findingId": "AA3_OPUS_FULL_TEXT_REVIEW",
            "decision": "ACCEPTED_AS_LIMITATION_NOT_FILLED_BY_UNAUTHORIZED_RESEARCH",
            "revisionIds": ["G"],
            "appliedEvidence": "Limitação de texto integral declarada; somente fonte local congelada, sem efeito ou número local.",
        },
    ]
    samples = [
        mechanism
        for mechanism in mechanisms
        if mechanism["question_id"]
        in {
            "P1_CONTEXT_ADJUSTED_TRAJECTORY",
            "P4_YOUTH_WORK_AND_HIGH_SCHOOL",
            "P5_OCCUPATIONS_AND_EPT",
            "P6_ADULT_SCHOOLING_WORK_AND_EJA",
        }
    ]
    sentinel = contract["publicDataSentinel"]
    return {
        "schemaVersion": "vocacoes-pne-aa3-complementary-evidence-v1",
        "programId": "vocacoes-pne-advanced-analytics-v1",
        "stage": "AA3",
        "generatedAt": GENERATED_AT,
        "purpose": "Fechar as lacunas residuais de apresentação de evidência da reauditoria Opus sem alterar resultados, fórmulas ou tetos.",
        "inputHashCount": len(input_hashes),
        "inputHashItems": [
            {
                "inputHashKey": key,
                "verificationType": input_descriptors[key][0],
                "sha256OrContentDigest": value,
                "meaning": input_descriptors[key][1],
            }
            for key, value in input_hashes.items()
        ],
        "ceilingPolicy": {
            "mayWidenAa2": False,
            "qaCheckId": "AA3_EFFECTIVE_CLAIM_CEILING_NEVER_WIDENS_AA2",
            "comparisonRule": "NARROWER_OR_EQUAL_BY_EXPLICIT_QUESTION_POLICY",
        },
        "ceilingRows": [
            {
                "question_id": mechanism["question_id"],
                "aa2_terminal_state": mechanism["aa2_terminal_state"],
                "aa2_claim_ceiling": mechanism["aa2_claim_ceiling"],
                "aa3_effective_claim_ceiling": mechanism[
                    "aa3_effective_claim_ceiling"
                ],
                "aa4_role": mechanism["aa4_role"],
                "promotion_state": mechanism["promotion_state"],
                "ceilingRelation": "NARROWER_OR_EQUAL_BY_EXPLICIT_QUESTION_POLICY",
                "allowedPair": list(
                    EXPECTED_CEILING_POLICY[mechanism["question_id"]]
                ),
            }
            for mechanism in mechanisms
        ],
        "reconciliationDecisionToRevisionCrosswalk": reconciliation_crosswalk,
        "technicalSpecificitySamples": [
            {
                "question_id": mechanism["question_id"],
                "manager_question": mechanism["manager_question"],
                "alternative_explanations": mechanism[
                    "alternative_explanations"
                ],
                "falsification_or_boundary": mechanism[
                    "falsification_or_boundary"
                ],
            }
            for mechanism in samples
        ],
        "publicDigestScope": {
            "role": "WRITE_INTEGRITY_SENTINEL_ONLY_NOT_ANALYTICAL_INPUT",
            "historicalAa2WholeTreeDigestSha256": sentinel[
                "aa2HistoricalDigestSha256"
            ],
            "firstObservedStableWholeTreeDigestSha256": sentinel[
                "firstObservedStableDigestSha256"
            ],
            "latestObservedStableWholeTreeDigestSha256": sentinel[
                "latestObservedStableDigestSha256"
            ],
            "candidateEntryWholeTreeDigestSha256": input_hashes[
                "publicDataTreeDigestSha256"
            ],
            "regionalEventEvidenceScope": "11 arquivos/subárvore public/data/regioes com hashes e timestamps individuais; não reconstrói por si só o digest da árvore public/data inteira.",
            "pneMatrizEventEvidenceScope": "Raiz public/data/pne2026-matriz e manifesto próprios; não é analiticamente comparável ao digest histórico da árvore public/data inteira.",
            "digestComparabilityRule": "Digests com escopos distintos servem à atribuição operacional; não são séries analíticas nem devem ser comparados como variação de indicador.",
            "aa4EntryPolicy": sentinel["futureBaselinePolicy"],
        },
        "transactionalCommitPath": {
            "stagingCandidates": 2,
            "candidateRoots": "Diretórios irmãos temporários .aa3-first-* e .aa3-second-* sob a raiz .tmp do pacote.",
            "steps": [
                "Materializar cada candidato em processo de sistema operacional fresco e somente em staging.",
                "Validar guardas externas, invariância de public/data e igualdade do conjunto não manifesto inicial.",
                "Registrar digests pré-normalização e finalizar evidência comum nos dois candidatos.",
                "Recalcular hashes dos artefatos e gravar o manifesto comum por último.",
                "Validar o pacote e exigir igualdade da árvore completa pós-normalização.",
                "Promover staging com os.replace; mover alvo anterior para .rollback-aa3 e restaurá-lo se a promoção falhar.",
            ],
            "atomicPrimitive": "os.replace",
            "rollbackSuffix": ".rollback-aa3",
            "manifestWrittenLast": True,
            "failClosed": True,
        },
        "inheritedLiteratureLimitation": {
            "newExternalResearchAuthorized": False,
            "fullTextReReviewPerformedInAa3": False,
            "localFrozenReferencesOnly": True,
            "localEffectAuthorized": False,
            "municipalNumberAuthorized": False,
            "downstreamRule": "AA4 deve transportar esta limitação; não pode convertê-la em mecanismo local comprovado.",
        },
        "opusReaudit": {
            "path": OPUS_REAUDIT_PATH.relative_to(REPO_ROOT).as_posix(),
            "sha256": EXPECTED_OPUS_REAUDIT_SHA256,
            "verdict": "ON_TRACK",
            "confidence": 0.78,
            "auditedCheckpointArtifactSetDigestSha256": "7298bb5db0e03b85b1c4e9a2b3c358a16bcfe28a970120ad293da5503e1a466d",
            "residualEvidenceRecommendation": "ADD_MANIFEST_LINKED_EVIDENCE_APPENDIX",
            "recommendationState": "APPLIED_AFTER_REAUDIT",
            "finalPackageDirectlyReaudited": False,
            "interpretation": "O parecer ON_TRACK avaliou o checkpoint corrigido e recomendou este apêndice; os bytes finais foram validados localmente depois do parecer e não são apresentados como reauditados diretamente.",
        },
        "qaCheckIds": [check["checkId"] for check in qa["checks"]],
        "determinismEvidence": {
            "state": "PENDING_PARENT_PROCESS_RECONCILIATION",
            "reason": "Os digests candidatos só existem após dois processos frescos; o processo pai os acrescenta de forma idêntica antes do manifesto final.",
        },
    }


def _quality_checks(
    contract: Mapping[str, Any],
    literature: Mapping[str, Any],
    mechanisms: Sequence[Mapping[str, Any]],
    references: Sequence[Mapping[str, Any]],
    coverage: pd.DataFrame,
    source_reconciliation: Mapping[str, Any],
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []

    def record(check_id: str, passed: bool, evidence: Any) -> None:
        checks.append({"checkId": check_id, "passed": bool(passed), "evidence": evidence})

    required_fields = set(contract["requiredMechanismFields"])
    mechanism_ids = [item["question_id"] for item in mechanisms]
    coverage_counts = {
        state: sum(item["reference_coverage_state"] == state for item in mechanisms)
        for state in contract["referenceCoverageStates"]
    }
    frozen_ref_ids = {item["refId"] for item in literature["references"]}
    used_ref_ids = {
        reference["ref_id"]
        for mechanism in mechanisms
        for reference in mechanism["primary_official_or_academic_refs"]
    }
    output_ref_ids = {item["refId"] for item in references}
    unused_ref_ids = {
        item["refId"] for item in references if item["usageState"].startswith("UNUSED_")
    }
    claim_ceiling_by_question = {
        item["question_id"]: item["aa3_effective_claim_ceiling"] for item in mechanisms
    }

    record("AA3_QUESTION_COUNT_EXACT", len(mechanisms) == 8, len(mechanisms))
    record("AA3_QUESTION_IDS_EXACT", mechanism_ids == list(QUESTION_IDS), mechanism_ids)
    record(
        "AA3_REQUIRED_FIELDS_COMPLETE",
        all(required_fields.issubset(item) for item in mechanisms),
        sorted(required_fields),
    )
    fields_allowing_empty_lists = {
        "primary_official_or_academic_refs",
        "source_mechanism_ids",
    }
    record(
        "AA3_REQUIRED_FIELDS_NONEMPTY_EXCEPT_DECLARED_REFERENCE_GAPS",
        all(
            all(
                field in item
                and (
                    field in fields_allowing_empty_lists
                    or (
                        field == "theory_can_override_aa2_terminal"
                        and item[field] is False
                    )
                    or item[field] not in (None, "", [], {})
                )
                for field in required_fields
            )
            for item in mechanisms
        ),
        {
            "questionCount": len(mechanisms),
            "fieldsAllowingEmptyLists": sorted(fields_allowing_empty_lists),
        },
    )
    record(
        "AA3_COVERAGE_COUNTS_EXACT",
        coverage_counts
        == {
            "SUPPORTED_WITH_STRICT_TRANSFER_LIMIT": 4,
            "IDENTITY_NO_MECHANISM_REFERENCE_REQUIRED": 1,
            "LOCAL_PRIMARY_REFERENCE_GAP_CEILING_REDUCED": 3,
        },
        coverage_counts,
    )
    record(
        "AA3_REFERENCE_GAPS_EXACT",
        {item["question_id"] for item in mechanisms if "GAP" in item["reference_coverage_state"]}
        == GAP_QUESTIONS,
        sorted(GAP_QUESTIONS),
    )
    record(
        "AA3_REFERENCES_FROZEN_AND_COMPLETE",
        output_ref_ids == frozen_ref_ids and len(references) == 8,
        sorted(output_ref_ids),
    )
    record(
        "AA3_USED_REFERENCES_EXIST_AND_SUPPORT_ATTRIBUTION",
        used_ref_ids.issubset(frozen_ref_ids)
        and all(
            reference["directly_supports_attributed_mechanism"] is True
            for mechanism in mechanisms
            for reference in mechanism["primary_official_or_academic_refs"]
        ),
        sorted(used_ref_ids),
    )
    record(
        "AA3_UNUSED_REFERENCES_RETAINED_EXPLICITLY",
        unused_ref_ids == EXPECTED_UNUSED_REFERENCE_IDS,
        sorted(unused_ref_ids),
    )
    record(
        "AA3_UNUSED_REFERENCES_BLOCKED_FOR_GAP_QUESTIONS",
        all(
            item["usageConstraint"] == "NOT_USABLE_FOR_P3_P7_P8"
            and set(item["notUsableForQuestionIds"]) == GAP_QUESTIONS
            for item in references
            if item["refId"] in EXPECTED_UNUSED_REFERENCE_IDS
        ),
        sorted(EXPECTED_UNUSED_REFERENCE_IDS),
    )
    record(
        "AA3_LITERATURE_NO_LOCAL_EFFECT_OR_NUMBER",
        literature["literatureAuthorizesLocalEffects"] is False
        and literature["literatureProvidesMunicipalNumbers"] is False
        and all(item["localEffectAuthorized"] is False and item["municipalNumberAuthorized"] is False for item in references),
        {"referenceCount": len(references)},
    )
    record(
        "AA3_THEORY_NEVER_OVERRIDES_AA2_TERMINAL",
        all(item["theory_can_override_aa2_terminal"] is False for item in mechanisms),
        {"questionCount": len(mechanisms)},
    )
    record(
        "AA3_NEGATIVE_TERMINALS_NOT_RESCUED",
        all(
            item["aa2_terminal_state"] in {"NO_ROBUST_ASSOCIATION", "INSUFFICIENT_DATA"}
            for item in mechanisms
            if item["question_id"] in {
                "P3_SCHOOL_CONDITIONS_AND_TRAJECTORY",
                "P4_YOUTH_WORK_AND_HIGH_SCHOOL",
                "P6_ADULT_SCHOOLING_WORK_AND_EJA",
                "P7_RURALITY_INCLUSION_AND_ACCESS",
                "P8_FINANCING_OFFER_AND_CAPACITY",
            }
        ),
        {
            item["question_id"]: item["aa2_terminal_state"]
            for item in mechanisms
            if item["aa2_negative_finding"] is True
        },
    )
    record(
        "AA3_P8_MANAGER_PROMOTION_BLOCKED",
        next(item for item in mechanisms if item["question_id"] == "P8_FINANCING_OFFER_AND_CAPACITY")["promotion_state"]
        == "BLOCKED_FROM_MANAGER_FACING"
        and claim_ceiling_by_question["P8_FINANCING_OFFER_AND_CAPACITY"]
        == "NOT_SUPPORTED_OR_UNAVAILABLE",
        claim_ceiling_by_question["P8_FINANCING_OFFER_AND_CAPACITY"],
    )
    p4 = next(
        item
        for item in mechanisms
        if item["question_id"] == "P4_YOUTH_WORK_AND_HIGH_SCHOOL"
    )
    p6 = next(
        item
        for item in mechanisms
        if item["question_id"] == "P6_ADULT_SCHOOLING_WORK_AND_EJA"
    )
    record(
        "AA3_P4_P6_NON_AFFIRMATIVE_CEILINGS_AND_AA2_BASIS",
        p4["aa3_effective_claim_ceiling"]
        == "NO_ROBUST_ASSOCIATION_LITERATURE_SUPPORTS_MONITORING_QUESTION_ONLY"
        and p6["aa3_effective_claim_ceiling"]
        == "NO_ROBUST_ASSOCIATION_DESCRIPTIVE_DISTRIBUTIONS_ONLY"
        and p4["aa2_descriptive_basis"]["association_terminal_remains_primary"]
        == "NO_ROBUST_ASSOCIATION"
        and p6["aa2_descriptive_basis"]["association_terminal_remains_primary"]
        == "NO_ROBUST_ASSOCIATION"
        and p4["aa2_descriptive_basis"]["rule_passed"] is False
        and p6["aa2_descriptive_basis"]["stable_primary_fit"] is None,
        {
            "P4": p4["aa2_descriptive_basis"],
            "P6": p6["aa2_descriptive_basis"],
        },
    )
    ceiling_rows = [
        {
            "questionId": item["question_id"],
            "aa2ClaimCeiling": item["aa2_claim_ceiling"],
            "aa3EffectiveClaimCeiling": item["aa3_effective_claim_ceiling"],
            "allowedPair": list(EXPECTED_CEILING_POLICY[item["question_id"]]),
        }
        for item in mechanisms
    ]
    record(
        "AA3_EFFECTIVE_CLAIM_CEILING_NEVER_WIDENS_AA2",
        all(
            (
                item["aa2_claim_ceiling"],
                item["aa3_effective_claim_ceiling"],
            )
            == EXPECTED_CEILING_POLICY[item["question_id"]]
            for item in mechanisms
        )
        and contract["qualityRequirements"][
            "effectiveClaimCeilingMayWidenAa2"
        ]
        is False,
        ceiling_rows,
    )
    p5 = next(
        item for item in mechanisms if item["question_id"] == "P5_OCCUPATIONS_AND_EPT"
    )
    p5_forbidden = " ".join(p5["forbidden_interpretations"]).lower()
    record(
        "AA3_P5_NOMENCLATURAL_CBO2_BOUNDARY",
        p5["aa3_effective_claim_ceiling"]
        == "DESCRIPTIVE_NOMENCLATURE_CORRESPONDENCE_CBO_2_DIGIT_ONLY"
        and all(
            token in p5_forbidden
            for token in ("demanda", "empreg", "egress", "ponte")
        ),
        {
            "claimCeiling": p5["aa3_effective_claim_ceiling"],
            "forbiddenInterpretationCount": len(p5["forbidden_interpretations"]),
        },
    )
    record(
        "AA3_ALTERNATIVES_BOUNDARIES_TRANSFER_NOTES_PRESENT",
        all(
            item["alternative_explanations"]
            and item["falsification_or_boundary"]
            and item["transferability_notes"].strip()
            for item in mechanisms
        ),
        {"questionCount": len(mechanisms)},
    )
    record(
        "AA3_FORBIDDEN_INTERPRETATIONS_PRESENT",
        all(len(item["forbidden_interpretations"]) >= 3 for item in mechanisms),
        {item["question_id"]: len(item["forbidden_interpretations"]) for item in mechanisms},
    )
    record(
        "AA3_IDENTITY_HAS_NO_MECHANISM_REFERENCE",
        next(item for item in mechanisms if item["question_id"] in IDENTITY_QUESTIONS)["primary_official_or_academic_refs"]
        == [],
        sorted(IDENTITY_QUESTIONS),
    )
    record(
        "AA3_COVERAGE_MATRIX_GRAIN_EXACT",
        len(coverage) == 9
        and coverage[["question_id", "reference_id"]].duplicated().sum() == 0
        and set(coverage["question_id"]) == set(QUESTION_IDS),
        {"rowCount": len(coverage)},
    )
    record(
        "AA3_COVERAGE_MATRIX_NO_LOCAL_EFFECT_OR_NUMBER",
        not coverage["local_effect_authorized"].astype(bool).any()
        and not coverage["municipal_number_authorized"].astype(bool).any(),
        {"rowCount": len(coverage)},
    )
    record(
        "AA3_SOURCE_MECHANISM_MAPPING_COMPLETE",
        source_reconciliation["frozenSourceMechanismCount"] == 7
        and source_reconciliation["aa3QuestionRecordCount"] == 8
        and len(source_reconciliation["sourceMechanismMappings"]) == 7
        and {
            item["source_mechanism_id"]
            for item in source_reconciliation["sourceMechanismMappings"]
        }
        == {item["mechanism_id"] for item in literature["mechanisms"]}
        and {
            item["question_id"]
            for item in source_reconciliation["questionRecordsWithoutSourceMechanism"]
        }
        == {
            "P2_DEMOGRAPHY_ENROLLMENT_DECOMPOSITION",
            "P3_SCHOOL_CONDITIONS_AND_TRAJECTORY",
            "P7_RURALITY_INCLUSION_AND_ACCESS",
            "P8_FINANCING_OFFER_AND_CAPACITY",
        },
        source_reconciliation,
    )
    record(
        "AA3_RECORD_TYPE_COUNTS_EXACT",
        source_reconciliation["recordTypeCounts"]
        == {
            "THEORY_MECHANISM": 4,
            "ACCOUNTING_IDENTITY": 1,
            "INTERPRETATION_BOUNDARY": 3,
        },
        source_reconciliation["recordTypeCounts"],
    )
    record(
        "AA3_CLASSIFICATION_DATA_LOGIC",
        contract.get("classification") == "DATA_LOGIC",
        contract.get("classification"),
    )
    municipality_code = contract["scope"]["selectedMunicipalityIbgeCode"]
    record(
        "AA3_MUNICIPALITY_IDENTITY_TEXTUAL_7_DIGITS",
        isinstance(municipality_code, str)
        and len(municipality_code) == 7
        and municipality_code.isdigit()
        and contract["scope"]["municipalityIdentity"]
        == "textual_ibge_code_7_digits",
        municipality_code,
    )
    record(
        "AA3_EDUCATION_SCOPE_TOTAL_ALL_DEPENDENCIES",
        contract["scope"]["educationNetworkScope"] == "total_all_dependencies",
        contract["scope"]["educationNetworkScope"],
    )
    record(
        "AA3_PUBLIC_SENTINEL_DEVIATION_FORMALLY_RECONCILED",
        contract["publicDataSentinel"]["gateRule"]
        == "PUBLIC_DATA_NOT_WRITTEN_BY_AA3_INVARIANT_WITHIN_AND_EQUAL_ACROSS_TWO_CANDIDATE_MATERIALIZATIONS"
        and contract["publicDataSentinel"]["aa2HistoricalDigestPreserved"] is True
        and len(contract["publicDataSentinel"]["observedChangedPaths"]) == 11
        and contract["publicDataSentinel"]["fixedDigestIsAnalyticalInput"]
        is False
        and contract["publicDataSentinel"]["futureBaselinePolicy"]["automaticRebaselineAllowed"]
        is False
        and contract["generation"]["publicDataFixedDigestRequired"] is False,
        {
            "historicalDigest": contract["publicDataSentinel"]["aa2HistoricalDigestSha256"],
            "firstObservedStableDigest": contract["publicDataSentinel"]["firstObservedStableDigestSha256"],
            "latestObservedStableDigest": contract["publicDataSentinel"]["latestObservedStableDigestSha256"],
            "changedPathCount": len(contract["publicDataSentinel"]["observedChangedPaths"]),
            "integrityMode": contract["generation"]["publicDataIntegrityMode"],
        },
    )
    record(
        "AA3_INITIAL_OPUS_RECONCILIATION_LINKED",
        sha256_file(OPUS_RECONCILIATION_PATH)
        == EXPECTED_OPUS_RECONCILIATION_SHA256,
        EXPECTED_OPUS_RECONCILIATION_SHA256,
    )
    opus_reaudit = _load_json(OPUS_REAUDIT_PATH)
    record(
        "AA3_OPUS_REAUDIT_ON_TRACK_AND_RESIDUAL_ACTION_BOUND",
        sha256_file(OPUS_REAUDIT_PATH) == EXPECTED_OPUS_REAUDIT_SHA256
        and opus_reaudit.get("verdict") == "ON_TRACK"
        and opus_reaudit.get("confidence") == 0.78
        and contract["qualityRequirements"][
            "evidenceAppendixManifestLinkedRequired"
        ]
        is True,
        {
            "sha256": EXPECTED_OPUS_REAUDIT_SHA256,
            "verdict": opus_reaudit.get("verdict"),
            "confidence": opus_reaudit.get("confidence"),
            "residualAction": "EVIDENCE_APPENDIX_MANIFEST_LINKED",
        },
    )
    record(
        "AA3_MANIFEST_LAST_CONTRACT",
        contract["package"]["manifestLast"] is True,
        contract["package"]["manifestLast"],
    )
    record(
        "AA3_EXTERNAL_RESEARCH_REMAINS_UNAUTHORIZED",
        contract["scope"]["externalResearchAuthorized"] is False
        and contract["scope"]["localFrozenReferencesOnly"] is True,
        contract["scope"],
    )
    record(
        "AA3_NETWORK_DATABASE_PUBLIC_BUILD_POLICY",
        contract["generation"]["networkUsed"] is False
        and contract["generation"]["databaseUsed"] is False
        and contract["generation"]["publicDataWritesAllowed"] is False
        and contract["generation"]["fullBuildAllowed"] is False,
        contract["generation"],
    )
    return checks


def build_theory_package(
    *, expected_public_digest: str | None = None
) -> dict[str, Any]:
    input_hashes = verify_frozen_inputs(
        expected_public_digest=expected_public_digest
    )
    contract = _load_json(CONTRACT_PATH)
    aa2_claims = _load_json(AA2_CLAIMS_PATH)
    literature = _load_json(LITERATURE_PATH)
    claims_by_id = {claim["questionId"]: claim for claim in aa2_claims["claims"]}
    mechanisms = _mechanism_definitions(claims_by_id)
    references = _augment_references(literature["references"], mechanisms)
    source_reconciliation = _source_mechanism_reconciliation(
        literature, mechanisms
    )
    coverage = _coverage_frame(mechanisms)
    boundaries = _build_boundaries(mechanisms)
    checks = _quality_checks(
        contract,
        literature,
        mechanisms,
        references,
        coverage,
        source_reconciliation,
    )
    failures = [check for check in checks if check["passed"] is not True]
    qa = {
        "schemaVersion": "vocacoes-pne-aa3-qa-v1",
        "programId": "vocacoes-pne-advanced-analytics-v1",
        "stage": "AA3",
        "generatedAt": GENERATED_AT,
        "finalState": "PASS" if not failures else "FAIL",
        "checkCount": len(checks),
        "passedCount": len(checks) - len(failures),
        "failedCount": len(failures),
        "counts": {
            "questionCount": len(mechanisms),
            "referenceCount": len(references),
            "usedReferenceCount": sum(bool(item["usedInQuestionIds"]) for item in references),
            "unusedReferenceCount": sum(not item["usedInQuestionIds"] for item in references),
            "coverageMatrixRowCount": len(coverage),
            "supportedWithStrictTransferLimitCount": sum(item["question_id"] in SUPPORTED_QUESTIONS for item in mechanisms),
            "identityNoMechanismReferenceRequiredCount": sum(item["question_id"] in IDENTITY_QUESTIONS for item in mechanisms),
            "localPrimaryReferenceGapCount": sum(item["question_id"] in GAP_QUESTIONS for item in mechanisms),
            "theoryOverrideAllowedCount": sum(item["theory_can_override_aa2_terminal"] is True for item in mechanisms),
            "managerFacingBlockedCount": sum(item["promotion_state"] == "BLOCKED_FROM_MANAGER_FACING" for item in mechanisms),
            "sourceMechanismCount": literature["mechanismCount"],
            "theoryMechanismRecordCount": source_reconciliation["recordTypeCounts"]["THEORY_MECHANISM"],
            "accountingIdentityRecordCount": source_reconciliation["recordTypeCounts"]["ACCOUNTING_IDENTITY"],
            "interpretationBoundaryRecordCount": source_reconciliation["recordTypeCounts"]["INTERPRETATION_BOUNDARY"],
        },
        "checks": checks,
    }
    if failures:
        failed_ids = ", ".join(check["checkId"] for check in failures)
        raise TheoryLibraryValidationError(f"QA AA3 falhou: {failed_ids}")

    library = {
        "schemaVersion": "vocacoes-pne-aa3-theory-library-v1",
        "programId": "vocacoes-pne-advanced-analytics-v1",
        "stage": "AA3",
        "generatedAt": GENERATED_AT,
        "scope": {
            "state": "RS",
            "regionId": "REGION_VALE_DO_SINOS",
            "selectedMunicipalityIbgeCode": "4313375",
            "municipalityIdentity": "textual_ibge_code_7_digits",
            "educationNetworkScope": "total_all_dependencies",
        },
        "claimPolicy": {
            "literatureAuthorizesLocalEffects": False,
            "literatureProvidesMunicipalNumbers": False,
            "theoryCanOverrideAa2Terminal": False,
            "genericProseMayFillReferenceGap": False,
            "associationIsCausation": False,
            "externalResearchAuthorized": False,
        },
        "coverageSummary": {
            "supportedWithStrictTransferLimitQuestionIds": sorted(SUPPORTED_QUESTIONS),
            "identityNoMechanismReferenceRequiredQuestionIds": sorted(IDENTITY_QUESTIONS),
            "localPrimaryReferenceGapQuestionIds": sorted(GAP_QUESTIONS),
        },
        "frozenMechanismReconciliation": source_reconciliation,
        "mechanismCount": len(mechanisms),
        "mechanisms": mechanisms,
        "referenceCount": len(references),
        "references": references,
        "inputHashes": input_hashes,
        "downstreamState": "AA4_NARRATIVE_DOSSIER_INPUT_ONLY_NOT_PUBLIC",
    }
    evidence = _build_evidence_appendix(
        input_hashes=input_hashes,
        mechanisms=mechanisms,
        qa=qa,
        contract=contract,
    )
    return {
        "library": library,
        "coverage": coverage,
        "boundaries": boundaries,
        "evidence": evidence,
        "qa": qa,
        "input_hashes": input_hashes,
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
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def _artifact_set_digest(output_dir: Path) -> str:
    return _sha256_payload(_artifact_records(output_dir))


def materialize_package(
    output_dir: Path,
    *,
    external_io_guarded: bool,
    entry_public_digest: str,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=False)
    bundle = build_theory_package(expected_public_digest=entry_public_digest)
    contract = _load_json(CONTRACT_PATH)
    sentinel = contract["publicDataSentinel"]
    atomic_write_json(output_dir / LIBRARY_FILE, bundle["library"])
    write_csv_gzip(output_dir / COVERAGE_FILE, bundle["coverage"])
    atomic_write_json(output_dir / BOUNDARIES_FILE, bundle["boundaries"])
    atomic_write_json(output_dir / EVIDENCE_FILE, bundle["evidence"])
    atomic_write_json(output_dir / QA_FILE, bundle["qa"])
    artifacts = _artifact_records(output_dir)
    implementation_paths = [CONTRACT_PATH, Path(__file__).resolve(), RUNNER_PATH]
    manifest = {
        "schemaVersion": "vocacoes-pne-aa3-manifest-v1",
        "programId": "vocacoes-pne-advanced-analytics-v1",
        "stage": "AA3",
        "generatedAt": GENERATED_AT,
        "finalState": "AA3_COMPLETE_OPUS_REAUDIT_ON_TRACK",
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
            "pandas": pd.__version__,
            "pythonHashSeed": os.environ.get("PYTHONHASHSEED", "UNSET"),
        },
        "counts": bundle["qa"]["counts"],
        "publicDataIntegrity": {
            "gateRule": sentinel["gateRule"],
            "aa2HistoricalDigestSha256": sentinel["aa2HistoricalDigestSha256"],
            "candidateEntryTreeDigestSha256": entry_public_digest,
            "beforeTreeDigestSha256": entry_public_digest,
            "afterTreeDigestSha256": entry_public_digest,
            "unchanged": True,
            "notWrittenByAa3": True,
            "fixedDigestIsAnalyticalInput": False,
            "observedPriorRegionalPublicationPathCount": len(
                sentinel["observedChangedPaths"]
            ),
            "producerAttribution": sentinel["producerAttribution"],
            "subsequentExternalPublication": sentinel[
                "subsequentExternalPublication"
            ],
            "futureBaselinePolicy": sentinel["futureBaselinePolicy"],
        },
        "opusReconciliation": {
            "path": OPUS_RECONCILIATION_PATH.relative_to(REPO_ROOT).as_posix(),
            "sha256": EXPECTED_OPUS_RECONCILIATION_SHA256,
            "initialSignedState": "CORRECTIONS_ACCEPTED_PENDING_REMATERIALIZATION_AND_REAUDIT",
            "currentExecutionState": "CORRECTIONS_APPLIED_REAUDITED_ON_TRACK_EVIDENCE_APPENDIX_COMPLETE",
            "initialAa4Allowed": False,
            "aa4Allowed": True,
            "reAudit": {
                "path": OPUS_REAUDIT_PATH.relative_to(REPO_ROOT).as_posix(),
                "sha256": EXPECTED_OPUS_REAUDIT_SHA256,
                "verdict": "ON_TRACK",
                "confidence": 0.78,
                "residualEvidenceRecommendation": "APPLIED_AFTER_REAUDIT",
                "finalPackageDirectlyReaudited": False,
            },
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
    with blocked_external_io_guard():
        materialize_package(
            output_dir,
            external_io_guarded=True,
            entry_public_digest=public_before,
        )
    gc.collect()
    public_after = directory_content_digest(REPO_ROOT / "public/data")
    if public_after != public_before:
        raise TheoryLibraryValidationError(
            "public/data mudou durante a materialização candidata AA3."
        )
    loaded_roots = {name.partition(".")[0] for name in sys.modules}
    return {
        "outputDir": output_dir.resolve().as_posix(),
        "artifactSetDigestSha256": _artifact_set_digest(output_dir),
        "candidateManifestSha256": sha256_file(output_dir / MANIFEST_FILE),
        "candidateTreeDigestSha256": directory_content_digest(output_dir),
        "implementationSha256": sha256_file(Path(__file__).resolve()),
        "networkGuardEnabled": True,
        "databaseGuardEnabled": True,
        "loadedDatabaseClientModules": sorted(loaded_roots & DATABASE_CLIENT_MODULE_ROOTS),
        "loadedNetworkClientModules": sorted(loaded_roots & NETWORK_CLIENT_MODULE_ROOTS),
        "publicDataBeforeTreeDigestSha256": public_before,
        "publicDataAfterTreeDigestSha256": public_after,
    }


def _run_candidate_process(output_dir: Path, *, python_hash_seed: str) -> dict[str, Any]:
    environment = os.environ.copy()
    environment["PYTHONHASHSEED"] = python_hash_seed
    started_at_utc = datetime.now(timezone.utc).isoformat(timespec="seconds")
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
    finished_at_utc = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if completed.returncode != 0:
        raise TheoryLibraryValidationError(
            "Processo candidato AA3 falhou "
            f"(seed={python_hash_seed}, exit={completed.returncode}): "
            f"{completed.stderr.strip()}"
        )
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise TheoryLibraryValidationError(
            f"Saída candidata AA3 inválida (seed={python_hash_seed})."
        ) from error
    payload["pythonHashSeed"] = python_hash_seed
    payload["processMode"] = "FRESH_OS_PROCESS"
    payload["startedAtUtc"] = started_at_utc
    payload["finishedAtUtc"] = finished_at_utc
    return payload


def _finalize_evidence_appendix(
    output_dir: Path,
    *,
    process_evidence: Sequence[Mapping[str, Any]],
) -> None:
    path = output_dir / EVIDENCE_FILE
    evidence = _load_json(path)
    evidence["determinismEvidence"] = {
        "state": "PRE_NORMALIZATION_CANDIDATES_RECORDED",
        "processIsolation": "TWO_FRESH_OPERATING_SYSTEM_PROCESSES",
        "processCount": len(process_evidence),
        "preNormalizationCandidateManifestDigests": [
            {
                "pythonHashSeed": item["pythonHashSeed"],
                "sha256": item["candidateManifestSha256"],
            }
            for item in process_evidence
        ],
        "preNormalizationCandidateTreeDigests": [
            {
                "pythonHashSeed": item["pythonHashSeed"],
                "sha256": item["candidateTreeDigestSha256"],
            }
            for item in process_evidence
        ],
        "preNormalizationCandidateArtifactSetDigests": [
            {
                "pythonHashSeed": item["pythonHashSeed"],
                "sha256": item["candidateArtifactSetDigestSha256"],
            }
            for item in process_evidence
        ],
        "normalizedManifestFields": [
            "artifacts",
            "artifactSetDigestSha256",
            "runtime.pythonHashSeed",
            "runtime.pythonHashSeeds",
            "independentMaterializationVerification",
        ],
        "preNormalizationComparisonScope": "NON_MANIFEST_ARTIFACT_SET",
        "postNormalizationComparisonScope": "ALL_FILES_INCLUDING_MANIFEST",
        "postNormalizationFinalTreeEqualityVerifiedByParent": True,
        "finalTreeDigestLocation": "External parent-runner receipt; it cannot be embedded in the hashed tree without a self-reference cycle.",
        "gzipMtime": 0,
    }
    atomic_write_json(path, evidence)


def _finalize_determinism(
    output_dir: Path,
    digest: str,
    *,
    process_evidence: Sequence[Mapping[str, Any]],
) -> None:
    path = output_dir / MANIFEST_FILE
    manifest = _load_json(path)
    artifacts = _artifact_records(output_dir)
    recalculated_digest = _sha256_payload(artifacts)
    if recalculated_digest != digest:
        raise TheoryLibraryValidationError(
            "Digest AA3 mudou entre a finalização da evidência e do manifesto."
        )
    manifest["artifacts"] = artifacts
    manifest["artifactSetDigestSha256"] = recalculated_digest
    manifest["runtime"]["pythonHashSeed"] = "MULTI_PROCESS_FINALIZED"
    manifest["runtime"]["pythonHashSeeds"] = ["303", "404"]
    manifest["independentMaterializationVerification"] = {
        "state": "VERIFIED_IDENTICAL",
        "equal": True,
        "artifactSetDigestSha256": digest,
        "comparisonScope": "PRE_NORMALIZATION_NON_MANIFEST_AND_POST_NORMALIZATION_FULL_TREE",
        "candidateManifestEqualityRequired": False,
        "candidateManifestDifferenceReason": (
            "Cada manifesto candidato registra seu PYTHONHASHSEED operacional; "
            "o manifesto final normaliza os dois processos em evidência comum."
        ),
        "finalManifestNormalization": "MULTI_PROCESS_COMMON_EVIDENCE",
        "processIsolation": "TWO_FRESH_OPERATING_SYSTEM_PROCESSES",
        "processCount": len(process_evidence),
        "preNormalizationCandidateManifestDigests": [
            item["candidateManifestSha256"] for item in process_evidence
        ],
        "preNormalizationCandidateTreeDigests": [
            item["candidateTreeDigestSha256"] for item in process_evidence
        ],
        "normalizedManifestFields": [
            "artifacts",
            "artifactSetDigestSha256",
            "runtime.pythonHashSeed",
            "runtime.pythonHashSeeds",
            "independentMaterializationVerification",
        ],
        "postNormalizationFinalTreeEqualityVerifiedByParent": True,
        "postNormalizationComparisonScope": "ALL_FILES_INCLUDING_MANIFEST",
        "processEvidence": list(process_evidence),
    }
    atomic_write_json(path, manifest)


def _replace_directory_transactionally(staging: Path, target: Path) -> bool:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and directory_content_digest(staging) == directory_content_digest(target):
        return False
    rollback = target.with_name(f".{target.name}.rollback-aa3")
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
        raise FileNotFoundError(f"Pacote AA3 ausente: {output_dir}")
    manifest = _load_json(output_dir / MANIFEST_FILE)
    if manifest.get("artifactSetDigestSha256") != _artifact_set_digest(output_dir):
        raise TheoryLibraryValidationError("Digest do conjunto AA3 divergente.")
    if [artifact["path"] for artifact in manifest.get("artifacts", [])] != list(NON_MANIFEST_FILES):
        raise TheoryLibraryValidationError("Lista de artefatos AA3 divergente.")
    for artifact in manifest["artifacts"]:
        path = output_dir / artifact["path"]
        if path.stat().st_size != artifact["byteSize"] or sha256_file(path) != artifact["sha256"]:
            raise TheoryLibraryValidationError(f"Artefato AA3 divergente: {artifact['path']}")
    qa = _load_json(output_dir / QA_FILE)
    if qa.get("failedCount") != 0 or qa.get("counts", {}).get("questionCount") != 8:
        raise TheoryLibraryValidationError("QA_SUMMARY_AA3 contém falhas ou universo divergente.")
    library = _load_json(output_dir / LIBRARY_FILE)
    if library.get("mechanismCount") != 8 or library.get("referenceCount") != 8:
        raise TheoryLibraryValidationError("Biblioteca AA3 contém universo divergente.")
    evidence = _load_json(output_dir / EVIDENCE_FILE)
    input_items = evidence.get("inputHashItems", [])
    if (
        evidence.get("schemaVersion")
        != "vocacoes-pne-aa3-complementary-evidence-v1"
        or evidence.get("inputHashCount") != 11
        or len(input_items) != 11
        or {
            item.get("inputHashKey"): item.get("sha256OrContentDigest")
            for item in input_items
        }
        != manifest.get("inputHashes")
    ):
        raise TheoryLibraryValidationError(
            "Apêndice AA3 não comprova exatamente os onze vínculos de entrada."
        )
    ceiling_rows = evidence.get("ceilingRows", [])
    if (
        [item.get("question_id") for item in ceiling_rows] != list(QUESTION_IDS)
        or any(
            (
                item.get("aa2_claim_ceiling"),
                item.get("aa3_effective_claim_ceiling"),
            )
            != EXPECTED_CEILING_POLICY[item["question_id"]]
            or item.get("ceilingRelation")
            != "NARROWER_OR_EQUAL_BY_EXPLICIT_QUESTION_POLICY"
            or not item.get("aa4_role")
            for item in ceiling_rows
        )
        or evidence.get("ceilingPolicy", {}).get("mayWidenAa2") is not False
    ):
        raise TheoryLibraryValidationError(
            "Apêndice AA3 não preserva a relação explícita entre tetos AA2 e AA3."
        )
    if (
        len(evidence.get("reconciliationDecisionToRevisionCrosswalk", [])) != 9
        or {
            revision
            for item in evidence["reconciliationDecisionToRevisionCrosswalk"]
            for revision in item.get("revisionIds", [])
        }
        != set("ABCDEFG")
        or {
            item.get("question_id")
            for item in evidence.get("technicalSpecificitySamples", [])
        }
        != {
            "P1_CONTEXT_ADJUSTED_TRAJECTORY",
            "P4_YOUTH_WORK_AND_HIGH_SCHOOL",
            "P5_OCCUPATIONS_AND_EPT",
            "P6_ADULT_SCHOOLING_WORK_AND_EJA",
        }
        or evidence.get("qaCheckIds")
        != [check["checkId"] for check in qa.get("checks", [])]
    ):
        raise TheoryLibraryValidationError(
            "Apêndice AA3 não fecha o crosswalk, as amostras técnicas ou o QA."
        )
    verification = manifest.get("independentMaterializationVerification", {})
    if verification.get("state") != "VERIFIED_IDENTICAL" or verification.get("equal") is not True:
        raise TheoryLibraryValidationError("Pacote AA3 não comprova duas materializações idênticas.")
    if (
        manifest.get("generation", {}).get("manifestLast") is not True
        or manifest.get("publicDataIntegrity", {}).get("gateRule")
        != "PUBLIC_DATA_NOT_WRITTEN_BY_AA3_INVARIANT_WITHIN_AND_EQUAL_ACROSS_TWO_CANDIDATE_MATERIALIZATIONS"
        or manifest.get("publicDataIntegrity", {}).get("notWrittenByAa3") is not True
        or manifest.get("opusReconciliation", {}).get("sha256")
        != EXPECTED_OPUS_RECONCILIATION_SHA256
        or manifest.get("opusReconciliation", {}).get("aa4Allowed") is not True
        or manifest.get("opusReconciliation", {}).get("reAudit", {}).get(
            "sha256"
        )
        != EXPECTED_OPUS_REAUDIT_SHA256
        or manifest.get("opusReconciliation", {}).get("reAudit", {}).get(
            "verdict"
        )
        != "ON_TRACK"
        or evidence.get("opusReaudit", {}).get("recommendationState")
        != "APPLIED_AFTER_REAUDIT"
        or evidence.get("opusReaudit", {}).get("finalPackageDirectlyReaudited")
        is not False
    ):
        raise TheoryLibraryValidationError("Gate formal de reconciliação AA3 divergente.")
    publication_times = (
        manifest["publicDataIntegrity"]["producerAttribution"][
            "regionalFilesLastWriteTimeUtc"
        ],
        manifest["publicDataIntegrity"]["subsequentExternalPublication"][
            "lastWriteTimeUtc"
        ],
    )
    latest_external_write = max(
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        for value in publication_times
    )
    process_evidence = verification.get("processEvidence", [])
    if len(process_evidence) != 2 or any(
        datetime.fromisoformat(item["startedAtUtc"]) <= latest_external_write
        or datetime.fromisoformat(item["finishedAtUtc"])
        < datetime.fromisoformat(item["startedAtUtc"])
        or item["publicDataBeforeTreeDigestSha256"]
        != manifest["publicDataIntegrity"]["candidateEntryTreeDigestSha256"]
        or item["publicDataAfterTreeDigestSha256"]
        != manifest["publicDataIntegrity"]["candidateEntryTreeDigestSha256"]
        for item in process_evidence
    ):
        raise TheoryLibraryValidationError(
            "Evidência temporal ou invariância pública dos processos AA3 divergiu."
        )
    determinism_evidence = evidence.get("determinismEvidence", {})
    if (
        determinism_evidence.get("state")
        != "PRE_NORMALIZATION_CANDIDATES_RECORDED"
        or determinism_evidence.get("processCount") != 2
        or [
            item.get("sha256")
            for item in determinism_evidence.get(
                "preNormalizationCandidateManifestDigests", []
            )
        ]
        != [item.get("candidateManifestSha256") for item in process_evidence]
        or [
            item.get("sha256")
            for item in determinism_evidence.get(
                "preNormalizationCandidateTreeDigests", []
            )
        ]
        != [item.get("candidateTreeDigestSha256") for item in process_evidence]
        or determinism_evidence.get(
            "postNormalizationFinalTreeEqualityVerifiedByParent"
        )
        is not True
        or verification.get("artifactSetDigestSha256")
        != manifest.get("artifactSetDigestSha256")
        or verification.get("postNormalizationFinalTreeEqualityVerifiedByParent")
        is not True
    ):
        raise TheoryLibraryValidationError(
            "Evidência determinística complementar AA3 divergiu do manifesto."
        )
    if verify_sources:
        verify_frozen_inputs(
            expected_public_digest=manifest["publicDataIntegrity"][
                "candidateEntryTreeDigestSha256"
            ]
        )
    return manifest


def materialize_twice_transactionally(
    output_dir: Path = DEFAULT_OUTPUT_ROOT,
) -> dict[str, Any]:
    public_before = directory_content_digest(REPO_ROOT / "public/data")
    contract = _load_json(CONTRACT_PATH)
    publication_times = (
        contract["publicDataSentinel"]["producerAttribution"][
            "regionalFilesLastWriteTimeUtc"
        ],
        contract["publicDataSentinel"]["subsequentExternalPublication"][
            "lastWriteTimeUtc"
        ],
    )
    latest_external_write = max(
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        for value in publication_times
    )
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    first = Path(tempfile.mkdtemp(prefix=".aa3-first-", dir=output_dir.parent))
    second = Path(tempfile.mkdtemp(prefix=".aa3-second-", dir=output_dir.parent))
    shutil.rmtree(first)
    shutil.rmtree(second)
    try:
        first_result = _run_candidate_process(first, python_hash_seed="303")
        second_result = _run_candidate_process(second, python_hash_seed="404")
        first_digest = _artifact_set_digest(first)
        second_digest = _artifact_set_digest(second)
        if first_digest != second_digest:
            raise TheoryLibraryValidationError(
                "As duas materializações AA3 produziram conjuntos divergentes."
            )
        implementation_sha = sha256_file(Path(__file__).resolve())
        for candidate in (first_result, second_result):
            if candidate["implementationSha256"] != implementation_sha:
                raise TheoryLibraryValidationError("Processo candidato AA3 usou implementação divergente.")
            if (
                candidate["networkGuardEnabled"] is not True
                or candidate["databaseGuardEnabled"] is not True
                or candidate["loadedDatabaseClientModules"]
                or candidate["loadedNetworkClientModules"]
            ):
                raise TheoryLibraryValidationError("Processo candidato AA3 não preservou as guardas externas.")
            if (
                candidate["publicDataBeforeTreeDigestSha256"] != public_before
                or candidate["publicDataAfterTreeDigestSha256"] != public_before
            ):
                raise TheoryLibraryValidationError("Processo candidato AA3 observou public/data divergente.")
            if (
                datetime.fromisoformat(candidate["startedAtUtc"]) <= latest_external_write
                or datetime.fromisoformat(candidate["finishedAtUtc"])
                < datetime.fromisoformat(candidate["startedAtUtc"])
            ):
                raise TheoryLibraryValidationError(
                    "Processo candidato AA3 não sucede as publicações externas reconciliadas."
                )
        evidence = [
            {
                "processMode": candidate["processMode"],
                "pythonHashSeed": candidate["pythonHashSeed"],
                "startedAtUtc": candidate["startedAtUtc"],
                "finishedAtUtc": candidate["finishedAtUtc"],
                "implementationSha256": candidate["implementationSha256"],
                "candidateArtifactSetDigestSha256": candidate["artifactSetDigestSha256"],
                "candidateManifestSha256": candidate["candidateManifestSha256"],
                "candidateTreeDigestSha256": candidate["candidateTreeDigestSha256"],
                "networkGuardEnabled": candidate["networkGuardEnabled"],
                "databaseGuardEnabled": candidate["databaseGuardEnabled"],
                "loadedDatabaseClientModules": candidate["loadedDatabaseClientModules"],
                "loadedNetworkClientModules": candidate["loadedNetworkClientModules"],
                "publicDataBeforeTreeDigestSha256": candidate["publicDataBeforeTreeDigestSha256"],
                "publicDataAfterTreeDigestSha256": candidate["publicDataAfterTreeDigestSha256"],
            }
            for candidate in (first_result, second_result)
        ]
        _finalize_evidence_appendix(first, process_evidence=evidence)
        _finalize_evidence_appendix(second, process_evidence=evidence)
        first_digest = _artifact_set_digest(first)
        second_digest = _artifact_set_digest(second)
        if first_digest != second_digest:
            raise TheoryLibraryValidationError(
                "As duas evidências complementares AA3 divergiram após a reconciliação."
            )
        _finalize_determinism(first, first_digest, process_evidence=evidence)
        _finalize_determinism(second, second_digest, process_evidence=evidence)
        first_tree = directory_content_digest(first)
        second_tree = directory_content_digest(second)
        if first_tree != second_tree:
            raise TheoryLibraryValidationError(
                "As duas árvores AA3 divergiram após o manifesto final."
            )
        validate_existing_output(first, verify_sources=False)
        changed = _replace_directory_transactionally(first, output_dir)
        return {
            "outputDir": output_dir.resolve().as_posix(),
            "artifactSetDigestSha256": first_digest,
            "fullTreeDigestSha256": first_tree,
            "finalCandidateTreeDigestsSha256": [first_tree, second_tree],
            "independentMaterializationsEqual": True,
            "processIsolation": "TWO_FRESH_OPERATING_SYSTEM_PROCESSES",
            "pythonHashSeeds": ["303", "404"],
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
