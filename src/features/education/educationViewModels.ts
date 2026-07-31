/* eslint-disable @typescript-eslint/ban-ts-comment */
// @ts-nocheck
// Raw Education payload adapters remain incrementally typed; exported page and
// component boundaries use explicit domain contracts.
import {
  EDUCATION_COMPLEMENTARY_INDICATOR_CATALOG,
  EDUCATION_SECTION_GROUPS,
  SCHOOL_INFRASTRUCTURE_BASIC_INDICATOR_ORDER,
  getEducationIndicatorCatalogItem,
} from '../../data/educationIndicatorCatalog.js'
import { PNE_CONTEXT_PROXY_INDICATOR_KEYS } from '../../utils/pneDisplayRules.js'
import {
  formatSchoolInfrastructurePercentage,
  formatSchoolInfrastructureQuantity,
  SCHOOL_INFRASTRUCTURE_CONTRACT_VERSION,
  SCHOOL_INFRASTRUCTURE_INDICATOR_ORDER,
  SCHOOL_INFRASTRUCTURE_PUBLIC_COPY,
  SCHOOL_INFRASTRUCTURE_SOURCE,
  selectSchoolInfrastructureResult,
} from '../../data/schoolInfrastructureContract.js'
import { chartSeriesColor } from '../../utils/chartVisuals.js'
import {
  depLabel,
  etapaLabel,
  formatNumber,
  formatPercent,
  formatRatio,
  formatValue,
  isMissing,
  locLabel,
  modLabel,
  normalizeYearSeries,
} from '../../utils/educationFormatters.js'
import { normalizeEducationIndicatorLabel } from './educationFormatters.js'
import type { EducationSectionKey } from './educationTypes'

export interface EducationPageViewModel {
  contextScope: string
  isDemandSection: boolean
  isMethodologySection: boolean
  isOverviewSection: boolean
}

function formatEducationIndicatorCount(count: number): string {
  return `${count} indicador${count === 1 ? '' : 'es'}`
}

export function buildEducationPageViewModel({
  indicatorCount,
  selectedSectionKey,
  sectionKeys,
}: {
  indicatorCount: number
  selectedSectionKey: EducationSectionKey
  sectionKeys: { demand: EducationSectionKey; methodology: EducationSectionKey; overview: EducationSectionKey }
}): EducationPageViewModel {
  const isOverviewSection = selectedSectionKey === sectionKeys.overview
  const isDemandSection = selectedSectionKey === sectionKeys.demand
  const isMethodologySection = selectedSectionKey === sectionKeys.methodology
  const contextScope = indicatorCount > 0
    ? formatEducationIndicatorCount(indicatorCount)
    : isOverviewSection
      ? 'Síntese municipal'
      : isDemandSection
        ? 'Cenários de atendimento escolar'
        : 'Fontes e critérios'

  return { contextScope, isDemandSection, isMethodologySection, isOverviewSection }
}

export function buildProjectionHistory(projection) {
  if (!projection) return []

  return (projection.historical_years ?? [])
    .map((year, index) => ({
      year,
      value: projection.historical_percent?.[index],
      population: projection.historical_population?.[index],
    }))
    .filter((point) => Number.isFinite(Number(point.year)) && Number.isFinite(Number(point.value)))
}

export function getLatestProjectionObservation(projection) {
  const history = buildProjectionHistory(projection)

  for (let index = history.length - 1; index >= 0; index -= 1) {
    const point = history[index]
    if (point.value != null && Number.isFinite(Number(point.value))) return point
  }

  return null
}

const EM = '\u2014'

const FILTER_KEYS = {
  todos: 'todos',
  infantil: 'educacao_infantil',
  fundamental: 'ensino_fundamental',
  medio: 'ensino_medio',
  eja: 'eja',
  profissional: 'educacao_profissional',
}

const CATEGORY_LABELS = {
  [FILTER_KEYS.todos]: 'Geral',
  [FILTER_KEYS.infantil]: 'Educação Infantil',
  [FILTER_KEYS.fundamental]: 'Ensino Fundamental',
  [FILTER_KEYS.medio]: 'Ensino Médio',
  [FILTER_KEYS.eja]: 'Educação de Jovens e Adultos',
  [FILTER_KEYS.profissional]: 'Educação Profissional e Tecnológica',
}

const DEPENDENCY_COLORS = {
  publica: '#0f766e',
  federal: '#2563eb',
  estadual: '#16a34a',
  municipal: '#f59e0b',
  privada: '#7c3aed',
}

const LOCATION_COLORS = {
  urbana: '#16713a',
  rural: '#2563eb',
}

const STAGE_FILTER_ORDER = ['total', 'infantil', 'fundamental', 'fundamental_anos_iniciais', 'fundamental_anos_finais', 'medio', 'eja', 'profissional']
const TOTAL_ENROLLMENT_STAGE_KEYS = ['infantil', 'fundamental', 'medio', 'eja', 'profissional']
const ALUNOS_TURMA_STAGE_ORDER = ['infantil', 'fundamental', 'medio']
const ATU_TOTAL_SERIE_BY_STAGE = {
  infantil: 'infantil_total',
  fundamental: 'fundamental_total',
  medio: 'medio_total',
}
const ALUNOS_TURMA_SERIE_LABELS = {
  infantil_total: 'Total — Educação Infantil',
  creche: 'Creche',
  pre_escola: 'Pré-Escola',
  fundamental_total: 'Total — Ensino Fundamental',
  fundamental_anos_iniciais: 'Anos Iniciais',
  fundamental_anos_finais: 'Anos Finais',
  fundamental_1_ano: '1º ano',
  fundamental_2_ano: '2º ano',
  fundamental_3_ano: '3º ano',
  fundamental_4_ano: '4º ano',
  fundamental_5_ano: '5º ano',
  fundamental_6_ano: '6º ano',
  fundamental_7_ano: '7º ano',
  fundamental_8_ano: '8º ano',
  fundamental_9_ano: '9º ano',
  fundamental_multietapa: 'Multietapa, multi ou correção de fluxo',
  medio_total: 'Total — Ensino Médio',
  medio_1_serie: '1ª série',
  medio_2_serie: '2ª série',
  medio_3_serie: '3ª série',
  medio_4_serie: '4ª série',
  medio_nao_seriado: 'Não-seriado',
}
const FUNDAMENTAL_FAIXA_STAGES = ['fundamental_anos_iniciais', 'fundamental_anos_finais']
const EJA_VALID_AGE_RANGES = [
  'Até 14 anos',
  '15 a 17 anos',
  '18 a 19 anos',
  '20 a 24 anos',
  '25 a 29 anos',
  '30 a 34 anos',
  '35 a 39 anos',
  '40 anos ou mais',
]
const CATEGORY_COMPARISON_COLORS = ['#0f766e', '#2563eb', '#f59e0b', '#7c3aed', '#0891b2', '#db2777', '#65a30d', '#9333ea']
const COR_RACA_ORDER = ['Branca', 'Parda', 'Preta', 'Amarela', 'Indígena', 'Não Declarada']

const PANORAMA_THEME_KEYS = {
  complementaresPne: 'pne_complementares',
  matriculas: 'matriculas',
  escolasSistemaS: 'escolasSistemaS',
}


export function buildPneComplementaryTheme({ indicadores, results, rede }) {
  const schoolInfrastructure = rede?.infraestrutura?.contractVersion === SCHOOL_INFRASTRUCTURE_CONTRACT_VERSION
    ? rede.infraestrutura
    : null
  if (!results && !schoolInfrastructure) return null

  const itemByKey = buildPneCatalogItemMap(indicadores)
  const groupByIndicatorKey = new Map(
    Object.values(EDUCATION_SECTION_GROUPS)
      .flat()
      .flatMap((group) => group.indicatorKeys.map((indicatorKey) => [indicatorKey, group])),
  )
  const items = EDUCATION_COMPLEMENTARY_INDICATOR_CATALOG.map((catalogEntry) => {
      const indicatorKey = catalogEntry.key
      const group = groupByIndicatorKey.get(indicatorKey)
      const result = results?.[indicatorKey]
      const catalogItem = itemByKey.get(indicatorKey)
      const isSchoolInfrastructureIndicator = SCHOOL_INFRASTRUCTURE_INDICATOR_ORDER.includes(indicatorKey)
      const schoolInfrastructureResult = isSchoolInfrastructureIndicator && schoolInfrastructure
        ? selectSchoolInfrastructureResult(schoolInfrastructure, indicatorKey)
        : null

      if (indicatorKey === 'infraestrutura-basica' && schoolInfrastructure) {
        const dimensions = SCHOOL_INFRASTRUCTURE_BASIC_INDICATOR_ORDER.map((key) => ({
          key,
          label: SCHOOL_INFRASTRUCTURE_PUBLIC_COPY[key].shortLabel,
          result: selectSchoolInfrastructureResult(schoolInfrastructure, key),
        }))
        return createIndicator({
          key: indicatorKey,
          label: 'Infraestrutura básica e espaços escolares',
          description: 'Disponibilidade de serviços básicos e espaços escolares em 2025.',
          themeKey: PANORAMA_THEME_KEYS.complementaresPne,
          themeLabel: group?.label ?? 'Infraestrutura básica e espaços escolares',
          themeShortLabel: 'Infraestrutura básica',
          categoryLabel: group?.label ?? 'Infraestrutura básica e espaços escolares',
          categories: [FILTER_KEYS.todos],
          series: [],
          currentValue: null,
          currentYear: schoolInfrastructure.referenceYear,
          formatType: 'percent',
          mainCutLabel: 'Total',
          groupKey: catalogEntry.groupKey,
          pneComplementaryGroupKey: catalogEntry.groupKey,
          schoolInfrastructure,
          schoolInfrastructureDimensions: dimensions,
          cardVariant: 'school-infrastructure-composite',
          source: SCHOOL_INFRASTRUCTURE_SOURCE,
          searchText: [
            'infraestrutura básica espaços escolares',
            ...dimensions.map(({ label }) => label),
          ].join(' '),
          statusTone: 'info',
        })
      }

      if (isSchoolInfrastructureIndicator && schoolInfrastructure) {
        if (!schoolInfrastructureResult) return null
        const isInternet = indicatorKey === 'internet'
        const historicalSeries = isInternet && hasPneComplementaryResult(result)
          ? normalizeYearSeries(result.series).filter((point) => point.ano < schoolInfrastructure.referenceYear)
          : []
        const series = schoolInfrastructureResult.percentage == null
          ? historicalSeries
          : [...historicalSeries, {
              ano: schoolInfrastructure.referenceYear,
              valor: schoolInfrastructureResult.percentage,
            }]
        const publicCopy = SCHOOL_INFRASTRUCTURE_PUBLIC_COPY[indicatorKey]
        const indicator = createIndicator({
          key: indicatorKey,
          label: publicCopy.label,
          description: publicCopy.description,
          themeKey: PANORAMA_THEME_KEYS.complementaresPne,
          themeLabel: group?.label ?? catalogEntry.section,
          themeShortLabel: group?.label ?? 'Infraestrutura',
          categoryLabel: group?.label ?? catalogEntry.section,
          categories: [FILTER_KEYS.todos],
          series: isInternet ? series : [],
          currentValue: schoolInfrastructureResult.percentage,
          currentYear: schoolInfrastructure.referenceYear,
          formatType: 'percent',
          mainCutLabel: 'Total',
          groupKey: catalogEntry.groupKey,
          pneComplementaryGroupKey: catalogEntry.groupKey,
          schoolInfrastructure,
          schoolInfrastructureKey: indicatorKey,
          schoolInfrastructureResult,
          snapshotOnly: !isInternet,
          source: SCHOOL_INFRASTRUCTURE_SOURCE,
          cardReading: `${formatSchoolInfrastructureQuantity(schoolInfrastructureResult)} escolas`,
          quickReading: `Situação em ${schoolInfrastructure.referenceYear}: ${formatSchoolInfrastructurePercentage(schoolInfrastructureResult)}.`,
          statusDetail: `Retrato do Censo Escolar em ${schoolInfrastructure.referenceYear}.`,
          statusLabel: `Situação em ${schoolInfrastructure.referenceYear}`,
          statusTone: 'info',
        })
        return {
          ...indicator,
          currentValue: schoolInfrastructureResult.percentage,
          currentDisplay: formatSchoolInfrastructurePercentage(schoolInfrastructureResult),
        }
      }

      if (!PNE_CONTEXT_PROXY_INDICATOR_KEYS.has(indicatorKey)) return null
      if (!hasPneComplementaryResult(result)) return null

      const formatType = inferPneComplementaryFormatType(catalogItem, result)
      const formatValueForType = getFormatter(formatType)
      const currentDisplay = result.display?.end_value ?? formatValueForType(result.end_value)
      const currentYear = result.end_year ?? getLatestSeriesYear(result.series)
      const trendStatus = getContextTrendStatus(result.series, result.end_value, currentYear)

      return createIndicator({
        key: indicatorKey,
        label: catalogItem?.label ?? catalogEntry.label ?? INFRA_METRIC_LABELS[indicatorKey] ?? indicatorKey,
        description: catalogItem?.desc ?? catalogEntry.description ?? 'Indicador contextual relacionado ao PNE.',
        themeKey: PANORAMA_THEME_KEYS.complementaresPne,
        themeLabel: group?.label ?? catalogEntry.section,
        themeShortLabel: group?.label ?? 'Indicador contextual',
        categoryLabel: group?.label ?? catalogEntry.section,
        categories: [FILTER_KEYS.todos],
        series: result.series ?? [],
        currentValue: result.end_value,
        currentYear,
        formatType,
        mainCutLabel: group?.label ?? catalogEntry.section,
        explore: buildInfrastructureMetricExplore(rede, indicatorKey, formatValueForType),
        groupKey: catalogEntry.groupKey,
        pneComplementaryGroupKey: catalogEntry.groupKey,
        quickReading: `Indicador contextual do PNE: ${currentDisplay} em ${currentYear ?? 'ano indisponível'}. Não representa cumprimento da meta legal.`,
        searchText: [
          indicatorKey,
          group?.label,
          catalogItem?.sub,
          catalogItem?.categoryLabel,
          'contexto proxy complementar PNE',
        ].filter(Boolean).join(' '),
        statusDetail: trendStatus.detail,
        statusLabel: trendStatus.label,
        statusTone: trendStatus.tone,
      })
  }).filter(Boolean)

  if (!items.length) return null

  return {
    key: PANORAMA_THEME_KEYS.complementaresPne,
    label: 'Contexto complementar',
    shortLabel: 'Contexto complementar',
    items,
  }
}

function buildPneCatalogItemMap(indicadores) {
  const categories = indicadores?.cycles?.pne_2026_2036?.categories ?? []
  const entries = categories.flatMap((category) =>
    (category.items ?? []).map((item) => [
      item.key,
      {
        ...item,
        categoryLabel: category.label,
      },
    ]),
  )

  return new Map(entries)
}

function hasPneComplementaryResult(result) {
  if (!result || result.available === false) return false
  if (Number.isFinite(Number(result.end_value))) return true
  return (result.series ?? []).some((point) => Number.isFinite(Number(point?.valor)))
}

function inferPneComplementaryFormatType(catalogItem, result) {
  const valueMode = catalogItem?.value_mode ?? result?.value_mode
  if (valueMode === 'count' || valueMode === 'absolute') return 'number'
  if (valueMode === 'ratio_percent' || valueMode === 'percent') return 'percent'
  if (String(result?.display?.end_value ?? '').includes('%')) return 'percent'
  return 'number'
}

