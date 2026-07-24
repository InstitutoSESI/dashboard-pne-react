import { useEffect, useMemo, useState } from 'react'
import { resolveDetailSequence, useDetailViewNavigation } from '../hooks/useDetailViewNavigation'
import { PNATE_INDICATORS, formatPnateValue } from '../data/pnateIndicators'
import { getFinancialIndicatorMetadata } from '../data/financialIndicatorMetadata'
import { DataSourceNote } from './DataSourceNote'
import { FinancialIndicatorDisclosures } from './FinancialIndicatorMetadata'
import { IndicatorHistoryChart } from '../components/IndicatorHistoryChart'
import {
  FinancialChartFrame,
  FinancialDetailHeader,
  FinancialDetailNavigation,
  FinancialSection,
  FinancialMetricStrip,
  FinancialMetricGrid,
  FinancialQuickReading,
  FinancialPrimaryAnalysis,
  FinancialSourcesFooter,
} from './FinancialIndicatorPrimitives'
import { FinancialIcon } from '../features/municipal-finance/FinancialPanoramaComponents'
import {
  isPublishableFinancialIndicator,
  isPublishableFinancialValue,
} from '../utils/financialPresentation'

const PNATE_INDICATOR_GROUPS = [
  {
    key: 'repasses',
    label: 'Valores do programa',
    description: 'Valores informados, autorizações e parâmetros das redes consideradas.',
    indicators: new Set([
      'repasse_total',
      'repasse_autorizado_apos_desconto',
      'resultado_per_capita',
      'valor_total_municipal',
      'valor_total_estadual',
    ]),
  },
  {
    key: 'atendimento',
    label: 'Estudantes atendidos',
    description: 'Base de estudantes considerada no cálculo do programa, por rede de ensino.',
    indicators: new Set(['total_alunos', 'total_alunos_rede_municipal', 'total_alunos_rede_estadual']),
  },
  {
    key: 'ajustes',
    label: 'Ajustes do repasse',
    description: 'Descontos e saldos desconsiderados na composição do valor autorizado.',
    indicators: new Set(['desconto', 'saldo_desconsiderado']),
  },
]

function getPnateGroup(indicatorKey) {
  return PNATE_INDICATOR_GROUPS.find((group) => group.indicators.has(indicatorKey)) ?? PNATE_INDICATOR_GROUPS[0]
}

function formatCompactCurrency(value) {
  if (!Number.isFinite(Number(value))) return ''
  const num = Number(value)
  const abs = Math.abs(num)
  const sign = num < 0 ? '-' : ''
  if (abs >= 1e9) return `${sign}R$ ${(abs / 1e9).toLocaleString('pt-BR', { maximumFractionDigits: 0 })} bi`
  if (abs >= 1e6) return `${sign}R$ ${(abs / 1e6).toLocaleString('pt-BR', { maximumFractionDigits: 0 })} mi`
  if (abs >= 1e3) return `${sign}R$ ${(abs / 1e3).toLocaleString('pt-BR', { maximumFractionDigits: 0 })} mil`
  return num.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 })
}

function formatCompactNumber(value) {
  if (!Number.isFinite(Number(value))) return ''
  return Number(value).toLocaleString('pt-BR', { maximumFractionDigits: 0 })
}

function formatCompactDataLabel(value, tipo) {
  if (!Number.isFinite(Number(value))) return ''
  if (tipo === 'numero') return formatCompactNumber(value)
  const num = Number(value)
  const abs = Math.abs(num)
  const sign = num < 0 ? '-' : ''
  if (abs >= 1e9) return `${sign}R$ ${(abs / 1e9).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} bi`
  if (abs >= 1e6) return `${sign}R$ ${(abs / 1e6).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} mi`
  if (abs >= 1e3) return `${sign}R$ ${(abs / 1e3).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} mil`
  return num.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 2 })
}

function formatVariation(value, tipo) {
  if (value === null || value === undefined) return '—'
  const signal = value >= 0 ? '+' : ''
  if (tipo === 'numero') {
    return `${signal}${value.toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%`
  }
  return `${signal}${value.toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%`
}

function calcVariation(current, previous) {
  if (current == null || previous == null) return null
  const cur = Number(current)
  const prev = Number(previous)
  if (!Number.isFinite(cur) || !Number.isFinite(prev) || prev === 0) return null
  return ((cur - prev) / Math.abs(prev)) * 100
}

