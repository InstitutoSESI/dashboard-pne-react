import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import path from 'node:path'
import test, { after } from 'node:test'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import react from '@vitejs/plugin-react'
import { createServer } from 'vite'


const repoRoot = path.resolve(import.meta.dirname, '..', '..')
const activeStateConfig = {
  schemaVersion: 'state-config-v1',
  stateCode: 'RS',
  stateName: 'Rio Grande do Sul',
  stateNameForms: {
    nominative: 'Rio Grande do Sul',
    withDe: 'do Rio Grande do Sul',
    withCom: 'com o Rio Grande do Sul',
  },
  municipalityIbgePrefix: '43',
  expectedMunicipalityCount: 497,
  locale: 'pt-BR',
}

function createTestServer(enabled) {
  return createServer({
    appType: 'custom',
    configFile: false,
    define: {
      __ACTIVE_PUBLICATION_CONFIG__: JSON.stringify({
        schemaVersion: 'state-publication-v3',
        stateCode: 'RS',
        analyticsStatus: 'complete',
        analyticsMessage: null,
        enabledProducts: null,
      }),
      __ACTIVE_REGIONS_CONFIG__: 'null',
      __ACTIVE_STATE_CONFIG__: JSON.stringify(activeStateConfig),
      'import.meta.env.VITE_ENABLE_VOCACOES_PNE_INTERNAL': JSON.stringify(enabled ? 'true' : 'false'),
    },
    plugins: [react()],
    publicDir: false,
    root: repoRoot,
    server: { middlewareMode: true, hmr: false },
  })
}

const vite = await createTestServer(false)

after(async () => vite.close())

const [coreRaw, seriesRaw, technicalRaw, insightsRaw] = await Promise.all([
  readFile(path.join(repoRoot, 'src/features/vocacoes-pne-internal/generated/vocacoesPneJob5iCore.json'), 'utf8').then(JSON.parse),
  readFile(path.join(repoRoot, 'src/features/vocacoes-pne-internal/generated/vocacoesPneJob5iSeries.json'), 'utf8').then(JSON.parse),
  readFile(path.join(repoRoot, 'src/features/vocacoes-pne-internal/generated/vocacoesPneJob5iTechnical.json'), 'utf8').then(JSON.parse),
  readFile(path.join(repoRoot, 'src/features/vocacoes-pne-internal/generated/vocacoesPneJob5kStories.json'), 'utf8').then(JSON.parse),
])

const [runtime, job5kRuntime, pageModule, contextModule, languageModule, routes, flagModule, visualModule, managerReviewModule] = await Promise.all([
  vite.ssrLoadModule('/src/features/vocacoes-pne-internal/vocacoesPneUiV2Runtime.ts'),
  vite.ssrLoadModule('/src/features/vocacoes-pne-internal/vocacoesPneJob5kRuntime.ts'),
  vite.ssrLoadModule('/src/features/vocacoes-pne-internal/VocacoesPneInternalPage.tsx'),
  vite.ssrLoadModule('/src/context/MunicipalityContext.tsx'),
  vite.ssrLoadModule('/src/features/vocacoes-pne-internal/vocacoesPneLanguageLinter.ts'),
  vite.ssrLoadModule('/src/app/appRoutes.ts'),
  vite.ssrLoadModule('/src/config/vocacoesPneInternalFlag.ts'),
  vite.ssrLoadModule('/src/features/vocacoes-pne-internal/components/VocacoesPneVisuals.tsx'),
  vite.ssrLoadModule('/src/features/vocacoes-pne-internal/vocacoesPneManagerReviewModel.ts'),
])

const core = runtime.parseVocacoesPneCore(coreRaw)
const seriesBundle = runtime.parseVocacoesPneSeriesBundle(seriesRaw)
const technical = runtime.parseVocacoesPneTechnicalBundle(technicalRaw)
const insights = job5kRuntime.parseVocacoesPneJob5K(insightsRaw)
const bundle = { core, series: seriesBundle.series, insights }

function renderPage() {
  return renderToStaticMarkup(createElement(
    contextModule.MunicipalityProvider,
    { municipalities: core.municipalities },
    createElement(pageModule.InternalPageContent, { bundle }),
  ))
}

function occurrences(text, fragment) {
  return text.split(fragment).length - 1
}

test('runtime V2 valida núcleo, séries e camada técnica fechados', () => {
  assert.equal(core.families.length, 13)
  assert.equal(core.macroblocks.length, 7)
  assert.equal(core.municipalities.length, 10)
  assert.equal(core.variants.length, 143)
  assert.equal(seriesBundle.series.length, 832)
  assert.equal(seriesBundle.series.reduce((sum, item) => sum + item.points.length, 0), 7284)
  assert.equal(technical.technicalEvidence.c1C12.length, 156)
  assert.equal(technical.technicalEvidence.visibleByDefault, false)
  assert.equal(technical.technicalEvidence.printedForManager, false)
  assert.equal(technical.technicalEvidence.rawCagedDetailExposed, false)
  assert.equal(insights.stories.length, 4)
  assert.equal(insights.stories.reduce((sum, story) => sum + story.selected_municipality_read.variants.length, 0), 44)
})

