import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

import {
  buildManifest,
  MatrizIngestionError,
  parseSourceMatrizManifest,
} from '../generate-pne-matriz.mjs'
import {
  createPne2026MatrizLoader,
  MatrizLoadError,
  parsePne2026Matriz,
  parsePne2026MatrizManifest,
  MATRIZ_PROOF_MAX_INFERENCES,
  PNE_2026_MATRIZ_MANIFEST_PATH,
  PNE_2026_MATRIZ_MANIFEST_SCHEMA,
  PNE_2026_MATRIZ_MUNICIPAL_PATH,
  PNE_2026_MATRIZ_SCHEMA_V3,
  PNE_2026_MATRIZ_SCHEMA_V4,
  PNE_2026_MATRIZ_SOURCE_MANIFEST_SCHEMA_V3,
  PNE_2026_MATRIZ_SOURCE_MANIFEST_SCHEMA_V4,
} from '../../src/features/matriz/pne2026MatrizLoader.js'
import {
  MATRIZ_FRONTS_SCHEMA_VERSION,
  MATRIZ_FRONTS_STORAGE_KEY_PREFIX,
  parseMatrizPlan,
  serializeMatrizPlan,
} from '../../src/domain/matrizFrontsStorage.ts'

const MUNICIPALITY_ID = '4313375'
const MUNICIPAL_PATH = PNE_2026_MATRIZ_MUNICIPAL_PATH.replace('{municipalityId}', MUNICIPALITY_ID)
const EXPECTED_INPUT_SHA256 = 'c32b53bb6ce89421720e74890c637ebcc8fa2659074e2d201002963d8c1f46a6'
const EXPECTED_OUTPUT_SHA256 = '7afbb731c506605b2fa98fd3405f263358ef592ef8542e5c74ccfa58315f7267'
const EXPECTED_OUTPUT_BYTE_SIZE = 513354
const manifestRaw = await readFile(new URL('../../public/data/pne2026-matriz/manifest.json', import.meta.url))
const municipalRaw = await readFile(
  new URL(`../../public/data/pne2026-matriz/municipios/${MUNICIPALITY_ID}.json`, import.meta.url),
)
const sourceManifestRaw = await readFile(
  new URL('../../.tmp/matriz/artefato/matriz-manifest.json', import.meta.url),
)
const rsRegistryRaw = await readFile(
  new URL('../../config/municipalities/rs.json', import.meta.url),
)
const manifest = JSON.parse(manifestRaw.toString('utf8'))
const matriz = JSON.parse(municipalRaw.toString('utf8'))
const sourceManifest = JSON.parse(sourceManifestRaw.toString('utf8'))
const rsRegistry = JSON.parse(rsRegistryRaw.toString('utf8'))
const entry = manifest.municipalities.find((municipality) => municipality.ibge7 === MUNICIPALITY_ID)

