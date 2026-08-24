import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'
import { mkdtempSync, rmSync, writeFileSync } from 'node:fs'
import { readFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import path from 'node:path'
import test from 'node:test'
import { pathToFileURL } from 'node:url'

/*
 * A politica de rota e de visibilidade vive em TypeScript. O teste compila
 * apenas os modulos puros envolvidos para um diretorio temporario e importa o
 * resultado, do mesmo jeito que a verificacao de rotas do aplicativo faz.
 */
const temporaryOutput = mkdtempSync(path.join(tmpdir(), 'dashboard-pne-foresight-'))
writeFileSync(path.join(temporaryOutput, 'package.json'), '{"type":"module"}\n')
execFileSync(
  process.execPath,
  [
    path.resolve('node_modules/typescript/bin/tsc'),
    '--project',
    'scripts/checks/tsconfig.foresight.json',
    '--outDir',
    temporaryOutput,
  ],
  { stdio: 'inherit' },
)
process.on('exit', () => rmSync(temporaryOutput, { force: true, recursive: true }))

const compiledModule = (relativePath) => pathToFileURL(path.join(temporaryOutput, relativePath)).href

const { isPageNavigable, resolvePageProduct } = await import(compiledModule('src/config/analyticsProducts.js'))
const { resolveActivePageFromHash } = await import(compiledModule('src/app/appRoutes.js'))
const { isForesightPublished } = await import(compiledModule('src/domain/foresightPublication.js'))

const NOVA_SANTA_RITA = '4313375'
const SAO_LEOPOLDO = '4318705'
const MULITERNO = '4312625'
const AGUDO = '4300109'

const manifest = JSON.parse(
  await readFile(new URL('../../public/data/foresight-educacao/manifest.json', import.meta.url), 'utf8'),
)
const publishedIds = new Set(manifest.municipalities.map((entry) => entry.ibgeCode))
const publication = { publishedIds, ready: true }

test('a rota dos cenários resolve pelos aliases publicados', () => {
  for (const hash of [
    '#cenarios-da-educacao',
    '#cenariosdaeducacao',
    '#cenarios-da-educacao?municipio=nova-santa-rita',
    '#cenarios-educacao',
    '#/Cenarios-Da-Educacao',
  ]) {
    assert.equal(resolveActivePageFromHash(hash), 'cenarios-educacao', hash)
  }
})

test('a página pertence ao produto do PNE e segue a publicação estadual', () => {
  assert.equal(resolvePageProduct('cenarios-educacao'), 'pne')
  assert.equal(isPageNavigable('cenarios-educacao', 'complete', null), true)
  assert.equal(isPageNavigable('cenarios-educacao', 'partial', ['pne']), true)
  assert.equal(isPageNavigable('cenarios-educacao', 'partial', ['educacao']), false)
  assert.equal(isPageNavigable('cenarios-educacao', 'identity-only', null), false)
})

test('a visibilidade vem do manifesto, município a município', () => {
  assert.equal(isForesightPublished(publication, NOVA_SANTA_RITA), true)
  assert.equal(isForesightPublished(publication, SAO_LEOPOLDO), true)
  assert.equal(isForesightPublished(publication, MULITERNO), false)
  assert.equal(isForesightPublished(publication, AGUDO), false)
  assert.equal(isForesightPublished(publication, null), false)
  assert.equal(isForesightPublished(publication, ''), false)
})

test('enquanto o manifesto não chega, nenhum município é considerado publicado', () => {
  const pending = { publishedIds: null, ready: false }
  assert.equal(isForesightPublished(pending, NOVA_SANTA_RITA), false)
  const empty = { publishedIds: new Set(), ready: true }
  assert.equal(isForesightPublished(empty, NOVA_SANTA_RITA), false)
})

/*
 * A identidade do item (rota canônica, rótulo, marca de condicionalidade) mudou
 * de casa na Fase 3 da reorganização: vive no registro único de navegação, e o
 * cabeçalho apenas aplica o gate. As asserções seguem as mesmas, cada uma no
 * arquivo que hoje é dono do literal.
 */
test('a entrada de navegação só existe quando o município selecionado está publicado', async () => {
  const registry = await readFile(new URL('../../src/app/navigationRegistry.ts', import.meta.url), 'utf8')
  assert.match(registry, /route: 'cenarios-da-educacao'/)
  assert.match(registry, /label: 'Cenários da educação'/)
  assert.match(registry, /itemFromPage\('cenarios-educacao', \{ condition: 'foresight' \}\)/)

  const { NAV_GROUPS } = await import(compiledModule('src/app/navigationRegistry.js'))
  const conditionalItem = NAV_GROUPS
    .flatMap((group) => group.items)
    .find((item) => item.key === 'cenarios-educacao')
  assert.deepEqual(
    {
      condition: conditionalItem?.condition,
      label: conditionalItem?.label,
      page: conditionalItem?.page,
      target: conditionalItem?.target,
    },
    {
      condition: 'foresight',
      label: 'Cenários da educação',
      page: 'cenarios-educacao',
      target: 'cenarios-da-educacao',
    },
  )

  const header = await readFile(new URL('../../src/components/Header.jsx', import.meta.url), 'utf8')
  assert.match(header, /const foresightVisible = isForesightPublished\(foresightPublication, selectedMunicipalityId\)/)
  assert.match(header, /withForesightItem\(block, foresightVisible\)/)
  assert.equal(/disabled/.test(header.split('function withForesightItem')[1]?.slice(0, 400) ?? ''), false)
})

test('acesso direto com município não publicado sai da rota em vez de abrir página vazia', async () => {
  const router = await readFile(new URL('../../src/app/AppPageRouter.tsx', import.meta.url), 'utf8')
  assert.match(router, /const foresightBlocked = isForesightRoute\s*\n\s*&& selectionReady\s*\n\s*&& foresightPublication\.ready\s*\n\s*&& !foresightAvailable/)
  assert.match(router, /replaceHashContext\('diagnostico', \{\s*\n\s*municipio: effectiveMunicipality\?\.slug \?\? null,\s*\n\s*\}\)/)
  assert.match(router, /if \(!foresightPublication\.ready \|\| foresightBlocked\) \{/)
  assert.match(router, /key=\{effectiveMunicipalityId\}/)
})

test('a migalha da página nomeia o planejamento municipal', async () => {
  const registry = await readFile(new URL('../../src/app/navigationRegistry.ts', import.meta.url), 'utf8')
  assert.match(registry, /crumb: 'Metas do PNE \/ Planejamento municipal \/ Cenários da educação'/)

  const { buildPageCrumbs } = await import(compiledModule('src/app/navigationRegistry.js'))
  assert.equal(
    buildPageCrumbs()['cenarios-educacao'],
    'Metas do PNE / Planejamento municipal / Cenários da educação',
  )
})
