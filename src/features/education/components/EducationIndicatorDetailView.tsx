import { useEffect, useMemo, useState } from 'react'
import { IndicatorChartHeader } from '../../../components/IndicatorChartHeader.jsx'
import { EducationLineChart } from '../../../components/EducationLineChart.jsx'
import { ChartEmptyState } from '../../../components/ChartPrimitives.jsx'
import type { SchoolInfrastructureContract } from '../../../data/schoolInfrastructureContract'
import {
  etapaLabel,
  formatNumber,
  formatRatio,
  isMissing,
} from '../../../utils/educationFormatters.js'
import {
  buildTurmasExplore,
  applyEducationIndicatorStageOption,
  calculateVariation,
  filterRenderableExplore,
  safeValueSeries,
} from '../educationViewModels'
import type { EducationIndicatorResult } from '../educationTypes'
import {
  EducationIndicatorDetailShell,
  EducationMetricSummary,
} from './EducationIndicatorDetailShell'
import { EducationIndicatorQuickReading } from './EducationIndicatorQuickReading'
import { IndicatorSegmentedControl } from './EducationIndicatorSegmentedControl'
import { EducationIndicatorBreakdown } from './EducationIndicatorSupportData'
import {
  EducationSourceNotes,
  dataSourceContextForEducation,
} from './EducationSourceNotes'
import {
  InfraDetailPanel,
  SchoolInfrastructureCombinedDetail,
  SchoolInfrastructureIndicatorDetail,
} from './SchoolInfrastructureDetail'

const EM = '\u2014'

interface EducationSeriesPoint {
  ano: number
  valor: number | null
  [property: string]: unknown
}

interface EducationStageOption {
  explore?: unknown[]
  key: string
  label: string
  mainCutLabel?: string
  scaleType?: string
  series?: unknown
  showPointLabels?: boolean
}

interface EducationIndicatorDetailModel extends EducationIndicatorResult {
  chartColor?: string
  currentDisplay?: string
  currentYear?: number | null
  explore?: unknown[]
  formatValue?: (value: unknown) => string
  initialDisplay?: string
  initialYear?: number | null
  mainCutLabel?: string
  quickReading?: string
  scaleType?: string
  schoolInfrastructure?: SchoolInfrastructureContract
  schoolInfrastructureKey?: string
  series?: EducationSeriesPoint[]
  showPointLabels?: boolean
  stageFilterLabel?: string
  stageFilterOptions?: EducationStageOption[]
  statusDetail?: string
  statusLabel?: string
  statusTone?: string
  variationDisplay?: string
  variationRaw?: number | null
  variationTone?: string
}

interface EducationIndicatorDetailViewProps {
  blocos: unknown
  initialStageKey?: string
  indicator: EducationIndicatorDetailModel | null
}

interface TurmasSeries {
  por_etapa?: Record<string, unknown>
  total?: unknown
}

interface TurmasBlock {
  series?: TurmasSeries
  [property: string]: unknown
}

interface TurmasPanoramaPanelProps {
  blocos: unknown
  indicator: EducationIndicatorDetailModel
}

interface TurmasCut {
  cutLabel: string
  formatLabel: typeof formatNumber
  metricKey: string
  stageKey?: string
}

