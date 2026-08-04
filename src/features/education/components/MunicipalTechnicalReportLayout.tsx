import type { CSSProperties, MouseEvent, ReactNode } from 'react'
import { ArrowUp } from 'lucide-react'

export interface ReportSectionDefinition {
  id: string
  shortTitle: string
  officialTitle: string
}

export interface ReportChapterDefinition {
  id: string
  number: number
  title: string
  description: string
  startIndex: number
  endIndex: number
}

export interface ReportMetricItem {
  detail?: ReactNode
  label: string
  value: ReactNode
}

export type ReportSectionModel =
  | 'flow'
  | 'coverage'
  | 'metrics-only'
  | 'metrics-table-side'
  | 'metrics-table-stack'
  | 'table-only'

export type ReportCoverage = 'complete' | 'partial' | 'municipal-complement'
export type ReportTableVariant = 'standard' | 'compact' | 'stacked' | 'split' | 'historical'

function scrollToReportTarget(event: MouseEvent<HTMLAnchorElement>, targetId: string) {
  const target = globalThis.document?.getElementById(targetId)
  if (!target) return

  event.preventDefault()
  const reduceMotion = globalThis.window?.matchMedia('(prefers-reduced-motion: reduce)').matches
  target.scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth', block: 'start' })
}

export function MissingInformation({ children }: { children?: ReactNode }) {
  return (
    <div className="municipal-technical-report__unavailable" role="note">
      <div className="municipal-technical-report__unavailable-status">
        <strong>Evidências públicas disponíveis</strong>
      </div>
      <p>
        {children ?? 'As bases públicas utilizadas não permitem calcular este indicador com segurança para o município.'}
      </p>
    </div>
  )
}

export function ReportChapter({
  chapter,
  children,
}: {
  chapter: ReportChapterDefinition
  children: ReactNode
}) {
  return (
    <section className="municipal-technical-report__chapter" id={chapter.id} aria-labelledby={`${chapter.id}-title`}>
      <header className="municipal-technical-report__chapter-header">
        <div className="municipal-technical-report__chapter-kicker">
          <span className="eyebrow">Capítulo {chapter.number}</span>
          <span>Seções {String(chapter.startIndex + 1).padStart(2, '0')}–{String(chapter.endIndex + 1).padStart(2, '0')}</span>
        </div>
        <h2 id={`${chapter.id}-title`}>{chapter.title}</h2>
        <p>{chapter.description}</p>
      </header>
      <div className="municipal-technical-report__chapter-sections">{children}</div>
      <nav className="municipal-technical-report__chapter-navigation" aria-label={`Navegação do capítulo ${chapter.number}`}>
        <a className="municipal-technical-report__back" href="#sumario" onClick={(event) => scrollToReportTarget(event, 'sumario')}>
          Sumário
        </a>
        <a className="municipal-technical-report__back" href="#inicio-relatorio" onClick={(event) => scrollToReportTarget(event, 'inicio-relatorio')}>
          Voltar ao início <ArrowUp aria-hidden="true" size={14} />
        </a>
      </nav>
    </section>
  )
}

export function ReportSection({
  children,
  compact = false,
  coverage,
  layout = 'flow',
  metadata,
  model = 'flow',
  number,
  section,
}: {
  children: ReactNode
  compact?: boolean
  coverage?: ReportCoverage
  layout?: 'flow' | 'split'
  metadata: string
  model?: ReportSectionModel
  number: number
  section: ReportSectionDefinition
}) {
  const subtitleId = section.shortTitle === section.officialTitle ? undefined : `${section.id}-subtitle`
  const metadataId = `${section.id}-metadata`
  const describedBy = [subtitleId, metadataId].filter(Boolean).join(' ')
  const resolvedCoverage = coverage
    ?? (model === 'coverage' ? 'municipal-complement' : compact ? 'partial' : 'complete')

  return (
    <section
      className={`municipal-technical-report__section municipal-technical-report__section--${layout} municipal-technical-report__section--model-${model}${compact ? ' municipal-technical-report__section--compact' : ''}`}
      id={section.id}
      aria-labelledby={`${section.id}-title`}
      aria-describedby={describedBy}
      data-report-coverage={resolvedCoverage}
    >
      <span className="municipal-technical-report__section-number">{String(number).padStart(2, '0')}</span>
      <div className="municipal-technical-report__section-main">
        <header className="municipal-technical-report__section-heading">
          <h3 id={`${section.id}-title`}>{section.shortTitle}</h3>
          {subtitleId ? <p className="municipal-technical-report__section-subtitle" id={subtitleId}>{section.officialTitle}</p> : null}
        </header>
        <div className="municipal-technical-report__section-body">{children}</div>
        <p className="municipal-technical-report__section-metadata" id={metadataId}>
          <strong>Fonte e referência:</strong> {metadata}.
        </p>
      </div>
    </section>
  )
}

