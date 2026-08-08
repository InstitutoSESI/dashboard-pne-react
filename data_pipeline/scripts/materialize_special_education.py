#!/usr/bin/env python3
"""Materializa e promove atomicamente o contrato special-education-v1."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path


DATA_PIPELINE_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = DATA_PIPELINE_DIR.parent
sys.path.insert(0, str(DATA_PIPELINE_DIR))

from src.data_loader import load_special_education_school_source_data  # noqa: E402
from src.education_municipality_routes import (  # noqa: E402
    EducationMunicipalityRouteCompatibility,
    EducationMunicipalityRouteCompatibilityError,
    load_education_municipality_route_compatibility,
    resolve_education_public_slug,
)
from src.municipality_registry import (  # noqa: E402
    MunicipalityRegistry,
    MunicipalityRegistryError,
    load_municipality_registry,
)
from src.special_education_materialization import (  # noqa: E402
    materialize,
    replace_directory_atomically,
    tree_hash,
)
from src.state_config import (  # noqa: E402
    DEFAULT_STATE_CODE,
    StateConfigError,
    load_state_config,
    normalize_state_code,
)
from src.state_publication import (  # noqa: E402
    StatePublicationError,
    resolve_education_data_dir,
)


def municipalities(
    registry: MunicipalityRegistry,
    route_compatibility: EducationMunicipalityRouteCompatibility,
) -> list[dict]:
    return [
        {
            "id_municipio": record.ibge_code,
            "municipio": record.name,
            "slug": resolve_education_public_slug(record, route_compatibility),
        }
        for record in registry.ordered_records
    ]


def _new_2025_total(contract: dict) -> int | float | None:
    yearly = next(item for item in contract["years"] if item["year"] == 2025)
    return yearly["cuts"]["total"]["specialEducation"]["enrollments"]["value"]


def reconcile_overview(
    stage: Path,
    universe: list[dict],
    overview_municipalities: Path,
) -> dict:
    divergent = []
    compared = 0
    for municipality in universe:
        code = municipality["id_municipio"]
        overview_path = overview_municipalities / f"{code}.json"
        if not overview_path.exists():
            continue
        overview = json.loads(overview_path.read_text(encoding="utf-8"))
        old_point = overview.get("specialEducation", {}).get("total")
        if isinstance(old_point, dict):
            old_value = old_point.get("value")
        else:
            old_value = old_point
        if old_value is None:
            continue
        compared += 1
        new = json.loads(
            (stage / "municipios" / f"{code}.json").read_text(encoding="utf-8")
        )
        new_value = _new_2025_total(new)
        if new_value != old_value:
            divergent.append({"code": code, "overview": old_value, "new": new_value})
    return {
        "comparedMunicipalities": compared,
        "divergenceCount": len(divergent),
        "divergences": divergent[:20],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        help=(
            "Diretorio publico exclusivo da Educacao Especial. Quando omitido, "
            "usa <raiz-publicada-da-UF>/educacao/educacao-especial."
        ),
    )
    parser.add_argument(
        "--state",
        default=DEFAULT_STATE_CODE,
        help=f"Código estadual configurado (padrão: {DEFAULT_STATE_CODE}).",
    )
    args = parser.parse_args(argv)

    try:
        state_code = normalize_state_code(args.state)
        state_config = load_state_config(state_code)
        registry = load_municipality_registry(state_config)
        route_compatibility = load_education_municipality_route_compatibility(
            state_config,
            registry,
        )
        output_directory = (
            args.output
            if args.output is not None
            else resolve_education_data_dir(state_code) / "educacao-especial"
        )
        overview_municipalities = (
            resolve_education_data_dir(state_code) / "visao-geral-municipal"
        )
    except (
        FileNotFoundError,
        StateConfigError,
        MunicipalityRegistryError,
        EducationMunicipalityRouteCompatibilityError,
        StatePublicationError,
    ) as exc:
        print(f"Configuração estadual inválida: {exc}", file=sys.stderr)
        return 2

    source = load_special_education_school_source_data(
        municipality_ids=registry.ids
    )
    universe = municipalities(registry, route_compatibility)
    staging_root = DATA_PIPELINE_DIR / ".staging"
    staging_root.mkdir(parents=True, exist_ok=True)
    first = Path(tempfile.mkdtemp(prefix=".special-first-", dir=staging_root))
    second = Path(tempfile.mkdtemp(prefix=".special-second-", dir=staging_root))
    first_output = first / "educacao-especial"
    second_output = second / "educacao-especial"
    try:
        first_manifest = materialize(source, universe, first_output)
        second_manifest = materialize(source, universe, second_output)
        first_hash = tree_hash(first_output)
        second_hash = tree_hash(second_output)
        if first_hash != second_hash:
            raise ValueError("Duas materializações idênticas produziram hashes diferentes.")
        reconciliation = reconcile_overview(
            first_output,
            universe,
            overview_municipalities,
        )
        if reconciliation["divergenceCount"]:
            raise ValueError(
                f"Snapshot 2025 diverge em {reconciliation['divergenceCount']} municípios."
            )
        replace_directory_atomically(first_output, output_directory.resolve())
        first_output = None
        print(
            json.dumps(
                {
                    "schemaVersion": first_manifest["schemaVersion"],
                    "municipalityCount": first_manifest["municipalityCount"],
                    "contentHash": first_manifest["contentHash"],
                    "deterministic": first_hash == second_hash,
                    "overviewReconciliation": reconciliation,
                    "output": str(output_directory.resolve()),
                },
                ensure_ascii=False,
            )
        )
        return 0
    finally:
        shutil.rmtree(first, ignore_errors=True)
        shutil.rmtree(second, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
