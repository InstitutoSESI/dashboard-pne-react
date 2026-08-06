import { useEffect, useMemo, useState } from 'react'
import {
  ArrowDown,
  ArrowUp,
  BookOpen,
  BriefcaseBusiness,
  Building2,
  ChartColumnIncreasing,
  ChartLine,
  ChartNoAxesColumnIncreasing,
  Clock3,
  Copy,
  Leaf,
  NotebookPen,
  Printer,
  School,
  TrendingUp,
  UserCheck,
  UsersRound,
} from 'lucide-react'
import { CategoryTabs } from './CategoryTabs'
import { ContentState } from './ContentState'
import { DiagnosticPrintReport } from './DiagnosticPrintReport'
import { DisclosureChevron } from './DisclosureChevron'
import { PnePageHeader } from './PnePageHeader'
import { PNE_2026_GOAL_TEXTS } from '../data/pne2026GoalTexts'
import {
  buildPublicDiagnosticCopy,
  buildPublicSummaryText,
  DIAGNOSTIC_RESULT_VIEWS,
  DIAGNOSTIC_VIEW_MODEL_VERSION,
  formatPublicDistance,
  formatPublicValue,
  getDiagnosticSituationKey,
  getPublicCurrentValue,
  getPublicResultReading,
  getPublicResultStatus,
  getPublicStateComparison,
  getPublicSupportingReadings,
  selectDiagnosticResults,
  selectDiagnosticOfficialSources,
  selectDiagnosticThemeGroups,
  selectLegalDiagnosticSummary,
} from '../features/diagnostic/diagnosticPresentation'

const SITUATION_OPTIONS = Object.freeze({
  [DIAGNOSTIC_RESULT_VIEWS.LEGAL]: [
    { key: 'all', label: 'Todos' },
    { key: 'advance', label: 'Abaixo da referência' },
    { key: 'maintain', label: 'Referência alcançada' },
  ],
  [DIAGNOSTIC_RESULT_VIEWS.TRACKING]: [
    { key: 'all', label: 'Todos' },
    { key: 'advance', label: 'Abaixo da referência de acompanhamento' },
    { key: 'maintain', label: 'Na referência de acompanhamento' },
  ],
})

const VIEW_OPTIONS = [
  {
    key: DIAGNOSTIC_RESULT_VIEWS.LEGAL,
    label: 'Referências previstas nas metas',
  },
  {
    key: DIAGNOSTIC_RESULT_VIEWS.TRACKING,
    label: 'Indicadores de acompanhamento',
  },
]

const DIAGNOSTIC_DESCRIPTION = 'Veja os resultados do município em relação às metas do PNE e ao contexto dos municípios do Rio Grande do Sul.'
const ACCELERATED_PACKAGE_RELATIONS = new Set([
  'relation.9.d.educacao_indigena_cobertura_estimada_4_17',
  'relation.10.b.aee_oferta_escolas_elegiveis',
  'relation.14.c.superior_concluintes_oferta_local',
  'relation.15.c.superior_docentes_mestres_doutores_sede',
  'relation.17.c.munic_planos_carreira_declarados',
  'relation.18.c.munic_forum_educacao_declarado',
  'relation.16.a.capes_titulados_oferta_local',
  'relation.15.a.cpc_cursos_oferta_local',
  'relation.17.e.enade_licenciaturas_oferta_local',
])

