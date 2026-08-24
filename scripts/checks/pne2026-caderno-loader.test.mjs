import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

import {
  CADERNO_HYPOTHESIS_SECTIONS,
  CadernoLoadError,
  createPne2026CadernoLoader,
  parsePne2026Caderno,
  parsePne2026CadernoManifest,
  PNE_2026_CADERNO_MANIFEST_PATH,
  PNE_2026_CADERNO_MANIFEST_SCHEMA,
  PNE_2026_CADERNO_MUNICIPAL_PATH,
  PNE_2026_CADERNO_SCHEMA,
  PNE_2026_WORKBOOK_SCHEMA,
} from '../../src/features/caderno/pne2026CadernoLoader.js'
import contract from '../../contracts/pne2026-goal-indicator-contract.json' with { type: 'json' }

const MUNICIPALITY_ID = '4313375'
const MUNICIPAL_PATH = PNE_2026_CADERNO_MUNICIPAL_PATH.replace('{municipalityId}', MUNICIPALITY_ID)
const manifestUrl = new URL('../../public/data/pne2026-caderno/manifest.json', import.meta.url)
const municipalUrl = new URL(
  `../../public/data/pne2026-caderno/municipios/${MUNICIPALITY_ID}.json`,
  import.meta.url,
)
const manifestRaw = await readFile(manifestUrl, 'utf8')
const municipalRaw = await readFile(municipalUrl)
const manifest = JSON.parse(manifestRaw)
const caderno = JSON.parse(municipalRaw.toString('utf8'))
const entry = manifest.municipalities.find((municipality) => municipality.ibge7 === MUNICIPALITY_ID)

function createFixtureLoader({
  document = caderno,
  manifestPayload = manifest,
  manifestError,
  municipalError,
} = {}) {
  const calls = []
  const logs = []
  const loader = createPne2026CadernoLoader({
    fetchJson: async (path, options) => {
      calls.push({ path, options })
      if (path === PNE_2026_CADERNO_MANIFEST_PATH) {
        if (manifestError) throw manifestError
        return structuredClone(manifestPayload)
      }
      if (municipalError) throw municipalError
      return structuredClone(document)
    },
    logger: (...items) => logs.push(items),
  })
  return { calls, load: loader.load, logs }
}

test('o manifesto publicado registra o hash exato do caderno municipal', () => {
  assert.ok(entry, `manifesto sem entrada para ${MUNICIPALITY_ID}.`)
  assert.equal(
    entry.outputSha256,
    createHash('sha256').update(municipalRaw).digest('hex'),
    'o hash publicado deve corresponder byte a byte ao arquivo municipal.',
  )
  assert.equal(entry.outputByteSize, municipalRaw.byteLength)
  assert.equal(entry.path, `municipios/${MUNICIPALITY_ID}.json`)
  assert.match(entry.inputSha256, /^[a-f0-9]{64}$/)
})

test('manifesto e caderno publicados passam pelos parsers', () => {
  assert.deepEqual(parsePne2026CadernoManifest(manifest), manifest)
  assert.equal(parsePne2026Caderno(caderno).schemaVersion, PNE_2026_CADERNO_SCHEMA)
  assert.equal(manifest.schemaVersion, PNE_2026_CADERNO_MANIFEST_SCHEMA)
  assert.equal(manifest.workbookSchemaVersion, PNE_2026_WORKBOOK_SCHEMA)
  assert.equal(caderno.workbookSchemaVersion, PNE_2026_WORKBOOK_SCHEMA)
  assert.deepEqual(Object.keys(caderno.curation).toSorted(), ['sha256', 'version'])
  assert.match(caderno.curation.sha256, /^[a-f0-9]{64}$/)
  assert.equal(caderno.municipality.ibge7, entry.ibge7)
  assert.equal(caderno.referenceDate, entry.referenceDate)
  assert.equal(caderno.contractVersion, contract.contractVersion)
})

test('o caminho feliz pede apenas o manifesto e o município ativo, com cache', async () => {
  const fixture = createFixtureLoader()
  const [first, second] = await Promise.all([
    fixture.load(MUNICIPALITY_ID),
    fixture.load(MUNICIPALITY_ID),
  ])
  assert.deepEqual(first, second)
  assert.equal(first.municipalityId, MUNICIPALITY_ID)
  assert.equal(first.municipalityName, entry.name)
  assert.equal(first.referenceDate, entry.referenceDate)
  assert.equal(first.outputSha256, entry.outputSha256)
  assert.deepEqual(
    fixture.calls.map(({ path }) => path),
    [PNE_2026_CADERNO_MANIFEST_PATH, MUNICIPAL_PATH],
  )
  assert.deepEqual(fixture.calls[0].options, { cache: 'no-store' })
  assert.equal(fixture.logs.length, 0)
})

