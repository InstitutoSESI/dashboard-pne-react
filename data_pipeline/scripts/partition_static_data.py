from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.config import PIPELINE_EXPORT_DIR, STATIC_PARTITIONED_DATA_DIR  # noqa: E402
from src.municipality_registry import (  # noqa: E402
    MunicipalityRecord,
    MunicipalityRegistry,
    MunicipalityRegistryError,
    load_municipality_registry,
)
from src.state_config import (  # noqa: E402
    DEFAULT_STATE_CODE,
    load_state_config,
)
from src.pipeline_profiling import (  # noqa: E402
    get_active_profile_session,
    profile_operation,
    profiled_main_from_environment,
)

SOURCE_DIR = PIPELINE_EXPORT_DIR / "data"
OUTPUT_DIR = STATIC_PARTITIONED_DATA_DIR

CYCLES = ("pne_2014_2024", "pne_2026_2036")
COPIED_ROOT_STATIC_FILES = ("indicadores.json",)


def load_json(path: Path) -> dict:
    session = get_active_profile_session()
    started_ns = time.perf_counter_ns() if session is not None else 0
    failed = False
    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except BaseException:
        failed = True
        raise
    finally:
        if session is not None:
            size = path.stat().st_size if path.is_file() else 0
            session.accumulate_event(
                category="read",
                name="partition.aggregate_reads",
                duration_ns=time.perf_counter_ns() - started_ns,
                counters={
                    "filesRead": int(not failed),
                    "bytesRead": size,
                    "errors": int(failed),
                },
                metadata={"format": "json"},
            )


def load_optional_json(path: Path, fallback: dict | None = None) -> dict:
    if path.exists():
        return load_json(path)
    return fallback or {}


def render_json(payload: dict) -> str:
    session = get_active_profile_session()
    if session is None:
        return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    started_ns = time.perf_counter_ns()
    content = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    session.accumulate_event(
        category="serialization",
        name="partition.render_json",
        duration_ns=time.perf_counter_ns() - started_ns,
        counters={
            "payloads": 1,
            "bytesRendered": len(content.encode("utf-8")),
        },
        metadata={"format": "json"},
    )
    return content


def record_write(path: Path, expected_paths: set[Path]) -> None:
    expected_paths.add(path.resolve())


