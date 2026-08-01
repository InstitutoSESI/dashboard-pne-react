from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Any, Iterable, Mapping

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_PIPELINE_DIR = REPO_ROOT / "data_pipeline"
PUBLIC_DATA_DIR = (REPO_ROOT / "public" / "data").resolve()
if str(DATA_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_PIPELINE_DIR))

from src.pne.diagnostic_presentation_policy import POLICY  # noqa: E402
from src.pne.goal_indicator_contract import CONTRACT  # noqa: E402
from src.data_loader import (  # noqa: E402
    load_ept_nivel_medio_data,
    load_medio_tecnico_articulado_data,
)
from src.medio_tecnico_articulado import (  # noqa: E402
    calculate_medio_tecnico_articulado_series,
    calculate_public_expansion_series,
    calculate_subsequent_expansion_series,
)
from src.pne_goal_11b_census import (  # noqa: E402
    load_snapshot as load_goal_11b_snapshot,
    ratio_result as goal_11b_ratio_result,
    state_ratio as goal_11b_state_ratio,
)
from src.child_literacy import (  # noqa: E402
    current_results as child_literacy_current_results,
    load_snapshot as load_child_literacy_snapshot,
)
from src.pne_goal_11d import (  # noqa: E402
    current_results as goal_11d_current_results,
    load_snapshot as load_goal_11d_snapshot,
)
from src.pne_goal_14_census import (  # noqa: E402
    load_snapshot as load_goal_14_snapshot,
)
from src.pne_goal_15b import (  # noqa: E402
    load_snapshot as load_goal_15b_snapshot,
)
from src.pne2026_public_diagnostic_v3 import (  # noqa: E402
    CONTRACT_HASH,
    PRESENTATION_POLICY_HASH,
    PRESENTATION_POLICY_VERSION,
    PUBLIC_V3_SCHEMA_VERSION,
    rebase_pne2026_public_diagnostic_v3,
)
from src.pne_macro_round import (  # noqa: E402
    MACRO_RELATION_IDS,
    SOURCE_PATHS as MACRO_SOURCE_PATHS,
    build_macro_round_results,
    load_macro_source_records,
)


MANIFEST_SCHEMA_VERSION = "pne2026-public-diagnostic-v3-manifest-v3"
EXPECTED_MUNICIPALITIES = 497
PUBLIC_V3_DIR = PUBLIC_DATA_DIR / "pne2026-diagnostic-v3"
SPECIAL_EDUCATION_DIR = PUBLIC_DATA_DIR / "educacao" / "educacao-especial"
HIGHER_EDUCATION_DIR = PUBLIC_DATA_DIR / "educacao" / "superior"
CONSOLIDATED_ROUND_RELATION_IDS = frozenset(
    {
        "relation.3.a.alfabetizacao",
        "relation.11.d.eja_atendimento_18_mais",
        "relation.14.a.graduacao_frequencia_18_24",
        "relation.14.b.superior_completo_25_34",
        "relation.14.d.taxa_bruta_graduacao",
        "relation.15.b.docentes_tempo_integral_ies",
        "relation.15.b.docentes_tempo_integral_universidades",
        "relation.15.b.docentes_tempo_integral_centros_universitarios",
        "relation.15.b.docentes_tempo_integral_faculdades",
    }
)
PACKAGE_RELATION_IDS = frozenset(MACRO_RELATION_IDS) | CONSOLIDATED_ROUND_RELATION_IDS
TRACKING_ROUND_RELATION_IDS = frozenset(
    {
        "relation.4.a.basico_15_17",
        "relation.4.b.idade_regular_quinto",
        "relation.4.c.idade_regular_nono",
        "relation.4.d.idade_regular_medio",
        "relation.10.b.aee_oferta_escolas_elegiveis",
        "relation.8.b.salas_climatizadas",
        "relation.19.c.salas_acessiveis",
        "relation.18.b.conselho_escolar",
        "relation.9.d.educacao_indigena_cobertura_estimada_4_17",
        "relation.12.a.medio_tecnico_articulado_percentual",
        "relation.17.c.munic_planos_carreira_declarados",
        "relation.18.c.munic_forum_educacao_declarado",
        "relation.14.a.graduacao_frequencia_18_24",
        "relation.14.b.superior_completo_25_34",
        "relation.15.b.docentes_tempo_integral_universidades",
        "relation.15.b.docentes_tempo_integral_centros_universitarios",
        "relation.15.b.docentes_tempo_integral_faculdades",
    }
)
PROJECTION_MIGRATION_RELATION_IDS = frozenset(
    {
        "relation.1.a.creche",
        "relation.1.c.pre_escola",
        "relation.4.a.basico_6_17",
    }
)

_POLICY_BY_RELATION_ID = {
    entry["relationId"]: entry for entry in POLICY["relations"]
}


class WorktreeSnapshot:
    """Leitor uniforme das entradas correntes, sem depender do estado do Git."""

    def __enter__(self) -> "WorktreeSnapshot":
        return self

    def read_bytes(self, path: str) -> bytes:
        source = (REPO_ROOT / path).resolve()
        try:
            source.relative_to(REPO_ROOT.resolve())
        except ValueError as exc:
            raise ValueError(f"Entrada fora do repositório: {path}.") from exc
        return source.read_bytes()

    def read_json(self, path: str) -> dict[str, Any]:
        payload = json.loads(self.read_bytes(path))
        if not isinstance(payload, dict):
            raise TypeError(f"{self.ref}:{path} não contém objeto JSON.")
        return payload

    def __exit__(self, *_: Any) -> None:
        return None


