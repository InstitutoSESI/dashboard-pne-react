const assert = require('node:assert/strict')
const path = require('node:path')
const { pathToFileURL } = require('node:url')
const { chromium } = require('playwright')

const repoRoot = path.resolve(__dirname, '..', '..')
const providedBaseUrl = process.env.BASE_URL
const port = Number(process.env.VOCACOES_LAYOUT_PORT ?? 5197)
const baseUrl = providedBaseUrl ?? `http://127.0.0.1:${port}`
const viewport = { width: 1440, height: 900 }
const screenshotPath = process.env.VOCACOES_LAYOUT_SCREENSHOT

async function startLocalServer() {
  if (providedBaseUrl !== undefined) return null
  const runStateViteUrl = pathToFileURL(path.join(repoRoot, 'scripts', 'run-state-vite.mjs')).href
  const { parseStateViteArguments } = await import(runStateViteUrl)
  const { stateCode } = parseStateViteArguments(['serve', 'RS'])
  process.env.PLATFORM_STATE = stateCode
  const { createServer } = await import('vite')
  const server = await createServer({
    optimizeDeps: {
      include: ['react', 'react-dom/client'],
      noDiscovery: true,
    },
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

async function measure() {
  const server = await startLocalServer()
  let browser
  try {
    browser = await chromium.launch({ headless: true })
    const context = await browser.newContext({ viewport })
    const page = await context.newPage()
    page.setDefaultTimeout(60_000)
    page.setDefaultNavigationTimeout(90_000)

    await page.goto(
      `${baseUrl}/#vocacoes-da-regiao?municipio=nova-santa-rita`,
      { timeout: 90_000, waitUntil: 'domcontentloaded' },
    )
    await page.locator('.vocacoes-hero').waitFor({ state: 'visible' })
    await page.evaluate(() => document.fonts.ready)

    const metrics = await page.evaluate(() => {
      const root = document.querySelector('.vocacoes-page')
      if (!(root instanceof HTMLElement)) throw new Error('.vocacoes-page não encontrada')

      const panelSelector = [
        '.vocacoes-relation-card',
        '.vocacoes-e2-card',
        '.vocacoes-screened-row',
        '.vocacoes-hero-tile',
        '.vocacoes-hero__copy',
        '.vocacoes-evidence-ladder',
        '.vocacoes-section__head',
        '.vocacoes-scenarios__absence',
        '.vocacoes-consultation',
        '.vocacoes-footer__panel',
        '.vocacoes-panel',
        '.vocacoes-section',
        '.vocacoes-hero',
      ].join(',')
      const ratios = [...root.querySelectorAll('p')]
        .filter((paragraph) => {
          const rect = paragraph.getBoundingClientRect()
          const style = getComputedStyle(paragraph)
          return (paragraph.textContent?.trim().length ?? 0) >= 80
            && rect.width > 0
            && rect.height > 0
            && style.display !== 'none'
            && style.visibility !== 'hidden'
        })
        .map((paragraph) => {
          const panel = paragraph.closest(panelSelector)
          if (!(panel instanceof HTMLElement)) return 0
          const style = getComputedStyle(panel)
          const contentWidth = panel.clientWidth
            - Number.parseFloat(style.paddingLeft)
            - Number.parseFloat(style.paddingRight)
          return contentWidth > 0 ? paragraph.getBoundingClientRect().width / contentWidth : 0
        })
        .sort((left, right) => left - right)
      const middle = Math.floor(ratios.length / 2)
      const medianTextRatio = ratios.length === 0
        ? 0
        : ratios.length % 2 === 0
          ? (ratios[middle - 1] + ratios[middle]) / 2
          : ratios[middle]

      const cards = [...root.querySelectorAll('.vocacoes-relations-grid > .vocacoes-relation-card')]
      const columns = new Set(cards.map((card) => Math.round(card.getBoundingClientRect().left))).size

      return {
        columns,
        height: root.getBoundingClientRect().height,
        medianTextRatio,
        paragraphCount: ratios.length,
      }
    })

    const measured = `altura=${metrics.height.toFixed(1)}px; mediana=${metrics.medianTextRatio.toFixed(3)}; colunas=${metrics.columns}; parágrafos=${metrics.paragraphCount}`
    console.log(`Vocações layout 1440×900: ${measured}`)
    assert.ok(metrics.height <= 7000, `altura máxima excedida: ${measured}`)
    assert.ok(metrics.medianTextRatio >= 0.60, `mediana de texto abaixo da meta: ${measured}`)
    assert.ok(metrics.columns >= 2, `grade P1 sem duas colunas: ${measured}`)
    if (screenshotPath !== undefined) {
      await page.screenshot({ fullPage: true, path: screenshotPath })
    }
    await context.close()
  } finally {
    if (browser !== undefined) await browser.close()
    if (server !== null) await server.close()
  }
}

measure().catch((error) => {
  console.error(error instanceof Error ? error.stack : String(error))
  process.exitCode = 1
})
