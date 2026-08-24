/*
 * Leitura da Matriz de Prioridades publicada em `public/data/pne2026-matriz/`.
 *
 * O manifesto é a única porta de entrada. O documento municipal só é aceito
 * depois de validar o esquema fechado e de reconciliar identidade, data e
 * grupo de pares com a entrada do manifesto. Toda falha vira erro estruturado.
 */

export const PNE_2026_MATRIZ_MANIFEST_PATH = '/data/pne2026-matriz/manifest.json'
export const PNE_2026_MATRIZ_MUNICIPAL_PATH = '/data/pne2026-matriz/municipios/{municipalityId}.json'

export const PNE_2026_MATRIZ_SCHEMA_V3 = 'matriz-3.0.0'
export const PNE_2026_MATRIZ_SCHEMA_V4 = 'matriz-4.0.0'
export const PNE_2026_MATRIZ_SCHEMA = PNE_2026_MATRIZ_SCHEMA_V3
export const PNE_2026_MATRIZ_SCHEMAS = Object.freeze([
  PNE_2026_MATRIZ_SCHEMA_V3,
  PNE_2026_MATRIZ_SCHEMA_V4,
])
export const PNE_2026_MATRIZ_MANIFEST_SCHEMA = 'pne2026-matriz-manifest-v3'
export const PNE_2026_MATRIZ_SOURCE_MANIFEST_SCHEMA_V3 = 'matriz-manifest-3.0.0'
export const PNE_2026_MATRIZ_SOURCE_MANIFEST_SCHEMA_V4 = 'matriz-manifest-4.0.0'
export const PNE_2026_MATRIZ_SOURCE_MANIFEST_SCHEMA = PNE_2026_MATRIZ_SOURCE_MANIFEST_SCHEMA_V3
export const PNE_2026_MATRIZ_SOURCE_MANIFEST_SCHEMAS = Object.freeze([
  PNE_2026_MATRIZ_SOURCE_MANIFEST_SCHEMA_V3,
  PNE_2026_MATRIZ_SOURCE_MANIFEST_SCHEMA_V4,
])
export const PNE_2026_MATRIZ_MUNICIPAL_FILE_PATTERN = 'municipios/{municipalityId}.json'

export const MATRIZ_DISTANCE_TO_TARGET = Object.freeze([
  'far_from_target',
  'below_target',
  'near_or_at_target',
])
export const MATRIZ_PEER_DEVIATIONS = Object.freeze([
  'much_worse_than_peers',
  'worse_than_peers',
  'in_line_with_peers',
  'better_than_peers',
])
export const MATRIZ_GOVERNABILITY = Object.freeze(['municipal', 'shared'])
export const MATRIZ_OTHER_CAUSE_REASONS = Object.freeze([
  'weak_signal_only',
  'no_eligible_anchor',
  'over_card_cap',
])
export const MATRIZ_PROOF_STATUSES = Object.freeze([
  'adverse_local_signal',
  'no_adverse_local_signal',
])
export const MATRIZ_PROOF_MAX_INFERENCES = Object.freeze([
  'measured_value_within_source_scope',
  'known_cases_or_events_only',
  'contextual_association_only',
])
export const MATRIZ_TREND_DIRECTIONS = Object.freeze(['improved', 'worsened', 'stable'])
export const MATRIZ_NETWORK_CONCENTRATIONS = Object.freeze([
  'concentrated_in_few_schools',
  'spread_across_network',
])

