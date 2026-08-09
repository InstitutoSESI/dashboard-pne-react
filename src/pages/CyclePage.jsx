import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { DataSourceNote } from '../components/DataSourceNote'
import { DetailNavigation } from '../components/DetailNavigation'
import { IndicatorDetail } from '../components/IndicatorDetail'
import { MetaCard } from '../components/MetaCard'
import { SearchField } from '../components/SearchField'
import { PNE_2026_INDICATOR_GOAL_REFS } from '../data/pne2026IndicatorGoalRefs'
import {
  PNE_2026_GOAL_INDICATOR_CONTRACT,
  PNE_2026_RELATIONSHIP_MODES,
  canPne2026RelationEnterCycleSummary,
  getPne2026RelationContext,
  reconcilePne2026MunicipalResult,
} from '../data/pne2026GoalIndicatorContract'
import { PNE_2014_INDICATOR_GOAL_REFS } from '../data/pne2014IndicatorGoalRefs'
import { buildThematicGroups } from '../data/thematicGroups'
import { loadMunicipioDetails, loadPneStateReference } from '../data/staticData'
import { normalizePopulationPercentResults } from '../utils/indicatorValues'
import { resolvePneCycleMunicipalResults } from '../utils/pneCycleDiagnosticResults'
import { getPneCycleCopy } from '../utils/pneCycleCopy'
import {
  applyPneCycleVisibilityPolicy,
  canIncludePneCycleSummary,
} from '../utils/pneDisplayRules'
import { resolveDetailSequence, useDetailViewNavigation } from '../hooks/useDetailViewNavigation'
import { PnePageHeader } from '../components/PnePageHeader'
import { getHashContext, setHashContext } from '../utils/hashNavigation'
import { useAsyncData } from '../utils/useAsyncData'
import { buildPne2026AccumulativePresentationModel } from '../utils/pneAccumulativeCycle'
import { useMunicipioDiagnostic } from '../hooks/useMunicipioDiagnostic'

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
  const municipalDiagnosticState = useMunicipioDiagnostic(
    cycle === 'pne_2026_2036' ? municipioData?.id_municipio : null,
  )
  const categories = useMemo(
    () => appendPne2026ComparableItems(
      enrichGoalRefs(indicadores?.cycles?.[cycle]?.categories ?? [], cycle),
      cycle,
    ),
    [indicadores, cycle],
  )
  const [selectedIndicatorKey, setSelectedIndicatorKey] = useState(initialDetailKey)
  const [isDetailOpen, setIsDetailOpen] = useState(Boolean(initialDetailKey))
  const [searchQuery, setSearchQuery] = useState('')
  const [activeThemeKey, setActiveThemeKey] = useState('')
  const previousCycleRef = useRef(cycle)
  const themeNavRef = useRef(null)
  const themeSectionRefs = useRef(new Map())
  const municipioResults = municipioData?.[cycle]?.indicadores ?? null
  const combinedMunicipioResults = useMemo(
    () => resolvePneCycleMunicipalResults(
      cycle,
      municipioResults,
      municipalDiagnosticState.data?.pne2026PublicDiagnostic,
    ),
    [cycle, municipalDiagnosticState.data, municipioResults],
  )
  const { data: stateReference } = useAsyncData(
    () => loadPneStateReference(cycle).catch(() => null),
    [cycle],
  )
  const {
    data: municipioDetails,
    loading: municipioDetailsLoading,
  } = useAsyncData(
    () => municipioData?.id_municipio ? loadMunicipioDetails(municipioData.id_municipio) : null,
    [municipioData?.id_municipio],
  )
  const allCycleItems = useMemo(
    () => categories.flatMap((category) => category.items ?? []),
    [categories],
  )
  const normalizedMunicipioResults = useMemo(
    () => normalizePopulationPercentResults(combinedMunicipioResults, allCycleItems, cycle),
    [combinedMunicipioResults, allCycleItems, cycle],
  )
  const visibleCategories = useMemo(
    () => applyPneCycleVisibilityPolicy(categories, normalizedMunicipioResults, cycle),
    [categories, normalizedMunicipioResults, cycle],
  )
  const thematicGroups = useMemo(
    () => buildThematicGroups(visibleCategories, cycle),
    [cycle, visibleCategories],
  )
  /*
   * Rodada "temas em scroll contínuo": a listagem deixou de exibir um tema por
   * vez. Todos os grupos temáticos são materializados de uma só vez e a barra
   * sticky passa a ser índice de navegação (âncora + scroll-spy), não filtro de
   * conteúdo. A busca é o único recorte da listagem e atravessa todos os grupos;
   * a etapa permanece visível como etiqueta contextual em cada cartão da
   * Educação Básica, sem criar uma segunda navegação concorrente.
   */
  const renderedGroups = useMemo(() => {
    const query = searchQuery.trim().toLocaleLowerCase('pt-BR')
    return thematicGroups.flatMap((group) => {
      const groupItems = group.items ?? []
      const items = query
        ? groupItems.filter((item) => item.label.toLocaleLowerCase('pt-BR').includes(query))
        : groupItems
      if (!items.length) return []
      return [{ ...group, items }]
    })
  }, [searchQuery, thematicGroups])
  const themeNavKeys = useMemo(
    () => renderedGroups.map((group) => group.key),
    [renderedGroups],
  )
  const themeNavSignature = themeNavKeys.join('|')
  /*
   * Sequência anterior/próxima do detalhe segue o grupo temático do item
   * aberto — o mesmo recorte que o leitor tem à vista na listagem.
   */
  const activeGroup = useMemo(
    () => renderedGroups.find((group) => (
      group.items.some((item) => item.key === selectedIndicatorKey)
    )) ?? null,
    [renderedGroups, selectedIndicatorKey],
  )
  const detailSequenceItems = useMemo(() => activeGroup?.items ?? [], [activeGroup])
  const activeItem = useMemo(
    () => detailSequenceItems.find((item) => item.key === selectedIndicatorKey) ?? null,
    [detailSequenceItems, selectedIndicatorKey],
  )
  const activeIndicatorKey = activeItem?.key ?? ''
  const activeResult = activeItem ? normalizedMunicipioResults?.[activeItem.key] : null
  const { activeIndex, previousItem, nextItem } = resolveDetailSequence(
    detailSequenceItems,
    activeIndicatorKey,
  )
  const cycleManagementStats = useMemo(
    () => buildCycleManagementStats(
      cycle === 'pne_2026_2036' ? categories : visibleCategories,
      normalizedMunicipioResults,
      cycle,
      municipioDetails,
    ),
    [categories, visibleCategories, normalizedMunicipioResults, cycle, municipioDetails],
  )
  const isCycleTransition = previousCycleRef.current !== cycle
  const isShowingDetail = Boolean(!isCycleTransition && isDetailOpen && activeItem)
  const shouldLoadInequalityPilot = cycle === 'pne_2026_2036'
    && isShowingDetail
    && activeItem?.key === 'basico_integral'
  const inequalityDiagnostic = shouldLoadInequalityPilot && municipioData?.id_municipio
    ? municipioDetails?._shared?.municipal_inequality ?? null
    : null
  const inequalityPilotLoading = shouldLoadInequalityPilot
    && Boolean(municipioData?.id_municipio)
    && municipioDetailsLoading
  const activeThemeLabel = activeGroup?.shortLabel ?? activeGroup?.label ?? null
  const detailNavigation = useDetailViewNavigation({
    activeKey: activeIndicatorKey,
    isOpen: isShowingDetail,
  })

  const registerThemeSection = useCallback((groupKey, node) => {
    if (node) themeSectionRefs.current.set(groupKey, node)
    else themeSectionRefs.current.delete(groupKey)
  }, [])

  useEffect(() => {
    setActiveThemeKey((current) => {
      if (!themeNavSignature) return ''
      const keys = themeNavSignature.split('|')
      return keys.includes(current) ? current : keys[0]
    })
  }, [themeNavSignature])

  /*
   * Scroll-spy da barra de temas. A janela útil (rootMargin) ignora o topo
   * coberto pelos sticky e a metade inferior da tela, de modo que o tema ativo
   * é o que ocupa a faixa de leitura, não o que apenas encostou na viewport.
   */
  useEffect(() => {
    if (isShowingDetail || !themeNavSignature) return undefined
    if (typeof IntersectionObserver === 'undefined') return undefined

    const keys = themeNavSignature.split('|')
    const nodes = keys
      .map((key) => themeSectionRefs.current.get(key))
      .filter(Boolean)
    if (!nodes.length) return undefined

    const intersecting = new Set()
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        const key = entry.target.dataset.themeKey
        if (!key) return
        if (entry.isIntersecting) intersecting.add(key)
        else intersecting.delete(key)
      })
      const nextKey = keys.find((key) => intersecting.has(key))
      if (nextKey) setActiveThemeKey(nextKey)
    }, { rootMargin: '-40% 0px -55% 0px', threshold: 0 })

    nodes.forEach((node) => observer.observe(node))
    return () => observer.disconnect()
  }, [isShowingDetail, themeNavSignature])

  /*
   * A barra sticky tem altura variável: os chips de tema quebram em uma, duas
   * ou três linhas conforme a largura da janela e o resultado da busca. Um
   * scroll-margin fixo ou escondia o título atrás da barra ou abria um vão
   * enorme. Aqui a altura medida vira --cycle-theme-nav-height no workspace, de
   * onde as seções a herdam (ver pne-cycle-experience.css, bloco final).
   */
  useEffect(() => {
    const node = themeNavRef.current
    const host = node?.parentElement
    if (!node || !host) return undefined

    function publishHeight() {
      const height = Math.round(node.getBoundingClientRect().height)
      if (height > 0) host.style.setProperty('--cycle-theme-nav-height', `${height}px`)
    }

    publishHeight()
    if (typeof ResizeObserver === 'undefined') return undefined
    const observer = new ResizeObserver(publishHeight)
    observer.observe(node)
    return () => observer.disconnect()
  }, [isShowingDetail, themeNavSignature])

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

  /* Troca de ciclo reinicia a leitura: busca, navegação temática e detalhe. */
  useEffect(() => {
    if (previousCycleRef.current === cycle) return

    previousCycleRef.current = cycle
    setSelectedIndicatorKey('')
    setIsDetailOpen(false)
    setSearchQuery('')
    setActiveThemeKey('')
  }, [cycle])

  function handleThemeNavSelect(groupKey) {
    setActiveThemeKey(groupKey)
    const node = themeSectionRefs.current.get(groupKey)
    if (!node) return
    const prefersReducedMotion = typeof window.matchMedia === 'function'
      && window.matchMedia('(prefers-reduced-motion: reduce)').matches
    node.scrollIntoView({
      behavior: prefersReducedMotion ? 'auto' : 'smooth',
      block: 'start',
    })
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
          {cycle === 'pne_2026_2036' ? (
            <>
              <PneHeaderMetric
                detail="Resultados disponíveis com referência prevista na meta"
                label="Referências previstas nas metas"
                tone="success"
                value={`${cycleManagementStats.legal.achieved} de ${cycleManagementStats.legal.total} alcançadas`}
              />
              <PneHeaderMetric
                detail="Resultados disponíveis com referência de acompanhamento"
                label="Referências de acompanhamento"
                tone="info"
                value={`${cycleManagementStats.tracking.achieved} de ${cycleManagementStats.tracking.total} alcançadas`}
              />
              <PneHeaderMetric
                detail="Indicadores do ciclo sem resultado comparável no período"
                label="Sem comparação no período"
                tone="info"
                value={`${cycleManagementStats.withoutComparison} indicadores`}
              />
            </>
          ) : (
            <>
          <PneHeaderMetric
            detail={cycleCopy.summary.totalDetail}
            label={cycleCopy.summary.totalLabel}
            tone="info"
            value={cycleManagementStats.displayedTotal}
          />
          <PneHeaderMetric
            detail={cycleManagementStats.displayedTotal
              ? `${cycleManagementStats.monitorableTotal} de ${cycleManagementStats.displayedTotal} indicadores exibidos`
              : cycleCopy.summary.emptyDetail}
            label={cycleCopy.summary.conclusiveLabel}
            tone="info"
            value={cycleManagementStats.monitorableTotal}
          />
          <PneHeaderMetric
            detail={cycleManagementStats.monitorableTotal
              ? `${cycleManagementStats.achieved} de ${cycleManagementStats.monitorableTotal} conclusivos · ${cycleManagementStats.achievedPercent}%`
              : cycleCopy.summary.emptyDetail}
            label={cycleCopy.summary.achievedLabel}
            tone="success"
            value={cycleManagementStats.monitorableTotal
              ? cycleManagementStats.achieved
              : '-'}
          />
          <PneHeaderMetric
            detail={cycleManagementStats.monitorableTotal
              ? `${cycleManagementStats.attention} de ${cycleManagementStats.monitorableTotal} conclusivos · ${cycleManagementStats.attentionPercent}%`
              : cycleCopy.summary.emptyDetail}
            label={cycleCopy.summary.belowLabel}
            tone="attention"
            value={cycleManagementStats.monitorableTotal
              ? cycleManagementStats.attention
              : '-'}
          />
            </>
          )}
        </dl>}
        description={cycleCopy.supportText}
        eyebrow={cycleCopy.eyebrow}
        title={<>{title}<span className="pne-page-header__print-context"> · {selectedMunicipio}</span></>}
        variant="listing"
      /> : null}

      {!isShowingDetail && cycle === 'pne_2026_2036' ? <PneStatusLegend /> : null}

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
              total={detailSequenceItems.length}
            />
            <IndicatorDetail
              cycle={cycle}
              inequalityPilot={shouldLoadInequalityPilot ? inequalityDiagnostic?.inequalityPilot : null}
              inequalityPilotLoading={inequalityPilotLoading}
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
              total={detailSequenceItems.length}
            />
          </div>
        ) : (
          <>
            {/*
              * Navegação única do ciclo, com a mesma anatomia compartilhada do
              * filtro de Metas legais: título e busca na primeira linha, rótulo
              * e temas na segunda. Os temas continuam sendo âncora + scroll-spy;
              * a busca é o único recorte do conteúdo.
              */}
            <nav
              aria-labelledby="cycle-theme-navigation-title"
              className="cycle-theme-nav platform-filter-panel"
              ref={themeNavRef}
            >
              <div className="cycle-theme-nav__heading platform-exploration-toolbar">
                <h2 id="cycle-theme-navigation-title">Metas e acompanhamento municipal</h2>
                <SearchField
                  ariaLabel="Buscar meta"
                  className="cycle-search platform-search-field cycle-theme-nav__search"
                  onChange={(event) => setSearchQuery(event.target.value)}
                  onClear={() => setSearchQuery('')}
                  placeholder="Buscar meta..."
                  value={searchQuery}
                />
              </div>

              <div className="cycle-theme-nav__themes platform-filter-group">
                <span>Navegar por tema</span>
                <div
                  aria-label="Temas das metas"
                  className="cycle-theme-nav__chips platform-filter-list"
                  role="group"
                >
                  {renderedGroups.map((group) => {
                    const isActiveTheme = group.key === activeThemeKey
                    return (
                      <button
                        aria-current={isActiveTheme ? 'true' : undefined}
                        className={`cycle-theme-nav__chip platform-filter-option${isActiveTheme ? ' is-active' : ''}`}
                        key={group.key}
                        onClick={() => handleThemeNavSelect(group.key)}
                        title={group.label}
                        type="button"
                      >
                        <span className="cycle-theme-nav__chip-label">
                          {group.label}
                        </span>
                        <span className="cycle-theme-nav__chip-count">{group.items.length}</span>
                      </button>
                    )
                  })}
                </div>
              </div>
            </nav>

            {renderedGroups.length === 0 ? (
              <div className="meta-grid-empty">
                <p>
                  {searchQuery.trim()
                    ? `Nenhuma meta encontrada para “${searchQuery.trim()}” neste ciclo.`
                    : 'Nenhum indicador disponível para este município neste ciclo.'}
                </p>
              </div>
            ) : (
              <div className="cycle-theme-sections">
                {renderedGroups.map((group) => {
                  const hasContextTitle = Boolean(group.contextTitle)
                  return (
                  <section
                    aria-labelledby={`tema-${group.key}-titulo`}
                    className="cycle-theme-section"
                    data-theme-key={group.key}
                    id={`tema-${group.key}`}
                    key={group.key}
                    ref={(node) => registerThemeSection(group.key, node)}
                  >
                    <div className="cycle-theme-section__heading">
                      <div>
                        {hasContextTitle ? <span className="eyebrow">{group.label}</span> : null}
                        <h2 id={`tema-${group.key}-titulo`}>
                          {group.contextTitle ?? group.label}
                        </h2>
                      </div>
                      <span className="cycle-theme-section__count">
                        {formatThemeIndicatorCount(group.items.length)}
                      </span>
                    </div>

                    <div className="meta-card-grid">
                      {group.items.map((item) => (
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
                            group.key === 'educacao_basica'
                              ? getStageTagLabel(item.key, group.filters)
                              : null
                          }
                        />
                      ))}
                    </div>
                  </section>
                  )
                })}
              </div>
            )}

            <footer className="cycle-card-workspace__notes">
              <DataSourceNote className="cycle-source-line" source={CYCLE_SOURCE_NOTE} />
              {cycle === 'pne_2026_2036' ? (
                <p className="cycle-complementary-note">
                  As referências de acompanhamento são aproximações municipais úteis e
                  não comprovam, isoladamente, o cumprimento integral da meta legal.
                </p>
              ) : null}
            </footer>
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
    items: (category.items ?? []).map((item) => {
      const metaRef = refMap[item.key]
      const context = cycle === 'pne_2026_2036' && metaRef
        ? getPne2026RelationContext(metaRef, item.key)
        : null
      const relation = context?.relation

      return {
        ...item,
        ...(metaRef ? { metaRef } : {}),
        ...(relation
          ? {
              monitoringMode: relation.mode,
              canDistance: relation.canDistance,
              canStatus: relation.canStatus,
              canProjection: relation.canProjection,
              includeInCycleSummary: canPne2026RelationEnterCycleSummary(relation),
              includeInReferenceSummary: relation.includeInReferenceSummary,
              desc:
                relation.publicDescriptionOverride
                ?? context.indicator?.publicDescription
                ?? item.desc,
              label:
                relation.publicLabelOverride
                ?? context.indicator?.publicTitle
                ?? item.label,
              title:
                relation.publicLabelOverride
                ?? context.indicator?.publicTitle
                ?? item.title
                ?? item.label,
            }
          : {}),
      }
    }),
  }))
}

