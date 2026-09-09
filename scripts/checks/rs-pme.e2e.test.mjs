import assert from 'node:assert/strict'
import { execFileSync, spawn } from 'node:child_process'
import { createWriteStream } from 'node:fs'
import { mkdir, readFile } from 'node:fs/promises'
import path from 'node:path'
import test, { after, before } from 'node:test'
import { fileURLToPath } from 'node:url'
import { unzipSync } from 'fflate'
import { chromium } from 'playwright'

const root = fileURLToPath(new URL('../..', import.meta.url))
const evidenceDirectory = path.join(root, '.tmp', 'rs-pme')
const defaultBaseUrl = process.env.PME_E2E_BASE_URL || 'http://127.0.0.1:5189'
let baseUrl = defaultBaseUrl
let browser
let managedServer

async function isAvailable(url) {
  try { return (await fetch(url)).ok } catch { return false }
}

async function waitForServer(url, timeoutMs = 20_000) {
  const startedAt = Date.now()
  while (Date.now() - startedAt < timeoutMs) {
    if (await isAvailable(url)) return
    await new Promise((resolve) => setTimeout(resolve, 200))
  }
  throw new Error(`O servidor PME não iniciou em ${url}.`)
}

async function pageFor(viewport = { width: 1440, height: 900 }) {
  const context = await browser.newContext({ viewport })
  const page = await context.newPage()
  return { context, page, network: observeNetwork(page) }
}

function observeNetwork(page) {
  const requests = []
  const pageErrors = []
  page.on('request', (request) => requests.push({ url: request.url(), method: request.method() }))
  page.on('pageerror', (error) => pageErrors.push(error.message))
  return { requests, pageErrors }
}

function requestedMunicipalityIds(requests) {
  return requests.flatMap(({ url }) => {
    const match = new URL(url).pathname.match(/\/municipios\/(\d{7})(?:\/|\.json)/)
    return match ? [match[1]] : []
  })
}

async function assertHealthyPage(page, network, selectedIds) {
  assert.deepEqual(network.pageErrors, [], `erros de página: ${network.pageErrors.join('\n')}`)
  const failedFonts = await page.evaluate(async () => {
    await document.fonts.ready
    return [...document.fonts].filter((font) => font.status === 'error').map((font) => font.family)
  })
  assert.deepEqual(failedFonts, [], `fontes não carregadas: ${failedFonts.join(', ')}`)
  assert.equal(await page.locator('input[type="file"]').count(), 0, 'a consulta PME não aceita anexos locais')
  const allowedOrigin = new URL(baseUrl).origin
  for (const request of network.requests) {
    assert.equal(new URL(request.url).origin, allowedOrigin, `requisição externa inesperada: ${request.url}`)
    assert.equal(request.method, 'GET', `requisição não somente leitura inesperada: ${request.method} ${request.url}`)
  }
  const municipalityIds = requestedMunicipalityIds(network.requests)
  assert.ok(municipalityIds.length > 0, 'a leitura municipal deve solicitar documentos municipais')
  assert.ok(municipalityIds.every((id) => selectedIds.includes(id)), `requisição municipal fora da seleção: ${municipalityIds.join(', ')}`)
}

async function waitForMunicipalPage(page, heading, exact = false) {
  await page.getByRole('heading', { name: heading, exact }).waitFor({ state: 'visible', timeout: 15_000 })
}

async function waitForReadyExport(page) {
  const exportButton = page.getByRole('button', { name: 'Baixar XLSX' })
  await exportButton.waitFor({ state: 'visible', timeout: 15_000 })
  await page.waitForFunction(() => [...document.querySelectorAll('button')]
    .some((button) => button.textContent?.includes('Baixar XLSX') && !button.disabled), undefined, { timeout: 15_000 })
  await page.getByRole('button', { name: 'Imprimir / salvar PDF' }).waitFor({ state: 'visible', timeout: 15_000 })
  await page.waitForFunction(() => [...document.querySelectorAll('button')]
    .some((button) => button.textContent?.includes('Imprimir / salvar PDF') && !button.disabled), undefined, { timeout: 15_000 })
  await page.locator('.pme-report table').first().waitFor({ state: 'visible', timeout: 15_000 })
}

