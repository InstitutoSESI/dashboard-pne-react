import {
  PNE_2026_RELATIONSHIP_MODES,
  canPne2026RelationEnterCycleSummary,
  reconcilePne2026MunicipalResult,
  resolvePne2026Relation,
} from '../data/pne2026GoalIndicatorContract.js'

const PNE_2026_CYCLE = 'pne_2026_2036'
const PNE_2014_CYCLE = 'pne_2014_2024'

export const PNE_CYCLE_PRESENTATION_STATES = Object.freeze({
  CONCLUSIVE: 'conclusive',
  OBSERVED: 'observed',
  UNAVAILABLE: 'unavailable',
})

// Heurísticas preservadas exclusivamente para o ciclo 2014–2024.
export const PNE_CONTEXT_PROXY_INDICATOR_KEYS = new Set([
  'aee',
  'eja_integrada_educacao_profissional',
  'internet',
  'internet_alunos',
  'internet_aprendizagem',
  'internet_comunidade',
  'acesso_internet_computador',
  'acesso_internet_disp_pessoais',
  'rede_local',
  'rede_wireless',
  'banda_larga',
  'proposta_pedagogica',
  'desktop_aluno',
  'comp_portatil_aluno',
  'tablet_aluno',
])

const PNE_GOAL_TRACKING_EXCEPTION_KEYS = new Set([
  'salas_climatizadas',
  'salas_acessiveis',
])

function relationIdentity(indicatorKey, indicatorRelation, item) {
  return {
    goalId:
      indicatorRelation?.legalGoalId ??
      indicatorRelation?.goalId ??
      item?.goalId ??
      item?.metaRef,
    indicatorId:
      indicatorKey ??
      indicatorRelation?.indicatorId ??
      indicatorRelation?.key ??
      item?.key,
  }
}

function canonicalRelation(indicatorKey, indicatorRelation, item) {
  const identity = relationIdentity(indicatorKey, indicatorRelation, item)
  return resolvePne2026Relation(identity.goalId, identity.indicatorId)
}

function isLegacyContextProxyIndicatorKey(indicatorKey) {
  if (PNE_GOAL_TRACKING_EXCEPTION_KEYS.has(indicatorKey)) return false
  return PNE_CONTEXT_PROXY_INDICATOR_KEYS.has(indicatorKey)
}

export function isPneContextProxyRelation(
  indicatorRelation,
  result,
  cycleId,
) {
  const indicatorId = indicatorRelation?.indicatorId ?? indicatorRelation?.key
  if (cycleId === PNE_2026_CYCLE) {
    const relation = canonicalRelation(indicatorId, indicatorRelation)
    return Boolean(
      relation &&
      (
        relation.legacyCoverage === 'aproximada' ||
        (
          relation.mode === PNE_2026_RELATIONSHIP_MODES.PROGRESS &&
          relation.canStatus === false
        )
      ),
    )
  }

  if (PNE_GOAL_TRACKING_EXCEPTION_KEYS.has(indicatorId)) return false
  if (PNE_CONTEXT_PROXY_INDICATOR_KEYS.has(indicatorId)) return true
  if (indicatorRelation?.hasDistance === false) return true
  if (indicatorRelation?.coverage === 'aproximada') return true
  if (result?.tracks_goal === false) return true
  return false
}

function isLegacyApproximateReferenceIndicator({ indicatorKey, item, result }) {
  return (
    item?.monitoring_mode === 'approximate_reference' ||
    result?.monitoring_mode === 'approximate_reference' ||
    isLegacyContextProxyIndicatorKey(indicatorKey)
  )
}

function hasComparableResult(result, { inspectLegacyStatus = true } = {}) {
  if (!result || result.available === false) return false

  const meta = Number(result.meta)
  const distance = Number(result.distance)
  const status = normalizeText(result.display?.status)
  return (
    Number.isFinite(meta) &&
    Number.isFinite(distance) &&
    typeof result.atingida === 'boolean' &&
    (
      !inspectLegacyStatus ||
      (
        !status.includes('visualizacao') &&
        !status.includes('informativo') &&
        !status.includes('indispon') &&
        !status.includes('sem dados') &&
        !status.includes('sem variacao')
      )
    )
  )
}

function isFinitePublishedNumber(value) {
  return typeof value === 'number' && Number.isFinite(value)
}

function hasPublishedResult(result) {
  if (!result || result.available === false) return false
  if (
    isFinitePublishedNumber(result.end_value)
    || isFinitePublishedNumber(result.start_value)
  ) {
    return true
  }
  return (result.series ?? []).some((point) => (
    isFinitePublishedNumber(point?.valor)
  ))
}

