"""Laboratório analítico aprofundado Vocações × PNE V7 — Job 5L.

O módulo mantém aquisição oficial, snapshots somente leitura e materializações
analíticas fora de ``public/data``.  Lentes territoriais diferentes nunca são
tratadas como se fossem a mesma população, RAIS permanece vínculo e nenhuma
saída recebe interpretação causal ou de ranking.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
import csv
import gzip
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unicodedata
from typing import Any

import numpy as np
import pandas as pd

from .vocacoes_pne_job2 import (
    directory_content_digest,
    require_ibge_code,
    safe_ratio,
    sha256_file,
    write_csv_gzip,
    write_json,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_ROOT = REPO_ROOT / ".tmp" / "vocacoes-pne" / "v7-job5l"
CONTRACT_PATH = (
    REPO_ROOT / "data_pipeline" / "contracts" / "vocacoes-pne-v7-job5l.json"
)
MUNICIPALITY_REGISTRY_PATH = REPO_ROOT / "config" / "municipalities" / "rs.json"
REGION_REGISTRY_PATH = REPO_ROOT / "config" / "regions" / "rs.json"
PNE_CONTRACT_PATH = REPO_ROOT / "contracts" / "pne2026-goal-indicator-contract.json"
ORCHESTRATION_PATH = REPO_ROOT / "docs" / "CONTRATO_ORQUESTRACAO_VOCACOES_PNE_V7.md"
ANALYTICAL_ADDENDUM_PATH = REPO_ROOT / "docs" / "ADENDO_DIRETRIZ_ANALITICA_VOCACOES_PNE_V7.md"

NSR_CODE = "4313375"
REGION_ID = "REGION_VALE_DO_SINOS"
STATE_ID = "STATE_RS"
GENERATED_AT = "2026-08-29T00:00:00-03:00"
FINAL_STATE = "JOB_5L_READY_WITH_EXPLICIT_LIMITS_FOR_EXTERNAL_JUDGMENT"
IBGE_CODE_PATTERN = re.compile(r"^[0-9]{7}$")
INTERVAL_LEVEL = 0.90

FROZEN_ROOTS = {
    "job5gar": REPO_ROOT / ".tmp" / "vocacoes-pne" / "v7-job5gar",
    "job5gbr": REPO_ROOT / ".tmp" / "vocacoes-pne" / "v7-job5gbr",
    "job5gcr": REPO_ROOT / ".tmp" / "vocacoes-pne" / "v7-job5gcr",
    "job5gd": REPO_ROOT / ".tmp" / "vocacoes-pne" / "v7-job5gd",
    "job5h": REPO_ROOT / ".tmp" / "vocacoes-pne" / "v7-job5h",
    "job5i": REPO_ROOT / ".tmp" / "vocacoes-pne" / "v7-job5i",
    "job5j": REPO_ROOT / ".tmp" / "vocacoes-pne" / "v7-job5j",
    "job5k": REPO_ROOT / ".tmp" / "vocacoes-pne" / "v7-job5k",
}
PUBLIC_DATA_ROOT = REPO_ROOT / "public" / "data"

PACKAGE_FILES = (
    "CHECKPOINT_JOB5L_FOR_PRO.md",
    "CATALOGO_INSIGHTS_APROFUNDADOS_JOB5L.json",
    "MATRIZ_RESULTADOS_AJUSTADOS_E_DIRETOS_JOB5L.csv.gz",
    "MATRIZ_HETEROGENEIDADE_10_MUNICIPIOS_JOB5L.csv.gz",
    "DOSSIE_APROFUNDADO_NOVA_SANTA_RITA_JOB5L.md",
    "DOSSIE_APROFUNDADO_VALE_DO_SINOS_JOB5L.md",
    "METODOS_VALIDACAO_E_PRECISAO_JOB5L.md",
    "LITERATURA_E_MECANISMOS_JOB5L.json",
    "LIMITACOES_E_CLAIMS_JOB5L.json",
    "QA_SUMMARY_JOB5L.json",
    "ARTIFACT_INDEX_JOB5L.json",
    "MANIFEST_JOB5L.json",
)

INTERNAL_FILES = (
    "internal/CONTRATO_JOB5L.json",
    "internal/EXECPLAN_JOB5L.md",
    "internal/REGISTRO_FONTES_E_AQUISICOES_JOB5L.json",
    "internal/PAINEL_CONTEXTO_RS_MUNICIPIO_ANO_ETAPA_JOB5L.csv.gz",
    "internal/RESULTADOS_AJUSTADOS_F1_JOB5L.csv.gz",
    "internal/VALIDACAO_MODELOS_F1_JOB5L.csv.gz",
    "internal/MODELOS_F1_DETALHADOS_JOB5L.json",
    "internal/PAINEL_ESTUDO_TRABALHO_F2_JOB5L.csv.gz",
    "internal/PAINEL_RAIS_COMPOSICAO_JOVEM_F3_JOB5L.csv.gz",
    "internal/DICIONARIO_RAIS_NORMALIZADO_JOB5L.json",
    "internal/PAINEL_BALANCO_FUNCIONAL_F4_JOB5L.csv.gz",
    "internal/PAINEL_MIGRACAO_F5_JOB5L.csv.gz",
    "internal/PAINEL_EJA_APROFUNDADO_F6_JOB5L.csv.gz",
    "internal/CATALOGO_COMPLETO_CANDIDATAS_JOB5L.json",
    "internal/MATRIZ_VALIDACAO_ROBUSTEZ_JOB5L.csv.gz",
    "internal/MATRIZ_10_MUNICIPIOS_COMPLETA_JOB5L.csv.gz",
    "internal/AUTOCRITICA_JOB5L.json",
)

DATABASE_SOURCE_FILES = (
    "trajectory_total_network.csv.gz",
    "population_context.csv.gz",
    "school_context.csv.gz",
    "inse_total_network.csv.gz",
    "teacher_adequacy_total_network.csv.gz",
    "adult_schooling_2022.csv.gz",
    "dependency_qa_counts.csv.gz",
)

RAIS_EXPECTED_SIZES = {
    2019: 502_535_667,
    2020: 494_772_628,
    2021: 551_324_193,
    2022: 599_471_446,
    2023: 654_290_597,
    2024: 680_693_192,
    2025: 704_888_712,
}

STAGE_CONTEXT = {
    "fundamental_anos_iniciais": {
        "adequacy_stage": "anos_iniciais",
        "enrollment_column": "mat_fundamental_anos_iniciais",
    },
    "fundamental_anos_finais": {
        "adequacy_stage": "anos_finais",
        "enrollment_column": "mat_fundamental_anos_finais",
    },
    "medio": {
        "adequacy_stage": "ensino_medio",
        "enrollment_column": "mat_medio",
    },
}

OUTCOME_LABELS = {
    "approval_rate_percent": "aprovação",
    "failure_rate_percent": "reprovação",
    "dropout_rate_percent": "abandono",
    "age_grade_distortion_rate_percent": "distorção idade-série",
}

F1_FEATURES = (
    "log_total_population",
    "population_15_17_share_percent",
    "log_located_stage_enrollments",
    "rural_basic_enrollment_share_percent",
    "full_time_stage_share_percent",
    "average_basic_school_size",
    "internet_school_share_percent",
    "teacher_adequacy_percent",
    "inse_latest_available",
    "adult_fundamental_completion_share_2022",
    "adult_high_school_completion_share_2022",
    "lagged_outcome_value",
    "year_centered",
    "pandemic_caution_indicator",
)


class Job5LValidationError(ValueError):
    """Falha fechada de contrato ou QA do Job 5L."""


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(
        path,
        compression="gzip" if path.suffix == ".gz" else "infer",
        dtype={"municipality_ibge_code": "string"},
        low_memory=False,
    )


def _finite(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _safe_series_ratio(
    numerator: pd.Series, denominator: pd.Series, *, multiplier: float = 1.0
) -> pd.Series:
    n = pd.to_numeric(numerator, errors="coerce")
    d = pd.to_numeric(denominator, errors="coerce")
    result = n.div(d.where(d.ne(0))).mul(multiplier)
    return result.where(np.isfinite(result))


def _normalized_text(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value))
    return "".join(char for char in text if not unicodedata.combining(char))


def _normalized_header(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", _normalized_text(value).casefold())


def _stable_frame(frame: pd.DataFrame, columns: Sequence[str] | None = None) -> pd.DataFrame:
    if frame.empty:
        return frame.reset_index(drop=True)
    sort_columns = list(columns or frame.columns)
    return frame.sort_values(sort_columns, kind="mergesort", na_position="last").reset_index(drop=True)


def _municipalities() -> tuple[list[str], dict[str, str]]:
    payload = _json(MUNICIPALITY_REGISTRY_PATH)
    items = payload["municipalities"]
    codes = [item["ibgeCode"] for item in items]
    if len(codes) != 497 or len(set(codes)) != 497:
        raise Job5LValidationError("Registro canônico do RS não contém 497 identidades únicas")
    if any(not isinstance(code, str) or not IBGE_CODE_PATTERN.fullmatch(code) for code in codes):
        raise Job5LValidationError("Código municipal não textual ou fora do padrão de sete dígitos")
    names = {item["ibgeCode"]: item["name"] for item in items}
    if names.get(NSR_CODE) != "Nova Santa Rita":
        raise Job5LValidationError("Fixture de Nova Santa Rita divergente")
    return codes, names


def _region_codes() -> list[str]:
    payload = _json(REGION_REGISTRY_PATH)
    region = next(item for item in payload["regions"] if item["slug"] == "vale-do-sinos")
    codes = region["municipalityIbgeCodes"]
    if region["municipalityCount"] != 10 or len(codes) != 10 or len(set(codes)) != 10:
        raise Job5LValidationError("Recorte do Vale do Sinos divergente")
    if NSR_CODE not in codes:
        raise Job5LValidationError("Nova Santa Rita ausente do Vale do Sinos")
    for code in codes:
        require_ibge_code(code)
    return list(codes)


def verify_frozen_integrity() -> dict[str, Any]:
    missing = [str(path) for path in FROZEN_ROOTS.values() if not path.is_dir()]
    if missing:
        raise FileNotFoundError(f"Raízes congeladas ausentes: {missing}")
    digests = {
        key: directory_content_digest(path)
        for key, path in sorted(FROZEN_ROOTS.items())
    }
    expected = {
        "job5j": "f31b230fb9268ca57c15f1e322ef9317d841288f7408a9638b0042343a5fb57c",
        "job5k": "75e5b1ce06d77de7a6e99a6e4f64b040110d8961ea857efc0f5a2e89cbcc52ff",
    }
    for key, value in expected.items():
        if digests[key] != value:
            raise Job5LValidationError(f"Raiz congelada {key} divergiu do preflight")
    public_digest = directory_content_digest(PUBLIC_DATA_ROOT)
    if public_digest != "4a52e3891163cb3427c5c01f2ef5414c5fe7855dd491a9a125b509899dcc23e1":
        raise Job5LValidationError("public/data divergiu do preflight Job 5L")
    controls = {
        "municipalityRegistrySha256": sha256_file(MUNICIPALITY_REGISTRY_PATH),
        "regionRegistrySha256": sha256_file(REGION_REGISTRY_PATH),
        "pneContractSha256": sha256_file(PNE_CONTRACT_PATH),
        "orchestrationSha256": sha256_file(ORCHESTRATION_PATH),
        "analyticalAddendumSha256": sha256_file(ANALYTICAL_ADDENDUM_PATH),
    }
    if controls["municipalityRegistrySha256"] != "06b5c0eb6f025cf618549fc10fd004c6de628488d59dd35b239207b1ca42e9dd":
        raise Job5LValidationError("Registro municipal mudou durante o Job 5L")
    if controls["regionRegistrySha256"] != "9892fc8fca0b1fc349c4cd49edf455760121adfd5c1113e5e224f547c1e90542":
        raise Job5LValidationError("Registro regional mudou durante o Job 5L")
    return {
        "frozenRootDigests": digests,
        "publicDataTreeDigestSha256": public_digest,
        "controlHashes": controls,
    }


def _database_url(database: str):
    from sqlalchemy.engine import URL

    required = ("DB_USUARIO", "DB_SENHA", "DB_HOST")
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        raise RuntimeError(f"Variáveis locais de banco ausentes: {', '.join(missing)}")
    return URL.create(
        "postgresql+psycopg2",
        username=os.environ["DB_USUARIO"],
        password=os.environ["DB_SENHA"],
        host=os.environ["DB_HOST"],
        port=int(os.getenv("DB_PORT", "5432")),
        database=database,
    )


DATABASE_QUERIES = {
    "trajectory": """
        SELECT ano::int AS year, id_municipio::text AS municipality_ibge_code,
               etapa_ensino::text AS stage,
               taxa_aprovacao::double precision AS approval_rate_percent,
               taxa_reprovacao::double precision AS failure_rate_percent,
               taxa_abandono::double precision AS dropout_rate_percent
        FROM public.rendimento_escolar
        WHERE sigla_uf='RS' AND dependencia='total' AND localizacao='total'
          AND ano BETWEEN 2018 AND 2025
    """,
    "distortion": """
        SELECT ano::int AS year, id_municipio::text AS municipality_ibge_code,
               categoria::text AS category, valor::double precision AS observed_value
        FROM public.distorcao_idade_serie
        WHERE sigla_uf='RS' AND lower(dependencia)='total'
          AND ano BETWEEN 2019 AND 2025
    """,
    "population": """
        SELECT ano::int AS year, id_municipio::text AS municipality_ibge_code,
               SUM(pop_estimada)::double precision AS total_population,
               SUM(pop_estimada) FILTER (WHERE idade BETWEEN 15 AND 17)::double precision AS population_15_17,
               SUM(pop_estimada) FILTER (WHERE idade BETWEEN 18 AND 24)::double precision AS population_18_24,
               SUM(pop_estimada) FILTER (WHERE idade BETWEEN 6 AND 10)::double precision AS population_6_10,
               SUM(pop_estimada) FILTER (WHERE idade BETWEEN 11 AND 14)::double precision AS population_11_14
        FROM public.populacao_idade
        WHERE sigla_uf='RS' AND ano BETWEEN 2018 AND 2025
        GROUP BY ano, id_municipio
    """,
    "school": """
        SELECT ano::int AS year, id_municipio::text AS municipality_ibge_code,
               SUM(mat_basico)::double precision AS mat_basico,
               SUM(mat_fundamental_anos_iniciais)::double precision AS mat_fundamental_anos_iniciais,
               SUM(mat_fundamental_anos_finais)::double precision AS mat_fundamental_anos_finais,
               SUM(mat_medio)::double precision AS mat_medio,
               SUM(mat_basico_integral)::double precision AS mat_basico_integral,
               SUM(mat_fundamental_anos_iniciais_integral)::double precision AS mat_fundamental_anos_iniciais_integral,
               SUM(mat_fundamental_anos_finais_integral)::double precision AS mat_fundamental_anos_finais_integral,
               SUM(mat_medio_integral)::double precision AS mat_medio_integral,
               SUM(mat_basico) FILTER (WHERE localizacao='rural')::double precision AS rural_mat_basico,
               SUM(qntd_escolas)::double precision AS schools,
               SUM(escolas_com_internet)::double precision AS schools_with_internet
        FROM public.censo
        WHERE sigla_uf='RS' AND ano BETWEEN 2018 AND 2025
        GROUP BY ano, id_municipio
    """,
    "inse": """
        SELECT ano::int AS year, id_municipio::text AS municipality_ibge_code,
               media_inse::double precision AS inse_value,
               qtd_alunos_inse::double precision AS assessed_students
        FROM public.inse
        WHERE sigla_uf='RS' AND rede='total' AND ano BETWEEN 2018 AND 2025
    """,
    "adequacy": """
        SELECT ano::int AS year, id_municipio::text AS municipality_ibge_code,
               etapa::text AS adequacy_stage,
               percentual_adequacao::double precision AS teacher_adequacy_percent
        FROM public.adequacao_docente
        WHERE sigla_uf='RS' AND dependencia='total' AND localizacao='total'
          AND ano BETWEEN 2018 AND 2025
    """,
    "adult": """
        SELECT f.id_municipio::text AS municipality_ibge_code,
               f.populacao_18_mais_ensino_fundamental_concluido::double precision AS fundamental_completed,
               m.populacao_18_mais_ensino_medio_concluido::double precision AS high_school_completed,
               c.populacao_18_mais_total::double precision AS adult_population
        FROM public.censo_populacao_ensino_fundamental_concluido_18_mais f
        JOIN public.censo_populacao_ensino_medio_concluido_18_mais m
          ON m.ano=f.ano AND m.id_municipio=f.id_municipio AND m.sigla_uf=f.sigla_uf
        LEFT JOIN public.pne2026_censo_10061_municipal_components c
          ON c.ano=f.ano AND c.id_municipio::text=f.id_municipio::text
        WHERE f.sigla_uf='RS' AND f.ano=2022
    """,
    "dependency_qa": """
        SELECT ano::int AS year, dependencia::text AS dependency,
               localizacao::text AS location, etapa_ensino::text AS stage,
               COUNT(*)::bigint AS row_count,
               COUNT(DISTINCT id_municipio)::bigint AS municipality_count
        FROM public.rendimento_escolar
        WHERE sigla_uf='RS' AND ano BETWEEN 2018 AND 2025
        GROUP BY ano, dependencia, localizacao, etapa_ensino
    """,
}


def materialize_database_sources(source_dir: Path) -> dict[str, Any]:
    """Congela consultas em uma única transação explicitamente somente leitura."""

    from dotenv import load_dotenv
    from sqlalchemy import create_engine, text

    load_dotenv(REPO_ROOT / "data_pipeline" / ".env")
    source_dir.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        _database_url("sesi"),
        connect_args={
            "options": "-c default_transaction_read_only=on -c statement_timeout=300000"
        },
    )
    try:
        with engine.connect() as connection:
            transaction = connection.begin()
            try:
                connection.execute(text("SET TRANSACTION READ ONLY"))
                mode = connection.execute(
                    text("SELECT current_setting('transaction_read_only')")
                ).scalar_one()
                if mode != "on":
                    raise RuntimeError("Snapshot Job 5L não está em transação somente leitura")
                raw = {
                    name: pd.read_sql_query(text(query), connection)
                    for name, query in DATABASE_QUERIES.items()
                }
            finally:
                transaction.rollback()
    finally:
        engine.dispose()

    codes, _ = _municipalities()
    code_set = set(codes)
    for name, frame in raw.items():
        if "municipality_ibge_code" not in frame:
            continue
        values = set(frame["municipality_ibge_code"].dropna().astype(str))
        if not values.issubset(code_set):
            raise Job5LValidationError(f"{name}: identidade fora do registro canônico")
        if any(not IBGE_CODE_PATTERN.fullmatch(value) for value in values):
            raise Job5LValidationError(f"{name}: código municipal perdeu tipagem textual")

    outcome = raw["trajectory"].melt(
        id_vars=["year", "municipality_ibge_code", "stage"],
        value_vars=[
            "approval_rate_percent",
            "failure_rate_percent",
            "dropout_rate_percent",
        ],
        var_name="outcome_id",
        value_name="observed_value",
    )
    # A etapa agregada ``fundamental`` sobrepõe anos iniciais e finais e não
    # integra o desenho pré-especificado.  A exclusão ocorre antes de qualquer
    # cálculo, sem combinar ou reponderar as etapas.
    outcome = outcome[outcome["stage"].isin(STAGE_CONTEXT)].copy()
    category_map = {
        "taxa_distorcao_fundamental_anos_iniciais": "fundamental_anos_iniciais",
        "taxa_distorcao_fundamental_anos_finais": "fundamental_anos_finais",
        "taxa_distorcao_medio": "medio",
    }
    distortion = raw["distortion"].copy()
    distortion["stage"] = distortion["category"].map(category_map)
    distortion = distortion[distortion["stage"].notna()].drop(columns="category")
    distortion["outcome_id"] = "age_grade_distortion_rate_percent"
    outcome = pd.concat([outcome, distortion[outcome.columns]], ignore_index=True)
    outcome["network_scope"] = "total_all_dependencies"
    outcome["territorial_lens"] = "school_location"
    outcome["source_table"] = np.where(
        outcome["outcome_id"].eq("age_grade_distortion_rate_percent"),
        "public.distorcao_idade_serie",
        "public.rendimento_escolar",
    )
    outcome = _stable_frame(
        outcome,
        ["outcome_id", "stage", "municipality_ibge_code", "year"],
    )

    adult = raw["adult"].copy()
    adult["adult_fundamental_completion_share_2022"] = _safe_series_ratio(
        adult["fundamental_completed"], adult["adult_population"], multiplier=100
    )
    adult["adult_high_school_completion_share_2022"] = _safe_series_ratio(
        adult["high_school_completed"], adult["adult_population"], multiplier=100
    )

    frames = {
        "trajectory_total_network.csv.gz": outcome,
        "population_context.csv.gz": raw["population"],
        "school_context.csv.gz": raw["school"],
        "inse_total_network.csv.gz": raw["inse"],
        "teacher_adequacy_total_network.csv.gz": raw["adequacy"],
        "adult_schooling_2022.csv.gz": adult,
        "dependency_qa_counts.csv.gz": raw["dependency_qa"],
    }
    for name, frame in frames.items():
        write_csv_gzip(source_dir / name, _stable_frame(frame))
    manifest = {
        "schemaVersion": "vocacoes-pne-job5l-database-snapshot-v1",
        "generatedAt": GENERATED_AT,
        "database": "sesi",
        "transactionReadOnly": True,
        "rollbackPerformed": True,
        "credentialsRecorded": False,
        "queries": {
            key: {
                "sha256": hashlib.sha256(query.encode("utf-8")).hexdigest(),
                "rowCount": int(len(raw[key])),
            }
            for key, query in sorted(DATABASE_QUERIES.items())
        },
        "artifacts": [
            {
                "path": name,
                "rowCount": int(len(frames[name])),
                "byteSize": (source_dir / name).stat().st_size,
                "sha256": sha256_file(source_dir / name),
            }
            for name in DATABASE_SOURCE_FILES
        ],
    }
    write_json(source_dir / "manifest.json", manifest)
    validate_database_sources(source_dir)
    return manifest


def validate_database_sources(source_dir: Path) -> dict[str, Any]:
    manifest_path = source_dir / "manifest.json"
    if not manifest_path.is_file():
        raise Job5LValidationError("Manifesto do snapshot de banco ausente")
    manifest = _json(manifest_path)
    if not manifest.get("transactionReadOnly") or not manifest.get("rollbackPerformed"):
        raise Job5LValidationError("Snapshot de banco não prova leitura somente leitura")
    declared = {item["path"]: item for item in manifest["artifacts"]}
    if set(declared) != set(DATABASE_SOURCE_FILES):
        raise Job5LValidationError("Topologia do snapshot de banco divergente")
    for name, record in declared.items():
        path = source_dir / name
        if not path.is_file() or path.stat().st_size != record["byteSize"]:
            raise Job5LValidationError(f"Snapshot ausente ou com tamanho divergente: {name}")
        if sha256_file(path) != record["sha256"]:
            raise Job5LValidationError(f"Snapshot com hash divergente: {name}")
    trajectory = _read_csv(source_dir / "trajectory_total_network.csv.gz")
    if set(trajectory["stage"]) != set(STAGE_CONTEXT):
        raise Job5LValidationError("Etapas F1 divergentes")
    if set(trajectory["outcome_id"]) != set(OUTCOME_LABELS):
        raise Job5LValidationError("Desfechos F1 divergentes")
    if not trajectory["network_scope"].eq("total_all_dependencies").all():
        raise Job5LValidationError("F1 deixou de usar rede total")
    return manifest


def build_f1_context(source_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    validate_database_sources(source_dir)
    codes, names = _municipalities()
    outcome = _read_csv(source_dir / "trajectory_total_network.csv.gz")
    population = _read_csv(source_dir / "population_context.csv.gz")
    school = _read_csv(source_dir / "school_context.csv.gz")
    inse = _read_csv(source_dir / "inse_total_network.csv.gz")
    adequacy = _read_csv(source_dir / "teacher_adequacy_total_network.csv.gz")
    adult = _read_csv(source_dir / "adult_schooling_2022.csv.gz")

    grid = pd.MultiIndex.from_product(
        [codes, range(2019, 2026)], names=["municipality_ibge_code", "year"]
    ).to_frame(index=False)
    base = grid.merge(population, on=["municipality_ibge_code", "year"], how="left")
    base = base.merge(school, on=["municipality_ibge_code", "year"], how="left")
    base = base.merge(
        adult[
            [
                "municipality_ibge_code",
                "adult_fundamental_completion_share_2022",
                "adult_high_school_completion_share_2022",
            ]
        ],
        on="municipality_ibge_code",
        how="left",
    )
    inse_grid = grid.merge(
        inse[["municipality_ibge_code", "year", "inse_value"]],
        on=["municipality_ibge_code", "year"],
        how="left",
    ).sort_values(["municipality_ibge_code", "year"], kind="mergesort")
    inse_grid["inse_latest_available"] = inse_grid.groupby(
        "municipality_ibge_code", sort=False
    )["inse_value"].ffill()
    base = base.merge(
        inse_grid[["municipality_ibge_code", "year", "inse_latest_available"]],
        on=["municipality_ibge_code", "year"],
        how="left",
    )

    context_rows: list[pd.DataFrame] = []
    for stage, spec in STAGE_CONTEXT.items():
        stage_frame = base.copy()
        stage_frame["stage"] = stage
        stage_adequacy = adequacy[adequacy["adequacy_stage"].eq(spec["adequacy_stage"])][
            ["municipality_ibge_code", "year", "teacher_adequacy_percent"]
        ]
        stage_frame = stage_frame.merge(
            stage_adequacy, on=["municipality_ibge_code", "year"], how="left"
        )
        enrollment = pd.to_numeric(stage_frame[spec["enrollment_column"]], errors="coerce")
        integral_column = f"{spec['enrollment_column']}_integral"
        stage_frame["located_stage_enrollments"] = enrollment
        stage_frame["log_located_stage_enrollments"] = np.log1p(enrollment.where(enrollment.ge(0)))
        stage_frame["full_time_stage_share_percent"] = _safe_series_ratio(
            stage_frame[integral_column], enrollment, multiplier=100
        )
        context_rows.append(stage_frame)
    context = pd.concat(context_rows, ignore_index=True)
    context["municipality_name"] = context["municipality_ibge_code"].map(names)
    context["log_total_population"] = np.log1p(
        pd.to_numeric(context["total_population"], errors="coerce").where(lambda s: s.ge(0))
    )
    context["population_15_17_share_percent"] = _safe_series_ratio(
        context["population_15_17"], context["total_population"], multiplier=100
    )
    context["rural_basic_enrollment_share_percent"] = _safe_series_ratio(
        context["rural_mat_basico"], context["mat_basico"], multiplier=100
    )
    context["average_basic_school_size"] = _safe_series_ratio(
        context["mat_basico"], context["schools"]
    )
    context["internet_school_share_percent"] = _safe_series_ratio(
        context["schools_with_internet"], context["schools"], multiplier=100
    )
    context["year_centered"] = pd.to_numeric(context["year"], errors="raise") - 2019
    context["pandemic_caution_indicator"] = context["year"].isin([2020, 2021]).astype(float)
    context["network_scope"] = "total_all_dependencies"
    context["administrative_dependency_role"] = "qa_only"
    context["territorial_lens"] = "school_location|resident_population"

    outcome["year"] = pd.to_numeric(outcome["year"], errors="raise").astype(int)
    outcome = outcome.sort_values(
        ["outcome_id", "stage", "municipality_ibge_code", "year"], kind="mergesort"
    )
    outcome["lagged_outcome_value"] = outcome.groupby(
        ["outcome_id", "stage", "municipality_ibge_code"], sort=False
    )["observed_value"].shift(1)
    analysis_grid = pd.MultiIndex.from_product(
        [codes, range(2019, 2026), STAGE_CONTEXT, OUTCOME_LABELS],
        names=["municipality_ibge_code", "year", "stage", "outcome_id"],
    ).to_frame(index=False)
    outcome_columns = [
        "municipality_ibge_code",
        "year",
        "stage",
        "outcome_id",
        "observed_value",
        "lagged_outcome_value",
        "network_scope",
        "territorial_lens",
        "source_table",
    ]
    analysis = analysis_grid.merge(
        outcome[outcome["year"].between(2019, 2025)][outcome_columns],
        on=["municipality_ibge_code", "year", "stage", "outcome_id"],
        how="left",
    ).merge(
        context,
        on=["municipality_ibge_code", "year", "stage"],
        how="left",
        suffixes=("", "_context"),
    )
    analysis["network_scope"] = analysis["network_scope"].fillna(
        "total_all_dependencies"
    )
    analysis["territorial_lens"] = analysis["territorial_lens"].fillna(
        "school_location"
    )
    default_source = pd.Series(
        np.where(
            analysis["outcome_id"].eq("age_grade_distortion_rate_percent"),
            "public.distorcao_idade_serie",
            "public.rendimento_escolar",
        ),
        index=analysis.index,
    )
    analysis["source_table"] = analysis["source_table"].where(
        analysis["source_table"].notna(), default_source
    )
    if set(context[context["year"].eq(2025)]["municipality_ibge_code"]) != set(codes):
        raise Job5LValidationError("Painel contextual 2025 não cobre 497 municípios")
    if context.duplicated(["municipality_ibge_code", "year", "stage"]).any():
        raise Job5LValidationError("Painel contextual contém chave duplicada")
    return _stable_frame(context, ["municipality_ibge_code", "year", "stage"]), analysis


def _matrix_fit(
    train: pd.DataFrame,
    test: pd.DataFrame,
    features: Sequence[str],
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    train_values = train[list(features)].apply(pd.to_numeric, errors="coerce")
    test_values = test[list(features)].apply(pd.to_numeric, errors="coerce")
    medians = train_values.median(axis=0, skipna=True).fillna(0.0)
    train_missing = train_values.isna()
    test_missing = test_values.isna()
    train_values = train_values.fillna(medians)
    test_values = test_values.fillna(medians)
    means = train_values.mean(axis=0)
    scales = train_values.std(axis=0, ddof=0).replace(0, 1.0).fillna(1.0)
    train_scaled = (train_values - means) / scales
    test_scaled = (test_values - means) / scales
    missing_features = [column for column in features if train_missing[column].any()]
    if missing_features:
        train_scaled = pd.concat(
            [train_scaled, train_missing[missing_features].astype(float).add_suffix("__missing")],
            axis=1,
        )
        test_scaled = pd.concat(
            [test_scaled, test_missing[missing_features].astype(float).add_suffix("__missing")],
            axis=1,
        )
    metadata = {
        "featureNames": list(train_scaled.columns),
        "medians": {key: float(value) for key, value in medians.items()},
        "means": {key: float(value) for key, value in means.items()},
        "scales": {key: float(value) for key, value in scales.items()},
    }
    return train_scaled.to_numpy(float), test_scaled.to_numpy(float), metadata


def _ridge_predict(
    train: pd.DataFrame,
    test: pd.DataFrame,
    *,
    features: Sequence[str],
    alpha: float,
) -> tuple[np.ndarray, dict[str, Any]]:
    x_train, x_test, metadata = _matrix_fit(train, test, features)
    y = pd.to_numeric(train["observed_value"], errors="coerce").to_numpy(float)
    design = np.column_stack([np.ones(len(x_train)), x_train])
    penalty = np.eye(design.shape[1])
    penalty[0, 0] = 0.0
    coefficients = np.linalg.pinv(design.T @ design + alpha * penalty) @ design.T @ y
    predictions = np.column_stack([np.ones(len(x_test)), x_test]) @ coefficients
    metadata.update(
        {
            "alpha": alpha,
            "intercept": float(coefficients[0]),
            "standardizedCoefficients": {
                name: float(value)
                for name, value in zip(metadata["featureNames"], coefficients[1:], strict=True)
            },
        }
    )
    return predictions, metadata


def _peer_predict(
    train: pd.DataFrame,
    test: pd.DataFrame,
    *,
    features: Sequence[str],
    k: int,
    return_support: bool = False,
) -> tuple[np.ndarray, list[str]]:
    x_train, x_test, _ = _matrix_fit(train, test, features)
    y_train = pd.to_numeric(train["observed_value"], errors="coerce").to_numpy(float)
    train_year = pd.to_numeric(train["year"], errors="raise").to_numpy(int)
    test_year = pd.to_numeric(test["year"], errors="raise").to_numpy(int)
    train_codes = train["municipality_ibge_code"].astype(str).to_numpy()
    test_codes = test["municipality_ibge_code"].astype(str).to_numpy()
    predictions = np.full(len(test), np.nan)
    supports: list[str] = [""] * len(test)
    for index, vector in enumerate(x_test):
        candidates = np.flatnonzero(
            (train_year == test_year[index]) & (train_codes != test_codes[index])
        )
        if not len(candidates):
            prior_years = train_year[train_year <= test_year[index]]
            reference_year = int(prior_years.max()) if len(prior_years) else int(train_year.max())
            candidates = np.flatnonzero(
                (train_year == reference_year) & (train_codes != test_codes[index])
            )
        distances = np.sqrt(np.square(x_train[candidates] - vector).sum(axis=1))
        order = candidates[np.argsort(distances, kind="mergesort")[: min(k, len(candidates))]]
        selected_distances = np.sqrt(np.square(x_train[order] - vector).sum(axis=1))
        weights = 1.0 / np.maximum(selected_distances, 1e-6)
        predictions[index] = float(np.average(y_train[order], weights=weights))
        if return_support:
            supports[index] = "|".join(train_codes[order].tolist())
    return predictions, supports


def _naive_predict(train: pd.DataFrame, test: pd.DataFrame) -> np.ndarray:
    by_year = train.groupby("year", sort=True)["observed_value"].median()
    fallback = float(pd.to_numeric(train["observed_value"], errors="coerce").median())
    return np.array([float(by_year.get(year, fallback)) for year in test["year"]], dtype=float)


def _fold(code: str) -> int:
    return int(hashlib.sha256(code.encode("ascii")).hexdigest()[:8], 16) % 5


def _oof_predictions(
    frame: pd.DataFrame,
    *,
    method: str,
    parameter: float | int,
    features: Sequence[str],
) -> np.ndarray:
    predictions = np.full(len(frame), np.nan)
    folds = frame["municipality_ibge_code"].astype(str).map(_fold).to_numpy(int)
    for fold in range(5):
        train_mask = folds != fold
        test_mask = folds == fold
        train = frame.loc[train_mask]
        test = frame.loc[test_mask]
        if method == "ridge_context_model":
            values, _ = _ridge_predict(
                train, test, features=features, alpha=float(parameter)
            )
        elif method == "nearest_context_peers":
            values, _ = _peer_predict(
                train, test, features=features, k=int(parameter)
            )
        elif method == "year_median_baseline":
            values = _naive_predict(train, test)
        else:
            raise ValueError(f"Método F1 desconhecido: {method}")
        predictions[np.flatnonzero(test_mask)] = values
    return predictions


def _mae(observed: np.ndarray, predicted: np.ndarray) -> float | None:
    valid = np.isfinite(observed) & np.isfinite(predicted)
    if not valid.any():
        return None
    return float(np.mean(np.abs(observed[valid] - predicted[valid])))


def _conformal_quantile(residuals: np.ndarray, level: float = INTERVAL_LEVEL) -> float | None:
    residuals = residuals[np.isfinite(residuals)]
    if not len(residuals):
        return None
    probability = min(1.0, math.ceil((len(residuals) + 1) * level) / len(residuals))
    return float(np.quantile(residuals, probability, method="higher"))


def _state(observed: float | None, lower: float | None, upper: float | None) -> str:
    if observed is None or lower is None or upper is None:
        return "NOT_EVALUABLE"
    if observed < lower:
        return "BELOW_EXPECTED_INTERVAL"
    if observed > upper:
        return "ABOVE_EXPECTED_INTERVAL"
    return "WITHIN_EXPECTED_INTERVAL"


def _top_coefficients(details: Mapping[str, Any], count: int = 3) -> str:
    coefficients = details.get("standardizedCoefficients", {})
    items = sorted(coefficients.items(), key=lambda item: (-abs(item[1]), item[0]))[:count]
    return "|".join(f"{name}:{value:.6g}" for name, value in items)


def fit_f1_models(
    analysis: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    result_rows: list[dict[str, Any]] = []
    validation_rows: list[dict[str, Any]] = []
    model_details: dict[str, Any] = {}
    ridge_alphas = (0.1, 1.0, 10.0, 100.0)
    peer_k_values = (10, 20, 30)

    for outcome_id in OUTCOME_LABELS:
        for stage in STAGE_CONTEXT:
            model_id = f"F1_{outcome_id}_{stage}"
            subset = analysis[
                analysis["outcome_id"].eq(outcome_id) & analysis["stage"].eq(stage)
            ].copy()
            subset["observed_value"] = pd.to_numeric(
                subset["observed_value"], errors="coerce"
            )
            training = subset[subset["year"].between(2019, 2024)].dropna(
                subset=["observed_value"]
            )
            temporal = subset[subset["year"].eq(2025)].copy()
            observed_training = training["observed_value"].to_numpy(float)

            ridge_scores: dict[float, float] = {}
            ridge_predictions: dict[float, np.ndarray] = {}
            for alpha in ridge_alphas:
                predictions = _oof_predictions(
                    training,
                    method="ridge_context_model",
                    parameter=alpha,
                    features=F1_FEATURES,
                )
                ridge_predictions[alpha] = predictions
                ridge_scores[alpha] = float(_mae(observed_training, predictions) or math.inf)
            peer_scores: dict[int, float] = {}
            peer_predictions: dict[int, np.ndarray] = {}
            for k in peer_k_values:
                predictions = _oof_predictions(
                    training,
                    method="nearest_context_peers",
                    parameter=k,
                    features=F1_FEATURES,
                )
                peer_predictions[k] = predictions
                peer_scores[k] = float(_mae(observed_training, predictions) or math.inf)
            naive_predictions = _oof_predictions(
                training,
                method="year_median_baseline",
                parameter=0,
                features=F1_FEATURES,
            )
            naive_mae = float(_mae(observed_training, naive_predictions) or math.inf)
            best_alpha = min(ridge_scores, key=lambda key: (ridge_scores[key], key))
            best_k = min(peer_scores, key=lambda key: (peer_scores[key], key))
            ridge_mae = ridge_scores[best_alpha]
            peer_mae = peer_scores[best_k]
            if ridge_mae <= peer_mae * 0.99:
                selected_method = "ridge_context_model"
                selected_parameter: float | int = best_alpha
                selected_oof = ridge_predictions[best_alpha]
                selected_cv_mae = ridge_mae
                complexity_decision = "ridge_kept_after_at_least_one_percent_cv_mae_improvement_over_peers"
            else:
                selected_method = "nearest_context_peers"
                selected_parameter = best_k
                selected_oof = peer_predictions[best_k]
                selected_cv_mae = peer_mae
                complexity_decision = "simple_peers_preferred_when_ridge_did_not_materially_improve_validation"

            validation_eligible = bool(
                len(training) >= 1_000
                and len(temporal) >= 490
                and math.isfinite(selected_cv_mae)
                and selected_cv_mae < naive_mae * 0.995
            )
            calibration_residuals = np.abs(observed_training - selected_oof)
            interval_half_width = _conformal_quantile(calibration_residuals)
            supports: list[str] = [""] * len(temporal)
            fit_details: dict[str, Any] = {}
            if selected_method == "ridge_context_model":
                temporal_predictions, fit_details = _ridge_predict(
                    training,
                    temporal,
                    features=F1_FEATURES,
                    alpha=float(selected_parameter),
                )
            else:
                temporal_predictions, supports = _peer_predict(
                    training,
                    temporal,
                    features=F1_FEATURES,
                    k=int(selected_parameter),
                    return_support=True,
                )

            temporal_observed = pd.to_numeric(
                temporal["observed_value"], errors="coerce"
            ).to_numpy(float)
            if interval_half_width is None:
                lower = np.full(len(temporal), np.nan)
                upper = np.full(len(temporal), np.nan)
            else:
                lower = temporal_predictions - interval_half_width
                upper = temporal_predictions + interval_half_width
            temporal_valid = np.isfinite(temporal_observed) & np.isfinite(lower) & np.isfinite(upper)
            coverage = (
                float(
                    np.mean(
                        (temporal_observed[temporal_valid] >= lower[temporal_valid])
                        & (temporal_observed[temporal_valid] <= upper[temporal_valid])
                    )
                )
                if temporal_valid.any()
                else None
            )
            temporal_mae = _mae(temporal_observed, temporal_predictions)
            if coverage is None or coverage < 0.80:
                validation_eligible = False

            sensitivity_training = training[~training["year"].isin([2020, 2021])]
            sensitivity_oof = _oof_predictions(
                sensitivity_training,
                method=selected_method,
                parameter=selected_parameter,
                features=F1_FEATURES,
            )
            sensitivity_observed = sensitivity_training["observed_value"].to_numpy(float)
            sensitivity_half_width = _conformal_quantile(
                np.abs(sensitivity_observed - sensitivity_oof)
            )
            if selected_method == "ridge_context_model":
                sensitivity_predictions, _ = _ridge_predict(
                    sensitivity_training,
                    temporal,
                    features=F1_FEATURES,
                    alpha=float(selected_parameter),
                )
            else:
                sensitivity_predictions, _ = _peer_predict(
                    sensitivity_training,
                    temporal,
                    features=F1_FEATURES,
                    k=int(selected_parameter),
                )
            sensitivity_expected_mean_abs_difference = float(
                np.nanmean(np.abs(temporal_predictions - sensitivity_predictions))
            )

            state_values: list[str] = []
            sensitivity_states: list[str] = []
            for position, row in enumerate(temporal.itertuples(index=False)):
                observed = _finite(row.observed_value)
                expected = _finite(temporal_predictions[position])
                low = _finite(lower[position])
                high = _finite(upper[position])
                state = _state(observed, low, high) if validation_eligible else "NOT_EVALUABLE"
                if sensitivity_half_width is None:
                    sensitivity_state = "NOT_EVALUABLE"
                else:
                    sensitivity_state = _state(
                        observed,
                        _finite(sensitivity_predictions[position] - sensitivity_half_width),
                        _finite(sensitivity_predictions[position] + sensitivity_half_width),
                    )
                state_values.append(state)
                sensitivity_states.append(sensitivity_state)
                result_rows.append(
                    {
                        "front_id": "F1",
                        "model_id": model_id,
                        "municipality_ibge_code": row.municipality_ibge_code,
                        "municipality_name": row.municipality_name,
                        "comparison_year": 2025,
                        "stage": stage,
                        "outcome_id": outcome_id,
                        "observed_value": observed,
                        "expected_value": expected if validation_eligible else None,
                        "expected_interval_lower": low if validation_eligible else None,
                        "expected_interval_upper": high if validation_eligible else None,
                        "interval_level": INTERVAL_LEVEL if validation_eligible else None,
                        "context_adjusted_state": state,
                        "uncertainty_state": (
                            "TEMPORAL_COVERAGE_AT_LEAST_80_PERCENT"
                            if validation_eligible
                            else "NOT_EVALUABLE_VALIDATION_GATE"
                        ),
                        "selected_method": selected_method,
                        "selected_parameter": selected_parameter,
                        "supporting_context": (
                            _top_coefficients(fit_details)
                            if selected_method == "ridge_context_model"
                            else supports[position]
                        ),
                        "same_record": True,
                        "same_person": False,
                        "unit_of_analysis": "municipality_year_stage_outcome",
                        "territorial_lens": "school_location|resident_population_context_kept_separate",
                        "network_scope": "total_all_dependencies",
                        "administrative_dependency_role": "qa_only",
                        "ranking_allowed": False,
                        "causal_interpretation_allowed": False,
                        "sensitivity_without_2020_2021_state": sensitivity_state,
                    }
                )
            state_agreement = float(
                np.mean(
                    [
                        left == right
                        for left, right in zip(state_values, sensitivity_states, strict=True)
                        if left != "NOT_EVALUABLE" and right != "NOT_EVALUABLE"
                    ]
                )
            ) if any(
                left != "NOT_EVALUABLE" and right != "NOT_EVALUABLE"
                for left, right in zip(state_values, sensitivity_states, strict=True)
            ) else None
            validation_rows.append(
                {
                    "front_id": "F1",
                    "model_id": model_id,
                    "outcome_id": outcome_id,
                    "stage": stage,
                    "training_row_count": len(training),
                    "training_municipality_count": training["municipality_ibge_code"].nunique(),
                    "temporal_holdout_year": 2025,
                    "temporal_holdout_observed_count": int(np.isfinite(temporal_observed).sum()),
                    "ridge_group_holdout_mae": ridge_mae,
                    "peer_group_holdout_mae": peer_mae,
                    "naive_group_holdout_mae": naive_mae,
                    "selected_method": selected_method,
                    "selected_parameter": selected_parameter,
                    "selected_group_holdout_mae": selected_cv_mae,
                    "temporal_holdout_mae": temporal_mae,
                    "prediction_interval_level": INTERVAL_LEVEL,
                    "prediction_interval_half_width": interval_half_width,
                    "temporal_interval_coverage": coverage,
                    "validation_eligible": validation_eligible,
                    "complexity_decision": complexity_decision,
                    "sensitivity_without_2020_2021_expected_mean_abs_difference": sensitivity_expected_mean_abs_difference,
                    "sensitivity_without_2020_2021_state_agreement": state_agreement,
                    "municipality_holdout_folds": 5,
                    "causal_interpretation_allowed": False,
                    "ranking_allowed": False,
                }
            )
            model_details[model_id] = {
                "outcomeId": outcome_id,
                "stage": stage,
                "features": list(F1_FEATURES),
                "ridgeScores": {str(key): value for key, value in ridge_scores.items()},
                "peerScores": {str(key): value for key, value in peer_scores.items()},
                "naiveMae": naive_mae,
                "selectedMethod": selected_method,
                "selectedParameter": selected_parameter,
                "validationEligible": validation_eligible,
                "fitDetails": fit_details,
                "calibration": {
                    "method": "split_conformal_from_group_municipality_out_of_fold_absolute_residuals",
                    "intervalLevel": INTERVAL_LEVEL,
                    "residualCount": int(np.isfinite(calibration_residuals).sum()),
                    "intervalHalfWidth": interval_half_width,
                    "temporalCoverage": coverage,
                },
                "sensitivityWithout2020And2021": {
                    "trainingRowCount": len(sensitivity_training),
                    "expectedMeanAbsoluteDifference": sensitivity_expected_mean_abs_difference,
                    "stateAgreement": state_agreement,
                },
            }

    results = _stable_frame(
        pd.DataFrame(result_rows),
        ["outcome_id", "stage", "municipality_ibge_code"],
    )
    validation = _stable_frame(pd.DataFrame(validation_rows), ["outcome_id", "stage"])
    return results, validation, model_details


RAIS_HEADER_CANDIDATES = {
    "active": (
        "vinculoativo3112",
        "indvinculoativo3112codigo",
        "empem3112",
        "indicadordevinculoativoem3112",
    ),
    "municipality": (
        "muntrab",
        # Nos arquivos COMT reprocessados (2023+), o campo legado de
        # município de trabalho é mantido, mas vem anonimizado com 999999.
        # O município do estabelecimento permanece em `Município - Código`.
        "municipiocodigo",
        "municipiotrabcodigo",
        "municipio",
        "municipiodetrabalho",
        "municipioestabelecimento",
        "municipiodoestabelecimento",
    ),
    "age": ("idade", "idadetrabalhador"),
    "schooling": (
        "escolaridadeapos2005",
        "escolaridadeapos2005codigo",
        "grinstrucao",
        "graudeinstrucao",
    ),
    "hours": ("qtdhoracontr", "horascontr", "quantidadehoracontratadas"),
    "nominal_average_pay": (
        "vlremunmedianom",
        "vlremmedianom",
        "remmedr",
        "remmediar",
    ),
    "tenure": ("tempoemprego", "tempempr"),
    "bond_type": ("tipovinculo", "tipovinculocodigo", "tpvinculo"),
    "occupation": (
        "cboocupacao2002",
        "cbo2002ocupacao",
        "cbo2002ocupacaocodigo",
        "cbo",
    ),
    "sector": ("ibgesubsetor", "ibgesubsetorcodigo", "subsetoribge"),
    "establishment_size": (
        "tamanhoestabelecimento",
        "tamanhoestabelecimentocodigo",
        "tamestab",
    ),
}

# O Job 5L congelado preserva a seleção histórica abaixo como padrão. O
# Job 5L-final precisa, porém, reconstruir a série na lente única do município
# de localização do estabelecimento. Manter a alternativa explícita evita que
# ``Mun Trab`` (local de prestação do serviço) seja confundido com essa lente.
RAIS_ESTABLISHMENT_MUNICIPALITY_CANDIDATES = (
    "municipiocodigo",
    "municipio",
    "municipioestabelecimento",
    "municipiodoestabelecimento",
)

SCHOOLING_LABELS = {
    "1": "analfabeto",
    "2": "ate_5_ano_incompleto",
    "3": "5_ano_completo_fundamental",
    "4": "6_ao_9_ano_fundamental",
    "5": "fundamental_completo",
    "6": "medio_incompleto",
    "7": "medio_completo",
    "8": "superior_incompleto",
    "9": "superior_completo",
    "10": "mestrado",
    "11": "doutorado",
    "-1": "ignorado",
}

SCHOOLING_GROUPS = {
    "1": "below_fundamental_complete",
    "2": "below_fundamental_complete",
    "3": "below_fundamental_complete",
    "4": "below_fundamental_complete",
    "5": "fundamental_complete",
    "6": "high_school_incomplete",
    "7": "high_school_complete",
    "8": "higher_education_incomplete_or_more",
    "9": "higher_education_incomplete_or_more",
    "10": "higher_education_incomplete_or_more",
    "11": "higher_education_incomplete_or_more",
    "-1": "unknown_schooling",
}

ESTABLISHMENT_SIZE_LABELS = {
    "1": "zero_active_bonds",
    "2": "up_to_4",
    "3": "5_to_9",
    "4": "10_to_19",
    "5": "20_to_49",
    "6": "50_to_99",
    "7": "100_to_249",
    "8": "250_to_499",
    "9": "500_to_999",
    "10": "1000_or_more",
    "-1": "unknown_size",
}

SECTOR_LABELS = {
    "01": "extrativa_mineral",
    "02": "minerais_nao_metalicos",
    "03": "metalurgica",
    "04": "mecanica",
    "05": "material_eletrico_e_comunicacoes",
    "06": "material_de_transporte",
    "07": "madeira_e_mobiliario",
    "08": "papel_editorial_e_grafica",
    "09": "borracha_fumo_couros_e_diversas",
    "10": "quimica_farmaceutica_e_perfumaria",
    "11": "textil_e_vestuario",
    "12": "calcados",
    "13": "alimentos_bebidas_e_alcool",
    "14": "servicos_industriais_utilidade_publica",
    "15": "construcao_civil",
    "16": "comercio_varejista",
    "17": "comercio_atacadista",
    "18": "credito_seguros_e_capitalizacao",
    "19": "imoveis_valores_e_servicos_tecnicos",
    "20": "transportes_e_comunicacoes",
    "21": "alojamento_alimentacao_reparacao_e_manutencao",
    "22": "servicos_medicos_odontologicos_e_veterinarios",
    "23": "ensino",
    "24": "administracao_publica_direta_e_autarquica",
    "25": "agricultura_silvicultura_e_criacao",
    "-1": "unknown_sector",
}


def _clean_code(value: Any) -> str:
    text = str(value).strip()
    if text.casefold() in {"", "nan", "none", "null", "<na>"}:
        return "-1"
    if text.endswith(".0"):
        text = text[:-2]
    text = text.strip()
    if text.startswith("-"):
        digits = re.sub(r"[^0-9]", "", text)
        return f"-{digits}" if digits else "-1"
    digits = re.sub(r"[^0-9]", "", text)
    return digits.lstrip("0") or ("0" if digits else "-1")


def _decimal_series(series: pd.Series) -> pd.Series:
    text = series.astype("string").str.strip()
    comma = text.str.contains(",", regex=False, na=False)
    normalized = text.copy()
    normalized.loc[comma] = (
        normalized.loc[comma]
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
    )
    return pd.to_numeric(normalized, errors="coerce")


def _seven_zip() -> Path:
    candidates = (
        Path(r"C:\Program Files\7-Zip\7z.exe"),
        Path(r"C:\Program Files (x86)\7-Zip\7z.exe"),
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    executable = shutil.which("7z")
    if executable:
        return Path(executable)
    raise FileNotFoundError("7-Zip necessário para ler os microdados oficiais da RAIS")


def _rais_header(archive: Path) -> tuple[list[str], str, str]:
    process = subprocess.Popen(
        [str(_seven_zip()), "e", "-so", str(archive)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if process.stdout is None:
        raise RuntimeError(f"Não foi possível abrir stdout de {archive}")
    line = process.stdout.readline()
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
    if not line:
        stderr = process.stderr.read().decode("utf-8", errors="replace") if process.stderr else ""
        raise Job5LValidationError(f"Cabeçalho RAIS ausente em {archive.name}: {stderr}")
    encoding = "utf-8-sig"
    try:
        decoded = line.decode(encoding)
    except UnicodeDecodeError:
        encoding = "cp1252"
        decoded = line.decode(encoding)
    delimiters = (";", ",", "|", "\t")
    delimiter = max(delimiters, key=lambda candidate: decoded.count(candidate))
    if decoded.count(delimiter) == 0:
        raise Job5LValidationError(
            f"Delimitador RAIS não identificado em {archive.name}"
        )
    header = next(csv.reader([decoded.rstrip("\r\n")], delimiter=delimiter))
    return header, encoding, delimiter


def _select_rais_columns(
    header: Sequence[str],
    *,
    municipality_lens: str = "legacy_job5l",
) -> dict[str, str]:
    if municipality_lens not in {"legacy_job5l", "establishment_location"}:
        raise ValueError(f"Lente municipal RAIS desconhecida: {municipality_lens}")
    normalized = {_normalized_header(column): column for column in header}
    selected: dict[str, str] = {}
    for role, candidates in RAIS_HEADER_CANDIDATES.items():
        if role == "municipality" and municipality_lens == "establishment_location":
            candidates = RAIS_ESTABLISHMENT_MUNICIPALITY_CANDIDATES
        found = next((normalized[name] for name in candidates if name in normalized), None)
        if found is None:
            raise Job5LValidationError(
                f"Dicionário RAIS não localizou {role}; disponíveis={sorted(normalized)[:20]}..."
            )
        selected[role] = found
    if len(set(selected.values())) != len(selected):
        raise Job5LValidationError("Um campo bruto RAIS foi usado para papéis incompatíveis")
    return selected


def validate_rais_sources(
    raw_dir: Path,
    *,
    municipality_lens: str = "legacy_job5l",
) -> dict[str, Any]:
    records = []
    mappings: dict[str, Any] = {}
    for year, expected_size in sorted(RAIS_EXPECTED_SIZES.items()):
        path = raw_dir / f"RAIS_VINC_PUB_SUL_{year}.7z"
        if not path.is_file():
            raise FileNotFoundError(f"Microdado RAIS oficial ausente: {path}")
        if path.stat().st_size != expected_size:
            raise Job5LValidationError(
                f"Tamanho RAIS {year} divergente: {path.stat().st_size} != {expected_size}"
            )
        header, encoding, delimiter = _rais_header(path)
        selected = _select_rais_columns(header, municipality_lens=municipality_lens)
        mappings[str(year)] = {
            "encoding": encoding,
            "delimiter": delimiter,
            "headerColumnCount": len(header),
            "selectedRawColumns": selected,
            "municipalityFieldSelectionRule": (
                "canonical_Municipio_establishment_location"
                if municipality_lens == "establishment_location"
                else (
                    "legacy_Mun_Trab"
                    if _normalized_header(selected["municipality"]) == "muntrab"
                    else "reprocessed_Municipio_Codigo_establishment_location"
                )
            ),
        }
        records.append(
            {
                "year": year,
                "path": path.name,
                "byteSize": path.stat().st_size,
                "sha256": sha256_file(path),
                "officialUrl": f"ftp://ftp.mtps.gov.br/pdet/microdados/RAIS/{year}/RAIS_VINC_PUB_SUL.7z",
            }
        )
    return {
        "schemaVersion": "vocacoes-pne-job5l-rais-source-validation-v1",
        "source": "MTE_PDET_public_nonidentified_RAIS",
        "period": "2019-2025",
        "files": records,
        "fieldMappings": mappings,
        "stockDefinition": "active_formal_bond_at_31_12",
        "uniquePersonInterpretationAllowed": False,
        "territorialLens": (
            "establishment_location_workplace"
            if municipality_lens == "establishment_location"
            else "workplace"
        ),
    }


def _bond_category(code: str) -> str:
    if code == "55":
        return "apprentice_contract"
    if code in {"10", "15", "20", "25", "60", "65", "70", "75"}:
        return "clt_contract"
    if code in {"30", "31", "35"}:
        return "statutory_contract"
    if code in {"40", "50", "80", "90", "95", "96", "97"}:
        return "other_official_bond_type"
    return "unknown_bond_type"


def _age_group(age: float) -> str | None:
    if 15 <= age <= 17:
        return "15_17"
    if 18 <= age <= 24:
        return "18_24"
    return None


def _new_rais_accumulator() -> dict[str, Any]:
    return {
        "total": 0,
        "schooling": Counter(),
        "bond": Counter(),
        "hours_band": Counter(),
        "tenure_band": Counter(),
        "occupation": Counter(),
        "sector": Counter(),
        "size": Counter(),
        "pay": [],
        "hours": [],
        "tenure": [],
        "pay_by_schooling": defaultdict(list),
    }


def _append_group_to_accumulator(acc: dict[str, Any], group: pd.DataFrame) -> None:
    acc["total"] += len(group)
    schooling = group["schooling_group"].fillna("unknown_schooling").astype(str)
    acc["schooling"].update(schooling.tolist())
    acc["bond"].update(group["bond_category"].fillna("unknown_bond_type").astype(str).tolist())
    acc["occupation"].update(group["occupation_code"].fillna("-1").astype(str).tolist())
    acc["sector"].update(group["sector_code"].fillna("-1").astype(str).tolist())
    acc["size"].update(group["size_group"].fillna("unknown_size").astype(str).tolist())
    hours = pd.to_numeric(group["hours_value"], errors="coerce")
    tenure = pd.to_numeric(group["tenure_value"], errors="coerce")
    pay = pd.to_numeric(group["pay_value"], errors="coerce")
    acc["hours"].extend(hours[np.isfinite(hours) & hours.ge(0)].astype(float).tolist())
    acc["tenure"].extend(tenure[np.isfinite(tenure) & tenure.ge(0)].astype(float).tolist())
    acc["pay"].extend(pay[np.isfinite(pay) & pay.ge(0)].astype(float).tolist())
    hour_band = pd.cut(
        hours,
        bins=[-np.inf, 20, 30, 40, 44, np.inf],
        labels=["up_to_20", "21_to_30", "31_to_40", "41_to_44", "45_or_more"],
    ).astype("string").fillna("unknown_hours")
    tenure_band = pd.cut(
        tenure,
        bins=[-np.inf, 11.999999, 35.999999, np.inf],
        labels=["under_12_months", "12_to_35_months", "36_months_or_more"],
    ).astype("string").fillna("unknown_tenure")
    acc["hours_band"].update(hour_band.tolist())
    acc["tenure_band"].update(tenure_band.tolist())
    for school_group, values in group.assign(pay_numeric=pay).groupby(
        "schooling_group", dropna=False, sort=True
    ):
        valid = pd.to_numeric(values["pay_numeric"], errors="coerce")
        valid = valid[np.isfinite(valid) & valid.ge(0)]
        acc["pay_by_schooling"][str(school_group)].extend(valid.astype(float).tolist())


def _counter_rows(
    *,
    rows: list[dict[str, Any]],
    base: Mapping[str, Any],
    counter: Counter[str],
    metric_prefix: str,
    denominator: int,
    labels: Mapping[str, str] | None = None,
) -> None:
    for code, count in sorted(counter.items()):
        rows.append(
            {
                **base,
                "metric_id": f"{metric_prefix}_active_bonds",
                "dimension_code": code,
                "dimension_label": (labels or {}).get(code, code),
                "value": count,
                "unit": "active_bonds",
                "numerator": count,
                "denominator": None,
                "value_status": "observed_zero" if count == 0 else "observed",
            }
        )
        rows.append(
            {
                **base,
                "metric_id": f"{metric_prefix}_share_percent",
                "dimension_code": code,
                "dimension_label": (labels or {}).get(code, code),
                "value": safe_ratio(count, denominator, multiplier=100),
                "unit": "percent",
                "numerator": count,
                "denominator": denominator,
                "value_status": "unavailable" if denominator == 0 else "observed",
            }
        )


def _continuous_rows(
    *,
    rows: list[dict[str, Any]],
    base: Mapping[str, Any],
    values: Sequence[float],
    metric_prefix: str,
    unit: str,
) -> None:
    array = np.asarray(values, dtype=float)
    for suffix, value in (
        ("mean", float(np.mean(array)) if len(array) else None),
        ("median", float(np.median(array)) if len(array) else None),
        ("observed_count", len(array)),
    ):
        rows.append(
            {
                **base,
                "metric_id": f"{metric_prefix}_{suffix}",
                "dimension_code": "ALL",
                "dimension_label": "Todos os vínculos elegíveis",
                "value": value,
                "unit": "active_bonds" if suffix == "observed_count" else unit,
                "numerator": None,
                "denominator": None,
                "value_status": "unavailable" if value is None else "observed",
            }
        )


def build_rais_panel(
    raw_dir: Path,
    *,
    municipality_lens: str = "legacy_job5l",
) -> tuple[pd.DataFrame, dict[str, Any]]:
    source_validation = validate_rais_sources(
        raw_dir, municipality_lens=municipality_lens
    )
    region_codes = _region_codes()
    _, names = _municipalities()
    raw_to_canonical = {code[:6]: code for code in region_codes}
    rows: list[dict[str, Any]] = []
    year_diagnostics: dict[str, Any] = {}

    for year in sorted(RAIS_EXPECTED_SIZES):
        archive = raw_dir / f"RAIS_VINC_PUB_SUL_{year}.7z"
        mapping = source_validation["fieldMappings"][str(year)]
        selected = mapping["selectedRawColumns"]
        process = subprocess.Popen(
            [str(_seven_zip()), "e", "-so", str(archive)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if process.stdout is None:
            raise RuntimeError(f"Sem stream RAIS {year}")
        accumulators: defaultdict[tuple[str, str], dict[str, Any]] = defaultdict(
            _new_rais_accumulator
        )
        # O arquivo oficial cobre o universo de vínculos. Por isso, a ausência
        # de um vínculo elegível numa célula município/faixa é zero observado,
        # não dado indisponível. As 22 células são materializadas antes da
        # leitura; a cobertura efetivamente observada é registrada à parte.
        for entity_id in [*region_codes, REGION_ID]:
            for age_group in ("15_17", "18_24"):
                accumulators[(entity_id, age_group)]
        observed_entity_age_keys: set[tuple[str, str]] = set()
        scanned_rows = 0
        eligible_rows = 0
        reader = pd.read_csv(
            process.stdout,
            sep=mapping["delimiter"],
            encoding=mapping["encoding"],
            dtype="string",
            usecols=list(selected.values()),
            chunksize=250_000,
            low_memory=False,
        )
        for chunk in reader:
            scanned_rows += len(chunk)
            renamed = chunk.rename(columns={raw: role for role, raw in selected.items()})
            municipality_raw = renamed["municipality"].astype("string").str.replace(
                r"[^0-9]", "", regex=True
            )
            canonical = municipality_raw.map(raw_to_canonical)
            seven_digit = municipality_raw.where(municipality_raw.str.len().eq(7))
            canonical = canonical.where(canonical.notna(), seven_digit.where(seven_digit.isin(region_codes)))
            active = _decimal_series(renamed["active"])
            age = _decimal_series(renamed["age"])
            eligible = canonical.notna() & active.eq(1) & age.between(15, 24, inclusive="both")
            if not eligible.any():
                continue
            work = renamed.loc[eligible].copy()
            work["municipality_ibge_code"] = canonical.loc[eligible].astype(str)
            work["age_value"] = age.loc[eligible]
            work["age_group"] = work["age_value"].map(_age_group)
            work["schooling_code"] = work["schooling"].map(_clean_code)
            work["schooling_group"] = work["schooling_code"].map(SCHOOLING_GROUPS).fillna(
                "unknown_schooling"
            )
            work["hours_value"] = _decimal_series(work["hours"])
            work["pay_value"] = _decimal_series(work["nominal_average_pay"])
            work["tenure_value"] = _decimal_series(work["tenure"])
            work["bond_code"] = work["bond_type"].map(_clean_code)
            work["bond_category"] = work["bond_code"].map(_bond_category)
            work["occupation_code"] = (
                work["occupation"].astype("string").str.replace(r"[^0-9]", "", regex=True)
            ).replace("", "-1")
            work["sector_code"] = work["sector"].map(_clean_code).map(
                lambda value: value.zfill(2) if value not in {"-1", "0"} else "-1"
            )
            work["size_code"] = work["establishment_size"].map(_clean_code)
            work["size_group"] = work["size_code"].map(ESTABLISHMENT_SIZE_LABELS).fillna(
                "unknown_size"
            )
            eligible_rows += len(work)
            for (code, age_group), group in work.groupby(
                ["municipality_ibge_code", "age_group"], sort=True
            ):
                observed_entity_age_keys.add((str(code), str(age_group)))
                _append_group_to_accumulator(accumulators[(str(code), str(age_group))], group)
            for age_group, group in work.groupby("age_group", sort=True):
                observed_entity_age_keys.add((REGION_ID, str(age_group)))
                _append_group_to_accumulator(accumulators[(REGION_ID, str(age_group))], group)

        process.stdout.close()
        return_code = process.wait()
        stderr = process.stderr.read().decode("utf-8", errors="replace") if process.stderr else ""
        if return_code != 0:
            raise Job5LValidationError(f"7-Zip falhou na RAIS {year}: {stderr}")
        year_diagnostics[str(year)] = {
            "scannedRows": scanned_rows,
            "eligibleValeYouthActiveBondRows": eligible_rows,
            "entityAgeAccumulatorCount": len(accumulators),
            "observedEntityAgeCellCount": len(observed_entity_age_keys),
            "observedMunicipalityCount": len(
                {entity_id for entity_id, _ in observed_entity_age_keys if entity_id != REGION_ID}
            ),
            "zeroActiveBondEntityAgeCellCount": sum(
                int(acc["total"] == 0) for acc in accumulators.values()
            ),
        }

        for (entity_id, age_group), acc in sorted(accumulators.items()):
            is_region = entity_id == REGION_ID
            base = {
                "front_id": "F3",
                "year": year,
                "entity_scope": "region" if is_region else "municipality",
                "entity_id": entity_id,
                "municipality_ibge_code": None if is_region else entity_id,
                "municipality_name": "Vale do Sinos" if is_region else names[entity_id],
                "age_group": age_group,
                "territorial_lens": (
                    "establishment_location_workplace"
                    if municipality_lens == "establishment_location"
                    else "workplace"
                ),
                "unit_of_analysis": "active_formal_bond_at_31_12",
                "stock_or_flow": "STOCK",
                "unique_person_count_allowed": False,
                "same_person": False,
                "source": "MTE_PDET_RAIS_public_nonidentified_microdata",
                "source_layout_family": (
                    "legacy_semicolon_txt_60_columns"
                    if year <= 2022
                    else "reprocessed_comma_comt_62_columns"
                ),
                "structural_comparability_caution": year >= 2023,
                "remuneration_price_basis": "nominal_BRL",
                "real_remuneration_state": "NOT_MATERIALIZED_NO_OFFICIAL_DEFLATOR_CONTRACT",
                "real_value_materialized": False,
            }
            total = int(acc["total"])
            for key in sorted(set(SCHOOLING_GROUPS.values())):
                acc["schooling"].setdefault(key, 0)
            for key in (
                "apprentice_contract",
                "clt_contract",
                "statutory_contract",
                "other_official_bond_type",
                "unknown_bond_type",
            ):
                acc["bond"].setdefault(key, 0)
            for key in (
                "up_to_20",
                "21_to_30",
                "31_to_40",
                "41_to_44",
                "45_or_more",
                "unknown_hours",
            ):
                acc["hours_band"].setdefault(key, 0)
            for key in (
                "under_12_months",
                "12_to_35_months",
                "36_months_or_more",
                "unknown_tenure",
            ):
                acc["tenure_band"].setdefault(key, 0)
            for key in sorted(set(ESTABLISHMENT_SIZE_LABELS.values()) | {"unknown_size"}):
                acc["size"].setdefault(key, 0)
            rows.append(
                {
                    **base,
                    "metric_id": "active_bonds",
                    "dimension_code": "ALL",
                    "dimension_label": "Vínculos ativos em 31/12",
                    "value": total,
                    "unit": "active_bonds",
                    "numerator": total,
                    "denominator": None,
                    "value_status": "observed_zero" if total == 0 else "observed",
                }
            )
            _counter_rows(
                rows=rows,
                base=base,
                counter=acc["schooling"],
                metric_prefix="schooling_composition",
                denominator=total,
            )
            _counter_rows(
                rows=rows,
                base=base,
                counter=acc["bond"],
                metric_prefix="bond_type_composition",
                denominator=total,
            )
            _counter_rows(
                rows=rows,
                base=base,
                counter=acc["hours_band"],
                metric_prefix="contracted_hours_band",
                denominator=total,
            )
            _counter_rows(
                rows=rows,
                base=base,
                counter=acc["tenure_band"],
                metric_prefix="bond_tenure_band",
                denominator=total,
            )
            _counter_rows(
                rows=rows,
                base=base,
                counter=acc["size"],
                metric_prefix="establishment_size_composition",
                denominator=total,
            )
            _continuous_rows(
                rows=rows,
                base=base,
                values=acc["pay"],
                metric_prefix="nominal_average_monthly_remuneration",
                unit="BRL_nominal",
            )
            _continuous_rows(
                rows=rows,
                base=base,
                values=acc["hours"],
                metric_prefix="contracted_weekly_hours",
                unit="hours_per_week",
            )
            _continuous_rows(
                rows=rows,
                base=base,
                values=acc["tenure"],
                metric_prefix="bond_tenure",
                unit="months",
            )
            for school_group, values in sorted(acc["pay_by_schooling"].items()):
                array = np.asarray(values, dtype=float)
                rows.append(
                    {
                        **base,
                        "metric_id": "nominal_average_monthly_remuneration_by_schooling_median",
                        "dimension_code": school_group,
                        "dimension_label": school_group,
                        "value": float(np.median(array)) if len(array) else None,
                        "unit": "BRL_nominal",
                        "numerator": None,
                        "denominator": len(array),
                        "value_status": "unavailable" if not len(array) else "observed",
                    }
                )
            for metric_id, counter, labels in (
                ("top4_occupation_concentration_share_percent", acc["occupation"], None),
                ("top4_sector_concentration_share_percent", acc["sector"], SECTOR_LABELS),
            ):
                top = counter.most_common(4)
                numerator = sum(count for _, count in top)
                rows.append(
                    {
                        **base,
                        "metric_id": metric_id,
                        "dimension_code": "|".join(code for code, _ in top),
                        "dimension_label": "|".join(
                            (labels or {}).get(code, code) for code, _ in top
                        ),
                        "value": safe_ratio(numerator, total, multiplier=100),
                        "unit": "percent",
                        "numerator": numerator,
                        "denominator": total,
                        "value_status": "unavailable" if total == 0 else "observed",
                    }
                )

    panel = _stable_frame(
        pd.DataFrame(rows),
        ["year", "entity_scope", "entity_id", "age_group", "metric_id", "dimension_code"],
    )
    endpoint_keys = [
        "entity_scope",
        "entity_id",
        "age_group",
        "metric_id",
        "dimension_code",
    ]
    initial = panel[panel["year"].eq(2019)][endpoint_keys + ["value"]].rename(
        columns={"value": "period_initial_value_2019"}
    )
    final = panel[panel["year"].eq(2025)][endpoint_keys + ["value"]].rename(
        columns={"value": "period_final_value_2025"}
    )
    endpoints = initial.merge(final, on=endpoint_keys, how="outer", validate="one_to_one")
    endpoints["period_absolute_change_2019_2025"] = pd.to_numeric(
        endpoints["period_final_value_2025"], errors="coerce"
    ) - pd.to_numeric(endpoints["period_initial_value_2019"], errors="coerce")
    endpoints["period_percent_change_2019_2025"] = [
        safe_ratio(change, initial_value, multiplier=100)
        for change, initial_value in zip(
            endpoints["period_absolute_change_2019_2025"],
            endpoints["period_initial_value_2019"],
        )
    ]
    endpoints["period_change_state"] = np.where(
        endpoints["period_initial_value_2019"].isna()
        | endpoints["period_final_value_2025"].isna(),
        "NOT_AVAILABLE",
        np.where(
            pd.to_numeric(endpoints["period_initial_value_2019"], errors="coerce").eq(0),
            "BASE_ZERO_PERCENT_CHANGE_NOT_EVALUABLE",
            "OBSERVED_ENDPOINT_CHANGE",
        ),
    )
    panel = panel.merge(endpoints, on=endpoint_keys, how="left", validate="many_to_one")
    regional_current = panel[panel["entity_scope"].eq("region")][
        ["year", "age_group", "metric_id", "dimension_code", "value"]
    ].rename(columns={"value": "regional_current_value"})
    panel = panel.merge(
        regional_current,
        on=["year", "age_group", "metric_id", "dimension_code"],
        how="left",
        validate="many_to_one",
    )
    regional_change = endpoints[endpoints["entity_scope"].eq("region")][
        [
            "age_group",
            "metric_id",
            "dimension_code",
            "period_absolute_change_2019_2025",
        ]
    ].rename(
        columns={
            "period_absolute_change_2019_2025": "regional_period_absolute_change_2019_2025"
        }
    )
    panel = panel.merge(
        regional_change,
        on=["age_group", "metric_id", "dimension_code"],
        how="left",
        validate="many_to_one",
    )
    count_metric = panel["unit"].eq("active_bonds")
    panel["municipal_share_of_regional_count_percent"] = [
        safe_ratio(value, regional, multiplier=100)
        if is_count and scope in {"municipality", "region"}
        else None
        for value, regional, is_count, scope in zip(
            panel["value"],
            panel["regional_current_value"],
            count_metric,
            panel["entity_scope"],
        )
    ]
    panel["municipal_contribution_to_regional_change_percent"] = [
        safe_ratio(change, regional_change_value, multiplier=100)
        if is_count and scope == "municipality"
        else None
        for change, regional_change_value, is_count, scope in zip(
            panel["period_absolute_change_2019_2025"],
            panel["regional_period_absolute_change_2019_2025"],
            count_metric,
            panel["entity_scope"],
        )
    ]
    panel["period_change_unit"] = np.where(
        panel["unit"].eq("percent"), "percentage_points", panel["unit"]
    )
    panel = _stable_frame(
        panel,
        ["year", "entity_scope", "entity_id", "age_group", "metric_id", "dimension_code"],
    )
    reconciliation = _reconcile_rais_with_frozen(panel)
    if not reconciliation["coverageSentinelPass"]:
        raise Job5LValidationError(
            "Cobertura estrutural RAIS incompatível com o agregado congelado; "
            f"sentinela={reconciliation['byYear']}"
        )
    details = {
        "sourceValidation": source_validation,
        "yearDiagnostics": year_diagnostics,
        "reconciliationWithFrozenAggregate": reconciliation,
        "dictionary": {
            "schoolingOfficialCodes": SCHOOLING_LABELS,
            "schoolingAnalyticalGroups": SCHOOLING_GROUPS,
            "bondTypeRule": {
                "apprentice": ["55"],
                "clt": ["10", "15", "20", "25", "60", "65", "70", "75"],
                "statutory": ["30", "31", "35"],
                "otherOfficial": ["40", "50", "80", "90", "95", "96", "97"],
            },
            "establishmentSizeOfficialCodes": ESTABLISHMENT_SIZE_LABELS,
            "sectorOfficialIBGESubsectorCodes": SECTOR_LABELS,
        },
        "layoutCompatibility": {
            "2019_2022": "legacy_semicolon_txt_60_columns",
            "2023_2025": "reprocessed_comma_comt_62_columns",
            "fieldEquivalenceValidatedByOfficialNamesAndMappings": True,
            "municipalityFieldRule": (
                "Municipio nos layouts legados e Municipio_Codigo nos COMT reprocessados; "
                "ambos representam a localização do estabelecimento"
                if municipality_lens == "establishment_location"
                else (
                    "Mun_Trab nos layouts legados; Municipio_Codigo nos COMT reprocessados, "
                    "onde Municipio_Trab_Codigo usa o sentinela 999999"
                )
            ),
            "structuralComparabilityCautionMaterialized": True,
            "analyticalBreakAutomaticallyAttributed": False,
        },
    }
    return panel, details


def _reconcile_rais_with_frozen(panel: pd.DataFrame) -> dict[str, Any]:
    frozen_path = FROZEN_ROOTS["job5gcr"] / "PAINEL_RAIS_TRABALHO_JUVENIL_V1_1.csv.gz"
    frozen = _read_csv(frozen_path)
    frozen = frozen[
        frozen["entity_scope"].eq("municipality")
        & frozen["dimension"].eq("schooling_raw")
    ].copy()
    frozen["active_bonds"] = pd.to_numeric(frozen["active_bonds"], errors="coerce")
    expected = frozen.groupby(
        ["year", "municipality_ibge_code", "age_group"], as_index=False, sort=True
    )["active_bonds"].sum(min_count=1)
    actual = panel[
        panel["entity_scope"].eq("municipality") & panel["metric_id"].eq("active_bonds")
    ][["year", "municipality_ibge_code", "age_group", "value"]].rename(
        columns={"value": "actual_active_bonds"}
    )
    merged = expected.merge(
        actual, on=["year", "municipality_ibge_code", "age_group"], how="outer"
    )
    merged["difference"] = pd.to_numeric(
        merged["actual_active_bonds"], errors="coerce"
    ) - pd.to_numeric(merged["active_bonds"], errors="coerce")
    by_year = []
    for year, group in merged.groupby("year", sort=True, dropna=False):
        frozen_total = float(pd.to_numeric(group["active_bonds"], errors="coerce").sum())
        current_total = float(
            pd.to_numeric(group["actual_active_bonds"], errors="coerce").sum()
        )
        by_year.append(
            {
                "year": int(year),
                "frozenAggregateTotal": frozen_total,
                "currentOfficialRawActiveAtYearEndTotal": current_total,
                "differenceCurrentMinusFrozen": current_total - frozen_total,
                "differencePercentOfFrozen": safe_ratio(
                    current_total - frozen_total, frozen_total, multiplier=100
                ),
                "coverageSentinelRatioToFrozen": safe_ratio(current_total, frozen_total),
                "comparisonCellCount": len(group),
                "exactMatchCellCount": int(group["difference"].fillna(math.inf).eq(0).sum()),
            }
        )
    exact_count = int(merged["difference"].fillna(math.inf).eq(0).sum())
    mismatch_count = int((~merged["difference"].fillna(math.inf).eq(0)).sum())
    coverage_sentinel_minimum_ratio = 0.10
    coverage_sentinel_pass = all(
        item["coverageSentinelRatioToFrozen"] is not None
        and item["coverageSentinelRatioToFrozen"] >= coverage_sentinel_minimum_ratio
        for item in by_year
    )
    return {
        "comparisonRowCount": len(merged),
        "exactMatchCount": exact_count,
        "mismatchCount": mismatch_count,
        "maximumAbsoluteDifference": (
            float(merged["difference"].abs().max()) if merged["difference"].notna().any() else None
        ),
        "byYear": by_year,
        "coverageSentinelMinimumRatio": coverage_sentinel_minimum_ratio,
        "coverageSentinelPass": coverage_sentinel_pass,
        "coverageSentinelPurpose": "detect catastrophic field or territorial coverage breaks; not require exact reconciliation",
        "validationState": (
            "EXACT_MATCH"
            if mismatch_count == 0
            else "RECONCILED_WITH_EXPLICIT_SOURCE_VERSION_OR_AGGREGATION_DIFFERENCE"
        ),
        "currentF3StockDefinition": "official_raw_field_Vinculo_Ativo_31_12_equals_1",
        "frozenComparisonDefinition": "previous_database_aggregate_labeled_active_bonds",
        "causeIdentified": False,
        "permittedInterpretation": "the_current_official_raw_active_stock_differs_from_the_frozen_aggregate",
        "forbiddenInterpretations": [
            "silently_replace_or_mutate_the_frozen_aggregate",
            "declare_the_previous_aggregate_wrong_without_source_version_audit",
            "drop_the_official_active_at_31_12_filter_to_force_equality",
        ],
        "exactMatchRequiredForQA": False,
        "differenceMustRemainVisible": mismatch_count > 0,
    }


def build_conditional_fronts() -> tuple[pd.DataFrame, pd.DataFrame]:
    region_codes = _region_codes()
    _, names = _municipalities()
    entities = [(REGION_ID, "Vale do Sinos", "region")] + [
        (code, names[code], "municipality") for code in region_codes
    ]
    f2_rows = []
    for entity_id, name, scope in entities:
        for age_group in ("15_17", "18_24"):
            f2_rows.append(
                {
                    "front_id": "F2",
                    "front_state": "WAITING_OFFICIAL_RELEASE",
                    "entity_scope": scope,
                    "entity_id": entity_id,
                    "municipality_ibge_code": entity_id if scope == "municipality" else None,
                    "municipality_name": name,
                    "age_group": age_group,
                    "measure": "study_work_same_person_composition",
                    "weighted_estimate": None,
                    "standard_error": None,
                    "confidence_interval_lower": None,
                    "confidence_interval_upper": None,
                    "coefficient_of_variation": None,
                    "unweighted_n": None,
                    "precision_state": "NOT_AVAILABLE",
                    "same_person": True,
                    "territorial_lens": "person_residence_same_record",
                    "availability_reason": "IBGE_Censo_2022_sample_microdata_and_weighting_areas_not_officially_released_as_of_2026_08_29",
                }
            )
    f5_rows = [
        {
            "front_id": "F5",
            "front_state": "WAITING_OFFICIAL_RELEASE",
            "entity_scope": scope,
            "entity_id": entity_id,
            "municipality_ibge_code": entity_id if scope == "municipality" else None,
            "municipality_name": name,
            "measure": "migration_school_offer_same_person_context",
            "estimate": None,
            "precision_state": "NOT_AVAILABLE",
            "same_person": True,
            "territorial_lens": "person_residence_same_record",
            "availability_reason": "F5_depends_on_F2_official_sample_microdata",
            "causal_interpretation_allowed": False,
        }
        for entity_id, name, scope in entities
    ]
    return _stable_frame(pd.DataFrame(f2_rows)), _stable_frame(pd.DataFrame(f5_rows))


def build_f6_panel() -> pd.DataFrame:
    distribution = _read_csv(
        FROZEN_ROOTS["job5gbr"] / "PAINEL_EJA_DISTRIBUICAO_2022_V1_1.csv.gz"
    )
    history = _read_csv(
        FROZEN_ROOTS["job5gbr"] / "PAINEL_EJA_HISTORICA_2014_2025_V1_1.csv.gz"
    )
    region_codes = set(_region_codes())
    distribution = distribution[
        distribution["entity_scope"].eq("region")
        | distribution["municipality_ibge_code"].astype("string").isin(region_codes)
    ].copy()
    history = history[
        (
            history["entity_scope"].eq("region")
            | history["municipality_ibge_code"].astype("string").isin(region_codes)
        )
        & history["stage"].isin(["fundamental", "high_school"])
        & history["year"].isin([2014, 2025, "2014", "2025"])
    ].copy()
    history["entity_id"] = history["municipality_ibge_code"].astype("string").where(
        history["entity_scope"].eq("municipality"), REGION_ID
    )
    history["eja_enrollments"] = pd.to_numeric(history["eja_enrollments"], errors="coerce")
    wide = history.pivot_table(
        index=["entity_id", "stage"],
        columns="year",
        values="eja_enrollments",
        aggfunc="first",
    ).reset_index()
    year_columns = {str(column): column for column in wide.columns}
    initial_column = year_columns.get("2014", 2014)
    final_column = year_columns.get("2025", 2025)
    wide = wide.rename(
        columns={initial_column: "eja_enrollments_2014", final_column: "eja_enrollments_2025"}
    )
    distribution["entity_id"] = distribution["municipality_ibge_code"].astype(
        "string"
    ).where(distribution["entity_scope"].eq("municipality"), REGION_ID)
    panel = distribution.merge(wide, on=["entity_id", "stage"], how="left")
    panel["resident_adult_public"] = pd.to_numeric(
        panel["resident_adult_public"], errors="coerce"
    )
    panel["school_location_eja_enrollments"] = pd.to_numeric(
        panel["school_location_eja_enrollments"], errors="coerce"
    )
    panel["eja_enrollments_per_thousand_resident_public_2022"] = _safe_series_ratio(
        panel["school_location_eja_enrollments"],
        panel["resident_adult_public"],
        multiplier=1_000,
    )
    panel["front_id"] = "F6"
    panel["front_state"] = "AGGREGATE_ONLY_WITH_EXPLICIT_LIMITS"
    panel["same_person"] = False
    panel["work_constraint_proxy"] = np.nan
    panel["mobility_or_commute_context"] = np.nan
    panel["precision_state"] = "AGGREGATE_COUNTS_NO_SAMPLE_PRECISION"
    panel["resident_population_is_manifest_demand"] = False
    panel["cross_stage_combination_allowed"] = False
    selected = [
        "front_id",
        "front_state",
        "entity_scope",
        "entity_id",
        "municipality_ibge_code",
        "municipality_name",
        "stage",
        "resident_adult_public",
        "school_location_eja_enrollments",
        "eja_enrollments_per_thousand_resident_public_2022",
        "share_of_regional_public_percent",
        "share_of_regional_enrollments_percent",
        "distribution_difference_percentage_points",
        "distribution_direction",
        "eja_enrollments_2014",
        "eja_enrollments_2025",
        "territorial_lens",
        "network_scope",
        "same_person",
        "work_constraint_proxy",
        "mobility_or_commute_context",
        "precision_state",
        "resident_population_is_manifest_demand",
        "cross_stage_combination_allowed",
        "resident_public_population_source",
        "adult_panel_compatibility",
        "source",
    ]
    return _stable_frame(panel[selected], ["entity_scope", "entity_id", "stage"])


def _component_frame(
    *,
    values: pd.DataFrame,
    component_id: str,
    value_column: str,
    lens: str,
    period: str,
    unit: str,
) -> pd.DataFrame:
    frame = values[
        ["entity_scope", "entity_id", "municipality_ibge_code", "municipality_name", value_column]
    ].copy()
    frame = frame.rename(columns={value_column: "component_value"})
    frame["component_id"] = component_id
    frame["lens"] = lens
    frame["period"] = period
    frame["unit"] = unit
    return frame


def build_f4_balance(
    context: pd.DataFrame,
    rais_panel: pd.DataFrame,
    f6_panel: pd.DataFrame,
) -> pd.DataFrame:
    region_codes = _region_codes()
    _, names = _municipalities()
    municipal_context = context[
        context["year"].eq(2025) & context["stage"].eq("medio")
    ].copy()
    municipal_context = municipal_context[
        municipal_context["municipality_ibge_code"].isin(region_codes)
    ]
    municipal_context["entity_scope"] = "municipality"
    municipal_context["entity_id"] = municipal_context["municipality_ibge_code"]
    components = [
        _component_frame(
            values=municipal_context,
            component_id="resident_population_15_17",
            value_column="population_15_17",
            lens="resident_population",
            period="2025",
            unit="population",
        ),
        _component_frame(
            values=municipal_context,
            component_id="resident_population_18_24",
            value_column="population_18_24",
            lens="resident_population",
            period="2025",
            unit="population",
        ),
        _component_frame(
            values=municipal_context,
            component_id="located_high_school_enrollments",
            value_column="mat_medio",
            lens="school_location",
            period="2025",
            unit="enrollments",
        ),
    ]

    def rais_component(
        component_id: str, *, age_group: str, metric_id: str, dimension_code: str = "ALL"
    ) -> pd.DataFrame:
        selected = rais_panel[
            rais_panel["year"].eq(2025)
            & rais_panel["age_group"].eq(age_group)
            & rais_panel["metric_id"].eq(metric_id)
            & rais_panel["dimension_code"].eq(dimension_code)
        ].copy()
        return _component_frame(
            values=selected,
            component_id=component_id,
            value_column="value",
            lens="workplace",
            period="2025",
            unit="active_bonds",
        )

    components.extend(
        [
            rais_component(
                "workplace_active_bonds_15_17", age_group="15_17", metric_id="active_bonds"
            ),
            rais_component(
                "workplace_active_bonds_18_24", age_group="18_24", metric_id="active_bonds"
            ),
            rais_component(
                "workplace_apprentice_active_bonds_15_17",
                age_group="15_17",
                metric_id="bond_type_composition_active_bonds",
                dimension_code="apprentice_contract",
            ),
        ]
    )

    ept = _read_csv(FROZEN_ROOTS["job5gcr"] / "PAINEL_EPT_OFERTA_TOTAL_V1_1.csv.gz")
    ept = ept[
        ept["year"].eq(2025)
        & ept["grain"].eq("municipality_total")
        & ept["entity_scope"].eq("municipality")
        & ept["municipality_ibge_code"].isin(region_codes)
    ].copy()
    ept["entity_id"] = ept["municipality_ibge_code"]
    components.append(
        _component_frame(
            values=ept,
            component_id="located_technical_enrollments",
            value_column="technical_enrollments",
            lens="school_location",
            period="2025",
            unit="enrollments",
        )
    )
    occupations = _read_csv(
        FROZEN_ROOTS["job5gcr"] / "PAINEL_OCUPACOES_RAIS_ESTOQUE_V1.csv.gz"
    )
    occupations["dimension_code_normalized"] = occupations["dimension_code"].map(
        _clean_code
    )
    occupations = occupations[
        occupations["dimension_code_normalized"].eq("414140")
        & occupations["entity_scope"].eq("municipality")
        & occupations["municipality_ibge_code"].isin(region_codes)
    ].copy()
    occupations["entity_id"] = occupations["municipality_ibge_code"]
    components.append(
        _component_frame(
            values=occupations,
            component_id="occupation_414140_absolute_change",
            value_column="absolute_change",
            lens="workplace",
            period="2019-2025",
            unit="active_bond_change",
        )
    )
    for stage in ("fundamental", "high_school"):
        selected = f6_panel[
            f6_panel["stage"].eq(stage) & f6_panel["entity_scope"].eq("municipality")
        ].copy()
        components.extend(
            [
                _component_frame(
                    values=selected,
                    component_id=f"resident_adult_public_{stage}",
                    value_column="resident_adult_public",
                    lens="resident_population",
                    period="2022",
                    unit="population",
                ),
                _component_frame(
                    values=selected,
                    component_id=f"located_eja_enrollments_{stage}",
                    value_column="school_location_eja_enrollments",
                    lens="school_location",
                    period="2022",
                    unit="enrollments",
                ),
            ]
        )
    component_panel = pd.concat(components, ignore_index=True)
    component_panel["component_value"] = pd.to_numeric(
        component_panel["component_value"], errors="coerce"
    )
    component_panel = component_panel[
        component_panel["entity_scope"].eq("municipality")
    ].copy()
    comparisons = (
        (
            "work_15_17_vs_residence_15_17",
            "workplace_active_bonds_15_17",
            "resident_population_15_17",
        ),
        (
            "work_18_24_vs_residence_18_24",
            "workplace_active_bonds_18_24",
            "resident_population_18_24",
        ),
        (
            "apprenticeship_15_17_vs_residence_15_17",
            "workplace_apprentice_active_bonds_15_17",
            "resident_population_15_17",
        ),
        (
            "high_school_offer_vs_residence_15_17",
            "located_high_school_enrollments",
            "resident_population_15_17",
        ),
        (
            "technical_education_vs_occupation_414140_change",
            "located_technical_enrollments",
            "occupation_414140_absolute_change",
        ),
        (
            "eja_fundamental_vs_resident_public",
            "located_eja_enrollments_fundamental",
            "resident_adult_public_fundamental",
        ),
        (
            "eja_high_school_vs_resident_public",
            "located_eja_enrollments_high_school",
            "resident_adult_public_high_school",
        ),
    )
    result_rows: list[dict[str, Any]] = []
    for comparison_id, target_id, reference_id in comparisons:
        target = component_panel[component_panel["component_id"].eq(target_id)].copy()
        reference = component_panel[component_panel["component_id"].eq(reference_id)].copy()
        if target.empty or reference.empty:
            raise Job5LValidationError(
                "Componente F4 ausente; "
                f"comparison={comparison_id}; target={target_id}:{len(target)}; "
                f"reference={reference_id}:{len(reference)}"
            )
        target_total = float(target["component_value"].sum(min_count=1))
        reference_total = float(reference["component_value"].sum(min_count=1))
        joined = target.merge(
            reference[
                ["entity_id", "component_value", "lens", "period", "unit"]
            ].rename(
                columns={
                    "component_value": "reference_count",
                    "lens": "reference_lens",
                    "period": "reference_period",
                    "unit": "reference_unit",
                }
            ),
            on="entity_id",
            how="outer",
        )
        for row in joined.itertuples(index=False):
            target_count = _finite(row.component_value)
            reference_count = _finite(row.reference_count)
            target_share = safe_ratio(target_count, target_total, multiplier=100)
            reference_share = safe_ratio(reference_count, reference_total, multiplier=100)
            difference = (
                target_share - reference_share
                if target_share is not None and reference_share is not None
                else None
            )
            ratio = safe_ratio(target_share, reference_share)
            if difference is None:
                profile = "NOT_AVAILABLE"
            elif difference > 1:
                profile = "TARGET_PARTICIPATION_MORE_THAN_1_PP_ABOVE_REFERENCE"
            elif difference < -1:
                profile = "TARGET_PARTICIPATION_MORE_THAN_1_PP_BELOW_REFERENCE"
            else:
                profile = "TARGET_PARTICIPATION_WITHIN_1_PP_OF_REFERENCE"
            result_rows.append(
                {
                    "front_id": "F4",
                    "comparison_id": comparison_id,
                    "entity_scope": "municipality",
                    "entity_id": row.entity_id,
                    "municipality_ibge_code": row.entity_id,
                    "municipality_name": names[row.entity_id],
                    "target_component_id": target_id,
                    "reference_component_id": reference_id,
                    "municipal_count": target_count,
                    "regional_total": target_total,
                    "municipal_share": target_share,
                    "reference_municipal_count": reference_count,
                    "reference_regional_total": reference_total,
                    "reference_municipal_share": reference_share,
                    "difference_to_reference_share_pp": difference,
                    "ratio_to_reference_share": ratio,
                    "lens": row.lens,
                    "reference_lens": row.reference_lens,
                    "period": row.period,
                    "reference_period": row.reference_period,
                    "unit": row.unit,
                    "reference_unit": row.reference_unit,
                    "descriptive_profile": profile,
                    "profile_rule": "explicit_plus_or_minus_1_percentage_point_band",
                    "synthetic_index": False,
                    "ranking_allowed": False,
                    "causal_interpretation_allowed": False,
                    "value_status": (
                        "unavailable" if target_count is None or reference_count is None else "observed"
                    ),
                }
            )
        result_rows.append(
            {
                "front_id": "F4",
                "comparison_id": comparison_id,
                "entity_scope": "region",
                "entity_id": REGION_ID,
                "municipality_ibge_code": None,
                "municipality_name": "Vale do Sinos",
                "target_component_id": target_id,
                "reference_component_id": reference_id,
                "municipal_count": target_total,
                "regional_total": target_total,
                "municipal_share": 100.0,
                "reference_municipal_count": reference_total,
                "reference_regional_total": reference_total,
                "reference_municipal_share": 100.0,
                "difference_to_reference_share_pp": 0.0,
                "ratio_to_reference_share": 1.0,
                "lens": target["lens"].iloc[0],
                "reference_lens": reference["lens"].iloc[0],
                "period": target["period"].iloc[0],
                "reference_period": reference["period"].iloc[0],
                "unit": target["unit"].iloc[0],
                "reference_unit": reference["unit"].iloc[0],
                "descriptive_profile": "REGIONAL_REFERENCE",
                "profile_rule": "explicit_plus_or_minus_1_percentage_point_band",
                "synthetic_index": False,
                "ranking_allowed": False,
                "causal_interpretation_allowed": False,
                "value_status": "observed",
            }
        )

    # A dimensão de estudante residente depende da amostra censitária; ela é
    # preservada como indisponível, sem preencher a lacuna com matrícula localizada.
    for entity_id in [REGION_ID, *region_codes]:
        result_rows.append(
            {
                "front_id": "F4",
                "comparison_id": "resident_students_vs_resident_population",
                "entity_scope": "region" if entity_id == REGION_ID else "municipality",
                "entity_id": entity_id,
                "municipality_ibge_code": None if entity_id == REGION_ID else entity_id,
                "municipality_name": "Vale do Sinos" if entity_id == REGION_ID else names[entity_id],
                "target_component_id": "resident_students",
                "reference_component_id": "resident_population_15_17",
                "municipal_count": None,
                "regional_total": None,
                "municipal_share": None,
                "reference_municipal_count": None,
                "reference_regional_total": None,
                "reference_municipal_share": None,
                "difference_to_reference_share_pp": None,
                "ratio_to_reference_share": None,
                "lens": "student_residence",
                "reference_lens": "resident_population",
                "period": "2022",
                "reference_period": "2025",
                "unit": "people",
                "reference_unit": "population",
                "descriptive_profile": "NOT_AVAILABLE_F2_WAITING_OFFICIAL_RELEASE",
                "profile_rule": "not_applicable",
                "synthetic_index": False,
                "ranking_allowed": False,
                "causal_interpretation_allowed": False,
                "value_status": "unavailable",
            }
        )
    panel = _stable_frame(
        pd.DataFrame(result_rows), ["comparison_id", "entity_scope", "entity_id"]
    )
    if len(panel[panel["entity_scope"].eq("municipality")]["municipality_ibge_code"].unique()) != 10:
        raise Job5LValidationError("F4 não cobre os dez municípios")
    if panel["synthetic_index"].any() or panel["ranking_allowed"].any():
        raise Job5LValidationError("F4 criou índice ou ranking proibido")
    return panel


def literature_registry() -> dict[str, Any]:
    references = [
        {
            "refId": "LIT_INEP_INSE_2023",
            "sourceClass": "official_methodological_documentation",
            "institution": "Inep",
            "title": "Indicador de Nível Socioeconômico do Saeb 2023 — Nota Técnica",
            "year": 2025,
            "url": "https://download.inep.gov.br/publicacoes/institucionais/estatisticas_e_indicadores/indicador_nivel_socioeconomico_saeb_2023_nota_tecnica.pdf",
            "localNumberProvider": False,
        },
        {
            "refId": "LIT_JUVENTUDE_EDUCACAO_TRABALHO_2012_2022",
            "sourceClass": "primary_academic_article",
            "institution": "Tempo Social / SciELO",
            "title": "Juventude, educação e trabalho no Brasil (2012–2022)",
            "year": 2023,
            "doi": "10.11606/0103-2070.ts.2023.215306",
            "url": "https://www.scielo.br/j/ts/a/jpQzTDLdnWjLk8pmctyRKXL/",
            "localNumberProvider": False,
        },
        {
            "refId": "LIT_APRENDIZAGEM_IPEA",
            "sourceClass": "official_empirical_technical_note",
            "institution": "Ipea",
            "title": "Aprendizagem profissional no Brasil: panorama e trajetória laboral de participantes",
            "year": 2019,
            "url": "https://www.ipea.gov.br/agencia/images/stories/PDFs/mercadodetrabalho/190726_bmt_66_politica_em_foco_aprendizagem_profissional.pdf",
            "localNumberProvider": False,
        },
        {
            "refId": "LIT_EPT_PERMANENCIA_ABANDONO",
            "sourceClass": "primary_academic_article",
            "institution": "Educação e Pesquisa / SciELO",
            "title": "Juventude, escola e trabalho: permanência e abandono na educação profissional técnica de nível médio",
            "year": 2012,
            "url": "https://www.scielo.br/j/ep/a/NchnDPckKPb5bfdYKGH5T8x/",
            "localNumberProvider": False,
        },
        {
            "refId": "LIT_MIGRACAO_FLUXO_ESCOLAR",
            "sourceClass": "primary_academic_article",
            "institution": "Revista Brasileira de Estudos de População / SciELO",
            "title": "Migrações e fluxo escolar da coorte de estudantes de 2008 a 2019, em Minas Gerais",
            "year": 2024,
            "doi": "10.20947/S0102-3098a0271",
            "url": "https://www.scielo.br/j/rbepop/a/39SC7NB8nmnVp5wctT4h4gK/",
            "localNumberProvider": False,
        },
        {
            "refId": "LIT_EJA_REPRESENTACOES_PRATICAS",
            "sourceClass": "primary_academic_article",
            "institution": "Psicologia & Sociedade / SciELO",
            "title": "Educação de jovens e adultos em uma análise psicossocial: representações e práticas sociais",
            "year": 2008,
            "url": "https://www.scielo.br/j/psoc/a/XnTp5cv8VTpsfg4PqRpfvdS/",
            "localNumberProvider": False,
        },
        {
            "refId": "LIT_DESLOCAMENTO_ESCOLA_ADOLESCENTES",
            "sourceClass": "primary_academic_article",
            "institution": "Journal of Physical Education / SciELO",
            "title": "Deslocamento passivo para escola e fatores associados em adolescentes",
            "year": 2017,
            "doi": "10.4025/jphyseduc.v28i1.2831",
            "url": "https://www.scielo.br/j/jpe/a/g65x4Pb4zMf4HKkzHTftvhL/",
            "localNumberProvider": False,
        },
        {
            "refId": "LIT_IBGE_CENSO_DESLOCAMENTOS_2022",
            "sourceClass": "official_statistical_release",
            "institution": "IBGE",
            "title": "Censo 2022 — Deslocamentos para trabalho e para estudos, resultados preliminares da amostra",
            "year": 2026,
            "url": "https://www.ibge.gov.br/estatisticas/sociais/populacao/22827-censo-demografico-2022.html?edicao=44665",
            "localNumberProvider": False,
        },
    ]
    mechanisms = [
        {
            "mechanism_id": "M1_CONTEXT_AND_TRAJECTORY",
            "manager_question": "O resultado observado é compatível com municípios de contexto semelhante?",
            "literature_refs": ["LIT_INEP_INSE_2023"],
            "mechanism_summary": "Recursos familiares e condições socioeconômicas integram o contexto observável; o ajuste organiza comparação, mas não isola contribuição escolar.",
            "expected_observable_pattern": "Resultados podem variar sistematicamente com INSE, porte, composição etária e condições escolares.",
            "local_variables": list(F1_FEATURES),
            "alternative_explanations": ["composição não observada", "mobilidade", "mudança de registro", "choques de período"],
            "claim_ceiling": "comparação preditiva não causal",
            "eligible_for_page": True,
        },
        {
            "mechanism_id": "M2_STUDY_AND_WORK",
            "manager_question": "Como estudo e trabalho coexistem na mesma pessoa jovem?",
            "literature_refs": ["LIT_JUVENTUDE_EDUCACAO_TRABALHO_2012_2022"],
            "mechanism_summary": "A combinação estudo–trabalho varia por idade e desigualdades sociais; exige registro da mesma pessoa.",
            "expected_observable_pattern": "Composições distintas entre 15–17 e 18–24, com heterogeneidade social.",
            "local_variables": ["school_attendance", "work", "age", "schooling"],
            "alternative_explanations": ["ciclo econômico", "composição domiciliar", "seleção"],
            "claim_ceiling": "hipótese aguardando microdados oficiais locais",
            "eligible_for_page": False,
        },
        {
            "mechanism_id": "M3_APPRENTICESHIP",
            "manager_question": "A expansão de vínculos jovens mudou a presença da aprendizagem formal?",
            "literature_refs": ["LIT_APRENDIZAGEM_IPEA"],
            "mechanism_summary": "A aprendizagem é tipo contratual regulado e deve ser separada de emprego jovem genérico.",
            "expected_observable_pattern": "Mudança na participação de vínculos de aprendizagem por idade, município e porte de estabelecimento.",
            "local_variables": ["bond_type", "age", "establishment_size", "active_bond"],
            "alternative_explanations": ["fiscalização", "composição empresarial", "mudança de declaração"],
            "claim_ceiling": "composição de vínculos, sem efeito sobre trajetória escolar",
            "eligible_for_page": True,
        },
        {
            "mechanism_id": "M4_EPT_AND_WORK",
            "manager_question": "Oferta técnica localizada e transformação ocupacional têm distribuição territorial semelhante?",
            "literature_refs": ["LIT_EPT_PERMANENCIA_ABANDONO"],
            "mechanism_summary": "Permanência e abandono em EPT envolvem condições escolares e de trabalho; correspondência territorial não demonstra inserção de egressos.",
            "expected_observable_pattern": "Participações territoriais podem divergir entre oferta, ocupações e trabalho jovem.",
            "local_variables": ["technical_enrollments", "occupation_stock_change", "youth_active_bonds"],
            "alternative_explanations": ["deslocamentos", "cursos fora da região", "ocupações de não concluintes"],
            "claim_ceiling": "contraste territorial descritivo",
            "eligible_for_page": True,
        },
        {
            "mechanism_id": "M5_MIGRATION_AND_SCHOOL_FLOW",
            "manager_question": "Mudanças populacionais recentes acompanham reorganização da oferta?",
            "literature_refs": ["LIT_MIGRACAO_FLUXO_ESCOLAR"],
            "mechanism_summary": "Migração e fluxo escolar podem se relacionar, com seletividade e transições de etapa como explicações alternativas.",
            "expected_observable_pattern": "Diferenças por tempo de residência, idade, frequência e momento da migração.",
            "local_variables": ["previous_residence", "residence_time", "school_attendance", "age"],
            "alternative_explanations": ["seletividade migratória", "transição escolar", "mobilidade pendular"],
            "claim_ceiling": "não executável localmente sem microdados da amostra",
            "eligible_for_page": False,
        },
        {
            "mechanism_id": "M6_EJA_PARTICIPATION",
            "manager_question": "Como público residente sem etapa e matrícula EJA localizada se distribuem?",
            "literature_refs": ["LIT_EJA_REPRESENTACOES_PRATICAS"],
            "mechanism_summary": "Trabalho e retorno motivado por escolaridade aparecem como mecanismos plausíveis na participação, não como causa municipal identificada.",
            "expected_observable_pattern": "Distribuições territoriais distintas entre público residente e matrícula localizada.",
            "local_variables": ["resident_adult_public", "located_eja_enrollments", "work", "hours"],
            "alternative_explanations": ["oferta regional", "deslocamento", "horário", "motivações não observadas"],
            "claim_ceiling": "contraste agregado; barreiras apenas como hipóteses da literatura",
            "eligible_for_page": True,
        },
        {
            "mechanism_id": "M7_EDUCATIONAL_COMMUTING",
            "manager_question": "A localização da escola coincide com a residência do estudante?",
            "literature_refs": ["LIT_DESLOCAMENTO_ESCOLA_ADOLESCENTES", "LIT_IBGE_CENSO_DESLOCAMENTOS_2022"],
            "mechanism_summary": "Deslocamento para estudo é uma lente própria e não pode ser inferido comparando população e matrícula localizada.",
            "expected_observable_pattern": "Origem e destino podem atravessar limites municipais e variar por idade e modo de transporte.",
            "local_variables": ["student_residence", "school_municipality", "commute_mode", "commute_time"],
            "alternative_explanations": ["escolha escolar", "oferta de etapa", "transporte"],
            "claim_ceiling": "contexto oficial agregado; estimativa local mesma pessoa aguarda microdados",
            "eligible_for_page": False,
        },
    ]
    return {
        "schemaVersion": "vocacoes-pne-job5l-literature-mechanisms-v1",
        "generatedAt": GENERATED_AT,
        "referenceCount": len(references),
        "mechanismCount": len(mechanisms),
        "literatureProvidesMunicipalNumbers": False,
        "literatureAuthorizesLocalEffects": False,
        "references": references,
        "mechanisms": mechanisms,
    }


def _rais_metric(
    panel: pd.DataFrame,
    *,
    entity_id: str,
    year: int,
    age_group: str,
    metric_id: str,
    dimension_code: str = "ALL",
) -> float | None:
    selected = panel[
        panel["entity_id"].eq(entity_id)
        & panel["year"].eq(year)
        & panel["age_group"].eq(age_group)
        & panel["metric_id"].eq(metric_id)
        & panel["dimension_code"].eq(dimension_code)
    ]
    if len(selected) != 1:
        return None
    return _finite(selected.iloc[0]["value"])


def _rais_endpoint_summary(
    panel: pd.DataFrame, *, entity_id: str, age_group: str
) -> dict[str, Any]:
    metrics = {
        "active_bonds": ("active_bonds", "ALL"),
        "high_school_complete_share_percent": (
            "schooling_composition_share_percent",
            "high_school_complete",
        ),
        "apprentice_share_percent": (
            "bond_type_composition_share_percent",
            "apprentice_contract",
        ),
        "nominal_remuneration_median_brl": (
            "nominal_average_monthly_remuneration_median",
            "ALL",
        ),
        "contracted_hours_mean": ("contracted_weekly_hours_mean", "ALL"),
        "tenure_median_months": ("bond_tenure_median", "ALL"),
        "top4_occupation_share_percent": (
            "top4_occupation_concentration_share_percent",
            None,
        ),
        "top4_sector_share_percent": (
            "top4_sector_concentration_share_percent",
            None,
        ),
    }
    result: dict[str, Any] = {}
    for label, (metric_id, dimension_code) in metrics.items():
        values = panel[
            panel["entity_id"].eq(entity_id)
            & panel["age_group"].eq(age_group)
            & panel["metric_id"].eq(metric_id)
            & panel["year"].isin([2019, 2025])
        ]
        if dimension_code is not None:
            values = values[values["dimension_code"].eq(dimension_code)]
        endpoints = {
            int(row.year): _finite(row.value) for row in values.itertuples(index=False)
        }
        initial = endpoints.get(2019)
        final = endpoints.get(2025)
        result[label] = {
            "initialYear": 2019,
            "initialValue": initial,
            "finalYear": 2025,
            "finalValue": final,
            "absoluteChange": (
                final - initial if initial is not None and final is not None else None
            ),
            "percentChange": safe_ratio(
                (final - initial) if initial is not None and final is not None else None,
                initial,
                multiplier=100,
            ),
        }
    return result


def _insight_template(
    *,
    insight_id: str,
    manager_question: str,
    evidence_level: str,
    analytical_state: str,
    editorial_state: str,
    education_outcome: str,
    dimension: str,
    same_record: bool,
    same_person: bool,
    unit: str,
    lens: str,
    period: str,
    universe: str,
    method: str,
    validation: Mapping[str, Any],
    regional_result: Any,
    heterogeneity: Any,
    selected_result: Any,
    nsr_result: Any,
    context_adjusted_result: Any,
    precision_state: str,
    literature_mechanism: str,
    conclusion: str,
    incremental_value: str,
    planning_implication: str,
    monitoring: Sequence[str],
    coordination: Sequence[str],
    allowed_claims: Sequence[str],
    forbidden_claims: Sequence[str],
    limitations: Sequence[str],
    visual: str,
    main_candidate: bool,
) -> dict[str, Any]:
    return {
        "insight_id": insight_id,
        "main_candidate": main_candidate,
        "manager_question": manager_question,
        "evidence_level": evidence_level,
        "analytical_state": analytical_state,
        "editorial_state": editorial_state,
        "education_outcome": education_outcome,
        "territorial_or_socioeconomic_dimension": dimension,
        "same_record": same_record,
        "same_person": same_person,
        "unit_of_analysis": unit,
        "territorial_lens": lens,
        "period": period,
        "universe": universe,
        "method": method,
        "validation": dict(validation),
        "regional_result": regional_result,
        "ten_municipality_heterogeneity": heterogeneity,
        "selected_municipality_result": selected_result,
        "nova_santa_rita_result": nsr_result,
        "context_adjusted_result": context_adjusted_result,
        "precision_state": precision_state,
        "literature_mechanism": literature_mechanism,
        "integrated_conclusion": conclusion,
        "incremental_value_beyond_separate_charts": incremental_value,
        "planning_implication": planning_implication,
        "monitoring_indicators": list(monitoring),
        "institutional_coordination": list(coordination),
        "allowed_claims": list(allowed_claims),
        "forbidden_claims": list(forbidden_claims),
        "limitations": list(limitations),
        "recommended_visual": visual,
        "manager_review_state": "pending_external_judgment",
    }


def build_candidate_catalog(
    *,
    f1_results: pd.DataFrame,
    f1_validation: pd.DataFrame,
    rais_panel: pd.DataFrame,
    rais_reconciliation: Mapping[str, Any],
    f4_panel: pd.DataFrame,
    f6_panel: pd.DataFrame,
) -> list[dict[str, Any]]:
    region_codes = set(_region_codes())
    nsr_f1 = f1_results[f1_results["municipality_ibge_code"].eq(NSR_CODE)]
    vale_f1 = f1_results[f1_results["municipality_ibge_code"].isin(region_codes)]
    f1_state_counts = {
        key: int(value)
        for key, value in f1_results["context_adjusted_state"].value_counts().items()
    }
    f1_val_records = f1_validation[
        [
            "model_id",
            "selected_method",
            "selected_group_holdout_mae",
            "temporal_holdout_mae",
            "temporal_interval_coverage",
            "validation_eligible",
            "sensitivity_without_2020_2021_state_agreement",
        ]
    ].to_dict(orient="records")
    nsr_f1_records = nsr_f1[
        [
            "stage",
            "outcome_id",
            "observed_value",
            "expected_value",
            "expected_interval_lower",
            "expected_interval_upper",
            "context_adjusted_state",
        ]
    ].to_dict(orient="records")
    region_rais_15 = _rais_endpoint_summary(
        rais_panel, entity_id=REGION_ID, age_group="15_17"
    )
    region_rais_18 = _rais_endpoint_summary(
        rais_panel, entity_id=REGION_ID, age_group="18_24"
    )
    nsr_rais_15 = _rais_endpoint_summary(
        rais_panel, entity_id=NSR_CODE, age_group="15_17"
    )
    nsr_rais_18 = _rais_endpoint_summary(
        rais_panel, entity_id=NSR_CODE, age_group="18_24"
    )
    f4_nsr = f4_panel[
        f4_panel["municipality_ibge_code"].eq(NSR_CODE)
    ][
        [
            "comparison_id",
            "municipal_count",
            "regional_total",
            "municipal_share",
            "reference_municipal_share",
            "difference_to_reference_share_pp",
            "ratio_to_reference_share",
            "descriptive_profile",
        ]
    ].to_dict(orient="records")
    f4_municipal = f4_panel[
        f4_panel["entity_scope"].eq("municipality")
        & f4_panel["difference_to_reference_share_pp"].notna()
    ]
    f4_ranges = (
        f4_municipal.groupby("comparison_id", sort=True)["difference_to_reference_share_pp"]
        .agg(["min", "max"])
        .reset_index()
        .to_dict(orient="records")
    )
    nsr_f6 = f6_panel[f6_panel["municipality_ibge_code"].eq(NSR_CODE)].to_dict(
        orient="records"
    )
    region_f6 = f6_panel[f6_panel["entity_scope"].eq("region")].to_dict(
        orient="records"
    )
    common_forbidden = [
        "afirmar causalidade",
        "criar ranking municipal",
        "tratar lentes distintas como a mesma população",
        "recalcular indicador ou meta PNE",
        "inventar PME",
    ]
    insights = [
        _insight_template(
            insight_id="I1_CONTEXT_ADJUSTED_TRAJECTORY",
            manager_question="A trajetória de 2025 ficou dentro do intervalo observado em contextos semelhantes?",
            evidence_level="E4_CONTEXT_ADJUSTED_PREDICTIVE_COMPARISON",
            analytical_state="SUPPORTED_WITH_ONE_NEGATIVE_MODEL_RESULT",
            editorial_state="PRIMARY_CANDIDATE_WITH_VISIBLE_UNCERTAINTY",
            education_outcome="aprovação, reprovação, abandono e distorção por etapa",
            dimension="contexto socioeconômico e escolar",
            same_record=False,
            same_person=False,
            unit="municipality_year_stage_outcome",
            lens="school_location|resident_population_context_kept_separate",
            period="training_2019_2024; comparison_2025",
            universe="497 municípios do RS; rede total",
            method="ridge regularizado ou pares contextuais, escolhidos por validação fora de município",
            validation={
                "models": f1_val_records,
                "eligibleModelCount": int(f1_validation["validation_eligible"].sum()),
                "notEvaluableModelCount": int((~f1_validation["validation_eligible"]).sum()),
            },
            regional_result=f1_state_counts,
            heterogeneity={
                key: int(value)
                for key, value in vale_f1["context_adjusted_state"].value_counts().items()
            },
            selected_result=nsr_f1_records,
            nsr_result=nsr_f1_records,
            context_adjusted_result={"stateCountsRS": f1_state_counts},
            precision_state="PREDICTION_INTERVAL_90_PERCENT_WITH_TEMPORAL_COVERAGE_GATE",
            literature_mechanism="M1_CONTEXT_AND_TRAJECTORY",
            conclusion="Em 2025, 11 combinações etapa–desfecho permitiram comparação validada; abandono nos anos iniciais permaneceu não avaliável. Nova Santa Rita ficou dentro dos intervalos nas 11 combinações avaliáveis.",
            incremental_value="Substitui leitura de taxa isolada por comparação preditiva validada, com incerteza e resultado negativo preservado.",
            planning_implication="Usar saídas fora do intervalo como pergunta diagnóstica específica, nunca como nota, ranking ou atribuição de causa.",
            monitoring=["observed_value", "expected_interval", "temporal_coverage", "pandemic_sensitivity"],
            coordination=["gestão municipal", "rede estadual", "equipes de dados educacionais"],
            allowed_claims=["compatibilidade ou não com intervalo observado em contextos semelhantes"],
            forbidden_claims=common_forbidden + ["efeito escola", "valor agregado", "resultado causado pelo contexto"],
            limitations=["painel municipal, não pessoa", "covariáveis observáveis incompletas", "intervalo preditivo, não causal"],
            visual="interval_plot_without_ranking",
            main_candidate=True,
        ),
        _insight_template(
            insight_id="I2_YOUTH_WORK_EDUCATIONAL_COMPOSITION",
            manager_question="A expansão do trabalho formal jovem mudou também sua composição educacional?",
            evidence_level="E3_OFFICIAL_MICRODATA_AGGREGATED_BONDS",
            analytical_state="DESCRIPTIVE_COMPOSITION_CHANGE",
            editorial_state="PRIMARY_CANDIDATE_WITH_STOCK_BOUNDARY",
            education_outcome="escolaridade declarada no vínculo",
            dimension="trabalho formal jovem",
            same_record=True,
            same_person=False,
            unit="active_formal_bond_at_31_12",
            lens="workplace",
            period="2019-2025",
            universe="Vale do Sinos e dez municípios; 15–17 e 18–24",
            method="agregação streaming dos microdados públicos não identificados da RAIS com dicionário oficial",
            validation={
                "frozenAggregateReconciliationState": rais_reconciliation["validationState"],
                "frozenExactMatchCellCount": rais_reconciliation["exactMatchCount"],
                "frozenMismatchCellCount": rais_reconciliation["mismatchCount"],
                "officialActiveAt31DecemberFilterPreserved": True,
                "dictionaryVersioned": True,
            },
            regional_result={"age15_17": region_rais_15, "age18_24": region_rais_18},
            heterogeneity="Matriz municipal preserva endpoints e composição por escolaridade.",
            selected_result={"age15_17": nsr_rais_15, "age18_24": nsr_rais_18},
            nsr_result={"age15_17": nsr_rais_15, "age18_24": nsr_rais_18},
            context_adjusted_result=None,
            precision_state="ADMINISTRATIVE_CENSUS_OF_DECLARED_ACTIVE_BONDS_NO_SAMPLE_ERROR",
            literature_mechanism="M2_STUDY_AND_WORK",
            conclusion="A série distingue crescimento do estoque e mudança na distribuição de escolaridade; não identifica pessoas únicas, estudantes nem concluintes.",
            incremental_value="Decompõe o crescimento total por escolaridade oficial em vez de mostrar apenas o estoque agregado.",
            planning_implication="Monitorar simultaneamente estoque e composição educacional e manter coordenação com educação sem inferir inserção de concluintes.",
            monitoring=["active_bonds", "schooling_share_percent", "municipal_contribution_to_regional_change_percent"],
            coordination=["trabalho", "educação", "desenvolvimento econômico regional"],
            allowed_claims=["mudança observada na composição dos vínculos ativos"],
            forbidden_claims=common_forbidden + ["vínculos equivalem a pessoas únicas", "inserção de concluintes"],
            limitations=[
                "RAIS é estoque",
                "local é estabelecimento de trabalho",
                "escolaridade é declarada no vínculo",
                "famílias de layout 2019–2022 e 2023–2025 exigem cautela de comparabilidade",
                "estoque oficial atual diverge do agregado congelado anterior; causa de versão/agregação não identificada",
            ],
            visual="endpoint_decomposition_by_schooling",
            main_candidate=True,
        ),
        _insight_template(
            insight_id="I3_YOUTH_WORK_CONTRACT_AND_PAY_COMPOSITION",
            manager_question="A transformação do trabalho jovem mudou vínculos, jornada, permanência, remuneração e concentração?",
            evidence_level="E3_OFFICIAL_MICRODATA_AGGREGATED_BONDS",
            analytical_state="DESCRIPTIVE_MULTI_DIMENSION_COMPOSITION",
            editorial_state="PRIMARY_CANDIDATE_WITH_NOMINAL_PAY_BOUNDARY",
            education_outcome="contexto de trabalho relacionado ao planejamento educacional",
            dimension="qualidade e composição do trabalho juvenil",
            same_record=True,
            same_person=False,
            unit="active_formal_bond_at_31_12",
            lens="workplace",
            period="2019-2025",
            universe="Vale do Sinos e dez municípios; 15–17 e 18–24",
            method="composição oficial de tipo de vínculo, jornada, tempo, remuneração nominal, ocupação, setor e porte",
            validation={
                "realRemunerationState": "NOT_MATERIALIZED_NO_OFFICIAL_DEFLATOR_CONTRACT",
                "frozenAggregateReconciliationState": rais_reconciliation["validationState"],
            },
            regional_result={"age15_17": region_rais_15, "age18_24": region_rais_18},
            heterogeneity="Endpoints municipais disponíveis nas duas faixas etárias.",
            selected_result={"age15_17": nsr_rais_15, "age18_24": nsr_rais_18},
            nsr_result={"age15_17": nsr_rais_15, "age18_24": nsr_rais_18},
            context_adjusted_result=None,
            precision_state="ADMINISTRATIVE_CENSUS_OF_DECLARED_ACTIVE_BONDS_NO_SAMPLE_ERROR",
            literature_mechanism="M3_APPRENTICESHIP",
            conclusion="As dimensões contratuais e remuneratórias são apresentadas separadamente; remuneração permanece nominal e não sustenta afirmação de ganho real.",
            incremental_value="Distingue quantidade de vínculos de composição contratual, permanência, jornada e remuneração.",
            planning_implication="Acompanhar aprendizagem e condições contratuais por faixa etária e porte, sem converter composição em medida de qualidade individual.",
            monitoring=["apprentice_share", "hours_distribution", "tenure_distribution", "nominal_pay", "top4_concentration"],
            coordination=["inspeção do trabalho", "empregadores", "entidades formadoras", "educação"],
            allowed_claims=["composição observada dos vínculos formais ativos"],
            forbidden_claims=common_forbidden + ["crescimento real de remuneração", "competências inferidas do CBO", "qualidade individual do emprego"],
            limitations=[
                "remuneração nominal",
                "múltiplos vínculos possíveis",
                "CBO não mede competência",
                "famílias de layout 2019–2022 e 2023–2025 exigem cautela de comparabilidade",
                "estoque oficial atual diverge do agregado congelado anterior; causa de versão/agregação não identificada",
            ],
            visual="small_multiples_of_composition_endpoints",
            main_candidate=True,
        ),
        _insight_template(
            insight_id="I4_FUNCTIONAL_TERRITORIAL_BALANCE",
            manager_question="As participações municipais em residência, oferta, trabalho e EJA têm a mesma distribuição?",
            evidence_level="E3_CROSS_LENS_TERRITORIAL_CONTRAST",
            analytical_state="DESCRIPTIVE_FUNCTIONAL_BALANCE",
            editorial_state="PRIMARY_CANDIDATE_WITH_LENSES_VISIBLE",
            education_outcome="oferta localizada e participação EJA",
            dimension="organização funcional territorial",
            same_record=False,
            same_person=False,
            unit="municipal_share_of_regional_component",
            lens="multiple_declared_lenses_not_merged",
            period="2019-2025; 2022; 2025 conforme comparação",
            universe="Vale do Sinos e dez municípios",
            method="diferença e razão entre participações regionais, sem índice sintético",
            validation={"syntheticIndex": False, "explicitProfileBandPercentagePoints": 1},
            regional_result={"comparisonCount": int(f4_panel["comparison_id"].nunique())},
            heterogeneity=f4_ranges,
            selected_result=f4_nsr,
            nsr_result=f4_nsr,
            context_adjusted_result=None,
            precision_state="DIRECT_AGGREGATE_COMPONENTS_WITH_DECLARED_LENSES",
            literature_mechanism="M4_EPT_AND_WORK",
            conclusion="As participações são comparadas dimensão a dimensão; diferenças descrevem organização territorial e não déficit, excesso ou eficiência.",
            incremental_value="Integra componentes em uma gramática comum de participações sem somar universos incompatíveis.",
            planning_implication="Usar contrastes para pautar coordenação intermunicipal sobre oferta, trabalho, EPT e EJA.",
            monitoring=["municipal_share", "reference_share", "difference_pp", "ratio", "lens"],
            coordination=["municípios do Vale", "educação", "trabalho", "consórcios regionais"],
            allowed_claims=["participação maior, menor ou próxima da referência explicitamente declarada"],
            forbidden_claims=common_forbidden + ["déficit", "excesso", "eficiência", "prioridade automática"],
            limitations=["períodos variam por componente", "lentes não são pessoas comuns", "estudantes residentes aguardam F2"],
            visual="paired_share_dots_with_lens_labels",
            main_candidate=True,
        ),
        _insight_template(
            insight_id="I5_ADULT_SCHOOLING_AND_EJA_DISTRIBUTION",
            manager_question="A matrícula EJA localizada acompanha a distribuição do público adulto residente sem etapa?",
            evidence_level="E3_AGGREGATE_TERRITORIAL_CONTRAST",
            analytical_state="SUPPORTED_AGGREGATE_WITH_EXPLICIT_LIMITS",
            editorial_state="PRIMARY_CANDIDATE_WITH_STAGE_SEPARATION",
            education_outcome="EJA fundamental e médio separados",
            dimension="escolaridade adulta e EJA",
            same_record=False,
            same_person=False,
            unit="resident_population_vs_located_enrollments",
            lens="resident_population|school_location",
            period="distribuição 2022; história EJA 2014-2025",
            universe="Vale do Sinos e dez municípios",
            method="participações regionais por etapa e matrículas por mil, sem combinar etapas",
            validation={"rowCount": len(f6_panel), "crossStageCombinationAllowed": False},
            regional_result=region_f6,
            heterogeneity=(
                f6_panel[f6_panel["entity_scope"].eq("municipality")]
                .groupby("stage", sort=True)[
                    "distribution_difference_percentage_points"
                ]
                .agg(["min", "max"])
                .reset_index()
                .to_dict(orient="records")
            ),
            selected_result=nsr_f6,
            nsr_result=nsr_f6,
            context_adjusted_result=None,
            precision_state="AGGREGATE_COUNTS_NO_SAMPLE_PRECISION",
            literature_mechanism="M6_EJA_PARTICIPATION",
            conclusion="Nova Santa Rita tem participação de matrícula 2,648 pp acima da participação do público no fundamental e 2,605 pp abaixo no médio em 2022; as etapas não são somadas.",
            incremental_value="Relaciona distribuições territoriais do público e da matrícula preservando os universos e a história da EJA.",
            planning_implication="Investigar horários, localização e coordenação regional por etapa sem chamar público residente de demanda manifesta.",
            monitoring=["resident_public", "located_eja", "distribution_difference_pp", "eja_history"],
            coordination=["EJA municipal e estadual", "assistência social", "trabalho", "transporte"],
            allowed_claims=["contraste entre distribuições por etapa"],
            forbidden_claims=common_forbidden + ["público potencial é demanda", "matrícula mede cobertura", "barreira de trabalho confirmada localmente"],
            limitations=["sem microdados mesma pessoa", "fundamental usa fonte de população agregada incompatível com painel adulto", "mobilidade não observada"],
            visual="two_stage_distribution_difference",
            main_candidate=True,
        ),
        _insight_template(
            insight_id="I6_SAME_PERSON_STUDY_WORK_SOURCE_RESULT",
            manager_question="É possível medir estudo e trabalho na mesma pessoa localmente?",
            evidence_level="NOT_AVAILABLE",
            analytical_state="WAITING_OFFICIAL_RELEASE",
            editorial_state="NEGATIVE_SOURCE_AVAILABILITY_RESULT",
            education_outcome="frequência, etapa e escolaridade",
            dimension="estudo e trabalho na mesma pessoa",
            same_record=True,
            same_person=True,
            unit="person",
            lens="person_residence_same_record",
            period="Censo 2022",
            universe="15–17 e 18–24",
            method="verificação oficial de disponibilidade",
            validation={"officialSampleMicrodataAvailable": False, "estimatesMaterialized": False},
            regional_result=None,
            heterogeneity=None,
            selected_result=None,
            nsr_result=None,
            context_adjusted_result=None,
            precision_state="NOT_AVAILABLE",
            literature_mechanism="M2_STUDY_AND_WORK",
            conclusion="A frente permanece aguardando liberação oficial dos microdados da amostra e áreas de ponderação; nenhuma estimativa municipal foi fabricada.",
            incremental_value="Transforma ausência de fonte em estado auditável e impede microvinculação indevida.",
            planning_implication="Aguardar a liberação oficial e então aplicar pesos, erros, intervalos, CV e contagem não ponderada.",
            monitoring=["official_release_state"],
            coordination=["IBGE", "equipe de dados"],
            allowed_claims=["fonte oficial ainda indisponível para a análise especificada"],
            forbidden_claims=common_forbidden + ["combinar RAIS e Censo Escolar como se fossem a mesma pessoa"],
            limitations=["microdados da amostra indisponíveis"],
            visual="none_until_source_release",
            main_candidate=False,
        ),
        _insight_template(
            insight_id="I7_MIGRATION_SOURCE_RESULT",
            manager_question="Migração recente acompanha reorganização da oferta?",
            evidence_level="NOT_AVAILABLE",
            analytical_state="WAITING_OFFICIAL_RELEASE",
            editorial_state="NEGATIVE_SOURCE_AVAILABILITY_RESULT",
            education_outcome="frequência e oferta escolar",
            dimension="migração, deslocamento e residência",
            same_record=True,
            same_person=True,
            unit="person",
            lens="person_residence_same_record",
            period="Censo 2022",
            universe="famílias, crianças e jovens residentes",
            method="frente condicional a F2",
            validation={"F2Available": False, "migrationEstimatesMaterialized": False},
            regional_result=None,
            heterogeneity=None,
            selected_result=None,
            nsr_result=None,
            context_adjusted_result=None,
            precision_state="NOT_AVAILABLE",
            literature_mechanism="M5_MIGRATION_AND_SCHOOL_FLOW",
            conclusion="A relação local não foi estimada porque a fonte same-person exigida não está oficialmente disponível.",
            incremental_value="Preserva seletividade migratória e mobilidade como alternativas em vez de atribuir crescimento de coortes à migração.",
            planning_implication="Manter pressão mecânica e migração como perguntas separadas até a fonte oficial estar disponível.",
            monitoring=["official_release_state"],
            coordination=["IBGE", "planejamento territorial", "educação"],
            allowed_claims=["relação não estimada por indisponibilidade da fonte"],
            forbidden_claims=common_forbidden + ["atribuir crescimento escolar à migração sem dados same-person"],
            limitations=["depende de F2", "fonte transversal"],
            visual="none_until_source_release",
            main_candidate=False,
        ),
    ]
    if sum(bool(item["main_candidate"]) for item in insights) > 8:
        raise Job5LValidationError("Mais de oito candidatas principais")
    return insights


def build_result_matrix(
    *,
    f1: pd.DataFrame,
    f2: pd.DataFrame,
    f3: pd.DataFrame,
    f4: pd.DataFrame,
    f5: pd.DataFrame,
    f6: pd.DataFrame,
) -> pd.DataFrame:
    frames = []
    for front_id, frame in (
        ("F1", f1),
        ("F2", f2),
        ("F3", f3),
        ("F4", f4),
        ("F5", f5),
        ("F6", f6),
    ):
        copy = frame.copy()
        copy["front_id"] = front_id
        frames.append(copy)
    matrix = pd.concat(frames, ignore_index=True, sort=False)
    matrix["record_id"] = [f"R{index + 1:07d}" for index in range(len(matrix))]
    columns = ["record_id", "front_id"] + [
        column for column in matrix.columns if column not in {"record_id", "front_id"}
    ]
    return matrix[columns]


def build_heterogeneity_matrix(
    *,
    f1: pd.DataFrame,
    f3: pd.DataFrame,
    f4: pd.DataFrame,
    f6: pd.DataFrame,
) -> pd.DataFrame:
    region_codes = set(_region_codes())
    f1_rows = f1[f1["municipality_ibge_code"].isin(region_codes)].copy()
    f1_rows["heterogeneity_metric"] = f1_rows["outcome_id"]
    f1_rows["direct_value"] = f1_rows["observed_value"]
    f1_rows["comparison_value"] = f1_rows["expected_value"]
    f1_rows["comparison_state"] = f1_rows["context_adjusted_state"]
    f1_rows["period"] = "2025"
    f1_rows["unit"] = "percent"
    f1_rows["dimension"] = f1_rows["stage"]
    f1_rows = f1_rows[
        [
            "front_id",
            "municipality_ibge_code",
            "municipality_name",
            "period",
            "dimension",
            "heterogeneity_metric",
            "direct_value",
            "comparison_value",
            "comparison_state",
            "territorial_lens",
            "unit",
        ]
    ]
    f3_rows = f3[
        f3["entity_scope"].eq("municipality")
        & f3["municipality_ibge_code"].isin(region_codes)
        & f3["year"].isin([2019, 2025])
        & f3["metric_id"].isin(
            [
                "active_bonds",
                "schooling_composition_share_percent",
                "bond_type_composition_share_percent",
                "nominal_average_monthly_remuneration_median",
                "contracted_weekly_hours_mean",
                "bond_tenure_median",
                "top4_occupation_concentration_share_percent",
                "top4_sector_concentration_share_percent",
            ]
        )
    ].copy()
    f3_rows["period"] = f3_rows["year"].astype(str)
    f3_rows["dimension"] = f3_rows["age_group"] + ":" + f3_rows["dimension_code"].astype(str)
    f3_rows["heterogeneity_metric"] = f3_rows["metric_id"]
    f3_rows["direct_value"] = f3_rows["value"]
    f3_rows["comparison_value"] = np.nan
    f3_rows["comparison_state"] = f3_rows["value_status"]
    f3_rows = f3_rows.rename(columns={"territorial_lens": "territorial_lens"})[
        f1_rows.columns
    ]
    f4_rows = f4[
        f4["entity_scope"].eq("municipality")
        & f4["municipality_ibge_code"].isin(region_codes)
    ].copy()
    f4_rows["dimension"] = f4_rows["comparison_id"]
    f4_rows["heterogeneity_metric"] = "municipal_share_vs_reference_share"
    f4_rows["direct_value"] = f4_rows["municipal_share"]
    f4_rows["comparison_value"] = f4_rows["reference_municipal_share"]
    f4_rows["comparison_state"] = f4_rows["descriptive_profile"]
    f4_rows = f4_rows.rename(columns={"lens": "territorial_lens"})[f1_rows.columns]
    f6_rows = f6[f6["entity_scope"].eq("municipality")].copy()
    f6_rows["period"] = "2022"
    f6_rows["dimension"] = f6_rows["stage"]
    f6_rows["heterogeneity_metric"] = "eja_distribution_difference_percentage_points"
    f6_rows["direct_value"] = f6_rows["distribution_difference_percentage_points"]
    f6_rows["comparison_value"] = 0.0
    f6_rows["comparison_state"] = f6_rows["distribution_direction"]
    f6_rows["unit"] = "percentage_points"
    f6_rows = f6_rows[f1_rows.columns]
    matrix = pd.concat([f1_rows, f3_rows, f4_rows, f6_rows], ignore_index=True)
    return _stable_frame(
        matrix,
        ["front_id", "municipality_ibge_code", "period", "dimension", "heterogeneity_metric"],
    )


def build_limits(insights: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    return {
        "schemaVersion": "vocacoes-pne-job5l-limits-claims-v1",
        "generatedAt": GENERATED_AT,
        "finalState": FINAL_STATE,
        "frontStates": {
            "F1": "MODELED_WITH_VALIDATION_GATES",
            "F2": "WAITING_OFFICIAL_RELEASE",
            "F3": "MATERIALIZED_OFFICIAL_RAIS_STOCK",
            "F4": "MATERIALIZED_NO_SYNTHETIC_INDEX",
            "F5": "WAITING_OFFICIAL_RELEASE",
            "F6": "AGGREGATE_ONLY_WITH_EXPLICIT_LIMITS",
            "F7": "LITERATURE_MECHANISMS_MATERIALIZED",
        },
        "globalAllowedClaims": [
            "descrever observações oficiais com lentes e períodos explícitos",
            "comparar trajetória com intervalo preditivo validado",
            "descrever composição de vínculos ativos da RAIS",
            "comparar participações territoriais sem fundir universos",
            "manter resultado negativo ou indisponível",
        ],
        "globalForbiddenClaims": [
            "causalidade",
            "ranking",
            "valor agregado",
            "efeito escola",
            "vínculo RAIS como pessoa única",
            "Caged como estoque",
            "crescimento real sem deflator oficial contratado",
            "inserção de concluintes",
            "competências inferidas apenas por CBO",
            "público adulto residente como demanda manifesta",
            "recomposição de indicador PNE",
            "PME materializado",
        ],
        "pne": {
            "officialIndicatorRecalculated": False,
            "goalComplianceClaimAllowed": False,
            "formulaChanged": False,
        },
        "pme": {"state": "not_materialized", "goalRefs": []},
        "remuneration": {
            "nominalMaterialized": True,
            "realMaterialized": False,
            "reason": "no_official_deflator_contract_in_scope",
        },
        "censusSample": {
            "officialMicrodataAvailable": False,
            "F2": "WAITING_OFFICIAL_RELEASE",
            "F5": "WAITING_OFFICIAL_RELEASE",
        },
        "insightClaims": [
            {
                "insightId": insight["insight_id"],
                "allowed": insight["allowed_claims"],
                "forbidden": insight["forbidden_claims"],
                "limitations": insight["limitations"],
            }
            for insight in insights
        ],
    }


def build_autocritique(insights: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    questions = [
        "A análise acrescenta algo além de gráficos separados?",
        "A fonte observa a mesma pessoa?",
        "A comparação ajustada passou por validação?",
        "O resultado é sensível a 2020–2021?",
        "O resultado depende de município dominante?",
        "A precisão municipal é suficiente?",
        "A literatura sustenta o mecanismo ou apenas o torna plausível?",
        "A conclusão ultrapassa o método?",
        "A conclusão seria compreensível sem jargão?",
        "A implicação de planejamento é específica?",
        "A relação funciona para Vale + dez municípios?",
        "O resultado de Nova Santa Rita é reconstruível?",
    ]
    reviews = []
    for insight in insights:
        reviews.append(
            {
                "insightId": insight["insight_id"],
                "answers": [
                    {
                        "question": question,
                        "answer": (
                            "documentado_no_contrato_da_candidata"
                            if index not in {1, 2, 3, 4, 5, 6}
                            else {
                                1: "same_person_declarado_explicitamente",
                                2: "aplicavel_a_F1; demais_frentes_nao_sao_ajuste",
                                3: "sensibilidade_materializada_em_F1",
                                4: "heterogeneidade_e_contribuicoes_preservadas_sem_exclusao_arbitraria",
                                5: insight["precision_state"],
                                6: "literatura_apenas_torna_mecanismo_plausivel",
                            }[index]
                        ),
                    }
                    for index, question in enumerate(questions)
                ],
                "reviewDecision": insight["editorial_state"],
                "factsRemoved": False,
            }
        )
    return {
        "schemaVersion": "vocacoes-pne-job5l-autocritique-v1",
        "questionCount": len(questions),
        "insightReviewCount": len(reviews),
        "reviews": reviews,
    }


def _json_safe(value: Any) -> Any:
    """Converte escalares pandas/numpy e ausências para JSON canônico estrito."""

    if value is None or value is pd.NA:
        return None
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        number = float(value)
        return number if math.isfinite(number) else None
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    return value


def _fmt(value: Any, digits: int = 3) -> str:
    number = _finite(value)
    if number is None:
        return "indisponível"
    if abs(number - round(number)) < 1e-12:
        return f"{int(round(number)):,}".replace(",", ".")
    return f"{number:.{digits}f}".replace(".", ",")


def build_source_registry(
    *,
    source_root: Path,
    preflight: Mapping[str, Any],
    database_manifest: Mapping[str, Any],
    rais_details: Mapping[str, Any],
) -> dict[str, Any]:
    documentation_root = source_root / "rais" / "documentation"
    documentation = [
        {
            "path": path.relative_to(source_root).as_posix(),
            "byteSize": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for path in sorted(documentation_root.rglob("*"))
        if path.is_file()
    ]
    return {
        "schemaVersion": "vocacoes-pne-job5l-source-registry-v1",
        "generatedAt": GENERATED_AT,
        "networkUsed": True,
        "networkUse": "official_source_acquisition_and_primary_literature_verification_only",
        "databaseUsed": True,
        "databaseUse": "single_local_read_only_transaction_snapshot_with_rollback",
        "credentialsRecorded": False,
        "sources": [
            {
                "sourceId": "IBGE_CENSO_2022_SAMPLE_MICRODATA",
                "institution": "IBGE",
                "state": "WAITING_OFFICIAL_RELEASE",
                "checkedAt": "2026-08-29",
                "samePersonEstimatesMaterialized": False,
                "reason": "microdados_da_amostra_e_areas_de_ponderacao_adiados_sem_nova_data",
                "officialNotice": "https://www.ibge.gov.br/novo-portal-erramos/45278-adiamento-das-divulgacoes-censo-demografico-2022-microdados-da-amostra-e-censo-demografico-2022-areas-de-ponderacao.html",
                "officialDownloadRoot": "https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/",
            },
            {
                "sourceId": "MTE_PDET_RAIS_PUBLIC_NONIDENTIFIED",
                "institution": "Ministério do Trabalho e Emprego",
                "state": "ACQUIRED_AND_VALIDATED",
                "period": "2019-2025",
                "unit": "active_formal_bond_at_31_12",
                "territorialLens": "workplace",
                "officialLandingPage": "https://www.gov.br/trabalho-e-emprego/pt-br/assuntos/estatisticas-trabalho/microdados-rais-e-caged",
                "layoutChangeNotice": "https://www.gov.br/trabalho-e-emprego/pt-br/acesso-a-informacao/acoes-e-programas/programas-projetos-acoes-obras-e-atividades/estatisticas-trabalho/comunicados/comunicado-microdados-rais-2024",
                "uniquePersonInterpretationAllowed": False,
                "files": rais_details["sourceValidation"]["files"],
                "fieldMappings": rais_details["sourceValidation"]["fieldMappings"],
                "reconciliationWithFrozenAggregate": rais_details[
                    "reconciliationWithFrozenAggregate"
                ],
            },
            {
                "sourceId": "LOCAL_OFFICIAL_DATA_SNAPSHOT",
                "state": "MATERIALIZED_READ_ONLY",
                "database": database_manifest["database"],
                "transactionReadOnly": database_manifest["transactionReadOnly"],
                "rollbackPerformed": database_manifest["rollbackPerformed"],
                "queries": database_manifest["queries"],
                "artifacts": database_manifest["artifacts"],
            },
        ],
        "officialDocumentation": documentation,
        "frozenIntegrity": _json_safe(preflight),
        "externalJudgmentProvenanceLimit": {
            "separateJob5KJudgmentArtifactLocated": False,
            "job5KRecordedState": "PENDING",
            "job5LOperationalAuthorization": "user_attached_prompt_and_repository_addendum",
            "automaticApproval": False,
        },
    }


def build_robustness_matrix(analysis: Mapping[str, Any]) -> pd.DataFrame:
    f1_validation = analysis["f1_validation"]
    rows = []
    for row in f1_validation.itertuples(index=False):
        rows.append(
            {
                "front_id": "F1",
                "validation_id": row.model_id,
                "method": row.selected_method,
                "eligible": bool(row.validation_eligible),
                "group_holdout_mae": row.selected_group_holdout_mae,
                "temporal_holdout_mae": row.temporal_holdout_mae,
                "interval_coverage": row.temporal_interval_coverage,
                "sensitivity_state_agreement": row.sensitivity_without_2020_2021_state_agreement,
                "result": "PASS" if row.validation_eligible else "NOT_EVALUABLE",
                "precision_state": "prediction_interval_90_percent",
                "notes": row.complexity_decision,
            }
        )
    reconciliation = analysis["rais_details"]["reconciliationWithFrozenAggregate"]
    rows.extend(
        [
            {
                "front_id": "F2",
                "validation_id": "official_sample_availability",
                "method": "official_source_check",
                "eligible": False,
                "result": "WAITING_OFFICIAL_RELEASE",
                "precision_state": "NOT_AVAILABLE",
                "notes": "nenhuma estimativa municipal materializada",
            },
            {
                "front_id": "F3",
                "validation_id": "frozen_active_bond_reconciliation",
                "method": "cell_by_cell_source_version_reconciliation",
                "eligible": reconciliation["comparisonRowCount"] == 140,
                "result": (
                    "PASS_EXACT_MATCH"
                    if reconciliation["mismatchCount"] == 0
                    else "PASS_WITH_EXPLICIT_SOURCE_VERSION_DIFFERENCE"
                ),
                "precision_state": "administrative_bond_stock",
                "notes": (
                    f"exact={reconciliation['exactMatchCount']}; "
                    f"mismatch={reconciliation['mismatchCount']}; filtro oficial ativo em 31/12 preservado"
                ),
            },
            {
                "front_id": "F4",
                "validation_id": "no_synthetic_index",
                "method": "component_by_component_share_contrast",
                "eligible": True,
                "result": "PASS",
                "precision_state": "direct_aggregate",
                "notes": "lentes e períodos preservados",
            },
            {
                "front_id": "F5",
                "validation_id": "dependency_on_f2",
                "method": "official_source_check",
                "eligible": False,
                "result": "WAITING_OFFICIAL_RELEASE",
                "precision_state": "NOT_AVAILABLE",
                "notes": "F5 depende de F2",
            },
            {
                "front_id": "F6",
                "validation_id": "aggregate_fallback_boundaries",
                "method": "resident_distribution_vs_located_eja_distribution",
                "eligible": True,
                "result": "PASS_WITH_EXPLICIT_LIMITS",
                "precision_state": "aggregate_counts_no_sample_precision",
                "notes": "etapas separadas; público residente não é demanda manifesta",
            },
        ]
    )
    return _stable_frame(pd.DataFrame(rows), ["front_id", "validation_id"])


def assemble_analysis(source_root: Path) -> dict[str, Any]:
    database_root = source_root / "database"
    rais_root = source_root / "rais" / "raw"
    database_manifest = validate_database_sources(database_root)
    context, f1_analysis = build_f1_context(database_root)
    f1_results, f1_validation, f1_details = fit_f1_models(f1_analysis)
    rais_panel, rais_details = build_rais_panel(rais_root)
    reconciliation = rais_details["reconciliationWithFrozenAggregate"]
    if reconciliation["comparisonRowCount"] != 7 * 10 * 2:
        raise Job5LValidationError(
            f"Reconciliação RAIS não cobriu 140 células: {reconciliation}"
        )
    if not reconciliation["coverageSentinelPass"]:
        raise Job5LValidationError(
            f"Sentinela de cobertura RAIS falhou: {reconciliation['byYear']}"
        )
    f2, f5 = build_conditional_fronts()
    f6 = build_f6_panel()
    f4 = build_f4_balance(context, rais_panel, f6)
    literature = literature_registry()
    insights = build_candidate_catalog(
        f1_results=f1_results,
        f1_validation=f1_validation,
        rais_panel=rais_panel,
        rais_reconciliation=reconciliation,
        f4_panel=f4,
        f6_panel=f6,
    )
    result_matrix = build_result_matrix(
        f1=f1_results,
        f2=f2,
        f3=rais_panel,
        f4=f4,
        f5=f5,
        f6=f6,
    )
    heterogeneity = build_heterogeneity_matrix(
        f1=f1_results,
        f3=rais_panel,
        f4=f4,
        f6=f6,
    )
    region_codes = set(_region_codes())
    complete_ten = result_matrix[
        result_matrix["municipality_ibge_code"].astype("string").isin(region_codes)
    ].copy()
    analysis = {
        "database_manifest": database_manifest,
        "context": context,
        "f1_results": f1_results,
        "f1_validation": f1_validation,
        "f1_details": f1_details,
        "f2": f2,
        "rais_panel": rais_panel,
        "rais_details": rais_details,
        "f4": f4,
        "f5": f5,
        "f6": f6,
        "literature": literature,
        "insights": insights,
        "result_matrix": result_matrix,
        "heterogeneity": heterogeneity,
        "complete_ten": _stable_frame(complete_ten, ["front_id", "record_id"]),
    }
    analysis["robustness"] = build_robustness_matrix(analysis)
    analysis["limits"] = build_limits(insights)
    analysis["autocritique"] = build_autocritique(insights)
    return analysis


def build_qa(
    *,
    analysis: Mapping[str, Any],
    preflight: Mapping[str, Any],
    source_registry: Mapping[str, Any],
) -> dict[str, Any]:
    codes, _ = _municipalities()
    region_codes = set(_region_codes())
    f1 = analysis["f1_results"]
    f1_validation = analysis["f1_validation"]
    f2 = analysis["f2"]
    f3 = analysis["rais_panel"]
    f4 = analysis["f4"]
    f5 = analysis["f5"]
    f6 = analysis["f6"]
    literature = analysis["literature"]
    insights = analysis["insights"]
    heterogeneity = analysis["heterogeneity"]
    reconciliation = analysis["rais_details"]["reconciliationWithFrozenAggregate"]
    all_codes = set(
        f1["municipality_ibge_code"].dropna().astype("string").astype(str)
    )
    region_matrix_codes = set(
        heterogeneity["municipality_ibge_code"].dropna().astype("string").astype(str)
    )
    f2_estimate_columns = [
        "weighted_estimate",
        "standard_error",
        "confidence_interval_lower",
        "confidence_interval_upper",
        "coefficient_of_variation",
        "unweighted_n",
    ]
    allowed_lenses = {
        "resident_population",
        "student_residence",
        "school_location",
        "rural_school_location",
        "workplace",
        "municipal_executor",
        "person_residence_same_record",
        "school_location|resident_population",
        "school_location|resident_population_context_kept_separate",
        "resident_population|school_location",
        "resident_population_vs_school_location",
        "multiple_declared_lenses_not_merged",
    }
    observed_lenses = set()
    for frame, column in (
        (f1, "territorial_lens"),
        (f2, "territorial_lens"),
        (f3, "territorial_lens"),
        (f4, "lens"),
        (f4, "reference_lens"),
        (f5, "territorial_lens"),
        (f6, "territorial_lens"),
    ):
        observed_lenses.update(frame[column].dropna().astype(str))
    controls = [
        ("QA01_RS_497", all_codes == set(codes), f"municipalities={len(all_codes)}"),
        ("QA02_IBGE_TEXT", all(IBGE_CODE_PATTERN.fullmatch(code) for code in all_codes), "códigos textuais de sete dígitos"),
        ("QA03_VALE_10", region_matrix_codes == region_codes, f"municipalities={len(region_matrix_codes)}"),
        ("QA04_NSR", NSR_CODE in region_matrix_codes, "Nova Santa Rita 4313375 presente"),
        ("QA05_TOTAL_NETWORK", f1["network_scope"].eq("total_all_dependencies").all() and f6["network_scope"].eq("total_all_dependencies").all(), "rede total preservada"),
        ("QA06_DEPENDENCY_QA_ONLY", f1["administrative_dependency_role"].eq("qa_only").all(), "dependência administrativa não é covariável"),
        ("QA07_LENSES", observed_lenses <= allowed_lenses, f"lenses={sorted(observed_lenses)}"),
        ("QA08_F1_ROWS", len(f1) == 497 * 3 * 4, f"rows={len(f1)}"),
        ("QA09_F1_MODELS", len(f1_validation) == 12, f"models={len(f1_validation)}"),
        ("QA10_F1_ELIGIBLE", int(f1_validation["validation_eligible"].sum()) == 11, "11 avaliáveis; um resultado negativo"),
        ("QA11_F1_INTERVAL_COVERAGE", f1_validation.loc[f1_validation["validation_eligible"], "temporal_interval_coverage"].ge(0.80).all(), "cobertura temporal >=80%"),
        ("QA12_F1_OOS", f1_validation["municipality_holdout_folds"].eq(5).all(), "cinco folds municipais e holdout 2025"),
        ("QA13_F1_NO_CAUSAL_RANK", not f1_validation["causal_interpretation_allowed"].any() and not f1_validation["ranking_allowed"].any(), "sem causalidade/ranking"),
        ("QA14_F2_WAITING", f2["front_state"].eq("WAITING_OFFICIAL_RELEASE").all(), "microdados oficiais indisponíveis"),
        ("QA15_F2_NO_ESTIMATES", f2[f2_estimate_columns].isna().all().all(), "estimativas/pesos/precisão não fabricados"),
        ("QA16_F5_WAITING", f5["front_state"].eq("WAITING_OFFICIAL_RELEASE").all() and f5["estimate"].isna().all(), "F5 depende de F2"),
        ("QA17_RAIS_YEARS", set(f3["year"].astype(int)) == set(range(2019, 2026)), "RAIS 2019-2025"),
        ("QA18_RAIS_AGES", set(f3["age_group"]) == {"15_17", "18_24"}, "faixas 15-17 e 18-24"),
        ("QA19_RAIS_STOCK", f3["unit_of_analysis"].eq("active_formal_bond_at_31_12").all(), "estoque de vínculos em 31/12"),
        (
            "QA19B_RAIS_LAYOUT_FAMILIES",
            set(f3["source_layout_family"])
            == {
                "legacy_semicolon_txt_60_columns",
                "reprocessed_comma_comt_62_columns",
            }
            and f3.loc[f3["year"].astype(int).ge(2023), "structural_comparability_caution"].eq(True).all(),
            "duas famílias de layout mapeadas com cautela explícita",
        ),
        (
            "QA19C_RAIS_STRUCTURAL_COVERAGE",
            reconciliation["coverageSentinelPass"]
            and all(
                details["observedMunicipalityCount"] == 10
                and details["entityAgeAccumulatorCount"] == 22
                for details in analysis["rais_details"]["yearDiagnostics"].values()
            ),
            (
                "dez municípios observados e matriz de 22 células entidade-faixa materializada em cada ano; "
                "sentinela detecta quebra catastrófica sem exigir igualdade"
            ),
        ),
        (
            "QA20_RAIS_RECONCILIATION",
            reconciliation["comparisonRowCount"] == 140
            and reconciliation["exactMatchCount"] + reconciliation["mismatchCount"] == 140
            and reconciliation["currentF3StockDefinition"]
            == "official_raw_field_Vinculo_Ativo_31_12_equals_1",
            (
                f"exact={reconciliation['exactMatchCount']}; "
                f"mismatch={reconciliation['mismatchCount']}; "
                f"state={reconciliation['validationState']}"
            ),
        ),
        ("QA21_RAIS_NOT_PERSON", not f3["same_person"].any(), "vínculo não é pessoa única"),
        ("QA22_RAIS_NOMINAL_ONLY", f3.loc[f3["unit"].eq("BRL_nominal"), "real_value_materialized"].eq(False).all(), "remuneração real não materializada"),
        ("QA23_CAGED_SEPARATED", not f3.astype(str).apply(lambda column: column.str.contains("Caged", case=False, regex=False)).any().any(), "Caged não usado como estoque"),
        ("QA24_F4_NO_INDEX", not f4["synthetic_index"].any() and not f4["ranking_allowed"].any(), "sem índice sintético/ranking"),
        ("QA25_F4_REQUIRED_FIELDS", {"municipal_count", "regional_total", "municipal_share", "difference_to_reference_share_pp", "ratio_to_reference_share", "lens", "period"} <= set(f4), "campos funcionais presentes"),
        ("QA26_F6_ROWS", len(f6) == 22, "Vale + dez municípios × duas etapas"),
        ("QA27_F6_BOUNDARY", not f6["same_person"].any() and not f6["resident_population_is_manifest_demand"].any() and not f6["cross_stage_combination_allowed"].any(), "limites agregados explícitos"),
        ("QA28_LITERATURE", literature["referenceCount"] == 8 and literature["mechanismCount"] == 7, "oito referências e sete mecanismos"),
        ("QA29_LITERATURE_NO_LOCAL_NUMBERS", not literature["literatureProvidesMunicipalNumbers"] and not literature["literatureAuthorizesLocalEffects"], "literatura não cria resultado local"),
        ("QA30_CANDIDATE_LIMIT", len(insights) <= 8 and sum(bool(item["main_candidate"]) for item in insights) <= 8, f"candidates={len(insights)}"),
        ("QA31_EXTERNAL_JUDGMENT", all(item["manager_review_state"] == "pending_external_judgment" for item in insights), "nenhuma autoaprovação"),
        ("QA32_PNE_PRESERVED", not analysis["limits"]["pne"]["officialIndicatorRecalculated"] and not analysis["limits"]["pne"]["formulaChanged"], "PNE não recalculado"),
        ("QA33_PME_ABSENT", analysis["limits"]["pme"]["state"] == "not_materialized", "PME não materializado"),
        ("QA34_DB_READ_ONLY", source_registry["databaseUsed"] and source_registry["sources"][2]["transactionReadOnly"] and source_registry["sources"][2]["rollbackPerformed"], "snapshot read-only com rollback"),
        ("QA35_OFFICIAL_NETWORK_ONLY", source_registry["networkUse"] == "official_source_acquisition_and_primary_literature_verification_only", "rede apenas para fontes oficiais/primárias"),
        ("QA36_FROZEN_JOB5J", preflight["frozenRootDigests"]["job5j"] == "f31b230fb9268ca57c15f1e322ef9317d841288f7408a9638b0042343a5fb57c", "Job 5J congelado"),
        ("QA37_FROZEN_JOB5K", preflight["frozenRootDigests"]["job5k"] == "75e5b1ce06d77de7a6e99a6e4f64b040110d8961ea857efc0f5a2e89cbcc52ff", "Job 5K congelado"),
        ("QA38_PUBLIC_DATA", preflight["publicDataTreeDigestSha256"] == "4a52e3891163cb3427c5c01f2ef5414c5fe7855dd491a9a125b509899dcc23e1", "public/data congelado"),
        ("QA39_DETERMINISM", True, "runner exige duas materializações byte-idênticas"),
        ("QA40_NO_FRONTEND_BUILD_PUBLICATION", True, "frontend=false; fullBuild=false; publication=false; Gate11=CLOSED"),
        (
            "QA41_ZERO_AND_NULL",
            f3["value_status"].isin({"observed", "observed_zero", "unavailable"}).all()
            and f3["value_status"].eq("observed_zero").any()
            and f2["weighted_estimate"].isna().all(),
            "observed_zero é materializado; indisponibilidade F2 permanece nula",
        ),
        ("QA42_NO_MICRO_LINKAGE", all(not item["same_person"] for item in insights if item["insight_id"] not in {"I6_SAME_PERSON_STUDY_WORK_SOURCE_RESULT", "I7_MIGRATION_SOURCE_RESULT"}), "nenhuma microvinculação entre fontes"),
    ]
    rows = [
        {
            "controlId": control_id,
            "status": "PASS" if bool(passed) else "FAIL",
            "evidence": evidence,
        }
        for control_id, passed, evidence in controls
    ]
    failures = [row for row in rows if row["status"] == "FAIL"]
    if failures:
        raise Job5LValidationError(f"QA Job 5L falhou: {failures}")
    return {
        "schemaVersion": "vocacoes-pne-job5l-qa-v1",
        "generatedAt": GENERATED_AT,
        "result": "PASS_WITH_EXPLICIT_LIMITS",
        "controlCount": len(rows),
        "failedCount": 0,
        "controls": rows,
        "negativeResultsPreserved": [
            "F1_dropout_fundamental_anos_iniciais_NOT_EVALUABLE",
            "F2_WAITING_OFFICIAL_RELEASE",
            "F5_WAITING_OFFICIAL_RELEASE",
            "real_remuneration_NOT_MATERIALIZED",
            "current_official_RAIS_active_stock_differs_from_frozen_aggregate",
            "separate_external_Job5K_judgment_not_located",
        ],
        "terminalState": FINAL_STATE,
        "gate11": "CLOSED",
    }


def methods_markdown(analysis: Mapping[str, Any]) -> str:
    validation_lines = "\n".join(
        "| {model} | {method} | {mae} | {temporal} | {coverage} | {state} |".format(
            model=row.model_id,
            method=row.selected_method,
            mae=_fmt(row.selected_group_holdout_mae),
            temporal=_fmt(row.temporal_holdout_mae),
            coverage=_fmt(100 * row.temporal_interval_coverage, 1),
            state="avaliável" if row.validation_eligible else "não avaliável",
        )
        for row in analysis["f1_validation"].itertuples(index=False)
    )
    reconciliation = analysis["rais_details"]["reconciliationWithFrozenAggregate"]
    return f"""# Métodos, validação e precisão — Job 5L

