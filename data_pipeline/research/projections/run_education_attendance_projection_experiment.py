"""Run the education-attendance shadow projection experiment."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


DATA_PIPELINE_DIR = Path(__file__).resolve().parents[2]
if str(DATA_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_PIPELINE_DIR))

from src.config import PIPELINE_EXPORT_DIR, POPULATION_PROJECTION_SOURCE_PATH  # noqa: E402
from src.data.repository import get_local_postgres_engine  # noqa: E402
from research.projections.education_attendance_projection_experiment import (  # noqa: E402
    DEFAULT_SEED,
    load_enrollment_panel,
    load_population_panel,
    load_rs_age_series,
    run_experiment,
)


DEFAULT_PANEL = (
    DATA_PIPELINE_DIR
    / "data"
    / "censo_escolar_panel"
    / "censo_escolar_municipal_2007_2025.csv.gz"
)
DEFAULT_OUTPUT = PIPELINE_EXPORT_DIR / "education_attendance_projection_experiment"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel", type=Path, default=DEFAULT_PANEL)
    parser.add_argument(
        "--population-projection", type=Path, default=POPULATION_PROJECTION_SOURCE_PATH
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--bootstrap-iterations", type=int, default=5000)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    enrollment = load_enrollment_panel(args.panel.resolve())
    engine = get_local_postgres_engine()
    try:
        population = load_population_panel(engine)
    finally:
        engine.dispose()
    rs_age_series = load_rs_age_series(args.population_projection.resolve())
    manifest = run_experiment(
        enrollment,
        population,
        rs_age_series,
        output_dir=args.output_dir.resolve(),
        seed=args.seed,
        bootstrap_iterations=args.bootstrap_iterations,
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
