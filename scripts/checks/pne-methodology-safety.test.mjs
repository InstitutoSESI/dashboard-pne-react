import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

import { PNE_2026_LEGAL_GOAL_INDICATOR_MAP } from '../../src/data/pne2026LegalGoalIndicatorMap.js'
import { PNE_2026_INDICATOR_GOAL_REFS } from '../../src/data/pne2026IndicatorGoalRefs.js'
import { PNE_2014_INDICATOR_GOAL_REFS } from '../../src/data/pne2014IndicatorGoalRefs.js'
import { buildThematicGroups } from '../../src/data/thematicGroups.js'
import {
  PNE_2026_GOAL_INDICATOR_CONTRACT,
  canPne2026RelationEnterCycleSummary,
} from '../../src/data/pne2026GoalIndicatorContract.js'
import {
  resolvePne2026PublicDiagnosticV3,
} from '../../src/features/diagnostic/pne2026PublicDiagnosticV3.js'
import {
  PNE_2026_RELATIONSHIP_MODES,
  getPne2026RelationshipPolicy,
} from '../../src/data/pne2026MethodologySafety.js'
import { getDataSourceParts } from '../../src/utils/dataSourceNotes.js'
import { normalizePopulationPercentResults } from '../../src/utils/indicatorValues.js'
import { getPneIndicatorPresentation } from '../../src/utils/pneIndicatorPresentation.js'
import {
  mergePne2026DiagnosticResults,
  resolvePneCycleMunicipalResults,
} from '../../src/utils/pneCycleDiagnosticResults.js'
import {
  PNE_CYCLE_PRESENTATION_STATES,
  applyPneCycleVisibilityPolicy,
  filterPneComparableCategories,
  getPneCycleIndicatorDisplayPolicy,
  isPneComparableIndicator,
} from '../../src/utils/pneDisplayRules.js'
import { getPneCycleCopy } from '../../src/utils/pneCycleCopy.js'

const PNE_2014_CYCLE = 'pne_2014_2024'
const PNE_2026_CYCLE = 'pne_2026_2036'
const activeReleasePointer = JSON.parse(readFileSync(
  new URL('../../public/data/pne2026-diagnostic-v3/current.json', import.meta.url),
  'utf8',
))

function readActiveReleaseMunicipality(municipalityId) {
  return JSON.parse(readFileSync(
    new URL(
      `../../public/data/pne2026-diagnostic-v3/releases/${activeReleasePointer.releaseId}/municipios/${municipalityId}.json`,
      import.meta.url,
    ),
    'utf8',
  ))
}

function relation(goalId, indicatorId) {
  return PNE_2026_LEGAL_GOAL_INDICATOR_MAP
    .find((goal) => goal.legalGoalId === goalId)
    ?.relatedIndicators.find((item) => item.indicatorId === indicatorId)
}

test('relationship policy distinguishes progress, tracking, complementary, and hidden', () => {
  assert.equal(
    getPne2026RelationshipPolicy('1.a', 'creche').monitoringMode,
    PNE_2026_RELATIONSHIP_MODES.PROGRESS,
  )
  assert.equal(
    getPne2026RelationshipPolicy('4.b', 'idade_regular_quinto').monitoringMode,
    PNE_2026_RELATIONSHIP_MODES.TRACKING,
  )
  assert.equal(
    getPne2026RelationshipPolicy('17.b', 'rendimento_magisterio').monitoringMode,
    PNE_2026_RELATIONSHIP_MODES.HIDDEN,
  )
  assert.equal(
    relation('4.b', 'idade_regular_quinto').publicName,
    'Estudantes matriculados sem distorção — anos iniciais',
  )
  assert.equal(
    relation('4.b', 'idade_regular_quinto').publicDescription,
    'Percentual derivado de 100 − taxa de distorção idade-série nos anos iniciais do ensino fundamental. Mede matrículas sem distorção e não mede conclusão.',
  )
  assert.equal(relation('4.b', 'idade_regular_quinto').hasDistance, true)
  assert.equal(relation('4.b', 'idade_regular_quinto').hasProjection2036, false)
})

