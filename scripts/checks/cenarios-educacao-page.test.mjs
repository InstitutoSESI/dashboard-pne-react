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
const vite = await createServer({
  appType: 'custom',
  cacheDir: path.join(repoRoot, '.tmp', 'vite-cache', 'cenarios-educacao-page-v3'),
  configFile: false,
  optimizeDeps: { noDiscovery: true },
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
  },
  plugins: [react()],
  publicDir: false,
  root: repoRoot,
  server: { middlewareMode: true, hmr: { port: 24713 } },
})
after(async () => vite.close())

const pageModule = await vite.ssrLoadModule('/src/features/cenarios-educacao/CenariosEducacaoPage.tsx')
const copyModule = await vite.ssrLoadModule('/src/features/cenarios-educacao/cenariosEducacaoPlainLanguage.ts')
const bundle = JSON.parse(await readFile(
  path.join(repoRoot, 'src/features/cenarios-educacao/generated/cenariosEducacaoValeDoSinos.json'),
  'utf8',
))
const summaryMarkup = renderToStaticMarkup(createElement(pageModule.CenariosEducacaoSummaryReport, {
  bundle,
  municipalityId: '4313375',
}))
const technicalMarkup = renderToStaticMarkup(createElement(pageModule.CenariosEducacaoReport, {
  bundle,
  municipalityId: '4313375',
}))
const css = await readFile(path.join(repoRoot, 'src/styles/cenarios-educacao.css'), 'utf8')
const pageSource = await readFile(
  path.join(repoRoot, 'src/features/cenarios-educacao/CenariosEducacaoPage.tsx'),
  'utf8',
)
const occurrences = (text, fragment) => text.split(fragment).length - 1
const visibleText = (markup) => markup
  .replace(/<[^>]*>/gu, ' ')
  .replace(/&[a-z0-9#]+;/giu, ' ')
  .replace(/\s+/gu, ' ')
  .trim()
const summaryText = visibleText(summaryMarkup)

test('resumo começa pelo objetivo e não ensina a metodologia', () => {
  assert.match(summaryMarkup, /data-page-kind="summary"/u)
  assert.match(summaryText, /Como Nova Santa Rita pode se preparar para mudanças na educação/u)
  assert.match(summaryText, /Estes quatro cenários não são previsões/u)
  assert.match(summaryText, /Antes de mudar vagas, cursos ou serviços/u)
  assert.doesNotMatch(summaryText, /Como ler esta página|Escolha uma para explorar|cinco perguntas/iu)
  assert.equal(occurrences(summaryMarkup, '<details'), 0)
  assert.equal(occurrences(summaryMarkup, 'class="ce-page-nav"'), 0)
})

test('percurso principal tem somente três seções, três decisões, quatro futuros e três sinais', () => {
  assert.equal(occurrences(summaryMarkup, 'class="ce-simple-section"'), 3)
  assert.equal(occurrences(summaryMarkup, 'data-decision-priority="'), 3)
  assert.equal(occurrences(summaryMarkup, 'ce-scenario-card ce-scenario-card--'), 4)
  assert.equal(occurrences(summaryMarkup, 'aria-pressed="'), 4)
  assert.equal(occurrences(summaryMarkup, 'data-scenario-domain="'), 6)
  assert.equal(occurrences(summaryMarkup, 'data-public-signal="'), 3)
  assert.deepEqual([
    'Três decisões para tomar com mais segurança',
    'Escolha um cenário para entender melhor',
    'Três informações públicas para revisar todo ano',
  ].map((heading) => summaryText.includes(heading)), [true, true, true])
  for (const decision of copyModule.SIMPLE_DECISION_PRIORITIES) {
    assert.ok(summaryText.includes(decision.title), decision.id)
    assert.ok(summaryText.includes(decision.explanation), decision.id)
  }
})

test('quatro cenários recuperam os títulos e a exploração estratégica anterior', () => {
  for (const scenario of bundle.scenarios) {
    const copy = copyModule.SCENARIO_PLAIN_LANGUAGE[scenario.scenarioId]
    assert.ok(copy, scenario.scenarioId)
    assert.ok(summaryText.includes(scenario.title), scenario.title)
    assert.ok(summaryText.includes(copy.summary), scenario.scenarioId)
  }
  const selectedCopy = copyModule.SCENARIO_PLAIN_LANGUAGE[bundle.scenarios[0].scenarioId]
  for (const statement of [
    ...selectedCopy.steps,
    ...selectedCopy.opportunities,
    ...selectedCopy.risks,
    ...selectedCopy.difficultChoices,
  ]) {
    assert.ok(summaryText.includes(statement), statement)
  }
  assert.match(summaryText, /Como este cenário pode se desenvolver/u)
  assert.match(summaryText, /O que pode ajudar/u)
  assert.match(summaryText, /O que pode dificultar/u)
  assert.match(summaryText, /Escolhas difíceis/u)
  assert.match(summaryText, /O que muda em seis áreas da educação/u)
})

test('somente sinais públicos disponíveis aparecem e lacunas continuam explícitas', () => {
  const byId = new Map(bundle.sentinelIndicators.map((indicator) => [indicator.indicatorId, indicator]))
  assert.equal(copyModule.SIMPLE_PUBLIC_SIGNALS.length, 3)
  for (const signal of copyModule.SIMPLE_PUBLIC_SIGNALS) {
    const indicator = byId.get(signal.indicatorId)
    assert.ok(indicator, signal.indicatorId)
    assert.ok(['calculated', 'observed'].includes(indicator.availability), signal.indicatorId)
    assert.ok(summaryText.includes(signal.title), signal.title)
    assert.ok(summaryText.includes(signal.decisionUse), signal.decisionUse)
  }
  assert.equal(bundle.sentinelIndicators.filter((indicator) => (
    indicator.availability === 'calculated' || indicator.availability === 'observed'
  )).length, 3)
  assert.ok(summaryText.includes(copyModule.SIMPLE_PUBLIC_DATA_GAP))
  assert.match(summaryText, /dias letivos interrompidos/u)
  assert.match(summaryText, /desconhecidas, não como estimativas/u)
})

test('resumo mantém linguagem comum e deixa matrizes e método na consulta técnica', () => {
  assert.doesNotMatch(summaryText, /\b(?:PNE|MDE|EJA|EPT|AEE)\b/u)
  assert.doesNotMatch(
    summaryText,
    /foresight|campo morfológico|distância morfológica|constructo|lock-in|stress-test|gate técnico|proveniência|SHA-256|hash|trade-?off|gatilho|sentinela|checkpoint/iu,
  )
  assert.equal(occurrences(summaryMarkup, 'class="ce-domain-card"'), 6)
  for (const retiredClass of [
    'ce-driver-card',
    'ce-scenario-technical-details',
    'ce-distribution-details',
    'ce-pne-matrix',
    'ce-action-group',
    'ce-sentinel-card',
    'ce-method-details',
  ]) assert.ok(!summaryMarkup.includes(retiredClass), retiredClass)
  assert.doesNotMatch(summaryText, /diminuiu em 64|aumentaram em 17|3,2%|de 309 para 152/iu)
})

test('links separam diagnóstico, metas e consulta técnica', () => {
  assert.equal(occurrences(summaryMarkup, 'class="ce-simple-links"'), 1)
  assert.match(summaryMarkup, /href="#vocacoes-regiao"/u)
  assert.match(summaryMarkup, /href="#pne2026"/u)
  assert.match(summaryMarkup, /href="#cenarios-da-educacao-dados"/u)
  assert.match(summaryText, /Ver os números atuais/u)
  assert.match(summaryText, /Acompanhar as metas/u)
  assert.match(summaryText, /Conferir fontes e construção dos futuros/u)
})

test('consulta técnica preserva cenários completos, ações, sinais e fontes', () => {
  assert.match(technicalMarkup, /data-page-kind="technical"/u)
  assert.match(technicalMarkup, /Dados e critérios da análise/u)
  assert.match(technicalMarkup, /href="#cenarios-da-educacao"/u)
  assert.equal(occurrences(technicalMarkup, 'data-driver-maturity="'), 4)
  assert.equal(occurrences(technicalMarkup, 'ce-scenario-card ce-scenario-card--'), 4)
  assert.equal(occurrences(technicalMarkup, 'data-scenario-domain="'), 6)
  assert.equal(occurrences(technicalMarkup, 'class="ce-action-group"'), 3)
  assert.equal(occurrences(technicalMarkup, 'class="ce-sentinel-card ce-sentinel-card--'), 12)
  for (const action of bundle.actions) assert.ok(technicalMarkup.includes(action.title), action.actionId)
  assert.match(technicalMarkup, new RegExp(bundle.sourceSnapshot.regionalPublicInputs.sha256, 'u'))
  assert.match(technicalMarkup, /30 arquivos: 10 educacionais, 10 financeiros e 10 matrizes do PNE/u)
})

test('estilos e estados de carregamento cobrem resumo e consulta técnica', () => {
  for (const className of [
    '.ce-simple-main',
    '.ce-simple-decision-grid',
    '.ce-scenario-grid',
    '.ce-scenario-detail',
    '.ce-causal-chain',
    '.ce-balance-grid',
    '.ce-domain-grid',
    '.ce-simple-signal-grid',
    '.ce-simple-data-gap',
    '.ce-simple-links',
    '.ce-technical-return',
  ]) assert.ok(css.includes(className), className)
  assert.ok(pageSource.includes('Preparando o resumo para decisão'))
  assert.ok(pageSource.includes('Não foi possível preparar este resumo'))
  assert.ok(pageSource.includes('Preparando dados e critérios da análise'))
  assert.ok(pageSource.includes('Não foi possível conferir os dados e critérios'))
  assert.doesNotMatch(summaryText, /Novo Hamburgo|contraste entre municípios|oficina humana/iu)
})
