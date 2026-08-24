import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

import {
  buildPublication,
  buildPublicSchema,
  FORESIGHT_GENERATOR_VERSION,
  slugify,
} from '../generate-foresight-educacao.mjs'
import {
  createForesightEducacaoLoader,
  FORESIGHT_DOCUMENT_SCHEMA,
  FORESIGHT_MANIFEST_PATH,
  FORESIGHT_MANIFEST_SCHEMA,
  FORESIGHT_MUNICIPAL_PATH,
  FORESIGHT_PUBLICATION_SCOPE,
  FORESIGHT_SCENARIO_COUNT,
  FORESIGHT_SOURCE_VERSION,
  ForesightLoadError,
  parseForesightDocument,
  parseForesightManifest,
  serializeForContentVersion,
} from '../../src/features/foresight/foresightEducacaoLoader.js'

const NOVA_SANTA_RITA = '4313375'
const SAO_LEOPOLDO = '4318705'
const MULITERNO = '4312625'

const manifestRaw = await readFile(
  new URL('../../public/data/foresight-educacao/manifest.json', import.meta.url),
  'utf8',
)
const rawByMunicipality = new Map()
for (const municipalityId of [NOVA_SANTA_RITA, SAO_LEOPOLDO]) {
  rawByMunicipality.set(
    municipalityId,
    await readFile(
      new URL(`../../public/data/foresight-educacao/municipios/${municipalityId}.json`, import.meta.url),
      'utf8',
    ),
  )
}
const manifest = JSON.parse(manifestRaw)

function sha256(text) {
  return createHash('sha256').update(Buffer.from(text, 'utf8')).digest('hex')
}

function createFixtureLoader({ manifestText = manifestRaw, municipalTexts = rawByMunicipality } = {}) {
  const calls = []
  const logs = []
  const loader = createForesightEducacaoLoader({
    fetchText: async (path, options) => {
      calls.push({ options, path })
      if (path === FORESIGHT_MANIFEST_PATH) return manifestText
      const match = /municipios\/(\d{7})\.json$/.exec(path)
      const text = match ? municipalTexts.get(match[1]) : undefined
      if (text === undefined) throw new Error(`HTTP 404 em ${path}`)
      return text
    },
    logger: (...items) => logs.push(items),
  })
  return { calls, loader, logs }
}

test('o manifesto publicado é válido e declara o piloto', () => {
  const parsed = parseForesightManifest(manifest)
  assert.equal(parsed.schemaVersion, FORESIGHT_MANIFEST_SCHEMA)
  assert.equal(parsed.documentSchemaVersion, FORESIGHT_DOCUMENT_SCHEMA)
  assert.equal(parsed.sourceVersion, FORESIGHT_SOURCE_VERSION)
  assert.equal(parsed.publicationScope, FORESIGHT_PUBLICATION_SCOPE)
  assert.equal(parsed.generatorVersion, FORESIGHT_GENERATOR_VERSION)
  assert.equal(parsed.horizonStateYear, 2031)
  assert.equal(parsed.scanThroughYear, 2036)
  assert.deepEqual(
    parsed.municipalities.map((entry) => entry.ibgeCode),
    [NOVA_SANTA_RITA, SAO_LEOPOLDO],
  )
})

test('cada entrada do manifesto reconcilia tamanho e resumo com o arquivo publicado', () => {
  for (const entry of manifest.municipalities) {
    const raw = rawByMunicipality.get(entry.ibgeCode)
    assert.equal(Buffer.byteLength(raw, 'utf8'), entry.byteSize, entry.ibgeCode)
    assert.equal(sha256(raw), entry.contentHash, entry.ibgeCode)
    const document = JSON.parse(raw)
    assert.equal(document.contentVersion, entry.contentVersion, entry.ibgeCode)
    assert.equal(sha256(serializeForContentVersion(document)), entry.contentVersion, entry.ibgeCode)
  }
})

test('Nova Santa Rita carrega com identidade e integridade conferidas', async () => {
  const { loader } = createFixtureLoader()
  const result = await loader.load(NOVA_SANTA_RITA)
  assert.equal(result.municipalityId, NOVA_SANTA_RITA)
  assert.equal(result.municipalityName, 'Nova Santa Rita')
  assert.equal(result.integrity, 'verified')
  assert.equal(result.document.municipality.ibgeCode, NOVA_SANTA_RITA)
  assert.equal(result.document.scenarios.length, FORESIGHT_SCENARIO_COUNT)
})

test('São Leopoldo carrega com identidade e integridade conferidas', async () => {
  const { loader } = createFixtureLoader()
  const result = await loader.load(SAO_LEOPOLDO)
  assert.equal(result.municipalityId, SAO_LEOPOLDO)
  assert.equal(result.municipalityName, 'São Leopoldo')
  assert.equal(result.integrity, 'verified')
  assert.equal(result.document.municipality.ibgeCode, SAO_LEOPOLDO)
})

