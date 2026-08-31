from __future__ import annotations

import pandas as pd
import pytest

from src.vocacoes_pne_job5gcr import (
    NSR_CODE,
    build_canonical_matrix,
    build_corrected_caged_detailed,
    build_fact_catalog,
    build_pne_links,
    build_qa_matrix,
    build_safe_caged_aggregate,
    normalize_numeric_code,
)


def test_numeric_codes_are_normalized_as_text_without_float_coercion() -> None:
    assert normalize_numeric_code("111301", width=7) == "0111301"
    assert normalize_numeric_code("142300", width=7) == "0142300"
    assert normalize_numeric_code("161099", width=7) == "0161099"
    assert normalize_numeric_code("810009", width=7) == "0810009"
    assert normalize_numeric_code("899199", width=7) == "0899199"
    assert normalize_numeric_code("1234", width=6) == "001234"
    assert normalize_numeric_code("ALL", width=7) == "ALL"
    assert pd.isna(normalize_numeric_code(pd.NA, width=6, nullable=True))
    with pytest.raises(ValueError, match="não inteiro textual"):
        normalize_numeric_code("111301.0", width=7)
    with pytest.raises(ValueError, match="não inteiro textual"):
        normalize_numeric_code("01-113-01", width=7)


def _caged_row(
    *,
    scope: str,
    time_grain: str,
    month: int | None,
    admissions: int,
    dismissals: int,
) -> dict[str, object]:
    return {
        "year": 2025,
        "month": month,
        "municipality_ibge_code": "4313375" if scope == "municipality" else pd.NA,
        "municipality_name": "Nova Santa Rita" if scope == "municipality" else "Vale do Sinos",
        "entity_scope": scope,
        "age_group": "18_24",
        "occupation_code": "414140",
        "cnae_subclass_code": "111301",
        "schooling_code": "7",
        "apprentice_indicator_code": "0",
        "admissions": admissions,
        "dismissals": dismissals,
        "balance": admissions - dismissals,
        "regional_admissions": 10,
        "regional_dismissals": 8,
        "annual_admissions_same_contract": 10,
        "time_grain": time_grain,
    }


def test_detailed_caged_preserves_raw_codes_and_nulls_unsafe_shares() -> None:
    original = pd.DataFrame(
        [
            _caged_row(
                scope="municipality",
                time_grain="month",
                month=1,
                admissions=-1,
                dismissals=2,
            ),
            _caged_row(
                scope="municipality",
                time_grain="year",
                month=None,
                admissions=-1,
                dismissals=2,
            ),
            _caged_row(
                scope="region",
                time_grain="month",
                month=1,
                admissions=10,
                dismissals=8,
            ),
            _caged_row(
                scope="region",
                time_grain="year",
                month=None,
                admissions=10,
                dismissals=8,
            ),
        ]
    )
    panel = build_corrected_caged_detailed(original)
    municipal = panel[panel["entity_scope"].eq("municipality")]
    assert set(panel["cnae_subclass_code"]) == {"0111301"}
    assert set(panel["cnae_subclass_code_raw"]) == {"111301"}
    assert set(panel["cnae_division_code"]) == {"01"}
    assert municipal["negative_adjustment_present"].all()
    share_columns = [column for column in panel if column.endswith("share")]
    assert municipal[share_columns].isna().all().all()
    assert set(municipal["share_status"]) == {
        "ADJUSTED_CELL_NOT_SHARE_ELIGIBLE"
    }
    assert not panel["visual_aggregation_eligible"].any()


