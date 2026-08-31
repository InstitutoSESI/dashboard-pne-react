from __future__ import annotations

import pandas as pd

from src.vocacoes_pne_job5gc import (
    _percent_change,
    build_canonical_matrix,
    build_qa_matrix,
    build_shift_share,
)


def test_percent_change_preserves_zero_base_as_null() -> None:
    assert _percent_change(0, 12) is None
    assert _percent_change(10, 15) == 50.0


def test_shift_share_closes_and_marks_new_activity() -> None:
    occupations = pd.DataFrame(
        [
            {"year": 2019, "municipality_ibge_code": "4313375", "municipality_name": "Nova Santa Rita", "entity_scope": "municipality", "cnae_subclass_code": "1000000", "active_bonds": 100},
            {"year": 2025, "municipality_ibge_code": "4313375", "municipality_name": "Nova Santa Rita", "entity_scope": "municipality", "cnae_subclass_code": "1000000", "active_bonds": 150},
            {"year": 2019, "municipality_ibge_code": "4313375", "municipality_name": "Nova Santa Rita", "entity_scope": "municipality", "cnae_subclass_code": "2000000", "active_bonds": 0},
            {"year": 2025, "municipality_ibge_code": "4313375", "municipality_name": "Nova Santa Rita", "entity_scope": "municipality", "cnae_subclass_code": "2000000", "active_bonds": 5},
        ]
    )
    state = pd.DataFrame(
        [
            {"year": 2019, "cnae_division_code": "10", "active_bonds": 1000},
            {"year": 2025, "cnae_division_code": "10", "active_bonds": 1200},
            {"year": 2019, "cnae_division_code": "20", "active_bonds": 500},
            {"year": 2025, "cnae_division_code": "20", "active_bonds": 600},
        ]
    )
    panel = build_shift_share(occupations, state)
    observed = panel[panel["cnae_division_code"].eq("10")].iloc[0]
    assert abs(observed["closure_residual"]) < 1e-9
    new = panel[panel["cnae_division_code"].eq("20")].iloc[0]
    assert new["component_status"] == "NEW_ACTIVITY_FROM_ZERO_BASE"
    assert pd.isna(new["local_differential_effect"])


def test_matrices_are_canonical_and_never_auto_approve() -> None:
    qa = build_qa_matrix()
    canonical = build_canonical_matrix()
    assert len(qa) == 144
    assert len(canonical) == 144
    assert not qa["automatic_approval"].any()
    assert not canonical["automatic_approval"].any()
    assert canonical["score"].isna().all()
    assert set(qa["qa_code"]) == {f"QA{i}_JOB5GC" for i in range(1, 13)}
    c1 = canonical[canonical["criterion_code"].eq("C1")]
    assert set(c1["criterion"]) == {"relevance_to_pne_pme"}