export function EducationIndicatorDetailView({
  indicator,
  blocos,
  initialStageKey = '',
}: EducationIndicatorDetailViewProps) {
  const [selectedStageKey, setSelectedStageKey] = useState(initialStageKey)

  useEffect(() => {
    setSelectedStageKey(initialStageKey)
  }, [indicator?.key, initialStageKey])

  if (!indicator) {
    return (
      <section className="detail-panel empty-panel">
        <p>Selecione um indicador para ver os detalhes.</p>
      </section>
    )
  }

  // Painel proprio para infraestrutura (sem grafico, com cards + tabela)
  if (indicator.key === 'rede-infraestrutura') {
    return <InfraDetailPanel indicator={indicator} blocos={blocos} />
  }

  if (indicator.key === 'infraestrutura-basica' && indicator.schoolInfrastructure) {
    return (
      <SchoolInfrastructureCombinedDetail
        contract={indicator.schoolInfrastructure}
      />
    )
  }

  if (indicator.schoolInfrastructureKey && indicator.schoolInfrastructure) {
    return <SchoolInfrastructureIndicatorDetail indicator={indicator} />
  }

  if (indicator.key.startsWith('turmas-')) {
    return <TurmasPanoramaPanel indicator={indicator} blocos={blocos} />
  }

  const stageOptions: readonly EducationStageOption[] = indicator.stageFilterOptions ?? []
  const selectedStageOption = stageOptions.find((option) => option.key === selectedStageKey) ?? stageOptions[0] ?? null
  const displayIndicator = applyEducationIndicatorStageOption(
    indicator,
    selectedStageOption?.key ?? '',
  )
  const hasMainSeries = (displayIndicator.series?.length ?? 0) >= 2
  const showStageFilter = stageOptions.length > 1
  const stageFilterLabel = indicator.stageFilterLabel ?? 'Etapa exibida'
  return (
    <EducationIndicatorDetailShell
      summary={<EducationMetricSummary
        currentValue={displayIndicator.currentDisplay}
        currentYear={displayIndicator.currentYear}
        initialValue={displayIndicator.initialDisplay}
        initialYear={displayIndicator.initialYear}
        statusLabel={displayIndicator.statusLabel}
        statusDetail={displayIndicator.statusDetail}
        statusTone={displayIndicator.statusTone}
        variation={{ display: displayIndicator.variationDisplay, raw: displayIndicator.variationRaw, tone: displayIndicator.variationTone }}
      />}
      primaryPanel={(
        <div className="indicator-chart-card educacao-main-chart-card">
          <IndicatorChartHeader
            title="Evolução do indicador"
            subtitle={`${displayIndicator.label} · Recorte exibido: ${displayIndicator.mainCutLabel}`}
            hasWideSegmented={showStageFilter}
            summary={null}
          >
            {showStageFilter ? (
              <div className="indicator-stage-select-wrap">
                <label className="educacao-age-detail__control indicator-stage-select">
                  <span>{stageFilterLabel}</span>
                  <select
                    aria-label="Recorte do histórico do indicador"
                    value={selectedStageOption?.key ?? ''}
                    onChange={(event) => setSelectedStageKey(event.target.value)}
                  >
                    {stageOptions.map((option) => (
                      <option key={option.key} value={option.key}>{option.label}</option>
                    ))}
                  </select>
                </label>
              </div>
            ) : null}
          </IndicatorChartHeader>
          {hasMainSeries ? (
            <>
              <EducationLineChart
                color={displayIndicator.chartColor}
                formatLabel={displayIndicator.formatValue}
                scaleType={displayIndicator.scaleType}
                series={displayIndicator.series ?? []}
                showPointLabels={displayIndicator.showPointLabels}
                title={null}
              />
              <EducationSourceNotes context={dataSourceContextForEducation(displayIndicator)} />
            </>
          ) : (
            <ChartEmptyState message="Histórico não disponível." />
          )}
        </div>
      )}
      quickReading={(
        <EducationIndicatorQuickReading
          cutLabel={displayIndicator.mainCutLabel}
          description={displayIndicator.description}
          text={displayIndicator.quickReading}
        />
      )}
    >
      {displayIndicator.explore?.length ? (
        <EducationIndicatorBreakdown indicator={displayIndicator} />
      ) : null}
    </EducationIndicatorDetailShell>
  )
}


