import { useId, useMemo, useRef, useState } from 'react'
import { ChartEmptyState, ChartLegend, ChartTooltip } from './ChartPrimitives'
import { closeChartTooltipOnEscape } from '../utils/chartVisuals'
import {
  buildPnePercentScale,
  buildPnePercentTicks,
  PNE_CHART_GEOMETRY,
  selectPneYearTicks,
} from '../utils/pneChartSystem'
import { useChartViewport } from '../hooks/useChartViewport'
import { buildProjectionEndLabelLayout } from '../utils/projectionEndLabels'

const DEFAULT_CHART_WIDTH = 980
const DEFAULT_CHART_HEIGHT = 260
const LEGACY_PADDING = { bottom: 44, left: 64, right: 68, top: 38 }

const percentFormatter = new Intl.NumberFormat('pt-BR', {
  maximumFractionDigits: 1,
  minimumFractionDigits: 1,
})
const countFormatter = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 0 })

export function IndicatorProjectionPanel({
  chartHeight = DEFAULT_CHART_HEIGHT,
  chartLabel,
  chartMaxYear = /** @type {number | null} */ (null),
  chartWidth = DEFAULT_CHART_WIDTH,
  compact = false,
  contentLabels = {},
  domainOverride = /** @type {{ max: number, min: number } | null} */ (null),
  maxXTicks = /** @type {number | null} */ (null),
  pneLayout = false,
  projection,
  showContextAlerts = true,
  showGoalReferenceLabel = true,
  showProjectedLegend = true,
  showSummaryCards = true,
  showTitle = true,
  contextOnly = false,
  showGoalReference = false,
  valueType = 'percent',
}) {
  const [activePoint, setActivePoint] = useState(null)
  const [tabStopYear, setTabStopYear] = useState(null)
  const pointRefs = useRef([])
  const chartId = useId().replace(/:/g, '')
  const { containerRef, width: measuredWidth } = useChartViewport(chartWidth)
  const responsiveChartWidth = pneLayout || compact ? measuredWidth : chartWidth
  const responsiveChartHeight = pneLayout
    ? measuredWidth < 300
      ? PNE_CHART_GEOMETRY.projection.mobileHeight
      : PNE_CHART_GEOMETRY.projection.desktopHeight
    : chartHeight

  const chart = useMemo(
    () => buildProjectionChart(projection, {
      chartHeight: responsiveChartHeight,
      chartMaxYear,
      chartMinYear: contextOnly ? projection?.historical_years?.[0] : undefined,
      chartWidth: responsiveChartWidth,
      compact,
      domainOverride,
      maxXTicks,
      padding: pneLayout ? PNE_CHART_GEOMETRY.projection.padding : LEGACY_PADDING,
      showGoalContext: !contextOnly || showGoalReference,
      valueType,
    }),
    [chartMaxYear, compact, contextOnly, domainOverride, maxXTicks, pneLayout, projection, responsiveChartHeight, responsiveChartWidth, showGoalReference, valueType],
  )
  const lastChartPointYear = chart.points.filter((point) => point.valid !== false).slice(-1)[0]?.year
  const transitionYear = chart.points.filter((point) => point.valid !== false && !point.isProjected).slice(-1)[0]?.year
  const latestHistoricalPoint = chart.points.filter((point) => point.valid !== false && !point.isProjected).slice(-1)[0]
  const projectedPointLabel = contentLabels.projectedPoint ?? 'Linha de base'
  const formatValue = (value) => formatProjectionValue(value, valueType)
  const accessibleChartLabel = chartLabel
    ? `${contentLabels.accessibleChartPrefix ?? 'Gráfico de linha de base de persistência'}: ${chartLabel}`
    : contentLabels.accessibleChartPrefix ?? 'Gráfico de linha de base de persistência'
  const focusablePoints = chart.points.filter((point) => point.valid !== false)
  const resolvedTabStopYear = focusablePoints.some((point) => point.year === tabStopYear)
    ? tabStopYear
    : focusablePoints[0]?.year

  function focusPoint(index) {
    const point = focusablePoints[index]
    if (!point) return
    setTabStopYear(point.year)
    pointRefs.current[index]?.focus()
  }

  function handlePointKeyDown(event, index) {
    if (event.key === 'Escape') {
      closeChartTooltipOnEscape(event, () => setActivePoint(null))
      return
    }

    let nextIndex = null
    if (event.key === 'ArrowRight') nextIndex = (index + 1) % focusablePoints.length
    if (event.key === 'ArrowLeft') nextIndex = (index - 1 + focusablePoints.length) % focusablePoints.length
    if (event.key === 'Home') nextIndex = 0
    if (event.key === 'End') nextIndex = focusablePoints.length - 1
    if (nextIndex === null) return

    event.preventDefault()
    focusPoint(nextIndex)
  }

  if (!projection?.available) {
    return (
      <div className="complementary-projection">
        <ChartEmptyState message={contentLabels.emptyMessage ?? 'Não há valores para o período selecionado.'} />
      </div>
    )
  }

  const projected2036 = projection.projected_2036
  const target = contextOnly && !showGoalReference ? null : projection.target_percent
  const distance = contextOnly && !showGoalReference ? null : projection.distance_to_target_2036
  const lastHistoricalPct = latestHistoricalPoint?.value ?? null
  const status = projection.status_2036
  const tendeAtingir = status === 'tende_a_atingir'
  const targetReferenceLabel = `${projection.target_label ?? 'Referência'}${projection.target_year ? ` ${projection.target_year}` : ''}`
  const targetDistanceLabel = projection.target_kind === 'monitoring'
    ? 'Distância da referência no cenário'
    : 'Distância da meta no cenário'

  return (
    <div className={`complementary-projection${contextOnly ? ' complementary-projection--context' : ''}${compact ? ' complementary-projection--compact' : ''}${contentLabels.variant ? ` complementary-projection--${contentLabels.variant}` : ''}`}>
      <div className="complementary-projection__header">
        {showTitle ? <h5>{contentLabels.title ?? (contextOnly ? 'Cenário de persistência até 2036' : 'Linha de base de persistência até 2036')}</h5> : null}
        {!contextOnly ? (
          <p className="complementary-projection__method">
            Este cenário mantém o último número observado de matrículas e atualiza o
            denominador com a variação populacional projetada para a faixa etária no RS.
            É uma linha de base para planejamento, sem intervalo probabilístico, e não
            representa uma previsão oficial.
          </p>
        ) : null}
      </div>

      {showSummaryCards ? <div className="complementary-projection__cards">
        <div className="complementary-projection__card">
          <span className="complementary-projection__card-label">{contentLabels.observedValue ?? (compact && latestHistoricalPoint?.year ? `Valor atual (${latestHistoricalPoint.year})` : contextOnly ? 'Último valor observado' : 'Valor atual')}</span>
          <span className="complementary-projection__card-value">
            {lastHistoricalPct != null
              ? `${formatValue(lastHistoricalPct)}${contextOnly && !compact && latestHistoricalPoint?.year ? ` (${latestHistoricalPoint.year})` : ''}`
              : '—'}
          </span>
        </div>
        <div className="complementary-projection__card">
          <span className="complementary-projection__card-label">{contentLabels.projectedValue ?? (compact ? 'Linha de base 2036' : 'Linha de base em 2036')}</span>
          <span className="complementary-projection__card-value">
            {projected2036 != null ? formatValue(projected2036) : '—'}
          </span>
        </div>
        {!contextOnly ? (
          <>
            <div className="complementary-projection__card">
              <span className="complementary-projection__card-label">{targetReferenceLabel}</span>
              <span className="complementary-projection__card-value">
                {target != null ? `${percentFormatter.format(target)}%` : '—'}
              </span>
            </div>
            <div className="complementary-projection__card">
              <span className="complementary-projection__card-label">{targetDistanceLabel}</span>
              <span className={`complementary-projection__card-value ${status == null ? '' : tendeAtingir ? 'complementary-projection__value--positive' : 'complementary-projection__value--negative'}`}>
                {distance != null ? `${distance >= 0 ? '+' : ''}${percentFormatter.format(distance)} p.p.` : '—'}
              </span>
            </div>
          </>
        ) : null}
      </div> : null}

      {chart.points.length > 0 ? (
        <>
          <ChartLegend
            className="complementary-projection__legend"
            items={[
              { key: 'observed', label: contentLabels.observedLegend ?? (transitionYear ? `Observado até ${transitionYear}` : 'Observado'), color: 'var(--chart-primary)' },
              ...(showProjectedLegend ? [{ key: 'projected', label: contentLabels.projectedLegend ?? 'Linha de base até 2036', color: contentLabels.projectedColor ?? (compact || !contextOnly ? 'var(--chart-primary)' : 'var(--chart-series-2)'), dashed: true }] : []),
              ...(chart.referencePaths.length ? [{ key: 'reference-trajectory', label: contentLabels.referenceLegend ?? 'Trajetória necessária para a referência', color: 'var(--chart-series-3)', dashed: true }] : []),
              ...(target != null ? [{ key: 'target', label: targetReferenceLabel, color: 'var(--chart-series-3)', dashed: true }] : []),
            ]}
          />
          <div
            className="history-chart__canvas complementary-projection__chart"
            ref={containerRef}
            role="region"
            aria-label={chartLabel ? `${compact ? 'Área interativa' : 'Área rolável'} do gráfico: ${chartLabel}` : `${compact ? 'Área interativa' : 'Área rolável'} do gráfico`}
            tabIndex={0}
          >
          <svg
            viewBox={`0 0 ${chart.width} ${chart.height}`}
            role="group"
            aria-label={accessibleChartLabel}
          >
            <defs>
              <clipPath id={`proj-clip-${chartId}`}>
                <rect
                  x={chart.padding.left}
                  y={chart.padding.top}
                  width={chart.width - chart.padding.left - chart.padding.right}
                  height={chart.height - chart.padding.top - chart.padding.bottom}
                />
              </clipPath>
            </defs>

            <g className="chart-grid" aria-hidden="true">
              {chart.yTicks.map((tick, i) => (
                <g key={i}>
                  <line
                    x1={chart.padding.left} x2={chart.width - chart.padding.right}
                    y1={tick.y} y2={tick.y}
                  />
                  <text x={chart.padding.left - 12} y={tick.y + 4} textAnchor="end">
                    {tick.label}
                  </text>
                </g>
              ))}
            </g>

            {chart.metaLine && (
              <g className="chart-meta-line" aria-hidden="true">
                <line
                  x1={chart.padding.left} x2={chart.width - chart.padding.right}
                  y1={chart.metaLine.y} y2={chart.metaLine.y}
                />
                {showGoalReferenceLabel && !chart.endLabels.meta?.hidden ? (
                  <text
                    x={chart.endLabels.meta?.x ?? chart.width - chart.padding.right - 6}
                    y={chart.endLabels.meta?.y ?? chart.metaLine.labelY}
                    textAnchor="end"
                    className="chart-meta-label"
                  >
                    {projection.target_label ?? 'Meta do PNE'}{projection.target_year ? ` · ${projection.target_year}` : ''} · {formatValue(target)}
                  </text>
                ) : null}
              </g>
            )}

            <g className="chart-axis" aria-hidden="true">
              <line className="chart-axis__x" x1={chart.padding.left} x2={chart.width - chart.padding.right} y1={chart.height - chart.padding.bottom} y2={chart.height - chart.padding.bottom} />
              <line className="chart-axis__y" x1={chart.padding.left} x2={chart.padding.left} y1={chart.padding.top} y2={chart.height - chart.padding.bottom} />
            </g>

            <g clipPath={`url(#proj-clip-${chartId})`} aria-hidden="true">
              {chart.areaPath && <path className="chart-area projection-area" d={chart.areaPath} />}
              {chart.historicalPaths.map((path, index) => (
                <path className="chart-line projection-line" d={path} key={`historical-${index}`} />
              ))}
              {chart.projectionPaths.map((path, index) => (
                <path className="chart-line projection-line--dashed" d={path} key={`projection-${index}`} />
              ))}
              {chart.referencePaths.map((path, index) => (
                <path className="chart-line projection-reference-trajectory" d={path} key={`reference-${index}`} />
              ))}
            </g>

            <g className="chart-points">
              {focusablePoints.map((point, index) => (
                <circle
                  ref={(element) => { pointRefs.current[index] = element }}
                  key={point.year}
                  role="img"
                  aria-label={`${point.isProjected ? projectedPointLabel : 'Observado'} ${point.year}: ${formatValue(point.value)}`}
                  aria-keyshortcuts="ArrowLeft ArrowRight Home End"
                  className={`chart-mark${point.isProjected ? ' is-projected' : ''}${point.year === transitionYear ? ' is-transition' : ''}${point.year === lastChartPointYear ? ' is-last' : ''}`}
                  cx={point.x} cy={point.y}
                  r={activePoint?.year === point.year ? 5.5 : point.year === transitionYear ? 5 : point.year === lastChartPointYear ? 4.5 : 3.5}
                  onMouseEnter={() => setActivePoint(point)}
                  onMouseLeave={() => setActivePoint(null)}
                  onFocus={() => {
                    setTabStopYear(point.year)
                    setActivePoint(point)
                  }}
                  onBlur={() => setActivePoint(null)}
                  onKeyDown={(event) => handlePointKeyDown(event, index)}
                  tabIndex={point.year === resolvedTabStopYear ? 0 : -1}
                >
                  <title>{`${point.year}: ${formatValue(point.value)}`}</title>
                </circle>
              ))}
            </g>

            <g className="chart-x-labels" aria-hidden="true">
              {chart.xTicks.map((tick, i, arr) => (
                <text
                  key={tick.year}
                  x={i === 0 ? tick.x + 4 : i === arr.length - 1 ? tick.x - 4 : tick.x}
                  y={chart.height - 20}
                  textAnchor={i === 0 ? 'start' : i === arr.length - 1 ? 'end' : 'middle'}
                >
                  {tick.year}
                </text>
              ))}
            </g>

            {chart.lastProjectedPoint && chart.endLabels.projected ? (
              <g className={`projection-direct-label${chart.endLabels.combined ? ' is-combined' : ''}`} aria-hidden="true">
                <text
                  x={chart.endLabels.projected.x}
                  y={chart.endLabels.projected.y}
                  textAnchor="end"
                >
                  {chart.endLabels.combined
                    ? `${chart.lastProjectedPoint.year} · Cenário e meta PNE: ${formatValue(chart.lastProjectedPoint.value)}`
                    : `${chart.lastProjectedPoint.year} · ${formatValue(chart.lastProjectedPoint.value)}`}
                </text>
              </g>
            ) : null}
          </svg>

          {activePoint && (
            <ChartTooltip
              className="history-chart__tooltip"
              label={activePoint.year}
              series={activePoint.isProjected ? projectedPointLabel : 'Observado'}
              value={activePoint.valid === false ? '—' : formatValue(activePoint.value)}
              style={{
                left: `${Math.min(92, Math.max(10, (activePoint.x / chart.width) * 100))}%`,
                top: `${(activePoint.y / chart.height) * 100}%`,
                transform: activePoint.y < chart.padding.top + 38
                  ? 'translate(-50%, 12px)'
                  : 'translate(-50%, calc(-100% - 12px))',
              }}
            />
          )}
          </div>
        </>
      ) : (
        <ChartEmptyState message="Série histórica insuficiente para exibir o gráfico." />
      )}

      {contextOnly ? (
        showContextAlerts && (projection.quality || projection.warnings?.length) ? (
          <div className="education-projection-alerts platform-coverage-note" role="note">
            {projection.quality ? <p><strong>Qualidade do cenário:</strong> {formatProjectionQuality(projection.quality)}.</p> : null}
            {projection.warnings?.length ? (
              <details className="education-projection-alerts__details">
                <summary>Alertas do cenário ({projection.warnings.length})</summary>
                <ul>
                  {projection.warnings.map((warning) => <li key={warning}>{warning}</li>)}
                </ul>
              </details>
            ) : null}
          </div>
        ) : null
      ) : (
        <div className="complementary-projection__reading">
          <p>{buildProjectionComparisonReading({ projection, status })}</p>
        </div>
      )}
    </div>
  )
}

