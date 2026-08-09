import { useEffect, useMemo, useRef, useState } from 'react'
import { GraduationCap } from 'lucide-react'
import { ContentState } from '../../components/ContentState.jsx'
import { ErrorState } from '../../components/ErrorState.jsx'
import { loadEducationMunicipio } from '../../data/educationData.js'
import {
  SCHOOL_INFRASTRUCTURE_CONTRACT_VERSION,
  type SchoolInfrastructureContract,
} from '../../data/schoolInfrastructureContract'
import {
  EDUCATION_INDICATOR_CATALOG,
  EDUCATION_SECTION_CATALOG,
  EDUCATION_SECTION_KEYS,
  SCHOOL_INFRASTRUCTURE_BASIC_INDICATOR_ORDER,
  getEducationThemeForSection,
  resolveEducationSection,
} from '../../data/educationIndicatorCatalog.js'
import { mergeHashContext, replaceHashContext } from '../../utils/hashNavigation'
import { useAsyncData } from '../../utils/useAsyncData.js'
import '../../styles/education-pages.css'
import { EducationCompactHeader } from './components/EducationCompactHeader'
import { EducationDemandSection } from './components/EducationDemandSection'
import { EducationIndicatorsSection } from './components/EducationIndicatorsSection'
import { HigherEducationSection } from './components/HigherEducationSection'
import { EducationLandingPage } from './components/EducationLandingPage'
import { EducationMethodologySection } from './components/EducationMethodologySection'
import { MunicipalEducationOverviewPrintReport } from './components/MunicipalEducationOverviewPrintReport'
import { EducationOverviewSection } from './components/EducationOverviewSection'
import { MunicipalTechnicalReport } from './components/MunicipalTechnicalReport'
import {
  filterEducationIndicators,
  getInitialEducationNavigation,
  selectActiveEducationIndicator,
  selectEducationDetailSequence,
  selectEducationSectionItems,
} from './educationSelectors'
import {
  buildEducationModel,
  buildEducationPageViewModel,
  buildPneComplementaryTheme,
  applyEducationIndicatorStageOption,
} from './educationViewModels'
import {
  buildTrajectoryDetailSequence,
  trajectoryStageCardKey,
} from './educationTrajectoryStages'
import { useEducationPageState } from './hooks/useEducationPageState'
import {
  useMunicipalEducationOverview,
  type MunicipalEducationOverviewState,
} from './hooks/useMunicipalEducationOverview'
import { normalizeEducationIndicatorLabel } from './educationFormatters'
import { buildMunicipalLearningStages } from './municipalEducationLearningPresentation'
import type { EducationIndicatorKey, EducationPageProps } from './educationTypes'
import { useMunicipioDiagnostic } from '../../hooks/useMunicipioDiagnostic'
import { useHigherEducation } from './hooks/useHigherEducation'
import { useSpecialEducation } from './hooks/useSpecialEducation'
import {
  isResolvedSpecialEducationPoint,
  pointForIndicator,
  SPECIAL_EDUCATION_CUT_OPTIONS,
  specialEducationCutLabel,
} from './specialEducationViewModel'
import {
  isSpecialEducationIndicatorId,
  type SpecialEducationCut,
} from './specialEducationTypes'

const PANORAMA_THEME_KEYS = {
  matriculas: 'matriculas',
  escolasSistemaS: 'escolasSistemaS',
}

const INDIGENOUS_INDICATOR_UNITS: Record<string, string> = {
  'indigena-cobertura-estimada-4-17': 'cobertura',
  'indigena-matriculas': 'matriculas',
  'indigena-estabelecimentos': 'estabelecimentos',
  'indigena-docentes': 'docentes',
  'indigena-turmas': 'turmas',
}

const INDIGENOUS_UNIT_LABELS: Record<string, string> = {
  matriculas: 'Matrículas',
  estabelecimentos: 'Estabelecimentos',
  docentes: 'Docentes',
  turmas: 'Turmas',
}

const EDUCATION_PAGE_COPY = {
  description: 'Indicadores de atendimento, trajetória escolar, profissionais, infraestrutura, modalidades e condições da oferta educacional no município.',
  emptyDescription: 'Os indicadores educacionais são carregados após a seleção do município. Use o seletor no topo da página.',
  eyebrow: 'Indicadores de Educação',
  title: 'Indicadores de Educação',
}

const printDateFormatter = new Intl.DateTimeFormat('pt-BR')

function latestEducationYear(items: ReadonlyArray<Record<string, unknown>>) {
  const years = items
    .map((item) => Number(item.currentYear ?? item.year))
    .filter((year) => Number.isFinite(year) && year > 0)
  return years.length ? Math.max(...years) : null
}

