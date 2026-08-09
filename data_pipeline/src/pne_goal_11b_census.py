"""Componentes censitários reproduzíveis da Meta 11.b do PNE 2026–2036."""

from __future__ import annotations

import hashlib
import json
import math
import re
import unicodedata
from pathlib import Path
from typing import Any, Iterable, Mapping

from .pne_state_context import (
    load_pne_state_context,
    resolve_state_snapshot_dir,
)


AGGREGATE_ID = "10061"
CENSUS_YEAR = 2022
VARIABLE_ID = "2667"
TERRITORIAL_LEVEL = "N6"
RS_STATE_ID = "43"
EXPECTED_MUNICIPALITIES = 497

SEX_CLASSIFICATION_ID = "2"
AGE_CLASSIFICATION_ID = "58"
RACE_CLASSIFICATION_ID = "86"
EDUCATION_CLASSIFICATION_ID = "1568"
SEX_TOTAL_ID = "6794"
RACE_TOTAL_ID = "95251"

AGE_IDS = {
    "18_plus": "95253",
    "18_24": "100052",
    "25_29": "1145",
}
EDUCATION_IDS = {
    "total": "120704",
    "below_fundamental": "9493",
    "fundamental_complete": "9494",
    "secondary_complete": "9495",
    "higher_complete": "99713",
}
COMPLETED_EDUCATION_KEYS = (
    "fundamental_complete",
    "secondary_complete",
    "higher_complete",
)

SNAPSHOT_DIR = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "pne_goal_11b_census_2022"
)
METADATA_URL = (
    f"https://servicodados.ibge.gov.br/api/v3/agregados/{AGGREGATE_ID}/metadados"
)


def data_url(state_code: str = "RS") -> str:
    state = load_pne_state_context(state_code)
    ages = ",".join(AGE_IDS.values())
    education = ",".join(EDUCATION_IDS.values())
    return (
        "https://servicodados.ibge.gov.br/api/v3/agregados/"
        f"{AGGREGATE_ID}/periodos/{CENSUS_YEAR}/variaveis/{VARIABLE_ID}"
        f"?localidades={TERRITORIAL_LEVEL}[N3[{state.state_id}]]"
        f"&classificacao={SEX_CLASSIFICATION_ID}[{SEX_TOTAL_ID}]"
        f"|{AGE_CLASSIFICATION_ID}[{ages}]"
        f"|{RACE_CLASSIFICATION_ID}[{RACE_TOTAL_ID}]"
        f"|{EDUCATION_CLASSIFICATION_ID}[{education}]"
    )


def _normalise_text(value: object) -> str:
    decomposed = unicodedata.normalize("NFKD", str(value or ""))
    without_marks = "".join(
        character
        for character in decomposed
        if not unicodedata.combining(character)
    )
    return " ".join(without_marks.casefold().split())


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


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


def age_in_scope(age: int, scope: str) -> bool:
    if scope == "15_29":
        return 15 <= int(age) <= 29
    if scope == "15_plus":
        return int(age) >= 15
    raise ValueError(f"Recorte etário desconhecido: {scope}.")


def education_level_counts_as_complete(level: str) -> bool:
    return str(level) in COMPLETED_EDUCATION_KEYS


def _classification(
    metadata: Mapping[str, Any],
    classification_id: str,
) -> Mapping[str, Any]:
    matches = [
        item
        for item in metadata.get("classificacoes", [])
        if str(item.get("id")) == classification_id
    ]
    if len(matches) != 1:
        raise ValueError(
            f"Classificação {classification_id} ausente ou duplicada."
        )
    return matches[0]


def _categories(classification: Mapping[str, Any]) -> dict[str, str]:
    return {
        str(item.get("id")): str(item.get("nome") or "")
        for item in classification.get("categorias", [])
    }