async function waitForObservedCount(page, expected) {
  await page.waitForFunction((count) => {
    const counts = document.querySelector('.pme-counts')?.textContent || ''
    return new RegExp(`Leituras com dados\\s*${count}`).test(counts)
      && !document.querySelector('.pme-module-states [role="status"]')
  }, expected, { timeout: 15_000 })
}

async function assertDiagnosticCountPending(page) {
  const counts = await page.locator('.pme-counts').innerText()
  assert.match(counts, /Leituras com dados\s*—/)
  assert.doesNotMatch(counts, /Leituras com dados\s*0/)
}

async function waitForObjectiveObservedCount(page, expected) {
  await page.waitForFunction((count) => {
    const counts = document.querySelector('.pme-counts')?.textContent || ''
    return new RegExp(`Leituras com dados\\s*${count}`).test(counts)
      && !document.querySelector('.pme-module-states [role="status"]')
  }, expected, { timeout: 15_000 })
}

function noGlobalHorizontalOverflow(page) {
  return page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)
}

async function savePdfWithTableReview(page, fileName, requiredText) {
  await waitForReadyExport(page)
  const output = path.join(evidenceDirectory, fileName)
  const tableCount = await page.locator('.pme-report table').count()
  assert.ok(tableCount > 0, 'o material deve expor tabelas depois de pronto e antes do PDF')
  await page.pdf({ path: output, format: 'A4', printBackground: true })
  const pdf = await readFile(output)
  assert.equal(pdf.subarray(0, 4).toString('utf8'), '%PDF')
  assert.ok(pdf.length > 4_000, 'o PDF precisa conter conteúdo além do cabeçalho')
  try {
    const text = execFileSync('pdftotext', [output, '-'], { encoding: 'utf8', windowsHide: true })
    assert.match(text, requiredText)
  } catch (error) {
    if (error?.code !== 'ENOENT') throw error
  }
}

async function downloadWorkbook(page, outputName) {
  await waitForReadyExport(page)
  const [download] = await Promise.all([
    page.waitForEvent('download'),
    page.getByRole('button', { name: 'Baixar XLSX' }).click(),
  ])
  const output = path.join(evidenceDirectory, outputName)
  await download.saveAs(output)
  const workbook = await readFile(output)
  assert.equal(workbook.subarray(0, 2).toString('utf8'), 'PK', 'XLSX deve ser um arquivo ZIP')
  return { output, entries: unzipSync(workbook) }
}

function assertWorkbookStructure(entries, outputName) {
  const xmlNames = Object.keys(entries).filter((entry) => entry.endsWith('.xml'))
  const sheets = xmlNames.filter((entry) => /^xl\/worksheets\/sheet\d+\.xml$/.test(entry))
  assert.equal(sheets.length, 8, `${outputName} deve manter as oito planilhas do contrato`)
  const workbookXml = new TextDecoder().decode(entries['xl/workbook.xml'])
  const sharedStrings = new TextDecoder().decode(entries['xl/sharedStrings.xml'])
  for (const tab of ['Leitura do material', 'Metas e cobertura', 'Evidências', 'Agenda', 'Instrumentos', 'Método e leituras', 'Fontes', 'Séries anuais de apoio']) {
    assert.match(workbookXml, new RegExp(`name="${tab}"`), `${outputName} deve manter a aba “${tab}”`)
  }
  assert.match(sharedStrings, /4313375/, `${outputName} deve preservar o IBGE textual`)
  for (const sheet of sheets) {
    const xml = new TextDecoder().decode(entries[sheet])
    assert.match(xml, /<row\b/, `${outputName}: ${sheet} deve conter linhas`)
    assert.doesNotMatch(xml, /<f[ >]/, `${outputName}: não deve criar fórmulas`)
  }
}

