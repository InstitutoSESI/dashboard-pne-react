export const PNE_CHART_GEOMETRY = Object.freeze({
  main: Object.freeze({
    desktopHeight: 300,
    mobileHeight: 280,
    padding: Object.freeze({ top: 18, right: 24, bottom: 28, left: 48 }),
  }),
  auxiliary: Object.freeze({
    desktopHeight: 270,
    mobileHeight: 280,
    padding: Object.freeze({ top: 28, right: 24, bottom: 44, left: 58 }),
  }),
  projection: Object.freeze({
    desktopHeight: 320,
    mobileHeight: 280,
    padding: Object.freeze({ top: 28, right: 28, bottom: 52, left: 58 }),
  }),
})

const MIN_TERMINAL_TICK_SPAN_RATIO = 0.12

export function buildPnePercentScale(values) {
  const numericValues = (values ?? []).map(Number).filter(Number.isFinite)
  const maxValue = numericValues.length ? Math.max(...numericValues, 0) : 0

  if (maxValue <= 100) {
    return {
      domain: { min: 0, max: 100, isPercent: true },
      ticks: [0, 25, 50, 75, 100],
    }
  }

  const max = Math.ceil((maxValue * 1.1) / 10) * 10
  return {
    domain: { min: 0, max, isPercent: true },
    ticks: buildEvenTicks(0, max, 6),
  }
}

export function buildPnePercentTicks(domain) {
  if (domain?.observed === true) {
    return buildObservedPercentageTicks(Number(domain.max))
  }
  if (!domain) return [0, 25, 50, 75, 100]

  const min = Number(domain.min) || 0
  const max = Number(domain.max)

  /*
   * As marcas precisam cair dentro da faixa do dominio, sempre.
   *
   * A escala fixa [0, 25, 50, 75, 100] funcionava enquanto todo percentual ia
   * de 0 a 100. Com o eixo ajustado aos dados ela passou a desenhar marcas
   * fora da area de plotagem: piso abaixo do eixo X num dominio 80-100, e
   * marca de 100 por cima da legenda num dominio 0-80.
   */
  if (min > 0) return buildEvenTicks(min, max, 5)
  if (max >= 100) return max > 100 ? buildEvenTicks(0, max, 6) : [0, 25, 50, 75, 100]
  return buildEvenTicks(0, max, 5)
}

export function buildObservedPercentageScale(values) {
  const numericValues = (values ?? [])
    .map(Number)
    .filter((value) => Number.isFinite(value) && value >= 0)
  const maxObserved = numericValues.length ? Math.max(...numericValues) : 0
  const paddedMax = maxObserved * 1.15
  const max = paddedMax <= 5
    ? 5
    : paddedMax <= 10
      ? 10
      : roundObservedUpperBound(paddedMax)

  return {
    domain: { min: 0, max, isPercent: true, observed: true },
    ticks: buildObservedPercentageTicks(max),
  }
}

export function buildPneAbsoluteScale(values, headroom = 0.12) {
  const numericValues = (values ?? []).map(Number).filter((value) => Number.isFinite(value) && value >= 0)
  const maxValue = numericValues.length ? Math.max(...numericValues) : 0
  const paddedMax = Math.max(1, maxValue * (1 + headroom))
  const step = pickNiceStep(paddedMax / 4)
  const max = Math.max(step, Math.ceil(paddedMax / step) * step)

  return {
    domain: { min: 0, max, isPercent: false },
    ticks: buildTicksByStep(0, max, step),
  }
}

export function buildPneStackedScale(rows, keys) {
  const totals = (rows ?? []).map((row) => (
    (keys ?? []).reduce((sum, key) => {
      const value = Number(row?.[key])
      return sum + (Number.isFinite(value) && value > 0 ? value : 0)
    }, 0)
  ))
  return buildPneAbsoluteScale(totals)
}