function findUltimoRegistro(historico, ultimoAno) {
  const ano = Number(ultimoAno)
  if (!Number.isFinite(ano)) return null
  const found = historico.find((item) => Number(item.ano) === ano)
  if (found) return found
  return historico
    .filter((item) => Number.isFinite(Number(item.ano)))
    .sort((a, b) => Number(b.ano) - Number(a.ano))[0] ?? null
}

function firstAvailable(series) {
  return [...series]
    .filter((point) => point.valor !== null && point.valor !== undefined && Number.isFinite(Number(point.valor)))
    .sort((a, b) => Number(a.ano) - Number(b.ano))[0] ?? null
}

function latestAvailable(series) {
  return [...series]
    .filter((point) => point.valor !== null && point.valor !== undefined && Number.isFinite(Number(point.valor)))
    .sort((a, b) => Number(b.ano) - Number(a.ano))[0] ?? null
}

function buildSeriesForIndicator(historico, indicator) {
  return (historico ?? [])
    .filter((entry) => entry.ano != null)
    .map((entry) => ({ ano: entry.ano, valor: entry[indicator.key] ?? null }))
}

function buildPnateHistorySummary(model) {
  if (!model.initialYear || !model.currentYear || model.initialYear === model.currentYear) return ''
  return `Série de ${model.initialYear} a ${model.currentYear}: ${model.initialDisplay} no início e ${model.currentDisplay} no dado mais recente.`
}

function buildPnateQuickReading(model) {
  if (!model.currentYear || model.currentDisplay === '—') return ''
  if (model.variationDisplay === '—') return `Não há dois anos com valores disponíveis para calcular a variação.`
  if (model.variation > 0) return `Aumentou ${Math.abs(model.variation).toLocaleString('pt-BR', { maximumFractionDigits: 1 })}% entre ${model.initialYear} e ${model.currentYear}.`
  if (model.variation < 0) return `Reduziu ${Math.abs(model.variation).toLocaleString('pt-BR', { maximumFractionDigits: 1 })}% entre ${model.initialYear} e ${model.currentYear}.`
  return `Permaneceu próximo ao valor de ${model.initialYear}.`
}

function getPnatePublicLabel(key, fallback) {
  const labels = {
    repasse_autorizado_apos_desconto: 'Valor autorizado após desconto',
    total_alunos: 'Estudantes considerados',
  }
  return labels[key] ?? fallback
}

function buildPnateIndicatorModel(indicator, historico) {
  const series = buildSeriesForIndicator(historico, indicator)
  const first = firstAvailable(series)
  const latest = latestAvailable(series)
  const variation = calcVariation(latest?.valor, first?.valor)
  const model = {
    description: indicator.description,
    initialDisplay: first ? formatPnateValue(first.valor, indicator.tipo) : '—',
    initialYear: first?.ano ?? null,
    key: indicator.key,
    label: indicator.label,
    groupLabel: getPnateGroup(indicator.key).label,
    moduleLabel: 'PNATE',
    currentDisplay: latest ? formatPnateValue(latest.valor, indicator.tipo) : '—',
    currentDisplayCompact: latest
      ? indicator.tipo === 'numero'
        ? formatCompactNumber(latest.valor)
        : formatCompactCurrency(latest.valor)
      : '—',
    currentYear: latest?.ano ?? null,
    sourceLabel: latest?.ano ? `PNATE ${latest.ano}` : 'PNATE',
    statusLabel: null,
    statusTone: 'default',
    unitLabel: indicator.tipo === 'numero' ? 'Contagem' : 'Financeiro',
    variationDisplay: variation === null ? '—' : formatVariation(variation, indicator.tipo),
    variationLabel: first?.ano ? `Variação desde ${first.ano}` : 'Variação no período',
    variationTone: 'default',
    variation,
    series,
    raw: indicator,
  }

  return {
    ...model,
    historySummary: buildPnateHistorySummary(model),
    quickReading: buildPnateQuickReading(model),
  }
}

function getCurrentNumericValue(model) {
  const latest = latestAvailable(model?.series ?? [])
  const value = Number(latest?.valor)
  return Number.isFinite(value) ? value : null
}

