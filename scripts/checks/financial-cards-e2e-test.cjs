const assert = require('node:assert/strict')
const { chromium } = require('playwright')

const BASE_URL = process.env.BASE_URL ?? 'http://127.0.0.1:5173'
const MUNICIPALITY_SLUG = 'sao-lourenco-do-sul'
const VIEWPORTS = [
  { width: 1600, height: 900 },
  { width: 1024, height: 900 },
  { width: 390, height: 844 },
]
const FINANCIAL_ROUTES = [
  'financeiros-panorama',
  'financeiros-aplicacao-recursos',
  'financeiros-fundeb',
  'financeiros-vaar',
  'financeiros-pnate',
]

async function assertNoHorizontalOverflow(page, label) {
  const dimensions = await page.evaluate(() => ({
    clientWidth: document.documentElement.clientWidth,
    scrollWidth: document.documentElement.scrollWidth,
  }))
  assert.ok(
    dimensions.scrollWidth <= dimensions.clientWidth,
    label + ': overflow horizontal (' + dimensions.scrollWidth + ' > ' + dimensions.clientWidth + ')',
  )
}

async function assertKpiContract(page, label, viewport) {
  await page.locator('.financial-kpi-grid .financial-kpi-card').first().waitFor({ state: 'visible' })
  const contract = await page.evaluate(() => {
    const grid = document.querySelector('.financial-kpi-grid')
    const cards = [...grid.querySelectorAll(':scope > .financial-kpi-card')]
    const pageHeader = document.querySelector('.financial-page-header')
    const moduleSelector = document.querySelector('.financial-compact-module')
    const siblings = pageHeader && moduleSelector && pageHeader.parentElement === moduleSelector.parentElement
      ? [...pageHeader.parentElement.children]
      : []

    return {
      cardWidths: cards.map((card) => card.getBoundingClientRect().width),
      columns: getComputedStyle(grid).gridTemplateColumns.split(' ').filter((column) => column !== '0px').length,
      headerBeforeSelector: siblings.indexOf(pageHeader) < siblings.indexOf(moduleSelector),
      paddings: [...new Set(cards.map((card) => getComputedStyle(card).padding))],
    }
  })

  assert.deepEqual(contract.paddings, ['16px'], label + ': KPIs usam o padding compartilhado')
  assert.ok(contract.cardWidths.every((width) => width >= 240), label + ': nenhum KPI fica mais estreito que o mínimo')
  assert.equal(contract.headerBeforeSelector, true, label + ': cabeçalho antecede a navegação compacta')
  if (viewport.width < 700) assert.equal(contract.columns, 1, label + ': KPIs empilham no celular')
}

async function assertTypographyContract(page, label) {
  const contract = await page.evaluate(() => {
    const read = (selector) => [...document.querySelectorAll(selector)].map((node) => {
      const style = getComputedStyle(node)
      return { family: style.fontFamily, size: style.fontSize }
    })

    return {
      cardTitles: read('.financial-card h3, .platform-entry-card__title'),
      disclosureTitles: read('.platform-support-disclosure__summary h3'),
      sectionTitles: read('.financial-section-heading h2, .siope-public-section-heading h2, .pnate-section-heading h2'),
      sourceTitles: read('.financial-sources-footer h2'),
    }
  })

  assert.ok(contract.sectionTitles.every(({ family, size }) => size === '24px' && family.includes('Source Serif 4')), label + ': secoes usam a hierarquia editorial')
  assert.ok(contract.cardTitles.every(({ family, size }) => size === '16px' && family.includes('Source Sans 3')), label + ': titulos de card usam a escala compartilhada')
  assert.ok(contract.disclosureTitles.every(({ family, size }) => size === '15px' && family.includes('Source Sans 3')), label + ': disclosures usam titulo auxiliar')
  assert.ok(contract.sourceTitles.every(({ family, size }) => size === '18px' && family.includes('Source Sans 3')), label + ': fontes e metodologia usam titulo compacto')
}

