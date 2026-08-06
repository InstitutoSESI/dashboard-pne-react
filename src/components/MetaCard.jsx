import { StatusBadge } from './StatusBadge'
import {
  formatIndicatorValue,
  formatMetaValue,
  getIndicatorTitle,
  resolveIndicatorUnit,
  roundPpString,
} from '../utils/format'
import { formatPpDifference, getStateReferenceComparison } from '../utils/stateReference'
import { getPneCycleCopy } from '../utils/pneCycleCopy'
import { InteractionChevron } from './InteractionChevron'
import { buildPne2026AccumulativePresentationModel } from '../utils/pneAccumulativeCycle'
import {
  PNE_2026_RELATIONSHIP_MODES,
  reconcilePne2026MunicipalResult,
} from '../data/pne2026GoalIndicatorContract'
import {
  PNE_CYCLE_PRESENTATION_STATES,
  isPneComparableIndicator,
} from '../utils/pneDisplayRules'
import {
  formatApproximateDifference,
  formatApproximatePercent,
  getPneIndicatorPresentation,
  isApproximateIndicator,
  isComparableIndicator,
  toPnePercentDisplay,
} from '../utils/pneIndicatorPresentation'

const STATE_REFERENCE_EPSILON = 0.05
const PNE_2026_CYCLE = 'pne_2026_2036'

