/*
 * Corpus bilateral permanente da leitura associativa — V3 R1 + V5 R1 + V5 R2.
 *
 * Como no corpus histórico do Vocações, cada caso é uma mutação sobre um
 * documento público real. A plataforma exercita a guarda lexical e o parser
 * fechado sobre a mesma mutação. O A-V3R1-07 fica registrado como furo
 * declarado: os marcadores de ordem também aparecem em cronologias honestas e
 * não há padrão léxico geral sem falso positivo.
 */

import {
  AGGREGATION_LABELS,
  EDITORIAL_CRITERIA_STATEMENT,
  EVIDENCE_CLASS_LABELS,
  SCREENED_ORIGIN_STATEMENT,
  computeComovement,
  computeDirectionConcordance,
  computePearsonDelta,
  computeSpearmanDelta,
  correlationStrength,
  renderComovementStatement,
  renderConcordanceStatement,
  renderCorrelationStatement,
  renderEditorialNoteStatement,
  renderE2AbsenceStatement,
  roundHalfAwayFromZero,
} from '../../../src/features/vocacoes-regiao/vocacoesRegiaoContract.js'

const primeiraAssociacao = (document) => document.associations.items[0]
const STAGE_ORDER = Object.freeze([
  'educacao_infantil',
  'ensino_fundamental',
  'ensino_medio',
])

function primeiroItemMatriculaE2(document) {
  const item = document.decompositions.enrollment.items[0]
  if (item === undefined) throw new Error('fixture não traz decomposição E2 de matrícula')
  return item
}

function itemEmpregoE2(document) {
  const item = document.decompositions.employment.item
  if (item === null) throw new Error('fixture não traz decomposição E2 de emprego')
  return item
}

function primeiraCorrelacaoAssociativa(document) {
  for (const association of document.associations.items) {
    for (const reading of association.associativeReading.factorReadings) {
      if (reading.correlation?.statement !== undefined) return reading.correlation
    }
  }
  throw new Error('fixture publicado não traz correlação associativa renderizada')
}

function leiturasCuradas(document) {
  return [
    ...document.associations.items.flatMap((association) =>
      association.associativeReading.factorReadings),
    ...document.temporalPairs.items.map((pair) => pair.associativeReading),
  ]
}

function leituraCurada(document, strength) {
  const reading = leiturasCuradas(document).find((candidate) =>
    candidate.correlation?.strength === strength)
  if (reading === undefined) throw new Error(`fixture não traz leitura curada ${strength}`)
  return reading
}

function seriePorId(document, seriesId) {
  const serie = document.territoryPortrait.series.find((candidate) => candidate.seriesId === seriesId)
  if (serie === undefined) throw new Error(`fixture não traz a série pública ${seriesId}`)
  return serie
}

function deltasComCorrelacao(targetDeltas, targetCorrelation) {
  const mean = targetDeltas.reduce((sum, value) => sum + value, 0) / targetDeltas.length
  const centered = targetDeltas.map((value) => value - mean)
  const normSquared = centered.reduce((sum, value) => sum + value ** 2, 0)
  if (normSquared === 0) throw new Error('fixture triado usa série B sem variância')
  const candidates = [
    targetDeltas.map((_value, index) => (index % 2 === 0 ? index + 1 : -(index + 1))),
    targetDeltas.map((_value, index) => (index + 1) ** 2),
  ]
  let orthogonal = null
  for (const seed of candidates) {
    const seedMean = seed.reduce((sum, value) => sum + value, 0) / seed.length
    const seedCentered = seed.map((value) => value - seedMean)
    const projection = seedCentered.reduce(
      (sum, value, index) => sum + value * centered[index],
      0,
    ) / normSquared
    const candidate = seedCentered.map((value, index) => value - projection * centered[index])
    const candidateNorm = candidate.reduce((sum, value) => sum + value ** 2, 0)
    if (candidateNorm > 1e-12) {
      const scale = Math.sqrt(normSquared / candidateNorm)
      orthogonal = candidate.map((value) => value * scale)
      break
    }
  }
  if (orthogonal === null) throw new Error('fixture não construiu vetor ortogonal para A-V5R1-04')
  const residual = Math.sqrt(1 - targetCorrelation ** 2)
  return centered.map((value, index) =>
    targetCorrelation * value + residual * orthogonal[index])
}

