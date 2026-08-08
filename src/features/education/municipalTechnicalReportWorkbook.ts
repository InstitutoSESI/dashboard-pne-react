import type { CellObject, Row, Sheet } from 'write-excel-file/browser'
import {
  SCHOOL_INFRASTRUCTURE_CUT_LABELS,
  SCHOOL_INFRASTRUCTURE_CUT_ORDER,
  SCHOOL_INFRASTRUCTURE_INDICATOR_ORDER,
  SCHOOL_INFRASTRUCTURE_METHODOLOGY,
  SCHOOL_INFRASTRUCTURE_PUBLIC_COPY,
  SCHOOL_INFRASTRUCTURE_SOURCE,
  type SchoolInfrastructureContract,
} from '../../data/schoolInfrastructureContract.js'
import type {
  Pne2026DiagnosticViewModel,
} from '../diagnostic/diagnosticTypes'
import type { HigherEducationViewModel } from './higherEducationTypes'
import {
  getMunicipalReportIndicatorLabel,
  MUNICIPAL_REPORT_CHAPTERS,
  MUNICIPAL_REPORT_METHODOLOGY_NOTES,
  MUNICIPAL_REPORT_PUBLIC_LABELS,
  MUNICIPAL_REPORT_SECTIONS,
} from './municipalTechnicalReportCatalog.js'
import type {
  DataState,
  EnrollmentComparisonValue,
  MunicipalEducationOverviewV1,
  SnapshotValue,
  StageSnapshot,
} from './municipalEducationOverviewTypes'
import type {
  SpecialEducationCut,
  SpecialEducationMunicipalDocument,
  SpecialEducationPoint,
  SpecialEducationYearCut,
} from './specialEducationTypes'
import {
  buildPmeReferenceTableModel,
  type PmeReferenceDataSources,
} from './pmeReferenceTableViewModel.js'

export interface MunicipalTechnicalReportExportIndicator {
  key: string
  label?: string
  currentDisplay?: string
  currentValue?: unknown
  currentYear?: unknown
  unit?: string
  source?: string
}

export interface MunicipalTechnicalReportWorkbookInput {
  educationItems: MunicipalTechnicalReportExportIndicator[]
  emissionDate: string
  higherEducation: HigherEducationViewModel | null
  municipalityId: string
  municipalityName: string
  municipalityPopulation?: unknown
  municipalitySlug?: string | null
  overview: MunicipalEducationOverviewV1 | null
  pmeDiagnostic: Pne2026DiagnosticViewModel | null
  pmeReferenceData?: PmeReferenceDataSources
  schoolInfrastructure: SchoolInfrastructureContract | null
  specialEducation: SpecialEducationMunicipalDocument | null
}

export interface MunicipalTechnicalReportWorkbook {
  fileName: string
  sheets: Sheet<Blob>[]
}

interface TrackingRow {
  section: number
  indicator: string
  value: number | string | null
  percent: boolean
  unit: string
  year: number | string | null
  source: string
  reference: number | null
  referencePercent: boolean
  referenceYear: number | null
  direction: string
  situation: string
  availability: string
  methodology: string
}

const COLORS = {
  deepGreen: '#14532D',
  green: '#166534',
  paleGreen: '#DCFCE7',
  paleYellow: '#FEF3C7',
  white: '#FFFFFF',
  border: '#CBD5E1',
  text: '#172033',
  muted: '#475569',
  unavailable: '#F1F5F9',
}

const SPECIAL_EDUCATION_CUT_LABELS: Record<SpecialEducationCut, string> = {
  total: 'Total municipal',
  publica: 'Rede pública',
  municipal: 'Rede municipal',
  estadual: 'Rede estadual',
  federal: 'Rede federal',
  privada: 'Rede privada',
  urbana: 'Localização urbana',
  rural: 'Localização rural',
}

const REPORT_EDUCATION_ITEM_SECTIONS: Record<string, number> = {
  'mat-integral': 5,
  'indigena-cobertura-estimada-4-17': 7,
  'indigena-matriculas': 7,
  'indigena-estabelecimentos': 7,
  'indigena-docentes': 7,
  'indigena-turmas': 7,
  'mat-rural': 7,
  'rural-cobertura-estimada-4-17': 7,
  'mat-eja': 8,
  eja_integrada_educacao_profissional: 8,
  'mat-profissional': 11,
  'oferta-total': 11,
  'docentes-total': 12,
  'docentes-infantil': 12,
  'docentes-fundamental': 12,
  'docentes-medio': 12,
  'docentes-eja': 12,
  'docentes-profissional': 12,
  'alunos-turma-infantil': 12,
  'alunos-turma-fundamental': 12,
  'alunos-turma-medio': 12,
  proposta_pedagogica: 13,
  internet: 14,
  internet_alunos: 14,
  internet_aprendizagem: 14,
  banda_larga: 14,
  rede_local: 14,
  rede_wireless: 14,
  desktop_aluno: 14,
  comp_portatil_aluno: 14,
  tablet_aluno: 14,
}

const DIAGNOSTIC_SECTIONS: Record<string, number> = {
  creche: 2,
  pre_escola: 2,
  basico_6_17: 3,
  alfabetizacao: 3,
  basico_15_17: 4,
  basico_integral: 5,
  escolas_integral: 5,
  educacao_ambiental: 6,
  eja_integrada_educacao_profissional_percentual: 8,
  eja_atendimento_18_mais: 8,
  aee_oferta_escolas_elegiveis: 9,
  superior_concluintes_oferta_local: 10,
  superior_docentes_mestres_doutores_sede: 10,
  graduacao_frequencia_18_24: 10,
  superior_completo_25_34: 10,
  taxa_bruta_graduacao: 10,
  docentes_tempo_integral_ies: 10,
  docentes_tempo_integral_universidades: 10,
  docentes_tempo_integral_centros_universitarios: 10,
  docentes_tempo_integral_faculdades: 10,
  adequacao_ai: 12,
  adequacao_af: 12,
  adequacao_em: 12,
  pos_graduacao: 12,
  temporarios: 12,
  conselho_escolar: 13,
  salas_climatizadas: 14,
  salas_acessiveis: 14,
  educacao_indigena_cobertura_estimada_4_17: 7,
}

const borderStyle = {
  borderColor: COLORS.border,
  borderStyle: 'thin' as const,
}

function cleanText(value: unknown) {
  return [...String(value ?? '')]
    .map((character) => {
      const code = character.charCodeAt(0)
      return code < 32 && code !== 9 && code !== 10 && code !== 13 ? ' ' : character
    })
    .join('')
    .replace(/\s+/g, ' ')
    .trim()
}

function textCell(value: unknown, style: Partial<CellObject> = {}): CellObject {
  return {
    value: cleanText(value),
    type: String,
    format: '@',
    textColor: COLORS.text,
    alignVertical: 'top',
    wrap: true,
    ...style,
  }
}

