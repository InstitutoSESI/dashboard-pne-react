import type {
  AvailabilityState,
  UiV2Series,
  VocacoesPneLoadedBundle,
} from './vocacoesPneUiV2Types'
import type {
  Job5KEndpoint,
  Job5KEjaStory,
  Job5KHighSchoolStory,
  Job5KLogisticsStory,
  Job5KStory,
  Job5KYouthStory,
} from './vocacoesPneJob5kTypes'
import {
  REGION_ENTITY_ID,
  findSeries,
  firstObservedPoint,
  latestObservedPoint,
} from './vocacoesPneSelectors'
import { storyVariant } from './vocacoesPneJob5kRuntime'
import { assertVocacoesPnePrototypeLanguage } from './vocacoesPneLanguageLinter'

export type ManagerReviewDirectionId =
  | 'education-to-territory'
  | 'territory-to-education'

export type ManagerReviewEvidenceClass =
  | 'structural-contrast'
  | 'territorial-mismatch'
  | 'tested-without-stable-pattern'
  | 'statistical-context'
  | 'descriptive-planning-signal'

export interface ManagerReviewEvidenceProfile {
  evidenceClass: ManagerReviewEvidenceClass
  evidenceLabel: string
  evidenceSummary: string
  mechanism: string
}

export interface ManagerReviewEvidence {
  id: string
  label: string
  value: string
  detail: string
  period: string
  lens: string
  availabilityState: AvailabilityState
  comparison: string | null
  series: UiV2Series | null
}

export interface ManagerReviewCard extends ManagerReviewEvidenceProfile {
  id: string
  directionId: ManagerReviewDirectionId
  sequence: number
  eyebrow: string
  title: string
  answer: string
  connector: string
  educationLabel: string
  territoryLabel: string
  educationEvidence: ManagerReviewEvidence[]
  territoryEvidence: ManagerReviewEvidence[]
  planningQuestion: string
  responsibility: string
  pneTopics: string[]
  monitoringIndicators: string[]
  sourceRefs: string[]
  interpretationBoundary: string
}

export interface ManagerReviewSupportingRelation extends ManagerReviewEvidenceProfile {
  id: string
  eyebrow: string
  title: string
  answer: string
  evidence: ManagerReviewEvidence[]
  planningQuestion: string
  responsibility: string
  monitoringIndicators: string[]
  sourceRefs: string[]
  interpretationBoundary: string
}

export interface ManagerReviewPriority {
  id: string
  label: string
  title: string
  summary: string
  figures: Array<{ label: string; value: string; period: string }>
  responsibility: string
  href: string
}

export interface ManagerReviewModel {
  entityId: string
  entityName: string
  isRegion: boolean
  priorities: ManagerReviewPriority[]
  supportingRelations: ManagerReviewSupportingRelation[]
  directions: Array<{
    id: ManagerReviewDirectionId
    sequence: number
    title: string
    question: string
    summary: string
    cards: ManagerReviewCard[]
  }>
}

const numberFormatter = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 0 })
const decimalFormatter = new Intl.NumberFormat('pt-BR', {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
})

function invariant<T>(value: T | null | undefined, message: string): T {
  if (value === null || value === undefined) throw new TypeError(`Página da gestora inválida: ${message}`)
  return value
}

function storyById<T extends Job5KStory['story_id']>(
  bundle: VocacoesPneLoadedBundle,
  storyId: T,
): Extract<Job5KStory, { story_id: T }> {
  return invariant(
    bundle.insights.stories.find((item) => item.story_id === storyId),
    `história ${storyId} ausente`,
  ) as Extract<Job5KStory, { story_id: T }>
}

function seriesByQuery(
  bundle: VocacoesPneLoadedBundle,
  familyId: string,
  entityId: string,
  metricId: string,
  educationalStage?: string,
  ageGroup?: string,
): UiV2Series {
  return invariant(findSeries(bundle.series, {
    familyId,
    entityId,
    metricId,
    educationalStage,
    ageGroup,
  }), `${familyId}/${entityId}/${metricId}/${educationalStage ?? ''}/${ageGroup ?? ''}`)
}

function formatValue(value: number, unit: string): string {
  if (unit === 'percent') return `${decimalFormatter.format(value)}%`
  if (unit === 'ratio') return decimalFormatter.format(value)
  return numberFormatter.format(value)
}

function formatSigned(value: number, unit: string): string {
  const sign = value > 0 ? '+' : value < 0 ? '−' : ''
  const absolute = Math.abs(value)
  if (unit === 'percent') return `${sign}${decimalFormatter.format(absolute)} p.p.`
  return `${sign}${numberFormatter.format(absolute)}`
}

function endpointText(endpoint: Job5KEndpoint): string {
  const initial = invariant(endpoint.initial_value, `${endpoint.series_id}.initial_value`)
  const final = invariant(endpoint.final_value, `${endpoint.series_id}.final_value`)
  return `${formatValue(initial, endpoint.unit)} → ${formatValue(final, endpoint.unit)}`
}

function seriesEvidence({
  id,
  label,
  series,
  comparisonSeries = null,
  lens,
}: {
  id: string
  label: string
  series: UiV2Series
  comparisonSeries?: UiV2Series | null
  lens: string
}): ManagerReviewEvidence {
  const first = invariant(firstObservedPoint(series), `${series.seriesId}.primeiro ponto observado`)
  const last = invariant(latestObservedPoint(series), `${series.seriesId}.último ponto observado`)
  const comparison = comparisonSeries
    ? (() => {
      const comparisonFirst = invariant(firstObservedPoint(comparisonSeries), `${comparisonSeries.seriesId}.primeiro ponto observado`)
      const comparisonLast = invariant(latestObservedPoint(comparisonSeries), `${comparisonSeries.seriesId}.último ponto observado`)
      return `Vale do Sinos: ${formatValue(invariant(comparisonFirst.value, comparisonSeries.seriesId), comparisonSeries.unit)} → ${formatValue(invariant(comparisonLast.value, comparisonSeries.seriesId), comparisonSeries.unit)}`
    })()
    : null
  const firstValue = invariant(first.value, `${series.seriesId}.${first.year}`)
  const lastValue = invariant(last.value, `${series.seriesId}.${last.year}`)
  return {
    id,
    label,
    value: `${formatValue(firstValue, series.unit)} → ${formatValue(lastValue, series.unit)}`,
    detail: `${formatSigned(lastValue - firstValue, series.unit)} no período`,
    period: `${first.year}–${last.year}`,
    lens,
    availabilityState: last.availabilityState,
    comparison,
    series,
  }
}

