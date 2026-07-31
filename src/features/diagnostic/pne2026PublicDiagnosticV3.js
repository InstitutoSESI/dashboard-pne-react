import presentationPolicy from '../../../contracts/pne2026-diagnostic-presentation-policy.json' with { type: 'json' }
import {
  PNE_2026_CONTRACT_VERSION,
  PNE_2026_GOAL_INDICATOR_CONTRACT,
  PNE_2026_RELATIONSHIP_MODES,
  getPne2026RelationContext,
} from '../../data/pne2026GoalIndicatorContract.js'
import {
  formatPublicValue,
  resolvePne2026DiagnosticViewModel,
} from './diagnosticPresentation.js'
import {
  getPne2026ReferenceLabel,
} from './pne2026DiagnosticPresentationCatalog.js'

export const PNE_2026_PUBLIC_DIAGNOSTIC_V3_SCHEMA = 'pne2026-public-diagnostic-v4'
export const PNE_2026_CONTRACT_HASH = 'f2778fe65582cb6efbbc0dc8e4b74dad023a656193beb2ea65954c30a91f1c9e'
export const PNE_2026_PRESENTATION_POLICY_HASH = 'c330fb98c727dbb461b809a5f178f92ac73661ee3fe4e9c73cfb9b38ea9f1d3b'

const TOP_LEVEL_FIELDS = new Set([
  'schemaVersion',
  'contractVersion',
  'contractHash',
  'presentationPolicyVersion',
  'presentationPolicyHash',
  'municipality',
  'summary',
  'results',
])
const MUNICIPALITY_FIELDS = new Set(['id', 'name'])
const SUMMARY_FIELDS = new Set([
  'visibleResultCount',
  'progressResultCount',
  'trackingResultCount',
  'complementaryResultCount',
  'legalReferenceResultCount',
  'monitoringReferenceResultCount',
  'dataStatusCounts',
  'classificationCounts',
  'presentationPriorityCounts',
])
const CLASSIFICATION_COUNT_FIELDS = new Set(['advance', 'maintain', 'unclassified'])
const PRIORITY_COUNT_FIELDS = new Set(['essential', 'standard'])
const DATA_STATUS_COUNT_FIELDS = new Set([
  'available',
  'unavailable',
  'not_applicable',
  'suppressed',
])
export const PNE_2026_V3_RESULT_FIELDS = new Set([
  'relationId',
  'goalId',
  'indicatorId',
  'dataStatus',
  'reasonCode',
  'year',
  'value',
  'numeratorField',
  'numeratorValue',
  'denominatorField',
  'denominatorValue',
  'resolvedReferenceId',
  'distance',
  'remainingGap',
  'favorableDifference',
  'status',
  'classification',
  'publicReading',
  'stateComparison',
  'statewidePosition',
  'similarMunicipalityComparison',
  'trend',
  'projection',
])
const NESTED_RESULT_FIELDS = new Map([
  ['stateComparison', new Set([
    'state',
    'municipalityValue',
    'stateValue',
    'year',
    'unit',
    'difference',
    'favorableDifference',
    'reading',
    'valueReading',
  ])],
  ['statewidePosition', new Set(['reading'])],
  ['similarMunicipalityComparison', new Set([
    'title',
    'year',
    'median',
    'unit',
    'reading',
  ])],
  ['trend', new Set(['historicalReading'])],
  ['projection', new Set([
    'estimatedAchievementYear',
    'achievementReading',
    'modelReading',
    'denominatorReading',
    'uncertaintyReading',
  ])],
])

const relationsById = new Map(
  PNE_2026_GOAL_INDICATOR_CONTRACT.relations.map((relation) => [
    relation.relationId,
    relation,
  ]),
)
const policyByRelationId = new Map(
  presentationPolicy.relations.map((entry) => [entry.relationId, entry]),
)
const SOURCE_PERIODS = Object.freeze({
  ibge_censo_demografico_2010_2022: '2010 e 2022',
  ibge_censo_demografico_2022_educacao_10061: '2022',
  ibge_censo_demografico_2022_educacao_superior: '2022',
  ibge_censo_demografico_2022_indigena_9970: '2022',
  inep_censo_escolar: '2014–2025',
  inep_avaliacao_alfabetizacao: '2023–2025',
  inep_sinopse_educacao_basica: '2024–2025',
  inep_censo_educacao_superior: '2018–2024',
  inep_saeb: '2019–2023',
  ibge_munic_2021: '2021',
  capes_sucupira_2024: '2024',
  inep_cpc_2023: '2023',
  inep_enade_licenciaturas_2025: '2025',
  municipal_age_population_panel: '2000–2025',
})

