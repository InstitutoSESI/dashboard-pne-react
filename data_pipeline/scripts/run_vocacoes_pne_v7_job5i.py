from __future__ import annotations

from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from data_pipeline.src.vocacoes_pne_job5i import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
