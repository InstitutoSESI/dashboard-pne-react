import { useRef } from 'react'
import { Search, X } from 'lucide-react'

export function SearchField({ ariaLabel, className, clearLabel = 'Limpar busca', disabled = false, onChange, onClear, placeholder, value }) {
  const inputRef = useRef(null)
  const resolvedClassName = [
    className,
    value ? 'is-filled' : '',
    disabled ? 'is-disabled' : '',
  ].filter(Boolean).join(' ')

  function handleClear() {
    onClear?.()
    requestAnimationFrame(() => inputRef.current?.focus())
  }

  return (
    <div className={resolvedClassName} data-filled={value ? 'true' : 'false'}>
      <Search aria-hidden="true" />
      <input
        ref={inputRef}
        type="search"
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        aria-label={ariaLabel}
        disabled={disabled}
      />
      {value && onClear && !disabled ? (
        <button className="platform-search-field__clear" type="button" aria-label={clearLabel} onClick={handleClear}>
          <X aria-hidden="true" />
        </button>
      ) : null}
    </div>
  )
}