test('município sem publicação falha fechado sem pedir o arquivo municipal', async () => {
  const fixture = createFixtureLoader()
  await assert.rejects(fixture.load('4300034'), {
    name: 'CadernoLoadError',
    code: 'municipality_not_published',
  })
  assert.deepEqual(fixture.calls.map(({ path }) => path), [PNE_2026_CADERNO_MANIFEST_PATH])
})

test('código municipal inválido nunca alcança a rede', async () => {
  const fixture = createFixtureLoader()
  await assert.rejects(fixture.load('431337'), { code: 'invalid_municipality' })
  assert.equal(fixture.calls.length, 0)
  assert.equal(fixture.logs.length, 1)
  assert.ok(fixture.logs[0][0] instanceof CadernoLoadError)
})

test('manifesto adulterado é recusado', async () => {
  for (const [label, mutate] of [
    ['schema divergente', (payload) => { payload.schemaVersion = 'outro' }],
    ['caderno divergente', (payload) => { payload.cadernoSchemaVersion = 'pne2026-caderno-v0' }],
    ['workbook v1', (payload) => { payload.workbookSchemaVersion = 'pne-priority-hypothesis-workbook-v1' }],
    ['campo desconhecido', (payload) => { payload.extra = true }],
    ['hash inválido', (payload) => { payload.municipalities[0].outputSha256 = 'nao-e-hash' }],
    ['caminho fora do padrão', (payload) => { payload.municipalities[0].path = 'municipios/x.json' }],
  ]) {
    const payload = structuredClone(manifest)
    mutate(payload)
    const fixture = createFixtureLoader({ manifestPayload: payload })
    await assert.rejects(fixture.load(MUNICIPALITY_ID), { code: 'invalid_manifest' }, label)
  }
})

test('documento municipal divergente do manifesto é recusado', async () => {
  for (const [label, mutate] of [
    ['outro município', (payload) => { payload.municipality.ibge7 = '4300034' }],
    ['caderno v1', (payload) => { payload.schemaVersion = 'pne2026-caderno-v1' }],
    ['workbook v1', (payload) => { payload.workbookSchemaVersion = 'pne-priority-hypothesis-workbook-v1' }],
    ['curadoria ausente', (payload) => { delete payload.curation }],
    ['hash de curadoria inválido', (payload) => { payload.curation.sha256 = 'nao-e-hash' }],
    ['campo extra na curadoria', (payload) => { payload.curation.extra = 'x' }],
    ['outra data', (payload) => {
      payload.referenceDate = '2026-08-15'
      for (const goal of payload.goals) {
        for (const section of CADERNO_HYPOTHESIS_SECTIONS) {
          for (const hypothesis of goal.hypotheses[section]) hypothesis.classDate = '2026-08-15'
        }
      }
    }],
    ['classe sem data de referência', (payload) => {
      payload.goals[0].hypotheses.adverse_signal[0].classDate = '2026-01-01'
    }],
    ['aviso vazio', (payload) => { payload.disclaimer = '' }],
    ['título oficial ausente', (payload) => { delete payload.goals[0].legalGoals[0].title }],
    ['campo numérico infiltrado', (payload) => { payload.goals[0].indicators[0].valueRaw = 1 }],
    ['contexto sem relação', (payload) => { payload.goals[0].monitoring_context[0].relations = [] }],
    ['relação de contexto fora da meta', (payload) => {
      payload.goals[0].monitoring_context[0].relations[0].relationId = '19.a'
    }],
  ]) {
    const payload = structuredClone(caderno)
    mutate(payload)
    const fixture = createFixtureLoader({ document: payload })
    await assert.rejects(fixture.load(MUNICIPALITY_ID), { code: 'invalid_payload' }, label)
  }
})

test('a falha de rede vira erro estruturado e é reportada uma única vez', async () => {
  const fixture = createFixtureLoader({ municipalError: new Error('offline') })
  await assert.rejects(fixture.load(MUNICIPALITY_ID), { code: 'municipality_unavailable' })
  await assert.rejects(fixture.load(MUNICIPALITY_ID), { code: 'municipality_unavailable' })
  assert.equal(fixture.logs.length, 1)
})