test('cycle filtering keeps only comparable progress and tracking relationships', () => {
  const categories = [{
    key: 'test',
    items: [
      { key: 'creche', metaRef: '1.a', monitoringMode: 'progress' },
      { key: 'idade_regular_quinto', metaRef: '4.b', monitoringMode: 'tracking' },
      { key: 'temporarios', metaRef: '17.d', monitoringMode: 'complementary' },
      { key: 'rendimento_magisterio', metaRef: '17.b', monitoringMode: 'hidden' },
    ],
  }]
  const comparableResult = {
    available: true,
    atingida: true,
    distance: 1,
    end_value: 100,
    meta: 100,
    tracks_goal: true,
    display: { status: 'Meta atingida' },
  }
  const results = {
    creche: comparableResult,
    idade_regular_quinto: comparableResult,
    temporarios: comparableResult,
    rendimento_magisterio: comparableResult,
  }
  const filtered = filterPneComparableCategories(categories, results, PNE_2026_CYCLE)

  assert.deepEqual(filtered[0].items.map((item) => item.key), [
    'creche',
    'idade_regular_quinto',
  ])
  assert.equal(isPneComparableIndicator({
    cycleId: PNE_2026_CYCLE,
    indicatorKey: 'idade_regular_quinto',
    item: categories[0].items[1],
    result: comparableResult,
  }), true)
})

test('cycle themes classify each comparable indicator exactly once', () => {
  const comparableRelations = PNE_2026_GOAL_INDICATOR_CONTRACT.relations
    .filter((item) => (
      [
        PNE_2026_RELATIONSHIP_MODES.PROGRESS,
        PNE_2026_RELATIONSHIP_MODES.TRACKING,
      ].includes(item.mode)
      && canPne2026RelationEnterCycleSummary(item)
    ))
  const items = comparableRelations.map((item) => ({
    key: item.indicatorId,
    metaRef: item.goalId,
  }))
  const groups = buildThematicGroups(
    [{ key: 'all', items }],
    PNE_2026_CYCLE,
  )
  const groupKeys = groups.flatMap((group) => group.items.map((item) => item.key))

  assert.equal(comparableRelations.length, 42)
  assert.equal(groupKeys.length, 42)
  assert.equal(groupKeys.length, new Set(groupKeys).size)
  assert.deepEqual(
    groups.filter((group) => group.items.some((item) => item.key === 'idade_regular_quinto'))
      .map((group) => group.key),
    ['aprendizagem_trajetoria_escolar_v2'],
  )
  assert.deepEqual(
    groups.filter((group) => group.items.some((item) => item.key === 'eja_atendimento_18_mais'))
      .map((group) => group.key),
    ['educacao_profissional_eja_v2'],
  )
  assert.deepEqual(
    groups.filter((group) => group.items.some((item) => (
      item.key === 'graduacao_frequencia_18_24'
    )))
      .map((group) => group.key),
    ['educacao_superior_v2'],
  )
  assert.deepEqual(
    groups.filter((group) => group.items.some((item) => (
      item.key === 'docentes_tempo_integral_faculdades'
    )))
      .map((group) => group.key),
    ['educacao_superior_v2'],
  )
})