const MANIFEST_FIELDS = new Set([
  'schemaVersion',
  'matrizSchemaVersion',
  'sourceManifestSchemaVersion',
  'generatorVersion',
  'municipalFilePattern',
  'municipalities',
])
const MANIFEST_ENTRY_FIELDS = new Set([
  'ibge7',
  'name',
  'uf',
  'referenceDate',
  'path',
  'inputSha256',
  'sourceManifestSha256',
  'outputSha256',
  'outputByteSize',
  'peerGroup',
])
const DOCUMENT_FIELDS = new Set([
  'schemaVersion',
  'municipality',
  'referenceDate',
  'sourceDiagnostic',
  'sourceWorkbook',
  'peerGroup',
  'curation',
  'priorityGoals',
  'goalsWithoutOwnCause',
  'outOfReach',
  'otherPossibleCauses',
  'summary',
])
const MUNICIPALITY_FIELDS = new Set(['ibge7', 'name', 'uf'])
const SOURCE_DIAGNOSTIC_FIELDS = new Set(['builderVersion', 'catalogSha256', 'diagnosticCsvSha256'])
const SOURCE_WORKBOOK_FIELDS = new Set(['schemaVersion', 'sha256'])
const PEER_GROUP_FIELDS = new Set(['criteria', 'band', 'n', 'populationPeriod', 'releaseId', 'expansions'])
const CURATION_FIELDS = new Set(['sha256', 'version'])
const SUMMARY_FIELDS = new Set(['goalsOnTrack', 'goalsWithoutData'])
const PRIORITY_GOAL_FIELDS = new Set([
  'goalId',
  'indicatorId',
  'title',
  'valueRaw',
  'referenceRaw',
  'unit',
  'year',
  'severity',
  'causes',
])
const PRIORITY_GOAL_V4_OPTIONAL_FIELDS = new Set(['trend', 'networkConcentration'])
const GOAL_WITHOUT_OWN_CAUSE_FIELDS = new Set([
  'goalId',
  'title',
  'valueRaw',
  'referenceRaw',
  'severity',
  'causesShownIn',
])
const CAUSE_FIELDS = new Set([
  'factorId',
  'name',
  'governability',
  'proofStatus',
  'proof',
  'firstStep',
  'workshopQuestions',
  'collapsed',
])
const SEVERITY_FIELDS = new Set([
  'level',
  'distanceToTarget',
  'peerDeviation',
  'peerN',
  'peerBenchmark',
  'placementRationale',
])
const PEER_BENCHMARK_FIELDS = new Set([
  'statistic',
  'valueRaw',
  'differenceRaw',
  'unit',
  'year',
  'n',
])
const PROOF_FIELDS = new Set([
  'measureId',
  'valueRaw',
  'unit',
  'period',
  'maxInference',
  'caution',
  'dimensions',
])
const PROOF_V4_OPTIONAL_FIELDS = new Set(['peerBenchmark'])
const FIRST_STEP_FIELDS = new Set(['kind', 'text', 'ref'])
const COLLAPSED_FIELDS = new Set([
  'signals',
  'mechanism',
  'expectedRelationship',
  'howToConfirmLocally',
])
const SIGNAL_FIELDS = new Set([
  'caution',
  'dimensions',
  'direction',
  'maxInference',
  'measureId',
  'observability',
  'period',
  'stance',
  'unit',
  'valueRaw',
])
const SIGNAL_V4_OPTIONAL_FIELDS = new Set(['peerBenchmark'])
const TREND_FIELDS = new Set(['previousValueRaw', 'previousYear', 'direction'])
const NETWORK_CONCENTRATION_FIELDS = new Set([
  'measureId',
  'classification',
  'affectedSchools',
  'totalSchools',
])
const OUT_OF_REACH_FIELDS = new Set(['factorId', 'name', 'reason'])
const OTHER_CAUSE_FIELDS = new Set(['factorId', 'name', 'goalId', 'reason'])

const SHA256_PATTERN = /^[a-f0-9]{64}$/
const IBGE7_PATTERN = /^\d{7}$/
const ISO_DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/
const RELATION_GOAL_ID_PATTERN = /^\d+\.[a-z]$/

function invariant(condition, message) {
  if (!condition) throw new TypeError(`Matriz de Prioridades inválida: ${message}`)
}

function isObject(value) {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value)
}

function validateExactFields(candidate, expected, label) {
  validateFields(candidate, expected, new Set(), label)
}

function validateFields(candidate, required, optional, label) {
  invariant(isObject(candidate), `${label} deve ser objeto.`)
  const unknown = Object.keys(candidate).filter((field) => !required.has(field) && !optional.has(field))
  const missing = [...required].filter((field) => !Object.hasOwn(candidate, field))
  invariant(!unknown.length, `${label} contém campos desconhecidos: ${unknown.join(', ')}.`)
  invariant(!missing.length, `${label} não contém: ${missing.join(', ')}.`)
}

function validateTextFields(candidate, fields, label) {
  for (const field of fields) {
    invariant(typeof candidate[field] === 'string', `${label}.${field} deve ser texto.`)
  }
}

function validateNonEmptyText(value, label) {
  invariant(typeof value === 'string' && value.trim().length > 0, `${label} não pode ser vazio.`)
}