function numberCell(value: number | null | undefined, style: Partial<CellObject> = {}): CellObject | null {
  if (value == null || !Number.isFinite(value)) return null
  return {
    value,
    type: Number,
    format: '#,##0.00',
    align: 'right',
    alignVertical: 'top',
    ...style,
  }
}

function integerCell(value: number | null | undefined, style: Partial<CellObject> = {}): CellObject | null {
  if (value == null || !Number.isFinite(value)) return null
  return {
    value,
    type: Number,
    format: '#,##0',
    align: 'right',
    alignVertical: 'top',
    ...style,
  }
}

function percentageCell(value: number | null | undefined, style: Partial<CellObject> = {}): CellObject | null {
  if (value == null || !Number.isFinite(value)) return null
  return {
    value: value / 100,
    type: Number,
    format: '0.00%',
    align: 'right',
    alignVertical: 'top',
    ...style,
  }
}

function analyticCell(value: number | string | null, percent = false): CellObject | null {
  if (value == null) return null
  if (typeof value === 'number' && Number.isFinite(value)) {
    return percent ? percentageCell(value, borderStyle) : numberCell(value, borderStyle)
  }
  return textCell(value, borderStyle)
}

function editableCell(): CellObject {
  return textCell('', {
    ...borderStyle,
    backgroundColor: COLORS.paleYellow,
  })
}

function headerCell(value: string): CellObject {
  return textCell(value, {
    ...borderStyle,
    backgroundColor: COLORS.deepGreen,
    textColor: COLORS.white,
    fontWeight: 'bold',
    align: 'center',
    alignVertical: 'center',
    height: 42,
  })
}

function titleRows(title: string, subtitle: string, columnCount: number): Row[] {
  const fill = (cell: CellObject): Row => [
    cell,
    ...Array.from({ length: Math.max(0, columnCount - 1) }, () => null),
  ]
  return [
    fill(textCell(title, {
      backgroundColor: COLORS.deepGreen,
      textColor: COLORS.white,
      fontWeight: 'bold',
      fontSize: 16,
      height: 28,
      columnSpan: columnCount,
    })),
    fill(textCell(subtitle, {
      backgroundColor: COLORS.paleGreen,
      textColor: COLORS.green,
      fontStyle: 'italic',
      height: 34,
      columnSpan: columnCount,
    })),
  ]
}

function tableSheet(
  sheet: string,
  title: string,
  subtitle: string,
  headers: string[],
  rows: Row[],
  widths: number[],
  stickyColumnsCount = 1,
): Sheet<Blob> {
  return {
    sheet,
    data: [
      ...titleRows(title, subtitle, headers.length),
      headers.map(headerCell),
      ...rows,
    ],
    columns: widths.map((width) => ({ width })),
    stickyRowsCount: 3,
    stickyColumnsCount,
    orientation: 'landscape',
    showGridLines: false,
    zoomScale: 0.85,
  }
}

function stateLabel(state: DataState | string | null | undefined) {
  if (state === 'observed') return 'Dado observado'
  if (state === 'derived_zero') return 'Zero confirmado'
  if (state === 'partial') return 'Dado parcial'
  if (state === 'not_applicable') return 'Não se aplica'
  if (state === 'published') return 'Publicado'
  if (state === 'historical_only') return 'Somente série histórica'
  if (state === 'current') return 'Atual'
  return 'Dado indisponível'
}

function sectionTitle(section: number) {
  return MUNICIPAL_REPORT_SECTIONS[section - 1]?.shortTitle ?? 'Referência técnica'
}

function chapterTitle(section: number) {
  const sectionIndex = section - 1
  const chapter = MUNICIPAL_REPORT_CHAPTERS.find(
    (item) => sectionIndex >= item.startIndex && sectionIndex <= item.endIndex,
  )
  return chapter ? `Capítulo ${chapter.number} — ${chapter.title}` : 'Referência técnica'
}

function snapshotRow(
  section: number,
  indicator: string,
  snapshot: SnapshotValue,
  source: string,
  methodology: string,
  unit = 'matrículas',
  percent = false,
): TrackingRow {
  return {
    section,
    indicator,
    value: snapshot.value,
    percent,
    unit,
    year: snapshot.year,
    source,
    reference: null,
    referencePercent: false,
    referenceYear: null,
    direction: '',
    situation: 'Acompanhamento descritivo',
    availability: stateLabel(snapshot.state),
    methodology,
  }
}

function sourceForDiagnostic(
  diagnostic: Pne2026DiagnosticViewModel,
  sourceIds: string[],
) {
  const sourcesById = new Map(diagnostic.sources.map((source) => [source.id, source]))
  const labels = sourceIds
    .map((sourceId) => sourcesById.get(sourceId))
    .filter((source) => source != null)
    .map((source) => source.organization
      ? `${source.organization} — ${source.publicTitle}`
      : source.publicTitle)
  return labels.join('; ') || 'Fontes oficiais declaradas no diagnóstico público'
}

function directionLabel(direction: string | null | undefined) {
  if (direction === 'at_least') return 'Aumentar ou manter acima da referência'
  if (direction === 'at_most') return 'Reduzir ou manter abaixo da referência'
  return 'Leitura contextual'
}

function classificationLabel(classification: string | null) {
  if (classification === 'maintain') return 'Manter o resultado observado'
  if (classification === 'advance') return 'Requer avanço em direção à referência'
  return 'Sem classificação comparável'
}

function parseYear(value: unknown): number | string | null {
  if (typeof value === 'number' && Number.isFinite(value)) return value
  const text = cleanText(value)
  return text || null
}

function parseIndicatorValue(item: MunicipalTechnicalReportExportIndicator) {
  if (typeof item.currentValue === 'number' && Number.isFinite(item.currentValue)) {
    return item.currentValue
  }
  const display = cleanText(item.currentDisplay)
  return display && display !== '—' ? display : null
}

function isPercentageIndicator(item: MunicipalTechnicalReportExportIndicator) {
  const definition = MUNICIPAL_REPORT_PUBLIC_LABELS[item.key]
  return /percent|%/i.test(`${definition?.unitLabel ?? ''} ${item.unit ?? ''} ${item.currentDisplay ?? ''}`)
}

