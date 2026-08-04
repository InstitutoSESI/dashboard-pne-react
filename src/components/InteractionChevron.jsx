import { ChevronRight } from 'lucide-react'

export function InteractionChevron({ className = '' }) {
  return (
    <span
      className={`interaction-chevron${className ? ` ${className}` : ''}`}
      aria-hidden="true"
    >
      <ChevronRight focusable="false" />
    </span>
  )
}
