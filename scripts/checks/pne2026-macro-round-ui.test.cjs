const assert = require('node:assert/strict')
const { chromium } = require('playwright')

const BASE_URL = process.env.BASE_URL ?? 'http://127.0.0.1:5173'
const MUNICIPALITY = 'Alegrete'
const MUNICIPALITY_SLUG = 'alegrete'
const PLAN_CAREER_TITLE = 'Requisitos declarados de plano de carreira'
const TRACKING_TITLES = [
  PLAN_CAREER_TITLE,
  'Fórum de educação declarado',
  'Escolas públicas que declararam possuir conselho escolar',
]
const COMPLEMENTARY_TITLES = [
  'Mestres e doutores titulados em programas locais',
  'Cursos locais com CPC 3 a 5',
  'Concluintes de licenciaturas no Padrão 1 do Enade',
]
const NEW_TITLES = [...TRACKING_TITLES, ...COMPLEMENTARY_TITLES]

async function selectMunicipality(page, municipality = MUNICIPALITY) {
  await page.goto(`${BASE_URL}/#home`, { waitUntil: 'domcontentloaded' })
  const input = page.getByRole('combobox', { name: 'Município', exact: true })
  assert.equal(await input.count(), 1, 'seletor municipal único')
  await input.fill(municipality)
  const option = page.getByRole('option', { name: municipality, exact: true })
  assert.equal(await option.count(), 1, `opção municipal única: ${municipality}`)
  await option.click()
  await page.getByRole('button', { name: 'Limpar seleção' }).waitFor({
    state: 'visible',
  })
}