function appendPne2026ComparableItems(categories, cycle) {
  if (cycle !== 'pne_2026_2036') return categories
  const existingKeys = new Set(
    categories.flatMap((category) => (
      (category.items ?? []).map((item) => item.key)
    )),
  )
  const items = PNE_2026_GOAL_INDICATOR_CONTRACT.relations.flatMap((relation) => {
    if (
      existingKeys.has(relation.indicatorId)
      || !canPne2026RelationEnterCycleSummary(relation)
      || ![
        PNE_2026_RELATIONSHIP_MODES.PROGRESS,
        PNE_2026_RELATIONSHIP_MODES.TRACKING,
      ].includes(relation.mode)
    ) return []
    const indicator = PNE_2026_GOAL_INDICATOR_CONTRACT.indicators[relation.indicatorId]
    if (!indicator) return []
    return [{
      key: relation.indicatorId,
      label: relation.publicLabelOverride ?? indicator.publicTitle,
      title: relation.publicLabelOverride ?? indicator.publicTitle,
      desc: relation.publicDescriptionOverride ?? indicator.publicDescription,
      metaRef: relation.goalId,
      value_mode: indicator.unit,
      monitoringMode: relation.mode,
      canDistance: relation.canDistance,
      canStatus: relation.canStatus,
      canProjection: relation.canProjection,
      includeInCycleSummary: true,
      includeInReferenceSummary: relation.includeInReferenceSummary,
    }]
  })
  return items.length
    ? [...categories, { key: 'pne2026_comparable', items }]
    : categories
}