export function EducationPage({
  indicadores,
  municipioData,
  municipalityId,
  municipalitySlug,
  navigationContext,
  selectedMunicipio,
}: EducationPageProps) {
  const pageCopy = EDUCATION_PAGE_COPY
  const selectedId = municipalityId
  const previousSelectedIdRef = useRef(selectedId)
  const munDataState = useAsyncData(async () => {
    if (!selectedId) return null
    return loadEducationMunicipio(selectedId)
  }, [selectedId])

  const currentNavigation = useMemo(
    () => getInitialEducationNavigation(navigationContext),
    [navigationContext],
  )
  const {
    detailNavigation,
    isDetailOpen,
    searchQuery,
    selectedIndicatorKey,
    selectedSectionKey,
    selectedThemeKey,
    setIsDetailOpen,
    setSearchQuery,
    setSelectedIndicatorKey,
    setSelectedThemeKey,
  } = useEducationPageState(currentNavigation)
  const isEducationLandingRoute = selectedSectionKey === EDUCATION_SECTION_KEYS.overview
  const isMunicipalOverviewRoute = selectedSectionKey === EDUCATION_SECTION_KEYS.panorama
    && selectedThemeKey !== PANORAMA_THEME_KEYS.escolasSistemaS
  const isTechnicalReportRoute = selectedSectionKey === EDUCATION_SECTION_KEYS.technicalReport
  const isHigherEducationRoute = selectedSectionKey === EDUCATION_SECTION_KEYS.higherEducation
  const municipalOverviewState = useMunicipalEducationOverview(
    selectedId,
    isMunicipalOverviewRoute || isTechnicalReportRoute || isEducationLandingRoute,
  )
  const municipalDiagnosticState = useMunicipioDiagnostic(
    isTechnicalReportRoute ? selectedId : null,
  )
  const higherEducationState = useHigherEducation(
    selectedId,
    isHigherEducationRoute || isTechnicalReportRoute,
  )
  const specialEducationState = useSpecialEducation(
    selectedId,
    selectedSectionKey === EDUCATION_SECTION_KEYS.modalities || isTechnicalReportRoute,
  )
  const [printEmissionDate, setPrintEmissionDate] = useState(() => printDateFormatter.format(new Date()))
  const [selectedSistemaSIndicator, setSelectedSistemaSIndicator] = useState('total_escolas')
  const [selectedIndicatorStageKey, setSelectedIndicatorStageKey] = useState(
    navigationContext?.params.get('etapa') ?? '',
  )
  const [selectedSpecialEducationCut, setSelectedSpecialEducationCut] = useState<SpecialEducationCut>('total')
  const [selectedIndigenousUnit, setSelectedIndigenousUnit] = useState(
    navigationContext?.params.get('medida') ?? 'matriculas',
  )
  const printButtonRef = useRef<HTMLButtonElement>(null)
  const dados = munDataState.data
  const sistemaS = dados?.blocos?.sistema_s ?? {}
  const educacaoIndigena = dados?.blocos?.educacao_indigena ?? {}
  const requestedDetailKey = navigationContext?.params.get('detalhe') ?? ''
  const requestedDimensionKey = navigationContext?.params.get('dimensao') ?? ''
  const requestedSectionKey = navigationContext?.params.get('secao') ?? ''

  useEffect(() => {
    const isLegacyInfrastructureAlias =
      SCHOOL_INFRASTRUCTURE_BASIC_INDICATOR_ORDER.some((key) => key === requestedDetailKey)
    if (!isLegacyInfrastructureAlias && !requestedDimensionKey) return
    replaceHashContext(navigationContext?.rawRoute || 'educacao', {
      secao: isLegacyInfrastructureAlias
        ? EDUCATION_SECTION_KEYS.infrastructure
        : requestedSectionKey || resolveEducationSection({ detailKey: requestedDetailKey }),
      detalhe: isLegacyInfrastructureAlias ? 'infraestrutura-basica' : requestedDetailKey,
      dimensao: null,
    })
  }, [navigationContext?.rawRoute, requestedDetailKey, requestedDimensionKey, requestedSectionKey])
  const hasSistemaS =
    Number(sistemaS.resumo_ultimo_ano?.total_escolas || 0) > 0 &&
    Number(sistemaS.ultimo_ano) === 2025
  const shouldKeepSistemaSTheme =
    munDataState.loading ||
    previousSelectedIdRef.current !== selectedId

  useEffect(() => {
    if (
      !shouldKeepSistemaSTheme &&
      selectedThemeKey === PANORAMA_THEME_KEYS.escolasSistemaS &&
      !hasSistemaS
    ) {
      setSelectedThemeKey(getEducationThemeForSection(selectedSectionKey) ?? PANORAMA_THEME_KEYS.matriculas)
    }
  }, [hasSistemaS, selectedSectionKey, selectedThemeKey, setSelectedThemeKey, shouldKeepSistemaSTheme])

  useEffect(() => {
    previousSelectedIdRef.current = selectedId
  }, [selectedId])

  useEffect(() => {
    setSelectedSpecialEducationCut('total')
  }, [selectedId, selectedIndicatorKey])

  useEffect(() => {
    const requestedUnit = navigationContext?.params.get('medida')
    if (requestedUnit && Object.values(INDIGENOUS_INDICATOR_UNITS).includes(requestedUnit)) {
      setSelectedIndigenousUnit(requestedUnit)
    }
    setSelectedIndicatorStageKey(navigationContext?.params.get('etapa') ?? '')
  }, [navigationContext])

  if (isEducationLandingRoute) {
    return (
      <div className="page-stack educacao-page education-landing-shell">
        <EducationLandingPage
          municipalitySlug={municipalitySlug}
          overview={municipalOverviewState}
        />
      </div>
    )
  }

  if (!selectedId) {
    return (
      <div className="page-stack educacao-page">
        <EducationCompactHeader
          description={pageCopy.description}
          eyebrow={pageCopy.eyebrow}
          title={pageCopy.title}
        />
        <section className="empty-state">
          <div className="empty-state__icon" aria-hidden="true">
            <GraduationCap strokeWidth={1.7} />
          </div>
          <h2>Selecione um município</h2>
          <p>{pageCopy.emptyDescription}</p>
        </section>
      </div>
    )
  }

  if (munDataState.loading) {
    return <div className="page-stack"><ContentState as="p" kind="loading" className="state-box state-box--loading">Carregando dados...</ContentState></div>
  }

  if (munDataState.error) {
    return (
      <div className="page-stack">
        <ErrorState
          title="Erro ao carregar dados"
          message="Não foi possível carregar os indicadores educacionais deste município."
        />
      </div>
    )
  }

  if (!dados) {
    return (
      <div className="page-stack">
        <ContentState kind="unavailable" className="state-box">
          <strong>Indicadores educacionais indisponíveis</strong>
          <span>Os dados deste município não estão disponíveis no momento.</span>
        </ContentState>
      </div>
    )
  }

  const model = buildEducationModel(dados.blocos ?? {})
  const schoolInfrastructure = dados.blocos?.rede_escolar?.infraestrutura?.contractVersion
    === SCHOOL_INFRASTRUCTURE_CONTRACT_VERSION
    ? dados.blocos.rede_escolar.infraestrutura as SchoolInfrastructureContract
    : null
  const pneComplementaryTheme = buildPneComplementaryTheme({
    indicadores,
    rede: dados.blocos?.rede_escolar,
    results: municipioData?.pne_2026_2036?.indicadores,
  })
  const allEducationItems = [
    ...model.items,
    ...(pneComplementaryTheme?.items ?? []).filter(
      (item) => !isSpecialEducationIndicatorId(item.key),
    ),
    ...(specialEducationState.data?.viewModel.items ?? []),
  ]
  const municipalLearningStages = buildMunicipalLearningStages(dados.blocos?.aprendizagem)
  const allSpecialEducationItems = specialEducationState.data?.viewModel.allItems ?? []
  const section = EDUCATION_SECTION_CATALOG.find((item) => item.key === selectedSectionKey)
  const sectionItems = selectEducationSectionItems(allEducationItems, section)
  const isTrajectorySection = selectedSectionKey === EDUCATION_SECTION_KEYS.trajectory
  const trajectoryDetailSequence = isTrajectorySection
    ? buildTrajectoryDetailSequence(sectionItems)
    : []
  const activeTrajectoryItem = isTrajectorySection
    ? trajectoryDetailSequence.find((item) => (
        item.indicatorKey === selectedIndicatorKey
        && (!selectedIndicatorStageKey || item.stageKey === selectedIndicatorStageKey)
      )) ?? null
    : null
  const effectiveIndicatorStageKey = activeTrajectoryItem?.stageKey ?? selectedIndicatorStageKey
  const displayedIndicatorCount = isTrajectorySection
    ? trajectoryDetailSequence.length
    : section?.indicatorCount ?? sectionItems.length
  const isSistemaSTheme = selectedThemeKey === PANORAMA_THEME_KEYS.escolasSistemaS && hasSistemaS
  const filteredItems = filterEducationIndicators(sectionItems, searchQuery)
  const activeIndicator = selectActiveEducationIndicator(sectionItems, selectedIndicatorKey)
    ?? selectActiveEducationIndicator(allSpecialEducationItems, selectedIndicatorKey)
    ?? (selectedIndicatorKey === 'rede-infraestrutura'
      ? selectActiveEducationIndicator(allEducationItems, selectedIndicatorKey)
      : null)
  const isSpecialEducationDetail = isSpecialEducationIndicatorId(selectedIndicatorKey)
  const detailSequenceItems = isTrajectorySection
    ? trajectoryDetailSequence
    : activeIndicator?.key === 'rede-infraestrutura'
      ? [activeIndicator, ...sectionItems]
      : sectionItems
  const activeDetailSequenceKey = isTrajectorySection
    ? activeTrajectoryItem?.key
    : activeIndicator?.key
  const { activeIndex: activeIndicatorIndex, previousItem: previousIndicator, nextItem: nextIndicator } = selectEducationDetailSequence(detailSequenceItems, activeDetailSequenceKey)
  const isShowingIndicatorDetail = Boolean(isDetailOpen && activeIndicator)
  const displayActiveIndicator = activeIndicator
    ? applyEducationIndicatorStageOption(activeIndicator, effectiveIndicatorStageKey)
    : null
  const isIndigenousDetail = Boolean(
    isDetailOpen && selectedIndicatorKey === 'educacao-indigena',
  )
  const {
    contextScope,
    isDemandSection,
    isMethodologySection,
    isOverviewSection,
  } = buildEducationPageViewModel({
    indicatorCount: displayedIndicatorCount,
    selectedSectionKey,
    sectionKeys: EDUCATION_SECTION_KEYS,
  })
  const isShowingHigherEducationDetail = isHigherEducationRoute && Boolean(
    selectedIndicatorKey && higherEducationState.data?.viewModel.indicators.some(
      (indicator) => indicator.id === selectedIndicatorKey && indicator.latestPoint,
    ),
  )
  const isShowingCompactEducationPage = isShowingIndicatorDetail || isIndigenousDetail || isSistemaSTheme || isDemandSection || isShowingHigherEducationDetail
  const sectionLatestYear = latestEducationYear(sectionItems)
  const overviewLatestYear = latestEducationYear(model.overview)
  const specialEducationYears = specialEducationState.data?.document.years.map(({ year }) => year) ?? []
  const specialEducationReference = specialEducationState.data?.document.years.find(({ year }) => year === 2025)
  const selectedSpecialEducationPoint = isSpecialEducationDetail && specialEducationReference
    ? pointForIndicator(
        specialEducationReference.cuts[selectedSpecialEducationCut],
        selectedIndicatorKey,
      )
    : undefined
  const specialEducationHasReferenceValue = isResolvedSpecialEducationPoint(selectedSpecialEducationPoint)
  const specialEducationPeriod = isSpecialEducationDetail
    && selectedIndicatorKey !== 'educacao-bilingue-surdos'
    && specialEducationHasReferenceValue
    && specialEducationYears.length > 1
    ? `${specialEducationYears[0]}–${specialEducationYears[specialEducationYears.length - 1]}`
    : String(
        activeIndicator?.currentYear
        ?? specialEducationYears[specialEducationYears.length - 1]
        ?? 2025,
      )

  const standardHeader = isMunicipalOverviewRoute ? (
    <EducationCompactHeader
      action={municipalOverviewState.status === 'ready' && municipalOverviewState.data ? (
        <button
          className="platform-navigation-button municipal-education-print-action"
          onClick={handlePrintOverview}
          ref={printButtonRef}
          type="button"
        >
          Imprimir relatório
        </button>
      ) : undefined}
      contextItems={[
        { icon: 'period', label: 'Ano de referência', value: String(municipalOverviewState.data?.reference.year ?? 2025) },
      ]}
      description="Síntese das matrículas, da oferta educacional, do rendimento escolar e das mudanças observadas no município."
      domain={EDUCATION_SECTION_KEYS.panorama}
      eyebrow="Educação municipal"
      title={section?.contextTitle ?? 'Panorama educacional do município'}
      variant="section"
    />
  ) : isSistemaSTheme ? (
    <EducationCompactHeader
      backLink={{ label: 'Voltar aos indicadores', onClick: handleBackFromSistemaS }}
      contextItems={[
        { icon: 'cut', label: 'Recorte', value: 'Sistema S' },
        { icon: 'period', label: 'Período', value: String(sistemaS.ultimo_ano ?? 'Último disponível') },
      ]}
      description="Histórico dos indicadores, distribuição das matrículas por etapa e escolas vinculadas no município."
      domain={EDUCATION_SECTION_KEYS.modalities}
      eyebrow="Indicador educacional"
      title="Sistema S"
      variant="detail"
    />
  ) : isIndigenousDetail ? (
    <EducationCompactHeader
      backLink={{ label: 'Voltar aos indicadores', onClick: handleBackToIndicators }}
      contextItems={[
        {
          icon: 'cut',
          label: 'Recorte',
          value: INDIGENOUS_UNIT_LABELS[selectedIndigenousUnit] ?? 'Educação Escolar Indígena',
        },
        {
          icon: 'period',
          label: 'Período',
          value: Array.isArray(educacaoIndigena.anos_disponiveis)
            ? `${educacaoIndigena.anos_disponiveis[0]}–${educacaoIndigena.anos_disponiveis.at(-1)}`
            : '2023–2025',
        },
      ]}
      description="Cobertura estimada para 4 a 17 anos e síntese municipal das matrículas, estabelecimentos, docentes e turmas da Educação Escolar Indígena."
      domain={EDUCATION_SECTION_KEYS.modalities}
      eyebrow="Indicador educacional"
      title="Educação Escolar Indígena"
      variant="detail"
    />
  ) : isShowingIndicatorDetail && activeIndicator && displayActiveIndicator ? (
    <EducationCompactHeader
      backLink={{ onClick: handleBackToIndicators }}
      contextItems={[
        isSpecialEducationDetail
          ? {
              icon: 'cut' as const,
              key: 'special-education-cut',
              label: 'Recorte',
              onSelect: (key: string) => setSelectedSpecialEducationCut(key as SpecialEducationCut),
              options: SPECIAL_EDUCATION_CUT_OPTIONS,
              selectedKey: selectedSpecialEducationCut,
              value: specialEducationCutLabel(selectedSpecialEducationCut),
            }
          : {
              icon: 'cut' as const,
              label: 'Recorte',
              value: String(displayActiveIndicator.mainCutLabel ?? displayActiveIndicator.themeLabel ?? section?.label ?? 'Municipal'),
            },
        { icon: 'period', label: 'Período', value: isSpecialEducationDetail ? specialEducationPeriod : displayActiveIndicator.currentYear ? String(displayActiveIndicator.currentYear) : 'Último disponível' },
      ]}
      description={displayActiveIndicator.key === 'infraestrutura-basica'
        ? 'Compare a disponibilidade de serviços básicos e espaços escolares nas escolas do município.'
        : displayActiveIndicator.description}
      domain={selectedSectionKey}
      eyebrow="Indicador educacional"
      title={normalizeEducationIndicatorLabel(
        activeIndicator.cardVariant === 'exploratory'
          ? activeIndicator.cardTitle ?? activeIndicator.label
          : activeIndicator.label,
      )}
      variant="detail"
    />
  ) : isMethodologySection ? (
    <EducationCompactHeader
      backLink={{ onClick: handleBackToEducationOverview }}
      contextItems={[
        { icon: 'scope', label: 'Escopo', value: `${EDUCATION_INDICATOR_CATALOG.length} indicadores` },
        { icon: 'source', label: 'Referência', value: 'Fontes oficiais' },
      ]}
      description={section?.description}
      eyebrow={section?.label ?? 'Metodologia e fontes'}
      title={section?.contextTitle ?? 'Construção e leitura dos indicadores'}
      variant="methodology"
    />
  ) : (
    <EducationCompactHeader
      backLink={isOverviewSection ? undefined : { onClick: handleBackToEducationOverview }}
      contextItems={[
        { icon: 'scope', label: 'Escopo', value: isOverviewSection ? '7 destaques' : contextScope },
        ...((isOverviewSection ? overviewLatestYear : sectionLatestYear)
          ? [{ icon: 'period' as const, label: 'Atualização', value: String(isOverviewSection ? overviewLatestYear : sectionLatestYear) }]
          : []),
      ]}
      description={isOverviewSection ? pageCopy.description : section?.description}
      domain={selectedSectionKey}
      eyebrow={isOverviewSection ? pageCopy.eyebrow : `Indicadores de Educação / ${section?.label ?? 'Seção'}`}
      title={isOverviewSection
        ? section?.contextTitle ?? pageCopy.title
        : section?.contextTitle ?? section?.label ?? pageCopy.title}
      variant="section"
    />
  )

  function handleIndicatorCardSelect(indicatorKey: EducationIndicatorKey, stageKey = '') {
    const indigenousUnit = INDIGENOUS_INDICATOR_UNITS[indicatorKey]
    if (indigenousUnit) {
      handleOpenIndigenousEducation(indicatorKey, indigenousUnit)
      return
    }
    detailNavigation.prepareDetail(trajectoryStageCardKey(indicatorKey, stageKey), { captureGridPosition: true })
    setSelectedIndicatorStageKey(stageKey)
    setSelectedIndicatorKey(indicatorKey)
    setIsDetailOpen(true)
    mergeHashContext(navigationContext?.rawRoute || 'educacao', {
      secao: navigationContext?.params.get('secao') ?? resolveEducationSection({ detailKey: indicatorKey }),
      detalhe: indicatorKey,
      dimensao: null,
      etapa: stageKey || null,
    })
  }

  function handleBackToIndicators() {
    const returnKey = isIndigenousDetail
      ? Object.entries(INDIGENOUS_INDICATOR_UNITS)
        .find(([, unit]) => unit === selectedIndigenousUnit)?.[0] ?? ''
      : trajectoryStageCardKey(selectedIndicatorKey, effectiveIndicatorStageKey)
    setIsDetailOpen(false)
    setSelectedIndicatorKey('')
    setSelectedIndicatorStageKey('')
    mergeHashContext(navigationContext?.rawRoute || 'educacao', {
      secao: navigationContext?.params.get('secao') ?? selectedSectionKey,
      detalhe: null,
      dimensao: null,
      etapa: null,
      medida: null,
    })
    detailNavigation.restoreGrid(returnKey)
  }

  function handleAdjacentIndicator(sequenceKey: EducationIndicatorKey) {
    const trajectoryItem = trajectoryDetailSequence.find((item) => item.key === sequenceKey)
    const indicatorKey = trajectoryItem?.indicatorKey ?? sequenceKey
    const stageKey = trajectoryItem?.stageKey ?? ''
    detailNavigation.prepareDetail(sequenceKey)
    setSelectedIndicatorStageKey(stageKey)
    setSelectedIndicatorKey(indicatorKey)
    setIsDetailOpen(true)
    mergeHashContext(navigationContext?.rawRoute || 'educacao', {
      secao: navigationContext?.params.get('secao') ?? resolveEducationSection({ detailKey: indicatorKey }),
      detalhe: indicatorKey,
      dimensao: null,
      etapa: stageKey || null,
    })
  }

  function handleHigherEducationIndicator(indicatorKey: string, captureGridPosition = false) {
    detailNavigation.prepareDetail(indicatorKey, { captureGridPosition })
    setSelectedIndicatorKey(indicatorKey)
    setIsDetailOpen(true)
    mergeHashContext(navigationContext?.rawRoute || 'educacao', {
      secao: EDUCATION_SECTION_KEYS.higherEducation,
      detalhe: indicatorKey,
    })
  }

  function handleBackToHigherEducation() {
    const returnKey = selectedIndicatorKey
    setSelectedIndicatorKey('')
    setIsDetailOpen(false)
    mergeHashContext(navigationContext?.rawRoute || 'educacao', {
      secao: EDUCATION_SECTION_KEYS.higherEducation,
      detalhe: null,
    })
    detailNavigation.restoreGrid(returnKey)
  }

  function handleOpenIndigenousEducation(indicatorKey: string, unitKey: string) {
    detailNavigation.prepareDetail(indicatorKey, { captureGridPosition: true })
    setSelectedIndigenousUnit(unitKey)
    setSelectedIndicatorKey('educacao-indigena')
    setIsDetailOpen(true)
    setSelectedThemeKey(getEducationThemeForSection(EDUCATION_SECTION_KEYS.modalities) ?? PANORAMA_THEME_KEYS.matriculas)
    mergeHashContext(navigationContext?.rawRoute || 'educacao', {
      secao: EDUCATION_SECTION_KEYS.modalities,
      detalhe: 'educacao-indigena',
      medida: unitKey,
      tema: null,
      theme: null,
    })
  }

  function handleOpenSistemaS(indicatorKey = 'total_escolas') {
    setSelectedSistemaSIndicator(indicatorKey)
    setSelectedIndicatorKey('')
    setIsDetailOpen(false)
    setSelectedThemeKey(PANORAMA_THEME_KEYS.escolasSistemaS)
    mergeHashContext(navigationContext?.rawRoute || 'educacao', {
      secao: EDUCATION_SECTION_KEYS.modalities,
      tema: PANORAMA_THEME_KEYS.escolasSistemaS,
      theme: null,
      detalhe: null,
    })
  }

  function handleBackFromSistemaS() {
    setSelectedThemeKey(getEducationThemeForSection(EDUCATION_SECTION_KEYS.modalities) ?? PANORAMA_THEME_KEYS.matriculas)
    mergeHashContext(navigationContext?.rawRoute || 'educacao', {
      secao: EDUCATION_SECTION_KEYS.modalities,
      tema: null,
      theme: null,
      detalhe: null,
    })
  }

  function handleBackToEducationOverview() {
    setSelectedIndicatorKey('')
    setIsDetailOpen(false)
    mergeHashContext(navigationContext?.rawRoute || 'educacao', {
      secao: EDUCATION_SECTION_KEYS.overview,
      tema: null,
      theme: null,
      detalhe: null,
      modulo: null,
    })
  }

  return (
    <div className={`page-stack educacao-page educacao-page--${selectedSectionKey}${isShowingCompactEducationPage ? ' educacao-page--detail' : ''}`}>
      {!isDemandSection && !isTechnicalReportRoute && !isHigherEducationRoute ? standardHeader : null}

      {isHigherEducationRoute ? (
        <HigherEducationSection
          detailKey={selectedIndicatorKey}
          detailViewRef={detailNavigation.detailViewRef}
          municipalityName={selectedMunicipio}
          onBack={handleBackToHigherEducation}
          onOpenIndicator={(indicatorKey) => handleHigherEducationIndicator(indicatorKey, true)}
          onSelectAdjacent={(indicatorKey) => handleHigherEducationIndicator(indicatorKey)}
          registerCard={detailNavigation.registerCard}
          state={higherEducationState}
        />
      ) : isMunicipalOverviewRoute ? (
        <MunicipalEducationOverviewContent
          learningStages={municipalLearningStages}
          state={municipalOverviewState}
        />
      ) : isTechnicalReportRoute ? (
        <MunicipalTechnicalReportContent
          diagnosticState={municipalDiagnosticState}
          educationItems={allEducationItems}
          emissionDate={printEmissionDate}
          higherEducationState={higherEducationState}
          municipalityId={selectedId}
          municipalityName={selectedMunicipio}
          municipalityPopulation={
            municipioData?.municipio?.populacao
            ?? municipioData?.municipio?.population
            ?? municipioData?.municipio?.populacao_total
          }
          municipalitySlug={municipalitySlug}
          pmeReferenceData={{
            planningScenarios: municipioData?.pne_2026_2036?.cenarios_planejamento,
            projections: municipioData?.pne_2026_2036?.projecoes,
          }}
          schoolInfrastructure={schoolInfrastructure}
          specialEducationState={specialEducationState}
          state={municipalOverviewState}
        />
      ) : isDemandSection && !isSistemaSTheme ? (
        <EducationDemandSection
          municipioData={municipioData}
          onBackToIndicators={handleBackToEducationOverview}
          selectedMunicipio={selectedMunicipio}
        />
      ) : isMethodologySection && !isSistemaSTheme ? (
        <EducationMethodologySection catalog={EDUCATION_INDICATOR_CATALOG} items={allEducationItems} />
      ) : (
        <section className="cycle-workspace educacao-workspace">
          <EducationIndicatorsSection
            actions={{
              onAdjacentIndicator: handleAdjacentIndicator,
              onBackToIndicators: handleBackToIndicators,
              onIndicatorCardSelect: handleIndicatorCardSelect,
              onOpenSistemaS: handleOpenSistemaS,
              onSearchChange: setSearchQuery,
            }}
            viewModel={{
              activeIndicator,
              activeIndicatorIndex,
              blocos: dados.blocos,
              detailNavigation,
              filteredItems,
              hasSistemaS,
              indicatorCount: displayedIndicatorCount,
              isDetailOpen,
              isIndigenousDetail,
              isShowingIndicatorDetail,
              isSistemaSTheme,
              nextIndicator,
              navigableContentCount: isShowingIndicatorDetail ? detailSequenceItems.length : sectionItems.length,
              previousIndicator,
              searchQuery,
              section,
              selectedSistemaSIndicator,
              selectedIndigenousUnit,
              selectedIndicatorKey,
              selectedIndicatorStageKey: effectiveIndicatorStageKey,
              selectedSectionKey,
              selectedSpecialEducationCut,
              specialEducationState,
            }}
          />
        </section>
      )}

      {isMunicipalOverviewRoute && municipalOverviewState.status === 'ready' && municipalOverviewState.data ? (
        <MunicipalEducationOverviewPrintReport
          data={municipalOverviewState.data}
          emissionDate={printEmissionDate}
          learningStages={municipalLearningStages}
        />
      ) : null}
    </div>
  )

  function handlePrintOverview() {
    if (municipalOverviewState.status !== 'ready' || !municipalOverviewState.data || !globalThis.window) return

    const emissionDate = printDateFormatter.format(new Date())
    const originalTitle = document.title
    const temporaryTitle = `panorama-educacional-${municipalOverviewState.data.municipality.slug}-${municipalOverviewState.data.reference.year}`
    const restoreDocument = () => {
      document.title = originalTitle
      globalThis.window?.removeEventListener('afterprint', restoreDocument)
      globalThis.window?.requestAnimationFrame(() => printButtonRef.current?.focus())
    }

    setPrintEmissionDate(emissionDate)
    globalThis.window.addEventListener('afterprint', restoreDocument, { once: true })
    globalThis.window.setTimeout(() => {
      document.title = temporaryTitle
      try {
        globalThis.window?.print()
        globalThis.window?.setTimeout(restoreDocument, 1500)
      } catch {
        restoreDocument()
      }
    }, 0)
  }
}

