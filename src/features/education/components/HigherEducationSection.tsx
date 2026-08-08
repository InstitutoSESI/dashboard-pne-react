import type { RefObject } from 'react'
import { ContentState } from '../../../components/ContentState'
import { DetailNavigation } from '../../../components/DetailNavigation'
import { DisclosureChevron } from '../../../components/DisclosureChevron'
import { EducationBarChart } from '../../../components/EducationBarChart'
import { EducationIndicatorCard } from '../../../components/EducationIndicatorCard'
import { EducationLineChart } from '../../../components/EducationLineChart'
import { EducationQuickReading } from '../../../components/EducationQuickReading'
import { EducationTable } from '../../../components/EducationTable'
import { ErrorState } from '../../../components/ErrorState'
import { MetricCard } from '../../../components/MetricCard'
import { QuestionHeading } from '../../../components/QuestionHeading'
import type { AsyncDataState } from '../../../types/async'
import type {
  HigherEducationAnnualPoint,
  HigherEducationBreakdownViewModel,
  HigherEducationIndicatorViewModel,
  HigherEducationViewModel,
} from '../higherEducationTypes'
import {
  analyzeHigherEducationBreakdown,
  analyzeHigherEducationSeries,
  areHigherEducationSeriesEqual,
  hasSubstantiveSupportContent,
  publicHigherEducationTitle,
} from '../higherEducationPresentation'
import { EducationCompactHeader } from './EducationCompactHeader'

type HigherEducationPayload = { viewModel: HigherEducationViewModel } | null

interface HigherEducationSectionProps {
  detailKey: string
  detailViewRef: RefObject<HTMLDivElement | null>
  municipalityName: string
  onBack: () => void
  onOpenIndicator: (indicatorKey: string) => void
  onSelectAdjacent: (indicatorKey: string) => void
  registerCard: (itemKey: string, node: HTMLButtonElement | null) => void
  state: AsyncDataState<HigherEducationPayload>
}

const numberFormatter = new Intl.NumberFormat('pt-BR')
const percentFormatter = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 1, minimumFractionDigits: 1 })
const GROUP_CUTS: Record<string, string> = {
  enrollments: 'Matrículas',
  institutions: 'Instituições e polos',
  'access-flow': 'Acesso e fluxo',
  faculty: 'Docentes',
}

function formatValue(value: number | null) {
  return value == null ? '—' : numberFormatter.format(value)
}

function statusLabel(point: HigherEducationAnnualPoint | null) {
  if (point?.status === 'observed') return 'Observado'
  if (point?.status === 'derived_zero') return 'Zero derivado'
  if (point?.status === 'not_applicable') return 'Não aplicável'
  return 'Indisponível'
}

function trendLabel(indicator: HigherEducationIndicatorViewModel, historical: boolean) {
  if (historical) return 'Informação histórica'
  return analyzeHigherEducationSeries(indicator).trendLabel
}

function variationDisplay(indicator: HigherEducationIndicatorViewModel) {
  if (!indicator.firstPoint || !indicator.latestPoint) return '—'
  if (indicator.percentVariation != null) {
    return `${indicator.percentVariation > 0 ? '+' : ''}${percentFormatter.format(indicator.percentVariation)}%`
  }
  if (indicator.absoluteVariation != null) {
    return `${indicator.absoluteVariation > 0 ? '+' : ''}${numberFormatter.format(indicator.absoluteVariation)} ${indicator.unit}`
  }
  return '—'
}

function cardAdapter(indicator: HigherEducationIndicatorViewModel) {
  const presentation = analyzeHigherEducationSeries(indicator)
  const comparisonSeries = [indicator.firstPoint, indicator.latestPoint]
    .filter((point, index, points): point is HigherEducationAnnualPoint => Boolean(
      point && points.findIndex((candidate) => candidate?.year === point.year) === index,
    ))
  return {
    key: indicator.id,
    label: publicHigherEducationTitle(indicator),
    description: indicator.description,
    themeShortLabel: GROUP_CUTS[indicator.group],
    currentDisplay: formatValue(indicator.currentValue),
    currentValue: indicator.currentValue,
    currentYear: indicator.currentYear,
    unit: indicator.unit,
    neutralTrend: false,
    statusLabel: indicator.availability === 'historical_only'
      ? 'Informação histórica'
      : presentation.trendLabel,
    statusTone: 'muted',
    cardReading: indicator.availability === 'historical_only'
      ? 'Informação histórica'
      : presentation.reading,
    zeroMessage: indicator.currentStatus === 'derived_zero'
      ? 'Zero derivado a partir de componentes observados na fonte.'
      : undefined,
    series: comparisonSeries.map((point) => ({ ano: point.year, valor: point.value })),
    formatValue,
  }
}

