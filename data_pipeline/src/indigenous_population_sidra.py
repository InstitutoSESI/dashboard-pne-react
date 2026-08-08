"""Extração e normalização da população indígena municipal no SIDRA.

O módulo mantém a consulta reproduzível, valida os metadados por identificador e
por rótulo semântico e preserva os símbolos especiais publicados pelo SIDRA.
"""

from __future__ import annotations

import hashlib
import gzip
import json
import re
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


AGGREGATE_ID = "9970"
CENSUS_YEAR = 2022
VARIABLE_ID = "350"
TERRITORIAL_LEVEL = "N6"
RS_STATE_ID = "43"
AGE_CLASSIFICATION_ID = "287"
LOCATION_CLASSIFICATION_ID = "2661"
HOUSEHOLD_SITUATION_CLASSIFICATION_ID = "1"
LOCATION_TOTAL_ID = "32776"
HOUSEHOLD_SITUATION_TOTAL_ID = "6795"
IMPORTER_SCHEMA_VERSION = 1
EXPECTED_MUNICIPALITIES = 497

AGE_IDS = {
    0: "6557",
    1: "6558",
    2: "6559",
    3: "6560",
    4: "6561",
    5: "6562",
    6: "6563",
    7: "6564",
    8: "6565",
    9: "6566",
    10: "6567",
    11: "6568",
    12: "6569",
    13: "6570",
    14: "6571",
    15: "6572",
    16: "6573",
    17: "6574",
}

AGE_GROUPS = {
    "0_3": (0, 3, "0 a 3 anos"),
    "4_5": (4, 5, "4 a 5 anos"),
    "6_14": (6, 14, "6 a 14 anos"),
    "15_17": (15, 17, "15 a 17 anos"),
    "4_17": (4, 17, "4 a 17 anos"),
    "0_17": (0, 17, "0 a 17 anos"),
}

METADATA_URL = (
    f"https://servicodados.ibge.gov.br/api/v3/agregados/{AGGREGATE_ID}/metadados"
)


def data_url(state_id: str = RS_STATE_ID) -> str:
    ages = ",".join(AGE_IDS.values())
    return (
        "https://servicodados.ibge.gov.br/api/v3/agregados/"
        f"{AGGREGATE_ID}/periodos/{CENSUS_YEAR}/variaveis/{VARIABLE_ID}"
        f"?localidades={TERRITORIAL_LEVEL}[N3[{state_id}]]"
        f"&classificacao={AGE_CLASSIFICATION_ID}[{ages}]"
        f"|{LOCATION_CLASSIFICATION_ID}[{LOCATION_TOTAL_ID}]"
        f"|{HOUSEHOLD_SITUATION_CLASSIFICATION_ID}"
        f"[{HOUSEHOLD_SITUATION_TOTAL_ID}]"
    )


def _normalise_text(value: object) -> str:
    decomposed = unicodedata.normalize("NFKD", str(value or ""))
    without_marks = "".join(
        character for character in decomposed if not unicodedata.combining(character)
    )
    return " ".join(without_marks.casefold().split())


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def download_bytes(
    url: str,
    *,
    attempts: int = 4,
    timeout: int = 120,
) -> bytes:
    """Baixa uma resposta oficial com timeout e retries limitados."""

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
                if content.startswith(b"\x1f\x8b"):
                    return gzip.decompress(content)
                return content
        except (HTTPError, URLError, TimeoutError) as error:
            last_error = error
            if attempt == attempts:
                break
            time.sleep(min(2 ** (attempt - 1), 8))
    raise RuntimeError(f"Falha ao baixar {url!r} após {attempts} tentativas") from last_error


def _classification(metadata: dict[str, Any], classification_id: str) -> dict[str, Any]:
    matches = [
        item
        for item in metadata.get("classificacoes", [])
        if str(item.get("id")) == classification_id
    ]
    if len(matches) != 1:
        raise ValueError(
            f"Classificação {classification_id} ausente ou duplicada nos metadados."
        )
    return matches[0]


def _category_map(classification: dict[str, Any]) -> dict[str, str]:
    return {
        str(category.get("id")): str(category.get("nome") or "")
        for category in classification.get("categorias", [])
    }


