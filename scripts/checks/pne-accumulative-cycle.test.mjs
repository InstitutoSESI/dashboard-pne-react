import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

import {
  buildPne2026AccumulativeModel,
  buildPne2026AccumulativePresentationModel,
  buildRecentPublicExpansionReading,
} from '../../src/utils/pneAccumulativeCycle.js'

const CYCLE = 'pne_2026_2036'
const EXPANSION_SHARE_MODE = 'expansion-share-baseline'
const ABSOLUTE_EXPANSION_MODE = 'absolute-expansion-target'

test('cursos subsequentes usam 2025 como base e calculam a meta de +60%', () => {
  const model = buildPne2026AccumulativeModel({
    cycle: CYCLE,
    indicatorKey: 'subsequente_expansao',
    details: {
      series_total: [
        { ano: 2015, valor: 2691 },
        { ano: 2024, valor: 2434 },
        { ano: 2025, valor: 2185 },
      ],
    },
  })

  assert.equal(model.baselineYear, 2025)
  assert.equal(model.baselineValue, 2185)
  assert.equal(model.currentValue, 2185)
  assert.equal(model.targetValue, 3496)
  assert.equal(model.missingValue, 1311)
  assert.equal(model.progress, 0)
  assert.equal(model.status, 'baseline')
  assert.equal(model.statusLabel, 'Linha de base definida')
  assert.equal(model.achieved, null)
})

test('participação pública permanece neutra enquanto não houver expansão após 2025', () => {
  const model = buildPne2026AccumulativeModel({
    cycle: CYCLE,
    indicatorKey: 'medio_tecnico_participacao_publica',
    details: {
      series_dependencia: [
        { ano: 2025, federal: 10, estadual: 50, municipal: 0, privada: 40 },
        { ano: 2026, federal: 10, estadual: 50, municipal: 0, privada: 40 },
      ],
    },
  })

  assert.equal(model.hasExpansion, false)
  assert.equal(model.status, 'pending')
  assert.equal(model.achieved, null)
  assert.equal(model.currentValue, null)
  assert.equal(model.missingValue, null)
})

test('participação pública usa expansão líquida entre 2025 e o último ano', () => {
  const model = buildPne2026AccumulativeModel({
    cycle: CYCLE,
    indicatorKey: 'medio_tecnico_participacao_publica',
    details: {
      series_dependencia: [
        { ano: 2025, federal: 10, estadual: 50, municipal: 0, privada: 40 },
        { ano: 2026, federal: 15, estadual: 55, municipal: 0, privada: 50 },
        { ano: 2027, federal: 10, estadual: 60, municipal: 0, privada: 70 },
      ],
    },
  })

  assert.equal(model.publicExpansion, 10)
  assert.equal(model.totalExpansion, 40)
  assert.equal(model.currentValue, 25)
  assert.equal(model.missingValue, 25)
  assert.equal(model.achieved, false)
  assert.equal(model.status, 'below')
})

test('participação pública preserva retração e valores superiores a 100%', () => {
  const buildModel = (latest) => buildPne2026AccumulativeModel({
    cycle: CYCLE,
    indicatorKey: 'medio_tecnico_participacao_publica',
    details: {
      series_dependencia: [
        { ano: 2025, federal: 10, estadual: 50, municipal: 0, privada: 40 },
        { ano: 2026, ...latest },
      ],
    },
  })

  const retraction = buildModel({ federal: 10, estadual: 40, municipal: 0, privada: 70 })
  assert.equal(retraction.publicExpansion, -10)
  assert.equal(retraction.totalExpansion, 20)
  assert.equal(retraction.currentValue, -50)

  const above100 = buildModel({ federal: 20, estadual: 70, municipal: 0, privada: 20 })
  assert.equal(above100.publicExpansion, 30)
  assert.equal(above100.totalExpansion, 10)
  assert.equal(above100.currentValue, 300)
})

test('outros indicadores e ciclos não recebem a regra especial', () => {
  assert.equal(buildPne2026AccumulativeModel({
    cycle: 'pne_2014_2024',
    indicatorKey: 'subsequente_expansao',
    details: {},
  }), null)

  assert.equal(buildPne2026AccumulativeModel({
    cycle: CYCLE,
    indicatorKey: 'creche',
    details: {},
  }), null)
})

test('leitura recente calcula participação na expansão, não participação no estoque', () => {
  const reading = buildRecentPublicExpansionReading({
    series_components: [
      { ano: 2021, numerador: 100, denominador: 200, percentual: 50 },
      { ano: 2025, numerador: 110, denominador: 300, percentual: 36.7 },
    ],
  })

  assert.equal(reading.publicExpansion, 10)
  assert.equal(reading.totalExpansion, 100)
  assert.equal(reading.currentValue, 10)
  assert.notEqual(reading.currentValue, 36.7)
  assert.equal(reading.status, 'below')
  assert.equal(reading.statusLabel, 'Abaixo do patamar de 50% no recorte recente')
})

