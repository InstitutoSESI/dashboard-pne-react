import {
  forwardRef,
  useEffect,
  useId,
  useImperativeHandle,
  useMemo,
  useRef,
  useState,
  type ChangeEvent,
  type KeyboardEvent,
  type MouseEvent,
  type ReactNode,
} from 'react'
import { ChevronDown, X } from 'lucide-react'
import { ACTIVE_STATE_CONFIG } from '../config/stateConfig'
import {
  filterMunicipalitiesByName,
  normalizeMunicipalitySearchText,
  sortMunicipalitiesByName,
} from '../domain/municipalitySelectorModel'
import type { MunicipalityId, MunicipalityRef } from '../types/data'

export interface MunicipalitySelectorHandle {
  click: () => void
  focus: () => void
}

export interface MunicipalitySelectorProps {
  className?: string
  municipalities: MunicipalityRef[]
  selectedMunicipalityId: MunicipalityId | null
  onChange: (value: MunicipalityId | null) => void
  variant?: 'default' | 'hero'
  placeholder?: string
}

export const MunicipalitySelector = forwardRef<
  MunicipalitySelectorHandle,
  MunicipalitySelectorProps
>(function MunicipalitySelector(
  {
    className = '',
    municipalities,
    selectedMunicipalityId,
    onChange,
    variant = 'default',
    placeholder = 'Buscar município',
  },
  ref,
) {
  const isHero = variant === 'hero'
  const instanceId = useId().replace(/:/g, '')
  const inputId = `municipio-selector-input-${instanceId}`
  const listboxId = `municipio-selector-listbox-${instanceId}`

  const [query, setQuery] = useState('')
  const [isOpen, setIsOpen] = useState(false)
  const [activeIndex, setActiveIndex] = useState(0)

  const inputRef = useRef<HTMLInputElement>(null)
  const containerRef = useRef<HTMLLabelElement>(null)
  const listboxRef = useRef<HTMLUListElement>(null)

  useImperativeHandle(ref, () => ({
    focus: () => inputRef.current?.focus(),
    click: () => inputRef.current?.click(),
  }))

  const list = useMemo(
    () => sortMunicipalitiesByName(
      Array.isArray(municipalities) ? municipalities : [],
      ACTIVE_STATE_CONFIG.locale,
    ),
    [municipalities],
  )
  const selectedMunicipality = useMemo(
    () => list.find((municipality) => municipality.ibgeCode === selectedMunicipalityId) ?? null,
    [list, selectedMunicipalityId],
  )

  const filtered = useMemo(() => {
    return filterMunicipalitiesByName(list, query, ACTIVE_STATE_CONFIG.locale)
  }, [list, query])

  const optionId = (municipality: MunicipalityRef) => (
    `municipio-option-${instanceId}-${municipality.ibgeCode}`
  )

  useEffect(() => {
    if (activeIndex >= filtered.length) {
      setActiveIndex(Math.max(0, filtered.length - 1))
    }
  }, [activeIndex, filtered.length])

  useEffect(() => {
    if (!isOpen || filtered.length === 0) return
    listboxRef.current?.children[activeIndex]?.scrollIntoView({ block: 'nearest' })
  }, [activeIndex, filtered.length, isOpen])

  useEffect(() => {
    if (!isOpen) return undefined
    function handleClickOutside(event: globalThis.MouseEvent) {
      if (
        containerRef.current
        && event.target instanceof Node
        && !containerRef.current.contains(event.target)
      ) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [isOpen])

  function commit(municipality: MunicipalityRef | undefined) {
    if (!municipality) return
    onChange(municipality.ibgeCode)
    setQuery('')
    setIsOpen(false)
    setActiveIndex(0)
    inputRef.current?.blur()
  }

  function handleInputChange(event: ChangeEvent<HTMLInputElement>) {
    setQuery(event.target.value)
    setIsOpen(true)
    setActiveIndex(0)
  }

  function handleKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === 'ArrowDown') {
      event.preventDefault()
      if (!isOpen) setIsOpen(true)
      setActiveIndex((index) => Math.min(filtered.length - 1, index + 1))
    } else if (event.key === 'ArrowUp') {
      event.preventDefault()
      setActiveIndex((index) => Math.max(0, index - 1))
    } else if (event.key === 'Enter') {
      if (isOpen && filtered.length > 0) {
        event.preventDefault()
        commit(filtered[activeIndex])
      }
    } else if (event.key === 'Escape') {
      setIsOpen(false)
    } else if (event.key === 'Backspace' && query === '' && selectedMunicipalityId) {
      onChange(null)
    }
  }

  const displayValue = isOpen ? query : selectedMunicipality?.name ?? ''
  const showPlaceholder = !displayValue

  return (
    <label
      ref={containerRef}
      className={`municipio-selector platform-selector ${isHero ? 'municipio-selector--hero' : ''} ${selectedMunicipality ? 'is-selected' : ''} ${className} ${isOpen ? 'is-open' : ''}`}
    >
      <span className="municipio-selector__label">Município</span>
      <div className="municipio-selector__field">
        <input
          id={inputId}
          ref={inputRef}
          type="text"
          role="combobox"
          aria-label="Município"
          aria-expanded={isOpen}
          aria-autocomplete="list"
          aria-controls={listboxId}
          aria-activedescendant={
            isOpen && filtered[activeIndex]
              ? optionId(filtered[activeIndex])
              : undefined
          }
          className="municipio-selector__input"
          value={displayValue}
          placeholder={showPlaceholder ? placeholder : ''}
          onChange={handleInputChange}
          onFocus={() => setIsOpen(true)}
          onKeyDown={handleKeyDown}
          autoComplete="off"
          spellCheck={false}
        />
        {selectedMunicipality && !isOpen ? (
          <button
            type="button"
            className="municipio-selector__clear"
            aria-label="Limpar seleção"
            onClick={(event: MouseEvent<HTMLButtonElement>) => {
              event.stopPropagation()
              onChange(null)
              setQuery('')
              inputRef.current?.focus()
            }}
          >
            <X aria-hidden="true" size={14} />
          </button>
        ) : null}
        <button
          type="button"
          className="municipio-selector__chevron-btn"
          aria-label="Abrir lista de municípios"
          tabIndex={-1}
          onClick={() => {
            if (isOpen) {
              setIsOpen(false)
            } else {
              setIsOpen(true)
              inputRef.current?.focus()
            }
          }}
        >
          <ChevronDown aria-hidden="true" className="municipio-selector__chevron" strokeWidth={1.7} />
        </button>
        {isOpen ? (
          <ul
            id={listboxId}
            ref={listboxRef}
            role="listbox"
            className="municipio-selector__listbox"
          >
            {filtered.length === 0 ? (
              <li className="municipio-selector__empty">Nenhum município encontrado.</li>
            ) : (
              filtered.map((municipality, index) => (
                <li
                  key={municipality.ibgeCode}
                  id={optionId(municipality)}
                  role="option"
                  aria-selected={municipality.ibgeCode === selectedMunicipalityId}
                  className={
                    index === activeIndex
                      ? 'municipio-selector__option is-active'
                      : 'municipio-selector__option'
                  }
                  onMouseDown={(event: MouseEvent<HTMLLIElement>) => {
                    event.preventDefault()
                  }}
                  onClick={(event: MouseEvent<HTMLLIElement>) => {
                    event.preventDefault()
                    event.stopPropagation()
                    commit(municipality)
                  }}
                  onMouseEnter={() => setActiveIndex(index)}
                >
                  {highlightMatch(municipality.name, query)}
                </li>
              ))
            )}
          </ul>
        ) : null}
      </div>
    </label>
  )
})

function highlightMatch(text: string, query: string): ReactNode {
  const normalizedQuery = normalizeMunicipalitySearchText(query, ACTIVE_STATE_CONFIG.locale)
  if (!normalizedQuery) return text
  const normalizedText = text.normalize('NFD').replace(/\p{Diacritic}/gu, '')
  const lowerText = normalizedText.toLocaleLowerCase('pt-BR')
  const matchIndex = lowerText.indexOf(normalizedQuery)
  if (matchIndex < 0) return text
  return (
    <>
      {text.slice(0, matchIndex)}
      <mark className="municipio-selector__match">
        {text.slice(matchIndex, matchIndex + normalizedQuery.length)}
      </mark>
      {text.slice(matchIndex + normalizedQuery.length)}
    </>
  )
}