function validateTextList(candidate, label, { nonEmpty = false } = {}) {
  invariant(Array.isArray(candidate), `${label} deve ser lista.`)
  if (nonEmpty) invariant(candidate.length > 0, `${label} não pode ser vazia.`)
  candidate.forEach((item, index) => {
    invariant(typeof item === 'string', `${label}[${index}] deve ser texto.`)
  })
}

function validateRawNumber(value, label) {
  validateNonEmptyText(value, label)
  invariant(Number.isFinite(Number(value)), `${label} deve conter número finito.`)
}

function validateSha256(value, label) {
  invariant(typeof value === 'string' && SHA256_PATTERN.test(value), `${label} deve ser sha256.`)
}

function validatePeerGroup(candidate, label) {
  validateExactFields(candidate, PEER_GROUP_FIELDS, label)
  validateTextFields(candidate, ['criteria', 'band', 'populationPeriod', 'releaseId'], label)
  validateNonEmptyText(candidate.criteria, `${label}.criteria`)
  validateNonEmptyText(candidate.band, `${label}.band`)
  invariant(Number.isInteger(candidate.n) && candidate.n >= 20, `${label}.n deve ser inteiro maior ou igual a 20.`)
  validateSha256(candidate.releaseId, `${label}.releaseId`)
  validateTextList(candidate.expansions, `${label}.expansions`)
}

function samePeerGroup(left, right) {
  return left.criteria === right.criteria
    && left.band === right.band
    && left.n === right.n
    && left.populationPeriod === right.populationPeriod
    && left.releaseId === right.releaseId
    && left.expansions.length === right.expansions.length
    && left.expansions.every((item, index) => item === right.expansions[index])
}

function validatePeerBenchmark(candidate, subject, label, { expectedN = null } = {}) {
  if (candidate === null) return
  validateExactFields(candidate, PEER_BENCHMARK_FIELDS, label)
  validateTextFields(candidate, ['statistic', 'valueRaw', 'differenceRaw', 'unit', 'year'], label)
  invariant(candidate.statistic === 'median', `${label}.statistic fora do vocabulário.`)
  validateRawNumber(candidate.valueRaw, `${label}.valueRaw`)
  validateRawNumber(candidate.differenceRaw, `${label}.differenceRaw`)
  validateNonEmptyText(candidate.unit, `${label}.unit`)
  invariant(/^\d{4}$/.test(candidate.year), `${label}.year inválido.`)
  invariant(Number.isInteger(candidate.n) && candidate.n >= 20, `${label}.n deve ser inteiro maior ou igual a 20.`)
  if (expectedN !== null) {
    invariant(candidate.n === expectedN, `${label}.n deve coincidir com peerN.`)
  }
  if (Object.hasOwn(subject, 'unit')) {
    invariant(candidate.unit === subject.unit, `${label}.unit diverge do indicador.`)
  }
  if (Object.hasOwn(subject, 'year')) {
    invariant(candidate.year === subject.year, `${label}.year diverge do indicador.`)
  }
  const expectedDifference = Number(subject.valueRaw) - Number(candidate.valueRaw)
  invariant(
    Math.abs(Number(candidate.differenceRaw) - expectedDifference) <= 1e-9,
    `${label}.differenceRaw diverge de valor municipal menos mediana.`,
  )
}

function validateSignalPeerBenchmark(signal, label) {
  if (!Object.hasOwn(signal, 'peerBenchmark')) return
  invariant(signal.peerBenchmark !== null, `${label}.peerBenchmark deve ser objeto quando presente.`)
  validateRawNumber(signal.valueRaw, `${label}.valueRaw`)
  invariant(/^\d{4}$/.test(signal.period), `${label}.peerBenchmark não é permitido para período em intervalo.`)
  validatePeerBenchmark(signal.peerBenchmark, {
    unit: signal.unit,
    valueRaw: signal.valueRaw,
    year: signal.period,
  }, `${label}.peerBenchmark`)
}

function validateSignal(signal, label, schemaVersion) {
  validateFields(
    signal,
    SIGNAL_FIELDS,
    schemaVersion === PNE_2026_MATRIZ_SCHEMA_V4 ? SIGNAL_V4_OPTIONAL_FIELDS : new Set(),
    label,
  )
  validateTextFields(signal, SIGNAL_FIELDS, label)
  validateSignalPeerBenchmark(signal, label)
}