def validate_metadata(metadata: Mapping[str, Any]) -> dict[str, Any]:
    if str(metadata.get("id")) != AGGREGATE_ID:
        raise ValueError("Metadados não correspondem à tabela SIDRA 10061.")
    expected_name = (
        "Pessoas de 18 anos ou mais de idade, por nível de instrução, "
        "segundo os grupos de idade, o sexo e a cor ou raça"
    )
    if _normalise_text(metadata.get("nome")) != _normalise_text(expected_name):
        raise ValueError("Nome semântico inesperado para a SIDRA 10061.")
    periodicity = metadata.get("periodicidade") or {}
    if int(periodicity.get("inicio") or 0) > CENSUS_YEAR or int(
        periodicity.get("fim") or 0
    ) < CENSUS_YEAR:
        raise ValueError("O período 2022 não está disponível na SIDRA 10061.")
    levels = (metadata.get("nivelTerritorial") or {}).get("Administrativo") or []
    if TERRITORIAL_LEVEL not in levels:
        raise ValueError("A SIDRA 10061 não oferece o nível municipal.")

    variables = {
        str(item.get("id")): item for item in metadata.get("variaveis", [])
    }
    variable = variables.get(VARIABLE_ID)
    if not variable:
        raise ValueError("Variável 2667 ausente da SIDRA 10061.")
    if _normalise_text(variable.get("unidade")) != "pessoas":
        raise ValueError("A variável 2667 não está expressa em pessoas.")

    expected = {
        SEX_CLASSIFICATION_ID: {
            SEX_TOTAL_ID: "Total",
        },
        AGE_CLASSIFICATION_ID: {
            AGE_IDS["18_plus"]: "Total",
            AGE_IDS["18_24"]: "18 a 24 anos",
            AGE_IDS["25_29"]: "25 a 29 anos",
        },
        RACE_CLASSIFICATION_ID: {
            RACE_TOTAL_ID: "Total",
        },
        EDUCATION_CLASSIFICATION_ID: {
            EDUCATION_IDS["total"]: "Total",
            EDUCATION_IDS["below_fundamental"]: (
                "Sem instrução e fundamental incompleto"
            ),
            EDUCATION_IDS["fundamental_complete"]: (
                "Fundamental completo e médio incompleto"
            ),
            EDUCATION_IDS["secondary_complete"]: (
                "Médio completo e superior incompleto"
            ),
            EDUCATION_IDS["higher_complete"]: "Superior completo",
        },
    }
    for classification_id, categories in expected.items():
        observed = _categories(_classification(metadata, classification_id))
        for category_id, label in categories.items():
            if _normalise_text(observed.get(category_id)) != _normalise_text(
                label
            ):
                raise ValueError(
                    f"Categoria {classification_id}:{category_id} divergente."
                )
    return {
        "aggregateId": AGGREGATE_ID,
        "year": CENSUS_YEAR,
        "variableId": VARIABLE_ID,
        "territorialLevel": TERRITORIAL_LEVEL,
        "ages": dict(AGE_IDS),
        "educationLevels": dict(EDUCATION_IDS),
    }


def parse_sidra_value(value: object) -> tuple[int | None, str]:
    original = "" if value is None else str(value).strip()
    special = {
        "X": "suppressed",
        "..": "not_applicable",
        "...": "unavailable",
        "": "unavailable",
    }
    if original in special:
        return None, special[original]
    if original in {"-", "0"}:
        return 0, "available"
    if not re.fullmatch(r"\d+", original):
        raise ValueError(f"Valor SIDRA inesperado: {value!r}.")
    return int(original), "available"


def _result_category(
    result: Mapping[str, Any],
    classification_id: str,
) -> tuple[str, str]:
    matches = [
        item
        for item in result.get("classificacoes", [])
        if str(item.get("id")) == classification_id
    ]
    if len(matches) != 1:
        raise ValueError(
            f"Resultado sem classificação única {classification_id}."
        )
    categories = matches[0].get("categoria") or {}
    if len(categories) != 1:
        raise ValueError(
            f"Resultado sem categoria única em {classification_id}."
        )
    key, label = next(iter(categories.items()))
    return str(key), str(label)


