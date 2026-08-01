"""Contrato e integração da infraestrutura escolar canônica."""

from __future__ import annotations

import copy
from collections.abc import Iterable, Mapping
from typing import Any

import pandas as pd

from src.school_infrastructure import INDICATORS, aggregate_school_infrastructure


CONTRACT_VERSION = "school-infrastructure-v2"
REFERENCE_YEAR = 2025
INDICATOR_ORDER = (
    "agua_potavel",
    "energia_eletrica",
    "internet",
    "biblioteca_sala_leitura",
    "quadra_esportes",
    "esgoto_rede_publica",
)
CUT_ORDER = (
    "total",
    "publica",
    "municipal",
    "estadual",
    "federal",
    "privada",
    "urbana",
    "rural",
)
RESULT_KEYS = (
    "numerator",
    "denominator",
    "percentage",
    "totalActiveSchools",
    "observedSchools",
    "missingSchools",
    "status",
)
CUT_KINDS = {
    "total": "total",
    "publica": "dependency",
    "municipal": "dependency",
    "estadual": "dependency",
    "federal": "dependency",
    "privada": "dependency",
    "urbana": "location",
    "rural": "location",
}
def _result(row: pd.Series) -> dict[str, Any]:
    percentage = row["percentage"]
    return {
        "numerator": int(row["numerator"]),
        "denominator": int(row["denominator"]),
        "percentage": None if pd.isna(percentage) else float(percentage),
        "totalActiveSchools": int(row["totalActiveSchools"]),
        "observedSchools": int(row["observedSchools"]),
        "missingSchools": int(row["missingSchools"]),
        "status": str(row["status"]),
    }


def build_contracts(
    source: pd.DataFrame,
    municipality_codes: Iterable[str],
) -> dict[str, dict[str, Any]]:
    """Agrega uma vez e produz os contratos municipais em ordem estável."""
    aggregate = aggregate_school_infrastructure(source, REFERENCE_YEAR)
    codes = tuple(sorted(str(code) for code in municipality_codes))
    grouped = {
        str(code): group
        for code, group in aggregate.groupby("id_municipio", sort=True)
    }
    missing = sorted(set(codes) - set(grouped))
    extra = sorted(set(grouped) - set(codes))
    if missing or extra:
        raise ValueError(
            f"Universo municipal divergente; ausentes={missing[:5]}, extras={extra[:5]}"
        )

    definitions = {
        item.key: {
            "label": item.label,
            "sourceVariable": item.source_column.upper(),
        }
        for item in INDICATORS
    }
    contracts: dict[str, dict[str, Any]] = {}
    for code in codes:
        rows = grouped[code].set_index(["recorte", "indicador"])
        cuts: dict[str, Any] = {}
        for cut in CUT_ORDER:
            cut_rows = grouped[code][grouped[code]["recorte"].eq(cut)]
            if len(cut_rows) != len(INDICATOR_ORDER):
                raise ValueError(f"{code}/{cut}: indicadores incompletos")
            active_counts = cut_rows["totalActiveSchools"].unique().tolist()
            if len(active_counts) != 1:
                raise ValueError(f"{code}/{cut}: universo inconsistente")
            cuts[cut] = {
                "kind": CUT_KINDS[cut],
                "totalActiveSchools": int(active_counts[0]),
                "indicators": {
                    indicator: _result(rows.loc[(cut, indicator)])
                    for indicator in INDICATOR_ORDER
                },
            }
        contracts[code] = {
            "contractVersion": CONTRACT_VERSION,
            "referenceYear": REFERENCE_YEAR,
            "availableYears": [REFERENCE_YEAR],
            "universe": {
                "unit": "school",
                "identifier": "CO_ENTIDADE",
                "municipalityVariable": "CO_MUNICIPIO",
                "activeStatus": {
                    "variable": "TP_SITUACAO_FUNCIONAMENTO",
                    "value": 1,
                },
                "deduplication": "CO_ENTIDADE",
            },
            "indicatorDefinitions": definitions,
            "years": [{"year": REFERENCE_YEAR, "cuts": cuts}],
        }
    return contracts


