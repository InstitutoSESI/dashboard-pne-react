import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

import {
  validateCardCatalog,
  validatePair,
} from '../lib/vocacoes-pne-compatibilidade.mjs'
import {
  assertCrossReferences,
  loadCatalogoMecanismos,
  loadCatalogoReferencias,
  loadRegistroSeries,
  loadRegrasUniverso,
} from '../lib/vocacoes-pne-registro.mjs'

const fixtureDirectory = new URL('./fixtures/vocacoes-pne/', import.meta.url)
const mecanismos = loadCatalogoMecanismos()
const referencias = loadCatalogoReferencias()
const registro = loadRegistroSeries()
const regras = loadRegrasUniverso()
const examples = JSON.parse(
  readFileSync(new URL('exemplos-cartoes.json', fixtureDirectory), 'utf8'),
)
const valeDoSinos = JSON.parse(
  readFileSync(
    new URL('../../public/data/vocacoes-regiao/regioes/vale-do-sinos.json', import.meta.url),
    'utf8',
  ),
)
const pairDependencies = { mecanismos, registro, regras }
const cardDependencies = { mecanismos, referencias }

test('loaders e referências cruzadas dos mecanismos são válidos', () => {
  assert.equal(
    assertCrossReferences({ mecanismos, registro, referencias }),
    true,
  )
})

test('catálogo contém os 16 mecanismos e as sete famílias com forma completa', () => {
  const entries = mecanismos.mecanismos
  assert.equal(mecanismos.version, '1.2.0')
  assert.equal(entries.length, 16)
  assert.equal(new Set(entries.map(({ id }) => id)).size, entries.length)
  assert.deepEqual(
    [...new Set(entries.map(({ familia }) => familia))].sort(),
    ['M1', 'M2', 'M3', 'M4', 'M5', 'M6', 'M7'],
  )

  const availability = new Set([
    'disponivel',
    'disponivel_pesquisa',
    'parcial',
    'pendente',
  ])
  for (const mechanism of entries) {
    for (const field of [
      'utilidadePlanejamento',
      'leituraPublicaMaxima',
      'justificativa',
    ]) {
      assert.ok(mechanism[field].trim().length > 0, `${mechanism.id}.${field}`)
    }
    assert.ok(
      availability.has(mechanism.disponibilidade),
      `${mechanism.id}.disponibilidade`,
    )
    if (mechanism.disponibilidade === 'pendente') {
      assert.ok(
        mechanism.observacaoDisponibilidade.trim().length > 0,
        `${mechanism.id}.observacaoDisponibilidade`,
      )
    }
  }
})

test('mecanismos destravados, inclusive M4 e M5, estão disponíveis na pesquisa', () => {
  const availabilityById = new Map(
    mecanismos.mecanismos.map(({ id, disponibilidade }) => [id, disponibilidade]),
  )
  for (const mechanismId of [
    'M2-trabalho-juvenil',
    'M3-eja-publico',
    'M4-ocupacoes',
    'M5-deslocamento-estudo',
    'M6-tempo-integral',
  ]) {
    assert.equal(
      availabilityById.get(mechanismId),
      'disponivel_pesquisa',
      mechanismId,
    )
  }
  assert.deepEqual(
    mecanismos.mecanismos.find(({ id }) => id === 'M4-ocupacoes').fontesAtuais,
    ['rais-por-cbo (base local 058)', 'correspondencia-cursos-cbo-rs-v1'],
  )
  assert.deepEqual(
    mecanismos.mecanismos.find(({ id }) => id === 'M5-deslocamento-estudo').fontesAtuais,
    ['censo-demografico-2022'],
  )
  assert.match(
    mecanismos.mecanismos
      .find(({ id }) => id === 'M3-eja-publico')
      .observacaoDisponibilidade,
    /18 anos ou mais \(D-R3-2\)/u,
  )
})

