import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test, { after } from 'node:test'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { createServer } from 'vite'

const municipalUrl = new URL(
  '../../public/data/pne2026-matriz/municipios/4313375.json',
  import.meta.url,
)
const matriz = JSON.parse(await readFile(municipalUrl, 'utf8'))
const educationUrl = new URL(
  '../../public/data/educacao/municipios/4313375.json',
  import.meta.url,
)
const educationDocument = JSON.parse(await readFile(educationUrl, 'utf8'))
const matrizCss = await readFile(
  new URL('../../src/styles/matriz-page.css', import.meta.url),
  'utf8',
)
const vite = await createServer({
  appType: 'custom',
  logLevel: 'silent',
  optimizeDeps: { include: [], noDiscovery: true },
  publicDir: false,
  server: { hmr: false, middlewareMode: true, watch: null },
})
const { LoadedMatrizPage } = await vite.ssrLoadModule(
  '/src/features/matriz/MatrizPage.tsx',
)
const {
  MATRIZ_FRENTES,
  matrizFrenteKey,
  resolveMatrizFrentes,
} = await vite.ssrLoadModule('/src/features/matriz/matrizFrentes.ts')
const {
  MATRIZ_GOAL_INSIGHTS,
  resolveMatrizGoalInsight,
} = await vite.ssrLoadModule('/src/features/matriz/matrizInsights.ts')
const {
  buildMatrizEducationContext,
} = await vite.ssrLoadModule('/src/features/matriz/matrizEducationContext.ts')
const educationContext = buildMatrizEducationContext(educationDocument)
const { buildMatrizFrentesWorkbook } = await vite.ssrLoadModule(
  '/src/features/matriz/matrizFrentesWorkbook.ts',
)
const {
  MATRIZ_FRONTS_LEGACY_KEY_PREFIX_V3,
  MATRIZ_FRONTS_LEGACY_SCHEMA_VERSION_V3,
  MATRIZ_FRONTS_LEGACY_KEY_PREFIX_V4,
  MATRIZ_FRONTS_LEGACY_SCHEMA_VERSION_V4,
  MATRIZ_FRONTS_SCHEMA_VERSION,
  MATRIZ_FRONTS_STORAGE_KEY_PREFIX,
  findPreviousMatrizPlan,
  parseMatrizPlan,
  persistMatrizPlan,
  reconcileMatrizPlanEntries,
  restoreMatrizPlan,
  serializeMatrizPlan,
} = await vite.ssrLoadModule('/src/domain/matrizFrontsStorage.ts')
const {
  formatMatrizGoalSituation,
  MATRIZ_DISTANCE_LABEL,
  MATRIZ_PEER_DEVIATION_LABEL,
  MATRIZ_SEVERITY_LABEL,
  MATRIZ_TREND_LABEL,
  matrizPeerBenchmarkComparison,
  matrizPriorityPeerSummary,
  resolveMatrizContextReadings,
} = await vite.ssrLoadModule('/src/features/matriz/matrizVocabulary.ts')

after(async () => {
  await vite.close()
})

function renderMatriz(document = matriz) {
  return renderToStaticMarkup(createElement(LoadedMatrizPage, { educationContext, matriz: document }))
}

function buildV3PresentationFixture() {
  const document = structuredClone(matriz)
  document.schemaVersion = 'matriz-3.0.0'
  for (const goal of document.priorityGoals) {
    delete goal.trend
    delete goal.networkConcentration
    for (const cause of goal.causes) {
      if (cause.proof) delete cause.proof.peerBenchmark
      for (const signal of cause.collapsed.signals) delete signal.peerBenchmark
    }
  }
  return document
}

function buildV4PresentationFixture() {
  const document = buildV3PresentationFixture()
  document.schemaVersion = 'matriz-4.0.0'
  const goal = document.priorityGoals.find((candidate) => candidate.goalId === '4.b')
  assert.ok(goal)
  const signal = goal.causes
    .flatMap((cause) => cause.collapsed.signals)
    .find((candidate) => (
      candidate.measureId === 'inep.tdi.fun_ai'
      && candidate.dimensions === 'dependencia=total;localizacao=total'
    ))
  assert.ok(signal)
  goal.trend = {
    previousValueRaw: '91',
    previousYear: '2024',
    direction: 'improved',
  }
  goal.networkConcentration = {
    measureId: signal.measureId,
    classification: 'concentrated_in_few_schools',
    affectedSchools: 3,
    totalSchools: 21,
  }
  signal.peerBenchmark = {
    statistic: 'median',
    valueRaw: '6.8',
    differenceRaw: '1',
    unit: signal.unit,
    year: signal.period,
    n: 88,
  }
  return document
}

function allDocumentMeasureIds() {
  return [...new Set(matriz.priorityGoals.flatMap((goal) => (
    goal.causes.flatMap((cause) => [
      cause.proof?.measureId,
      ...cause.collapsed.signals.map((signal) => signal.measureId),
    ])
  )).filter(Boolean))]
}

function allDocumentFactorIds() {
  return matriz.priorityGoals.flatMap((goal) => goal.causes.map((cause) => cause.factorId))
}

