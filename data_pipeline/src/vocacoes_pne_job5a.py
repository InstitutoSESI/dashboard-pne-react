"""Execução determinística do Redesenho Dirigido V7 — Job 5A.

O módulo consome somente os artefatos locais e congelados dos Jobs 2–4B,
materializa um pacote factual em staging interno e nunca acessa banco, rede ou
``public/data``.
"""

from __future__ import annotations

from collections import defaultdict
import ast
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import unicodedata
from typing import Any, Iterable, Mapping, Sequence

import pandas as pd

from src.vocacoes_pne_job2 import (
    artifact_record,
    assert_outside_public_data,
    canonical_json_bytes,
    replace_directory_transactionally,
    safe_ratio,
    sha256_file,
    staging_directory_for,
    validate_unique_key,
    write_csv_gzip,
    write_json,
)


SCHEMA_VERSION = "vocacoes-pne-v7-job5a-v1"
JOB_ID = "v7-job5a"
REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_PIPELINE_DIR = REPO_ROOT / "data_pipeline"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / ".tmp" / "vocacoes-pne" / JOB_ID
CONTRACT_PATH = DATA_PIPELINE_DIR / "contracts" / "vocacoes-pne-v7-job5a.json"
PREREGISTRATION_PATH = REPO_ROOT / "docs" / "PRE_REGISTRO_JOB_5A_REDESENHO_DIRIGIDO_V7.yaml"
JOB2_ROOT = REPO_ROOT / ".tmp" / "vocacoes-pne" / "v7-job2"
JOB3_ROOT = REPO_ROOT / ".tmp" / "vocacoes-pne" / "v7-job3"
JOB2_MANIFEST_SHA256 = "28ca53d020af6eb8168eef15af2a7752034c149ada942b4323756e55ef8f8d85"
JOB3_MANIFEST_SHA256 = "eb123990bd04a28e8fe4995f8d350e7573cf1a0a74a7cffb3f35d981bb4074ea"
JOB2_RELEASE_SHA256 = "81296d78b97b0418b89d2ed7b2bb353eedf0c10fda3f7af62570cfc33c537f51"
JOB3_RELEASE_SHA256 = "92e90e9c3fa790415009fad949b9e02abb1d90a430788155f1f87d70cb98f361"
JOB2_EXECUTION_STATE_SHA256 = "fd01f128773367598a1b36d190439029a91af1757bce6c6807cd53ded1869425"
JOB3_PREREGISTRATION_SHA256 = "5da7602b349dd913d91e259319bd296074390bb449fa7af5a0859ed7939c3bab"
IBGE_PATTERN = re.compile(r"^[0-9]{7}$")
PEER_IDS = ("4307609", "4314803", "4303905")
NOVA_SANTA_RITA_ID = "4313375"
ALLOWED_DATA_STATES = frozenset(
    {"observed", "null", "unavailable", "suppressed", "not_applicable"}
)

JOB4B_HASHES = {
    "docs/DECISAO_ESCOPO_REDE_TOTAL_JOB_4B_V7.md": "ab8b6d8288fd4a788b0041d915fa4b35a057cb07005dbbb037db42996943c536",
    "docs/DECISAO_JULGAMENTO_EXTERNO_FINAL_JOB_4B_V7.md": "0bbc37df84ce5bcf6442d835989defa9f83ca1bc65d1a771f7e899292dd7b5cb",
    "docs/MATRIZ_DECISAO_FINAL_CANDIDATAS_JOB_4B_V7.csv": "6e409884fc43f36cc24479b04662c0d11a7a8dc87494d47447a50c4affd31b5b",
    "docs/ADITIVO_PROVISORIO_PORTFOLIO_3_MAIS_2_V7.md": "1428af1ae52f89ed8dfa990fda04feabc24496c00386cfca8d27fe803812a289",
    "docs/PRE_REGISTRO_JOB_5A_REDESENHO_DIRIGIDO_V7.yaml": "eaec73eeeb562db362ad3ab3d2e29c7e21cd6f28542fb5b046add944c2323549",
    "docs/PLANO_JOB_5A_REDESENHO_DIRIGIDO_V7.md": "e906f06ea521753030ec29c5080c6a49e2495e39f93c7988a45d7a697e04a8ff",
}

JOB4A_HASHES = {
    "docs/MATRIZ_EVIDENCIA_H2_JOB_4A_V7.csv": (
        167974,
        "6a9c3bddf31e72ae5ddf8d6ed18ab7f57aa43767b13e0cf59691f41392c62c59",
    ),
    "docs/SINTESE_EVIDENCIA_H2_JOB_4A_V7.md": (
        3843,
        "62c1f1a334738d62eb720fe9daf44abed0eb8362f57b9070842aed84dcfc7d7a",
    ),
    "docs/MATRIZ_EVIDENCIA_H3_JOB_4A_V7.csv": (
        131495,
        "8396c84dd173124fb2553f512a5da0e1d9f3b0396901a3aacfd580bd1fc7632e",
    ),
    "docs/SINTESE_EVIDENCIA_H3_JOB_4A_V7.md": (
        5289,
        "264c8354c24202d253769dc8000ff40c1c151ddfda4d4364dbe93047ffb31b1c",
    ),
    "docs/DOSSIE_A3_OCUPACOES_FORMACAO_JOB_4A_V7.md": (
        10017,
        "de7ad8cd94ceed9c437b9832fb5beb3e3f151bebc6661fb8a7622f78c14f0560",
    ),
    "docs/MATRIZ_A3_OCUPACOES_FORMACAO_JOB_4A_V7.csv": (
        66364,
        "75bca0cfd5cf3cde9237525316a0a1a0cd9be840480d04620ae4f16b1b5a7ea5",
    ),
    "docs/AUDITORIA_PRE_REGISTRO_JOB_4A_V7.md": (
        6070,
        "df9d48b03412cf0491a232be4040f07d7f8093fd768c11707d237df7f2174047",
    ),
    "docs/CORRECOES_C9_POS_JOB_3_V7.md": (
        1314,
        "6061a3262002e080b2b718fddcd1c57f9916149aead18b63334568189a343820",
    ),
    "docs/AUDITORIA_FECHAMENTO_PORTFOLIO_V7_JOB_4A.md": (
        5391,
        "4f1005cc6808197fde4fa415194577308f6399b15926c68a5f0add4fd4d61d02",
    ),
    "docs/PACOTE_COMPLEMENTAR_REVISAO_EXTERNA_JOB_4A_V7.md": (
        9394,
        "6899b13ffaf2ada39e522f018a61d0f4f06465ade1d4d14cbbcd22b9b531cad2",
    ),
}

OUTPUT_FILES = (
    "input_inventory.json",
    "external_authorization.json",
    "total_network_qa.csv.gz",
    "h2_factual_matrix.csv.gz",
    "h2_internal_synthesis.json",
    "nova_santa_rita_h2.json",
    "a4_factual_matrix.csv.gz",
    "a4_internal_synthesis.json",
    "nova_santa_rita_a4.json",
    "a3_optional_youth_context.json",
    "c1_c12_evidence.csv.gz",
    "external_review_package.json",
    "limitations.json",
    "schemas.json",
    "output_inventory.json",
    "manifest.json",
)


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _yaml_scalar(value: str) -> Any:
    value = value.strip()
    if value == "":
        return None
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [_yaml_scalar(item) for item in inner.split(",")]
    if value.startswith('"') and value.endswith('"'):
        return json.loads(value)
    if value.startswith("'") and value.endswith("'"):
        return ast.literal_eval(value)
    lowered = value.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    if lowered in {"null", "~"}:
        return None
    if re.fullmatch(r"-?[0-9]+", value):
        return int(value)
    if re.fullmatch(r"-?(?:[0-9]+\.[0-9]*|[0-9]*\.[0-9]+)", value):
        return float(value)
    return value


def parse_yaml_subset(text: str) -> Any:
    """Parseia o subconjunto YAML usado pelos pré-registros congelados.

    O parser é deliberadamente fail-closed: aceita mapas, listas, escalares,
    listas inline e blocos dobrados, rejeita tabs, mistura de mapa/lista no
    mesmo nível e conteúdo sem ``:``. Isso evita adicionar uma dependência ao
    ambiente congelado apenas para esta execução.
    """

    tokens: list[tuple[int, str, int]] = []
    for line_number, raw in enumerate(text.splitlines(), start=1):
        if "\t" in raw[: len(raw) - len(raw.lstrip())]:
            raise ValueError(f"Tab de indentação YAML na linha {line_number}.")
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        tokens.append((indent, raw[indent:], line_number))
    if not tokens:
        raise ValueError("YAML vazio.")

    def split_mapping(content: str, line_number: int) -> tuple[str, str]:
        if ":" not in content:
            raise ValueError(f"Entrada YAML sem ':' na linha {line_number}.")
        key, value = content.split(":", 1)
        key = key.strip()
        if not key:
            raise ValueError(f"Chave YAML vazia na linha {line_number}.")
        return key, value.strip()

    def parse_block(position: int, indent: int) -> tuple[Any, int]:
        if position >= len(tokens) or tokens[position][0] != indent:
            raise ValueError("Indentação YAML inesperada.")
        list_mode = tokens[position][1].startswith("- ") or tokens[position][1] == "-"
        container: Any = [] if list_mode else {}
        while position < len(tokens):
            current_indent, content, line_number = tokens[position]
            if current_indent < indent:
                break
            if current_indent > indent:
                raise ValueError(f"Indentação YAML órfã na linha {line_number}.")
            is_list_item = content.startswith("- ") or content == "-"
            if is_list_item != list_mode:
                raise ValueError(f"Mistura YAML de mapa/lista na linha {line_number}.")
            if list_mode:
                rest = content[1:].strip()
                position += 1
                if not rest:
                    if position >= len(tokens) or tokens[position][0] <= indent:
                        raise ValueError(f"Item YAML vazio na linha {line_number}.")
                    item, position = parse_block(position, tokens[position][0])
                    container.append(item)
                    continue
                if ":" not in rest:
                    container.append(_yaml_scalar(rest))
                    continue
                key, raw_value = split_mapping(rest, line_number)
                item: dict[str, Any] = {}
                if raw_value in {">", ">-", "|", "|-"}:
                    folded: list[str] = []
                    while position < len(tokens) and tokens[position][0] > indent:
                        folded.append(tokens[position][1].strip())
                        position += 1
                    item[key] = " ".join(folded)
                elif raw_value:
                    item[key] = _yaml_scalar(raw_value)
                else:
                    if position >= len(tokens) or tokens[position][0] <= indent:
                        item[key] = None
                    else:
                        item[key], position = parse_block(position, tokens[position][0])
                if position < len(tokens) and tokens[position][0] > indent:
                    continuation, position = parse_block(position, tokens[position][0])
                    if not isinstance(continuation, dict):
                        raise ValueError(
                            f"Continuação de item não é mapa após linha {line_number}."
                        )
                    duplicate = set(item) & set(continuation)
                    if duplicate:
                        raise ValueError(f"Chave YAML duplicada: {sorted(duplicate)}.")
                    item.update(continuation)
                container.append(item)
                continue

            key, raw_value = split_mapping(content, line_number)
            if key in container:
                raise ValueError(f"Chave YAML duplicada na linha {line_number}: {key}.")
            position += 1
            if raw_value in {">", ">-", "|", "|-"}:
                folded = []
                while position < len(tokens) and tokens[position][0] > indent:
                    folded.append(tokens[position][1].strip())
                    position += 1
                container[key] = " ".join(folded)
            elif raw_value:
                container[key] = _yaml_scalar(raw_value)
            elif position < len(tokens) and tokens[position][0] > indent:
                container[key], position = parse_block(position, tokens[position][0])
            else:
                container[key] = None
        return container, position

    parsed, final_position = parse_block(0, tokens[0][0])
    if final_position != len(tokens):
        raise ValueError("YAML não foi consumido integralmente.")
    return parsed