function getLatestSeriesYear(series = []) {
  return normalizeYearSeries(series).at(-1)?.ano ?? null
}

function getContextTrendStatus(series, currentValue, currentYear) {
  const normalizedSeries = normalizeYearSeries(series)
  const initial = normalizedSeries[0]
  const latestValue = isMissing(currentValue) ? normalizedSeries.at(-1)?.valor : currentValue

  if (isMissing(latestValue)) {
    return { detail: 'Último dado indisponível', label: 'Sem dados', tone: 'muted' }
  }
  if (normalizedSeries.length < 2 || isMissing(initial?.valor)) {
    return { detail: 'Sem comparação temporal', label: 'Série disponível', tone: 'info' }
  }

  const endYear = currentYear ?? normalizedSeries.at(-1)?.ano
  const period = initial.ano && endYear ? ` entre ${initial.ano} e ${endYear}` : ' no período'
  const difference = Number(latestValue) - Number(initial.valor)

  if (difference > 0) return { detail: `Aumento${period}`, label: 'Crescimento', tone: 'success' }
  if (difference < 0) return { detail: `Redução${period}`, label: 'Redução', tone: 'warning' }
  return { detail: `Sem variação${period}`, label: 'Estabilidade', tone: 'muted' }
}

function signedOverviewValue(value, maximumFractionDigits = 1) {
  const numericValue = Number(value)
  if (!Number.isFinite(numericValue)) return null
  const formatted = Math.abs(numericValue).toLocaleString('pt-BR', {
    minimumFractionDigits: maximumFractionDigits,
    maximumFractionDigits,
  })
  if (numericValue > 0) return `+${formatted}`
  if (numericValue < 0) return `−${formatted}`
  return formatted
}

function overviewSeriesContext(series, valueKey, currentYear) {
  const points = normalizeYearSeries(series, valueKey)
    .map((point) => ({ year: Number(point.ano), value: Number(point[valueKey]) }))
    .filter((point) => Number.isFinite(point.year) && Number.isFinite(point.value))

  if (!points.length) return { points, current: null, previous: null }
  const currentIndex = currentYear == null
    ? points.length - 1
    : points.findIndex((point) => point.year === Number(currentYear))
  if (currentIndex < 0) return { points, current: null, previous: null }
  return {
    points,
    current: points[currentIndex],
    previous: currentIndex > 0 ? points[currentIndex - 1] : null,
  }
}

function overviewComparisonText(card, current, previous) {
  const difference = current.value - previous.value

  if (card.comparison === 'percentage') {
    if (previous.value === 0) return `Sem variação percentual calculável sobre ${previous.year}`
    const percentage = signedOverviewValue((difference / Math.abs(previous.value)) * 100)
    return percentage ? `${percentage}% em relação a ${previous.year} · ${formatNumber(previous.value)}` : null
  }

  if (card.comparison === 'count') {
    if (difference === 0) return `Mesmo total de ${card.countLabel}s de ${previous.year}`
    const amount = formatNumber(Math.abs(difference))
    const direction = difference > 0 ? 'a mais' : 'a menos'
    return `${amount} ${card.countLabel}${Math.abs(difference) === 1 ? '' : 's'} ${direction} que em ${previous.year}`
  }

  if (card.comparison === 'ratio') {
    if (difference === 0) return `Sem diferença na média desde ${previous.year}`
    const ratio = signedOverviewValue(difference)
    return ratio ? `${ratio} aluno por turma desde ${previous.year}` : null
  }

  if (card.comparison === 'percentage-points') {
    const points = signedOverviewValue(difference)
    return points ? `${points} p.p. em relação a ${previous.year} · ${formatPercent(previous.value)}` : null
  }

  if (card.comparison === 'score') {
    if (difference === 0) return `Mesmo resultado da edição de ${previous.year}`
    const score = signedOverviewValue(difference)
    return score ? `${score} ponto desde ${previous.year}` : null
  }

  return null
}

function buildOverviewInsight(card) {
  const numericValue = Number(card.currentValue)
  const hasCurrentValue = !isMissing(card.currentValue) && Number.isFinite(numericValue)
  const context = overviewSeriesContext(card.series, card.valueKey, card.year)
  const current = context.current

  if (!hasCurrentValue) {
    return card.year ? `Sem valor publicado em ${card.year}` : 'Série sem valor publicado'
  }

  if (card.zeroMessage && numericValue === 0) return card.zeroMessage(card.year)

  if (current && context.previous) {
    const comparison = overviewComparisonText(card, current, context.previous)
    if (comparison) return comparison
  }

  if (typeof card.composition === 'function') {
    const composition = card.composition()
    if (composition) return composition
  }

  if (context.points.length === 1) {
    return card.comparison === 'score'
      ? `Indicador publicado apenas em ${context.points[0].year}`
      : `Série disponível somente para ${context.points[0].year}`
  }

  return 'Sem valor comparável no período anterior'
}

function buildEducationOverviewCards({ alunosTurma, aprend, fluxo, mat, oferta, preferredIdeb, rede, turmas }) {
  const matResumo = mat.resumo_ultimo_ano ?? {}
  const redeResumo = rede.resumo_ultimo_ano ?? {}
  const alunosTurmaResumo = alunosTurma.resumo_ultimo_ano ?? {}
  const turmasResumo = turmas.resumo_ultimo_ano ?? {}
  const fluxoResumo = fluxo.resumo_ultimo_ano ?? {}
  const ofertaResumo = oferta.resumo_ultimo_ano ?? {}
  const preferredIdebSeries = preferredIdeb?.etapa ? aprend.series?.ideb?.[preferredIdeb.etapa] : []

  const cards = [
    { key: 'matriculas', icon: 'enrollment', label: 'Matrículas', currentValue: matResumo.total_matriculas, value: formatNumber(matResumo.total_matriculas), year: mat.ultimo_ano, series: mat.series?.total, valueKey: 'valor', comparison: 'percentage' },
    { key: 'escolas', icon: 'school', label: 'Escolas', currentValue: redeResumo.total_escolas, value: formatNumber(redeResumo.total_escolas), year: rede.ultimo_ano, series: rede.series?.total, valueKey: 'valor', comparison: 'count', countLabel: 'escola', composition: () => {
      const publicCount = Number(redeResumo.escolas_publica)
      const privateCount = Number(redeResumo.escolas_privada)
      if (!Number.isFinite(publicCount) || !Number.isFinite(privateCount)) return null
      return `${formatNumber(publicCount)} públicas · ${formatNumber(privateCount)} privadas`
    } },
    { key: 'docentes', icon: 'teacher', label: 'Docentes', currentValue: turmasResumo.docentes, value: formatNumber(turmasResumo.docentes), year: turmas.ultimo_ano, series: turmas.series?.total, valueKey: 'docentes', comparison: 'count', countLabel: 'docente' },
    { key: 'alunos-turma', icon: 'classroom', label: 'Alunos/turma — ensino fundamental', currentValue: alunosTurmaResumo.alunos_por_turma_fundamental, value: formatRatio(alunosTurmaResumo.alunos_por_turma_fundamental), year: alunosTurma.ultimo_ano, series: alunosTurma.series?.por_etapa?.fundamental, valueKey: 'alunos_por_turma', comparison: 'ratio' },
    { key: 'aprovacao', icon: 'approval', label: 'Aprovação', currentValue: fluxoResumo.taxa_aprovacao, value: formatPercent(fluxoResumo.taxa_aprovacao), year: fluxo.ultimo_ano, series: fluxo.series?.por_etapa?.fundamental, valueKey: 'taxa_aprovacao', comparison: 'percentage-points' },
    { key: 'ideb', icon: 'ideb', label: 'IDEB', currentValue: preferredIdeb?.ideb, value: preferredIdeb ? formatValue(preferredIdeb.ideb) : EM, year: preferredIdeb?.ano, series: preferredIdebSeries, valueKey: 'ideb', comparison: 'score' },
    { key: 'matriculas-tecnicas', icon: 'technical', label: 'Matrículas técnicas', currentValue: ofertaResumo.total_matriculas_tecnicas, value: formatNumber(ofertaResumo.total_matriculas_tecnicas), year: oferta.ultimo_ano, series: oferta.series?.total, valueKey: 'valor', comparison: 'count', countLabel: 'matrícula', zeroMessage: (year) => year ? `Sem matrículas registradas em ${year}` : 'Série publicada com valor zero' },
  ]

  return cards.map((card) => ({ ...card, detail: buildOverviewInsight(card) }))
}

export function buildEducationModel(blocos) {
  const mat = blocos.matriculas ?? {}
  const rede = blocos.rede_escolar ?? {}
  const alunosTurma = blocos.alunos_turma ?? {}
  const turmas = blocos.turmas_docentes ?? {}
  const fluxo = blocos.fluxo ?? {}
  const aprend = blocos.aprendizagem ?? {}
  const oferta = blocos.oferta_tecnica ?? {}
  const educacaoIndigena = blocos.educacao_indigena ?? {}
  const aprendResumo = aprend.resumo_ultimo_ano ?? {}
  const preferredIdeb = getPreferredIdeb(aprendResumo)

  const items = [
    ...buildMatriculasIndicators(mat),
    ...buildRedeIndicators(rede),
    ...buildAlunosTurmaIndicators(alunosTurma),
    ...buildDocentesIndicators(turmas),
    ...buildFluxoIndicators(fluxo),
    ...buildAprendizagemIndicators(aprend),
    ...buildOfertaIndicators(oferta),
    ...buildIndigenousEducationIndicators(educacaoIndigena),
  ]

  const themes = [
    makeTheme('matriculas', 'Matrículas e atendimento', 'Matrículas', items),
    makeTheme('rede', 'Escolas', 'Escolas', items),
    makeTheme('turmas', 'Alunos por turma', 'Alunos por turma', items),
    makeTheme('docentes', 'Docentes', 'Docentes', items),
    makeTheme('fluxo', 'Fluxo escolar', 'Fluxo', items),
    makeTheme('aprendizagem', 'Aprendizagem', 'Aprendizagem', items),
    makeTheme('oferta', 'Matrículas técnicas · Sinopse Estatística', 'Sinopse Estatística', items),
    makeTheme('educacao_indigena', 'Educação indígena', 'Educação indígena', items),
  ]

  return {
    overview: buildEducationOverviewCards({ alunosTurma, aprend, fluxo, mat, oferta, preferredIdeb, rede, turmas }),
    items,
    themes,
  }
}

function makeTheme(key, label, shortLabel, items) {
  const themeItems = items.filter((item) => item.themeKey === key)
  return { key, label, shortLabel, items: themeItems }
}

function buildMatriculasIndicators(mat) {
  const series = mat.series ?? {}
  const resumo = mat.resumo_ultimo_ano ?? {}
  const byEtapa = resumo.por_etapa ?? {}
  const latestYear = mat.ultimo_ano

  return [
    createIndicator({ key: 'mat-total', label: 'Total de matrículas', description: 'Total oficial de matrículas da Educação Básica divulgado pelo Censo Escolar; não é recalculado pela soma das etapas e modalidades exibidas.', themeKey: 'matriculas', themeLabel: 'Matrículas e atendimento', themeShortLabel: 'Matrículas', categories: [FILTER_KEYS.todos], isGeral: true, series: normalizeYearSeries(series.total), currentValue: resumo.total_matriculas, currentYear: latestYear, formatType: 'number', mainCutLabel: 'Total do município', explore: buildMatriculasExplore(mat, { cutKey: 'total', cutLabel: 'Total do município' }), stageFilterOptions: buildMatriculasStageOptions(mat) }),
    createIndicator({ key: 'mat-infantil', label: 'Matrículas na educação infantil', description: 'Matrículas registradas na educação infantil.', themeKey: 'matriculas', themeLabel: 'Matrículas e atendimento', themeShortLabel: 'Matrículas', categories: [FILTER_KEYS.infantil], stageLabel: 'Educação Infantil', series: normalizeYearSeries(series.por_etapa?.infantil), currentValue: byEtapa.infantil, currentYear: latestYear, formatType: 'number', mainCutLabel: 'Educação Infantil', explore: buildMatriculasExplore(mat, { cutKey: 'infantil', cutLabel: 'Educação Infantil', stageKey: 'infantil' }) }),
    createIndicator({ key: 'mat-fundamental', label: 'Matrículas no ensino fundamental', description: 'Matrículas registradas no ensino fundamental.', themeKey: 'matriculas', themeLabel: 'Matrículas e atendimento', themeShortLabel: 'Matrículas', categories: [FILTER_KEYS.fundamental], stageLabel: 'Ensino Fundamental', series: normalizeYearSeries(series.por_etapa?.fundamental), currentValue: byEtapa.fundamental, currentYear: latestYear, formatType: 'number', mainCutLabel: 'Ensino Fundamental', explore: buildMatriculasExplore(mat, { cutKey: 'fundamental', cutLabel: 'Ensino Fundamental', stageKey: 'fundamental' }) }),
    createIndicator({ key: 'mat-medio', label: 'Matrículas no ensino médio', description: 'Matrículas registradas no ensino médio.', themeKey: 'matriculas', themeLabel: 'Matrículas e atendimento', themeShortLabel: 'Matrículas', categories: [FILTER_KEYS.medio], stageLabel: 'Ensino Médio', series: normalizeYearSeries(series.por_etapa?.medio), currentValue: byEtapa.medio, currentYear: latestYear, formatType: 'number', mainCutLabel: 'Ensino Médio', explore: buildMatriculasExplore(mat, { cutKey: 'medio', cutLabel: 'Ensino Médio', stageKey: 'medio' }) }),
    createIndicator({ key: 'mat-eja', label: 'Matrículas na EJA', description: 'Matrículas registradas na educação de jovens e adultos.', themeKey: 'matriculas', themeLabel: 'Matrículas e atendimento', themeShortLabel: 'Matrículas', categories: [FILTER_KEYS.eja], stageLabel: 'EJA', series: normalizeYearSeries(series.por_etapa?.eja), currentValue: byEtapa.eja, currentYear: latestYear, formatType: 'number', mainCutLabel: 'EJA', explore: buildMatriculasExplore(mat, { cutKey: 'eja', cutLabel: 'EJA', stageKey: 'eja' }) }),
    createIndicator({ key: 'mat-profissional', label: 'Matrículas na educação profissional — Censo Escolar', description: 'Matrículas registradas na educação profissional/técnica no Censo Escolar, por etapa de ensino.', themeKey: 'matriculas', themeLabel: 'Matrículas e atendimento', themeShortLabel: 'Censo Escolar', categories: [FILTER_KEYS.profissional], stageLabel: 'Educação Profissional', series: normalizeYearSeries(series.por_etapa?.profissional), currentValue: byEtapa.profissional, currentYear: latestYear, formatType: 'number', mainCutLabel: 'Educação Profissional · Censo Escolar', explore: buildMatriculasExplore(mat, { cutKey: 'profissional', cutLabel: 'Educação Profissional', stageKey: 'profissional' }) }),
    createIndicator({ key: 'mat-integral', label: 'Matrículas em tempo integral', description: 'Percentual total de matrículas em tempo integral no município.', themeKey: 'matriculas', themeLabel: 'Matrículas e atendimento', themeShortLabel: 'Matrículas', categories: [FILTER_KEYS.todos], isGeral: true, series: valueSeries(series.integral, 'percentual'), currentValue: resumo.percentual_integral, currentYear: latestYear, formatType: 'percent', mainCutLabel: 'Tempo integral no total do município', explore: buildMatriculasIntegralExplore(mat) }),
    createIndicator({ key: 'mat-rural', label: 'Matrículas em zona rural', description: 'Matrículas vinculadas à localização rural.', themeKey: 'matriculas', themeLabel: 'Matrículas e atendimento', themeShortLabel: 'Matrículas', categories: [FILTER_KEYS.todos], isGeral: true, series: normalizeYearSeries(series.por_localizacao?.rural), currentValue: resumo.matriculas_rural, currentYear: latestYear, formatType: 'number', mainCutLabel: 'Zona rural', explore: buildMatriculasExplore(mat, { cutKey: 'rural', cutLabel: 'Zona rural', locationKey: 'rural' }) }),
    createIndicator({ key: 'mat-publica', label: 'Matrículas na rede pública', description: 'Matrículas na rede pública municipal, estadual e federal.', themeKey: 'matriculas', themeLabel: 'Matrículas e atendimento', themeShortLabel: 'Matrículas', categories: [FILTER_KEYS.todos], isGeral: true, series: normalizeYearSeries(series.por_dependencia?.publica), currentValue: resumo.matriculas_publica, currentYear: latestYear, formatType: 'number', mainCutLabel: 'Rede pública', explore: buildMatriculasExplore(mat, { cutKey: 'publica', cutLabel: 'Rede pública', dependencyKey: 'publica' }) }),
    createIndicator({ key: 'mat-privada', label: 'Matrículas na rede privada', description: 'Matrículas na rede privada.', themeKey: 'matriculas', themeLabel: 'Matrículas e atendimento', themeShortLabel: 'Matrículas', categories: [FILTER_KEYS.todos], isGeral: true, series: normalizeYearSeries(series.por_dependencia?.privada), currentValue: resumo.matriculas_privada, currentYear: latestYear, formatType: 'number', mainCutLabel: 'Rede privada', explore: buildMatriculasExplore(mat, { cutKey: 'privada', cutLabel: 'Rede privada', dependencyKey: 'privada' }) }),
  ]
}