def _serialized(payload: Mapping[str, Any]) -> bytes:
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


def _aggregate_hash(blocks: Iterable[tuple[str, bytes]]) -> str:
    digest = hashlib.sha256()
    for relative_path, block in sorted(blocks):
        identifier = relative_path.replace("\\", "/").encode("utf-8")
        digest.update(len(identifier).to_bytes(4, "big"))
        digest.update(identifier)
        digest.update(len(block).to_bytes(8, "big"))
        digest.update(block)
    return digest.hexdigest()


def _release_identity_block() -> tuple[str, bytes]:
    return (
        "__release_identity__.json",
        _serialized(
            {
                "sourceManifestSchema": MANIFEST_SCHEMA_VERSION,
                "diagnosticSchemaVersion": PUBLIC_V3_SCHEMA_VERSION,
                "contractVersion": CONTRACT["contractVersion"],
                "contractHash": CONTRACT_HASH,
                "presentationPolicyVersion": PRESENTATION_POLICY_VERSION,
                "presentationPolicyHash": PRESENTATION_POLICY_HASH,
            }
        ),
    )


def _update_aggregate_digest(
    digest: Any,
    relative_path: str,
    block: bytes,
) -> None:
    identifier = relative_path.replace("\\", "/").encode("utf-8")
    digest.update(len(identifier).to_bytes(4, "big"))
    digest.update(identifier)
    digest.update(len(block).to_bytes(8, "big"))
    digest.update(block)


def _load_json_bytes(content: bytes, label: str) -> dict[str, Any]:
    def reject_constant(value: str) -> None:
        raise ValueError(f"{label} contém constante JSON inválida: {value}.")

    payload = json.loads(content, parse_constant=reject_constant)
    if not isinstance(payload, dict):
        raise TypeError(f"{label} não contém objeto JSON.")
    return payload


def _read_worktree_json(path: Path) -> tuple[dict[str, Any], bytes]:
    content = path.read_bytes()
    return _load_json_bytes(content, str(path)), content


def _active_release() -> tuple[dict[str, Any], dict[str, Any], Path]:
    current, _ = _read_worktree_json(PUBLIC_V3_DIR / "current.json")
    release_id = str(current.get("releaseId") or "")
    if (
        len(release_id) != 64
        or any(character not in "0123456789abcdef" for character in release_id)
    ):
        raise RuntimeError("current.json contém releaseId inválido.")
    expected_manifest_path = f"releases/{release_id}/manifest.json"
    if current.get("manifestPath") != expected_manifest_path:
        raise RuntimeError("current.json não aponta para o manifesto confinado.")
    release_root = PUBLIC_V3_DIR / "releases" / release_id
    manifest, _ = _read_worktree_json(release_root / "manifest.json")
    if (
        manifest.get("aggregateHash") != current.get("aggregateHash")
        or manifest.get("municipalityCount") != EXPECTED_MUNICIPALITIES
    ):
        raise RuntimeError("Release ativa diverge do current.json.")
    files = list((release_root / "municipios").glob("*.json"))
    if len(files) != EXPECTED_MUNICIPALITIES:
        raise RuntimeError("Release ativa não contém 497 arquivos municipais.")
    return current, manifest, release_root


def _materialization_indexes() -> tuple[
    dict[str, Any],
    bytes,
    dict[str, Any],
    bytes,
]:
    special, special_bytes = _read_worktree_json(
        SPECIAL_EDUCATION_DIR / "index.json"
    )
    higher, higher_bytes = _read_worktree_json(
        HIGHER_EDUCATION_DIR / "index.json"
    )
    if (
        special.get("schemaVersion") != "special-education-v1"
        or special.get("municipalityCount") != EXPECTED_MUNICIPALITIES
        or special.get("fileCount") != EXPECTED_MUNICIPALITIES
    ):
        raise RuntimeError("Materialização de Educação Especial incompleta.")
    if (
        higher.get("schemaVersion") != 1
        or higher.get("municipalityCount") != EXPECTED_MUNICIPALITIES
    ):
        raise RuntimeError("Materialização de Educação Superior incompleta.")
    return special, special_bytes, higher, higher_bytes


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def validate_staging_output_path(output_dir: Path) -> Path:
    resolved = output_dir.expanduser().resolve()
    if resolved == PUBLIC_DATA_DIR or _is_within(resolved, PUBLIC_DATA_DIR):
        raise ValueError("A saída V3 em public/data é bloqueada nesta rodada.")
    if resolved == REPO_ROOT.resolve():
        raise ValueError("A raiz do repositório não pode ser usada como staging.")
    return resolved


def _registry(snapshot: WorktreeSnapshot) -> list[dict[str, Any]]:
    registry = snapshot.read_json("public/data/municipios_index.json")
    entries = list(registry.get("municipios") or [])
    if (
        registry.get("total_municipios") != EXPECTED_MUNICIPALITIES
        or len(entries) != EXPECTED_MUNICIPALITIES
    ):
        raise RuntimeError("O registro versionado não contém 497 municípios.")
    entries.sort(key=lambda item: str(item["id_municipio"]))
    identifiers = [str(item["id_municipio"]) for item in entries]
    if len(set(identifiers)) != EXPECTED_MUNICIPALITIES:
        raise RuntimeError("O registro versionado contém códigos IBGE duplicados.")
    return entries


