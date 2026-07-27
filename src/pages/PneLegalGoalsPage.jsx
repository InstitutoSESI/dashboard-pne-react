import { useMemo, useState } from 'react'
import { PneSourceNotes } from '../components/PneSourceNotes'
import { MunicipalitySelector } from '../components/MunicipalitySelector'
import { PnePageHeader } from '../components/PnePageHeader'
import { SearchField } from '../components/SearchField'
import {
  PNE_2026_LEGAL_GOAL_INDICATOR_MAP,
  PNE_2026_LEGAL_GOAL_MAPPING_METADATA,
} from '../data/pne2026LegalGoalIndicatorMap'
import {
  formatIndicatorValue,
  formatMetaValue,
  getIndicatorTitle,
  resolveIndicatorUnit,
  roundPpString,
} from '../utils/format'
import { normalizePopulationPercentResults } from '../utils/indicatorValues'
import { getPneCycleCopy } from '../utils/pneCycleCopy'
import { isPne2026AccumulativeIndicator } from '../utils/pneAccumulativeCycle'
import {
  isPneComparableIndicator,
  isPneContextProxyRelation,
} from '../utils/pneDisplayRules'

const PNE_2026_CYCLE = 'pne_2026_2036'
const PNE_2026_COPY = getPneCycleCopy(PNE_2026_CYCLE)
const EMPTY_ARRAY = []

const METHODOLOGY_WARNINGS_BY_KEY = {
  salas_climatizadas:
    'Proxy parcial de conforto térmico; não mede todo o padrão físico do estabelecimento.',
  salas_acessiveis:
    'Proxy parcial de acessibilidade; não mede toda a acessibilidade escolar.',
}

const COVERAGE_LABELS = {
  contexto: 'Indicador de contexto',
  direta: 'Acompanhamento direto',
  parcial: 'Cobertura parcial',
  proxy: 'Proxy metodológico',
  sem_comparavel: 'Sem acompanhamento municipal comparável',
  sem_indicador: 'Sem indicador municipal',
}

const ALL_THEMES_FILTER = 'todos'
const UNMAPPED_THEME_LABEL = 'Tema sem indicador associado'

const PERCENT_FORMATTER = new Intl.NumberFormat('pt-BR', {
  maximumFractionDigits: 1,
  minimumFractionDigits: 0,
})

