import { useState, type MouseEvent } from 'react'
import { buildAppHash } from '../../../app/appHash'
import { ACTIVE_STATE_CONFIG } from '../../../config/stateConfig.js'
import { FINANCIAL_PAGE_KEYS } from '../../../data/financialPageKeys'
import {
  formatOverviewEnrollments,
  formatOverviewPercentage,
  formatSchoolPerformanceRate,
} from '../municipalEducationOverviewPresentation'
import type {
  BreakdownValue,
  MunicipalEducationOverviewV1,
  SnapshotValue,
  StageSnapshot,
} from '../municipalEducationOverviewTypes'
import '../../../styles/municipal-technical-report-print.css'
import type {
  Pne2026DiagnosticResultViewModel,
  Pne2026DiagnosticViewModel,
} from '../../diagnostic/diagnosticTypes'
import type { PmeReferenceDataSources } from '../pmeReferenceTableViewModel'
import {
  MissingInformation,
  ReportBlockHeader,
  ReportChapter,
  ReportMetrics,
  ReportMunicipalReading,
  ReportNote,
  ReportSection,
  ReportTableRegion,
  scrollToReportTarget,
} from './MunicipalTechnicalReportLayout'
import { PmeReferenceIndicatorsTable } from './PmeReferenceIndicatorsTable'
import type { HigherEducationViewModel } from '../higherEducationTypes'
import type { SchoolInfrastructureContract } from '../../../data/schoolInfrastructureContract'
import { SchoolInfrastructureReportTable } from './SchoolInfrastructureReportTable'
import type { SpecialEducationMunicipalDocument } from '../specialEducationTypes'
import {
  getSpecialEducationTechnicalReportYear,
  SpecialEducationTechnicalReportSummary,
} from './SpecialEducationTechnicalReportSummary'
import {
  getMunicipalReportIndicatorLabel,
  MUNICIPAL_REPORT_CHAPTERS,
  MUNICIPAL_REPORT_METHODOLOGY_NOTES,
  MUNICIPAL_REPORT_SECTIONS,
} from '../municipalTechnicalReportCatalog'

interface ReportIndicator {
  key: string
  label?: string
  currentDisplay?: string
  currentValue?: unknown
  currentYear?: unknown
  unit?: string
  source?: string
}

interface MunicipalTechnicalReportProps {
  educationItems: ReportIndicator[]
  emissionDate: string
  higherEducation: HigherEducationViewModel | null
  higherEducationError?: string | null
  higherEducationLoading?: boolean
  municipalityId: string
  municipalityName: string
  municipalityPopulation?: unknown
  municipalitySlug?: string | null
  overview: MunicipalEducationOverviewV1 | null
  pmeDiagnostic: Pne2026DiagnosticViewModel | null
  pmeDiagnosticError?: string | null
  pmeDiagnosticLoading?: boolean
  pmeReferenceData?: PmeReferenceDataSources
  schoolInfrastructure: SchoolInfrastructureContract | null
  specialEducation: SpecialEducationMunicipalDocument | null
  specialEducationError?: string | null
  specialEducationLoading?: boolean
}

type ExcelExportStatus = 'idle' | 'generating' | 'success' | 'error'

const NETWORK_ROWS = [
  ['Municipal', (stage: StageSnapshot) => stage.byNetwork.municipal],
  ['Estadual', (stage: StageSnapshot) => stage.byNetwork.state],
  ['Federal', (stage: StageSnapshot) => stage.byNetwork.federal],
  ['Privada', (stage: StageSnapshot) => stage.byNetwork.private],
] as const

function commonReferenceYear(values: unknown[]) {
  const years = values.map((value) => value == null ? null : String(value))
  if (!years.length || years.some((value) => value == null)) return undefined
  return years.every((value) => value === years[0]) ? years[0] : undefined
}

function StageOfferTable({ caption, stage }: { caption: string; stage: StageSnapshot }) {
  const values = NETWORK_ROWS.map(([, select]) => select(stage) as BreakdownValue)
  const commonYear = commonReferenceYear([
    ...values.map((value) => value.enrollments.year),
    stage.total.year,
  ])

  return (
    <ReportTableRegion metadata={commonYear ? `Ano-base: ${commonYear}` : undefined} title={caption} variant="standard">
      <table className={`municipal-technical-report__table municipal-technical-report__table--stage${commonYear ? ' municipal-technical-report__table--three-columns' : ''}`}>
        <caption className="municipal-technical-report__table-caption--semantic">{caption}</caption>
        <colgroup>
          <col className="municipal-technical-report__table-col-label" />
          <col className="municipal-technical-report__table-col-value" />
          <col className="municipal-technical-report__table-col-value" />
          {!commonYear ? <col className="municipal-technical-report__table-col-year" /> : null}
        </colgroup>
        <thead>
          <tr>
            <th scope="col">Rede</th>
            <th className="municipal-technical-report__numeric" scope="col">Matrículas</th>
            <th className="municipal-technical-report__numeric" scope="col">Participação</th>
            {!commonYear ? <th className="municipal-technical-report__numeric" scope="col">Ano</th> : null}
          </tr>
        </thead>
        <tbody>
          {NETWORK_ROWS.map(([label, select]) => {
            const value = select(stage) as BreakdownValue
            return (
              <tr key={label}>
                <th scope="row">{label}</th>
                <td className="municipal-technical-report__numeric">{formatOverviewEnrollments(value.enrollments)}</td>
                <td className="municipal-technical-report__numeric">{formatOverviewPercentage(value.share)}</td>
                {!commonYear ? <td className="municipal-technical-report__numeric">{value.enrollments.year}</td> : null}
              </tr>
            )
          })}
          <tr className="municipal-technical-report__total">
            <th scope="row">Total</th>
            <td className="municipal-technical-report__numeric">{formatOverviewEnrollments(stage.total)}</td>
            <td className="municipal-technical-report__numeric">100,0%</td>
            {!commonYear ? <td className="municipal-technical-report__numeric">{stage.total.year}</td> : null}
          </tr>
        </tbody>
      </table>
    </ReportTableRegion>
  )
}

function SnapshotSummary({ values }: { values: Array<[string, SnapshotValue]> }) {
  const commonYear = commonReferenceYear(values.map(([, value]) => value.year))

  return (
    <ReportMetrics
      metadata={commonYear ? `Ano-base: ${commonYear}` : undefined}
      items={values.map(([label, value]) => ({
        detail: commonYear ? undefined : `Ano ${value.year}`,
        label,
        value: formatOverviewEnrollments(value),
      }))}
    />
  )
}

function isAvailableSnapshot(value: SnapshotValue) {
  return (value.state === 'observed' || value.state === 'derived_zero')
    && value.value != null
}

