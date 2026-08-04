import { forwardRef, useEffect, useState } from 'react'
import { Clock3, Database, Flag, Ruler, TrendingDown, TrendingUp } from 'lucide-react'
import {
  floorValueForGoal,
  formatIndicatorValue,
  formatMetaValue,
  getDisplayValue,
  getIndicatorTitle,
  isAccumulativeExpansionIndicator,
  isIdebIndicator,
  isSingleYearIndicator,
  resolveIndicatorUnit,
  roundPpString,
} from '../utils/format'
import {
  clampMarkerPosition,
  getStableVisualDomain,
  projectValueToPercent,
} from '../utils/visualDomain'
import { IndicatorComplementaryData } from './IndicatorComplementaryData'
import { DisclosureChevron } from './DisclosureChevron'
import { IndicatorHistoryChart } from './IndicatorHistoryChart'
import { ChartEmptyState } from './ChartPrimitives'
import { isDemographicCensusIndicator, buildDisplayIndicatorSeries } from '../utils/indicatorSeries'
import { loadIndicatorDetail } from '../data/staticData'
import { PneSourceNotes } from './PneSourceNotes'
import { MetricCard } from './MetricCard'
import { QuickReadingHeading } from './QuickReadingHeading'
import { PNE_2026_GOAL_TEXTS } from '../data/pne2026GoalTexts'
import { PNE_2014_GOAL_TEXTS } from '../data/pne2014GoalTexts'
import { getPneCycleCopy, isClosedPneCycle } from '../utils/pneCycleCopy'
import { formatPpDifference } from '../utils/stateReference'
import { buildPne2026AccumulativePresentationModel } from '../utils/pneAccumulativeCycle'
import { buildPnePercentScale } from '../utils/pneChartSystem'
import {
  ExpansionShareBaselineAnalysis,
  ExpansionShareQuickReading,
  ExpansionShareTechnicalDisclosure,
} from './ExpansionShareBaselineDetail'
import {
  SubsequentExpansionQuickReading,
  SubsequentExpansionTargetAnalysis,
  SubsequentExpansionTracking,
} from './SubsequentExpansionTargetDetail'
import { RatioDualMilestoneDetail } from './RatioDualMilestoneDetail'
import { InequalityPilotSection } from './InequalityPilotSection'
import {
  PNE_2026_GOAL_INDICATOR_CONTRACT,
  PNE_2026_RELATIONSHIP_MODES,
  reconcilePne2026MunicipalResult,
} from '../data/pne2026GoalIndicatorContract'
import {
  PNE_CYCLE_PRESENTATION_STATES,
  isPneComparableIndicator,
} from '../utils/pneDisplayRules'
import {
  buildPneSingleYearDataModel,
  getPneIndicatorPresentation,
  toPnePercentDisplay,
} from '../utils/pneIndicatorPresentation'

const PNE_2026_CYCLE = 'pne_2026_2036'

