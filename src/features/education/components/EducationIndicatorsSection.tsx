import type { ChangeEvent, RefObject } from 'react'
import { ContentState } from '../../../components/ContentState.jsx'
import { DetailNavigation } from '../../../components/DetailNavigation.jsx'
import { EducationIndicatorCard } from '../../../components/EducationIndicatorCard.jsx'
import { IndigenousEducationPanel } from '../../../components/IndigenousEducationPanel.jsx'
import { SearchField } from '../../../components/SearchField.jsx'
import { SistemaSPanel } from '../../../components/SistemaSPanel.jsx'
import {
  EDUCATION_SECTION_GROUPS,
  EDUCATION_SECTION_KEYS,
} from '../../../data/educationIndicatorCatalog.js'
import { selectEducationVisibleGroups } from '../educationSelectors'
import { formatIndicatorCount } from '../educationFormatters'
import { EducationIndicatorDetailView } from './EducationIndicatorDetailView'
import { EducationSectionBar } from './EducationSectionBar'
import { SpecialEducationDetailView } from './SpecialEducationDetailView'
import {
  isSpecialEducationIndicatorId,
  type SpecialEducationCut,
  type SpecialEducationMunicipalDocument,
} from '../specialEducationTypes'
import type {
  EducationIndicatorKey,
  EducationIndicatorResult,
  EducationSection,
  EducationSectionKey,
} from '../educationTypes'

interface EducationDetailNavigationController {
  detailViewRef: RefObject<HTMLDivElement | null>
  registerCard: (itemKey: string, node: HTMLButtonElement | null) => void
}

interface EducationIndicatorsSectionActions {
  onAdjacentIndicator: (indicatorKey: EducationIndicatorKey) => void
  onBackToIndicators: () => void
  onIndicatorCardSelect: (indicatorKey: EducationIndicatorKey) => void
  onOpenSistemaS: (indicatorKey?: string) => void
  onSearchChange: (value: string) => void
}

interface EducationIndicatorsSectionViewModel {
  activeIndicator: EducationIndicatorResult | null
  activeIndicatorIndex: number
  blocos: unknown
  detailNavigation: EducationDetailNavigationController
  filteredItems: EducationIndicatorResult[]
  hasSistemaS: boolean
  indicatorCount: number
  isDetailOpen: boolean
  isIndigenousDetail: boolean
  isShowingIndicatorDetail: boolean
  isSistemaSTheme: boolean
  nextIndicator: EducationIndicatorResult | null
  navigableContentCount: number
  previousIndicator: EducationIndicatorResult | null
  searchQuery: string
  section?: EducationSection
  selectedSistemaSIndicator: string
  selectedIndigenousUnit: string
  selectedIndicatorKey: EducationIndicatorKey
  selectedSectionKey: EducationSectionKey
  selectedSpecialEducationCut: SpecialEducationCut
  specialEducationState: {
    data: { document: SpecialEducationMunicipalDocument } | null
    error: string | null
    loading: boolean
  }
}

interface EducationIndicatorsSectionProps {
  actions: EducationIndicatorsSectionActions
  viewModel: EducationIndicatorsSectionViewModel
}

interface EducationDetailNavigationProps {
  activeIndex: number
  contextLabel?: string
  isBottom?: boolean
  nextIndicator: EducationIndicatorResult | null
  onBack: () => void
  onNext: (key: EducationIndicatorKey) => void
  onPrevious: (key: EducationIndicatorKey) => void
  previousIndicator: EducationIndicatorResult | null
  showSequence?: boolean
  total: number
}

