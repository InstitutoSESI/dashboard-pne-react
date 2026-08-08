import { useMemo, useState } from 'react'
import { getBoundedDomain } from '../utils/chartDomain.js'
import { useChartViewport } from '../hooks/useChartViewport'
import { isMissing } from '../utils/educationFormatters'
import { selectPneYearTicks } from '../utils/pneChartSystem'
import { closeChartTooltipOnEscape, resolveChartColor } from '../utils/chartVisuals'
import { ChartEmptyState, ChartTooltip } from './ChartPrimitives'

const FALLBACK_CHART_WIDTH = 760

export function EducationLineChart({
  series,
  title,
  color = '#16713a',
  formatLabel = (v) => String(v),
  hideTitle = false,
  integerTicks = false,
  scaleType = 'count',
  showPointLabels = false,
}) {
  const [activePoint, setActivePoint] = useState(null)
  const { containerRef, width: chartWidth } = useChartViewport(FALLBACK_CHART_WIDTH)
  const chartHeight = chartWidth < 420 ? 280 : 300
  const chart = useMemo(
    () => buildChart(series, scaleType, chartWidth, chartHeight, integerTicks),
    [chartHeight, chartWidth, integerTicks, scaleType, series],
  )
  const resolvedColor = resolveChartColor(color)

  if (!chart || chart.points.length < 2) {
    return (
      <ChartEmptyState message="Histórico não disponível." />
    )
  }

  return (
    <div className="education-chart">
      {title && !hideTitle ? <h4 className="education-chart__title">{title}</h4> : null}
      <div className="education-chart__canvas" ref={containerRef}>
        <svg
          viewBox={`0 0 ${chartWidth} ${chartHeight}`}
          role="img"
          aria-label={title || 'Gráfico de linha'}
          data-series-segments={chart.linePaths.length}
        >
          <g className="chart-grid">
            {chart.yTicks.map((tick, i) => (
              <g key={`y-${i}`}>
                <line x1={chart.padding.left} x2={chartWidth - chart.padding.right} y1={tick.y} y2={tick.y} stroke="var(--chart-grid)" strokeWidth="1" />
                <text x={chart.padding.left - 10} y={tick.y + 4} textAnchor="end" className="chart-axis-label">{tick.label}</text>
              </g>
            ))}
          </g>
          <line x1={chart.padding.left} x2={chartWidth - chart.padding.right} y1={chartHeight - chart.padding.bottom} y2={chartHeight - chart.padding.bottom} stroke="var(--chart-axis)" strokeWidth="1" />
          <line x1={chart.padding.left} x2={chart.padding.left} y1={chart.padding.top} y2={chartHeight - chart.padding.bottom} stroke="var(--chart-axis)" strokeWidth="1" />
          {chart.areaPaths.map((path, index) => (
            <path className="education-chart__series-area" d={path} fill={resolvedColor} fillOpacity="0.08" key={`area-${index}`} />
          ))}
          {chart.linePaths.map((path, index) => (
            <path className="education-chart__series-line" d={path} fill="none" stroke={resolvedColor} strokeWidth="2.25" strokeLinejoin="round" key={`line-${index}`} />
          ))}
          {chart.points.map((point, i) => (
            <g key={`pt-${i}`}>
              <circle
                aria-label={`${title || 'Município'}, ${point.year}: ${formatLabel(point.value)}`}
                className={`chart-mark${point.isLast ? ' is-last' : ''}`}
                cx={point.x} cy={point.y} r={activePoint?.year === point.year ? 5 : 3.5}
                fill={resolvedColor}
                onBlur={() => setActivePoint(null)}
                onFocus={() => setActivePoint(point)}
                onKeyDown={(event) => closeChartTooltipOnEscape(event, () => setActivePoint(null))}
                onMouseEnter={() => setActivePoint(point)}
                onMouseLeave={() => setActivePoint(null)}
                tabIndex="0"
                style={{ cursor: 'pointer' }}
              >
                <title>{`${title || 'Município'}, ${point.year}: ${formatLabel(point.value)}`}</title>
              </circle>
              {showPointLabels && point.showLabel ? (
                <text
                  x={point.x}
                  y={point.y < chart.padding.top + 18 ? point.y + 18 : point.y - 10}
                  textAnchor="middle"
                  className={point.isLast ? 'chart-point-label is-last' : 'chart-point-label'}
                >
                  {formatLabel(point.value)}
                </text>
              ) : null}
            </g>
          ))}
          <g className="chart-x-labels">
            {chart.xTicks.map((tick) => (
              <text x={tick.x} y={chartHeight - 14} textAnchor="middle" className="chart-x-label" key={tick.year}>{tick.year}</text>
            ))}
          </g>
        </svg>
        {activePoint && (
          <ChartTooltip
            className="education-chart__tooltip"
            label={activePoint.year}
            series={title || 'Município'}
            value={formatLabel(activePoint.value)}
            style={{
              left: `${Math.min(90, Math.max(10, (activePoint.x / chartWidth) * 100))}%`,
              top: `${(activePoint.y / chartHeight) * 100}%`,
              transform: activePoint.y < chart.padding.top + 46
                ? 'translate(-50%, 12px)'
                : 'translate(-50%, calc(-100% - 12px))',
            }}
          />
        )}
      </div>
    </div>
  )
}