function buildRedeIndicators(rede) {
  const series = rede.series ?? {}
  const resumo = rede.resumo_ultimo_ano ?? {}
  const porEtapa = resumo.por_etapa ?? {}
  const latestYear = rede.ultimo_ano
  const infra = rede.infraestrutura ?? {}
  const schoolInfrastructure = infra.contractVersion === SCHOOL_INFRASTRUCTURE_CONTRACT_VERSION ? infra : null
  const canonicalInternet = schoolInfrastructure
    ? selectSchoolInfrastructureResult(schoolInfrastructure, 'internet')
    : null
  const infraGroups = Object.values(infra.grupos ?? {})
  const infraDimensionCount = infraGroups.reduce((total, group) => total + (group.metricas?.length ?? 0), 0)
  const infraLatestYear = schoolInfrastructure?.referenceYear ?? infra.ultimo_ano ?? latestYear
  const stageOrder = ['infantil', 'fundamental', 'medio', 'eja', 'profissional']
  const base = { themeKey: 'rede', themeLabel: 'Escolas', themeShortLabel: 'Escolas', categories: [FILTER_KEYS.todos], isGeral: true, currentYear: latestYear }

  const etapaIndicators = stageOrder.map((stageKey) => createIndicator({
    ...base,
    key: `rede-${stageKey}`,
    label: etapaLabel(stageKey),
    description: `Escolas que ofertam ${etapaLabel(stageKey).toLowerCase()}.`,
    categories: [FILTER_KEYS.todos],
    isGeral: true,
    series: normalizeYearSeries(series.por_etapa?.[stageKey]),
    currentValue: porEtapa[stageKey],
    formatType: 'number',
    mainCutLabel: etapaLabel(stageKey),
    explore: buildRedeExplore(rede, { cutKey: stageKey, cutLabel: etapaLabel(stageKey), stageKey }),
  }))

  return [
    createIndicator({ ...base, key: 'rede-total', label: 'Total de escolas', description: 'Total de escolas registradas no município.', series: normalizeYearSeries(series.total), currentValue: resumo.total_escolas, formatType: 'number', mainCutLabel: 'Total do município', explore: buildRedeExplore(rede, { cutKey: 'total', cutLabel: 'Total do município' }) }),
    ...etapaIndicators,
    createIndicator({
      ...base,
      key: 'rede-infraestrutura',
      label: 'Infraestrutura',
      cardTitle: 'Panorama da infraestrutura escolar',
      cardVariant: 'exploratory',
      description: 'Explore as condições básicas, os espaços escolares, a conectividade e os equipamentos disponíveis nas escolas.',
      series: schoolInfrastructure
        ? [
            ...valueSeries(series.internet, 'perc_internet')
              .filter((point) => point.ano < schoolInfrastructure.referenceYear),
            ...(canonicalInternet?.percentage == null ? [] : [{
              ano: schoolInfrastructure.referenceYear,
              valor: canonicalInternet.percentage,
            }]),
          ]
        : valueSeries(series.internet, 'perc_internet'),
      currentValue: canonicalInternet?.percentage ?? resumo.perc_internet,
      formatType: 'percent',
      mainCutLabel: 'Total',
      explore: buildRedeInfraExplore(rede),
      exploratorySummary: {
        count: schoolInfrastructure ? SCHOOL_INFRASTRUCTURE_INDICATOR_ORDER.length : infraDimensionCount,
        groupCount: schoolInfrastructure ? 1 : infraGroups.length,
        label: 'dimensões',
        latestYear: infraLatestYear,
      },
      schoolInfrastructure,
    }),
  ]
}

function buildAlunosTurmaIndicators(alunosTurma) {
  const series = alunosTurma.series ?? {}
  const resumo = alunosTurma.resumo_ultimo_ano ?? {}
  const latestYear = alunosTurma.ultimo_ano
  const base = {
    themeKey: 'turmas',
    themeLabel: 'Alunos por turma',
    themeShortLabel: 'Alunos por turma',
    currentYear: latestYear,
    formatType: 'ratio',
    scaleType: 'dynamic',
    notices: alunosTurma.avisos ?? [],
  }

  const options = (alunosTurma.series_options ?? [])
    .filter((option) => ALUNOS_TURMA_STAGE_ORDER.includes(option.etapa_ensino))
    .filter((option) => hasSeriesData(series.por_serie?.[option.key]))
    .sort((a, b) => {
      const stageDiff = ALUNOS_TURMA_STAGE_ORDER.indexOf(a.etapa_ensino) - ALUNOS_TURMA_STAGE_ORDER.indexOf(b.etapa_ensino)
      if (stageDiff !== 0) return stageDiff
      return Number(a.ordem ?? 999) - Number(b.ordem ?? 999)
    })

  return ALUNOS_TURMA_STAGE_ORDER.map((stageKey) => {
    const stageOptions = options.filter((option) => option.etapa_ensino === stageKey)
    const totalSerieKey = ATU_TOTAL_SERIE_BY_STAGE[stageKey] ?? stageOptions[0]?.key
    const mainOption = stageOptions.find((option) => option.key === totalSerieKey) ?? stageOptions[0]
    if (!mainOption) return null

    const serieKey = mainOption.key
    const serieLabel = alunosTurmaSerieLabel(serieKey, mainOption.label)
    const serie = normalizeYearSeries(series.por_serie?.[serieKey])
    if (serie.length < 2) return null
    const searchText = stageOptions
      .map((option) => alunosTurmaSerieLabel(option.key, option.label))
      .join(' ')

    return createIndicator({
      ...base,
      key: `alunos-turma-${stageKey}`,
      label: `Alunos por turma — ${etapaLabel(stageKey)}`,
      description: `Média oficial de alunos por turma em ${etapaLabel(stageKey).toLocaleLowerCase('pt-BR')}.`,
      categories: [FILTER_KEYS[stageKey] ?? FILTER_KEYS.todos],
      stageKey,
      stageLabel: etapaLabel(stageKey),
      series: serie,
      currentValue: resumo.por_etapa?.[stageKey] ?? serie.at(-1)?.valor,
      mainCutLabel: serieLabel,
      searchText,
      explore: buildAlunosTurmaExplore(alunosTurma, {
        stageKey,
        serieKey,
        serieLabel,
      }),
      stageFilterLabel: 'Série exibida',
      stageFilterOptions: buildAlunosTurmaSerieOptions(alunosTurma, stageOptions),
    })
  }).filter(Boolean)
}

function buildDocentesIndicators(turmas) {
  const series = turmas.series ?? {}
  const resumo = turmas.resumo_ultimo_ano ?? {}
  const latestYear = turmas.ultimo_ano
  const base = { themeKey: 'docentes', themeLabel: 'Docentes', themeShortLabel: 'Docentes', categories: [FILTER_KEYS.todos], isGeral: true, currentYear: latestYear, notices: turmas.avisos ?? [] }
  const stageOrder = ['infantil', 'fundamental', 'medio', 'eja', 'profissional']

  const etapaIndicators = stageOrder.map((stageKey) => {
    const stageSeries = valueSeries(series.por_etapa?.[stageKey], 'docentes')
    if (stageSeries.length < 2) return null
    return createIndicator({
      ...base,
      key: `docentes-${stageKey}`,
      label: `Docentes — ${etapaLabel(stageKey)}`,
      description: `Total de docentes vinculados a ${etapaLabel(stageKey).toLowerCase()}.`,
      categories: [FILTER_KEYS[stageKey] ?? FILTER_KEYS.todos],
      isGeral: false,
      stageLabel: etapaLabel(stageKey),
      series: stageSeries,
      currentValue: latestValue(series.por_etapa?.[stageKey], 'docentes'),
      formatType: 'number',
      mainCutLabel: etapaLabel(stageKey),
      explore: buildTurmasExplore(turmas, {
        cutLabel: etapaLabel(stageKey),
        formatLabel: formatNumber,
        metricKey: 'docentes',
        stageKey,
      }),
    })
  }).filter(Boolean)

  return [
    createIndicator({
      ...base,
      key: 'docentes-total',
      label: 'Total de docentes',
      description: 'Total de docentes registrados no município.',
      series: valueSeries(series.total, 'docentes'),
      currentValue: resumo.docentes,
      formatType: 'number',
      mainCutLabel: 'Total do município',
      explore: buildTurmasExplore(turmas, {
        cutLabel: 'Total do município',
        formatLabel: formatNumber,
        metricKey: 'docentes',
      }),
      stageFilterOptions: buildTurmasStageOptions(turmas, {
        formatLabel: formatNumber,
        metricKey: 'docentes',
      }),
    }),
    ...etapaIndicators,
  ]
}

function buildFluxoIndicators(fluxo) {
  const series = fluxo.series ?? {}
  const resumo = fluxo.resumo_ultimo_ano ?? {}
  const latestYear = fluxo.ultimo_ano
  const defaultSeries = series.por_etapa?.fundamental ?? []
  const medioSeries = series.por_etapa?.medio ?? []
  const base = { themeKey: 'fluxo', themeLabel: 'Fluxo escolar', themeShortLabel: 'Fluxo', categories: [FILTER_KEYS.fundamental], stageLabel: 'Ensino Fundamental', currentYear: latestYear, formatType: 'percent', notices: fluxo.avisos ?? [] }
  return [
    createIndicator({ ...base, key: 'fluxo-aprovacao', label: 'Taxa de aprovação', description: 'Percentual de aprovação no fluxo escolar.', series: valueSeries(defaultSeries, 'taxa_aprovacao'), currentValue: resumo.taxa_aprovacao, mainCutLabel: 'Ensino Fundamental', explore: buildFluxoExplore(fluxo, { cutLabel: 'Ensino Fundamental', stageKey: 'fundamental', metricKey: 'taxa_aprovacao' }), stageFilterOptions: buildFluxoStageOptions(fluxo, { metricKey: 'taxa_aprovacao' }) }),
    createIndicator({ ...base, key: 'fluxo-aprovacao-medio', label: 'Taxa de aprovação no ensino médio', description: 'Percentual de aprovação no ensino médio.', series: valueSeries(medioSeries, 'taxa_aprovacao'), currentValue: latestValue(medioSeries, 'taxa_aprovacao'), mainCutLabel: 'Ensino Médio', stageLabel: 'Ensino Médio', categories: [FILTER_KEYS.medio], explore: buildFluxoExplore(fluxo, { cutLabel: 'Ensino Médio', stageKey: 'medio', metricKey: 'taxa_aprovacao' }) }),
    createIndicator({ ...base, key: 'fluxo-reprovacao', label: 'Taxa de reprovação', description: 'Percentual de reprovação no fluxo escolar.', series: valueSeries(defaultSeries, 'taxa_reprovacao'), currentValue: resumo.taxa_reprovacao, mainCutLabel: 'Ensino Fundamental', explore: buildFluxoExplore(fluxo, { cutLabel: 'Ensino Fundamental', stageKey: 'fundamental', metricKey: 'taxa_reprovacao' }), stageFilterOptions: buildFluxoStageOptions(fluxo, { metricKey: 'taxa_reprovacao' }) }),
    createIndicator({ ...base, key: 'fluxo-abandono', label: 'Taxa de abandono', description: 'Percentual de abandono no fluxo escolar.', series: valueSeries(defaultSeries, 'taxa_abandono'), currentValue: resumo.taxa_abandono, mainCutLabel: 'Ensino Fundamental', explore: buildFluxoExplore(fluxo, { cutLabel: 'Ensino Fundamental', stageKey: 'fundamental', metricKey: 'taxa_abandono' }), stageFilterOptions: buildFluxoStageOptions(fluxo, { metricKey: 'taxa_abandono' }) }),
    createIndicator({ ...base, key: 'fluxo-distorcao', label: 'Distorção idade-série', description: 'Percentual de estudantes com distorção idade-série.', series: valueSeries(defaultSeries, 'taxa_distorcao'), currentValue: resumo.taxa_distorcao, mainCutLabel: 'Ensino Fundamental', explore: buildFluxoExplore(fluxo, { cutLabel: 'Ensino Fundamental', stageKey: 'fundamental', metricKey: 'taxa_distorcao', noLocation: true }), stageFilterOptions: buildFluxoStageOptions(fluxo, { metricKey: 'taxa_distorcao', noLocation: true }) }),
  ]
}

