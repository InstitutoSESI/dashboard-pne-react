import { MoveRight, TrendingDown, TrendingUp } from 'lucide-react'

export function StatusBadge({ className = '', displayStatus, marker, status, title, tone }) {
  const classes = ['status-badge']
  if (className) {
    classes.push(className)
  }
  if (tone) {
    classes.push(`status-badge--${tone}`)
  } else {
    const normalizedStatus = String(status).toLocaleLowerCase('pt-BR')
    const inferred =
      normalizedStatus.includes('atingida') && !normalizedStatus.includes('não') && !normalizedStatus.includes('nao')
        ? 'success'
        : normalizedStatus.includes('visualiza')
          ? 'info'
          : normalizedStatus.includes('não') ||
              normalizedStatus.includes('nao') ||
              normalizedStatus.includes('aten') ||
              normalizedStatus.includes('warning') ||
              normalizedStatus.includes('attention')
            ? 'warning'
            : normalizedStatus.includes('indispon') ||
                normalizedStatus.includes('sem dados') ||
                normalizedStatus.includes('muted')
              ? 'muted'
              : 'default'
    classes.push(`status-badge--${inferred}`)
  }
  return (
    <span className={classes.join(' ')} title={title ?? status}>
      {marker ? (
        <>
          <StatusMarker marker={marker} />
          <span>{displayStatus ?? status}</span>
        </>
      ) : displayStatus ?? status}
    </span>
  )
}

function StatusMarker({ marker }) {
  const icons = {
    up: TrendingUp,
    down: TrendingDown,
    stable: MoveRight,
  }
  const Icon = icons[marker]
  if (!Icon) return null
  return <Icon aria-hidden="true" className="status-badge__marker" />
}