test('every comparable indicator has a canonical detail key and presentation model', () => {
  const comparableRelations = PNE_2026_GOAL_INDICATOR_CONTRACT.relations
    .filter((item) => (
      [
        PNE_2026_RELATIONSHIP_MODES.PROGRESS,
        PNE_2026_RELATIONSHIP_MODES.TRACKING,
      ].includes(item.mode)
      && canPne2026RelationEnterCycleSummary(item)
    ))
  const cyclePageSource = readFileSync(
    new URL('../../src/pages/CyclePage.jsx', import.meta.url),
    'utf8',
  )

  assert.match(cyclePageSource, /\{ detalhe: itemKey \}/)
  for (const relation of comparableRelations) {
    const indicator = PNE_2026_GOAL_INDICATOR_CONTRACT
      .indicators[relation.indicatorId]
    const presentation = getPneIndicatorPresentation({
      cycle: PNE_2026_CYCLE,
      item: {
        key: relation.indicatorId,
        metaRef: relation.goalId,
      },
      result: {
        available: true,
        dataStatus: 'available',
        distance: -1,
        end_value: 0,
        end_year: 2025,
        meta: 1,
      },
    })

    assert.equal(
      PNE_2026_INDICATOR_GOAL_REFS[relation.indicatorId],
      relation.goalId,
      relation.relationId,
    )
    assert.ok(
      relation.publicLabelOverride ?? indicator?.publicTitle,
      relation.relationId,
    )
    assert.equal(presentation?.mode, relation.mode, relation.relationId)
    assert.deepEqual(
      presentation?.sourceIds,
      indicator.sourceIds,
      relation.relationId,
    )
  }
})

test('every available comparable relation in the active São Leopoldo release can appear in one policy-derived menu', () => {
  const payload = readActiveReleaseMunicipality('4318705')
  const relationsById = new Map(
    PNE_2026_GOAL_INDICATOR_CONTRACT.relations.map((item) => [
      item.relationId,
      item,
    ]),
  )
  const availableComparableResults = payload.results.filter((result) => {
    const canonical = relationsById.get(result.relationId)
    return (
      result.dataStatus === 'available'
      && [
        PNE_2026_RELATIONSHIP_MODES.PROGRESS,
        PNE_2026_RELATIONSHIP_MODES.TRACKING,
      ].includes(canonical?.mode)
      && canPne2026RelationEnterCycleSummary(canonical)
    )
  })
  const groups = buildThematicGroups([{
    key: 'active-release',
    items: availableComparableResults.map((result) => ({
      key: result.indicatorId,
      metaRef: result.goalId,
    })),
  }], PNE_2026_CYCLE)
  const menuKeys = groups.flatMap((group) => group.items.map((item) => item.key))

  assert.equal(availableComparableResults.length, 39)
  assert.equal(menuKeys.length, 39)
  assert.equal(new Set(menuKeys).size, 39)
  assert.deepEqual(
    Object.fromEntries(groups.map((group) => [group.key, group.items.length])),
    {
      atendimento_escolar_v2: 4,
      educacao_tempo_integral_v2: 2,
      aprendizagem_trajetoria_escolar_v2: 9,
      escolaridade_alfabetizacao_v2: 6,
      educacao_profissional_eja_v2: 3,
      profissionais_educacao_v2: 4,
      infraestrutura_escolar_v2: 2,
      gestao_escolar_educacao_ambiental_v2: 3,
      educacao_superior_v2: 6,
    },
  )
  for (const indicatorId of [
    'alfabetizacao',
    'eja_atendimento_18_mais',
    'graduacao_frequencia_18_24',
    'superior_completo_25_34',
    'taxa_bruta_graduacao',
    'docentes_tempo_integral_ies',
    'docentes_tempo_integral_universidades',
    'docentes_tempo_integral_faculdades',
  ]) {
    assert.ok(menuKeys.includes(indicatorId), indicatorId)
  }
  assert.ok(!menuKeys.includes('docentes_tempo_integral_centros_universitarios'))
})

test('real release preserves a valid EJA zero and never turns unavailable literacy into zero', () => {
  const aguaSanta = resolvePne2026PublicDiagnosticV3(
    readActiveReleaseMunicipality('4300059'),
  )
  const aguaSantaResults = mergePne2026DiagnosticResults(null, aguaSanta)
  assert.equal(aguaSantaResults.eja_atendimento_18_mais.available, true)
  assert.equal(aguaSantaResults.eja_atendimento_18_mais.end_value, 0)
  assert.equal(
    applyPneCycleVisibilityPolicy([{
      key: 'eja',
      items: [{
        key: 'eja_atendimento_18_mais',
        metaRef: '11.d',
      }],
    }], aguaSantaResults, PNE_2026_CYCLE)[0].items.length,
    1,
  )

  const alegrete = resolvePne2026PublicDiagnosticV3(
    readActiveReleaseMunicipality('4300406'),
  )
  const alegreteResults = mergePne2026DiagnosticResults(null, alegrete)
  assert.equal(alegreteResults.alfabetizacao.available, false)
  assert.equal(alegreteResults.alfabetizacao.dataStatus, 'unavailable')
  assert.equal(alegreteResults.alfabetizacao.end_value, undefined)
})

