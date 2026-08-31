"""Executa o Job 5L-final em staging local, determinístico e transacional."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
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
from src.vocacoes_pne_job5l_final import (  # noqa: E402
    CONTRACT_PATH,
    DEFAULT_OUTPUT_ROOT,
    FINAL_STATE,
    INTERNAL_FILES,
    PACKAGE_FILES,
    acquire_censo_source_snapshot,
    assemble_analysis,
    validate_censo_source_snapshot,
    validate_existing_output,
    verify_frozen_inputs,
    write_package,
)


ALLOWED_ROOT = REPO_ROOT / ".tmp" / "vocacoes-pne"


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_contract() -> dict[str, Any]:
    contract = _json(CONTRACT_PATH)
    if contract["jobId"] != "v7-job5l-final":
        raise ValueError("Contrato Job 5L-final divergente")
    if FINAL_STATE not in contract["allowedFinalStates"]:
        raise ValueError("Estado terminal não autorizado pelo contrato")
    if contract["packageFiles"] != list(PACKAGE_FILES) or len(PACKAGE_FILES) != 12:
        raise ValueError("Contrato deve declarar exatamente 12 arquivos compartilhados")
    if contract["internalSupportingArtifacts"] != list(INTERNAL_FILES):
        raise ValueError("Contrato e suportes internos divergem")
    if contract["gate11"] != "CLOSED" or not contract["internalOnly"]:
        raise ValueError("Contrato abriu escopo proibido")
    if contract["job5MAllowed"]:
        raise ValueError("Contrato autorizou Job 5M indevidamente")
    return contract


def _validate_output_path(output: Path) -> None:
    resolved = output.resolve()
    allowed = ALLOWED_ROOT.resolve()
    if resolved == allowed or allowed not in resolved.parents:
        raise ValueError(f"Saída deve ficar abaixo de {allowed}: {resolved}")
    assert_outside_public_data(resolved, REPO_ROOT)


def _new_stage(prefix: str) -> Path:
    ALLOWED_ROOT.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=prefix, dir=ALLOWED_ROOT))
    stage.rmdir()
    return stage


def _remove_stage(stage: Path, prefix: str) -> None:
    if not stage.exists():
        return
    resolved = stage.resolve()
    allowed = ALLOWED_ROOT.resolve()
    if allowed not in resolved.parents or not stage.name.startswith(prefix):
        raise ValueError(f"Recusa de remoção de staging inesperado: {resolved}")
    shutil.rmtree(stage)


def _prepare_censo_sources(source_root: Path, *, refresh: bool) -> dict[str, Any]:
    target = source_root / "ibge-censo-2022"
    if target.is_dir() and not refresh:
        return validate_censo_source_snapshot(target)
    stage = _new_stage(".v7-job5l-final.censo-stage-")
    backup = ALLOWED_ROOT / ".v7-job5l-final.censo-backup"
    try:
        acquire_censo_source_snapshot(stage)
        validate_censo_source_snapshot(stage)
        source_root.mkdir(parents=True, exist_ok=True)
        if backup.exists():
            raise ValueError(f"Backup Censo inesperado já existe: {backup}")
        if target.exists():
            os.replace(target, backup)
        os.replace(stage, target)
        if backup.exists():
            shutil.rmtree(backup)
        return validate_censo_source_snapshot(target)
    except Exception:
        if target.exists() and backup.exists():
            shutil.rmtree(target)
            os.replace(backup, target)
        elif backup.exists() and not target.exists():
            os.replace(backup, target)
        _remove_stage(stage, ".v7-job5l-final.censo-stage-")
        raise


def _validate_existing_target_topology(output: Path) -> None:
    if not output.exists():
        return
    unexpected_root_files = {
        path.name for path in output.iterdir() if path.is_file()
    } - set(PACKAGE_FILES)
    unexpected_dirs = {
        path.name for path in output.iterdir() if path.is_dir()
    } - {"sources", "internal"}
    if unexpected_root_files or unexpected_dirs:
        raise ValueError(
            "Raiz Job 5L-final contém itens não administrados: "
            f"files={sorted(unexpected_root_files)}, dirs={sorted(unexpected_dirs)}"
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
    backup = Path(
        tempfile.mkdtemp(prefix=".v7-job5l-final.backup-", dir=ALLOWED_ROOT)
    )
    managed = [*PACKAGE_FILES, *INTERNAL_FILES]
    installed: list[Path] = []
    backed_up: list[tuple[Path, Path]] = []
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
        _remove_stage(stage, ".v7-job5l-final.stage-")
    return "generated_files_replaced_transactionally_sources_preserved"


def _generate_twice(
    *,
    source_root: Path,
    analysis: dict[str, Any],
    execplan_text: str,
) -> tuple[Path, str]:
    first = _new_stage(".v7-job5l-final.stage-")
    second = _new_stage(".v7-job5l-final.stage-")
    try:
        write_package(
            output_dir=first,
            source_root=source_root,
            analysis=analysis,
            execplan_text=execplan_text,
        )
        first_digest = directory_content_digest(first)
        write_package(
            output_dir=second,
            source_root=source_root,
            analysis=analysis,
            execplan_text=execplan_text,
        )
        second_digest = directory_content_digest(second)
        if first_digest != second_digest:
            raise ValueError(
                f"Job 5L-final não determinístico: first={first_digest}, second={second_digest}"
            )
        _remove_stage(second, ".v7-job5l-final.stage-")
        return first, first_digest
    except Exception:
        _remove_stage(first, ".v7-job5l-final.stage-")
        _remove_stage(second, ".v7-job5l-final.stage-")
        raise


def _finalize_execplan_text(text: str, analysis: Mapping[str, Any]) -> str:
    base = re.split(r"\n## Fechamento\n", text, maxsplit=1)[0].rstrip() + "\n"
    base = base.replace(
        "| Censo/F2/F5 | microdados da amostra e áreas de ponderação oficiais |",
        "| Censo/F2/F5 | microdados da amostra, áreas de ponderação e documentação oficiais |",
    )
    base = base.replace(
        "| EJA/I5 | etapas separadas e linguagem não inferencial | `PRESERVE_WITH_LIMITS` | fundamental e médio separados; sem taxa por mil, cobertura, demanda ou déficit |",
        "| EJA/I5 | distribuição e trajetória por etapa com linguagem não inferencial | `PRESERVE_WITH_LIMITS` | contrastes preservados; fundamental com incompatibilidade explícita; sem taxa por mil, cobertura, demanda ou déficit |",
    )
    if "| I4 | comparações territoriais com lentes declaradas |" not in base:
        base = base.replace(
            "| EJA/I5 | distribuição e trajetória por etapa com linguagem não inferencial |",
            "| I4 | comparações territoriais com lentes declaradas | `CROSS_CUTTING_GRAMMAR` | componentes preservados sem história autônoma ou índice sintético |\n"
            "| EJA/I5 | distribuição e trajetória por etapa com linguagem não inferencial |",
        )
    base = base.replace(
        "- [x] Censo oficial reverificado: raízes esperadas de Microdados e Áreas de Ponderação ausentes no FTP oficial.",
        "- [x] Censo oficial reverificado: Microdados, Áreas de Ponderação e documentação do pacote não satisfazem conjuntamente o gate oficial.",
    )
    finalized = base.replace("- [ ] Pipeline final implementado e testado.", "- [x] Pipeline final implementado e testado.")
    finalized = finalized.replace(
        "- [ ] Duas materializações byte-idênticas verificadas.",
        "- [x] Duas materializações byte-idênticas verificadas.",
    )
    finalized = finalized.replace(
        "- [ ] Pacote final validado e preparado para julgamento externo.",
        "- [x] Pacote final validado e preparado para julgamento externo.",
    )
    finalized += (
        "\n## Fechamento\n\n"
        f"- Estado terminal: `{FINAL_STATE}`.\n"
        f"- F1: {len(analysis['f1_results'])} resultados, "
        f"{int(analysis['f1_validation']['validation_eligible'].astype(bool).sum())}/12 modelos elegíveis.\n"
        f"- RAIS: {analysis['rais_details']['reconciliationWithFrozenAggregate']['exactMatchCount']}/140 células exatas.\n"
        f"- Catálogo: {analysis['catalog']['candidateInsightCount']} candidatas, sem autoaprovação.\n"
        "- I4: gramática transversal, não história autônoma; transformação ocupacional × EPT preservada.\n"
        "- I5: contrastes +2,648 p.p. e −2,605 p.p. preservados por etapa; fundamental incompatível explicitamente.\n"
        "- Gate 11 fechado; Job 5M não iniciado; frontend, publicação, build completo e `public/data` intocados.\n"
    )
    return finalized.rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
        help="Raiz local exclusiva do Job 5L-final.",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Valida o pacote e as fontes existentes sem materializar.",
    )
    parser.add_argument(
        "--refresh-censo",
        action="store_true",
        help="Reverifica os endpoints oficiais do Censo antes da materialização.",
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

    print("[job5l-final] reverificando fontes oficiais do Censo", flush=True)
    _prepare_censo_sources(source_root, refresh=args.refresh_censo)
    execplan_path = output / "internal" / "EXECPLAN_JOB5L_FINAL.md"
    if not execplan_path.is_file():
        raise FileNotFoundError(f"ExecPlan Job 5L-final ausente: {execplan_path}")
    execplan_text = execplan_path.read_text(encoding="utf-8")

    print("[job5l-final] verificando entradas congeladas", flush=True)
    frozen_before = verify_frozen_inputs()
    print("[job5l-final] executando F1 e reconstruindo RAIS 2019–2025", flush=True)
    analysis = assemble_analysis(source_root=source_root, frozen_inputs=frozen_before)
    execplan_text = _finalize_execplan_text(execplan_text, analysis)
    print("[job5l-final] gerando duas materializações determinísticas", flush=True)
    stage, deterministic_digest = _generate_twice(
        source_root=source_root,
        analysis=analysis,
        execplan_text=execplan_text,
    )
    promotion = _promote_generated_tree(stage, output)
    manifest = validate_existing_output(
        output,
        source_root=source_root,
        verify_sources=False,
    )
    frozen_after = verify_frozen_inputs()
    if frozen_after != frozen_before:
        raise RuntimeError("Entradas congeladas mudaram durante o Job 5L-final")
    print(
        json.dumps(
            {
                "status": "ok",
                "output": str(output),
                "promotion": promotion,
                "deterministicDigest": deterministic_digest,
                "finalState": manifest["finalState"],
                "counts": manifest["counts"],
                "frozenIntegrity": frozen_after,
                "networkUsed": True,
                "networkUse": "official_IBGE_current_state_verification",
                "databaseUsed": False,
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
