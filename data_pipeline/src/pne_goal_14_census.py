"""Relações municipais da Meta 14 a partir do Censo Demográfico 2022."""

from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any, Iterable, Mapping


YEAR = 2022
EXPECTED_MUNICIPALITIES = 497
STATE_ID = "43"
TERRITORIAL_LEVEL = "N6"
SEX_CLASSIFICATION = "2"
AGE_CLASSIFICATION = "58"
RACE_CLASSIFICATION = "86"
COURSE_CLASSIFICATION = "11798"
EDUCATION_CLASSIFICATION = "1568"
SEX_TOTAL = "6794"
RACE_TOTAL = "95251"
COURSE_GRADUATION = "95307"
EDUCATION_TOTAL = "120704"
EDUCATION_HIGHER_COMPLETE = "99713"
AGE_TOTAL = "95253"
AGE_18_24 = "100052"
AGE_25_29 = "1145"
AGE_30_34 = "1146"

TABLES = {
    "10058": {
        "variable": "13283",
        "classifications": {
            COURSE_CLASSIFICATION: (COURSE_GRADUATION,),
            AGE_CLASSIFICATION: (AGE_TOTAL,),
            SEX_CLASSIFICATION: (SEX_TOTAL,),
            RACE_CLASSIFICATION: (RACE_TOTAL,),
        },
    },
    "10059": {
        "variable": "13284",
        "classifications": {
            COURSE_CLASSIFICATION: (COURSE_GRADUATION,),
            AGE_CLASSIFICATION: (AGE_TOTAL, AGE_18_24),
            SEX_CLASSIFICATION: (SEX_TOTAL,),
            RACE_CLASSIFICATION: (RACE_TOTAL,),
        },
    },
    "10061": {
        "variable": "2667",
        "classifications": {
            EDUCATION_CLASSIFICATION: (
                EDUCATION_TOTAL,
                EDUCATION_HIGHER_COMPLETE,
            ),
            AGE_CLASSIFICATION: (AGE_18_24, AGE_25_29, AGE_30_34),
            SEX_CLASSIFICATION: (SEX_TOTAL,),
            RACE_CLASSIFICATION: (RACE_TOTAL,),
        },
    },
}

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
SNAPSHOT_DIR = DATA_DIR / "pne_goal_14_census_2022"


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


def metadata_url(table_id: str) -> str:
    return (
        "https://servicodados.ibge.gov.br/api/v3/agregados/"
        f"{table_id}/metadados"
    )


def data_url(table_id: str) -> str:
    table = TABLES[table_id]
    classifications = "|".join(
        f"{classification}[{','.join(categories)}]"
        for classification, categories in table["classifications"].items()
    )
    return (
        "https://servicodados.ibge.gov.br/api/v3/agregados/"
        f"{table_id}/periodos/{YEAR}/variaveis/{table['variable']}"
        f"?localidades={TERRITORIAL_LEVEL}[N3[{STATE_ID}]]"
        f"&classificacao={classifications}"
    )


def _normal(value: object) -> str:
    return " ".join(str(value or "").casefold().split())


def validate_metadata(table_id: str, metadata: Mapping[str, Any]) -> None:
    if str(metadata.get("id")) != table_id:
        raise ValueError(f"Metadados SIDRA divergentes para {table_id}.")
    table = TABLES[table_id]
    variables = {
        str(item.get("id")): item for item in metadata.get("variaveis", [])
    }
    variable = variables.get(table["variable"])
    if not variable or _normal(variable.get("unidade")) != "pessoas":
        raise ValueError(f"Variável em pessoas ausente na SIDRA {table_id}.")
    levels = (metadata.get("nivelTerritorial") or {}).get("Administrativo") or []
    if TERRITORIAL_LEVEL not in levels:
        raise ValueError(f"SIDRA {table_id} sem nível municipal.")
    classifications = {
        str(item.get("id")): {
            str(category.get("id")): str(category.get("nome") or "")
            for category in item.get("categorias", [])
        }
        for item in metadata.get("classificacoes", [])
    }
    for classification, categories in table["classifications"].items():
        observed = classifications.get(classification) or {}
        if not set(categories).issubset(observed):
            raise ValueError(
                f"Categorias requeridas ausentes em {table_id}/{classification}."
            )


def _category(result: Mapping[str, Any], classification: str) -> str:
    matches = [
        item
        for item in result.get("classificacoes", [])
        if str(item.get("id")) == classification
    ]
    if len(matches) != 1:
        raise ValueError(f"Classificação não única: {classification}.")
    categories = matches[0].get("categoria") or {}
    if len(categories) != 1:
        raise ValueError(f"Categoria não única: {classification}.")
    return str(next(iter(categories)))