function buildAprendizagemIndicators(aprend) {
  const series = aprend.series ?? {}
  const resumo = aprend.resumo_ultimo_ano ?? {}
  const preferredIdeb = getPreferredIdeb(resumo)
  const preferredSeries = preferredIdeb?.etapa ? series.ideb?.[preferredIdeb.etapa] : []
  const base = { themeKey: 'aprendizagem', themeLabel: 'Aprendizagem', themeShortLabel: 'Aprendizagem', categories: [FILTER_KEYS.todos], isGeral: true, currentYear: preferredIdeb?.ano ?? aprend.ultimo_ano?.ideb, notices: aprend.avisos ?? [] }
  return [
    createIndicator({ ...base, key: 'apr-ideb', label: 'IDEB', description: 'Último IDEB disponível para o recorte principal.', series: valueSeries(preferredSeries, 'ideb'), currentValue: preferredIdeb?.ideb, formatType: 'value', mainCutLabel: preferredIdeb ? etapaLabel(preferredIdeb.etapa) : 'IDEB', explore: buildAprendizagemExplore(aprend, { metricKey: 'ideb', metricLabel: 'IDEB', formatLabel: formatValue }), stageFilterOptions: buildAprendizagemStageOptions(aprend, { metricKey: 'ideb', metricLabel: 'IDEB', formatLabel: formatValue }) }),
    createIndicator({ ...base, key: 'apr-saeb-lp', label: 'SAEB Língua Portuguesa', description: 'Resultado de Língua Portuguesa no SAEB.', series: valueSeries(preferredSeries, 'saeb_lp'), currentValue: latestValue(preferredSeries, 'saeb_lp'), formatType: 'value', mainCutLabel: preferredIdeb ? etapaLabel(preferredIdeb.etapa) : 'SAEB LP', explore: buildAprendizagemExplore(aprend, { metricKey: 'saeb_lp', metricLabel: 'SAEB LP', formatLabel: formatValue }), stageFilterOptions: buildAprendizagemStageOptions(aprend, { metricKey: 'saeb_lp', metricLabel: 'SAEB LP', formatLabel: formatValue }) }),
    createIndicator({ ...base, key: 'apr-saeb-mt', label: 'SAEB Matemática', description: 'Resultado de Matemática no SAEB.', series: valueSeries(preferredSeries, 'saeb_mt'), currentValue: latestValue(preferredSeries, 'saeb_mt'), formatType: 'value', mainCutLabel: preferredIdeb ? etapaLabel(preferredIdeb.etapa) : 'SAEB MT', explore: buildAprendizagemExplore(aprend, { metricKey: 'saeb_mt', metricLabel: 'SAEB Matemática', formatLabel: formatValue }), stageFilterOptions: buildAprendizagemStageOptions(aprend, { metricKey: 'saeb_mt', metricLabel: 'SAEB Matemática', formatLabel: formatValue }) }),
    createIndicator({ ...base, key: 'apr-alfabetizacao', label: 'Alfabetização', description: 'Taxa de alfabetização disponível para os anos recentes.', categories: [FILTER_KEYS.fundamental], isGeral: false, stageLabel: 'Ensino Fundamental', series: valueSeries(series.alfabetizacao, 'taxa_alfabetizacao'), currentValue: resumo.taxa_alfabetizacao, currentYear: aprend.ultimo_ano?.alfabetizacao, formatType: 'percent', mainCutLabel: 'Alfabetização', explore: buildAprendizagemExplore(aprend, { metricKey: 'taxa_alfabetizacao', metricLabel: 'Alfabetização', formatLabel: formatPercent }) }),
    createIndicator({ ...base, key: 'apr-inse', label: 'INSE', description: 'Média do indicador de nível socioeconômico.', series: valueSeries(series.inse, 'media_inse'), currentValue: resumo.media_inse, currentYear: aprend.ultimo_ano?.inse, formatType: 'value', mainCutLabel: 'Nível socioeconômico', explore: buildAprendizagemExplore(aprend, { metricKey: 'media_inse', metricLabel: 'INSE', formatLabel: formatValue }) }),
  ]
}

function buildOfertaIndicators(oferta) {
  const series = oferta.series ?? {}
  const resumo = oferta.resumo_ultimo_ano ?? {}
  const latestYear = oferta.ultimo_ano
  const explore = buildOfertaExplore(oferta)
  return [
    createIndicator({ key: 'oferta-total', label: 'Matrículas técnicas — Sinopse Estatística', description: 'Total de matrículas em cursos técnicos e profissionais segundo a Sinopse Estatística do Censo Escolar.', themeKey: 'oferta', themeLabel: 'Matrículas técnicas · Sinopse Estatística', themeShortLabel: 'Sinopse Estatística', categories: [FILTER_KEYS.profissional], stageLabel: 'Educação Profissional', series: normalizeYearSeries(series.total), currentValue: resumo.total_matriculas_tecnicas, currentYear: latestYear, formatType: 'number', mainCutLabel: 'Matrículas técnicas · Sinopse Estatística', explore, notices: oferta.avisos ?? [] }),
  ]
}

export function buildIndigenousEducationIndicators(block) {
  const latestYear = block.ultimo_ano
  const summary = block.resumo_ultimo_ano ?? {}
  const series = block.series_totais ?? {}
  const estimatedCoverage = block.coberturaEstimada ?? {}
  const coverageSeries = Object.entries(estimatedCoverage.series ?? {}).map(([year, item]) => ({
    ano: Number(year),
    valor: item?.status === 'available' ? item.percentage : null,
    status: item?.status ?? 'unavailable',
  }))
  const latestCoverage = coverageSeries.find((item) => item.ano === latestYear)
  const base = {
    themeKey: 'educacao_indigena',
    themeLabel: 'Educação indígena',
    themeShortLabel: 'Educação indígena',
    categories: [FILTER_KEYS.todos],
    isGeral: true,
    currentYear: latestYear,
    formatType: 'number',
    mainCutLabel: 'Educação Escolar Indígena',
    neutralTrend: true,
    zeroMessage: 'Nenhuma ocorrência registrada no universo medido',
    notices: block.avisos ?? [],
  }

  return [
    createIndicator({
      ...base,
      key: 'indigena-cobertura-estimada-4-17',
      label: 'Cobertura estimada da educação escolar indígena — 4 a 17 anos',
      description: 'Relação entre as matrículas de pré-escola, ensino fundamental e ensino médio e a população indígena de 4 a 17 anos recenseada em 2022.',
      series: coverageSeries,
      currentValue: latestCoverage?.valor ?? null,
      unit: '%',
      formatType: 'percent',
      indigenousUnitKey: 'cobertura',
      neutralTrend: true,
      zeroMessage: 'Não foram registradas matrículas nas etapas consideradas',
    }),
    createIndicator({
      ...base,
      key: 'indigena-matriculas',
      label: 'Matrículas na educação escolar indígena',
      description: 'Total municipal oficial de matrículas nas tabelas específicas de Educação Indígena da Sinopse Estatística.',
      series: normalizeYearSeries(series.matriculas),
      currentValue: summary.matriculas,
      unit: 'matrículas',
      indigenousUnitKey: 'matriculas',
    }),
    createIndicator({
      ...base,
      key: 'indigena-estabelecimentos',
      label: 'Estabelecimentos com oferta de educação escolar indígena',
      description: 'Total municipal oficial de estabelecimentos com oferta nas tabelas específicas de Educação Indígena da Sinopse Estatística.',
      series: normalizeYearSeries(series.estabelecimentos),
      currentValue: summary.estabelecimentos,
      unit: 'estabelecimentos',
      indigenousUnitKey: 'estabelecimentos',
    }),
    createIndicator({
      ...base,
      key: 'indigena-docentes',
      label: 'Docentes da educação escolar indígena',
      description: 'Total municipal oficial de docentes nas tabelas específicas de Educação Indígena da Sinopse Estatística.',
      series: normalizeYearSeries(series.docentes),
      currentValue: summary.docentes,
      unit: 'docentes',
      indigenousUnitKey: 'docentes',
    }),
    createIndicator({
      ...base,
      key: 'indigena-turmas',
      label: 'Turmas da educação escolar indígena',
      description: 'Total municipal oficial de turmas nas tabelas específicas de Educação Indígena da Sinopse Estatística.',
      series: normalizeYearSeries(series.turmas),
      currentValue: summary.turmas,
      unit: 'turmas',
      indigenousUnitKey: 'turmas',
    }),
  ]
}

export function createIndicator(config) {
  const catalogItem = getEducationIndicatorCatalogItem(config.key)
  const displayLabel = normalizeEducationIndicatorLabel(config.label)
  const series = normalizeYearSeries(config.series)
  const categories = normalizeIndicatorCategories(config)
  const isGeral = config.isGeral ?? (categories.length === 1 && categories[0] === FILTER_KEYS.todos)
  const first = series[0] ?? null
  const latest = series.at(-1) ?? null
  const currentValue = isMissing(config.currentValue) ? latest?.valor : config.currentValue
  const currentYear = config.currentYear ?? latest?.ano ?? null
  const initialValue = first?.valor
  const initialYear = first?.ano ?? null
  const formatValueForType = getFormatter(config.formatType)
  const variation = calculateVariation(initialValue, currentValue, config.formatType)
  const status = getIndicatorStatus(currentValue, series, variation)

  return {
    ...config,
    label: displayLabel,
    id: config.id ?? config.key,
    catalogKey: catalogItem?.key ?? config.key,
    catalogType: catalogItem?.type ?? 'base',
    section: config.section ?? catalogItem?.section ?? null,
    sections: config.sections ?? catalogItem?.sections ?? [],
    groupKey: config.groupKey ?? catalogItem?.groupKey ?? null,
    renderer: config.renderer ?? catalogItem?.renderer ?? 'EducationIndicatorDetail',
    missingPolicy: config.missingPolicy ?? catalogItem?.missingPolicy ?? null,
    tema: config.tema ?? config.themeKey,
    categorias: categories,
    categories,
    recortePrincipal: config.recortePrincipal ?? config.mainCutLabel,
    isGeral,
    categoryLabel: config.categoryLabel ?? getCategoryLabel(categories),
    showPointLabels: config.showPointLabels ?? true,
    series,
    chartColor: config.chartColor ?? '#16713a',
    currentDisplay: formatValueForType(currentValue),
    currentValue,
    currentYear,
    formatValue: formatValueForType,
    initialDisplay: formatValueForType(initialValue),
    initialValue,
    initialYear,
    formatType: config.formatType ?? 'number',
    unit: config.unit ?? catalogItem?.unit ?? null,
    notices: config.notices ?? [],
    explore: filterRenderableExplore(config.explore),
    stageFilterOptions: filterStageFilterOptions(config.stageFilterOptions),
    quickReading: config.quickReading ?? buildQuickReading({ currentDisplay: formatValueForType(currentValue), currentValue, currentYear, formatType: config.formatType, initialValue, initialYear, label: displayLabel, variation }),
    scaleType: config.scaleType ?? inferScaleType(config),
    statusLabel: config.statusLabel ?? status.label,
    statusTone: config.statusTone ?? status.tone,
    variationDisplay: variation.display,
    variationRaw: variation.raw,
    variationTone: variation.tone,
  }
}

function normalizeIndicatorCategories(config) {
  const categories = config.categories ?? config.stageKeys ?? ['todos']
  const normalized = categories.filter(Boolean)
  return normalized.length ? normalized : ['todos']
}

function getCategoryLabel(categories) {
  if (!categories.length) return CATEGORY_LABELS[FILTER_KEYS.todos]
  if (categories.length === 1) return CATEGORY_LABELS[categories[0]] ?? categories[0]
  return categories.map((category) => CATEGORY_LABELS[category] ?? category).join(', ')
}

export function filterRenderableExplore(explore) {
  if (!Array.isArray(explore)) return []
  return explore.filter((item) => hasExploreData(item))
}

function filterStageFilterOptions(options) {
  if (!Array.isArray(options)) return []
  return options
    .map((option) => ({
      ...option,
      explore: filterRenderableExplore(option.explore),
      series: normalizeYearSeries(option.series),
    }))
    .filter((option) => option.series.length >= 2)
}

function hasExploreData(item) {
  if (!item) return false
  if (item.type === 'stacked') {
    return Array.isArray(item.categories)
      && item.categories.length > 0
      && Array.isArray(item.data)
      && item.data.some((row) => Object.values(row.values ?? {}).some((value) => !isMissing(value)))
  }
  if (item.type === 'bar') {
    return Array.isArray(item.data) && item.data.some((row) => !isMissing(row.value))
  }
  if (item.type === 'line') {
    return Array.isArray(item.series) && item.series.length >= 2
  }
  if (item.type === 'age-range') {
    return Array.isArray(item.rows) && item.rows.some((row) => !isMissing(detailRowValue(row, 'matriculas')))
  }
  if (item.type === 'color-race') {
    return Array.isArray(item.rows) && item.rows.some((row) => !isMissing(detailRowValue(row, 'matriculas')))
  }
  if (item.type === 'modality-range') {
    return Array.isArray(item.rows) && item.rows.some((row) => !isMissing(detailRowValue(row, 'matriculas')))
  }
  if (item.type === 'stage-detail') {
    return Array.isArray(item.distributionData) && item.distributionData.some((row) => !isMissing(row.value))
  }
  if (item.type === 'stage-context') {
    return !isMissing(item.value ?? item.turmas)
  }
  if (item.type === 'table') {
    return Array.isArray(item.rows) && item.rows.length > 0
  }
  return true
}

function buildMatriculasStageOptions(mat) {
  const series = mat.series ?? {}
  const options = [
    makeStageOption({
      key: 'total',
      label: 'Total',
      mainCutLabel: 'Total do município',
      series: series.total,
      explore: buildMatriculasExplore(mat, { cutKey: 'total', cutLabel: 'Total do município' }),
    }),
    ...orderedStageKeys(series.por_etapa).map((key) => makeStageOption({
      key,
      label: etapaLabel(key),
      mainCutLabel: etapaLabel(key),
      series: series.por_etapa?.[key],
      explore: buildMatriculasExplore(mat, { cutKey: key, cutLabel: etapaLabel(key), stageKey: key }),
    })),
  ]
  return options.filter(Boolean)
}

function buildAlunosTurmaSerieOptions(alunosTurma, options) {
  const series = alunosTurma.series ?? {}
  return options
    .map((option) => {
      const serieKey = option.key
      const serieLabel = alunosTurmaSerieLabel(serieKey, option.label)
      return makeStageOption({
        key: serieKey,
        label: serieLabel,
        mainCutLabel: serieLabel,
        series: series.por_serie?.[serieKey],
        explore: buildAlunosTurmaExplore(alunosTurma, {
          stageKey: option.etapa_ensino,
          serieKey,
          serieLabel,
        }),
      })
    })
    .filter(Boolean)
}

function buildTurmasStageOptions(turmas, metric) {
  const series = turmas.series ?? {}
  const metricLabel = turmasMetricLabel(metric.metricKey)
  const options = [
    makeStageOption({
      key: 'total',
      label: 'Total',
      mainCutLabel: 'Total do município',
      series: valueSeries(series.total, metric.metricKey),
      explore: buildTurmasExplore(turmas, {
        cutLabel: 'Total do município',
        formatLabel: metric.formatLabel,
        metricKey: metric.metricKey,
      }),
    }),
    ...orderedStageKeys(series.por_etapa, metric.metricKey).map((key) => makeStageOption({
      key,
      label: etapaLabel(key),
      mainCutLabel: etapaLabel(key),
      series: valueSeries(series.por_etapa?.[key], metric.metricKey),
      explore: buildTurmasExplore(turmas, {
        cutLabel: etapaLabel(key),
        formatLabel: metric.formatLabel,
        metricKey: metric.metricKey,
        stageKey: key,
      }),
    })),
  ]
  return options
    .filter(Boolean)
    .map((option) => ({ ...option, label: option.key === 'total' ? `Total de ${metricLabel.toLowerCase()}` : option.label }))
}

function buildFluxoStageOptions(fluxo, metric) {
  const series = fluxo.series ?? {}
  return orderedStageKeys(series.por_etapa, metric.metricKey)
    .map((key) => makeStageOption({
      key,
      label: etapaLabel(key),
      mainCutLabel: etapaLabel(key),
      series: valueSeries(series.por_etapa?.[key], metric.metricKey),
      explore: buildFluxoExplore(fluxo, { ...metric, cutLabel: etapaLabel(key), stageKey: key }),
    }))
    .filter(Boolean)
}

