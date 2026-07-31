"""Fonte agregada e auditável do indicador municipal Criança Alfabetizada."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import zipfile
from pathlib import Path
from typing import Any, Iterable, Mapping


YEARS = (2023, 2024, 2025)
MUNICIPAL_NETWORK_ID = "3"
RS_STATE_ID = "43"
RS_STATE_CODE = "RS"
EXPECTED_MUNICIPALITIES = 497
EXPECTED_AVAILABLE = {2023: 456, 2024: 441, 2025: 463}
EXPECTED_RS_VALUES = {2023: 63.55, 2024: 44.23, 2025: 52.13}
MINIMUM_PARTICIPATION = 70.0

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
SNAPSHOT_DIR = DATA_DIR / "pne_child_literacy"
MUNICIPAL_UNIVERSE_PATH = (
    DATA_DIR / "pne_goal_11b_census_2022" / "municipal_components.json"
)


def stable_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def participation_is_eligible(value: float) -> bool:
    """A divulgação oficial é elegível a partir de 70%, inclusive."""
    return float(value) >= MINIMUM_PARTICIPATION


def _float(value: object, *, field: str) -> float:
    text = str(value or "").strip().replace(",", ".")
    try:
        result = float(text)
    except ValueError as exc:
        raise ValueError(f"Valor inválido em {field}: {value!r}.") from exc
    if not math.isfinite(result) or result < 0 or result > 100:
        raise ValueError(f"Percentual fora do domínio em {field}: {value!r}.")
    return result


def _csv_rows(content: bytes) -> list[dict[str, str]]:
    for encoding in ("utf-8-sig", "latin-1"):
        try:
            text = content.decode(encoding)
            reader = csv.DictReader(io.StringIO(text), delimiter=";")
            rows = list(reader)
            if reader.fieldnames:
                return rows
        except UnicodeDecodeError:
            continue
    raise ValueError("Não foi possível decodificar o CSV oficial.")


def load_municipal_universe(
    path: Path = MUNICIPAL_UNIVERSE_PATH,
) -> dict[str, str]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    universe = {
        str(row["municipalityId"]): str(row["municipalityName"])
        for row in rows
    }
    if len(universe) != EXPECTED_MUNICIPALITIES:
        raise ValueError("Universo municipal do RS deve conter 497 municípios.")
    return universe


def parse_municipal_file(
    content: bytes,
    *,
    year: int,
    universe: Mapping[str, str],
    published_ids: set[str],
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in _csv_rows(content):
        if str(row.get("NU_ANO_AVALIACAO") or "") != str(year):
            continue
        if str(row.get("SG_UF") or "").strip().upper() != RS_STATE_CODE:
            continue
        if str(row.get("ID_TIPO_REDE") or "").strip() != MUNICIPAL_NETWORK_ID:
            continue
        if str(row.get("TP_SERIE") or "").strip() != "2":
            continue
        municipality_id = str(row.get("CO_MUNICIPIO") or "").strip()
        if municipality_id not in universe:
            raise ValueError(
                f"Município inesperado no arquivo de {year}: {municipality_id!r}."
            )
        if municipality_id in result:
            raise ValueError(
                "Duplicidade no grão município × ano × rede municipal: "
                f"{municipality_id}/{year}/3."
            )
        if municipality_id not in published_ids:
            continue
        value = _float(
            row.get("PC_ALUNO_ALFABETIZADO"),
            field="PC_ALUNO_ALFABETIZADO",
        )
        result[municipality_id] = {
            "municipalityId": municipality_id,
            "municipalityName": universe[municipality_id],
            "year": year,
            "dataStatus": "available",
            "value": value,
            "numerator": None,
            "denominator": None,
        }
    expected = EXPECTED_AVAILABLE[year]
    if len(result) != expected:
        raise ValueError(
            f"Cobertura municipal de {year} divergente: {len(result)} != {expected}."
        )
    return result


def participation_by_municipality(
    archive: Path,
    *,
    year: int,
) -> dict[str, float]:
    """Reconstrói somente a taxa de participação que condiciona a divulgação."""
    counts: dict[str, list[int]] = {}
    with zipfile.ZipFile(archive) as bundle:
        matches = [
            name
            for name in bundle.namelist()
            if name.replace("\\", "/").endswith("/TS_ALUNO.csv")
        ]
        if len(matches) != 1:
            raise ValueError(f"TS_ALUNO não é único no ZIP de {year}.")
        with bundle.open(matches[0]) as raw:
            text = io.TextIOWrapper(raw, encoding="latin-1", newline="")
            for row in csv.DictReader(text, delimiter=";"):
                if str(row.get("NU_ANO_AVALIACAO") or "") != str(year):
                    continue
                if str(row.get("SG_UF") or "") != RS_STATE_CODE:
                    continue
                if str(row.get("TP_DEPENDENCIA") or "") != MUNICIPAL_NETWORK_ID:
                    continue
                if str(row.get("TP_SERIE") or "") != "2":
                    continue
                municipality_id = str(row.get("CO_MUNICIPIO") or "")
                count = counts.setdefault(municipality_id, [0, 0])
                count[0] += 1
                count[1] += int(str(row.get("IN_PRESENCA_LP") or "") == "1")
    rates = {
        municipality_id: 100.0 * present / enrolled
        for municipality_id, (enrolled, present) in counts.items()
        if enrolled > 0
    }
    eligible_count = sum(participation_is_eligible(value) for value in rates.values())
    if eligible_count != EXPECTED_AVAILABLE[year]:
        raise ValueError(
            f"Elegibilidade por participação de {year} divergente: "
            f"{eligible_count}."
        )
    return rates


def parse_state_file(content: bytes, *, year: int) -> dict[str, Any]:
    matches = []
    for row in _csv_rows(content):
        if str(row.get("NU_ANO_AVALIACAO") or "") != str(year):
            continue
        if str(row.get("SG_UF") or "").strip().upper() != RS_STATE_CODE:
            continue
        if str(row.get("ID_TIPO_REDE") or "").strip() != MUNICIPAL_NETWORK_ID:
            continue
        if str(row.get("TP_SERIE") or "").strip() != "2":
            continue
        matches.append(row)
    if len(matches) != 1:
        raise ValueError(
            f"Resultado estadual de rede municipal não é único em {year}."
        )
    value = _float(
        matches[0].get("PC_ALUNO_ALFABETIZADO"),
        field="PC_ALUNO_ALFABETIZADO",
    )
    expected = EXPECTED_RS_VALUES[year]
    if abs(value - expected) > 1e-9:
        raise ValueError(
            f"Resultado estadual de {year} divergente: {value} != {expected}."
        )
    return {
        "territoryId": RS_STATE_ID,
        "territoryName": "Rio Grande do Sul",
        "year": year,
        "network": "municipal",
        "dataStatus": "available",
        "value": value,
    }


def _state_source(source_dir: Path, year: int) -> tuple[bytes, Path, str]:
    direct = source_dir / f"TS_ESTADO_{year}.csv"
    if direct.is_file():
        return direct.read_bytes(), direct, direct.name
    archives = sorted(source_dir.glob(f"*{year}.zip"))
    if len(archives) != 1:
        raise FileNotFoundError(
            f"Esperado um TS_ESTADO_{year}.csv ou um ZIP oficial único."
        )
    archive = archives[0]
    with zipfile.ZipFile(archive) as bundle:
        matches = [
            name
            for name in bundle.namelist()
            if name.replace("\\", "/").endswith("/TS_ESTADO.csv")
        ]
        if len(matches) != 1:
            raise ValueError(f"TS_ESTADO não é único no ZIP de {year}.")
        return bundle.read(matches[0]), archive, matches[0]


def build_snapshot(
    source_dir: Path,
    *,
    reference_date: str,
    universe_path: Path = MUNICIPAL_UNIVERSE_PATH,
) -> dict[str, Any]:
    source_root = source_dir.resolve()
    universe = load_municipal_universe(universe_path)
    by_year: dict[int, dict[str, dict[str, Any]]] = {}
    participation_by_year: dict[int, dict[str, float]] = {}
    state_rows: list[dict[str, Any]] = []
    sources: list[dict[str, Any]] = []

    for year in YEARS:
        archives = sorted(source_root.glob(f"*{year}.zip"))
        if len(archives) != 1:
            raise FileNotFoundError(f"Esperado um ZIP oficial único de {year}.")
        participation = participation_by_municipality(archives[0], year=year)
        participation_by_year[year] = participation
        published_ids = {
            municipality_id
            for municipality_id, rate in participation.items()
            if participation_is_eligible(rate)
        }
        municipal_path = source_root / f"TS_MUNICIPIO_{year}.csv"
        municipal_content = municipal_path.read_bytes()
        by_year[year] = parse_municipal_file(
            municipal_content,
            year=year,
            universe=universe,
            published_ids=published_ids,
        )
        sources.append(
            {
                "year": year,
                "role": "municipal_official_percentage",
                "fileName": municipal_path.name,
                "sha256": sha256_bytes(municipal_content),
            }
        )
        state_content, state_path, member = _state_source(source_root, year)
        state_rows.append(parse_state_file(state_content, year=year))
        sources.append(
            {
                "year": year,
                "role": "state_official_percentage",
                "additionalRole": "municipal_publication_eligibility",
                "fileName": state_path.name,
                "archiveMember": member,
                "sha256": sha256_bytes(state_path.read_bytes()),
                "memberSha256": sha256_bytes(state_content),
            }
        )

    municipal_rows = []
    for municipality_id, municipality_name in sorted(universe.items()):
        series = []
        for year in YEARS:
            published = by_year[year].get(municipality_id)
            participation = participation_by_year[year].get(municipality_id)
            series.append(
                (
                    {**published, "participation": participation}
                    if published
                    else None
                )
                or {
                    "municipalityId": municipality_id,
                    "municipalityName": municipality_name,
                    "year": year,
                    "dataStatus": "unavailable",
                    "reasonCode": (
                        "below_minimum_participation"
                        if participation is not None
                        and not participation_is_eligible(participation)
                        else "no_published_result"
                    ),
                    "value": None,
                    "participation": participation,
                    "numerator": None,
                    "denominator": None,
                }
            )
        municipal_rows.append(
            {
                "municipalityId": municipality_id,
                "municipalityName": municipality_name,
                "series": series,
            }
        )

    municipal_bytes = stable_json_bytes(municipal_rows)
    state_bytes = stable_json_bytes(state_rows)
    manifest = {
        "schemaVersion": "pne-child-literacy-snapshot-v1",
        "sourceReferenceDate": reference_date,
        "indicator": "alfabetizacao",
        "network": "municipal",
        "territorialBasis": "municipality_of_school",
        "officialValueField": "PC_ALUNO_ALFABETIZADO",
        "minimumParticipation": MINIMUM_PARTICIPATION,
        "municipalityCount": EXPECTED_MUNICIPALITIES,
        "availableByYear": {
            str(year): EXPECTED_AVAILABLE[year] for year in YEARS
        },
        "stateValues": {
            str(year): EXPECTED_RS_VALUES[year] for year in YEARS
        },
        "sources": sources,
        "files": {
            "municipal_results.json": sha256_bytes(municipal_bytes),
            "state_results.json": sha256_bytes(state_bytes),
        },
    }
    return {
        "municipal_results.json": municipal_bytes,
        "state_results.json": state_bytes,
        "manifest.json": stable_json_bytes(manifest),
    }


def load_snapshot(
    snapshot_dir: Path = SNAPSHOT_DIR,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    root = snapshot_dir.resolve()
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("schemaVersion") != "pne-child-literacy-snapshot-v1":
        raise ValueError("Schema do snapshot Criança Alfabetizada inválido.")
    for filename, expected_hash in (manifest.get("files") or {}).items():
        if sha256_bytes((root / filename).read_bytes()) != expected_hash:
            raise ValueError(f"Hash divergente no snapshot: {filename}.")
    municipal = json.loads(
        (root / "municipal_results.json").read_text(encoding="utf-8")
    )
    state = json.loads((root / "state_results.json").read_text(encoding="utf-8"))
    if len(municipal) != EXPECTED_MUNICIPALITIES:
        raise ValueError("Cobertura municipal do snapshot inválida.")
    return municipal, state, manifest


def current_results(
    rows: Iterable[Mapping[str, Any]],
    *,
    year: int = 2025,
) -> dict[str, dict[str, Any]]:
    result = {}
    for row in rows:
        matches = [item for item in row["series"] if int(item["year"]) == year]
        if len(matches) != 1:
            raise ValueError(f"Série sem ano único {year}: {row['municipalityId']}.")
        result[str(row["municipalityId"])] = dict(matches[0])
    return result
