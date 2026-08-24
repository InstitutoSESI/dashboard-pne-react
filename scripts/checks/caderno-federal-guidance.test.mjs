import test from 'node:test'
import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'
import { registerHooks } from 'node:module'
import { fileURLToPath, pathToFileURL } from 'node:url'
import path from 'node:path'
import writeXlsxFile from 'write-excel-file/node'

import { PNE_2026_FEDERAL_GUIDANCE } from '../../src/data/pne2026FederalGuidance.js'
import { cadernoFrontKey } from '../../src/domain/cadernoFrontsStorage.ts'
import {
  FACTOR_GUIDANCE,
  resolveFactorGuidance,
} from '../../src/features/caderno/cadernoFederalGuidance.ts'
import { FACTOR_TITLE } from '../../src/features/caderno/cadernoPlainLanguage.ts'

registerHooks({
  resolve(specifier, context, nextResolve) {
    if (context.parentURL?.startsWith('file:') && specifier.endsWith('.js')) {
      const sourceUrl = new URL(specifier.replace(/\.js$/, '.ts'), context.parentURL)
      if (existsSync(fileURLToPath(sourceUrl))) {
        return { shortCircuit: true, url: pathToFileURL(fileURLToPath(sourceUrl)).href }
      }
    }
    return nextResolve(specifier, context)
  },
})

const {
  buildCadernoDecisionWorkbook,
  buildCadernoFederalGuidanceRows,
  CADERNO_DECISION_COLUMNS,
} = await import('../../src/features/caderno/cadernoDecisionWorkbook.ts')

const repoRoot = fileURLToPath(new URL('../..', import.meta.url))
const pilotArtifact = JSON.parse(
  readFileSync(
    path.join(
      repoRoot,
      'public',
      'data',
      'pne2026-caderno',
      'municipios',
      '4313375.json',
    ),
    'utf8',
  ),
)
const publishedGoalIds = new Set(pilotArtifact.goals.map((goal) => goal.goalId))
const allowedHosts = Object.freeze([
  'camara.leg.br',
  'www2.camara.leg.br',
  'planalto.gov.br',
  'gov.br',
  'www.gov.br',
  'pne.mec.gov.br',
  'in.gov.br',
])
const expectedDecisionColumns = Object.freeze([
  'municipality_ibge7',
  'municipality_name',
  'uf',
  'decision_cycle',
  'goal_id',
  'indicator_id',
  'factor_id',
  'diagnostic_reference_date',
  'public_deliberation_class_at_decision',
  'municipal_weight_profile',
  'action_decision',
  'action_description',
  'responsible',
  'partners',
  'deadline',
  'budget_nominal',
  'budget_share_of_available',
  'process_indicator',
  'outcome_indicator',
  'baseline',
  'action_target',
  'decision_justification',
  'workshop_date',
  'participants',
  'review_date',
  'notes',
])

function firstHypothesis(goal) {
  for (const hypotheses of Object.values(goal.hypotheses)) {
    if (hypotheses[0]) return hypotheses[0]
  }
  throw new Error(`Objetivo ${goal.goalId} sem hipótese para o teste`)
}

function assertOfficialHttpsUrl(rawUrl) {
  const url = new URL(rawUrl)
  assert.equal(url.protocol, 'https:', `URL sem HTTPS: ${rawUrl}`)
  assert.ok(
    allowedHosts.some(
      (host) => url.hostname === host || url.hostname.endsWith(`.${host}`),
    ),
    `Host não permitido: ${url.hostname}`,
  )
}

function sentenceCount(text) {
  return (text.match(/[.!?](?=\s|$)/g) ?? []).length
}

test('the federal guidance tests use the curated v2 artifact, including context-only goals', () => {
  assert.equal(pilotArtifact.schemaVersion, 'pne2026-caderno-v2')
  assert.equal(pilotArtifact.workbookSchemaVersion, 'pne-priority-hypothesis-workbook-v2')
  for (const goalId of ['15', '16']) {
    const goal = pilotArtifact.goals.find((candidate) => candidate.goalId === goalId)
    const hypothesisCount = Object.values(goal.hypotheses).reduce(
      (total, hypotheses) => total + hypotheses.length,
      0,
    )
    assert.equal(hypothesisCount, 0)
    assert.ok(PNE_2026_FEDERAL_GUIDANCE[goalId])
  }
})

test('every factor guidance key has a public factor title', () => {
  const missing = Object.keys(FACTOR_GUIDANCE).filter((factorId) => !FACTOR_TITLE[factorId])
  assert.deepEqual(missing, [])
  assert.equal(Object.keys(FACTOR_GUIDANCE).length, 37)
})

test('every federal goal guidance key is published by the pilot artifact', () => {
  const guidanceGoalIds = Object.keys(PNE_2026_FEDERAL_GUIDANCE)
  const missing = guidanceGoalIds.filter((goalId) => !publishedGoalIds.has(goalId))
  assert.deepEqual(missing, [])
  assert.equal(guidanceGoalIds.length, 17)
})