def validate_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """Valida IDs e significados necessários antes de construir a consulta."""

    if str(metadata.get("id")) != AGGREGATE_ID:
        raise ValueError("Os metadados não correspondem ao agregado SIDRA 9970.")
    if _normalise_text(metadata.get("nome")) != _normalise_text(
        "Pessoas indígenas, por idade, localização e situação do domicílio"
    ):
        raise ValueError("Nome semântico inesperado para o agregado SIDRA 9970.")

    periodicity = metadata.get("periodicidade") or {}
    if int(periodicity.get("inicio") or 0) > CENSUS_YEAR or int(
        periodicity.get("fim") or 0
    ) < CENSUS_YEAR:
        raise ValueError("O período 2022 não está disponível no agregado SIDRA 9970.")

    administrative_levels = (
        (metadata.get("nivelTerritorial") or {}).get("Administrativo") or []
    )
    if TERRITORIAL_LEVEL not in administrative_levels:
        raise ValueError("O nível municipal N6 não está disponível no agregado 9970.")

    variables = {
        str(variable.get("id")): variable for variable in metadata.get("variaveis", [])
    }
    variable = variables.get(VARIABLE_ID)
    if not variable:
        raise ValueError("A variável 350 não está disponível no agregado 9970.")
    if _normalise_text(variable.get("nome")) != _normalise_text("Pessoas indígenas"):
        raise ValueError("A variável 350 não representa Pessoas indígenas.")
    if _normalise_text(variable.get("unidade")) != "pessoas":
        raise ValueError("A variável 350 não está expressa em pessoas.")

    age_classification = _classification(metadata, AGE_CLASSIFICATION_ID)
    if _normalise_text(age_classification.get("nome")) != "idade":
        raise ValueError("A classificação 287 não representa idade.")
    age_categories = _category_map(age_classification)
    for age, category_id in AGE_IDS.items():
        expected_label = "Menos de 1 ano" if age == 0 else f"{age} anos"
        if age == 1:
            expected_label = "1 ano"
        if _normalise_text(age_categories.get(category_id)) != _normalise_text(
            expected_label
        ):
            raise ValueError(
                f"Categoria {category_id} não representa a idade simples {age}."
            )

    location_classification = _classification(
        metadata, LOCATION_CLASSIFICATION_ID
    )
    if _normalise_text(location_classification.get("nome")) != _normalise_text(
        "Localização do domicílio"
    ):
        raise ValueError("A classificação 2661 não representa localização do domicílio.")
    if _normalise_text(
        _category_map(location_classification).get(LOCATION_TOTAL_ID)
    ) != "total":
        raise ValueError("A categoria de localização selecionada não representa Total.")

    situation_classification = _classification(
        metadata, HOUSEHOLD_SITUATION_CLASSIFICATION_ID
    )
    if _normalise_text(situation_classification.get("nome")) != _normalise_text(
        "Situação do domicílio"
    ):
        raise ValueError("A classificação 1 não representa situação do domicílio.")
    if _normalise_text(
        _category_map(situation_classification).get(
            HOUSEHOLD_SITUATION_TOTAL_ID
        )
    ) != "total":
        raise ValueError("A categoria de situação selecionada não representa Total.")

    return {
        "aggregate": AGGREGATE_ID,
        "period": CENSUS_YEAR,
        "variable": {
            "id": VARIABLE_ID,
            "label": str(variable["nome"]),
            "unit": str(variable["unidade"]),
        },
        "territorialLevel": {
            "id": TERRITORIAL_LEVEL,
            "label": "Município",
            "municipalCodeDigits": 7,
        },
        "classifications": {
            "age": {
                "id": AGE_CLASSIFICATION_ID,
                "categories": {
                    str(age): {"id": category_id, "label": age_categories[category_id]}
                    for age, category_id in AGE_IDS.items()
                },
            },
            "householdLocation": {
                "id": LOCATION_CLASSIFICATION_ID,
                "category": {
                    "id": LOCATION_TOTAL_ID,
                    "label": _category_map(location_classification)[LOCATION_TOTAL_ID],
                },
            },
            "householdSituation": {
                "id": HOUSEHOLD_SITUATION_CLASSIFICATION_ID,
                "category": {
                    "id": HOUSEHOLD_SITUATION_TOTAL_ID,
                    "label": _category_map(situation_classification)[
                        HOUSEHOLD_SITUATION_TOTAL_ID
                    ],
                },
            },
        },
    }


def parse_sidra_value(original: object) -> tuple[int | None, str]:
    """Converte somente zeros e inteiros publicados; preserva demais estados."""

    value = "" if original is None else str(original).strip()
    statuses = {
        "X": "suppressed",
        "..": "not_applicable",
        "...": "unavailable",
        "": "missing",
    }
    if value in statuses:
        return None, statuses[value]
    if value in {"-", "0"}:
        return 0, "available"
    if not re.fullmatch(r"\d+", value):
        raise ValueError(f"Valor SIDRA inesperado: {original!r}.")
    return int(value), "available"