def _build_manifest(
    payloads: list[dict[str, Any]],
    municipal_files: Mapping[str, bytes],
    duplicate_count: int,
) -> dict[str, Any]:
    result_counts = [len(payload["results"]) for payload in payloads]
    mode_counts: Counter[str] = Counter()
    classifications: Counter[str] = Counter()
    priorities: Counter[str] = Counter()
    data_statuses: Counter[str] = Counter()
    reference_kinds: Counter[str] = Counter()
    above_100_by_unit: Counter[str] = Counter()
    for payload in payloads:
        summary = payload["summary"]
        mode_counts["progress"] += summary["progressResultCount"]
        mode_counts["tracking"] += summary["trackingResultCount"]
        mode_counts["complementary"] += summary["complementaryResultCount"]
        classifications.update(summary["classificationCounts"])
        priorities.update(summary["presentationPriorityCounts"])
        data_statuses.update(summary["dataStatusCounts"])
        reference_kinds["legal"] += summary["legalReferenceResultCount"]
        reference_kinds["monitoring"] += summary["monitoringReferenceResultCount"]
        for result in payload["results"]:
            if (
                isinstance(result.get("value"), (int, float))
                and not isinstance(result.get("value"), bool)
                and result["value"] > 100
            ):
                unit = CONTRACT["indicators"][result["indicatorId"]]["unit"]
                above_100_by_unit[unit] += 1
    eligible_relations = [
        relation
        for relation in CONTRACT["relations"]
        if relation["mode"] != "hidden"
        and relation.get("includeInDiagnostic") is True
        and relation["relationId"] in _POLICY_BY_RELATION_ID
    ]
    eligible_modes = Counter(
        relation["mode"] for relation in eligible_relations
    )
    eligible_priorities = Counter(
        _POLICY_BY_RELATION_ID[relation["relationId"]]["summaryPriority"]
        for relation in eligible_relations
    )
    return {
        "schemaVersion": MANIFEST_SCHEMA_VERSION,
        "diagnosticSchemaVersion": PUBLIC_V3_SCHEMA_VERSION,
        "contractVersion": CONTRACT["contractVersion"],
        "contractHash": CONTRACT_HASH,
        "presentationPolicyVersion": PRESENTATION_POLICY_VERSION,
        "presentationPolicyHash": PRESENTATION_POLICY_HASH,
        "expectedMunicipalityCount": EXPECTED_MUNICIPALITIES,
        "generatedMunicipalityCount": len(payloads),
        "totalResultCount": sum(result_counts),
        "modeCounts": {
            key: mode_counts[key]
            for key in ("progress", "tracking", "complementary")
        },
        "referenceKindCounts": {
            "legal": reference_kinds["legal"],
            "monitoring": reference_kinds["monitoring"],
        },
        "dataStatusCounts": {
            key: data_statuses[key]
            for key in ("available", "unavailable", "not_applicable", "suppressed")
        },
        "classificationCounts": {
            key: classifications[key]
            for key in ("advance", "maintain", "unclassified")
        },
        "presentationPriorityCounts": {
            key: priorities[key] for key in ("essential", "standard")
        },
        "eligibleRelationCounts": {
            "visible": len(eligible_relations),
            "progress": eligible_modes["progress"],
            "tracking": eligible_modes["tracking"],
            "complementary": eligible_modes["complementary"],
            "essential": eligible_priorities["essential"],
            "standard": eligible_priorities["standard"],
        },
        "minimumResultsPerMunicipality": min(result_counts, default=0),
        "maximumResultsPerMunicipality": max(result_counts, default=0),
        "percentValuesAbove100Count": above_100_by_unit["percent"],
        "countValuesAbove100Count": above_100_by_unit["count"],
        "hiddenExcludedCount": 0,
        "invalidFileCount": 0,
        "duplicateRelationCount": duplicate_count,
        "orphanFileCount": 0,
        "generationHash": _aggregate_hash(
            [*municipal_files.items(), _release_identity_block()]
        ),
    }


def _assert_manifest_invariants(manifest: Mapping[str, Any]) -> None:
    if manifest.get("generatedMunicipalityCount") != EXPECTED_MUNICIPALITIES:
        raise RuntimeError("O staging V3 não contém os 497 municípios.")
    for field in (
        "invalidFileCount",
        "duplicateRelationCount",
        "orphanFileCount",
    ):
        if manifest.get(field) != 0:
            raise RuntimeError(
                f"Manifesto V3 inválido em {field}: {manifest.get(field)!r}."
            )
    minimum = manifest.get("minimumResultsPerMunicipality")
    maximum = manifest.get("maximumResultsPerMunicipality")
    if (
        not isinstance(minimum, int)
        or not isinstance(maximum, int)
        or minimum <= 0
        or minimum > maximum
    ):
        raise RuntimeError("Distribuição municipal de resultados V3 inválida.")


def _latest_rows(frame: pd.DataFrame) -> dict[str, pd.Series]:
    if frame.empty:
        return {}
    ordered = frame.sort_values(["id_municipio", "ano"])
    return {
        str(row["id_municipio"]): row
        for _, row in ordered.groupby("id_municipio", sort=True).tail(1).iterrows()
    }


