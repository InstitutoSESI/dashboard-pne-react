import { useMemo, useState } from 'react'
import { isMissing } from '../utils/educationFormatters'
import { chartSeriesColor, closeChartTooltipOnEscape } from '../utils/chartVisuals'
import { selectPneYearTicks } from '../utils/pneChartSystem'
import { ChartEmptyState, ChartLegend, ChartTooltip } from './ChartPrimitives'

const CHART_WIDTH = 820
const CHART_HEIGHT = 340
const PADDING = { top: 26, right: 32, bottom: 50, left: 104 }
const BAR_GAP = 8

export function EducationStackedBarChart({
  categories,
  data,
  title,
  sectionTitle,
  formatLabel = (v) => String(v),
}) {
  const [activeSegment, setActiveSegment] = useState(null)
  const chart = useMemo(() => buildStackedChart(data, categories), [categories, data])

  if (!chart || chart.rows.length === 0 || chart.categories.length === 0) {
    return (
      <ChartEmptyState />
    )
  }

  return (
    <div className="education-chart education-chart--stacked">
      {title && title !== sectionTitle ? <h4 className="education-chart__title">{title}</h4> : null}
      {chart.categories.length ? (
        <ChartLegend className="education-stacked-legend" items={chart.categories} />
      ) : null}
      <div className="education-chart__canvas">
        <svg viewBox={`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`} role="img" aria-label={title || 'Gráfico de barras empilhadas'}>
          <g className="chart-grid">
            {chart.yTicks.map((tick, i) => (
              <g key={`y-${i}`}>
                <line x1={PADDING.left} x2={CHART_WIDTH - PADDING.right} y1={tick.y} y2={tick.y} stroke="var(--chart-grid)" strokeWidth="1" />
                <text x={PADDING.left - 10} y={tick.y + 4} textAnchor="end" className="chart-axis-label">{tick.label}</text>
              </g>
            ))}
          </g>
          <line x1={PADDING.left} x2={CHART_WIDTH - PADDING.right} y1={CHART_HEIGHT - PADDING.bottom} y2={CHART_HEIGHT - PADDING.bottom} stroke="var(--chart-axis)" strokeWidth="1" />
          <line x1={PADDING.left} x2={PADDING.left} y1={PADDING.top} y2={CHART_HEIGHT - PADDING.bottom} stroke="var(--chart-axis)" strokeWidth="1" />
          {chart.rows.map((row) => (
            <g key={row.year}>
              {row.segments.map((segment) => (
                <rect
                  aria-label={`${segment.label}, ${row.year}: ${formatLabel(segment.value)}`}
                  className="chart-mark"
                  key={`${row.year}-${segment.key}`}
                  x={segment.x}
                  y={segment.y}
                  width={segment.width}
                  height={segment.height}
                  fill={segment.color}
                  fillOpacity={activeSegment?.year === row.year && activeSegment?.key === segment.key ? '1' : '0.86'}
                  rx="3"
                  onBlur={() => setActiveSegment(null)}
                  onFocus={() => setActiveSegment(segment)}
                  onKeyDown={(event) => closeChartTooltipOnEscape(event, () => setActiveSegment(null))}
                  onMouseEnter={() => setActiveSegment(segment)}
                  onMouseLeave={() => setActiveSegment(null)}
                  tabIndex="0"
                  style={{ cursor: 'pointer', transition: 'fill-opacity 0.12s' }}
                >
                  <title>{`${segment.label}, ${row.year}: ${formatLabel(segment.value)}`}</title>
                </rect>
              ))}
              {chart.visibleYearSet.has(row.year) ? (
                <text x={row.x + row.width / 2} y={CHART_HEIGHT - 18} textAnchor="middle" className="chart-x-label">{row.year}</text>
              ) : null}
            </g>
          ))}
        </svg>
        {activeSegment && (
          <ChartTooltip
            className="education-chart__tooltip education-chart__tooltip--bar"
            label={activeSegment.year}
            items={activeSegment.tooltipValues.map((item) => ({
              ...item,
              value: item.missing ? 'Dado não disponível' : formatLabel(item.value),
            }))}
            style={{
              left: `${Math.min(88, Math.max(12, ((activeSegment.x + activeSegment.width / 2) / CHART_WIDTH) * 100))}%`,
              top: `${Math.min(82, Math.max(12, (activeSegment.y / CHART_HEIGHT) * 100))}%`,
              transform: activeSegment.y < PADDING.top + 46
                ? 'translate(-50%, 12px)'
                : 'translate(-50%, calc(-100% - 12px))',
            }}
          />
        )}
      </div>
    </div>
  )
}