function coreTrackingRows(overview: MunicipalEducationOverviewV1 | null): TrackingRow[] {
  if (!overview) return []
  const censo = 'INEP — Censo Escolar'
  const territorialNote = 'Matrículas segundo a localização da escola; os totais oficiais não são recompostos pela soma das etapas.'
  const rows: TrackingRow[] = [
    snapshotRow(1, 'Matrículas da Educação Básica', overview.basicEducation.total, censo, territorialNote),
    snapshotRow(2, 'Matrículas da Educação Infantil', overview.earlyChildhood.total.total, censo, territorialNote),
    snapshotRow(2, 'Matrículas em creche', overview.earlyChildhood.creche.total, censo, territorialNote),
    snapshotRow(2, 'Matrículas na pré-escola', overview.earlyChildhood.preSchool.total, censo, territorialNote),
    snapshotRow(3, 'Matrículas do Ensino Fundamental', overview.elementary.total.total, censo, territorialNote),
    snapshotRow(3, 'Matrículas dos anos iniciais do Ensino Fundamental', overview.elementary.initialYears.total, censo, territorialNote),
    snapshotRow(3, 'Matrículas dos anos finais do Ensino Fundamental', overview.elementary.finalYears.total, censo, territorialNote),
    snapshotRow(4, 'Matrículas do Ensino Médio', overview.highSchool.total.total, censo, territorialNote),
    snapshotRow(4, 'Matrículas em curso técnico integrado ao Ensino Médio', overview.highSchool.integratedTechnical.total, censo, territorialNote),
    snapshotRow(8, 'Matrículas da Educação de Jovens e Adultos', overview.basicEducationComposition.components.youthAndAdultEducation.total, censo, territorialNote),
    snapshotRow(8, 'Matrículas da EJA — Ensino Fundamental', overview.basicEducationComposition.components.youthAndAdultEducation.details.elementary, censo, territorialNote),
    snapshotRow(8, 'Matrículas da EJA — Ensino Médio', overview.basicEducationComposition.components.youthAndAdultEducation.details.highSchool, censo, territorialNote),
    snapshotRow(9, 'Matrículas da Educação Especial', overview.specialEducation.total, censo, 'Recorte transversal já incluído nas etapas e modalidades.'),
    snapshotRow(9, 'Matrículas da Educação Especial em classes comuns', overview.specialEducation.commonClasses, censo, 'Recorte transversal já incluído nas etapas e modalidades.'),
    snapshotRow(9, 'Matrículas da Educação Especial em classes exclusivas', overview.specialEducation.exclusiveClasses, censo, 'Recorte transversal já incluído nas etapas e modalidades.'),
    snapshotRow(11, 'Matrículas em outras ofertas de Educação Profissional', overview.basicEducationComposition.components.otherProfessionalOffers.total, censo, territorialNote),
  ]

  const performance = [
    ['Ensino Fundamental', overview.schoolPerformance.stages.elementary],
    ['Anos iniciais do Ensino Fundamental', overview.schoolPerformance.stages.initialYears],
    ['Anos finais do Ensino Fundamental', overview.schoolPerformance.stages.finalYears],
    ['Ensino Médio', overview.schoolPerformance.stages.highSchool],
  ] as const
  performance.forEach(([stage, values], stageIndex) => {
    const section = stageIndex === performance.length - 1 ? 4 : 3
    rows.push(
      snapshotRow(section, `Taxa de aprovação — ${stage}`, values.approval, 'INEP — Taxas de Rendimento Escolar', 'Percentual municipal publicado pelo INEP.', 'percentual', true),
      snapshotRow(section, `Taxa de reprovação — ${stage}`, values.failure, 'INEP — Taxas de Rendimento Escolar', 'Percentual municipal publicado pelo INEP.', 'percentual', true),
      snapshotRow(section, `Taxa de abandono — ${stage}`, values.dropout, 'INEP — Taxas de Rendimento Escolar', 'Percentual municipal publicado pelo INEP.', 'percentual', true),
    )
  })
  return rows
}

function educationItemTrackingRows(items: MunicipalTechnicalReportExportIndicator[]) {
  return items.flatMap((item): TrackingRow[] => {
    const section = REPORT_EDUCATION_ITEM_SECTIONS[item.key]
    if (!section) return []
    const definition = MUNICIPAL_REPORT_PUBLIC_LABELS[item.key]
    const value = parseIndicatorValue(item)
    return [{
      section,
      indicator: getMunicipalReportIndicatorLabel(item.key, item.label),
      value,
      percent: typeof value === 'number' && isPercentageIndicator(item),
      unit: definition?.unitLabel ?? (cleanText(item.unit) || 'medida publicada'),
      year: parseYear(item.currentYear),
      source: definition?.sourceLabel ?? (cleanText(item.source) || 'Fonte oficial declarada na plataforma'),
      reference: null,
      referencePercent: false,
      referenceYear: null,
      direction: '',
      situation: 'Acompanhamento descritivo',
      availability: value == null ? 'Dado indisponível' : 'Disponível',
      methodology: definition?.interpretationNote ?? 'Consultar a metodologia do indicador na plataforma.',
    }]
  })
}

function diagnosticTrackingRows(diagnostic: Pne2026DiagnosticViewModel | null) {
  if (!diagnostic) return []
  return diagnostic.goals.flatMap((goal) => goal.results).map((result): TrackingRow => {
    const isComplementary = result.mode === 'complementary'
    const isAvailable = result.dataStatus === 'available'
    const section = DIAGNOSTIC_SECTIONS[result.indicatorId] ?? 17
    const definition = MUNICIPAL_REPORT_PUBLIC_LABELS[result.indicatorId]
    return {
      section,
      indicator: definition?.publicTitle ?? result.publicName,
      value: isAvailable
        ? result.current.displayValue
        : result.dataStatusLabel ?? 'Não disponível para o período',
      percent: result.current.unit === 'percent',
      unit: definition?.unitLabel
        ?? (result.current.unit === 'percent' ? 'percentual' : result.current.unit === 'years' ? 'anos' : result.current.unit === 'count' ? 'quantidade' : 'índice'),
      year: result.current.year,
      source: sourceForDiagnostic(diagnostic, result.sourceIds),
      reference: isComplementary || !isAvailable ? null : result.indicatorReference?.value ?? null,
      referencePercent: !isComplementary && isAvailable && result.current.unit === 'percent',
      referenceYear: isComplementary || !isAvailable ? null : result.indicatorReference?.year ?? null,
      direction: isComplementary
        ? 'Acompanhamento descritivo'
        : directionLabel(result.indicatorReference?.direction ?? result.direction),
      situation: isComplementary || !isAvailable
        ? ''
        : result.mode === 'tracking'
          ? result.status ?? ''
          : classificationLabel(result.classification),
      availability: isAvailable
        ? 'Disponível'
        : result.dataStatusLabel ?? 'Não disponível para o período',
      methodology: [
        definition?.interpretationNote ?? result.publicDescription,
        isComplementary
          ? 'Indicador complementar; não mede sozinho o cumprimento da meta.'
          : result.relationshipLabel,
      ].filter(Boolean).join(' '),
    }
  })
}