def _status_payload(
    row: pd.Series,
    *,
    target: float | None,
    public_reading: str,
) -> dict[str, Any]:
    data_status = str(row.get("data_status") or "available")
    result: dict[str, Any] = {
        "dataStatus": data_status,
        "year": int(row["ano"]),
        "value": None,
    }
    reason_code = row.get("reason_code")
    if reason_code:
        result["reasonCode"] = str(reason_code)
    value = row.get("valor")
    if data_status != "available" or pd.isna(value):
        return result
    result["value"] = float(value)
    for source, destination in (
        ("numerador", "numerator"),
        ("denominador", "denominator"),
    ):
        numeric = row.get(source)
        if pd.notna(numeric):
            result[destination] = float(numeric)
    result["publicReading"] = public_reading
    if target is not None:
        distance = float(value) - target
        result.update(
            {
                "distance": distance,
                "classification": "maintain" if distance >= 0 else "advance",
                "status": (
                    "Atinge a referência no momento"
                    if distance >= 0
                    else "Ainda não atinge a referência"
                ),
            }
        )
    return result


def _methodology_results() -> tuple[
    dict[str, dict[str, dict[str, Any]]],
    dict[str, Any],
]:
    articulated_source = load_medio_tecnico_articulado_data()
    ept_source = load_ept_nivel_medio_data()
    articulated = calculate_medio_tecnico_articulado_series(articulated_source)
    public_expansion = calculate_public_expansion_series(ept_source)
    subsequent_expansion = calculate_subsequent_expansion_series(ept_source)

    articulated_rows = _latest_rows(articulated)
    public_rows = _latest_rows(public_expansion)
    subsequent_rows = _latest_rows(subsequent_expansion)
    municipality_ids = sorted(
        set(articulated_rows) | set(public_rows) | set(subsequent_rows)
    )
    by_municipality: dict[str, dict[str, dict[str, Any]]] = {}
    absence_reasons: Counter[str] = Counter()
    observed_by_relation: Counter[str] = Counter()

    for municipality_id in municipality_ids:
        municipal: dict[str, dict[str, Any]] = {}
        articulated_row = articulated_rows.get(municipality_id)
        if articulated_row is not None:
            denominator = articulated_row["mat_medio"]
            value = articulated_row["percentual_calculado"]
            if pd.isna(value):
                data_status = (
                    "not_applicable"
                    if pd.notna(denominator) and float(denominator) == 0
                    else "unavailable"
                )
                reason_code = (
                    "denominator_zero"
                    if data_status == "not_applicable"
                    else "required_component_unavailable"
                )
                row = articulated_row.copy()
                row["data_status"] = data_status
                row["reason_code"] = reason_code
                row["valor"] = pd.NA
                row["numerador"] = pd.NA
                row["denominador"] = denominator
            else:
                row = articulated_row.copy()
                row["data_status"] = "available"
                row["reason_code"] = None
                row["valor"] = value
                row["numerador"] = row["mat_articulado_total"]
                row["denominador"] = denominator
            municipal[
                "relation.12.a.medio_tecnico_articulado_percentual"
            ] = _status_payload(
                row,
                target=None,
                public_reading=(
                    "Matrículas integradas e concomitantes em relação ao total "
                    "de matrículas do ensino médio."
                ),
            )

        for relation_id, row, target, reading in (
            (
                "relation.12.a.medio_tecnico_participacao_publica",
                public_rows.get(municipality_id),
                50.0,
                "Participação pública na expansão líquida da EPT desde 2025.",
            ),
            (
                "relation.12.b.subsequente_expansao",
                subsequent_rows.get(municipality_id),
                60.0,
                "Expansão das matrículas subsequentes em relação à base de 2025.",
            ),
        ):
            if row is not None:
                municipal[relation_id] = _status_payload(
                    row,
                    target=target,
                    public_reading=reading,
                )

        for relation_id, result in municipal.items():
            if result["dataStatus"] == "available":
                observed_by_relation[relation_id] += 1
            else:
                absence_reasons[
                    f"{relation_id}:{result.get('reasonCode', 'unspecified')}"
                ] += 1
        by_municipality[municipality_id] = municipal

    source_years = sorted(
        {
            int(value)
            for value in pd.concat(
                [articulated_source["ano"], ept_source["ano"]],
                ignore_index=True,
            )
            .dropna()
            .tolist()
        }
    )
    audit = {
        "sourceYears": source_years,
        "latestSourceYear": max(source_years),
        "observedByRelation": dict(sorted(observed_by_relation.items())),
        "absenceReasonCounts": dict(sorted(absence_reasons.items())),
    }
    return by_municipality, audit


def _goal_11b_state_comparison(
    municipality_value: float,
    state_value: float,
    *,
    year: int,
) -> dict[str, Any]:
    difference = municipality_value - state_value
    if abs(difference) < 1e-12:
        state = "equal"
        reading = "O resultado do município coincide com o Rio Grande do Sul."
    elif difference > 0:
        state = "above"
        reading = "O resultado do município está acima do Rio Grande do Sul."
    else:
        state = "below"
        reading = "O resultado do município está abaixo do Rio Grande do Sul."
    municipal_text = f"{municipality_value:.1f}".replace(".", ",")
    state_text = f"{state_value:.1f}".replace(".", ",")
    return {
        "state": state,
        "municipalityValue": municipality_value,
        "stateValue": state_value,
        "year": year,
        "unit": "percent",
        "difference": difference,
        "favorableDifference": difference,
        "reading": reading,
        "valueReading": (
            f"O município apresenta {municipal_text}%, enquanto o Rio Grande "
            f"do Sul apresenta {state_text}%."
        ),
    }