def _count(value: object) -> dict[str, Any]:
    original = str(value or "").strip()
    if original in {"X"}:
        return {"status": "suppressed", "value": None, "original": original}
    if original in {"", "..."}:
        return {"status": "unavailable", "value": None, "original": original}
    if original in {".."}:
        return {"status": "not_applicable", "value": None, "original": original}
    if original == "-":
        original = "0"
    if not re.fullmatch(r"\d+", original):
        raise ValueError(f"Contagem SIDRA inesperada: {value!r}.")
    return {"status": "available", "value": int(original), "original": original}


def parse_response(
    table_id: str,
    payload: list[dict[str, Any]],
) -> dict[str, dict[tuple[str, str], dict[str, Any]]]:
    table = TABLES[table_id]
    if len(payload) != 1 or str(payload[0].get("id")) != table["variable"]:
        raise ValueError(f"Resposta da SIDRA {table_id} sem variável única.")
    level_classification = (
        EDUCATION_CLASSIFICATION
        if table_id == "10061"
        else COURSE_CLASSIFICATION
    )
    output: dict[str, dict[tuple[str, str], dict[str, Any]]] = {}
    seen: set[tuple[str, str, str]] = set()
    for result in payload[0].get("resultados", []):
        if _category(result, SEX_CLASSIFICATION) != SEX_TOTAL:
            raise ValueError("Resposta SIDRA fora do total de sexo.")
        if _category(result, RACE_CLASSIFICATION) != RACE_TOTAL:
            raise ValueError("Resposta SIDRA fora do total de cor ou raça.")
        age = _category(result, AGE_CLASSIFICATION)
        level = _category(result, level_classification)
        expected = table["classifications"]
        if age not in expected[AGE_CLASSIFICATION]:
            raise ValueError(f"Idade não solicitada na SIDRA {table_id}.")
        if level not in expected[level_classification]:
            raise ValueError(f"Nível não solicitado na SIDRA {table_id}.")
        for series in result.get("series", []):
            locality = series.get("localidade") or {}
            municipality_id = str(locality.get("id") or "")
            if not municipality_id.startswith("43"):
                raise ValueError(f"Município fora do RS: {municipality_id}.")
            if str((locality.get("nivel") or {}).get("id")) != TERRITORIAL_LEVEL:
                raise ValueError("Resposta SIDRA fora do nível municipal.")
            key = (municipality_id, age, level)
            if key in seen:
                raise ValueError(f"Chave SIDRA duplicada: {key}.")
            seen.add(key)
            output.setdefault(municipality_id, {})[(age, level)] = _count(
                (series.get("serie") or {}).get(str(YEAR))
            )
    expected_per_municipality = (
        len(table["classifications"][AGE_CLASSIFICATION])
        * len(table["classifications"][level_classification])
    )
    if len(output) != EXPECTED_MUNICIPALITIES:
        raise ValueError(f"SIDRA {table_id} não cobre os 497 municípios.")
    if len(seen) != EXPECTED_MUNICIPALITIES * expected_per_municipality:
        raise ValueError(f"SIDRA {table_id} tem cobertura categorial incompleta.")
    return output


