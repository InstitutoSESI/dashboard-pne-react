import type { ReactNode } from 'react'

export function PmePageHeading({ title, description, children }: { title: string; description?: string; children?: ReactNode }) {
  return <header className="pme-page-heading"><h1 tabIndex={-1}>{title}</h1>{description && <p>{description}</p>}{children}</header>
}

export function PmeState({ kind = 'info', title, children, onRetry }: {
  kind?: 'info' | 'loading' | 'error' | 'unavailable'
  title: string
  children?: ReactNode
  onRetry?: () => void
}) {
  return <section className={`pme-state pme-state--${kind}`} role={kind === 'error' ? 'alert' : kind === 'loading' ? 'status' : undefined}>
    <h2>{title}</h2>{children}{onRetry && <button className="pme-button" type="button" onClick={onRetry}>Tentar novamente</button>}
  </section>
}

export function PmeTableRegion({ label, children }: { label: string; children: ReactNode }) {
  return <div className="pme-table-region" role="region" aria-label={label} tabIndex={0}>{children}</div>
}