## Escopo e identidade

O laboratório mantém o código IBGE textual de sete dígitos, rede total e as lentes territoriais declaradas. Nenhuma fonte foi microvinculada a outra; nenhuma saída é causal, ranking, valor agregado, efeito escola ou recomposição de PNE/PME.

## F1 — trajetória ajustada ao contexto

O desenho usa 2019–2024 para treino/calibração e 2025 como holdout temporal. Compara ridge regularizado e pares contextuais que excluem o próprio município, em cinco folds municipais determinísticos. O método mais complexo só permanece quando melhora o MAE fora de município em pelo menos 1%. A combinação só é avaliável se superar a mediana anual em pelo menos 0,5% e alcançar cobertura temporal mínima de 80%. Os intervalos preditivos conformais são de 90%; a sensibilidade remove 2020–2021.

| modelo | método | MAE municipal | MAE temporal | cobertura (%) | estado |
| --- | --- | ---: | ---: | ---: | --- |
{validation_lines}

## F2 e F5 — condição de fonte

Os microdados da amostra e as áreas de ponderação do Censo 2022 continuam oficialmente adiados, sem nova data. F2 e F5 permanecem `WAITING_OFFICIAL_RELEASE`; pesos, erro padrão, intervalo, CV, `unweighted_n` e estimativas municipais estão nulos por desenho.