async function openDiagnostic(page) {
  await selectMunicipality(page)
  await page.goto(
    `${BASE_URL}/#diagnostico?municipio=${MUNICIPALITY_SLUG}`,
    { waitUntil: 'domcontentloaded' },
  )
  await page.getByRole('heading', {
    level: 1,
    name: `Diagnóstico educacional de ${MUNICIPALITY}`,
  }).waitFor({ state: 'visible' })
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

function getDiagnosticCard(page, title) {
  return page.getByRole('article', { name: title, exact: true })
}

async function verifyScreen(browser, viewport) {
  const context = await browser.newContext({ viewport })
  const page = await context.newPage()
  const errors = []
  const warnings = []
  page.on('console', (message) => {
    if (message.type() === 'error') errors.push(message.text())
    if (message.type() === 'warning') warnings.push(message.text())
  })
  page.on('pageerror', (error) => errors.push(error.message))

  try {
    await openDiagnostic(page)
    await assertNoHorizontalOverflow(page, `${viewport.width}x${viewport.height}`)

    const legalView = page.getByRole('button', {
      name: 'Referências previstas nas metas',
      exact: true,
    })
    const trackingView = page.getByRole('button', {
      name: 'Indicadores de acompanhamento',
      exact: true,
    })
    assert.equal(await legalView.getAttribute('aria-pressed'), 'true')
    assert.equal(await trackingView.getAttribute('aria-pressed'), 'false')

    const legalSummary = page.getByRole('region', {
      name: 'Resumo do diagnóstico',
      exact: true,
    })
    const initialLegalSummaryText = await legalSummary.innerText()
    assert.doesNotMatch(
      initialLegalSummaryText,
      /plano de carreira|fórum de educação|conselho escolar/i,
      'tracking não entra no resumo legal',
    )

    for (const title of TRACKING_TITLES) {
      assert.equal(
        await getDiagnosticCard(page, title).count(),
        0,
        `${title}: ausente da visualização legal inicial`,
      )
    }

    await trackingView.click()
    assert.equal(await legalView.getAttribute('aria-pressed'), 'false')
    assert.equal(await trackingView.getAttribute('aria-pressed'), 'true')
    assert.match(
      await page.getByRole('region', { name: 'Resultados por tema' }).innerText(),
      /Indicadores de acompanhamento/,
    )

    const planCareerCard = getDiagnosticCard(page, PLAN_CAREER_TITLE)
    assert.equal(await planCareerCard.count(), 1, `${PLAN_CAREER_TITLE}: card único`)
    const planCareerText = await planCareerCard.innerText()
    assert.match(planCareerText, /\b\d+ de 2 requisitos\b/)
    assert.match(planCareerText, /Referência de acompanhamento/)
    assert.doesNotMatch(planCareerText, /\d+(?:[.,]\d+)?\s*%/)
    assert.doesNotMatch(
      planCareerText,
      /Referência prevista na meta|cumprimento integral|meta legal alcançada/i,
    )

    for (const title of TRACKING_TITLES.filter((item) => item !== PLAN_CAREER_TITLE)) {
      const card = getDiagnosticCard(page, title)
      assert.equal(await card.count(), 1, `${title}: card único em Alegrete`)
      const cardText = await card.innerText()
      assert.match(cardText, /Referência de acompanhamento/)
      assert.doesNotMatch(
        cardText,
        /Referência prevista na meta|cumprimento integral|meta legal alcançada/i,
      )
    }

    assert.equal(
      await legalSummary.innerText(),
      initialLegalSummaryText,
      'a troca de visualização não altera o resumo legal',
    )
    const box = await planCareerCard.boundingBox()
    assert.ok(
      box && box.width <= viewport.width,
      `${PLAN_CAREER_TITLE}: card cabe no viewport`,
    )

    if (viewport.width === 1280) {
      const input = page.getByRole('combobox', { name: 'Município', exact: true })
      assert.equal(await input.count(), 1, 'seletor municipal único no diagnóstico')
      await input.fill('São Pedro da Serra')
      const option = page.getByRole('option', {
        name: 'São Pedro da Serra',
        exact: true,
      })
      assert.equal(await option.count(), 1, 'opção São Pedro da Serra única')
      await option.click()
      await page.getByRole('heading', {
        level: 1,
        name: 'Diagnóstico educacional de São Pedro da Serra',
      }).waitFor({ state: 'visible' })
      assert.equal(
        await getDiagnosticCard(
          page,
          'Mestres e doutores titulados em programas locais',
        ).count(),
        0,
        'not_applicable não cria card vazio',
      )
    }
    assert.deepEqual(errors, [], `${viewport.width}x${viewport.height}: erros`)
    assert.deepEqual(warnings, [], `${viewport.width}x${viewport.height}: avisos repetidos`)
  } finally {
    await context.close()
  }
}

async function verifyPrint(browser) {
  const context = await browser.newContext({ viewport: { width: 1280, height: 720 } })
  const page = await context.newPage()
  try {
    await openDiagnostic(page)
    await page.emulateMedia({ media: 'print' })
    const report = page.locator('.diagnostic-print-report')
    await report.waitFor({ state: 'visible' })
    for (const title of NEW_TITLES) {
      const card = report.locator('.diagnostic-print-indicator').filter({ hasText: title })
      assert.equal(
        await card.count(),
        0,
        `${title}: impressão legal não mistura acompanhamento ou complemento`,
      )
    }
    assert.ok(
      await report.locator('.diagnostic-print-indicator').count() > 0,
      'impressão preserva os resultados legais disponíveis',
    )
    const pdf = await page.pdf({ format: 'A4', printBackground: true })
    assert.equal(pdf.subarray(0, 4).toString(), '%PDF')
    assert.ok(pdf.length > 50_000, `PDF A4 inesperadamente pequeno: ${pdf.length}`)
  } finally {
    await context.close()
  }
}

async function verifyCyclePrint(browser) {
  const context = await browser.newContext({ viewport: { width: 1280, height: 720 } })
  const page = await context.newPage()
  try {
    await selectMunicipality(page, 'São Pedro da Serra')
    await page.goto(`${BASE_URL}/#pne2026`, { waitUntil: 'domcontentloaded' })
    await page.getByRole('heading', {
      level: 1,
      name: 'PNE 2026–2036',
    }).waitFor({ state: 'visible' })
    await page.locator('[aria-label="Resumo dos indicadores do ciclo"]').waitFor({
      state: 'visible',
    })
    await page.waitForSelector(
      'button[aria-label^="Abrir detalhe do indicador"]',
      { state: 'visible' },
    )
    assert.equal(
      await page.locator('button[aria-label^="Abrir detalhe do indicador"]').count(),
      4,
      'caso mínimo imprime apenas os quatro cards comparáveis do tema ativo',
    )

    await page.emulateMedia({ media: 'print' })
    await assertNoHorizontalOverflow(page, 'impressão A4 do ciclo')
    const printState = await page.evaluate(() => ({
      cardsAvoidBreak: Array.from(document.querySelectorAll('.cycle-page .meta-card'))
        .every((card) => getComputedStyle(card).breakInside === 'avoid'),
      contextBarHidden: getComputedStyle(document.querySelector('.context-bar')).display === 'none',
      navigationHidden: getComputedStyle(document.querySelector('.app-header')).display === 'none',
      columns: getComputedStyle(document.querySelector('.cycle-page .meta-card-grid'))
        .gridTemplateColumns.split(' ').length,
    }))
    assert.deepEqual(printState, {
      cardsAvoidBreak: true,
      contextBarHidden: true,
      navigationHidden: true,
      columns: 2,
    })

    const pdf = await page.pdf({ format: 'A4', printBackground: true })
    assert.equal(pdf.subarray(0, 4).toString(), '%PDF')
    assert.ok(pdf.length > 40_000, `PDF A4 do ciclo inesperadamente pequeno: ${pdf.length}`)
    assert.ok(
      (pdf.toString('latin1').match(/\/Type\s*\/Page\b/g) || []).length >= 1,
      'PDF A4 do ciclo sem páginas reconhecíveis',
    )
  } finally {
    await context.close()
  }
}

async function main() {
  const browser = await chromium.launch({ headless: true })
  try {
    await verifyScreen(browser, { width: 1280, height: 720 })
    await verifyScreen(browser, { width: 390, height: 844 })
    await verifyPrint(browser)
    await verifyCyclePrint(browser)
  } finally {
    await browser.close()
  }
  console.log('Macro-rodada validada em 1280×720, 390×844 e impressão A4.')
}

main().catch((error) => {
  console.error(error)
  process.exitCode = 1
})
