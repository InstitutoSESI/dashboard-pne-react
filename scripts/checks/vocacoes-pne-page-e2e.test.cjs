const assert = require('node:assert/strict')
const { mkdir, readFile } = require('node:fs/promises')
const path = require('node:path')
const { chromium } = require('playwright')

const repoRoot = path.resolve(__dirname, '..', '..')
const providedBaseUrl = process.env.BASE_URL
const port = Number(process.env.VOCACOES_PNE_PAGE_PORT ?? 5198)
const baseUrl = providedBaseUrl ?? `http://127.0.0.1:${port}`
const screenshotEnabled = process.env.VOCACOES_PNE_SCREENSHOTS === '1'
const screenshotDir = path.join(
  repoRoot,
  '.tmp',
  'vocacoes-pne',
  'rodada-07',
  'screenshots',
)

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

function createHarnessPlugin(documents) {
  const publicEntry = '/__vocacoes-pne-page-e2e.js'
  const virtualEntry = '\0vocacoes-pne-page-e2e'
  return {
    name: 'vocacoes-pne-page-e2e-harness',
    resolveId(id) {
      return id === publicEntry ? virtualEntry : null
    },
    load(id) {
      if (id !== virtualEntry) return null
      return `
        import React from 'react'
        import { createRoot } from 'react-dom/client'
        import { VocacoesResolvedReport } from '/src/features/vocacoes-regiao/VocacoesRegiaoPage.tsx'

        const documents = ${JSON.stringify(documents)}
        const root = createRoot(document.getElementById('root'))

        function renderRoute() {
          const query = location.hash.includes('?') ? location.hash.split('?')[1] : ''
          const municipality = new URLSearchParams(query).get('municipio')
          const legacyDocument = municipality === 'bento-goncalves'
            ? documents.serra
            : documents.vale
          root.render(React.createElement(VocacoesResolvedReport, { legacyDocument }))
        }

        addEventListener('hashchange', renderRoute)
        renderRoute()
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
          '<!doctype html><html lang="pt-BR"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head><body><div id="root"></div><script type="module" src="/__vocacoes-pne-page-e2e.js"></script></body></html>',
        )
        response.statusCode = 200
        response.setHeader('Content-Type', 'text/html; charset=utf-8')
        response.end(html)
      })
    },
  }
}

async function startLocalServer() {
  if (providedBaseUrl !== undefined) return null
  const [{ createServer }, { default: react }] = await Promise.all([
    import('vite'),
    import('@vitejs/plugin-react'),
  ])
  const [vale, serra] = await Promise.all([
    readLegacyDocument('vale-do-sinos'),
    readLegacyDocument('serra'),
  ])
  const server = await createServer({
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
    plugins: [react(), createHarnessPlugin({ vale, serra })],
    publicDir: false,
    root: repoRoot,
    server: {
      hmr: false,
      host: '127.0.0.1',
      port,
      strictPort: true,
    },
  })
  await server.listen()
  return server
}

async function assertNoHorizontalOverflow(page, label) {
  const result = await page.evaluate(() => {
    const root = document.querySelector('.vocacoes-pne-page')
    if (!(root instanceof HTMLElement)) throw new Error('.vocacoes-pne-page não encontrada')
    const nodes = [
      document.documentElement,
      document.body,
      root,
      ...root.querySelectorAll(
        '.vocacoes-pne-card, .vocacoes-pne-visual, .vocacoes-pne-disclosure, .vocacoes-pne-consultation',
      ),
    ]
    return nodes.map((node) => ({
      className: node.className || node.tagName,
      clientWidth: node.clientWidth,
      scrollWidth: node.scrollWidth,
      offenders: [...node.querySelectorAll('*')]
        .filter((child) => child.getBoundingClientRect().right > node.getBoundingClientRect().right + 1)
        .slice(0, 4)
        .map((child) => child.className || child.tagName),
    }))
  })
  for (const metric of result) {
    assert.ok(
      metric.scrollWidth <= metric.clientWidth + 1,
      `${label}: overflow em ${metric.className}: ${metric.scrollWidth}/${metric.clientWidth}; ${metric.offenders.join(', ')}`,
    )
  }
}

async function measureClosedPage(page, label) {
  const metrics = await page.evaluate(() => {
    const root = document.querySelector('.vocacoes-pne-page')
    const sections = document.querySelectorAll('.vocacoes-pne-section')
    if (!(root instanceof HTMLElement) || sections.length !== 2) {
      throw new Error('percurso narrativo incompleto')
    }
    const rootRect = root.getBoundingClientRect()
    const secondRect = sections[1].getBoundingClientRect()
    return {
      cards: root.querySelectorAll('.vocacoes-pne-card').length,
      disclosures: root.querySelectorAll('.vocacoes-pne-disclosure').length,
      pageHeight: rootRect.height,
      pathHeight: secondRect.bottom - rootRect.top,
      sections: sections.length,
    }
  })
  assert.equal(metrics.cards, 5, `${label}: quantidade de cartões`)
  assert.equal(metrics.disclosures, 20, `${label}: quantidade de detalhes`)
  assert.equal(metrics.sections, 2, `${label}: quantidade de seções`)
  return metrics
}

async function openPilotPage(context) {
  const page = await context.newPage()
  page.setDefaultTimeout(60_000)
  page.setDefaultNavigationTimeout(90_000)
  await page.goto(
    `${baseUrl}/#vocacoes-da-regiao?municipio=nova-santa-rita`,
    { timeout: 90_000, waitUntil: 'domcontentloaded' },
  )
  await page.locator('.vocacoes-pne-page').waitFor({ state: 'visible' })
  await page.evaluate(() => document.fonts.ready)
  return page
}

async function exerciseNavigationAndDetails(page) {
  const initialUrl = page.url()
  const initialHistoryLength = await page.evaluate(() => history.length)

  for (const button of await page.locator('.vocacoes-pne-highlight').all()) {
    const target = await button.getAttribute('data-card-target')
    await button.click()
    const focus = await page.evaluate((cardId) => {
      const heading = document.getElementById(`vocacoes-pne-card-${cardId}-title`)
      const rect = heading?.getBoundingClientRect()
      return {
        focused: document.activeElement === heading,
        top: rect?.top ?? -1,
      }
    }, target)
    assert.equal(focus.focused, true, `destaque ${target} deve mover foco`)
    assert.ok(focus.top >= 0, `destaque ${target} não pode cortar foco`)
    assert.equal(page.url(), initialUrl)
  }

  for (const button of await page.locator('.vocacoes-pne-nav button').all()) {
    const target = await button.getAttribute('data-section-target')
    await button.click()
    assert.equal(
      await page.evaluate((sectionId) => (
        document.activeElement?.id === `vocacoes-pne-section-${sectionId}-title`
      ), target),
      true,
      `seção ${target} deve receber foco`,
    )
    assert.equal(page.url(), initialUrl)
  }

  assert.equal(await page.evaluate(() => history.length), initialHistoryLength)
  assert.match(page.url(), /municipio=nova-santa-rita/)

  const firstCard = page.locator('.vocacoes-pne-card').first()
  for (const kind of ['evolution', 'municipalities', 'pne', 'sources']) {
    const disclosure = firstCard.locator(`[data-disclosure="${kind}"]`)
    await disclosure.locator('summary').click()
    assert.equal(await disclosure.getAttribute('open'), '')
    assert.equal(page.url(), initialUrl)
    if (kind === 'municipalities') {
      await disclosure.getByText('Nova Santa Rita', { exact: true }).waitFor({ state: 'visible' })
    }
    if (kind === 'sources') {
      await disclosure.getByText('Censo Escolar (INEP)', { exact: true }).waitFor({ state: 'visible' })
    }
    await disclosure.locator('summary').click()
    assert.equal(await disclosure.getAttribute('open'), null)
  }

  await page.evaluate(() => {
    history.pushState({ vocacoesProbe: true }, '', '#home?municipio=nova-santa-rita')
  })
  await page.goBack({ waitUntil: 'commit' })
  assert.match(page.url(), /#vocacoes-da-regiao\?municipio=nova-santa-rita$/)
  await page.locator('.vocacoes-pne-page').waitFor({ state: 'visible' })
}

async function assertPrint(page) {
  await page.emulateMedia({ media: 'print' })
  const metrics = await page.evaluate(() => {
    const nav = document.querySelector('.vocacoes-pne-nav')
    const detailBody = document.querySelector('.vocacoes-pne-disclosure__body')
    const root = document.querySelector('.vocacoes-pne-page')
    if (!(nav instanceof HTMLElement)
      || !(detailBody instanceof HTMLElement)
      || !(root instanceof HTMLElement)) {
      throw new Error('estrutura de impressão incompleta')
    }
    return {
      detailDisplay: getComputedStyle(detailBody).display,
      detailHeight: detailBody.getBoundingClientRect().height,
      navDisplay: getComputedStyle(nav).display,
      offenders: [...root.querySelectorAll('*')]
        .filter((child) => child.getBoundingClientRect().right > root.getBoundingClientRect().right + 1)
        .slice(0, 6)
        .map((child) => child.className || child.tagName),
      rootClientWidth: root.clientWidth,
      rootScrollWidth: root.scrollWidth,
    }
  })
  assert.equal(metrics.navDisplay, 'none')
  assert.notEqual(metrics.detailDisplay, 'none')
  assert.ok(metrics.detailHeight > 0, 'conteúdo essencial deve aparecer na impressão')
  assert.ok(
    metrics.rootScrollWidth <= metrics.rootClientWidth + 1,
    `impressão sem overflow horizontal: ${metrics.rootScrollWidth}/${metrics.rootClientWidth}; ${metrics.offenders.join(', ')}`,
  )
  await page.emulateMedia({ media: 'screen' })
}

async function assertLegacyFallback(page) {
  await page.goto(
    `${baseUrl}/#vocacoes-da-regiao?municipio=bento-goncalves`,
    { timeout: 90_000, waitUntil: 'domcontentloaded' },
  )
  await page.locator('.vocacoes-page .vocacoes-hero').waitFor({ state: 'visible' })
  assert.equal(await page.locator('.vocacoes-pne-page').count(), 0)
  await page.getByText('Vocações da Região — Serra', { exact: true }).waitFor({ state: 'visible' })
  assert.match(page.url(), /municipio=bento-goncalves/)
}

async function capture(page, name) {
  if (!screenshotEnabled) return
  await mkdir(screenshotDir, { recursive: true })
  await page.screenshot({
    fullPage: true,
    path: path.join(screenshotDir, `${name}.png`),
  })
}

async function runVocacoesPnePageE2e({ layoutOnly = false } = {}) {
  const server = await startLocalServer()
  let browser
  const report = {}
  try {
    browser = await chromium.launch({ headless: true })

    const desktopContext = await browser.newContext({ viewport: { width: 1440, height: 900 } })
    const desktopPage = await openPilotPage(desktopContext)
    if (!layoutOnly) await exerciseNavigationAndDetails(desktopPage)
    const desktop = await measureClosedPage(desktopPage, 'desktop')
    console.log(`Vocações PNE desktop: ${JSON.stringify(desktop)}`)
    assert.ok(desktop.pathHeight <= 6000, `percurso principal: ${desktop.pathHeight.toFixed(1)}px`)
    assert.ok(desktop.pageHeight <= 7000, `página total: ${desktop.pageHeight.toFixed(1)}px`)
    await assertNoHorizontalOverflow(desktopPage, 'desktop')
    await assertPrint(desktopPage)
    await capture(desktopPage, 'desktop-1440x900')
    await assertLegacyFallback(desktopPage)
    await desktopContext.close()
    report.desktop = desktop

    for (const viewport of [
      { label: 'tablet', width: 768, height: 1024 },
      { label: 'mobile', width: 390, height: 844 },
    ]) {
      const context = await browser.newContext({
        viewport: { width: viewport.width, height: viewport.height },
      })
      const page = await openPilotPage(context)
      await assertNoHorizontalOverflow(page, viewport.label)
      const metrics = await measureClosedPage(page, viewport.label)
      await capture(page, `${viewport.label}-${viewport.width}x${viewport.height}`)
      report[viewport.label] = metrics
      await context.close()
    }

    console.log(`Vocações PNE página: ${JSON.stringify(report)}`)
    return report
  } finally {
    if (browser !== undefined) await browser.close()
    if (server !== null) await server.close()
  }
}

module.exports = { runVocacoesPnePageE2e }

if (require.main === module) {
  runVocacoesPnePageE2e().catch((error) => {
    console.error(error instanceof Error ? error.stack : String(error))
    process.exitCode = 1
  })
}
