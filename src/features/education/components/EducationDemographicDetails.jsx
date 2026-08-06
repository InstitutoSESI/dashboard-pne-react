import { useState } from 'react'
import { EducationLineChart } from '../../../components/EducationLineChart.jsx'
import { ChartEmptyState, ChartLegend, ChartTooltip } from '../../../components/ChartPrimitives.jsx'
import { useChartViewport } from '../../../hooks/useChartViewport.js'
import { closeChartTooltipOnEscape } from '../../../utils/chartVisuals.js'
import {
  isMissing,
  modLabel,
} from '../../../utils/educationFormatters.js'
import {
  ageRangeCategoryDefinitions,
  ageRangeComparisonRows,
  ageRangeHistorySeries,
  ageRangeOptions,
  buildAgeRangeComparisonChart,
  categoryComparisonRows,
  categoryHistorySeries,
  comparisonYearsForRows,
  comparisonYearsWithRecentTail,
  corRacaLabel,
  corRacaOptions,
  formatYearList,
  modalityOptions,
} from '../educationViewModels'
import { EDUCATION_CATEGORY_COMPARISON_COLORS } from '../educationChartPalette.js'

export function AgeRangeDetail({ item }) {
  const stageOptions = item.stageOptions ?? []
  const defaultStage = stageOptions[0]?.key ?? null
  const [viewMode, setViewMode] = useState('comparison')
  const [selectedStageKey, setSelectedStageKey] = useState(defaultStage ?? '')
  const activeStageKey = stageOptions.some((stage) => stage.key === selectedStageKey)
    ? selectedStageKey
    : defaultStage
  const activeStage = stageOptions.find((stage) => stage.key === activeStageKey) ?? null
  const activeStageLabel = activeStage?.label ?? item.stageLabel
  const scopedRows = activeStageKey
    ? item.rows.filter((row) => row[activeStage?.field ?? 'etapa_ensino'] === activeStageKey)
    : item.rows
  const faixaOptions = ageRangeOptions(scopedRows)
  const [selectedFaixa, setSelectedFaixa] = useState('')
  const activeFaixa = faixaOptions.includes(selectedFaixa) ? selectedFaixa : faixaOptions[0]
  const comparisonYears = comparisonYearsWithRecentTail(scopedRows)
  const comparisonRows = ageRangeComparisonRows(scopedRows, comparisonYears, faixaOptions)
  const ageCategories = ageRangeCategoryDefinitions(faixaOptions)
  const historySeries = ageRangeHistorySeries(scopedRows, activeFaixa)
  const period = historySeries.length
    ? `${historySeries[0].ano}-${historySeries[historySeries.length - 1].ano}`
    : ''
  const comparisonTitlePrefix = item.comparisonTitlePrefix ?? 'Matrículas por faixa etária'
  const historyStageLabel = item.historyStageLabel ?? activeStageLabel
  const comparisonTitle = `${comparisonTitlePrefix} — ${activeStageLabel}`
  const historyTitle = period
    ? `Histórico — ${historyStageLabel} — ${activeFaixa} — ${period}`
    : `Histórico — ${historyStageLabel} — ${activeFaixa}`

  if (!comparisonRows.length || !ageCategories.length) {
    return <div className="education-chart-empty"><p>Não há dados suficientes para exibir o gráfico.</p></div>
  }

  return (
    <div className="educacao-age-detail">
      <div className="educacao-age-detail__controls">
        <label className="educacao-age-detail__control">
          <span>Visualização</span>
          <select value={viewMode} onChange={(event) => setViewMode(event.target.value)}>
            <option value="comparison">Comparação por ano</option>
            <option value="history">Histórico de uma faixa</option>
          </select>
        </label>
        {stageOptions.length ? (
          <label className="educacao-age-detail__control">
            <span>Etapa</span>
            <select value={activeStageKey ?? ''} onChange={(event) => setSelectedStageKey(event.target.value)}>
              {stageOptions.map((stage) => (

                <option key={stage.key} value={stage.key}>{stage.label}</option>
              ))}
            </select>
          </label>
        ) : null}
        {viewMode === 'history' ? (
          <label className="educacao-age-detail__control">
            <span>Faixa etária</span>
            <select value={activeFaixa ?? ''} onChange={(event) => setSelectedFaixa(event.target.value)}>
              {faixaOptions.map((faixa) => (
                <option key={faixa} value={faixa}>{faixa}</option>
              ))}
            </select>
          </label>
        ) : null}
      </div>

      {viewMode === 'comparison' ? (
        <AgeRangeComparisonChart
          categories={ageCategories}
          data={comparisonRows}
          formatLabel={item.formatLabel}
          title={comparisonTitle}
          years={comparisonYears}
        />
      ) : (
        <EducationLineChart
          color={item.historyColor}
          formatLabel={item.formatLabel}
          scaleType="count"
          series={historySeries}
          showPointLabels
          title={historyTitle}
        />
      )}
    </div>
  )
}

