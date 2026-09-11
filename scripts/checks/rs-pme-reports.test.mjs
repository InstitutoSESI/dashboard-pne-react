import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import test, { after } from 'node:test'
import { createServer } from 'vite'
import writeXlsxFile from 'write-excel-file/node'
import { unzipSync, strFromU8 } from 'fflate'
import { createPne2026DiagnosticLoader } from '../../src/features/diagnostic/pne2026DiagnosticLoader.js'
import { createPne2026MatrizLoader } from '../../src/features/matriz/pne2026MatrizLoader.js'

const root = new URL('../../', import.meta.url)
const server = await createServer({ root: fileURLToPath(root), configFile: false, optimizeDeps: { noDiscovery: true, entries: [] }, server: { middlewareMode: true, watch: null }, appType: 'custom' })
after(() => server.close())
const [presentation, reports, workbook, finance, routes, registry] = await Promise.all([
  server.ssrLoadModule('/src/experiences/pme/pmePresentation.ts'),
  server.ssrLoadModule('/src/experiences/pme/pmeReports.ts'),
  server.ssrLoadModule('/src/experiences/pme/pmeReportWorkbook.ts'),
  server.ssrLoadModule('/src/experiences/pme/pmeFinancePresentation.ts'),
  server.ssrLoadModule('/src/experiences/pme/pmeRoutes.ts'),
  server.ssrLoadModule('/src/experiences/pme/pmeRegistry.ts'),
])