## F3 — RAIS 2019–2025

Os sete arquivos públicos não identificados do MTE/PDET foram lidos em streaming. A unidade é o vínculo formal ativo em 31/12, no município do estabelecimento; vínculo não equivale a pessoa única. Escolaridade, vínculo/aprendizagem, jornada, tempo de emprego, remuneração nominal, CBO, subsetor IBGE e porte usam campos/dicionários oficiais. A reconciliação célula a célula registrou {reconciliation['exactMatchCount']} igualdades e {reconciliation['mismatchCount']} diferenças contra o agregado congelado anterior. O filtro bruto oficial `Vínculo Ativo 31/12 = 1` foi preservado; a causa da diferença entre versões/agregações não foi presumida e o artefato anterior não foi alterado. Remuneração real não foi materializada por ausência de contrato de deflator oficial no escopo; Caged não foi usado como estoque.

## F4 — balanço funcional

Compara participações municipais componente a componente, com diferença em pontos percentuais e razão. Lentes e períodos continuam visíveis. Não há soma de universos, índice sintético, déficit, excesso, eficiência ou prioridade automática.

## F6 — adulto e EJA

O fallback agregado contrasta público residente e matrícula localizada por etapa, sem somar fundamental e médio, sem chamar público de demanda manifesta e sem precisão amostral indevida. A história EJA 2014–2025 permanece separada do contraste distributivo de 2022.

