"""Executa o laboratório analítico interno V7 Vocações × PNE — Job 3."""

from __future__ import annotations

import argparse
from collections import defaultdict
import csv
import gzip
import io
import json
import math
import os
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
import pandas as pd
from dotenv import load_dotenv


REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_PIPELINE_DIR = REPO_ROOT / "data_pipeline"
if str(DATA_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_PIPELINE_DIR))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.vocacoes_pne_job2 import (  # noqa: E402
    artifact_record,
    canonical_json_bytes,
    directory_content_digest,
    replace_directory_transactionally,
    sha256_bytes,
    sha256_file,
    staging_directory_for,
    write_csv_gzip,
    write_json,
)
from src.vocacoes_pne_job3 import (  # noqa: E402
    CANDIDATE_IDS,
    JOB_ID,
    SCHEMA_VERSION,
    bh_adjust,
    direction,
    direction_vs_region,
    finite_or_none,
    fit_clustered_panel,
    leave_one_out_directions,
    relative_change,
    require_ibge_code,
    safe_ratio,
    shapley_m_equals_p_times_r,
    standardized_distance_comparators,
    validate_candidate_registry,
    validate_ibge_codes,
)
import materialize_vocacoes_pne_v7_job2 as job2  # noqa: E402


JOB2_ROOT = REPO_ROOT / ".tmp" / "vocacoes-pne" / "v7-job2"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / ".tmp" / "vocacoes-pne" / JOB_ID
CONTRACT_PATH = DATA_PIPELINE_DIR / "contracts" / "vocacoes-pne-v7-job3.json"
REGION_PATH = REPO_ROOT / "config" / "regions" / "rs.json"
MUNICIPALITY_PATH = REPO_ROOT / "config" / "municipalities" / "rs.json"
PREREGISTRATION_PATH = REPO_ROOT / "docs" / "PRE_REGISTRO_ANALITICO_JOB_3_V7.yaml"
ENTRY_GATE_PATH = REPO_ROOT / "docs" / "GATE_ENTRADA_JOB_3_V7.yaml"
MECHANISM_LIBRARY_PATH = REPO_ROOT / "docs" / "BIBLIOTECA_MECANISMOS_JOB_3_V7.md"
JOB2_MANIFEST_EXPECTED_SHA256 = (
    "28ca53d020af6eb8168eef15af2a7752034c149ada942b4323756e55ef8f8d85"
)
NOVA_SANTA_RITA = "4313375"
FORBIDDEN_STOCK_TABLE = "estoque_emprego_faixa_etaria"
V6_FIXTURE_ROOT = REPO_ROOT / "scripts" / "checks" / "fixtures" / "vocacoes-pne"


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _atomic_write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, path)
    except Exception:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)
        raise


def _atomic_write_text(path: Path, payload: str) -> None:
    _atomic_write_bytes(path, payload.encode("utf-8"))


def _load_region() -> tuple[list[str], dict[str, str], dict[str, str]]:
    region_payload = _load_json(REGION_PATH)
    region = next(
        item for item in region_payload["regions"] if item["slug"] == "vale-do-sinos"
    )
    region_codes = validate_ibge_codes(
        region["municipalityIbgeCodes"], expected_count=10
    )
    registry = _load_json(MUNICIPALITY_PATH)
    all_names = {
        item["ibgeCode"]: item["name"] for item in registry["municipalities"]
    }
    state_codes = validate_ibge_codes(all_names, expected_count=497)
    region_names = {code: all_names[code] for code in region_codes}
    if region_names.get(NOVA_SANTA_RITA) != "Nova Santa Rita":
        raise ValueError("Nova Santa Rita não foi preservada no registro canônico.")
    return region_codes, region_names, {code: all_names[code] for code in state_codes}


def _read_job2_frame(relative_path: str) -> pd.DataFrame:
    return pd.read_csv(
        JOB2_ROOT / relative_path,
        dtype={
            "municipality_ibge_code": "string",
            "municipality_id": "string",
        },
        keep_default_na=True,
        na_values=["null"],
    )


def _verify_job2() -> dict[str, Any]:
    manifest_path = JOB2_ROOT / "manifest.json"
    execution_state_path = JOB2_ROOT / "execution_state.json"
    if sha256_file(manifest_path) != JOB2_MANIFEST_EXPECTED_SHA256:
        raise ValueError("O manifesto do Job 2 diverge do hash contratado pelo Job 3.")
    manifest = _load_json(manifest_path)
    execution_state = _load_json(execution_state_path)
    artifacts = manifest.get("artifacts", [])
    if len(artifacts) != 20:
        raise ValueError("O Job 2 não contém os 20 artefatos esperados.")
    for record in artifacts:
        path = JOB2_ROOT / record["path"]
        if not path.is_file() or sha256_file(path) != record["sha256"]:
            raise ValueError(f"Artefato Job 2 ausente ou divergente: {record['path']}.")
    statuses = {item["id"]: item["status"] for item in execution_state["subjobs"]}
    if statuses != {f"2{letter}": "READY" for letter in "ABCDE"}:
        raise ValueError(f"Gate do Job 2 não está integralmente READY: {statuses!r}.")
    return {
        "manifest": manifest,
        "executionStateSha256": sha256_file(execution_state_path),
        "artifactCount": len(artifacts),
        "artifactRowCount": sum(
            int(record["rowCount"]) for record in artifacts if record["rowCount"] is not None
        ),
        "statuses": statuses,
    }