function MunicipalSynthesis({
  educationItems,
  overview,
}: {
  educationItems: ReportIndicator[]
  overview: MunicipalEducationOverviewV1
}) {
  const candidates: Array<[string, SnapshotValue]> = [
    ['Matrículas da Educação Básica', overview.basicEducation.total],
    ['Educação Infantil', overview.earlyChildhood.total.total],
    ['Ensino Fundamental', overview.elementary.total.total],
    ['Ensino Médio', overview.highSchool.total.total],
    ['Educação de Jovens e Adultos', overview.basicEducationComposition.components.youthAndAdultEducation.total],
    ['Educação Especial', overview.specialEducation.total],
    ['Educação Profissional', overview.basicEducationComposition.components.otherProfessionalOffers.total],
  ]
  const available = candidates.filter(([, value]) => isAvailableSnapshot(value))
  const primary = available[0]
  const secondary = available.slice(1)
  const indicatorsByKey = new Map(educationItems.map((item) => [item.key, item]))
  const complementary = [
    ['Tempo integral', indicatorsByKey.get('mat-integral')],
    ['Escolas', indicatorsByKey.get('rede-total')],
  ] as const
  const availableComplementary: Array<[string, ReportIndicator]> = complementary.flatMap(
    ([label, item]) => item ? [[label, item]] : [],
  )
  const synthesisCommonYear = commonReferenceYear([
    ...available.map(([, value]) => value.year),
    ...availableComplementary.map(([, item]) => item.currentYear),
  ])
  const stages = candidates.slice(1, 4).filter(([, value]) => isAvailableSnapshot(value))
  const largestStage = [...stages].sort(
    (left, right) => (right[1].value ?? 0) - (left[1].value ?? 0),
  )[0]
  const basicEducationChange = overview.enrollmentComparison.stages.basicEducation.total.percentageChange
  const timeIntegral = indicatorsByKey.get('mat-integral')
  const internet = indicatorsByKey.get('internet')

  return (
    <section className="municipal-technical-report__synthesis" id="sintese" aria-labelledby="sintese-municipal-title">
      <header>
        <span className="eyebrow">Síntese municipal</span>
        <h2 id="sintese-municipal-title">Panorama educacional em leitura rápida</h2>
        <p>Seleção concisa de medidas municipais disponíveis, sem avaliação automática da gestão.</p>
      </header>
      <div className="municipal-technical-report__synthesis-layout">
        <div className="municipal-technical-report__synthesis-metrics">
          <ReportBlockHeader
            metadata={synthesisCommonYear ? `Ano-base: ${synthesisCommonYear}` : undefined}
            title="Indicadores principais"
          />
          {primary ? (
            <dl className="municipal-technical-report__synthesis-primary">
              <div>
                <dt>{primary[0]}</dt>
                <dd>{formatOverviewEnrollments(primary[1])}</dd>
                {!synthesisCommonYear ? <span>Ano {primary[1].year}</span> : null}
              </div>
            </dl>
          ) : null}
          <ReportMetrics
            title={null}
            items={[
              ...secondary.map(([label, value]) => ({
                detail: synthesisCommonYear ? undefined : `Ano ${value.year}`,
                label,
                value: formatOverviewEnrollments(value),
              })),
              ...availableComplementary.map(([label, item]) => ({
                detail: synthesisCommonYear || item.currentYear == null ? undefined : `Ano ${String(item.currentYear)}`,
                label,
                value: indicatorValue(item),
              })),
            ]}
          />
        </div>
        <aside className="municipal-technical-report__synthesis-reading" aria-label="Leitura municipal em destaque">
          <span className="eyebrow">Leitura municipal em destaque</span>
          <ul className="municipal-technical-report__synthesis-readings">
            <li>
              A Educação Básica registra {formatOverviewEnrollments(overview.basicEducation.total)} matrículas em {overview.basicEducation.total.year}.
            </li>
            {largestStage ? (
              <li>
                Entre as três etapas principais, {largestStage[0]} apresenta o maior número de matrículas no recorte publicado.
              </li>
            ) : null}
            {basicEducationChange.value != null ? (
              <li>
                Entre 2015 e 2025, o total da Educação Básica apresentou {basicEducationChange.value > 0 ? 'crescimento' : basicEducationChange.value < 0 ? 'redução' : 'estabilidade'} de {formatOverviewPercentage(basicEducationChange)}.
              </li>
            ) : null}
            {timeIntegral ? (
              <li>
                A participação das matrículas em tempo integral corresponde a {indicatorValue(timeIntegral)} no recorte disponível.
              </li>
            ) : null}
            {internet ? (
              <li>
                O indicador municipal de acesso à internet registra {indicatorValue(internet)} na referência publicada.
              </li>
            ) : null}
            <li>
              As medidas abaixo descrevem registros das bases oficiais e devem ser lidas com o ano e a fonte de cada seção.
            </li>
          </ul>
        </aside>
      </div>
    </section>
  )
}

function formatGenerationDate(value: string) {
  const date = new Date(value)
  return Number.isNaN(date.getTime())
    ? value
    : new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short' }).format(date)
}

function formatPopulation(value: unknown) {
  const candidate = typeof value === 'object' && value != null
    ? (value as Record<string, unknown>).value
      ?? (value as Record<string, unknown>).valor
      ?? (value as Record<string, unknown>).currentValue
    : value
  const numeric = typeof candidate === 'string'
    ? Number(candidate.replace(/\./g, '').replace(',', '.'))
    : Number(candidate)
  return Number.isFinite(numeric) ? Math.round(numeric).toLocaleString('pt-BR') : 'Não disponível'
}

function indicatorValue(item: ReportIndicator | undefined) {
  if (!item) return '—'
  if (item.currentValue == null) return '—'
  if (item.currentDisplay != null) {
    const display = String(item.currentDisplay).trim()
    if (
      !display.includes('_')
      && !/null|não calculável|dados insuficientes|indicador indisponível/i.test(display)
    ) return display
  }
  return String(item.currentValue)
}

function formatDiagnosticResult(result: Pne2026DiagnosticResultViewModel) {
  if (result.dataStatus !== 'available') {
    return result.dataStatusLabel ?? 'Não disponível para o período'
  }
  const suppliedDisplay = result.current.displayText?.trim()
  if (
    suppliedDisplay
    && !suppliedDisplay.includes('_')
    && !/null|dados insuficientes|indicador indisponível/i.test(suppliedDisplay)
  ) return suppliedDisplay

  const formatted = result.current.displayValue.toLocaleString('pt-BR', {
    maximumFractionDigits: 2,
  })
  if (result.current.unit === 'percent') return `${formatted}%`
  if (result.current.unit === 'years') return `${formatted} anos`
  return formatted
}

function diagnosticUnit(result: Pne2026DiagnosticResultViewModel) {
  if (result.current.unit === 'percent') return 'percentual'
  if (result.current.unit === 'count') return 'quantidade'
  if (result.current.unit === 'years') return 'anos'
  return 'índice'
}

function getDiagnosticReportIndicators(
  diagnostic: Pne2026DiagnosticViewModel | null,
  keys: string[],
): ReportIndicator[] {
  if (!diagnostic) return []

  const sourcesById = new Map(diagnostic.sources.map((source) => [source.id, source]))
  const resultsByKey = new Map(
    diagnostic.goals
      .flatMap((goal) => goal.results)
      .map((result) => [result.indicatorId, result]),
  )

  return keys.flatMap((key) => {
    const result = resultsByKey.get(key)
    if (!result) return []
    const source = result.sourceIds
      .map((sourceId) => sourcesById.get(sourceId))
      .filter((item) => item != null)
      .map((item) => item.organization ? `${item.organization} — ${item.publicTitle}` : item.publicTitle)
      .join('; ')

    return [{
      key,
      label: result.publicName,
      currentDisplay: formatDiagnosticResult(result),
      currentValue: result.current.value,
      currentYear: result.current.year,
      unit: diagnosticUnit(result),
      source: source || 'INEP — Censo Escolar e bases declaradas no diagnóstico',
    }]
  })
}

