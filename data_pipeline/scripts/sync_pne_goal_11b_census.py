#!/usr/bin/env python3
"""Baixa e materializa os componentes censitários da Meta 11.b."""

from __future__ import annotations

import argparse
import gzip
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pandas as pd


DATA_PIPELINE_DIR = Path(__file__).resolve().parents[1]
if str(DATA_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_PIPELINE_DIR))

from src.data.repository import get_local_postgres_engine  # noqa: E402
from src.data_loader import (  # noqa: E402
    load_censo_populacao_ensino_fundamental_concluido_18_mais_data,
    load_censo_populacao_ensino_fundamental_concluido_18_29_data,
    load_censo_populacao_ensino_medio_15_17_data,
)
from src.pne_goal_11b_census import (  # noqa: E402
    CENSUS_YEAR,
    EXPECTED_MUNICIPALITIES,
    METADATA_URL,
    SNAPSHOT_DIR,
    build_municipal_components,
    data_url,
    parse_response,
    sha256_bytes,
    stable_json_bytes,
    state_ratio,
    validate_metadata,
)
from src.pne_state_context import (  # noqa: E402
    PneStateContext,
    load_pne_state_context,
    resolve_state_snapshot_dir,
)
from src.state_config import (  # noqa: E402
    DEFAULT_STATE_CODE,
    PIPELINE_STATE_ENV_VAR,
)


def download_bytes(url: str, attempts: int = 4, timeout: int = 120) -> bytes:
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "dashboard-pne-react-data-pipeline/1.0",
        },
    )
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            with urlopen(request, timeout=timeout) as response:
                content = response.read()
                return (
                    gzip.decompress(content)
                    if content.startswith(b"\x1f\x8b")
                    else content
                )
        except (HTTPError, URLError, TimeoutError) as error:
            last_error = error
            if attempt < attempts:
                time.sleep(min(2 ** (attempt - 1), 8))
    raise RuntimeError(f"Falha no download oficial: {url}") from last_error


def _local_components(state: PneStateContext) -> tuple[
    list[dict],
    dict[str, int],
    dict[str, int],
]:
    fifteen = load_censo_populacao_ensino_medio_15_17_data()
    eighteen_twenty_nine = (
        load_censo_populacao_ensino_fundamental_concluido_18_29_data()
    )
    eighteen_plus = (
        load_censo_populacao_ensino_fundamental_concluido_18_mais_data()
    )
    frames = [fifteen, eighteen_twenty_nine, eighteen_plus]
    frames = [
        frame.loc[frame["ano"].astype(int) == CENSUS_YEAR].copy()
        for frame in frames
    ]
    for frame in frames:
        if len(frame) != state.expected_municipality_count:
            raise ValueError(
                f"Base local não cobre {state.expected_municipality_count} "
                f"municípios em {CENSUS_YEAR}."
            )
        frame["id_municipio"] = frame["id_municipio"].astype(str)
        if set(frame["id_municipio"]) != state.municipality_ids:
            raise ValueError("Base local diverge do registro municipal configurado.")
    fifteen, eighteen_twenty_nine, eighteen_plus = frames
    local_rows = [
        {
            "municipalityId": str(row.id_municipio),
            "municipalityName": str(row.municipio),
            "year": CENSUS_YEAR,
            "numerator": int(
                row.populacao_15_17_ensino_medio_ou_basica_completa
            ),
            "denominator": int(row.populacao_15_17_total),
            "status": "available",
            "sourceTable": "censo_populacao_ensino_medio_15_17",
        }
        for row in fifteen.sort_values("id_municipio").itertuples()
    ]
    local_18_29 = {
        str(row.id_municipio): int(
            row.populacao_18_29_ensino_fundamental_concluido
        )
        for row in eighteen_twenty_nine.itertuples()
    }
    local_18_plus = {
        str(row.id_municipio): int(
            row.populacao_18_mais_ensino_fundamental_concluido
        )
        for row in eighteen_plus.itertuples()
    }
    return local_rows, local_18_29, local_18_plus


def _reconcile(
    rows: list[dict],
    local_18_29: dict[str, int],
    local_18_plus: dict[str, int],
) -> dict[str, int]:
    differences_18_29 = 0
    differences_18_plus = 0
    for row in rows:
        municipality_id = row["municipalityId"]
        observed_18_29 = (
            int(row["eighteenToTwentyFour"]["numerator"])
            + int(row["twentyFiveToTwentyNine"]["numerator"])
        )
        differences_18_29 += (
            observed_18_29 != local_18_29[municipality_id]
        )
        differences_18_plus += (
            int(row["eighteenPlus"]["numerator"])
            != local_18_plus[municipality_id]
        )
    if differences_18_29 or differences_18_plus:
        raise ValueError(
            "Numeradores locais divergem da SIDRA 10061: "
            f"18–29={differences_18_29}; 18+={differences_18_plus}."
        )
    return {
        "municipalities": len(rows),
        "fifteenToTwentyNineNumeratorDifferences": differences_18_29,
        "eighteenPlusNumeratorDifferences": differences_18_plus,
    }


