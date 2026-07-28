import { ContentState } from '../../../components/ContentState.jsx'
import {
  formatSpecialEducationValue,
  publicSpecialEducationState,
  SPECIAL_EDUCATION_REFERENCE_YEAR,
} from '../specialEducationViewModel'
import type {
  SpecialEducationMunicipalDocument,
  SpecialEducationPoint,
} from '../specialEducationTypes'
import { ReportMetrics } from './MunicipalTechnicalReportLayout'

interface SpecialEducationTechnicalReportSummaryProps {
  document: SpecialEducationMunicipalDocument | null
  error?: string | null
  loading?: boolean
}

interface SummaryMetric {
  label: string
  percent?: boolean
  point: SpecialEducationPoint
  unit: string
}

function metricDetail(point: SpecialEducationPoint, unit: string, year: number) {
  const availability = publicSpecialEducationState(point)
  return `${year} · ${unit} · ${availability}`
}

function latestReference(document: SpecialEducationMunicipalDocument) {
  return document.years.find(({ year }) => year === SPECIAL_EDUCATION_REFERENCE_YEAR)
    ?? [...document.years].sort((left, right) => right.year - left.year)[0]
}

export function getSpecialEducationTechnicalReportYear(
  document: SpecialEducationMunicipalDocument | null,
) {
  return document ? latestReference(document)?.year : undefined
}

export function SpecialEducationTechnicalReportSummary({
  document,
  error,
  loading = false,
}: SpecialEducationTechnicalReportSummaryProps) {
  if (loading) {
    return (
      <ContentState as="p" kind="loading" className="state-box state-box--loading">
        Carregando os indicadores complementares de Educação Especial…
      </ContentState>
    )
  }

  if (error) {
    return (
      <ContentState as="p" kind="unavailable" className="state-box">
        Os indicadores complementares de Educação Especial não puderam ser carregados neste momento.
      </ContentState>
    )
  }

  if (!document) {
    return (
      <ContentState as="p" kind="empty" className="state-box">
        Não há dados complementares de Educação Especial disponíveis para este município.
      </ContentState>
    )
  }

  const reference = latestReference(document)
  const total = reference?.cuts.total
  if (!reference || !total) {
    return (
      <ContentState as="p" kind="empty" className="state-box">
        Não há ano de referência utilizável para os indicadores complementares de Educação Especial.
      </ContentState>
    )
  }

  const metrics: SummaryMetric[] = [
    {
      label: 'Inclusão em classes comuns',
      percent: true,
      point: total.commonClassInclusionRate,
      unit: 'percentual das matrículas',
    },
    {
      label: 'Escolas que oferecem AEE',
      point: total.aee.schoolsOfferingAee,
      unit: 'escolas',
    },
    {
      label: 'Escolas com sala de recursos',
      point: total.aee.schoolsWithResourceRoom,
      unit: 'escolas',
    },
    {
      label: 'Matrículas na Educação Bilíngue de Surdos',
      point: total.bilingualDeafEducation.enrollments,
      unit: 'matrículas',
    },
  ]

  return (
    <ReportMetrics
      ariaLabel={`Indicadores complementares de Educação Especial em ${reference.year}`}
      description="Recorte total do município para inclusão em classes comuns, oferta de AEE e Educação Bilíngue de Surdos."
      items={metrics.map(({ label, percent, point, unit }) => ({
        detail: metricDetail(point, unit, reference.year),
        label,
        value: formatSpecialEducationValue(point, percent),
      }))}
      metadata={`Ano-base: ${reference.year}`}
      title="Inclusão, AEE e Educação Bilíngue de Surdos"
    />
  )
}
