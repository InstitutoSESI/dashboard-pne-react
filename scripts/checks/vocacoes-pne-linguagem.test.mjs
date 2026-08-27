import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

import {
  lintCard,
  lintText,
  loadVocabulario,
} from '../lib/vocacoes-pne-linter.mjs'

const fixtureDirectory = new URL('./fixtures/vocacoes-pne/', import.meta.url)
const vocab = loadVocabulario()
const examples = JSON.parse(
  readFileSync(new URL('exemplos-cartoes.json', fixtureDirectory), 'utf8'),
)

function formatViolations(violations) {
  return violations
    .map(({ ruleId, field, excerpt }) => `${ruleId} @ ${field}: ${excerpt}`)
    .join('\n')
}

test('vocabulário carrega com regras RegExp iu e ids únicos', () => {
  const ids = vocab.regras.map(({ id }) => id)
  assert.equal(new Set(ids).size, ids.length)
  for (const rule of vocab.regras) {
    assert.ok(rule.regex instanceof RegExp, `${rule.id} não foi compilada`)
    assert.equal(rule.regex.flags, 'iu', `${rule.id} usa flags inesperadas`)
  }
})

test('cada regra captura o próprio exemplo bloqueado', () => {
  for (const rule of vocab.regras) {
    const observed = lintText(rule.exemploBloqueado, vocab).map(({ ruleId }) => ruleId)
    assert.ok(
      observed.includes(rule.id),
      `${rule.id} não capturou: ${rule.exemploBloqueado}`,
    )
  }
})

test('cartões aprovados não têm violações de linguagem', () => {
  for (const card of examples.aprovados) {
    const violations = lintCard(card, vocab)
    assert.deepEqual(
      violations,
      [],
      `${card.id} falhou:\n${formatViolations(violations)}`,
    )
  }
})

test('cartões reprovados contêm todos os ruleIds de linguagem esperados', () => {
  for (const item of examples.reprovados.filter(({ expected }) => expected.linter.length > 0)) {
    const violations = lintCard(item.card, vocab)
    const observed = new Set(violations.map(({ ruleId }) => ruleId))
    for (const expectedRuleId of item.expected.linter) {
      assert.ok(
        observed.has(expectedRuleId),
        `${item.card.id} não capturou ${expectedRuleId}:\n${formatViolations(violations)}`,
      )
    }
  }
})

test('campos internos não são lintados', () => {
  const card = structuredClone(examples.aprovados[0])
  card.internal.mechanism_id = 'shift-share de Bennett'
  assert.deepEqual(lintCard(card, vocab), [])
})

test('guardas de falso positivo passam sem violação', () => {
  for (const phrase of vocab.guardasFalsoPositivo) {
    assert.deepEqual(
      lintText(phrase, vocab),
      [],
      `falso positivo em: ${phrase}`,
    )
  }
})
