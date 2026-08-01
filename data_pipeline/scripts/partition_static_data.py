from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.config import PIPELINE_EXPORT_DIR, STATIC_PARTITIONED_DATA_DIR  # noqa: E402

SOURCE_DIR = PIPELINE_EXPORT_DIR / "data"
OUTPUT_DIR = STATIC_PARTITIONED_DATA_DIR

CYCLES = ("pne_2014_2024", "pne_2026_2036")
EXPECTED_MUNICIPALITIES = 497
COPIED_ROOT_STATIC_FILES = ("indicadores.json",)


def slugify(value: str, fallback: str = "municipio") -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_value.lower()).strip("-")
    slug = re.sub(r"-+", "-", slug)
    return slug or fallback


def unique_slugs(names: list[str]) -> dict[str, str]:
    used: dict[str, int] = {}
    result: dict[str, str] = {}

    for name in names:
        base_slug = slugify(name)
        count = used.get(base_slug, 0) + 1
        used[base_slug] = count
        result[name] = base_slug if count == 1 else f"{base_slug}-{count}"

    return result


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def load_optional_json(path: Path, fallback: dict | None = None) -> dict:
    if path.exists():
        return load_json(path)
    return fallback or {}


def render_json(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def record_write(path: Path, expected_paths: set[Path]) -> None:
    expected_paths.add(path.resolve())


def write_text_if_changed(path: Path, content: str, stats: dict[str, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists():
        current = path.read_text(encoding="utf-8")
        if current == content:
            stats["preserved"] += 1
            return
        action = "updated"
    else:
        action = "created"

    path.write_text(content, encoding="utf-8")
    stats[action] += 1


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
    content = source.read_bytes()

    if destination.exists():
        if destination.read_bytes() == content:
            stats["preserved"] += 1
            return
        action = "updated"
    else:
        action = "created"

    destination.write_bytes(content)
    stats[action] += 1


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


def validate_fundeb_payload(payloads: dict[str, dict], municipios: list[str]) -> None:
    fundeb_payload = payloads.get("fundeb") or {}
    fundeb_municipios = fundeb_payload.get("municipios")
    if not isinstance(fundeb_municipios, dict):
        raise RuntimeError(
            "[partition] FUNDEB invalido: arquivo fundeb_por_municipio.json ausente "
            "ou sem objeto 'municipios'. Rode export_static_data.py completo antes do particionamento."
        )

    total_expected = EXPECTED_MUNICIPALITIES
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

    if problems:
        raise RuntimeError(
            "[partition] Fonte FUNDEB incompleta/parcial; particionamento interrompido para "
            "nao sobrescrever a base final. " + "; ".join(problems)
        )


def validate_pnate_payload(payloads: dict[str, dict], municipios: list[str]) -> None:
    pnate_payload = payloads.get("pnate") or {}
    pnate_municipios = pnate_payload.get("municipios")
    if not isinstance(pnate_municipios, dict):
        raise RuntimeError(
            "[partition] PNATE invalido: arquivo pnate_por_municipio.json ausente "
            "ou sem objeto 'municipios'. Rode export_static_data.py completo antes do particionamento."
        )

    total_expected = EXPECTED_MUNICIPALITIES
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

    if problems:
        raise RuntimeError(
            "[partition] Fonte PNATE incompleta/parcial; particionamento interrompido para "
            "nao sobrescrever a base final. " + "; ".join(problems)
        )


def validate_planning_scenarios_payload(
    payloads: dict[str, dict], municipios: list[str]
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
    if not isinstance(scenarios, dict) or len(scenarios) != EXPECTED_MUNICIPALITIES:
        problems.append("cobertura municipal incompleta")
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


def extract_fundeb_id(payload: dict, municipio: str) -> str | None:
    fundeb_data = extract_fundeb(payload, municipio)
    if not fundeb_data:
        return None

    resumo_id = fundeb_data.get("resumo_ultimo_ano", {}).get("id_municipio")
    if resumo_id:
        return str(resumo_id)

    for row in fundeb_data.get("historico", []):
        row_id = row.get("id_municipio")
        if row_id:
            return str(row_id)

    return None


def build_municipio_payload(
    payloads: dict[str, dict],
    municipio: str,
    slug: str,
    id_municipio: str | None = None,
) -> dict:
    fundeb_data = extract_fundeb(payloads["fundeb"], municipio)
    pnate_data = extract_pnate(payloads["pnate"], municipio)
    projection_data = extract_projections(payloads["projecoes"], municipio)
    planning_scenarios = extract_planning_scenarios(
        payloads["planning_scenarios"], municipio
    )
    education_attendance = extract_education_attendance(
        payloads["education_attendance"], municipio
    )
    payload = {
        "id_municipio": id_municipio,
        "municipio": municipio,
        "slug": slug,
        "pne_2014_2024": {
            "indicadores": extract_results(payloads["pne_2014_2024_indicadores"], municipio),
            "rankings": extract_rankings(payloads["pne_2014_2024_rankings"], municipio),
        },
        "pne_2026_2036": {
            "indicadores": extract_results(payloads["pne_2026_2036_indicadores"], municipio),
            "rankings": extract_rankings(payloads["pne_2026_2036_rankings"], municipio),
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
    args = parser.parse_args()

    SOURCE_DIR = Path(args.source_dir).resolve()
    OUTPUT_DIR = Path(args.output_dir).resolve()

    print("[partition] Iniciando particionamento dos dados estáticos.")
    print(f"[partition] Origem: {SOURCE_DIR}")
    print(f"[partition] Saída: {OUTPUT_DIR}")

    payloads = load_aggregate_payloads()
    municipios = payloads["municipios"].get("municipios", [])
    validate_fundeb_payload(payloads, municipios)
    validate_pnate_payload(payloads, municipios)
    validate_planning_scenarios_payload(payloads, municipios)
    slug_map = unique_slugs(municipios)
    id_map = {
        municipio: extract_fundeb_id(payloads["fundeb"], municipio)
        for municipio in municipios
    }
    stats = {"created": 0, "updated": 0, "preserved": 0, "removed": 0}
    expected_paths: set[Path] = set()

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
    index_items = [
        {
            "nome": municipio,
            "id_municipio": id_map.get(municipio),
            "slug": slug_map[municipio],
            "path": f"/data/municipios/{id_map.get(municipio) or slug_map[municipio]}/index.json",
        }
        for municipio in municipios
    ]
    write_json(
        OUTPUT_DIR / "municipios_index.json",
        {
            "generated_at": generated_at,
            "total_municipios": len(index_items),
            "municipios": index_items,
        },
        stats,
        expected_paths,
    )

    errors: list[dict[str, str]] = []
    for position, municipio in enumerate(municipios, start=1):
        slug = slug_map[municipio]
        id_municipio = id_map.get(municipio)
        canonical_id = id_municipio or slug
        print(f"[partition] {position}/{len(municipios)} {municipio} -> {canonical_id}")
        try:
            municipio_payload = build_municipio_payload(
                payloads,
                municipio,
                slug,
                id_municipio,
            )
            write_json(
                OUTPUT_DIR / "municipios" / canonical_id / "index.json",
                municipio_payload,
                stats,
                expected_paths,
            )
            write_json(
                OUTPUT_DIR / "municipios" / canonical_id / "details.json",
                extract_indicator_details(payloads["indicator_details"], municipio),
                stats,
                expected_paths,
            )
        except Exception as exc:  # noqa: BLE001 - keep processing other municipalities.
            errors.append({"municipio": municipio, "slug": slug, "erro": str(exc)})
            print(f"[partition] ERRO em {municipio}: {exc}")

    if errors:
        write_json(
            OUTPUT_DIR / "partition_errors.json",
            {"generated_at": generated_at, "total_erros": len(errors), "errors": errors},
            stats,
            expected_paths,
        )

    remove_orphan_json_files(OUTPUT_DIR, expected_paths, stats)

    files = list(OUTPUT_DIR.rglob("*.json"))
    municipio_files = list((OUTPUT_DIR / "municipios").rglob("index.json"))
    total_size = sum(path.stat().st_size for path in files)
    largest = max(files, key=lambda path: path.stat().st_size)

    print("[partition] Concluído.")
    print(f"[partition] Municípios particionados: {len(municipio_files)}")
    print(f"[partition] Arquivos criados: {stats['created']}")
    print(f"[partition] Arquivos atualizados: {stats['updated']}")
    print(f"[partition] Arquivos preservados: {stats['preserved']}")
    print(f"[partition] Arquivos removidos: {stats['removed']}")
    print(f"[partition] Erros: {len(errors)}")
    print(f"[partition] Arquivos JSON: {len(files)}")
    print(f"[partition] Tamanho total: {format_size(total_size)}")
    print(f"[partition] Maior arquivo: {largest.relative_to(OUTPUT_DIR)} ({format_size(largest.stat().st_size)})")

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