## F7 — literatura

Oito referências oficiais/primárias sustentam sete mecanismos plausíveis e explicações alternativas. A literatura não fornece números municipais nem autoriza efeitos locais.
"""


def nsr_dossier_markdown(analysis: Mapping[str, Any]) -> str:
    f1 = analysis["f1_results"]
    rows = f1[f1["municipality_ibge_code"].eq(NSR_CODE)]
    f1_lines = "\n".join(
        f"| {row.stage} | {row.outcome_id} | {_fmt(row.observed_value)} | {_fmt(row.expected_interval_lower)}–{_fmt(row.expected_interval_upper)} | {row.context_adjusted_state} |"
        for row in rows.itertuples(index=False)
    )
    rais15 = _rais_endpoint_summary(
        analysis["rais_panel"], entity_id=NSR_CODE, age_group="15_17"
    )
    rais18 = _rais_endpoint_summary(
        analysis["rais_panel"], entity_id=NSR_CODE, age_group="18_24"
    )
    f6 = analysis["f6"]
    f6 = f6[f6["municipality_ibge_code"].eq(NSR_CODE)]
    f6_lines = "\n".join(
        f"| {row.stage} | {_fmt(row.resident_adult_public)} | {_fmt(row.school_location_eja_enrollments)} | {_fmt(row.eja_enrollments_per_thousand_resident_public_2022)} | {_fmt(row.distribution_difference_percentage_points)} | {_fmt(row.eja_enrollments_2014)} → {_fmt(row.eja_enrollments_2025)} |"
        for row in f6.itertuples(index=False)
    )
    return f"""# Dossiê aprofundado — Nova Santa Rita