function formatThemeIndicatorCount(count) {
  return `${count} ${count === 1 ? 'indicador' : 'indicadores'}`
}

function PneHeaderMetric({ detail, label, tone, value }) {
  return (
    <div
      className={`pne-page-header__metric pne-page-header__metric--${tone}`}
      title={typeof detail === 'string' ? detail : undefined}
    >
      <dt>{label}</dt>
      <dd>{value}</dd>
      <small>{detail}</small>
    </div>
  )
}

function PneStatusLegend() {
  const items = [
    { label: 'Referência alcançada', tone: 'success' },
    { label: 'Abaixo da referência prevista na meta', tone: 'danger' },
    { label: 'Abaixo da referência de acompanhamento', tone: 'warning' },
  ]

  return (
    <aside className="cycle-status-legend" aria-label="Legenda das situações">
      <strong>Legenda</strong>
      <div>
        {items.map((item) => (
          <span key={item.tone}>
            <i className={`cycle-status-legend__dot cycle-status-legend__dot--${item.tone}`} aria-hidden="true" />
            {item.label}
          </span>
        ))}
      </div>
    </aside>
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
    displayedTotal: 0,
    monitorableTotal: 0,
    legal: { achieved: 0, total: 0 },
    tracking: { achieved: 0, total: 0 },
    withoutComparison: 0,
  }

  const allCycleItems = categories.flatMap((category) => category.items ?? [])
  stats.displayedTotal = allCycleItems.length

  allCycleItems.forEach((item) => {
    const municipalResult = municipioResults?.[item.key]
    const result = cycle === 'pne_2026_2036'
      ? reconcilePne2026MunicipalResult({
          goalId: item.metaRef,
          indicatorId: item.key,
          result: municipalResult,
        }).result
      : municipalResult
    const accumulativePresentation = buildPne2026AccumulativePresentationModel({
      cycle,
      indicatorKey: item.key,
      details: municipioDetails?.[item.key],
      presentationMode: item.presentationMode,
    })

    if (
      cycle === 'pne_2026_2036'
      && ['unavailable', 'not_applicable', 'suppressed'].includes(result?.dataStatus)
      && item.includeInCycleSummary === true
    ) {
      stats.withoutComparison += 1
      return
    }

    if (!canIncludePneCycleSummary({ cycleId: cycle, item, result })) {
      return
    }

    if (accumulativePresentation && accumulativePresentation.summaryState === null) {
      return
    }

    stats.monitorableTotal += 1
    const achieved = accumulativePresentation
      ? accumulativePresentation.summaryState === 'achieved'
      : result.atingida === true
    const mode = item.monitoringMode ?? result.monitoringMode ?? result.monitoring_mode
    const bucket = mode === 'tracking' ? stats.tracking : stats.legal
    bucket.total += 1
    if (achieved) {
      stats.achieved += 1
      bucket.achieved += 1
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