test('Muliterno não está publicado e a leitura falha fechada', async () => {
  const { loader } = createFixtureLoader()
  assert.equal(manifest.municipalities.some((entry) => entry.ibgeCode === MULITERNO), false)
  await assert.rejects(
    () => loader.load(MULITERNO),
    (error) => {
      assert.ok(error instanceof ForesightLoadError)
      assert.equal(error.code, 'municipality_not_published')
      assert.equal(error.municipalityId, MULITERNO)
      return true
    },
  )
})

test('município sem arquivo publicado não aparece na lista de publicados', async () => {
  const { loader } = createFixtureLoader()
  const published = await loader.listPublishedMunicipalityIds()
  assert.deepEqual(published, [NOVA_SANTA_RITA, SAO_LEOPOLDO])
  assert.equal(published.includes(MULITERNO), false)
  assert.equal(published.includes('4300109'), false)
})

test('trocar de município troca o pacote inteiro, sem reaproveitar o anterior', async () => {
  const { loader } = createFixtureLoader()
  const first = await loader.load(NOVA_SANTA_RITA)
  const second = await loader.load(SAO_LEOPOLDO)
  const third = await loader.load(NOVA_SANTA_RITA)

  assert.notEqual(first.contentHash, second.contentHash)
  assert.equal(third.contentHash, first.contentHash)
  assert.equal(second.document.municipality.ibgeCode, SAO_LEOPOLDO)
  assert.equal(third.document.municipality.ibgeCode, NOVA_SANTA_RITA)
  assert.notDeepEqual(
    first.document.scenarios.map((scenario) => scenario.sections),
    second.document.scenarios.map((scenario) => scenario.sections),
  )
})

test('a leitura é deduplicada por resumo e código, e o manifesto é buscado uma vez', async () => {
  const { calls, loader } = createFixtureLoader()
  await Promise.all([
    loader.load(NOVA_SANTA_RITA),
    loader.load(NOVA_SANTA_RITA),
    loader.load(NOVA_SANTA_RITA),
  ])
  assert.equal(calls.filter((call) => call.path === FORESIGHT_MANIFEST_PATH).length, 1)
  assert.equal(
    calls.filter((call) => call.path === FORESIGHT_MUNICIPAL_PATH.replace('{municipalityId}', NOVA_SANTA_RITA)).length,
    1,
  )
})

test('arquivo de outro município é recusado mesmo com caminho correto', async () => {
  const swapped = new Map(rawByMunicipality)
  swapped.set(NOVA_SANTA_RITA, rawByMunicipality.get(SAO_LEOPOLDO))
  const { loader } = createFixtureLoader({ municipalTexts: swapped })
  await assert.rejects(
    () => loader.load(NOVA_SANTA_RITA),
    (error) => {
      assert.equal(error.code, 'invalid_payload')
      assert.match(error.message, /resumo do arquivo diverge do manifesto/)
      return true
    },
  )
})

test('identidade municipal divergente do manifesto é recusada', async () => {
  const document = JSON.parse(rawByMunicipality.get(NOVA_SANTA_RITA))
  document.municipality = { ...document.municipality, ibgeCode: SAO_LEOPOLDO }
  const mutated = `${JSON.stringify(document, null, 2)}\n`

  const mutatedManifest = structuredClone(manifest)
  const entry = mutatedManifest.municipalities.find((item) => item.ibgeCode === NOVA_SANTA_RITA)
  entry.contentHash = sha256(mutated)
  entry.byteSize = Buffer.byteLength(mutated, 'utf8')

  const texts = new Map(rawByMunicipality)
  texts.set(NOVA_SANTA_RITA, mutated)
  const { loader } = createFixtureLoader({
    manifestText: JSON.stringify(mutatedManifest),
    municipalTexts: texts,
  })

  await assert.rejects(
    () => loader.load(NOVA_SANTA_RITA),
    (error) => {
      assert.equal(error.code, 'invalid_payload')
      assert.match(error.message, /pertence a outro município/)
      return true
    },
  )
})

test('resumo divergente do manifesto é recusado', async () => {
  const mutatedManifest = structuredClone(manifest)
  const entry = mutatedManifest.municipalities.find((item) => item.ibgeCode === NOVA_SANTA_RITA)
  entry.contentHash = entry.contentHash.replace(/^./, entry.contentHash[0] === 'a' ? 'b' : 'a')
  const { loader } = createFixtureLoader({ manifestText: JSON.stringify(mutatedManifest) })

  await assert.rejects(
    () => loader.load(NOVA_SANTA_RITA),
    (error) => {
      assert.equal(error.code, 'invalid_payload')
      assert.match(error.message, /resumo do arquivo diverge do manifesto/)
      return true
    },
  )
})

