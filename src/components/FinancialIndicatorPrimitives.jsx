import { DisclosureChevron } from './DisclosureChevron'
import { DetailNavigation } from './DetailNavigation'
import { DetailHeadingText } from './HeadingText'
import { IndicatorChartHeader } from './IndicatorChartHeader'
import { MetricCard } from './MetricCard'
import { isPublishableFinancialDisplay } from '../utils/financialPresentation'

export { FinancialQuickReading } from './FinancialQuickReading'

export function FinancialDetailNavigation({
  activeIndex,
  nextIndicator,
  onBack,
  onNext,
  onPrevious,
  previousIndicator,
  total,
  isBottom = false,
}) {
  return (
    <DetailNavigation
      activeIndex={activeIndex}
      className={`financial-detail-nav${isBottom ? ' financial-detail-nav--bottom' : ''}`}
      isBottom={isBottom}
      nextItem={nextIndicator}
      onBack={onBack}
      onNext={onNext}
      onPrevious={onPrevious}
      previousItem={previousIndicator}
      showBack
      total={total}
    />
  )
}

export function FinancialSectionHeader({ actions = null, description, eyebrow, meta, title, titleId, className = '' }) {
  return (
    <div className={`pne-overview-section__heading financial-section-heading${className ? ` ${className}` : ''}`}>
      <span className="eyebrow">{eyebrow}</span>
      <div className="financial-section-heading__title-row">
        <h2 id={titleId}>{title}</h2>
        {meta || actions ? (
          <div className="financial-section-heading__tools">
            {meta ? <span className="financial-section-heading__meta">{meta}</span> : null}
            {actions ? <div className="financial-section-heading__actions">{actions}</div> : null}
          </div>
        ) : null}
      </div>
      {description ? <p>{description}</p> : null}
    </div>
  )
}

/**
 * @param {{
 *   actions?: import('react').ReactNode,
 *   children?: import('react').ReactNode,
 *   className?: string,
 *   description?: import('react').ReactNode,
 *   eyebrow?: import('react').ReactNode,
 *   meta?: import('react').ReactNode,
 *   title: import('react').ReactNode,
 *   titleId: string,
 * }} props
 */
export function FinancialSection({
  actions,
  children,
  className = '',
  description,
  eyebrow,
  meta,
  title,
  titleId,
}) {
  return (
    <section
      aria-labelledby={titleId}
      className={`page-card pne-overview-section financial-section${className ? ` ${className}` : ''}`}
    >
      <FinancialSectionHeader
        actions={actions}
        description={description}
        eyebrow={eyebrow}
        meta={meta}
        title={title}
        titleId={titleId}
      />
      {children}
    </section>
  )
}

export function FinancialMetricStrip({ children, className = '' }) {
  return <FinancialKpiGrid className={className}>{children}</FinancialKpiGrid>
}

export function FinancialKpiGrid({ children, className = '' }) {
  return <div className={`financial-kpi-grid${className ? ` ${className}` : ''}`}>{children}</div>
}

/**
 * @param {{
 *   action?: import('react').ReactNode,
 *   children?: import('react').ReactNode,
 *   className?: string,
 *   icon?: import('react').ReactNode,
 *   label: import('react').ReactNode,
 *   meta?: import('react').ReactNode,
 *   title?: string,
 *   tone?: string,
 *   value?: import('react').ReactNode,
 * }} props
 */
export function FinancialKpiCard({
  action,
  children,
  className = '',
  icon,
  label,
  meta,
  title,
  tone = 'default',
  value,
}) {
  const displayedValue = value ?? children

  return (
    <article className={`financial-card financial-kpi-card financial-kpi-card--${tone}${className ? ` ${className}` : ''}`}>
      <div className="financial-kpi-card__heading">
        {icon ? <span className="financial-kpi-card__icon" aria-hidden="true">{icon}</span> : null}
        <span className="financial-kpi-card__label">{label}</span>
      </div>
      <strong className="financial-kpi-card__value" title={title}>{displayedValue}</strong>
      {meta ? <small className="financial-kpi-card__meta">{meta}</small> : null}
      {action ? <div className="financial-card__action">{action}</div> : null}
    </article>
  )
}

export function FinancialLeadCard({ action = null, children, className = '', label, meta = null, value }) {
  return (
    <article className={`financial-card financial-lead-card${className ? ` ${className}` : ''}`}>
      <span className="financial-lead-card__label">{label}</span>
      <strong className="financial-lead-card__value">{value}</strong>
      {meta ? <small className="financial-lead-card__meta">{meta}</small> : null}
      {children}
      {action ? <div className="financial-card__action">{action}</div> : null}
    </article>
  )
}

