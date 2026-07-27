import { isHigherEducationUsablePoint } from '../../data/higherEducationValidation.js'
import {
  HIGHER_EDUCATION_BREAKDOWN_CATALOG,
  HIGHER_EDUCATION_GROUPS,
  HIGHER_EDUCATION_INDICATOR_CATALOG,
} from './higherEducationCatalog.js'
import type {
  HigherEducationAnnualPoint,
  HigherEducationAvailability,
  HigherEducationBreakdown,
  HigherEducationBreakdownViewModel,
  HigherEducationIndicatorViewModel,
  HigherEducationManifest,
  HigherEducationMunicipalDocument,
  HigherEducationViewModel,
} from './higherEducationTypes.js'

function sourceIds(point: HigherEducationAnnualPoint | null) {
  if (!point) return []
  return Array.from(new Set([
    ...(point.sourceId ? [point.sourceId] : []),
    ...(point.sourceIds ?? []),
  ]))
}

function availabilityForPoint(
  point: HigherEducationAnnualPoint | null,
  latestGlobalYear: number,
): HigherEducationAvailability {
  if (!point) return 'unavailable'
  return point.year === latestGlobalYear ? 'current' : 'historical_only'
}

function buildIndicator(
  document: HigherEducationMunicipalDocument,
  manifest: HigherEducationManifest,
  catalogItem: (typeof HIGHER_EDUCATION_INDICATOR_CATALOG)[number],
): HigherEducationIndicatorViewModel {
  const series = document.indicators[catalogItem.id]?.series ?? []
  const usefulPoints = series.filter(isHigherEducationUsablePoint)
  const firstPoint = usefulPoints[0] ?? null
  const latestPoint = usefulPoints[usefulPoints.length - 1] ?? null
  const comparable = usefulPoints.length >= 2 && firstPoint && latestPoint
  const absoluteVariation = comparable ? latestPoint.value! - firstPoint.value! : null
  const percentVariation = comparable && firstPoint.value !== 0
    ? (absoluteVariation! / firstPoint.value!) * 100
    : null
  return {
    ...catalogItem,
    series,
    usefulPoints,
    firstPoint,
    latestPoint,
    currentYear: latestPoint?.year ?? null,
    currentValue: latestPoint?.value ?? null,
    currentStatus: latestPoint?.status ?? null,
    absoluteVariation,
    percentVariation,
    effectiveSourceIds: Array.from(new Set(usefulPoints.flatMap(sourceIds))),
    availability: availabilityForPoint(latestPoint, manifest.latestYear),
  }
}

function latestUsableBreakdown(
  breakdowns: HigherEducationBreakdown[],
  id: string,
): HigherEducationBreakdown | null {
  const candidates = breakdowns
    .filter((item) => item.id === id && isHigherEducationUsablePoint({
      year: item.year,
      value: item.status === 'derived_zero' ? 0 : item.status === 'observed' ? 0 : null,
      status: item.status,
    }))
    .sort((a, b) => a.year - b.year)
  return candidates[candidates.length - 1] ?? null
}

function buildBreakdown(
  document: HigherEducationMunicipalDocument,
  catalogItem: (typeof HIGHER_EDUCATION_BREAKDOWN_CATALOG)[number],
): HigherEducationBreakdownViewModel {
  const breakdown = latestUsableBreakdown(document.breakdowns, catalogItem.id)
  const denominator = breakdown?.categories.reduce(
    (sum, category) => sum + (isHigherEducationUsablePoint({
      year: breakdown.year,
      value: category.value,
      status: category.status,
    }) ? category.value ?? 0 : 0),
    0,
  ) ?? 0
  const canShare = Boolean(catalogItem.shareAllowed && breakdown?.exhaustive && denominator > 0)
  return {
    ...catalogItem,
    year: breakdown?.year ?? null,
    status: breakdown?.status ?? null,
    exhaustive: breakdown?.exhaustive ?? false,
    sourceId: breakdown?.sourceId ?? null,
    universe: breakdown?.universe ?? null,
    territorialReference: breakdown?.territorialReference ?? null,
    categories: (breakdown?.categories ?? []).map((category) => ({
      ...category,
      share: canShare && category.value != null ? (category.value / denominator) * 100 : null,
    })),
  }
}