test('runtime V2 falha fechado para propriedade extra, escala duplicada e zero adulterado', () => {
  const extra = structuredClone(coreRaw)
  extra.unexpected = true
  assert.throws(() => runtime.parseVocacoesPneCore(extra), /propriedades inesperadas/u)

  const scale = structuredClone(seriesRaw)
  const percentPoint = scale.series.find((item) => item.unit === 'percent').points.find((point) => point.value !== null)
  percentPoint.displayValue *= 100
  percentPoint.value = percentPoint.displayValue
  assert.throws(() => runtime.parseVocacoesPneSeriesBundle(scale), /percentual|escala/u)

  const zero = structuredClone(seriesRaw)
  const zeroPoint = zero.series.flatMap((item) => item.points).find((point) => point.availabilityState === 'observed_zero')
  zeroPoint.value = 1
  assert.throws(() => runtime.parseVocacoesPneSeriesBundle(zero), /zero observado/u)
})

test('rota interna depende da flag e não é alias público', () => {
  assert.equal(routes.resolveActivePageFromHash('#vocacoes-pne-interno'), 'home')
  assert.equal(routes.resolveActivePageFromHash('#vocacoes-pne-internal'), 'home')
  assert.equal(flagModule.resolveVocacoesPneInternalEnabled(undefined), false)
  assert.equal(flagModule.resolveVocacoesPneInternalPage('vocacoespneinterno', true), 'vocacoes-pne-internal')
  assert.equal(flagModule.resolveVocacoesPneInternalPage('vocacoespneinterno', false), null)
  assert.equal(flagModule.resolveVocacoesPneInternalPage('vocacoespneinternal', true), null)
})

test('página da gestora fecha duas direções em quatro relações e três agendas', () => {
  const html = renderPage()
  assert.match(html, /Página piloto para validação com a gestora — ainda não publicada/u)
  assert.match(html, /Nova Santa Rita: educação, território e próximos anos/u)
  assert.equal(occurrences(html, 'class="vpm-direction"'), 2)
  assert.equal(occurrences(html, 'class="vpm-card"'), 7)
  assert.equal(occurrences(html, 'class="vpm-priority"'), 3)
  assert.equal(occurrences(html, 'data-main-visual='), 7)
  assert.equal(occurrences(html, 'class="vpi-macroblock"'), 7)
  assert.equal(occurrences(html, 'data-macroblock-id='), 7)
  assert.match(html, /data-job="manager-review-v1"/u)
  assert.match(html, /data-publication="closed"/u)
  assert.doesNotMatch(html, />Gate(?: 11)?</u)
  assert.doesNotMatch(html, /class="vpi-technical"/u)
})

test('fallback vem do bundle e reconstrói Nova Santa Rita sem texto manual por município', () => {
  const html = renderPage()
  assert.equal(core.fallbackMunicipalityIbgeCode, '4313375')
  assert.equal(insights.fallback_municipality_ibge_code, '4313375')
  assert.match(html, /O que os dados colocam na agenda de Nova Santa Rita/u)
  for (const anchor of [
    '759 → 848',
    '459 → 823',
    '799 → 840',
    '309 → 208',
    '104 → 172',
    '1.117 → 1.638',
    '17 → 722',
    '174 de 219 eventos',
  ]) {
    assert.ok(html.includes(anchor), anchor)
  }
  assert.match(html, /EPT localizada[\s\S]*0 → 0/iu)
  assert.match(html, /A leitura não atribui automaticamente uma mudança à outra/u)
})

test('modelo municipal preserva identidade textual, evidências e responsabilidades', () => {
  const model = managerReviewModule.buildVocacoesPneManagerReviewModel(bundle, '4313375', 'Nova Santa Rita')
  assert.equal(model.entityId, '4313375')
  assert.equal(typeof model.entityId, 'string')
  assert.equal(model.isRegion, false)
  assert.equal(model.priorities.length, 3)
  assert.deepEqual(model.directions.map((direction) => direction.cards.length), [4, 3])
  assert.deepEqual(model.directions[0].cards.map((card) => card.id), [
    'relacao-coortes-oferta',
    'relacao-trajetoria-mobilidade',
    'relacao-trabalho-juvenil-ensino-medio',
    'relacao-eja-escolaridade-adulta',
  ])
  assert.deepEqual(model.directions[1].cards.map((card) => card.id), [
    'agenda-coortes-capacidade',
    'agenda-trabalho-aprendizagem',
    'agenda-ocupacoes-formacao',
  ])
  for (const card of model.directions.flatMap((direction) => direction.cards)) {
    assert.ok(card.educationEvidence.length > 0, card.id)
    assert.ok(card.territoryEvidence.length > 0, card.id)
    assert.ok(card.sourceRefs.length > 0, card.id)
    assert.ok(card.responsibility.length > 0, card.id)
    assert.ok(card.monitoringIndicators.length > 0, card.id)
  }
})

