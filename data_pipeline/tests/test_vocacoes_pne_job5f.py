from __future__ import annotations

import json
from pathlib import Path
import sys

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_PIPELINE_DIR = REPO_ROOT / "data_pipeline"
if str(DATA_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_PIPELINE_DIR))


from src.vocacoes_pne_job5f import (
    ALLOWED_STATES,
    MATRIX_COLUMNS,
    NOVA_SANTA_RITA_ID,
    VERDICT,
    build_exploratory_evidence,
    build_opportunity_matrix,
    materialize,
    validate_existing_output,
)


def test_job5f_matrix_covers_both_directions_without_score() -> None:
    evidence = build_exploratory_evidence()
    matrix = build_opportunity_matrix(evidence)

    assert tuple(matrix.columns) == MATRIX_COLUMNS
    assert len(matrix) >= 30
    assert matrix["analysis_id"].is_unique
    assert set(matrix["direction"]) == {1, 2}
    assert set(matrix["status"]).issubset(ALLOWED_STATES)
    assert set(matrix["education_network"]) == {"total_all_dependencies"}
    assert not any("score" in column.casefold() for column in matrix.columns)
    assert matrix[list(MATRIX_COLUMNS)].notna().all().all()
    assert NOVA_SANTA_RITA_ID in json.dumps(
        evidence, ensure_ascii=False, sort_keys=True
    ) or "Nova Santa Rita" in " ".join(matrix["nova_santa_rita"])


def test_job5f_preserves_h2_and_dependency_boundaries() -> None:
    evidence = build_exploratory_evidence()
    matrix = build_opportunity_matrix(evidence)

    assert evidence["h2FrozenStateChanged"] is False
    assert evidence["administrativeDependencyUsedAnalytically"] is False
    dependency = matrix[matrix["analysis_id"].str.contains("DEPENDENCIA")]
    assert set(dependency["status"]) == {"REJECTED"}
    trajectory = matrix[matrix["theme"].str.contains("Trajetória|trajetória", regex=True)]
    assert any("sem recompor" in text or "recomposição" in text for text in trajectory["robustness_limitations"])


def test_job5f_materialization_is_deterministic_and_valid(tmp_path: Path) -> None:
    output = tmp_path / "job5f"
    first = materialize(output)
    first_hashes = {
        path.name: path.read_bytes()
        for path in output.iterdir()
        if path.is_file()
    }
    second = materialize(output)
    second_hashes = {
        path.name: path.read_bytes()
        for path in output.iterdir()
        if path.is_file()
    }

    assert first["verdict"] == VERDICT
    assert second["promotion"] == "unchanged"
    assert first_hashes == second_hashes
    checked = validate_existing_output(output)
    assert checked["schemaValidation"] == "PASS"

    matrix = pd.read_csv(output / "master_analytical_opportunities.csv.gz")
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["summary"]["opportunityCount"] == len(matrix)
    assert manifest["generation"]["databaseUsed"] is False
    assert manifest["generation"]["networkUsed"] is False
    assert manifest["generation"]["publicDataChanged"] is False
    assert manifest["generation"]["frontendChanged"] is False
