import { resolveSignalReading } from './matrizSignalLanguage.js'
import { formatPublicValue } from '../diagnostic/diagnosticPresentation.js'
import type { MatrizPlanStatus } from '../../domain/matrizFrontsStorage.js'
import type { MatrizMeasureContext } from './matrizInsights.js'
import type {
  MatrizDistanceToTarget,
  MatrizDocument,
  MatrizNetworkConcentrationClassification,
  MatrizPeerBenchmark,
  MatrizPeerDeviation,
  MatrizPriorityGoal,
  MatrizSeverity,
  MatrizSeverityLevel,
  MatrizSignal,
  MatrizTrendDirection,
} from './matrizTypes.js'

export const MATRIZ_DISTANCE_LABEL: Readonly<Record<MatrizDistanceToTarget, string>> = Object.freeze({
  far_from_target: 'longe da referência',
  below_target: 'abaixo da referência',
  near_or_at_target: 'na referência ou perto dela',
})

export const MATRIZ_PEER_DEVIATION_LABEL: Readonly<Record<MatrizPeerDeviation, string>> = Object.freeze({
  much_worse_than_peers: 'entre as que mais precisam avançar das cidades parecidas',
  worse_than_peers: 'abaixo da maioria das cidades parecidas',
  in_line_with_peers: 'na média das cidades parecidas',
  better_than_peers: 'acima da maioria das cidades parecidas',
})

export const MATRIZ_SEVERITY_LABEL: Readonly<Record<MatrizSeverityLevel, string>> = Object.freeze({
  high: 'atenção maior',
  medium: 'atenção',
})

export const MATRIZ_TREND_LABEL: Readonly<Record<MatrizTrendDirection, string>> = Object.freeze({
  improved: 'avançou desde a leitura anterior',
  worsened: 'recuou desde a leitura anterior',
  stable: 'estável desde a leitura anterior',
})

const MATRIZ_NETWORK_CONCENTRATION_LABEL: Readonly<Record<
  MatrizNetworkConcentrationClassification,
  (affectedSchools: number, totalSchools: number) => string
>> = Object.freeze({
  concentrated_in_few_schools: (affectedSchools, totalSchools) => (
    `concentrada em poucas escolas da rede (${affectedSchools} de ${totalSchools})`
  ),
  spread_across_network: () => 'distribuída pelas escolas da rede',
})

export const MATRIZ_PLAN_STATUS_LABEL: Readonly<Record<MatrizPlanStatus, string>> = Object.freeze({
  todo: 'para fazer',
  doing: 'em andamento',
  done: 'feito',
})

const MONTHS = [
  'janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho',
  'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro',
]

export interface MatrizPublicSignalReading {
  readonly caution: string
  readonly display: string
  readonly label: string
  readonly period: string
  readonly use: string
  readonly peerBenchmarkComparison?: string
  readonly peerUse?: string
}

export function formatMatrizReferenceDate(reference: string): string {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(reference)
  if (!match) return reference
  const [, year, month, day] = match
  return `${Number(day)} de ${MONTHS[Number(month) - 1] ?? month} de ${year}`
}

export function matrizPeerComparison(severity: MatrizSeverity, uf: string): string {
  const peers = `${severity.peerN} cidades parecidas do ${uf}`
  switch (severity.peerDeviation) {
    case 'much_worse_than_peers': return `entre as que mais precisam avançar das ${peers}`
    case 'worse_than_peers': return `abaixo da maioria das ${peers}`
    case 'in_line_with_peers': return `na média das ${peers}`
    case 'better_than_peers': return `acima da maioria das ${peers}`
  }
}

function matrizPeerBenchmarkPosition(benchmark: MatrizPeerBenchmark): string {
  const difference = Number(benchmark.differenceRaw)
  let municipalPosition = 'na mediana'
  if (Math.abs(difference) >= 0.05) {
    const magnitude = benchmark.unit === 'percent'
      ? `${Math.abs(difference).toLocaleString('pt-BR', { maximumFractionDigits: 1 })} p.p.`
      : formatPublicValue(Math.abs(difference), benchmark.unit)
    municipalPosition = `${magnitude} ${difference < 0 ? 'abaixo' : 'acima'}`
  }
  return municipalPosition
}

