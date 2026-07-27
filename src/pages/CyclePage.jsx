import { useEffect, useMemo, useRef, useState } from 'react'
import { CategoryTabs } from '../components/CategoryTabs'
import { DataSourceNote } from '../components/DataSourceNote'
import { DetailNavigation } from '../components/DetailNavigation'
import { IndicatorDetail } from '../components/IndicatorDetail'
import { MetaCard } from '../components/MetaCard'
import { SearchField } from '../components/SearchField'
import { SegmentedControl } from '../components/SegmentedControl'
import { PNE_2026_INDICATOR_GOAL_REFS } from '../data/pne2026IndicatorGoalRefs'
import { PNE_2014_INDICATOR_GOAL_REFS } from '../data/pne2014IndicatorGoalRefs'
import { buildThematicGroups } from '../data/thematicGroups'
import { loadMunicipioDetails, loadMunicipioDiagnostic, loadPneStateReference } from '../data/staticData'
import { normalizePopulationPercentResults } from '../utils/indicatorValues'
import { getPneCycleCopy } from '../utils/pneCycleCopy'
import { filterPneComparableCategories } from '../utils/pneDisplayRules'
import { resolveDetailSequence, useDetailViewNavigation } from '../hooks/useDetailViewNavigation'
import { PnePageHeader } from '../components/PnePageHeader'
import { getHashContext, setHashContext } from '../utils/hashNavigation'
import { useAsyncData } from '../utils/useAsyncData'
import { buildPne2026AccumulativePresentationModel } from '../utils/pneAccumulativeCycle'

const CYCLE_SOURCE_NOTE = 'INEP, Censo Escolar, SAEB, IBGE e bases oficiais consolidadas no painel.'
const PNE_2026_DETAIL_REDIRECTS = {
  medio_tecnico: 'medio_tecnico_articulado_percentual',
}

function resolveCycleDetailKey(cycle, indicatorKey) {
  if (cycle !== 'pne_2026_2036') return indicatorKey
  return PNE_2026_DETAIL_REDIRECTS[indicatorKey] ?? indicatorKey
}

