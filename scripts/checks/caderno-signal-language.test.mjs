import test from 'node:test'
import assert from 'node:assert/strict'
import { readdirSync, readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

import {
  formatSignalValue,
  MEASURE_LABEL,
  resolveSignalReading,
} from '../../src/features/caderno/cadernoSignalLanguage.ts'
import {
  CONTEXT_TITLE,
  FACTOR_TITLE,
  FACTOR_TITLE_BY_GOAL,
  resolveContextTitle,
  resolvePlainCause,
} from '../../src/features/caderno/cadernoPlainLanguage.ts'

const repoRoot = fileURLToPath(new URL('../..', import.meta.url))
const municipalitiesRoot = path.join(
  repoRoot,
  'public',
  'data',
  'pne2026-caderno',
  'municipios',
)
const hypothesisSections = Object.freeze([
  'adverse_signal',
  'no_public_data',
  'protective_present',
])

function collectPublishedMeasureIds() {
  const measureIds = new Set()
  const files = readdirSync(municipalitiesRoot)
    .filter((name) => name.endsWith('.json'))
    .sort()

  for (const file of files) {
    const document = JSON.parse(readFileSync(path.join(municipalitiesRoot, file), 'utf8'))
    for (const goal of document.goals ?? []) {
      for (const section of hypothesisSections) {
        for (const hypothesis of goal.hypotheses?.[section] ?? []) {
          for (const signal of hypothesis.signals ?? []) measureIds.add(signal.measureId)
        }
      }
      for (const context of goal.monitoring_context ?? []) {
        for (const signal of context.signals ?? []) measureIds.add(signal.measureId)
      }
    }
  }
  return [...measureIds].sort()
}

test('every published hypothesis and context signal has an authored public label', () => {
  const missing = collectPublishedMeasureIds().filter((measureId) => !MEASURE_LABEL[measureId])
  assert.deepEqual(
    missing,
    [],
    `Measure IDs sem rótulo público:\n${missing.join('\n')}`,
  )
})

test('context signals use the same public reading without requiring cause-only fields', () => {
  const document = JSON.parse(readFileSync(path.join(municipalitiesRoot, '4313375.json'), 'utf8'))
  const contextSignal = document.goals
    .flatMap((goal) => goal.monitoring_context)
    .flatMap((context) => context.signals)
    .find((signal) => signal.valueRaw.trim() !== '')

  assert.ok(contextSignal)
  assert.equal(Object.hasOwn(contextSignal, 'caution'), false)
  assert.equal(Object.hasOwn(contextSignal, 'stance'), false)
  const reading = resolveSignalReading(contextSignal)
  assert.ok(reading)
  assert.equal(reading.caution, '')
  assert.notEqual(reading.label, contextSignal.measureId)
})

test('new context units are formatted for people and empty values remain omitted', () => {
  assert.equal(formatSignalValue('thousand_brl_current_prices', '3229383', 'descriptive'), 'R$ 3.229.383 mil')
  assert.equal(formatSignalValue('inse_scale_points', '5.1336', 'descriptive'), '5,13 pontos')
  assert.equal(formatSignalValue('students_per_class', '21.5', 'descriptive'), '21,5 alunos por turma')
  assert.equal(formatSignalValue('students_per_class', '', 'descriptive'), null)
})

test('goal-specific cause language and context titles match the curated v2 copy', () => {
  const document = JSON.parse(readFileSync(path.join(municipalitiesRoot, '4313375.json'), 'utf8'))
  const expectedCauses = {
    '1:F_POV_CCT': {
      title: 'Custo para a família manter a criança na creche',
      why: 'Transporte, material, roupa e horários pesam no orçamento; quando o custo aperta, a família adia ou desiste da vaga.',
      help: 'Apoio de renda, transporte e prioridade de vaga para famílias do Bolsa Família costumam facilitar a matrícula.',
      look: ['Famílias do Bolsa Família com crianças fora da creche', 'Custos que as famílias citam para não matricular'],
    },
    '6:F_BASIC_INFRA': {
      title: 'Espaço e estrutura para ampliar a jornada',
      why: 'Sem salas, refeitório e espaço adequados, a escola não consegue oferecer o dia inteiro.',
      help: 'Adequar espaços existentes e planejar obras destrava a ampliação da jornada.',
      look: ['Escolas sem espaço para o dia inteiro', 'Obras previstas e seu andamento'],
    },
    '8:F_BASIC_INFRA': {
      title: 'Estrutura e recursos para climatizar as salas',
      why: 'Climatizar exige rede elétrica que aguente, equipamento instalado e manutenção em dia.',
      help: 'Adequar a rede elétrica e manter os equipamentos funcionando amplia as salas com conforto térmico.',
      look: ['Salas ainda sem climatização e o motivo', 'Equipamentos parados por falta de manutenção ou energia'],
    },
    '19:F_BASIC_INFRA': {
      title: 'Obras e adaptações de acessibilidade que não saem do papel',
      why: 'A adaptação das escolas depende de obra e recurso executados; o que fica no papel não muda o prédio.',
      help: 'Plano de acessibilidade por escola, com obra e prazo, tende a destravar as adaptações.',
      look: ['Escolas sem salas acessíveis e o que falta em cada uma', 'Obras e recursos de acessibilidade parados'],
    },
    '17:F_CAREER_PAY': {
      title: 'Plano de carreira e salário na prática',
      why: 'Ter lei de plano de carreira não basta: progressão e salário praticados definem quem entra e quem fica.',
      help: 'Cumprir a progressão prevista e comparar o salário com redes vizinhas ajuda a atrair e reter professores.',
      look: ['Progressões previstas e efetivadas', 'Salário praticado comparado ao piso e a redes próximas'],
    },
  }

  for (const [goalFactorKey, expected] of Object.entries(expectedCauses)) {
    const [goalId, factorId] = goalFactorKey.split(':')
    const goal = document.goals.find((candidate) => candidate.goalId === goalId)
    const hypothesis = Object.values(goal.hypotheses)
      .flat()
      .find((candidate) => candidate.factorId === factorId)
    assert.equal(FACTOR_TITLE_BY_GOAL[goalFactorKey], expected.title)
    assert.deepEqual(resolvePlainCause(hypothesis, goalId), expected)
  }

  const expectedContextTitles = {
    F_SES: 'Condições sociais do território',
    F_EC_OFFER: 'Vagas e matrículas na rede',
    F_HEALTH: 'Saúde dos alunos no território',
    F_TEACH_STABILITY: 'Rotatividade e vínculos dos professores',
    F_FINANCING_EXECUTION: 'Recursos da educação e sua execução',
    F_EPT_DEMAND: 'Conexão dos cursos técnicos com o trabalho local',
  }
  const publishedContexts = document.goals.flatMap((goal) => goal.monitoring_context)
  for (const [factorId, expected] of Object.entries(expectedContextTitles)) {
    const context = publishedContexts.find((candidate) => candidate.factorId === factorId)
    assert.equal(CONTEXT_TITLE[factorId], expected)
    assert.equal(resolveContextTitle(context), expected)
  }
  const fallback = publishedContexts.find((context) => context.factorId === 'F_DISTANCE')
  assert.equal(resolveContextTitle(fallback), FACTOR_TITLE.F_DISTANCE)
})

test('presence values never expose raw boolean or category codes', () => {
  for (const unit of ['boolean_indicator', 'category_code']) {
    for (const direction of ['presence_favorable', 'presence_adverse']) {
      for (const valueRaw of ['0', '1']) {
        const display = formatSignalValue(unit, valueRaw, direction)
        assert.ok(display)
        assert.notEqual(display, valueRaw)
      }
    }
  }
})

test('unknown measures are omitted without throwing', () => {
  const unknownSignal = {
    caution: 'Texto preservado.',
    dimensions: '',
    direction: 'descriptive',
    maxInference: 'description_only',
    measureId: 'unknown.measure',
    observability: 'direct',
    period: '2025',
    stance: 'context',
    unit: 'percent',
    valueRaw: '10',
  }
  assert.doesNotThrow(() => resolveSignalReading(unknownSignal))
  assert.equal(resolveSignalReading(unknownSignal), null)
})
