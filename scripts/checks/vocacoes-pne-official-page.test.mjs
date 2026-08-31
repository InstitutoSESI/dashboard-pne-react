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
    path.join(repoRoot, '.tmp', 'vocacoes-pne', 'rodada-00', 'baseline-290', `${slug}.json`),
  ]
  for (const candidate of candidates) {
    try {
      return JSON.parse(await readFile(candidate, 'utf8'))
    } catch (error) {
      if (error?.code !== 'ENOENT') throw error
    }
  }
  throw new Error(`Pacote regional indisponível para ${slug}.`)
}

const vite = await createServer({
  appType: 'custom',
  cacheDir: path.join(repoRoot, '.tmp', 'vite-cache', 'vocacoes-pne-official-unit'),
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
  server: { middlewareMode: true, hmr: { port: 24679 } },
})

after(async () => vite.close())

const reportModule = await vite.ssrLoadModule(
  '/src/features/vocacoes-regiao/VocacoesPneOfficialReport.tsx',
)
const promotionModule = await vite.ssrLoadModule(
  '/src/features/vocacoes-regiao/vocacoesPneOfficialPromotion.ts',
)
const loaderModule = await vite.ssrLoadModule(
  '/src/features/vocacoes-regiao/useVocacoesPneOfficialBundle.ts',
)
const bundle = await loaderModule.loadVocacoesPneOfficialBundle()
const valeDocument = await readLegacyDocument('vale-do-sinos')
const occurrences = (text, fragment) => text.split(fragment).length - 1

function renderOfficial(municipalityId = '4313375') {
  return renderToStaticMarkup(createElement(
    reportModule.VocacoesPneOfficialReport,
    { bundle, legacyDocument: valeDocument, municipalityId },
  ))
}

test('contrato de promoção fecha identidade, política de evidência e hashes dos bundles', async () => {
  const contract = promotionModule.VOCACOES_PNE_OFFICIAL_PROMOTION
  assert.equal(contract.authorizationBasis, 'explicit_user_request_for_official_route_promotion')
  assert.equal(contract.officialRoute, 'vocacoes-regiao')
  assert.equal(contract.regionSlug, 'vale-do-sinos')
  assert.equal(contract.municipalityCount, 10)
  assert.equal(contract.evidencePolicy.causalClaimsAllowed, false)
  assert.equal(contract.evidencePolicy.samePersonClaimsAllowed, false)
  assert.equal(contract.evidencePolicy.negativeFindingsVisibleAsBoundaries, true)
  assert.deepEqual(contract.evidencePolicy.supportingRelationIds, [
    'R6_SOCIOECONOMIC_TRAJECTORY',
    'R7_RURALITY_TRANSPORT',
    'R8_SPECIAL_AEE',
  ])
  assert.equal(
    promotionModule.matchesVocacoesPneOfficialPromotion(valeDocument, 'RS'),
    true,
  )

  const changedDocument = structuredClone(valeDocument)
  changedDocument.contentVersion = 'f'.repeat(64)
  assert.equal(
    promotionModule.matchesVocacoesPneOfficialPromotion(changedDocument, 'RS'),
    false,
  )
  assert.equal(
    promotionModule.matchesVocacoesPneOfficialPromotion(valeDocument, 'AL'),
    false,
  )
  assert.doesNotThrow(() => promotionModule.assertVocacoesPneOfficialBundle(bundle))

  const filesByContractKey = {
    job5iCoreSha256: 'vocacoesPneJob5iCore.json',
    job5iSeriesSha256: 'vocacoesPneJob5iSeries.json',
    job5kStoriesSha256: 'vocacoesPneJob5kStories.json',
  }
  for (const [contractKey, filename] of Object.entries(filesByContractKey)) {
    const bytes = await readFile(path.join(
      repoRoot,
      'src',
      'features',
      'vocacoes-pne-internal',
      'generated',
      filename,
    ))
    const sha256 = createHash('sha256').update(bytes).digest('hex')
    assert.equal(sha256, contract.sourceBundleHashes[contractKey], filename)
  }
})

test('Nova Santa Rita recebe a leitura oficial completa em duas direções e com conexões complementares', () => {
  const markup = renderOfficial()

  assert.match(markup, /data-publication="official"/u)
  assert.match(markup, /data-region="vale-do-sinos"/u)
  assert.match(markup, /Nova Santa Rita: educação e território/u)
  assert.equal(occurrences(markup, 'data-review-card="'), 7)
  assert.equal(occurrences(markup, 'data-direction="education-to-territory"'), 4)
  assert.equal(occurrences(markup, 'data-direction="territory-to-education"'), 3)
  assert.equal(occurrences(markup, 'data-supporting-relation="'), 3)
  assert.equal(occurrences(markup, 'data-evidence-class="'), 10)
  assert.equal(occurrences(markup, 'data-priority-id="'), 3)

  for (const relationId of [
    'conexao-contexto-socioeconomico-trajetoria',
    'conexao-ruralidade-oferta-transporte',
    'conexao-educacao-especial-aee',
  ]) {
    assert.match(markup, new RegExp(`data-supporting-relation="${relationId}"`, 'u'))
  }
  for (const text of [
    'O que o território ajuda a compreender sobre a educação?',
    'O que o futuro do território exige da educação?',
    'O que os dados sustentam',
    'Por que vale ler em conjunto',
    'Questão para o planejamento',
    'Diferenças entre municípios; evolução temporal limitada',
    'Reconfiguração observada da oferta rural',
    'Movimentos paralelos observados',
  ]) {
    assert.ok(markup.includes(text), text)
  }
  assert.doesNotMatch(markup, /Página pronta para validação de conteúdo/u)
  assert.doesNotMatch(markup, /(?:comprovou|provou|determinou|garante que)/iu)
})

test('visão regional preserva contexto e a identidade municipal falha de modo fechado', () => {
  const regionalMarkup = renderOfficial(null)
  assert.match(regionalMarkup, /Vale do Sinos: educação e território/u)
  assert.match(regionalMarkup, /10 municípios · RS/u)
  assert.throws(
    () => renderOfficial('4300000'),
    /município não pertence ao Vale do Sinos/u,
  )
})

test('os dez municípios canônicos do Vale renderizam a superfície oficial pela identidade IBGE textual', () => {
  assert.equal(bundle.core.municipalities.length, 10)
  for (const municipality of bundle.core.municipalities) {
    assert.match(municipality.ibgeCode, /^43\d{5}$/u)
    const markup = renderOfficial(municipality.ibgeCode)
    assert.ok(markup.includes(`${municipality.name}: educação e território`), municipality.name)
    assert.equal(occurrences(markup, 'data-review-card="'), 7, municipality.name)
    assert.ok(occurrences(markup, 'data-supporting-relation="') >= 2, municipality.name)
  }
})

test('rota oficial mantém seleção promovida e fallback legado explícitos no código', async () => {
  const source = await readFile(path.join(
    repoRoot,
    'src',
    'features',
    'vocacoes-regiao',
    'VocacoesRegiaoPage.tsx',
  ), 'utf8')
  assert.match(source, /matchesVocacoesPneOfficialPromotion/u)
  assert.match(source, /useVocacoesPneOfficialBundle/u)
  assert.match(source, /<VocacoesPneOfficialReport/u)
  assert.match(source, /<VocacoesResolvedReport/u)
})
