const assert = require('node:assert/strict')
const { chromium } = require('playwright')

const BASE_URL = process.env.BASE_URL ?? 'http://127.0.0.1:5173'
const MUNICIPALITY = 'Agudo'
const MUNICIPALITY_SLUG = 'agudo'
const MUNICIPALITY_ID = '4300109'
const SECOND_MUNICIPALITY = 'Alegria'
const SECOND_MUNICIPALITY_ID = '4300455'
const SECOND_MUNICIPALITY_SLUG = 'alegria'
const MUNICIPALITY_STORAGE_KEY = 'pne_dashboard_context_v2'
const LEGACY_MUNICIPALITY_STORAGE_KEY = 'pne_dashboard_municipio'
const VIEWPORTS = [
  { width: 1366, height: 768 },
  { width: 390, height: 844 },
]

async function selectMunicipality(page, municipality = MUNICIPALITY) {
  const input = page.locator('input[role="combobox"]:visible').first()
  await input.fill(municipality)
  await page.getByRole('option', { name: municipality, exact: true }).first().click()
  await page.getByRole('button', { name: 'Limpar seleção' }).first().waitFor({ state: 'visible' })
}

async function assertGlobalMunicipalitySelection(page, municipality) {
  const input = page.locator('input[role="combobox"]:visible')
  assert.equal(await input.count(), 1, 'há exatamente um seletor municipal global visível')
  assert.equal(await input.inputValue(), municipality, 'o seletor municipal global preserva a seleção')
}

async function readStoredMunicipalityContext(page) {
  return page.evaluate((storageKey) => {
    const raw = localStorage.getItem(storageKey)
    return raw ? JSON.parse(raw) : null
  }, MUNICIPALITY_STORAGE_KEY)
}