function hasSamePnateValue(left, right) {
  if (!left || !right || left.currentYear !== right.currentYear) return false
  const leftValue = getCurrentNumericValue(left)
  const rightValue = getCurrentNumericValue(right)
  return Number.isFinite(leftValue) && Number.isFinite(rightValue) && leftValue === rightValue
}

function formatPeriod(year) {
  return year ? `Período: ${year}` : 'Período não informado'
}

function PnateDetailButton({ model, onSelect, registerButton }) {
  if (!model) return null
  return (
    <button
      aria-label={`Ver detalhe de ${model.label}`}
      ref={(node) => registerButton?.(model.key, node)}
      type="button"
      onClick={() => onSelect(model.key)}
    >
      Ver detalhe
    </button>
  )
}

function PnateSummaryMetric({ icon, label, model }) {
  if (!model) return null
  return (
    <article className="pnate-summary-card">
      <span className="pnate-metric-icon" aria-hidden="true"><FinancialIcon name={icon} /></span>
      <span>{label}</span>
      <strong>{model.currentDisplay}</strong>
      <small>{formatPeriod(model.currentYear)}</small>
    </article>
  )
}

function PnateDataRow({ label, model, onSelect, registerButton }) {
  if (!model) return null
  return (
    <article className="pnate-data-row">
      <div>
        <span>{label}</span>
        <strong>{model.currentDisplay}</strong>
        <small>{formatPeriod(model.currentYear)}</small>
      </div>
      <PnateDetailButton model={model} onSelect={onSelect} registerButton={registerButton} />
    </article>
  )
}

function PnateStudentMetric({ icon, label, model, onSelect, registerButton }) {
  if (!model) return null
  return (
    <article className="pnate-student-metric">
      <div className="pnate-student-metric__label">
        <span className="pnate-metric-icon" aria-hidden="true"><FinancialIcon name={icon} /></span>
        <span>{label}</span>
      </div>
      <strong>{model.currentDisplay}</strong>
      <small>{formatPeriod(model.currentYear)}</small>
      <PnateDetailButton model={model} onSelect={onSelect} registerButton={registerButton} />
    </article>
  )
}

function PnateAdjustmentRow({ explanation, model, onSelect, registerButton }) {
  if (!model) return null
  return (
    <article className="pnate-adjustment-row">
      <div>
        <span>{model.label}</span>
        <strong>{model.currentDisplay}</strong>
        <small>{formatPeriod(model.currentYear)}</small>
        <p>{explanation}</p>
      </div>
      <PnateDetailButton model={model} onSelect={onSelect} registerButton={registerButton} />
    </article>
  )
}

