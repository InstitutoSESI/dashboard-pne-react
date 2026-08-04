import { ChevronDown } from 'lucide-react'

export function DisclosureChevron({ className = '' }) {
  return (
    <ChevronDown
      aria-hidden="true"
      className={`platform-disclosure-chevron${className ? ` ${className}` : ''}`}
    />
  )
}