function reescreverTriadaComPearson055(document) {
  const item = document.screenedRelations.items[0]
  if (item === undefined) throw new Error('fixture não traz relação triada para A-V5R1-04')
  const serieB = seriePorId(document, item.seriesBId)
  const pointsInWindow = serieB.points.filter((point) =>
    point.period >= item.window.start && point.period <= item.window.end)
  const targetDeltas = pointsInWindow.slice(1).map((point, index) =>
    point.value - pointsInWindow[index].value)
  const attackDeltas = deltasComCorrelacao(targetDeltas, 0.55)
  const deltaByPeriod = new Map(pointsInWindow.slice(1).map((point, index) => [
    point.period,
    attackDeltas[index],
  ]))
  let value = 100_000
  const points = serieB.points.map((point) => {
    if (point.period > serieB.points[0].period) value += deltaByPeriod.get(point.period) ?? 1
    return { ...point, value }
  })
  const label = 'Série territorial sintética do ataque'
  const serieA = {
    ...structuredClone(seriePorId(document, item.seriesAId)),
    seriesId: 'serie-territorial-sintetica-do-ataque',
    label,
    evidenceClass: 'observed',
    evidenceLabel: EVIDENCE_CLASS_LABELS.observed,
    ratioOf: null,
    universeLabel: null,
    aggregationLabel: AGGREGATION_LABELS.sum,
    periodGranularity: 'annual',
    periodStart: points[0].period,
    periodEnd: points[points.length - 1].period,
    periodLabel: `${points[0].period} a ${points[points.length - 1].period}`,
    preliminaryPeriods: [],
    points: points.map((point) => ({ ...point, evidenceClass: 'observed' })),
  }
  document.territoryPortrait.series.push(serieA)

  const direction = computeDirectionConcordance(serieA.points, serieB.points, item.window)
  if ('reasonCode' in direction) throw new Error('A-V5R1-04 não produziu intervalos comparáveis')
  const movementA = computeComovement(serieA.points, item.window, 'nivel')
  const movementB = computeComovement(
    serieB.points,
    item.window,
    serieB.ratioOf === null ? 'nivel' : 'pontos',
  )
  if ('reasonCode' in movementA || 'reasonCode' in movementB) {
    throw new Error('A-V5R1-04 não produziu co-movimento')
  }
  const pearsonRaw = computePearsonDelta(serieA.points, serieB.points, item.window)
  const spearmanRaw = computeSpearmanDelta(serieA.points, serieB.points, item.window)
  if (pearsonRaw === null || spearmanRaw === null || roundHalfAwayFromZero(pearsonRaw, 2) !== 0.55) {
    throw new Error(`A-V5R1-04 não construiu pearson 0,55: ${pearsonRaw}`)
  }
  const correlation = {
    intervals: direction.intervals,
    pearsonDelta: 0.55,
    spearmanDelta: roundHalfAwayFromZero(spearmanRaw, 2),
    strength: correlationStrength(Math.abs(pearsonRaw)),
    direction: 'positiva',
  }
  item.relationId = `${serieA.seriesId}--${serieB.seriesId}`
  item.seriesAId = serieA.seriesId
  item.directionConcordance = {
    ...direction,
    statement: renderConcordanceStatement({ ...direction, labelA: serieA.label, labelB: serieB.label }),
  }
  item.comovement = {
    a: { seriesId: serieA.seriesId, ...movementA },
    b: { seriesId: serieB.seriesId, ...movementB },
    statement: renderComovementStatement({
      a: movementA,
      b: movementB,
      labelA: serieA.label,
      labelB: serieB.label,
    }),
  }
  item.correlation = {
    ...correlation,
    statement: renderCorrelationStatement({
      windowStart: item.window.start,
      windowEnd: item.window.end,
      ...correlation,
    }),
  }
  item.salience = 'lead'
}

function encontrarStatement(document, expected) {
  const correlations = [
    ...document.associations.items.flatMap((association) =>
      association.associativeReading.factorReadings.map((reading) => reading.correlation)),
    ...document.temporalPairs.items.map((pair) => pair.associativeReading.correlation),
    ...document.screenedRelations.items.map((item) => item.correlation),
  ]
  const correlation = correlations.find((candidate) => candidate?.statement === expected)
  if (correlation === undefined) throw new Error(`statement honesto ausente do fixture: ${expected}`)
  return correlation
}

