const assert = require('node:assert/strict')
const { mkdir } = require('node:fs/promises')
const path = require('node:path')
const { chromium } = require('playwright')

const repoRoot = path.resolve(__dirname, '..', '..')
const port = Number(process.env.CENARIOS_EDUCACAO_E2E_PORT ?? 5206)
let baseUrl = process.env.BASE_URL ?? `http://127.0.0.1:${port}`
const screenshotEnabled = process.env.CENARIOS_EDUCACAO_SCREENSHOTS === '1'
const screenshotDir = path.join(repoRoot, '.tmp', 'cenarios-educacao', 'screenshots')

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

function createHarnessPlugin() {
  const publicEntry = '/__cenarios-educacao-e2e.js'
  const virtualEntry = '\0cenarios-educacao-e2e'
  return {
    name: 'cenarios-educacao-e2e-harness',
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
        import {
          CenariosEducacaoDadosPage,
          CenariosEducacaoPage,
        } from '/src/features/cenarios-educacao/CenariosEducacaoPage.tsx'

        const Page = window.location.hash === '#dados'
          ? CenariosEducacaoDadosPage
          : CenariosEducacaoPage
        createRoot(document.getElementById('root')).render(
          React.createElement(Page, { municipalityId: '4313375' }),
        )
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
          '<!doctype html><html lang="pt-BR"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head><body><div id="root"></div><script type="module" src="/__cenarios-educacao-e2e.js"></script></body></html>',
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
  const [{ createServer }, { default: react }] = await Promise.all([
    import('vite'),
    import('@vitejs/plugin-react'),
  ])
  const server = await createServer({
    appType: 'custom',
    cacheDir: path.join(repoRoot, '.tmp', 'vite-cache', 'cenarios-educacao-e2e'),
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
    plugins: [react(), createHarnessPlugin()],
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

async function openPage(context, errors, label, hash = '') {
  const page = await context.newPage()
  page.setDefaultTimeout(60_000)
  page.setDefaultNavigationTimeout(90_000)
  page.on('console', (message) => {
    if (message.type() === 'error') errors.push(`${label}: ${message.text()}`)
  })
  page.on('pageerror', (error) => errors.push(`${label}: ${error.message}`))
  await page.goto(`${baseUrl}/${hash}`, { waitUntil: 'domcontentloaded' })
  await page.locator('.cenarios-educacao-page').waitFor({ state: 'visible' })
  await page.evaluate(() => document.fonts.ready)
  return page
}

async function assertNoHorizontalOverflow(page, label) {
  const metrics = await page.evaluate(() => {
    const root = document.querySelector('.cenarios-educacao-page')
    if (!(root instanceof HTMLElement)) throw new Error('página de cenários ausente')
    const cardSelectors = [
      '.ce-simple-decision-grid article',
      '.ce-simple-signal-grid article',
      '.ce-scenario-card',
      '.ce-driver-card',
      '.ce-domain-card',
      '.ce-action-groups article',
      '.ce-sentinel-card',
    ].join(',')
    return {
      documentClient: document.documentElement.clientWidth,
      documentScroll: document.documentElement.scrollWidth,
      rootClient: root.clientWidth,
      rootScroll: root.scrollWidth,
      cardOverflow: [...root.querySelectorAll(cardSelectors)]
        .some((card) => card.scrollWidth > card.clientWidth + 1),
    }
  })
  assert.ok(metrics.documentScroll <= metrics.documentClient + 1, `${label}: documento com overflow horizontal`)
  assert.ok(metrics.rootScroll <= metrics.rootClient + 1, `${label}: página com overflow horizontal`)
  assert.equal(metrics.cardOverflow, false, `${label}: cartão com overflow horizontal`)
}

async function assertSummary(page) {
  const root = page.locator('.cenarios-educacao-page')
  assert.equal(await root.getAttribute('data-page-kind'), 'summary')
  assert.equal(await root.getAttribute('data-publication-status'), 'exploratory_model_public_data_audited')
  assert.equal(await root.getAttribute('data-selected-municipality'), '4313375')
  assert.equal(await page.locator('[data-decision-priority]').count(), 3)
  assert.equal(await page.locator('.ce-scenario-card').count(), 4)
  assert.equal(await page.locator('[data-scenario-domain]').count(), 6)
  assert.equal(await page.locator('[data-public-signal]').count(), 3)
  assert.equal(await page.locator('details').count(), 0)
  assert.equal(await page.locator('.ce-page-nav').count(), 0)
  assert.equal(await page.locator('h1').count(), 1)
  assert.deepEqual(await page.locator('.ce-simple-main h2').allInnerTexts(), [
    'Três decisões para tomar com mais segurança',
    'Escolha um cenário para entender melhor',
    'Três informações públicas para revisar todo ano',
  ])

  const bodyText = await root.innerText()
  assert.match(bodyText, /Estes quatro cenários não são previsões/u)
  assert.match(bodyText, /Rede em compasso desigual/u)
  assert.match(bodyText, /Como este cenário pode se desenvolver/u)
  assert.match(bodyText, /O que muda em seis áreas da educação/u)
  assert.match(bodyText, /O que os dados públicos ainda não mostram/u)
  assert.match(bodyText, /dias letivos interrompidos/u)
  assert.doesNotMatch(bodyText, /Novo Hamburgo|contraste entre municípios|oficina humana/iu)
  assert.doesNotMatch(bodyText, /cenário mais provável|probabilidade do cenário/iu)
  assert.doesNotMatch(bodyText, /\b(?:PNE|MDE|EJA|EPT|AEE)\b/u)
  assert.doesNotMatch(bodyText, /foresight|campo morfológico|distância morfológica|constructo|lock-in|stress-test|gate técnico|proveniência|SHA-256|bytes|trade-?offs?|gatilhos?|sentinelas?|checkpoint|hash/iu)

  const cards = page.locator('.ce-scenario-card')
  const firstButton = cards.nth(0).locator('button')
  const secondButton = cards.nth(1).locator('button')
  assert.equal(await firstButton.getAttribute('aria-pressed'), 'true')
  await secondButton.focus()
  await page.keyboard.press('Enter')
  assert.equal(await firstButton.getAttribute('aria-pressed'), 'false')
  assert.equal(await secondButton.getAttribute('aria-pressed'), 'true')
  assert.match(await page.locator('.ce-scenario-detail__hero h3').innerText(), /Trabalho acelera, formação desencontra/u)
  assert.equal(await page.locator('[data-scenario-domain]').count(), 6)

  assert.equal(await page.locator('.ce-simple-links a').count(), 3)
  assert.equal(await page.locator('.ce-simple-links a').nth(0).getAttribute('href'), '#vocacoes-regiao')
  assert.equal(await page.locator('.ce-simple-links a').nth(1).getAttribute('href'), '#pne2026')
  assert.equal(await page.locator('.ce-simple-links a').nth(2).getAttribute('href'), '#cenarios-da-educacao-dados')
  await page.locator('.ce-simple-links a').first().focus()
  await page.keyboard.press('Tab')
  assert.equal(await page.locator('.ce-simple-links a').nth(1).evaluate((element) => element === document.activeElement), true)

  const pageHeight = await page.evaluate(() => document.documentElement.scrollHeight)
  assert.ok(pageHeight < 5000, `resumo ainda está longo: ${pageHeight}px`)
}

async function assertTechnical(page) {
  const root = page.locator('.cenarios-educacao-page')
  assert.equal(await root.getAttribute('data-page-kind'), 'technical')
  assert.match(await page.locator('h1').innerText(), /Dados e critérios da análise/u)
  assert.equal(await page.locator('.ce-technical-return').getAttribute('href'), '#cenarios-da-educacao')
  assert.equal(await page.locator('.ce-scenario-card').count(), 4)
  assert.equal(await page.locator('.ce-driver-card').count(), 4)
  assert.equal(await page.locator('[data-scenario-domain]').count(), 6)
  assert.equal(await page.locator('.ce-action-groups article').count(), 10)
  assert.equal(await page.locator('.ce-sentinel-card').count(), 12)

  const cards = page.locator('.ce-scenario-card')
  const secondButton = cards.nth(1).locator('button')
  await secondButton.focus()
  await page.keyboard.press('Enter')
  assert.equal(await secondButton.getAttribute('aria-pressed'), 'true')
  assert.match(await page.locator('.ce-scenario-detail__hero h3').innerText(), /Trabalho acelera, formação desencontra/u)

  const goalDetails = page.locator('.ce-goal-baseline')
  await goalDetails.locator('summary').focus()
  await page.keyboard.press('Enter')
  assert.equal(await goalDetails.getAttribute('open'), '')
  assert.equal(await goalDetails.locator('.ce-goal-grid article').count(), 7)

  const actionDetails = page.locator('.ce-action-group').first()
  await actionDetails.locator('summary').focus()
  await page.keyboard.press('Enter')
  assert.equal(await actionDetails.getAttribute('open'), '')
  assert.ok(await actionDetails.locator('article').count() > 0)
}

async function assertSummaryPrint(page) {
  await page.emulateMedia({ media: 'print' })
  const metrics = await page.evaluate(() => ({
    printButton: getComputedStyle(document.querySelector('.ce-print-button')).display,
    links: getComputedStyle(document.querySelector('.ce-simple-links')).display,
  }))
  assert.equal(metrics.printButton, 'none')
  assert.equal(metrics.links, 'none')
  await assertNoHorizontalOverflow(page, 'impressão do resumo')
  await page.emulateMedia({ media: 'screen' })
}

async function assertTechnicalPrint(page) {
  await page.emulateMedia({ media: 'print' })
  const metrics = await page.evaluate(() => ({
    nav: getComputedStyle(document.querySelector('.ce-page-nav')).display,
    printButton: getComputedStyle(document.querySelector('.ce-print-button')).display,
    returnLink: getComputedStyle(document.querySelector('.ce-technical-return')).display,
    goalBody: getComputedStyle(document.querySelector('.ce-goal-baseline > div')).display,
    methodBody: getComputedStyle(document.querySelector('.ce-method-details > :not(summary)')).display,
    actionBody: getComputedStyle(document.querySelector('.ce-action-group > div')).display,
    monitoringBody: getComputedStyle(document.querySelector('.ce-monitoring-group > div')).display,
  }))
  assert.equal(metrics.nav, 'none')
  assert.equal(metrics.printButton, 'none')
  assert.equal(metrics.returnLink, 'none')
  assert.equal(metrics.goalBody, 'block')
  assert.equal(metrics.methodBody, 'block')
  assert.equal(metrics.actionBody, 'block')
  assert.equal(metrics.monitoringBody, 'block')
  await assertNoHorizontalOverflow(page, 'impressão técnica')
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
      const page = await openPage(context, errors, viewport.label)
      await assertNoHorizontalOverflow(page, viewport.label)
      if (viewport.label === 'desktop') {
        await assertSummary(page)
        await assertSummaryPrint(page)
      }
      if (viewport.label === 'mobile') {
        const columns = await page.locator('.ce-scenario-grid').evaluate((element) => (
          getComputedStyle(element).gridTemplateColumns
        ))
        assert.doesNotMatch(columns, /\S+px \S+px/u, 'cartões móveis devem usar uma coluna')
      }
      await capture(page, `${viewport.label}-${viewport.width}x${viewport.height}`)
      await context.close()
    }

    const technicalContext = await browser.newContext({ viewport: { width: 1440, height: 900 } })
    const technicalPage = await openPage(technicalContext, errors, 'consulta técnica', '#dados')
    await assertNoHorizontalOverflow(technicalPage, 'consulta técnica')
    await assertTechnical(technicalPage)
    await assertTechnicalPrint(technicalPage)
    await capture(technicalPage, 'technical-desktop-1440x900')
    await technicalContext.close()

    assert.deepEqual(errors, [])
    console.log('OK: resumo e consulta técnica passaram em desktop, tablet, mobile, teclado e impressão.')
  } finally {
    if (browser !== undefined) await browser.close()
    if (server !== null) await server.close()
  }
}

run().catch((error) => {
  console.error(error instanceof Error ? error.stack : String(error))
  process.exitCode = 1
})
