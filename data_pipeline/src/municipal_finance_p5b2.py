from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections.abc import Iterable, Mapping
from typing import Any


ADAPTER_VERSION = "municipal-finance-p5b2-a-v1"
RREO_PARSER_VERSION = "municipal-finance-rreo-p5b2b1-v1"
RREO_LAYOUT_VERSION = "rreo-annex8-municipal-2024-v1"
POC_REQUIRED_FIELDS = (
    "municipality",
    "ibgeCode",
    "referenceYear",
    "period",
    "concept",
    "financialStage",
    "amountNature",
    "value",
    "sourceId",
    "sourceUrl",
    "sourceHash",
    "publishedAt",
    "accessedAt",
    "adapterVersion",
    "notes",
)

SIOPE_REQUIRED_FIELDS = {
    "TIPO",
    "NUM_ANO",
    "NUM_PERI",
    "COD_UF",
    "SIG_UF",
    "COD_MUNI",
    "NOM_MUNI",
    "COD_INDI",
    "COD_EXIB",
    "NOM_INDI",
    "COD_GRUP",
    "NOM_GRUP_INDI",
    "VAL_INDI",
}

MSC_REQUIRED_FIELDS = {
    "tipo_matriz",
    "cod_ibge",
    "classe_conta",
    "conta_contabil",
    "poder_orgao",
    "ano_fonte_recursos",
    "fonte_recursos",
    "funcao",
    "subfuncao",
    "exercicio",
    "mes_referencia",
    "educacao_saude",
    "data_referencia",
    "entrada_msc",
    "natureza_despesa",
    "ano_inscricao",
    "natureza_receita",
    "valor",
    "natureza_conta",
    "tipo_valor",
}


class SourceSchemaError(ValueError):
    pass


class DuplicateGrainError(ValueError):
    pass


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def validate_ibge_code(
    code: str | int,
    municipality_ibge_prefix: str = "43",
    state_code: str = "RS",
) -> str:
    normalized = re.sub(r"\D", "", str(code))
    if re.fullmatch(
        rf"{re.escape(municipality_ibge_prefix)}\d{{5}}",
        normalized,
    ) is None:
        raise ValueError(
            f"Código IBGE municipal de {state_code} inválido: {code!r}"
        )
    return normalized


def siope_code_from_ibge(
    code: str | int,
    municipality_ibge_prefix: str = "43",
    state_code: str = "RS",
) -> str:
    return validate_ibge_code(code, municipality_ibge_prefix, state_code)[:6]


def parse_brazilian_number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    normalized = str(value).strip().replace("R$", "").replace(" ", "")
    if not normalized or normalized in {"-", "--"}:
        return None
    if "," in normalized:
        normalized = normalized.replace(".", "").replace(",", ".")
    return float(normalized)