export function CyclePage({ cycle, indicadores, municipioData, selectedMunicipio, title }) {
  const rawInitialDetailKey = getHashContext().params.get('detalhe') ?? ''
  const initialDetailKey = resolveCycleDetailKey(cycle, rawInitialDetailKey)
  const cycleCopy = getPneCycleCopy(cycle)
  const categories = useMemo(
    () => enrichGoalRefs(indicadores?.cycles?.[cycle]?.categories ?? [], cycle),
    [indicadores, cycle],
  )
  const [selectedGroupKey, setSelectedGroupKey] = useState('')
  const [selectedBasicEducationFilterKey, setSelectedBasicEducationFilterKey] = useState('todos')
  const [selectedIndicatorKey, setSelectedIndicatorKey] = useState(initialDetailKey)
  const [isDetailOpen, setIsDetailOpen] = useState(Boolean(initialDetailKey))
  const [searchQuery, setSearchQuery] = useState('')
  const previousCycleRef = useRef(cycle)
  const municipioResults = municipioData?.[cycle]?.indicadores ?? null
  const { data: stateReference } = useAsyncData(
    () => loadPneStateReference(cycle).catch(() => null),
    [cycle],
  )
  const { data: municipioDetails } = useAsyncData(
    () => municipioData?.id_municipio ? loadMunicipioDetails(municipioData.id_municipio) : null,
    [municipioData?.id_municipio],
  )
  const allCycleItems = useMemo(
    () => categories.flatMap((category) => category.items ?? []),
    [categories],
  )
  const normalizedMunicipioResults = useMemo(
    () => normalizePopulationPercentResults(municipioResults, allCycleItems),
    [municipioResults, allCycleItems],
  )
  const comparableCategories = useMemo(
    () => filterPneComparableCategories(categories, normalizedMunicipioResults),
    [categories, normalizedMunicipioResults],
  )
  const thematicGroups = useMemo(
    () => buildThematicGroups(comparableCategories),
    [comparableCategories],
  )
  const selectedGroup = useMemo(() => {
    if (!thematicGroups.length) return null
    return (
      thematicGroups.find((group) => group.key === selectedGroupKey) ??
      thematicGroups[0]
    )
  }, [thematicGroups, selectedGroupKey])

  const selectedBasicEducationFilter = useMemo(() => {
    const filters = selectedGroup?.filters ?? []
    if (!filters.length) return null
    return (
      filters.find((filter) => filter.key === selectedBasicEducationFilterKey) ??
      filters[0]
    )
  }, [selectedGroup, selectedBasicEducationFilterKey])
  const visibleGroupItems = useMemo(
    () => selectedBasicEducationFilter?.items ?? selectedGroup?.items ?? [],
    [selectedBasicEducationFilter, selectedGroup],
  )

  useEffect(() => {
    if (!selectedIndicatorKey) return
    const currentGroup = thematicGroups.find((group) => group.key === selectedGroupKey)
    if (currentGroup?.items?.some((item) => item.key === selectedIndicatorKey)) return

    const targetGroup = thematicGroups.find((group) => (
      group.items?.some((item) => item.key === selectedIndicatorKey)
    ))
    if (!targetGroup || targetGroup.key === selectedGroupKey) return
    setSelectedGroupKey(targetGroup.key)
    setSelectedBasicEducationFilterKey('todos')
  }, [selectedGroupKey, selectedIndicatorKey, thematicGroups])

  const filteredGroupItems = useMemo(() => {
    const query = searchQuery.trim().toLocaleLowerCase('pt-BR')
    if (!query) return visibleGroupItems
    return visibleGroupItems.filter((item) => item.label.toLocaleLowerCase('pt-BR').includes(query))
  }, [visibleGroupItems, searchQuery])
  const activeIndicatorKey = useMemo(
    () => filteredGroupItems.some((item) => item.key === selectedIndicatorKey)
      ? selectedIndicatorKey
      : '',
    [filteredGroupItems, selectedIndicatorKey],
  )
  const activeItem = useMemo(
    () => filteredGroupItems.find((item) => item.key === activeIndicatorKey) ?? null,
    [activeIndicatorKey, filteredGroupItems],
  )
  const activeResult = activeItem ? normalizedMunicipioResults?.[activeItem.key] : null
  const { activeIndex, previousItem, nextItem } = resolveDetailSequence(filteredGroupItems, activeItem?.key)
  const cycleManagementStats = useMemo(
    () => buildCycleManagementStats(
      comparableCategories,
      normalizedMunicipioResults,
      cycle,
      municipioDetails,
    ),
    [comparableCategories, normalizedMunicipioResults, cycle, municipioDetails],
  )
  const isCycleTransition = previousCycleRef.current !== cycle
  const isShowingDetail = Boolean(!isCycleTransition && isDetailOpen && activeItem)
  const shouldLoadInequalityPilot = cycle === 'pne_2026_2036'
    && isShowingDetail
    && activeItem?.key === 'basico_integral'
  const {
    data: inequalityDiagnostic,
    loading: inequalityPilotLoading,
  } = useAsyncData(
    () => shouldLoadInequalityPilot && municipioData?.id_municipio
      ? loadMunicipioDiagnostic(municipioData.id_municipio)
      : null,
    [municipioData?.id_municipio, shouldLoadInequalityPilot],
  )
  const activeThemeLabel = selectedGroup?.shortLabel ?? selectedGroup?.label ?? null
  const detailNavigation = useDetailViewNavigation({
    activeKey: activeIndicatorKey,
    isOpen: isShowingDetail,
  })

  useEffect(() => {
    if (cycle === 'pne_2026_2036' && rawInitialDetailKey !== initialDetailKey) {
      setHashContext('pne2026', { detalhe: initialDetailKey })
    }
  }, [cycle, initialDetailKey, rawInitialDetailKey])

  useEffect(() => {
    function handleHashChange() {
      const detailKey = resolveCycleDetailKey(
        cycle,
        getHashContext().params.get('detalhe') ?? '',
      )
      setSelectedIndicatorKey(detailKey)
      setIsDetailOpen(Boolean(detailKey))
    }
    window.addEventListener('hashchange', handleHashChange)
    return () => window.removeEventListener('hashchange', handleHashChange)
  }, [cycle])

  useEffect(() => {
    if (previousCycleRef.current === cycle) return

    previousCycleRef.current = cycle
    const nextGroup = thematicGroups.find((group) => group.key === selectedGroupKey)
      ?? thematicGroups[0]
      ?? null
    const filterIsValid = nextGroup?.filters?.some(
      (filter) => filter.key === selectedBasicEducationFilterKey,
    )

    setSelectedGroupKey(nextGroup?.key ?? '')
    setSelectedBasicEducationFilterKey(filterIsValid ? selectedBasicEducationFilterKey : 'todos')
    setSelectedIndicatorKey('')
    setIsDetailOpen(false)
  }, [
    cycle,
    selectedBasicEducationFilterKey,
    selectedGroupKey,
    thematicGroups,
  ])

  function handleGroupSelect(groupKey) {
    setSelectedGroupKey(groupKey)
    setSelectedBasicEducationFilterKey('todos')
    setSelectedIndicatorKey('')
    setIsDetailOpen(false)
    setSearchQuery('')
  }

  function handleBasicEducationFilterSelect(filterKey) {
    setSelectedBasicEducationFilterKey(filterKey)
    setSelectedIndicatorKey('')
    setIsDetailOpen(false)
    setSearchQuery('')
  }

  function handleCardSelect(itemKey) {
    detailNavigation.prepareDetail(itemKey, { captureGridPosition: true })
    setSelectedIndicatorKey(itemKey)
    setIsDetailOpen(true)
    setHashContext(cycle === 'pne_2014_2024' ? 'pne2014' : 'pne2026', { detalhe: itemKey })
  }

  function handleBackToGrid() {
    const returnKey = activeIndicatorKey
    setIsDetailOpen(false)
    setSelectedIndicatorKey('')
    setHashContext(cycle === 'pne_2014_2024' ? 'pne2014' : 'pne2026')
    detailNavigation.restoreGrid(returnKey)
  }

  function handleAdjacentMeta(itemKey) {
    detailNavigation.prepareDetail(itemKey)
    setSelectedIndicatorKey(itemKey)
    setIsDetailOpen(true)
    setHashContext(cycle === 'pne_2014_2024' ? 'pne2014' : 'pne2026', { detalhe: itemKey })
  }

  return (
    <div className={`page-stack cycle-page${isShowingDetail ? ' cycle-page--detail' : ''}`}>
      {isShowingDetail ? <h1 className="u-sr-only">{title}</h1> : null}
      {!isShowingDetail ? <PnePageHeader
        asideLabel="Resumo dos indicadores do ciclo"
        asideContent={<dl className="pne-page-header__metrics">
          <PneHeaderMetric
            detail={cycleCopy.summary.totalDetail}
            label={cycleCopy.summary.totalLabel}
            tone="info"
            value={cycleManagementStats.monitorableTotal}
          />
          <PneHeaderMetric
            detail={cycleManagementStats.monitorableTotal
              ? `${cycleManagementStats.achievedPercent}% ${cycleCopy.summary.detailLabel}`
              : cycleCopy.summary.emptyDetail}
            label={cycleCopy.summary.achievedLabel}
            tone="success"
            value={cycleManagementStats.monitorableTotal
              ? cycleManagementStats.achieved
              : '-'}
          />
          <PneHeaderMetric
            detail={cycleManagementStats.monitorableTotal
              ? `${cycleManagementStats.attentionPercent}% ${cycleCopy.summary.detailLabel}`
              : cycleCopy.summary.emptyDetail}
            label={cycleCopy.summary.belowLabel}
            tone="attention"
            value={cycleManagementStats.monitorableTotal
              ? cycleManagementStats.attention
              : '-'}
          />
        </dl>}
        context={<>Município em foco: <strong>{selectedMunicipio}</strong></>}
        description={cycleCopy.supportText}
        eyebrow={cycleCopy.eyebrow}
        title={title}
        variant="listing"
      /> : null}

      <section className="cycle-workspace cycle-card-workspace">
        {isShowingDetail ? (
          <div className="cycle-detail-view" ref={detailNavigation.detailViewRef}>
            <DetailNavigation
              activeIndex={activeIndex}
              itemLabel="Meta"
              itemPlural="metas"
              nextItem={nextItem}
              nextLabel="Próxima meta"
              onBack={handleBackToGrid}
              onNext={handleAdjacentMeta}
              onPrevious={handleAdjacentMeta}
              previousItem={previousItem}
              statusLabel={activeThemeLabel}
              statusTone="info"
              total={filteredGroupItems.length}
            />
            <IndicatorDetail
              cycle={cycle}
              inequalityPilot={shouldLoadInequalityPilot ? inequalityDiagnostic?.inequalityPilot : null}
              inequalityPilotLoading={shouldLoadInequalityPilot && inequalityPilotLoading}
              item={activeItem}
              municipioData={municipioData}
              result={activeResult}
            />
            <DetailNavigation
              activeIndex={activeIndex}
              isBottom
              itemLabel="Meta"
              itemPlural="metas"
              nextItem={nextItem}
              nextLabel="Próxima meta"
              onBack={handleBackToGrid}
              onNext={handleAdjacentMeta}
              onPrevious={handleAdjacentMeta}
              previousItem={previousItem}
              statusLabel={activeThemeLabel}
              statusTone="info"
              total={filteredGroupItems.length}
            />
          </div>
        ) : (
          <>
            <div className="cycle-filter-panel platform-filter-panel">
              <div className="cycle-filter-panel__heading platform-exploration-toolbar">
                <div>
                  <span className="eyebrow">Temas das metas</span>
                  <h2>{selectedGroup?.label ?? 'Metas do ciclo'}</h2>
                </div>
                <SearchField
                  ariaLabel="Buscar meta"
                  className="cycle-search platform-search-field"
                  onChange={(event) => setSearchQuery(event.target.value)}
                  onClear={() => setSearchQuery('')}
                  placeholder="Buscar meta..."
                  value={searchQuery}
                />
              </div>

              <CategoryTabs
                categories={thematicGroups}
                selectedCategory={selectedGroup?.key}
                onSelectCategory={handleGroupSelect}
                ariaLabel="Temas"
              />

              {selectedGroup?.filters?.length ? (
                <div className="basic-education-filter-wrap">
                  <div className="basic-education-filter-wrap__header">
                    <span>Etapa</span>
                  </div>
                  <BasicEducationFilter
                    filters={selectedGroup.filters}
                    selectedFilter={selectedBasicEducationFilter?.key}
                    onSelectFilter={handleBasicEducationFilterSelect}
                  />
                </div>
              ) : null}
            </div>

            {filteredGroupItems.length === 0 ? (
              <div className="meta-grid-empty">
                <p>Nenhum indicador disponível para este município neste tema.</p>
              </div>
            ) : (
              <div className="meta-card-grid">
                {filteredGroupItems.map((item) => (
                  <MetaCard
                    buttonRef={(node) => detailNavigation.registerCard(item.key, node)}
                    cycle={cycle}
                    isSelected={isDetailOpen && item.key === selectedIndicatorKey}
                    item={item}
                    details={municipioDetails?.[item.key]}
                    key={item.key}
                    onSelect={() => handleCardSelect(item.key)}
                    result={normalizedMunicipioResults?.[item.key]}
                    stateReference={stateReference}
                    stageLabel={
                      selectedGroup?.key === 'educacao_basica'
                        ? getStageTagLabel(item.key, selectedGroup.filters)
                        : null
                    }
                  />
                ))}
              </div>
            )}

            <DataSourceNote className="cycle-source-line" source={CYCLE_SOURCE_NOTE} />
            {cycle === 'pne_2026_2036' ? (
              <p className="cycle-complementary-note">
                Dados complementares estão disponíveis em Indicadores de Educação.
                Uma meta legal pode ter mais de um indicador associado; por isso o total
                de indicadores pode ser maior que o total de metas acompanhadas.
              </p>
            ) : null}
          </>
        )}
      </section>
    </div>
  )
}

