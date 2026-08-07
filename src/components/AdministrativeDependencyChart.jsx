import { useMemo, useState } from 'react'
import { closeChartTooltipOnEscape } from '../utils/chartVisuals'
import {
  buildPnePercentScale,
  buildPneStackedScale,
  PNE_CHART_GEOMETRY,
  resolvePneAuxiliaryYearTickLimit,
  selectPneYearTicks,
} from '../utils/pneChartSystem'
import { useChartViewport } from '../hooks/useChartViewport'
import { ChartLegend, ChartTooltip } from './ChartPrimitives'

const FALLBACK_CHART_WIDTH = 420

const ALL_DEPENDENCY_KEYS = [
  { key: 'federal', label: 'Federal', color: 'var(--chart-series-1)', opacity: 1 },
  { key: 'estadual', label: 'Estadual', color: 'var(--chart-series-2)', opacity: 1 },
  { key: 'municipal', label: 'Municipal', color: 'var(--chart-series-3)', opacity: 1 },
  { key: 'privada', label: 'Privada', color: 'var(--chart-series-4)', opacity: 1 },
]

function formatNumber(value, unit) {
  if (!Number.isFinite(value)) return '-'
  if (unit === '%') {
    return `${value.toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%`
  }
  return value.toLocaleString('pt-BR', { maximumFractionDigits: 0 })
}

