export type MunicipalLearningMetricKey = 'ideb' | 'saebLp' | 'saebMt'

export interface MunicipalLearningMetricSnapshot {
  change: number | null
  currentValue: number | null
  currentYear: number | null
  previousValue: number | null
  previousYear: number | null
}

export interface MunicipalLearningStageSnapshot {
  key: string
  label: string
  metrics: Record<MunicipalLearningMetricKey, MunicipalLearningMetricSnapshot>
}

const LEARNING_METRICS: ReadonlyArray<{
  key: MunicipalLearningMetricKey
  sourceKey: string
}> = [
  { key: 'ideb', sourceKey: 'ideb' },
  { key: 'saebLp', sourceKey: 'saeb_lp' },
  { key: 'saebMt', sourceKey: 'saeb_mt' },
]

const LEARNING_STAGES = [
  { key: 'fundamental_anos_iniciais', label: 'Ensino Fundamental — Anos iniciais' },
  { key: 'fundamental_anos_finais', label: 'Ensino Fundamental — Anos finais' },
  { key: 'medio', label: 'Ensino Médio' },
] as const

const valueFormatter = new Intl.NumberFormat('pt-BR', {
  maximumFractionDigits: 1,
})

const changeFormatter = new Intl.NumberFormat('pt-BR', {
  maximumFractionDigits: 1,
  minimumFractionDigits: 1,
})

export function buildMunicipalLearningStages(
  learningBlock: unknown,
): MunicipalLearningStageSnapshot[] {
  return LEARNING_STAGES.map((stage) => ({
    ...stage,
    metrics: Object.fromEntries(LEARNING_METRICS.map((metric) => [
      metric.key,
      buildMetricSnapshot(learningBlock, stage.key, metric.sourceKey),
    ])) as Record<MunicipalLearningMetricKey, MunicipalLearningMetricSnapshot>,
  }))
}

export function formatMunicipalLearningValue(metric: MunicipalLearningMetricSnapshot): string {
  return metric.currentValue === null ? '—' : valueFormatter.format(metric.currentValue)
}

export function formatMunicipalLearningChange(metric: MunicipalLearningMetricSnapshot): string {
  if (metric.change === null) return 'Variação indisponível'
  if (metric.change === 0) return '0,0 pontos'
  const formatted = changeFormatter.format(Math.abs(metric.change))
  const unit = Math.abs(metric.change) === 1 ? 'ponto' : 'pontos'
  return `${metric.change > 0 ? '+' : '−'}${formatted} ${unit}`
}

export function getMunicipalLearningChangeTone(
  metric: MunicipalLearningMetricSnapshot,
): 'positive' | 'negative' | 'neutral' | 'missing' {
  if (metric.change === null) return 'missing'
  if (metric.change > 0) return 'positive'
  if (metric.change < 0) return 'negative'
  return 'neutral'
}

function buildMetricSnapshot(
  learningBlock: unknown,
  stageKey: string,
  sourceKey: string,
): MunicipalLearningMetricSnapshot {
  const series = getStageSeries(learningBlock, stageKey, sourceKey)
  const current = series.length ? series[series.length - 1] : null
  let previous: { value: number; year: number } | null = null
  if (current) {
    for (let index = series.length - 1; index >= 0; index -= 1) {
      if (series[index].year < current.year) {
        previous = series[index]
        break
      }
    }
  }

  return {
    change: current && previous ? current.value - previous.value : null,
    currentValue: current?.value ?? null,
    currentYear: current?.year ?? null,
    previousValue: previous?.value ?? null,
    previousYear: previous?.year ?? null,
  }
}

function getStageSeries(
  learningBlock: unknown,
  stageKey: string,
  sourceKey: string,
): Array<{ value: number; year: number }> {
  const seriesRoot = isRecord(learningBlock) && isRecord(learningBlock.series)
    ? learningBlock.series
    : null
  const idebSeries = seriesRoot && isRecord(seriesRoot.ideb)
    ? seriesRoot.ideb
    : null
  const series = idebSeries && Array.isArray(idebSeries[stageKey])
    ? idebSeries[stageKey]
    : []

  return series
    .flatMap((point) => {
      if (!isRecord(point)) return []
      const year = point.ano
      const value = point[sourceKey]
      return typeof year === 'number'
        && Number.isFinite(year)
        && typeof value === 'number'
        && Number.isFinite(value)
        ? [{ value, year }]
        : []
    })
    .sort((left, right) => left.year - right.year)
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object'
}
