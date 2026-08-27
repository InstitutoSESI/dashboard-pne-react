import assert from 'node:assert/strict'
import test from 'node:test'

import {
  AGENDA_THEME_LABELS,
  AGENDA_THEMES,
  AGGREGATION_LABELS,
  ASSOCIATIVE_GRAMMAR_VERSION,
  ASSOCIATIVE_METHOD_NOTE,
  DECOMPOSITION_CRITERIA,
  DECOMPOSITION_EMPLOYMENT_SOURCE_LABEL,
  DECOMPOSITION_FRAMING,
  DECOMPOSITION_STAGE_CONFIG,
  EDITORIAL_CRITERIA_STATEMENT,
  EDITORIAL_READING_CRITERIA,
  E2_EMPLOYMENT_METHOD_STATEMENT,
  E2_ENROLLMENT_METHOD_STATEMENT,
  EVIDENCE_CLASS_LABELS,
  PNE_SERIES_THEME_MAP,
  SCENARIO_FRAMING,
  SCREENED_ORIGIN_STATEMENT,
  SCREENED_RELATIONS_CRITERIA,
  SCREENING_EXCLUDED_SERIES_IDS,
  SYNTHESIS_FRAMING,
  SYNTHESIS_KIND_LABELS,
  VOCACOES_DOCUMENT_SCHEMA,
  computeComovement,
  computeDirectionConcordance,
  computePearsonDelta,
  computeSpearmanDelta,
  correlationStrength,
  createVocacoesDocumentParser,
  formatPublicNumber,
  renderComovementStatement,
  renderConcordanceStatement,
  renderContrastStatement,
  renderCorrelationStatement,
  renderEditorialNoteStatement,
  renderE2AbsenceStatement,
  renderE2EmploymentStatement,
  renderE2EnrollmentStatement,
  renderLaggedStatement,
  roundHalfAwayFromZero,
} from '../../src/features/vocacoes-regiao/vocacoesRegiaoContract.js'
import {
  CAUSAL_FLOOR,
  LOOSE_COEFFICIENT_FLOOR,
  TOKEN_FLOOR,
  assertNoPublicMetaNumber,
  createPublicLanguageGuard,
  scanPublicDocument,
} from '../lib/vocacoes-public-language.mjs'
import {
  ATAQUES,
  ATTACK_COUNT,
  HONESTOS,
  HONEST_COUNT,
} from './fixtures/vocacoes-associativo-corpus.mjs'

const SOURCE_VERSION = 'vocacoes-regiao-pesquisa-v0.6'
const PUBLICATION_SCOPE = 'estadual'
const REFERENCE_YEAR = 2025
const REFERENCE_MONTH = 12
const WINDOW = Object.freeze({ start: 2010, end: 2019 })
const LAG_YEARS = 6
const LAGGED_RATIONALE =
  'a coorte nascida em um ano atinge a idade de ingresso no ensino fundamental seis anos depois'
const EDUCATION_ID = 'matriculas-no-ensino-fundamental'
const MODERATE_ID = 'populacao-estimada'
const WEAK_ID = 'familias-inscritas-no-cadastro-social-posicao-de-dezembro'
const STRONG_CURATED_ID = 'vinculos-formais-de-pessoas-com-ensino-medio-completo'
const STRONG_SCREENED_ID = 'vinculos-formais-ativos'
const EDUCATION_DELTAS = Object.freeze([1, 2, 3, 4, 5, 6, 7, 8, 9, 1, 2, 3, 4, 5, 6])
const MODERATE_DELTAS = Object.freeze([4, 6, 3, 2, 5, 1, 7, 8, 9, 2, 4, 6, 8, 3, 5])
const WEAK_DELTAS = Object.freeze([7, 6, 3, 5, 2, 1, 4, 8, 9, 3, 1, 5, 2, 6, 4])

const languageGuard = createPublicLanguageGuard({
  causalLanguagePatterns: [...CAUSAL_FLOOR],
  causalConnectivePatterns: [],
  forbiddenPublicTokens: [...TOKEN_FLOOR],
  associativeReadingLayer: {
    looseCoefficientPatterns: [...LOOSE_COEFFICIENT_FLOOR],
    closedGrammarForbiddenPatterns: [],
  },
  cadastralSeriesForbiddenTerms: [],
  futureYearAssertionVerbs: [],
  futureYearNegationMarkers: [],
  futureYearNumberWords: [],
  spelledYearPrefixes: {},
  referenceYear: REFERENCE_YEAR,
})

const parseDocument = createVocacoesDocumentParser({
  sourceVersion: SOURCE_VERSION,
  publicationScope: PUBLICATION_SCOPE,
  referenceYear: REFERENCE_YEAR,
  referenceMonth: REFERENCE_MONTH,
})

