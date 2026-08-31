import type {
  AvailabilityState,
  UiV2Series,
  VocacoesPneCoreBundle,
  VocacoesPneSeriesBundle,
  VocacoesPneTechnicalBundle,
} from './vocacoesPneUiV2Types'

const AVAILABILITY = new Set<AvailabilityState>([
  'observed',
  'observed_zero',
  'unavailable',
  'not_applicable',
  'suppressed',
])

function invariant(condition: unknown, message: string): asserts condition {
  if (!condition) throw new TypeError(`Bundle Job 5I inválido: ${message}`)
}

function record(value: unknown, label: string): Record<string, unknown> {
  invariant(value !== null && typeof value === 'object' && !Array.isArray(value), `${label} deve ser objeto`)
  return value as Record<string, unknown>
}

function exactKeys(value: Record<string, unknown>, expected: readonly string[], label: string) {
  const actual = Object.keys(value).sort()
  const canonical = [...expected].sort()
  invariant(actual.length === canonical.length && actual.every((key, index) => key === canonical[index]), `${label} contém propriedades inesperadas`)
}

function textualIbgeCode(value: unknown): value is string {
  return typeof value === 'string' && /^[0-9]{7}$/u.test(value)
}

function validateStateValue(state: unknown, value: unknown, label: string) {
  invariant(typeof state === 'string' && AVAILABILITY.has(state as AvailabilityState), `${label} tem estado inválido`)
  if (state === 'observed_zero') invariant(value === 0, `${label} deve preservar zero observado`)
  if (state === 'unavailable' || state === 'not_applicable' || state === 'suppressed') {
    invariant(value === null, `${label} não pode combinar ausência e número`)
  }
}

export function parseVocacoesPneCore(raw: unknown): VocacoesPneCoreBundle {
  const bundle = record(raw, 'núcleo')
  exactKeys(bundle, [
    'schemaVersion', 'contractVersion', 'meta', 'region', 'fallbackMunicipalityIbgeCode',
    'municipalities', 'directions', 'macroblocks', 'families', 'variants', 'facts',
    'distributions', 'occupationEvidence', 'bridgeSummaries', 'bridgeCorrespondences',
    'sourceRegistry', 'limitRegistry', 'visualContracts', 'languageContract',
    'parallelSeriesContract', 'occupationSelectionContract', 'bridgeContract', 'pneContract',
    'pmeContract', 'summaryBlueprint', 'indices', 'counts', 'seriesBundle', 'technicalBundle',
  ], 'núcleo')
  invariant(bundle.schemaVersion === 'vocacoes-pne-ui-bundle-v2', 'schemaVersion do núcleo')

  const meta = record(bundle.meta, 'meta')
  invariant(meta.internalOnly === true, 'bundle deve ser interno')
  invariant(meta.gate11 === 'CLOSED', 'Gate 11 deve permanecer fechado')
  invariant(meta.publicNarrativeAuthorized === false, 'narrativa pública não autorizada')
  invariant(meta.publicationAuthorized === false, 'publicação não autorizada')
  invariant(meta.publicDataWritesAuthorized === false, 'public/data deve permanecer somente leitura')

  invariant(Array.isArray(bundle.municipalities) && bundle.municipalities.length === 10, 'dez municípios')
  const municipalityCodes = bundle.municipalities.map((item, index) => {
    const municipality = record(item, `município ${index}`)
    invariant(textualIbgeCode(municipality.ibgeCode), 'código IBGE textual de sete dígitos')
    invariant(typeof municipality.name === 'string' && municipality.name.length > 0, 'nome municipal')
    return municipality.ibgeCode
  })
  invariant(new Set(municipalityCodes).size === 10, 'dez códigos municipais únicos')
  invariant(textualIbgeCode(bundle.fallbackMunicipalityIbgeCode) && municipalityCodes.includes(bundle.fallbackMunicipalityIbgeCode), 'fallback municipal canônico')

  invariant(Array.isArray(bundle.families) && bundle.families.length === 13, '13 famílias')
  invariant(Array.isArray(bundle.macroblocks) && bundle.macroblocks.length === 7, 'sete macroblocos')
  invariant(Array.isArray(bundle.variants) && bundle.variants.length === 143, '143 variantes')
  for (const value of bundle.families) {
    const family = record(value, 'família')
    invariant(family.networkScope === 'total_all_dependencies', 'rede total')
    invariant(Array.isArray(family.pmeGoalRefs) && family.pmeGoalRefs.length === 0, 'PME vazio')
  }
  for (const value of bundle.variants) {
    const variant = record(value, 'variante')
    invariant(variant.variantScope === 'region' || variant.variantScope === 'municipality', 'escopo de variante')
    if (variant.variantScope === 'region') {
      invariant(variant.entityId === 'REGION_VALE_DO_SINOS' && variant.municipalityIbgeCode === null, 'variante regional')
    } else {
      invariant(textualIbgeCode(variant.entityId) && variant.municipalityIbgeCode === variant.entityId, 'variante municipal × IBGE')
    }
  }
  invariant(Array.isArray(bundle.facts), 'facts deve ser array')
  for (const value of bundle.facts) {
    const fact = record(value, 'fato')
    validateStateValue(fact.availabilityState, fact.value, String(fact.factId))
    if (fact.unit === 'percent' && fact.value !== null) {
      invariant(typeof fact.value === 'number' && fact.value >= 0 && fact.value <= 100, `${String(fact.factId)} em escala percentual`)
      if (typeof fact.rawRatio === 'number') {
        invariant(Math.abs((fact.value as number) - fact.rawRatio * 100) < 1e-8, `${String(fact.factId)} sem dupla multiplicação`)
      }
    }
    invariant(fact.unit !== 'students', 'unidade students não normalizada')
  }
  invariant(Array.isArray(bundle.distributions), 'distribuições deve ser array')
  for (const value of bundle.distributions) {
    const distribution = record(value, 'distribuição')
    invariant(Array.isArray(distribution.municipalValues) && distribution.municipalValues.length === 10, 'distribuição com dez municípios')
    const codes = distribution.municipalValues.map((item) => {
      const municipalValue = record(item, 'valor municipal')
      validateStateValue(municipalValue.availabilityState, municipalValue.value, 'valor municipal')
      if (typeof municipalValue.value === 'number') {
        invariant(typeof municipalValue.numerator === 'number', 'numerador da distribuição')
        invariant(typeof municipalValue.denominator === 'number', 'denominador da distribuição')
        invariant(typeof municipalValue.rawRatio === 'number', 'razão bruta da distribuição')
        invariant(typeof municipalValue.displayValue === 'number', 'valor de apresentação da distribuição')
        invariant(Math.abs(municipalValue.displayValue - municipalValue.rawRatio * 100) < 1e-8, 'escala da distribuição')
      }
      return municipalValue.municipalityIbgeCode
    })
    invariant(new Set(codes).size === 10 && codes.every(textualIbgeCode), 'distribuição com dez códigos únicos')
    invariant(typeof distribution.valeMedianLabel === 'string' && distribution.valeMedianLabel.includes('Mediana'), 'mediana identificada')
  }
  const pme = record(bundle.pmeContract, 'PME')
  invariant(pme.state === 'not_materialized' && Array.isArray(pme.goalRefs) && pme.goalRefs.length === 0, 'PME não materializado')
  return raw as VocacoesPneCoreBundle
}