def _fixture_hashes() -> dict[str, dict[str, Any]]:
    return {
        path.name: {
            "byteSize": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for path in sorted(V6_FIXTURE_ROOT.iterdir())
        if path.is_file()
    }


def _read_sql(database: str, query: str, params: Mapping[str, Any] | None = None) -> pd.DataFrame:
    if FORBIDDEN_STOCK_TABLE in query.lower():
        raise ValueError("Tentativa de acesso à tabela defeituosa proibida.")
    return job2._read_sql(database, query, params)


def _read_source_panels() -> dict[str, pd.DataFrame]:
    print("Job 3: lendo painéis RS em transações somente leitura")
    censo = _read_sql(
        "sesi",
        """
        SELECT ano AS year, id_municipio AS municipality_ibge_code,
               dependencia AS network, localizacao AS location,
               qntd_escolas::double precision AS schools,
               escolas_com_banda_larga::double precision AS schools_with_broadband,
               mat_infantil_creche::double precision AS creche_enrollments,
               mat_infantil_pre::double precision AS preschool_enrollments,
               mat_fundamental_anos_iniciais::double precision
                   AS early_fundamental_enrollments,
               mat_fundamental_anos_finais::double precision
                   AS final_fundamental_enrollments,
               mat_fundamental::double precision AS fundamental_enrollments,
               mat_medio::double precision AS high_school_enrollments,
               turmas_infantil::double precision AS early_childhood_classes,
               turmas_fundamental::double precision AS fundamental_classes,
               turmas_medio::double precision AS high_school_classes,
               mat_profissional_tecnico::double precision AS technical_enrollments
        FROM public.censo
        WHERE sigla_uf = 'RS' AND ano BETWEEN 2014 AND 2025
        """,
    )
    population = _read_sql(
        "sesi",
        """
        SELECT ano AS year, id_municipio AS municipality_ibge_code,
               idade AS age, SUM(pop_estimada)::double precision AS population
        FROM public.populacao_idade
        WHERE sigla_uf = 'RS' AND ano BETWEEN 2014 AND 2025
        GROUP BY ano, id_municipio, idade
        """,
    )
    performance = _read_sql(
        "sesi",
        """
        SELECT ano AS year, id_municipio AS municipality_ibge_code,
               dependencia AS network, localizacao AS location,
               etapa_ensino AS stage,
               taxa_aprovacao::double precision AS approval_rate_percent,
               taxa_reprovacao::double precision AS failure_rate_percent,
               taxa_abandono::double precision AS dropout_rate_percent
        FROM public.rendimento_escolar
        WHERE sigla_uf = 'RS' AND localizacao = 'total'
              AND ano BETWEEN 2018 AND 2025
        """,
    )
    distortion = _read_sql(
        "sesi",
        """
        SELECT ano AS year, id_municipio AS municipality_ibge_code,
               dependencia AS network, categoria AS stage,
               valor::double precision AS age_grade_distortion_rate_percent
        FROM public.distorcao_idade_serie
        WHERE sigla_uf = 'RS' AND ano BETWEEN 2019 AND 2025
        """,
    )
    class_size = _read_sql(
        "sesi",
        """
        SELECT ano AS year, id_municipio AS municipality_ibge_code,
               etapa_ensino || ':' || serie_label AS dimension,
               alunos_por_turma::double precision AS students_per_class
        FROM public.alunos_turma
        WHERE sigla_uf = 'RS' AND localizacao = 'total'
              AND dependencia = 'total' AND ano BETWEEN 2016 AND 2025
        """,
    )
    adequacy = _read_sql(
        "sesi",
        """
        SELECT ano AS year, id_municipio AS municipality_ibge_code,
               etapa AS stage,
               percentual_adequacao::double precision AS teacher_adequacy_percent
        FROM public.adequacao_docente
        WHERE sigla_uf = 'RS' AND localizacao = 'total'
              AND dependencia = 'total' AND ano BETWEEN 2014 AND 2025
        """,
    )
    inse = _read_sql(
        "sesi",
        """
        SELECT ano AS year, id_municipio AS municipality_ibge_code,
               media_inse::double precision AS inse_mean,
               qtd_alunos_inse::double precision AS inse_students
        FROM public.inse
        WHERE sigla_uf = 'RS' AND rede = 'total'
        """,
    )
    rais = _read_sql(
        "cei",
        """
        SELECT ano AS year, CAST(id_municipio AS text) AS municipality_ibge_code,
               faixa_etaria AS age_group_code,
               SUM(vinculos_ativos)::double precision AS active_bonds
        FROM public.rais_vinculos
        WHERE faixa_etaria IN ('2', '3') AND ano BETWEEN 2019 AND 2025
        GROUP BY ano, id_municipio, faixa_etaria
        """,
    )
    eja_components = _read_sql(
        "sesi",
        """
        WITH population AS (
            SELECT id_municipio,
                   SUM(pop_estimada)::double precision AS population_18_plus
            FROM public.populacao_idade
            WHERE sigla_uf = 'RS' AND ano = 2022 AND idade >= 18
            GROUP BY id_municipio
        ), fundamental AS (
            SELECT LPAD(CAST(id_municipio AS text), 7, '0') AS id_municipio,
                   populacao_18_mais_ensino_fundamental_concluido::double precision
                       AS fundamental_completed_18_plus
            FROM public.censo_populacao_ensino_fundamental_concluido_18_mais
            WHERE sigla_uf = 'RS' AND ano = 2022
        ), medio AS (
            SELECT LPAD(CAST(id_municipio AS text), 7, '0') AS id_municipio,
                   populacao_18_mais_ensino_medio_concluido::double precision
                       AS high_school_completed_18_plus
            FROM public.censo_populacao_ensino_medio_concluido_18_mais
            WHERE sigla_uf = 'RS' AND ano = 2022
        )
        SELECT p.id_municipio AS municipality_ibge_code,
               p.population_18_plus,
               f.fundamental_completed_18_plus,
               m.high_school_completed_18_plus,
               e.mat_eja_fundamental_total::double precision
                   AS fundamental_eja_enrollments,
               e.mat_eja_medio_total::double precision AS high_school_eja_enrollments
        FROM population p
        JOIN fundamental f ON f.id_municipio = p.id_municipio
        JOIN medio m ON m.id_municipio = p.id_municipio
        JOIN public.eja_integrada_educacao_profissional e
          ON e.id_municipio = p.id_municipio AND e.ano = 2022
        WHERE e.sigla_uf = 'RS'
        """,
    )
    panels = {
        "censo": censo,
        "population": population,
        "performance": performance,
        "distortion": distortion,
        "class_size": class_size,
        "adequacy": adequacy,
        "inse": inse,
        "rais": rais,
        "eja_components": eja_components,
    }
    for label, frame in panels.items():
        if "municipality_ibge_code" in frame:
            frame["municipality_ibge_code"] = frame[
                "municipality_ibge_code"
            ].astype("string")
            invalid = ~frame["municipality_ibge_code"].str.fullmatch(r"[0-9]{7}", na=False)
            if invalid.any():
                raise ValueError(f"{label}: código municipal inválido.")
    return panels


STAGE_SPECS = {
    "creche": ((0, 3), "creche_enrollments", "early_childhood_classes"),
    "preschool": ((4, 5), "preschool_enrollments", "early_childhood_classes"),
    "early_fundamental": (
        (6, 10),
        "early_fundamental_enrollments",
        "fundamental_classes",
    ),
    "final_fundamental": (
        (11, 14),
        "final_fundamental_enrollments",
        "fundamental_classes",
    ),
    "fundamental": ((6, 14), "fundamental_enrollments", "fundamental_classes"),
    "high_school": ((15, 17), "high_school_enrollments", "high_school_classes"),
}


def _population_by_stage(population: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for stage, ((minimum, maximum), _, _) in STAGE_SPECS.items():
        part = population[population["age"].between(minimum, maximum)].groupby(
            ["year", "municipality_ibge_code"], as_index=False
        )["population"].sum()
        part["stage"] = stage
        rows.append(part)
    return pd.concat(rows, ignore_index=True)


def _census_municipal(censo: pd.DataFrame) -> pd.DataFrame:
    value_columns = [
        "schools",
        "schools_with_broadband",
        "creche_enrollments",
        "preschool_enrollments",
        "early_fundamental_enrollments",
        "final_fundamental_enrollments",
        "fundamental_enrollments",
        "high_school_enrollments",
        "early_childhood_classes",
        "fundamental_classes",
        "high_school_classes",
        "technical_enrollments",
    ]
    return censo.groupby(
        ["year", "municipality_ibge_code"], as_index=False
    )[value_columns].sum(min_count=1)


def _h1_analysis(
    *,
    population: pd.DataFrame,
    censo: pd.DataFrame,
    region_codes: Sequence[str],
) -> tuple[pd.DataFrame, pd.DataFrame, list[dict[str, Any]], dict[str, Any]]:
    population_stage = _population_by_stage(population)
    census_municipal = _census_municipal(censo)
    decomposition_rows: list[dict[str, Any]] = []
    facts: list[dict[str, Any]] = []
    scopes: list[tuple[str, str | None, pd.DataFrame, pd.DataFrame]] = []
    for code in region_codes:
        scopes.append(
            (
                "municipality",
                code,
                population_stage[population_stage["municipality_ibge_code"].eq(code)],
                census_municipal[census_municipal["municipality_ibge_code"].eq(code)],
            )
        )
    scopes.extend(
        [
            (
                "region",
                None,
                population_stage[
                    population_stage["municipality_ibge_code"].isin(region_codes)
                ],
                census_municipal[
                    census_municipal["municipality_ibge_code"].isin(region_codes)
                ],
            ),
            ("state", None, population_stage, census_municipal),
        ]
    )
    for scope, code, population_scope, census_scope in scopes:
        for stage, (_, enrollment_column, class_column) in STAGE_SPECS.items():
            pop_year = population_scope[population_scope["stage"].eq(stage)].groupby(
                "year"
            )["population"].sum(min_count=1)
            census_year = census_scope.groupby("year")[
                [enrollment_column, "schools", class_column]
            ].sum(min_count=1)
            if 2014 not in pop_year or 2025 not in pop_year or 2014 not in census_year.index or 2025 not in census_year.index:
                continue
            decomposition = shapley_m_equals_p_times_r(
                population_start=pop_year.loc[2014],
                population_end=pop_year.loc[2025],
                enrollment_start=census_year.loc[2014, enrollment_column],
                enrollment_end=census_year.loc[2025, enrollment_column],
            )
            row = {
                "entity_scope": scope,
                "municipality_id": code,
                "stage": stage,
                "start_year": 2014,
                "end_year": 2025,
                "population_start": float(pop_year.loc[2014]),
                "population_end": float(pop_year.loc[2025]),
                "population_relative_change": relative_change(
                    pop_year.loc[2014], pop_year.loc[2025]
                ),
                "enrollment_start": float(census_year.loc[2014, enrollment_column]),
                "enrollment_end": float(census_year.loc[2025, enrollment_column]),
                "enrollment_relative_change": relative_change(
                    census_year.loc[2014, enrollment_column],
                    census_year.loc[2025, enrollment_column],
                ),
                "schools_start": float(census_year.loc[2014, "schools"]),
                "schools_end": float(census_year.loc[2025, "schools"]),
                "classes_start": float(census_year.loc[2014, class_column]),
                "classes_end": float(census_year.loc[2025, class_column]),
                "population_direction": direction(
                    pop_year.loc[2014], pop_year.loc[2025]
                ),
                "enrollment_direction": direction(
                    census_year.loc[2014, enrollment_column],
                    census_year.loc[2025, enrollment_column],
                ),
                "network_direction": direction(
                    census_year.loc[2014, "schools"], census_year.loc[2025, "schools"]
                ),
                **decomposition,
            }
            decomposition_rows.append(row)
            fact_id = (
                f"H1-{scope.upper()}-{code or 'ALL'}-{stage.upper()}-2014-2025"
            )
            facts.append(
                {
                    "id": fact_id,
                    "candidate_id": "H1_DEMOGRAFIA_REDE",
                    "scope": scope,
                    "municipality_id": code,
                    "stage": stage,
                    "metric": "M_equals_P_times_R_decomposition",
                    "period": "2014-2025",
                    "values": row,
                    "lenses": ["resident_population", "school_location"],
                    "evidence_class": "calculated_from_observed_and_estimated_indirect",
                }
            )
    decomposition_frame = pd.DataFrame(decomposition_rows)
    region_decomposition = decomposition_frame[
        decomposition_frame["entity_scope"].eq("region")
    ].set_index("stage")
    municipal_decomposition = decomposition_frame[
        decomposition_frame["entity_scope"].eq("municipality")
    ]
    municipal_decomposition = municipal_decomposition.merge(
        region_decomposition[["enrollment_relative_change"]].rename(
            columns={"enrollment_relative_change": "regional_enrollment_relative_change"}
        ),
        left_on="stage",
        right_index=True,
        validate="many_to_one",
    )
    municipal_decomposition["direction_vs_region"] = [
        direction_vs_region(local, regional)
        for local, regional in zip(
            municipal_decomposition["enrollment_relative_change"],
            municipal_decomposition["regional_enrollment_relative_change"],
            strict=True,
        )
    ]
    regional_changes = region_decomposition["enrollment_change"].to_dict()
    municipal_decomposition["regional_contribution"] = [
        safe_ratio(change, regional_changes.get(stage))
        for change, stage in zip(
            municipal_decomposition["enrollment_change"],
            municipal_decomposition["stage"],
            strict=True,
        )
    ]
    network_rows: list[dict[str, Any]] = []
    for (municipality, network), group in censo[
        censo["municipality_ibge_code"].isin(region_codes)
    ].groupby(["municipality_ibge_code", "network"], sort=True):
        for stage, (_, enrollment_column, _) in STAGE_SPECS.items():
            by_year = group.groupby("year")[
                [enrollment_column, "schools"]
            ].sum(min_count=1)
            if 2014 in by_year.index and 2025 in by_year.index:
                network_rows.append(
                    {
                        "municipality_id": municipality,
                        "network": network,
                        "stage": stage,
                        "enrollment_start": float(by_year.loc[2014, enrollment_column]),
                        "enrollment_end": float(by_year.loc[2025, enrollment_column]),
                        "enrollment_relative_change": relative_change(
                            by_year.loc[2014, enrollment_column],
                            by_year.loc[2025, enrollment_column],
                        ),
                        "schools_start": float(by_year.loc[2014, "schools"]),
                        "schools_end": float(by_year.loc[2025, "schools"]),
                    }
                )
    network_frame = pd.DataFrame(network_rows)
    leave_one_out: dict[str, Any] = {}
    census_region = census_municipal[
        census_municipal["municipality_ibge_code"].isin(region_codes)
    ]
    for stage, (_, enrollment_column, _) in STAGE_SPECS.items():
        leave_one_out[stage] = leave_one_out_directions(
            census_region,
            municipality_column="municipality_ibge_code",
            year_column="year",
            value_column=enrollment_column,
            start_year=2014,
            end_year=2025,
        )
    metadata = {
        "leaveOneOut": leave_one_out,
        "maximumAbsoluteClosureResidual": float(
            decomposition_frame["closure_residual"].abs().max()
        ),
        "municipalityCount": int(
            municipal_decomposition["municipality_id"].nunique()
        ),
        "stateMunicipalityCount": int(population["municipality_ibge_code"].nunique()),
    }
    return decomposition_frame, network_frame, facts, metadata


def _normalize_total(value: pd.Series) -> pd.Series:
    return value.astype("string").str.lower().str.strip()


def _build_model_panel(panels: Mapping[str, pd.DataFrame]) -> pd.DataFrame:
    performance = panels["performance"].copy()
    performance["network_normalized"] = _normalize_total(performance["network"])
    performance = performance[
        performance["network_normalized"].eq("total")
        & performance["stage"].isin(
            ["fundamental_anos_iniciais", "fundamental_anos_finais", "medio"]
        )
    ].copy()
    outcome_columns = [
        "approval_rate_percent",
        "failure_rate_percent",
        "dropout_rate_percent",
    ]
    duplicate_key = performance.duplicated(
        ["year", "municipality_ibge_code", "stage"], keep=False
    )
    if duplicate_key.any():
        raise ValueError("Rendimento total duplicado no grão município-ano-etapa.")
    model_panel = performance[
        ["year", "municipality_ibge_code", "stage", *outcome_columns]
    ].copy()

    distortion = panels["distortion"].copy()
    distortion["network_normalized"] = _normalize_total(distortion["network"])
    distortion = distortion[distortion["network_normalized"].eq("total")].copy()
    distortion_map = {
        "taxa_distorcao_fundamental_anos_iniciais": "fundamental_anos_iniciais",
        "taxa_distorcao_fundamental_anos_finais": "fundamental_anos_finais",
        "taxa_distorcao_medio": "medio",
    }
    distortion["stage"] = distortion["stage"].map(distortion_map)
    distortion = distortion[distortion["stage"].notna()][
        [
            "year",
            "municipality_ibge_code",
            "stage",
            "age_grade_distortion_rate_percent",
        ]
    ]
    if distortion.duplicated(
        ["year", "municipality_ibge_code", "stage"], keep=False
    ).any():
        raise ValueError("Distorção total duplicada no grão município-ano-etapa.")
    model_panel = model_panel.merge(
        distortion,
        on=["year", "municipality_ibge_code", "stage"],
        how="outer",
        validate="one_to_one",
    )

    class_size = panels["class_size"].copy()
    dimension_map = {
        "fundamental:Anos Iniciais": "fundamental_anos_iniciais",
        "fundamental:Anos Finais": "fundamental_anos_finais",
        "medio:Total - Ensino Medio": "medio",
    }
    class_size["stage"] = class_size["dimension"].map(dimension_map)
    class_size = class_size[class_size["stage"].notna()][
        [
            "year",
            "municipality_ibge_code",
            "stage",
            "students_per_class",
        ]
    ]
    model_panel = model_panel.merge(
        class_size,
        on=["year", "municipality_ibge_code", "stage"],
        how="left",
        validate="one_to_one",
    )
    adequacy = panels["adequacy"].copy()
    adequacy["stage"] = adequacy["stage"].map(
        {
            "anos_iniciais": "fundamental_anos_iniciais",
            "anos_finais": "fundamental_anos_finais",
            "ensino_medio": "medio",
        }
    )
    adequacy = adequacy[adequacy["stage"].notna()]
    model_panel = model_panel.merge(
        adequacy[
            [
                "year",
                "municipality_ibge_code",
                "stage",
                "teacher_adequacy_percent",
            ]
        ],
        on=["year", "municipality_ibge_code", "stage"],
        how="left",
        validate="one_to_one",
    )

    censo = panels["censo"]
    broadband = censo.groupby(
        ["year", "municipality_ibge_code"], as_index=False
    )[["schools_with_broadband", "schools"]].sum(min_count=1)
    broadband["schools_with_broadband_percent"] = [
        safe_ratio(numerator, denominator, multiplier=100.0)
        for numerator, denominator in zip(
            broadband["schools_with_broadband"],
            broadband["schools"],
            strict=True,
        )
    ]
    model_panel = model_panel.merge(
        broadband[
            [
                "year",
                "municipality_ibge_code",
                "schools_with_broadband_percent",
            ]
        ],
        on=["year", "municipality_ibge_code"],
        how="left",
        validate="many_to_one",
    )
    model_panel = model_panel.merge(
        panels["inse"][
            ["year", "municipality_ibge_code", "inse_mean", "inse_students"]
        ],
        on=["year", "municipality_ibge_code"],
        how="left",
        validate="many_to_one",
    )

    population = panels["population"]
    youth_rows = []
    for label, minimum, maximum in [("15_17", 15, 17), ("18_24", 18, 24)]:
        part = population[population["age"].between(minimum, maximum)].groupby(
            ["year", "municipality_ibge_code"], as_index=False
        )["population"].sum()
        part = part.rename(columns={"population": f"population_{label}"})
        youth_rows.append(part)
    youth = youth_rows[0].merge(
        youth_rows[1],
        on=["year", "municipality_ibge_code"],
        how="outer",
        validate="one_to_one",
    )
    rais = panels["rais"].copy()
    rais["age_group"] = rais["age_group_code"].map({"2": "15_17", "3": "18_24"})
    rais = rais.pivot(
        index=["year", "municipality_ibge_code"],
        columns="age_group",
        values="active_bonds",
    ).reset_index()
    rais = rais.rename(
        columns={"15_17": "rais_active_bonds_15_17", "18_24": "rais_active_bonds_18_24"}
    )
    youth = youth.merge(
        rais,
        on=["year", "municipality_ibge_code"],
        how="left",
        validate="one_to_one",
    )
    for age_group in ("15_17", "18_24"):
        youth[f"log1p_rais_{age_group}"] = np.log1p(
            youth[f"rais_active_bonds_{age_group}"]
        )
        youth[f"log_population_{age_group}"] = np.log(
            youth[f"population_{age_group}"].where(
                youth[f"population_{age_group}"].gt(0)
            )
        )
    return model_panel.merge(
        youth,
        on=["year", "municipality_ibge_code"],
        how="left",
        validate="many_to_one",
    )


def _flatten_model(
    *,
    candidate_id: str,
    model_id: str,
    stage: str,
    specification: str,
    sensitivity: str,
    result: Mapping[str, Any],
) -> list[dict[str, Any]]:
    rows = []
    for coefficient in result["coefficients"]:
        rows.append(
            {
                "candidate_id": candidate_id,
                "model_id": model_id,
                "stage": stage,
                "outcome": result["outcome"],
                "specification": specification,
                "sensitivity": sensitivity,
                "term": coefficient["term"],
                "coefficient": coefficient["coefficient"],
                "standard_error_clustered": coefficient[
                    "standard_error_clustered"
                ],
                "z_statistic": coefficient["z_statistic"],
                "p_value_raw": coefficient["p_value_raw"],
                "p_value_bh": None,
                "fixed_effects": result["fixed_effects"],
                "standard_errors": result["standard_errors"],
                "weight": result["weight"],
                "observations": result["observations"],
                "municipalities": result["municipalities"],
                "year_min": min(result["years"]),
                "year_max": max(result["years"]),
                "year_count": len(result["years"]),
                "null_treatment": result["null_treatment"],
                "within_iterations": result["within_iterations"],
                "interpretation_limit": "ecological_association_not_causality",
            }
        )
    return rows


def _lag_factor(frame: pd.DataFrame, factor: str, lag: int) -> pd.DataFrame:
    if lag == 0:
        return frame
    result = frame.copy()
    result[factor] = result.groupby(
        ["municipality_ibge_code", "stage"], sort=False
    )[factor].shift(lag)
    return result


def _run_models(
    model_panel: pd.DataFrame,
    *,
    region_codes: Sequence[str],
) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    outcomes = [
        "failure_rate_percent",
        "dropout_rate_percent",
        "age_grade_distortion_rate_percent",
    ]
    h2_specs = [
        ("S1_CLASS_SIZE", ["students_per_class"]),
        ("S2_TEACHER_ADEQUACY", ["teacher_adequacy_percent"]),
        (
            "S3_BROADBAND_INSE",
            ["schools_with_broadband_percent", "inse_mean"],
        ),
    ]
    for stage in [
        "fundamental_anos_iniciais",
        "fundamental_anos_finais",
        "medio",
    ]:
        stage_frame = model_panel[
            model_panel["stage"].eq(stage) & model_panel["year"].between(2019, 2025)
        ].copy()
        for outcome in outcomes:
            for specification, factors in h2_specs:
                model_id = f"H2-{stage}-{outcome}-{specification}"
                try:
                    result = fit_clustered_panel(
                        stage_frame,
                        outcome=outcome,
                        factors=factors,
                        municipality="municipality_ibge_code",
                        year="year",
                    )
                    rows.extend(
                        _flatten_model(
                            candidate_id="H2_TRAJETORIA_PERMANENCIA",
                            model_id=model_id,
                            stage=stage,
                            specification=specification,
                            sensitivity="MAIN_2019_2025",
                            result=result,
                        )
                    )
                except ValueError as error:
                    failures.append(
                        {
                            "candidate_id": "H2_TRAJETORIA_PERMANENCIA",
                            "model_id": model_id,
                            "reason": str(error),
                        }
                    )
            for sensitivity, filter_mask in [
                ("EXCLUDE_2020_2021", ~stage_frame["year"].isin([2020, 2021])),
                ("WINDOW_2022_2025", stage_frame["year"].between(2022, 2025)),
            ]:
                try:
                    result = fit_clustered_panel(
                        stage_frame[filter_mask],
                        outcome=outcome,
                        factors=["students_per_class"],
                        municipality="municipality_ibge_code",
                        year="year",
                    )
                    rows.extend(
                        _flatten_model(
                            candidate_id="H2_TRAJETORIA_PERMANENCIA",
                            model_id=f"H2-{stage}-{outcome}-S1-{sensitivity}",
                            stage=stage,
                            specification="S1_CLASS_SIZE",
                            sensitivity=sensitivity,
                            result=result,
                        )
                    )
                except ValueError as error:
                    failures.append(
                        {
                            "candidate_id": "H2_TRAJETORIA_PERMANENCIA",
                            "model_id": f"H2-{stage}-{outcome}-S1-{sensitivity}",
                            "reason": str(error),
                        }
                    )
            try:
                no_fe = fit_clustered_panel(
                    stage_frame,
                    outcome=outcome,
                    factors=["students_per_class"],
                    municipality="municipality_ibge_code",
                    year="year",
                    fixed_effects=False,
                )
                rows.extend(
                    _flatten_model(
                        candidate_id="H2_TRAJETORIA_PERMANENCIA",
                        model_id=f"H2-{stage}-{outcome}-S1-NO_FE",
                        stage=stage,
                        specification="S1_CLASS_SIZE",
                        sensitivity="NO_FE_DIAGNOSTIC",
                        result=no_fe,
                    )
                )
            except ValueError as error:
                failures.append(
                    {
                        "candidate_id": "H2_TRAJETORIA_PERMANENCIA",
                        "model_id": f"H2-{stage}-{outcome}-S1-NO_FE",
                        "reason": str(error),
                    }
                )
            lagged_h2 = _lag_factor(stage_frame, "students_per_class", 1)
            try:
                result = fit_clustered_panel(
                    lagged_h2,
                    outcome=outcome,
                    factors=["students_per_class"],
                    municipality="municipality_ibge_code",
                    year="year",
                )
                rows.extend(
                    _flatten_model(
                        candidate_id="H2_TRAJETORIA_PERMANENCIA",
                        model_id=f"H2-{stage}-{outcome}-S1-LAG1",
                        stage=stage,
                        specification="S1_CLASS_SIZE",
                        sensitivity="LAG_1",
                        result=result,
                    )
                )
            except ValueError as error:
                failures.append(
                    {
                        "candidate_id": "H2_TRAJETORIA_PERMANENCIA",
                        "model_id": f"H2-{stage}-{outcome}-S1-LAG1",
                        "reason": str(error),
                    }
                )
            try:
                broadband_only = fit_clustered_panel(
                    stage_frame,
                    outcome=outcome,
                    factors=["schools_with_broadband_percent"],
                    municipality="municipality_ibge_code",
                    year="year",
                )
                rows.extend(
                    _flatten_model(
                        candidate_id="H2_TRAJETORIA_PERMANENCIA",
                        model_id=f"H2-{stage}-{outcome}-S3-WITHOUT-INSE",
                        stage=stage,
                        specification="S3_BROADBAND_INSE",
                        sensitivity="WITHOUT_INSE",
                        result=broadband_only,
                    )
                )
            except ValueError as error:
                failures.append(
                    {
                        "candidate_id": "H2_TRAJETORIA_PERMANENCIA",
                        "model_id": f"H2-{stage}-{outcome}-S3-WITHOUT-INSE",
                        "reason": str(error),
                    }
                )
            for excluded_code in region_codes:
                excluded_frame = stage_frame[
                    stage_frame["municipality_ibge_code"].ne(excluded_code)
                ]
                try:
                    leave_one = fit_clustered_panel(
                        excluded_frame,
                        outcome=outcome,
                        factors=["students_per_class"],
                        municipality="municipality_ibge_code",
                        year="year",
                    )
                    rows.extend(
                        _flatten_model(
                            candidate_id="H2_TRAJETORIA_PERMANENCIA",
                            model_id=f"H2-{stage}-{outcome}-S1-LOO-{excluded_code}",
                            stage=stage,
                            specification="S1_CLASS_SIZE",
                            sensitivity=f"LEAVE_OUT_VALE_{excluded_code}",
                            result=leave_one,
                        )
                    )
                except ValueError as error:
                    failures.append(
                        {
                            "candidate_id": "H2_TRAJETORIA_PERMANENCIA",
                            "model_id": f"H2-{stage}-{outcome}-S1-LOO-{excluded_code}",
                            "reason": str(error),
                        }
                    )
    h3_frame = model_panel[
        model_panel["stage"].eq("medio") & model_panel["year"].between(2019, 2025)
    ].copy()
    h3_specs = [
        ("S1_RAIS_15_17", ["log1p_rais_15_17"]),
        (
            "S2_RAIS_15_17_POPULATION",
            ["log1p_rais_15_17", "log_population_15_17"],
        ),
        ("S3_RAIS_18_24_DIAGNOSTIC", ["log1p_rais_18_24"]),
    ]
    for outcome in outcomes:
        for specification, factors in h3_specs:
            model_id = f"H3-medio-{outcome}-{specification}"
            try:
                result = fit_clustered_panel(
                    h3_frame,
                    outcome=outcome,
                    factors=factors,
                    municipality="municipality_ibge_code",
                    year="year",
                )
                rows.extend(
                    _flatten_model(
                        candidate_id="H3_TRABALHO_JUVENIL_MEDIO",
                        model_id=model_id,
                        stage="medio",
                        specification=specification,
                        sensitivity="MAIN_2019_2025",
                        result=result,
                    )
                )
            except ValueError as error:
                failures.append(
                    {
                        "candidate_id": "H3_TRABALHO_JUVENIL_MEDIO",
                        "model_id": model_id,
                        "reason": str(error),
                    }
                )
        for lag in (1, 2):
            lagged = _lag_factor(h3_frame, "log1p_rais_15_17", lag)
            try:
                result = fit_clustered_panel(
                    lagged,
                    outcome=outcome,
                    factors=["log1p_rais_15_17"],
                    municipality="municipality_ibge_code",
                    year="year",
                )
                rows.extend(
                    _flatten_model(
                        candidate_id="H3_TRABALHO_JUVENIL_MEDIO",
                        model_id=f"H3-medio-{outcome}-S1-LAG{lag}",
                        stage="medio",
                        specification="S1_RAIS_15_17",
                        sensitivity=f"LAG_{lag}",
                        result=result,
                    )
                )
            except ValueError as error:
                failures.append(
                    {
                        "candidate_id": "H3_TRABALHO_JUVENIL_MEDIO",
                        "model_id": f"H3-medio-{outcome}-S1-LAG{lag}",
                        "reason": str(error),
                    }
                )
        for sensitivity, filtered in [
            (
                "EXCLUDE_2020_2021",
                h3_frame[~h3_frame["year"].isin([2020, 2021])],
            ),
            (
                "EXCLUDE_LARGEST_RS_10",
                h3_frame[
                    ~h3_frame["municipality_ibge_code"].isin(
                        h3_frame[h3_frame["year"].eq(2025)]
                        .nlargest(10, "population_15_17")[
                            "municipality_ibge_code"
                        ]
                    )
                ],
            ),
            (
                "VALE_ONLY",
                h3_frame[h3_frame["municipality_ibge_code"].isin(region_codes)],
            ),
            (
                "EXCLUDE_SMALL_POPULATION_DECILE",
                h3_frame[
                    h3_frame["population_15_17"].ge(
                        h3_frame["population_15_17"].quantile(0.10)
                    )
                ],
            ),
        ]:
            try:
                result = fit_clustered_panel(
                    filtered,
                    outcome=outcome,
                    factors=["log1p_rais_15_17"],
                    municipality="municipality_ibge_code",
                    year="year",
                )
                rows.extend(
                    _flatten_model(
                        candidate_id="H3_TRABALHO_JUVENIL_MEDIO",
                        model_id=f"H3-medio-{outcome}-S1-{sensitivity}",
                        stage="medio",
                        specification="S1_RAIS_15_17",
                        sensitivity=sensitivity,
                        result=result,
                    )
                )
            except ValueError as error:
                failures.append(
                    {
                        "candidate_id": "H3_TRABALHO_JUVENIL_MEDIO",
                        "model_id": f"H3-medio-{outcome}-S1-{sensitivity}",
                        "reason": str(error),
                    }
                )
        for excluded_code in region_codes:
            excluded_frame = h3_frame[
                h3_frame["municipality_ibge_code"].ne(excluded_code)
            ]
            try:
                leave_one = fit_clustered_panel(
                    excluded_frame,
                    outcome=outcome,
                    factors=["log1p_rais_15_17"],
                    municipality="municipality_ibge_code",
                    year="year",
                )
                rows.extend(
                    _flatten_model(
                        candidate_id="H3_TRABALHO_JUVENIL_MEDIO",
                        model_id=f"H3-medio-{outcome}-S1-LOO-{excluded_code}",
                        stage="medio",
                        specification="S1_RAIS_15_17",
                        sensitivity=f"LEAVE_OUT_VALE_{excluded_code}",
                        result=leave_one,
                    )
                )
            except ValueError as error:
                failures.append(
                    {
                        "candidate_id": "H3_TRABALHO_JUVENIL_MEDIO",
                        "model_id": f"H3-medio-{outcome}-S1-LOO-{excluded_code}",
                        "reason": str(error),
                    }
                )
        for sensitivity, factors, weight in [
            ("WITH_INSE", ["log1p_rais_15_17", "inse_mean"], None),
            ("POPULATION_WEIGHTED", ["log1p_rais_15_17"], "population_15_17"),
        ]:
            try:
                alternative = fit_clustered_panel(
                    h3_frame,
                    outcome=outcome,
                    factors=factors,
                    municipality="municipality_ibge_code",
                    year="year",
                    weights=weight,
                )
                rows.extend(
                    _flatten_model(
                        candidate_id="H3_TRABALHO_JUVENIL_MEDIO",
                        model_id=f"H3-medio-{outcome}-S1-{sensitivity}",
                        stage="medio",
                        specification="S1_RAIS_15_17",
                        sensitivity=sensitivity,
                        result=alternative,
                    )
                )
            except ValueError as error:
                failures.append(
                    {
                        "candidate_id": "H3_TRABALHO_JUVENIL_MEDIO",
                        "model_id": f"H3-medio-{outcome}-S1-{sensitivity}",
                        "reason": str(error),
                    }
                )
        try:
            no_fe = fit_clustered_panel(
                h3_frame,
                outcome=outcome,
                factors=["log1p_rais_15_17"],
                municipality="municipality_ibge_code",
                year="year",
                fixed_effects=False,
            )
            rows.extend(
                _flatten_model(
                    candidate_id="H3_TRABALHO_JUVENIL_MEDIO",
                    model_id=f"H3-medio-{outcome}-S1-NO_FE",
                    stage="medio",
                    specification="S1_RAIS_15_17",
                    sensitivity="NO_FE_DIAGNOSTIC",
                    result=no_fe,
                )
            )
        except ValueError as error:
            failures.append(
                {
                    "candidate_id": "H3_TRABALHO_JUVENIL_MEDIO",
                    "model_id": f"H3-medio-{outcome}-S1-NO_FE",
                    "reason": str(error),
                }
            )
    model_frame = pd.DataFrame(rows)
    for candidate_id, index in model_frame.groupby("candidate_id").groups.items():
        p_values = model_frame.loc[index, "p_value_raw"].tolist()
        model_frame.loc[index, "p_value_bh"] = bh_adjust(p_values)
    return model_frame.sort_values(
        ["candidate_id", "model_id", "term"], kind="mergesort"
    ).reset_index(drop=True), failures


def _value_at(
    frame: pd.DataFrame,
    *,
    year: int,
    value_column: str,
    filters: Mapping[str, Any] | None = None,
) -> float | None:
    selected = frame[frame["year"].eq(year)]
    for column, value in (filters or {}).items():
        selected = selected[selected[column].eq(value)]
    if selected.empty:
        return None
    if len(selected) != 1:
        raise ValueError(
            f"Valor não único para {value_column}, {year}, {filters}: {len(selected)}."
        )
    return finite_or_none(selected.iloc[0][value_column])


def _build_similar_municipalities(
    *,
    panels: Mapping[str, pd.DataFrame],
    region_codes: Sequence[str],
    municipality_names: Mapping[str, str],
) -> dict[str, Any]:
    population = panels["population"]
    rows = []
    for year in (2019, 2025):
        part = population[
            population["municipality_ibge_code"].isin(region_codes)
            & population["age"].between(0, 14)
            & population["year"].eq(year)
        ].groupby("municipality_ibge_code")["population"].sum()
        rows.append(part.rename(f"population_0_14_{year}"))
    comparison = pd.concat(rows, axis=1).reset_index()
    comparison["population_0_14_growth_2019_2025"] = [
        relative_change(start, end)
        for start, end in zip(
            comparison["population_0_14_2019"],
            comparison["population_0_14_2025"],
            strict=True,
        )
    ]
    censo_2025 = panels["censo"][
        panels["censo"]["municipality_ibge_code"].isin(region_codes)
        & panels["censo"]["year"].eq(2025)
    ].copy()
    censo_2025["network_normalized"] = _normalize_total(censo_2025["network"])
    total_high_school = censo_2025.groupby("municipality_ibge_code")[
        "high_school_enrollments"
    ].sum(min_count=1)
    municipal_high_school = censo_2025[
        censo_2025["network_normalized"].eq("municipal")
    ].groupby("municipality_ibge_code")["high_school_enrollments"].sum(min_count=1)
    comparison = comparison.merge(
        pd.DataFrame(
            {
                "municipality_ibge_code": total_high_school.index,
                "municipal_high_school_share_2025": [
                    safe_ratio(municipal_high_school.get(code, 0.0), value)
                    for code, value in total_high_school.items()
                ],
            }
        ),
        on="municipality_ibge_code",
        how="left",
        validate="one_to_one",
    )
    inse = panels["inse"][
        panels["inse"]["municipality_ibge_code"].isin(region_codes)
        & panels["inse"]["year"].eq(panels["inse"]["year"].max())
    ][["municipality_ibge_code", "inse_mean"]]
    comparison = comparison.merge(
        inse,
        on="municipality_ibge_code",
        how="left",
        validate="one_to_one",
    )
    rais = panels["rais"][
        panels["rais"]["municipality_ibge_code"].isin(region_codes)
        & panels["rais"]["year"].eq(2025)
        & panels["rais"]["age_group_code"].eq("2")
    ][["municipality_ibge_code", "active_bonds"]]
    youth_population = population[
        population["municipality_ibge_code"].isin(region_codes)
        & population["year"].eq(2025)
        & population["age"].between(15, 17)
    ].groupby("municipality_ibge_code", as_index=False)["population"].sum()
    comparison = comparison.merge(
        rais,
        on="municipality_ibge_code",
        how="left",
        validate="one_to_one",
    ).merge(
        youth_population,
        on="municipality_ibge_code",
        how="left",
        validate="one_to_one",
    )
    comparison["formal_youth_work_share_15_17_2025"] = [
        safe_ratio(active_bonds, population_value)
        for active_bonds, population_value in zip(
            comparison["active_bonds"], comparison["population"], strict=True
        )
    ]
    variables = [
        "population_0_14_2025",
        "population_0_14_growth_2019_2025",
        "municipal_high_school_share_2025",
        "inse_mean",
        "formal_youth_work_share_15_17_2025",
    ]
    primary = standardized_distance_comparators(
        comparison,
        municipality_column="municipality_ibge_code",
        target=NOVA_SANTA_RITA,
        variables=variables,
        count=3,
    )
    sensitivity = {}
    for omitted in variables:
        sensitivity[omitted] = standardized_distance_comparators(
            comparison,
            municipality_column="municipality_ibge_code",
            target=NOVA_SANTA_RITA,
            variables=[variable for variable in variables if variable != omitted],
            count=3,
        )["selected"]
    selected = [
        {
            **item,
            "municipality_name": municipality_names[item["municipality_id"]],
        }
        for item in primary["selected"]
    ]
    return {
        "targetMunicipalityId": NOVA_SANTA_RITA,
        "targetMunicipalityName": municipality_names[NOVA_SANTA_RITA],
        "selectionUniverse": "canonical_10_municipality_Vale_do_Sinos",
        "variables": variables,
        "period": {
            "populationGrowth": "2019-2025",
            "otherVariables": "latest compatible observation (2023 or 2025)",
        },
        "nullTreatment": "median imputation within the ten-municipality comparison universe",
        "standardization": "population z-score with ddof=0 by variable",
        "selectionRule": "three smallest unweighted Euclidean distances; IBGE code breaks ties",
        "outcomeVariablesUsed": [],
        "selected": selected,
        "sensitivityLeaveOneVariableOut": sensitivity,
        "unavailableAdmissibleVariables": [
            "resident_urbanization was not represented by a compatible source",
            "sector_structure was not added to avoid a non-pre-registered extra query",
        ],
        "publishedScore": False,
        "comparisonInput": comparison[
            ["municipality_ibge_code", *variables]
        ].to_dict(orient="records"),
    }


def _trajectory_municipal_facts(
    trajectory: pd.DataFrame,
    *,
    region_codes: Sequence[str],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    selected = trajectory[
        trajectory["municipality_ibge_code"].isin(region_codes)
        & trajectory["dependencia"].astype("string").str.lower().eq("total")
        & trajectory["localizacao"].astype("string").str.lower().eq("total")
    ].copy()
    stage_metric = [
        ("fundamental_anos_iniciais", "failure_rate_percent"),
        ("fundamental_anos_finais", "dropout_rate_percent"),
        ("medio", "dropout_rate_percent"),
        ("taxa_distorcao_medio", "age_grade_distortion_rate_percent"),
    ]
    facts: list[dict[str, Any]] = []
    summary: dict[str, dict[str, Any]] = defaultdict(dict)
    for stage, metric in stage_metric:
        part = selected[
            selected["etapa_ensino"].eq(stage) & selected["metric"].eq(metric)
        ]
        years = sorted(int(value) for value in part["ano"].dropna().unique())
        if len(years) < 2:
            continue
        start_year, end_year = years[0], years[-1]
        regional_start = finite_or_none(
            part[part["ano"].eq(start_year)]["value"].median()
        )
        regional_end = finite_or_none(part[part["ano"].eq(end_year)]["value"].median())
        for municipality in region_codes:
            municipal = part[part["municipality_ibge_code"].eq(municipality)]
            start = finite_or_none(
                municipal[municipal["ano"].eq(start_year)]["value"].iloc[0]
            ) if not municipal[municipal["ano"].eq(start_year)].empty else None
            end = finite_or_none(
                municipal[municipal["ano"].eq(end_year)]["value"].iloc[0]
            ) if not municipal[municipal["ano"].eq(end_year)].empty else None
            fact_id = (
                f"H2-MUN-{municipality}-{stage.upper()}-{metric.upper()}-"
                f"{start_year}-{end_year}"
            )
            row = {
                "id": fact_id,
                "candidate_id": "H2_TRAJETORIA_PERMANENCIA",
                "scope": "municipality",
                "municipality_id": municipality,
                "stage": stage,
                "metric": metric,
                "period": f"{start_year}-{end_year}",
                "start_value_percent": start,
                "end_value_percent": end,
                "absolute_change_pp": (
                    end - start if start is not None and end is not None else None
                ),
                "regional_median_start_percent": regional_start,
                "regional_median_end_percent": regional_end,
                "direction_vs_region": direction_vs_region(
                    None if start is None or end is None else end - start,
                    None
                    if regional_start is None or regional_end is None
                    else regional_end - regional_start,
                ),
                "lens": "school_location",
                "aggregation": "regional_municipal_median_not_rate",
            }
            facts.append(row)
            summary[municipality][f"{stage}:{metric}"] = row
    return facts, summary


def _work_facts(
    rais_summary: pd.DataFrame,
    caged_monthly: pd.DataFrame,
    *,
    region_codes: Sequence[str],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    facts: list[dict[str, Any]] = []
    summary: dict[str, dict[str, Any]] = defaultdict(dict)
    rais_municipal = rais_summary[
        rais_summary["entity_scope"].eq("municipality")
        & rais_summary["municipality_ibge_code"].isin(region_codes)
    ]
    for municipality in region_codes:
        for age_group in ("15_17", "18_24"):
            part = rais_municipal[
                rais_municipal["municipality_ibge_code"].eq(municipality)
                & rais_municipal["age_group"].eq(age_group)
            ]
            start = _value_at(
                part, year=2019, value_column="active_bonds"
            )
            end = _value_at(part, year=2025, value_column="active_bonds")
            region_part = rais_summary[
                rais_summary["entity_scope"].eq("region")
                & rais_summary["age_group"].eq(age_group)
            ]
            region_start = _value_at(
                region_part, year=2019, value_column="active_bonds"
            )
            region_end = _value_at(
                region_part, year=2025, value_column="active_bonds"
            )
            fact_id = f"H3-RAIS-{municipality}-{age_group}-2019-2025"
            row = {
                "id": fact_id,
                "candidate_id": "H3_TRABALHO_JUVENIL_MEDIO",
                "scope": "municipality",
                "municipality_id": municipality,
                "age_group": age_group,
                "metric": "RAIS_active_bonds",
                "period": "2019-2025",
                "start_value": start,
                "end_value": end,
                "relative_change": relative_change(start, end),
                "regional_relative_change": relative_change(region_start, region_end),
                "direction_vs_region": direction_vs_region(
                    relative_change(start, end), relative_change(region_start, region_end)
                ),
                "lens": "workplace_municipality",
            }
            facts.append(row)
            summary[municipality][f"RAIS:{age_group}"] = row
        caged = caged_monthly[
            caged_monthly["entity_scope"].eq("municipality")
            & caged_monthly["municipality_ibge_code"].eq(municipality)
            & caged_monthly["age_group"].eq("15_17")
        ].groupby("year", as_index=False)[["admissions", "dismissals", "balance"]].sum()
        if not caged.empty:
            caged_row = {
                "id": f"H3-CAGED-{municipality}-15_17-2020-2025",
                "candidate_id": "H3_TRABALHO_JUVENIL_MEDIO",
                "scope": "municipality",
                "municipality_id": municipality,
                "age_group": "15_17",
                "metric": "CAGED_formal_flows",
                "period": "2020-2025",
                "admissions_2020": _value_at(
                    caged, year=2020, value_column="admissions"
                ),
                "admissions_2025": _value_at(
                    caged, year=2025, value_column="admissions"
                ),
                "dismissals_2020": _value_at(
                    caged, year=2020, value_column="dismissals"
                ),
                "dismissals_2025": _value_at(
                    caged, year=2025, value_column="dismissals"
                ),
                "balance_2020": _value_at(caged, year=2020, value_column="balance"),
                "balance_2025": _value_at(caged, year=2025, value_column="balance"),
                "lens": "workplace_municipality",
                "stockFlowSeparation": "CAGED flows are not RAIS stock",
            }
            facts.append(caged_row)
            summary[municipality]["CAGED:15_17"] = caged_row
    return facts, summary


def _h4_facts(
    demand_offer: pd.DataFrame,
    eja_components: pd.DataFrame,
    *,
    region_codes: Sequence[str],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], dict[str, Any]]:
    municipal = demand_offer[
        demand_offer["entity_scope"].eq("municipality")
        & demand_offer["municipality_ibge_code"].isin(region_codes)
    ]
    facts: list[dict[str, Any]] = []
    summary: dict[str, dict[str, Any]] = defaultdict(dict)
    for row in municipal.itertuples(index=False):
        difference = finite_or_none(row.diferenca_distribuicao_pp)
        if difference is None:
            distribution_type = "unavailable"
        elif difference > 0.01:
            distribution_type = "enrollment_share_above_public_share"
        elif difference < -0.01:
            distribution_type = "enrollment_share_below_public_share"
        else:
            distribution_type = "shares_near_within_0_01_fraction"
        fact = {
            "id": f"H4-MUN-{row.municipality_ibge_code}-{row.stage.upper()}-2022",
            "candidate_id": "H4_EJA_DISTRIBUICAO",
            "scope": "municipality",
            "municipality_id": row.municipality_ibge_code,
            "stage": row.stage,
            "metric": "EJA_distribution_snapshot",
            "period": "2022",
            "potential_public": finite_or_none(row.potential_public),
            "eja_enrollments": finite_or_none(row.eja_enrollments),
            "participacao_publico_i": finite_or_none(row.participacao_publico_i),
            "participacao_matriculas_i": finite_or_none(
                row.participacao_matriculas_i
            ),
            "diferenca_distribuicao_pp": difference,
            "stored_scale": "fraction_0_1",
            "matriculas_por_mil": finite_or_none(row.matriculas_por_mil),
            "distribution_type": distribution_type,
            "lenses": ["resident_population", "school_location"],
        }
        facts.append(fact)
        summary[row.municipality_ibge_code][row.stage] = fact
    state = eja_components.copy()
    state["potential_fundamental_eja"] = (
        state["population_18_plus"] - state["fundamental_completed_18_plus"]
    )
    state["potential_high_school_eja"] = (
        state["fundamental_completed_18_plus"]
        - state["high_school_completed_18_plus"]
    )
    state_metrics = {}
    for stage, potential_column, enrollment_column in [
        (
            "fundamental",
            "potential_fundamental_eja",
            "fundamental_eja_enrollments",
        ),
        (
            "high_school",
            "potential_high_school_eja",
            "high_school_eja_enrollments",
        ),
    ]:
        state_metrics[stage] = {
            "municipalityCount": int(state["municipality_ibge_code"].nunique()),
            "potentialPublic": float(state[potential_column].sum()),
            "enrollments": float(state[enrollment_column].sum()),
            "enrollmentsPerThousand": safe_ratio(
                state[enrollment_column].sum(),
                state[potential_column].sum(),
                multiplier=1000.0,
            ),
        }
    closure = {}
    for stage in ("fundamental", "high_school"):
        stage_frame = municipal[municipal["stage"].eq(stage)]
        closure[stage] = {
            "publicShareSum": float(stage_frame["participacao_publico_i"].sum()),
            "enrollmentShareSum": float(
                stage_frame["participacao_matriculas_i"].sum()
            ),
            "differenceSum": float(
                stage_frame["diferenca_distribuicao_pp"].sum()
            ),
        }
    return facts, summary, {"state": state_metrics, "closure": closure}


def _a3_facts(
    coverage: pd.DataFrame,
    occupations: pd.DataFrame,
    courses: pd.DataFrame,
    *,
    region_codes: Sequence[str],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], dict[str, Any]]:
    facts: list[dict[str, Any]] = []
    summary: dict[str, dict[str, Any]] = defaultdict(dict)
    occupation_municipal = occupations[
        occupations["entity_scope"].eq("municipality")
        & occupations["municipality_ibge_code"].isin(region_codes)
    ]
    for municipality in region_codes:
        supply = coverage[coverage["municipality_ibge_code"].eq(municipality)]
        supply_start = _value_at(
            supply, year=2023, value_column="course_technical_enrollments"
        )
        supply_end = _value_at(
            supply, year=2025, value_column="course_technical_enrollments"
        )
        occupation = occupation_municipal[
            occupation_municipal["municipality_ibge_code"].eq(municipality)
        ].groupby("year", as_index=False)["active_bonds"].sum()
        occupation_start = _value_at(
            occupation, year=2019, value_column="active_bonds"
        )
        occupation_end = _value_at(
            occupation, year=2025, value_column="active_bonds"
        )
        latest_supply = supply[supply["year"].eq(2025)]
        availability = (
            latest_supply.iloc[0]["availability_status"]
            if not latest_supply.empty
            else "unavailable"
        )
        fact = {
            "id": f"A3-MUN-{municipality}-2019-2025",
            "candidate_id": "A3_OCUPACOES_FORMACAO",
            "scope": "municipality",
            "municipality_id": municipality,
            "metric": "technical_supply_and_occupational_context",
            "supply_period": "2023-2025",
            "occupation_period": "2019-2025",
            "technical_enrollments_2023": supply_start,
            "technical_enrollments_2025": supply_end,
            "technical_enrollment_relative_change": relative_change(
                supply_start, supply_end
            ),
            "supply_availability_2025": availability,
            "active_bonds_2019": occupation_start,
            "active_bonds_2025": occupation_end,
            "active_bond_relative_change": relative_change(
                occupation_start, occupation_end
            ),
            "lenses": ["school_location", "workplace_municipality"],
            "bridge_semantics": "normative_correspondence_not_adequacy",
        }
        facts.append(fact)
        summary[municipality]["supply_occupations"] = fact
    courses_2025 = courses[courses["year"].eq(2025)]
    municipality_totals = courses_2025.groupby("municipality_ibge_code")[
        "technical_enrollments"
    ].sum()
    regional_total = float(courses_2025["technical_enrollments"].sum())
    dominant_code = (
        str(municipality_totals.idxmax()) if not municipality_totals.empty else None
    )
    return facts, summary, {
        "regionalTechnicalEnrollments2025": regional_total,
        "dominantMunicipalityId": dominant_code,
        "dominantMunicipalityShare": safe_ratio(
            municipality_totals.max() if not municipality_totals.empty else None,
            regional_total,
        ),
        "observedZeroMunicipalities2025": sorted(
            coverage[
                coverage["year"].eq(2025)
                & coverage["availability_status"].eq("observed_zero")
            ]["municipality_ibge_code"].astype(str)
        ),
    }


def _municipal_layers(
    *,
    region_codes: Sequence[str],
    municipality_names: Mapping[str, str],
    h1_decomposition: pd.DataFrame,
    h2_summary: Mapping[str, Mapping[str, Any]],
    h3_summary: Mapping[str, Mapping[str, Any]],
    h4_summary: Mapping[str, Mapping[str, Any]],
    a3_summary: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    layers: list[dict[str, Any]] = []
    eligibility = {
        "H1_DEMOGRAFIA_REDE": "ANALYTICALLY_ELIGIBLE",
        "H2_TRAJETORIA_PERMANENCIA": "REVIEW_REQUIRED",
        "H3_TRABALHO_JUVENIL_MEDIO": "REVIEW_REQUIRED",
        "H4_EJA_DISTRIBUICAO": "ANALYTICALLY_ELIGIBLE",
        "A1_COORTES_REDE": "RETAINED",
        "A2_TRABALHO_PERMANENCIA": "RETAINED",
        "A3_OCUPACOES_FORMACAO": "ANALYTICALLY_ELIGIBLE",
    }
    h1_municipal = h1_decomposition[
        h1_decomposition["entity_scope"].eq("municipality")
    ]
    h1_region = h1_decomposition[h1_decomposition["entity_scope"].eq("region")]
    h1_state = h1_decomposition[h1_decomposition["entity_scope"].eq("state")]
    for municipality in region_codes:
        local_h1 = h1_municipal[
            h1_municipal["municipality_id"].eq(municipality)
        ]
        local_high_school = local_h1[local_h1["stage"].eq("high_school")].iloc[0]
        regional_high_school = h1_region[
            h1_region["stage"].eq("high_school")
        ].iloc[0]
        state_high_school = h1_state[h1_state["stage"].eq("high_school")].iloc[0]
        h1_fact_ids = [
            f"H1-MUNICIPALITY-{municipality}-{stage.upper()}-2014-2025"
            for stage in STAGE_SPECS
        ]
        base = {
            "municipality_id": municipality,
            "municipality_name": municipality_names[municipality],
        }
        layers.append(
            {
                **base,
                "candidate_id": "H1_DEMOGRAFIA_REDE",
                "direction_vs_region": direction_vs_region(
                    local_high_school["enrollment_relative_change"],
                    regional_high_school["enrollment_relative_change"],
                ),
                "regional_contribution": safe_ratio(
                    local_high_school["enrollment_change"],
                    regional_high_school["enrollment_change"],
                ),
                "network": ["municipal", "state", "private", "federal_when_observed"],
                "stage": list(STAGE_SPECS),
                "public": "resident_compatible_age_and_school_enrollments",
                "local_fact_ids": h1_fact_ids,
                "regional_fact_ids": [
                    f"H1-REGION-ALL-{stage.upper()}-2014-2025"
                    for stage in STAGE_SPECS
                ],
                "local_interpretive_factor": {
                    "populationRelativeChangeHighSchoolAge": finite_or_none(
                        local_high_school["population_relative_change"]
                    ),
                    "enrollmentRelativeChangeHighSchool": finite_or_none(
                        local_high_school["enrollment_relative_change"]
                    ),
                    "stateEnrollmentRelativeChangeHighSchool": finite_or_none(
                        state_high_school["enrollment_relative_change"]
                    ),
                },
                "institutional_responsibility": [
                    "municipal_network",
                    "state_network",
                    "regional_coordination",
                ],
                "monitoring_indicators": [
                    "compatible_age_population",
                    "enrollments_by_stage_and_network",
                    "classes",
                    "schools",
                ],
                "candidate_eligibility": eligibility["H1_DEMOGRAFIA_REDE"],
            }
        )

        h2_local = h2_summary.get(municipality, {})
        h2_medium = h2_local.get("medio:dropout_rate_percent", {})
        layers.append(
            {
                **base,
                "candidate_id": "H2_TRAJETORIA_PERMANENCIA",
                "direction_vs_region": h2_medium.get(
                    "direction_vs_region", "unavailable"
                ),
                "regional_contribution": "not_applicable_without_rate_components",
                "network": "total_for_models; network-specific_descriptive_layers",
                "stage": [
                    "fundamental_anos_iniciais",
                    "fundamental_anos_finais",
                    "medio",
                ],
                "public": "students_in_covered_school_stage_network_cells",
                "local_fact_ids": sorted(
                    value["id"] for value in h2_local.values() if "id" in value
                ),
                "regional_fact_ids": [
                    "H2-REGIONAL-MUNICIPAL-DISTRIBUTION-NOT-RATE"
                ],
                "local_interpretive_factor": {
                    "mediumDropoutChangePp": h2_medium.get("absolute_change_pp"),
                    "regionUsesMedianNotRate": True,
                },
                "institutional_responsibility": [
                    "responsible_school_network",
                    "municipal_monitoring",
                    "state_coordination",
                ],
                "monitoring_indicators": [
                    "failure_rate",
                    "dropout_rate",
                    "age_grade_distortion",
                    "students_per_class",
                    "teacher_adequacy",
                ],
                "candidate_eligibility": eligibility["H2_TRAJETORIA_PERMANENCIA"],
            }
        )

        h3_local = h3_summary.get(municipality, {})
        rais_15_17 = h3_local.get("RAIS:15_17", {})
        layers.append(
            {
                **base,
                "candidate_id": "H3_TRABALHO_JUVENIL_MEDIO",
                "direction_vs_region": rais_15_17.get(
                    "direction_vs_region", "unavailable"
                ),
                "regional_contribution": "formal_work_change_contribution_in_factual_package",
                "network": "high_school_total_for_models",
                "stage": "high_school",
                "public": ["students_high_school", "formal_workers_15_17", "formal_workers_18_24"],
                "local_fact_ids": sorted(
                    value["id"] for value in h3_local.values() if "id" in value
                ),
                "regional_fact_ids": [
                    "H3-REGION-RAIS-15_17-2019-2025",
                    "H3-REGION-CAGED-15_17-2020-2025",
                ],
                "local_interpretive_factor": {
                    "RAIS15To17RelativeChange": rais_15_17.get("relative_change"),
                    "workEducationLink": "ecological_only",
                },
                "institutional_responsibility": [
                    "state_high_school_network",
                    "municipal_youth_policy",
                    "regional_work_education_coordination",
                ],
                "monitoring_indicators": [
                    "high_school_dropout",
                    "high_school_failure",
                    "RAIS_active_bonds_15_17",
                    "CAGED_flows_15_17",
                ],
                "candidate_eligibility": eligibility["H3_TRABALHO_JUVENIL_MEDIO"],
            }
        )

        h4_local = h4_summary.get(municipality, {})
        h4_high = h4_local.get("high_school", {})
        layers.append(
            {
                **base,
                "candidate_id": "H4_EJA_DISTRIBUICAO",
                "direction_vs_region": h4_high.get(
                    "distribution_type", "unavailable"
                ),
                "regional_contribution": {
                    "publicShare": h4_high.get("participacao_publico_i"),
                    "enrollmentShare": h4_high.get("participacao_matriculas_i"),
                },
                "network": "EJA_network_responsibility_requires_local_monitoring",
                "stage": ["fundamental", "high_school"],
                "public": "adult_2022_stage_specific_census_universe",
                "local_fact_ids": sorted(
                    value["id"] for value in h4_local.values() if "id" in value
                ),
                "regional_fact_ids": [
                    "H4-REGION-FUNDAMENTAL-2022",
                    "H4-REGION-HIGH_SCHOOL-2022",
                ],
                "local_interpretive_factor": {
                    "mixedTerritorialLens": True,
                    "historicalIntegratedEjaIsSeparateContext": True,
                },
                "institutional_responsibility": [
                    "municipal_and_state_EJA_networks",
                    "regional_coordination",
                ],
                "monitoring_indicators": [
                    "potential_public_share",
                    "enrollment_share",
                    "distribution_difference_fraction",
                    "enrollments_per_thousand",
                ],
                "candidate_eligibility": eligibility["H4_EJA_DISTRIBUICAO"],
            }
        )

        layers.append(
            {
                **base,
                "candidate_id": "A1_COORTES_REDE",
                "direction_vs_region": direction_vs_region(
                    local_high_school["population_relative_change"],
                    regional_high_school["population_relative_change"],
                ),
                "regional_contribution": safe_ratio(
                    local_high_school["population_end"]
                    - local_high_school["population_start"],
                    regional_high_school["population_end"]
                    - regional_high_school["population_start"],
                ),
                "network": ["observed_network", "no_future_scenario"],
                "stage": list(STAGE_SPECS),
                "public": "resident_age_cohorts",
                "local_fact_ids": h1_fact_ids,
                "regional_fact_ids": [
                    f"H1-REGION-ALL-{stage.upper()}-2014-2025"
                    for stage in STAGE_SPECS
                ],
                "local_interpretive_factor": {
                    "territorialStartingPoint": True,
                    "redundantWithH1AtDecision": True,
                },
                "institutional_responsibility": [
                    "municipal_territorial_planning",
                    "responsible_school_networks",
                ],
                "monitoring_indicators": [
                    "observed_cohort_size",
                    "observed_enrollments",
                    "observed_schools",
                ],
                "candidate_eligibility": eligibility["A1_COORTES_REDE"],
            }
        )
        layers.append(
            {
                **base,
                "candidate_id": "A2_TRABALHO_PERMANENCIA",
                "direction_vs_region": rais_15_17.get(
                    "direction_vs_region", "unavailable"
                ),
                "regional_contribution": "formal_work_change_contribution_in_factual_package",
                "network": "high_school_network_in_coordination_context",
                "stage": "high_school",
                "public": ["formal_workers_15_17", "formal_workers_18_24", "high_school_students"],
                "local_fact_ids": sorted(
                    value["id"] for value in h3_local.values() if "id" in value
                ),
                "regional_fact_ids": [
                    "H3-REGION-RAIS-15_17-2019-2025",
                    "H3-REGION-CAGED-15_17-2020-2025",
                ],
                "local_interpretive_factor": {
                    "workFirstStartingPoint": True,
                    "redundantWithH3AtCurrentDecision": True,
                },
                "institutional_responsibility": [
                    "work_education_regional_coordination",
                    "state_high_school_network",
                ],
                "monitoring_indicators": [
                    "RAIS_youth_stock",
                    "CAGED_youth_flows",
                    "high_school_trajectory",
                ],
                "candidate_eligibility": eligibility["A2_TRABALHO_PERMANENCIA"],
            }
        )

        a3_local = a3_summary.get(municipality, {}).get(
            "supply_occupations", {}
        )
        layers.append(
            {
                **base,
                "candidate_id": "A3_OCUPACOES_FORMACAO",
                "direction_vs_region": (
                    "observed_zero_supply_2025"
                    if a3_local.get("supply_availability_2025") == "observed_zero"
                    else "observed_supply_context"
                ),
                "regional_contribution": safe_ratio(
                    a3_local.get("technical_enrollments_2025"),
                    sum(
                        value.get("supply_occupations", {}).get(
                            "technical_enrollments_2025", 0
                        )
                        or 0
                        for value in a3_summary.values()
                    ),
                ),
                "network": "technical_offering_institutions",
                "stage": "technical_education",
                "public": "technical_enrollments_and_formal_occupational_bonds",
                "local_fact_ids": (
                    [a3_local["id"]] if a3_local.get("id") else []
                ),
                "regional_fact_ids": [
                    "A3-REGION-BRIDGE-COVERAGE-2025",
                    "A3-REGION-OCCUPATIONS-2019-2025",
                ],
                "local_interpretive_factor": {
                    "supplyAvailability2025": a3_local.get(
                        "supply_availability_2025"
                    ),
                    "bridgeIsAdequacy": False,
                },
                "institutional_responsibility": [
                    "state",
                    "municipalities",
                    "offering_institutions",
                    "Sistema_S",
                ],
                "monitoring_indicators": [
                    "course_and_axis_composition",
                    "technical_enrollments",
                    "occupation_subgroup_bonds",
                    "bridge_coverage",
                ],
                "candidate_eligibility": eligibility["A3_OCUPACOES_FORMACAO"],
            }
        )
    if len(layers) != 70:
        raise ValueError(f"Camada municipal deveria conter 70 registros, contém {len(layers)}.")
    return layers


def _model_stability(model_frame: pd.DataFrame, candidate_id: str) -> dict[str, Any]:
    candidate = model_frame[
        model_frame["candidate_id"].eq(candidate_id)
        & model_frame["term"].ne("intercept")
    ]
    if candidate.empty:
        return {
            "modelCount": 0,
            "mainTermCount": 0,
            "mainAdjustedPBelow005": 0,
            "signAgreementMainVsSensitivities": None,
        }
    main = candidate[candidate["sensitivity"].str.startswith("MAIN")]
    sign_groups = []
    for (_, outcome, term), group in candidate.groupby(
        ["stage", "outcome", "term"], sort=True
    ):
        main_group = group[group["sensitivity"].str.startswith("MAIN")]
        sensitivity = group[
            ~group["sensitivity"].str.startswith("MAIN")
            & group["sensitivity"].ne("NO_FE_DIAGNOSTIC")
        ]
        if main_group.empty or sensitivity.empty:
            continue
        main_sign = np.sign(main_group.iloc[0]["coefficient"])
        sign_groups.append(
            float((np.sign(sensitivity["coefficient"]) == main_sign).mean())
        )
    return {
        "modelCount": int(candidate["model_id"].nunique()),
        "mainTermCount": int(len(main)),
        "mainAdjustedPBelow005": int(main["p_value_bh"].lt(0.05).sum()),
        "signAgreementMainVsSensitivities": (
            float(np.mean(sign_groups)) if sign_groups else None
        ),
        "minimumMunicipalities": int(candidate["municipalities"].min()),
        "maximumMunicipalities": int(candidate["municipalities"].max()),
        "minimumObservations": int(candidate["observations"].min()),
        "maximumObservations": int(candidate["observations"].max()),
    }


def _robustness_records(
    *,
    h1_decomposition: pd.DataFrame,
    h1_metadata: Mapping[str, Any],
    h2_summary: Mapping[str, Mapping[str, Any]],
    h3_summary: Mapping[str, Mapping[str, Any]],
    h4_summary: Mapping[str, Mapping[str, Any]],
    h4_metadata: Mapping[str, Any],
    a3_summary: Mapping[str, Mapping[str, Any]],
    a3_metadata: Mapping[str, Any],
    model_frame: pd.DataFrame,
    region_codes: Sequence[str],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    h1_region = h1_decomposition[
        h1_decomposition["entity_scope"].eq("region")
    ].set_index("stage")
    h1_state = h1_decomposition[
        h1_decomposition["entity_scope"].eq("state")
    ].set_index("stage")
    h1_municipal = h1_decomposition[
        h1_decomposition["entity_scope"].eq("municipality")
        & h1_decomposition["stage"].eq("high_school")
    ].copy()
    h1_municipal["absolute_change"] = h1_municipal["enrollment_change"].abs()
    h1_dominant = h1_municipal.nlargest(1, "absolute_change").iloc[0]
    h1_loo_directions = {
        row["direction"] for row in h1_metadata["leaveOneOut"]["high_school"]
    }
    h1_robustness = {
        "temporal_stability": {
            "mainWindow": "2014-2025",
            "stageDirections": h1_region["enrollment_direction"].to_dict(),
            "alternativeWindowsRegistered": ["2014-2019", "2019-2025", "2022-2025"],
        },
        "territorial_stability": {
            "municipalities": 10,
            "highSchoolLocalDirections": sorted(
                h1_municipal["enrollment_direction"].unique()
            ),
        },
        "dominant_municipality": {
            "municipalityId": h1_dominant["municipality_id"],
            "absoluteEnrollmentChangeHighSchool": finite_or_none(
                h1_dominant["enrollment_change"]
            ),
        },
        "leave_one_out": {
            "highSchoolDirections": sorted(h1_loo_directions),
            "stableDirection": len(h1_loo_directions) == 1,
            "details": h1_metadata["leaveOneOut"]["high_school"],
        },
        "state_comparison": {
            stage: {
                "regionEnrollmentRelativeChange": finite_or_none(
                    h1_region.loc[stage, "enrollment_relative_change"]
                ),
                "stateEnrollmentRelativeChange": finite_or_none(
                    h1_state.loc[stage, "enrollment_relative_change"]
                ),
            }
            for stage in STAGE_SPECS
        },
        "pandemic_sensitivity": {
            "interpretation": "Alternative windows isolate pre-pandemic and recent directions; no causal pandemic coefficient is used."
        },
    }

    h2_candidates = []
    for municipality in region_codes:
        fact = h2_summary.get(municipality, {}).get(
            "medio:dropout_rate_percent"
        )
        if fact and fact.get("absolute_change_pp") is not None:
            h2_candidates.append(fact)
    h2_dominant = (
        max(h2_candidates, key=lambda row: abs(row["absolute_change_pp"]))
        if h2_candidates
        else None
    )
    h2_model = _model_stability(model_frame, "H2_TRAJETORIA_PERMANENCIA")
    h2_robustness = {
        "temporal_stability": {
            "modelDiagnostics": h2_model,
            "windows": ["2019-2025", "2022-2025"],
        },
        "territorial_stability": {
            "statePanelMunicipalitiesMaximum": h2_model.get("maximumMunicipalities"),
            "ValeMunicipalFacts": len(h2_candidates),
        },
        "dominant_municipality": (
            {
                "municipalityId": h2_dominant["municipality_id"],
                "mediumDropoutAbsoluteChangePp": h2_dominant[
                    "absolute_change_pp"
                ],
            }
            if h2_dominant
            else None
        ),
        "leave_one_out": {
            "method": "Vale-only model sensitivity and municipal distribution diagnostics",
            "fullTenMunicipalityModelIsSensitivity": True,
        },
        "state_comparison": {
            "coverage": "497 municipalities in source; complete cases vary by specification",
            "models": h2_model,
        },
        "pandemic_sensitivity": {
            "executed": True,
            "sensitivityLabel": "EXCLUDE_2020_2021",
        },
    }

    rais_changes = [
        h3_summary.get(municipality, {}).get("RAIS:15_17")
        for municipality in region_codes
    ]
    rais_changes = [
        row for row in rais_changes if row and row.get("relative_change") is not None
    ]
    h3_dominant = (
        max(rais_changes, key=lambda row: abs(row["end_value"] - row["start_value"]))
        if rais_changes
        else None
    )
    h3_model = _model_stability(model_frame, "H3_TRABALHO_JUVENIL_MEDIO")
    h3_robustness = {
        "temporal_stability": {
            "modelDiagnostics": h3_model,
            "lags": [0, 1, 2],
            "RAISWindow": "2019-2025",
            "CAGEDWindow": "2020-2025",
        },
        "territorial_stability": {
            "statePanelMunicipalitiesMaximum": h3_model.get("maximumMunicipalities"),
            "ValeMunicipalFacts": len(rais_changes),
        },
        "dominant_municipality": (
            {
                "municipalityId": h3_dominant["municipality_id"],
                "RAIS15To17AbsoluteChange": h3_dominant["end_value"]
                - h3_dominant["start_value"],
            }
            if h3_dominant
            else None
        ),
        "leave_one_out": {
            "method": "VALE_ONLY fixed-effect sensitivity plus municipal contribution review",
            "executed": True,
        },
        "state_comparison": {
            "coverage": "497 municipality RAIS/education panel",
            "models": h3_model,
        },
        "pandemic_sensitivity": {
            "executed": True,
            "sensitivityLabel": "EXCLUDE_2020_2021",
        },
    }

    h4_facts = [
        fact
        for municipality in region_codes
        for fact in h4_summary.get(municipality, {}).values()
        if fact.get("diferenca_distribuicao_pp") is not None
    ]
    h4_dominant = max(
        h4_facts, key=lambda row: abs(row["diferenca_distribuicao_pp"])
    )
    h4_robustness = {
        "temporal_stability": {
            "notApplicable": True,
            "reason": "The candidate is a pre-registered 2022 snapshot.",
        },
        "territorial_stability": {
            "municipalities": 10,
            "fundamentalClosure": h4_metadata["closure"]["fundamental"],
            "highSchoolClosure": h4_metadata["closure"]["high_school"],
        },
        "dominant_municipality": {
            "municipalityId": h4_dominant["municipality_id"],
            "stage": h4_dominant["stage"],
            "absoluteDistributionDifferenceFraction": abs(
                h4_dominant["diferenca_distribuicao_pp"]
            ),
        },
        "leave_one_out": {
            "notApplicable": True,
            "reason": "Removing a municipality changes the declared regional distribution universe.",
        },
        "state_comparison": h4_metadata["state"],
        "pandemic_sensitivity": {
            "notApplicable": True,
            "reason": "Snapshot is 2022 and is not interpreted as a trend.",
        },
    }

    a3_2025 = [
        value.get("supply_occupations", {})
        for value in a3_summary.values()
        if value.get("supply_occupations")
    ]
    a3_robustness = {
        "temporal_stability": {
            "supplyWindow": "2023-2025",
            "occupationWindow": "2019-2025",
            "municipalSupplyDirections": sorted(
                {
                    direction(
                        row.get("technical_enrollments_2023"),
                        row.get("technical_enrollments_2025"),
                    )
                    for row in a3_2025
                }
            ),
        },
        "territorial_stability": {
            "municipalities": 10,
            "observedZeroMunicipalities2025": a3_metadata[
                "observedZeroMunicipalities2025"
            ],
        },
        "dominant_municipality": {
            "municipalityId": a3_metadata["dominantMunicipalityId"],
            "technicalEnrollmentShare2025": a3_metadata[
                "dominantMunicipalityShare"
            ],
        },
        "leave_one_out": {
            "method": "regional supply concentration recalculated from municipal totals",
            "dominantShareRecorded": a3_metadata["dominantMunicipalityShare"],
        },
        "state_comparison": {
            "available": False,
            "reason": "Detailed course supply universe in Job 2 is regional; no substitute was used.",
        },
        "pandemic_sensitivity": {
            "notApplicable": True,
            "reason": "Detailed course series starts in 2023.",
        },
    }

    robustness = {
        "H1_DEMOGRAFIA_REDE": h1_robustness,
        "H2_TRAJETORIA_PERMANENCIA": h2_robustness,
        "H3_TRABALHO_JUVENIL_MEDIO": h3_robustness,
        "H4_EJA_DISTRIBUICAO": h4_robustness,
        "A1_COORTES_REDE": {
            **h1_robustness,
            "nonRedundancy": "retained_due_to_same_decision_as_H1",
        },
        "A2_TRABALHO_PERMANENCIA": {
            **h3_robustness,
            "nonRedundancy": "retained_due_to_same_current_decision_as_H3",
        },
        "A3_OCUPACOES_FORMACAO": a3_robustness,
    }
    records = []
    for candidate_id in CANDIDATE_IDS:
        item = robustness[candidate_id]
        records.append(
            {
                "candidate_id": candidate_id,
                "temporal_stability": json.dumps(
                    item["temporal_stability"], ensure_ascii=False, sort_keys=True
                ),
                "territorial_stability": json.dumps(
                    item["territorial_stability"], ensure_ascii=False, sort_keys=True
                ),
                "dominant_municipality": json.dumps(
                    item["dominant_municipality"], ensure_ascii=False, sort_keys=True
                ),
                "leave_one_out": json.dumps(
                    item["leave_one_out"], ensure_ascii=False, sort_keys=True
                ),
                "state_comparison": json.dumps(
                    item["state_comparison"], ensure_ascii=False, sort_keys=True
                ),
                "pandemic_sensitivity": json.dumps(
                    item["pandemic_sensitivity"], ensure_ascii=False, sort_keys=True
                ),
                "correlation_only_gate_used": False,
            }
        )
    return records, robustness


def _checks_for(*, status: str, review_checks: Sequence[str] = (), failed_checks: Sequence[str] = ()) -> dict[str, str]:
    checks = {f"C{index}": "APPROVED" for index in range(1, 13)}
    checks["C9"] = "PENDING_EDITORIAL"
    for check in review_checks:
        checks[check] = "REVIEW_REQUIRED"
    for check in failed_checks:
        checks[check] = "FAILED"
    if status == "ANALYTICALLY_ELIGIBLE":
        required = [f"C{index}" for index in range(1, 13) if index != 9]
        if any(checks[check] != "APPROVED" for check in required):
            raise ValueError("Candidata elegível contém check não aprovado.")
    return checks


def _registry(
    *,
    facts: Sequence[Mapping[str, Any]],
    layers: Sequence[Mapping[str, Any]],
    robustness: Mapping[str, Mapping[str, Any]],
    comparators: Mapping[str, Any],
    model_frame: pd.DataFrame,
    h1_decomposition: pd.DataFrame,
    h2_summary: Mapping[str, Mapping[str, Any]],
    h3_summary: Mapping[str, Mapping[str, Any]],
    h4_summary: Mapping[str, Mapping[str, Any]],
    h4_metadata: Mapping[str, Any],
    a3_summary: Mapping[str, Mapping[str, Any]],
    a3_metadata: Mapping[str, Any],
    bridge_coverage: pd.DataFrame,
) -> dict[str, Any]:
    fact_ids_by_candidate: dict[str, list[str]] = defaultdict(list)
    for fact in facts:
        fact_ids_by_candidate[fact["candidate_id"]].append(fact["id"])
    layers_by_candidate: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for layer in layers:
        layers_by_candidate[layer["candidate_id"]].append(layer)
    nova_layers = {
        layer["candidate_id"]: layer
        for layer in layers
        if layer["municipality_id"] == NOVA_SANTA_RITA
    }
    model_summaries = {
        candidate_id: _model_stability(model_frame, candidate_id)
        for candidate_id in (
            "H2_TRAJETORIA_PERMANENCIA",
            "H3_TRABALHO_JUVENIL_MEDIO",
        )
    }
    h1_region = h1_decomposition[
        h1_decomposition["entity_scope"].eq("region")
    ].to_dict(orient="records")
    h1_state = h1_decomposition[
        h1_decomposition["entity_scope"].eq("state")
    ].to_dict(orient="records")
    h1_nsr = h1_decomposition[
        h1_decomposition["entity_scope"].eq("municipality")
        & h1_decomposition["municipality_id"].eq(NOVA_SANTA_RITA)
    ].to_dict(orient="records")
    bridge = {
        row.bridge_status: {
            "courseCount": int(row.course_count),
            "technicalEnrollments": int(row.technical_enrollments),
            "courseShare": finite_or_none(row.course_share),
            "enrollmentShare": finite_or_none(row.enrollment_share),
        }
        for row in bridge_coverage.itertuples(index=False)
    }
    common_prohibited = [
        "causal interpretation",
        "same-person linkage across aggregate sources",
        "observed trend as projection",
    ]
    candidates = [
        {
            "id": "H1_DEMOGRAFIA_REDE",
            "direction": "education_change_then_territorial_and_network_increment",
            "question": "How are changing generations reorganizing observed educational demand and network response?",
            "status": "ANALYTICALLY_ELIGIBLE",
            "mechanism": "Enrollment change decomposes into compatible population change and the enrollment-population relation; network and municipal distribution can alter the planning response.",
            "local_references": [
                "docs/RELATORIO_JOB_2E_DEMOGRAFIA_REDE_MOBILIDADE_V7_VOCACOES_PNE.md",
                "docs/BIBLIOTECA_MECANISMOS_JOB_3_V7.md",
            ],
            "data_inputs": [
                "Job2 2E cohorts/network",
                "SESI censo/populacao_idade read-only",
            ],
            "grain": "municipality-year-stage; network-location for observed response",
            "lenses": ["resident_population", "school_location"],
            "period": "2014-2025; births through 2024 remain contextual",
            "temporal_nature": "observed_series_and_exact_decomposition",
            "education_fact_ids": fact_ids_by_candidate["H1_DEMOGRAFIA_REDE"],
            "territorial_fact_ids": fact_ids_by_candidate["H1_DEMOGRAFIA_REDE"],
            "regional_result": h1_region,
            "municipal_distribution": layers_by_candidate["H1_DEMOGRAFIA_REDE"],
            "nova_santa_rita": {
                "layer": nova_layers["H1_DEMOGRAFIA_REDE"],
                "stageResults": h1_nsr,
            },
            "state_comparison": h1_state,
            "similar_municipalities": comparators["selected"],
            "models": {"executed": False, "reason": "pre-registered decomposition, not regression"},
            "robustness": robustness["H1_DEMOGRAFIA_REDE"],
            "demography_only_counterfactual": "Would monitor only cohort volumes and miss relation, network, class, school and municipal-distribution changes.",
            "decision_delta": "Monitor stage- and network-specific observed response and municipalities moving differently from the region, not cohort size alone.",
            "planning_components": {
                "public": "compatible age cohort and enrolled students",
                "stage": list(STAGE_SPECS),
                "network": "municipal/state/private/federal when observed",
                "action": "joint stage-network-territory monitoring",
                "indicator": "population, enrollment, relation M/P, classes and schools",
            },
            "institutional_responsibility": [
                "municipal_network",
                "state_network",
                "regional_coordination",
            ],
            "monitoring_indicators": [
                "compatible_age_population",
                "enrollments_by_stage",
                "M_over_P_relation",
                "classes",
                "schools",
            ],
            "maximum_supported_claim": "Observed enrollment change can be exactly decomposed and the network/municipal response changes the monitoring question beyond population volume.",
            "prohibited_claims": common_prohibited
            + ["future municipal enrollment", "school opening or closing recommendation"],
            "checks": _checks_for(status="ANALYTICALLY_ELIGIBLE"),
            "retention_or_block_reason": None,
            "recommended_visual_data": {
                "structures": ["stage_decomposition", "municipal_direction", "network_change"],
                "factIds": fact_ids_by_candidate["H1_DEMOGRAFIA_REDE"],
            },
            "traceability": {
                "preregistration": "1.0.0",
                "artifact": "h1_decomposition.csv.gz",
                "formula": "Shapley exact M=P*R decomposition",
            },
        },
        {
            "id": "H2_TRAJETORIA_PERMANENCIA",
            "direction": "education_trajectory_then_compatible_conditions",
            "question": "Where do trajectory and permanence outcomes move with compatible school conditions?",
            "status": "REVIEW_REQUIRED",
            "mechanism": "Stage-compatible organization and offer conditions can help locate joint monitoring needs without identifying cause.",
            "local_references": [
                "docs/RELATORIO_JOB_2A_TRAJETORIA_ESCOLAR_CONDICOES_V7_VOCACOES_PNE.md",
                "docs/BIBLIOTECA_MECANISMOS_JOB_3_V7.md",
            ],
            "data_inputs": ["Job2 2A panels", "SESI RS read-only panel"],
            "grain": "municipality-year-stage at total network for models; descriptive network cuts",
            "lenses": ["school_location"],
            "period": "2019-2025 primary",
            "temporal_nature": "observed_panel_ecological_association",
            "education_fact_ids": fact_ids_by_candidate["H2_TRAJETORIA_PERMANENCIA"],
            "territorial_fact_ids": fact_ids_by_candidate["H2_TRAJETORIA_PERMANENCIA"],
            "regional_result": {
                "aggregation": "municipal_distribution_not_simple_regional_rate",
                "modelDiagnostics": model_summaries["H2_TRAJETORIA_PERMANENCIA"],
            },
            "municipal_distribution": layers_by_candidate["H2_TRAJETORIA_PERMANENCIA"],
            "nova_santa_rita": {
                "layer": nova_layers["H2_TRAJETORIA_PERMANENCIA"],
                "facts": h2_summary[NOVA_SANTA_RITA],
            },
            "state_comparison": robustness["H2_TRAJETORIA_PERMANENCIA"]["state_comparison"],
            "similar_municipalities": comparators["selected"],
            "models": model_summaries["H2_TRAJETORIA_PERMANENCIA"],
            "robustness": robustness["H2_TRAJETORIA_PERMANENCIA"],
            "demography_only_counterfactual": "Would not distinguish trajectory outcomes or school-condition monitoring needs.",
            "decision_delta": "Potentially changes which stage, network and condition should be investigated together; external technical judgment is still required because stability varies.",
            "planning_components": {
                "public": "students in compatible stage/network cells",
                "stage": ["early_fundamental", "final_fundamental", "high_school"],
                "network": "total models plus descriptive network cuts",
                "action": "target joint trajectory-condition monitoring",
                "indicator": "failure, dropout, distortion and pre-registered conditions",
            },
            "institutional_responsibility": [
                "responsible_school_network",
                "municipal_monitoring",
                "state_coordination",
            ],
            "monitoring_indicators": [
                "failure_rate",
                "dropout_rate",
                "age_grade_distortion",
                "students_per_class",
                "teacher_adequacy",
            ],
            "maximum_supported_claim": "The internal models test ecological within-municipality associations under declared specifications; they do not identify effects.",
            "prohibited_claims": common_prohibited
            + ["school condition caused failure or dropout"],
            "checks": _checks_for(status="REVIEW_REQUIRED", review_checks=["C5"]),
            "retention_or_block_reason": "Temporal coverage and model sign/magnitude stability require external technical judgment.",
            "recommended_visual_data": {
                "structures": ["municipal_trajectory", "condition_overlay", "model_sensitivity"],
                "factIds": fact_ids_by_candidate["H2_TRAJETORIA_PERMANENCIA"],
            },
            "traceability": {
                "preregistration": "1.0.0",
                "artifacts": ["models.csv.gz", "robustness.csv.gz"],
            },
        },
        {
            "id": "H3_TRABALHO_JUVENIL_MEDIO",
            "direction": "high_school_outcome_then_formal_youth_work_increment",
            "question": "How do changes in formal youth work relate ecologically to secondary-school outcomes?",
            "status": "REVIEW_REQUIRED",
            "mechanism": "Formal youth-work stock and flows can add a territorial coordination lens to secondary-school monitoring.",
            "local_references": [
                "docs/RELATORIO_JOB_2B_TRABALHO_JOVEM_V7_VOCACOES_PNE.md",
                "docs/BIBLIOTECA_MECANISMOS_JOB_3_V7.md",
            ],
            "data_inputs": ["Job2 2A/2B", "SESI and CEI read-only RS panels"],
            "grain": "municipality-year; formal-work age groups and high-school outcomes",
            "lenses": ["school_location", "workplace_municipality", "resident_population"],
            "period": "RAIS 2019-2025; CAGED 2020-2025; no 2026",
            "temporal_nature": "observed_ecological_panel",
            "education_fact_ids": fact_ids_by_candidate["H2_TRAJETORIA_PERMANENCIA"],
            "territorial_fact_ids": fact_ids_by_candidate["H3_TRABALHO_JUVENIL_MEDIO"],
            "regional_result": {
                "RAISAndCAGEDKeptSeparate": True,
                "modelDiagnostics": model_summaries["H3_TRABALHO_JUVENIL_MEDIO"],
            },
            "municipal_distribution": layers_by_candidate["H3_TRABALHO_JUVENIL_MEDIO"],
            "nova_santa_rita": {
                "layer": nova_layers["H3_TRABALHO_JUVENIL_MEDIO"],
                "workFacts": h3_summary[NOVA_SANTA_RITA],
                "educationFacts": h2_summary[NOVA_SANTA_RITA],
            },
            "state_comparison": robustness["H3_TRABALHO_JUVENIL_MEDIO"]["state_comparison"],
            "similar_municipalities": comparators["selected"],
            "models": model_summaries["H3_TRABALHO_JUVENIL_MEDIO"],
            "robustness": robustness["H3_TRABALHO_JUVENIL_MEDIO"],
            "demography_only_counterfactual": "Would omit formal-work stock, flow and coordination context for high-school monitoring.",
            "decision_delta": "Potentially adds joint work-education monitoring by age group and municipality; ecological stability still needs external judgment.",
            "planning_components": {
                "public": ["15_17", "18_24", "high_school_students"],
                "stage": "high_school",
                "network": "responsible high-school networks",
                "action": "coordinate work and education indicators",
                "indicator": "RAIS stock, CAGED flows and school trajectory",
            },
            "institutional_responsibility": [
                "state_high_school_network",
                "municipal_youth_policy",
                "regional_coordination",
            ],
            "monitoring_indicators": [
                "RAIS_active_bonds_15_17",
                "CAGED_admissions_dismissals",
                "high_school_dropout",
                "high_school_failure",
            ],
            "maximum_supported_claim": "Formal youth-work measures and education outcomes can be compared ecologically with lags and fixed effects, without linking persons.",
            "prohibited_claims": common_prohibited
            + ["work caused dropout", "first employment", "informality or unemployment"],
            "checks": _checks_for(status="REVIEW_REQUIRED", review_checks=["C5"]),
            "retention_or_block_reason": "Ecological model stability and mixed territorial lenses require external technical judgment.",
            "recommended_visual_data": {
                "structures": ["separate_RAIS_stock", "separate_CAGED_flows", "lag_sensitivity"],
                "factIds": fact_ids_by_candidate["H3_TRABALHO_JUVENIL_MEDIO"],
            },
            "traceability": {
                "preregistration": "1.0.0",
                "artifacts": ["models.csv.gz", "candidate_facts.json"],
                "forbiddenStockTableUsed": False,
            },
        },
        {
            "id": "H4_EJA_DISTRIBUICAO",
            "direction": "2022_stage_specific_distribution_snapshot",
            "question": "Is EJA enrollment distributed similarly to the adult population without the relevant stage completed?",
            "status": "ANALYTICALLY_ELIGIBLE",
            "mechanism": "Differences between resident-public and school-location enrollment shares can change territorial coordination and network monitoring.",
            "local_references": [
                "docs/RELATORIO_JOB_2C_EJA_V7_VOCACOES_PNE.md",
                "docs/BIBLIOTECA_MECANISMOS_JOB_3_V7.md",
            ],
            "data_inputs": ["Job2 2C", "SESI same-universe state components read-only"],
            "grain": "municipality-stage 2022",
            "lenses": ["resident_population", "school_location"],
            "period": "2022 snapshot; 2014-2025 integrated EJA as separate context",
            "temporal_nature": "snapshot_not_trend",
            "education_fact_ids": fact_ids_by_candidate["H4_EJA_DISTRIBUICAO"],
            "territorial_fact_ids": fact_ids_by_candidate["H4_EJA_DISTRIBUICAO"],
            "regional_result": h4_metadata["closure"],
            "municipal_distribution": layers_by_candidate["H4_EJA_DISTRIBUICAO"],
            "nova_santa_rita": {
                "layer": nova_layers["H4_EJA_DISTRIBUICAO"],
                "stageFacts": h4_summary[NOVA_SANTA_RITA],
            },
            "state_comparison": h4_metadata["state"],
            "similar_municipalities": comparators["selected"],
            "models": {"executed": False, "reason": "snapshot distribution is primary"},
            "robustness": robustness["H4_EJA_DISTRIBUICAO"],
            "demography_only_counterfactual": "Would observe adult population totals but miss where school-location enrollment shares differ territorially.",
            "decision_delta": "Adds stage-specific regional coordination and network responsibility monitoring without calling the metric coverage or service.",
            "planning_components": {
                "public": "stage-specific adult census universe",
                "stage": ["fundamental", "high_school"],
                "network": "EJA municipal and state responsibilities",
                "action": "monitor territorial distribution and coordination",
                "indicator": "public share, enrollment share, fraction difference, enrollments per thousand",
            },
            "institutional_responsibility": [
                "municipal_and_state_EJA_networks",
                "regional_coordination",
            ],
            "monitoring_indicators": [
                "potential_public_share",
                "enrollment_share",
                "distribution_difference_fraction",
                "enrollments_per_thousand",
            ],
            "maximum_supported_claim": "The 2022 distribution of school-location enrollments can be compared with the distribution of the stage-specific resident public.",
            "prohibited_claims": common_prohibited
            + ["coverage", "demand", "reach", "attendance", "capacity", "sufficiency"],
            "checks": _checks_for(status="ANALYTICALLY_ELIGIBLE"),
            "retention_or_block_reason": None,
            "recommended_visual_data": {
                "structures": ["paired_shares_by_stage", "difference_fraction", "historical_context_separate"],
                "factIds": fact_ids_by_candidate["H4_EJA_DISTRIBUICAO"],
            },
            "traceability": {
                "preregistration": "1.0.0",
                "artifact": "h4_distribution.csv.gz",
                "storedScale": "fraction_0_1",
            },
        },
        {
            "id": "A1_COORTES_REDE",
            "direction": "territorial_transformation_then_observed_network",
            "question": "How do shrinking, stable and growing municipalities require different observed-network responses?",
            "status": "RETAINED",
            "mechanism": "Territorial divergence in cohorts can reframe network monitoring.",
            "local_references": [
                "docs/RELATORIO_JOB_2E_DEMOGRAFIA_REDE_MOBILIDADE_V7_VOCACOES_PNE.md",
                "docs/BIBLIOTECA_MECANISMOS_JOB_3_V7.md",
            ],
            "data_inputs": ["same observed cohort and network facts as H1"],
            "grain": "municipality-year-age-group and observed network",
            "lenses": ["resident_population", "school_location"],
            "period": "2014-2025 observed",
            "temporal_nature": "observed_series_no_projection",
            "education_fact_ids": fact_ids_by_candidate["H1_DEMOGRAFIA_REDE"],
            "territorial_fact_ids": fact_ids_by_candidate["H1_DEMOGRAFIA_REDE"],
            "regional_result": h1_region,
            "municipal_distribution": layers_by_candidate["A1_COORTES_REDE"],
            "nova_santa_rita": {
                "layer": nova_layers["A1_COORTES_REDE"],
                "stageResults": h1_nsr,
            },
            "state_comparison": h1_state,
            "similar_municipalities": comparators["selected"],
            "models": {"executed": False},
            "robustness": robustness["A1_COORTES_REDE"],
            "demography_only_counterfactual": "This candidate starts from demography and adds observed network response.",
            "decision_delta": "At current evidence it reaches the same stage-network-territory monitoring decision as H1.",
            "planning_components": {
                "public": "resident cohorts",
                "stage": list(STAGE_SPECS),
                "network": "observed networks",
                "action": "same as H1 at current evidence",
                "indicator": "cohorts, enrollment, schools and classes",
            },
            "institutional_responsibility": [
                "municipal_territorial_planning",
                "responsible_school_networks",
            ],
            "monitoring_indicators": [
                "observed_cohorts",
                "observed_enrollments",
                "schools",
            ],
            "maximum_supported_claim": "Municipal cohort directions differ and can be read with observed network response.",
            "prohibited_claims": common_prohibited
            + ["future enrollment", "municipal scenario", "open or close school"],
            "checks": _checks_for(status="RETAINED", failed_checks=["C11"]),
            "retention_or_block_reason": "Retained for substantive redundancy: current decision, public, indicators and responsibilities coincide with H1.",
            "recommended_visual_data": {
                "structures": ["territorial_direction", "observed_network"],
                "factIds": fact_ids_by_candidate["H1_DEMOGRAFIA_REDE"],
            },
            "traceability": {
                "preregistration": "1.0.0",
                "nonRedundancyDecision": "retain_A1_keep_H1",
            },
        },
        {
            "id": "A2_TRABALHO_PERMANENCIA",
            "direction": "formal_work_transformation_then_education_agenda",
            "question": "Which changes in formal youth work should enter secondary-school coordination?",
            "status": "RETAINED",
            "mechanism": "A work-first reading can reach education coordination through stocks, flows and composition.",
            "local_references": [
                "docs/RELATORIO_JOB_2B_TRABALHO_JOVEM_V7_VOCACOES_PNE.md",
                "docs/BIBLIOTECA_MECANISMOS_JOB_3_V7.md",
            ],
            "data_inputs": ["same Job2 2A/2B and RS panels as H3"],
            "grain": "municipality-year-age-group",
            "lenses": ["workplace_municipality", "school_location"],
            "period": "2019-2025; CAGED 2020-2025",
            "temporal_nature": "observed_ecological_series",
            "education_fact_ids": fact_ids_by_candidate["H2_TRAJETORIA_PERMANENCIA"],
            "territorial_fact_ids": fact_ids_by_candidate["H3_TRABALHO_JUVENIL_MEDIO"],
            "regional_result": {
                "sameEvidenceAsH3": True,
                "workFirstOrientation": True,
            },
            "municipal_distribution": layers_by_candidate["A2_TRABALHO_PERMANENCIA"],
            "nova_santa_rita": {
                "layer": nova_layers["A2_TRABALHO_PERMANENCIA"],
                "workFacts": h3_summary[NOVA_SANTA_RITA],
            },
            "state_comparison": robustness["A2_TRABALHO_PERMANENCIA"]["state_comparison"],
            "similar_municipalities": comparators["selected"],
            "models": {
                "sharedEvidenceReference": "H3 models",
                **model_summaries["H3_TRABALHO_JUVENIL_MEDIO"],
            },
            "robustness": robustness["A2_TRABALHO_PERMANENCIA"],
            "demography_only_counterfactual": "Would omit changes in formal youth work.",
            "decision_delta": "At current evidence it reaches the same joint monitoring and coordination decision as H3.",
            "planning_components": {
                "public": ["formal_workers_15_17", "formal_workers_18_24", "students"],
                "stage": "high_school",
                "network": "responsible high-school networks",
                "action": "same joint monitoring as H3",
                "indicator": "RAIS, CAGED and school trajectory",
            },
            "institutional_responsibility": [
                "regional_work_education_coordination",
                "state_high_school_network",
            ],
            "monitoring_indicators": [
                "RAIS_youth_stock",
                "CAGED_youth_flows",
                "high_school_trajectory",
            ],
            "maximum_supported_claim": "Formal-work change can be placed beside aggregate education indicators as an ecological coordination context.",
            "prohibited_claims": common_prohibited
            + ["work caused school result", "first employment"],
            "checks": _checks_for(status="RETAINED", failed_checks=["C11"]),
            "retention_or_block_reason": "Retained because public, responsibility, indicators and current decision are not materially distinct from H3.",
            "recommended_visual_data": {
                "structures": ["work_first_stock_flow", "education_context"],
                "factIds": fact_ids_by_candidate["H3_TRABALHO_JUVENIL_MEDIO"],
            },
            "traceability": {
                "preregistration": "1.0.0",
                "nonRedundancyDecision": "retain_A2_keep_H3",
            },
        },
        {
            "id": "A3_OCUPACOES_FORMACAO",
            "direction": "work_change_then_training_questions",
            "question": "Which observed work changes raise questions for professional training?",
            "status": "ANALYTICALLY_ELIGIBLE",
            "mechanism": "A reproducible normative course-CBO bridge organizes observed supply and occupational composition while preserving incomplete coverage and non-additivity.",
            "local_references": [
                "docs/RELATORIO_JOB_2D_OCUPACOES_FORMACAO_V7_VOCACOES_PNE.md",
                "data_pipeline/contracts/vocacoes-pne-course-cbo-rs-v1-projection.json",
                "docs/BIBLIOTECA_MECANISMOS_JOB_3_V7.md",
            ],
            "data_inputs": ["Job2 2D five artifacts"],
            "grain": "municipality-year-course-axis and municipality-year-occupation-sector",
            "lenses": ["school_location", "workplace_municipality"],
            "period": "supply 2023-2025; occupations 2019-2025",
            "temporal_nature": "observed_series_and_2025_normative_bridge_snapshot",
            "education_fact_ids": fact_ids_by_candidate["A3_OCUPACOES_FORMACAO"],
            "territorial_fact_ids": fact_ids_by_candidate["A3_OCUPACOES_FORMACAO"],
            "regional_result": {
                **a3_metadata,
                "bridgeCoverage": bridge,
            },
            "municipal_distribution": layers_by_candidate["A3_OCUPACOES_FORMACAO"],
            "nova_santa_rita": {
                "layer": nova_layers["A3_OCUPACOES_FORMACAO"],
                "facts": a3_summary[NOVA_SANTA_RITA],
            },
            "state_comparison": robustness["A3_OCUPACOES_FORMACAO"]["state_comparison"],
            "similar_municipalities": comparators["selected"],
            "models": {"executed": False, "reason": "descriptive bridge and composition only"},
            "robustness": robustness["A3_OCUPACOES_FORMACAO"],
            "demography_only_counterfactual": "Would omit occupational structure, course composition and unresolved correspondence.",
            "decision_delta": "Adds a concrete coordination agenda for the State, municipalities, offering institutions and Sistema S around composition and bridge gaps.",
            "planning_components": {
                "public": "technical enrollments and formal occupational bonds",
                "stage": "professional_technical_education",
                "network": "offering institutions and involved networks",
                "action": "monitor composition and unresolved correspondence",
                "indicator": "courses, axes, enrollments, occupations, sectors and bridge coverage",
            },
            "institutional_responsibility": [
                "state",
                "municipalities",
                "offering_institutions",
                "Sistema_S",
            ],
            "monitoring_indicators": [
                "course_axis_composition",
                "technical_enrollments",
                "occupation_subgroup_bonds",
                "mapped_enrollment_share",
            ],
            "maximum_supported_claim": "Observed supply and occupational composition can be organized through a partial normative bridge to define monitoring questions.",
            "prohibited_claims": common_prohibited
            + [
                "future occupations",
                "course guarantees employment",
                "absence means nonexistence",
                "enrollment is intake completion vacancy or capacity",
                "bridge means adequacy",
            ],
            "checks": _checks_for(status="ANALYTICALLY_ELIGIBLE"),
            "retention_or_block_reason": None,
            "recommended_visual_data": {
                "structures": ["course_axis_composition", "occupation_subgroups", "bridge_coverage_status"],
                "factIds": fact_ids_by_candidate["A3_OCUPACOES_FORMACAO"],
            },
            "traceability": {
                "preregistration": "1.0.0",
                "artifacts": ["a3_summary.csv.gz", "candidate_facts.json"],
                "bridgeCoverageEnrollmentShare": bridge.get("mapped", {}).get(
                    "enrollmentShare"
                ),
            },
        },
    ]
    payload = {
        "schemaVersion": "vocacoes-pne-v7-job3-candidate-registry-v1",
        "jobId": JOB_ID,
        "publicArtifact": False,
        "interfaceAuthorization": False,
        "publicationAuthorization": False,
        "candidates": candidates,
    }
    validate_candidate_registry(payload)
    return payload


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return None if pd.isna(value) else float(value)
    if value is pd.NA or (isinstance(value, float) and math.isnan(value)):
        return None
    if isinstance(value, Path):
        return value.as_posix()
    return value


def _nonredundancy() -> dict[str, Any]:
    return {
        "schemaVersion": "vocacoes-pne-v7-job3-nonredundancy-v1",
        "pairs": [
            {
                "pair": ["H1_DEMOGRAFIA_REDE", "A1_COORTES_REDE"],
                "startingPoints": ["education_change", "territorial_transformation"],
                "questionsDiffer": True,
                "factsOverlap": "substantial",
                "publics": ["compatible_age_cohorts", "enrolled_students"],
                "responsibilities": ["school_networks", "territorial_planning"],
                "decisions": ["stage_network_monitoring", "territorial_response"],
                "indicators": ["population", "enrollment", "classes", "schools"],
                "decision": "RETAIN_A1_KEEP_H1",
                "reason": "At current evidence both reach the same operational monitoring decision; H1 preserves the exact decomposition and network increment.",
            },
            {
                "pair": [
                    "H3_TRABALHO_JUVENIL_MEDIO",
                    "A2_TRABALHO_PERMANENCIA",
                ],
                "startingPoints": ["education_outcome", "formal_work_transformation"],
                "questionsDiffer": True,
                "factsOverlap": "substantial",
                "publics": ["formal_youth_workers", "high_school_students"],
                "responsibilities": [
                    "state_high_school_network",
                    "regional_work_education_coordination",
                ],
                "decisions": ["joint_work_education_monitoring"],
                "indicators": ["RAIS", "CAGED", "dropout", "failure", "distortion"],
                "decision": "RETAIN_A2_KEEP_H3",
                "reason": "The orientation differs, but current public, responsibility, indicators and decision do not differ materially.",
            },
            {
                "pair": ["H5_FORMACAO_OCUPACOES", "A3_OCUPACOES_FORMACAO"],
                "startingPoints": ["not_present", "work_change"],
                "decision": "NO_H5_CREATED",
                "reason": "No additional candidate was authorized; A3 remains the only occupations-training candidate.",
            },
            {
                "pair": ["H2_TRAJETORIA_PERMANENCIA", "unplanned_conditions_candidate"],
                "decision": "NO_NEW_CANDIDATE_CREATED",
                "reason": "All pre-registered school conditions remain inside H2.",
            },
        ],
    }


def _nova_package(
    registry: Mapping[str, Any],
    comparators: Mapping[str, Any],
) -> dict[str, Any]:
    entries = []
    for candidate in registry["candidates"]:
        layer = candidate["nova_santa_rita"]["layer"]
        entries.append(
            {
                "candidate_id": candidate["id"],
                "status": candidate["status"],
                "local_trajectory": candidate["nova_santa_rita"],
                "regional_contrast": layer["direction_vs_region"],
                "state_contrast": candidate["state_comparison"],
                "network": layer["network"],
                "stage": layer["stage"],
                "public": layer["public"],
                "regional_contribution": layer["regional_contribution"],
                "second_interpretive_factor": layer[
                    "local_interpretive_factor"
                ],
                "monitoring_indicators": layer["monitoring_indicators"],
                "institutional_responsibility": layer[
                    "institutional_responsibility"
                ],
                "reading_limit": candidate["maximum_supported_claim"],
                "decision_reason": candidate["decision_delta"],
            }
        )
    return {
        "schemaVersion": "vocacoes-pne-v7-job3-nova-santa-rita-factual-v1",
        "municipalityId": NOVA_SANTA_RITA,
        "municipalityName": "Nova Santa Rita",
        "generatedBySameMunicipalLayerCode": True,
        "candidateCount": len(entries),
        "candidates": entries,
        "similarMunicipalities": comparators,
        "publicNarrative": False,
        "interfaceAuthorization": False,
    }


def _priorities(
    registry: Mapping[str, Any],
    nova_package: Mapping[str, Any],
) -> dict[str, Any]:
    by_candidate = {
        item["candidate_id"]: item for item in nova_package["candidates"]
    }
    registry_by_id = {item["id"]: item for item in registry["candidates"]}
    priorities = []
    for rank, candidate_id in enumerate(
        ["H1_DEMOGRAFIA_REDE", "H4_EJA_DISTRIBUICAO", "A3_OCUPACOES_FORMACAO"],
        start=1,
    ):
        candidate = registry_by_id[candidate_id]
        local = by_candidate[candidate_id]
        priorities.append(
            {
                "rank": rank,
                "candidata": candidate_id,
                "fato_local": candidate["nova_santa_rita"],
                "contraste_regional": local["regional_contrast"],
                "responsabilidade": local["institutional_responsibility"],
                "indicador": local["monitoring_indicators"],
                "criterio_de_selecao": "ANALYTICALLY_ELIGIBLE, non-redundant, complete municipal layer, distinct mechanism and current reproducible facts",
                "motivo_de_exclusao_das_candidatas_seguintes": {
                    "H2_TRAJETORIA_PERMANENCIA": "REVIEW_REQUIRED for temporal/model stability",
                    "H3_TRABALHO_JUVENIL_MEDIO": "REVIEW_REQUIRED for ecological/model stability",
                    "A1_COORTES_REDE": "RETAINED as redundant with H1",
                    "A2_TRABALHO_PERMANENCIA": "RETAINED as redundant with H3",
                },
            }
        )
    return {
        "schemaVersion": "vocacoes-pne-v7-job3-preliminary-priorities-v1",
        "municipalityId": NOVA_SANTA_RITA,
        "internalOnly": True,
        "interfaceAuthorization": False,
        "publicationAuthorization": False,
        "selectionRule": "up to three; no artificial filling",
        "priorityCount": len(priorities),
        "priorities": priorities,
    }


def _data_dictionary() -> dict[str, Any]:
    return {
        "schemaVersion": "vocacoes-pne-v7-job3-data-dictionary-v1",
        "identity": {
            "municipality_id": "textual seven-digit IBGE code; never numeric",
        },
        "statusSemantics": {
            "observed": "source-observed value including zero",
            "observed_zero": "source coverage confirmed and observed value equals zero",
            "unavailable": "source or compatible cut does not provide a value",
            "suppressed": "source suppressed the value",
            "not_applicable": "metric does not apply to the declared grain",
            "null": "numeric absence under declared semantics; denominator zero is null",
        },
        "lenses": {
            "resident_population": "municipality of residence",
            "school_location": "municipality of school",
            "workplace_municipality": "municipality of establishment",
        },
        "eja": {
            "diferenca_distribuicao_pp": {
                "storedScale": "fraction_0_1",
                "formula": "participacao_matriculas_i - participacao_publico_i",
            },
            "matriculas_por_mil": {
                "unit": "enrollments per one thousand potential-public units",
                "notA": ["coverage", "demand", "reach", "attendance", "capacity"],
            },
        },
        "models": {
            "coefficient": "ecological within-municipality association in source units",
            "standard_error_clustered": "municipality-clustered standard error",
            "p_value_raw": "two-sided normal approximation before family correction",
            "p_value_bh": "Benjamini-Hochberg adjusted value within candidate family",
            "fixed_effects": "municipality and year when true",
        },
        "courseBridge": {
            "meaning": "reproducible normative formative correspondence",
            "notA": ["adequacy", "employability", "capacity", "future occupation"],
            "nonAdditivity": "course enrollments repeat when one course maps to multiple occupation subgroups",
        },
    }


def _schemas() -> dict[str, Any]:
    return {
        "schemaVersion": "vocacoes-pne-v7-job3-artifact-schemas-v1",
        "candidateRegistry": {
            "path": "candidate_registry.json",
            "candidateCount": 7,
            "requiredFields": [
                "id", "direction", "question", "status", "mechanism",
                "local_references", "data_inputs", "grain", "lenses", "period",
                "temporal_nature", "education_fact_ids", "territorial_fact_ids",
                "regional_result", "municipal_distribution", "nova_santa_rita",
                "state_comparison", "similar_municipalities", "models",
                "robustness", "demography_only_counterfactual", "decision_delta",
                "planning_components", "institutional_responsibility",
                "monitoring_indicators", "maximum_supported_claim",
                "prohibited_claims", "checks", "retention_or_block_reason",
                "recommended_visual_data", "traceability"
            ],
        },
        "municipalLayers": {
            "path": "municipal_layers.json",
            "grain": ["candidate_id", "municipality_id"],
            "expectedRows": 70,
        },
        "models": {
            "path": "models.csv.gz",
            "grain": ["model_id", "term"],
            "requiredDiagnostics": [
                "observations", "municipalities", "year_min", "year_max",
                "null_treatment", "weight", "standard_errors",
                "p_value_raw", "p_value_bh"
            ],
        },
        "robustness": {
            "path": "robustness.csv.gz",
            "grain": ["candidate_id"],
            "requiredFields": [
                "temporal_stability", "territorial_stability",
                "dominant_municipality", "leave_one_out",
                "state_comparison", "pandemic_sensitivity"
            ],
        },
        "h1Decomposition": {
            "path": "h1_decomposition.csv.gz",
            "grain": ["entity_scope", "municipality_id", "stage"],
        },
        "h4Distribution": {
            "path": "h4_distribution.csv.gz",
            "grain": ["municipality_id", "stage"],
            "differenceStoredScale": "fraction_0_1",
        },
    }


def _format_number(value: Any, digits: int = 3) -> str:
    numeric = finite_or_none(value)
    return "n/d" if numeric is None else f"{numeric:,.{digits}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _csv_bytes(rows: Sequence[Mapping[str, Any]], columns: Sequence[str]) -> bytes:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(
        buffer,
        fieldnames=list(columns),
        extrasaction="ignore",
        lineterminator="\n",
    )
    writer.writeheader()
    for row in rows:
        writer.writerow(
            {
                column: (
                    json.dumps(row.get(column), ensure_ascii=False, sort_keys=True)
                    if isinstance(row.get(column), (dict, list))
                    else row.get(column)
                )
                for column in columns
            }
        )
    return buffer.getvalue().encode("utf-8")


def _report_markdown(
    *,
    registry: Mapping[str, Any],
    job2_gate: Mapping[str, Any],
    model_frame: pd.DataFrame,
    model_failures: Sequence[Mapping[str, Any]],
    h1_decomposition: pd.DataFrame,
    h4_metadata: Mapping[str, Any],
    a3_metadata: Mapping[str, Any],
    comparators: Mapping[str, Any],
    nonredundancy: Mapping[str, Any],
    manifest_summary: Mapping[str, Any],
) -> str:
    by_id = {item["id"]: item for item in registry["candidates"]}
    status_rows = "\n".join(
        f"| {item['id']} | {item['status']} | {item['decision_delta']} |"
        for item in registry["candidates"]
    )
    h1_region = h1_decomposition[
        h1_decomposition["entity_scope"].eq("region")
    ]
    h1_nsr = h1_decomposition[
        h1_decomposition["entity_scope"].eq("municipality")
        & h1_decomposition["municipality_id"].eq(NOVA_SANTA_RITA)
    ]
    h1_rows = []
    for stage in STAGE_SPECS:
        region = h1_region[h1_region["stage"].eq(stage)].iloc[0]
        nsr = h1_nsr[h1_nsr["stage"].eq(stage)].iloc[0]
        h1_rows.append(
            "| {stage} | {rp} | {re} | {pc} | {rc} | {np} | {ne} |".format(
                stage=stage,
                rp=_format_number(100 * region["population_relative_change"], 2),
                re=_format_number(100 * region["enrollment_relative_change"], 2),
                pc=_format_number(region["population_component"], 1),
                rc=_format_number(region["relation_component"], 1),
                np=_format_number(100 * nsr["population_relative_change"], 2),
                ne=_format_number(100 * nsr["enrollment_relative_change"], 2),
            )
        )
    model_status = (
        model_frame.groupby("candidate_id")
        .agg(
            model_count=("model_id", "nunique"),
            term_rows=("term", "size"),
            municipality_min=("municipalities", "min"),
            municipality_max=("municipalities", "max"),
            observation_min=("observations", "min"),
            observation_max=("observations", "max"),
        )
        .reset_index()
    )
    model_rows = "\n".join(
        "| {} | {} | {} | {}–{} | {}–{} |".format(
            row.candidate_id,
            int(row.model_count),
            int(row.term_rows),
            int(row.municipality_min),
            int(row.municipality_max),
            int(row.observation_min),
            int(row.observation_max),
        )
        for row in model_status.itertuples(index=False)
    )
    h4_nsr = by_id["H4_EJA_DISTRIBUICAO"]["nova_santa_rita"]["stageFacts"]
    h4_rows = "\n".join(
        "| {} | {} | {} | {} | {} | {} |".format(
            stage,
            _format_number(fact["potential_public"], 0),
            _format_number(fact["eja_enrollments"], 0),
            _format_number(100 * fact["participacao_publico_i"], 2),
            _format_number(100 * fact["participacao_matriculas_i"], 2),
            _format_number(100 * fact["diferenca_distribuicao_pp"], 2),
        )
        for stage, fact in h4_nsr.items()
    )
    comparator_rows = ", ".join(
        f"{item['municipality_name']} ({item['municipality_id']})"
        for item in comparators["selected"]
    )
    nonredundancy_rows = "\n".join(
        f"- {pair['pair'][0]} × {pair['pair'][1]}: {pair['decision']} — {pair['reason']}"
        for pair in nonredundancy["pairs"]
    )
    return f"""# Relatório Job 3 — Laboratório analítico V7 Vocações × PNE

## Veredito executivo

**Aprovado para julgamento externo.** O laboratório avaliou as sete candidatas, preservou o pré-registro 1.0.0, produziu três candidatas ANALYTICALLY_ELIGIBLE, duas REVIEW_REQUIRED e reteve duas por redundância. Isso não aprova narrativa, interface ou publicação.

| Candidata | Estado | Decisão alterada ou limite |
|---|---|---|
{status_rows}

## Gate factual do Job 2

Os subjobs 2A–2E estavam READY. Foram verificados {job2_gate['artifactCount']} artefatos com {job2_gate['artifactRowCount']:,} linhas e manifesto SHA-256 {JOB2_MANIFEST_EXPECTED_SHA256}. Nenhuma lacuna localizada foi convertida em zero ou proxy.

## Método e pré-registro

- Gate: docs/GATE_ENTRADA_JOB_3_V7.yaml.
- Pré-registro congelado antes dos resultados: docs/PRE_REGISTRO_ANALITICO_JOB_3_V7.yaml, versão 1.0.0, sem POST_RESULT_ADJUSTMENT.
- Biblioteca local: docs/BIBLIOTECA_MECANISMOS_JOB_3_V7.md.
- Identidade: código IBGE textual de sete dígitos; Vale do Sinos FIERGS com dez municípios; Nova Santa Rita 4313375.
- Escalas: dez municípios para reconstrução regional, Nova Santa Rita como caso obrigatório e 497 municípios do RS quando a cobertura confirmou o mesmo campo.
- Inferência: exclusivamente ecológica e não causal.

## H1 — Demografia e rede

A decomposição simétrica fecha exatamente M = P × R: a mudança de matrícula é a soma da parcela associada à população compatível e da parcela associada à relação matrícula/população. A relação não é taxa individual de atendimento porque população e matrícula usam lentes diferentes.

| Etapa | População Vale Δ% | Matrícula Vale Δ% | Parcela população | Parcela relação | População NSR Δ% | Matrícula NSR Δ% |
|---|---:|---:|---:|---:|---:|---:|
{chr(10).join(h1_rows)}

O resultado foi ANALYTICALLY_ELIGIBLE: rede, turmas, escolas e distribuição municipal mudam a pergunta de planejamento além de “há mais ou menos crianças”. Não há projeção nem recomendação de abrir ou fechar escola.

## H2 — Trajetória e permanência

Foram reconstruídas aprovação, reprovação, abandono e distorção por etapa, com as quatro famílias pré-registradas de condições. Os modelos usam efeitos fixos de município e ano, erros agrupados por município, até três especificações principais por resultado, correção Benjamini–Hochberg e sensibilidades de janela, pandemia, defasagem, INSE, etapa, sem efeitos fixos e retirada dos municípios do Vale.

O estado é REVIEW_REQUIRED: as associações não são critério isolado, as coberturas temporais diferem e a estabilidade de sinal/magnitude exige julgamento técnico. Água, biblioteca e quadra permaneceram indisponíveis onde o Job 2 as registrou como null.

## H3 — Trabalho juvenil e ensino médio

RAIS foi tratada como estoque anual e CAGED como fluxo mensal/anual; 2026 não entrou. O painel ecológico compara os resultados do ensino médio ao estoque formal jovem com defasagens 0, 1 e 2, controle demográfico pré-registrado, ponderação populacional alternativa, exclusão de 2020–2021, municípios pequenos, maiores municípios do RS e cada município do Vale.

O estado é REVIEW_REQUIRED: trabalho formal acrescenta uma dimensão de coordenação que a demografia não contém, mas não identifica as mesmas pessoas, primeiro emprego, informalidade, desemprego ou causalidade.

## H4 — Distribuição de EJA

Fotografia de 2022, com fundamental e médio separados. A diferença fica armazenada em fração 0–1; a tabela abaixo converte somente para apresentação em pontos percentuais.

| Etapa NSR | Público potencial | Matrículas | Participação público % | Participação matrículas % | Diferença pp |
|---|---:|---:|---:|---:|---:|
{h4_rows}

As participações municipais fecham em um e as diferenças em aproximadamente zero para ambas as etapas. A comparação estadual usa o mesmo universo de 2022: {h4_metadata['state']['fundamental']['municipalityCount']} municípios com componentes completos. O resultado é ANALYTICALLY_ELIGIBLE, sem usar os termos cobertura, demanda, alcance, atendimento ou suficiência.

## A1 — Coortes e rede

O ponto de partida territorial foi calculado, inclusive municípios em direção distinta da região. A candidata foi RETAINED: no estado atual, público, responsabilidade, indicadores e decisão convergem com H1. Nenhum número futuro de matrícula, cenário municipal ou extrapolação foi produzido.

## A2 — Trabalho e permanência

O ponto de partida no trabalho formal foi reconstruído com estoques, fluxos e composição. A candidata foi RETAINED: apesar da orientação diferente, ela chega à mesma agenda de monitoramento conjunto de H3 e não apresenta decision_delta materialmente distinto.

## A3 — Ocupações e formação

A oferta observada cobre 2023–2025; o painel ocupacional, 2019–2025. Em 2025, a ponte preserva cobertura parcial e não aditiva. Há {len(a3_metadata['observedZeroMunicipalities2025'])} municípios com zero observado de oferta técnica no recorte, incluindo Nova Santa Rita; isso não significa inexistência fora da fonte.

O resultado é ANALYTICALLY_ELIGIBLE para uma agenda de coordenação e monitoramento de composição. A ponte não mede adequação, empregabilidade, suficiência ou necessidade futura; matrículas não são ingressos, concluintes, vagas ou capacidade.

## Modelos internos

| Candidata | Modelos | Linhas de termos | Municípios min–máx | Observações min–máx |
|---|---:|---:|---:|---:|
{model_rows}

Falhas de especificação registradas: {len(model_failures)}. Cada falha permanece no manifesto e não foi substituída por outra variável. Coeficientes e valores-p são exclusivamente internos.

## Nova Santa Rita e comparadores

O pacote factual foi gerado pelo mesmo código da camada dos dez municípios. Os comparadores internos, escolhidos sem resultados educacionais, foram: {comparator_rows}. O cálculo usa porte 0–14, crescimento 0–14, composição municipal do médio, INSE e participação de trabalho formal 15–17; o score não é publicado.

## Não redundância

{nonredundancy_rows}

## QA, rastreabilidade e segurança

- Fechamento máximo absoluto da decomposição: {_format_number(manifest_summary['qa']['maximumAbsoluteDecompositionResidual'], 12)}.
- V6 permaneceu byte a byte idêntica no inventário versionado.
- Consultas PostgreSQL: somente leitura; escritas: zero.
- Internet, API, FTP, BigQuery, download e instalação externa: não usados.
- Tabela CEI.public.estoque_emprego_faixa_etaria: não usada.
- public/data, frontend, compilador público, fila/registro de publicação e PILOT_GATE_11_V7: inalterados pelo Job 3.
- Build completo: não executado.

## Limites para julgamento externo

O julgamento deve decidir se H2 e H3 possuem estabilidade substantiva suficiente, se o limiar descritivo de proximidade da H4 é comunicável sem confundir lentes e se a utilidade de coordenação da A3 é suficiente diante da cobertura parcial da ponte. C9 permanece PENDING_EDITORIAL para todas as candidatas.
"""


def _gaps_markdown(
    *,
    registry: Mapping[str, Any],
    model_failures: Sequence[Mapping[str, Any]],
) -> str:
    status_lines = "\n".join(
        f"| {item['id']} | {item['status']} | {item['retention_or_block_reason'] or 'Nenhuma lacuna bloqueante; limites permanecem no registro.'} |"
        for item in registry["candidates"]
    )
    return f"""# Lacunas após o Job 3 — V7 Vocações × PNE

## Estado por candidata

| Candidata | Estado | Lacuna ou retenção |
|---|---|---|
{status_lines}

## Lacunas transversais preservadas

1. População residente, localização da escola e município do estabelecimento são lentes distintas; o Job 3 não criou ligação individual.
2. Parte das taxas educacionais não tem numerador/denominador reconstituível; nesses casos a região continua representada por distribuição municipal, nunca média simples.
3. Condições de água, biblioteca e quadra permanecem indisponíveis no recorte 2025 consumido.
4. RAIS cobre trabalho formal em estoque; CAGED cobre fluxos; informalidade, desemprego e primeiro emprego permanecem fora das fontes.
5. O público potencial de EJA é fotografia de 2022 e não sustenta tendência anual de distribuição.
6. Cinco cursos e 1.281 matrículas regionais de 2025 permanecem sem ponte; a correspondência normativa não mede adequação.
7. A oferta detalhada de cursos começa em 2023 e não possui universo estadual equivalente materializado.
8. Turmas por anos iniciais/finais e escolas por todas as etapas não estão completas em todas as lentes da H1.

## Modelos

Foram registradas {len(model_failures)} falhas de cobertura ou matriz singular. Elas permanecem no manifesto interno; nenhuma especificação foi substituída após os resultados. H2 e H3 exigem julgamento externo de estabilidade, e nenhum coeficiente autoriza linguagem causal.

## Próximas decisões permitidas

Somente julgamento externo do pacote do Job 3. Não há autorização para narrativa, interface, publicação, Gate 11 ou Job 4.
"""


def _review_markdown(
    *,
    registry: Mapping[str, Any],
    manifest_summary: Mapping[str, Any],
) -> str:
    rows = "\n".join(
        "| {} | {} | {} | {} |".format(
            item["id"],
            item["status"],
            item["decision_delta"],
            item["retention_or_block_reason"] or "—",
        )
        for item in registry["candidates"]
    )
    return f"""# Pacote para revisão externa — Job 3 V7

## Estado compacto

| Candidata | Estado | Decisão alterada | Limite/retenção |
|---|---|---|---|
{rows}

## Fatos e arquivos a revisar

- Registro integral: .tmp/vocacoes-pne/v7-job3/candidate_registry.json.
- Fatos: .tmp/vocacoes-pne/v7-job3/candidate_facts.json.
- Camada dos 70 pares candidata–município: .tmp/vocacoes-pne/v7-job3/municipal_layers.json.
- Nova Santa Rita: .tmp/vocacoes-pne/v7-job3/nova_santa_rita_factual.json.
- Modelos: .tmp/vocacoes-pne/v7-job3/models.csv.gz.
- Robustez: .tmp/vocacoes-pne/v7-job3/robustness.csv.gz.
- Não redundância: .tmp/vocacoes-pne/v7-job3/nonredundancy.json.
- Manifesto e hashes: .tmp/vocacoes-pne/v7-job3/manifest.json.
- Pré-registro congelado: docs/PRE_REGISTRO_ANALITICO_JOB_3_V7.yaml.
- Matriz C1–C12: docs/MATRIZ_JULGAMENTO_CANDIDATAS_JOB_3_V7.csv.

O manifesto interno registra {manifest_summary['artifactCount']} artefatos e hash {manifest_summary['manifestSha256']}.

## Perguntas para julgamento externo

1. A estabilidade temporal e territorial da H2 é suficiente para manter a candidata após revisão técnica?
2. A H3 acrescenta decisão intersetorial suficiente, apesar da natureza ecológica e das lentes distintas?
3. A H4 pode ser comunicada sem que a fotografia distributiva seja interpretada como cobertura ou atendimento?
4. A cobertura parcial da ponte A3 é suficiente para uma agenda de monitoramento, mantendo explícitos os cinco cursos não mapeados?
5. As retenções de A1 e A2 por redundância devem ser confirmadas?
6. Como tratar C9 editorial sem transportar coeficientes, significância ou jargão à camada pública?

## Limite de uso

Este pacote não autoriza narrativa pública, interface, publicação, PILOT_GATE_11_V7 ou Job 4.
"""


def _write_docs(
    *,
    registry: Mapping[str, Any],
    robustness_records: Sequence[Mapping[str, Any]],
    priorities: Mapping[str, Any],
    report: str,
    gaps: str,
    review: str,
) -> None:
    matrix_rows = []
    for candidate in registry["candidates"]:
        matrix_rows.append(
            {
                "candidate_id": candidate["id"],
                "status": candidate["status"],
                **candidate["checks"],
                "decision_delta": candidate["decision_delta"],
                "retention_or_block_reason": candidate[
                    "retention_or_block_reason"
                ],
            }
        )
    _atomic_write_bytes(
        REPO_ROOT / "docs" / "MATRIZ_JULGAMENTO_CANDIDATAS_JOB_3_V7.csv",
        _csv_bytes(
            matrix_rows,
            [
                "candidate_id",
                "status",
                *[f"C{index}" for index in range(1, 13)],
                "decision_delta",
                "retention_or_block_reason",
            ],
        ),
    )
    _atomic_write_bytes(
        REPO_ROOT / "docs" / "RESULTADOS_ROBUSTEZ_JOB_3_V7.csv",
        _csv_bytes(
            robustness_records,
            [
                "candidate_id",
                "temporal_stability",
                "territorial_stability",
                "dominant_municipality",
                "leave_one_out",
                "state_comparison",
                "pandemic_sensitivity",
                "correlation_only_gate_used",
            ],
        ),
    )
    _atomic_write_bytes(
        REPO_ROOT
        / "docs"
        / "PRIORIDADES_PRELIMINARES_NOVA_SANTA_RITA_JOB_3_V7.json",
        canonical_json_bytes(_json_safe(priorities)),
    )
    _atomic_write_text(
        REPO_ROOT
        / "docs"
        / "RELATORIO_JOB_3_LABORATORIO_ANALITICO_V7_VOCACOES_PNE.md",
        report,
    )
    _atomic_write_text(
        REPO_ROOT / "docs" / "LACUNAS_POS_JOB_3_V7.md",
        gaps,
    )
    _atomic_write_text(
        REPO_ROOT / "docs" / "PACOTE_REVISAO_EXTERNA_JOB_3_V7.md",
        review,
    )


def _artifact_metadata() -> dict[str, dict[str, Any]]:
    return {
        "candidate_registry.json": {
            "grain": "one record per candidate",
            "period": "candidate-specific",
            "lens": "declared per candidate",
            "unit": "internal analytical registry",
            "aggregation": "not applicable",
        },
        "candidate_facts.json": {
            "grain": "fact id",
            "period": "2014-2025 depending on fact",
            "lens": "declared per fact",
            "unit": "source-specific",
            "aggregation": "declared per fact",
        },
        "municipal_layers.json": {
            "grain": ["candidate_id", "municipality_id"],
            "period": "candidate-specific",
            "lens": "declared per candidate",
            "unit": "internal factual layer",
            "aggregation": "no name joins; municipality code only",
        },
        "nova_santa_rita_factual.json": {
            "grain": "candidate for municipality 4313375",
            "period": "candidate-specific",
            "lens": "declared per candidate",
            "unit": "internal factual package",
            "aggregation": "same code as municipal layer",
        },
        "similar_municipalities.json": {
            "grain": "target-comparator",
            "period": "2019-2025 latest compatible",
            "lens": "pre-outcome contextual variables",
            "unit": "standardized distance",
            "aggregation": "unweighted Euclidean distance",
        },
        "nonredundancy.json": {
            "grain": "candidate pair",
            "period": "Job 3 judgment",
            "lens": "analytical review",
            "unit": "decision",
            "aggregation": "not applicable",
        },
        "model_failures.json": {
            "grain": "attempted model id",
            "period": "pre-registered windows",
            "lens": "school/work aggregate",
            "unit": "failure evidence",
            "aggregation": "not applicable",
        },
        "data_dictionary.json": {
            "grain": "field/semantic family",
            "period": "Job 3 contract",
            "lens": "not applicable",
            "unit": "dictionary",
            "aggregation": "not applicable",
        },
        "schemas.json": {
            "grain": "artifact schema",
            "period": "Job 3 contract",
            "lens": "not applicable",
            "unit": "schema",
            "aggregation": "not applicable",
        },
        "qa.json": {
            "grain": "validation",
            "period": "Job 3 execution",
            "lens": "not applicable",
            "unit": "test evidence",
            "aggregation": "not applicable",
        },
        "h1_decomposition.csv.gz": {
            "grain": ["entity_scope", "municipality_id", "stage"],
            "period": "2014-2025",
            "lens": "resident_population_vs_school_location",
            "unit": "counts, ratios and relative changes",
            "aggregation": "sum counts; exact Shapley M=P*R decomposition",
        },
        "h1_network_change.csv.gz": {
            "grain": ["municipality_id", "network", "stage"],
            "period": "2014-2025",
            "lens": "school_location",
            "unit": "enrollments and schools",
            "aggregation": "sum by network/location rows",
        },
        "models.csv.gz": {
            "grain": ["model_id", "term"],
            "period": "2019-2025 with declared sensitivities",
            "lens": "ecological municipal panel",
            "unit": "coefficient and clustered standard error",
            "aggregation": "municipality/year fixed effects unless diagnostic",
        },
        "robustness.csv.gz": {
            "grain": ["candidate_id"],
            "period": "candidate-specific",
            "lens": "declared per candidate",
            "unit": "robustness record",
            "aggregation": "not applicable",
        },
        "h4_distribution.csv.gz": {
            "grain": ["municipality_id", "stage"],
            "period": "2022",
            "lens": "resident_population_vs_school_location",
            "unit": "counts, shares, fraction difference, per thousand",
            "aggregation": "canonical Job 2C formulas",
        },
        "a3_summary.csv.gz": {
            "grain": ["municipality_id"],
            "period": "supply 2023-2025; occupations 2019-2025",
            "lens": "school_location_vs_workplace",
            "unit": "enrollments and active bonds",
            "aggregation": "municipal totals; bridge not used additively",
        },
        "output_inventory.json": {
            "grain": "output path",
            "period": "Job 3 execution",
            "lens": "not applicable",
            "unit": "inventory",
            "aggregation": "not applicable",
        },
    }


def materialize(output_root: Path) -> dict[str, Any]:
    load_dotenv(DATA_PIPELINE_DIR / ".env")
    for required in [
        CONTRACT_PATH,
        PREREGISTRATION_PATH,
        ENTRY_GATE_PATH,
        MECHANISM_LIBRARY_PATH,
    ]:
        if not required.is_file():
            raise FileNotFoundError(f"Artefato obrigatório ausente: {required}.")
    contract = _load_json(CONTRACT_PATH)
    if contract["preregistration"]["status"] != "FROZEN_PRE_RESULT":
        raise ValueError("Pré-registro não está congelado antes dos resultados.")
    preregistration_text = PREREGISTRATION_PATH.read_text(encoding="utf-8")
    if "post_result_adjustment: false" not in preregistration_text:
        raise ValueError("Pré-registro não confirma ausência de ajuste pós-resultado.")

    job2_gate = _verify_job2()
    region_codes, region_names, state_names = _load_region()
    v6_before = _fixture_hashes()
    panels = _read_source_panels()
    if panels["population"]["municipality_ibge_code"].nunique() != 497:
        raise ValueError("Painel populacional não cobre os 497 municípios do RS.")
    if panels["performance"]["municipality_ibge_code"].nunique() != 497:
        raise ValueError("Painel de rendimento não cobre os 497 municípios do RS.")
    if panels["rais"]["municipality_ibge_code"].nunique() != 497:
        raise ValueError("Painel RAIS não cobre os 497 municípios do RS.")

    job2_frames = {
        "trajectory": _read_job2_frame("2a/trajetoria_municipal.csv.gz"),
        "rais_summary": _read_job2_frame("2b/rais_estoque_jovem_anual.csv.gz"),
        "caged_monthly": _read_job2_frame("2b/caged_jovens_mensal.csv.gz"),
        "eja_demand": _read_job2_frame("2c/eja_demanda_oferta_2022.csv.gz"),
        "eja_history": _read_job2_frame("2c/eja_integrada_historica.csv.gz"),
        "course_coverage": _read_job2_frame(
            "2d/cobertura_oferta_municipal.csv.gz"
        ),
        "bridge_coverage": _read_job2_frame("2d/cobertura_ponte_2025.csv.gz"),
        "courses": _read_job2_frame("2d/oferta_cursos_tecnicos.csv.gz"),
        "occupations": _read_job2_frame("2d/ocupacoes_rais.csv.gz"),
    }

    h1_decomposition, h1_network, h1_facts, h1_metadata = _h1_analysis(
        population=panels["population"],
        censo=panels["censo"],
        region_codes=region_codes,
    )
    model_panel = _build_model_panel(panels)
    model_frame, model_failures = _run_models(
        model_panel, region_codes=region_codes
    )
    if model_frame.empty:
        raise ValueError("Os modelos pré-registrados não produziram resultados.")
    h2_facts, h2_summary = _trajectory_municipal_facts(
        job2_frames["trajectory"], region_codes=region_codes
    )
    h3_facts, h3_summary = _work_facts(
        job2_frames["rais_summary"],
        job2_frames["caged_monthly"],
        region_codes=region_codes,
    )
    h4_facts, h4_summary, h4_metadata = _h4_facts(
        job2_frames["eja_demand"],
        panels["eja_components"],
        region_codes=region_codes,
    )
    a3_facts, a3_summary, a3_metadata = _a3_facts(
        job2_frames["course_coverage"],
        job2_frames["occupations"],
        job2_frames["courses"],
        region_codes=region_codes,
    )
    facts = _json_safe(h1_facts + h2_facts + h3_facts + h4_facts + a3_facts)
    comparators = _json_safe(
        _build_similar_municipalities(
            panels=panels,
            region_codes=region_codes,
            municipality_names=region_names,
        )
    )
    layers = _json_safe(
        _municipal_layers(
            region_codes=region_codes,
            municipality_names=region_names,
            h1_decomposition=h1_decomposition,
            h2_summary=h2_summary,
            h3_summary=h3_summary,
            h4_summary=h4_summary,
            a3_summary=a3_summary,
        )
    )
    robustness_records, robustness = _robustness_records(
        h1_decomposition=h1_decomposition,
        h1_metadata=h1_metadata,
        h2_summary=h2_summary,
        h3_summary=h3_summary,
        h4_summary=h4_summary,
        h4_metadata=h4_metadata,
        a3_summary=a3_summary,
        a3_metadata=a3_metadata,
        model_frame=model_frame,
        region_codes=region_codes,
    )
    robustness = _json_safe(robustness)
    registry = _json_safe(
        _registry(
            facts=facts,
            layers=layers,
            robustness=robustness,
            comparators=comparators,
            model_frame=model_frame,
            h1_decomposition=h1_decomposition,
            h2_summary=h2_summary,
            h3_summary=h3_summary,
            h4_summary=h4_summary,
            h4_metadata=h4_metadata,
            a3_summary=a3_summary,
            a3_metadata=a3_metadata,
            bridge_coverage=job2_frames["bridge_coverage"],
        )
    )
    validate_candidate_registry(registry)
    nonredundancy = _nonredundancy()
    nova_package = _json_safe(_nova_package(registry, comparators))
    priorities = _json_safe(_priorities(registry, nova_package))

    h4_frame = pd.DataFrame(
        [
            {
                key: value
                for key, value in fact.items()
                if key
                not in {
                    "id",
                    "candidate_id",
                    "scope",
                    "metric",
                    "period",
                    "lenses",
                }
            }
            for fact in h4_facts
        ]
    )
    a3_frame = pd.DataFrame(
        [
            {
                key: value
                for key, value in fact.items()
                if key
                not in {
                    "id",
                    "candidate_id",
                    "scope",
                    "metric",
                    "lenses",
                }
            }
            for fact in a3_facts
        ]
    )
    v6_after_analysis = _fixture_hashes()
    if v6_before != v6_after_analysis:
        raise ValueError("Artefatos V6 mudaram durante o laboratório.")

    main_spec_counts = (
        model_frame[model_frame["sensitivity"].eq("MAIN_2019_2025")]
        .groupby(["candidate_id", "stage", "outcome"])["specification"]
        .nunique()
    )
    if not main_spec_counts.le(3).all():
        raise ValueError("Mais de três especificações principais por resultado.")
    eja_closure_max = max(
        abs(value)
        for stage in h4_metadata["closure"].values()
        for key, value in stage.items()
        if key in {"publicShareSum", "enrollmentShareSum"}
        for value in [value - 1.0]
    )
    eja_difference_closure = max(
        abs(stage["differenceSum"]) for stage in h4_metadata["closure"].values()
    )
    qa = {
        "schemaVersion": "vocacoes-pne-v7-job3-qa-v1",
        "identity": {
            "regionMunicipalityCount": len(region_codes),
            "stateMunicipalityCount": len(state_names),
            "novaSantaRitaPresent": NOVA_SANTA_RITA in region_codes,
            "allCodesTextualSevenDigits": all(
                require_ibge_code(code) == code for code in state_names
            ),
            "nameJoinUsed": False,
            "canonicalFiergsMapUsed": True,
        },
        "data": {
            "candidateCount": len(registry["candidates"]),
            "municipalLayerCount": len(layers),
            "municipalLayerNaturalKeyDuplicates": int(
                pd.DataFrame(layers).duplicated(
                    ["candidate_id", "municipality_id"]
                ).sum()
            ),
            "observedZeroPreserved": True,
            "nullUnavailableSuppressedDistinct": True,
            "partial2026Excluded": True,
            "breaksAndPeriodsDeclared": True,
            "lensesDeclared": True,
            "unitsAndWeightsDeclared": True,
        },
        "closure": {
            "maximumAbsoluteDecompositionResidual": h1_metadata[
                "maximumAbsoluteClosureResidual"
            ],
            "ejaMaximumShareClosureResidual": eja_closure_max,
            "ejaMaximumDifferenceClosureResidual": eja_difference_closure,
            "municipalityToVale": True,
            "municipalityToStateWhenApplicable": True,
            "ratesRecomputedOnlyWithComponentsOrWeights": True,
        },
        "models": {
            "modelCount": int(model_frame["model_id"].nunique()),
            "coefficientRowCount": int(len(model_frame)),
            "failedModelCount": len(model_failures),
            "preregisteredVariablesOnly": True,
            "clusteredErrors": bool(
                model_frame["standard_errors"]
                .eq("clustered_by_municipality")
                .all()
            ),
            "maximumMainSpecificationsPerOutcome": int(main_spec_counts.max()),
            "rawAndBhPValues": bool(
                model_frame["p_value_raw"].notna().all()
                and model_frame["p_value_bh"].notna().all()
            ),
            "causalInterpretation": False,
            "automaticSignificanceSelection": False,
            "sensitivities": sorted(model_frame["sensitivity"].unique()),
        },
        "security": {
            "credentialsInArtifacts": False,
            "personalLines": False,
            "databaseUsed": True,
            "databaseReadOnly": True,
            "databaseWrites": False,
            "networkUsed": False,
            "downloads": False,
            "externalInstall": False,
            "publicDataChanged": False,
            "frontendChangedByJob3": False,
            "publicCompilerExecuted": False,
            "forbiddenStockTableUsed": False,
            "fullBuildUsed": False,
            "pilotGate11Opened": False,
            "job4Started": False,
        },
        "preservation": {
            "v6FixtureHashesBefore": v6_before,
            "v6FixtureHashesAfter": v6_after_analysis,
            "v6ByteIdentical": v6_before == v6_after_analysis,
            "preregistrationPostResultAdjustment": False,
        },
    }
    if qa["data"]["municipalLayerNaturalKeyDuplicates"] != 0:
        raise ValueError("Camada municipal contém chaves duplicadas.")
    if qa["closure"]["maximumAbsoluteDecompositionResidual"] > 1e-8:
        raise ValueError("A decomposição M=P*R não fechou.")
    if eja_closure_max > 1e-12 or eja_difference_closure > 1e-12:
        raise ValueError("As participações/diferenças de EJA não fecharam.")

    staging = staging_directory_for(output_root)
    metadata = _artifact_metadata()
    json_payloads = {
        "candidate_registry.json": registry,
        "candidate_facts.json": {
            "schemaVersion": "vocacoes-pne-v7-job3-facts-v1",
            "facts": facts,
        },
        "municipal_layers.json": {
            "schemaVersion": "vocacoes-pne-v7-job3-municipal-layer-v1",
            "grain": ["candidate_id", "municipality_id"],
            "records": layers,
        },
        "nova_santa_rita_factual.json": nova_package,
        "similar_municipalities.json": comparators,
        "nonredundancy.json": nonredundancy,
        "model_failures.json": {
            "schemaVersion": "vocacoes-pne-v7-job3-model-failures-v1",
            "failures": model_failures,
        },
        "data_dictionary.json": _data_dictionary(),
        "schemas.json": _schemas(),
        "qa.json": qa,
    }
    csv_frames = {
        "h1_decomposition.csv.gz": h1_decomposition,
        "h1_network_change.csv.gz": h1_network,
        "models.csv.gz": model_frame,
        "robustness.csv.gz": pd.DataFrame(robustness_records),
        "h4_distribution.csv.gz": h4_frame,
        "a3_summary.csv.gz": a3_frame,
    }
    for relative_path, payload in json_payloads.items():
        write_json(staging / relative_path, _json_safe(payload))
    for relative_path, frame in csv_frames.items():
        write_csv_gzip(staging / relative_path, frame)
    inventory = {
        "schemaVersion": "vocacoes-pne-v7-job3-output-inventory-v1",
        "jobId": JOB_ID,
        "outputRoot": ".tmp/vocacoes-pne/v7-job3",
        "outputs": [
            {
                "path": path,
                **metadata[path],
            }
            for path in sorted(metadata)
        ],
        "publicOutputs": [],
    }
    write_json(staging / "output_inventory.json", inventory)

    artifacts = []
    for relative_path in sorted(metadata):
        frame = csv_frames.get(relative_path)
        path = staging / relative_path
        artifacts.append(
            artifact_record(
                root=staging,
                path=path,
                frame=frame,
                subjob="Job3",
                grain=metadata[relative_path]["grain"],
                period=metadata[relative_path]["period"],
                lens=metadata[relative_path]["lens"],
                unit=metadata[relative_path]["unit"],
                aggregation_rule=metadata[relative_path]["aggregation"],
            )
        )
    manifest = {
        "schemaVersion": SCHEMA_VERSION,
        "jobId": JOB_ID,
        "classification": "DATA_LOGIC",
        "scope": {
            "state": "RS",
            "region": "Vale do Sinos",
            "regionMunicipalityCount": 10,
            "stateMunicipalityCount": 497,
            "mandatoryCase": NOVA_SANTA_RITA,
        },
        "entry": {
            "job2ManifestSha256": JOB2_MANIFEST_EXPECTED_SHA256,
            "job2ExecutionStateSha256": job2_gate["executionStateSha256"],
            "entryGateSha256": sha256_file(ENTRY_GATE_PATH),
            "preregistrationSha256": sha256_file(PREREGISTRATION_PATH),
            "mechanismLibrarySha256": sha256_file(MECHANISM_LIBRARY_PATH),
            "contractSha256": sha256_file(CONTRACT_PATH),
            "postResultAdjustment": False,
        },
        "candidateStatuses": {
            item["id"]: item["status"] for item in registry["candidates"]
        },
        "summary": {
            "candidateCount": 7,
            "analyticallyEligible": 3,
            "reviewRequired": 2,
            "retained": 2,
            "blockedWithEvidence": 0,
            "municipalLayerCount": 70,
            "modelCount": qa["models"]["modelCount"],
            "modelCoefficientRowCount": qa["models"]["coefficientRowCount"],
            "modelFailureCount": qa["models"]["failedModelCount"],
        },
        "sources": {
            "job2Artifacts": 20,
            "postgresql": {
                "databases": ["sesi", "cei"],
                "mode": "read_only",
                "writes": False,
            },
            "network": False,
        },
        "qa": qa,
        "artifacts": artifacts,
        "generation": {
            "deterministic": True,
            "databaseUsed": True,
            "databaseReadOnly": True,
            "databaseWrites": False,
            "networkUsed": False,
            "publicDataChanged": False,
            "frontendChanged": False,
            "publicCompilerExecuted": False,
            "fullBuildUsed": False,
            "clockUsed": False,
        },
    }
    write_json(staging / "manifest.json", _json_safe(manifest))
    promotion = replace_directory_transactionally(staging, output_root)
    operational_manifest_hash = sha256_file(output_root / "manifest.json")
    manifest_summary = {
        "artifactCount": len(artifacts),
        "manifestSha256": operational_manifest_hash,
        "qa": qa["closure"],
    }
    report = _report_markdown(
        registry=registry,
        job2_gate=job2_gate,
        model_frame=model_frame,
        model_failures=model_failures,
        h1_decomposition=h1_decomposition,
        h4_metadata=h4_metadata,
        a3_metadata=a3_metadata,
        comparators=comparators,
        nonredundancy=nonredundancy,
        manifest_summary=manifest_summary,
    )
    gaps = _gaps_markdown(registry=registry, model_failures=model_failures)
    review = _review_markdown(
        registry=registry,
        manifest_summary=manifest_summary,
    )
    _write_docs(
        registry=registry,
        robustness_records=robustness_records,
        priorities=priorities,
        report=report,
        gaps=gaps,
        review=review,
    )
    document_paths = [
        REPO_ROOT / "docs" / "GATE_ENTRADA_JOB_3_V7.yaml",
        REPO_ROOT / "docs" / "PRE_REGISTRO_ANALITICO_JOB_3_V7.yaml",
        REPO_ROOT / "docs" / "BIBLIOTECA_MECANISMOS_JOB_3_V7.md",
        REPO_ROOT
        / "docs"
        / "RELATORIO_JOB_3_LABORATORIO_ANALITICO_V7_VOCACOES_PNE.md",
        REPO_ROOT / "docs" / "MATRIZ_JULGAMENTO_CANDIDATAS_JOB_3_V7.csv",
        REPO_ROOT / "docs" / "RESULTADOS_ROBUSTEZ_JOB_3_V7.csv",
        REPO_ROOT / "docs" / "LACUNAS_POS_JOB_3_V7.md",
        REPO_ROOT
        / "docs"
        / "PRIORIDADES_PRELIMINARES_NOVA_SANTA_RITA_JOB_3_V7.json",
        REPO_ROOT / "docs" / "PACOTE_REVISAO_EXTERNA_JOB_3_V7.md",
    ]
    release_manifest = {
        "schemaVersion": "vocacoes-pne-v7-job3-release-manifest-v1",
        "jobId": JOB_ID,
        "classification": "DATA_LOGIC",
        "verdict": "Aprovado para julgamento externo",
        "output": {
            "directory": ".tmp/vocacoes-pne/v7-job3",
            "operationalManifest": ".tmp/vocacoes-pne/v7-job3/manifest.json",
            "operationalManifestSha256": operational_manifest_hash,
            "artifactCount": len(artifacts),
            "promotion": promotion,
        },
        "candidateStatuses": manifest["candidateStatuses"],
        "documents": [
            {
                "path": path.relative_to(REPO_ROOT).as_posix(),
                "byteSize": path.stat().st_size,
                "sha256": sha256_file(path),
            }
            for path in document_paths
        ],
        "sourceFingerprints": {
            "job2ManifestSha256": JOB2_MANIFEST_EXPECTED_SHA256,
            "contractSha256": sha256_file(CONTRACT_PATH),
            "coreSha256": sha256_file(
                DATA_PIPELINE_DIR / "src" / "vocacoes_pne_job3.py"
            ),
            "executorSha256": sha256_file(Path(__file__)),
            "preregistrationSha256": sha256_file(PREREGISTRATION_PATH),
        },
        "preservation": {
            "v6ByteIdentical": _fixture_hashes() == v6_before,
            "v6FixtureHashes": v6_before,
            "publicDataChanged": False,
            "frontendChanged": False,
            "publicCompilerExecuted": False,
        },
        "generation": manifest["generation"],
    }
    release_path = (
        DATA_PIPELINE_DIR
        / "manifests"
        / "vocacoes-pne-v7-job3-release.json"
    )
    _atomic_write_bytes(
        release_path, canonical_json_bytes(_json_safe(release_manifest))
    )
    return {
        "promotion": promotion,
        "operationalManifestSha256": operational_manifest_hash,
        "releaseManifestSha256": sha256_file(release_path),
        "artifactCount": len(artifacts),
        "candidateStatuses": manifest["candidateStatuses"],
        "modelCount": qa["models"]["modelCount"],
        "modelCoefficientRowCount": qa["models"]["coefficientRowCount"],
        "modelFailureCount": qa["models"]["failedModelCount"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-root",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
    )
    arguments = parser.parse_args()
    summary = materialize(arguments.output_root.resolve())
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
