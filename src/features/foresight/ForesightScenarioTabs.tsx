import { useCallback, useRef } from 'react'
import type { ForesightScenario } from './foresightTypes'

/*
 * Abas dos quatro cenários.
 *
 * Todas têm o mesmo peso: mesma tipografia, mesma cor, mesma borda. A aba ativa
 * se distingue apenas por contraste de superfície, nunca por juízo de valor —
 * nada de verde para "bom" ou vermelho para "ruim", nada de ordem numérica.
 *
 * Teclado: tabindex móvel, setas para andar entre as abas, Home e End para os
 * extremos, exatamente como o padrão de abas manuais prevê.
 */

const TAB_ID_PREFIX = 'cenario-aba'
const PANEL_ID_PREFIX = 'cenario-painel'

export function foresightTabId(slug: string): string {
  return `${TAB_ID_PREFIX}-${slug}`
}

export function foresightPanelId(slug: string): string {
  return `${PANEL_ID_PREFIX}-${slug}`
}

export function ForesightScenarioTabs({
  onSelect,
  scenarios,
  selectedSlug,
}: {
  onSelect: (slug: string) => void
  scenarios: readonly ForesightScenario[]
  selectedSlug: string
}) {
  const listRef = useRef<HTMLDivElement | null>(null)

  const focusTab = useCallback((slug: string) => {
    const target = listRef.current?.querySelector<HTMLButtonElement>(`#${CSS.escape(foresightTabId(slug))}`)
    target?.focus()
  }, [])

  const handleKeyDown = useCallback((event: React.KeyboardEvent<HTMLDivElement>) => {
    const currentIndex = scenarios.findIndex((scenario) => scenario.slug === selectedSlug)
    if (currentIndex < 0) return

    let nextIndex: number | null = null
    if (event.key === 'ArrowRight' || event.key === 'ArrowDown') nextIndex = (currentIndex + 1) % scenarios.length
    if (event.key === 'ArrowLeft' || event.key === 'ArrowUp') nextIndex = (currentIndex - 1 + scenarios.length) % scenarios.length
    if (event.key === 'Home') nextIndex = 0
    if (event.key === 'End') nextIndex = scenarios.length - 1
    if (nextIndex === null) return

    event.preventDefault()
    const next = scenarios[nextIndex]
    onSelect(next.slug)
    focusTab(next.slug)
  }, [focusTab, onSelect, scenarios, selectedSlug])

  return (
    <div
      aria-label="Cenários da educação municipal"
      className="foresight-tabs"
      onKeyDown={handleKeyDown}
      ref={listRef}
      role="tablist"
    >
      {scenarios.map((scenario) => {
        const isSelected = scenario.slug === selectedSlug
        return (
          <button
            aria-controls={foresightPanelId(scenario.slug)}
            aria-selected={isSelected}
            className={isSelected ? 'foresight-tab is-active' : 'foresight-tab'}
            id={foresightTabId(scenario.slug)}
            key={scenario.slug}
            onClick={() => onSelect(scenario.slug)}
            role="tab"
            tabIndex={isSelected ? 0 : -1}
            type="button"
          >
            {scenario.title}
          </button>
        )
      })}
    </div>
  )
}