function buildProjectionComparisonReading({ projection, status }) {
  if (status == null) return 'A comparação do cenário com a referência não está disponível.'

  const finalYear = projection.projected_end_year ?? 2036
  const targetYear = projection.target_year ?? null
  const reference = projection.target_kind === 'monitoring'
    ? 'referência de acompanhamento'
    : 'meta'
  const result = status === 'tende_a_atingir' ? 'alcança' : 'não alcança'
  if (targetYear != null && targetYear !== finalYear) {
    return `No cenário de ${finalYear}, o município ${result} a ${reference} prevista para ${targetYear}. Essa comparação não informa se ela foi atingida dentro do prazo legal.`
  }
  return `No cenário de ${finalYear}, o município ${result} a ${reference}${targetYear != null ? ` prevista para ${targetYear}` : ''}.`
}

function formatProjectionQuality(quality) {
  const labels = { alta: 'alta', media: 'média', baixa: 'baixa' }
  return labels[quality] ?? quality
}

function buildProjectionChart(projection, {
  chartHeight,
  chartMaxYear,
  chartMinYear,
  chartWidth,
  compact = false,
  domainOverride,
  maxXTicks,
  padding = LEGACY_PADDING,
  showGoalContext = true,
  valueType = 'percent',
} = {}) {
  const width = Math.max(180, Number(chartWidth) || DEFAULT_CHART_WIDTH)
  const height = Math.max(compact ? 180 : 240, Number(chartHeight) || DEFAULT_CHART_HEIGHT)
  const emptyChart = {
    areaPath: null,
    height,
    historicalPaths: [],
    metaLine: null,
    points: [],
    projectionPaths: [],
    referencePaths: [],
    padding,
    width,
    xTicks: [],
    yTicks: [],
    lastProjectedPoint: null,
    endLabels: { combined: false, meta: null, projected: null },
  }

  if (!projection?.available) {
    return emptyChart
  }

  const historicalPct = projection.historical_percent || []
  const historicalYears = projection.historical_years || []
  const firstHistoricalYear = historicalYears
    .map(Number)
    .filter(Number.isFinite)
    .sort((a, b) => a - b)[0]
  const CHART_MIN_YEAR = chartMinYear ?? Math.max(firstHistoricalYear ?? 2015, 2015)
  const CHART_MAX_YEAR = chartMaxYear ?? 2036
  const histPoints = historicalYears
    .map((y, i) => ({
      year: y,
      value: historicalPct[i],
      valid: historicalPct[i] != null && isFinite(historicalPct[i]) && y >= CHART_MIN_YEAR,
      isProjected: false,
    }))
    .filter((point) => point.year >= CHART_MIN_YEAR)

  const projPct = projection.projected_percent || []
  const projYears = projection.years || []
  const projPoints = projYears
    .map((y, i) => ({
      year: y,
      value: projPct[i],
      valid: projPct[i] != null && isFinite(projPct[i]),
      isProjected: true,
    }))

  const referenceValues = projection.reference_trajectory_values || []
  const referenceYears = projection.reference_trajectory_years || []
  const referencePoints = referenceYears.map((year, index) => ({
    year,
    value: referenceValues[index],
    valid: referenceValues[index] != null && isFinite(referenceValues[index]),
  }))

  const validPoints = [...histPoints, ...projPoints].filter((point) => point.valid)
  if (validPoints.length < 1) {
    return emptyChart
  }

  const allPoints = [...histPoints, ...projPoints]

  const target = showGoalContext ? projection.target_percent : null
  const values = validPoints.map(p => p.value)
  values.push(...referencePoints.filter((point) => point.valid).map((point) => point.value))
  if (target != null) values.push(target)
  const domain = domainOverride ?? (valueType === 'count'
    ? buildCountScale(values).domain
    : buildPnePercentScale(values).domain)
  const domainMin = domain.min
  const domainMax = domain.max

  const plotWidth = width - padding.left - padding.right
  const plotHeight = height - padding.top - padding.bottom

  const minYear = CHART_MIN_YEAR
  const maxYear = CHART_MAX_YEAR

  const xScale = (year) => padding.left + ((year - minYear) / (maxYear - minYear)) * plotWidth
  const yScale = (value) => padding.top + ((domainMax - value) / (domainMax - domainMin)) * plotHeight

  const scaledPoints = allPoints.map(p => ({
    ...p,
    x: xScale(p.year),
    y: p.valid ? yScale(p.value) : padding.top + plotHeight / 2,
  }))

  const histScaled = scaledPoints.filter((point) => !point.isProjected)
  const projScaled = scaledPoints.filter((point) => point.isProjected)
  const historicalSegments = buildProjectionSegments(histScaled)
  const projectionSegments = buildProjectionSegments(projScaled)
  const lastHist = histScaled.filter((point) => point.valid).slice(-1)[0]
  if (lastHist && projectionSegments.length > 0 && projectionSegments[0]?.[0]?.year === projScaled[0]?.year) {
    projectionSegments[0] = [lastHist, ...projectionSegments[0]]
  }
  const historicalPaths = historicalSegments.map(buildProjectionPath)
  const projectionPaths = projectionSegments.map(buildProjectionPath)
  const referenceScaled = referencePoints.map((point) => ({
    ...point,
    x: xScale(point.year),
    y: point.valid ? yScale(point.value) : padding.top + plotHeight / 2,
  }))
  const referencePaths = buildProjectionSegments(referenceScaled).map(buildProjectionPath)

  const allScaledValid = scaledPoints.filter(p => p.valid)
  const firstPt = allScaledValid[0]
  const lastPt = allScaledValid[allScaledValid.length - 1]
  const zeroY = height - padding.bottom

  const fullLinePath = allScaledValid.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(' ')
  const areaPath = allScaledValid.length > 1 && allPoints.every((point) => point.valid)
    ? `${fullLinePath} L${lastPt.x.toFixed(1)} ${zeroY.toFixed(1)} L${firstPt.x.toFixed(1)} ${zeroY.toFixed(1)} Z`
    : ''

  const yTickValues = valueType === 'count'
    ? buildCountScale(values, domain).ticks
    : buildPnePercentTicks(domain)
  const yTicks = yTickValues.map((value) => ({
    label: formatProjectionValue(value, valueType),
    value,
    y: yScale(value),
  }))

  const metaLine = target != null
    ? buildProjectionMetaLine({
        points: allScaledValid,
        value: target,
        chartHeight: height,
        chartWidth: width,
        padding,
        y: Math.max(padding.top, Math.min(yScale(target), height - padding.bottom)),
      })
    : null
  const lastProjectedPoint = projScaled.filter((point) => point.valid).slice(-1)[0] ?? null
  const endLabels = buildProjectionEndLabelLayout({
    chartHeight: height,
    chartWidth: width,
    lastProjectedPoint,
    metaLine,
    padding,
    projectedRawValue: Number(projection.raw_projected_2036),
    targetRawValue: Number(target),
    targetYear: Number(projection.target_year),
  })

  const responsiveXTickLimit = width < 320 ? 3 : width < 420 ? 5 : width < 520 ? 6 : 8
  const xTickLimit = maxXTicks == null ? responsiveXTickLimit : Math.min(maxXTicks, responsiveXTickLimit)
  const targetYear = Number(projection.target_year)
  const tickCandidates = Number.isFinite(targetYear) && targetYear >= minYear && targetYear <= maxYear
    ? [...allScaledValid, { year: targetYear, x: xScale(targetYear), valid: true }]
    : allScaledValid
  const xTicks = selectPneYearTicks(tickCandidates, xTickLimit)

  return {
    points: scaledPoints,
    yTicks,
    metaLine,
    areaPath,
    height,
    historicalPaths,
    padding,
    projectionPaths,
    referencePaths,
    width,
    xTicks,
    endLabels,
    lastProjectedPoint,
  }
}

