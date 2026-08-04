import { useMemo, useState } from 'react'
import { PneSourceNotes } from '../components/PneSourceNotes'
import { MunicipalitySelector } from '../components/MunicipalitySelector'
import { PnePageHeader } from '../components/PnePageHeader'
import { SearchField } from '../components/SearchField'
import {
  PNE_2026_LEGAL_GOAL_INDICATOR_MAP,
  PNE_2026_LEGAL_GOAL_MAPPING_METADATA,
  getPne2026PublicLegalGoalRelations,
} from '../data/pne2026LegalGoalIndicatorMap'
import {
  formatIndicatorValue,
  resolveIndicatorUnit,
} from '../utils/format'
import { normalizePopulationPercentResults } from '../utils/indicatorValues'
import {
  PNE_2026_RELATIONSHIP_MODES,
  reconcilePne2026MunicipalResult,
} from '../data/pne2026GoalIndicatorContract'
import { useMunicipioDiagnostic } from '../hooks/useMunicipioDiagnostic'
import { mergePne2026DiagnosticResults } from '../utils/pneCycleDiagnosticResults'
import {
  PNE_LEGAL_GOAL_CATEGORIES,
  PNE_LEGAL_GOAL_CATEGORY_LABELS,
  buildPneLegalGoalsSummary,
  getPne2026CanonicalCycleItems,
  getPneLegalDataStatusLabel,
  getPneLegalGoalCategory,
  getPneLegalRelationPresentation,
  indexPne2026DiagnosticResults,
} from '../utils/pneLegalGoalsPresentation'
import { getPneComparisonStatusPresentation } from '../utils/pneIndicatorPresentation'

const PNE_2026_CYCLE = 'pne_2026_2036'
const EMPTY_ARRAY = []

const COVERAGE_LABELS = PNE_LEGAL_GOAL_CATEGORY_LABELS

const ALL_THEMES_FILTER = 'todos'
const UNMAPPED_THEME_LABEL = 'Tema sem indicador associado'

const PERCENT_FORMATTER = new Intl.NumberFormat('pt-BR', {
  maximumFractionDigits: 1,
  minimumFractionDigits: 0,
})

