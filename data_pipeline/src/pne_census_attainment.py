"""Conclusão escolar: componentes do mesmo universo censitário de 2022.

Não combina os numeradores da SIDRA 10061 com estimativas populacionais.
O snapshot é validado (hash e universo IBGE) pelo leitor original.
"""

from functools import lru_cache

import pandas as pd

from src.pne_goal_11b_census import (
    _combine_ranges,
    _status_precedence,
    _sum_components,
    load_snapshot,
    ratio_result,
)
from src.pne_state_context import load_pne_state_context


CONFIG = {
    "fundamental_concluido_15_29": (
        "populacao_15_29_ensino_fundamental_concluido", "populacao_15_29_total"
    ),
    "medio_concluido_18_29": (
        "populacao_18_29_ensino_medio_concluido", "populacao_18_29_total"
    ),
    "medio_concluido_18_mais": (
        "populacao_18_mais_ensino_medio_concluido", "populacao_18_mais_total"
    ),
}


def secondary_component(age):
    values = age["sourceValues"]
    numerator = _sum_components(
        values[key] for key in ("secondary_complete", "higher_complete")
    )
    denominator = values["total"]
    return {
        "numerator": numerator["value"],
        "denominator": denominator["value"],
        "status": _status_precedence((numerator["status"], denominator["status"])),
    }


def component(row, indicator_id):
    if indicator_id == "fundamental_concluido_15_29":
        return dict(row["fifteenToTwentyNine"])
    if indicator_id == "medio_concluido_18_mais":
        return secondary_component(row["eighteenPlus"])
    if indicator_id == "medio_concluido_18_29":
        return _combine_ranges(
            secondary_component(row["eighteenToTwentyFour"]),
            secondary_component(row["twentyFiveToTwentyNine"]),
        )
    raise KeyError(indicator_id)


@lru_cache(maxsize=2)
def _snapshot(state_code):
    return load_snapshot(state_code=state_code)


def census_results(indicator_id, state_code=None):
    state = load_pne_state_context(state_code)
    rows, _manifest = _snapshot(state.state_code)
    return {
        row["municipalityId"]: {
            **ratio_result(component(row, indicator_id)),
            "year": row["year"],
        }
        for row in rows
    }


@lru_cache(maxsize=6)
def _attainment_frame(indicator_id, state_code):
    state = load_pne_state_context(state_code)
    rows, _manifest = _snapshot(state.state_code)
    numerator, denominator = CONFIG[indicator_id]
    output = []
    for row in rows:
        result = ratio_result(component(row, indicator_id))
        observed = result["dataStatus"] == "available"
        output.append({
            "id_municipio": row["municipalityId"],
            "municipio": row["municipalityName"],
            "ano": row["year"],
            numerator: result["numerator"] if observed else None,
            denominator: result["denominator"] if observed else None,
            "data_status": result["dataStatus"],
            "reason_code": result.get("reasonCode"),
        })
    return pd.DataFrame(output)


def load_attainment_frame(indicator_id, state_code=None):
    state = load_pne_state_context(state_code)
    return _attainment_frame(indicator_id, state.state_code).copy()