function buildChart(series, scaleType, chartWidth, chartHeight, integerTicks = false) {
  if (!Array.isArray(series) || series.length < 2) return null
  const padding = chartWidth < 420
    ? { top: 30, right: 34, bottom: 40, left: 64 }
    : { top: 34, right: 56, bottom: 42, left: 76 }
  const rawPoints = normalizeChartYearSeries(series)
    .filter((p) => p.ano)
    .map((p) => ({
      year: Number(p.ano),
      value: isMissing(p.valor) ? null : Number(p.valor),
      valid: !isMissing(p.valor) && Number.isFinite(Number(p.valor)),
    }))
    .sort((a, b) => a.year - b.year)
  const points = rawPoints.filter((point) => point.valid)
  if (points.length < 2) return null
  const values = points.map((p) => p.value)
  const domain = integerTicks && Math.max(...values) <= 20
    ? getSmallIntegerDomain(values)
    : getYAxisDomain(values, scaleType)
  const range = domain.max - domain.min || 1
  const years = rawPoints.map((p) => p.year)
  const minYear = Math.min(...years); const maxYear = Math.max(...years)
  const yearRange = maxYear - minYear || 1
  const plotW = chartWidth - padding.left - padding.right
  const plotH = chartHeight - padding.top - padding.bottom
  const xScale = (year) => padding.left + ((year - minYear) / yearRange) * plotW
  const yScale = (val) => padding.top + ((domain.max - val) / (domain.max - domain.min || 1)) * plotH
  const minValue = Math.min(...values)
  const maxValue = Math.max(...values)
  const firstYear = points[0].year
  const lastYear = points[points.length - 1].year
  const scaledRaw = rawPoints.map((p) => ({
    ...p,
    x: xScale(p.year),
    y: p.valid ? yScale(p.value) : null,
    isLast: p.year === lastYear,
    showLabel: p.valid && shouldShowPointLabel(p, points.length, chartWidth, { firstYear, lastYear, minValue, maxValue }),
  }))
  const scaled = scaledRaw.filter((point) => point.valid)
  const segments = buildLineSegments(scaledRaw)
  const baselineY = yScale(domain.min)
  const linePaths = segments.map((segment) => segment.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(' '))
  const areaPaths = segments.flatMap((segment, index) => segment.length > 1
    ? [`${linePaths[index]} L${segment[segment.length - 1].x.toFixed(1)} ${baselineY.toFixed(1)} L${segment[0].x.toFixed(1)} ${baselineY.toFixed(1)} Z`]
    : [])
  const yTicksRaw = integerTicks && domain.max <= 20
    ? buildIntegerTicks(domain)
    : [domain.min, domain.min + range * 0.25, domain.min + range * 0.5, domain.min + range * 0.75, domain.max]
  const yTicks = yTicksRaw.map((val) => ({ label: formatAxisTick(val, scaleType), y: yScale(val) }))
  const xTickLimit = chartWidth < 420 ? 3 : chartWidth < 620 ? 5 : 7
  return { areaPaths, linePaths, padding, points: scaled, xTicks: selectPneYearTicks(scaledRaw, xTickLimit), yTicks }
}