export function PneLegalGoalsPage({
  indicadores,
  municipioData,
  municipios = EMPTY_ARRAY,
  onMunicipioChange,
  onNavigate,
  selectedMunicipio,
}) {
  const [expandedGoalIds, setExpandedGoalIds] = useState(() => new Set())
  const [showUntrackedGoals, setShowUntrackedGoals] = useState(false)
  const [themeFilter, setThemeFilter] = useState(ALL_THEMES_FILTER)
  const [searchQuery, setSearchQuery] = useState('')

  const cycleCategories = indicadores?.cycles?.[PNE_2026_CYCLE]?.categories ?? EMPTY_ARRAY
  const cycleItems = useMemo(
    () => cycleCategories.flatMap((category) =>
      (category.items ?? []).map((item) => ({
        ...item,
        categoryKey: category.key,
        categoryLabel: category.label,
      })),
    ),
    [cycleCategories],
  )
  const itemByKey = useMemo(
    () => new Map(cycleItems.map((item) => [item.key, item])),
    [cycleItems],
  )

  const municipioResults = municipioData?.[PNE_2026_CYCLE]?.indicadores ?? null
  const normalizedResults = useMemo(
    () => normalizePopulationPercentResults(municipioResults, cycleItems),
    [cycleItems, municipioResults],
  )
  const projections = municipioData?.[PNE_2026_CYCLE]?.projecoes ?? {}

  const summary = useMemo(
    () => buildCoverageSummary(PNE_2026_LEGAL_GOAL_INDICATOR_MAP, normalizedResults),
    [normalizedResults],
  )

  const themeOptions = useMemo(
    () => [
      { label: 'Todos os temas', value: ALL_THEMES_FILTER },
      ...cycleCategories.map((category) => ({
        label: category.label,
        value: category.key,
      })),
    ],
    [cycleCategories],
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
    () => filteredGoals.filter((goal) => classifyGoalCoverage(goal, normalizedResults) !== 'sem_comparavel'),
    [filteredGoals, normalizedResults],
  )
  const untrackedGoals = useMemo(
    () => filteredGoals.filter((goal) => classifyGoalCoverage(goal, normalizedResults) === 'sem_comparavel'),
    [filteredGoals, normalizedResults],
  )

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
        context={selectedMunicipio ? <>Município em foco: <strong>{selectedMunicipio}</strong></> : null}
        description="Consulte as metas legais do ciclo vigente e veja como elas se conectam aos indicadores municipais disponíveis no painel."
        eyebrow="PLANO NACIONAL DE EDUCAÇÃO · CICLO VIGENTE"
        title="Metas legais do PNE 2026–2036"
        variant="listing"
      />

      <section className="legal-goals-summary-grid" aria-label="Resumo da cobertura da matriz">
        <SummaryCard
          detail="na matriz legal"
          label="Total de metas legais"
          value={summary.total}
        />
        <SummaryCard
          detail="metas únicas com ao menos um indicador comparável"
          label="Metas legais acompanhadas"
          value={summary.tracked}
        />
        <SummaryCard
          detail="melhor cobertura disponível para a meta"
          label="Acompanhamento direto"
          value={summary.direct}
        />
        <SummaryCard
          detail="com indicador comparável, mas não integral"
          label="Cobertura parcial"
          value={summary.partial}
        />
        <SummaryCard
          detail="sem distância/status interpretável"
          label="Sem acompanhamento comparável"
          value={summary.withoutComparableTracking}
        />
      </section>

      <section className="legal-goals-method-note" role="note">
        <div>
          <span>Aviso metodológico</span>
          <p>
            Indicadores de contexto não representam cumprimento da meta legal e
            não exibem distância da meta. Uma meta legal pode ter mais de um
            indicador associado; por isso o total de indicadores pode ser maior
            que o total de metas acompanhadas.
          </p>
        </div>
        <CoverageLegend />
      </section>

      {!selectedMunicipio ? (
        <section className="page-card legal-goals-empty-municipio">
          <h2>Selecione um município para acompanhar os indicadores relacionados</h2>
          <p>
            A matriz legal já está disponível, mas resultados atuais, distâncias
            e projeções dependem da escolha de um município.
          </p>
          {onMunicipioChange ? (
            <div className="legal-goals-empty-municipio__selector">
              <MunicipalitySelector
                municipios={municipios}
                onChange={onMunicipioChange}
                selectedMunicipio=""
                variant="hero"
              />
            </div>
          ) : null}
        </section>
      ) : (
        <>
          <section className="legal-goals-filter-panel platform-filter-panel">
            <div className="legal-goals-filter-panel__heading platform-exploration-toolbar">
              <div>
                <span className="eyebrow">Ciclo vigente · acompanhamento atual</span>
                <h2>Metas do ciclo vigente e acompanhamento municipal</h2>
                <p>
                  A lista mostra a situação observada até o ano mais recente disponível,
                  sem representar uma previsão de cumprimento em 2036.
                  Use os temas para navegar por área e a busca para localizar
                  código, texto legal ou indicador.
                </p>
              </div>
              <SearchField
                ariaLabel="Buscar metas legais"
                className="legal-goals-search platform-search-field"
                onChange={(event) => setSearchQuery(event.target.value)}
                onClear={() => setSearchQuery('')}
                placeholder="Buscar por código, texto legal ou indicador..."
                value={searchQuery}
              />
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
            <span>{trackedGoals.length} metas acompanhadas exibidas</span>
            <p>
              {getSelectedThemeLabel(themeOptions, themeFilter)} · {selectedMunicipio} ·
              Lei nº 15.388/2026
            </p>
          </div>

          {trackedGoals.length === 0 ? (
            <section className="page-card legal-goals-no-results">
              <p>Nenhuma meta com acompanhamento municipal comparável encontrada para os filtros selecionados.</p>
            </section>
          ) : (
            <section className="legal-goals-accordion" aria-label="Metas legais do PNE 2026-2036">
              {trackedGoals.map((goal) => (
                <LegalGoalAccordionItem
                  goal={goal}
                  isExpanded={expandedGoalIds.has(goal.legalGoalId)}
                  itemByKey={itemByKey}
                  key={goal.legalGoalId}
                  normalizedResults={normalizedResults}
                  onNavigate={onNavigate}
                  onToggle={() => toggleGoal(goal.legalGoalId)}
                  projections={projections}
                />
              ))}
            </section>
          )}

          <UntrackedLegalGoals
            goals={untrackedGoals}
            isOpen={showUntrackedGoals}
            itemByKey={itemByKey}
            normalizedResults={normalizedResults}
            onToggle={() => setShowUntrackedGoals((current) => !current)}
          />
        </>
      )}
    </div>
  )
}

