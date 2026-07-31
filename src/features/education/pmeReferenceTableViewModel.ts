import type {
  Pne2026DiagnosticResultViewModel,
  Pne2026DiagnosticViewModel,
  Pne2026ProgressResultViewModel,
  Pne2026TrackingResultViewModel,
  Pne2026DiagnosticSource,
} from '../diagnostic/diagnosticTypes'
import { getPmePublicIndicatorLabel } from './municipalTechnicalReportCatalog.js'

export const PME_COMPARISON_UNAVAILABLE = 'Sem medida municipal comparável — As bases públicas utilizadas não permitem calcular este indicador com segurança para o município.'
export const PME_REFERENCE_EQUAL = 'No valor da referência'
export const PME_DESCRIPTIVE_MONITORING = 'Acompanhamento descritivo — O indicador é apresentado como informação de contexto, sem comparação direta com uma meta municipal.'

export interface PmeReferenceDataSources {
  projections?: Record<string, unknown> | null
  planningScenarios?: Record<string, unknown> | null
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
  result: Pne2026DiagnosticResultViewModel
  rawComponents: RawComponents | null
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

const MATERIALIZED_COMPONENT_UNITS: Record<string, Pick<RawComponents, 'numeratorUnit' | 'denominatorUnit' | 'effortUnit'>> = {
  eja_atendimento_18_mais: {
    numeratorUnit: 'matrículas',
    denominatorUnit: 'pessoas',
    effortUnit: 'matrículas',
  },
  graduacao_frequencia_18_24: {
    numeratorUnit: 'pessoas',
    denominatorUnit: 'pessoas',
    effortUnit: 'pessoas',
  },
  superior_completo_25_34: {
    numeratorUnit: 'pessoas',
    denominatorUnit: 'pessoas',
    effortUnit: 'pessoas',
  },
  taxa_bruta_graduacao: {
    numeratorUnit: 'pessoas',
    denominatorUnit: 'pessoas',
    effortUnit: 'pessoas',
  },
  docentes_tempo_integral_ies: {
    numeratorUnit: 'docentes',
    denominatorUnit: 'docentes',
    effortUnit: 'docentes',
  },
  docentes_tempo_integral_universidades: {
    numeratorUnit: 'docentes contabilizados',
    denominatorUnit: 'docentes contabilizados',
    effortUnit: 'docentes contabilizados',
  },
  docentes_tempo_integral_centros_universitarios: {
    numeratorUnit: 'docentes contabilizados',
    denominatorUnit: 'docentes contabilizados',
    effortUnit: 'docentes contabilizados',
  },
  docentes_tempo_integral_faculdades: {
    numeratorUnit: 'docentes contabilizados',
    denominatorUnit: 'docentes contabilizados',
    effortUnit: 'docentes contabilizados',
  },
  educacao_indigena_cobertura_estimada_4_17: {
    numeratorUnit: 'matrículas',
    denominatorUnit: 'pessoas',
    effortUnit: 'matrículas',
  },
  aee_oferta_escolas_elegiveis: {
    numeratorUnit: 'escolas',
    denominatorUnit: 'escolas',
    effortUnit: 'escolas',
  },
  superior_docentes_mestres_doutores_sede: {
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

function formatRawComponent(value: number | null, unit: string | null) {
  if (!isFiniteNumber(value) || !unit) return '—'
  return `${integerFormatter.format(value)} ${unit}`
}

function formatMetricValue(
  value: number | null,
  unit: Pne2026DiagnosticResultViewModel['current']['unit'],
) {
  if (!isFiniteNumber(value)) return '—'
  if (unit === 'percent') return `${formatNumber(value)}%`
  if (unit === 'years') return `${formatNumber(value)} anos`
  if (unit === 'index') return `${formatNumber(value)} pontos`
  return formatNumber(value)
}

function formatCurrentResult(result: Pne2026DiagnosticResultViewModel) {
  if (!isFiniteNumber(result.current.value)) {
    return result.dataStatusLabel ?? 'Não disponível para o período'
  }
  if (result.current.unit === 'percent') {
    return formatMetricValue(result.current.value, result.current.unit)
  }
  const displayText = result.current.displayText?.trim()
  if (
    displayText
    && !displayText.includes('_')
    && !/null|não calculável|dados insuficientes|indicador indisponível/i.test(displayText)
  ) return displayText
  return formatMetricValue(result.current.displayValue, result.current.unit)
}

function formatTarget(result: Pne2026ProgressResultViewModel | Pne2026TrackingResultViewModel) {
  const reference = result.indicatorReference
  if (!isFiniteNumber(reference?.value) || !isFiniteNumber(reference?.year)) return '—'
  return `${formatMetricValue(reference.value, result.current.unit)} · até ${reference.year}`
}

function extractProjectionComponents(
  result: Pne2026DiagnosticResultViewModel,
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
  result: Pne2026DiagnosticResultViewModel,
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

function extractMaterializedComponents(
  result: Pne2026DiagnosticResultViewModel,
): RawComponents | null {
  const units = MATERIALIZED_COMPONENT_UNITS[result.indicatorId]
  if (
    !units
    || !isFiniteNumber(result.numerator)
    || !isFiniteNumber(result.denominator)
  ) return null

  return {
    numerator: result.numerator,
    denominator: result.denominator,
    ...units,
  }
}

function extractRawComponents(
  result: Pne2026DiagnosticResultViewModel,
  sources: PmeReferenceDataSources,
) {
  return extractMaterializedComponents(result)
    ?? extractProjectionComponents(result, sources.projections)
    ?? extractPlanningComponents(result, sources.planningScenarios)
}

function sourceOrganization(sourceId: string, sourcesById: Map<string, Pne2026DiagnosticSource>) {
  if (sourceId.startsWith('inep_')) return 'INEP'
  if (sourceId.startsWith('ibge_')) return 'IBGE'
  if (sourceId === 'municipal_age_population_panel') return 'MS/DATASUS'

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
  result: Pne2026DiagnosticResultViewModel,
  sourcesById: Map<string, Pne2026DiagnosticSource>,
) {
  const organizations = [...new Set(
    result.sourceIds.map((sourceId) => sourceOrganization(sourceId, sourcesById)),
  )]
  const label = organizations.length ? organizations.join('/') : 'Fonte não informada'
  return `${label} · ${result.current.year}`
}

export function formatMaterializedPmeEffort(
  result: Pne2026DiagnosticResultViewModel,
  raw: RawComponents | null = null,
): PmeEffortResult {
  if (result.dataStatus !== 'available') {
    return {
      text: result.dataStatusLabel ?? PME_COMPARISON_UNAVAILABLE,
      quantitativeCalculable: false,
      atOrBeyondReference: false,
    }
  }
  if (result.mode === 'complementary') {
    return {
      text: PME_DESCRIPTIVE_MONITORING,
      quantitativeCalculable: false,
      atOrBeyondReference: false,
    }
  }
  if (
    !result.direction
    || !isFiniteNumber(result.distance)
    || (result.mode === 'progress' && !result.classification)
  ) {
    return {
      text: PME_COMPARISON_UNAVAILABLE,
      quantitativeCalculable: false,
      atOrBeyondReference: false,
    }
  }
  if (result.distance === 0) {
    return {
      text: PME_REFERENCE_EQUAL,
      quantitativeCalculable: true,
      atOrBeyondReference: result.mode === 'tracking'
        ? result.distance >= 0
        : result.classification === 'maintain',
    }
  }

  const isAboveReference = result.mode === 'tracking'
    ? result.distance >= 0
    : result.direction === 'at_least'
      ? result.classification === 'maintain'
      : result.classification === 'advance'
  const position = isAboveReference ? 'Acima da referência' : 'Abaixo da referência'
  const comparison = isAboveReference ? 'acima' : 'abaixo'
  const amount = formatNumber(Math.abs(result.distance))
  const referenceName = result.direction === 'at_most'
    ? 'limite de referência'
    : 'valor de referência'
  const unit = result.current.unit === 'percent'
    ? `${Math.abs(result.distance) === 1 ? 'ponto percentual' : 'pontos percentuais'}`
    : raw?.effortUnit ?? (result.current.unit === 'index' ? 'pontos' : '')
  return {
    text: `${position} — ${amount} ${unit} ${comparison} do ${referenceName}.`.replace('  ', ' '),
    quantitativeCalculable: true,
    atOrBeyondReference: result.mode === 'tracking'
      ? result.distance >= 0
      : result.classification === 'maintain',
  }
}

function buildRow(
  result: Pne2026DiagnosticResultViewModel,
  sources: PmeReferenceDataSources,
  sourcesById: Map<string, Pne2026DiagnosticSource>,
): PmeReferenceRow {
  const raw = extractRawComponents(result, sources)
  const effort = formatMaterializedPmeEffort(result, raw)

  return {
    key: `${result.goalId}:${result.indicatorId}`,
    goalLabel: `Meta ${result.goalId}`,
    indicatorLabel: getPmePublicIndicatorLabel(result.indicatorId, result.publicName),
    description: result.publicName,
    relationshipLabel: result.relationshipLabel,
    year: isFiniteNumber(result.current.year) ? String(result.current.year) : '—',
    numerator: formatRawComponent(raw?.numerator ?? null, raw?.numeratorUnit ?? null),
    denominator: formatRawComponent(raw?.denominator ?? null, raw?.denominatorUnit ?? null),
    currentResult: formatCurrentResult(result),
    target: result.mode === 'complementary' ? '—' : formatTarget(result),
    effort,
    source: formatSource(result, sourcesById),
    result,
    rawComponents: raw,
  }
}

export function buildPmeReferenceTableModel(
  diagnostic: Pne2026DiagnosticViewModel,
  dataSources: PmeReferenceDataSources = {},
): PmeReferenceTableModel {
  const sourcesById = new Map(diagnostic.sources.map((source) => [source.id, source]))
  const results = diagnostic.goals
    .flatMap((goal) => goal.results)
    .sort((left, right) => left.displayOrder - right.displayOrder)

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
