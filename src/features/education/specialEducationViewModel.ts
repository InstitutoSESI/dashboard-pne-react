import { createIndicator } from './educationViewModels.js'
import {
  SPECIAL_EDUCATION_CUTS,
  type SpecialEducationCut,
  type SpecialEducationIndicatorId,
  type SpecialEducationMunicipalDocument,
  type SpecialEducationPoint,
  type SpecialEducationYearCut,
} from './specialEducationTypes.js'

const SPECIAL_EDUCATION_CUT_LABELS = {
  total: 'Total municipal',
  publica: 'Rede pública',
  municipal: 'Rede municipal',
  estadual: 'Rede estadual',
  federal: 'Rede federal',
  privada: 'Rede privada',
  urbana: 'Localização urbana',
  rural: 'Localização rural',
} satisfies Record<SpecialEducationCut, string>

export const SPECIAL_EDUCATION_REFERENCE_YEAR = 2025

export const SPECIAL_EDUCATION_CUT_OPTIONS = SPECIAL_EDUCATION_CUTS.map((key) => ({
  key,
  label: SPECIAL_EDUCATION_CUT_LABELS[key],
}))

export function specialEducationCutLabel(cut: SpecialEducationCut) {
  return SPECIAL_EDUCATION_CUT_LABELS[cut]
}

export const SPECIAL_EDUCATION_DEFINITIONS = {
  'educacao-especial-matriculas': {
    label: 'Matrículas da Educação Especial',
    description: 'Matrículas da Educação Especial em classes comuns e classes exclusivas.',
    formatType: 'number',
    unit: 'matrículas',
  },
  'educacao-especial-inclusao-classes-comuns': {
    label: 'Inclusão em classes comuns',
    description: 'Percentual das matrículas da Educação Especial em classes comuns.',
    formatType: 'percent',
    unit: 'percentual',
  },
  aee: {
    label: 'Escolas que oferecem AEE',
    description: 'Número de escolas que oferecem Atendimento Educacional Especializado.',
    formatType: 'number',
    unit: 'escolas',
  },
  'educacao-bilingue-surdos': {
    label: 'Educação Bilíngue de Surdos',
    description: 'Matrículas da educação básica bilíngue de surdos registradas no município.',
    formatType: 'number',
    unit: 'matrículas',
  },
} as const

export function isResolvedSpecialEducationPoint(point: SpecialEducationPoint | undefined): boolean {
  return Boolean(point && (point.state === 'observed' || point.state === 'derived_zero') && point.value != null)
}

export function isPublishableSpecialEducationPoint(point: SpecialEducationPoint | undefined): boolean {
  return Boolean(point && point.value != null && (
    point.state === 'observed'
    || point.state === 'derived_zero'
    || point.state === 'partial'
  ))
}

export function publicSpecialEducationState(point: SpecialEducationPoint | undefined): string {
  if (!point) return 'Sem informação'
  if (point.state === 'observed') return 'Dado observado'
  if (point.state === 'derived_zero') return 'Zero confirmado'
  if (point.state === 'partial') return 'Dado parcial'
  if (point.state === 'not_applicable') return 'Não se aplica'
  return 'Dado indisponível'
}

export function formatSpecialEducationValue(point: SpecialEducationPoint | undefined, percent = false): string {
  if (!isPublishableSpecialEducationPoint(point)) return '—'
  return percent
    ? `${Number(point?.value).toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%`
    : Number(point?.value).toLocaleString('pt-BR', { maximumFractionDigits: 0 })
}

export function pointForIndicator(cut: SpecialEducationYearCut, id: SpecialEducationIndicatorId) {
  if (id === 'educacao-especial-matriculas') return cut.specialEducation.enrollments
  if (id === 'educacao-especial-inclusao-classes-comuns') return cut.commonClassInclusionRate
  if (id === 'aee') return cut.aee.schoolsOfferingAee
  return cut.bilingualDeafEducation.enrollments
}

export function buildIndicatorSeries(
  document: SpecialEducationMunicipalDocument,
  id: SpecialEducationIndicatorId,
  cut: SpecialEducationCut,
) {
  return document.years
    .map(({ year, cuts }) => {
      const point = pointForIndicator(cuts[cut], id)
      return { ano: year, valor: isPublishableSpecialEducationPoint(point) ? point.value : null, state: point.state }
    })
    .sort((left, right) => left.ano - right.ano)
}

export function buildSpecialEducationViewModel(document: SpecialEducationMunicipalDocument) {
  const reference = document.years.find(({ year }) => year === SPECIAL_EDUCATION_REFERENCE_YEAR)
  const allItems = (Object.keys(SPECIAL_EDUCATION_DEFINITIONS) as SpecialEducationIndicatorId[]).map((id) => {
    const definition = SPECIAL_EDUCATION_DEFINITIONS[id]
    const currentPoint = reference ? pointForIndicator(reference.cuts.total, id) : undefined
    const snapshotOnly = id === 'educacao-bilingue-surdos'
    const series = buildIndicatorSeries(document, id, 'total')
    const currentValue = isPublishableSpecialEducationPoint(currentPoint) ? currentPoint?.value : null
    const availableInReferenceYear = isPublishableSpecialEducationPoint(currentPoint)
    const indicator = createIndicator({
      key: id,
      label: definition.label,
      description: definition.description,
      section: 'modalidades',
      sections: ['modalidades'],
      groupKey: 'inclusao',
      themeKey: 'inclusao',
      themeLabel: 'Inclusão',
      mainCutLabel: 'Total municipal',
      source: 'Censo Escolar da Educação Básica — INEP',
      formatType: definition.formatType,
      unit: definition.unit,
      currentValue,
      currentYear: SPECIAL_EDUCATION_REFERENCE_YEAR,
      series,
      cardReading: snapshotOnly && availableInReferenceYear
        ? `Retrato disponível em ${SPECIAL_EDUCATION_REFERENCE_YEAR}`
        : undefined,
      snapshotOnly,
      statusLabel: currentPoint?.state === 'partial'
        ? 'Dado parcial'
        : snapshotOnly && availableInReferenceYear
        ? `Retrato ${SPECIAL_EDUCATION_REFERENCE_YEAR}`
        : availableInReferenceYear
          ? undefined
          : `Indisponível em ${SPECIAL_EDUCATION_REFERENCE_YEAR}`,
      statusTone: snapshotOnly ? 'muted' : undefined,
      specialEducationIndicator: true,
    })
    return {
      ...indicator,
      availableInReferenceYear,
      currentDisplay: formatSpecialEducationValue(currentPoint, definition.formatType === 'percent'),
      currentValue,
      currentYear: SPECIAL_EDUCATION_REFERENCE_YEAR,
      referencePointState: currentPoint?.state ?? 'unavailable',
      // createIndicator normaliza séries genéricas removendo valores nulos. Neste
      // contrato, os nulos são lacunas semânticas e precisam permanecer no eixo.
      series,
      variationDisplay: snapshotOnly || !availableInReferenceYear ? '—' : indicator.variationDisplay,
      variationRaw: snapshotOnly || !availableInReferenceYear ? null : indicator.variationRaw,
      variationTone: snapshotOnly || !availableInReferenceYear ? 'muted' : indicator.variationTone,
    }
  })
  return {
    allItems,
    items: allItems.filter((item) => item.availableInReferenceYear),
    latestYear: SPECIAL_EDUCATION_REFERENCE_YEAR,
  }
}