export function HigherEducationSection(props: HigherEducationSectionProps) {
  const { state } = props
  if (state.loading) {
    return <ContentState kind="loading" className="state-box state-box--loading">Carregando dados de Educação Superior...</ContentState>
  }
  if (state.error) {
    return <ErrorState title="Não foi possível carregar a Educação Superior" message={state.error} />
  }
  const viewModel = state.data?.viewModel
  if (!viewModel) {
    return <ContentState kind="unavailable" className="state-box">Dados municipais de Educação Superior indisponíveis.</ContentState>
  }
  const activeIndicator = viewModel.indicators.find(
    (indicator) => indicator.id === props.detailKey && indicator.latestPoint,
  )
  return activeIndicator
    ? <HigherEducationDetail {...props} indicator={activeIndicator} viewModel={viewModel} />
    : <HigherEducationLanding {...props} viewModel={viewModel} />
}

function HigherEducationLanding({
  onOpenIndicator,
  registerCard,
  viewModel,
}: HigherEducationSectionProps & { viewModel: HigherEducationViewModel }) {
  const situation = viewModel.availability === 'current'
    ? 'Dados atuais'
    : viewModel.availability === 'historical_only'
      ? 'Informações históricas'
      : 'Sem informações integradas'
  const availableCount = viewModel.indicators.filter(
    (indicator) => indicator.latestPoint && indicator.group !== 'composition',
  ).length
  const countLabel = availableCount === 0
    ? 'Sem indicadores disponíveis'
    : `${availableCount} ${availableCount === 1 ? 'indicador' : 'indicadores'}`
  return (
    <main className="higher-education-page higher-education-landing">
      <EducationCompactHeader
        contextItems={[
          { icon: 'period', label: 'Período publicado', value: viewModel.globalPeriod },
          { icon: 'period', label: 'Última referência municipal', value: viewModel.latestMunicipalUsableYear ? String(viewModel.latestMunicipalUsableYear) : 'Sem referência' },
          ...(viewModel.availability === 'current'
            ? []
            : [{ icon: 'source' as const, label: 'Situação da informação', value: situation }]),
        ]}
        description="Matrículas, instituições, polos, acesso, fluxo e docentes mostram a presença municipal da graduação."
        eyebrow="Indicadores de Educação / Educação Superior"
        title="Como a graduação está presente no município?"
        variant="section"
      />
      <section className="cycle-workspace educacao-workspace higher-education-workspace">
        <div className="education-filter-bar higher-education-filter-bar" aria-label="Indicadores da Educação Superior">
          <span className="education-filter-bar__count">{countLabel}</span>
        </div>
        {viewModel.availability === 'historical_only' ? (
          <ContentState kind="unavailable" className="state-box higher-education-information-state">
            <strong>Informações históricas disponíveis</strong>
            <span>O município possui registros de Educação Superior no período publicado, mas não apresenta informações utilizáveis no último ano da base.</span>
          </ContentState>
        ) : null}
        {viewModel.availability === 'unavailable' ? (
          <>
            <ContentState kind="unavailable" className="state-box higher-education-unavailable">
              <strong>Sem informações municipais integradas</strong>
              <span>Não foram identificadas informações utilizáveis de Educação Superior para o município no período de 2018 a 2024 nas tabelas utilizadas.</span>
            </ContentState>
            <SourceAndReading />
          </>
        ) : (
          <>
            <div className="education-indicator-groups higher-education-indicator-groups">
              {viewModel.groups.filter((group) => group.id !== 'composition').map((group) => {
                const indicators = viewModel.indicators.filter((item) => item.group === group.id)
                const availableIndicators = indicators.filter((item) => item.latestPoint)
                const unavailableIndicators = indicators.filter((item) => !item.latestPoint)
                const countLabel = availableIndicators.length === 0
                  ? 'Sem informação municipal'
                  : unavailableIndicators.length
                    ? `${availableIndicators.length} com dados · ${unavailableIndicators.length} sem informação`
                    : `${availableIndicators.length} ${availableIndicators.length === 1 ? 'indicador' : 'indicadores'}`
                return (
                  <section className="education-indicator-group" aria-labelledby={`higher-education-${group.id}-title`} key={group.id}>
                    <div className="education-indicator-group__heading">
                      <div>
                        {group.question ? <span className="eyebrow">{group.title}</span> : null}
                        <h2 id={`higher-education-${group.id}-title`}>
                          {group.question ? <QuestionHeading text={group.question} /> : group.title}
                        </h2>
                      </div>
                      <span>{countLabel}</span>
                    </div>
                    <p className="education-indicator-group__description">{group.description}</p>
                    <div className="education-indicator-card-grid">
                      {availableIndicators.map((indicator) => (
                        <EducationIndicatorCard
                          buttonRef={(node: HTMLButtonElement | null) => registerCard(indicator.id, node)}
                          indicator={cardAdapter(indicator)}
                          key={indicator.id}
                          onSelect={() => onOpenIndicator(indicator.id)}
                        />
                      ))}
                    </div>
                    {unavailableIndicators.length ? (
                      <ContentState kind="empty" className="higher-education-unavailable-strip">
                        <strong>Sem informação municipal:</strong>
                        <span>{formatIndicatorList(unavailableIndicators.map(publicHigherEducationTitle))}.</span>
                      </ContentState>
                    ) : null}
                  </section>
                )
              })}
            </div>
            <InstitutionalComposition viewModel={viewModel} />
            <SourceAndReading />
          </>
        )}
      </section>
    </main>
  )
}

