import assert from 'node:assert/strict'
import { mkdtemp, readFile, rm, writeFile } from 'node:fs/promises'
import path from 'node:path'
import test, { after, before } from 'node:test'
import { fileURLToPath, pathToFileURL } from 'node:url'
import ts from 'typescript'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..')
let temporaryDirectory
let presentation
let loaders
let contract

async function compile(sourcePath, outputName, rewrite = (source) => source) {
  const absolute = path.join(root, sourcePath)
  const source = await readFile(absolute, 'utf8')
  const output = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022, resolveJsonModule: true },
    fileName: absolute,
  }).outputText
  const outputPath = path.join(temporaryDirectory, outputName)
  await writeFile(outputPath, rewrite(output), 'utf8')
  return outputPath
}

before(async () => {
  temporaryDirectory = await mkdtemp(path.join(root, 'node_modules', '.rs-pme-presentation-'))
  await compile('src/features/matriz/matrizFrentes.ts', 'matrizFrentes.mjs')
  const financing = JSON.parse(await readFile(path.join(root, 'src/data/diagnostic/financingPrograms.json'), 'utf8'))
  await compile('src/experiences/pme/pmeCatalog.ts', 'pmeCatalog.mjs', (source) => source.replace(
    /import financingPrograms from ['"]..\/..\/data\/diagnostic\/financingPrograms\.json['"];?\r?\n/,
    `const financingPrograms = ${JSON.stringify(financing)};\n`,
  ).replace("from '../../features/matriz/matrizFrentes'", "from './matrizFrentes.mjs'"))
  const contractUrl = pathToFileURL(path.join(root, 'src/data/pne2026GoalIndicatorContract.js')).href
  contract = await import(contractUrl)
  const presentationPath = await compile('src/experiences/pme/pmePresentation.ts', 'pmePresentation.mjs', (source) => source
    .replace("from '../../data/pne2026GoalIndicatorContract.js'", `from '${contractUrl}'`)
    .replace("from './pmeCatalog'", "from './pmeCatalog.mjs'"))
  const syntheticRegistry = JSON.stringify({
    municipalities: Array.from({ length: 497 }, (_, index) => ({
      ibgeCode: index === 0 ? '4313375' : index === 1 ? '4314902' : `43${String(index).padStart(5, '0')}`,
      name: `Município ${index}`,
      slug: `municipio-${index}`,
    })),
  })
  const loadersPath = await compile('src/experiences/pme/pmeLoaders.ts', 'pmeLoaders.mjs', (source) => source
    .replace(/import registry from ['"]..\/..\/..\/config\/municipalities\/rs\.json['"];?\r?\n/, `const registry = ${syntheticRegistry};\n`)
    .replace(/import \{ createPne2026DiagnosticLoader \} from ['"][^'"]+['"];?\r?\n/, 'const createPne2026DiagnosticLoader = () => ({ load: async () => { throw new Error("diagnostic stub") } });\n')
    .replace(/import \{ createPne2026MatrizLoader \} from ['"][^'"]+['"];?\r?\n/, 'const createPne2026MatrizLoader = () => ({ load: async () => { throw new Error("matriz stub") } });\n')
    .replace("from './pmePresentation'", "from './pmePresentation.mjs'"))
  presentation = await import(pathToFileURL(presentationPath).href)
  loaders = await import(pathToFileURL(loadersPath).href)
})

after(async () => {
  if (temporaryDirectory) await rm(temporaryDirectory, { recursive: true, force: true })
})

function diagnosticResult({ relationId, goalId, indicatorId, rawValue, dataStatus = 'available', classification = null, mode = 'progress' }) {
  return {
    relationId, goalId, indicatorId, mode, publicName: `Indicador ${relationId}`,
    publicDescription: 'Descrição publicada.', relationshipNote: 'Limite publicado.',
    current: { displayValue: rawValue, year: 2025, unit: 'percent' }, rawValue,
    year: 2025, unit: 'percent', sourceIds: ['inep_censo_escolar'], territoriality: 'municipal',
    methodology: { description: 'Método publicado.' }, dataStatus, reasonCode: null,
    dataStatusLabel: dataStatus === 'suppressed' ? 'Dado suprimido pela fonte' : null,
    indicatorReference: { value: 60, year: 2036, direction: 'at_least', validationStatus: 'official_law' },
    numeratorField: 'numerador', numerator: 0, denominatorField: 'denominador', denominator: 10,
    classification, status: classification ? 'Leitura publicada' : null, distance: classification ? -2 : null,
    trajectory: mode === 'progress' ? { historicalReading: 'Série histórica publicada.' } : null,
    stateComparison: { state: 'below', municipalityValue: 0, stateValue: 10, year: 2025, unit: 'percent', difference: -10, favorableDifference: -10, reading: 'Comparação publicada.', valueReading: '0% e 10%' },
    similarMunicipalities: { median: 8, unit: 'percent', title: 'Municípios com oferta educacional de tamanho semelhante', reading: 'Referência publicada.' },
    statewidePosition: { reading: 'Leitura estadual publicada.' }, publicReading: 'Leitura pública existente.',
  }
}

function diagnostic(municipalityId = '4313375') {
  return {
    schemaVersion: 'pne2026-diagnostic-loader-result-v1', municipalityId, municipalityName: 'Nova Santa Rita', diagnosticSource: 'v3', diagnosticReleaseId: 'a'.repeat(64),
    pne2026PublicDiagnostic: {
      sources: [{ id: 'inep_censo_escolar', publicTitle: 'Censo Escolar da Educação Básica', officialUrl: 'https://example.test' }],
      goals: [
        { goalId: '1.a', results: [diagnosticResult({ relationId: 'relation.1.a.creche', goalId: '1.a', indicatorId: 'creche', rawValue: 0, classification: 'advance' })] },
        { goalId: '1.c', results: [diagnosticResult({ relationId: 'relation.1.c.pre_escola', goalId: '1.c', indicatorId: 'pre_escola', rawValue: null })] },
        { goalId: '7.a', results: [diagnosticResult({ relationId: 'relation.7.a.internet', goalId: '7.a', indicatorId: 'internet', rawValue: 0, mode: 'complementary' })] },
        { goalId: '8.b', results: [diagnosticResult({ relationId: 'relation.8.b.salas_climatizadas', goalId: '8.b', indicatorId: 'salas_climatizadas', rawValue: null, dataStatus: 'suppressed', mode: 'tracking' })] },
      ],
    },
  }
}

function matriz(municipalityId = '4313375') {
  return {
    schemaVersion: 'pne2026-matriz-loader-result-v3', municipalityId, municipalityName: 'Nova Santa Rita', referenceDate: '2026-07-19', outputSha256: 'b'.repeat(64),
    matriz: { municipality: { ibge7: municipalityId, name: 'Nova Santa Rita', uf: 'RS' }, referenceDate: '2026-07-19', sourceDiagnostic: { builderVersion: 'x', catalogSha256: 'a', diagnosticCsvSha256: 'b' }, sourceWorkbook: { schemaVersion: 'x', sha256: 'c' }, curation: { version: 'x', sha256: 'd' }, priorityGoals: [{ goalId: '1.a', indicatorId: 'creche', title: 'Creche', valueRaw: '0', referenceRaw: '60', unit: 'percent', year: '2025', severity: {}, causes: [{ factorId: 'f', name: 'Fator a investigar', governability: 'municipal', proofStatus: 'adverse_local_signal', proof: {}, firstStep: { kind: 'check', text: 'Conferir.', ref: 'x' }, workshopQuestions: ['Pergunta da Matriz.'], collapsed: {} }] }], goalsWithoutOwnCause: [], outOfReach: [], otherPossibleCauses: [], summary: { goalsOnTrack: [], goalsWithoutData: [] } },
  }
}

test('projeção PME reconcilia 19 objetivos e 73 metas sem identidade fictícia', () => {
  const bundle = presentation.buildPmePublicObjectives()
  const { objectives } = bundle
  assert.equal(objectives.length, 19)
  assert.equal(objectives.flatMap((objective) => objective.goals).length, 73)
  assert.equal(objectives[12].title, 'Qualidade da educação profissional e tecnológica')
  assert.equal(objectives[18].title, 'Financiamento e infraestrutura educacional')
  assert.ok(objectives.flatMap((objective) => objective.goals).flatMap((goal) => goal.evidence).every((evidence) => evidence.mode !== 'hidden'))
  assert.ok(objectives.flatMap((objective) => objective.goals).flatMap((goal) => goal.evidence).every((evidence) => evidence.dataState === 'not_loaded'))
  assert.equal(bundle.modules.diagnostic.status, 'not_loaded')
  assert.match(bundle.sources.find((source) => source.sourceId === 'lei_15388_2026').officialUrl, /planalto\.gov\.br/)
})

test('preserva zero, nulo, supressão, relação complementar e ordem canônica', () => {
  const model = presentation.buildPmeMunicipalModel({ municipality: { ibgeCode: '4313375', name: 'Nova Santa Rita', slug: 'nova-santa-rita', stateCode: 'RS' }, diagnostic: diagnostic(), matriz: matriz() })
  const evidence = model.objectives.flatMap((objective) => objective.goals).flatMap((goal) => goal.evidence)
  const zero = evidence.find((item) => item.relationId === 'relation.1.a.creche')
  const nil = evidence.find((item) => item.relationId === 'relation.1.c.pre_escola')
  const suppressed = evidence.find((item) => item.relationId === 'relation.8.b.salas_climatizadas')
  const complementary = evidence.find((item) => item.relationId === 'relation.7.a.internet')
  assert.equal(zero.rawValue, 0); assert.equal(zero.dataState, 'observed')
  assert.equal(nil.rawValue, null); assert.equal(nil.dataState, 'null')
  assert.equal(suppressed.dataState, 'suppressed')
  assert.equal(complementary.permissions.canStatus, false); assert.equal(complementary.status, null); assert.equal(complementary.distance, null); assert.equal(complementary.trajectory, null)
  assert.equal(new Set(evidence.map((item) => item.relationId)).size, evidence.length)
  assert.ok(model.objectives[0].counts.methodologicalRelationships > model.objectives[0].counts.observedRelationships)
  assert.equal(model.agenda.items[0].relationId, 'relation.1.a.creche')
  assert.equal(model.agenda.items[0].questions.at(-1), 'Pergunta da Matriz.')
  assert.match(model.agenda.criterion, /não uma afirmação de tendência/)
})

test('não mistura comparações incompatíveis e mantém todos os estados públicos distintos', () => {
  const result = diagnosticResult({ relationId: 'relation.1.a.creche', goalId: '1.a', indicatorId: 'creche', rawValue: 0, classification: 'advance' })
  const creche = Object.values(contract.PNE_2026_GOAL_INDICATOR_CONTRACT.indicators).find((indicator) => indicator.indicatorId === 'creche')
  result.unit = creche.unit
  result.current.unit = creche.unit
  result.territoriality = creche.territoriality
  result.stateComparison.unit = creche.unit
  result.sourceIds = ['inep_censo_escolar', 'fonte_publica_adicional']
  result.stateComparison = { ...result.stateComparison, year: 2024 }
  const source = diagnostic()
  source.pne2026PublicDiagnostic.goals = [{ goalId: '1.a', results: [result] }]
  const model = presentation.buildPmeMunicipalModel({
    municipality: { ibgeCode: '4313375', name: 'Nova Santa Rita', slug: 'nova-santa-rita', stateCode: 'RS' },
    diagnostic: source,
  })
  const evidence = model.objectives.flatMap((objective) => objective.goals).flatMap((goal) => goal.evidence)
  const incompatible = evidence.find((item) => item.relationId === 'relation.1.a.creche')
  assert.equal(incompatible.comparisonCompatibility, 'incompatible')
  assert.equal(incompatible.stateComparison, null)
  assert.match(incompatible.comparisonNote, /não exibida/)
  assert.equal(incompatible.historicalReading, 'Série histórica publicada.')
  assert.equal(incompatible.projection, null)
  assert.ok(model.sources.some((item) => item.sourceId === 'fonte_publica_adicional'))
  assert.ok(evidence.some((item) => item.dataState === 'not_published'))
  assert.ok(!evidence.some((item) => item.dataState === 'unavailable' || item.dataState === 'not_applicable'))

  for (const [label, mutate] of [
    ['período', (candidate) => { candidate.stateComparison.year = 2024 }],
    ['unidade', (candidate) => { candidate.stateComparison.unit = 'count' }],
    ['valor municipal', (candidate) => { candidate.stateComparison.municipalityValue = 1 }],
    ['território', (candidate) => { candidate.territoriality = 'território incompatível' }],
  ]) {
    const candidate = diagnosticResult({ relationId: 'relation.1.a.creche', goalId: '1.a', indicatorId: 'creche', rawValue: 0, classification: 'advance' })
    candidate.unit = creche.unit
    candidate.current.unit = creche.unit
    candidate.territoriality = creche.territoriality
    candidate.stateComparison.unit = creche.unit
    mutate(candidate)
    const variant = diagnostic()
    variant.pne2026PublicDiagnostic.goals = [{ goalId: '1.a', results: [candidate] }]
    const comparison = presentation.buildPmeMunicipalModel({ municipality: { ibgeCode: '4313375', name: 'Nova Santa Rita', slug: 'nova-santa-rita', stateCode: 'RS' }, diagnostic: variant })
      .objectives.flatMap((objective) => objective.goals).flatMap((goal) => goal.evidence).find((item) => item.relationId === 'relation.1.a.creche')
    assert.equal(comparison.comparisonCompatibility, 'incompatible', `deve bloquear comparação por ${label}`)
  }

  const unavailable = diagnosticResult({ relationId: 'relation.1.a.creche', goalId: '1.a', indicatorId: 'creche', rawValue: null, dataStatus: 'unavailable' })
  const notApplicable = diagnosticResult({ relationId: 'relation.1.c.pre_escola', goalId: '1.c', indicatorId: 'pre_escola', rawValue: null, dataStatus: 'not_applicable' })
  const states = diagnostic()
  states.pne2026PublicDiagnostic.goals = [{ goalId: '1.a', results: [unavailable] }, { goalId: '1.c', results: [notApplicable] }]
  const stateEvidence = presentation.buildPmeMunicipalModel({ municipality: { ibgeCode: '4313375', name: 'Nova Santa Rita', slug: 'nova-santa-rita', stateCode: 'RS' }, diagnostic: states })
    .objectives.flatMap((objective) => objective.goals).flatMap((goal) => goal.evidence)
  assert.equal(stateEvidence.find((item) => item.relationId === 'relation.1.a.creche').dataState, 'unavailable')
  assert.equal(stateEvidence.find((item) => item.relationId === 'relation.1.c.pre_escola').dataState, 'not_applicable')
})

test('comparação com semelhantes confere seus próprios metadados mesmo com estado compatível', () => {
  const indicator = contract.PNE_2026_GOAL_INDICATOR_CONTRACT.indicators.creche
  for (const [peerYear, peerUnit, compatible] of [[2025, 'percent', true], [2024, 'percent', false], [null, 'percent', false], [undefined, 'percent', false], [2025, 'count', false]]) {
    const candidate = diagnosticResult({ relationId: 'relation.1.a.creche', goalId: '1.a', indicatorId: 'creche', rawValue: 0, classification: 'advance' })
    candidate.territoriality = indicator.territoriality
    candidate.similarMunicipalities = { ...candidate.similarMunicipalities, year: peerYear, unit: peerUnit }
    const variant = diagnostic()
    variant.pne2026PublicDiagnostic.goals = [{ goalId: '1.a', results: [candidate] }]
    const evidence = presentation.buildPmeMunicipalModel({ municipality: { ibgeCode: '4313375', name: 'Nova Santa Rita', slug: 'nova-santa-rita', stateCode: 'RS' }, diagnostic: variant })
      .objectives[0].goals[0].evidence[0]
    assert.equal(evidence.comparisonCompatibility, 'compatible')
    assert.notEqual(evidence.stateComparison, null)
    assert.equal(evidence.similarMunicipalities !== null, compatible)
    if (!compatible) assert.match(evidence.comparisonNote, /semelhantes não exibida/)
  }
})

test('contexto da Matriz permanece no objetivo e caminhos não nascem de fallback financeiro', () => {
  const document = matriz()
  document.matriz.priorityGoals[0].causes[0].firstStep = { kind: 'federal_instrument', text: 'Consultar instrumento federal.', ref: 'instrumento-federal' }
  document.matriz.priorityGoals.push({
    goalId: '19.c', indicatorId: 'infraestrutura', title: 'Infraestrutura', valueRaw: '0', referenceRaw: '1', unit: 'percent', year: '2025', severity: {},
    causes: [{ factorId: 'par', name: 'Planejamento', governability: 'municipal', proofStatus: 'adverse_local_signal', proof: {}, firstStep: { kind: 'federal_instrument', text: 'Consultar Novo PAR.', ref: 'novo-par' }, workshopQuestions: ['Pergunta financeira.'], collapsed: {} }],
  })
  const model = presentation.buildPmeMunicipalModel({ municipality: { ibgeCode: '4313375', name: 'Nova Santa Rita', slug: 'nova-santa-rita', stateCode: 'RS' }, matriz: document })
  const objective1 = model.objectives.find((item) => item.objectiveId === '1')
  const objective19 = model.objectives.find((item) => item.objectiveId === '19')
  assert.equal(objective1.matrizContexts[0].goalId, '1.a')
  assert.equal(objective1.paths[0].origin, 'matriz_first_step')
  assert.ok(objective19.matrizContexts.some((item) => item.goalId === '19.c'))
  assert.ok(objective19.paths.every((item) => item.origin !== 'fallback'))
  assert.ok(objective19.paths.some((item) => item.programId === 'par_novo_par'))
  assert.deepEqual(presentation.buildPmePublicObjectives().objectives.find((item) => item.objectiveId === '19').paths, [])
})

test('Matriz ausente ou com erro não invalida diagnóstico, e identidades não se misturam', async () => {
  const missing = await loaders.loadPmeMatrizOptional(async () => { throw Object.assign(new Error('ausente'), { code: 'municipality_not_published' }) }, '4313375')
  const failed = await loaders.loadPmeMatrizOptional(async () => { throw Object.assign(new Error('manifesto inválido'), { code: 'invalid_manifest' }) }, '4313375')
  assert.deepEqual(missing, { status: 'not_published' })
  assert.equal(failed.status, 'error')
  const loader = loaders.createPmeMunicipalLoader({ loadDiagnostic: async () => diagnostic(), loadMatriz: async () => { throw Object.assign(new Error('ausente'), { code: 'municipality_not_published' }) } })
  const model = await loader.load('4313375')
  assert.equal(model.modules.diagnostic.status, 'available'); assert.equal(model.modules.matriz.status, 'not_published')
  assert.equal(loaders.resolvePmeMunicipality('4314902').ibgeCode, '4314902')
  const portoAlegre = presentation.buildPmeMunicipalModel({ municipality: { ibgeCode: '4314902', name: 'Porto Alegre', slug: 'porto-alegre', stateCode: 'RS' }, diagnostic: diagnostic('4314902'), matriz: { status: 'error', error: { code: 'invalid_manifest', message: 'manifesto inválido' } } })
  assert.equal(portoAlegre.municipality.ibgeCode, '4314902'); assert.equal(portoAlegre.modules.matriz.status, 'error')
  assert.throws(() => presentation.buildPmeMunicipalModel({ municipality: { ibgeCode: '4314902', name: 'Porto Alegre', slug: 'porto-alegre', stateCode: 'RS' }, diagnostic: diagnostic() }), /divergente/)
})

test('carregador emite modelos completos por módulo e isola falha de identidade', async () => {
  let releaseDiagnostic
  let releaseMatriz
  const diagnosticPromise = new Promise((resolve) => { releaseDiagnostic = resolve })
  const matrizPromise = new Promise((resolve) => { releaseMatriz = resolve })
  const updates = []
  const loader = loaders.createPmeMunicipalLoader({
    loadDiagnostic: async () => diagnosticPromise,
    loadMatriz: async () => matrizPromise,
  })
  const pending = loader.load('4313375', (model) => updates.push(model))
  assert.equal(updates.length, 1)
  assert.equal(updates[0].modules.diagnostic.status, 'not_loaded')
  assert.equal(updates[0].modules.matriz.status, 'not_loaded')
  releaseDiagnostic(diagnostic())
  await new Promise((resolve) => setImmediate(resolve))
  assert.equal(updates.at(-1).modules.diagnostic.status, 'available')
  assert.equal(updates.at(-1).modules.matriz.status, 'not_loaded')
  releaseMatriz(matriz('4314902'))
  const model = await pending
  assert.equal(model.modules.diagnostic.status, 'available')
  assert.equal(model.modules.matriz.status, 'error')
  assert.equal(model.modules.matriz.error.code, 'matriz_municipality_mismatch')
})