export const IndicatorDetail = forwardRef(function IndicatorDetail(
  {
    cycle,
    inequalityPilot,
    inequalityPilotLoading,
    item,
    municipioData,
    result: municipalResult,
  },
  ref,
) {
  const reconciliation = cycle === PNE_2026_CYCLE
    ? reconcilePne2026MunicipalResult({
        goalId: item?.metaRef,
        indicatorId: item?.key,
        result: municipalResult,
      })
    : { context: null, result: municipalResult }
  const result = reconciliation.result
  const displayPolicy = item?.cycleDisplayPolicy ?? null
  const cycleCopy = getPneCycleCopy(cycle)
  const isOrganizedPneDetail = cycle === 'pne_2014_2024' || cycle === 'pne_2026_2036'
  const [loadedDetails, setLoadedDetails] = useState(null)
  const [detailLoadState, setDetailLoadState] = useState({
    key: '',
    status: 'idle',
  })
  const fallbackDetails = municipioData?.indicator_details?.[item?.key] ?? null
  const details = loadedDetails ?? fallbackDetails
  const detailRequestKey = `${municipioData?.id_municipio ?? ''}:${item?.key ?? ''}`
  const detailsStatus = details
    ? 'ready'
    : detailLoadState.key === detailRequestKey
      ? detailLoadState.status
      : 'loading'
  const canonicalRelation = reconciliation.context?.relation
  const relationshipMode = canonicalRelation?.mode
  const presentation = cycle === PNE_2026_CYCLE
    ? getPneIndicatorPresentation({
        cycle,
        item,
        relationContext: reconciliation.context,
        result,
      })
    : null
  const isComplementaryRelationship =
    relationshipMode === PNE_2026_RELATIONSHIP_MODES.COMPLEMENTARY
  const isProgressRelationship = cycle !== PNE_2026_CYCLE
    || [
      PNE_2026_RELATIONSHIP_MODES.PROGRESS,
      PNE_2026_RELATIONSHIP_MODES.TRACKING,
    ].includes(relationshipMode)
  const canProject = cycle !== PNE_2026_CYCLE
    ? isProgressRelationship
    : canonicalRelation?.canProjection === true
  const accumulativePresentationModel = isProgressRelationship
    ? buildPne2026AccumulativePresentationModel({
        cycle,
        indicatorKey: item?.key,
        details,
        presentationMode: item?.presentationMode,
      })
    : null

  useEffect(() => {
    let isMounted = true
    const idMunicipio = municipioData?.id_municipio
    const indicatorKey = item?.key
    const requestKey = `${idMunicipio ?? ''}:${indicatorKey ?? ''}`

    setLoadedDetails(null)
    setDetailLoadState({ key: requestKey, status: 'loading' })

    if (!idMunicipio || !indicatorKey) {
      setDetailLoadState({ key: requestKey, status: fallbackDetails ? 'ready' : 'empty' })
      return () => {
        isMounted = false
      }
    }

    loadIndicatorDetail(idMunicipio, indicatorKey)
      .then((data) => {
        if (isMounted) {
          setLoadedDetails(data)
          setDetailLoadState({
            key: requestKey,
            status: data || fallbackDetails ? 'ready' : 'empty',
          })
        }
      })
      .catch(() => {
        if (isMounted) {
          setLoadedDetails(null)
          setDetailLoadState({
            key: requestKey,
            status: fallbackDetails ? 'ready' : 'error',
          })
        }
      })

    return () => {
      isMounted = false
    }
  }, [fallbackDetails, municipioData?.id_municipio, item?.key])

  if (!item) {
    return (
      <section className="detail-panel detail-panel--empty empty-panel" ref={ref}>
        <p>Selecione um indicador para ver os detalhes.</p>
      </section>
    )
  }

  if (displayPolicy?.state === PNE_CYCLE_PRESENTATION_STATES.UNAVAILABLE) {
    return (
      <ClosedCycleUnavailableDetail
        item={item}
        panelRef={ref}
        statusLabel={displayPolicy.statusLabel}
      />
    )
  }

  if (!result) {
    return (
      <section className="detail-panel detail-panel--empty empty-panel" ref={ref}>
        <p>{cycleCopy.emptyResult}</p>
      </section>
    )
  }

  if (item?.presentationMode === 'ratio-dual-milestone') {
    return (
      <RatioDualMilestoneDetail
        cycle={cycle}
        details={details}
        item={item}
        legalReference={reconciliation.context?.legalReference}
        presentation={presentation}
        ref={ref}
        result={result}
        detailsStatus={detailsStatus}
      />
    )
  }

  const cycleMinYear = cycle === 'pne_2014_2024' ? 2014 : null
  const isCensusIndicator = isDemographicCensusIndicator({ indicatorKey: item?.key, item, details })
  const displaySeries = buildDisplayIndicatorSeries({ cycle, result, details, item, indicatorKey: item?.key })
  const currentDetailModel = buildPneCurrentDetailModel({
    accumulativePresentationModel,
    cycle,
  })
  const isExpansionShareBaseline = item?.presentationMode === 'expansion-share-baseline'
  const isAbsoluteExpansionTarget = item?.presentationMode === 'absolute-expansion-target'
  const effectiveCycleMinYear = isCensusIndicator ? null : cycleMinYear
  const filteredStartYear = effectiveCycleMinYear && Number.isFinite(Number(result.start_year)) && Number(result.start_year) < effectiveCycleMinYear
    ? effectiveCycleMinYear
    : startYearFromSeries(displaySeries) ?? result.start_year
  const filteredEndYear = effectiveCycleMinYear
    ? endYearFromSeries(displaySeries) ?? result.end_year
    : result.end_year

  const status = getDisplayValue(result.display, 'status')
  const normalizedStatus = String(status).toLocaleLowerCase('pt-BR')
  const isInformative =
    normalizedStatus.includes('visualiza') || normalizedStatus.includes('informativo')
  const isApproximate = !displayPolicy && isApproximateIndicator(item, result)
  const isObserved = displayPolicy?.state === PNE_CYCLE_PRESENTATION_STATES.OBSERVED
  const isDangerStatus =
    normalizedStatus.includes('distante') ||
    normalizedStatus.includes('crítico') ||
    normalizedStatus.includes('critico') ||
    normalizedStatus.includes('não atingida') ||
    normalizedStatus.includes('nao atingida')
  const tone = isObserved
    ? 'muted'
    : isComplementaryRelationship
    ? 'muted'
    : currentDetailModel
    ? currentDetailModel.tone
    : isApproximate || isInformative
    ? 'muted'
    : result.atingida
      ? 'success'
      : isDangerStatus
        ? 'danger'
        : result.available
        ? 'warning'
        : 'muted'
  const isComparable = displayPolicy
    ? displayPolicy.state === PNE_CYCLE_PRESENTATION_STATES.CONCLUSIVE
    : cycle === PNE_2026_CYCLE
    ? isPneComparableIndicator({
        cycleId: cycle,
        indicatorKey: item?.key,
        item,
        result,
      })
    : isComparableIndicator(result)
  const rawStartYear = getBoundaryYear(result, 'start')
  const rawEndYear = getBoundaryYear(result, 'end')
  const startYear = filteredStartYear ?? rawStartYear
  const endYear = filteredEndYear ?? rawEndYear
  const distanceTone = getDistanceTone(result, isComparable)
  const unit = resolveIndicatorUnit(item, result)
  const discretePresentation = ['binaryDeclaration', 'countOfTotal'].includes(
    presentation?.valueKind,
  )
    ? presentation
    : null
  const isIdeb = isIdebIndicator(item, result)
  const isAccExpansion = isAccumulativeExpansionIndicator(item, result)
  const ppOptions = { keepOneDecimal: isIdeb }
  const endValueForGoal = floorValueForGoal(Number(result.end_value), item, result)
  const startValueForGoal = floorValueForGoal(Number(result.start_value), item, result)
  const metaValueForGoal = floorValueForGoal(Number(result.meta), item, result)
  const flooredResult = isAccExpansion
    ? {
        ...result,
        end_value: endValueForGoal,
        start_value: startValueForGoal,
        meta: metaValueForGoal,
        distance: Number.isFinite(endValueForGoal) && Number.isFinite(metaValueForGoal)
          ? endValueForGoal - metaValueForGoal
          : result.distance,
      }
    : result
  const goalResult = isAccExpansion && Number.isFinite(flooredResult.distance)
    ? {
        ...flooredResult,
        display: {
          ...flooredResult.display,
          distance: `${flooredResult.distance > 0 ? '+' : ''}${Math.round(flooredResult.distance).toLocaleString('pt-BR', { maximumFractionDigits: 0 })} p.p.`,
        },
    }
    : flooredResult
  const summaryStartValue = getPneSummaryDisplayValue(goalResult.start_value, unit)
  const summaryEndValue = getPneSummaryDisplayValue(goalResult.end_value, unit)
  const summaryGoalResult = buildPneSummaryResult(goalResult, unit)
  const formattedStart = isApproximate
    ? formatApproximatePercent(summaryStartValue)
    : formatIndicatorValue(summaryStartValue, unit)
  const formattedEnd = presentation?.currentText
    ?? (isApproximate
      ? formatApproximatePercent(summaryEndValue)
      : formatIndicatorValue(summaryEndValue, unit))
  const variation = roundPpString(getDisplayValue(result.display, 'variation'), ppOptions)
  const compactVariation = formatCompactVariation(variation)
  const hasStartYear = typeof startYear === 'number' && startYear > 0
  const hasEndYear = typeof endYear === 'number' && endYear > 0
  const isSingleYear = isSingleYearIndicator(result)
  const validYears = [...new Set(displaySeries
    .filter((point) => Number.isFinite(Number(point?.valor)))
    .map((point) => Number(point?.ano))
    .filter(Number.isFinite))]
  const hasHistory = validYears.length >= 2
  const seriesValues = displaySeries.map((p) => Number(p?.valor)).filter(Number.isFinite)
  const hasRealSeriesValues = seriesValues.some((v) => v !== 0)
  const hasSeries = seriesValues.length >= 2 && (isApproximate || hasRealSeriesValues)
  const hasRenderableHistory = isOrganizedPneDetail ? hasHistory : hasSeries
  const usesSingleYearComposition = isOrganizedPneDetail && !hasHistory
  const availableYear = validYears[0] ?? (hasEndYear ? endYear : startYear)
  const cycleTargetYear = isClosedPneCycle(cycle)
    ? 2024
    : reconciliation.context?.legalReference?.targetYear
      ?? PNE_2026_GOAL_INDICATOR_CONTRACT.cycle.endYear

  const metaValue = presentation?.referenceText
    ?? (isApproximate
      ? formatApproximatePercent(result.reference_value)
      : formatMetaValue(goalResult, unit))
  const distanceValue = presentation?.distanceText
    ?? (unit === 'percent'
      && Number.isFinite(Number(summaryEndValue))
      && Number.isFinite(Number(goalResult.meta))
      ? formatPpDifference(Number(summaryEndValue) - Number(goalResult.meta))
      : roundPpString(getDisplayValue(goalResult.display, 'distance'), ppOptions))
  const distanceLabel = presentation?.distanceLabel
    ?? (cycle === PNE_2026_CYCLE ? 'Distância da referência' : 'Distância da meta')
  const referenceDifferenceValue = formatApproximateDifference(result.reference_difference)
  const showGoalProgress = isComparable && Number.isFinite(Number(goalResult?.meta)) && Number.isFinite(Number(goalResult?.end_value))
  const historyReferenceValue = isApproximate ? result.reference_value : goalResult.meta
  const showHistoryReference =
    ((!displayPolicy && isApproximate) || isComparable)
    && Number.isFinite(Number(historyReferenceValue))
  const sharedPnePercentDomain = buildSharedPnePercentDomain({
    allowProjection: canProject,
    cycle,
    displaySeries,
    indicatorKey: item?.key,
    municipioData,
    referenceValue: historyReferenceValue,
    unit,
  })
  const goalTexts = cycle === 'pne_2026_2036'
    ? PNE_2026_GOAL_TEXTS
    : cycle === 'pne_2014_2024'
      ? PNE_2014_GOAL_TEXTS
      : null
  const legalGoal = goalTexts && item.metaRef
    ? goalTexts[item.metaRef]
    : null
  const quickReading = currentDetailModel?.reading ?? buildQuickReading({
    atingida: goalResult.atingida,
    cycle,
    distanceValue,
    direction: goalResult.direction,
    endYear,
    formattedEnd,
    isComplementary: isComplementaryRelationship,
    isComparable,
    isApproximate: displayPolicy ? false : isApproximate,
    metaValue,
    startYear,
    targetYear: cycle === PNE_2026_CYCLE
      ? cycleTargetYear
      : PNE_2026_GOAL_INDICATOR_CONTRACT.cycle.endYear,
    variation: item?.key === 'medio_tecnico_articulado_percentual'
      ? compactVariation
      : variation,
  })
  const quickReadingInsights = isOrganizedPneDetail
    ? buildPneQuickReadingInsights({
        atingida: goalResult.atingida,
        cycle,
        distanceValue,
        endYear,
        formattedEnd,
        isComparable,
        isApproximate: displayPolicy ? false : isApproximate,
        metaValue,
        quickReading,
        showGoalComparison: displayPolicy?.showGoalComparison ?? true,
        startYear,
        targetYear: cycleTargetYear,
        variation: item?.key === 'medio_tecnico_articulado_percentual'
          ? compactVariation
          : variation,
      })
    : null
  const historySummary = buildHistoryChartSummary({
    atingida: goalResult.atingida,
    distanceValue,
    direction: goalResult.direction,
    endYear,
    formattedEnd,
    isComparable,
    isApproximate,
    metaValue,
  })

  return (
    <section
      className={`detail-panel detail-panel--${tone}${isOrganizedPneDetail ? ' detail-panel--organized' : ''}`}
      ref={ref}
    >
      <div className="detail-heading">
        <div className="detail-heading__copy">
          <span className="eyebrow">{cycleCopy.detailEyebrow}</span>
          <h2 data-detail-title tabIndex={-1}>{getIndicatorTitle(item, result)}</h2>
          {isExpansionShareBaseline ? (
            <>
              <p className="expansion-share-detail-period">Período de referência: {currentDetailModel.composition.period ?? 'indisponível'}</p>
              <p className="expansion-share-detail-note">Contexto pré-ciclo: estes dados antecedem o acompanhamento do PNE 2026–2036.</p>
            </>
          ) : null}
        </div>
      </div>

      {usesSingleYearComposition && isComplementaryRelationship ? (
        <div className="metric-grid metric-grid--two metric-grid--single-year">
          <MetricCard
            icon="current"
            label={`Valor disponível${hasReadableYear(availableYear) ? ` (${availableYear})` : ''}`}
            value={formattedEnd}
          />
          <MetricCard icon="type" label="Uso" value="Apoio à leitura da meta" tone="muted" />
        </div>
      ) : usesSingleYearComposition && isObserved ? (
        <ClosedCycleObservedMetrics
          endYear={availableYear}
          formattedEnd={formattedEnd}
          formattedStart={formattedStart}
          goalContextLabel={displayPolicy.goalContextLabel}
          hasEndYear={hasReadableYear(availableYear)}
          hasStartYear={hasStartYear}
          startYear={startYear}
          variation={compactVariation}
        />
      ) : usesSingleYearComposition ? (
        <div className={`metric-grid ${presentation?.showDistance === false ? 'metric-grid--three' : 'metric-grid--four'} metric-grid--single-year${discretePresentation ? ' metric-grid--discrete' : ''}`}>
          <MetricCard
            icon="current"
            label={`${presentation?.currentLabel ?? 'Valor disponível'}${hasReadableYear(availableYear) ? ` (${availableYear})` : ''}`}
            value={formattedEnd}
          />
          <MetricCard
            icon="target"
            label={presentation?.referenceLabel ?? result.meta_label ?? `Meta PNE ${cycleTargetYear}`}
            value={metaValue}
          />
          {presentation?.showDistance !== false ? (
            <MetricCard
              icon="distance"
              label={distanceLabel}
              value={distanceValue}
              tone={distanceTone}
            />
          ) : null}
          <MetricCard
            icon="status"
            label="Situação"
            value={presentation?.statusText || status || (result.atingida ? cycleCopy.status.achieved : cycleCopy.status.below)}
            tone={distanceTone}
          />
        </div>
      ) : currentDetailModel ? (
        <PneCurrentMetrics model={currentDetailModel} />
      ) : isSingleYear ? (
        isObserved ? (
          <ClosedCycleObservedMetrics
            endYear={endYear}
            formattedEnd={formattedEnd}
            formattedStart={formattedStart}
            goalContextLabel={displayPolicy.goalContextLabel}
            hasEndYear={hasEndYear}
            hasStartYear={hasStartYear}
            startYear={startYear}
            variation={compactVariation}
          />
        ) : isApproximate ? (
          <div className="metric-grid metric-grid--three">
            {hasStartYear && (
              <MetricCard icon="start" label={`Valor inicial (${startYear})`} value={formattedStart} />
            )}
            <MetricCard icon="target" label="Referência legal final (2036)" value={metaValue} />
            <MetricCard icon="type" label="Tipo" value="Indicador aproximado" tone="muted" />
          </div>
        ) : isComparable ? (
          <div className={`metric-grid ${presentation?.showDistance === false ? 'metric-grid--three' : 'metric-grid--four'}${discretePresentation ? ' metric-grid--discrete' : ''}`}>
            {hasStartYear && (
              <MetricCard icon="start" label={`Valor inicial (${startYear})`} value={formattedStart} />
            )}
            <MetricCard
              icon="target"
              label={presentation?.referenceLabel ?? result.meta_label ?? 'Meta'}
              value={metaValue}
            />
            {presentation?.showDistance !== false ? (
              <MetricCard
                icon="distance"
                label={distanceLabel}
                value={distanceValue}
                tone={distanceTone}
              />
            ) : null}
            <MetricCard
              icon="status"
              label="Situação"
              value={presentation?.statusText || (result.atingida ? cycleCopy.status.achieved : cycleCopy.status.below)}
              tone={distanceTone}
            />
          </div>
        ) : isComplementaryRelationship ? (
          <div className="metric-grid">
            {hasStartYear && (
              <MetricCard icon="start" label={`Valor inicial (${startYear})`} value={formattedStart} />
            )}
            {hasEndYear && (
              <MetricCard icon="current" label={cycleCopy.valueLabel(endYear)} value={formattedEnd} size="large" />
            )}
            <MetricCard
              icon={getPneMetricIcon('Variação', compactVariation, getVariationDetail(variation, startYear))}
              detail={getVariationDetail(variation, startYear)}
              label="Variação"
              value={compactVariation}
            />
          </div>
        ) : (
          <div className="metric-grid metric-grid--two">
            {hasStartYear && (
              <MetricCard icon="start" label={`Valor inicial (${startYear})`} value={formattedStart} />
            )}
            <MetricCard icon="type" label="Tipo" value="Informativo" tone="muted" />
          </div>
        )
      ) : (
        isObserved ? (
          <ClosedCycleObservedMetrics
            endYear={endYear}
            formattedEnd={formattedEnd}
            formattedStart={formattedStart}
            goalContextLabel={displayPolicy.goalContextLabel}
            hasEndYear={hasEndYear}
            hasStartYear={hasStartYear}
            startYear={startYear}
            variation={compactVariation}
          />
        ) : isApproximate ? (
          <div className="metric-grid">
            {hasStartYear && (
              <MetricCard icon="start" label={`Valor inicial (${startYear})`} value={formattedStart} />
            )}
            {hasEndYear && (
              <MetricCard icon="current" label={cycleCopy.valueLabel(endYear)} value={formattedEnd} size="large" />
            )}
            <MetricCard
              icon={getPneMetricIcon('Variação', compactVariation, getVariationDetail(variation, startYear))}
              detail={getVariationDetail(variation, startYear)}
              label="Variação"
              value={compactVariation}
            />
            <MetricCard icon="target" label="Referência legal final (2036)" value={metaValue} />
            {Number.isFinite(Number(result.reference_difference)) ? (
              <MetricCard
                icon="distance"
                label="Diferença para a referência de 2036"
                value={referenceDifferenceValue}
              />
            ) : null}
          </div>
        ) : isComparable ? (
          <div className="metric-grid">
            {hasStartYear && (
              <MetricCard icon="start" label={`Valor inicial (${startYear})`} value={formattedStart} />
            )}
            {hasEndYear && (
              <MetricCard icon="current" label={cycleCopy.valueLabel(endYear)} value={formattedEnd} size="large" />
            )}
            <MetricCard
              icon={getPneMetricIcon('Variação', compactVariation, getVariationDetail(variation, startYear))}
              detail={getVariationDetail(variation, startYear)}
              label="Variação"
              value={compactVariation}
            />
            <MetricCard icon="target" label={result.meta_label ?? 'Meta'} value={metaValue} />
            <MetricCard
              icon="distance"
              label={cycle === PNE_2026_CYCLE ? 'Distância da referência' : 'Distância da meta'}
              value={distanceValue}
              tone={distanceTone}
            />
          </div>
        ) : (
          <div className="metric-grid metric-grid--four">
            {hasStartYear && (
              <MetricCard icon="start" label={`Valor inicial (${startYear})`} value={formattedStart} />
            )}
            {hasEndYear && (
              <MetricCard icon="current" label={cycleCopy.valueLabel(endYear)} value={formattedEnd} size="large" />
            )}
            <MetricCard
              icon={getPneMetricIcon('Variação', compactVariation, getVariationDetail(variation, startYear))}
              detail={getVariationDetail(variation, startYear)}
              label="Variação"
              value={compactVariation}
            />
            <MetricCard icon="type" label="Tipo" value="Informativo" tone="muted" />
          </div>
        )
      )}

      {isAbsoluteExpansionTarget && currentDetailModel?.composition ? (
        <SubsequentExpansionTracking model={currentDetailModel} />
      ) : currentDetailModel?.composition ? (
        null
      ) : showGoalProgress && discretePresentation ? (
        <DiscreteGoalProgress
          label={presentation?.mode === 'tracking'
            ? 'Acompanhamento do indicador'
            : cycleCopy.progressLabel}
          presentation={discretePresentation}
          status={presentation?.statusText || status || (result.atingida ? cycleCopy.status.achieved : cycleCopy.status.below)}
          tone={distanceTone}
        />
      ) : !currentDetailModel && showGoalProgress ? (
        <div className="indicator-goal-tracking">
          <GoalProgress
            label={presentation?.mode === 'tracking'
              ? 'Acompanhamento do indicador'
              : cycleCopy.progressLabel}
            presentation={presentation}
            result={summaryGoalResult}
            unit={unit}
          />
        </div>
      ) : currentDetailModel && showGoalProgress ? (
        <div className="indicator-goal-tracking">
          <GoalProgress
            label={presentation?.mode === 'tracking'
              ? 'Acompanhamento do indicador'
              : cycleCopy.progressLabel}
            presentation={presentation}
            result={summaryGoalResult}
            unit={unit}
          />
        </div>
      ) : currentDetailModel ? (
        <PneCurrentTracking model={currentDetailModel} />
      ) : null}

      <div className={`indicator-primary-analysis${usesSingleYearComposition ? ' indicator-primary-analysis--single-year' : ''}${isExpansionShareBaseline ? ' indicator-primary-analysis--expansion-share' : ''}${isAbsoluteExpansionTarget ? ' indicator-primary-analysis--absolute-expansion' : ''}`}>
        {usesSingleYearComposition ? (
          <PneSingleYearDataCard
            availableYear={availableYear}
            cycle={cycle}
            details={details}
            indicatorKey={item?.key}
            item={item}
            presentation={presentation}
            result={result}
            unit={unit}
          />
        ) : isExpansionShareBaseline && currentDetailModel?.composition ? (
          <ExpansionShareBaselineAnalysis model={currentDetailModel} />
        ) : isAbsoluteExpansionTarget && currentDetailModel?.composition ? (
          <SubsequentExpansionTargetAnalysis model={currentDetailModel} />
        ) : currentDetailModel ? (
          <PneRecentIndicatorChart
            cycle={cycle}
            details={details}
            domainOverride={sharedPnePercentDomain}
            item={item}
            model={currentDetailModel}
            result={result}
          />
        ) : null}

        {!usesSingleYearComposition && !currentDetailModel && hasRenderableHistory && (
          <div className="indicator-chart-card">
            <IndicatorHistoryChart
              chartHeight={320}
              chartWidth={700}
              domainOverride={sharedPnePercentDomain}
              endYear={endYear}
              essentialLabels
              item={item}
              meta={showHistoryReference ? historyReferenceValue : null}
              referenceLabel={isApproximate
                ? 'Referência 2036'
                : isClosedPneCycle(cycle)
                  ? 'Referência final'
                  : 'Meta'}
              result={isAccExpansion ? flooredResult : result}
              series={displaySeries}
              showMetaLine={showHistoryReference}
              startYear={startYear}
              subtitle={isApproximate
                ? 'Série histórica do ciclo vigente, com referência legal final para 2036.'
                : isClosedPneCycle(cycle)
                  ? 'Série histórica consolidada do ciclo encerrado, com meta de referência quando aplicável.'
                  : 'Série histórica do ciclo vigente, com meta de referência quando aplicável.'}
                title={isOrganizedPneDetail ? 'Evolução do indicador' : historySummary}
              unit={unit}
              floorNegativeValues={isAccExpansion}
              pneLayout={isOrganizedPneDetail}
            />
            <PneSourceNotes
              compact
              includeMethodology={false}
              context={{
                block: 'pne',
                cycle,
                details,
                indicatorKey: item?.key,
                item,
                presentation,
                result,
              }}
            />
          </div>
        )}

        {!usesSingleYearComposition && !currentDetailModel && !hasRenderableHistory && !isInformative && (
          <div className="indicator-chart-card indicator-chart-card--empty">
            <ChartEmptyState message="Histórico não disponível." />
            <PneSourceNotes
              includeMethodology={false}
              context={{
                block: 'pne',
                cycle,
                details,
                indicatorKey: item?.key,
                item,
                presentation,
                result,
              }}
            />
          </div>
        )}

        {!usesSingleYearComposition && !currentDetailModel && isInformative && !hasRenderableHistory && (
          <div className="detail-empty-state indicator-chart-card--empty">
            <p>Este indicador é informativo e não possui acompanhamento de meta neste ciclo.</p>
          </div>
        )}

        {usesSingleYearComposition ? (
          <PneQuickReading
            goalContextLabel={displayPolicy?.goalContextLabel}
            insights={isObserved
              ? quickReadingInsights
              : isComplementaryRelationship
              ? buildComplementarySingleYearInsights({ availableYear, formattedEnd })
              : buildSingleYearQuickReadingInsights({
                availableYear,
                cycle,
                distanceValue,
                metaValue,
                presentation,
                status,
              })}
            isSingleYear={false}
            legalGoal={legalGoal}
            metaRef={item.metaRef}
            presentation={presentation}
            quickReading=""
            tone={tone}
          />
        ) : isExpansionShareBaseline && currentDetailModel?.composition ? (
          <ExpansionShareQuickReading
            legalGoal={legalGoal}
            metaRef={item.metaRef}
            presentation={presentation}
            model={currentDetailModel}
          />
        ) : isAbsoluteExpansionTarget && currentDetailModel?.composition ? (
          <SubsequentExpansionQuickReading
            legalGoal={legalGoal}
            metaRef={item.metaRef}
            presentation={presentation}
            model={currentDetailModel}
          />
        ) : quickReading ? (
          <PneQuickReading
            goalContextLabel={displayPolicy?.goalContextLabel}
            insights={quickReadingInsights}
            isSingleYear={isSingleYear}
            legalGoal={legalGoal}
            metaRef={item.metaRef}
            presentation={presentation}
            quickReading={quickReading}
            tone={tone}
          />
        ) : null}
      </div>

      {usesSingleYearComposition ? null : currentDetailModel ? (
        <>
          <PneHistoricalContext
            allowProjection={canProject}
            cycle={cycle}
            domainOverride={sharedPnePercentDomain}
            indicatorKey={item?.key}
            item={item}
            key={`history-${item?.key}`}
            municipioData={municipioData}
            presentationMode={item?.presentationMode}
            result={result}
          />
        </>
      ) : (
        <IndicatorComplementaryData
          allowProjection={canProject}
          cycle={cycle}
          domainOverride={sharedPnePercentDomain}
          indicatorKey={item?.key}
          item={item}
          municipioData={municipioData}
          result={result}
        />
      )}

      {isExpansionShareBaseline ? (
        <ExpansionShareTechnicalDisclosure model={currentDetailModel} />
      ) : null}
      {cycle === 'pne_2026_2036' && item?.key === 'basico_integral' ? (
        <InequalityPilotSection loading={inequalityPilotLoading} pilot={inequalityPilot} />
      ) : null}
      <footer className="pne-detail-footer">
        <PneSourceNotes
          context={{
            block: 'pne',
            cycle,
            details,
            indicatorKey: item?.key,
            item,
            presentation,
            result,
            title: item?.label,
          }}
        />
        {isExpansionShareBaseline ? <p className="expansion-share-footer-note">Fonte e método: matrículas públicas e totais da EPT no período disponível; participação calculada pela variação pública dividida pela variação total, multiplicada por 100.</p> : null}
      </footer>
      {!isExpansionShareBaseline && currentDetailModel ? (
        <PneMethodologyDisclosure key={`methodology-${item?.key}`} model={currentDetailModel} />
      ) : null}
    </section>
  )
})

