/*
 * Contrato do painel regional publicado: gerador e leitor precisam concordar
 * byte a byte, e o leitor precisa recusar tudo o que não veio do gerador.
 *
 * O teste também guarda a regra de agregação, que é o ponto em que o legado
 * errava: contagem soma, percentual nasce da divisão dos totais somados, e um
 * ano com cobertura parcial não publica valor. Os spot-checks refazem a soma a
 * partir dos artefatos municipais, sem passar pelo gerador.
 */

import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

import { buildPublication } from '../generate-regioes.mjs'
import {
  REGIOES_DOCUMENT_SCHEMA,
  REGIOES_MANIFEST_PATH,
  REGIOES_MANIFEST_SCHEMA,
  REGIOES_REGION_PATH,
  RegionalLoadError,
  createRegionalLoader,
  parseRegiaoDocument,
  parseRegioesManifest,
  serializeForContentVersion,
} from '../../src/features/regional/regionalLoader.js'

const SERRA = 'serra'
const readRepositoryFile = (relativePath) =>
  readFile(new URL(`../../${relativePath}`, import.meta.url), 'utf8')

const manifestRaw = await readRepositoryFile('public/data/regioes/manifest.json')
const manifest = parseRegioesManifest(JSON.parse(manifestRaw))
const regionRawBySlug = new Map()
for (const entry of manifest.regions) {
  regionRawBySlug.set(entry.slug, await readRepositoryFile(`public/data/regioes/${entry.slug}.json`))
}

const regionsConfig = JSON.parse(await readRepositoryFile('config/regions/rs.json'))
const municipalityRegistry = JSON.parse(await readRepositoryFile('config/municipalities/rs.json'))

function createFixtureLoader(overrides = new Map()) {
  return createRegionalLoader({
    logger: () => {},
    fetchText: async (path) => {
      if (overrides.has(path)) return overrides.get(path)
      if (path === REGIOES_MANIFEST_PATH) return manifestRaw
      for (const [slug, raw] of regionRawBySlug) {
        if (path === REGIOES_REGION_PATH.replace('{regionSlug}', slug)) return raw
      }
      throw new Error(`caminho não publicado: ${path}`)
    },
  })
}

test('o publicado é exatamente o que o gerador produz agora', () => {
  const publication = buildPublication()
  assert.equal(
    `${JSON.stringify(publication.manifest, null, 2)}\n`,
    manifestRaw,
    'o manifesto publicado divergiu do gerador',
  )
  assert.equal(publication.files.length, manifest.regionCount)
  for (const file of publication.files) {
    assert.equal(file.serialized, regionRawBySlug.get(file.region.slug), `região ${file.region.slug} divergiu`)
  }
})

test('o manifesto cobre o mapa de regiões e o universo municipal', () => {
  assert.equal(manifest.schemaVersion, REGIOES_MANIFEST_SCHEMA)
  assert.equal(manifest.documentSchemaVersion, REGIOES_DOCUMENT_SCHEMA)
  assert.equal(manifest.stateCode, 'RS')
  assert.equal(manifest.regionCount, regionsConfig.regionCount)
  assert.equal(manifest.municipalityCount, municipalityRegistry.municipalityCount)
  assert.deepEqual(
    manifest.regions.map((entry) => entry.slug).toSorted(),
    regionsConfig.regions.map((region) => region.slug).toSorted(),
  )
})

test('cada arquivo publicado confere resumo, versão e identidade', async () => {
  const loader = createFixtureLoader()
  for (const entry of manifest.regions) {
    const raw = regionRawBySlug.get(entry.slug)
    assert.equal(createHash('sha256').update(raw, 'utf8').digest('hex'), entry.contentHash)
    assert.equal(Buffer.byteLength(raw, 'utf8'), entry.byteSize)

    const { document } = await loader.loadRegion(entry.slug)
    assert.equal(document.regiao.slug, entry.slug)
    assert.equal(document.regiao.nome, entry.name)
    assert.equal(document.regiao.totalMunicipios, entry.municipalityCount)
    assert.equal(document.contentVersion, entry.contentVersion)

    const { contentVersion, ...withoutVersion } = document
    void withoutVersion
    const republished = JSON.parse(raw)
    delete republished.contentVersion
    assert.equal(
      createHash('sha256').update(serializeForContentVersion(republished), 'utf8').digest('hex'),
      contentVersion,
      `contentVersion de ${entry.slug} não reproduz o conteúdo`,
    )
  }
})

