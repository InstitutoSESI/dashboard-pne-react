import {
  PNE_2026_GOAL_INDICATOR_CONTRACT,
  getPne2026RelationContext,
} from '../data/pne2026GoalIndicatorContract.js'
import { formatIndicatorValue } from './format.js'

const PNE_2026_CYCLE = 'pne_2026_2036'
const NEGATIVE_DATA_STATUSES = new Set([
  'not_applicable',
  'suppressed',
  'unavailable',
])

const PERCENT_TABLE_LABELS = Object.freeze({
  educacao_indigena_cobertura_estimada_4_17: Object.freeze({
    denominator: 'População indígena de 4 a 17 anos',
    numerator: 'Matrículas indígenas',
  }),
  aee_oferta_escolas_elegiveis: Object.freeze({
    denominator: 'Escolas elegíveis',
    numerator: 'Escolas elegíveis com oferta de AEE',
  }),
})

export function getPneIndicatorPresentation({
  cycle,
  item,
  relationContext,
  result,
} = {}) {
  if (!result) return null

  const context = relationContext
    ?? (cycle === PNE_2026_CYCLE
      ? getPne2026RelationContext(item?.metaRef, item?.key, result?.end_year)
      : null)
  const indicator = context?.indicator
    ?? PNE_2026_GOAL_INDICATOR_CONTRACT.indicators?.[item?.key]
    ?? null
  const relation = context?.relation ?? null
  const formula = indicator?.formulaId
    ? PNE_2026_GOAL_INDICATOR_CONTRACT.formulas?.[indicator.formulaId]
    : null
  const mode = relation?.mode
    ?? result?.monitoringMode
    ?? result?.monitoring_mode
    ?? 'progress'
  const current = toFiniteNumber(result?.end_value)
  const reference = toFiniteNumber(result?.meta)
  const valueKind = resolveValueKind(indicator?.unit, reference)
  const currentDisplay = valueKind === 'percent'
    ? toPnePercentDisplay(current)
    : { displayValue: current, displayWasCapped: false, rawValue: current }
  const isTracking = mode === 'tracking'
  const isComplementary = mode === 'complementary'
  const referenceLabel = isComplementary
    ? 'Sem referência municipal'
    : isTracking
    ? 'Referência de acompanhamento'
    : 'Referência prevista na meta'
  const distanceLabel = isComplementary
    ? null
    : isTracking
    ? 'Distância da referência de acompanhamento'
    : 'Distância da referência'
  const comparisonDirection = relation?.comparisonDirection
    ?? context?.comparisonReference?.milestone?.direction
    ?? context?.comparisonReference?.milestonesAtYear?.[0]?.direction
  const isAtReference = current !== null && reference !== null
    ? comparisonDirection === 'at_most'
      ? current <= reference
      : current >= reference
    : null
  const canonicalDistance = toFiniteNumber(result?.distance)
    ?? parseLocalizedNumber(result?.display?.distance)
  const achieved = isAtReference !== null
    ? isAtReference
    : canonicalDistance !== null
      ? canonicalDistance >= 0
      : typeof result?.atingida === 'boolean'
        ? result.atingida
        : null
  const statusPresentation = getPneComparisonStatusPresentation({
    achieved,
    dataStatus: result?.dataStatus,
    direction: comparisonDirection ?? result?.direction,
    mode,
  })
  const base = {
    currentLabel: 'Valor disponível',
    distanceLabel,
    formula,
    goalId: relation?.goalId ?? item?.metaRef ?? null,
    mode,
    cardDistanceLabel: isComplementary ? null : 'Distância',
    cardReferenceLabel: isComplementary
      ? null
      : isTracking
        ? 'Referência de acompanhamento'
        : 'Referência da meta',
    quickReadingLabels: {
      distance: distanceLabel,
      goal: isTracking || isComplementary ? 'Meta relacionada' : 'Meta do PNE',
      reference: referenceLabel,
      status: 'Situação atual',
    },
    referenceLabel,
    listValueLabel: 'Município',
    sourceIds: indicator?.sourceIds ?? [],
    statusState: statusPresentation.state,
    statusText: statusPresentation.text,
    statusTone: statusPresentation.tone,
    tableSchema: buildTableSchema(item?.key, valueKind),
    valueKind,
    displayWasCapped: currentDisplay.displayWasCapped,
  }

  if (valueKind === 'binaryDeclaration') {
    const declared = current !== null && current >= 1
    const discreteStatus = getPneComparisonStatusPresentation({
      achieved: declared,
      dataStatus: result?.dataStatus,
      direction: comparisonDirection ?? result?.direction,
      mode,
    })
    return {
      ...base,
      currentText: declared ? 'Declarado' : 'Não declarado',
      distanceText: null,
      filledSegments: declared ? 1 : 0,
      observation: 'A medida registra a declaração municipal de existência do fórum.',
      referenceText: 'Declarado',
      scaleEndLabel: 'Declarado',
      scaleKind: 'binary',
      scaleStartLabel: 'Não declarado',
      segmentCount: 1,
      showDistance: false,
      statusState: discreteStatus.state,
      statusText: discreteStatus.text,
      statusTone: discreteStatus.tone,
    }
  }

  if (valueKind === 'countOfTotal') {
    const roundedCurrent = Math.max(0, Math.round(current ?? 0))
    const roundedReference = Math.max(0, Math.round(reference ?? 0))
    const distance = roundedCurrent - roundedReference
    const discreteStatus = getPneComparisonStatusPresentation({
      achieved: roundedCurrent >= roundedReference,
      dataStatus: result?.dataStatus,
      direction: comparisonDirection ?? result?.direction,
      mode,
    })
    return {
      ...base,
      currentText: `${roundedCurrent} de ${roundedReference} ${pluralizeRequirement(roundedReference)}`,
      distanceText: formatRequirementDistance(distance),
      filledSegments: Math.min(roundedCurrent, roundedReference),
      observation: 'Contagem dos tipos de plano de carreira declarados pela administração municipal.',
      referenceText: `${roundedReference} ${pluralizeRequirement(roundedReference)}`,
      scaleEndLabel: `${roundedReference} ${pluralizeRequirement(roundedReference)}`,
      scaleKind: 'segmented',
      scaleStartLabel: '0 requisitos',
      segmentCount: Math.max(1, Math.min(roundedReference, 8)),
      showDistance: true,
      statusState: discreteStatus.state,
      statusText: discreteStatus.text,
      statusTone: discreteStatus.tone,
    }
  }

  return {
    ...base,
    currentText: formatIndicatorValue(currentDisplay.displayValue, indicator?.unit),
    distanceText: isComplementary
      ? null
      : valueKind === 'percent'
        && currentDisplay.displayValue != null
        && reference != null
      ? formatNumericDistance(
          currentDisplay.displayValue - reference,
          indicator?.unit,
        )
      : result?.display?.distance
        ?? formatNumericDistance(result?.distance, indicator?.unit),
    observation: 'Há somente uma observação municipal disponível para este indicador.',
    referenceText: isComplementary
      ? null
      : formatIndicatorValue(reference, indicator?.unit),
    scaleKind: isComplementary
      ? 'none'
      : valueKind === 'percent' ? 'continuous' : 'none',
    showDistance: !isComplementary,
  }
}