function validateSeverity(severity, goal, label) {
  validateExactFields(severity, SEVERITY_FIELDS, label)
  validateTextFields(
    severity,
    ['level', 'distanceToTarget', 'peerDeviation', 'placementRationale'],
    label,
  )
  invariant(['high', 'medium'].includes(severity.level), `${label}.level fora do vocabulário.`)
  invariant(
    MATRIZ_DISTANCE_TO_TARGET.includes(severity.distanceToTarget),
    `${label}.distanceToTarget fora do vocabulário.`,
  )
  invariant(
    MATRIZ_PEER_DEVIATIONS.includes(severity.peerDeviation),
    `${label}.peerDeviation fora do vocabulário.`,
  )
  invariant(Number.isInteger(severity.peerN) && severity.peerN >= 20, `${label}.peerN deve ser inteiro maior ou igual a 20.`)
  validatePeerBenchmark(severity.peerBenchmark, goal, `${label}.peerBenchmark`, {
    expectedN: severity.peerN,
  })
  validateNonEmptyText(severity.placementRationale, `${label}.placementRationale`)
}

function validateCause(cause, label, schemaVersion) {
  validateExactFields(cause, CAUSE_FIELDS, label)
  validateTextFields(cause, ['factorId', 'name', 'governability', 'proofStatus'], label)
  validateNonEmptyText(cause.factorId, `${label}.factorId`)
  validateNonEmptyText(cause.name, `${label}.name`)
  invariant(MATRIZ_GOVERNABILITY.includes(cause.governability), `${label}.governability fora do vocabulário.`)
  invariant(MATRIZ_PROOF_STATUSES.includes(cause.proofStatus), `${label}.proofStatus fora do vocabulário.`)

  if (cause.proofStatus === 'no_adverse_local_signal') {
    invariant(cause.proof === null, `${label}.proof deve ser null quando não há sinal local adverso.`)
  } else {
    validateFields(
      cause.proof,
      PROOF_FIELDS,
      schemaVersion === PNE_2026_MATRIZ_SCHEMA_V4 ? PROOF_V4_OPTIONAL_FIELDS : new Set(),
      `${label}.proof`,
    )
    validateTextFields(cause.proof, PROOF_FIELDS, `${label}.proof`)
    validateRawNumber(cause.proof.valueRaw, `${label}.proof.valueRaw`)
    invariant(
      MATRIZ_PROOF_MAX_INFERENCES.includes(cause.proof.maxInference),
      `${label}.proof.maxInference fora do vocabulário.`,
    )
    validateSignalPeerBenchmark(cause.proof, `${label}.proof`)
  }
  invariant(
    (cause.proof === null) === (cause.proofStatus === 'no_adverse_local_signal'),
    `${label}.proofStatus diverge de proof.`,
  )

  validateExactFields(cause.firstStep, FIRST_STEP_FIELDS, `${label}.firstStep`)
  validateTextFields(cause.firstStep, FIRST_STEP_FIELDS, `${label}.firstStep`)
  invariant(['local_check', 'federal_instrument'].includes(cause.firstStep.kind), `${label}.firstStep.kind fora do vocabulário.`)
  invariant(cause.firstStep.ref === cause.factorId, `${label}.firstStep.ref deve apontar para factorId.`)
  if (cause.firstStep.kind === 'local_check') {
    validateNonEmptyText(cause.firstStep.text, `${label}.firstStep.text`)
  }

  validateTextList(cause.workshopQuestions, `${label}.workshopQuestions`)
  validateExactFields(cause.collapsed, COLLAPSED_FIELDS, `${label}.collapsed`)
  validateTextFields(cause.collapsed, ['mechanism', 'expectedRelationship'], `${label}.collapsed`)
  validateTextList(cause.collapsed.howToConfirmLocally, `${label}.collapsed.howToConfirmLocally`)
  invariant(Array.isArray(cause.collapsed.signals), `${label}.collapsed.signals deve ser lista.`)
  cause.collapsed.signals.forEach((signal, index) => (
    validateSignal(signal, `${label}.collapsed.signals[${index}]`, schemaVersion)
  ))
}

function validateTrend(trend, goal, label) {
  validateExactFields(trend, TREND_FIELDS, label)
  validateTextFields(trend, TREND_FIELDS, label)
  validateRawNumber(trend.previousValueRaw, `${label}.previousValueRaw`)
  invariant(/^\d{4}$/.test(trend.previousYear), `${label}.previousYear inválido.`)
  invariant(trend.previousYear < goal.year, `${label}.previousYear deve ser anterior ao ano da meta.`)
  invariant(MATRIZ_TREND_DIRECTIONS.includes(trend.direction), `${label}.direction fora do vocabulário.`)
}