test('versão de conteúdo divergente é recusada mesmo com resumo coerente', async () => {
  const document = JSON.parse(rawByMunicipality.get(NOVA_SANTA_RITA))
  document.contentVersion = sha256('outro conteúdo')
  const mutated = `${JSON.stringify(document, null, 2)}\n`

  const mutatedManifest = structuredClone(manifest)
  const entry = mutatedManifest.municipalities.find((item) => item.ibgeCode === NOVA_SANTA_RITA)
  entry.contentHash = sha256(mutated)
  entry.byteSize = Buffer.byteLength(mutated, 'utf8')

  const texts = new Map(rawByMunicipality)
  texts.set(NOVA_SANTA_RITA, mutated)
  const { loader } = createFixtureLoader({
    manifestText: JSON.stringify(mutatedManifest),
    municipalTexts: texts,
  })

  await assert.rejects(
    () => loader.load(NOVA_SANTA_RITA),
    (error) => {
      assert.match(error.message, /versão de conteúdo divergente/)
      return true
    },
  )
})

test('manifesto ausente não deixa nenhum município publicado', async () => {
  const loader = createForesightEducacaoLoader({
    fetchText: async () => { throw new Error('HTTP 404') },
    logger: () => {},
  })
  assert.deepEqual(await loader.listPublishedMunicipalityIds(), [])
})

test('código municipal inválido é recusado antes de qualquer leitura', async () => {
  const { calls, loader } = createFixtureLoader()
  await assert.rejects(() => loader.load('43133'), (error) => {
    assert.equal(error.code, 'invalid_municipality')
    return true
  })
  assert.equal(calls.length, 0)
})

test('cada município publica exatamente quatro cenários com títulos únicos', () => {
  for (const [municipalityId, raw] of rawByMunicipality) {
    const document = parseForesightDocument(JSON.parse(raw))
    assert.equal(document.scenarios.length, FORESIGHT_SCENARIO_COUNT, municipalityId)
    const titles = document.scenarios.map((scenario) => scenario.title)
    assert.equal(new Set(titles).size, FORESIGHT_SCENARIO_COUNT, municipalityId)
    const slugs = document.scenarios.map((scenario) => scenario.slug)
    assert.equal(new Set(slugs).size, FORESIGHT_SCENARIO_COUNT, municipalityId)
    for (const scenario of document.scenarios) {
      assert.equal(scenario.slug, slugify(scenario.title), municipalityId)
    }
  }
})

test('a subseção específica é omitida quando a origem não a traz', () => {
  const document = parseForesightDocument(JSON.parse(rawByMunicipality.get(NOVA_SANTA_RITA)))
  const withoutSpecificLimit = document.scenarios.filter(
    (scenario) => !scenario.sections.some((section) => section.key === 'limite-especifico'),
  )
  assert.ok(withoutSpecificLimit.length > 0, 'ao menos um cenário exercita a omissão')
  for (const scenario of withoutSpecificLimit) {
    assert.equal(scenario.sections.length, 6)
    assert.equal(scenario.sections.at(-1).key, 'o-que-acompanhar')
  }
  for (const scenario of document.scenarios) {
    for (const section of scenario.sections) {
      assert.ok(section.items.length > 0, `${scenario.slug}/${section.key} não pode ser uma seção vazia`)
    }
  }
})

test('as condições comuns aparecem uma única vez, fora dos cenários', () => {
  for (const [municipalityId, raw] of rawByMunicipality) {
    const document = parseForesightDocument(JSON.parse(raw))
    const shared = document.sharedConditions.items
    assert.ok(shared.length > 0, municipalityId)
    assert.equal(new Set(shared).size, shared.length, municipalityId)
    const scenarioTexts = document.scenarios.flatMap(
      (scenario) => scenario.sections.flatMap((section) => section.items),
    )
    for (const condition of shared) {
      assert.equal(scenarioTexts.includes(condition), false, `${municipalityId}: condição comum repetida no cenário`)
    }
  }
})

/*
 * Mutações adversariais: cada uma injeta num pacote válido exatamente o que a
 * camada pública proíbe e confere que a leitura falha fechada. São permanentes
 * de propósito — o que impede a regressão não é a injeção feita uma vez, é o
 * teste que a repete a cada execução.
 */
