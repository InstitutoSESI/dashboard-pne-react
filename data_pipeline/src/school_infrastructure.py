"""Fonte canônica e agregação da infraestrutura escolar.

O módulo opera no grão escola e não conhece contratos públicos ou componentes
de interface. Respostas válidas são exclusivamente 0 e 1; qualquer outro valor
é contabilizado como ausência.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pandas as pd


@dataclass(frozen=True)
class IndicatorDefinition:
    key: str
    label: str
    source_column: str
    positive_value: int


@dataclass(frozen=True)
class CutDefinition:
    key: str
    label: str
    predicate: Callable[[pd.DataFrame], pd.Series]


INDICATORS = (
    IndicatorDefinition(
        "agua_potavel", "Água potável", "in_agua_potavel", 1
    ),
    IndicatorDefinition(
        "energia_eletrica",
        "Energia elétrica",
        "in_energia_inexistente",
        0,
    ),
    IndicatorDefinition("internet", "Internet", "in_internet", 1),
    IndicatorDefinition(
        "biblioteca_sala_leitura",
        "Biblioteca ou sala de leitura",
        "in_biblioteca_sala_leitura",
        1,
    ),
    IndicatorDefinition(
        "quadra_esportes", "Quadra de esportes", "in_quadra_esportes", 1
    ),
    IndicatorDefinition(
        "esgoto_rede_publica",
        "Esgoto por rede pública",
        "in_esgoto_rede_publica",
        1,
    ),
)


CUTS = (
    CutDefinition("total", "Total", lambda frame: pd.Series(True, index=frame.index)),
    CutDefinition(
        "publica",
        "Pública",
        lambda frame: frame["tp_dependencia"].isin([1, 2, 3]),
    ),
    CutDefinition(
        "federal", "Federal", lambda frame: frame["tp_dependencia"].eq(1)
    ),
    CutDefinition(
        "estadual", "Estadual", lambda frame: frame["tp_dependencia"].eq(2)
    ),
    CutDefinition(
        "municipal", "Municipal", lambda frame: frame["tp_dependencia"].eq(3)
    ),
    CutDefinition(
        "privada", "Privada", lambda frame: frame["tp_dependencia"].eq(4)
    ),
    CutDefinition("urbana", "Urbana", lambda frame: frame["tp_localizacao"].eq(1)),
    CutDefinition("rural", "Rural", lambda frame: frame["tp_localizacao"].eq(2)),
)


SOURCE_COLUMNS = tuple(indicator.source_column for indicator in INDICATORS)
CORE_COLUMNS = (
    "ano",
    "id_municipio",
    "cod_escola",
    "situacao_funcionamento",
    "tp_dependencia",
    "tp_localizacao",
)
REQUIRED_COLUMNS = CORE_COLUMNS + SOURCE_COLUMNS

COLUMN_ALIASES = {
    "NU_ANO_CENSO": "ano",
    "CO_MUNICIPIO": "id_municipio",
    "CO_ENTIDADE": "cod_escola",
    "TP_SITUACAO_FUNCIONAMENTO": "situacao_funcionamento",
    "TP_DEPENDENCIA": "tp_dependencia",
    "TP_LOCALIZACAO": "tp_localizacao",
    "IN_AGUA_POTAVEL": "in_agua_potavel",
    "IN_ENERGIA_INEXISTENTE": "in_energia_inexistente",
    "IN_INTERNET": "in_internet",
    "escolas_com_internet": "in_internet",
    "IN_BIBLIOTECA_SALA_LEITURA": "in_biblioteca_sala_leitura",
    "IN_QUADRA_ESPORTES": "in_quadra_esportes",
    "IN_ESGOTO_REDE_PUBLICA": "in_esgoto_rede_publica",
}


def _canonicalize_columns(frame: pd.DataFrame) -> pd.DataFrame:
    rename = {
        source: target
        for source, target in COLUMN_ALIASES.items()
        if source in frame.columns and target not in frame.columns
    }
    canonical = frame.rename(columns=rename).copy()
    missing = [column for column in REQUIRED_COLUMNS if column not in canonical]
    if missing:
        raise ValueError(f"Colunas obrigatórias ausentes: {missing}")
    return canonical


def _active_schools(frame: pd.DataFrame, year: int | None = None) -> pd.DataFrame:
    schools = _canonicalize_columns(frame)
    for column in (
        "ano",
        "cod_escola",
        "situacao_funcionamento",
        "tp_dependencia",
        "tp_localizacao",
    ):
        schools[column] = pd.to_numeric(schools[column], errors="coerce").astype(
            "Int64"
        )
    schools["id_municipio"] = schools["id_municipio"].astype("string")
    if year is not None:
        schools = schools[schools["ano"].eq(year)].copy()
    schools = schools[schools["situacao_funcionamento"].eq(1)].copy()

    missing_keys = schools[
        schools[["ano", "id_municipio", "cod_escola"]].isna().any(axis=1)
    ]
    if not missing_keys.empty:
        raise ValueError("Escola ativa sem ano, município ou CO_ENTIDADE.")

    duplicate_keys = ["ano", "cod_escola"]
    duplicates = schools[schools.duplicated(duplicate_keys, keep=False)]
    if not duplicates.empty:
        conflicts = (
            duplicates.groupby(duplicate_keys, dropna=False)[list(REQUIRED_COLUMNS)]
            .nunique(dropna=False)
            .gt(1)
            .any(axis=1)
        )
        if conflicts.any():
            examples = [tuple(key) for key in conflicts[conflicts].index[:5]]
            raise ValueError(
                "CO_ENTIDADE duplicado com valores conflitantes: "
                f"{examples}"
            )
        schools = schools.drop_duplicates(duplicate_keys, keep="first")
    return schools


def summarize_source_quality(
    frame: pd.DataFrame, year: int | None = None
) -> pd.DataFrame:
    """Conta respostas válidas, ausências originais e códigos inválidos."""
    schools = _active_schools(frame, year)
    rows = []
    for indicator in INDICATORS:
        raw = schools[indicator.source_column]
        numeric = pd.to_numeric(raw, errors="coerce")
        valid = numeric.isin([0, 1])
        present = (
            raw.notna()
            & raw.astype("string").str.strip().ne("").fillna(False)
        )
        invalid = present & ~valid
        rows.append(
            {
                "indicador": indicator.key,
                "observedSchools": int(valid.sum()),
                "missingSchools": int((~valid).sum()),
                "nullSchools": int((~present).sum()),
                "invalidSchools": int(invalid.sum()),
            }
        )
    return pd.DataFrame(rows)


def aggregate_school_infrastructure(
    frame: pd.DataFrame, year: int | None = None
) -> pd.DataFrame:
    """Agrega os seis indicadores por município, ano e oito recortes."""
    schools = _active_schools(frame, year)
    rows: list[dict[str, object]] = []

    for (school_year, municipality), municipal in schools.groupby(
        ["ano", "id_municipio"], sort=True, dropna=False
    ):
        for cut in CUTS:
            sliced = municipal[cut.predicate(municipal)]
            total_active = len(sliced)
            for indicator in INDICATORS:
                values = pd.to_numeric(
                    sliced[indicator.source_column], errors="coerce"
                )
                observed = values.isin([0, 1])
                denominator = int(observed.sum())
                numerator = int(
                    values[observed].eq(indicator.positive_value).sum()
                )
                missing = total_active - denominator
                percentage = (
                    numerator / denominator * 100 if denominator else None
                )
                status = (
                    "unavailable"
                    if denominator == 0
                    else "partial"
                    if missing > 0
                    else "published"
                )
                rows.append(
                    {
                        "ano": int(school_year),
                        "id_municipio": str(municipality),
                        "indicador": indicator.key,
                        "indicadorLabel": indicator.label,
                        "variavelOrigem": indicator.source_column.upper(),
                        "recorte": cut.key,
                        "recorteLabel": cut.label,
                        "totalActiveSchools": total_active,
                        "observedSchools": denominator,
                        "missingSchools": missing,
                        "numerator": numerator,
                        "denominator": denominator,
                        "percentage": percentage,
                        "status": status,
                    }
                )

    result = pd.DataFrame(rows)
    if not result.empty:
        validate_infrastructure_aggregation(result)
        result = result.sort_values(
            ["ano", "id_municipio", "indicador", "recorte"]
        ).reset_index(drop=True)
    return result


def validate_infrastructure_aggregation(result: pd.DataFrame) -> None:
    """Valida invariantes e reconcilia o recorte público."""
    if (result["numerator"] > result["denominator"]).any():
        raise ValueError("numerator não pode superar denominator.")
    if (
        result["observedSchools"] + result["missingSchools"]
        != result["totalActiveSchools"]
    ).any():
        raise ValueError("Observadas e ausentes não reconciliam com o total ativo.")
    if (result["denominator"] != result["observedSchools"]).any():
        raise ValueError("denominator deve ser igual a observedSchools.")

    zero_denominator = result["denominator"].eq(0)
    if result.loc[zero_denominator, "percentage"].notna().any():
        raise ValueError("Denominador zero deve produzir percentage nulo.")
    if result.loc[~zero_denominator, "percentage"].isna().any():
        raise ValueError("Denominador positivo deve produzir percentage.")

    expected_status = result.apply(
        lambda row: (
            "unavailable"
            if row["denominator"] == 0
            else "partial"
            if row["missingSchools"] > 0
            else "published"
        ),
        axis=1,
    )
    if not expected_status.equals(result["status"]):
        raise ValueError("Status incompatível com denominador e ausências.")

    index_columns = ["ano", "id_municipio", "indicador"]
    count_columns = [
        "totalActiveSchools",
        "observedSchools",
        "missingSchools",
        "numerator",
        "denominator",
    ]
    dependencies = result[
        result["recorte"].isin(["federal", "estadual", "municipal"])
    ]
    expected_public = dependencies.groupby(index_columns)[count_columns].sum()
    actual_public = result[result["recorte"].eq("publica")].set_index(index_columns)[
        count_columns
    ]
    if not actual_public.equals(expected_public.reindex(actual_public.index)):
        raise ValueError(
            "Recorte pública não reconcilia com federal + estadual + municipal."
        )