def _plain_text(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    return " ".join(
        "".join(char for char in text if not unicodedata.combining(char))
        .lower()
        .split()
    )


def _identity_text(value: Any) -> str:
    without_apostrophes = _plain_text(value).replace("'", "").replace("’", "")
    return re.sub(r"[^a-z0-9]+", " ", without_apostrophes).strip()


def assert_schema(row: Mapping[str, Any], required: set[str], source_id: str) -> None:
    missing = sorted(required.difference(row))
    if missing:
        raise SourceSchemaError(f"{source_id}: campos obrigatórios ausentes: {', '.join(missing)}")


def coverage_summary(
    present_codes: Iterable[str],
    registry_codes: Iterable[str],
    *,
    municipality_ibge_prefix: str = "43",
    state_code: str = "RS",
) -> dict[str, Any]:
    registry = {
        validate_ibge_code(code, municipality_ibge_prefix, state_code)
        for code in registry_codes
    }
    present = {
        validate_ibge_code(code, municipality_ibge_prefix, state_code)
        for code in present_codes
    }
    unexpected = sorted(present.difference(registry))
    covered = present.intersection(registry)
    return {
        "denominator": len(registry),
        "covered": len(covered),
        "coverageRate": round(len(covered) / len(registry), 8) if registry else None,
        "missingCodes": sorted(registry.difference(covered)),
        "unexpectedCodes": unexpected,
    }


def detect_duplicate_grain(records: Iterable[Mapping[str, Any]], keys: tuple[str, ...]) -> list[tuple[Any, ...]]:
    seen: set[tuple[Any, ...]] = set()
    duplicates: set[tuple[Any, ...]] = set()
    for record in records:
        grain = tuple(record.get(key) for key in keys)
        if grain in seen:
            duplicates.add(grain)
        seen.add(grain)
    return sorted(duplicates, key=str)


def validate_poc_records(
    records: list[dict[str, Any]],
    *,
    municipality_ibge_prefix: str = "43",
    state_code: str = "RS",
) -> None:
    for position, record in enumerate(records):
        missing = [field for field in POC_REQUIRED_FIELDS if field not in record]
        if missing:
            raise SourceSchemaError(f"registro POC {position}: campos ausentes: {', '.join(missing)}")
        validate_ibge_code(
            record["ibgeCode"],
            municipality_ibge_prefix,
            state_code,
        )
        if not isinstance(record["referenceYear"], int) or not record["period"]:
            raise SourceSchemaError(f"registro POC {position}: exercício/período inválido")
        if not record["financialStage"] or not record["amountNature"]:
            raise SourceSchemaError(f"registro POC {position}: estágio/natureza ausente")
        if record["value"] is None and "ausente" not in _plain_text(record["notes"]):
            raise SourceSchemaError(f"registro POC {position}: nulo sem justificativa de ausência")
        if not re.fullmatch(r"[0-9a-f]{64}", record["sourceHash"]):
            raise SourceSchemaError(f"registro POC {position}: hash SHA-256 inválido")


def _poc_record(
    *,
    municipality: str,
    ibge_code: str,
    reference_year: int,
    period: str,
    concept: str,
    financial_stage: str,
    amount_nature: str,
    value: float | None,
    source_id: str,
    source_url: str,
    source_hash: str,
    published_at: str | None,
    accessed_at: str,
    notes: str,
    dimensions: dict[str, Any] | None = None,
    municipality_ibge_prefix: str = "43",
    state_code: str = "RS",
) -> dict[str, Any]:
    record = {
        "municipality": municipality,
        "ibgeCode": validate_ibge_code(
            ibge_code,
            municipality_ibge_prefix,
            state_code,
        ),
        "referenceYear": int(reference_year),
        "period": period,
        "concept": concept,
        "financialStage": financial_stage,
        "amountNature": amount_nature,
        "value": value,
        "sourceId": source_id,
        "sourceUrl": source_url,
        "sourceHash": source_hash,
        "publishedAt": published_at,
        "accessedAt": accessed_at,
        "adapterVersion": ADAPTER_VERSION,
        "notes": notes,
    }
    if dimensions:
        record["dimensions"] = dimensions
    return record


def classify_siope_indicator(name: str) -> tuple[str, str] | None:
    plain = _plain_text(name)
    if plain.startswith("valor aplicado em mde da receita de impostos"):
        return "mde_applied_value", "BRL"
    if plain.startswith("percentual de aplicacao das receitas de impostos"):
        return "mde_application_rate", "percent"
    if plain.startswith("percentual de aplicacao do fundeb na remuneracao"):
        return "fundeb_professionals_remuneration_rate", "percent"
    if plain.startswith("saldo financeiro do fundeb no exercicio atual"):
        return "fundeb_financial_balance", "BRL"
    return None


def adapt_siope_rows(
    rows: Iterable[Mapping[str, Any]],
    registry_by_siope_code: Mapping[str, Mapping[str, str]],
    *,
    source_url: str,
    source_hash: str,
    accessed_at: str,
    published_at: str | None,
    municipality_ibge_prefix: str = "43",
    state_code: str = "RS",
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for row in rows:
        assert_schema(row, SIOPE_REQUIRED_FIELDS, "fnde_siope_indicators_odata")
        if row["COD_MUNI"] is None:
            continue
        concept_unit = classify_siope_indicator(str(row["NOM_INDI"]))
        if concept_unit is None:
            continue
        municipality = registry_by_siope_code.get(str(row["COD_MUNI"]))
        if municipality is None:
            continue
        concept, unit = concept_unit
        value = parse_brazilian_number(row["VAL_INDI"])
        records.append(
            _poc_record(
                municipality=municipality["name"],
                ibge_code=municipality["ibgeCode"],
                reference_year=int(row["NUM_ANO"]),
                period=f"bimestre_{int(row['NUM_PERI'])}",
                concept=concept,
                financial_stage="calculated_indicator",
                amount_nature="municipal_declared",
                value=value,
                source_id="fnde_siope_indicators_odata",
                source_url=source_url,
                source_hash=source_hash,
                published_at=published_at,
                accessed_at=accessed_at,
                notes=(
                    f"Indicador {row['COD_EXIB']} ({unit}); não equivale, por si só, a transferência federal."
                    if value is not None
                    else "Indicador ausente na resposta oficial; ausência preservada como null."
                ),
                dimensions={
                    "indicatorCode": row["COD_INDI"],
                    "displayCode": row["COD_EXIB"],
                    "indicatorName": row["NOM_INDI"],
                    "unit": unit,
                },
                municipality_ibge_prefix=municipality_ibge_prefix,
                state_code=state_code,
            )
        )
    records.sort(key=lambda item: (item["ibgeCode"], item["referenceYear"], item["period"], item["concept"]))
    duplicates = detect_duplicate_grain(
        records,
        ("ibgeCode", "referenceYear", "period", "concept", "financialStage", "amountNature"),
    )
    if duplicates:
        raise DuplicateGrainError(f"SIOPE: grãos duplicados: {duplicates[:3]}")
    validate_poc_records(
        records,
        municipality_ibge_prefix=municipality_ibge_prefix,
        state_code=state_code,
    )
    return records


_BRL_PATTERN = r"-?\d{1,3}(?:\.\d{3})*,\d{2}"


def _extract_rreo_values(text: str, start: str, end: str | None, expected: int) -> list[float]:
    start_at = text.find(start)
    if start_at < 0:
        raise SourceSchemaError(f"RREO: linha não localizada: {start}")
    fragment = text[start_at : text.find(end, start_at) if end and text.find(end, start_at) >= 0 else None]
    values = [parse_brazilian_number(value) for value in re.findall(_BRL_PATTERN, fragment)]
    if len(values) != expected:
        raise SourceSchemaError(f"RREO: linha {start} tem {len(values)} valores; esperado exatamente {expected}")
    return [float(value) for value in values if value is not None]


def adapt_rreo_text(
    text: str,
    *,
    municipality: str,
    ibge_code: str,
    reference_year: int,
    bimester: int,
    source_url: str,
    source_hash: str,
    accessed_at: str,
    published_at: str | None,
    municipality_ibge_prefix: str = "43",
    state_code: str = "RS",
) -> list[dict[str, Any]]:
    plain = _plain_text(text)
    expected_title = "demonstrativo das receitas e despesas com manutencao e desenvolvimento do ensino - mde"
    expected_municipality = _identity_text(f"{municipality} - {state_code}")
    expected_note = (
        "nos cinco primeiros bimestres do exercicio o acompanhamento sera feito com base na despesa liquidada. "
        "no ultimo bimestre do exercicio, o valor devera corresponder ao total da despesa empenhada"
    )
    if (
        "rreo - anexo 8" not in plain
        or expected_title not in plain
        or f"{bimester}o bimestre/{reference_year}" not in plain
        or expected_municipality not in _identity_text(text)
        or "r$ 1,00" not in plain
        or expected_note not in plain
    ):
        raise SourceSchemaError("RREO: cabeçalho, anexo, exercício ou período inesperado")
    line6 = _extract_rreo_values(text, "6- TOTAL DAS RECEITAS DO FUNDEB RECEBIDAS", "6.1-", 2)
    line15 = _extract_rreo_values(text, "15- MÍNIMO DE 70% DO FUNDEB", "16 -", 4)
    line29 = _extract_rreo_values(text, "29- APLICAÇÃO EM MDE", "RESTOS A PAGAR", 3)
    definitions = (
        ("fundeb_total_received", "received", "municipal_declared", line6[1], "Linha 6, coluna de receitas realizadas até o bimestre.", "6", "b"),
        ("fundeb_professionals_remuneration_applied", "empenhado" if bimester == 6 else "liquidado", "municipal_declared", line15[1], "Linha 15, valor aplicado; a nota 5 define o estágio conforme o bimestre.", "15", "k"),
        ("fundeb_professionals_remuneration_rate", "calculated_indicator", "municipal_declared", line15[3], "Linha 15, percentual após as deduções do demonstrativo.", "15", "m"),
        ("mde_applied_value", "empenhado" if bimester == 6 else "liquidado", "municipal_declared", line29[1], "Linha 29, valor considerado na apuração constitucional.", "29", "aa"),
        ("mde_application_rate", "calculated_indicator", "municipal_declared", line29[2], "Linha 29; não inferido da DCA por função.", "29", "ab"),
    )
    records = [
        _poc_record(
            municipality=municipality,
            ibge_code=ibge_code,
            reference_year=reference_year,
            period=f"bimestre_{bimester}",
            concept=concept,
            financial_stage=stage,
            amount_nature=nature,
            value=value,
            source_id="fnde_siope_rreo_annex8_pdf",
            source_url=source_url,
            source_hash=source_hash,
            published_at=published_at,
            accessed_at=accessed_at,
            notes=notes,
            dimensions={
                "demonstrative": "RREO Anexo 8",
                "line": line,
                "column": column,
                "unit": "BRL" if concept in {"fundeb_total_received", "fundeb_professionals_remuneration_applied", "mde_applied_value"} else "percent",
                "layoutVersion": RREO_LAYOUT_VERSION,
                "parserVersion": RREO_PARSER_VERSION,
                "stageBasisNote": 5,
            },
            municipality_ibge_prefix=municipality_ibge_prefix,
            state_code=state_code,
        )
        for concept, stage, nature, value, notes, line, column in definitions
    ]
    validate_poc_records(
        records,
        municipality_ibge_prefix=municipality_ibge_prefix,
        state_code=state_code,
    )
    return records


def classify_expense_nature(code: str | int | None) -> tuple[str, str] | None:
    digits = re.sub(r"\D", "", str(code or ""))
    if len(digits) < 2:
        return None
    category = {"3": "current_expense", "4": "capital_expense"}.get(digits[0])
    group = {
        "1": "personnel_and_social_charges",
        "3": "other_current_expenses",
        "4": "investments",
        "5": "financial_inversions",
    }.get(digits[1])
    if category is None or group is None:
        return None
    return category, group


def adapt_msc_rows(
    rows: Iterable[Mapping[str, Any]],
    municipality: str,
    *,
    source_url: str,
    source_hash: str,
    accessed_at: str,
    published_at: str | None,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for row in rows:
        assert_schema(row, MSC_REQUIRED_FIELDS, "siconfi_msc_orcamentaria")
        if str(row["funcao"]).zfill(2) != "12" or str(row["conta_contabil"]) != "622130500":
            continue
        nature = classify_expense_nature(row["natureza_despesa"])
        if nature is None:
            continue
        category, group = nature
        records.append(
            _poc_record(
                municipality=municipality,
                ibge_code=str(row["cod_ibge"]),
                reference_year=int(row["exercicio"]),
                period=f"mes_{int(row['mes_referencia']):02d}",
                concept=group,
                financial_stage="paid",
                amount_nature="municipal_declared",
                value=float(row["valor"]) if row["valor"] is not None else None,
                source_id="siconfi_msc_orcamentaria",
                source_url=source_url,
                source_hash=source_hash,
                published_at=published_at,
                accessed_at=accessed_at,
                notes="Conta PCASP 6.2.2.1.3.05.00 (despesa paga); grão bruto preservado, sem soma entre entradas MSC.",
                dimensions={
                    "economicCategory": category,
                    "expenseNature": row["natureza_despesa"],
                    "function": str(row["funcao"]).zfill(2),
                    "subfunction": str(row["subfuncao"]).zfill(3),
                    "account": str(row["conta_contabil"]),
                    "resourceSource": row["fonte_recursos"],
                    "resourceSourceComplement": row.get("complemento_fonte"),
                    "powerOrAgency": row["poder_orgao"],
                    "managementUnit": None,
                    "mscEntry": row["entrada_msc"],
                    "valueType": row["tipo_valor"],
                },
            )
        )
    records.sort(
        key=lambda item: (
            item["ibgeCode"],
            item["period"],
            item["concept"],
            json.dumps(item.get("dimensions"), sort_keys=True),
        )
    )
    validate_poc_records(records)
    return records


def reconciliation_state(left: Mapping[str, Any] | None, right: Mapping[str, Any] | None) -> str:
    if left is None or right is None:
        return "source_missing"
    if left.get("financialStage") != right.get("financialStage"):
        return "not_comparable"
    if left.get("amountNature") != right.get("amountNature"):
        return "not_comparable"
    if left.get("concept") != right.get("concept"):
        return "not_comparable"
    left_value, right_value = left.get("value"), right.get("value")
    if left_value is None or right_value is None:
        return "source_missing"
    return "reconciled" if abs(float(left_value) - float(right_value)) < 0.01 else "divergent_unexplained"