export function DiagnosticPanel({
  contractStatus = 'ready',
  data,
  initialView = DIAGNOSTIC_RESULT_VIEWS.LEGAL,
  municipio,
}) {
  const publicDiagnostic = data?.pne2026PublicDiagnostic
  const [selectedView, setSelectedView] = useState(initialView)
  const [selectedSituation, setSelectedSituation] = useState('all')
  const [activeThemeId, setActiveThemeId] = useState('')
  const [copyStatus, setCopyStatus] = useState('idle')

  useEffect(() => {
    setSelectedView(initialView)
    setSelectedSituation('all')
    setActiveThemeId('')
    setCopyStatus('idle')
  }, [initialView, publicDiagnostic])

  const legalSummary = useMemo(
    () => selectLegalDiagnosticSummary(publicDiagnostic),
    [publicDiagnostic],
  )
  const viewResults = useMemo(
    () => selectDiagnosticResults(publicDiagnostic, selectedView),
    [publicDiagnostic, selectedView],
  )
  const hasAbove100 = useMemo(
    () => viewResults.some(({ result }) => (
      result.current?.unit === 'percent' && Number(result.current?.value) > 100
    )),
    [viewResults],
  )
  const availableSituations = useMemo(
    () => SITUATION_OPTIONS[selectedView].filter((option) => (
      option.key === 'all'
      || viewResults.some(({ result }) => getDiagnosticSituationKey(result) === option.key)
    )),
    [selectedView, viewResults],
  )
  const visibleThemeGroups = useMemo(
    () => selectDiagnosticThemeGroups(publicDiagnostic, {
      situation: selectedSituation,
      view: selectedView,
    }),
    [publicDiagnostic, selectedSituation, selectedView],
  )
  const themeNavigationItems = useMemo(
    () => visibleThemeGroups.map(({ results, theme }) => ({
      count: results.length,
      key: theme.id,
      label: theme.label,
    })),
    [visibleThemeGroups],
  )

  useEffect(() => {
    if (!themeNavigationItems.length) return
    setActiveThemeId((currentThemeId) => (
      themeNavigationItems.some(({ key }) => key === currentThemeId)
        ? currentThemeId
        : themeNavigationItems[0].key
    ))
  }, [themeNavigationItems])

  function handleViewSelect(view) {
    setSelectedView(view)
    setSelectedSituation('all')
    setActiveThemeId('')
  }

  async function handleCopySummary() {
    try {
      if (!globalThis.navigator?.clipboard?.writeText) throw new Error('clipboard')
      await globalThis.navigator.clipboard.writeText(
        buildPublicDiagnosticCopy(publicDiagnostic, municipio),
      )
      setCopyStatus('copied')
    } catch {
      setCopyStatus('error')
    }
  }

  function handleThemeSelect(themeId) {
    setActiveThemeId(themeId)
    globalThis.document
      ?.getElementById(`pne-diagnostic-theme-section-${themeId}`)
      ?.scrollIntoView({ block: 'start' })
  }

  if (
    contractStatus !== 'ready'
    || publicDiagnostic?.viewModelVersion !== DIAGNOSTIC_VIEW_MODEL_VERSION
  ) {
    return (
      <ContentState kind="error" className="pne-diagnostic-error">
        <strong>Não foi possível abrir o diagnóstico agora. Tente novamente.</strong>
      </ContentState>
    )
  }

  return (
    <div className="pne-diagnostic" data-public-diagnostic-version={publicDiagnostic.version}>
      <PnePageHeader
        actions={<>
          <button type="button" className="pne-diagnostic-action" onClick={handleCopySummary}>
            <ActionIcon name="copy" />
            {copyStatus === 'copied' ? 'Síntese copiada' : 'Copiar síntese'}
          </button>
          <button
            type="button"
            className="pne-diagnostic-action pne-diagnostic-action--primary"
            onClick={() => globalThis.window?.print()}
          >
            <ActionIcon name="print" />
            Imprimir relatório
          </button>
          <span className="u-sr-only" role="status" aria-live="polite">
            {copyStatus === 'copied' ? 'Síntese copiada para a área de transferência.' : ''}
            {copyStatus === 'error' ? 'Não foi possível copiar a síntese.' : ''}
          </span>
        </>}
        asideLabel="Resumo do diagnóstico municipal"
        asideContent={<DiagnosticHeaderSummary summary={legalSummary} />}
        description={DIAGNOSTIC_DESCRIPTION}
        eyebrow="DIAGNÓSTICO MUNICIPAL · PNE 2026–2036"
        title={<>Diagnóstico educacional<span className="pne-page-header__print-context"> de {municipio}</span></>}
      />

      <section className="pne-diagnostic-summary" aria-labelledby="pne-diagnostic-summary-title">
        <div className="pne-diagnostic-section-heading">
          <p>Visão do município</p>
          <h2 id="pne-diagnostic-summary-title">Resumo do diagnóstico</h2>
        </div>
        <p className="pne-diagnostic-summary__reading">
          {buildPublicSummaryText(legalSummary)}
        </p>
        <SummaryCards summary={legalSummary} />
        <p className="pne-diagnostic-summary__availability">
          {legalSummary.comparableIndicatorCount} de {legalSummary.totalIndicatorCount} indicadores possuem comparação disponível para este município.
        </p>
      </section>

      <div
        className="pne-diagnostic-view-switcher"
        aria-label="Tipo de resultado do diagnóstico"
        role="group"
      >
        {VIEW_OPTIONS.map((option) => (
          <FilterButton
            active={selectedView === option.key}
            key={option.key}
            label={option.label}
            onClick={() => handleViewSelect(option.key)}
          />
        ))}
      </div>

      <section className="pne-diagnostic-filters platform-filter-panel" aria-labelledby="pne-diagnostic-filters-title">
        <div className="pne-diagnostic-section-heading">
          <p>Refine a leitura</p>
          <h2 id="pne-diagnostic-filters-title">Filtros</h2>
        </div>
        <div className="pne-diagnostic-filters__groups">
          <FilterGroup label="Situação">
            {availableSituations.map((option) => (
              <FilterButton
                active={selectedSituation === option.key}
                key={option.key}
                label={option.label}
                onClick={() => setSelectedSituation(option.key)}
              />
            ))}
          </FilterGroup>
        </div>
      </section>

      <nav className="pne-diagnostic-theme-nav" aria-label="Navegação entre os temas">
        <p className="pne-diagnostic-theme-nav__title">Navegue pelos temas da página</p>
        <CategoryTabs
          ariaLabel="Temas do diagnóstico"
          categories={themeNavigationItems}
          onSelectCategory={handleThemeSelect}
          selectedCategory={activeThemeId}
        />
      </nav>

      <DiagnosticLegend />

      <section className="pne-diagnostic-results" aria-labelledby="pne-diagnostic-results-title">
        <div className="pne-diagnostic-section-heading pne-diagnostic-section-heading--results">
          <p>
            {selectedView === DIAGNOSTIC_RESULT_VIEWS.LEGAL
              ? 'Referências previstas nas metas'
              : 'Indicadores de acompanhamento'}
          </p>
          <h2 id="pne-diagnostic-results-title">Resultados por tema</h2>
        </div>
        <div className="pne-diagnostic-themes">
          {visibleThemeGroups.map(({ results, summary, theme }) => (
            <ThemeBlock
              key={theme.id}
              results={results}
              sources={publicDiagnostic.sources}
              summary={summary}
              theme={theme}
              view={selectedView}
            />
          ))}
        </div>
      </section>

      <SourcesSection
        hasAbove100={hasAbove100}
        sources={selectDiagnosticOfficialSources(publicDiagnostic, selectedView)}
      />

      <p className="pne-diagnostic-complementary-note">
        Outras informações educacionais sem referência municipal estão disponíveis nas páginas de Indicadores educacionais e no Relatório Técnico.
      </p>

      <DiagnosticPrintReport
        description={DIAGNOSTIC_DESCRIPTION}
        municipio={municipio}
        publicDiagnostic={publicDiagnostic}
      />
    </div>
  )
}