export function PnatePanel({ pnateData, detailKey = '', onDetailChange }) {
  const hasPnateData = Boolean(pnateData?.historico?.length)
  const [selectedKey, setSelectedKey] = useState(detailKey || PNATE_INDICATORS[0].key)
  const [isDetailOpen, setIsDetailOpen] = useState(Boolean(detailKey))
  const detailNavigation = useDetailViewNavigation({
    activeKey: selectedKey,
    isOpen: isDetailOpen,
  })

  const selectedIndicator = useMemo(
    () => PNATE_INDICATORS.find((ind) => ind.key === selectedKey) ?? PNATE_INDICATORS[0],
    [selectedKey],
  )

  const { ultimo_ano, historico = [] } = pnateData ?? {}
  const ultimoRegistro = useMemo(
    () => findUltimoRegistro(historico, ultimo_ano),
    [historico, ultimo_ano],
  )

  const series = useMemo(() => {
    if (!selectedIndicator) return []
    return historico
      .filter((h) => h.ano != null)
      .map((h) => ({ ano: h.ano, valor: h[selectedIndicator.key] ?? null }))
  }, [selectedIndicator, historico])

  const validSeries = useMemo(() => series.filter((s) => isPublishableFinancialValue(s.valor)), [series])
  const chartUnit = selectedIndicator?.tipo === 'numero' ? 'count' : 'currency'

  const indicatorModels = useMemo(
    () => PNATE_INDICATORS
      .map((indicator) => buildPnateIndicatorModel(indicator, historico))
      .filter(isPublishableFinancialIndicator),
    [historico],
  )
  const publicModelByKey = useMemo(
    () => new Map(indicatorModels.map((indicator) => [indicator.key, indicator])),
    [indicatorModels],
  )
  const selectedIndicatorModel = indicatorModels.find((indicator) => indicator.key === selectedKey) ?? indicatorModels[0] ?? null
  const selectedMetadata = selectedIndicatorModel
    ? getFinancialIndicatorMetadata('pnate', selectedIndicatorModel.key)
    : null
  const { activeIndex: selectedIndex, previousItem: previousIndicator, nextItem: nextIndicator } = resolveDetailSequence(indicatorModels, selectedIndicatorModel?.key)
  const reportedModel = publicModelByKey.get('repasse_total')
  const authorizedModel = publicModelByKey.get('repasse_autorizado_apos_desconto')
  const perCapitaModel = publicModelByKey.get('resultado_per_capita')
  const totalStudentsModel = publicModelByKey.get('total_alunos')
  const municipalStudentsModel = publicModelByKey.get('total_alunos_rede_municipal')
  const stateStudentsModel = publicModelByKey.get('total_alunos_rede_estadual')
  const discountModel = publicModelByKey.get('desconto')
  const disregardedBalanceModel = publicModelByKey.get('saldo_desconsiderado')
  const municipalAmountModel = publicModelByKey.get('valor_total_municipal')
  const stateAmountModel = publicModelByKey.get('valor_total_estadual')
  const reportedAndAuthorizedMatch = hasSamePnateValue(reportedModel, authorizedModel)
  const reportedAndMunicipalAmountMatch = hasSamePnateValue(reportedModel, municipalAmountModel)
  const summaryModels = [
    reportedModel,
    totalStudentsModel,
    perCapitaModel,
  ].filter(Boolean)
  const hasSummary = summaryModels.length > 0
  const equalProgramValues = reportedAndAuthorizedMatch && reportedAndMunicipalAmountMatch
  const adjustmentModels = [discountModel, disregardedBalanceModel].filter(Boolean)
  const noProgramAdjustments = adjustmentModels.length === 2
    && adjustmentModels.every((model) => getCurrentNumericValue(model) === 0)
  const programLead = reportedModel ?? authorizedModel ?? municipalAmountModel ?? stateAmountModel

  useEffect(() => {
    if (!detailKey) return setIsDetailOpen(false)
    if (indicatorModels.some((indicator) => indicator.key === detailKey)) {
      setSelectedKey(detailKey)
      setIsDetailOpen(true)
    } else if (indicatorModels.length) {
      setIsDetailOpen(false)
      onDetailChange?.('')
    }
  }, [detailKey, indicatorModels, onDetailChange])

  function handleIndicatorSelect(indicatorKey) {
    detailNavigation.prepareDetail(indicatorKey, {
      captureGridPosition: !isDetailOpen,
    })
    setSelectedKey(indicatorKey)
    setIsDetailOpen(true)
    onDetailChange?.(indicatorKey)
  }

  function handleBackToGrid() {
    const returnKey = selectedKey
    setIsDetailOpen(false)
    setSelectedKey('')
    onDetailChange?.('')
    detailNavigation.restoreGrid(returnKey)
  }

  if (!hasPnateData) {
    return (
      <div className="fundeb-panel-embedded">
        <div className="fundeb-empty">
          <p>Não há informações financeiras do PNATE para este município.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="fundeb-panel-embedded pnate-public-page">
      {hasSummary ? (
        <FinancialSection
          className="pnate-summary financial-metric-strip"
          eyebrow="Resumo principal"
          title="Números mais recentes"
          titleId="pnate-summary-title"
        >
          <FinancialMetricStrip className="pnate-summary-grid">
            <PnateSummaryMetric icon="payment" label={getPnatePublicLabel(reportedModel?.key, reportedModel?.label)} model={reportedModel} />
            <PnateSummaryMetric icon="resources" label={getPnatePublicLabel(totalStudentsModel?.key, totalStudentsModel?.label)} model={totalStudentsModel} />
            <PnateSummaryMetric icon="allocation" label={getPnatePublicLabel(perCapitaModel?.key, perCapitaModel?.label)} model={perCapitaModel} />
          </FinancialMetricStrip>
        </FinancialSection>
      ) : null}

      {isDetailOpen && selectedIndicatorModel ? (
        <div className="financial-detail-view education-detail-view" ref={detailNavigation.detailViewRef}>
          <FinancialDetailNavigation
            activeIndex={selectedIndex}
            nextIndicator={nextIndicator}
            onBack={handleBackToGrid}
            onNext={handleIndicatorSelect}
            onPrevious={handleIndicatorSelect}
            previousIndicator={previousIndicator}
            statusLabel={selectedIndicatorModel.statusLabel}
            statusTone={selectedIndicatorModel.statusTone}
            total={indicatorModels.length}
          />
          <section className="detail-panel educacao-detail-panel financial-detail-panel fundeb-detail pnate-detail">
            <FinancialDetailHeader indicator={selectedIndicatorModel} />
            <FinancialMetricGrid indicator={selectedIndicatorModel} />
            <FinancialPrimaryAnalysis>
              {validSeries.length >= 2 ? (
              <FinancialChartFrame
                subtitle={selectedIndicatorModel.description}
                source={(
                  <DataSourceNote
                    className="fundeb-data-source"
                    context={{
                      block: 'pnate',
                      detailType: 'chart',
                      indicatorKey: selectedIndicator?.key,
                      indicatorName: selectedIndicator?.label,
                    }}
                  />
                )}
              >
                  <IndicatorHistoryChart
                    chartType="bar"
                    chartHeight={300}
                    distributeBars
                    endYear={validSeries[validSeries.length - 1].ano}
                    formatDataLabel={(v) => formatCompactDataLabel(v, selectedIndicator.tipo)}
                    formatYAxis={selectedIndicator.tipo === 'numero' ? formatCompactNumber : formatCompactCurrency}
                    item={{ label: selectedIndicator.label }}
                    labelMode="all"
                    missingLabel="—"
                    result={null}
                    series={validSeries}
                    showMetaLine={false}
                    showMissingPoints={false}
                    startYear={validSeries[0].ano}
                    title={selectedIndicator.label}
                    unit={chartUnit}
                    yTickCount={5}
                  />
              </FinancialChartFrame>
              ) : null}
              <FinancialQuickReading
                description={selectedIndicatorModel.description}
                indicator={selectedIndicatorModel}
                metadata={selectedMetadata}
                text={selectedIndicatorModel.quickReading}
              />
            </FinancialPrimaryAnalysis>

            <FinancialIndicatorDisclosures
              formatValue={(value) => formatPnateValue(value, selectedIndicator?.tipo)}
              indicator={selectedIndicatorModel}
              metadata={selectedMetadata}
              series={selectedIndicatorModel.series}
              showDataDisclosure={false}
            />

            {ultimoRegistro?.repasse_autorizado === false && (
              <p className="fundeb-indicator-note">
                <strong>Atenção:</strong> o último registro indica repasse não autorizado para este município.
              </p>
            )}
          </section>
        </div>
      ) : (
        <>
          <section className="page-card pnate-public-section pnate-program-section" aria-labelledby="pnate-program-title">
            <div className="pnate-section-heading">
              <span className="eyebrow">Valor do programa</span>
              <h2 id="pnate-program-title">Quanto foi considerado para o município?</h2>
            </div>
            {programLead ? (
              <div className="pnate-program-layout">
                <article className="pnate-program-lead">
                  <span>{programLead.label}</span>
                  <strong>{programLead.currentDisplay}</strong>
                  <small>{formatPeriod(programLead.currentYear)}</small>
                  <PnateDetailButton model={programLead} onSelect={handleIndicatorSelect} registerButton={detailNavigation.registerCard} />
                </article>
                <div className="pnate-program-rows" aria-label="Outros valores informados pelo programa">
                  <PnateDataRow label="Valor autorizado após desconto" model={authorizedModel?.key === programLead.key ? null : authorizedModel} onSelect={handleIndicatorSelect} registerButton={detailNavigation.registerCard} />
                  <PnateDataRow label="Valor associado à rede municipal" model={municipalAmountModel?.key === programLead.key ? null : municipalAmountModel} onSelect={handleIndicatorSelect} registerButton={detailNavigation.registerCard} />
                  <PnateDataRow label="Valor associado à rede estadual (contexto territorial)" model={stateAmountModel?.key === programLead.key ? null : stateAmountModel} onSelect={handleIndicatorSelect} registerButton={detailNavigation.registerCard} />
                </div>
              </div>
            ) : null}
            {reportedAndAuthorizedMatch ? (
              <p className="pnate-section-note">
                {equalProgramValues
                  ? 'O valor informado, o autorizado e o associado à rede municipal coincidem neste exercício, mas são campos com funções distintas no registro do programa.'
                  : 'O valor informado e o valor autorizado coincidem neste exercício; o autorizado permanece como linha secundária porque tem função própria no registro do programa.'}
              </p>
            ) : null}
          </section>

          <section className="page-card pnate-public-section pnate-students-section" aria-labelledby="pnate-students-title">
            <div className="pnate-section-heading">
              <span className="eyebrow">Estudantes considerados</span>
              <h2 id="pnate-students-title">Quem entrou no cálculo?</h2>
            </div>
            <div className="pnate-students-layout">
              <PnateStudentMetric icon="resources" label="Total de estudantes considerados" model={totalStudentsModel} onSelect={handleIndicatorSelect} registerButton={detailNavigation.registerCard} />
              <PnateStudentMetric icon="fundeb" label="Estudantes da rede municipal" model={municipalStudentsModel} onSelect={handleIndicatorSelect} registerButton={detailNavigation.registerCard} />
              <PnateStudentMetric icon="fundeb" label="Estudantes da rede estadual" model={stateStudentsModel} onSelect={handleIndicatorSelect} registerButton={detailNavigation.registerCard} />
            </div>
            <p className="pnate-section-note">Os estudantes da rede estadual compõem a base territorial do programa e não representam automaticamente despesa executada pelo município.</p>
          </section>

          <section className="page-card pnate-public-section pnate-adjustments-section" aria-labelledby="pnate-adjustments-title">
            <div className="pnate-section-heading">
              <span className="eyebrow">Ajustes do programa</span>
              <h2 id="pnate-adjustments-title">Houve descontos ou saldos desconsiderados?</h2>
            </div>
            {noProgramAdjustments ? (
              <div className="pnate-adjustments-empty">
                <span className="pnate-metric-icon" aria-hidden="true"><FinancialIcon name="budget" /></span>
                <p>Não houve descontos nem saldo desconsiderado no exercício.</p>
              </div>
            ) : adjustmentModels.length ? (
              <div className="pnate-adjustment-list">
                <PnateAdjustmentRow explanation="Desconto registrado no cálculo; reduz o valor considerado na autorização." model={discountModel} onSelect={handleIndicatorSelect} registerButton={detailNavigation.registerCard} />
                <PnateAdjustmentRow explanation="Saldo informado que foi desconsiderado no cálculo do valor autorizado." model={disregardedBalanceModel} onSelect={handleIndicatorSelect} registerButton={detailNavigation.registerCard} />
              </div>
            ) : (
              <div className="pnate-adjustments-empty">
                <span className="pnate-metric-icon" aria-hidden="true"><FinancialIcon name="budget" /></span>
                <p>Não há ajustes informados para o exercício.</p>
              </div>
            )}
          </section>

          <details className="platform-support-disclosure pnate-calculation-disclosure">
            <summary className="platform-support-disclosure__summary">
              <div>
                <h3>Dados usados no cálculo</h3>
                <p>Tabela anual, unidade e regra da leitura exibida. <span>{indicatorModels.length} indicadores</span></p>
              </div>
            </summary>
            <div className="pnate-calculation-disclosure__body">
              <table>
                <thead>
                  <tr>
                    <th scope="col">Indicador</th>
                    <th scope="col">Valor mais recente</th>
                    <th scope="col">Período</th>
                    <th scope="col"><span className="sr-only">Ação</span></th>
                  </tr>
                </thead>
                <tbody>
                  {indicatorModels.map((model) => (
                    <tr key={model.key}>
                      <th scope="row">{model.label}</th>
                      <td data-label="Valor mais recente">{model.currentDisplay}</td>
                      <td data-label="Período">{formatPeriod(model.currentYear)}</td>
                      <td data-label="Ação"><PnateDetailButton model={model} onSelect={handleIndicatorSelect} registerButton={detailNavigation.registerCard} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </details>

          <FinancialSourcesFooter
            periods={`Exercícios exibidos: ${ultimo_ano ? `até ${ultimo_ano}` : 'conforme o registro disponível'}.`}
            source="FNDE/PNATE."
          >
            Os valores informados podem representar previsão, plano de atendimento ou registro anual. A autorização e os estudantes considerados não comprovam, por si só, o recebimento ou a execução. Valores ausentes são omitidos; zeros oficiais permanecem visíveis nos dados usados no cálculo.
          </FinancialSourcesFooter>
        </>
      )}
    </div>
  )
}