test('leitura recente classifica valores acima, abaixo e iguais ao patamar', () => {
  const buildReading = (lastPublic) => buildRecentPublicExpansionReading({
    series_components: [
      { ano: 2021, numerador: 100, denominador: 200 },
      { ano: 2025, numerador: lastPublic, denominador: 300 },
    ],
  })

  const below = buildReading(140)
  const equal = buildReading(150)
  const above = buildReading(160)

  assert.equal(below.currentValue, 40)
  assert.equal(below.status, 'below')
  assert.equal(below.achieved, false)
  assert.equal(equal.currentValue, 50)
  assert.equal(equal.status, 'at-reference')
  assert.equal(equal.achieved, true)
  assert.equal(equal.statusLabel, 'No patamar de 50% no recorte recente')
  assert.equal(above.currentValue, 60)
  assert.equal(above.status, 'above')
  assert.equal(above.achieved, true)
})

test('expansão total zero ou negativa não produz percentual', () => {
  const zero = buildRecentPublicExpansionReading({
    series_components: [
      { ano: 2021, numerador: 100, denominador: 200 },
      { ano: 2025, numerador: 120, denominador: 200 },
    ],
  })
  const negative = buildRecentPublicExpansionReading({
    series_components: [
      { ano: 2021, numerador: 100, denominador: 200 },
      { ano: 2025, numerador: 90, denominador: 180 },
    ],
  })

  for (const reading of [zero, negative]) {
    assert.equal(reading.currentValue, null)
    assert.equal(reading.achieved, null)
    assert.equal(reading.status, 'insufficient')
    assert.equal(reading.statusLabel, 'Sem expansão suficiente para calcular')
  }
})

test('dados ausentes e série insuficiente não são convertidos em zero', () => {
  const missing = buildRecentPublicExpansionReading({
    series_components: [
      { ano: 2021, numerador: 100, denominador: 200 },
      { ano: 2025, numerador: null, denominador: 300 },
    ],
  })
  const insufficient = buildRecentPublicExpansionReading({
    series_components: [
      { ano: 2025, numerador: 110, denominador: 300 },
    ],
  })

  for (const reading of [missing, insufficient]) {
    assert.equal(reading.currentValue, null)
    assert.equal(reading.status, 'insufficient')
    assert.equal(reading.unavailableReason, 'insufficient-series')
  }
})

test('recorte recente usa no máximo os cinco últimos anos comparáveis', () => {
  const reading = buildRecentPublicExpansionReading({
    series_components: [
      { ano: 2019, numerador: 80, denominador: 150 },
      { ano: 2020, numerador: 90, denominador: 170 },
      { ano: 2021, numerador: 100, denominador: 200 },
      { ano: 2022, numerador: 110, denominador: 220 },
      { ano: 2023, numerador: 120, denominador: 240 },
      { ano: 2024, numerador: 130, denominador: 260 },
      { ano: 2025, numerador: 150, denominador: 300 },
    ],
  })

  assert.equal(reading.startYear, 2021)
  assert.equal(reading.endYear, 2025)
  assert.equal(reading.recentSeries.length, 5)
  assert.equal(reading.currentValue, 50)
})

test('modelo compartilhado apresenta período, status e distância do recorte recente', () => {
  const model = buildPne2026AccumulativePresentationModel({
    cycle: CYCLE,
    indicatorKey: 'medio_tecnico_participacao_publica',
    presentationMode: EXPANSION_SHARE_MODE,
    details: {
      series_components: [
        { ano: 2021, numerador: 100, denominador: 200 },
        { ano: 2022, numerador: 110, denominador: 220 },
        { ano: 2023, numerador: 120, denominador: 240 },
        { ano: 2024, numerador: 140, denominador: 270 },
        { ano: 2025, numerador: 162.8, denominador: 300 },
      ],
    },
  })

  assert.equal(model.currentLabel, 'Contexto pré-ciclo')
  assert.equal(model.currentDisplay, '62,8%')
  assert.equal(model.referenceLabel, 'Patamar PNE')
  assert.equal(model.referenceDisplay, '50%')
  assert.equal(model.distanceDisplay, '+12,8 p.p.')
  assert.equal(model.footerText, '2021–2025 · contexto anterior ao novo ciclo')
  assert.equal(model.statusLabel, 'Contexto pré-ciclo')
  assert.equal(model.summaryState, null)
  assert.equal(model.progress, null)
})

