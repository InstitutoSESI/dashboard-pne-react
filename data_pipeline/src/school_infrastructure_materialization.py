"""Contrato e materialização da infraestrutura escolar canônica.

As fórmulas permanecem exclusivamente em ``school_infrastructure.py``. Este
módulo apenas organiza o resultado agregado, adapta consumidores legados e
valida artefatos já materializados.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import re
import shutil
import tempfile
from collections import Counter
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import pandas as pd

from src.school_infrastructure import INDICATORS, aggregate_school_infrastructure


SCHEMA_VERSION = 1
CONTRACT_VERSION = "school-infrastructure-v2"
REFERENCE_YEAR = 2025
SOURCE = "Censo Escolar/INEP"
INDICATOR_ORDER = (
    "agua_potavel",
    "energia_eletrica",
    "internet",
    "biblioteca_sala_leitura",
    "quadra_esportes",
    "esgoto_rede_publica",
)
CUT_ORDER = (
    "total",
    "publica",
    "municipal",
    "estadual",
    "federal",
    "privada",
    "urbana",
    "rural",
)
RESULT_KEYS = (
    "numerator",
    "denominator",
    "percentage",
    "totalActiveSchools",
    "observedSchools",
    "missingSchools",
    "status",
)
VALID_STATUSES = {"published", "partial", "unavailable"}
CUT_KINDS = {
    "total": "total",
    "publica": "dependency",
    "municipal": "dependency",
    "estadual": "dependency",
    "federal": "dependency",
    "privada": "dependency",
    "urbana": "location",
    "rural": "location",
}
EXPECTED_STATE_TOTALS = {
    "total": 9946,
    "federal": 51,
    "estadual": 2302,
    "municipal": 4879,
    "publica": 7232,
    "privada": 2714,
    "urbana": 8235,
    "rural": 1711,
}
EXPECTED_STATE_INDICATORS = {
    "agua_potavel": (9877, 9946),
    "energia_eletrica": (9946, 9946),
    "internet": (9866, 9946),
    "biblioteca_sala_leitura": (7234, 9946),
    "quadra_esportes": (4495, 9946),
    "esgoto_rede_publica": (6481, 9946),
}


def json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8")


def write_json_atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(json_bytes(value))
    os.replace(temporary, path)


def _result(row: pd.Series) -> dict[str, Any]:
    percentage = row["percentage"]
    return {
        "numerator": int(row["numerator"]),
        "denominator": int(row["denominator"]),
        "percentage": None if pd.isna(percentage) else float(percentage),
        "totalActiveSchools": int(row["totalActiveSchools"]),
        "observedSchools": int(row["observedSchools"]),
        "missingSchools": int(row["missingSchools"]),
        "status": str(row["status"]),
    }


def build_contracts(
    source: pd.DataFrame,
    municipality_codes: Iterable[str],
) -> dict[str, dict[str, Any]]:
    """Agrega uma vez e produz os contratos municipais em ordem estável."""
    aggregate = aggregate_school_infrastructure(source, REFERENCE_YEAR)
    codes = tuple(sorted(str(code) for code in municipality_codes))
    grouped = {
        str(code): group
        for code, group in aggregate.groupby("id_municipio", sort=True)
    }
    missing = sorted(set(codes) - set(grouped))
    extra = sorted(set(grouped) - set(codes))
    if missing or extra:
        raise ValueError(
            f"Universo municipal divergente; ausentes={missing[:5]}, extras={extra[:5]}"
        )

    definitions = {
        item.key: {
            "label": item.label,
            "sourceVariable": item.source_column.upper(),
        }
        for item in INDICATORS
    }
    contracts: dict[str, dict[str, Any]] = {}
    for code in codes:
        rows = grouped[code].set_index(["recorte", "indicador"])
        cuts: dict[str, Any] = {}
        for cut in CUT_ORDER:
            cut_rows = grouped[code][grouped[code]["recorte"].eq(cut)]
            if len(cut_rows) != len(INDICATOR_ORDER):
                raise ValueError(f"{code}/{cut}: indicadores incompletos")
            active_counts = cut_rows["totalActiveSchools"].unique().tolist()
            if len(active_counts) != 1:
                raise ValueError(f"{code}/{cut}: universo inconsistente")
            cuts[cut] = {
                "kind": CUT_KINDS[cut],
                "totalActiveSchools": int(active_counts[0]),
                "indicators": {
                    indicator: _result(rows.loc[(cut, indicator)])
                    for indicator in INDICATOR_ORDER
                },
            }
        contracts[code] = {
            "contractVersion": CONTRACT_VERSION,
            "referenceYear": REFERENCE_YEAR,
            "availableYears": [REFERENCE_YEAR],
            "universe": {
                "unit": "school",
                "identifier": "CO_ENTIDADE",
                "municipalityVariable": "CO_MUNICIPIO",
                "activeStatus": {
                    "variable": "TP_SITUACAO_FUNCIONAMENTO",
                    "value": 1,
                },
                "deduplication": "CO_ENTIDADE",
            },
            "indicatorDefinitions": definitions,
            "years": [{"year": REFERENCE_YEAR, "cuts": cuts}],
        }
    return contracts


def result_for(
    contract: Mapping[str, Any], indicator: str, cut: str = "total"
) -> Mapping[str, Any]:
    return contract["years"][0]["cuts"][cut]["indicators"][indicator]


def _replace_year_value(
    rows: list[dict[str, Any]], field: str, value: Any, **identity: Any
) -> None:
    for row in rows:
        if row.get("ano") == REFERENCE_YEAR and all(
            row.get(key) == expected for key, expected in identity.items()
        ):
            row[field] = value
            return


def adapt_legacy_document(
    document: Mapping[str, Any], contract: Mapping[str, Any]
) -> dict[str, Any]:
    """Acrescenta o v2 e deriva somente os campos legados de Internet de 2025.

    ``series``, ``resumo_ultimo_ano``, ``por_rede`` e ``por_localizacao``
    permanecem temporariamente. Eles só poderão ser removidos após a migração
    completa do frontend.
    """
    adapted = copy.deepcopy(document)
    network = adapted["blocos"]["rede_escolar"]
    legacy = network["infraestrutura"]
    for key in (
        "contractVersion",
        "referenceYear",
        "availableYears",
        "universe",
        "indicatorDefinitions",
        "years",
    ):
        legacy[key] = copy.deepcopy(contract[key])

    total = result_for(contract, "internet")
    rounded = (
        None if total["percentage"] is None else round(total["percentage"], 1)
    )
    _replace_year_value(legacy.get("series", {}).get("internet", []), "valor", rounded)
    if legacy.get("ultimo_ano") == REFERENCE_YEAR:
        legacy.get("resumo_ultimo_ano", {})["internet"] = rounded

    for dimension, rows in (
        ("dependencia", legacy.get("por_rede", [])),
        ("localizacao", legacy.get("por_localizacao", [])),
    ):
        for row in rows:
            if row.get("ano") != REFERENCE_YEAR:
                continue
            cut = row.get(dimension)
            if cut not in CUT_ORDER:
                continue
            current = result_for(contract, "internet", cut)
            row["escolas"] = current["totalActiveSchools"]
            row["perc_internet"] = (
                None
                if current["percentage"] is None
                else round(current["percentage"], 1)
            )

    _replace_year_value(
        network.get("series", {}).get("internet", []),
        "perc_internet",
        rounded,
    )
    if network.get("ultimo_ano") == REFERENCE_YEAR:
        network.get("resumo_ultimo_ano", {})["perc_internet"] = rounded
    return adapted


def adapt_pne_internet_details(
    payload: Mapping[str, Any] | None, contract: Mapping[str, Any]
) -> dict[str, Any] | None:
    """Substitui 2025 por um adaptador puro do resultado canônico."""
    if payload is None:
        return None
    adapted = copy.deepcopy(payload)
    total = result_for(contract, "internet")
    for key in ("series_total", "series_components", "series_dependencia"):
        if key in adapted:
            adapted[key] = [
                row for row in adapted[key] if row.get("ano") != REFERENCE_YEAR
            ]
    if total["denominator"] > 0:
        adapted.setdefault("series_total", []).append(
            {"ano": REFERENCE_YEAR, "valor": total["numerator"]}
        )
        adapted.setdefault("series_components", []).append(
            {
                "ano": REFERENCE_YEAR,
                "numerador": total["numerator"],
                "denominador": total["denominator"],
                "percentual": total["percentage"],
            }
        )
    dependencies = {
        cut: result_for(contract, "internet", cut)["numerator"]
        for cut in ("publica", "privada", "estadual", "municipal", "federal")
    }
    adapted.setdefault("series_dependencia", []).append(
        {"ano": REFERENCE_YEAR, **dependencies}
    )
    return adapted


def adapt_pne_internet_yearly(
    yearly: pd.DataFrame, contract: Mapping[str, Any]
) -> pd.DataFrame:
    """Mantém 2014–2024 e substitui o percentual de 2025 sem nova fórmula."""
    historical = yearly[yearly["ano"].ne(REFERENCE_YEAR)][["ano", "valor"]].copy()
    current = result_for(contract, "internet")
    if current["percentage"] is not None:
        historical = pd.concat(
            [
                historical,
                pd.DataFrame(
                    [{"ano": REFERENCE_YEAR, "valor": current["percentage"]}]
                ),
            ],
            ignore_index=True,
        )
    return historical.sort_values("ano").reset_index(drop=True)


def municipality_content_hash(directory: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted((directory / "municipios").glob("*.json")):
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def tree_hash(directory: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(path for path in directory.rglob("*") if path.is_file()):
        relative = path.relative_to(directory).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def build_manifest(stage: Path, codes: Iterable[str]) -> dict[str, Any]:
    municipality_codes = sorted(str(code) for code in codes)
    return {
        "schemaVersion": SCHEMA_VERSION,
        "contractVersion": CONTRACT_VERSION,
        "referenceYear": REFERENCE_YEAR,
        "municipalityCount": len(municipality_codes),
        "fileCount": len(municipality_codes),
        "indicatorCount": len(INDICATOR_ORDER),
        "cutCount": len(CUT_ORDER),
        "source": SOURCE,
        "municipalityCodes": municipality_codes,
        "contentHash": municipality_content_hash(stage),
    }


def _contract(document: Mapping[str, Any]) -> Mapping[str, Any]:
    return document["blocos"]["rede_escolar"]["infraestrutura"]


def validate_stage(
    stage: Path,
    official_codes: Iterable[str],
    *,
    expected_count: int = 497,
) -> dict[str, Any]:
    """Valida somente arquivos materializados; não acessa nem recalcula a fonte."""
    errors: list[str] = []
    expected = sorted(str(code) for code in official_codes)
    files = sorted((stage / "municipios").glob("*.json"))
    documents: dict[str, Any] = {}
    if len(files) != expected_count:
        errors.append(f"Esperados {expected_count} arquivos; encontrados {len(files)}")
    for path in files:
        try:
            raw = path.read_bytes()
            text = raw.decode("utf-8")
            if re.search(r"\b(?:NaN|Infinity|-Infinity)\b", text):
                errors.append(f"{path.name}: valor JSON não finito")
                continue
            if re.search(r"[A-Za-z]:\\\\|/Users/|/home/", text):
                errors.append(f"{path.name}: caminho local encontrado")
            document = json.loads(text)
            code = str(document.get("id_municipio"))
            if code != path.stem:
                errors.append(f"{path.name}: id_municipio divergente ({code})")
            if code in documents:
                errors.append(f"{path.name}: município duplicado")
            documents[code] = document
        except Exception as exc:
            errors.append(f"{path.name}: JSON inválido: {exc}")
    if sorted(documents) != expected:
        errors.append("Conjunto municipal difere do cadastro oficial")

    state_active = Counter()
    state_indicators = Counter()
    for code, document in documents.items():
        try:
            contract = _contract(document)
            if contract.get("contractVersion") != CONTRACT_VERSION:
                raise ValueError("contractVersion incorreto")
            if contract.get("referenceYear") != REFERENCE_YEAR:
                raise ValueError("referenceYear incorreto")
            if contract.get("availableYears") != [REFERENCE_YEAR]:
                raise ValueError("availableYears incorreto")
            if list(contract["indicatorDefinitions"]) != list(INDICATOR_ORDER):
                raise ValueError("indicadores ou ordem incorretos")
            if len(contract["years"]) != 1 or contract["years"][0]["year"] != REFERENCE_YEAR:
                raise ValueError("years incorreto")
            cuts = contract["years"][0]["cuts"]
            if list(cuts) != list(CUT_ORDER):
                raise ValueError("recortes ou ordem incorretos")
            for cut_name, cut in cuts.items():
                if set(cut) != {"kind", "totalActiveSchools", "indicators"}:
                    raise ValueError(f"{cut_name}: chaves de recorte inesperadas")
                if list(cut["indicators"]) != list(INDICATOR_ORDER):
                    raise ValueError(f"{cut_name}: indicadores incorretos")
                active = cut["totalActiveSchools"]
                if not isinstance(active, int) or isinstance(active, bool) or active < 0:
                    raise ValueError(f"{cut_name}: totalActiveSchools inválido")
                state_active[cut_name] += active
                for indicator, result in cut["indicators"].items():
                    if list(result) != list(RESULT_KEYS):
                        raise ValueError(f"{cut_name}/{indicator}: chaves inesperadas")
                    numerator = result["numerator"]
                    denominator = result["denominator"]
                    observed = result["observedSchools"]
                    missing = result["missingSchools"]
                    percentage = result["percentage"]
                    for field, value in (
                        ("numerator", numerator),
                        ("denominator", denominator),
                        ("observedSchools", observed),
                        ("missingSchools", missing),
                    ):
                        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                            raise ValueError(f"{cut_name}/{indicator}: {field} inválido")
                    if numerator > denominator or denominator != observed:
                        raise ValueError(f"{cut_name}/{indicator}: contagens inválidas")
                    if missing != active - observed:
                        raise ValueError(f"{cut_name}/{indicator}: ausências inválidas")
                    if denominator == 0 and percentage is not None:
                        raise ValueError(f"{cut_name}/{indicator}: percentual deveria ser null")
                    if denominator > 0 and (
                        not isinstance(percentage, (int, float))
                        or isinstance(percentage, bool)
                        or not math.isfinite(percentage)
                        or not 0 <= percentage <= 100
                    ):
                        raise ValueError(f"{cut_name}/{indicator}: percentual inválido")
                    if result["status"] not in VALID_STATUSES:
                        raise ValueError(f"{cut_name}/{indicator}: status inválido")
                    if cut_name == "total":
                        state_indicators[(indicator, "numerator")] += numerator
                        state_indicators[(indicator, "denominator")] += denominator
            for indicator in INDICATOR_ORDER:
                def counts(
                    cut_name: str,
                    *,
                    _cuts=cuts,
                    _indicator=indicator,
                ) -> tuple[int, int, int, int, int]:
                    item = _cuts[cut_name]["indicators"][_indicator]
                    return (
                        item["totalActiveSchools"],
                        item["observedSchools"],
                        item["missingSchools"],
                        item["numerator"],
                        item["denominator"],
                    )
                public = tuple(
                    sum(values)
                    for values in zip(
                        counts("municipal"), counts("estadual"), counts("federal")
                    )
                )
                if counts("publica") != public:
                    raise ValueError(f"{indicator}: rede pública não reconcilia")
                total_dependencies = tuple(
                    left + right
                    for left, right in zip(counts("publica"), counts("privada"))
                )
                if counts("total") != total_dependencies:
                    raise ValueError(f"{indicator}: dependências não reconciliam")
                total_locations = tuple(
                    left + right
                    for left, right in zip(counts("urbana"), counts("rural"))
                )
                if counts("total") != total_locations:
                    raise ValueError(f"{indicator}: localizações não reconciliam")
        except Exception as exc:
            errors.append(f"{code}: {exc}")

    for cut, expected_total in EXPECTED_STATE_TOTALS.items():
        if state_active[cut] != expected_total:
            errors.append(
                f"RS/{cut}: esperado {expected_total}, obtido {state_active[cut]}"
            )
    for indicator, expected_values in EXPECTED_STATE_INDICATORS.items():
        actual = (
            state_indicators[(indicator, "numerator")],
            state_indicators[(indicator, "denominator")],
        )
        if actual != expected_values:
            errors.append(f"RS/{indicator}: esperado {expected_values}, obtido {actual}")
    return {
        "schemaVersion": SCHEMA_VERSION,
        "contractVersion": CONTRACT_VERSION,
        "valid": not errors,
        "municipalityCount": len(documents),
        "errorCount": len(errors),
        "errors": errors,
        "stateTotals": {key: state_active[key] for key in CUT_ORDER},
        "stateIndicators": {
            key: {
                "numerator": state_indicators[(key, "numerator")],
                "denominator": state_indicators[(key, "denominator")],
            }
            for key in INDICATOR_ORDER
        },
    }


def _list_segment(item: Any, index: int) -> str:
    if isinstance(item, dict) and "ano" in item:
        extras = [
            f"{key}={item[key]}"
            for key in ("dependencia", "localizacao")
            if key in item
        ]
        suffix = "," + ",".join(extras) if extras else ""
        return f"[ano={item['ano']}{suffix}]"
    return f"[{index}]"


def json_diff_paths(old: Any, new: Any, path: str = "") -> list[str]:
    if type(old) is not type(new):
        return [path or "/"]
    if isinstance(old, dict):
        paths: list[str] = []
        for key in sorted(old.keys() | new.keys()):
            child = f"{path}/{key}"
            if key not in old or key not in new:
                paths.append(child)
            else:
                paths.extend(json_diff_paths(old[key], new[key], child))
        return paths
    if isinstance(old, list):
        paths = []
        for index in range(max(len(old), len(new))):
            item = new[index] if index < len(new) else old[index]
            child = f"{path}/{_list_segment(item, index)}"
            if index >= len(old) or index >= len(new):
                paths.append(child)
            else:
                paths.extend(json_diff_paths(old[index], new[index], child))
        return paths
    return [] if old == new else [path or "/"]


_CONTRACT_PREFIX = "/blocos/rede_escolar/infraestrutura/"
_CONTRACT_FIELDS = (
    "contractVersion",
    "referenceYear",
    "availableYears",
    "universe",
    "indicatorDefinitions",
    "years",
)
_LEGACY_PATTERNS = (
    re.compile(r"^/blocos/rede_escolar/infraestrutura/series/internet/\[ano=2025\]/valor$"),
    re.compile(r"^/blocos/rede_escolar/infraestrutura/resumo_ultimo_ano/internet$"),
    re.compile(r"^/blocos/rede_escolar/infraestrutura/por_rede/\[ano=2025,dependencia=[^]]+\]/(?:escolas|perc_internet)$"),
    re.compile(r"^/blocos/rede_escolar/infraestrutura/por_localizacao/\[ano=2025,localizacao=[^]]+\]/(?:escolas|perc_internet)$"),
    re.compile(r"^/blocos/rede_escolar/series/internet/\[ano=2025\]/perc_internet$"),
    re.compile(r"^/blocos/rede_escolar/resumo_ultimo_ano/perc_internet$"),
)


def classify_diff_path(path: str) -> str:
    if any(path.startswith(_CONTRACT_PREFIX + field) for field in _CONTRACT_FIELDS):
        return "canonicalContract"
    if any(pattern.match(path) for pattern in _LEGACY_PATTERNS):
        return "internet2025"
    return "unexpected"


def compare_with_public(stage: Path, public_directory: Path) -> dict[str, Any]:
    staged_files = {path.name: path for path in (stage / "municipios").glob("*.json")}
    public_files = {path.name: path for path in public_directory.glob("*.json")}
    added = sorted(staged_files.keys() - public_files.keys())
    missing = sorted(public_files.keys() - staged_files.keys())
    changes = Counter()
    categories = Counter()
    unexpected: list[dict[str, str]] = []
    changed_internet = []
    unchanged_internet = []
    impacts = []
    for name in sorted(staged_files.keys() & public_files.keys()):
        old = json.loads(public_files[name].read_text(encoding="utf-8"))
        new = json.loads(staged_files[name].read_text(encoding="utf-8"))
        paths = json_diff_paths(old, new)
        for path in paths:
            changes[path] += 1
            category = classify_diff_path(path)
            categories[category] += 1
            if category == "unexpected":
                unexpected.append({"municipalityCode": name[:-5], "path": path})
        old_value = next(
            (
                row.get("valor")
                for row in old["blocos"]["rede_escolar"]["infraestrutura"]["series"]["internet"]
                if row.get("ano") == REFERENCE_YEAR
            ),
            None,
        )
        new_value = next(
            (
                row.get("valor")
                for row in new["blocos"]["rede_escolar"]["infraestrutura"]["series"]["internet"]
                if row.get("ano") == REFERENCE_YEAR
            ),
            None,
        )
        code = name[:-5]
        if old_value == new_value:
            unchanged_internet.append(code)
        else:
            changed_internet.append(code)
            impacts.append(
                {
                    "municipalityCode": code,
                    "municipality": new.get("municipio"),
                    "before": old_value,
                    "after": new_value,
                    "differencePercentagePoints": round(new_value - old_value, 1),
                }
            )
    impacts.sort(
        key=lambda row: (-row["differencePercentagePoints"], row["municipalityCode"])
    )
    return {
        "schemaVersion": SCHEMA_VERSION,
        "filesCompared": len(staged_files.keys() & public_files.keys()),
        "addedMunicipalities": [name[:-5] for name in added],
        "missingMunicipalities": [name[:-5] for name in missing],
        "changesByPath": dict(sorted(changes.items())),
        "changesByCategory": {
            key: categories[key]
            for key in ("canonicalContract", "internet2025", "unexpected")
        },
        "internetImpact": {
            "unchangedMunicipalityCount": len(unchanged_internet),
            "changedMunicipalityCount": len(changed_internet),
            "reductionCount": sum(
                row["differencePercentagePoints"] < 0 for row in impacts
            ),
            "maximumDifferencePercentagePoints": (
                impacts[0]["differencePercentagePoints"] if impacts else 0
            ),
            "highestImpactMunicipalities": impacts[:10],
        },
        "unexpectedChangeCount": len(unexpected),
        "unexpectedChanges": unexpected,
    }


def compare_trees(first: Path, second: Path) -> dict[str, Any]:
    first_files = {
        path.relative_to(first).as_posix(): path for path in first.rglob("*") if path.is_file()
    }
    second_files = {
        path.relative_to(second).as_posix(): path for path in second.rglob("*") if path.is_file()
    }
    names_equal = set(first_files) == set(second_files)
    mismatches = [
        name
        for name in sorted(set(first_files) & set(second_files))
        if first_files[name].read_bytes() != second_files[name].read_bytes()
    ]
    return {
        "identical": names_equal and not mismatches,
        "fileNamesIdentical": names_equal,
        "fileCount": len(first_files),
        "byteMismatches": mismatches,
        "firstTreeHash": tree_hash(first),
        "secondTreeHash": tree_hash(second),
    }


def replace_directory_atomically(source: Path, destination: Path) -> None:
    """Promoção futura de conjunto completo; não é chamada pela INFRA-2."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    backup = destination.with_name(destination.name + ".previous")
    if backup.exists():
        shutil.rmtree(backup)