test('cycle treats the current diagnostic as authoritative over base results', () => {
  const baseResults = {
    basico_15_17: {
      available: true,
      end_value: 90,
      series: [{ ano: 2025, valor: 90 }],
    },
    medio_tecnico_participacao_publica: {
      available: true,
      end_value: 65,
      meta: 50,
      distance: 15,
      tracks_goal: true,
    },
    temporarios: {
      available: true,
      end_value: 12,
    },
  }
  const merged = mergePne2026DiagnosticResults(baseResults, {
    goals: [{
      results: [{
        current: { unit: 'percent', value: 105, year: 2025 },
        distance: 5,
        indicatorId: 'basico_15_17',
        indicatorReference: { direction: 'at_least', value: 100 },
        mode: 'tracking',
        status: 'Referência alcançada',
      }],
    }],
  })

  assert.equal(merged.basico_15_17.end_value, 105)
  assert.deepEqual(merged.basico_15_17.series, baseResults.basico_15_17.series)
  assert.equal(merged.medio_tecnico_participacao_publica, undefined)
  assert.equal(merged.temporarios, baseResults.temporarios)
  assert.equal(
    mergePne2026DiagnosticResults(baseResults, null)
      .medio_tecnico_participacao_publica,
    undefined,
  )
})

test('the 2026 diagnostic adapter never removes results from the closed cycle', () => {
  const closedCycleResults = {
    creche: { end_value: 40, tracks_goal: true },
    pre_escola: { end_value: 90, tracks_goal: true },
  }

  assert.equal(
    resolvePneCycleMunicipalResults(
      PNE_2014_CYCLE,
      closedCycleResults,
      null,
    ),
    closedCycleResults,
  )
  assert.deepEqual(
    resolvePneCycleMunicipalResults(
      PNE_2026_CYCLE,
      closedCycleResults,
      null,
    ),
    {},
  )
})

test('canonical capabilities authorize tracking and reject contradictory local flags', () => {
  const result = {
    available: true,
    atingida: true,
    distance: 0,
    end_value: 100,
    meta: 100,
    tracks_goal: true,
    display: { status: 'Meta atingida' },
  }

  assert.equal(isPneComparableIndicator({
    cycleId: PNE_2026_CYCLE,
    indicatorKey: 'idade_regular_quinto',
    item: { key: 'idade_regular_quinto', metaRef: '4.b' },
    result,
  }), true)
  assert.equal(isPneComparableIndicator({
    cycleId: PNE_2026_CYCLE,
    indicatorKey: 'temporarios',
    item: { key: 'temporarios', metaRef: '17.d' },
    result,
  }), false)
})

test('closed-cycle comparability and copy remain isolated from the 2026 contract', () => {
  const closedCycleItem = {
    key: 'idade_regular_quinto',
    metaRef: '4.b',
  }
  const closedCycleResult = {
    available: true,
    atingida: false,
    distance: -2,
    meta: 95,
    tracks_goal: true,
    display: { status: 'Meta não atingida' },
  }

  assert.equal(isPneComparableIndicator({
    cycleId: PNE_2014_CYCLE,
    indicatorKey: closedCycleItem.key,
    item: closedCycleItem,
    result: closedCycleResult,
  }), true)
  assert.equal(
    filterPneComparableCategories(
      [{ key: 'closed-cycle', items: [closedCycleItem] }],
      { [closedCycleItem.key]: closedCycleResult },
      PNE_2014_CYCLE,
    )[0].items[0].cycleDisplayPolicy.state,
    PNE_CYCLE_PRESENTATION_STATES.CONCLUSIVE,
  )
  assert.equal(getPneCycleCopy(PNE_2014_CYCLE).status.achieved, 'Meta atingida')
  assert.equal(getPneCycleCopy(PNE_2014_CYCLE).status.below, 'Meta não atingida')
  assert.equal(
    getPneCycleCopy(PNE_2026_CYCLE).status.achieved,
    'Referência alcançada',
  )
  assert.equal(
    getPneCycleCopy(PNE_2026_CYCLE).summary.achievedLabel,
    'Referência alcançada',
  )
})