test('as regiões particionam o registro municipal sem sobra nem duplicata', () => {
  const owners = new Map()
  for (const [slug, raw] of regionRawBySlug) {
    for (const municipality of JSON.parse(raw).regiao.municipios) {
      assert.equal(owners.has(municipality.ibgeCode), false)
      owners.set(municipality.ibgeCode, slug)
    }
  }
  assert.deepEqual(
    [...owners.keys()].toSorted(),
    municipalityRegistry.municipalities.map(({ ibgeCode }) => ibgeCode).toSorted(),
  )
})

test('contagens regionais somam os municípios, conferidas fora do gerador', async () => {
  const region = regionsConfig.regions.find((candidate) => candidate.slug === SERRA)
  const published = JSON.parse(regionRawBySlug.get(SERRA))

  let manualTotal = 0
  let manualRural = 0
  for (const ibgeCode of region.municipalityIbgeCodes) {
    const municipal = JSON.parse(
      await readRepositoryFile(`public/data/educacao/municipios/${ibgeCode}.json`),
    )
    const total = municipal.blocos.matriculas.series.total.find((point) => point.ano === 2025)
    manualTotal += total.valor
    const rural = (municipal.blocos.matriculas.series.por_localizacao.rural ?? []).find(
      (point) => point.ano === 2025,
    )
    // A ausência da série rural é zero estrutural: o município não tem escola rural.
    manualRural += rural?.valor ?? 0
  }

  assert.equal(
    published.matriculas.series.total.find((point) => point.ano === 2025).valor,
    manualTotal,
  )
  assert.equal(
    published.matriculas.series.por_localizacao.rural.find((point) => point.ano === 2025).valor,
    manualRural,
  )
})

test('percentuais nascem da divisão dos totais somados, não da média dos municípios', async () => {
  const region = regionsConfig.regions.find((candidate) => candidate.slug === SERRA)
  const published = JSON.parse(regionRawBySlug.get(SERRA))

  let numerator = 0
  let denominator = 0
  const municipalRates = []
  for (const ibgeCode of region.municipalityIbgeCodes) {
    const index = JSON.parse(await readRepositoryFile(`public/data/municipios/${ibgeCode}/index.json`))
    const point = index.educacao.atendimento_cenarios.ageCoverage.creche.historical.find(
      (entry) => entry.year === 2025,
    )
    numerator += point.numerator
    denominator += point.denominator
    municipalRates.push((point.numerator / point.denominator) * 100)
  }

  const regional = published.atendimento.indicadores
    .find((indicator) => indicator.chave === 'creche')
    .series.find((point) => point.ano === 2025)
  assert.equal(regional.numerador, numerator)
  assert.equal(regional.denominador, denominator)
  assert.equal(regional.valor, Math.round((numerator / denominator) * 10000) / 100)

  const simpleMean = municipalRates.reduce((sum, rate) => sum + rate, 0) / municipalRates.length
  assert.notEqual(
    Math.round(regional.valor * 100),
    Math.round(simpleMean * 100),
    'a média simples coincidiu com o valor publicado; o teste perdeu o poder de detectar a regressão',
  )
})