function assertPublicLanguage(html) {
  const forbiddenFragments = [
    'factorId',
    'measureId',
    'maxInference',
    'placementRationale',
    'goalId',
    'dimensions',
    'cobrade=',
    'declared_existence_only',
    'measured_value_within_source_scope',
    'known_cases_or_events_only',
    'contextual_association_only',
    ...allDocumentFactorIds(),
    ...allDocumentMeasureIds(),
    ...matriz.priorityGoals.map((goal) => goal.severity.placementRationale),
    'O que pode estar segurando',
    'Sem sinal público',
    'Primeiro passo para verificação',
    'Perguntas para a oficina',
    'Possível causa',
    'Outras causas possíveis',
    'Fora do alcance municipal',
    'a prefeitura pode agir',
    'depende de outras esferas',
  ].filter(Boolean)
  const leaked = [...new Set(forbiddenFragments.filter((fragment) => html.includes(fragment)))]

  assert.deepEqual(leaked, [], `Termos técnicos vazaram no HTML:\n${leaked.join('\n')}`)
  assert.doesNotMatch(html, /causa/iu)
  assert.doesNotMatch(html, /oficina/iu)
  assert.doesNotMatch(html, /quadrante/iu)
  assert.doesNotMatch(html, /parceir/iu)
  assert.doesNotMatch(html, /evid[êe]ncia insuficiente/iu)
  assert.doesNotMatch(html, /n[ãa]o [ée] poss[íi]vel verificar/iu)
}

test('vocabulário público preserva distância, desvio entre pares e gravidade', () => {
  assert.deepEqual(MATRIZ_DISTANCE_LABEL, {
    far_from_target: 'longe da referência',
    below_target: 'abaixo da referência',
    near_or_at_target: 'na referência ou perto dela',
  })
  assert.deepEqual(MATRIZ_PEER_DEVIATION_LABEL, {
    much_worse_than_peers: 'entre as que mais precisam avançar das cidades parecidas',
    worse_than_peers: 'abaixo da maioria das cidades parecidas',
    in_line_with_peers: 'na média das cidades parecidas',
    better_than_peers: 'acima da maioria das cidades parecidas',
  })
  assert.deepEqual(MATRIZ_SEVERITY_LABEL, {
    high: 'atenção maior',
    medium: 'atenção',
  })
  assert.deepEqual(MATRIZ_TREND_LABEL, {
    improved: 'avançou desde a leitura anterior',
    worsened: 'recuou desde a leitura anterior',
    stable: 'estável desde a leitura anterior',
  })
})

test('o contrato 4.0.0 renderiza trajetória, leitura da rede e mediana da medida em linguagem pública', () => {
  const document = buildV4PresentationFixture()
  const html = renderMatriz(document)

  assert.ok(html.includes('Na leitura de 2024: 91% · hoje: 92,2% — avançou desde a leitura anterior.'))
  assert.ok(html.includes('Distorção idade-série — anos iniciais: concentrada em poucas escolas da rede (3 de 21).'))
  assert.ok(html.includes('Mediana das 88 cidades parecidas (2025): 6,8% · município 1 p.p. acima.'))
  assert.ok(html.includes('A posição diante da mediana indica se o atraso escolar exige atenção adicional e orienta o acompanhamento por escola, turma e trajetória.'))
  for (const rawVocabulary of [
    'improved',
    'worsened',
    'stable',
    'concentrated_in_few_schools',
    'spread_across_network',
  ]) {
    assert.equal(html.includes(rawVocabulary), false, rawVocabulary)
  }
  assertPublicLanguage(html)
})

test('a página real 4.0.0 renderiza as medianas publicadas nas medidas com uso editorial', () => {
  const html = renderMatriz()
  const peerReadings = Object.values(MATRIZ_GOAL_INSIGHTS)
    .flatMap((insight) => insight.mechanisms)
    .flatMap((mechanism) => mechanism.measure ? [mechanism.measure] : [])
    .map((context) => resolveMatrizContextReadings(matriz, [context])[0])
    .filter((reading) => reading?.peerBenchmarkComparison && reading.peerUse)

  assert.equal(peerReadings.length, 4)
  assert.equal((html.match(/Mediana das/gu) ?? []).length, peerReadings.length)
  for (const reading of peerReadings) {
    assert.ok(
      html.includes(`${reading.peerBenchmarkComparison}. ${reading.peerUse}`),
      reading.label,
    )
  }
  assertPublicLanguage(html)
})

test('a fixture 3.0.0 preservada não cria elementos nem mensagens para campos 4.0.0 ausentes', () => {
  const html = renderMatriz(buildV3PresentationFixture())

  assert.equal(html.includes('matriz-goal__trend'), false)
  assert.equal(html.includes('matriz-goal__network'), false)
  assert.equal(html.includes('Mediana das'), false)
  assert.equal(html.includes('leitura anterior indisponível'), false)
  assert.equal(html.includes('concentração da rede indisponível'), false)
  assert.equal(html.includes('comparação da medida indisponível'), false)
})

