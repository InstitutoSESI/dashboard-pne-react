const assert = require('node:assert/strict')
const { chromium } = require('playwright')

const BASE_URL = process.env.BASE_URL ?? 'http://127.0.0.1:5191'
const INTERNAL_URL = `${BASE_URL}/#vocacoes-pne-interno`
const PRINT_SCREENSHOT_PATH = process.env.PRINT_SCREENSHOT_PATH
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

async function assertEventually(assertion, attempts = 40) {
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

async function selectMunicipality(page, name) {
  const selector = page.locator('input[role="combobox"]:visible')
  assert.equal(await selector.count(), 1, 'somente o seletor municipal interno fica visível')
  await selector.fill(name)
  await page.getByRole('option', { name, exact: true }).click()
  await page.getByRole('heading', { level: 1, name: `${name}: educação, território e próximos anos`, exact: true }).waitFor()
  await assertEventually(async () => assert.equal(await selector.inputValue(), name))
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

async function contrastRatio(page, selector) {
  return page.locator(selector).first().evaluate((element) => {
    function channels(color) {
      const values = color.match(/[\d.]+/gu)?.slice(0, 3).map(Number)
      if (!values || values.length !== 3) throw new Error(`cor não reconhecida: ${color}`)
      return color.startsWith('color(srgb') ? values.map((value) => value * 255) : values
    }
    function luminance(color) {
      const linear = channels(color).map((value) => {
        const normalized = value / 255
        return normalized <= 0.04045 ? normalized / 12.92 : ((normalized + 0.055) / 1.055) ** 2.4
      })
      return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]
    }
    const foreground = getComputedStyle(element).color
    let current = element
    let background = 'rgb(255, 255, 255)'
    while (current) {
      const candidate = getComputedStyle(current).backgroundColor
      if (candidate && candidate !== 'rgba(0, 0, 0, 0)' && candidate !== 'transparent') {
        background = candidate
        break
      }
      current = current.parentElement
    }
    const first = luminance(foreground)
    const second = luminance(background)
    return (Math.max(first, second) + 0.05) / (Math.min(first, second) + 0.05)
  })
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
    const url = new URL(request.url())
    if (/CORPUS_VARIANTES_TERRITORIAIS_JOB5H|\/data\/municipios\/[^/]+\//u.test(url.pathname)) {
      forbiddenRequests.push(url.pathname)
    }
    if (url.origin !== BASE_URL) forbiddenRequests.push(url.href)
  })
  await page.addInitScript(() => localStorage.clear())

  try {
    await page.goto(INTERNAL_URL, { waitUntil: 'domcontentloaded' })
    await page.getByRole('heading', { level: 1, name: 'Nova Santa Rita: educação, território e próximos anos' }).waitFor()
    await page.getByText('Página piloto para validação com a gestora — ainda não publicada', { exact: true }).waitFor()

    assert.equal(await page.locator('main[data-job="manager-review-v1"][data-publication="closed"]').count(), 1)
    assert.equal(await page.locator('.vpm-direction').count(), 2)
    assert.equal(await page.locator('.vpm-card').count(), 7)
    assert.equal(await page.locator('.vpm-priority').count(), 3)
    assert.equal(await page.locator('.vpm-relation-visual').count(), 7)
    assert.equal(await page.locator('.vpm-card').evaluateAll((cards) => cards.every((card) => card.querySelectorAll('[data-main-visual]').length === 1)), true)
    assert.equal(await page.locator('.vpm-direction-nav a').count(), 2)
    assert.equal(await page.locator('.vpi-macroblock').count(), 7)
    assert.equal(await page.locator('h1').count(), 1)
    assert.equal(await page.locator('.context-bar:visible').count(), 0)
    assert.equal(await page.locator('.vpi-technical').count(), 0)
    assert.equal(await page.getByTestId('job5i-evidence-layer').getAttribute('open'), null)
    assert.equal(await page.locator('input[role="combobox"]:visible').inputValue(), 'Nova Santa Rita')
    assert.equal(await page.locator('.app-header a[href*="vocacoes-pne-interno"]').count(), 0)

    const opening = page.locator('.vpm-review')
    const openingText = await opening.innerText()
    for (const anchor of ['759 → 848', '459 → 823', '799 → 840', '309 → 208', '104 → 172', '17 → 722', '0 → 0', '174 de 219 eventos']) {
      assert.ok(openingText.includes(anchor), anchor)
    }
    assert.match(openingText, /O que o território ajuda a compreender sobre a educação\?/u)
    assert.match(openingText, /O que o futuro do território exige da educação\?/u)
    assert.match(openingText, /Nova Santa Rita ampliou matrículas e turmas do ensino médio enquanto o Vale retraiu matrículas/u)
    assert.match(await page.locator('#relacao-trajetoria-mobilidade').innerText(), /Residentes que estudavam fora/u)
    assert.match(await page.locator('#relacao-trabalho-juvenil-ensino-medio').innerText(), /Aprendizagem nas admissões juvenis/u)
    assert.match(await page.locator('#agenda-ocupacoes-formacao').innerText(), /EPT localizada/u)

    const visibleText = await page.locator('body').innerText()
    for (const forbidden of [
      /\bR[1-8]\b/u,
      /\bTVD\b/u,
      /\brho\b/iu,
      /\bfixed effects\b/iu,
      /\bregress(?:ão|ion)\b/iu,
      /\bshift[- ]share\b/iu,
      /\bHHI\b/u,
      /\bGate(?: 11)?\b/iu,
      /\bschema\b/iu,
      /mobilidade (?:não )?explica/iu,
      /não (?:há|existe) relação/iu,
    ]) assert.doesNotMatch(visibleText, forbidden)

    const firstCardDetails = page.locator('.vpm-card .vpm-details').first()
    assert.equal(await firstCardDetails.getAttribute('open'), null)
    await firstCardDetails.locator('summary').click()
    assert.match(await firstCardDetails.innerText(), /Indicadores para acompanhar/u)
    assert.match(await firstCardDetails.innerText(), /Fontes e períodos/u)
    assert.match(await firstCardDetails.innerText(), /Como ler esta relação/u)
    await firstCardDetails.locator('summary').click()

    const firstAnchor = page.locator('.vpm-direction-nav a').first()
    await firstAnchor.focus()
    await page.keyboard.press('Enter')
    assert.equal(new URL(page.url()).hash, '#vocacoes-pne-interno')
    await assertEventually(async () => {
      const top = await page.locator('#education-to-territory').evaluate((element) => element.getBoundingClientRect().top)
      assert.ok(top < 180)
    })

    assert.ok(await contrastRatio(page, '.vpm-card__header h3') >= 4.5)
    assert.ok(await contrastRatio(page, '.vpm-priority > p:not(.vpi-eyebrow)') >= 4.5)
    assert.ok(await contrastRatio(page, '.vpm-method-note') >= 4.5)

    await page.getByRole('button', { name: 'Vale do Sinos', exact: true }).click()
    await page.getByRole('heading', { level: 1, name: 'Vale do Sinos: educação, território e próximos anos' }).waitFor()
    await page.getByRole('heading', { name: 'O que os dados colocam na agenda de Vale do Sinos', exact: true }).waitFor()
    assert.equal(await page.locator('input[role="combobox"]:visible').inputValue(), '')
    assert.equal(await page.locator('.vpm-card').count(), 7)

    const firstTitles = new Set()
    for (const [ibgeCode, name] of MUNICIPALITIES) {
      await selectMunicipality(page, name)
      await page.getByRole('heading', { level: 1, name: `${name}: educação, território e próximos anos` }).waitFor()
      const stored = await page.evaluate(() => JSON.parse(localStorage.getItem('pne_dashboard_context_v2')))
      assert.equal(stored.municipalityId, ibgeCode)
      assert.equal(typeof stored.municipalityId, 'string')
      assert.equal(await page.locator('.vpm-card').count(), 7)
      firstTitles.add(await page.locator('.vpm-card h3').first().innerText())
      assert.match(await page.locator('.vpi-hero__region').innerText(), /Vale do Sinos/u)
    }
    assert.ok(firstTitles.size >= 4, 'títulos municipais são derivados dos dados e mudam entre territórios')

    await selectMunicipality(page, 'Ivoti')
    assert.match(await page.locator('#agenda-ocupacoes-formacao').innerText(), /EPT localizada/u)
    assert.match(await page.locator('#agenda-ocupacoes-formacao').innerText(), /153 → 0/u)
    assert.ok(await page.locator('#agenda-ocupacoes-formacao [data-availability-state="observed_zero"]').count() > 0)

    await selectMunicipality(page, 'Novo Hamburgo')
    assert.match(await page.locator('#agenda-ocupacoes-formacao').innerText(), /5\.541/u)

    await selectMunicipality(page, 'Nova Santa Rita')
    const evidenceLayer = page.getByTestId('job5i-evidence-layer')
    await evidenceLayer.locator('summary').first().click()
    assert.notEqual(await evidenceLayer.getAttribute('open'), null)
    assert.equal(await evidenceLayer.locator('.vpi-macroblock').count(), 7)
    const demographyEvidence = evidenceLayer.getByTestId('evidence-demography')
    await demographyEvidence.locator('summary').click()
    assert.match(await demographyEvidence.innerText(), /Indisponível/u)
    await demographyEvidence.locator('summary').click()
    const firstTabs = evidenceLayer.locator('.vpi-tabs').first()
    const firstTab = firstTabs.getByRole('tab').first()
    await firstTab.focus()
    await page.keyboard.press('ArrowRight')
    assert.equal(await firstTabs.getByRole('tab').nth(1).getAttribute('aria-selected'), 'true')
    const tooltipButton = evidenceLayer.getByRole('button', { name: 'Como ler' }).first()
    await tooltipButton.focus()
    const tooltipId = await tooltipButton.getAttribute('aria-describedby')
    assert.ok(tooltipId)
    assert.equal(await page.locator(`#${tooltipId}`).getAttribute('role'), 'tooltip')
    await evidenceLayer.locator('summary').first().click()

    await page.getByRole('button', { name: 'Abrir modo técnico' }).click()
    await page.getByRole('heading', { name: 'Modo técnico', exact: true }).waitFor()
    const technicalText = await page.locator('.vpi-technical').innerText()
    assert.match(technicalText, /Critérios metodológicos/u)
    assert.doesNotMatch(technicalText, /shift[- ]share/iu)

    await page.emulateMedia({ media: 'print' })
    for (const selector of ['.app-header', '.context-bar', '.sidebar-mobile-bar', '.vpi-controls', '.vpm-direction-nav', '.vpi-review-tools', '.vpi-technical', '.vpk-evidence-layer']) {
      const element = page.locator(selector).first()
      if (await element.count()) assert.equal(await element.evaluate((node) => getComputedStyle(node).display), 'none', selector)
    }
    assert.notEqual(await page.locator('.vpi-internal-banner').evaluate((node) => getComputedStyle(node).display), 'none')
    assert.equal(await page.locator('.vpm-card:visible').count(), 7)
    assert.equal(await page.locator('.vpm-print-details:visible').count(), 7)
    if (PRINT_SCREENSHOT_PATH) {
      await page.setViewportSize({ width: 794, height: 1123 })
      await page.evaluate(() => {
        document.documentElement.style.scrollBehavior = 'auto'
        window.scrollTo(0, 0)
      })
      await assertEventually(async () => assert.equal(await page.evaluate(() => window.scrollY), 0))
      await assertNoHorizontalOverflow(page, 'impressão A4')
      await page.screenshot({ path: PRINT_SCREENSHOT_PATH, fullPage: false })
      await page.setViewportSize({ width: 1440, height: 1000 })
    }
    await page.emulateMedia({ media: 'screen' })
    await page.getByRole('button', { name: 'Ocultar modo técnico' }).click()

    await assertNoHorizontalOverflow(page, 'desktop 1440')
    await page.setViewportSize({ width: 1024, height: 900 })
    await assertNoHorizontalOverflow(page, 'tablet 1024')
    await page.setViewportSize({ width: 390, height: 844 })
    await assertNoHorizontalOverflow(page, 'mobile 390')
    assert.equal(await page.locator('.vpm-direction-nav a:visible').count(), 2)
    assert.equal(await page.locator('.vpm-relation-visual:visible').count(), 7)

    await page.locator('body').click({ position: { x: 2, y: 2 } })
    await page.keyboard.press('Tab')
    const focusStyle = await page.locator(':focus').evaluate((element) => {
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
  () => console.log('OK: E2E, acessibilidade, mobile e impressão da página de revisão passaram.'),
  (error) => {
    console.error(error)
    process.exitCode = 1
  },
)