function buildAprendizagemStageOptions(aprend, metric) {
  const stageSeries = aprendizStageSeries(aprend, metric.metricKey)
  const preferredStage = getPreferredIdeb(aprend.resumo_ultimo_ano ?? {})?.etapa
  return orderPreferredStageFirst(orderedStageKeys(stageSeries, metric.metricKey), preferredStage)
    .map((key) => makeStageOption({
      key,
      label: etapaLabel(key),
      mainCutLabel: etapaLabel(key),
      series: valueSeries(stageSeries?.[key], metric.metricKey),
      explore: buildAprendizagemExplore(aprend, { ...metric, stageKey: key, cutLabel: etapaLabel(key) }),
    }))
    .filter(Boolean)
}

function makeStageOption(option) {
  const series = normalizeYearSeries(option.series)
  if (series.length < 2) return null
  return { ...option, series }
}

function orderedStageKeys(source, valueKey = 'valor') {
  const keys = Object.keys(source ?? {}).filter((key) => hasSeriesData(source?.[key], valueKey))
  return STAGE_FILTER_ORDER.filter((key) => key !== 'total' && keys.includes(key))
}

function orderPreferredStageFirst(keys, preferredStage) {
  if (!preferredStage || !keys.includes(preferredStage)) return keys
  return [preferredStage, ...keys.filter((key) => key !== preferredStage)]
}

function aprendizStageSeries(aprend, metricKey) {
  const series = aprend.series ?? {}
  if (metricKey === 'taxa_alfabetizacao') return { fundamental: series.alfabetizacao }
  if (metricKey === 'media_inse') return series.inse_por_etapa ?? {}
  return series.ideb ?? {}
}

function buildMatriculasExplore(mat, cut = { cutKey: 'total', cutLabel: 'Total do município' }) {
  const series = mat.series ?? {}
  const resumo = mat.resumo_ultimo_ano ?? {}
  const detalhamentos = mat.detalhamentos ?? {}
  const dependencyKeys = dependencyCategoryKeys(series.por_dependencia)
  const titleSuffix = ` — ${cut.cutLabel}`
  const latestYear = mat.ultimo_ano ? ` — ${mat.ultimo_ano}` : ''

  if (cut.cutKey === 'total') {
    const totalByStage = Object.fromEntries(
      TOTAL_ENROLLMENT_STAGE_KEYS.map((key) => [key, resumo.por_etapa?.[key]]),
    )
    return [
      { key: 'mat-etapa', type: 'bar', title: `Matrículas por etapa e modalidade${latestYear}${titleSuffix}`, color: '#16713a', data: entriesToRows(totalByStage, etapaLabel), formatLabel: formatNumber },
      { key: 'mat-dep', type: 'stacked', title: `Composição por rede${titleSuffix}`, categories: categoryDefinitions(dependencyKeys, depLabel, DEPENDENCY_COLORS), data: seriesMapToStackedRows(series.por_dependencia, dependencyKeys), formatLabel: formatNumber },
      { key: 'mat-loc', type: 'stacked', title: `Composição por localização${titleSuffix}`, categories: categoryDefinitions(['urbana', 'rural'], locLabel, LOCATION_COLORS), data: seriesMapToStackedRows(series.por_localizacao, ['urbana', 'rural']), formatLabel: formatNumber },
    ]
  }

  if (cut.stageKey) {
    const etapaItems = []
    if (cut.stageKey === 'fundamental') {
      etapaItems.push({
        key: 'mat-fundamental-subetapas',
        type: 'bar',
        presentation: 'compact-comparison',
        title: `Composição por etapa${latestYear}${titleSuffix}`,
        color: '#16713a',
        data: entriesToRows({
          fundamental_anos_iniciais: resumo.por_etapa?.fundamental_anos_iniciais,
          fundamental_anos_finais: resumo.por_etapa?.fundamental_anos_finais,
        }, etapaLabel),
        formatLabel: formatNumber,
      })
    }

    const stageDependencyRows = detailRowsFor(detalhamentos.por_etapa_rede, { etapa_ensino: cut.stageKey })
    const stageDependencyKeys = dependencyKeysFromDetailRows(stageDependencyRows)
    const stageLocationRows = detailRowsFor(detalhamentos.por_etapa_localizacao, { etapa_ensino: cut.stageKey })
    const stageLocationKeys = detailKeys(stageLocationRows, 'localizacao', ['urbana', 'rural'])
    const faixaEtariaItem = buildMatriculasFaixaEtariaItem(detalhamentos, cut)
    const corRacaItem = buildMatriculasCorRacaItem(detalhamentos, cut)

    return [
      ...etapaItems,
      ...(faixaEtariaItem ? [faixaEtariaItem] : []),
      ...(corRacaItem ? [corRacaItem] : []),
      {
        key: `mat-${cut.stageKey}-dep`,
        type: 'stacked',
        title: `Composição por rede${titleSuffix}`,
        categories: categoryDefinitions(stageDependencyKeys, depLabel, DEPENDENCY_COLORS),
        data: detailRowsToStackedRows(stageDependencyRows, 'dependencia', stageDependencyKeys),
        formatLabel: formatNumber,
      },
      {
        key: `mat-${cut.stageKey}-loc`,
        type: 'stacked',
        title: `Composição por localização${titleSuffix}`,
        categories: categoryDefinitions(stageLocationKeys, locLabel, LOCATION_COLORS),
        data: detailRowsToStackedRows(stageLocationRows, 'localizacao', stageLocationKeys),
        formatLabel: formatNumber,
      },
    ]
  }

  if (cut.locationKey) {
    const etapaRows = detailRowsFor(detalhamentos.por_etapa_localizacao, { localizacao: cut.locationKey })
    const dependencyRows = detailRowsFor(detalhamentos.por_rede_localizacao, { localizacao: cut.locationKey })
    const locationDependencyKeys = dependencyKeysFromDetailRows(dependencyRows)
    return [
      { key: `mat-${cut.locationKey}-etapa`, type: 'bar', title: titleWithYear(`Composição por etapa${titleSuffix}`, detailRowsToLatestRows(etapaRows, 'etapa_ensino', etapaLabel)), color: '#16713a', data: detailRowsToLatestRows(etapaRows, 'etapa_ensino', etapaLabel), formatLabel: formatNumber },
      {
        key: `mat-${cut.locationKey}-dep`,
        type: 'stacked',
        title: `Composição por rede${titleSuffix}`,
        categories: categoryDefinitions(locationDependencyKeys, depLabel, DEPENDENCY_COLORS),
        data: detailRowsToStackedRows(dependencyRows, 'dependencia', locationDependencyKeys),
        formatLabel: formatNumber,
      },
    ]
  }

  if (cut.dependencyKey) {
    const etapaRows = detailRowsFor(detalhamentos.por_etapa_rede, { dependencia: cut.dependencyKey })
    const locationRows = detailRowsFor(detalhamentos.por_rede_localizacao, { dependencia: cut.dependencyKey })
    const dependencyLocationKeys = detailKeys(locationRows, 'localizacao', ['urbana', 'rural'])
    return [
      { key: `mat-${cut.dependencyKey}-etapa`, type: 'bar', title: titleWithYear(`Composição por etapa${titleSuffix}`, detailRowsToLatestRows(etapaRows, 'etapa_ensino', etapaLabel)), color: '#16713a', data: detailRowsToLatestRows(etapaRows, 'etapa_ensino', etapaLabel), formatLabel: formatNumber },
      {
        key: `mat-${cut.dependencyKey}-loc`,
        type: 'stacked',
        title: `Composição por localização${titleSuffix}`,
        categories: categoryDefinitions(dependencyLocationKeys, locLabel, LOCATION_COLORS),
        data: detailRowsToStackedRows(locationRows, 'localizacao', dependencyLocationKeys),
        formatLabel: formatNumber,
      },
    ]
  }

  return []
}

function buildMatriculasFaixaEtariaItem(detalhamentos, cut) {
  const fonte = detalhamentos.por_etapa_faixa_etaria ?? []
  const fonteSecao = detalhamentos.por_etapa_secao_faixa_etaria ?? []
  let rows = []
  let stageLabel = cut.cutLabel
  let stageOptions = []

  if (cut.stageKey === 'infantil') {
    rows = detailRowsFor(fonteSecao, { etapa_ensino: 'infantil' })
      .filter((row) => ['creche', 'pre_escola'].includes(row?.secao_sinopse))
    stageLabel = 'Creche'
    stageOptions = [
      { key: 'creche', label: 'Creche', field: 'secao_sinopse' },
      { key: 'pre_escola', label: 'Pré-escola', field: 'secao_sinopse' },
    ].filter((option) => rows.some((row) => row.secao_sinopse === option.key))
  } else if (cut.stageKey === 'fundamental') {
    rows = fonte.filter((row) => FUNDAMENTAL_FAIXA_STAGES.includes(row?.etapa_ensino))
    stageLabel = etapaLabel(FUNDAMENTAL_FAIXA_STAGES[0])
    stageOptions = FUNDAMENTAL_FAIXA_STAGES
      .filter((stageKey) => rows.some((row) => row.etapa_ensino === stageKey))
      .map((stageKey) => ({ key: stageKey, label: etapaLabel(stageKey), field: 'etapa_ensino' }))
  } else if (cut.stageKey === 'eja') {
    rows = filterEjaAgeRangeRows(detailRowsFor(fonte, { etapa_ensino: cut.stageKey }))
  } else if (cut.stageKey) {
    rows = detailRowsFor(fonte, { etapa_ensino: cut.stageKey })
  }

  if (!ageRangeLatestRows(rows).length) return null

  return {
    key: `mat-${cut.stageKey}-faixa-etaria`,
    type: 'age-range',
    title: 'Matrículas por faixa etária',
    color: '#0f766e',
    historyColor: '#2563eb',
    rows,
    stageLabel,
    stageOptions,
    formatLabel: formatNumber,
  }
}

function buildMatriculasCorRacaItem(detalhamentos, cut) {
  const fonte = detalhamentos.por_etapa_cor_raca ?? []
  const fonteSecao = detalhamentos.por_etapa_secao_cor_raca ?? []
  let rows = []
  let stageLabel = cut.cutLabel
  let stageOptions = []

  if (cut.stageKey === 'infantil') {
    rows = detailRowsFor(fonteSecao, { etapa_ensino: 'infantil' })
      .filter((row) => ['creche', 'pre_escola'].includes(row?.secao_sinopse))
    stageLabel = 'Creche'
    stageOptions = [
      { key: 'creche', label: 'Creche', field: 'secao_sinopse' },
      { key: 'pre_escola', label: 'Pré-escola', field: 'secao_sinopse' },
    ].filter((option) => rows.some((row) => row.secao_sinopse === option.key))
  } else if (cut.stageKey === 'fundamental') {
    rows = fonte.filter((row) => FUNDAMENTAL_FAIXA_STAGES.includes(row?.etapa_ensino))
    stageLabel = etapaLabel(FUNDAMENTAL_FAIXA_STAGES[0])
    stageOptions = FUNDAMENTAL_FAIXA_STAGES
      .filter((stageKey) => rows.some((row) => row.etapa_ensino === stageKey))
      .map((stageKey) => ({ key: stageKey, label: etapaLabel(stageKey), field: 'etapa_ensino' }))
  } else if (cut.stageKey) {
    rows = detailRowsFor(fonte, { etapa_ensino: cut.stageKey })
  }

  if (!corRacaOptions(rows).length) return null

  return {
    key: `mat-${cut.stageKey}-cor-raca`,
    type: 'color-race',
    title: 'Matrículas por cor/raça',
    rows,
    stageLabel,
    stageOptions,
    historyColor: '#7c3aed',
    formatLabel: formatNumber,
  }
}

function filterEjaAgeRangeRows(rows) {
  return (Array.isArray(rows) ? rows : []).filter((row) => (
    EJA_VALID_AGE_RANGES.includes(row?.faixa_etaria)
  ))
}

function buildMatriculasIntegralExplore(mat) {
  const detalhamentos = mat.detalhamentos ?? {}
  const etapaRows = detailRowsToLatestRows(detalhamentos.tempo_integral_por_etapa, 'etapa_ensino', etapaLabel, 'matriculas_integral')
  const dependencyRows = detalhamentos.tempo_integral_por_rede ?? []
  const dependencyKeys = dependencyKeysFromDetailRows(dependencyRows, 'matriculas_integral')
  const locationRows = detalhamentos.tempo_integral_por_localizacao ?? []
  const locationKeys = detailKeys(locationRows, 'localizacao', ['urbana', 'rural'], 'matriculas_integral')

  return [
    {
      key: 'mat-integral-etapa',
      type: 'bar',
      title: titleWithYear('Matrículas em tempo integral por etapa', etapaRows),
      color: '#16713a',
      data: etapaRows,
      formatLabel: formatNumber,
    },
    {
      key: 'mat-integral-rede',
      type: 'stacked',
      title: 'Matrículas em tempo integral por rede — histórico',
      categories: categoryDefinitions(dependencyKeys, depLabel, DEPENDENCY_COLORS),
      data: detailRowsToStackedRows(dependencyRows, 'dependencia', dependencyKeys, 'matriculas_integral'),
      formatLabel: formatNumber,
    },
    {
      key: 'mat-integral-localizacao',
      type: 'stacked',
      title: 'Matrículas em tempo integral por localização — histórico',
      categories: categoryDefinitions(locationKeys, locLabel, LOCATION_COLORS),
      data: detailRowsToStackedRows(locationRows, 'localizacao', locationKeys, 'matriculas_integral'),
      formatLabel: formatNumber,
    },
  ]
}

function detailRowsFor(rows, filters) {
  if (!Array.isArray(rows)) return []
  return rows.filter((row) => (
    Object.entries(filters).every(([field, value]) => row?.[field] === value)
  ))
}

function detailKeys(rows, field, preferredOrder, valueKey = 'valor') {
  const keys = new Set()
  rows.forEach((row) => {
    if (!isMissing(row?.[field]) && !isMissing(detailRowValue(row, valueKey))) keys.add(row[field])
  })
  return preferredOrder.filter((key) => keys.has(key))
}

function dependencyKeysFromDetailRows(rows, valueKey = 'valor') {
  const detailed = detailKeys(rows, 'dependencia', ['federal', 'estadual', 'municipal', 'privada'], valueKey)
  if (detailed.length) return detailed
  return detailKeys(rows, 'dependencia', ['publica', 'privada'], valueKey)
}

function detailRowsToStackedRows(rows, dimension, keys, valueKey = 'valor') {
  const years = new Set()
  rows.forEach((row) => {
    if (!isMissing(row?.ano) && keys.includes(row?.[dimension]) && !isMissing(detailRowValue(row, valueKey))) {
      years.add(Number(row.ano))
    }
  })

  return [...years].sort((a, b) => a - b).map((year) => {
    const values = {}
    keys.forEach((key) => {
      const point = rows.find((row) => Number(row.ano) === year && row[dimension] === key)
      const value = detailRowValue(point, valueKey)
      if (!isMissing(value)) values[key] = value
    })
    return { year, values }
  })
}

function detailRowsToLatestRows(rows, dimension, labelFn, valueKey = 'valor') {
  const latestByKey = new Map()
  rows.forEach((row) => {
    const key = row?.[dimension]
    const value = detailRowValue(row, valueKey)
    if (isMissing(key) || isMissing(row?.ano) || isMissing(value)) return
    const current = latestByKey.get(key)
    if (!current || Number(row.ano) > Number(current.ano)) {
      latestByKey.set(key, { ano: Number(row.ano), value })
    }
  })

  return Array.from(latestByKey.entries())
    .map(([key, point]) => ({ label: labelFn(key), value: point.value, year: point.ano }))
}

