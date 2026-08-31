import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { readFile } from 'node:fs/promises'
import path from 'node:path'
import test, { after } from 'node:test'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import react from '@vitejs/plugin-react'
import { createServer } from 'vite'

const repoRoot = path.resolve(import.meta.dirname, '..', '..')

const activeStateConfig = {
  schemaVersion: 'state-config-v1',
  stateCode: 'RS',
  stateName: 'Rio Grande do Sul',
  stateNameForms: {
    nominative: 'Rio Grande do Sul',
    withDe: 'do Rio Grande do Sul',
    withCom: 'com o Rio Grande do Sul',
  },
  municipalityIbgePrefix: '43',
  expectedMunicipalityCount: 497,
  locale: 'pt-BR',
}

async function readLegacyDocument(slug) {
  const candidates = [
    path.join(repoRoot, 'public', 'data', 'vocacoes-regiao', 'regioes', `${slug}.json`),
    path.join(
      repoRoot,
      '.tmp',
      'vocacoes-pne',
      'rodada-00',
      'baseline-290',
      `${slug}.json`,
    ),
  ]
  for (const candidate of candidates) {
    try {
      return JSON.parse(await readFile(candidate, 'utf8'))
    } catch (error) {
      if (error?.code !== 'ENOENT') throw error
    }
  }
  throw new Error(`Fixture 2.9.0 indisponível para ${slug}.`)
}

const vite = await createServer({
  appType: 'custom',
  configFile: false,
  define: {
    __ACTIVE_PUBLICATION_CONFIG__: JSON.stringify({
      schemaVersion: 'state-publication-v3',
      stateCode: 'RS',
      analyticsStatus: 'complete',
      analyticsMessage: null,
      enabledProducts: null,
    }),
    __ACTIVE_REGIONS_CONFIG__: 'null',
    __ACTIVE_STATE_CONFIG__: JSON.stringify(activeStateConfig),
  },
  plugins: [react()],
  publicDir: false,
  root: repoRoot,
  server: { middlewareMode: true },
})

after(async () => vite.close())

const pageModule = await vite.ssrLoadModule(
  '/src/features/vocacoes-regiao/VocacoesRegiaoPage.tsx',
)
const narrativeModule = await vite.ssrLoadModule(
  '/src/features/vocacoes-regiao/VocacoesPneNarrativeReport.tsx',
)
const contractModule = await vite.ssrLoadModule(
  '/src/features/vocacoes-regiao/vocacoesPneNarrativeContract.js',
)
const registryModule = await vite.ssrLoadModule(
  '/src/features/vocacoes-regiao/vocacoesPneNarrativeRegistry.js',
)
const narrativePath = path.join(
  repoRoot,
  'src',
  'features',
  'vocacoes-regiao',
  'generated',
  'vocacoesPneValeDoSinos.json',
)
const narrativeRawText = await readFile(narrativePath, 'utf8')
const narrativeRaw = JSON.parse(narrativeRawText)
const narrative = contractModule.parseVocacoesPneNarrative(narrativeRaw)
const valeDocument = await readLegacyDocument('vale-do-sinos')
const serraDocument = await readLegacyDocument('serra')

const renderNarrative = () => renderToStaticMarkup(createElement(
  narrativeModule.VocacoesPneNarrativeReport,
  { legacyDocument: valeDocument, narrative },
))
const occurrences = (text, fragment) => text.split(fragment).length - 1

function cloneRegistry() {
  return structuredClone(registryModule.VOCACOES_PNE_NARRATIVE_REGISTRY_MANIFEST)
}

function cloneImportedDocuments() {
  return structuredClone(registryModule.VOCACOES_PNE_NARRATIVE_IMPORTED_DOCUMENTS)
}

function importedDocumentWithMutation(mutate) {
  const document = structuredClone(narrativeRaw)
  mutate(document)
  const raw = JSON.stringify(document)
  const importedDocuments = cloneImportedDocuments()
  importedDocuments[0].raw = raw
  const registry = cloneRegistry()
  registry.entries[0].narrativeByteSize = new TextEncoder().encode(raw).length
  registry.entries[0].narrativeSha256 = registryModule.sha256Utf8(raw)
  return { importedDocuments, registry }
}

function expandCards(document, sectionIndex, count) {
  const cards = document.sections[sectionIndex].cards
  const originals = structuredClone(cards)
  while (cards.length < count) {
    const card = structuredClone(originals[cards.length % originals.length])
    card.id = `${card.id}-extra-${cards.length}`
    cards.push(card)
  }
}