def _goal_11b_results() -> tuple[
    dict[str, dict[str, dict[str, Any]]],
    dict[str, Any],
]:
    rows, manifest = load_goal_11b_snapshot()
    configurations = {
        "relation.11.b.fundamental_concluido_15_29": {
            "component": "fifteenToTwentyNine",
            "target": 100.0,
            "reading": (
                "Conclusão do ensino fundamental na população de 15 a 29 "
                "anos, calculada com componentes censitários de 2022."
            ),
        },
        "relation.11.b.fundamental_concluido_15_mais": {
            "component": "fifteenPlus",
            "target": 85.0,
            "reading": (
                "Conclusão do ensino fundamental na população de 15 anos ou "
                "mais, calculada com componentes censitários de 2022."
            ),
        },
    }
    state_references = {
        relation_id: goal_11b_state_ratio(rows, config["component"])
        for relation_id, config in configurations.items()
    }
    by_municipality: dict[str, dict[str, dict[str, Any]]] = {}
    absence_reasons: Counter[str] = Counter()
    for source_row in rows:
        municipality_id = str(source_row["municipalityId"])
        municipal: dict[str, dict[str, Any]] = {}
        for relation_id, config in configurations.items():
            ratio = goal_11b_ratio_result(source_row[config["component"]])
            if ratio["dataStatus"] != "available":
                absence_reasons[
                    f"{relation_id}:{ratio.get('reasonCode', 'unspecified')}"
                ] += 1
                municipal[relation_id] = ratio
                continue
            row = pd.Series(
                {
                    "ano": int(source_row["year"]),
                    "data_status": "available",
                    "valor": ratio["value"],
                    "numerador": ratio["numerator"],
                    "denominador": ratio["denominator"],
                }
            )
            result = _status_payload(
                row,
                target=float(config["target"]),
                public_reading=str(config["reading"]),
            )
            state_reference = state_references[relation_id]
            result["stateComparison"] = _goal_11b_state_comparison(
                float(result["value"]),
                float(state_reference["value"]),
                year=int(source_row["year"]),
            )
            municipal[relation_id] = result
        by_municipality[municipality_id] = municipal
    return by_municipality, {
        "sourceSnapshotSchema": manifest["schemaVersion"],
        "sourceReferenceDate": manifest["sourceReferenceDate"],
        "coverage": manifest["coverage"],
        "reconciliation": manifest["reconciliation"],
        "stateReferences": state_references,
        "absenceReasonCounts": dict(sorted(absence_reasons.items())),
    }


def _consolidated_result_payload(
    source: Mapping[str, Any],
    *,
    target: float,
    reading: str,
    state: Mapping[str, Any],
) -> dict[str, Any]:
    data_status = str(source.get("dataStatus") or "unavailable")
    if data_status != "available":
        result = {
            "dataStatus": data_status,
            "year": int(source.get("year") or 0),
            "value": None,
        }
        reason_code = source.get("reasonCode")
        if reason_code:
            result["reasonCode"] = str(reason_code)
        return result
    row = pd.Series(
        {
            "ano": int(source["year"]),
            "data_status": "available",
            "valor": float(source["value"]),
            "numerador": (
                source.get("numerator")
                if source.get("numerator") is not None
                else pd.NA
            ),
            "denominador": (
                source.get("denominator")
                if source.get("denominator") is not None
                else pd.NA
            ),
        }
    )
    result = _status_payload(
        row,
        target=target,
        public_reading=reading,
    )
    if state.get("dataStatus") == "available":
        result["stateComparison"] = _goal_11b_state_comparison(
            float(result["value"]),
            float(state["value"]),
            year=int(source["year"]),
        )
    return result