export function ageRangeOptions(rows) {
  return [...new Set((Array.isArray(rows) ? rows : [])
    .map((row) => row?.faixa_etaria)
    .filter((faixa) => !isMissing(faixa)))]
    .sort((a, b) => faixaEtariaSortValue(a) - faixaEtariaSortValue(b))
}

function ageRangeLatestRows(rows) {
  return detailRowsToLatestRowsByLabel(
    rows,
    (row) => row.faixa_etaria,
    'matriculas',
    (row) => faixaEtariaSortValue(row.faixa_etaria),
  )
}

export function comparisonYearsForRows(rows) {
  const years = [...new Set((Array.isArray(rows) ? rows : [])
    .map((row) => Number(row?.ano))
    .filter((year) => Number.isFinite(year)))]
    .sort((a, b) => a - b)
  if (years.length <= 3) return years
  const middleIndex = Math.floor((years.length - 1) / 2)
  return [...new Set([years[0], years[middleIndex], years[years.length - 1]])]
}

export function comparisonYearsWithRecentTail(rows, options = {}) {
  const { minYear, maxYears = 5, recentCount = 3 } = options

  const years = [...new Set((Array.isArray(rows) ? rows : [])
    .map((row) => Number(row?.ano))
    .filter((year) => Number.isFinite(year)))]
    .sort((a, b) => a - b)

  let available = years
  if (minYear !== undefined) {
    available = years.filter((year) => year >= minYear)
  }

  if (available.length === 0) {
    available = years
  }

  if (available.length <= maxYears) return available

  const result = [available[0]]
  const tail = available.slice(-recentCount)
  const middleCandidates = available.filter((y) => y > result[0] && y < tail[0])

  if (middleCandidates.length > 0) {
    const midIndex = Math.round((middleCandidates.length - 1) / 2)
    result.push(middleCandidates[midIndex])
  }

  result.push(...tail)
  return result
}

export function ageRangeComparisonRows(rows, years, faixas) {
  return years.map((year) => {
    const values = {}
    faixas.forEach((faixa) => {
      const row = rows.find((item) => item?.faixa_etaria === faixa && Number(item?.ano) === year)
      const value = row ? detailRowValue(row, 'matriculas') : null
      if (!isMissing(value)) values[faixa] = value
    })
    return { year, values }
  }).filter((row) => Object.values(row.values).some((value) => !isMissing(value)))
}

export function ageRangeCategoryDefinitions(faixas) {
  return faixas.map((faixa, index) => ({
    key: faixa,
    label: faixa,
    color: CATEGORY_COMPARISON_COLORS[index % CATEGORY_COMPARISON_COLORS.length],
  }))
}

export function modalityOptions(rows) {
  return [...new Set((Array.isArray(rows) ? rows : [])
    .map((row) => row?.modalidade)
    .filter((modalidade) => !isMissing(modalidade)))]
    .sort((a, b) => modLabel(a).localeCompare(modLabel(b), 'pt-BR'))
    .map((key) => ({ key, label: modLabel(key) }))
}

export function corRacaLabel(key) {
  return key ?? EM
}

export function corRacaOptions(rows) {
  return [...new Set((Array.isArray(rows) ? rows : [])
    .map((row) => row?.cor_raca)
    .filter((corRaca) => !isMissing(corRaca)))]
    .sort((a, b) => {
      const ai = COR_RACA_ORDER.indexOf(a)
      const bi = COR_RACA_ORDER.indexOf(b)
      if (ai >= 0 && bi >= 0) return ai - bi
      if (ai >= 0) return -1
      if (bi >= 0) return 1
      return String(a).localeCompare(String(b), 'pt-BR')
    })
    .map((key) => ({ key, label: corRacaLabel(key) }))
}

export function categoryComparisonRows(rows, years, options, field) {
  return years.map((year) => {
    const values = {}
    options.forEach((option) => {
      const row = rows.find((item) => item?.[field] === option.key && Number(item?.ano) === year)
      const value = row ? detailRowValue(row, 'matriculas') : null
      if (!isMissing(value)) values[option.key] = value
    })
    return { year, values }
  }).filter((row) => Object.values(row.values).some((value) => !isMissing(value)))
}

export function categoryHistorySeries(rows, key, field) {
  return (Array.isArray(rows) ? rows : [])
    .filter((row) => row?.[field] === key)
    .map((row) => ({
      ano: Number(row.ano),
      valor: detailRowValue(row, 'matriculas'),
    }))
    .filter((row) => Number.isFinite(row.ano) && !isMissing(row.valor))
    .sort((a, b) => a.ano - b.ano)
}

export function buildAgeRangeComparisonChart(data, categories, years, formatLabel, chartWidth = 1500, chartHeight = 520) {
  if (!Array.isArray(data) || !data.length || !Array.isArray(categories) || !categories.length || !Array.isArray(years) || !years.length) return null

  const width = Math.max(180, Number(chartWidth) || 1500)
  const height = Math.max(280, Number(chartHeight) || 520)
  const isNarrow = width < 600
  const padding = isNarrow
    ? { top: 36, right: 12, bottom: 44, left: 54 }
    : { top: 38, right: 16, bottom: 46, left: 62 }
  const visibleCategories = categories
    .filter((category) => data.some((row) => !isMissing(row.values?.[category.key])))
    .map((category, index) => ({ ...category, color: chartSeriesColor(index) }))
  if (!visibleCategories.length) return null

  const values = data.flatMap((row) => visibleCategories.map((category) => row.values?.[category.key]))
    .filter((value) => !isMissing(value))
    .map((value) => Number(value))
  const maxVal = Math.max(...values, 1)
  const domainMax = niceChartMax(maxVal)
  const plotW = width - padding.left - padding.right
  const plotH = height - padding.top - padding.bottom
  const slotWidth = plotW / years.length
  const groupWidth = Math.min(slotWidth * 0.9, isNarrow ? slotWidth * 0.96 : 120)
  const groupTravel = Math.max(0, plotW - groupWidth)
  const groupStep = years.length > 1 ? groupTravel / (years.length - 1) : 0
  const gap = isNarrow ? 1 : visibleCategories.length > 4 ? 4 : 7
  const barWidth = Math.max(isNarrow ? 2 : 8, Math.min(30, (groupWidth - gap * (visibleCategories.length - 1)) / visibleCategories.length))
  const yScale = (value) => padding.top + ((domainMax - value) / domainMax) * plotH

  const rows = data.map((row, rowIndex) => {
    const xBase = years.length > 1
      ? padding.left + rowIndex * groupStep
      : padding.left + groupTravel / 2
    return {
      year: row.year,
      x: xBase,
      width: groupWidth,
      bars: visibleCategories.map((category, categoryIndex) => {
        const value = row.values?.[category.key]
        const numeric = Number(value)
        const y = !isMissing(value) ? yScale(numeric) : yScale(0)
        const height = !isMissing(value) ? Math.max(1, yScale(0) - y) : 0
        return {
          key: category.key,
          category: category.label,
          color: category.color,
          year: row.year,
          value,
          x: xBase + categoryIndex * (barWidth + gap),
          y,
          width: barWidth,
          height,
          label: isMissing(value) ? EM : formatLabel(value),
          labelX: xBase + categoryIndex * (barWidth + gap) + barWidth / 2,
          labelY: Math.max(padding.top + 12, y - 7),
        }
      }),
    }
  })

  const yTicksRaw = [0, domainMax * 0.2, domainMax * 0.4, domainMax * 0.6, domainMax * 0.8, domainMax]
  const yTicks = yTicksRaw.map((value) => ({
    label: Math.round(value).toLocaleString('pt-BR'),
    y: yScale(value),
  }))

  return { categories: visibleCategories, height, padding, rows, width, yTicks }
}

function niceChartMax(value) {
  if (!Number.isFinite(value) || value <= 0) return 1
  const power = 10 ** Math.floor(Math.log10(value))
  const scaled = value / power
  if (scaled <= 1) return power
  if (scaled <= 2) return 2 * power
  if (scaled <= 5) return 5 * power
  return 10 * power
}

export function ageRangeHistorySeries(rows, faixaEtaria) {
  return (Array.isArray(rows) ? rows : [])
    .filter((row) => row?.faixa_etaria === faixaEtaria)
    .map((row) => ({
      ano: Number(row.ano),
      valor: detailRowValue(row, 'matriculas'),
    }))
    .filter((row) => Number.isFinite(row.ano) && !isMissing(row.valor))
    .sort((a, b) => a.ano - b.ano)
}

export function formatYearList(years) {
  if (!years.length) return ''
  if (years.length === 1) return String(years[0])
  if (years.length === 2) return `${years[0]} e ${years[1]}`
  return `${years.slice(0, -1).join(', ')} e ${years.at(-1)}`
}

function detailRowsToLatestRowsByLabel(rows, labelFn, valueKey = 'valor', sortFn = null) {
  const latestByLabel = new Map()
  rows.forEach((row) => {
    const label = labelFn(row)
    const value = detailRowValue(row, valueKey)
    if (isMissing(label) || isMissing(row?.ano) || isMissing(value)) return
    const current = latestByLabel.get(label)
    if (!current || Number(row.ano) > Number(current.ano)) {
      latestByLabel.set(label, {
        ano: Number(row.ano),
        sortKey: typeof sortFn === 'function' ? sortFn(row) : null,
        value,
      })
    }
  })

  return [...latestByLabel.entries()]
    .map(([label, point]) => ({ label, value: point.value, year: point.ano, sortKey: point.sortKey }))
    .sort((a, b) => {
      if (Number.isFinite(a.sortKey) && Number.isFinite(b.sortKey)) return a.sortKey - b.sortKey
      return String(a.label).localeCompare(String(b.label), 'pt-BR')
    })
}

function faixaEtariaSortValue(label) {
  const text = String(label ?? '').toLocaleLowerCase('pt-BR')
  if (text.includes('menos')) return -1
  const match = text.match(/\d+/)
  const base = match ? Number(match[0]) : 999
  return text.includes('mais') ? base + 0.5 : base
}

function latestYearFromRows(rows) {
  const years = (Array.isArray(rows) ? rows : [])
    .map((row) => Number(row?.year ?? row?.ano))
    .filter((year) => Number.isFinite(year))
  return years.length ? Math.max(...years) : null
}

function titleWithYear(title, rows) {
  const year = latestYearFromRows(rows)
  return year ? `${title} — ${year}` : title
}

function detailRowValue(row, valueKey = 'valor') {
  return detailMetricValue(row, valueKey)
}

function detailMetricValue(row, valueKey = 'valor') {
  if (!row) return null
  return isMissing(row[valueKey]) ? row.valor : row[valueKey]
}

function buildRedeExplore(rede, cut = { cutKey: 'total', cutLabel: 'Total do município' }) {
  const series = rede.series ?? {}
  const resumo = rede.resumo_ultimo_ano ?? {}
  const detalhamentos = rede.detalhamentos ?? {}
  const dependencyKeys = dependencyCategoryKeys(series.por_dependencia)
  const titleSuffix = ` — ${cut.cutLabel}`

  if (cut.stageKey) {
    const dependencyRows = detailRowsFor(detalhamentos.por_etapa_rede, { etapa_ensino: cut.stageKey })
    const locationRows = detailRowsFor(detalhamentos.por_etapa_localizacao, { etapa_ensino: cut.stageKey })
    const dependencyKeys = dependencyKeysFromDetailRows(dependencyRows, 'escolas')
    const locationKeys = detailKeys(locationRows, 'localizacao', ['urbana', 'rural'], 'escolas')
    return [
      {
        key: `rede-${cut.stageKey}-dep`,
        type: 'stacked',
        title: `Escolas por rede${titleSuffix}`,
        categories: categoryDefinitions(dependencyKeys, depLabel, DEPENDENCY_COLORS),
        data: detailRowsToStackedRows(dependencyRows, 'dependencia', dependencyKeys, 'escolas'),
        formatLabel: formatNumber,
      },
      {
        key: `rede-${cut.stageKey}-loc`,
        type: 'stacked',
        title: `Escolas por localização${titleSuffix}`,
        categories: categoryDefinitions(locationKeys, locLabel, LOCATION_COLORS),
        data: detailRowsToStackedRows(locationRows, 'localizacao', locationKeys, 'escolas'),
        formatLabel: formatNumber,
      },
    ]
  }

  if (cut.metricKey) {
    const depRows = detailRowsToLatestRows(detalhamentos.infraestrutura_por_rede, 'dependencia', depLabel, cut.metricKey)
    const locRows = detailRowsToLatestRows(detalhamentos.infraestrutura_por_localizacao, 'localizacao', locLabel, cut.metricKey)
    return [
      { key: 'rede-infra-dep', type: 'bar', title: titleWithYear(`Infraestrutura por rede${titleSuffix}`, depRows), color: '#16713a', formatLabel: cut.metricFormat, data: depRows },
      { key: 'rede-infra-loc', type: 'bar', title: titleWithYear(`Infraestrutura por localização${titleSuffix}`, locRows), color: '#2563eb', formatLabel: cut.metricFormat, data: locRows },
    ]
  }

  if (cut.locationKey) {
    const rows = detailRowsFor(detalhamentos.por_rede_localizacao, { localizacao: cut.locationKey })
    const keys = dependencyKeysFromDetailRows(rows, 'escolas')
    return [
      { key: `rede-${cut.locationKey}-dep`, type: 'stacked', title: `Composição por rede${titleSuffix}`, categories: categoryDefinitions(keys, depLabel, DEPENDENCY_COLORS), data: detailRowsToStackedRows(rows, 'dependencia', keys, 'escolas'), formatLabel: formatNumber },
    ]
  }

  if (cut.dependencyKey) {
    const rows = detailRowsFor(detalhamentos.por_rede_localizacao, { dependencia: cut.dependencyKey })
    const keys = detailKeys(rows, 'localizacao', ['urbana', 'rural'], 'escolas')
    return [
      { key: `rede-${cut.dependencyKey}-loc`, type: 'stacked', title: `Composição por localização${titleSuffix}`, categories: categoryDefinitions(keys, locLabel, LOCATION_COLORS), data: detailRowsToStackedRows(rows, 'localizacao', keys, 'escolas'), formatLabel: formatNumber },
    ]
  }

  const etapaRows = detailRowsToLatestRows(detalhamentos.por_etapa, 'etapa_ensino', etapaLabel, 'escolas')
  const etapaFallback = !etapaRows.length && resumo.por_etapa ? entriesToRows(resumo.por_etapa, etapaLabel) : []
  const etapaData = etapaRows.length ? etapaRows : etapaFallback
  const etapaItem = etapaData.length ? {
    key: 'rede-etapa',
    type: 'bar',
    title: titleWithYear(`Escolas por etapa de ensino${titleSuffix}`, etapaRows),
    color: '#16713a',
    formatLabel: formatNumber,
    data: etapaData,
    note: 'Uma mesma escola pode ofertar mais de uma etapa; por isso, a soma por etapa pode ser maior que o total de escolas.',
  } : null

  return [
    ...(etapaItem ? [etapaItem] : []),
    { key: 'rede-dep', type: 'stacked', title: `Composição por rede${titleSuffix}`, categories: categoryDefinitions(dependencyKeys, depLabel, DEPENDENCY_COLORS), data: seriesMapToStackedRows(series.por_dependencia, dependencyKeys), formatLabel: formatNumber },
    { key: 'rede-loc', type: 'stacked', title: `Composição por localização${titleSuffix}`, categories: categoryDefinitions(['urbana', 'rural'], locLabel, LOCATION_COLORS), data: seriesMapToStackedRows(series.por_localizacao, ['urbana', 'rural']), formatLabel: formatNumber },
  ]
}