function ClosedCycleUnavailableDetail({ item, panelRef, statusLabel }) {
  return (
    <section
      className="detail-panel detail-panel--muted detail-panel--organized"
      ref={panelRef}
    >
      <div className="detail-heading">
        <div className="detail-heading__copy">
          <span className="eyebrow">Indicador selecionado · ciclo encerrado</span>
          <h2 data-detail-title tabIndex={-1}>{getIndicatorTitle(item)}</h2>
        </div>
      </div>
      <div className="detail-empty-state indicator-chart-card--empty">
        <p><strong>{statusLabel}</strong></p>
        <p>O indicador permanece disponível para consulta, sem converter a ausência de resultado em zero.</p>
      </div>
    </section>
  )
}

function ClosedCycleObservedMetrics({
  endYear,
  formattedEnd,
  formattedStart,
  goalContextLabel,
  hasEndYear,
  hasStartYear,
  startYear,
  variation,
}) {
  return (
    <div className="metric-grid metric-grid--four">
      {hasStartYear ? (
        <MetricCard icon="start" label={`Valor inicial (${startYear})`} value={formattedStart} />
      ) : null}
      <MetricCard
        icon="current"
        label={`Resultado final${hasEndYear ? ` (${endYear})` : ''}`}
        value={formattedEnd}
        size="large"
      />
      <MetricCard
        icon={getPneMetricIcon('Evolução', variation, getVariationDetail(variation, startYear))}
        detail={getVariationDetail(variation, startYear)}
        label="Evolução"
        value={hasReadableValue(variation) ? variation : '—'}
      />
      <MetricCard
        icon="type"
        label="Classificação"
        value={goalContextLabel ?? 'Resultado observado'}
        tone="muted"
      />
    </div>
  )
}