test('all guidance URLs are HTTPS and use an allowed official host', () => {
  for (const entry of Object.values(PNE_2026_FEDERAL_GUIDANCE)) {
    for (const source of entry.sources) assertOfficialHttpsUrl(source.url)
  }
  for (const entry of Object.values(FACTOR_GUIDANCE)) {
    for (const reference of entry.references) assertOfficialHttpsUrl(reference.url)
  }
})

test('unknown factor guidance resolves to null without throwing', () => {
  assert.doesNotThrow(() => resolveFactorGuidance('F_UNKNOWN'))
  assert.equal(resolveFactorGuidance('F_UNKNOWN'), null)
})

test('workbook preserves the exact 26 research-template columns in its first sheet', async () => {
  const goal = pilotArtifact.goals[0]
  const hypothesis = firstHypothesis(goal)
  const selectedKeys = [cadernoFrontKey(goal.goalId, hypothesis.factorId)]
  const workbook = buildCadernoDecisionWorkbook(pilotArtifact, selectedKeys)

  assert.equal(expectedDecisionColumns.length, 26)
  assert.deepEqual([...CADERNO_DECISION_COLUMNS], expectedDecisionColumns)
  assert.deepEqual(
    workbook.sheets[0].data[0].map((header) => header.value),
    expectedDecisionColumns,
  )
  assert.deepEqual(
    workbook.sheets.map(({ sheet }) => sheet),
    ['Frentes da oficina', 'Orientação federal'],
  )
  const buffer = await writeXlsxFile(workbook.sheets, {
    fontFamily: 'Arial',
    fontSize: 10,
  }).toBuffer()
  assert.equal(buffer.subarray(0, 4).toString('hex'), '504b0304')
})

test('federal guidance sheet has one correctly identified row per selected front', () => {
  const selectedFronts = pilotArtifact.goals.slice(0, 2).map((goal) => {
    const hypothesis = firstHypothesis(goal)
    return {
      factorId: hypothesis.factorId,
      goalId: goal.goalId,
      key: cadernoFrontKey(goal.goalId, hypothesis.factorId),
    }
  })

  const rows = buildCadernoFederalGuidanceRows(
    pilotArtifact,
    selectedFronts.map(({ key }) => key),
  )

  assert.equal(rows.length, selectedFronts.length)
  assert.deepEqual(
    rows.map((row) => ({ factorId: row.factor_id, goalId: row.goal_id })),
    selectedFronts.map(({ factorId, goalId }) => ({ factorId, goalId })),
  )
  for (const row of rows) {
    assert.equal(row.causa, FACTOR_TITLE[row.factor_id])
    assert.ok(row.orientacao_meta)
    assert.ok(row.orientacao_causa)
    assert.match(row.referencias, / — https:\/\//)
  }
})

test('federal guidance rows use empty cells and artifact title when guidance is absent', () => {
  const sourceGoal = pilotArtifact.goals[0]
  const sourceHypothesis = firstHypothesis(sourceGoal)
  const unknownGoal = {
    ...sourceGoal,
    goalId: '999',
    legalGoals: [{ legalGoalId: '999.a', title: 'Objetivo sem orientação federal' }],
    hypotheses: {
      adverse_signal: [{
        ...sourceHypothesis,
        factorId: 'F_UNKNOWN',
        name: 'Nome da causa no artefato',
      }],
      no_public_data: [],
      protective_present: [],
    },
  }
  const cadernoWithoutGuidance = { ...pilotArtifact, goals: [unknownGoal] }
  const selectedKeys = [cadernoFrontKey('999', 'F_UNKNOWN')]

  let rows
  assert.doesNotThrow(() => {
    rows = buildCadernoFederalGuidanceRows(cadernoWithoutGuidance, selectedKeys)
  })
  assert.deepEqual(rows, [{
    goal_id: '999',
    objetivo: 'Objetivo sem orientação federal',
    factor_id: 'F_UNKNOWN',
    causa: 'Nome da causa no artefato',
    orientacao_meta: '',
    orientacao_causa: '',
    referencias: '',
  }])
})

test('guidance summaries and factor texts are not empty', () => {
  for (const [goalId, entry] of Object.entries(PNE_2026_FEDERAL_GUIDANCE)) {
    assert.ok(entry.summary.trim(), `Resumo vazio no objetivo ${goalId}`)
    assert.ok(
      sentenceCount(entry.summary) >= 2 && sentenceCount(entry.summary) <= 4,
      `Resumo fora do limite de 2 a 4 frases no objetivo ${goalId}`,
    )
    assert.ok(entry.strategies.length >= 3 && entry.strategies.length <= 6)
    for (const strategy of entry.strategies) {
      assert.match(strategy.ref, /^(?:Meta \d+\.[a-z]|Estratégia \d+\.\d+)$/)
      assert.ok(strategy.text.trim())
    }
    assert.ok(entry.sources.length >= 1)
  }
  for (const [factorId, entry] of Object.entries(FACTOR_GUIDANCE)) {
    assert.ok(entry.text.trim(), `Orientação vazia no fator ${factorId}`)
    assert.ok(
      sentenceCount(entry.text) >= 1 && sentenceCount(entry.text) <= 3,
      `Orientação fora do limite de 1 a 3 frases no fator ${factorId}`,
    )
    assert.ok(entry.references.length >= 1 && entry.references.length <= 2)
  }
})