def _sum(parts: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    values = list(parts)
    for status in ("suppressed", "unavailable", "not_applicable"):
        if any(item["status"] == status for item in values):
            return {"status": status, "value": None}
    return {
        "status": "available",
        "value": sum(int(item["value"]) for item in values),
    }


def ratio_result(
    numerator: Mapping[str, Any],
    denominator: Mapping[str, Any],
    *,
    allow_above_100: bool,
) -> dict[str, Any]:
    for status in ("suppressed", "unavailable", "not_applicable"):
        if numerator["status"] == status or denominator["status"] == status:
            return {
                "dataStatus": status,
                "reasonCode": f"source_{status}",
                "value": None,
                "numerator": numerator.get("value"),
                "denominator": denominator.get("value"),
            }
    denominator_value = int(denominator["value"])
    numerator_value = int(numerator["value"])
    if denominator_value == 0:
        return {
            "dataStatus": "not_applicable",
            "reasonCode": "denominator_zero",
            "value": None,
            "numerator": numerator_value,
            "denominator": 0,
        }
    value = 100.0 * numerator_value / denominator_value
    if not math.isfinite(value) or value < 0:
        raise ValueError("Razão da Meta 14 inválida.")
    if not allow_above_100 and value > 100:
        raise ValueError("Razão limitada da Meta 14 acima de 100%.")
    return {
        "dataStatus": "available",
        "value": value,
        "numerator": numerator_value,
        "denominator": denominator_value,
    }


def build_results(
    parsed: Mapping[str, Mapping[str, Mapping[tuple[str, str], Mapping[str, Any]]]],
    *,
    municipality_names: Mapping[str, str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if set(parsed) != set(TABLES):
        raise ValueError("Conjunto de tabelas da Meta 14 incompleto.")
    codes = set(parsed["10058"])
    if any(set(table) != codes for table in parsed.values()):
        raise ValueError("Coberturas municipais divergentes entre tabelas.")
    if set(municipality_names) != codes:
        raise ValueError("Cadastro municipal diverge das tabelas da Meta 14.")

    municipal = []
    state_accumulator = {
        "14.a": [0, 0],
        "14.b": [0, 0],
        "14.d": [0, 0],
    }
    for municipality_id in sorted(codes):
        table_58 = parsed["10058"][municipality_id]
        table_59 = parsed["10059"][municipality_id]
        table_61 = parsed["10061"][municipality_id]
        ingredients = {
            "14.a": (
                table_59[(AGE_18_24, COURSE_GRADUATION)],
                table_61[(AGE_18_24, EDUCATION_TOTAL)],
                False,
            ),
            "14.b": (
                _sum(
                    (
                        table_61[(AGE_25_29, EDUCATION_HIGHER_COMPLETE)],
                        table_61[(AGE_30_34, EDUCATION_HIGHER_COMPLETE)],
                    )
                ),
                _sum(
                    (
                        table_61[(AGE_25_29, EDUCATION_TOTAL)],
                        table_61[(AGE_30_34, EDUCATION_TOTAL)],
                    )
                ),
                False,
            ),
            "14.d": (
                _sum(
                    (
                        table_58[(AGE_TOTAL, COURSE_GRADUATION)],
                        table_59[(AGE_TOTAL, COURSE_GRADUATION)],
                    )
                ),
                table_61[(AGE_18_24, EDUCATION_TOTAL)],
                True,
            ),
        }
        indicators = {}
        for relation_id, (numerator, denominator, allow_above) in ingredients.items():
            result = ratio_result(
                numerator,
                denominator,
                allow_above_100=allow_above,
            )
            indicators[relation_id] = result
            if result["dataStatus"] == "available":
                state_accumulator[relation_id][0] += int(result["numerator"])
                state_accumulator[relation_id][1] += int(result["denominator"])
        municipal.append(
            {
                "municipalityId": municipality_id,
                "municipalityName": municipality_names[municipality_id],
                "year": YEAR,
                "indicators": indicators,
            }
        )

    state = []
    for relation_id, (numerator, denominator) in state_accumulator.items():
        if denominator == 0:
            raise ValueError(f"Denominador estadual nulo em {relation_id}.")
        state.append(
            {
                "relationId": relation_id,
                "territoryId": STATE_ID,
                "territoryName": "Rio Grande do Sul",
                "year": YEAR,
                "dataStatus": "available",
                "value": 100.0 * numerator / denominator,
                "numerator": numerator,
                "denominator": denominator,
            }
        )
    return municipal, state


def build_snapshot(
    *,
    metadata_payloads: Mapping[str, Mapping[str, Any]],
    data_payloads: Mapping[str, list[dict[str, Any]]],
    source_hashes: Mapping[str, Mapping[str, str]],
    municipality_names: Mapping[str, str],
    reference_date: str,
) -> dict[str, bytes]:
    parsed = {}
    for table_id in TABLES:
        validate_metadata(table_id, metadata_payloads[table_id])
        parsed[table_id] = parse_response(table_id, data_payloads[table_id])
    municipal, state = build_results(parsed, municipality_names=municipality_names)
    municipal_bytes = stable_json_bytes(municipal)
    state_bytes = stable_json_bytes(state)
    manifest = {
        "schemaVersion": "pne-goal-14-census-snapshot-v1",
        "sourceReferenceDate": reference_date,
        "year": YEAR,
        "municipalityCount": EXPECTED_MUNICIPALITIES,
        "tables": {
            table_id: {
                "metadataUrl": metadata_url(table_id),
                "dataUrl": data_url(table_id),
                "variable": TABLES[table_id]["variable"],
                "classifications": TABLES[table_id]["classifications"],
                **source_hashes[table_id],
            }
            for table_id in TABLES
        },
        "territorialBasis": "municipality_of_residence",
        "allAgesGraduationScope": (
            "Pessoas de 6 a 17 anos e pessoas de 18 anos ou mais; "
            "graduação não é categoria aplicável a pessoas de até 5 anos."
        ),
        "statePolicy": "ratio_of_municipal_sums",
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
    if manifest.get("schemaVersion") != "pne-goal-14-census-snapshot-v1":
        raise ValueError("Schema do snapshot da Meta 14 inválido.")
    for filename, expected in (manifest.get("files") or {}).items():
        if sha256_bytes((root / filename).read_bytes()) != expected:
            raise ValueError(f"Hash divergente no snapshot Meta 14: {filename}.")
    municipal = json.loads(
        (root / "municipal_results.json").read_text(encoding="utf-8")
    )
    state = json.loads((root / "state_results.json").read_text(encoding="utf-8"))
    if len(municipal) != EXPECTED_MUNICIPALITIES:
        raise ValueError("Cobertura municipal da Meta 14 inválida.")
    return municipal, state, manifest
