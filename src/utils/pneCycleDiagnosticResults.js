import {
  PNE_2026_GOAL_INDICATOR_CONTRACT,
  PNE_2026_RELATIONSHIP_MODES,
  canPne2026RelationEnterCycleSummary,
} from '../data/pne2026GoalIndicatorContract.js'

const COMPARABLE_MODES = new Set([
  PNE_2026_RELATIONSHIP_MODES.PROGRESS,
  PNE_2026_RELATIONSHIP_MODES.TRACKING,
])

export function resolvePneCycleMunicipalResults(cycleId, municipalResults, diagnostic) {
  return cycleId === 'pne_2026_2036'
    ? mergePne2026DiagnosticResults(municipalResults, diagnostic)
    : municipalResults
}

export function mergePne2026DiagnosticResults(municipalResults, diagnostic) {
  const merged = { ...(municipalResults ?? {}) }
  for (const relation of PNE_2026_GOAL_INDICATOR_CONTRACT.relations) {
    if (
      COMPARABLE_MODES.has(relation.mode)
      && canPne2026RelationEnterCycleSummary(relation)
    ) {
      delete merged[relation.indicatorId]
    }
  }
  if (!diagnostic) return merged

  for (const result of diagnostic.goals.flatMap((goal) => goal.results ?? [])) {
    const baseResult = municipalResults?.[result.indicatorId] ?? {}
    if (result.mode === PNE_2026_RELATIONSHIP_MODES.HIDDEN) continue
    const dataStatus = result.dataStatus ?? 'available'
    if (dataStatus !== 'available') {
      merged[result.indicatorId] = {
        ...baseResult,
        available: false,
        dataStatus,
        dataStatusLabel: result.dataStatusLabel,
        monitoringMode: result.mode,
        monitoring_mode: result.mode,
        reasonCode: result.reasonCode,
      }
      continue
    }
    if (!Number.isFinite(result.current?.value)) continue

    if (result.mode === PNE_2026_RELATIONSHIP_MODES.COMPLEMENTARY) {
      merged[result.indicatorId] = {
        ...baseResult,
        available: true,
        dataStatus,
        end_value: result.current.value,
        end_year: result.current.year,
        numerator: result.numerator ?? result.current.numerator ?? null,
        denominator: result.denominator ?? result.current.denominator ?? null,
        value_mode: result.current.unit,
        tracks_goal: false,
        monitoringMode: result.mode,
        monitoring_mode: result.mode,
      }
      continue
    }

    if (
      !COMPARABLE_MODES.has(result.mode)
      || !Number.isFinite(result.indicatorReference?.value)
      || !Number.isFinite(result.distance)
    ) continue

    merged[result.indicatorId] = {
      ...baseResult,
      available: true,
      dataStatus,
      end_value: result.current.value,
      end_year: result.current.year,
      numerator: result.numerator ?? result.current.numerator ?? null,
      denominator: result.denominator ?? result.current.denominator ?? null,
      value_mode: result.current.unit,
      meta: result.indicatorReference.value,
      meta_label: result.mode === PNE_2026_RELATIONSHIP_MODES.TRACKING
        ? 'Referência de acompanhamento'
        : 'Referência prevista na meta',
      direction: result.indicatorReference.direction ?? result.direction,
      distance: result.distance,
      atingida: result.distance >= 0,
      tracks_goal: true,
      hasDistance: true,
      monitoringMode: result.mode,
      monitoring_mode: result.mode,
      display: {
        ...baseResult.display,
        status: result.status,
      },
    }
  }
  return merged
}
