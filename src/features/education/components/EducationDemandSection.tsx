import { useEffect, useMemo, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { CategoryTabs } from '../../../components/CategoryTabs.jsx'
import { IndicatorProjectionPanel } from '../../../components/IndicatorProjectionPanel.jsx'
import { getBoundedDomain } from '../../../utils/chartDomain.js'
import type { EducationProjectionViewContract } from '../educationAttendancePresentation'
import { MetricCard } from '../../../components/MetricCard.jsx'
import { QuickReadingHeading } from '../../../components/QuickReadingHeading.jsx'
import { SegmentedControl } from '../../../components/SegmentedControl.jsx'
import {
  projectionAssumptionText,
  toDisplayPercentage,
  toProjectionView,
} from '../educationAttendancePresentation'
import type {
  DisplayPercentage,
  EducationProjectedIndicator,
} from '../educationAttendanceTypes'
import {
  CUT_LABELS,
  getAvailableCuts,
  getAvailableIndicatorTypes,
  getDisplayableAttendanceItems,
  getMetricGridClass,
  getVisibleAttendanceItems,
  TYPE_LABELS,
} from '../educationAttendanceFilters'
import type {
  CutKey,
  DisplayableAttendanceItem,
  IndicatorTypeKey,
} from '../educationAttendanceFilters'
import type { EducationMunicipioData } from '../educationTypes'
import { EducationCompactHeader } from './EducationCompactHeader'
import { EducationSectionBar } from './EducationSectionBar'

interface EducationDemandSectionProps {
  municipioData?: EducationMunicipioData | null
  onBackToIndicators?: () => void
  selectedMunicipio?: string
}

const DISPLAY_TITLES: Partial<Record<EducationProjectedIndicator['indicatorKey'], string>> = {
  basico_6_17: 'Educação básica — 6 a 17 anos',
  obrigatoria_4_17: 'Escolaridade obrigatória — 4 a 17 anos',
  escolar_6_14: 'Atendimento escolar — 6 a 14 anos',
}

/*
 * O eixo era fixo em 0-100, e a serie de pre-escola (88% a 100%) virava um
 * traco colado no topo com tres quartos do grafico vazios. getBoundedDomain
 * usa a area disponivel mas garante um vao minimo de 20 p.p., para nao
 * transformar variacao pequena em escalada. A meta entra no calculo para que
 * a linha de referencia nunca fique fora do grafico.
 */
function resolveDomain(projection: EducationProjectionViewContract) {
  const values = [
    ...(projection.historical_percent ?? []),
    ...(projection.projected_percent ?? []),
    projection.target_percent,
  ].filter((value): value is number => Number.isFinite(value as number))
  return getBoundedDomain(values, 'percent', { allowPercentOverflow: false })
}
const percentFormatter = new Intl.NumberFormat('pt-BR', {
  maximumFractionDigits: 1,
  minimumFractionDigits: 1,
})

export function EducationDemandSection({
  municipioData,
  onBackToIndicators,
  selectedMunicipio = 'Município selecionado',
}: EducationDemandSectionProps) {
  const payload = municipioData?.educacao?.atendimento_cenarios
  const pageTitleRef = useRef<HTMLHeadingElement | null>(null)
  const [selectedType, setSelectedType] = useState<IndicatorTypeKey>('coverage')
  const [selectedCut, setSelectedCut] = useState<CutKey>('all')

  const availableItems = useMemo<DisplayableAttendanceItem[]>(
    () => getDisplayableAttendanceItems(payload),
    [payload],
  )

  const availableTypes = useMemo(
    () => getAvailableIndicatorTypes(availableItems),
    [availableItems],
  )
  const effectiveType = availableTypes.includes(selectedType)
    ? selectedType
    : availableTypes[0]
  const cutOptions = useMemo(
    () => getAvailableCuts(availableItems, effectiveType),
    [availableItems, effectiveType],
  )
  const effectiveCut = cutOptions.includes(selectedCut) ? selectedCut : cutOptions[0]
  const visibleItems = getVisibleAttendanceItems(availableItems, effectiveType, effectiveCut)

  useEffect(() => {
    const frame = window.requestAnimationFrame(() => {
      window.scrollTo({ behavior: 'auto', top: 0 })
      pageTitleRef.current?.focus({ preventScroll: true })
    })
    return () => window.cancelAnimationFrame(frame)
  }, [])

  useEffect(() => {
    if (effectiveType && effectiveType !== selectedType) setSelectedType(effectiveType)
    if (effectiveCut && effectiveCut !== selectedCut) setSelectedCut(effectiveCut)
  }, [effectiveCut, effectiveType, selectedCut, selectedType])

  const typeOptions = availableTypes.map((key) => ({
    count: availableItems.filter((item) => item.type === key).length,
    key,
    label: TYPE_LABELS[key],
  }))
  const filterCutOptions = cutOptions.map((key) => ({
    key,
    label: key === 'all' ? 'Todos' : CUT_LABELS[key],
  }))
  const integralCutDescriptionId = 'education-attendance-integral-cut-description'
  const projectionYears = availableItems
    .map((item) => toProjectionView(item.indicator).projected_end_year)
    .filter((year): year is number => Number.isFinite(year))
  const lastProjectionYear = projectionYears.length ? Math.max(...projectionYears) : null

  return (
    <div className="education-detail-view education-attendance-detail-view education-attendance-page">
      <EducationCompactHeader
        backLink={{ onClick: onBackToIndicators }}
        className="education-attendance-page-header"
        contextItems={[
          { icon: 'municipality', label: 'Município', value: selectedMunicipio },
          { icon: 'scope', label: 'Escopo', value: 'Cobertura e tempo integral' },
          { icon: 'cut', label: 'Faixas etárias', value: 'Recortes combinados' },
          ...(lastProjectionYear ? [{ icon: 'projection' as const, label: 'Cenários', value: `Até ${lastProjectionYear}` }] : []),
        ]}
        description={(
          <span>Histórico dos indicadores e cenários de atendimento até 2036, considerando a evolução das matrículas e da população.</span>
        )}
        headingRef={pageTitleRef}
        title="Cenários de atendimento escolar"
        variant="scenarios"
      />

      {availableItems.length === 0 ? (
        <section className="detail-panel empty-panel education-attendance-empty" aria-labelledby="education-attendance-empty-title">
          <h2 id="education-attendance-empty-title">Não há cenários disponíveis para este município</h2>
          <p>Os dados deste município ainda estão sendo atualizados. Tente novamente mais tarde.</p>
        </section>
      ) : (
        <>
          <EducationSectionBar
            description="Selecione o tipo de indicador e o recorte para consultar as trajetórias disponíveis."
            filters={(
              <div className="education-attendance-filters platform-filter-panel" aria-label="Filtros dos indicadores">
                <div className="education-attendance-filter-group education-attendance-filter-group--type platform-filter-group">
                  <span>Tipo de indicador</span>
                  <CategoryTabs
                    ariaLabel="Tipo de indicador"
                    categories={typeOptions}
                    onSelectCategory={(key: IndicatorTypeKey) => {
                      setSelectedType(key)
                      setSelectedCut('all')
                    }}
                    selectedCategory={effectiveType}
                  />
                </div>
                <div className="education-attendance-filter-group education-attendance-filter-group--cut platform-filter-group">
                  <span id="education-attendance-cut-label">Recorte</span>
                  {effectiveType === 'integral' ? (
                    <div
                      aria-describedby={integralCutDescriptionId}
                      aria-label="Recorte"
                      className="education-attendance-cut-summary"
                      role="group"
                    >
                      <span className="education-attendance-cut-summary__chip">Educação básica</span>
                      <p id={integralCutDescriptionId}>Tempo integral possui trajetória futura apenas no recorte geral da educação básica.</p>
                    </div>
                  ) : (
                    <div className="education-attendance-cut-control">
                      <SegmentedControl
                        ariaLabel="Recorte"
                        className="education-attendance-cut-filter platform-segmented-control platform-segmented-control--scrollable"
                        onSelect={(key: CutKey) => setSelectedCut(key)}
                        optionClassName="education-attendance-cut-filter__option platform-segmented-option"
                        options={filterCutOptions}
                        selectedKey={effectiveCut}
                      />
                      <p aria-hidden="true" className="education-attendance-cut-control__placeholder">&nbsp;</p>
                    </div>
                  )}
                </div>
              </div>
            )}
            id="education-attendance-section-title"
            title="Atendimento por indicador"
            variant="scenarios"
          />

          <div className="education-attendance-indicator-list">
            {visibleItems.map(({ cut, indicator }) => (
              <ProjectedIndicatorSection cut={cut} indicator={indicator} key={indicator.indicatorKey} />
            ))}
          </div>
        </>
      )}

      <Methodology />
    </div>
  )
}

function ProjectedIndicatorSection({ cut, indicator }: {
  cut: DisplayableAttendanceItem['cut']
  indicator: EducationProjectedIndicator
}) {
  const projection = toProjectionView(indicator)
  const finalYear = projection.projected_end_year
  const targetYear = projection.target_year ?? null
  const targetValue = projection.target_percent ?? null
  const distance = projection.distance_to_target_2036 ?? null
  const comparable = targetValue != null && distance != null
  const targetLabel = projection.target_label ?? 'Referência'
  const targetCardLabel = targetYear != null
    ? `${targetLabel} em ${targetYear}`
    : targetLabel
  const cardCount = 2 + (targetValue != null ? 1 : 0) + (comparable ? 1 : 0)
  const displayTitle = DISPLAY_TITLES[indicator.indicatorKey] ?? indicator.title
  const description = indicator.kind === 'age_coverage'
    ? `Relação entre as matrículas registradas no município e a população de referência de ${indicator.ageRange}.`
    : 'Participação da educação básica pública em tempo integral, com trajetória futura para as referências do PNE.'

  return (
    <section
      className="detail-panel educacao-detail-panel educacao-detail-panel--organized education-attendance-detail education-attendance-sequence-item"
      aria-labelledby={`education-attendance-${indicator.indicatorKey}-title`}
    >
      <header className="detail-heading educacao-detail-heading education-attendance-detail__header">
        <div className="detail-heading__copy">
          <h2 id={`education-attendance-${indicator.indicatorKey}-title`}>{displayTitle}</h2>
          <p>{description}</p>
        </div>
        <div className="educacao-detail-heading__badges">
          <span className="indicator-stage-badge">{indicator.kind === 'integral_coverage' ? 'Educação básica' : CUT_LABELS[cut]}</span>
        </div>
      </header>

      <div className={`metric-grid education-metric-summary education-attendance-kpis ${getMetricGridClass(cardCount)}`}>
        <MetricCard
          icon="current"
          label="Valor atual"
          value={<PercentageValue value={toDisplayPercentage(indicator.observed?.rawValue)} />}
          detail={indicator.observed?.year ?? 'Ano indisponível'}
        />
        <MetricCard
          icon="variation"
          label={`Cenário em ${finalYear ?? 'ano indisponível'}`}
          value={<PercentageValue value={toDisplayPercentage(projection.raw_projected_2036)} />}
          detail={indicator.kind === 'integral_coverage' ? 'Trajetória projetada para as referências' : 'Trajetória projetada'}
        />
        {targetValue != null ? (
          <MetricCard
            icon="target"
            label={targetCardLabel}
            value={<PercentageValue value={toDisplayPercentage(targetValue)} />}
            detail={projection.target_kind === 'legal' ? 'Referência normativa' : 'Parâmetro de acompanhamento'}
          />
        ) : null}
        {comparable ? (
          <MetricCard
            icon="distance"
            label={projection.target_kind === 'legal' ? 'Distância para a meta' : 'Distância da referência'}
            value={formatDistance(distance)}
            detail={targetYear != null && targetYear !== finalYear
              ? `Cenário em ${finalYear} versus referência de ${targetYear}`
              : targetYear != null
                ? `Cenário e referência em ${targetYear}`
                : `Cenário em ${finalYear}`}
          />
        ) : null}
      </div>

      {projection.displayWasCapped ? (
        <p className="education-attendance-year-note" role="note">
          Quando o cálculo ultrapassa 100%, o painel apresenta 100% para facilitar a leitura.
        </p>
      ) : null}

      {targetValue != null && targetYear != null && targetYear !== finalYear ? (
        <p className="education-attendance-year-note" role="note">
          A comparação usa o cenário de {finalYear} e a {lowercaseInitial(targetLabel)} prevista para {targetYear}; ela não informa se a referência foi atingida dentro do prazo legal.
        </p>
      ) : null}

      <div className="education-primary-analysis education-attendance-analysis">
        <div className="indicator-chart-card educacao-main-chart-card education-attendance-main-chart">
          <header className="education-attendance-chart-heading">
            <h3>Evolução histórica e cenário projetado</h3>
            <p>A linha contínua mostra os anos já observados; a linha tracejada mostra o cenário até {finalYear}.</p>
          </header>
          <IndicatorProjectionPanel
            chartHeight={300}
            chartLabel={`${displayTitle}. Histórico observado e trajetória projetada até ${finalYear}.`}
            chartMaxYear={Math.max(finalYear ?? 0, targetYear ?? 0) || null}
            compact
            contentLabels={{
              accessibleChartPrefix: 'Gráfico da evolução histórica e da trajetória projetada',
              observedLegend: `Histórico observado até ${indicator.observed?.year ?? 'o último ano disponível'}`,
              projectedLegend: indicator.kind === 'integral_coverage'
                ? `Trajetória de planejamento até ${finalYear}`
                : `Trajetória projetada até ${finalYear}`,
              projectedPoint: 'Cenário projetado',
              variant: 'attendance-focus',
            }}
            contextOnly
            domainOverride={resolveDomain(projection)}
            maxXTicks={7}
            projection={projection}
            showContextAlerts={false}
            showGoalReference={targetValue != null}
            showGoalReferenceLabel={false}
            showSummaryCards={false}
            showTitle={false}
          />
        </div>
        <AttendanceQuickReading indicator={indicator} projection={projection} />
      </div>
    </section>
  )
}

function AttendanceQuickReading({ indicator, projection }: {
  indicator: EducationProjectedIndicator
  projection: ReturnType<typeof toProjectionView>
}) {
  const historical = indicator.historical
    .filter((point) => point.rawValue != null && Number.isFinite(point.rawValue))
    .sort((left, right) => left.year - right.year)
  const first = historical[0]
  const last = historical[historical.length - 1]
  const finalYear = projection.projected_end_year
  const targetYear = projection.target_year ?? null
  const targetValue = projection.target_percent ?? null
  const distance = projection.distance_to_target_2036 ?? null
  const insights = [
    {
      icon: 'trend',
      label: 'Evolução observada',
      text: buildObservedEvolution(first, last),
    },
    {
      icon: 'projection',
      label: indicator.kind === 'integral_coverage' ? 'Trajetória até a referência' : 'Cenário ao final do período',
      text: buildProjectedEvolution(indicator, projection.projected_2036, finalYear),
    },
    {
      icon: 'projection',
      label: 'Como foi projetado',
      text: buildProjectionAssumptions(indicator, projection),
    },
    ...(targetValue != null ? [{
      icon: 'target',
      label: projection.target_label ?? 'Referência',
      text: projection.target_kind === 'legal'
        ? `A referência normativa é ${formatPercentage(targetValue)}${targetYear != null ? ` em ${targetYear}` : ''}.`
        : `O parâmetro de acompanhamento é ${formatPercentage(targetValue)} e não constitui meta legal autônoma.`,
    }] : []),
    ...(targetValue != null && distance != null ? [{
      icon: 'distance',
      label: projection.target_kind === 'legal'
        ? 'Situação em relação à meta'
        : 'Situação em relação à referência',
      text: buildTargetSituation({
        distance,
        finalYear,
        targetKind: projection.target_kind,
        targetYear,
      }),
    }] : []),
  ]

  return (
    <aside className="interpretation-box education-quick-reading education-attendance-reading" aria-label="Leitura rápida">
      <QuickReadingHeading />
      <ul className="education-quick-reading__list">
        {insights.map((insight) => (
          <li key={insight.label}>
            <AttendanceInsightIcon name={insight.icon} />
            <div>
              <span>{insight.label}</span>
              <p>{insight.text}</p>
            </div>
          </li>
        ))}
      </ul>
    </aside>
  )
}

function AttendanceInsightIcon({ name }: { name: string }) {
  const paths: Record<string, ReactNode> = {
    distance: <><path d="M5 18 18 5" /><path d="M6 8v10h10" /><path d="M14 5h4v4" /></>,
    projection: <><path d="M4 18c4-1 5-5 8-7s5-1 8-6" /><path d="M16 5h4v4" /></>,
    target: <><circle cx="12" cy="12" r="8" /><circle cx="12" cy="12" r="3" /></>,
    trend: <><path d="M5 16 10 11l3 3 6-7" /><path d="M15 7h4v4" /></>,
  }

  return (
    <svg aria-hidden="true" className="education-quick-reading__icon" fill="none" viewBox="0 0 24 24">
      {paths[name] ?? paths.projection}
    </svg>
  )
}

function buildObservedEvolution(
  first: EducationProjectedIndicator['historical'][number] | undefined,
  last: EducationProjectedIndicator['historical'][number] | undefined,
) {
  if (!first || !last || first.rawValue == null || last.rawValue == null) {
    return 'O histórico observado ainda não permite comparar dois pontos.'
  }
  if (first.year === last.year) return `O dado observado disponível é de ${last.year}.`
  const firstDisplay = toDisplayPercentage(first.rawValue).displayValue
  const lastDisplay = toDisplayPercentage(last.rawValue).displayValue
  if (firstDisplay == null || lastDisplay == null) return 'O histórico observado ainda não permite comparar dois pontos.'
  const change = lastDisplay - firstDisplay
  if (Math.abs(change) < 0.05) return `O indicador permaneceu estável entre ${first.year} e ${last.year}.`
  return `${change > 0 ? 'Avançou' : 'Recuou'} ${formatPercentage(Math.abs(change), ' p.p.')} entre ${first.year} e ${last.year}.`
}

function buildProjectedEvolution(
  indicator: EducationProjectedIndicator,
  finalValue: number | null,
  finalYear: number | null,
) {
  if (finalValue == null || finalYear == null) return 'Não há ponto final calculável para a trajetória.'
  if (indicator.kind === 'integral_coverage') {
    return `A trajetória de planejamento alcança ${formatPercentage(finalValue)} em ${finalYear}.`
  }
  return `O cenário indica ${formatPercentage(finalValue)} em ${finalYear}.`
}

function buildProjectionAssumptions(
  indicator: EducationProjectedIndicator,
  projection: ReturnType<typeof toProjectionView>,
) {
  return projectionAssumptionText(
    indicator.kind,
    projection.trend?.selectedBasis,
  )
}

function buildTargetSituation({
  distance,
  finalYear,
  targetKind,
  targetYear,
}: {
  distance: number | null
  finalYear: number | null
  targetKind?: EducationProjectionViewContract['target_kind']
  targetYear: number | null
}) {
  if (distance == null || !Number.isFinite(distance)) return 'A comparação direta não está disponível.'
  const reference = targetKind === 'legal' ? 'meta' : 'referência de acompanhamento'
  const yearContext = targetYear != null && targetYear !== finalYear
    ? ` prevista para ${targetYear}`
    : targetYear != null
      ? ` em ${targetYear}`
      : ''
  const timingNote = targetKind === 'legal' && targetYear != null && targetYear !== finalYear
    ? ' Essa comparação não informa se ela foi atingida dentro do prazo legal.'
    : ''
  if (Math.abs(distance) < 0.05) {
    return `Em ${finalYear}, o cenário coincide com a ${reference}${yearContext}.${timingNote}`
  }
  return `Em ${finalYear}, o cenário fica ${formatPercentage(Math.abs(distance), ' p.p.')} ${distance > 0 ? 'acima' : 'abaixo'} da ${reference}${yearContext}.${timingNote}`
}

function formatPercentage(value: number, suffix = '%') {
  return `${percentFormatter.format(value)}${suffix}`
}

function lowercaseInitial(value: string) {
  return value ? `${value[0].toLocaleLowerCase('pt-BR')}${value.slice(1)}` : value
}

function PercentageValue({ value }: { value: DisplayPercentage }) {
  if (value.displayValue == null) return <>Não calculável</>
  return <>{percentFormatter.format(value.displayValue)}%</>
}

function formatDistance(value: number | null) {
  if (value == null || !Number.isFinite(value)) return 'Não calculável'
  return `${value > 0 ? '+' : ''}${percentFormatter.format(value)} p.p.`
}

function Methodology() {
  return (
    <section className="detail-panel education-attendance-methodology" aria-labelledby="education-attendance-methodology-title">
      <header>
        <span className="educacao-explore__eyebrow">Metodologia</span>
        <h2 id="education-attendance-methodology-title">Como os cenários foram estimados</h2>
      </header>
      <div className="education-attendance-methodology__content">
        <section>
          <h3>Cobertura escolar</h3>
          <p>As projeções combinam as matrículas registradas no município com a população estimada para cada faixa etária. Para os anos futuros, consideramos a mudança esperada da população do Rio Grande do Sul até 2036.</p>
          <p>Nos recortes de 6 a 17 e de 4 a 17 anos, o cenário combina o histórico de matrículas do município e do Rio Grande do Sul. No atendimento de 15 a 17 anos, acompanha a evolução das matrículas no estado. Nos demais indicadores, mantém como referência o número mais recente de matrículas.</p>
          <p>Os cenários servem como referência para o planejamento municipal e podem mudar conforme novas matrículas e estimativas populacionais forem divulgadas.</p>
        </section>
        <section>
          <h3>Tempo integral</h3>
          <p>A trajetória parte do valor atual e mostra o avanço necessário para alcançar as referências de 2031 e 2036.</p>
        </section>
        <section className="education-attendance-methodology__sources">
          <h3>Fontes e recorte</h3>
          <p>Dados do Censo Escolar (INEP), das estimativas populacionais do Ministério da Saúde/DATASUS e das projeções populacionais do IBGE, revisão 2024. As matrículas são contadas no município da escola e comparadas com a população residente. Por isso, o cálculo pode passar de 100%; nesses casos, o painel mostra 100% para facilitar a leitura.</p>
        </section>
      </div>
    </section>
  )
}
