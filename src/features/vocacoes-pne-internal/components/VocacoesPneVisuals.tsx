import { Info, Minus, Plus } from 'lucide-react'
import { useId, type ReactNode } from 'react'
import {
  availabilityLabel,
  firstObservedPoint,
  formatUiValue,
  latestObservedPoint,
  lensLabel,
  unitLabel,
} from '../vocacoesPneSelectors'
import type {
  AvailabilityState,
  UiV2Distribution,
  UiV2Series,
  UiV2Source,
  UiV2VisualContract,
} from '../vocacoesPneUiV2Types'

export function AvailabilityValue({
  state,
  unit,
  value,
  fractionDigits,
}: {
  state: AvailabilityState
  unit: string
  value: number | null
  fractionDigits?: number
}) {
  if (state === 'observed' || state === 'observed_zero') {
    return (
      <span className="vpi-value-state" data-availability-state={state}>
        <strong>{formatUiValue(value, unit, fractionDigits)}</strong>
        {state === 'observed_zero' ? <small>Zero observado</small> : null}
      </span>
    )
  }
  return (
    <span className="vpi-value-state vpi-value-state--missing" data-availability-state={state}>
      <strong aria-hidden="true">—</strong>
      <small>{availabilityLabel(state)}</small>
    </span>
  )
}

export function VisualMeta({
  contract,
  sourceLabels,
  sourceRefs,
  period,
  unit,
  lens,
}: {
  contract: UiV2VisualContract
  sourceLabels: Map<string, string>
  sourceRefs: string[]
  period: string
  unit: string
  lens: string
}) {
  const tooltipId = useId()
  return (
    <div className="vpi-visual-meta" aria-label="Metadados da visualização">
      <span><b>Medida:</b> {contract.measure}</span>
      <span><b>Unidade:</b> {unitLabel(unit)}</span>
      <span><b>Período:</b> {period}</span>
      <span><b>Lente:</b> {lensLabel(lens)}</span>
      <span><b>Fonte:</b> {sourceRefs.map((ref) => sourceLabels.get(ref) ?? ref).join('; ')}</span>
      <span className="vpi-tooltip-wrap">
        <button type="button" className="vpi-tooltip-trigger" aria-describedby={tooltipId}>
          <Info aria-hidden="true" size={15} />
          Como ler
        </button>
        <span id={tooltipId} role="tooltip" className="vpi-tooltip">
          {contract.tooltip} Comparação: {contract.comparisonRule}
        </span>
      </span>
    </div>
  )
}

interface ChartSeries {
  label: string
  series: UiV2Series | null
  role: 'municipality' | 'region'
}

function observedPoints(series: UiV2Series | null) {
  return series?.points.filter((point) => (
    point.value !== null
    && (point.availabilityState === 'observed' || point.availabilityState === 'observed_zero')
  )) ?? []
}

