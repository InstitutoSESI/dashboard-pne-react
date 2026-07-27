import type {
  DiagnosticDirection,
  Pne2026PublicDiagnosticV2,
  Pne2026PublicRelationshipV2,
  Pne2026PublicResultV2,
  Pne2026PublicSourceV2,
} from '../diagnostic/diagnosticTypes'
import { getPmePublicIndicatorLabel } from './municipalTechnicalReportCatalog.js'

export const PME_COMPARISON_UNAVAILABLE = 'Sem medida municipal comparável — As bases públicas utilizadas não permitem calcular este indicador com segurança para o município.'
export const PME_REFERENCE_EQUAL = 'No valor da referência'
export const PME_DESCRIPTIVE_MONITORING = 'Acompanhamento descritivo — O indicador é apresentado como informação de contexto, sem comparação direta com uma meta municipal.'

type EffortKind = 'percentage' | 'absolute' | 'index' | 'qualitative'

export interface PmeReferenceDataSources {
  projections?: Record<string, unknown> | null
  planningScenarios?: Record<string, unknown> | null
}

export interface PmeEffortInput {
  kind: EffortKind
  direction: DiagnosticDirection | null
  currentValue: number | null
  targetValue: number | null
  numerator?: number | null
  denominator?: number | null
  effortUnit?: string | null
  qualitativeAchieved?: boolean | null
}

export interface PmeEffortResult {
  text: string
  quantitativeCalculable: boolean
  atOrBeyondReference: boolean
}

export interface PmeReferenceSource {
  id: string
  organization?: string
  title: string
  period?: string
  url?: string
}

export interface PmeReferenceRow {
  key: string
  goalLabel: string
  indicatorLabel: string
  description: string
  relationshipLabel: string | null
  year: string
  numerator: string
  denominator: string
  currentResult: string
  target: string
  effort: PmeEffortResult
  source: string
}

export interface PmeReferenceThemeGroup {
  id: string
  label: string
  rows: PmeReferenceRow[]
}

export interface PmeReferenceTableModel {
  groups: PmeReferenceThemeGroup[]
  sources: PmeReferenceSource[]
  indicatorCount: number
  quantitativeCalculableCount: number
  nonQuantitativeCalculableCount: number
  themeCount: number
}

interface RawComponents {
  numerator: number
  denominator: number
  numeratorUnit: string
  denominatorUnit: string
  effortUnit: string
}

const numberFormatter = new Intl.NumberFormat('pt-BR', {
  maximumFractionDigits: 2,
})

const integerFormatter = new Intl.NumberFormat('pt-BR', {
  maximumFractionDigits: 0,
})

const PLANNING_COMPONENT_UNITS: Record<string, Pick<RawComponents, 'numeratorUnit' | 'denominatorUnit' | 'effortUnit'>> = {
  basico_integral: {
    numeratorUnit: 'matrículas',
    denominatorUnit: 'matrículas',
    effortUnit: 'matrículas',
  },
  escolas_integral: {
    numeratorUnit: 'escolas',
    denominatorUnit: 'escolas',
    effortUnit: 'escolas',
  },
  pos_graduacao: {
    numeratorUnit: 'docentes',
    denominatorUnit: 'docentes',
    effortUnit: 'docentes',
  },
  temporarios: {
    numeratorUnit: 'docentes',
    denominatorUnit: 'docentes',
    effortUnit: 'docentes',
  },
}

function isFiniteNumber(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value)
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return value != null && typeof value === 'object' && !Array.isArray(value)
    ? value as Record<string, unknown>
    : null
}

function asArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : []
}

function formatNumber(value: number) {
  return numberFormatter.format(value)
}

function isAtOrBeyondReference(
  direction: DiagnosticDirection | null,
  currentValue: number | null,
  targetValue: number | null,
) {
  if (!direction || !isFiniteNumber(currentValue) || !isFiniteNumber(targetValue)) return false
  return direction === 'at_least'
    ? currentValue >= targetValue
    : currentValue <= targetValue
}

