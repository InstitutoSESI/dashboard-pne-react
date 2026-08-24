const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const { chromium } = require('playwright')

/*
 * Verificação de ponta a ponta dos Cenários da educação municipal.
 *
 * Exercita a política de visibilidade, a troca de município, o acesso direto
 * por URL a município não publicado, a navegação por teclado nas abas, a
 * ausência de rolagem horizontal no celular e a folha de impressão.
 */

const BASE_URL = process.env.BASE_URL ?? 'http://127.0.0.1:5173'
const SCREENSHOT_DIR = process.env.FORESIGHT_SCREENSHOT_DIR ?? null

const PUBLISHED = [
  { name: 'Nova Santa Rita', slug: 'nova-santa-rita', id: '4313375' },
  { name: 'São Leopoldo', slug: 'sao-leopoldo', id: '4318705' },
]
const UNPUBLISHED = { name: 'Muliterno', slug: 'muliterno', id: '4312625' }
const OTHER_UNPUBLISHED = { name: 'Agudo', slug: 'agudo', id: '4300109' }

const DESKTOP = { width: 1366, height: 768 }
const NOTEBOOK = { width: 1280, height: 720 }
const MOBILE = { width: 390, height: 844 }

const FORBIDDEN_TEXT = [
  /\bC[1-4]\b/,
  /\bMC-\d{3}\b/,
  /\bRP-\d{2}\b/,
  /\bF0[1-5]\b/,
  /\bNAR-\d{7}/,
  /\bTRJ-\d{7}/,
  /\bSHR-\d{7}/,
  /packageStatus/,
  /not_located/,
  /fail[_ ]closed/i,
  /em breve/i,
  /dados insuficientes/i,
  /indisponível/i,
  /\bstaging\b/i,
  /\bpipeline\b/i,
]

async function selectMunicipality(page, municipality) {
  const input = page.locator('input[role="combobox"]:visible').first()
  await input.fill(municipality)
  await page.getByRole('option', { name: municipality, exact: true }).first().click()
  await page.getByRole('button', { name: 'Limpar seleção' }).first().waitFor({ state: 'visible' })
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

/*
 * A barra lateral é fixa e o menu do celular vive fora da tela. Numa captura de
 * página inteira o Chromium reposiciona elementos fixos e o menu aparece no
 * meio do conteúdo. No celular, portanto, a captura é do que cabe na tela.
 */
async function shoot(page, name, { fullPage = true } = {}) {
  if (!SCREENSHOT_DIR) return
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true })
  await page.screenshot({ fullPage, path: path.join(SCREENSHOT_DIR, `${name}.png`) })
  process.stdout.write(`  captura: ${name}.png\n`)
}

async function scrollTo(page, selector) {
  await page.locator(selector).first().scrollIntoViewIfNeeded()
  await page.waitForTimeout(300)
}

async function openForesight(page, municipality) {
  await page.goto(`${BASE_URL}/#cenarios-da-educacao?municipio=${municipality.slug}`, {
    waitUntil: 'networkidle',
  })
  await page.getByRole('heading', { level: 1, name: 'Cenários da educação municipal' }).waitFor()
}