export function PneLegalGoalsPage({
  indicadores,
  municipioData,
  municipalities = EMPTY_ARRAY,
  onMunicipalityChange,
  onNavigate,
  selectedMunicipalityId,
  selectedMunicipio,
}) {
  const [expandedGoalIds, setExpandedGoalIds] = useState(() => new Set())
  const [showUntrackedGoals, setShowUntrackedGoals] = useState(false)
  const [themeFilter, setThemeFilter] = useState(ALL_THEMES_FILTER)
  const [searchQuery, setSearchQuery] = useState('')
  const municipalDiagnosticState = useMunicipioDiagnostic(
    municipioData?.id_municipio,
  )
  const diagnostic = municipalDiagnosticState.data?.pne2026PublicDiagnostic ?? null
  const diagnosticResultByRelation = useMemo(
    () => indexPne2026DiagnosticResults(diagnostic),
    [diagnostic],
  )

  const cycleCategories = indicadores?.cycles?.[PNE_2026_CYCLE]?.categories ?? EMPTY_ARRAY
  const cycleItems = useMemo(
    () => {
      const catalogItems = cycleCategories.flatMap((category) =>
        (category.items ?? []).map((item) => ({
          ...item,
          categoryKey: category.key,
          categoryLabel: category.label,
        })),
      )
      const catalogByKey = new Map(catalogItems.map((item) => [item.key, item]))
      return getPne2026CanonicalCycleItems().map((item) => ({
        ...catalogByKey.get(item.key),
        ...item,
      }))
    },
    [cycleCategories],
  )
  const itemByKey = useMemo(
    () => new Map(cycleItems.map((item) => [item.key, item])),
    [cycleItems],
  )

  const municipioResults = municipioData?.[PNE_2026_CYCLE]?.indicadores ?? null
  const combinedMunicipioResults = useMemo(
    () => mergePne2026DiagnosticResults(municipioResults, diagnostic),
    [diagnostic, municipioResults],
  )
  const normalizedResults = useMemo(
    () => normalizePopulationPercentResults(combinedMunicipioResults, cycleItems, PNE_2026_CYCLE),
    [combinedMunicipioResults, cycleItems],
  )

  const summary = useMemo(
    () => buildPneLegalGoalsSummary(PNE_2026_LEGAL_GOAL_INDICATOR_MAP),
    [],
  )

  const themeOptions = useMemo(
    () => {
      const categoriesByKey = new Map()
      cycleItems.forEach((item) => {
        if (!categoriesByKey.has(item.categoryKey)) {
          categoriesByKey.set(item.categoryKey, {
            label: item.categoryLabel,
            order: item.categoryOrder ?? Number.MAX_SAFE_INTEGER,
            value: item.categoryKey,
          })
        }
      })
      return [
        { label: 'Todos os temas', value: ALL_THEMES_FILTER },
        ...[...categoriesByKey.values()]
          .toSorted((left, right) => (
            left.order - right.order || left.label.localeCompare(right.label, 'pt-BR')
          ))
          .map(({ label, value }) => ({ label, value })),
      ]
    },
    [cycleItems],
  )

  const filteredGoals = useMemo(() => {
    const query = normalizeText(searchQuery.trim())

    return PNE_2026_LEGAL_GOAL_INDICATOR_MAP.filter((goal) => {
      if (!matchesThemeFilter(goal, themeFilter, itemByKey)) {
        return false
      }

      if (!query) return true

      const goalThemes = getGoalThemeLabels(goal, itemByKey)
      const indicatorTexts = goal.relatedIndicators.flatMap((indicatorRelation) => {
        const item = itemByKey.get(indicatorRelation.indicatorId)
        return [
          indicatorRelation.indicatorId,
          indicatorRelation.coverage,
          indicatorRelation.relationNote,
          item?.label,
          item?.desc,
          item?.categoryLabel,
        ]
      })

      const searchableText = [
        goal.legalGoalId,
        `Meta ${goal.legalGoalId}`,
        goal.objectiveId,
        `Objetivo ${goal.objectiveId}`,
        goal.legalText,
        ...goalThemes,
        ...indicatorTexts,
      ].join(' ')

      return normalizeText(searchableText).includes(query)
    })
  }, [itemByKey, searchQuery, themeFilter])

  const trackedGoals = useMemo(
    () => filteredGoals.filter(
      (goal) => getPneLegalGoalCategory(goal) !== PNE_LEGAL_GOAL_CATEGORIES.WITHOUT_INDICATOR,
    ),
    [filteredGoals],
  )
  const untrackedGoals = useMemo(
    () => filteredGoals.filter(
      (goal) => getPneLegalGoalCategory(goal) === PNE_LEGAL_GOAL_CATEGORIES.WITHOUT_INDICATOR,
    ),
    [filteredGoals],
  )
  const trackedGoalGroups = useMemo(
    () => groupGoalsByTheme(trackedGoals, itemByKey),
    [itemByKey, trackedGoals],
  )
  const hasActiveFilters = themeFilter !== ALL_THEMES_FILTER || Boolean(searchQuery.trim())

  function toggleGoal(goalId) {
    setExpandedGoalIds((current) => {
      const next = new Set(current)

      if (next.has(goalId)) {
        next.delete(goalId)
      } else {
        next.add(goalId)
      }

      return next
    })
  }

  return (
    <div className="page-stack legal-goals-page">
      <PnePageHeader
        asideLabel="Base legal"
        asideContent={(
          <>
            <span className="pne-page-header__aside-title">Base legal</span>
            <strong className="pne-page-header__aside-highlight">{PNE_2026_LEGAL_GOAL_MAPPING_METADATA.law}</strong>
            <p className="pne-page-header__aside-description">
              {PNE_2026_LEGAL_GOAL_MAPPING_METADATA.totalLegalGoals} metas legais
              do ciclo vigente, com acompanhamento municipal quando há indicador
              comparável disponível no painel.
            </p>
          </>
        )}
        description="Consulte as metas legais do ciclo vigente e veja como elas se conectam aos indicadores municipais disponíveis no painel."
        eyebrow="PLANO NACIONAL DE EDUCAÇÃO · CICLO VIGENTE"
        title={<>Metas legais do PNE 2026–2036{selectedMunicipio ? <span className="pne-page-header__print-context"> · {selectedMunicipio}</span> : null}</>}
        variant="listing"
      />

      <section className="legal-goals-summary-grid" aria-label="Resumo da cobertura da matriz">
        <SummaryCard
          detail="na matriz legal"
          label="Total de metas legais"
          value={summary.total}
        />
        <SummaryCard
          breakdown={[
            { label: 'Direto', tone: PNE_LEGAL_GOAL_CATEGORIES.DIRECT, value: summary.direct },
            { label: 'Parcial', tone: PNE_LEGAL_GOAL_CATEGORIES.PARTIAL, value: summary.partial },
            { label: 'Complementar', tone: PNE_LEGAL_GOAL_CATEGORIES.COMPLEMENTARY, value: summary.complementary },
          ]}
          detail="classificações metodológicas com relação pública"
          label="Categorias com relação pública"
        />
        <SummaryCard
          detail="sem relação pública utilizável"
          label="Sem indicador municipal"
          tone={PNE_LEGAL_GOAL_CATEGORIES.WITHOUT_INDICATOR}
          value={summary.withoutIndicator}
        />
      </section>

      <details className="legal-goals-method-note">
        <summary>
          <span>Como ler os selos e a nota metodológica</span>
          <span className="legal-goal-chevron" aria-hidden="true" />
        </summary>
        <div className="legal-goals-method-note__body">
          <p>
            A classificação descreve a aderência metodológica entre meta e
            indicador; não avalia o desempenho municipal nem representa
            previsão de cumprimento em 2036. As quatro categorias são
            mutuamente exclusivas e totalizam as 73 metas legais.
          </p>
          <CoverageLegend />
        </div>
      </details>

      {!selectedMunicipalityId ? (
        <section className="page-card legal-goals-empty-municipio">
          <h2>Selecione um município para acompanhar os indicadores relacionados</h2>
          <p>
            A matriz legal já está disponível, mas resultados atuais, distâncias
            e situações observadas dependem da escolha de um município.
          </p>
          {onMunicipalityChange ? (
            <div className="legal-goals-empty-municipio__selector">
              <MunicipalitySelector
                municipalities={municipalities}
                onChange={onMunicipalityChange}
                selectedMunicipalityId={selectedMunicipalityId ?? null}
                variant="hero"
              />
            </div>
          ) : null}
        </section>
      ) : (
        <>
          <section className="legal-goals-filter-panel platform-filter-panel">
            <div className="legal-goals-filter-panel__heading platform-exploration-toolbar">
              <h2>Metas e acompanhamento municipal</h2>
              <SearchField
                ariaLabel="Buscar metas legais"
                className="legal-goals-search platform-search-field"
                onChange={(event) => setSearchQuery(event.target.value)}
                onClear={() => setSearchQuery('')}
                placeholder="Buscar por código, texto legal ou indicador..."
                value={searchQuery}
              />
              {hasActiveFilters ? (
                <button
                  className="legal-goals-clear-filters platform-navigation-button"
                  onClick={() => {
                    setThemeFilter(ALL_THEMES_FILTER)
                    setSearchQuery('')
                  }}
                  type="button"
                >
                  Limpar filtros
                </button>
              ) : null}
            </div>

            <div className="legal-goals-theme-filter platform-filter-group">
              <span>Filtrar por tema</span>
              <div className="legal-goals-theme-filter__chips platform-filter-list" aria-label="Temas das metas">
                {themeOptions.map((theme) => (
                  <button
                    aria-pressed={themeFilter === theme.value}
                    className={`platform-filter-option${themeFilter === theme.value ? ' is-active' : ''}`}
                    key={theme.value}
                    onClick={() => setThemeFilter(theme.value)}
                    type="button"
                  >
                    {theme.label}
                  </button>
                ))}
              </div>
            </div>
          </section>

          <div className="legal-goals-results-meta platform-results-summary">
            <span>{trackedGoals.length} metas com informação municipal</span>
            <p>
              {getSelectedThemeLabel(themeOptions, themeFilter)} · Lei nº 15.388/2026
            </p>
          </div>

          {trackedGoals.length === 0 ? (
            <section className="page-card legal-goals-no-results">
              <p>Nenhuma meta com acompanhamento municipal comparável encontrada para os filtros selecionados.</p>
            </section>
          ) : (
            <section className="legal-goals-accordion" aria-label="Metas legais do PNE 2026-2036">
              {trackedGoalGroups.map((group) => (
                <details className="legal-goals-theme-group" key={group.label} open>
                  <summary>
                    <span>{group.label}</span>
                    <small>{group.goals.length} metas com acompanhamento</small>
                  </summary>
                  <div className="legal-goals-theme-group__items">
                    {group.goals.map((goal) => (
                      <LegalGoalAccordionItem
                        goal={goal}
                        isExpanded={expandedGoalIds.has(goal.legalGoalId)}
                        itemByKey={itemByKey}
                        key={goal.legalGoalId}
                        normalizedResults={normalizedResults}
                        diagnosticResultByRelation={diagnosticResultByRelation}
                        onNavigate={onNavigate}
                        onToggle={() => toggleGoal(goal.legalGoalId)}
                      />
                    ))}
                  </div>
                </details>
              ))}
            </section>
          )}

          <UntrackedLegalGoals
            goals={untrackedGoals}
            isOpen={showUntrackedGoals}
            onToggle={() => setShowUntrackedGoals((current) => !current)}
          />
        </>
      )}
    </div>
  )
}