def parse_response(
    payload: list[dict[str, Any]],
    *,
    municipality_codes: set[str],
) -> dict[str, dict[str, dict[str, Any]]]:
    if len(payload) != 1:
        raise ValueError("A resposta SIDRA deve conter exatamente uma variável.")
    variable = payload[0]
    if str(variable.get("id")) != VARIABLE_ID:
        raise ValueError("A resposta SIDRA não contém a variável 2667.")
    if _normalise_text(variable.get("unidade")) != "pessoas":
        raise ValueError("A resposta SIDRA não está expressa em pessoas.")

    age_keys = {value: key for key, value in AGE_IDS.items()}
    education_keys = {value: key for key, value in EDUCATION_IDS.items()}
    by_municipality: dict[str, dict[str, dict[str, Any]]] = {
        code: {} for code in sorted(municipality_codes)
    }
    seen: set[tuple[str, str, str]] = set()
    for result in variable.get("resultados", []):
        sex_id, _ = _result_category(result, SEX_CLASSIFICATION_ID)
        age_id, _ = _result_category(result, AGE_CLASSIFICATION_ID)
        race_id, _ = _result_category(result, RACE_CLASSIFICATION_ID)
        education_id, _ = _result_category(
            result, EDUCATION_CLASSIFICATION_ID
        )
        if sex_id != SEX_TOTAL_ID or race_id != RACE_TOTAL_ID:
            raise ValueError("A resposta não está restrita aos totais de sexo/cor.")
        if age_id not in age_keys or education_id not in education_keys:
            raise ValueError("A resposta contém categoria não solicitada.")
        age_key = age_keys[age_id]
        education_key = education_keys[education_id]
        for series in result.get("series", []):
            locality = series.get("localidade") or {}
            municipality_id = str(locality.get("id") or "")
            if municipality_id not in municipality_codes:
                raise ValueError(
                    f"Município inesperado na SIDRA: {municipality_id!r}."
                )
            level = locality.get("nivel") or {}
            if str(level.get("id")) != TERRITORIAL_LEVEL:
                raise ValueError("A resposta contém nível não municipal.")
            key = (municipality_id, age_key, education_key)
            if key in seen:
                raise ValueError(f"Chave SIDRA duplicada: {key!r}.")
            seen.add(key)
            original = (series.get("serie") or {}).get(str(CENSUS_YEAR))
            numeric, status = parse_sidra_value(original)
            by_municipality[municipality_id].setdefault(age_key, {})[
                education_key
            ] = {
                "value": numeric,
                "status": status,
                "original": "" if original is None else str(original),
            }

    expected_per_municipality = len(AGE_IDS) * len(EDUCATION_IDS)
    if len(seen) != len(municipality_codes) * expected_per_municipality:
        raise ValueError("Cobertura categorial incompleta na SIDRA 10061.")
    return by_municipality


def _status_precedence(statuses: Iterable[str]) -> str:
    observed = set(statuses)
    for status in ("suppressed", "unavailable", "not_applicable"):
        if status in observed:
            return status
    return "available"