function getSmallIntegerDomain(values) {
  const max = Math.max(...values, 1)
  const step = Math.max(1, Math.ceil(max / 4))
  return { min: 0, max: Math.ceil(max / step) * step }
}

function buildIntegerTicks(domain) {
  const step = Math.max(1, Math.ceil((domain.max - domain.min) / 4))
  const ticks = []
  for (let value = domain.min; value <= domain.max; value += step) ticks.push(value)
  if (ticks[ticks.length - 1] !== domain.max) ticks.push(domain.max)
  return ticks
}

function normalizeChartYearSeries(series) {
  const byYear = new Map()
  series.forEach((point) => {
    if (!point || isMissing(point.ano)) return
    const year = Number(point.ano)
    if (!Number.isFinite(year)) return
    byYear.set(year, { ...point, ano: year })
  })
  return Array.from(byYear.values()).sort((a, b) => Number(a.ano) - Number(b.ano))
}

function buildLineSegments(points) {
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

function shouldShowPointLabel(point, pointCount, chartWidth, { firstYear, lastYear, minValue, maxValue }) {
  if (chartWidth < 420) return point.year === firstYear || point.year === lastYear
  if (pointCount <= 7) return true
  return (
    point.year === firstYear ||
    point.year === lastYear ||
    point.value === minValue ||
    point.value === maxValue
  )
}

function getYAxisDomain(values, scaleType) {
  const minVal = Math.min(...values)
  const maxVal = Math.max(...values)
  const rawRange = maxVal - minVal

  if (scaleType === 'percent' || scaleType === 'ideb' || scaleType === 'inse') {
    return getBoundedDomain(values, scaleType)
  }

  if (scaleType === 'saeb') {
    const margin = Math.max(rawRange * 0.45, 20)
    return niceDomain(Math.max(0, minVal - margin), maxVal + margin)
  }

  if (scaleType === 'ratio') {
    const margin = Math.max(rawRange * 0.45, 0.02)
    if (minVal === maxVal) {
      return {
        min: Math.max(0, minVal - 0.05),
        max: Math.min(1, maxVal + 0.05),
      }
    }
    const domain = niceDomain(Math.max(0, minVal - margin), Math.min(1, maxVal + margin))
    return { min: Math.max(0, domain.min), max: Math.min(1, domain.max) }
  }

  if (scaleType === 'count') {
    if (maxVal <= 0) return niceDomain(minVal, maxVal)
    const relativeRange = rawRange / maxVal
    if (relativeRange > 0.35 || minVal < maxVal * 0.35) {
      return niceDomain(0, maxVal * 1.08)
    }
    const margin = Math.max(rawRange * 1.2, maxVal * 0.12, 1)
    return niceDomain(Math.max(0, minVal - margin), maxVal + margin)
  }

  const margin = Math.max(rawRange * 0.6, Math.abs(maxVal) * 0.1, 1)
  return niceDomain(Math.max(0, minVal - margin), maxVal + margin)
}

function niceDomain(min, max) {
  if (!Number.isFinite(min) || !Number.isFinite(max)) return { min: 0, max: 1 }
  if (min === max) {
    const margin = Math.max(Math.abs(max) * 0.15, 1)
    return { min: Math.max(0, min - margin), max: max + margin }
  }
  const span = max - min
  const step = niceStep(span / 4)
  return {
    min: Math.floor(min / step) * step,
    max: Math.ceil(max / step) * step,
  }
}

function niceStep(value) {
  if (!Number.isFinite(value) || value <= 0) return 1
  const power = 10 ** Math.floor(Math.log10(value))
  const scaled = value / power
  if (scaled <= 1) return power
  if (scaled <= 2) return 2 * power
  if (scaled <= 5) return 5 * power
  return 10 * power
}

function formatAxisTick(value, scaleType) {
  const digits = scaleType === 'ratio' ? 2 : scaleType === 'ideb' || scaleType === 'inse' ? 1 : 0
  return value.toLocaleString('pt-BR', { maximumFractionDigits: digits })
}