test('nenhum ano publicado mistura cobertura parcial com valor', () => {
  for (const [slug, raw] of regionRawBySlug) {
    const published = JSON.parse(raw)
    const expected = published.regiao.totalMunicipios
    for (const indicator of published.atendimento.indicadores) {
      for (const point of indicator.series) {
        if (point.municipiosComDado === expected) continue
        assert.equal(point.valor, null, `${slug}/${indicator.chave}/${point.ano} publicou valor parcial`)
      }
    }
    const countSeries = [
      published.matriculas.series.total,
      published.matriculas.series.integral,
      ...['por_etapa', 'por_dependencia', 'por_localizacao'].flatMap((key) =>
        Object.values(published.matriculas.series[key]),
      ),
    ]
    for (const series of countSeries) {
      for (const point of series) {
        if (point.municipiosComDado === expected) continue
        assert.equal(point.valor, null, `${slug} publicou contagem parcial em ${point.ano}`)
      }
    }
  }
})

test('o leitor recusa resumo, identidade, versão e esquema divergentes', async () => {
  const regionPath = REGIOES_REGION_PATH.replace('{regionSlug}', SERRA)
  const tampered = JSON.parse(regionRawBySlug.get(SERRA))
  tampered.matriculas.series.total[0].valor += 1

  const withBadHash = createFixtureLoader(
    new Map([[regionPath, `${JSON.stringify(tampered, null, 2)}\n`]]),
  )
  await assert.rejects(withBadHash.loadRegion(SERRA), (error) => {
    assert.ok(error instanceof RegionalLoadError)
    assert.equal(error.code, 'invalid_payload')
    assert.equal(error.regionSlug, SERRA)
    return true
  })

  // Manifesto forjado para casar com o arquivo trocado: assim o resumo passa e
  // quem precisa recusar é a checagem de identidade, não a de integridade.
  const forgedManifest = JSON.parse(manifestRaw)
  const sulEntry = forgedManifest.regions.find((entry) => entry.slug === 'sul')
  const serraEntry = forgedManifest.regions.find((entry) => entry.slug === SERRA)
  serraEntry.contentHash = sulEntry.contentHash
  serraEntry.contentVersion = sulEntry.contentVersion
  serraEntry.byteSize = sulEntry.byteSize
  const withForeignRegion = createFixtureLoader(
    new Map([
      [REGIOES_MANIFEST_PATH, `${JSON.stringify(forgedManifest, null, 2)}\n`],
      [regionPath, regionRawBySlug.get('sul')],
    ]),
  )
  await assert.rejects(withForeignRegion.loadRegion(SERRA), /pertence a outra região/)

  const unknownSchema = JSON.parse(regionRawBySlug.get(SERRA))
  unknownSchema.schemaVersion = 'regioes-2.0.0'
  assert.throws(() => parseRegiaoDocument(unknownSchema), /schemaVersion/)

  const extraField = JSON.parse(regionRawBySlug.get(SERRA))
  extraField.observacao = 'fora do contrato'
  assert.throws(() => parseRegiaoDocument(extraField), /campos divergentes/)
})

test('o leitor recusa manifesto quebrado e região não publicada', async () => {
  const brokenManifest = JSON.parse(manifestRaw)
  brokenManifest.municipalityCount += 1
  const withBrokenManifest = createFixtureLoader(
    new Map([[REGIOES_MANIFEST_PATH, `${JSON.stringify(brokenManifest, null, 2)}\n`]]),
  )
  await assert.rejects(withBrokenManifest.loadManifest(), (error) => {
    assert.equal(error.code, 'invalid_manifest')
    return true
  })

  const loader = createFixtureLoader()
  await assert.rejects(loader.loadRegion('regiao-inexistente'), (error) => {
    assert.equal(error.code, 'region_not_published')
    return true
  })
})

test('o painel regional não expõe o nome institucional do recorte', () => {
  const corpus = [manifestRaw, ...regionRawBySlug.values()]
    .join('\n')
    .normalize('NFD')
    .replace(/\p{Diacritic}/gu, '')
    .toLocaleLowerCase('pt-BR')
  for (const token of ['fiergs', 'senai', 'sesi']) {
    assert.equal(corpus.includes(token), false, `o painel regional expõe "${token}"`)
  }
})
