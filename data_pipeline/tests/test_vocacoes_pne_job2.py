from __future__ import annotations

import gzip
import json
from pathlib import Path
import re
import sys

import pandas as pd
import pytest


DATA_PIPELINE_DIR = Path(__file__).resolve().parents[1]
if str(DATA_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_PIPELINE_DIR))

from src.vocacoes_pne_job2 import (
    FORBIDDEN_STOCK_TABLE,
    assert_outside_public_data,
    eja_distribution_metrics,
    municipal_distribution,
    replace_directory_transactionally,
    require_ibge_code,
    safe_ratio,
    validate_unique_key,
    write_csv_gzip,
    write_json,
)


REPO_ROOT = DATA_PIPELINE_DIR.parent
CONTRACT_PATH = REPO_ROOT / "data_pipeline" / "contracts" / "vocacoes-pne-v7-job2.json"
BRIDGE_PATH = (
    REPO_ROOT
    / "data_pipeline"
    / "contracts"
    / "vocacoes-pne-course-cbo-rs-v1-projection.json"
)
RELEASE_MANIFEST_PATH = (
    REPO_ROOT
    / "data_pipeline"
    / "manifests"
    / "vocacoes-pne-v7-job2-release.json"
)
SCRIPT_PATH = (
    REPO_ROOT / "data_pipeline" / "scripts" / "materialize_vocacoes_pne_v7_job2.py"
)


def test_ibge_identity_accepts_only_text_with_seven_digits() -> None:
    assert require_ibge_code("4313375") == "4313375"
    for invalid in (4313375, 4313375.0, "431337", "04313375", "Nova Santa Rita"):
        with pytest.raises(ValueError):
            require_ibge_code(invalid)


def test_denominator_zero_produces_null() -> None:
    assert safe_ratio(0, 10) == 0
    assert safe_ratio(10, 0) is None
    assert safe_ratio(None, 10) is None


def test_eja_formula_preserves_fraction_scale() -> None:
    metrics = eja_distribution_metrics(
        potential_public=20,
        enrollments=10,
        regional_potential_public=100,
        regional_enrollments=20,
    )
    assert metrics == {
        "participacao_publico_i": 0.2,
        "participacao_matriculas_i": 0.5,
        "diferenca_distribuicao_pp": 0.3,
        "matriculas_por_mil": 500.0,
    }


def test_municipal_comparison_is_distribution_not_simple_mean() -> None:
    summary = municipal_distribution(pd.Series([1.0, 2.0, 100.0]))
    assert summary["municipality_count"] == 3
    assert summary["median"] == 2.0
    assert "mean" not in summary


def test_unique_key_validator_fails_closed() -> None:
    frame = pd.DataFrame(
        [
            {"municipality_ibge_code": "4313375", "year": 2025},
            {"municipality_ibge_code": "4313375", "year": 2025},
        ]
    )
    with pytest.raises(ValueError, match="chave duplicada"):
        validate_unique_key(
            frame,
            ("municipality_ibge_code", "year"),
            label="teste",
        )


def test_gzip_serialization_is_deterministic_and_keeps_null_explicit(
    tmp_path: Path,
) -> None:
    frame = pd.DataFrame(
        [
            {"municipality_ibge_code": "4313375", "value": 0.0},
            {"municipality_ibge_code": "4313409", "value": None},
        ]
    )
    first = tmp_path / "first.csv.gz"
    second = tmp_path / "second.csv.gz"
    write_csv_gzip(first, frame)
    write_csv_gzip(second, frame)
    assert first.read_bytes() == second.read_bytes()
    with gzip.open(first, "rt", encoding="utf-8") as stream:
        text = stream.read()
    assert "4313375,0.0" in text
    assert "4313409,null" in text


def test_transactional_directory_noop_preserves_existing_bytes(tmp_path: Path) -> None:
    target = tmp_path / "output"
    staging = tmp_path / "staging"
    write_json(target / "manifest.json", {"status": "READY"})
    write_json(staging / "manifest.json", {"status": "READY"})
    before = (target / "manifest.json").read_bytes()
    assert replace_directory_transactionally(staging, target) == "unchanged"
    assert (target / "manifest.json").read_bytes() == before
    assert not staging.exists()


