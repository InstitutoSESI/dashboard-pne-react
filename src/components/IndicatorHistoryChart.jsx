import { useId, useMemo, useState } from 'react'
import {
  getStableVisualDomain,
  stableAbsoluteTicks,
  stableIndexTicks,
  stablePercentTicks,
  stableYearsTicks,
} from '../utils/visualDomain'
import { formatIndicatorValue, resolveIndicatorUnit } from '../utils/format'
import { closeChartTooltipOnEscape } from '../utils/chartVisuals'
import {
  buildPnePercentTicks,
  PNE_CHART_GEOMETRY,
  selectPneYearTicks,
} from '../utils/pneChartSystem'
import { useChartViewport } from '../hooks/useChartViewport'
import { ChartTooltip } from './ChartPrimitives'

const CHART_WIDTH = 980
const CHART_HEIGHT_INFORMATIVE = 280
const CHART_HEIGHT_NORMAL = 300
const CHART_HEIGHT_NEGATIVE = 330
const LEGACY_PADDING = { bottom: 44, left: 64, right: 86, top: 38 }

export function IndicatorHistoryChart({
  adaptiveDomain = false,
  chartHeight,
  chartType = 'line',
  chartWidth = undefined,
  domainOverride = undefined,
  distributeBars = false,
  endYear,
  essentialLabels = false,
  formatDataLabel: formatDataLabelProp,
  formatYAxis: formatYAxisProp,
  item,
  labelMode = undefined,
  meta = undefined,
  missingLabel = '—',
  referenceLabel = 'Referência',
  result = undefined,
  series,
  showMetaLine = true,
  showMissingPoints = undefined,
  startYear,
  subtitle,
  title = 'Histórico do indicador',
  unit: unitProp,
  yTickCount = undefined,
  floorNegativeValues = false,
  pneLayout = false,
}) {
  const [activePoint, setActivePoint] = useState(null)
  const rawClipId = useId()
  const clipId = `history-chart-clip-${rawClipId.replace(/:/g, '')}`
  const resolvedUnit = unitProp || resolveIndicatorUnit(item, result)
  const { containerRef, width: measuredWidth } = useChartViewport(chartWidth || CHART_WIDTH)
  const responsiveChartWidth = pneLayout ? measuredWidth : chartWidth
  const responsiveChartHeight = pneLayout
    ? measuredWidth < 480
      ? PNE_CHART_GEOMETRY.main.mobileHeight
      : chartHeight ?? PNE_CHART_GEOMETRY.main.desktopHeight
    : chartHeight
  const chart = useMemo(
    () =>
      buildChartModel({
        endYear,
        chartType,
        formatDataLabel: formatDataLabelProp,
        formatYAxis: formatYAxisProp,
        labelMode,
        meta,
        missingLabel,
        resolvedUnit,
        series,
        showMetaLine,
        showMissingPoints,
        startYear,
        yTickCount,
        floorNegativeValues,
        adaptiveDomain,
        essentialLabels,
        exactHeightOverride: pneLayout,
        chartHeightOverride: responsiveChartHeight,
        chartWidthOverride: responsiveChartWidth,
        chartMinWidthOverride: pneLayout ? 180 : 420,
        domainOverride,
        distributeBars,
        paddingOverride: pneLayout ? PNE_CHART_GEOMETRY.main.padding : LEGACY_PADDING,
      }),
    [adaptiveDomain, chartType, distributeBars, domainOverride, endYear, essentialLabels, floorNegativeValues, formatDataLabelProp, formatYAxisProp, labelMode, meta, missingLabel, pneLayout, resolvedUnit, responsiveChartHeight, responsiveChartWidth, series, showMetaLine, showMissingPoints, startYear, yTickCount],
  )

  const validCount = chart.points.filter(p => p.valid !== false).length
  if (validCount < 2 && !showMissingPoints) {
    return null
  }

  return (
    <section className={`history-chart${chart.hasNegativeValues ? ' history-chart--with-negatives' : ''}${chart.isInformative ? ' history-chart--informative' : ''}${chartType === 'bar' ? ' history-chart--bars' : ''}`}>
      <div className="history-chart__heading">
        <div>
          <span className="eyebrow">Histórico do indicador</span>
          <h4>{title}</h4>
          {subtitle ? <p className="history-chart__subtitle">{subtitle}</p> : null}
        </div>
      </div>

      <div className="history-chart__canvas" ref={containerRef}>
        <svg
          viewBox={`0 0 ${chart.width} ${chart.height}`}
          role="img"
          aria-label={`${title}: ${chartType === 'bar' ? 'barras anuais' : 'linha histórica por ano'}`}
        >
          <defs>
            <clipPath id={clipId}>
              <rect
                x={chart.padding.left}
                y={chart.padding.top}
                width={chart.width - chart.padding.left - chart.padding.right}
                height={chart.height - chart.padding.top - chart.padding.bottom}
              />
            </clipPath>
          </defs>
          <g className="chart-grid">
            {chart.yTicks.map((tick, index) => (
              <g key={`${tick.value}-${index}`}>
                <line
                  x1={chart.padding.left}
                  x2={chart.width - chart.padding.right}
                  y1={tick.y}
                  y2={tick.y}
                />
                <text x={chart.padding.left - 12} y={tick.y + 4}>
                  {chart.formatYAxis ? chart.formatYAxis(tick.value) : chart.formatValue(tick.value)}
                </text>
              </g>
            ))}
          </g>

          {chart.metaLine && (
            <g className="chart-meta-line">
              <line
                x1={chart.padding.left}
                x2={chart.width - chart.padding.right}
                y1={chart.metaLine.y}
                y2={chart.metaLine.y}
              />
            </g>
          )}

          <g className="chart-axis">
            <line
              className="chart-axis__x"
              x1={chart.padding.left}
              x2={chart.width - chart.padding.right}
              y1={chart.height - chart.padding.bottom}
              y2={chart.height - chart.padding.bottom}
            />
            <line
              className="chart-axis__y"
              x1={chart.padding.left}
              x2={chart.padding.left}
              y1={chart.padding.top}
              y2={chart.height - chart.padding.bottom}
            />
          </g>

          {chart.zeroLine && (
            <g className="chart-zero-line">
              <line
                x1={chart.padding.left}
                x2={chart.width - chart.padding.right}
                y1={chart.zeroLine.y}
                y2={chart.zeroLine.y}
              />
            </g>
          )}

          <g className="chart-year-markers">
            {chart.yearMarkers.map((marker) => (
              <line
                key={marker.year}
                x1={marker.x}
                x2={marker.x}
                y1={chart.padding.top}
                y2={chart.height - chart.padding.bottom}
              />
            ))}
          </g>

          <g clipPath={`url(#${clipId})`}>
            {chartType === 'bar'
              ? chart.points.filter((point) => point.valid !== false).map((point) => (
                <rect
                  className={`chart-bar${point.isLast ? ' is-last' : ''}`}
                  height={Math.max(1, chart.barBaselineY - point.y)}
                  key={point.year}
                  onBlur={() => setActivePoint(null)}
                  onFocus={() => setActivePoint(point)}
                  onKeyDown={(event) => closeChartTooltipOnEscape(event, () => setActivePoint(null))}
                  onMouseEnter={() => setActivePoint(point)}
                  onMouseLeave={() => setActivePoint(null)}
                  rx="4"
                  tabIndex="0"
                  width={chart.barWidth}
                  x={point.x - chart.barWidth / 2}
                  y={Math.min(point.y, chart.barBaselineY)}
                >
                  <title>{`${point.year}: ${chart.formatValue(point.value)}`}</title>
                </rect>
              ))
              : <>
                  {chart.areaPath ? <path className="chart-area" d={chart.areaPath} /> : null}
                  <path className="chart-line" d={chart.linePath} />
                </>}
          </g>

          {chartType !== 'bar' ? <g className="chart-points">
            {chart.points.filter(p => p.valid !== false).map((point) => (
              <circle
                aria-label={`Município, ${point.year}: ${chart.formatValue(point.value)}`}
                className={`chart-mark${point.isLast ? ' is-last' : ''}`}
                cx={point.x}
                cy={point.y}
                key={point.year}
                r={activePoint?.year === point.year ? 5.5 : point.isLast ? 5 : 4}
                onBlur={() => setActivePoint(null)}
                onFocus={() => setActivePoint(point)}
                onMouseEnter={() => setActivePoint(point)}
                onMouseLeave={() => setActivePoint(null)}
                onKeyDown={(event) => closeChartTooltipOnEscape(event, () => setActivePoint(null))}
                tabIndex="0"
              >
                <title>{`${point.year}: ${chart.formatValue(point.value)}`}</title>
              </circle>
            ))}
          </g> : null}

          {showMissingPoints && chart.missingPointLabels && (
            <g className="chart-missing-labels">
              {chart.missingPointLabels.map((label) => (
                <text key={label.year} x={label.x} y={label.y} textAnchor="middle" className="chart-missing-label">
                  {missingLabel}
                </text>
              ))}
            </g>
          )}

          <g className="chart-data-labels">
            {chart.dataLabels.map((label) => (
              <text
                key={label.year}
                x={label.x}
                y={label.y}
                textAnchor={label.anchor}
                className={
                  label.isMeta
                    ? 'chart-meta-label'
                    : label.isLast
                      ? 'chart-point-label is-last'
                      : 'chart-point-label'
                }
              >
                {label.isMeta ? `${referenceLabel} ${chart.formatValue(label.value)}` : (chart.formatDataLabel ? chart.formatDataLabel(label.value) : chart.formatValue(label.value))}
              </text>
            ))}
          </g>

          <g className="chart-x-labels">
            {chart.xTicks.map((tick, i, arr) => (
              <text
                key={tick.year}
                x={
                  chartType === 'bar'
                    ? tick.x
                    : i === 0
                    ? tick.x + 4
                    : i === arr.length - 1
                      ? tick.x - 4
                      : tick.x
                }
                y={chart.height - 12}
                textAnchor={
                  chartType === 'bar'
                    ? 'middle'
                    : i === 0 ? 'start' : i === arr.length - 1 ? 'end' : 'middle'
                }
              >
                {tick.year}
              </text>
            ))}
          </g>
        </svg>

        {activePoint && (
          <ChartTooltip
            className="history-chart__tooltip"
            label={activePoint.year}
            series="Município"
            value={activePoint.valid === false ? missingLabel : chart.formatValue(activePoint.value)}
            style={{
              left: `${Math.min(92, Math.max(10, (activePoint.x / chart.width) * 100))}%`,
              top: `${(activePoint.y / chart.height) * 100}%`,
              transform:
                activePoint.y < chart.padding.top + 38
                  ? 'translate(-50%, 12px)'
                  : 'translate(-50%, calc(-100% - 12px))',
            }}
          />
        )}
      </div>
    </section>
  )
}