const MUTATIONS = [
  {
    name: 'identificador interno de cenário no texto público',
    mutate: (document) => {
      document.scenarios[0].summary = 'O cenário C2 se forma pela combinação MC-001.'
    },
    expected: /identificador interno de cenário/,
  },
  {
    name: 'identificador de relação no texto público',
    mutate: (document) => {
      document.sharedConditions.items[0] = 'A relação RP-09 sustenta esta leitura.'
    },
    expected: /identificador interno de relação/,
  },
  {
    name: 'enum interno na prosa pública',
    mutate: (document) => {
      document.startingPoint.tensions[0] = 'A série ficou em not_located durante o período.'
    },
    expected: /identificador snake_case|termo proibido/,
  },
  {
    name: 'fingerprint no texto público',
    mutate: (document) => {
      document.scenarios[0].sections[0].items[0] = 'Base 164bf2f462e1b8d4e055fd8164964a0cf233304e.'
    },
    expected: /fingerprint ou hash/,
  },
  {
    name: 'projeção numérica futura',
    mutate: (document) => {
      document.startingPoint.movements[0] = 'Em 2031, a cobertura da pré-escola chega a 99,2%.'
    },
    expected: /número associado a ano futuro|ano futuro em texto/,
  },
  {
    name: 'ano futuro numa janela observada',
    mutate: (document) => {
      document.observedSeries.items[0].fullPeriod.endYear = 2031
    },
    expected: /precisa ser um ano observado/,
  },
  {
    name: 'cenário destacado como o melhor',
    mutate: (document) => {
      document.scenarios[0].summary = 'Este é o melhor cenário para o município.'
    },
    expected: /termo proibido/,
  },
  {
    name: 'quinto cenário publicado',
    mutate: (document) => {
      document.scenarios.push(structuredClone(document.scenarios[0]))
    },
    expected: /exatamente 4 cenários/,
  },
  {
    name: 'seção fora da estrutura pública',
    mutate: (document) => {
      document.scenarios[0].sections[0].key = 'secao-inventada'
    },
    expected: /não pertence à estrutura pública/,
  },
  {
    name: 'campo desconhecido no pacote',
    mutate: (document) => {
      document.probabilidade = 0.4
    },
    expected: /campo desconhecido/,
  },
]

for (const mutation of MUTATIONS) {
  test(`recusa: ${mutation.name}`, async () => {
    const document = JSON.parse(rawByMunicipality.get(NOVA_SANTA_RITA))
    mutation.mutate(document)
    assert.throws(() => parseForesightDocument(document), mutation.expected)

    const mutated = `${JSON.stringify(document, null, 2)}\n`
    const mutatedManifest = structuredClone(manifest)
    const entry = mutatedManifest.municipalities.find((item) => item.ibgeCode === NOVA_SANTA_RITA)
    entry.contentHash = sha256(mutated)
    entry.byteSize = Buffer.byteLength(mutated, 'utf8')
    const texts = new Map(rawByMunicipality)
    texts.set(NOVA_SANTA_RITA, mutated)

    const { loader } = createFixtureLoader({
      manifestText: JSON.stringify(mutatedManifest),
      municipalTexts: texts,
    })
    await assert.rejects(() => loader.load(NOVA_SANTA_RITA), (error) => {
      assert.equal(error.code, 'invalid_payload')
      return true
    })
  })
}

test('controle: o pacote intacto continua sendo aceito depois das mutações', async () => {
  const { loader } = createFixtureLoader()
  const result = await loader.load(NOVA_SANTA_RITA)
  assert.equal(result.integrity, 'verified')
  assert.equal(result.document.scenarios.length, FORESIGHT_SCENARIO_COUNT)
})

test('o gerador público é determinístico e reproduz os arquivos publicados', () => {
  const first = buildPublication()
  const second = buildPublication()

  assert.deepEqual(first.manifest, second.manifest)
  assert.deepEqual(
    first.files.map((file) => file.serialized),
    second.files.map((file) => file.serialized),
  )
  assert.equal(`${JSON.stringify(first.manifest, null, 2)}\n`, manifestRaw)
  for (const file of first.files) {
    assert.equal(file.serialized, rawByMunicipality.get(file.document.municipality.ibgeCode))
  }
  assert.deepEqual(first.refused.map((refusal) => refusal.candidate), ['muliterno'])
  assert.equal(first.refused[0].ibgeCode, MULITERNO)
})

test('o esquema público acompanha os dados e declara as regras da página', async () => {
  const schema = JSON.parse(
    await readFile(new URL('../../public/data/foresight-educacao/schema.json', import.meta.url), 'utf8'),
  )
  assert.deepEqual(schema, buildPublicSchema())
  assert.equal(schema.documentSchemaVersion, FORESIGHT_DOCUMENT_SCHEMA)
  assert.equal(schema.manifestSchemaVersion, FORESIGHT_MANIFEST_SCHEMA)
  assert.equal(schema.scenarioCount, FORESIGHT_SCENARIO_COUNT)
  assert.deepEqual(schema.horizon, { stateYear: 2031, scanThroughYear: 2036 })
})