def result_for(
    contract: Mapping[str, Any], indicator: str, cut: str = "total"
) -> Mapping[str, Any]:
    return contract["years"][0]["cuts"][cut]["indicators"][indicator]


def _replace_year_value(
    rows: list[dict[str, Any]], field: str, value: Any, **identity: Any
) -> None:
    for row in rows:
        if row.get("ano") == REFERENCE_YEAR and all(
            row.get(key) == expected for key, expected in identity.items()
        ):
            row[field] = value
            return


def attach_school_infrastructure_contract(
    document: Mapping[str, Any], contract: Mapping[str, Any]
) -> dict[str, Any]:
    """Acrescenta o contrato atual e sincroniza Internet no histórico de 2025."""
    adapted = copy.deepcopy(document)
    network = adapted["blocos"]["rede_escolar"]
    infrastructure = network["infraestrutura"]
    for key in (
        "contractVersion",
        "referenceYear",
        "availableYears",
        "universe",
        "indicatorDefinitions",
        "years",
    ):
        infrastructure[key] = copy.deepcopy(contract[key])

    total = result_for(contract, "internet")
    rounded = (
        None if total["percentage"] is None else round(total["percentage"], 1)
    )
    _replace_year_value(
        infrastructure.get("series", {}).get("internet", []), "valor", rounded
    )
    if infrastructure.get("ultimo_ano") == REFERENCE_YEAR:
        infrastructure.get("resumo_ultimo_ano", {})["internet"] = rounded

    for dimension, rows in (
        ("dependencia", infrastructure.get("por_rede", [])),
        ("localizacao", infrastructure.get("por_localizacao", [])),
    ):
        for row in rows:
            if row.get("ano") != REFERENCE_YEAR:
                continue
            cut = row.get(dimension)
            if cut not in CUT_ORDER:
                continue
            current = result_for(contract, "internet", cut)
            row["escolas"] = current["totalActiveSchools"]
            row["perc_internet"] = (
                None
                if current["percentage"] is None
                else round(current["percentage"], 1)
            )

    _replace_year_value(
        network.get("series", {}).get("internet", []),
        "perc_internet",
        rounded,
    )
    if network.get("ultimo_ano") == REFERENCE_YEAR:
        network.get("resumo_ultimo_ano", {})["perc_internet"] = rounded
    return adapted


def adapt_pne_internet_details(
    payload: Mapping[str, Any] | None, contract: Mapping[str, Any]
) -> dict[str, Any] | None:
    """Substitui 2025 por um adaptador puro do resultado canônico."""
    if payload is None:
        return None
    adapted = copy.deepcopy(payload)
    total = result_for(contract, "internet")
    for key in ("series_total", "series_components", "series_dependencia"):
        if key in adapted:
            adapted[key] = [
                row for row in adapted[key] if row.get("ano") != REFERENCE_YEAR
            ]
    if total["denominator"] > 0:
        adapted.setdefault("series_total", []).append(
            {"ano": REFERENCE_YEAR, "valor": total["numerator"]}
        )
        adapted.setdefault("series_components", []).append(
            {
                "ano": REFERENCE_YEAR,
                "numerador": total["numerator"],
                "denominador": total["denominator"],
                "percentual": total["percentage"],
            }
        )
    dependencies = {
        cut: result_for(contract, "internet", cut)["numerator"]
        for cut in ("publica", "privada", "estadual", "municipal", "federal")
    }
    adapted.setdefault("series_dependencia", []).append(
        {"ano": REFERENCE_YEAR, **dependencies}
    )
    return adapted


def adapt_pne_internet_yearly(
    yearly: pd.DataFrame, contract: Mapping[str, Any]
) -> pd.DataFrame:
    """Mantém 2014–2024 e substitui o percentual de 2025 sem nova fórmula."""
    historical = yearly[yearly["ano"].ne(REFERENCE_YEAR)][["ano", "valor"]].copy()
    current = result_for(contract, "internet")
    if current["percentage"] is not None:
        historical = pd.concat(
            [
                historical,
                pd.DataFrame(
                    [{"ano": REFERENCE_YEAR, "valor": current["percentage"]}]
                ),
            ],
            ignore_index=True,
        )
    return historical.sort_values("ano").reset_index(drop=True)
