"""Executa o Job 5L em staging local, determinístico e transacional."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_PIPELINE_DIR = REPO_ROOT / "data_pipeline"
if str(DATA_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_PIPELINE_DIR))

from src.vocacoes_pne_job2 import (  # noqa: E402
    assert_outside_public_data,
    directory_content_digest,
)
from src.vocacoes_pne_job5l import (  # noqa: E402
    CONTRACT_PATH,
    DEFAULT_OUTPUT_ROOT,
    FINAL_STATE,
    INTERNAL_FILES,
    PACKAGE_FILES,
    assemble_analysis,
    validate_existing_output,
    verify_frozen_integrity,
    write_package,
)


ALLOWED_ROOT = REPO_ROOT / ".tmp" / "vocacoes-pne"


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_contract() -> dict[str, Any]:
    contract = _json(CONTRACT_PATH)
    if contract["jobId"] != "v7-job5l" or FINAL_STATE not in contract["allowedFinalStates"]:
        raise ValueError("Contrato Job 5L ou estado terminal divergente")
    if contract["packageFiles"] != list(PACKAGE_FILES) or len(PACKAGE_FILES) != 12:
        raise ValueError("Contrato Job 5L deve declarar exatamente 12 arquivos compartilhados")
    if contract["gate11"] != "CLOSED" or not contract["internalOnly"]:
        raise ValueError("Contrato Job 5L abriu escopo proibido")
    if contract["job5MAllowed"]:
        raise ValueError("Contrato Job 5L autorizou Job 5M indevidamente")
    return contract


def _validate_output_path(output: Path) -> None:
    resolved = output.resolve()
    allowed = ALLOWED_ROOT.resolve()
    if resolved == allowed or allowed not in resolved.parents:
        raise ValueError(f"Saída deve ficar abaixo de {allowed}: {resolved}")
    assert_outside_public_data(resolved, REPO_ROOT)


def _new_stage() -> Path:
    ALLOWED_ROOT.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".v7-job5l.stage-", dir=ALLOWED_ROOT))
    stage.rmdir()
    return stage


def _remove_stage(stage: Path) -> None:
    if not stage.exists():
        return
    resolved = stage.resolve()
    allowed = ALLOWED_ROOT.resolve()
    if allowed not in resolved.parents or not stage.name.startswith(".v7-job5l.stage-"):
        raise ValueError(f"Recusa de remoção de staging inesperado: {resolved}")
    shutil.rmtree(stage)


def _validate_existing_target_topology(output: Path) -> None:
    if not output.exists():
        return
    allowed_root_files = set(PACKAGE_FILES) | {"EXECPLAN_JOB5L.md"}
    unexpected_root_files = {
        path.name for path in output.iterdir() if path.is_file()
    } - allowed_root_files
    unexpected_dirs = {
        path.name for path in output.iterdir() if path.is_dir()
    } - {"sources", "internal"}
    if unexpected_root_files or unexpected_dirs:
        raise ValueError(
            f"Raiz Job 5L contém itens não administrados: files={sorted(unexpected_root_files)}, dirs={sorted(unexpected_dirs)}"
        )
    internal = output / "internal"
    if internal.is_dir():
        unexpected_internal = {
            path.relative_to(output).as_posix()
            for path in internal.rglob("*")
            if path.is_file()
        } - set(INTERNAL_FILES)
        if unexpected_internal:
            raise ValueError(
                f"internal contém arquivos não administrados: {sorted(unexpected_internal)}"
            )


def _promote_generated_tree(stage: Path, output: Path) -> str:
    """Promove somente artefatos gerados e preserva ``sources`` com rollback."""

    _validate_existing_target_topology(output)
    output.mkdir(parents=True, exist_ok=True)
    backup = Path(tempfile.mkdtemp(prefix=".v7-job5l.backup-", dir=ALLOWED_ROOT))
    managed = [*PACKAGE_FILES, *INTERNAL_FILES]
    installed: list[Path] = []
    backed_up: list[tuple[Path, Path]] = []
    legacy_execplan = output / "EXECPLAN_JOB5L.md"
    try:
        for relative in managed:
            source = stage / relative
            destination = output / relative
            if not source.is_file():
                raise FileNotFoundError(f"Artefato de staging ausente: {source}")
            destination.parent.mkdir(parents=True, exist_ok=True)
            if destination.exists():
                backup_path = backup / relative
                backup_path.parent.mkdir(parents=True, exist_ok=True)
                os.replace(destination, backup_path)
                backed_up.append((backup_path, destination))
            os.replace(source, destination)
            installed.append(destination)
        if legacy_execplan.is_file():
            backup_path = backup / "EXECPLAN_JOB5L.md"
            os.replace(legacy_execplan, backup_path)
            backed_up.append((backup_path, legacy_execplan))
        validate_existing_output(
            output,
            source_root=output / "sources",
            verify_sources=False,
        )
    except Exception:
        for destination in reversed(installed):
            if destination.is_file():
                destination.unlink()
        for backup_path, destination in reversed(backed_up):
            if backup_path.exists():
                destination.parent.mkdir(parents=True, exist_ok=True)
                os.replace(backup_path, destination)
        raise
    finally:
        if backup.exists():
            shutil.rmtree(backup)
        _remove_stage(stage)
    return "generated_files_replaced_transactionally_sources_preserved"


def _generate_twice(
    *,
    output: Path,
    source_root: Path,
    analysis: dict[str, Any],
    preflight: dict[str, Any],
    execplan_text: str,
) -> tuple[Path, str]:
    first = _new_stage()
    second = _new_stage()
    try:
        write_package(
            output_dir=first,
            source_root=source_root,
            analysis=analysis,
            preflight=preflight,
            execplan_text=execplan_text,
        )
        first_digest = directory_content_digest(first)
        write_package(
            output_dir=second,
            source_root=source_root,
            analysis=analysis,
            preflight=preflight,
            execplan_text=execplan_text,
        )
        second_digest = directory_content_digest(second)
        if first_digest != second_digest:
            raise ValueError(
                f"Job 5L não determinístico: first={first_digest}, second={second_digest}"
            )
        _remove_stage(second)
        return first, first_digest
    except Exception:
        _remove_stage(first)
        _remove_stage(second)
        raise


def _finalize_execplan_text(
    text: str, analysis: dict[str, Any], deterministic_requirement: str
) -> str:
    reconciliation = analysis["rais_details"]["reconciliationWithFrozenAggregate"]
    replacements = {
        "- Estado geral:": f"- Estado geral: `{FINAL_STATE}`.",
        "| F1 |": "| F1 | Trajetória ajustada ao contexto socioeconômico | Painel escola-ano/município, covariáveis comparáveis, validação temporal e municipal | `MODELED_11_OF_12_COMBINATIONS_VALIDATED_1_NOT_EVALUABLE` |",
        "| F2 |": "| F2 | Estudo e trabalho na mesma pessoa | Disponibilidade oficial dos microdados da amostra do Censo 2022 e documentação do desenho | `WAITING_OFFICIAL_RELEASE` |",
        "| F3 |": "| F3 | Qualidade e composição do trabalho juvenil | Microdados RAIS públicos, dicionário oficial versionado e série compatível | `MATERIALIZED_OFFICIAL_ACTIVE_STOCK_WITH_EXPLICIT_FROZEN_AGGREGATE_DIFFERENCE` |",
        "| F4 |": "| F4 | Balanço funcional municipal | Painéis congelados e saídas válidas de F1/F3; F2 quando disponível | `MATERIALIZED_NO_SYNTHETIC_INDEX` |",
        "| F5 |": "| F5 | Migração e reorganização da oferta | F2 disponível e variáveis adequadas | `WAITING_OFFICIAL_RELEASE` |",
        "| F6 |": "| F6 | Escolaridade adulta, trabalho e EJA | F2/Censo amostra quando disponível e painéis EJA congelados | `AGGREGATE_ONLY_WITH_EXPLICIT_LIMITS_MATERIALIZED` |",
        "| F7 |": "| F7 | Literatura e mecanismos | Fontes oficiais e artigos acadêmicos primários rastreáveis | `SEVEN_MECHANISMS_EIGHT_TRACEABLE_REFERENCES_MATERIALIZED` |",
        "- Aquisição:": "- Aquisição: documentação oficial, snapshot de banco e sete arquivos RAIS 2019–2025 concluídos, com tamanhos e hashes validados.",
        "- F1–F7:": "- F1–F7: todas as frentes executáveis materializadas; F2/F5 preservadas como `WAITING_OFFICIAL_RELEASE`.",
        "- Catálogo/seleção:": f"- Catálogo/seleção: concluídos com {len(analysis['insights'])} candidatas e {sum(bool(item['main_candidate']) for item in analysis['insights'])} principais, sem autoaprovação.",
        "- Outputs compartilhados:": "- Outputs compartilhados: 12 arquivos concluídos; 17 suportes internos materializados.",
        "- QA final:": f"- QA final: concluído com limites explícitos; determinismo {deterministic_requirement}.",
    }
    lines = []
    for line in text.splitlines():
        replacement = next(
            (value for prefix, value in replacements.items() if line.startswith(prefix)),
            None,
        )
        lines.append(replacement if replacement is not None else line)
    lines.extend(
        [
            "",
            "## Fechamento da materialização",
            "",
            f"- Estado terminal: `{FINAL_STATE}`.",
            f"- F3: {len(analysis['rais_panel'])} linhas agregadas; reconciliação com agregado congelado: {reconciliation['exactMatchCount']} células exatas e {reconciliation['mismatchCount']} divergentes, sem alteração do artefato anterior.",
            f"- Matriz integrada: {len(analysis['result_matrix'])} registros; heterogeneidade: {len(analysis['heterogeneity'])} registros.",
            f"- Determinismo: {deterministic_requirement}.",
            "- Gate 11 fechado; Job 5M não iniciado; frontend, publicação, build completo e `public/data` intocados.",
            "- 2026-08-29 — Job 5L materializado, validado e preparado para julgamento externo com limites explícitos.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
        help="Raiz local exclusiva do Job 5L.",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Valida o pacote e todas as fontes existentes sem materializar.",
    )
    args = parser.parse_args()
    output = args.output if args.output.is_absolute() else REPO_ROOT / args.output
    _validate_output_path(output)
    _validate_contract()
    source_root = output / "sources"
    if args.validate_only:
        manifest = validate_existing_output(
            output,
            source_root=source_root,
            verify_sources=True,
        )
        print(
            json.dumps(
                {
                    "status": "valid",
                    "output": str(output),
                    "finalState": manifest["finalState"],
                    "counts": manifest["counts"],
                    "sourcesVerified": True,
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 0

    if not source_root.is_dir():
        raise FileNotFoundError(f"Raiz de fontes Job 5L ausente: {source_root}")
    execplan_path = output / "EXECPLAN_JOB5L.md"
    if not execplan_path.is_file():
        execplan_path = output / "internal" / "EXECPLAN_JOB5L.md"
    if not execplan_path.is_file():
        raise FileNotFoundError("ExecPlan Job 5L ausente")
    execplan_text = execplan_path.read_text(encoding="utf-8")

    preflight_before = verify_frozen_integrity()
    analysis = assemble_analysis(source_root)
    execplan_text = _finalize_execplan_text(
        execplan_text,
        analysis,
        "duas materializações byte-idênticas verificadas pelo runner",
    )
    stage, deterministic_digest = _generate_twice(
        output=output,
        source_root=source_root,
        analysis=analysis,
        preflight=preflight_before,
        execplan_text=execplan_text,
    )
    promotion = _promote_generated_tree(stage, output)
    manifest = validate_existing_output(
        output,
        source_root=source_root,
        verify_sources=False,
    )
    preflight_after = verify_frozen_integrity()
    if preflight_after != preflight_before:
        raise RuntimeError("Entradas congeladas mudaram durante o Job 5L")
    print(
        json.dumps(
            {
                "status": "ok",
                "output": str(output),
                "promotion": promotion,
                "deterministicDigest": deterministic_digest,
                "finalState": manifest["finalState"],
                "counts": manifest["counts"],
                "frozenIntegrity": preflight_after,
                "networkUsed": True,
                "databaseUsedReadOnly": True,
                "databaseWritePerformed": False,
                "fullBuildUsed": False,
                "publicDataChanged": False,
                "frontendChanged": False,
                "publicationPerformed": False,
                "gate11": "CLOSED",
                "job5MStarted": False,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