def test_safe_caged_keeps_monthly_and_annual_grains_reconcilable() -> None:
    rows = []
    for month, admissions, dismissals in ((1, 3, 1), (2, 4, 2)):
        rows.append(
            {
                "entity_scope": "municipality",
                "entity_id": NSR_CODE,
                "municipality_ibge_code": NSR_CODE,
                "municipality_name": "Nova Santa Rita",
                "year": 2025,
                "month": month,
                "time_grain": "monthly_flow",
                "age_group": "18_24",
                "apprentice_indicator_code": "0",
                "admissions": admissions,
                "dismissals": dismissals,
                "negative_adjustment_present": False,
            }
        )
        rows.append(
            {
                "entity_scope": "state",
                "entity_id": "STATE_RS",
                "municipality_ibge_code": pd.NA,
                "municipality_name": "Rio Grande do Sul",
                "year": 2025,
                "month": month,
                "time_grain": "monthly_flow",
                "age_group": "18_24",
                "apprentice_indicator_code": "ALL",
                "admissions": admissions + 10,
                "dismissals": dismissals + 5,
                "negative_adjustment_present": False,
            }
        )
    safe = build_safe_caged_aggregate(pd.DataFrame(rows))
    annual = safe[
        safe["entity_id"].eq(NSR_CODE)
        & safe["time_grain"].eq("annual_flow")
        & safe["aggregation_scope"].eq("all_apprentice_status")
    ].iloc[0]
    assert annual["admissions"] == 7
    assert annual["dismissals"] == 3
    assert annual["balance"] == 4
    assert set(safe["time_grain"]) == {"monthly_flow", "annual_flow"}
    assert not safe[["admissions", "dismissals"]].lt(0).any().any()


def _change_frame(rows: list[dict[str, object]]) -> pd.DataFrame:
    columns = [
        "entity_id",
        "measure",
        "dimension_code",
        "dimension_label",
        "initial_value",
        "final_value",
        "absolute_change",
        "percent_change",
        "regional_initial_value",
        "regional_final_value",
        "final_regional_share",
        "small_volume_sensitive",
        "negative_adjustment_present",
        "label_available",
        "selection_eligible",
    ]
    return pd.DataFrame(rows, columns=columns)


def test_fact_selection_uses_materiality_not_physical_head() -> None:
    rows = []
    for code, change, small in (
        ("01", 10, False),
        ("02", 100, False),
        ("03", 50, False),
        ("04", 20, False),
        ("05", 200, True),
    ):
        rows.append(
            {
                "entity_id": NSR_CODE,
                "measure": "active_bonds",
                "dimension_code": code,
                "dimension_label": f"Setor {code}",
                "initial_value": 100,
                "final_value": 100 + change,
                "absolute_change": change,
                "percent_change": float(change),
                "regional_initial_value": 1000,
                "regional_final_value": 1000 + change,
                "final_regional_share": 0.1,
                "small_volume_sensitive": small,
                "negative_adjustment_present": False,
                "label_available": True,
                "selection_eligible": not small,
            }
        )
    stock = _change_frame(rows)
    empty = _change_frame([])
    shift = pd.DataFrame(
        columns=[
            "municipality_ibge_code",
            "cnae_division_code",
            "local_differential_effect",
            "initial_value",
            "final_value",
            "absolute_change",
            "percent_change",
            "state_sector_initial",
            "state_sector_final",
            "small_volume_sensitive",
            "cnae_division_label",
            "label_available",
            "selection_eligible",
        ]
    )
    facts = build_fact_catalog(stock, empty, empty, empty, shift)
    selected = facts[facts["selected_for_synthesis"]].sort_values("selection_rank")
    assert list(selected["dimension_code"]) == ["02", "03", "04"]
    assert not facts.loc[facts["dimension_code"].eq("05"), "selected_for_synthesis"].any()
    assert not facts["physical_order_used"].any()
    assert not facts["code_order_used"].any()
    assert not facts["alphabetical_order_used"].any()
    assert facts["exact_tie_content_digest_only"].all()
    assert not facts["selection_rule"].str.contains("code only", regex=False).any()


def test_qa_c1_c12_and_pne_links_never_auto_approve() -> None:
    qa = build_qa_matrix()
    canonical = build_canonical_matrix()
    links = build_pne_links()
    assert len(qa) == len(canonical)
    assert set(qa["qa_control_id"]) == {f"QA{i}_JOB5GC" for i in range(1, 13)}
    assert canonical["score"].isna().all()
    assert not canonical["automatic_approval"].any()
    assert not canonical.loc[
        canonical["criterion_id"].eq("C5"), "criterion_status"
    ].eq("SUPPORTED").any()
    assert not links["monitoring_indicator"].map(type).eq(bool).any()
    assert set(links["monitoring_indicator"]) == {
        "not_applicable",
        "not_materialized",
    }
