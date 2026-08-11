from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import unicodedata
from copy import deepcopy
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from pypdf import PdfReader


ICMS_EDUCATION_SOURCE_ID = "rs_dee_imers_pre_2022_2024"
ICMS_EDUCATION_STATE_CODE = "RS"
ICMS_EDUCATION_BUNDLE_SCHEMA = "icms-education-source-bundle-v1"
ICMS_EDUCATION_ADAPTER_VERSION = "icms-education-rs-v1"
ICMS_EDUCATION_PARSER_VERSION = "imersvis-csv-v1"
ICMS_EDUCATION_LAYOUT_VERSION = "imersvis-csv-77-columns-2024"
ICMS_EDUCATION_METHODOLOGY_VERSION = "imers-pre-nota-tecnica-100-2024"
ICMS_EDUCATION_OFFICIAL_PAGE = "https://dee.rs.gov.br/imers"
ICMS_EDUCATION_APP_URL = "https://imersvis.dee.rs.gov.br/"
ICMS_EDUCATION_RESULTS_URL = (
    "https://dee.rs.gov.br/upload/arquivos/202607/"
    "01101721-01101510-vf-ppt-coletiva-imers.pdf"
)

EXPECTED_REFERENCE_YEARS = (2022, 2023, 2024)
EXPECTED_MUNICIPALITIES = 497
IMERS_FORMULA_TOLERANCE = Decimal("0.00001")
MUNICIPAL_SIZE_FORMULA_TOLERANCE = Decimal("0.00000001")
PRE_TOTAL_WARNING_TOLERANCE = Decimal("0.000001")
PRE_TOTAL_FAIL_TOLERANCE = Decimal("0.005")
PRE_FORMULA_FAIL_TOLERANCE = Decimal("0.001")

DISTRIBUTION_CONTEXT = {
    2022: {"distributionYear": 2024, "ipmEducationCriterionWeightPercent": Decimal("10")},
    2023: {"distributionYear": 2025, "ipmEducationCriterionWeightPercent": Decimal("11.4")},
    2024: {"distributionYear": 2026, "ipmEducationCriterionWeightPercent": Decimal("12.8")},
}

REQUIRED_COLUMNS = {
    "CO_MUN7",
    "NOME_MUN",
    "ANO",
    "IQA",
    "IQI",
    "IQF",
    "IA",
    "IMERS",
    "POP",
    "NM",
    "NAV",
    "POP/SOMA(POP)",
    "NAV/SOMA(NAV)",
    "NM/SOMA(NM)",
    "PORTE_PERCENTUAL",
    "PRE_PERCENTUAL",
}

ARTIFACT_PATHS = {
    "raw_data": Path("raw/imers-pre-2022-2024.csv"),
    "data_dictionary": Path("documents/data-dictionary.pdf"),
    "methodology_note": Path("documents/methodology-note-100-2024.pdf"),
    "results_presentation": Path("documents/results-presentation-2024.pdf"),
}

ICMS_EDUCATION_SOURCE_CATALOG = {
    "name": "IMERS e Percentual de Recursos da Educação (PRE)",
    "url": ICMS_EDUCATION_OFFICIAL_PAGE,
    "agency": "DEE/SPGG e SEDUC/RS",
    "referenceYear": 2024,
    "referenceYears": list(EXPECTED_REFERENCE_YEARS),
    "status": "integrated",
    "municipalKey": "ibge_code",
    "stateCodes": [ICMS_EDUCATION_STATE_CODE],
    "uses": [
        "icms_education_imers",
        "icms_education_pre_share",
        "icms_education_components",
    ],
    "methodologyUrl": ICMS_EDUCATION_OFFICIAL_PAGE,
    "resultsUrl": ICMS_EDUCATION_RESULTS_URL,
}

PDF_EXPECTED_TOKENS = {
    "data_dictionary": ("Dicionário de dados", "CO_MUN7", "PRE_PERCENTUAL"),
    "methodology_note": ("Nota Técnica", "100", "IMERS", "PRE"),
    "results_presentation": ("Resultados 2024", "IMERS", "PRE", "enchentes"),
}