function validateNetworkConcentration(concentration, measureIds, label) {
  validateExactFields(concentration, NETWORK_CONCENTRATION_FIELDS, label)
  validateTextFields(concentration, ['measureId', 'classification'], label)
  validateNonEmptyText(concentration.measureId, `${label}.measureId`)
  invariant(
    MATRIZ_NETWORK_CONCENTRATIONS.includes(concentration.classification),
    `${label}.classification fora do vocabulário.`,
  )
  invariant(
    Number.isInteger(concentration.affectedSchools) && concentration.affectedSchools >= 0,
    `${label}.affectedSchools deve ser inteiro maior ou igual a zero.`,
  )
  invariant(
    Number.isInteger(concentration.totalSchools) && concentration.totalSchools >= 1,
    `${label}.totalSchools deve ser inteiro maior ou igual a um.`,
  )
  invariant(
    concentration.affectedSchools <= concentration.totalSchools,
    `${label}.affectedSchools não pode superar totalSchools.`,
  )
  invariant(
    measureIds.has(concentration.measureId),
    `${label}.measureId não existe entre os sinais da mesma meta.`,
  )
}

function validatePriorityGoal(goal, label, schemaVersion) {
  validateFields(
    goal,
    PRIORITY_GOAL_FIELDS,
    schemaVersion === PNE_2026_MATRIZ_SCHEMA_V4 ? PRIORITY_GOAL_V4_OPTIONAL_FIELDS : new Set(),
    label,
  )
  validateTextFields(goal, ['goalId', 'indicatorId', 'title', 'valueRaw', 'referenceRaw', 'unit', 'year'], label)
  invariant(RELATION_GOAL_ID_PATTERN.test(goal.goalId), `${label}.goalId inválido.`)
  validateNonEmptyText(goal.indicatorId, `${label}.indicatorId`)
  validateNonEmptyText(goal.title, `${label}.title`)
  validateRawNumber(goal.valueRaw, `${label}.valueRaw`)
  validateRawNumber(goal.referenceRaw, `${label}.referenceRaw`)
  validateNonEmptyText(goal.unit, `${label}.unit`)
  invariant(/^\d{4}$/.test(goal.year), `${label}.year inválido.`)
  if (Object.hasOwn(goal, 'trend')) validateTrend(goal.trend, goal, `${label}.trend`)
  validateSeverity(goal.severity, goal, `${label}.severity`)
  invariant(Array.isArray(goal.causes) && goal.causes.length > 0, `${label}.causes não pode ser vazia.`)
  invariant(goal.causes.length <= 3, `${label}.causes não pode ter mais de três causas.`)
  goal.causes.forEach((cause, index) => validateCause(cause, `${label}.causes[${index}]`, schemaVersion))
  if (Object.hasOwn(goal, 'networkConcentration')) {
    const measureIds = new Set(goal.causes.flatMap((cause) => [
      ...(cause.proof ? [cause.proof.measureId] : []),
      ...cause.collapsed.signals.map((signal) => signal.measureId),
    ]))
    validateNetworkConcentration(goal.networkConcentration, measureIds, `${label}.networkConcentration`)
  }
}

function validateGoalWithoutOwnCause(goal, label) {
  validateExactFields(goal, GOAL_WITHOUT_OWN_CAUSE_FIELDS, label)
  validateTextFields(goal, ['goalId', 'title', 'valueRaw', 'referenceRaw'], label)
  invariant(RELATION_GOAL_ID_PATTERN.test(goal.goalId), `${label}.goalId inválido.`)
  validateNonEmptyText(goal.title, `${label}.title`)
  validateRawNumber(goal.valueRaw, `${label}.valueRaw`)
  validateRawNumber(goal.referenceRaw, `${label}.referenceRaw`)
  validateSeverity(goal.severity, goal, `${label}.severity`)
  validateTextList(goal.causesShownIn, `${label}.causesShownIn`)
  invariant(new Set(goal.causesShownIn).size === goal.causesShownIn.length, `${label}.causesShownIn contém repetição.`)
}