async function assertNoInternalText(page, pageName) {
  const visibleText = await page.locator('.pme-main').innerText()
  assert.doesNotMatch(visibleText, /(?:\/data\/|sha-?256|\brelease\b|\bschema\b|\bsourceid\b|pne2026|diagnostic-v\d|mat_infantil_pre|pre_escola|\bcobrade\b|\bdisaster(?:group|type|typecode)\b|\bprotocols2id\b|\brecognitionstatus\b)/i, `${pageName}: detalhe interno não deve ser texto visível`)
}

async function screenshotViewport(page, fileName) {
  await page.screenshot({ path: path.join(evidenceDirectory, fileName), fullPage: false })
}

before(async () => {
  await mkdir(evidenceDirectory, { recursive: true })
  if (!await isAvailable(baseUrl)) {
    const port = 5197
    baseUrl = `http://127.0.0.1:${port}`
    const output = path.join(evidenceDirectory, 'dev-server.log')
    managedServer = spawn(process.execPath, ['scripts/run-state-vite.mjs', 'serve', 'RS', 'pme', '--host', '127.0.0.1', '--port', String(port), '--strictPort'], { cwd: root, stdio: ['ignore', 'pipe', 'pipe'], windowsHide: true })
    managedServer.stdout.pipe(createWriteStream(output, { flags: 'a' }))
    managedServer.stderr.pipe(createWriteStream(output, { flags: 'a' }))
    await waitForServer(baseUrl)
  }
  browser = await chromium.launch({ headless: true })
})

after(async () => {
  await browser?.close()
  if (managedServer && !managedServer.killed) managedServer.kill()
})

