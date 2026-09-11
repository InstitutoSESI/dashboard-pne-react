import { loadMunicipioData } from '../../data/staticData'
import {
  PNE_2026_GOAL_INDICATOR_CONTRACT,
  getPne2026Indicator,
} from '../../data/pne2026GoalIndicatorContract.js'
import { getPne2026PublicLegalGoalRelations } from '../../data/pne2026LegalGoalIndicatorMap.js'
import type { MunicipioData } from '../../types/data'
import type { PmeDataState, PmeEvidence } from './pmeTypes'

const IBGE7_PATTERN = /^\d{7}$/

type PmeHistoryReason =
  | 'evidence_not_observed'
  | 'indicator_not_mapped'
  | 'series_not_published'
  | 'series_empty'

export interface PmeEvidenceHistoryPoint {
  year: number
  value: number | null
}

export interface PmeEvidenceHistorySource {
  sourceId: string
  title: string
  officialUrl: string | null
}

export interface PmeEvidenceHistoryAvailable {
  status: 'available'
  dataState: PmeDataState
  indicatorId: string
  seriesKey: string
  points: PmeEvidenceHistoryPoint[]
  unit: string
  universe: string | null
  sources: PmeEvidenceHistorySource[]
  sourceDocument: string
  sourceRelease: string
  temporalCompatibility: 'same_period_and_value' | 'same_period_different_value' | 'period_not_in_series' | 'current_period_not_published'
}

export interface PmeEvidenceHistoryAbsent {
  status: 'absent'
  dataState: PmeDataState
  reason: PmeHistoryReason
  indicatorId: string
}

export type PmeEvidenceHistory = PmeEvidenceHistoryAvailable | PmeEvidenceHistoryAbsent

type RecordValue = Record<string, unknown>
type ContractIndicator = { indicatorId: string; formulaId: string; sourceIds: string[]; unit: string }
type ContractSource = { publicTitle: string; officialUrl?: string | null }
type ContractFormula = { universe?: unknown }

function isRecord(value: unknown): value is RecordValue {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value)
}

function isHistoryEligible(state: PmeDataState): boolean {
  return state === 'observed' || state === 'null'
}

/**
 * Resolves the public index key exclusively through the published PNE contract
 * and legal-goal map. Names and labels are deliberately not lookup keys.
 */
export function resolvePmeEvidenceSeriesKey(evidence: Pick<PmeEvidence, 'goalId' | 'indicatorId' | 'relationId'>): string | null {
  const indicator = getPne2026Indicator(evidence.indicatorId) as ContractIndicator | undefined
  if (!indicator) return null
  const relation = getPne2026PublicLegalGoalRelations(evidence.goalId).find((candidate: { relationId: string; indicatorId: string }) => (
    candidate.relationId === evidence.relationId && candidate.indicatorId === evidence.indicatorId
  ))
  return relation ? indicator.indicatorId : null
}

function historySources(indicatorId: string): PmeEvidenceHistorySource[] {
  const indicator = getPne2026Indicator(indicatorId) as ContractIndicator | undefined
  if (!indicator) return []
  return indicator.sourceIds.flatMap((sourceId) => {
    const source = (PNE_2026_GOAL_INDICATOR_CONTRACT.sources as Record<string, ContractSource>)[sourceId]
    return source ? [{
      sourceId,
      title: source.publicTitle,
      officialUrl: source.officialUrl ?? null,
    }] : []
  })
}

function historyUniverse(indicatorId: string): string | null {
  const indicator = getPne2026Indicator(indicatorId) as ContractIndicator | undefined
  const formula = indicator
    ? (PNE_2026_GOAL_INDICATOR_CONTRACT.formulas as Record<string, ContractFormula>)[indicator.formulaId]
    : null
  return typeof formula?.universe === 'string' ? formula.universe : null
}

function readPublishedSeries(document: MunicipioData, seriesKey: string): PmeEvidenceHistoryPoint[] | null {
  const cycle = isRecord(document.pne_2026_2036) ? document.pne_2026_2036 : null
  const indicators = cycle && isRecord(cycle.indicadores) ? cycle.indicadores : null
  const indicator = indicators && isRecord(indicators[seriesKey]) ? indicators[seriesKey] : null
  if (!indicator || indicator.available !== true || !Array.isArray(indicator.series)) return null

  const seenYears = new Set<number>()
  const points: PmeEvidenceHistoryPoint[] = []
  for (const rawPoint of indicator.series) {
    if (!isRecord(rawPoint)) throw new TypeError(`A série publicada de ${seriesKey} contém ponto inválido.`)
    const year = typeof rawPoint.ano === 'number' ? rawPoint.ano : NaN
    const rawValue = rawPoint.valor
    const value = rawValue === null ? null : typeof rawValue === 'number' && Number.isFinite(rawValue) ? rawValue : undefined
    if (!Number.isInteger(year) || seenYears.has(year) || value === undefined) {
      throw new TypeError(`A série publicada de ${seriesKey} tem ano duplicado ou valor inválido.`)
    }
    seenYears.add(year)
    points.push({ year, value })
  }
  return points.sort((left, right) => left.year - right.year)
}