export function toPnePercentDisplay(rawValue) {
  const numeric = toFiniteNumber(rawValue)
  if (numeric === null) {
    return { displayValue: null, displayWasCapped: false, rawValue: null }
  }

  return {
    displayValue: Math.min(100, numeric),
    displayWasCapped: numeric > 100,
    rawValue: numeric,
  }
}

export function getPneComparisonStatusPresentation({
  achieved,
  dataStatus,
  direction,
  mode,
} = {}) {
  if (NEGATIVE_DATA_STATUSES.has(dataStatus) || achieved === null || achieved === undefined) {
    return Object.freeze({
      state: 'missing',
      text: null,
      tone: 'muted',
    })
  }

  const isTracking = mode === 'tracking'
  const isAtMost = direction === 'at_most'
  if (achieved) {
    return Object.freeze({
      state: 'success',
      text: isAtMost
        ? isTracking
          ? 'Dentro do limite de acompanhamento'
          : 'Dentro do limite previsto na meta'
        : isTracking
          ? 'Referência de acompanhamento alcançada'
          : 'Referência prevista na meta alcançada',
      tone: 'success',
    })
  }

  return Object.freeze({
    state: isTracking ? 'warning' : 'danger',
    text: isAtMost
      ? isTracking
        ? 'Acima do limite de acompanhamento'
        : 'Acima do limite previsto na meta'
      : isTracking
        ? 'Abaixo da referência de acompanhamento'
        : 'Abaixo da referência prevista na meta',
    tone: isTracking ? 'warning' : 'danger',
  })
}

export function getPneDiscreteIndicatorPresentation(indicatorKey, result, options = {}) {
  const presentation = getPneIndicatorPresentation({
    cycle: options.cycle ?? PNE_2026_CYCLE,
    item: options.item ?? { key: indicatorKey, metaRef: options.goalId },
    relationContext: options.relationContext,
    result,
  })

  if (!['binaryDeclaration', 'countOfTotal'].includes(presentation?.valueKind)) {
    return null
  }

  return {
    currentDisplay: presentation.currentText,
    currentLabel: presentation.currentLabel,
    dataUnitLabel: presentation.valueKind === 'binaryDeclaration'
      ? 'Declaração municipal'
      : 'Requisitos declarados',
    distanceDisplay: presentation.distanceText,
    distanceLabel: presentation.distanceLabel,
    filledSegments: presentation.filledSegments,
    kind: presentation.valueKind === 'binaryDeclaration' ? 'binary' : 'requirements',
    observation: presentation.observation,
    referenceDisplay: presentation.referenceText,
    referenceLabel: presentation.referenceLabel,
    scaleEndLabel: presentation.scaleEndLabel,
    scaleStartLabel: presentation.scaleStartLabel,
    segmentCount: presentation.segmentCount,
    showDistance: presentation.showDistance,
  }
}