function HigherEducationDetail({
  detailViewRef,
  indicator,
  municipalityName,
  onBack,
  onSelectAdjacent,
  viewModel,
}: HigherEducationSectionProps & {
  indicator: HigherEducationIndicatorViewModel
  viewModel: HigherEducationViewModel
}) {
  const usable = viewModel.indicators.filter((item) => item.latestPoint)
  const activeIndex = usable.findIndex((item) => item.id === indicator.id)
  const previous = activeIndex > 0 ? { key: usable[activeIndex - 1].id } : null
  const next = activeIndex < usable.length - 1 ? { key: usable[activeIndex + 1].id } : null
  const historical = indicator.availability === 'historical_only'
  const seriesPresentation = analyzeHigherEducationSeries(indicator)
  const publicTitle = publicHigherEducationTitle(indicator)
  const period = indicator.firstPoint && indicator.latestPoint
    ? `${indicator.firstPoint.year}–${indicator.latestPoint.year}`
    : 'Série insuficiente'
  const seriesRows = indicator.series.map((point) => ({
    year: point.year,
    value: point.value,
    status: statusLabel(point),
  }))
  return (
    <main className="higher-education-page higher-education-detail education-detail-view" ref={detailViewRef}>
      <EducationCompactHeader
        backLink={{ onClick: onBack, label: 'Voltar aos indicadores' }}
        contextItems={[
          { icon: 'municipality', label: 'Município', value: municipalityName },
          { icon: 'cut', label: 'Recorte', value: GROUP_CUTS[indicator.group] },
          { icon: 'period', label: 'Período', value: period },
        ]}
        description={indicator.description}
        eyebrow="Indicador de Educação Superior"
        title={publicTitle}
        variant="detail"
      />
      <DetailNavigation
        activeIndex={activeIndex}
        className="education-detail-nav"
        contextLabel={GROUP_CUTS[indicator.group]}
        nextItem={next}
        nextLabel={undefined}
        onBack={onBack}
        onNext={onSelectAdjacent}
        onPrevious={onSelectAdjacent}
        previousItem={previous}
        showBack={false}
        total={usable.length}
      />
      {historical ? (
        <ContentState kind="unavailable" className="state-box higher-education-information-state">
          <strong>Informação histórica</strong>
          <span>A série disponível para este indicador não alcança 2024; o último valor utilizável é de {indicator.currentYear}.</span>
        </ContentState>
      ) : null}
      <section className="educacao-detail-panel educacao-detail-panel--organized" aria-label="Resumo e evolução do indicador">
        <div className="metric-grid metric-grid--four education-metric-summary">
          <MetricCard label="Valor inicial" value={formatValue(indicator.firstPoint?.value ?? null)} detail={indicator.firstPoint ? `${indicator.firstPoint.year} · ${indicator.unit}` : 'Série indisponível'} icon="start" />
          <MetricCard label="Valor mais recente" value={formatValue(indicator.latestPoint?.value ?? null)} detail={indicator.latestPoint ? `${indicator.latestPoint.year} · ${indicator.unit}` : 'Série indisponível'} icon="current" />
          <MetricCard label="Variação no período" value={variationDisplay(indicator)} detail={variationDetail(indicator)} icon="variation" />
          <MetricCard label="Tendência observada" value={trendLabel(indicator, historical)} detail="Classificação descritiva da série" icon="status" />
        </div>
        <div className="education-primary-analysis">
          <article className="educacao-main-chart-card indicator-chart-card">
            <div className="indicator-chart-title-group">
              <span className="eyebrow">Evolução do indicador</span>
              <h2>{publicTitle}</h2>
              <p>Valores municipais publicados entre 2018 e 2024. Lacunas interrompem a linha.</p>
            </div>
            {seriesPresentation.kind === 'line' ? (
              <EducationLineChart
                formatLabel={numberFormatter.format}
                hideTitle
                integerTicks
                scaleType="count"
                series={indicator.series.map((point) => ({ ano: point.year, valor: point.value }))}
                showPointLabels
                title={`Evolução anual de ${publicTitle}`}
              />
            ) : (
              <SeriesAnalyticalState indicator={indicator} presentation={seriesPresentation} />
            )}
            <p className="higher-education-panel-source">Fonte: Censo da Educação Superior — INEP</p>
          </article>
          <EducationQuickReading
            items={[
              { key: 'trend', icon: 'trend', label: 'Evolução observada', text: buildEvolutionReading(indicator) },
              { key: 'measure', icon: 'measure', label: 'O que o indicador mede', text: indicator.description },
              { key: 'cut', icon: 'cut', label: 'Referência territorial', text: territorialLabel(indicator.territorialReference) },
            ]}
          />
        </div>
        <details className="platform-support-disclosure higher-education-series-disclosure">
          <summary className="platform-support-disclosure__summary"><div><h3>Ver valores da série</h3><p>Consulte os valores anuais e o estado de cada observação.</p></div><DisclosureChevron /></summary>
          <div className="platform-support-disclosure__body">
            <EducationTable
              caption={`Série histórica de ${publicTitle}`}
              columns={[
                { key: 'year', label: 'Ano', rowHeader: true },
                { key: 'value', label: 'Valor', numeric: true, format: formatValue },
                { key: 'status', label: 'Estado da informação' },
              ]}
              rows={seriesRows}
            />
          </div>
        </details>
      </section>
      <SupportData indicator={indicator} viewModel={viewModel} />
      <IndicatorMethodology indicator={indicator} />
      <DetailNavigation
        activeIndex={activeIndex}
        className="education-detail-nav education-detail-nav--bottom"
        isBottom
        nextItem={next}
        nextLabel={undefined}
        onBack={onBack}
        onNext={onSelectAdjacent}
        onPrevious={onSelectAdjacent}
        previousItem={previous}
        total={usable.length}
      />
    </main>
  )
}