async function localJson(publicPath) {
  assert.match(publicPath, /^\/data\//)
  assert.equal(publicPath.includes('..'), false)
  return JSON.parse(await readFile(new URL(`public${publicPath}`, root), 'utf8'))
}
const municipality = registry.findPmeMunicipality('4313375')
const [diagnostic, matriz, financial] = await Promise.all([
  createPne2026DiagnosticLoader({ fetchJson: localJson, expectedMunicipalityCount: 497 }).load(municipality.ibgeCode),
  createPne2026MatrizLoader({ fetchJson: localJson }).load(municipality.ibgeCode),
  localJson(`/data/municipios/${municipality.ibgeCode}/financeiro.json`),
])
const model = presentation.buildPmeMunicipalModel({ municipality, diagnostic, matriz })
const emission = '2026-09-07T20:00:00.000Z'
const route = (kind = 'sintese', extra = '') => routes.parsePmeHash(`#relatorios?municipio=4313375&relatorio=${kind}${extra}`)
const cellValue = (cell) => cell && typeof cell === 'object' && 'value' in cell ? cell.value : cell
function columnIndex(sheet, heading) {
  const index = sheet.data[0].findIndex((cell) => cellValue(cell) === heading)
  assert.notEqual(index, -1, `cabeçalho ausente: ${heading}`)
  return index
}
function cellAt(sheet, row, heading) {
  return sheet.data[row][columnIndex(sheet, heading)]
}
function nonUrlCellText(workbook) {
  return workbook.sheets.flatMap((sheet) => {
    const urlColumns = new Set(sheet.data[0].flatMap((cell, index) => /^(URL oficial|Fonte oficial)$/.test(String(cellValue(cell))) ? [index] : []))
    return sheet.data.slice(1).flatMap((row) => row.flatMap((cell, index) => urlColumns.has(index) ? [] : [String(cellValue(cell) ?? '')]))
  }).join('\n')
}

test('a prévia usa escolhas de material e linguagem municipal nas tabelas e síntese', async () => {
  const page = await readFile(new URL('src/experiences/pme/PmeReportsPage.tsx', root), 'utf8')
  assert.match(page, /pme-report-choice/)
  assert.match(page, /Dados disponíveis por objetivo/)
  assert.match(page, /Medidas acompanhadas/)
  assert.match(page, /Informações ausentes/)
  assert.match(page, /pme-report-meta/)
  assert.match(page, /Preparando os dados do material/)
  assert.match(page, /pme-agenda-list--summary/)
  assert.match(page, /compact=\{report\.kind === 'sintese'\}/)
  assert.match(page, /count > 0/)
  assert.doesNotMatch(page, /Cobertura metodológica|Objetivo \/ tema editorial|Demais estados|model\.agenda\.criterion/)
})

test('os três relatórios conservam município, recorte e relações sem multiplicar totais', () => {
  const all = reports.buildPmeReport(model, route(), emission)
  assert.equal(all.objectives.length, 19)
  assert.equal(all.objectives.reduce((sum, item) => sum + item.goals.length, 0), 73)
  assert.equal(new Set(all.rows.map((row) => row.relationId)).size, all.rows.length)
  assert.equal(all.rows.length, model.objectives.flatMap((item) => item.goals.flatMap((goal) => goal.evidence)).length)
  assert.ok(all.sources.every((source) => source.title))
  for (const kind of ['sintese', 'caderno', 'agenda']) {
    const report = reports.buildPmeReport(model, route(kind, '&objetivo=1'), emission)
    assert.equal(report.municipality.ibgeCode, '4313375')
    assert.equal(report.objectives.length, 1)
    assert.ok(report.rows.every((item) => item.objectiveId === '1'))
    assert.ok(report.agendaItems.every((item) => item.objectiveId === '1'))
    assert.equal(report.rows.length, model.objectives[0].goals.flatMap((goal) => goal.evidence).length)
    assert.ok(workbook.buildPmeReportWorkbook(report).fileName.includes(`pme-${kind}-4313375`))
  }
  assert.throws(() => reports.buildPmeReport(model, { ...route(), municipalityId: '4314902' }, emission), /município/)
  assert.throws(() => reports.buildPmeReport(model, route('caderno'), emission), /objetivo/)
  assert.throws(() => reports.buildPmeReport(model, route(), 'invalid'), /emissão/)
})

test('matriz ausente ou indisponível não invalida as observações municipais do relatório', () => {
  for (const matrizState of [{ status: 'not_published' }, { status: 'error', error: { code: 'invalid_manifest', message: 'Inválido' } }]) {
    const partial = presentation.buildPmeMunicipalModel({ municipality, diagnostic, matriz: matrizState })
    const report = reports.buildPmeReport(partial, route(), emission)
    assert.equal(report.rows.filter((row) => row.dataState === 'observed').length, 41)
    assert.equal(report.caveats.some((item) => item.includes('orientações locais não pôde ser usado')), matrizState.status === 'error')
  }
})

test('XLSX real mantém zero, precisão bruta, estados, IBGE textual e texto semelhante a fórmula', async () => {
  const report = reports.buildPmeReport(model, route(), emission)
  const states = ['observed', 'null', 'unavailable', 'suppressed', 'not_applicable', 'not_published']
  report.rows = states.map((dataState, index) => ({ ...report.rows[index], dataState, rawValue: index === 0 ? 0 : null, displayValue: index === 0 ? 0 : null }))
  report.rows.push({ ...report.rows[0], relationId: 'test.raw', title: '=HYPERLINK("https://invalid.example","texto")', rawValue: 117.423456789, displayValue: 117.4, unit: 'percent' })
  report.municipality = { ...report.municipality, name: '+texto de teste' }
  const result = workbook.buildPmeReportWorkbook(report)
  const evidenceSheet = result.sheets.find((sheet) => sheet.sheet === 'Evidências')
  assert.equal(result.sheets.length, 8)
  assert.equal(cellAt(evidenceSheet, 1, 'Valor informado').value, 0)
  assert.equal(cellAt(evidenceSheet, 1, 'Valor informado').type, Number)
  assert.equal(cellAt(evidenceSheet, 2, 'Valor informado'), null)
  assert.equal(cellAt(evidenceSheet, 7, 'Valor informado').value, 117.423456789)
  assert.equal(cellAt(evidenceSheet, 7, 'Valor exibido').value, 117.4)
  assert.equal(cellAt(evidenceSheet, 7, 'Indicador').type, String)
  assert.equal(cellValue(cellAt(evidenceSheet, 1, 'Unidade')), 'Percentual (%)')
  assert.doesNotMatch(String(cellValue(cellAt(evidenceSheet, 1, 'Universo'))), /school_location_over_resident_population|resident_population/)
  assert.deepEqual(evidenceSheet.data.slice(1, 7).map((row) => cellValue(row[columnIndex(evidenceSheet, 'Situação')])), ['Observação disponível', 'Valor nulo na publicação', 'Indisponível na fonte', 'Dado suprimido', 'Não aplicável', 'Relação sem observação publicada'])
  assert.doesNotMatch(evidenceSheet.data[0].map(cellValue).join(' '), /Relação|Estado original|Indicador ID/i)
  const zip = unzipSync(new Uint8Array(await writeXlsxFile(result.sheets).toBuffer()))
  const files = Object.fromEntries(Object.entries(zip).map(([name, bytes]) => [name, strFromU8(bytes)]))
  for (const [name, xml] of Object.entries(files)) {
    if (name.endsWith('.xml')) assert.doesNotMatch(xml, /<f(?:\s|>)/)
  }
  assert.match(files['xl/worksheets/sheet1.xml'], /<c(?=[^>]*r="B4")(?=[^>]*t="s")[^>]*>/)
  assert.match(files['xl/sharedStrings.xml'], /4313375/)
  assert.match(files['xl/sharedStrings.xml'], /HYPERLINK/)
  assert.match(files['xl/worksheets/sheet3.xml'], /117\.423456789/)
  assert.match(files['xl/sharedStrings.xml'], /Dado suprimido/)
  assert.match(files['xl/sharedStrings.xml'], /Não aplicável/)
  assert.doesNotMatch(files['xl/sharedStrings.xml'], /test\.raw|Estado original|Campo numerador|sourceDocument/)
  assert.doesNotMatch(nonUrlCellText(result), /school_location_over_resident_population|resident_population|institution_location|\b(percent|count|years|observed|unavailable|suppressed|not_applicable|not_published)\b|sourceDocument|sourceRelease|numeratorField|denominatorField/)
})

test('o financeiro projeta valores existentes e rejeita identidade e histórico incoerentes', () => {
  const metrics = finance.buildPmeFinancialMetrics(financial, municipality)
  assert.equal(metrics.length, 10)
  assert.equal(metrics.find((item) => item.id === 'fundeb').amount, financial.amounts.fundebTotalAnnualForecast)
  assert.equal(metrics.find((item) => item.id === 'paid').amount, financial.execution.dcaEducation.paid)
  const altered = structuredClone(financial)
  altered.amounts.fundebVaafAnnualForecast.value = 0
  altered.amounts.fundebVaatAnnualForecast.value = null
  const states = finance.buildPmeFinancialMetrics(altered, municipality)
  assert.equal(states.find((item) => item.id === 'vaaf').amount.value, 0)
  assert.equal(states.find((item) => item.id === 'vaat').amount.value, null)
  assert.throws(() => finance.buildPmeFinancialMetrics(financial, { ...municipality, ibgeCode: '4314902' }), /identidade/)
  altered.execution.dcaEducation.history[0].paid.referenceYear -= 1
  assert.throws(() => finance.buildPmeFinancialMetrics(altered, municipality), /histórico financeiro/)
  altered.execution.dcaEducation.history = null
  assert.throws(() => finance.buildPmeFinancialMetrics(altered, municipality), /Histórico/)
})

test('caderno e XLSX reutilizam o snapshot de séries sem recalcular valor ou preencher lacunas', () => {
  const relationId = model.objectives[0].goals[0].evidence[0].relationId
  const history = {
    status: 'available', dataState: 'observed', indicatorId: 'creche', seriesKey: 'creche',
    points: [{ year: 2023, value: 0 }, { year: 2024, value: null }, { year: 2025, value: 117.423456789 }],
    unit: 'percent', universe: 'Universo publicado', sources: [{ sourceId: 'test', title: 'Fonte publicada', officialUrl: null }],
    sourceDocument: '/data/municipios/4313375/index.json', sourceRelease: 'Índice público sem identificador próprio de release.', temporalCompatibility: 'same_period_different_value',
  }
  const report = reports.buildPmeReport(model, route('caderno', '&objetivo=1'), emission, { [relationId]: history })
  assert.equal(report.histories[relationId], history)
  assert.ok(report.caveats.some((item) => item.includes('apenas contexto temporal')))
  const sheet = workbook.buildPmeReportWorkbook(report).sheets.find((item) => item.sheet === 'Séries anuais de apoio')
  assert.equal(cellAt(sheet, 1, 'Valor informado').value, 0)
  assert.equal(cellAt(sheet, 2, 'Valor informado'), null)
  assert.equal(cellValue(cellAt(sheet, 2, 'Situação')), 'Valor nulo na publicação')
  assert.equal(cellAt(sheet, 3, 'Valor informado').value, 117.423456789)
  assert.equal(cellValue(cellAt(sheet, 1, 'Unidade')), 'Percentual (%)')
  assert.match(cellValue(cellAt(sheet, 3, 'Nota de leitura')), /difere da observação/)
  assert.doesNotMatch(sheet.data[0].map(cellValue).join(' '), /Relação|Indicador|Documento|Versão|Compatibilidade/)
})
