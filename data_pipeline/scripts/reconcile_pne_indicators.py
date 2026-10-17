"""Rematerialização controlada dos sete indicadores da auditoria de 29/09/2026.

Gera somente em staging; valida ciclo, componentes, diagnóstico e referências.
A promoção ocorre em comando separado, após os checks da implementação.
"""

from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import json
import math
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "data_pipeline"))

from scripts import materialize_pne2026_public_diagnostic_v3 as diagnostic
from scripts import promote_pne2026_public_diagnostic_v3 as promotion
from scripts.export_static_data import (
    _build_rankings_payload_for_municipio, _serialize_item, _serialize_result,
)
from src.pne import calculations_2026 as calculations, common, indicator_details
from src.pne.goal_indicator_contract import CONTRACT
from src.pne_census_attainment import CONFIG, census_results, load_attainment_frame
from src.pne2026_public_diagnostic_v3 import (
    rebase_pne2026_public_diagnostic_v3, validate_pne2026_public_diagnostic_v3,
)
from src.pne_state_context import load_pne_state_context
from src import pne_state_reference as state_reference
from src.child_literacy import load_snapshot as literacy_snapshot

CYCLE = "pne_2026_2036"
TARGETS = frozenset(CONFIG) | {
    "alfabetizacao", "medio_tecnico_articulado_percentual",
    "medio_tecnico_participacao_publica", "subsequente_expansao",
}


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def serialize(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")


def write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def same_number(left, right):
    if left is None or right is None:
        return left is right
    return math.isclose(left, right, abs_tol=1e-8, rel_tol=1e-12)


def rebuild_state_references(previous, state):
    output = deepcopy(previous)
    registry = state_reference.build_registry(methodology_version=state.methodology_version(CYCLE))
    for key in CONFIG:
        config = state_reference.CENSUS_CONFIGS[key]
        metadata = deepcopy(registry[key])
        metadata.update({
            "source": "IBGE — Censo Demográfico 2022, SIDRA 10061 (mesmo universo)",
            "filters": {"anos": [2022]},
            "notes": "Numerador e denominador do mesmo recorte censitário; sem interpolação.",
            "comparison_status": "comparable",
        })
        records = state_reference._build_census_records(
            load_attainment_frame(key, state.state_code), indicator_id=key,
            config=config, municipalities_expected=state.expected_municipality_count,
        )
        records = state_reference._add_common_series_fields(
            records, metadata, methodology_version=metadata["methodology_version"],
        )
        output["registry"][key] = metadata
        output["indicators"][key] = {**metadata, "series": records}
    # These calculations already implement the fixed 2025 baseline and the
    # integrated + concomitant numerator; rebuild their old public outputs.
    ept = diagnostic.load_ept_nivel_medio_data()
    articulated = diagnostic.calculate_medio_tecnico_articulado_series(
        diagnostic.load_medio_tecnico_articulado_data()
    )
    for key in ("medio_tecnico_articulado_percentual", "medio_tecnico_participacao_publica", "subsequente_expansao"):
        metadata = deepcopy(state_reference.build_registry(
            methodology_version=state.methodology_version(CYCLE)
        )[key])
        if key == "medio_tecnico_articulado_percentual":
            config = state_reference.RATIO_CONFIGS[key]
            frame = articulated[articulated.ano.isin(config["allowed_years"])]
            records = state_reference.aggregate_ratio_of_sums(
                frame, config["numerator_column"], config["denominator_column"],
                indicator_id=key, municipalities_expected=state.expected_municipality_count,
                base_notes=config["notes"],
            )
        elif key == "medio_tecnico_participacao_publica":
            records = state_reference._build_medio_tecnico_participacao_records(
                ept, municipalities_expected=state.expected_municipality_count,
            )
        else:
            records = state_reference._build_subsequente_records(
                ept, municipalities_expected=state.expected_municipality_count,
            )
        status, records = state_reference._finalize_series(records)
        metadata["comparison_status"] = status
        output["registry"][key] = metadata
        output["indicators"][key] = {**metadata, "series": state_reference._add_common_series_fields(
            records, metadata, methodology_version=metadata["methodology_version"],
        )}
    # The state result is the official municipal-network result, never a mean
    # of municipal percentages. Keep the published metadata when available.
    metadata = deepcopy(registry["alfabetizacao"])
    metadata.update({"source": "Inep — Indicador Criança Alfabetizada, rede municipal",
                     "comparison_status": "comparable",
                     "aggregation_method": "official_state_result",
                     "notes": "Resultado estadual oficial da rede municipal; não é média municipal."})
    output["registry"]["alfabetizacao"] = metadata
    output["indicators"]["alfabetizacao"] = {
        **metadata,
        "series": state_reference._add_common_series_fields(
            state_reference.build_child_literacy_records(state.state_code), metadata,
            methodology_version=metadata["methodology_version"],
        ),
    }
    for key in TARGETS:
        if key in output.get("projections", {}):
            rebuilt = state_reference.build_state_projections({key: output["indicators"][key]})
            if key in rebuilt:
                output["projections"][key] = rebuilt[key]
            else:
                output["projections"].pop(key)
    return output


def prepare(state_code, output_dir):
    diagnostic.configure_state(state_code)
    promotion.configure_state(state_code)
    state = load_pne_state_context(state_code)
    public = diagnostic.PUBLIC_DATA_DIR
    stage = output_dir.resolve()
    if stage == public or public in stage.parents:
        raise ValueError("Staging deve ficar fora da raiz pública.")
    if stage.exists():
        raise FileExistsError(stage)
    source_hashes = {}
    outputs = {}

    def source(path):
        content = path.read_bytes()
        source_hashes[str(path.relative_to(ROOT)).replace('\\', '/')] = hashlib.sha256(content).hexdigest()
        return json.loads(content)

    for path in (ROOT / "contracts/pne2026-goal-indicator-contract.json",
                 ROOT / f"config/municipalities/{state_code.lower()}.json"):
        source(path)
    for snapshot_name in ("pne_goal_11b_census_2022", "pne_child_literacy"):
        for path in diagnostic._source_snapshot_dir(snapshot_name).glob("*.json"):
            source(path)

    ref_path = public / CYCLE / "referencia_estadual.json"
    reference = rebuild_state_references(source(ref_path), state)
    outputs[ref_path.relative_to(ROOT)] = serialize(reference)
    ref_points = {(key, p["year"]): {"unit": item["unit"], "value": p["value"]}
                  for key, item in reference["indicators"].items()
                  for p in item["series"] if p.get("comparison_status") == "comparable"}
    census = {key: census_results(key, state_code) for key in CONFIG}
    canonical_core = diagnostic._reconciled_core_results()
    child_rows, child_state_rows, _child_manifest = literacy_snapshot(state_code=state_code)
    child_current = diagnostic.child_literacy_current_results(child_rows)
    child_state = {p["year"]: p for p in child_state_rows}[2025]
    old_pointer = source(public / "pne2026-diagnostic-v3/current.json")
    old_release = public / "pne2026-diagnostic-v3/releases" / old_pointer["releaseId"]
    items = {item["key"]: item for category in calculations.INDICADORES.values() for item in category["items"]}
    payloads, comparison_sizes, changes = [], {}, Counter()
    errors = []
    for municipality_id in sorted(state.municipality_ids):
        index_path = public / "municipios" / municipality_id / "index.json"
        details_path = index_path.with_name("details.json")
        index, details = source(index_path), source(details_path)
        if index["id_municipio"] != municipality_id:
            raise ValueError(f"Identidade divergente: {municipality_id}")
        name = index["municipio"]
        previous_cycle = deepcopy(index[CYCLE])
        results = calculations._calculate_results_for_indicators(name, TARGETS)
        if set(results) != TARGETS:
            raise ValueError(f"Cálculos incompletos: {municipality_id}")
        for key, result in results.items():
            if key in census:
                canonical = census[key][municipality_id]
                result.update({"data_status": canonical["dataStatus"],
                               "reason_code": canonical.get("reasonCode")})
            serialized = _serialize_result(result=result, item=items[key], shared=common,
                municipio=name, cycle_key=CYCLE, indicator_key=key, errors=errors)
            if serialized != index[CYCLE]["indicadores"].get(key):
                changes[key] += 1
            index[CYCLE]["indicadores"][key] = serialized
        index[CYCLE]["rankings"] = _build_rankings_payload_for_municipio(
            cycle_key=CYCLE, cycle_module=calculations, municipio=name,
            results=index[CYCLE]["indicadores"], shared=common, errors=errors,
        )["categories"]
        # These seven indicators have no approved municipal projection. A stale
        # projection must not survive a methodological change.
        for collection in ("projecoes", "cenarios_planejamento"):
            affected = TARGETS & set(index[CYCLE].get(collection, {}))
            if affected:
                raise ValueError(f"Projeção exige reconstrução explícita: {municipality_id}/{affected}")
        for key in CONFIG:
            builder = getattr(indicator_details, f"build_{key}_details")
            built = builder(name)
            if not built:
                raise ValueError(f"Componentes censitários ausentes: {municipality_id}/{key}")
            details[key] = built
        built = indicator_details.build_medio_tecnico_articulado_percentual_details(name)
        if built:
            details["medio_tecnico_articulado_percentual"] = built
        comparison_sizes[municipality_id] = diagnostic._comparison_sizes_from_details(details)
        active = source(old_release / "municipios" / f"{municipality_id}.json")
        replacements = dict(canonical_core[municipality_id])
        replacements["relation.3.a.alfabetizacao"] = diagnostic._consolidated_result_payload(
            child_current[municipality_id], target=80.0,
            reading="Resultado oficial da rede municipal para estudantes avaliados ao final do 2º ano.",
            state=child_state,
        )
        payload = rebase_pne2026_public_diagnostic_v3(active, methodology_results=replacements)
        diagnostic._apply_published_state_references(payload, ref_points)
        by_indicator = {result["indicatorId"]: result for result in payload["results"]}
        for key in TARGETS:
            current = by_indicator[key]
            cycle = index[CYCLE]["indicadores"][key]
            observed = current["dataStatus"] == "available"
            if observed != bool(cycle.get("available")) or (observed and (
                current["year"] != cycle.get("end_year") or not same_number(current["value"], cycle.get("end_value"))
            )):
                raise ValueError(f"Ciclo/diagnóstico divergentes: {municipality_id}/{key}: {current.get('value')} vs {cycle.get('end_value')}")
            if observed and "distance" in current and not same_number(current["distance"], cycle.get("distance")):
                raise ValueError(f"Referência divergente: {municipality_id}/{key}")
        if {key: value for key, value in previous_cycle["indicadores"].items() if key not in TARGETS} != {
            key: value for key, value in index[CYCLE]["indicadores"].items() if key not in TARGETS
        }:
            raise AssertionError("Indicador fora do escopo alterado.")
        outputs[index_path.relative_to(ROOT)] = serialize(index)
        outputs[details_path.relative_to(ROOT)] = serialize(details)
        payloads.append(payload)
        if len(payloads) % 100 == 0:
            print(f"{state_code}: {len(payloads)}/{state.expected_municipality_count} municípios reconciliados", flush=True)
    if errors:
        raise ValueError(f"Erros de serialização: {errors[:5]}")
    # Recompute comparisons for the changed census denominator/cohorts. The
    # helper preserves untouched comparisons and rejects irreproducible data.
    for payload in payloads:
        for result in payload["results"]:
            if result["indicatorId"] in {"medio_concluido_18_29", "medio_concluido_18_mais"}:
                result.pop("statewidePosition", None)
                result.pop("similarMunicipalityComparison", None)
    context_audit = diagnostic._apply_municipal_context_comparisons(
        payloads, comparison_sizes, {record.ibge_code: n for n, record in enumerate(state.registry.ordered_records)},
    )
    municipal_files = {f"municipalities/{p['municipality']['id']}.json": diagnostic._serialized(
        validate_pne2026_public_diagnostic_v3(p)) for p in payloads}
    manifest = diagnostic._build_manifest(payloads, municipal_files, 0)
    diagnostic._assert_manifest_invariants(manifest)
    source_stage = stage / "diagnostic-source"
    for relative, content in {**municipal_files, "manifest.json": diagnostic._serialized(manifest)}.items():
        write(source_stage / relative, content)
    validated = promotion.validate_source_package(source_stage)
    release_manifest = validated["releaseManifest"]
    pointer = promotion.build_current_pointer(release_manifest)
    release_relative = public.relative_to(ROOT) / "pne2026-diagnostic-v3/releases" / pointer["releaseId"]
    for relative, content in municipal_files.items():
        outputs[release_relative / "municipios" / Path(relative).name] = content
    outputs[release_relative / "manifest.json"] = promotion._serialized(release_manifest)
    outputs[public.relative_to(ROOT) / "pne2026-diagnostic-v3/current.json"] = promotion._serialized(pointer)
    catalog_path = public / "indicadores.json"
    catalog = source(catalog_path)
    for category in catalog["cycles"][CYCLE]["categories"]:
        for i, item in enumerate(category["items"]):
            if item["key"] in TARGETS:
                category["items"][i] = _serialize_item(items[item["key"]])
    outputs[catalog_path.relative_to(ROOT)] = serialize(catalog)
    # Check optimistic concurrency before handing off the validated batch.
    for relative, digest in source_hashes.items():
        if hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() != digest:
            raise RuntimeError(f"Insumo alterado durante geração: {relative}")
    for relative, content in outputs.items():
        write(stage / "files" / relative, content)
    report = {"state": state_code, "municipalities": len(payloads), "indicators": sorted(TARGETS),
              "changedCycleRecords": dict(changes), "releaseId": pointer["releaseId"],
              "previousReleaseId": old_pointer["releaseId"], "contractVersion": CONTRACT["contractVersion"],
              "validatedComparisons": len(payloads) * len(TARGETS), "contextAudit": context_audit,
              "sourceHashes": source_hashes,
              "files": {str(path).replace('\\', '/'): hashlib.sha256(content).hexdigest() for path, content in outputs.items()}}
    write(stage / "report.json", serialize(report))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", choices=("RS", "AL"), required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    report = prepare(args.state, args.output_dir)
    print(json.dumps({key: value for key, value in report.items() if key not in {"files", "sourceHashes", "contextAudit"}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