function AgeRangeComparisonChart({ categories, data, years, title, formatLabel }) {
  const [activeBar, setActiveBar] = useState(null)
  const { containerRef, width: chartWidth } = useChartViewport(1000)
  const chartHeight = chartWidth < 420 ? 280 : chartWidth < 900 ? 300 : 320
  const chart = buildAgeRangeComparisonChart(data, categories, years, formatLabel, chartWidth, chartHeight)

  if (!chart || !chart.rows.length || !chart.categories.length) {
    return <ChartEmptyState />
  }

  return (
    <div className="education-chart education-age-comparison-chart">
      <h4 className="education-chart__title">{title}</h4>
      {chart.categories.length > 1 ? (
        <ChartLegend className="education-stacked-legend" items={chart.categories} />
      ) : null}
      <div className="education-chart__canvas" ref={containerRef}>
        <svg viewBox={`0 0 ${chart.width} ${chart.height}`} role="img" aria-label={title}>
          <g className="chart-grid">
            {chart.yTicks.map((tick, i) => (
              <g key={`y-${i}`}>
                <line x1={chart.padding.left} x2={chart.width - chart.padding.right} y1={tick.y} y2={tick.y} stroke="var(--chart-grid)" strokeWidth="1" />
                <text x={chart.padding.left - 10} y={tick.y + 4} textAnchor="end" className="chart-axis-label">{tick.label}</text>
              </g>
            ))}
          </g>
          <line x1={chart.padding.left} x2={chart.width - chart.padding.right} y1={chart.height - chart.padding.bottom} y2={chart.height - chart.padding.bottom} stroke="var(--chart-axis)" strokeWidth="1" />
          <line x1={chart.padding.left} x2={chart.padding.left} y1={chart.padding.top} y2={chart.height - chart.padding.bottom} stroke="var(--chart-axis)" strokeWidth="1" />
          {chart.rows.map((row) => (
            <g key={row.year}>
              {row.bars.map((bar) => (
                <g key={`${row.year}-${bar.key}`}>
                  {!isMissing(bar.value) ? (
                    <>
                      <rect
                        aria-label={`${bar.category}, ${bar.year}: ${bar.label}`}
                        className="chart-mark"
                        x={bar.x}
                        y={bar.y}
                        width={bar.width}
                        height={bar.height}
                        fill={bar.color}
                        fillOpacity={activeBar?.key === bar.key && activeBar?.year === bar.year ? '1' : '0.86'}
                        onBlur={() => setActiveBar(null)}
                        onFocus={() => setActiveBar(bar)}
                        onKeyDown={(event) => closeChartTooltipOnEscape(event, () => setActiveBar(null))}
                        onMouseEnter={() => setActiveBar(bar)}
                        onMouseLeave={() => setActiveBar(null)}
                        rx="3"
                        tabIndex="0"
                      >
                        <title>{`${bar.category}, ${bar.year}: ${bar.label}`}</title>
                      </rect>
                      <text
                        x={bar.labelX}
                        y={bar.labelY}
                        textAnchor="middle"
                        className="chart-bar-value"
                      >
                        {bar.label}
                      </text>
                    </>
                  ) : null}
                </g>
              ))}
              <text
                x={row.x + row.width / 2}
                y={chart.height - chart.padding.bottom + 24}
                textAnchor="middle"
                className="chart-x-label"
              >
                {row.year}
              </text>
            </g>
          ))}
        </svg>
        {activeBar ? (
          <ChartTooltip
            className="education-chart__tooltip education-chart__tooltip--bar"
            label={activeBar.year}
            series={activeBar.category}
            value={activeBar.label}
            style={{
              left: `${Math.min(90, Math.max(10, ((activeBar.x + activeBar.width / 2) / chart.width) * 100))}%`,
              top: `${Math.min(82, Math.max(12, (activeBar.y / chart.height) * 100))}%`,
              transform: activeBar.y < chart.padding.top + 46
                ? 'translate(-50%, 12px)'
                : 'translate(-50%, calc(-100% - 12px))',
            }}
          />
        ) : null}
      </div>
    </div>
  )
}