function MunicipalTechnicalReportContent({
  diagnosticState,
  educationItems,
  emissionDate,
  higherEducationState,
  municipalityId,
  municipalityName,
  municipalityPopulation,
  municipalitySlug,
  pmeReferenceData,
  schoolInfrastructure,
  specialEducationState,
  state,
}: {
  diagnosticState: ReturnType<typeof useMunicipioDiagnostic>
  educationItems: Array<{ key: string; [property: string]: unknown }>
  emissionDate: string
  higherEducationState: ReturnType<typeof useHigherEducation>
  municipalityId: string
  municipalityName: string
  municipalityPopulation?: unknown
  municipalitySlug?: string | null
  pmeReferenceData: {
    planningScenarios?: Record<string, unknown> | null
    projections?: Record<string, unknown> | null
  }
  schoolInfrastructure: SchoolInfrastructureContract | null
  specialEducationState: ReturnType<typeof useSpecialEducation>
  state: MunicipalEducationOverviewState
}) {
  if (state.status === 'idle' || state.status === 'loading') {
    return (
      <ContentState kind="loading" className="state-box state-box--loading">
        Carregando as bases do relatório técnico...
      </ContentState>
    )
  }

  return (
    <MunicipalTechnicalReport
      educationItems={educationItems}
      emissionDate={emissionDate}
      higherEducation={higherEducationState.data?.viewModel ?? null}
      higherEducationError={higherEducationState.error}
      higherEducationLoading={higherEducationState.loading}
      municipalityId={municipalityId}
      municipalityName={municipalityName}
      municipalityPopulation={municipalityPopulation}
      municipalitySlug={municipalitySlug}
      overview={state.status === 'ready' ? state.data : null}
      pmeDiagnostic={
        diagnosticState.status === 'success'
          ? diagnosticState.data?.pne2026PublicDiagnostic ?? null
          : null
      }
      pmeDiagnosticError={diagnosticState.status === 'error' ? diagnosticState.error : null}
      pmeDiagnosticLoading={diagnosticState.status === 'loading'}
      pmeReferenceData={pmeReferenceData}
      schoolInfrastructure={schoolInfrastructure}
      specialEducation={specialEducationState.data?.document ?? null}
      specialEducationError={specialEducationState.error}
      specialEducationLoading={specialEducationState.loading}
    />
  )
}