function SummaryCard({ breakdown = [], detail, label, tone, value }) {
  return (
    <article
      className={`legal-goals-summary-card${tone ? ` legal-goals-summary-card--${tone}` : ''}`}
    >
      <span>{label}</span>
      {value !== undefined ? <strong>{value}</strong> : null}
      {breakdown.length ? (
        <dl className="legal-goals-summary-card__breakdown">
          {breakdown.map((item) => (
            <div className={`legal-goals-summary-card__breakdown-item legal-goals-summary-card__breakdown-item--${item.tone}`} key={item.label}>
              <dt>{item.label}</dt>
              <dd>{item.value}</dd>
            </div>
          ))}
        </dl>
      ) : null}
      <small>{detail}</small>
    </article>
  )
}

function CoverageLegend() {
  const legendItems = [
    {
      coverage: PNE_LEGAL_GOAL_CATEGORIES.DIRECT,
      description: 'o indicador acompanha de forma próxima a meta legal.',
      label: 'Acompanhamento direto',
    },
    {
      coverage: PNE_LEGAL_GOAL_CATEGORIES.PARTIAL,
      description: 'o indicador mede uma parte relevante da meta, mas não representa sozinho todo o texto legal.',
      label: 'Acompanhamento parcial',
    },
    {
      coverage: PNE_LEGAL_GOAL_CATEGORIES.COMPLEMENTARY,
      description: 'há informação municipal útil, sem comparação com referência.',
      label: 'Informação complementar',
    },
    {
      coverage: PNE_LEGAL_GOAL_CATEGORIES.WITHOUT_INDICATOR,
      description: 'não há relação pública municipal utilizável no contrato atual.',
      label: 'Sem indicador municipal',
    },
  ]

  return (
    <div className="legal-goals-legend" aria-label="Como ler os selos">
      <strong>Como ler os selos</strong>
      <div>
        {legendItems.map((item) => (
          <p key={item.coverage}>
            <CoverageBadge coverage={item.coverage} label={item.label} />
            <span>{item.description}</span>
          </p>
        ))}
      </div>
    </div>
  )
}