test('card e detalhe derivam valores e status do mesmo modelo compartilhado', () => {
  const model = buildPne2026AccumulativePresentationModel({
    cycle: CYCLE,
    indicatorKey: 'medio_tecnico_participacao_publica',
    presentationMode: EXPANSION_SHARE_MODE,
    details: {
      series_components: [
        { ano: 2021, numerador: 100, denominador: 200 },
        { ano: 2025, numerador: 140, denominador: 300 },
      ],
    },
  })

  assert.equal(model.statusLabel, model.detail.statusLabel)
  assert.equal(model.tone, model.detail.tone)
  assert.equal(model.currentDisplay, `${model.detail.composition.currentValue}%`)
  assert.equal(model.detail.metrics[1].value, '100 → 140')
  assert.equal(model.detail.metrics[3].value, '200 → 300')
  assert.equal(model.referenceDisplay, '50%')
  assert.equal(model.statusLabel, 'Contexto pré-ciclo')
  assert.equal(model.summaryState, null)
})

test('modelo compartilhado cobre acima, igual, abaixo e sem cálculo', () => {
  const buildModel = (lastPublic, lastTotal = 300) => buildPne2026AccumulativePresentationModel({
    cycle: CYCLE,
    indicatorKey: 'medio_tecnico_participacao_publica',
    presentationMode: EXPANSION_SHARE_MODE,
    details: {
      series_components: [
        { ano: 2021, numerador: 100, denominador: 200 },
        { ano: 2025, numerador: lastPublic, denominador: lastTotal },
      ],
    },
  })

  assert.equal(buildModel(160).status, 'baseline')
  assert.equal(buildModel(160).summaryState, null)
  assert.equal(buildModel(150).status, 'baseline')
  assert.equal(buildModel(150).summaryState, null)
  assert.equal(buildModel(140).status, 'baseline')
  assert.equal(buildModel(140).summaryState, null)

  const unavailable = buildModel(120, 200)
  assert.equal(unavailable.statusLabel, 'Contexto pré-ciclo')
  assert.equal(unavailable.currentDisplay, '—')
  assert.equal(unavailable.distanceDisplay, '—')
  assert.equal(unavailable.summaryState, null)
})

test('cursos subsequentes apresentam a trajetória absoluta desde a base de 2025', () => {
  const model = buildPne2026AccumulativePresentationModel({
    cycle: CYCLE,
    indicatorKey: 'subsequente_expansao',
    presentationMode: ABSOLUTE_EXPANSION_MODE,
    details: {
      series_total: [
        { ano: 2021, valor: 1900 },
        { ano: 2022, valor: 2000 },
        { ano: 2023, valor: 2050 },
        { ano: 2024, valor: 2100 },
        { ano: 2025, valor: 2185 },
      ],
    },
  })

  assert.equal(model.statusLabel, 'Ponto de partida definido')
  assert.equal(model.currentLabel, 'Valor atual do ciclo')
  assert.equal(model.currentDisplay, '2.185')
  assert.equal(model.referenceLabel, 'Referência 2036')
  assert.equal(model.referenceDisplay, '3.496')
  assert.equal(model.distanceDisplay, 'Faltam 1.311')
  assert.equal(model.comparisonTitle, 'Ponto de partida + expansão necessária = meta 2036')
  assert.equal(model.footerText, 'Ponto de partida · 2025')
  assert.equal(model.summaryState, null)
  assert.equal(model.progress, 0)
  assert.equal(model.detail.composition.mode, ABSOLUTE_EXPANSION_MODE)
  assert.equal(model.detail.composition.missingValue, 1311)
  assert.equal(model.detail.metrics.length, 4)
  assert.equal(model.detail.metrics[0].label, 'Ponto de partida — 2025')
  assert.equal(model.detail.metrics[1].value, '+1.311')
  assert.equal(model.detail.metrics[3].value, 'Começa com os dados de 2026')
  assert.doesNotMatch(model.detail.metrics.map((metric) => `${metric.label} ${metric.value}`).join(' '), /Avanço do ciclo|0%/i)
})

test('cards não contêm mensagens legadas e ambos consumidores usam o mesmo builder', () => {
  const cardSource = readFileSync(new URL('../../src/components/MetaCard.jsx', import.meta.url), 'utf8')
  const detailSource = readFileSync(new URL('../../src/components/IndicatorDetail.jsx', import.meta.url), 'utf8')
  const forbiddenCardCopy = /A partir de 2026|Aguardando expansão|Resultado disponível a partir de 2026|Linha de base definida|Progresso do ciclo/i

  assert.doesNotMatch(cardSource, forbiddenCardCopy)
  assert.match(cardSource, /buildPne2026AccumulativePresentationModel/)
  assert.match(detailSource, /buildPne2026AccumulativePresentationModel/)
})

test('demais cards permanecem fora do modelo acumulativo compartilhado', () => {
  assert.equal(buildPne2026AccumulativePresentationModel({
    cycle: CYCLE,
    indicatorKey: 'eja_integrada_educacao_profissional_percentual',
    details: {},
  }), null)
  assert.equal(buildPne2026AccumulativePresentationModel({
    cycle: 'pne_2014_2024',
    indicatorKey: 'subsequente_expansao',
    details: {},
  }), null)
})