export function FinancialDataRow({ action = null, children, className = '', icon = null, label, meta = null, value }) {
  return (
    <article className={`financial-data-row${className ? ` ${className}` : ''}`}>
      <div className="financial-data-row__content">
        <div className="financial-data-row__heading">
          {icon ? <span className="financial-data-row__icon" aria-hidden="true">{icon}</span> : null}
          <span className="financial-data-row__label">{label}</span>
        </div>
        <strong className="financial-data-row__value">{value}</strong>
        {meta ? <small className="financial-data-row__meta">{meta}</small> : null}
        {children}
      </div>
      {action ? <div className="financial-data-row__action">{action}</div> : null}
    </article>
  )
}

export function FinancialNarrativeCard({ children, className = '' }) {
  return <article className={`financial-card financial-narrative-card${className ? ` ${className}` : ''}`}>{children}</article>
}

export function FinancialProcessStepCard({ connector = null, label, meta, number, value }) {
  return (
    <li className="financial-process-step-card">
      <span className="financial-process-step-card__number">{number}</span>
      <div>
        <small>{label}</small>
        <strong>{value}</strong>
        {meta ? <b>{meta}</b> : null}
      </div>
      {connector ? <span className="financial-process-step-card__connector" aria-hidden="true">{connector}</span> : null}
    </li>
  )
}

export function FinancialDetailHeader({ indicator }) {
  return (
    <div className="detail-heading educacao-detail-heading financial-detail-heading">
      <DetailHeadingText description={indicator.description} eyebrow="Indicador selecionado" level={1} title={indicator.label} />
      <div className="educacao-detail-heading__badges financial-detail-heading__badges" aria-label="Contexto do indicador">
        {indicator.moduleLabel ? <span className="indicator-stage-badge">{indicator.moduleLabel}</span> : null}
        {indicator.unitLabel ? <span className="indicator-stage-badge">{indicator.unitLabel}</span> : null}
      </div>
    </div>
  )
}

export function FinancialMetricGrid({ indicator }) {
  const hasInitialValue = isPublishableFinancialDisplay(indicator.initialDisplay)
  const hasCurrentValue = isPublishableFinancialDisplay(indicator.currentDisplay)
  const hasVariation = isPublishableFinancialDisplay(indicator.variationDisplay)
    && indicator.initialYear !== indicator.currentYear
  const metrics = [
    hasInitialValue && indicator.initialYear !== indicator.currentYear ? (
      <MetricCard
        icon="current"
        key="initial"
        label="Valor inicial"
        value={indicator.initialDisplay}
        detail={indicator.initialYear ? `Ano ${indicator.initialYear}` : null}
      />
    ) : null,
    hasCurrentValue ? (
      <MetricCard
        icon="comparison"
        key="current"
        label="Valor atual"
        value={indicator.currentDisplay}
        detail={indicator.currentYear ? `Ano ${indicator.currentYear}` : null}
        size="large"
      />
    ) : null,
    hasVariation ? (
      <MetricCard
        icon="variation"
        key="variation"
        label="Variação no período"
        value={indicator.variationDisplay}
        detail={indicator.initialYear && indicator.currentYear ? `${indicator.initialYear} a ${indicator.currentYear}` : null}
        tone={indicator.variationTone ?? 'default'}
      />
    ) : null,
    indicator.currentYear ? (
      <MetricCard icon="current" key="year" label="Ano de referência" value={indicator.currentYear} />
    ) : null,
  ].filter(Boolean)

  if (!metrics.length) return null

  return (
    <div className="metric-grid metric-grid--four financial-metric-grid">
      {metrics}
    </div>
  )
}

export function FinancialPrimaryAnalysis({ children }) {
  return (
    <div className="financial-primary-analysis">
      {children}
    </div>
  )
}

export function FinancialChartFrame({ children, source, subtitle, summary, title = 'Evolução do indicador' }) {
  return (
    <div className="indicator-chart-card educacao-main-chart-card financial-chart-card">
      <IndicatorChartHeader className="financial-chart-header" subtitle={subtitle} summary={summary} title={title} />
      {children}
      {source}
    </div>
  )
}

export function FinancialSourcesFooter({ children, periods, source }) {
  if (!source && !periods && !children) return null

  return (
    <footer className="financial-sources-footer">
      <div className="financial-sources-footer__heading">
        <span className="eyebrow">Referências oficiais</span>
        <h2>Fontes e metodologia</h2>
      </div>
      {source ? <p><strong>Fonte oficial:</strong> {source}</p> : null}
      {periods ? <p>{periods}</p> : null}
      {children ? (
        <details className="platform-support-disclosure financial-sources-footer__details">
          <DisclosureSummary description="Critérios de publicação e cuidados de interpretação." title="Consultar detalhes" />
          <div className="platform-support-disclosure__body">{children}</div>
        </details>
      ) : null}
    </footer>
  )
}

function DisclosureSummary({ description, title }) {
  return (
    <summary className="platform-support-disclosure__summary">
      <div>
        <h3>{title}</h3>
        <p>{description}</p>
      </div>
      <DisclosureChevron />
    </summary>
  )
}