function LegalGoalAccordionItem({
  diagnosticResultByRelation,
  goal,
  isExpanded,
  itemByKey,
  normalizedResults,
  onNavigate,
  onToggle,
}) {
  const contentId = `legal-goal-panel-${goal.legalGoalId.replace('.', '-')}`
  const goalCoverage = getPneLegalGoalCategory(goal)
  const visibleRelations = getVisibleGoalRelations(goal)
  const goalThemeLabel = getGoalThemeSummary(goal, itemByKey)
  const referenceType = visibleRelations.some((relation) => relation.monitoringMode === PNE_2026_RELATIONSHIP_MODES.TRACKING)
    ? 'Acompanhamento'
    : 'Referência legal'
  const monitoringAvailability = visibleRelations.length
    ? `${visibleRelations.length} indicador${visibleRelations.length === 1 ? '' : 'es'} disponível${visibleRelations.length === 1 ? '' : 'is'}`
    : 'Sem acompanhamento municipal'

  return (
    <article className={`legal-goal-card${isExpanded ? ' is-expanded' : ''}`}>
      <button
        aria-controls={contentId}
        aria-expanded={isExpanded}
        className="legal-goal-toggle"
        onClick={onToggle}
        type="button"
      >
        <span className="legal-goal-toggle__content">
          <span className="legal-goal-toggle__topline">
            <span className="legal-goal-code">Meta {goal.legalGoalId}</span>
            <span className="legal-goal-theme">{goalThemeLabel}</span>
          </span>
          <span className="legal-goal-short-title">{getShortGoalTitle(goal.legalText)}</span>
          <span className="legal-goal-badge-row">
            <span className="legal-goal-reference-type">{referenceType}</span>
            <span className="legal-goal-monitoring-availability">{monitoringAvailability}</span>
            <CoverageBadge coverage={goalCoverage} />
          </span>
        </span>
        <span className="legal-goal-chevron" aria-hidden="true" />
      </button>

      {isExpanded ? (
        <div className="legal-goal-card__body" id={contentId}>
          <section className="legal-goal-legal-text">
            <h3>Texto legal</h3>
            <div className="legal-goal-legal-text__meta">
              <span>Meta {goal.legalGoalId}</span>
              <span>{goalThemeLabel}</span>
            </div>
            <p className="legal-goal-full-text">{goal.legalText}</p>
          </section>
          {visibleRelations.length === 0 ? (
            <NoMunicipalIndicator reason={goal.noMunicipalIndicatorReason} />
          ) : (
            <section className="legal-goal-monitoring">
              <h3>
                {visibleRelations.length > 1
                  ? `Indicadores municipais associados — ${visibleRelations.length}`
                  : 'Como esta meta é acompanhada no município'}
              </h3>
              <div className="legal-goal-indicator-list">
              {visibleRelations.map((indicatorRelation) => (
                <LegalGoalIndicator
                  diagnosticResult={diagnosticResultByRelation.get(indicatorRelation.relationId)}
                  indicatorRelation={indicatorRelation}
                  item={itemByKey.get(indicatorRelation.indicatorId)}
                  key={`${goal.legalGoalId}-${indicatorRelation.indicatorId}`}
                  onNavigate={onNavigate}
                  result={normalizedResults?.[indicatorRelation.indicatorId]}
                />
              ))}
              </div>
            </section>
          )}
        </div>
      ) : null}
    </article>
  )
}

