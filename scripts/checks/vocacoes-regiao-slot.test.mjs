/*
 * O slot do Vocações da Região existe antes do conteúdo, e este teste guarda
 * exatamente isso: que a ausência é um estado declarado e verificável, não um
 * descuido.
 *
 * Três garantias: o manifesto vazio é válido e é o que está publicado; nada
 * fica visível ou alcançável enquanto ele estiver vazio; e o pacote regional,
 * quando existir, será validado pelo mesmo contrato do municipal, com a
 * identidade da região no lugar do município — o que o teste exercita com uma
 * fixture derivada de um pacote municipal real.
 */

import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'
import { createHash } from 'node:crypto'
import { mkdtempSync, rmSync, writeFileSync } from 'node:fs'
import { readFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import path from 'node:path'
import test from 'node:test'
import { pathToFileURL } from 'node:url'

import {
  EMPTY_MANIFEST_PUBLICATION_SCOPE,
  EMPTY_MANIFEST_SOURCE_VERSION,
  buildEmptyManifest,
  buildPublication,
  resolveSource,
} from '../generate-vocacoes-regiao.mjs'
import {
  VOCACOES_DOCUMENT_SCHEMA,
  VOCACOES_MANIFEST_PATH,
  VOCACOES_MANIFEST_SCHEMA,
  VOCACOES_REGION_PATH,
  VocacoesLoadError,
  createVocacoesDocumentParser,
  createVocacoesRegiaoLoader,
  parseVocacoesManifest,
  validateRegionIdentity,
} from '../../src/features/vocacoes-regiao/vocacoesRegiaoLoader.js'

/* A politica de visibilidade vive em TypeScript; o teste compila so ela. */
const temporaryOutput = mkdtempSync(path.join(tmpdir(), 'dashboard-pne-vocacoes-'))
writeFileSync(path.join(temporaryOutput, 'package.json'), '{"type":"module"}\n')
execFileSync(
  process.execPath,
  [
    path.resolve('node_modules/typescript/bin/tsc'),
    '--project',
    'scripts/checks/tsconfig.vocacoes.json',
    '--outDir',
    temporaryOutput,
  ],
  { stdio: 'inherit' },
)
process.on('exit', () => rmSync(temporaryOutput, { force: true, recursive: true }))

const { isVocacoesPublished, VOCACOES_PUBLICATION_PENDING } = await import(
  pathToFileURL(path.join(temporaryOutput, 'src/domain/vocacoesRegiaoPublication.js')).href
)

const readRepositoryFile = (relativePath) =>
  readFile(new URL(`../../${relativePath}`, import.meta.url), 'utf8')

const publishedManifestRaw = await readRepositoryFile('public/data/vocacoes-regiao/manifest.json')
const municipalRaw = await readRepositoryFile(
  'public/data/foresight-educacao/municipios/4313375.json',
)

test('o manifesto publicado é o manifesto vazio que o gerador produz', () => {
  const publication = buildPublication()
  assert.equal(`${JSON.stringify(publication.manifest, null, 2)}\n`, publishedManifestRaw)
  assert.deepEqual(publication.files, [])
  assert.equal(publication.available, false)
})

test('o manifesto vazio passa pelo validador de produção', () => {
  const manifest = parseVocacoesManifest(JSON.parse(publishedManifestRaw))
  assert.equal(manifest.schemaVersion, VOCACOES_MANIFEST_SCHEMA)
  assert.equal(manifest.documentSchemaVersion, VOCACOES_DOCUMENT_SCHEMA)
  assert.equal(manifest.scopeType, 'region')
  assert.deepEqual(manifest.regions, [])
})

test('nenhuma região é considerada publicada enquanto o manifesto estiver vazio', async () => {
  const loader = createVocacoesRegiaoLoader({
    logger: () => {},
    fetchText: async (path) => {
      if (path === VOCACOES_MANIFEST_PATH) return publishedManifestRaw
      throw new Error(`caminho não publicado: ${path}`)
    },
  })
  assert.deepEqual(await loader.listPublishedRegionSlugs(), [])
  await assert.rejects(loader.loadRegion('serra'), (error) => {
    assert.ok(error instanceof VocacoesLoadError)
    assert.equal(error.code, 'region_not_published')
    return true
  })
})

test('a decisão de visibilidade fecha antes e depois do manifesto', () => {
  assert.equal(isVocacoesPublished(VOCACOES_PUBLICATION_PENDING, 'serra'), false)
  const empty = { publishedSlugs: new Set(), ready: true }
  assert.equal(isVocacoesPublished(empty, 'serra'), false)
  const published = { publishedSlugs: new Set(['serra']), ready: true }
  assert.equal(isVocacoesPublished(published, 'serra'), true)
  assert.equal(isVocacoesPublished(published, null), false)
})

test('manifesto quebrado é recusado em vez de virar publicação parcial', async () => {
  const broken = JSON.parse(publishedManifestRaw)
  broken.scopeType = 'municipality'
  assert.throws(() => parseVocacoesManifest(broken), /escopo territorial/)

  const extra = JSON.parse(publishedManifestRaw)
  extra.observacao = 'fora do contrato'
  assert.throws(() => parseVocacoesManifest(extra), /fora do contrato/)

  const loader = createVocacoesRegiaoLoader({
    logger: () => {},
    fetchText: async () => `${JSON.stringify(broken, null, 2)}\n`,
  })
  await assert.rejects(loader.loadManifest(), (error) => {
    assert.equal(error.code, 'invalid_manifest')
    return true
  })
})

test('a identidade regional substitui a municipal sem afrouxar o contrato', () => {
  assert.throws(() => validateRegionIdentity({ slug: 'serra' }, 'regiao'), /campos obrigatórios/)
  assert.throws(
    () => validateRegionIdentity({ slug: 'Serra', name: 'Serra', uf: 'RS', municipalityCount: 42 }, 'regiao'),
    /slug/,
  )
  assert.throws(
    () => validateRegionIdentity({ slug: 'serra', name: 'Serra', uf: 'rs', municipalityCount: 42 }, 'regiao'),
    /uf/,
  )
  assert.throws(
    () => validateRegionIdentity({ slug: 'serra', name: 'Serra', uf: 'RS', municipalityCount: 0 }, 'regiao'),
    /municipalityCount/,
  )
  assert.ok(validateRegionIdentity({ slug: 'serra', name: 'Serra', uf: 'RS', municipalityCount: 42 }, 'regiao'))
})

/*
 * A fixture nasce de um pacote municipal publicado: é a transposição literal
 * que a metodologia prevê. Se o validador regional aceitasse menos — ou mais —
 * do que o municipal, este teste falharia.
 */
test('o pacote regional é validado pelo mesmo contrato do municipal', () => {
  const manifest = {
    ...buildEmptyManifest(),
    sourceVersion: 'v0.1.0-regional',
    publicationScope: 'pilot',
  }
  const parseDocument = createVocacoesDocumentParser(manifest)

  const municipal = JSON.parse(municipalRaw)
  const { municipality, ...body } = municipal
  const regional = {
    ...body,
    schemaVersion: VOCACOES_DOCUMENT_SCHEMA,
    sourceVersion: manifest.sourceVersion,
    publicationScope: manifest.publicationScope,
    provenance: {
      ...municipal.provenance,
      methodologySource: manifest.sourceVersion,
      publicationScope: manifest.publicationScope,
    },
    region: { slug: 'serra', name: 'Serra', uf: municipality.uf, municipalityCount: 42 },
  }

  const parsed = parseDocument(regional)
  assert.equal(parsed.region.slug, 'serra')
  assert.equal(parsed.scenarios.length, municipal.scenarios.length)

  const withMunicipality = { ...regional, municipality }
  assert.throws(() => parseDocument(withMunicipality), /campo desconhecido "municipality"/)

  const wrongSource = { ...regional, sourceVersion: EMPTY_MANIFEST_SOURCE_VERSION }
  assert.throws(() => parseDocument(wrongSource), /versão de origem/)

  const wrongScope = { ...regional, publicationScope: EMPTY_MANIFEST_PUBLICATION_SCOPE }
  assert.throws(() => parseDocument(wrongScope), /escopo de publicação/)
})

test('o leitor confere resumo e identidade antes de aceitar um pacote regional', async () => {
  const manifest = {
    ...buildEmptyManifest(),
    sourceVersion: 'v0.1.0-regional',
    publicationScope: 'pilot',
  }
  const municipal = JSON.parse(municipalRaw)
  const { municipality, ...body } = municipal
  const regional = {
    ...body,
    schemaVersion: VOCACOES_DOCUMENT_SCHEMA,
    sourceVersion: manifest.sourceVersion,
    publicationScope: manifest.publicationScope,
    provenance: {
      ...municipal.provenance,
      methodologySource: manifest.sourceVersion,
      publicationScope: manifest.publicationScope,
    },
    region: { slug: 'serra', name: 'Serra', uf: municipality.uf, municipalityCount: 42 },
  }
  const serialized = `${JSON.stringify(regional, null, 2)}\n`
  const contentHash = createHash('sha256').update(serialized, 'utf8').digest('hex')
  const populated = {
    ...manifest,
    generatedAt: regional.generatedAt,
    sourceMethodologyStatus: regional.sourceMethodologyStatus,
    regions: [
      {
        slug: 'serra',
        name: 'Serra',
        uf: municipality.uf,
        path: 'regioes/serra.json',
        municipalityCount: 42,
        contentHash,
        contentVersion: regional.contentVersion,
        byteSize: Buffer.byteLength(serialized, 'utf8'),
        publicationStatus: 'published',
        scenarioCount: regional.scenarios.length,
      },
    ],
  }
  const manifestRaw = `${JSON.stringify(populated, null, 2)}\n`
  const regionPath = VOCACOES_REGION_PATH.replace('{regionSlug}', 'serra')

  const loader = createVocacoesRegiaoLoader({
    logger: () => {},
    fetchText: async (path) => {
      if (path === VOCACOES_MANIFEST_PATH) return manifestRaw
      if (path === regionPath) return serialized
      throw new Error(`caminho não publicado: ${path}`)
    },
  })
  assert.deepEqual(await loader.listPublishedRegionSlugs(), ['serra'])
  const loaded = await loader.loadRegion('serra')
  assert.equal(loaded.document.region.slug, 'serra')
  assert.equal(loaded.entry.contentHash, contentHash)

  const tampered = { ...regional, region: { ...regional.region, name: 'Serra Gaúcha' } }
  const tamperedLoader = createVocacoesRegiaoLoader({
    logger: () => {},
    fetchText: async (path) => {
      if (path === VOCACOES_MANIFEST_PATH) return manifestRaw
      if (path === regionPath) return `${JSON.stringify(tampered, null, 2)}\n`
      throw new Error(`caminho não publicado: ${path}`)
    },
  })
  await assert.rejects(tamperedLoader.loadRegion('serra'), (error) => {
    assert.equal(error.code, 'invalid_payload')
    return true
  })
})

test('origem sem contrato público aprovado: manifesto vazio com recusa registrada', () => {
  const semOrigem = resolveSource('caminho/que/nao/existe')
  assert.equal(semOrigem.available, false)
  assert.equal(semOrigem.refusal, null)

  const semAprovacao = resolveSource('scripts')
  assert.equal(semAprovacao.available, false)
  assert.match(semAprovacao.refusal, /ainda não foi aprovado/)

  const publication = buildPublication({ sourceRoot: 'scripts' })
  assert.deepEqual(publication.manifest.regions, [])
  assert.deepEqual(publication.files, [])
  assert.match(publication.refusal, /não transpõe\s+nada por conta própria/)
})

test('aprovação declarada sem transposição implementada é erro alto, não publicação', async () => {
  const { mkdtemp, writeFile: writeTempFile, rm } = await import('node:fs/promises')
  const { tmpdir } = await import('node:os')
  const { join } = await import('node:path')
  const dir = await mkdtemp(join(tmpdir(), 'vocacoes-regiao-aprovacao-'))
  try {
    await writeTempFile(join(dir, 'CONTRATO_PUBLICO_APROVADO.json'), '{}\n', 'utf8')
    assert.throws(() => resolveSource(dir), /transposição ainda não está\s+implementada/)
  } finally {
    await rm(dir, { recursive: true, force: true })
  }
})