test('corpus usa mecanismos conhecidos e direções permitidas nos cinco aprovados', () => {
  const mechanismById = new Map(
    mecanismos.mecanismos.map((mechanism) => [mechanism.id, mechanism]),
  )
  const corpusCards = [
    ...examples.aprovados,
    ...examples.reprovados.map(({ card }) => card),
  ]

  for (const card of corpusCards) {
    assert.ok(
      mechanismById.has(card.internal.mechanism_id),
      `${card.id}: ${card.internal.mechanism_id}`,
    )
  }
  assert.equal(examples.aprovados.length, 5)
  for (const card of examples.aprovados) {
    assert.ok(
      mechanismById.get(card.internal.mechanism_id).direcoes.includes(card.direction),
      `${card.id}: ${card.direction}`,
    )
  }
})

test('cinco cartões aprovados não têm violações de catálogo', () => {
  for (const card of examples.aprovados) {
    assert.deepEqual(
      validateCardCatalog(card, cardDependencies),
      [],
      card.id,
    )
  }
})

test('cartões sintéticos exercitam todas as violações do catálogo', () => {
  const base = structuredClone(examples.aprovados[0])

  const unknownMechanism = structuredClone(base)
  unknownMechanism.internal.mechanism_id = 'M0-inexistente'
  assert.ok(
    validateCardCatalog(unknownMechanism, cardDependencies)
      .some(({ ruleId }) => ruleId === 'mecanismo-desconhecido'),
  )

  const emptyMechanism = structuredClone(base)
  emptyMechanism.internal.mechanism_id = '   '
  assert.equal(
    validateCardCatalog(emptyMechanism, cardDependencies)
      .some(({ ruleId }) => ruleId === 'mecanismo-desconhecido'),
    false,
  )

  const invalidDirection = structuredClone(base)
  invalidDirection.internal.mechanism_id = 'M1-envelhecimento-rede'
  invalidDirection.direction = 'educacao_para_territorio'
  assert.ok(
    validateCardCatalog(invalidDirection, cardDependencies)
      .some(({ ruleId }) => ruleId === 'direcao-nao-permitida'),
  )

  const outsideCatalog = structuredClone(base)
  outsideCatalog.pne_topics = ['   ']
  outsideCatalog.sources = ['Fonte inexistente']
  const outsideRuleIds = new Set(
    validateCardCatalog(outsideCatalog, cardDependencies)
      .map(({ ruleId }) => ruleId),
  )
  assert.ok(outsideRuleIds.has('item-fora-do-catalogo:pne_topics[0]'))
  assert.ok(outsideRuleIds.has('item-fora-do-catalogo:sources[0]'))

  const duplicateItem = structuredClone(base)
  duplicateItem.monitoring_indicators = [
    base.monitoring_indicators[0],
    base.monitoring_indicators[0],
  ]
  assert.ok(
    validateCardCatalog(duplicateItem, cardDependencies)
      .some(({ ruleId }) => ruleId === 'item-duplicado:monitoring_indicators'),
  )
})

test('default-deny bloqueia os oito pares de triagem em todos os mecanismos', () => {
  const screenedRelations = valeDoSinos.screenedRelations.items
  const seriesById = new Map(registro.series.map((series) => [series.seriesId, series]))
  assert.equal(screenedRelations.length, 8)

  for (const relation of screenedRelations) {
    const pairSeries = [relation.seriesAId, relation.seriesBId]
    const educational = pairSeries.filter(
      (seriesId) => seriesById.get(seriesId)?.universo === 'matriculas_localizadas',
    )
    assert.equal(educational.length, 1, relation.relationId)
    const educationalSeriesId = educational[0]
    const territorialSeriesId = pairSeries.find(
      (seriesId) => seriesId !== educationalSeriesId,
    )

    for (const mechanism of mecanismos.mecanismos) {
      const result = validatePair(
        { educationalSeriesId, territorialSeriesId, mechanismId: mechanism.id },
        pairDependencies,
      )
      assert.equal(
        result.allowed,
        false,
        `${relation.relationId} foi aceito por ${mechanism.id}`,
      )
    }
  }
})

test('P3 usa exatamente faixa-etaria-incompativel antes do default-deny', () => {
  const result = validatePair(
    {
      educationalSeriesId: 'matriculas-no-ensino-medio',
      territorialSeriesId: 'populacao-de-0-a-14-anos',
      mechanismId: 'M1-coorte-15-17',
    },
    pairDependencies,
  )
  assert.equal(result.allowed, false)
  assert.equal(result.reasonCode, 'faixa-etaria-incompativel')
})