export function getPneCycleIndicatorDisplayPolicy({
  cycleId,
  item,
  result,
}) {
  if (cycleId !== PNE_2014_CYCLE) {
    return {
      visible: isPneVisibleIndicator({
        cycleId,
        indicatorKey: item?.key,
        item,
        result,
      }),
    }
  }

  const isConclusive = Boolean(
    result
    && result.available !== false
    && result.tracks_goal === true
    && isFinitePublishedNumber(result.meta)
    && isFinitePublishedNumber(result.distance)
    && typeof result.atingida === 'boolean',
  )
  const state = isConclusive
    ? PNE_CYCLE_PRESENTATION_STATES.CONCLUSIVE
    : hasPublishedResult(result)
      ? PNE_CYCLE_PRESENTATION_STATES.OBSERVED
      : PNE_CYCLE_PRESENTATION_STATES.UNAVAILABLE
  const endYear = isFinitePublishedNumber(result?.end_year)
    ? result.end_year
    : null
  const isChildLiteracyObservation =
    state === PNE_CYCLE_PRESENTATION_STATES.OBSERVED
    && item?.key === 'alfabetizacao'

  return {
    currentLabel: state === PNE_CYCLE_PRESENTATION_STATES.OBSERVED
      ? endYear ? `Resultado final (${endYear})` : 'Resultado final'
      : null,
    goalContextLabel:
      state === PNE_CYCLE_PRESENTATION_STATES.OBSERVED && item?.metaRef
        ? isChildLiteracyObservation
          ? `Indicador relacionado à Meta ${item.metaRef}`
          : `Indicador de acompanhamento da Meta ${item.metaRef}`
        : null,
    showGoalComparison: state === PNE_CYCLE_PRESENTATION_STATES.CONCLUSIVE,
    showStateComparison: isChildLiteracyObservation,
    state,
    statusLabel: state === PNE_CYCLE_PRESENTATION_STATES.CONCLUSIVE
      ? result.atingida
        ? 'Meta atingida'
        : 'Meta não atingida'
      : state === PNE_CYCLE_PRESENTATION_STATES.OBSERVED
        ? 'Resultado observado'
        : 'Sem dados suficientes para conclusão',
    visible: true,
  }
}

export function isPneComparableIndicator({
  cycleId,
  indicatorKey,
  indicatorRelation,
  item,
  result,
}) {
  if (cycleId === PNE_2026_CYCLE) {
    const relation = canonicalRelation(indicatorKey, indicatorRelation, item)
    const authoritativeResult = reconcilePne2026MunicipalResult({
      goalId: relation?.goalId,
      indicatorId: relation?.indicatorId,
      result,
    }).result
    return Boolean(
      relation &&
      [
        PNE_2026_RELATIONSHIP_MODES.PROGRESS,
        PNE_2026_RELATIONSHIP_MODES.TRACKING,
      ].includes(relation.mode) &&
      canPne2026RelationEnterCycleSummary(relation) &&
      relation.canDistance &&
      relation.canStatus &&
      hasComparableResult(authoritativeResult, { inspectLegacyStatus: false }),
    )
  }

  if (!hasComparableResult(result)) return false
  if (isLegacyContextProxyIndicatorKey(indicatorKey)) return false
  if (isPneContextProxyRelation(indicatorRelation, result, cycleId)) return false
  if (result.tracks_goal !== true) return false
  if (indicatorRelation?.hasDistance === false) return false
  return true
}

function isPneVisibleIndicator({
  cycleId,
  indicatorKey,
  item,
  result,
}) {
  if (cycleId === PNE_2026_CYCLE) {
    const relation = canonicalRelation(indicatorKey, undefined, item)
    if (
      !relation
      || !canPne2026RelationEnterCycleSummary(relation)
      || relation.mode === PNE_2026_RELATIONSHIP_MODES.HIDDEN
    ) {
      return false
    }
    return isPneComparableIndicator({
      cycleId,
      indicatorKey,
      item,
      result,
    })
  }

  if (
    item?.show_in_cycle === true &&
    isLegacyApproximateReferenceIndicator({ indicatorKey, item, result })
  ) {
    return true
  }
  return isPneComparableIndicator({
    cycleId,
    indicatorKey,
    item,
    result,
  })
}

export function filterPneComparableCategories(
  categories,
  results = {},
  cycleId,
) {
  return applyPneCycleVisibilityPolicy(categories, results, cycleId)
}

export function applyPneCycleVisibilityPolicy(
  categories,
  results = {},
  cycleId,
) {
  return categories
    .map((category) => ({
      ...category,
      items: (category.items ?? []).flatMap((item) => {
        const displayPolicy = getPneCycleIndicatorDisplayPolicy({
          cycleId,
          item,
          result: results?.[item.key],
        })
        if (!displayPolicy.visible) return []
        return cycleId === PNE_2014_CYCLE
          ? [{ ...item, cycleDisplayPolicy: displayPolicy }]
          : [item]
      }),
    }))
    .filter((category) => category.items.length > 0)
}

export function canIncludePneCycleSummary({ cycleId, item, result }) {
  if (cycleId === PNE_2026_CYCLE) {
    const relation = canonicalRelation(item?.key, undefined, item)
    return Boolean(
      canPne2026RelationEnterCycleSummary(relation)
      && result
      && result.available !== false
      && hasComparableResult(result, { inspectLegacyStatus: false }),
    )
  }

  return getPneCycleIndicatorDisplayPolicy({
    cycleId,
    item,
    result,
  }).state === PNE_CYCLE_PRESENTATION_STATES.CONCLUSIVE
}

function normalizeText(value) {
  return String(value ?? '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLocaleLowerCase('pt-BR')
}