def _result_category(result: dict[str, Any], classification_id: str) -> tuple[str, str]:
    matches = [
        item
        for item in result.get("classificacoes", [])
        if str(item.get("id")) == classification_id
    ]
    if len(matches) != 1:
        raise ValueError(
            f"Resultado sem classificação única {classification_id}: {matches!r}."
        )
    categories = matches[0].get("categoria") or {}
    if len(categories) != 1:
        raise ValueError(
            f"Resultado sem categoria única em {classification_id}: {categories!r}."
        )
    return next(iter((str(key), str(value)) for key, value in categories.items()))


def parse_response(
    payload: list[dict[str, Any]],
    *,
    municipality_codes: set[str] | None,
    source_metadata: dict[str, Any],
) -> list[dict[str, Any]]:
    """Normaliza a resposta para uma linha por município e idade de 0 a 17."""

    if len(payload) != 1:
        raise ValueError("A resposta SIDRA deve conter exatamente uma variável.")
    variable = payload[0]
    if str(variable.get("id")) != VARIABLE_ID:
        raise ValueError("A resposta SIDRA não contém a variável 350.")
    if _normalise_text(variable.get("variavel")) != _normalise_text(
        "Pessoas indígenas"
    ):
        raise ValueError("O rótulo da variável SIDRA é incompatível.")
    if _normalise_text(variable.get("unidade")) != "pessoas":
        raise ValueError("A resposta SIDRA não está expressa em pessoas.")

    by_key: dict[tuple[str, int], dict[str, Any]] = {}
    discovered_codes: set[str] = set()
    age_by_category_id = {category_id: age for age, category_id in AGE_IDS.items()}
    for result in variable.get("resultados", []):
        age_id, age_label = _result_category(result, AGE_CLASSIFICATION_ID)
        location_id, location_label = _result_category(
            result, LOCATION_CLASSIFICATION_ID
        )
        situation_id, situation_label = _result_category(
            result, HOUSEHOLD_SITUATION_CLASSIFICATION_ID
        )
        if age_id not in age_by_category_id:
            raise ValueError(f"Categoria de idade inesperada na resposta: {age_id}.")
        age = age_by_category_id[age_id]
        expected_age_label = source_metadata["classifications"]["age"]["categories"][
            str(age)
        ]["label"]
        if _normalise_text(age_label) != _normalise_text(expected_age_label):
            raise ValueError(f"Rótulo divergente para a idade {age}: {age_label!r}.")
        if (
            location_id != LOCATION_TOTAL_ID
            or _normalise_text(location_label) != "total"
        ):
            raise ValueError("A resposta não usa o total de localização do domicílio.")
        if (
            situation_id != HOUSEHOLD_SITUATION_TOTAL_ID
            or _normalise_text(situation_label) != "total"
        ):
            raise ValueError("A resposta não usa o total de situação do domicílio.")

        for series in result.get("series", []):
            locality = series.get("localidade") or {}
            municipality_id = str(locality.get("id") or "")
            if not re.fullmatch(r"\d{7}", municipality_id):
                raise ValueError(
                    f"Código municipal inválido na resposta: {municipality_id!r}."
                )
            level = locality.get("nivel") or {}
            if str(level.get("id")) != TERRITORIAL_LEVEL or _normalise_text(
                level.get("nome")
            ) != _normalise_text("Município"):
                raise ValueError("A resposta contém nível territorial não municipal.")
            original = (series.get("serie") or {}).get(str(CENSUS_YEAR))
            numeric, status = parse_sidra_value(original)
            key = (municipality_id, age)
            if key in by_key:
                raise ValueError(f"Chave municipal/idade duplicada: {key!r}.")
            discovered_codes.add(municipality_id)
            by_key[key] = {
                "ano_censo": CENSUS_YEAR,
                "id_municipio": municipality_id,
                "idade": age,
                "pessoas_indigenas": numeric,
                "status_valor": status,
                "valor_original": "" if original is None else str(original),
                "tabela_origem": AGGREGATE_ID,
                "metadados_fonte": source_metadata,
            }

    expected_codes = municipality_codes or discovered_codes
    if municipality_codes is None and len(expected_codes) != EXPECTED_MUNICIPALITIES:
        raise ValueError(
            f"Cobertura municipal inválida: esperados {EXPECTED_MUNICIPALITIES}, "
            f"encontrados {len(expected_codes)}."
        )
    unexpected = discovered_codes - expected_codes
    if unexpected:
        raise ValueError(f"A resposta contém municípios inesperados: {sorted(unexpected)}.")

    rows = []
    for municipality_id in sorted(expected_codes):
        for age in sorted(AGE_IDS):
            rows.append(
                by_key.get(
                    (municipality_id, age),
                    {
                        "ano_censo": CENSUS_YEAR,
                        "id_municipio": municipality_id,
                        "idade": age,
                        "pessoas_indigenas": None,
                        "status_valor": "missing",
                        "valor_original": "",
                        "tabela_origem": AGGREGATE_ID,
                        "metadados_fonte": source_metadata,
                    },
                )
            )
    return rows


