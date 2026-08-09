"""Contexto estadual estrito compartilhado pelos produtos PNE."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .municipality_registry import MunicipalityRegistry, load_municipality_registry
from .state_config import (
    DEFAULT_STATE_CODE,
    StateConfig,
    load_state_config,
    normalize_state_code,
    resolve_pipeline_state_code,
)


_METHODOLOGY_VERSIONS = {
    ("RS", "pne_2014_2024"): "pne2014-rs-reference-v1",
    ("AL", "pne_2014_2024"): "pne2014-al-reference-v1",
    ("RS", "pne_2026_2036"): "pne2026-rs-reference-v3",
    ("AL", "pne_2026_2036"): "pne2026-al-reference-v1",
}


@dataclass(frozen=True, slots=True)
class PneStateContext:
    config: StateConfig
    registry: MunicipalityRegistry

    @property
    def state_code(self) -> str:
        return self.config.state_code

    @property
    def state_name(self) -> str:
        return self.config.state_name

    @property
    def state_id(self) -> str:
        return self.config.municipality_ibge_prefix

    @property
    def expected_municipality_count(self) -> int:
        return self.config.expected_municipality_count

    @property
    def municipality_ids(self) -> frozenset[str]:
        return self.registry.ids

    @property
    def municipality_names(self) -> dict[str, str]:
        return dict(self.registry.names_by_id)

    @property
    def municipality_universe_label(self) -> str:
        return f"Todos os municípios de {self.state_name}"

    def methodology_version(self, cycle: str) -> str:
        try:
            return _METHODOLOGY_VERSIONS[(self.state_code, cycle)]
        except KeyError as exc:
            raise ValueError(
                f"Ciclo PNE {cycle!r} não configurado para {self.state_code}."
            ) from exc


def resolve_pne_state_code(state_code: object | None = None) -> str:
    if state_code is None:
        return resolve_pipeline_state_code()
    normalized = normalize_state_code(state_code)
    load_state_config(normalized)
    return normalized


def load_pne_state_context(
    state_code: object | None = DEFAULT_STATE_CODE,
) -> PneStateContext:
    normalized = resolve_pne_state_code(state_code)
    config = load_state_config(normalized)
    registry = load_municipality_registry(config)
    return PneStateContext(config=config, registry=registry)


def resolve_state_snapshot_dir(
    base_dir: Path,
    state_code: object | None = DEFAULT_STATE_CODE,
) -> Path:
    """Preserva o layout legado do RS e isola as demais UFs em subdiretórios."""

    normalized = resolve_pne_state_code(state_code)
    root = Path(base_dir)
    return root if normalized == DEFAULT_STATE_CODE else root / normalized.lower()


__all__ = [
    "PneStateContext",
    "load_pne_state_context",
    "resolve_pne_state_code",
    "resolve_state_snapshot_dir",
]