function sourceRelease(document: MunicipioData): string {
  const cycle = isRecord(document.pne_2026_2036) ? document.pne_2026_2036 : null
  const generatedAt = typeof document.generated_at === 'string'
    ? document.generated_at
    : typeof cycle?.generated_at === 'string' ? cycle.generated_at : null
  if (generatedAt) return `Índice público gerado em ${generatedAt}.`
  const dataVersion = typeof document.data_version === 'string'
    ? document.data_version
    : typeof cycle?.data_version === 'string' ? cycle.data_version : null
  if (dataVersion) return `Índice público na versão ${dataVersion}.`
  return 'Índice público sem identificador próprio de release.'
}

function temporalCompatibility(
  evidence: Pick<PmeEvidence, 'period' | 'rawValue'>,
  points: readonly PmeEvidenceHistoryPoint[],
): PmeEvidenceHistoryAvailable['temporalCompatibility'] {
  if (evidence.period === null) return 'current_period_not_published'
  const point = points.find((candidate) => candidate.year === evidence.period)
  if (!point) return 'period_not_in_series'
  return point.value === evidence.rawValue ? 'same_period_and_value' : 'same_period_different_value'
}

/** Builds an auditable view of an already published annual series; no value is recalculated. */
export function buildPmeEvidenceHistory(
  document: MunicipioData,
  municipalityId: string,
  evidence: Pick<PmeEvidence, 'dataState' | 'goalId' | 'indicatorId' | 'period' | 'rawValue' | 'relationId' | 'unit'>,
): PmeEvidenceHistory {
  if (!IBGE7_PATTERN.test(municipalityId) || document.id_municipio !== municipalityId) {
    throw new TypeError('A série PME não corresponde ao código IBGE textual do município selecionado.')
  }
  if (!isHistoryEligible(evidence.dataState)) {
    return { status: 'absent', dataState: evidence.dataState, reason: 'evidence_not_observed', indicatorId: evidence.indicatorId }
  }
  const seriesKey = resolvePmeEvidenceSeriesKey(evidence)
  if (!seriesKey) {
    return { status: 'absent', dataState: evidence.dataState, reason: 'indicator_not_mapped', indicatorId: evidence.indicatorId }
  }
  const canonicalUnit = (getPne2026Indicator(evidence.indicatorId) as ContractIndicator | undefined)?.unit
  if (evidence.unit !== null && canonicalUnit && evidence.unit !== canonicalUnit) {
    throw new TypeError(`A unidade da evidência (${evidence.unit}) não corresponde à unidade canônica (${canonicalUnit}).`)
  }
  const points = readPublishedSeries(document, seriesKey)
  if (points === null) {
    return { status: 'absent', dataState: evidence.dataState, reason: 'series_not_published', indicatorId: evidence.indicatorId }
  }
  if (!points.length) {
    return { status: 'absent', dataState: evidence.dataState, reason: 'series_empty', indicatorId: evidence.indicatorId }
  }
  return {
    status: 'available',
    dataState: evidence.dataState,
    indicatorId: evidence.indicatorId,
    seriesKey,
    points,
    unit: canonicalUnit ?? 'count',
    universe: historyUniverse(evidence.indicatorId),
    sources: historySources(evidence.indicatorId),
    sourceDocument: `/data/municipios/${municipalityId}/index.json`,
    sourceRelease: sourceRelease(document),
    temporalCompatibility: temporalCompatibility(evidence, points),
  }
}

export function loadPmeEvidenceHistory(
  municipalityId: string,
  evidence: Pick<PmeEvidence, 'dataState' | 'goalId' | 'indicatorId' | 'period' | 'rawValue' | 'relationId' | 'unit'>,
  load = loadMunicipioData,
): Promise<PmeEvidenceHistory> {
  if (!IBGE7_PATTERN.test(municipalityId)) {
    return Promise.reject(new TypeError('A série PME requer um código IBGE textual válido.'))
  }
  if (!isHistoryEligible(evidence.dataState)) {
    return Promise.resolve({ status: 'absent', dataState: evidence.dataState, reason: 'evidence_not_observed', indicatorId: evidence.indicatorId })
  }
  return load(municipalityId).then((document) => buildPmeEvidenceHistory(document, municipalityId, evidence))
}