function DiagnosticHeaderSummary({ summary }) {
  return (
    <dl className="pne-page-header__metrics">
      <div className="pne-page-header__metric pne-page-header__metric--info">
        <dt>Indicadores com comparação disponível</dt>
        <dd>{summary.comparableIndicatorCount}</dd>
      </div>
      <div className="pne-page-header__metric pne-page-header__metric--attention">
        <dt>Abaixo da referência</dt>
        <dd>{summary.advanceCount}</dd>
      </div>
      <div className="pne-page-header__metric pne-page-header__metric--success">
        <dt>Referências alcançadas</dt>
        <dd>{summary.maintainCount}</dd>
      </div>
    </dl>
  )
}

function SummaryCards({ summary }) {
  const cards = [
    ['Indicadores com comparação disponível', summary.comparableIndicatorCount, 'neutral'],
    ['Referências alcançadas', summary.maintainCount, 'maintain'],
    ['Abaixo da referência', summary.advanceCount, 'advance'],
    ['Sem comparação no período', summary.unavailableComparisonCount, 'neutral'],
  ]

  return (
    <dl className="pne-diagnostic-summary__cards">
      {cards.map(([label, value, tone], index) => (
        <div
          className={`pne-diagnostic-summary-card pne-diagnostic-summary-card--${tone}${index === 3 ? ' pne-diagnostic-summary-card--context-start' : ''}`}
          key={label}
        >
          <dt>{label}</dt>
          <dd>{value}</dd>
        </div>
      ))}
    </dl>
  )
}

