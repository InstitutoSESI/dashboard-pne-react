import assert from 'node:assert/strict'
import { readFile, readdir } from 'node:fs/promises'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import test from 'node:test'
import { createServer } from 'vite'
import React from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import ts from 'typescript'

const repoRoot = join(dirname(fileURLToPath(import.meta.url)), '..', '..')
const readText = (relativePath) => readFile(join(repoRoot, relativePath), 'utf8')
const readJson = (relativePath) => readText(relativePath).then(JSON.parse)

async function loadTypeScriptModule(relativePath) {
  // O módulo é importado isolado via data: URL, onde imports relativos não
  // resolvem. Este teste valida a publicação RS, então o padrão do estado
  // ativo é substituído pelo equivalente RS.
  const source = (await readText(relativePath)).replace(
    /import \{ ACTIVE_MUNICIPALITY_ID_PATTERN \} from '[^']*stateConfig(?:\.js)?';?\r?\n/,
    'const ACTIVE_MUNICIPALITY_ID_PATTERN = /^43\\d{5}$/;\n',
  )
  const output = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
  }).outputText
  return import(`data:text/javascript;base64,${Buffer.from(output).toString('base64')}`)
}

const [loaderModule, manifest, municipalities] = await Promise.all([
  loadTypeScriptModule('src/data/qseAnnual.ts'),
  readJson('public/data/financeiro/qse-anual-manifest.json'),
  readJson('public/data/municipios_index.json'),
])

test('cobertura publicada é integral e a reconciliação de 2024 não diverge', () => {
  assert.deepEqual(manifest.years, [2020, 2021, 2022, 2023, 2024, 2025])
  manifest.coverage.forEach((quality) => {
    assert.equal(quality.municipalitiesExpected, 497)
    assert.equal(quality.municipalitiesIdentified, 497)
    assert.equal(quality.municipalitiesWithValue, 497)
    assert.equal(quality.coverageRate, 1)
    assert.deepEqual(quality.absentMunicipalityCodes, [])
    assert.deepEqual(quality.duplicateMunicipalityCodes, [])
    assert.deepEqual(quality.unmappedRecords, [])
    assert.deepEqual(quality.nullValueMunicipalityCodes, [])
    assert.deepEqual(quality.officialZeroMunicipalityCodes, [])
    assert.deepEqual(quality.negativeValueMunicipalityCodes, [])
  })
  assert.equal(manifest.reconciliation2024.comparedMunicipalities, 497)
  assert.equal(manifest.reconciliation2024.divergenceCount, 0)
  assert.equal(manifest.reconciliation2024.maximumAbsoluteDifference, 0)
  assert.equal(manifest.monthlyContinuity2024.comparedMunicipalities, 497)
  assert.equal(manifest.monthlyContinuity2024.divergenceCount, 0)
  assert.equal(manifest.monthlyContinuity2024.maximumAbsoluteDifference, 0)
  const quality2025 = manifest.coverage.find((quality) => quality.year === 2025)
  assert.equal(quality2025.monthlyReconciledMunicipalities, 497)
  assert.equal(quality2025.monthlyDivergenceCount, 0)
  assert.deepEqual(quality2025.missingMonthMunicipalityCodes, [])
  assert.equal(quality2025.stateRowsSeparated, 1)
  assert.equal(manifest.enrollmentBasis2025Quality.municipalitiesIdentified, 497)
  const source2025 = manifest.sources.find((source) => source.sourceId === 'fnde_qse_realized_2025')
  assert.equal(source2025.sha256, 'a7c01d0645a3f582d4c2c6c531d05f80b829d07f836915fc347a25031d4e7841')
  assert.equal(source2025.fileSizeBytes, 2239536)
  assert.equal(source2025.parser, 'parse_qse_monthly_lines')
  assert.equal(source2025.columns.length, 16)
})

test('contrato anual é versionado, municipal e reutiliza o ID canônico', async () => {
  assert.equal(manifest.schemaVersion, 'qse-annual-v1')
  assert.equal(manifest.indicatorId, 'qse.distributed_amount')
  assert.equal(manifest.logicalContracts, 497)
  const codeDirectories = await readdir(join(repoRoot, 'public', 'data', 'municipios'), { withFileTypes: true })
  const contracts = codeDirectories.filter((entry) => /^43\d{5}$/.test(entry.name))
  assert.equal(contracts.length, 497)
  for (const municipality of municipalities.municipios) {
    const document = await readJson(`public/data/municipios/${municipality.id_municipio}/qse-anual.json`)
    assert.equal(loaderModule.isQseAnnualDocument(document), true, municipality.id_municipio)
    assert.equal(document.indicatorId, 'qse.distributed_amount')
    assert.equal(document.municipality.ibgeCode, municipality.id_municipio)
    assert.deepEqual(document.series.map((point) => point.year), [2020, 2021, 2022, 2023, 2024, 2025])
    assert.equal(document.series.some((point) => 'officialEstimate' in point), false)
    assert.equal(document.series.some((point) => 'monthlyAmounts' in point || 'monthlySum' in point), false)
  }
  const agudo = await readJson('public/data/municipios/4300109/qse-anual.json')
  const latest = agudo.series.at(-1)
  assert.equal(latest.year, 2025)
  assert.equal(latest.distributedAmount, 1103967.26)
  assert.equal(latest.enrollmentBasis, 1890)
  assert.equal(latest.distributedPerEnrollment, 584.1096613756614)
})