def _sum_components(components: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    parts = list(components)
    status = _status_precedence(str(part["status"]) for part in parts)
    if status != "available":
        return {"value": None, "status": status}
    return {
        "value": sum(int(part["value"]) for part in parts),
        "status": "available",
    }


def _age_component(age: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    denominator = age["total"]
    numerator = _sum_components(age[key] for key in COMPLETED_EDUCATION_KEYS)
    return {
        "numerator": numerator["value"],
        "denominator": denominator["value"],
        "status": _status_precedence(
            (str(numerator["status"]), str(denominator["status"]))
        ),
        "sourceValues": {
            key: {
                "value": age[key]["value"],
                "status": age[key]["status"],
                "original": age[key]["original"],
            }
            for key in EDUCATION_IDS
        },
    }


def _combine_ranges(*ranges: Mapping[str, Any]) -> dict[str, Any]:
    status = _status_precedence(str(item["status"]) for item in ranges)
    if status != "available":
        return {"numerator": None, "denominator": None, "status": status}
    return {
        "numerator": sum(int(item["numerator"]) for item in ranges),
        "denominator": sum(int(item["denominator"]) for item in ranges),
        "status": "available",
    }


def build_municipal_components(
    sidra: Mapping[str, Mapping[str, Mapping[str, Any]]],
    fifteen_to_seventeen: Iterable[Mapping[str, Any]],
    *,
    expected_municipalities: int = EXPECTED_MUNICIPALITIES,
) -> list[dict[str, Any]]:
    local_by_code: dict[str, Mapping[str, Any]] = {}
    for row in fifteen_to_seventeen:
        municipality_id = str(row["municipalityId"])
        if municipality_id in local_by_code:
            raise ValueError(f"Componente 15–17 duplicado: {municipality_id}.")
        local_by_code[municipality_id] = row
    if set(local_by_code) != set(sidra):
        raise ValueError("Cobertura municipal 15–17 diverge da SIDRA 10061.")

    rows: list[dict[str, Any]] = []
    for municipality_id in sorted(sidra):
        local = local_by_code[municipality_id]
        fifteen = {
            "numerator": local.get("numerator"),
            "denominator": local.get("denominator"),
            "status": str(local.get("status") or "unavailable"),
        }
        eighteen_plus = _age_component(sidra[municipality_id]["18_plus"])
        eighteen_to_twenty_four = _age_component(
            sidra[municipality_id]["18_24"]
        )
        twenty_five_to_twenty_nine = _age_component(
            sidra[municipality_id]["25_29"]
        )
        rows.append(
            {
                "municipalityId": municipality_id,
                "municipalityName": str(local["municipalityName"]),
                "year": CENSUS_YEAR,
                "fifteenToSeventeen": fifteen,
                "eighteenPlus": eighteen_plus,
                "eighteenToTwentyFour": eighteen_to_twenty_four,
                "twentyFiveToTwentyNine": twenty_five_to_twenty_nine,
                "fifteenToTwentyNine": _combine_ranges(
                    fifteen,
                    eighteen_to_twenty_four,
                    twenty_five_to_twenty_nine,
                ),
                "fifteenPlus": _combine_ranges(fifteen, eighteen_plus),
            }
        )
    if len(rows) != expected_municipalities:
        raise ValueError(
            f"Cobertura municipal inválida: {len(rows)} municípios."
        )
    return rows


def ratio_result(component: Mapping[str, Any]) -> dict[str, Any]:
    status = str(component.get("status") or "unavailable")
    numerator = component.get("numerator")
    denominator = component.get("denominator")
    if status != "available":
        return {
            "dataStatus": status,
            "reasonCode": f"source_{status}",
            "value": None,
            "numerator": numerator,
            "denominator": denominator,
        }
    if denominator is None:
        return {
            "dataStatus": "unavailable",
            "reasonCode": "denominator_unavailable",
            "value": None,
            "numerator": numerator,
            "denominator": None,
        }
    if int(denominator) == 0:
        return {
            "dataStatus": "not_applicable",
            "reasonCode": "denominator_zero",
            "value": None,
            "numerator": numerator,
            "denominator": denominator,
        }
    if numerator is None:
        return {
            "dataStatus": "unavailable",
            "reasonCode": "numerator_unavailable",
            "value": None,
            "numerator": None,
            "denominator": denominator,
        }
    value = 100.0 * int(numerator) / int(denominator)
    if not math.isfinite(value):
        raise ValueError("Razão censitária não finita.")
    return {
        "dataStatus": "available",
        "value": value,
        "numerator": int(numerator),
        "denominator": int(denominator),
    }


def state_ratio(
    rows: Iterable[Mapping[str, Any]],
    component_key: str,
    *,
    expected_municipalities: int = EXPECTED_MUNICIPALITIES,
) -> dict[str, Any]:
    results = [ratio_result(row[component_key]) for row in rows]
    available = [
        result for result in results if result["dataStatus"] == "available"
    ]
    if len(available) != expected_municipalities:
        return {
            "dataStatus": "unavailable",
            "value": None,
            "numerator": None,
            "denominator": None,
        }
    numerator = sum(int(result["numerator"]) for result in available)
    denominator = sum(int(result["denominator"]) for result in available)
    return {
        "dataStatus": "available",
        "value": 100.0 * numerator / denominator,
        "numerator": numerator,
        "denominator": denominator,
    }


def load_snapshot(
    snapshot_dir: Path | None = None,
    *,
    state_code: str = "RS",
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    state = load_pne_state_context(state_code)
    root = (
        Path(snapshot_dir)
        if snapshot_dir is not None
        else resolve_state_snapshot_dir(SNAPSHOT_DIR, state.state_code)
    ).resolve()
    manifest_path = root / "manifest.json"
    components_path = root / "municipal_components.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schemaVersion") != "pne-goal-11b-census-snapshot-v1":
        raise ValueError("Schema do snapshot censitário 11.b inválido.")
    if manifest.get("stateCode", "RS") != state.state_code:
        raise ValueError("UF do snapshot censitário 11.b divergente.")
    files = manifest.get("files") or {}
    for filename, expected_hash in files.items():
        path = root / filename
        if sha256_bytes(path.read_bytes()) != expected_hash:
            raise ValueError(f"Hash divergente no snapshot 11.b: {filename}.")
    rows = json.loads(components_path.read_text(encoding="utf-8"))
    if (
        not isinstance(rows, list)
        or len(rows) != state.expected_municipality_count
        or len({str(row.get("municipalityId")) for row in rows})
        != state.expected_municipality_count
    ):
        raise ValueError("Cobertura municipal do snapshot 11.b inválida.")
    if {str(row.get("municipalityId")) for row in rows} != state.municipality_ids:
        raise ValueError("Universo municipal do snapshot 11.b divergente.")
    return rows, manifest