function specialEducationReference(document: SpecialEducationMunicipalDocument | null) {
  if (!document) return null
  return document.years.find(({ year }) => year === 2025)
    ?? [...document.years].sort((left, right) => right.year - left.year)[0]
    ?? null
}

function specialPointTracking(
  year: number,
  indicator: string,
  point: SpecialEducationPoint,
  unit: string,
  percent = false,
): TrackingRow {
  return {
    section: 9,
    indicator,
    value: point.value,
    percent,
    unit,
    year,
    source: 'INEP — Censo Escolar',
    reference: null,
    referencePercent: false,
    referenceYear: null,
    direction: '',
    situation: 'Acompanhamento descritivo',
    availability: stateLabel(point.state),
    methodology: 'Recorte total do município; a Educação Especial é transversal às etapas e modalidades.',
  }
}

function specialEducationTrackingRows(document: SpecialEducationMunicipalDocument | null) {
  const reference = specialEducationReference(document)
  const total = reference?.cuts.total
  if (!reference || !total) return []
  return [
    specialPointTracking(reference.year, 'Inclusão das matrículas da Educação Especial em classes comuns', total.commonClassInclusionRate, 'percentual das matrículas', true),
    specialPointTracking(reference.year, 'Escolas que oferecem Atendimento Educacional Especializado', total.aee.schoolsOfferingAee, 'escolas'),
    specialPointTracking(reference.year, 'Escolas com sala de recursos multifuncionais', total.aee.schoolsWithResourceRoom, 'escolas'),
    specialPointTracking(reference.year, 'Matrículas na Educação Bilíngue de Surdos', total.bilingualDeafEducation.enrollments, 'matrículas'),
  ]
}

function higherEducationTrackingRows(viewModel: HigherEducationViewModel | null) {
  if (!viewModel) return []
  return viewModel.indicators.flatMap((indicator): TrackingRow[] => {
    if (!indicator.latestPoint) return []
    return [{
      section: 10,
      indicator: indicator.title,
      value: indicator.latestPoint.value,
      percent: false,
      unit: indicator.unit,
      year: indicator.latestPoint.year,
      source: 'INEP — Sinopse Estatística da Educação Superior',
      reference: null,
      referencePercent: false,
      referenceYear: null,
      direction: '',
      situation: 'Acompanhamento descritivo',
      availability: stateLabel(indicator.latestPoint.status),
      methodology: indicator.description,
    }]
  })
}

function infrastructureTrackingRows(contract: SchoolInfrastructureContract | null) {
  if (!contract) return []
  const reference = contract.years.find(({ year }) => year === contract.referenceYear)
  if (!reference) return []
  return SCHOOL_INFRASTRUCTURE_INDICATOR_ORDER.map((key): TrackingRow => {
    const result = reference.cuts.total.indicators[key]
    return {
      section: 14,
      indicator: SCHOOL_INFRASTRUCTURE_PUBLIC_COPY[key].label,
      value: result.percentage,
      percent: true,
      unit: 'percentual de escolas',
      year: reference.year,
      source: SCHOOL_INFRASTRUCTURE_SOURCE,
      reference: null,
      referencePercent: false,
      referenceYear: null,
      direction: '',
      situation: 'Acompanhamento descritivo',
      availability: stateLabel(result.status),
      methodology: SCHOOL_INFRASTRUCTURE_METHODOLOGY,
    }
  })
}

function deduplicateTrackingRows(rows: TrackingRow[]) {
  const unique = new Map<string, TrackingRow>()
  rows.forEach((row) => {
    const key = `${row.section}|${row.indicator.toLocaleLowerCase('pt-BR')}|${String(row.year ?? '')}`
    if (!unique.has(key)) unique.set(key, row)
  })
  return [...unique.values()].sort((left, right) =>
    left.section - right.section || left.indicator.localeCompare(right.indicator, 'pt-BR'))
}

function buildTrackingSheet(input: MunicipalTechnicalReportWorkbookInput) {
  const headers = [
    'Capítulo temático',
    'Seção do relatório',
    'Indicador',
    'Resultado atual',
    'Unidade',
    'Ano de referência',
    'Fonte',
    'Referência do PNE',
    'Ano da referência',
    'Direção desejável',
    'Situação em relação à referência',
    'Disponibilidade',
    'Observação metodológica',
    'Meta municipal (preencher)',
    'Prazo municipal (preencher)',
    'Responsável pelo acompanhamento (preencher)',
    'Periodicidade de revisão (preencher)',
    'Observações da gestão (preencher)',
  ]
  const trackingRows = deduplicateTrackingRows([
    ...coreTrackingRows(input.overview),
    ...educationItemTrackingRows(input.educationItems),
    ...diagnosticTrackingRows(input.pmeDiagnostic),
    ...specialEducationTrackingRows(input.specialEducation),
    ...higherEducationTrackingRows(input.higherEducation),
    ...infrastructureTrackingRows(input.schoolInfrastructure),
  ])
  const rows = trackingRows.map((row): Row => [
    textCell(chapterTitle(row.section), borderStyle),
    textCell(`${String(row.section).padStart(2, '0')} — ${sectionTitle(row.section)}`, borderStyle),
    textCell(row.indicator, borderStyle),
    analyticCell(row.value, row.percent),
    textCell(row.unit, borderStyle),
    typeof row.year === 'number' ? integerCell(row.year, borderStyle) : textCell(row.year ?? '', borderStyle),
    textCell(row.source, borderStyle),
    analyticCell(row.reference, row.referencePercent),
    integerCell(row.referenceYear, borderStyle),
    textCell(row.direction, borderStyle),
    textCell(row.situation, borderStyle),
    textCell(row.availability, {
      ...borderStyle,
      backgroundColor: row.availability.includes('indisponível') ? COLORS.unavailable : undefined,
    }),
    textCell(row.methodology, borderStyle),
    editableCell(),
    editableCell(),
    editableCell(),
    editableCell(),
    editableCell(),
  ])
  return tableSheet(
    'Acompanhamento',
    'Matriz municipal de acompanhamento educacional',
    'As cinco últimas colunas, em amarelo, foram preparadas para preenchimento pela gestão municipal. Percentuais são armazenados como números e podem ser usados em fórmulas.',
    headers,
    rows,
    [18, 28, 46, 17, 22, 16, 32, 18, 16, 25, 28, 20, 54, 24, 22, 30, 26, 38],
    3,
  )
}