function CoverageBadge({ coverage, label }) {
  const displayLabel = label ?? COVERAGE_LABELS[coverage] ?? coverage

  return (
    <span className={`coverage-badge coverage-badge--${coverage}`}>
      {displayLabel}
    </span>
  )
}

function NoMunicipalIndicator({ reason }) {
  return (
    <div className="legal-goal-no-indicator">
      <span>Sem indicador municipal disponível atualmente na plataforma.</span>
      {reason ? <p>{reason}</p> : null}
    </div>
  )
}

function UntrackedLegalGoals({ goals, isOpen, onToggle }) {
  if (!goals.length) return null

  return (
    <section className="legal-goals-untracked">
      <button
        aria-expanded={isOpen}
        className="legal-goals-untracked__toggle"
        onClick={onToggle}
        type="button"
      >
        <span>
          <strong>Metas sem indicador municipal</strong>
          <em>{goals.length} metas nos filtros atuais</em>
        </span>
        <span className="legal-goal-chevron" aria-hidden="true" />
      </button>

      {isOpen ? (
        <div className="legal-goals-untracked__list">
          <p className="legal-goals-untracked__support">
            Essas metas fazem parte da lei, mas ainda não possuem indicador
            municipal adequado no painel. Em alguns casos, há dados contextuais
            em Indicadores de Educação, mas eles não representam cumprimento da
            meta legal.
          </p>
          {goals.map((goal) => (
            <article className="legal-goals-untracked__item" key={goal.legalGoalId}>
              <div className="legal-goals-untracked__heading">
                <span className="legal-goal-code">Meta {goal.legalGoalId}</span>
                <CoverageBadge coverage={PNE_LEGAL_GOAL_CATEGORIES.WITHOUT_INDICATOR} />
              </div>
              <p className="legal-goals-untracked__text">{goal.legalText}</p>
              <p className="legal-goals-untracked__reason">
                {getUntrackedReasonLabel(goal)}
              </p>
            </article>
          ))}
        </div>
      ) : null}
    </section>
  )
}