function DiagnosticLegend() {
  return (
    <details className="pne-diagnostic-legend platform-support-disclosure">
      <summary className="platform-support-disclosure__summary">
        <span>Como ler os quadros de comparação</span>
        <DisclosureChevron />
      </summary>
      <div className="pne-diagnostic-legend__body platform-support-disclosure__body">
        <p className="pne-diagnostic-legend__intro">
          Em cada indicador, além da meta do PNE, o município aparece ao lado do Rio Grande do Sul — com o valor do estado e a diferença do município para ele — e é comparado a municípios de porte parecido. As etiquetas abaixo resumem essas leituras.
        </p>
        <div className="pne-diagnostic-legend__grid">
          <LegendCard
            desc="Onde o município está entre todos os do RS neste indicador."
            icon="position"
            items={[
              ['positive', 'Faixa superior', 'entre os de resultado mais favorável'],
              ['neutral', 'Faixa intermediária', 'no meio da distribuição estadual'],
              ['attention', 'Faixa prioritária', 'entre os com maior espaço para avançar'],
            ]}
            title="Posição no RS"
          />
          <LegendCard
            desc="Comparação com municípios de porte educacional parecido."
            icon="similar"
            items={[
              ['positive', 'Acima da mediana', 'resultado acima do grupo semelhante'],
              ['attention', 'Abaixo da mediana', 'resultado abaixo do grupo semelhante'],
            ]}
            title="Municípios semelhantes"
          />
          <LegendCard
            desc="Como o indicador variou nos últimos anos disponíveis."
            icon="reading"
            items={[
              ['positive', 'Melhorou nos últimos anos', 'avançou no período'],
              ['neutral', 'Permaneceu estável', 'sem variação relevante'],
              ['attention', 'Recuou nos últimos anos', 'perdeu terreno no período'],
            ]}
            title="Evolução recente"
          />
        </div>
      </div>
    </details>
  )
}

function LegendCard({ desc, icon, items, title }) {
  return (
    <article className="pne-diagnostic-legend__card">
      <header className="pne-diagnostic-legend__card-head">
        <span className="pne-diagnostic-legend__card-icon" aria-hidden="true">
          <DiagnosticSupportIcon name={icon} />
        </span>
        <h3>{title}</h3>
      </header>
      <p className="pne-diagnostic-legend__card-desc">{desc}</p>
      {items ? (
        <dl className="pne-diagnostic-legend__items">
          {items.map(([tone, label, meaning]) => (
            <div className="pne-diagnostic-legend__item" key={label}>
              <dt>
                <span className={`pne-diagnostic-support-reading__badge pne-diagnostic-support-reading__badge--${tone}`}>
                  {label}
                </span>
              </dt>
              <dd>{meaning}</dd>
            </div>
          ))}
        </dl>
      ) : null}
    </article>
  )
}