test('piloto narrativo preserva bytes, SHA-256 e registro inicial fechado', () => {
  const expectedFields = [
    'legacyContentVersion',
    'legacySourceVersion',
    'municipalityCount',
    'name',
    'narrativeByteSize',
    'narrativeContractVersion',
    'narrativeSchemaVersion',
    'narrativeSha256',
    'slug',
    'stateCode',
    'status',
  ]
  const registry = registryModule.VOCACOES_PNE_NARRATIVE_REGISTRY_MANIFEST

  assert.equal(Buffer.byteLength(narrativeRawText, 'utf8'), 25_963)
  assert.equal(
    createHash('sha256').update(narrativeRawText, 'utf8').digest('hex'),
    '8f9515bf35283bb2622f823830dc1c5ff5cad4aa711158ce120edc07eab64f2c',
  )
  assert.equal(registry.schemaVersion, 'vocacoes-pne-narrative-registry-v1')
  assert.equal(registry.entries.length, 1)
  assert.deepEqual(Object.keys(registry.entries[0]).sort(), expectedFields)
  assert.deepEqual(
    registryModule.resolveRegisteredVocacoesPneNarrative(valeDocument, 'RS'),
    narrativeRaw,
  )
})

test('parser regional aceita slug e contagem positivos no RS e limites 3–5 + 2–5', () => {
  const regional = structuredClone(narrativeRaw)
  regional.region.slug = 'regiao-de-teste'
  regional.region.name = 'Região de Teste'
  regional.region.municipalityCount = 1
  for (const section of regional.sections) {
    for (const card of section.cards) card.municipal_distribution.items.splice(1)
  }
  expandCards(regional, 0, 5)
  expandCards(regional, 1, 5)
  assert.equal(contractModule.parseVocacoesPneNarrative(regional), regional)

  const invalidCardCounts = [
    (document) => { document.sections[0].cards.splice(2) },
    (document) => { expandCards(document, 0, 6) },
    (document) => { document.sections[1].cards.splice(1) },
    (document) => { expandCards(document, 1, 6) },
  ]
  for (const mutate of invalidCardCounts) {
    const candidate = structuredClone(narrativeRaw)
    mutate(candidate)
    assert.throws(() => contractModule.parseVocacoesPneNarrative(candidate), TypeError)
  }

  const zeroMunicipalities = structuredClone(narrativeRaw)
  zeroMunicipalities.region.municipalityCount = 0
  assert.throws(() => contractModule.parseVocacoesPneNarrative(zeroMunicipalities), TypeError)
  const anotherState = structuredClone(narrativeRaw)
  anotherState.region.stateCode = 'AL'
  assert.throws(() => contractModule.parseVocacoesPneNarrative(anotherState), TypeError)
})

test('registro recusa adulteração independente de todos os campos declarados', () => {
  const attacks = {
    slug: (entry) => { entry.slug = 'serra' },
    name: (entry) => { entry.name = 'Outro Vale' },
    stateCode: (entry) => { entry.stateCode = 'AL' },
    municipalityCount: (entry) => { entry.municipalityCount += 1 },
    narrativeSchemaVersion: (entry) => { entry.narrativeSchemaVersion = 'outro-schema' },
    narrativeContractVersion: (entry) => { entry.narrativeContractVersion = '9.9.9' },
    legacySourceVersion: (entry) => { entry.legacySourceVersion = 'outra-versao' },
    legacyContentVersion: (entry) => { entry.legacyContentVersion = 'f'.repeat(64) },
    narrativeByteSize: (entry) => { entry.narrativeByteSize += 1 },
    narrativeSha256: (entry) => { entry.narrativeSha256 = 'f'.repeat(64) },
    status: (entry) => { entry.status = 'draft' },
  }
  for (const [field, mutate] of Object.entries(attacks)) {
    const registry = cloneRegistry()
    mutate(registry.entries[0])
    const compiled = registryModule.createVocacoesPneNarrativeRegistry(registry)
    assert.equal(
      registryModule.resolveRegisteredVocacoesPneNarrative(valeDocument, 'RS', compiled),
      null,
      field,
    )
  }
})

test('registro recusa path, duplicata, documento não registrado e entrada sem import', () => {
  const wrongPath = cloneImportedDocuments()
  wrongPath[0].path = './generated/serra.json'
  assert.equal(
    registryModule.createVocacoesPneNarrativeRegistry(cloneRegistry(), wrongPath),
    null,
  )

  const duplicate = cloneRegistry()
  duplicate.entries.push(structuredClone(duplicate.entries[0]))
  assert.equal(registryModule.createVocacoesPneNarrativeRegistry(duplicate), null)

  const unregisteredDocument = cloneRegistry()
  unregisteredDocument.entries = []
  assert.throws(
    () => registryModule.parseVocacoesPneNarrativeRegistry(unregisteredDocument),
    /documento não registrado/u,
  )

  assert.throws(
    () => registryModule.parseVocacoesPneNarrativeRegistry(cloneRegistry(), []),
    /entrada fora dos documentos importados/u,
  )
})