function LegalGoalIndicator({
  diagnosticResult,
  indicatorRelation,
  item,
  onNavigate,
  result: municipalResult,
}) {
  const result = reconcilePne2026MunicipalResult({
    goalId: indicatorRelation.legalGoalId,
    indicatorId: indicatorRelation.indicatorId,
    result: municipalResult,
  }).result
  const relationshipMode = indicatorRelation.monitoringMode
  const isComplementary =
    relationshipMode === PNE_2026_RELATIONSHIP_MODES.COMPLEMENTARY
  const relationPresentation = getPneLegalRelationPresentation({
    diagnosticResult,
    item,
    relation: indicatorRelation,
  })
  const dataStatus = diagnosticResult?.dataStatus
    ?? result?.dataStatus
    ?? (hasUsableMunicipalResult(indicatorRelation, result) ? 'available' : 'unavailable')
  const hasMunicipalResult = dataStatus === 'available'
  const unit = relationPresentation.indicator?.unit ?? resolveIndicatorUnit(item, result)
  const currentValue = diagnosticResult?.current?.value ?? result?.end_value
  const currentYear = diagnosticResult?.current?.year ?? result?.end_year
  const referenceValue = diagnosticResult?.indicatorReference?.value ?? result?.meta
  const distanceValue = diagnosticResult?.distance ?? result?.distance
  const direction = diagnosticResult?.direction
    ?? diagnosticResult?.indicatorReference?.direction
    ?? result?.direction
    ?? indicatorRelation.direction
  const achieved = Number.isFinite(Number(distanceValue))
    ? Number(distanceValue) >= 0
    : typeof result?.atingida === 'boolean'
      ? result.atingida
      : null
  const statusPresentation = getPneComparisonStatusPresentation({
    achieved,
    dataStatus,
    direction,
    mode: relationshipMode,
  })
  const indicatorCoverage = isComplementary
    ? PNE_LEGAL_GOAL_CATEGORIES.COMPLEMENTARY
    : indicatorRelation.coverage === 'direta'
      ? PNE_LEGAL_GOAL_CATEGORIES.DIRECT
      : PNE_LEGAL_GOAL_CATEGORIES.PARTIAL
  const sourceResult = {
    ...result,
    end_value: currentValue,
    end_year: currentYear,
  }
  const sourceContext = {
    block: 'pne',
    cycle: PNE_2026_CYCLE,
    indicatorKey: indicatorRelation.indicatorId,
    item,
    result: sourceResult,
  }

  return (
    <article className={`legal-goal-indicator legal-goal-indicator--${relationshipMode}`}>
      <header className="legal-goal-indicator__header">
        <div>
          <span className="legal-goal-indicator__eyebrow">
            Indicador municipal associado · {relationPresentation.modeLabel}
          </span>
          <h4>{relationPresentation.publicName}</h4>
        </div>
        <CoverageBadge coverage={indicatorCoverage} />
      </header>

      <div className="legal-goal-relation-meta">
        <span>Natureza da referência: <strong>{relationPresentation.referenceNatureLabel}</strong></span>
        <span>Modo público: <strong>{relationPresentation.modeLabel}</strong></span>
      </div>

      <section className="legal-goal-result">
        <h5>Resultado atual</h5>
        {!hasMunicipalResult ? (
          <p className="legal-goal-indicator__empty">
            {getPneLegalDataStatusLabel(dataStatus) ?? 'Sem resultado comparável no período'}
          </p>
        ) : (
          <div className="legal-goal-metric-grid">
            <LegalMetric
              label="Valor municipal"
              value={diagnosticResult?.current?.displayText
                ?? formatIndicatorValue(currentValue, unit)}
            />
            <LegalMetric
              label="Ano"
              value={getReadableYear(currentYear) ?? '—'}
            />
            {!isComplementary ? (
              <>
                <LegalMetric
                  label={relationPresentation.referenceNatureLabel}
                  value={formatIndicatorValue(referenceValue, unit)}
                />
                <LegalMetric
                  label="Distância"
                  tone={statusPresentation.tone}
                  value={formatDistance({
                    ...result,
                    distance: distanceValue,
                    display: { ...result?.display, distance: null },
                  }, unit)}
                />
                <LegalMetric
                  label={relationshipMode === PNE_2026_RELATIONSHIP_MODES.TRACKING
                    ? 'Situação de acompanhamento'
                    : 'Situação'}
                  tone={statusPresentation.tone}
                  value={statusPresentation.text ?? 'Situação indisponível'}
                />
              </>
            ) : null}
          </div>
        )}
      </section>

      <section className="legal-goal-interpretation">
        <h5>Como interpretar</h5>
        <div className="legal-goal-explanation-grid">
          <div className="legal-goal-explanation">
            <span>O que o indicador mede</span>
            <p>{relationPresentation.measurement}</p>
          </div>
          <div className="legal-goal-explanation">
            <span>Relação com a meta</span>
            <p>{relationPresentation.relationship}</p>
          </div>
          <div className="legal-goal-explanation legal-goal-explanation--limit">
            <span>Limite da leitura</span>
            <p>{relationPresentation.limitation}</p>
          </div>
        </div>
      </section>

      <div className="legal-goal-indicator__footer">
        <span className="legal-goal-territoriality">
          Territorialidade: <strong>{relationPresentation.territorialityLabel}</strong>
        </span>
        <PneSourceNotes compact context={sourceContext} />
        {onNavigate ? (
          <button
            className="legal-goal-open-cycle"
            onClick={() => onNavigate('pne2026')}
            type="button"
          >
            Abrir página do ciclo vigente 2026-2036
          </button>
        ) : null}
      </div>
    </article>
  )
}