const ATAQUES_V3 = [
  ['A-V3R1-01', 8, (document) => {
    primeiraCorrelacaoAssociativa(document).statement =
      'Na janela de 2014 a 2025, a correlação entre as variações anuais das duas séries é de 0,91 e comprova a relação.'
  }],
  ['A-V3R1-02', 8, (document) => {
    primeiraCorrelacaoAssociativa(document).statement =
      'Na janela de 2014 a 2025, a correlação entre as variações anuais das duas séries é de 0,91 — forte e positiva, mostrando que o emprego determina a matrícula.'
  }],
  ['A-V3R1-03', 8, (document) => {
    const correlation = primeiraCorrelacaoAssociativa(document)
    correlation.statement = `${correlation.statement} Com p-valor de 0,03.`
  }],
  ['A-V3R1-04', 8, (document) => {
    const correlation = primeiraCorrelacaoAssociativa(document)
    correlation.pearsonDelta = 0.4
    correlation.strength = 'forte'
  }],
  ['A-V3R1-05', 8, (document) => {
    const association = primeiraAssociacao(document)
    association.observedStatement = `${association.observedStatement} r = 0,91`
  }],
  ['A-V3R1-06', 8, (document) => {
    primeiraAssociacao(document).observedStatement =
      'Depois que a indústria retraiu, a matrícula técnica caiu.'
  }],
  ['A-V3R1-07', 8, (document) => {
    primeiraAssociacao(document).observedStatement =
      'Primeiro o emprego caiu; as matrículas caíram em seguida.'
  }],
]

const ATAQUES_V5 = [
  ['A-V5R1-01', 9, (document) => {
    const reading = leituraCurada(document, 'fraca')
    reading.correlation.pearsonDelta = 0.2
    reading.correlation.strength = 'forte'
  }],
  ['A-V5R1-02', 9, (document) => {
    leituraCurada(document, 'fraca').salience = 'lead'
  }],
  ['A-V5R1-03', 9, (document) => {
    leituraCurada(document, 'forte').salience = 'note'
  }],
  ['A-V5R1-04', 9, (document) => {
    reescreverTriadaComPearson055(document)
  }],
  ['A-V5R1-05', 9, (document) => {
    if (document.editorialReading.leads.length < 2) {
      throw new Error('fixture não traz dois destaques para A-V5R1-05')
    }
    const first = document.editorialReading.leads[0]
    document.editorialReading.leads[0] = document.editorialReading.leads[1]
    document.editorialReading.leads[1] = first
  }],
  ['A-V5R1-06', 9, (document) => {
    primeiraAssociacao(document).pneThemes = [{
      theme: 'eja',
      themeLabel: 'Educação de jovens e adultos',
    }]
  }],
  ['A-V5R1-07', 9, (document) => {
    primeiraAssociacao(document).pneThemes[0].themeLabel =
      'Universalização e permanência no ensino médio — meta 3, 85% até 2031'
  }],
  ['A-V5R1-08', 9, (document) => {
    const structural = document.temporalPairs.laggedItems.find((item) => item.salience === 'lead')
    if (structural === undefined) throw new Error('fixture não traz estrutural publicada')
    structural.salience = 'note'
  }],
  ['A-V5R1-09', 9, (document) => {
    const screened = document.screenedRelations.items[0]
    if (screened === undefined) throw new Error('fixture não traz relação triada')
    screened.seriesAId = 'obitos-por-residencia-idade-ignorada'
  }],
]

const ATAQUES_V5_R2 = [
  ['A-V5R2-01', 10, (document) => {
    primeiraAssociacao(document).observedStatement =
      'A relação observada explica 12 pontos percentuais da variação.'
  }],
  ['A-V5R2-02', 10, (document) => {
    primeiroItemMatriculaE2(document).statement =
      'Até 2031 a coorte explicará 12 pontos percentuais da variação.'
  }],
  ['A-V5R2-03', 10, (document) => {
    const item = primeiroItemMatriculaE2(document)
    item.statement = `${item.statement}; o restante decorre do abandono escolar.`
  }],
  ['A-V5R2-04', 10, (document) => {
    primeiroItemMatriculaE2(document).contributions.demographicPp += 2
  }],
  ['A-V5R2-05', 10, (document) => {
    delete primeiroItemMatriculaE2(document).terms
  }],
  ['A-V5R2-06', 10, (document) => {
    const item = primeiroItemMatriculaE2(document)
    const cohort = seriePorId(document, item.cohortSeriesId)
    const birthPeriod = item.window.end - item.cohortAges.min
    cohort.preliminaryPeriods = [...new Set([...cohort.preliminaryPeriods, birthPeriod])]
      .sort((left, right) => left - right)
  }],
  ['A-V5R2-07', 10, (document) => {
    itemEmpregoE2(document).sectors.pop()
  }],
  ['A-V5R2-08', 10, (document) => {
    const item = primeiroItemMatriculaE2(document)
    item.statement = item.statement.replace(
      'taxa de atendimento aparente',
      'taxa de atendimento',
    )
  }],
  ['A-V5R2-09', 10, (document) => {
    primeiroItemMatriculaE2(document).grade = 'E1'
  }],
]