export function ModalityDetail({ item }) {
  const modalidadeOptions = modalityOptions(item.rows)
  const [viewMode, setViewMode] = useState('comparison')
  const [selectedModalidade, setSelectedModalidade] = useState('')
  const activeModalidade = modalidadeOptions.some((option) => option.key === selectedModalidade)
    ? selectedModalidade
    : modalidadeOptions[0]?.key
  const comparisonYears = comparisonYearsForRows(item.rows)
  const comparisonRows = categoryComparisonRows(item.rows, comparisonYears, modalidadeOptions, 'modalidade')
  const categories = modalidadeOptions.map((option, index) => ({
    key: option.key,
    label: option.label,
    color: EDUCATION_CATEGORY_COMPARISON_COLORS[index % EDUCATION_CATEGORY_COMPARISON_COLORS.length],
  }))
  const historySeries = categoryHistorySeries(item.rows, activeModalidade, 'modalidade')
  const period = historySeries.length
    ? `${historySeries[0].ano}-${historySeries[historySeries.length - 1].ano}`
    : ''
  const comparisonTitle = comparisonYears.length
    ? `Matrículas por modalidade — ${formatYearList(comparisonYears)}`
    : 'Matrículas por modalidade — comparação entre anos'
  const historyTitle = period
    ? `Histórico — ${modLabel(activeModalidade)} — ${period}`
    : `Histórico — ${modLabel(activeModalidade)}`

  if (!comparisonRows.length || !categories.length) {
    return <div className="education-chart-empty"><p>Não há dados suficientes para exibir o gráfico.</p></div>
  }

  return (
    <div className="educacao-age-detail">
      <div className="educacao-age-detail__controls">
        <label className="educacao-age-detail__control">
          <span>Visualização</span>
          <select value={viewMode} onChange={(event) => setViewMode(event.target.value)}>
            <option value="comparison">Comparação por ano</option>
            <option value="history">Histórico de uma modalidade</option>
          </select>
        </label>
        {viewMode === 'history' ? (
          <label className="educacao-age-detail__control">
            <span>Modalidade</span>
            <select value={activeModalidade ?? ''} onChange={(event) => setSelectedModalidade(event.target.value)}>
              {modalidadeOptions.map((option) => (
                <option key={option.key} value={option.key}>{option.label}</option>
              ))}
            </select>
          </label>
        ) : null}
      </div>

      {viewMode === 'comparison' ? (
        <AgeRangeComparisonChart
          categories={categories}
          data={comparisonRows}
          formatLabel={item.formatLabel}
          title={comparisonTitle}
          years={comparisonYears}
        />
      ) : (
        <EducationLineChart
          color={item.historyColor}
          formatLabel={item.formatLabel}
          scaleType="count"
          series={historySeries}
          showPointLabels
          title={historyTitle}
        />
      )}
    </div>
  )
}