function FilterGroup({ children, label }) {
  return (
    <fieldset className="pne-diagnostic-filter-group">
      <legend>{label}</legend>
      <div className="pne-diagnostic-filter-group__options">{children}</div>
    </fieldset>
  )
}

function FilterButton({ active, label, onClick }) {
  return (
    <button
      type="button"
      aria-pressed={active}
      className={`platform-filter-option pne-diagnostic-filter${active ? ' is-active' : ''}`}
      onClick={onClick}
    >
      {label}
    </button>
  )
}

function ThemeBlock({
  results,
  sources,
  summary,
  theme,
  view,
}) {
  const titleId = `pne-diagnostic-theme-${theme.id}`

  return (
    <article className="pne-diagnostic-theme" aria-labelledby={titleId} id={`pne-diagnostic-theme-section-${theme.id}`}>
      <details className="pne-diagnostic-theme__disclosure" open>
      <summary className="pne-diagnostic-theme__header">
        <div className="pne-diagnostic-theme__heading">
          <span className="pne-diagnostic-theme__icon" aria-hidden="true">
            <DiagnosticIcon name={theme.id} />
          </span>
          <div>
            <p>Tema {theme.visibleOrder}</p>
            <h3 id={titleId}>{theme.label}</h3>
          </div>
        </div>
        <ThemeSummary summary={summary} view={view} />
      </summary>
      <div className="pne-diagnostic-theme__results">
        {results.map(({ goal, result }) => (
          <ResultCard
            goal={goal}
            headingLevel={4}
            key={result.relationId}
            result={result}
            sources={sources}
            standalone
          />
        ))}
      </div>
      </details>
    </article>
  )
}

function ThemeSummary({ summary, view }) {
  const items = view === DIAGNOSTIC_RESULT_VIEWS.TRACKING
    ? [
        ['Indicadores', summary.total],
        ['Na referência de acompanhamento', summary.maintain],
        ['Abaixo da referência de acompanhamento', summary.advance],
      ]
    : [
        ['Indicadores', summary.total],
        ['Referências alcançadas', summary.maintain],
        ['Abaixo da referência', summary.advance],
      ]

  return (
    <dl className="pne-diagnostic-theme-summary">
      {items.map(([label, value]) => (
        <div key={label}>
          <dt>{label}</dt>
          <dd>{value}</dd>
        </div>
      ))}
    </dl>
  )
}