function LegalMetric({ detail, label, tone = 'default', value }) {
  return (
    <div className={`legal-goal-metric legal-goal-metric--${tone}`}>
      <span>{label}</span>
      <strong>{value ?? '—'}</strong>
      {detail ? <small>{detail}</small> : null}
    </div>
  )
}

function matchesThemeFilter(goal, themeFilter, itemByKey) {
  if (themeFilter === ALL_THEMES_FILTER) return true

  return (goal.relatedIndicators ?? []).some((indicatorRelation) => (
    itemByKey.get(indicatorRelation.indicatorId)?.categoryKey === themeFilter
  ))
}

function getGoalThemeLabels(goal, itemByKey) {
  const labels = []
  const seenLabels = new Set()
  const relatedIndicators = goal.relatedIndicators ?? []

  relatedIndicators.forEach((indicatorRelation) => {
    const label = itemByKey.get(indicatorRelation.indicatorId)?.categoryLabel
    if (!label || seenLabels.has(label)) return

    seenLabels.add(label)
    labels.push(label)
  })

  return labels
}

function getGoalThemeSummary(goal, itemByKey) {
  const labels = getGoalThemeLabels(goal, itemByKey)

  if (!labels.length) return UNMAPPED_THEME_LABEL
  if (labels.length === 1) return labels[0]

  const extraCount = labels.length - 1
  return `${labels[0]} + ${extraCount} tema${extraCount > 1 ? 's' : ''}`
}

