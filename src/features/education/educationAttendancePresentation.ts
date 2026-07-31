import type {
  DisplayPercentage,
  EducationAttendancePoint,
  EducationProjectedIndicator,
} from './educationAttendanceTypes'
import { getPne2026IndicatorReferenceProfile } from '../../data/pne2026GoalIndicatorContract.js'

export interface EducationProjectionViewContract {
  available: boolean
  displayWasCapped: boolean
  distance_to_target_2036?: number | null
  status_2036?: 'tende_a_atingir' | 'nao_tende_a_atingir' | null
  historical_display: DisplayPercentage[]
  historical_percent: Array<number | null>
  historical_years: number[]
  projected_2036: number | null
  projected_display: DisplayPercentage[]
  projected_end_year: number | null
  projected_percent: Array<number | null>
  raw_historical_percent: Array<number | null>
  raw_projected_2036: number | null
  raw_projected_percent: Array<number | null>
  target_label?: string
  target_kind?: 'legal' | 'monitoring' | 'configured'
  target_direction?: 'at_least' | 'at_most'
  target_percent?: number | null
  target_reference_id?: string | null
  target_validation_status?: string | null
  target_year?: number | null
  trend?: EducationProjectedIndicator['scenario']['trend']
  denominator_model?: EducationProjectedIndicator['scenario']['denominatorModel']
  uncertainty?: EducationProjectedIndicator['scenario']['uncertainty']
  warnings: string[]
  years: number[]
}

const EXCLUDED_PROJECTION_IDENTIFIERS = new Set([
  'constant',
  'damped_numerator_trend_with_state_age_denominator',
  'last_components',
  'last_value',
  'maintenance',
  'persistence',
  'tendencia suavizada com limite de variacao anual para reduzir extrapolacoes excessivas',
  'tendencia suavizada com limite plausivel por indicador para reduzir extrapolacoes excessivas',
])

function finiteRawValue(point: EducationAttendancePoint | undefined): number | null {
  return point?.rawValue != null && Number.isFinite(point.rawValue) ? point.rawValue : null
}

function referenceTrajectory(indicator: EducationProjectedIndicator): EducationAttendancePoint[] {
  if (indicator.kind !== 'integral_coverage') return []
  return (indicator.reference.trajectory ?? []).map((point) => ({
    denominator: point.denominator ?? null,
    numerator: point.numerator ?? null,
    rawValue: point.rawValue ?? point.value ?? null,
    year: point.year,
  }))
}

function getProjectionPoints(indicator: EducationProjectedIndicator): EducationAttendancePoint[] {
  const configuredTrajectory = referenceTrajectory(indicator)
  return configuredTrajectory.length > 0 ? configuredTrajectory : indicator.scenario?.projected ?? []
}

/**
 * Regra única para publicação na página. Metadados semânticos são avaliados
 * primeiro; a comparação numérica usa os valores brutos, sem arredondamento.
 */
export function isDisplayableProjection(indicator: EducationProjectedIndicator | null | undefined): boolean {
  if (!indicator) return false

  const historical = indicator.historical
    .filter((point) => Number.isFinite(point.year) && finiteRawValue(point) != null)
    .sort((left, right) => left.year - right.year)
  const lastObserved = historical[historical.length - 1]
  const lastObservedValue = finiteRawValue(lastObserved)
  if (!lastObserved || lastObservedValue == null) return false

  const future = getProjectionPoints(indicator)
    .filter((point) => point.year > lastObserved.year && finiteRawValue(point) != null)
    .sort((left, right) => left.year - right.year)
  const finalPoint = future[future.length - 1]
  if (!finalPoint || finiteRawValue(finalPoint) == null) return false

  const isPlanningTrajectory = indicator.kind === 'integral_coverage'
    && (referenceTrajectory(indicator).length > 0 || indicator.scenario?.type === 'pne_reference_trajectory')
  if (isPlanningTrajectory) return true

  if (!indicator.scenario || indicator.scenario.status !== 'available') return false

  const semanticIdentifiers = [
    indicator.scenario.type,
    indicator.scenario.model,
    indicator.scenario.method,
  ]
    .filter((value): value is string => typeof value === 'string')
    .map((value) => value.trim().toLowerCase())

  if (semanticIdentifiers.some((value) => EXCLUDED_PROJECTION_IDENTIFIERS.has(value))) {
    return false
  }

  return !future.every((point) => finiteRawValue(point) === lastObservedValue)
}

export function toDisplayPercentage(rawValue: number | null | undefined): DisplayPercentage {
  if (rawValue == null || !Number.isFinite(rawValue)) {
    return { displayValue: null, displayWasCapped: false, rawValue: null }
  }

  return {
    displayValue: Math.min(100, rawValue),
    displayWasCapped: rawValue > 100,
    rawValue,
  }
}

