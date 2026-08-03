"""Contrato e integração da infraestrutura escolar canônica."""

from __future__ import annotations

import copy
import math
from collections.abc import Iterable, Mapping
from typing import Any

import pandas as pd

from src.school_infrastructure import INDICATORS, aggregate_school_infrastructure


CONTRACT_VERSION = "school-infrastructure-v2"
REFERENCE_YEAR = 2025
PNE_INTERNET_DETAIL_KEY = "internet"
PNE_INTERNET_PUBLIC_DEPENDENCY_CUTS = ("federal", "estadual", "municipal")
PNE_INTERNET_DEPENDENCY_CUTS = (
    "publica",
    "privada",
    "estadual",
    "municipal",
    "federal",
)
PNE_INTERNET_DEPENDENCY_POINT_FIELDS = frozenset(
    ("ano", *PNE_INTERNET_DEPENDENCY_CUTS)
)
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


def build_pne_internet_dependency_point(
    contract: Mapping[str, Any],
) -> dict[str, Any]:
    """Projeta o ponto canônico reconciliado de Internet no PNE."""
    return {
        "ano": REFERENCE_YEAR,
        **{
            cut: result_for(contract, PNE_INTERNET_DETAIL_KEY, cut)["numerator"]
            for cut in PNE_INTERNET_DEPENDENCY_CUTS
        },
    }


def _is_finite_non_negative_number(value: Any) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(float(value))
        and value >= 0
    )


def _reference_year_rows(
    value: Any,
    *,
    field_name: str,
    errors: list[str],
) -> list[Mapping[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list):
        errors.append(
            f"Internet {REFERENCE_YEAR}: {field_name} must be a list."
        )
        return []
    return [
        row
        for row in value
        if isinstance(row, Mapping) and row.get("ano") == REFERENCE_YEAR
    ]


def validate_pne_internet_dependency_point(
    point: Mapping[str, Any],
    *,
    series_total: Any,
    series_components: Any,
) -> tuple[str, ...]:
    """Valida o subtotal público e os totais do ponto misto de Internet."""
    errors: list[str] = []
    if not isinstance(point, Mapping):
        return (
            f"Internet {REFERENCE_YEAR}: dependency point must be an object.",
        )

    fields = set(point)
    missing = PNE_INTERNET_DEPENDENCY_POINT_FIELDS - fields
    unexpected = fields - PNE_INTERNET_DEPENDENCY_POINT_FIELDS
    if missing:
        errors.append(
            f"Internet {REFERENCE_YEAR}: dependency point is missing fields: "
            f"{', '.join(sorted(missing))}."
        )
    if unexpected:
        errors.append(
            f"Internet {REFERENCE_YEAR}: dependency point has unexpected fields: "
            f"{', '.join(sorted(unexpected))}."
        )

    year = point.get("ano")
    if isinstance(year, bool) or not isinstance(year, int) or year != REFERENCE_YEAR:
        errors.append(
            f"Internet dependency point year must equal {REFERENCE_YEAR}; got {year!r}."
        )

    dependency_values_valid = True
    for cut in PNE_INTERNET_DEPENDENCY_CUTS:
        if cut not in point:
            dependency_values_valid = False
            continue
        value = point[cut]
        if not _is_finite_non_negative_number(value):
            dependency_values_valid = False
            errors.append(
                f"Internet {REFERENCE_YEAR}: dependency '{cut}' must be a finite, "
                f"non-negative number and cannot be bool; got {value!r}."
            )

    expected_total: int | float | None = None
    if dependency_values_valid:
        expected_public = sum(
            point[cut] for cut in PNE_INTERNET_PUBLIC_DEPENDENCY_CUTS
        )
        if point["publica"] != expected_public:
            errors.append(
                f"Internet {REFERENCE_YEAR}: publica == federal + estadual + "
                f"municipal failed ({point['publica']!r} != {expected_public!r})."
            )
        expected_total = point["publica"] + point["privada"]

    total_rows = _reference_year_rows(
        series_total,
        field_name="series_total",
        errors=errors,
    )
    component_rows = _reference_year_rows(
        series_components,
        field_name="series_components",
        errors=errors,
    )

    # O adaptador omite ambos os pontos quando o universo canônico é indisponível
    # e todas as contagens reconciliadas são zero.
    if expected_total == 0 and not total_rows and not component_rows:
        return tuple(errors)

    if len(total_rows) != 1:
        errors.append(
            f"Internet {REFERENCE_YEAR}: series_total must contain exactly one "
            f"row for the reference year; found {len(total_rows)}."
        )
    if len(component_rows) != 1:
        errors.append(
            f"Internet {REFERENCE_YEAR}: series_components must contain exactly "
            f"one row for the reference year; found {len(component_rows)}."
        )

    total_value: int | float | None = None
    if len(total_rows) == 1:
        candidate = total_rows[0].get("valor")
        if not _is_finite_non_negative_number(candidate):
            errors.append(
                f"Internet {REFERENCE_YEAR}: series_total.valor must be a finite, "
                f"non-negative number and cannot be bool; got {candidate!r}."
            )
        else:
            total_value = candidate
            if expected_total is not None and total_value != expected_total:
                errors.append(
                    f"Internet {REFERENCE_YEAR}: series_total.valor == publica + "
                    f"privada failed ({total_value!r} != {expected_total!r})."
                )

    if len(component_rows) == 1:
        numerator = component_rows[0].get("numerador")
        if not _is_finite_non_negative_number(numerator):
            errors.append(
                f"Internet {REFERENCE_YEAR}: series_components.numerador must be "
                f"a finite, non-negative number and cannot be bool; got {numerator!r}."
            )
        elif total_value is None:
            errors.append(
                f"Internet {REFERENCE_YEAR}: series_components.numerador cannot "
                "reconcile without a valid series_total.valor."
            )
        elif numerator != total_value:
            errors.append(
                f"Internet {REFERENCE_YEAR}: series_components.numerador == "
                f"series_total.valor failed ({numerator!r} != {total_value!r})."
            )

    return tuple(errors)


def reconcile_pne_internet_details(payload: Mapping[str, Any]) -> tuple[str, ...]:
    """Valida, sem efeitos, todos os pontos mistos de Internet no payload."""
    series = payload.get("series_dependencia")
    if not isinstance(series, list):
        return ("Internet series_dependencia must be a list.",)

    mixed_points = []
    dependency_cuts = set(PNE_INTERNET_DEPENDENCY_CUTS) - {"publica"}
    for index, point in enumerate(series):
        if not isinstance(point, Mapping):
            continue
        fields = set(point) - {"ano"}
        if "publica" in fields and fields & dependency_cuts:
            mixed_points.append((index, point))

    if not mixed_points:
        return ()

    errors: list[str] = []
    if len(mixed_points) != 1:
        errors.append(
            f"Internet {REFERENCE_YEAR}: series_dependencia must contain exactly "
            f"one reconciled mixed point; found {len(mixed_points)}."
        )
    for index, point in mixed_points:
        for message in validate_pne_internet_dependency_point(
            point,
            series_total=payload.get("series_total"),
            series_components=payload.get("series_components"),
        ):
            errors.append(f"series_dependencia[{index}]: {message}")
    return tuple(errors)


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
    adapted.setdefault("series_dependencia", []).append(
        build_pne_internet_dependency_point(contract)
    )
    reconciliation_errors = reconcile_pne_internet_details(adapted)
    if reconciliation_errors:
        raise ValueError(
            "Contrato canônico de Internet inválido: "
            + "; ".join(reconciliation_errors)
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
