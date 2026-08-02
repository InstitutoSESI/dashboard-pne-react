"""Caminhos e configurações externas compartilhados pelo pipeline."""

from __future__ import annotations

import os
from pathlib import Path


DATA_PIPELINE_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = DATA_PIPELINE_DIR.parent
CONFIG_DIR = REPO_ROOT / "config"
STATE_CONFIG_DIR = CONFIG_DIR / "states"
MUNICIPALITY_REGISTRY_DIR = CONFIG_DIR / "municipalities"
EDUCATION_MUNICIPALITY_ROUTE_COMPATIBILITY_DIR = (
    CONFIG_DIR / "compatibility" / "education-municipality-routes"
)
PUBLIC_DATA_DIR = REPO_ROOT / "public" / "data"
PIPELINE_EXPORT_DIR = DATA_PIPELINE_DIR / "export"
STATIC_PARTITIONED_DATA_DIR = PIPELINE_EXPORT_DIR / "static_partitioned"
MUNICIPAL_FINANCE_EXPORT_DIR = PIPELINE_EXPORT_DIR / "municipal_finance"
EDUCATION_DATA_DIR = PUBLIC_DATA_DIR / "educacao"
SESI_DB_DIR = Path(
    os.environ.get("SESI_DB_DIR", REPO_ROOT.parent / "SESI" / "DB")
).resolve()
HIGHER_EDUCATION_SOURCE_DIR = Path(
    os.environ.get(
        "HIGHER_EDUCATION_SOURCE_DIR",
        SESI_DB_DIR / "data" / "sinopse_educacao_superior",
    )
).resolve()
CENSO_ESCOLAR_SOURCE_DIR = Path(
    os.environ.get(
        "CENSO_ESCOLAR_SOURCE_DIR",
        SESI_DB_DIR / "data" / "censo_escolar",
    )
).resolve()
POPULATION_PROJECTION_SOURCE_PATH = Path(
    os.environ.get(
        "POPULATION_PROJECTION_SOURCE_PATH",
        SESI_DB_DIR
        / "data"
        / "projecao_populacao"
        / "projecao_pop.xlsx",
    )
).resolve()
