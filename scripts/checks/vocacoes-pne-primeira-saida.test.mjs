import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { readFileSync } from 'node:fs'
import test from 'node:test'

import { buildExpectedOutput } from '../generate-vocacoes-pne-primeira-saida.mjs'
import {
  derivePublicationDecision,
  GATE_IDS,
  PrimeiraSaidaError,
  validateFirstOutputArtifact,
  validateResearchArtifact,
} from '../lib/vocacoes-pne-primeira-saida.mjs'
import { lintCard, loadVocabulario } from '../lib/vocacoes-pne-linter.mjs'
import {
  loadCatalogoMecanismos,
  loadCatalogoReferencias,
  loadRegistroSeries,
  loadRegrasUniverso,
} from '../lib/vocacoes-pne-registro.mjs'

const fixtureDirectory = new URL('./fixtures/vocacoes-pne/', import.meta.url)
const researchUrl = new URL(
  'primeira-saida-pesquisa-vale-do-sinos.json',
  fixtureDirectory,
)
const outputUrl = new URL('primeira-saida-vale-do-sinos.json', fixtureDirectory)
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

function fact(candidate, kind) {
  return candidate.facts.find((item) => item.kind === kind)
}

function factBySeries(candidate, seriesId) {
  return candidate.facts.find((item) => item.seriesId === seriesId)
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
    PrimeiraSaidaError,
  )
}

function assertOutputRejected(mutator) {
  const mutated = structuredClone(output)
  mutator(mutated)
  assert.throws(
    () => validateFirstOutputArtifact(mutated, research, dependencies),
    PrimeiraSaidaError,
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
  assert.equal(validateFirstOutputArtifact(output, research, dependencies), true)
})

test('handshake registra hash e tamanho exatos do artefato de pesquisa', () => {
  assert.deepEqual(output.researchArtifact, {
    path: 'scripts/checks/fixtures/vocacoes-pne/primeira-saida-pesquisa-vale-do-sinos.json',
    sha256: createHash('sha256').update(researchBytes).digest('hex'),
    byteSize: researchBytes.length,
  })
  assert.equal(research.sourceManifest.length, 28)
  assert.equal(
    new Set(research.sourceManifest.map(({ path }) => path)).size,
    research.sourceManifest.length,
  )
  assert.ok(
    research.sourceManifest.every(({ sha256 }) => /^[a-f0-9]{64}$/u.test(sha256)),
  )
})

