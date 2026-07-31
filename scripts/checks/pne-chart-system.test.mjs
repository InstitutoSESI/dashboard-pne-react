import assert from 'node:assert/strict'
import test from 'node:test'

import { getBoundedDomain } from '../../src/utils/chartDomain.js'
import {
  buildObservedPercentageScale,
  buildPneAbsoluteScale,
  buildPnePercentScale,
  buildPneStackedScale,
  resolvePneAuxiliaryYearTickLimit,
  selectPneYearTicks,
} from '../../src/utils/pneChartSystem.js'

test('escala percentual observada preserva detalhes de séries municipais baixas', () => {
  assert.deepEqual(buildObservedPercentageScale([0, 0.8, 1]), {
    domain: { min: 0, max: 5, isPercent: true, observed: true },
    ticks: [0, 1, 2, 3, 4, 5],
  })

  assert.equal(buildObservedPercentageScale([5.8]).domain.max, 10)
  assert.equal(buildObservedPercentageScale([10]).domain.max, 12.5)
})

test('percentuais regulares usam a escala fixa de 0 a 100', () => {
  assert.deepEqual(buildPnePercentScale([23, 27, 60]), {
    domain: { min: 0, max: 100, isPercent: true },
    ticks: [0, 25, 50, 75, 100],
  })
})

test('percentuais acima de 100 preservam o valor e recebem folga', () => {
  const scale = buildPnePercentScale([82, 127])
  assert.equal(scale.domain.min, 0)
  assert.equal(scale.domain.max % 10, 0)
  assert.ok(scale.domain.max >= 127 * 1.1)
  assert.equal(scale.ticks.length, 6)
})

test('domínio educacional também preserva percentuais acima de 100 por padrão', () => {
  const domain = getBoundedDomain([88, 103.4, 121], 'percent')
  assert.equal(domain.min >= 0, true)
  assert.ok(domain.max > 121)

  const bounded = getBoundedDomain([88, 103.4], 'percent', {
    allowPercentOverflow: false,
  })
  assert.equal(bounded.max, 100)
})

test('séries absolutas partem de zero e geram de quatro a cinco marcas inteiras', () => {
  const scale = buildPneAbsoluteScale([678, 1139, 836])
  assert.equal(scale.domain.min, 0)
  assert.ok(scale.domain.max >= 1139 * 1.12)
  assert.ok(scale.ticks.length >= 4 && scale.ticks.length <= 5)
  assert.ok(scale.ticks.every(Number.isInteger))
})

test('barras empilhadas calculam o limite pelo total anual', () => {
  const scale = buildPneStackedScale([
    { municipal: 700, privada: 300 },
    { municipal: 850, privada: 350 },
  ], ['municipal', 'privada'])
  assert.ok(scale.domain.max >= 1200 * 1.12)
})

test('seleção responsiva de anos mantém início e fim da série', () => {
  const years = Array.from({ length: 12 }, (_, index) => ({ year: 2015 + index }))
  const selected = selectPneYearTicks(years, 4)
  assert.deepEqual(selected.map((point) => point.year), [2015, 2019, 2023, 2026])
})

test('eixos temporais priorizam cadências regulares de dois a quatro anos', () => {
  const longSeries = Array.from({ length: 23 }, (_, index) => ({ year: 2014 + index }))
  const shortSeries = Array.from({ length: 7 }, (_, index) => ({ year: 2019 + index }))

  assert.deepEqual(
    selectPneYearTicks(longSeries, 7).map((point) => point.year),
    [2014, 2018, 2022, 2026, 2030, 2036],
  )
  assert.deepEqual(
    selectPneYearTicks(shortSeries, 6).map((point) => point.year),
    [2019, 2021, 2023, 2025],
  )
})

test('marca terminal não colide com um ano intermediário muito próximo', () => {
  const years = Array.from({ length: 23 }, (_, index) => ({ year: 2014 + index }))
  const selected = selectPneYearTicks(years, 7).map((point) => point.year)

  assert.equal(selected.at(-1), 2036)
  assert.ok(selected.at(-1) - selected.at(-2) >= 3)
})

test('gráficos auxiliares compactos reduzem a densidade de anos', () => {
  assert.equal(resolvePneAuxiliaryYearTickLimit(280), 3)
  assert.equal(resolvePneAuxiliaryYearTickLimit(317), 4)
  assert.equal(resolvePneAuxiliaryYearTickLimit(460), 6)
  assert.equal(resolvePneAuxiliaryYearTickLimit(317, 3), 3)
})
