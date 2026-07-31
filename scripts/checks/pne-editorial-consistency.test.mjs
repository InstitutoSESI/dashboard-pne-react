import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

import {
  PNE_2026_GOAL_INDICATOR_CONTRACT,
  getPne2026Indicator,
  getPne2026PublicRelationsForGoal,
} from '../../src/data/pne2026GoalIndicatorContract.js'
import {
  PNE_2026_LEGAL_GOAL_INDICATOR_MAP,
} from '../../src/data/pne2026LegalGoalIndicatorMap.js'
import {
  PNE_LEGAL_GOAL_CATEGORIES,
  buildPneLegalGoalsSummary,
  getPne2026CanonicalCycleItems,
  getPneLegalDataStatusLabel,
  getPneLegalGoalCategory,
} from '../../src/utils/pneLegalGoalsPresentation.js'
import {
  getPneComparisonStatusPresentation,
} from '../../src/utils/pneIndicatorPresentation.js'
import { mergePne2026DiagnosticResults } from '../../src/utils/pneCycleDiagnosticResults.js'

const legalPageSource = readFileSync(
  new URL('../../src/pages/PneLegalGoalsPage.jsx', import.meta.url),
  'utf8',
)
const cyclePageSource = readFileSync(
  new URL('../../src/pages/CyclePage.jsx', import.meta.url),
  'utf8',
)
const metaCardSource = readFileSync(
  new URL('../../src/components/MetaCard.jsx', import.meta.url),
  'utf8',
)
const legalPresentationSource = readFileSync(
  new URL('../../src/utils/pneLegalGoalsPresentation.js', import.meta.url),
  'utf8',
)
const indicatorPresentationSource = readFileSync(
  new URL('../../src/utils/pneIndicatorPresentation.js', import.meta.url),
  'utf8',
)
const legalMapSource = readFileSync(
  new URL('../../src/data/pne2026LegalGoalIndicatorMap.js', import.meta.url),
  'utf8',
)

test('the 73 legal goals retain their canonical text and exclusive public category', () => {
  assert.equal(PNE_2026_LEGAL_GOAL_INDICATOR_MAP.length, 73)
  const canonicalGoals = Object.values(PNE_2026_GOAL_INDICATOR_CONTRACT.goals)
    .sort((left, right) => left.legalOrder - right.legalOrder)

  assert.deepEqual(
    PNE_2026_LEGAL_GOAL_INDICATOR_MAP.map((goal) => goal.legalText),
    canonicalGoals.map((goal) => goal.legalText),
  )

  const validCategories = new Set(Object.values(PNE_LEGAL_GOAL_CATEGORIES))
  for (const goal of PNE_2026_LEGAL_GOAL_INDICATOR_MAP) {
    assert.ok(validCategories.has(getPneLegalGoalCategory(goal)))
  }

  const summary = buildPneLegalGoalsSummary(PNE_2026_LEGAL_GOAL_INDICATOR_MAP)
  assert.deepEqual(summary, {
    complementary: 10,
    direct: 14,
    partial: 15,
    total: 73,
    withIndicator: 39,
    withoutIndicator: 34,
  })
  assert.equal(
    summary.direct + summary.partial + summary.complementary + summary.withoutIndicator,
    summary.total,
  )
  assert.equal(summary.direct + summary.partial + summary.complementary, 39)
  assert.equal(summary.withIndicator + summary.withoutIndicator, 73)
  assert.match(legalPageSource, /\{trackedGoals\.length\} metas com informação municipal/)
  assert.doesNotMatch(legalPageSource, /metas acompanhadas/i)
})

test('direct and partial categories come from canonical relationship nature, not mode alone', () => {
  const directTrackingGoal = PNE_2026_LEGAL_GOAL_INDICATOR_MAP.find(
    (goal) => goal.legalGoalId === '18.b',
  )
  const partialTrackingGoal = PNE_2026_LEGAL_GOAL_INDICATOR_MAP.find(
    (goal) => goal.legalGoalId === '17.c',
  )
  const complementaryGoal = PNE_2026_LEGAL_GOAL_INDICATOR_MAP.find(
    (goal) => getPneLegalGoalCategory(goal) === PNE_LEGAL_GOAL_CATEGORIES.COMPLEMENTARY,
  )

  assert.equal(directTrackingGoal.relatedIndicators[0].monitoringMode, 'tracking')
  assert.equal(partialTrackingGoal.relatedIndicators[0].monitoringMode, 'tracking')
  assert.equal(directTrackingGoal.relatedIndicators[0].coverage, 'direta')
  assert.notEqual(partialTrackingGoal.relatedIndicators[0].coverage, 'direta')
  assert.equal(getPneLegalGoalCategory(directTrackingGoal), PNE_LEGAL_GOAL_CATEGORIES.DIRECT)
  assert.equal(getPneLegalGoalCategory(partialTrackingGoal), PNE_LEGAL_GOAL_CATEGORIES.PARTIAL)
  assert.equal(getPneLegalGoalCategory(complementaryGoal), PNE_LEGAL_GOAL_CATEGORIES.COMPLEMENTARY)
  assert.notEqual(getPneLegalGoalCategory(complementaryGoal), PNE_LEGAL_GOAL_CATEGORIES.DIRECT)
})