export function MetaCard({
  buttonRef,
  cycle,
  details = null,
  isSelected = false,
  item,
  onSelect,
  result: municipalResult,
  stateReference,
  stageLabel,
}) {
  const reconciliation = cycle === PNE_2026_CYCLE
    ? reconcilePne2026MunicipalResult({
        goalId: item?.metaRef,
        indicatorId: item?.key,
        result: municipalResult,
      })
    : { context: null, result: municipalResult }
  const result = reconciliation.result
  const displayPolicy = item?.cycleDisplayPolicy ?? null
  const presentation = cycle === PNE_2026_CYCLE
    ? getPneIndicatorPresentation({
        cycle,
        item,
        relationContext: reconciliation.context,
        result,
      })
    : null
  const cycleCopy = getPneCycleCopy(cycle)
  const unit = resolveIndicatorUnit(item, result)
  const isApproximate = !displayPolicy && isApproximateIndicator(item, result)
  const canonicalRelation = reconciliation.context?.relation
  const relationshipMode = canonicalRelation?.mode
  const isComplementary = relationshipMode === PNE_2026_RELATIONSHIP_MODES.COMPLEMENTARY
  const isProgressRelationship = cycle !== PNE_2026_CYCLE
    || [
      PNE_2026_RELATIONSHIP_MODES.PROGRESS,
      PNE_2026_RELATIONSHIP_MODES.TRACKING,
    ].includes(relationshipMode)
  const comparable = displayPolicy
    ? displayPolicy.state === PNE_CYCLE_PRESENTATION_STATES.CONCLUSIVE
    : cycle === PNE_2026_CYCLE
    ? isPneComparableIndicator({
        cycleId: cycle,
        indicatorKey: item?.key,
        item,
        result,
      })
    : isComparableIndicator(result)
  const accumulativePresentation = isProgressRelationship
    ? buildPne2026AccumulativePresentationModel({
        cycle,
        indicatorKey: item?.key,
        details,
        presentationMode: item?.presentationMode,
      })
    : null
  const baseStatus = displayPolicy?.state === PNE_CYCLE_PRESENTATION_STATES.OBSERVED
    ? {
        label: displayPolicy.statusLabel,
        rawStatus: result?.display?.status ?? '',
        state: 'no-goal',
        tone: 'muted',
      }
    : displayPolicy?.state === PNE_CYCLE_PRESENTATION_STATES.UNAVAILABLE
      ? {
          label: displayPolicy.statusLabel,
          rawStatus: result?.display?.status ?? '',
          state: 'missing',
          tone: 'muted',
        }
    : displayPolicy?.state === PNE_CYCLE_PRESENTATION_STATES.CONCLUSIVE
      ? getMetaCardStatus(result, true, cycleCopy, false)
    : isComplementary
    ? {
        label: 'Indicador complementar',
        rawStatus: '',
        state: 'muted',
      }
    : accumulativePresentation
      ? getAccumulativeMetaCardStatus(accumulativePresentation)
      : getMetaCardStatus(result, comparable, cycleCopy, isApproximate)
  const status = presentation && !isComplementary
    ? {
        ...baseStatus,
        label: presentation.statusText,
        state: presentation.statusState ?? baseStatus.state,
        tone: presentation.statusTone ?? baseStatus.tone,
      }
    : baseStatus
  const isNextCycle = cycle === 'pne_2026_2036'
  const isDiscrete = ['binaryDeclaration', 'countOfTotal'].includes(
    presentation?.valueKind,
  )
  const summaryCurrentValue = unit === 'percent'
    ? toPnePercentDisplay(result?.end_value).displayValue
    : result?.end_value
  const summaryDistance = unit === 'percent'
    && Number.isFinite(Number(summaryCurrentValue))
    && Number.isFinite(Number(result?.meta))
    ? Number(summaryCurrentValue) - Number(result.meta)
    : null
  const currentValue = displayPolicy?.state === PNE_CYCLE_PRESENTATION_STATES.UNAVAILABLE
    ? '—'
    : accumulativePresentation
    ? accumulativePresentation.currentDisplay
    : presentation
    ? presentation.currentText
    : result
    ? isApproximate
      ? formatApproximatePercent(summaryCurrentValue)
      : formatIndicatorValue(summaryCurrentValue, unit)
    : '—'
  const referenceValue = result?.reference_value ?? item?.reference_value
  const metaValue = displayPolicy && !displayPolicy.showGoalComparison
    ? '—'
    : accumulativePresentation
    ? accumulativePresentation.referenceDisplay
    : presentation
    ? presentation.referenceText
    : comparable
    ? formatMetaValue(result, unit)
    : isApproximate
      ? formatIndicatorValue(referenceValue, unit)
      : 'Sem meta'
  const progress = displayPolicy && !displayPolicy.showGoalComparison
    ? null
    : accumulativePresentation
    ? accumulativePresentation.progress
    : comparable ? getProgressPercent(result) : null
  const supportValue = displayPolicy?.state === PNE_CYCLE_PRESENTATION_STATES.OBSERVED
    ? roundPpString(result?.display?.variation ?? '—')
    : displayPolicy?.state === PNE_CYCLE_PRESENTATION_STATES.UNAVAILABLE
      ? '—'
    : accumulativePresentation
    ? accumulativePresentation.distanceDisplay
    : presentation
    ? presentation.distanceText
    : comparable
    ? summaryDistance != null
      ? formatPpDifference(summaryDistance)
      : roundPpString(result?.display?.distance ?? '—')
    : isApproximate
      ? formatApproximateDifference(result?.reference_difference)
      : roundPpString(result?.display?.variation ?? '—')
  const supportLabel = displayPolicy?.state === PNE_CYCLE_PRESENTATION_STATES.OBSERVED
    ? 'Evolução'
    : accumulativePresentation
    ? accumulativePresentation.distanceLabel
    : presentation
    ? presentation.distanceLabel
    : comparable
    ? 'Distância'
    : isApproximate
      ? 'Diferença'
      : 'Variação'
  const identifier = item?.metaRef ? `Meta ${item.metaRef}` : 'Indicador'
  const title = getIndicatorTitle(item, result)
  const rawStateComparison = accumulativePresentation
    || isComplementary
    || (
      displayPolicy
      && !displayPolicy.showGoalComparison
      && !displayPolicy.showStateComparison
    )
    ? null
    : getStateReferenceComparison(stateReference, item?.key, result, unit)
  const stateComparison = getPneStateComparisonDisplay(
    rawStateComparison,
    summaryCurrentValue,
    unit,
  )
  const stateComparisonTone = stateComparison
    ? getStateComparisonTone(stateComparison.difference)
    : null
  const cardAriaLabel = `Abrir detalhe do indicador ${title}`
  const showTargetMetric = displayPolicy
    ? displayPolicy.showGoalComparison
    : !isComplementary
  const showStatusBadge = displayPolicy ? true : !isComplementary
  const showSupportMetric = displayPolicy
    ? displayPolicy.state !== PNE_CYCLE_PRESENTATION_STATES.UNAVAILABLE
    : presentation?.showDistance !== false
  const progressMessage = displayPolicy?.state === PNE_CYCLE_PRESENTATION_STATES.OBSERVED
    ? displayPolicy.goalContextLabel ?? 'Resultado de acompanhamento'
    : displayPolicy?.state === PNE_CYCLE_PRESENTATION_STATES.UNAVAILABLE
      ? displayPolicy.statusLabel
      : isComplementary
        ? 'Apoia a leitura da meta; não mede seu cumprimento.'
        : accumulativePresentation?.comparisonTitle
          ?? (isApproximate ? 'Referência legal final: 50% em 2036' : 'Sem meta comparável')

  return (
    <button
      className={`meta-card meta-card--cycle interaction-card--explorable meta-card--${status.state}${isNextCycle ? ' meta-card--next-cycle' : ' meta-card--closed-cycle'}${accumulativePresentation ? ` meta-card--${accumulativePresentation.kind}` : ''}${isDiscrete ? ` meta-card--discrete meta-card--discrete-${presentation.valueKind}` : ''}${isSelected ? ' is-selected' : ''}`}
      ref={buttonRef}
      type="button"
      onClick={onSelect}
      aria-label={cardAriaLabel}
      aria-pressed={isSelected}
      title={title}
    >
      <span className="meta-card__topline">
        <span className="meta-card__identifier">{identifier}</span>
        {showStatusBadge ? (
          <StatusBadge
            displayStatus={status.label}
            status={status.rawStatus}
            title={status.label}
            tone={status.tone}
          />
        ) : null}
      </span>

      <span className="meta-card__title">{title}</span>

      <span className="meta-card__value-row">
        <span className="meta-card__metric meta-card__metric--current">
          <span>
            {accumulativePresentation?.currentLabel
              ?? presentation?.listValueLabel
              ?? displayPolicy?.currentLabel
              ?? 'Município'}
          </span>
          <strong>{currentValue}</strong>
        </span>
        {showTargetMetric ? (
          <span className="meta-card__metric meta-card__metric--target">
            <span>
              {presentation?.cardReferenceLabel
                ?? accumulativePresentation?.referenceLabel
                ?? presentation?.referenceLabel
                ?? (isApproximate ? 'Ref.' : isNextCycle ? 'Referência' : 'Meta PNE')}
            </span>
            <strong>{metaValue}</strong>
          </span>
        ) : null}
        {showSupportMetric ? (
          <span className="meta-card__metric meta-card__metric--distance">
            <span>{presentation?.cardDistanceLabel ?? supportLabel}</span>
            <strong>{supportValue}</strong>
          </span>
        ) : null}
      </span>

      {accumulativePresentation?.kind === 'public-share' ? null : (
        <span className="meta-card__progress-group">
          {isDiscrete ? (
            <span
              className="meta-card__progress meta-card__progress--discrete"
              aria-label={`${presentation.currentText}; ${presentation.referenceLabel}: ${presentation.referenceText}`}
            >
              {Array.from({ length: presentation.segmentCount }, (_value, index) => (
                <span
                  className={index < presentation.filledSegments ? 'is-filled' : ''}
                  key={index}
                />
              ))}
            </span>
          ) : progress !== null ? (
            <span
              className="meta-card__progress"
              aria-label={accumulativePresentation
                ? accumulativePresentation.comparisonAriaLabel
                : `Comparação do resultado municipal ${currentValue} com a referência ${metaValue}`}
            >
              <span style={{ width: `${progress}%` }} />
            </span>
          ) : (
            <span className="meta-card__no-progress">
              {progressMessage}
            </span>
          )}
          {accumulativePresentation?.comparisonTitle ? (
            <span className="meta-card__progress-caption">
              {accumulativePresentation.comparisonTitle}
            </span>
          ) : null}
        </span>
      )}

      {stateComparison ? (
        <span
          className={`meta-card__state-reference meta-card__state-reference--${stateComparisonTone}`}
          aria-label={`Referência RS ${formatIndicatorValue(stateComparison.stateValue, unit)}; Município vs RS ${formatPpDifference(stateComparison.difference)}; ano ${stateComparison.year}`}
        >
          <span>
            <span>Referência RS</span>
            <strong>{formatIndicatorValue(stateComparison.stateValue, unit)}</strong>
          </span>
          <span>
            <span>Município vs RS</span>
            <strong>{formatPpDifference(stateComparison.difference)}</strong>
          </span>
        </span>
      ) : null}

      <span className="meta-card__footer">
        {accumulativePresentation?.footerText || stageLabel ? (
          <span>{accumulativePresentation?.footerText ?? stageLabel}</span>
        ) : null}
        <InteractionChevron />
      </span>
    </button>
  )
}

