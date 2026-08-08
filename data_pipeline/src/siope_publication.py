"""Publicação estadual dos indicadores municipais oficiais do SIOPE/FNDE."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen


SIOPE_YEARS = (2021, 2022, 2023, 2024, 2025)
SIOPE_PERIOD = 6
SIOPE_SOURCE_LABEL = "SIOPE/FNDE - Indicadores Financeiros e Educacionais via OData"
SIOPE_GENERATED_AT = "2026-08-08T00:00:00-03:00"
SIOPE_ODATA_BASE = (
    "https://www.fnde.gov.br/olinda-ide/servico/DADOS_ABERTOS_SIOPE/"
    "versao/v1/odata/Indicadores_Siope(Ano_Consulta=@Ano_Consulta,"
    "Num_Peri=@Num_Peri,Sig_UF=@Sig_UF)"
)


INDICATOR_DEFINITIONS: tuple[dict[str, Any], ...] = (
    {
        "slug": "aplicacao_mde_percentual", "codigo_indicador": "1.1",
        "nome_dashboard": "Aplicação em MDE", "grupo_dashboard": "Aplicação mínima em educação",
        "unidade": "percentual", "descricao_curta": "Percentual aplicado em manutenção e desenvolvimento do ensino.",
        "interpretacao": "Mostra se o município alcançou o mínimo constitucional de 25% em educação.",
        "direcao_referencia": "cumprimento_minimo", "observacao": "Referência legal: mínimo de 25%.",
        "usar_no_resumo": True,
    },
    {
        "slug": "fundeb_remuneracao_profissionais_percentual", "codigo_indicador": "1.2",
        "nome_dashboard": "FUNDEB em remuneração", "grupo_dashboard": "FUNDEB",
        "unidade": "percentual", "descricao_curta": "Percentual do FUNDEB aplicado na remuneração dos profissionais da educação.",
        "interpretacao": "Indica cumprimento do mínimo de aplicação do FUNDEB em remuneração.",
        "direcao_referencia": "cumprimento_minimo", "observacao": "Referência legal: mínimo de 70%.",
        "usar_no_resumo": True,
    },
    {
        "slug": "fundeb_nao_aplicado_percentual", "codigo_indicador": "1.4",
        "nome_dashboard": "FUNDEB não aplicado", "grupo_dashboard": "FUNDEB",
        "unidade": "percentual", "descricao_curta": "Percentual das receitas do FUNDEB não aplicadas no exercício.",
        "interpretacao": "Ajuda a identificar saldo de recursos do FUNDEB não executado no ano.",
        "direcao_referencia": "menor_melhor", "observacao": "Referência legal indicada pela fonte: máximo de 10%.",
        "usar_no_resumo": True,
    },
    {
        "slug": "valor_aplicado_mde_reais", "codigo_indicador": "8.2",
        "nome_dashboard": "Valor aplicado em MDE", "grupo_dashboard": "Aplicação mínima em educação",
        "unidade": "reais", "descricao_curta": "Valor aplicado em MDE com receita de impostos.",
        "interpretacao": "Mostra o volume financeiro aplicado em educação; deve ser interpretado junto ao porte do município.",
        "direcao_referencia": "informativo", "observacao": "Valor nominal em reais, sem correção inflacionária.",
        "usar_no_resumo": False,
    },
    {
        "slug": "fundeb_educacao_infantil_percentual", "codigo_indicador": "2.1",
        "nome_dashboard": "FUNDEB na educação infantil", "grupo_dashboard": "FUNDEB",
        "unidade": "percentual", "descricao_curta": "Percentual dos recursos do FUNDEB aplicados na educação infantil.",
        "interpretacao": "Ajuda a entender a priorização da educação infantil dentro do uso do FUNDEB.",
        "direcao_referencia": "informativo", "observacao": "Não classificar maior ou menor como melhor sem contexto de oferta e matrícula.",
        "usar_no_resumo": False,
    },
    {
        "slug": "fundeb_ensino_fundamental_percentual", "codigo_indicador": "2.2",
        "nome_dashboard": "FUNDEB no ensino fundamental", "grupo_dashboard": "FUNDEB",
        "unidade": "percentual", "descricao_curta": "Percentual dos recursos do FUNDEB aplicados no ensino fundamental.",
        "interpretacao": "Ajuda a entender a distribuição do FUNDEB entre etapas de ensino.",
        "direcao_referencia": "informativo", "observacao": "Não classificar maior ou menor como melhor sem contexto de oferta e matrícula.",
        "usar_no_resumo": False,
    },
    {
        "slug": "despesas_educacao_total_percentual", "codigo_indicador": "2.8",
        "nome_dashboard": "Educação nas despesas totais", "grupo_dashboard": "Aplicação mínima em educação",
        "unidade": "percentual", "descricao_curta": "Percentual das despesas em educação em relação às despesas de todas as áreas.",
        "interpretacao": "Mostra o peso da educação no conjunto das despesas municipais.",
        "direcao_referencia": "informativo", "observacao": "Indicador de composição orçamentária; não indica qualidade do gasto por si só.",
        "usar_no_resumo": False,
    },
    {
        "slug": "investimento_aluno_basica_reais", "codigo_indicador": "4.8",
        "nome_dashboard": "Investimento por aluno da educação básica", "grupo_dashboard": "Gasto por aluno",
        "unidade": "reais", "descricao_curta": "Investimento educacional por aluno da educação básica.",
        "interpretacao": "Permite acompanhar o gasto por aluno ao longo do tempo e comparar municípios com cautela.",
        "direcao_referencia": "informativo", "observacao": "Valor nominal em reais, sem correção inflacionária.",
        "usar_no_resumo": True,
    },
    {
        "slug": "investimento_aluno_infantil_reais", "codigo_indicador": "4.1",
        "nome_dashboard": "Investimento por aluno da educação infantil", "grupo_dashboard": "Gasto por aluno",
        "unidade": "reais", "descricao_curta": "Investimento educacional por aluno da educação infantil.",
        "interpretacao": "Apoia leitura do esforço financeiro na educação infantil.",
        "direcao_referencia": "informativo", "observacao": "Valor nominal em reais, sem correção inflacionária.",
        "usar_no_resumo": False,
    },
    {
        "slug": "investimento_aluno_fundamental_reais", "codigo_indicador": "4.2",
        "nome_dashboard": "Investimento por aluno do ensino fundamental", "grupo_dashboard": "Gasto por aluno",
        "unidade": "reais", "descricao_curta": "Investimento educacional por aluno do ensino fundamental.",
        "interpretacao": "Apoia leitura do esforço financeiro no ensino fundamental.",
        "direcao_referencia": "informativo", "observacao": "Valor nominal em reais, sem correção inflacionária.",
        "usar_no_resumo": False,
    },
    {
        "slug": "despesa_professores_aluno_basica_reais", "codigo_indicador": "4.10",
        "nome_dashboard": "Despesa com professores por aluno", "grupo_dashboard": "Despesas com pessoal",
        "unidade": "reais", "descricao_curta": "Despesa com professores por aluno da educação básica.",
        "interpretacao": "Mostra o gasto por aluno associado à remuneração de professores.",
        "direcao_referencia": "informativo", "observacao": "Valor nominal em reais; não deve ser usado isoladamente para julgar eficiência.",
        "usar_no_resumo": False,
    },
    {
        "slug": "receitas_impostos_total_percentual", "codigo_indicador": "6.2",
        "nome_dashboard": "Impostos na receita total", "grupo_dashboard": "Receitas da educação",
        "unidade": "percentual", "descricao_curta": "Percentual das receitas de impostos em relação à receita total.",
        "interpretacao": "Ajuda a entender a composição das receitas consideradas no financiamento educacional.",
        "direcao_referencia": "informativo", "observacao": "Cobertura menor em alguns anos; usar com aviso de disponibilidade.",
        "usar_no_resumo": False,
    },
    {
        "slug": "resultado_financeiro_exercicio_reais", "codigo_indicador": "7.1",
        "nome_dashboard": "Resultado financeiro do exercício", "grupo_dashboard": "Resultado financeiro",
        "unidade": "reais", "descricao_curta": "Superávit ou déficit do ente federado no exercício.",
        "interpretacao": "Indica o resultado financeiro anual informado no SIOPE.",
        "direcao_referencia": "informativo", "observacao": "Valor nominal em reais; superávit ou déficit precisa ser lido junto ao contexto fiscal.",
        "usar_no_resumo": False,
    },
    {
        "slug": "saldo_financeiro_fundeb_reais", "codigo_indicador": "7.2",
        "nome_dashboard": "Saldo financeiro do FUNDEB", "grupo_dashboard": "Resultado financeiro",
        "unidade": "reais", "descricao_curta": "Saldo financeiro do FUNDEB no exercício atual.",
        "interpretacao": "Mostra o saldo financeiro associado ao FUNDEB no ano.",
        "direcao_referencia": "informativo", "observacao": "Valor nominal em reais; deve ser interpretado com dados de execução e calendário financeiro.",
        "usar_no_resumo": False,
    },
)


def siope_source_url(year: int, state_code: str) -> str:
    query = urlencode(
        {"@Ano_Consulta": year, "@Num_Peri": SIOPE_PERIOD, "@Sig_UF": f"'{state_code}'"}
    )
    return f"{SIOPE_ODATA_BASE}?{query}"


def fetch_siope_rows(year: int, state_code: str) -> list[dict[str, Any]]:
    url = siope_source_url(year, state_code)
    request = Request(url, headers={"User-Agent": "Dashboard-PNE-SIOPE/1.0"})
    with urlopen(request, timeout=120) as response:
        payload = json.load(response)
    rows = payload.get("value")
    if not isinstance(rows, list):
        raise ValueError(f"OData SIOPE {year} não retornou uma lista em value.")
    return rows


def _json_number(value: object) -> tuple[int | float | None, str | None]:
    if value is None or str(value).strip() == "":
        return None, None
    original = str(value).strip()
    try:
        decimal = Decimal(original.replace(",", "."))
    except InvalidOperation as exc:
        raise ValueError(f"VAL_INDI inválido no OData SIOPE: {value!r}.") from exc
    if not decimal.is_finite():
        raise ValueError(f"VAL_INDI não finito no OData SIOPE: {value!r}.")
    number: int | float = int(decimal) if decimal == decimal.to_integral() else float(decimal)
    return number, original


def _coverage(year: int, present: int, expected: int) -> dict[str, Any]:
    incomplete = present != expected
    observation = (
        f"Cobertura incompleta no periodo {SIOPE_PERIOD}: {present} de {expected} municipios."
        if incomplete
        else f"Cobertura completa no periodo {SIOPE_PERIOD}."
    )
    return {
        "ano": year,
        "periodo": SIOPE_PERIOD,
        "qtd_municipios_presentes": present,
        "qtd_municipios_esperados": expected,
        "percentual_cobertura": round(100 * present / expected, 2),
        "ano_completo_para_comparacao": not incomplete,
        "cobertura_incompleta": incomplete,
        "observacao": observation,
    }


def build_siope_publication(
    *,
    state_code: str,
    municipality_ibge_prefix: str,
    municipalities: Sequence[Mapping[str, str]],
    rows_by_year: Mapping[int, Sequence[Mapping[str, Any]]],
    generated_at: str = SIOPE_GENERATED_AT,
) -> dict[str, dict[str, Any]]:
    """Monta catálogo, cobertura e wide sem imputar indicadores ausentes."""

    if tuple(sorted(rows_by_year)) != SIOPE_YEARS:
        raise ValueError(f"SIOPE exige a janela oficial {list(SIOPE_YEARS)}.")
    registry = {
        str(item["ibgeCode"]): {"name": str(item["name"]), "slug": str(item["slug"])}
        for item in municipalities
    }
    if len(registry) != len(municipalities) or not registry:
        raise ValueError("Registro municipal SIOPE vazio ou com códigos duplicados.")
    pattern = re.compile(rf"{re.escape(municipality_ibge_prefix)}\d{{5}}")
    invalid = sorted(code for code in registry if pattern.fullmatch(code) is None)
    if invalid:
        raise ValueError(f"Registro municipal fora do prefixo estadual: {invalid[:5]}.")
    by_siope_code = {code[:6]: code for code in registry}
    if len(by_siope_code) != len(registry):
        raise ValueError("Crosswalk SIOPE/IBGE contém colisões nos seis primeiros dígitos.")

    definitions_by_code = {item["codigo_indicador"]: item for item in INDICATOR_DEFINITIONS}
    observations: dict[str, list[tuple[int, str, str]]] = {
        code: [] for code in definitions_by_code
    }
    values: dict[str, dict[int, dict[str, dict[str, Any]]]] = {
        code: {} for code in registry
    }
    raw_catalog_codes: set[str] = set()

    for year in SIOPE_YEARS:
        seen: set[tuple[str, str]] = set()
        for row in rows_by_year[year]:
            if row.get("SIG_UF") != state_code:
                raise ValueError(f"Linha SIOPE {year} pertence a outra UF: {row.get('SIG_UF')!r}.")
            if row.get("NUM_ANO") != year or row.get("NUM_PERI") != SIOPE_PERIOD:
                raise ValueError(f"Linha SIOPE fora do exercício/período esperado em {year}.")
            if row.get("TIPO") != "Municipal":
                continue
            indicator_code = str(row.get("COD_EXIB") or "").strip()
            raw_catalog_codes.add(indicator_code)
            if indicator_code not in definitions_by_code:
                continue
            siope_code = re.sub(r"\D", "", str(row.get("COD_MUNI") or ""))
            ibge_code = by_siope_code.get(siope_code)
            if ibge_code is None:
                raise ValueError(f"Código municipal SIOPE sem crosswalk oficial: {siope_code!r}.")
            key = (ibge_code, indicator_code)
            if key in seen:
                raise ValueError(f"Indicador SIOPE duplicado em {year}: {ibge_code}/{indicator_code}.")
            seen.add(key)
            numeric, original = _json_number(row.get("VAL_INDI"))
            if numeric is None:
                continue
            definition = definitions_by_code[indicator_code]
            values[ibge_code].setdefault(year, {})[definition["slug"]] = {
                "valor": numeric,
                "valor_original": original,
                "unidade": definition["unidade"],
                "codigo_indicador": indicator_code,
                "nome_dashboard": definition["nome_dashboard"],
                "grupo_dashboard": definition["grupo_dashboard"],
                "direcao_referencia": definition["direcao_referencia"],
            }
            observations[indicator_code].append(
                (year, ibge_code, str(row.get("NOM_INDI") or "").strip())
            )

    coverage_by_year = [
        _coverage(
            year,
            sum(bool(values[code].get(year)) for code in registry),
            len(registry),
        )
        for year in SIOPE_YEARS
    ]
    coverage_map = {item["ano"]: item for item in coverage_by_year}
    wide_municipalities: dict[str, Any] = {}
    for ibge_code in sorted(registry):
        years: dict[str, Any] = {}
        for year in SIOPE_YEARS:
            indicators = values[ibge_code].get(year)
            if not indicators:
                continue
            year_coverage = coverage_map[year]
            years[str(year)] = {
                "ano": year,
                "periodo": SIOPE_PERIOD,
                "cobertura_incompleta": year_coverage["cobertura_incompleta"],
                "observacao_cobertura": year_coverage["observacao"],
                "indicadores": dict(sorted(indicators.items())),
            }
        wide_municipalities[ibge_code] = {
            "id_municipio": ibge_code,
            "municipio": registry[ibge_code]["name"],
            "anos": years,
        }

    latest_year = SIOPE_YEARS[-1]
    missing_latest = [
        {
            "id_municipio": code,
            "municipio": registry[code]["name"],
            "status": "municipio_ausente",
        }
        for code in sorted(registry)
        if not values[code].get(latest_year)
    ]
    incomplete_indicators: list[dict[str, Any]] = []
    for year in SIOPE_YEARS:
        expected_in_year = sum(bool(values[code].get(year)) for code in registry)
        for definition in INDICATOR_DEFINITIONS:
            present = sum(
                definition["slug"] in values[code].get(year, {}) for code in registry
            )
            if present == expected_in_year:
                continue
            incomplete_indicators.append(
                {
                    "ano": year,
                    "periodo": SIOPE_PERIOD,
                    "codigo_indicador": definition["codigo_indicador"],
                    "slug": definition["slug"],
                    "qtd_municipios_presentes": present,
                    "qtd_municipios_esperados_no_ano": expected_in_year,
                    "percentual_cobertura_no_ano": (
                        round(100 * present / expected_in_year, 2)
                        if expected_in_year
                        else 0.0
                    ),
                    "cobertura_incompleta": True,
                }
            )

    catalog_indicators = []
    for definition in INDICATOR_DEFINITIONS:
        occurrences = observations[definition["codigo_indicador"]]
        if not occurrences:
            raise ValueError(
                f"Indicador oficial ausente em toda a janela: {definition['codigo_indicador']}."
            )
        most_recent_name = sorted(occurrences, key=lambda item: (item[0], item[1]))[-1][2]
        years = [item[0] for item in occurrences]
        catalog_indicators.append(
            {
                **definition,
                "nome_original": most_recent_name,
                "usar_no_grafico_historico": True,
                "usar_na_tabela": True,
                "primeira_ocorrencia_ano": min(years),
                "ultima_ocorrencia_ano": max(years),
                "qtd_ocorrencias_catalogo": len(occurrences),
                "qtd_municipios_catalogo": len({item[1] for item in occurrences}),
            }
        )

    wide = {
        "generated_at": generated_at,
        "fonte": SIOPE_SOURCE_LABEL,
        "periodo_utilizado": SIOPE_PERIOD,
        "total_municipios": len(registry),
        "indicadores": [item["slug"] for item in INDICATOR_DEFINITIONS],
        "cobertura_por_ano": coverage_by_year,
        "municipios": wide_municipalities,
    }
    catalog = {
        "generated_at": generated_at,
        "fonte_catalogo": SIOPE_SOURCE_LABEL,
        "total_indicadores_catalogo_bruto": len(raw_catalog_codes),
        "total_indicadores_selecionados": len(INDICATOR_DEFINITIONS),
        "indicadores": catalog_indicators,
    }
    coverage = {
        "generated_at": generated_at,
        "fonte": SIOPE_SOURCE_LABEL,
        "periodo_utilizado": SIOPE_PERIOD,
        "qtd_municipios_esperados": len(registry),
        "cobertura_por_ano": coverage_by_year,
        "municipios_ausentes_2025_p6": missing_latest,
        "indicadores_selecionados_com_cobertura_incompleta": incomplete_indicators,
        "observacao_interface": "Para cada ano, foi considerado o dado declarado no 6º bimestre.",
        "codigos_indicadores_selecionados": [
            item["codigo_indicador"] for item in INDICATOR_DEFINITIONS
        ],
    }
    artifacts = {"wide": wide, "catalog": catalog, "coverage": coverage}
    validate_siope_publication(artifacts, registry)
    return artifacts


def validate_siope_publication(
    artifacts: Mapping[str, Mapping[str, Any]],
    registry: Mapping[str, Mapping[str, str]],
) -> None:
    wide = artifacts["wide"]
    catalog = artifacts["catalog"]
    coverage = artifacts["coverage"]
    if wide.get("total_municipios") != len(registry):
        raise ValueError("Wide SIOPE diverge do universo municipal.")
    if set(wide.get("municipios", {})) != set(registry):
        raise ValueError("Wide SIOPE não contém exatamente o cadastro municipal.")
    if catalog.get("total_indicadores_selecionados") != len(INDICATOR_DEFINITIONS):
        raise ValueError("Catálogo SIOPE perdeu indicadores selecionados.")
    latest = str(SIOPE_YEARS[-1])
    absent = {
        code for code, municipality in wide["municipios"].items()
        if latest not in municipality["anos"]
    }
    declared_absent = {
        item["id_municipio"] for item in coverage["municipios_ausentes_2025_p6"]
    }
    if absent != declared_absent:
        raise ValueError("Ausências SIOPE de 2025 não reconciliam com a cobertura.")
    for municipality in wide["municipios"].values():
        for annual in municipality["anos"].values():
            for indicator in annual["indicadores"].values():
                if indicator.get("valor") is None:
                    raise ValueError("Indicador SIOPE nulo foi publicado como valor.")


def write_siope_publication(directory: Path, artifacts: Mapping[str, Any]) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    filenames = {
        "wide": "siope_indicadores_dashboard_wide.json",
        "catalog": "siope_indicadores_dashboard_catalogo.json",
        "coverage": "siope_indicadores_dashboard_cobertura.json",
    }
    for key, filename in filenames.items():
        (directory / filename).write_text(
            json.dumps(artifacts[key], ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