export function parsePne2026MatrizManifest(candidate) {
  validateExactFields(candidate, MANIFEST_FIELDS, 'manifest.json')
  invariant(candidate.schemaVersion === PNE_2026_MATRIZ_MANIFEST_SCHEMA, 'schema do manifesto divergente.')
  invariant(PNE_2026_MATRIZ_SCHEMAS.includes(candidate.matrizSchemaVersion), 'matrizSchemaVersion divergente.')
  invariant(
    PNE_2026_MATRIZ_SOURCE_MANIFEST_SCHEMAS.includes(candidate.sourceManifestSchemaVersion),
    'sourceManifestSchemaVersion divergente.',
  )
  invariant(
    candidate.municipalFilePattern === PNE_2026_MATRIZ_MUNICIPAL_FILE_PATTERN,
    'municipalFilePattern divergente.',
  )
  validateTextFields(candidate, ['generatorVersion'], 'manifest.json')
  invariant(Array.isArray(candidate.municipalities), 'manifest.json.municipalities deve ser lista.')

  const seen = new Set()
  for (const entry of candidate.municipalities) {
    validateExactFields(entry, MANIFEST_ENTRY_FIELDS, 'manifest.json.municipalities[]')
    validateTextFields(
      entry,
      ['ibge7', 'name', 'uf', 'referenceDate', 'path', 'inputSha256', 'sourceManifestSha256', 'outputSha256'],
      'manifest.json.municipalities[]',
    )
    invariant(IBGE7_PATTERN.test(entry.ibge7), `código municipal inválido no manifesto: ${entry.ibge7}.`)
    invariant(!seen.has(entry.ibge7), `município duplicado no manifesto: ${entry.ibge7}.`)
    seen.add(entry.ibge7)
    invariant(/^[A-Z]{2}$/.test(entry.uf), `UF inválida em ${entry.ibge7}.`)
    invariant(ISO_DATE_PATTERN.test(entry.referenceDate), `referenceDate inválida em ${entry.ibge7}.`)
    for (const field of ['inputSha256', 'sourceManifestSha256', 'outputSha256']) {
      validateSha256(entry[field], `manifest.json.municipalities[].${field}`)
    }
    invariant(
      entry.path === PNE_2026_MATRIZ_MUNICIPAL_FILE_PATTERN.replace('{municipalityId}', entry.ibge7),
      `caminho publicado fora do padrão em ${entry.ibge7}.`,
    )
    invariant(Number.isInteger(entry.outputByteSize) && entry.outputByteSize > 0, `outputByteSize inválido em ${entry.ibge7}.`)
    validatePeerGroup(entry.peerGroup, `manifest.json.municipalities[${entry.ibge7}].peerGroup`)
  }
  return structuredClone(candidate)
}

