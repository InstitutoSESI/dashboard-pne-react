import { CalendarDays, Clock3, ListFilter, TrendingUp, TriangleAlert } from 'lucide-react'
import { QuickReadingHeading } from './QuickReadingHeading'

export function EducationQuickReading({
  items = /** @type {Array<{key?: string, icon?: string, label: string, text: string}>} */ ([]),
  tone = 'default',
  className = '',
}) {
  const visibleItems = items.filter((item) => item?.text)
  if (!visibleItems.length) return null

  return (
    <aside
      className={`interpretation-box education-quick-reading education-quick-reading--${tone}${className ? ` ${className}` : ''}`}
      aria-label="Leitura rápida"
    >
      <QuickReadingHeading />
      <ul className="education-quick-reading__list">
        {visibleItems.map((item) => (
          <li key={item.key ?? item.label}>
            <EducationInsightIcon name={item.icon} />
            <div>
              <span>{item.label}</span>
              <p>{item.text}</p>
            </div>
          </li>
        ))}
      </ul>
    </aside>
  )
}

function EducationInsightIcon({ name }) {
  const icons = {
    trend: TrendingUp,
    measure: Clock3,
    cut: ListFilter,
    period: CalendarDays,
    attention: TriangleAlert,
  }
  const Icon = icons[name] ?? Clock3

  return <Icon aria-hidden="true" className="education-quick-reading__icon" />
}