function buildChartModel({
  adaptiveDomain,
  chartType,
  endYear,
  essentialLabels,
  formatDataLabel,
  formatYAxis,
  labelMode,
  meta,
  missingLabel,
  resolvedUnit,
  series,
  showMetaLine,
  showMissingPoints,
  startYear,
  yTickCount,
  floorNegativeValues = false,
  exactHeightOverride = false,
  chartHeightOverride,
  chartMinWidthOverride,
  chartWidthOverride,
  domainOverride,
  distributeBars,
  paddingOverride,
}) {
  const padding = paddingOverride ?? LEGACY_PADDING
  const rawPoints = normalizeSeries(series, floorNegativeValues, showMissingPoints)
  const validPoints = rawPoints.filter((p) => p.valid !== false)
  const points = showMissingPoints ? rawPoints : validPoints
  const rawMetaValue =
    meta === null || meta === undefined || meta === '' ? Number.NaN : Number(meta)
  const metaValue = Number.isFinite(rawMetaValue) ? rawMetaValue : null

  if (validPoints.length < 2) {
    const baseChartHeight = showMetaLine ? CHART_HEIGHT_NORMAL : CHART_HEIGHT_INFORMATIVE
    const chartHeight = resolveChartHeight(baseChartHeight, chartHeightOverride, exactHeightOverride)
    const chartWidth = resolveChartWidth(chartWidthOverride, chartMinWidthOverride)
    return {
      formatDataLabel,
      formatValue: (value) => formatIndicatorValue(value, resolvedUnit),
      formatYAxis,
      hasNegativeValues: false,
      height: chartHeight,
      width: chartWidth,
      isInformative: !showMetaLine,
      missingPointLabels: showMissingPoints ? computeMissingLabels(points, chartHeight, missingLabel) : undefined,
      padding,
      points,
    }
  }

  const values = validPoints.map((point) => point.value)
  const hasNegativeValues = values.some((value) => value < 0)
  const baseChartHeight = hasNegativeValues
    ? CHART_HEIGHT_NEGATIVE
    : showMetaLine
      ? CHART_HEIGHT_NORMAL
      : CHART_HEIGHT_INFORMATIVE
  const chartHeight = resolveChartHeight(baseChartHeight, chartHeightOverride, exactHeightOverride)
  const chartWidth = resolveChartWidth(chartWidthOverride, chartMinWidthOverride)
  const isPercent = resolvedUnit === 'percent'
  const isIndex = resolvedUnit === 'index'
  const isYears = resolvedUnit === 'years'
  const domainValues = metaValue !== null ? [...values, metaValue] : values
  const domain = domainOverride ?? (adaptiveDomain
    ? getAdaptiveHistoryDomain({
        values: domainValues,
        meta: metaValue,
        isPercent,
        isIndex,
        isYears,
      })
    : getStableVisualDomain({
        values: domainValues,
        meta: metaValue,
        isPercent,
        isIndex,
        isYears,
      }))
  const allYears = points.map((point) => point.year)
  const minYear = Math.min(...allYears)
  const maxYear = Math.max(...allYears)
  const plotWidth = chartWidth - padding.left - padding.right
  const plotHeight = chartHeight - padding.top - padding.bottom
  const barWidth = Math.max(20, Math.min(76, plotWidth / Math.max(validPoints.length * 2.25, 3)))
  const barEdgeGap = chartType === 'bar' ? Math.max(12, barWidth * 0.25) : 0
  const barEdgeInset = chartType === 'bar' ? barWidth / 2 + barEdgeGap : 0
  const effectivePlotWidth = Math.max(0, plotWidth - barEdgeInset * 2)

  const xScale = (year) => {
    if (chartType === 'bar' && distributeBars) {
      const pointIndex = points.findIndex((point) => point.year === year)
      if (pointIndex >= 0) {
        const bandWidth = plotWidth / Math.max(points.length, 1)
        return padding.left + bandWidth * (pointIndex + 0.5)
      }
    }
    if (maxYear === minYear) return padding.left + plotWidth / 2
    return padding.left + barEdgeInset + ((year - minYear) / (maxYear - minYear)) * effectivePlotWidth
  }
  const yScale = (value) => {
    if (domain.max === domain.min) return padding.top + plotHeight / 2
    return padding.top + ((domain.max - value) / (domain.max - domain.min)) * plotHeight
  }

  const scaledPoints = points.map((point) => ({
    ...point,
    x: xScale(point.year),
    y: point.valid !== false ? yScale(point.value) : padding.top + plotHeight / 2,
  }))
  const scaledValidPoints = scaledPoints.filter((p) => p.valid !== false)
  const barBaselineY = domain.min <= 0 && domain.max >= 0
    ? yScale(0)
    : chartHeight - padding.bottom
  const lastValidYear = scaledValidPoints[scaledValidPoints.length - 1]?.year
  const displayPoints = scaledPoints.map((point) => ({
    ...point,
    isLast: point.valid !== false && point.year === lastValidYear,
  }))
  const linePath = showMissingPoints
    ? buildBrokenLinePath(scaledPoints)
    : scaledPoints
        .map((point, index) => `${index === 0 ? 'M' : 'L'}${point.x.toFixed(1)} ${point.y.toFixed(1)}`)
        .join(' ')
  const last = scaledValidPoints[scaledValidPoints.length - 1]
  const first = scaledValidPoints[0]
  const hasGaps = showMissingPoints && scaledPoints.some((p) => p.valid === false)
  const zeroY = domain.min < 0 && domain.max > 0
    ? yScale(0)
    : chartHeight - padding.bottom
  const areaPath = hasNegativeValues || hasGaps
    ? null
    : `${linePath} L${last.x.toFixed(1)} ${zeroY.toFixed(1)} L${first.x.toFixed(1)} ${zeroY.toFixed(1)} Z`

  const yTicksRaw = domainOverride?.isPercent
    ? buildPnePercentTicks(domain)
    : domain.adaptive
    ? buildAdaptiveTicks(domain)
    : isPercent
      ? stablePercentTicks(domain) ?? [domain.min, domain.max]
      : isIndex
        ? stableIndexTicks(domain) ?? [domain.min, domain.max]
        : isYears
          ? stableYearsTicks(domain) ?? [domain.min, domain.max]
          : stableAbsoluteTicks(domain) ?? [domain.min, domain.max]
  let yTicks = yTicksRaw
    .filter((value) => value >= domain.min - 0.0001 && value <= domain.max + 0.0001)
    .map((value) => ({ value, y: yScale(value) }))

  if (yTickCount && yTicks.length > yTickCount) {
    const step = (yTicks.length - 1) / (yTickCount - 1)
    const thinned = []
    for (let i = 0; i < yTickCount; i++) {
      const idx = Math.round(i * step)
      thinned.push(yTicks[idx])
    }
    yTicks = thinned
  }

  const shouldShowMeta = showMetaLine && metaValue !== null && Number.isFinite(metaValue)
  let metaLine = null
  if (shouldShowMeta) {
    const baseY = yScale(metaValue)
    metaLine = {
      value: metaValue,
      y: Math.max(padding.top, Math.min(baseY, chartHeight - padding.bottom)),
    }
  }

  const zeroLine = domain.min < 0 && domain.max > 0
    ? { y: yScale(0) }
    : null

  const candidateMarkerYears = [startYear, endYear]
    .map((year) => Number(year))
    .filter((year) => Number.isFinite(year) && year > 0)

  const fallbackMarkerYears = [minYear, maxYear]

  const finalMarkerYears = candidateMarkerYears.length
    ? candidateMarkerYears
    : fallbackMarkerYears

  const yearMarkers = finalMarkerYears
    .filter((year) => year >= minYear && year <= maxYear)
    .filter((year, index, arr) => arr.indexOf(year) === index)
    .map((year) => ({ year, x: xScale(year) }))

  const formatValue = (value) => formatIndicatorValue(value, resolvedUnit)
  const formatLabel = formatDataLabel || formatValue
  const labelsForCompute = labelMode === 'all' ? scaledValidPoints : scaledPoints
  const dataLabels = computeDataLabels(labelsForCompute, metaLine, formatLabel, chartHeight, chartWidth, padding, labelMode, essentialLabels, chartType)

  const missingPointLabels = showMissingPoints
    ? scaledPoints.filter((p) => p.valid === false).map((p) => ({ year: p.year, x: p.x, y: chartHeight - padding.bottom + 18 }))
    : undefined

  return {
    areaPath,
    barBaselineY,
    barWidth,
    dataLabels,
    formatDataLabel,
    formatValue,
    formatYAxis,
    hasNegativeValues,
    height: chartHeight,
    width: chartWidth,
    isInformative: !showMetaLine,
    linePath,
    metaLine,
    missingPointLabels,
    padding,
    points: displayPoints,
    xTicks: chartType === 'bar' && chartWidth >= 520 && scaledPoints.length <= 8
      ? scaledPoints.map((point) => ({ year: point.year, x: point.x }))
      : showMissingPoints
        ? selectPneYearTicks(pickAllYearTicks(scaledPoints), chartWidth < 420 ? 3 : 6)
        : selectPneYearTicks(scaledPoints, chartWidth < 420 ? 3 : 6),
    yTicks,
    yearMarkers,
    zeroLine,
  }
}

