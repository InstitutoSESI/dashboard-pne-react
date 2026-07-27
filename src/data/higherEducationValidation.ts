import {
  HIGHER_EDUCATION_SCHEMA_VERSION,
  type HigherEducationAnnualPoint,
  type HigherEducationManifest,
  type HigherEducationMunicipalDocument,
  type HigherEducationValueStatus,
} from '../features/education/higherEducationTypes.js'

const VALUE_STATUSES = new Set<HigherEducationValueStatus>([
  'observed',
  'derived_zero',
  'unavailable',
  'not_applicable',
])
const AVAILABILITIES = new Set(['current', 'historical_only', 'unavailable'])

function record(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value)
}

function fail(message: string): never {
  throw new Error(`Contrato de Educação Superior inválido: ${message}`)
}

function string(value: unknown, path: string) {
  if (typeof value !== 'string' || !value.trim()) fail(`${path} deve ser texto não vazio.`)
  return value
}

function integer(value: unknown, path: string) {
  if (!Number.isInteger(value)) fail(`${path} deve ser inteiro.`)
  return value as number
}

function validateSourceReference(
  point: Record<string, unknown>,
  path: string,
  sources: HigherEducationManifest['sources'],
) {
  const ids = [
    ...(typeof point.sourceId === 'string' ? [point.sourceId] : []),
    ...(Array.isArray(point.sourceIds) ? point.sourceIds : []),
  ]
  if (point.sourceId != null && typeof point.sourceId !== 'string') fail(`${path}.sourceId é malformado.`)
  if (point.sourceIds != null && (!Array.isArray(point.sourceIds) || point.sourceIds.some((id) => typeof id !== 'string'))) {
    fail(`${path}.sourceIds é malformado.`)
  }
  ids.forEach((id) => {
    if (!sources[id]) fail(`${path} referencia a fonte desconhecida ${id}.`)
  })
  return ids
}

function validateValueState(value: unknown, status: unknown, path: string) {
  if (!VALUE_STATUSES.has(status as HigherEducationValueStatus)) fail(`${path}.status é desconhecido.`)
  if (status === 'unavailable' || status === 'not_applicable') {
    if (value !== null) fail(`${path} não pode ter valor numérico com status ${status}.`)
    return
  }
  if (typeof value !== 'number' || !Number.isFinite(value)) fail(`${path}.value deve ser numérico para status ${status}.`)
  if (status === 'derived_zero' && value !== 0) fail(`${path}.value deve ser zero quando derivado.`)
}

export function validateHigherEducationManifest(value: unknown): HigherEducationManifest {
  if (!record(value)) fail('o manifesto deve ser um objeto.')
  if (value.schemaVersion !== HIGHER_EDUCATION_SCHEMA_VERSION) fail(`schemaVersion ${String(value.schemaVersion)} não é compatível.`)
  string(value.dataVersion, 'dataVersion')
  const firstYear = integer(value.firstYear, 'firstYear')
  const latestYear = integer(value.latestYear, 'latestYear')
  if (!Array.isArray(value.availableYears) || value.availableYears.some((year) => !Number.isInteger(year))) fail('availableYears é inválido.')
  const availableYears = value.availableYears as number[]
  if (!availableYears.length || availableYears[0] !== firstYear || availableYears[availableYears.length - 1] !== latestYear) fail('availableYears não corresponde ao período global.')
  if (new Set(availableYears).size !== availableYears.length) fail('availableYears contém anos repetidos.')
  integer(value.municipalityCount, 'municipalityCount')
  if (!Array.isArray(value.indicators) || !Array.isArray(value.breakdowns) || !record(value.sources)) fail('catálogos ou fontes ausentes.')

  const indicatorIds = new Set<string>()
  value.indicators.forEach((item, index) => {
    if (!record(item)) fail(`indicators[${index}] é inválido.`)
    const id = string(item.id, `indicators[${index}].id`)
    if (indicatorIds.has(id)) fail(`indicador duplicado ${id}.`)
    indicatorIds.add(id)
    string(item.universe, `indicators[${index}].universe`)
    string(item.territorialReference, `indicators[${index}].territorialReference`)
    string(item.sourceTable, `indicators[${index}].sourceTable`)
    if (!record(item.coverageByYear)) fail(`indicators[${index}].coverageByYear é inválido.`)
  })

  const breakdownIds = new Set<string>()
  value.breakdowns.forEach((item, index) => {
    if (!record(item) || !Array.isArray(item.categories)) fail(`breakdowns[${index}] é inválido.`)
    const id = string(item.id, `breakdowns[${index}].id`)
    breakdownIds.add(id)
    string(item.universe, `breakdowns[${index}].universe`)
    string(item.territorialReference, `breakdowns[${index}].territorialReference`)
    string(item.sourceTable, `breakdowns[${index}].sourceTable`)
    if (!record(item.coverageByYear)) fail(`breakdowns[${index}].coverageByYear é inválido.`)
    const categoryIds = new Set<string>()
    item.categories.forEach((category, categoryIndex) => {
      if (!record(category)) fail(`breakdowns[${index}].categories[${categoryIndex}] é inválido.`)
      const categoryId = string(category.id, `breakdowns[${index}].categories[${categoryIndex}].id`)
      string(category.label, `breakdowns[${index}].categories[${categoryIndex}].label`)
      if (categoryIds.has(categoryId)) fail(`categoria duplicada ${categoryId}.`)
      categoryIds.add(categoryId)
    })
  })
  if (breakdownIds.size !== value.breakdowns.length) fail('há breakdowns duplicados.')

  Object.entries(value.sources).forEach(([id, source]) => {
    if (!record(source)) fail(`fonte ${id} é inválida.`)
    integer(source.year, `sources.${id}.year`)
    string(source.table, `sources.${id}.table`)
    string(source.fileName, `sources.${id}.fileName`)
    string(source.sha256, `sources.${id}.sha256`)
    string(source.universe, `sources.${id}.universe`)
    string(source.territorialReference, `sources.${id}.territorialReference`)
  })
  return value as unknown as HigherEducationManifest
}