def promote_municipal_documents(
    stage: Path,
    public_root: Path,
    official_codes: Iterable[str],
) -> dict[str, Any]:
    """Promove somente os documentos municipais, com rollback integral.

    A função não recalcula dados. Cada destino é substituído atomicamente e
    comparado ao staging antes de avançar. Os backups permanecem fora de
    ``public/data`` e só são removidos após a validação completa.
    """
    stage = stage.resolve()
    public_root = public_root.resolve()
    stage_municipalities = stage / "municipios"
    public_municipalities = public_root / "municipios"
    codes = tuple(sorted(str(code) for code in official_codes))
    staged_files = sorted(stage_municipalities.glob("*.json"))
    if [path.stem for path in staged_files] != list(codes):
        raise ValueError("O staging não corresponde ao conjunto municipal oficial.")

    expected_diff = json.loads((stage / "diff-report.json").read_text(encoding="utf-8"))
    current_diff = compare_with_public(stage, public_municipalities)
    if current_diff != expected_diff:
        raise ValueError("A base pública divergiu após a geração do staging.")

    backup_root = Path(
        tempfile.mkdtemp(prefix=".infra3-promotion-backup-", dir=stage.parent)
    )
    promoted: list[str] = []
    try:
        for source in staged_files:
            destination = public_municipalities / source.name
            backup = backup_root / source.name
            shutil.copy2(destination, backup)
            temporary = destination.with_suffix(destination.suffix + ".infra3.tmp")
            shutil.copyfile(source, temporary)
            os.replace(temporary, destination)
            promoted.append(source.stem)

            if destination.read_bytes() != source.read_bytes():
                raise ValueError(f"{source.name}: conteúdo promovido divergente")
            payload = json.loads(destination.read_text(encoding="utf-8"))
            if str(payload.get("id_municipio")) != source.stem:
                raise ValueError(f"{source.name}: id_municipio inválido após promoção")

        if any(
            (public_municipalities / source.name).read_bytes() != source.read_bytes()
            for source in staged_files
        ):
            raise ValueError("O conjunto promovido não é idêntico ao staging.")

        validation = validate_stage(public_root, codes)
        post_diff = compare_with_public(stage, public_municipalities)
        if not validation["valid"]:
            raise ValueError(f"Validação pós-promoção falhou: {validation['errors'][:5]}")
        if (
            post_diff["unexpectedChangeCount"] != 0
            or post_diff["addedMunicipalities"]
            or post_diff["missingMunicipalities"]
            or post_diff["changesByPath"]
        ):
            raise ValueError("O conteúdo público não ficou idêntico ao staging.")

        result = {
            "promotedFileCount": len(promoted),
            "contentHash": municipality_content_hash(public_root),
            "validation": validation,
            "postPromotionDiff": post_diff,
        }
    except Exception:
        for code in reversed(promoted):
            backup = backup_root / f"{code}.json"
            destination = public_municipalities / f"{code}.json"
            temporary = destination.with_suffix(destination.suffix + ".rollback.tmp")
            shutil.copyfile(backup, temporary)
            os.replace(temporary, destination)
        raise
    else:
        shutil.rmtree(backup_root)
        return result
    if destination.exists():
        os.replace(destination, backup)
    try:
        try:
            os.replace(source, destination)
        except PermissionError:
            if destination.exists():
                raise
            shutil.copytree(source, destination)
            shutil.rmtree(source)
    except Exception:
        if backup.exists() and not destination.exists():
            os.replace(backup, destination)
        raise
    if backup.exists():
        shutil.rmtree(backup)