export function parsePne2026Matriz(candidate) {
  validateExactFields(candidate, DOCUMENT_FIELDS, 'matriz municipal')
  invariant(PNE_2026_MATRIZ_SCHEMAS.includes(candidate.schemaVersion), 'schema da matriz divergente.')
  invariant(ISO_DATE_PATTERN.test(candidate.referenceDate), 'referenceDate inválida.')

  validateExactFields(candidate.municipality, MUNICIPALITY_FIELDS, 'matriz.municipality')
  validateTextFields(candidate.municipality, MUNICIPALITY_FIELDS, 'matriz.municipality')
  invariant(IBGE7_PATTERN.test(candidate.municipality.ibge7), 'municipality.ibge7 inválido.')
  invariant(/^[A-Z]{2}$/.test(candidate.municipality.uf), 'municipality.uf inválida.')

  validateExactFields(candidate.sourceDiagnostic, SOURCE_DIAGNOSTIC_FIELDS, 'matriz.sourceDiagnostic')
  validateTextFields(candidate.sourceDiagnostic, SOURCE_DIAGNOSTIC_FIELDS, 'matriz.sourceDiagnostic')
  validateSha256(candidate.sourceDiagnostic.catalogSha256, 'matriz.sourceDiagnostic.catalogSha256')
  validateSha256(candidate.sourceDiagnostic.diagnosticCsvSha256, 'matriz.sourceDiagnostic.diagnosticCsvSha256')

  validateExactFields(candidate.sourceWorkbook, SOURCE_WORKBOOK_FIELDS, 'matriz.sourceWorkbook')
  validateTextFields(candidate.sourceWorkbook, SOURCE_WORKBOOK_FIELDS, 'matriz.sourceWorkbook')
  validateSha256(candidate.sourceWorkbook.sha256, 'matriz.sourceWorkbook.sha256')

  validatePeerGroup(candidate.peerGroup, 'matriz.peerGroup')
  validateExactFields(candidate.curation, CURATION_FIELDS, 'matriz.curation')
  validateTextFields(candidate.curation, CURATION_FIELDS, 'matriz.curation')
  validateSha256(candidate.curation.sha256, 'matriz.curation.sha256')

  invariant(Array.isArray(candidate.priorityGoals), 'matriz.priorityGoals deve ser lista.')
  const priorityGoalIds = new Set()
  const seenFactors = new Set()
  let causeCount = 0
  candidate.priorityGoals.forEach((goal, index) => {
    validatePriorityGoal(goal, `matriz.priorityGoals[${index}]`, candidate.schemaVersion)
    invariant(!priorityGoalIds.has(goal.goalId), `goalId repetido em priorityGoals: ${goal.goalId}.`)
    priorityGoalIds.add(goal.goalId)
    causeCount += goal.causes.length
    for (const cause of goal.causes) {
      invariant(!seenFactors.has(cause.factorId), `factorId repetido entre metas: ${cause.factorId}.`)
      seenFactors.add(cause.factorId)
    }
  })
  invariant(causeCount <= 10, 'matriz.priorityGoals não pode ter mais de dez causas no total.')

  invariant(Array.isArray(candidate.goalsWithoutOwnCause), 'matriz.goalsWithoutOwnCause deve ser lista.')
  const goalsWithoutOwnCauseIds = new Set()
  candidate.goalsWithoutOwnCause.forEach((goal, index) => {
    validateGoalWithoutOwnCause(goal, `matriz.goalsWithoutOwnCause[${index}]`)
    invariant(!priorityGoalIds.has(goal.goalId), `goalId aparece com e sem causa própria: ${goal.goalId}.`)
    invariant(!goalsWithoutOwnCauseIds.has(goal.goalId), `goalId repetido em goalsWithoutOwnCause: ${goal.goalId}.`)
    goalsWithoutOwnCauseIds.add(goal.goalId)
    goal.causesShownIn.forEach((goalId) => {
      invariant(priorityGoalIds.has(goalId), `causesShownIn aponta meta ausente de priorityGoals: ${goalId}.`)
    })
  })

  invariant(Array.isArray(candidate.outOfReach), 'matriz.outOfReach deve ser lista.')
  candidate.outOfReach.forEach((item, index) => {
    validateExactFields(item, OUT_OF_REACH_FIELDS, `matriz.outOfReach[${index}]`)
    validateTextFields(item, OUT_OF_REACH_FIELDS, `matriz.outOfReach[${index}]`)
    invariant(item.reason === 'external_governability', `matriz.outOfReach[${index}].reason fora do vocabulário.`)
  })

  invariant(Array.isArray(candidate.otherPossibleCauses), 'matriz.otherPossibleCauses deve ser lista.')
  candidate.otherPossibleCauses.forEach((item, index) => {
    validateExactFields(item, OTHER_CAUSE_FIELDS, `matriz.otherPossibleCauses[${index}]`)
    validateTextFields(item, OTHER_CAUSE_FIELDS, `matriz.otherPossibleCauses[${index}]`)
    invariant(MATRIZ_OTHER_CAUSE_REASONS.includes(item.reason), `matriz.otherPossibleCauses[${index}].reason fora do vocabulário.`)
  })

  validateExactFields(candidate.summary, SUMMARY_FIELDS, 'matriz.summary')
  validateTextList(candidate.summary.goalsOnTrack, 'matriz.summary.goalsOnTrack')
  validateTextList(candidate.summary.goalsWithoutData, 'matriz.summary.goalsWithoutData')

  return structuredClone(candidate)
}

async function defaultFetchJson(path, options) {
  const response = await fetch(path, options)
  if (!response.ok) throw new Error(`Falha ao carregar ${path}: HTTP ${response.status}.`)
  return response.json()
}

export class MatrizLoadError extends Error {
  constructor(message, { cause, code, municipalityId = null, path = null, stage }) {
    super(message, { cause })
    this.name = 'MatrizLoadError'
    this.code = code
    this.stage = stage
    this.municipalityId = municipalityId
    this.path = path
  }
}

function structuredError(error, details) {
  if (error instanceof MatrizLoadError) return error
  return new MatrizLoadError(
    error instanceof Error ? error.message : String(error),
    { ...details, cause: error },
  )
}

function memoized(cache, key, producer) {
  if (cache.has(key)) return cache.get(key)
  const pending = Promise.resolve().then(producer)
  cache.set(key, pending)
  pending.catch(() => {
    if (cache.get(key) === pending) cache.delete(key)
  })
  return pending
}