export function EducationIndicatorsSection({ actions, viewModel }: EducationIndicatorsSectionProps) {
  const {
    activeIndicator,
    activeIndicatorIndex,
    blocos,
    detailNavigation,
    filteredItems,
    hasSistemaS,
    indicatorCount,
    isDetailOpen,
    isIndigenousDetail,
    isShowingIndicatorDetail,
    isSistemaSTheme,
    nextIndicator,
    navigableContentCount,
    previousIndicator,
    searchQuery,
    section,
    selectedSistemaSIndicator,
    selectedIndigenousUnit,
    selectedIndicatorKey,
    selectedSectionKey,
    selectedSpecialEducationCut,
    specialEducationState,
  } = viewModel
  const {
    onAdjacentIndicator,
    onBackToIndicators,
    onIndicatorCardSelect,
    onOpenSistemaS,
    onSearchChange,
  } = actions
  const groups = EDUCATION_SECTION_GROUPS[selectedSectionKey] ?? []
  const normalizedSearchQuery = searchQuery.trim().toLocaleLowerCase('pt-BR')
  const visibleGroups = selectEducationVisibleGroups(groups, filteredItems)
  const showSistemaSGroup =
    selectedSectionKey === EDUCATION_SECTION_KEYS.modalities &&
    hasSistemaS &&
    (!normalizedSearchQuery || 'sistema s oferta profissional'.includes(normalizedSearchQuery))

  if (isSistemaSTheme) {
    return (
      <div className="education-detail-view education-detail-view--sistema-s" ref={detailNavigation.detailViewRef}>
        <SistemaSPanel
          blocos={blocos}
          initialIndicatorKey={selectedSistemaSIndicator}
          onOpenDetails={undefined}
        />
      </div>
    )
  }

  if (isIndigenousDetail) {
    return (
      <div className="education-detail-view" ref={detailNavigation.detailViewRef}>
        <IndigenousEducationPanel blocos={blocos} initialUnitKey={selectedIndigenousUnit} />
      </div>
    )
  }

  if (isShowingIndicatorDetail) {
    const isSpecialEducationDetail = isSpecialEducationIndicatorId(selectedIndicatorKey)
    const showDetailSequence = activeIndicator?.availableInReferenceYear !== false
    return (
      <div className="education-detail-view" ref={detailNavigation.detailViewRef}>
        <EducationDetailNavigation
          activeIndex={activeIndicatorIndex}
          contextLabel={section?.label}
          nextIndicator={nextIndicator}
          onBack={onBackToIndicators}
          onNext={onAdjacentIndicator}
          onPrevious={onAdjacentIndicator}
          previousIndicator={previousIndicator}
          showSequence={showDetailSequence}
          total={navigableContentCount}
        />
        {isSpecialEducationDetail && specialEducationState.data ? (
          <SpecialEducationDetailView
            cut={selectedSpecialEducationCut}
            document={specialEducationState.data.document}
            indicatorId={selectedIndicatorKey}
          />
        ) : (
          <EducationIndicatorDetailView
            blocos={blocos}
            indicator={activeIndicator}
          />
        )}
        <EducationDetailNavigation
          activeIndex={activeIndicatorIndex}
          contextLabel={section?.label}
          isBottom
          nextIndicator={nextIndicator}
          onBack={onBackToIndicators}
          onNext={onAdjacentIndicator}
          onPrevious={onAdjacentIndicator}
          previousIndicator={previousIndicator}
          showSequence={showDetailSequence}
          total={navigableContentCount}
        />
      </div>
    )
  }

  return (
    <>
      <EducationSectionBar
        description={section?.description}
        id="education-thematic-title"
        search={(
          <div className="education-section-bar__search">
          <div>
            <span className="eyebrow">{'Indicadores da seção'}</span>
            <strong className="education-section-filter-count">{formatIndicatorCount(indicatorCount)}</strong>
          </div>
          <SearchField
            ariaLabel="Buscar indicador"
            className="cycle-search platform-search-field"
            onChange={(event: ChangeEvent<HTMLInputElement>) => onSearchChange(event.target.value)}
            onClear={() => onSearchChange('')}
            placeholder="Buscar indicador..."
            value={searchQuery}
          />
          </div>
        )}
        title={section?.label}
      />

      {selectedSectionKey === EDUCATION_SECTION_KEYS.modalities && specialEducationState.loading ? (
        <ContentState as="p" kind="loading" className="state-box state-box--loading special-education-load-state">
          Carregando indicadores de Educação Especial…
        </ContentState>
      ) : null}
      {selectedSectionKey === EDUCATION_SECTION_KEYS.modalities && specialEducationState.error ? (
        <ContentState as="p" kind="unavailable" className="state-box special-education-load-state">
          Os indicadores de Educação Especial não puderam ser carregados neste momento.
        </ContentState>
      ) : null}

      {filteredItems.length === 0 && !showSistemaSGroup ? (
        <div className="meta-grid-empty education-indicator-grid-empty">
          <ContentState as="p" kind="noResults">
            {searchQuery.trim()
              ? `Nenhum indicador encontrado para “${searchQuery.trim()}” nesta seção.`
              : 'Nenhum indicador disponível para esta seção.'}
          </ContentState>
        </div>
      ) : (
        <div className="education-indicator-groups">
          {visibleGroups.map((group) => (
            <section className={`education-indicator-group education-indicator-group--${group.key}`} key={group.key} aria-labelledby={`education-group-${group.key}`}>
              <div className="education-indicator-group__heading">
                <div>
                  <span className="eyebrow">Indicadores relacionados</span>
                  <h3 id={`education-group-${group.key}`}>{group.label}</h3>
                </div>
                <span>{formatEducationGroupCount(group)}</span>
              </div>
              <p className="education-indicator-group__description">{group.description}</p>
              <div className="education-indicator-card-grid">
                {group.items.map((item) => (
                  <EducationIndicatorCard
                    buttonRef={(node: HTMLButtonElement | null) => detailNavigation.registerCard(item.key, node)}
                    indicator={item}
                    isSelected={isDetailOpen && item.key === selectedIndicatorKey}
                    key={item.key}
                    onSelect={() => onIndicatorCardSelect(item.key)}
                  />
                ))}
              </div>
            </section>
          ))}
          {showSistemaSGroup ? (
            <section className="education-special-group" aria-labelledby="education-section-sistema-s-title">
              <div className="education-indicator-group__heading">
                <div>
                  <span className="eyebrow">{section?.label}</span>
                  <h3 id="education-section-sistema-s-title">Sistema S</h3>
                </div>
                <span>4 indicadores</span>
              </div>
              <SistemaSPanel blocos={blocos} mode="summary" onOpenDetails={onOpenSistemaS} />
            </section>
          ) : null}
        </div>
      )}
    </>
  )
}

function formatEducationGroupCount(group: { key?: string; items?: unknown[]; indicatorCount?: number }): string {
  const count = group.indicatorCount ?? group.items?.length ?? 0
  if (group.key === 'rede-escolar') return `${count} ${count === 1 ? 'panorama' : 'panoramas'}`
  return formatIndicatorCount(count)
}

function EducationDetailNavigation({
  activeIndex,
  contextLabel,
  isBottom = false,
  nextIndicator,
  onBack,
  onNext,
  onPrevious,
  previousIndicator,
  showSequence = true,
  total,
}: EducationDetailNavigationProps) {
  return (
    <DetailNavigation
      activeIndex={activeIndex}
      className={`education-detail-nav${isBottom ? ' education-detail-nav--bottom' : ''}`}
      contextLabel={contextLabel}
      isBottom={isBottom}
      nextLabel={undefined}
      nextItem={nextIndicator}
      onBack={onBack}
      onNext={onNext}
      onPrevious={onPrevious}
      previousItem={previousIndicator}
      showSequence={showSequence}
      showBack={isBottom}
      total={total}
    />
  )
}
