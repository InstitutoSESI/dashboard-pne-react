/*
 * Corpus bilateral permanente da leitura associativa — V3, Rodada 1.
 *
 * Como no corpus histórico do Vocações, cada caso é uma mutação sobre um
 * documento público real. A plataforma exercita a guarda lexical e o parser
 * fechado sobre a mesma mutação. O A-V3R1-07 fica registrado como furo
 * declarado: os marcadores de ordem também aparecem em cronologias honestas e
 * não há padrão léxico geral sem falso positivo.
 */

const primeiraAssociacao = (document) => document.associations.items[0]

function primeiraCorrelacaoAssociativa(document) {
  for (const association of document.associations.items) {
    for (const reading of association.associativeReading.factorReadings) {
      if (reading.correlation?.statement !== undefined) return reading.correlation
    }
  }
  throw new Error('fixture publicado não traz correlação associativa renderizada')
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

const ATAQUES = [
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

const CORRELATION_HONESTA =
  'Na janela de 2014 a 2025, a correlação entre as variações anuais das duas séries é de -0,72 — forte e negativa.'
const LAG_HONESTO =
  'Com defasagem de 6 anos — a coorte nascida em um ano atinge a idade de ingresso no ensino fundamental seis anos depois —, em 4 dos 11 intervalos anuais Nascidos vivos por residência da mãe (2008 a 2019) e Matrículas no ensino fundamental (2014 a 2025) variaram no mesmo sentido; a correlação das variações anuais nessa defasagem é de -0,18.'

const HONESTOS = [
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

export const ATTACK_COUNT = ATAQUES.length
export const HONEST_COUNT = HONESTOS.length
export const DECLARED_GAPS = Object.freeze(['A-V3R1-07'])

export { ATAQUES, HONESTOS }