function ResultCard({
  goal,
  headingLevel,
  result,
  sources,
  standalone = false,
}) {
  const isComplementary = result.mode === 'complementary'
  const isAvailable = result.dataStatus === 'available'
  const hasReference = isAvailable && Number.isFinite(result.indicatorReference?.value)
  const distanceAvailable = Number.isFinite(result.distance)
  const stateComparison = getPublicStateComparison(result)
  const supportingReadings = getPublicSupportingReadings(result)
  const status = getPublicResultStatus(result)
  const titleId = `pne-diagnostic-result-${goal.goalId}-${result.indicatorId}`
  const Heading = `h${headingLevel}`
  const currentValue = getPublicCurrentValue(result)
  const publicReading = getPublicResultReading(result)
  const legalText = PNE_2026_GOAL_TEXTS[goal.goalId]?.displayText
  const positionReading = supportingReadings.find(({ kind }) => kind === 'position')
  const similarReading = supportingReadings.find(({ kind }) => kind === 'similar')
  const trajectoryReading = supportingReadings.find(({ kind }) => kind === 'trajectory')
  const trajectoryBadge = trajectoryReading ? getSupportingReadingBadge(trajectoryReading) : ''
  const hasCompare = Boolean(stateComparison || positionReading || similarReading)
  const hasFooter = Boolean(trajectoryReading || publicReading)
  // Distância como frase: "faltam X" quando abaixo da referência, "+X além da
  // meta" quando alcançada. A palavra segue a situação, não o sinal cru.
  const distanceSigned = distanceAvailable
    ? formatPublicDistance(result.distance, result.current.unit)
    : ''
  const reachedReference = status.key === 'maintain'
  const gapText = reachedReference
    ? `${distanceSigned} além da meta`
    : `faltam ${distanceSigned.replace(/^[+−-]/, '')}`
  // A primeira linha da trajetória é a síntese ("melhorou/recuou"), já no rodapé.
  // Só as ressalvas de cenário (linha de base, denominador, incerteza) descem
  // para a divulgação recolhida — nada some, e o cartão não estica sem ressalva.
  const trajectoryNotes = trajectoryReading ? trajectoryReading.lines.slice(1) : []
  const isAccelerated = ACCELERATED_PACKAGE_RELATIONS.has(result.relationId)
  const showDisclosure = trajectoryNotes.length > 0 || isAccelerated

  return (
    <article
      className={`pne-diagnostic-result pne-diagnostic-result--${status.key}${standalone ? ' pne-diagnostic-result--standalone' : ''}`}
      aria-labelledby={titleId}
    >
      <header className="pne-diagnostic-result__head">
        <span className="pne-diagnostic-result__icon" aria-hidden="true">
          <DiagnosticIcon name={result.themeId} />
        </span>
        <div className="pne-diagnostic-result__id">
          <p className="pne-diagnostic-result__goal-context">Meta {goal.goalId} — {goal.title}</p>
          <Heading className="pne-diagnostic-result__name" id={titleId}>{result.publicName}</Heading>
        </div>
        {!isComplementary && isAvailable ? (
          <span className={`pne-diagnostic-result__status pne-diagnostic-result__status--${status.key}`}>
            {status.label}
          </span>
        ) : null}
      </header>

      {legalText ? (
        <div className="pne-diagnostic-result__legal">
          <p className="pne-diagnostic-result__legal-label">O que diz a meta no PNE</p>
          <p className="pne-diagnostic-result__legal-text">{legalText}</p>
        </div>
      ) : null}

      <div className="pne-diagnostic-result__panels">
        <section className="pne-diagnostic-result__panel pne-diagnostic-result__panel--meta" aria-label="Resultado em relação à meta do PNE">
          <p className="pne-diagnostic-result__panel-label">Meta do PNE</p>
          <p className="pne-diagnostic-result__hero">
            <strong>{currentValue}</strong>
            {Number.isFinite(result.current?.year)
              ? <span>resultado {result.current.year}</span>
              : null}
          </p>
          {hasReference ? (
            <p className="pne-diagnostic-result__target">
              {result.mode === 'tracking' ? 'Referência de acompanhamento: ' : 'Referência: '}
              <b>{formatPublicValue(result.indicatorReference?.value, result.current.unit)}</b>
              {Number.isFinite(result.indicatorReference?.year)
                ? <> até <b>{result.indicatorReference.year}</b></>
                : null}
            </p>
          ) : null}
          {distanceAvailable ? (
            <span
              className="pne-diagnostic-result__gap"
              title={result.mode === 'tracking'
                ? 'Distância para a referência de acompanhamento'
                : 'Distância para a referência'}
            >
              <DistanceIcon value={result.distance} />
              {gapText}
            </span>
          ) : null}
        </section>

        {hasCompare ? (
          <section className="pne-diagnostic-result__panel pne-diagnostic-result__panel--compare" aria-label="Comparação com o Rio Grande do Sul e municípios semelhantes">
            <p className="pne-diagnostic-result__panel-label">Como se compara</p>
            <dl className="pne-diagnostic-result__compare">
              {stateComparison ? (
                <div className="pne-diagnostic-result__compare-row">
                  <dt>
                    <span className="pne-diagnostic-result__compare-icon" aria-hidden="true">
                      <DiagnosticSupportIcon name="comparison" />
                    </span>
                    Rio Grande do Sul
                  </dt>
                  <dd className="pne-diagnostic-result__compare-values">
                    <span className="pne-diagnostic-result__compare-value">{stateComparison.stateValue}</span>
                    <span className="pne-diagnostic-result__compare-diff">{stateComparison.difference}</span>
                  </dd>
                </div>
              ) : null}
              {similarReading ? (
                <CompareBadgeRow icon="similar" label="Municípios semelhantes" reading={similarReading} />
              ) : null}
              {positionReading ? (
                <CompareBadgeRow icon="position" label="Posição no RS" reading={positionReading} />
              ) : null}
            </dl>
          </section>
        ) : null}
      </div>

      {hasFooter ? (
        <footer className="pne-diagnostic-result__foot">
          {trajectoryReading ? (
            <span className={`pne-diagnostic-result__evo pne-diagnostic-result__evo--${getSupportingBadgeTone(trajectoryBadge)}`}>
              <span className="pne-diagnostic-result__evo-icon" aria-hidden="true">
                <DiagnosticSupportIcon name="trajectory" />
              </span>
              {trajectoryBadge || 'Evolução recente'}
            </span>
          ) : null}
          {publicReading ? (
            <p className="pne-diagnostic-result__reading">{publicReading}</p>
          ) : null}
        </footer>
      ) : null}

      {showDisclosure ? (
        <MethodologyDisclosure
          isAccelerated={isAccelerated}
          notes={trajectoryNotes}
          result={result}
          sources={sources}
        />
      ) : null}
    </article>
  )
}