export function ReportMetrics({
  ariaLabel,
  compact = false,
  description,
  items,
  metadata,
  title = 'Indicadores principais',
}: {
  ariaLabel?: string
  compact?: boolean
  description?: ReactNode
  items: ReportMetricItem[]
  metadata?: ReactNode
  title?: ReactNode | null
}) {
  const visibleCount = Math.min(Math.max(items.length, 1), 4)
  const metricStyle = {
    '--metric-count': visibleCount,
  } as CSSProperties

  return (
    <div
      className={`municipal-technical-report__metrics municipal-technical-report__metrics--${visibleCount}${compact ? ' municipal-technical-report__metrics--compact' : ''}`}
      style={metricStyle}
    >
      {title != null ? (
        <ReportBlockHeader description={description} metadata={metadata} title={title} />
      ) : null}
      <dl className="municipal-technical-report__metrics-list" aria-label={ariaLabel}>
        {items.map((item) => (
          <div key={item.label}>
            <dt>{item.label}</dt>
            <dd>{item.value}</dd>
            {item.detail != null ? <span>{item.detail}</span> : null}
          </div>
        ))}
      </dl>
    </div>
  )
}

export function ReportBlockHeader({
  description,
  metadata,
  title,
}: {
  description?: ReactNode
  metadata?: ReactNode
  title: ReactNode
}) {
  return (
    <header className="municipal-technical-report__block-header">
      <div className="municipal-technical-report__block-heading">
        <div className="municipal-technical-report__block-title">{title}</div>
        {description != null ? <p>{description}</p> : null}
      </div>
      {metadata != null ? <div className="municipal-technical-report__block-metadata">{metadata}</div> : null}
    </header>
  )
}

export function ReportNote({
  children,
  placement = 'full',
}: {
  children: ReactNode
  placement?: 'full' | 'table'
}) {
  return (
    <p className={`municipal-technical-report__note municipal-technical-report__note--${placement}`}>
      <span>{children}</span>
    </p>
  )
}

export function ReportMunicipalReading({ children }: { children: ReactNode }) {
  return (
    <section className="municipal-technical-report__municipal-reading" aria-label="Leitura do município">
      <h4>Leitura do município</h4>
      <div>{children}</div>
    </section>
  )
}

export function ReportTableRegion({
  ariaLabel,
  children,
  className = '',
  description,
  focusable = false,
  metadata,
  title,
  variant = 'standard',
}: {
  ariaLabel?: string
  children: ReactNode
  className?: string
  description?: ReactNode
  focusable?: boolean
  metadata?: ReactNode
  title?: ReactNode
  variant?: ReportTableVariant
}) {
  const viewportClasses = [
    'municipal-technical-report__table-scroll',
    className,
  ].filter(Boolean).join(' ')

  return (
    <div className={`municipal-technical-report__table-region municipal-technical-report__table-region--${variant}`} data-print-variant={variant}>
      {title != null ? (
        <ReportBlockHeader description={description} metadata={metadata} title={title} />
      ) : null}
      <div className={viewportClasses} tabIndex={focusable ? 0 : undefined} aria-label={ariaLabel}>
        {children}
      </div>
    </div>
  )
}

export { scrollToReportTarget }
