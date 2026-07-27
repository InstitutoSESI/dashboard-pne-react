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
  const paths = {
    trend: <><path d="M5 16 10 11l3 3 6-7" /><path d="M15 7h4v4" /></>,
    measure: <><circle cx="12" cy="12" r="8" /><path d="M12 8v4l3 2" /></>,
    cut: <><path d="M5 6h14M8 12h8M10 18h4" /></>,
    period: <><rect height="15" rx="2" width="16" x="4" y="5" /><path d="M8 3v4M16 3v4M4 10h16" /></>,
    attention: <><path d="M12 4 3.5 19h17L12 4Z" /><path d="M12 9v4M12 16h.01" /></>,
  }

  return (
    <svg aria-hidden="true" className="education-quick-reading__icon" fill="none" viewBox="0 0 24 24">
      {paths[name] ?? paths.measure}
    </svg>
  )
}
