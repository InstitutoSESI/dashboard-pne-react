"""Materializa a anatomia pública SIOPE de uma UF via OData oficial do FNDE."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


DATA_PIPELINE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DATA_PIPELINE_DIR))

from src.municipality_registry import load_municipality_registry  # noqa: E402
from src.publication_transaction import promote_files_atomically  # noqa: E402
from src.siope_publication import (  # noqa: E402
    SIOPE_YEARS,
    build_siope_publication,
    fetch_siope_rows,
    write_siope_publication,
)
from src.state_config import DEFAULT_STATE_CODE, load_state_config  # noqa: E402
from src.state_publication import resolve_education_data_dir  # noqa: E402


FILENAMES = (
    "siope_indicadores_dashboard_wide.json",
    "siope_indicadores_dashboard_catalogo.json",
    "siope_indicadores_dashboard_cobertura.json",
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", default=DEFAULT_STATE_CODE)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()

    state = load_state_config(args.state)
    registry = load_municipality_registry(state)
    municipalities = [
        {"ibgeCode": item.ibge_code, "name": item.name, "slug": item.slug}
        for item in registry.ordered_records
    ]
    output = args.output_dir or resolve_education_data_dir(state.state_code) / "siope"
    with ThreadPoolExecutor(max_workers=len(SIOPE_YEARS)) as executor:
        rows_by_year = dict(
            zip(
                SIOPE_YEARS,
                executor.map(
                    lambda year: fetch_siope_rows(year, state.state_code),
                    SIOPE_YEARS,
                ),
                strict=True,
            )
        )
    artifacts = build_siope_publication(
        state_code=state.state_code,
        municipality_ibge_prefix=state.municipality_ibge_prefix,
        municipalities=municipalities,
        rows_by_year=rows_by_year,
    )

    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=f".{output.name}-stage-",
        dir=output.parent,
    ) as stage_directory:
        stage_root = Path(stage_directory)
        write_siope_publication(stage_root, artifacts)
        promote_files_atomically(
            stage_root,
            output,
            [Path(filename) for filename in FILENAMES],
        )
    print(
        json.dumps(
            {
                "stateCode": state.state_code,
                "years": list(SIOPE_YEARS),
                "municipalities": len(municipalities),
                "coverage": artifacts["coverage"]["cobertura_por_ano"],
                "missing2025": artifacts["coverage"]["municipios_ausentes_2025_p6"],
                "output": str(output.resolve()),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