function enrichGoalRefs(categories, cycle) {
  const refMap = cycle === 'pne_2026_2036'
    ? PNE_2026_INDICATOR_GOAL_REFS
    : cycle === 'pne_2014_2024'
      ? PNE_2014_INDICATOR_GOAL_REFS
      : null

  if (!refMap) return categories

  return categories.map((category) => ({
    ...category,
    items: (category.items ?? []).map((item) => ({
      ...item,
      ...(refMap[item.key]
        ? { metaRef: refMap[item.key] }
        : {}),
    })),
  }))
}

function PneHeaderMetric({ detail, label, tone, value }) {
  return (
    <div className={`pne-page-header__metric pne-page-header__metric--${tone}`}>
      <dt>{label}</dt>
      <dd>{value}</dd>
      <small>{detail}</small>
    </div>
  )
}

function BasicEducationFilter({ filters, selectedFilter, onSelectFilter }) {
  return (
    <SegmentedControl
      ariaLabel="Etapas da Educação Básica"
      className="basic-education-filter platform-segmented-control"
      optionClassName="basic-education-filter__chip platform-segmented-option"
      options={filters.map(({ key, label }) => ({ key, label }))}
      onSelect={onSelectFilter}
      selectedKey={selectedFilter}
    />
  )
}

function getStageTagLabel(itemKey, stageFilters = []) {
  const stages = stageFilters
    .filter((filter) => filter.key !== 'todos' && filterIncludesItem(filter, itemKey))
    .map((filter) => filter.key)

  if (!stages.length) return null
  if (stages.length >= 3) return 'Todas as etapas'

  if (stages.length === 1) {
    return STAGE_LABELS[stages[0]] ?? null
  }

  return stages
    .map((stageKey) => STAGE_COMPACT_LABELS[stageKey])
    .filter(Boolean)
    .join(' + ')
}

