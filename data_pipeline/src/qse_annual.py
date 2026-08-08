"""Série anual municipal da Quota do Salário-Educação (QSE).

O módulo mantém separados parsing, medição de cobertura, reconciliação e
materialização. A aplicação consome somente os JSONs estáticos gerados aqui.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import re
import unicodedata
from typing import Any, Iterable, Mapping

from pypdf import PdfReader


QSE_ANNUAL_SCHEMA_VERSION = "qse-annual-v1"
QSE_ANNUAL_DATA_VERSION = "fnde-qse-annual-2020-2025-2026-07-21"
QSE_ANNUAL_CUTOFF_DATE = "2026-07-21"
RS_MUNICIPALITY_COUNT = 497
PUBLICATION_COVERAGE_THRESHOLD = Decimal("0.95")

QSE_ANNUAL_SOURCES: dict[int, dict[str, Any]] = {
    2020: {
        "sourceId": "fnde_qse_realized_2020",
        "reference": "Distribuição das quotas estaduais e municipais do Salário-Educação 2020, por ente federado",
        "url": "https://www.gov.br/fnde/pt-br/acesso-a-informacao/acoes-e-programas/financiamento/salario-educacao/media-salario-educacao/consultas/2024/Distribuioporentefederado2020.pdf",
    },
    2021: {
        "sourceId": "fnde_qse_realized_2021",
        "reference": "Distribuição das quotas estaduais e municipais do Salário-Educação 2021, por ente federado",
        "url": "https://www.gov.br/fnde/pt-br/acesso-a-informacao/acoes-e-programas/financiamento/salario-educacao/media-salario-educacao/consultas/2024/Distribuioporentefederado2021.pdf",
    },
    2022: {
        "sourceId": "fnde_qse_realized_2022",
        "reference": "Distribuição realizada — matrículas, coeficientes e recursos distribuídos da QSE 2022",
        "url": "https://www.gov.br/fnde/pt-br/acesso-a-informacao/acoes-e-programas/financiamento/salario-educacao/media-salario-educacao/consultas/2022/DistribuioTotalmatrculasecoeficientesQuota2022.pdf",
    },
    2023: {
        "sourceId": "fnde_qse_realized_2023",
        "reference": "Distribuição realizada — matrículas, coeficientes e recursos distribuídos da QSE 2023",
        "url": "https://www.gov.br/fnde/pt-br/acesso-a-informacao/acoes-e-programas/financiamento/salario-educacao/media-salario-educacao/consultas/2023/DistribuioTotalMatrculaseCoeficientesQuota2023.pdf",
    },
    2024: {
        "sourceId": "fnde_qse_realized_2024",
        "reference": "Distribuição realizada — matrículas, coeficientes e recursos distribuídos da QSE 2024",
        "url": "https://www.gov.br/fnde/pt-br/acesso-a-informacao/acoes-e-programas/financiamento/salario-educacao/defeso-eleitoral/2024/distribuiototalmatrculasecoeficienteqse2024.pdf",
    },
    2025: {
        "sourceId": "fnde_qse_realized_2025",
        "reference": "Distribuição mensal por ente federado da QSE, janeiro a dezembro de 2025",
        "url": "https://www.gov.br/fnde/pt-br/acesso-a-informacao/acoes-e-programas/financiamento/salario-educacao/defeso-eleitoral/2025/distribuiomensalporentefederadodez25.pdf",
        "snapshotFile": "fnde-qse-distribuicao-mensal-ente-2025.pdf",
        "parser": "parse_qse_monthly_lines",
        "documentId": "Demonstrativo da distribuição mensal dos recursos das quotas estaduais e municipais do Salário-Educação 2025 de janeiro a dezembro",
        "columns": [
            "UF", "Ente Federado", "Código IBGE", "Janeiro", "Fevereiro",
            "Março", "Abril", "Maio", "Junho", "Julho", "Agosto",
            "Setembro", "Outubro", "Novembro", "Dezembro", "Total",
        ],
        "collectedAt": "2026-07-21",
        "consultationPageUpdatedAt": "2026-07-03T08:41:00-03:00",
    },
}

QSE_AUDIT_SOURCES: dict[str, dict[str, Any]] = {
    "monthly2024": {
        "sourceId": "fnde_qse_monthly_2024",
        "reference": "Distribuição mensal por ente federado da QSE, janeiro a dezembro de 2024",
        "url": "https://www.gov.br/fnde/pt-br/acesso-a-informacao/acoes-e-programas/financiamento/salario-educacao/defeso-eleitoral/2024/distribuiomensalporentefederadodezembro.pdf",
        "snapshotFile": "fnde-qse-distribuicao-mensal-ente-2024.pdf",
        "parser": "parse_qse_monthly_lines",
        "purpose": "Validação de continuidade metodológica com o valor anual de 2024",
    },
    "enrollmentBasis2025": {
        "sourceId": "fnde_qse_enrollment_basis_2025",
        "reference": "Matrículas consideradas e coeficientes de distribuição da QSE 2025",
        "url": "https://www.gov.br/fnde/pt-br/acesso-a-informacao/acoes-e-programas/financiamento/salario-educacao/media-salario-educacao/consultas/2025/AnexoIIPortariaQSE.pdf",
        "snapshotFile": "fnde-qse-matriculas-coeficientes-2025.pdf",
        "parser": "parse_qse_enrollment_basis_lines",
        "purpose": "Denominador oficial e coeficiente de 2025; a estimativa monetária do anexo não integra a série realizada",
    },
}

# Única divergência nominal observada nos arquivos de 2020 e 2021. É um
# crosswalk explícito, não uma aproximação textual.
QSE_EXPLICIT_NAME_CROSSWALK = {
    "SANTANA DO LIVRAMENTO": "4317103",
    # Os PDFs nacionais de 2020/2021 removem apóstrofo e espaço destes nomes
    # oficiais de AL; o vínculo continua sendo explícito e baseado no código IBGE.
    "OLHO DAGUA DAS FLORES": "2705705",
    "OLHO DAGUA DO CASADO": "2705804",
    "OLHO DAGUA GRANDE": "2705903",
    "TANQUE DARCA": "2709004",
}

_MONEY_TOKEN = r"(?:-?[\d.]+,\d{2}|-)"
_BASIS_NUMBER_TOKEN = r"(?:-?[\d.]+(?:,\d+)?|-)"
QSE_MONTH_NAMES = (
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
)


@dataclass(frozen=True)
class Municipality:
    code: str
    name: str
    slug: str


def normalize_official_name(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^A-Z0-9]+", " ", ascii_value.upper()).strip()


def parse_brazilian_decimal(value: str) -> Decimal | None:
    if value == "-":
        return None
    try:
        return Decimal(value.replace(".", "").replace(",", "."))
    except InvalidOperation as error:
        raise ValueError(f"Número brasileiro inválido: {value}") from error


def extract_pdf_lines(content: bytes) -> list[str]:
    lines: list[str] = []
    for page in PdfReader(BytesIO(content)).pages:
        lines.extend(
            re.sub(r"\s+", " ", line.strip())
            for line in (page.extract_text() or "").splitlines()
            if line.strip()
        )
    return lines


def load_municipalities(
    index_path: Path,
    *,
    expected_municipality_count: int = RS_MUNICIPALITY_COUNT,
    municipality_ibge_prefix: str = "43",
) -> dict[str, Municipality]:
    payload = json.loads(index_path.read_text(encoding="utf-8"))
    municipalities = {
        entry["id_municipio"]: Municipality(
            code=entry["id_municipio"],
            name=entry["nome"],
            slug=entry["slug"],
        )
        for entry in payload["municipios"]
    }
    if len(municipalities) != expected_municipality_count:
        raise ValueError(
            f"Esperados {expected_municipality_count} municípios; "
            f"encontrados {len(municipalities)}."
        )
    invalid_codes = sorted(
        code
        for code in municipalities
        if re.fullmatch(rf"{re.escape(municipality_ibge_prefix)}\d{{5}}", code)
        is None
    )
    if invalid_codes:
        raise ValueError(
            "Códigos municipais fora do prefixo estadual: "
            f"{invalid_codes[:5]}."
        )
    return municipalities


def build_exact_name_map(municipalities: Mapping[str, Municipality]) -> dict[str, str]:
    result: dict[str, str] = {}
    for code, municipality in municipalities.items():
        normalized = normalize_official_name(municipality.name)
        if normalized in result and result[normalized] != code:
            raise ValueError(f"Nome municipal canônico duplicado: {normalized}")
        result[normalized] = code
    result.update(
        {
            name: code
            for name, code in QSE_EXPLICIT_NAME_CROSSWALK.items()
            if code in municipalities
        }
    )
    return result


def _qse_patterns(
    state_code: str,
    municipality_ibge_prefix: str,
) -> tuple[re.Pattern[str], re.Pattern[str], re.Pattern[str], re.Pattern[str]]:
    state = re.escape(state_code)
    prefix = re.escape(municipality_ibge_prefix)
    return (
        re.compile(rf"^{state}\s+(.+?)\s+({_MONEY_TOKEN})$"),
        re.compile(
            rf"^{state}\s+(.+?)\s+({prefix}\d{{5}})\s+"
            rf"([\d.]+(?:,\d{{2}})?|-)\s+([\d,]+|-)\s+({_MONEY_TOKEN})$"
        ),
        re.compile(
            rf"^{state}\s+(.+?)\s+({prefix}\d{{5}}|{prefix})\s+"
            rf"((?:{_MONEY_TOKEN}\s+){{12}}{_MONEY_TOKEN})$"
        ),
        re.compile(
            rf"^{state}\s+(.+?)\s+({prefix}\d{{5}}|{prefix})\s+"
            rf"((?:{_BASIS_NUMBER_TOKEN}\s+){{12}}{_BASIS_NUMBER_TOKEN})$"
        ),
    )


def parse_qse_annual_lines(
    lines: Iterable[str],
    year: int,
    municipalities: Mapping[str, Municipality],
    *,
    state_code: str = "RS",
    municipality_ibge_prefix: str = "43",
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    if year not in QSE_ANNUAL_SOURCES:
        raise ValueError(f"Exercício não configurado: {year}")

    exact_names = build_exact_name_map(municipalities)
    older_pattern, coded_pattern, _, _ = _qse_patterns(
        state_code,
        municipality_ibge_prefix,
    )
    records: dict[str, dict[str, Any]] = {}
    duplicates: list[str] = []
    unmapped: list[str] = []
    null_values: list[str] = []
    official_zeros: list[str] = []
    negative_values: list[str] = []

    for raw_line in lines:
        line = re.sub(r"\s+", " ", raw_line.strip())
        if not line.startswith(f"{state_code} "):
            continue

        if year <= 2021:
            match = older_pattern.match(line)
            if not match:
                continue
            official_name, amount_token = match.groups()
            if normalize_official_name(official_name) == "GOVERNO ESTADUAL":
                continue
            code = exact_names.get(normalize_official_name(official_name))
            if code is None:
                unmapped.append(official_name)
                continue
            enrollment_token = coefficient_token = None
        else:
            match = coded_pattern.match(line)
            if not match:
                continue
            official_name, code, enrollment_token, coefficient_token, amount_token = match.groups()
            if code not in municipalities:
                unmapped.append(f"{code} — {official_name}")
                continue

        if code in records:
            duplicates.append(code)
            continue

        amount = parse_brazilian_decimal(amount_token)
        enrollments = parse_brazilian_decimal(enrollment_token) if enrollment_token else None
        coefficient = parse_brazilian_decimal(coefficient_token) if coefficient_token else None
        if amount is None:
            null_values.append(code)
        elif amount == 0:
            official_zeros.append(code)
        elif amount < 0:
            negative_values.append(code)

        records[code] = {
            "municipalityCode": code,
            "officialName": official_name,
            "distributedAmount": amount,
            "enrollmentBasis": int(enrollments) if enrollments is not None else None,
            "distributionCoefficient": coefficient,
        }

    identified_codes = set(records)
    absent = sorted(set(municipalities) - identified_codes)
    municipalities_with_value = sum(
        record["distributedAmount"] is not None and record["distributedAmount"] >= 0
        for record in records.values()
    )
    total = sum(
        (record["distributedAmount"] for record in records.values()
         if record["distributedAmount"] is not None and record["distributedAmount"] >= 0),
        Decimal("0"),
    )
    quality = {
        "year": year,
        "municipalitiesExpected": len(municipalities),
        "municipalitiesIdentified": len(identified_codes),
        "municipalitiesWithValue": municipalities_with_value,
        "coverageRate": float(Decimal(municipalities_with_value) / Decimal(len(municipalities))),
        "absentMunicipalityCodes": absent,
        "duplicateMunicipalityCodes": sorted(set(duplicates)),
        "unmappedRecords": sorted(set(unmapped)),
        "nullValueMunicipalityCodes": sorted(null_values),
        "officialZeroMunicipalityCodes": sorted(official_zeros),
        "negativeValueMunicipalityCodes": sorted(negative_values),
        "stateAggregate": float(total.quantize(Decimal("0.01"))),
    }
    return records, quality


def parse_qse_monthly_lines(
    lines: Iterable[str],
    year: int,
    municipalities: Mapping[str, Municipality],
    *,
    state_code: str = "RS",
    municipality_ibge_prefix: str = "43",
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    """Extrai o Total oficial e usa os 12 meses somente para conciliação."""
    normalized_lines = [re.sub(r"\s+", " ", line.strip()) for line in lines if line.strip()]
    records: dict[str, dict[str, Any]] = {}
    duplicates: list[str] = []
    unmapped: list[str] = []
    null_values: list[str] = []
    official_zeros: list[str] = []
    negative_values: list[str] = []
    negative_months: list[str] = []
    missing_months: list[str] = []
    monthly_divergences: list[dict[str, Any]] = []
    state_record: dict[str, Any] | None = None
    recognized_rows = 0
    _, _, monthly_pattern, _ = _qse_patterns(
        state_code,
        municipality_ibge_prefix,
    )

    for line in normalized_lines:
        match = monthly_pattern.match(line)
        if not match:
            continue
        recognized_rows += 1
        official_name, code, value_tokens = match.groups()
        values = [parse_brazilian_decimal(token) for token in value_tokens.split()]
        monthly_values = values[:12]
        official_total = values[12]
        monthly_sum = sum(monthly_values, Decimal("0")) if all(
            value is not None for value in monthly_values
        ) else None

        if (
            code == municipality_ibge_prefix
            and normalize_official_name(official_name) == "GOVERNO ESTADUAL"
        ):
            state_record = {
                "officialName": official_name,
                "monthlyAmounts": monthly_values,
                "monthlySum": monthly_sum,
                "officialTotal": official_total,
            }
            continue
        if code not in municipalities:
            unmapped.append(f"{code} — {official_name}")
            continue
        if code in records:
            duplicates.append(code)
            continue

        if any(value is None for value in monthly_values):
            missing_months.append(code)
        if any(value is not None and value < 0 for value in monthly_values):
            negative_months.append(code)
        if official_total is None:
            null_values.append(code)
        elif official_total == 0:
            official_zeros.append(code)
        elif official_total < 0:
            negative_values.append(code)

        difference = None if monthly_sum is None or official_total is None else monthly_sum - official_total
        if difference is not None and difference != 0:
            monthly_divergences.append({
                "municipalityCode": code,
                "monthlySum": float(monthly_sum),
                "officialTotal": float(official_total),
                "absoluteDifference": float(abs(difference)),
            })
        records[code] = {
            "municipalityCode": code,
            "officialName": official_name,
            "distributedAmount": official_total,
            "monthlyAmounts": monthly_values,
            "monthlySum": monthly_sum,
            "enrollmentBasis": None,
            "distributionCoefficient": None,
        }

    identified_codes = set(records)
    municipalities_with_value = sum(
        record["distributedAmount"] is not None and record["distributedAmount"] >= 0
        for record in records.values()
    )
    municipal_total = sum(
        (record["distributedAmount"] for record in records.values()
         if record["distributedAmount"] is not None and record["distributedAmount"] >= 0),
        Decimal("0"),
    )
    joined_headers = normalize_official_name(" ".join(normalized_lines)).replace(" ", "")
    required_columns = ["UF", "Ente Federado", "Código IBGE", *QSE_MONTH_NAMES, "Total"]
    missing_columns = [
        column for column in required_columns
        if normalize_official_name(column).replace(" ", "") not in joined_headers
    ]
    state_difference = None
    if state_record and state_record["monthlySum"] is not None and state_record["officialTotal"] is not None:
        state_difference = state_record["monthlySum"] - state_record["officialTotal"]

    unreconciled_codes = (
        set(missing_months)
        | set(null_values)
        | {item["municipalityCode"] for item in monthly_divergences}
    )
    quality = {
        "year": year,
        "municipalitiesExpected": len(municipalities),
        "municipalitiesIdentified": len(identified_codes),
        "municipalitiesWithValue": municipalities_with_value,
        "coverageRate": float(Decimal(municipalities_with_value) / Decimal(len(municipalities))),
        "absentMunicipalityCodes": sorted(set(municipalities) - identified_codes),
        "duplicateMunicipalityCodes": sorted(set(duplicates)),
        "unmappedRecords": sorted(set(unmapped)),
        "nullValueMunicipalityCodes": sorted(null_values),
        "officialZeroMunicipalityCodes": sorted(official_zeros),
        "negativeValueMunicipalityCodes": sorted(negative_values),
        "negativeMonthMunicipalityCodes": sorted(negative_months),
        "missingMonthMunicipalityCodes": sorted(missing_months),
        "monthlyReconciledMunicipalities": len(records) - len(unreconciled_codes),
        "monthlyDivergenceCount": len(monthly_divergences),
        "maximumMonthlyAbsoluteDifference": max(
            (item["absoluteDifference"] for item in monthly_divergences), default=0.0
        ),
        "monthlyDivergences": monthly_divergences,
        "requiredColumns": required_columns,
        "missingRequiredColumns": missing_columns,
        "inputLineCount": len(normalized_lines),
        "totalRecordsProcessed": recognized_rows,
        "discardedLineCount": len(normalized_lines) - recognized_rows,
        "stateRowsSeparated": 1 if state_record else 0,
        "stateAggregate": float(municipal_total.quantize(Decimal("0.01"))),
        "stateGovernmentOfficialTotal": json_number(
            state_record["officialTotal"] if state_record else None
        ),
        "stateGovernmentMonthlySum": json_number(
            state_record["monthlySum"] if state_record else None
        ),
        "stateGovernmentMonthlyDifference": json_number(state_difference),
    }
    return records, quality


def parse_qse_enrollment_basis_lines(
    lines: Iterable[str],
    municipalities: Mapping[str, Municipality],
    *,
    state_code: str = "RS",
    municipality_ibge_prefix: str = "43",
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    """Extrai somente Total de matrículas e coeficiente do anexo oficial de 2025."""
    records: dict[str, dict[str, Any]] = {}
    duplicates: list[str] = []
    unmapped: list[str] = []
    state_rows = 0
    _, _, _, basis_pattern = _qse_patterns(
        state_code,
        municipality_ibge_prefix,
    )
    for raw_line in lines:
        line = re.sub(r"\s+", " ", raw_line.strip())
        match = basis_pattern.match(line)
        if not match:
            continue
        official_name, code, value_tokens = match.groups()
        if (
            code == municipality_ibge_prefix
            and normalize_official_name(official_name) == "GOVERNO ESTADUAL"
        ):
            state_rows += 1
            continue
        if code not in municipalities:
            unmapped.append(f"{code} — {official_name}")
            continue
        if code in records:
            duplicates.append(code)
            continue
        values = value_tokens.split()
        enrollment_total = parse_brazilian_decimal(values[-3])
        coefficient = parse_brazilian_decimal(values[-2])
        records[code] = {
            "municipalityCode": code,
            "officialName": official_name,
            "enrollmentBasis": int(enrollment_total) if enrollment_total is not None else None,
            "distributionCoefficient": coefficient,
        }

    identified_codes = set(records)
    quality = {
        "year": 2025,
        "municipalitiesExpected": len(municipalities),
        "municipalitiesIdentified": len(identified_codes),
        "coverageRate": float(Decimal(len(identified_codes)) / Decimal(len(municipalities))),
        "absentMunicipalityCodes": sorted(set(municipalities) - identified_codes),
        "duplicateMunicipalityCodes": sorted(set(duplicates)),
        "unmappedRecords": sorted(set(unmapped)),
        "nullEnrollmentMunicipalityCodes": sorted(
            code for code, record in records.items() if record["enrollmentBasis"] is None
        ),
        "nonPositiveEnrollmentMunicipalityCodes": sorted(
            code for code, record in records.items()
            if record["enrollmentBasis"] is not None and record["enrollmentBasis"] <= 0
        ),
        "nullCoefficientMunicipalityCodes": sorted(
            code for code, record in records.items() if record["distributionCoefficient"] is None
        ),
        "stateRowsSeparated": state_rows,
    }
    return records, quality


def merge_2025_enrollment_basis(
    monthly_records: Mapping[str, Mapping[str, Any]],
    basis_records: Mapping[str, Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for code, monthly_record in monthly_records.items():
        basis = basis_records.get(code)
        merged[code] = {
            **monthly_record,
            "enrollmentBasis": basis["enrollmentBasis"] if basis else None,
            "distributionCoefficient": basis["distributionCoefficient"] if basis else None,
        }
    return merged


def validate_publication_quality(quality: Mapping[str, Any]) -> None:
    failures: list[str] = []
    if Decimal(str(quality["coverageRate"])) < PUBLICATION_COVERAGE_THRESHOLD:
        failures.append("cobertura inferior a 95%")
    if quality["year"] == 2025 and quality["municipalitiesWithValue"] != quality["municipalitiesExpected"]:
        failures.append(
            "cobertura de 2025 diferente do universo municipal esperado"
        )
    for key, label in (
        ("duplicateMunicipalityCodes", "duplicidades"),
        ("unmappedRecords", "registros não mapeados"),
        ("negativeValueMunicipalityCodes", "valores negativos"),
    ):
        if quality[key]:
            failures.append(label)
    for key, label in (
        ("missingMonthMunicipalityCodes", "meses ausentes"),
        ("monthlyDivergences", "divergências entre meses e Total"),
        ("negativeMonthMunicipalityCodes", "valores mensais negativos"),
        ("missingRequiredColumns", "colunas obrigatórias ausentes"),
    ):
        if quality.get(key):
            failures.append(label)
    if failures:
        raise ValueError(f"Publicação bloqueada em {quality['year']}: {', '.join(failures)}.")


def reconcile_2024(
    annual_records: Mapping[str, Mapping[str, Any]],
    public_data_root: Path,
) -> dict[str, Any]:
    compared = 0
    divergences: list[dict[str, Any]] = []
    for code, record in sorted(annual_records.items()):
        current_path = public_data_root / "municipios" / code / "financeiro.json"
        current = json.loads(current_path.read_text(encoding="utf-8"))
        current_amount = Decimal(str(current["amounts"]["qseDistributedClosedYear"]["value"]))
        annual_amount = record["distributedAmount"]
        if annual_amount is None:
            continue
        difference = annual_amount - current_amount
        compared += 1
        if difference != 0:
            divergences.append({
                "municipalityCode": code,
                "currentAmount": float(current_amount),
                "annualAmount": float(annual_amount),
                "absoluteDifference": float(abs(difference)),
            })
    return {
        "comparedMunicipalities": compared,
        "divergenceCount": len(divergences),
        "maximumAbsoluteDifference": max(
            (item["absoluteDifference"] for item in divergences),
            default=0.0,
        ),
        "divergences": divergences,
    }


def validate_2025_enrollment_basis(quality: Mapping[str, Any]) -> None:
    failures: list[str] = []
    if quality["municipalitiesIdentified"] != quality["municipalitiesExpected"]:
        failures.append("cobertura diferente do universo municipal esperado")
    for key, label in (
        ("duplicateMunicipalityCodes", "duplicidades"),
        ("unmappedRecords", "códigos não canônicos"),
        ("nullEnrollmentMunicipalityCodes", "matrículas nulas"),
        ("nonPositiveEnrollmentMunicipalityCodes", "matrículas não positivas"),
        ("nullCoefficientMunicipalityCodes", "coeficientes nulos"),
    ):
        if quality[key]:
            failures.append(label)
    if failures:
        raise ValueError(f"Base de matrículas de 2025 bloqueada: {', '.join(failures)}.")


def reconcile_monthly_continuity_2024(
    monthly_records: Mapping[str, Mapping[str, Any]],
    annual_records: Mapping[str, Mapping[str, Any]],
    public_data_root: Path,
) -> dict[str, Any]:
    divergences: list[dict[str, Any]] = []
    compared = 0
    monthly_total = Decimal("0")
    annual_total = Decimal("0")
    contract_total = Decimal("0")
    for code, monthly_record in sorted(monthly_records.items()):
        monthly_amount = monthly_record["distributedAmount"]
        annual_record = annual_records.get(code)
        annual_amount = annual_record["distributedAmount"] if annual_record else None
        current_path = public_data_root / "municipios" / code / "financeiro.json"
        current = json.loads(current_path.read_text(encoding="utf-8"))
        contract_amount = Decimal(str(current["amounts"]["qseDistributedClosedYear"]["value"]))
        if monthly_amount is None or annual_amount is None:
            continue
        compared += 1
        monthly_total += monthly_amount
        annual_total += annual_amount
        contract_total += contract_amount
        annual_difference = monthly_amount - annual_amount
        contract_difference = monthly_amount - contract_amount
        if annual_difference != 0 or contract_difference != 0:
            divergences.append({
                "municipalityCode": code,
                "monthlyTotal": float(monthly_amount),
                "annualSeriesAmount": float(annual_amount),
                "currentContractAmount": float(contract_amount),
                "annualAbsoluteDifference": float(abs(annual_difference)),
                "contractAbsoluteDifference": float(abs(contract_difference)),
            })
    return {
        "comparedMunicipalities": compared,
        "divergenceCount": len(divergences),
        "maximumAbsoluteDifference": max(
            (max(item["annualAbsoluteDifference"], item["contractAbsoluteDifference"])
             for item in divergences),
            default=0.0,
        ),
        "monthlyMunicipalTotal": float(monthly_total.quantize(Decimal("0.01"))),
        "annualSeriesTotal": float(annual_total.quantize(Decimal("0.01"))),
        "currentContractTotal": float(contract_total.quantize(Decimal("0.01"))),
        "divergences": divergences,
    }


def source_digest(content: bytes) -> str:
    return sha256(content).hexdigest()


def json_number(value: Decimal | None) -> float | None:
    return float(value) if value is not None else None


def build_contract(
    municipality: Municipality,
    records_by_year: Mapping[int, Mapping[str, Mapping[str, Any]]],
    source_sha256_by_year: Mapping[int, str],
) -> dict[str, Any]:
    series: list[dict[str, Any]] = []
    for year in sorted(records_by_year):
        record = records_by_year[year].get(municipality.code)
        if not record:
            continue
        amount: Decimal | None = record["distributedAmount"]
        if amount is None or amount < 0:
            continue
        enrollments = record["enrollmentBasis"]
        per_enrollment = amount / Decimal(enrollments) if enrollments and enrollments > 0 else None
        source = QSE_ANNUAL_SOURCES[year]
        series.append({
            "year": year,
            "distributedAmount": json_number(amount),
            "enrollmentBasis": enrollments,
            "distributionCoefficient": json_number(record["distributionCoefficient"]),
            "distributedPerEnrollment": json_number(per_enrollment),
            "sourceId": source["sourceId"],
            "sourceFileReference": source["reference"],
            "sourceFileSha256": source_sha256_by_year[year],
            "cutoffDate": QSE_ANNUAL_CUTOFF_DATE,
        })
    return {
        "schemaVersion": QSE_ANNUAL_SCHEMA_VERSION,
        "dataVersion": QSE_ANNUAL_DATA_VERSION,
        "indicatorId": "qse.distributed_amount",
        "municipality": {"ibgeCode": municipality.code, "name": municipality.name},
        "series": series,
    }


def write_publication(
    output_root: Path,
    municipalities: Mapping[str, Municipality],
    records_by_year: Mapping[int, Mapping[str, Mapping[str, Any]]],
    quality_by_year: Mapping[int, Mapping[str, Any]],
    source_sha256_by_year: Mapping[int, str],
    reconciliation: Mapping[str, Any],
    source_size_by_year: Mapping[int, int] | None = None,
    audit_sources: Iterable[Mapping[str, Any]] = (),
    monthly_continuity_2024: Mapping[str, Any] | None = None,
    enrollment_basis_2025_quality: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    for quality in quality_by_year.values():
        validate_publication_quality(quality)
    if reconciliation["divergenceCount"]:
        raise ValueError("Publicação bloqueada: reconciliação de 2024 possui divergências.")
    if monthly_continuity_2024 and monthly_continuity_2024["divergenceCount"]:
        raise ValueError("Publicação bloqueada: a fonte mensal de 2024 não reproduz a série anual.")
    if enrollment_basis_2025_quality:
        validate_2025_enrollment_basis(enrollment_basis_2025_quality)

    for code, municipality in sorted(municipalities.items()):
        contract = build_contract(municipality, records_by_year, source_sha256_by_year)
        target = output_root / "municipios" / code / "qse-anual.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(contract, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
            encoding="utf-8",
        )

    manifest = {
        "schemaVersion": QSE_ANNUAL_SCHEMA_VERSION,
        "dataVersion": QSE_ANNUAL_DATA_VERSION,
        "generatedAt": "2026-07-21T00:00:00-03:00",
        "cutoffDate": QSE_ANNUAL_CUTOFF_DATE,
        "indicatorId": "qse.distributed_amount",
        "logicalContracts": len(municipalities),
        "years": sorted(records_by_year),
        "sources": [
            {
                **QSE_ANNUAL_SOURCES[year],
                "sha256": source_sha256_by_year[year],
                "fileSizeBytes": source_size_by_year[year] if source_size_by_year else None,
            }
            for year in sorted(records_by_year)
        ],
        "auditSources": list(audit_sources),
        "coverage": [quality_by_year[year] for year in sorted(quality_by_year)],
        "reconciliation2024": reconciliation,
        "monthlyContinuity2024": monthly_continuity_2024,
        "enrollmentBasis2025Quality": enrollment_basis_2025_quality,
    }
    manifest_path = output_root / "financeiro" / "qse-anual-manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    return manifest
