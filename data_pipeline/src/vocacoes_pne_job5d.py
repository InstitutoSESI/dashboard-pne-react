"""Aquisição dirigida e materialização dos componentes exatos de H2 — Job 5D.

O módulo audita fontes oficiais locais e documentação oficial adquirida, sem
retrocálculo por arredondamento, imputação ou uso de matrícula genérica. Quando
os componentes exatos não existem nas fontes abertas autorizadas, produz um
pacote negativo completo e falha fechado para qualquer avaliação de H2.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import time
from typing import Any, Mapping, Sequence
import zipfile

import pandas as pd

from src.vocacoes_pne_job2 import (
    assert_outside_public_data,
    directory_content_digest,
    sha256_file,
    staging_directory_for,
    validate_unique_key,
    write_csv_gzip,
    write_json,
)


SCHEMA_VERSION = "vocacoes-pne-v7-job5d-v1"
JOB_ID = "v7-job5d"
FINAL_STATE = "JOB_5D_EXACT_DENOMINATORS_NOT_OBTAINABLE_FROM_AUTHORIZED_SOURCES"
REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_PIPELINE_DIR = REPO_ROOT / "data_pipeline"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / ".tmp" / "vocacoes-pne" / JOB_ID
CONTRACT_PATH = DATA_PIPELINE_DIR / "contracts" / "vocacoes-pne-v7-job5d.json"
CORE_PATH = Path(__file__).resolve()
LAUNCHER_PATH = DATA_PIPELINE_DIR / "scripts" / "run_vocacoes_pne_v7_job5d.py"
TEST_PATH = DATA_PIPELINE_DIR / "tests" / "test_vocacoes_pne_job5d.py"
NOVA_SANTA_RITA_ID = "4313375"
IBGE_PATTERN = re.compile(r"^[0-9]{7}$")

SESI_DB_ROOT = Path(r"C:\Users\rnbirck\PROJETOS\SESI\DB")
RATE_RAW_ROOT = SESI_DB_ROOT / "data" / "rendimento"
CENSO_LOCAL_ROOT = SESI_DB_ROOT / "data" / "censo_escolar"
RATE_ACQUISITION_ROOT = Path(
    r"C:\Users\rnbirck\PROJETOS\SESI\PNE\foresight\vocacoes-regiao\aquisicao"
)
RATE_ACQUISITION_MANIFEST = RATE_ACQUISITION_ROOT / "MANIFESTO_AQUISICAO_FLUXO_INEP.json"
RATE_LONG_PATH = RATE_ACQUISITION_ROOT / "bruto" / "fluxo_inep" / "fluxo_municipios_rs_long.csv"
CENSO_2025_ZIP = Path(
    r"C:\Users\rnbirck\PROJETOS\SESI\PNE\data_pipeline\data"
    r"\pne_priority_matrix_sources\inep_censo_escolar\2025_v2\raw"
    r"\microdados_censo_escolar_2025.zip"
)
METHODOLOGY_ROOT = DATA_PIPELINE_DIR / "data" / "vocacoes_pne_v7_job5d" / "sources"

OUTPUT_FILES = (
    "AUDITORIA_FONTES_DENOMINADORES_H2_V7.md",
    "DICIONARIO_COMPONENTES_TAXAS_H2_V7.json",
    "COBERTURA_DENOMINADORES_H2_V7.csv.gz",
    "PAINEL_COMPONENTES_EXATOS_H2_V7.csv.gz",
    "QA_RECOMPUTACAO_TAXAS_H2_V7.csv.gz",
    "NOVA_SANTA_RITA_COMPONENTES_H2_V7.json",
    "DRAFT_PRE_REGISTRO_ESTABILIDADE_H2_V7.yaml",
    "LIMITACOES_AQUISICAO_H2_V7.json",
    "PACOTE_REVISAO_EXTERNA_JOB5D_V7.json",
    "MANIFEST_JOB5D_V7.json",
)

COVERAGE_STATES = frozenset(
    {
        "EXACT_COMPONENTS_AVAILABLE",
        "OFFICIAL_RATE_ONLY",
        "PARTIAL_COMPONENT_COVERAGE",
        "DEFINITION_INCOMPATIBLE",
        "SOURCE_UNAVAILABLE",
        "SUPPRESSED",
        "NOT_APPLICABLE",
    }
)

STAGES = (
    "fundamental",
    "fundamental_anos_iniciais",
    "fundamental_anos_finais",
    "medio",
)
PERFORMANCE_INDICATORS = (
    "approval_rate_percent",
    "failure_rate_percent",
    "dropout_rate_percent",
)
DISTORTION_INDICATOR = "age_grade_distortion_rate_percent"
INDICATOR_MAP = {
    "taxa_aprovacao": "approval_rate_percent",
    "taxa_reprovacao": "failure_rate_percent",
    "taxa_abandono": "dropout_rate_percent",
    "taxa_distorcao": DISTORTION_INDICATOR,
}

CHECKPOINT_HASHES = {
    r"C:\Users\rnbirck\.codex\attachments\1ad6edd5-dde3-4189-9ac6-8973867869d4\pasted-text.txt": (
        "eb7970c9789251117c19d63496cb11bea8dcf79e181d6ea68ff274e344e4b74b"
    ),
    "docs/DECISAO_ESCOPO_REDE_TOTAL_JOB_4B_V7.md": (
        "ab8b6d8288fd4a788b0041d915fa4b35a057cb07005dbbb037db42996943c536"
    ),
    "docs/PRE_REGISTRO_JOB_5A_REDESENHO_DIRIGIDO_V7.yaml": (
        "eaec73eeeb562db362ad3ab3d2e29c7e21cd6f28542fb5b046add944c2323549"
    ),
    ".tmp/vocacoes-pne/v7-job5b/h2_stability_qa.json": (
        "7a016b21f5e8f94b13a18da26b9731f79405e872e02990c7bd78db6ebeec011b"
    ),
    ".tmp/vocacoes-pne/v7-job5b/h2_corrected_internal_synthesis.json": (
        "5fbf2a67879f224fbe626aec56d8e9298c5537169109c7de8b3acc8d9b9b8cf6"
    ),
    ".tmp/vocacoes-pne/v7-job5b/limitations_job5b.json": (
        "96b3b28a03a27912fdc62aabe110d2136154c92887b238b1c0ac148e2b436b71"
    ),
    ".tmp/vocacoes-pne/v7-job5b/external_review_package_job5b.json": (
        "03849b4b8316c0ea5001fe780d8f0beb5d74ebfbb340cede3935d6c422b3d1d8"
    ),
    ".tmp/vocacoes-pne/v7-job5b/manifest_job5b.json": (
        "9a486351bd9c57389f5fd58891d52182b68794c7d3a3dc4858c84d7d9b372d4d"
    ),
    "docs/ARQUITETURA_EDITORIAL_INTERNA_POS_JOB5B_V7.md": (
        "9acb364a52bc98b8955c19817cefbae631dc8d4cb90d8519134b23ae2e9a5f80"
    ),
    "docs/MAPA_LACUNAS_PARA_PAGINA_GESTORA_POS_JOB5B_V7.md": (
        "9e221d4bb5c9f05b4e22c3a51269ab878a82b441b6a189d06733549b7779e99b"
    ),
    "docs/PACOTE_REVISAO_EXTERNA_JOB5C_V7.md": (
        "5f6e4cb7e1e63d143a45d42e3fb69353d2a2dd860440a3415a8a9e4d1d4c1408"
    ),
    "data_pipeline/manifests/vocacoes-pne-v7-job5c-release.json": (
        "3833cf3fc811cc29d5a642f58a8ed814aab233be01299e86a343331d59a6984b"
    ),
}

RATE_ACQUISITION_MANIFEST_SHA256 = (
    "bc52c9946bc5edaad5aca21f7ee75a5f9f8ec307cb58a3d9c519815994bec8b0"
)
RATE_LONG_SHA256 = "fa93a6f0a71c9cecb7339c16d4ab0553a9fc798f433e695db86602205d24839b"
CENSO_2025_ZIP_SHA256 = "ad2c389160be5cf6b8e32257677e9b5657f01d10a342355ad9757bfecd2fc90a"

METHODOLOGY_SOURCES = (
    {
        "filename": "caderno_situacao_aluno_2025.pdf",
        "url": (
            "https://download.inep.gov.br/publicacoes/institucionais/"
            "estatisticas_e_indicadores/cadernos_de_conceitos_e_orientacoes_da_"
            "segunda_etapa_do_censo_escolar_2025_situacao_do_aluno_ed.pdf"
        ),
        "organization": "Instituto Nacional de Estudos e Pesquisas Educacionais Anísio Teixeira (Inep/MEC)",
        "title": "Caderno de conceitos e orientações da 2ª etapa do Censo Escolar 2025: Situação do Aluno",
        "version": "edição referente ao Censo Escolar 2025, publicada em 2026",
        "referenceDate": "Censo Escolar 2025",
        "byteSize": 741976,
        "sha256": "3446013688abcf4c4fa5ea564d7efa21f481f0e75880e5f05bedc50463b79cb6",
        "methodologyRole": "definições atuais de aprovação, reprovação, transferência, deixou de frequentar, falecimento e universos por etapa",
    },
    {
        "filename": "taxas_de_rendimento_escolar_2020.pdf",
        "url": (
            "https://download.inep.gov.br/educacao_basica/educacenso/"
            "situacao_aluno/documentos/2020/taxas_de_rendimento_escolar.pdf"
        ),
        "organization": "Instituto Nacional de Estudos e Pesquisas Educacionais Anísio Teixeira (Inep/MEC)",
        "title": "Taxas de Rendimento Escolar",
        "version": "material metodológico 2020 referente à Situação do Aluno 2019",
        "referenceDate": "Censo Escolar 2019 / publicação 2020",
        "byteSize": 675346,
        "sha256": "e5cdf3ac2f9a51c9c18a9134da44f454d7b2303abe28908f3e575dc730815e2c",
        "methodologyRole": "fórmulas APR, REP e ABA e taxa de não resposta",
    },
    {
        "filename": "analise_indicadores_educacionais.pdf",
        "url": (
            "https://download.inep.gov.br/download/estudos_pesquisas/"
            "indic_educacionais/analise_indicadores_educacionais.pdf"
        ),
        "organization": "Instituto Nacional de Estudos e Pesquisas Educacionais Anísio Teixeira (Inep/MEC)",
        "title": "Análise dos indicadores educacionais calculados durante o convênio INEP/CEDEPLAR",
        "version": "publicação institucional sem versão explícita no arquivo",
        "referenceDate": "séries históricas até 2003",
        "byteSize": 292148,
        "sha256": "e21da9fa8fba5f51c6a20fc6ce08e44cc368426d9eb48a566e00e82112e41b9b",
        "methodologyRole": "forma geral da razão de distorção idade-série",
    },
    {
        "filename": "dicionario_indicadores_educacionais_formulas.pdf",
        "url": (
            "https://download.inep.gov.br/publicacoes/institucionais/"
            "estatisticas_e_indicadores/dicionario_de_indicadores_educacionais_"
            "formulas_de_calculo.pdf"
        ),
        "organization": "Instituto Nacional de Estudos e Pesquisas Educacionais Anísio Teixeira (Inep/MEC)",
        "title": "Dicionário de indicadores educacionais: fórmulas de cálculo",
        "version": "publicação institucional do Inep",
        "referenceDate": "metodologia de indicadores educacionais",
        "byteSize": 422985,
        "sha256": "d7699aaf93a86caace384968472e832126947795df22efb5bc39651fbef391d2",
        "methodologyRole": "fórmula, grão e critério etário da distorção idade-série",
    },
)

CENSO_SIMPLIFIED_2018_2024 = {
    2018: ("microdados_ed_basica_2018.csv", 224419401, "765c94d4d828c53091ebdfc72e442a81ad61998abe785acc66e69f3d4f263892"),
    2019: ("microdados_ed_basica_2019.csv", 217066579, "d3f315b5a5f3145b139ae8bcee920bb0f3a804e8deb63263a2de9633e9c1d9fe"),
    2020: ("microdados_ed_basica_2020.CSV", 213247882, "cba48906eb0d2c1f3ea320505bcfdf875e59730d43212f821c19c649e53aa48d"),
    2021: ("microdados_ed_basica_2021.csv", 210559443, "96c1d0f4637fda8dcb6d8cbf2ad284e15ab7089dafa773e29404f58b4f215cb2"),
    2022: ("microdados_ed_basica_2022.csv", 190008267, "dfa3b5e8ce977f4e650c84c19b741e063f4c94fe63841c6cbce60831deb52602"),
    2023: ("microdados_ed_basica_2023.csv", 210035219, "b2dd87c32cf25af4af89202adb908d17b0d3fea99e2ea046229aa86a9d69679a"),
    2024: ("microdados_ed_basica_2024.csv", 217925280, "3fb4d93c714b7d9303e34430f0287ca102bf984a4769d5abaca21eb4d1453bc9"),
}

COVERAGE_COLUMNS = (
    "municipality_ibge_code",
    "municipality_name",
    "year",
    "stage",
    "indicator",
    "network_scope",
    "numerator",
    "denominator",
    "recomputed_rate_percent",
    "official_rate_percent",
    "difference_pp",
    "source_id",
    "source_version",
    "source_grain",
    "definition_status",
    "component_dependencies_present",
    "component_dependencies_missing",
    "availability_state",
    "zero_denominator",
    "qa_status",
    "coverage_state",
    "raw_availability_marker",
    "component_source_status",
    "aggregate_rate_eligible",
)

RECOMPUTATION_QA_COLUMNS = (
    "municipality_ibge_code",
    "municipality_name",
    "year",
    "stage",
    "indicator",
    "network_scope",
    "numerator",
    "denominator",
    "recomputed_rate_percent",
    "official_rate_percent",
    "difference_pp",
    "tolerance_pp",
    "qa_status",
)


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_checkpoint(path_text: str) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else REPO_ROOT / path


def _verify(path: Path, expected_sha256: str, *, expected_size: int | None = None) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Entrada congelada ausente: {path}")
    size = path.stat().st_size
    if expected_size is not None and size != expected_size:
        raise ValueError(f"Tamanho divergente em {path}: {size} != {expected_size}.")
    digest = sha256_file(path)
    if digest != expected_sha256:
        raise ValueError(f"SHA-256 divergente em {path}: {digest} != {expected_sha256}.")
    return {"path": str(path), "byteSize": size, "sha256": digest}


def _load_registry() -> tuple[list[str], dict[str, str], list[str]]:
    payload = _load_json(REPO_ROOT / "config" / "municipalities" / "rs.json")
    municipalities = payload["municipalities"]
    codes = [item["ibgeCode"] for item in municipalities]
    if payload["municipalityCount"] != 497 or len(codes) != 497 or len(set(codes)) != 497:
        raise ValueError("Registro municipal canônico de RS não fecha em 497 municípios.")
    if not all(isinstance(code, str) and IBGE_PATTERN.fullmatch(code) for code in codes):
        raise ValueError("Registro municipal contém identidade IBGE não textual/fora de sete dígitos.")
    names = {item["ibgeCode"]: item["name"] for item in municipalities}
    region_payload = _load_json(REPO_ROOT / "config" / "regions" / "rs.json")
    region = next(item for item in region_payload["regions"] if item["slug"] == "vale-do-sinos")
    region_codes = list(region["municipalityIbgeCodes"])
    if len(region_codes) != 10 or len(set(region_codes)) != 10:
        raise ValueError("Vale do Sinos canônico não fecha em dez municípios.")
    if NOVA_SANTA_RITA_ID not in region_codes or names[NOVA_SANTA_RITA_ID] != "Nova Santa Rita":
        raise ValueError("Nova Santa Rita 4313375 não foi preservada no universo canônico.")
    return codes, names, region_codes


def _inspect_simplified_microdata_headers() -> list[dict[str, Any]]:
    forbidden = ("APROV", "REPROV", "ABAND", "SITUACAO_ALUNO", "SITUAÇÃO_ALUNO")
    inspected: list[dict[str, Any]] = []
    for year, (filename, size, frozen_sha256) in CENSO_SIMPLIFIED_2018_2024.items():
        path = CENSO_LOCAL_ROOT / filename
        if not path.is_file() or path.stat().st_size != size:
            raise ValueError(f"Microdado simplificado ausente ou divergente: {path}")
        with path.open("r", encoding="latin-1", errors="replace") as stream:
            header = stream.readline().strip().split(";")
        outcome_columns = [column for column in header if any(token in column.upper() for token in forbidden)]
        if outcome_columns:
            raise ValueError(f"Auditoria de cabeçalho mudou em {year}: {outcome_columns}")
        inspected.append(
            {
                "year": year,
                "path": str(path),
                "byteSize": size,
                "sha256FrozenAtDiscovery": frozen_sha256,
                "columnCount": len(header),
                "outcomeComponentColumns": [],
                "finding": "school-level simplified census file; no approval, failure or dropout outcome components and no age-by-series matrix",
            }
        )

    verified_2025 = _verify(CENSO_2025_ZIP, CENSO_2025_ZIP_SHA256, expected_size=537217189)
    member = "microdados_censo_escolar_2025_v2/dados/Tabela_Matricula_2025_V2.csv"
    with zipfile.ZipFile(CENSO_2025_ZIP) as archive:
        with archive.open(member) as stream:
            header_2025 = stream.readline().decode("utf-8-sig", errors="replace").strip().split(";")
    outcome_columns_2025 = [
        column for column in header_2025 if any(token in column.upper() for token in forbidden)
    ]
    if outcome_columns_2025:
        raise ValueError(f"Auditoria do microdado 2025 mudou: {outcome_columns_2025}")
    inspected.append(
        {
            "year": 2025,
            **verified_2025,
            "archiveMember": member,
            "columnCount": len(header_2025),
            "outcomeComponentColumns": [],
            "finding": "aggregated enrollment table; series counts and age bands are marginal, not a cross age-by-series, and no final student outcome components are published",
        }
    )
    return inspected


def verify_frozen_inputs() -> dict[str, Any]:
    contract = _load_json(CONTRACT_PATH)
    if contract["outputs"] != list(OUTPUT_FILES):
        raise ValueError("Contrato Job 5D diverge da allowlist de outputs.")
    if contract["selectedFinalState"] != FINAL_STATE:
        raise ValueError("Estado final contratado divergiu.")
    if contract["scope"]["networkScope"] != "total_all_dependencies":
        raise ValueError("Escopo canônico de rede total divergiu.")
    if contract["componentPolicy"]["reverseRoundingAllowed"]:
        raise ValueError("Retrocálculo por arredondamento foi indevidamente autorizado.")

    checkpoints = []
    for relative, expected in CHECKPOINT_HASHES.items():
        checkpoints.append(_verify(_resolve_checkpoint(relative), expected))

    rate_manifest_record = _verify(
        RATE_ACQUISITION_MANIFEST, RATE_ACQUISITION_MANIFEST_SHA256, expected_size=12803
    )
    rate_long_record = _verify(RATE_LONG_PATH, RATE_LONG_SHA256, expected_size=3017295)
    rate_manifest = _load_json(RATE_ACQUISITION_MANIFEST)
    if rate_manifest["networkUsed"] or rate_manifest["output"]["rowCount"] != 61597:
        raise ValueError("Manifesto de taxas oficial local divergiu.")
    if rate_manifest["output"]["sha256"] != RATE_LONG_SHA256:
        raise ValueError("Manifesto de aquisição não aponta para o CSV congelado.")
    if len(rate_manifest["sources"]) != 15:
        raise ValueError("Inventário bruto de rendimento/distorção não contém 15 fontes anuais.")
    raw_sources = []
    for source in rate_manifest["sources"]:
        path = Path(source["sourceLocalPath"])
        record = _verify(path, source["sha256"], expected_size=source["byteSize"])
        raw_sources.append(
            {
                **source,
                **record,
                "organization": "Instituto Nacional de Estudos e Pesquisas Educacionais Anísio Teixeira (Inep/MEC)",
                "referenceDate": str(source["year"]),
                "accessDate": "2026-08-28",
                "licenseOrUse": "publicação oficial de acesso público; licença específica não identificada no XLSX local",
                "methodology": "official municipal rate table; no numerator or denominator columns",
            }
        )

    methodology_sources = []
    for source in METHODOLOGY_SOURCES:
        record = _verify(
            METHODOLOGY_ROOT / source["filename"],
            source["sha256"],
            expected_size=source["byteSize"],
        )
        methodology_sources.append(
            {
                **source,
                **record,
                "accessDate": "2026-08-28",
                "licenseOrUse": "publicação oficial de acesso público para consulta e citação; licença específica não declarada no arquivo",
            }
        )

    microdata = _inspect_simplified_microdata_headers()
    return {
        "contract": contract,
        "checkpoints": checkpoints,
        "rateAcquisitionManifest": rate_manifest_record,
        "rateLong": rate_long_record,
        "rawRateSources": raw_sources,
        "methodologySources": methodology_sources,
        "microdataAudit": microdata,
    }


def _source_maps(raw_sources: Sequence[Mapping[str, Any]]) -> dict[tuple[str, int], Mapping[str, Any]]:
    result: dict[tuple[str, int], Mapping[str, Any]] = {}
    for source in raw_sources:
        key = (str(source["indicatorGroup"]), int(source["year"]))
        if key in result:
            raise ValueError(f"Fonte anual duplicada: {key}")
        result[key] = source
    return result


def _load_official_rates() -> pd.DataFrame:
    frame = pd.read_csv(
        RATE_LONG_PATH,
        dtype={"id_municipio": "string", "ano": "int64", "valor": "float64"},
    )
    frame = frame.rename(
        columns={
            "id_municipio": "municipality_ibge_code",
            "ano": "year",
            "etapa": "stage",
            "indicador": "source_indicator",
            "valor": "official_rate_percent",
        }
    )
    frame["indicator"] = frame["source_indicator"].map(INDICATOR_MAP)
    if frame["indicator"].isna().any():
        raise ValueError("Indicador não mapeado no CSV oficial derivado.")
    validate_unique_key(
        frame,
        ["municipality_ibge_code", "year", "stage", "indicator"],
        label="taxas oficiais locais",
    )
    if len(frame) != 61597:
        raise ValueError(f"CSV oficial derivado contém {len(frame)} linhas, esperado 61597.")
    if not frame["municipality_ibge_code"].map(
        lambda value: isinstance(value, str) and bool(IBGE_PATTERN.fullmatch(value))
    ).all():
        raise ValueError("Identidade municipal inválida no CSV de taxas.")
    if frame["official_rate_percent"].lt(0).any() or frame["official_rate_percent"].gt(100).any():
        raise ValueError("Taxa oficial fora de 0–100.")
    return frame


def build_coverage(
    *, raw_sources: Sequence[Mapping[str, Any]]
) -> tuple[pd.DataFrame, list[str], dict[str, str], list[str]]:
    codes, names, region_codes = _load_registry()
    rates = _load_official_rates()
    rows: list[dict[str, Any]] = []
    for code in codes:
        for year in range(2018, 2026):
            for stage in STAGES:
                for indicator in PERFORMANCE_INDICATORS:
                    rows.append(
                        {
                            "municipality_ibge_code": code,
                            "municipality_name": names[code],
                            "year": year,
                            "stage": stage,
                            "indicator": indicator,
                            "source_group": "taxa_rendimento",
                        }
                    )
        for year in range(2019, 2026):
            for stage in STAGES:
                rows.append(
                    {
                        "municipality_ibge_code": code,
                        "municipality_name": names[code],
                        "year": year,
                        "stage": stage,
                        "indicator": DISTORTION_INDICATOR,
                        "source_group": "taxa_distorcao",
                    }
                )
    expected = pd.DataFrame(rows)
    coverage = expected.merge(
        rates[
            [
                "municipality_ibge_code",
                "year",
                "stage",
                "indicator",
                "official_rate_percent",
            ]
        ],
        on=["municipality_ibge_code", "year", "stage", "indicator"],
        how="left",
        validate="one_to_one",
    )
    sources = _source_maps(raw_sources)

    def source_value(row: pd.Series, field: str) -> Any:
        source = sources[(row["source_group"], int(row["year"]))]
        return source[field]

    available = coverage["official_rate_percent"].notna()
    coverage["network_scope"] = "total_all_dependencies"
    for column in ("numerator", "denominator", "recomputed_rate_percent", "difference_pp"):
        coverage[column] = pd.NA
    coverage["source_id"] = coverage.apply(
        lambda row: (
            f"inep_taxas_rendimento_escolar_municipios_{row['year']}"
            if row["source_group"] == "taxa_rendimento"
            else f"inep_taxa_distorcao_idade_serie_municipios_{row['year']}"
        ),
        axis=1,
    )
    coverage["source_version"] = coverage.apply(
        lambda row: f"{source_value(row, 'fileName')}@sha256:{source_value(row, 'sha256')}", axis=1
    )
    coverage["source_grain"] = (
        "municipality_ibge_code×year×stage×indicator×network_scope=total_all_dependencies"
    )
    coverage["definition_status"] = "OFFICIAL_DEFINITION_CONFIRMED_COMPONENTS_NOT_PUBLISHED"
    coverage["component_dependencies_present"] = "[]"
    coverage["component_dependencies_missing"] = json.dumps(
        ["federal", "state", "municipal", "private"], ensure_ascii=False, separators=(",", ":")
    )
    coverage["availability_state"] = "unavailable"
    coverage.loc[available, "availability_state"] = "observed"
    coverage.loc[available & coverage["official_rate_percent"].eq(0), "availability_state"] = (
        "observed_zero"
    )
    coverage["zero_denominator"] = pd.NA
    coverage["qa_status"] = "NOT_RECOMPUTABLE_OFFICIAL_RATE_UNAVAILABLE"
    coverage.loc[available, "qa_status"] = "NOT_RECOMPUTABLE_MISSING_EXACT_COMPONENTS"
    coverage["coverage_state"] = "SOURCE_UNAVAILABLE"
    coverage.loc[available, "coverage_state"] = "OFFICIAL_RATE_ONLY"
    coverage["raw_availability_marker"] = "--_or_absent_in_rate_only_derivative"
    coverage.loc[available, "raw_availability_marker"] = "numeric_official_rate"
    coverage["component_source_status"] = "NO_AUTHORIZED_OPEN_SOURCE_WITH_EXACT_COMPONENTS"
    coverage["aggregate_rate_eligible"] = False
    coverage = coverage.drop(columns=["source_group"])[list(COVERAGE_COLUMNS)]
    coverage = coverage.sort_values(
        ["municipality_ibge_code", "year", "stage", "indicator"], kind="mergesort"
    ).reset_index(drop=True)
    validate_unique_key(
        coverage,
        ["municipality_ibge_code", "year", "stage", "indicator", "network_scope"],
        label="cobertura Job 5D",
    )
    if len(coverage) != 61628:
        raise ValueError(f"Cobertura esperada 61628, obtida {len(coverage)}.")
    if int(coverage["official_rate_percent"].notna().sum()) != 61597:
        raise ValueError("Cobertura de taxas oficiais não preservou as 61597 observações.")
    return coverage, codes, names, region_codes


def build_component_dictionary(inputs: Mapping[str, Any]) -> dict[str, Any]:
    common_performance = {
        "denominatorOfficialSymbol": "APR + REP + ABA",
        "denominatorDefinition": "matrículas com situação final válida como aprovado, reprovado ou deixou de frequentar, no mesmo grão da taxa",
        "unit": "enrollments",
        "population": "ensino fundamental e médio; situação final informada pela escola de conclusão/admissão após",
        "exclusions": [
            "transferência na escola de origem; a situação final passa a ser computada na escola que admite o aluno",
            "falecimento",
            "SIR — sem informação de rendimento, abandono ou falecimento",
            "educação infantil, para a qual aprovação/reprovação não se aplica",
            "turmas exclusivas de AEE, atividade complementar ou itinerário formativo sem Formação Geral Básica, que não entram no módulo de rendimento",
        ],
        "nonresponse": "SIR tem indicador próprio TNR = SIR/(APR+REP+ABA+SIR)×100 e não integra o denominador das três taxas de rendimento",
        "transferTreatment": "aluno transferido é contado pela situação final da escola que o admitiu após a data de referência",
        "deathTreatment": "falecimento não integra APR+REP+ABA",
        "comparability": "fórmula comum confirmada; mudanças de coleta, calendário e cobertura anual devem permanecer como ressalva operacional",
        "componentAvailability": "not_published_in_authorized_open_municipal_sources",
    }
    definitions = {
        "approval_rate_percent": {
            "officialName": "Taxa de aprovação",
            "formula": "APR / (APR + REP + ABA) * 100",
            "numeratorOfficialSymbol": "APR",
            "numeratorDefinition": "número de matrículas com aprovação",
            **common_performance,
        },
        "failure_rate_percent": {
            "officialName": "Taxa de reprovação",
            "formula": "REP / (APR + REP + ABA) * 100",
            "numeratorOfficialSymbol": "REP",
            "numeratorDefinition": "número de matrículas com reprovação",
            **common_performance,
        },
        "dropout_rate_percent": {
            "officialName": "Taxa de abandono",
            "formula": "ABA / (APR + REP + ABA) * 100",
            "numeratorOfficialSymbol": "ABA",
            "numeratorDefinition": "número de matrículas informadas como deixou de frequentar",
            **common_performance,
        },
        DISTORTION_INDICATOR: {
            "officialName": "Taxa de distorção idade-série",
            "formula": "M_ks_i_sup / M_ks * 100",
            "numeratorOfficialSymbol": "M_ks_i_sup",
            "numeratorDefinition": "matrículas que, no ano de referência, completam a idade recomendada para a série mais dois anos ou mais",
            "denominatorOfficialSymbol": "M_ks",
            "denominatorDefinition": "total de matrículas no mesmo nível de ensino e na mesma série ou grupo de séries",
            "unit": "enrollments",
            "population": "matrículas do ensino fundamental ou médio no mesmo recorte territorial, de rede e grupo de séries",
            "ageRule": "idade ideal de 6 anos para ingresso no 1º ano do ensino fundamental; o critério usa idade calculada no ano e mantém como adequada a criança que completa a idade seguinte ao longo do ano",
            "exclusions": [
                "a publicação municipal aberta não enumera integralmente exclusões adicionais do processamento do indicador",
                "matrícula genérica por etapa não substitui M_ks porque não preserva o cruzamento idade×série usado no numerador",
            ],
            "transferTreatment": "not_applicable_to_initial_enrollment_indicator",
            "deathTreatment": "not_applicable_to_initial_enrollment_indicator",
            "nonresponse": "not_documented_as_a_component_in_the_public_rate_workbook",
            "comparability": "a estrutura seriada e o critério etário devem ser preservados; não agregar taxas de séries por média",
            "componentAvailability": "not_published_in_authorized_open_municipal_sources",
        },
    }
    return {
        "schemaVersion": "vocacoes-pne-v7-job5d-component-dictionary-v1",
        "jobId": JOB_ID,
        "networkScope": "total_all_dependencies",
        "grain": [
            "municipality_ibge_code",
            "year",
            "stage",
            "indicator",
            "network_scope",
        ],
        "definitions": definitions,
        "aggregationRule": "somar numeradores e denominadores oficiais compatíveis e só então calcular a razão; média simples de taxas é proibida",
        "zeroDenominatorRule": "denominator == 0 -> recomputed_rate_percent = null",
        "sourceMetadata": {
            "rawRateSources": inputs["rawRateSources"],
            "methodologySources": inputs["methodologySources"],
            "microdataAudit": inputs["microdataAudit"],
        },
        "discoveryConclusion": FINAL_STATE,
        "reverseRoundingUsed": False,
        "imputationUsed": False,
    }


def _coverage_counts(coverage: pd.DataFrame, region_codes: Sequence[str]) -> dict[str, Any]:
    def counts(frame: pd.DataFrame) -> dict[str, int]:
        values = frame["coverage_state"].value_counts().to_dict()
        return {state: int(values.get(state, 0)) for state in sorted(COVERAGE_STATES)}

    return {
        "rs": {"rowCount": len(coverage), "municipalityCount": 497, "states": counts(coverage)},
        "valeDoSinos": {
            "rowCount": int(coverage["municipality_ibge_code"].isin(region_codes).sum()),
            "municipalityCount": 10,
            "states": counts(coverage[coverage["municipality_ibge_code"].isin(region_codes)]),
        },
        "novaSantaRita": {
            "rowCount": int(coverage["municipality_ibge_code"].eq(NOVA_SANTA_RITA_ID).sum()),
            "states": counts(coverage[coverage["municipality_ibge_code"].eq(NOVA_SANTA_RITA_ID)]),
        },
    }


def _audit_markdown(
    *, inputs: Mapping[str, Any], coverage: pd.DataFrame, region_codes: Sequence[str]
) -> str:
    counts = _coverage_counts(coverage, region_codes)
    raw_rows = []
    for source in inputs["rawRateSources"]:
        raw_rows.append(
            f"| {source['year']} | `{source['fileName']}` | {source['indicatorGroup']} | "
            f"{source['byteSize']} | `{source['sha256']}` | somente taxas |"
        )
    return "\n".join(
        [
            "# Auditoria de fontes e denominadores H2 — Job 5D V7",
            "",
            f"**Estado final:** `{FINAL_STATE}`",
            "",
            "## Conclusão executiva",
            "",
            "A aquisição dirigida não encontrou numeradores e denominadores oficiais exatos no grão município × ano × etapa × indicador × rede total. Os XLSX municipais do Inep preservados localmente publicam apenas percentuais. Os ETLs de `public.rendimento_escolar` e `public.distorcao_idade_serie` leem exatamente essas colunas de taxa; portanto, não descartaram componentes durante a carga.",
            "",
            "Os microdados abertos simplificados do Censo Escolar de 2018–2025 também não resolvem a lacuna: não publicam os resultados finais individuais da Situação do Aluno e não fornecem o cruzamento idade × série necessário para recompor a distorção. A coleta detalhada existe no Educacenso, mas não integra as fontes abertas autorizadas deste Job.",
            "",
            "Nenhum denominador foi retrocalculado a partir de taxa arredondada; matrícula genérica, população, média de taxas, imputação e estimativa foram rejeitadas.",
            "",
            "## Linhagem auditada",
            "",
            "- `public.rendimento_escolar` ← `SESI/DB/rendimento_escolar.py` ← `tx_rend_municipios_<ANO>.xlsx`; colunas finais: aprovação, reprovação e abandono em percentual.",
            "- `public.distorcao_idade_serie` ← `SESI/DB/distorcao_idade_serie.py` ← `TDI_MUNICIPIOS_<ANO>.xlsx`; coluna final: taxa de distorção em percentual.",
            "- A consulta `data_pipeline/queries/distorcao_idade_serie.sql` usa matrículas gerais apenas para impedir cálculo quando não há matrícula; ela não contém nem produz o denominador oficial da taxa de distorção.",
            "",
            "## Cobertura materializada",
            "",
            f"- RS: {counts['rs']['rowCount']} combinações esperadas; {counts['rs']['states']['OFFICIAL_RATE_ONLY']} com taxa oficial e zero com componente exato.",
            f"- Vale do Sinos: {counts['valeDoSinos']['rowCount']} combinações; {counts['valeDoSinos']['states']['OFFICIAL_RATE_ONLY']} com taxa oficial e zero com componente exato.",
            f"- Nova Santa Rita (`4313375`): {counts['novaSantaRita']['rowCount']} combinações; {counts['novaSantaRita']['states']['OFFICIAL_RATE_ONLY']} com taxa oficial e zero com componente exato.",
            "- As combinações sem percentual numérico são marcadas `SOURCE_UNAVAILABLE`; o marcador `--` não foi reinterpretado como supressão sem documentação explícita.",
            "",
            "## Definições oficiais preservadas",
            "",
            "- Aprovação: `APR / (APR + REP + ABA) × 100`.",
            "- Reprovação: `REP / (APR + REP + ABA) × 100`.",
            "- Abandono: `ABA / (APR + REP + ABA) × 100`.",
            "- Distorção idade-série: matrículas acima da idade recomendada na série ou grupo de séries divididas pelo total de matrículas no mesmo recorte, multiplicado por 100.",
            "- Transferidos são atribuídos à escola de admissão para a situação final; falecidos e SIR não integram `APR + REP + ABA`. A TNR é um indicador separado.",
            "",
            "## Fontes brutas oficiais locais",
            "",
            "| ano | arquivo | família | bytes | SHA-256 | achado |",
            "|---:|---|---|---:|---|---|",
            *raw_rows,
            "",
            "## Documentos oficiais adquiridos nesta rodada",
            "",
            *[
                f"- [{source['title']}]({source['url']}) — {source['byteSize']} bytes; SHA-256 `{source['sha256']}`; acesso 2026-08-28; {source['licenseOrUse']}."
                for source in inputs["methodologySources"]
            ],
            "",
            "## Fontes rejeitadas como componentes",
            "",
            "- matrícula inicial total por etapa: universo diferente de `APR + REP + ABA` e sem situação final;",
            "- faixas etárias marginais e contagens por série em tabelas separadas: não preservam o cruzamento idade × série;",
            "- população residente ou estimada: universo incompatível;",
            "- dependências administrativas com taxas prontas: somar ou promediar taxas não recompõe a rede total;",
            "- inversão de percentuais arredondados: há múltiplos pares inteiros compatíveis e o método é expressamente proibido.",
            "",
            "## Limite decisório",
            "",
            "O Job 5D não escolhe padrão de trajetória, não avalia C5, não fixa regra final de pequeno denominador e não aprova H2. O Job 6 permanece não autorizado e o Gate 11 permanece bloqueado. O próximo ato é julgamento externo do GPT-5.6 Pro.",
            "",
        ]
    )


def _stability_draft() -> str:
    return """schema_version: vocacoes-pne-v7-job5d-stability-draft-v1