def aggregate_age_groups(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Deriva faixas apenas quando todas as idades simples estão disponíveis."""

    rows_by_municipality: dict[str, dict[int, dict[str, Any]]] = {}
    for row in rows:
        rows_by_municipality.setdefault(str(row["id_municipio"]), {})[
            int(row["idade"])
        ] = row

    aggregated = []
    status_priority = (
        "suppressed",
        "unavailable",
        "not_applicable",
        "missing",
    )
    for municipality_id, by_age in sorted(rows_by_municipality.items()):
        for group_key, (age_from, age_to, label) in AGE_GROUPS.items():
            members = [by_age.get(age) for age in range(age_from, age_to + 1)]
            statuses = [
                member.get("status_valor", "missing") if member else "missing"
                for member in members
            ]
            if all(status == "available" for status in statuses):
                value = sum(int(member["pessoas_indigenas"]) for member in members)
                status = "available"
            else:
                value = None
                status = next(
                    candidate
                    for candidate in status_priority
                    if candidate in statuses
                )
            aggregated.append(
                {
                    "ano_censo": CENSUS_YEAR,
                    "id_municipio": municipality_id,
                    "faixa_etaria": group_key,
                    "idade_de": age_from,
                    "idade_ate": age_to,
                    "rotulo": label,
                    "pessoas_indigenas": value,
                    "status_valor": status,
                    "tabela_origem": AGGREGATE_ID,
                }
            )
    return aggregated


def extract_to_directory(
    output_dir: Path,
    *,
    metadata_content: bytes | None = None,
    data_content: bytes | None = None,
    municipality_codes: set[str] | None = None,
    state_code: str = "RS",
    state_id: str = RS_STATE_ID,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Baixa, valida e materializa fonte bruta, estrutura longa e faixas."""

    output_dir.mkdir(parents=True, exist_ok=True)
    metadata_content = metadata_content or download_bytes(METADATA_URL)
    data_content = data_content or download_bytes(data_url(state_id))
    metadata = json.loads(metadata_content)
    query_contract = validate_metadata(metadata)
    extracted_at = datetime.now(timezone.utc).isoformat()
    response_hash = _sha256(data_content)
    source_metadata = {
        "provider": "IBGE",
        "survey": "Censo Demográfico 2022",
        "aggregate": AGGREGATE_ID,
        "period": CENSUS_YEAR,
        "variable": query_contract["variable"],
        "classifications": query_contract["classifications"],
        "territorialLevel": query_contract["territorialLevel"],
        "extractedAt": extracted_at,
        "metadataUrl": METADATA_URL,
        "queryUrl": data_url(state_id),
        "stateCode": state_code,
        "responseSha256": response_hash,
        "metadataSha256": _sha256(metadata_content),
        "importerSchemaVersion": IMPORTER_SCHEMA_VERSION,
    }
    rows = parse_response(
        json.loads(data_content),
        municipality_codes=municipality_codes,
        source_metadata=source_metadata,
    )
    age_groups = aggregate_age_groups(rows)
    manifest = {
        **source_metadata,
        "sourceTableDecision": (
            "Agregado 9970 utilizado porque disponibiliza no nível municipal as "
            "idades simples de 0 a 17 anos, a variável Pessoas indígenas e os "
            "totais de localização e situação do domicílio."
        ),
        "rawRows": len(rows),
        "ageGroupRows": len(age_groups),
        "municipalities": len({row["id_municipio"] for row in rows}),
    }

    (output_dir / "metadata_9970.json").write_bytes(metadata_content)
    (output_dir / f"response_9970_{state_code.lower()}_2022.json").write_bytes(
        data_content
    )
    (output_dir / "population_by_age.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (output_dir / "population_age_groups.json").write_text(
        json.dumps(age_groups, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return rows, age_groups, manifest
