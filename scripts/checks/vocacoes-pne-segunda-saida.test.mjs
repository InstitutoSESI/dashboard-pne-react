import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { readFileSync } from 'node:fs'
import test from 'node:test'

import { buildExpectedOutput } from '../generate-vocacoes-pne-segunda-saida.mjs'
import {
  derivePublicationDecision,
  GATE_IDS,
  SegundaSaidaError,
  validateResearchArtifact,
  validateSecondOutputArtifact,
} from '../lib/vocacoes-pne-segunda-saida.mjs'
import {
  lintCard,
  loadVocabulario,
  validateCardContract,
} from '../lib/vocacoes-pne-linter.mjs'
import {
  loadCatalogoMecanismos,
  loadCatalogoReferencias,
  loadRegistroSeries,
  loadRegrasUniverso,
} from '../lib/vocacoes-pne-registro.mjs'

const fixtureDirectory = new URL('./fixtures/vocacoes-pne/', import.meta.url)
const researchUrl = new URL(
  'segunda-saida-pesquisa-vale-do-sinos.json',
  fixtureDirectory,
)
const outputUrl = new URL('segunda-saida-vale-do-sinos.json', fixtureDirectory)
const researchBytes = readFileSync(researchUrl)
const research = JSON.parse(researchBytes.toString('utf8'))
const output = JSON.parse(readFileSync(outputUrl, 'utf8'))
const mecanismos = loadCatalogoMecanismos()
const referencias = loadCatalogoReferencias()
const dependencies = {
  vocab: loadVocabulario(),
  pairDependencies: {
    mecanismos,
    registro: loadRegistroSeries(),
    regras: loadRegrasUniverso(),
  },
  cardDependencies: { mecanismos, referencias },
}
const candidateById = new Map(
  research.candidates.map((candidate) => [candidate.id, candidate]),
)

function fact(candidateId, suffix) {
  return candidateById.get(candidateId).facts
    .find(({ id }) => id === `${candidateId}.${suffix}`)
}

function assertNearlyEqual(observed, expected, tolerance = 1e-8) {
  assert.ok(
    Math.abs(observed - expected) <= tolerance,
    `${observed} difere de ${expected}`,
  )
}

function assertResearchRejected(mutator) {
  const mutated = structuredClone(research)
  mutator(mutated)
  assert.throws(
    () => validateResearchArtifact(mutated, dependencies.pairDependencies),
    SegundaSaidaError,
  )
}

function assertOutputRejected(mutator) {
  const mutated = structuredClone(output)
  mutator(mutated)
  assert.throws(
    () => validateSecondOutputArtifact(mutated, research, dependencies),
    SegundaSaidaError,
  )
}

test('artefato final é determinístico e idêntico ao gerador', () => {
  const expected = buildExpectedOutput()
  assert.deepEqual(output, expected)
  assert.equal(
    readFileSync(outputUrl, 'utf8'),
    `${JSON.stringify(expected, null, 2)}\n`,
  )
  assert.equal(validateResearchArtifact(research, dependencies.pairDependencies), true)
  assert.equal(validateSecondOutputArtifact(output, research, dependencies), true)
})

test('handshake registra hash, tamanho e manifesto exatos da pesquisa', () => {
  assert.deepEqual(output.researchArtifact, {
    path: 'scripts/checks/fixtures/vocacoes-pne/segunda-saida-pesquisa-vale-do-sinos.json',
    sha256: createHash('sha256').update(researchBytes).digest('hex'),
    byteSize: researchBytes.length,
  })
  assert.equal(research.sourceManifest.length, 30)
  assert.equal(
    new Set(research.sourceManifest.map(({ path }) => path)).size,
    research.sourceManifest.length,
  )
  assert.ok(
    research.sourceManifest.every(({ sha256 }) => /^[a-f0-9]{64}$/u.test(sha256)),
  )
})