function stageNetworkRows(overview: MunicipalEducationOverviewV1 | null) {
  if (!overview) return []
  const stages: Array<[string, StageSnapshot]> = [
    ['Educação Infantil', overview.earlyChildhood.total],
    ['Creche', overview.earlyChildhood.creche],
    ['Pré-escola', overview.earlyChildhood.preSchool],
    ['Ensino Fundamental', overview.elementary.total],
    ['Anos iniciais do Ensino Fundamental', overview.elementary.initialYears],
    ['Anos finais do Ensino Fundamental', overview.elementary.finalYears],
    ['Ensino Médio', overview.highSchool.total],
  ]
  const networks = [
    ['Municipal', (stage: StageSnapshot) => stage.byNetwork.municipal],
    ['Estadual', (stage: StageSnapshot) => stage.byNetwork.state],
    ['Federal', (stage: StageSnapshot) => stage.byNetwork.federal],
    ['Privada', (stage: StageSnapshot) => stage.byNetwork.private],
    ['Rede pública — subtotal', (stage: StageSnapshot) => stage.byNetwork.publicSubtotal],
  ] as const
  return stages.flatMap(([stageLabel, stage]) => [
    [
      textCell(stageLabel, borderStyle),
      textCell('Total', borderStyle),
      integerCell(stage.total.value, borderStyle),
      stage.total.value != null
        && (stage.total.state === 'observed' || stage.total.state === 'derived_zero')
        ? percentageCell(100, borderStyle)
        : null,
      integerCell(stage.total.year, borderStyle),
      textCell(stateLabel(stage.total.state), borderStyle),
      textCell('INEP — Censo Escolar', borderStyle),
      textCell(overview.universe.locationLabel, borderStyle),
    ],
    ...networks.map(([networkLabel, select]): Row => {
      const value = select(stage)
      return [
        textCell(stageLabel, borderStyle),
        textCell(networkLabel, borderStyle),
        integerCell(value.enrollments.value, borderStyle),
        percentageCell(value.share.value, borderStyle),
        integerCell(value.enrollments.year, borderStyle),
        textCell(stateLabel(value.enrollments.state), borderStyle),
        textCell('INEP — Censo Escolar', borderStyle),
        textCell(overview.universe.locationLabel, borderStyle),
      ]
    }),
  ])
}

function buildNetworkSheet(input: MunicipalTechnicalReportWorkbookInput) {
  return tableSheet(
    'Matrículas por rede',
    'Matrículas por etapa e rede de ensino',
    'Os totais são oficiais. A referência territorial é a localização da escola; uma matrícula não identifica necessariamente o município de residência do estudante.',
    ['Etapa', 'Rede de ensino', 'Matrículas', 'Participação na etapa', 'Ano', 'Estado do dado', 'Fonte', 'Base territorial'],
    stageNetworkRows(input.overview),
    [34, 25, 16, 20, 12, 20, 26, 28],
    2,
  )
}

function buildPerformanceSheet(input: MunicipalTechnicalReportWorkbookInput) {
  const overview = input.overview
  const rows: Row[] = []
  if (overview) {
    const stages = [
      ['Ensino Fundamental', overview.schoolPerformance.stages.elementary],
      ['Anos iniciais do Ensino Fundamental', overview.schoolPerformance.stages.initialYears],
      ['Anos finais do Ensino Fundamental', overview.schoolPerformance.stages.finalYears],
      ['Ensino Médio', overview.schoolPerformance.stages.highSchool],
    ] as const
    stages.forEach(([stage, values]) => {
      const measures = [
        ['Aprovação', values.approval],
        ['Reprovação', values.failure],
        ['Abandono', values.dropout],
      ] as const
      measures.forEach(([measure, value]) => rows.push([
        textCell(stage, borderStyle),
        textCell(measure, borderStyle),
        percentageCell(value.value, borderStyle),
        integerCell(value.year, borderStyle),
        textCell(stateLabel(value.state), borderStyle),
        textCell('INEP — Taxas de Rendimento Escolar', borderStyle),
        textCell('Percentual municipal publicado para o conjunto das redes; não é média simples entre escolas.', borderStyle),
      ]))
    })
  }
  return tableSheet(
    'Rendimento escolar',
    'Taxas de rendimento escolar',
    'Aprovação, reprovação e abandono são medidas distintas e devem ser acompanhadas com o ano e o universo publicados pelo INEP.',
    ['Etapa', 'Medida', 'Resultado', 'Ano', 'Estado do dado', 'Fonte', 'Observação metodológica'],
    rows,
    [36, 18, 16, 12, 20, 34, 56],
    2,
  )
}

function historicalRows(overview: MunicipalEducationOverviewV1 | null) {
  if (!overview) return []
  const comparisons: Array<[string, EnrollmentComparisonValue]> = [
    ['Matrículas da Educação Básica', overview.enrollmentComparison.stages.basicEducation.total],
    ['Matrículas da Educação Infantil', overview.enrollmentComparison.stages.earlyChildhood.total],
    ['Matrículas em creche', overview.enrollmentComparison.stages.creche.total],
    ['Matrículas na pré-escola', overview.enrollmentComparison.stages.preSchool.total],
    ['Matrículas do Ensino Fundamental', overview.enrollmentComparison.stages.elementary.total],
    ['Matrículas dos anos iniciais do Ensino Fundamental', overview.enrollmentComparison.stages.initialYears.total],
    ['Matrículas dos anos finais do Ensino Fundamental', overview.enrollmentComparison.stages.finalYears.total],
    ['Matrículas do Ensino Médio', overview.enrollmentComparison.stages.highSchool.total],
    ['Matrículas da Educação de Jovens e Adultos', overview.enrollmentComparison.stages.youthAndAdultEducation.total],
  ]
  return comparisons.flatMap(([label, comparison]): Row[] => [
    [
      textCell(label, borderStyle),
      integerCell(comparison.value2015.year, borderStyle),
      integerCell(comparison.value2015.value, borderStyle),
      textCell(stateLabel(comparison.value2015.state), borderStyle),
      numberCell(comparison.absoluteChange, borderStyle),
      percentageCell(comparison.percentageChange.value, borderStyle),
      textCell('INEP — Censo Escolar', borderStyle),
      textCell(overview.enrollmentComparison.methodologyNote, borderStyle),
    ],
    [
      textCell(label, borderStyle),
      integerCell(comparison.value2025.year, borderStyle),
      integerCell(comparison.value2025.value, borderStyle),
      textCell(stateLabel(comparison.value2025.state), borderStyle),
      numberCell(comparison.absoluteChange, borderStyle),
      percentageCell(comparison.percentageChange.value, borderStyle),
      textCell('INEP — Censo Escolar', borderStyle),
      textCell(overview.enrollmentComparison.methodologyNote, borderStyle),
    ],
  ])
}

function buildHistoricalSheet(input: MunicipalTechnicalReportWorkbookInput) {
  return tableSheet(
    'Série histórica',
    'Comparação histórica das matrículas',
    'A variação é apresentada para o período completo. Os valores de cada ano permanecem em linhas separadas para facilitar filtros, fórmulas e gráficos.',
    ['Indicador', 'Ano', 'Valor', 'Estado do dado', 'Variação absoluta no período', 'Variação percentual no período', 'Fonte', 'Observação metodológica'],
    historicalRows(input.overview),
    [44, 12, 16, 20, 25, 27, 26, 54],
    2,
  )
}

