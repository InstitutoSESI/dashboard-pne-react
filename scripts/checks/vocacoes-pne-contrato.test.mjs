import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

import {
  loadVocabulario,
  serializePublic,
  validateCardContract,
  validateCardSet,
} from '../lib/vocacoes-pne-linter.mjs'

const fixtureDirectory = new URL('./fixtures/vocacoes-pne/', import.meta.url)
const vocab = loadVocabulario(new URL('vocabulario.json', fixtureDirectory))
const examples = JSON.parse(
  readFileSync(new URL('exemplos-cartoes.json', fixtureDirectory), 'utf8'),
)
const internalKeys = new Set([
  'internal',
  'mechanism_id',
  'universe_check',
  'temporal_check',
  'sensitivity_check',
  'territorial_check',
  'publication_decision',
  'transformation_class',
  'future_basis',
])

function collectInternalKeyPaths(value, field = '') {
  if (Array.isArray(value)) {
    return value.flatMap(
      (item, index) => collectInternalKeyPaths(item, `${field}[${index}]`),
    )
  }
  if (value === null || typeof value !== 'object') return []

  return Object.entries(value).flatMap(([key, child]) => {
    const childField = field ? `${field}.${key}` : key
    return [
      ...(internalKeys.has(key) ? [childField] : []),
      ...collectInternalKeyPaths(child, childField),
    ]
  })
}

test('cartões aprovados atendem ao contrato', () => {
  for (const card of examples.aprovados) {
    assert.deepEqual(
      validateCardContract(card),
      [],
      `violações inesperadas em ${card.id}`,
    )
  }
})

test('cartões reprovados contêm todos os ruleIds de contrato esperados', () => {
  for (const item of examples.reprovados.filter(({ expected }) => expected.contrato.length > 0)) {
    const violations = validateCardContract(item.card)
    const observed = new Set(violations.map(({ ruleId }) => ruleId))
    for (const expectedRuleId of item.expected.contrato) {
      assert.ok(
        observed.has(expectedRuleId),
        `${item.card.id} não produziu ${expectedRuleId}: ${JSON.stringify(violations)}`,
      )
    }
  }
})

test('serializePublic preserva campos públicos e remove qualquer campo fora da allowlist', () => {
  for (const card of examples.aprovados) {
    const serialized = serializePublic(card)
    const reparsed = JSON.parse(JSON.stringify(serialized))
    assert.deepEqual(collectInternalKeyPaths(reparsed), [], card.id)
    assert.deepEqual(
      Object.keys(serialized),
      Object.keys(card).filter((key) => key !== 'internal'),
      `${card.id} teve campos públicos divergentes`,
    )
    for (const field of Object.keys(serialized)) {
      assert.equal(
        JSON.stringify(serialized[field]),
        JSON.stringify(card[field]),
        `${card.id}.${field} não foi preservado byte a byte`,
      )
    }
  }

  const cardWithExtraField = { ...structuredClone(examples.aprovados[0]), score: 1 }
  assert.equal(Object.hasOwn(serializePublic(cardWithExtraField), 'score'), false)
})

test('mínimos e máximos controlam a publicação do conjunto', () => {
  const approved = structuredClone(examples.aprovados)
  const complete = validateCardSet(approved, vocab)
  assert.equal(complete.publishable, true)
  assert.deepEqual(complete.counts.porDirecao, {
    educacao_para_territorio: 3,
    territorio_para_educacao: 2,
  })

  const withoutFirstDirection = approved.filter((_, index) => index !== 0)
  assert.equal(validateCardSet(withoutFirstDirection, vocab).publishable, false)

  const withoutSecondDirection = approved.filter((_, index) => index !== 3)
  assert.equal(validateCardSet(withoutSecondDirection, vocab).publishable, false)

  const sixFirstDirection = [
    ...approved,
    ...Array.from({ length: 3 }, (_, index) => ({
      ...structuredClone(approved[0]),
      id: `${approved[0].id}-extra-${index + 1}`,
    })),
  ]
  const aboveMaximum = validateCardSet(sixFirstDirection, vocab)
  assert.equal(aboveMaximum.counts.porDirecao.educacao_para_territorio, 6)
  assert.equal(aboveMaximum.publishable, false)
})

test('cartão retido não entra na contagem publicável', () => {
  const cards = structuredClone(examples.aprovados)
  cards[0].internal.publication_decision = 'retida'
  const result = validateCardSet(cards, vocab)
  assert.equal(result.counts.porDirecao.educacao_para_territorio, 2)
  assert.equal(result.publishable, false)
})

test('decisão publicada é incoerente com check interno diferente de ok', () => {
  const published = structuredClone(examples.aprovados[0])
  published.internal.universe_check = 'incompativel'
  assert.ok(
    validateCardContract(published).some(({ ruleId }) => ruleId === 'decisao-incoerente'),
  )

  const retained = structuredClone(published)
  retained.internal.publication_decision = 'retida'
  assert.equal(
    validateCardContract(retained).some(({ ruleId }) => ruleId === 'decisao-incoerente'),
    false,
  )
})