function PneCurrentTracking({ model }) {
  return (
    <section className={`indicator-goal-tracking indicator-goal-tracking--${model.tone}`} aria-label="Acompanhamento do indicador">
      <span>Acompanhamento do indicador</span>
      <strong>{model.statusLabel}</strong>
    </section>
  )
}

function DiscreteGoalProgress({ label, presentation, status, tone }) {
  const kind = presentation.valueKind === 'binaryDeclaration'
    ? 'binary'
    : 'requirements'
  const scaleDescription = kind === 'binary'
    ? 'Declaração municipal em relação à referência de acompanhamento'
    : 'Requisitos declarados em relação à referência de acompanhamento'

  return (
    <section
      className={`discrete-goal-progress discrete-goal-progress--${kind} discrete-goal-progress--${tone}`}
      aria-label={`${label}. ${presentation.currentText}. ${status}.`}
    >
      <header className="discrete-goal-progress__heading">
        <div className="discrete-goal-progress__heading-copy">
          <span>{label}</span>
          <p>{scaleDescription}</p>
        </div>
        <strong className="discrete-goal-progress__status">{status}</strong>
      </header>
      <div className="discrete-goal-progress__segments" aria-hidden="true">
        {Array.from({ length: presentation.segmentCount }, (_value, index) => (
          <span
            className={index < presentation.filledSegments ? 'is-filled' : ''}
            key={index}
          />
        ))}
      </div>
      <dl className="discrete-goal-progress__scale">
        <div>
          <dt>Início da escala</dt>
          <dd>{presentation.scaleStartLabel}</dd>
        </div>
        <div className="discrete-goal-progress__scale-current">
          <dt>{presentation.currentLabel}</dt>
          <dd>{presentation.currentText}</dd>
        </div>
        <div>
          <dt>{presentation.referenceLabel}</dt>
          <dd>{presentation.scaleEndLabel}</dd>
        </div>
      </dl>
    </section>
  )
}