function buildEvolutionReading(indicator: HigherEducationIndicatorViewModel) {
  if (!indicator.firstPoint || !indicator.latestPoint) return 'Série insuficiente para comparação.'
  const base = `Em ${indicator.latestPoint.year}, o município registrou ${formatValue(indicator.latestPoint.value)} ${indicator.unit}.`
  if (indicator.absoluteVariation == null) return base
  if (indicator.absoluteVariation === 0) {
    return `Entre ${indicator.firstPoint.year} e ${indicator.latestPoint.year}, a série permaneceu em ${formatValue(indicator.latestPoint.value)} ${indicator.unit}.`
  }
  const direction = indicator.absoluteVariation > 0 ? 'aumento' : 'redução'
  return `${base} Em relação a ${indicator.firstPoint.year}, houve ${direction} de ${formatValue(Math.abs(indicator.absoluteVariation))} ${indicator.unit}.`
}

function SeriesAnalyticalState({
  indicator,
  presentation,
}: {
  indicator: HigherEducationIndicatorViewModel
  presentation: ReturnType<typeof analyzeHigherEducationSeries>
}) {
  if (presentation.kind === 'constant_zero') {
    return (
      <div className="higher-education-analytical-state" role="note">
        <span className="higher-education-analytical-state__marker" aria-hidden="true" />
        <span>Série constante em zero</span>
        <strong>0 {indicator.unit}</strong>
        <p>Sem variação entre {presentation.firstPoint?.year} e {presentation.latestPoint?.year}.</p>
        {presentation.usefulPoints.some((point) => point.status === 'derived_zero') ? (
          <small>Zero derivado a partir de componentes observados na fonte.</small>
        ) : null}
      </div>
    )
  }
  if (presentation.kind === 'single_point') {
    return (
      <div className="higher-education-analytical-state" role="note">
        <span>Série insuficiente para evolução</span>
        <strong>{formatValue(presentation.latestPoint?.value ?? null)} {indicator.unit}</strong>
        <p>Há somente um ponto utilizável, referente a {presentation.latestPoint?.year}.</p>
      </div>
    )
  }
  return (
    <ContentState kind="empty" className="higher-education-analytical-state">
      Sem informação municipal utilizável para exibir a evolução.
    </ContentState>
  )
}