const ATAQUES = [...ATAQUES_V3, ...ATAQUES_V5, ...ATAQUES_V5_R2]

const CORRELATION_HONESTA =
  'Na janela de 2014 a 2025, a correlação entre as variações anuais das duas séries é de -0,72 — forte e negativa.'
const LAG_HONESTO =
  'Com defasagem de 6 anos — a coorte nascida em um ano atinge a idade de ingresso no ensino fundamental seis anos depois —, em 4 dos 11 intervalos anuais Nascidos vivos por residência da mãe (2008 a 2019) e Matrículas no ensino fundamental (2014 a 2025) variaram no mesmo sentido; a correlação das variações anuais nessa defasagem é de -0,18.'

const HONESTOS_V3 = [
  ['H-V3R1-01', (document) => {
    encontrarStatement(document, CORRELATION_HONESTA).statement = CORRELATION_HONESTA
  }],
  ['H-V3R1-02', (document) => {
    document.screenedRelations.methodNote =
      'Concordância, co-movimento e correlação descrevem movimento conjunto no período observado; não medem causa nem permitem projeção.'
  }],
  ['H-V3R1-03', (document) => {
    const lagged = document.temporalPairs.laggedItems.find((item) => item.statement === LAG_HONESTO)
    if (lagged === undefined) throw new Error('T-LAG honesto ausente do fixture publicado')
    lagged.statement = LAG_HONESTO
  }],
  ['H-V3R1-04', (document) => {
    document.limitations.items.push('Esta leitura não afirma causa.')
  }],
]

const HONESTOS_V5 = [
  ['H-V5R1-01', (document) => {
    const reading = leituraCurada(document, 'moderada')
    reading.salience = 'lead'
    reading.grade = 'E1'
  }],
  ['H-V5R1-02', (document) => {
    const reading = leituraCurada(document, 'fraca')
    reading.salience = 'note'
    reading.grade = 'E1'
  }],
  ['H-V5R1-03', (document) => {
    document.editorialReading.criteriaStatement = EDITORIAL_CRITERIA_STATEMENT
    document.editorialReading.noteStatement = renderEditorialNoteStatement(
      document.editorialReading.noteCount,
    )
  }],
  ['H-V5R1-04', (document) => {
    const screened = document.screenedRelations.items[0]
    if (screened === undefined) throw new Error('fixture não traz relação triada honesta')
    screened.salience = 'lead'
    screened.grade = 'E1'
    screened.originStatement = SCREENED_ORIGIN_STATEMENT
  }],
]

const HONESTOS_V5_R2 = [
  ['H-V5R2-01', (document) => {
    primeiroItemMatriculaE2(document)
    itemEmpregoE2(document)
  }],
  ['H-V5R2-02', (document) => {
    const item = document.decompositions.enrollment.items.shift()
    if (item === undefined) throw new Error('fixture não traz item E2 para rebaixamento')
    const absence = {
      stage: item.stage,
      stageLabel: item.stageLabel,
      reasonCode: 'conta_nao_fecha',
    }
    document.decompositions.enrollment.absences.push({
      ...absence,
      statement: renderE2AbsenceStatement(absence),
    })
    document.decompositions.enrollment.absences.sort((left, right) =>
      STAGE_ORDER.indexOf(left.stage) - STAGE_ORDER.indexOf(right.stage))
  }],
  ['H-V5R2-03', (document) => {
    document.limitations.items.push(
      'As hipóteses explicativas são limitações porque esta leitura não afirma causa.',
    )
  }],
  ['H-V5R2-04', (document) => {
    const item = primeiroItemMatriculaE2(document)
    if ((item.statement.match(/\bexplica\b/gu) ?? []).length !== 2) {
      throw new Error('fixture E2 honesto não contém as duas ocorrências de "explica"')
    }
  }],
]

const HONESTOS = [...HONESTOS_V3, ...HONESTOS_V5, ...HONESTOS_V5_R2]

export const ATTACK_COUNT = ATAQUES.length
export const HONEST_COUNT = HONESTOS.length
export const DECLARED_GAPS = Object.freeze(['A-V3R1-07'])

export { ATAQUES, HONESTOS }
