const assert = require('node:assert/strict')
const { mkdirSync } = require('node:fs')
const path = require('node:path')
const { chromium } = require('playwright')


const BASE_URL = process.env.BASE_URL ?? 'http://127.0.0.1:5191'
const INTERNAL_URL = `${BASE_URL}/#vocacoes-pne-interno`
const SCREENSHOT_DIR = process.env.SCREENSHOT_DIR
const MUNICIPALITIES = [
  ['4303905', 'Campo Bom'],
  ['4306403', 'Dois Irmãos'],
  ['4307609', 'Estância Velha'],
  ['4307708', 'Esteio'],
  ['4310801', 'Ivoti'],
  ['4313375', 'Nova Santa Rita'],
  ['4313409', 'Novo Hamburgo'],
  ['4314803', 'Portão'],
  ['4318705', 'São Leopoldo'],
  ['4320008', 'Sapucaia do Sul'],
]

async function selectMunicipality(page, name) {
  const selector = page.locator('input[role="combobox"]:visible')
  assert.equal(await selector.count(), 1, 'somente o seletor municipal interno fica visível')
  await selector.fill(name)
  await page.getByRole('option', { name, exact: true }).click()
  await assertEventually(async () => assert.equal(await selector.inputValue(), name))
  await page.getByRole('heading', { name: `O que essa leitura reúne para ${name}`, exact: true }).waitFor()
}

async function assertEventually(assertion, attempts = 30) {
  let lastError
  for (let index = 0; index < attempts; index += 1) {
    try {
      await assertion()
      return
    } catch (error) {
      lastError = error
      await new Promise((resolve) => setTimeout(resolve, 100))
    }
  }
  throw lastError
}

async function assertNoHorizontalOverflow(page, label) {
  const dimensions = await page.evaluate(() => ({
    clientWidth: document.documentElement.clientWidth,
    scrollWidth: document.documentElement.scrollWidth,
  }))
  assert.ok(
    dimensions.scrollWidth <= dimensions.clientWidth,
    `${label}: overflow horizontal (${dimensions.scrollWidth} > ${dimensions.clientWidth})`,
  )
}