function pluralSeriesMovement(series: UiV2Series): 'cresceram' | 'diminuíram' | 'permaneceram estáveis' {
  const first = invariant(firstObservedPoint(series), `${series.seriesId}.primeiro ponto observado`)
  const last = invariant(latestObservedPoint(series), `${series.seriesId}.último ponto observado`)
  const firstValue = invariant(first.value, `${series.seriesId}.${first.year}`)
  const lastValue = invariant(last.value, `${series.seriesId}.${last.year}`)
  if (lastValue > firstValue) return 'cresceram'
  if (lastValue < firstValue) return 'diminuíram'
  return 'permaneceram estáveis'
}

function endpointEvidence({
  id,
  label,
  endpoint,
  lens,
  comparison = null,
}: {
  id: string
  label: string
  endpoint: Job5KEndpoint
  lens: string
  comparison?: string | null
}): ManagerReviewEvidence {
  const initialYear = invariant(endpoint.initial_year, `${endpoint.series_id}.initial_year`)
  const finalYear = invariant(endpoint.final_year, `${endpoint.series_id}.final_year`)
  const absoluteChange = invariant(endpoint.absolute_change, `${endpoint.series_id}.absolute_change`)
  return {
    id,
    label,
    value: endpointText(endpoint),
    detail: `${formatSigned(absoluteChange, endpoint.unit)} no período`,
    period: `${initialYear}–${finalYear}`,
    lens,
    availabilityState: endpoint.availability_state,
    comparison,
    series: null,
  }
}

function snapshotEvidence({
  id,
  label,
  value,
  unit = 'percent',
  detail,
  period,
  lens,
  availabilityState = value === 0 ? 'observed_zero' : 'observed',
  comparison = null,
}: {
  id: string
  label: string
  value: number
  unit?: string
  detail: string
  period: string
  lens: string
  availabilityState?: AvailabilityState
  comparison?: string | null
}): ManagerReviewEvidence {
  return {
    id,
    label,
    value: formatValue(value, unit),
    detail,
    period,
    lens,
    availabilityState,
    comparison,
    series: null,
  }
}

function pairedShareEvidence({
  id,
  label,
  first,
  second,
  detail,
  period,
  lens,
}: {
  id: string
  label: string
  first: number
  second: number
  detail: string
  period: string
  lens: string
}): ManagerReviewEvidence {
  return {
    id,
    label,
    value: `${decimalFormatter.format(first)}% / ${decimalFormatter.format(second)}%`,
    detail,
    period,
    lens,
    availabilityState: first === 0 && second === 0 ? 'observed_zero' : 'observed',
    comparison: null,
    series: null,
  }
}

function sourceRefsForFamily(bundle: VocacoesPneLoadedBundle, familyId: string): string[] {
  return invariant(
    bundle.core.families.find((item) => item.storyFamilyId === familyId),
    `família ${familyId} ausente`,
  ).sourceRefs
}

function unique(values: readonly string[]): string[] {
  return [...new Set(values)]
}