function buildInfrastructureSheet(input: MunicipalTechnicalReportWorkbookInput) {
  const contract = input.schoolInfrastructure
  const rows: Row[] = []
  if (contract) {
    const reference = contract.years.find(({ year }) => year === contract.referenceYear)
    if (reference) {
      SCHOOL_INFRASTRUCTURE_CUT_ORDER.forEach((cutKey) => {
        SCHOOL_INFRASTRUCTURE_INDICATOR_ORDER.forEach((indicatorKey) => {
          const result = reference.cuts[cutKey].indicators[indicatorKey]
          rows.push([
            textCell(SCHOOL_INFRASTRUCTURE_CUT_LABELS[cutKey], borderStyle),
            textCell(SCHOOL_INFRASTRUCTURE_PUBLIC_COPY[indicatorKey].label, borderStyle),
            integerCell(result.numerator, borderStyle),
            integerCell(result.denominator, borderStyle),
            percentageCell(result.percentage, borderStyle),
            integerCell(result.totalActiveSchools, borderStyle),
            integerCell(result.observedSchools, borderStyle),
            integerCell(result.missingSchools, borderStyle),
            textCell(stateLabel(result.status), borderStyle),
            integerCell(reference.year, borderStyle),
            textCell(SCHOOL_INFRASTRUCTURE_SOURCE, borderStyle),
            textCell(SCHOOL_INFRASTRUCTURE_METHODOLOGY, borderStyle),
          ])
        })
      })
    }
  }
  return tableSheet(
    'Infraestrutura',
    'Infraestrutura escolar por rede e localização',
    'Numerador, denominador e registros sem resposta são mantidos em colunas próprias para permitir auditoria e construção de indicadores locais.',
    ['Recorte', 'Indicador', 'Escolas com a condição', 'Escolas com resposta válida', 'Percentual', 'Escolas ativas', 'Escolas observadas', 'Escolas sem resposta', 'Situação', 'Ano', 'Fonte', 'Metodologia'],
    rows,
    [24, 44, 21, 24, 16, 16, 18, 20, 18, 12, 24, 54],
    2,
  )
}

function specialEducationRows(document: SpecialEducationMunicipalDocument | null) {
  const reference = specialEducationReference(document)
  if (!reference) return []
  const metrics = (cut: SpecialEducationYearCut): Array<[string, SpecialEducationPoint, string, boolean]> => [
    ['Matrículas da Educação Especial', cut.specialEducation.enrollments, 'matrículas', false],
    ['Matrículas da Educação Especial em classes comuns', cut.specialEducation.commonClassEnrollments, 'matrículas', false],
    ['Matrículas da Educação Especial em classes exclusivas', cut.specialEducation.exclusiveClassEnrollments, 'matrículas', false],
    ['Inclusão em classes comuns', cut.commonClassInclusionRate, 'percentual das matrículas', true],
    ['Escolas que oferecem Atendimento Educacional Especializado', cut.aee.schoolsOfferingAee, 'escolas', false],
    ['Escolas com sala de recursos multifuncionais', cut.aee.schoolsWithResourceRoom, 'escolas', false],
    ['Matrículas na Educação Bilíngue de Surdos', cut.bilingualDeafEducation.enrollments, 'matrículas', false],
  ]
  return (Object.entries(reference.cuts) as Array<[SpecialEducationCut, SpecialEducationYearCut]>)
    .flatMap(([cutKey, cut]) => metrics(cut).map(([label, point, unit, percent]): Row => [
      textCell(SPECIAL_EDUCATION_CUT_LABELS[cutKey], borderStyle),
      textCell(label, borderStyle),
      percent ? percentageCell(point.value, borderStyle) : integerCell(point.value, borderStyle),
      textCell(unit, borderStyle),
      integerCell(reference.year, borderStyle),
      textCell(stateLabel(point.state), borderStyle),
      integerCell(point.numerator, borderStyle),
      integerCell(point.denominator, borderStyle),
      textCell('INEP — Censo Escolar', borderStyle),
      textCell(point.reason ?? 'A Educação Especial é transversal às etapas e modalidades.', borderStyle),
    ]))
}

function buildSpecialEducationSheet(input: MunicipalTechnicalReportWorkbookInput) {
  return tableSheet(
    'Educação Especial',
    'Educação Especial, AEE e Educação Bilíngue de Surdos',
    'A planilha preserva zero, dado parcial, indisponibilidade e não aplicabilidade. Matrículas da Educação Especial já estão incluídas nas etapas e modalidades.',
    ['Recorte', 'Indicador', 'Resultado', 'Unidade', 'Ano', 'Estado do dado', 'Numerador', 'Denominador', 'Fonte', 'Observação'],
    specialEducationRows(input.specialEducation),
    [25, 50, 17, 24, 12, 20, 16, 16, 26, 52],
    2,
  )
}

function buildHigherEducationSheet(input: MunicipalTechnicalReportWorkbookInput) {
  const rows: Row[] = []
  const viewModel = input.higherEducation
  if (viewModel) {
    viewModel.indicators.forEach((indicator) => {
      indicator.series.forEach((point) => rows.push([
        textCell('Série anual', borderStyle),
        textCell(indicator.title, borderStyle),
        textCell('', borderStyle),
        integerCell(point.year, borderStyle),
        integerCell(point.value, borderStyle),
        textCell(indicator.unit, borderStyle),
        textCell(stateLabel(point.status), borderStyle),
        textCell('INEP — Sinopse Estatística da Educação Superior', borderStyle),
        textCell(indicator.description, borderStyle),
      ]))
    })
    viewModel.breakdowns.forEach((breakdown) => {
      breakdown.categories.forEach((category) => rows.push([
        textCell('Recorte do ano mais recente', borderStyle),
        textCell(breakdown.title, borderStyle),
        textCell(category.label, borderStyle),
        integerCell(breakdown.year, borderStyle),
        integerCell(category.value, borderStyle),
        textCell('quantidade', borderStyle),
        textCell(stateLabel(category.status), borderStyle),
        textCell('INEP — Sinopse Estatística da Educação Superior', borderStyle),
        textCell(breakdown.description, borderStyle),
      ]))
    })
  }
  return tableSheet(
    'Educação Superior',
    'Educação Superior — séries e recortes',
    'Os dados municipais desta edição referem-se à graduação. Pós-graduação não está incluída na base municipal utilizada.',
    ['Tipo de informação', 'Indicador ou recorte', 'Categoria', 'Ano', 'Valor', 'Unidade', 'Estado do dado', 'Fonte', 'Descrição'],
    rows,
    [25, 46, 30, 12, 16, 18, 20, 38, 54],
    2,
  )
}

