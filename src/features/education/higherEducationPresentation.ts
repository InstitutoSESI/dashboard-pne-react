import type {
  HigherEducationAnnualPoint,
  HigherEducationBreakdownViewModel,
  HigherEducationIndicatorViewModel,
} from './higherEducationTypes.js'

export const HIGHER_EDUCATION_PUBLIC_TITLES: Readonly<Record<string, string>> = Object.freeze({
  'esup-matriculas-total': 'Matrículas na graduação',
  'esup-matriculas-presenciais': 'Matrículas presenciais',
  'esup-matriculas-ead': 'Matrículas EaD',
  'esup-ies-sede': 'Instituições de Educação Superior com sede',
  'esup-polos-ead': 'Polos EaD',
  'esup-vagas-presenciais': 'Vagas presenciais',
  'esup-ingressantes': 'Ingressantes',
  'esup-concluintes': 'Concluintes',
  'esup-docentes': 'Docentes',
})

export type HigherEducationSeriesPresentation = {
  kind: 'line' | 'constant_zero' | 'single_point' | 'unavailable'
  usefulPoints: HigherEducationAnnualPoint[]
  firstPoint: HigherEducationAnnualPoint | null
  latestPoint: HigherEducationAnnualPoint | null
  trend: 'up' | 'down' | 'stable' | 'data'
  trendLabel: 'Aumentou' | 'Diminuiu' | 'Sem alteração relevante' | 'Série disponível'
  reading: string
}

export function publicHigherEducationTitle(indicator: Pick<HigherEducationIndicatorViewModel, 'id' | 'title'>) {
  return HIGHER_EDUCATION_PUBLIC_TITLES[indicator.id] ?? indicator.title
}

export function analyzeHigherEducationSeries(
  indicator: Pick<HigherEducationIndicatorViewModel, 'series' | 'unit'>,
): HigherEducationSeriesPresentation {
  const usefulPoints = indicator.series.filter(isUsablePoint)
  const firstPoint = usefulPoints[0] ?? null
  const latestPoint = usefulPoints[usefulPoints.length - 1] ?? null
  if (!firstPoint || !latestPoint) {
    return {
      kind: 'unavailable',
      usefulPoints,
      firstPoint,
      latestPoint,
      trend: 'data',
      trendLabel: 'Série disponível',
      reading: 'Sem informação municipal utilizável no período.',
    }
  }
  const distinctYears = new Set(usefulPoints.map((point) => point.year))
  const allZero = usefulPoints.every((point) => point.value === 0)
  const difference = latestPoint.value! - firstPoint.value!
  const trend = difference > 0 ? 'up' : difference < 0 ? 'down' : 'stable'
  const trendLabel = trend === 'up' ? 'Aumentou' : trend === 'down' ? 'Diminuiu' : 'Sem alteração relevante'
  if (allZero) {
    return {
      kind: 'constant_zero',
      usefulPoints,
      firstPoint,
      latestPoint,
      trend: 'stable',
      trendLabel: 'Sem alteração relevante',
      reading: 'Estabilidade no período',
    }
  }
  if (usefulPoints.length < 2 || distinctYears.size < 2) {
    return {
      kind: 'single_point',
      usefulPoints,
      firstPoint,
      latestPoint,
      trend: 'data',
      trendLabel: 'Série disponível',
      reading: 'Série insuficiente para evolução',
    }
  }
  return {
    kind: 'line',
    usefulPoints,
    firstPoint,
    latestPoint,
    trend,
    trendLabel,
    reading: trend === 'up' ? 'Aumentou no período' : trend === 'down' ? 'Diminuiu no período' : 'Sem alteração relevante no período',
  }
}

export function areHigherEducationSeriesEqual(
  first: Pick<HigherEducationIndicatorViewModel, 'series'>,
  second: Pick<HigherEducationIndicatorViewModel, 'series'>,
) {
  const firstPoints = first.series.filter(isUsablePoint)
  const secondByYear = new Map(second.series.filter(isUsablePoint).map((point) => [point.year, point.value]))
  if (!firstPoints.length || firstPoints.length !== secondByYear.size) return false
  return firstPoints.every((point) => secondByYear.has(point.year) && secondByYear.get(point.year) === point.value)
}

export type HigherEducationSupportContent = {
  hasComposition?: boolean
  hasUsefulReferenceSeries?: boolean
  breakdownCount?: number
}

export function hasSubstantiveSupportContent({
  hasComposition = false,
  hasUsefulReferenceSeries = false,
  breakdownCount = 0,
}: HigherEducationSupportContent) {
  return hasComposition || hasUsefulReferenceSeries || breakdownCount > 0
}

export type HigherEducationCategoryPresentation = {
  kind: 'bars' | 'single_category' | 'all_zero' | 'unavailable'
  chartRows: Array<{ label: string; value: number }>
  singleCategory: HigherEducationBreakdownViewModel['categories'][number] | null
  tableCategories: HigherEducationBreakdownViewModel['categories']
}

export function analyzeHigherEducationBreakdown(
  breakdown: Pick<HigherEducationBreakdownViewModel, 'categories' | 'exhaustive'>,
): HigherEducationCategoryPresentation {
  const tableCategories = breakdown.categories.filter((category) => category.value != null)
  if (!tableCategories.length) {
    return { kind: 'unavailable', chartRows: [], singleCategory: null, tableCategories }
  }
  const nonZero = tableCategories.filter((category) => Number(category.value) > 0)
  if (!nonZero.length) {
    return { kind: 'all_zero', chartRows: [], singleCategory: null, tableCategories }
  }
  if (nonZero.length === 1 && breakdown.exhaustive) {
    return { kind: 'single_category', chartRows: [], singleCategory: nonZero[0], tableCategories }
  }
  return {
    kind: 'bars',
    chartRows: nonZero.map((category) => ({ label: category.label, value: category.value! })),
    singleCategory: null,
    tableCategories,
  }
}

function isUsablePoint(point: HigherEducationAnnualPoint) {
  return (point.status === 'observed' || point.status === 'derived_zero')
    && point.value != null
    && Number.isFinite(point.value)
}