test('registro recusa documento importado adulterado mesmo com hash e tamanho atualizados', () => {
  const attacks = [
    (document) => { document.schemaVersion = 'outro-schema' },
    (document) => { document.contractVersion = '9.9.9' },
    (document) => { document.region.slug = 'serra' },
    (document) => { document.region.name = 'Outro Vale' },
    (document) => { document.region.stateCode = 'AL' },
    (document) => { document.region.municipalityCount += 1 },
  ]
  for (const mutate of attacks) {
    const { importedDocuments, registry } = importedDocumentWithMutation(mutate)
    assert.equal(
      registryModule.createVocacoesPneNarrativeRegistry(registry, importedDocuments),
      null,
    )
  }
})

test('rollback mantém validação integral e desativa somente o resolvedor narrativo', () => {
  const original = cloneRegistry()
  const rolledBack = cloneRegistry()
  rolledBack.entries[0].status = 'rolled_back'
  const compiled = registryModule.createVocacoesPneNarrativeRegistry(rolledBack)

  assert.notEqual(compiled, null)
  assert.equal(compiled.resolve('vale-do-sinos').entry.status, 'rolled_back')
  assert.equal(
    registryModule.resolveRegisteredVocacoesPneNarrative(
      valeDocument,
      'RS',
      compiled,
    ),
    null,
  )
  assert.equal(original.entries[0].status, 'published')

  const adulteratedDocuments = cloneImportedDocuments()
  adulteratedDocuments[0].raw += '\n'
  assert.equal(
    registryModule.createVocacoesPneNarrativeRegistry(
      rolledBack,
      adulteratedDocuments,
    ),
    null,
  )
})