status: DRAFT_FOR_EXTERNAL_PREREGISTRATION_REVIEW
job_id: v7-job5d
result_blind: true
applied_to_h2_in_this_job: false
official_rules_found:
  rate_nonresponse:
    formula: SIR / (APR + REP + ABA + SIR) * 100
    role: separate_quality_indicator_not_a_small_denominator_rule
  zero_denominator:
    rule: denominator_zero_produces_null
  published_small_denominator_threshold:
    status: NOT_FOUND_IN_AUTHORIZED_SOURCES
candidate_rules_for_external_review:
  - id: denominator_floor
    threshold: TBD_BY_EXTERNAL_PREREGISTRATION
    required_fields: [denominator, indicator, stage, year, municipality_ibge_code]
    affected_coverage: all_rows_with_exact_components_if_obtained
    advantages: [simple, auditable, directly tied to precision]
    risks: [one_floor_may_not_fit_all_indicators, discontinuity_near_threshold]
    edge_cases: [denominator_zero, denominator_exactly_at_threshold, suppressed_component]
  - id: minimum_event_count_by_numerator
    threshold: TBD_BY_EXTERNAL_PREREGISTRATION
    required_fields: [numerator, denominator, indicator]
    affected_coverage: performance_and_distortion_rows_with_exact_components_if_obtained
    advantages: [guards_rare_outcomes, indicator_specific]
    risks: [different_rules_across_family, may_hide_observed_zero]
    edge_cases: [observed_zero_with_positive_denominator, multiple_performance_numerators_share_denominator]
  - id: uncertainty_width
    threshold: TBD_BY_EXTERNAL_PREREGISTRATION
    required_fields: [numerator, denominator, interval_method, confidence_level]
    affected_coverage: rows_with_exact_components_if_obtained
    advantages: [continuous_measure_of_precision]
    risks: [requires_statistical_assumptions, more_complex_for_managerial_use]
    edge_cases: [zero_events, all_events, very_small_denominator]