function PneSingleYearDataCard({
  availableYear,
  cycle,
  details,
  indicatorKey,
  item,
  presentation,
  result,
  unit,
}) {
  const model = buildPneSingleYearDataModel({
    availableYear,
    cycle,
    details,
    indicatorKey,
    item,
    presentation,
    result,
    unit,
  })
  const availabilityReference = hasReadableYear(availableYear)
    ? `referente a ${availableYear}`
    : 'referente ao ano de referência'

  return (
    <section
      className={`indicator-data-card indicator-data-card--${model.kind}`}
      aria-labelledby="single-year-indicator-data-title"
    >
      <header className="indicator-data-card__heading">
        <h3 id="single-year-indicator-data-title">Dados do indicador</h3>
        <p>Valores disponíveis para o município no ano de referência</p>
      </header>
      <div className="indicator-data-card__notice">
        <Database aria-hidden="true" className="indicator-data-card__notice-icon" />
        <div>
          <strong>Disponibilidade do dado</strong>
          <p>
            Há somente um valor municipal disponível, {availabilityReference}. Por isso, não é possível apresentar evolução histórica ou projeção tendencial.
          </p>
        </div>
      </div>
      {model.kind === 'table' ? (
        <PnePresentationDataTable columns={model.columns} rows={model.rows} />
      ) : (
        <dl className="indicator-data-summary">
          {model.fields.map((field) => (
            <div
              className={`indicator-data-summary__item indicator-data-summary__item--${field.key}`}
              key={field.key}
            >
              <dt>{field.label}</dt>
              <dd>{field.value}</dd>
            </div>
          ))}
        </dl>
      )}
    </section>
  )
}