function makeSeries({ seriesId, label, deltas }) {
  let value = 1_000
  const points = [{ period: 2010, value, evidenceClass: 'observed' }]
  deltas.forEach((delta, index) => {
    value += delta
    points.push({ period: 2011 + index, value, evidenceClass: 'observed' })
  })
  return {
    seriesId,
    label,
    unitLabel: 'unidades',
    sourceLabel: 'Fonte sintética determinística',
    evidenceClass: 'observed',
    evidenceLabel: EVIDENCE_CLASS_LABELS.observed,
    universeLabel: null,
    aggregationLabel: AGGREGATION_LABELS.sum,
    ratioOf: null,
    periodGranularity: 'annual',
    periodStart: 2010,
    periodEnd: 2025,
    periodLabel: '2010 a 2025',
    preliminaryPeriods: [],
    limitations: [],
    points,
  }
}

function makeBirthSeries() {
  const config = DECOMPOSITION_STAGE_CONFIG.ensino_fundamental
  const points = []
  for (let period = 1996; period <= 2019; period += 1) {
    points.push({ period, value: 100 + period - 1996, evidenceClass: 'observed' })
  }
  return {
    seriesId: config.cohortSeriesId,
    label: 'Nascidos vivos por residência da mãe',
    unitLabel: 'pessoas',
    sourceLabel: 'Fonte sintética determinística',
    evidenceClass: 'observed',
    evidenceLabel: EVIDENCE_CLASS_LABELS.observed,
    universeLabel: null,
    aggregationLabel: AGGREGATION_LABELS.sum,
    ratioOf: null,
    periodGranularity: 'annual',
    periodStart: 1996,
    periodEnd: 2019,
    periodLabel: '1996 a 2019',
    preliminaryPeriods: [],
    limitations: [],
    points,
  }
}

function decompositionCriteria() {
  return {
    cohortAges: Object.fromEntries(Object.entries(DECOMPOSITION_CRITERIA.cohortAges)
      .map(([stage, ages]) => [stage, [...ages]])),
    stagesWithoutCohort: [...DECOMPOSITION_CRITERIA.stagesWithoutCohort],
    minIntervals: DECOMPOSITION_CRITERIA.minIntervals,
    sectors: [...DECOMPOSITION_CRITERIA.sectors],
    reference: DECOMPOSITION_CRITERIA.reference,
    rounding: { ...DECOMPOSITION_CRITERIA.rounding },
    closureToleranceAbs: DECOMPOSITION_CRITERIA.closureToleranceAbs,
  }
}

function makeEnrollmentDecomposition(education, births) {
  const stage = 'ensino_fundamental'
  const config = DECOMPOSITION_STAGE_CONFIG[stage]
  const birthByPeriod = new Map(births.points.map((point) => [point.period, point.value]))
  const cohortAt = (period) => {
    let total = 0
    for (let age = config.cohortAges.min; age <= config.cohortAges.max; age += 1) {
      total += birthByPeriod.get(period - age)
    }
    return total
  }
  const first = education.points[0]
  const last = education.points[education.points.length - 1]
  const cohortStart = cohortAt(first.period)
  const cohortEnd = cohortAt(last.period)
  const ratioStart = first.value / cohortStart
  const ratioEnd = last.value / cohortEnd
  const totalPctRaw = 100 * (last.value - first.value) / first.value
  const demographicPpRaw = 100
    * (cohortEnd - cohortStart)
    * ((ratioStart + ratioEnd) / 2)
    / first.value
  const ratioPpRaw = 100
    * (ratioEnd - ratioStart)
    * ((cohortStart + cohortEnd) / 2)
    / first.value
  const decimals = DECOMPOSITION_CRITERIA.rounding.published
  const item = {
    stage,
    stageLabel: config.stageLabel,
    outcomeSeriesId: config.outcomeSeriesId,
    cohortSeriesId: config.cohortSeriesId,
    cohortAges: { ...config.cohortAges },
    window: {
      start: first.period,
      end: last.period,
      intervals: last.period - first.period,
    },
    terms: {
      enrollmentStart: first.value,
      enrollmentEnd: last.value,
      cohortStart,
      cohortEnd,
      ratioStartPerHundred: roundHalfAwayFromZero(ratioStart * 100, decimals),
      ratioEndPerHundred: roundHalfAwayFromZero(ratioEnd * 100, decimals),
    },
    contributions: {
      totalPct: roundHalfAwayFromZero(totalPctRaw, decimals),
      demographicPp: roundHalfAwayFromZero(demographicPpRaw, decimals),
      ratioPp: roundHalfAwayFromZero(ratioPpRaw, decimals),
    },
    grade: 'E2',
    pneThemes: pneThemesFor(config.outcomeSeriesId),
  }
  const absences = ['educacao_infantil', 'ensino_medio'].map((absenceStage) => {
    const absence = {
      stage: absenceStage,
      stageLabel: DECOMPOSITION_STAGE_CONFIG[absenceStage].stageLabel,
      reasonCode: 'serie_ausente',
    }
    return { ...absence, statement: renderE2AbsenceStatement(absence) }
  })
  return {
    methodStatement: E2_ENROLLMENT_METHOD_STATEMENT,
    criteria: decompositionCriteria(),
    items: [{ ...item, statement: renderE2EnrollmentStatement(item) }],
    absences,
  }
}

