import type { Key, ReactNode } from 'react'
import {
  CalendarDays,
  ChartSpline,
  Clock3,
  ListFilter,
  Ruler,
  Target,
  TrendingUp,
  TriangleAlert,
} from 'lucide-react'
import { QuickReadingHeading } from './QuickReadingHeading'

export type QuickReadingIcon =
  | 'attention'
  | 'cut'
  | 'distance'
  | 'measure'
  | 'period'
  | 'projection'
  | 'target'
  | 'trend'

export interface QuickReadingItem {
  emphasized?: boolean
  icon?: QuickReadingIcon
  key?: Key
  label: string
  text: ReactNode
  warning?: ReactNode
}

export interface QuickReadingListProps {
  ariaLabel?: string
  className?: string
  items?: readonly QuickReadingItem[]
}

const QUICK_READING_ICONS = {
  attention: TriangleAlert,
  cut: ListFilter,
  distance: Ruler,
  measure: Clock3,
  period: CalendarDays,
  projection: ChartSpline,
  target: Target,
  trend: TrendingUp,
} as const

function hasRenderableContent(content: ReactNode): boolean {
  if (content === null || content === undefined || typeof content === 'boolean') return false
  if (typeof content === 'string') return content.trim().length > 0
  if (typeof content === 'number') return Number.isFinite(content)
  return true
}

export function QuickReadingList({
  ariaLabel = 'Leitura rápida',
  className = '',
  items = [],
}: QuickReadingListProps) {
  const visibleItems = items.filter((item) => hasRenderableContent(item?.text))
  if (!visibleItems.length) return null

  return (
    <aside
      className={`interpretation-box platform-quick-reading${className ? ` ${className}` : ''}`}
      aria-label={ariaLabel}
    >
      <QuickReadingHeading />
      <ul className="platform-quick-reading__list">
        {visibleItems.map((item) => (
          <li key={item.key ?? item.label}>
            <QuickReadingItemIcon name={item.icon} />
            <div>
              <span>{item.label}</span>
              <p>{item.emphasized ? <strong>{item.text}</strong> : item.text}</p>
              {hasRenderableContent(item.warning) ? <small>{item.warning}</small> : null}
            </div>
          </li>
        ))}
      </ul>
    </aside>
  )
}

function QuickReadingItemIcon({ name = 'measure' }: { name?: QuickReadingIcon }) {
  const Icon = QUICK_READING_ICONS[name]

  return <Icon aria-hidden="true" className="platform-quick-reading__icon" />
}