export function SeriesComparisonChart({
  title,
  description,
  municipality,
  region,
}: {
  title: string
  description: string
  municipality: ChartSeries | null
  region: ChartSeries
}) {
  const titleId = useId()
  const descriptionId = useId()
  const municipalityFocused = Boolean(municipality?.series)
  const entries = municipalityFocused && municipality ? [municipality] : [region]
  const textEntries = municipalityFocused ? [...entries, region] : entries
  const allPoints = entries.flatMap((entry) => observedPoints(entry.series))
  if (allPoints.length === 0) {
    return <UnavailablePanel title={title} state="unavailable" />
  }
  const years = [...new Set(allPoints.map((point) => point.year))].sort((a, b) => a - b)
  const values = allPoints.map((point) => point.value as number)
  const minimum = Math.min(...values)
  const maximum = Math.max(...values)
  const span = maximum - minimum || Math.max(Math.abs(maximum), 1)
  const chartMin = minimum - span * 0.08
  const chartMax = maximum + span * 0.08
  const width = 720
  const height = 248
  const margin = { top: 24, right: 24, bottom: 38, left: 54 }
  const innerWidth = width - margin.left - margin.right
  const innerHeight = height - margin.top - margin.bottom
  const x = (year: number) => margin.left + (
    years.length === 1 ? innerWidth / 2 : ((year - years[0]) / (years[years.length - 1] - years[0])) * innerWidth
  )
  const y = (value: number) => margin.top + ((chartMax - value) / (chartMax - chartMin)) * innerHeight
  const unit = entries.find((entry) => entry.series)?.series?.unit ?? 'count'
  const tickValues = [chartMax, (chartMax + chartMin) / 2, chartMin]

  return (
    <figure className="vpi-chart" data-visual="series-comparison">
      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-labelledby={`${titleId} ${descriptionId}`}>
        <title id={titleId}>{title}</title>
        <desc id={descriptionId}>{description}</desc>
        {tickValues.map((tick) => (
          <g key={tick}>
            <line className="vpi-chart__grid" x1={margin.left} x2={width - margin.right} y1={y(tick)} y2={y(tick)} />
            <text className="vpi-chart__axis-label" x={margin.left - 8} y={y(tick) + 4} textAnchor="end">
              {formatUiValue(tick, unit, 1)}
            </text>
          </g>
        ))}
        {years.filter((_, index) => index === 0 || index === years.length - 1 || years.length <= 5).map((year) => (
          <text key={year} className="vpi-chart__axis-label" x={x(year)} y={height - 12} textAnchor="middle">{year}</text>
        ))}
        {years.includes(2020) && years.includes(2021) ? (
          <g aria-label="2020 e 2021: cautela de continuidade">
            <rect className="vpi-chart__caution" x={x(2020) - 10} y={margin.top} width={Math.max(24, x(2021) - x(2020) + 20)} height={innerHeight} />
            <text className="vpi-chart__caution-label" x={x(2020)} y={margin.top + 14}>cautela</text>
          </g>
        ) : null}
        {entries.map((entry) => {
          const points = observedPoints(entry.series)
          const path = points.map((point, index) => `${index === 0 ? 'M' : 'L'} ${x(point.year)} ${y(point.value as number)}`).join(' ')
          return (
            <g key={entry.role} className={`vpi-chart__series vpi-chart__series--${entry.role}`}>
              <path d={path} fill="none" />
              {points.map((point) => (
                <g key={point.year} tabIndex={0} role="img" aria-label={`${entry.label}, ${point.year}: ${formatUiValue(point.value, point.unit, 1)}. ${availabilityLabel(point.availabilityState)}`}>
                  <title>{`${entry.label} · ${point.year} · ${formatUiValue(point.value, point.unit, 1)}`}</title>
                  {entry.role === 'region' ? (
                    <rect x={x(point.year) - 3.5} y={y(point.value as number) - 3.5} width="7" height="7" />
                  ) : (
                    <circle cx={x(point.year)} cy={y(point.value as number)} r="4" />
                  )}
                </g>
              ))}
            </g>
          )
        })}
      </svg>
      <figcaption>
        {!municipalityFocused && region.series ? <span className="vpi-legend-key vpi-legend-key--region"><i aria-hidden="true" />{region.label}</span> : null}
        {municipality?.series ? <span className="vpi-legend-key vpi-legend-key--municipality"><i aria-hidden="true" />{municipality.label}</span> : null}
      </figcaption>
      {municipalityFocused && region.series ? (
        <div className="vpi-chart__regional-context">
          <span>Contexto regional</span>
          <p>
            <b>{region.label}:</b>{' '}
            {firstObservedPoint(region.series)?.year}: {formatUiValue(firstObservedPoint(region.series)?.value ?? null, region.series.unit, 1)}
            {' → '}
            {latestObservedPoint(region.series)?.year}: {formatUiValue(latestObservedPoint(region.series)?.value ?? null, region.series.unit, 1)}
          </p>
        </div>
      ) : null}
      <div className="vpi-chart__mobile-fallback" aria-label="Resumo textual da série">
        {textEntries.map((entry) => {
          const first = firstObservedPoint(entry.series)
          const latest = latestObservedPoint(entry.series)
          return (
            <p key={entry.role}>
              <b>{entry.label}:</b>{' '}
              {first ? `${first.year}: ${formatUiValue(first.value, first.unit, 1)}` : 'início indisponível'}
              {' → '}
              {latest ? `${latest.year}: ${formatUiValue(latest.value, latest.unit, 1)}` : 'fim indisponível'}
            </p>
          )
        })}
      </div>
    </figure>
  )
}