function buildPneReferenceSheet(input: MunicipalTechnicalReportWorkbookInput) {
  const diagnostic = input.pmeDiagnostic
  const rows: Row[] = []
  if (diagnostic) {
    const model = buildPmeReferenceTableModel(diagnostic, input.pmeReferenceData)
    model.groups.forEach((group) => {
      group.rows.forEach((viewRow) => {
        const result = viewRow.result
        const isComplementary = result.mode === 'complementary'
        const definition = MUNICIPAL_REPORT_PUBLIC_LABELS[result.indicatorId]
        const rawComponents = viewRow.rawComponents
        rows.push([
          textCell(`Meta ${result.goalId}`, borderStyle),
          textCell(group.label, borderStyle),
          textCell(definition?.publicTitle ?? result.publicName, borderStyle),
          textCell(result.publicDescription, borderStyle),
          result.dataStatus !== 'available'
            ? textCell(result.dataStatusLabel ?? 'Não disponível para o período', borderStyle)
            : result.current.unit === 'percent'
            ? percentageCell(result.current.displayValue, borderStyle)
            : numberCell(result.current.displayValue, borderStyle),
          textCell(definition?.unitLabel ?? result.current.unit, borderStyle),
          integerCell(result.current.year, borderStyle),
          numberCell(rawComponents?.numerator, borderStyle),
          textCell(rawComponents?.numeratorUnit ?? '', borderStyle),
          numberCell(rawComponents?.denominator, borderStyle),
          textCell(rawComponents?.denominatorUnit ?? '', borderStyle),
          isComplementary || result.dataStatus !== 'available'
            ? null
            : result.current.unit === 'percent'
              ? percentageCell(result.indicatorReference?.value, borderStyle)
              : numberCell(result.indicatorReference?.value, borderStyle),
          isComplementary || result.dataStatus !== 'available'
            ? null
            : integerCell(result.indicatorReference?.year, borderStyle),
          textCell(
            isComplementary
              ? 'Acompanhamento descritivo'
              : result.dataStatus !== 'available'
                ? ''
              : directionLabel(result.indicatorReference?.direction ?? result.direction),
            borderStyle,
          ),
          textCell(
            isComplementary
              ? 'Indicador complementar; não mede sozinho o cumprimento da meta'
              : result.relationshipLabel ?? '',
            borderStyle,
          ),
          textCell(
            isComplementary
              ? ''
              : result.dataStatus !== 'available'
                ? result.dataStatusLabel ?? 'Não disponível para o período'
              : result.mode === 'tracking'
                ? result.status ?? ''
              : classificationLabel(result.classification),
            borderStyle,
          ),
          numberCell(isComplementary ? null : result.remainingGap, borderStyle),
          textCell(sourceForDiagnostic(diagnostic, result.sourceIds), borderStyle),
          textCell(definition?.interpretationNote ?? result.publicReading ?? result.relationshipNote, borderStyle),
        ])
      })
    })
  }
  return tableSheet(
    'Referências PNE',
    'Referências do PNE para o acompanhamento municipal',
    'As referências nacionais subsidiam o planejamento, mas não substituem metas próprias aprovadas no Plano Municipal de Educação.',
    ['Meta do PNE', 'Tema', 'Indicador', 'Descrição', 'Resultado atual', 'Unidade', 'Ano do resultado', 'Numerador', 'Unidade do numerador', 'Denominador', 'Unidade do denominador', 'Referência', 'Ano da referência', 'Direção desejável', 'Relação com a meta', 'Situação', 'Distância restante', 'Fonte', 'Nota de interpretação'],
    rows,
    [15, 30, 48, 54, 18, 24, 16, 16, 22, 16, 22, 16, 17, 28, 36, 28, 20, 38, 56],
    3,
  )
}

function formatPopulation(value: unknown) {
  const candidate = typeof value === 'object' && value != null
    ? (value as Record<string, unknown>).value
      ?? (value as Record<string, unknown>).valor
      ?? (value as Record<string, unknown>).currentValue
    : value
  if (typeof candidate === 'number' && Number.isFinite(candidate)) return candidate
  if (typeof candidate !== 'string') return null
  const normalized = Number(candidate.replace(/\./g, '').replace(',', '.'))
  return Number.isFinite(normalized) ? normalized : null
}

function buildGuidanceSheet(input: MunicipalTechnicalReportWorkbookInput) {
  const columns = 4
  const identityRows: Row[] = [
    [textCell('Município', { ...borderStyle, fontWeight: 'bold' }), textCell(input.municipalityName, borderStyle), textCell('Código IBGE', { ...borderStyle, fontWeight: 'bold' }), textCell(input.municipalityId || 'Não informado', borderStyle)],
    [textCell('População', { ...borderStyle, fontWeight: 'bold' }), integerCell(formatPopulation(input.municipalityPopulation), borderStyle), textCell('Data de geração', { ...borderStyle, fontWeight: 'bold' }), textCell(input.emissionDate, borderStyle)],
    [textCell('Ano-base principal', { ...borderStyle, fontWeight: 'bold' }), integerCell(input.overview?.reference.year, borderStyle), textCell('Base territorial principal', { ...borderStyle, fontWeight: 'bold' }), textCell(input.overview?.universe.locationLabel ?? 'Conforme cada fonte', borderStyle)],
  ]
  const guidance = [
    ['Como usar', 'Use a aba Acompanhamento como matriz de trabalho. Filtre por seção ou indicador e preencha as colunas amarelas com a meta municipal, o prazo, o responsável, a periodicidade e as observações da gestão.'],
    ['Percentuais', 'Os percentuais são gravados como valores numéricos do Excel, com formatação percentual. Isso permite médias, diferenças e gráficos sem conversão manual.'],
    ['Zero', 'Zero é mantido como valor somente quando a base ou o contrato o publica como resultado. Não deve ser confundido com ausência de informação.'],
    ['Célula vazia', 'Célula analítica vazia significa informação indisponível ou não aplicável. Consulte a coluna Estado do dado ou Disponibilidade antes de usar o valor.'],
    ['Referências do PNE', 'São referências nacionais para subsidiar o acompanhamento. Elas não substituem as metas próprias do Plano Municipal de Educação.'],
    ['Proteção de dados', 'O arquivo contém somente agregados municipais e metadados públicos. Não há registros individuais de estudantes, docentes ou escolas.'],
  ]
  const sheetGuide = [
    ['Acompanhamento', 'Matriz consolidada com colunas editáveis para a gestão municipal.'],
    ['Referências PNE', 'Resultados atuais, referências nacionais, direção desejável, situação e fontes.'],
    ['Matrículas por rede', 'Matrículas e participação por etapa e dependência administrativa.'],
    ['Rendimento escolar', 'Aprovação, reprovação e abandono por etapa.'],
    ['Série histórica', 'Valores de 2015 e 2025 e variação do período.'],
    ['Infraestrutura', 'Numerador, denominador, percentual, faltantes e recortes do contrato canônico.'],
    ['Educação Especial', 'Educação Especial, AEE e Educação Bilíngue de Surdos por recorte.'],
    ['Educação Superior', 'Séries e recortes municipais de graduação.'],
    ['Fontes e metodologia', 'Inventário de fontes, períodos, links e notas metodológicas.'],
  ]
  return {
    sheet: 'Orientações',
    data: [
      ...titleRows(
        'Relatório Técnico Municipal — arquivo de acompanhamento',
        'Planilha preparada para apoiar secretarias municipais na organização, no cálculo e na revisão dos seus indicadores educacionais.',
        columns,
      ),
      ...identityRows,
      [textCell('Orientações de uso', {
        backgroundColor: COLORS.paleGreen,
        textColor: COLORS.green,
        fontWeight: 'bold',
        columnSpan: columns,
      }), null, null, null],
      ...guidance.map(([title, description]): Row => [
        textCell(title, { ...borderStyle, fontWeight: 'bold' }),
        textCell(description, { ...borderStyle, columnSpan: 3 }),
        null,
        null,
      ]),
      [textCell('Conteúdo das abas', {
        backgroundColor: COLORS.paleGreen,
        textColor: COLORS.green,
        fontWeight: 'bold',
        columnSpan: columns,
      }), null, null, null],
      ...sheetGuide.map(([sheet, description]): Row => [
        textCell(sheet, { ...borderStyle, fontWeight: 'bold' }),
        textCell(description, { ...borderStyle, columnSpan: 3 }),
        null,
        null,
      ]),
    ],
    columns: [{ width: 24 }, { width: 52 }, { width: 24 }, { width: 42 }],
    stickyRowsCount: 2,
    showGridLines: false,
    zoomScale: 0.9,
  } satisfies Sheet<Blob>
}