def _normalize_text(value: Any) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    ascii_value = "".join(
        character for character in normalized if not unicodedata.combining(character)
    )
    return re.sub(r"[^a-z0-9]+", " ", ascii_value.casefold()).strip()


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _decimal_text(value: Decimal) -> str:
    return format(value, "f")


def _parse_decimal(row: dict[str, str], field: str, row_key: str) -> Decimal:
    raw = str(row.get(field, "")).strip()
    if not raw or raw.upper() == "NA":
        raise ValueError(f"{row_key}: campo obrigatório {field} ausente.")
    try:
        return Decimal(raw.replace(" ", "").replace(",", "."))
    except InvalidOperation as error:
        raise ValueError(f"{row_key}: valor inválido em {field}: {raw!r}.") from error


def _parse_count(row: dict[str, str], field: str, row_key: str) -> int:
    value = _parse_decimal(row, field, row_key)
    if value != value.to_integral_value() or value < 0:
        raise ValueError(f"{row_key}: contagem inválida em {field}: {value}.")
    return int(value)


def load_icms_education_registry(path: Path) -> list[dict[str, str]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("stateCode") != ICMS_EDUCATION_STATE_CODE:
        raise RuntimeError(
            f"Cadastro municipal de {payload.get('stateCode')}, esperado "
            f"{ICMS_EDUCATION_STATE_CODE}."
        )
    raw_municipalities = payload.get("municipalities")
    if not isinstance(raw_municipalities, list):
        raise RuntimeError("Cadastro municipal canônico sem a lista municipalities.")

    municipalities: list[dict[str, str]] = []
    for item in raw_municipalities:
        code = item.get("ibgeCode")
        if not isinstance(code, str) or re.fullmatch(r"43\d{5}", code) is None:
            raise RuntimeError(f"Código IBGE textual inválido no cadastro: {code!r}.")
        municipalities.append({"ibgeCode": code, "name": str(item.get("name", ""))})

    if len(municipalities) != EXPECTED_MUNICIPALITIES:
        raise RuntimeError(
            f"Cadastro municipal contém {len(municipalities)} municípios; "
            f"esperado {EXPECTED_MUNICIPALITIES}."
        )
    codes = [item["ibgeCode"] for item in municipalities]
    if len(set(codes)) != len(codes):
        raise RuntimeError("Cadastro municipal contém códigos IBGE duplicados.")
    return sorted(municipalities, key=lambda item: item["ibgeCode"])


def parse_icms_education_csv(
    content: bytes,
    municipalities: list[dict[str, str]],
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise RuntimeError("O CSV do IMERS/PRE não está em UTF-8.") from error

    reader = csv.DictReader(io.StringIO(text, newline=""), delimiter=";")
    fieldnames = set(reader.fieldnames or [])
    missing_columns = sorted(REQUIRED_COLUMNS - fieldnames)
    if missing_columns:
        raise RuntimeError(
            "Layout do CSV do IMERS/PRE incompatível; colunas ausentes: "
            f"{missing_columns}."
        )

    registry_by_code = {item["ibgeCode"]: item for item in municipalities}
    registry_codes = set(registry_by_code)
    seen_keys: set[tuple[str, int]] = set()
    duplicate_keys: list[str] = []
    unknown_codes: set[str] = set()
    name_mismatches: list[str] = []
    parsed_rows: list[dict[str, Any]] = []
    codes_by_year = {year: set() for year in EXPECTED_REFERENCE_YEARS}
    rows_by_year = {year: 0 for year in EXPECTED_REFERENCE_YEARS}
    imers_formula_max = Decimal("0")
    municipal_size_formula_max = Decimal("0")

    for row_number, row in enumerate(reader, start=2):
        code = str(row.get("CO_MUN7", "")).strip()
        if re.fullmatch(r"43\d{5}", code) is None:
            raise RuntimeError(
                f"Linha {row_number}: código IBGE municipal textual inválido: {code!r}."
            )
        if code not in registry_codes:
            unknown_codes.add(code)

        year_text = str(row.get("ANO", "")).strip()
        if not year_text.isdigit():
            raise RuntimeError(f"Linha {row_number}: ano inválido: {year_text!r}.")
        assessment_year = int(year_text)
        if assessment_year not in EXPECTED_REFERENCE_YEARS:
            raise RuntimeError(
                f"Linha {row_number}: ano {assessment_year} fora do contrato "
                f"{EXPECTED_REFERENCE_YEARS}."
            )

        row_key = f"{code}/{assessment_year}"
        key = (code, assessment_year)
        if key in seen_keys:
            duplicate_keys.append(row_key)
        seen_keys.add(key)
        codes_by_year[assessment_year].add(code)
        rows_by_year[assessment_year] += 1

        source_name = str(row.get("NOME_MUN", "")).strip()
        registry_name = registry_by_code.get(code, {}).get("name")
        if registry_name and _normalize_text(source_name) != _normalize_text(registry_name):
            name_mismatches.append(row_key)

        iqa = _parse_decimal(row, "IQA", row_key)
        iqi = _parse_decimal(row, "IQI", row_key)
        iqf = _parse_decimal(row, "IQF", row_key)
        approval_rate = _parse_decimal(row, "IA", row_key)
        imers = _parse_decimal(row, "IMERS", row_key)
        population_share = _parse_decimal(row, "POP/SOMA(POP)", row_key)
        vulnerable_share = _parse_decimal(row, "NAV/SOMA(NAV)", row_key)
        enrollment_share = _parse_decimal(row, "NM/SOMA(NM)", row_key)
        municipal_size_share = _parse_decimal(row, "PORTE_PERCENTUAL", row_key)
        pre_share = _parse_decimal(row, "PRE_PERCENTUAL", row_key)

        for field, value in (
            ("IQA", iqa),
            ("IQI", iqi),
            ("IQF", iqf),
            ("IA", approval_rate),
            ("IMERS", imers),
        ):
            if value < 0 or value > 100:
                raise RuntimeError(f"{row_key}: {field} fora do intervalo [0, 100].")
        if municipal_size_share < 0 or pre_share < 0:
            raise RuntimeError(f"{row_key}: Porte ou PRE negativo.")

        imers_recomputed = (
            Decimal("0.40") * iqa
            + Decimal("0.35") * iqi
            + Decimal("0.15") * iqf
            + Decimal("0.10") * approval_rate
        )
        imers_error = abs(imers - imers_recomputed)
        imers_formula_max = max(imers_formula_max, imers_error)
        if imers_error > IMERS_FORMULA_TOLERANCE:
            raise RuntimeError(
                f"{row_key}: IMERS diverge da fórmula oficial em {imers_error}."
            )

        municipal_size_recomputed = (
            Decimal("85") * population_share
            + Decimal("10") * enrollment_share
            + Decimal("5") * vulnerable_share
        )
        municipal_size_error = abs(municipal_size_share - municipal_size_recomputed)
        municipal_size_formula_max = max(
            municipal_size_formula_max,
            municipal_size_error,
        )
        if municipal_size_error > MUNICIPAL_SIZE_FORMULA_TOLERANCE:
            raise RuntimeError(
                f"{row_key}: Porte diverge da fórmula oficial em {municipal_size_error}."
            )

        distribution = DISTRIBUTION_CONTEXT[assessment_year]
        parsed_rows.append(
            {
                "code": code,
                "assessmentYear": assessment_year,
                "distributionYear": distribution["distributionYear"],
                "ipmEducationCriterionWeightPercent": distribution[
                    "ipmEducationCriterionWeightPercent"
                ],
                "imers": imers,
                "preSharePercent": pre_share,
                "municipalSizeSharePercent": municipal_size_share,
                "components": {
                    "iqa": iqa,
                    "iqi": iqi,
                    "iqf": iqf,
                    "approvalRate": approval_rate,
                },
                "context": {
                    "population": _parse_count(row, "POP", row_key),
                    "initialYearsEnrollments": _parse_count(row, "NM", row_key),
                    "vulnerableStudents": _parse_count(row, "NAV", row_key),
                },
                "imersTimesMunicipalSize": imers * municipal_size_share,
            }
        )

    if duplicate_keys:
        raise RuntimeError(
            "CSV do IMERS/PRE contém chaves município/ano duplicadas: "
            f"{duplicate_keys[:5]}."
        )
    if unknown_codes:
        raise RuntimeError(
            "CSV do IMERS/PRE contém códigos fora do cadastro canônico: "
            f"{sorted(unknown_codes)[:5]}."
        )
    if name_mismatches:
        raise RuntimeError(
            "CSV do IMERS/PRE contém nomes incompatíveis com os códigos IBGE: "
            f"{name_mismatches[:5]}."
        )

    for year in EXPECTED_REFERENCE_YEARS:
        missing = sorted(registry_codes - codes_by_year[year])
        extra = sorted(codes_by_year[year] - registry_codes)
        if missing or extra or rows_by_year[year] != EXPECTED_MUNICIPALITIES:
            raise RuntimeError(
                f"Cobertura municipal inválida em {year}: "
                f"{rows_by_year[year]} linhas, ausentes={missing[:5]}, extras={extra[:5]}."
            )

    pre_totals: dict[str, str] = {}
    pre_total_deviations: dict[str, str] = {}
    pre_formula_max_errors: dict[str, str] = {}
    warning_codes: list[str] = []
    for year in EXPECTED_REFERENCE_YEARS:
        year_rows = [row for row in parsed_rows if row["assessmentYear"] == year]
        pre_total = sum(
            (row["preSharePercent"] for row in year_rows),
            start=Decimal("0"),
        )
        total_product = sum(
            (row["imersTimesMunicipalSize"] for row in year_rows),
            start=Decimal("0"),
        )
        if total_product <= 0:
            raise RuntimeError(f"Denominador do PRE inválido em {year}.")
        pre_formula_max = max(
            abs(
                row["preSharePercent"]
                - row["imersTimesMunicipalSize"] / total_product * Decimal("100")
            )
            for row in year_rows
        )
        total_deviation = pre_total - Decimal("100")
        if abs(total_deviation) > PRE_TOTAL_FAIL_TOLERANCE:
            raise RuntimeError(
                f"Total oficial do PRE em {year} diverge de 100% em {total_deviation} p.p."
            )
        if pre_formula_max > PRE_FORMULA_FAIL_TOLERANCE:
            raise RuntimeError(
                f"PRE municipal em {year} diverge da fórmula oficial em até "
                f"{pre_formula_max} p.p."
            )
        if abs(total_deviation) > PRE_TOTAL_WARNING_TOLERANCE:
            warning_codes.append(f"source_published_pre_total_deviation_{year}")
        pre_totals[str(year)] = _decimal_text(pre_total)
        pre_total_deviations[str(year)] = _decimal_text(total_deviation)
        pre_formula_max_errors[str(year)] = _decimal_text(pre_formula_max)

    records: dict[str, list[dict[str, Any]]] = {
        code: [] for code in sorted(registry_codes)
    }
    for row in parsed_rows:
        records[row["code"]].append(
            {
                "assessmentYear": row["assessmentYear"],
                "distributionYear": row["distributionYear"],
                "ipmEducationCriterionWeightPercent": float(
                    row["ipmEducationCriterionWeightPercent"]
                ),
                "imers": float(row["imers"]),
                "preSharePercent": float(row["preSharePercent"]),
                "municipalSizeSharePercent": float(row["municipalSizeSharePercent"]),
                "components": {
                    key: float(value) for key, value in row["components"].items()
                },
                "context": row["context"],
            }
        )
    for history in records.values():
        history.sort(key=lambda item: item["assessmentYear"])

    quality = {
        "rows": len(parsed_rows),
        "municipalitiesExpected": EXPECTED_MUNICIPALITIES,
        "municipalitiesFound": len(records),
        "municipalitiesNotFound": 0,
        "duplicateMunicipalityCodes": [],
        "duplicateMunicipalityYearKeys": [],
        "incompatibleMunicipalityKeys": 0,
        "unknownMunicipalityCodes": [],
        "nameMismatches": [],
        "referenceYears": list(EXPECTED_REFERENCE_YEARS),
        "rowsByReferenceYear": {
            str(year): rows_by_year[year] for year in EXPECTED_REFERENCE_YEARS
        },
        "coreNullValues": 0,
        "imersFormulaMaxAbsoluteError": _decimal_text(imers_formula_max),
        "municipalSizeFormulaMaxAbsoluteError": _decimal_text(
            municipal_size_formula_max
        ),
        "preShareTotalsPercent": pre_totals,
        "preShareTotalDeviationsPercentagePoints": pre_total_deviations,
        "preFormulaMaxAbsoluteErrorsPercentagePoints": pre_formula_max_errors,
        "warningCodes": warning_codes,
    }
    return records, quality


def _validate_pdf(content: bytes, label: str) -> None:
    if not content.startswith(b"%PDF-") or b"%%EOF" not in content[-2048:]:
        raise RuntimeError(f"Documento PDF inválido: {label}.")
    try:
        reader = PdfReader(io.BytesIO(content), strict=False)
        extracted_text = "\n".join(
            page.extract_text() or "" for page in reader.pages
        )
    except Exception as error:
        raise RuntimeError(f"Não foi possível ler o documento PDF: {label}.") from error
    if not reader.pages:
        raise RuntimeError(f"Documento PDF sem páginas: {label}.")
    normalized_text = _normalize_text(extracted_text)
    missing_tokens = [
        token
        for token in PDF_EXPECTED_TOKENS.get(label, ())
        if _normalize_text(token) not in normalized_text
    ]
    if missing_tokens:
        raise RuntimeError(
            f"Documento PDF incompatível com o papel {label}; "
            f"marcadores ausentes: {missing_tokens}."
        )


def build_icms_education_manifest(
    artifacts: dict[str, bytes],
    quality: dict[str, Any],
    accessed_at: str,
) -> dict[str, Any]:
    expected_roles = set(ARTIFACT_PATHS)
    if set(artifacts) != expected_roles:
        raise ValueError(
            f"Artefatos incompletos: recebido {sorted(artifacts)}, "
            f"esperado {sorted(expected_roles)}."
        )
    for role in expected_roles - {"raw_data"}:
        _validate_pdf(artifacts[role], role)

    source_urls = {
        "raw_data": ICMS_EDUCATION_APP_URL,
        "data_dictionary": ICMS_EDUCATION_APP_URL,
        "methodology_note": ICMS_EDUCATION_APP_URL,
        "results_presentation": ICMS_EDUCATION_RESULTS_URL,
    }
    return {
        "schemaVersion": ICMS_EDUCATION_BUNDLE_SCHEMA,
        "sourceId": ICMS_EDUCATION_SOURCE_ID,
        "stateCode": ICMS_EDUCATION_STATE_CODE,
        "accessedAt": accessed_at,
        "acquisitionMethod": "official_shiny_session_download",
        "adapterVersion": ICMS_EDUCATION_ADAPTER_VERSION,
        "parserVersion": ICMS_EDUCATION_PARSER_VERSION,
        "layoutVersion": ICMS_EDUCATION_LAYOUT_VERSION,
        "methodologyVersion": ICMS_EDUCATION_METHODOLOGY_VERSION,
        "officialPage": ICMS_EDUCATION_OFFICIAL_PAGE,
        "applicationUrl": ICMS_EDUCATION_APP_URL,
        "referenceYears": list(EXPECTED_REFERENCE_YEARS),
        "yearSemantics": "assessment_year_saers",
        "distributionContext": [
            {
                "assessmentYear": year,
                "distributionYear": DISTRIBUTION_CONTEXT[year]["distributionYear"],
                "ipmEducationCriterionWeightPercent": float(
                    DISTRIBUTION_CONTEXT[year][
                        "ipmEducationCriterionWeightPercent"
                    ]
                ),
            }
            for year in EXPECTED_REFERENCE_YEARS
        ],
        "artifacts": [
            {
                "role": role,
                "path": ARTIFACT_PATHS[role].as_posix(),
                "sourceUrl": source_urls[role],
                "bytes": len(artifacts[role]),
                "sha256": _sha256(artifacts[role]),
            }
            for role in ARTIFACT_PATHS
        ],
        "quality": quality,
    }


def canonical_manifest_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def load_icms_education_source(
    bundle_root: Path,
    registry_path: Path,
) -> dict[str, Any]:
    manifest_path = bundle_root / "manifest.json"
    if not manifest_path.is_file():
        raise RuntimeError(f"Manifesto do ICMS Educação ausente: {manifest_path}.")
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes.decode("utf-8"))
    if manifest.get("schemaVersion") != ICMS_EDUCATION_BUNDLE_SCHEMA:
        raise RuntimeError("Schema do bundle do ICMS Educação incompatível.")
    if manifest.get("sourceId") != ICMS_EDUCATION_SOURCE_ID:
        raise RuntimeError("Identidade da fonte do ICMS Educação incompatível.")
    if manifest.get("stateCode") != ICMS_EDUCATION_STATE_CODE:
        raise RuntimeError("UF do bundle do ICMS Educação incompatível.")

    manifest_artifacts = manifest.get("artifacts")
    if not isinstance(manifest_artifacts, list):
        raise RuntimeError("Manifesto do ICMS Educação sem artefatos.")
    artifacts_by_role = {
        str(artifact.get("role")): artifact for artifact in manifest_artifacts
    }
    if set(artifacts_by_role) != set(ARTIFACT_PATHS):
        raise RuntimeError("Manifesto do ICMS Educação com conjunto de artefatos inválido.")

    artifact_contents: dict[str, bytes] = {}
    resolved_root = bundle_root.resolve()
    for role, expected_relative_path in ARTIFACT_PATHS.items():
        artifact = artifacts_by_role[role]
        relative_path = Path(str(artifact.get("path", "")))
        if relative_path != expected_relative_path or relative_path.is_absolute():
            raise RuntimeError(f"Caminho inválido para o artefato {role}.")
        artifact_path = (bundle_root / relative_path).resolve()
        if resolved_root not in artifact_path.parents:
            raise RuntimeError(f"Artefato {role} escapa da raiz do bundle.")
        if not artifact_path.is_file():
            raise RuntimeError(f"Artefato do ICMS Educação ausente: {artifact_path}.")
        content = artifact_path.read_bytes()
        if len(content) != artifact.get("bytes") or _sha256(content) != artifact.get("sha256"):
            raise RuntimeError(f"Hash ou tamanho divergente no artefato {role}.")
        if role != "raw_data":
            _validate_pdf(content, role)
        artifact_contents[role] = content

    municipalities = load_icms_education_registry(registry_path)
    records, quality = parse_icms_education_csv(
        artifact_contents["raw_data"],
        municipalities,
    )
    if quality != manifest.get("quality"):
        raise RuntimeError(
            "A qualidade recalculada do ICMS Educação diverge do manifesto preservado."
        )
    if manifest.get("referenceYears") != list(EXPECTED_REFERENCE_YEARS):
        raise RuntimeError("Anos de referência do ICMS Educação incompatíveis.")

    return {
        "sourceId": ICMS_EDUCATION_SOURCE_ID,
        "stateCode": ICMS_EDUCATION_STATE_CODE,
        "referenceYear": max(EXPECTED_REFERENCE_YEARS),
        "referenceYears": list(EXPECTED_REFERENCE_YEARS),
        "accessedAt": manifest["accessedAt"],
        "adapterVersion": manifest["adapterVersion"],
        "parserVersion": manifest["parserVersion"],
        "layoutVersion": manifest["layoutVersion"],
        "methodologyVersion": manifest["methodologyVersion"],
        "rawSha256": artifacts_by_role["raw_data"]["sha256"],
        "manifestSha256": _sha256(manifest_bytes),
        "quality": quality,
        "records": records,
    }


def merge_icms_education_source(
    snapshot: dict[str, Any],
    source_snapshot: dict[str, Any],
    municipalities: list[dict[str, str]],
) -> dict[str, Any]:
    state_code = snapshot.get("stateCode", ICMS_EDUCATION_STATE_CODE)
    if state_code != ICMS_EDUCATION_STATE_CODE:
        raise RuntimeError(
            f"Fonte do ICMS Educação do RS não pode ser aplicada a {state_code}."
        )
    expected_codes = {item["ibgeCode"] for item in municipalities}
    source_codes = set(source_snapshot.get("records", {}))
    if source_codes != expected_codes:
        raise RuntimeError(
            "Cobertura do ICMS Educação diverge do universo municipal da geração: "
            f"ausentes={sorted(expected_codes - source_codes)[:5]}, "
            f"extras={sorted(source_codes - expected_codes)[:5]}."
        )
    sources = dict(snapshot.get("sources", {}))
    sources[ICMS_EDUCATION_SOURCE_ID] = source_snapshot
    return {**snapshot, "sources": sources}


def build_icms_education_contract(
    snapshot: dict[str, Any],
    municipality_code: str,
) -> dict[str, Any] | None:
    source = snapshot.get("sources", {}).get(ICMS_EDUCATION_SOURCE_ID)
    if not source:
        return None
    history = source.get("records", {}).get(municipality_code)
    if not history:
        raise RuntimeError(
            f"{municipality_code}: registro do ICMS Educação ausente na fonte integrada."
        )
    history_copy = deepcopy(history)
    latest = history_copy[-1]
    return {
        "status": "available",
        "sourceId": ICMS_EDUCATION_SOURCE_ID,
        "methodologyVersion": ICMS_EDUCATION_METHODOLOGY_VERSION,
        "latestAssessmentYear": latest["assessmentYear"],
        "latestDistributionYear": latest["distributionYear"],
        "latest": deepcopy(latest),
        "history": history_copy,
        "qualityReasonCodes": list(source.get("quality", {}).get("warningCodes", [])),
    }


def validate_icms_education_contract(
    block: dict[str, Any],
    municipality_code: str,
) -> None:
    if block.get("status") != "available":
        raise AssertionError(f"{municipality_code}: status do ICMS Educação inválido.")
    if block.get("sourceId") != ICMS_EDUCATION_SOURCE_ID:
        raise AssertionError(f"{municipality_code}: fonte do ICMS Educação inválida.")
    history = block.get("history")
    if not isinstance(history, list) or len(history) != len(EXPECTED_REFERENCE_YEARS):
        raise AssertionError(f"{municipality_code}: histórico do ICMS Educação inválido.")
    if [item.get("assessmentYear") for item in history] != list(EXPECTED_REFERENCE_YEARS):
        raise AssertionError(f"{municipality_code}: anos do ICMS Educação inválidos.")
    if block.get("latest") != history[-1]:
        raise AssertionError(f"{municipality_code}: último registro do ICMS Educação divergente.")
    for item in history:
        context = DISTRIBUTION_CONTEXT[item["assessmentYear"]]
        if item.get("distributionYear") != context["distributionYear"]:
            raise AssertionError(
                f"{municipality_code}: ano de distribuição do ICMS Educação inválido."
            )
        if Decimal(str(item.get("ipmEducationCriterionWeightPercent"))) != context[
            "ipmEducationCriterionWeightPercent"
        ]:
            raise AssertionError(
                f"{municipality_code}: peso do critério Educação no IPM inválido."
            )
        components = item.get("components", {})
        recomputed = (
            Decimal("0.40") * Decimal(str(components.get("iqa")))
            + Decimal("0.35") * Decimal(str(components.get("iqi")))
            + Decimal("0.15") * Decimal(str(components.get("iqf")))
            + Decimal("0.10") * Decimal(str(components.get("approvalRate")))
        )
        if abs(Decimal(str(item.get("imers"))) - recomputed) > IMERS_FORMULA_TOLERANCE:
            raise AssertionError(f"{municipality_code}: fórmula do IMERS inválida.")
        if Decimal(str(item.get("preSharePercent"))) < 0:
            raise AssertionError(f"{municipality_code}: PRE negativo.")