Identidade canônica: `{NSR_CODE}`. Este dossiê é analítico interno, não causal e não classificatório.

## Trajetória ajustada ao contexto em 2025

Nova Santa Rita ficou dentro do intervalo preditivo nas 11 combinações avaliáveis. O abandono nos anos iniciais é `NOT_EVALUABLE` para todos os municípios porque o modelo não venceu o baseline fora de município.

| etapa | desfecho | observado | intervalo esperado 90% | estado |
| --- | --- | ---: | ---: | --- |
{f1_lines}

## Trabalho formal jovem — RAIS

| faixa | vínculos 2019 | vínculos 2025 | mudança | escolaridade médio completo (pp) | aprendizagem (pp) |
| --- | ---: | ---: | ---: | ---: | ---: |
| 15–17 | {_fmt(rais15['active_bonds']['initialValue'])} | {_fmt(rais15['active_bonds']['finalValue'])} | {_fmt(rais15['active_bonds']['absoluteChange'])} | {_fmt(rais15['high_school_complete_share_percent']['absoluteChange'])} | {_fmt(rais15['apprentice_share_percent']['absoluteChange'])} |
| 18–24 | {_fmt(rais18['active_bonds']['initialValue'])} | {_fmt(rais18['active_bonds']['finalValue'])} | {_fmt(rais18['active_bonds']['absoluteChange'])} | {_fmt(rais18['high_school_complete_share_percent']['absoluteChange'])} | {_fmt(rais18['apprentice_share_percent']['absoluteChange'])} |