test('loader busca somente o histórico do município solicitado e mantém cache', async () => {
  const fixture = await readJson('public/data/municipios/4300109/qse-anual.json')
  const paths = []
  const loader = loaderModule.createQseAnnualLoader(async (path) => {
    paths.push(path)
    return new Response(JSON.stringify(fixture), { status: 200 })
  })
  assert.equal(paths.length, 0)
  const first = loader.load('4300109')
  assert.equal(loader.getState('4300109').status, 'loading')
  assert.equal((await first).municipality.ibgeCode, '4300109')
  await loader.load('4300109')
  assert.deepEqual(paths, ['/data/municipios/4300109/qse-anual.json'])
})

test('ordenação omite ano ausente e preserva zero oficial', () => {
  const point = (year, distributedAmount) => ({
    year,
    distributedAmount,
    enrollmentBasis: null,
    distributionCoefficient: null,
    distributedPerEnrollment: null,
    sourceId: `source-${year}`,
    sourceFileReference: `file-${year}`,
    sourceFileSha256: 'a'.repeat(64),
    cutoffDate: '2026-07-21',
  })
  const prepared = loaderModule.prepareQseAnnualSeries([point(2024, 10), point(2020, 0), point(2022, 5)])
  assert.deepEqual(prepared.map((item) => item.year), [2020, 2022, 2024])
  assert.equal(prepared[0].distributedAmount, 0)
  assert.equal(prepared.some((item) => item.year === 2021 || item.year === 2023), false)
})

test('variação usa somente os dois últimos exercícios oficiais realizados', () => {
  const series = [
    { year: 2020, distributedAmount: 100 },
    { year: 2022, distributedAmount: 120 },
  ]
  const variation = loaderModule.calculateQseAnnualVariation(series)
  assert.equal(variation.previous.year, 2020)
  assert.equal(variation.current.year, 2022)
  assert.equal(variation.percentage, 20)
})

test('contrato de Agudo calcula a variação realizada de 2025 contra 2024', async () => {
  const document = await readJson('public/data/municipios/4300109/qse-anual.json')
  const variation = loaderModule.calculateQseAnnualVariation(document.series)
  assert.equal(variation.previous.year, 2024)
  assert.equal(variation.current.year, 2025)
  assert.equal(variation.current.distributedAmount, 1103967.26)
  assert.equal(variation.percentage, 5.641879045437224)
})

test('gráfico renderiza barras anuais, zero e destaque final sem estimativa', async (context) => {
  const server = await createServer({
    root: repoRoot,
    server: { middlewareMode: true },
    appType: 'custom',
  })
  context.after(() => server.close())
  const module = await server.ssrLoadModule('/src/features/municipal-finance/QseAnnualPanel.tsx')
  const series = [2020, 2021, 2022, 2023, 2024, 2025].map((year, index) => ({
    year,
    distributedAmount: index === 0 ? 0 : 100 + index * 20,
    enrollmentBasis: year === 2025 ? 10 : null,
    distributionCoefficient: year === 2025 ? 0.1 : null,
    distributedPerEnrollment: year === 2025 ? 20 : null,
    sourceId: `fnde-${year}`,
    sourceFileReference: `${year}`,
    sourceFileSha256: String(index + 1).repeat(64),
    cutoffDate: '2026-07-21',
  }))
  const markup = renderToStaticMarkup(React.createElement(module.QseAnnualChart, { series }))
  assert.match(markup, /2020: R\$/)
  assert.match(markup, /class="chart-bar is-last"/)
  assert.equal((markup.match(/class="chart-bar(?: is-last)?"/g) ?? []).length, 6)
  assert.match(markup, /2025/)
  assert.doesNotMatch(markup, /estimativa|2026/i)
})

test('interface separa realizado e estimado e não expõe status técnico', async () => {
  const source = await readText('src/features/municipal-finance/QseAnnualPanel.tsx')
  assert.match(source, /estimados; ainda não representam recurso distribuído\./)
  assert.match(source, /QSE distribuída em/)
  assert.match(source, /Variação em relação a/)
  assert.match(source, /Histórico de valores \(R\$ mil\)/)
  assert.match(source, /Valor por matrícula em/)
  assert.match(source, /Dados usados no cálculo/)
  assert.doesNotMatch(source, /\b(?:Janeiro|Fevereiro|Março|Abril|Maio|Junho|Julho|Agosto|Setembro|Outubro|Novembro|Dezembro)\b/)
  assert.doesNotMatch(source, /incompatible_version|invalid_contract|schemaVersion/)
  assert.doesNotMatch(source, /ranking|projeção da QSE|comparação entre municípios/i)
})