export function projectionAssumptionText(
  kind: EducationProjectedIndicator['kind'],
  selectedBasis: string | null | undefined,
): string {
  if (kind === 'integral_coverage') {
    return 'A trajetória parte do valor atual e mostra o avanço necessário para alcançar as referências de 2031 e 2036.'
  }
  if (selectedBasis === 'municipal_state_shrunk_theil_sen_log') {
    return 'Combina o histórico de matrículas do município e do Rio Grande do Sul com a mudança esperada da população da faixa etária.'
  }
  if (selectedBasis === 'state_aggregate_damped_holt') {
    return 'Considera a evolução das matrículas no Rio Grande do Sul e a mudança esperada da população da faixa etária no município.'
  }
  return 'Mantém como referência o número mais recente de matrículas e considera a mudança esperada da população da faixa etária no município.'
}

function targetFor(indicator: EducationProjectedIndicator, finalYear: number | null) {
  const canonical = getPne2026IndicatorReferenceProfile(
    indicator.indicatorKey,
    indicator.observed?.year,
  )
  if (canonical?.kind === 'legal' && indicator.kind === 'integral_coverage') {
    const milestone = canonical.milestones.find((item) => item.year === finalYear)
      ?? canonical.milestones[canonical.milestones.length - 1]
    return milestone
      ? {
          ...milestone,
          kind: canonical.kind,
          label: canonical.label,
          referenceId: canonical.referenceId,
          validationStatus: canonical.validationStatus,
        }
      : null
  }
  if (canonical) return canonical
  if (indicator.kind === 'age_coverage') return indicator.reference
  const targets = indicator.reference.targets
  const target = targets.find((item) => item.year === finalYear)
    ?? targets[targets.length - 1]
  return target
    ? {
        ...target,
        kind: indicator.reference.kind ?? 'configured',
        label: indicator.reference.label ?? 'Referência configurada',
        referenceId: indicator.reference.referenceId ?? null,
        validationStatus: indicator.reference.validationStatus,
      }
    : null
}

export function toProjectionView(indicator: EducationProjectedIndicator): EducationProjectionViewContract {
  const projected = getProjectionPoints(indicator)
    .filter((point) => point.year > (indicator.observed?.year ?? -Infinity))
    .sort((left, right) => left.year - right.year)
  const historicalDisplay = indicator.historical.map((point) => toDisplayPercentage(point.rawValue))
  const projectedDisplay = projected.map((point) => toDisplayPercentage(point.rawValue))
  const finalPoint = projected[projected.length - 1]
  const finalRawValue = finiteRawValue(finalPoint)
  const finalDisplayValue = toDisplayPercentage(finalRawValue).displayValue
  const finalYear = finalPoint?.year ?? null
  const target = targetFor(indicator, finalYear)
  const targetValue = target?.value == null ? null : Number(target.value)
  const targetDirection = target?.direction === 'at_most' ? 'at_most' : 'at_least'
  const hasComparableTarget = finalDisplayValue != null
    && targetValue != null
    && Number.isFinite(targetValue)
  const distanceToTarget = hasComparableTarget ? finalDisplayValue - targetValue : null
  const reachesTarget = hasComparableTarget
    ? targetDirection === 'at_most'
      ? finalDisplayValue <= targetValue + 0.05
      : finalDisplayValue >= targetValue - 0.05
    : null

  return {
    available: isDisplayableProjection(indicator),
    displayWasCapped: [...historicalDisplay, ...projectedDisplay].some((point) => point.displayWasCapped),
    distance_to_target_2036: distanceToTarget,
    status_2036: reachesTarget == null
      ? null
      : reachesTarget ? 'tende_a_atingir' : 'nao_tende_a_atingir',
    historical_display: historicalDisplay,
    historical_percent: historicalDisplay.map((point) => point.displayValue),
    historical_years: indicator.historical.map((point) => point.year),
    projected_2036: finalDisplayValue,
    projected_display: projectedDisplay,
    projected_end_year: finalYear,
    projected_percent: projectedDisplay.map((point) => point.displayValue),
    raw_historical_percent: indicator.historical.map((point) => point.rawValue),
    raw_projected_2036: finalRawValue,
    raw_projected_percent: projected.map((point) => point.rawValue),
    target_kind: target?.kind,
    target_direction: target ? targetDirection : undefined,
    target_label: target?.label,
    target_percent: target?.value ?? null,
    target_reference_id: target?.referenceId ?? null,
    target_validation_status: target?.validationStatus ?? null,
    target_year: target?.year ?? null,
    trend: indicator.scenario?.trend,
    denominator_model: indicator.scenario?.denominatorModel,
    uncertainty: indicator.scenario?.uncertainty,
    warnings: indicator.diagnostics.warnings,
    years: projected.map((point) => point.year),
  }
}