export function matrizPeerBenchmarkComparison(goal: MatrizPriorityGoal, uf: string): string {
  const benchmark = goal.severity.peerBenchmark
  if (!benchmark) return `Comparação com pares: ${matrizPeerComparison(goal.severity, uf)}`

  const median = formatPublicValue(Number(benchmark.valueRaw), benchmark.unit)
  const municipalPosition = matrizPeerBenchmarkPosition(benchmark)
  return `Cidades parecidas do ${uf} (${benchmark.n}, ${benchmark.year}): mediana ${median} · município ${municipalPosition}`
}

export function matrizSignalPeerBenchmarkComparison(benchmark: MatrizPeerBenchmark): string {
  const median = formatPublicValue(Number(benchmark.valueRaw), benchmark.unit)
  return `Mediana das ${benchmark.n} cidades parecidas (${benchmark.year}): ${median} · município ${matrizPeerBenchmarkPosition(benchmark)}`
}

export function matrizDecisionPeerReading(goal: MatrizPriorityGoal): string {
  switch (goal.severity.peerDeviation) {
    case 'much_worse_than_peers':
      return 'A diferença para cidades parecidas mostra que o desafio está mais concentrado no município e pede resposta própria.'
    case 'worse_than_peers':
      return 'O município também fica abaixo da maioria das cidades parecidas; o contexto local precisa orientar a resposta.'
    case 'in_line_with_peers':
      return 'O resultado acompanha cidades parecidas, mas continua abaixo da referência; é um desafio compartilhado que ainda exige resposta local.'
    case 'better_than_peers':
      return 'O município supera cidades parecidas, mas ainda não alcança a referência; a comparação não elimina a necessidade de avançar.'
  }
}

export function matrizPriorityPeerSummary(matriz: MatrizDocument): string {
  const highlights = matriz.priorityGoals
    .flatMap((goal) => {
      const benchmark = goal.severity.peerBenchmark
      if (
        goal.severity.peerDeviation !== 'much_worse_than_peers'
        || !benchmark
        || benchmark.unit !== 'percent'
      ) return []

      const difference = Number(benchmark.differenceRaw)
      if (!Number.isFinite(difference) || Math.abs(difference) < 0.05) return []

      return [{
        difference,
        text: `${goal.title}, ${Math.abs(difference).toLocaleString('pt-BR', { maximumFractionDigits: 1 })} p.p. ${difference < 0 ? 'abaixo' : 'acima'} (${benchmark.year})`,
      }]
    })
    .sort((left, right) => Math.abs(right.difference) - Math.abs(left.difference))
    .slice(0, 2)

  const peers = `${matriz.peerGroup.n} cidades parecidas do ${matriz.municipality.uf}`
  if (highlights.length === 0) return `Comparação: ${peers}`
  if (highlights.length === 1) {
    return `Uma meta apresenta a maior diferença frente às ${peers}: ${highlights[0].text}.`
  }
  return `Duas metas apresentam as maiores diferenças frente às ${peers}: ${highlights[0].text}, e ${highlights[1].text}.`
}

export function formatMatrizGoalSituation(goal: {
  readonly referenceRaw: string
  readonly unit?: string
  readonly valueRaw: string
}): string {
  const unit = goal.unit ?? 'percent'
  return `${formatPublicValue(Number(goal.valueRaw), unit)} hoje · referência ${formatPublicValue(Number(goal.referenceRaw), unit)}`
}

export function matrizTrendReading(goal: MatrizPriorityGoal): string | null {
  if (!goal.trend) return null
  const previous = formatPublicValue(Number(goal.trend.previousValueRaw), goal.unit)
  const current = formatPublicValue(Number(goal.valueRaw), goal.unit)
  return `Na leitura de ${goal.trend.previousYear}: ${previous} · hoje: ${current} — ${MATRIZ_TREND_LABEL[goal.trend.direction]}.`
}

/**
 * Recortes mais amplos primeiro: sem dimensões, depois dimensões com valor
 * "total". Entre recortes igualmente amplos, vence o valor de maior módulo
 * (o evento relevante, não o registro zerado) e, por fim, o período mais novo.
 */
function narrownessOf(signal: MatrizSignal): number {
  if (!signal.dimensions) return 0
  return signal.dimensions
    .split(';')
    .filter((pair) => pair.includes('=') && !/=total$/iu.test(pair))
    .length
}

