"""Correção determinística e isolada do H2 — Job 5B.

Consome somente materializações locais congeladas do Job 5A, registra a busca
dirigida de denominadores e produz dez artefatos em staging interno. Não acessa
banco, rede ou fontes externas e nunca escreve em ``public/data``.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any, Mapping, Sequence

import pandas as pd

from src.vocacoes_pne_job2 import (
    artifact_record,
    assert_outside_public_data,
    replace_directory_transactionally,
    sha256_file,
    staging_directory_for,
    validate_unique_key,
    write_csv_gzip,
    write_json,
)


SCHEMA_VERSION = "vocacoes-pne-v7-job5b-v1"
JOB_ID = "v7-job5b"
REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_PIPELINE_DIR = REPO_ROOT / "data_pipeline"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / ".tmp" / "vocacoes-pne" / JOB_ID
JOB5A_ROOT = REPO_ROOT / ".tmp" / "vocacoes-pne" / "v7-job5a"
CONTRACT_PATH = DATA_PIPELINE_DIR / "contracts" / "vocacoes-pne-v7-job5b.json"
LAUNCHER_PATH = DATA_PIPELINE_DIR / "scripts" / "run_vocacoes_pne_v7_job5b.py"
CORE_PATH = Path(__file__).resolve()
NOVA_SANTA_RITA_ID = "4313375"
PEER_IDS = ("4307609", "4314803", "4303905")
IBGE_PATTERN = re.compile(r"^[0-9]{7}$")
RECENT_YEARS = (2023, 2024, 2025)
PERFORMANCE_METRICS = (
    "approval_rate_percent",
    "failure_rate_percent",
    "dropout_rate_percent",
)
DISTORTION_METRIC = "age_grade_distortion_rate_percent"
RESULT_STATE = "NOT_EVALUABLE_DUE_TO_DATA_OR_QA_LIMIT"

OUTPUT_FILES = (
    "h2_family_level_matrix.csv.gz",
    "h2_distortion_corrected_matrix.csv.gz",
    "h2_stability_qa.json",
    "nova_santa_rita_h2_corrected.json",
    "h2_corrected_internal_synthesis.json",
    "h2_corrected_c1_c12_evidence.csv.gz",
    "external_review_package_job5b.json",
    "limitations_job5b.json",
    "output_inventory_job5b.json",
    "manifest_job5b.json",
)

JOB5A_HASHES = {
    "manifest.json": "6af6f111557489f3ca09584619f508388fe6a2d7b6d70597ea48a58dc39f1c92",
    "h2_factual_matrix.csv.gz": "d0ee6c59e0a01afb2bc20e893201cf893702b9de25882017efca59589721e079",
    "h2_internal_synthesis.json": "8eabc09396c222e51cf6d127de0ee0bfeeb3f5d94b42e3b60cd28cc31bd19dd2",
    "nova_santa_rita_h2.json": "04c757291fb317caa6d538b8eee08627b2212cdd74ef22ab9f2113ef8dfb4861",
    "total_network_qa.csv.gz": "60b37f27534bb263b7ee7d94bada3f48158f241c501c988b48c1281386aa8170",
    "c1_c12_evidence.csv.gz": "3608df45b98430a17a31dfa463b50786297a888fd946e772ad9db70b0fffb773",
    "external_review_package.json": "6675ac60c51f57815c3e721c141ef7bf25c15ba90644f873b7cfa88634697f3d",
}

LOCAL_DENOMINATOR_AUDIT_HASHES = {
    "public/data/educacao/visao-geral-municipal/4313375.json": (
        "72f858563f97ba439206baba69ed5f639deddd7b9d34a9c01d560d341a50f2d7"
    ),
    "public/data/educacao/municipios/4313375.json": (
        "4c0ea7e23d9244d074cdbe9b9426fb1509a7447b256b32cf1442bd2ab6d6b64d"
    ),
}

STAGE_LABELS = {
    "fundamental": "ensino fundamental",
    "fundamental_anos_iniciais": "anos iniciais do ensino fundamental",
    "fundamental_anos_finais": "anos finais do ensino fundamental",
    "medio": "ensino médio",
}

CRITERIA = {
    "C1": "PNE_PME_relevance",
    "C2": "municipal_specificity",
    "C3": "canonical_total_network_scope",
    "C4": "multi_year_recent_period",
    "C5": "stability_and_small_denominator_QA",
    "C6": "performance_family_integration",
    "C7": "allowed_comparator_support",
    "C8": "distortion_rule_separation",
    "C9": "noncausal_interpretation",
    "C10": "traceability",
    "C11": "internal_only_boundary",
    "C12": "external_judgment_stop",
}


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _inline_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _json_safe(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


def _verify_hash(path: Path, expected: str, *, label: str) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"Entrada congelada ausente ({label}): {path}")
    actual = sha256_file(path)
    if actual != expected:
        raise ValueError(f"Hash divergente para {label}: {actual} != {expected}.")


def verify_frozen_inputs() -> dict[str, Any]:
    for relative, expected in JOB5A_HASHES.items():
        _verify_hash(JOB5A_ROOT / relative, expected, label=f"Job 5A/{relative}")
    for relative, expected in LOCAL_DENOMINATOR_AUDIT_HASHES.items():
        _verify_hash(REPO_ROOT / relative, expected, label=f"auditoria local/{relative}")
    contract = _load_json(CONTRACT_PATH)
    if contract["outputs"] != list(OUTPUT_FILES):
        raise ValueError("Contrato Job 5B diverge da allowlist de outputs.")
    if contract["scope"]["networkScope"] != "total_all_dependencies":
        raise ValueError("Escopo de rede canônico não preservado.")
    if contract["distortion"]["performanceFamilyClosureStatus"] != "NOT_APPLICABLE":
        raise ValueError("Distorção voltou a depender do fechamento de rendimento.")
    return contract


def _read_h2() -> pd.DataFrame:
    frame = pd.read_csv(
        JOB5A_ROOT / "h2_factual_matrix.csv.gz",
        dtype={"municipality_ibge_code": "string"},
    )
    validate_unique_key(
        frame,
        ["municipality_ibge_code", "year", "stage", "indicator"],
        label="H2 congelado do Job 5A",
    )
    if len(frame) != 1240 or frame["municipality_ibge_code"].nunique() != 10:
        raise ValueError("Cobertura H2 congelada divergente.")
    if set(frame["network_scope"]) != {"total_all_dependencies"}:
        raise ValueError("H2 contém rede fora do escopo total canônico.")
    if not frame["municipality_ibge_code"].map(
        lambda value: isinstance(value, str) and bool(IBGE_PATTERN.fullmatch(value))
    ).all():
        raise ValueError("Identidade IBGE textual inválida no H2.")
    return frame


def _metric_snapshot(
    frame: pd.DataFrame,
    municipality_id: str,
    stage: str,
    metric: str,
) -> pd.Series:
    selected = frame[
        (frame["municipality_ibge_code"] == municipality_id)
        & (frame["stage"] == stage)
        & (frame["indicator"] == metric)
        & (frame["year"] == 2025)
    ]
    if len(selected) != 1:
        raise ValueError(
            f"Série H2 ambígua/ausente: {municipality_id}/{stage}/{metric}."
        )
    return selected.iloc[0]


def _values(row: pd.Series) -> dict[int, float]:
    result = {
        year: float(row[f"recent_{year}_value_percent"]) for year in RECENT_YEARS
    }
    if any(pd.isna(value) for value in result.values()):
        raise ValueError("Período recente H2 contém valor ausente.")
    return result


def _literal_direction(start: float, end: float, *, tolerance: float = 1e-12) -> str:
    delta = end - start
    if delta > tolerance:
        return "increase"
    if delta < -tolerance:
        return "decrease"
    return "stable"


def _transitions(values: Mapping[int, float]) -> list[str]:
    return [
        _literal_direction(values[2023], values[2024]),
        _literal_direction(values[2024], values[2025]),
    ]


def _format_percent(value: float) -> str:
    return f"{value:.1f}".replace(".", ",") + "%"


def _movement_phrase(label: str, values: Mapping[int, float]) -> str:
    direction = _literal_direction(values[2023], values[2025])
    article = "o" if label == "abandono" else "a"
    if direction == "increase":
        movement = f"aumentou de {_format_percent(values[2023])} para {_format_percent(values[2025])}"
    elif direction == "decrease":
        movement = f"caiu de {_format_percent(values[2023])} para {_format_percent(values[2025])}"
    else:
        movement = (
            f"ficou estável entre {_format_percent(values[2023])} "
            f"e {_format_percent(values[2025])}"
        )
    return f"{article} {label} {movement}"


def _family_routine(
    approval: Mapping[int, float],
    failure: Mapping[int, float],
    dropout: Mapping[int, float],
) -> str:
    directions = (
        _literal_direction(approval[2023], approval[2025]),
        _literal_direction(failure[2023], failure[2025]),
        _literal_direction(dropout[2023], dropout[2025]),
    )
    if directions[1] == "increase" and directions[2] == "decrease":
        return "revisar separadamente as rotinas de recuperação e de prevenção do abandono"
    if directions == ("increase", "decrease", "decrease"):
        return "definir quais rotinas anuais devem ser preservadas e verificadas no próximo fechamento"
    if directions[0] == "decrease" or directions[2] == "increase":
        return "priorizar uma revisão anual das rotinas de permanência, recuperação e conclusão"
    return "definir uma rotina anual conjunta de verificação de permanência e rendimento"


def _family_question(
    municipality_name: str,
    stage: str,
    approval: Mapping[int, float],
    failure: Mapping[int, float],
    dropout: Mapping[int, float],
) -> str:
    return (
        f"Em {municipality_name}, como {_family_routine(approval, failure, dropout)} "
        f"no {STAGE_LABELS[stage]} diante dos movimentos simultâneos — "
        f"{_movement_phrase('aprovação', approval)}, "
        f"{_movement_phrase('abandono', dropout)} e {_movement_phrase('reprovação', failure)} "
        "— entre 2023 e 2025, sem presumir que os mesmos estudantes transitaram entre categorias?"
    )


def _joint_classification(
    approval: Mapping[int, float],
    failure: Mapping[int, float],
    dropout: Mapping[int, float],
) -> str:
    return "__".join(
        (
            f"approval_{_literal_direction(approval[2023], approval[2025])}",
            f"failure_{_literal_direction(failure[2023], failure[2025])}",
            f"dropout_{_literal_direction(dropout[2023], dropout[2025])}",
        )
    ).upper()


def _family_snapshot(
    frame: pd.DataFrame, municipality_id: str, stage: str
) -> dict[str, Any]:
    rows = {
        metric: _metric_snapshot(frame, municipality_id, stage, metric)
        for metric in PERFORMANCE_METRICS
    }
    values = {metric: _values(row) for metric, row in rows.items()}
    approval = values["approval_rate_percent"]
    failure = values["failure_rate_percent"]
    dropout = values["dropout_rate_percent"]
    closure = {
        year: approval[year] + failure[year] + dropout[year] for year in RECENT_YEARS
    }
    residual = {year: closure[year] - 100.0 for year in RECENT_YEARS}
    if any(abs(value) > 1e-9 for value in residual.values()):
        raise ValueError(f"Família de rendimento não fecha: {municipality_id}/{stage}.")
    return {
        "rows": rows,
        "values": values,
        "closure": closure,
        "residual": residual,
        "classification": _joint_classification(approval, failure, dropout),
    }


def build_family_matrix(frame: pd.DataFrame) -> pd.DataFrame:
    names = (
        frame[["municipality_ibge_code", "municipality_name"]]
        .drop_duplicates()
        .set_index("municipality_ibge_code")["municipality_name"]
        .to_dict()
    )
    stages = sorted(frame["stage"].unique())
    snapshots = {
        (municipality_id, stage): _family_snapshot(frame, municipality_id, stage)
        for municipality_id in sorted(names)
        for stage in stages
    }
    rows: list[dict[str, Any]] = []
    for municipality_id in sorted(names):
        for stage in stages:
            item = snapshots[(municipality_id, stage)]
            values = item["values"]
            peer_support: dict[str, Any] = {}
            different_peers: list[str] = []
            for peer_id in PEER_IDS:
                if peer_id == municipality_id:
                    continue
                peer = snapshots[(peer_id, stage)]
                peer_support[peer_id] = {
                    "municipalityName": names[peer_id],
                    "jointClassification": peer["classification"],
                    "approval2025": peer["values"]["approval_rate_percent"][2025],
                    "failure2025": peer["values"]["failure_rate_percent"][2025],
                    "dropout2025": peer["values"]["dropout_rate_percent"][2025],
                    "supportRole": "frozen_peer_observed_family",
                }
                if peer["classification"] != item["classification"]:
                    different_peers.append(peer_id)
            approval = values["approval_rate_percent"]
            failure = values["failure_rate_percent"]
            dropout = values["dropout_rate_percent"]
            source_rows = item["rows"]
            rows.append(
                {
                    "municipality_ibge_code": municipality_id,
                    "municipality_name": names[municipality_id],
                    "stage": stage,
                    "recent_period": "2023-2025",
                    "performance_family": "approval_failure_dropout",
                    "network_scope": "total_all_dependencies",
                    **{
                        f"approval_{year}_percent": approval[year] for year in RECENT_YEARS
                    },
                    **{f"failure_{year}_percent": failure[year] for year in RECENT_YEARS},
                    **{f"dropout_{year}_percent": dropout[year] for year in RECENT_YEARS},
                    **{
                        f"closure_{year}_percent": item["closure"][year]
                        for year in RECENT_YEARS
                    },
                    "maximum_absolute_closure_residual_pp": max(
                        abs(value) for value in item["residual"].values()
                    ),
                    "performance_family_closure_status": "APPLICABLE_CLOSED",
                    "approval_transition_directions": _inline_json(_transitions(approval)),
                    "failure_transition_directions": _inline_json(_transitions(failure)),
                    "dropout_transition_directions": _inline_json(_transitions(dropout)),
                    "approval_persistence_status": source_rows[
                        "approval_rate_percent"
                    ]["recent_persistence_status"],
                    "failure_persistence_status": source_rows[
                        "failure_rate_percent"
                    ]["recent_persistence_status"],
                    "dropout_persistence_status": source_rows[
                        "dropout_rate_percent"
                    ]["recent_persistence_status"],
                    "joint_direction_classification": item["classification"],
                    "frozen_peer_support": _inline_json(peer_support),
                    "different_joint_direction_peer_ids": _inline_json(different_peers),
                    "vale_aggregate_rate_status": "unavailable_missing_compatible_numerators_denominators",
                    "rs_aggregate_rate_status": "unavailable_missing_compatible_numerators_denominators",
                    "vale_rs_direction_claim_allowed": False,
                    "small_denominator_status": "SMALL_DENOMINATOR_RULE_UNAVAILABLE",
                    "stability_status": "STABILITY_NOT_VERIFIABLE",
                    "automatic_series_approval_allowed": False,
                    "internal_evidence_status": "INTERNAL_FACT_FOR_EXTERNAL_JUDGMENT",
                    "monitoring_indicator": (
                        f"três taxas oficiais da rede total em {stage}, verificadas em conjunto por ano"
                    ),
                    "planning_question": _family_question(
                        names[municipality_id], stage, approval, failure, dropout
                    ),
                    "decision_delta": (
                        "one joint family-level decision; no duplicated indicator-level decision"
                    ),
                    "administrative_dependency_is_analytic_dimension": False,
                    "same_student_transition_inference_allowed": False,
                    "causal_interpretation_allowed": False,
                }
            )
    result = pd.DataFrame(rows).sort_values(
        ["municipality_ibge_code", "stage"]
    ).reset_index(drop=True)
    validate_unique_key(
        result,
        ["municipality_ibge_code", "stage", "recent_period", "performance_family"],
        label="matriz familiar H2 corrigida",
    )
    if len(result) != 40:
        raise ValueError(f"Matriz familiar deveria ter 40 séries, recebeu {len(result)}.")
    return result


def _distortion_question(
    municipality_name: str,
    stage: str,
    values: Mapping[int, float],
    persistence: str,
) -> str:
    movement = _movement_phrase("distorção idade-série", values)
    if persistence == "persistent_improvement":
        routine = "verificar anualmente quais ações de correção de fluxo devem ser preservadas"
    elif persistence == "persistent_worsening":
        routine = "priorizar a revisão anual das ações de correção de fluxo e permanência"
    else:
        routine = "definir uma rotina anual para distinguir oscilação de mudança sustentada"
    return (
        f"Em {municipality_name}, como {routine} no {STAGE_LABELS[stage]}, considerando que {movement} "
        f"entre 2023 e 2025 e que a trajetória foi classificada como {persistence}?"
    )


def build_distortion_matrix(frame: pd.DataFrame) -> pd.DataFrame:
    snapshots = frame[
        (frame["indicator"] == DISTORTION_METRIC) & (frame["year"] == 2025)
    ].copy()
    if len(snapshots) != 40:
        raise ValueError("Esperadas 40 séries de distorção em 2025.")
    lookup = {
        (str(row.municipality_ibge_code), str(row.stage)): row
        for row in snapshots.itertuples(index=False)
    }
    rows: list[dict[str, Any]] = []
    for source in snapshots.sort_values(["municipality_ibge_code", "stage"]).itertuples(
        index=False
    ):
        source_dict = source._asdict()
        values = {
            year: float(source_dict[f"recent_{year}_value_percent"])
            for year in RECENT_YEARS
        }
        persistence = str(source.recent_persistence_status)
        peer_support: dict[str, Any] = {}
        different_peers: list[str] = []
        for peer_id in PEER_IDS:
            if peer_id == source.municipality_ibge_code:
                continue
            peer = lookup[(peer_id, source.stage)]
            peer_support[peer_id] = {
                "municipalityName": peer.municipality_name,
                "value2025Percent": float(peer.recent_2025_value_percent),
                "persistence": peer.recent_persistence_status,
                "supportRole": "frozen_peer_observed_distortion_series",
            }
            if peer.recent_persistence_status != persistence:
                different_peers.append(peer_id)
        persistent = persistence in {"persistent_improvement", "persistent_worsening"}
        peer_difference = bool(different_peers)
        if persistent and peer_difference:
            inclusion = "INTERNAL_FACT_RETAINED_STABILITY_NOT_VERIFIABLE"
            reason = (
                "multi-year persistent movement with a different frozen-peer direction; "
                "automatic approval blocked by unavailable exact denominator"
            )
        elif not persistent:
            inclusion = "EXCLUDED_FROM_PASS_RULE_NON_PERSISTENT"
            reason = "recent movement is stable_or_mixed across the two transitions"
        else:
            inclusion = "EXCLUDED_FROM_PASS_RULE_NO_DIFFERENT_FROZEN_PEER_DIRECTION"
            reason = "no frozen peer has a different recent persistence classification"
        rows.append(
            {
                "municipality_ibge_code": source.municipality_ibge_code,
                "municipality_name": source.municipality_name,
                "stage": source.stage,
                "indicator": DISTORTION_METRIC,
                "recent_period": "2023-2025",
                "network_scope": "total_all_dependencies",
                **{f"value_{year}_percent": values[year] for year in RECENT_YEARS},
                "recent_change_2023_2025_pp": values[2025] - values[2023],
                "recent_transition_directions": _inline_json(_transitions(values)),
                "recent_persistence_status": persistence,
                "performance_family_closure_status": "NOT_APPLICABLE",
                "frozen_peer_support": _inline_json(peer_support),
                "different_recent_direction_peer_ids": _inline_json(different_peers),
                "vale_aggregate_rate_status": "unavailable_missing_compatible_numerators_denominators",
                "rs_aggregate_rate_status": "unavailable_missing_compatible_numerators_denominators",
                "vale_municipal_distribution_median_2025_percent": source.vale_municipal_distribution_median_percent,
                "rs_municipal_distribution_median_2025_percent": source.rs_municipal_distribution_median_percent,
                "municipal_distribution_median_role": "context_only_not_aggregate_rate",
                "vale_rs_direction_claim_allowed": False,
                "small_denominator_status": "SMALL_DENOMINATOR_RULE_UNAVAILABLE",
                "stability_status": "STABILITY_NOT_VERIFIABLE",
                "automatic_series_approval_allowed": False,
                "series_inclusion_status": inclusion,
                "series_inclusion_or_exclusion_reason": reason,
                "monitoring_indicator": (
                    f"taxa oficial de distorção idade-série da rede total em {source.stage}, acompanhada anualmente"
                ),
                "planning_question": _distortion_question(
                    source.municipality_name, source.stage, values, persistence
                ),
                "administrative_dependency_is_analytic_dimension": False,
                "causal_interpretation_allowed": False,
            }
        )
    result = pd.DataFrame(rows)
    validate_unique_key(
        result,
        ["municipality_ibge_code", "stage", "indicator", "recent_period"],
        label="matriz de distorção H2 corrigida",
    )
    return result


def build_stability_qa() -> dict[str, Any]:
    return {
        "schemaVersion": "vocacoes-pne-v7-job5b-stability-qa-v1",
        "auditRuleDeclaredBeforeCorrectedResultReading": True,
        "acceptedExactGrain": [
            "municipality_ibge_code",
            "year",
            "stage",
            "indicator",
            "network_scope=total_all_dependencies",
        ],
        "acceptedDenominatorDefinition": (
            "explicit denominator used by the official H2 rate at the exact accepted grain"
        ),
        "rejectedSubstitutes": [
            {
                "source": "public/data/educacao/municipios/4313375.json",
                "candidate": "Censo Escolar enrollment by year and stage",
                "reason": "enrollment is not the explicit denominator of the official rate",
            },
            {
                "source": "public/data/educacao/visao-geral-municipal/4313375.json",
                "candidate": "numerator/denominator fields from enrollment shares",
                "reason": "fields belong to other indicators and not to H2 rates",
            },
            {
                "source": "population or administrative-network totals",
                "candidate": "approximate denominator",
                "reason": "approximation explicitly forbidden by the correction contract",
            },
        ],
        "inspectedLocalMaterializedSources": [
            {
                "path": ".tmp/vocacoes-pne/v7-job2/2a/trajetoria_municipal.csv.gz",
                "finding": "rates and availability only; no numerator or denominator columns",
            },
            {
                "path": ".tmp/vocacoes-pne/v7-job2/2a/trajetoria_comparacoes.csv.gz",
                "finding": "municipal distribution statistics only; no compatible aggregate numerator or denominator",
            },
            {
                "path": ".tmp/vocacoes-pne/v7-job5a/total_network_qa.csv.gz",
                "finding": "component_rate_denominators_available=false for all 1240 rows",
            },
            {
                "path": "public/data/educacao/visao-geral-municipal/4313375.json",
                "sha256": LOCAL_DENOMINATOR_AUDIT_HASHES[
                    "public/data/educacao/visao-geral-municipal/4313375.json"
                ],
                "finding": "H2 block exposes official percentages without numerator or denominator",
            },
            {
                "path": "public/data/educacao/municipios/4313375.json",
                "sha256": LOCAL_DENOMINATOR_AUDIT_HASHES[
                    "public/data/educacao/municipios/4313375.json"
                ],
                "finding": "H2 series expose values; enrollment series are a non-compatible substitute",
            },
        ],
        "relevantMaterializedDataFilesFoundByDirectedFilenameSearch": [
            ".tmp/vocacoes-pne/v7-job2/2a/trajetoria_municipal.csv.gz",
            ".tmp/vocacoes-pne/v7-job2/2a/trajetoria_comparacoes.csv.gz",
            ".tmp/vocacoes-pne/v7-job5a/total_network_qa.csv.gz",
        ],
        "exactDenominatorFound": False,
        "smallDenominatorRule": "SMALL_DENOMINATOR_RULE_UNAVAILABLE",
        "stabilityStatus": "STABILITY_NOT_VERIFIABLE",
        "automaticSeriesApprovalAllowed": False,
        "c5FullyMet": False,
        "databaseUsed": False,
        "networkUsed": False,
    }


def build_c1_c12() -> pd.DataFrame:
    statuses = {
        "C1": ("MET", "questions concern annual municipal school-flow routines"),
        "C2": ("MET", "every question names municipality, stage, period and observed movement"),
        "C3": ("MET", "official total_all_dependencies rates only"),
        "C4": ("MET", "two transitions across 2023-2025 are retained"),
        "C5": (
            "NOT_FULLY_MET",
            "exact rate denominator unavailable; stability is not verifiable",
        ),
        "C6": (
            "MET_CORRECTED_FAMILY_LEVEL",
            "approval, failure and dropout integrated once per municipality-stage-period",
        ),
        "C7": (
            "MET_FROZEN_PEERS_ONLY",
            "frozen peers support claims; Vale/RS aggregate rates remain unavailable",
        ),
        "C8": (
            "MET_CORRECTED_NOT_APPLICABLE",
            "distortion evaluated independently of performance-family closure",
        ),
        "C9": ("MET", "no causal or same-student transition inference"),
        "C10": ("MET", "all sources, hashes, grains and inclusion decisions are recorded"),
        "C11": ("MET", "outputs are internal staging facts only"),
        "C12": ("MET", "package stops for GPT-5.6 Pro external judgment"),
    }
    rows = [
        {
            "front_id": "H2_TRAJETORIA_MUNICIPAL_V2",
            "evaluation_type": "job5b_corrected_internal_evidence",
            "criterion_id": criterion_id,
            "criterion_name": CRITERIA[criterion_id],
            "status": statuses[criterion_id][0],
            "evidence_or_limitation": statuses[criterion_id][1],
            "creates_automatic_candidate": False,
            "external_judgment_required": True,
        }
        for criterion_id in sorted(CRITERIA, key=lambda value: int(value[1:]))
    ]
    result = pd.DataFrame(rows)
    validate_unique_key(result, ["front_id", "criterion_id"], label="C1-C12 Job 5B")
    return result


def _limitations() -> dict[str, Any]:
    return {
        "schemaVersion": "vocacoes-pne-v7-job5b-limitations-v1",
        "executionBlockingFailureCount": 0,
        "evaluationBlockingItems": [
            {
                "code": "SMALL_DENOMINATOR_RULE_UNAVAILABLE",
                "effect": "no automatic series approval; C5 is not fully met",
            },
            {
                "code": "STABILITY_NOT_VERIFIABLE",
                "effect": "H2 result state is NOT_EVALUABLE_DUE_TO_DATA_OR_QA_LIMIT",
            },
        ],
        "nonBlockingComparisonLimits": [
            {
                "code": "H2_VALE_AGGREGATE_RATE_UNAVAILABLE",
                "effect": "no direction claim versus Vale do Sinos",
            },
            {
                "code": "H2_RS_AGGREGATE_RATE_UNAVAILABLE",
                "effect": "no direction claim versus RS",
            },
            {
                "code": "MUNICIPAL_DISTRIBUTION_MEDIAN_NOT_AGGREGATE_RATE",
                "effect": "median retained only as labeled context for distortion",
            },
        ],
        "forbiddenInferencesPreserved": [
            "causal interpretation",
            "same students moving among approval, failure and dropout",
            "administrative dependency as analytic dimension",
            "approximate enrollment or population as H2 denominator",
        ],
    }


def _artifact_metadata(
    root: Path, frames: Mapping[str, pd.DataFrame], paths: Sequence[str]
) -> list[dict[str, Any]]:
    specs = {
        "h2_family_level_matrix.csv.gz": (
            ["municipality_ibge_code", "stage", "recent_period", "performance_family"],
            "2023-2025",
            "percent and joint classification",
        ),
        "h2_distortion_corrected_matrix.csv.gz": (
            ["municipality_ibge_code", "stage", "indicator", "recent_period"],
            "2023-2025",
            "percent and inclusion state",
        ),
        "h2_stability_qa.json": ("stability audit", "Job 5B", "QA state"),
        "nova_santa_rita_h2_corrected.json": (
            "Nova Santa Rita corrected H2",
            "2023-2025",
            "percent and internal facts",
        ),
        "h2_corrected_internal_synthesis.json": (
            "corrected H2 front",
            "Job 5B",
            "evaluation state",
        ),
        "h2_corrected_c1_c12_evidence.csv.gz": (
            ["front_id", "criterion_id"],
            "Job 5B",
            "criterion state",
        ),
        "external_review_package_job5b.json": (
            "Job 5B external package",
            "Job 5B",
            "internal evidence",
        ),
        "limitations_job5b.json": ("limitations", "Job 5B", "availability state"),
        "output_inventory_job5b.json": (
            "artifact inventory",
            "Job 5B",
            "file metadata",
        ),
    }
    records = []
    for relative in paths:
        grain, period, unit = specs[relative]
        records.append(
            artifact_record(
                root=root,
                path=root / relative,
                frame=frames.get(relative),
                subjob="5B",
                grain=grain,
                period=period,
                lens="school_location" if relative.startswith("h2_") else "internal",
                unit=unit,
                aggregation_rule=(
                    "official total rates; integrated performance family; no mean of rates"
                ),
            )
        )
    return records


def _validate_staging(root: Path) -> dict[str, Any]:
    actual = sorted(path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file())
    if actual != sorted(OUTPUT_FILES):
        raise ValueError(f"Conjunto de outputs Job 5B divergente: {actual}.")
    manifest = _load_json(root / "manifest_job5b.json")
    for artifact in manifest["artifacts"]:
        path = root / artifact["path"]
        if not path.is_file() or path.stat().st_size != artifact["byteSize"]:
            raise ValueError(f"Output ausente ou tamanho divergente: {artifact['path']}.")
        if sha256_file(path) != artifact["sha256"]:
            raise ValueError(f"Hash divergente: {artifact['path']}.")
    family = pd.read_csv(
        root / "h2_family_level_matrix.csv.gz",
        dtype={"municipality_ibge_code": "string"},
    )
    distortion = pd.read_csv(
        root / "h2_distortion_corrected_matrix.csv.gz",
        dtype={"municipality_ibge_code": "string"},
    )
    c12 = pd.read_csv(root / "h2_corrected_c1_c12_evidence.csv.gz")
    validate_unique_key(
        family,
        ["municipality_ibge_code", "stage", "recent_period", "performance_family"],
        label="família serializada",
    )
    validate_unique_key(
        distortion,
        ["municipality_ibge_code", "stage", "indicator", "recent_period"],
        label="distorção serializada",
    )
    validate_unique_key(c12, ["front_id", "criterion_id"], label="C1-C12 serializado")
    if len(family) != 40 or len(distortion) != 40 or len(c12) != 12:
        raise ValueError("Contagens finais Job 5B divergentes.")
    for frame in (family, distortion):
        if frame["municipality_ibge_code"].nunique() != 10:
            raise ValueError("Output Job 5B não cobre dez municípios.")
        if NOVA_SANTA_RITA_ID not in set(frame["municipality_ibge_code"]):
            raise ValueError("Nova Santa Rita ausente do Job 5B.")
        if frame["automatic_series_approval_allowed"].astype(str).str.lower().ne("false").any():
            raise ValueError("Série foi aprovada automaticamente sem estabilidade verificável.")
    if set(distortion["performance_family_closure_status"]) != {"NOT_APPLICABLE"}:
        raise ValueError("Distorção voltou a exigir fechamento da família de rendimento.")
    stability = _load_json(root / "h2_stability_qa.json")
    if stability["exactDenominatorFound"] or stability["c5FullyMet"]:
        raise ValueError("QA de estabilidade contradiz a auditoria local.")
    synthesis = _load_json(root / "h2_corrected_internal_synthesis.json")
    if synthesis["resultState"] != RESULT_STATE:
        raise ValueError("Estado interno H2 divergente.")
    return {
        "schemaValidation": "PASS",
        "outputCount": len(actual),
        "familyRows": len(family),
        "distortionRows": len(distortion),
        "c1C12Rows": len(c12),
        "resultState": synthesis["resultState"],
    }


def materialize(output_root: Path = DEFAULT_OUTPUT_ROOT) -> dict[str, Any]:
    output_root = output_root.resolve()
    assert_outside_public_data(output_root, REPO_ROOT)
    contract = verify_frozen_inputs()
    h2 = _read_h2()
    family = build_family_matrix(h2)
    distortion = build_distortion_matrix(h2)
    stability = build_stability_qa()
    c1_c12 = build_c1_c12()

    nova_family = family[family["municipality_ibge_code"] == NOVA_SANTA_RITA_ID]
    nova_distortion = distortion[
        distortion["municipality_ibge_code"] == NOVA_SANTA_RITA_ID
    ]
    nova_medio = nova_family[nova_family["stage"] == "medio"]
    if len(nova_medio) != 1:
        raise ValueError("Família do ensino médio de Nova Santa Rita ausente.")
    nova_payload = {
        "schemaVersion": "vocacoes-pne-v7-job5b-nova-santa-rita-h2-v1",
        "municipalityId": NOVA_SANTA_RITA_ID,
        "municipalityName": "Nova Santa Rita",
        "resultState": RESULT_STATE,
        "highSchoolIntegratedFamily": _json_safe(nova_medio.iloc[0].to_dict()),
        "allFamilyRows": _json_safe(nova_family.to_dict(orient="records")),
        "distortionRows": _json_safe(nova_distortion.to_dict(orient="records")),
        "automaticApprovalAllowed": False,
        "sameStudentTransitionInferenceAllowed": False,
    }
    retained_distortion = int(
        distortion["series_inclusion_status"]
        .eq("INTERNAL_FACT_RETAINED_STABILITY_NOT_VERIFIABLE")
        .sum()
    )
    synthesis = {
        "schemaVersion": "vocacoes-pne-v7-job5b-h2-synthesis-v1",
        "frontId": "H2_TRAJETORIA_MUNICIPAL_V2",
        "resultState": RESULT_STATE,
        "familyRowCount": len(family),
        "distortionSeriesCount": len(distortion),
        "distortionInternalFactsRetainedCount": retained_distortion,
        "distortionSeriesExcludedFromPassRuleCount": len(distortion) - retained_distortion,
        "corrections": {
            "distortionPerformanceClosureStatus": "NOT_APPLICABLE",
            "performanceFamilyIntegrated": True,
            "exactDenominatorFound": False,
            "planningQuestionsGroundedInObservedMovements": True,
        },
        "requirements": [
            {"requirement": "canonical_total_network_scope", "met": True},
            {"requirement": "multi_year_persistence", "met": True},
            {"requirement": "performance_family_integration", "met": True},
            {"requirement": "distortion_rule_separated", "met": True},
            {"requirement": "frozen_peer_support_only", "met": True},
            {"requirement": "specific_grounded_questions", "met": True},
            {"requirement": "exact_denominator_and_small_denominator_QA", "met": False},
        ],
        "c5FullyMet": False,
        "stabilityStatus": "STABILITY_NOT_VERIFIABLE",
        "automaticSeriesApprovalAllowed": False,
        "approvalDecisionMade": False,
        "approvalDecisionReservedForExternalReviewer": True,
        "externalReviewer": "GPT-5.6 Pro",
    }
    limitations = _limitations()
    external_package = {
        "schemaVersion": "vocacoes-pne-v7-job5b-external-review-package-v1",
        "jobId": JOB_ID,
        "verdict": "JOB_5B_COMPLETED_FOR_EXTERNAL_JUDGMENT",
        "frontState": RESULT_STATE,
        "scope": contract["scope"],
        "externalJudgmentBlockersAddressed": contract["externalJudgment"]["blockers"],
        "stabilityQA": stability,
        "novaSantaRita": nova_payload,
        "artifactReferences": {
            "familyMatrix": "h2_family_level_matrix.csv.gz",
            "distortionMatrix": "h2_distortion_corrected_matrix.csv.gz",
            "criteria": "h2_corrected_c1_c12_evidence.csv.gz",
            "synthesis": "h2_corrected_internal_synthesis.json",
            "limitations": "limitations_job5b.json",
        },
        "editorialApprovalMade": False,
        "pilotGate11Started": False,
        "stopForExternalJudgment": True,
    }

    staging = staging_directory_for(output_root)
    try:
        write_csv_gzip(staging / "h2_family_level_matrix.csv.gz", family)
        write_csv_gzip(staging / "h2_distortion_corrected_matrix.csv.gz", distortion)
        write_json(staging / "h2_stability_qa.json", stability)
        write_json(staging / "nova_santa_rita_h2_corrected.json", nova_payload)
        write_json(staging / "h2_corrected_internal_synthesis.json", synthesis)
        write_csv_gzip(staging / "h2_corrected_c1_c12_evidence.csv.gz", c1_c12)
        write_json(staging / "external_review_package_job5b.json", external_package)
        write_json(staging / "limitations_job5b.json", limitations)

        frames = {
            "h2_family_level_matrix.csv.gz": family,
            "h2_distortion_corrected_matrix.csv.gz": distortion,
            "h2_corrected_c1_c12_evidence.csv.gz": c1_c12,
        }
        first_paths = OUTPUT_FILES[:8]
        first_artifacts = _artifact_metadata(staging, frames, first_paths)
        inventory = {
            "schemaVersion": "vocacoes-pne-v7-job5b-output-inventory-v1",
            "jobId": JOB_ID,
            "artifactCount": len(first_artifacts),
            "artifacts": first_artifacts,
        }
        write_json(staging / "output_inventory_job5b.json", inventory)
        manifest_artifacts = _artifact_metadata(staging, frames, OUTPUT_FILES[:9])
        manifest = {
            "schemaVersion": "vocacoes-pne-v7-job5b-operational-manifest-v1",
            "jobId": JOB_ID,
            "classification": "DATA_LOGIC",
            "verdict": "JOB_5B_COMPLETED_FOR_EXTERNAL_JUDGMENT",
            "frontState": RESULT_STATE,
            "scope": contract["scope"],
            "sourceFingerprints": {
                "job5a": JOB5A_HASHES,
                "denominatorAuditLocalFiles": LOCAL_DENOMINATOR_AUDIT_HASHES,
                "externalJudgmentBriefSha256": contract["externalJudgment"]["sha256"],
                "contractSha256": sha256_file(CONTRACT_PATH),
                "coreSha256": sha256_file(CORE_PATH),
                "launcherSha256": sha256_file(LAUNCHER_PATH),
            },
            "summary": {
                "outputCount": len(OUTPUT_FILES),
                "manifestSelfExcludedFromArtifactHashes": True,
                "artifactHashCount": len(manifest_artifacts),
                "familyRowCount": len(family),
                "distortionSeriesCount": len(distortion),
                "c1C12RowCount": len(c1_c12),
                "exactDenominatorFound": False,
                "c5FullyMet": False,
            },
            "generation": {
                "deterministic": True,
                "transactional": True,
                "partialPromotionAllowed": False,
                "clockUsed": False,
                "databaseUsed": False,
                "networkUsed": False,
                "fullBuildUsed": False,
                "frontendChanged": False,
                "publicDataChanged": False,
                "job5aArtifactsChanged": False,
                "a4OrA3Rerun": False,
                "roundingAppliedToCalculations": False,
            },
            "artifacts": manifest_artifacts,
            "stopForExternalJudgment": True,
            "externalReviewer": "GPT-5.6 Pro",
        }
        write_json(staging / "manifest_job5b.json", manifest)
        validation = _validate_staging(staging)
        promotion = replace_directory_transactionally(staging, output_root)
    except Exception:
        if staging.exists():
            import shutil

            shutil.rmtree(staging)
        raise
    return {
        "verdict": "JOB_5B_COMPLETED_FOR_EXTERNAL_JUDGMENT",
        "outputDirectory": output_root.as_posix(),
        "operationalManifestSha256": sha256_file(output_root / "manifest_job5b.json"),
        "promotion": promotion,
        **validation,
    }


def validate_existing_output(output_root: Path = DEFAULT_OUTPUT_ROOT) -> dict[str, Any]:
    output_root = output_root.resolve()
    assert_outside_public_data(output_root, REPO_ROOT)
    verify_frozen_inputs()
    validation = _validate_staging(output_root)
    return {
        "verdict": "JOB_5B_COMPLETED_FOR_EXTERNAL_JUDGMENT",
        "outputDirectory": output_root.as_posix(),
        "operationalManifestSha256": sha256_file(output_root / "manifest_job5b.json"),
        "promotion": "validated_existing",
        **validation,
    }
