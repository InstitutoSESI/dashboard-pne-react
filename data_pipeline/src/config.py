"""Caminhos e configurações externas compartilhados pelo pipeline."""

from __future__ import annotations

import os
from pathlib import Path


DATA_PIPELINE_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = DATA_PIPELINE_DIR.parent
PUBLIC_DATA_DIR = REPO_ROOT / "public" / "data"
PIPELINE_EXPORT_DIR = DATA_PIPELINE_DIR / "export"
PARTITIONED_DATA_DIR = PIPELINE_EXPORT_DIR / "data_partitioned"
EDUCATION_DATA_DIR = PUBLIC_DATA_DIR / "educacao"
SESI_DB_DIR = Path(
    os.environ.get("SESI_DB_DIR", REPO_ROOT.parent / "SESI" / "DB")
).resolve()