test('cada meta prioritária recebe exatamente dois caminhos ligados à leitura', () => {
  const expectedStartHereByGoal = {
    '1.a': 'procura-por-vaga',
    '5.a': 'avaliar-e-recompor',
    '11.c': 'eja-compativel-com-trabalho',
    '17.a': 'formacao-na-area-de-atuacao',
    '4.a': 'encontrar-quem-esta-fora',
    '4.b': 'alfabetizar-na-idade-certa',
    '19.c': 'acessibilidade-das-escolas',
  }
  const seenIds = new Set()
  let total = 0
  let bridgeCount = 0

  for (const goal of matriz.priorityGoals) {
    const fronts = MATRIZ_FRENTES[goal.goalId]
    const insight = resolveMatrizGoalInsight(goal.goalId)
    assert.ok(fronts, goal.goalId)
    assert.ok(insight, goal.goalId)
    assert.equal(fronts.length, 2, goal.goalId)
    assert.deepEqual(resolveMatrizFrentes(goal.goalId), fronts)
    const startHereFronts = fronts.filter((front) => front.startHere === true)
    assert.equal(startHereFronts.length, 1, goal.goalId)
    assert.equal(startHereFronts[0].id, expectedStartHereByGoal[goal.goalId], goal.goalId)
    total += fronts.length

    for (const front of fronts) {
      assert.ok(front.mechanismId.trim(), `${goal.goalId}|${front.id}`)
      assert.ok(
        insight.mechanisms.some((mechanism) => mechanism.id === front.mechanismId),
        `${goal.goalId}|${front.id}`,
      )
      assert.ok(front.steps.length >= 2 && front.steps.length <= 3, front.id)
      assert.ok(front.implementationMilestone.trim(), front.id)
      assert.ok(front.implementationMilestone.length <= 160, front.id)
      assert.match(front.implementationMilestone, /\.$/u, front.id)
      assert.ok(front.programs.length >= 1, front.id)
      assert.ok(front.legalRef.startsWith('PNE 2026–2036'), front.legalRef)
      assert.equal(seenIds.has(front.id), false, front.id)
      seenIds.add(front.id)
      for (const program of front.programs) {
        assert.ok(program.name.trim(), front.id)
        assert.ok(program.description.trim(), front.id)
        if (program.url) assert.ok(program.url.startsWith('https://'), program.url)
      }
      if (front.bridge) {
        bridgeCount += 1
        assert.equal(front.bridge.page, 'educacao')
        assert.ok(front.bridge.label.trim(), front.id)
        assert.ok(front.bridge.params?.secao, front.id)
        assert.equal(Object.keys(front.bridge.params ?? {}).length, 1, front.id)
      }
    }
    assert.deepEqual(
      fronts.map((front) => front.mechanismId).sort(),
      insight.mechanisms.map((mechanism) => mechanism.id).sort(),
      goal.goalId,
    )
  }

  assert.equal(total, 14)
  assert.equal(seenIds.size, 14)
  assert.equal(bridgeCount, 13)
})

test('cada meta recebe uma leitura curta com exatamente dois pontos verificáveis', () => {
  const goalIds = matriz.priorityGoals.map((goal) => goal.goalId).sort()
  assert.deepEqual(Object.keys(MATRIZ_GOAL_INSIGHTS).sort(), goalIds)

  let mechanismCount = 0
  const seenIds = new Set()
  for (const goal of matriz.priorityGoals) {
    const insight = resolveMatrizGoalInsight(goal.goalId)
    assert.ok(insight, goal.goalId)
    assert.ok(insight.focus.trim(), goal.goalId)
    assert.ok(insight.focus.length <= 180, goal.goalId)
    assert.equal(insight.mechanisms.length, 2, goal.goalId)

    for (const mechanism of insight.mechanisms) {
      const key = `${goal.goalId}|${mechanism.id}`
      assert.equal(seenIds.has(key), false, key)
      seenIds.add(key)
      mechanismCount += 1
      assert.ok(mechanism.title.trim(), key)
      assert.ok(mechanism.explanation.trim(), key)
      assert.ok(mechanism.verification.trim(), key)
      const contextReferences = [
        mechanism.measure,
        mechanism.relatedGoal,
        mechanism.educationContext,
      ].filter(Boolean)
      assert.ok(contextReferences.length <= 1, key)
      if (mechanism.measure) {
        assert.ok(mechanism.measure.measureId.trim(), key)
        assert.ok(mechanism.measure.use.trim(), key)
      }
      if (mechanism.relatedGoal) {
        assert.ok(mechanism.relatedGoal.goalId.trim(), key)
        assert.ok(mechanism.relatedGoal.use.trim(), key)
      }
      if (mechanism.educationContext) {
        assert.equal(mechanism.educationContext.key, 'accessibility_by_network', key)
        assert.ok(mechanism.educationContext.use.trim(), key)
      }
    }
  }

  assert.equal(mechanismCount, 14)
  assert.equal(seenIds.size, 14)
})