test('o caderno publicado preserva a ordem e o vocabulário do artefato de origem', () => {
  assert.deepEqual(
    caderno.goals.map((goal) => goal.goalId),
    ['1', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '14', '15', '16', '17', '18', '19'],
  )
  let indicatorCount = 0
  const factorPositions = new Map()
  for (const goal of caderno.goals) {
    indicatorCount += goal.indicators.length
    for (const indicator of goal.indicators) {
      const legalGoal = contract.goals[indicator.relationId]
      assert.equal(indicator.legalGoalTitle, legalGoal.publicTitle, indicator.relationId)
      assert.equal(
        indicator.indicatorTitle,
        contract.indicators[indicator.indicatorId].publicTitle,
        indicator.indicatorId,
      )
      assert.equal(indicator.relationId.split('.')[0], goal.goalId)
    }
    for (const legalGoal of goal.legalGoals) {
      assert.equal(legalGoal.title, contract.goals[legalGoal.legalGoalId].publicTitle)
    }
    for (const section of CADERNO_HYPOTHESIS_SECTIONS) {
      // A ordem publicada é alfabética dentro da seção e não expressa
      // importância: a ingestão não pode reordenar nem introduzir ranking.
      const names = goal.hypotheses[section].map((hypothesis) => hypothesis.name)
      assert.deepEqual(
        names,
        [...names].toSorted((left, right) => left.localeCompare(right, 'pt-BR')),
        `${goal.goalId}/${section}`,
      )
      for (const hypothesis of goal.hypotheses[section]) {
        const key = `${goal.goalId}::${hypothesis.factorId}`
        assert.ok(!factorPositions.has(key), `fator repetido entre seções: ${key}`)
        factorPositions.set(key, section)
      }
    }
  }
  assert.equal(indicatorCount, 57)
})

test('a curadoria v2 reduz as causas escolhíveis e preserva o contexto sem ranking', () => {
  const causeCount = caderno.goals.reduce(
    (total, goal) => total
      + goal.hypotheses.adverse_signal.length
      + goal.hypotheses.no_public_data.length,
    0,
  )
  const protectiveCount = caderno.goals.reduce(
    (total, goal) => total + goal.hypotheses.protective_present.length,
    0,
  )
  const contextCount = caderno.goals.reduce(
    (total, goal) => total + goal.monitoring_context.length,
    0,
  )

  assert.equal(causeCount, 47)
  assert.equal(protectiveCount, 3)
  assert.equal(contextCount, 33)
  for (const goalId of ['15', '16']) {
    const goal = caderno.goals.find((candidate) => candidate.goalId === goalId)
    assert.equal(goal.hypotheses.adverse_signal.length, 0)
    assert.equal(goal.hypotheses.no_public_data.length, 0)
  }

  for (const goal of caderno.goals) {
    for (const context of goal.monitoring_context) {
      assert.ok(context.relations.length > 0, `${goal.goalId}/${context.factorId}`)
      for (const relation of context.relations) {
        assert.ok(
          goal.indicators.some(
            (indicator) => indicator.relationId === relation.relationId
              && indicator.indicatorId === relation.indicatorId,
          ),
          `${goal.goalId}/${context.factorId}/${relation.relationId}/${relation.indicatorId}`,
        )
      }
    }
  }
})

test('todo sinal carrega o recorte da observação e nenhum recorte se funde com outro', () => {
  let signalCount = 0
  const missingDimensions = []
  const merged = []
  for (const goal of caderno.goals) {
    const collections = [
      ...CADERNO_HYPOTHESIS_SECTIONS.flatMap((section) => goal.hypotheses[section].map(
        (hypothesis) => [`${goal.goalId}/${hypothesis.factorId}`, hypothesis.signals],
      )),
      ...goal.monitoring_context.map((context) => [
        `${goal.goalId}/${context.factorId}`,
        context.signals,
      ]),
    ]
    for (const [label, signals] of collections) {
      const seen = new Set()
      for (const signal of signals) {
        signalCount += 1
        if (typeof signal.dimensions !== 'string') missingDimensions.push(`${label}:${signal.measureId}`)
        // A desfusão do P-K1c depende do recorte entrar na chave de deduplicação:
        // sem ele, observações de subgrupos distintos voltam a colapsar em uma.
        const key = [
          signal.measureId,
          signal.period,
          signal.unit,
          signal.valueRaw,
          signal.dimensions,
        ].join(' ')
        if (seen.has(key)) merged.push(`${label}:${signal.measureId}`)
        seen.add(key)
      }
    }
  }
  assert.deepEqual(missingDimensions, [], 'sinal publicado sem o campo dimensions')
  assert.deepEqual(merged, [], 'observações distintas voltaram a se fundir')
  assert.equal(signalCount, 3906)
})

test('nenhum valor do caderno publicado é numérico: não existe campo capaz de ordenar hipóteses', () => {
  const offenders = []
  const walk = (value, path) => {
    if (typeof value === 'string') return
    if (Array.isArray(value)) {
      value.forEach((item, index) => walk(item, `${path}[${index}]`))
      return
    }
    if (value && typeof value === 'object') {
      for (const key of Object.keys(value)) walk(value[key], `${path}.${key}`)
      return
    }
    offenders.push(path)
  }
  for (const goal of caderno.goals) walk(goal, `goals.${goal.goalId}`)
  assert.deepEqual(offenders, [])
})