function territorialLabel(reference: string) {
  if (reference === 'ies_administrative_headquarters') return 'Sede administrativa da instituição no município.'
  if (reference === 'faculty_institution_headquarters') return 'Docentes vinculados a instituições com sede no município.'
  if (reference === 'ead_offer_location') return 'Local de oferta de educação a distância registrado no município.'
  return 'Local de oferta do curso registrado no município.'
}

function SupportData({ indicator, viewModel }: { indicator: HigherEducationIndicatorViewModel; viewModel: HigherEducationViewModel }) {
  const breakdowns = viewModel.breakdowns.filter(
    (breakdown) => indicator.relatedBreakdowns.includes(breakdown.id) && breakdown.year != null,
  )
  const related: HigherEducationIndicatorViewModel[] = []
  if (indicator.id === 'esup-matriculas-ead') {
    const total = viewModel.indicators.find((item) => item.id === 'esup-matriculas-total')
    const poles = viewModel.indicators.find((item) => item.id === 'esup-polos-ead')
    if (total && !areHigherEducationSeriesEqual(indicator, total)) related.push(total)
    if (poles) related.push(poles)
  }
  const usefulRelated = related.filter((item) => item.latestPoint && analyzeHigherEducationSeries(item).kind === 'line')
  const showComposition = ['esup-matriculas-total', 'esup-matriculas-presenciais', 'esup-matriculas-ead'].includes(indicator.id)
    && viewModel.modalityComposition
  if (!hasSubstantiveSupportContent({
    breakdownCount: breakdowns.length,
    hasComposition: Boolean(showComposition),
    hasUsefulReferenceSeries: usefulRelated.length > 0,
  })) return null
  const compositionTitle = indicator.id === 'esup-matriculas-presenciais'
    ? 'Participação no total de matrículas'
    : 'Composição presencial e EaD'
  return (
    <section className="educacao-detail-panel education-support-data" aria-labelledby="higher-education-support-title">
      <div className="educacao-explore__heading">
        <span className="eyebrow">Aprofundamento</span>
        <h2 id="higher-education-support-title">Dados de apoio do indicador</h2>
        <p>Recortes e informações complementares disponíveis para este indicador.</p>
      </div>
      {showComposition && viewModel.modalityComposition ? (
        <ModalityComposition composition={viewModel.modalityComposition} title={compositionTitle} />
      ) : null}
      {indicator.id === 'esup-matriculas-ead' && (() => {
        const total = viewModel.indicators.find((item) => item.id === 'esup-matriculas-total')
        return total && areHigherEducationSeriesEqual(indicator, total)
          ? <p className="higher-education-method-note">A série de matrículas EaD coincide com a série total no período utilizável.</p>
          : null
      })()}
      {usefulRelated.map((item) => (
        <article className="higher-education-support-card higher-education-reference-card" key={item.id}>
          <header><span className="eyebrow">Série de referência</span><h3>{publicHigherEducationTitle(item)}</h3><p>{item.description}</p></header>
          <EducationLineChart formatLabel={numberFormatter.format} hideTitle integerTicks scaleType="count" series={item.series.map((point) => ({ ano: point.year, valor: point.value }))} title={publicHigherEducationTitle(item)} />
          {item.id === 'esup-polos-ead' ? <p className="higher-education-table-note">Polos são locais de oferta e não equivalem a instituições com sede no município.</p> : null}
        </article>
      ))}
      <div className="higher-education-support-grid">
        {breakdowns.map((breakdown) => <BreakdownCard breakdown={breakdown} key={breakdown.id} />)}
      </div>
    </section>
  )
}

