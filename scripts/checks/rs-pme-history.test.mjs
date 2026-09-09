import assert from 'node:assert/strict'
import { mkdtemp, readFile, rm, writeFile } from 'node:fs/promises'
import path from 'node:path'
import test, { after, before } from 'node:test'
import { fileURLToPath, pathToFileURL } from 'node:url'
import ts from 'typescript'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..')
let temporaryDirectory
let historyApi

async function compile() {
  const sourcePath = path.join(root, 'src/experiences/pme/pmeEvidenceHistory.ts')
  const source = await readFile(sourcePath, 'utf8')
  const contractUrl = pathToFileURL(path.join(root, 'src/data/pne2026GoalIndicatorContract.js')).href
  const goalMapUrl = pathToFileURL(path.join(root, 'src/data/pne2026LegalGoalIndicatorMap.js')).href
  const output = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
    fileName: sourcePath,
  }).outputText
  const staticDataPath = path.join(temporaryDirectory, 'staticData.mjs')
  await writeFile(staticDataPath, 'export const loadMunicipioData = async () => { throw new Error("stub") }\n', 'utf8')
  const outputPath = path.join(temporaryDirectory, 'pmeEvidenceHistory.mjs')
  await writeFile(outputPath, output
    .replace("from '../../data/staticData'", "from './staticData.mjs'")
    .replace("from '../../data/pne2026GoalIndicatorContract.js'", `from '${contractUrl}'`)
    .replace("from '../../data/pne2026LegalGoalIndicatorMap.js'", `from '${goalMapUrl}'`), 'utf8')
  return outputPath
}

function evidence(overrides = {}) {
  return {
    relationId: 'relation.1.a.creche', goalId: '1.a', indicatorId: 'creche',
    dataState: 'observed', period: 2025, rawValue: 35.097668557025834, unit: 'percent',
    ...overrides,
  }
}

before(async () => {
  temporaryDirectory = await mkdtemp(path.join(root, 'node_modules', '.rs-pme-history-'))
  historyApi = await import(pathToFileURL(await compile()).href)
})

after(async () => {
  if (temporaryDirectory) await rm(temporaryDirectory, { recursive: true, force: true })
})

test('lê somente a série PNE 2026 mapeada por IDs canônicos e preserva fonte, universo e compatibilidade', async () => {
  const document = JSON.parse(await readFile(path.join(root, 'public/data/municipios/4313375/index.json'), 'utf8'))
  const history = historyApi.buildPmeEvidenceHistory(document, '4313375', evidence())
  assert.equal(history.status, 'available')
  assert.equal(history.seriesKey, 'creche')
  assert.equal(history.points.at(-1).year, 2025)
  assert.equal(history.points.at(-1).value, 35.097668557025834)
  assert.equal(history.temporalCompatibility, 'same_period_and_value')
  assert.ok(history.sources.some((source) => source.sourceId === 'inep_censo_escolar'))
  assert.match(history.universe, /0 a 3 anos/)
  assert.match(history.sourceDocument, /4313375\/index\.json$/)
  assert.equal(history.sourceRelease, 'Índice público sem identificador próprio de release.')
})

test('preserva zero e nulo publicados e nunca cria série por nome ou relação divergente', () => {
  const document = {
    id_municipio: '4313375',
    pne_2026_2036: { indicadores: { creche: { available: true, series: [
      { ano: 2024, valor: 0 }, { ano: 2025, valor: null },
    ] } } },
  }
  const zero = historyApi.buildPmeEvidenceHistory(document, '4313375', evidence({ period: 2024, rawValue: 0 }))
  assert.equal(zero.status, 'available')
  assert.deepEqual(zero.points, [{ year: 2024, value: 0 }, { year: 2025, value: null }])
  assert.equal(zero.temporalCompatibility, 'same_period_and_value')
  const nil = historyApi.buildPmeEvidenceHistory(document, '4313375', evidence({ dataState: 'null', period: 2025, rawValue: null }))
  assert.equal(nil.status, 'available')
  assert.equal(nil.temporalCompatibility, 'same_period_and_value')
  const unmapped = historyApi.buildPmeEvidenceHistory(document, '4313375', evidence({ relationId: 'relation.inventada.creche' }))
  assert.deepEqual(unmapped, { status: 'absent', dataState: 'observed', reason: 'indicator_not_mapped', indicatorId: 'creche' })
})

test('recusa série malformada ou unidade incompatível sem tentar normalizar o dado publicado', () => {
  const duplicateYear = {
    id_municipio: '4313375',
    pne_2026_2036: { indicadores: { creche: { available: true, series: [
      { ano: 2025, valor: 10 }, { ano: 2025, valor: 11 },
    ] } } },
  }
  assert.throws(() => historyApi.buildPmeEvidenceHistory(duplicateYear, '4313375', evidence({ rawValue: 10 })), /ano duplicado/)
  const gap = {
    id_municipio: '4313375',
    pne_2026_2036: { indicadores: { creche: { available: true, series: [
      { ano: 2023, valor: 10 }, { ano: 2024, valor: null }, { ano: 2025, valor: 12 },
    ] } } },
  }
  const history = historyApi.buildPmeEvidenceHistory(gap, '4313375', evidence({ rawValue: 12 }))
  assert.equal(history.status, 'available')
  assert.deepEqual(history.points[1], { year: 2024, value: null })
  assert.throws(() => historyApi.buildPmeEvidenceHistory(gap, '4313375', evidence({ rawValue: 12, unit: 'count' })), /unidade da evidência/)
})

test('preserva estados indisponíveis e recusa documento de outro código IBGE', async () => {
  const document = JSON.parse(await readFile(path.join(root, 'public/data/municipios/4314902/index.json'), 'utf8'))
  const suppressed = historyApi.buildPmeEvidenceHistory(document, '4314902', evidence({ dataState: 'suppressed' }))
  assert.deepEqual(suppressed, { status: 'absent', dataState: 'suppressed', reason: 'evidence_not_observed', indicatorId: 'creche' })
  const notApplicable = historyApi.buildPmeEvidenceHistory(document, '4314902', evidence({ dataState: 'not_applicable' }))
  assert.equal(notApplicable.status, 'absent')
  assert.throws(() => historyApi.buildPmeEvidenceHistory(document, '4313375', evidence()), /IBGE textual/)
  const loaded = await historyApi.loadPmeEvidenceHistory('4314902', evidence({ rawValue: 40.22724062077456 }), async (id) => {
    assert.equal(id, '4314902')
    return document
  })
  assert.equal(loaded.status, 'available')
})
