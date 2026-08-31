const assert = require('node:assert/strict')
const { mkdir, readFile } = require('node:fs/promises')
const path = require('node:path')
const { chromium } = require('playwright')

const repoRoot = path.resolve(__dirname, '..', '..')
const port = Number(process.env.VOCACOES_PNE_OFFICIAL_PORT ?? 5199)
let baseUrl = process.env.BASE_URL ?? `http://127.0.0.1:${port}`
const screenshotEnabled = process.env.VOCACOES_PNE_SCREENSHOTS === '1'
const screenshotDir = path.join(repoRoot, '.tmp', 'vocacoes-pne', 'official', 'screenshots')

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

async function readValeDocument() {
  const candidates = [
    path.join(repoRoot, 'public', 'data', 'vocacoes-regiao', 'regioes', 'vale-do-sinos.json'),
    path.join(repoRoot, '.tmp', 'vocacoes-pne', 'rodada-00', 'baseline-290', 'vale-do-sinos.json'),
  ]
  for (const candidate of candidates) {
    try {
      return JSON.parse(await readFile(candidate, 'utf8'))
    } catch (error) {
      if (error?.code !== 'ENOENT') throw error
    }
  }
  throw new Error('Pacote regional do Vale do Sinos indisponível.')
}

function createHarnessPlugin(legacyDocument) {
  const publicEntry = '/__vocacoes-pne-official-e2e.js'
  const virtualEntry = '\0vocacoes-pne-official-e2e'
  return {
    name: 'vocacoes-pne-official-e2e-harness',
    resolveId(id) {
      return id === publicEntry ? virtualEntry : null
    },
    load(id) {
      if (id !== virtualEntry) return null
      return `
        import React from 'react'
        import { createRoot } from 'react-dom/client'
        import '/src/index.css'
        import '/src/App.css'
        import '/src/styles/institutional-refresh.css'
        import '/src/styles/typography-system.css'
        import { VocacoesPneOfficialReport } from '/src/features/vocacoes-regiao/VocacoesPneOfficialReport.tsx'
        import { loadVocacoesPneOfficialBundle } from '/src/features/vocacoes-regiao/useVocacoesPneOfficialBundle.ts'

        const legacyDocument = ${JSON.stringify(legacyDocument)}
        const root = createRoot(document.getElementById('root'))
        root.render(React.createElement('p', null, 'Preparando leitura integrada…'))
        loadVocacoesPneOfficialBundle().then((bundle) => {
          root.render(React.createElement(VocacoesPneOfficialReport, {
            bundle,
            legacyDocument,
            municipalityId: '4313375',
          }))
        })
      `
    },
    configureServer(server) {
      server.middlewares.use(async (request, response, next) => {
        const pathname = String(request.url ?? '').split('?')[0]
        if (pathname !== '/' && pathname !== '/index.html') {
          next()
          return
        }
        const html = await server.transformIndexHtml(
          request.url ?? '/',
          '<!doctype html><html lang="pt-BR"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head><body><div id="root"></div><script type="module" src="/__vocacoes-pne-official-e2e.js"></script></body></html>',
        )
        response.statusCode = 200
        response.setHeader('Content-Type', 'text/html; charset=utf-8')
        response.end(html)
      })
    },
  }
}

async function startLocalServer() {
  if (process.env.BASE_URL !== undefined) return null
  const [{ createServer }, { default: react }, legacyDocument] = await Promise.all([
    import('vite'),
    import('@vitejs/plugin-react'),
    readValeDocument(),
  ])
  const server = await createServer({
    appType: 'custom',
    cacheDir: path.join(repoRoot, '.tmp', 'vite-cache', 'vocacoes-pne-official-e2e'),
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
    plugins: [react(), createHarnessPlugin(legacyDocument)],
    publicDir: false,
    root: repoRoot,
    server: { hmr: false, host: '127.0.0.1', port, strictPort: false },
  })
  try {
    await server.listen()
  } catch (error) {
    await server.close()
    throw error
  }
  const resolvedUrl = server.resolvedUrls?.local?.[0]
  if (resolvedUrl) baseUrl = resolvedUrl.replace(/\/$/u, '')
  return server
}

async function openOfficialPage(context) {
  const page = await context.newPage()
  page.setDefaultTimeout(60_000)
  page.setDefaultNavigationTimeout(90_000)
  await page.goto(
    `${baseUrl}/#vocacoes-da-regiao?municipio=nova-santa-rita`,
    { waitUntil: 'domcontentloaded' },
  )
  await page.locator('.vocacoes-pne-official-page').waitFor({ state: 'visible' })
  await page.evaluate(() => document.fonts.ready)
  return page
}