function buildStackedChart(data, categories) {
  if (!Array.isArray(data) || !Array.isArray(categories) || !data.length || !categories.length) return null

  const visibleCategories = categories
    .filter((category) => data.some((row) => !isMissing(row.values?.[category.key])))
    .map((category, index) => ({ ...category, color: chartSeriesColor(index) }))
  if (!visibleCategories.length) return null

  const normalizedRows = data
    .map((row) => {
      const values = Object.fromEntries(
        visibleCategories
          .map((category) => [category.key, row.values?.[category.key]])
          .filter(([, value]) => !isMissing(value)),
      )
      const total = Object.values(values).reduce((sum, value) => sum + Number(value), 0)
      const hasValue = Object.values(values).some((value) => !isMissing(value))
      return { year: Number(row.year), values, total, hasValue }
    })
    .filter((row) => Number.isFinite(row.year) && row.hasValue)
    .sort((a, b) => a.year - b.year)

  if (!normalizedRows.length) return null

  const maxTotal = Math.max(...normalizedRows.map((row) => row.total), 1)
  const domainMax = niceMax(maxTotal)
  const plotW = CHART_WIDTH - PADDING.left - PADDING.right
  const plotH = CHART_HEIGHT - PADDING.top - PADDING.bottom
  const slotWidth = plotW / normalizedRows.length
  const barWidth = Math.max(24, Math.min(54, slotWidth * 0.62 - BAR_GAP))
  const yScale = (value) => PADDING.top + ((domainMax - value) / domainMax) * plotH

  const rows = normalizedRows.map((row, rowIndex) => {
    const x = PADDING.left + rowIndex * slotWidth + (slotWidth - barWidth) / 2
    let accumulated = 0
    const tooltipValues = visibleCategories.map((category) => {
      const rawValue = row.values[category.key]
      return {
        color: category.color,
        key: category.key,
        label: category.label,
        missing: isMissing(rawValue),
        value: Number(rawValue),
      }
    })
    const segments = visibleCategories.flatMap((category) => {
      const value = Number(row.values[category.key])
      if (!Number.isFinite(value) || value <= 0) return []
      const yTop = yScale(accumulated + value)
      const yBottom = yScale(accumulated)
      accumulated += value
      return [{
        key: category.key,
        label: category.label,
        color: category.color,
        value,
        year: row.year,
        x,
        y: yTop,
        width: barWidth,
        height: Math.max(1, yBottom - yTop),
        tooltipValues,
      }]
    })
    return { year: row.year, x, width: barWidth, segments }
  })

  const yTicksRaw = [0, domainMax * 0.2, domainMax * 0.4, domainMax * 0.6, domainMax * 0.8, domainMax]
  const yTicks = yTicksRaw.map((value) => ({
    label: Math.round(value).toLocaleString('pt-BR'),
    y: yScale(value),
  }))

  return {
    categories: visibleCategories,
    rows,
    visibleYearSet: new Set(
      (rows.length <= 8 ? rows : selectPneYearTicks(rows, 6)).map((row) => row.year),
    ),
    yTicks,
  }
}

function niceMax(value) {
  if (!Number.isFinite(value) || value <= 0) return 1
  const power = 10 ** Math.floor(Math.log10(value))
  const scaled = value / power
  if (scaled <= 1) return power
  if (scaled <= 2) return 2 * power
  if (scaled <= 5) return 5 * power
  return 10 * power
}