test('home apresenta a plataforma; 19 objetivos, 73 metas e links diretos preservam contexto', async () => {
  const { context, page, network } = await pageFor()
  try {
    await page.goto(`${baseUrl}/`, { waitUntil: 'domcontentloaded' })
    await page.getByRole('heading', { name: 'Evidências para planejar a educação municipal' }).waitFor()
    assert.match(await page.locator('.pme-main').innerText(), /73 metas/)
    assert.equal(requestedMunicipalityIds(network.requests).length, 0, 'a apresentação não busca dados municipais sem seleção')
    await page.getByRole('button', { name: 'Selecionar município', exact: true }).click()
    assert.equal(await page.getByRole('combobox', { name: 'Município' }).evaluate((element) => element === document.activeElement), true)
    await page.keyboard.press('Escape')
    assert.equal(await page.getByRole('combobox', { name: 'Município' }).getAttribute('aria-expanded'), 'false')
    await page.getByRole('link', { name: 'Conhecer os objetivos do PNE' }).click()
    await page.getByRole('heading', { name: 'Panorama dos 19 objetivos' }).waitFor()
    assert.equal(await page.locator('.pme-objective-card').count(), 19)
    await page.locator('.pme-objective-card').first().click()
    await waitForMunicipalPage(page, /Objetivo 1 — Educação infantil/)
    await page.goBack({ waitUntil: 'domcontentloaded' })
    await page.getByRole('heading', { name: 'Panorama dos 19 objetivos' }).waitFor()
    await page.goto(`${baseUrl}/#objetivo?municipio=4313375&objetivo=1&disponibilidade=observadas`, { waitUntil: 'domcontentloaded' })
    await waitForMunicipalPage(page, /Objetivo 1 — Educação infantil/)
    await page.reload({ waitUntil: 'domcontentloaded' })
    await waitForMunicipalPage(page, /Objetivo 1 — Educação infantil/)
    await page.goBack({ waitUntil: 'domcontentloaded' })
    await page.goForward({ waitUntil: 'domcontentloaded' })
    await waitForMunicipalPage(page, /Objetivo 1 — Educação infantil/)
    assert.match(page.url(), /municipio=4313375.*objetivo=1.*disponibilidade=observadas/)
    await page.getByRole('link', { name: 'Início', exact: true }).click()
    await page.getByRole('heading', { name: 'Evidências para planejar a educação municipal' }).waitFor()
    assert.match(page.url(), /#apresentacao\?municipio=4313375/)
    assert.match(await page.locator('.pme-introduction-start').innerText(), /Nova Santa Rita/)
    await page.getByRole('link', { name: 'Ver panorama municipal', exact: true }).click()
    await waitForMunicipalPage(page, /Panorama de Nova Santa Rita/)
    await assertHealthyPage(page, network, ['4313375'])
  } finally { await context.close() }
})

test('seletor por teclado e troca rápida não misturam requisições ou observações municipais', async () => {
  const { context, page, network } = await pageFor()
  try {
    let releaseDelayedNova
    await page.route('**/data/pne2026-diagnostic-v3/releases/*/municipios/4313375.json', async (route) => {
      releaseDelayedNova = new Promise((resolve) => setTimeout(resolve, 3_000))
      await releaseDelayedNova
      await route.continue()
    })
    await page.goto(`${baseUrl}/`, { waitUntil: 'domcontentloaded' })
    await page.locator('.pme-skip-link').waitFor({ state: 'visible', timeout: 15_000 })
    await page.keyboard.press('Tab')
    assert.equal(await page.locator(':focus').getAttribute('class'), 'pme-skip-link')
    await page.keyboard.press('Enter')
    assert.equal(await page.locator(':focus').getAttribute('id'), 'pme-main')
    const selector = page.getByRole('combobox', { name: 'Município' })
    await selector.fill('Nova Santa Rita')
    await page.getByRole('option', { name: /Nova Santa Rita/ }).click()
    await page.getByRole('heading', { name: /Panorama de Nova Santa Rita/ }).waitFor({ timeout: 15_000 })
    assert.match(page.url(), /#inicio\?municipio=4313375/)
    await assertDiagnosticCountPending(page)
    network.requests.length = 0
    await selector.fill('Porto Alegre')
    await page.getByRole('option', { name: /Porto Alegre/ }).click()
    await waitForMunicipalPage(page, /Panorama de Porto Alegre/)
    await releaseDelayedNova
    await page.waitForTimeout(250)
    assert.match(await page.locator('.pme-main h1').innerText(), /Porto Alegre/)
    assert.doesNotMatch(await page.locator('.pme-main').innerText(), /Panorama de Nova Santa Rita/)
    await waitForObservedCount(page, 49)
    assert.ok(requestedMunicipalityIds(network.requests).includes('4314902'), 'a troca deve buscar Porto Alegre')
    await selector.fill('Nova Santa Rita')
    await page.getByRole('option', { name: /Nova Santa Rita/ }).click()
    await waitForMunicipalPage(page, /Panorama de Nova Santa Rita/)
    await waitForObservedCount(page, 41)
    await assertHealthyPage(page, network, ['4313375', '4314902'])
  } finally { await context.close() }
})

test('Matriz lenta não oculta observações; ausência e erro de Matriz permanecem distintos e Agenda acessível', async () => {
  const slow = await pageFor()
  try {
    await slow.page.route('**/data/pne2026-matriz/municipios/4313375.json', async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 2_000))
      await route.continue()
    })
    await slow.page.goto(`${baseUrl}/#objetivo?municipio=4313375&objetivo=1`, { waitUntil: 'domcontentloaded' })
    await slow.page.getByText('Consultando os dados de apoio à discussão…').waitFor({ timeout: 15_000 })
    const observedValue = slow.page.locator('.pme-evidence__metric strong').filter({ hasText: /\d/ }).first()
    await observedValue.waitFor({ state: 'visible', timeout: 15_000 })
    assert.match(await observedValue.innerText(), /\d/)
    await assertHealthyPage(slow.page, slow.network, ['4313375'])
  } finally { await slow.context.close() }

  const absent = await pageFor()
  try {
    await absent.page.route('**/data/pne2026-matriz/manifest.json', async (route) => {
      const response = await route.fetch()
      const manifest = await response.json()
      manifest.municipalities = manifest.municipalities.filter((entry) => entry.ibge7 !== '4313375')
      await route.fulfill({ response, json: manifest })
    })
    await absent.page.goto(`${baseUrl}/#agenda?municipio=4313375`, { waitUntil: 'domcontentloaded' })
    await absent.page.getByText('Os dados de apoio da Matriz ainda não foram publicados para este município. Os indicadores disponíveis continuam acessíveis.').waitFor({ timeout: 15_000 })
    await waitForMunicipalPage(absent.page, /Agenda de Análise de Nova Santa Rita/)
    await assertHealthyPage(absent.page, absent.network, ['4313375'])
  } finally { await absent.context.close() }

  const invalid = await pageFor()
  try {
    await invalid.page.route('**/data/pne2026-matriz/municipios/4313375.json', async (route) => {
      const response = await route.fetch()
      const fixture = await response.json()
      fixture.municipality.ibge7 = '4314902'
      await route.fulfill({ response, json: fixture })
    })
    await invalid.page.goto(`${baseUrl}/#agenda?municipio=4313375`, { waitUntil: 'domcontentloaded' })
    await invalid.page.getByRole('heading', { name: 'Não foi possível carregar os dados de apoio' }).waitFor({ timeout: 15_000 })
    await waitForMunicipalPage(invalid.page, /Agenda de Análise de Nova Santa Rita/)
    await assertHealthyPage(invalid.page, invalid.network, ['4313375'])
  } finally { await invalid.context.close() }
})