function resolveChartHeight(baseHeight, override, exact = false) {
  const numericOverride = Number(override)
  if (!Number.isFinite(numericOverride)) return baseHeight
  return exact ? numericOverride : Math.max(baseHeight, numericOverride)
}

function resolveChartWidth(override, minWidth = 420) {
  const numericOverride = Number(override)
  if (!Number.isFinite(numericOverride)) return CHART_WIDTH
  return Math.max(minWidth, numericOverride)
}

function normalizeSeries(series = [], floorNegativeValues = false, showMissingPoints = false) {
  return series
    .map((point) => {
      const isMissing = showMissingPoints && (point?.valor === null || point?.valor === undefined)
      const rawValue = Number(point?.valor)
      const valid = !isMissing && Number.isFinite(rawValue) && Number.isFinite(Number(point?.ano))
      return {
        value: isMissing ? null : (floorNegativeValues && rawValue < 0 ? 0 : rawValue),
        year: Number(point?.ano),
        valid,
        missing: isMissing,
      }
    })
    .filter((point) => {
      if (showMissingPoints) return Number.isFinite(point.year)
      return Number.isFinite(point.year) && point.valid
    })
    .sort((a, b) => a.year - b.year)
}

function getAdaptiveHistoryDomain({ values, meta, isPercent = false, isIndex = false, isYears = false }) {
  if (isIndex || isYears) {
    return getStableVisualDomain({ values, meta, isPercent, isIndex, isYears })
  }

  const numericValues = (values ?? []).filter(Number.isFinite)
  const numericMeta = Number.isFinite(meta) ? [meta] : []
  const all = [...numericValues, ...numericMeta]

  if (!all.length) {
    return getStableVisualDomain({ values, meta, isPercent, isIndex, isYears })
  }

  const dataMin = Math.min(...all)
  const dataMax = Math.max(...all)

  if (isPercent && dataMin >= 0 && dataMax <= 100) {
    const dataOnlyMax = numericValues.length ? Math.max(...numericValues) : dataMax
    const metaIsCeiling = Number.isFinite(meta) && meta >= dataOnlyMax
    const maxWithHeadroom = metaIsCeiling
      ? dataMax
      : Math.max(dataMax * 1.08, 10)
    return {
      adaptive: true,
      isPercent: true,
      max: Math.min(100, Math.max(5, Math.ceil(maxWithHeadroom / 5) * 5)),
      min: 0,
    }
  }

  if (isPercent && dataMin >= 0) {
    return {
      adaptive: true,
      isPercent: true,
      max: roundUpAdaptive(dataMax * 1.08),
      min: 0,
    }
  }

  if (dataMin >= 0) {
    return {
      adaptive: true,
      isPercent: false,
      max: roundUpAdaptive(dataMax * 1.1),
      min: 0,
    }
  }

  return getStableVisualDomain({ values, meta, isPercent, isIndex, isYears })
}