def _atomic_write_directory(output_dir: Path, files: dict[str, bytes]) -> None:
    target = output_dir.resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(
        tempfile.mkdtemp(prefix=f".{target.name}.tmp-", dir=target.parent)
    )
    try:
        for filename, content in sorted(files.items()):
            path = temporary / filename
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        if target.exists():
            backup = target.parent / f".{target.name}.previous"
            if backup.exists():
                shutil.rmtree(backup)
            target.replace(backup)
            temporary.replace(target)
            shutil.rmtree(backup)
        else:
            temporary.replace(target)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def _apply_tables(rows: list[dict], local_rows: list[dict]) -> None:
    components = pd.DataFrame(
        [
            {
                "ano": row["year"],
                "id_municipio": row["municipalityId"],
                "municipio": row["municipalityName"],
                "populacao_18_24_total": row["eighteenToTwentyFour"][
                    "denominator"
                ],
                "populacao_25_29_total": row["twentyFiveToTwentyNine"][
                    "denominator"
                ],
                "populacao_18_mais_total": row["eighteenPlus"]["denominator"],
                "populacao_18_24_fundamental_concluido": row[
                    "eighteenToTwentyFour"
                ]["numerator"],
                "populacao_25_29_fundamental_concluido": row[
                    "twentyFiveToTwentyNine"
                ]["numerator"],
                "populacao_18_mais_fundamental_concluido": row["eighteenPlus"][
                    "numerator"
                ],
                "status_valor": row["fifteenPlus"]["status"],
                "tabela_origem": "SIDRA 10061",
            }
            for row in rows
        ]
    )
    fifteen = pd.DataFrame(
        [
            {
                "ano": row["year"],
                "id_municipio": row["municipalityId"],
                "municipio": row["municipalityName"],
                "populacao_15_17_ensino_medio_ou_basica_completa": row[
                    "numerator"
                ],
                "populacao_15_17_total": row["denominator"],
                "status_valor": row["status"],
                "tabela_origem": row["sourceTable"],
            }
            for row in local_rows
        ]
    )
    engine = get_local_postgres_engine()
    with engine.begin() as connection:
        components.to_sql(
            "pne2026_censo_10061_municipal_components",
            connection,
            if_exists="replace",
            index=False,
            method="multi",
            chunksize=1000,
        )
        fifteen.to_sql(
            "pne2026_goal_11b_15_17_snapshot",
            connection,
            if_exists="replace",
            index=False,
            method="multi",
            chunksize=1000,
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", default=DEFAULT_STATE_CODE)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--reference-date", default="2026-07-28")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    state = load_pne_state_context(args.state)
    os.environ[PIPELINE_STATE_ENV_VAR] = state.state_code
    output_dir = (
        args.output_dir.resolve()
        if args.output_dir is not None
        else resolve_state_snapshot_dir(SNAPSHOT_DIR, state.state_code).resolve()
    )

    metadata_bytes = download_bytes(METADATA_URL)
    response_bytes = download_bytes(data_url(state.state_code))
    metadata = json.loads(metadata_bytes)
    response = json.loads(response_bytes)
    source_metadata = validate_metadata(metadata)
    local_rows, local_18_29, local_18_plus = _local_components(state)
    municipality_codes = {
        str(row["municipalityId"]) for row in local_rows
    }
    sidra = parse_response(
        response,
        municipality_codes=municipality_codes,
    )
    rows = build_municipal_components(
        sidra,
        local_rows,
        expected_municipalities=state.expected_municipality_count,
    )
    reconciliation = _reconcile(rows, local_18_29, local_18_plus)

    local_bytes = stable_json_bytes(local_rows)
    components_bytes = stable_json_bytes(rows)
    files = {
        "metadata_10061.json": metadata_bytes,
        f"response_10061_{state.state_code.lower()}_2022.json": response_bytes,
        "component_15_17_local_2022.json": local_bytes,
        "municipal_components.json": components_bytes,
    }
    manifest = {
        "schemaVersion": "pne-goal-11b-census-snapshot-v1",
        "stateCode": state.state_code,
        "stateId": state.state_id,
        "stateName": state.state_name,
        "referenceYear": CENSUS_YEAR,
        "sourceReferenceDate": args.reference_date,
        "source": {
            "provider": "IBGE",
            "survey": "Censo Demográfico 2022 — Educação",
            "aggregate": "10061",
            "metadataUrl": METADATA_URL,
            "dataUrl": data_url(state.state_code),
            "localFifteenToSeventeenTable": (
                "censo_populacao_ensino_medio_15_17"
            ),
        },
        "metadata": source_metadata,
        "files": {
            filename: sha256_bytes(content)
            for filename, content in sorted(files.items())
        },
        "coverage": {
            "municipalityCount": len(rows),
            "availableFifteenToTwentyNine": sum(
                row["fifteenToTwentyNine"]["status"] == "available"
                for row in rows
            ),
            "availableFifteenPlus": sum(
                row["fifteenPlus"]["status"] == "available" for row in rows
            ),
        },
        "reconciliation": reconciliation,
        "stateReferences": {
            "fifteenToTwentyNine": state_ratio(
                rows,
                "fifteenToTwentyNine",
                expected_municipalities=state.expected_municipality_count,
            ),
            "fifteenPlus": state_ratio(
                rows,
                "fifteenPlus",
                expected_municipalities=state.expected_municipality_count,
            ),
        },
        "seriesPolicy": {
            "canonicalSnapshotYear": CENSUS_YEAR,
            "combineWith2010": False,
            "trend": False,
            "projection": False,
            "interpolation": False,
        },
    }
    files["manifest.json"] = stable_json_bytes(manifest)
    _atomic_write_directory(output_dir, files)
    if args.apply:
        _apply_tables(rows, local_rows)
    print(
        json.dumps(
            {
                "state": state.state_code,
                "output": str(output_dir),
                "municipalityCount": len(rows),
                "reconciliation": reconciliation,
                "stateReferences": manifest["stateReferences"],
                "applied": args.apply,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