def _consolidated_round_results() -> tuple[
    dict[str, dict[str, dict[str, Any]]],
    dict[str, Any],
]:
    child_rows, child_state_rows, child_manifest = load_child_literacy_snapshot()
    eja_rows, eja_state_rows, eja_manifest = load_goal_11d_snapshot()
    goal_14_rows, goal_14_state_rows, goal_14_manifest = load_goal_14_snapshot()
    goal_15_rows, goal_15_state_rows, goal_15_manifest = load_goal_15b_snapshot()

    child_current = child_literacy_current_results(child_rows)
    eja_current = goal_11d_current_results(eja_rows)
    goal_14_current = {
        str(row["municipalityId"]): row for row in goal_14_rows
    }
    goal_15_current = {}
    for row in goal_15_rows:
        latest = [item for item in row["series"] if int(item["year"]) == 2024]
        if len(latest) != 1:
            raise RuntimeError(
                f"Snapshot 15.b sem 2024 único: {row['municipalityId']}."
            )
        goal_15_current[str(row["municipalityId"])] = latest[0]

    municipality_ids = set(child_current)
    for source in (eja_current, goal_14_current, goal_15_current):
        if set(source) != municipality_ids:
            raise RuntimeError("Coberturas municipais divergentes na rodada.")
    if len(municipality_ids) != EXPECTED_MUNICIPALITIES:
        raise RuntimeError("Rodada consolidada não cobre os 497 municípios.")

    child_state = {int(row["year"]): row for row in child_state_rows}[2025]
    eja_state = {int(row["year"]): row for row in eja_state_rows}[2025]
    goal_14_state = {
        str(row["relationId"]): row for row in goal_14_state_rows
    }
    goal_15_state = {
        str(row["relationId"]): row
        for row in goal_15_state_rows
        if int(row["year"]) == 2024
    }
    goal_14_config = {
        "14.a": (
            "relation.14.a.graduacao_frequencia_18_24",
            40.0,
            "População residente de 18 a 24 anos que frequentava graduação.",
        ),
        "14.b": (
            "relation.14.b.superior_completo_25_34",
            40.0,
            "População residente de 25 a 34 anos com superior completo.",
        ),
        "14.d": (
            "relation.14.d.taxa_bruta_graduacao",
            60.0,
            "Taxa bruta de frequência à graduação por residência.",
        ),
    }
    goal_15_config = {
        "15.b.total": (
            "relation.15.b.docentes_tempo_integral_ies",
            70.0,
            "Docentes em exercício em tempo integral no total das IES.",
        ),
        "15.b.universidades": (
            "relation.15.b.docentes_tempo_integral_universidades",
            50.0,
            "Acompanhamento do tempo integral nas universidades.",
        ),
        "15.b.centros_universitarios": (
            "relation.15.b.docentes_tempo_integral_centros_universitarios",
            40.0,
            "Acompanhamento do tempo integral nos centros universitários.",
        ),
        "15.b.faculdades": (
            "relation.15.b.docentes_tempo_integral_faculdades",
            30.0,
            "Acompanhamento do tempo integral nas faculdades.",
        ),
    }

    by_municipality: dict[str, dict[str, dict[str, Any]]] = {}
    status_counts = {
        relation_id: Counter() for relation_id in CONSOLIDATED_ROUND_RELATION_IDS
    }
    for municipality_id in sorted(municipality_ids):
        municipal = {
            "relation.3.a.alfabetizacao": _consolidated_result_payload(
                child_current[municipality_id],
                target=80.0,
                reading=(
                    "Resultado oficial da rede municipal para estudantes "
                    "avaliados ao final do 2º ano."
                ),
                state=child_state,
            ),
            "relation.11.d.eja_atendimento_18_mais": (
                _consolidated_result_payload(
                    eja_current[municipality_id],
                    target=10.0,
                    reading=(
                        "Matrículas EJA de estudantes com 18 anos ou mais sobre "
                        "a população residente sem Educação Básica concluída."
                    ),
                    state=eja_state,
                )
            ),
        }
        for source_key, (
            relation_id,
            target,
            reading,
        ) in goal_14_config.items():
            municipal[relation_id] = _consolidated_result_payload(
                {
                    "year": int(goal_14_current[municipality_id]["year"]),
                    **goal_14_current[municipality_id]["indicators"][source_key],
                },
                target=target,
                reading=reading,
                state=goal_14_state[source_key],
            )
        for source_key, (
            relation_id,
            target,
            reading,
        ) in goal_15_config.items():
            municipal[relation_id] = _consolidated_result_payload(
                {
                    "year": 2024,
                    **goal_15_current[municipality_id]["indicators"][source_key],
                },
                target=target,
                reading=reading,
                state=goal_15_state[source_key],
            )
        for relation_id, result in municipal.items():
            status_counts[relation_id][result["dataStatus"]] += 1
        by_municipality[municipality_id] = municipal

    return by_municipality, {
        "sources": {
            "childLiteracy": {
                "schemaVersion": child_manifest["schemaVersion"],
                "sourceReferenceDate": child_manifest["sourceReferenceDate"],
                "availableByYear": child_manifest["availableByYear"],
            },
            "goal11d": {
                "schemaVersion": eja_manifest["schemaVersion"],
                "sourceReferenceDate": eja_manifest["sourceReferenceDate"],
                "zeroNumeratorsByYear": eja_manifest["zeroNumeratorsByYear"],
            },
            "goal14": {
                "schemaVersion": goal_14_manifest["schemaVersion"],
                "sourceReferenceDate": goal_14_manifest["sourceReferenceDate"],
            },
            "goal15b": {
                "schemaVersion": goal_15_manifest["schemaVersion"],
                "sourceReferenceDate": goal_15_manifest["sourceReferenceDate"],
                "years": goal_15_manifest["years"],
            },
        },
        "statusByRelation": {
            relation_id: dict(sorted(counts.items()))
            for relation_id, counts in sorted(status_counts.items())
        },
    }