test('a página preserva metas, números e comparações do artefato', () => {
  const html = renderMatriz()
  const situations = [
    '35,1% hoje · referência 60%',
    '43,5% hoje · referência 70%',
    '57,2% hoje · referência 100%',
    '65,8% hoje · referência 100%',
    '91,1% hoje · referência 100%',
    '92,2% hoje · referência 100%',
    '47,1% hoje · referência 100%',
  ]
  const peerBenchmarks = [
    'Cidades parecidas do RS (88, 2025): mediana 50,9% · município 15,8 p.p. abaixo',
    'Cidades parecidas do RS (88, 2023): mediana 54,2% · município 10,7 p.p. abaixo',
    'Cidades parecidas do RS (88, 2022): mediana 57,4% · município 0,2 p.p. abaixo',
    'Cidades parecidas do RS (88, 2025): mediana 66,2% · município 0,4 p.p. abaixo',
    'Cidades parecidas do RS (88, 2025): mediana 95% · município 3,9 p.p. abaixo',
    'Cidades parecidas do RS (88, 2025): mediana 94,6% · município 2,4 p.p. abaixo',
    'Cidades parecidas do RS (88, 2025): mediana 40,7% · município 6,4 p.p. acima',
  ]

  assert.ok(html.includes('7 metas prioritárias · 14 caminhos para avançar'))
  assert.ok(html.includes('Duas metas apresentam as maiores diferenças frente às 88 cidades parecidas do RS: Creche, 15,8 p.p. abaixo (2025), e Aprendizagem nos anos iniciais, 10,7 p.p. abaixo (2023).'))
  assert.ok(html.includes('Referência de 14 de agosto de 2026'))
  assert.ok(html.includes('Cada meta reúne o contexto essencial, o que confirmar na rede e os caminhos para avançar.'))
  assert.ok(html.includes('Dados públicos ajudam a escolher o que investigar; a confirmação acontece com registros e equipes da rede.'))
  assert.match(html, /<span class="matriz-severity matriz-severity--high">atenção maior<\/span>/u)
  assert.match(html, /<span class="matriz-severity matriz-severity--medium">atenção<\/span>/u)
  assert.equal((html.match(/Caminhos para avançar/gu) ?? []).length, 7)
  assert.equal(html.includes('Leitura para decisão'), false)
  assert.equal(html.includes('Frentes recomendadas para avançar'), false)
  for (const goal of matriz.priorityGoals) assert.ok(html.includes(goal.title), goal.title)
  for (const situation of situations) assert.ok(html.includes(situation), situation)
  for (const benchmark of peerBenchmarks) assert.ok(html.includes(benchmark), benchmark)
  assert.ok(html.includes('Outras metas abaixo do esperado'))
  assert.ok(html.includes('Alfabetização ao final do 2º ano'))
  assert.ok(html.includes('49% hoje · referência 80%'))
})

test('o resumo destaca no máximo duas grandes diferenças e preserva fallback neutro', () => {
  const summary = matrizPriorityPeerSummary(matriz)
  const withoutHighlights = {
    ...matriz,
    priorityGoals: matriz.priorityGoals.map((goal) => ({
      ...goal,
      severity: { ...goal.severity, peerDeviation: 'worse_than_peers' },
    })),
  }

  assert.equal(
    summary,
    'Duas metas apresentam as maiores diferenças frente às 88 cidades parecidas do RS: Creche, 15,8 p.p. abaixo (2025), e Aprendizagem nos anos iniciais, 10,7 p.p. abaixo (2023).',
  )
  assert.equal((summary.match(/p\.p\./gu) ?? []).length, 2)
  assert.equal(matrizPriorityPeerSummary(withoutHighlights), 'Comparação: 88 cidades parecidas do RS')
})

test('a matriz comparativa cruza referência e pares sem ampliar o conteúdo inicial', () => {
  const html = renderMatriz()
  const priorityButtons = html.match(/<button\b[^>]*class="matriz-priority-card"[^>]*>/gu) ?? []
  const distanceRows = html.match(/<tr\b[^>]*class="matriz-priority-table__row"[^>]*>/gu) ?? []
  const peerHeaders = html.match(/<th\b[^>]*class="matriz-priority-table__peer"[^>]*>/gu) ?? []
  const goalSections = html.match(/<section\b[^>]*class="matriz-goal"[^>]*>/gu) ?? []
  const frontDetails = html.match(/<details\b[^>]*class="matriz-frente__more"[^>]*>/gu) ?? []

  assert.ok(html.includes('Matriz comparativa das metas'))
  assert.ok(html.includes('Distância da referência × situação entre cidades parecidas.'))
  assert.equal(html.includes('Panorama das metas'), false)
  assert.equal(priorityButtons.length, 7)
  assert.equal(distanceRows.length, 2)
  assert.equal(peerHeaders.length, 3)
  assert.ok(distanceRows.some((row) => row.includes('data-distance="far_from_target"')))
  assert.ok(distanceRows.some((row) => row.includes('data-distance="below_target"')))
  assert.ok(peerHeaders.some((header) => header.includes('data-peer="much_worse_than_peers"')))
  assert.ok(peerHeaders.some((header) => header.includes('data-peer="worse_than_peers"')))
  assert.ok(peerHeaders.some((header) => header.includes('data-peer="in_line_with_peers"')))
  assert.equal(html.includes('href="#"'), false)
  assert.equal(html.includes('href="#matriz'), false)
  assert.equal(goalSections.length, 7)
  for (let index = 0; index < 7; index += 1) {
    const goalSection = goalSections.find((tag) => tag.includes('id="matriz-goal-' + index + '"'))
    assert.ok(goalSection)
    assert.match(goalSection, /\stabindex="-1"(?:\s|>)/u)
  }

  assert.equal(frontDetails.length, 14)
  for (const detailsTag of frontDetails) {
    assert.doesNotMatch(detailsTag, /\sopen(?:=|\s|>)/u)
  }
  assert.equal((html.match(/Comece por aqui/gu) ?? []).length, 7)
})