recommendation:
  state: WAIT_FOR_EXACT_COMPONENT_ACCESS_AND_EXTERNAL_DECISION
  rationale: no_rule_can_be_applied_or_selected_from_rate_only_results
  preserve_observed_zero: true
  forbid_reverse_rounding: true
external_decisions_required:
  - choose_or_reject_a_small_denominator_rule_before_any_h2_result_reassessment
  - define_indicator_specific_or_common_thresholds
  - define_treatment_of_observed_zero_with_positive_denominator
  - define_treatment_of_suppressed_and_unavailable_components
"""


def _artifact_record(root: Path, name: str, frame: pd.DataFrame | None = None) -> dict[str, Any]:
    path = root / name
    return {
        "path": name,
        "byteSize": path.stat().st_size,
        "sha256": sha256_file(path),
        "rowCount": int(len(frame)) if frame is not None else None,
        "columns": list(frame.columns) if frame is not None else None,
    }


def _copy_manifest_last(source: Path, target: Path) -> None:
    if target.exists():
        raise FileExistsError(f"Destino já existe: {target}")
    target.mkdir(parents=True)
    files = sorted(path for path in source.rglob("*") if path.is_file())
    files.sort(
        key=lambda path: (
            path.relative_to(source).as_posix() == "MANIFEST_JOB5D_V7.json",
            path.relative_to(source).as_posix(),
        )
    )
    for source_path in files:
        relative = source_path.relative_to(source)
        target_path = target / relative
        target_path.parent.mkdir(parents=True, exist_ok=True)
        partial = target_path.with_name(f".{target_path.name}.partial")
        shutil.copy2(source_path, partial)
        delays = (0.1, 0.2, 0.4, 0.8, 1.6, None)
        for delay in delays:
            try:
                os.replace(partial, target_path)
                break
            except PermissionError:
                if delay is None:
                    raise
                time.sleep(delay)


def _promote_transactionally(staging: Path, target: Path) -> str:
    if target.exists() and directory_content_digest(staging) == directory_content_digest(target):
        shutil.rmtree(staging)
        return "unchanged"
    target.parent.mkdir(parents=True, exist_ok=True)
    backup = target.parent / f".{target.name}.backup"
    candidate = Path(tempfile.mkdtemp(prefix=f".{target.name}.candidate-", dir=target.parent))
    if backup.exists():
        shutil.rmtree(backup)
    try:
        shutil.copytree(staging, candidate, dirs_exist_ok=True)
        if directory_content_digest(candidate) != directory_content_digest(staging):
            raise RuntimeError("Candidato diverge do staging validado.")
        if target.exists():
            _copy_manifest_last(target, backup)
            shutil.rmtree(target)
        _copy_manifest_last(candidate, target)
        if directory_content_digest(target) != directory_content_digest(candidate):
            raise RuntimeError("Destino promovido diverge do candidato.")
        if backup.exists():
            shutil.rmtree(backup)
        shutil.rmtree(candidate)
        shutil.rmtree(staging)
        return "replaced"
    except Exception:
        if target.exists():
            shutil.rmtree(target)
        if backup.exists():
            _copy_manifest_last(backup, target)
            shutil.rmtree(backup)
        if candidate.exists():
            shutil.rmtree(candidate)
        raise


def _validate_staging(root: Path) -> dict[str, Any]:
    actual = sorted(path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file())
    if actual != sorted(OUTPUT_FILES):
        raise ValueError(f"Conjunto de outputs Job 5D divergente: {actual}")
    manifest = _load_json(root / "MANIFEST_JOB5D_V7.json")
    if manifest["finalState"] != FINAL_STATE:
        raise ValueError("Estado final do manifesto divergiu.")
    for artifact in manifest["artifacts"]:
        path = root / artifact["path"]
        if path.stat().st_size != artifact["byteSize"] or sha256_file(path) != artifact["sha256"]:
            raise ValueError(f"Integridade divergente: {artifact['path']}")

    coverage = pd.read_csv(
        root / "COBERTURA_DENOMINADORES_H2_V7.csv.gz",
        dtype={"municipality_ibge_code": "string"},
    )
    exact = pd.read_csv(
        root / "PAINEL_COMPONENTES_EXATOS_H2_V7.csv.gz",
        dtype={"municipality_ibge_code": "string"},
    )
    recomputation = pd.read_csv(
        root / "QA_RECOMPUTACAO_TAXAS_H2_V7.csv.gz",
        dtype={"municipality_ibge_code": "string"},
    )
    if list(coverage.columns) != list(COVERAGE_COLUMNS):
        raise ValueError("Schema de cobertura divergiu.")
    if list(exact.columns) != list(COVERAGE_COLUMNS) or len(exact) != 0:
        raise ValueError("Painel exato negativo deve ter schema completo e zero linhas.")
    if list(recomputation.columns) != list(RECOMPUTATION_QA_COLUMNS) or len(recomputation) != 0:
        raise ValueError("QA de recomputação deve ter schema completo e zero linhas.")
    validate_unique_key(
        coverage,
        ["municipality_ibge_code", "year", "stage", "indicator", "network_scope"],
        label="cobertura serializada Job 5D",
    )
    if len(coverage) != 61628 or coverage["municipality_ibge_code"].nunique() != 497:
        raise ValueError("Cobertura RS serializada divergente.")
    if set(coverage["coverage_state"]) - COVERAGE_STATES:
        raise ValueError("Estado de cobertura fora do contrato.")
    if coverage["coverage_state"].isin(
        ["EXACT_COMPONENTS_AVAILABLE", "PARTIAL_COMPONENT_COVERAGE"]
    ).any():
        raise ValueError("Cobertura negativa contém componente exato/partial indevido.")
    if coverage["numerator"].notna().any() or coverage["denominator"].notna().any():
        raise ValueError("Componentes foram inventados em uma cobertura negativa.")
    if set(coverage["network_scope"]) != {"total_all_dependencies"}:
        raise ValueError("Rede total não foi preservada.")
    performance = coverage[coverage["indicator"].isin(PERFORMANCE_INDICATORS)]
    distortion = coverage[coverage["indicator"].eq(DISTORTION_INDICATOR)]
    if (
        len(performance) != 47712
        or set(performance["year"]) != set(range(2018, 2026))
        or set(distortion["year"]) != set(range(2019, 2026))
        or set(coverage["stage"]) != set(STAGES)
    ):
        raise ValueError("Períodos ou etapas da cobertura serializada divergiram.")
    _, _, region_codes = _load_registry()
    vale = coverage[coverage["municipality_ibge_code"].isin(region_codes)]
    if len(vale) != 1240 or vale["municipality_ibge_code"].nunique() != 10:
        raise ValueError("Cobertura dos dez municípios do Vale do Sinos divergiu.")
    if coverage["aggregate_rate_eligible"].astype(bool).any():
        raise ValueError("Agregação foi autorizada sem componentes exatos.")
    if coverage["zero_denominator"].notna().any():
        raise ValueError("Denominador zero foi inferido sem denominador disponível.")
    expected_availability = coverage["official_rate_percent"].map(
        lambda value: (
            "unavailable" if pd.isna(value) else "observed_zero" if value == 0 else "observed"
        )
    )
    if not coverage["availability_state"].eq(expected_availability).all():
        raise ValueError("Estados de disponibilidade não correspondem às taxas oficiais.")
    if not coverage["municipality_ibge_code"].map(
        lambda value: isinstance(value, str) and bool(IBGE_PATTERN.fullmatch(value))
    ).all():
        raise ValueError("Identidade IBGE serializada inválida.")
    nova = _load_json(root / "NOVA_SANTA_RITA_COMPONENTES_H2_V7.json")
    if nova["municipalityIbgeCode"] != NOVA_SANTA_RITA_ID or nova["coverageRowCount"] != 124:
        raise ValueError("Recorte de Nova Santa Rita divergiu.")
    draft = (root / "DRAFT_PRE_REGISTRO_ESTABILIDADE_H2_V7.yaml").read_text(encoding="utf-8")
    if "status: DRAFT_FOR_EXTERNAL_PREREGISTRATION_REVIEW" not in draft:
        raise ValueError("Status do draft de estabilidade divergiu.")
    return {
        "schemaValidation": "PASS",
        "outputCount": len(actual),
        "coverageRowCount": len(coverage),
        "officialRateOnlyRowCount": int(coverage["coverage_state"].eq("OFFICIAL_RATE_ONLY").sum()),
        "sourceUnavailableRowCount": int(coverage["coverage_state"].eq("SOURCE_UNAVAILABLE").sum()),
        "exactComponentRowCount": len(exact),
        "recomputationQaRowCount": len(recomputation),
        "finalState": FINAL_STATE,
    }


def materialize(output_root: Path = DEFAULT_OUTPUT_ROOT) -> dict[str, Any]:
    output_root = output_root.resolve()
    assert_outside_public_data(output_root, REPO_ROOT)
    inputs = verify_frozen_inputs()
    coverage, _, _, region_codes = build_coverage(raw_sources=inputs["rawRateSources"])
    exact_panel = pd.DataFrame(columns=COVERAGE_COLUMNS)
    recomputation_qa = pd.DataFrame(columns=RECOMPUTATION_QA_COLUMNS)
    dictionary = build_component_dictionary(inputs)
    counts = _coverage_counts(coverage, region_codes)
    nova_coverage = coverage[coverage["municipality_ibge_code"].eq(NOVA_SANTA_RITA_ID)]
    nova = {
        "schemaVersion": "vocacoes-pne-v7-job5d-nova-santa-rita-components-v1",
        "municipalityIbgeCode": NOVA_SANTA_RITA_ID,
        "municipalityName": "Nova Santa Rita",
        "networkScope": "total_all_dependencies",
        "coverageRowCount": len(nova_coverage),
        "exactComponentRowCount": 0,
        "officialRateOnlyRowCount": int(
            nova_coverage["coverage_state"].eq("OFFICIAL_RATE_ONLY").sum()
        ),
        "sourceUnavailableRowCount": int(
            nova_coverage["coverage_state"].eq("SOURCE_UNAVAILABLE").sum()
        ),
        "componentStatus": "NO_AUTHORIZED_OPEN_SOURCE_WITH_EXACT_COMPONENTS",
        "coverageRows": json.loads(nova_coverage.to_json(orient="records", force_ascii=False)),
        "trajectoryPatternSelected": False,
        "c5Assessed": False,
        "h2Approved": False,
        "finalState": FINAL_STATE,
    }
    limitations = {
        "schemaVersion": "vocacoes-pne-v7-job5d-limitations-v1",
        "jobId": JOB_ID,
        "finalState": FINAL_STATE,
        "blockingItems": [
            {
                "code": "EXACT_COMPONENTS_NOT_PUBLISHED_IN_AUTHORIZED_OPEN_SOURCES",
                "effect": "no exact denominator panel and no rate recomputation QA rows",
            },
            {
                "code": "SITUACAO_DO_ALUNO_DETAIL_NOT_IN_PUBLIC_MICRODATA",
                "effect": "APR, REP and ABA counts cannot be aggregated at the accepted grain",
            },
            {
                "code": "AGE_BY_SERIES_CROSS_NOT_IN_PUBLIC_SIMPLIFIED_MICRODATA",
                "effect": "distortion numerator and denominator cannot be reconstructed exactly",
            },
            {
                "code": "SMALL_DENOMINATOR_RULE_NOT_PREREGISTERED",
                "effect": "stability and C5 remain not evaluable",
            },
        ],
        "rejectedMethods": [
            "reverse rounding of official rates",
            "generic enrollment or population as denominator",
            "mean or sum of dependency rates",
            "imputation or estimation of suppressed/unavailable components",
        ],
        "coverageCounts": counts,
        "databaseUsed": False,
        "networkUsed": True,
        "networkScope": "four official Inep methodology PDFs only",
        "fullBuildUsed": False,
        "publicDataChanged": False,
        "job5bOrJob5cArtifactsChanged": False,
        "job6Authorized": False,
        "gate11Status": "BLOCKED",
    }
    external_package = {
        "schemaVersion": "vocacoes-pne-v7-job5d-external-review-package-v1",
        "jobId": JOB_ID,
        "finalState": FINAL_STATE,
        "scope": inputs["contract"]["scope"],
        "finding": "official municipal open files expose rates only; exact components are not obtainable without a different authorized access route",
        "coverageCounts": counts,
        "definitions": dictionary["definitions"],
        "novaSantaRita": {
            key: value for key, value in nova.items() if key != "coverageRows"
        },
        "artifactReferences": {
            "audit": OUTPUT_FILES[0],
            "dictionary": OUTPUT_FILES[1],
            "coverage": OUTPUT_FILES[2],
            "exactPanel": OUTPUT_FILES[3],
            "recomputationQA": OUTPUT_FILES[4],
            "novaSantaRita": OUTPUT_FILES[5],
            "stabilityDraft": OUTPUT_FILES[6],
            "limitations": OUTPUT_FILES[7],
        },
        "externalReviewQuestions": [
            "A evidência é suficiente para confirmar que as fontes abertas autorizadas não permitem materializar os componentes exatos?",
            "Deve ser aberta uma rota formal de acesso ao Sedap/Inep ou coordenação com a rede para obter a Situação do Aluno agregada no grão aceito?",
            "O draft de regra de pequeno denominador pode avançar para pré-registro externo sem escolher limiar antes dos dados?",
            "C5 deve permanecer não atendido e H2 não avaliável até uma fonte exata ser autorizada?",
            "O Job 6 e o Gate 11 devem permanecer bloqueados?",
        ],
        "decisionsMade": {
            "trajectoryPatternSelected": False,
            "c5Assessed": False,
            "smallDenominatorRuleFinalized": False,
            "h2Approved": False,
            "job6Started": False,
        },
        "nextActor": "GPT-5.6 Pro external judgment",
    }

    staging = staging_directory_for(output_root)
    try:
        (staging / OUTPUT_FILES[0]).write_text(
            _audit_markdown(inputs=inputs, coverage=coverage, region_codes=region_codes),
            encoding="utf-8",
            newline="\n",
        )
        write_json(staging / OUTPUT_FILES[1], dictionary)
        write_csv_gzip(staging / OUTPUT_FILES[2], coverage)
        write_csv_gzip(staging / OUTPUT_FILES[3], exact_panel)
        write_csv_gzip(staging / OUTPUT_FILES[4], recomputation_qa)
        write_json(staging / OUTPUT_FILES[5], nova)
        (staging / OUTPUT_FILES[6]).write_text(
            _stability_draft(), encoding="utf-8", newline="\n"
        )
        write_json(staging / OUTPUT_FILES[7], limitations)
        write_json(staging / OUTPUT_FILES[8], external_package)

        frames = {
            OUTPUT_FILES[2]: coverage,
            OUTPUT_FILES[3]: exact_panel,
            OUTPUT_FILES[4]: recomputation_qa,
        }
        artifacts = [
            _artifact_record(staging, name, frames.get(name)) for name in OUTPUT_FILES[:-1]
        ]
        manifest = {
            "schemaVersion": "vocacoes-pne-v7-job5d-manifest-v1",
            "jobId": JOB_ID,
            "classification": "SOURCE_REFRESH",
            "requestedScope": "DATA_DISCOVERY + DATA_MATERIALIZATION_ONLY",
            "finalState": FINAL_STATE,
            "objective": inputs["contract"]["objective"],
            "sourceInputs": {
                "checkpoints": inputs["checkpoints"],
                "rateAcquisitionManifest": inputs["rateAcquisitionManifest"],
                "rateLong": inputs["rateLong"],
                "rawRateSources": inputs["rawRateSources"],
                "methodologySources": inputs["methodologySources"],
                "microdataAudit": inputs["microdataAudit"],
            },
            "formulas": {
                indicator: definition["formula"]
                for indicator, definition in dictionary["definitions"].items()
            },
            "formulasAltered": False,
            "artifacts": artifacts,
            "summary": {
                "outputCount": 10,
                "coverageRowCount": len(coverage),
                "officialRateOnlyRowCount": int(
                    coverage["coverage_state"].eq("OFFICIAL_RATE_ONLY").sum()
                ),
                "sourceUnavailableRowCount": int(
                    coverage["coverage_state"].eq("SOURCE_UNAVAILABLE").sum()
                ),
                "exactComponentRowCount": 0,
                "recomputationQaRowCount": 0,
                "municipalityCount": 497,
                "valeMunicipalityCount": 10,
                "novaSantaRitaCoverageRowCount": len(nova_coverage),
            },
            "generation": {
                "controlledStaging": True,
                "validatedBeforePromotion": True,
                "atomicFileWrites": True,
                "transactionalDirectoryPromotion": True,
                "rollbackImplemented": True,
                "identicalFilesPreservedByNoOpPromotion": True,
                "databaseUsed": False,
                "networkUsed": True,
                "networkHosts": ["download.inep.gov.br"],
                "fullBuildUsed": False,
                "publicDataChanged": False,
                "job5bOrJob5cArtifactsChanged": False,
                "job5bOrH2Rerun": False,
                "job6Started": False,
                "gate11Status": "BLOCKED",
            },
            "forbiddenMethodsUsed": [],
            "externalReviewRequired": True,
            "nextActor": "GPT-5.6 Pro",
        }
        write_json(staging / OUTPUT_FILES[9], manifest)
        validation = _validate_staging(staging)
        promotion = _promote_transactionally(staging, output_root)
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise

    checked = validate_existing_output(output_root)
    return {
        **checked,
        "promotion": promotion,
        "validation": validation,
        "operationalManifestSha256": sha256_file(output_root / OUTPUT_FILES[9]),
    }


def validate_existing_output(output_root: Path = DEFAULT_OUTPUT_ROOT) -> dict[str, Any]:
    output_root = output_root.resolve()
    assert_outside_public_data(output_root, REPO_ROOT)
    validation = _validate_staging(output_root)
    return {
        **validation,
        "outputRoot": str(output_root),
        "operationalManifestSha256": sha256_file(output_root / OUTPUT_FILES[9]),
    }
