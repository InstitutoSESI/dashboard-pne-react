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
import { mkdir, mkdtemp, readFile, readdir, rm, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import path from 'node:path'
import test from 'node:test'

import {
  buildPublication,
  publishPublicationTransactionally,
  validatePublicationDirectory,
} from '../generate-regioes.mjs'
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
const pneCatalog = JSON.parse(await readRepositoryFile('public/data/indicadores.json'))
  .cycles.pne_2026_2036

function pneIndicator(document, key) {
  return document.pne2026.categorias
    .flatMap((category) => category.indicadores)
    .find((indicator) => indicator.chave === key)
}

function valueAtYear(result, year) {
  return result.series?.find((point) => point.ano === year)?.valor
    ?? (result.end_year === year ? result.end_value : null)
}

function median(values) {
  const ordered = [...values].toSorted((left, right) => left - right)
  const middle = Math.floor(ordered.length / 2)
  const value = ordered.length % 2 === 1
    ? ordered[middle]
    : (ordered[middle - 1] + ordered[middle]) / 2
  return Math.round(value * 100) / 100
}

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

test('cada região publica todo o catálogo PNE 2026–2036 e reconcilia o resumo', () => {
  const catalogKeys = pneCatalog.categories
    .flatMap((category) => category.items)
    .map((indicator) => indicator.key)
    .toSorted()
  assert.equal(catalogKeys.length, 49)
  for (const [slug, raw] of regionRawBySlug) {
    const published = JSON.parse(raw)
    const indicators = published.pne2026.categorias.flatMap((category) => category.indicadores)
    assert.deepEqual(
      indicators.map((indicator) => indicator.chave).toSorted(),
      catalogKeys,
      `${slug} não publicou o catálogo completo`,
    )
    assert.equal(published.pne2026.totalIndicadores, indicators.length)
    assert.equal(
      published.pne2026.totalReferencias,
      indicators.filter((indicator) => indicator.referencia !== null).length,
    )
    assert.equal(
      published.pne2026.indicadoresSemResultado,
      indicators.filter((indicator) => indicator.resultado.valor === null).length,
    )
  }
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
  let manualSchools = 0
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
    manualSchools += municipal.blocos.rede_escolar.series.total
      .find((point) => point.ano === 2025).valor
  }

  assert.equal(
    published.matriculas.series.total.find((point) => point.ano === 2025).valor,
    manualTotal,
  )
  assert.equal(
    published.matriculas.series.por_localizacao.rural.find((point) => point.ano === 2025).valor,
    manualRural,
  )
  assert.equal(
    published.educacao.contagens.find((indicator) => indicator.chave === 'escolas').valor,
    manualSchools,
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

  const pneCreche = pneIndicator(published, 'creche')
  assert.equal(pneCreche.resultado.metodo, 'regional_ratio')
  assert.equal(pneCreche.resultado.valor, regional.valor)
  assert.equal(pneCreche.resultado.ano, regional.ano)
})

test('medianas municipais e referências do PNE são reproduzíveis fora do gerador', async () => {
  const region = regionsConfig.regions.find((candidate) => candidate.slug === SERRA)
  const published = JSON.parse(regionRawBySlug.get(SERRA))
  const adequacy = pneIndicator(published, 'adequacao_ai')
  const values = []
  for (const ibgeCode of region.municipalityIbgeCodes) {
    const index = JSON.parse(await readRepositoryFile(`public/data/municipios/${ibgeCode}/index.json`))
    const value = valueAtYear(index.pne_2026_2036.indicadores.adequacao_ai, adequacy.resultado.ano)
    if (typeof value === 'number' && Number.isFinite(value)) values.push(value)
  }
  assert.equal(adequacy.resultado.metodo, 'municipal_median')
  assert.equal(adequacy.resultado.valor, median(values))
  assert.equal(adequacy.resultado.municipiosComDado, values.length)

  const preschool = pneIndicator(published, 'pre_escola')
  assert.deepEqual(
    {
      ano: preschool.referencia.ano,
      direcao: preschool.referencia.direcao,
      valor: preschool.referencia.valor,
    },
    { ano: 2028, direcao: 'at_least', valor: 100 },
  )
  const literacy = pneIndicator(published, 'alfabetizacao')
  assert.equal(literacy.resultado.valor, null)
  assert.equal(literacy.resultado.municipiosComDado, 0)
  assert.notEqual(literacy.resultado.valor, 0)
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
  unknownSchema.schemaVersion = 'regioes-3.0.0'
  assert.throws(() => parseRegiaoDocument(unknownSchema), /schemaVersion/)

  const extraField = JSON.parse(regionRawBySlug.get(SERRA))
  extraField.observacao = 'fora do contrato'
  assert.throws(() => parseRegiaoDocument(extraField), /campos divergentes/)
})

/*
 * As duas conferências que o manifesto declarava sem verificar. Um par
 * (arquivo, manifesto) internamente coerente é a forma mais barata de burlar
 * um leitor que só compara valores declarados entre si: o resumo bate, o
 * tamanho bate, e a versão de conteúdo é o que o falsificador quiser. A defesa
 * é recompor — e recompor é o que este teste guarda.
 */
test('o leitor recompõe versão de conteúdo e confere o tamanho declarado', async () => {
  const regionPath = REGIOES_REGION_PATH.replace('{regionSlug}', SERRA)
  const raw = regionRawBySlug.get(SERRA)

  const inflatedSize = JSON.parse(manifestRaw)
  inflatedSize.regions.find((entry) => entry.slug === SERRA).byteSize += 7
  const withBadSize = createFixtureLoader(
    new Map([[REGIOES_MANIFEST_PATH, `${JSON.stringify(inflatedSize, null, 2)}\n`]]),
  )
  await assert.rejects(withBadSize.loadRegion(SERRA), /tamanho do arquivo diverge/)

  // Falsificação coerente: contentVersion trocado no arquivo E no manifesto,
  // com resumo e tamanho recalculados para casar. Só a recomposição pega.
  const forgedDocument = JSON.parse(raw)
  forgedDocument.contentVersion = 'f'.repeat(64)
  const forgedRaw = `${JSON.stringify(forgedDocument, null, 2)}\n`
  const forgedManifest = JSON.parse(manifestRaw)
  const forgedEntry = forgedManifest.regions.find((entry) => entry.slug === SERRA)
  forgedEntry.contentVersion = 'f'.repeat(64)
  forgedEntry.contentHash = createHash('sha256').update(forgedRaw, 'utf8').digest('hex')
  forgedEntry.byteSize = Buffer.byteLength(forgedRaw, 'utf8')
  const withForgedVersion = createFixtureLoader(
    new Map([
      [REGIOES_MANIFEST_PATH, `${JSON.stringify(forgedManifest, null, 2)}\n`],
      [regionPath, forgedRaw],
    ]),
  )
  await assert.rejects(withForgedVersion.loadRegion(SERRA), /versão de conteúdo não confere/)

  // E o publicado de verdade continua passando pelas duas conferências.
  const honest = await createFixtureLoader().loadRegion(SERRA)
  assert.equal(honest.integrity, 'verified')
  const { contentVersion, ...documentWithoutVersion } = JSON.parse(raw)
  assert.equal(
    createHash('sha256').update(serializeForContentVersion(documentWithoutVersion), 'utf8').digest('hex'),
    contentVersion,
  )
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

test('a publicação regional promove o lote inteiro, preserva idênticos e reverte falha', async (context) => {
  const temporaryRoot = await mkdtemp(path.join(tmpdir(), 'pne-regioes-'))
  context.after(() => rm(temporaryRoot, { recursive: true, force: true }))
  const outputRoot = path.join(temporaryRoot, 'output')
  const stagingRoot = path.join(temporaryRoot, 'staging')
  await mkdir(outputRoot, { recursive: true })
  const legacy = new Map([
    ['manifest.json', '{"legacy":true}\n'],
    ['serra.json', '{"legacy":"serra"}\n'],
    ['orphan.json', '{"legacy":"orphan"}\n'],
  ])
  for (const [filename, contents] of legacy) {
    await writeFile(path.join(outputRoot, filename), contents, 'utf8')
  }

  const publication = buildPublication()
  assert.throws(
    () => publishPublicationTransactionally(publication, {
      outputRoot,
      stagingRoot,
      afterTargetPromoted: () => {
        throw new Error('falha injetada depois da primeira promoção')
      },
    }),
    /falha injetada/,
  )
  assert.deepEqual((await readdir(outputRoot)).toSorted(), [...legacy.keys()].toSorted())
  for (const [filename, contents] of legacy) {
    assert.equal(await readFile(path.join(outputRoot, filename), 'utf8'), contents)
  }

  const firstReport = publishPublicationTransactionally(publication, { outputRoot, stagingRoot })
  assert.equal(firstReport.removed.includes('orphan.json'), true)
  assert.equal(validatePublicationDirectory(outputRoot).regionCount, 10)
  const secondReport = publishPublicationTransactionally(publication, { outputRoot, stagingRoot })
  assert.equal(secondReport.created.length, 0)
  assert.equal(secondReport.updated.length, 0)
  assert.equal(secondReport.removed.length, 0)
  assert.equal(secondReport.preserved.length, 11)
})

test('a tabela de matrículas usa participação regional, sem coluna repetitiva', async () => {
  const source = await readRepositoryFile('src/features/regional/AnaliseRegionalPage.tsx')
  assert.match(source, /Participação no total regional/)
  assert.doesNotMatch(source, /todos os municípios/i)
  assert.doesNotMatch(source, /<th[^>]*>Cobertura<\/th>/i)
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