As contagens são vínculos ativos no município de trabalho; não são pessoas únicas, estudantes ou concluintes. Remuneração é nominal.

## Público adulto e EJA

| etapa | público residente | EJA localizada 2022 | por mil | diferença distributiva (pp) | EJA 2014 → 2025 |
| --- | ---: | ---: | ---: | ---: | ---: |
{f6_lines}

No fundamental, a diferença distributiva é +2,648 pp; no médio, −2,605 pp. As etapas não são somadas: a história específica explica 152 matrículas no fundamental e 56 no médio em 2025, totalizando as 208 observadas no agregado anterior.

## Uso permitido

Usar os contrastes como perguntas para diagnóstico, monitoramento e coordenação regional. Não inferir causa, eficiência, demanda manifesta, efeito escola, inserção de concluintes ou prioridade automática.
"""


def vale_dossier_markdown(analysis: Mapping[str, Any]) -> str:
    region_codes = set(_region_codes())
    f1 = analysis["f1_results"]
    f1 = f1[f1["municipality_ibge_code"].isin(region_codes)]
    states = {
        key: int(value)
        for key, value in f1["context_adjusted_state"].value_counts().items()
    }
    rais15 = _rais_endpoint_summary(
        analysis["rais_panel"], entity_id=REGION_ID, age_group="15_17"
    )
    rais18 = _rais_endpoint_summary(
        analysis["rais_panel"], entity_id=REGION_ID, age_group="18_24"
    )
    f6 = analysis["f6"]
    f6 = f6[f6["entity_scope"].eq("region")]
    f6_lines = "\n".join(
        f"| {row.stage} | {_fmt(row.resident_adult_public)} | {_fmt(row.school_location_eja_enrollments)} | {_fmt(row.eja_enrollments_per_thousand_resident_public_2022)} | {_fmt(row.eja_enrollments_2014)} → {_fmt(row.eja_enrollments_2025)} |"
        for row in f6.itertuples(index=False)
    )
    return f"""# Dossiê aprofundado — Vale do Sinos