test('cada caminho mostra o resultado esperado antes do detalhamento', () => {
  const html = renderMatriz()
  const frontCards = html.match(/<article\b[^>]*class="matriz-frente"[^>]*>[\s\S]*?<\/article>/gu) ?? []
  const frontDetails = html.match(/<details\b[^>]*class="matriz-frente__more"[^>]*>[\s\S]*?<\/details>/gu) ?? []

  assert.equal(frontCards.length, 14)
  assert.equal(frontDetails.length, 14)
  assert.equal((html.match(/Resultado esperado/gu) ?? []).length, 14)
  assert.equal(html.includes('Marco de implementação'), false)
  for (const goal of matriz.priorityGoals) {
    for (const front of resolveMatrizFrentes(goal.goalId)) {
      assert.ok(html.includes(front.implementationMilestone), matrizFrenteKey(goal.goalId, front.id))
    }
  }
  for (const card of frontCards) {
    assert.ok(
      card.indexOf('Resultado esperado') < card.indexOf('<details'),
      'O resultado esperado deve anteceder o detalhamento.',
    )
  }
  for (const details of frontDetails) {
    assert.equal(details.includes('Resultado esperado'), false)
    assert.doesNotMatch(details, /^<details\b[^>]*\sopen(?:=|\s|>)/u)
  }
})

test('os 14 caminhos exibem um único sinal de acompanhamento depois do resultado esperado', () => {
  const html = renderMatriz()
  const frontCards = html.match(/<article\b[^>]*class="matriz-frente"[^>]*>[\s\S]*?<\/article>/gu) ?? []
  const fronts = Object.entries(MATRIZ_FRENTES).flatMap(([goalId, entries]) => (
    entries.map((front) => ({ front, goalId }))
  ))

  assert.equal(fronts.length, 14)
  assert.equal(frontCards.length, 14)
  assert.equal((html.match(/Sinal de acompanhamento/gu) ?? []).length, 14)
  for (const { front, goalId } of fronts) {
    const key = matrizFrenteKey(goalId, front.id)
    assert.ok(front.monitoringSignal.trim(), key)
    assert.ok(front.monitoringSignal.length <= 160, key)
    assert.match(front.monitoringSignal, /\.$/u, key)
    assert.equal((front.monitoringSignal.match(/\./gu) ?? []).length, 1, key)
    assert.doesNotMatch(front.monitoringSignal, /causa/iu, key)
    assert.ok(html.includes(front.monitoringSignal), key)
  }
  for (const card of frontCards) {
    assert.ok(card.indexOf('Resultado esperado') < card.indexOf('Sinal de acompanhamento'))
    assert.ok(card.indexOf('Sinal de acompanhamento') < card.indexOf('<details'))
  }
})

test('as cinco medidas editoriais têm frase de uso da comparação com pares', () => {
  const contexts = Object.values(MATRIZ_GOAL_INSIGHTS)
    .flatMap((insight) => insight.mechanisms)
    .flatMap((mechanism) => mechanism.measure ? [mechanism.measure] : [])

  assert.equal(contexts.length, 5)
  assert.equal(new Set(contexts.map((context) => context.measureId)).size, 5)
  for (const context of contexts) {
    assert.ok(context.peerUse?.trim(), context.measureId)
    assert.match(context.peerUse, /\.$/u, context.measureId)
    assert.doesNotMatch(context.peerUse, /causa/iu, context.measureId)
  }
})

test('a grade das frentes preserva a altura própria de cada cartão', () => {
  const frontListRule = matrizCss.match(/\.matriz-frente-list\s*\{([\s\S]*?)\}/u)

  assert.ok(frontListRule, 'Regra de layout da lista de frentes não encontrada.')
  assert.match(frontListRule[1], /align-items:\s*start;/u)
})