function SummaryCard({ detail, label, value }) {
  return (
    <article className="legal-goals-summary-card">
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{detail}</small>
    </article>
  )
}

function CoverageLegend() {
  const legendItems = [
    {
      coverage: 'direta',
      description: 'o indicador acompanha de forma próxima a meta legal.',
      label: 'Acompanhamento direto',
    },
    {
      coverage: 'parcial',
      description: 'o indicador mede uma parte relevante da meta, mas não representa sozinho todo o texto legal.',
      label: 'Cobertura parcial',
    },
    {
      coverage: 'sem_comparavel',
      description: 'ainda não há fonte municipal adequada para acompanhar a meta no painel.',
      label: 'Sem acompanhamento municipal comparável',
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
  goal,
  isExpanded,
  itemByKey,
  normalizedResults,
  onNavigate,
  onToggle,
  projections,
}) {
  const contentId = `legal-goal-panel-${goal.legalGoalId.replace('.', '-')}`
  const goalCoverage = classifyGoalCoverage(goal, normalizedResults)
  const comparableRelations = getComparableGoalRelations(goal, normalizedResults)
  const goalThemeLabel = getGoalThemeSummary(goal, itemByKey)

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
          <span className="legal-goal-text">{goal.legalText}</span>
          <span className="legal-goal-badge-row">
            <CoverageBadge coverage={goalCoverage} />
          </span>
        </span>
        <span className="legal-goal-chevron" aria-hidden="true" />
      </button>

      {isExpanded ? (
        <div className="legal-goal-card__body" id={contentId}>
          <p className="legal-goal-full-text">{goal.legalText}</p>
          {comparableRelations.length === 0 ? (
            <NoMunicipalIndicator reason={goal.noMunicipalIndicatorReason} />
          ) : (
            <div className="legal-goal-indicator-list">
              {comparableRelations.map((indicatorRelation) => (
                <LegalGoalIndicator
                  indicatorRelation={indicatorRelation}
                  item={itemByKey.get(indicatorRelation.indicatorId)}
                  key={`${goal.legalGoalId}-${indicatorRelation.indicatorId}`}
                  onNavigate={onNavigate}
                  projection={projections?.[indicatorRelation.indicatorId]}
                  result={normalizedResults?.[indicatorRelation.indicatorId]}
                />
              ))}
            </div>
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

function UntrackedLegalGoals({ goals, isOpen, itemByKey, normalizedResults, onToggle }) {
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
          <strong>Metas sem acompanhamento municipal comparável</strong>
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
                <CoverageBadge coverage="sem_comparavel" />
              </div>
              <p className="legal-goals-untracked__text">{goal.legalText}</p>
              <p className="legal-goals-untracked__reason">
                {getUntrackedReasonLabel(goal, normalizedResults)}
              </p>
              {goal.relatedIndicators.length ? (
                <p className="legal-goals-untracked__related">
                  Dados relacionados:{' '}
                  {goal.relatedIndicators
                    .map((indicatorRelation) => itemByKey.get(indicatorRelation.indicatorId)?.label ?? indicatorRelation.indicatorId)
                    .join(', ')}
                </p>
              ) : null}
            </article>
          ))}
        </div>
      ) : null}
    </section>
  )
}