test('contexto regional, comparação e estados ficam visíveis no HTML sem taxa regional inventada', () => {
  const html = renderPage()
  assert.match(html, /Contexto sempre visível/u)
  assert.match(html, /Distribuição dos dez municípios/u)
  assert.match(html, /Mediana dos dez municípios/u)
  assert.match(html, /Distribuição municipal do RS/iu)
  assert.match(html, /Indisponível na fonte congelada/u)
  assert.doesNotMatch(html, /taxa do Vale/iu)
  assert.doesNotMatch(html, /dependência administrativa[^<]{0,80}(?:comparação|estrato)/iu)
})

test('componentes de disponibilidade distinguem zero, ausência, supressão e não aplicabilidade', () => {
  const states = [
    ['observed', 12],
    ['observed_zero', 0],
    ['unavailable', null],
    ['not_applicable', null],
    ['suppressed', null],
  ]
  const html = renderToStaticMarkup(createElement(
    'div',
    null,
    ...states.map(([state, value]) => createElement(visualModule.AvailabilityValue, {
      key: state,
      state,
      value,
      unit: 'count',
    })),
  ))
  assert.match(html, /Zero observado/u)
  assert.match(html, /Indisponível na fonte congelada/u)
  assert.match(html, /Não aplicável/u)
  assert.match(html, /Valor suprimido/u)
})

test('linter bloqueia todas as expressões vedadas e aceita o texto visível compilado', () => {
  const blocked = [
    'município receptor',
    'corredor origem-destino',
    'rota inferida',
    'PNATE executado em 2026',
    'vaga de aprendiz',
    'alunos abandonam para trabalhar',
    'faltam cursos',
    'demanda por curso',
    'déficit de profissionais',
    'profissões do futuro',
    'ranking municipal',
    'taxa do Vale',
    'causalidade',
    'PNE_6',
    'PME_tema',
    'a mobilidade não explica o abandono',
    'não há relação entre trabalho e escola',
    'déficit de oferta',
    'shift-share',
    'Gate 11',
  ]
  for (const value of blocked) {
    assert.ok(languageModule.lintVocacoesPnePrototypeText(value).length > 0, value)
  }
  const visibleBundleText = [
    ...core.directions.flatMap((item) => [item.title, item.summary]),
    ...core.macroblocks.flatMap((item) => [item.title, item.summary, item.primaryQuestion]),
    ...core.visualContracts.flatMap((item) => [item.title, item.measure, item.comparisonRule, item.tooltip]),
    ...insights.stories.flatMap((story) => [
      story.title_conclusion,
      story.integrated_summary,
      story.regional_read,
      story.planning_implication,
      story.interpretation_boundary,
      ...story.selected_municipality_read.variants.flatMap((variant) => [variant.title_conclusion, variant.integrated_summary, variant.selected_municipality_read]),
    ]),
    ...insights.conditional_contexts.flatMap((context) => context.variants.flatMap((variant) => [variant.title, variant.summary])),
  ]
  assert.doesNotThrow(() => languageModule.assertVocacoesPnePrototypeLanguage(visibleBundleText))
})

test('cada contrato visual declara medida, unidade, período, fonte, lente e fallbacks', () => {
  assert.equal(core.visualContracts.length, 7)
  for (const contract of core.visualContracts) {
    for (const field of [
      'title', 'measure', 'unit', 'period', 'comparisonRule', 'tooltip',
      'zeroState', 'absentState', 'mobileFallback', 'printBehavior',
    ]) {
      assert.equal(typeof contract[field], 'string', `${contract.visualContractId}.${field}`)
      assert.ok(contract[field].length > 0, `${contract.visualContractId}.${field}`)
    }
    assert.ok(contract.sourceRefs.length > 0)
    assert.ok(contract.territorialLenses.length > 0)
  }
})

test('bundle React é normalizado e não importa o corpus Job 5H de 4 MB', async () => {
  const hookSource = await readFile(
    path.join(repoRoot, 'src/features/vocacoes-pne-internal/useVocacoesPneInternalBundle.ts'),
    'utf8',
  )
  const navigationSource = await readFile(path.join(repoRoot, 'src/app/navigationRegistry.ts'), 'utf8')
  assert.match(hookSource, /import\('\.\/generated\/vocacoesPneJob5iCore\.json'\)/u)
  assert.match(hookSource, /import\('\.\/generated\/vocacoesPneJob5iSeries\.json'\)/u)
  assert.match(hookSource, /import\('\.\/generated\/vocacoesPneJob5iTechnical\.json'\)/u)
  assert.match(hookSource, /import\('\.\/generated\/vocacoesPneJob5kStories\.json'\)/u)
  assert.doesNotMatch(hookSource, /CORPUS_VARIANTES_TERRITORIAIS_JOB5H/u)
  assert.doesNotMatch(navigationSource, /vocacoes-pne-internal|vocacoes-pne-interno/u)
})