test('identidade regional usa dez códigos IBGE textuais e canônicos', () => {
  assert.equal(research.region.slug, 'vale-do-sinos')
  assert.equal(research.region.stateCode, 'RS')
  assert.equal(research.region.municipalityCount, 10)
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

test('motor publica três leituras e retém três candidatas silenciosamente', () => {
  assert.deepEqual(research.summary, {
    candidateCount: 6,
    readyForAuthorshipCount: 3,
    readyForAuthorshipIds: [
      'vds-educacao-infantil-populacao',
      'vds-ensino-fundamental-populacao',
      'vds-ensino-medio-populacao',
    ],
    retainedCount: 3,
    retainedIds: [
      'vds-eja-publico-potencial',
      'vds-educacao-profissional-ocupacoes',
      'vds-tempo-integral-trabalho-familias',
    ],
    technicalGate6: 'aprovado',
    technicalGate8: 'aprovado',
  })
  assert.deepEqual(output.summary, {
    candidateCount: 6,
    publishedCount: 3,
    retainedCount: 3,
    gate6: 'aprovado',
    gate8: 'aprovado',
  })

  for (const candidate of research.candidates.slice(0, 3)) {
    assert.equal(candidate.engineDecision, 'apta_para_autoria')
    assert.equal(candidate.gates.G8.status, 'pendente_autoria')
    for (const gateId of GATE_IDS.filter((id) => id !== 'G8')) {
      assert.equal(candidate.gates[gateId].status, 'ok', `${candidate.id}.${gateId}`)
    }
  }
  for (const candidate of research.candidates.slice(3)) {
    assert.equal(candidate.engineDecision, 'retida')
    assert.deepEqual(candidate.facts, [])
    assert.deepEqual(candidate.visualizations, [])
    assert.equal(candidate.planningComponents, null)
    assert.equal(
      Object.values(candidate.gates).filter(({ status }) => status === 'reprovado').length,
      1,
    )
  }
  const publicIds = new Set(output.publicProjection.map(({ id }) => id))
  assert.ok(output.retainedCandidates.every(({ candidateId }) => !publicIds.has(candidateId)))
})

test('autoria fecha G8 e a decisão publicada é derivada de G1–G10', () => {
  for (const card of output.cards) {
    assert.equal(derivePublicationDecision(card.internal.gates), 'publicada')
    assert.equal(card.internal.publication_decision, 'publicada')
    assert.equal(card.internal.gates.G8.status, 'ok')
    assert.ok(
      GATE_IDS.every((gateId) => card.internal.gates[gateId].status === 'ok'),
      card.id,
    )
  }
})

test('todos os trechos narrativos apontam para fatos e fontes conhecidos', () => {
  const sourceIds = new Set(research.sourceCatalog.map(({ id }) => id))
  const readyCandidates = research.candidates.slice(0, 3)
  assert.equal(
    readyCandidates.reduce((total, candidate) => total + candidate.facts.length, 0),
    27,
  )
  for (const candidate of readyCandidates) {
    const factIds = new Set(candidate.facts.map(({ id }) => id))
    assert.ok(candidate.facts.every(({ sourceId }) => sourceIds.has(sourceId)))
    const card = output.cards.find(({ id }) => id === candidate.id)
    const references = card.internal.fact_references
    for (const ids of Object.values(references)) {
      assert.ok(ids.length > 0)
      assert.equal(new Set(ids).size, ids.length)
      assert.ok(ids.every((id) => factIds.has(id)))
    }
    assert.equal(lintCard(card, dependencies.vocab).length, 0)
  }
})

test('números centrais e componentes são recomputados sem arredondamento', () => {
  const expected = [
    ['vds-educacao-infantil-populacao', 34568, 40333, 71337, 60661, 'ratio'],
    ['vds-ensino-fundamental-populacao', 114192, 104328, 113469, 104481, 'population'],
    ['vds-ensino-medio-populacao', 30847, 26911, 42781, 33093, 'population'],
  ]
  for (const [id, educationStart, educationEnd, populationStart, populationEnd, dominant] of expected) {
    const candidate = candidateById.get(id)
    const education = fact(candidate, 'observed-change').values
    const population = fact(candidate, 'estimated-change').values
    const ratio = fact(candidate, 'calculated-ratio').values
    const components = fact(candidate, 'accounting-decomposition').values
    assert.deepEqual(
      [education.start, education.end, population.start, population.end],
      [educationStart, educationEnd, populationStart, populationEnd],
    )
    const ratioStart = educationStart / populationStart
    const ratioEnd = educationEnd / populationEnd
    const populationComponent = (
      (populationEnd - populationStart) * (ratioStart + ratioEnd) / 2
    )
    const ratioComponent = (
      (ratioEnd - ratioStart) * (populationStart + populationEnd) / 2
    )
    assertNearlyEqual(ratio.start, ratioStart)
    assertNearlyEqual(ratio.end, ratioEnd)
    assertNearlyEqual(components.populationComponent, populationComponent)
    assertNearlyEqual(components.ratioComponent, ratioComponent)
    assertNearlyEqual(
      components.populationComponent + components.ratioComponent,
      educationEnd - educationStart,
    )
    assert.equal(components.dominantComponent, dominant)
  }
})

test('todo número quantitativo dos textos deriva dos fatos com arredondamento público', () => {
  const formatInteger = (value) => new Intl.NumberFormat('pt-BR', {
    maximumFractionDigits: 0,
  }).format(value)
  const formatDecimal = (value) => new Intl.NumberFormat('pt-BR', {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  }).format(value)
  const formatSignedInteger = (value) => (
    `${value >= 0 ? '+' : '-'}${formatInteger(Math.abs(value))}`
  )

  for (const card of output.cards) {
    const candidate = candidateById.get(card.id)
    const education = fact(candidate, 'observed-change').values
    const population = fact(candidate, 'estimated-change').values
    const components = fact(candidate, 'accounting-decomposition').values
    const educationText = card.education_facts.join(' ')
    const populationText = card.territorial_facts[0]
    for (const value of [education.start, education.end, Math.abs(education.absoluteChange)]) {
      assert.match(educationText, new RegExp(formatInteger(value).replace('.', '\\.'), 'u'))
    }
    assert.ok(
      educationText.includes(`${formatDecimal(Math.abs(education.percentageChange))}%`),
    )
    for (const value of [population.start, population.end, Math.abs(population.absoluteChange)]) {
      assert.match(populationText, new RegExp(formatInteger(value).replace('.', '\\.'), 'u'))
    }
    assert.ok(
      populationText.includes(`${formatDecimal(Math.abs(population.percentageChange))}%`),
    )
    assert.ok(
      card.integrated_reading.includes(
        formatInteger(Math.round(Math.abs(components.populationComponent))),
      ),
    )
    assert.ok(
      card.integrated_reading.includes(
        formatInteger(Math.round(Math.abs(components.ratioComponent))),
      ),
    )

    const municipal = fact(candidate, 'municipal-decomposition').values
    for (const ibgeCode of [
      ...municipal.topEducationContributors,
      ...municipal.oppositeEducationDirection,
    ]) {
      const entry = municipal.entries.find((item) => item.ibgeCode === ibgeCode)
      assert.ok(entry)
      assert.ok(card.municipal_pattern.includes(entry.name))
      assert.ok(
        card.municipal_pattern.includes(
          `(${formatSignedInteger(entry.education.change)})`,
        ),
      )
    }
  }

  const fundamental = output.cards[1]
  const fundamentalCandidate = candidateById.get(fundamental.id)
  const fundamentalDistortion = factBySeries(
    fundamentalCandidate,
    'fluxo_taxa_distorcao_fundamental',
  ).values
  const fundamentalFlowText = fundamental.territorial_facts[1]
  for (const value of [
    fundamentalDistortion.regionalDistribution.median,
    fundamentalDistortion.stateDistribution.median,
    fundamentalDistortion.regionalDistribution.min,
    fundamentalDistortion.regionalDistribution.max,
  ]) {
    assert.ok(fundamentalFlowText.includes(`${formatDecimal(value)}%`))
  }

  const medio = output.cards[2]
  const medioCandidate = candidateById.get(medio.id)
  const medioFlowText = medio.territorial_facts[1]
  for (const seriesId of [
    'fluxo_taxa_reprovacao_medio',
    'fluxo_taxa_abandono_medio',
  ]) {
    const values = factBySeries(medioCandidate, seriesId).values
    assert.ok(
      medioFlowText.includes(`${formatDecimal(values.regionalDistribution.median)}%`),
    )
    assert.ok(
      medioFlowText.includes(`${formatDecimal(values.stateDistribution.median)}%`),
    )
  }
})

test('heterogeneidade municipal reconcilia e passa os limiares de estabilidade', () => {
  for (const candidate of research.candidates.slice(0, 3)) {
    const educationTotal = fact(candidate, 'observed-change').values.absoluteChange
    const populationTotal = fact(candidate, 'estimated-change').values.absoluteChange
    const municipal = fact(candidate, 'municipal-decomposition').values
    assert.equal(municipal.entries.length, 10)
    assert.equal(
      municipal.entries.reduce((total, entry) => total + entry.education.change, 0),
      educationTotal,
    )
    assert.equal(
      municipal.entries.reduce((total, entry) => total + entry.population.change, 0),
      populationTotal,
    )
    assert.ok(municipal.tests.educationConcentration <= 0.5)
    assert.ok(municipal.tests.populationConcentration <= 0.5)
    assert.ok(municipal.tests.educationDirectionShare >= 0.6)
    assert.ok(municipal.tests.populationDirectionShare >= 0.6)
    assert.equal(municipal.tests.educationLeaveOneOutStable, true)
    assert.equal(municipal.tests.populationLeaveOneOutStable, true)
    assert.equal(municipal.tests.passed, true)
    assert.ok(municipal.oppositeEducationDirection.length > 0)
    for (const entry of municipal.entries) {
      assert.match(entry.ibgeCode, /^\d{7}$/u)
      assert.equal(
        Math.sign(entry.education.leaveOneOutChange),
        Math.sign(educationTotal),
      )
      assert.equal(
        Math.sign(entry.population.leaveOneOutChange),
        Math.sign(populationTotal),
      )
    }
  }
})

test('quatro janelas temporais preservam direção, componente e reconciliação', () => {
  const expectedWindows = new Set(['2015-2025', '2014-2025', '2016-2025', '2015-2024'])
  for (const candidate of research.candidates.slice(0, 3)) {
    const sensitivity = fact(candidate, 'sensitivity-check').values
    assert.equal(sensitivity.windows.length, 4)
    assert.deepEqual(
      new Set(sensitivity.windows.map(({ start, end }) => `${start}-${end}`)),
      expectedWindows,
    )
    assert.deepEqual(sensitivity.tests, {
      dominantComponentStable: true,
      educationDirectionStable: true,
      passed: true,
      populationDirectionStable: true,
      reconciled: true,
    })
    assert.ok(
      sensitivity.windows.every(
        ({ reconciliationDifference }) => Math.abs(reconciliationDifference) <= 1e-8,
      ),
    )
  }
})

test('taxas de fluxo permanecem distribuições municipais, nunca somas', () => {
  const fundamental = candidateById.get('vds-ensino-fundamental-populacao')
  const medio = candidateById.get('vds-ensino-medio-populacao')
  const expectedMedians = [
    [fundamental, 'fluxo_taxa_reprovacao_fundamental', 2.85, 2.3],
    [fundamental, 'fluxo_taxa_abandono_fundamental', 0.1, 0.1],
    [fundamental, 'fluxo_taxa_distorcao_fundamental', 7.5, 8.1],
    [medio, 'fluxo_taxa_reprovacao_medio', 6, 2.65],
    [medio, 'fluxo_taxa_abandono_medio', 2.8, 1.5],
    [medio, 'fluxo_taxa_distorcao_medio', 18.05, 14.4],
  ]
  for (const [candidate, seriesId, regionalMedian, stateMedian] of expectedMedians) {
    const rate = factBySeries(candidate, seriesId)
    assert.equal(rate.aggregationRule, 'municipal_distribution')
    assert.equal(rate.values.regionalMunicipalitiesWithData, 10)
    assert.ok(rate.values.stateMunicipalitiesWithData >= 496)
    assertNearlyEqual(rate.values.regionalDistribution.median, regionalMedian)
    assertNearlyEqual(rate.values.stateDistribution.median, stateMedian)
  }
})

test('planejamento e visuais mantêm períodos alinhados e acrescentam informação', () => {
  for (const candidate of research.candidates.slice(0, 3)) {
    assert.ok(candidate.planningComponents.indicatorIds.length >= 2)
    assert.equal(candidate.visualizations.length, 4)
    assert.ok(candidate.visualizations.every(({ addsInformation }) => addsInformation))
    const temporal = candidate.visualizations.find(
      ({ kind }) => kind === 'aligned-mini-charts',
    )
    for (const series of temporal.series) {
      assert.deepEqual(
        series.points.map(({ period }) => period),
        temporal.periods,
      )
    }
  }
})

test('projeção pública usa allowlist e não vaza maquinaria interna', () => {
  const forbiddenKeys = new Set([
    'internal',
    'mechanism_id',
    'gates',
    'fact_references',
    'planning_components',
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
    output.cards.map(({ id }) => id),
  )
})

test('validador falha fechado contra adulterações técnicas da pesquisa', () => {
  const mutations = [
    (value) => { value.region.municipalities[0].ibge7 = 4303905 },
    (value) => {
      fact(value.candidates[0], 'accounting-decomposition')
        .values.populationComponent += 1
    },
    (value) => {
      fact(value.candidates[0], 'municipal-decomposition')
        .values.entries[0].education.absoluteShare = 0.9
    },
    (value) => { value.candidates[0].pairs[0].mechanismId = 'M0-inexistente' },
    (value) => { value.candidates[0].gates.G5.status = 'reprovado' },
  ]
  for (const mutate of mutations) assertResearchRejected(mutate)
})

test('validador falha fechado contra adulterações da saída final', () => {
  const mutations = [
    (value) => { value.cards[2] = structuredClone(value.cards[0]) },
    (value) => { value.cards[0].internal.planning_components.scope = 'escopo adulterado' },
    (value) => { value.publicProjection[0].internal = { gates: {} } },
    (value) => { value.retainedCandidates[0].failedGates[0].reasonCode = 'alterado' },
    (value) => { value.generation.networkUsed = true },
  ]
  for (const mutate of mutations) assertOutputRejected(mutate)
})
