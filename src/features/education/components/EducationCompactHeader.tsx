import { useEffect, useId, useRef, useState, type KeyboardEvent, type ReactNode, type Ref } from 'react'

type EducationHeaderVariant = 'section' | 'detail' | 'scenarios' | 'methodology'

type EducationContextIcon =
  | 'municipality'
  | 'section'
  | 'scope'
  | 'period'
  | 'cut'
  | 'source'
  | 'projection'

interface EducationContextItem {
  icon?: EducationContextIcon
  key?: string
  label: string
  onSelect?: (key: string) => void
  options?: ReadonlyArray<{ key: string; label: string }>
  selectedKey?: string
  value: ReactNode
}

interface EducationBackLink {
  label?: string
  onClick?: () => void
  href?: string
}

interface EducationCompactHeaderProps {
  action?: ReactNode
  backLink?: EducationBackLink
  className?: string
  contextItems?: ReadonlyArray<EducationContextItem>
  description?: ReactNode
  eyebrow?: string
  headingRef?: Ref<HTMLHeadingElement>
  title: ReactNode
  variant?: EducationHeaderVariant
}

export function EducationCompactHeader({
  action,
  backLink,
  className = '',
  contextItems = [],
  description,
  eyebrow = 'Indicadores de Educação',
  headingRef,
  title,
  variant = 'section',
}: EducationCompactHeaderProps) {
  const inlineBackLink = variant === 'detail' ? undefined : backLink
  const visualVariant = variant === 'section' ? 'listing' : 'detail'

  return (
    <header className={`education-compact-header education-compact-header--${variant} platform-page-header platform-page-header--${visualVariant}${className ? ` ${className}` : ''}`}>
      <div className="education-compact-header__copy">
        {backLink && !inlineBackLink ? <EducationHeaderBackLink backLink={backLink} /> : null}
        <span className="education-compact-header__eyebrow">{eyebrow}</span>
        <h1 ref={headingRef} tabIndex={-1}>{title}</h1>
        {description ? <p className="education-compact-header__description">{description}</p> : null}
      </div>

      {contextItems.length || action || inlineBackLink ? (
        <div className="education-compact-header__context-row">
          {contextItems.length ? (
            <div className="education-compact-header__context" aria-label="Contexto desta página">
              {contextItems.map((item) => (
                <EducationContextChip item={item} key={item.key ?? `${item.label}-${String(item.value)}`} />
              ))}
            </div>
          ) : null}
          {action || inlineBackLink ? (
            <div className="education-compact-header__action">
              {action}
              {inlineBackLink ? <EducationHeaderBackLink backLink={inlineBackLink} /> : null}
            </div>
          ) : null}
        </div>
      ) : null}
    </header>
  )
}

function EducationContextChip({ item }: { item: EducationContextItem }) {
  if (item.options?.length && item.selectedKey && item.onSelect) {
    return <EducationContextMenu item={item} />
  }

  return (
    <div className={`education-context-chip${item.label === 'Seção' ? ' education-context-chip--section' : ''}`}>
      <span className="education-context-chip__icon" aria-hidden="true">
        <EducationContextIconGlyph name={item.icon ?? 'scope'} />
      </span>
      <span className="education-context-chip__copy">
        <span className="education-context-chip__label">{item.label}</span>
        <strong className="education-context-chip__value">{item.value}</strong>
      </span>
    </div>
  )
}