export const INFRA_METRIC_LABELS = {
  agua_potavel: SCHOOL_INFRASTRUCTURE_PUBLIC_COPY.agua_potavel.shortLabel,
  energia_eletrica: SCHOOL_INFRASTRUCTURE_PUBLIC_COPY.energia_eletrica.shortLabel,
  internet: 'Escolas com internet',
  biblioteca_sala_leitura: SCHOOL_INFRASTRUCTURE_PUBLIC_COPY.biblioteca_sala_leitura.shortLabel,
  quadra_esportes: SCHOOL_INFRASTRUCTURE_PUBLIC_COPY.quadra_esportes.shortLabel,
  esgoto_rede_publica: SCHOOL_INFRASTRUCTURE_PUBLIC_COPY.esgoto_rede_publica.shortLabel,
  internet_alunos: 'Internet disponível para alunos',
  internet_aprendizagem: 'Internet usada na aprendizagem',
  internet_comunidade: 'Internet aberta à comunidade',
  banda_larga: 'Internet banda larga',
  acesso_internet_computador: 'Acesso à internet por computador',
  acesso_internet_disp_pessoais: 'Acesso à internet por dispositivos pessoais',
  rede_local: 'Rede local de computadores',
  rede_wireless: 'Rede local sem fio',
  desktop_aluno: 'Computadores de mesa para alunos',
  comp_portatil_aluno: 'Computadores portáteis para alunos',
  tablet_aluno: 'Tablets para alunos',
  salas_climatizadas: 'Salas de aula climatizadas',
  salas_acessiveis: 'Salas de aula com acessibilidade',
}

function buildInfrastructureMetricExplore(rede, indicatorKey, formatLabel) {
  if (!rede || !INFRA_METRIC_LABELS[indicatorKey]) return []

  const infra = rede.infraestrutura ?? {}
  const metricKey = `perc_${indicatorKey}`
  const dependencyRows = detailRowsToLatestRows(
    infra.por_rede ?? [],
    'dependencia',
    depLabel,
    metricKey,
  )
  const locationRows = detailRowsToLatestRows(
    infra.por_localizacao ?? [],
    'localizacao',
    locLabel,
    metricKey,
  )
  const metricLabel = INFRA_METRIC_LABELS[indicatorKey]

  return [
    dependencyRows.length ? {
      key: `${indicatorKey}-por-rede`,
      type: 'bar',
      chartSize: 'large',
      title: titleWithYear(`${metricLabel} por rede`, dependencyRows),
      color: '#16713a',
      formatLabel,
      data: dependencyRows,
    } : null,
    locationRows.length ? {
      key: `${indicatorKey}-por-localizacao`,
      type: 'bar',
      chartSize: 'large',
      title: titleWithYear(`${metricLabel} por localização`, locationRows),
      color: '#2563eb',
      formatLabel,
      data: locationRows,
    } : null,
  ].filter(Boolean)
}

function buildRedeInfraExplore(rede) {
  const infra = rede.infraestrutura ?? {}
  const detalhamentos = rede.detalhamentos ?? {}

  const infraPorRede = infra.por_rede ?? detalhamentos.infraestrutura_por_rede ?? []
  const redeTab = buildInfraDimensionTab(
    infraPorRede, 'dependencia', depLabel,
    'rede-infra-por-rede', 'Indicadores de infraestrutura por dependência administrativa',
    'Por rede', 0,
  )

  const infraPorLoc = infra.por_localizacao ?? detalhamentos.infraestrutura_por_localizacao ?? []
  const locTab = buildInfraDimensionTab(
    infraPorLoc, 'localizacao', locLabel,
    'rede-infra-por-localizacao', 'Indicadores de infraestrutura por localização',
    'Por localização', 1,
  )

  return [redeTab, locTab].filter(Boolean)
}

function buildInfraDimensionTab(rawRows, dimKey, dimLabelFn, itemKey, title, tabLabel, tabPriority) {
  if (!Array.isArray(rawRows) || !rawRows.length) return null

  const dims = [...new Set(rawRows.map((r) => r[dimKey]).filter(Boolean))]
  if (!dims.length) return null

  // Metricas disponiveis: tentar as mais comuns primeiro
  const metricCandidates = ['perc_internet', 'perc_banda_larga', 'perc_rede_local',
    'perc_rede_wireless', 'perc_desktop_aluno', 'perc_comp_portatil_aluno',
    'perc_tablet_aluno', 'perc_internet_alunos', 'perc_internet_aprendizagem',
    'perc_internet_comunidade', 'perc_acesso_internet_computador',
    'perc_acesso_internet_disp_pessoais', 'perc_salas_climatizadas', 'perc_salas_acessiveis']
  const availableMetrics = metricCandidates.filter((mk) =>
    rawRows.some((r) => !isMissing(r[mk]))
  )
  if (!availableMetrics.length) return null

  const metricLabels = {
    perc_internet: 'Internet', perc_banda_larga: 'Banda larga',
    perc_rede_local: 'Rede local', perc_rede_wireless: 'Rede sem fio',
    perc_desktop_aluno: 'Desktop', perc_comp_portatil_aluno: 'Portátil',
    perc_tablet_aluno: 'Tablet', perc_internet_alunos: 'Internet (alunos)',
    perc_internet_aprendizagem: 'Internet (aprendizagem)',
    perc_internet_comunidade: 'Internet (comunidade)',
    perc_acesso_internet_computador: 'Acesso por computador',
    perc_acesso_internet_disp_pessoais: 'Acesso por disp. pessoais',
    perc_salas_climatizadas: 'Salas climatizadas',
    perc_salas_acessiveis: 'Salas acessíveis',
  }

  const columns = [
    { key: 'dimensao', label: dimKey === 'dependencia' ? 'Rede' : 'Localização' },
    ...availableMetrics.map((mk) => ({ key: mk, label: metricLabels[mk] ?? mk, format: formatPercent })),
  ]

  const rows = dims.map((dim) => {
    const dimRows = rawRows.filter((r) => r[dimKey] === dim)
    const latest = dimRows.reduce((a, b) => Number(a.ano) > Number(b.ano) ? a : b, dimRows[0])
    const row = { dimensao: dimLabelFn(dim) }
    for (const mk of availableMetrics) {
      row[mk] = !isMissing(latest[mk]) ? latest[mk] : null
    }
    return row
  })

  return {
    key: itemKey,
    type: 'table',
    title,
    tabLabel,
    tabPriority,
    columns,
    rows,
  }
}

function alunosTurmaSerieLabel(key, fallback) {
  return ALUNOS_TURMA_SERIE_LABELS[key] ?? fallback ?? key
}

function alunosTurmaLatestSerieRows(rows) {
  const latestBySerie = new Map()
  rows.forEach((row) => {
    const key = row?.serie
    const value = detailRowValue(row, 'alunos_por_turma')
    if (isMissing(key) || isMissing(row?.ano) || isMissing(value)) return
    const current = latestBySerie.get(key)
    if (!current || Number(row.ano) > Number(current.ano)) {
      latestBySerie.set(key, {
        ano: Number(row.ano),
        label: alunosTurmaSerieLabel(key, row.serie_label),
        order: Number(row.serie_ordem ?? 999),
        value,
      })
    }
  })

  return [...latestBySerie.values()]
    .sort((a, b) => a.order - b.order)
    .map((row) => ({ label: row.label, value: row.value, year: row.ano }))
}

function buildAlunosTurmaExplore(alunosTurma, cut = { stageKey: 'fundamental', serieKey: 'fundamental_total', serieLabel: 'Total - Ensino Fundamental' }) {
  const detalhamentos = alunosTurma.detalhamentos ?? {}
  const titleSuffix = ` — ${cut.serieLabel}`
  const serieRows = alunosTurmaLatestSerieRows(
    detailRowsFor(detalhamentos.por_serie, { etapa_ensino: cut.stageKey }),
  )
  const dependencyRows = detailRowsFor(detalhamentos.por_serie_rede, { serie: cut.serieKey })
    .filter((row) => row.dependencia !== 'total')
  const locationRows = detailRowsFor(detalhamentos.por_serie_localizacao, { serie: cut.serieKey })
    .filter((row) => row.localizacao !== 'total')
  const dependencyLatest = detailRowsToLatestRows(dependencyRows, 'dependencia', depLabel, 'alunos_por_turma')
  const locationLatest = detailRowsToLatestRows(locationRows, 'localizacao', locLabel, 'alunos_por_turma')

  const items = [
    serieRows.length ? {
      key: 'alunos-turma-series',
      type: 'bar',
      chartSize: 'large',
      title: titleWithYear(`Média de alunos por turma por série — ${etapaLabel(cut.stageKey)}`, serieRows),
      color: '#16713a',
      formatLabel: formatRatio,
      preserveOrder: true,
      data: serieRows,
      tabLabel: 'Por série',
      tabPriority: 1,
    } : null,
    dependencyLatest.length ? {
      key: 'alunos-turma-rede',
      type: 'bar',
      chartSize: 'large',
      title: titleWithYear(`Média de alunos por turma por rede${titleSuffix}`, dependencyLatest),
      color: '#2563eb',
      formatLabel: formatRatio,
      data: dependencyLatest,
      tabLabel: 'Por rede',
      tabPriority: 2,
    } : null,
    locationLatest.length ? {
      key: 'alunos-turma-localizacao',
      type: 'bar',
      chartSize: 'large',
      title: titleWithYear(`Média de alunos por turma por localização${titleSuffix}`, locationLatest),
      color: '#7c3aed',
      formatLabel: formatRatio,
      data: locationLatest,
      tabLabel: 'Por localização',
      tabPriority: 3,
    } : null,
  ].filter(Boolean)

  if (cut.stageKey === 'fundamental') {
    return items.map((item) => item.key === 'alunos-turma-series'
      ? { ...item, orientation: 'vertical', supportLayout: 'full' }
      : item)
  }

  return items.length === 3
    ? items.map((item) => ({ ...item, supportLayout: 'third' }))
    : items
}

export function buildTurmasExplore(turmas, cut = { cutLabel: 'Total do município', metricKey: 'turmas', formatLabel: formatNumber }) {
  const detalhamentos = turmas.detalhamentos ?? {}
  const series = turmas.series ?? {}
  const isCountMetric = ['turmas', 'docentes', 'matriculas'].includes(cut.metricKey)
  const titleBase = turmasMetricLabel(cut.metricKey)
  const titleSuffix = ` — ${cut.cutLabel}`

  if (cut.stageKey) {
    const dependencyRows = detailRowsFor(detalhamentos.por_etapa_rede, { etapa_ensino: cut.stageKey })
    const locationRows = detailRowsFor(detalhamentos.por_etapa_localizacao, { etapa_ensino: cut.stageKey })
    const dependencyKeys = dependencyKeysFromDetailRows(dependencyRows, cut.metricKey)
    const locationKeys = detailKeys(locationRows, 'localizacao', ['urbana', 'rural'], cut.metricKey)

    const stageLast = normalizeYearSeries(series.por_etapa?.[cut.stageKey]).at(-1)
    const contextItem = cut.metricKey === 'turmas' && stageLast ? {
      key: `turmas-${cut.stageKey}-context`,
      type: 'stage-context',
      tabLabel: 'Resumo',
      tabPriority: 0,
      value: stageLast[cut.metricKey],
      valueLabel: titleBase,
      alunosPorTurma: stageLast.alunos_por_turma,
      docentes: stageLast.docentes,
      ano: stageLast.ano,
      formatLabel: cut.formatLabel,
    } : null

    if (isCountMetric) {
      return [
        ...(contextItem ? [contextItem] : []),
        ...(dependencyKeys.length ? [{ key: `turmas-${cut.stageKey}-rede`, type: 'stacked', title: `${titleBase} por rede${titleSuffix}`, categories: categoryDefinitions(dependencyKeys, depLabel, DEPENDENCY_COLORS), data: detailRowsToStackedRows(dependencyRows, 'dependencia', dependencyKeys, cut.metricKey), formatLabel: cut.formatLabel }] : []),
        ...(locationKeys.length ? [{ key: `turmas-${cut.stageKey}-localizacao`, type: 'stacked', title: `${titleBase} por localização${titleSuffix}`, categories: categoryDefinitions(locationKeys, locLabel, LOCATION_COLORS), data: detailRowsToStackedRows(locationRows, 'localizacao', locationKeys, cut.metricKey), formatLabel: cut.formatLabel }] : []),
      ]
    }
    const dependencyLatest = detailRowsToLatestRows(dependencyRows, 'dependencia', depLabel, cut.metricKey)
    const locationLatest = detailRowsToLatestRows(locationRows, 'localizacao', locLabel, cut.metricKey)
    return [
      ...(contextItem ? [contextItem] : []),
      ...(dependencyLatest.length ? [{ key: `turmas-${cut.stageKey}-rede`, type: 'bar', title: titleWithYear(`${titleBase} por rede${titleSuffix}`, dependencyLatest), color: '#2563eb', formatLabel: cut.formatLabel, data: dependencyLatest }] : []),
      ...(locationLatest.length ? [{ key: `turmas-${cut.stageKey}-localizacao`, type: 'bar', title: titleWithYear(`${titleBase} por localização${titleSuffix}`, locationLatest), color: '#7c3aed', formatLabel: cut.formatLabel, data: locationLatest }] : []),
    ]
  }

  const etapaFromDetalhamento = detailRowsToLatestRows(detalhamentos.por_etapa, 'etapa_ensino', etapaLabel, cut.metricKey)
  const etapaFromSeries = seriesPorEtapaToLatestRows(series.por_etapa, cut.metricKey)
  const etapaBarData = etapaFromDetalhamento.length ? etapaFromDetalhamento : etapaFromSeries

  const panorama = isCountMetric ? buildEtapaPanorama(series.por_etapa, cut.metricKey, turmas.ultimo_ano) : null

  const etapaStacked = seriesPorEtapaToStackedRows(series.por_etapa, cut.metricKey)
  const hasEtapaHistory = !!etapaStacked && etapaStacked.data.length >= 2

  const etapaItem = etapaBarData.length ? {
    key: 'turmas-etapa',
    type: isCountMetric ? 'stage-detail' : 'bar',
    title: titleWithYear(`${titleBase} por etapa de ensino${titleSuffix}`, etapaBarData),
    ...(isCountMetric ? {
      distributionData: etapaBarData,
      distributionColor: '#16713a',
      formatLabel: cut.formatLabel,
      ...(hasEtapaHistory ? {
        historyCategories: etapaStacked.categories,
        historyData: etapaStacked.data,
        historyTitle: `Histórico do indicador — ${titleBase} por etapa${titleSuffix}`,
      } : {}),
      panoramaColumns: panorama?.columns,
      panoramaRows: panorama?.rows,
      panoramaTitle: panorama?.title,
    } : {
      color: '#16713a',
      formatLabel: cut.formatLabel,
      data: etapaBarData,
    }),
  } : null

  const dependencyKeys = dependencyKeysFromDetailRows(detalhamentos.por_rede, cut.metricKey)
  const locationKeys = detailKeys(detalhamentos.por_localizacao, 'localizacao', ['urbana', 'rural'], cut.metricKey)

  if (isCountMetric) {
    return [
      ...(etapaItem ? [etapaItem] : []),
      ...(dependencyKeys.length ? [{ key: 'turmas-rede', type: 'stacked', title: `${titleBase} por rede${titleSuffix}`, categories: categoryDefinitions(dependencyKeys, depLabel, DEPENDENCY_COLORS), data: detailRowsToStackedRows(detalhamentos.por_rede, 'dependencia', dependencyKeys, cut.metricKey), formatLabel: cut.formatLabel }] : []),
      ...(locationKeys.length ? [{ key: 'turmas-localizacao', type: 'stacked', title: `${titleBase} por localização${titleSuffix}`, categories: categoryDefinitions(locationKeys, locLabel, LOCATION_COLORS), data: detailRowsToStackedRows(detalhamentos.por_localizacao, 'localizacao', locationKeys, cut.metricKey), formatLabel: cut.formatLabel }] : []),
    ]
  }

  const dependencyLatest = detailRowsToLatestRows(detalhamentos.por_rede, 'dependencia', depLabel, cut.metricKey)
  const locationLatest = detailRowsToLatestRows(detalhamentos.por_localizacao, 'localizacao', locLabel, cut.metricKey)
  return [
    ...(etapaItem ? [etapaItem] : []),
    ...(dependencyLatest.length ? [{ key: 'turmas-rede', type: 'bar', title: titleWithYear(`${titleBase} por rede${titleSuffix}`, dependencyLatest), color: '#2563eb', formatLabel: cut.formatLabel, data: dependencyLatest }] : []),
    ...(locationLatest.length ? [{ key: 'turmas-localizacao', type: 'bar', title: titleWithYear(`${titleBase} por localização${titleSuffix}`, locationLatest), color: '#7c3aed', formatLabel: cut.formatLabel, data: locationLatest }] : []),
  ]
}

