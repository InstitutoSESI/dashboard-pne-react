export const SCHOOL_INFRASTRUCTURE_CONTRACT_VERSION = 'school-infrastructure-v2' as const

export const SCHOOL_INFRASTRUCTURE_INDICATOR_ORDER = [
  'agua_potavel',
  'energia_eletrica',
  'internet',
  'biblioteca_sala_leitura',
  'quadra_esportes',
  'esgoto_rede_publica',
] as const

export const SCHOOL_INFRASTRUCTURE_CUT_ORDER = [
  'total',
  'publica',
  'municipal',
  'estadual',
  'federal',
  'privada',
  'urbana',
  'rural',
] as const

export const SCHOOL_INFRASTRUCTURE_STATUSES = [
  'published',
  'partial',
  'unavailable',
] as const

export type SchoolInfrastructureIndicatorKey = typeof SCHOOL_INFRASTRUCTURE_INDICATOR_ORDER[number]
export type SchoolInfrastructureCutKey = typeof SCHOOL_INFRASTRUCTURE_CUT_ORDER[number]
export type SchoolInfrastructureStatus = typeof SCHOOL_INFRASTRUCTURE_STATUSES[number]

export const SCHOOL_INFRASTRUCTURE_PUBLIC_COPY: Record<
  SchoolInfrastructureIndicatorKey,
  { label: string; shortLabel: string; description: string }
> = {
  agua_potavel: {
    label: 'Escolas com água potável',
    shortLabel: 'Água potável',
    description: 'Percentual de escolas com disponibilidade de água potável.',
  },
  energia_eletrica: {
    label: 'Escolas com energia elétrica',
    shortLabel: 'Energia elétrica',
    description: 'Percentual de escolas que dispõem de energia elétrica.',
  },
  internet: {
    label: 'Escolas com acesso à internet',
    shortLabel: 'Internet',
    description: 'Percentual de escolas com acesso à internet.',
  },
  biblioteca_sala_leitura: {
    label: 'Escolas com biblioteca ou sala de leitura',
    shortLabel: 'Biblioteca ou sala de leitura',
    description: 'Percentual de escolas com biblioteca ou sala de leitura.',
  },
  quadra_esportes: {
    label: 'Escolas com quadra de esportes',
    shortLabel: 'Quadra de esportes',
    description: 'Percentual de escolas com quadra de esportes.',
  },
  esgoto_rede_publica: {
    label: 'Escolas atendidas por rede pública de esgoto',
    shortLabel: 'Rede pública de esgoto',
    description: 'Percentual de escolas atendidas por rede pública de esgoto.',
  },
}

export const SCHOOL_INFRASTRUCTURE_CUT_LABELS: Record<SchoolInfrastructureCutKey, string> = {
  total: 'Total',
  publica: 'Rede pública',
  municipal: 'Rede municipal',
  estadual: 'Rede estadual',
  federal: 'Rede federal',
  privada: 'Rede privada',
  urbana: 'Urbana',
  rural: 'Rural',
}

export const SCHOOL_INFRASTRUCTURE_SOURCE = 'Censo Escolar/INEP'
export const SCHOOL_INFRASTRUCTURE_METHODOLOGY =
  'Percentuais calculados sobre as escolas em atividade com resposta válida para cada informação.'

export interface SchoolInfrastructureUniverse {
  unit: 'school'
  identifier: 'CO_ENTIDADE'
  municipalityVariable: 'CO_MUNICIPIO'
  activeStatus: {
    variable: 'TP_SITUACAO_FUNCIONAMENTO'
    value: 1
  }
  deduplication: 'CO_ENTIDADE'
}

export interface SchoolInfrastructureDefinition {
  label: string
  sourceVariable: string
}

export interface SchoolInfrastructureResult {
  numerator: number
  denominator: number
  percentage: number | null
  totalActiveSchools: number
  observedSchools: number
  missingSchools: number
  status: SchoolInfrastructureStatus
}

export interface SchoolInfrastructureCut {
  kind: 'total' | 'dependency' | 'location'
  totalActiveSchools: number
  indicators: Record<SchoolInfrastructureIndicatorKey, SchoolInfrastructureResult>
}

export interface SchoolInfrastructureYear {
  year: number
  cuts: Record<SchoolInfrastructureCutKey, SchoolInfrastructureCut>
}

export interface SchoolInfrastructureContract {
  contractVersion: typeof SCHOOL_INFRASTRUCTURE_CONTRACT_VERSION
  referenceYear: number
  availableYears: number[]
  universe: SchoolInfrastructureUniverse
  indicatorDefinitions: Record<SchoolInfrastructureIndicatorKey, SchoolInfrastructureDefinition>
  years: SchoolInfrastructureYear[]
}

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null && !Array.isArray(value)

const isFiniteNonNegativeInteger = (value: unknown): value is number =>
  typeof value === 'number' && Number.isFinite(value) && Number.isInteger(value) && value >= 0

const hasExactKeys = (value: Record<string, unknown>, expected: readonly string[]) => {
  const actual = Object.keys(value)
  return actual.length === expected.length && expected.every((key) => actual.includes(key))
}

function validateResult(value: unknown, totalActiveSchools: number) {
  if (!isRecord(value)) return false
  const { numerator, denominator, percentage, observedSchools, missingSchools, status } = value
  if (
    !isFiniteNonNegativeInteger(numerator)
    || !isFiniteNonNegativeInteger(denominator)
    || !isFiniteNonNegativeInteger(value.totalActiveSchools)
    || !isFiniteNonNegativeInteger(observedSchools)
    || !isFiniteNonNegativeInteger(missingSchools)
    || !SCHOOL_INFRASTRUCTURE_STATUSES.includes(status as SchoolInfrastructureStatus)
  ) return false
  if (
    value.totalActiveSchools !== totalActiveSchools
    || numerator > denominator
    || denominator !== observedSchools
    || missingSchools !== totalActiveSchools - observedSchools
  ) return false
  if (denominator === 0) return percentage === null
  return typeof percentage === 'number'
    && Number.isFinite(percentage)
    && percentage >= 0
    && percentage <= 100
}

