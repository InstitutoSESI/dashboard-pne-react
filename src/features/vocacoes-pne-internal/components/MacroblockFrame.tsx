import type { KeyboardEvent, ReactNode } from 'react'
import type {
  UiV2Macroblock,
  UiV2Source,
  UiV2VisualContract,
} from '../vocacoesPneUiV2Types'
import { PlanningQuestion, SourceLimitDisclosure } from './VocacoesPneVisuals'

export function MacroblockFrame({
  macroblock,
  visualContract,
  sourceRegistry,
  limits,
  children,
  evidence,
}: {
  macroblock: UiV2Macroblock
  visualContract: UiV2VisualContract
  sourceRegistry: Map<string, UiV2Source>
  limits: Array<{ limitId: string; appliesTo: string; statement: string }>
  children: ReactNode
  evidence?: ReactNode
}) {
  const applicableLimits = limits.filter((item) => (
    item.appliesTo === 'all'
    || item.appliesTo === macroblock.macroblockId
    || macroblock.familyIds.includes(item.appliesTo)
  ))
  return (
    <section
      id={`macro-${macroblock.sequence}`}
      className="vpi-macroblock"
      data-macroblock-id={macroblock.macroblockId}
      aria-labelledby={`macro-${macroblock.sequence}-title`}
    >
      <header className="vpi-macroblock__header">
        <span className="vpi-macroblock__index" aria-hidden="true">{String.fromCharCode(64 + macroblock.sequence)}</span>
        <div>
          <p className="vpi-eyebrow">Macrobloco {macroblock.sequence} de 7</p>
          <h2 id={`macro-${macroblock.sequence}-title`}>{macroblock.title}</h2>
          <p>{macroblock.summary}</p>
        </div>
      </header>
      <div className="vpi-macroblock__primary">{children}</div>
      <PlanningQuestion>{macroblock.primaryQuestion}</PlanningQuestion>
      {evidence}
      <SourceLimitDisclosure
        sources={sourceRegistry}
        sourceRefs={visualContract.sourceRefs}
        limits={applicableLimits}
      />
    </section>
  )
}

export function TabList<T extends string>({
  label,
  options,
  value,
  onChange,
}: {
  label: string
  options: ReadonlyArray<{ value: T; label: string }>
  value: T
  onChange: (value: T) => void
}) {
  function handleKeyDown(event: KeyboardEvent<HTMLButtonElement>) {
    if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return
    const tabs = Array.from(
      event.currentTarget.parentElement?.querySelectorAll<HTMLButtonElement>('[role="tab"]') ?? [],
    )
    const currentIndex = tabs.indexOf(event.currentTarget)
    if (currentIndex < 0 || tabs.length === 0) return
    event.preventDefault()
    const nextIndex = event.key === 'Home'
      ? 0
      : event.key === 'End'
        ? tabs.length - 1
        : event.key === 'ArrowRight'
          ? (currentIndex + 1) % tabs.length
          : (currentIndex - 1 + tabs.length) % tabs.length
    tabs[nextIndex].focus()
    tabs[nextIndex].click()
  }

  return (
    <div className="vpi-tabs" role="tablist" aria-label={label}>
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          role="tab"
          aria-selected={option.value === value}
          tabIndex={option.value === value ? 0 : -1}
          className={option.value === value ? 'is-active' : ''}
          onClick={() => onChange(option.value)}
          onKeyDown={handleKeyDown}
        >
          {option.label}
        </button>
      ))}
    </div>
  )
}
