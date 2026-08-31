"""Executa a correção dirigida 5G-C-R em staging local e determinístico."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import shutil
import sys
from typing import Any, Iterator, Mapping

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, URL


REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_PIPELINE_DIR = REPO_ROOT / "data_pipeline"
if str(DATA_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_PIPELINE_DIR))

from src.vocacoes_pne_job2 import (  # noqa: E402
    assert_outside_public_data,
    directory_content_digest,
    sha256_file,
    staging_directory_for,
)
from src.vocacoes_pne_job5gcr import (  # noqa: E402
    FINAL_STATE,
    normalize_numeric_code,
    validate_existing_output,
    verify_checkpoints,
    verify_original_job5gc,
    write_package,
)


DEFAULT_OUTPUT = REPO_ROOT / ".tmp" / "vocacoes-pne" / "v7-job5gcr"
SOURCE_JOB5GC_ROOT = REPO_ROOT / ".tmp" / "vocacoes-pne" / "v7-job5gc"
CONTRACT_PATH = DATA_PIPELINE_DIR / "contracts" / "vocacoes-pne-v7-job5gcr.json"
REGION_PATH = REPO_ROOT / "config" / "regions" / "rs.json"
REGISTRY_PATH = REPO_ROOT / "config" / "municipalities" / "rs.json"


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _inputs() -> dict[str, Path]:
    source = REPO_ROOT / ".tmp" / "vocacoes-pne" / "v7-job2"
    job5gar = REPO_ROOT / ".tmp" / "vocacoes-pne" / "v7-job5gar"
    return {
        "job5gcr_contract": CONTRACT_PATH,
        "job5gcr_generator": DATA_PIPELINE_DIR / "src" / "vocacoes_pne_job5gcr.py",
        "job5gcr_runner": Path(__file__).resolve(),
        "rais_youth_cube": source / "2b" / "rais_cubo_jovem.csv.gz",
        "rais_youth_annual": source / "2b" / "rais_estoque_jovem_anual.csv.gz",
        "caged_youth_cube": source / "2b" / "caged_jovens_cubo.csv.gz",
        "caged_youth_monthly": source / "2b" / "caged_jovens_mensal.csv.gz",
        "rais_occupations": source / "2d" / "ocupacoes_rais.csv.gz",
        "ept_offer": source / "2d" / "oferta_cursos_tecnicos.csv.gz",
        "ept_coverage": source / "2d" / "cobertura_oferta_municipal.csv.gz",
        "course_cbo_bridge": source / "2d" / "cursos_cbo_2025.csv.gz",
        "bridge_coverage": source / "2d" / "cobertura_ponte_2025.csv.gz",
        "bridge_contract": DATA_PIPELINE_DIR
        / "contracts"
        / "vocacoes-pne-course-cbo-rs-v1-projection.json",
        "trajectory": job5gar / "PAINEL_TRAJETORIA_OFICIAL_DESCRITIVA_V1_1.csv.gz",
        "trajectory_contract": job5gar
        / "CONTRATO_TRAJETORIA_OFICIAL_DESCRITIVA_V1_1.json",
        "job5gc_manifest": SOURCE_JOB5GC_ROOT / "MANIFEST_JOB5GC.json",
        "job5f_manifest": REPO_ROOT
        / ".tmp"
        / "vocacoes-pne"
        / "v7-job5f"
        / "manifest.json",
        "job5gar_manifest": job5gar / "MANIFEST_JOB5GAR.json",
        "job5gbr_manifest": REPO_ROOT
        / ".tmp"
        / "vocacoes-pne"
        / "v7-job5gbr"
        / "MANIFEST_JOB5GBR.json",
        "job5f_report": REPO_ROOT / "docs" / "RELATORIO_JOB_5F_EXPANSAO_ANALITICA_V7.md",
        "maximum_page_map": REPO_ROOT / "docs" / "MAPA_PAGINA_MAXIMA_GESTORA_V7.md",
    }


def _load_municipalities() -> dict[str, str]:
    region_payload = _json(REGION_PATH)
    region = next(
        item for item in region_payload["regions"] if item["slug"] == "vale-do-sinos"
    )
    codes = [str(value) for value in region["municipalityIbgeCodes"]]
    if region["municipalityCount"] != 10 or len(codes) != 10:
        raise ValueError("O Vale do Sinos não contém os dez municípios contratados.")
    registry = _json(REGISTRY_PATH)
    names = {
        str(item["ibgeCode"]): item["name"]
        for item in registry["municipalities"]
        if str(item["ibgeCode"]) in codes
    }
    if set(names) != set(codes) or names.get("4313375") != "Nova Santa Rita":
        raise ValueError("O registro municipal canônico divergiu do recorte contratado.")
    return names


def _verify_local_inputs(inputs: Mapping[str, Path]) -> None:
    missing = [str(path) for path in inputs.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Entradas congeladas ausentes: {missing}")


def _database_url() -> URL:
    required = ("DB_USUARIO", "DB_SENHA", "DB_HOST")
    missing = [key for key in required if not os.getenv(key)]
    if missing:
        raise RuntimeError(f"Variáveis locais ausentes: {', '.join(missing)}")
    return URL.create(
        "postgresql+psycopg2",
        username=os.environ["DB_USUARIO"],
        password=os.environ["DB_SENHA"],
        host=os.environ["DB_HOST"],
        port=int(os.getenv("DB_PORT", "5432")),
        database="cei",
    )


@contextmanager
def _read_only_connection() -> Iterator[Connection]:
    engine = create_engine(
        _database_url(),
        connect_args={
            "options": "-c default_transaction_read_only=on -c statement_timeout=180000"
        },
    )
    try:
        with engine.connect() as connection:
            transaction = connection.begin()
            try:
                connection.execute(text("SET TRANSACTION READ ONLY"))
                mode = connection.execute(
                    text("SELECT current_setting('transaction_read_only')")
                ).scalar_one()
                if mode != "on":
                    raise RuntimeError("A conexão CEI não está em modo somente leitura.")
                yield connection
            finally:
                transaction.rollback()
    finally:
        engine.dispose()


def _catalogs_and_state_sector() -> tuple[
    pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any]
]:
    with _read_only_connection() as connection:
        cnae_raw = pd.read_sql_query(
            text(
                """
                SELECT cod_subclasse AS cnae_subclass_code_raw,
                       subclasse AS cnae_subclass_label,
                       cod_divisao AS cnae_division_code_raw,
                       divisao AS cnae_division_label
                FROM public.cnae
                ORDER BY cod_subclasse
                """
            ),
            connection,
        )
        occupation_raw = pd.read_sql_query(
            text(
                """
                SELECT cod_ocupacao AS occupation_code_raw,
                       desc_ocupacao AS occupation_label
                FROM public.ocupacao
                ORDER BY cod_ocupacao
                """
            ),
            connection,
        )
        schooling = pd.read_sql_query(
            text(
                """
                SELECT cod_grau_instrucao AS schooling_code,
                       grau_instrucao_desc AS schooling_label
                FROM public.grau_instrucao
                ORDER BY cod_grau_instrucao
                """
            ),
            connection,
        )
        state_raw = pd.read_sql_query(
            text(
                """
                WITH source_rows AS (
                    SELECT 2019::bigint AS year,
                           cnae_2_subclasse AS cnae_subclass_code_raw,
                           SUM(vinculos_ativos)::bigint AS active_bonds
                    FROM public.rais_vinculos_ocupacao
                    WHERE ano = 2019
                    GROUP BY cnae_2_subclasse
                    UNION ALL
                    SELECT 2025::bigint AS year,
                           cnae_2_subclasse AS cnae_subclass_code_raw,
                           SUM(vinculos_ativos)::bigint AS active_bonds
                    FROM public.rais_ocupacoes_rs_25
                    WHERE ano = 2025
                    GROUP BY cnae_2_subclasse
                )
                SELECT year, cnae_subclass_code_raw, active_bonds
                FROM source_rows
                ORDER BY year, cnae_subclass_code_raw NULLS LAST
                """
            ),
            connection,
        )

    cnae_rows: list[dict[str, Any]] = []
    for row in cnae_raw.to_dict("records"):
        subclass = normalize_numeric_code(
            row["cnae_subclass_code_raw"], width=7, allow_all=False
        )
        declared_division = normalize_numeric_code(
            row["cnae_division_code_raw"], width=2, allow_all=False
        )
        derived_division = subclass[:2]
        if declared_division != derived_division:
            raise ValueError(
                f"Catálogo CNAE inconsistente: {subclass} -> {declared_division}/{derived_division}."
            )
        cnae_rows.append(
            {
                "cnae_subclass_code": subclass,
                "cnae_subclass_label": row["cnae_subclass_label"],
                "cnae_division_code": derived_division,
                "cnae_division_label": row["cnae_division_label"],
            }
        )
    cnae = (
        pd.DataFrame(cnae_rows)
        .drop_duplicates()
        .sort_values(["cnae_subclass_code"], kind="mergesort")
        .reset_index(drop=True)
    )
    if cnae["cnae_subclass_code"].duplicated().any():
        raise ValueError("O catálogo CNAE normalizado contém subclasses duplicadas.")

    occupation_rows = [
        {
            "occupation_code": normalize_numeric_code(
                row["occupation_code_raw"], width=6, allow_all=False
            ),
            "occupation_label": row["occupation_label"],
        }
        for row in occupation_raw.to_dict("records")
    ]
    occupation = (
        pd.DataFrame(occupation_rows)
        .drop_duplicates()
        .sort_values(["occupation_code"], kind="mergesort")
        .reset_index(drop=True)
    )
    if occupation["occupation_code"].duplicated().any():
        raise ValueError("O catálogo CBO normalizado contém códigos duplicados.")

    schooling["schooling_code"] = schooling["schooling_code"].astype("string").str.strip()
    schooling = (
        schooling.drop_duplicates()
        .sort_values(["schooling_code"], kind="mergesort")
        .reset_index(drop=True)
    )
    if schooling["schooling_code"].duplicated().any():
        raise ValueError("O catálogo local de escolaridade contém códigos duplicados.")

    reference_totals = {2019: 0, 2025: 0}
    analyzed_totals = {2019: 0, 2025: 0}
    excluded_bonds = {2019: 0, 2025: 0}
    excluded_codes: set[str] = set()
    normalized_state_rows: list[dict[str, Any]] = []
    for row in state_raw.to_dict("records"):
        year = int(row["year"])
        bonds = int(row["active_bonds"] or 0)
        reference_totals[year] += bonds
        raw = row["cnae_subclass_code_raw"]
        try:
            subclass = normalize_numeric_code(
                raw, width=7, allow_all=False, nullable=False
            )
        except ValueError:
            excluded_codes.add("<NULL>" if raw is None or pd.isna(raw) else str(raw))
            excluded_bonds[year] += bonds
            continue
        analyzed_totals[year] += bonds
        normalized_state_rows.append(
            {
                "year": year,
                "cnae_division_code": subclass[:2],
                "active_bonds": bonds,
            }
        )
    state = (
        pd.DataFrame(normalized_state_rows)
        .groupby(["year", "cnae_division_code"], as_index=False, dropna=False)[
            "active_bonds"
        ]
        .sum()
    )
    for year in (2019, 2025):
        if excluded_bonds[year] != 0:
            state.loc[len(state)] = {
                "year": year,
                "cnae_division_code": "EXCLUDED_INVALID_CNAE",
                "active_bonds": excluded_bonds[year],
            }
    state = state.sort_values(
        ["year", "cnae_division_code"], kind="mergesort"
    ).reset_index(drop=True)
    observed_reference = state.groupby("year")["active_bonds"].sum().astype(int).to_dict()
    if observed_reference != reference_totals:
        raise ValueError("O total estadual de referência não fecha com a extração bruta.")
    audit = {
        "referenceTotalScope": (
            "all rows from the same frozen RAIS source tables/version after raw subclass aggregation"
        ),
        "analyzedSectorScope": (
            "valid numeric CNAE subclasses normalized to seven digits and aggregated to division"
        ),
        "excludedSectorCodes": sorted(excluded_codes),
        "excludedSectorBonds": {str(key): value for key, value in excluded_bonds.items()},
        "referenceTotalsByYear": {
            str(key): value for key, value in reference_totals.items()
        },
        "analyzedTotalsByYear": {
            str(key): value for key, value in analyzed_totals.items()
        },
        "comparisonUsesSameSourceVersion": True,
        "referenceFrozenBeforeCalculation": True,
        "periods": [2019, 2025],
        "databaseMode": "read_only_transaction",
        "databaseWrites": False,
    }
    return cnae, occupation, schooling, state, audit


def _validate_output_path(output: Path) -> None:
    assert_outside_public_data(output, REPO_ROOT)
    allowed_root = (REPO_ROOT / ".tmp" / "vocacoes-pne").resolve()
    if output == allowed_root or allowed_root not in output.parents:
        raise ValueError("A saída 5G-C-R deve ser um subdiretório de .tmp/vocacoes-pne.")
    if output == SOURCE_JOB5GC_ROOT.resolve():
        raise ValueError("O novo staging não pode substituir o Job 5G-C congelado.")


def _remove_generated_stage(stage: Path) -> None:
    resolved = stage.resolve()
    allowed_root = (REPO_ROOT / ".tmp" / "vocacoes-pne").resolve()
    if allowed_root not in resolved.parents or not resolved.name.startswith(".v7-job5gcr"):
        raise ValueError(f"Recusa de remover staging fora do escopo: {resolved}")
    if resolved.exists():
        shutil.rmtree(resolved)


def _activate_stage(stage: Path, target: Path) -> str:
    if target.exists() and directory_content_digest(stage) == directory_content_digest(target):
        _remove_generated_stage(stage)
        return "unchanged"
    backup = target.parent / f".{target.name}.job5gcr-backup"
    if backup.exists():
        raise FileExistsError(f"Backup residual exige inspeção: {backup}")
    moved_old = False
    try:
        if target.exists():
            os.replace(target, backup)
            moved_old = True
        os.replace(stage, target)
        if moved_old:
            shutil.rmtree(backup)
        return "replaced"
    except Exception:
        if target.exists() and target != stage:
            shutil.rmtree(target)
        if moved_old and backup.exists():
            os.replace(backup, target)
        raise


def _new_empty_stage(output: Path) -> Path:
    stage = staging_directory_for(output)
    stage.rmdir()
    return stage


def _generate(
    *,
    output: Path,
    contract: Mapping[str, Any],
    inputs: Mapping[str, Path],
    municipality_names: Mapping[str, str],
    original_integrity: Mapping[str, Any],
    cnae_catalog: pd.DataFrame,
    occupation_catalog: pd.DataFrame,
    schooling_catalog: pd.DataFrame,
    state_sector_totals: pd.DataFrame,
    state_sector_audit: Mapping[str, Any],
) -> dict[str, Any]:
    bridge_contract = _json(inputs["bridge_contract"])
    stages = [_new_empty_stage(output), _new_empty_stage(output)]
    try:
        manifests = []
        validations = []
        for stage in stages:
            manifests.append(
                write_package(
                    output_dir=stage,
                    source_job5gc_root=SOURCE_JOB5GC_ROOT,
                    inputs=inputs,
                    state_sector_totals=state_sector_totals,
                    state_sector_audit=state_sector_audit,
                    municipality_names=municipality_names,
                    cnae_catalog=cnae_catalog,
                    occupation_catalog=occupation_catalog,
                    schooling_catalog=schooling_catalog,
                    bridge_contract=bridge_contract,
                    contract=contract,
                    original_integrity=original_integrity,
                )
            )
            validations.append(validate_existing_output(stage))
        first_digest = directory_content_digest(stages[0])
        second_digest = directory_content_digest(stages[1])
        if first_digest != second_digest:
            raise ValueError(
                f"A materialização não foi determinística: {first_digest} != {second_digest}."
            )
        _remove_generated_stage(stages[1])
        activation = _activate_stage(stages[0], output)
        final_validation = validate_existing_output(output)
        return {
            "manifest": manifests[0],
            "validation": final_validation,
            "determinismSha256": first_digest,
            "stagingActivation": activation,
            "replicateValidations": validations,
        }
    except Exception:
        for stage in stages:
            if stage.exists():
                _remove_generated_stage(stage)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    output = args.output.resolve()
    _validate_output_path(output)
    contract = _json(CONTRACT_PATH)
    inputs = _inputs()
    _verify_local_inputs(inputs)
    verify_checkpoints(REPO_ROOT, contract)
    original_before = verify_original_job5gc(
        SOURCE_JOB5GC_ROOT,
        contract["checkpoints"][".tmp/vocacoes-pne/v7-job5gc/MANIFEST_JOB5GC.json"],
    )
    if args.validate_only:
        validation = validate_existing_output(output)
        print(
            json.dumps(
                {
                    **validation,
                    "output": str(output),
                    "originalJob5GCIntegrity": original_before["sha256"],
                    "validationOnly": True,
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 0

    load_dotenv(DATA_PIPELINE_DIR / ".env")
    municipality_names = _load_municipalities()
    (
        cnae_catalog,
        occupation_catalog,
        schooling_catalog,
        state_sector_totals,
        state_sector_audit,
    ) = _catalogs_and_state_sector()
    result = _generate(
        output=output,
        contract=contract,
        inputs=inputs,
        municipality_names=municipality_names,
        original_integrity=original_before,
        cnae_catalog=cnae_catalog,
        occupation_catalog=occupation_catalog,
        schooling_catalog=schooling_catalog,
        state_sector_totals=state_sector_totals,
        state_sector_audit=state_sector_audit,
    )
    verify_checkpoints(REPO_ROOT, contract)
    original_after = verify_original_job5gc(
        SOURCE_JOB5GC_ROOT,
        contract["checkpoints"][".tmp/vocacoes-pne/v7-job5gc/MANIFEST_JOB5GC.json"],
    )
    if original_after != original_before:
        raise ValueError("O pacote original 5G-C mudou durante a correção dirigida.")
    manifest = result["manifest"]
    print(
        json.dumps(
            {
                "finalState": FINAL_STATE,
                "output": str(output),
                "outputCount": manifest["summary"]["outputCount"],
                "artifactHashCount": manifest["summary"]["artifactHashCount"],
                "manifestSha256": result["validation"]["manifestSha256"],
                "determinismSha256": result["determinismSha256"],
                "originalJob5GCIntegrity": original_before["sha256"],
                "stagingActivation": result["stagingActivation"],
                "databaseMode": "read_only_transaction",
                "networkUsed": False,
                "publicDataChanged": False,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