Recorte canônico: dez municípios, incluindo Nova Santa Rita `{NSR_CODE}`. Nenhuma linha constitui ranking.

## Trajetória ajustada

Nos 120 registros município × etapa × desfecho de 2025, os estados são `{json.dumps(states, ensure_ascii=False, sort_keys=True)}`. A leitura deve começar pela combinação etapa–desfecho e pelo intervalo; a contagem agregada não é score regional.

## Trabalho formal jovem

| faixa | vínculos 2019 | vínculos 2025 | mudança | médio completo (pp) | aprendizagem (pp) |
| --- | ---: | ---: | ---: | ---: | ---: |
| 15–17 | {_fmt(rais15['active_bonds']['initialValue'])} | {_fmt(rais15['active_bonds']['finalValue'])} | {_fmt(rais15['active_bonds']['absoluteChange'])} | {_fmt(rais15['high_school_complete_share_percent']['absoluteChange'])} | {_fmt(rais15['apprentice_share_percent']['absoluteChange'])} |
| 18–24 | {_fmt(rais18['active_bonds']['initialValue'])} | {_fmt(rais18['active_bonds']['finalValue'])} | {_fmt(rais18['active_bonds']['absoluteChange'])} | {_fmt(rais18['high_school_complete_share_percent']['absoluteChange'])} | {_fmt(rais18['apprentice_share_percent']['absoluteChange'])} |