function buildCountScale(values, suppliedDomain) {
  const finite = values.map(Number).filter(Number.isFinite)
  const maxValue = finite.length ? Math.max(...finite, 0) : 1
  const roughStep = maxValue > 0 ? maxValue / 4 : 1
  const magnitude = 10 ** Math.floor(Math.log10(roughStep))
  const normalized = roughStep / magnitude
  const step = (normalized <= 1 ? 1 : normalized <= 2 ? 2 : normalized <= 5 ? 5 : 10) * magnitude
  const domain = suppliedDomain ?? { min: 0, max: Math.max(step, Math.ceil(maxValue / step) * step) }
  const span = domain.max - domain.min
  return {
    domain,
    ticks: Array.from({ length: 5 }, (_item, index) => domain.min + (span * index) / 4),
  }
}

function formatProjectionValue(value, valueType) {
  if (value == null || !Number.isFinite(Number(value))) return '—'
  return valueType === 'count'
    ? countFormatter.format(Number(value))
    : `${percentFormatter.format(Number(value))}%`
}


function buildProjectionSegments(points) {
  const segments = []
  let current = []

  points.forEach((point) => {
    if (!point.valid) {
      if (current.length) segments.push(current)
      current = []
      return
    }
    current.push(point)
  })

  if (current.length) segments.push(current)
  return segments
}

function buildProjectionPath(points) {
  return points
    .map((point, index) => `${index === 0 ? 'M' : 'L'}${point.x.toFixed(1)} ${point.y.toFixed(1)}`)
    .join(' ')
}

function buildProjectionMetaLine({ chartHeight, chartWidth, padding, points, value, y }) {
  const plotTop = padding.top
  const plotBottom = chartHeight - padding.bottom
  const labelX = chartWidth - padding.right - 6
  let labelY = y - 12

  if (y < plotTop + 24) {
    labelY = y + 20
  } else if (y > plotBottom - 18) {
    labelY = y - 14
  }

  const rightSideCollision = points.some((point) => (
    point.valid !== false &&
    Math.abs(point.x - labelX) < 132 &&
    Math.abs(point.y - labelY) < 22
  ))

  if (rightSideCollision) {
    const hasRoomAbove = y - 28 > plotTop
    labelY = hasRoomAbove ? y - 28 : y + 28
  }

  return {
    labelY: Math.max(plotTop + 14, Math.min(labelY, plotBottom - 12)),
    value,
    y,
  }
}