function interpretationNotes(id: string) {
  if (id === 'esup-polos-ead') return ['Polo EaD é local de oferta e não equivale a uma Instituição de Educação Superior com sede no município.']
  if (id === 'esup-vagas-presenciais') return ['O universo publicado é o de vagas presenciais; não é calculada taxa de ocupação.']
  if (id === 'esup-ingressantes') return ['Os valores representam ingressantes registrados na oferta localizada no município. Não é calculada taxa a partir de vagas ou matrículas, pois os universos podem não ser comparáveis.']
  if (id === 'esup-concluintes') return ['A série apresenta o número de concluintes registrados. Não é calculada taxa de conclusão ou relação automática com ingressantes de anos anteriores.']
  if (id === 'esup-docentes') return ['A cobertura é restrita a docentes vinculados a registros de IES-sede no município.']
  return []
}

function ModalityComposition({
  composition,
  title,
}: {
  composition: NonNullable<HigherEducationViewModel['modalityComposition']>
  title: string
}) {
  const rows = [
    { category: 'Presencial', value: composition.presential, share: composition.presentialShare },
    { category: 'EaD', value: composition.distance, share: composition.distanceShare },
  ]
  const dominant = rows.find((row) => row.share === 100)
  return (
    <article className="higher-education-support-card higher-education-composition-card">
      <header><span className="eyebrow">Modalidade · {composition.year}</span><h3>{title}</h3><p>Participação no total de matrículas com ano compatível.</p></header>
      <div className="higher-education-composition-bar" aria-label={`Composição das matrículas em ${composition.year}`}>
        {rows.filter((row) => row.share > 0).map((row) => (
          <span
            className={`higher-education-composition-bar__segment higher-education-composition-bar__segment--${row.category === 'EaD' ? 'ead' : 'presential'}`}
            key={row.category}
            style={{ width: `${row.share}%` }}
            title={`${row.category}: ${percentFormatter.format(row.share)}%`}
          />
        ))}
      </div>
      <div className="higher-education-composition-legend" aria-label="Legenda da composição">
        {rows.map((row) => (
          <span key={row.category}>
            <i className={`higher-education-composition-legend__swatch higher-education-composition-legend__swatch--${row.category === 'EaD' ? 'ead' : 'presential'}`} aria-hidden="true" />
            {row.category}: {percentFormatter.format(row.share)}%
          </span>
        ))}
      </div>
      {dominant ? <p className="higher-education-composition-reading"><strong>{dominant.category}</strong> representa 100,0% das matrículas no ano.</p> : null}
      <EducationTable
        caption={`Composição presencial e EaD, ${composition.year}`}
        className="higher-education-simple-table"
        columns={[
          { key: 'category', label: 'Modalidade', rowHeader: true },
          { key: 'value', label: 'Matrículas', numeric: true, format: formatValue },
          { key: 'share', label: 'Participação', numeric: true, format: (value: number) => `${percentFormatter.format(value)}%` },
        ]}
        rows={rows}
      />
    </article>
  )
}

function InstitutionalComposition({ viewModel }: { viewModel: HigherEducationViewModel }) {
  const breakdowns = viewModel.breakdowns.filter((item) => item.year != null)
  if (!breakdowns.length) return null
  const group = viewModel.groups.find((item) => item.id === 'composition')
  return (
    <section className="education-indicator-group higher-education-composition-section" aria-labelledby="higher-education-composition-title">
      <div className="education-indicator-group__heading"><div>{group?.question ? <span className="eyebrow">{group.title}</span> : null}<h2 id="higher-education-composition-title">{group?.question ? <QuestionHeading text={group.question} /> : (group?.title ?? 'Composição institucional')}</h2></div></div>
      <p className="education-indicator-group__description">Síntese do último ano utilizável próprio de cada decomposição.</p>
      <div className="higher-education-support-grid">{breakdowns.map((item) => <BreakdownCard breakdown={item} compact key={item.id} />)}</div>
    </section>
  )
}