function TurmasPanoramaPanel({ indicator, blocos }: TurmasPanoramaPanelProps) {
  const turmas = useMemo<TurmasBlock>(() => {
    if (!isRecord(blocos)) return {}
    return isTurmasBlock(blocos.turmas_docentes) ? blocos.turmas_docentes : {}
  }, [blocos])
  const turmasSeries = useMemo<TurmasSeries>(() => turmas.series ?? {}, [turmas])

  const isTotalMode = indicator.key === 'turmas-total'
  const stageKey = isTotalMode ? null : indicator.key.replace('turmas-', '')

  const METRIC_OPTIONS = [
    { key: 'turmas', label: 'Turmas', formatLabel: formatNumber },
    { key: 'alunos_por_turma', label: 'Média de alunos por turma', formatLabel: formatRatio },
    { key: 'docentes', label: 'Docentes', formatLabel: formatNumber },
    { key: 'alunos_por_docente', label: 'Alunos por docente', formatLabel: formatRatio },
  ]

  const [selectedMetricKey, setSelectedMetricKey] = useState('turmas')

  const activeMetric = METRIC_OPTIONS.find((m) => m.key === selectedMetricKey) ?? METRIC_OPTIONS[0]

  const cutLabel = isTotalMode ? 'Total do município' : etapaLabel(stageKey)

  const metricFormat = selectedMetricKey === 'turmas' || selectedMetricKey === 'docentes' ? formatNumber : formatRatio

  const displaySeries = safeValueSeries(
    isTotalMode ? turmasSeries.total : stageKey ? turmasSeries.por_etapa?.[stageKey] : undefined,
    selectedMetricKey,
  )

  const cut: TurmasCut = { cutLabel, metricKey: selectedMetricKey, formatLabel: metricFormat }
  if (stageKey) cut.stageKey = stageKey

  const displayExplore = filterRenderableExplore(buildTurmasExplore(turmas, cut))

  const lastPoint = displaySeries[displaySeries.length - 1] ?? null
  const firstPoint = displaySeries[0] ?? null
  const currentValue = lastPoint?.valor ?? null
  const initialValue = firstPoint?.valor ?? null
  const currentYear = lastPoint?.ano ?? null
  const variation = calculateVariation(initialValue, currentValue, selectedMetricKey === 'turmas' || selectedMetricKey === 'docentes' ? 'number' : 'ratio')
  const hasMainSeries = displaySeries.length >= 2
  const quickReading = `Em ${currentYear ?? '—'}, o município registra ${!isMissing(currentValue) ? activeMetric.formatLabel(currentValue) : EM} em ${activeMetric.label.toLowerCase()} no recorte ${cutLabel}.`
  return (
    <section className="detail-panel educacao-detail-panel educacao-detail-panel--organized">
      <div className="indicator-control-bar platform-control-bar">
        <div className="indicator-control-bar__copy">
          <span className="indicator-control-bar__label">Métrica analisada</span>
          <span className="indicator-control-bar__hint">Atualiza os valores, o histórico do indicador e o detalhamento.</span>
        </div>
        <IndicatorSegmentedControl
          options={METRIC_OPTIONS}
          selectedKey={selectedMetricKey}
          onSelect={setSelectedMetricKey}
          ariaLabel="Métrica analisada"
        />
      </div>

      <EducationMetricSummary
        currentValue={!isMissing(currentValue) ? activeMetric.formatLabel(currentValue) : EM}
        currentYear={currentYear}
        initialValue={!isMissing(initialValue) ? activeMetric.formatLabel(initialValue) : EM}
        initialYear={firstPoint?.ano}
        variation={variation}
      />

      <div className="education-primary-analysis">
        <div className="indicator-chart-card educacao-main-chart-card">
          <IndicatorChartHeader
            children={null}
            title="Evolução do indicador"
            subtitle={`${activeMetric.label} · Recorte exibido: ${cutLabel}`}
            summary={null}
          />
          {hasMainSeries ? (
            <>
              <EducationLineChart
                color="#16713a"
                formatLabel={activeMetric.formatLabel}
                scaleType={selectedMetricKey === 'turmas' || selectedMetricKey === 'docentes' ? 'count' : 'dynamic'}
                series={displaySeries}
                showPointLabels
                title={null}
              />
              <EducationSourceNotes
                context={dataSourceContextForEducation(indicator, {
                  detailType: selectedMetricKey,
                  title: activeMetric.label,
                })}
              />
            </>
          ) : (
            <ChartEmptyState message="Histórico não disponível." />
          )}
        </div>

        <EducationIndicatorQuickReading
          cutLabel={cutLabel}
          description={indicator.description}
          text={quickReading}
        />
      </div>

      {displayExplore.length ? (
        <EducationIndicatorBreakdown indicator={{ ...indicator, explore: displayExplore }} />
      ) : null}
    </section>
  )
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value)
}

function isTurmasBlock(value: unknown): value is TurmasBlock {
  if (!isRecord(value)) return false
  return value.series === undefined || isRecord(value.series)
}