async function run() {
  const browser = await chromium.launch()
  const context = await browser.newContext({ viewport: DESKTOP })
  const page = await context.newPage()
  const consoleErrors = []
  page.on('console', (message) => {
    if (message.type() === 'error') consoleErrors.push(message.text())
  })

  try {
    for (const municipality of PUBLISHED) {
      await openForesight(page, municipality)

      const body = await page.locator('main').innerText()
      for (const pattern of FORBIDDEN_TEXT) {
        assert.equal(pattern.test(body), false, `${municipality.name}: "${pattern}" visível na página`)
      }

      assert.match(body, /Planejamento educacional/)
      assert.match(body, /não são previsões/)
      assert.ok(body.includes(municipality.name), `${municipality.name}: identidade municipal ausente`)
      for (const other of PUBLISHED) {
        if (other.id === municipality.id) continue
        assert.equal(body.includes(other.name), false, `${municipality.name}: nome de outro município na página`)
      }

      const cards = page.locator('.foresight-card')
      assert.equal(await cards.count(), 4, `${municipality.name}: a grade precisa ter quatro cenários`)
      const tabs = page.getByRole('tab')
      assert.equal(await tabs.count(), 4, `${municipality.name}: precisam existir quatro abas`)

      const titles = await cards.locator('.foresight-card__title').allInnerTexts()
      assert.equal(new Set(titles).size, 4, `${municipality.name}: títulos repetidos`)
      for (const title of titles) {
        assert.equal(/^\d/.test(title.trim()), false, `${municipality.name}: cenário numerado "${title}"`)
      }

      /* Peso visual igual: mesma superfície e mesma borda nos quatro cartões. */
      const styles = await cards.locator('article').evaluateAll((nodes) => nodes.map((node) => {
        const computed = getComputedStyle(node)
        return `${computed.backgroundColor}|${computed.borderColor}|${computed.borderWidth}`
      }))
      assert.equal(new Set(styles).size, 1, `${municipality.name}: um cenário recebeu destaque visual`)

      /* As condições comuns aparecem uma única vez em toda a página. */
      const sharedItems = await page
        .locator('#cenarios-condicoes-comuns')
        .locator('xpath=../..')
        .locator('.foresight-list > li')
        .allInnerTexts()
      assert.ok(sharedItems.length > 0)
      for (const item of sharedItems) {
        const occurrences = body.split(item.trim()).length - 1
        assert.equal(occurrences, 1, `${municipality.name}: condição comum repetida na página`)
      }

      /* Fontes ao final: a última seção da página é a de fontes e metodologia. */
      const sectionIds = await page.locator('main section[aria-labelledby]').evaluateAll(
        (nodes) => nodes.map((node) => node.getAttribute('aria-labelledby')),
      )
      assert.equal(sectionIds.at(-1), 'cenarios-fontes', `${municipality.name}: fontes fora do final`)

      /* Séries observadas: valores concretos, com período e direção declarados. */
      const series = page.locator('.foresight-serie')
      const seriesCount = await series.count()
      assert.ok(seriesCount >= 3, `${municipality.name}: poucas séries observadas (${seriesCount})`)
      const windows = await page.locator('.foresight-window__values').allInnerTexts()
      assert.ok(windows.length >= seriesCount, `${municipality.name}: janelas observadas ausentes`)
      for (const window of windows) {
        assert.match(
          window,
          /(alta|queda|estabilidade|oscilação|sem direção única) no período/,
          `${municipality.name}: janela sem direção declarada`,
        )
      }
      const periods = await page.locator('.foresight-window__period').allInnerTexts()
      for (const period of periods) {
        const years = [...period.matchAll(/\b(20\d{2})\b/g)].map((match) => Number(match[1]))
        assert.ok(years.length > 0, `${municipality.name}: período sem ano`)
        for (const year of years) {
          assert.ok(year <= 2026, `${municipality.name}: período com ano futuro (${year})`)
        }
      }

      /* Comparação: uma coluna por cenário, todas com a mesma largura. */
      const comparisonHeaders = await page.locator('.foresight-comparison__scenario').allInnerTexts()
      assert.deepEqual(comparisonHeaders, titles, `${municipality.name}: comparação fora dos cenários publicados`)
      const columnWidths = await page.locator('.foresight-comparison__scenario').evaluateAll(
        (nodes) => nodes.map((node) => Math.round(node.getBoundingClientRect().width)),
      )
      assert.equal(new Set(columnWidths).size, 1, `${municipality.name}: colunas de larguras diferentes`)

      /* Sinais consolidados aparecem uma vez, na sua própria seção. */
      const signals = await page.locator('#cenarios-sinais').locator('xpath=../..').locator('.foresight-list > li').allInnerTexts()
      assert.ok(signals.length > 0, `${municipality.name}: sem sinais consolidados`)
      assert.equal(new Set(signals).size, signals.length, `${municipality.name}: sinal repetido`)

      /* Hierarquia de títulos: um h1, seções em h2, subseções em h3/h4. */
      const headingLevels = await page.locator('main h1, main h2, main h3, main h4').evaluateAll(
        (nodes) => nodes.map((node) => Number(node.tagName.slice(1))),
      )
      assert.equal(headingLevels.filter((level) => level === 1).length, 1, `${municipality.name}: h1 único`)
      let previous = 1
      for (const level of headingLevels) {
        assert.ok(level - previous <= 1, `${municipality.name}: salto de heading ${previous} -> ${level}`)
        previous = level
      }
    }

    /* Detalhe: abrir um cenário e navegar as abas pelo teclado. */
    await openForesight(page, PUBLISHED[0])
    const exploreButtons = page.getByRole('button', { name: /Explorar cenário/ })
    await exploreButtons.nth(2).click()
    const selectedTab = page.getByRole('tab', { selected: true })
    const openedTitle = await selectedTab.innerText()
    assert.equal(openedTitle, (await page.locator('.foresight-card__title').allInnerTexts())[2])
    assert.equal(await page.evaluate(() => document.activeElement?.getAttribute('role')), 'tab')

    await page.keyboard.press('ArrowRight')
    const afterArrow = await page.getByRole('tab', { selected: true }).innerText()
    assert.notEqual(afterArrow, openedTitle, 'a seta deveria trocar a aba ativa')
    await page.keyboard.press('Home')
    const afterHome = await page.getByRole('tab', { selected: true }).innerText()
    assert.equal(afterHome, (await page.locator('.foresight-card__title').allInnerTexts())[0])

    const panel = page.getByRole('tabpanel')
    assert.equal(await panel.count(), 1, 'exatamente um painel de cenário fica visível')
    const panelText = await panel.innerText()
    assert.match(panelText, /De onde o município parte/)
    assert.match(panelText, /O que acompanhar/)

    /* Troca de município pela barra de contexto, sem vazamento entre pacotes. */
    await selectMunicipality(page, PUBLISHED[1].name)
    await page.getByRole('heading', { level: 1, name: 'Cenários da educação municipal' }).waitFor()
    const afterSwitch = await page.locator('main').innerText()
    assert.ok(afterSwitch.includes(PUBLISHED[1].name))
    assert.equal(afterSwitch.includes(PUBLISHED[0].name), false, 'município anterior vazou após a troca')

    await selectMunicipality(page, PUBLISHED[0].name)
    const afterReturn = await page.locator('main').innerText()
    assert.ok(afterReturn.includes(PUBLISHED[0].name))
    assert.equal(afterReturn.includes(PUBLISHED[1].name), false, 'município anterior vazou ao voltar')

    /* Visibilidade da navegação: só o município publicado exibe a entrada. */
    const navEntry = page.getByRole('link', { name: 'Cenários da educação' })
    assert.equal(await navEntry.count(), 1, 'a entrada precisa existir para município publicado')

    for (const hidden of [UNPUBLISHED, OTHER_UNPUBLISHED]) {
      await page.goto(`${BASE_URL}/#diagnostico?municipio=${hidden.slug}`, { waitUntil: 'networkidle' })
      await page.waitForTimeout(400)
      assert.equal(
        await page.getByRole('link', { name: 'Cenários da educação' }).count(),
        0,
        `${hidden.name}: a entrada não pode aparecer`,
      )
      const sidebar = await page.locator('.app-header').innerText()
      assert.equal(/Cenários da educação/.test(sidebar), false, `${hidden.name}: entrada visível na barra lateral`)
    }

    /* Acesso direto por URL a município não publicado sai da rota. */
    for (const hidden of [UNPUBLISHED, OTHER_UNPUBLISHED]) {
      await page.goto(`${BASE_URL}/#cenarios-da-educacao?municipio=${hidden.slug}`, { waitUntil: 'networkidle' })
      await page.waitForFunction(() => !window.location.hash.includes('cenarios-da-educacao'), null, { timeout: 5000 })
      assert.match(page.url(), /#diagnostico/, `${hidden.name}: deveria voltar ao diagnóstico municipal`)
      const redirected = await page.locator('main').innerText()
      assert.equal(
        /Cenários da educação municipal/.test(redirected),
        false,
        `${hidden.name}: a página de cenários não pode ser montada`,
      )
      for (const published of PUBLISHED) {
        assert.equal(
          redirected.includes(published.name),
          false,
          `${hidden.name}: dado de município publicado apareceu após o redirecionamento`,
        )
      }
    }

    /* Celular: sem rolagem horizontal, coluna única. */
    await page.setViewportSize(MOBILE)
    await openForesight(page, PUBLISHED[0])
    await assertNoHorizontalOverflow(page, 'mobile 390x844')
    const columns = await page.locator('.foresight-grid').evaluate(
      (node) => getComputedStyle(node).gridTemplateColumns.split(' ').length,
    )
    assert.equal(columns, 1, 'no celular a grade precisa ser de coluna única')

    await page.setViewportSize(NOTEBOOK)
    await openForesight(page, PUBLISHED[0])
    await assertNoHorizontalOverflow(page, 'notebook 1280x720')

    await page.setViewportSize(DESKTOP)
    await openForesight(page, PUBLISHED[0])
    await assertNoHorizontalOverflow(page, 'desktop 1366x768')
    const desktopColumns = await page.locator('.foresight-grid').evaluate(
      (node) => getComputedStyle(node).gridTemplateColumns.split(' ').length,
    )
    assert.equal(desktopColumns, 2, 'no desktop a grade precisa ser 2 x 2')

    /* Impressão: sem controles de navegação e sem barra lateral. */
    await page.emulateMedia({ media: 'print' })
    const hiddenOnPrint = await page.evaluate(() => {
      const action = document.querySelector('.foresight-card__action')
      const tabs = document.querySelector('.foresight-tabs')
      return {
        action: action ? getComputedStyle(action).display : 'missing',
        tabs: tabs ? getComputedStyle(tabs).display : 'missing',
      }
    })
    assert.equal(hiddenOnPrint.action, 'none', 'a ação do cartão precisa sumir na impressão')
    assert.equal(hiddenOnPrint.tabs, 'none', 'as abas precisam sumir na impressão')
    const printedText = await page.locator('main').innerText()
    assert.match(printedText, /Fontes e metodologia/)
    await page.emulateMedia({ media: 'screen' })

    assert.deepEqual(consoleErrors, [], `erros de console: ${consoleErrors.join(' | ')}`)

    /* Capturas para conferência visual, quando pedidas. */
    if (SCREENSHOT_DIR) {
      await page.setViewportSize(DESKTOP)
      await openForesight(page, PUBLISHED[0])
      await shoot(page, 'nova-santa-rita-desktop-1366x768')
      await page.getByRole('button', { name: /Explorar cenário/ }).nth(1).click()
      await page.waitForTimeout(600)
      await shoot(page, 'nova-santa-rita-desktop-cenario-aberto')

      await page.setViewportSize(NOTEBOOK)
      await openForesight(page, PUBLISHED[0])
      await shoot(page, 'nova-santa-rita-notebook-1280x720')

      await page.setViewportSize(MOBILE)
      await openForesight(page, PUBLISHED[0])
      await shoot(page, 'nova-santa-rita-mobile-390x844', { fullPage: false })
      await scrollTo(page, '#cenarios-entrada')
      await shoot(page, 'nova-santa-rita-mobile-390x844-cenarios', { fullPage: false })

      await page.setViewportSize(DESKTOP)
      await openForesight(page, PUBLISHED[1])
      await shoot(page, 'sao-leopoldo-desktop-1366x768')
      await page.getByRole('button', { name: /Explorar cenário/ }).nth(3).click()
      await page.waitForTimeout(600)
      await shoot(page, 'sao-leopoldo-desktop-cenario-aberto')
    }

    process.stdout.write('Cenários da educação: verificação de ponta a ponta aprovada.\n')
  } finally {
    await context.close()
    await browser.close()
  }
}

run().catch((error) => {
  process.exitCode = 1
  process.stderr.write(`${error?.stack ?? error}\n`)
})