function buildAdaptiveTicks(domain) {
  const step = domain.isPercent
    ? pickAdaptivePercentStep(domain.max)
    : pickAdaptiveAbsoluteStep(domain.max - domain.min)
  const ticks = []

  for (let value = domain.min; value <= domain.max + 0.0001; value += step) {
    ticks.push(Number(value.toFixed(2)))
  }

  if (!ticks.includes(domain.max)) {
    ticks.push(domain.max)
  }

  return ticks
}

function pickAdaptivePercentStep(max) {
  if (max <= 20) return 5
  if (max <= 50) return 10
  if (max <= 80) return 20
  return 25
}

function pickAdaptiveAbsoluteStep(span) {
  if (span <= 0) return 1
  const magnitude = 10 ** Math.floor(Math.log10(Math.max(span, 1)))
  if (span / magnitude <= 2) return magnitude / 2
  if (span / magnitude <= 5) return magnitude
  return magnitude * 2
}

function roundUpAdaptive(value) {
  if (!Number.isFinite(value) || value <= 0) return 1
  const magnitude = 10 ** Math.floor(Math.log10(value))
  const normalized = value / magnitude
  if (normalized <= 1) return magnitude
  if (normalized <= 2) return 2 * magnitude
  if (normalized <= 5) return 5 * magnitude
  return 10 * magnitude
}