async function assertNoHorizontalOverflow(page, label) {
  const metrics = await page.evaluate(() => {
    const root = document.querySelector('.vocacoes-pne-official-page')
    if (!(root instanceof HTMLElement)) throw new Error('superfície oficial ausente')
    return {
      documentClient: document.documentElement.clientWidth,
      documentScroll: document.documentElement.scrollWidth,
      rootClient: root.clientWidth,
      rootScroll: root.scrollWidth,
      cardOverflow: [...root.querySelectorAll('.vpm-card, .vpm-supporting-card')]
        .some((card) => card.scrollWidth > card.clientWidth + 1),
    }
  })
  assert.ok(metrics.documentScroll <= metrics.documentClient + 1, `${label}: documento com overflow`)
  assert.ok(metrics.rootScroll <= metrics.rootClient + 1, `${label}: relatório com overflow`)
  assert.equal(metrics.cardOverflow, false, `${label}: cartão com overflow`)
}

async function assertContentAndInteraction(page) {
  assert.equal(await page.locator('[data-review-card]').count(), 7)
  assert.equal(await page.locator('[data-direction="education-to-territory"]').count(), 4)
  assert.equal(await page.locator('[data-direction="territory-to-education"]').count(), 3)
  assert.equal(await page.locator('[data-supporting-relation]').count(), 3)
  assert.equal(await page.locator('[data-evidence-class]').count(), 10)
  assert.equal(await page.locator('[data-priority-id]').count(), 3)
  assert.equal(await page.locator('.vpo-section-nav a').count(), 4)
  assert.equal(await page.locator('.vpm-review-status--official').count(), 1)
  assert.equal(await page.getByText('Página pronta para validação de conteúdo', { exact: false }).count(), 0)

  const initialUrl = page.url()
  const firstDirection = page.locator('#education-to-territory')
  await page.getByRole('link', { name: 'Educação → território', exact: true }).click()
  assert.equal(page.url(), initialUrl)
  assert.equal(await firstDirection.evaluate((element) => document.activeElement === element), true)

  const firstDetails = page.locator('.vpm-details').first()
  assert.equal(await firstDetails.getAttribute('open'), null)
  await firstDetails.locator('summary').click()
  assert.equal(await firstDetails.getAttribute('open'), '')
  assert.match(await firstDetails.innerText(), /Indicadores para acompanhar/u)
  assert.match(await firstDetails.innerText(), /Fontes e períodos/u)
  assert.match(await firstDetails.innerText(), /Como ler esta relação/u)
}

async function assertPrint(page) {
  await page.emulateMedia({ media: 'print' })
  const metrics = await page.evaluate(() => ({
    officialNav: getComputedStyle(document.querySelector('.vpo-section-nav')).display,
    directionNav: getComputedStyle(document.querySelector('.vpm-direction-nav')).display,
    printButton: getComputedStyle(document.querySelector('.vpo-overview__scope button')).display,
    visiblePrintDetails: [...document.querySelectorAll('.vpm-print-details')]
      .filter((element) => getComputedStyle(element).display !== 'none').length,
  }))
  assert.equal(metrics.officialNav, 'none')
  assert.equal(metrics.directionNav, 'none')
  assert.equal(metrics.printButton, 'none')
  assert.equal(metrics.visiblePrintDetails, 10)
  await assertNoHorizontalOverflow(page, 'impressão')
  await page.emulateMedia({ media: 'screen' })
}

async function capture(page, name) {
  if (!screenshotEnabled) return
  await mkdir(screenshotDir, { recursive: true })
  await page.screenshot({ fullPage: true, path: path.join(screenshotDir, `${name}.png`) })
}

async function run() {
  const server = await startLocalServer()
  let browser
  try {
    browser = await chromium.launch({ headless: true })
    const errors = []
    for (const viewport of [
      { label: 'desktop', width: 1440, height: 900 },
      { label: 'tablet', width: 768, height: 1024 },
      { label: 'mobile', width: 390, height: 844 },
    ]) {
      const context = await browser.newContext({ viewport })
      const page = await openOfficialPage(context)
      page.on('console', (message) => {
        if (message.type() === 'error') errors.push(`${viewport.label}: ${message.text()}`)
      })
      page.on('pageerror', (error) => errors.push(`${viewport.label}: ${error.message}`))
      await assertNoHorizontalOverflow(page, viewport.label)
      if (viewport.label === 'desktop') {
        await assertContentAndInteraction(page)
        await assertPrint(page)
      }
      if (viewport.label === 'mobile') {
        const nav = await page.locator('.vpo-section-nav').evaluate((element) => ({
          clientWidth: element.clientWidth,
          scrollWidth: element.scrollWidth,
          columns: getComputedStyle(element).gridTemplateColumns,
        }))
        assert.ok(nav.scrollWidth <= nav.clientWidth + 1, 'navegação móvel não exige rolagem horizontal')
        assert.match(nav.columns, /\S+px \S+px/u)
      }
      await capture(page, `${viewport.label}-${viewport.width}x${viewport.height}`)
      await context.close()
    }
    assert.deepEqual(errors, [])
    console.log('OK: superfície oficial Vocações × PNE passou em desktop, tablet, mobile e impressão.')
  } finally {
    if (browser !== undefined) await browser.close()
    if (server !== null) await server.close()
  }
}

run().catch((error) => {
  console.error(error instanceof Error ? error.stack : String(error))
  process.exitCode = 1
})