export function parseVocacoesPneSeriesBundle(raw: unknown): VocacoesPneSeriesBundle {
  const bundle = record(raw, 'bundle de séries')
  exactKeys(bundle, ['schemaVersion', 'series'], 'bundle de séries')
  invariant(bundle.schemaVersion === 'vocacoes-pne-ui-series-bundle-v2', 'schema de séries')
  invariant(Array.isArray(bundle.series), 'series deve ser array')
  const ids = new Set<string>()
  for (const value of bundle.series) {
    const series = record(value, 'série')
    exactKeys(series, [
      'seriesId', 'storyFamilyId', 'entityId', 'metricId', 'title', 'unit', 'period',
      'territorialLens', 'networkScope', 'ageGroup', 'populationScope', 'educationalStage',
      'offerUniverse', 'temporalNature', 'points',
    ], `série ${String(series.seriesId)}`)
    invariant(typeof series.seriesId === 'string' && !ids.has(series.seriesId), 'seriesId único')
    ids.add(series.seriesId)
    invariant(series.networkScope === 'total_all_dependencies', 'rede total da série')
    invariant(series.unit !== 'students', 'unidade students não normalizada')
    invariant(Array.isArray(series.points) && series.points.length > 0, 'pontos de série')
    let previousYear = 0
    for (const pointValue of series.points) {
      const point = record(pointValue, 'ponto')
      exactKeys(point, [
        'year', 'value', 'availabilityState', 'unit', 'sourceRef', 'territorialLens',
        'breakOrCautionState', 'aggregationRule', 'numerator', 'denominator', 'rawRatio',
        'displayValue', 'displayUnit', 'scaleContract',
      ], `ponto ${String(series.seriesId)}`)
      invariant(typeof point.year === 'number' && point.year > previousYear, 'anos ordenados sem invenção')
      previousYear = point.year
      validateStateValue(point.availabilityState, point.value, String(series.seriesId))
      if (series.unit === 'percent' && point.value !== null) {
        invariant(typeof point.value === 'number' && point.value >= 0 && point.value <= 100, 'ponto percentual 0–100')
        invariant(typeof point.rawRatio === 'number' && Math.abs((point.value as number) - point.rawRatio * 100) < 1e-8, 'escala do ponto percentual')
      }
    }
  }
  return raw as VocacoesPneSeriesBundle
}

export function parseVocacoesPneTechnicalBundle(raw: unknown): VocacoesPneTechnicalBundle {
  const bundle = record(raw, 'bundle técnico')
  exactKeys(bundle, ['schemaVersion', 'technicalEvidence'], 'bundle técnico')
  invariant(bundle.schemaVersion === 'vocacoes-pne-ui-technical-bundle-v2', 'schema técnico')
  const technical = record(bundle.technicalEvidence, 'evidência técnica')
  invariant(technical.visibleByDefault === false, 'modo técnico não pode abrir por padrão')
  invariant(technical.printedForManager === false, 'modo técnico não pode entrar na impressão da gestora')
  invariant(technical.rawCagedDetailExposed === false, 'Caged detalhado não pode ser exposto')
  invariant(Array.isArray(technical.c1C12) && technical.c1C12.length === 156, 'C1–C12 completo')
  return raw as VocacoesPneTechnicalBundle
}

export function indexSeries(series: UiV2Series[]): Map<string, UiV2Series> {
  return new Map(series.map((item) => [item.seriesId, item]))
}
