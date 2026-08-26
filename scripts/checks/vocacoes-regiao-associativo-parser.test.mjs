import assert from 'node:assert/strict'
import test from 'node:test'

import {
  AGGREGATION_LABELS,
  ASSOCIATIVE_GRAMMAR_VERSION,
  ASSOCIATIVE_METHOD_NOTE,
  EVIDENCE_CLASS_LABELS,
  SCENARIO_FRAMING,
  SCREENED_ORIGIN_STATEMENT,
  SCREENED_RELATIONS_CRITERIA,
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
  renderLaggedStatement,
  roundHalfAwayFromZero,
} from '../../src/features/vocacoes-regiao/vocacoesRegiaoContract.js'

const SOURCE_VERSION = 'vocacoes-regiao-pesquisa-v0.4'
const PUBLICATION_SCOPE = 'estadual'
const REFERENCE_YEAR = 2025
const REFERENCE_MONTH = 12
const WINDOW = Object.freeze({ start: 2010, end: 2019 })
const LAG_YEARS = 6
const LAGGED_RATIONALE =
  'a coorte nascida em um ano atinge a idade de ingresso no ensino fundamental seis anos depois'

const parseDocument = createVocacoesDocumentParser({
  sourceVersion: SOURCE_VERSION,
  publicationScope: PUBLICATION_SCOPE,
  referenceYear: REFERENCE_YEAR,
  referenceMonth: REFERENCE_MONTH,
})

function makeSeries({ seriesId, label, multiplier }) {
  const points = []
  for (let period = 2010; period <= 2025; period += 1) {
    const index = period - 2009
    points.push({ period, value: multiplier * index ** 2, evidenceClass: 'observed' })
  }
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

function makeAssociationReading(seriesA, seriesB) {
  return {
    grammarVersion: ASSOCIATIVE_GRAMMAR_VERSION,
    methodNote: ASSOCIATIVE_METHOD_NOTE,
    factorReadings: [{
      outcomeSeriesId: seriesA.seriesId,
      factorSeriesId: seriesB.seriesId,
      directionConcordance: makeDirectionConcordance(seriesA, seriesB, WINDOW),
      comovement: makeComovement(seriesA, seriesB, WINDOW, 'association'),
      correlation: makeCorrelation(seriesA, seriesB, WINDOW),
    }],
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

function observedSynthesisStatement(seriesA, seriesB) {
  const startA = seriesA.points.find((point) => point.period === WINDOW.start).value
  const endA = seriesA.points.find((point) => point.period === WINDOW.end).value
  const startB = seriesB.points.find((point) => point.period === WINDOW.start).value
  const endB = seriesB.points.find((point) => point.period === WINDOW.end).value
  return `Conclui-se do observado que, entre ${WINDOW.start} e ${WINDOW.end}, ${seriesA.label} `
    + `passou de ${formatPublicNumber(startA)} para ${formatPublicNumber(endA)} e, no mesmo `
    + `período, ${seriesB.label} passou de ${formatPublicNumber(startB)} para `
    + `${formatPublicNumber(endB)}.`
}

function buildDocument() {
  const seriesA = makeSeries({ seriesId: 'serie-a', label: 'Série A', multiplier: 1 })
  const seriesB = makeSeries({ seriesId: 'serie-b', label: 'Série B', multiplier: 2 })
  const association = {
    associationId: 'serie-a-e-serie-b',
    label: 'Série A associada à Série B',
    window: { ...WINDOW },
    periodLabel: '2010 a 2019',
    educationOutcome: { seriesId: seriesA.seriesId, label: seriesA.label },
    territorialFactors: [{ seriesId: seriesB.seriesId, label: seriesB.label }],
    observedStatement: 'As duas séries variaram no período observado.',
    allowedInterpretation: 'A leitura descreve movimentos observados em conjunto.',
    prohibitedClaim: 'Não se pode concluir que uma série determine a outra.',
    hypotheses: ['A relação observada pode orientar investigação posterior.'],
    associativeReading: makeAssociationReading(seriesA, seriesB),
  }
  const temporalPair = {
    pairId: 'serie-a-e-serie-b-no-tempo',
    label: 'Série A e Série B no tempo',
    window: { ...WINDOW },
    periodLabel: '2010 a 2019',
    seriesA: { seriesId: seriesA.seriesId, label: seriesA.label },
    seriesB: { seriesId: seriesB.seriesId, label: seriesB.label },
    observedStatement: 'As duas séries apresentam transformações simultâneas.',
    prohibitedClaim: 'Não se pode concluir que a transformação de uma cause a da outra.',
    associativeReading: makeTemporalReading(seriesA, seriesB),
  }
  const screenedRelation = {
    relationId: `${seriesA.seriesId}--${seriesB.seriesId}`,
    seriesAId: seriesA.seriesId,
    seriesBId: seriesB.seriesId,
    window: { ...WINDOW },
    directionConcordance: makeDirectionConcordance(seriesA, seriesB, WINDOW),
    comovement: makeComovement(seriesA, seriesB, WINDOW, 'screened'),
    correlation: makeCorrelation(seriesA, seriesB, WINDOW),
    originStatement: SCREENED_ORIGIN_STATEMENT,
  }
  const synthesisStatement = observedSynthesisStatement(seriesA, seriesB)
  return {
    schemaVersion: VOCACOES_DOCUMENT_SCHEMA,
    contentVersion: '0'.repeat(64),
    generatedAt: '2025-12-31',
    generatorVersion: 'vocacoes-regiao-generator-test-v5',
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
          basisLabel: 'Série A · Série B',
          statement: synthesisStatement,
        },
        {
          kindLabel: SYNTHESIS_KIND_LABELS.observed,
          basisLabel: temporalPair.label,
          statement: synthesisStatement,
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
      description: 'Duas séries anuais sintéticas.',
      series: [seriesA, seriesB],
    },
    associations: {
      label: 'Associações',
      description: 'Uma associação sintética.',
      items: [association],
    },
    temporalPairs: {
      label: 'Pares temporais',
      description: 'Um par temporal sintético.',
      items: [temporalPair],
      laggedItems: [makeLaggedReading(seriesA, seriesB)],
    },
    screenedRelations: {
      label: 'Relações observadas por triagem',
      description: 'Relações adicionais descritas sem inferência causal.',
      methodNote: ASSOCIATIVE_METHOD_NOTE,
      criteria: { ...SCREENED_RELATIONS_CRITERIA },
      items: [screenedRelation],
    },
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
      sourceContractVersion: 'v0.4',
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

test('parser 2.6.0 aceita documento associativo sintético válido', () => {
  const parsed = parseDocument(buildDocument())
  assert.equal(parsed.schemaVersion, VOCACOES_DOCUMENT_SCHEMA)
  assert.equal(parsed.temporalPairs.laggedItems.length, 1)
  assert.equal(parsed.screenedRelations.items.length, 1)
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
      .factorReadings[0].correlation.strength = 'moderada'
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