def prepare_staging() -> dict[str, Any]:
    payloads: list[dict[str, Any]] = []
    municipal_files: dict[str, bytes] = {}
    duplicate_count = 0
    current, active_manifest, active_release_root = _active_release()
    (
        special_index,
        special_index_bytes,
        higher_index,
        higher_index_bytes,
    ) = _materialization_indexes()
    (
        munic_records,
        capes_records,
        quality_records,
    ) = load_macro_source_records()
    consolidated_results, consolidated_audit = _consolidated_round_results()
    source_digest = hashlib.sha256()
    _update_aggregate_digest(
        source_digest,
        "educacao-especial/index.json",
        special_index_bytes,
    )
    _update_aggregate_digest(
        source_digest,
        "educacao-superior/index.json",
        higher_index_bytes,
    )
    macro_source_metadata: dict[str, Any] = {}
    for source_id, source_path in sorted(MACRO_SOURCE_PATHS.items()):
        source_bytes = source_path.read_bytes()
        _update_aggregate_digest(
            source_digest,
            f"pne-macro/{source_id}/normalized.json",
            source_bytes,
        )
        macro_source_metadata[source_id] = {
            "schemaVersion": _load_json_bytes(
                source_bytes,
                str(source_path),
            )["schemaVersion"],
            "municipalityCount": EXPECTED_MUNICIPALITIES,
            "sha256": hashlib.sha256(source_bytes).hexdigest(),
        }
    for snapshot_name in (
        "pne_child_literacy",
        "pne_goal_11d_eja",
        "pne_goal_14_census_2022",
        "pne_goal_15b",
    ):
        snapshot_root = DATA_PIPELINE_DIR / "data" / snapshot_name
        for source_path in sorted(snapshot_root.glob("*.json")):
            _update_aggregate_digest(
                source_digest,
                f"{snapshot_name}/{source_path.name}",
                source_path.read_bytes(),
            )
    status_by_relation: dict[str, Counter[str]] = {
        relation_id: Counter() for relation_id in PACKAGE_RELATION_IDS
    }
    absence_reasons: Counter[str] = Counter()
    observed_by_relation: Counter[str] = Counter()
    preserved_record_count = 0
    changed_non_package_record_count = 0
    changed_tracking_record_count = 0
    changed_projection_record_count = 0
    with WorktreeSnapshot() as snapshot:
        entries = _registry(snapshot)
        for entry in entries:
            municipality_id = str(entry["id_municipio"])
            special_path = (
                SPECIAL_EDUCATION_DIR
                / "municipios"
                / f"{municipality_id}.json"
            )
            higher_path = (
                HIGHER_EDUCATION_DIR
                / "municipios"
                / f"{municipality_id}.json"
            )
            special, special_bytes = _read_worktree_json(special_path)
            higher, higher_bytes = _read_worktree_json(higher_path)
            education_path = (
                f"public/data/educacao/municipios/{municipality_id}.json"
            )
            education_bytes = snapshot.read_bytes(education_path)
            education = _load_json_bytes(education_bytes, education_path)
            _update_aggregate_digest(
                source_digest,
                f"educacao-especial/municipios/{municipality_id}.json",
                special_bytes,
            )
            _update_aggregate_digest(
                source_digest,
                f"educacao-superior/municipios/{municipality_id}.json",
                higher_bytes,
            )
            _update_aggregate_digest(
                source_digest,
                f"educacao-municipal/{municipality_id}.json",
                education_bytes,
            )

            if (
                str((special.get("municipality") or {}).get("code"))
                != municipality_id
                or str((higher.get("municipality") or {}).get("id"))
                != municipality_id
                or str(education.get("id_municipio")) != municipality_id
            ):
                raise RuntimeError(
                    f"{municipality_id}: identidade divergente em materialização."
                )
            package_results = dict(consolidated_results[municipality_id])
            macro_results = build_macro_round_results(
                municipality_id=municipality_id,
                munic_records=munic_records,
                capes_records=capes_records,
                quality_records=quality_records,
                higher_education=higher,
            )
            overlap = set(package_results) & set(macro_results)
            if overlap:
                raise RuntimeError(
                    f"{municipality_id}: relações sobrepostas no pacote: {overlap}."
                )
            package_results.update(macro_results)
            for relation_id, result in package_results.items():
                status = str(result.get("dataStatus") or "unavailable")
                status_by_relation[relation_id][status] += 1
                if status == "available":
                    observed_by_relation[relation_id] += 1
                else:
                    absence_reasons[
                        f"{relation_id}:"
                        f"{result.get('reasonCode', 'unspecified')}"
                    ] += 1

            active_payload, _ = _read_worktree_json(
                active_release_root / "municipios" / f"{municipality_id}.json"
            )
            if (
                str((active_payload.get("municipality") or {}).get("id"))
                != municipality_id
            ):
                raise RuntimeError(
                    f"{municipality_id}: identidade divergente na release ativa."
                )
            payload = rebase_pne2026_public_diagnostic_v3(
                active_payload,
                methodology_results=package_results,
            )
            if payload["municipality"]["id"] != municipality_id:
                raise RuntimeError(
                    f"{municipality_id}: identidade municipal V3 divergente."
                )
            active_by_relation = {
                result["relationId"]: result
                for result in active_payload.get("results") or []
            }
            output_by_relation = {
                result["relationId"]: result for result in payload["results"]
            }
            active_relation_ids = set(active_by_relation)
            active_preserved_relation_ids = (
                active_relation_ids
                - TRACKING_ROUND_RELATION_IDS
                - PROJECTION_MIGRATION_RELATION_IDS
            )
            output_preserved_relation_ids = (
                set(output_by_relation)
                - TRACKING_ROUND_RELATION_IDS
                - PROJECTION_MIGRATION_RELATION_IDS
            )
            for relation_id in (
                active_preserved_relation_ids & output_preserved_relation_ids
            ):
                preserved_record_count += 1
                if (
                    active_by_relation[relation_id]
                    != output_by_relation[relation_id]
                ):
                    changed_non_package_record_count += 1
            for relation_id in (
                active_relation_ids
                & set(output_by_relation)
                & TRACKING_ROUND_RELATION_IDS
            ):
                if (
                    active_by_relation[relation_id]
                    != output_by_relation[relation_id]
                ):
                    changed_tracking_record_count += 1
            for relation_id in (
                active_relation_ids
                & set(output_by_relation)
                & PROJECTION_MIGRATION_RELATION_IDS
            ):
                if (
                    active_by_relation[relation_id]
                    != output_by_relation[relation_id]
                ):
                    changed_projection_record_count += 1
            relation_ids = [
                result["relationId"] for result in payload["results"]
            ]
            duplicate_count += len(relation_ids) - len(set(relation_ids))
            relative_path = f"municipalities/{municipality_id}.json"
            municipal_files[relative_path] = _serialized(payload)
            payloads.append(payload)

    manifest = _build_manifest(
        payloads,
        municipal_files,
        duplicate_count,
    )
    _assert_manifest_invariants(manifest)
    contents = dict(municipal_files)
    contents["manifest.json"] = _serialized(manifest)
    return {
        "contents": contents,
        "manifest": manifest,
        "payloads": payloads,
        "methodologyAudit": {
            "activeRelease": {
                "releaseId": current["releaseId"],
                "aggregateHash": active_manifest["aggregateHash"],
                "contractVersion": active_manifest["contractVersion"],
                "contractHash": active_manifest["contractHash"],
                "presentationPolicyVersion": active_manifest[
                    "presentationPolicyVersion"
                ],
                "presentationPolicyHash": active_manifest[
                    "presentationPolicyHash"
                ],
            },
            "sourceMaterializations": {
                "aggregateInputHash": source_digest.hexdigest(),
                "specialEducation": {
                    "schemaVersion": special_index["schemaVersion"],
                    "contentHash": special_index["contentHash"],
                    "municipalityCount": special_index["municipalityCount"],
                },
                "higherEducation": {
                    "schemaVersion": higher_index["schemaVersion"],
                    "dataVersion": higher_index["dataVersion"],
                    "municipalityCount": higher_index["municipalityCount"],
                    "availableYears": higher_index["availableYears"],
                },
                "indigenousEducation": {
                    "populationReferenceYear": 2022,
                    "sourceState": "worktree",
                    "municipalityCount": EXPECTED_MUNICIPALITIES,
                },
                "macroRound": macro_source_metadata,
                "consolidatedRound": consolidated_audit,
            },
            "observedByRelation": dict(sorted(observed_by_relation.items())),
            "statusByRelation": {
                relation_id: dict(sorted(counts.items()))
                for relation_id, counts in sorted(status_by_relation.items())
            },
            "absenceReasonCounts": dict(sorted(absence_reasons.items())),
            "preservedNonPackageRecordCount": preserved_record_count,
            "changedNonPackageRecordCount": changed_non_package_record_count,
            "changedTrackingRecordCount": changed_tracking_record_count,
            "changedProjectionRecordCount": changed_projection_record_count,
            "blocked": {
                "aeeStudentCoverage": (
                    "Materialização não contém numerador de estudantes "
                    "efetivamente atendidos e denominador estudantil compatível."
                ),
                "minimumInfrastructureComposite": (
                    "Materialização pública contém apenas marginais por item; "
                    "não permite classificar a mesma escola na cesta completa."
                ),
                "higherEducationFullTimeFaculty": (
                    "Regime de trabalho docente não integra a camada materializada."
                ),
                "directorSelection": (
                    "O dicionário do Censo Escolar 2025 documenta a tabela de "
                    "gestor, mas o CSV público não contém suas variáveis."
                ),
                "inecConnectivity": (
                    "Não há snapshot oficial estruturado por escola com todos "
                    "os componentes do INEC e estados de monitoramento."
                ),
                "municipalClimatePlan": (
                    "A MUNIC 2024 não contém variável de plano climático da "
                    "rede municipal de ensino."
                ),
                "igcMunicipalization": (
                    "O IGC 2023 não traz município da sede da IES no arquivo "
                    "oficial e a junção externa não foi homologada."
                ),
            },
        },
    }