function MunicipalEducationOverviewContent({
  learningStages,
  state,
}: {
  learningStages: ReturnType<typeof buildMunicipalLearningStages>
  state: MunicipalEducationOverviewState
}) {
  if (state.status === 'idle' || state.status === 'loading') {
    return (
      <section className="municipal-education-overview-state">
        <ContentState kind="loading" className="state-box state-box--loading">
          <span className="state-box__loading-heading">
            <span className="state-spinner" aria-hidden="true" />
            <strong>Carregando o panorama educacional...</strong>
          </span>
          <span className="state-skeleton" aria-hidden="true"><span /><span /><span /></span>
        </ContentState>
      </section>
    )
  }

  if (state.status === 'absent') {
    return (
      <section className="municipal-education-overview-state">
        <ContentState kind="unavailable" className="state-box">
          <strong>Panorama educacional indisponível</strong>
          <span>As informações desta visão ainda não estão disponíveis para este município.</span>
        </ContentState>
      </section>
    )
  }

  if (state.status === 'error' || !state.data) {
    return (
      <section className="municipal-education-overview-state">
        <ErrorState
          title="Não foi possível carregar o panorama educacional"
          message="Tente novamente em instantes. Os demais indicadores educacionais permanecem disponíveis."
        />
      </section>
    )
  }

  return <EducationOverviewSection data={state.data} learningStages={learningStages} />
}