function invariant(condition, message) {
  if (!condition) throw new TypeError(`Diagnóstico PNE V3 inválido: ${message}`)
}

function isObject(value) {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value)
}

function validateExactFields(value, allowed, path, required = allowed) {
  invariant(isObject(value), `${path} deve ser objeto.`)
  const keys = Object.keys(value)
  const unknown = keys.filter((key) => !allowed.has(key))
  invariant(!unknown.length, `${path} contém campos desconhecidos: ${unknown.join(', ')}.`)
  const missing = [...required].filter((key) => !Object.hasOwn(value, key))
  invariant(!missing.length, `${path} não contém campos obrigatórios: ${missing.join(', ')}.`)
  return value
}

function validateFiniteTree(value, path = '$') {
  if (typeof value === 'number') {
    invariant(Number.isFinite(value), `${path} contém NaN ou Infinity.`)
    return
  }
  if (Array.isArray(value)) {
    value.forEach((child, index) => validateFiniteTree(child, `${path}[${index}]`))
    return
  }
  if (isObject(value)) {
    Object.entries(value).forEach(([key, child]) => {
      validateFiniteTree(child, `${path}.${key}`)
    })
  }
}

function canonicalJson(value) {
  if (Array.isArray(value)) return value.map(canonicalJson)
  if (!isObject(value)) return value
  return Object.fromEntries(
    Object.keys(value)
      .sort()
      .map((key) => [key, canonicalJson(value[key])]),
  )
}

function buildCanonicalSummary(results) {
  const summary = {
    visibleResultCount: results.length,
    progressResultCount: 0,
    trackingResultCount: 0,
    complementaryResultCount: 0,
    legalReferenceResultCount: 0,
    monitoringReferenceResultCount: 0,
    dataStatusCounts: {
      available: 0,
      unavailable: 0,
      not_applicable: 0,
      suppressed: 0,
    },
    classificationCounts: { advance: 0, maintain: 0, unclassified: 0 },
    presentationPriorityCounts: { essential: 0, standard: 0 },
  }
  for (const result of results) {
    const relation = relationsById.get(result.relationId)
    const editorial = policyByRelationId.get(result.relationId)
    summary.dataStatusCounts[result.dataStatus] += 1
    summary.presentationPriorityCounts[editorial.summaryPriority] += 1
    if (relation.mode === PNE_2026_RELATIONSHIP_MODES.PROGRESS) {
      summary.progressResultCount += 1
      if (result.dataStatus === 'available' && result.resolvedReferenceId) {
        summary.legalReferenceResultCount += 1
        const classification = ['advance', 'maintain'].includes(result.classification)
          ? result.classification
          : 'unclassified'
        summary.classificationCounts[classification] += 1
      }
    } else if (relation.mode === PNE_2026_RELATIONSHIP_MODES.TRACKING) {
      summary.trackingResultCount += 1
      if (result.dataStatus === 'available' && result.resolvedReferenceId) {
        summary.monitoringReferenceResultCount += 1
      }
    } else {
      summary.complementaryResultCount += 1
    }
  }
  return summary
}