function getAccumulativeMetaCardStatus(model) {
  const state = model.achieved === true
    ? 'success'
    : model.achieved === false
      ? 'warning'
      : 'missing'

  return {
    label: model.statusLabel,
    rawStatus: model.statusLabel,
    state,
    tone: model.tone,
  }
}

function getStateComparisonTone(difference) {
  const numeric = Number(difference)
  if (!Number.isFinite(numeric) || Math.abs(numeric) <= STATE_REFERENCE_EPSILON) {
    return 'neutral'
  }
  return numeric > 0 ? 'positive' : 'negative'
}

function getMetaCardStatus(result, comparable, cycleCopy, isApproximate) {
  const rawStatus = result?.display?.status ?? ''
  const normalized = String(rawStatus).toLocaleLowerCase('pt-BR')

  if (
    !result ||
    result.available === false ||
    normalized.includes('indispon') ||
    normalized.includes('sem dados')
  ) {
    return { label: cycleCopy.status.missing, rawStatus, state: 'missing', tone: 'muted' }
  }

  if (isApproximate) {
    return { label: 'Indicador aproximado', rawStatus, state: 'no-goal', tone: 'info' }
  }

  if (!comparable || normalized.includes('visualiza') || normalized.includes('informativo')) {
    return { label: 'Sem meta', rawStatus, state: 'no-goal', tone: 'muted' }
  }

  if (result.atingida === true) {
    return { label: cycleCopy.status.achieved, rawStatus, state: 'success', tone: 'success' }
  }

  const isDanger =
    normalized.includes('distante') ||
    normalized.includes('crítico') ||
    normalized.includes('critico') ||
    normalized.includes('não atingida') ||
    normalized.includes('nao atingida')

  if (result.atingida === false) {
    if (result.direction === 'at_most') {
      return {
        label: cycleCopy.status.aboveLimit ?? cycleCopy.status.below,
        rawStatus,
        state: 'warning',
        tone: 'warning',
      }
    }
    return {
      label: cycleCopy.status.below,
      rawStatus,
      state: isDanger ? 'danger' : 'warning',
      tone: isDanger ? 'danger' : 'warning',
    }
  }

  return { label: cycleCopy.status.missing, rawStatus, state: 'missing', tone: 'muted' }
}

function getProgressPercent(result) {
  const current = Number(result?.end_value)
  const meta = Number(result?.meta)
  if (!Number.isFinite(current) || !Number.isFinite(meta) || meta <= 0 || current < 0) {
    return null
  }
  if (result?.direction === 'at_most') {
    if (current <= meta) return 100
    return Math.max(0, Math.min(100, (meta / current) * 100))
  }
  return Math.max(0, Math.min(100, (current / meta) * 100))
}

function getPneStateComparisonDisplay(comparison, municipalityValue, unit) {
  if (!comparison || unit !== 'percent') return comparison
  const municipalityDisplay = toPnePercentDisplay(municipalityValue).displayValue
  const stateDisplay = toPnePercentDisplay(comparison.stateValue).displayValue
  if (municipalityDisplay == null || stateDisplay == null) return comparison

  return {
    ...comparison,
    difference: municipalityDisplay - stateDisplay,
    municipalityValue: municipalityDisplay,
    stateValue: stateDisplay,
  }
}