test('identidade regional preserva os dez códigos IBGE textuais', () => {
  assert.equal(research.region.slug, 'vale-do-sinos')
  assert.equal(research.region.stateCode, 'RS')
  assert.deepEqual(
    research.region.municipalities.map(({ ibge7 }) => ibge7),
    [
      '4303905',
      '4306403',
      '4307609',
      '4307708',
      '4310801',
      '4313375',
      '4313409',
      '4314803',
      '4318705',
      '4320008',
    ],
  )
})

test('motor aprova duas agendas e retém três candidatas silenciosamente', () => {
  assert.deepEqual(research.summary, {
    candidateCount: 5,
    readyForAuthorshipCount: 2,
    readyForAuthorshipIds: ['vds-coortes-rede', 'vds-deslocamento-oferta'],
    retainedCount: 3,
    retainedIds: [
      'vds-ocupacoes-formacao',
      'vds-rede-rural',
      'vds-escolaridade-emprego-eja',
    ],
    technicalGate7: 'aprovado',
    technicalGate8: 'aprovado',
  })
  assert.deepEqual(output.summary, {
    candidateCount: 5,
    publishedCount: 2,
    retainedCount: 3,
    gate7: 'aprovado',
    gate8: 'aprovado',
  })
  for (const id of research.summary.readyForAuthorshipIds) {
    const candidate = candidateById.get(id)
    assert.equal(candidate.gates.G8.status, 'pendente_autoria')
    assert.ok(
      GATE_IDS.filter((gateId) => gateId !== 'G8')
        .every((gateId) => candidate.gates[gateId].status === 'ok'),
    )
  }
  for (const id of research.summary.retainedIds) {
    const candidate = candidateById.get(id)
    assert.equal(candidate.engineDecision, 'retida')
    assert.deepEqual(candidate.facts, [])
    assert.equal(
      Object.values(candidate.gates)
        .filter(({ status }) => status === 'reprovado').length,
      1,
    )
  }
  const publicIds = new Set(output.publicProjection.map(({ id }) => id))
  assert.ok(output.retainedCandidates.every(({ candidateId }) => !publicIds.has(candidateId)))
})

test('base futura usa somente série observada ou fotografia observada', () => {
  const coortes = candidateById.get('vds-coortes-rede').futureBasis
  const mobility = candidateById.get('vds-deslocamento-oferta').futureBasis
  assert.deepEqual(
    [coortes.basisType, coortes.supportsTrend, coortes.scenarioId, coortes.futureNumericValues],
    ['observed_series', true, null, []],
  )
  assert.deepEqual(
    [mobility.basisType, mobility.supportsTrend, mobility.scenarioId, mobility.futureNumericValues],
    ['observed_snapshot', false, null, []],
  )
  assert.equal(research.generation.scenarioUsed, false)
  assert.ok(output.cards.every((card) => (
    card.internal.future_basis.scenarioId === null
    && card.internal.future_basis.futureNumericValues.length === 0
  )))
})

test('contrato genérico recusa base futura incoerente ou cenário sem id', () => {
  const mutations = [
    (card) => { card.internal.future_basis.futureNumericValues = [1] },
    (card) => { card.internal.future_basis.supportsTrend = false },
    (card) => {
      card.internal.transformation_class = 'mudanca_observada'
      card.internal.future_basis.basisType = 'observed_series'
    },
    (card) => {
      card.internal.transformation_class = 'cenario'
      card.internal.future_basis.basisType = 'scenario'
      card.internal.future_basis.supportsTrend = false
      card.internal.future_basis.scenarioId = null
    },
  ]
  for (const mutate of mutations) {
    const card = structuredClone(output.cards[0])
    mutate(card)
    assert.ok(validateCardContract(card).some(
      ({ ruleId }) => ruleId === 'campo-obrigatorio:internal.future_basis',
    ))
  }
})