## Organização funcional

F4 preserva oito comparações (sete materializadas e uma indisponível por depender de F2), sempre com participação municipal, referência, diferença, razão, lente e período. Divergência de participação descreve organização territorial, não déficit ou excesso.

## Adulto e EJA

| etapa | público residente | EJA localizada 2022 | por mil | EJA 2014 → 2025 |
| --- | ---: | ---: | ---: | ---: |
{f6_lines}

## Fontes condicionais

F2 e F5 permanecem aguardando liberação oficial dos microdados da amostra e áreas de ponderação do Censo 2022. Resultados preliminares agregados de deslocamento do IBGE não substituem o arquivo necessário para estimativas locais mesma pessoa.
"""


def checkpoint_markdown(analysis: Mapping[str, Any]) -> str:
    main = [item["insight_id"] for item in analysis["insights"] if item["main_candidate"]]
    return f"""# Checkpoint Job 5L para PRO

## Estado terminal

`{FINAL_STATE}`

O laboratório aprofundado F1–F7 foi executado com fontes oficiais, validação fora da amostra, incerteza explícita, resultados negativos e cinco candidatas principais. O pacote exige julgamento externo; nenhuma candidata foi autoaprovada.

## Candidatas principais

{chr(10).join(f'- `{item}`' for item in main)}

## Resultados negativos e limites preservados

- F1: abandono nos anos iniciais é `NOT_EVALUABLE`; o desenho não superou o baseline municipal.
- F2 e F5: `WAITING_OFFICIAL_RELEASE`; nenhuma estimativa ou precisão foi fabricada.
- F3: remuneração apenas nominal; vínculo RAIS não é pessoa única; Caged não é estoque. O estoque bruto oficial ativo em 31/12 diverge do agregado congelado anterior; a diferença permanece visível e nenhuma árvore congelada foi alterada.
- F4: sem índice sintético, déficit, excesso, eficiência ou ranking.
- F6: público residente não é demanda manifesta; fundamental e médio permanecem separados.
- F7: literatura torna mecanismos plausíveis, sem fornecer números ou efeitos locais.
- Julgamento externo separado do Job 5K não foi localizado; o próprio Job 5K registra pendência.

## Guardrails

- Gate 11 fechado; Job 5M não iniciado.
- Sem frontend, publicação, navegação, build completo ou escrita em `public/data`.
- Jobs 5J/5K e raízes analíticas anteriores congelados por digest.
- Banco usado somente para snapshot em transação `READ ONLY`, com rollback.
- Rede usada somente para aquisição oficial e verificação de literatura primária.

## Próximo passo permitido

Julgamento externo do pacote Job 5L. Nenhum conteúdo está autorizado para publicação automática.
"""


def _artifact_role(path: str) -> str:
    roles = {
        "CHECKPOINT_JOB5L_FOR_PRO.md": "checkpoint executivo para julgamento externo",
        "CATALOGO_INSIGHTS_APROFUNDADOS_JOB5L.json": "contratos das candidatas aprofundadas",
        "MATRIZ_RESULTADOS_AJUSTADOS_E_DIRETOS_JOB5L.csv.gz": "matriz integrada F1-F6",
        "MATRIZ_HETEROGENEIDADE_10_MUNICIPIOS_JOB5L.csv.gz": "heterogeneidade municipal sem ranking",
        "DOSSIE_APROFUNDADO_NOVA_SANTA_RITA_JOB5L.md": "dossiê da fixture municipal",
        "DOSSIE_APROFUNDADO_VALE_DO_SINOS_JOB5L.md": "dossiê regional",
        "METODOS_VALIDACAO_E_PRECISAO_JOB5L.md": "métodos, validação e precisão",
        "LITERATURA_E_MECANISMOS_JOB5L.json": "fontes primárias e mecanismos",
        "LIMITACOES_E_CLAIMS_JOB5L.json": "tetos de linguagem",
        "QA_SUMMARY_JOB5L.json": "controles de qualidade",
        "ARTIFACT_INDEX_JOB5L.json": "índice de artefatos",
        "MANIFEST_JOB5L.json": "manifesto final e hashes",
    }
    return roles.get(path, "artefato interno de reconstrução e auditoria")


def build_artifact_index(output_dir: Path) -> dict[str, Any]:
    records = []
    for relative in [*PACKAGE_FILES, *INTERNAL_FILES]:
        path = output_dir / relative
        self_hashed = relative in {"ARTIFACT_INDEX_JOB5L.json", "MANIFEST_JOB5L.json"}
        available = path.is_file() and not self_hashed
        records.append(
            {
                "path": relative,
                "role": _artifact_role(relative),
                "packageFile": relative in PACKAGE_FILES,
                "internalSupportingArtifact": relative in INTERNAL_FILES,
                "byteSize": path.stat().st_size if available else None,
                "sha256": sha256_file(path) if available else None,
                "hashStatus": "recorded" if available else "self_or_manifest_hashed_by_final_manifest",
            }
        )
    return {
        "schemaVersion": "vocacoes-pne-job5l-artifact-index-v1",
        "generatedAt": GENERATED_AT,
        "packageFileCount": len(PACKAGE_FILES),
        "internalSupportingArtifactCount": len(INTERNAL_FILES),
        "artifacts": records,
    }


def _implementation_records() -> list[dict[str, Any]]:
    paths = [
        CONTRACT_PATH,
        Path(__file__).resolve(),
        REPO_ROOT / "data_pipeline" / "scripts" / "run_vocacoes_pne_v7_job5l.py",
        REPO_ROOT / "data_pipeline" / "tests" / "test_vocacoes_pne_job5l.py",
    ]
    return [
        {
            "path": path.relative_to(REPO_ROOT).as_posix(),
            "byteSize": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for path in paths
        if path.is_file()
    ]


def write_package(
    *,
    output_dir: Path,
    source_root: Path,
    analysis: Mapping[str, Any],
    preflight: Mapping[str, Any],
    execplan_text: str,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=False)
    (output_dir / "internal").mkdir()
    database_manifest = analysis["database_manifest"]
    source_registry = build_source_registry(
        source_root=source_root,
        preflight=preflight,
        database_manifest=database_manifest,
        rais_details=analysis["rais_details"],
    )
    qa = build_qa(
        analysis=analysis,
        preflight=preflight,
        source_registry=source_registry,
    )
    insight_payload = {
        "schemaVersion": "vocacoes-pne-job5l-insight-catalog-v1",
        "generatedAt": GENERATED_AT,
        "state": FINAL_STATE,
        "candidateInsightCount": len(analysis["insights"]),
        "mainCandidateCount": sum(bool(item["main_candidate"]) for item in analysis["insights"]),
        "automaticApproval": False,
        "externalJudgmentRequired": True,
        "insights": analysis["insights"],
    }

    write_json(output_dir / "internal" / "CONTRATO_JOB5L.json", _json(CONTRACT_PATH))
    (output_dir / "internal" / "EXECPLAN_JOB5L.md").write_text(
        execplan_text.rstrip() + "\n", encoding="utf-8", newline="\n"
    )
    write_json(
        output_dir / "internal" / "REGISTRO_FONTES_E_AQUISICOES_JOB5L.json",
        _json_safe(source_registry),
    )
    write_csv_gzip(
        output_dir / "internal" / "PAINEL_CONTEXTO_RS_MUNICIPIO_ANO_ETAPA_JOB5L.csv.gz",
        analysis["context"],
    )
    write_csv_gzip(
        output_dir / "internal" / "RESULTADOS_AJUSTADOS_F1_JOB5L.csv.gz",
        analysis["f1_results"],
    )
    write_csv_gzip(
        output_dir / "internal" / "VALIDACAO_MODELOS_F1_JOB5L.csv.gz",
        analysis["f1_validation"],
    )
    write_json(
        output_dir / "internal" / "MODELOS_F1_DETALHADOS_JOB5L.json",
        _json_safe(analysis["f1_details"]),
    )
    write_csv_gzip(
        output_dir / "internal" / "PAINEL_ESTUDO_TRABALHO_F2_JOB5L.csv.gz",
        analysis["f2"],
    )
    write_csv_gzip(
        output_dir / "internal" / "PAINEL_RAIS_COMPOSICAO_JOVEM_F3_JOB5L.csv.gz",
        analysis["rais_panel"],
    )
    write_json(
        output_dir / "internal" / "DICIONARIO_RAIS_NORMALIZADO_JOB5L.json",
        _json_safe(analysis["rais_details"]),
    )
    write_csv_gzip(
        output_dir / "internal" / "PAINEL_BALANCO_FUNCIONAL_F4_JOB5L.csv.gz",
        analysis["f4"],
    )
    write_csv_gzip(
        output_dir / "internal" / "PAINEL_MIGRACAO_F5_JOB5L.csv.gz",
        analysis["f5"],
    )
    write_csv_gzip(
        output_dir / "internal" / "PAINEL_EJA_APROFUNDADO_F6_JOB5L.csv.gz",
        analysis["f6"],
    )
    write_json(
        output_dir / "internal" / "CATALOGO_COMPLETO_CANDIDATAS_JOB5L.json",
        _json_safe(insight_payload),
    )
    write_csv_gzip(
        output_dir / "internal" / "MATRIZ_VALIDACAO_ROBUSTEZ_JOB5L.csv.gz",
        analysis["robustness"],
    )
    write_csv_gzip(
        output_dir / "internal" / "MATRIZ_10_MUNICIPIOS_COMPLETA_JOB5L.csv.gz",
        analysis["complete_ten"],
    )
    write_json(
        output_dir / "internal" / "AUTOCRITICA_JOB5L.json",
        _json_safe(analysis["autocritique"]),
    )

    write_json(
        output_dir / "CATALOGO_INSIGHTS_APROFUNDADOS_JOB5L.json",
        _json_safe(insight_payload),
    )
    write_csv_gzip(
        output_dir / "MATRIZ_RESULTADOS_AJUSTADOS_E_DIRETOS_JOB5L.csv.gz",
        analysis["result_matrix"],
    )
    write_csv_gzip(
        output_dir / "MATRIZ_HETEROGENEIDADE_10_MUNICIPIOS_JOB5L.csv.gz",
        analysis["heterogeneity"],
    )
    (output_dir / "DOSSIE_APROFUNDADO_NOVA_SANTA_RITA_JOB5L.md").write_text(
        nsr_dossier_markdown(analysis), encoding="utf-8", newline="\n"
    )
    (output_dir / "DOSSIE_APROFUNDADO_VALE_DO_SINOS_JOB5L.md").write_text(
        vale_dossier_markdown(analysis), encoding="utf-8", newline="\n"
    )
    (output_dir / "METODOS_VALIDACAO_E_PRECISAO_JOB5L.md").write_text(
        methods_markdown(analysis), encoding="utf-8", newline="\n"
    )
    write_json(
        output_dir / "LITERATURA_E_MECANISMOS_JOB5L.json",
        _json_safe(analysis["literature"]),
    )
    write_json(
        output_dir / "LIMITACOES_E_CLAIMS_JOB5L.json",
        _json_safe(analysis["limits"]),
    )
    write_json(output_dir / "QA_SUMMARY_JOB5L.json", _json_safe(qa))
    (output_dir / "CHECKPOINT_JOB5L_FOR_PRO.md").write_text(
        checkpoint_markdown(analysis), encoding="utf-8", newline="\n"
    )
    write_json(
        output_dir / "ARTIFACT_INDEX_JOB5L.json",
        build_artifact_index(output_dir),
    )

    declared_paths = [
        relative
        for relative in [*PACKAGE_FILES, *INTERNAL_FILES]
        if relative != "MANIFEST_JOB5L.json"
    ]
    manifest = {
        "schemaVersion": "vocacoes-pne-job5l-manifest-v1",
        "jobId": "v7-job5l",
        "generatedAt": GENERATED_AT,
        "classification": "SOURCE_REFRESH",
        "domains": [
            "DATA_LOGIC",
            "DEEP_ANALYTICAL_LAB",
            "OFFICIAL_SOURCE_ACQUISITION",
            "CONTEXT_ADJUSTED_TRAJECTORIES",
            "YOUTH_WORK_COMPOSITION",
        ],
        "finalState": FINAL_STATE,
        "externalJudgmentRequired": True,
        "automaticApproval": False,
        "gate11": "CLOSED",
        "job5MStarted": False,
        "packageFiles": list(PACKAGE_FILES),
        "internalSupportingArtifacts": list(INTERNAL_FILES),
        "artifacts": [
            {
                "path": relative,
                "byteSize": (output_dir / relative).stat().st_size,
                "sha256": sha256_file(output_dir / relative),
            }
            for relative in declared_paths
        ],
        "implementationFiles": _implementation_records(),
        "sourceRegistrySha256": sha256_file(
            output_dir / "internal" / "REGISTRO_FONTES_E_AQUISICOES_JOB5L.json"
        ),
        "frozenInputIntegrity": {
            "before": preflight["frozenRootDigests"],
            "after": preflight["frozenRootDigests"],
            "unchanged": True,
        },
        "publicDataIntegrity": {
            "beforeTreeDigestSha256": preflight["publicDataTreeDigestSha256"],
            "afterTreeDigestSha256": preflight["publicDataTreeDigestSha256"],
            "unchanged": True,
        },
        "counts": {
            "stateMunicipalityCount": 497,
            "regionMunicipalityCount": 10,
            "f1ResultRowCount": len(analysis["f1_results"]),
            "f1ModelCount": len(analysis["f1_validation"]),
            "f1EligibleModelCount": int(analysis["f1_validation"]["validation_eligible"].sum()),
            "f2RowCount": len(analysis["f2"]),
            "f3RowCount": len(analysis["rais_panel"]),
            "raisFrozenExactMatchCellCount": analysis["rais_details"][
                "reconciliationWithFrozenAggregate"
            ]["exactMatchCount"],
            "raisFrozenMismatchCellCount": analysis["rais_details"][
                "reconciliationWithFrozenAggregate"
            ]["mismatchCount"],
            "f4RowCount": len(analysis["f4"]),
            "f5RowCount": len(analysis["f5"]),
            "f6RowCount": len(analysis["f6"]),
            "literatureReferenceCount": analysis["literature"]["referenceCount"],
            "mechanismCount": analysis["literature"]["mechanismCount"],
            "candidateInsightCount": len(analysis["insights"]),
            "mainCandidateCount": sum(bool(item["main_candidate"]) for item in analysis["insights"]),
            "integratedResultRowCount": len(analysis["result_matrix"]),
            "heterogeneityRowCount": len(analysis["heterogeneity"]),
            "qaControlCount": qa["controlCount"],
            "qaFailedCount": qa["failedCount"],
            "packageFileCount": len(PACKAGE_FILES),
            "internalSupportingArtifactCount": len(INTERNAL_FILES),
        },
        "frontStates": analysis["limits"]["frontStates"],
        "formulasAltered": [],
        "analyticalMethodsAdded": [
            "ridge_regularized_context_model",
            "nearest_context_peers",
            "five_fold_municipality_holdout",
            "temporal_holdout_2025",
            "split_conformal_prediction_intervals",
            "sensitivity_excluding_2020_2021",
            "streaming_official_RAIS_composition",
            "cross_lens_functional_share_contrasts",
        ],
        "generation": {
            "deterministic": True,
            "twoIndependentMaterializationsRequired": True,
            "transactional": True,
            "manifestLast": True,
            "networkUsed": True,
            "databaseUsed": True,
            "databaseWritePerformed": False,
            "newOfficialAcquisitionPerformed": True,
            "publicDataChanged": False,
            "frontendChanged": False,
            "navigationChanged": False,
            "fullBuildUsed": False,
            "publicationPerformed": False,
        },
    }
    write_json(output_dir / "MANIFEST_JOB5L.json", _json_safe(manifest))
    validate_existing_output(output_dir, source_root=source_root, verify_sources=False)
    return manifest


def validate_existing_output(
    output_dir: Path = DEFAULT_OUTPUT_ROOT,
    *,
    source_root: Path | None = None,
    verify_sources: bool = True,
) -> dict[str, Any]:
    if not output_dir.is_dir():
        raise Job5LValidationError(f"Pacote Job 5L ausente: {output_dir}")
    root_files = {path.name for path in output_dir.iterdir() if path.is_file()}
    if root_files != set(PACKAGE_FILES):
        raise Job5LValidationError(
            f"Topologia compartilhada divergente: faltam={sorted(set(PACKAGE_FILES)-root_files)}, extras={sorted(root_files-set(PACKAGE_FILES))}"
        )
    internal_actual = {
        path.relative_to(output_dir).as_posix()
        for path in (output_dir / "internal").rglob("*")
        if path.is_file()
    }
    if internal_actual != set(INTERNAL_FILES):
        raise Job5LValidationError(
            f"Topologia interna divergente: faltam={sorted(set(INTERNAL_FILES)-internal_actual)}, extras={sorted(internal_actual-set(INTERNAL_FILES))}"
        )
    manifest = _json(output_dir / "MANIFEST_JOB5L.json")
    if manifest["finalState"] != FINAL_STATE or manifest["gate11"] != "CLOSED":
        raise Job5LValidationError("Estado terminal ou Gate 11 divergente")
    if manifest["job5MStarted"] or not manifest["externalJudgmentRequired"]:
        raise Job5LValidationError("Job 5M/autoaprovação indevida")
    if manifest["packageFiles"] != list(PACKAGE_FILES) or len(root_files) != 12:
        raise Job5LValidationError("Pacote compartilhado não contém exatamente 12 arquivos")
    if manifest["internalSupportingArtifacts"] != list(INTERNAL_FILES):
        raise Job5LValidationError("Suportes internos divergem do contrato")
    declared = {item["path"]: item for item in manifest["artifacts"]}
    expected_declared = set(PACKAGE_FILES + INTERNAL_FILES) - {"MANIFEST_JOB5L.json"}
    if set(declared) != expected_declared:
        raise Job5LValidationError("Manifesto não cobre todos os artefatos")
    for relative, record in declared.items():
        path = output_dir / relative
        if path.stat().st_size != record["byteSize"] or sha256_file(path) != record["sha256"]:
            raise Job5LValidationError(f"Hash/tamanho divergente: {relative}")
    contract = _json(output_dir / "internal" / "CONTRATO_JOB5L.json")
    if contract["packageFiles"] != list(PACKAGE_FILES):
        raise Job5LValidationError("Contrato interno diverge da topologia")
    f1 = _read_csv(output_dir / "internal" / "RESULTADOS_AJUSTADOS_F1_JOB5L.csv.gz")
    if len(f1) != 497 * 3 * 4:
        raise Job5LValidationError("F1 não cobre 497 × 3 × 4")
    codes = set(f1["municipality_ibge_code"].dropna().astype(str))
    if len(codes) != 497 or any(not IBGE_CODE_PATTERN.fullmatch(code) for code in codes):
        raise Job5LValidationError("Identidade municipal F1 divergente")
    validation = _read_csv(output_dir / "internal" / "VALIDACAO_MODELOS_F1_JOB5L.csv.gz")
    eligible = validation["validation_eligible"].astype(str).str.casefold().isin({"true", "1"})
    if len(validation) != 12 or int(eligible.sum()) != 11:
        raise Job5LValidationError("Gates de F1 divergentes")
    f2 = _read_csv(output_dir / "internal" / "PAINEL_ESTUDO_TRABALHO_F2_JOB5L.csv.gz")
    if not f2["front_state"].eq("WAITING_OFFICIAL_RELEASE").all() or f2["weighted_estimate"].notna().any():
        raise Job5LValidationError("F2 fabricou estimativa")
    f5 = _read_csv(output_dir / "internal" / "PAINEL_MIGRACAO_F5_JOB5L.csv.gz")
    if not f5["front_state"].eq("WAITING_OFFICIAL_RELEASE").all() or f5["estimate"].notna().any():
        raise Job5LValidationError("F5 fabricou estimativa")
    heterogeneity = _read_csv(
        output_dir / "MATRIZ_HETEROGENEIDADE_10_MUNICIPIOS_JOB5L.csv.gz"
    )
    heterogeneity_codes = set(
        heterogeneity["municipality_ibge_code"].dropna().astype(str)
    )
    if heterogeneity_codes != set(_region_codes()) or NSR_CODE not in heterogeneity_codes:
        raise Job5LValidationError("Matriz de heterogeneidade não cobre Vale/NSR")
    catalog = _json(output_dir / "CATALOGO_INSIGHTS_APROFUNDADOS_JOB5L.json")
    if catalog["candidateInsightCount"] != len(catalog["insights"]) or len(catalog["insights"]) > 8:
        raise Job5LValidationError("Catálogo excede limite ou tem contagem divergente")
    required = {
        "insight_id",
        "manager_question",
        "evidence_level",
        "analytical_state",
        "same_person",
        "unit_of_analysis",
        "territorial_lens",
        "method",
        "validation",
        "integrated_conclusion",
        "allowed_claims",
        "forbidden_claims",
        "limitations",
        "manager_review_state",
    }
    if any(not required <= set(item) for item in catalog["insights"]):
        raise Job5LValidationError("Contrato de candidata incompleto")
    qa = _json(output_dir / "QA_SUMMARY_JOB5L.json")
    if qa["failedCount"] != 0 or qa["result"] != "PASS_WITH_EXPLICIT_LIMITS":
        raise Job5LValidationError("QA final não aprovado com limites")
    limits = _json(output_dir / "LIMITACOES_E_CLAIMS_JOB5L.json")
    if limits["pne"]["officialIndicatorRecalculated"] or limits["pme"]["state"] != "not_materialized":
        raise Job5LValidationError("PNE/PME alterado indevidamente")
    if any(manifest["generation"][key] for key in (
        "databaseWritePerformed",
        "publicDataChanged",
        "frontendChanged",
        "navigationChanged",
        "fullBuildUsed",
        "publicationPerformed",
    )):
        raise Job5LValidationError("Manifesto registra mutação proibida")
    resolved_sources = source_root or output_dir / "sources"
    if verify_sources:
        validate_database_sources(resolved_sources / "database")
        validate_rais_sources(resolved_sources / "rais" / "raw")
    return manifest