test('a navegação por meta reserva espaço para as duas barras fixas em tela estreita', () => {
  const mobileGoalRule = matrizCss.match(
    /@media\s*\(max-width:\s*1079px\)\s*\{[\s\S]*?\.matriz-goal\s*\{([\s\S]*?)\}/u,
  )

  assert.ok(mobileGoalRule, 'Regra móvel de rolagem da meta não encontrada.')
  assert.match(
    mobileGoalRule[1],
    /scroll-margin-top:\s*calc\(64px \+ var\(--context-bar-height\) \+ var\(--space-4\)\);/u,
  )
})

test('o contexto municipal fica centralizado na leitura da meta e preserva seus limites', () => {
  const html = renderMatriz()
  const allGoals = [...matriz.priorityGoals, ...matriz.goalsWithoutOwnCause]
  let measureContexts = 0
  let relatedGoalContexts = 0
  let educationContexts = 0

  for (const goal of matriz.priorityGoals) {
    const insight = resolveMatrizGoalInsight(goal.goalId)
    assert.ok(insight, goal.goalId)
    for (const mechanism of insight.mechanisms) {
      if (mechanism.measure) {
        measureContexts += 1
        const readings = resolveMatrizContextReadings(matriz, [mechanism.measure])
        assert.equal(readings.length, 1, `${goal.goalId}|${mechanism.id}`)
        assert.ok(html.includes(readings[0].label), readings[0].label)
        assert.ok(html.includes(readings[0].use), readings[0].use)
      }
      if (mechanism.relatedGoal) {
        relatedGoalContexts += 1
        const relatedGoal = allGoals.find((candidate) => candidate.goalId === mechanism.relatedGoal.goalId)
        assert.ok(relatedGoal, `${goal.goalId}|${mechanism.id}`)
        assert.ok(html.includes(mechanism.relatedGoal.use), mechanism.relatedGoal.use)
      }
      if (mechanism.educationContext) educationContexts += 1
    }
  }

  assert.equal(measureContexts, 5)
  assert.equal(relatedGoalContexts, 2)
  assert.equal(educationContexts, 1)
  assert.equal((html.match(/Caminhos para avançar/gu) ?? []).length, 7)
  assert.equal((html.match(/Antes de agir, confira:/gu) ?? []).length, 14)
  assert.ok(html.includes('Acessibilidade por rede'))
  assert.ok(html.includes('Rede municipal: 53,8% das salas · rede estadual: 0% (2025)'))
  assert.ok(html.includes('declarações administrativas orientam a vistoria, mas não substituem avaliação técnica'))
  assert.equal(html.includes('Leitura para decisão'), false)
  assert.equal(html.includes('Contexto e pontos para verificar'), false)
  assert.equal(html.includes('Para acompanhar no município'), false)
  assert.equal(html.includes('Nota oficial do levantamento oficial'), false)
  for (const measureId of allDocumentMeasureIds()) {
    assert.equal(html.includes(measureId), false, measureId)
  }
})

test('as pontes internas aprofundam a frente sem perder o município selecionado', () => {
  const html = renderMatriz()
  const bridgeLinks = html.match(/<a href="#[^"]*municipio=4313375[^"]*">[^<]+<\/a>/gu) ?? []

  assert.equal(bridgeLinks.length, 13)
  assert.ok(bridgeLinks.every((link) => link.includes('#educacao?')))
  assert.ok(html.includes('Informações relacionadas no painel'))
  assert.ok(html.includes('Infraestrutura escolar no município'))
})

test('a página mantém linguagem expositiva e não oferece plano de ação nem guia rápido', () => {
  const html = renderMatriz()

  for (const removedText of [
    'Meu plano de ação',
    'Adicionar ao plano de ação',
    'Remover do plano de ação',
    'Exportar plano de ação',
    'Versão para imprimir',
    'Guia rápido',
    'Sugestão: comece por aqui',
    'Veja também no painel',
    'Frente inicial sugerida',
    'Ações recomendadas e apoio federal',
  ]) {
    assert.equal(html.includes(removedText), false, removedText)
  }
  assert.ok(html.includes('Comece por aqui'))
  assert.ok(html.includes('Como avançar e onde buscar apoio'))
  assert.ok(html.includes('Etapas sugeridas'))
  assert.ok(html.includes('Resultado esperado'))
  assert.ok(html.includes('Informações relacionadas no painel'))
})

test('o contexto educacional usa o recorte validado mais recente e falha sem inventar zero', () => {
  assert.deepEqual(educationContext, {
    accessibilityByNetwork: {
      year: 2025,
      municipalSchools: 18,
      municipalAccessibleRoomsPercent: 53.8,
      stateSchools: 3,
      stateAccessibleRoomsPercent: 0,
      publicSchools: 21,
      publicAccessibleRoomsPercent: 47.8,
    },
  })
  assert.deepEqual(buildMatrizEducationContext({}), { accessibilityByNetwork: null })
  assert.deepEqual(buildMatrizEducationContext({
    blocos: {
      rede_escolar: {
        infraestrutura: {
          por_rede: [
            { ano: 2025, dependencia: 'municipal', escolas: 18, perc_salas_acessiveis: 53.8 },
            { ano: 2025, dependencia: 'estadual', escolas: 3, perc_salas_acessiveis: null },
            { ano: 2025, dependencia: 'publica', escolas: 21, perc_salas_acessiveis: 47.8 },
          ],
        },
      },
    },
  }), { accessibilityByNetwork: null })
})

test('a leitura da EJA não converte perfil econômico em demanda comprovada', () => {
  const html = renderMatriz()

  assert.ok(html.includes('não define qual curso oferecer nem comprova demanda profissional'))
  assert.ok(html.includes('validar sua utilidade com estudantes, instituições formadoras e empregadores'))
  assert.equal(html.includes('demanda real na região'), false)
  assert.equal(html.includes('aumentam a procura'), false)
  assert.equal(html.includes('cursos vinculados às demandas da região'), false)
  assert.equal(html.includes('840 matrículas'), false)
  assert.equal(html.includes('8 das 21 escolas'), false)
})

test('o HTML não expõe campos, identificadores nem linguagem antiga', () => {
  const html = renderMatriz()

  assertPublicLanguage(html)
})

test('a exportação gera linhas públicas na ordem das metas selecionadas', () => {
  const selection = [
    {
      key: matrizFrenteKey('5.a', 'avaliar-e-recompor'),
      status: 'doing',
      note: '  Secretaria\u0000   acompanha  ',
    },
    matrizFrenteKey('4.b', 'alfabetizar-na-idade-certa'),
  ]
  const workbook = buildMatrizFrentesWorkbook(matriz, selection)
  const expected = [
    ['5.a', 'avaliar-e-recompor', 'em andamento', 'Secretaria acompanha'],
    ['4.b', 'alfabetizar-na-idade-certa', 'para fazer', ''],
  ]

  assert.equal(workbook.rows.length, 2)
  for (const [index, [goalId, frontId, estado, anotacao]] of expected.entries()) {
    const goal = matriz.priorityGoals.find((item) => item.goalId === goalId)
    const front = resolveMatrizFrentes(goalId).find((item) => item.id === frontId)
    const insight = resolveMatrizGoalInsight(goalId)
    const mechanism = insight?.mechanisms.find((item) => item.id === front?.mechanismId)
    const row = workbook.rows[index]
    assert.ok(goal)
    assert.ok(front)
    assert.ok(mechanism)
    assert.equal(row.meta, goal.title)
    assert.equal(row.situacao, formatMatrizGoalSituation(goal))
    assert.equal(row.gravidade, MATRIZ_SEVERITY_LABEL[goal.severity.level])
    assert.equal(row.comparacao, matrizPeerBenchmarkComparison(goal, matriz.municipality.uf))
    assert.equal(row.frente, front.title)
    assert.equal(row.pontoDeAtencao, mechanism.explanation)
    assert.equal(row.comoAvancar, front.steps.join('\n'))
    assert.equal(row.estado, estado)
    assert.equal(row.anotacao, anotacao)
  }

  const headers = workbook.sheets[0].data[0].map((cell) => cell.value)
  assert.equal(headers[2], 'Atenção')
  assert.deepEqual(headers.slice(-3), ['Estado', 'Anotação', 'Data de referência'])

  const serialized = JSON.stringify(workbook)
  assert.equal(serialized.includes('F_'), false)
  for (const measureId of allDocumentMeasureIds()) {
    assert.equal(serialized.includes(measureId), false, measureId)
  }
  assert.ok(workbook.fileName.endsWith('.xlsx'))
})

test('storage v5 saneia o plano e migra planos v4 e seleções v3 do mesmo escopo', () => {
  const scope = {
    municipalityIbge7: matriz.municipality.ibge7,
    referenceDate: matriz.referenceDate,
  }
  const doingKey = matrizFrenteKey('5.a', 'avaliar-e-recompor')
  const todoKey = matrizFrenteKey('4.b', 'alfabetizar-na-idade-certa')
  const entries = [
    { key: doingKey, status: 'doing', note: '  Próximo\u0000   passo  ' },
    { key: todoKey, status: 'unknown', note: 'x'.repeat(300) },
  ]
  const serialized = serializeMatrizPlan(scope, entries)
  const parsed = parseMatrizPlan(JSON.stringify({
    ...JSON.parse(serialized),
    entries: [
      ...JSON.parse(serialized).entries,
      { key: 'F_ATTEND', status: 'done', note: 'descartar' },
    ],
  }), scope)
  const legacyPayload = JSON.stringify({
    schemaVersion: MATRIZ_FRONTS_LEGACY_SCHEMA_VERSION_V3,
    municipalityIbge7: scope.municipalityIbge7,
    referenceDate: scope.referenceDate,
    selections: [doingKey, todoKey],
  })
  const values = new Map([
    [`${MATRIZ_FRONTS_LEGACY_KEY_PREFIX_V3}:${scope.municipalityIbge7}:${scope.referenceDate}`, legacyPayload],
  ])
  const storage = {
    getItem(key) { return values.get(key) ?? null },
    removeItem(key) { values.delete(key) },
    setItem(key, value) { values.set(key, value) },
  }

  assert.equal(MATRIZ_FRONTS_STORAGE_KEY_PREFIX, 'pne_matriz_frentes_v5')
  assert.equal(MATRIZ_FRONTS_SCHEMA_VERSION, 'matriz-frentes-v5')
  assert.deepEqual(parsed, [
    { key: todoKey, status: 'todo', note: 'x'.repeat(280) },
    { key: doingKey, status: 'doing', note: 'Próximo passo' },
  ].sort((left, right) => left.key.localeCompare(right.key)))
  assert.deepEqual(restoreMatrizPlan(storage, scope), [
    { key: todoKey, status: 'todo', note: '' },
    { key: doingKey, status: 'todo', note: '' },
  ].sort((left, right) => left.key.localeCompare(right.key)))
  const legacyKey = `${MATRIZ_FRONTS_LEGACY_KEY_PREFIX_V3}:${scope.municipalityIbge7}:${scope.referenceDate}`
  const currentKey = `${MATRIZ_FRONTS_STORAGE_KEY_PREFIX}:${scope.municipalityIbge7}:${scope.referenceDate}`
  const expectedMigrated = [
    { key: todoKey, status: 'todo', note: '' },
    { key: doingKey, status: 'todo', note: '' },
  ].sort((left, right) => left.key.localeCompare(right.key))
  assert.equal(values.has(legacyKey), false)
  assert.equal(values.has(currentKey), true)
  assert.deepEqual(parseMatrizPlan(values.get(currentKey), scope), expectedMigrated)
  assert.deepEqual(restoreMatrizPlan(storage, scope), expectedMigrated)
  assert.equal(persistMatrizPlan(storage, scope, []), true)
  assert.deepEqual(restoreMatrizPlan(storage, scope), [])
  assert.throws(() => serializeMatrizPlan(scope, [{ key: 'F_ATTEND', status: 'todo', note: '' }]))

  const v4Scope = { ...scope, referenceDate: '2026-08-13' }
  const v4Key = `${MATRIZ_FRONTS_LEGACY_KEY_PREFIX_V4}:${v4Scope.municipalityIbge7}:${v4Scope.referenceDate}`
  const v5Key = `${MATRIZ_FRONTS_STORAGE_KEY_PREFIX}:${v4Scope.municipalityIbge7}:${v4Scope.referenceDate}`
  values.set(v4Key, JSON.stringify({
    schemaVersion: MATRIZ_FRONTS_LEGACY_SCHEMA_VERSION_V4,
    municipalityIbge7: v4Scope.municipalityIbge7,
    referenceDate: v4Scope.referenceDate,
    entries: [{ key: doingKey, status: 'doing', note: 'Mantida' }],
  }))
  assert.deepEqual(restoreMatrizPlan(storage, v4Scope), [
    { key: doingKey, status: 'doing', note: 'Mantida' },
  ])
  assert.equal(values.has(v4Key), false)
  assert.equal(values.has(v5Key), true)
})

test('o plano mais recente de data anterior é reconciliado sem expor chaves retiradas', () => {
  const currentScope = {
    municipalityIbge7: matriz.municipality.ibge7,
    referenceDate: matriz.referenceDate,
  }
  const keptKey = matrizFrenteKey('5.a', 'avaliar-e-recompor')
  const removedKey = '5.a|frente-retirada'
  const priorScope = { ...currentScope, referenceDate: '2026-08-10' }
  const olderScope = { ...currentScope, referenceDate: '2026-07-01' }
  const values = new Map([
    [
      `${MATRIZ_FRONTS_STORAGE_KEY_PREFIX}:${priorScope.municipalityIbge7}:${priorScope.referenceDate}`,
      serializeMatrizPlan(priorScope, [
        { key: keptKey, status: 'doing', note: 'Continuar', frontTitle: 'Avaliar e recompor as aprendizagens', goalTitle: 'Aprendizagem' },
        { key: removedKey, status: 'done', note: '', frontTitle: 'Frente encerrada', goalTitle: 'Aprendizagem' },
      ]),
    ],
    [
      `${MATRIZ_FRONTS_LEGACY_KEY_PREFIX_V4}:${olderScope.municipalityIbge7}:${olderScope.referenceDate}`,
      JSON.stringify({
        schemaVersion: MATRIZ_FRONTS_LEGACY_SCHEMA_VERSION_V4,
        municipalityIbge7: olderScope.municipalityIbge7,
        referenceDate: olderScope.referenceDate,
        entries: [{ key: keptKey, status: 'todo', note: '' }],
      }),
    ],
    [
      `${MATRIZ_FRONTS_STORAGE_KEY_PREFIX}:4300000:2026-08-12`,
      serializeMatrizPlan(
        { municipalityIbge7: '4300000', referenceDate: '2026-08-12' },
        [{ key: keptKey, status: 'done', note: '' }],
      ),
    ],
  ])
  const storage = {
    get length() { return values.size },
    getItem(key) { return values.get(key) ?? null },
    key(index) { return [...values.keys()][index] ?? null },
    removeItem(key) { values.delete(key) },
    setItem(key, value) { values.set(key, value) },
  }
  const previous = findPreviousMatrizPlan(storage, currentScope)

  assert.ok(previous)
  assert.equal(previous.referenceDate, priorScope.referenceDate)
  const reconciled = reconcileMatrizPlanEntries(previous.entries, new Set([keptKey]))
  assert.deepEqual(reconciled.kept.map((entry) => entry.key), [keptKey])
  assert.deepEqual(reconciled.removed.map((entry) => entry.frontTitle), ['Frente encerrada'])
})