function pickBroadestSignal(candidates: readonly MatrizSignal[]): MatrizSignal {
  return [...candidates].sort((left, right) => (
    narrownessOf(left) - narrownessOf(right)
    || Math.abs(Number(right.valueRaw) || 0) - Math.abs(Number(left.valueRaw) || 0)
    || right.period.localeCompare(left.period)
  ))[0]
}

export function resolveMatrizNetworkConcentrationReading(goal: MatrizPriorityGoal): string | null {
  const concentration = goal.networkConcentration
  if (!concentration) return null
  const candidates = goal.causes.flatMap((cause): MatrizSignal[] => [
    ...(cause.proof
      ? [{ ...cause.proof, direction: 'descriptive', observability: '', stance: '' }]
      : []),
    ...cause.collapsed.signals,
  ]).filter((signal) => signal.measureId === concentration.measureId)
  if (candidates.length === 0) return null
  const reading = resolveSignalReading(pickBroadestSignal(candidates))
  if (!reading) return null
  const classification = MATRIZ_NETWORK_CONCENTRATION_LABEL[concentration.classification](
    concentration.affectedSchools,
    concentration.totalSchools,
  )
  return `${reading.label}: ${classification}.`
}

export function resolveMatrizContextReadings(
  matriz: MatrizDocument,
  context: readonly MatrizMeasureContext[],
): readonly MatrizPublicSignalReading[] {
  const signalsByMeasure = new Map<string, MatrizSignal[]>()

  for (const goal of matriz.priorityGoals) {
    for (const cause of goal.causes) {
      const candidates: MatrizSignal[] = cause.proof
        ? [{ ...cause.proof, direction: 'descriptive', observability: '', stance: '' }]
        : []
      candidates.push(...cause.collapsed.signals)
      for (const signal of candidates) {
        const bucket = signalsByMeasure.get(signal.measureId)
        if (bucket) bucket.push(signal)
        else signalsByMeasure.set(signal.measureId, [signal])
      }
    }
  }

  const readings: MatrizPublicSignalReading[] = []
  for (const item of context) {
    const candidates = signalsByMeasure.get(item.measureId)
    if (!candidates || candidates.length === 0) continue
    const signal = pickBroadestSignal(candidates)
    const reading = resolveSignalReading(signal)
    if (!reading) continue
    const peerBenchmarkComparison = item.peerUse && signal.peerBenchmark
      ? matrizSignalPeerBenchmarkComparison(signal.peerBenchmark)
      : undefined
    readings.push(Object.freeze({
      ...reading,
      caution: publicMatrizCaution(reading.caution),
      use: item.use,
      peerBenchmarkComparison,
      peerUse: peerBenchmarkComparison ? item.peerUse : undefined,
    }))
    if (readings.length === 2) break
  }
  return Object.freeze(readings)
}

/** Retira identificadores de fonte sem apagar a cautela metodológica. */
export function publicMatrizCaution(caution: string, goalTitle?: string): string {
  return caution
    .replace(/\bMeta\s+\d+\.[a-z]\b/giu, goalTitle ? `meta “${goalTitle}”` : 'esta meta')
    .replace(/\s*\|\s*valueStatus=.*$/giu, '')
    .replace(/Censo Escolar(?:\s+(\d{4}))?/giu, (_match, year: string | undefined) => (
      year ? `levantamento oficial de ${year}` : 'levantamento oficial'
    ))
    .replace(/\bCenso\b/giu, 'levantamento oficial')
    .replace(/\bda Sinopse\b/giu, 'do levantamento oficial')
    .replace(/\bSinopse\b/giu, 'levantamento oficial')
    .replace(/\bcódigo Inep\b/giu, 'identificador da escola')
    .replace(/\bInep\b/giu, 'publicação oficial')
    .replace(/\bIBGE(?:\/MUNIC)?\b/giu, 'levantamento oficial')
    .replace(/\bAtlas Digital de Desastres\b/giu, 'registro oficial de desastres')
    .replace(/\bparceir\w*\b/giu, 'articulação com outras esferas')
    .replace(/\b[A-Za-z]+(?:_[A-Za-z0-9]+)+\b/g, 'campo da publicação')
    .replace(/\s{2,}/g, ' ')
    .trim()
}