/**
 * @param {{
 *   fetchJson?: (path: any, options?: any) => Promise<any>,
 *   logger?: (...data: any[]) => void,
 * }} [options]
 */
export function createPne2026MatrizLoader({
  fetchJson = defaultFetchJson,
  logger = console.error,
} = {}) {
  const documentCache = new Map()
  const reportedErrors = new Set()
  let manifestPending = null

  function reportOnce(error) {
    const key = [error.code, error.stage, error.municipalityId, error.path, error.message].join(':')
    if (reportedErrors.has(key)) return
    reportedErrors.add(key)
    logger(error)
  }

  function loadManifest() {
    if (manifestPending) return manifestPending
    manifestPending = Promise.resolve()
      .then(() => fetchJson(PNE_2026_MATRIZ_MANIFEST_PATH, { cache: 'no-store' }))
      .catch((error) => {
        throw structuredError(error, {
          code: 'manifest_unavailable',
          path: PNE_2026_MATRIZ_MANIFEST_PATH,
          stage: 'manifest',
        })
      })
      .then((candidate) => {
        try {
          return parsePne2026MatrizManifest(candidate)
        } catch (error) {
          throw structuredError(error, {
            code: 'invalid_manifest',
            path: PNE_2026_MATRIZ_MANIFEST_PATH,
            stage: 'manifest',
          })
        }
      })
      .finally(() => {
        manifestPending = null
      })
    return manifestPending
  }

  async function loadDocument(municipalityId) {
    const manifest = await loadManifest()
    const entry = manifest.municipalities.find((municipality) => municipality.ibge7 === municipalityId)
    if (!entry) {
      throw new MatrizLoadError(
        `A Matriz de Prioridades ainda não foi publicada para ${municipalityId}.`,
        { code: 'municipality_not_published', municipalityId, stage: 'manifest' },
      )
    }
    const key = `${entry.outputSha256}:${municipalityId}`
    return memoized(documentCache, key, async () => {
      const path = PNE_2026_MATRIZ_MUNICIPAL_PATH.replace('{municipalityId}', municipalityId)
      let candidate
      try {
        candidate = await fetchJson(path)
      } catch (error) {
        throw structuredError(error, {
          code: 'municipality_unavailable',
          municipalityId,
          path,
          stage: 'municipality',
        })
      }
      try {
        const matriz = parsePne2026Matriz(candidate)
        invariant(
          matriz.schemaVersion === manifest.matrizSchemaVersion,
          `schema do documento municipal diverge do manifesto em ${municipalityId}.`,
        )
        invariant(matriz.municipality.ibge7 === municipalityId, `documento municipal divergente: ${municipalityId}.`)
        invariant(matriz.referenceDate === entry.referenceDate, `data de referência divergente do manifesto em ${municipalityId}.`)
        invariant(
          matriz.municipality.name === entry.name && matriz.municipality.uf === entry.uf,
          `identidade municipal divergente do manifesto em ${municipalityId}.`,
        )
        invariant(samePeerGroup(matriz.peerGroup, entry.peerGroup), `grupo de pares divergente do manifesto em ${municipalityId}.`)
        return { entry, matriz }
      } catch (error) {
        throw structuredError(error, {
          code: 'invalid_payload',
          municipalityId,
          path,
          stage: 'municipality',
        })
      }
    })
  }

  function load(municipalityId) {
    const normalizedId = String(municipalityId)
    if (!IBGE7_PATTERN.test(normalizedId)) {
      const error = new MatrizLoadError(`Código municipal inválido: ${normalizedId}.`, {
        code: 'invalid_municipality',
        municipalityId: normalizedId,
        stage: 'input',
      })
      reportOnce(error)
      return Promise.reject(error)
    }
    return loadDocument(normalizedId)
      .then(({ entry, matriz }) => ({
        schemaVersion: 'pne2026-matriz-loader-result-v3',
        municipalityId: normalizedId,
        municipalityName: matriz.municipality.name,
        referenceDate: matriz.referenceDate,
        outputSha256: entry.outputSha256,
        matriz,
      }))
      .catch((error) => {
        const structured = structuredError(error, {
          code: 'matriz_unavailable',
          municipalityId: normalizedId,
          stage: 'load',
        })
        if (structured.municipalityId === null) structured.municipalityId = normalizedId
        reportOnce(structured)
        throw structured
      })
  }

  return { load }
}