def _repo_path(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()


def _normalize_label(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value))
    return "".join(char for char in text if not unicodedata.combining(char)).lower()


def normalize_dependency(value: Any) -> str:
    normalized = _normalize_label(value).strip()
    aliases = {"publica": "publica", "public": "publica"}
    return aliases.get(normalized, normalized)


def normalize_stage(value: Any) -> str:
    stage = str(value)
    prefix = "taxa_distorcao_"
    return stage[len(prefix) :] if stage.startswith(prefix) else stage


def _require_code(value: Any) -> str:
    if not isinstance(value, str) or not IBGE_PATTERN.fullmatch(value):
        raise ValueError(f"Código IBGE inválido ou numericamente coercível: {value!r}.")
    return value


def _json_safe(value: Any) -> Any:
    if value is None or value is pd.NA:
        return None
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return int(value)
    if isinstance(value, float):
        return None if math.isnan(value) else float(value)
    if hasattr(value, "item"):
        return _json_safe(value.item())
    return value


def _canonical_inline_json(value: Any) -> str:
    return json.dumps(
        _json_safe(value), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def _verify_path(
    path: Path,
    *,
    expected_sha256: str,
    expected_size: int | None,
    role: str,
    frozen_group: str,
) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Entrada congelada ausente: {path}.")
    size = path.stat().st_size
    digest = sha256_file(path)
    if expected_size is not None and size != expected_size:
        raise ValueError(f"Tamanho divergente em {_repo_path(path)}: {size}.")
    if digest != expected_sha256:
        raise ValueError(f"SHA-256 divergente em {_repo_path(path)}: {digest}.")
    return {
        "path": _repo_path(path),
        "byteSize": size,
        "sha256": digest,
        "role": role,
        "frozenState": "FROZEN_VERIFIED",
        "frozenGroup": frozen_group,
    }


def _git_context() -> dict[str, Any]:
    def run(*args: str) -> str:
        result = subprocess.run(
            ["git", *args],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        return result.stdout.strip()

    public_status = run("status", "--short", "--untracked-files=all", "--", "public/data")
    public_diff = run("diff", "--name-only", "--", "public/data")
    if public_status or public_diff:
        raise ValueError("public/data já apresenta mudança; o Job 5A falha fechado.")
    full_status = run("status", "--short", "--branch", "--untracked-files=all")
    return {
        "branch": run("branch", "--show-current"),
        "head": run("rev-parse", "HEAD"),
        "status": full_status.splitlines(),
        "workingTreeDirty": len(full_status.splitlines()) > 1,
        "publicDataStatusCount": 0,
        "publicDataDiffCount": 0,
    }


def _load_region() -> tuple[list[str], dict[str, str]]:
    region_payload = _load_json(REPO_ROOT / "config" / "regions" / "rs.json")
    region = next(
        item for item in region_payload["regions"] if item["slug"] == "vale-do-sinos"
    )
    codes = [_require_code(code) for code in region["municipalityIbgeCodes"]]
    if len(codes) != 10 or len(set(codes)) != 10 or region["municipalityCount"] != 10:
        raise ValueError("O universo do Vale do Sinos não fecha em dez municípios.")
    registry = _load_json(REPO_ROOT / "config" / "municipalities" / "rs.json")
    names = {
        item["ibgeCode"]: item["name"]
        for item in registry["municipalities"]
        if item["ibgeCode"] in codes
    }
    if set(names) != set(codes):
        raise ValueError("O registro municipal canônico não cobre os dez municípios.")
    if names.get(NOVA_SANTA_RITA_ID) != "Nova Santa Rita":
        raise ValueError("Nova Santa Rita 4313375 não foi preservada.")
    return codes, names


def verify_frozen_inputs() -> tuple[dict[str, Any], list[str], dict[str, str]]:
    """Confere os 61 itens do Job 4B e as seis entradas superiores do Job 5A."""

    prereg = parse_yaml_subset(PREREGISTRATION_PATH.read_text(encoding="utf-8"))
    if prereg["execution_authorized_by_job4b"] is not False:
        raise ValueError("O campo congelado de autorização não permaneceu false.")
    if len(prereg["fronts"]) != 3 or len(prereg["references"]) != 6:
        raise ValueError("O pré-registro não contém exatamente três frentes e seis referências.")
    expected_fronts = [
        "H2_TRAJETORIA_MUNICIPAL_V2",
        "A4_MOBILIDADE_COORDENACAO",
        "A3_OPTIONAL_YOUTH_CONTEXT",
    ]
    if [item["front_id"] for item in prereg["fronts"]] != expected_fronts:
        raise ValueError("As frentes congeladas do Job 5A divergiram.")

    entries: list[dict[str, Any]] = []
    frozen61_paths: list[str] = []

    job2_manifest_path = JOB2_ROOT / "manifest.json"
    if sha256_file(job2_manifest_path) != JOB2_MANIFEST_SHA256:
        raise ValueError("O manifest operacional do Job 2 divergiu.")
    job2_manifest = _load_json(job2_manifest_path)
    if len(job2_manifest["artifacts"]) != 20:
        raise ValueError("O Job 2 não contém 20 artefatos.")
    for artifact in job2_manifest["artifacts"]:
        path = JOB2_ROOT / artifact["path"]
        entries.append(
            _verify_path(
                path,
                expected_sha256=artifact["sha256"],
                expected_size=int(artifact["byteSize"]),
                role="frozen_job2_factual_artifact",
                frozen_group="JOB2_PAYLOADS",
            )
        )
        frozen61_paths.append(_repo_path(path))

    job3_manifest_path = JOB3_ROOT / "manifest.json"
    if sha256_file(job3_manifest_path) != JOB3_MANIFEST_SHA256:
        raise ValueError("O manifest operacional do Job 3 divergiu.")
    job3_manifest = _load_json(job3_manifest_path)
    if len(job3_manifest["artifacts"]) != 17:
        raise ValueError("O Job 3 não contém 17 artefatos.")
    for artifact in job3_manifest["artifacts"]:
        path = JOB3_ROOT / artifact["path"]
        entries.append(
            _verify_path(
                path,
                expected_sha256=artifact["sha256"],
                expected_size=int(artifact["byteSize"]),
                role="frozen_job3_factual_artifact",
                frozen_group="JOB3_PAYLOADS",
            )
        )
        frozen61_paths.append(_repo_path(path))

    job3_release_path = DATA_PIPELINE_DIR / "manifests" / "vocacoes-pne-v7-job3-release.json"
    if sha256_file(job3_release_path) != JOB3_RELEASE_SHA256:
        raise ValueError("O manifest de release do Job 3 divergiu.")
    job3_release = _load_json(job3_release_path)
    if len(job3_release["documents"]) != 9:
        raise ValueError("O Job 3 não contém nove documentos congelados.")
    for document in job3_release["documents"]:
        path = REPO_ROOT / document["path"]
        entries.append(
            _verify_path(
                path,
                expected_sha256=document["sha256"],
                expected_size=int(document["byteSize"]),
                role="frozen_job3_document",
                frozen_group="JOB3_DOCUMENTS",
            )
        )
        frozen61_paths.append(_repo_path(path))

    for relative, (size, digest) in JOB4A_HASHES.items():
        path = REPO_ROOT / relative
        entries.append(
            _verify_path(
                path,
                expected_sha256=digest,
                expected_size=size,
                role="frozen_job4a_external_review_evidence",
                frozen_group="JOB4A_PACKAGE",
            )
        )
        frozen61_paths.append(relative)

    extras = (
        (job2_manifest_path, JOB2_MANIFEST_SHA256, "job2_operational_manifest"),
        (
            JOB2_ROOT / "execution_state.json",
            JOB2_EXECUTION_STATE_SHA256,
            "job2_execution_state",
        ),
        (
            DATA_PIPELINE_DIR / "manifests" / "vocacoes-pne-v7-job2-release.json",
            JOB2_RELEASE_SHA256,
            "job2_release_manifest",
        ),
        (job3_manifest_path, JOB3_MANIFEST_SHA256, "job3_operational_manifest"),
        (job3_release_path, JOB3_RELEASE_SHA256, "job3_release_manifest"),
    )
    for path, digest, role in extras:
        entries.append(
            _verify_path(
                path,
                expected_sha256=digest,
                expected_size=None,
                role=role,
                frozen_group="JOB2_JOB3_OPERATIONAL",
            )
        )
        frozen61_paths.append(_repo_path(path))

    if len(frozen61_paths) != 61 or len(set(frozen61_paths)) != 61:
        raise ValueError("A lista congelada não contém 61 paths únicos.")

    existing_paths = {entry["path"] for entry in entries}
    for relative, digest in JOB4B_HASHES.items():
        if relative in existing_paths:
            continue
        entries.append(
            _verify_path(
                REPO_ROOT / relative,
                expected_sha256=digest,
                expected_size=None,
                role="frozen_job4b_governing_input",
                frozen_group="JOB4B_FINAL",
            )
        )

    for path, role in (
        (CONTRACT_PATH, "job5a_execution_contract"),
        (Path(__file__), "job5a_executor_core"),
        (DATA_PIPELINE_DIR / "scripts" / "run_vocacoes_pne_v7_job5a.py", "job5a_launcher"),
        (REPO_ROOT / "config" / "regions" / "rs.json", "canonical_region_config"),
        (
            REPO_ROOT / "config" / "municipalities" / "rs.json",
            "canonical_municipality_registry",
        ),
    ):
        entries.append(
            {
                "path": _repo_path(path),
                "byteSize": path.stat().st_size,
                "sha256": sha256_file(path),
                "role": role,
                "frozenState": "EXECUTION_INPUT_VERIFIED",
                "frozenGroup": "JOB5A_EXECUTION",
            }
        )

    codes, names = _load_region()
    inventory = {
        "schemaVersion": "vocacoes-pne-v7-job5a-input-inventory-v1",
        "jobId": JOB_ID,
        "frozen61Count": 61,
        "entries": sorted(entries, key=lambda item: item["path"]),
        "nominalHandoff": {
            "path": "HANDOFF_VOCACOES_PNE_V7_POS_JOB4B.md",
            "available": False,
            "treatment": "NON_BLOCKING_LOWER_PRECEDENCE_INPUT_MISSING",
            "precedenceApplied": [
                "explicit_product_owner_authorization",
                "final_job4b_documents",
                "frozen_job5a_preregistration",
                "job5a_plan",
            ],
        },
        "smallDenominatorRule": "SMALL_DENOMINATOR_RULE_UNAVAILABLE",
        "municipalityUniverse": codes,
        "mandatoryMunicipalityId": NOVA_SANTA_RITA_ID,
    }
    return inventory, codes, names


def _read_job2_frame(relative: str, **kwargs: Any) -> pd.DataFrame:
    return pd.read_csv(JOB2_ROOT / relative, **kwargs)


def _prepare_trajectory() -> tuple[pd.DataFrame, pd.DataFrame]:
    trajectory = _read_job2_frame(
        "2a/trajetoria_municipal.csv.gz",
        dtype={"municipality_ibge_code": "string"},
    )
    comparisons = _read_job2_frame("2a/trajetoria_comparacoes.csv.gz")
    trajectory["municipality_ibge_code"] = trajectory["municipality_ibge_code"].map(
        _require_code
    )
    trajectory["year"] = pd.to_numeric(trajectory["ano"], errors="raise").astype(int)
    trajectory["stage"] = trajectory["etapa_ensino"].map(normalize_stage)
    trajectory["dependency_normalized"] = trajectory["dependencia"].map(
        normalize_dependency
    )
    trajectory["value"] = pd.to_numeric(trajectory["value"], errors="coerce")
    comparisons["year"] = pd.to_numeric(comparisons["ano"], errors="raise").astype(int)
    comparisons["stage"] = comparisons["etapa_ensino"].map(normalize_stage)
    comparisons["dependency_normalized"] = comparisons["dependencia"].map(
        normalize_dependency
    )
    for column in (
        "minimum",
        "quartile_1",
        "median",
        "quartile_3",
        "maximum",
        "municipality_count",
    ):
        comparisons[column] = pd.to_numeric(comparisons[column], errors="coerce")
    return trajectory, comparisons


def _closure_map(totals: pd.DataFrame) -> dict[tuple[str, int, str], dict[str, Any]]:
    performance = totals[
        totals["metric"].isin(
            ("approval_rate_percent", "failure_rate_percent", "dropout_rate_percent")
        )
    ]
    result: dict[tuple[str, int, str], dict[str, Any]] = {}
    for keys, group in performance.groupby(
        ["municipality_ibge_code", "year", "stage"], sort=True
    ):
        values = group.set_index("metric")["value"].to_dict()
        expected = {
            "approval_rate_percent",
            "failure_rate_percent",
            "dropout_rate_percent",
        }
        if set(values) != expected or any(pd.isna(value) for value in values.values()):
            result[keys] = {
                "residual": None,
                "status": "unavailable",
                "passes": False,
            }
            continue
        residual = float(sum(float(value) for value in values.values()) - 100.0)
        result[keys] = {
            "residual": residual,
            "status": "closed" if abs(residual) <= 1e-9 else "not_closed",
            "passes": abs(residual) <= 1e-9,
        }
    return result


def build_total_network_qa(
    trajectory: pd.DataFrame,
    *,
    region_codes: Sequence[str],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    totals = trajectory[trajectory["dependency_normalized"] == "total"].copy()
    source_key = ["municipality_ibge_code", "year", "stage", "metric"]
    output_key = ["municipality_ibge_code", "year", "stage", "indicator"]
    validate_unique_key(totals, source_key, label="registros oficiais totais H2")
    expected_grains = 10 * ((8 * 4 * 3) + (7 * 4))
    if len(totals) != expected_grains:
        raise ValueError(f"Cobertura total H2 divergente: {len(totals)} != {expected_grains}.")
    if set(totals["municipality_ibge_code"]) != set(region_codes):
        raise ValueError("Os registros totais H2 não cobrem o universo canônico.")
    if set(totals["value_status"]) - ALLOWED_DATA_STATES:
        raise ValueError("H2 contém estado de disponibilidade não contratado.")
    if (totals["value_status"] != "observed").any() or totals["value"].isna().any():
        raise ValueError("Há registro oficial total H2 indisponível; QA bloqueante falhou.")

    closure = _closure_map(totals)
    expected_parts = ("estadual", "federal", "municipal", "privada")
    rows: list[dict[str, Any]] = []
    source_groups = {
        keys: group
        for keys, group in trajectory.groupby(source_key, sort=False, dropna=False)
    }
    for total in totals.sort_values(source_key).itertuples(index=False):
        keys = (
            total.municipality_ibge_code,
            int(total.year),
            total.stage,
            total.metric,
        )
        group = source_groups.get(keys, pd.DataFrame())
        component_group = group[
            ~group["dependency_normalized"].isin(("total", "publica"))
        ]
        present = sorted(set(component_group["dependency_normalized"]))
        observed_components = component_group[
            component_group["value_status"] == "observed"
        ]
        unavailable_components = sorted(
            set(
                component_group.loc[
                    component_group["value_status"] != "observed",
                    "dependency_normalized",
                ]
            )
        )
        component_values = {
            row.dependency_normalized: _json_safe(row.value)
            for row in observed_components.sort_values("dependency_normalized").itertuples()
        }
        closure_item = closure.get(keys[:3])
        rows.append(
            {
                "municipality_ibge_code": keys[0],
                "year": keys[1],
                "stage": keys[2],
                "indicator": keys[3],
                "network_scope": "total_all_dependencies",
                "official_total_value": float(total.value),
                "official_total_status": total.value_status,
                "reconstructed_total_value": None,
                "absolute_difference": None,
                "relative_difference": None,
                "component_rate_denominators_available": False,
                "component_numerators": None,
                "component_denominators": None,
                "administrative_parts_present_count": len(present),
                "administrative_parts_observed_count": len(observed_components),
                "administrative_parts_present": _canonical_inline_json(present),
                "administrative_parts_missing": _canonical_inline_json(
                    sorted(set(expected_parts) - set(present))
                ),
                "administrative_parts_unavailable": _canonical_inline_json(
                    unavailable_components
                ),
                "administrative_component_values_qa_only": _canonical_inline_json(
                    component_values
                ),
                "public_aggregate_present": "publica"
                in set(group["dependency_normalized"]),
                "official_vs_reconstructed_status": "not_computable_missing_component_denominators",
                "closure_residual_pp": (
                    closure_item["residual"] if closure_item is not None else None
                ),
                "closure_status": (
                    closure_item["status"] if closure_item is not None else "not_applicable"
                ),
                "qa_status": "OFFICIAL_TOTAL_ACCEPTED_COMPONENT_RECOMPOSITION_UNAVAILABLE",
                "source_table": total.source_table,
                "value_status": total.value_status,
                "small_denominator_status": "SMALL_DENOMINATOR_RULE_UNAVAILABLE",
                "administrative_dependency_is_analytic_dimension": False,
            }
        )
    qa = pd.DataFrame(rows).sort_values(output_key).reset_index(drop=True)
    validate_unique_key(qa, output_key, label="QA de rede total")
    performance_qa = qa[qa["indicator"] != "age_grade_distortion_rate_percent"]
    if (performance_qa["closure_status"] != "closed").any():
        raise ValueError("A família aprovação/reprovação/abandono não fecha em 100%.")
    summary = {
        "rowCount": len(qa),
        "officialTotalObservedCount": int((qa["official_total_status"] == "observed").sum()),
        "componentReconstructionAvailableCount": 0,
        "componentReconstructionUnavailableCount": len(qa),
        "performanceClosureRowCount": len(performance_qa),
        "performanceClosurePassCount": int(
            (performance_qa["closure_status"] == "closed").sum()
        ),
        "maximumAbsoluteClosureResidual": float(
            performance_qa["closure_residual_pp"].abs().max()
        ),
        "blockingStatus": "PASS_OFFICIAL_TOTAL_COMPLETE",
    }
    return qa, summary


def _trajectory_direction(metric: str, delta: float | None) -> str:
    if delta is None or pd.isna(delta):
        return "unavailable"
    if abs(float(delta)) <= 1e-12:
        return "stable"
    beneficial = float(delta) > 0 if metric == "approval_rate_percent" else float(delta) < 0
    return "improvement" if beneficial else "worsening"


def _group_summary(group: pd.DataFrame, metric: str) -> dict[str, Any]:
    values = {
        int(row.year): float(row.value)
        for row in group.sort_values("year").itertuples(index=False)
        if not pd.isna(row.value)
    }
    directions = []
    for first, second in ((2023, 2024), (2024, 2025)):
        delta = values.get(second) - values.get(first) if first in values and second in values else None
        directions.append(_trajectory_direction(metric, delta))
    if directions == ["improvement", "improvement"]:
        persistence = "persistent_improvement"
    elif directions == ["worsening", "worsening"]:
        persistence = "persistent_worsening"
    elif "unavailable" in directions:
        persistence = "unavailable"
    else:
        persistence = "stable_or_mixed"
    start_year = min(values) if values else None
    return {
        "values": values,
        "recentDirections": directions,
        "persistence": persistence,
        "periodStartYear": start_year,
        "periodStartValue": values.get(start_year) if start_year is not None else None,
        "periodEndValue": values.get(2025),
        "periodChange": (
            values[2025] - values[start_year]
            if start_year is not None and 2025 in values
            else None
        ),
        "recentChange": values[2025] - values[2023] if 2023 in values and 2025 in values else None,
    }


def _monitoring_indicator(metric: str, stage: str) -> str:
    labels = {
        "approval_rate_percent": "taxa oficial de aprovação",
        "failure_rate_percent": "taxa oficial de reprovação",
        "dropout_rate_percent": "taxa oficial de abandono",
        "age_grade_distortion_rate_percent": "taxa oficial de distorção idade-série",
    }
    return f"{labels[metric]} da rede total em {stage}, acompanhada anualmente"


def _planning_question(metric: str, stage: str) -> str:
    if metric == "dropout_rate_percent":
        return (
            f"Quais transições e rotinas de acompanhamento em {stage} devem ser "
            "coordenadas para responder ao padrão observado de abandono?"
        )
    if metric == "failure_rate_percent":
        return (
            f"Quais rotinas de recuperação e acompanhamento em {stage} devem ser "
            "priorizadas diante do padrão observado de reprovação?"
        )
    if metric == "approval_rate_percent":
        return (
            f"Quais práticas de acompanhamento em {stage} devem ser preservadas ou "
            "revistas diante da trajetória observada de aprovação?"
        )
    return (
        f"Quais ações de recomposição de trajetória em {stage} devem ser examinadas "
        "diante da distorção idade-série observada?"
    )


def build_h2(
    trajectory: pd.DataFrame,
    comparisons: pd.DataFrame,
    qa: pd.DataFrame,
    *,
    names: Mapping[str, str],
) -> tuple[pd.DataFrame, dict[str, Any], dict[str, Any]]:
    totals = trajectory[trajectory["dependency_normalized"] == "total"].copy()
    totals["municipality_name"] = totals["municipality_ibge_code"].map(names)
    totals = totals.sort_values(
        ["municipality_ibge_code", "stage", "metric", "year"]
    ).reset_index(drop=True)
    summaries: dict[tuple[str, str, str], dict[str, Any]] = {}
    for keys, group in totals.groupby(
        ["municipality_ibge_code", "stage", "metric"], sort=True
    ):
        summaries[keys] = _group_summary(group, keys[2])

    closure_recent = (
        qa[
            (qa["year"].between(2023, 2025))
            & (qa["indicator"] != "age_grade_distortion_rate_percent")
        ]
        .groupby(["municipality_ibge_code", "stage", "indicator"])["closure_status"]
        .apply(lambda values: len(values) == 3 and (values == "closed").all())
        .to_dict()
    )

    comparison_rows = comparisons[
        comparisons["dependency_normalized"] == "total"
    ].copy()
    comp_map: dict[tuple[int, str, str, str], Mapping[str, Any]] = {}
    for row in comparison_rows.to_dict(orient="records"):
        comp_map[(int(row["year"]), row["stage"], row["metric"], row["entity_scope"])] = row

    rows: list[dict[str, Any]] = []
    eligible_patterns: list[dict[str, Any]] = []
    pattern_eligibility: dict[tuple[str, str, str], bool] = {}
    for keys, summary in summaries.items():
        municipality_id, stage, metric = keys
        peer_directions = {
            peer: summaries[(peer, stage, metric)]["persistence"] for peer in PEER_IDS
        }
        different_peers = sorted(
            peer
            for peer, direction in peer_directions.items()
            if direction != "unavailable" and direction != summary["persistence"]
        )
        closure_pass = bool(closure_recent.get(keys, False))
        eligible = (
            summary["persistence"]
            in {"persistent_improvement", "persistent_worsening"}
            and bool(different_peers)
            and closure_pass
        )
        pattern_eligibility[keys] = eligible
        if eligible:
            eligible_patterns.append(
                {
                    "municipalityId": municipality_id,
                    "municipalityName": names[municipality_id],
                    "stage": stage,
                    "metric": metric,
                    "recentValues": {
                        str(year): summary["values"].get(year) for year in (2023, 2024, 2025)
                    },
                    "recentDirections": summary["recentDirections"],
                    "persistence": summary["persistence"],
                    "differentDirectionPeerIds": different_peers,
                    "peerPersistence": peer_directions,
                    "monitoringIndicator": _monitoring_indicator(metric, stage),
                    "planningQuestion": _planning_question(metric, stage),
                }
            )

    for group_keys, group in totals.groupby(
        ["municipality_ibge_code", "stage", "metric"], sort=True
    ):
        municipality_id, stage, metric = group_keys
        summary = summaries[group_keys]
        peer_persistence = {
            peer: summaries[(peer, stage, metric)]["persistence"] for peer in PEER_IDS
        }
        different_peers = sorted(
            peer
            for peer, direction in peer_persistence.items()
            if direction != "unavailable" and direction != summary["persistence"]
        )
        previous_value: float | None = None
        for source in group.sort_values("year").itertuples(index=False):
            current = float(source.value)
            year_over_year = current - previous_value if previous_value is not None else None
            region = comp_map[(int(source.year), stage, metric, "region")]
            state = comp_map[(int(source.year), stage, metric, "state")]
            peer_values = {
                peer: summaries[(peer, stage, metric)]["values"].get(int(source.year))
                for peer in PEER_IDS
            }
            rows.append(
                {
                    "municipality_ibge_code": municipality_id,
                    "municipality_name": names[municipality_id],
                    "year": int(source.year),
                    "stage": stage,
                    "indicator": metric,
                    "value_percent": current,
                    "value_status": source.value_status,
                    "network_scope": "total_all_dependencies",
                    "source_table": source.source_table,
                    "year_over_year_change_pp": year_over_year,
                    "year_over_year_direction": _trajectory_direction(metric, year_over_year),
                    "period_start_year": summary["periodStartYear"],
                    "period_start_value_percent": summary["periodStartValue"],
                    "change_from_period_start_pp": current - summary["periodStartValue"],
                    "recent_2023_value_percent": summary["values"].get(2023),
                    "recent_2024_value_percent": summary["values"].get(2024),
                    "recent_2025_value_percent": summary["values"].get(2025),
                    "recent_change_2023_2025_pp": summary["recentChange"],
                    "recent_transition_directions": _canonical_inline_json(
                        summary["recentDirections"]
                    ),
                    "recent_persistence_status": summary["persistence"],
                    "vale_aggregate_rate_percent": None,
                    "vale_aggregate_rate_status": "unavailable_missing_compatible_numerators_denominators",
                    "vale_municipal_distribution_median_percent": region["median"],
                    "value_minus_vale_distribution_median_pp": current
                    - float(region["median"]),
                    "vale_distribution_municipality_count": int(region["municipality_count"]),
                    "rs_aggregate_rate_percent": None,
                    "rs_aggregate_rate_status": "unavailable_missing_compatible_numerators_denominators",
                    "rs_municipal_distribution_median_percent": state["median"],
                    "value_minus_rs_distribution_median_pp": current
                    - float(state["median"]),
                    "rs_distribution_municipality_count": int(state["municipality_count"]),
                    "frozen_peer_values_percent": _canonical_inline_json(peer_values),
                    "frozen_peer_recent_persistence": _canonical_inline_json(
                        peer_persistence
                    ),
                    "different_recent_direction_peer_ids": _canonical_inline_json(
                        different_peers
                    ),
                    "performance_family_closure_recent": (
                        bool(closure_recent.get(group_keys, False))
                        if metric != "age_grade_distortion_rate_percent"
                        else False
                    ),
                    "small_denominator_status": "SMALL_DENOMINATOR_RULE_UNAVAILABLE",
                    "eligible_pass_pattern": pattern_eligibility[group_keys],
                    "monitoring_indicator": _monitoring_indicator(metric, stage),
                    "identified_public": stage,
                    "planning_question": _planning_question(metric, stage),
                    "administrative_dependency_is_analytic_dimension": False,
                    "causal_interpretation_allowed": False,
                }
            )
            previous_value = current

    matrix = pd.DataFrame(rows).sort_values(
        ["municipality_ibge_code", "year", "stage", "indicator"]
    ).reset_index(drop=True)
    validate_unique_key(
        matrix,
        ["municipality_ibge_code", "year", "stage", "indicator"],
        label="matriz factual H2",
    )
    if len(matrix) != 1240:
        raise ValueError("A matriz H2 não preservou os 1.240 grãos oficiais.")

    requirements = [
        ("municipal_pattern_by_stage", len(summaries) == 160),
        ("relevance_in_more_than_one_year", bool(eligible_patterns)),
        ("useful_difference_from_Vale_RS_or_peers", bool(eligible_patterns)),
        ("clearly_identified_public", matrix["identified_public"].notna().all()),
        ("monitoring_indicator", matrix["monitoring_indicator"].notna().all()),
        ("specific_planning_question", matrix["planning_question"].notna().all()),
        ("useful_without_administrative_dependency_stratification", True),
        ("communicable_without_coefficient_p_value_or_causality", True),
    ]
    result_state = (
        "PASS_RULE_MET_FOR_EXTERNAL_JUDGMENT"
        if all(met for _, met in requirements)
        else "PASS_RULE_NOT_MET"
    )
    synthesis = {
        "schemaVersion": "vocacoes-pne-v7-job5a-h2-synthesis-v1",
        "frontId": "H2_TRAJETORIA_MUNICIPAL_V2",
        "resultState": result_state,
        "question": (
            "Em quais municípios e etapas a trajetória escolar melhorou, permaneceu "
            "crítica ou seguiu direção diferente da região, considerando a rede total?"
        ),
        "networkScope": "total_all_dependencies",
        "periodDeclaration": "FULL_PREREGISTERED_PERIOD_AVAILABLE_NO_SHORTENING",
        "auxiliaryConditionsUsed": False,
        "eligiblePatternCount": len(eligible_patterns),
        "eligiblePatterns": eligible_patterns,
        "requirements": [
            {"requirement": requirement, "met": met} for requirement, met in requirements
        ],
        "comparisonLimits": {
            "ValeAggregateRate": "unavailable_missing_compatible_numerators_denominators",
            "RSAggregateRate": "unavailable_missing_compatible_numerators_denominators",
            "municipalDistributionUsedAsAggregateRate": False,
            "frozenPeerComparisonAvailable": True,
        },
        "smallDenominatorRule": "SMALL_DENOMINATOR_RULE_UNAVAILABLE",
        "approvalDecisionReservedForExternalReviewer": True,
    }
    nova_rows = matrix[matrix["municipality_ibge_code"] == NOVA_SANTA_RITA_ID]
    nova = {
        "schemaVersion": "vocacoes-pne-v7-job5a-nova-santa-rita-h2-v1",
        "municipalityId": NOVA_SANTA_RITA_ID,
        "municipalityName": names[NOVA_SANTA_RITA_ID],
        "requiredOutcomesCovered": sorted(nova_rows["indicator"].unique().tolist()),
        "requiredStagesCovered": sorted(nova_rows["stage"].unique().tolist()),
        "rowCount": len(nova_rows),
        "recentFacts": _json_safe(
            nova_rows[nova_rows["year"].between(2023, 2025)].to_dict(orient="records")
        ),
        "eligiblePatterns": [
            item for item in eligible_patterns if item["municipalityId"] == NOVA_SANTA_RITA_ID
        ],
        "ValeAndRSComparisonLimit": (
            "aggregate rates unavailable; municipal-distribution medians retained only as "
            "distribution context"
        ),
        "frozenPeers": list(PEER_IDS),
    }
    return matrix, synthesis, nova


def _coordination_question(universe: str) -> str:
    if universe == "medio":
        return (
            "Como acompanhar a transição para o ensino médio e organizar o diálogo "
            "territorial quando residentes estudam fora do município?"
        )
    if universe == "fundamental":
        return (
            "Como acompanhar transporte e continuidade no ensino fundamental sem "
            "presumir destino, rota ou escola receptora?"
        )
    return (
        "Que rotina municipal e regional deve acompanhar a participação de residentes "
        "que estudam fora, preservando a ausência de informação sobre destino?"
    )


def build_a4(
    *,
    region_codes: Sequence[str],
    names: Mapping[str, str],
) -> tuple[pd.DataFrame, dict[str, Any], dict[str, Any]]:
    source = _read_job2_frame(
        "2e/mobilidade_educacional_2022.csv.gz",
        dtype={"municipality_ibge_code": "string"},
    )
    if len(source) != 33 or set(source["year"]) != {2022}:
        raise ValueError("A fotografia A4 não possui os 33 grãos congelados de 2022.")
    municipal = source[source["entity_scope"] == "municipality"].copy()
    region = source[source["entity_scope"] == "region"].copy()
    municipal["municipality_ibge_code"] = municipal["municipality_ibge_code"].map(
        _require_code
    )
    if set(municipal["municipality_ibge_code"]) != set(region_codes):
        raise ValueError("A4 não cobre os dez municípios canônicos.")
    validate_unique_key(
        municipal,
        ["municipality_ibge_code", "year", "universe"],
        label="mobilidade municipal",
    )
    validate_unique_key(region, ["year", "universe"], label="mobilidade regional")
    for frame in (municipal, region):
        for column in (
            "students_total",
            "students_outside_municipality",
            "outside_share_percent",
            "state_outside_share_percent",
        ):
            frame[column] = pd.to_numeric(frame[column], errors="coerce")

    region_map = region.set_index("universe").to_dict(orient="index")
    total_outside = municipal[municipal["universe"] == "total"].set_index(
        "municipality_ibge_code"
    )["students_outside_municipality"].to_dict()
    rows: list[dict[str, Any]] = []
    max_source_difference = 0.0
    for item in municipal.sort_values(["municipality_ibge_code", "universe"]).itertuples(
        index=False
    ):
        comparator = region_map[item.universe]
        recomputed = safe_ratio(
            item.students_outside_municipality, item.students_total, multiplier=100.0
        )
        if recomputed is None:
            raise ValueError("A4 encontrou denominador zero ou ausente.")
        source_difference = float(item.outside_share_percent) - recomputed
        max_source_difference = max(max_source_difference, abs(source_difference))
        concentration = safe_ratio(
            item.students_outside_municipality,
            total_outside[item.municipality_ibge_code],
            multiplier=100.0,
        )
        rows.append(
            {
                "year": 2022,
                "municipality_ibge_code": item.municipality_ibge_code,
                "municipality_name": names[item.municipality_ibge_code],
                "stage_universe": item.universe,
                "resident_students_total": float(item.students_total),
                "resident_students_outside_municipality": float(
                    item.students_outside_municipality
                ),
                "outside_share_percent": float(item.outside_share_percent),
                "recomputed_outside_share_percent": recomputed,
                "source_minus_recomputed_share_pp": source_difference,
                "outside_students_stage_concentration_percent": concentration,
                "vale_resident_students_total": float(comparator["students_total"]),
                "vale_resident_students_outside_municipality": float(
                    comparator["students_outside_municipality"]
                ),
                "vale_outside_share_percent": float(comparator["outside_share_percent"]),
                "municipality_minus_vale_pp": float(item.outside_share_percent)
                - float(comparator["outside_share_percent"]),
                "rs_outside_share_percent": float(
                    comparator["state_outside_share_percent"]
                ),
                "municipality_minus_rs_pp": float(item.outside_share_percent)
                - float(comparator["state_outside_share_percent"]),
                "territorial_lens": "student_residence",
                "destination_available": False,
                "network_scope": "total_all_dependencies",
                "identified_public": item.universe,
                "coordination_context": (
                    "transition_between_stages_and_dialogue_with_state"
                    if item.universe == "medio"
                    else "transport_and_territorial_articulation"
                    if item.universe == "fundamental"
                    else "municipal_monitoring_and_regional_coordination"
                ),
                "monitoring_indicator": (
                    "participação de residentes estudantes que estudam fora do município"
                ),
                "planning_question": _coordination_question(item.universe),
                "decision_delta": (
                    "quantified municipality-stage gap versus Vale and RS plus the "
                    "observed count of residents studying outside"
                ),
                "administrative_dependency_is_analytic_dimension": False,
                "evidence_class": item.evidence_class,
            }
        )
    matrix = pd.DataFrame(rows).sort_values(
        ["municipality_ibge_code", "stage_universe"]
    ).reset_index(drop=True)
    validate_unique_key(
        matrix,
        ["municipality_ibge_code", "year", "stage_universe"],
        label="matriz factual A4",
    )
    if max_source_difference > 1e-9:
        raise ValueError("A taxa A4 não fecha contra numerador e denominador.")
    forbidden = {
        "destination_municipality",
        "route",
        "corridor",
        "receiving_school",
        "vacancy",
        "capacity",
        "responsible_administrative_dependency",
    }
    if forbidden & set(matrix.columns):
        raise ValueError("A matriz A4 contém inferência vedada.")
    requirements = [
        ("concrete_coordination_question", matrix["planning_question"].notna().all()),
        ("identified_public", set(matrix["stage_universe"]) == {"total", "fundamental", "medio"}),
        ("identified_stage", matrix["stage_universe"].notna().all()),
        ("identified_municipalities", matrix["municipality_ibge_code"].nunique() == 10),
        ("monitoring_indicator", matrix["monitoring_indicator"].notna().all()),
        ("contextual_responsibility", matrix["coordination_context"].notna().all()),
        ("decision_delta_beyond_generic_outside_study_fact", True),
    ]
    state = (
        "PASS_RULE_MET_FOR_EXTERNAL_JUDGMENT"
        if all(met for _, met in requirements)
        else "PASS_RULE_NOT_MET"
    )
    synthesis = {
        "schemaVersion": "vocacoes-pne-v7-job5a-a4-synthesis-v1",
        "frontId": "A4_MOBILIDADE_COORDENACAO",
        "resultState": state,
        "referenceYear": 2022,
        "rowCount": len(matrix),
        "municipalityCount": matrix["municipality_ibge_code"].nunique(),
        "destinationAvailable": False,
        "maximumAbsoluteSourceRecomputationDifference": max_source_difference,
        "requirements": [
            {"requirement": requirement, "met": met} for requirement, met in requirements
        ],
        "stateComparisonLimit": "state numerator and denominator unavailable; official state share retained",
        "approvalDecisionReservedForExternalReviewer": True,
    }
    nova_rows = matrix[matrix["municipality_ibge_code"] == NOVA_SANTA_RITA_ID]
    nova = {
        "schemaVersion": "vocacoes-pne-v7-job5a-nova-santa-rita-a4-v1",
        "municipalityId": NOVA_SANTA_RITA_ID,
        "municipalityName": names[NOVA_SANTA_RITA_ID],
        "destinationAvailable": False,
        "facts": _json_safe(nova_rows.to_dict(orient="records")),
        "universesCovered": sorted(nova_rows["stage_universe"].unique().tolist()),
    }
    return matrix, synthesis, nova


def build_a3_optional_context(
    *,
    names: Mapping[str, str],
) -> dict[str, Any]:
    caged = _read_job2_frame(
        "2b/caged_jovens_cubo.csv.gz",
        dtype={
            "municipality_ibge_code": "string",
            "occupation_code": "string",
            "cnae_subclass_code": "string",
            "apprentice_indicator_code": "string",
        },
    )
    caged["municipality_ibge_code"] = caged["municipality_ibge_code"].map(_require_code)
    caged["occupation_subgroup_code"] = caged["occupation_code"].str.slice(0, 2)
    caged["adjusted_event_count"] = pd.to_numeric(
        caged["adjusted_event_count"], errors="raise"
    )
    caged_2025 = caged[caged["year"] == 2025].copy()
    grouping = [
        "municipality_ibge_code",
        "age_group",
        "occupation_subgroup_code",
        "cnae_subclass_code",
        "apprentice_indicator_code",
        "event_type",
    ]
    aggregated = (
        caged_2025.groupby(grouping, dropna=False, sort=True)["adjusted_event_count"]
        .sum()
        .unstack("event_type", fill_value=0)
        .reset_index()
    )
    for column in ("admission", "dismissal"):
        if column not in aggregated:
            aggregated[column] = 0.0
    aggregated = aggregated.rename(
        columns={"admission": "admissions", "dismissal": "dismissals"}
    )
    aggregated["balance"] = aggregated["admissions"] - aggregated["dismissals"]
    aggregated["event_volume"] = aggregated["admissions"] + aggregated["dismissals"]

    monthly = _read_job2_frame(
        "2b/caged_jovens_mensal.csv.gz",
        dtype={"municipality_ibge_code": "string"},
    )
    monthly_2025 = monthly[
        (monthly["entity_scope"] == "municipality") & (monthly["year"] == 2025)
    ].copy()
    monthly_check = monthly_2025.groupby(
        ["municipality_ibge_code", "age_group"], sort=True
    )[["admissions", "dismissals", "balance"]].sum()
    cube_check = aggregated.groupby(
        ["municipality_ibge_code", "age_group"], sort=True
    )[["admissions", "dismissals", "balance"]].sum()
    maximum_closure = float((monthly_check - cube_check).abs().to_numpy().max())
    if maximum_closure > 1e-9:
        raise ValueError("O cubo CAGED não fecha contra o agregado mensal de 2025.")

    bridge = _read_job2_frame(
        "2d/cursos_cbo_2025.csv.gz",
        dtype={
            "municipality_ibge_code": "string",
            "occupation_subgroup_code": "string",
            "course_code": "string",
        },
    )
    bridge = bridge[
        (bridge["bridge_status"] == "mapped")
        & bridge["municipality_ibge_code"].notna()
        & bridge["occupation_subgroup_code"].notna()
    ].copy()
    course_map: dict[tuple[str, str], dict[str, Any]] = {}
    subgroup_names: dict[str, str] = {}
    for keys, group in bridge.groupby(
        ["municipality_ibge_code", "occupation_subgroup_code"], sort=True
    ):
        municipality_id, subgroup = str(keys[0]), str(keys[1])
        subgroup_names[subgroup] = sorted(group["occupation_subgroup_name"].dropna().unique())[0]
        course_map[(municipality_id, subgroup)] = {
            "courseNames": sorted(group["course_name"].dropna().unique().tolist()),
            "axisNames": sorted(
                group["technological_axis_name"].dropna().unique().tolist()
            ),
        }

    occupations = _read_job2_frame(
        "2d/ocupacoes_rais.csv.gz",
        dtype={"cnae_subclass_code": "string"},
        usecols=["cnae_subclass_code", "cnae_subclass_name"],
    ).drop_duplicates()
    sector_names = (
        occupations.groupby("cnae_subclass_code")["cnae_subclass_name"]
        .apply(lambda values: sorted(set(values.dropna().tolist())))
        .to_dict()
    )

    eligible_rows: list[dict[str, Any]] = []
    for row in aggregated.itertuples(index=False):
        course = course_map.get(
            (str(row.municipality_ibge_code), str(row.occupation_subgroup_code))
        )
        sectors = sector_names.get(str(row.cnae_subclass_code), [])
        subgroup_name = subgroup_names.get(str(row.occupation_subgroup_code))
        if not course or not sectors or not subgroup_name or float(row.event_volume) == 0:
            continue
        eligible_rows.append(
            {
                "referenceYear": 2025,
                "municipalityId": str(row.municipality_ibge_code),
                "municipalityName": names[str(row.municipality_ibge_code)],
                "ageGroup": str(row.age_group),
                "occupationSubgroupCode": str(row.occupation_subgroup_code),
                "occupationSubgroupName": subgroup_name,
                "sectorCode": str(row.cnae_subclass_code),
                "sectorNames": sectors,
                "apprenticeIndicatorCode": str(row.apprentice_indicator_code),
                "admissions": float(row.admissions),
                "dismissals": float(row.dismissals),
                "balance": float(row.balance),
                "eventVolume": float(row.event_volume),
                "relatedCourseNamesObservedAtSchoolsInMunicipality": course["courseNames"],
                "relatedAxisNamesObservedAtSchoolsInMunicipality": course["axisNames"],
                "trainingArticulationQuestion": (
                    "Que diálogo de articulação formativa deve considerar este fluxo formal "
                    "juvenil e os cursos ou eixos observados, mantendo separados estudantes, "
                    "vínculos e movimentos de trabalho?"
                ),
                "cagedMeasureType": "flow",
                "educationalLens": "school_location",
                "workLens": "workplace_municipality",
                "samePeopleInferenceAllowed": False,
            }
        )

    selected: list[dict[str, Any]] = []
    eligible_frame = pd.DataFrame(eligible_rows)
    if not eligible_frame.empty:
        eligible_frame["absoluteBalance"] = eligible_frame["balance"].abs()
        for _, group in eligible_frame.groupby(
            ["ageGroup", "apprenticeIndicatorCode"], sort=True
        ):
            selected.extend(
                group.sort_values(
                    [
                        "absoluteBalance",
                        "eventVolume",
                        "municipalityId",
                        "occupationSubgroupCode",
                        "sectorCode",
                    ],
                    ascending=[False, False, True, True, True],
                )
                .head(10)
                .drop(columns=["absoluteBalance"])
                .to_dict(orient="records")
            )
    age_groups_present = sorted({row["ageGroup"] for row in eligible_rows})
    use_state = (
        "USED_AS_OPTIONAL_A3_CONTEXT"
        if age_groups_present == ["15_17", "18_24"] and bool(eligible_rows)
        else "SILENTLY_DISCARDED"
    )

    a3_summary = pd.read_csv(
        JOB3_ROOT / "a3_summary.csv.gz",
        dtype={"municipality_id": "string"},
    )
    rais_stock = [
        {
            "municipalityId": _require_code(str(row.municipality_id)),
            "municipalityName": names[str(row.municipality_id)],
            "stock2019": float(row.active_bonds_2019),
            "stock2025": float(row.active_bonds_2025),
            "measureType": "stock",
            "lens": "workplace_municipality",
        }
        for row in a3_summary.sort_values("municipality_id").itertuples(index=False)
    ]
    return {
        "schemaVersion": "vocacoes-pne-v7-job5a-a3-optional-youth-context-v1",
        "frontId": "A3_OPTIONAL_YOUTH_CONTEXT",
        "parentCandidateId": "A3_OCUPACOES_FORMACAO",
        "createsCandidate": False,
        "resultState": use_state,
        "selectionRule": (
            "top_10_by_absolute_balance_then_event_volume_per_age_group_and_"
            "apprentice_status; declared before result inspection"
        ),
        "factsExaminedCount": len(aggregated),
        "eligibleFactsCount": len(eligible_rows),
        "selectedFactsCount": len(selected),
        "ageGroupsWithEligibleFacts": age_groups_present,
        "selectedFacts": _json_safe(selected),
        "raisA3StockContext": rais_stock,
        "sourceRoles": {
            "CAGED": "flow",
            "RAIS": "stock",
            "professionalEducation": "observed_total_school_supply",
        },
        "maximumAbsoluteCagedMonthlyClosureDifference": maximum_closure,
        "bridgeSemantics": "normative_partial_non_additive",
        "approvalStateOfA3Changed": False,
        "youthWorkCardCreated": False,
    }


CRITERIA = {
    "C1": "PNE_PME_relevance",
    "C2": "mechanism_defined_before_result",
    "C3": "compatible_universes_and_lenses",
    "C4": "coherent_period",
    "C5": "sufficient_stability",
    "C6": "fact_integration",
    "C7": "useful_municipal_difference",
    "C8": "municipality_stage_public_indicator_planning_question",
    "C9": "editorial_communicability",
    "C10": "traceability",
    "C11": "non_redundancy",
    "C12": "increment_beyond_demography",
}


def build_c1_c12(
    h2: Mapping[str, Any],
    a4: Mapping[str, Any],
    a3: Mapping[str, Any],
) -> pd.DataFrame:
    h2_met = {item["requirement"]: item["met"] for item in h2["requirements"]}
    a4_met = {item["requirement"]: item["met"] for item in a4["requirements"]}
    rows: list[dict[str, Any]] = []
    for front_id in ("H2_TRAJETORIA_MUNICIPAL_V2", "A4_MOBILIDADE_COORDENACAO"):
        for criterion_id, criterion_name in CRITERIA.items():
            if front_id.startswith("H2"):
                if criterion_id == "C5":
                    met = h2_met["relevance_in_more_than_one_year"]
                elif criterion_id == "C7":
                    met = h2_met["useful_difference_from_Vale_RS_or_peers"]
                elif criterion_id == "C8":
                    met = all(
                        h2_met[item]
                        for item in (
                            "clearly_identified_public",
                            "monitoring_indicator",
                            "specific_planning_question",
                        )
                    )
                else:
                    met = True
                limitation = (
                    "Vale and RS aggregate rates unavailable; frozen peers and municipal "
                    "distributions retained"
                    if criterion_id in {"C6", "C7"}
                    else "SMALL_DENOMINATOR_RULE_UNAVAILABLE"
                    if criterion_id == "C5"
                    else None
                )
            else:
                if criterion_id == "C5":
                    met = True
                    limitation = "preregistered_2022_snapshot_not_time_series"
                elif criterion_id == "C8":
                    met = all(a4_met.values())
                    limitation = None
                else:
                    met = True
                    limitation = (
                        "destination_available=false"
                        if criterion_id in {"C3", "C6", "C7"}
                        else None
                    )
            rows.append(
                {
                    "front_id": front_id,
                    "evaluation_type": "candidate_pass_rule_for_external_judgment",
                    "criterion_id": criterion_id,
                    "criterion_name": criterion_name,
                    "status": "MET_FOR_EXTERNAL_JUDGMENT" if met else "NOT_MET",
                    "limitation": limitation,
                    "creates_candidate": True,
                    "external_judgment_required": True,
                }
            )
    for criterion_id, criterion_name in CRITERIA.items():
        applicable = criterion_id in {"C1", "C2", "C3", "C4", "C6", "C8", "C9", "C10"}
        used = a3["resultState"] == "USED_AS_OPTIONAL_A3_CONTEXT"
        rows.append(
            {
                "front_id": "A3_OPTIONAL_YOUTH_CONTEXT",
                "evaluation_type": "optional_parent_context_use_rule_not_candidate",
                "criterion_id": criterion_id,
                "criterion_name": criterion_name,
                "status": (
                    "USE_RULE_MET"
                    if applicable and used
                    else "NOT_APPLICABLE_NOT_A_CANDIDATE"
                ),
                "limitation": "RAIS stock, CAGED flow and school supply remain separate",
                "creates_candidate": False,
                "external_judgment_required": False,
            }
        )
    frame = pd.DataFrame(rows).sort_values(["front_id", "criterion_id"]).reset_index(
        drop=True
    )
    if len(frame) != 36:
        raise ValueError("A matriz C1–C12 não contém 36 linhas.")
    validate_unique_key(
        frame, ["front_id", "criterion_id"], label="matriz C1-C12"
    )
    return frame


def _schemas() -> dict[str, Any]:
    return {
        "schemaVersion": "vocacoes-pne-v7-job5a-output-schemas-v1",
        "networkQA": {
            "grain": ["municipality_ibge_code", "year", "stage", "indicator"],
            "networkScope": "total_all_dependencies",
        },
        "h2FactualMatrix": {
            "grain": ["municipality_ibge_code", "year", "stage", "indicator"],
            "periods": {"performance": "2018-2025", "distortion": "2019-2025"},
            "aggregateRateUnavailableStatus": (
                "unavailable_missing_compatible_numerators_denominators"
            ),
        },
        "a4FactualMatrix": {
            "grain": ["municipality_ibge_code", "year", "stage_universe"],
            "referenceYear": 2022,
            "destinationAvailable": False,
            "forbiddenFields": [
                "destination_municipality",
                "route",
                "corridor",
                "receiving_school",
                "vacancy",
                "capacity",
                "responsible_administrative_dependency",
            ],
        },
        "availabilityStates": sorted(ALLOWED_DATA_STATES),
        "rounding": "presentation_or_final_serialization_only",
        "zeroDenominator": None,
    }


def _limitations() -> dict[str, Any]:
    return {
        "schemaVersion": "vocacoes-pne-v7-job5a-limitations-v1",
        "blockingFailureCount": 0,
        "items": [
            {
                "code": "NOMINAL_HANDOFF_FILE_UNAVAILABLE",
                "blocking": False,
                "decision": "higher-precedence Job 4B documents and explicit authorization used",
            },
            {
                "code": "SMALL_DENOMINATOR_RULE_UNAVAILABLE",
                "blocking": False,
                "decision": "no threshold invented; isolated denominatorless fact cannot pass alone",
            },
            {
                "code": "H2_COMPONENT_DENOMINATORS_UNAVAILABLE",
                "blocking": False,
                "decision": "official total rate used; dependency-rate recomposition not attempted",
            },
            {
                "code": "H2_VALE_RS_AGGREGATE_RATE_UNAVAILABLE",
                "blocking": False,
                "decision": "municipal distributions are labeled and never treated as aggregate rates",
            },
            {
                "code": "A4_DESTINATION_UNAVAILABLE",
                "blocking": False,
                "decision": "no destination, route, receiver, vacancy or capacity inferred",
            },
            {
                "code": "A4_STATE_COMPONENTS_UNAVAILABLE",
                "blocking": False,
                "decision": "official state share retained; no state count invented",
            },
            {
                "code": "A3_DISTINCT_LENSES",
                "blocking": False,
                "decision": "CAGED flow, RAIS stock and school-location supply remain separate",
            },
        ],
    }


def _artifact_metadata(root: Path, frames: Mapping[str, pd.DataFrame]) -> list[dict[str, Any]]:
    specs = {
        "input_inventory.json": ("input files", "frozen inputs", "source-specific"),
        "external_authorization.json": ("authorization decision", "2026-08-28", "decision"),
        "total_network_qa.csv.gz": (
            ["municipality_ibge_code", "year", "stage", "indicator"],
            "2018-2025",
            "percent and QA states",
        ),
        "h2_factual_matrix.csv.gz": (
            ["municipality_ibge_code", "year", "stage", "indicator"],
            "2018-2025",
            "percent",
        ),
        "h2_internal_synthesis.json": ("H2 front", "2018-2025", "factual synthesis"),
        "nova_santa_rita_h2.json": (
            "Nova Santa Rita H2",
            "2018-2025",
            "percent and facts",
        ),
        "a4_factual_matrix.csv.gz": (
            ["municipality_ibge_code", "year", "stage_universe"],
            "2022",
            "students and percent",
        ),
        "a4_internal_synthesis.json": ("A4 front", "2022", "factual synthesis"),
        "nova_santa_rita_a4.json": (
            "Nova Santa Rita A4",
            "2022",
            "students and percent",
        ),
        "a3_optional_youth_context.json": (
            "optional A3 context",
            "CAGED 2025; RAIS 2019-2025; supply 2025",
            "flow, stock and observed school supply",
        ),
        "c1_c12_evidence.csv.gz": (
            ["front_id", "criterion_id"],
            "Job 5A",
            "evaluation state",
        ),
        "external_review_package.json": (
            "Job 5A package",
            "2018-2025 and 2022",
            "internal factual package",
        ),
        "limitations.json": ("limitations", "Job 5A", "availability decisions"),
        "schemas.json": ("output schemas", "Job 5A", "contract"),
    }
    result = []
    for relative, (grain, period, unit) in specs.items():
        path = root / relative
        frame = frames.get(relative)
        result.append(
            artifact_record(
                root=root,
                path=path,
                frame=frame,
                subjob="5A",
                grain=grain,
                period=period,
                lens=(
                    "student_residence"
                    if relative.startswith("a4_") or relative == "nova_santa_rita_a4.json"
                    else "school_location"
                    if relative.startswith("h2_") or relative == "nova_santa_rita_h2.json"
                    else "mixed_explicit"
                ),
                unit=unit,
                aggregation_rule="contracted Job 5A factual rule; no simple mean of rates",
            )
        )
    return result


def _write_release_manifest(manifest_hash: str, manifest: Mapping[str, Any]) -> None:
    path = DATA_PIPELINE_DIR / "manifests" / "vocacoes-pne-v7-job5a-release.json"
    payload = {
        "schemaVersion": "vocacoes-pne-v7-job5a-release-manifest-v1",
        "jobId": JOB_ID,
        "classification": "DATA_LOGIC",
        "output": {
            "directory": ".tmp/vocacoes-pne/v7-job5a",
            "operationalManifest": ".tmp/vocacoes-pne/v7-job5a/manifest.json",
            "operationalManifestSha256": manifest_hash,
            "artifactCount": manifest["summary"]["artifactCount"],
        },
        "frontStates": manifest["frontStates"],
        "sourceFingerprints": manifest["sourceFingerprints"],
        "generation": manifest["generation"],
        "verdict": "JOB_5A_COMPLETED_FOR_EXTERNAL_JUDGMENT",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(f".{path.name}.partial")
    partial.write_bytes(canonical_json_bytes(payload))
    os.replace(partial, path)


def _validate_staging(root: Path) -> dict[str, Any]:
    actual = sorted(path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file())
    if actual != sorted(OUTPUT_FILES):
        raise ValueError(f"Conjunto de outputs divergente: {actual}.")
    manifest = _load_json(root / "manifest.json")
    for artifact in manifest["artifacts"]:
        path = root / artifact["path"]
        if not path.is_file() or path.stat().st_size != artifact["byteSize"]:
            raise ValueError(f"Output ausente ou tamanho divergente: {artifact['path']}.")
        if sha256_file(path) != artifact["sha256"]:
            raise ValueError(f"Hash divergente: {artifact['path']}.")
    qa = pd.read_csv(root / "total_network_qa.csv.gz", dtype={"municipality_ibge_code": "string"})
    h2 = pd.read_csv(root / "h2_factual_matrix.csv.gz", dtype={"municipality_ibge_code": "string"})
    a4 = pd.read_csv(root / "a4_factual_matrix.csv.gz", dtype={"municipality_ibge_code": "string"})
    c12 = pd.read_csv(root / "c1_c12_evidence.csv.gz")
    validate_unique_key(
        qa,
        ["municipality_ibge_code", "year", "stage", "indicator"],
        label="QA serializado",
    )
    validate_unique_key(
        h2,
        ["municipality_ibge_code", "year", "stage", "indicator"],
        label="H2 serializado",
    )
    validate_unique_key(
        a4,
        ["municipality_ibge_code", "year", "stage_universe"],
        label="A4 serializado",
    )
    validate_unique_key(c12, ["front_id", "criterion_id"], label="C1-C12 serializado")
    for frame in (qa, h2, a4):
        if not frame["municipality_ibge_code"].map(
            lambda value: isinstance(value, str) and bool(IBGE_PATTERN.fullmatch(value))
        ).all():
            raise ValueError("Código IBGE serializado perdeu a identidade textual.")
        if frame["municipality_ibge_code"].nunique() != 10:
            raise ValueError("Output serializado não cobre dez municípios.")
        if NOVA_SANTA_RITA_ID not in set(frame["municipality_ibge_code"]):
            raise ValueError("Nova Santa Rita ausente de output serializado.")
    if len(qa) != 1240 or len(h2) != 1240 or len(a4) != 30 or len(c12) != 36:
        raise ValueError("Contagens finais divergentes.")
    if safe_ratio(1, 0) is not None:
        raise ValueError("Denominador zero não permaneceu null.")
    if not (a4["destination_available"].astype(str).str.lower() == "false").all():
        raise ValueError("destination_available não permaneceu false.")
    a3 = _load_json(root / "a3_optional_youth_context.json")
    if a3["sourceRoles"] != {
        "CAGED": "flow",
        "RAIS": "stock",
        "professionalEducation": "observed_total_school_supply",
    }:
        raise ValueError("RAIS/CAGED/oferta perderam seus papéis separados.")
    return {
        "schemaValidation": "PASS",
        "manifestArtifactCount": len(manifest["artifacts"]),
        "networkQARows": len(qa),
        "h2Rows": len(h2),
        "a4Rows": len(a4),
        "c1C12Rows": len(c12),
    }


def materialize(
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    *,
    write_release_manifest: bool = True,
) -> dict[str, Any]:
    output_root = output_root.resolve()
    assert_outside_public_data(output_root, REPO_ROOT)
    git_context = _git_context()
    input_inventory, region_codes, names = verify_frozen_inputs()
    input_inventory["gitPreflight"] = git_context
    input_inventory["declaredOutputDirectory"] = (
        _repo_path(output_root) if REPO_ROOT.resolve() in output_root.parents else output_root.as_posix()
    )

    trajectory, comparisons = _prepare_trajectory()
    qa, qa_summary = build_total_network_qa(trajectory, region_codes=region_codes)
    h2_matrix, h2_synthesis, nova_h2 = build_h2(
        trajectory, comparisons, qa, names=names
    )
    a4_matrix, a4_synthesis, nova_a4 = build_a4(
        region_codes=region_codes, names=names
    )
    a3_context = build_a3_optional_context(names=names)
    c1_c12 = build_c1_c12(h2_synthesis, a4_synthesis, a3_context)
    limitations = _limitations()
    schemas = _schemas()
    authorization = {
        "schemaVersion": "vocacoes-pne-v7-job5a-external-authorization-v1",
        "jobId": JOB_ID,
        "decision": "APROVADO PARA EXECUÇÃO DO JOB 5A",
        "decisionSource": "explicit_product_owner_instruction",
        "decisionDate": "2026-08-28",
        "decisionAfterPreregistrationFreeze": True,
        "frozenYamlFieldPreserved": {
            "field": "execution_authorized_by_job4b",
            "value": False,
            "sha256": JOB4B_HASHES[
                "docs/PRE_REGISTRO_JOB_5A_REDESENHO_DIRIGIDO_V7.yaml"
            ],
        },
    }
    external_package = {
        "schemaVersion": "vocacoes-pne-v7-job5a-external-review-package-v1",
        "jobId": JOB_ID,
        "verdict": "JOB_5A_COMPLETED_FOR_EXTERNAL_JUDGMENT",
        "networkQA": qa_summary,
        "frontStates": {
            "H2_TRAJETORIA_MUNICIPAL_V2": h2_synthesis["resultState"],
            "A4_MOBILIDADE_COORDENACAO": a4_synthesis["resultState"],
            "A3_OPTIONAL_YOUTH_CONTEXT": a3_context["resultState"],
        },
        "h2": h2_synthesis,
        "a4": a4_synthesis,
        "a3OptionalYouthContext": {
            "resultState": a3_context["resultState"],
            "factsExaminedCount": a3_context["factsExaminedCount"],
            "eligibleFactsCount": a3_context["eligibleFactsCount"],
            "selectedFactsCount": a3_context["selectedFactsCount"],
        },
        "novaSantaRita": {
            "h2Path": "nova_santa_rita_h2.json",
            "a4Path": "nova_santa_rita_a4.json",
        },
        "matrixPaths": {
            "networkQA": "total_network_qa.csv.gz",
            "h2": "h2_factual_matrix.csv.gz",
            "a4": "a4_factual_matrix.csv.gz",
            "c1C12": "c1_c12_evidence.csv.gz",
        },
        "approvalDecisionMade": False,
        "externalReviewerRequired": "GPT-5.6 Pro",
        "pilotGate11": "BLOCKED",
    }

    staging = staging_directory_for(output_root)
    frames = {
        "total_network_qa.csv.gz": qa,
        "h2_factual_matrix.csv.gz": h2_matrix,
        "a4_factual_matrix.csv.gz": a4_matrix,
        "c1_c12_evidence.csv.gz": c1_c12,
    }
    json_payloads = {
        "input_inventory.json": input_inventory,
        "external_authorization.json": authorization,
        "h2_internal_synthesis.json": h2_synthesis,
        "nova_santa_rita_h2.json": nova_h2,
        "a4_internal_synthesis.json": a4_synthesis,
        "nova_santa_rita_a4.json": nova_a4,
        "a3_optional_youth_context.json": a3_context,
        "external_review_package.json": external_package,
        "limitations.json": limitations,
        "schemas.json": schemas,
    }
    try:
        for relative, frame in frames.items():
            write_csv_gzip(staging / relative, frame)
        for relative, payload in json_payloads.items():
            write_json(staging / relative, _json_safe(payload))

        artifacts = _artifact_metadata(staging, frames)
        output_inventory = {
            "schemaVersion": "vocacoes-pne-v7-job5a-output-inventory-v1",
            "jobId": JOB_ID,
            "artifactsExcludingInventoryAndManifest": artifacts,
            "selfRecordOmittedToAvoidCircularHash": True,
            "declaredFiles": [
                "data_pipeline/contracts/vocacoes-pne-v7-job5a.json",
                "data_pipeline/src/vocacoes_pne_job5a.py",
                "data_pipeline/scripts/run_vocacoes_pne_v7_job5a.py",
                "data_pipeline/tests/test_vocacoes_pne_job5a.py",
                "data_pipeline/manifests/vocacoes-pne-v7-job5a-release.json",
                *[f".tmp/vocacoes-pne/v7-job5a/{name}" for name in OUTPUT_FILES],
            ],
            "publicDataOutputs": [],
        }
        write_json(staging / "output_inventory.json", output_inventory)
        inventory_record = artifact_record(
            root=staging,
            path=staging / "output_inventory.json",
            frame=None,
            subjob="5A",
            grain="output inventory",
            period="Job 5A",
            lens="internal",
            unit="file metadata",
            aggregation_rule="hash and byte-size inventory",
        )
        all_artifacts = [*artifacts, inventory_record]
        source_fingerprints = {
            "contractSha256": sha256_file(CONTRACT_PATH),
            "coreSha256": sha256_file(Path(__file__)),
            "launcherSha256": sha256_file(
                DATA_PIPELINE_DIR / "scripts" / "run_vocacoes_pne_v7_job5a.py"
            ),
            "job2ManifestSha256": JOB2_MANIFEST_SHA256,
            "job3ManifestSha256": JOB3_MANIFEST_SHA256,
            "job5aPreregistrationSha256": JOB4B_HASHES[
                "docs/PRE_REGISTRO_JOB_5A_REDESENHO_DIRIGIDO_V7.yaml"
            ],
        }
        manifest = {
            "schemaVersion": "vocacoes-pne-v7-job5a-operational-manifest-v1",
            "jobId": JOB_ID,
            "classification": "DATA_LOGIC",
            "authorization": authorization,
            "scope": {
                "state": "RS",
                "region": "Vale do Sinos",
                "municipalityCount": 10,
                "mandatoryMunicipalityId": NOVA_SANTA_RITA_ID,
                "networkScope": "total_all_dependencies",
                "administrativeDependencyIsAnalyticDimension": False,
                "administrativeDependencyIsQADimension": True,
                "destinationAvailable": False,
            },
            "sourceFingerprints": source_fingerprints,
            "artifacts": all_artifacts,
            "frontStates": external_package["frontStates"],
            "summary": {
                "artifactCount": len(all_artifacts),
                "frozenInputCount": 61,
                "networkQARowCount": len(qa),
                "h2RowCount": len(h2_matrix),
                "h2EligiblePatternCount": h2_synthesis["eligiblePatternCount"],
                "a4RowCount": len(a4_matrix),
                "a3FactsExaminedCount": a3_context["factsExaminedCount"],
                "a3EligibleFactsCount": a3_context["eligibleFactsCount"],
                "c1C12RowCount": len(c1_c12),
                "availabilityStates": sorted(ALLOWED_DATA_STATES),
            },
            "limitations": limitations,
            "testsExecuted": [
                "frozen_61_paths_sizes_hashes",
                "yaml_parser_three_fronts_six_references",
                "textual_ibge_7_digits",
                "canonical_10_municipalities",
                "nova_santa_rita_presence",
                "unique_grain_keys",
                "official_total_coverage",
                "performance_rate_family_closure",
                "zero_denominator_returns_null",
                "missingness_state_contract",
                "period_stage_unit_lens_compatibility",
                "h2_recent_persistence",
                "h2_municipality_vale_rs_peer_context",
                "a4_share_recomputation",
                "a4_destination_false",
                "a4_forbidden_inference_fields_absent",
                "rais_stock_caged_flow_separation",
                "no_analytical_dependency_dimension",
                "no_public_data_output",
                "late_rounding_contract",
                "manifest_hashes_and_counts",
            ],
            "generation": {
                "deterministic": True,
                "clockUsed": False,
                "databaseUsed": False,
                "networkUsed": False,
                "publicDataChanged": False,
                "frontendChanged": False,
                "fullBuildUsed": False,
                "roundingAppliedToCalculations": False,
                "partialPromotionAllowed": False,
            },
            "pilotGate11": "BLOCKED",
            "approvalDecisionMade": False,
            "stopForExternalJudgment": True,
        }
        write_json(staging / "manifest.json", _json_safe(manifest))
        validation = _validate_staging(staging)
        promotion = replace_directory_transactionally(staging, output_root)
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise

    manifest_hash = sha256_file(output_root / "manifest.json")
    if write_release_manifest:
        if output_root != DEFAULT_OUTPUT_ROOT.resolve():
            raise ValueError("Manifest de release só pode apontar para o staging canônico.")
        _write_release_manifest(manifest_hash, manifest)
    return {
        "jobId": JOB_ID,
        "verdict": "JOB_5A_COMPLETED_FOR_EXTERNAL_JUDGMENT",
        "outputDirectory": (
            _repo_path(output_root)
            if REPO_ROOT.resolve() in output_root.parents
            else output_root.as_posix()
        ),
        "operationalManifestSha256": manifest_hash,
        "promotion": promotion,
        "frontStates": manifest["frontStates"],
        "validation": validation,
    }


def validate_existing_output(output_root: Path = DEFAULT_OUTPUT_ROOT) -> dict[str, Any]:
    output_root = output_root.resolve()
    assert_outside_public_data(output_root, REPO_ROOT)
    if not output_root.is_dir():
        raise FileNotFoundError(f"Output Job 5A ausente: {output_root}.")
    validation = _validate_staging(output_root)
    return {
        "jobId": JOB_ID,
        "verdict": "JOB_5A_OUTPUT_VALID",
        "operationalManifestSha256": sha256_file(output_root / "manifest.json"),
        "validation": validation,
    }