export function isSchoolInfrastructureContract(value: unknown): value is SchoolInfrastructureContract {
  if (!isRecord(value) || value.contractVersion !== SCHOOL_INFRASTRUCTURE_CONTRACT_VERSION) return false
  if (
    !isFiniteNonNegativeInteger(value.referenceYear)
    || !Array.isArray(value.availableYears)
    || value.availableYears.length === 0
    || !value.availableYears.every(isFiniteNonNegativeInteger)
    || !value.availableYears.includes(value.referenceYear)
  ) return false

  const universe = value.universe
  if (
    !isRecord(universe)
    || universe.unit !== 'school'
    || universe.identifier !== 'CO_ENTIDADE'
    || universe.municipalityVariable !== 'CO_MUNICIPIO'
    || universe.deduplication !== 'CO_ENTIDADE'
    || !isRecord(universe.activeStatus)
    || universe.activeStatus.variable !== 'TP_SITUACAO_FUNCIONAMENTO'
    || universe.activeStatus.value !== 1
  ) return false

  const definitions = value.indicatorDefinitions
  if (!isRecord(definitions) || !hasExactKeys(definitions, SCHOOL_INFRASTRUCTURE_INDICATOR_ORDER)) return false
  for (const key of SCHOOL_INFRASTRUCTURE_INDICATOR_ORDER) {
    const definition = definitions[key]
    if (!isRecord(definition) || typeof definition.label !== 'string' || typeof definition.sourceVariable !== 'string') {
      return false
    }
  }

  if (!Array.isArray(value.years) || value.years.length !== value.availableYears.length) return false
  const seenYears = new Set<number>()
  for (const yearValue of value.years) {
    if (!isRecord(yearValue) || !isFiniteNonNegativeInteger(yearValue.year) || !isRecord(yearValue.cuts)) return false
    if (!value.availableYears.includes(yearValue.year) || seenYears.has(yearValue.year)) return false
    seenYears.add(yearValue.year)
    if (!hasExactKeys(yearValue.cuts, SCHOOL_INFRASTRUCTURE_CUT_ORDER)) return false
    for (const cutKey of SCHOOL_INFRASTRUCTURE_CUT_ORDER) {
      const cut = yearValue.cuts[cutKey]
      if (!isRecord(cut) || !isFiniteNonNegativeInteger(cut.totalActiveSchools) || !isRecord(cut.indicators)) return false
      if (!['total', 'dependency', 'location'].includes(String(cut.kind))) return false
      if (!hasExactKeys(cut.indicators, SCHOOL_INFRASTRUCTURE_INDICATOR_ORDER)) return false
      for (const indicatorKey of SCHOOL_INFRASTRUCTURE_INDICATOR_ORDER) {
        if (!validateResult(cut.indicators[indicatorKey], cut.totalActiveSchools)) return false
      }
    }
  }
  return value.availableYears.every((year) => seenYears.has(year))
}

export function assertSchoolInfrastructureContract(value: unknown): asserts value is SchoolInfrastructureContract {
  if (!isSchoolInfrastructureContract(value)) {
    throw new Error('Contrato school-infrastructure-v2 inválido no documento municipal.')
  }
}

export function getSchoolInfrastructureContractFromDocument(document: unknown) {
  if (!isRecord(document)) return null
  const blocks = document.blocos
  if (!isRecord(blocks) || !isRecord(blocks.rede_escolar) || !isRecord(blocks.rede_escolar.infraestrutura)) {
    return null
  }
  const infrastructure = blocks.rede_escolar.infraestrutura
  if (infrastructure.contractVersion == null) return null
  assertSchoolInfrastructureContract(infrastructure)
  return infrastructure
}

export function selectSchoolInfrastructureYear(
  contract: SchoolInfrastructureContract,
  year = contract.referenceYear,
) {
  return contract.years.find((entry) => entry.year === year) ?? null
}

export function selectSchoolInfrastructureResult(
  contract: SchoolInfrastructureContract,
  indicator: SchoolInfrastructureIndicatorKey,
  cut: SchoolInfrastructureCutKey = 'total',
  year = contract.referenceYear,
) {
  return selectSchoolInfrastructureYear(contract, year)?.cuts[cut]?.indicators[indicator] ?? null
}

export function formatSchoolInfrastructurePercentage(result: SchoolInfrastructureResult | null) {
  if (!result || result.totalActiveSchools === 0) return 'Não se aplica'
  if (result.denominator === 0 || result.percentage == null) return 'Não disponível'
  return `${result.percentage.toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 })}%`
}

export function formatSchoolInfrastructureQuantity(result: SchoolInfrastructureResult | null) {
  if (!result || result.totalActiveSchools === 0) return 'Não se aplica'
  if (result.denominator === 0) return 'Não disponível'
  return `${result.numerator.toLocaleString('pt-BR')} de ${result.denominator.toLocaleString('pt-BR')}`
}

export function formatSchoolInfrastructureReportCell(result: SchoolInfrastructureResult | null) {
  const quantity = formatSchoolInfrastructureQuantity(result)
  if (quantity === 'Não se aplica' || quantity === 'Não disponível') return quantity
  return `${quantity} · ${formatSchoolInfrastructurePercentage(result)}`
}