function buildBrokenLinePath(scaledPoints) {
  let path = ''
  let inSegment = false
  for (const p of scaledPoints) {
    if (p.valid === false) {
      inSegment = false
      continue
    }
    if (!inSegment) {
      path += `${path ? ' ' : ''}M${p.x.toFixed(1)} ${p.y.toFixed(1)}`
      inSegment = true
    } else {
      path += ` L${p.x.toFixed(1)} ${p.y.toFixed(1)}`
    }
  }
  return path
}

function pickAllYearTicks(points) {
  const seen = new Set()
  const result = []
  for (const p of points) {
    if (!seen.has(p.year)) {
      seen.add(p.year)
      result.push(p)
    }
  }
  return result
}

function computeMissingLabels(points, chartHeight) {
  const y = chartHeight - 18
  return points
    .filter((p) => p.valid === false)
    .map((p) => ({ year: p.year, x: p.x, y }))
}

function computeDataLabels(points, metaLine, formatValue, chartHeight, chartWidth, padding, labelMode, essentialLabels = false, chartType = 'line') {
  if (points.length === 0) return []

  const plotLeft = padding.left
  const plotRight = chartWidth - padding.right
  const plotTop = padding.top
  const plotBottom = chartHeight - padding.bottom

  const LABEL_OFFSET_Y = 14
  const MIN_DISTANCE_Y = 24
  const MIN_DISTANCE_X = 44

  const lastPoint = points[points.length - 1]
  const firstPoint = points[0]

  if (essentialLabels) {
    return computeEssentialDataLabels({
      firstPoint,
      lastPoint,
      metaLine,
      plotBottom,
      plotLeft,
      plotRight,
      plotTop,
      centerPointLabels: chartType === 'bar',
    })
  }

  const candidates = []

  // 1. Último ponto (prioridade 1 - mais alta)
  const centerPointLabels = chartType === 'bar'
  const lastNeedsEndAnchor = lastPoint.x > plotRight - 30
  candidates.push({
    anchor: centerPointLabels ? 'middle' : lastNeedsEndAnchor ? 'end' : 'start',
    isLast: true,
    isMeta: false,
    priority: 1,
    type: 'last',
    value: lastPoint.value,
    x: centerPointLabels ? lastPoint.x : lastNeedsEndAnchor ? lastPoint.x - 8 : lastPoint.x + 8,
    y: pickLabelY(lastPoint.y, plotTop, plotBottom, LABEL_OFFSET_Y),
    year: lastPoint.year,
  })

  // 2. Demais pontos
  if (points.length <= 6 || labelMode === 'all') {
    for (let i = 0; i < points.length - 1; i++) {
      const p = points[i]
      candidates.push({
        anchor: 'middle',
        isLast: false,
        isMeta: false,
        priority: 7,
        type: 'point',
        value: p.value,
        x: p.x,
        y: pickLabelY(p.y, plotTop, plotBottom, LABEL_OFFSET_Y),
        year: p.year,
      })
    }
  } else {
    const maxPoint = points.reduce((max, p) => (p.value > max.value ? p : max), points[0])
    const minPoint = points.reduce((min, p) => (p.value < min.value ? p : min), points[0])

    const seen = new Set([lastPoint.year])
    const addCandidate = (p, priority, type) => {
      if (!p || seen.has(p.year)) return
      seen.add(p.year)
      candidates.push({
        anchor: 'middle',
        isLast: false,
        isMeta: false,
        priority,
        type,
        value: p.value,
        x: p.x,
        y: pickLabelY(p.y, plotTop, plotBottom, LABEL_OFFSET_Y),
        year: p.year,
      })
    }

    addCandidate(maxPoint, 5, 'max')
    addCandidate(minPoint, 5, 'min')
    addCandidate(firstPoint, 6, 'first')
  }

  // 3. Meta label (prioridade 8 - mais baixa que todos os pontos)
  if (metaLine) {
    const metaY = metaLine.y
    let metaLabelY
    if (metaY < plotTop + 30) {
      metaLabelY = metaY + 18
    } else if (metaY > plotBottom - 20) {
      metaLabelY = metaY - 10
    } else {
      metaLabelY = metaY - 8
    }
    metaLabelY = clampNumber(metaLabelY, plotTop + 14, plotBottom - 10)

    // Verificar se meta label ficará perto do último ponto
    const dyFromLast = Math.abs(metaLabelY - lastPoint.y)
    const dxFromLast = Math.abs(plotRight - 2 - lastPoint.x)
    if (dyFromLast < MIN_DISTANCE_Y && dxFromLast < 80) {
      // Último ponto está perto: deslocar meta label para o lado oposto
      if (lastPoint.y > plotTop + plotBottom / 2) {
        metaLabelY = plotTop + 18
      } else {
        metaLabelY = plotBottom - 12
      }
    }

    candidates.push({
      anchor: 'end',
      isLast: false,
      isMeta: true,
      priority: 8,
      type: 'meta',
      value: metaLine.value,
      x: plotRight - 2,
      y: metaLabelY,
      year: 'meta',
    })
  }

  // 4. Ajustar posições dos labels de pontos
  for (const label of candidates) {
    if (label.isMeta) continue
    label.y = clampNumber(label.y, plotTop + 14, plotBottom - 10)

    if (label.x < plotLeft + 14) {
      label.x = plotLeft + 14
    }
    if (label.x > plotRight - 14) {
      label.x = plotRight - 14
    }

    // Último ponto: refinamento de posição
    if (label.isLast && !centerPointLabels) {
      if (isLastAtRightEdge(lastPoint.x, plotRight)) {
        label.anchor = 'end'
        label.x = lastPoint.x - 8
        if (label.x < plotLeft + 14) {
          label.x = plotLeft + 20
          label.anchor = 'start'
        }
      } else {
        label.anchor = 'start'
        label.x = lastPoint.x + 8
        if (label.x > plotRight - 6) {
          label.x = plotRight - 6
          label.anchor = 'end'
        }
      }
    }

    if (label.type === 'first' && firstPoint.x < plotLeft + 16) {
      label.hidden = true
    }
  }

  // 5. Filtrar ocultos e ordenar por prioridade
  let visible = candidates.filter((l) => !l.hidden)
  visible.sort((a, b) => a.priority - b.priority)

  // 6. Colisão final
  const filtered = []
  for (const label of visible) {
    const tooClose = filtered.some((existing) => {
      const dy = Math.abs(existing.y - label.y)
      const dx = Math.abs(existing.x - label.x)
      return dy < MIN_DISTANCE_Y && dx < MIN_DISTANCE_X
    })
    if (!tooClose) filtered.push(label)
  }

  // 7. Garantir que a meta não foi removida; se foi, tentar reinserir com posição alternativa
  const hasMeta = filtered.some((l) => l.isMeta)
  if (metaLine && !hasMeta) {
    const metaCandidate = visible.find((l) => l.isMeta)
    if (metaCandidate) {
      const altY = metaCandidate.y < plotTop + 40 ? plotBottom - 12 : plotTop + 18
      metaCandidate.y = altY
      const stillTooClose = filtered.some((existing) => {
        const dy = Math.abs(existing.y - metaCandidate.y)
        const dx = Math.abs(existing.x - metaCandidate.x)
        return dy < MIN_DISTANCE_Y && dx < MIN_DISTANCE_X
      })
      if (!stillTooClose) {
        filtered.push(metaCandidate)
      }
    }
  }

  return filtered
}