function PnePresentationDataTable({ columns, rows }) {
  return (
    <div className="pne-presentation-table-wrap">
      <table className="pne-presentation-table">
        <caption className="u-sr-only">Dados do indicador no ano de referência</caption>
        <thead>
          <tr>
            {columns.map((column) => <th key={column.key} scope="col">{column.label}</th>)}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rowIndex) => (
            <tr key={`${row.year ?? 'row'}-${rowIndex}`}>
              {columns.map((column) => (
                <td data-label={column.label} key={column.key}>
                  {formatPresentationTableValue(row[column.key], column.key)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function formatPresentationTableValue(value, key) {
  if (value === null || value === undefined || value === '') return '—'
  if (key === 'year') {
    const year = Number(value)
    return Number.isFinite(year)
      ? year.toLocaleString('pt-BR', { maximumFractionDigits: 0, useGrouping: false })
      : String(value)
  }
  if (typeof value === 'number') {
    return value.toLocaleString('pt-BR', { maximumFractionDigits: 1 })
  }
  return value
}

function buildSingleYearQuickReadingInsights({
  availableYear,
  cycle,
  distanceValue,
  metaValue,
  presentation,
  status,
}) {
  const year = hasReadableYear(availableYear) ? availableYear : 'de referência'
  const referenceLabel = presentation?.referenceLabel
    ?? (cycle === PNE_2026_CYCLE ? 'Referência prevista na meta' : 'Meta')
  const insights = [
    {
      detail: `Valor municipal disponível em ${year}.`,
      icon: 'current',
      key: 'current',
      label: presentation?.quickReadingLabels?.status ?? 'Situação atual',
      value: presentation?.statusText || status || 'Dado disponível',
    },
    {
      detail: presentation?.mode === 'tracking'
        ? 'Parâmetro usado para acompanhar este indicador, sem representar sozinho o cumprimento integral da meta.'
        : 'Valor previsto na meta para a comparação deste indicador.',
      icon: 'reference',
      key: 'reference',
      label: referenceLabel,
      value: metaValue,
    },
  ]

  if (presentation?.showDistance !== false) {
    insights.push({
      detail: presentation?.mode === 'tracking'
        ? 'Diferença entre o valor disponível e a referência de acompanhamento.'
        : 'Diferença entre o valor disponível e a referência prevista na meta.',
      icon: 'distance',
      key: 'distance',
      label: presentation?.distanceLabel
        ?? (cycle === PNE_2026_CYCLE ? 'Distância da referência' : 'Distância da meta'),
      value: hasReadableValue(distanceValue) ? distanceValue : '—',
    })
  }

  return insights
}

function buildComplementarySingleYearInsights({ availableYear, formattedEnd }) {
  const year = hasReadableYear(availableYear) ? availableYear : 'de referência'
  return [{
    detail: 'A medida apoia a leitura da meta, sem aferir seu cumprimento.',
    icon: 'current',
    key: 'current',
    label: 'Valor disponível',
    value: `${formattedEnd} em ${year}`,
  }]
}

function PneQuickReading({
  goalContextLabel,
  insights,
  isSingleYear,
  legalGoal,
  metaRef,
  presentation,
  quickReading,
  tone,
}) {
  const hasInsights = Array.isArray(insights) && insights.length > 0
  const isRelatedGoal = ['tracking', 'complementary'].includes(presentation?.mode)
  const goalDescription = isRelatedGoal
    ? getPneGoalFullText(legalGoal)
    : getPneGoalSummary(legalGoal)
  const hasGoalReference = Boolean(legalGoal && goalDescription)

  return (
    <aside className={`indicator-quick-reading interpretation-box interpretation-box--${tone}`} aria-label="Leitura rápida">
      <QuickReadingHeading />
      {hasGoalReference || hasInsights ? (
        <ul className="indicator-quick-reading__list">
          {hasGoalReference ? (
            <li className="indicator-quick-reading__reference">
              <PneInsightIcon name="reference" />
              <div>
                <span>{presentation?.quickReadingLabels?.goal ?? 'Meta do PNE'}</span>
                <p>
                  {goalContextLabel
                    ? <><strong>{goalContextLabel}.</strong> {goalDescription}</>
                    : presentation?.mode === 'tracking'
                    ? <>Este indicador apoia o acompanhamento da Meta {metaRef}. {goalDescription}</>
                    : <><strong>Meta {metaRef} —</strong> {goalDescription}</>}
                </p>
              </div>
            </li>
          ) : null}
          {(insights ?? []).map((insight) => (
            <li key={insight.key}>
              <PneInsightIcon name={insight.icon} />
              <div>
                <span>{insight.label}</span>
                <p><strong>{insight.value}</strong>{insight.detail ? ` — ${insight.detail}` : ''}</p>
              </div>
            </li>
          ))}
        </ul>
      ) : (
        <p>{quickReading}</p>
      )}
      {isSingleYear ? <small>Há apenas um ano disponível para este indicador.</small> : null}
    </aside>
  )
}

function PneInsightIcon({ name }) {
  const icons = {
    current: Clock3,
    distance: Ruler,
    variation: TrendingUp,
    variationDown: TrendingDown,
    reference: Flag,
  }
  const Icon = icons[name] ?? Clock3

  return <Icon aria-hidden="true" className="indicator-quick-reading__icon" />
}

function PneCurrentMetrics({ model }) {
  const compactMetrics = model.metrics.filter((metric) => metric.label !== 'Situação atual')
  const compositionMode = model.composition?.mode

  return (
    <div className={`metric-grid accumulative-cycle-metrics${compositionMode === 'expansion-share-baseline' ? ' accumulative-cycle-metrics--expansion-share' : ''}${compositionMode === 'absolute-expansion-target' ? ' accumulative-cycle-metrics--absolute-expansion' : ''}`}>
      {compactMetrics.map((metric) => (
        <MetricCard
          detail={metric.detail}
          icon={getPneMetricIcon(metric.label, metric.value, metric.detail)}
          key={metric.label}
          label={metric.label}
          size={metric.size}
          tone={metric.tone}
          value={metric.value}
        />
      ))}
    </div>
  )
}

function getPneMetricIcon(label, value, detail) {
  const normalized = String(label ?? '').toLocaleLowerCase('pt-BR')
  if (normalized.includes('inicial') || normalized.includes('ponto de partida')) return 'start'
  if (normalized.includes('acompanhamento') || normalized.includes('recente') || normalized.includes('atual')) return 'current'
  if (normalized.includes('varia')) {
    const valueText = `${value ?? ''} ${detail ?? ''}`
    return /^\s*-/.test(valueText) || /queda|redu[cç][aã]o/i.test(valueText)
      ? 'variationDown'
      : 'variation'
  }
  if (normalized.includes('expansão necessária')) return 'variation'
  if (normalized.includes('meta') || normalized.includes('refer')) return 'target'
  if (normalized.includes('dist')) return 'distance'
  return 'status'
}

function getPneGoalSummary(goal) {
  if (!goal) return ''
  const declaredSummary = goal.dashboardText || ''
  if (declaredSummary) return declaredSummary

  const text = goal.displayText || goal.originalText || ''
  if (!text) return ''
  const firstClause = text.split(/[.;:]/, 1)[0].trim()
  if (firstClause.length >= 24 && firstClause.length <= 180) {
    return `${firstClause}.`
  }
  if (text.length <= 180) return text
  return `${text.slice(0, 177).trimEnd()}…`
}

function buildPneQuickReadingInsights({
  atingida,
  cycle,
  distanceValue,
  endYear,
  formattedEnd,
  isComparable,
  isApproximate,
  metaValue,
  quickReading,
  showGoalComparison = true,
  startYear,
  targetYear,
  variation,
}) {
  const isClosedCycle = isClosedPneCycle(cycle)
  const hasCurrentValue = hasReadableYear(endYear) && hasReadableValue(formattedEnd)
  const hasVariation = hasReadableYear(startYear) && hasReadableValue(variation)
  const hasDistance = isComparable && hasReadableValue(distanceValue) && hasReadableValue(metaValue)
  const currentDetail = !hasCurrentValue
    ? 'Sem valor recente disponível.'
    : !isComparable
      ? isClosedCycle
        ? `Resultado consolidado do município em ${endYear}.`
        : `Valor municipal mais recente, em ${endYear}.`
      : atingida
        ? isClosedCycle
          ? `No resultado de ${endYear}, atingiu a meta do ciclo.`
          : `Em ${endYear}, está na referência.`
        : isClosedCycle
          ? `No resultado de ${endYear}, não atingiu a meta do ciclo.`
          : `Em ${endYear}, está abaixo da referência.`

  const insights = [
    {
      detail: currentDetail,
      icon: 'current',
      key: 'current',
      label: isClosedCycle ? 'Resultado final' : 'Situação atual',
      value: hasCurrentValue ? formattedEnd : '—',
    },
    {
      detail: hasVariation
        ? `Variação acumulada desde ${startYear}.`
        : hasReadableYear(startYear) && hasReadableYear(endYear) && startYear !== endYear
          ? `Série disponível entre ${startYear} e ${endYear}.`
          : 'Evolução não comparável no período.',
      icon: /^\s*-/.test(String(variation ?? '')) ? 'variationDown' : 'variation',
      key: 'evolution',
      label: isClosedCycle ? 'Evolução no ciclo' : 'Evolução desde o início',
      value: hasVariation ? variation : '—',
    },
  ]

  if (showGoalComparison) {
    insights.push({
      detail: hasDistance
        ? isClosedCycle
          ? atingida ? `Acima da meta de ${metaValue}.` : `Para alcançar a meta de ${metaValue}.`
          : atingida
            ? `Referência de ${metaValue} alcançada.`
            : `Para alcançar a referência de ${metaValue}.`
        : isApproximate && hasReadableValue(metaValue)
          ? `Referência legal final em ${targetYear}: ${metaValue}.`
          : hasReadableValue(quickReading) ? quickReading : 'Distância não disponível para comparação.',
      icon: 'distance',
      key: 'distance',
      label: isClosedCycle ? 'Distância da meta' : 'Distância da referência',
      value: hasDistance ? distanceValue : isApproximate && hasReadableValue(metaValue) ? metaValue : '—',
    })
  }

  return insights
}

function getPneGoalFullText(goal) {
  if (!goal) return ''
  return goal.originalText || goal.displayText || goal.dashboardText || ''
}

function PneRecentIndicatorChart({ cycle, details, domainOverride, item, model, result }) {
  if (model.loading) {
    return <ChartEmptyState message="Carregando série recente." />
  }

  const validChartPoints = model.chart.series.filter(hasFiniteSeriesValue)

  if (validChartPoints.length < 2) {
    return <ChartEmptyState message="Série recente insuficiente para exibir o gráfico." />
  }

  return (
    <div className="indicator-chart-card recent-goal-chart">
      <IndicatorHistoryChart
        chartHeight={320}
        chartWidth={700}
        domainOverride={domainOverride}
        endYear={model.chart.endYear}
        essentialLabels
        item={item}
        meta={model.chart.showMetaLine ? model.chart.meta : null}
        pneLayout
        referenceLabel={model.chart.referenceLabel}
        result={result}
        series={model.chart.series}
        showMetaLine={model.chart.showMetaLine}
        showMissingPoints={model.chart.showMissingPoints}
        startYear={model.chart.startYear}
        subtitle={model.chart.subtitle}
        title="Evolução do indicador"
        unit={model.chart.unit}
      />
      {model.chart.note ? <p className="recent-goal-chart__note">{model.chart.note}</p> : null}
      <PneSourceNotes
        compact
        includeMethodology={false}
        context={{
          block: 'pne',
          cycle,
          details,
          indicatorKey: item?.key,
          item,
          result,
        }}
      />
    </div>
  )
}

function PneMethodologyDisclosure({ model }) {
  return (
    <details className="accumulative-history-disclosure accumulative-history-disclosure--methodology">
      <summary>
        <span>Linha de base e metodologia</span>
        <small>{model.methodSummary}</small>
        <DisclosureChevron />
      </summary>
      <div className="accumulative-history-disclosure__body">
        {model.methodology.map((paragraph) => <p key={paragraph}>{paragraph}</p>)}
      </div>
    </details>
  )
}

function PneHistoricalContext({
  allowProjection,
  cycle,
  domainOverride,
  indicatorKey,
  item,
  municipioData,
  presentationMode,
  result,
}) {
  const isExpansionShareBaseline = presentationMode === 'expansion-share-baseline'
  const isAbsoluteExpansionTarget = presentationMode === 'absolute-expansion-target'
  return (
    <section className="pne-historical-context" aria-label="Dados históricos de apoio">
      <p>
        {isExpansionShareBaseline
          ? 'Dados de apoio para observar a evolução das matrículas e a composição por rede.'
          : isAbsoluteExpansionTarget
            ? 'O histórico ajuda a compreender o contexto, mas a evolução da meta será acompanhada somente a partir do valor de referência de 2025.'
          : 'Os dados históricos abaixo oferecem contexto para a leitura e não representam avanço da meta de 2036.'}
      </p>
      <IndicatorComplementaryData
        allowProjection={allowProjection}
        cycle={cycle}
        domainOverride={domainOverride}
        indicatorKey={indicatorKey}
        item={item}
        municipioData={municipioData}
        presentationMode={presentationMode}
        result={result}
      />
    </section>
  )
}

function buildSharedPnePercentDomain({
  allowProjection = true,
  cycle,
  displaySeries,
  indicatorKey,
  municipioData,
  referenceValue,
  unit,
}) {
  if (!['pne_2014_2024', 'pne_2026_2036'].includes(cycle) || unit !== 'percent') return null
  const projection = allowProjection
    ? municipioData?.[cycle]?.projecoes?.[indicatorKey]
    : null
  const values = [
    ...(displaySeries ?? []).map((point) => point?.valor),
    ...(projection?.historical_percent ?? []),
    ...(projection?.projected_percent ?? []),
    projection?.target_percent,
    referenceValue,
  ]
  return buildPnePercentScale(values).domain
}

function buildPneCurrentDetailModel({
  accumulativePresentationModel,
  cycle,
}) {
  if (cycle !== 'pne_2026_2036') return null

  return accumulativePresentationModel?.detail ?? null
}

function getPneSummaryDisplayValue(value, unit) {
  return unit === 'percent' ? toPnePercentDisplay(value).displayValue : value
}

function buildPneSummaryResult(result, unit) {
  if (unit !== 'percent') return result

  return {
    ...result,
    end_value: getPneSummaryDisplayValue(result.end_value, unit),
    start_value: getPneSummaryDisplayValue(result.start_value, unit),
    series: (result.series ?? []).map((point) => ({
      ...point,
      valor: getPneSummaryDisplayValue(point?.valor, unit),
    })),
  }
}

function hasFiniteSeriesValue(point) {
  return point?.valor !== null && point?.valor !== undefined && point?.valor !== '' && Number.isFinite(Number(point.valor))
}

function GoalProgress({ label, presentation, result, unit }) {
  const endValue = formatIndicatorValue(
    getPneSummaryDisplayValue(result.end_value, unit),
    unit,
  )
  const metaMarkerLabel = formatMetaValue(result, unit)
  const progress = calculateGoalProgress(result, unit)
  const end = Number(result.end_value)
  const meta = Number(result.meta)
  const isOverLimit = Number.isFinite(end) && Number.isFinite(meta) && end > meta && result.atingida === false
  const markersAreClose = Math.abs(progress.current - progress.meta) < 8
  const statusText = String(result?.display?.status ?? '').toLocaleLowerCase('pt-BR')
  const currentTone = result.atingida
    ? 'success'
    : statusText.includes('distante') ||
        statusText.includes('crítico') ||
        statusText.includes('critico') ||
        statusText.includes('não atingida') ||
        statusText.includes('nao atingida')
      ? 'danger'
      : result.atingida === false
        ? 'warning'
        : 'muted'
  const metaLabelOffsetPct = markersAreClose
    ? Math.min(progress.meta + 14, 95)
    : progress.meta
  const markerEdgeClass = progress.current >= 92
    ? ' goal-progress__marker--edge-end'
    : progress.current <= 8
      ? ' goal-progress__marker--edge-start'
      : ''

  return (
    <section
      className={`goal-progress${isOverLimit ? ' goal-progress--over-limit' : ''}`}
      aria-label={label}
    >
      <div className="goal-progress__heading">
        <span>{label}</span>
      </div>
      <div className="goal-progress__track">
        {isOverLimit ? (
          <>
            <span
              className={`goal-progress__fill goal-progress__fill--${currentTone}`}
              style={{ width: `${progress.meta}%` }}
            />
            <span
              className="goal-progress__overlimit"
              style={{
                left: `${progress.meta}%`,
                width: `${progress.current - progress.meta}%`,
              }}
            />
          </>
        ) : (
          <span
            className={`goal-progress__fill goal-progress__fill--${currentTone}`}
            style={{ width: `${progress.current}%` }}
          />
        )}
        <span
          className="goal-progress__target-tick"
          style={{ left: `${progress.meta}%` }}
        />
        <span
          className="goal-progress__target-label"
          style={{ left: `${metaLabelOffsetPct}%` }}
        >
          {presentation?.referenceLabel ?? 'Meta'} {metaMarkerLabel}
        </span>
        <span
          className={`goal-progress__marker goal-progress__marker--${currentTone}${markerEdgeClass}`}
          style={{ left: `${progress.current}%` }}
        >
          <em>{endValue}</em>
        </span>
      </div>
    </section>
  )
}

function formatCompactVariation(value) {
  if (!hasReadableValue(value)) return value ?? '-'
  const numeric = parseDisplayNumber(value)
  if (!Number.isFinite(numeric)) return value

  const normalized = String(value).toLocaleLowerCase('pt-BR')
  const signedValue = normalized.includes('queda')
    ? -Math.abs(numeric)
    : normalized.includes('alta') || normalized.includes('+')
      ? Math.abs(numeric)
      : numeric
  const formatted = Math.abs(signedValue).toLocaleString('pt-BR', {
    maximumFractionDigits: 1,
  })
  const sign = signedValue > 0 ? '+' : signedValue < 0 ? '-' : ''

  return `${sign}${formatted} p.p.`
}

function getVariationDetail(value, startYear) {
  const normalized = String(value ?? '').toLocaleLowerCase('pt-BR')
  const yearSuffix = hasReadableYear(startYear) ? ` desde ${startYear}` : ''

  if (normalized.includes('alta')) return `alta${yearSuffix}`
  if (normalized.includes('queda')) return `queda${yearSuffix}`
  if (parseDisplayNumber(value) === 0) return 'sem variação relevante'
  return undefined
}

export function isComparableIndicator(result) {
  if (
    !result ||
    result.available === false ||
    result.tracks_goal === false ||
    result.monitoring_mode === 'approximate_reference' ||
    result.meta == null ||
    result.distance == null ||
    typeof result.atingida !== 'boolean'
  ) {
    return false
  }

  const meta = Number(result?.meta)
  const distance = Number(result?.distance)
  const status = String(result?.display?.status ?? '').toLocaleLowerCase('pt-BR')
  return (
    Number.isFinite(distance) &&
    Number.isFinite(meta) &&
    !status.includes('visualiza') &&
    !status.includes('informativo') &&
    !status.includes('indispon') &&
    !status.includes('sem dados') &&
    !status.includes('sem variação') &&
    !status.includes('sem variacao')
  )
}

function calculateGoalProgress(result, unit) {
  const start = Number(result?.start_value)
  const current = Number(result?.end_value)
  const meta = Number(result?.meta)

  if (!Number.isFinite(current) || !Number.isFinite(meta)) {
    return { fill: 0, current: 0, meta: 0 }
  }

  const seriesValues = (result?.series ?? [])
    .map((point) => Number(point?.valor))
    .filter(Number.isFinite)
  const allValues = [...seriesValues, current, start].filter(Number.isFinite)

  const domain = getStableVisualDomain({
    values: allValues,
    meta,
    isPercent: unit === 'percent',
    isIndex: unit === 'index',
    isYears: unit === 'years',
  })

  const currentPosition = projectValueToPercent(current, domain)
  const targetPosition = projectValueToPercent(meta, domain)
  const fill = unit === 'percent' ? currentPosition : clampMarkerPosition(currentPosition)
  const metaPosition = unit === 'percent' ? targetPosition : clampMarkerPosition(targetPosition)

  return {
    current: fill,
    fill,
    meta: metaPosition,
  }
}

function getBoundaryYear(result, boundary) {
  const rawYear = boundary === 'start' ? result?.start_year : result?.end_year
  const directYear = Number(rawYear)
  if (Number.isFinite(directYear) && directYear > 0) return directYear
  const years = (result?.series ?? [])
    .map((point) => Number(point?.ano))
    .filter(Number.isFinite)
    .sort((a, b) => a - b)
  if (!years.length) return '-'
  return boundary === 'start' ? years[0] : years[years.length - 1]
}

function getDistanceTone(result, isComparable) {
  if (!isComparable) return 'muted'
  if (result?.atingida === true) return 'success'
  const status = String(result?.display?.status ?? '').toLocaleLowerCase('pt-BR')
  if (
    status.includes('distante') ||
    status.includes('crítico') ||
    status.includes('critico') ||
    status.includes('não atingida') ||
    status.includes('nao atingida')
  ) {
    return 'danger'
  }
  if (result?.atingida === false) return 'warning'
  return 'muted'
}

function buildHistoryChartSummary({
  atingida,
  distanceValue,
  direction,
  endYear,
  formattedEnd,
  isApproximate,
  isComparable,
  metaValue,
}) {
  if (!hasReadableValue(formattedEnd) || !hasReadableYear(endYear)) {
    return 'Histórico do indicador'
  }

  if (isApproximate) {
    return `${formattedEnd} em ${endYear} — indicador aproximado; referência legal final: ${metaValue} em 2036.`
  }

  if (!isComparable || !hasReadableValue(metaValue)) {
    return `${formattedEnd} em ${endYear} — indicador informativo, sem meta de referência.`
  }

  const normalizedDistance = String(distanceValue ?? '').toLocaleLowerCase('pt-BR')
  const parsedDistanceNumber = parseDisplayNumber(distanceValue)
  let distanceNumber = parsedDistanceNumber
  if (Number.isFinite(parsedDistanceNumber)) {
    if (normalizedDistance.includes('abaixo') || atingida === false) {
      distanceNumber = -Math.abs(parsedDistanceNumber)
    } else if (normalizedDistance.includes('acima') || atingida === true) {
      distanceNumber = Math.abs(parsedDistanceNumber)
    }
  }
  const distanceAbs = formatAbsPp(distanceValue)

  if (direction === 'at_most' && hasReadableValue(distanceAbs)) {
    if (atingida === true) {
      return `${formattedEnd} em ${endYear} — dentro do limite maximo de ${metaValue}.`
    }
    return `${formattedEnd} em ${endYear} — ${distanceAbs} acima do limite maximo de ${metaValue}.`
  }

  if (Number.isFinite(distanceNumber) && Math.abs(distanceNumber) < 0.05) {
    return `${formattedEnd} em ${endYear} — no nível da meta de ${metaValue}.`
  }

  if (Number.isFinite(distanceNumber) && hasReadableValue(distanceAbs)) {
    const relation = distanceNumber > 0
      ? `${distanceAbs} acima da meta de ${metaValue}`
      : `a ${distanceAbs} da meta de ${metaValue}`
    return `${formattedEnd} em ${endYear} — ${relation}.`
  }

  return `${formattedEnd} em ${endYear} — meta de referência: ${metaValue}.`
}

function buildQuickReading({
  atingida,
  cycle,
  distanceValue,
  direction,
  endYear,
  formattedEnd,
  isComplementary,
  isApproximate,
  isComparable,
  metaValue,
  startYear,
  targetYear,
  variation,
}) {
  if (!hasReadableValue(formattedEnd) || !hasReadableYear(endYear)) return ''

  const isClosedCycle = isClosedPneCycle(cycle)
  const variationAbs = formatAbsPp(variation)
  const distanceAbs = formatAbsPp(distanceValue)
  const hasVariation = hasReadableValue(variationAbs)
  const hasDistance = hasReadableValue(distanceAbs)
  const hasStartYear = hasReadableYear(startYear)
  const hasMeta = hasReadableValue(metaValue)
  const variationNumber = parseDisplayNumber(variation)
  const isStable = Number.isFinite(variationNumber) && Math.abs(variationNumber) < 0.5

  if (isComplementary) {
    return `Em ${endYear}, o município registra ${formattedEnd}. A medida apoia a leitura da meta, sem distância, situação de cumprimento ou projeção.`
  }

  if (isApproximate) {
    return `Em ${endYear}, o município registra ${formattedEnd}. A referência legal final é ${metaValue} em ${targetYear}; este proxy não representa cumprimento da meta.`
  }

  if (!isComparable || !hasMeta) {
    const periodText = isClosedCycle
      ? `No resultado consolidado de ${endYear}`
      : `Em ${endYear}`
    return `${periodText}, o município registra ${formattedEnd}. Este indicador é apresentado como informação de contexto, sem meta definida para comparação.`
  }

  if (direction === 'at_most') {
    if (atingida === true) {
      return isClosedCycle
        ? `No resultado consolidado de ${endYear}, o município registra ${formattedEnd}, dentro do limite máximo de ${metaValue}.`
        : `Em ${endYear}, o município registra ${formattedEnd}, dentro do limite máximo de ${metaValue} no momento.`
    }
    const distance = hasDistance
      ? `, ${distanceAbs} acima do limite máximo de ${metaValue}`
      : `, acima do limite máximo de ${metaValue}`
    return isClosedCycle
      ? `No resultado consolidado de ${endYear}, o município registra ${formattedEnd}${distance}.`
      : `Em ${endYear}, o município registra ${formattedEnd}${distance}; portanto, ainda não atinge a meta no momento.`
  }

  if (isStable && hasStartYear && hasVariation) {
    const periodText = isClosedCycle
      ? `No resultado consolidado de ${endYear}`
      : `Em ${endYear}`
    return `${periodText}, o município registra ${formattedEnd}. O indicador permaneceu próximo ao nível observado em ${startYear}, com variação de ${variationAbs} no período.`
  }

  if (atingida === true) {
    const evolution = hasStartYear && hasVariation && Number.isFinite(variationNumber)
      ? variationNumber >= 0
        ? ` Em relação a ${startYear}, houve aumento de ${variationAbs} no período.`
        : ` Em relação a ${startYear}, houve queda de ${variationAbs} no período.`
      : ''
    return isClosedCycle
      ? `No resultado consolidado de ${endYear}, o município registra ${formattedEnd}, atingindo a meta de ${metaValue}.${evolution}`
      : `Em ${endYear}, o município registra ${formattedEnd} e atinge a meta de ${metaValue} no momento.${evolution}`
  }

  if (atingida === false) {
    const distance = hasDistance
      ? `, ${distanceAbs} abaixo da referência de ${metaValue}`
      : `, abaixo da referência de ${metaValue}`
    const evolution = hasStartYear && hasVariation && Number.isFinite(variationNumber)
      ? variationNumber >= 0
        ? ` Em relação a ${startYear}, houve aumento de ${variationAbs} no período.`
        : ` Em relação a ${startYear}, houve queda de ${variationAbs} no período.`
      : ''
    return isClosedCycle
      ? `No resultado consolidado de ${endYear}, o município registra ${formattedEnd}${distance}; a meta não foi atingida.${evolution}`
      : `Em ${endYear}, o município registra ${formattedEnd}${distance} e ainda não atinge a meta no momento.${evolution}`
  }

  const periodText = isClosedCycle
    ? `No resultado consolidado de ${endYear}`
    : `Em ${endYear}`
  return `${periodText}, o município registra ${formattedEnd}. A referência de comparação é ${metaValue}.`
}

function hasReadableValue(value) {
  return value !== null && value !== undefined && value !== '' && value !== '-'
}

function hasReadableYear(value) {
  return typeof value === 'number' && Number.isFinite(value) && value > 0
}

function formatAbsPp(value) {
  if (!hasReadableValue(value)) return '-'
  const numeric = parseDisplayNumber(value)
  if (!Number.isFinite(numeric)) return value
  const formatted = Math.abs(numeric).toLocaleString('pt-BR', {
    maximumFractionDigits: 1,
  })
  return `${formatted} p.p.`
}

function isApproximateIndicator(item, result) {
  return (
    item?.monitoring_mode === 'approximate_reference' ||
    result?.monitoring_mode === 'approximate_reference'
  )
}

function formatApproximatePercent(value) {
  const numeric = Number(value)
  if (!Number.isFinite(numeric)) return '—'
  return `${numeric.toLocaleString('pt-BR', {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  })}%`
}

function formatApproximateDifference(value) {
  const numeric = Number(value)
  if (!Number.isFinite(numeric)) return '—'
  const sign = numeric > 0 ? '+' : ''
  return `${sign}${numeric.toLocaleString('pt-BR', {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  })} p.p.`
}

function parseDisplayNumber(value) {
  const match = String(value ?? '').match(/[-+]?\d+(?:[,.]\d+)?/)
  if (!match) return Number.NaN
  const numeric = Number(match[0].replace(',', '.'))
  return Number.isFinite(numeric) ? numeric : Number.NaN
}

function startYearFromSeries(series) {
  const years = series.map((p) => Number(p?.ano)).filter((y) => Number.isFinite(y))
  return years.length ? Math.min(...years) : null
}

function endYearFromSeries(series) {
  const years = series.map((p) => Number(p?.ano)).filter((y) => Number.isFinite(y))
  return years.length ? Math.max(...years) : null
}