export function AdministrativeDependencyChart({
  series,
  showHeading = true,
  title = 'Por dependência administrativa',
  unit = '',
  valueType,
}) {
  const [activePoint, setActivePoint] = useState(null)
  const { containerRef, width: chartWidth } = useChartViewport(FALLBACK_CHART_WIDTH)
  const chartHeight = chartWidth < 300
    ? PNE_CHART_GEOMETRY.auxiliary.mobileHeight
    : PNE_CHART_GEOMETRY.auxiliary.desktopHeight
  const padding = PNE_CHART_GEOMETRY.auxiliary.padding
  const isPercent = valueType === 'percent' || unit === '%'

  const activeKeys = useMemo(() => {
    if (!series || series.length === 0) return []
    return ALL_DEPENDENCY_KEYS.filter((dep) =>
      series.some((p) => {
        const v = p?.[dep.key]
        return v !== null && v !== undefined && Number(v) > 0
      })
    )
  }, [series])

  const rawRows = useMemo(() => {
    if (activeKeys.length === 0) return []
    return (series ?? [])
      .map((p) => {
        const row = { year: Number(p?.ano) }
        for (const dep of activeKeys) {
          row[dep.key] = p?.[dep.key] !== null && p?.[dep.key] !== undefined ? Number(p[dep.key]) : null
        }
        return row
      })
      .filter((p) => Number.isFinite(p.year))
      .sort((a, b) => a.year - b.year)
  }, [series, activeKeys])

  if (rawRows.length === 0 || activeKeys.length === 0) return null

  const rows = rawRows
  const allHaveAnyValue = rows.some((r) => activeKeys.some((dep) => Number.isFinite(r[dep.key])))
  if (!allHaveAnyValue) return null

  const values = rows.flatMap((row) => activeKeys.map((dep) => Number.isFinite(row[dep.key]) ? row[dep.key] : 0))
  const yScaleModel = isPercent
    ? buildPnePercentScale(values)
    : buildPneStackedScale(rows, activeKeys.map((dep) => dep.key))
  const maxValue = yScaleModel.domain.max

  const plotWidth = chartWidth - padding.left - padding.right
  const plotHeight = chartHeight - padding.top - padding.bottom
  const barSlot = plotWidth / (rows.length || 1)
  const barWidth = Math.min(Math.max(barSlot * 0.68, 12), barSlot * 0.84, 44)
  const minYear = rows[0].year
  const maxYear = rows[rows.length - 1].year
  const yearSpan = Math.max(maxYear - minYear, 1)
  const xScale = (year) => padding.left + ((year - minYear) / yearSpan) * plotWidth
  const yScale = (value) =>
    padding.top + plotHeight - (value / Math.max(maxValue, 1)) * plotHeight
  const visibleYearSet = new Set(
    selectPneYearTicks(
      rows,
      resolvePneAuxiliaryYearTickLimit(chartWidth),
    ).map((row) => row.year),
  )

  const clearActive = () => setActivePoint(null)
  const formatTooltipValue = (value) => {
    const formatted = formatNumber(value, unit)
    if (!unit || unit === '%') return formatted
    return `${formatted} ${unit.toLocaleLowerCase('pt-BR')}`
  }

  return (
    <section className="complementary-chart complementary-chart--dependency">
      {showHeading ? (
        <div className="complementary-chart__heading">
          <span className="eyebrow">{title}</span>
        </div>
      ) : null}
      <ChartLegend className="complementary-chart__legend complementary-chart__legend--top" items={activeKeys} />
      <div className="complementary-chart__canvas" ref={containerRef}>
        <svg viewBox={`0 0 ${chartWidth} ${chartHeight}`} role="img" aria-label={`${title}: histórico do indicador por dependência administrativa`}>
          {yScaleModel.ticks.map((value) => {
            const y = yScale(value)
            return (
              <g key={value}>
                <line
                  className="complementary-chart__gridline"
                  x1={padding.left}
                  x2={chartWidth - padding.right}
                  y1={y}
                  y2={y}
                />
                <text x={padding.left - 10} y={y + 4} textAnchor="end" className="complementary-chart__tick">
                  {formatNumber(value, unit)}
                </text>
              </g>
            )
          })}
          <line
            x1={padding.left}
            x2={chartWidth - padding.right}
            y1={chartHeight - padding.bottom}
            y2={chartHeight - padding.bottom}
            className="complementary-chart__axis complementary-chart__axis--x"
          />
          <line
            x1={padding.left}
            x2={padding.left}
            y1={padding.top}
            y2={chartHeight - padding.bottom}
            className="complementary-chart__axis complementary-chart__axis--y"
          />

          {activePoint ? (
            <line
              className="complementary-chart__hover-line"
              x1={activePoint.x}
              x2={activePoint.x}
              y1={padding.top}
              y2={chartHeight - padding.bottom}
            />
          ) : null}

          {isPercent ? (
            <>
              {activeKeys.map((dep) => {
                const allPoints = rows
                  .map((row) => ({
                    color: dep.color,
                    dependency: dep.label,
                    value: row[dep.key],
                    year: row.year,
                    x: xScale(row.year),
                    y: Number.isFinite(row[dep.key]) ? yScale(row[dep.key]) : null,
                  }))
                const segments = []
                let current = []
                for (const p of allPoints) {
                  if (!Number.isFinite(p.value)) {
                    if (current.length > 0) {
                      segments.push(current)
                      current = []
                    }
                    continue
                  }
                  current.push(p)
                }
                if (current.length > 0) segments.push(current)
                if (segments.length === 0) return null
                return (
                  <g key={dep.key}>
                    {segments.map((seg, si) => {
                      const pathD = seg
                        .map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x.toFixed(1)} ${p.y.toFixed(1)}`)
                        .join(' ')
                      return (
                        <path
                          className="complementary-chart__dependency-line"
                          d={pathD}
                          fill="none"
                          key={si}
                          stroke={dep.color}
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeOpacity={dep.opacity}
                          strokeWidth="2.5"
                          style={{ '--dependency-color': dep.color }}
                        />
                      )
                    })}
                    {allPoints.filter((p) => Number.isFinite(p.value)).map((point) => (
                      <circle
                        aria-label={`${point.dependency} ${point.year}: ${formatTooltipValue(point.value)}`}
                        className={`chart-mark complementary-chart__dependency-point${activePoint?.dependency === point.dependency && activePoint?.year === point.year ? ' is-active' : ''}${point.year === maxYear ? ' is-last' : ''}`}
                        cx={point.x}
                        cy={point.y}
                        fill={point.color}
                        key={`${dep.key}-${point.year}`}
                        opacity={activePoint?.dependency === point.dependency && activePoint?.year === point.year ? 1 : dep.opacity}
                        onBlur={clearActive}
                        onFocus={() => setActivePoint(point)}
                        onMouseEnter={() => setActivePoint(point)}
                        onMouseLeave={clearActive}
                        onKeyDown={(event) => closeChartTooltipOnEscape(event, clearActive)}
                        r={activePoint?.dependency === point.dependency && activePoint?.year === point.year ? 5 : point.year === maxYear ? 4.3 : 3.8}
                        style={{ '--dependency-color': point.color }}
                        tabIndex="0"
                      />
                    ))}
                  </g>
                )
              })}
              {rows.map((row, index) => {
                if (!visibleYearSet.has(row.year)) return null
                const x = xScale(row.year)
                const anchor = index === 0 ? 'start' : index === rows.length - 1 ? 'end' : 'middle'
                const dx = index === 0 ? 6 : index === rows.length - 1 ? -6 : 0
                return (
                  <text
                    key={row.year}
                    x={x + dx}
                    y={chartHeight - 14}
                    textAnchor={anchor}
                    className="complementary-chart__x-label"
                  >
                    {row.year}
                  </text>
                )
              })}
            </>
          ) : (
            rows.map((row, index) => {
              const x = padding.left + index * barSlot + (barSlot - barWidth) / 2
              let y = chartHeight - padding.bottom
              return (
                <g key={row.year}>
                  {activeKeys.map((dep) => {
                    const value = row[dep.key]
                    if (!Number.isFinite(value) || value <= 0) return null
                    const rawBarHeight = (value / Math.max(maxValue, 1)) * plotHeight
                    const barHeight = Math.max(rawBarHeight, 3)
                    const segmentY = y - barHeight
                    const point = {
                      color: dep.color,
                      dependency: dep.label,
                      value,
                      year: row.year,
                      x: x + barWidth / 2,
                      y: segmentY + barHeight / 2,
                    }
                    const isActive =
                      activePoint?.dependency === point.dependency &&
                      activePoint?.year === point.year
                    const segment = (
                      <rect
                        aria-label={`${dep.label} ${row.year}: ${formatTooltipValue(value)}`}
                        className={`chart-mark complementary-chart__bar-segment${isActive ? ' is-active' : ''}`}
                        fill={dep.color}
                        height={barHeight}
                        key={dep.key}
                        onBlur={clearActive}
                        onFocus={() => setActivePoint(point)}
                        onMouseEnter={() => setActivePoint(point)}
                        onMouseLeave={clearActive}
                        onKeyDown={(event) => closeChartTooltipOnEscape(event, clearActive)}
                        opacity={isActive ? 1 : Math.max(dep.opacity, rawBarHeight < 3 ? 0.55 : dep.opacity)}
                        rx={3}
                        tabIndex="0"
                        width={barWidth}
                        x={x}
                        y={segmentY}
                      />
                    )
                    y = segmentY
                    return segment
                  })}
                  {visibleYearSet.has(row.year) ? (
                    <text
                      key={`label-${row.year}`}
                      x={x + barWidth / 2}
                      y={chartHeight - 14}
                      textAnchor="middle"
                      className="complementary-chart__x-label"
                    >
                      {row.year}
                    </text>
                  ) : null}
                </g>
              )
            })
          )}
        </svg>
        {activePoint ? (
          <ChartTooltip
            className="complementary-chart__tooltip"
            label={activePoint.year}
            series={activePoint.dependency}
            value={formatTooltipValue(activePoint.value)}
            style={{
              left: `${Math.min(92, Math.max(10, (activePoint.x / chartWidth) * 100))}%`,
              top: `${(activePoint.y / chartHeight) * 100}%`,
              transform:
                activePoint.y < padding.top + 38
                  ? 'translate(-50%, 12px)'
                  : 'translate(-50%, calc(-100% - 12px))',
            }}
          />
        ) : null}
      </div>
    </section>
  )
}