function mergeReportIndicators(...groups: ReportIndicator[][]) {
  const byKey = new Map<string, ReportIndicator>()
  groups.flat().forEach((item) => byKey.set(item.key, item))
  return [...byKey.values()]
}

function IndicatorTable({ caption, items }: { caption: string; items: ReportIndicator[] }) {
  if (!items.length) return <MissingInformation />
  const commonYear = commonReferenceYear(items.map((item) => item.currentYear))

  return (
    <ReportTableRegion
      metadata={commonYear ? `Ano-base: ${commonYear}` : undefined}
      title={caption}
      variant={items.length > 6 ? 'compact' : 'standard'}
    >
      <table className={`municipal-technical-report__table municipal-technical-report__table--indicators${commonYear ? ' municipal-technical-report__table--two-columns' : ''}`}>
        <caption className="municipal-technical-report__table-caption--semantic">{caption}</caption>
        <colgroup>
          <col className="municipal-technical-report__table-col-indicator" />
          <col className="municipal-technical-report__table-col-value" />
          {!commonYear ? <col className="municipal-technical-report__table-col-year" /> : null}
        </colgroup>
        <thead>
          <tr>
            <th scope="col">Indicador</th>
            <th className="municipal-technical-report__numeric" scope="col">Valor</th>
            {!commonYear ? <th className="municipal-technical-report__numeric" scope="col">Ano</th> : null}
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.key}>
              <th scope="row">{getMunicipalReportIndicatorLabel(item.key, item.label)}</th>
              <td className="municipal-technical-report__numeric">{indicatorValue(item)}</td>
              {!commonYear ? <td className="municipal-technical-report__numeric">{item.currentYear == null ? '—' : String(item.currentYear)}</td> : null}
            </tr>
          ))}
        </tbody>
      </table>
    </ReportTableRegion>
  )
}

function HigherEducationReportContent({
  error,
  loading,
  viewModel,
}: {
  error?: string | null
  loading?: boolean
  viewModel: HigherEducationViewModel | null
}) {
  if (loading) return <p>Preparando a síntese de Educação Superior...</p>
  if (error || !viewModel) return <MissingInformation />
  const usable = viewModel.indicators.filter((indicator) => indicator.latestPoint)
  const commonYear = commonReferenceYear(usable.map((indicator) => indicator.currentYear))
  const enrollment = usable.find((indicator) => /matrículas de graduação/i.test(indicator.title))
  return (
    <>
      <ReportNote>
        Os dados desta edição referem-se à graduação. Informações municipais de pós-graduação ainda não estão disponíveis nas bases utilizadas.
      </ReportNote>
      {viewModel.availability === 'unavailable' ? (
        <MissingInformation />
      ) : (
        <>
          {viewModel.availability === 'historical_only' ? (
            <p><strong>Informações históricas disponíveis.</strong> Último ano municipal utilizável: {viewModel.latestMunicipalUsableYear}.</p>
          ) : null}
          <ReportTableRegion metadata={commonYear ? `Referência: ${commonYear}` : undefined} title="Indicadores municipais de graduação" variant="standard">
            <table className={`municipal-technical-report__table municipal-technical-report__table--indicators${commonYear ? ' municipal-technical-report__table--two-columns' : ''}`}>
              <caption className="municipal-technical-report__table-caption--semantic">Indicadores municipais de graduação</caption>
              <colgroup>
                <col className="municipal-technical-report__table-col-indicator" />
                <col className="municipal-technical-report__table-col-value" />
                {!commonYear ? <col className="municipal-technical-report__table-col-year" /> : null}
              </colgroup>
              <thead><tr><th scope="col">Indicador</th><th className="municipal-technical-report__numeric" scope="col">Valor mais recente</th>{!commonYear ? <th className="municipal-technical-report__numeric" scope="col">Ano</th> : null}</tr></thead>
              <tbody>
                {usable.map((indicator) => (
                  <tr key={indicator.id}>
                    <th scope="row">{indicator.title}</th>
                    <td className="municipal-technical-report__numeric">{indicator.currentValue!.toLocaleString('pt-BR')}</td>
                    {!commonYear ? <td className="municipal-technical-report__numeric">{indicator.currentYear}</td> : null}
                  </tr>
                ))}
              </tbody>
            </table>
          </ReportTableRegion>
          {enrollment?.currentValue != null ? (
            <ReportMunicipalReading>
              <p>A graduação registra {enrollment.currentValue.toLocaleString('pt-BR')} matrículas municipais na referência mais recente disponível.</p>
            </ReportMunicipalReading>
          ) : null}
        </>
      )}
    </>
  )
}

