const assert = require('node:assert/strict')
const { mkdir, readFile } = require('node:fs/promises')
const path = require('node:path')
const { chromium } = require('playwright')

const repoRoot = path.resolve(__dirname, '..', '..')
const port = Number(process.env.VOCACOES_PNE_AA5_PORT ?? 5205)
let baseUrl = process.env.BASE_URL ?? `http://127.0.0.1:${port}`
const screenshotEnabled = process.env.VOCACOES_PNE_SCREENSHOTS === '1'
const screenshotDir = path.join(repoRoot, '.tmp', 'vocacoes-pne', 'aa5', 'screenshots')

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

async function readLegacyDocument() {
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
  const publicEntry = '/__vocacoes-pne-aa5-e2e.js'
  const virtualEntry = '\0vocacoes-pne-aa5-e2e'
  return {
    name: 'vocacoes-pne-aa5-e2e-harness',
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
        import { VocacoesPneAdvancedReport } from '/src/features/vocacoes-regiao/VocacoesPneAdvancedReport.tsx'
        import { VocacoesPneOfficialReport } from '/src/features/vocacoes-regiao/VocacoesPneOfficialReport.tsx'
        import { createVocacoesPneAdvancedLoader, loadVocacoesPneAdvancedBundle } from '/src/features/vocacoes-regiao/useVocacoesPneAdvancedBundle.ts'
        import { loadVocacoesPneOfficialBundle } from '/src/features/vocacoes-regiao/useVocacoesPneOfficialBundle.ts'
        import { resolveVocacoesPneSurface } from '/src/features/vocacoes-regiao/vocacoesPneSurfaceResolution.ts'

        const legacyDocument = ${JSON.stringify(legacyDocument)}
        const root = createRoot(document.getElementById('root'))
        root.render(React.createElement('p', null, 'Preparando leitura integrada…'))
        const parameters = new URLSearchParams(location.search)
        const forceFallback = parameters.get('fallback') === '1'
        const unsupportedScope = parameters.get('unsupported') === '1'
        const municipalityId = parameters.get('region') === '1' ? null : '4313375'

        if (unsupportedScope) {
          loadVocacoesPneOfficialBundle().then((official) => {
            const unsupportedMunicipality = official.core.municipalities.find((item) => item.ibgeCode !== '4313375')
            if (!unsupportedMunicipality) throw new Error('município de fallback ausente')
            root.render(React.createElement(VocacoesPneOfficialReport, {
              advancedScopeNotice: true,
              bundle: official,
              legacyDocument,
              municipalityId: unsupportedMunicipality.ibgeCode,
            }))
          })
        } else if (!forceFallback) {
          loadVocacoesPneAdvancedBundle().then((bundle) => {
            root.render(React.createElement(VocacoesPneAdvancedReport, { bundle, municipalityId }))
          })
        } else {
          const rejectedLoader = createVocacoesPneAdvancedLoader(async () => {
            throw new Error('falha avançada injetada')
          })
          Promise.allSettled([rejectedLoader(), loadVocacoesPneOfficialBundle()]).then(([advanced, official]) => {
            const surface = resolveVocacoesPneSurface({
              eligible: true,
              advancedRequested: true,
              advancedStatus: advanced.status === 'rejected' ? 'error' : 'ready',
              advancedScopeSupported: advanced.status === 'fulfilled',
              officialStatus: official.status === 'fulfilled' ? 'ready' : 'error',
              officialScopeSupported: official.status === 'fulfilled',
            })
            document.documentElement.dataset.resolvedSurface = surface
            if (surface !== 'official_previous' || official.status !== 'fulfilled') {
              throw new Error('fallback oficial anterior não foi selecionado')
            }
            root.render(React.createElement(VocacoesPneOfficialReport, {
              bundle: official.value,
              legacyDocument,
              municipalityId: '4313375',
            }))
          })
        }
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
          '<!doctype html><html lang="pt-BR"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head><body><div id="root"></div><script type="module" src="/__vocacoes-pne-aa5-e2e.js"></script></body></html>',
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
    readLegacyDocument(),
  ])
  const server = await createServer({
    appType: 'custom',
    cacheDir: path.join(repoRoot, '.tmp', 'vite-cache', 'vocacoes-pne-aa5-e2e'),
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

async function openAdvancedPage(context, query = '') {
  const page = await context.newPage()
  page.setDefaultTimeout(60_000)
  page.setDefaultNavigationTimeout(90_000)
  await page.goto(`${baseUrl}/${query}`, { waitUntil: 'domcontentloaded' })
  await page.locator('.vocacoes-pne-advanced-page').waitFor({ state: 'visible' })
  await page.evaluate(() => document.fonts.ready)
  return page
}

async function assertNoHorizontalOverflow(page, label, rootSelector = '.vocacoes-pne-advanced-page') {
  const metrics = await page.evaluate((selector) => {
    const root = document.querySelector(selector)
    if (!(root instanceof HTMLElement)) throw new Error(`superfície ausente: ${selector}`)
    return {
      documentClient: document.documentElement.clientWidth,
      documentScroll: document.documentElement.scrollWidth,
      rootClient: root.clientWidth,
      rootScroll: root.scrollWidth,
      cardOverflow: [...root.querySelectorAll('.vpr-reading, .vpr-agenda, .vpr-relation')]
        .some((card) => card.scrollWidth > card.clientWidth + 1),
      offenders: [...root.querySelectorAll('*')]
        .filter((element) => element instanceof HTMLElement && element.scrollWidth > element.clientWidth + 1)
        .slice(0, 8)
        .map((element) => ({
          tag: element.tagName,
          className: element.className,
          clientWidth: element.clientWidth,
          scrollWidth: element.scrollWidth,
          text: element.textContent?.trim().slice(0, 80),
        })),
    }
  }, rootSelector)
  const diagnostic = JSON.stringify(metrics.offenders)
  assert.ok(metrics.documentScroll <= metrics.documentClient + 1, `${label}: documento com overflow ${diagnostic}`)
  assert.ok(metrics.rootScroll <= metrics.rootClient + 1, `${label}: relatório com overflow ${diagnostic}`)
  assert.equal(metrics.cardOverflow, false, `${label}: cartão com overflow`)
}

async function assertContentAndInteraction(page) {
  assert.equal(await page.locator('[data-reading-card]').count(), 3)
  assert.equal(await page.locator('[data-agenda-card]').count(), 3)
  assert.equal(await page.locator('[data-agenda-secondary]').count(), 1)
  assert.equal(await page.locator('[data-relation-group]').count(), 4)
  assert.equal(await page.locator('[data-relation-item]').count(), 8)
  assert.equal(await page.locator('[data-analysis-check]').count(), 3)
  assert.equal(await page.locator('.vpr-page details').count(), 9)
  assert.equal(await page.locator('.vpr-agenda-collective').count(), 1)
  assert.deepEqual(
    await page.locator('[data-reading-card]').evaluateAll((cards) => cards.map((card) => card.getAttribute('data-reading-card'))),
    ['demografia-matriculas-rede', 'transformacao-economica-ept', 'escolaridade-adulta-eja'],
  )
  assert.equal(await page.locator('[data-strongest-pattern="ruralidade-organizacao-rede"]').isVisible(), true)
  assert.match(
    await page.locator('[data-strongest-pattern="ruralidade-organizacao-rede"]').innerText(),
    /não mostra o que veio primeiro nem se a oferta foi suficiente/iu,
  )
  const visibleBoundaries = page.locator('[data-reading-boundary="visible"]')
  assert.equal(await visibleBoundaries.count(), 3)
  assert.equal(await visibleBoundaries.evaluateAll((elements) => elements.every((element) => {
    const style = getComputedStyle(element)
    return style.display !== 'none' && style.visibility !== 'hidden' && element.getClientRects().length > 0
  })), true, 'os três limites específicos devem estar visíveis sem expandir detalhes')
  assert.equal(await page.locator('.vpa-nav a').count(), 4)
  assert.deepEqual(await page.locator('.vpa-nav a').allTextContents(), [
    'Resumo',
    'Entender o cenário',
    'Planejar os próximos anos',
    'Explorar relações',
  ])
  assert.equal(
    await page.locator('[data-reading-card="transformacao-economica-ept"] .vpr-measure__zero').count(),
    1,
  )
  assert.doesNotMatch(await page.locator('body').innerText(), /financiamento|agenda ausente|candidata rejeitada/iu)
  assert.equal(await page.locator('[data-reading-card]').evaluateAll((cards) => cards.every((card) => {
    const labelledBy = card.getAttribute('aria-labelledby')
    return labelledBy !== null && document.getElementById(labelledBy)?.tagName === 'H3'
  })), true, 'cada leitura deve ser nomeada por seu h3')
  assert.equal(await page.locator('[data-analysis-check]').evaluateAll((checks) => checks.every((check) => {
    const labelledBy = check.getAttribute('aria-labelledby')
    return labelledBy !== null && document.getElementById(labelledBy)?.textContent?.trim().length > 0
  })), true, 'cada resultado analítico deve possuir um nome acessível')
  assert.equal(await page.locator('[data-reading-card]').evaluateAll((cards) => cards.every((card) => {
    const measureCount = card.querySelectorAll('.vpr-measure-grid > .vpr-measure').length
    return measureCount >= 1
      && measureCount <= 2
      && card.querySelectorAll('.vpr-measure-grid .vpr-measure__value').length === measureCount
      && card.querySelector('.vpr-reading__question') !== null
      && card.querySelector('.vpr-action') !== null
      && card.querySelector('[data-reading-boundary="visible"]') !== null
  })), true, 'cada história responde pergunta, mostra até duas medidas, ação e limite')

  const signalLimits = await page.locator('.vpr-signal-grid article').evaluateAll((signals) => signals.map((signal) => {
    const title = signal.querySelector('h3')?.textContent ?? ''
    const body = signal.querySelector('p')?.textContent ?? ''
    return {
      titleWords: (title.match(/\S+/gu) ?? []).length,
      bodyWords: (body.match(/\S+/gu) ?? []).length,
      highlightedNumbers: (body.match(/(?:^|\s)[+-]?\d+(?:[.,]\d+)?%?(?=\s|[.,;:]|$)/gu) ?? []).length,
    }
  }))
  assert.equal(signalLimits.length, 3)
  for (const signal of signalLimits) {
    assert.ok(signal.titleWords <= 12, 'título do sinal com ' + signal.titleWords + ' palavras')
    assert.ok(signal.bodyWords <= 35, 'explicação do sinal com ' + signal.bodyWords + ' palavras')
    assert.ok(signal.highlightedNumbers <= 2, 'sinal com ' + signal.highlightedNumbers + ' números')
  }

  const relationIntegrity = await page.locator('[data-relation-item]').evaluateAll((relations) => relations.map((relation) => ({
    id: relation.getAttribute('data-relation-item'),
    measureCount: relation.querySelectorAll('.vpr-measure').length,
    periodsComplete: [...relation.querySelectorAll('.vpr-measure__meta')]
      .every((meta) => (meta.textContent?.trim().length ?? 0) > 0),
    text: relation.textContent ?? '',
  })))
  assert.equal(relationIntegrity.length, 8)
  for (const relation of relationIntegrity) {
    assert.equal(relation.measureCount, 2, relation.id + ': duas medidas públicas')
    assert.equal(relation.periodsComplete, true, relation.id + ': período ausente')
    assert.match(relation.text, /(?:Questão para a gestão|Por que isso importa para a gestão)\./u, relation.id)
    assert.match(relation.text, /Limite\./u, relation.id)
    assert.match(relation.text, /Fontes:/u, relation.id)
  }
  assert.equal(await page.locator('[data-relation-item][data-analysis-status="not_confirmed"]').evaluateAll(
    (relations) => relations.every((relation) => (
      /Pergunta que testamos\./u.test(relation.textContent ?? '')
      && /O que encontramos\./u.test(relation.textContent ?? '')
      && /Por que isso importa para a gestão\./u.test(relation.textContent ?? '')
    )),
  ), true, 'relações não confirmadas devem explicar pergunta, resultado e importância')

  const negativeResults = await page
    .locator('[data-relation-item][data-analysis-status="not_confirmed"] .vpr-relation__result')
    .allTextContents()
  assert.equal(negativeResults.length, 3)
  for (const result of negativeResults) {
    assert.match(result, /(?:continua|segue) em aberto|não apareceu/iu)
    assert.doesNotMatch(result, /se repetiu|comprovad|relação confirmada/iu)
  }
  const watchResults = await page
    .locator('[data-relation-item][data-analysis-status="watch"] .vpr-relation__result')
    .allTextContents()
  assert.equal(watchResults.length, 2)
  for (const result of watchResults) assert.match(result, /faltam|não sabemos/iu)

  const primaryText = await page.locator('.vpr-page').innerText()
  const visibleWords = primaryText.trim().split(/\s+/u).filter(Boolean).length
  assert.ok(visibleWords <= 1_500, 'camada principal tem ' + visibleWords + ' palavras')
  assert.doesNotMatch(
    primaryText,
    /\b(?:p-valor|significância|regressão|bootstrap|placebo|intervalo de confiança|correlação|causalidade|inferência|robustez|modelo|efeito fixo|evidência insuficiente|Pearson|Spearman)\b|(?:^|\s)q(?:\s|$)/iu,
  )
  const density = await page.locator('.vpr-page').evaluate((root) => ({
    pageHeight: root.scrollHeight,
    headingCount: [...root.querySelectorAll('h1, h2, h3')]
      .filter((heading) => heading.closest('details:not([open])') === null).length,
    nestedDetails: [...root.querySelectorAll('details')].some((details) => details.querySelector('details') !== null),
    cardWords: [...root.querySelectorAll('[data-reading-card]')].map((card) => ({
      id: card.getAttribute('data-reading-card'),
      words: (card.innerText.match(/\S+/gu) ?? []).length,
    })),
  }))
  assert.ok(density.pageHeight <= 7_183, 'altura pública: ' + density.pageHeight + 'px')
  assert.ok(density.headingCount <= 20, 'títulos visíveis: ' + density.headingCount)
  assert.equal(density.nestedDetails, false, 'a leitura não deve aninhar expansões')
  for (const card of density.cardWords) {
    assert.ok(
      card.words >= 110 && card.words <= 160,
      card.id + ': ' + card.words + ' palavras visíveis; cartões=' + JSON.stringify(density.cardWords),
    )
  }
  const agendaWords = await page.locator('[data-agenda-card]').evaluateAll((cards) => cards.map((card) => ({
    id: card.getAttribute('data-agenda-card'),
    words: (card.innerText.match(/\S+/gu) ?? []).length,
  })))
  for (const agenda of agendaWords) {
    assert.ok(agenda.words <= 90, agenda.id + ': ' + agenda.words + ' palavras visíveis')
  }
  assert.equal(
    await page.locator('[data-relation-group]').evaluateAll((groups) => groups.every((group) => !group.hasAttribute('open'))),
    true,
    'os quatro grupos da biblioteca começam recolhidos',
  )

  const initialUrl = page.url()
  const readings = page.locator('#vpr-understand')
  await page.getByRole('link', { name: 'Entender o cenário', exact: true }).click()
  assert.equal(page.url(), initialUrl)
  assert.equal(await readings.evaluate((element) => document.activeElement === element), true)

  const firstDetails = page.locator('.vpr-details').first()
  assert.equal(await firstDetails.getAttribute('open'), null)
  const firstSummary = firstDetails.locator('summary')
  await firstSummary.focus()
  assert.equal(await firstSummary.evaluate((element) => document.activeElement === element), true)
  await page.keyboard.press('Enter')
  assert.equal(await firstDetails.getAttribute('open'), '')
  assert.match(await firstDetails.innerText(), /Outras explicações possíveis/u)
  assert.match(await firstDetails.innerText(), /O que acompanhar/u)
  assert.match(await firstDetails.innerText(), /Fontes e o que cada dado mede/u)

  const watchDetails = page.locator('[data-reading-card="escolaridade-adulta-eja"] .vpr-details')
  const watchBody = watchDetails.locator('.vpr-details__body')
  assert.equal(await watchDetails.getAttribute('open'), null)
  assert.equal(await watchBody.isVisible(), false, 'a estimativa de monitoramento começa recolhida')
  assert.match(await watchBody.textContent(), /0,52/u)
  await watchDetails.locator('summary').click()
  assert.equal(await watchBody.isVisible(), true)
  assert.match(await watchBody.innerText(), /0,52/u)

  const agendaDetails = page.locator('.vpr-agenda-collective')
  assert.equal(await agendaDetails.getAttribute('open'), null)
  await agendaDetails.locator('summary').click()
  assert.equal(await agendaDetails.getAttribute('open'), '')
  assert.equal(await agendaDetails.locator(':scope > div > section').count(), 4)
}

async function assertPrint(page) {
  await page.emulateMedia({ media: 'print' })
  const metrics = await page.evaluate(() => ({
    nav: getComputedStyle(document.querySelector('.vpa-nav')).display,
    printButton: getComputedStyle(document.querySelector('.vpr-hero__scope button')).display,
    detailsBody: getComputedStyle(document.querySelector('.vpr-details__body')).display,
    agendaBody: getComputedStyle(document.querySelector('.vpr-agenda-collective > div')).display,
    libraryBody: getComputedStyle(document.querySelector('.vpr-library__rows')).display,
    methodBody: getComputedStyle(document.querySelector('.vpr-method__details > div')).display,
    visibleBoundary: getComputedStyle(document.querySelector('[data-reading-boundary="visible"]')).display,
  }))
  assert.equal(metrics.nav, 'none')
  assert.equal(metrics.printButton, 'none')
  assert.equal(metrics.detailsBody, 'grid')
  assert.equal(metrics.agendaBody, 'grid')
  assert.equal(metrics.libraryBody, 'grid')
  assert.equal(metrics.methodBody, 'grid')
  assert.notEqual(metrics.visibleBoundary, 'none')
  await assertNoHorizontalOverflow(page, 'impressão')
  await page.emulateMedia({ media: 'screen' })
}

async function capture(page, name) {
  if (!screenshotEnabled) return
  await mkdir(screenshotDir, { recursive: true })
  await page.screenshot({ fullPage: true, path: path.join(screenshotDir, `${name}.png`) })
}

async function assertForcedFallback(context) {
  const page = await context.newPage()
  page.setDefaultTimeout(60_000)
  await page.goto(`${baseUrl}/?fallback=1`, { waitUntil: 'domcontentloaded' })
  await page.locator('.vocacoes-pne-official-page').waitFor({ state: 'visible' })
  assert.equal(await page.locator('.vocacoes-pne-advanced-page').count(), 0)
  assert.equal(await page.locator('[data-publication="official"]').count(), 1)
  assert.equal(await page.evaluate(() => document.documentElement.dataset.resolvedSurface), 'official_previous')
  await page.close()
}

async function assertUnsupportedScopeNotice(context) {
  const page = await context.newPage()
  page.setDefaultTimeout(60_000)
  await page.goto(`${baseUrl}/?unsupported=1`, { waitUntil: 'domcontentloaded' })
  await page.locator('.vocacoes-pne-official-page').waitFor({ state: 'visible' })
  assert.equal(await page.locator('.vocacoes-pne-advanced-page').count(), 0)
  const notice = page.locator('[data-advanced-scope-note]')
  assert.equal(await notice.count(), 1)
  assert.equal(await notice.isVisible(), true)
  assert.match(await notice.innerText(), /novo dossiê analítico está disponível para o Vale do Sinos e Nova Santa Rita/u)
  assert.match(await notice.innerText(), /leitura oficial anterior/u)
  await page.close()
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
      const page = await openAdvancedPage(context)
      page.on('console', (message) => {
        if (message.type() === 'error') errors.push(`${viewport.label}: ${message.text()}`)
      })
      page.on('pageerror', (error) => errors.push(`${viewport.label}: ${error.message}`))
      await assertNoHorizontalOverflow(page, viewport.label)
      if (viewport.label === 'desktop') {
        await assertContentAndInteraction(page)
        await assertPrint(page)
        await assertForcedFallback(context)
        await assertUnsupportedScopeNotice(context)
      }
      if (viewport.label === 'mobile') {
        const nav = await page.locator('.vpa-nav').evaluate((element) => ({
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

    const regionalContext = await browser.newContext({ viewport: { width: 1280, height: 900 } })
    const regionalPage = await openAdvancedPage(regionalContext, '?region=1')
    assert.equal(await regionalPage.locator('[data-scope="region"]').count(), 1)
    assert.equal(await regionalPage.getByRole('heading', { name: 'Vale do Sinos: educação e território' }).count(), 1)
    await regionalContext.close()

    assert.deepEqual(errors, [])
    console.log('OK: AA5 passou em desktop, tablet, mobile, impressão, região e fallback forçado.')
  } finally {
    if (browser !== undefined) await browser.close()
    if (server !== null) await server.close()
  }
}

run().catch((error) => {
  console.error(error instanceof Error ? error.stack : String(error))
  process.exitCode = 1
})