export function calculatePmeEffort(input: PmeEffortInput): PmeEffortResult {
  if (input.kind === 'qualitative') {
    return {
      text: PME_DESCRIPTIVE_MONITORING,
      quantitativeCalculable: false,
      atOrBeyondReference: input.qualitativeAchieved === true,
    }
  }

  if (
    !input.direction
    || !isFiniteNumber(input.currentValue)
    || !isFiniteNumber(input.targetValue)
  ) {
    return {
      text: PME_COMPARISON_UNAVAILABLE,
      quantitativeCalculable: false,
      atOrBeyondReference: false,
    }
  }

  const delta = input.currentValue - input.targetValue
  const atOrBeyondReference = isAtOrBeyondReference(
    input.direction,
    input.currentValue,
    input.targetValue,
  )
  if (delta === 0) {
    return {
      text: PME_REFERENCE_EQUAL,
      quantitativeCalculable: true,
      atOrBeyondReference,
    }
  }

  const position = delta > 0 ? 'Acima da referência' : 'Abaixo da referência'
  const amount = formatNumber(Math.abs(delta))
  const comparison = delta > 0 ? 'acima' : 'abaixo'
  const referenceName = input.direction === 'at_most' ? 'limite de referência' : 'valor de referência'
  const unit = input.kind === 'percentage'
    ? `${Math.abs(delta) === 1 ? 'ponto percentual' : 'pontos percentuais'}`
    : input.effortUnit || (input.kind === 'index' ? 'pontos' : '')
  return {
    text: `${position} — ${amount} ${unit} ${comparison} do ${referenceName}.`.replace('  ', ' '),
    quantitativeCalculable: true,
    atOrBeyondReference,
  }
}

function formatRawComponent(value: number | null, unit: string | null) {
  if (!isFiniteNumber(value) || !unit) return '—'
  return `${integerFormatter.format(value)} ${unit}`
}

function formatMetricValue(value: number | null, unit: Pne2026PublicResultV2['current']['unit']) {
  if (!isFiniteNumber(value)) return '—'
  if (unit === 'percent') return `${formatNumber(value)}%`
  if (unit === 'years') return `${formatNumber(value)} anos`
  if (unit === 'index') return `${formatNumber(value)} pontos`
  return formatNumber(value)
}

function formatCurrentResult(result: Pne2026PublicResultV2) {
  if (!isFiniteNumber(result.current.value)) return '—'
  const displayText = result.current.displayText?.trim()
  if (
    displayText
    && !displayText.includes('_')
    && !/null|não calculável|dados insuficientes|indicador indisponível/i.test(displayText)
  ) return displayText
  return formatMetricValue(result.current.displayValue, result.current.unit)
}

function formatTarget(result: Pne2026PublicResultV2) {
  const reference = result.indicatorReference
  if (!isFiniteNumber(reference?.value) || !isFiniteNumber(reference?.year)) return '—'
  return `${formatMetricValue(reference.value, result.current.unit)} · até ${reference.year}`
}

function relationshipLabel(relationship: Pne2026PublicRelationshipV2) {
  if (relationship === 'partial_component') return 'Componente parcial da meta'
  if (relationship === 'contextual_proxy') return 'Indicador contextual'
  return null
}

function extractProjectionComponents(
  result: Pne2026PublicResultV2,
  projections: Record<string, unknown> | null | undefined,
): RawComponents | null {
  const projection = asRecord(projections?.[result.indicatorId])
  if (!projection) return null

  const years = asArray(projection.historical_years)
  const numerator = asArray(projection.historical_numerator)
  const denominator = asArray(projection.historical_population)
  const index = years.findIndex((year) => Number(year) === result.current.year)
  const numeratorValue = Number(numerator[index])
  const denominatorValue = Number(denominator[index])
  if (!Number.isFinite(numeratorValue) || !Number.isFinite(denominatorValue)) return null

  return {
    numerator: numeratorValue,
    denominator: denominatorValue,
    numeratorUnit: 'matrículas',
    denominatorUnit: 'pessoas',
    effortUnit: 'matrículas',
  }
}

function extractPlanningComponents(
  result: Pne2026PublicResultV2,
  scenarios: Record<string, unknown> | null | undefined,
): RawComponents | null {
  const scenario = asRecord(scenarios?.[result.indicatorId])
  const units = PLANNING_COMPONENT_UNITS[result.indicatorId]
  if (!scenario || !units || scenario.indicatorKey !== result.indicatorId) return null

  const point = asArray(scenario.historical)
    .map(asRecord)
    .find((item) => Number(item?.year) === result.current.year)
  const numerator = Number(point?.numerator)
  const denominator = Number(point?.denominator)
  if (!Number.isFinite(numerator) || !Number.isFinite(denominator)) return null

  return { numerator, denominator, ...units }
}

