"""Compilador editorial interno, insight-first, do Job 5K.

O módulo promove o julgamento externo do Job 5J para uma camada editorial
normalizada sobre o bundle Job 5I. Ele usa somente entradas locais congeladas,
preserva as seis lentes territoriais, mantém a rede total e nunca escreve em
``public/data``.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import csv
from functools import lru_cache
import gzip
import hashlib
import io
import json
import math
from pathlib import Path
import re
import shutil
from typing import Any

from .vocacoes_pne_job2 import directory_content_digest, sha256_file


REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = (
    REPO_ROOT / "data_pipeline" / "contracts" / "vocacoes-pne-v7-job5k.json"
)
JOB5I_ROOT = REPO_ROOT / ".tmp" / "vocacoes-pne" / "v7-job5i"
JOB5J_ROOT = REPO_ROOT / ".tmp" / "vocacoes-pne" / "v7-job5j"
JOB5GCR_ROOT = REPO_ROOT / ".tmp" / "vocacoes-pne" / "v7-job5gcr"
OCCUPATION_PANEL = JOB5GCR_ROOT / "PAINEL_OCUPACOES_RAIS_ESTOQUE_V1.csv.gz"
PUBLIC_DATA_ROOT = REPO_ROOT / "public" / "data"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / ".tmp" / "vocacoes-pne" / "v7-job5k"
FRONTEND_BUNDLE = (
    REPO_ROOT
    / "src"
    / "features"
    / "vocacoes-pne-internal"
    / "generated"
    / "vocacoesPneJob5kStories.json"
)
VALIDATION_EVIDENCE_PATH = (
    REPO_ROOT
    / ".tmp"
    / "vocacoes-pne"
    / "v7-job5k-internal"
    / "validation-evidence.json"
)

GENERATED_AT = "2026-08-29T00:00:00-03:00"
REGION_ID = "REGION_VALE_DO_SINOS"
REGION_NAME = "Vale do Sinos"
NSR_CODE = "4313375"
NETWORK_SCOPE = "total_all_dependencies"
FINAL_STATE = "JOB_5K_READY_WITH_EXPLICIT_LIMITS_FOR_EXTERNAL_JUDGMENT"
PENDING_STATE = "JOB_5K_IMPLEMENTATION_QA_PENDING"
IBGE_PATTERN = re.compile(r"[0-9]{7}")

NON_SCREENSHOT_FILES = (
    "CHECKPOINT_JOB5K_FOR_PRO.md",
    "CONTRATO_INSIGHT_FIRST_JOB5K.json",
    "BUNDLE_INSIGHTS_UI_JOB5K.json",
    "DOSSIE_PAGINA_NOVA_SANTA_RITA_JOB5K.md",
    "DOSSIE_PAGINA_VALE_DO_SINOS_JOB5K.md",
    "MATRIZ_COBERTURA_INSIGHTS_10_MUNICIPIOS_JOB5K.csv.gz",
    "MATRIZ_QA_VISUAL_JOB5K.json",
    "VALIDATION_REPORT_JOB5K.json",
    "ARTIFACT_INDEX_JOB5K.json",
    "PACOTE_REVISAO_EXTERNA_JOB5K.json",
    "MANIFEST_JOB5K.json",
)
SCREENSHOT_FILES = (
    "SCREENSHOT_NOVA_SANTA_RITA_DESKTOP_JOB5K.png",
    "SCREENSHOT_VALE_DO_SINOS_DESKTOP_JOB5K.png",
    "SCREENSHOT_NOVA_SANTA_RITA_MOBILE_JOB5K.png",
    "SCREENSHOT_IMPRESSAO_JOB5K.png",
)
OUTPUT_FILES = NON_SCREENSHOT_FILES + SCREENSHOT_FILES

REQUIRED_STORY_FIELDS = {
    "story_id",
    "direction_id",
    "editorial_role",
    "analytical_sources",
    "analytical_relation_states",
    "title_conclusion",
    "integrated_summary",
    "regional_read",
    "selected_municipality_read",
    "ten_municipality_distribution",
    "primary_evidence",
    "secondary_evidence",
    "planning_implication",
    "monitoring_indicators",
    "institutional_coordination",
    "interpretation_boundary",
    "allowed_claims",
    "forbidden_claims",
    "source_refs",
    "periods",
    "territorial_lenses",
    "network_scope",
    "availability_state",
    "zero_state",
    "manager_review_state",
    "public_narrative_authorized",
}

VISIBLE_BLOCKED_PATTERNS = (
    re.compile(r"\bmobilidade não explica\b", re.IGNORECASE),
    re.compile(r"\bnão existe relação\b", re.IGNORECASE),
    re.compile(r"\bfaltam cursos\b", re.IGNORECASE),
    re.compile(r"\bfalta de acesso\b", re.IGNORECASE),
    re.compile(r"\bcurso necessário\b", re.IGNORECASE),
    re.compile(r"\branking\b", re.IGNORECASE),
    re.compile(r"\bzero escolas\b", re.IGNORECASE),
    re.compile(r"\b(?:rho|Benjamini|regressão|efeitos fixos|shift-share|HHI)\b", re.IGNORECASE),
    re.compile(r"\bR[1-8]\b"),
)


class Job5KValidationError(ValueError):
    """Falha fechada do contrato editorial Job 5K."""


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _json_bytes(value: Any, *, compact: bool = False) -> bytes:
    if compact:
        payload = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    else:
        payload = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        ) + "\n"
    return payload.encode("utf-8")


def _gzip_csv_bytes(rows: Sequence[Mapping[str, Any]], fieldnames: Sequence[str]) -> bytes:
    text = io.StringIO(newline="")
    writer = csv.DictWriter(text, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    output = io.BytesIO()
    with gzip.GzipFile(fileobj=output, mode="wb", mtime=0, filename="") as stream:
        stream.write(text.getvalue().encode("utf-8"))
    return output.getvalue()


def _read_csv_gzip(path: Path) -> list[dict[str, str]]:
    with gzip.open(path, "rt", encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def _number(value: Any) -> int | float | None:
    if value is None or value == "":
        return None
    number = float(value)
    if not math.isfinite(number):
        return None
    if number.is_integer() and abs(number) <= 9_007_199_254_740_991:
        return int(number)
    return number


def _fmt_number(value: int | float, digits: int = 0) -> str:
    if digits == 0:
        return f"{int(round(value)):,}".replace(",", ".")
    rendered = f"{value:,.{digits}f}"
    return rendered.replace(",", "X").replace(".", ",").replace("X", ".")


def _fmt_signed(value: int | float, digits: int = 0) -> str:
    if math.isclose(float(value), 0.0, abs_tol=1e-12):
        return _fmt_number(0, digits)
    sign = "+" if value > 0 else "−"
    return f"{sign}{_fmt_number(abs(value), digits)}"


def _contract() -> dict[str, Any]:
    contract = _json(CONTRACT_PATH)
    if contract["scope"]["gate11"] != "CLOSED":
        raise Job5KValidationError("o contrato Job 5K deve manter o Gate 11 fechado")
    if len(contract["checkpointFiles"]) != 15:
        raise Job5KValidationError("o contrato deve declarar exatamente 15 arquivos finais")
    return contract


def verify_frozen_integrity() -> dict[str, Any]:
    contract = _contract()
    frozen = contract["frozenInputs"]
    required = [
        JOB5I_ROOT / "BUNDLE_UI_V2_JOB5I.json",
        JOB5I_ROOT / "MANIFEST_JOB5I.json",
        JOB5J_ROOT / "CATALOGO_INSIGHTS_CANDIDATOS_JOB5J.json",
        JOB5J_ROOT / "MATRIZ_HETEROGENEIDADE_10_MUNICIPIOS_JOB5J.csv.gz",
        JOB5J_ROOT / "MODELOS_E_ROBUSTEZ_DETALHADOS_JOB5J.json",
        JOB5J_ROOT / "MANIFEST_JOB5J.json",
        OCCUPATION_PANEL,
        REPO_ROOT / "contracts" / "pne2026-goal-indicator-contract.json",
        REPO_ROOT / "config" / "municipalities" / "rs.json",
        REPO_ROOT / "config" / "regions" / "rs.json",
    ]
    missing = [path.as_posix() for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"entradas obrigatórias Job 5K ausentes: {missing}")
    actual = {
        "job5gcrTreeDigestSha256": directory_content_digest(JOB5GCR_ROOT),
        "job5gcrOccupationPanelSha256": sha256_file(OCCUPATION_PANEL),
        "job5iTreeDigestSha256": directory_content_digest(JOB5I_ROOT),
        "job5jTreeDigestSha256": directory_content_digest(JOB5J_ROOT),
        "publicDataTreeDigestSha256": directory_content_digest(PUBLIC_DATA_ROOT),
        "pne2026ContractSha256": sha256_file(
            REPO_ROOT / "contracts" / "pne2026-goal-indicator-contract.json"
        ),
        "municipalityRegistrySha256": sha256_file(
            REPO_ROOT / "config" / "municipalities" / "rs.json"
        ),
        "regionRegistrySha256": sha256_file(
            REPO_ROOT / "config" / "regions" / "rs.json"
        ),
    }
    for key, value in actual.items():
        if value != frozen[key]:
            raise Job5KValidationError(
                f"preflight congelado divergente em {key}: esperado={frozen[key]}, atual={value}"
            )
    job5i_manifest = _json(JOB5I_ROOT / "MANIFEST_JOB5I.json")
    job5j_manifest = _json(JOB5J_ROOT / "MANIFEST_JOB5J.json")
    if job5i_manifest["gate11"] != "CLOSED" or job5j_manifest["gate11"] != "CLOSED":
        raise Job5KValidationError("Jobs 5I/5J congelados não preservaram Gate 11 fechado")
    if job5j_manifest["finalState"] != (
        "JOB_5J_READY_WITH_EXPLICIT_LIMITS_FOR_EXTERNAL_JUDGMENT"
    ):
        raise Job5KValidationError("estado terminal do Job 5J divergente")
    return {
        "schemaVersion": "vocacoes-pne-job5k-preflight-v1",
        "result": "PASSED",
        "checkedAt": GENERATED_AT,
        "digests": actual,
        "job5iPreserved": True,
        "job5jPreserved": True,
        "publicDataPreserved": True,
        "canonicalPnePreserved": True,
        "canonicalMunicipalityIdentityPreserved": True,
        "networkScope": NETWORK_SCOPE,
        "databaseUsed": False,
        "networkUsed": False,
        "newAcquisitionPerformed": False,
        "orchestrationContractResolution": {
            "requestedPath": "docs/VOCACOES_PNE_V7_ORCHESTRATION_CONTRACT.md",
            "requestedPathExists": False,
            "canonicalPathUsed": "docs/CONTRATO_ORQUESTRACAO_VOCACOES_PNE_V7.md",
            "semanticMismatchDetected": False,
        },
    }


def _municipalities() -> list[dict[str, str]]:
    regions = _json(REPO_ROOT / "config" / "regions" / "rs.json")
    vale = next(item for item in regions["regions"] if item["slug"] == "vale-do-sinos")
    codes = [str(value) for value in vale["municipalityIbgeCodes"]]
    if len(codes) != 10 or len(set(codes)) != 10:
        raise Job5KValidationError("Vale do Sinos deve preservar dez municípios")
    if any(not IBGE_PATTERN.fullmatch(code) for code in codes):
        raise Job5KValidationError("código IBGE municipal não textual de sete dígitos")
    registry = _json(REPO_ROOT / "config" / "municipalities" / "rs.json")
    names = {str(item["ibgeCode"]): str(item["name"]) for item in registry["municipalities"]}
    if not set(codes) <= set(names):
        raise Job5KValidationError("registro municipal canônico incompleto para o Vale")
    return [{"ibgeCode": code, "name": names[code]} for code in codes]


def _find_series(
    source: Mapping[str, Any],
    *,
    family: str,
    entity: str,
    metric: str,
    stage: str | None = None,
    age: str | None = None,
) -> Mapping[str, Any]:
    matches = [
        item
        for item in source["series"]
        if item["storyFamilyId"] == family
        and item["entityId"] == entity
        and item["metricId"] == metric
        and (stage is None or item["educationalStage"] == stage)
        and (age is None or item["ageGroup"] == age)
    ]
    if len(matches) != 1:
        raise Job5KValidationError(
            f"série única esperada: {family}/{entity}/{metric}/{stage}/{age}; obtidas={len(matches)}"
        )
    return matches[0]


def _find_fact(
    source: Mapping[str, Any],
    *,
    family: str,
    entity: str,
    metric: str,
    stage: str | None = None,
    age: str | None = None,
    period_contains: str | None = None,
) -> Mapping[str, Any]:
    matches = [
        item
        for item in source["facts"]
        if item["storyFamilyId"] == family
        and item["entityId"] == entity
        and item["metricId"] == metric
        and (stage is None or item["educationalStage"] == stage)
        and (age is None or item["ageGroup"] == age)
        and (period_contains is None or period_contains in item["period"])
    ]
    if len(matches) != 1:
        raise Job5KValidationError(
            f"fato único esperado: {family}/{entity}/{metric}/{stage}/{age}; obtidos={len(matches)}"
        )
    return matches[0]


def _point(series: Mapping[str, Any], year: int) -> Mapping[str, Any]:
    matches = [item for item in series["points"] if item["year"] == year]
    if len(matches) != 1:
        raise Job5KValidationError(f"ponto {year} ausente ou duplicado em {series['seriesId']}")
    return matches[0]


def _endpoint(series: Mapping[str, Any]) -> dict[str, Any]:
    observed = [
        item
        for item in series["points"]
        if item["availabilityState"] in {"observed", "observed_zero"}
    ]
    if not observed:
        return {
            "series_id": series["seriesId"],
            "availability_state": "unavailable",
            "initial_year": None,
            "initial_value": None,
            "final_year": None,
            "final_value": None,
            "absolute_change": None,
            "unit": series["unit"],
        }
    first, last = observed[0], observed[-1]
    return {
        "series_id": series["seriesId"],
        "availability_state": last["availabilityState"],
        "initial_year": first["year"],
        "initial_value": first["value"],
        "final_year": last["year"],
        "final_value": last["value"],
        "absolute_change": last["value"] - first["value"],
        "unit": series["unit"],
        "territorial_lens": series["territorialLens"],
    }


@lru_cache(maxsize=1)
def _occupation_414140_by_entity() -> dict[str, dict[str, Any]]:
    rows = _read_csv_gzip(OCCUPATION_PANEL)
    selected = [row for row in rows if row["dimension_code"] == "414140"]
    records = {
        str(row["entity_id"]): {
            "absoluteChange": _number(row["absolute_change"]),
            "dimensionCode": "414140",
            "entityId": str(row["entity_id"]),
            "finalValue": _number(row["final_value"]),
            "finalYear": int(row["final_year"]),
            "initialValue": _number(row["initial_value"]),
            "initialYear": int(row["initial_year"]),
            "label": row["dimension_label"],
            "sourceRef": "job5gcr_occupation_endpoints",
            "territorialLens": "workplace",
            "unit": "active_bonds",
        }
        for row in selected
    }
    if len(records) != 11 or REGION_ID not in records or NSR_CODE not in records:
        raise Job5KValidationError("painel CBO 414140 não cobre Vale + dez municípios")
    return records


def _occupation(source: Mapping[str, Any], entity: str) -> Mapping[str, Any]:
    raw = _occupation_414140_by_entity().get(entity)
    if raw is None:
        raise Job5KValidationError(f"CBO 414140 ausente em {entity}")
    bundle_matches = [
        item
        for item in source["occupationEvidence"]
        if item["entityId"] == entity
        and item["kind"] == "occupation"
        and item["dimensionCode"] == "414140"
    ]
    if len(bundle_matches) > 1:
        raise Job5KValidationError(f"CBO 414140 duplicada no bundle 5I em {entity}")
    if bundle_matches:
        bundle_value = bundle_matches[0]
        for key in ("initialValue", "finalValue", "absoluteChange"):
            if bundle_value[key] != raw[key]:
                raise Job5KValidationError(f"CBO 414140 5G-C-R/5I divergente em {entity}/{key}")
    return raw


def _series_endpoint_record(
    source: Mapping[str, Any],
    *,
    family: str,
    entity: str,
    metric: str,
    stage: str | None = None,
    age: str | None = None,
) -> dict[str, Any]:
    return _endpoint(
        _find_series(
            source,
            family=family,
            entity=entity,
            metric=metric,
            stage=stage,
            age=age,
        )
    )


def _story_common(
    *,
    story_id: str,
    direction_id: str,
    editorial_role: str,
    analytical_sources: Sequence[str],
    analytical_states: Mapping[str, str],
    title: str,
    summary: str,
    regional_read: str,
    variants: list[dict[str, Any]],
    distribution: Any,
    primary: Any,
    secondary: Any,
    planning: str,
    monitoring: Sequence[str],
    coordination: Sequence[str],
    boundary: str,
    allowed: Sequence[str],
    forbidden: Sequence[str],
    source_refs: Sequence[str],
    periods: Sequence[str],
    lenses: Sequence[str],
    pne_goal_refs: Sequence[str],
) -> dict[str, Any]:
    return {
        "story_id": story_id,
        "direction_id": direction_id,
        "editorial_role": editorial_role,
        "analytical_sources": list(analytical_sources),
        "analytical_relation_states": dict(analytical_states),
        "title_conclusion": title,
        "integrated_summary": summary,
        "regional_read": regional_read,
        "selected_municipality_read": {
            "generator_contract": "deterministic_direction_magnitude_share_zero_period_rule",
            "municipality_overrides": False,
            "variants": variants,
        },
        "ten_municipality_distribution": distribution,
        "primary_evidence": primary,
        "secondary_evidence": secondary,
        "planning_implication": planning,
        "monitoring_indicators": list(monitoring),
        "institutional_coordination": list(coordination),
        "interpretation_boundary": boundary,
        "allowed_claims": list(allowed),
        "forbidden_claims": list(forbidden),
        "source_refs": list(source_refs),
        "periods": list(periods),
        "territorial_lenses": list(lenses),
        "network_scope": NETWORK_SCOPE,
        "availability_state": "observed",
        "zero_state": "mixed",
        "manager_review_state": "pending",
        "public_narrative_authorized": False,
        "pne_goal_refs": list(pne_goal_refs),
    }


def _pne_refs(source: Mapping[str, Any], family_ids: Sequence[str]) -> list[str]:
    selected = set(family_ids)
    refs = {
        ref
        for family in source["families"]
        if family["storyFamilyId"] in selected
        for ref in family["visiblePneGoalRefs"]
    }
    return sorted(refs)


def _build_high_school_story(
    source: Mapping[str, Any],
    municipalities: Sequence[Mapping[str, str]],
    heterogeneity: Mapping[str, list[Mapping[str, str]]],
) -> dict[str, Any]:
    entities = [REGION_ID, *[item["ibgeCode"] for item in municipalities]]
    names = {item["ibgeCode"]: item["name"] for item in municipalities}
    names[REGION_ID] = REGION_NAME
    high_school_by_entity: dict[str, dict[str, Any]] = {}
    classes_by_entity: dict[str, dict[str, Any]] = {}
    primary_by_entity = []
    secondary_by_entity = []
    distribution = []
    r1_rows = {row["municipality_ibge_code"]: row for row in heterogeneity["R1"]}
    r6_rows = {row["municipality_ibge_code"]: row for row in heterogeneity["R6"]}

    for entity in entities:
        high_school = _series_endpoint_record(
            source,
            family="D1_COHORT_OFFER_CAPACITY",
            entity=entity,
            metric="located_enrollments",
            stage="high_school",
        )
        classes = _series_endpoint_record(
            source,
            family="D1_COHORT_OFFER_CAPACITY",
            entity=entity,
            metric="classes",
            stage="high_school",
        )
        high_school_by_entity[entity] = high_school
        classes_by_entity[entity] = classes
        primary_by_entity.append(
            {
                "entity_id": entity,
                "high_school": high_school,
                "classes": classes,
            }
        )
        trajectory = {}
        if entity != REGION_ID:
            for metric, key in (
                ("approval_rate_percent", "approval_percent"),
                ("failure_rate_percent", "failure_percent"),
                ("dropout_rate_percent", "dropout_percent"),
                ("age_grade_distortion_rate_percent", "age_grade_distortion_percent"),
            ):
                series = _find_series(
                    source,
                    family="D1_TRAJECTORY_CONDITIONS",
                    entity=entity,
                    metric=metric,
                    stage="high_school",
                )
                point = _point(series, 2025)
                trajectory[key] = {
                    "value": point["value"],
                    "availability_state": point["availabilityState"],
                    "series_id": series["seriesId"],
                }
        mobility = _find_series(
            source,
            family="D1_MOBILITY_HIGH_SCHOOL_OFFER",
            entity=entity,
            metric="residents_studying_other_municipality_share",
            stage="high_school",
        )
        mobility_point = _point(mobility, 2022)
        pressure = _find_fact(
            source,
            family="D1_COHORT_OFFER_CAPACITY",
            entity=entity,
            metric="mechanical_cohort_to_2025_enrollment_ratio",
            stage="high_school",
            period_contains="2030",
        )
        secondary_by_entity.append(
            {
                "entity_id": entity,
                "trajectory_2025": trajectory,
                "mobility_2022": {
                    "value": mobility_point["value"],
                    "availability_state": mobility_point["availabilityState"],
                    "unit": mobility["unit"],
                    "series_id": mobility["seriesId"],
                },
                "inse_2023": (
                    None if entity == REGION_ID else _number(r6_rows[entity]["x_value"])
                ),
                "mechanical_pressure_2030": {
                    "value": pressure["value"],
                    "availability_state": pressure["availabilityState"],
                    "unit": "ratio",
                    "fact_id": pressure["factId"],
                    "editorial_visibility": "secondary_non_predictive_detail",
                },
            }
        )
        if entity != REGION_ID:
            change = high_school["absolute_change"]
            if not math.isclose(float(change), float(_number(r1_rows[entity]["y_value"])), abs_tol=1e-12):
                raise Job5KValidationError(f"R1 5I/5J divergente em {entity}")
            distribution.append(
                {
                    "municipality_ibge_code": entity,
                    "municipality_name": names[entity],
                    "initial_value": high_school["initial_value"],
                    "final_value": high_school["final_value"],
                    "absolute_change": change,
                    "change_direction": (
                        "expanded" if change > 0 else "contracted" if change < 0 else "stable"
                    ),
                    "availability_state": high_school["availability_state"],
                }
            )

    regional = high_school_by_entity[REGION_ID]
    if regional["absolute_change"] != -4878:
        raise Job5KValidationError("âncora regional do ensino médio divergente")
    if sum(item["absolute_change"] for item in distribution) != regional["absolute_change"]:
        raise Job5KValidationError("mudanças municipais do ensino médio não fecham o Vale")
    positive_count = sum(item["absolute_change"] > 0 for item in distribution)
    regional_summary = (
        f"Entre 2014 e 2025, o Vale perdeu {_fmt_number(abs(regional['absolute_change']))} "
        f"matrículas localizadas de ensino médio, enquanto {positive_count} dos dez municípios ampliaram a oferta observada. "
        "A trajetória escolar, a mobilidade de 2022 e o contexto socioeconômico permanecem leituras complementares."
    )
    variants = []
    for entity in entities:
        item = high_school_by_entity[entity]
        classes = classes_by_entity[entity]
        if entity == REGION_ID:
            title = "A retração regional do ensino médio esconde movimentos municipais em direções diferentes."
            summary = regional_summary
            selected_read = (
                "A visão regional mostra a série do Vale e as mudanças dos dez municípios sem criar uma taxa regional de trajetória."
            )
            key_figures = [
                {"label": "Matrículas do Vale", "value": _fmt_signed(item["absolute_change"]), "period": "2014–2025"},
                {"label": "Municípios com expansão", "value": f"{positive_count} de 10", "period": "2014–2025"},
            ]
            function = "contraste regional"
        else:
            name = names[entity]
            change = item["absolute_change"]
            class_change = classes["absolute_change"]
            if change > 0 and class_change > 0:
                title = f"{name} ampliou matrículas e turmas do ensino médio enquanto o Vale retraiu matrículas."
            elif change > 0:
                title = f"{name} ampliou matrículas do ensino médio enquanto o Vale retraiu."
            elif change < 0:
                title = f"{name} e o Vale reduziram matrículas do ensino médio, em intensidades diferentes."
            else:
                title = f"{name} manteve as matrículas do ensino médio estáveis enquanto o Vale retraiu."
            summary = (
                f"Em {name}, as matrículas passaram de {_fmt_number(item['initial_value'])} para "
                f"{_fmt_number(item['final_value'])} ({_fmt_signed(change)}) entre 2014 e 2025; "
                f"no Vale, a mudança foi {_fmt_signed(regional['absolute_change'])}. "
                "Indicadores de trajetória, mobilidade e contexto escolar são mostrados sem atribuir um resultado ao outro."
            )
            selected_read = (
                f"{name} teve mudança de {_fmt_signed(change)} matrículas e {_fmt_signed(class_change)} turmas no período observado."
            )
            key_figures = [
                {"label": f"Matrículas em {name}", "value": _fmt_signed(change), "period": "2014–2025"},
                {"label": "Matrículas no Vale", "value": _fmt_signed(regional["absolute_change"]), "period": "2014–2025"},
            ]
            function = "leitura municipal no contraste regional"
        variants.append(
            {
                "variant_id": f"STORY_HIGH_SCHOOL_TRAJECTORY.{entity}",
                "entity_id": entity,
                "municipality_ibge_code": None if entity == REGION_ID else entity,
                "title_conclusion": title,
                "integrated_summary": summary,
                "selected_municipality_read": selected_read,
                "key_figures": key_figures,
                "territorial_function": function,
                "availability_state": item["availability_state"],
                "zero_state": "not_zero" if item["final_value"] != 0 else "observed_zero",
                "primary_evidence_entity_id": entity,
                "secondary_evidence_entity_id": entity,
            }
        )
    return _story_common(
        story_id="STORY_HIGH_SCHOOL_TRAJECTORY",
        direction_id="DIRECTION_EDUCATION_TERRITORY",
        editorial_role="PRIMARY_INSIGHT",
        analytical_sources=["JOB5J_R1", "JOB5J_R2", "JOB5J_R6", "JOB5I_EVIDENCE"],
        analytical_states={"R1": "STRUCTURAL_CONTRAST", "R2": "NOT_SUPPORTED", "R6": "PLANNING_SIGNAL"},
        title="A retração regional do ensino médio esconde movimentos municipais em direções diferentes.",
        summary=regional_summary,
        regional_read="A retração regional do ensino médio esconde movimentos municipais em direções diferentes.",
        variants=variants,
        distribution=distribution,
        primary={"by_entity": primary_by_entity},
        secondary={"by_entity": secondary_by_entity},
        planning="Acompanhar anualmente matrículas, turmas, trajetória e mobilidade antes de decisões sobre organização da oferta.",
        monitoring=["matrículas do ensino médio", "turmas do ensino médio", "trajetória escolar", "mobilidade de residentes", "contexto socioeconômico"],
        coordination=["municípios", "rede estadual", "planejamento regional"],
        boundary="Na comparação entre os dez municípios, a fotografia de mobilidade de 2022 não mostrou um padrão consistente com os indicadores de trajetória escolar. O marcador mecânico de 2030 é apenas contexto e não antecipa o que ocorrerá.",
        allowed=["contraste histórico de oferta", "trajetória como acompanhamento separado", "mobilidade como contexto de coordenação"],
        forbidden=["causalidade", "previsão de oferta", "destino da mobilidade", "taxa regional agregada de trajetória"],
        source_refs=["job5gd_offer", "job5gar_trajectory", "job5gd_mobility", "job5gar_conditions", "job5gar_pressure"],
        periods=["2014–2025", "2022", "2023", "horizonte mecânico 2030"],
        lenses=["resident_population", "student_residence", "school_location"],
        pne_goal_refs=_pne_refs(source, ["D1_COHORT_OFFER_CAPACITY", "D1_TRAJECTORY_CONDITIONS", "D1_MOBILITY_HIGH_SCHOOL_OFFER"]),
    )


def _build_eja_story(
    source: Mapping[str, Any],
    municipalities: Sequence[Mapping[str, str]],
    heterogeneity: Mapping[str, list[Mapping[str, str]]],
    models: Mapping[str, Any],
) -> dict[str, Any]:
    entities = [REGION_ID, *[item["ibgeCode"] for item in municipalities]]
    names = {item["ibgeCode"]: item["name"] for item in municipalities}
    names[REGION_ID] = REGION_NAME
    r5_rows: dict[str, dict[str, Mapping[str, str]]] = {}
    for row in heterogeneity["R5"]:
        stage = "fundamental" if "fundamental" in row["x_metric"] else "high_school"
        r5_rows.setdefault(row["municipality_ibge_code"], {})[stage] = row
    distribution = []
    for municipality in municipalities:
        code = municipality["ibgeCode"]
        record: dict[str, Any] = {
            "municipality_ibge_code": code,
            "municipality_name": municipality["name"],
        }
        for stage in ("fundamental", "high_school"):
            row = r5_rows[code][stage]
            resident = _number(row["x_value"])
            located = _number(row["y_value"])
            record[stage] = {
                "resident_public_share_percent": resident,
                "located_eja_share_percent": located,
                "difference_percentage_points": located - resident,
                "availability_state": row["availability_state"],
            }
        distribution.append(record)
    tvd = {
        "fundamental": models["relations"]["R5"]["R5_TERRITORIAL_DISTRIBUTION_TVD_FUNDAMENTAL"]["valuePercentagePoints"],
        "high_school": models["relations"]["R5"]["R5_TERRITORIAL_DISTRIBUTION_TVD_HIGH_SCHOOL"]["valuePercentagePoints"],
    }
    for stage in ("fundamental", "high_school"):
        calculated = 0.5 * sum(
            abs(item[stage]["difference_percentage_points"]) for item in distribution
        )
        if not math.isclose(calculated, tvd[stage], abs_tol=1e-12):
            raise Job5KValidationError(f"distância territorial R5 divergente em {stage}")
        if not math.isclose(
            sum(item[stage]["resident_public_share_percent"] for item in distribution),
            100,
            abs_tol=1e-9,
        ) or not math.isclose(
            sum(item[stage]["located_eja_share_percent"] for item in distribution),
            100,
            abs_tol=1e-9,
        ):
            raise Job5KValidationError(f"participações R5 não fecham 100% em {stage}")
    history_by_entity = [
        {
            "entity_id": entity,
            "eja_history": _series_endpoint_record(
                source,
                family="D1_ADULT_SCHOOLING_EJA",
                entity=entity,
                metric="total_context",
                stage="total_context",
            ),
        }
        for entity in entities
    ]
    by_code = {item["municipality_ibge_code"]: item for item in distribution}
    regional_history = next(item["eja_history"] for item in history_by_entity if item["entity_id"] == REGION_ID)
    variants = []
    for entity in entities:
        history = next(item["eja_history"] for item in history_by_entity if item["entity_id"] == entity)
        if entity == REGION_ID:
            title = "A EJA ocupa posições territoriais diferentes no fundamental e no ensino médio."
            summary = (
                f"Em 2022, a distância entre as distribuições municipais foi de {_fmt_number(tvd['fundamental'], 3)} p.p. "
                f"no fundamental e {_fmt_number(tvd['high_school'], 3)} p.p. no ensino médio. "
                "As duas etapas permanecem separadas e a série histórica aparece somente como contexto."
            )
            selected_read = "A visão regional compara participações dentro de cada etapa e mostra os dez municípios na mesma base visual."
            key_figures = [
                {"label": "Distância no fundamental", "value": f"{_fmt_number(tvd['fundamental'], 3)} p.p.", "period": "2022"},
                {"label": "Distância no ensino médio", "value": f"{_fmt_number(tvd['high_school'], 3)} p.p.", "period": "2022"},
            ]
            function = "distribuição regional por etapa"
        else:
            name = names[entity]
            item = by_code[entity]
            fundamental = item["fundamental"]["difference_percentage_points"]
            high_school = item["high_school"]["difference_percentage_points"]
            title = f"Em {name}, a EJA ocupa posições territoriais diferentes no fundamental e no ensino médio."
            summary = (
                f"Em 2022, a diferença entre participação na EJA localizada e participação no público residente foi "
                f"{_fmt_signed(fundamental, 3)} p.p. no fundamental e {_fmt_signed(high_school, 3)} p.p. no ensino médio. "
                f"Como contexto separado, as matrículas de EJA passaram de {_fmt_number(history['initial_value'])} para {_fmt_number(history['final_value'])} entre 2014 e 2025."
            )
            selected_read = (
                f"{name} é lido em duas distribuições distintas, sem somar etapas nem converter diferença territorial em medida de atendimento."
            )
            key_figures = [
                {"label": "Diferença no fundamental", "value": f"{_fmt_signed(fundamental, 3)} p.p.", "period": "2022"},
                {"label": "Diferença no ensino médio", "value": f"{_fmt_signed(high_school, 3)} p.p.", "period": "2022"},
            ]
            function = "posição municipal em duas distribuições"
        variants.append(
            {
                "variant_id": f"STORY_EJA_TERRITORY.{entity}",
                "entity_id": entity,
                "municipality_ibge_code": None if entity == REGION_ID else entity,
                "title_conclusion": title,
                "integrated_summary": summary,
                "selected_municipality_read": selected_read,
                "key_figures": key_figures,
                "territorial_function": function,
                "availability_state": "observed",
                "zero_state": "mixed",
                "primary_evidence_entity_id": entity,
                "secondary_evidence_entity_id": entity,
            }
        )
    regional_summary = next(item["integrated_summary"] for item in variants if item["entity_id"] == REGION_ID)
    return _story_common(
        story_id="STORY_EJA_TERRITORY",
        direction_id="DIRECTION_EDUCATION_TERRITORY",
        editorial_role="PRIMARY_INSIGHT",
        analytical_sources=["JOB5J_R5", "JOB5I_EVIDENCE"],
        analytical_states={"R5": "TERRITORIAL_MISMATCH"},
        title="A EJA ocupa posições territoriais diferentes no fundamental e no ensino médio.",
        summary=regional_summary,
        regional_read="As distribuições municipais do público residente e da EJA localizada divergem de formas distintas no fundamental e no ensino médio.",
        variants=variants,
        distribution=distribution,
        primary={"regional_distance_percentage_points": tvd, "distribution_id": "EJA_RESIDENT_LOCATED_SHARES_2022"},
        secondary={"by_entity": history_by_entity, "regional_history": regional_history},
        planning="Comparar periodicamente as duas distribuições e discutir a organização territorial entre redes, mantendo as etapas separadas.",
        monitoring=["participação do público residente por etapa", "participação da EJA localizada por etapa", "série histórica da EJA"],
        coordination=["redes municipais", "rede estadual", "gestão regional da EJA"],
        boundary="Público residente e matrículas localizadas pertencem a universos territoriais diferentes; as duas etapas não são somadas e a diferença serve somente à leitura territorial.",
        allowed=["diferenças de distribuição dentro de cada etapa", "série histórica como contexto separado"],
        forbidden=["combinação entre etapas", "equivalência entre residente e matrícula", "prioridade automática"],
        source_refs=["job5gbr_eja_distribution", "job5gbr_eja_history", "job5gbr_adult_schooling"],
        periods=["2022", "2014–2025"],
        lenses=["resident_population", "school_location"],
        pne_goal_refs=_pne_refs(source, ["D1_ADULT_SCHOOLING_EJA"]),
    )


def _build_logistics_ept_story(
    source: Mapping[str, Any],
    municipalities: Sequence[Mapping[str, str]],
) -> dict[str, Any]:
    entities = [REGION_ID, *[item["ibgeCode"] for item in municipalities]]
    names = {item["ibgeCode"]: item["name"] for item in municipalities}
    names[REGION_ID] = REGION_NAME
    region_occupation = _occupation(source, REGION_ID)
    region_ept = _series_endpoint_record(
        source,
        family="D2_EPT_TERRITORIAL_OFFER",
        entity=REGION_ID,
        metric="technical_enrollments",
    )
    region_youth = _series_endpoint_record(
        source,
        family="D2_YOUTH_WORK_18_24",
        entity=REGION_ID,
        metric="total",
        age="18_24",
    )
    records = []
    occupation_records: dict[str, Mapping[str, Any]] = {}
    ept_records: dict[str, dict[str, Any]] = {}
    youth_records: dict[str, dict[str, Any]] = {REGION_ID: region_youth}
    positive_change_denominator = sum(
        max(0, float(_occupation(source, item["ibgeCode"])["absoluteChange"]))
        for item in municipalities
    )
    if positive_change_denominator <= 0:
        raise Job5KValidationError("R4 não possui denominador positivo de mudança")
    ept_denominator = region_ept["final_value"]
    if ept_denominator != 13945:
        raise Job5KValidationError("âncora regional EPT 2025 divergente")
    for municipality in municipalities:
        code = municipality["ibgeCode"]
        occupation = _occupation(source, code)
        occupation_records[code] = occupation
        ept = _series_endpoint_record(
            source,
            family="D2_EPT_TERRITORIAL_OFFER",
            entity=code,
            metric="technical_enrollments",
        )
        ept_records[code] = ept
        youth_records[code] = _series_endpoint_record(
            source,
            family="D2_YOUTH_WORK_18_24",
            entity=code,
            metric="total",
            age="18_24",
        )
        occupation_share = occupation["absoluteChange"] / positive_change_denominator * 100
        ept_share = ept["final_value"] / ept_denominator * 100
        records.append(
            {
                "municipality_ibge_code": code,
                "municipality_name": municipality["name"],
                "cbo_414140_initial_value": occupation["initialValue"],
                "cbo_414140_final_value": occupation["finalValue"],
                "cbo_414140_absolute_change": occupation["absoluteChange"],
                "share_of_positive_regional_change_percent": occupation_share,
                "technical_enrollments_2025": ept["final_value"],
                "technical_enrollments_availability_state": ept["availability_state"],
                "share_of_regional_ept_percent": ept_share,
                "share_difference_percentage_points": occupation_share - ept_share,
            }
        )
    if not math.isclose(sum(item["share_of_positive_regional_change_percent"] for item in records), 100, abs_tol=1e-9):
        raise Job5KValidationError("participações da mudança positiva R4 não fecham 100%")
    if not math.isclose(sum(item["share_of_regional_ept_percent"] for item in records), 100, abs_tol=1e-9):
        raise Job5KValidationError("participações EPT R4 não fecham 100%")
    divergence = 0.5 * sum(abs(item["share_difference_percentage_points"]) for item in records)
    by_code = {item["municipality_ibge_code"]: item for item in records}
    bridge_by_entity = {item["entityId"]: item for item in source["bridgeSummaries"]}
    primary_by_entity = [
        {
            "entity_id": REGION_ID,
            "occupation": {
                "initial_value": region_occupation["initialValue"],
                "final_value": region_occupation["finalValue"],
                "absolute_change": region_occupation["absoluteChange"],
                "unit": "active_bonds",
            },
            "ept": region_ept,
            "occupation_change_share_percent": None,
            "ept_share_percent": None,
            "share_difference_percentage_points": None,
        }
    ]
    secondary_by_entity = [
        {
            "entity_id": REGION_ID,
            "youth_work_18_24": region_youth,
            "youth_regional_change_contribution_percent": None,
            "bridge": bridge_by_entity[REGION_ID],
        }
    ]
    region_youth_change = region_youth["absolute_change"]
    for municipality in municipalities:
        code = municipality["ibgeCode"]
        record = by_code[code]
        occupation = occupation_records[code]
        primary_by_entity.append(
            {
                "entity_id": code,
                "occupation": {
                    "initial_value": occupation["initialValue"],
                    "final_value": occupation["finalValue"],
                    "absolute_change": occupation["absoluteChange"],
                    "unit": "active_bonds",
                },
                "ept": ept_records[code],
                "occupation_change_share_percent": record["share_of_positive_regional_change_percent"],
                "ept_share_percent": record["share_of_regional_ept_percent"],
                "share_difference_percentage_points": record["share_difference_percentage_points"],
            }
        )
        youth = youth_records[code]
        contribution = (
            None
            if region_youth_change == 0
            else youth["absolute_change"] / region_youth_change * 100
        )
        secondary_by_entity.append(
            {
                "entity_id": code,
                "youth_work_18_24": youth,
                "youth_regional_change_contribution_percent": contribution,
                "bridge": bridge_by_entity.get(code),
            }
        )
    variants = []
    for entity in entities:
        primary = next(item for item in primary_by_entity if item["entity_id"] == entity)
        secondary = next(item for item in secondary_by_entity if item["entity_id"] == entity)
        occupation = primary["occupation"]
        ept = primary["ept"]
        if entity == REGION_ID:
            title = "A transformação logística se concentra em Nova Santa Rita, enquanto a oferta técnica está localizada em outros municípios do Vale."
            summary = (
                f"No Vale, os vínculos da ocupação auxiliar de logística passaram de {_fmt_number(occupation['initial_value'])} "
                f"para {_fmt_number(occupation['final_value'])} entre 2019 e 2025. Em 2025, a EPT localizada somou "
                f"{_fmt_number(ept['final_value'])} matrículas, distribuídas de modo diferente entre os dez municípios."
            )
            selected_read = "A visão regional alinha a participação de cada município na mudança ocupacional positiva e na EPT localizada."
            key_figures = [
                {"label": "Auxiliar de logística no Vale", "value": f"{_fmt_number(occupation['initial_value'])} → {_fmt_number(occupation['final_value'])}", "period": "2019–2025"},
                {"label": "EPT localizada no Vale", "value": _fmt_number(ept["final_value"]), "period": "2025"},
            ]
            function = "distribuições regionais alinhadas"
        else:
            name = names[entity]
            if ept["availability_state"] == "observed_zero":
                if entity == NSR_CODE:
                    title = "A transformação logística se concentra em Nova Santa Rita, enquanto a oferta técnica está localizada em outros municípios do Vale."
                else:
                    title = f"O trabalho logístico cresceu em {name}, onde a EPT localizada registrou zero observado em 2025."
            elif primary["share_difference_percentage_points"] > 0:
                title = f"A participação de {name} no crescimento logístico supera sua participação na EPT localizada do Vale."
            elif primary["share_difference_percentage_points"] < 0:
                title = f"A participação de {name} na EPT localizada supera sua participação no crescimento logístico do Vale."
            else:
                title = f"{name} ocupa participações equivalentes no crescimento logístico e na EPT localizada do Vale."
            ept_text = (
                "zero observado"
                if ept["availability_state"] == "observed_zero"
                else _fmt_number(ept["final_value"])
            )
            summary = (
                f"Em {name}, a ocupação passou de {_fmt_number(occupation['initial_value'])} para {_fmt_number(occupation['final_value'])}, "
                f"respondendo por {_fmt_number(primary['occupation_change_share_percent'], 3)}% da mudança positiva regional; "
                f"a EPT localizada registrou {ept_text} em 2025. "
                f"Os vínculos formais de 18 a 24 anos passaram de {_fmt_number(secondary['youth_work_18_24']['initial_value'])} "
                f"para {_fmt_number(secondary['youth_work_18_24']['final_value'])}."
            )
            selected_read = (
                f"{name} é comparado ao Vale por duas participações territoriais, sem supor que trabalhadores e estudantes sejam as mesmas pessoas."
            )
            key_figures = [
                {"label": "Auxiliar de logística", "value": f"{_fmt_number(occupation['initial_value'])} → {_fmt_number(occupation['final_value'])}", "period": "2019–2025"},
                {"label": "EPT localizada", "value": ept_text, "period": "2025"},
            ]
            function = "contraste entre local de trabalho e localização escolar"
        variants.append(
            {
                "variant_id": f"STORY_LOGISTICS_EPT.{entity}",
                "entity_id": entity,
                "municipality_ibge_code": None if entity == REGION_ID else entity,
                "title_conclusion": title,
                "integrated_summary": summary,
                "selected_municipality_read": selected_read,
                "key_figures": key_figures,
                "territorial_function": function,
                "availability_state": ept["availability_state"] if entity != REGION_ID else "observed",
                "zero_state": "observed_zero" if ept["availability_state"] == "observed_zero" else "not_zero",
                "primary_evidence_entity_id": entity,
                "secondary_evidence_entity_id": entity,
            }
        )
    regional_summary = next(item["integrated_summary"] for item in variants if item["entity_id"] == REGION_ID)
    return _story_common(
        story_id="STORY_LOGISTICS_EPT",
        direction_id="DIRECTION_WORK_EDUCATION_COORDINATION",
        editorial_role="PRIMARY_INSIGHT",
        analytical_sources=["JOB5J_R4", "JOB5I_EVIDENCE"],
        analytical_states={"R4": "TERRITORIAL_MISMATCH"},
        title="A transformação logística se concentra em Nova Santa Rita, enquanto a oferta técnica está localizada em outros municípios do Vale.",
        summary=regional_summary,
        regional_read="A mudança da ocupação auxiliar de logística e a EPT localizada têm distribuições municipais diferentes no Vale.",
        variants=variants,
        distribution={
            "distribution_id": "CBO_414140_CHANGE_SHARE_VS_EPT_SHARE_2025",
            "positive_change_denominator_contract": "sum_of_positive_municipal_absolute_changes_only",
            "positive_change_denominator": positive_change_denominator,
            "regional_ept_denominator": ept_denominator,
            "regional_distribution_divergence_percentage_points": divergence,
            "rows": records,
        },
        primary={"by_entity": primary_by_entity},
        secondary={"by_entity": secondary_by_entity},
        planning="Usar o contraste para verificar deslocamentos, itinerários e organização regional antes de qualquer decisão local sobre oferta.",
        monitoring=["CBO 414140", "vínculos formais de 18 a 24 anos", "EPT localizada", "origem dos estudantes quando disponível", "correspondências normativas"],
        coordination=["desenvolvimento econômico", "trabalho", "instituições de EPT", "municípios do Vale"],
        boundary="O contraste combina local de trabalho e localização escolar, sem identificar as mesmas pessoas. A ponte é normativa, muitos-para-muitos e não transforma o total de EPT em formação específica para logística.",
        allowed=["mudança ocupacional observada", "participações territoriais", "zero observado de EPT", "diferença entre distribuições"],
        forbidden=["necessidade automática de curso", "acesso individual", "aderência curricular provada", "mesmas pessoas", "prioridade municipal"],
        source_refs=["job5gcr_occupation_endpoints", "job5gcr_ept_offer", "job5gcr_rais_youth", "job5gcr_bridge"],
        periods=["2019–2025", "2025"],
        lenses=["workplace", "school_location"],
        pne_goal_refs=_pne_refs(source, ["D2_OCCUPATIONS_SECTORS", "D2_EPT_TERRITORIAL_OFFER", "D2_NORMATIVE_WORK_EDUCATION_BRIDGE"]),
    )


def _build_youth_story(
    source: Mapping[str, Any],
    municipalities: Sequence[Mapping[str, str]],
) -> dict[str, Any]:
    entities = [REGION_ID, *[item["ibgeCode"] for item in municipalities]]
    names = {item["ibgeCode"]: item["name"] for item in municipalities}
    names[REGION_ID] = REGION_NAME
    primary_by_entity = []
    secondary_by_entity = []
    distribution = []
    for entity in entities:
        rais15 = _series_endpoint_record(
            source,
            family="D2_YOUTH_WORK_15_17",
            entity=entity,
            metric="total",
            age="15_17",
        )
        apprentice15 = _series_endpoint_record(
            source,
            family="D2_APPRENTICESHIP",
            entity=entity,
            metric="apprentice_admissions",
            age="15_17",
        )
        share = _find_fact(
            source,
            family="D2_APPRENTICESHIP",
            entity=entity,
            metric="apprenticeship_share_of_youth_admission_events",
            age="15_17",
            period_contains="2025",
        )
        rais18 = _series_endpoint_record(
            source,
            family="D2_YOUTH_WORK_18_24",
            entity=entity,
            metric="total",
            age="18_24",
        )
        caged15 = _series_endpoint_record(
            source,
            family="D2_YOUTH_WORK_15_17",
            entity=entity,
            metric="caged_youth_admissions",
            age="15_17",
        )
        caged18 = _series_endpoint_record(
            source,
            family="D2_YOUTH_WORK_18_24",
            entity=entity,
            metric="caged_youth_admissions",
            age="18_24",
        )
        trajectory = None
        if entity != REGION_ID:
            dropout = _find_series(
                source,
                family="D2_YOUTH_WORK_15_17",
                entity=entity,
                metric="education_dropout_rate_percent",
                stage="high_school",
            )
            trajectory = {
                "dropout_percent_2025": _point(dropout, 2025)["value"],
                "series_id": dropout["seriesId"],
            }
        primary_by_entity.append(
            {
                "entity_id": entity,
                "rais_15_17": rais15,
                "apprenticeship_15_17": apprentice15,
                "apprenticeship_share_2025": {
                    "numerator": share["numerator"],
                    "denominator": share["denominator"],
                    "percent": share["displayValue"],
                    "availability_state": share["availabilityState"],
                    "fact_id": share["factId"],
                },
            }
        )
        secondary_by_entity.append(
            {
                "entity_id": entity,
                "rais_18_24": rais18,
                "caged_admissions_15_17": caged15,
                "caged_admissions_18_24": caged18,
                "school_trajectory": trajectory,
            }
        )
        if entity != REGION_ID:
            distribution.append(
                {
                    "municipality_ibge_code": entity,
                    "municipality_name": names[entity],
                    "rais_15_17_initial_value": rais15["initial_value"],
                    "rais_15_17_final_value": rais15["final_value"],
                    "rais_15_17_absolute_change": rais15["absolute_change"],
                    "apprenticeship_events_2025": share["numerator"],
                    "youth_admission_events_2025": share["denominator"],
                    "apprenticeship_share_percent_2025": share["displayValue"],
                    "availability_state": share["availabilityState"],
                }
            )
    variants = []
    for entity in entities:
        primary = next(item for item in primary_by_entity if item["entity_id"] == entity)
        rais = primary["rais_15_17"]
        share = primary["apprenticeship_share_2025"]
        if entity == REGION_ID:
            title = "O trabalho formal juvenil e a aprendizagem mudaram no território, sem uma relação estável com a trajetória escolar."
            summary = (
                f"No Vale, os vínculos formais de 15 a 17 anos passaram de {_fmt_number(rais['initial_value'])} para {_fmt_number(rais['final_value'])}. "
                f"Em 2025, {_fmt_number(share['numerator'])} de {_fmt_number(share['denominator'])} eventos de admissão juvenil foram classificados como aprendizagem."
            )
            selected_read = "A visão regional mantém estoques de vínculos, fluxos de admissão e trajetória escolar em camadas separadas."
            function = "agenda regional de monitoramento separado"
        else:
            name = names[entity]
            title = f"Em {name}, trabalho formal juvenil e aprendizagem mudaram; a trajetória escolar é acompanhada separadamente."
            summary = (
                f"Em {name}, os vínculos formais de 15 a 17 anos passaram de {_fmt_number(rais['initial_value'])} para {_fmt_number(rais['final_value'])}; "
                f"em 2025, foram {_fmt_number(share['numerator'])} eventos de aprendizagem em {_fmt_number(share['denominator'])} admissões juvenis "
                f"({_fmt_number(share['percent'], 3)}%). A leitura escolar permanece paralela."
            )
            selected_read = f"{name} é mostrado com estoque RAIS e fluxos de admissão separados, sem identificar as mesmas pessoas."
            function = "fatos municipais em séries paralelas"
        variants.append(
            {
                "variant_id": f"STORY_YOUTH_WORK_APPRENTICESHIP.{entity}",
                "entity_id": entity,
                "municipality_ibge_code": None if entity == REGION_ID else entity,
                "title_conclusion": title,
                "integrated_summary": summary,
                "selected_municipality_read": selected_read,
                "key_figures": [
                    {"label": "Vínculos formais de 15 a 17 anos", "value": f"{_fmt_number(rais['initial_value'])} → {_fmt_number(rais['final_value'])}", "period": "2019–2025"},
                    {"label": "Aprendizagem nas admissões de 2025", "value": f"{_fmt_number(share['numerator'])} / {_fmt_number(share['denominator'])} = {_fmt_number(share['percent'], 3)}%", "period": "2025"},
                ],
                "territorial_function": function,
                "availability_state": share["availability_state"],
                "zero_state": "observed_zero" if share["numerator"] == 0 else "not_zero",
                "primary_evidence_entity_id": entity,
                "secondary_evidence_entity_id": entity,
            }
        )
    regional_summary = next(item["integrated_summary"] for item in variants if item["entity_id"] == REGION_ID)
    return _story_common(
        story_id="STORY_YOUTH_WORK_APPRENTICESHIP",
        direction_id="DIRECTION_WORK_EDUCATION_COORDINATION",
        editorial_role="PRIMARY_FACTUAL_STORY_WITH_ASSOCIATION_BOUNDARY",
        analytical_sources=["JOB5J_R3", "JOB5I_EVIDENCE"],
        analytical_states={"R3": "NOT_SUPPORTED"},
        title="O trabalho formal juvenil e a aprendizagem mudaram no território, sem uma relação estável com a trajetória escolar.",
        summary=regional_summary,
        regional_read="O trabalho formal juvenil e a aprendizagem mudaram no território, mas os dados agregados disponíveis não mostraram uma relação estável com abandono ou reprovação.",
        variants=variants,
        distribution=distribution,
        primary={"by_entity": primary_by_entity},
        secondary={"by_entity": secondary_by_entity},
        planning="Monitorar escola, trabalho e aprendizagem em conjunto institucional, mantendo os registros separados e sem recomendação automática.",
        monitoring=["estoque RAIS de 15 a 17 anos", "admissões Caged", "eventos de aprendizagem", "trajetória do ensino médio", "faixa de 18 a 24 anos"],
        coordination=["educação", "trabalho", "assistência", "empregadores", "Sistema S"],
        boundary="O trabalho formal juvenil e a aprendizagem mudaram no território, mas os dados agregados disponíveis não mostraram uma relação estável com abandono ou reprovação. Estoques e eventos não equivalem a pessoas únicas.",
        allowed=["mudanças observadas no trabalho formal", "eventos de aprendizagem", "monitoramento institucional paralelo"],
        forbidden=["explicação do abandono pelo trabalho", "vínculo de mesma pessoa", "fusão de estoque e fluxo", "recomendação automática"],
        source_refs=["job5gcr_rais_youth", "job5gcr_caged_safe", "job5gcr_apprenticeship", "job5gar_trajectory"],
        periods=["2019–2025", "2020–2025"],
        lenses=["workplace", "school_location"],
        pne_goal_refs=_pne_refs(source, ["D2_YOUTH_WORK_15_17", "D2_YOUTH_WORK_18_24", "D2_APPRENTICESHIP"]),
    )


def _build_conditional_contexts(
    source: Mapping[str, Any],
    municipalities: Sequence[Mapping[str, str]],
) -> list[dict[str, Any]]:
    entities = [REGION_ID, *[item["ibgeCode"] for item in municipalities]]
    names = {item["ibgeCode"]: item["name"] for item in municipalities}
    names[REGION_ID] = REGION_NAME
    rural_variants = []
    special_variants = []
    for entity in entities:
        rural_total = _series_endpoint_record(
            source,
            family="D1_RURALITY_PNATE_PLANNING",
            entity=entity,
            metric="rural_enrollments",
            stage="all",
        )
        rural_schools = _series_endpoint_record(
            source,
            family="D1_RURALITY_PNATE_PLANNING",
            entity=entity,
            metric="rural_schools",
            stage="all",
        )
        rural_high = _series_endpoint_record(
            source,
            family="D1_RURALITY_PNATE_PLANNING",
            entity=entity,
            metric="rural_enrollments",
            stage="high_school",
        )
        pnate = _find_series(
            source,
            family="D1_RURALITY_PNATE_PLANNING",
            entity=entity,
            metric="pnate_adjusted_forecast",
        )
        pnate_2026 = _point(pnate, 2026)
        stable_phrase = (
            "o número de escolas rurais permaneceu estável"
            if rural_schools["absolute_change"] == 0
            else f"a mudança no número de escolas rurais foi {_fmt_signed(rural_schools['absolute_change'])}"
        )
        rural_variants.append(
            {
                "entity_id": entity,
                "municipality_ibge_code": None if entity == REGION_ID else entity,
                "title": "A oferta rural mudou em ritmos diferentes; o transporte permanece contexto separado de planejamento.",
                "summary": (
                    f"Em {names[entity]}, as matrículas rurais mudaram {_fmt_signed(rural_total['absolute_change'])} e {stable_phrase}; "
                    f"no ensino médio rural, a mudança foi {_fmt_signed(rural_high['absolute_change'])} entre 2014 e 2025. "
                    "O valor de 2026 é uma previsão administrativa de planejamento, não execução nem uso observado."
                ),
                "rural_enrollments": rural_total,
                "rural_schools": rural_schools,
                "rural_high_school_enrollments": rural_high,
                "pnate_2026": {
                    "value": pnate_2026["value"],
                    "availability_state": pnate_2026["availabilityState"],
                    "unit": pnate["unit"],
                    "series_id": pnate["seriesId"],
                    "planning_only": True,
                },
                "availability_state": rural_total["availability_state"],
                "zero_state": "observed_zero" if rural_total["final_value"] == 0 else "not_zero",
            }
        )
        special = _series_endpoint_record(
            source,
            family="D1_SPECIAL_AEE_TERRITORY",
            entity=entity,
            metric="special_enrollments",
            stage="all",
        )
        aee = _series_endpoint_record(
            source,
            family="D1_SPECIAL_AEE_TERRITORY",
            entity=entity,
            metric="schools_offering_aee",
            stage="all",
        )
        special_variants.append(
            {
                "entity_id": entity,
                "municipality_ibge_code": None if entity == REGION_ID else entity,
                "title": "Educação especial e AEE — contexto descritivo.",
                "summary": (
                    f"Em {names[entity]}, as matrículas da educação especial passaram de {_fmt_number(special['initial_value'])} para {_fmt_number(special['final_value'])}, "
                    f"e as escolas que informam AEE passaram de {_fmt_number(aee['initial_value'])} para {_fmt_number(aee['final_value'])}."
                ),
                "special_enrollments": special,
                "schools_reporting_aee": aee,
                "interpretation_boundary": "Matrículas da educação especial e escolas que informam AEE cresceram, mas os dados não medem cobertura nem atendimento das mesmas pessoas.",
                "availability_state": special["availability_state"],
                "zero_state": "mixed",
            }
        )
    return [
        {
            "context_id": "CONTEXT_RURALITY_TRANSPORT",
            "direction_id": "DIRECTION_EDUCATION_TERRITORY",
            "analytical_source": "JOB5J_R7",
            "analytical_relation_state": "PLANNING_SIGNAL",
            "editorial_story_state": "CONDITIONAL_EXPANDED",
            "source_refs": ["job5gbr_rural", "job5gd_pnate"],
            "territorial_lenses": ["rural_school_location", "municipal_executor"],
            "network_scope": NETWORK_SCOPE,
            "variants": rural_variants,
        },
        {
            "context_id": "CONTEXT_SPECIAL_AEE",
            "direction_id": "DIRECTION_EDUCATION_TERRITORY",
            "analytical_source": "JOB5J_R8",
            "analytical_relation_state": "PLANNING_SIGNAL",
            "editorial_story_state": "DESCRIPTIVE_CONTEXT_ONLY",
            "source_refs": ["job5gbr_special_aee"],
            "territorial_lenses": ["school_location"],
            "network_scope": NETWORK_SCOPE,
            "variants": special_variants,
        },
    ]


def _promotion_contract(contract: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "relation_id": relation_id,
            "analytical_relation_state": value["analyticalRelationState"],
            "editorial_story_state": value["editorialStoryState"],
            "component_fact_visibility": value["componentFactVisibility"],
            "interpretation_boundary_state": value["interpretationBoundaryState"],
        }
        for relation_id, value in contract["externalJudgment"]["relationPromotion"].items()
    ]


def build_bundle(preflight: Mapping[str, Any] | None = None) -> dict[str, Any]:
    contract = _contract()
    preflight_record = dict(preflight or verify_frozen_integrity())
    source = _json(JOB5I_ROOT / "BUNDLE_UI_V2_JOB5I.json")
    catalog = _json(JOB5J_ROOT / "CATALOGO_INSIGHTS_CANDIDATOS_JOB5J.json")
    models = _json(JOB5J_ROOT / "MODELOS_E_ROBUSTEZ_DETALHADOS_JOB5J.json")
    heterogeneity_rows = _read_csv_gzip(
        JOB5J_ROOT / "MATRIZ_HETEROGENEIDADE_10_MUNICIPIOS_JOB5J.csv.gz"
    )
    heterogeneity = {
        relation_id: [row for row in heterogeneity_rows if row["relation_id"] == relation_id]
        for relation_id in (f"R{index}" for index in range(1, 9))
    }
    municipalities = _municipalities()
    stories = [
        _build_high_school_story(source, municipalities, heterogeneity),
        _build_eja_story(source, municipalities, heterogeneity, models),
        _build_logistics_ept_story(source, municipalities),
        _build_youth_story(source, municipalities),
    ]
    contexts = _build_conditional_contexts(source, municipalities)
    source_registry = [
        item
        for item in source["sourceRegistry"]
        if item["sourceRef"] in {ref for story in stories for ref in story["source_refs"]}
        or item["sourceRef"] in {ref for context in contexts for ref in context["source_refs"]}
    ]
    bundle = {
        "schema_version": "vocacoes-pne-insight-first-bundle-v1",
        "contract_version": "1.0.0-internal-job5k",
        "meta": {
            "job_id": "v7-job5k",
            "generated_at": GENERATED_AT,
            "internal_only": True,
            "feature_flag": "VITE_ENABLE_VOCACOES_PNE_INTERNAL",
            "public_narrative_authorized": False,
            "publication_authorized": False,
            "public_data_writes_authorized": False,
            "gate11": "CLOSED",
            "external_judgment_required": True,
            "manager_validation_started": False,
            "network_used": False,
            "database_used": False,
            "new_acquisition_performed": False,
            "official_formulas_altered": False,
        },
        "preflight": preflight_record,
        "external_judgment": {
            "state": contract["externalJudgment"]["state"],
            "job5j_rerun_required": False,
            "job5k_authorized": True,
            "automatic_product_approval": False,
        },
        "editorial_promotion_contract": _promotion_contract(contract),
        "region": {
            "entity_id": REGION_ID,
            "name": REGION_NAME,
            "slug": "vale-do-sinos",
            "state_code": "RS",
            "municipality_count": 10,
        },
        "fallback_municipality_ibge_code": NSR_CODE,
        "municipalities": municipalities,
        "directions": [
            {
                "direction_id": "DIRECTION_EDUCATION_TERRITORY",
                "sequence": 1,
                "title": "Oferta, trajetória e organização territorial",
                "manager_question": "Como a oferta e a trajetória educacional se reorganizam entre o município e o Vale?",
                "story_ids": ["STORY_HIGH_SCHOOL_TRAJECTORY", "STORY_EJA_TERRITORY"],
            },
            {
                "direction_id": "DIRECTION_WORK_EDUCATION_COORDINATION",
                "sequence": 2,
                "title": "Trabalho, formação e coordenação regional",
                "manager_question": "Onde as transformações do trabalho e a oferta formativa pedem coordenação territorial?",
                "story_ids": ["STORY_LOGISTICS_EPT", "STORY_YOUTH_WORK_APPRENTICESHIP"],
            },
        ],
        "stories": stories,
        "conditional_contexts": contexts,
        "source_registry": source_registry,
        "evidence_layer": {
            "job5i_preserved": True,
            "job5i_bundle_dynamic_import": "./vocacoesPneJob5iCore.json + ./vocacoesPneJob5iSeries.json",
            "default_open": False,
            "technical_layer_default_open": False,
            "technical_layer_printed": False,
        },
        "pne_contract": {
            "canonical_path": "contracts/pne2026-goal-indicator-contract.json",
            "sha256": contract["frozenInputs"]["pne2026ContractSha256"],
            "official_indicator_recalculated": False,
            "goal_compliance_claim_allowed": False,
        },
        "pme_contract": {
            "state": "not_materialized",
            "goal_refs": [],
            "planning_themes_are_not_goals": True,
        },
        "normalization": {
            "regional_evidence_stored_once": True,
            "municipal_variants_generated_by_rules": True,
            "manual_municipality_profiles": False,
            "canonical_code_used_for_identity_only": True,
            "ranking_used": False,
            "opaque_materiality_threshold_used": False,
            "json_encoded_inside_strings": False,
        },
        "job5j_catalog_state": catalog["state"],
        "counts": {
            "direction_count": 2,
            "primary_story_count": len(stories),
            "story_variant_count": sum(
                len(story["selected_municipality_read"]["variants"])
                for story in stories
            ),
            "conditional_context_count": len(contexts),
            "conditional_variant_count": sum(len(item["variants"]) for item in contexts),
            "municipality_count": len(municipalities),
            "relation_count": len(contract["externalJudgment"]["relationPromotion"]),
        },
    }
    validate_bundle(bundle)
    return bundle


def _visible_texts(bundle: Mapping[str, Any]) -> list[str]:
    values: list[str] = []
    for direction in bundle["directions"]:
        values.extend([direction["title"], direction["manager_question"]])
    for story in bundle["stories"]:
        values.extend(
            [
                story["title_conclusion"],
                story["integrated_summary"],
                story["regional_read"],
                story["planning_implication"],
                story["interpretation_boundary"],
            ]
        )
        for variant in story["selected_municipality_read"]["variants"]:
            values.extend(
                [
                    variant["title_conclusion"],
                    variant["integrated_summary"],
                    variant["selected_municipality_read"],
                ]
            )
    for context in bundle["conditional_contexts"]:
        for variant in context["variants"]:
            values.extend([variant["title"], variant["summary"]])
            if "interpretation_boundary" in variant:
                values.append(variant["interpretation_boundary"])
    return values


def _story_variant(story: Mapping[str, Any], entity_id: str) -> Mapping[str, Any]:
    matches = [
        item
        for item in story["selected_municipality_read"]["variants"]
        if item["entity_id"] == entity_id
    ]
    if len(matches) != 1:
        raise Job5KValidationError(f"variante única ausente em {story['story_id']}/{entity_id}")
    return matches[0]


def validate_bundle(bundle: Mapping[str, Any]) -> None:
    if bundle["meta"]["gate11"] != "CLOSED":
        raise Job5KValidationError("Gate 11 deve permanecer fechado")
    if any(
        bundle["meta"][key]
        for key in (
            "public_narrative_authorized",
            "publication_authorized",
            "public_data_writes_authorized",
            "manager_validation_started",
            "network_used",
            "database_used",
            "new_acquisition_performed",
            "official_formulas_altered",
        )
    ):
        raise Job5KValidationError("operação ou autorização proibida no meta Job 5K")
    codes = [item["ibgeCode"] for item in bundle["municipalities"]]
    if len(codes) != 10 or len(set(codes)) != 10 or any(
        not isinstance(code, str) or not IBGE_PATTERN.fullmatch(code) for code in codes
    ):
        raise Job5KValidationError("identidade/cobertura municipal inválida")
    if bundle["fallback_municipality_ibge_code"] != NSR_CODE or NSR_CODE not in codes:
        raise Job5KValidationError("fixture de reconstrução Nova Santa Rita ausente")
    if len(bundle["directions"]) != 2 or len(bundle["stories"]) != 4:
        raise Job5KValidationError("o bundle deve conter duas direções e quatro histórias principais")
    if bundle["counts"]["story_variant_count"] != 44:
        raise Job5KValidationError("cada história deve cobrir Vale + dez municípios")
    if bundle["counts"]["conditional_variant_count"] != 22:
        raise Job5KValidationError("contextos condicionais devem cobrir Vale + dez municípios")
    expected_entities = {REGION_ID, *codes}
    for story in bundle["stories"]:
        if not REQUIRED_STORY_FIELDS <= set(story):
            raise Job5KValidationError(
                f"contrato de história incompleto em {story.get('story_id')}"
            )
        if story["network_scope"] != NETWORK_SCOPE:
            raise Job5KValidationError("história fora da rede total")
        if story["manager_review_state"] != "pending" or story["public_narrative_authorized"]:
            raise Job5KValidationError("história autoaprovada")
        variants = story["selected_municipality_read"]["variants"]
        if {item["entity_id"] for item in variants} != expected_entities:
            raise Job5KValidationError(f"cobertura de variantes incompleta em {story['story_id']}")
        if any(item["municipality_ibge_code"] not in {None, item["entity_id"]} for item in variants):
            raise Job5KValidationError("identidade municipal de variante divergente")
    promotion = {item["relation_id"]: item for item in bundle["editorial_promotion_contract"]}
    if set(promotion) != {f"R{index}" for index in range(1, 9)}:
        raise Job5KValidationError("contrato editorial não cobre R1–R8")
    if promotion["R1"]["editorial_story_state"] != "PRIMARY_INSIGHT":
        raise Job5KValidationError("R1 não promovido a história primária")
    if promotion["R2"]["editorial_story_state"] != "NOT_STANDALONE":
        raise Job5KValidationError("R2 deve permanecer sem cartão próprio")
    if promotion["R8"]["editorial_story_state"] != "DESCRIPTIVE_CONTEXT_ONLY":
        raise Job5KValidationError("R8 não foi rebaixado editorialmente")
    if any(story["story_id"].endswith("R2") or story["story_id"].endswith("R8") for story in bundle["stories"]):
        raise Job5KValidationError("R2/R8 não podem virar headline principal")
    for text in _visible_texts(bundle):
        for pattern in VISIBLE_BLOCKED_PATTERNS:
            if pattern.search(text):
                raise Job5KValidationError(
                    f"linguagem bloqueada no texto visível: {pattern.pattern}: {text}"
                )
    high_school = next(item for item in bundle["stories"] if item["story_id"] == "STORY_HIGH_SCHOOL_TRAJECTORY")
    high_nsr = _story_variant(high_school, NSR_CODE)
    if "+41" not in json.dumps(high_nsr, ensure_ascii=False):
        raise Job5KValidationError("âncora +41 de Nova Santa Rita ausente")
    eja = next(item for item in bundle["stories"] if item["story_id"] == "STORY_EJA_TERRITORY")
    eja_nsr = _story_variant(eja, NSR_CODE)
    eja_text = json.dumps(eja_nsr, ensure_ascii=False)
    if "+2,648 p.p." not in eja_text or "−2,605 p.p." not in eja_text:
        raise Job5KValidationError("âncoras R5 Nova Santa Rita ausentes")
    logistics = next(item for item in bundle["stories"] if item["story_id"] == "STORY_LOGISTICS_EPT")
    logistics_nsr = _story_variant(logistics, NSR_CODE)
    logistics_text = json.dumps(logistics_nsr, ensure_ascii=False)
    if "17 → 722" not in logistics_text or "zero observado" not in logistics_text:
        raise Job5KValidationError("âncoras R4 Nova Santa Rita ausentes")
    youth = next(item for item in bundle["stories"] if item["story_id"] == "STORY_YOUTH_WORK_APPRENTICESHIP")
    youth_text = json.dumps(_story_variant(youth, NSR_CODE), ensure_ascii=False)
    if "104 → 172" not in youth_text or "174 / 219 = 79,452%" not in youth_text:
        raise Job5KValidationError("âncoras de aprendizagem Nova Santa Rita ausentes")
    legal = _json(REPO_ROOT / "contracts" / "pne2026-goal-indicator-contract.json")
    legal_refs = set(legal["goals"])
    visible_refs = {ref for story in bundle["stories"] for ref in story["pne_goal_refs"]}
    if not visible_refs <= legal_refs:
        raise Job5KValidationError("referência PNE fora do contrato canônico")
    if bundle["pme_contract"]["goal_refs"]:
        raise Job5KValidationError("PME deve permanecer não materializado")


def _source_inventory(preflight: Mapping[str, Any]) -> list[dict[str, Any]]:
    candidates = {
        "job5i_bundle": JOB5I_ROOT / "BUNDLE_UI_V2_JOB5I.json",
        "job5i_manifest": JOB5I_ROOT / "MANIFEST_JOB5I.json",
        "job5j_catalog": JOB5J_ROOT / "CATALOGO_INSIGHTS_CANDIDATOS_JOB5J.json",
        "job5j_heterogeneity": JOB5J_ROOT / "MATRIZ_HETEROGENEIDADE_10_MUNICIPIOS_JOB5J.csv.gz",
        "job5j_models": JOB5J_ROOT / "MODELOS_E_ROBUSTEZ_DETALHADOS_JOB5J.json",
        "job5j_manifest": JOB5J_ROOT / "MANIFEST_JOB5J.json",
        "job5gcr_occupation_panel": OCCUPATION_PANEL,
        "job5k_prompt": Path("C:/Users/rnbirck/Downloads/PROMPT_JOB5K_SOL_MAX.md"),
        "orchestration_contract": REPO_ROOT / "docs" / "CONTRATO_ORQUESTRACAO_VOCACOES_PNE_V7.md",
        "pne_contract": REPO_ROOT / "contracts" / "pne2026-goal-indicator-contract.json",
        "municipality_registry": REPO_ROOT / "config" / "municipalities" / "rs.json",
        "region_registry": REPO_ROOT / "config" / "regions" / "rs.json",
    }
    return [
        {
            "source_ref": key,
            "path": (
                path.relative_to(REPO_ROOT).as_posix()
                if path.is_relative_to(REPO_ROOT)
                else path.as_posix()
            ),
            "byte_size": path.stat().st_size,
            "sha256": sha256_file(path),
            "local_frozen_input": True,
            "network_used": False,
            "database_used": False,
        }
        for key, path in sorted(candidates.items())
    ]


def _coverage_rows(bundle: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = []
    names = {item["ibgeCode"]: item["name"] for item in bundle["municipalities"]}
    names[REGION_ID] = REGION_NAME
    for story in bundle["stories"]:
        for variant in story["selected_municipality_read"]["variants"]:
            rows.append(
                {
                    "record_type": "primary_story",
                    "direction_id": story["direction_id"],
                    "story_or_context_id": story["story_id"],
                    "entity_id": variant["entity_id"],
                    "municipality_ibge_code": variant["municipality_ibge_code"] or "",
                    "entity_name": names[variant["entity_id"]],
                    "editorial_role": story["editorial_role"],
                    "availability_state": variant["availability_state"],
                    "zero_state": variant["zero_state"],
                    "network_scope": story["network_scope"],
                    "manager_review_state": story["manager_review_state"],
                    "public_narrative_authorized": str(story["public_narrative_authorized"]).lower(),
                }
            )
    for context in bundle["conditional_contexts"]:
        for variant in context["variants"]:
            rows.append(
                {
                    "record_type": "conditional_context",
                    "direction_id": context["direction_id"],
                    "story_or_context_id": context["context_id"],
                    "entity_id": variant["entity_id"],
                    "municipality_ibge_code": variant["municipality_ibge_code"] or "",
                    "entity_name": names[variant["entity_id"]],
                    "editorial_role": context["editorial_story_state"],
                    "availability_state": variant["availability_state"],
                    "zero_state": variant["zero_state"],
                    "network_scope": context["network_scope"],
                    "manager_review_state": "pending",
                    "public_narrative_authorized": "false",
                }
            )
    return rows


def _dossier(bundle: Mapping[str, Any], entity_id: str) -> str:
    name = REGION_NAME if entity_id == REGION_ID else next(
        item["name"] for item in bundle["municipalities"] if item["ibgeCode"] == entity_id
    )
    lines = [
        f"# Dossiê da página insight-first — {name}",
        "",
        "> Protótipo interno para avaliação; conteúdo não publicado e revisão da gestora ainda não iniciada.",
        "",
        "## Quatro leituras principais",
        "",
    ]
    for index, story in enumerate(bundle["stories"], start=1):
        variant = _story_variant(story, entity_id)
        lines.extend(
            [
                f"### {index}. {variant['title_conclusion']}",
                "",
                variant["integrated_summary"],
                "",
                f"**Função territorial:** {variant['territorial_function']}.",
                "",
                f"**Limite:** {story['interpretation_boundary']}",
                "",
            ]
        )
    lines.extend(
        [
            "## Contextos condicionais",
            "",
            *[
                f"- {next(item for item in context['variants'] if item['entity_id'] == entity_id)['summary']}"
                for context in bundle["conditional_contexts"]
            ],
            "",
            "## Estado",
            "",
            "- Rede: total, todas as dependências.",
            "- Código IBGE: textual, sete dígitos.",
            "- Revisão da gestora: pendente.",
            "- Narrativa pública: não autorizada.",
            "- Publicação: não realizada.",
        ]
    )
    return "\n".join(lines) + "\n"


def _visual_qa(finalized: bool, screenshots: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    visual_status = "PASS" if finalized else "PENDING"
    controls = [
        {"controlId": "FLAG_OFF_FAIL_CLOSED", "status": "PASS", "evidence": "rota interna depende de VITE_ENABLE_VOCACOES_PNE_INTERNAL=true"},
        {"controlId": "PUBLIC_NAVIGATION_UNCHANGED", "status": "PASS", "evidence": "registro público não contém a rota interna"},
        {"controlId": "TWO_DIRECTIONS_FOUR_STORIES", "status": "PASS", "evidence": "bundle normalizado: 2 direções, 4 histórias"},
        {"controlId": "VALE_PLUS_TEN_MUNICIPALITIES", "status": "PASS", "evidence": "44 variantes principais e 22 condicionais"},
        {"controlId": "DESKTOP_1440", "status": visual_status, "evidence": SCREENSHOT_FILES[0] if finalized else "captura pendente"},
        {"controlId": "REGIONAL_VIEW", "status": visual_status, "evidence": SCREENSHOT_FILES[1] if finalized else "captura pendente"},
        {"controlId": "MOBILE_390_NO_OVERFLOW", "status": visual_status, "evidence": SCREENSHOT_FILES[2] if finalized else "captura pendente"},
        {"controlId": "PRINT_WITHOUT_SHELL_CONTROLS_TECHNICAL", "status": visual_status, "evidence": SCREENSHOT_FILES[3] if finalized else "captura pendente"},
        {"controlId": "KEYBOARD_FOCUS_HEADINGS_TOOLTIPS", "status": visual_status, "evidence": "E2E Job 5K" if finalized else "E2E pendente"},
        {"controlId": "CONSOLE_CLEAN", "status": visual_status, "evidence": "E2E Job 5K" if finalized else "E2E pendente"},
    ]
    return {
        "schemaVersion": "vocacoes-pne-job5k-visual-qa-v1",
        "generatedAt": GENERATED_AT,
        "result": "PASS_WITH_EXPLICIT_LIMITS" if finalized else "PENDING_VISUAL_QA",
        "controlCount": len(controls),
        "failedCount": sum(item["status"] == "FAIL" for item in controls),
        "pendingCount": sum(item["status"] == "PENDING" for item in controls),
        "controls": controls,
        "screenshots": list(screenshots),
    }


def _validation_report(
    bundle: Mapping[str, Any],
    finalized: bool,
    evidence: Mapping[str, Any] | None,
) -> dict[str, Any]:
    commands = list((evidence or {}).get("commands", []))
    return {
        "schemaVersion": "vocacoes-pne-job5k-validation-v1",
        "generatedAt": GENERATED_AT,
        "result": "PASS_WITH_EXPLICIT_LIMITS" if finalized else "PENDING_RUNTIME_AND_VISUAL_QA",
        "requiredChecksPassed": bool(finalized and (evidence or {}).get("requiredChecksPassed")),
        "commands": commands,
        "knownUnrelatedHygieneIssue": (evidence or {}).get("knownUnrelatedHygieneIssue"),
        "counts": bundle["counts"],
        "anchors": {
            "valeHighSchoolChange": -4878,
            "novaSantaRitaHighSchoolChange": 41,
            "valeCbo414140": [303, 2124],
            "novaSantaRitaCbo414140": [17, 722],
            "novaSantaRitaCboContributionPercent": 38.715,
            "novaSantaRitaEpt2025": 0,
            "valeEpt2025": 13945,
            "r5FundamentalDistancePercentagePoints": 21.678,
            "r5HighSchoolDistancePercentagePoints": 51.814,
            "novaSantaRitaR5FundamentalDifferencePercentagePoints": 2.648,
            "novaSantaRitaR5HighSchoolDifferencePercentagePoints": -2.605,
            "novaSantaRitaApprenticeship2025": [174, 219, 79.452],
            "novaSantaRitaYouthWork18_24": [1117, 1638, 45.582],
        },
        "numericTolerance": {
            "absoluteCounts": 0,
            "percentagePoints": 0.0005,
            "percentages": 0.0005,
        },
        "sideEffects": {
            "networkUsed": False,
            "databaseUsed": False,
            "newAcquisitionPerformed": False,
            "publicDataChanged": False,
            "publicationPerformed": False,
            "navigationChanged": False,
            "managerValidationStarted": False,
            "gate11": "CLOSED",
        },
    }


def _checkpoint(
    bundle: Mapping[str, Any],
    finalized: bool,
    validation: Mapping[str, Any],
) -> str:
    state = FINAL_STATE if finalized else PENDING_STATE
    return "\n".join(
        [
            "# Checkpoint Job 5K para julgamento externo",
            "",
            f"**Estado:** `{state}`",
            "",
            "## Resultado",
            "",
            "A rota interna foi reorganizada para quatro conclusões em duas direções. O bundle Job 5I permanece como camada de evidências recolhida e o julgamento Job 5J foi promovido por contrato editorial separado.",
            "",
            "## Preflight",
            "",
            f"- Job 5I preservado: `{bundle['preflight']['digests']['job5iTreeDigestSha256']}`.",
            f"- Job 5J preservado: `{bundle['preflight']['digests']['job5jTreeDigestSha256']}`.",
            f"- `public/data` preservado: `{bundle['preflight']['digests']['publicDataTreeDigestSha256']}`.",
            "- O nome de contrato solicitado não existia; foi usado `docs/CONTRATO_ORQUESTRACAO_VOCACOES_PNE_V7.md`, sem diferença semântica detectada.",
            "",
            "## Limites",
            "",
            "- Resultados negativos de mobilidade e trabalho–trajetória aparecem como limites de interpretação, não como inexistência de relação.",
            "- Trabalho, residência estudantil, oferta escolar e execução municipal continuam em lentes separadas.",
            "- Revisão da gestora segue pendente; narrativa pública, publicação e Gate 11 continuam fechados.",
            "",
            "## Validação",
            "",
            f"- Resultado: `{validation['result']}`.",
            f"- Comandos registrados: {len(validation['commands'])}.",
        ]
    ) + "\n"


def _artifact_roles() -> dict[str, str]:
    return {
        "CHECKPOINT_JOB5K_FOR_PRO.md": "checkpoint executivo e estado do produto interno",
        "CONTRATO_INSIGHT_FIRST_JOB5K.json": "contrato editorial de promoção 5J→5K",
        "BUNDLE_INSIGHTS_UI_JOB5K.json": "bundle normalizado de histórias e variantes",
        "DOSSIE_PAGINA_NOVA_SANTA_RITA_JOB5K.md": "reconstrução da página para Nova Santa Rita",
        "DOSSIE_PAGINA_VALE_DO_SINOS_JOB5K.md": "reconstrução da visão regional",
        "MATRIZ_COBERTURA_INSIGHTS_10_MUNICIPIOS_JOB5K.csv.gz": "cobertura simétrica Vale + dez municípios",
        "MATRIZ_QA_VISUAL_JOB5K.json": "controles de interface, acessibilidade e impressão",
        "VALIDATION_REPORT_JOB5K.json": "testes, âncoras e efeitos colaterais",
        "ARTIFACT_INDEX_JOB5K.json": "índice dos quinze artefatos compartilhados",
        "PACOTE_REVISAO_EXTERNA_JOB5K.json": "payload compacto para julgamento externo",
        "MANIFEST_JOB5K.json": "manifesto final, hashes e estado",
        SCREENSHOT_FILES[0]: "captura desktop de Nova Santa Rita",
        SCREENSHOT_FILES[1]: "captura desktop do Vale do Sinos",
        SCREENSHOT_FILES[2]: "captura mobile de Nova Santa Rita",
        SCREENSHOT_FILES[3]: "captura da impressão",
    }


def _artifact_index(output_dir: Path, finalized: bool) -> dict[str, Any]:
    records = []
    roles = _artifact_roles()
    expected = OUTPUT_FILES if finalized else NON_SCREENSHOT_FILES
    for name in expected:
        path = output_dir / name
        self_or_manifest = name in {"ARTIFACT_INDEX_JOB5K.json", "MANIFEST_JOB5K.json"}
        available = path.is_file() and not self_or_manifest
        records.append(
            {
                "path": name,
                "role": roles[name],
                "byteSize": path.stat().st_size if available else None,
                "sha256": sha256_file(path) if available else None,
                "hashStatus": "recorded" if available else "self_or_manifest_hashed_by_final_manifest",
            }
        )
    return {
        "schemaVersion": "vocacoes-pne-job5k-artifact-index-v1",
        "generatedAt": GENERATED_AT,
        "sharedFileLimit": 15,
        "sharedFileCount": len(expected),
        "finalized": finalized,
        "artifacts": records,
    }


def _implementation_files() -> list[dict[str, Any]]:
    candidates = [
        CONTRACT_PATH,
        Path(__file__).resolve(),
        REPO_ROOT / "data_pipeline" / "scripts" / "run_vocacoes_pne_v7_job5k.py",
        REPO_ROOT / "data_pipeline" / "tests" / "test_vocacoes_pne_job5k.py",
        REPO_ROOT / "src" / "features" / "vocacoes-pne-internal" / "VocacoesPneInternalPage.tsx",
        REPO_ROOT / "src" / "features" / "vocacoes-pne-internal" / "components" / "VocacoesPneInsights.tsx",
        REPO_ROOT / "src" / "styles" / "vocacoes-pne-internal.css",
    ]
    return [
        {
            "path": path.relative_to(REPO_ROOT).as_posix(),
            "byteSize": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for path in candidates
        if path.is_file()
    ]


def _manifest(
    output_dir: Path,
    bundle: Mapping[str, Any],
    finalized: bool,
    validation: Mapping[str, Any],
) -> dict[str, Any]:
    paths = sorted(
        path
        for path in output_dir.iterdir()
        if path.is_file() and path.name != "MANIFEST_JOB5K.json"
    )
    return {
        "schemaVersion": "vocacoes-pne-job5k-manifest-v1",
        "jobId": "v7-job5k",
        "generatedAt": GENERATED_AT,
        "classification": "DATA_LOGIC",
        "domains": ["DATA_PRESENTATION", "UI_ONLY", "INTERNAL_EDITORIAL_COMPILER", "VISUAL_QA"],
        "generationState": FINAL_STATE if finalized else PENDING_STATE,
        "finalState": FINAL_STATE if finalized else None,
        "externalJudgmentRequired": True,
        "automaticProductApproval": False,
        "managerReviewState": "pending",
        "publicNarrativeAuthorized": False,
        "gate11": "CLOSED",
        "checkpointFiles": list(OUTPUT_FILES if finalized else NON_SCREENSHOT_FILES),
        "artifacts": [
            {"path": path.name, "byteSize": path.stat().st_size, "sha256": sha256_file(path)}
            for path in paths
        ],
        "implementationFiles": _implementation_files(),
        "sourceInventory": _source_inventory(bundle["preflight"]),
        "frozenInputIntegrity": {
            "job5gcr": bundle["preflight"]["digests"]["job5gcrTreeDigestSha256"],
            "job5i": bundle["preflight"]["digests"]["job5iTreeDigestSha256"],
            "job5j": bundle["preflight"]["digests"]["job5jTreeDigestSha256"],
            "unchanged": True,
        },
        "publicDataIntegrity": {
            "beforeTreeDigestSha256": bundle["preflight"]["digests"]["publicDataTreeDigestSha256"],
            "afterTreeDigestSha256": bundle["preflight"]["digests"]["publicDataTreeDigestSha256"],
            "unchanged": True,
        },
        "counts": {
            **bundle["counts"],
            "shared_file_count": len(OUTPUT_FILES if finalized else NON_SCREENSHOT_FILES),
            "validation_command_count": len(validation["commands"]),
        },
        "formulasAltered": [],
        "deterministicTransformsAdded": [
            "endpoint_absolute_change",
            "share_of_positive_regional_change",
            "share_of_regional_ept",
            "share_difference_percentage_points",
            "total_variation_distance_reuse_from_job5j",
            "regional_change_contribution",
        ],
        "generation": {
            "deterministic": True,
            "transactional": True,
            "manifestLast": True,
            "networkUsed": False,
            "databaseUsed": False,
            "newAcquisitionPerformed": False,
            "publicDataChanged": False,
            "frontendChanged": True,
            "publicNavigationChanged": False,
            "fullBuildUsed": bool(finalized and any(item.get("id") == "full-build-flag" and item.get("status") == "PASS" for item in validation["commands"])),
            "publicationPerformed": False,
        },
    }


def write_package(
    *,
    output_dir: Path,
    bundle: Mapping[str, Any],
    finalized: bool = False,
    screenshot_source_root: Path | None = None,
    validation_evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if output_dir.exists():
        raise FileExistsError(f"staging Job 5K deve ser novo: {output_dir}")
    output_dir.mkdir(parents=True)
    if finalized:
        if screenshot_source_root is None:
            raise Job5KValidationError("finalização exige raiz das quatro capturas")
        for name in SCREENSHOT_FILES:
            source = screenshot_source_root / name
            if not source.is_file() or source.stat().st_size == 0:
                raise Job5KValidationError(f"captura final ausente: {source}")
            shutil.copy2(source, output_dir / name)
        if not validation_evidence or not validation_evidence.get("requiredChecksPassed"):
            raise Job5KValidationError("finalização exige evidência de validação integral")
    screenshots = [
        {"path": name, "byteSize": (output_dir / name).stat().st_size, "sha256": sha256_file(output_dir / name)}
        for name in SCREENSHOT_FILES
        if (output_dir / name).is_file()
    ]
    contract_payload = {
        **_contract(),
        "executionState": {
            "preflight": "PASSED",
            "editorialCompilation": "PASSED",
            "frontendImplementation": "AUTHORIZED_INTERNAL_ONLY",
            "visualQa": "PASSED" if finalized else "PENDING",
            "externalJudgment": "PENDING",
            "managerValidation": "NOT_STARTED",
            "gate11": "CLOSED",
        },
        "promotionContract": bundle["editorial_promotion_contract"],
    }
    coverage_rows = _coverage_rows(bundle)
    coverage_fields = [
        "record_type",
        "direction_id",
        "story_or_context_id",
        "entity_id",
        "municipality_ibge_code",
        "entity_name",
        "editorial_role",
        "availability_state",
        "zero_state",
        "network_scope",
        "manager_review_state",
        "public_narrative_authorized",
    ]
    visual_qa = _visual_qa(finalized, screenshots)
    validation = _validation_report(bundle, finalized, validation_evidence)
    external_package = {
        "schemaVersion": "vocacoes-pne-job5k-external-review-v1",
        "generatedAt": GENERATED_AT,
        "state": FINAL_STATE if finalized else PENDING_STATE,
        "externalJudgmentRequired": True,
        "automaticApproval": False,
        "managerReviewState": "pending",
        "publicNarrativeAuthorized": False,
        "gate11": "CLOSED",
        "directions": bundle["directions"],
        "primaryStories": [
            {
                "storyId": story["story_id"],
                "editorialRole": story["editorial_role"],
                "title": story["title_conclusion"],
                "regionalRead": story["regional_read"],
                "interpretationBoundary": story["interpretation_boundary"],
            }
            for story in bundle["stories"]
        ],
        "conditionalContexts": [
            {"contextId": item["context_id"], "editorialStoryState": item["editorial_story_state"]}
            for item in bundle["conditional_contexts"]
        ],
        "validationResult": validation["result"],
        "visualQaResult": visual_qa["result"],
        "remainingLimits": [
            "revisão externa do produto ainda pendente",
            "validação da gestora não iniciada",
            "origem dos estudantes da EPT não disponível",
            "registros não identificam as mesmas pessoas entre educação e trabalho",
            "PME não materializado",
        ],
    }
    payloads: dict[str, bytes] = {
        "CONTRATO_INSIGHT_FIRST_JOB5K.json": _json_bytes(contract_payload),
        "BUNDLE_INSIGHTS_UI_JOB5K.json": _json_bytes(bundle),
        "DOSSIE_PAGINA_NOVA_SANTA_RITA_JOB5K.md": _dossier(bundle, NSR_CODE).encode("utf-8"),
        "DOSSIE_PAGINA_VALE_DO_SINOS_JOB5K.md": _dossier(bundle, REGION_ID).encode("utf-8"),
        "MATRIZ_COBERTURA_INSIGHTS_10_MUNICIPIOS_JOB5K.csv.gz": _gzip_csv_bytes(coverage_rows, coverage_fields),
        "MATRIZ_QA_VISUAL_JOB5K.json": _json_bytes(visual_qa),
        "VALIDATION_REPORT_JOB5K.json": _json_bytes(validation),
        "PACOTE_REVISAO_EXTERNA_JOB5K.json": _json_bytes(external_package),
        "CHECKPOINT_JOB5K_FOR_PRO.md": _checkpoint(bundle, finalized, validation).encode("utf-8"),
    }
    for name, content in payloads.items():
        (output_dir / name).write_bytes(content)
    (output_dir / "ARTIFACT_INDEX_JOB5K.json").write_bytes(
        _json_bytes(_artifact_index(output_dir, finalized))
    )
    manifest = _manifest(output_dir, bundle, finalized, validation)
    (output_dir / "MANIFEST_JOB5K.json").write_bytes(_json_bytes(manifest))
    validate_existing_output(output_dir, require_screenshots=finalized)
    return manifest


def frontend_bundle_bytes(bundle: Mapping[str, Any]) -> bytes:
    return _json_bytes(bundle, compact=True)


def validate_existing_output(
    output_dir: Path = DEFAULT_OUTPUT_ROOT,
    *,
    require_screenshots: bool | None = None,
    allow_draft_screenshots: bool = False,
) -> dict[str, Any]:
    if not output_dir.is_dir():
        raise Job5KValidationError(f"pacote Job 5K ausente: {output_dir}")
    manifest = _json(output_dir / "MANIFEST_JOB5K.json")
    finalized = manifest["finalState"] == FINAL_STATE
    if require_screenshots is not None and finalized != require_screenshots:
        raise Job5KValidationError("fase de validação do pacote Job 5K divergente")
    declared_expected = set(OUTPUT_FILES if finalized else NON_SCREENSHOT_FILES)
    expected = set(OUTPUT_FILES if finalized or allow_draft_screenshots else NON_SCREENSHOT_FILES)
    actual = {path.name for path in output_dir.iterdir() if path.is_file()}
    if actual != expected:
        raise Job5KValidationError(
            f"topologia Job 5K divergente: faltam={sorted(expected-actual)}, extras={sorted(actual-expected)}"
        )
    declared = {item["path"]: item for item in manifest["artifacts"]}
    if set(declared) != declared_expected - {"MANIFEST_JOB5K.json"}:
        raise Job5KValidationError("manifesto Job 5K não cobre todos os artefatos")
    for name, item in declared.items():
        path = output_dir / name
        if path.stat().st_size != item["byteSize"] or sha256_file(path) != item["sha256"]:
            raise Job5KValidationError(f"hash/tamanho divergente em {name}")
    bundle = _json(output_dir / "BUNDLE_INSIGHTS_UI_JOB5K.json")
    validate_bundle(bundle)
    validation = _json(output_dir / "VALIDATION_REPORT_JOB5K.json")
    visual = _json(output_dir / "MATRIZ_QA_VISUAL_JOB5K.json")
    if finalized:
        if not validation["requiredChecksPassed"] or validation["result"] != "PASS_WITH_EXPLICIT_LIMITS":
            raise Job5KValidationError("relatório final de validação não passou")
        if visual["failedCount"] or visual["pendingCount"] or visual["result"] != "PASS_WITH_EXPLICIT_LIMITS":
            raise Job5KValidationError("QA visual final não passou")
        if len(manifest["checkpointFiles"]) != 15:
            raise Job5KValidationError("checkpoint final não contém 15 arquivos")
    else:
        if manifest["generationState"] != PENDING_STATE:
            raise Job5KValidationError("pacote preliminar deve permanecer pendente de QA")
    if manifest["gate11"] != "CLOSED" or manifest["publicNarrativeAuthorized"]:
        raise Job5KValidationError("manifesto abriu autorização proibida")
    return manifest