export function MunicipalTechnicalReport({
  educationItems,
  emissionDate,
  higherEducation,
  higherEducationError,
  higherEducationLoading,
  municipalityId,
  municipalityName,
  municipalityPopulation,
  municipalitySlug,
  overview,
  pmeDiagnostic,
  pmeDiagnosticError,
  pmeDiagnosticLoading,
  pmeReferenceData,
  schoolInfrastructure,
  specialEducation,
  specialEducationError,
  specialEducationLoading,
}: MunicipalTechnicalReportProps) {
  const [excelExportState, setExcelExportState] = useState<{
    municipalityId: string
    status: ExcelExportStatus
  }>(() => ({ municipalityId, status: 'idle' }))
  const excelExportStatus = excelExportState.municipalityId === municipalityId
    ? excelExportState.status
    : 'idle'
  const setExcelExportStatus = (status: ExcelExportStatus) => {
    setExcelExportState({ municipalityId, status })
  }
  const byKey = new Map(educationItems.map((item) => [item.key, item]))
  const getItems = (...keys: string[]) => keys.flatMap((key) => byKey.has(key) ? [byKey.get(key)!] : [])
  const getDiagnosticItems = (...keys: string[]) =>
    getDiagnosticReportIndicators(pmeDiagnostic, keys)
  const earlyChildhoodAttendanceItems = getDiagnosticItems('creche', 'pre_escola')
  const hasEarlyChildhoodAttendanceAbove100 = earlyChildhoodAttendanceItems.some(
    (item) => Number.isFinite(Number(item.currentValue)) && Number(item.currentValue) > 100,
  )
  const elementaryAttendanceItems = getDiagnosticItems('basico_6_17', 'alfabetizacao')
  const highSchoolAttendanceItems = getDiagnosticItems('basico_15_17')
  const fullTimeItems = mergeReportIndicators(
    getItems('mat-integral'),
    getDiagnosticItems('basico_integral', 'escolas_integral'),
  )
  const environmentalEducationItems = getDiagnosticItems('educacao_ambiental')
  const ejaProfessionalItems = mergeReportIndicators(
    getItems('eja_integrada_educacao_profissional'),
    getDiagnosticItems('eja_atendimento_18_mais', 'eja_integrada_educacao_profissional_percentual'),
  )
  const higherEducationDiagnosticItems = getDiagnosticItems(
    'graduacao_frequencia_18_24',
    'superior_completo_25_34',
    'taxa_bruta_graduacao',
    'docentes_tempo_integral_ies',
    'docentes_tempo_integral_universidades',
    'docentes_tempo_integral_centros_universitarios',
    'docentes_tempo_integral_faculdades',
  )
  const teachingConditionsItems = mergeReportIndicators(
    getItems('alunos-turma-infantil', 'alunos-turma-fundamental', 'alunos-turma-medio'),
    getDiagnosticItems('adequacao_ai', 'adequacao_af', 'adequacao_em', 'pos_graduacao', 'temporarios'),
  )
  const democraticManagementItems = mergeReportIndicators(
    getDiagnosticItems('conselho_escolar'),
    getItems('proposta_pedagogica'),
  )
  const classroomInfrastructureItems = getDiagnosticItems('salas_climatizadas', 'salas_acessiveis')
  const sources = overview?.sources ?? []
  const methodology = overview?.methodology ?? []
  const mainPeriod = overview?.reference.year ?? 'Sem referência municipal'
  const sourcesUpdatedAt = overview?.reference.generatedAt
    ? formatGenerationDate(overview.reference.generatedAt)
    : 'Conforme a fonte'
  const specialEducationYear = getSpecialEducationTechnicalReportYear(specialEducation)
  const printReport = () => globalThis.window?.print()
  const reportDataLoading = Boolean(
    higherEducationLoading || pmeDiagnosticLoading || specialEducationLoading,
  )
  const exportExcel = async () => {
    if (excelExportStatus === 'generating' || reportDataLoading) return
    setExcelExportStatus('generating')
    try {
      const { downloadMunicipalTechnicalReportXlsx } = await import('../municipalTechnicalReportXlsx')
      await downloadMunicipalTechnicalReportXlsx({
        educationItems,
        emissionDate,
        higherEducation,
        municipalityId,
        municipalityName,
        municipalityPopulation,
        municipalitySlug,
        overview,
        pmeDiagnostic,
        pmeReferenceData,
        schoolInfrastructure,
        specialEducation,
      })
      setExcelExportStatus('success')
    } catch {
      setExcelExportStatus('error')
    }
  }
  const navigateChapter = (event: MouseEvent<HTMLButtonElement>, direction: -1 | 1) => {
    event.preventDefault()
    const chapters = MUNICIPAL_REPORT_CHAPTERS
      .map((chapter) => globalThis.document?.getElementById(chapter.id))
      .filter((chapter): chapter is HTMLElement => Boolean(chapter))
    const currentIndex = chapters.reduce(
      (activeIndex, chapter, index) => chapter.getBoundingClientRect().top <= 180 ? index : activeIndex,
      -1,
    )
    const targetIndex = direction < 0 ? currentIndex - 1 : currentIndex + 1
    const target = targetIndex < 0
      ? globalThis.document?.getElementById(currentIndex < 0 ? 'sintese' : 'sumario')
      : chapters[Math.min(targetIndex, chapters.length - 1)]
    target?.scrollIntoView({
      behavior: globalThis.window?.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth',
      block: 'start',
    })
  }
  const educationLink = (section: string) => buildAppHash('educacao', { municipio: municipalitySlug || undefined, secao: section })
  const financialLink = (page: string) => buildAppHash(page, { municipio: municipalitySlug || undefined })
  const traceabilityRows = [
    ['2–4 e 8–11', 'Matrículas por etapa, modalidade, rede e localização', 'INEP — Censo Escolar', overview?.reference.year, 'matrículas'],
    ['2–4', 'Atendimento estimado por faixa etária', 'INEP — Censo Escolar e base populacional do diagnóstico', earlyChildhoodAttendanceItems[0]?.currentYear ?? elementaryAttendanceItems[0]?.currentYear ?? highSchoolAttendanceItems[0]?.currentYear, '% estimado'],
    ['4', 'Rendimento escolar', 'INEP — Taxas de Rendimento Escolar', overview?.schoolPerformance.referenceYear, '%'],
    ['5', 'Alunos e escolas com jornada em tempo integral', 'INEP — Censo Escolar', fullTimeItems[0]?.currentYear, '%'],
    ['6', 'Escolas que promovem educação ambiental', 'INEP — Censo Escolar', environmentalEducationItems[0]?.currentYear, '% de escolas'],
    ['7', 'Educação escolar indígena e territórios rurais', 'INEP — Censo Escolar; IBGE — Censo Demográfico 2022', byKey.get('rural-cobertura-estimada-4-17')?.currentYear ?? byKey.get('indigena-matriculas')?.currentYear ?? byKey.get('mat-rural')?.currentYear, 'matrículas e % estimado'],
    ['8', 'EJA articulada à Educação Profissional', 'INEP — Censo Escolar e Sinopse Estatística', ejaProfessionalItems[0]?.currentYear, 'matrículas e %'],
    ['9', 'Educação Especial, AEE e Educação Bilíngue de Surdos', 'INEP — Censo Escolar', specialEducationYear, 'diversas'],
    ['10', 'Educação Superior — graduação', 'INEP — Sinopse Estatística da Educação Superior', higherEducation?.latestMunicipalUsableYear, 'diversas'],
    ['12', 'Docentes, organização das turmas e formação', 'INEP — Censo Escolar e indicadores educacionais', byKey.get('docentes-total')?.currentYear ?? teachingConditionsItems[0]?.currentYear, 'diversas'],
    ['13', 'Conselho escolar e proposta pedagógica', 'INEP — Censo Escolar', democraticManagementItems[0]?.currentYear, '% de escolas públicas'],
    ['14', 'Infraestrutura, conectividade e acessibilidade', 'Censo Escolar/INEP', schoolInfrastructure?.referenceYear ?? classroomInfrastructureItems[0]?.currentYear ?? byKey.get('internet')?.currentYear, '% de escolas ou salas'],
    ['16', 'Cenários de atendimento escolar', 'INEP e IBGE', null, '% e população'],
    ['17', 'Referências para o acompanhamento do PME', 'Diagnóstico público do PNE 2026–2036', null, 'diversas'],
  ] as const

  return (
    <article className="municipal-technical-report municipal-technical-report--print" id="inicio-relatorio">
      <header className="municipal-technical-report__hero">
        <div className="municipal-technical-report__hero-main">
          <div className="municipal-technical-report__hero-copy">
            <span className="eyebrow">Documento técnico municipal · Ano-base {mainPeriod}</span>
            <h1>Relatório Técnico Municipal</h1>
            <span className="municipal-technical-report__hero-subject">{municipalityName} · {ACTIVE_STATE_CONFIG.stateName}</span>
            <p>As seções exigidas para o diagnóstico educacional do município, geradas a partir das bases públicas oficiais — prontas para leitura, impressão e entrega, sem preenchimento manual.</p>
          </div>
          <div className="municipal-technical-report__hero-actions">
            <button
              aria-busy={excelExportStatus === 'generating'}
              className="platform-navigation-button municipal-technical-report__excel"
              disabled={reportDataLoading || excelExportStatus === 'generating'}
              type="button"
              onClick={exportExcel}
            >
              {excelExportStatus === 'generating' ? 'Gerando Excel…' : 'Baixar Excel'}
            </button>
            <button className="platform-navigation-button municipal-technical-report__print-preview" type="button" onClick={printReport}>
              Visualizar impressão
            </button>
            <button className="platform-navigation-button municipal-technical-report__print" type="button" onClick={printReport}>
              Imprimir relatório
            </button>
            {reportDataLoading ? (
              <p role="status" aria-live="polite">O Excel será liberado quando as bases complementares terminarem de carregar.</p>
            ) : excelExportStatus === 'success' ? (
              <p role="status" aria-live="polite">Arquivo Excel preparado para download.</p>
            ) : excelExportStatus === 'error' ? (
              <p role="alert" aria-live="assertive">Não foi possível gerar o Excel. Tente novamente.</p>
            ) : null}
          </div>
        </div>
        <dl className="municipal-technical-report__hero-identity" aria-label="Identificação do relatório">
          <div><dt>Município</dt><dd>{municipalityName}</dd></div>
          <div><dt>Código IBGE</dt><dd>{municipalityId || 'Não informado'}</dd></div>
          <div><dt>População</dt><dd>{formatPopulation(municipalityPopulation)}</dd></div>
          <div><dt>Ano-base principal</dt><dd>{mainPeriod}</dd></div>
          <div><dt>Data de geração</dt><dd>{emissionDate}</dd></div>
        </dl>
      </header>

      <nav className="municipal-technical-report__quick-navigation" aria-label="Navegação rápida do relatório">
        <div>
          <a href="#sintese" onClick={(event) => scrollToReportTarget(event, 'sintese')}>Síntese</a>
          <a href="#sumario" onClick={(event) => scrollToReportTarget(event, 'sumario')}>Sumário</a>
          <a href="#anexo-a" onClick={(event) => scrollToReportTarget(event, 'anexo-a')}>Anexos</a>
        </div>
        <div>
          <button type="button" onClick={(event) => navigateChapter(event, -1)}>Capítulo anterior</button>
          <button type="button" onClick={(event) => navigateChapter(event, 1)}>Próximo capítulo</button>
          <a href="#inicio-relatorio" onClick={(event) => scrollToReportTarget(event, 'inicio-relatorio')}>Voltar ao início</a>
          <button type="button" onClick={printReport}>Imprimir</button>
        </div>
      </nav>

      {overview ? <MunicipalSynthesis educationItems={educationItems} overview={overview} /> : null}

      <nav className="municipal-technical-report__summary" id="sumario" aria-labelledby="technical-report-summary-title">
        <ReportBlockHeader
          metadata={overview ? `Referência principal: ${mainPeriod}` : undefined}
          title={(
            <>
              <span className="eyebrow">Sumário</span>
              <h2 id="technical-report-summary-title">Capítulos e seções do relatório</h2>
            </>
          )}
        />
        <div className="municipal-technical-report__summary-grid">
          {MUNICIPAL_REPORT_CHAPTERS.map((chapter) => (
            <section className="municipal-technical-report__summary-chapter" key={chapter.id} aria-labelledby={`${chapter.id}-summary-title`}>
              <header>
                <span className="municipal-technical-report__summary-chapter-number">Capítulo {chapter.number}</span>
                <h3 id={`${chapter.id}-summary-title`}>
                  <a href={`#${chapter.id}`} onClick={(event) => scrollToReportTarget(event, chapter.id)}>{chapter.title}</a>
                </h3>
                <span className="municipal-technical-report__summary-chapter-range">
                  Seções {String(chapter.startIndex + 1).padStart(2, '0')}–{String(chapter.endIndex + 1).padStart(2, '0')}
                </span>
              </header>
              <ol start={chapter.startIndex + 1}>
                {MUNICIPAL_REPORT_SECTIONS.slice(chapter.startIndex, chapter.endIndex + 1).map((section, index) => (
                  <li key={section.id}>
                    <a href={`#${section.id}`} onClick={(event) => scrollToReportTarget(event, section.id)}>
                      <span className="municipal-technical-report__summary-item-title">{section.shortTitle}</span>
                      <span className="municipal-technical-report__summary-leader" aria-hidden="true" />
                      <span className="municipal-technical-report__summary-locator">{String(chapter.startIndex + index + 1).padStart(2, '0')}</span>
                    </a>
                  </li>
                ))}
              </ol>
            </section>
          ))}
        </div>
      </nav>

      <ReportChapter chapter={MUNICIPAL_REPORT_CHAPTERS[0]}>
        <ReportSection model="flow" number={1} section={MUNICIPAL_REPORT_SECTIONS[0]} metadata={`Identificação municipal · Referência ${mainPeriod}`}>
          <dl className="municipal-technical-report__identity">
            <div><dt>Município</dt><dd>{municipalityName}</dd></div>
            <div><dt>Código IBGE</dt><dd>{municipalityId || 'Não informado'}</dd></div>
            <div><dt>Referência educacional</dt><dd>{overview?.reference.year ?? 'Sem referência municipal'}</dd></div>
            <div><dt>Atualização das fontes</dt><dd>{sourcesUpdatedAt}</dd></div>
          </dl>
        </ReportSection>

        <ReportSection compact={!overview && !earlyChildhoodAttendanceItems.length && !getItems('alunos-turma-infantil').length} coverage="partial" model="metrics-table-stack" number={2} section={MUNICIPAL_REPORT_SECTIONS[1]} metadata={`INEP — Censo Escolar, base populacional e Média de Alunos por Turma · ${mainPeriod}`}>
          {overview ? <><SnapshotSummary values={[['Educação Infantil', overview.earlyChildhood.total.total], ['Creche', overview.earlyChildhood.creche.total], ['Pré-escola', overview.earlyChildhood.preSchool.total]]} /><StageOfferTable caption="Matrículas da Educação Infantil por rede" stage={overview.earlyChildhood.total} /><ReportMunicipalReading><p>A rede municipal responde por {formatOverviewEnrollments(overview.earlyChildhood.total.byNetwork.municipal.enrollments)} das {formatOverviewEnrollments(overview.earlyChildhood.total.total)} matrículas da Educação Infantil, equivalente a {formatOverviewPercentage(overview.earlyChildhood.total.byNetwork.municipal.share)}.</p></ReportMunicipalReading></> : null}
          <IndicatorTable caption="Atendimento estimado e organização das turmas" items={mergeReportIndicators(earlyChildhoodAttendanceItems, getItems('alunos-turma-infantil'))} />
          <ReportNote>
            Os percentuais estimados combinam matrículas segundo a localização da escola e população residente. Não são taxas líquidas de atendimento. {hasEarlyChildhoodAttendanceAbove100 ? 'Há resultado acima de 100% neste município, preservado em seu valor bruto. ' : ''}A média de alunos por turma não revela a distribuição entre escolas, redes ou localizações.
          </ReportNote>
        </ReportSection>

        <ReportSection compact={!overview && !elementaryAttendanceItems.length && !getItems('alunos-turma-fundamental').length} coverage="partial" model="metrics-table-stack" number={3} section={MUNICIPAL_REPORT_SECTIONS[2]} metadata={`INEP — Censo Escolar, base populacional e Média de Alunos por Turma · ${mainPeriod}`}>
          {overview ? <><SnapshotSummary values={[['Ensino Fundamental', overview.elementary.total.total], ['Anos iniciais', overview.elementary.initialYears.total], ['Anos finais', overview.elementary.finalYears.total]]} /><StageOfferTable caption="Matrículas do Ensino Fundamental por rede" stage={overview.elementary.total} /><ReportMunicipalReading><p>A rede municipal concentra {formatOverviewEnrollments(overview.elementary.total.byNetwork.municipal.enrollments)} matrículas do Ensino Fundamental, correspondentes a {formatOverviewPercentage(overview.elementary.total.byNetwork.municipal.share)} do total da etapa.</p></ReportMunicipalReading></> : null}
          <IndicatorTable caption="Atendimento estimado e organização das turmas" items={mergeReportIndicators(elementaryAttendanceItems, getItems('alunos-turma-fundamental'))} />
          <ReportNote>O indicador de 6 a 17 anos combina matrículas no município da escola e população residente. É uma aproximação contextual e não uma taxa líquida de atendimento. A média de alunos por turma não revela a distribuição entre escolas, redes ou localizações.</ReportNote>
        </ReportSection>

        <ReportSection compact={!overview && !highSchoolAttendanceItems.length && !getItems('alunos-turma-medio').length} coverage="partial" model="metrics-table-stack" number={4} section={MUNICIPAL_REPORT_SECTIONS[3]} metadata={`INEP — Censo Escolar, base populacional e Taxas de Rendimento Escolar · ${mainPeriod}`}>
          {overview ? (
            <>
              <SnapshotSummary values={[['Ensino Médio', overview.highSchool.total.total], ['Técnico integrado', overview.highSchool.integratedTechnical.total]]} />
              <StageOfferTable caption="Matrículas do Ensino Médio por rede" stage={overview.highSchool.total} />
              <ReportTableRegion metadata={`Ano-base: ${overview.schoolPerformance.referenceYear}`} title="Rendimento escolar no Ensino Médio" variant="compact">
                <table className="municipal-technical-report__table municipal-technical-report__table--rates municipal-technical-report__table--three-rates">
                  <caption className="municipal-technical-report__table-caption--semantic">Rendimento escolar no Ensino Médio</caption>
                  <thead>
                    <tr>
                      <th className="municipal-technical-report__numeric" scope="col">Aprovação</th>
                      <th className="municipal-technical-report__numeric" scope="col">Reprovação</th>
                      <th className="municipal-technical-report__numeric" scope="col">Abandono</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td className="municipal-technical-report__numeric">{formatSchoolPerformanceRate(overview.schoolPerformance.stages.highSchool.approval)}</td>
                      <td className="municipal-technical-report__numeric">{formatSchoolPerformanceRate(overview.schoolPerformance.stages.highSchool.failure)}</td>
                      <td className="municipal-technical-report__numeric">{formatSchoolPerformanceRate(overview.schoolPerformance.stages.highSchool.dropout)}</td>
                    </tr>
                  </tbody>
                </table>
              </ReportTableRegion>
              <ReportMunicipalReading>
                <p>A rede estadual reúne {formatOverviewEnrollments(overview.highSchool.total.byNetwork.state.enrollments)} matrículas do Ensino Médio, equivalentes a {formatOverviewPercentage(overview.highSchool.total.byNetwork.state.share)} do total da etapa.</p>
              </ReportMunicipalReading>
            </>
          ) : null}
          <IndicatorTable caption="Atendimento estimado e organização das turmas" items={mergeReportIndicators(highSchoolAttendanceItems, getItems('alunos-turma-medio'))} />
          <ReportNote>O indicador de 15 a 17 anos é contextual: combina matrículas no município da escola e população residente, portanto não equivale a uma taxa líquida de atendimento. A média de alunos por turma não revela a distribuição entre escolas, redes ou localizações.</ReportNote>
        </ReportSection>

        <ReportSection compact={!fullTimeItems.length} coverage="partial" model="table-only" number={5} section={MUNICIPAL_REPORT_SECTIONS[4]} metadata="INEP — Censo Escolar · Última referência disponível">
          <IndicatorTable caption="Oferta de educação em tempo integral" items={fullTimeItems} />
          <ReportNote>Os indicadores possuem universos diferentes: o percentual geral de matrículas, o público-alvo da rede pública e as escolas que atingem o limiar de jornada integral não devem ser somados.</ReportNote>
        </ReportSection>
      </ReportChapter>

      <ReportChapter chapter={MUNICIPAL_REPORT_CHAPTERS[1]}>
        <ReportSection compact={!environmentalEducationItems.length} coverage="partial" model="table-only" number={6} section={MUNICIPAL_REPORT_SECTIONS[5]} metadata="INEP — Censo Escolar · Última referência disponível">
          <IndicatorTable caption="Sustentabilidade socioambiental nas escolas" items={environmentalEducationItems} />
          <ReportNote>O indicador é declaratório e informa a presença de ações de educação ambiental; não mede sua intensidade, continuidade ou qualidade.</ReportNote>
        </ReportSection>

        <ReportSection coverage="partial" model="table-only" number={7} section={MUNICIPAL_REPORT_SECTIONS[6]} metadata="INEP — Sinopse Estatística e Censo Escolar · Última referência disponível">
          <IndicatorTable caption="Recortes indígenas e rurais disponíveis" items={getItems('indigena-cobertura-estimada-4-17', 'indigena-matriculas', 'indigena-estabelecimentos', 'indigena-docentes', 'indigena-turmas', 'mat-rural', 'rural-cobertura-estimada-4-17')} />
        </ReportSection>

        <ReportSection compact={!overview && !getItems('mat-eja').length && !ejaProfessionalItems.length} coverage="partial" model="metrics-only" number={8} section={MUNICIPAL_REPORT_SECTIONS[7]} metadata={`INEP — Censo Escolar e Sinopse Estatística · ${overview ? mainPeriod : 'Última referência disponível'}`}>
          {overview ? <><SnapshotSummary values={[['EJA', overview.basicEducationComposition.components.youthAndAdultEducation.total], ['EJA — Ensino Fundamental', overview.basicEducationComposition.components.youthAndAdultEducation.details.elementary], ['EJA — Ensino Médio', overview.basicEducationComposition.components.youthAndAdultEducation.details.highSchool]]} /><ReportMunicipalReading><p>A EJA registra {formatOverviewEnrollments(overview.basicEducationComposition.components.youthAndAdultEducation.total)} matrículas, distribuídas entre {formatOverviewEnrollments(overview.basicEducationComposition.components.youthAndAdultEducation.details.elementary)} no Ensino Fundamental e {formatOverviewEnrollments(overview.basicEducationComposition.components.youthAndAdultEducation.details.highSchool)} no Ensino Médio.</p></ReportMunicipalReading></> : <IndicatorTable caption="Matrículas da EJA" items={getItems('mat-eja')} />}
          <IndicatorTable caption="Articulação da EJA com a Educação Profissional" items={ejaProfessionalItems} />
          <ReportNote>O percentual considera as matrículas da EJA articuladas às ofertas profissionais previstas na metodologia em relação ao total elegível de matrículas da EJA.</ReportNote>
        </ReportSection>

        <ReportSection compact={!overview && !specialEducation} coverage="partial" model="metrics-only" number={9} section={MUNICIPAL_REPORT_SECTIONS[8]} metadata={`INEP — Censo Escolar · ${specialEducationYear ?? mainPeriod}`}>
          {overview ? <><SnapshotSummary values={[['Educação Especial', overview.specialEducation.total], ['Classes comuns', overview.specialEducation.commonClasses], ['Classes exclusivas', overview.specialEducation.exclusiveClasses]]} /><ReportMunicipalReading><p>Das {formatOverviewEnrollments(overview.specialEducation.total)} matrículas da Educação Especial, {formatOverviewEnrollments(overview.specialEducation.commonClasses)} estão em classes comuns e {formatOverviewEnrollments(overview.specialEducation.exclusiveClasses)} em classes exclusivas.</p></ReportMunicipalReading></> : null}
          <SpecialEducationTechnicalReportSummary
            document={specialEducation}
            error={specialEducationError}
            loading={specialEducationLoading}
          />
          <ReportNote>As matrículas da Educação Especial já estão incluídas nas etapas e modalidades. A quantidade de escolas que oferecem AEE não representa o número de estudantes atendidos.</ReportNote>
        </ReportSection>
      </ReportChapter>

      <ReportChapter chapter={MUNICIPAL_REPORT_CHAPTERS[2]}>
        <ReportSection compact={higherEducation?.availability === 'unavailable' && !higherEducationDiagnosticItems.length} model="table-only" number={10} section={MUNICIPAL_REPORT_SECTIONS[9]} metadata={`INEP e IBGE · ${higherEducation?.latestMunicipalUsableYear ?? higherEducationDiagnosticItems[0]?.currentYear ?? 'Sem referência municipal'}`}>
          <HigherEducationReportContent
            error={higherEducationError}
            loading={higherEducationLoading}
            viewModel={higherEducation}
          />
          <IndicatorTable caption="Indicadores de graduação e docentes em tempo integral" items={higherEducationDiagnosticItems} />
          <a className="platform-navigation-button" href={educationLink('educacao-superior')}>Abrir página de Educação Superior</a>
        </ReportSection>

        <ReportSection compact={!overview && !getItems('mat-profissional', 'oferta-total').length} model="metrics-only" number={11} section={MUNICIPAL_REPORT_SECTIONS[10]} metadata={`INEP — Censo Escolar e Sinopse Estatística · ${overview ? mainPeriod : 'Última referência disponível'}`}>
          {overview ? <><SnapshotSummary values={[['Técnico integrado ao Ensino Médio', overview.highSchool.integratedTechnical.total], ['Outras ofertas profissionais', overview.basicEducationComposition.components.otherProfessionalOffers.total]]} /><ReportMunicipalReading><p>A oferta profissional reúne {formatOverviewEnrollments(overview.highSchool.integratedTechnical.total)} matrículas em cursos técnicos integrados ao Ensino Médio e {formatOverviewEnrollments(overview.basicEducationComposition.components.otherProfessionalOffers.total)} nas demais ofertas profissionais.</p></ReportMunicipalReading></> : <IndicatorTable caption="Educação profissional e tecnológica" items={getItems('mat-profissional', 'oferta-total')} />}
        </ReportSection>
        <ReportSection compact={!getItems('docentes-total', 'docentes-infantil', 'docentes-fundamental', 'docentes-medio', 'docentes-eja', 'docentes-profissional').length && !teachingConditionsItems.length} coverage="partial" model="table-only" number={12} section={MUNICIPAL_REPORT_SECTIONS[11]} metadata="INEP — Censo Escolar e indicadores educacionais · Última referência disponível">
          <IndicatorTable caption="Docentes por etapa e modalidade" items={getItems('docentes-total', 'docentes-infantil', 'docentes-fundamental', 'docentes-medio', 'docentes-eja', 'docentes-profissional')} />
          <IndicatorTable caption="Organização das turmas, formação e vínculos docentes" items={teachingConditionsItems} />
          {byKey.get('docentes-total') ? <ReportMunicipalReading><p>O município registra {indicatorValue(byKey.get('docentes-total'))} docentes no total; o Ensino Fundamental reúne {indicatorValue(byKey.get('docentes-fundamental'))} profissionais na referência publicada.</p></ReportMunicipalReading> : null}
          <ReportNote>Conforme o indicador, os registros podem representar docentes, vínculos ou atuações; não devem ser somados como se fossem pessoas únicas.</ReportNote>
        </ReportSection>

      </ReportChapter>

      <ReportChapter chapter={MUNICIPAL_REPORT_CHAPTERS[3]}>
        <ReportSection compact={!democraticManagementItems.length} coverage="partial" model="table-only" number={13} section={MUNICIPAL_REPORT_SECTIONS[12]} metadata="INEP — Censo Escolar · Última referência disponível">
          <IndicatorTable caption="Participação social e instrumentos de gestão" items={democraticManagementItems} />
          <ReportNote>Os indicadores são registros declaratórios. Eles informam a existência do conselho ou do documento pedagógico, sem avaliar participação efetiva, frequência das reuniões ou qualidade da implementação.</ReportNote>
        </ReportSection>

        <ReportSection coverage="partial" model="table-only" number={14} section={MUNICIPAL_REPORT_SECTIONS[13]} metadata={`Censo Escolar/INEP · ${schoolInfrastructure?.referenceYear ?? 'Última referência disponível'}`}>
          {schoolInfrastructure ? (
            <SchoolInfrastructureReportTable contract={schoolInfrastructure} />
          ) : null}
          <IndicatorTable caption="Infraestrutura e conectividade disponíveis" items={getItems('internet', 'internet_alunos', 'internet_aprendizagem', 'banda_larga', 'rede_local', 'rede_wireless', 'desktop_aluno', 'comp_portatil_aluno', 'tablet_aluno')} />
          <IndicatorTable caption="Climatização e acessibilidade das salas de aula" items={classroomInfrastructureItems} />
          <ReportNote>Climatização e acessibilidade usam como denominador as salas de aula utilizadas. A acessibilidade das salas é um recorte parcial e não resume todas as condições de acessibilidade da escola.</ReportNote>
        </ReportSection>
        <ReportSection coverage="partial" model="coverage" number={15} section={MUNICIPAL_REPORT_SECTIONS[14]} metadata="Módulos financeiros da plataforma · Períodos conforme cada fonte">
          <p>Os cálculos financeiros permanecem nos módulos homologados de Financiamento, evitando duplicação de regras no relatório educacional.</p>
          <div className="municipal-technical-report__links">
            <a href={financialLink(FINANCIAL_PAGE_KEYS.panorama)}>Abrir Panorama financeiro</a>
            <a href={financialLink(FINANCIAL_PAGE_KEYS.application)}>Aplicação constitucional e execução das despesas</a>
            <a href={financialLink(FINANCIAL_PAGE_KEYS.fundeb)}>Fundeb</a>
            <a href={financialLink(FINANCIAL_PAGE_KEYS.vaar)}>VAAR</a>
            <a href={financialLink(FINANCIAL_PAGE_KEYS.pnate)}>PNATE</a>
          </div>
          <ReportNote>Os valores devem ser consultados nos módulos financeiros, que preservam as fontes e metodologias próprias de cada medida.</ReportNote>
        </ReportSection>
      </ReportChapter>

      <ReportChapter chapter={MUNICIPAL_REPORT_CHAPTERS[4]}>
        <ReportSection coverage="partial" model="coverage" number={16} section={MUNICIPAL_REPORT_SECTIONS[15]} metadata="INEP — Censo Escolar e IBGE — estimativas populacionais · Períodos conforme o módulo">
          <p>Os cenários combinam séries observadas, população e trajetórias futuras, distinguindo dado histórico de projeção.</p>
          <a className="platform-navigation-button" href={educationLink('demanda')}>Abrir Cenários de atendimento escolar</a>
        </ReportSection>

        <ReportSection coverage="partial" model="table-only" number={17} section={MUNICIPAL_REPORT_SECTIONS[16]} metadata="PNE 2026–2036 · Último ano disponível por indicador">
          <p>
            Os indicadores abaixo apresentam referências do PNE 2026–2036 que podem
            subsidiar a definição e o acompanhamento das metas do Plano Municipal de
            Educação. Quando houver metas próprias do PME disponíveis na plataforma, elas
            deverão ser apresentadas separadamente.
          </p>
          <a className="platform-navigation-button" href="#anexo-d" onClick={(event) => scrollToReportTarget(event, 'anexo-d')}>
            Consultar detalhamento no Anexo D
          </a>
        </ReportSection>
      </ReportChapter>

      <ReportChapter chapter={MUNICIPAL_REPORT_CHAPTERS[5]}>
        <ReportSection compact={!methodology.length && !sources.length} model="flow" number={18} section={MUNICIPAL_REPORT_SECTIONS[17]} metadata={`Fontes oficiais e notas metodológicas · ${mainPeriod}`}>
          {methodology.length ? <ul>{MUNICIPAL_REPORT_METHODOLOGY_NOTES.map((note) => <li key={note}>{note}</li>)}</ul> : <MissingInformation />}
        </ReportSection>

        <ReportSection model="table-only" number={19} section={MUNICIPAL_REPORT_SECTIONS[18]} metadata={`Bases públicas utilizadas · ${mainPeriod}`}>
          <div className="municipal-technical-report__annexes">
            <section className="municipal-technical-report__annex" id="anexo-a">
              <h4>Anexo A — Indicadores utilizados</h4>
              <ReportTableRegion title="Rastreabilidade das bases e indicadores" variant="compact">
                <table className="municipal-technical-report__table municipal-technical-report__table--traceability">
                  <caption className="municipal-technical-report__table-caption--semantic">Rastreabilidade das bases e indicadores</caption>
                  <colgroup>
                    <col className="municipal-technical-report__trace-col-section" />
                    <col className="municipal-technical-report__trace-col-indicator" />
                    <col className="municipal-technical-report__trace-col-source" />
                    <col className="municipal-technical-report__trace-col-year" />
                    <col className="municipal-technical-report__trace-col-unit" />
                  </colgroup>
                  <thead><tr><th scope="col">Seção</th><th scope="col">Indicador</th><th scope="col">Fonte</th><th scope="col">Ano</th><th scope="col">Unidade</th></tr></thead>
                  <tbody>
                    {traceabilityRows.map(([section, indicator, source, year, unit]) => (
                      <tr key={`${section}-${indicator}`}>
                        <th scope="row">{section}</th>
                        <td>{indicator}</td>
                        <td>{source}</td>
                        <td className="municipal-technical-report__numeric">{year == null ? '—' : String(year)}</td>
                        <td>{unit}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </ReportTableRegion>
            </section>

            <section className="municipal-technical-report__annex" id="anexo-b">
              <h4>Anexo B — Séries históricas</h4>
              {overview ? (
                <ReportTableRegion
                  metadata={`Período: ${overview.enrollmentComparison.years[0]}–${overview.enrollmentComparison.years[1]}`}
                  title="Matrículas da Educação Básica"
                  variant="historical"
                >
                  <table className="municipal-technical-report__table municipal-technical-report__table--historical">
                    <caption className="municipal-technical-report__table-caption--semantic">Série histórica de matrículas da Educação Básica</caption>
                    <thead><tr><th scope="col">Ano</th><th className="municipal-technical-report__numeric" scope="col">Matrículas</th></tr></thead>
                    <tbody>
                      <tr><th scope="row">{overview.enrollmentComparison.stages.basicEducation.total.value2015.year}</th><td className="municipal-technical-report__numeric">{formatOverviewEnrollments(overview.enrollmentComparison.stages.basicEducation.total.value2015)}</td></tr>
                      <tr><th scope="row">{overview.enrollmentComparison.stages.basicEducation.total.value2025.year}</th><td className="municipal-technical-report__numeric">{formatOverviewEnrollments(overview.enrollmentComparison.stages.basicEducation.total.value2025)}</td></tr>
                    </tbody>
                  </table>
                </ReportTableRegion>
              ) : <MissingInformation />}
            </section>

            <section className="municipal-technical-report__annex" id="anexo-c">
              <h4>Anexo C — Detalhamentos educacionais</h4>
              <div className="municipal-technical-report__links">
                <a href="#educacao-infantil" onClick={(event) => scrollToReportTarget(event, 'educacao-infantil')}>Etapas e redes de ensino</a>
                <a href="#territorios" onClick={(event) => scrollToReportTarget(event, 'territorios')}>Modalidades, localização e territórios</a>
                <a href={educationLink('panorama')}>Panorama educacional e tabelas municipais</a>
              </div>
            </section>

            <section className="municipal-technical-report__annex" id="anexo-d">
              <h4>Anexo D — Indicadores do PME</h4>
              <PmeReferenceIndicatorsTable
                dataSources={pmeReferenceData}
                diagnostic={pmeDiagnostic}
                error={pmeDiagnosticError}
                loading={pmeDiagnosticLoading}
              />
            </section>

            <section className="municipal-technical-report__annex" id="anexo-e">
              <h4>Anexo E — Bases e notas metodológicas</h4>
              {sources.length ? <div className="municipal-technical-report__sources">{sources.map((source) => <p key={source.id}><strong>{source.organization}</strong> — {source.title}, {source.referenceYear}{source.url ? <> · <a href={source.url}>fonte oficial</a></> : null}</p>)}</div> : <MissingInformation />}
              <div className="municipal-technical-report__links">
                <a href="#metodologia" onClick={(event) => scrollToReportTarget(event, 'metodologia')}>Metodologia do relatório</a>
                <a href={educationLink('metodologia')}>Catálogo de fontes e metodologia</a>
              </div>
            </section>
          </div>
        </ReportSection>
      </ReportChapter>

      <footer className="municipal-technical-report__footer">
        <span>Relatório Técnico Municipal</span>
        <span>{municipalityName}</span>
        <span>{emissionDate}</span>
        <span className="municipal-technical-report__page-number" aria-hidden="true" />
      </footer>
    </article>
  )
}