test('coortes, nascimentos, rede e matrículas por etapa são recomputáveis', () => {
  const population = fact('vds-coortes-rede', 'populacao-0-14').values
  const births = fact('vds-coortes-rede', 'nascimentos').values
  const schools = fact('vds-coortes-rede', 'rede').values
  const enrollments = fact('vds-coortes-rede', 'matriculas-etapas').values.entries
  assert.deepEqual(
    [population.start, population.end, population.absoluteChange],
    [184806, 165142, -19664],
  )
  assertNearlyEqual(population.percentageChange, -10.640347174875274)
  assert.deepEqual(
    [births.start, births.end, births.lastFinalYear],
    [13004, 9276, 2024],
  )
  assert.deepEqual([schools.start, schools.end, schools.absoluteChange], [679, 693, 14])
  assert.deepEqual(
    enrollments.map(({ absoluteChange }) => absoluteChange),
    [5765, -9864, -3936],
  )
})

test('quatro janelas e decomposição municipal preservam a queda regional', () => {
  const sensitivity = fact('vds-coortes-rede', 'estabilidade').values
  assert.deepEqual(
    new Set(sensitivity.windows.map(({ start, end }) => `${start}-${end}`)),
    new Set(['2014-2025', '2015-2025', '2016-2025', '2015-2024']),
  )
  assert.ok(sensitivity.windows.every(({ change }) => change < 0))
  const municipal = fact('vds-coortes-rede', 'municipios').values
  assert.equal(municipal.entries.length, 10)
  assert.equal(municipal.tests.directionShare, 0.6)
  assert.equal(municipal.tests.leaveOneOutStable, true)
  assert.ok(municipal.tests.maximumConcentration < 0.5)
  assert.deepEqual(municipal.topNegativeContributors, [
    '4313409',
    '4318705',
    '4320008',
  ])
  assert.deepEqual(municipal.oppositeDirection, [
    '4306403',
    '4307609',
    '4310801',
    '4313375',
  ])
})

test('deslocamento mantém universos e denominadores separados', () => {
  const entries = fact('vds-deslocamento-oferta', 'deslocamento').values.entries
  assert.deepEqual(entries.map(({ universe }) => universe), [
    'total',
    'fundamental',
    'medio',
  ])
  assert.deepEqual(
    entries.map(({ outsideMunicipality, total, residual }) => [
      outsideMunicipality,
      total,
      residual,
    ]),
    [
      [33868, 229441, 50],
      [7507, 107060, 1],
      [5812, 38516, 1],
    ],
  )
  for (const entry of entries) {
    assertNearlyEqual(
      entry.outsideSharePercent,
      entry.outsideMunicipality / entry.total * 100,
    )
    assert.ok(Math.abs(entry.residual) <= Math.max(5, entry.total * 0.01))
  }
  const censoSource = research.sourceCatalog
    .find(({ id }) => id === 'censo-demografico-2022')
  assert.equal(censoSource.evidenceClass, 'preliminary')
})

test('exposição municipal de deslocamento reconcilia com o total regional', () => {
  const municipal = fact('vds-deslocamento-oferta', 'municipios').values
  const mobility = fact('vds-deslocamento-oferta', 'deslocamento').values.entries
  for (const universe of ['total', 'fundamental', 'medio']) {
    const regional = mobility.find((entry) => entry.universe === universe)
    assert.equal(
      municipal.entries.reduce(
        (sum, entry) => sum + entry.universes[universe].outsideMunicipality,
        0,
      ),
      regional.outsideMunicipality,
    )
    assert.equal(
      municipal.entries.reduce(
        (sum, entry) => sum + entry.universes[universe].total,
        0,
      ),
      regional.total,
    )
  }
  assert.ok(municipal.tests.maximumConcentration < 0.5)
  assert.deepEqual(municipal.topHighSchoolShare, [
    '4307609',
    '4307708',
    '4313375',
  ])
  assert.deepEqual(municipal.topAbsoluteOutside, [
    '4320008',
    '4318705',
    '4313409',
  ])
})

