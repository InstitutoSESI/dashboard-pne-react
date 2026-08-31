import type {
  UiV2Distribution,
  UiV2Fact,
  UiV2OccupationEvidence,
  UiV2Series,
  VocacoesPneCoreBundle,
} from './vocacoesPneUiV2Types'

export const REGION_ENTITY_ID = 'REGION_VALE_DO_SINOS'

export interface SeriesQuery {
  familyId: string
  entityId: string
  metricId: string
  educationalStage?: string
  ageGroup?: string
}

export function findSeries(series: readonly UiV2Series[], query: SeriesQuery): UiV2Series | null {
  return series.find((item) => (
    item.storyFamilyId === query.familyId
    && item.entityId === query.entityId
    && item.metricId === query.metricId
    && (query.educationalStage === undefined || item.educationalStage === query.educationalStage)
    && (query.ageGroup === undefined || item.ageGroup === query.ageGroup)
  )) ?? null
}

export function findFact(
  core: VocacoesPneCoreBundle,
  query: Omit<SeriesQuery, 'ageGroup'> & { ageGroup?: string; period?: string },
): UiV2Fact | null {
  return core.facts.find((item) => (
    item.storyFamilyId === query.familyId
    && item.entityId === query.entityId
    && item.metricId === query.metricId
    && (query.educationalStage === undefined || item.educationalStage === query.educationalStage)
    && (query.ageGroup === undefined || item.ageGroup === query.ageGroup)
    && (query.period === undefined || item.period === query.period)
  )) ?? null
}

export function findDistribution(
  core: VocacoesPneCoreBundle,
  metricId: string,
  educationalStage: string,
  year = 2025,
): UiV2Distribution | null {
  return core.distributions.find((item) => (
    item.storyFamilyId === 'D1_TRAJECTORY_CONDITIONS'
    && item.metricId === metricId
    && item.educationalStage === educationalStage
    && item.year === year
  )) ?? null
}

export function evidenceForEntity(
  core: VocacoesPneCoreBundle,
  entityId: string,
  kind?: 'occupation' | 'sector',
): UiV2OccupationEvidence[] {
  return core.occupationEvidence.filter((item) => (
    item.entityId === entityId && (kind === undefined || item.kind === kind)
  ))
}

export function latestObservedPoint(series: UiV2Series | null) {
  return [...(series?.points ?? [])].reverse().find((point) => (
    point.availabilityState === 'observed' || point.availabilityState === 'observed_zero'
  )) ?? null
}

export function firstObservedPoint(series: UiV2Series | null) {
  return series?.points.find((point) => (
    point.availabilityState === 'observed' || point.availabilityState === 'observed_zero'
  )) ?? null
}

export function formatUiValue(value: number | null, unit: string, maximumFractionDigits = 1): string {
  if (value === null) return '—'
  if (unit === 'percent') {
    return `${new Intl.NumberFormat('pt-BR', { maximumFractionDigits }).format(value)}%`
  }
  if (unit === 'ratio') {
    return new Intl.NumberFormat('pt-BR', {
      minimumFractionDigits: 3,
      maximumFractionDigits: 3,
    }).format(value)
  }
  if (unit === 'BRL_nominal') {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL',
      maximumFractionDigits: 0,
    }).format(value)
  }
  return new Intl.NumberFormat('pt-BR', {
    maximumFractionDigits: Number.isInteger(value) ? 0 : maximumFractionDigits,
  }).format(value)
}

export function unitLabel(unit: string): string {
  return {
    enrollments: 'matrículas',
    schools: 'escolas',
    classes: 'turmas',
    teaching_units: 'unidades de docência',
    teachers: 'docentes ou unidades de docência',
    active_bonds: 'vínculos formais ativos',
    adjusted_events: 'eventos ajustados',
    persons: 'pessoas residentes',
    beneficiaries: 'beneficiários informados',
    percent: 'percentual',
    ratio: 'razão',
    BRL_nominal: 'R$ nominais',
    count: 'contagem',
  }[unit] ?? unit
}

export function lensLabel(lens: string): string {
  return {
    resident_population: 'população residente',
    student_residence: 'residência do estudante',
    school_location: 'localização da oferta escolar',
    rural_school_location: 'localização da oferta rural',
    workplace: 'local de trabalho',
    municipal_executor: 'executor municipal',
  }[lens] ?? lens
}

export function availabilityLabel(state: string): string {
  return {
    observed: 'Valor observado',
    observed_zero: 'Zero observado',
    unavailable: 'Indisponível na fonte congelada',
    not_applicable: 'Não aplicável',
    suppressed: 'Valor suprimido',
  }[state] ?? state
}