function LegalGoalIndicator({ indicatorRelation, item, onNavigate, projection, result }) {
  const hasCatalogItem = Boolean(item)
  const hasMunicipalResult = hasUsableMunicipalResult(indicatorRelation, result)
  const isAccumulativeBaseline = (
    isPne2026AccumulativeIndicator(PNE_2026_CYCLE, indicatorRelation.indicatorId) &&
    Number(result?.end_year) <= 2025
  )
  const unit = resolveIndicatorUnit(item, result)
  const comparable = !isAccumulativeBaseline && hasMunicipalResult && isComparableLegalIndicator(indicatorRelation, result)
  const showDistance = comparable && hasComparableDistance(indicatorRelation, result)
  const showProjection = comparable && hasProjection2036(indicatorRelation, projection)
  const showStatus = comparable && hasReadableStatus(result)
  const indicatorCoverage = getIndicatorCoverage(indicatorRelation, result)
  const relationType = getRelationTypeLabel(indicatorRelation, result)
  const methodologyWarning = getMethodologyWarning(indicatorRelation, result)
  const indicatorTitle = hasCatalogItem
    ? getIndicatorTitle(item, result)
    : indicatorRelation.indicatorId
  const relationCopy = buildRelationCopy(indicatorRelation, methodologyWarning)
  const sourceContext = {
    block: 'pne',
    cycle: PNE_2026_CYCLE,
    indicatorKey: indicatorRelation.indicatorId,
    item,
    result,
  }

  return (
    <article className="legal-goal-indicator">
      <header className="legal-goal-indicator__header">
        <div>
          <span className="legal-goal-indicator__eyebrow">
            Indicador usado no painel · {item?.categoryLabel ?? 'Indicador relacionado'} · {indicatorRelation.indicatorId}
          </span>
          <h3>{indicatorTitle}</h3>
          {item?.desc ? (
            <p>{isAccumulativeBaseline ? getAccumulativeLegalDescription(indicatorRelation.indicatorId) : item.desc}</p>
          ) : null}
        </div>
        <CoverageBadge coverage={indicatorCoverage} />
      </header>

      <div className="legal-goal-relation-meta">
        <span>Leitura no painel: <strong>{relationType}</strong></span>
        {isPneContextProxyRelation(indicatorRelation, result) ? (
          <span>Sem distância, status de meta ou projeção.</span>
        ) : null}
      </div>

      <div className="legal-goal-explanation-grid">
        <div className="legal-goal-explanation">
          <span>Indicador usado no painel</span>
          <p>{indicatorTitle}</p>
        </div>
        <div className="legal-goal-explanation">
          <span>Por que este indicador foi associado</span>
          <p>{relationCopy.rationale}</p>
        </div>
        {relationCopy.limit ? (
          <div className="legal-goal-explanation legal-goal-explanation--limit">
            <span>Limite da leitura</span>
            <p>{relationCopy.limit}</p>
          </div>
        ) : null}
      </div>

      {!hasCatalogItem ? (
        <div className="legal-goal-indicator__empty">
          Indicador mapeado não encontrado no catálogo atual do ciclo PNE 2026-2036.
        </div>
      ) : !hasMunicipalResult ? (
        <div className="legal-goal-indicator__empty">
          Sem leitura municipal disponível para este indicador no ciclo vigente.
        </div>
      ) : isAccumulativeBaseline ? (
        <div className="legal-goal-metric-grid">
          <LegalMetric label="Situação no ciclo" tone="muted" value="Linha de base definida" />
          <LegalMetric label="Ano de referência" value="2025" />
          <LegalMetric
            label="Meta de referência"
            value={indicatorRelation.indicatorId === 'medio_tecnico_participacao_publica' ? '50%' : '+60%'}
          />
          <LegalMetric label="Resultado do ciclo" tone="muted" value="Disponível a partir de 2026" />
        </div>
      ) : (
        <div className="legal-goal-metric-grid">
          <LegalMetric
            label="Valor mais recente"
            value={formatCurrentValue(result, unit)}
          />
          <LegalMetric
            label="Ano de referência"
            value={getReadableYear(result?.end_year) ?? '—'}
          />
          {comparable ? (
            <LegalMetric
              detail={result.meta_label ?? 'Meta de referência do indicador'}
              label="Meta de referência"
              value={formatMetaValue(result, unit)}
            />
          ) : null}
          {showDistance ? (
            <LegalMetric
              label="Distância da meta"
              tone={result.atingida ? 'success' : 'warning'}
              value={formatDistance(result, unit)}
            />
          ) : null}
          {showStatus ? (
            <LegalMetric
              label="Situação no momento"
              tone={result.atingida ? 'success' : 'warning'}
              value={result.atingida ? PNE_2026_COPY.status.achieved : PNE_2026_COPY.status.below}
            />
          ) : null}
          {showProjection ? (
            <LegalMetric
              detail={formatProjectionDistance(projection.distance_to_target_2036)}
              label="Projeção para 2036"
              tone={projection.status_2036 === 'tende_a_atingir' ? 'success' : 'warning'}
              value={formatProjectionPercent(projection.projected_2036)}
            />
          ) : null}
        </div>
      )}

      <div className="legal-goal-indicator__footer">
        <PneSourceNotes context={sourceContext} />
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

function getAccumulativeLegalDescription(indicatorId) {
  if (indicatorId === 'medio_tecnico_participacao_publica') {
    return 'Pelo menos 50% das novas matrículas de EPT de nível médio criadas no ciclo deverão ser públicas. O acompanhamento começa na linha de base de 2025.'
  }
  return 'A expansão de 60% das matrículas em cursos técnicos subsequentes será acompanhada a partir da linha de base de 2025.'
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

function buildCoverageSummary(goals, results) {
  return goals.reduce(
    (summary, goal) => {
      const coverage = classifyGoalCoverage(goal, results, { allowMatrixFallback: true })

      summary.total += 1

      if (coverage === 'direta') {
        summary.direct += 1
        summary.tracked += 1
      } else if (coverage === 'parcial') {
        summary.partial += 1
        summary.tracked += 1
      } else if (coverage === 'sem_comparavel') {
        summary.withoutComparableTracking += 1
      }

      return summary
    },
    {
      direct: 0,
      partial: 0,
      tracked: 0,
      total: 0,
      withoutComparableTracking: 0,
    },
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

function getUntrackedReasonLabel(goal, results) {
  if (hasContextualRelatedData(goal, results)) {
    return 'Possui apenas dado contextual'
  }

  const normalizedReason = normalizeText(goal.noMunicipalIndicatorReason)
  if (
    normalizedReason.includes('administrativa') ||
    normalizedReason.includes('local')
  ) {
    return 'Depende de base administrativa/local'
  }

  return 'Sem fonte municipal anual adequada'
}

function buildRelationCopy(indicatorRelation, methodologyWarning) {
  const relationNote = String(indicatorRelation?.relationNote ?? '').trim()
  const noteParts = relationNote.split(';').map((part) => part.trim()).filter(Boolean)
  const rationale = noteParts[0] || relationNote || 'Nota metodológica não disponível na matriz.'
  const limitParts = noteParts.slice(1)

  if (
    methodologyWarning &&
    !limitParts.some((part) => normalizeText(part) === normalizeText(methodologyWarning))
  ) {
    limitParts.push(methodologyWarning)
  }

  return {
    limit: indicatorRelation?.coverage === 'direta'
      ? ''
      : limitParts.join(' ') || relationNote || methodologyWarning,
    rationale,
  }
}

function classifyGoalCoverage(goal, results, { allowMatrixFallback = false } = {}) {
  const comparableRelations = getComparableGoalRelations(goal, results, { allowMatrixFallback })

  if (!comparableRelations.length) return 'sem_comparavel'
  if (comparableRelations.some((indicatorRelation) => indicatorRelation.coverage === 'direta')) {
    return 'direta'
  }
  return 'parcial'
}

function getComparableGoalRelations(goal, results, { allowMatrixFallback = false } = {}) {
  return (goal.relatedIndicators ?? []).filter((indicatorRelation) => (
    isComparableGoalRelation(indicatorRelation, results, { allowMatrixFallback })
  ))
}

function isComparableGoalRelation(indicatorRelation, results, { allowMatrixFallback = false } = {}) {
  const result = results?.[indicatorRelation.indicatorId]

  if (!result && allowMatrixFallback) {
    return (
      indicatorRelation.hasDistance !== false &&
      !isPneContextProxyRelation(indicatorRelation)
    )
  }

  return isPneComparableIndicator({
    indicatorKey: indicatorRelation.indicatorId,
    indicatorRelation,
    result,
  })
}

function hasContextualRelatedData(goal, results) {
  return (goal.relatedIndicators ?? []).some((indicatorRelation) => (
    isPneContextProxyRelation(indicatorRelation, results?.[indicatorRelation.indicatorId])
  ))
}

function getIndicatorCoverage(indicatorRelation, result) {
  if (!isPneContextProxyRelation(indicatorRelation, result)) {
    return indicatorRelation.coverage === 'direta' ? 'direta' : 'parcial'
  }

  return isProxyMethodologicalRelation(indicatorRelation) ? 'proxy' : 'contexto'
}

function getRelationTypeLabel(indicatorRelation, result) {
  if (isPneContextProxyRelation(indicatorRelation, result)) {
    return isProxyMethodologicalRelation(indicatorRelation)
      ? 'Contexto/proxy'
      : 'Contexto'
  }
  if (indicatorRelation.coverage === 'direta') return 'Direta'
  if (indicatorRelation.coverage === 'parcial') return 'Parcial'
  if (indicatorRelation.coverage === 'aproximada') return 'Aproximada'
  return indicatorRelation.coverage ?? 'Relacionada'
}

function getMethodologyWarning(indicatorRelation, result) {
  const indicatorId = indicatorRelation.indicatorId

  if (METHODOLOGY_WARNINGS_BY_KEY[indicatorId]) {
    return METHODOLOGY_WARNINGS_BY_KEY[indicatorId]
  }

  if (isPneContextProxyRelation(indicatorRelation, result)) {
    return 'Indicador exibido apenas como contexto metodológico; não representa cumprimento da meta legal.'
  }

  return ''
}

function isProxyMethodologicalRelation(indicatorRelation) {
  const note = normalizeText(indicatorRelation?.relationNote)
  return note.includes('proxy')
}

function hasUsableMunicipalResult(indicatorRelation, result) {
  if (!indicatorRelation.hasMunicipalResult || !result || result.available === false) {
    return false
  }

  const endValue = Number(result.end_value)
  if (Number.isFinite(endValue)) return true

  return (result.series ?? []).some((point) => Number.isFinite(Number(point?.valor)))
}

function isComparableLegalIndicator(indicatorRelation, result) {
  return isPneComparableIndicator({
    indicatorKey: indicatorRelation.indicatorId,
    indicatorRelation,
    result,
  })
}

function hasComparableDistance(indicatorRelation, result) {
  if (!isComparableLegalIndicator(indicatorRelation, result)) return false
  return Number.isFinite(Number(result?.distance))
}

function hasProjection2036(indicatorRelation, projection) {
  return (
    indicatorRelation.hasProjection2036 === true &&
    projection?.available === true &&
    Number.isFinite(Number(projection.projected_2036))
  )
}

function hasReadableStatus(result) {
  const status = result?.display?.status
  if (!status) return false

  const normalizedStatus = normalizeText(status)
  return !(
    normalizedStatus.includes('visualizacao') ||
    normalizedStatus.includes('informativo') ||
    normalizedStatus.includes('indispon') ||
    normalizedStatus.includes('sem dados')
  )
}

function formatCurrentValue(result, unit) {
  if (result?.display?.end_value) return result.display.end_value
  return formatIndicatorValue(result?.end_value, unit)
}

function formatDistance(result, unit) {
  const ppOptions = { keepOneDecimal: unit === 'index' }
  const displayDistance = roundPpString(result?.display?.distance, ppOptions)

  if (displayDistance) return displayDistance

  const numericDistance = Number(result?.distance)
  if (!Number.isFinite(numericDistance)) return '—'

  const sign = numericDistance > 0 ? '+' : ''
  return `${sign}${PERCENT_FORMATTER.format(numericDistance)} p.p.`
}

function formatProjectionPercent(value) {
  const numeric = Number(value)
  return Number.isFinite(numeric) ? `${PERCENT_FORMATTER.format(numeric)}%` : '—'
}

function formatProjectionDistance(value) {
  const numeric = Number(value)
  if (!Number.isFinite(numeric)) return 'Distância estimada não disponível'
  const sign = numeric > 0 ? '+' : ''
  return `Distância estimada: ${sign}${PERCENT_FORMATTER.format(numeric)} p.p.`
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