def test_transactional_directory_replacement_promotes_validated_candidate(
    tmp_path: Path,
) -> None:
    target = tmp_path / "output"
    staging = tmp_path / "staging"
    write_json(target / "manifest.json", {"version": "old"})
    write_json(staging / "manifest.json", {"version": "new"})
    assert replace_directory_transactionally(staging, target) == "replaced"
    assert json.loads((target / "manifest.json").read_text(encoding="utf-8")) == {
        "version": "new"
    }
    assert not staging.exists()
    assert not (tmp_path / ".output.backup").exists()


def test_research_output_guard_rejects_public_data(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    with pytest.raises(ValueError, match="public/data"):
        assert_outside_public_data(repo / "public" / "data" / "job2", repo)
    assert_outside_public_data(repo / ".tmp" / "vocacoes-pne" / "v7-job2", repo)


def test_contract_lists_every_subjob_and_forbids_defective_stock() -> None:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    assert [item["id"] for item in contract["subjobs"]] == ["2A", "2B", "2C", "2D", "2E"]
    assert sum(len(item["minimumArtifacts"]) for item in contract["subjobs"]) == 20
    assert contract["forbiddenSources"] == [
        {
            "database": "cei",
            "table": f"public.{FORBIDDEN_STOCK_TABLE}",
            "reason": (
                "600834 linhas; 297492 grupos de chave duplicados; "
                "262231 conflitos; 89395 grupos negativos"
            ),
        }
    ]
    assert contract["formulas"]["eja"]["diferencaDistribuicaoStoredScale"] == "fraction_0_1"


def test_versioned_course_cbo_bridge_preserves_r6_contract() -> None:
    bridge = json.loads(BRIDGE_PATH.read_text(encoding="utf-8"))
    assert bridge["source"]["sha256"] == (
        "e11a6d1d6acf961ca0c28d778158571bef64f108ac32f7b3a9df0e2dac21cf8f"
    )
    assert len(bridge["mappings"]) == 115
    assert len(bridge["unmappedCourseCodes"]) == 22
    assert len(bridge["occupationSubgroups"]) == 20
    assert bridge["statistics"]["unmappedCourses"] == 22
    assert bridge["statistics"]["courseOccupationSubgroupPairs"] == 115


def test_versioned_release_manifest_covers_all_job2_artifacts() -> None:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    release = json.loads(RELEASE_MANIFEST_PATH.read_text(encoding="utf-8"))
    expected_paths = {
        path
        for subjob in contract["subjobs"]
        for path in subjob["minimumArtifacts"]
    }
    assert release["output"]["artifactCount"] == 20
    assert release["output"]["artifactRowCount"] == 840105
    assert release["output"]["readyCount"] == 5
    assert {artifact["path"] for artifact in release["artifacts"]} == expected_paths
    assert [subjob["status"] for subjob in release["subjobs"]] == ["READY"] * 5
    assert release["generation"]["idempotencePromotion"] == "unchanged"
    assert release["generation"]["publicDataChanged"] is False


def test_executor_has_no_network_client_or_database_write_statement() -> None:
    source = SCRIPT_PATH.read_text(encoding="utf-8")
    assert not re.search(r"\b(requests|httpx|urllib|FTP|ftplib)\b", source)
    assert not re.search(
        r"(?i)\b(INSERT\s+INTO|UPDATE\s+public\.|DELETE\s+FROM|DROP\s+TABLE|CREATE\s+TABLE)\b",
        source,
    )
    assert "SET TRANSACTION READ ONLY" in source
    assert "vocacoes-pne-course-cbo-rs-v1-projection.json" in source
    assert "os.walk(" not in source
    assert "search_root" not in source
    assert FORBIDDEN_STOCK_TABLE not in "\n".join(
        line for line in source.splitlines() if "FORBIDDEN_STOCK_TABLE" not in line
    )


def test_executor_does_not_numerically_coerce_municipal_identity() -> None:
    source = SCRIPT_PATH.read_text(encoding="utf-8")
    forbidden_patterns = (
        r"int\([^\n)]*municipality_ibge_code",
        r"float\([^\n)]*municipality_ibge_code",
        r"to_numeric\([^\n)]*municipality_ibge_code",
    )
    for pattern in forbidden_patterns:
        assert not re.search(pattern, source)