export function buildPneSingleYearDataModel({
  availableYear,
  cycle,
  details,
  indicatorKey,
  item,
  presentation: suppliedPresentation,
  result,
  unit,
}) {
  const presentation = suppliedPresentation ?? getPneIndicatorPresentation({
    cycle,
    item: item ?? { key: indicatorKey },
    result,
  })
  const sourceRows =
    details?.series_components_by_cycle?.[cycle] ?? details?.series_components
  const detailRows = (Array.isArray(sourceRows) ? sourceRows : [])
    .map(normalizeDetailRow)
    .filter((row) => row.year !== null)
    .sort((left, right) => right.year - left.year)
  const preferredYear = toFiniteNumber(availableYear)
  const detailRow = detailRows.find((row) => row.year === preferredYear)
    ?? detailRows[0]
    ?? null
  const year = detailRow?.year
    ?? preferredYear
    ?? toFiniteNumber(result?.end_year)
  const numerator = detailRow?.numerator
    ?? toFiniteNumber(result?.numerator)
  const denominator = detailRow?.denominator
    ?? toFiniteNumber(result?.denominator)
  const value = detailRow?.value
    ?? toFiniteNumber(result?.end_value)

  if (presentation?.valueKind === 'binaryDeclaration') {
    return {
      columns: presentation.tableSchema,
      kind: 'table',
      rows: [{
        result: presentation.currentText,
        year,
      }],
    }
  }

  if (presentation?.valueKind === 'countOfTotal') {
    const current = toFiniteNumber(result?.end_value)
    const reference = toFiniteNumber(result?.meta)
    return {
      columns: presentation.tableSchema,
      kind: 'table',
      rows: [{
        denominator: denominator ?? reference,
        numerator: numerator ?? current,
        result: presentation.currentText,
        year,
      }],
    }
  }

  if (
    presentation?.valueKind === 'percent'
    && year !== null
    && numerator !== null
    && denominator !== null
  ) {
    return {
      columns: presentation.tableSchema,
      kind: 'table',
      rows: [{
        denominator,
        numerator,
        result: formatIndicatorValue(value, 'percent'),
        year,
      }],
    }
  }

  return {
    fields: [
      {
        key: 'year',
        label: 'Ano',
        value: year === null ? 'Não informado' : String(year),
      },
      {
        key: 'result',
        label: 'Resultado',
        value: presentation?.currentText ?? formatIndicatorValue(value, unit),
      },
    ],
    kind: 'summary',
  }
}

function buildTableSchema(indicatorKey, valueKind) {
  if (valueKind === 'binaryDeclaration') {
    return [
      { key: 'year', label: 'Ano' },
      { key: 'result', label: 'Situação declarada' },
    ]
  }

  if (valueKind === 'countOfTotal') {
    return [
      { key: 'year', label: 'Ano' },
      { key: 'numerator', label: 'Requisitos declarados' },
      { key: 'denominator', label: 'Total de requisitos' },
      { key: 'result', label: 'Situação' },
    ]
  }

  const labels = PERCENT_TABLE_LABELS[indicatorKey] ?? {
    denominator: 'Denominador',
    numerator: 'Numerador',
  }
  return [
    { key: 'year', label: 'Ano' },
    { key: 'numerator', label: labels.numerator },
    { key: 'denominator', label: labels.denominator },
    { key: 'result', label: 'Resultado' },
  ]
}

function resolveValueKind(unit, reference) {
  if (unit === 'percent') return 'percent'
  if (unit === 'count' && reference !== null && reference <= 1) {
    return 'binaryDeclaration'
  }
  if (unit === 'count' && reference !== null && reference > 1) {
    return 'countOfTotal'
  }
  return unit ?? 'count'
}

function normalizeDetailRow(row) {
  return {
    denominator: toFiniteNumber(row?.denominador),
    numerator: toFiniteNumber(row?.numerador),
    value: toFiniteNumber(row?.percentual) ?? toFiniteNumber(row?.valor),
    year: toFiniteNumber(row?.ano),
  }
}

function formatNumericDistance(value, unit) {
  const numeric = toFiniteNumber(value)
  if (numeric === null) return '—'
  if (unit === 'percent') {
    return `${numeric > 0 ? '+' : ''}${numeric.toLocaleString('pt-BR', {
      maximumFractionDigits: 1,
    })} p.p.`
  }
  return formatIndicatorValue(numeric, unit)
}

function formatRequirementDistance(distance) {
  const absolute = Math.abs(distance)
  const sign = distance > 0 ? '+' : distance < 0 ? '-' : ''
  return `${sign}${absolute} ${pluralizeRequirement(absolute)}`
}

function pluralizeRequirement(value) {
  return Math.abs(Number(value)) === 1 ? 'requisito' : 'requisitos'
}

function toFiniteNumber(value) {
  if (value === null || value === undefined || value === '') return null
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric : null
}

function parseLocalizedNumber(value) {
  const match = String(value ?? '').match(/[+-]?\d+(?:[.,]\d+)?/)
  if (!match) return null
  const numeric = Number(match[0].replace(',', '.'))
  return Number.isFinite(numeric) ? numeric : null
}