function validateResult(result, index, seen) {
  const path = `$.results[${index}]`
  validateExactFields(
    result,
    PNE_2026_V3_RESULT_FIELDS,
    path,
    new Set(['relationId', 'goalId', 'indicatorId', 'dataStatus']),
  )
  const relation = relationsById.get(result.relationId)
  invariant(relation, `${path}.relationId desconhecido.`)
  invariant(
    relation.goalId === result.goalId && relation.indicatorId === result.indicatorId,
    `${path} diverge da identidade canônica de ${result.relationId}.`,
  )
  invariant(!seen.has(result.relationId), `${path}.relationId duplicado.`)
  seen.add(result.relationId)
  invariant(
    relation.mode !== PNE_2026_RELATIONSHIP_MODES.HIDDEN
      && relation.includeInDiagnostic === true,
    `${path} referencia relação oculta.`,
  )
  invariant(policyByRelationId.has(result.relationId), `${path} não possui política editorial.`)
  invariant(DATA_STATUS_COUNT_FIELDS.has(result.dataStatus), `${path}.dataStatus inválido.`)
  if (result.dataStatus === 'available') {
    invariant(Number.isInteger(result.year), `${path}.year inválido.`)
    invariant(Number.isFinite(result.value), `${path}.value inválido.`)
  } else {
    const forbiddenNegative = [
      'year',
      'value',
      'numeratorValue',
      'denominatorValue',
      'resolvedReferenceId',
      'distance',
      'remainingGap',
      'favorableDifference',
      'status',
      'classification',
      'publicReading',
      'stateComparison',
      'statewidePosition',
      'similarMunicipalityComparison',
      'trend',
      'projection',
    ].filter((field) => Object.hasOwn(result, field))
    invariant(!forbiddenNegative.length, `${path} contém resultado em estado negativo.`)
    invariant(typeof result.reasonCode === 'string' && result.reasonCode, `${path}.reasonCode obrigatório.`)
  }
  for (const field of ['numeratorField', 'denominatorField']) {
    if (Object.hasOwn(result, field)) {
      invariant(typeof result[field] === 'string' && result[field].trim(), `${path}.${field} inválido.`)
    }
  }
  for (const field of ['numeratorValue', 'denominatorValue']) {
    if (Object.hasOwn(result, field)) {
      invariant(Number.isFinite(result[field]), `${path}.${field} deve ser numérico.`)
    }
  }

  if (Object.hasOwn(result, 'resolvedReferenceId')) {
    const reference = getPne2026RelationContext(
      relation.goalId,
      relation.indicatorId,
      result.year,
    )?.comparisonReference
    invariant(
      [
        PNE_2026_RELATIONSHIP_MODES.PROGRESS,
        PNE_2026_RELATIONSHIP_MODES.TRACKING,
      ].includes(relation.mode)
        && reference
        && result.resolvedReferenceId === reference.referenceId,
      `${path}.resolvedReferenceId não autorizado.`,
    )
  }
  for (const field of ['distance', 'remainingGap', 'favorableDifference']) {
    if (!Object.hasOwn(result, field)) continue
    invariant(relation.canDistance === true, `${path}.${field} não autorizado.`)
    invariant(Number.isFinite(result[field]), `${path}.${field} deve ser finito.`)
  }
  for (const field of ['status', 'classification']) {
    if (Object.hasOwn(result, field)) {
      invariant(relation.canStatus === true, `${path}.${field} não autorizado.`)
    }
  }
  if (Object.hasOwn(result, 'classification')) {
    invariant(
      relation.mode === PNE_2026_RELATIONSHIP_MODES.PROGRESS
        && ['advance', 'maintain', null].includes(result.classification),
      `${path}.classification inválida.`,
    )
  }
  if (
    relation.mode === PNE_2026_RELATIONSHIP_MODES.TRACKING
    && result.dataStatus === 'available'
  ) {
    invariant(
      Object.hasOwn(result, 'resolvedReferenceId')
        && Object.hasOwn(result, 'distance')
        && Object.hasOwn(result, 'status')
        && !Object.hasOwn(result, 'classification')
        && !Object.hasOwn(result, 'trend')
        && !Object.hasOwn(result, 'projection'),
      `${path} não contém a comparação municipal canônica.`,
    )
  }
  if (Object.hasOwn(result, 'trend') || Object.hasOwn(result, 'projection')) {
    invariant(relation.canProjection === true, `${path} contém projeção não autorizada.`)
  }
  if (['stateComparison', 'statewidePosition', 'similarMunicipalityComparison']
    .some((field) => Object.hasOwn(result, field))) {
    invariant(
      relation.stateReferencePolicy !== 'none',
      `${path} contém comparação estadual não autorizada.`,
    )
  }
  if (relation.mode === PNE_2026_RELATIONSHIP_MODES.COMPLEMENTARY) {
    const forbidden = [
      'resolvedReferenceId',
      'distance',
      'remainingGap',
      'favorableDifference',
      'status',
      'classification',
      'trend',
      'projection',
    ].filter((field) => Object.hasOwn(result, field))
    invariant(
      !forbidden.length,
      `${path} complementar contém campos classificatórios: ${forbidden.join(', ')}.`,
    )
  }
  for (const [field, allowed] of NESTED_RESULT_FIELDS) {
    if (Object.hasOwn(result, field)) {
      validateExactFields(result[field], allowed, `${path}.${field}`, new Set())
    }
  }
}

