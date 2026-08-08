"""Amostras de QA por estado, sempre reconciliadas com o registro ativo.

Uma amostra de QA não é identidade nem dado analítico: é um recorte de auditoria.
Mesmo assim ela não pode ser um código solto no meio de um script. Aqui existem
dois mecanismos distintos:

- **âncora estadual**: a capital da UF. Não há como derivá-la do registro (o
  registro não sabe qual município é capital), então ela é declarada uma vez por
  estado e validada contra o registro ativo antes de qualquer uso.
- **amostras derivadas**: obtidas do próprio registro por uma regra determinística
  (primeiro código, âncora, último código), sem lista fixa por estado.

Um estado sem âncora declarada falha em vez de herdar a do Rio Grande do Sul.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from .municipality_registry import MunicipalityRegistry
from .state_config import StateConfig


class StateQaSampleError(ValueError):
    """Indica que a amostra de QA não pode ser resolvida para o estado."""


@dataclass(frozen=True, slots=True)
class StateQaAnchor:
    """Município de referência das auditorias; `role` é rótulo público."""

    role: str
    municipality_id: str


STATE_QA_ANCHORS: Mapping[str, StateQaAnchor] = {
    "RS": StateQaAnchor(role="porto_alegre", municipality_id="4314902"),
    "AL": StateQaAnchor(role="maceio", municipality_id="2704302"),
}


def _known_ids(universe: MunicipalityRegistry | Iterable[str]) -> frozenset[str]:
    if isinstance(universe, MunicipalityRegistry):
        return frozenset(universe.ids)
    return frozenset(universe)


def resolve_state_qa_anchor(
    state_config: StateConfig,
    universe: MunicipalityRegistry | Iterable[str] | None = None,
) -> StateQaAnchor:
    """Resolve a âncora declarada e prova que ela existe no universo ativo."""
    anchor = STATE_QA_ANCHORS.get(state_config.state_code)
    if anchor is None:
        raise StateQaSampleError(
            "Nenhuma âncora de QA declarada para "
            f"{state_config.state_code}; declare-a em STATE_QA_ANCHORS antes de "
            "auditar este estado."
        )
    if not anchor.municipality_id.startswith(state_config.municipality_ibge_prefix):
        raise StateQaSampleError(
            f"Âncora de QA {anchor.municipality_id} não pertence a "
            f"{state_config.state_code}."
        )
    if universe is not None and anchor.municipality_id not in _known_ids(universe):
        raise StateQaSampleError(
            f"Âncora de QA {anchor.municipality_id} ausente do universo municipal "
            f"de {state_config.state_code}."
        )
    return anchor


def resolve_qa_sample_ids(
    state_config: StateConfig,
    registry: MunicipalityRegistry,
) -> tuple[str, ...]:
    """Amostra determinística do registro: primeiro código, âncora e último."""
    if registry.state_code != state_config.state_code:
        raise StateQaSampleError(
            "Registro municipal e configuração estadual divergem: "
            f"{registry.state_code} != {state_config.state_code}."
        )
    ordered = [record.ibge_code for record in registry.ordered_records]
    if not ordered:
        raise StateQaSampleError("Registro municipal vazio não produz amostra.")
    anchor = resolve_state_qa_anchor(state_config, registry)
    sample: list[str] = []
    for candidate in (ordered[0], anchor.municipality_id, ordered[-1]):
        if candidate not in sample:
            sample.append(candidate)
    return tuple(sample)


__all__ = [
    "STATE_QA_ANCHORS",
    "StateQaAnchor",
    "StateQaSampleError",
    "resolve_qa_sample_ids",
    "resolve_state_qa_anchor",
]