export function selectPneYearTicks(points, maxTicks = 6) {
  const unique = []
  const seen = new Set()

  for (const point of points ?? []) {
    const year = Number(point?.year ?? point?.ano)
    if (!Number.isFinite(year) || seen.has(year)) continue
    seen.add(year)
    unique.push(point)
  }

  unique.sort((a, b) => (
    Number(a?.year ?? a?.ano) - Number(b?.year ?? b?.ano)
  ))

  const limit = Math.max(1, Math.floor(Number(maxTicks) || 1))
  if (unique.length <= 2) return unique
  if (limit === 1) return [unique[0]]
  if (limit === 2) return [unique[0], unique.at(-1)]

  const firstYear = Number(unique[0]?.year ?? unique[0]?.ano)
  const lastYear = Number(unique.at(-1)?.year ?? unique.at(-1)?.ano)
  const preferredStep = [2, 3, 4].find((step) => (
    Math.ceil((lastYear - firstYear) / step) + 1 <= limit
  ))

  if (preferredStep) {
    return selectClosestAvailableYears(
      unique,
      buildCalendarYears(firstYear, lastYear, preferredStep),
    )
  }

  if (unique.length <= limit) return unique

  const selected = []
  const lastIndex = unique.length - 1
  for (let index = 0; index < limit; index += 1) {
    const sourceIndex = Math.round((index * lastIndex) / (limit - 1))
    const point = unique[sourceIndex]
    if (selected.at(-1) !== point) selected.push(point)
  }
  return selected
}

function buildCalendarYears(firstYear, lastYear, step) {
  const years = [firstYear]
  for (let year = firstYear + step; year < lastYear; year += step) years.push(year)
  const span = lastYear - firstYear
  const terminalGap = lastYear - years.at(-1)
  if (years.length > 1 && span > 0 && terminalGap / span < MIN_TERMINAL_TICK_SPAN_RATIO) years.pop()
  if (years.at(-1) !== lastYear) years.push(lastYear)
  return years
}

function selectClosestAvailableYears(points, targetYears) {
  const selected = []

  for (const targetYear of targetYears) {
    const candidate = points
      .filter((point) => !selected.includes(point))
      .sort((left, right) => {
        const leftYear = Number(left?.year ?? left?.ano)
        const rightYear = Number(right?.year ?? right?.ano)
        return Math.abs(leftYear - targetYear) - Math.abs(rightYear - targetYear)
          || leftYear - rightYear
      })[0]
    if (candidate) selected.push(candidate)
  }

  return selected.sort((left, right) => (
    Number(left?.year ?? left?.ano) - Number(right?.year ?? right?.ano)
  ))
}

export function resolvePneAuxiliaryYearTickLimit(chartWidth, maxTicks = 6) {
  const width = Number(chartWidth)
  const limit = Math.max(1, Math.floor(Number(maxTicks) || 1))

  if (!Number.isFinite(width)) return limit
  if (width < 300) return Math.min(limit, 3)
  if (width < 360) return Math.min(limit, 4)
  return limit
}

function buildEvenTicks(min, max, count) {
  if (count <= 1 || max <= min) return [min, max]
  return Array.from({ length: count }, (_, index) => (
    Math.round(min + ((max - min) * index) / (count - 1))
  ))
}

function buildTicksByStep(min, max, step) {
  const ticks = []
  for (let value = min; value <= max + step / 10; value += step) {
    ticks.push(Number(value.toFixed(6)))
  }
  return ticks
}

function pickNiceStep(value) {
  if (!Number.isFinite(value) || value <= 0) return 1
  const magnitude = 10 ** Math.floor(Math.log10(value))
  const normalized = value / magnitude
  const nice = normalized <= 1
    ? 1
    : normalized <= 2
      ? 2
      : normalized <= 2.5
        ? 2.5
        : normalized <= 5
          ? 5
          : 10
  return nice * magnitude
}

function buildObservedPercentageTicks(max) {
  const numericMax = Number(max)
  if (!Number.isFinite(numericMax) || numericMax <= 0) return [0, 1, 2, 3, 4, 5]
  const step = pickNiceStep(numericMax / 5)
  return buildTicksByStep(0, numericMax, step)
    .filter((value) => value <= numericMax + 0.0001)
}

function roundObservedUpperBound(value) {
  const step = pickNiceStep(value / 5)
  return Math.ceil(value / step) * step
}
