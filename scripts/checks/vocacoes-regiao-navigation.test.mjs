/*
 * Navegabilidade do Vocações da Região.
 *
 * O teste de slot prova que o pacote é válido. Este prova que ele é
 * **alcançável**: que a rota resolve, que o município leva à região certa, e
 * que cada uma das dez regiões do estado tem pacote publicado e legível pelo
 * mesmo leitor que roda no navegador.
 *
 * A verificação no navegador real cobre "a página desenha". Esta cobre "as dez
 * regiões chegam lá" — que é a parte que ninguém percorre à mão sem errar.
 */

import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'
import { mkdtempSync, rmSync, writeFileSync } from 'node:fs'
import { readFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import path from 'node:path'
import test from 'node:test'
import { pathToFileURL } from 'node:url'

import {
  VOCACOES_MANIFEST_PATH,
  VOCACOES_REGION_PATH,
  createVocacoesRegiaoLoader,
} from '../../src/features/vocacoes-regiao/vocacoesRegiaoLoader.js'

const temporaryOutput = mkdtempSync(path.join(tmpdir(), 'dashboard-pne-vocacoes-nav-'))
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

const compiled = (relativePath) => pathToFileURL(path.join(temporaryOutput, relativePath)).href
const { resolveActivePageFromHash } = await import(compiled('src/app/appRoutes.js'))
const { isPageNavigable, resolvePageProduct } = await import(compiled('src/config/analyticsProducts.js'))
const { isVocacoesPublished } = await import(compiled('src/domain/vocacoesRegiaoPublication.js'))
const { NAV_GROUPS } = await import(compiled('src/app/navigationRegistry.js'))

const readRepositoryFile = (relativePath) =>
  readFile(new URL(`../../${relativePath}`, import.meta.url), 'utf8')

const regionsConfig = JSON.parse(await readRepositoryFile('config/regions/rs.json'))
const manifest = JSON.parse(await readRepositoryFile('public/data/vocacoes-regiao/manifest.json'))
const publication = { publishedSlugs: new Set(manifest.regions.map((entry) => entry.slug)), ready: true }

/* O mesmo caminho que `resolveRegionForMunicipality` percorre no navegador —
 * reescrito aqui porque lá ele lê a configuração injetada em tempo de build. */
function regionOf(municipalityId) {
  return regionsConfig.regions.find((region) =>
    region.municipalityIbgeCodes.includes(municipalityId)) ?? null
}

test('a rota do Vocações da Região resolve pela canônica e pelos apelidos', () => {
  for (const hash of [
    '#vocacoes-da-regiao',
    '#vocacoesdaregiao',
    '#vocacoes',
    '#vocacoes-regiao',
    '#vocacoes-da-regiao?municipio=santa-cruz-do-sul',
    '#/Vocacoes-Da-Regiao',
  ]) {
    assert.equal(resolveActivePageFromHash(hash), 'vocacoes-regiao', hash)
  }
})

test('a página segue a publicação estadual e vive na divisão Análise Regional', () => {
  /*
   * O produto é `educacao`, e não `pne`: a divisão Análise Regional inteira
   * pertence ao produto de educação — o Panorama da Região já pertencia, e o
   * Vocações da Região o acompanha. Quem move isto move a publicação por UF
   * junto, e este teste é o lugar onde alguém vai notar.
   */
  assert.equal(resolvePageProduct('vocacoes-regiao'), 'educacao')
  assert.equal(
    resolvePageProduct('vocacoes-regiao'),
    resolvePageProduct('analise-regional'),
    'as duas páginas da divisão precisam pertencer ao mesmo produto',
  )
  assert.equal(isPageNavigable('vocacoes-regiao', 'complete', null), true)
  assert.equal(isPageNavigable('vocacoes-regiao', 'partial', ['educacao']), true)
  assert.equal(isPageNavigable('vocacoes-regiao', 'partial', ['pne']), false)
  assert.equal(isPageNavigable('vocacoes-regiao', 'identity-only', null), false)

  const group = NAV_GROUPS.find((candidate) => candidate.id === 'analise-regional')
  assert.ok(group, 'a divisão Análise Regional precisa existir')
  assert.ok(group.ownedPages.includes('vocacoes-regiao'))
  const item = group.items.find((candidate) => candidate.page === 'vocacoes-regiao')
  assert.ok(item, 'o item de menu do Vocações da Região precisa estar no grupo')
  assert.equal(item.condition, 'vocacoes', 'a visibilidade do item vem do manifesto, não de lista fixa')
})

test('as dez regiões do mapa estão publicadas e são navegáveis', () => {
  assert.equal(regionsConfig.regions.length, 10)
  assert.equal(manifest.regions.length, 10)
  for (const region of regionsConfig.regions) {
    assert.equal(
      isVocacoesPublished(publication, region.slug),
      true,
      `${region.slug} está no mapa regional e precisa estar publicada`,
    )
    const entry = manifest.regions.find((candidate) => candidate.slug === region.slug)
    assert.ok(entry, region.slug)
    assert.equal(entry.name, region.name, region.slug)
    assert.equal(entry.municipalityCount, region.municipalityCount, region.slug)
  }
})

test('todo município do estado chega a uma região publicada', () => {
  let municipalities = 0
  for (const region of regionsConfig.regions) {
    for (const municipalityId of region.municipalityIbgeCodes) {
      municipalities += 1
      const resolved = regionOf(municipalityId)
      assert.ok(resolved, municipalityId)
      assert.equal(resolved.slug, region.slug, municipalityId)
      assert.equal(isVocacoesPublished(publication, resolved.slug), true, municipalityId)
    }
  }
  assert.equal(municipalities, regionsConfig.municipalityCount)
  assert.equal(municipalities, 497)
})

test('município fora do mapa não alcança a página, e nem tenta', () => {
  assert.equal(regionOf('3550308'), null, 'município de outro estado')
  assert.equal(regionOf(''), null)
  assert.equal(isVocacoesPublished(publication, null), false)
})

/*
 * O leitor de produção, sobre os arquivos publicados, uma região por vez — que
 * é como o navegador os lê. Se qualquer uma das dez não passar, ela sumiria do
 * menu em produção, e é melhor descobrir aqui.
 */
test('o leitor de produção carrega e confere as dez regiões publicadas', async () => {
  const loader = createVocacoesRegiaoLoader({
    logger: () => {},
    fetchText: async (requested) => {
      if (requested === VOCACOES_MANIFEST_PATH) {
        return readRepositoryFile('public/data/vocacoes-regiao/manifest.json')
      }
      const slug = requested.replace('/data/vocacoes-regiao/regioes/', '').replace('.json', '')
      return readRepositoryFile(`public/data/vocacoes-regiao/regioes/${slug}.json`)
    },
  })

  const slugs = await loader.listPublishedRegionSlugs()
  assert.equal(slugs.length, 10)

  for (const slug of slugs) {
    const loaded = await loader.loadRegion(slug)
    assert.equal(loaded.document.region.slug, slug)
    assert.equal(loaded.document.page.title, `Vocações da Região — ${loaded.document.region.name}`)
    assert.ok(loaded.document.territoryPortrait.series.length > 0, slug)
    assert.ok(loaded.document.associations.items.length > 0, slug)
    assert.ok(loaded.document.temporalPairs.items.length > 0, slug)
    assert.ok(loaded.document.sources.items.length > 0, slug)
    assert.ok(loaded.document.limitations.items.length > 0, slug)
    /*
     * `verified` só quando há WebCrypto; em Node há, e por isso este teste
     * confere o resumo de verdade em vez de aceitar o declarado.
     */
    assert.equal(loaded.integrity, 'verified', slug)
    assert.equal(VOCACOES_REGION_PATH.replace('{regionSlug}', slug), `/data/vocacoes-regiao/regioes/${slug}.json`)
  }

  /* Nenhuma região saiu do conjunto durante a leitura das dez. */
  assert.deepEqual(await loader.listPublishedRegionSlugs(), slugs)
})