test('legal-goal theme metadata for the consolidated relations comes from the active policy', () => {
  const publicItems = getPne2026CanonicalCycleItems()
  const canonicalItems = new Map(publicItems.map((item) => [item.key, item]))
  for (const item of publicItems) {
    assert.ok(item.categoryKey, item.relationId)
    assert.ok(item.categoryLabel, item.relationId)
  }
  assert.equal(
    canonicalItems.get('alfabetizacao').categoryKey,
    'escolaridade_alfabetizacao_v2',
  )
  assert.equal(
    canonicalItems.get('eja_atendimento_18_mais').categoryKey,
    'educacao_profissional_eja_v2',
  )
  for (const indicatorId of [
    'graduacao_frequencia_18_24',
    'superior_completo_25_34',
    'taxa_bruta_graduacao',
    'docentes_tempo_integral_ies',
    'docentes_tempo_integral_universidades',
    'docentes_tempo_integral_centros_universitarios',
    'docentes_tempo_integral_faculdades',
  ]) {
    assert.equal(
      canonicalItems.get(indicatorId).categoryKey,
      'educacao_superior_v2',
      indicatorId,
    )
  }
})

test('legal-goal adapter preserves canonical public and methodological fields', () => {
  const canonicalRelations = new Map(
    PNE_2026_GOAL_INDICATOR_CONTRACT.relations.map(
      (relation) => [relation.relationId, relation],
    ),
  )

  for (const goal of PNE_2026_LEGAL_GOAL_INDICATOR_MAP) {
    for (const relation of goal.relatedIndicators) {
      const canonical = canonicalRelations.get(relation.relationId)
      const indicator = getPne2026Indicator(canonical.indicatorId)
      assert.ok(canonical, relation.relationId)
      assert.equal(
        relation.publicName,
        canonical.publicLabelOverride ?? indicator.publicTitle,
      )
      assert.equal(
        relation.publicDescription,
        canonical.publicDescriptionOverride ?? indicator.publicDescription,
      )
      assert.equal(relation.monitoringMode, canonical.mode)
      assert.equal(relation.referenceId, canonical.referenceId)
      assert.equal(Object.hasOwn(relation, 'source'), false)
      assert.equal(Object.hasOwn(relation, 'limitation'), false)
    }
  }

  assert.doesNotMatch(legalMapSource, /publicName:\s*['"`]/)
  assert.doesNotMatch(legalMapSource, /publicDescription:\s*['"`]/)
  assert.doesNotMatch(legalMapSource, /monitoringMode:\s*['"`]/)
  assert.doesNotMatch(legalMapSource, /referenceId:\s*['"`]/)
})

test('all and only public canonical relations are available to the legal page', () => {
  const expectedRelationIds = PNE_2026_GOAL_INDICATOR_CONTRACT.relations
    .filter((relation) => relation.mode !== 'hidden')
    .map((relation) => relation.relationId)
    .sort()
  const actualRelationIds = PNE_2026_LEGAL_GOAL_INDICATOR_MAP
    .flatMap((goal) => getPne2026PublicRelationsForGoal(goal.legalGoalId))
    .map((relation) => relation.relationId)
    .sort()

  assert.deepEqual(actualRelationIds, expectedRelationIds)
  for (const goalId of ['4.a', '5.a', '5.b', '5.d', '6.a', '11.b', '11.c', '12.a', '17.a']) {
    const expectedCount = expectedRelationIds.filter((relationId) => (
      relationId.startsWith(`relation.${goalId}.`)
    )).length
    assert.equal(getPne2026PublicRelationsForGoal(goalId).length, expectedCount)
    assert.ok(expectedCount > 1)
  }
})

test('canonical names are shared by legal and cycle consumers', () => {
  assert.equal(
    PNE_2026_GOAL_INDICATOR_CONTRACT.indicators.creche.publicTitle,
    'Matrículas de crianças de 0 a 3 anos em relação à população residente estimada',
  )
  assert.equal(
    PNE_2026_GOAL_INDICATOR_CONTRACT.indicators.pre_escola.publicTitle,
    'Matrículas de crianças de 4 a 5 anos em relação à população residente estimada',
  )
  assert.equal(
    PNE_2026_GOAL_INDICATOR_CONTRACT.indicators.basico_6_17.publicTitle,
    'Matrículas de 6 a 17 anos em relação à população residente estimada',
  )
  assert.equal(
    PNE_2026_GOAL_INDICATOR_CONTRACT.indicators.basico_15_17.publicTitle,
    'Matrículas de 15 a 17 anos em relação à população residente estimada',
  )
  assert.match(cyclePageSource, /context\.indicator\?\.publicTitle/)
  assert.match(legalPageSource, /relationPresentation\.publicName/)
})

test('legal-page copy omits projections and internal mode language', () => {
  assert.doesNotMatch(legalPageSource, /Projeção para 2036/)
  assert.doesNotMatch(legalPageSource, /Cobertura parcial/)
  assert.doesNotMatch(`${legalPageSource}\n${cyclePageSource}`, /modo progress|modo tracking/i)
  assert.match(legalPresentationSource, /Informação complementar — sem referência municipal/)
})

test('negative data states remain textual and are not converted to zero', () => {
  assert.equal(getPneLegalDataStatusLabel('unavailable'), 'Sem resultado comparável no período')
  assert.equal(getPneLegalDataStatusLabel('not_applicable'), 'Não se aplica ao município')
  assert.equal(getPneLegalDataStatusLabel('suppressed'), 'Dado suprimido pela fonte')

  const merged = mergePne2026DiagnosticResults({}, {
    goals: [{
      results: [{
        current: { value: null },
        dataStatus: 'suppressed',
        dataStatusLabel: 'Dado suprimido pela fonte',
        indicatorId: 'creche',
        mode: 'progress',
        reasonCode: 'source_suppression',
      }],
    }],
  })
  assert.equal(merged.creche.available, false)
  assert.equal(merged.creche.dataStatus, 'suppressed')
  assert.equal(merged.creche.end_value, undefined)
})

test('one semantic rule determines progress and tracking colors and texts', () => {
  const progressAchieved = getPneComparisonStatusPresentation({
    achieved: true,
    direction: 'at_least',
    mode: 'progress',
  })
  const trackingAchieved = getPneComparisonStatusPresentation({
    achieved: true,
    direction: 'at_least',
    mode: 'tracking',
  })

  assert.deepEqual(progressAchieved, {
    state: 'success',
    text: 'Referência prevista na meta alcançada',
    tone: 'success',
  })
  assert.deepEqual(trackingAchieved, {
    state: 'success',
    text: 'Referência de acompanhamento alcançada',
    tone: 'success',
  })
  assert.doesNotMatch(
    trackingAchieved.text,
    /cumprimento integral|meta legal alcançada|meta cumprida/i,
  )
  assert.deepEqual(
    getPneComparisonStatusPresentation({
      achieved: false,
      direction: 'at_least',
      mode: 'progress',
    }),
    {
      state: 'danger',
      text: 'Abaixo da referência prevista na meta',
      tone: 'danger',
    },
  )
  assert.deepEqual(
    getPneComparisonStatusPresentation({
      achieved: false,
      direction: 'at_least',
      mode: 'tracking',
    }),
    {
      state: 'warning',
      text: 'Abaixo da referência de acompanhamento',
      tone: 'warning',
    },
  )
  assert.deepEqual(
    getPneComparisonStatusPresentation({
      achieved: true,
      direction: 'at_most',
      mode: 'progress',
    }),
    {
      state: 'success',
      text: 'Dentro do limite previsto na meta',
      tone: 'success',
    },
  )
  assert.match(metaCardSource, /presentation\.statusState/)
  assert.doesNotMatch(metaCardSource, /indicatorId.*tone|item\?\.key.*tone/)
  const statusRuleSource = indicatorPresentationSource.slice(
    indicatorPresentationSource.indexOf('export function getPneComparisonStatusPresentation'),
    indicatorPresentationSource.indexOf('export function getPneDiscreteIndicatorPresentation'),
  )
  assert.doesNotMatch(statusRuleSource, /indicatorId|theme/)
  assert.match(cyclePageSource, /Verde — referência alcançada/)
  assert.match(cyclePageSource, /Vermelho — abaixo da referência prevista na meta/)
  assert.match(cyclePageSource, /Amarelo — abaixo da referência de acompanhamento/)
})