async function run() {
  const browser = await chromium.launch({ headless: true })
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } })
  const page = await context.newPage()
  const browserErrors = []
  const forbiddenRequests = []

  page.on('console', (message) => {
    if (message.type() === 'error') browserErrors.push(`console: ${message.text()}`)
  })
  page.on('pageerror', (error) => browserErrors.push(`pageerror: ${error.message}`))
  page.on('request', (request) => {
    const pathname = new URL(request.url()).pathname
    if (/CORPUS_VARIANTES_TERRITORIAIS_JOB5H|\/data\/municipios\/[^/]+\//u.test(pathname)) {
      forbiddenRequests.push(pathname)
    }
  })
  await page.addInitScript(() => localStorage.clear())

  try {
    await page.goto(INTERNAL_URL, { waitUntil: 'domcontentloaded' })
    await page.getByRole('heading', { level: 1, name: 'Educação e transformações do Vale do Sinos' }).waitFor()
    await page.getByText('Protótipo interno para avaliação — conteúdo ainda não publicado', { exact: true }).waitFor()

    assert.equal(await page.locator('.vpi-macroblock').count(), 7)
    assert.equal(await page.locator('.vpi-direction').count(), 2)
    assert.equal(await page.locator('.vpi-anchor-nav a').count(), 7)
    assert.equal(await page.locator('h1').count(), 1)
    assert.equal(await page.locator('main[data-gate-11="closed"]').count(), 1)
    assert.equal(await page.locator('.context-bar:visible').count(), 0)
    assert.equal(await page.locator('.vpi-technical').count(), 0)
    assert.equal(await page.locator('input[role="combobox"]:visible').inputValue(), 'Nova Santa Rita')

    const summary = page.locator('.vpi-municipality-summary')
    const summaryText = await summary.innerText()
    for (const anchor of [
      '459 → 823', '3.873 → 3.957', '799 → 840', '24 → 28', '1,642',
      '19,1%', '81,1%', '15,7%',
    ]) assert.match(summaryText, new RegExp(anchor.replaceAll('.', '\\.')))
    await summary.getByTestId('municipality-summary-expanded').locator('summary').click()
    const fullSummaryText = await summary.innerText()
    for (const anchor of [
      '3,2%', '24,8%', '130 → 40', '309 → 208', '0 → 0', '104 → 172',
      '1.117 → 1.638', '174', '17 → 722',
    ]) assert.match(fullSummaryText, new RegExp(anchor.replaceAll('.', '\\.')))
    assert.match(fullSummaryText, /Zero observado/u)
    assert.match(fullSummaryText, /previsão de planejamento/u)
    assert.equal(await summary.locator('[data-availability-state="observed_zero"]').count(), 1)

    await page.locator('.vpi-anchor-nav a[href="#macro-7"]').click()
    await assertEventually(async () => {
      const top = await page.locator('#macro-7').evaluate((element) => element.getBoundingClientRect().top)
      assert.ok(top < 180)
    })

    const firstTabs = page.locator('.vpi-tabs').first()
    const firstTab = firstTabs.getByRole('tab').first()
    await firstTab.focus()
    await page.keyboard.press('ArrowRight')
    assert.equal(await firstTabs.getByRole('tab').nth(1).getAttribute('aria-selected'), 'true')
    assert.equal(await firstTabs.getByRole('tab').nth(1).getAttribute('tabindex'), '0')

    const evidence = page.getByTestId('evidence-demography')
    assert.equal(await evidence.getAttribute('open'), null)
    await evidence.locator('summary').click()
    assert.notEqual(await evidence.getAttribute('open'), null)
    await evidence.getByText('Creche 0–3 isolada', { exact: true }).waitFor()
    assert.match(await evidence.innerText(), /Indisponível/u)

    const tooltipButton = page.getByRole('button', { name: 'Como ler' }).first()
    await tooltipButton.focus()
    const tooltipId = await tooltipButton.getAttribute('aria-describedby')
    assert.ok(tooltipId)
    assert.equal(await page.locator(`#${tooltipId}`).getAttribute('role'), 'tooltip')
    await assertEventually(async () => {
      assert.notEqual(await page.locator(`#${tooltipId}`).evaluate((element) => getComputedStyle(element).opacity), '0')
    })

    await page.getByRole('button', { name: 'Abrir modo técnico' }).click()
    await page.getByRole('heading', { name: 'Modo técnico', exact: true }).waitFor()
    assert.equal(await page.locator('.vpi-technical').count(), 1)
    assert.match(await page.locator('.vpi-technical').innerText(), /C1–C12/u)
    assert.doesNotMatch(await page.locator('.vpi-technical').innerText(), /detalhe individual do Caged/iu)

    await page.emulateMedia({ media: 'print' })
    if (SCREENSHOT_DIR) {
      mkdirSync(SCREENSHOT_DIR, { recursive: true })
      await page.screenshot({
        path: path.join(SCREENSHOT_DIR, '05-impressao.png'),
        fullPage: true,
      })
    }
    for (const locator of ['.app-header', '.context-bar', '.vpi-controls', '.vpi-anchor-nav', '.vpi-technical']) {
      const element = page.locator(locator).first()
      if (await element.count()) assert.equal(await element.evaluate((node) => getComputedStyle(node).display), 'none', locator)
    }
    assert.notEqual(await page.locator('.vpi-internal-banner').evaluate((node) => getComputedStyle(node).display), 'none')
    await page.emulateMedia({ media: 'screen' })
    await page.getByRole('button', { name: 'Ocultar modo técnico' }).click()

    await page.getByRole('button', { name: 'Vale do Sinos', exact: true }).click()
    await page.getByRole('heading', { name: 'O que essa leitura reúne para Vale do Sinos', exact: true }).waitFor()
    assert.equal(await page.locator('input[role="combobox"]:visible').inputValue(), '')
    assert.match(await page.locator('#macro-2').innerText(), /A visão regional não cria uma taxa agregada/u)
    assert.match(await page.locator('#macro-2').innerText(), /Mediana dos dez municípios/u)

    for (const [ibgeCode, name] of MUNICIPALITIES) {
      await selectMunicipality(page, name)
      const stored = await page.evaluate(() => JSON.parse(localStorage.getItem('pne_dashboard_context_v2')))
      assert.equal(stored.municipalityId, ibgeCode)
      assert.equal(typeof stored.municipalityId, 'string')
      assert.match(await page.locator('.vpi-hero__region').innerText(), /Vale do Sinos/u)
    }

    await selectMunicipality(page, 'Nova Santa Rita')
    assert.match(await page.locator('#macro-7').innerText(), /Zero observado/u)
    assert.match(await page.locator('#macro-7').innerText(), /Ponte local[\s\S]*Indisponível/u)

    await selectMunicipality(page, 'Campo Bom')
    const ruralZeroText = await page.locator('#macro-4').innerText()
    assert.match(ruralZeroText, /Oferta rural — Campo Bom[\s\S]*2014\s*0\s*→\s*2025\s*0/u)
    assert.match(ruralZeroText, /Zero observado/iu)

    await selectMunicipality(page, 'Novo Hamburgo')
    assert.equal(await page.locator('#macro-7 [aria-label*="Novo Hamburgo, 2025: 5.541"]').count(), 1)
    assert.match(await page.locator('#macro-7').innerText(), /39,7%/u)

    await assertNoHorizontalOverflow(page, 'desktop 1440')
    await page.setViewportSize({ width: 1024, height: 900 })
    await assertNoHorizontalOverflow(page, 'tablet 1024')
    await page.setViewportSize({ width: 390, height: 844 })
    await assertNoHorizontalOverflow(page, 'mobile 390')
    assert.equal(await page.locator('.vpi-chart svg:visible').count(), 0)
    assert.ok(await page.locator('.vpi-chart__mobile-fallback:visible').count() > 0)
    assert.equal(await page.locator('.vpi-anchor-nav a:visible').count(), 7)

    await page.locator('body').click({ position: { x: 2, y: 2 } })
    await page.keyboard.press('Tab')
    const focusTarget = page.locator(':focus')
    const focusStyle = await focusTarget.evaluate((element) => {
      const style = getComputedStyle(element)
      return { outlineStyle: style.outlineStyle, outlineWidth: style.outlineWidth }
    })
    assert.notEqual(focusStyle.outlineStyle, 'none')
    assert.notEqual(focusStyle.outlineWidth, '0px')

    const unnamedButtons = await page.locator('button:visible').evaluateAll((buttons) => buttons.filter((button) => {
      const name = button.getAttribute('aria-label') || button.textContent.trim() || button.getAttribute('title')
      return !name
    }).length)
    assert.equal(unnamedButtons, 0, 'todos os botões visíveis têm nome acessível')
    assert.equal(await page.locator('img:not([alt])').count(), 0)
    assert.equal(forbiddenRequests.length, 0, `requisições vedadas: ${forbiddenRequests.join(', ')}`)
    assert.deepEqual(browserErrors, [])
  } finally {
    await context.close()
    await browser.close()
  }
}

run().then(
  () => console.log('OK: E2E e acessibilidade do Job 5I passaram.'),
  (error) => {
    console.error(error)
    process.exitCode = 1
  },
)