function getSelectedThemeLabel(themeOptions, themeFilter) {
  return (
    themeOptions.find((theme) => theme.value === themeFilter)?.label ??
    'Todos os temas'
  )
}

function groupGoalsByTheme(goals, itemByKey) {
  const groups = new Map()
  goals.forEach((goal) => {
    const label = getGoalThemeSummary(goal, itemByKey)
    const group = groups.get(label) ?? { label, goals: [] }
    group.goals.push(goal)
    groups.set(label, group)
  })
  return [...groups.values()].sort((left, right) => left.label.localeCompare(right.label, 'pt-BR'))
}

function getShortGoalTitle(legalText) {
  const normalized = String(legalText ?? '').replace(/\s+/g, ' ').trim()
  const sentenceEnd = normalized.search(/[.;](?:\s|$)/)
  return sentenceEnd > 0 ? normalized.slice(0, sentenceEnd + 1) : normalized
}

function getUntrackedReasonLabel(goal) {
  const normalizedReason = normalizeText(goal.noMunicipalIndicatorReason)
  if (
    normalizedReason.includes('administrativa') ||
    normalizedReason.includes('local')
  ) {
    return 'Depende de base administrativa/local'
  }

  return 'Sem fonte municipal anual adequada'
}

function getVisibleGoalRelations(goal) {
  return getPne2026PublicLegalGoalRelations(goal.legalGoalId)
}

function hasUsableMunicipalResult(indicatorRelation, result) {
  if (!indicatorRelation.hasMunicipalResult || !result || result.available === false) {
    return false
  }

  const endValue = Number(result.end_value)
  if (Number.isFinite(endValue)) return true

  return (result.series ?? []).some((point) => Number.isFinite(Number(point?.valor)))
}

function formatDistance(result, unit) {
  const numericDistance = Number(result?.distance)
  if (!Number.isFinite(numericDistance)) return '—'

  const sign = numericDistance > 0 ? '+' : ''
  const formatted = `${sign}${PERCENT_FORMATTER.format(numericDistance)}`
  if (unit === 'percent') return `${formatted} p.p.`
  if (unit === 'years') return `${formatted} anos`
  if (unit === 'index') return `${formatted} pontos`
  return formatted
}

function getReadableYear(value) {
  const numeric = Number(value)
  return Number.isFinite(numeric) && numeric > 0 ? numeric : null
}

function normalizeText(value) {
  return String(value ?? '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLocaleLowerCase('pt-BR')
}
