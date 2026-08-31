import type { CSSProperties, MouseEvent as ReactMouseEvent, ReactNode } from 'react'
import { PnePageHeader } from '../../components/PnePageHeader'
import type {
  VocacoesPneAlignedSeriesVisual,
  VocacoesPneCategoryBarsVisual,
  VocacoesPneMunicipalDistribution,
  VocacoesPneNarrativeCard,
  VocacoesPneNarrativeDocument,
  VocacoesPneNarrativeSection,
  VocacoesPnePrimaryVisual,
} from './vocacoesPneNarrativeTypes'
import type { VocacoesDocument, VocacoesSeries } from './vocacoesRegiaoTypes'
import '../../styles/vocacoes-pne-narrative-page.css'

const integerFormatter = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 0 })
const decimalFormatter = new Intl.NumberFormat('pt-BR', {
  maximumFractionDigits: 1,
  minimumFractionDigits: 1,
})
const MONTH_LABELS = [
  'jan.', 'fev.', 'mar.', 'abr.', 'mai.', 'jun.',
  'jul.', 'ago.', 'set.', 'out.', 'nov.', 'dez.',
] as const

function formatValue(value: number, unit: string): string {
  const formatted = Number.isInteger(value)
    ? integerFormatter.format(value)
    : decimalFormatter.format(value)
  return unit === 'percentual' ? `${formatted}%` : `${formatted} ${unit}`
}

function formatConsultationPeriod(
  period: number,
  granularity: VocacoesSeries['periodGranularity'],
): string {
  if (granularity === 'annual') return String(period)
  const year = Math.floor(period / 100)
  const month = period % 100
  return `${MONTH_LABELS[month - 1]} ${year}`
}

function focusNarrativeTarget(
  event: ReactMouseEvent<HTMLButtonElement>,
  targetId: string,
): void {
  event.preventDefault()
  if (typeof document === 'undefined') return
  const target = document.getElementById(targetId)
  if (!(target instanceof HTMLElement)) return
  const reducedMotion = globalThis.window
    ?.matchMedia?.('(prefers-reduced-motion: reduce)')
    .matches
  target.scrollIntoView({
    behavior: reducedMotion ? 'auto' : 'smooth',
    block: 'start',
  })
  target.focus({ preventScroll: true })
}

function buildLinePoints(values: readonly number[]): string {
  const width = 536
  const height = 104
  const min = Math.min(...values)
  const max = Math.max(...values)
  const span = max - min || 1
  return values.map((value, index) => {
    const x = 12 + (values.length === 1 ? 0 : (index / (values.length - 1)) * width)
    const y = 12 + height - ((value - min) / span) * height
    return `${x.toFixed(2)},${y.toFixed(2)}`
  }).join(' ')
}

function AlignedSeriesVisual({
  visual,
}: {
  visual: VocacoesPneAlignedSeriesVisual
}) {
  const firstPeriod = visual.periods[0]
  const lastPeriod = visual.periods[visual.periods.length - 1]

  return (
    <div className="vocacoes-pne-aligned-series">
      {visual.series.map((series, index) => {
        const firstValue = series.values[0]
        const lastValue = series.values[series.values.length - 1]
        return (
          <figure className="vocacoes-pne-mini-chart" key={series.label}>
            <figcaption>
              <span>{series.label}</span>
              <small>{series.unit}</small>
            </figcaption>
            <svg
              aria-label={`${visual.alt_text} — ${series.label}`}
              preserveAspectRatio="none"
              role="img"
              viewBox="0 0 560 128"
            >
              <title>{`${visual.alt_text} — ${series.label}`}</title>
              <line className="vocacoes-pne-chart-axis" x1="12" x2="548" y1="116" y2="116" />
              <polyline
                className={index === 0
                  ? 'vocacoes-pne-chart-line vocacoes-pne-chart-line--education'
                  : 'vocacoes-pne-chart-line vocacoes-pne-chart-line--territory'}
                points={buildLinePoints(series.values)}
              />
            </svg>
            <dl className="vocacoes-pne-chart-endpoints">
              <div>
                <dt>{firstPeriod}</dt>
                <dd>{formatValue(firstValue, series.unit)}</dd>
              </div>
              <div>
                <dt>{lastPeriod}</dt>
                <dd>{formatValue(lastValue, series.unit)}</dd>
              </div>
            </dl>
          </figure>
        )
      })}
    </div>
  )
}

