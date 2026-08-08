"""Promoção recuperável de lotes de arquivos públicos já validados."""

from __future__ import annotations

import os
import shutil
import tempfile
from collections.abc import Iterable
from pathlib import Path


def _inside(root: Path, candidate: Path) -> bool:
    return candidate == root or root in candidate.parents


def promote_files_atomically(
    stage_root: Path,
    target_root: Path,
    relative_paths: Iterable[Path],
) -> None:
    """Promove arquivos do stage e restaura todo o lote se uma troca falhar."""

    stage = stage_root.resolve()
    target = target_root.resolve()
    paths = tuple(dict.fromkeys(Path(path) for path in relative_paths))
    if not paths:
        raise ValueError("A promoção pública exige ao menos um arquivo.")

    resolved_pairs: list[tuple[Path, Path, Path]] = []
    for relative in paths:
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"Caminho relativo inválido para promoção: {relative}.")
        source = (stage / relative).resolve()
        destination = (target / relative).resolve()
        if not _inside(stage, source) or not _inside(target, destination):
            raise ValueError(f"Caminho escapa da raiz de publicação: {relative}.")
        if not source.is_file():
            raise FileNotFoundError(f"Arquivo validado ausente no stage: {source}.")
        resolved_pairs.append((relative, source, destination))

    target.parent.mkdir(parents=True, exist_ok=True)
    promoted: list[tuple[Path, Path | None]] = []
    with tempfile.TemporaryDirectory(
        prefix=f".{target.name}-publication-backup-",
        dir=target.parent,
    ) as backup_directory:
        backup_root = Path(backup_directory)
        try:
            for relative, source, destination in resolved_pairs:
                destination.parent.mkdir(parents=True, exist_ok=True)
                backup = backup_root / relative
                if destination.exists():
                    backup.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(destination, backup)
                    previous: Path | None = backup
                else:
                    previous = None
                os.replace(source, destination)
                promoted.append((destination, previous))
        except Exception:
            for destination, previous in reversed(promoted):
                if previous is None:
                    destination.unlink(missing_ok=True)
                else:
                    os.replace(previous, destination)
            raise