export function ColorRaceDetail({ item }) {
  const stageOptions = item.stageOptions ?? []
  const defaultStage = stageOptions[0]?.key ?? null
  const [viewMode, setViewMode] = useState('comparison')
  const [selectedStageKey, setSelectedStageKey] = useState(defaultStage ?? '')
  const activeStageKey = stageOptions.some((stage) => stage.key === selectedStageKey)
    ? selectedStageKey
    : defaultStage
  const activeStage = stageOptions.find((stage) => stage.key === activeStageKey) ?? null
  const activeStageLabel = activeStage?.label ?? item.stageLabel
  const scopedRows = activeStageKey
    ? item.rows.filter((row) => row[activeStage?.field ?? 'etapa_ensino'] === activeStageKey)
    : item.rows
  const corOptions = corRacaOptions(scopedRows)
  const [selectedCorRaca, setSelectedCorRaca] = useState('')
  const activeCorRaca = corOptions.some((option) => option.key === selectedCorRaca)
    ? selectedCorRaca
    : corOptions[0]?.key
  const comparisonYears = comparisonYearsWithRecentTail(scopedRows, { minYear: 2019 })
  const comparisonRows = categoryComparisonRows(scopedRows, comparisonYears, corOptions, 'cor_raca')
  const categories = corOptions.map((option, index) => ({
    key: option.key,
    label: option.label,
    color: EDUCATION_CATEGORY_COMPARISON_COLORS[index % EDUCATION_CATEGORY_COMPARISON_COLORS.length],
  }))
  const historySeries = categoryHistorySeries(scopedRows, activeCorRaca, 'cor_raca')
  const period = historySeries.length
    ? `${historySeries[0].ano}-${historySeries[historySeries.length - 1].ano}`
    : ''
  const comparisonTitlePrefix = item.comparisonTitlePrefix ?? 'Matrículas por cor/raça'
  const historyStageLabel = item.historyStageLabel ?? activeStageLabel
  const comparisonTitle = `${comparisonTitlePrefix} — ${activeStageLabel}`
  const historyTitle = period
    ? `Histórico — ${historyStageLabel} — ${corRacaLabel(activeCorRaca)} — ${period}`
    : `Histórico — ${historyStageLabel} — ${corRacaLabel(activeCorRaca)}`

  if (!comparisonRows.length || !categories.length) {
    return <div className="education-chart-empty"><p>Não há dados suficientes para exibir o gráfico.</p></div>
  }

  return (
    <div className="educacao-age-detail">
      <div className="educacao-age-detail__controls">
        <label className="educacao-age-detail__control">
          <span>Visualização</span>
          <select value={viewMode} onChange={(event) => setViewMode(event.target.value)}>
            <option value="comparison">Comparação por ano</option>
            <option value="history">Histórico de uma cor/raça</option>
          </select>
        </label>
        {stageOptions.length ? (
          <label className="educacao-age-detail__control">
            <span>Etapa</span>
            <select value={activeStageKey ?? ''} onChange={(event) => setSelectedStageKey(event.target.value)}>
              {stageOptions.map((stage) => (
                <option key={stage.key} value={stage.key}>{stage.label}</option>
              ))}
            </select>
          </label>
        ) : null}
        {viewMode === 'history' ? (
          <label className="educacao-age-detail__control">
            <span>Cor/raça</span>
            <select value={activeCorRaca ?? ''} onChange={(event) => setSelectedCorRaca(event.target.value)}>
              {corOptions.map((option) => (
                <option key={option.key} value={option.key}>{option.label}</option>
              ))}
            </select>
          </label>
        ) : null}
      </div>

      {viewMode === 'comparison' ? (
        <AgeRangeComparisonChart
          categories={categories}
          data={comparisonRows}
          formatLabel={item.formatLabel}
          title={comparisonTitle}
          years={comparisonYears}
        />
      ) : (
        <EducationLineChart
          color={item.historyColor}
          formatLabel={item.formatLabel}
          scaleType="count"
          series={historySeries}
          showPointLabels
          title={historyTitle}
        />
      )}
    </div>
  )
}