test('closed-cycle visibility keeps every catalog item and assigns presentation states', () => {
  const catalog = JSON.parse(readFileSync(
    new URL('../../public/data/indicadores.json', import.meta.url),
    'utf8',
  ))
  const saoLeopoldo = JSON.parse(readFileSync(
    new URL('../../public/data/municipios/4318705/index.json', import.meta.url),
    'utf8',
  ))
  const categories = catalog.cycles[PNE_2014_CYCLE].categories.map((category) => ({
    ...category,
    items: category.items.map((item) => ({
      ...item,
      metaRef: PNE_2014_INDICATOR_GOAL_REFS[item.key],
    })),
  }))
  const results = saoLeopoldo[PNE_2014_CYCLE].indicadores
  const visibleCategories = applyPneCycleVisibilityPolicy(
    categories,
    results,
    PNE_2014_CYCLE,
  )
  const visibleItems = visibleCategories.flatMap((category) => category.items)
  const thematicItems = buildThematicGroups(visibleCategories)
    .flatMap((group) => group.items)
  const stateByKey = new Map(
    visibleItems.map((item) => [item.key, item.cycleDisplayPolicy.state]),
  )

  assert.equal(visibleItems.length, 24)
  assert.equal(thematicItems.length, 24)
  assert.equal(new Set(thematicItems.map((item) => item.key)).size, 24)
  assert.deepEqual(
    [...stateByKey.values()].reduce((counts, state) => ({
      ...counts,
      [state]: (counts[state] ?? 0) + 1,
    }), {}),
    {
      [PNE_CYCLE_PRESENTATION_STATES.CONCLUSIVE]: 21,
      [PNE_CYCLE_PRESENTATION_STATES.OBSERVED]: 3,
    },
  )

  for (const key of [
    'creche',
    'pre_escola',
    'basico_6_17',
    'basico_15_17',
    'basico_integral',
    'escolas_integral',
    'eja_integrada_educacao_profissional_percentual',
    'medio_tecnico_total',
    'medio_tecnico_participacao_publica',
    'medio_tecnico',
  ]) {
    assert.ok(stateByKey.has(key), key)
  }

  for (const key of ['medio_tecnico_total', 'medio_tecnico']) {
    const policy = visibleItems.find((item) => item.key === key).cycleDisplayPolicy
    assert.equal(policy.state, PNE_CYCLE_PRESENTATION_STATES.OBSERVED)
    assert.equal(policy.statusLabel, 'Resultado observado')
    assert.equal(policy.showGoalComparison, false)
    assert.equal(policy.goalContextLabel, 'Indicador de acompanhamento da Meta 11')
  }
  const alfabetizacaoPolicy = visibleItems.find(
    (item) => item.key === 'alfabetizacao',
  ).cycleDisplayPolicy
  assert.equal(
    alfabetizacaoPolicy.state,
    PNE_CYCLE_PRESENTATION_STATES.OBSERVED,
  )
  assert.equal(alfabetizacaoPolicy.showGoalComparison, false)
  assert.equal(alfabetizacaoPolicy.showStateComparison, true)
  assert.equal(
    alfabetizacaoPolicy.goalContextLabel,
    'Indicador relacionado à Meta 5',
  )
})

