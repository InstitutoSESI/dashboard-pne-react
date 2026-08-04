import {
  ArrowLeftRight,
  Boxes,
  CalendarDays,
  CircleCheckBig,
  Flag,
  Ruler,
  Target,
  TrendingDown,
  TrendingUp,
} from 'lucide-react'

export function MetricCard({ label, value, detail, icon = /** @type {string | null} */ (null), tone = 'default', size = 'normal' }) {
  const toneClass = tone !== 'default' ? `metric-card--${tone}` : ''
  const sizeClass = size === 'large' ? 'metric-card--large' : ''
  return (
    <div className={`metric-card interaction-card--informative ${toneClass} ${sizeClass}${icon ? ' metric-card--with-icon' : ''}`}>
      {icon ? <MetricIcon name={icon} /> : null}
      <span className="metric-card__label">{label}</span>
      <strong className="metric-card__value">{value ?? '-'}</strong>
      {detail !== undefined && <small className="metric-card__detail">{detail}</small>}
    </div>
  )
}

function MetricIcon({ name }) {
  const icons = {
    current: CalendarDays,
    comparison: ArrowLeftRight,
    distance: Ruler,
    start: Flag,
    status: CircleCheckBig,
    target: Target,
    type: Boxes,
    variation: TrendingUp,
    variationDown: TrendingDown,
  }
  const Icon = icons[name] ?? CircleCheckBig

  return <Icon aria-hidden="true" className="metric-card__icon" />
}