export function buildVocacoesPneManagerReviewModel(
  bundle: VocacoesPneLoadedBundle,
  municipalityEntityId: string | null,
  municipalityName: string | null,
): ManagerReviewModel {
  const entityId = municipalityEntityId ?? REGION_ENTITY_ID
  const isRegion = entityId === REGION_ENTITY_ID
  const entityName = municipalityName ?? bundle.core.region.name
  const comparisonEntityId = REGION_ENTITY_ID

  const highSchool = storyById(bundle, 'STORY_HIGH_SCHOOL_TRAJECTORY') as Job5KHighSchoolStory
  const eja = storyById(bundle, 'STORY_EJA_TERRITORY') as Job5KEjaStory
  const logistics = storyById(bundle, 'STORY_LOGISTICS_EPT') as Job5KLogisticsStory
  const youth = storyById(bundle, 'STORY_YOUTH_WORK_APPRENTICESHIP') as Job5KYouthStory
  const highSchoolVariant = storyVariant(highSchool, entityId)
  const ejaVariant = storyVariant(eja, entityId)
  const logisticsVariant = storyVariant(logistics, entityId)
  const youthVariant = storyVariant(youth, entityId)

  const highSchoolSecondary = invariant(
    highSchool.secondary_evidence.by_entity.find((item) => item.entity_id === entityId),
    `trajetória/${entityId}`,
  )
  const highSchoolSecondaryRegion = invariant(
    highSchool.secondary_evidence.by_entity.find((item) => item.entity_id === REGION_ENTITY_ID),
    'trajetória/Vale',
  )
  const youthPrimary = invariant(
    youth.primary_evidence.by_entity.find((item) => item.entity_id === entityId),
    `trabalho juvenil/${entityId}`,
  )
  const logisticsPrimary = invariant(
    logistics.primary_evidence.by_entity.find((item) => item.entity_id === entityId),
    `logística/${entityId}`,
  )
  const logisticsRegion = invariant(
    logistics.primary_evidence.by_entity.find((item) => item.entity_id === REGION_ENTITY_ID),
    'logística/Vale',
  )
  const logisticsSecondary = invariant(
    logistics.secondary_evidence.by_entity.find((item) => item.entity_id === entityId),
    `logística secundária/${entityId}`,
  )
  const ruralContext = invariant(
    bundle.insights.conditional_contexts.find((item) => item.context_id === 'CONTEXT_RURALITY_TRANSPORT'),
    'contexto ruralidade/transporte',
  )
  const ruralVariant = invariant(
    ruralContext.variants.find((item) => item.entity_id === entityId),
    `contexto ruralidade/transporte/${entityId}`,
  )
  const specialContext = invariant(
    bundle.insights.conditional_contexts.find((item) => item.context_id === 'CONTEXT_SPECIAL_AEE'),
    'contexto educação especial/AEE',
  )
  const specialVariant = invariant(
    specialContext.variants.find((item) => item.entity_id === entityId),
    `contexto educação especial/AEE/${entityId}`,
  )

  const preSchoolPopulation = seriesByQuery(
    bundle,
    'D1_COHORT_OFFER_CAPACITY',
    entityId,
    'resident_population',
    'pre_school_age_4_5',
  )
  const preSchoolPopulationRegion = seriesByQuery(
    bundle,
    'D1_COHORT_OFFER_CAPACITY',
    comparisonEntityId,
    'resident_population',
    'pre_school_age_4_5',
  )
  const preSchoolEnrollments = seriesByQuery(
    bundle,
    'D1_COHORT_OFFER_CAPACITY',
    entityId,
    'located_enrollments',
    'pre_school_age_4_5',
  )
  const preSchoolEnrollmentsRegion = seriesByQuery(
    bundle,
    'D1_COHORT_OFFER_CAPACITY',
    comparisonEntityId,
    'located_enrollments',
    'pre_school_age_4_5',
  )
  const fundamentalEnrollments = seriesByQuery(
    bundle,
    'D1_COHORT_OFFER_CAPACITY',
    entityId,
    'located_enrollments',
    'fundamental',
  )
  const fundamentalEnrollmentsRegion = seriesByQuery(
    bundle,
    'D1_COHORT_OFFER_CAPACITY',
    comparisonEntityId,
    'located_enrollments',
    'fundamental',
  )
  const highSchoolEnrollments = seriesByQuery(
    bundle,
    'D1_COHORT_OFFER_CAPACITY',
    entityId,
    'located_enrollments',
    'high_school',
  )
  const highSchoolEnrollmentsRegion = seriesByQuery(
    bundle,
    'D1_COHORT_OFFER_CAPACITY',
    comparisonEntityId,
    'located_enrollments',
    'high_school',
  )
  const youthWorkSeries = seriesByQuery(
    bundle,
    'D2_YOUTH_WORK_15_17',
    entityId,
    'total',
    undefined,
    '15_17',
  )
  const youthWorkSeriesRegion = seriesByQuery(
    bundle,
    'D2_YOUTH_WORK_15_17',
    comparisonEntityId,
    'total',
    undefined,
    '15_17',
  )
  const ejaHistory = seriesByQuery(
    bundle,
    'D1_ADULT_SCHOOLING_EJA',
    entityId,
    'total_context',
    'total_context',
  )
  const ejaHistoryRegion = seriesByQuery(
    bundle,
    'D1_ADULT_SCHOOLING_EJA',
    comparisonEntityId,
    'total_context',
    'total_context',
  )

  const comparisonSuffix = isRegion ? null : preSchoolPopulationRegion
  const selectedEjaDistribution = isRegion
    ? null
    : invariant(
      eja.ten_municipality_distribution.find((item) => item.municipality_ibge_code === entityId),
      `distribuição EJA/${entityId}`,
    )

  const failure = highSchoolSecondary.trajectory_2025.failure_percent?.value
  const distortion = highSchoolSecondary.trajectory_2025.age_grade_distortion_percent?.value
  const dropout = highSchoolSecondary.trajectory_2025.dropout_percent?.value
  const approval = highSchoolSecondary.trajectory_2025.approval_percent?.value
  const regionMobility = highSchoolSecondaryRegion.mobility_2022.value
  const localMobility = highSchoolSecondary.mobility_2022.value
  const youthWorkMovement = pluralSeriesMovement(youthWorkSeries)
  const ejaPriorityFigures: ManagerReviewPriority['figures'] = selectedEjaDistribution
    ? [
      {
        label: 'Diferença no fundamental',
        value: formatSigned(selectedEjaDistribution.fundamental.difference_percentage_points, 'percent'),
        period: '2022',
      },
      {
        label: 'Diferença no ensino médio',
        value: formatSigned(selectedEjaDistribution.high_school.difference_percentage_points, 'percent'),
        period: '2022',
      },
    ]
    : [
      {
        label: 'Distância regional no fundamental',
        value: `${decimalFormatter.format(eja.primary_evidence.regional_distance_percentage_points.fundamental)} p.p.`,
        period: '2022',
      },
      {
        label: 'Distância regional no ensino médio',
        value: `${decimalFormatter.format(eja.primary_evidence.regional_distance_percentage_points.high_school)} p.p.`,
        period: '2022',
      },
    ]

  const educationToTerritory: ManagerReviewCard[] = [
    {
      id: 'relacao-coortes-oferta',
      directionId: 'education-to-territory',
      sequence: 1,
      eyebrow: 'Demografia e organização da oferta',
      title: `Moradores de 4 e 5 anos e matrículas de pré-escola mudaram em ritmos próprios em ${entityName}.`,
      answer: 'A série de moradores acrescenta contexto à expansão ou retração das matrículas localizadas. As duas medidas, lidas juntas ao longo do tempo, mostram quando a rede precisa rever capacidade sem tratar população e matrícula como o mesmo universo.',
      evidenceClass: 'structural-contrast',
      evidenceLabel: 'Contraste estrutural observado',
      evidenceSummary: 'As duas séries anuais cobrem a mesma janela de 2014 a 2025 e permitem comparar direção e ritmo. A leitura mostra pressão demográfica e resposta da oferta, sem transformar a razão entre elas em demanda prevista.',
      mechanism: 'O tamanho das coortes altera o público potencial da etapa. Migração, fluxo escolar e escolhas de rede também interferem nas matrículas localizadas, por isso as duas medidas qualificam — mas não substituem — uma à outra.',
      connector: 'Mudanças observadas no mesmo período',
      educationLabel: 'O que mudou na educação',
      territoryLabel: 'O que o território acrescenta',
      educationEvidence: [seriesEvidence({
        id: 'pre-school-enrollments',
        label: 'Matrículas de pré-escola',
        series: preSchoolEnrollments,
        comparisonSeries: isRegion ? null : preSchoolEnrollmentsRegion,
        lens: 'Matrículas nas escolas do município',
      })],
      territoryEvidence: [seriesEvidence({
        id: 'pre-school-population',
        label: 'Moradores de 4 e 5 anos',
        series: preSchoolPopulation,
        comparisonSeries: comparisonSuffix,
        lens: 'Moradores do município',
      })],
      planningQuestion: 'Como ajustar turmas e capacidade da pré-escola acompanhando moradores e matrículas sem usar uma medida como substituta da outra?',
      responsibility: 'Ação direta da rede municipal',
      pneTopics: ['Educação infantil', 'Acesso e organização da oferta'],
      monitoringIndicators: ['população de 4 e 5 anos', 'matrículas de pré-escola', 'turmas e escolas por etapa'],
      sourceRefs: sourceRefsForFamily(bundle, 'D1_COHORT_OFFER_CAPACITY'),
      interpretationBoundary: 'População representa moradores; matrículas representam escolas localizadas. A leitura contrasta as duas lentes e não acompanha as mesmas pessoas.',
    },
    {
      id: 'relacao-trajetoria-mobilidade',
      directionId: 'education-to-territory',
      sequence: 2,
      eyebrow: 'Ensino médio, trajetória e mobilidade',
      title: highSchoolVariant.title_conclusion,
      answer: `${highSchoolVariant.integrated_summary} A leitura conjunta muda a pergunta de planejamento: além do volume da oferta, entram trajetória, transição e coordenação com a rede estadual.`,
      evidenceClass: 'statistical-context',
      evidenceLabel: 'Contraste territorial com contexto testado',
      evidenceSummary: 'A oferta tem série de 2014 a 2025; trajetória e contexto social entram em anos compatíveis, e mobilidade permanece fotografia de 2022. Nos dez municípios, mobilidade e trajetória não formaram um padrão consistente, portanto a mobilidade qualifica a coordenação, não o resultado escolar.',
      mechanism: 'A organização territorial da oferta e o deslocamento para estudar podem alterar acesso e transição entre redes. Como a fonte não informa destino nem acompanha estudantes ao longo do tempo, o mecanismo orienta coordenação e não atribuição de resultado.',
      connector: 'Oferta, trajetória e mobilidade no mesmo território',
      educationLabel: 'Resultado educacional observado',
      territoryLabel: 'Contexto territorial relacionado',
      educationEvidence: [
        seriesEvidence({
          id: 'high-school-enrollments',
          label: 'Matrículas do ensino médio',
          series: highSchoolEnrollments,
          comparisonSeries: isRegion ? null : highSchoolEnrollmentsRegion,
          lens: 'Matrículas nas escolas do município',
        }),
        ...(failure === null || failure === undefined ? [] : [snapshotEvidence({
          id: 'high-school-failure',
          label: 'Reprovação no ensino médio',
          value: failure,
          detail: distortion === null || distortion === undefined
            ? 'taxa oficial da rede total'
            : `distorção idade-série: ${formatValue(distortion, 'percent')}`,
          period: '2025',
          lens: 'Rede responsável pela oferta',
        })]),
      ],
      territoryEvidence: localMobility === null ? [] : [snapshotEvidence({
        id: 'high-school-mobility',
        label: 'Residentes que estudavam fora',
        value: localMobility,
        detail: 'fotografia do ensino médio',
        period: '2022',
        lens: 'Residência do estudante',
        comparison: !isRegion && regionMobility !== null
          ? `Vale do Sinos: ${formatValue(regionMobility, 'percent')}`
          : null,
      })],
      planningQuestion: 'Como município e rede estadual podem acompanhar reprovação, distorção, transição e mobilidade antes de reorganizar a oferta do ensino médio?',
      responsibility: 'Coordenação com a rede estadual',
      pneTopics: ['Ensino médio', 'Permanência e trajetória escolar'],
      monitoringIndicators: unique(['matrículas do ensino médio', 'reprovação', 'distorção idade-série', 'mobilidade de residentes']),
      sourceRefs: highSchool.source_refs,
      interpretationBoundary: 'Matrículas, taxas escolares e mobilidade por residência são lentes complementares. A mobilidade disponível é uma fotografia de 2022 e não informa destino.',
    },
    {
      id: 'relacao-trabalho-juvenil-ensino-medio',
      directionId: 'education-to-territory',
      sequence: 3,
      eyebrow: 'Trabalho juvenil e permanência',
      title: `Os vínculos formais de 15 a 17 anos ${youthWorkMovement} em ${entityName}; o padrão com a trajetória escolar não se manteve estável.`,
      answer: `Em ${entityName}, os registros de trabalho juvenil, aprendizagem e trajetória escolar descrevem grupos distintos. Lidos lado a lado, eles definem uma agenda comum de acompanhamento entre escola, trabalho e formação profissional.`,
      evidenceClass: 'tested-without-stable-pattern',
      evidenceLabel: 'Mudança relevante; padrão escolar não estável',
      evidenceSummary: 'A mudança do trabalho formal juvenil é observada. Quando a comparação mudou o peso dado a cada município, considerou anos anteriores ou retirou 2020–2021, o padrão com a trajetória escolar não se manteve. Trabalho e trajetória entram na mesma agenda, sem virar explicação automática.',
      mechanism: 'Horários, intensidade do trabalho e qualidade da aprendizagem podem afetar a conciliação entre escola e trabalho. Os registros disponíveis não identificam os mesmos jovens, então esse mecanismo sustenta monitoramento conjunto, não uma conclusão individual.',
      connector: 'Séries paralelas para uma decisão coordenada',
      educationLabel: 'Ponto de atenção na educação',
      territoryLabel: 'Mudança observada no trabalho',
      educationEvidence: [
        ...(approval === null || approval === undefined ? [] : [snapshotEvidence({
          id: 'high-school-approval',
          label: 'Aprovação no ensino médio',
          value: approval,
          detail: failure === null || failure === undefined
            ? 'taxa oficial da rede total'
            : `reprovação: ${formatValue(failure, 'percent')}`,
          period: '2025',
          lens: 'Rede responsável pela oferta',
        })]),
        ...(dropout === null || dropout === undefined ? [] : [snapshotEvidence({
          id: 'high-school-dropout',
          label: 'Abandono no ensino médio',
          value: dropout,
          detail: distortion === null || distortion === undefined
            ? 'taxa oficial da rede total'
            : `distorção idade-série: ${formatValue(distortion, 'percent')}`,
          period: '2025',
          lens: 'Rede responsável pela oferta',
        })]),
      ],
      territoryEvidence: [
        seriesEvidence({
          id: 'youth-work-15-17',
          label: 'Vínculos formais de 15 a 17 anos',
          series: youthWorkSeries,
          comparisonSeries: isRegion ? null : youthWorkSeriesRegion,
          lens: 'Vínculos nos estabelecimentos do município',
        }),
        snapshotEvidence({
          id: 'apprenticeship-share',
          label: 'Aprendizagem nas admissões juvenis',
          value: youthPrimary.apprenticeship_share_2025.percent,
          detail: `${numberFormatter.format(youthPrimary.apprenticeship_share_2025.numerator)} de ${numberFormatter.format(youthPrimary.apprenticeship_share_2025.denominator)} eventos`,
          period: '2025',
          lens: 'Eventos de admissão no local de trabalho',
        }),
      ],
      planningQuestion: 'Que rotina conjunta entre educação, trabalho, empregadores e formação profissional deve acompanhar permanência, aprendizagem e transição do ensino médio?',
      responsibility: 'Coordenação com a rede estadual e articulação educação–trabalho',
      pneTopics: ['Ensino médio', 'Permanência', 'Aprendizagem profissional'],
      monitoringIndicators: unique(['aprovação', 'reprovação', 'abandono', ...youth.monitoring_indicators]),
      sourceRefs: youth.source_refs,
      interpretationBoundary: 'Vínculos ativos e eventos de admissão são medidas diferentes; os registros de trabalho e educação permanecem agregados e separados.',
    },
    {
      id: 'relacao-eja-escolaridade-adulta',
      directionId: 'education-to-territory',
      sequence: 4,
      eyebrow: 'EJA e escolaridade da população adulta',
      title: ejaVariant.title_conclusion,
      answer: ejaVariant.integrated_summary,
      evidenceClass: 'territorial-mismatch',
      evidenceLabel: 'Desencontro territorial observado',
      evidenceSummary: 'Em 2022, a participação de cada município no público adulto residente foi comparada à sua participação nas matrículas localizadas, separadamente no fundamental e no ensino médio. A diferença é uma medida de distribuição, não de cobertura ou demanda.',
      mechanism: 'Quando público residente e oferta localizada ocupam posições diferentes na região, horários, localização, deslocamento e pactuação entre redes tornam-se perguntas concretas. A comparação localiza a questão, mas não identifica por que cada adulto frequenta ou não a EJA.',
      connector: 'Duas distribuições comparadas por etapa',
      educationLabel: 'Onde estão as matrículas de EJA',
      territoryLabel: 'Onde está o público residente',
      educationEvidence: [
        seriesEvidence({
          id: 'eja-history',
          label: 'Matrículas de EJA',
          series: ejaHistory,
          comparisonSeries: isRegion ? null : ejaHistoryRegion,
          lens: 'Matrículas nas escolas do município',
        }),
        ...(selectedEjaDistribution ? [pairedShareEvidence({
          id: 'eja-enrollment-shares',
          label: 'Participação nas matrículas regionais',
          first: selectedEjaDistribution.fundamental.located_eja_share_percent,
          second: selectedEjaDistribution.high_school.located_eja_share_percent,
          detail: 'fundamental / ensino médio',
          period: '2022',
          lens: 'Matrículas nas escolas do município',
        })] : [snapshotEvidence({
          id: 'eja-regional-distance',
          label: 'Distância entre distribuições no ensino médio',
          value: eja.primary_evidence.regional_distance_percentage_points.high_school,
          detail: 'distribuição dos dez municípios',
          period: '2022',
          lens: 'Vale do Sinos',
        })]),
      ],
      territoryEvidence: selectedEjaDistribution ? [
        pairedShareEvidence({
          id: 'eja-resident-shares',
          label: 'Participação no público residente regional',
          first: selectedEjaDistribution.fundamental.resident_public_share_percent,
          second: selectedEjaDistribution.high_school.resident_public_share_percent,
          detail: 'fundamental / ensino médio',
          period: '2022',
          lens: 'Moradores do município',
        }),
        {
          id: 'eja-distribution-difference',
          label: 'Diferença entre as duas participações',
          value: `${formatSigned(selectedEjaDistribution.fundamental.difference_percentage_points, 'percent')} / ${formatSigned(selectedEjaDistribution.high_school.difference_percentage_points, 'percent')}`,
          detail: 'fundamental / ensino médio',
          period: '2022',
          lens: 'Contraste entre residência e localização escolar',
          availabilityState: 'observed',
          comparison: null,
          series: null,
        },
      ] : [snapshotEvidence({
        id: 'eja-regional-distance-fundamental',
        label: 'Distância entre distribuições no fundamental',
        value: eja.primary_evidence.regional_distance_percentage_points.fundamental,
        detail: 'distribuição dos dez municípios',
        period: '2022',
        lens: 'Vale do Sinos',
      })],
      planningQuestion: 'Em qual etapa a localização da oferta, os horários e a coordenação entre redes precisam ser revistos diante da distribuição do público residente?',
      responsibility: 'Ação municipal e coordenação regional entre redes',
      pneTopics: ['Educação de jovens e adultos', 'Escolaridade da população adulta'],
      monitoringIndicators: eja.monitoring_indicators,
      sourceRefs: eja.source_refs,
      interpretationBoundary: eja.interpretation_boundary,
    },
  ]

  const territoryToEducation: ManagerReviewCard[] = [
    {
      id: 'agenda-coortes-capacidade',
      directionId: 'territory-to-education',
      sequence: 1,
      eyebrow: 'Mudança já em curso · coortes e rede',
      title: 'Os ritmos próprios de cada etapa devem orientar a revisão periódica da capacidade da rede.',
      answer: `Em ${entityName}, a mudança observada nas coortes e nas matrículas não segue automaticamente o agregado regional. O planejamento dos próximos anos precisa distinguir expansão, estabilidade e retração por etapa.`,
      evidenceClass: 'structural-contrast',
      evidenceLabel: 'Série histórica e contraste por etapa',
      evidenceSummary: 'Matrículas e população são observadas por etapa na mesma janela. Direções diferentes entre município e região impedem que o agregado regional seja usado como resposta automática para a capacidade local.',
      mechanism: 'Coortes menores ou maiores alteram a pressão potencial sobre cada etapa, enquanto fluxo, rede responsável e mobilidade modulam a resposta efetiva. Por isso a revisão deve ocorrer por etapa e com responsabilidades distintas.',
      connector: 'Do movimento territorial à decisão sobre capacidade',
      educationLabel: 'Ponto de partida da oferta',
      territoryLabel: 'Transformação territorial observada',
      educationEvidence: [
        seriesEvidence({
          id: 'agenda-pre-school',
          label: 'Pré-escola',
          series: preSchoolEnrollments,
          comparisonSeries: isRegion ? null : preSchoolEnrollmentsRegion,
          lens: 'Matrículas nas escolas do município',
        }),
        seriesEvidence({
          id: 'agenda-fundamental',
          label: 'Ensino fundamental',
          series: fundamentalEnrollments,
          comparisonSeries: isRegion ? null : fundamentalEnrollmentsRegion,
          lens: 'Matrículas nas escolas do município',
        }),
        seriesEvidence({
          id: 'agenda-high-school',
          label: 'Ensino médio',
          series: highSchoolEnrollments,
          comparisonSeries: isRegion ? null : highSchoolEnrollmentsRegion,
          lens: 'Matrículas nas escolas do município',
        }),
      ],
      territoryEvidence: [seriesEvidence({
        id: 'agenda-pre-school-population',
        label: 'Moradores de 4 e 5 anos',
        series: preSchoolPopulation,
        comparisonSeries: comparisonSuffix,
        lens: 'Moradores do município',
      })],
      planningQuestion: 'Quais mudanças por etapa devem disparar revisão de turmas, transições, espaços e coordenação com a rede estadual?',
      responsibility: 'Ação municipal e coordenação com a rede estadual',
      pneTopics: ['Acesso', 'Organização da oferta', 'Transição entre etapas'],
      monitoringIndicators: ['população por idade', 'matrículas por etapa', 'turmas', 'escolas'],
      sourceRefs: sourceRefsForFamily(bundle, 'D1_COHORT_OFFER_CAPACITY'),
      interpretationBoundary: 'A agenda usa somente mudanças observadas. Ela não antecipa vagas, abertura ou fechamento de escolas.',
    },
    {
      id: 'agenda-trabalho-aprendizagem',
      directionId: 'territory-to-education',
      sequence: 2,
      eyebrow: 'Mudança já em curso · trabalho juvenil',
      title: 'O avanço do trabalho formal juvenil e da aprendizagem coloca permanência e transição na agenda do ensino médio.',
      answer: youthVariant.integrated_summary,
      evidenceClass: 'tested-without-stable-pattern',
      evidenceLabel: 'Agenda sustentada; efeito escolar não demonstrado',
      evidenceSummary: 'Vínculos ativos e eventos de aprendizagem mostram mudança material no território. A relação com abandono e reprovação não foi estável nas especificações testadas, então a implicação pública é coordenação e acompanhamento, não atribuição de efeito.',
      mechanism: 'A entrada no trabalho pode reorganizar tempo, renda e expectativas de transição. A escola, a rede estadual, empregadores e instituições formadoras conseguem agir sobre essa interface mesmo sem presumir que os registros descrevem os mesmos jovens.',
      connector: 'Do trabalho observado à coordenação educacional',
      educationLabel: 'Ponto de partida da educação',
      territoryLabel: 'Transformação do trabalho',
      educationEvidence: [
        seriesEvidence({
          id: 'agenda-youth-high-school',
          label: 'Matrículas do ensino médio',
          series: highSchoolEnrollments,
          comparisonSeries: isRegion ? null : highSchoolEnrollmentsRegion,
          lens: 'Matrículas nas escolas do município',
        }),
        ...(dropout === null || dropout === undefined ? [] : [snapshotEvidence({
          id: 'agenda-youth-dropout',
          label: 'Abandono no ensino médio',
          value: dropout,
          detail: failure === null || failure === undefined
            ? 'taxa oficial da rede total'
            : `reprovação: ${formatValue(failure, 'percent')}`,
          period: '2025',
          lens: 'Rede responsável pela oferta',
        })]),
      ],
      territoryEvidence: [
        seriesEvidence({
          id: 'agenda-youth-work',
          label: 'Vínculos formais de 15 a 17 anos',
          series: youthWorkSeries,
          comparisonSeries: isRegion ? null : youthWorkSeriesRegion,
          lens: 'Vínculos nos estabelecimentos do município',
        }),
        snapshotEvidence({
          id: 'agenda-apprenticeship',
          label: 'Aprendizagem nas admissões juvenis',
          value: youthPrimary.apprenticeship_share_2025.percent,
          detail: `${numberFormatter.format(youthPrimary.apprenticeship_share_2025.numerator)} de ${numberFormatter.format(youthPrimary.apprenticeship_share_2025.denominator)} eventos`,
          period: '2025',
          lens: 'Eventos de admissão no local de trabalho',
        }),
      ],
      planningQuestion: 'Como articular horários, transição do 9º ano, permanência e aprendizagem com a rede estadual, empregadores e instituições formadoras?',
      responsibility: 'Coordenação com a rede estadual e articulação formação–trabalho',
      pneTopics: ['Ensino médio', 'Aprendizagem profissional', 'Educação profissional'],
      monitoringIndicators: youth.monitoring_indicators,
      sourceRefs: youth.source_refs,
      interpretationBoundary: 'O estoque de vínculos, os eventos de admissão e os registros escolares permanecem medidas separadas; a agenda é institucional e territorial.',
    },
    {
      id: 'agenda-ocupacoes-formacao',
      directionId: 'territory-to-education',
      sequence: 3,
      eyebrow: 'Mudança já em curso · ocupações e formação',
      title: logisticsVariant.title_conclusion,
      answer: logisticsVariant.integrated_summary,
      evidenceClass: 'territorial-mismatch',
      evidenceLabel: 'Desencontro territorial observado',
      evidenceSummary: 'A mudança da ocupação auxiliar de logística entre 2019 e 2025 foi comparada à localização da EPT em 2025. O resultado mostra concentração em municípios diferentes e sustenta uma pergunta regional de acesso, sem provar falta de curso ou aderência curricular.',
      mechanism: 'Transformações ocupacionais podem alterar os conhecimentos demandados e os trajetos de formação. Como trabalhadores podem residir fora e estudantes podem estudar fora, a decisão deve considerar acesso regional e a ponte normativa entre cursos e ocupações.',
      connector: 'Da transformação ocupacional à agenda formativa',
      educationLabel: 'Ponto de partida da formação',
      territoryLabel: 'Transformação do trabalho',
      educationEvidence: [endpointEvidence({
        id: 'agenda-ept',
        label: 'EPT localizada',
        endpoint: logisticsPrimary.ept,
        lens: 'Matrículas nas escolas do município',
        comparison: isRegion ? null : `Vale do Sinos em 2025: ${numberFormatter.format(invariant(logisticsRegion.ept.final_value, 'EPT regional'))} matrículas`,
      })],
      territoryEvidence: [
        {
          id: 'agenda-logistics-occupation',
          label: 'Auxiliar de logística',
          value: `${numberFormatter.format(logisticsPrimary.occupation.initial_value)} → ${numberFormatter.format(logisticsPrimary.occupation.final_value)}`,
          detail: logisticsPrimary.occupation_change_share_percent === null
            ? `${formatSigned(logisticsPrimary.occupation.absolute_change, 'active_bonds')} vínculos`
            : `${decimalFormatter.format(logisticsPrimary.occupation_change_share_percent)}% da mudança positiva regional`,
          period: '2019–2025',
          lens: 'Vínculos nos estabelecimentos do município',
          availabilityState: logisticsPrimary.occupation.final_value === 0 ? 'observed_zero' : 'observed',
          comparison: isRegion
            ? null
            : `Vale do Sinos: ${numberFormatter.format(logisticsRegion.occupation.initial_value)} → ${numberFormatter.format(logisticsRegion.occupation.final_value)}`,
          series: null,
        },
        endpointEvidence({
          id: 'agenda-youth-18-24',
          label: 'Vínculos formais de 18 a 24 anos',
          endpoint: logisticsSecondary.youth_work_18_24,
          lens: 'Vínculos nos estabelecimentos do município',
        }),
      ],
      planningQuestion: 'Que itinerários, parcerias e formas de acesso regional devem ser avaliados antes de qualquer decisão local sobre educação profissional?',
      responsibility: 'Articulação regional entre formação e trabalho',
      pneTopics: ['Educação profissional e tecnológica', 'Formação de jovens e adultos'],
      monitoringIndicators: logistics.monitoring_indicators,
      sourceRefs: logistics.source_refs,
      interpretationBoundary: logistics.interpretation_boundary,
    },
  ]

  const supportingRelations: ManagerReviewSupportingRelation[] = [
    ...(highSchoolSecondary.inse_2023 === null ? [] : [{
      id: 'conexao-contexto-socioeconomico-trajetoria',
      eyebrow: 'Conexão complementar · contexto social',
      title: 'O contexto socioeconômico qualifica a leitura da trajetória, mas não substitui o histórico escolar.',
      answer: `Em ${entityName}, o INSE dos alunos avaliados pode ser lido ao lado de aprovação, abandono e distorção do ensino médio. A comparação ajuda a localizar vulnerabilidades sem rotular estudantes ou transformar contexto em resultado.`,
      evidenceClass: 'statistical-context' as const,
      evidenceLabel: 'Diferenças entre municípios; evolução temporal limitada',
      evidenceSummary: 'Na comparação entre os municípios em 2019 e 2023, contexto socioeconômico e trajetória apresentaram diferenças relacionadas, mas esse desenho não permaneceu estável ao longo do tempo. O contexto social funciona como referência adicional, não como explicação isolada.',
      mechanism: 'Condições socioeconômicas podem organizar acesso a tempo, transporte, trabalho e apoio à aprendizagem. O INSE descreve alunos avaliados e não representa todos os moradores, por isso só qualifica o diagnóstico escolar.',
      evidence: [
        snapshotEvidence({
          id: 'support-inse',
          label: 'INSE médio dos alunos avaliados',
          value: highSchoolSecondary.inse_2023,
          unit: 'index',
          detail: 'escala oficial do INSE; contexto socioeconômico da rede total',
          period: '2023',
          lens: 'Alunos avaliados nas escolas do município',
        }),
        ...(approval === null || approval === undefined ? [] : [snapshotEvidence({
          id: 'support-approval',
          label: 'Aprovação no ensino médio',
          value: approval,
          detail: 'resultado escolar observado',
          period: '2025',
          lens: 'Rede responsável pela oferta',
        })]),
        ...(distortion === null || distortion === undefined ? [] : [snapshotEvidence({
          id: 'support-distortion',
          label: 'Distorção idade-série',
          value: distortion,
          detail: 'resultado escolar observado',
          period: '2025',
          lens: 'Rede responsável pela oferta',
        })]),
      ],
      planningQuestion: 'Em quais etapas e redes o contexto dos alunos precisa orientar apoio à permanência e à correção da distorção, sem substituir a análise do histórico escolar?',
      responsibility: 'Coordenação entre rede municipal e rede estadual',
      monitoringIndicators: ['INSE dos alunos avaliados', 'aprovação', 'abandono', 'distorção idade-série'],
      sourceRefs: highSchool.source_refs,
      interpretationBoundary: 'O gradiente entre municípios não se manteve como padrão longitudinal estável. INSE, taxas escolares e população residente têm universos distintos.',
    }]),
    {
      id: 'conexao-ruralidade-oferta-transporte',
      eyebrow: 'Conexão complementar · território rural',
      title: ruralVariant.title,
      answer: ruralVariant.summary,
      evidenceClass: 'descriptive-planning-signal',
      evidenceLabel: 'Reconfiguração observada da oferta rural',
      evidenceSummary: 'Matrículas e escolas rurais são comparadas entre 2014 e 2025. O PNATE permanece contexto administrativo separado, pois autorização financeira não informa rota, execução, pagamento ou uso.',
      mechanism: 'Quando a oferta rural muda, distância e transporte podem alterar o acesso às etapas. Sem dados de residência e rotas, a página formula uma questão de coordenação e preserva a separação entre oferta escolar e recurso administrativo.',
      evidence: [
        endpointEvidence({
          id: 'support-rural-enrollments',
          label: 'Matrículas em escolas rurais',
          endpoint: ruralVariant.rural_enrollments,
          lens: 'Matrículas nas escolas rurais do município',
        }),
        endpointEvidence({
          id: 'support-rural-high-school',
          label: 'Ensino médio em escolas rurais',
          endpoint: ruralVariant.rural_high_school_enrollments,
          lens: 'Matrículas nas escolas rurais do município',
        }),
        endpointEvidence({
          id: 'support-rural-schools',
          label: 'Escolas rurais',
          endpoint: ruralVariant.rural_schools,
          lens: 'Escolas localizadas no município',
        }),
      ],
      planningQuestion: 'Que dados de origem, rota e acesso precisam ser combinados com a oferta rural antes de reorganizar transporte ou etapas?',
      responsibility: 'Ação municipal e coordenação entre redes',
      monitoringIndicators: ['matrículas rurais por etapa', 'escolas rurais', 'rotas e estudantes transportados', 'execução do PNATE'],
      sourceRefs: ruralContext.source_refs,
      interpretationBoundary: 'Localização da escola não equivale à residência rural. O valor administrativo do PNATE não mede deslocamento, rota ou uso do recurso.',
    },
    {
      id: 'conexao-educacao-especial-aee',
      eyebrow: 'Conexão complementar · inclusão',
      title: 'Matrículas da educação especial e escolas que informam AEE mudaram em paralelo, sem medir cobertura.',
      answer: specialVariant.summary,
      evidenceClass: 'descriptive-planning-signal',
      evidenceLabel: 'Movimentos paralelos observados',
      evidenceSummary: 'As duas contagens têm endpoints comparáveis de 2014 e 2025. O crescimento simultâneo sinaliza pressão de organização da oferta, mas não informa quantos estudantes recebem AEE nem se a capacidade é suficiente.',
      mechanism: 'O crescimento das matrículas da educação especial pode exigir reorganização de escolas, profissionais e atendimento especializado. As fontes contam matrículas e escolas, não ligam cada estudante ao serviço recebido.',
      evidence: [
        endpointEvidence({
          id: 'support-special-enrollments',
          label: 'Matrículas da educação especial',
          endpoint: specialVariant.special_enrollments,
          lens: 'Matrículas nas escolas do município',
        }),
        endpointEvidence({
          id: 'support-aee-schools',
          label: 'Escolas que informam AEE',
          endpoint: specialVariant.schools_reporting_aee,
          lens: 'Escolas localizadas no município',
        }),
      ],
      planningQuestion: 'Como verificar capacidade, profissionais e acesso ao AEE por etapa diante da mudança observada nas matrículas?',
      responsibility: 'Ação das redes responsáveis pela oferta',
      monitoringIndicators: ['matrículas da educação especial', 'escolas que informam AEE', 'profissionais e atendimentos por etapa'],
      sourceRefs: specialContext.source_refs,
      interpretationBoundary: specialVariant.interpretation_boundary,
    },
  ]

  const priorities: ManagerReviewPriority[] = [
    {
      id: 'priority-high-school',
      label: 'Trajetória e coordenação',
      title: highSchoolVariant.title_conclusion,
      summary: 'O volume da oferta precisa ser lido junto a permanência, transição e mobilidade no ensino médio.',
      figures: highSchoolVariant.key_figures,
      responsibility: 'Município + rede estadual',
      href: '#relacao-trajetoria-mobilidade',
    },
    {
      id: 'priority-logistics',
      label: 'Trabalho e formação',
      title: logisticsVariant.title_conclusion,
      summary: 'A transformação ocupacional e a localização da formação colocam acesso e articulação regional na agenda.',
      figures: logisticsVariant.key_figures,
      responsibility: 'Formação + trabalho + região',
      href: '#agenda-ocupacoes-formacao',
    },
    {
      id: 'priority-eja',
      label: 'EJA por etapa',
      title: ejaVariant.title_conclusion,
      summary: 'Fundamental e ensino médio pedem leituras separadas sobre público residente e oferta localizada.',
      figures: ejaPriorityFigures,
      responsibility: 'Município + redes + região',
      href: '#relacao-eja-escolaridade-adulta',
    },
  ]

  const visibleTexts = [
    ...priorities.flatMap((item) => [item.label, item.title, item.summary, item.responsibility]),
    ...educationToTerritory.flatMap((item) => [
      item.eyebrow,
      item.title,
      item.answer,
      item.evidenceLabel,
      item.evidenceSummary,
      item.mechanism,
      item.connector,
      item.planningQuestion,
      item.responsibility,
      item.interpretationBoundary,
      ...item.pneTopics,
    ]),
    ...territoryToEducation.flatMap((item) => [
      item.eyebrow,
      item.title,
      item.answer,
      item.evidenceLabel,
      item.evidenceSummary,
      item.mechanism,
      item.connector,
      item.planningQuestion,
      item.responsibility,
      item.interpretationBoundary,
      ...item.pneTopics,
    ]),
    ...supportingRelations.flatMap((item) => [
      item.eyebrow,
      item.title,
      item.answer,
      item.evidenceLabel,
      item.evidenceSummary,
      item.mechanism,
      item.planningQuestion,
      item.responsibility,
      item.interpretationBoundary,
    ]),
  ]
  assertVocacoesPnePrototypeLanguage(visibleTexts)

  return {
    entityId,
    entityName,
    isRegion,
    priorities,
    supportingRelations,
    directions: [
      {
        id: 'education-to-territory',
        sequence: 1,
        title: 'O que o território ajuda a compreender sobre a educação?',
        question: 'Partimos de resultados educacionais e mostramos que características do território mudam ou qualificam essa leitura.',
        summary: 'Quatro relações integram demografia, trajetória, trabalho juvenil e escolaridade adulta sem transformar simultaneidade em explicação automática.',
        cards: educationToTerritory,
      },
      {
        id: 'territory-to-education',
        sequence: 2,
        title: 'O que o futuro do território exige da educação?',
        question: 'Partimos de mudanças já observadas no território e mostramos o que precisa entrar no planejamento educacional dos próximos anos.',
        summary: 'Três agendas ligam coortes, trabalho juvenil e transformação ocupacional a decisões sobre rede, permanência e formação profissional.',
        cards: territoryToEducation,
      },
    ],
  }
}