export function parsePne2026PublicDiagnosticV3(candidate) {
  validateExactFields(candidate, TOP_LEVEL_FIELDS, '$')
  invariant(
    candidate.schemaVersion === PNE_2026_PUBLIC_DIAGNOSTIC_V3_SCHEMA,
    'schemaVersion divergente.',
  )
  invariant(
    candidate.contractVersion === PNE_2026_CONTRACT_VERSION
      && candidate.contractVersion === '1.9.0',
    'contractVersion divergente.',
  )
  invariant(candidate.contractHash === PNE_2026_CONTRACT_HASH, 'contractHash divergente.')
  invariant(
    candidate.presentationPolicyVersion === presentationPolicy.policyVersion
      && candidate.presentationPolicyVersion === '1.7.0',
    'presentationPolicyVersion divergente.',
  )
  invariant(
    candidate.presentationPolicyHash === PNE_2026_PRESENTATION_POLICY_HASH,
    'presentationPolicyHash divergente.',
  )
  validateExactFields(candidate.municipality, MUNICIPALITY_FIELDS, '$.municipality')
  invariant(
    typeof candidate.municipality.id === 'string'
      && /^\d+$/.test(candidate.municipality.id),
    '$.municipality.id inválido.',
  )
  invariant(
    typeof candidate.municipality.name === 'string'
      && candidate.municipality.name.trim(),
    '$.municipality.name inválido.',
  )
  invariant(Array.isArray(candidate.results), '$.results deve ser lista.')
  const seen = new Set()
  candidate.results.forEach((result, index) => validateResult(result, index, seen))

  validateExactFields(candidate.summary, SUMMARY_FIELDS, '$.summary')
  validateExactFields(
    candidate.summary.classificationCounts,
    CLASSIFICATION_COUNT_FIELDS,
    '$.summary.classificationCounts',
  )
  validateExactFields(
    candidate.summary.presentationPriorityCounts,
    PRIORITY_COUNT_FIELDS,
    '$.summary.presentationPriorityCounts',
  )
  validateExactFields(
    candidate.summary.dataStatusCounts,
    DATA_STATUS_COUNT_FIELDS,
    '$.summary.dataStatusCounts',
  )
  invariant(
    JSON.stringify(canonicalJson(candidate.summary))
      === JSON.stringify(canonicalJson(buildCanonicalSummary(candidate.results))),
    '$.summary diverge da lista final de resultados.',
  )
  validateFiniteTree(candidate)
  return structuredClone(candidate)
}

function buildIndicatorReference(result, relation) {
  if (!result.resolvedReferenceId) return null
  const context = getPne2026RelationContext(
    relation.goalId,
    relation.indicatorId,
    result.year,
  )
  const reference = relation.referenceKind === 'monitoring'
    ? context?.comparisonReference
    : context?.legalReference
  const milestone = reference?.milestone ?? (
    Number.isFinite(reference?.value)
      ? {
          value: reference.value,
          direction: reference.direction,
          unit: reference.unit,
        }
      : null
  )
  invariant(
    reference?.referenceId === result.resolvedReferenceId && milestone,
    `referência ${result.resolvedReferenceId} não pode ser resolvida.`,
  )
  return {
    value: milestone.value,
    direction: milestone.direction,
    ...(Number.isFinite(milestone.year) ? { year: milestone.year } : {}),
    label: relation.referenceKind === 'monitoring'
      ? 'Referência de acompanhamento'
      : getPne2026ReferenceLabel(relation.relationId, milestone.year),
    kind: relation.referenceKind === 'monitoring'
      ? 'municipal_monitoring_reference'
      : 'official_law_reference',
    validationStatus: reference.validationStatus,
  }
}