export function DistributionPlot({
  distribution,
  municipalityNames,
  selectedMunicipalityId,
}: {
  distribution: UiV2Distribution | null
  municipalityNames: Map<string, string>
  selectedMunicipalityId: string | null
}) {
  if (!distribution) return <UnavailablePanel title="Distribuição municipal" state="unavailable" />
  const observed = distribution.municipalValues.filter((item) => item.value !== null)
  const values = observed.map((item) => item.value as number)
  const min = Math.min(...values)
  const max = Math.max(...values)
  const span = max - min || 1
  const position = (value: number) => ((value - min) / span) * 100
  return (
    <figure className="vpi-distribution" data-visual="municipal-distribution">
      <div className="vpi-distribution__axis" aria-label={`${distribution.label}; ${distribution.valeMedianLabel}: ${formatUiValue(distribution.valeMunicipalMedian, distribution.unit, 1)}`}>
        <span className="vpi-distribution__min">{formatUiValue(min, distribution.unit, 1)}</span>
        <span className="vpi-distribution__max">{formatUiValue(max, distribution.unit, 1)}</span>
        {distribution.valeMunicipalMedian !== null ? (
          <span className="vpi-distribution__median" style={{ left: `${position(distribution.valeMunicipalMedian)}%` }}>
            <b>Mediana</b>
          </span>
        ) : null}
        {observed.map((item) => {
          const selected = item.municipalityIbgeCode === selectedMunicipalityId
          const name = municipalityNames.get(item.municipalityIbgeCode) ?? item.municipalityIbgeCode
          return (
            <span
              key={item.municipalityIbgeCode}
              className={`vpi-distribution__dot ${selected ? 'is-selected' : ''}`}
              style={{ left: `${position(item.value as number)}%` }}
              role="img"
              aria-label={`${name}: ${formatUiValue(item.value, distribution.unit, 1)}${selected ? ', município selecionado' : ''}`}
              tabIndex={0}
            >
              <span className="sr-only">{name}</span>
            </span>
          )
        })}
      </div>
      <figcaption>
        {distribution.label}. {distribution.valeMedianLabel}; RS aparece como {distribution.rsMunicipalDistribution.label.toLocaleLowerCase('pt-BR')}.
      </figcaption>
      <ul className="vpi-distribution__mobile-fallback">
        {distribution.municipalValues.map((item) => (
          <li key={item.municipalityIbgeCode} className={item.municipalityIbgeCode === selectedMunicipalityId ? 'is-selected' : ''}>
            <span>{municipalityNames.get(item.municipalityIbgeCode)}</span>
            <b>{formatUiValue(item.value, distribution.unit, 1)}</b>
          </li>
        ))}
      </ul>
    </figure>
  )
}

export function EndpointCard({
  label,
  series,
  compact = false,
}: {
  label: string
  series: UiV2Series | null
  compact?: boolean
}) {
  const first = firstObservedPoint(series)
  const latest = latestObservedPoint(series)
  const state = latest?.availabilityState ?? 'unavailable'
  return (
    <article className={`vpi-endpoint-card ${compact ? 'vpi-endpoint-card--compact' : ''}`}>
      <h4>{label}</h4>
      {first && latest ? (
        <div className="vpi-endpoint-card__values">
          <span><small>{first.year}</small><b>{formatUiValue(first.value, first.unit, 1)}</b></span>
          <span aria-hidden="true">→</span>
          <span><small>{latest.year}</small><b>{formatUiValue(latest.value, latest.unit, 1)}</b></span>
        </div>
      ) : (
        <AvailabilityValue state={state} value={latest?.value ?? null} unit={series?.unit ?? 'count'} />
      )}
      {state === 'observed_zero' ? <small className="vpi-zero-label">Zero observado</small> : null}
      <p>{series ? `${unitLabel(series.unit)} · ${lensLabel(series.territorialLens)}` : availabilityLabel('unavailable')}</p>
    </article>
  )
}

export function UnavailablePanel({
  title,
  state,
  note,
}: {
  title: string
  state: AvailabilityState
  note?: string
}) {
  return (
    <div className="vpi-unavailable" data-availability-state={state} role="status">
      <strong>{title}</strong>
      <span>{availabilityLabel(state)}</span>
      {note ? <p>{note}</p> : null}
    </div>
  )
}

export function EvidenceDisclosure({
  title = 'Ver evidências e limites',
  children,
  open = false,
  testId,
}: {
  title?: string
  children: ReactNode
  open?: boolean
  testId?: string
}) {
  return (
    <details className="vpi-disclosure" open={open} data-testid={testId}>
      <summary>
        <span>{title}</span>
        <Plus className="vpi-disclosure__plus" aria-hidden="true" size={17} />
        <Minus className="vpi-disclosure__minus" aria-hidden="true" size={17} />
      </summary>
      <div className="vpi-disclosure__content">{children}</div>
    </details>
  )
}

export function SourceLimitDisclosure({
  sources,
  sourceRefs,
  limits,
}: {
  sources: Map<string, UiV2Source>
  sourceRefs: string[]
  limits: Array<{ limitId: string; appliesTo: string; statement: string }>
}) {
  return (
    <EvidenceDisclosure title="Fontes, lentes e limites">
      <div className="vpi-source-limit-grid">
        <section>
          <h4>Fontes congeladas</h4>
          <ul>
            {sourceRefs.map((ref) => {
              const source = sources.get(ref)
              return (
                <li key={ref}>
                  <b>{source?.label ?? ref}</b>
                  <span>{source?.period ?? 'período específico'} · {(source?.territorialLenses ?? []).map(lensLabel).join(', ')}</span>
                </li>
              )
            })}
          </ul>
        </section>
        <section>
          <h4>Limites transportados</h4>
          <ul>{limits.map((item) => <li key={item.limitId}>{item.statement}</li>)}</ul>
        </section>
      </div>
    </EvidenceDisclosure>
  )
}

export function PlanningQuestion({ children }: { children: ReactNode }) {
  return (
    <aside className="vpi-planning-question">
      <span>Questão de planejamento</span>
      <p>{children}</p>
    </aside>
  )
}