function makeEmploymentDecomposition() {
  const sectorCounts = [
    [100, 120, 1_000, 1_100],
    [200, 210, 2_000, 2_300],
    [50, 55, 500, 600],
    [300, 280, 3_000, 3_300],
    [350, 420, 3_500, 4_200],
  ]
  const sectors = DECOMPOSITION_CRITERIA.sectors.map((sectorLabel, index) => ({
    sectorLabel,
    regionStart: sectorCounts[index][0],
    regionEnd: sectorCounts[index][1],
    stateStart: sectorCounts[index][2],
    stateEnd: sectorCounts[index][3],
  }))
  const totals = Object.fromEntries(
    ['regionStart', 'regionEnd', 'stateStart', 'stateEnd'].map((field) => [
      field,
      sectors.reduce((sum, sector) => sum + sector[field], 0),
    ]),
  )
  const stateGrowth = (totals.stateEnd - totals.stateStart) / totals.stateStart
  const stateTerm = totals.regionStart * stateGrowth
  let mixTerm = 0
  let ownTerm = 0
  for (const sector of sectors) {
    const sectorStateGrowth = (sector.stateEnd - sector.stateStart) / sector.stateStart
    mixTerm += sector.regionStart * (sectorStateGrowth - stateGrowth)
    ownTerm += (sector.regionEnd - sector.regionStart) - sector.regionStart * sectorStateGrowth
  }
  const totalTerm = totals.regionEnd - totals.regionStart
  const decimals = DECOMPOSITION_CRITERIA.rounding.published
  const item = {
    window: { start: 2010, end: 2019, intervals: 9 },
    sectors,
    totals,
    excludedSectorLinks: { regionStart: 0, regionEnd: 0, stateStart: 0, stateEnd: 0 },
    contributions: {
      totalPct: roundHalfAwayFromZero(100 * totalTerm / totals.regionStart, decimals),
      statePp: roundHalfAwayFromZero(100 * stateTerm / totals.regionStart, decimals),
      mixPp: roundHalfAwayFromZero(100 * mixTerm / totals.regionStart, decimals),
      ownPp: roundHalfAwayFromZero(100 * ownTerm / totals.regionStart, decimals),
    },
    grade: 'E2',
    sourceLabel: DECOMPOSITION_EMPLOYMENT_SOURCE_LABEL,
  }
  return {
    methodStatement: E2_EMPLOYMENT_METHOD_STATEMENT,
    criteria: decompositionCriteria(),
    item: { ...item, statement: renderE2EmploymentStatement(item) },
    absence: null,
  }
}

function makeDecompositions(education, births) {
  return {
    ...DECOMPOSITION_FRAMING,
    enrollment: makeEnrollmentDecomposition(education, births),
    employment: makeEmploymentDecomposition(),
  }
}

function expectedSalience(seriesA, seriesB, window) {
  const pearson = computePearsonDelta(seriesA.points, seriesB.points, window)
  return pearson !== null
    && EDITORIAL_READING_CRITERIA.leadStrengths.includes(correlationStrength(Math.abs(pearson)))
    ? 'lead'
    : 'note'
}

function pneThemesFor(...seriesIds) {
  const resolved = new Set(seriesIds.flatMap((seriesId) => PNE_SERIES_THEME_MAP[seriesId] ?? []))
  return AGENDA_THEMES.filter((theme) => resolved.has(theme)).map((theme) => ({
    theme,
    themeLabel: AGENDA_THEME_LABELS[theme],
  }))
}

function makeCorrelation(seriesA, seriesB, window, { statement = true } = {}) {
  const pearsonRaw = computePearsonDelta(seriesA.points, seriesB.points, window)
  const spearmanRaw = computeSpearmanDelta(seriesA.points, seriesB.points, window)
  assert.notEqual(pearsonRaw, null)
  assert.notEqual(spearmanRaw, null)
  const directionConcordance = computeDirectionConcordance(seriesA.points, seriesB.points, window)
  assert.ok(!('reasonCode' in directionConcordance))
  const pearsonDelta = roundHalfAwayFromZero(pearsonRaw, 2)
  const correlation = {
    intervals: directionConcordance.intervals,
    pearsonDelta,
    spearmanDelta: roundHalfAwayFromZero(spearmanRaw, 2),
    strength: correlationStrength(Math.abs(pearsonRaw)),
    direction: pearsonRaw > 0 ? 'positiva' : pearsonRaw < 0 ? 'negativa' : 'nula',
  }
  if (statement) {
    correlation.statement = renderCorrelationStatement({
      windowStart: window.start,
      windowEnd: window.end,
      pearsonDelta: correlation.pearsonDelta,
      strength: correlation.strength,
      direction: correlation.direction,
    })
  }
  return correlation
}