function CategoryBarsVisual({
  visual,
}: {
  visual: VocacoesPneCategoryBarsVisual
}) {
  const chartStart = 180
  const chartWidth = 340
  return (
    <div className="vocacoes-pne-category-visual">
      <svg
        aria-label={visual.alt_text}
        preserveAspectRatio="xMinYMin meet"
        role="img"
        viewBox="0 0 560 314"
      >
        <title>{visual.alt_text}</title>
        {visual.categories.map((category, index) => {
          const y = 16 + index * 92
          const regionWidth = Math.max(0, Math.min(100, category.region_value)) * chartWidth / 100
          const stateWidth = Math.max(0, Math.min(100, category.state_value)) * chartWidth / 100
          return (
            <g key={category.label}>
              <text className="vocacoes-pne-svg-category" x="0" y={y + 13}>{category.label}</text>
              <text className="vocacoes-pne-svg-series" x="0" y={y + 40}>
                {visual.series_labels.region}
              </text>
              <rect
                className="vocacoes-pne-svg-bar vocacoes-pne-svg-bar--region"
                height="16"
                rx="4"
                width={regionWidth}
                x={chartStart}
                y={y + 25}
              />
              <text className="vocacoes-pne-svg-value" x={chartStart + regionWidth + 6} y={y + 39}>
                {formatValue(category.region_value, visual.unit)}
              </text>
              <text className="vocacoes-pne-svg-series" x="0" y={y + 67}>
                {visual.series_labels.state}
              </text>
              <rect
                className="vocacoes-pne-svg-bar vocacoes-pne-svg-bar--state"
                height="16"
                rx="4"
                width={stateWidth}
                x={chartStart}
                y={y + 52}
              />
              <text className="vocacoes-pne-svg-value" x={chartStart + stateWidth + 6} y={y + 66}>
                {formatValue(category.state_value, visual.unit)}
              </text>
            </g>
          )
        })}
        <line className="vocacoes-pne-chart-axis" x1={chartStart} x2={chartStart + chartWidth} y1="294" y2="294" />
        <text className="vocacoes-pne-svg-axis-label" x={chartStart} y="311">0%</text>
        <text className="vocacoes-pne-svg-axis-label" textAnchor="end" x={chartStart + chartWidth} y="311">100%</text>
      </svg>
      <ul className="vocacoes-pne-visual-equivalent">
        {visual.categories.map((category) => (
          <li key={category.label}>
            <span>{category.label}</span>
            <span>{visual.series_labels.region}: {formatValue(category.region_value, visual.unit)}</span>
            <span>{visual.series_labels.state}: {formatValue(category.state_value, visual.unit)}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

function PrimaryVisual({ visual }: { visual: VocacoesPnePrimaryVisual }) {
  return (
    <figure className="vocacoes-pne-visual">
      <figcaption>{visual.title}</figcaption>
      {visual.template === 'aligned_series'
        ? <AlignedSeriesVisual visual={visual} />
        : <CategoryBarsVisual visual={visual} />}
    </figure>
  )
}

function EvolutionDetail({ visual }: { visual: VocacoesPnePrimaryVisual }) {
  if (visual.template === 'category_bars') {
    return (
      <ul className="vocacoes-pne-detail-list">
        {visual.categories.map((category) => (
          <li key={category.label}>
            <strong>{category.label}</strong>
            <span>{visual.series_labels.region}: {formatValue(category.region_value, visual.unit)}</span>
            <span>{visual.series_labels.state}: {formatValue(category.state_value, visual.unit)}</span>
          </li>
        ))}
      </ul>
    )
  }

  return (
    <div className="vocacoes-pne-evolution-grid">
      {visual.series.map((series) => (
        <section key={series.label}>
          <h4>{series.label}</h4>
          <ol>
            {visual.periods.map((period, index) => (
              <li key={period}>
                <span>{period}</span>
                <span>{formatValue(series.values[index], series.unit)}</span>
              </li>
            ))}
          </ol>
        </section>
      ))}
    </div>
  )
}

function MunicipalDistribution({
  distribution,
}: {
  distribution: VocacoesPneMunicipalDistribution
}) {
  const acceptsSign = distribution.items.some((item) => item.value < 0)
  const scale = acceptsSign
    ? Math.max(...distribution.items.map((item) => Math.abs(item.value)), 1)
    : 100
  return (
    <div
      className={`vocacoes-pne-municipal-bars${acceptsSign ? ' vocacoes-pne-municipal-bars--diverging' : ''}`}
      data-signed={acceptsSign ? 'true' : 'false'}
    >
      {distribution.items.map((item) => {
        const width = acceptsSign
          ? Math.abs(item.value) / scale * 50
          : Math.max(0, Math.min(100, item.value))
        const style = { '--voc-pne-bar-size': `${width}%` } as CSSProperties
        return (
          <div className="vocacoes-pne-municipal-row" key={item.name}>
            <span>{item.name}</span>
            <span
              aria-hidden="true"
              className={`vocacoes-pne-municipal-track${item.value < 0 ? ' is-negative' : ' is-positive'}`}
              style={style}
            >
              <i />
            </span>
            <strong>{formatValue(item.value, distribution.unit)}</strong>
          </div>
        )
      })}
    </div>
  )
}

function Disclosure({
  children,
  kind,
  label,
}: {
  children: ReactNode
  kind: 'evolution' | 'municipalities' | 'pne' | 'sources'
  label: string
}) {
  return (
    <details className="vocacoes-pne-disclosure" data-disclosure={kind}>
      <summary>{label}</summary>
      <div className="vocacoes-pne-disclosure__body">{children}</div>
    </details>
  )
}

function CardDetails({
  card,
  narrative,
}: {
  card: VocacoesPneNarrativeCard
  narrative: VocacoesPneNarrativeDocument
}) {
  const municipalityNote = card.direction === 'educacao_para_territorio'
    ? card.municipal_pattern
    : card.exposed_groups_or_municipalities
  const period = card.direction === 'educacao_para_territorio' ? card.period : card.horizon

  return (
    <div className="vocacoes-pne-disclosures">
      <Disclosure kind="evolution" label={narrative.page.details.evolution}>
        <EvolutionDetail visual={card.primary_visual} />
      </Disclosure>
      <Disclosure kind="municipalities" label={narrative.page.details.municipalities}>
        <p>{municipalityNote}</p>
        <MunicipalDistribution distribution={card.municipal_distribution} />
      </Disclosure>
      <Disclosure kind="pne" label={narrative.page.details.pne}>
        <div className="vocacoes-pne-related-lists">
          <ul>{card.pne_topics.map((topic) => <li key={topic}>{topic}</li>)}</ul>
          <ul>{card.monitoring_indicators.map((indicator) => <li key={indicator}>{indicator}</li>)}</ul>
        </div>
      </Disclosure>
      <Disclosure kind="sources" label={narrative.page.details.sources}>
        <p>{period}</p>
        <ul>{card.sources.map((source) => <li key={source}>{source}</li>)}</ul>
      </Disclosure>
    </div>
  )
}

function EducationToTerritoryCard({
  card,
  narrative,
  section,
}: {
  card: Extract<VocacoesPneNarrativeCard, { direction: 'educacao_para_territorio' }>
  narrative: VocacoesPneNarrativeDocument
  section: VocacoesPneNarrativeSection
}) {
  return (
    <article className="vocacoes-pne-card vocacoes-pne-card--education" data-card-id={card.id}>
      <p className="vocacoes-pne-card__direction">{section.title}</p>
      <h3 id={`vocacoes-pne-card-${card.id}-title`} tabIndex={-1}>{card.title}</h3>
      <div className="vocacoes-pne-card__fact vocacoes-pne-card__fact--education">
        <p>{card.education_question}</p>
        {card.education_facts.map((fact) => <p key={fact}>{fact}</p>)}
      </div>
      <div className="vocacoes-pne-card__fact vocacoes-pne-card__fact--territory">
        {card.territorial_facts.map((fact) => <p key={fact}>{fact}</p>)}
      </div>
      <PrimaryVisual visual={card.primary_visual} />
      <p className="vocacoes-pne-card__reading">{card.integrated_reading}</p>
      <p className="vocacoes-pne-card__planning">{card.planning_question}</p>
      <CardDetails card={card} narrative={narrative} />
    </article>
  )
}

function TerritoryToEducationCard({
  card,
  narrative,
}: {
  card: Extract<VocacoesPneNarrativeCard, { direction: 'territorio_para_educacao' }>
  narrative: VocacoesPneNarrativeDocument
}) {
  return (
    <article className="vocacoes-pne-card vocacoes-pne-card--territory" data-card-id={card.id}>
      <p className="vocacoes-pne-card__direction">{card.future_label}</p>
      <h3 id={`vocacoes-pne-card-${card.id}-title`} tabIndex={-1}>{card.title}</h3>
      <p className="vocacoes-pne-card__transformation">{card.territorial_transformation}</p>
      <div className="vocacoes-pne-card__fact vocacoes-pne-card__fact--territory">
        {card.territorial_facts.map((fact) => <p key={fact}>{fact}</p>)}
      </div>
      <p className="vocacoes-pne-card__starting-point">{card.education_starting_point}</p>
      <PrimaryVisual visual={card.primary_visual} />
      <p className="vocacoes-pne-card__planning">{card.education_agenda}</p>
      <CardDetails card={card} narrative={narrative} />
    </article>
  )
}

function NarrativeCard({
  card,
  narrative,
  section,
}: {
  card: VocacoesPneNarrativeCard
  narrative: VocacoesPneNarrativeDocument
  section: VocacoesPneNarrativeSection
}) {
  return card.direction === 'educacao_para_territorio'
    ? <EducationToTerritoryCard card={card} narrative={narrative} section={section} />
    : <TerritoryToEducationCard card={card} narrative={narrative} />
}

function SeriesConsultation({ series }: { series: VocacoesSeries }) {
  return (
    <article className="vocacoes-pne-consultation-series" data-consultation-series-id={series.seriesId}>
      <h3>{series.label}</h3>
      <p>{series.unitLabel} · {series.periodLabel}</p>
      <p>{series.sourceLabel}</p>
      <ol>
        {series.points.map((point) => (
          <li key={point.period}>
            <span>{formatConsultationPeriod(point.period, series.periodGranularity)}</span>
            <span>{formatValue(point.value, series.unitLabel)}</span>
          </li>
        ))}
      </ol>
    </article>
  )
}

function DataConsultation({
  legacyDocument,
  narrative,
}: {
  legacyDocument: VocacoesDocument
  narrative: VocacoesPneNarrativeDocument
}) {
  return (
    <details className="vocacoes-pne-consultation">
      <summary>{narrative.consultation.title}</summary>
      <div className="vocacoes-pne-consultation__body">
        <p>{narrative.consultation.description}</p>
        <div className="vocacoes-pne-consultation__series">
          {legacyDocument.territoryPortrait.series.map((series) => (
            <SeriesConsultation key={series.seriesId} series={series} />
          ))}
        </div>
        <section className="vocacoes-pne-consultation__sources">
          <h2>{legacyDocument.sources.label}</h2>
          <p>{legacyDocument.sources.description}</p>
          <table>
            <caption className="u-sr-only">{legacyDocument.sources.label}</caption>
            <tbody>
              {legacyDocument.sources.items.map((source) => (
                <tr key={source.label}>
                  <th scope="row">{source.label}</th>
                  <td>{source.periodLabel}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      </div>
    </details>
  )
}

export function VocacoesPneNarrativeReport({
  legacyDocument,
  narrative,
}: {
  legacyDocument: VocacoesDocument
  narrative: VocacoesPneNarrativeDocument
}) {
  return (
    <div className="page-stack vocacoes-pne-page">
      <PnePageHeader
        actions={null}
        asideContent={null}
        asideLabel={null}
        context={`${narrative.region.name} · ${narrative.region.municipalityCount} municípios · ${narrative.region.stateCode}`}
        description={narrative.page.framing}
        eyebrow={narrative.page.eyebrow}
        title={narrative.page.title}
        variant="editorial"
      />

      <section className="vocacoes-pne-hero" aria-label={narrative.page.eyebrow}>
        <p className="vocacoes-pne-hero__reference">{narrative.page.referenceLabel}</p>
        <div className="vocacoes-pne-hero__highlights">
          {narrative.highlights.map((highlight) => (
            <button
              className="vocacoes-pne-highlight"
              data-card-target={highlight.cardId}
              key={highlight.cardId}
              onClick={(event) => focusNarrativeTarget(
                event,
                `vocacoes-pne-card-${highlight.cardId}-title`,
              )}
              type="button"
            >
              {highlight.label}
            </button>
          ))}
        </div>
      </section>

      <nav aria-label={narrative.page.eyebrow} className="vocacoes-pne-nav">
        {narrative.sections.map((section) => (
          <button
            data-section-target={section.id}
            key={section.id}
            onClick={(event) => focusNarrativeTarget(
              event,
              `vocacoes-pne-section-${section.id}-title`,
            )}
            type="button"
          >
            {section.title}
          </button>
        ))}
      </nav>

      {narrative.sections.map((section) => (
        <section
          className="vocacoes-pne-section"
          data-direction={section.cards[0]?.direction}
          key={section.id}
        >
          <header>
            <h2 id={`vocacoes-pne-section-${section.id}-title`} tabIndex={-1}>{section.title}</h2>
            <p>{section.question}</p>
          </header>
          <div className="vocacoes-pne-section__cards">
            {section.cards.map((card) => (
              <NarrativeCard
                card={card}
                key={card.id}
                narrative={narrative}
                section={section}
              />
            ))}
          </div>
        </section>
      ))}

      <DataConsultation legacyDocument={legacyDocument} narrative={narrative} />
    </div>
  )
}