function buildModalityComposition(indicators: HigherEducationIndicatorViewModel[]) {
  const presential = indicators.find((item) => item.id === 'esup-matriculas-presenciais')
  const distance = indicators.find((item) => item.id === 'esup-matriculas-ead')
  const presentialByYear = new Map(
    presential?.usefulPoints.map((point) => [point.year, point]) ?? [],
  )
  const sharedYears = (distance?.usefulPoints ?? [])
    .map((point) => point.year)
    .filter((year) => presentialByYear.has(year))
    .sort((a, b) => a - b)
  const year = sharedYears[sharedYears.length - 1]
  if (year == null || !presential || !distance) return null
  if (presential.universe !== 'presential_graduation' || distance.universe !== 'distance_graduation') return null
  const presentialValue = presentialByYear.get(year)?.value
  const distanceValue = distance.usefulPoints.find((point) => point.year === year)?.value
  if (presentialValue == null || distanceValue == null) return null
  const denominator = presentialValue + distanceValue
  if (denominator <= 0) return null
  return {
    year,
    presential: presentialValue,
    distance: distanceValue,
    denominator,
    presentialShare: (presentialValue / denominator) * 100,
    distanceShare: (distanceValue / denominator) * 100,
  }
}

function buildQuickReads(
  indicators: HigherEducationIndicatorViewModel[],
  modalityComposition: HigherEducationViewModel['modalityComposition'],
  latestGlobalYear: number,
) {
  const reads: string[] = []
  const total = indicators.find((item) => item.id === 'esup-matriculas-total')
  if (total?.latestPoint) {
    reads.push(`O município registrou ${total.latestPoint.value!.toLocaleString('pt-BR')} matrículas de graduação em ${total.latestPoint.year}.`)
  }
  const ies = indicators.find((item) => item.id === 'esup-ies-sede')
  const faculty = indicators.find((item) => item.id === 'esup-docentes')
  if (ies?.latestPoint && faculty?.latestPoint && ies.latestPoint.year === faculty.latestPoint.year) {
    const institutionLabel = ies.latestPoint.value === 1 ? 'instituição com sede' : 'instituições com sede'
    reads.push(`Em ${ies.latestPoint.year}, havia ${ies.latestPoint.value!.toLocaleString('pt-BR')} ${institutionLabel} e ${faculty.latestPoint.value!.toLocaleString('pt-BR')} docentes vinculados a ${ies.latestPoint.value === 1 ? 'essa sede' : 'essas sedes'}.`)
  }
  if (modalityComposition && modalityComposition.distanceShare > 50) {
    reads.push(`Em ${modalityComposition.year}, as matrículas de graduação eram predominantemente a distância.`)
  }
  const latestYear = Math.max(...indicators.flatMap((item) => item.usefulPoints.map((point) => point.year)), 0)
  if (latestYear > 0 && latestYear < latestGlobalYear) {
    reads.push(`Os dados municipais mais recentes são de ${latestYear}, anteriores ao último ano da base.`)
  }
  return reads.slice(0, 4)
}

export function buildHigherEducationViewModel(
  manifest: HigherEducationManifest,
  document: HigherEducationMunicipalDocument,
): HigherEducationViewModel {
  const indicators = HIGHER_EDUCATION_INDICATOR_CATALOG.map((item) => buildIndicator(document, manifest, item))
  const breakdowns = HIGHER_EDUCATION_BREAKDOWN_CATALOG.map((item) => buildBreakdown(document, item))
  const allYears = indicators.flatMap((item) => item.usefulPoints.map((point) => point.year))
  const latestMunicipalUsableYear = allYears.length ? Math.max(...allYears) : null
  const effectiveSourceIds = Array.from(new Set([
    ...indicators.flatMap((item) => item.effectiveSourceIds),
    ...breakdowns.flatMap((item) => item.sourceId ? [item.sourceId] : []),
  ]))
  const modalityComposition = buildModalityComposition(indicators)
  return {
    municipality: document.municipality,
    availability: document.availability,
    globalPeriod: `${manifest.firstYear}–${manifest.latestYear}`,
    latestMunicipalUsableYear,
    groups: [...HIGHER_EDUCATION_GROUPS],
    indicators,
    breakdowns,
    quickReads: buildQuickReads(indicators, modalityComposition, manifest.latestYear),
    effectiveSources: effectiveSourceIds.flatMap((id) => manifest.sources[id] ? [{ id, ...manifest.sources[id] }] : []),
    methodNotes: [
      'Os dados apresentados cobrem somente cursos de graduação. Informações de pós-graduação ainda não estão integradas.',
      'Matrículas, ingressantes e concluintes usam o município do local de oferta; polos EaD usam o local de oferta a distância.',
      'Instituições e docentes usam o município da sede administrativa da instituição. Esses recortes não devem ser somados entre si.',
      'Zero observado ou derivado é um valor válido; ausência de informação é exibida como indisponível.',
    ],
    modalityComposition,
  }
}