async function assertPanoramaCompositeContract(page, label, viewport) {
  await page.locator('.municipal-finance-constitutional-primary-grid .financial-composite-card').first().waitFor({ state: 'visible' })
  const contract = await page.evaluate(() => {
    const measureGroup = (selector, cardSelector = '.financial-composite-card') => {
      const grid = document.querySelector(selector)
      const cards = [...grid.querySelectorAll(':scope > ' + cardSelector)]
      const gridRect = grid.getBoundingClientRect()
      return {
        cardPaddings: [...new Set(cards.map((card) => getComputedStyle(card).padding))],
        cardWidths: cards.map((card) => card.getBoundingClientRect().width),
        gridPadding: getComputedStyle(grid).padding,
        rightInset: gridRect.right - Math.max(...cards.map((card) => card.getBoundingClientRect().right)),
      }
    }

    return {
      summary: measureGroup('.municipal-finance-summary-grid', '.financial-kpi-card'),
      constitutional: measureGroup('.municipal-finance-constitutional-primary-grid'),
      fundeb: measureGroup('.municipal-finance-fundeb-overview__grid'),
      qse: measureGroup('.municipal-finance-qse-kpis', '.financial-kpi-card'),
    }
  })

  for (const [groupName, group] of Object.entries(contract)) {
    assert.deepEqual(group.cardPaddings, ['16px'], label + ': ' + groupName + ' usa padding interno uniforme')
    assert.equal(group.gridPadding, viewport.width < 700 ? '12px' : '16px', label + ': ' + groupName + ' usa o mesmo inset da grade')
    assert.ok(group.cardWidths.every((width) => width >= 240), label + ': ' + groupName + ' preserva a largura minima')
    assert.ok(Math.max(...group.cardWidths) - Math.min(...group.cardWidths) < 1, label + ': ' + groupName + ' usa cartoes de largura equivalente')
    if (viewport.width >= 1200 && groupName !== 'summary') {
      assert.ok(group.rightInset <= 17, label + ': ' + groupName + ' nao reserva uma coluna vazia')
    }
  }

  if (viewport.width < 700) {
    const mobileWidths = Object.values(contract).map((group) => group.cardWidths[0])
    assert.ok(Math.max(...mobileWidths) - Math.min(...mobileWidths) < 1, label + ': grupos equivalentes usam a mesma largura no celular')
  }

  const mdeTypography = await page.evaluate(() => {
    const read = (selector) => {
      const style = getComputedStyle(document.querySelector(selector))
      return { fontSize: style.fontSize, fontWeight: style.fontWeight, padding: style.padding }
    }
    return {
      disclosure: read('.municipal-finance-constitutional-disclosure .platform-support-disclosure__summary'),
      footer: read('.municipal-finance-constitutional-card__footer'),
      secondaryLabel: read('.municipal-finance-constitutional-card__secondary-value > span:last-child'),
      secondaryValue: read('.municipal-finance-constitutional-card__secondary-value .municipal-finance-value'),
    }
  })

  assert.deepEqual(mdeTypography.secondaryValue, { fontSize: '18px', fontWeight: '700', padding: '0px' }, label + ': valor secundario de MDE usa escala compacta')
  assert.deepEqual(mdeTypography.secondaryLabel, { fontSize: '13px', fontWeight: '400', padding: '0px' }, label + ': complemento do valor de MDE permanece auxiliar')
  assert.equal(mdeTypography.footer.fontSize, '13px', label + ': rodape do card usa escala de apoio')
  assert.equal(mdeTypography.disclosure.padding, '8px 16px', label + ': disclosure de metodologia usa inset compartilhado')
}

async function verifyViewport(browser, viewport) {
  const context = await browser.newContext({ viewport })
  const page = await context.newPage()
  const label = viewport.width + 'x' + viewport.height
  const browserErrors = []

  page.on('console', (message) => {
    if (message.type() === 'error') browserErrors.push('console: ' + message.text())
  })
  page.on('pageerror', (error) => browserErrors.push('pageerror: ' + error.message))

  try {
    for (const route of FINANCIAL_ROUTES) {
      await page.goto(BASE_URL + '/#' + route + '?municipio=' + MUNICIPALITY_SLUG, { waitUntil: 'domcontentloaded' })
      await assertKpiContract(page, route + ' ' + label, viewport)
      await assertTypographyContract(page, route + ' ' + label)
      if (route === 'financeiros-panorama') await assertPanoramaCompositeContract(page, route + ' ' + label, viewport)
      await assertNoHorizontalOverflow(page, route + ' ' + label)
    }

    await page.goto(BASE_URL + '/#financeiros?municipio=' + MUNICIPALITY_SLUG, { waitUntil: 'domcontentloaded' })
    await page.locator('.financial-module-entry-card').first().waitFor({ state: 'visible' })
    await assertTypographyContract(page, 'financeiros ' + label)
    const entryPaddings = await page.locator('.financial-module-entry-card').evaluateAll(
      (cards) => [...new Set(cards.map((card) => getComputedStyle(card).padding))],
    )
    assert.deepEqual(
      entryPaddings,
      [viewport.width < 700 ? '16px' : '20px'],
      label + ': todos os cartões de módulo usam o mesmo padding',
    )
    await assertNoHorizontalOverflow(page, 'financeiros ' + label)
    assert.deepEqual(browserErrors, [], label + ': erros no navegador')
  } finally {
    await context.close()
  }
}

async function main() {
  const browser = await chromium.launch({ headless: true })
  try {
    for (const viewport of VIEWPORTS) await verifyViewport(browser, viewport)
  } finally {
    await browser.close()
  }
  console.log('Financial UI E2E validation passed: typography, padding, minimum width, reflow and page order.')
}

main().catch((error) => {
  console.error(error)
  process.exitCode = 1
})