def write_text_if_changed(path: Path, content: str, stats: dict[str, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    session = get_active_profile_session()
    rendered_bytes = len(content.encode("utf-8")) if session is not None else 0

    if path.exists():
        read_started_ns = time.perf_counter_ns() if session is not None else 0
        current = path.read_text(encoding="utf-8")
        if session is not None:
            session.accumulate_event(
                category="read",
                name="partition.output_comparison",
                duration_ns=time.perf_counter_ns() - read_started_ns,
                counters={
                    "filesRead": 1,
                    "bytesRead": len(current.encode("utf-8")),
                },
            )
        if current == content:
            stats["preserved"] += 1
            if session is not None:
                session.accumulate_event(
                    category="write",
                    name="partition.file_outputs",
                    counters={
                        "preserved": 1,
                        "bytesRendered": rendered_bytes,
                    },
                )
            return
        action = "updated"
    else:
        action = "created"

    write_started_ns = time.perf_counter_ns() if session is not None else 0
    path.write_text(content, encoding="utf-8")
    stats[action] += 1
    if session is not None:
        session.accumulate_event(
            category="write",
            name="partition.file_outputs",
            duration_ns=time.perf_counter_ns() - write_started_ns,
            counters={
                action: 1,
                "bytesRendered": rendered_bytes,
                "bytesWritten": rendered_bytes,
            },
        )


def write_json(
    path: Path,
    payload: dict,
    stats: dict[str, int],
    expected_paths: set[Path],
) -> None:
    record_write(path, expected_paths)
    write_text_if_changed(path, render_json(payload), stats)


def copy_file_if_changed(
    source: Path,
    destination: Path,
    stats: dict[str, int],
    expected_paths: set[Path],
) -> None:
    record_write(destination, expected_paths)
    destination.parent.mkdir(parents=True, exist_ok=True)
    session = get_active_profile_session()
    read_started_ns = time.perf_counter_ns() if session is not None else 0
    content = source.read_bytes()
    bytes_read = len(content)

    if destination.exists():
        destination_content = destination.read_bytes()
        bytes_read += len(destination_content)
        if destination_content == content:
            stats["preserved"] += 1
            if session is not None:
                session.accumulate_event(
                    category="read",
                    name="partition.copy_reads",
                    duration_ns=time.perf_counter_ns() - read_started_ns,
                    counters={"filesRead": 2, "bytesRead": bytes_read},
                )
                session.accumulate_event(
                    category="write",
                    name="partition.file_outputs",
                    counters={"preserved": 1, "bytesRendered": len(content)},
                )
            return
        action = "updated"
    else:
        action = "created"

    if session is not None:
        session.accumulate_event(
            category="read",
            name="partition.copy_reads",
            duration_ns=time.perf_counter_ns() - read_started_ns,
            counters={
                "filesRead": 2 if destination.exists() else 1,
                "bytesRead": bytes_read,
            },
        )
    write_started_ns = time.perf_counter_ns() if session is not None else 0
    destination.write_bytes(content)
    stats[action] += 1
    if session is not None:
        session.accumulate_event(
            category="write",
            name="partition.file_outputs",
            duration_ns=time.perf_counter_ns() - write_started_ns,
            counters={
                action: 1,
                "bytesRendered": len(content),
                "bytesWritten": len(content),
            },
        )


def copy_root_static_files(
    stats: dict[str, int],
    expected_paths: set[Path],
) -> None:
    for filename in COPIED_ROOT_STATIC_FILES:
        copy_file_if_changed(
            SOURCE_DIR / filename,
            OUTPUT_DIR / filename,
            stats,
            expected_paths,
        )


def safe_prepare_output_dir() -> None:
    resolved_output = OUTPUT_DIR.resolve()
    expected_parent = PIPELINE_EXPORT_DIR.resolve()

    if resolved_output.parent != expected_parent:
        raise RuntimeError(f"Diretório de saída inesperado: {resolved_output}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def remove_orphan_json_files(
    output_dir: Path,
    expected_paths: set[Path],
    stats: dict[str, int],
) -> None:
    expected = {path.resolve() for path in expected_paths}

    for path in output_dir.rglob("*.json"):
        if path.resolve() in expected:
            continue
        path.unlink()
        stats["removed"] += 1

    directories = [path for path in output_dir.rglob("*") if path.is_dir()]
    for directory in sorted(directories, key=lambda path: len(path.parts), reverse=True):
        if directory == output_dir:
            continue
        try:
            directory.rmdir()
        except OSError:
            pass


def load_aggregate_payloads() -> dict[str, dict]:
    payloads = {
        "municipios": load_json(SOURCE_DIR / "municipios.json"),
        "indicadores": load_json(SOURCE_DIR / "indicadores.json"),
    }

    for cycle in CYCLES:
        payloads[f"{cycle}_indicadores"] = load_json(
            SOURCE_DIR / cycle / "indicadores_por_municipio.json"
        )
        payloads[f"{cycle}_rankings"] = load_optional_json(
            SOURCE_DIR / cycle / "rankings_por_municipio.json"
        )

    payloads["indicator_details"] = load_json(
        SOURCE_DIR / "indicator_details_por_municipio.json"
    )
    payloads["fundeb"] = load_optional_json(
        SOURCE_DIR / "fundeb_por_municipio.json"
    )
    payloads["pnate"] = load_optional_json(
        SOURCE_DIR / "pnate_por_municipio.json"
    )
    for cycle in CYCLES:
        payloads[f"{cycle}_state_reference"] = load_optional_json(
            SOURCE_DIR / cycle / "referencia_estadual.json"
        )
    payloads["projecoes"] = load_optional_json(
        SOURCE_DIR / "pne_2026_2036" / "projecoes_por_municipio.json"
    )
    payloads["planning_scenarios"] = load_json(
        SOURCE_DIR
        / "pne_2026_2036"
        / "cenarios_planejamento_por_municipio.json"
    )
    payloads["education_attendance"] = load_json(
        SOURCE_DIR
        / "pne_2026_2036"
        / "atendimento_cenarios_por_municipio.json"
    )
    return payloads


def resolve_aggregate_municipalities(
    payload: dict,
    registry: MunicipalityRegistry,
) -> dict[str, str]:
    raw_names = payload.get("municipios")
    if not isinstance(raw_names, list):
        raise RuntimeError(
            "[partition] Agregado municipios.json inválido: 'municipios' deve ser uma lista."
        )

    aggregate_names_by_id: dict[str, str] = {}
    for position, raw_name in enumerate(raw_names, start=1):
        if not isinstance(raw_name, str) or not raw_name.strip():
            raise RuntimeError(
                f"[partition] Nome municipal inválido na posição {position}: {raw_name!r}."
            )
        try:
            record = registry.resolve_unique_name(raw_name)
        except MunicipalityRegistryError as exc:
            raise RuntimeError(
                f"[partition] Município do agregado não resolvido: {raw_name!r}: {exc}"
            ) from exc
        if record.ibge_code in aggregate_names_by_id:
            raise RuntimeError(
                "[partition] Agregado municipal duplicado para o código "
                f"{record.ibge_code}: {raw_name!r}."
            )
        aggregate_names_by_id[record.ibge_code] = raw_name

    observed_ids = set(aggregate_names_by_id)
    if observed_ids != registry.ids:
        missing = sorted(registry.ids - observed_ids)
        extra = sorted(observed_ids - registry.ids)
        raise RuntimeError(
            "[partition] Agregado municipal diverge do registro; "
            f"ausentes={missing[:5]}, extras={extra[:5]}."
        )
    return aggregate_names_by_id


def validate_fundeb_payload(
    payloads: dict[str, dict],
    municipios: list[str],
    registry: MunicipalityRegistry,
) -> None:
    fundeb_payload = payloads.get("fundeb") or {}
    fundeb_municipios = fundeb_payload.get("municipios")
    if not isinstance(fundeb_municipios, dict):
        raise RuntimeError(
            "[partition] FUNDEB invalido: arquivo fundeb_por_municipio.json ausente "
            "ou sem objeto 'municipios'. Rode export_static_data.py completo antes do particionamento."
        )

    total_expected = registry.municipality_count
    total_base = len(municipios)
    total_file = int(fundeb_payload.get("total_municipios") or len(fundeb_municipios))
    total_entries = len(fundeb_municipios)
    total_with_data = sum(
        1
        for municipio in municipios
        if isinstance(fundeb_municipios.get(municipio, {}).get("fundeb"), dict)
        and fundeb_municipios[municipio]["fundeb"].get("historico")
    )

    print("[partition] Validacao FUNDEB")
    print(f"[partition]   total esperado: {total_expected}")
    print(f"[partition]   total da base municipal: {total_base}")
    print(f"[partition]   total declarado no FUNDEB: {total_file}")
    print(f"[partition]   total de entradas no FUNDEB: {total_entries}")
    print(f"[partition]   total com dados FUNDEB: {total_with_data}")

    problems = []
    if total_base != total_expected:
        problems.append(f"base municipal tem {total_base}, esperado {total_expected}")
    if total_file != total_expected:
        problems.append(f"fundeb_por_municipio.json declara {total_file}, esperado {total_expected}")
    if total_entries != total_expected:
        problems.append(f"fundeb_por_municipio.json contem {total_entries} entradas, esperado {total_expected}")
    if total_with_data != total_expected:
        problems.append(f"FUNDEB com dados em {total_with_data} municipios, esperado {total_expected}")
    if set(fundeb_municipios) != set(municipios):
        problems.append("FUNDEB diverge do conjunto de nomes do agregado municipal")

    if problems:
        raise RuntimeError(
            "[partition] Fonte FUNDEB incompleta/parcial; particionamento interrompido para "
            "nao sobrescrever a base final. " + "; ".join(problems)
        )


def validate_pnate_payload(
    payloads: dict[str, dict],
    municipios: list[str],
    registry: MunicipalityRegistry,
) -> None:
    pnate_payload = payloads.get("pnate") or {}
    pnate_municipios = pnate_payload.get("municipios")
    if not isinstance(pnate_municipios, dict):
        raise RuntimeError(
            "[partition] PNATE invalido: arquivo pnate_por_municipio.json ausente "
            "ou sem objeto 'municipios'. Rode export_static_data.py completo antes do particionamento."
        )

    total_expected = registry.municipality_count
    total_base = len(municipios)
    total_file = int(pnate_payload.get("total_municipios") or len(pnate_municipios))
    total_entries = len(pnate_municipios)
    total_with_data = sum(
        1
        for municipio in municipios
        if isinstance(pnate_municipios.get(municipio, {}).get("pnate"), dict)
        and pnate_municipios[municipio]["pnate"].get("historico")
    )

    print("[partition] Validacao PNATE")
    print(f"[partition]   total esperado: {total_expected}")
    print(f"[partition]   total da base municipal: {total_base}")
    print(f"[partition]   total declarado no PNATE: {total_file}")
    print(f"[partition]   total de entradas no PNATE: {total_entries}")
    print(f"[partition]   total com dados PNATE: {total_with_data}")

    problems = []
    if total_base != total_expected:
        problems.append(f"base municipal tem {total_base}, esperado {total_expected}")
    if total_file != total_expected:
        problems.append(f"pnate_por_municipio.json declara {total_file}, esperado {total_expected}")
    if total_entries != total_expected:
        problems.append(f"pnate_por_municipio.json contem {total_entries} entradas, esperado {total_expected}")
    if total_with_data != total_expected:
        problems.append(f"PNATE com dados em {total_with_data} municipios, esperado {total_expected}")
    if set(pnate_municipios) != set(municipios):
        problems.append("PNATE diverge do conjunto de nomes do agregado municipal")

    if problems:
        raise RuntimeError(
            "[partition] Fonte PNATE incompleta/parcial; particionamento interrompido para "
            "nao sobrescrever a base final. " + "; ".join(problems)
        )


def validate_planning_scenarios_payload(
    payloads: dict[str, dict],
    municipios: list[str],
    registry: MunicipalityRegistry,
) -> None:
    payload = payloads.get("planning_scenarios") or {}
    scenarios = payload.get("municipios")
    expected_keys = {
        "basico_integral",
        "escolas_integral",
        "pos_graduacao",
        "temporarios",
    }
    problems = []
    if payload.get("publicationStatus") != "published":
        problems.append("status de publicação inválido")
    if payload.get("scenarioType") != "maintenance":
        problems.append("tipo de cenário inválido")
    if not isinstance(scenarios, dict) or len(scenarios) != registry.municipality_count:
        problems.append("cobertura municipal incompleta")
    elif set(scenarios) != set(municipios):
        problems.append("conjunto municipal divergente")
    else:
        for municipio in municipios:
            contracts = scenarios.get(municipio)
            if not isinstance(contracts, dict) or set(contracts) != expected_keys:
                problems.append(f"contratos incompletos para {municipio}")
                break
            if any(
                contract.get("targetValidationStatus") != "configured_unvalidated"
                for contract in contracts.values()
            ):
                problems.append(f"situação jurídica inválida para {municipio}")
                break
    if problems:
        raise RuntimeError(
            "[partition] Cenários de planejamento inválidos: " + "; ".join(problems)
        )


def extract_results(payload: dict, municipio: str) -> dict:
    return payload.get("municipios", {}).get(municipio, {}).get("results", {})


def extract_rankings(payload: dict, municipio: str) -> dict:
    return payload.get("municipios", {}).get(municipio, {}).get("categories", {})


def extract_indicator_details(payload: dict, municipio: str) -> dict:
    return payload.get("municipios", {}).get(municipio, {}).get("indicator_details", {})


def extract_projections(payload: dict, municipio: str) -> dict:
    return payload.get("municipios", {}).get(municipio, {})


def extract_planning_scenarios(payload: dict, municipio: str) -> dict:
    return payload.get("municipios", {}).get(municipio, {})


def extract_education_attendance(payload: dict, municipio: str) -> dict:
    return payload.get("municipios", {}).get(municipio, {})


def extract_fundeb(payload: dict, municipio: str) -> dict | None:
    return payload.get("municipios", {}).get(municipio, {}).get("fundeb")


def extract_pnate(payload: dict, municipio: str) -> dict | None:
    return payload.get("municipios", {}).get(municipio, {}).get("pnate")


def build_municipio_payload(
    payloads: dict[str, dict],
    aggregate_name: str,
    record: MunicipalityRecord,
) -> dict:
    fundeb_data = extract_fundeb(payloads["fundeb"], aggregate_name)
    pnate_data = extract_pnate(payloads["pnate"], aggregate_name)
    projection_data = extract_projections(payloads["projecoes"], aggregate_name)
    planning_scenarios = extract_planning_scenarios(
        payloads["planning_scenarios"], aggregate_name
    )
    education_attendance = extract_education_attendance(
        payloads["education_attendance"], aggregate_name
    )
    payload = {
        "id_municipio": record.ibge_code,
        "municipio": record.name,
        "slug": record.slug,
        "pne_2014_2024": {
            "indicadores": extract_results(
                payloads["pne_2014_2024_indicadores"], aggregate_name
            ),
            "rankings": extract_rankings(
                payloads["pne_2014_2024_rankings"], aggregate_name
            ),
        },
        "pne_2026_2036": {
            "indicadores": extract_results(
                payloads["pne_2026_2036_indicadores"], aggregate_name
            ),
            "rankings": extract_rankings(
                payloads["pne_2026_2036_rankings"], aggregate_name
            ),
            "projecoes": projection_data,
            "cenarios_planejamento": planning_scenarios,
        },
        "educacao": {
            "atendimento_cenarios": education_attendance,
        },
    }
    if fundeb_data is not None:
        payload.setdefault("blocos", {})["fundeb"] = fundeb_data
    if pnate_data is not None:
        payload.setdefault("blocos", {})["pnate"] = pnate_data
    return payload


def format_size(bytes_count: int) -> str:
    units = ("B", "KB", "MB", "GB")
    size = float(bytes_count)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{bytes_count} B"


def resolve_generated_at(payloads: dict[str, dict]) -> str:
    generated_at = payloads.get("municipios", {}).get("generated_at")
    if generated_at:
        return str(generated_at)
    return datetime.now(timezone.utc).isoformat()


@profiled_main_from_environment("partition")
def main() -> int:
    global SOURCE_DIR, OUTPUT_DIR

    parser = argparse.ArgumentParser(
        description="Particiona os JSONs exportados do Dashboard PNE por município."
    )
    parser.add_argument(
        "--source-dir",
        default=str(SOURCE_DIR),
        help="Diretório com os JSONs agregados gerados por export_static_data.py.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(OUTPUT_DIR),
        help="Diretório onde os JSONs particionados serão gerados.",
    )
    parser.add_argument(
        "--state",
        default=DEFAULT_STATE_CODE,
        help=f"Código estadual configurado (padrão: {DEFAULT_STATE_CODE}).",
    )
    args = parser.parse_args()

    SOURCE_DIR = Path(args.source_dir).resolve()
    OUTPUT_DIR = Path(args.output_dir).resolve()
    with profile_operation(
        "validation",
        "partition.configuration",
        metadata={"state": args.state},
    ) as configuration_event:
        state_config = load_state_config(args.state)
        registry = load_municipality_registry(state_config)
        configuration_event.add_counter("municipalities", registry.municipality_count)

    print("[partition] Iniciando particionamento dos dados estáticos.")
    print(f"[partition] Origem: {SOURCE_DIR}")
    print(f"[partition] Saída: {OUTPUT_DIR}")

    with profile_operation(
        "read",
        "partition.read_aggregates",
        metadata={"sourceRoot": SOURCE_DIR},
    ) as read_event:
        payloads = load_aggregate_payloads()
        read_event.add_counter("aggregatePayloads", len(payloads))
    with profile_operation(
        "validation",
        "partition.validate_aggregates",
    ) as validation_event:
        aggregate_names_by_id = resolve_aggregate_municipalities(
            payloads["municipios"], registry
        )
        municipios = list(aggregate_names_by_id.values())
        validate_fundeb_payload(payloads, municipios, registry)
        validate_pnate_payload(payloads, municipios, registry)
        validate_planning_scenarios_payload(payloads, municipios, registry)
        validation_event.add_counter("municipalities", len(municipios))
        validation_event.add_counter("contracts", 4)
    stats = {"created": 0, "updated": 0, "preserved": 0, "removed": 0}
    expected_paths: set[Path] = set()

    with profile_operation(
        "write",
        "partition.prepare_and_root_outputs",
        metadata={"outputRoot": OUTPUT_DIR},
    ):
        safe_prepare_output_dir()
        copy_root_static_files(stats, expected_paths)
        for cycle in CYCLES:
            state_reference_path = SOURCE_DIR / cycle / "referencia_estadual.json"
            if state_reference_path.exists():
                copy_file_if_changed(
                    state_reference_path,
                    OUTPUT_DIR / cycle / "referencia_estadual.json",
                    stats,
                    expected_paths,
                )

        generated_at = resolve_generated_at(payloads)
        write_json(
            OUTPUT_DIR / "municipios_index.json",
            registry.build_public_index_payload(generated_at=generated_at),
            stats,
            expected_paths,
        )

    errors: list[dict[str, str]] = []
    with profile_operation(
        "compute",
        "partition.materialize_municipalities",
        metadata={"eventGranularity": "aggregate"},
    ) as municipal_event:
        for position, record in enumerate(registry.ordered_records, start=1):
            aggregate_name = aggregate_names_by_id[record.ibge_code]
            print(
                f"[partition] {position}/{registry.municipality_count} "
                f"{record.name} -> {record.ibge_code}"
            )
            try:
                municipio_payload = build_municipio_payload(
                    payloads,
                    aggregate_name,
                    record,
                )
                write_json(
                    OUTPUT_DIR / "municipios" / record.ibge_code / "index.json",
                    municipio_payload,
                    stats,
                    expected_paths,
                )
                write_json(
                    OUTPUT_DIR / "municipios" / record.ibge_code / "details.json",
                    extract_indicator_details(
                        payloads["indicator_details"], aggregate_name
                    ),
                    stats,
                    expected_paths,
                )
            except Exception as exc:  # noqa: BLE001 - keep processing other municipalities.
                errors.append(
                    {"municipio": record.name, "slug": record.slug, "erro": str(exc)}
                )
                print(f"[partition] ERRO em {record.name}: {exc}")
        municipal_event.add_counter(
            "municipalitiesCompleted",
            registry.municipality_count - len(errors),
        )
        municipal_event.add_counter("errors", len(errors))

    if errors:
        write_json(
            OUTPUT_DIR / "partition_errors.json",
            {"generated_at": generated_at, "total_erros": len(errors), "errors": errors},
            stats,
            expected_paths,
        )

    removed_before = stats["removed"]
    with profile_operation(
        "promotion",
        "partition.remove_orphans",
        metadata={"outputRoot": OUTPUT_DIR},
    ) as orphan_event:
        remove_orphan_json_files(OUTPUT_DIR, expected_paths, stats)
        orphan_event.add_counter("removed", stats["removed"] - removed_before)

    with profile_operation(
        "validation",
        "partition.output_inventory",
    ) as inventory_event:
        files = list(OUTPUT_DIR.rglob("*.json"))
        municipio_files = list((OUTPUT_DIR / "municipios").rglob("index.json"))
        sizes = {path: path.stat().st_size for path in files}
        total_size = sum(sizes.values())
        largest = max(files, key=sizes.__getitem__)
        inventory_event.add_counters(
            files=len(files),
            municipalities=len(municipio_files),
            bytes=total_size,
            largestFileBytes=sizes[largest],
            created=stats["created"],
            updated=stats["updated"],
            preserved=stats["preserved"],
            removed=stats["removed"],
            errors=len(errors),
        )

    print("[partition] Concluído.")
    print(f"[partition] Municípios particionados: {len(municipio_files)}")
    print(f"[partition] Arquivos criados: {stats['created']}")
    print(f"[partition] Arquivos atualizados: {stats['updated']}")
    print(f"[partition] Arquivos preservados: {stats['preserved']}")
    print(f"[partition] Arquivos removidos: {stats['removed']}")
    print(f"[partition] Erros: {len(errors)}")
    print(f"[partition] Arquivos JSON: {len(files)}")
    print(f"[partition] Tamanho total: {format_size(total_size)}")
    print(f"[partition] Maior arquivo: {largest.relative_to(OUTPUT_DIR)} ({format_size(sizes[largest])})")

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