test('diagnóstico com erro conserva as perguntas e contextos da Matriz na ficha', async () => {
  const { context, page, network } = await pageFor()
  try {
    let matrizQuestion = null
    await page.route('**/data/pne2026-diagnostic-v3/releases/*/municipios/4313375.json', (route) => route.fulfill({ status: 500, contentType: 'application/json', body: '{}' }))
    await page.route('**/data/pne2026-matriz/municipios/4313375.json', async (route) => {
      const response = await route.fetch()
      const fixture = await response.json()
      const goal = fixture.priorityGoals.find((item) => item.goalId.startsWith('1.'))
      matrizQuestion = goal?.causes?.flatMap((cause) => cause.workshopQuestions)[0] || null
      await route.fulfill({ response, json: fixture })
    })
    await page.goto(`${baseUrl}/#inicio?municipio=4313375`, { waitUntil: 'domcontentloaded' })
    await page.getByRole('heading', { name: /Panorama de Nova Santa Rita/ }).waitFor({ timeout: 15_000 })
    await assertDiagnosticCountPending(page)
    await page.goto(`${baseUrl}/#objetivo?municipio=4313375&objetivo=1`, { waitUntil: 'domcontentloaded' })
    await page.getByRole('heading', { name: 'Não foi possível carregar o diagnóstico' }).waitFor({ timeout: 15_000 })
    await page.getByRole('heading', { name: /Objetivo 1 — Educação infantil/ }).waitFor({ timeout: 15_000 })
    assert.ok(matrizQuestion, 'a fixture da Matriz deve fornecer uma pergunta para o objetivo 1')
    const displayedQuestion = matrizQuestion === 'rota/tempo/km/dias sem serviço' ? 'Verificar rotas, tempos, distâncias e dias sem transporte escolar.' : matrizQuestion
    await page.getByText(displayedQuestion, { exact: true }).first().waitFor({ timeout: 15_000 })
    await page.getByRole('heading', { name: 'Questões para a discussão municipal' }).waitFor()
    await assertHealthyPage(page, network, ['4313375'])
  } finally { await context.close() }
})