function EducationContextMenu({ item }: { item: EducationContextItem }) {
  const [open, setOpen] = useState(false)
  const menuId = useId()
  const rootRef = useRef<HTMLDivElement>(null)
  const triggerRef = useRef<HTMLButtonElement>(null)
  const optionRefs = useRef<Array<HTMLButtonElement | null>>([])
  const selectedIndex = Math.max(0, item.options?.findIndex((option) => option.key === item.selectedKey) ?? 0)

  useEffect(() => {
    if (!open) return undefined

    const closeOnOutsidePointer = (event: PointerEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false)
    }
    const closeOnEscape = (event: globalThis.KeyboardEvent) => {
      if (event.key !== 'Escape') return
      event.preventDefault()
      setOpen(false)
      triggerRef.current?.focus()
    }

    document.addEventListener('pointerdown', closeOnOutsidePointer)
    document.addEventListener('keydown', closeOnEscape)
    return () => {
      document.removeEventListener('pointerdown', closeOnOutsidePointer)
      document.removeEventListener('keydown', closeOnEscape)
    }
  }, [open])

  function openMenu(index = selectedIndex) {
    setOpen(true)
    globalThis.requestAnimationFrame(() => optionRefs.current[index]?.focus())
  }

  function handleTriggerKeyDown(event: KeyboardEvent<HTMLButtonElement>) {
    if (event.key === 'ArrowDown' || event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      openMenu()
    }
  }

  function handleOptionKeyDown(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    const options = item.options ?? []
    let nextIndex: number | null = null
    if (event.key === 'ArrowDown') nextIndex = (index + 1) % options.length
    if (event.key === 'ArrowUp') nextIndex = (index - 1 + options.length) % options.length
    if (event.key === 'Home') nextIndex = 0
    if (event.key === 'End') nextIndex = options.length - 1
    if (nextIndex == null) return
    event.preventDefault()
    optionRefs.current[nextIndex]?.focus()
  }

  return (
    <div className="education-context-chip education-context-chip--menu" ref={rootRef}>
      <span className="education-context-chip__icon" aria-hidden="true">
        <EducationContextIconGlyph name={item.icon ?? 'scope'} />
      </span>
      <button
        aria-controls={menuId}
        aria-expanded={open}
        aria-haspopup="menu"
        className="education-context-chip__menu-trigger"
        onClick={() => setOpen((current) => !current)}
        onKeyDown={handleTriggerKeyDown}
        ref={triggerRef}
        type="button"
      >
        <span className="education-context-chip__copy">
          <span className="education-context-chip__label">{item.label}</span>
          <strong className="education-context-chip__value">{item.value}</strong>
        </span>
        <span aria-hidden="true" className="education-context-chip__chevron">⌄</span>
      </button>
      {open ? (
        <div aria-label={`Selecionar ${item.label.toLocaleLowerCase('pt-BR')}`} className="education-context-chip__menu" id={menuId} role="menu">
          {(item.options ?? []).map((option, index) => (
            <button
              aria-checked={option.key === item.selectedKey}
              className={option.key === item.selectedKey ? 'is-selected' : ''}
              key={option.key}
              onClick={() => {
                item.onSelect?.(option.key)
                setOpen(false)
                triggerRef.current?.focus()
              }}
              onKeyDown={(event) => handleOptionKeyDown(event, index)}
              ref={(node) => { optionRefs.current[index] = node }}
              role="menuitemradio"
              type="button"
            >
              <span>{option.label}</span>
              {option.key === item.selectedKey ? <span aria-hidden="true">✓</span> : null}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  )
}

function EducationHeaderBackLink({ backLink }: { backLink: EducationBackLink }) {
  const content = (
    <>
      <span aria-hidden="true">←</span>
      {backLink.label ?? 'Voltar aos indicadores'}
    </>
  )

  if (backLink.href) {
    return <a className="education-compact-header__back platform-navigation-button" href={backLink.href}>{content}</a>
  }

  return (
    <button className="education-compact-header__back platform-navigation-button" onClick={backLink.onClick} type="button">
      {content}
    </button>
  )
}

function EducationContextIconGlyph({ name }: { name: EducationContextIcon }) {
  const paths: Record<EducationContextIcon, ReactNode> = {
    municipality: <><path d="M4 20h16" /><path d="M6 20V9l6-4 6 4v11" /><path d="M9 20v-5h6v5" /></>,
    section: <><path d="M4 6h16" /><path d="M4 12h16" /><path d="M4 18h10" /></>,
    scope: <><circle cx="9" cy="8" r="3" /><circle cx="17" cy="9" r="2" /><path d="M3 20c.5-4 2.5-6 6-6s5.5 2 6 6" /><path d="M15 15c3 0 5 1.5 6 4" /></>,
    period: <><circle cx="12" cy="12" r="8" /><path d="M12 7v5l3 2" /></>,
    cut: <><path d="M4 7h16" /><path d="M7 4v6" /><path d="M4 17h16" /><path d="M16 14v6" /></>,
    source: <><path d="M5 4h11l3 3v13H5z" /><path d="M16 4v4h4" /><path d="M8 12h8" /><path d="M8 16h6" /></>,
    projection: <><path d="M4 18V6" /><path d="M4 18h16" /><path d="m7 14 4-4 3 2 5-6" /></>,
  }

  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      {paths[name]}
    </svg>
  )
}