function computeEssentialDataLabels({
  centerPointLabels = false,
  firstPoint,
  lastPoint,
  metaLine,
  plotBottom,
  plotLeft,
  plotRight,
  plotTop,
}) {
  const labels = []
  const LABEL_OFFSET_Y = 16
  const MIN_DISTANCE_Y = 24
  const MIN_DISTANCE_X = 52
  const RIGHT_COLLISION_X = 112

  const metaIsNearLast =
    metaLine &&
    lastPoint &&
    Math.abs(lastPoint.x - (plotRight - 2)) < RIGHT_COLLISION_X &&
    Math.abs(lastPoint.y - metaLine.y) < 52

  const addPointLabel = (point, priority, type, isLast = false) => {
    if (!point) return
    const isNearRight = point.x > plotRight - 30
    const isNearLeft = point.x < plotLeft + 30
    const anchor = centerPointLabels
      ? 'middle'
      : isLast
      ? isNearRight ? 'end' : 'start'
      : isNearLeft ? 'start' : 'middle'
    const x = centerPointLabels
      ? point.x
      : isLast
      ? isNearRight ? point.x - 10 : point.x + 10
      : isNearLeft ? point.x + 8 : point.x
    const y = isLast && metaIsNearLast
      ? clampNumber(point.y - LABEL_OFFSET_Y, plotTop + 14, plotBottom - 10)
      : clampNumber(pickLabelY(point.y, plotTop, plotBottom, LABEL_OFFSET_Y), plotTop + 14, plotBottom - 10)

    labels.push({
      anchor,
      isLast,
      isMeta: false,
      priority,
      type,
      value: point.value,
      x: clampNumber(x, plotLeft + 8, plotRight - 8),
      y,
      year: point.year,
    })
  }

  addPointLabel(lastPoint, 1, 'last', true)

  if (firstPoint?.year !== lastPoint?.year) {
    addPointLabel(firstPoint, 3, 'first')
  }

  if (metaLine) {
    const lastLabel = labels.find((label) => label.isLast)
    const metaLabelCandidates = [
      metaLine.y + 18,
      metaLine.y - 14,
      metaLine.y + 32,
      metaLine.y - 28,
    ]
      .map((y) => clampNumber(y, plotTop + 14, plotBottom - 10))
      .filter((y, index, arr) => arr.indexOf(y) === index)

    const preferredMetaY = metaIsNearLast
      ? metaLabelCandidates.find((candidateY) => (
          !lastLabel || Math.abs(candidateY - lastLabel.y) >= MIN_DISTANCE_Y
        ))
      : metaLine.y < plotTop + 30
        ? metaLabelCandidates[0]
        : metaLine.y > plotBottom - 20
          ? metaLabelCandidates[1]
          : metaLabelCandidates[1]

    const metaLabelY = preferredMetaY ?? metaLabelCandidates[0]

    labels.push({
      anchor: 'end',
      isLast: false,
      isMeta: true,
      priority: 5,
      type: 'meta',
      value: metaLine.value,
      x: plotRight - 2,
      y: clampNumber(metaLabelY, plotTop + 14, plotBottom - 10),
      year: 'meta',
    })
  }

  const ordered = labels.sort((a, b) => a.priority - b.priority)
  const filtered = []
  for (const label of ordered) {
    const tooClose = filtered.some((existing) => {
      const dy = Math.abs(existing.y - label.y)
      const dx = Math.abs(existing.x - label.x)
      return dy < MIN_DISTANCE_Y && dx < MIN_DISTANCE_X
    })
    if (!tooClose || label.isLast || label.isMeta) {
      filtered.push(label)
    }
  }

  return filtered
}

function isLastAtRightEdge(x, plotRight) {
  return x > plotRight - 30
}

function pickLabelY(pointY, plotTop, plotBottom, offset) {
  if (pointY < plotTop + 26) return pointY + offset + 6
  if (pointY > plotBottom - 20) return pointY - offset - 2
  return pointY - offset
}

function clampNumber(value, min, max) {
  return Math.max(min, Math.min(value, max))
}