async function assertCanonicalMunicipalityStorage(page, municipalityId) {
  assert.deepEqual(await readStoredMunicipalityContext(page), {
    schemaVersion: 'dashboard-context-v2',
    stateCode: 'RS',
    municipalityId,
  })
  assert.equal(
    await page.evaluate((storageKey) => localStorage.getItem(storageKey), LEGACY_MUNICIPALITY_STORAGE_KEY),
    null,
  )
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

async function verifyViewport(browser, viewport) {
  const context = await browser.newContext({ viewport })
  const page = await context.newPage()
  const label = `${viewport.width}x${viewport.height}`
  const browserErrors = []
  const financeRequests = []

  page.on('console', (message) => {
    if (message.type() === 'error') browserErrors.push(`console: ${message.text()}`)
  })
  page.on('pageerror', (error) => browserErrors.push(`pageerror: ${error.message}`))
  page.on('request', (request) => {
    if (/\/data\/municipios\/[^/]+\/financeiro\.json$/.test(new URL(request.url()).pathname)) {
      financeRequests.push(request.url())
    }
  })

  try {
    await page.goto(`${BASE_URL}/#home`, { waitUntil: 'domcontentloaded' })
    await page.getByRole('heading', { level: 1 }).waitFor({ state: 'visible' })
    await selectMunicipality(page)
    await selectMunicipality(page, SECOND_MUNICIPALITY)
    await assertGlobalMunicipalitySelection(page, SECOND_MUNICIPALITY)
    await selectMunicipality(page)
    await assertCanonicalMunicipalityStorage(page, MUNICIPALITY_ID)
    await page.getByRole('button', { name: 'Limpar seleção' }).first().click()
    assert.equal(await readStoredMunicipalityContext(page), null)
    await selectMunicipality(page)
    await assertNoHorizontalOverflow(page, `Home ${label}`)

    await page.goto(`${BASE_URL}/#educacao?municipio=${SECOND_MUNICIPALITY_ID}&secao=panorama`, { waitUntil: 'domcontentloaded' })
    await page.getByRole('heading', { level: 1, name: 'Panorama educacional' }).first().waitFor({ state: 'visible' })
    await assertGlobalMunicipalitySelection(page, SECOND_MUNICIPALITY)
    await page.waitForFunction((slug) => new URLSearchParams(window.location.hash.split('?')[1]).get('municipio') === slug, SECOND_MUNICIPALITY_SLUG)
    await assertCanonicalMunicipalityStorage(page, SECOND_MUNICIPALITY_ID)

    await page.goto(`${BASE_URL}/#educacao?municipio=${encodeURIComponent(MUNICIPALITY)}&secao=panorama`, { waitUntil: 'domcontentloaded' })
    await assertGlobalMunicipalitySelection(page, MUNICIPALITY)
    await page.waitForFunction((slug) => new URLSearchParams(window.location.hash.split('?')[1]).get('municipio') === slug, MUNICIPALITY_SLUG)
    await assertCanonicalMunicipalityStorage(page, MUNICIPALITY_ID)

    if (viewport.width < 700) {
      await page.getByRole('button', { name: 'Menu', exact: true }).click()
      await page.getByRole('button', { name: 'Fechar menu' }).first().waitFor({ state: 'visible' })
      await page.getByRole('button', { name: 'Fechar menu' }).first().click()
    }

    for (const [route, heading] of [
      ['pne2014', /PNE 2014/],
      ['pne2026', /PNE 2026/],
    ]) {
      await page.goto(`${BASE_URL}/#${route}`, { waitUntil: 'domcontentloaded' })
      await page.getByRole('heading', { level: 1, name: heading }).waitFor({ state: 'visible' })
      await page.locator('button:visible, a:visible, input:visible').first().focus()
      const hoverCandidate = page.locator('.meta-card:visible, .platform-entry-card:visible').first()
      if (await hoverCandidate.count()) await hoverCandidate.hover()
      await assertNoHorizontalOverflow(page, `${route} ${label}`)
    }

    await page.goto(`${BASE_URL}/#educacao?secao=visao-geral`, { waitUntil: 'domcontentloaded' })
    await page.getByRole('heading', { level: 1, name: 'Conheça a educação do município' }).first().waitFor({ state: 'visible' })
    await assertNoHorizontalOverflow(page, `Visão geral de Educação ${label}`)

    await page.goto(`${BASE_URL}/#educacao?municipio=${MUNICIPALITY_SLUG}&secao=panorama`, { waitUntil: 'domcontentloaded' })
    await page.getByRole('heading', { level: 1, name: 'Panorama educacional' }).first().waitFor({ state: 'visible' })
    await assertGlobalMunicipalitySelection(page, MUNICIPALITY)
    assert.doesNotMatch(
      await page.locator('main').innerText(),
      new RegExp(`Município:\\s*${MUNICIPALITY}`),
      `${label}: a seleção municipal não é repetida no conteúdo principal`,
    )
    await assertNoHorizontalOverflow(page, `Panorama educacional ${label}`)

    await page.goto(`${BASE_URL}/#pne-legal-goals?municipio=${MUNICIPALITY_SLUG}`, { waitUntil: 'domcontentloaded' })
    await page.getByRole('heading', { level: 1, name: 'Metas legais do PNE 2026–2036' }).waitFor({ state: 'visible' })
    const legalGoalsMainText = await page.locator('main').innerText()
    assert.doesNotMatch(
      legalGoalsMainText,
      new RegExp(MUNICIPALITY),
      `${label}: a seleção municipal não é repetida nas metas legais`,
    )
    assert.match(legalGoalsMainText, /Direto/)
    assert.match(legalGoalsMainText, /Parcial/)
    assert.match(legalGoalsMainText, /Complementar/)

    await page.goto(`${BASE_URL}/#educacao?municipio=${MUNICIPALITY_SLUG}&secao=relatorio-tecnico-municipal`, { waitUntil: 'domcontentloaded' })
    await page.getByRole('heading', { level: 1, name: 'Relatório Técnico Municipal' }).waitFor({ state: 'visible' })
    assert.equal(await page.locator('.municipal-technical-report__section').count(), 19)
    await assertNoHorizontalOverflow(page, `Relatório Técnico Municipal ${label}`)

    await page.goto(`${BASE_URL}/#diagnostico?municipio=${MUNICIPALITY_SLUG}`, { waitUntil: 'domcontentloaded' })
    await page.getByRole('heading', {
      level: 1,
      name: 'Diagnóstico educacional',
    }).waitFor({ state: 'visible' })
    await page.getByRole('heading', { name: 'Resultados por tema' }).waitFor({ state: 'visible' })
    assert.equal(financeRequests.length, 0, `${label}: financeiro permanece lazy fora da rota`)
    await assertNoHorizontalOverflow(page, `Diagnóstico ${label}`)

    await page.goto(`${BASE_URL}/#financeiros-panorama?municipio=${MUNICIPALITY_SLUG}`, { waitUntil: 'domcontentloaded' })
    await page.getByRole('heading', { level: 1, name: 'Panorama financeiro' }).waitFor({ state: 'visible' })
    await page.getByRole('heading', { name: 'Fundeb e complementações' }).waitFor({ state: 'visible' })
    await page.getByRole('heading', { name: 'QSE — Quota Salário Educação' }).waitFor({ state: 'visible' })
    assert.ok(financeRequests.some((url) => url.includes(`/${MUNICIPALITY_ID}/financeiro.json`)))
    await assertNoHorizontalOverflow(page, `Panorama financeiro ${label}`)

    assert.deepEqual(browserErrors, [], `${label}: erros no navegador`)
  } finally {
    await context.close()
  }
}

async function verifyLegacyStorageMigration(browser) {
  const context = await browser.newContext({ viewport: VIEWPORTS[0] })
  const page = await context.newPage()
  await page.addInitScript(({ key, municipality }) => {
    localStorage.setItem(key, municipality)
  }, { key: LEGACY_MUNICIPALITY_STORAGE_KEY, municipality: MUNICIPALITY })

  try {
    await page.goto(`${BASE_URL}/#home`, { waitUntil: 'domcontentloaded' })
    await page.getByRole('button', { name: 'Limpar seleção' }).first().waitFor({ state: 'visible' })
    await assertCanonicalMunicipalityStorage(page, MUNICIPALITY_ID)
  } finally {
    await context.close()
  }
}

async function main() {
  const browser = await chromium.launch({ headless: true })
  try {
    await verifyLegacyStorageMigration(browser)
    for (const viewport of VIEWPORTS) await verifyViewport(browser, viewport)
  } finally {
    await browser.close()
  }
  console.log(`Plataforma atual validada em ${VIEWPORTS.length} viewports.`)
}

main().catch((error) => {
  console.error(error)
  process.exitCode = 1
})