function turmasMetricLabel(metricKey) {
  if (metricKey === 'docentes') return 'Docentes'
  if (metricKey === 'alunos_por_turma') return 'Média de alunos por turma'
  if (metricKey === 'alunos_por_docente') return 'Alunos por docente'
  return 'Turmas'
}

function buildFluxoExplore(fluxo, cut = { cutLabel: 'Ensino Fundamental', stageKey: 'fundamental', metricKey: 'taxa_aprovacao' }) {
  const detalhamentos = fluxo.detalhamentos ?? {}
  const stageRows = detailRowsFor(detalhamentos.por_etapa_rede, { etapa_ensino: cut.stageKey })
  const locationRows = detailRowsFor(detalhamentos.por_etapa_localizacao, { etapa_ensino: cut.stageKey })
  const locKeys = detailKeys(locationRows, 'localizacao', ['urbana', 'rural'], cut.metricKey)
  const titleSuffix = ` — ${cut.cutLabel}`
  const dependencyLatest = detailRowsToLatestRows(stageRows, 'dependencia', depLabel, cut.metricKey)
  const etapaLatest = detailRowsToLatestRows(detalhamentos.por_etapa, 'etapa_ensino', etapaLabel, cut.metricKey)
  const items = [
    { key: 'fluxo-dep', type: 'bar', chartSize: 'large', title: titleWithYear(`Taxa por rede${titleSuffix}`, dependencyLatest), color: '#2563eb', formatLabel: formatPercent, data: dependencyLatest },
  ]
  if (!cut.noLocation) {
    const locationLatest = detailRowsToLatestRows(locationRows.filter((row) => locKeys.includes(row.localizacao)), 'localizacao', locLabel, cut.metricKey)
    items.push({ key: 'fluxo-loc', type: 'bar', chartSize: 'large', title: titleWithYear(`Taxa por localização${titleSuffix}`, locationLatest), color: '#7c3aed', formatLabel: formatPercent, data: locationLatest })
  }
  if (etapaLatest.length) {
    items.push({ key: 'fluxo-etapa', type: 'bar', chartSize: 'large', title: titleWithYear(`Taxa por etapa`, etapaLatest), color: '#16713a', formatLabel: formatPercent, data: etapaLatest })
  }
  return items.length === 3
    ? items.map((item) => ({ ...item, supportLayout: 'third' }))
    : items
}

function buildAprendizagemExplore(aprend, metric) {
  const detalhamentos = aprend.detalhamentos ?? {}
  if (metric.stageKey) {
    const dependencyRows = detailRowsFor(detalhamentos.por_etapa_rede, { etapa_ensino: metric.stageKey })
    const dependencyLatest = detailRowsToLatestRows(dependencyRows, 'dependencia', depLabel, metric.metricKey)
    return [
      { key: `apr-${metric.metricKey}-${metric.stageKey}-rede`, type: 'bar', chartSize: 'large', title: titleWithYear(`${metric.metricLabel} por rede — ${metric.cutLabel}`, dependencyLatest), data: dependencyLatest, color: '#2563eb', formatLabel: metric.formatLabel },
    ]
  }
  const etapaRows = detailRowsToLatestRows(detalhamentos.por_etapa, 'etapa_ensino', etapaLabel, metric.metricKey)
  const redeRows = detailRowsToLatestRows(detalhamentos.por_rede, 'dependencia', depLabel, metric.metricKey)
  return [
    { key: `apr-${metric.metricKey}-etapa`, type: 'bar', chartSize: 'large', title: titleWithYear(`${metric.metricLabel} por etapa`, etapaRows), data: etapaRows, color: '#16713a', formatLabel: metric.formatLabel },
    { key: `apr-${metric.metricKey}-rede`, type: 'bar', chartSize: 'large', title: titleWithYear(`${metric.metricLabel} por rede`, redeRows), data: redeRows, color: '#2563eb', formatLabel: metric.formatLabel },
  ]
}

function buildOfertaExplore(oferta) {
  const detalhamentos = oferta.detalhamentos ?? {}
  const redeRows = detalhamentos.por_rede ?? []
  const redeKeys = dependencyKeysFromDetailRows(redeRows, 'matriculas')
  const modalidadeRows = detalhamentos.por_modalidade ?? []
  const faixaRows = detalhamentos.por_faixa_etaria ?? []
  const redeTitle = redeKeys.length === 1 && redeKeys[0] === 'publica'
    ? 'Matrículas técnicas por rede — histórico (recorte disponível: Pública)'
    : 'Matrículas técnicas por rede — histórico'
  return [
    redeKeys.length ? {
      key: 'oferta-rede',
      type: 'stacked',
      title: redeTitle,
      categories: categoryDefinitions(redeKeys, depLabel, DEPENDENCY_COLORS),
      data: detailRowsToStackedRows(redeRows, 'dependencia', redeKeys, 'matriculas'),
      formatLabel: formatNumber,
      tabPriority: 1,
    } : null,
    {
      key: 'oferta-mod',
      type: 'modality-range',
      title: 'Matrículas por modalidade',
      rows: modalidadeRows,
      historyColor: '#7c3aed',
      formatLabel: formatNumber,
      tabPriority: 2,
    },
    {
      key: 'oferta-faixa',
      type: 'age-range',
      title: 'Matrículas técnicas por faixa etária',
      rows: faixaRows,
      stageLabel: 'Educação técnica/profissional',
      historyStageLabel: 'Educação técnica/profissional',
      comparisonTitlePrefix: 'Matrículas técnicas por faixa etária',
      historyColor: '#2563eb',
      formatLabel: formatNumber,
      tabPriority: 3,
    },
  ].filter(Boolean)
}

function valueSeries(series, key) {
  return normalizeYearSeries(Array.isArray(series) ? series.map((point) => ({ ano: point.ano, valor: point[key] })) : [])
}

export function safeValueSeries(raw, metricKey) {
  if (!Array.isArray(raw)) return []
  if (metricKey === 'alunos_por_docente') {
    const points = raw.map((point) => {
      if (!isMissing(point.alunos_por_docente)) {
        return { ano: point.ano, valor: point.alunos_por_docente }
      }
      const turmas = point.turmas
      const alunosPorTurma = point.alunos_por_turma
      const docentes = point.docentes
      if (!isMissing(turmas) && !isMissing(alunosPorTurma) && !isMissing(docentes) && Number(docentes) > 0) {
        return { ano: point.ano, valor: (Number(turmas) * Number(alunosPorTurma)) / Number(docentes) }
      }
      return null
    }).filter(Boolean)
    return normalizeYearSeries(points)
  }
  return valueSeries(raw, metricKey)
}

function latestValue(series, key) {
  return valueSeries(series, key).at(-1)?.valor ?? null
}

function entriesToRows(source, labelFn) {
  return Object.entries(source ?? {}).map(([key, value]) => ({ label: labelFn(key), value })).filter((row) => !isMissing(row.value))
}

function dependencyCategoryKeys(source) {
  const detailedKeys = ['federal', 'estadual', 'municipal', 'privada']
    .filter((key) => hasSeriesData(source?.[key]))
  if (detailedKeys.length) return detailedKeys
  return ['publica', 'privada'].filter((key) => hasSeriesData(source?.[key]))
}

function hasSeriesData(series, valueKey = 'valor') {
  return normalizeYearSeries(series, valueKey).some((point) => !isMissing(point[valueKey]))
}

function categoryDefinitions(keys, labelFn, colors) {
  return keys.map((key) => ({ key, label: labelFn(key), color: colors[key] ?? '#16713a' }))
}

function seriesMapToStackedRows(source, keys, valueKey = 'valor') {
  const years = new Set()
  keys.forEach((key) => {
    normalizeYearSeries(source?.[key]).forEach((point) => {
      if (!isMissing(point[valueKey]) && point.ano) years.add(Number(point.ano))
    })
  })
  return [...years].sort((a, b) => a - b).map((year) => {
    const values = {}
    keys.forEach((key) => {
      const point = normalizeYearSeries(source?.[key]).find((item) => Number(item.ano) === year)
      if (point && !isMissing(point[valueKey])) values[key] = point[valueKey]
    })
    return { year, values }
  })
}

function seriesPorEtapaToLatestRows(source, metricKey) {
  const keys = Object.keys(source ?? {})
  return keys
    .map((key) => {
      const s = normalizeYearSeries(source[key], metricKey)
      const last = s.at(-1)
      if (!last || isMissing(last[metricKey])) return null
      return { label: etapaLabel(key), value: last[metricKey], year: last.ano }
    })
    .filter(Boolean)
}

function seriesPorEtapaToStackedRows(source, metricKey) {
  const keys = orderedStageKeys(source, metricKey)
  if (!keys.length) return null
  return {
    categories: categoryDefinitions(keys, etapaLabel, CATEGORY_COMPARISON_COLORS),
    data: seriesMapToStackedRows(source, keys, metricKey),
  }
}

function buildEtapaPanorama(porEtapa, metricKey, ultimoAno) {
  const stages = orderedStageKeys(porEtapa, metricKey)
  if (!stages.length) return null
  const metricLabel = turmasMetricLabel(metricKey)

  const rows = stages.map((key) => {
    const s = normalizeYearSeries(porEtapa[key])
    const last = s.at(-1)
    if (!last || isMissing(last[metricKey])) return null
    const first = s[0]
    const currentTurmas = last[metricKey]
    let variacao = EM
    if (first && !isMissing(first[metricKey]) && Number(first[metricKey]) !== 0) {
      const diff = Number(currentTurmas) - Number(first[metricKey])
      const pct = (diff / Math.abs(Number(first[metricKey]))) * 100
      variacao = `${pct >= 0 ? '+' : ''}${formatPercent(pct)}`
    }
    return {
      etapa: etapaLabel(key),
      valor: formatNumber(currentTurmas),
      alunos_por_turma: !isMissing(last.alunos_por_turma) ? formatRatio(last.alunos_por_turma) : EM,
      variacao,
    }
  }).filter(Boolean)

  if (!rows.length) return null

  return {
    columns: [
      { key: 'etapa', label: 'Etapa' },
      { key: 'valor', label: metricLabel },
      { key: 'alunos_por_turma', label: 'Média de alunos por turma' },
      { key: 'variacao', label: 'Variação' },
    ],
    rows,
    title: `Panorama por etapa de ensino${ultimoAno ? ` — ${ultimoAno}` : ''}`,
  }
}

function inferScaleType(config) {
  if (config.scaleType) return config.scaleType
  if (config.formatType === 'percent') return 'percent'
  if (config.key?.includes('ideb')) return 'ideb'
  if (config.key?.includes('saeb')) return 'saeb'
  if (config.key?.includes('inse')) return 'inse'
  if (config.formatType === 'ratio' || config.formatType === 'value') return 'dynamic'
  return 'count'
}

function getFormatter(formatType) {
  if (formatType === 'percent') return formatPercent
  if (formatType === 'ratio') return formatRatio
  if (formatType === 'value') return formatValue
  return formatNumber
}

export function calculateVariation(initialValue, currentValue, formatType) {
  if (isMissing(initialValue) || isMissing(currentValue)) return { display: EM, tone: 'muted', raw: null }
  const diff = Number(currentValue) - Number(initialValue)
  if (formatType === 'percent') return { display: `${diff > 0 ? '+' : ''}${formatValue(diff)} p.p.`, tone: diff > 0 ? 'success' : diff < 0 ? 'warning' : 'muted', raw: diff }
  if (Number(initialValue) === 0) return { display: diff === 0 ? '0' : `${diff > 0 ? '+' : ''}${getFormatter(formatType)(diff)}`, tone: diff > 0 ? 'success' : diff < 0 ? 'warning' : 'muted', raw: diff }
  const percent = (diff / Math.abs(Number(initialValue))) * 100
  return { display: `${percent > 0 ? '+' : ''}${formatPercent(percent)}`, tone: diff > 0 ? 'success' : diff < 0 ? 'warning' : 'muted', raw: percent }
}

function getIndicatorStatus(currentValue, series, variation) {
  if (isMissing(currentValue)) return { label: 'Sem dados', tone: 'muted' }
  if (series.length < 2 || variation?.raw === null) return { label: 'Com dados', tone: 'info' }
  if (variation.raw > 0) return { label: 'Alta', tone: 'success' }
  if (variation.raw < 0) return { label: 'Queda', tone: 'warning' }
  return { label: 'Estável', tone: 'muted' }
}

function buildQuickReading({ currentDisplay, currentValue, currentYear, formatType, initialValue, initialYear, label, variation }) {
  if (isMissing(currentValue)) return `Não há dado recente disponível para ${label.toLocaleLowerCase('pt-BR')}.`
  if (isMissing(initialValue) || !initialYear || !currentYear || variation.raw === null) return 'Não há série histórica suficiente para exibir o histórico do indicador.'
  const movement = variation.raw > 0 ? 'aumento' : variation.raw < 0 ? 'redução' : 'estabilidade'
  const variationText = formatType === 'percent' ? variation.display : variation.display.replace('+', '')
  return `Em ${currentYear}, o município registra ${currentDisplay}. Em relação a ${initialYear}, houve ${movement} de ${variationText}.`
}

function getPreferredIdeb(resumo) {
  return Object.entries(resumo)
    .filter(([key, value]) => key.startsWith('ideb_') && !isMissing(value))
    .map(([key, ideb]) => {
      const etapa = key.replace('ideb_', '')
      return { etapa, ideb, ano: resumo[`ano_ideb_${etapa}`], saeb_lp: resumo[`saeb_lp_${etapa}`], saeb_mt: resumo[`saeb_mt_${etapa}`] }
    })
    .sort((a, b) => Number(b.ano ?? 0) - Number(a.ano ?? 0))[0] ?? null
}