function makeDirectionConcordance(seriesA, seriesB, window) {
  const computed = computeDirectionConcordance(seriesA.points, seriesB.points, window)
  assert.ok(!('reasonCode' in computed))
  return {
    ...computed,
    statement: renderConcordanceStatement({
      ...computed,
      labelA: seriesA.label,
      labelB: seriesB.label,
    }),
  }
}

function makeComovement(seriesA, seriesB, window, role) {
  const movementA = computeComovement(seriesA.points, window, 'nivel')
  const movementB = computeComovement(seriesB.points, window, 'nivel')
  assert.ok(!('reasonCode' in movementA))
  assert.ok(!('reasonCode' in movementB))
  const statement = renderComovementStatement({
    a: movementA,
    b: movementB,
    labelA: seriesA.label,
    labelB: seriesB.label,
  })
  const a = { seriesId: seriesA.seriesId, ...movementA }
  const b = { seriesId: seriesB.seriesId, ...movementB }
  return role === 'association'
    ? { outcome: a, factor: b, statement }
    : { a, b, statement }
}

function makeStateContrast(series, window) {
  const movement = computeComovement(series.points, window, 'nivel')
  assert.ok(!('reasonCode' in movement))
  const direction = movement.delta > 0 ? 'alta' : 'queda'
  const contrast = {
    seriesId: series.seriesId,
    statistic: 'variacao_percentual',
    value: roundHalfAwayFromZero(movement.delta / movement.valueStart * 100, 1),
    rank: 1,
    totalComparable: 2,
    sameDirectionCount: 2,
    direction,
  }
  return {
    ...contrast,
    statement: renderContrastStatement({
      ...contrast,
      label: series.label,
    }),
  }
}

function makeAssociationReading(seriesA, factors) {
  return {
    grammarVersion: ASSOCIATIVE_GRAMMAR_VERSION,
    methodNote: ASSOCIATIVE_METHOD_NOTE,
    factorReadings: factors.map((seriesB) => ({
      outcomeSeriesId: seriesA.seriesId,
      factorSeriesId: seriesB.seriesId,
      directionConcordance: makeDirectionConcordance(seriesA, seriesB, WINDOW),
      comovement: makeComovement(seriesA, seriesB, WINDOW, 'association'),
      correlation: makeCorrelation(seriesA, seriesB, WINDOW),
      salience: expectedSalience(seriesA, seriesB, WINDOW),
      grade: EDITORIAL_READING_CRITERIA.gradeEnum[0],
    })),
    stateContrast: makeStateContrast(seriesA, WINDOW),
  }
}

function makeTemporalReading(seriesA, seriesB) {
  return {
    grammarVersion: ASSOCIATIVE_GRAMMAR_VERSION,
    methodNote: ASSOCIATIVE_METHOD_NOTE,
    directionConcordance: makeDirectionConcordance(seriesA, seriesB, WINDOW),
    comovement: makeComovement(seriesA, seriesB, WINDOW, 'temporal'),
    correlation: makeCorrelation(seriesA, seriesB, WINDOW),
    stateContrast: makeStateContrast(seriesB, WINDOW),
    salience: expectedSalience(seriesA, seriesB, WINDOW),
    grade: EDITORIAL_READING_CRITERIA.gradeEnum[0],
  }
}

function makeLaggedReading(seriesA, seriesB) {
  const windowA = { start: 2010, end: 2019 }
  const windowB = { start: 2016, end: 2025 }
  const shiftedB = seriesB.points.map((point) => ({ ...point, period: point.period - LAG_YEARS }))
  const concordance = computeDirectionConcordance(seriesA.points, shiftedB, windowA)
  assert.ok(!('reasonCode' in concordance))
  const correlation = makeCorrelation(seriesA, { ...seriesB, points: shiftedB }, windowA, {
    statement: false,
  })
  const reading = {
    aSeriesId: seriesA.seriesId,
    bSeriesId: seriesB.seriesId,
    lagYears: LAG_YEARS,
    rationale: LAGGED_RATIONALE,
    windowA,
    windowB,
    intervals: concordance.intervals,
    concordant: concordance.concordant,
    opposite: concordance.opposite,
    ties: concordance.ties,
    correlation,
    salience: 'lead',
    grade: EDITORIAL_READING_CRITERIA.gradeEnum[0],
    pneThemes: pneThemesFor(seriesB.seriesId),
  }
  return {
    ...reading,
    statement: renderLaggedStatement({
      aSeriesLabel: seriesA.label,
      bSeriesLabel: seriesB.label,
      lagYears: reading.lagYears,
      rationale: reading.rationale,
      windowA,
      windowB,
      concordant: reading.concordant,
      intervals: reading.intervals,
      correlation,
    }),
  }
}