test('runtime regional usa somente o documento narrativo embutido e o pacote legado carregado', async () => {
  const runtimeSources = await Promise.all([
    readFile(path.join(
      repoRoot,
      'src',
      'features',
      'vocacoes-regiao',
      'VocacoesRegiaoPage.tsx',
    ), 'utf8'),
    readFile(path.join(
      repoRoot,
      'src',
      'features',
      'vocacoes-regiao',
      'vocacoesPneNarrativeRegistry.js',
    ), 'utf8'),
  ])
  for (const source of runtimeSources) {
    assert.doesNotMatch(source, /public[\\/]data|\/data\/vocacoes|\bfetch\s*\(|\breadFile\s*\(/u)
  }
})

test('SSR preserva o percurso narrativo fechado, seus seletores e a ordem 3 + 2', () => {
  const markup = renderNarrative()

  assert.equal(occurrences(markup, 'class="vocacoes-pne-highlight"'), 3)
  assert.equal(occurrences(markup, 'class="vocacoes-pne-section"'), 2)
  assert.equal(occurrences(markup, 'data-card-id="'), 5)
  assert.equal(occurrences(markup, 'class="vocacoes-pne-disclosure"'), 20)
  assert.equal(occurrences(markup, 'data-consultation-series-id="'), 71)
  assert.equal(occurrences(markup, '<main'), 0)

  const expectedOrder = narrative.sections.flatMap((section) => (
    section.cards.map((card) => card.id)
  ))
  let cursor = -1
  for (const cardId of expectedOrder) {
    const position = markup.indexOf(`data-card-id="${cardId}"`)
    assert.ok(position > cursor, `${cardId} deve respeitar a ordem aprovada`)
    cursor = position
  }

  for (const section of narrative.sections) {
    assert.match(markup, new RegExp(`data-section-target="${section.id}"`))
    assert.match(markup, new RegExp(`>${section.title}</button>`))
  }
  for (const highlight of narrative.highlights) {
    assert.match(markup, new RegExp(`data-card-target="${highlight.cardId}"`))
    assert.match(markup, new RegExp(`data-card-id="${highlight.cardId}"`))
    assert.ok(markup.includes(highlight.label))
  }

  assert.ok(markup.includes('Mudança já em curso'))
  assert.ok(markup.includes('Tendência para os próximos anos'))
  assert.ok(markup.includes('10 municípios · RS'))
  assert.ok(markup.includes(narrative.page.referenceLabel))
})

test('SSR mantém quatro detalhes, visuais acessíveis, municípios, fontes e consulta 2.9.0', () => {
  const markup = renderNarrative()

  for (const [kind, label] of Object.entries(narrative.page.details)) {
    assert.equal(occurrences(markup, `data-disclosure="${kind}"`), 5)
    assert.equal(occurrences(markup, `>${label}</summary>`), 5)
  }
  for (const municipality of narrative.sections[0].cards[0].municipal_distribution.items) {
    assert.ok(markup.includes(municipality.name), municipality.name)
  }
  for (const source of valeDocument.sources.items) {
    assert.ok(markup.includes(source.label), source.label)
  }
  for (const series of valeDocument.territoryPortrait.series) {
    assert.ok(markup.includes(`data-consultation-series-id="${series.seriesId}"`))
  }

  const svgCount = occurrences(markup, '<svg')
  assert.ok(svgCount >= 5)
  assert.equal(occurrences(markup, 'role="img"'), svgCount)
  assert.equal(occurrences(markup, '<title>'), svgCount)
})

test('consulta formata período mensal como no explorador legado', () => {
  const markup = renderNarrative()
  const seriesId = 'familias-inscritas-com-cadastro-atualizado'
  const seriesStart = markup.indexOf(`data-consultation-series-id="${seriesId}"`)
  assert.ok(seriesStart >= 0, 'série mensal real deve integrar a consulta')
  const seriesEnd = markup.indexOf('</article>', seriesStart)
  assert.ok(seriesEnd > seriesStart, 'trecho da série mensal deve fechar no mesmo artigo')
  const seriesMarkup = markup.slice(seriesStart, seriesEnd)

  assert.match(seriesMarkup, />abr\. 2015</)
  assert.doesNotMatch(seriesMarkup, />201504</)
})

test('markup narrativo não reintroduz linguagem ou metadados retirados do percurso', () => {
  const markup = renderNarrative()
  const blocked = [
    /Pergunta\s+[12]/iu,
    /\bE[1-5]\b/u,
    /triagem/iu,
    /correla(?:ção|cao)/iu,
    /\bforça\b/iu,
    /p-?valor/iu,
    /reasonCode/u,
    /(?:primeira|segunda)-saida-pesquisa/iu,
    /\binternal\b/iu,
    /\bgates?\b/iu,
    /\bchecks?\b/iu,
  ]
  for (const pattern of blocked) assert.doesNotMatch(markup, pattern)
})

test('resolver usa piloto apenas na identidade exata e mantém os fallbacks legados', () => {
  assert.deepEqual(pageModule.resolveVocacoesPneNarrative(valeDocument), narrativeRaw)
  assert.equal(
    pageModule.resolveVocacoesPneNarrativePilot,
    pageModule.resolveVocacoesPneNarrative,
  )

  const attacks = [
    (document) => { document.contentVersion = 'f'.repeat(64) },
    (document) => { document.sourceVersion = 'outra-versao' },
    (document) => { document.schemaVersion = 'vocacoes-regiao-2.8.0' },
    (document) => { document.region.slug = 'serra' },
    (document) => { document.region.name = 'Outro Vale' },
    (document) => { document.region.uf = 'AL' },
    (document) => { document.region.municipalityCount += 1 },
    (document) => { document.territoryPortrait.series.pop() },
  ]
  for (const mutate of attacks) {
    const candidate = structuredClone(valeDocument)
    mutate(candidate)
    assert.equal(pageModule.resolveVocacoesPneNarrative(candidate), null)
    const markup = renderToStaticMarkup(createElement(
      pageModule.VocacoesResolvedReport,
      { legacyDocument: candidate },
    ))
    assert.match(markup, /class="page-stack vocacoes-page"/)
    assert.doesNotMatch(markup, /vocacoes-pne-page/)
  }

  assert.equal(pageModule.resolveVocacoesPneNarrative(serraDocument), null)
  const serraMarkup = renderToStaticMarkup(createElement(
    pageModule.VocacoesResolvedReport,
    { legacyDocument: serraDocument },
  ))
  assert.match(serraMarkup, /class="page-stack vocacoes-page"/)
  assert.ok(serraMarkup.includes(serraDocument.page.title))
})

test('wrapper integrado seleciona a experiência nova sem alterar o relatório legado exportado', () => {
  const pilotMarkup = renderToStaticMarkup(createElement(
    pageModule.VocacoesResolvedReport,
    { legacyDocument: valeDocument },
  ))
  assert.match(pilotMarkup, /class="page-stack vocacoes-pne-page"/)
  assert.doesNotMatch(pilotMarkup, /class="page-stack vocacoes-page"/)

  const legacyMarkup = renderToStaticMarkup(createElement(
    pageModule.VocacoesReport,
    { document: serraDocument },
  ))
  assert.match(legacyMarkup, /class="page-stack vocacoes-page"/)
  assert.ok(legacyMarkup.includes(serraDocument.page.title))
})