function CompareBadgeRow({ icon, label, reading }) {
  const badge = getSupportingReadingBadge(reading)
  const tone = getSupportingBadgeTone(badge)

  return (
    <div className="pne-diagnostic-result__compare-row">
      <dt>
        <span className="pne-diagnostic-result__compare-icon" aria-hidden="true">
          <DiagnosticSupportIcon name={icon} />
        </span>
        {label}
      </dt>
      <dd className="pne-diagnostic-result__compare-values">
        {badge ? (
          <span className={`pne-diagnostic-support-reading__badge pne-diagnostic-support-reading__badge--${tone}`}>
            {badge}
          </span>
        ) : (
          <span className="pne-diagnostic-result__compare-note">{reading.lines[0]}</span>
        )}
      </dd>
    </div>
  )
}

function DistanceIcon({ value }) {
  const down = Number(value) < 0
  const Icon = down ? ArrowDown : ArrowUp
  return <Icon aria-hidden="true" />
}

function MethodologyDisclosure({ isAccelerated = false, notes = [], result, sources = [] }) {
  const selectedSources = result.sourceIds
    .map((sourceId) => sources.find((source) => source.id === sourceId))
    .filter(Boolean)
  const numerator = Number.isFinite(result.numerator)
    ? result.numerator.toLocaleString('pt-BR')
    : null
  const denominator = Number.isFinite(result.denominator)
    ? result.denominator.toLocaleString('pt-BR')
    : null
  const hasCalc = isAccelerated
    && (selectedSources.length || result.methodology || numerator !== null || denominator !== null)
  const summary = notes.length && hasCalc
    ? 'Evolução recente e cálculo'
    : notes.length
      ? 'Evolução recente e cenário'
      : 'Fonte e cálculo'

  return (
    <details className="pne-diagnostic-result__methodology">
      <summary>{summary}</summary>
      <div>
        {notes.map((note) => <p key={note}>{note}</p>)}
        {hasCalc && selectedSources.length ? (
          <p>
            <strong>Fonte:</strong>{' '}
            {selectedSources.map((source) => source.publicTitle).join('; ')}.
          </p>
        ) : null}
        {hasCalc && result.methodology ? (
          <p>
            <strong>Cálculo:</strong>{' '}
            {result.methodology.description}
          </p>
        ) : null}
        {hasCalc && (numerator !== null || denominator !== null) ? (
          <dl>
            {numerator !== null ? (
              <div><dt>Numerador</dt><dd>{numerator}</dd></div>
            ) : null}
            {denominator !== null ? (
              <div><dt>Denominador</dt><dd>{denominator}</dd></div>
            ) : null}
          </dl>
        ) : null}
      </div>
    </details>
  )
}