function BreakdownCard({ breakdown, compact = false }: { breakdown: HigherEducationBreakdownViewModel; compact?: boolean }) {
  const presentation = analyzeHigherEducationBreakdown(breakdown)
  const rows = presentation.tableCategories.map((category) => ({
    category: category.label,
    value: category.value,
    share: category.share,
  }))
  if (!rows.length) return null
  const shownRows = rows
  return (
    <article className="higher-education-support-card">
      <header><span className="eyebrow">Composição · {breakdown.year}</span><h3>{breakdown.title}</h3><p>{breakdown.description}</p></header>
      {!compact && presentation.kind === 'bars' ? (
        <EducationBarChart data={presentation.chartRows} formatLabel={numberFormatter.format} preserveOrder size="large" title={breakdown.title} />
      ) : null}
      {!compact && presentation.kind === 'single_category' && presentation.singleCategory ? (
        <div className="higher-education-single-category" role="note">
          <div aria-hidden="true"><span /></div>
          <p><strong>{presentation.singleCategory.label}</strong> · {formatValue(presentation.singleCategory.value)} {breakdown.id.startsWith('enrollment_') ? 'matrículas' : ''} · 100,0%</p>
        </div>
      ) : null}
      {!compact && presentation.kind === 'all_zero' ? (
        <div className="higher-education-analytical-state" role="note">
          <span>Composição registrada em zero</span>
          <strong>0</strong>
          <p>Todas as categorias utilizáveis apresentam valor zero.</p>
        </div>
      ) : null}
      <EducationTable
        caption={`${breakdown.title}, ${breakdown.year}`}
        className="higher-education-simple-table"
        columns={[
          { key: 'category', label: 'Categoria', rowHeader: true },
          { key: 'value', label: 'Valor', numeric: true, format: formatValue },
          ...(shownRows.some((row) => row.share != null) ? [{ key: 'share', label: 'Participação', numeric: true, format: (value: number) => `${percentFormatter.format(value)}%` }] : []),
        ]}
        rows={shownRows}
      />
      {!breakdown.exhaustive ? <p className="higher-education-table-note">Decomposição não exaustiva; participações não foram normalizadas.</p> : null}
    </article>
  )
}

function SourceAndReading() {
  return (
    <section className="page-card higher-education-sources" aria-labelledby="higher-education-reading-title">
      <div className="higher-education-methodology">
        <span className="eyebrow">Orientação de leitura</span>
        <h3 id="higher-education-reading-title">Como ler estes dados</h3>
        <ul>
          <li>Os dados se referem à localização da oferta registrada no município.</li>
          <li>As matrículas não representam necessariamente residentes do município.</li>
          <li>IES-sede e polos EaD são estruturas diferentes.</li>
          <li>Ausência de informação não representa zero.</li>
        </ul>
        <p>Os dados integrados referem-se à graduação. Informações de pós-graduação ainda não integram esta página.</p>
      </div>
      <footer className="higher-education-consolidated-source">
        <span>Fonte</span>
        <strong>Censo da Educação Superior — INEP</strong>
        <p>Dados municipais publicados para o período de 2018 a 2024.</p>
      </footer>
    </section>
  )
}

function IndicatorMethodology({ indicator }: { indicator: HigherEducationIndicatorViewModel }) {
  const notes = interpretationNotes(indicator.id)
  if (!notes.length) return null
  return (
    <section className="higher-education-detail-methodology" aria-labelledby="higher-education-detail-methodology-title">
      <span className="eyebrow">Orientação de leitura</span>
      <h2 id="higher-education-detail-methodology-title">Como interpretar este indicador</h2>
      {notes.map((note) => <p key={note}>{note}</p>)}
    </section>
  )
}

function variationDetail(indicator: HigherEducationIndicatorViewModel) {
  if (!indicator.firstPoint || !indicator.latestPoint || indicator.absoluteVariation == null) {
    return 'Série insuficiente para comparação'
  }
  if (Math.abs(indicator.percentVariation ?? 0) >= 500) {
    return `${formatValue(indicator.firstPoint.value)} para ${formatValue(indicator.latestPoint.value)} ${indicator.unit}`
  }
  const prefix = indicator.absoluteVariation > 0 ? '+' : ''
  return `${prefix}${formatValue(indicator.absoluteVariation)} ${indicator.unit}`
}

function formatIndicatorList(labels: string[]) {
  if (labels.length < 2) return labels[0] ?? ''
  return `${labels.slice(0, -1).join(', ')} e ${labels[labels.length - 1]}`
}