export function validateHigherEducationMunicipalDocument(
  value: unknown,
  requestedMunicipalityId: string,
  manifest: HigherEducationManifest,
): HigherEducationMunicipalDocument {
  if (!record(value)) fail('o documento municipal deve ser um objeto.')
  if (value.schemaVersion !== HIGHER_EDUCATION_SCHEMA_VERSION) fail(`schemaVersion municipal ${String(value.schemaVersion)} não é compatível.`)
  if (!record(value.municipality)) fail('municipality está ausente.')
  if (value.municipality.id !== requestedMunicipalityId) fail(`município ${String(value.municipality.id)} não corresponde ao solicitado ${requestedMunicipalityId}.`)
  string(value.municipality.name, 'municipality.name')
  if (!AVAILABILITIES.has(value.availability as string)) fail('availability é desconhecida.')
  if (!record(value.indicators) || !Array.isArray(value.breakdowns)) fail('indicadores ou breakdowns municipais ausentes.')

  const expectedYears = manifest.availableYears
  const knownIndicatorIds = new Set(manifest.indicators.map((item) => item.id))
  const actualIndicatorIds = Object.keys(value.indicators)
  if (actualIndicatorIds.some((id) => !knownIndicatorIds.has(id))) fail('o documento contém indicador desconhecido.')
  if (knownIndicatorIds.size !== actualIndicatorIds.length) fail('o documento não contém todos os indicadores.')

  const municipalIndicators = value.indicators as Record<string, unknown>
  manifest.indicators.forEach((definition) => {
    const item = municipalIndicators[definition.id]
    if (!record(item) || !Array.isArray(item.series)) fail(`indicador ${definition.id} é inválido.`)
    if (item.id !== definition.id || item.universe !== definition.universe || item.territorialReference !== definition.territorialReference) {
      fail(`contrato do indicador ${definition.id} é incompatível.`)
    }
    if (item.series.length !== expectedYears.length) fail(`série ${definition.id} não possui os ${expectedYears.length} anos esperados.`)
    item.series.forEach((rawPoint, index) => {
      if (!record(rawPoint)) fail(`${definition.id}.series[${index}] é inválido.`)
      const year = integer(rawPoint.year, `${definition.id}.series[${index}].year`)
      if (year !== expectedYears[index]) fail(`${definition.id}.series contém ano ausente, repetido ou fora do período.`)
      validateValueState(rawPoint.value, rawPoint.status, `${definition.id}.${year}`)
      validateSourceReference(rawPoint, `${definition.id}.${year}`, manifest.sources)
      const hasSource = typeof rawPoint.sourceId === 'string' || (Array.isArray(rawPoint.sourceIds) && rawPoint.sourceIds.length > 0)
      if ((rawPoint.status === 'observed' || rawPoint.status === 'derived_zero') && !hasSource) fail(`${definition.id}.${year} não possui fonte.`)
    })
  })

  const definitions = new Map(manifest.breakdowns.map((item) => [item.id, item]))
  if (value.breakdowns.length !== manifest.breakdowns.length * expectedYears.length) fail('o documento não contém todos os breakdowns anuais.')
  const seen = new Set<string>()
  value.breakdowns.forEach((rawBreakdown, index) => {
    if (!record(rawBreakdown) || !Array.isArray(rawBreakdown.categories)) fail(`breakdowns[${index}] é inválido.`)
    const definition = definitions.get(String(rawBreakdown.id))
    if (!definition) fail(`breakdown desconhecido ${String(rawBreakdown.id)}.`)
    const year = integer(rawBreakdown.year, `breakdowns[${index}].year`)
    if (!expectedYears.includes(year)) fail(`breakdown ${definition.id} possui ano fora do período.`)
    const identity = `${definition.id}:${year}`
    if (seen.has(identity)) fail(`breakdown duplicado ${identity}.`)
    seen.add(identity)
    if (rawBreakdown.universe !== definition.universe || rawBreakdown.territorialReference !== definition.territorialReference) fail(`contrato do breakdown ${identity} é incompatível.`)
    if (typeof rawBreakdown.exhaustive !== 'boolean') fail(`${identity}.exhaustive é inválido.`)
    validateValueState(
      rawBreakdown.status === 'observed' || rawBreakdown.status === 'derived_zero' ? 0 : null,
      rawBreakdown.status,
      identity,
    )
    const breakdownSourceIds = validateSourceReference(rawBreakdown, identity, manifest.sources)
    if ((rawBreakdown.status === 'observed' || rawBreakdown.status === 'derived_zero') && !breakdownSourceIds.length) fail(`${identity} não possui fonte.`)
    const categories = definition.categories
    if (rawBreakdown.categories.length !== categories.length) fail(`${identity} possui categorias ausentes.`)
    rawBreakdown.categories.forEach((rawCategory, categoryIndex) => {
      if (!record(rawCategory)) fail(`${identity}.categories[${categoryIndex}] é inválida.`)
      const expected = categories[categoryIndex]
      if (rawCategory.id !== expected.id || rawCategory.label !== expected.label) fail(`${identity} possui categoria desconhecida ou fora de ordem.`)
      validateValueState(rawCategory.value, rawCategory.status, `${identity}.${expected.id}`)
    })
  })
  return value as unknown as HigherEducationMunicipalDocument
}

export function isHigherEducationUsablePoint(point: HigherEducationAnnualPoint) {
  return point.status === 'observed' || point.status === 'derived_zero'
}
