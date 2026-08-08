"""Estimativa municipal da população rural de 4 a 17 anos no Censo 2022.

O SIDRA não publica idades simples por situação rural no nível municipal. Por
isso, o denominador combina as faixas rurais quinquenais da tabela 10089 com a
distribuição etária municipal da tabela 9606 apenas nas duas faixas de borda.
Os códigos IBGE permanecem textos de sete dígitos em todo o fluxo.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import re
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


CENSUS_YEAR = 2022
VARIABLE_ID = "93"
TERRITORIAL_LEVEL = "N6"
RS_STATE_ID = "43"
EXPECTED_MUNICIPALITIES = 497
IMPORTER_SCHEMA_VERSION = 1

RURAL_GROUP_AGGREGATE_ID = "10089"
RURAL_GROUP_AGE_CLASSIFICATION_ID = "58"
RURAL_GROUP_AGE_IDS = {
    "0_4": "1140",
    "5_9": "1141",
    "10_14": "1142",
    "15_19": "1143",
}
SEX_CLASSIFICATION_ID = "2"
SEX_TOTAL_ID = "6794"
LOCATION_CLASSIFICATION_ID = "2661"
LOCATION_TOTAL_ID = "32776"
HOUSEHOLD_SITUATION_CLASSIFICATION_ID = "1"
HOUSEHOLD_SITUATION_RURAL_ID = "2"

EXACT_AGE_AGGREGATE_ID = "9606"
EXACT_AGE_CLASSIFICATION_ID = "287"
RACE_CLASSIFICATION_ID = "86"
RACE_TOTAL_ID = "95251"
EXACT_AGE_IDS = {age: str(6557 + age) for age in range(20)}

RURAL_GROUP_METADATA_URL = (
    "https://servicodados.ibge.gov.br/api/v3/agregados/"
    f"{RURAL_GROUP_AGGREGATE_ID}/metadados"
)
EXACT_AGE_METADATA_URL = (
    "https://servicodados.ibge.gov.br/api/v3/agregados/"
    f"{EXACT_AGE_AGGREGATE_ID}/metadados"
)


def rural_group_data_url() -> str:
    age_ids = ",".join(RURAL_GROUP_AGE_IDS.values())
    return (
        "https://servicodados.ibge.gov.br/api/v3/agregados/"
        f"{RURAL_GROUP_AGGREGATE_ID}/periodos/{CENSUS_YEAR}/variaveis/{VARIABLE_ID}"
        f"?localidades={TERRITORIAL_LEVEL}[N3[{RS_STATE_ID}]]"
        f"&classificacao={SEX_CLASSIFICATION_ID}[{SEX_TOTAL_ID}]"
        f"|{RURAL_GROUP_AGE_CLASSIFICATION_ID}[{age_ids}]"
        f"|{LOCATION_CLASSIFICATION_ID}[{LOCATION_TOTAL_ID}]"
        f"|{HOUSEHOLD_SITUATION_CLASSIFICATION_ID}"
        f"[{HOUSEHOLD_SITUATION_RURAL_ID}]"
    )


def exact_age_data_url() -> str:
    age_ids = ",".join(EXACT_AGE_IDS.values())
    return (
        "https://servicodados.ibge.gov.br/api/v3/agregados/"
        f"{EXACT_AGE_AGGREGATE_ID}/periodos/{CENSUS_YEAR}/variaveis/{VARIABLE_ID}"
        f"?localidades={TERRITORIAL_LEVEL}[N3[{RS_STATE_ID}]]"
        f"&classificacao={RACE_CLASSIFICATION_ID}[{RACE_TOTAL_ID}]"
        f"|{SEX_CLASSIFICATION_ID}[{SEX_TOTAL_ID}]"
        f"|{EXACT_AGE_CLASSIFICATION_ID}[{age_ids}]"
    )


def _normalise_text(value: object) -> str:
    decomposed = unicodedata.normalize("NFKD", str(value or ""))
    without_marks = "".join(
        character for character in decomposed if not unicodedata.combining(character)
    )
    return " ".join(without_marks.casefold().split())


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def download_bytes(url: str, *, attempts: int = 4, timeout: int = 120) -> bytes:
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
                return gzip.decompress(content) if content.startswith(b"\x1f\x8b") else content
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


def _validate_common_metadata(metadata: dict[str, Any], aggregate_id: str) -> dict[str, Any]:
    if str(metadata.get("id")) != aggregate_id:
        raise ValueError(f"Metadados não correspondem ao agregado SIDRA {aggregate_id}.")
    periodicity = metadata.get("periodicidade") or {}
    if int(periodicity.get("inicio") or 0) > CENSUS_YEAR or int(
        periodicity.get("fim") or 0
    ) < CENSUS_YEAR:
        raise ValueError(f"O período 2022 não está disponível no agregado {aggregate_id}.")
    administrative = (metadata.get("nivelTerritorial") or {}).get("Administrativo") or []
    if TERRITORIAL_LEVEL not in administrative:
        raise ValueError(f"O nível municipal N6 não está disponível no agregado {aggregate_id}.")
    variables = {
        str(variable.get("id")): variable for variable in metadata.get("variaveis", [])
    }
    variable = variables.get(VARIABLE_ID)
    if not variable or _normalise_text(variable.get("nome")) != "populacao residente":
        raise ValueError(f"A variável 93 não representa População residente em {aggregate_id}.")
    if _normalise_text(variable.get("unidade")) != "pessoas":
        raise ValueError(f"A variável 93 não está expressa em pessoas em {aggregate_id}.")
    return variable


def validate_rural_group_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """Valida a semântica da tabela rural quinquenal antes da consulta."""

    variable = _validate_common_metadata(metadata, RURAL_GROUP_AGGREGATE_ID)
    normalized_name = _normalise_text(metadata.get("nome"))
    for fragment in ("grupos de idade", "situacao do domicilio"):
        if fragment not in normalized_name:
            raise ValueError(f"Nome semântico inesperado para o agregado 10089: {fragment}.")

    expected_categories = {
        SEX_CLASSIFICATION_ID: ("sexo", SEX_TOTAL_ID, "total"),
        LOCATION_CLASSIFICATION_ID: (
            "localizacao do domicilio",
            LOCATION_TOTAL_ID,
            "total",
        ),
        HOUSEHOLD_SITUATION_CLASSIFICATION_ID: (
            "situacao do domicilio",
            HOUSEHOLD_SITUATION_RURAL_ID,
            "rural",
        ),
    }
    for classification_id, (classification_name, category_id, category_name) in expected_categories.items():
        classification = _classification(metadata, classification_id)
        if _normalise_text(classification.get("nome")) != classification_name:
            raise ValueError(f"Classificação {classification_id} possui semântica inesperada.")
        if _normalise_text(_category_map(classification).get(category_id)) != category_name:
            raise ValueError(f"Categoria {category_id} possui semântica inesperada.")

    age_classification = _classification(metadata, RURAL_GROUP_AGE_CLASSIFICATION_ID)
    if _normalise_text(age_classification.get("nome")) != "grupo de idade":
        raise ValueError("A classificação 58 não representa Grupo de idade.")
    age_categories = _category_map(age_classification)
    expected_age_labels = {
        "0_4": "0 a 4 anos",
        "5_9": "5 a 9 anos",
        "10_14": "10 a 14 anos",
        "15_19": "15 a 19 anos",
    }
    for key, category_id in RURAL_GROUP_AGE_IDS.items():
        if _normalise_text(age_categories.get(category_id)) != expected_age_labels[key]:
            raise ValueError(f"Categoria {category_id} não representa a faixa {key}.")
    return {
        "aggregate": RURAL_GROUP_AGGREGATE_ID,
        "variable": {"id": VARIABLE_ID, "label": variable["nome"], "unit": variable["unidade"]},
        "ageCategories": {
            key: {"id": category_id, "label": age_categories[category_id]}
            for key, category_id in RURAL_GROUP_AGE_IDS.items()
        },
    }


def validate_exact_age_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """Valida a tabela municipal de idades simples usada somente nos pesos."""

    variable = _validate_common_metadata(metadata, EXACT_AGE_AGGREGATE_ID)
    if _normalise_text(metadata.get("nome")) != _normalise_text(
        "População residente, por cor ou raça, segundo o sexo e a idade"
    ):
        raise ValueError("Nome semântico inesperado para o agregado SIDRA 9606.")
    fixed = {
        RACE_CLASSIFICATION_ID: ("cor ou raca", RACE_TOTAL_ID),
        SEX_CLASSIFICATION_ID: ("sexo", SEX_TOTAL_ID),
    }
    for classification_id, (name, category_id) in fixed.items():
        classification = _classification(metadata, classification_id)
        if _normalise_text(classification.get("nome")) != name:
            raise ValueError(f"Classificação {classification_id} possui semântica inesperada.")
        if _normalise_text(_category_map(classification).get(category_id)) != "total":
            raise ValueError(f"Categoria {category_id} não representa Total.")
    age_classification = _classification(metadata, EXACT_AGE_CLASSIFICATION_ID)
    if _normalise_text(age_classification.get("nome")) != "idade":
        raise ValueError("A classificação 287 não representa idade.")
    age_categories = _category_map(age_classification)
    for age, category_id in EXACT_AGE_IDS.items():
        expected = "Menos de 1 ano" if age == 0 else ("1 ano" if age == 1 else f"{age} anos")
        if _normalise_text(age_categories.get(category_id)) != _normalise_text(expected):
            raise ValueError(f"Categoria {category_id} não representa a idade {age}.")
    return {
        "aggregate": EXACT_AGE_AGGREGATE_ID,
        "variable": {"id": VARIABLE_ID, "label": variable["nome"], "unit": variable["unidade"]},
        "ageCategories": {
            str(age): {"id": category_id, "label": age_categories[category_id]}
            for age, category_id in EXACT_AGE_IDS.items()
        },
    }


def parse_sidra_value(original: object) -> tuple[int | None, str]:
    """Converte somente zeros e inteiros; preserva estados especiais do SIDRA."""

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
        raise ValueError(f"Resultado sem classificação única {classification_id}.")
    categories = matches[0].get("categoria") or {}
    if len(categories) != 1:
        raise ValueError(f"Resultado sem categoria única em {classification_id}.")
    key, label = next(iter(categories.items()))
    return str(key), str(label)


def _validate_variable_response(payload: list[dict[str, Any]]) -> dict[str, Any]:
    if len(payload) != 1:
        raise ValueError("A resposta SIDRA deve conter exatamente uma variável.")
    variable = payload[0]
    if str(variable.get("id")) != VARIABLE_ID:
        raise ValueError("A resposta SIDRA não contém a variável 93.")
    if _normalise_text(variable.get("variavel")) != "populacao residente":
        raise ValueError("O rótulo da variável SIDRA é incompatível.")
    if _normalise_text(variable.get("unidade")) != "pessoas":
        raise ValueError("A resposta SIDRA não está expressa em pessoas.")
    return variable


def _validate_locality(series: dict[str, Any]) -> str:
    locality = series.get("localidade") or {}
    municipality_id = str(locality.get("id") or "")
    if not re.fullmatch(r"\d{7}", municipality_id):
        raise ValueError(f"Código municipal inválido na resposta: {municipality_id!r}.")
    level = locality.get("nivel") or {}
    if str(level.get("id")) != TERRITORIAL_LEVEL or _normalise_text(
        level.get("nome")
    ) != "municipio":
        raise ValueError("A resposta contém nível territorial não municipal.")
    return municipality_id


def _validate_expected_codes(discovered: set[str], expected: set[str]) -> None:
    unexpected = discovered - expected
    if unexpected:
        raise ValueError(f"A resposta contém municípios inesperados: {sorted(unexpected)}.")


def parse_rural_group_response(
    payload: list[dict[str, Any]],
    *,
    municipality_codes: set[str],
) -> list[dict[str, Any]]:
    """Normaliza uma linha por município e faixa rural quinquenal."""

    variable = _validate_variable_response(payload)
    key_by_age_id = {category_id: key for key, category_id in RURAL_GROUP_AGE_IDS.items()}
    by_key: dict[tuple[str, str], dict[str, Any]] = {}
    discovered: set[str] = set()
    for result in variable.get("resultados", []):
        age_id, _ = _result_category(result, RURAL_GROUP_AGE_CLASSIFICATION_ID)
        sex_id, _ = _result_category(result, SEX_CLASSIFICATION_ID)
        location_id, _ = _result_category(result, LOCATION_CLASSIFICATION_ID)
        situation_id, _ = _result_category(result, HOUSEHOLD_SITUATION_CLASSIFICATION_ID)
        if age_id not in key_by_age_id:
            raise ValueError(f"Faixa etária inesperada na resposta: {age_id}.")
        if (sex_id, location_id, situation_id) != (
            SEX_TOTAL_ID,
            LOCATION_TOTAL_ID,
            HOUSEHOLD_SITUATION_RURAL_ID,
        ):
            raise ValueError("A resposta não corresponde a sexo total, localização total e situação rural.")
        for series in result.get("series", []):
            municipality_id = _validate_locality(series)
            original = (series.get("serie") or {}).get(str(CENSUS_YEAR))
            numeric, status = parse_sidra_value(original)
            key = (municipality_id, key_by_age_id[age_id])
            if key in by_key:
                raise ValueError(f"Chave municipal/faixa duplicada: {key!r}.")
            discovered.add(municipality_id)
            by_key[key] = {
                "ano_censo": CENSUS_YEAR,
                "id_municipio": municipality_id,
                "faixa_etaria": key[1],
                "populacao_rural": numeric,
                "status_valor": status,
                "valor_original": "" if original is None else str(original),
                "tabela_origem": RURAL_GROUP_AGGREGATE_ID,
            }
    _validate_expected_codes(discovered, municipality_codes)
    return [
        by_key.get(
            (municipality_id, age_group),
            {
                "ano_censo": CENSUS_YEAR,
                "id_municipio": municipality_id,
                "faixa_etaria": age_group,
                "populacao_rural": None,
                "status_valor": "missing",
                "valor_original": "",
                "tabela_origem": RURAL_GROUP_AGGREGATE_ID,
            },
        )
        for municipality_id in sorted(municipality_codes)
        for age_group in RURAL_GROUP_AGE_IDS
    ]


def parse_exact_age_response(
    payload: list[dict[str, Any]],
    *,
    municipality_codes: set[str],
) -> list[dict[str, Any]]:
    """Normaliza a população municipal total por idade simples de 0 a 19."""

    variable = _validate_variable_response(payload)
    age_by_id = {category_id: age for age, category_id in EXACT_AGE_IDS.items()}
    by_key: dict[tuple[str, int], dict[str, Any]] = {}
    discovered: set[str] = set()
    for result in variable.get("resultados", []):
        race_id, _ = _result_category(result, RACE_CLASSIFICATION_ID)
        sex_id, _ = _result_category(result, SEX_CLASSIFICATION_ID)
        age_id, _ = _result_category(result, EXACT_AGE_CLASSIFICATION_ID)
        if race_id != RACE_TOTAL_ID or sex_id != SEX_TOTAL_ID:
            raise ValueError("A resposta de idades simples não usa raça e sexo totais.")
        if age_id not in age_by_id:
            raise ValueError(f"Idade inesperada na resposta: {age_id}.")
        for series in result.get("series", []):
            municipality_id = _validate_locality(series)
            original = (series.get("serie") or {}).get(str(CENSUS_YEAR))
            numeric, status = parse_sidra_value(original)
            key = (municipality_id, age_by_id[age_id])
            if key in by_key:
                raise ValueError(f"Chave municipal/idade duplicada: {key!r}.")
            discovered.add(municipality_id)
            by_key[key] = {
                "ano_censo": CENSUS_YEAR,
                "id_municipio": municipality_id,
                "idade": key[1],
                "populacao_municipal": numeric,
                "status_valor": status,
                "valor_original": "" if original is None else str(original),
                "tabela_origem": EXACT_AGE_AGGREGATE_ID,
            }
    _validate_expected_codes(discovered, municipality_codes)
    return [
        by_key.get(
            (municipality_id, age),
            {
                "ano_censo": CENSUS_YEAR,
                "id_municipio": municipality_id,
                "idade": age,
                "populacao_municipal": None,
                "status_valor": "missing",
                "valor_original": "",
                "tabela_origem": EXACT_AGE_AGGREGATE_ID,
            },
        )
        for municipality_id in sorted(municipality_codes)
        for age in EXACT_AGE_IDS
    ]


def _unavailable_status(statuses: list[str]) -> str:
    for candidate in ("suppressed", "unavailable", "not_applicable", "missing"):
        if candidate in statuses:
            return candidate
    return "unavailable"


def estimate_population_4_17(
    rural_group_rows: list[dict[str, Any]],
    exact_age_rows: list[dict[str, Any]],
    *,
    source_metadata: dict[str, Any],
) -> list[dict[str, Any]]:
    """Estima 4–17 sem arredondar e preserva indisponibilidades das fontes."""

    rural_by_municipality: dict[str, dict[str, dict[str, Any]]] = {}
    for row in rural_group_rows:
        rural_by_municipality.setdefault(str(row["id_municipio"]), {})[
            str(row["faixa_etaria"])
        ] = row
    ages_by_municipality: dict[str, dict[int, dict[str, Any]]] = {}
    for row in exact_age_rows:
        ages_by_municipality.setdefault(str(row["id_municipio"]), {})[
            int(row["idade"])
        ] = row

    rows: list[dict[str, Any]] = []
    municipality_ids = sorted(set(rural_by_municipality) | set(ages_by_municipality))
    for municipality_id in municipality_ids:
        rural = rural_by_municipality.get(municipality_id, {})
        ages = ages_by_municipality.get(municipality_id, {})
        rural_members = [rural.get(key) for key in RURAL_GROUP_AGE_IDS]
        age_members = [ages.get(age) for age in (*range(0, 5), *range(15, 20))]
        statuses = [
            str(member.get("status_valor") or "missing") if member else "missing"
            for member in (*rural_members, *age_members)
        ]
        value: float | None = None
        weight_4: float | None = None
        weight_15_17: float | None = None
        reason: str | None = None
        status = "available"
        if any(item != "available" for item in statuses):
            status = _unavailable_status(statuses)
            reason = "source_value_unavailable"
        else:
            rural_values = {
                key: int(rural[key]["populacao_rural"]) for key in RURAL_GROUP_AGE_IDS
            }
            age_values = {age: int(ages[age]["populacao_municipal"]) for age in ages}
            total_0_4 = sum(age_values[age] for age in range(0, 5))
            total_15_19 = sum(age_values[age] for age in range(15, 20))
            if total_0_4 == 0 and rural_values["0_4"] != 0:
                status = "unavailable"
                reason = "inconsistent_zero_total_0_4"
            elif total_15_19 == 0 and rural_values["15_19"] != 0:
                status = "unavailable"
                reason = "inconsistent_zero_total_15_19"
            else:
                weight_4 = (
                    age_values[4] / total_0_4 if total_0_4 else None
                )
                weight_15_17 = (
                    sum(age_values[age] for age in range(15, 18)) / total_15_19
                    if total_15_19
                    else None
                )
                edge_4 = rural_values["0_4"] * weight_4 if weight_4 is not None else 0.0
                edge_15_17 = (
                    rural_values["15_19"] * weight_15_17
                    if weight_15_17 is not None
                    else 0.0
                )
                value = (
                    edge_4
                    + rural_values["5_9"]
                    + rural_values["10_14"]
                    + edge_15_17
                )

        rows.append(
            {
                "ano_censo": CENSUS_YEAR,
                "id_municipio": municipality_id,
                "populacao_rural_estimada_4_17": value,
                "status_valor": status,
                "motivo_indisponibilidade": reason,
                "populacao_rural_0_4": rural.get("0_4", {}).get("populacao_rural"),
                "populacao_rural_5_9": rural.get("5_9", {}).get("populacao_rural"),
                "populacao_rural_10_14": rural.get("10_14", {}).get("populacao_rural"),
                "populacao_rural_15_19": rural.get("15_19", {}).get("populacao_rural"),
                "peso_idade_4_no_grupo_0_4": weight_4,
                "peso_idades_15_17_no_grupo_15_19": weight_15_17,
                "metodo_estimacao": (
                    "rural_0_4*peso_municipal_idade_4 + rural_5_9 + rural_10_14 + "
                    "rural_15_19*peso_municipal_idades_15_17"
                ),
                "metadados_fonte": source_metadata,
            }
        )
    return rows


def extract_to_directory(
    output_dir: Path,
    *,
    municipality_codes: set[str],
    rural_metadata_content: bytes | None = None,
    rural_data_content: bytes | None = None,
    exact_metadata_content: bytes | None = None,
    exact_data_content: bytes | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Adquire, valida e materializa um snapshot auditável em diretório de staging."""

    output_dir.mkdir(parents=True, exist_ok=True)
    rural_metadata_content = rural_metadata_content or download_bytes(RURAL_GROUP_METADATA_URL)
    rural_data_content = rural_data_content or download_bytes(rural_group_data_url())
    exact_metadata_content = exact_metadata_content or download_bytes(EXACT_AGE_METADATA_URL)
    exact_data_content = exact_data_content or download_bytes(exact_age_data_url())

    rural_contract = validate_rural_group_metadata(json.loads(rural_metadata_content))
    exact_contract = validate_exact_age_metadata(json.loads(exact_metadata_content))
    source_metadata = {
        "provider": "IBGE",
        "survey": "Censo Demográfico 2022",
        "period": CENSUS_YEAR,
        "ruralGroups": {
            **rural_contract,
            "metadataUrl": RURAL_GROUP_METADATA_URL,
            "queryUrl": rural_group_data_url(),
            "metadataSha256": _sha256(rural_metadata_content),
            "responseSha256": _sha256(rural_data_content),
        },
        "exactAgeWeights": {
            **exact_contract,
            "metadataUrl": EXACT_AGE_METADATA_URL,
            "queryUrl": exact_age_data_url(),
            "metadataSha256": _sha256(exact_metadata_content),
            "responseSha256": _sha256(exact_data_content),
        },
        "importerSchemaVersion": IMPORTER_SCHEMA_VERSION,
    }
    rural_rows = parse_rural_group_response(
        json.loads(rural_data_content), municipality_codes=municipality_codes
    )
    exact_rows = parse_exact_age_response(
        json.loads(exact_data_content), municipality_codes=municipality_codes
    )
    estimates = estimate_population_4_17(
        rural_rows, exact_rows, source_metadata=source_metadata
    )
    if len(estimates) != len(municipality_codes):
        raise ValueError(
            f"Cobertura municipal inválida: {len(estimates)} de {len(municipality_codes)}."
        )

    raw_files = {
        "sidra_10089_metadata.json": rural_metadata_content,
        "sidra_10089_response.json": rural_data_content,
        "sidra_9606_metadata.json": exact_metadata_content,
        "sidra_9606_response.json": exact_data_content,
    }
    for filename, content in raw_files.items():
        (output_dir / filename).write_bytes(content)
    (output_dir / "population_estimates.json").write_text(
        json.dumps(estimates, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    manifest = {
        "schemaVersion": IMPORTER_SCHEMA_VERSION,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "municipalityCount": len(estimates),
        "availableCount": sum(row["status_valor"] == "available" for row in estimates),
        "sourceMetadata": source_metadata,
        "method": (
            "Faixas rurais quinquenais da tabela 10089; as bordas 4 e 15–17 "
            "são estimadas com pesos da distribuição etária municipal da tabela 9606."
        ),
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return estimates, manifest
