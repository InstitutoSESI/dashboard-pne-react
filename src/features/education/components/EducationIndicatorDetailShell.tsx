import type { ReactNode } from 'react'
import { ChartColumnIncreasing } from 'lucide-react'
import { MetricCard } from '../../../components/MetricCard.jsx'

const EM = '\u2014'

interface Variation {
  display?: string
  raw?: number | null
  tone?: string
}

interface EducationMetricSummaryProps {
  currentLabel?: string
  currentValue: ReactNode
  currentYear?: number | null
  initialLabel?: string
  initialValue: ReactNode
  initialYear?: number | null
  statusDetail?: string
  statusLabel?: string
  statusTone?: string
  variation?: Variation
  variationLabel?: string
}

interface EducationIndicatorDetailShellProps {
  children?: ReactNode
  className?: string
  primaryPanel: ReactNode
  quickReading: ReactNode
  summary: ReactNode
}

interface EducationSupportDataSectionProps {
  children: ReactNode
  className?: string
  description?: string
  footer?: ReactNode
  id: string
}

interface EducationSupportDataCardProps {
  children: ReactNode
  className?: string
  description: string
  eyebrow: string
  id: string
  title: string
}

export function EducationIndicatorDetailShell({
  children,
  className = '',
  primaryPanel,
  quickReading,
  summary,
}: EducationIndicatorDetailShellProps) {
  return (
    <section className={`detail-panel educacao-detail-panel educacao-detail-panel--organized${className ? ` ${className}` : ''}`}>
      {summary}
      <div className="education-primary-analysis">
        {primaryPanel}
        {quickReading}
      </div>
      {children}
    </section>
  )
}

export function EducationMetricGrid({ children }: { children: ReactNode }) {
  return <div className="metric-grid metric-grid--four education-metric-summary">{children}</div>
}

export function EducationMetricSummary({
  currentLabel = 'Valor mais recente',
  currentValue,
  currentYear,
  initialLabel = 'Valor inicial',
  initialValue,
  initialYear,
  statusDetail,
  statusLabel,
  statusTone,
  variation,
  variationLabel = 'Variação no período',
}: EducationMetricSummaryProps) {
  const period = initialYear && currentYear ? `${initialYear} a ${currentYear}` : 'Período indisponível'

  return (
    <EducationMetricGrid>
      <MetricCard
        detail="Início da série histórica"
        icon="start"
        label={initialYear ? `${initialLabel} (${initialYear})` : initialLabel}
        value={initialValue}
      />
      <MetricCard
        detail={currentYear === 2025 ? 'Ano de referência' : 'Último dado disponível'}
        icon="current"
        label={currentYear ? `${currentLabel} (${currentYear})` : currentLabel}
        size="large"
        value={currentValue}
      />
      <MetricCard
        detail={period}
        icon={variation?.raw != null && variation.raw < 0 ? 'variationDown' : 'variation'}
        label={variationLabel}
        tone={variation?.tone}
        value={variation?.display ?? EM}
      />
      <MetricCard
        detail={statusDetail ?? 'Leitura descritiva da série'}
        icon="status"
        label="Tendência observada"
        tone={statusTone ?? variation?.tone}
        value={statusLabel ?? variationStatusLabel(variation)}
      />
    </EducationMetricGrid>
  )
}

export function EducationSupportDataSection({
  children,
  className = '',
  description = 'Recortes por etapa, rede, localização ou perfil, quando disponíveis na estrutura atual.',
  footer,
  id,
}: EducationSupportDataSectionProps) {
  return (
    <section
      aria-labelledby={`${id}-title`}
      className={`educacao-explore education-support-data education-support-data--organized${className ? ` ${className}` : ''}`}
    >
      <header className="education-support-data__header">
        <EducationSupportDataIcon />
        <div className="education-support-data__summary">
          <span className="educacao-explore__eyebrow">Aprofundamento</span>
          <h3 id={`${id}-title`}>Dados de apoio do indicador</h3>
          <p>{description}</p>
        </div>
      </header>
      <div className="education-support-data__body">
        <div className="education-support-data__grid">{children}</div>
      </div>
      {footer ? (
        <footer aria-label="Fonte consolidada dos dados de apoio" className="education-support-data__footer">
          {footer}
        </footer>
      ) : null}
    </section>
  )
}

export function EducationSupportDataCard({
  children,
  className = '',
  description,
  eyebrow,
  id,
  title,
}: EducationSupportDataCardProps) {
  return (
    <section
      aria-labelledby={`${id}-title`}
      className={`education-support-data__item${className ? ` ${className}` : ''}`}
    >
      <header className="education-support-data__item-heading">
        <div>
          <span>{eyebrow}</span>
          <h4 id={`${id}-title`}>{title}</h4>
          <p>{description}</p>
        </div>
      </header>
      <div className="education-support-data__item-content">{children}</div>
    </section>
  )
}

function variationStatusLabel(variation?: Variation) {
  if (variation?.raw === null || variation?.raw === undefined) return 'Sem série'
  if (variation.raw > 0) return 'Aumentou'
  if (variation.raw < 0) return 'Diminuiu'
  return 'Sem alteração relevante'
}

function EducationSupportDataIcon() {
  return <ChartColumnIncreasing aria-hidden="true" className="education-support-data__icon" />
}