function getSupportingBadgeTone(badge = '') {
  const normalizedBadge = badge.toLocaleLowerCase('pt-BR')

  if (
    normalizedBadge.includes('prioritária')
    || normalizedBadge.includes('abaixo')
    || normalizedBadge.includes('recuou')
  ) {
    return 'attention'
  }

  if (
    normalizedBadge.includes('superior')
    || normalizedBadge.includes('acima')
    || normalizedBadge.includes('melhorou')
  ) {
    return 'positive'
  }

  return 'neutral'
}

function getSupportingReadingBadge({ kind, lines }) {
  const reading = lines.join(' ').toLocaleLowerCase('pt-BR')

  if (kind === 'position') {
    if (reading.includes('mais favoráveis')) return 'Faixa superior'
    if (reading.includes('maior espaço para avançar')) return 'Faixa prioritária'
    if (reading.includes('intermediária')) return 'Faixa intermediária'
    return ''
  }

  if (kind === 'similar') {
    if (reading.includes('acima da mediana')) return 'Acima da mediana'
    if (reading.includes('abaixo da mediana')) return 'Abaixo da mediana'
    return ''
  }

  if (reading.includes('melhorou')) return 'Melhorou nos últimos anos'
  if (reading.includes('recuou')) return 'Recuou nos últimos anos'
  if (reading.includes('estável')) return 'Permaneceu estável'
  return ''
}

function DiagnosticSupportIcon({ name }) {
  const icons = {
    comparison: ChartColumnIncreasing,
    reading: BookOpen,
    position: ChartNoAxesColumnIncreasing,
    similar: UsersRound,
    trajectory: TrendingUp,
  }
  const Icon = icons[name] ?? TrendingUp
  return <Icon aria-hidden="true" />
}


function SourcesSection({ hasAbove100, sources }) {
  return (
    <section className="pne-diagnostic-sources" aria-labelledby="pne-diagnostic-sources-title">
      <div className="pne-diagnostic-section-heading">
        <p>Dados oficiais</p>
        <h2 id="pne-diagnostic-sources-title">Fontes das informações</h2>
      </div>
      <ul>
        {sources.map((source) => (
          <li key={source.id}>
            <div>
              <strong>{source.organization}</strong>
              <span>{source.publicTitle} · {source.period}</span>
            </div>
            <a
              aria-label={`Acessar fonte oficial: ${source.organization} — ${source.publicTitle}`}
              href={source.officialUrl}
              rel="noreferrer"
              target="_blank"
            >
              Acessar fonte oficial
            </a>
          </li>
        ))}
      </ul>
      {hasAbove100 ? (
        <p className="pne-diagnostic-sources__method-note">
          Há resultado percentual acima de 100% neste município. O valor bruto foi preservado; esse comportamento pode decorrer da combinação entre matrículas por local de oferta e estimativas da população residente.
        </p>
      ) : null}
    </section>
  )
}

function ActionIcon({ name }) {
  const Icon = name === 'copy' ? Copy : Printer
  return <Icon aria-hidden="true" />
}

function DiagnosticIcon({ name }) {
  const icons = {
    atendimento_escolar_v2: School,
    educacao_tempo_integral_v2: Clock3,
    aprendizagem_trajetoria_escolar_v2: BookOpen,
    escolaridade_alfabetizacao_v2: NotebookPen,
    educacao_profissional_eja_v2: BriefcaseBusiness,
    profissionais_educacao_v2: UserCheck,
    infraestrutura_escolar_v2: Building2,
    gestao_escolar_educacao_ambiental_v2: Leaf,
  }
  const Icon = icons[name] ?? ChartLine
  return <Icon aria-hidden="true" />
}