test('fichas, agenda, financiamento, relatórios e relatório técnico mantêm IBGE e dados prontos', async () => {
  const { context, page, network } = await pageFor()
  try {
    await page.goto(`${baseUrl}/#objetivo?municipio=4313375&objetivo=1`, { waitUntil: 'domcontentloaded' })
    await waitForMunicipalPage(page, /Objetivo 1 — Educação infantil/)
    await waitForObjectiveObservedCount(page, 2)
    const firstEvidence = page.locator('.pme-evidence').first()
    await firstEvidence.locator('summary').click()
    await firstEvidence.getByRole('heading', { name: 'Como ler esta evidência' }).waitFor({ state: 'visible' })
    await screenshotViewport(page, 'ficha-details-1440.png')
    await page.getByRole('link', { name: 'Ver situações na Agenda' }).click()
    await waitForMunicipalPage(page, /Agenda de Análise de Nova Santa Rita/)
    await page.getByRole('link', { name: 'Consultar os 19 objetivos' }).click()
    await waitForMunicipalPage(page, /Panorama dos 19 objetivos/)
    await page.goto(`${baseUrl}/#financiamento?municipio=4313375&objetivo=1`, { waitUntil: 'domcontentloaded' })
    await page.getByRole('heading', { name: /Financiamento em Nova Santa Rita/ }).waitFor({ timeout: 15_000 })
    await page.locator('.pme-finance-values .pme-finance-value').first().waitFor({ state: 'visible', timeout: 15_000 })
    assert.match(await page.locator('.pme-finance-values').innerText(), /R\$|%|Indisponível|Não aplicável/)
    assert.match(await page.getByRole('link', { name: /Objetivo 1/ }).first().getAttribute('href'), /municipio=4313375.*objetivo=1/)
    await screenshotViewport(page, 'financiamento-1440.png')
    await page.goto(`${baseUrl}/#relatorios?municipio=4313375&relatorio=sintese`, { waitUntil: 'domcontentloaded' })
    await waitForReadyExport(page)
    await page.getByRole('link', { name: 'Abrir Relatório Técnico Municipal' }).click()
    await page.getByRole('heading', { name: 'Relatório Técnico Municipal', exact: true }).waitFor({ timeout: 15_000 })
    const scenarioLink = page.getByRole('link', { name: /Abrir Cenários de atendimento escolar/ })
    await scenarioLink.waitFor({ timeout: 15_000 })
    assert.match(await scenarioLink.getAttribute('href'), /^#evidencias\?municipio=4313375/)
    await screenshotViewport(page, 'relatorio-tecnico-1440.png')
    await assertHealthyPage(page, network, ['4313375'])
  } finally { await context.close() }
})

test('três materiais prontos baixam XLSX reais e caderno/agenda geram PDFs com observações e histórico', async () => {
  const { context, page, network } = await pageFor({ width: 1440, height: 900 })
  try {
    for (const [kind, objectiveId, output] of [['sintese', null, 'sintese.xlsx'], ['caderno', '1', 'caderno.xlsx'], ['agenda', null, 'agenda.xlsx']]) {
      const query = new URLSearchParams({ municipio: '4313375', relatorio: kind })
      if (objectiveId) query.set('objetivo', objectiveId)
      await page.goto(`${baseUrl}/#relatorios?${query}`, { waitUntil: 'domcontentloaded' })
      const workbook = await downloadWorkbook(page, output)
      assertWorkbookStructure(workbook.entries, output)
    }
    await page.goto(`${baseUrl}/#relatorios?municipio=4313375&relatorio=caderno&objetivo=1`, { waitUntil: 'domcontentloaded' })
    await waitForReadyExport(page)
    const cadernoText = await page.locator('.pme-report').innerText()
    assert.match(cadernoText, /Observação disponível/)
    assert.match(cadernoText, /Dados por ano/)
    assert.match(await page.locator('.pme-evidence__metric strong').first().innerText(), /\d/)
    await savePdfWithTableReview(page, 'caderno.pdf', /Caderno/i)
    await screenshotViewport(page, 'caderno.png')
    await page.goto(`${baseUrl}/#relatorios?municipio=4313375&relatorio=agenda`, { waitUntil: 'domcontentloaded' })
    await savePdfWithTableReview(page, 'agenda.pdf', /Agenda/i)
    await screenshotViewport(page, 'agenda.png')
    await assertHealthyPage(page, network, ['4313375'])
  } finally { await context.close() }
})

test('home e nove páginas municipais usam linguagem pública e layout proporcional em tela ampla', async () => {
  const { context, page, network } = await pageFor({ width: 1920, height: 1080 })
  try {
    const pages = [
      { name: 'apresentacao', hash: '#apresentacao?municipio=4313375', heading: 'Evidências para planejar a educação municipal' },
      { name: 'inicio', hash: '#inicio?municipio=4313375', heading: /Panorama de Nova Santa Rita/, ready: () => waitForObservedCount(page, 41) },
      { name: 'objetivos', hash: '#objetivos?municipio=4313375', heading: /Panorama dos 19 objetivos/ },
      { name: 'objetivo', hash: '#objetivo?municipio=4313375&objetivo=1', heading: /Objetivo 1 — Educação infantil/, ready: () => waitForObjectiveObservedCount(page, 2) },
      { name: 'agenda', hash: '#agenda?municipio=4313375', heading: /Agenda de Análise de Nova Santa Rita/ },
      { name: 'evidencias', hash: '#evidencias?municipio=4313375&objetivo=1', heading: 'Evidências e indicadores' },
      { name: 'financiamento', hash: '#financiamento?municipio=4313375', heading: /Financiamento em Nova Santa Rita/, ready: () => page.locator('.pme-finance-value').first().waitFor({ state: 'visible', timeout: 15_000 }) },
      { name: 'relatorios', hash: '#relatorios?municipio=4313375&relatorio=sintese', heading: 'Materiais para leitura e discussão', ready: () => waitForReadyExport(page) },
      { name: 'relatorio-tecnico', hash: '#relatorio-tecnico?municipio=4313375', heading: 'Relatório Técnico Municipal', exact: true, ready: () => page.locator('.municipal-technical-report').waitFor({ state: 'visible', timeout: 15_000 }) },
      { name: 'transparencia', hash: '#transparencia?municipio=4313375', heading: 'Fontes e como usar esta leitura' },
    ]
    for (const current of pages) {
      await page.goto(`${baseUrl}/${current.hash}`, { waitUntil: 'domcontentloaded' })
      await waitForMunicipalPage(page, current.heading, current.exact)
      await current.ready?.()
      if (current.name === 'relatorios') {
        assert.equal(await page.getByRole('button', { name: 'Síntese' }).count(), 1)
        assert.equal(await page.getByRole('button', { name: 'Caderno' }).count(), 1)
        assert.equal(await page.getByRole('button', { name: 'Agenda' }).count(), 1)
        assert.equal(await page.getByRole('combobox', { name: 'Material' }).count(), 0)
      }
      await assertNoInternalText(page, current.name)
      assert.equal(await noGlobalHorizontalOverflow(page), true, `overflow global em ${current.name}, 1920px`)
      await screenshotViewport(page, `compact-${current.name}-1920.png`)
    }

    await page.goto(`${baseUrl}/#evidencias?municipio=4313375&objetivo=1`, { waitUntil: 'domcontentloaded' })
    await waitForMunicipalPage(page, 'Evidências e indicadores')
    const evidence = page.locator('.pme-evidence').first()
    await evidence.locator('summary').click()
    await evidence.getByRole('heading', { name: 'Dados por ano' }).waitFor({ state: 'visible', timeout: 15_000 })
    const point = evidence.locator('.pme-history-chart__point').first()
    await point.waitFor({ state: 'visible', timeout: 15_000 })
    const graphBox = await evidence.locator('.pme-history-chart__screen-svg').boundingBox()
    assert.ok(graphBox && graphBox.height <= 250, 'o gráfico mantém altura compacta mesmo em telas amplas')
    const pointLabel = await point.getAttribute('aria-label')
    assert.match(pointLabel || '', /^\d{4}: /, 'cada ponto do gráfico informa ano e valor publicado')
    const tableYears = await evidence.locator('.pme-history__table-panel tbody th').allTextContents()
    assert.ok(tableYears.some((year) => pointLabel?.startsWith(`${year}:`)), 'o ano do ponto focal deve estar na tabela publicada')
    await point.focus()
    await evidence.getByRole('tooltip').waitFor({ state: 'visible', timeout: 15_000 })
    assert.match(await evidence.getByRole('tooltip').innerText(), /^\d{4}/)
    await page.keyboard.press('Escape')
    await evidence.getByRole('tooltip').waitFor({ state: 'detached', timeout: 15_000 })

    const tableToggle = evidence.getByRole('button', { name: 'Ocultar tabela' })
    await tableToggle.click()
    const showTableToggle = evidence.getByRole('button', { name: 'Mostrar tabela' })
    assert.equal(await showTableToggle.getAttribute('aria-expanded'), 'false')
    assert.match(await evidence.locator('.pme-history__table-panel').getAttribute('class') || '', /is-hidden/)
    await page.setViewportSize({ width: 704, height: 1000 })
    await page.emulateMedia({ media: 'print' })
    assert.notEqual(await evidence.locator('.pme-history__table-panel').evaluate((element) => getComputedStyle(element).display), 'none', 'a tabela anual deve voltar a aparecer na impressão')
    assert.equal(await evidence.locator('.pme-history__table-toggle').evaluate((element) => getComputedStyle(element).display), 'none', 'o controle de alternância não deve aparecer na impressão')
    const printChart = evidence.locator('.pme-history-chart__print-svg')
    assert.equal(await printChart.isVisible(), true, 'a impressão tem geometria própria e legível')
    assert.equal(await printChart.evaluate((element) => element.getBoundingClientRect().right <= element.parentElement.getBoundingClientRect().right + 1), true, 'todos os anos cabem na largura imprimível')
    assert.deepEqual(await printChart.locator('circle title').allTextContents(), await evidence.locator('.pme-history-chart__screen-svg circle title').allTextContents(), 'tela e impressão contêm as mesmas observações anuais')
    await page.emulateMedia({ media: 'screen' })
    await page.setViewportSize({ width: 1920, height: 1080 })
    await showTableToggle.click()
    assert.equal(await evidence.getByRole('button', { name: 'Ocultar tabela' }).getAttribute('aria-expanded'), 'true')
    await screenshotViewport(page, 'ux-evidencias-detalhes-1440.png')
    await assertNoInternalText(page, 'evidencias-detalhes')
    await assertHealthyPage(page, network, ['4313375'])
  } finally { await context.close() }
})

test('layout PME conserva foco, texto a 200% e overflow em 320, 768, 1440 e 1920', async () => {
  for (const viewport of [{ width: 320, height: 700 }, { width: 768, height: 900 }, { width: 1440, height: 900 }, { width: 1920, height: 1080 }]) {
    const { context, page, network } = await pageFor(viewport)
    try {
      await page.goto(`${baseUrl}/#relatorios?municipio=4313375&relatorio=agenda`, { waitUntil: 'domcontentloaded' })
      await waitForReadyExport(page)
      assert.equal(await noGlobalHorizontalOverflow(page), true, `overflow global em ${viewport.width}px`)
      await page.keyboard.press('Tab')
      assert.equal(await page.locator(':focus').getAttribute('class'), 'pme-skip-link')
      if (viewport.width === 320) await screenshotViewport(page, 'mobile-320.png')
      await assertHealthyPage(page, network, ['4313375'])
    } finally { await context.close() }
  }
  for (const viewport of [{ width: 320, height: 700 }, { width: 1440, height: 900 }]) {
    const { context, page, network } = await pageFor(viewport)
    try {
      for (const [name, hash, heading] of [
        ['inicio', '#inicio?municipio=4313375', /Panorama de Nova Santa Rita/],
        ['financiamento', '#financiamento?municipio=4313375', /Financiamento em Nova Santa Rita/],
      ]) {
        await page.goto(`${baseUrl}/${hash}`, { waitUntil: 'domcontentloaded' })
        await waitForMunicipalPage(page, heading)
        if (name === 'inicio') await waitForObservedCount(page, 41)
        else await page.locator('.pme-finance-value').first().waitFor({ state: 'visible', timeout: 15_000 })
        if (viewport.width === 1440) await screenshotViewport(page, `${name}-1440.png`)
        const zoomStyle = await page.addStyleTag({ content: 'html { font-size: 200% !important; }' })
        await page.locator('.pme-main h1').waitFor({ state: 'visible' })
        assert.equal(await noGlobalHorizontalOverflow(page), true, `overflow global com texto 200% em ${name}, ${viewport.width}px`)
        await screenshotViewport(page, `${name}-texto-200-${viewport.width}.png`)
        await zoomStyle.evaluate((element) => element.remove())
      }
      await assertHealthyPage(page, network, ['4313375'])
    } finally { await context.close() }
  }
})
