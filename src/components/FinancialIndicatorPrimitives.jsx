import { Clock3, ListFilter, TrendingUp } from 'lucide-react'
import { DisclosureChevron } from './DisclosureChevron'
import { DetailNavigation } from './DetailNavigation'
import { DetailHeadingText } from './HeadingText'
import { IndicatorChartHeader } from './IndicatorChartHeader'
import { MetricCard } from './MetricCard'
import { QuickReadingHeading } from './QuickReadingHeading'
import { isPublishableFinancialDisplay } from '../utils/financialPresentation'

const EM = '\u2014'
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
  return <div className={`education-summary-grid financial-summary-grid${className ? ` ${className}` : ''}`}>{children}</div>
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

function FinancialQuickReadingIcon({ name }) {
  const icons = {
    measure: Clock3,
    period: ListFilter,
    trend: TrendingUp,
  }
  const Icon = icons[name] ?? Clock3

  return <Icon aria-hidden="true" className="education-quick-reading__icon" />
}

function getFinancialReadingItems({ description, indicator, metadata, readingGuide, text }) {
  const period = indicator?.initialYear && indicator?.currentYear
    ? `${indicator.initialYear} a ${indicator.currentYear}`
    : indicator?.currentYear
      ? String(indicator.currentYear)
      : EM

  return [
    { icon: 'trend', label: 'Evolução observada', text: text ?? indicator?.quickReading },
    { icon: 'measure', label: 'O que o indicador mede', text: readingGuide?.oQueMede ?? metadata?.measures ?? description },
    { emphasis: true, icon: 'period', label: 'Recorte exibido', text: period },
  ].filter((item) => item.text)
}

export function FinancialQuickReading({ description, indicator, metadata, readingGuide, text }) {
  const items = getFinancialReadingItems({ description, indicator, metadata, readingGuide, text })
  if (!items.length) return null

  return (
    <aside className="interpretation-box education-quick-reading financial-quick-reading" aria-label="Leitura rápida do indicador">
      <QuickReadingHeading />
      <ul className="education-quick-reading__list">
        {items.map((item) => (
          <li key={item.label}>
            <FinancialQuickReadingIcon name={item.icon} />
            <div>
              <span>{item.label}</span>
              <p>{item.emphasis ? <strong>{item.text}</strong> : item.text}</p>
            </div>
          </li>
        ))}
      </ul>
    </aside>
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