function observedSynthesisStatement(...series) {
  const clauses = series.map((serie) => {
    const start = serie.points.find((point) => point.period === WINDOW.start).value
    const end = serie.points.find((point) => point.period === WINDOW.end).value
    return `${serie.label} passou de ${formatPublicNumber(start)} para ${formatPublicNumber(end)}`
  })
  return `Conclui-se do observado que, entre ${WINDOW.start} e ${WINDOW.end}, ${clauses[0]} `
    + `e, no mesmo período, ${clauses.slice(1).join(' e ')}.`
}

function editorialRefId(reference) {
  if (reference.kind === 'structural') {
    return `${reference.kind}/${reference.aSeriesId}/${reference.bSeriesId}/${reference.lagYears}`
  }
  if (reference.kind === 'curated_association') {
    return `${reference.kind}/${reference.associationId}/${reference.factorSeriesId}`
  }
  if (reference.kind === 'curated_pair') return `${reference.kind}/${reference.pairId}`
  return `${reference.kind}/${reference.relationId}`
}

function makeEditorialReading({ association, temporalPair, lagged, screenedRelation, seriesById }) {
  const ranked = []
  let noteCount = 0
  const outcome = seriesById.get(association.educationOutcome.seriesId)
  for (const reading of association.associativeReading.factorReadings) {
    if (reading.salience === 'note') {
      noteCount += 1
      continue
    }
    const factor = seriesById.get(reading.factorSeriesId)
    const reference = {
      kind: 'curated_association',
      associationId: association.associationId,
      factorSeriesId: reading.factorSeriesId,
    }
    ranked.push({
      reference,
      absPearson: Math.abs(computePearsonDelta(outcome.points, factor.points, association.window)),
      refId: editorialRefId(reference),
    })
  }
  if (temporalPair.associativeReading.salience === 'note') {
    noteCount += 1
  } else {
    const reference = { kind: 'curated_pair', pairId: temporalPair.pairId }
    ranked.push({
      reference,
      absPearson: Math.abs(computePearsonDelta(
        seriesById.get(temporalPair.seriesA.seriesId).points,
        seriesById.get(temporalPair.seriesB.seriesId).points,
        temporalPair.window,
      )),
      refId: editorialRefId(reference),
    })
  }
  const screenedReference = { kind: 'screened', relationId: screenedRelation.relationId }
  ranked.push({
    reference: screenedReference,
    absPearson: Math.abs(computePearsonDelta(
      seriesById.get(screenedRelation.seriesAId).points,
      seriesById.get(screenedRelation.seriesBId).points,
      screenedRelation.window,
    )),
    refId: editorialRefId(screenedReference),
  })
  ranked.sort((left, right) => right.absPearson - left.absPearson
    || (left.refId < right.refId ? -1 : left.refId > right.refId ? 1 : 0))
  const structuralReference = {
    kind: 'structural',
    aSeriesId: lagged.aSeriesId,
    bSeriesId: lagged.bSeriesId,
    lagYears: lagged.lagYears,
  }
  return {
    criteria: {
      leadStrengths: [...EDITORIAL_READING_CRITERIA.leadStrengths],
      structuralAlwaysLead: EDITORIAL_READING_CRITERIA.structuralAlwaysLead,
      gradeEnum: [...EDITORIAL_READING_CRITERIA.gradeEnum],
      orderedBy: EDITORIAL_READING_CRITERIA.orderedBy,
    },
    criteriaStatement: EDITORIAL_CRITERIA_STATEMENT,
    leads: [structuralReference, ...ranked.map((entry) => entry.reference)],
    noteCount,
    noteStatement: renderEditorialNoteStatement(noteCount),
  }
}