test('comparações com RS preservam a mesma medida dentro de cada universo', () => {
  const coortes = fact('vds-coortes-rede', 'comparacao-rs').values
  assertNearlyEqual(coortes.population.statePercentageChange, -8.782951357437236)
  assertNearlyEqual(coortes.schools.statePercentageChange, -1.936637203297249)
  const mobility = fact('vds-deslocamento-oferta', 'comparacao-rs').values.entries
  assert.deepEqual(mobility.map(({ universe }) => universe), [
    'total',
    'fundamental',
    'medio',
  ])
  assert.deepEqual(
    mobility.map(({ stateOutsideSharePercent }) => stateOutsideSharePercent),
    [8.81484168915293, 3.3018410814228547, 8.2202237766851],
  )
})

test('autoria fecha G8 e deriva a publicação de G1–G10', () => {
  for (const card of output.cards) {
    assert.equal(card.internal.gates.G8.status, 'ok')
    assert.equal(card.internal.publication_decision, 'publicada')
    assert.equal(derivePublicationDecision(card.internal.gates), 'publicada')
    assert.ok(GATE_IDS.every((gateId) => card.internal.gates[gateId].status === 'ok'))
    assert.ok(Object.values(card.internal.fact_references).every((ids) => ids.length > 0))
    assert.ok(card.internal.visualization_ids.length >= 3)
  }
})

test('texto público passa no linter e usa duas agendas concretas', () => {
  assert.equal(output.cards.length, 2)
  for (const card of output.cards) {
    assert.deepEqual(lintCard(card, dependencies.vocab), [])
    assert.match(card.education_agenda, /^Como /u)
    assert.ok(card.education_agenda.endsWith('?'))
    assert.equal(card.horizon, 'próximos anos')
  }
})

test('projeção pública usa allowlist e não vaza maquinaria interna', () => {
  const forbiddenKeys = new Set([
    'internal',
    'mechanism_id',
    'future_basis',
    'gates',
    'fact_references',
    'planning_components',
    'transformation_map',
    'visualization_ids',
    'research_candidate_id',
  ])
  function collect(value) {
    if (Array.isArray(value)) return value.flatMap(collect)
    if (value === null || typeof value !== 'object') return []
    return Object.entries(value).flatMap(([key, child]) => [
      ...(forbiddenKeys.has(key) ? [key] : []),
      ...collect(child),
    ])
  }
  assert.deepEqual(collect(output.publicProjection), [])
  assert.deepEqual(
    output.publicProjection.map(({ id }) => id),
    ['vds-coortes-rede', 'vds-deslocamento-oferta'],
  )
})

test('validador falha fechado contra adulterações técnicas da pesquisa', () => {
  const mutations = [
    (value) => { value.region.municipalities[0].ibge7 = 4303905 },
    (value) => {
      value.candidates[0].facts
        .find(({ id }) => id.endsWith('.populacao-0-14'))
        .values.absoluteChange += 1
    },
    (value) => {
      value.candidates[1].facts
        .find(({ id }) => id.endsWith('.deslocamento'))
        .values.entries[0].outsideSharePercent += 1
    },
    (value) => { value.candidates[0].futureBasis.futureNumericValues.push(150000) },
    (value) => { value.candidates[1].futureBasis.supportsTrend = true },
    (value) => { value.candidates[1].futureBasis.scenarioId = 'cenario-inexistente' },
    (value) => { value.candidates[0].pairs[0].territorialSeriesId = 'serie-inexistente' },
    (value) => { value.candidates[0].gates.G5.status = 'reprovado' },
  ]
  for (const mutate of mutations) assertResearchRejected(mutate)
})

test('validador falha fechado contra adulterações da saída final', () => {
  const mutations = [
    (value) => { value.cards[1] = structuredClone(value.cards[0]) },
    (value) => { value.cards[0].internal.future_basis.futureNumericValues.push(1) },
    (value) => { value.cards[0].internal.planning_components.scope = 'alterado' },
    (value) => { value.cards[1].internal.fact_references.education_agenda = [] },
    (value) => { value.publicProjection[0].internal = { gates: {} } },
    (value) => { value.retainedCandidates[0].failedGates[0].reasonCode = 'alterado' },
    (value) => { value.generation.scenarioUsed = true },
  ]
  for (const mutate of mutations) assertOutputRejected(mutate)
})
