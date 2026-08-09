#!/usr/bin/env python3
"""Valida e materializa as relações municipais 14.a, 14.b e 14.d."""

from __future__ import annotations

import argparse
import gzip
import json
import shutil
import sys
import tempfile
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DATA_PIPELINE_DIR = Path(__file__).resolve().parents[1]
if str(DATA_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_PIPELINE_DIR))

from src.pne_goal_14_census import (  # noqa: E402
    SNAPSHOT_DIR,
    TABLES,
    build_snapshot,
    data_url,
    metadata_url,
    sha256_bytes,
)
from src.pne_state_context import (  # noqa: E402
    load_pne_state_context,
    resolve_state_snapshot_dir,
)
from src.state_config import DEFAULT_STATE_CODE  # noqa: E402


def _download(url: str, attempts: int = 4) -> bytes:
    request = Request(url, headers={"User-Agent": "PNE-source-sync/1.0"})
    for attempt in range(1, attempts + 1):
        try:
            with urlopen(request, timeout=120) as response:
                content = response.read()
            return gzip.decompress(content) if content[:2] == b"\x1f\x8b" else content
        except (HTTPError, URLError, TimeoutError):
            if attempt == attempts:
                raise
            time.sleep(attempt)
    raise RuntimeError("Download SIDRA não concluído.")


def _apply(output_dir: Path, files: dict[str, bytes]) -> None:
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(
        tempfile.mkdtemp(prefix=f".{output_dir.name}.tmp-", dir=output_dir.parent)
    )
    try:
        for filename, content in files.items():
            (temporary / filename).write_bytes(content)
        if output_dir.exists():
            backup = output_dir.with_name(f".{output_dir.name}.previous")
            if backup.exists():
                shutil.rmtree(backup)
            output_dir.replace(backup)
            temporary.replace(output_dir)
            shutil.rmtree(backup)
        else:
            temporary.replace(output_dir)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", default=DEFAULT_STATE_CODE)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--reference-date", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    state = load_pne_state_context(args.state)
    output_dir = (
        args.output_dir.resolve()
        if args.output_dir is not None
        else resolve_state_snapshot_dir(SNAPSHOT_DIR, state.state_code).resolve()
    )

    metadata_payloads = {}
    data_payloads = {}
    source_hashes = {}
    for table_id in TABLES:
        metadata_bytes = _download(metadata_url(table_id))
        data_bytes = _download(data_url(table_id, state.state_code))
        metadata_payloads[table_id] = json.loads(metadata_bytes)
        data_payloads[table_id] = json.loads(data_bytes)
        source_hashes[table_id] = {
            "metadataSha256": sha256_bytes(metadata_bytes),
            "dataSha256": sha256_bytes(data_bytes),
        }
    municipality_names = dict(state.municipality_names)
    files = build_snapshot(
        metadata_payloads=metadata_payloads,
        data_payloads=data_payloads,
        source_hashes=source_hashes,
        municipality_names=municipality_names,
        reference_date=args.reference_date,
        state_code=state.state_code,
    )
    if args.apply:
        _apply(output_dir, files)
    print(
        json.dumps(
            {
                "mode": "apply" if args.apply else "check",
                "state": state.state_code,
                "output": str(output_dir),
                "written": bool(args.apply),
                "files": {
                    name: sha256_bytes(content)
                    for name, content in sorted(files.items())
                },
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