function adaptResult(result) {
  const relation = relationsById.get(result.relationId)
  const indicator = PNE_2026_GOAL_INDICATOR_CONTRACT.indicators[result.indicatorId]
  const trajectory = {
    ...(result.trend ?? {}),
    ...(result.projection ?? {}),
  }
  const isAvailable = result.dataStatus === 'available'
  return {
    relationId: result.relationId,
    goalId: result.goalId,
    indicatorId: result.indicatorId,
    current: {
      value: isAvailable ? result.value : null,
      displayValue: isAvailable ? result.value : null,
      displayText: isAvailable
        ? formatPublicValue(result.value, indicator.unit)
        : getPne2026DataStatusLabel(result.dataStatus, result.reasonCode),
      year: isAvailable ? result.year : null,
      unit: indicator.unit,
      numerator: isAvailable ? result.numeratorValue ?? null : null,
      denominator: isAvailable ? result.denominatorValue ?? null : null,
    },
    dataStatus: result.dataStatus,
    reasonCode: result.reasonCode ?? null,
    dataStatusLabel: getPne2026DataStatusLabel(result.dataStatus, result.reasonCode),
    indicatorReference: buildIndicatorReference(result, relation),
    classification: Object.hasOwn(result, 'classification')
      ? result.classification
      : null,
    status: result.status ?? null,
    distance: result.distance ?? null,
    remainingGap: result.remainingGap ?? null,
    favorableDifference: result.favorableDifference ?? null,
    numeratorField: result.numeratorField ?? null,
    numeratorValue: result.numeratorValue ?? null,
    denominatorField: result.denominatorField ?? null,
    denominatorValue: result.denominatorValue ?? null,
    publicReading: result.publicReading ?? null,
    stateComparison: result.stateComparison,
    statewidePosition: result.statewidePosition,
    similarMunicipalities: result.similarMunicipalityComparison,
    ...(Object.keys(trajectory).length ? { trajectory } : {}),
  }
}

export function getPne2026DataStatusLabel(dataStatus, reasonCode) {
  if (
    dataStatus === 'unavailable'
    && reasonCode === 'below_minimum_participation'
  ) return 'Participação abaixo do mínimo para divulgação'
  if (
    dataStatus === 'unavailable'
    && ['no_published_result', 'source_record_absent'].includes(reasonCode)
  ) return 'Resultado não publicado pela fonte'
  if (
    dataStatus === 'unavailable'
    && reasonCode === 'no_post_baseline_observation'
  ) return 'Sem resultado comparável após 2025'
  if (dataStatus === 'unavailable') return 'Não disponível para o período'
  if (dataStatus === 'not_applicable') return 'Não se aplica ao município'
  if (dataStatus === 'suppressed') return 'Dado suprimido pela fonte'
  return null
}

export function adaptPne2026PublicDiagnosticV3ToResolverInput(candidate) {
  const payload = parsePne2026PublicDiagnosticV3(candidate)
  const resultsByGoal = new Map()
  for (const result of payload.results) {
    const current = resultsByGoal.get(result.goalId) ?? []
    current.push(adaptResult(result))
    resultsByGoal.set(result.goalId, current)
  }
  const usedSourceIds = new Set(
    payload.results.flatMap((result) => (
      PNE_2026_GOAL_INDICATOR_CONTRACT.indicators[result.indicatorId]?.sourceIds ?? []
    )),
  )
  const sources = [...usedSourceIds].sort().flatMap((sourceId) => {
    const source = PNE_2026_GOAL_INDICATOR_CONTRACT.sources[sourceId]
    if (!source) return []
    return [{
      id: source.sourceId,
      organization: source.organization,
      publicTitle: source.publicTitle,
      ...(SOURCE_PERIODS[sourceId] ? { period: SOURCE_PERIODS[sourceId] } : {}),
      officialUrl: source.officialUrl,
    }]
  })
  return {
    municipalityId: payload.municipality.id,
    municipalityName: payload.municipality.name,
    goals: [...resultsByGoal].map(([goalId, results], index) => ({
      goalId,
      order: index + 1,
      results,
    })),
    sources,
  }
}

export function resolvePne2026PublicDiagnosticV3(candidate) {
  return resolvePne2026DiagnosticViewModel(
    adaptPne2026PublicDiagnosticV3ToResolverInput(candidate),
  )
}
