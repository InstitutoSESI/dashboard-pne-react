import { useEffect, useId, useRef, useState, type KeyboardEvent, type ReactNode, type Ref } from 'react'
import {
  ArrowLeft,
  ChartSpline,
  Check,
  ChevronDown,
  Clock3,
  FileText,
  House,
  List,
  SlidersHorizontal,
  UsersRound,
  type LucideIcon,
} from 'lucide-react'
import { EducationDomainIcon, isEducationDomain } from '../../../components/icons/EducationDomainIcon'
import { NavGlyphIcon, isNavGlyphName } from '../../../components/icons/NavGlyphIcon'

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
  domain?: string
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
  domain,
  eyebrow = 'Indicadores de Educação',
  headingRef,
  title,
  variant = 'section',
}: EducationCompactHeaderProps) {
  const inlineBackLink = variant === 'detail' ? undefined : backLink
  const visualVariant = variant === 'section' ? 'listing' : 'detail'
  const passiveContextItems = contextItems.filter((item) => !(
    item.options?.length && item.selectedKey && item.onSelect
  ))
  const interactiveContextItems = contextItems.filter((item) => (
    item.options?.length && item.selectedKey && item.onSelect
  ))

  return (
    <header className={`education-compact-header education-compact-header--${variant} platform-page-header platform-page-header--${visualVariant}${className ? ` ${className}` : ''}`}>
      <div className="education-compact-header__copy">
        {backLink && !inlineBackLink ? <EducationHeaderBackLink backLink={backLink} /> : null}
        <span className="education-compact-header__eyebrow">
          {isEducationDomain(domain)
            ? <EducationDomainIcon domain={domain} size="md" />
            : isNavGlyphName(domain)
              ? <NavGlyphIcon name={domain} size="md" />
              : null}
          {eyebrow}
        </span>
        <h1 ref={headingRef} tabIndex={-1}>{title}</h1>
        {description ? <p className="education-compact-header__description">{description}</p> : null}
      </div>

      {contextItems.length || action || inlineBackLink ? (
        <div className="education-compact-header__context-row">
          {contextItems.length ? (
            <div className="education-compact-header__context" aria-label="Contexto desta página">
              {passiveContextItems.length ? (
                <div className="education-compact-header__context-summary">
                  {passiveContextItems.map((item, index) => (
                    <span key={item.key ?? `${item.label}-${String(item.value)}`}>
                      {index ? <span aria-hidden="true"> · </span> : null}
                      {item.label === 'Escopo' ? item.value : <>{item.label}: {item.value}</>}
                    </span>
                  ))}
                </div>
              ) : null}
              {interactiveContextItems.map((item) => (
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
        <ChevronDown aria-hidden="true" className="education-context-chip__chevron" />
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
              {option.key === item.selectedKey ? <span aria-hidden="true"><Check /></span> : null}
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
      <ArrowLeft aria-hidden="true" />
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
  const icons: Record<EducationContextIcon, LucideIcon> = {
    municipality: House,
    section: List,
    scope: UsersRound,
    period: Clock3,
    cut: SlidersHorizontal,
    source: FileText,
    projection: ChartSpline,
  }
  const Icon = icons[name]

  return <Icon aria-hidden="true" strokeWidth={1.7} />
}