function buildDocument() {
  const education = makeSeries({
    seriesId: EDUCATION_ID,
    label: 'Matrículas no ensino fundamental',
    deltas: EDUCATION_DELTAS,
  })
  const births = makeBirthSeries()
  const moderate = makeSeries({
    seriesId: MODERATE_ID,
    label: 'População estimada',
    deltas: MODERATE_DELTAS,
  })
  const weak = makeSeries({
    seriesId: WEAK_ID,
    label: 'Famílias inscritas no cadastro social — posição de dezembro',
    deltas: WEAK_DELTAS,
  })
  const strongCurated = makeSeries({
    seriesId: STRONG_CURATED_ID,
    label: 'Vínculos formais de pessoas com ensino médio completo',
    deltas: EDUCATION_DELTAS.map((delta) => delta * 2),
  })
  const strongScreened = makeSeries({
    seriesId: STRONG_SCREENED_ID,
    label: 'Vínculos formais ativos',
    deltas: EDUCATION_DELTAS.map((delta) => delta * 3),
  })
  const factors = [moderate, weak, strongCurated]
  const association = {
    associationId: 'matriculas-no-ensino-fundamental-e-populacao-estimada',
    label: education.label,
    window: { ...WINDOW },
    periodLabel: '2010 a 2019',
    educationOutcome: { seriesId: education.seriesId, label: education.label },
    territorialFactors: factors.map((factor) => ({ seriesId: factor.seriesId, label: factor.label })),
    observedStatement: 'As duas séries variaram no período observado.',
    allowedInterpretation: 'A leitura descreve movimentos observados em conjunto.',
    prohibitedClaim: 'Não se pode concluir que uma série determine a outra.',
    hypotheses: ['A relação observada pode orientar investigação posterior.'],
    associativeReading: makeAssociationReading(education, factors),
    pneThemes: pneThemesFor(education.seriesId),
  }
  const temporalPair = {
    pairId: 'populacao-estimada-e-matriculas-no-ensino-fundamental',
    label: 'População estimada e matrículas no ensino fundamental',
    window: { ...WINDOW },
    periodLabel: '2010 a 2019',
    seriesA: { seriesId: moderate.seriesId, label: moderate.label },
    seriesB: { seriesId: education.seriesId, label: education.label },
    observedStatement: 'As duas séries apresentam transformações simultâneas.',
    prohibitedClaim: 'Não se pode concluir que a transformação de uma cause a da outra.',
    associativeReading: makeTemporalReading(moderate, education),
    pneThemes: pneThemesFor(moderate.seriesId, education.seriesId),
  }
  const screenedRelation = {
    relationId: `${strongScreened.seriesId}--${education.seriesId}`,
    seriesAId: strongScreened.seriesId,
    seriesBId: education.seriesId,
    window: { ...WINDOW },
    directionConcordance: makeDirectionConcordance(strongScreened, education, WINDOW),
    comovement: makeComovement(strongScreened, education, WINDOW, 'screened'),
    correlation: makeCorrelation(strongScreened, education, WINDOW),
    originStatement: SCREENED_ORIGIN_STATEMENT,
    salience: 'lead',
    grade: EDITORIAL_READING_CRITERIA.gradeEnum[0],
    pneThemes: pneThemesFor(education.seriesId),
  }
  const lagged = makeLaggedReading(strongScreened, education)
  const series = [education, births, moderate, weak, strongCurated, strongScreened]
  const seriesById = new Map(series.map((serie) => [serie.seriesId, serie]))
  const associationSynthesisStatement = observedSynthesisStatement(education, ...factors)
  const temporalSynthesisStatement = observedSynthesisStatement(moderate, education)
  const editorialReading = makeEditorialReading({
    association,
    temporalPair,
    lagged,
    screenedRelation,
    seriesById,
  })
  return {
    schemaVersion: VOCACOES_DOCUMENT_SCHEMA,
    contentVersion: '0'.repeat(64),
    generatedAt: '2025-12-31',
    generatorVersion: 'vocacoes-regiao-generator-test-v7',
    sourceVersion: SOURCE_VERSION,
    sourceMethodologyStatus: 'piloto sintético',
    publicationScope: PUBLICATION_SCOPE,
    region: { slug: 'regiao-teste', name: 'Região Teste', uf: 'RS', municipalityCount: 1 },
    page: {
      eyebrow: 'Vocações da Região',
      title: 'Região Teste',
      description: 'Documento sintético para teste do parser.',
      neutralityNote: 'Leitura descritiva sem inferência causal.',
    },
    howToRead: {
      label: 'Como ler',
      description: 'Notas de leitura do documento.',
      items: ['Os valores são observados nas séries sintéticas.'],
    },
    synthesis: {
      ...SYNTHESIS_FRAMING,
      items: [
        {
          kindLabel: SYNTHESIS_KIND_LABELS.observed,
          basisLabel: [education, ...factors].map((serie) => serie.label).join(' · '),
          statement: associationSynthesisStatement,
        },
        {
          kindLabel: SYNTHESIS_KIND_LABELS.observed,
          basisLabel: temporalPair.label,
          statement: temporalSynthesisStatement,
        },
      ],
      absentKinds: [
        {
          kindLabel: SYNTHESIS_KIND_LABELS.scenario_invariant,
          statement: 'Não há conclusão invariante de cenários nesta região.',
        },
        {
          kindLabel: SYNTHESIS_KIND_LABELS.agenda,
          statement: 'Não há conclusão de agenda derivada de cenários nesta região.',
        },
      ],
    },
    territoryPortrait: {
      label: 'Retrato do território',
      description: 'Seis séries anuais sintéticas.',
      series,
    },
    decompositions: makeDecompositions(education, births),
    associations: {
      label: 'Associações',
      description: 'Uma associação sintética.',
      items: [association],
    },
    temporalPairs: {
      label: 'Pares temporais',
      description: 'Um par temporal sintético.',
      items: [temporalPair],
      laggedItems: [lagged],
    },
    screenedRelations: {
      label: 'Relações observadas por triagem',
      description: 'Relações adicionais descritas sem inferência causal.',
      methodNote: ASSOCIATIVE_METHOD_NOTE,
      criteria: {
        ...SCREENED_RELATIONS_CRITERIA,
        excludedSeries: [...SCREENING_EXCLUDED_SERIES_IDS],
      },
      items: [screenedRelation],
    },
    editorialReading,
    scenarios: {
      label: SCENARIO_FRAMING.label,
      description: SCENARIO_FRAMING.absentDescription,
      statuteReadingNote: null,
      status: 'absent',
      absenceStatement: SCENARIO_FRAMING.absenceStatement,
      block: null,
    },
    sources: {
      label: 'Fontes',
      description: 'Fonte usada no teste.',
      items: [{ label: 'Fonte sintética determinística', periodLabel: '2010 a 2025' }],
    },
    limitations: {
      label: 'Limitações',
      description: 'Limitações do documento sintético.',
      items: ['Os dados existem apenas para exercitar o contrato.'],
    },
    provenance: {
      sourcePackageSha256: '1'.repeat(64),
      sourceContractVersion: 'v0.6',
      sourceBuilderVersion: 'builder-test-v1',
      sourceGeneratedAt: '2025-12-31',
      registrySha256: '2'.repeat(64),
      scenarioPackageSha256: null,
      scenarioSourceSha256: null,
      municipalPackageSha256: null,
      synthesisPackageSha256: '3'.repeat(64),
    },
  }
}