function createFixtureLoader({
  document = matriz,
  manifestPayload = manifest,
  manifestError,
  municipalError,
} = {}) {
  const calls = []
  const logs = []
  const loader = createPne2026MatrizLoader({
    fetchJson: async (path, options) => {
      calls.push({ options, path })
      if (path === PNE_2026_MATRIZ_MANIFEST_PATH) {
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

function clonedCause(cause, factorId) {
  const cloned = structuredClone(cause)
  cloned.factorId = factorId
  cloned.firstStep.ref = factorId
  return cloned
}

function allCauses(document = matriz) {
  return document.priorityGoals.flatMap((goal) => goal.causes)
}

function peerBenchmarkForSignal(signal, { differenceRaw = signal.valueRaw, valueRaw = '0' } = {}) {
  return {
    statistic: 'median',
    valueRaw,
    differenceRaw,
    unit: signal.unit,
    year: signal.period,
    n: 88,
  }
}

function buildV3Fixture() {
  const document = structuredClone(matriz)
  document.schemaVersion = PNE_2026_MATRIZ_SCHEMA_V3
  for (const goal of document.priorityGoals) {
    delete goal.trend
    delete goal.networkConcentration
    for (const cause of goal.causes) {
      if (cause.proof) delete cause.proof.peerBenchmark
      for (const signal of cause.collapsed.signals) delete signal.peerBenchmark
    }
  }
  return document
}

function buildV4Fixture() {
  const document = buildV3Fixture()
  document.schemaVersion = PNE_2026_MATRIZ_SCHEMA_V4
  const goal = document.priorityGoals[0]
  const proof = goal.causes[0].proof
  assert.ok(proof)
  goal.trend = {
    previousValueRaw: '34.2',
    previousYear: '2024',
    direction: 'improved',
  }
  goal.networkConcentration = {
    measureId: proof.measureId,
    classification: 'concentrated_in_few_schools',
    affectedSchools: 2,
    totalSchools: 5,
  }
  proof.peerBenchmark = peerBenchmarkForSignal(proof)
  return document
}

test('o manifesto publicado registra o hash e o tamanho exatos do documento municipal', () => {
  assert.ok(entry, `manifesto sem entrada para ${MUNICIPALITY_ID}.`)
  assert.equal(entry.inputSha256, EXPECTED_INPUT_SHA256)
  assert.equal(entry.outputSha256, EXPECTED_OUTPUT_SHA256)
  assert.equal(entry.outputByteSize, EXPECTED_OUTPUT_BYTE_SIZE)
  assert.equal(entry.outputSha256, createHash('sha256').update(municipalRaw).digest('hex'))
  assert.equal(entry.outputByteSize, municipalRaw.byteLength)
  assert.equal(entry.path, `municipios/${MUNICIPALITY_ID}.json`)
  assert.deepEqual(entry.peerGroup, matriz.peerGroup)
})

test('a coleção publicada cobre exatamente os 497 municípios canônicos do RS e reconcilia todos os arquivos', async () => {
  const publishedCodes = manifest.municipalities.map((municipality) => municipality.ibge7).toSorted()
  const canonicalCodes = rsRegistry.municipalities.map((municipality) => municipality.ibgeCode).toSorted()
  assert.equal(manifest.municipalities.length, 497)
  assert.deepEqual(publishedCodes, canonicalCodes)

  for (const municipality of manifest.municipalities) {
    const raw = await readFile(new URL(`../../public/data/pne2026-matriz/${municipality.path}`, import.meta.url))
    const document = JSON.parse(raw.toString('utf8'))
    assert.equal(raw.byteLength, municipality.outputByteSize, municipality.ibge7)
    assert.equal(createHash('sha256').update(raw).digest('hex'), municipality.outputSha256, municipality.ibge7)
    assert.equal(document.municipality.ibge7, municipality.ibge7)
    assert.equal(document.municipality.name, municipality.name)
    assert.equal(document.municipality.uf, 'RS')
  }
})

test('manifestos de origem e publicação e documento municipal passam pelos parsers fechados', () => {
  assert.deepEqual(parseSourceMatrizManifest(sourceManifest), sourceManifest)
  assert.deepEqual(parsePne2026MatrizManifest(manifest), manifest)
  assert.deepEqual(parsePne2026Matriz(matriz), matriz)
  assert.equal(sourceManifest.schemaVersion, PNE_2026_MATRIZ_SOURCE_MANIFEST_SCHEMA_V4)
  assert.equal(sourceManifest.matrixSchemaVersion, PNE_2026_MATRIZ_SCHEMA_V4)
  assert.equal(manifest.schemaVersion, PNE_2026_MATRIZ_MANIFEST_SCHEMA)
  assert.equal(manifest.matrizSchemaVersion, PNE_2026_MATRIZ_SCHEMA_V4)
  assert.equal(manifest.sourceManifestSchemaVersion, PNE_2026_MATRIZ_SOURCE_MANIFEST_SCHEMA_V4)
  assert.equal(matriz.schemaVersion, PNE_2026_MATRIZ_SCHEMA_V4)
  assert.deepEqual(Object.keys(entry.peerGroup).toSorted(), [
    'band', 'criteria', 'expansions', 'n', 'populationPeriod', 'releaseId',
  ])
  assert.equal(Object.hasOwn(matriz, 'cards'), false)
  assert.equal(Object.hasOwn(matriz, 'quadrant'), false)
  for (const goal of matriz.priorityGoals) {
    assert.deepEqual(Object.keys(goal.severity.peerBenchmark).toSorted(), [
      'differenceRaw', 'n', 'statistic', 'unit', 'valueRaw', 'year',
    ])
    assert.equal(goal.severity.peerBenchmark.statistic, 'median')
    assert.equal(goal.severity.peerBenchmark.n, goal.severity.peerN)
    assert.equal(goal.severity.peerBenchmark.unit, goal.unit)
    assert.equal(goal.severity.peerBenchmark.year, goal.year)
  }
})

test('faixa-base com 19 municípios é válida e registra a expansão das comparações', async () => {
  const matrixWithSmallBaseBand = structuredClone(matriz)
  matrixWithSmallBaseBand.peerGroup.band = '100k_mais'
  matrixWithSmallBaseBand.peerGroup.n = 19
  matrixWithSmallBaseBand.peerGroup.expansions = [{
    bands: ['100k_mais', '20k_100k'],
    goalId: matrixWithSmallBaseBand.priorityGoals[0].goalId,
    indicatorId: matrixWithSmallBaseBand.priorityGoals[0].indicatorId,
    n: 107,
  }]
  assert.deepEqual(parsePne2026Matriz(matrixWithSmallBaseBand), matrixWithSmallBaseBand)
  assert.ok(matrixWithSmallBaseBand.priorityGoals.every((goal) => goal.severity.peerN >= 20))

  const sourceManifestWithSmallBaseBand = structuredClone(sourceManifest)
  sourceManifestWithSmallBaseBand.peerGroup = structuredClone(matrixWithSmallBaseBand.peerGroup)
  assert.deepEqual(
    parseSourceMatrizManifest(sourceManifestWithSmallBaseBand),
    sourceManifestWithSmallBaseBand,
  )

  const publishedManifestWithSmallBaseBand = structuredClone(manifest)
  const municipality = publishedManifestWithSmallBaseBand.municipalities.find(
    (candidate) => candidate.ibge7 === MUNICIPALITY_ID,
  )
  municipality.peerGroup = structuredClone(matrixWithSmallBaseBand.peerGroup)
  assert.deepEqual(
    parsePne2026MatrizManifest(publishedManifestWithSmallBaseBand),
    publishedManifestWithSmallBaseBand,
  )

  const fixture = createFixtureLoader({
    document: matrixWithSmallBaseBand,
    manifestPayload: publishedManifestWithSmallBaseBand,
  })
  assert.equal((await fixture.load(MUNICIPALITY_ID)).matriz.peerGroup.n, 19)
})

test('documento 4.0.0 válido aceita trajetória, concentração da rede e mediana por sinal', () => {
  const document = buildV4Fixture()
  assert.deepEqual(parsePne2026Matriz(document), document)

  const v4SourceManifest = {
    ...structuredClone(sourceManifest),
    schemaVersion: PNE_2026_MATRIZ_SOURCE_MANIFEST_SCHEMA_V4,
    matrixSchemaVersion: PNE_2026_MATRIZ_SCHEMA_V4,
  }
  assert.deepEqual(parseSourceMatrizManifest(v4SourceManifest), v4SourceManifest)

  const v4PublishedManifest = {
    ...structuredClone(manifest),
    matrizSchemaVersion: PNE_2026_MATRIZ_SCHEMA_V4,
    sourceManifestSchemaVersion: PNE_2026_MATRIZ_SOURCE_MANIFEST_SCHEMA_V4,
  }
  assert.deepEqual(parsePne2026MatrizManifest(v4PublishedManifest), v4PublishedManifest)
})

test('gerador recusa troca de versão quando preservaria outro município da coleção', () => {
  const incomingEntry = {
    ...structuredClone(entry),
    ibge7: '4300034',
    name: 'Aceguá',
    path: 'municipios/4300034.json',
  }

  const v3Manifest = {
    ...structuredClone(manifest),
    matrizSchemaVersion: PNE_2026_MATRIZ_SCHEMA_V3,
    sourceManifestSchemaVersion: PNE_2026_MATRIZ_SOURCE_MANIFEST_SCHEMA_V3,
    municipalities: [structuredClone(entry)],
  }
  const cases = [
    {
      label: 'coleção v4 e ingestão v3',
      previousManifest: manifest,
      versions: {
        matrizSchemaVersion: PNE_2026_MATRIZ_SCHEMA_V3,
        sourceManifestSchemaVersion: PNE_2026_MATRIZ_SOURCE_MANIFEST_SCHEMA_V3,
      },
    },
    {
      label: 'coleção v3 e ingestão v4',
      previousManifest: v3Manifest,
      versions: {
        matrizSchemaVersion: PNE_2026_MATRIZ_SCHEMA_V4,
        sourceManifestSchemaVersion: PNE_2026_MATRIZ_SOURCE_MANIFEST_SCHEMA_V4,
      },
    },
  ]

  for (const { label, previousManifest, versions } of cases) {
    assert.throws(
      () => buildManifest(previousManifest, incomingEntry, versions),
      (error) => {
        assert.ok(error instanceof MatrizIngestionError)
        assert.match(error.message, /release da coleção deve ser homogênea/)
        assert.match(error.message, /republicar todos os municípios da coleção na mesma versão/)
        return true
      },
      label,
    )
  }
})

test('gerador permite troca de versão quando não há outras entradas preservadas', () => {
  const v3Manifest = {
    ...structuredClone(manifest),
    matrizSchemaVersion: PNE_2026_MATRIZ_SCHEMA_V3,
    sourceManifestSchemaVersion: PNE_2026_MATRIZ_SOURCE_MANIFEST_SCHEMA_V3,
    municipalities: [structuredClone(entry)],
  }
  const updatedManifest = buildManifest(v3Manifest, structuredClone(entry), {
    matrizSchemaVersion: PNE_2026_MATRIZ_SCHEMA_V4,
    sourceManifestSchemaVersion: PNE_2026_MATRIZ_SOURCE_MANIFEST_SCHEMA_V4,
  })

  assert.equal(updatedManifest.matrizSchemaVersion, PNE_2026_MATRIZ_SCHEMA_V4)
  assert.equal(
    updatedManifest.sourceManifestSchemaVersion,
    PNE_2026_MATRIZ_SOURCE_MANIFEST_SCHEMA_V4,
  )
  assert.deepEqual(updatedManifest.municipalities, [entry])
})

test('documento 4.0.0 recusa violações de trajetória, concentração e mediana por sinal', () => {
  for (const [label, mutate] of [
    ['direction inválida', (payload) => { payload.priorityGoals[0].trend.direction = 'up' }],
    ['previousYear malformado', (payload) => { payload.priorityGoals[0].trend.previousYear = '24' }],
    ['previousYear igual ao ano da meta', (payload) => {
      payload.priorityGoals[0].trend.previousYear = payload.priorityGoals[0].year
    }],
    ['previousYear posterior ao ano da meta', (payload) => { payload.priorityGoals[0].trend.previousYear = '2026' }],
    ['previousValueRaw não numérico', (payload) => { payload.priorityGoals[0].trend.previousValueRaw = 'indisponível' }],
    ['classificação da concentração inválida', (payload) => {
      payload.priorityGoals[0].networkConcentration.classification = 'unknown'
    }],
    ['measureId da concentração ausente na meta', (payload) => {
      payload.priorityGoals[0].networkConcentration.measureId = 'measure.not.in.goal'
    }],
    ['affectedSchools negativo', (payload) => {
      payload.priorityGoals[0].networkConcentration.affectedSchools = -1
    }],
    ['totalSchools menor que um', (payload) => {
      payload.priorityGoals[0].networkConcentration.totalSchools = 0
    }],
    ['affectedSchools maior que totalSchools', (payload) => {
      payload.priorityGoals[0].networkConcentration.affectedSchools = 6
    }],
    ['unit da mediana do sinal divergente', (payload) => {
      payload.priorityGoals[0].causes[0].proof.peerBenchmark.unit = 'count'
    }],
    ['year da mediana do sinal divergente', (payload) => {
      payload.priorityGoals[0].causes[0].proof.peerBenchmark.year = '2024'
    }],
    ['mediana do sinal nula', (payload) => {
      payload.priorityGoals[0].causes[0].proof.peerBenchmark = null
    }],
    ['mediana em sinal com período no formato de intervalo', (payload) => {
      payload.priorityGoals[0].causes[0].proof.period = '2024-2025'
    }],
    ['diferença da mediana do sinal inconsistente', (payload) => {
      payload.priorityGoals[0].causes[0].proof.peerBenchmark.differenceRaw = '0'
    }],
  ]) {
    const payload = buildV4Fixture()
    mutate(payload)
    assert.throws(() => parsePne2026Matriz(payload), undefined, label)
  }
})

test('documento 3.0.0 recusa todos os campos exclusivos do contrato 4.0.0', () => {
  for (const [label, keep] of [
    ['trend', (payload) => { delete payload.priorityGoals[0].networkConcentration; delete payload.priorityGoals[0].causes[0].proof.peerBenchmark }],
    ['networkConcentration', (payload) => { delete payload.priorityGoals[0].trend; delete payload.priorityGoals[0].causes[0].proof.peerBenchmark }],
    ['peerBenchmark de sinal', (payload) => { delete payload.priorityGoals[0].trend; delete payload.priorityGoals[0].networkConcentration }],
  ]) {
    const payload = buildV4Fixture()
    payload.schemaVersion = PNE_2026_MATRIZ_SCHEMA_V3
    keep(payload)
    assert.throws(() => parsePne2026Matriz(payload), undefined, label)
  }
})

test('a fixture 3.0.0 derivada do documento publicado continua aceita sem adaptação', () => {
  const document = buildV3Fixture()
  assert.deepEqual(parsePne2026Matriz(document), document)
})

test('o caminho feliz pede somente manifesto e município ativo, com cache', async () => {
  const fixture = createFixtureLoader()
  const [first, second] = await Promise.all([
    fixture.load(MUNICIPALITY_ID),
    fixture.load(MUNICIPALITY_ID),
  ])
  assert.deepEqual(first, second)
  assert.equal(first.schemaVersion, 'pne2026-matriz-loader-result-v3')
  assert.equal(first.municipalityName, 'Nova Santa Rita')
  assert.equal(first.outputSha256, entry.outputSha256)
  assert.deepEqual(fixture.calls.map(({ path }) => path), [PNE_2026_MATRIZ_MANIFEST_PATH, MUNICIPAL_PATH])
  assert.deepEqual(fixture.calls[0].options, { cache: 'no-store' })
  assert.equal(fixture.logs.length, 0)
})

test('o loader aceita pares homogêneos 3.0.0 e 4.0.0 e recusa versões divergentes', async () => {
  const v4Document = buildV4Fixture()
  const v4Manifest = {
    ...structuredClone(manifest),
    matrizSchemaVersion: PNE_2026_MATRIZ_SCHEMA_V4,
    sourceManifestSchemaVersion: PNE_2026_MATRIZ_SOURCE_MANIFEST_SCHEMA_V4,
  }
  const v3Document = buildV3Fixture()
  const v3Manifest = {
    ...structuredClone(manifest),
    matrizSchemaVersion: PNE_2026_MATRIZ_SCHEMA_V3,
    sourceManifestSchemaVersion: PNE_2026_MATRIZ_SOURCE_MANIFEST_SCHEMA_V3,
  }

  const acceptedV4 = createFixtureLoader({ document: v4Document, manifestPayload: v4Manifest })
  assert.equal((await acceptedV4.load(MUNICIPALITY_ID)).matriz.schemaVersion, PNE_2026_MATRIZ_SCHEMA_V4)
  const acceptedV3 = createFixtureLoader({ document: v3Document, manifestPayload: v3Manifest })
  assert.equal((await acceptedV3.load(MUNICIPALITY_ID)).matriz.schemaVersion, PNE_2026_MATRIZ_SCHEMA_V3)

  const v4DocumentWithV3Manifest = createFixtureLoader({ document: v4Document, manifestPayload: v3Manifest })
  await assert.rejects(v4DocumentWithV3Manifest.load(MUNICIPALITY_ID), { code: 'invalid_payload' })
  const v3DocumentWithV4Manifest = createFixtureLoader({ document: v3Document, manifestPayload: v4Manifest })
  await assert.rejects(v3DocumentWithV4Manifest.load(MUNICIPALITY_ID), { code: 'invalid_payload' })
})

test('município ausente e código inválido falham fechados antes do documento', async () => {
  const absent = createFixtureLoader()
  await assert.rejects(absent.load('2700300'), {
    name: 'MatrizLoadError',
    code: 'municipality_not_published',
  })
  assert.deepEqual(absent.calls.map(({ path }) => path), [PNE_2026_MATRIZ_MANIFEST_PATH])

  const invalid = createFixtureLoader()
  await assert.rejects(invalid.load('431337'), { code: 'invalid_municipality' })
  assert.equal(invalid.calls.length, 0)
  assert.ok(invalid.logs[0][0] instanceof MatrizLoadError)
})

test('manifesto adulterado ou sem peerGroup completo é recusado', async () => {
  for (const [label, mutate] of [
    ['schema divergente', (payload) => { payload.schemaVersion = 'outro' }],
    ['campo desconhecido', (payload) => { payload.extra = true }],
    ['peerGroup ausente', (payload) => { delete payload.municipalities[0].peerGroup }],
    ['peerGroup incompleto', (payload) => { delete payload.municipalities[0].peerGroup.releaseId }],
    ['peerGroup vazio', (payload) => { payload.municipalities[0].peerGroup.n = 0 }],
    ['hash inválido', (payload) => { payload.municipalities[0].outputSha256 = 'x' }],
    ['caminho fora do padrão', (payload) => { payload.municipalities[0].path = 'municipios/x.json' }],
  ]) {
    const payload = structuredClone(manifest)
    mutate(payload)
    const fixture = createFixtureLoader({ manifestPayload: payload })
    await assert.rejects(fixture.load(MUNICIPALITY_ID), { code: 'invalid_manifest' }, label)
  }
})

test('documento divergente do manifesto é recusado', async () => {
  for (const [label, mutate] of [
    ['outro município', (payload) => { payload.municipality.ibge7 = '4300034' }],
    ['outra data', (payload) => { payload.referenceDate = '2026-08-15' }],
    ['outro grupo', (payload) => { payload.peerGroup.n = 89 }],
    ['maxInference fora do vocabulário', (payload) => {
      payload.priorityGoals[0].causes[0].proof.maxInference = 'future_inference_level'
    }],
  ]) {
    const payload = structuredClone(matriz)
    mutate(payload)
    const fixture = createFixtureLoader({ document: payload })
    await assert.rejects(fixture.load(MUNICIPALITY_ID), { code: 'invalid_payload' }, label)
  }
})

test('D19 falha fechado para limites, unicidade, referências e campos obrigatórios', () => {
  for (const [label, mutate] of [
    ['mais de três causas na meta', (payload) => {
      payload.priorityGoals[1].causes.push(clonedCause(payload.priorityGoals[0].causes[0], 'F_SYNTH_LIMIT'))
    }],
    ['mais de dez causas no total', (payload) => {
      payload.priorityGoals[0].causes.push(
        clonedCause(payload.priorityGoals[0].causes[0], 'F_SYNTH_TOTAL_A'),
        clonedCause(payload.priorityGoals[0].causes[0], 'F_SYNTH_TOTAL_B'),
      )
    }],
    ['factorId repetido entre metas', (payload) => {
      payload.priorityGoals[1].causes[0].factorId = payload.priorityGoals[0].causes[0].factorId
      payload.priorityGoals[1].causes[0].firstStep.ref = payload.priorityGoals[0].causes[0].factorId
    }],
    ['causesShownIn aponta meta ausente', (payload) => { payload.goalsWithoutOwnCause[0].causesShownIn = ['99.a'] }],
    ['meta sem título', (payload) => { payload.priorityGoals[0].title = '' }],
    ['meta sem referência', (payload) => { payload.priorityGoals[0].referenceRaw = '' }],
    ['meta sem justificativa', (payload) => { payload.priorityGoals[0].severity.placementRationale = '' }],
    ['mediana com campo desconhecido', (payload) => { payload.priorityGoals[0].severity.peerBenchmark.extra = true }],
    ['mediana sem diferença', (payload) => { delete payload.priorityGoals[0].severity.peerBenchmark.differenceRaw }],
    ['mediana de outro ano', (payload) => { payload.priorityGoals[0].severity.peerBenchmark.year = '2024' }],
    ['mediana com outra unidade', (payload) => { payload.priorityGoals[0].severity.peerBenchmark.unit = 'count' }],
    ['mediana com n divergente', (payload) => { payload.priorityGoals[0].severity.peerBenchmark.n = 87 }],
    ['diferença para mediana inconsistente', (payload) => { payload.priorityGoals[0].severity.peerBenchmark.differenceRaw = '0' }],
  ]) {
    const payload = structuredClone(matriz)
    mutate(payload)
    assert.throws(() => parsePne2026Matriz(payload), undefined, label)
  }
})

test('as demais regras próprias da matriz permanecem fail-closed', () => {
  for (const [label, mutate] of [
    ['proofStatus desconhecido', (payload) => { payload.priorityGoals[0].causes[0].proofStatus = 'unknown' }],
    ['proof nula com sinal adverso', (payload) => { payload.priorityGoals[0].causes[0].proof = null }],
    ['proof presente sem sinal adverso', (payload) => {
      const withoutProof = allCauses(payload).find((cause) => cause.proof === null)
      withoutProof.proof = structuredClone(payload.priorityGoals[0].causes[0].proof)
    }],
    ['inferência proibida na proof', (payload) => { payload.priorityGoals[0].causes[0].proof.maxInference = 'declared_existence_only' }],
    ['distância desconhecida', (payload) => { payload.priorityGoals[0].severity.distanceToTarget = 'far' }],
    ['desvio desconhecido', (payload) => { payload.priorityGoals[0].severity.peerDeviation = 'worse' }],
    ['governabilidade desconhecida', (payload) => { payload.priorityGoals[0].causes[0].governability = 'external' }],
    ['razão desconhecida', (payload) => { payload.otherPossibleCauses[0].reason = 'unknown' }],
  ]) {
    const payload = structuredClone(matriz)
    mutate(payload)
    assert.throws(() => parsePne2026Matriz(payload), undefined, label)
  }
})

test('proof.maxInference usa vocabulário fechado com os três níveis públicos', () => {
  assert.deepEqual(MATRIZ_PROOF_MAX_INFERENCES, [
    'measured_value_within_source_scope',
    'known_cases_or_events_only',
    'contextual_association_only',
  ])

  for (const maxInference of MATRIZ_PROOF_MAX_INFERENCES) {
    const payload = structuredClone(matriz)
    payload.priorityGoals[0].causes[0].proof.maxInference = maxInference
    assert.doesNotThrow(() => parsePne2026Matriz(payload), maxInference)
  }
})

test('Nova Santa Rita preserva sete metas, nove causas únicas e a ordem do artefato', () => {
  const expected = [
    ['1.a', ['F_DISTANCE']],
    ['5.a', ['F_ATTEND', 'F_FOUNDATION', 'F_TIME_QUALITY']],
    ['11.c', ['F_EJA_FIT']],
    ['17.a', ['F_TEACH_MATCH']],
    ['4.a', ['F_DISASTER']],
    ['4.b', ['F_REPETITION']],
    ['19.c', ['F_BASIC_INFRA']],
  ]
  assert.deepEqual(
    matriz.priorityGoals.map((goal) => [goal.goalId, goal.causes.map((cause) => cause.factorId)]),
    expected,
  )
  assert.equal(allCauses().length, 9)
  assert.equal(new Set(allCauses().map((cause) => cause.factorId)).size, 9)
  assert.equal(matriz.goalsWithoutOwnCause.length, 11)
  assert.deepEqual(
    matriz.goalsWithoutOwnCause.find((goal) => goal.goalId === '3.a')?.causesShownIn,
    ['5.a'],
  )
  const noAdverse = allCauses().filter((cause) => cause.proofStatus === 'no_adverse_local_signal')
  assert.deepEqual(noAdverse.map((cause) => cause.factorId), ['F_FOUNDATION'])
  assert.equal(noAdverse[0].proof, null)
})

test('falha de rede vira erro estruturado e é reportada uma única vez', async () => {
  const fixture = createFixtureLoader({ municipalError: new Error('offline') })
  await assert.rejects(fixture.load(MUNICIPALITY_ID), { code: 'municipality_unavailable' })
  await assert.rejects(fixture.load(MUNICIPALITY_ID), { code: 'municipality_unavailable' })
  assert.equal(fixture.logs.length, 1)
})

test('storage v5 da matriz usa chave de frente, prefixo e schema próprios', () => {
  const scope = { municipalityIbge7: MUNICIPALITY_ID, referenceDate: matriz.referenceDate }
  const serialized = serializeMatrizPlan(
    scope,
    [
      { key: '5.a|avaliar-e-recompor', status: 'doing', note: 'Em revisão' },
      { key: '1.a|ampliar-oferta', status: 'todo', note: '' },
      { key: '1.a|ampliar-oferta', status: 'todo', note: '' },
    ],
  )
  assert.equal(MATRIZ_FRONTS_STORAGE_KEY_PREFIX, 'pne_matriz_frentes_v5')
  assert.equal(JSON.parse(serialized).schemaVersion, MATRIZ_FRONTS_SCHEMA_VERSION)
  assert.deepEqual(
    parseMatrizPlan(serialized, scope),
    [
      { key: '1.a|ampliar-oferta', status: 'todo', note: '' },
      { key: '5.a|avaliar-e-recompor', status: 'doing', note: 'Em revisão' },
    ],
  )
  assert.deepEqual(parseMatrizPlan(serialized, { ...scope, referenceDate: '2026-08-15' }), [])
  assert.throws(() => serializeMatrizPlan(scope, [{ key: 'F_ATTEND', status: 'todo', note: '' }]))
})