function filterIncludesItem(filter, itemKey) {
  return (
    filter.indicatorKeys?.includes(itemKey) ||
    filter.items?.some((item) => item.key === itemKey)
  )
}

const STAGE_LABELS = {
  educacao_infantil: 'Educação Infantil',
  ensino_fundamental: 'Ensino Fundamental',
  ensino_medio: 'Ensino Médio',
}

const STAGE_COMPACT_LABELS = {
  educacao_infantil: 'Infantil',
  ensino_fundamental: 'Fundamental',
  ensino_medio: 'Médio',
}

function buildCycleManagementStats(categories, municipioResults, cycle, municipioDetails) {
  const stats = {
    achieved: 0,
    achievedPercent: 0,
    attention: 0,
    monitorableTotal: 0,
  }

  const allCycleItems = categories.flatMap((category) => category.items ?? [])

  allCycleItems.forEach((item) => {
    const result = municipioResults?.[item.key]
    const accumulativePresentation = buildPne2026AccumulativePresentationModel({
      cycle,
      indicatorKey: item.key,
      details: municipioDetails?.[item.key],
      presentationMode: item.presentationMode,
    })

    if (
      item.include_in_cycle_summary === false ||
      item.monitoring_mode === 'approximate_reference' ||
      item.tracks_goal === false ||
      !result ||
      result.available === false ||
      result.tracks_goal === false
    ) {
      return
    }

    if (accumulativePresentation && accumulativePresentation.summaryState === null) {
      return
    }

    stats.monitorableTotal += 1
    if (accumulativePresentation ? accumulativePresentation.summaryState === 'achieved' : result.atingida === true) {
      stats.achieved += 1
    } else {
      stats.attention += 1
    }
  })

  stats.achievedPercent = stats.monitorableTotal
    ? Math.round((stats.achieved / stats.monitorableTotal) * 100)
    : 0

  stats.attentionPercent = stats.monitorableTotal
    ? Math.round((stats.attention / stats.monitorableTotal) * 100)
    : 0

  return stats
}