function refuses(mutate, pattern) {
  const candidate = buildDocument()
  mutate(candidate)
  assert.throws(() => parseDocument(candidate), pattern)
}

test('parser 2.8.0 aceita documento associativo sintético válido', () => {
  const parsed = parseDocument(buildDocument())
  assert.equal(parsed.schemaVersion, VOCACOES_DOCUMENT_SCHEMA)
  assert.equal(parsed.decompositions.enrollment.items.length, 1)
  assert.notEqual(parsed.decompositions.employment.item, null)
  assert.equal(parsed.temporalPairs.laggedItems.length, 1)
  assert.equal(parsed.screenedRelations.items.length, 1)
  assert.deepEqual(parsed.screenedRelations.criteria, {
    ...SCREENED_RELATIONS_CRITERIA,
    excludedSeries: [...SCREENING_EXCLUDED_SERIES_IDS],
  })
  assert.equal(parsed.editorialReading.criteriaStatement, EDITORIAL_CRITERIA_STATEMENT)
  assert.equal(
    parsed.editorialReading.noteStatement,
    renderEditorialNoteStatement(parsed.editorialReading.noteCount),
  )
  assert.equal(parsed.editorialReading.noteCount, 1)
  assert.deepEqual(parsed.associations.items[0].pneThemes, pneThemesFor(EDUCATION_ID))
  assert.equal(
    parsed.associations.items[0].associativeReading.factorReadings
      .find((reading) => reading.factorSeriesId === WEAK_ID).salience,
    'note',
  )
})

test('parser 2.8.0 recusa documento 2.7.0', () => {
  refuses((candidate) => { candidate.schemaVersion = 'vocacoes-regiao-2.7.0' }, /esquema/u)
})

test('parser recusa associativeReading ausente', () => {
  refuses(
    (candidate) => { delete candidate.associations.items[0].associativeReading },
    /campos obrigatórios: associativeReading/u,
  )
})

test('parser recusa seriesId órfão', () => {
  refuses((candidate) => {
    const item = candidate.screenedRelations.items[0]
    item.seriesAId = 'serie-orfa'
    item.relationId = `${item.seriesAId}--${item.seriesBId}`
  }, /não resolve em nenhuma série/u)
})

test('parser recusa concordant divergente da recomputação', () => {
  refuses((candidate) => {
    candidate.associations.items[0].associativeReading
      .factorReadings[0].directionConcordance.concordant -= 1
  }, /concordant diverge da recomputação/u)
})

test('parser recusa pearsonDelta divergente da recomputação', () => {
  refuses((candidate) => {
    candidate.associations.items[0].associativeReading
      .factorReadings[0].correlation.pearsonDelta = 0.91
  }, /pearsonDelta diverge da recomputação/u)
})

test('parser recusa strength fora do bin recomputado', () => {
  refuses((candidate) => {
    candidate.associations.items[0].associativeReading
      .factorReadings[0].correlation.strength = 'forte'
  }, /strength diverge do bin recomputado/u)
})

test('parser recusa statement com um byte trocado', () => {
  refuses((candidate) => {
    const correlation = candidate.associations.items[0].associativeReading
      .factorReadings[0].correlation
    correlation.statement = `${correlation.statement.slice(0, -1)}!`
  }, /statement diverge do template T-CORR/u)
})

test('parser recusa reasonCode fora do enum fechado', () => {
  refuses((candidate) => {
    candidate.associations.items[0].associativeReading.stateContrast = {
      reasonCode: 'dados_insuficientes',
    }
  }, /reasonCode fora do contrato/u)
})

