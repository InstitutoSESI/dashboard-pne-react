import assert from 'node:assert/strict'
import { execFile } from 'node:child_process'
import { readFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import test from 'node:test'
import { promisify } from 'node:util'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { createServer } from 'vite'

import {
  buildPublicDiagnosticCopy,
  buildPublicSummaryText,
  DIAGNOSTIC_RESULT_VIEWS,
  formatPublicValue,
  getPublicCurrentValue,
  getPublicOfficialSources,
  getPublicRelationshipNote,
  getPublicResultStatus,
  getPublicStateComparison,
  getPublicSupportingReadings,
  isAvailableTrackingDiagnosticResult,
  isComparableLegalDiagnosticResult,
  selectDiagnosticResults,
  selectDiagnosticThemeGroups,
  selectLegalDiagnosticSummary,
} from '../../src/features/diagnostic/diagnosticPresentation.js'
import {
  resolvePne2026PublicDiagnosticV3,
} from '../../src/features/diagnostic/pne2026PublicDiagnosticV3.js'
import {
  sanitizeMunicipalDiagnosticContract,
  sanitizePne2026PublicDiagnostic,
  selectMunicipalDiagnosticContract,
} from './support/pne2026DiagnosticV2Audit.mjs'
import {
  getPne2026Relation,
  PNE_2026_RELATIONSHIP_MODES,
} from '../../src/data/pne2026GoalIndicatorContract.js'

const PUBLIC_VERSION = 'pne2026-public-diagnostic-v2'
const projectRoot = fileURLToPath(new URL('../..', import.meta.url))
const execFileAsync = promisify(execFile)
const vite = await createServer({
  appType: 'custom',
  configFile: false,
  logLevel: 'silent',
  publicDir: false,
  root: projectRoot,
  server: { middlewareMode: true },
})
const { DiagnosticPanel } = await vite.ssrLoadModule('/src/components/DiagnosticPanel.jsx')

test.after(async () => {
  await vite.close()
})

async function readVersionedJson(relativePath) {
  const { stdout } = await execFileAsync(
    'git',
    ['show', `HEAD:${relativePath}`],
    { cwd: projectRoot, encoding: 'utf8', maxBuffer: 16 * 1024 * 1024 },
  )
  return JSON.parse(stdout)
}

async function readContract(slug) {
  return readVersionedJson(`public/data/municipios/${slug}/diagnostico.json`)
}

function flatten(diagnostic) {
  return diagnostic.goals.flatMap((goal) => goal.results)
}

function renderDiagnostic(
  contract,
  municipio = 'Município de teste',
  initialView = DIAGNOSTIC_RESULT_VIEWS.LEGAL,
) {
  return renderToStaticMarkup(createElement(DiagnosticPanel, {
    contractStatus: 'ready',
    data: sanitizeMunicipalDiagnosticContract(contract),
    initialView,
    municipio,
  }))
}

function renderViewModel(
  diagnostic,
  municipio = 'Município de teste',
  initialView = DIAGNOSTIC_RESULT_VIEWS.LEGAL,
) {
  return renderToStaticMarkup(createElement(DiagnosticPanel, {
    contractStatus: 'ready',
    data: { pne2026PublicDiagnostic: diagnostic },
    initialView,
    municipio,
  }))
}

function visibleText(markup) {
  return markup
    .replace(/<[^>]+>/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/&quot;/g, '"')
    .replace(/&#x27;/g, "'")
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/\s+/g, ' ')
    .trim()
}

function visibleScreenText(markup) {
  return visibleText(markup.replace(/<article class="diagnostic-print-report"[\s\S]*$/, ''))
}

async function readCurrentV3Municipality(municipalityId) {
  const pointer = JSON.parse(await readFile(
    new URL('../../public/data/pne2026-diagnostic-v3/current.json', import.meta.url),
    'utf8',
  ))
  const payload = JSON.parse(await readFile(
    new URL(
      `../../public/data/pne2026-diagnostic-v3/releases/${pointer.releaseId}/municipios/${municipalityId}.json`,
      import.meta.url,
    ),
    'utf8',
  ))
  return resolvePne2026PublicDiagnosticV3(payload)
}

test('offline historical audit accepts only the supported legacy technical contract', () => {
  assert.equal(selectMunicipalDiagnosticContract(null).status, 'missing')
  assert.equal(selectMunicipalDiagnosticContract({ schemaVersion: 'future' }).status, 'incompatible_version')
  assert.equal(selectMunicipalDiagnosticContract({
    schemaVersion: 'municipal-diagnostic-v2',
    pne2026PublicDiagnostic: { version: 'pne2026-public-diagnostic-v1' },
  }).status, 'incompatible_version')
  assert.equal(selectMunicipalDiagnosticContract({
    schemaVersion: 'municipal-diagnostic-v2',
    pne2026PublicDiagnosticV2: { version: PUBLIC_VERSION },
  }).status, 'ready')
})

test('legal summary reports only comparable indicators and resolved situations', () => {
  const summary = {
    advanceCount: 22,
    maintainCount: 2,
    comparableIndicatorCount: 24,
    stateComparisonCount: 17,
    statewidePositionCount: 17,
  }
  assert.equal(
    buildPublicSummaryText(summary),
    'Entre os 24 indicadores com comparação disponível, 2 referências foram alcançadas e 22 estão abaixo da referência.',
  )
  assert.doesNotMatch(buildPublicSummaryText(summary), /Rio Grande do Sul|acompanhamento|posição/i)
})

test('methodological safety hides blocked relationships and preserves raw percentages', () => {
  const baseResult = {
    resultOrder: 1,
    goalId: '4.b',
    indicatorId: 'idade_regular_quinto',
    themeId: 'theme',
    tier: 'essential',
    priorityOrder: 1,
    publicName: 'Nome anterior',
    relationshipType: 'direct',
    classification: 'maintain',
    current: { value: 102.4, displayValue: 100, displayText: '100%', year: 2025, unit: 'percent' },
    indicatorReference: { value: 100, year: 2036, direction: 'at_least' },
    distance: 2.4,
    remainingGap: 0,
    favorableDifference: 2.4,
  }
  const hiddenResult = {
    ...baseResult,
    goalId: '17.b',
    indicatorId: 'rendimento_magisterio',
  }
  const safe = sanitizePne2026PublicDiagnostic({
    version: PUBLIC_VERSION,
    goals: [
      { goalId: '4.b', results: [baseResult] },
      { goalId: '17.b', results: [hiddenResult] },
    ],
    summary: {},
  })
  const results = flatten(safe)

  assert.equal(results.length, 1)
  assert.equal(results[0].publicName, 'Estudantes matriculados sem distorção — anos iniciais')
  assert.equal(results[0].current.displayValue, 102.4)
  assert.equal(results[0].current.displayText, '102,4%')
  assert.equal(results[0].mode, 'tracking')
  assert.equal(results[0].indicatorReference.value, 100)
  assert.equal(results[0].distance, 2.4)
  assert.equal(results[0].classification, null)
  assert.equal(formatPublicValue(102.4, 'percent'), '102,4%')
})

test('canonical mode and editorial policy override every legacy compatibility field', async () => {
  const contract = await readContract('4315503')
  const rawDiagnostic = structuredClone(contract.pne2026PublicDiagnosticV2)
  const rawResult = flatten(rawDiagnostic).find((result) => (
    getPne2026Relation(result.goalId, result.indicatorId)?.mode
    === PNE_2026_RELATIONSHIP_MODES.COMPLEMENTARY
  ))
  const relation = getPne2026Relation(rawResult.goalId, rawResult.indicatorId)
  rawDiagnostic.summary = structuredClone(
    sanitizePne2026PublicDiagnostic(rawDiagnostic).summary,
  )
  Object.assign(rawResult, {
    relationId: relation.relationId,
    tracksGoal: true,
    tracks_goal: true,
    hasDistance: true,
    monitoringMode: 'progress',
    tier: 'essential',
    priorityOrder: -100,
    themeId: 'tema-inventado',
    classification: 'maintain',
    distance: 999,
    status: 'Meta atingida',
    trajectory: { estimatedAchievementYear: 2027 },
  })

  const result = flatten(sanitizePne2026PublicDiagnostic(rawDiagnostic))
    .find((item) => item.relationId === relation.relationId)
  assert.equal(result.mode, 'complementary')
  assert.notEqual(result.themeId, 'tema-inventado')
  assert.notEqual(result.displayOrder, -100)
  for (const field of [
    'classification',
    'distance',
    'indicatorReference',
    'status',
    'trajectory',
    'tier',
    'priorityOrder',
    'relationshipType',
    'tracksGoal',
    'tracks_goal',
    'hasDistance',
  ]) {
    assert.equal(field in result, false, field)
  }
})

test('relationId must match the exact goal × indicator pair', async () => {
  const contract = await readContract('4315503')
  const rawDiagnostic = structuredClone(contract.pne2026PublicDiagnosticV2)
  const first = rawDiagnostic.goals[0].results[0]
  first.relationId = 'relation.17.b.rendimento_magisterio'
  assert.throws(
    () => sanitizePne2026PublicDiagnostic(rawDiagnostic),
    /não corresponde/,
  )
})

test('production omits invalid relations and reports the same issue only once', () => {
  const previousNodeEnv = process.env.NODE_ENV
  const originalConsoleError = console.error
  const errors = []
  process.env.NODE_ENV = 'production'
  console.error = (message) => errors.push(message)
  try {
    const rawDiagnostic = {
      version: PUBLIC_VERSION,
      summary: {},
      goals: [{
        goalId: '1.a',
        results: [{
          relationId: 'relation.unknown',
          indicatorId: 'indicator.unknown',
          current: { value: 1, year: 2025, unit: 'percent' },
        }],
      }],
    }
    assert.equal(flatten(sanitizePne2026PublicDiagnostic(rawDiagnostic)).length, 0)
    assert.equal(flatten(sanitizePne2026PublicDiagnostic(rawDiagnostic)).length, 0)
    assert.equal(errors.length, 1)
    assert.match(errors[0], /relationId desconhecido/)
  } finally {
    console.error = originalConsoleError
    if (previousNodeEnv === undefined) delete process.env.NODE_ENV
    else process.env.NODE_ENV = previousNodeEnv
  }
})

test('state comparison formats the materialized difference without recalculating it', async () => {
  const contract = await readContract('4315503')
  const rawDiagnostic = structuredClone(contract.pne2026PublicDiagnosticV2)
  const rawResult = flatten(rawDiagnostic).find((result) => result.stateComparison)
  rawResult.stateComparison = {
    ...rawResult.stateComparison,
    municipalityValue: 10,
    stateValue: 90,
    difference: 123.4,
  }
  const result = flatten(sanitizePne2026PublicDiagnostic(rawDiagnostic))
    .find((item) => (
      item.goalId === rawResult.goalId && item.indicatorId === rawResult.indicatorId
    ))
  assert.equal(getPublicStateComparison(result).difference, '+123,4 p.p.')
})

test('canonical view model recomputes summary without retaining the legacy summary', async () => {
  const contract = await readContract('4315503')
  const rawDiagnostic = structuredClone(contract.pne2026PublicDiagnosticV2)
  for (const result of flatten(rawDiagnostic)) {
    result.relationId = getPne2026Relation(result.goalId, result.indicatorId).relationId
  }
  rawDiagnostic.summary.advanceCount += 1
  const resolved = sanitizePne2026PublicDiagnostic(rawDiagnostic)
  assert.equal(
    resolved.summary.advanceCount,
    flatten(resolved).filter(
      (result) => result.mode === 'progress' && result.classification === 'advance',
    ).length,
  )
  assert.notEqual(resolved.summary.advanceCount, rawDiagnostic.summary.advanceCount)
  assert.equal('authorizedResultCount' in resolved.summary, false)
  assert.equal('relationshipCounts' in resolved.summary, false)
})

test('initial page renders only comparable legal indicators grouped by visible theme', async () => {
  const contract = await readContract('4315503')
  const diagnostic = sanitizePne2026PublicDiagnostic(contract.pne2026PublicDiagnosticV2)
  const legal = selectDiagnosticResults(diagnostic)
  const excluded = flatten(diagnostic).filter(
    (result) => !isComparableLegalDiagnosticResult(result),
  )
  const markup = renderDiagnostic(contract, 'Restinga Seca')
  const text = visibleScreenText(markup)

  assert.match(text, /Diagnóstico educacional de Restinga Seca/)
  assert.match(text, /Resumo do diagnóstico/)
  assert.match(text, /Filtros/)
  assert.match(text, /Resultados por tema/)
  assert.match(text, /Referências previstas nas metas/)
  assert.ok(legal.every(({ result }) => text.includes(result.publicName)))
  assert.ok(excluded.every((result) => !text.includes(result.publicName)))
  assert.doesNotMatch(text, /tier|priorityOrder|essencial \d de 9/i)
})

test('legal and complementary relationships retain their presentation-safe statuses', async () => {
  const contract = await readContract('4315503')
  const results = flatten(sanitizePne2026PublicDiagnostic(contract.pne2026PublicDiagnosticV2))
  const unclassified = {
    mode: 'progress',
    dataStatus: 'available',
    classification: null,
    relationshipLabel: null,
    publicReading: 'Resultado disponível para acompanhamento.',
  }
  const complementary = results.find((result) => result.mode === 'complementary')

  assert.deepEqual(
    getPublicResultStatus(unclassified),
    { key: 'followup', label: 'Situação indisponível' },
  )
  assert.equal(unclassified.relationshipLabel, null)
  assert.equal(getPublicRelationshipNote(unclassified), '')
  assert.doesNotMatch(
    unclassified.publicReading,
    /distância|alcançou a meta|superou a meta/i,
  )
  assert.deepEqual(
    getPublicResultStatus(complementary),
    { key: 'context', label: 'Indicador complementar' },
  )
})

test('public comparisons and trajectories render without technical terms', async () => {
  const contract = await readContract('4315503')
  const results = flatten(sanitizePne2026PublicDiagnostic(contract.pne2026PublicDiagnosticV2))
  assert.ok(results.some((result) => result.stateComparison?.reading))
  assert.ok(results.some((result) => getPublicSupportingReadings(result).length > 0))
  const markup = renderDiagnostic(contract, 'Restinga Seca')
  const text = visibleScreenText(markup)
  assert.match(text, /Como se compara/)
  assert.match(text, /Rio Grande do Sul/)
  assert.match(text, /Posição no RS/)
  assert.match(text, /Evolução recente/)
  assert.match(
    text,
    /Veja os resultados do município em relação às metas do PNE e ao contexto dos municípios do Rio Grande do Sul\./,
  )
  assert.doesNotMatch(text, /better|equivalent|similar|worse|percentil|quartil|coorte|cluster|modelo|quality/i)
})

test('copy from the historical fixture contains only comparable legal results', async () => {
  const contract = await readContract('4315503')
  const diagnostic = sanitizePne2026PublicDiagnostic(
    contract.pne2026PublicDiagnosticV2,
  )
  const text = buildPublicDiagnosticCopy(diagnostic, 'Restinga Seca')
  const legal = selectDiagnosticResults(diagnostic)
  const excluded = flatten(diagnostic).filter(
    (result) => !isComparableLegalDiagnosticResult(result),
  )

  assert.match(text, /Resumo do diagnóstico/)
  assert.match(text, /Indicadores com comparação disponível: 18\./)
  assert.match(text, /Abaixo da referência: 17\./)
  assert.match(text, /Referências alcançadas: 1\./)
  assert.doesNotMatch(text, /Resultados para acompanhamento:/)
  assert.match(text, /Acima ou próximos do RS: 1\./)
  assert.match(text, /Abaixo do RS: 10\./)
  assert.match(text, /Comparação com o RS/)
  assert.match(text, /Posição entre os municípios do RS/)
  assert.match(text, /Municípios com oferta educacional de tamanho semelhante/)
  assert.match(text, /Evolução recente/)
  assert.match(text, /Resultados essenciais/)
  assert.match(text, /Demais resultados/)
  assert.match(text, /Fontes das informações/)
  for (const { result } of legal) {
    assert.equal(text.split(result.publicName).length - 1, 1, result.indicatorId)
  }
  assert.ok(excluded.every((result) => !text.includes(result.publicName)))
  assert.doesNotMatch(text, /Remuneração dos profissionais do magistério|Expansão de cursos técnicos subsequentes/i)
  assert.doesNotMatch(text, /priorityOrder|\btier\b|pne2026-public|financiamento|null|undefined|NaN/i)
})

test('only complete official sources from the historical fixture are rendered with distinct names', async () => {
  const contract = await readContract('4315503')
  const diagnostic = contract.pne2026PublicDiagnosticV2
  const officialSources = getPublicOfficialSources(diagnostic.sources)
  const markup = renderDiagnostic(contract, 'Restinga Seca')

  assert.equal(officialSources.length, 3)
  assert.equal(
    (markup.match(/aria-label="Acessar fonte oficial: /g) ?? []).length,
    officialSources.length,
  )
  assert.doesNotMatch(visibleText(markup), /proveniência pendente|Base municipal de população por idade/i)
})

test('São Leopoldo separates legal, tracking, complementary, and unavailable results', async () => {
  const diagnostic = await readCurrentV3Municipality('4318705')
  const allResults = flatten(diagnostic)
  const legal = selectDiagnosticResults(diagnostic)
  const tracking = selectDiagnosticResults(
    diagnostic,
    DIAGNOSTIC_RESULT_VIEWS.TRACKING,
  )
  const complementary = allResults.filter((result) => result.mode === 'complementary')
  const summary = selectLegalDiagnosticSummary(diagnostic)
  const legalIds = new Set(legal.map(({ result }) => result.indicatorId))
  const trackingIds = new Set(tracking.map(({ result }) => result.indicatorId))

  assert.equal(legal.length, 25)
  assert.equal(tracking.length, 14)
  assert.equal(complementary.length, 9)
  assert.equal(summary.totalIndicatorCount, 27)
  assert.equal(summary.comparableIndicatorCount, 25)
  assert.equal(summary.unavailableComparisonCount, 2)
  assert.equal(summary.advanceCount + summary.maintainCount, legal.length)
  assert.ok(legal.every(({ result }) => isComparableLegalDiagnosticResult(result)))
  assert.ok(tracking.every(({ result }) => isAvailableTrackingDiagnosticResult(result)))
  assert.deepEqual(
    [...legalIds].filter((id) => id.startsWith('saeb_')).toSorted(),
    [
      'saeb_matematica_anos_finais',
      'saeb_matematica_anos_iniciais',
      'saeb_matematica_ensino_medio',
      'saeb_portugues_anos_finais',
      'saeb_portugues_anos_iniciais',
      'saeb_portugues_ensino_medio',
    ],
  )
  for (const indicatorId of [
    'creche',
    'pre_escola',
    'basico_6_17',
    'adequacao_ai',
    'adequacao_af',
    'adequacao_em',
  ]) {
    assert.ok(legalIds.has(indicatorId), indicatorId)
  }
  for (const indicatorId of [
    'medio_tecnico_participacao_publica',
    'subsequente_expansao',
    'aee_oferta_escolas_elegiveis',
    'educacao_indigena_cobertura_estimada_4_17',
    'temporarios',
    'pos_graduacao',
    'superior_concluintes_oferta_local',
    'superior_docentes_mestres_doutores_sede',
    'capes_titulados_oferta_local',
    'cpc_cursos_oferta_local',
    'enade_licenciaturas_oferta_local',
  ]) {
    assert.equal(legalIds.has(indicatorId), false, indicatorId)
    assert.equal(trackingIds.has(indicatorId), false, indicatorId)
  }
})

test('São Leopoldo renders each diagnostic view without mixing modes or empty themes', async () => {
  const diagnostic = await readCurrentV3Municipality('4318705')
  const legal = selectDiagnosticResults(diagnostic)
  const tracking = selectDiagnosticResults(
    diagnostic,
    DIAGNOSTIC_RESULT_VIEWS.TRACKING,
  )
  const excluded = flatten(diagnostic).filter((result) => result.mode === 'complementary')
  const legalMarkup = renderViewModel(diagnostic, 'São Leopoldo')
  const trackingMarkup = renderViewModel(
    diagnostic,
    'São Leopoldo',
    DIAGNOSTIC_RESULT_VIEWS.TRACKING,
  )
  const legalText = visibleScreenText(legalMarkup)
  const trackingText = visibleScreenText(trackingMarkup)
  const legalThemes = selectDiagnosticThemeGroups(diagnostic)
  const trackingThemes = selectDiagnosticThemeGroups(diagnostic, {
    view: DIAGNOSTIC_RESULT_VIEWS.TRACKING,
  })

  assert.ok(legal.every(({ result }) => legalText.includes(result.publicName)))
  assert.ok(tracking.every(({ result }) => !legalText.includes(result.publicName)))
  assert.ok(tracking.every(({ result }) => trackingText.includes(result.publicName)))
  assert.ok(legal.every(({ result }) => !trackingText.includes(result.publicName)))
  assert.ok(excluded.every((result) => !legalText.includes(result.publicName)))
  assert.ok(excluded.every((result) => !trackingText.includes(result.publicName)))
  assert.deepEqual(
    legalThemes.map(({ theme }) => theme.visibleOrder),
    legalThemes.map((_, index) => index + 1),
  )
  assert.deepEqual(
    trackingThemes.map(({ theme }) => theme.visibleOrder),
    trackingThemes.map((_, index) => index + 1),
  )
  assert.ok(legalThemes.every(({ results }) => results.length > 0))
  assert.ok(trackingThemes.every(({ results }) => results.length > 0))
  assert.match(trackingText, /Na referência de acompanhamento/)
  assert.match(trackingText, /Abaixo da referência de acompanhamento/)
  assert.match(trackingText, /2 de 2 requisitos/)
  assert.match(trackingText, /Declarado/)
  assert.doesNotMatch(trackingText, /meta alcançada|cumprimento legal/i)
})

test('negative data states never become zero or below-reference results', () => {
  const comparable = {
    mode: 'progress',
    dataStatus: 'available',
    current: { value: 101.4, unit: 'percent' },
    indicatorReference: { value: 100 },
    distance: 1.4,
    classification: 'maintain',
  }
  const notApplicable = {
    ...comparable,
    dataStatus: 'not_applicable',
    current: { value: null, unit: 'percent' },
    classification: 'advance',
  }
  const suppressed = {
    ...notApplicable,
    dataStatus: 'suppressed',
  }
  const diagnostic = {
    goals: [{
      goalId: 'test',
      results: [comparable, notApplicable, suppressed],
    }],
  }
  const summary = selectLegalDiagnosticSummary(diagnostic)

  assert.equal(isComparableLegalDiagnosticResult(notApplicable), false)
  assert.equal(isComparableLegalDiagnosticResult(suppressed), false)
  assert.equal(summary.comparableIndicatorCount, 1)
  assert.equal(summary.maintainCount, 1)
  assert.equal(summary.advanceCount, 0)
  assert.equal(summary.unavailableComparisonCount, 2)
  assert.equal(getPublicCurrentValue(comparable), '101,4%')
})

test('default print report contains only comparable legal indicators', async () => {
  const diagnostic = await readCurrentV3Municipality('4318705')
  const markup = renderViewModel(
    diagnostic,
    'São Leopoldo',
    DIAGNOSTIC_RESULT_VIEWS.TRACKING,
  )
  const printText = visibleText(
    markup.slice(markup.indexOf('<article class="diagnostic-print-report"')),
  )
  const legal = selectDiagnosticResults(diagnostic)
  const excluded = flatten(diagnostic).filter(
    (result) => !isComparableLegalDiagnosticResult(result),
  )

  assert.ok(legal.every(({ result }) => printText.includes(result.publicName)))
  assert.ok(excluded.every((result) => !printText.includes(result.publicName)))
  assert.doesNotMatch(printText, /Referência de acompanhamento/)
  assert.match(printText, /Indicadores com comparação disponível 25/)
})

test('missing or incompatible canonical diagnostic renders only the operational error', () => {
  const text = visibleText(renderToStaticMarkup(createElement(DiagnosticPanel, {
    contractStatus: 'incompatible_version',
    data: { schemaVersion: 'municipal-diagnostic-v2' },
    municipio: 'Teste',
  })))
  assert.equal(text, 'Não foi possível abrir o diagnóstico agora. Tente novamente.')
})

test('route consumes only the canonical view model without frontend business-rule sources', async () => {
  const [
    panelSource,
    presentationSource,
    pageSource,
    printSource,
    pmeSource,
    workbookSource,
  ] = await Promise.all([
    readFile(new URL('../../src/components/DiagnosticPanel.jsx', import.meta.url), 'utf8'),
    readFile(new URL('../../src/features/diagnostic/diagnosticPresentation.js', import.meta.url), 'utf8'),
    readFile(new URL('../../src/pages/Diagnostico.jsx', import.meta.url), 'utf8'),
    readFile(new URL('../../src/components/DiagnosticPrintReport.jsx', import.meta.url), 'utf8'),
    readFile(new URL('../../src/features/education/pmeReferenceTableViewModel.ts', import.meta.url), 'utf8'),
    readFile(new URL('../../src/features/education/municipalTechnicalReportWorkbook.ts', import.meta.url), 'utf8'),
  ])
  const combined = `${panelSource}\n${presentationSource}\n${pageSource}`
  const resolvedConsumers = `${panelSource}\n${printSource}\n${pmeSource}\n${workbookSource}`

  assert.match(panelSource, /data\?\.pne2026PublicDiagnostic/)
  assert.doesNotMatch(panelSource, /pne2026PublicDiagnosticV2/)
  assert.doesNotMatch(combined, /pne2026PublicDiagnosticV2/)
  assert.doesNotMatch(combined, /analysis\.indicators|decisionSummary|attentionItems|preservedItems/)
  assert.doesNotMatch(combined, /DiagnosticFinancingSection|buildPublicFinancingItems|DF2/)
  assert.doesNotMatch(presentationSource, /favorableDifference\s*[+-]|performancePercentile/)
  assert.doesNotMatch(panelSource, /numeratorLabel|denominatorLabel/)
  assert.doesNotMatch(panelSource, /result\.numeratorField|result\.denominatorField/)
  assert.doesNotMatch(presentationSource, /\brelationshipType\b/)
  assert.doesNotMatch(
    resolvedConsumers,
    /\btracksGoal\b|\btracks_goal\b|\bhasDistance\b|\brelationshipType\b|\bpriorityOrder\b|\btier\b/,
  )
  assert.doesNotMatch(resolvedConsumers, /indicatorCatalog\.json|diagnostic_presentation_v2/)
})

test('read-only offline audit confirms all 497 historical V2 contracts and representative special values', async (t) => {
  const index = await readVersionedJson('public/data/municipios_index.json')
  const historicalPresentation = await readVersionedJson(
    'data_pipeline/src/data/pne2026_diagnostic_presentation_v2.json',
  )
  const historicalByPair = new Map(
    historicalPresentation.results.map((result) => {
      const relation = getPne2026Relation(result.goalId, result.indicatorId)
      return [
        `${result.goalId}:${result.indicatorId}`,
        {
          ...result,
          monitoringMode: relation?.legacyV2Mode
            ?? result.monitoringMode
            ?? relation?.mode
            ?? 'progress',
        },
      ]
    }),
  )
  const metrics = {
    contracts: 0,
    results: 0,
    advance: 0,
    maintain: 0,
    unclassified: 0,
    stateComparisons: 0,
    statewidePositions: 0,
    similarMunicipalities: 0,
    trajectories: 0,
    estimatedAchievementYears: 0,
    publicSupportingReadings: 0,
    negative: 0,
    above100: 0,
    duplicate: 0,
    rawResults: 0,
  }
  const visibleByMode = new Map()
  const visibleByRelationId = new Map()
  const hiddenRawByRelationId = new Map()
  const hiddenMunicipalitiesByRelationId = new Map()
  const rows = []

  for (const municipality of index.municipios) {
    const contract = await readContract(municipality.id_municipio)
    const rawDiagnostic = contract.pne2026PublicDiagnosticV2
    const rawResults = flatten(rawDiagnostic)
    const diagnostic = sanitizePne2026PublicDiagnostic({
      ...rawDiagnostic,
      goals: rawDiagnostic.goals.map((goal) => ({
        ...goal,
        results: goal.results.filter((result) => (
          historicalByPair.get(`${goal.goalId}:${result.indicatorId}`)
            ?.monitoringMode !== 'hidden'
        )),
      })),
    })
    assert.equal(
      diagnostic?.viewModelVersion,
      'pne2026-diagnostic-view-model-v1',
      municipality.slug,
    )
    const results = flatten(diagnostic)
    const progressResults = results.filter((result) => result.mode === 'progress')
    const ids = results.map((result) => result.indicatorId)
    const relationPairs = results.map((result) => `${result.goalId}:${result.indicatorId}`)
    const essentials = results.filter((result) => result.summaryPriority === 'essential')
      .toSorted((left, right) => left.displayOrder - right.displayOrder)
    assert.deepEqual(
      essentials.map((result) => result.displayOrder),
      essentials.map((result) => result.displayOrder).toSorted((left, right) => left - right),
      municipality.slug,
    )
    assert.equal(new Set(essentials.map((result) => result.displayOrder)).size, essentials.length)
    assert.equal(diagnostic.summary.advanceCount, progressResults.filter((result) => result.classification === 'advance').length)
    assert.equal(diagnostic.summary.maintainCount, progressResults.filter((result) => result.classification === 'maintain').length)
    assert.equal(diagnostic.summary.unclassifiedCount, progressResults.filter((result) => result.classification == null).length)
    assert.equal(
      diagnostic.summary.stateAboveOrNearCount,
      progressResults.filter((result) => ['above', 'near'].includes(result.stateComparison?.state)).length,
    )
    assert.equal(
      diagnostic.summary.stateBelowCount,
      progressResults.filter((result) => result.stateComparison?.state === 'below').length,
    )

    metrics.contracts += 1
    metrics.results += results.length
    metrics.rawResults += rawResults.length
    metrics.advance += diagnostic.summary.advanceCount
    metrics.maintain += diagnostic.summary.maintainCount
    metrics.unclassified += diagnostic.summary.unclassifiedCount
    metrics.stateComparisons += results.filter((result) => result.stateComparison).length
    metrics.statewidePositions += results.filter((result) => result.statewidePosition).length
    metrics.similarMunicipalities += results.filter((result) => result.similarMunicipalities).length
    metrics.trajectories += results.filter((result) => result.trajectory).length
    metrics.estimatedAchievementYears += results.filter(
      (result) => Number.isFinite(result.trajectory?.estimatedAchievementYear),
    ).length
    metrics.publicSupportingReadings += results.reduce(
      (total, result) => total + getPublicSupportingReadings(result).length,
      0,
    )
    metrics.negative += results.filter((result) => result.current.value < 0).length
    metrics.above100 += results.filter((result) => result.current.value > 100).length
    metrics.duplicate += relationPairs.length - new Set(relationPairs).size
    for (const result of results) {
      const relation = getPne2026Relation(result.goalId, result.indicatorId)
      assert.ok(relation, `${municipality.slug}:${result.goalId}:${result.indicatorId}`)
      assert.equal(relation.includeInDiagnostic, true)
      assert.notEqual(relation.mode, PNE_2026_RELATIONSHIP_MODES.HIDDEN)
      visibleByMode.set(relation.mode, (visibleByMode.get(relation.mode) ?? 0) + 1)
      visibleByRelationId.set(
        relation.relationId,
        (visibleByRelationId.get(relation.relationId) ?? 0) + 1,
      )
    }
    for (const result of rawResults) {
      const relation = getPne2026Relation(result.goalId, result.indicatorId)
      assert.ok(relation, `raw:${municipality.slug}:${result.goalId}:${result.indicatorId}`)
      const historical = historicalByPair.get(`${result.goalId}:${result.indicatorId}`)
      if (historical?.monitoringMode !== 'hidden') continue
      hiddenRawByRelationId.set(
        relation.relationId,
        (hiddenRawByRelationId.get(relation.relationId) ?? 0) + 1,
      )
      const municipalities = hiddenMunicipalitiesByRelationId.get(relation.relationId) ?? new Set()
      municipalities.add(municipality.id_municipio)
      hiddenMunicipalitiesByRelationId.set(relation.relationId, municipalities)
    }
    assert.ok(!ids.includes('rendimento_magisterio'), municipality.slug)
    assert.ok(!ids.includes('medio_tecnico_participacao_publica'), municipality.slug)
    assert.ok(!ids.includes('subsequente_expansao'), municipality.slug)
    for (const result of results.filter((item) => item.mode === 'complementary')) {
      assert.equal('classification' in result, false, `${municipality.slug}:${result.indicatorId}`)
      assert.equal('distance' in result, false, `${municipality.slug}:${result.indicatorId}`)
      assert.equal('trajectory' in result, false, `${municipality.slug}:${result.indicatorId}`)
    }
    rows.push({
      slug: municipality.slug,
      resultCount: results.length,
      essentialCount: essentials.length,
      unclassifiedCount: diagnostic.summary.unclassifiedCount,
      lacksRendimento: !ids.includes('rendimento_magisterio'),
    })
  }

  assert.equal(metrics.contracts, 497)
  assert.equal(metrics.duplicate, 0)
  assert.equal(metrics.results, 14617)
  assert.equal(metrics.above100, 412)
  assert.equal(Math.min(...rows.map((row) => row.resultCount)), 24)
  assert.equal(Math.max(...rows.map((row) => row.resultCount)), 30)
  assert.equal(visibleByMode.has(PNE_2026_RELATIONSHIP_MODES.HIDDEN), false)
  assert.ok(rows.every((row) => row.lacksRendimento))
  assert.ok(rows.every((row) => row.essentialCount <= 9))
  t.diagnostic(`methodology-audit=${JSON.stringify({
    contracts: metrics.contracts,
    previousAvailableResults: metrics.rawResults,
    visibleResults: metrics.results,
    above100: metrics.above100,
    minimumVisibleResults: Math.min(...rows.map((row) => row.resultCount)),
    maximumVisibleResults: Math.max(...rows.map((row) => row.resultCount)),
    duplicateGoalIndicatorMunicipality: metrics.duplicate,
    visibleByMode: Object.fromEntries([...visibleByMode].toSorted()),
    visibleByRelationId: Object.fromEntries([...visibleByRelationId].toSorted()),
    hiddenRawByRelationId: Object.fromEntries([...hiddenRawByRelationId].toSorted()),
    hiddenMunicipalityCountByRelationId: Object.fromEntries(
      [...hiddenMunicipalitiesByRelationId]
        .map(([relationId, municipalities]) => [relationId, municipalities.size])
        .toSorted(),
    ),
  })}`)
  t.diagnostic(`inspection-cases=${JSON.stringify({
    minimum: rows.find((row) => row.resultCount === Math.min(...rows.map((item) => item.resultCount)))?.slug,
    maximum: rows.find((row) => row.resultCount === Math.max(...rows.map((item) => item.resultCount)))?.slug,
    mostEssentials: rows.toSorted((a, b) => b.essentialCount - a.essentialCount)[0]?.slug,
    mostUnclassified: rows.toSorted((a, b) => b.unclassifiedCount - a.unclassifiedCount)[0]?.slug,
    withoutRendimento: rows.find((row) => row.lacksRendimento)?.slug,
  })}`)
})

test('diagnostic remains lazy and outside the initial payload', async () => {
  const [initialPayload, pageSource, routerSource] = await Promise.all([
    readVersionedJson('public/data/municipios/4300109/index.json'),
    readFile(new URL('../../src/pages/Diagnostico.jsx', import.meta.url), 'utf8'),
    readFile(new URL('../../src/app/AppPageRouter.tsx', import.meta.url), 'utf8'),
  ])
  assert.equal('diagnostico_v2' in initialPayload.pne_2026_2036, false)
  assert.match(pageSource, /useMunicipioDiagnostic\(idMunicipio\)/)
  assert.match(routerSource, /const LazyDiagnostico = lazy/)
})
