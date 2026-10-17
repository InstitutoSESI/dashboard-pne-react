"""Adapta o resultado oficial de alfabetização ao contrato do ciclo atual."""

from functools import lru_cache

import pandas as pd

from src.child_literacy import load_snapshot
from src.pne.common import _build_result, _empty_result
from src.pne_state_context import load_pne_state_context


@lru_cache(maxsize=2)
def _snapshot(state_code):
    return load_snapshot(state_code=state_code)


def build_cycle_result(municipality, *, meta, state_code=None):
    state = load_pne_state_context(state_code)
    rows, _state_rows, manifest = _snapshot(state.state_code)
    # Compatibility with the existing name-based calculation entry point;
    # identities and the snapshot universe are validated by the source reader.
    matches = [row for row in rows if municipality in (
        row["municipalityId"], row["municipalityName"]
    )]
    if len(matches) != 1:
        raise ValueError(f"Município sem identidade única: {municipality!r}")
    points = sorted(matches[0]["series"], key=lambda point: point["year"])
    current = points[-1]
    observed = [{"ano": point["year"], "valor": point["value"]}
                for point in points if point["dataStatus"] == "available"]
    if current["dataStatus"] == "available":
        result = _build_result(
            pd.DataFrame(observed), meta, meta_label="Meta PNE 2031",
            target_start_year=points[0]["year"], target_end_year=current["year"],
        )
    else:
        result = _empty_result(meta, meta_label="Meta PNE 2031")
        result.update({"atingida": None, "series": observed})
    result.update({
        "data_status": current["dataStatus"],
        "reason_code": current.get("reasonCode"),
        "reference_year": current["year"],
        "source": "Inep — Indicador Criança Alfabetizada, rede municipal",
        "source_id": "inep_avaliacao_alfabetizacao",
        "network": "municipal",
        "origin_files": manifest["files"],
    })
    return result