test('parser recusa campo desconhecido na leitura associativa', () => {
  refuses((candidate) => {
    candidate.temporalPairs.items[0].associativeReading.coeficienteLivre = 0.9
  }, /campo desconhecido fora do contrato/u)
})

test('corpus V5 R1 recusa A-V5R1-01..09 no parser', () => {
  assert.equal(ATTACK_COUNT, 25)
  const attacks = ATAQUES.filter(([id]) => id.startsWith('A-V5R1-'))
  assert.equal(attacks.length, 9)
  for (const [id, _vector, mutate] of attacks) {
    const candidate = buildDocument()
    mutate(candidate)
    assert.throws(() => parseDocument(candidate), undefined, `${id} atravessou o parser`)
  }
})

test('corpus V5 R1 aceita H-V5R1-01..04 no parser', () => {
  assert.equal(HONEST_COUNT, 12)
  const honest = HONESTOS.filter(([id]) => id.startsWith('H-V5R1-'))
  assert.equal(honest.length, 4)
  for (const [id, mutate] of honest) {
    const candidate = buildDocument()
    mutate(candidate)
    assert.doesNotThrow(() => parseDocument(candidate), `${id} foi recusado pelo parser`)
  }
})

test('corpus V5 R2 recusa A-V5R2-01..09 entre guarda e parser', () => {
  const attacks = ATAQUES.filter(([id]) => id.startsWith('A-V5R2-'))
  assert.equal(attacks.length, 9)
  for (const [id, _vector, mutate] of attacks) {
    const candidate = buildDocument()
    mutate(candidate)
    let caught = false
    try { scanPublicDocument(candidate, languageGuard) } catch { caught = true }
    if (!caught) {
      try { parseDocument(candidate) } catch { caught = true }
    }
    assert.equal(caught, true, `${id} atravessou a guarda e o parser`)
  }
})

test('corpus V5 R2 aceita H-V5R2-01..04 e preserva E1 no rebaixamento', () => {
  const honest = HONESTOS.filter(([id]) => id.startsWith('H-V5R2-'))
  assert.equal(honest.length, 4)
  for (const [id, mutate] of honest) {
    const candidate = buildDocument()
    const e1Before = structuredClone(candidate.associations)
    mutate(candidate)
    assert.doesNotThrow(() => scanPublicDocument(candidate, languageGuard), `${id} barrado pela guarda`)
    assert.doesNotThrow(() => parseDocument(candidate), `${id} barrado pelo parser`)
    if (id === 'H-V5R2-02') {
      assert.deepEqual(candidate.associations, e1Before, 'o rebaixamento E2 alterou a leitura E1')
      assert.ok(candidate.decompositions.enrollment.absences.some((absence) =>
        absence.reasonCode === 'conta_nao_fecha'))
    }
  }
})

test('guarda pública barra "meta 3" e preserva texto honesto sem número de meta', () => {
  assert.throws(
    () => assertNoPublicMetaNumber('Universalização do ensino médio — meta 3.', 'ataque'),
    /número de uma meta/u,
  )
  assert.doesNotThrow(() => assertNoPublicMetaNumber(
    'As metas de aprendizagem permanecem descritas sem numeração.',
    'honesto',
  ))
})

test('roundHalfAwayFromZero cobre empate decimal que toFixed arredonda para baixo', () => {
  assert.equal(Number((1.005).toFixed(2)), 1)
  assert.equal(roundHalfAwayFromZero(1.005, 2), 1.01)
  assert.equal(roundHalfAwayFromZero(-1.005, 2), -1.01)
})

test('formatPublicNumber replica o half-even binário de numero_publico', () => {
  assert.equal(formatPublicNumber(1234), '1 234')
  assert.equal(formatPublicNumber(1234.5), '1 234,5')
  assert.equal(formatPublicNumber(2.25), '2,2')
})

test('Spearman usa postos médios nos empates', () => {
  const pointsFromDeltas = (deltas) => {
    let value = 0
    return [
      { period: 2010, value, evidenceClass: 'observed' },
      ...deltas.map((delta, index) => {
        value += delta
        return { period: 2011 + index, value, evidenceClass: 'observed' }
      }),
    ]
  }
  const pointsA = pointsFromDeltas([1, 1, 2, 3, 4])
  const pointsB = pointsFromDeltas([1, 2, 2, 3, 5])
  const spearman = computeSpearmanDelta(pointsA, pointsB, { start: 2010, end: 2015 })
  assert.equal(roundHalfAwayFromZero(spearman, 6), 0.921053)
})

test('bins de força incluem exatamente os limiares 0.3 e 0.7', () => {
  assert.equal(correlationStrength(0.299999), 'fraca')
  assert.equal(correlationStrength(0.3), 'moderada')
  assert.equal(correlationStrength(0.699999), 'moderada')
  assert.equal(correlationStrength(0.7), 'forte')
})