function buildSourcesSheet(input: MunicipalTechnicalReportWorkbookInput) {
  const rows: Row[] = []
  input.overview?.sources.forEach((source) => rows.push([
    textCell('Fonte de dados', borderStyle),
    textCell(source.organization, borderStyle),
    textCell(source.title, borderStyle),
    integerCell(source.referenceYear, borderStyle),
    textCell(source.url ?? '', borderStyle),
    textCell('Educação Básica e rendimento escolar.', borderStyle),
  ]))
  input.pmeDiagnostic?.sources.forEach((source) => rows.push([
    textCell('Fonte de dados', borderStyle),
    textCell(source.organization ?? '', borderStyle),
    textCell(source.publicTitle, borderStyle),
    textCell(source.period ?? '', borderStyle),
    textCell(source.officialUrl ?? '', borderStyle),
    textCell('Fonte declarada no diagnóstico público do PNE 2026–2036.', borderStyle),
  ]))
  input.higherEducation?.effectiveSources.forEach((source) => rows.push([
    textCell('Fonte de dados', borderStyle),
    textCell('INEP', borderStyle),
    textCell('Sinopse Estatística da Educação Superior', borderStyle),
    integerCell(source.year, borderStyle),
    textCell('', borderStyle),
    textCell('Graduação; referência territorial conforme o indicador ou recorte.', borderStyle),
  ]))
  input.specialEducation?.sources.forEach((source) => rows.push([
    textCell('Fonte de dados', borderStyle),
    textCell(source.provider, borderStyle),
    textCell(source.survey, borderStyle),
    textCell('', borderStyle),
    textCell(source.url ?? '', borderStyle),
    textCell('Educação Especial, AEE e Educação Bilíngue de Surdos.', borderStyle),
  ]))
  if (input.schoolInfrastructure) rows.push([
    textCell('Fonte de dados', borderStyle),
    textCell('INEP', borderStyle),
    textCell(SCHOOL_INFRASTRUCTURE_SOURCE, borderStyle),
    integerCell(input.schoolInfrastructure.referenceYear, borderStyle),
    textCell('', borderStyle),
    textCell(SCHOOL_INFRASTRUCTURE_METHODOLOGY, borderStyle),
  ])
  const methodNotes = [
    ...MUNICIPAL_REPORT_METHODOLOGY_NOTES,
    ...(input.overview?.methodology ?? []),
    ...(input.higherEducation?.methodNotes ?? []),
  ]
  ;[...new Set(methodNotes)].forEach((note) => rows.push([
    textCell('Nota metodológica', borderStyle),
    textCell('', borderStyle),
    textCell('Metodologia do Relatório Técnico Municipal', borderStyle),
    textCell('', borderStyle),
    textCell('', borderStyle),
    textCell(note, borderStyle),
  ]))
  return tableSheet(
    'Fontes e metodologia',
    'Fontes, períodos e metodologia',
    'Use esta aba para documentar a origem dos indicadores e conferir as limitações antes de publicar metas ou comparações.',
    ['Tipo', 'Organização', 'Fonte ou documento', 'Período ou ano', 'Link oficial', 'Aplicação ou nota metodológica'],
    rows,
    [22, 24, 46, 18, 46, 68],
    3,
  )
}

function sanitizeFileSegment(value: string) {
  return value
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLocaleLowerCase('pt-BR')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 80)
}

export function buildMunicipalTechnicalReportFileName(
  input: MunicipalTechnicalReportWorkbookInput,
) {
  const municipality = sanitizeFileSegment(
    input.municipalitySlug
      || input.municipalityName
      || input.municipalityId
      || 'municipio',
  ) || sanitizeFileSegment(input.municipalityId) || 'municipio'
  const referenceYear = input.overview?.reference.year
    ?? input.schoolInfrastructure?.referenceYear
    ?? input.higherEducation?.latestMunicipalUsableYear
    ?? 'atual'
  return `relatorio-tecnico-municipal-${municipality}-${referenceYear}.xlsx`
}

export function buildMunicipalTechnicalReportWorkbook(
  input: MunicipalTechnicalReportWorkbookInput,
): MunicipalTechnicalReportWorkbook {
  return {
    fileName: buildMunicipalTechnicalReportFileName(input),
    sheets: [
      buildGuidanceSheet(input),
      buildTrackingSheet(input),
      buildPneReferenceSheet(input),
      buildNetworkSheet(input),
      buildPerformanceSheet(input),
      buildHistoricalSheet(input),
      buildInfrastructureSheet(input),
      buildSpecialEducationSheet(input),
      buildHigherEducationSheet(input),
      buildSourcesSheet(input),
    ],
  }
}