test('closed-cycle state policy distinguishes absence from zero without hiding either', () => {
  const observedZero = getPneCycleIndicatorDisplayPolicy({
    cycleId: PNE_2014_CYCLE,
    item: { key: 'observed', metaRef: '10' },
    result: {
      available: true,
      end_value: 0,
      end_year: 2024,
      tracks_goal: false,
    },
  })
  const unavailableNull = getPneCycleIndicatorDisplayPolicy({
    cycleId: PNE_2014_CYCLE,
    item: { key: 'unavailable' },
    result: {
      available: true,
      end_value: null,
      series: [{ ano: 2024, valor: null }],
    },
  })
  const explicitlyUnavailable = getPneCycleIndicatorDisplayPolicy({
    cycleId: PNE_2014_CYCLE,
    item: { key: 'unavailable-with-value' },
    result: {
      available: false,
      end_value: 0,
    },
  })

  assert.equal(observedZero.state, PNE_CYCLE_PRESENTATION_STATES.OBSERVED)
  assert.equal(observedZero.visible, true)
  assert.equal(unavailableNull.state, PNE_CYCLE_PRESENTATION_STATES.UNAVAILABLE)
  assert.equal(unavailableNull.visible, true)
  assert.equal(explicitlyUnavailable.state, PNE_CYCLE_PRESENTATION_STATES.UNAVAILABLE)
  assert.equal(explicitlyUnavailable.visible, true)
})

test('raw percentages are unchanged and the above-100 note explains the capped summaries', () => {
  const results = {
    creche: {
      end_value: 102.4,
      series: [{ ano: 2025, valor: 102.4 }],
    },
  }

  assert.equal(
    normalizePopulationPercentResults(
      results,
      [{ key: 'creche', metaRef: '1.a' }],
      PNE_2026_CYCLE,
    ),
    results,
  )
  assert.match(
    getDataSourceParts({
      indicatorKey: 'creche',
      result: results.creche,
    }).methodology,
    /resumos exibem no máximo 100%[\s\S]*valor calculado foi 102,4%/i,
  )
  assert.doesNotMatch(
    getDataSourceParts({
      indicatorKey: 'creche',
      result: { end_value: 99.9 },
    }).methodology,
    /resumos exibem no máximo 100%/i,
  )
})

test('public methodology notes never expose database fields or formula identifiers', () => {
  const technicalIdentifier = /\b(?:(?:[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ0-9]*_)+[A-Za-zÀ-ÿ0-9]+|PC_[A-Z0-9_]+|TP_[A-Z0-9_]+|MEDU\d+)\b/u
  const seen = new Set()

  for (const relation of PNE_2026_GOAL_INDICATOR_CONTRACT.relations) {
    if (seen.has(relation.indicatorId)) continue
    seen.add(relation.indicatorId)
    const note = getDataSourceParts({
      cycle: PNE_2026_CYCLE,
      indicatorKey: relation.indicatorId,
      item: { key: relation.indicatorId, metaRef: relation.goalId },
      result: { end_value: 50, end_year: 2025, goalId: relation.goalId },
    }).methodology

    assert.doesNotMatch(note, technicalIdentifier, relation.relationId)
    assert.doesNotMatch(note, /\b(?:Numerador|Denominador)\s*:/iu, relation.relationId)
  }
})

test('development reconciliation warnings are emitted only once per incompatibility', () => {
  const source = readFileSync(
    new URL('../../src/utils/indicatorValues.js', import.meta.url),
    'utf8',
  )

  assert.match(source, /const emittedPne2026ReconciliationWarnings = new Set\(\)/)
  assert.match(source, /!emittedPne2026ReconciliationWarnings\.has\(warning\)/)
  assert.match(source, /emittedPne2026ReconciliationWarnings\.add\(warning\)/)
})

test('2026 consumers rely only on canonical relation capabilities', () => {
  const consumers = [
    '../../src/components/MetaCard.jsx',
    '../../src/components/IndicatorDetail.jsx',
    '../../src/pages/CyclePage.jsx',
    '../../src/pages/PneLegalGoalsPage.jsx',
  ].map((path) => readFileSync(new URL(path, import.meta.url), 'utf8'))

  for (const source of consumers) {
    assert.doesNotMatch(source, /getPne2026RelationshipMode/)
  }
  assert.doesNotMatch(consumers.join('\n'), /\?\?\s*2036|\|\|\s*2036/)
})