def write_staging(
    output_dir: Path,
    prepared: Mapping[str, Any],
) -> Path:
    target = validate_staging_output_path(output_dir)
    if target.exists():
        raise FileExistsError(
            f"O staging já existe; escolha um diretório vazio: {target}"
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(
        tempfile.mkdtemp(prefix=f".{target.name}.tmp-", dir=target.parent)
    )
    try:
        for relative_path, content in sorted(prepared["contents"].items()):
            destination = temporary / relative_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(content)
        expected_files = {
            Path(relative_path)
            for relative_path in prepared["contents"]
        }
        actual_files = {
            path.relative_to(temporary)
            for path in temporary.rglob("*")
            if path.is_file()
        }
        if actual_files != expected_files:
            raise RuntimeError("O staging temporário contém arquivos órfãos ou ausentes.")
        shutil.copytree(temporary, target)
        shutil.rmtree(temporary)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        shutil.rmtree(target, ignore_errors=True)
        raise
    return target


def staging_hashes(output_dir: Path) -> dict[str, str]:
    root = validate_staging_output_path(output_dir)
    if not root.is_dir():
        raise FileNotFoundError(root)
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(
            path.read_bytes()
        ).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def compare_staging_directories(left: Path, right: Path) -> None:
    left_hashes = staging_hashes(left)
    right_hashes = staging_hashes(right)
    if left_hashes != right_hashes:
        differing = sorted(set(left_hashes) | set(right_hashes))
        differing = [
            path
            for path in differing
            if left_hashes.get(path) != right_hashes.get(path)
        ]
        raise RuntimeError(
            f"Gerações V3 divergentes: {differing[:10]}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Materializa o diagnóstico municipal PNE V3 exclusivamente em staging."
        )
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Diretório explícito fora de public/data.",
    )
    args = parser.parse_args()
    prepared = prepare_staging()
    output = write_staging(args.output_dir, prepared)
    report = {
        "output": str(output),
        "generatedMunicipalityCount": prepared["manifest"][
            "generatedMunicipalityCount"
        ],
        "totalResultCount": prepared["manifest"]["totalResultCount"],
        "generationHash": prepared["manifest"]["generationHash"],
        "methodologyAudit": prepared["methodologyAudit"],
    }
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