function extractRawComponents(
  result: Pne2026PublicResultV2,
  sources: PmeReferenceDataSources,
) {
  return extractProjectionComponents(result, sources.projections)
    ?? extractPlanningComponents(result, sources.planningScenarios)
}

function sourceOrganization(sourceId: string, sourcesById: Map<string, Pne2026PublicSourceV2>) {
  if (sourceId.startsWith('inep_')) return 'INEP'
  if (sourceId.startsWith('ibge_') || sourceId === 'municipal_age_population_panel') return 'IBGE'

  const source = sourcesById.get(sourceId)
  const acronym = source?.organization?.match(/\(([^)]+)\)/)?.[1]
  return acronym || 'Fonte em verificação'
}

function publicSourceTitle(title: string) {
  return title
    .replace(
      /^Fonte do (.+?) — proveniência pendente no pipeline$/i,
      '$1 — fonte em verificação',
    )
    .replace(/\bpipeline\b/gi, 'processo de publicação')
}

function formatSource(
  result: Pne2026PublicResultV2,
  sourcesById: Map<string, Pne2026PublicSourceV2>,
) {
  const organizations = [...new Set(
    result.sourceIds.map((sourceId) => sourceOrganization(sourceId, sourcesById)),
  )]
  const label = organizations.length ? organizations.join('/') : 'Fonte não informada'
  return `${label} · ${result.current.year}`
}

function effortKind(result: Pne2026PublicResultV2): EffortKind {
  if (result.current.unit === 'percent') return 'percentage'
  if (result.current.unit === 'count') return 'absolute'
  return 'index'
}

function buildRow(
  result: Pne2026PublicResultV2,
  sources: PmeReferenceDataSources,
  sourcesById: Map<string, Pne2026PublicSourceV2>,
): PmeReferenceRow {
  const raw = extractRawComponents(result, sources)
  const direction = result.indicatorReference.direction ?? result.direction ?? null
  const effort = calculatePmeEffort({
    kind: result.relationshipType === 'contextual_proxy' ? 'qualitative' : effortKind(result),
    direction,
    currentValue: result.current.value,
    targetValue: result.indicatorReference.value,
    numerator: raw?.numerator,
    denominator: raw?.denominator,
    effortUnit: raw?.effortUnit ?? (result.current.unit === 'years' ? 'anos' : result.current.unit === 'index' ? 'pontos' : null),
  })

  return {
    key: `${result.goalId}:${result.indicatorId}`,
    goalLabel: `Meta ${result.goalId}`,
    indicatorLabel: getPmePublicIndicatorLabel(result.indicatorId, result.publicName),
    description: result.publicName,
    relationshipLabel: relationshipLabel(result.relationshipType),
    year: String(result.current.year),
    numerator: formatRawComponent(raw?.numerator ?? null, raw?.numeratorUnit ?? null),
    denominator: formatRawComponent(raw?.denominator ?? null, raw?.denominatorUnit ?? null),
    currentResult: formatCurrentResult(result),
    target: formatTarget(result),
    effort,
    source: formatSource(result, sourcesById),
  }
}

export function buildPmeReferenceTableModel(
  diagnostic: Pne2026PublicDiagnosticV2,
  dataSources: PmeReferenceDataSources = {},
): PmeReferenceTableModel {
  const sourcesById = new Map(diagnostic.sources.map((source) => [source.id, source]))
  const results = diagnostic.goals
    .flatMap((goal) => goal.results)
    .sort((left, right) => left.resultOrder - right.resultOrder)

  const groups = [...diagnostic.presentation.themes]
    .sort((left, right) => left.order - right.order)
    .map((theme) => ({
      id: theme.id,
      label: theme.label,
      rows: results
        .filter((result) => result.themeId === theme.id)
        .map((result) => buildRow(result, dataSources, sourcesById)),
    }))
    .filter((group) => group.rows.length > 0)

  const rows = groups.flatMap((group) => group.rows)
  const sources = diagnostic.sources.map((source) => ({
    id: source.id,
    organization: source.organization,
    title: publicSourceTitle(source.publicTitle),
    period: source.period,
    url: source.officialUrl,
  }))

  return {
    groups,
    sources,
    indicatorCount: rows.length,
    quantitativeCalculableCount: rows.filter((row) => row.effort.quantitativeCalculable).length,
    nonQuantitativeCalculableCount: rows.filter((row) => !row.effort.quantitativeCalculable).length,
    themeCount: groups.length,
  }
}
