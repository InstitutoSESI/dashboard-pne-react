import { forwardRef, useEffect, useId, useImperativeHandle, useMemo, useRef, useState } from 'react'

function normalizeText(value) {
  return String(value ?? '')
    .normalize('NFD')
    .replace(/\p{Diacritic}/gu, '')
    .toLocaleLowerCase('pt-BR')
    .trim()
}

export const MunicipalitySelector = forwardRef(function MunicipalitySelector(
  {
    className = '',
    municipios,
    selectedMunicipio,
    value,
    onChange,
    variant = 'default',
    placeholder = 'Buscar município',
  },
  ref,
) {
  const current = value ?? selectedMunicipio ?? ''
  const isHero = variant === 'hero'
  const instanceId = useId().replace(/:/g, '')
  const inputId = `municipio-selector-input-${instanceId}`
  const listboxId = `municipio-selector-listbox-${instanceId}`

  const [query, setQuery] = useState('')
  const [isOpen, setIsOpen] = useState(false)
  const [activeIndex, setActiveIndex] = useState(0)

  const inputRef = useRef(null)
  const containerRef = useRef(null)
  const listboxRef = useRef(null)

  useImperativeHandle(ref, () => ({
    focus: () => inputRef.current?.focus(),
    click: () => inputRef.current?.click(),
  }))

  const list = useMemo(() => (
    Array.isArray(municipios)
      ? [...municipios].sort((left, right) => left.localeCompare(right, 'pt-BR', { sensitivity: 'base' }))
      : []
  ), [municipios])

  const filtered = useMemo(() => {
    const q = normalizeText(query)
    return q
      ? list.filter((municipio) => normalizeText(municipio).includes(q))
      : list
  }, [list, query])

  const optionId = (municipio) => `municipio-option-${instanceId}-${normalizeText(municipio).replace(/[^a-z0-9]+/g, '-')}`

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
    function handleClickOutside(event) {
      if (containerRef.current && !containerRef.current.contains(event.target)) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [isOpen])

  function commit(municipio) {
    if (!municipio) return
    onChange?.(municipio)
    setQuery('')
    setIsOpen(false)
    setActiveIndex(0)
    inputRef.current?.blur()
  }

  function handleInputChange(event) {
    setQuery(event.target.value)
    setIsOpen(true)
    setActiveIndex(0)
  }

  function handleInputFocus() {
    setIsOpen(true)
  }

  function handleChevronClick() {
    if (isOpen) {
      setIsOpen(false)
    } else {
      setIsOpen(true)
      inputRef.current?.focus()
    }
  }

  function handleKeyDown(event) {
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
    } else if (event.key === 'Backspace' && query === '' && current) {
      onChange?.(null)
    }
  }

  const displayValue = isOpen ? query : current || ''
  const showPlaceholder = !displayValue

  return (
    <label
      ref={containerRef}
      className={`municipio-selector platform-selector ${isHero ? 'municipio-selector--hero' : ''} ${current ? 'is-selected' : ''} ${className} ${isOpen ? 'is-open' : ''}`}
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
          onFocus={handleInputFocus}
          onKeyDown={handleKeyDown}
          autoComplete="off"
          spellCheck="false"
        />
        {current && !isOpen && (
          <button
            type="button"
            className="municipio-selector__clear"
            aria-label="Limpar seleção"
            onClick={(event) => {
              event.stopPropagation()
              onChange?.(null)
              setQuery('')
              inputRef.current?.focus()
            }}
          >
            ×
          </button>
        )}
        <button
          type="button"
          className="municipio-selector__chevron-btn"
          aria-label="Abrir lista de municípios"
          tabIndex={-1}
          onClick={handleChevronClick}
        >
          <svg className="municipio-selector__chevron" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
            <path d="m6 9 6 6 6-6" />
          </svg>
        </button>
        {isOpen && (
          <ul
            id={listboxId}
            ref={listboxRef}
            role="listbox"
            className="municipio-selector__listbox"
          >
            {filtered.length === 0 ? (
              <li className="municipio-selector__empty">Nenhum município encontrado.</li>
            ) : (
              filtered.map((municipio, index) => (
                <li
                  key={municipio}
                  id={optionId(municipio)}
                  role="option"
                  aria-selected={index === activeIndex}
                  className={
                    index === activeIndex
                      ? 'municipio-selector__option is-active'
                      : 'municipio-selector__option'
                  }
                  onMouseDown={(event) => {
                    event.preventDefault()
                  }}
                  onClick={(event) => {
                    event.preventDefault()
                    event.stopPropagation()
                    commit(municipio)
                  }}
                  onMouseEnter={() => setActiveIndex(index)}
                >
                  {highlightMatch(municipio, query)}
                </li>
              ))
            )}
          </ul>
        )}
      </div>
    </label>
  )
})

function highlightMatch(text, query) {
  const q = normalizeText(query)
  if (!q) return text
  const normalizedText = String(text).normalize('NFD').replace(/\p{Diacritic}/gu, '')
  const lowerText = normalizedText.toLocaleLowerCase('pt-BR')
  const matchIndex = lowerText.indexOf(q)
  if (matchIndex < 0) return text
  return (
    <>
      {text.slice(0, matchIndex)}
      <mark className="municipio-selector__match">{text.slice(matchIndex, matchIndex + q.length)}</mark>
      {text.slice(matchIndex + q.length)}
    </>
  )
}
