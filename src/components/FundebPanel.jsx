import { useEffect, useMemo, useState } from 'react'
import { resolveDetailSequence, useDetailViewNavigation } from '../hooks/useDetailViewNavigation'
import { FUNDEB_INDICATORS, formatFundebCompactValue, formatFundebValue, getLimiteReferencia } from '../data/fundebIndicators'
import { getFinancialIndicatorMetadata } from '../data/financialIndicatorMetadata'
import { DataSourceNote } from './DataSourceNote'
import { DisclosureChevron } from './DisclosureChevron'
import { FinancialIndicatorDisclosures } from './FinancialIndicatorMetadata'
import { MethodNote } from './MethodNote'
import { IndicatorHistoryChart } from '../components/IndicatorHistoryChart'
import {
  FinancialChartFrame,
  FinancialDataRow,
  FinancialDetailHeader,
  FinancialDetailNavigation,
  FinancialKpiCard,
  FinancialKpiGrid,
  FinancialLeadCard,
  FinancialMetricGrid,
  FinancialQuickReading,
  FinancialPrimaryAnalysis,
  FinancialSourcesFooter,
} from './FinancialIndicatorPrimitives'
import {
  isPublishableFinancialIndicator,
  isPublishableFinancialValue,
} from '../utils/financialPresentation'
import { FinancialIcon } from '../features/municipal-finance/FinancialPanoramaComponents'

const FUNDEB_INDICATOR_GROUPS = Object.freeze({
  receitas: new Set([
    'receitas',
    'despesa_total_fundeb',
    'ingresso_recursos_ate_bimestre',
    'pagamentos_efetuados_ate_bimestre',
  ]),
  remuneracao: new Set([
    'despesa_remuneracao_profissionais',
    'despesa_remuneracao_profissionais_ensino_fundamental',
    'despesa_remuneracao_profissionais_ensino_infantil',
    'despesa_remuneracao_profissionais_creche',
    'despesa_remuneracao_profissionais_pre_escola',
    'percentual_minimo_remuneracao_profissionais',
  ]),
  saldos: new Set([
    'disponibilidade_financeira_ano_anterior',
    'disponibilidade_financeira_ate_bimestre',
    'saldo_financeiro_conciliado',
  ]),
})

const FUNDEB_CATALOG_GROUPS = [
  {
    key: 'receitas',
    label: 'Receitas e movimentação',
    description: 'Receita declarada, despesas totais, ingressos e pagamentos registrados no período.',
  },
  {
    key: 'remuneracao',
    label: 'Remuneração',
    description: 'Aplicação dos recursos do FUNDEB na remuneração dos profissionais da educação.',
  },
  {
    key: 'saldos',
    label: 'Saldos financeiros',
    description: 'Disponibilidade financeira, saldos anteriores e conciliação ao fim do período.',
  },
]

function getFundebGroup(indicatorKey) {
  return FUNDEB_CATALOG_GROUPS.find((group) => FUNDEB_INDICATOR_GROUPS[group.key]?.has(indicatorKey))
    ?? FUNDEB_CATALOG_GROUPS[0]
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

function formatCompactDataLabel(value, tipo) {
  if (!Number.isFinite(Number(value))) return ''
  if (tipo === 'percentual') return `${Math.round(Number(value))}%`
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
  if (tipo === 'percentual') {
    return `${signal}${value.toLocaleString('pt-BR', { maximumFractionDigits: 1 })} p.p.`
  }
  return `${signal}${value.toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%`
}

function calcVariation(current, previous, tipo) {
  if (current == null || previous == null) return null
  const cur = Number(current)
  const prev = Number(previous)
  if (!Number.isFinite(cur) || !Number.isFinite(prev)) return null
  if (tipo === 'percentual') return cur - prev
  if (prev === 0) return null
  return ((cur - prev) / Math.abs(prev)) * 100
}

function filterCrechePreEscola(historico, indicatorKey) {
  if (
    indicatorKey === 'despesa_remuneracao_profissionais_creche' ||
    indicatorKey === 'despesa_remuneracao_profissionais_pre_escola'
  ) {
    return historico.filter((item) => Number(item.ano) >= 2021)
  }
  return historico
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
  return filterCrechePreEscola(historico ?? [], indicator.key)
    .filter((entry) => entry.ano != null)
    .map((entry) => ({ ano: entry.ano, valor: entry[indicator.key] ?? null }))
}

function getFundebStatus(indicator, latest) {
  if (latest?.valor === null || latest?.valor === undefined || !Number.isFinite(Number(latest.valor))) {
    return { label: null, tone: 'default' }
  }

  if (indicator.key === 'percentual_minimo_remuneracao_profissionais') {
    const minimum = getLimiteReferencia(latest.ano)
    return Number(latest.valor) >= minimum
      ? { label: 'Acima do mínimo', tone: 'success' }
      : { label: 'Abaixo do mínimo', tone: 'warning' }
  }

  return { label: null, tone: 'default' }
}

function buildFundebHistorySummary(model) {
  if (!model.initialYear || !model.currentYear || model.initialYear === model.currentYear) return ''
  return `Série de ${model.initialYear} a ${model.currentYear}: ${model.initialDisplay} no início e ${model.currentDisplay} no dado mais recente.`
}

function buildFundebQuickReading(model) {
  if (!model.currentYear || model.currentDisplay === '—') return ''
  if (model.raw.key === 'percentual_minimo_remuneracao_profissionais') {
    return model.statusTone === 'success'
      ? `O município alcançou o mínimo de remuneração do FUNDEB em ${model.currentYear}.`
      : `O município ficou abaixo do mínimo de remuneração do FUNDEB em ${model.currentYear}.`
  }
  if (model.variationDisplay === '—') return `Valor informado em ${model.currentYear}.`
  return `Entre ${model.initialYear} e ${model.currentYear}, a variação foi de ${model.variationDisplay}.`
}

function buildFundebIndicatorModel(indicator, historico) {
  const series = buildSeriesForIndicator(historico, indicator)
  const first = firstAvailable(series)
  const latest = latestAvailable(series)
  const variation = calcVariation(latest?.valor, first?.valor, indicator.tipo)
  const status = getFundebStatus(indicator, latest)
  const model = {
    cardDescription: indicator.cardDescription ?? getIndicatorHelpText(indicator),
    description: getIndicatorHelpText(indicator),
    initialDisplay: first ? formatFundebValue(first.valor, indicator.tipo) : '—',
    initialYear: first?.ano ?? null,
    key: indicator.key,
    label: indicator.label,
    groupLabel: getFundebGroup(indicator.key).label,
    moduleLabel: 'FUNDEB',
    currentDisplay: latest ? formatFundebValue(latest.valor, indicator.tipo) : '—',
    currentDisplayCompact: latest ? formatFundebCompactValue(latest.valor, indicator.tipo) : '—',
    currentYear: latest?.ano ?? null,
    sourceLabel: latest?.ano ? `FUNDEB ${latest.ano}` : 'FUNDEB',
    statusLabel: status.label,
    statusTone: status.tone,
    unitLabel: indicator.tipo === 'percentual' ? 'Percentual' : 'Financeiro',
    variationDisplay: variation === null ? '—' : formatVariation(variation, indicator.tipo),
    variationLabel: first?.ano ? `Variação desde ${first.ano}` : 'Variação no período',
    variationTone: variation === null || variation === 0 ? 'muted' : 'info',
    series,
    raw: indicator,
  }

  return {
    ...model,
    historySummary: buildFundebHistorySummary(model),
    quickReading: buildFundebQuickReading(model),
  }
}

function getIndicatorHelpText(indicator) {
  return indicator?.description || 'Acompanhe a evolução anual deste indicador.'
}

function FundebDetailButton({ label = 'Ver detalhe', model, onSelect, registerButton }) {
  return (
    <button
      ref={(node) => registerButton?.(model.key, node)}
      type="button"
      onClick={() => onSelect(model.key)}
    >
      {label}
    </button>
  )
}

function hasSameFundebSnapshot(left, right) {
  if (!left || !right || left.currentYear !== right.currentYear) return false
  const leftValue = Number(latestAvailable(left.series)?.valor)
  const rightValue = Number(latestAvailable(right.series)?.valor)
  return Number.isFinite(leftValue) && Number.isFinite(rightValue) && leftValue === rightValue
}

function FundebSummaryMetric({ icon, label, model }) {
  if (!model) return null
  return (
    <FinancialKpiCard
      icon={<FinancialIcon name={icon} />}
      label={label}
      meta={model.currentYear ? `Período: ${model.currentYear}` : 'Período não informado'}
      value={model.currentDisplay}
    />
  )
}

function FundebPublicMetric({ label, model, onSelect, registerButton }) {
  if (!model) return null
  return (
    <FinancialDataRow
      action={<FundebDetailButton model={model} onSelect={onSelect} registerButton={registerButton} />}
      label={label}
      meta={model.currentYear ? `Período: ${model.currentYear}` : 'Período não informado'}
      value={model.currentDisplay}
    />
  )
}

function FundebLeadMetric({ label, model, onSelect, registerButton }) {
  if (!model) return null
  return (
    <FinancialLeadCard
      action={<FundebDetailButton label="Ver detalhe e evolução" model={model} onSelect={onSelect} registerButton={registerButton} />}
      label={label}
      meta={model.currentYear ? `Período: ${model.currentYear}` : 'Período não informado'}
      value={model.currentDisplay}
    />
  )
}

export function FundebPanel({ municipioData, embedded = false, detailKey = '', onDetailChange }) {
  const rawFundebData = municipioData?.blocos?.fundeb
  const hasFundebData = Boolean(rawFundebData?.historico?.length)
  const fundebData = rawFundebData ?? {}
  const [selectedKey, setSelectedKey] = useState(detailKey || FUNDEB_INDICATORS[0].key)
  const [isDetailOpen, setIsDetailOpen] = useState(Boolean(detailKey))
  const detailNavigation = useDetailViewNavigation({
    activeKey: selectedKey,
    isOpen: isDetailOpen,
  })

  const selectedIndicator = useMemo(
    () => FUNDEB_INDICATORS.find((ind) => ind.key === selectedKey) ?? FUNDEB_INDICATORS[0],
    [selectedKey],
  )

  const { historico } = fundebData
  const historicoVisivel = useMemo(
    () => filterCrechePreEscola(historico ?? [], selectedIndicator?.key),
    [historico, selectedIndicator?.key],
  )
  const series = useMemo(() => {
    if (!selectedIndicator || !historicoVisivel) return []
    return historicoVisivel
      .filter((h) => h.ano != null)
      .map((h) => ({ ano: h.ano, valor: h[selectedIndicator.key] ?? null }))
  }, [selectedIndicator, historicoVisivel])

  const validSeries = useMemo(() => series.filter((s) => isPublishableFinancialValue(s.valor)), [series])

  const chartUnit = selectedIndicator?.tipo === 'percentual' ? 'percent' : 'currency'

  const indicatorModels = useMemo(
    () => FUNDEB_INDICATORS
      .map((indicator) => buildFundebIndicatorModel(indicator, historico ?? []))
      .filter(isPublishableFinancialIndicator),
    [historico],
  )
  const publicModelByKey = new Map(indicatorModels.map((indicator) => [indicator.key, indicator]))
  const selectedIndicatorModel = indicatorModels.find((indicator) => indicator.key === selectedKey) ?? indicatorModels[0] ?? null
  const selectedMetadata = selectedIndicatorModel
    ? getFinancialIndicatorMetadata('fundeb', selectedIndicatorModel.key)
    : null
  const { activeIndex: selectedIndex, previousItem: previousIndicator, nextItem: nextIndicator } = resolveDetailSequence(indicatorModels, selectedIndicatorModel?.key)
  const declaredRevenueModel = publicModelByKey.get('receitas')
  const declaredInflowsModel = publicModelByKey.get('ingresso_recursos_ate_bimestre')
  const totalExpenseModel = publicModelByKey.get('despesa_total_fundeb')
  const remunerationModel = publicModelByKey.get('despesa_remuneracao_profissionais')
  const finalAvailabilityModel = publicModelByKey.get('disponibilidade_financeira_ate_bimestre')
  const reconciledBalanceModel = publicModelByKey.get('saldo_financeiro_conciliado')
  const revenueAndInflowsMatch = hasSameFundebSnapshot(declaredRevenueModel, declaredInflowsModel)
  const availabilityAndBalanceMatch = hasSameFundebSnapshot(finalAvailabilityModel, reconciledBalanceModel)
  const summaryMetrics = [
    { icon: 'fundeb', label: 'Receita do Fundeb declarada', model: declaredRevenueModel },
    revenueAndInflowsMatch
      ? { icon: 'resources', label: 'Despesa do Fundeb com remuneração', model: remunerationModel }
      : { icon: 'trend', label: 'Ingressos do Fundeb declarados no ano', model: declaredInflowsModel },
    { icon: 'payment', label: 'Despesa total declarada do Fundeb', model: totalExpenseModel },
    { icon: 'budget', label: 'Disponibilidade do Fundeb ao final do exercício', model: finalAvailabilityModel },
  ].filter(({ model }) => Boolean(model))

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

  if (!hasFundebData) {
    return (
      <div className={embedded ? 'fundeb-panel-embedded' : 'page-stack fundeb-page'}>
        <div className="fundeb-empty">
          <p>Não há informações financeiras do Fundeb para este município.</p>
        </div>
      </div>
    )
  }

  return (
    <div className={embedded ? 'fundeb-panel-embedded' : 'page-stack fundeb-page'}>
      {!embedded && (
        <section className="page-card fundeb-hero">
          <div>
            <span className="eyebrow">FUNDEB</span>
            <h1>Fundeb: recursos, aplicação e saldos</h1>
            <p>Veja os recursos declarados, como foram utilizados e a disponibilidade financeira do Fundeb no município.</p>
          </div>
        </section>
      )}

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
          <section className="detail-panel educacao-detail-panel financial-detail-panel fundeb-detail">
            <FinancialDetailHeader indicator={selectedIndicatorModel} />
            <FinancialMetricGrid indicator={selectedIndicatorModel} />
            {(selectedKey === 'despesa_remuneracao_profissionais_creche' || selectedKey === 'despesa_remuneracao_profissionais_pre_escola') && (
              <MethodNote className="fundeb-indicator-note"><strong>Nota metodológica:</strong> Série exibida a partir de 2021 para manter comparabilidade com a estrutura do Novo FUNDEB.</MethodNote>
            )}

            <FinancialPrimaryAnalysis>
              {validSeries.length >= 2 ? (
              <FinancialChartFrame
                subtitle={selectedIndicatorModel.description}
                source={(
                  <DataSourceNote
                    className="fundeb-data-source"
                    context={{
                      block: 'fundeb',
                      detailType: 'chart',
                      indicatorKey: selectedIndicator?.key,
                      indicatorName: selectedIndicator?.label,
                    }}
                  />
                )}
              >
                <IndicatorHistoryChart
                    chartType={chartUnit === 'currency' && validSeries.length <= 3 ? 'bar' : 'line'}
                    chartHeight={300}
                    endYear={validSeries[validSeries.length - 1].ano}
                    formatDataLabel={chartUnit === 'currency' ? (v) => formatCompactDataLabel(v, 'financeiro') : (v) => formatCompactDataLabel(v, 'percentual')}
                    formatYAxis={chartUnit === 'currency' ? formatCompactCurrency : undefined}
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
              formatValue={(value) => formatFundebValue(value, selectedIndicator?.tipo)}
              indicator={selectedIndicatorModel}
              metadata={selectedMetadata}
              series={selectedIndicatorModel.series}
              showDataDisclosure={false}
            />
          </section>
        </div>
      ) : (
        <div className="fundeb-public-page">
          {summaryMetrics.length ? (
            <section className="page-card siope-public-summary fundeb-public-summary" aria-labelledby="fundeb-summary-title">
              <div className="siope-public-section-heading">
                <span className="eyebrow">Resumo principal</span>
                <h2 id="fundeb-summary-title">Números mais recentes</h2>
              </div>
              <FinancialKpiGrid>
                {summaryMetrics.map(({ icon, label, model }) => (
                  <FundebSummaryMetric key={model.key} icon={icon} label={label} model={model} />
                ))}
              </FinancialKpiGrid>
            </section>
          ) : null}

          <section className="page-card siope-public-section fundeb-resources" aria-labelledby="fundeb-resources-title">
            <div className="siope-public-section-heading">
              <span className="eyebrow">Recursos do Fundeb</span>
              <h2 id="fundeb-resources-title">Quanto foi declarado como recurso do Fundeb?</h2>
            </div>
            <div className="siope-application__layout fundeb-section-layout">
              <FundebLeadMetric
                label="Recursos do Fundeb declarados"
                model={publicModelByKey.get('receitas')}
                onSelect={handleIndicatorSelect}
                registerButton={detailNavigation.registerCard}
              />
              <div className="siope-application__primary-list">
                <FundebPublicMetric
                  label="Ingressos do Fundeb declarados no ano"
                  model={publicModelByKey.get('ingresso_recursos_ate_bimestre')}
                  onSelect={handleIndicatorSelect}
                  registerButton={detailNavigation.registerCard}
                />
              </div>
            </div>
            {revenueAndInflowsMatch ? (
              <p className="financial-inline-note">A receita declarada e os ingressos coincidem no exercício exibido; os ingressos permanecem como linha de apoio, pois representam conceitos distintos.</p>
            ) : null}
          </section>

          <section className="page-card siope-public-section fundeb-use" aria-labelledby="fundeb-use-title">
            <div className="siope-public-section-heading">
              <span className="eyebrow">Utilização dos recursos</span>
              <h2 id="fundeb-use-title">Como os recursos do Fundeb foram utilizados?</h2>
              <p>Despesa total e pagamentos mostram momentos diferentes da utilização dos recursos e não devem ser somados. A remuneração é uma parcela da despesa do Fundeb.</p>
            </div>
            <div className="siope-application__layout fundeb-section-layout">
              <FundebLeadMetric
                label="Despesa total declarada do Fundeb"
                model={publicModelByKey.get('despesa_total_fundeb')}
                onSelect={handleIndicatorSelect}
                registerButton={detailNavigation.registerCard}
              />
              <div className="siope-application__primary-list">
                <FundebPublicMetric
                  label="Pagamentos realizados com recursos do Fundeb"
                  model={publicModelByKey.get('pagamentos_efetuados_ate_bimestre')}
                  onSelect={handleIndicatorSelect}
                  registerButton={detailNavigation.registerCard}
                />
                <FundebPublicMetric
                  label="Parcela destinada à remuneração"
                  model={publicModelByKey.get('despesa_remuneracao_profissionais')}
                  onSelect={handleIndicatorSelect}
                  registerButton={detailNavigation.registerCard}
                />
              </div>
            </div>
          </section>

          <section className="page-card siope-public-section fundeb-remuneration" aria-labelledby="fundeb-remuneration-title">
            <div className="siope-public-section-heading">
              <span className="eyebrow">Remuneração dos profissionais</span>
              <h2 id="fundeb-remuneration-title">Quanto foi destinado à remuneração?</h2>
            </div>
            <div className="fundeb-remuneration__layout">
              <FundebLeadMetric
                label="Total destinado à remuneração"
                model={publicModelByKey.get('despesa_remuneracao_profissionais')}
                onSelect={handleIndicatorSelect}
                registerButton={detailNavigation.registerCard}
              />
              <div className="fundeb-remuneration__composition" aria-label="Composição da remuneração">
                <FundebPublicMetric
                  label="Ensino fundamental"
                  model={publicModelByKey.get('despesa_remuneracao_profissionais_ensino_fundamental')}
                  onSelect={handleIndicatorSelect}
                  registerButton={detailNavigation.registerCard}
                />
                <div className="fundeb-remuneration__child-group">
                  <FundebPublicMetric
                    label="Educação infantil"
                    model={publicModelByKey.get('despesa_remuneracao_profissionais_ensino_infantil')}
                    onSelect={handleIndicatorSelect}
                    registerButton={detailNavigation.registerCard}
                  />
                  <div className="fundeb-remuneration__details" aria-label="Detalhamento da educação infantil">
                    <FundebPublicMetric
                      label="Creche"
                      model={publicModelByKey.get('despesa_remuneracao_profissionais_creche')}
                      onSelect={handleIndicatorSelect}
                      registerButton={detailNavigation.registerCard}
                    />
                    <FundebPublicMetric
                      label="Pré-escola"
                      model={publicModelByKey.get('despesa_remuneracao_profissionais_pre_escola')}
                      onSelect={handleIndicatorSelect}
                      registerButton={detailNavigation.registerCard}
                    />
                  </div>
                </div>
              </div>
            </div>
            <div className="fundeb-remuneration__rate">
              <FundebPublicMetric
                label="Percentual dos recursos aplicado em remuneração"
                model={publicModelByKey.get('percentual_minimo_remuneracao_profissionais')}
                onSelect={handleIndicatorSelect}
                registerButton={detailNavigation.registerCard}
              />
            </div>
          </section>

          <section className="page-card siope-public-section fundeb-balances" aria-labelledby="fundeb-balances-title">
            <div className="siope-public-section-heading">
              <span className="eyebrow">Disponibilidade e saldos</span>
              <h2 id="fundeb-balances-title">Qual era a disponibilidade financeira?</h2>
              <p>Estes valores mostram disponibilidades e saldos do Fundeb; não representam receita nova.</p>
            </div>
            <div className="fundeb-balances__grid">
              <FundebPublicMetric
                label="Disponibilidade no início do exercício"
                model={publicModelByKey.get('disponibilidade_financeira_ano_anterior')}
                onSelect={handleIndicatorSelect}
                registerButton={detailNavigation.registerCard}
              />
              <FundebPublicMetric
                label="Disponibilidade ao final do exercício"
                model={publicModelByKey.get('disponibilidade_financeira_ate_bimestre')}
                onSelect={handleIndicatorSelect}
                registerButton={detailNavigation.registerCard}
              />
            </div>
            {availabilityAndBalanceMatch ? (
              <details className="platform-support-disclosure fundeb-balance-disclosure">
                <summary className="platform-support-disclosure__summary">
                  <div><h3>Dados usados no cálculo</h3><p>Disponibilidade final e saldo conciliado coincidem no exercício exibido.</p></div>
                  <DisclosureChevron />
                </summary>
                <div className="platform-support-disclosure__body">
                  <FundebPublicMetric
                    label="Saldo conciliado"
                    model={reconciledBalanceModel}
                    onSelect={handleIndicatorSelect}
                    registerButton={detailNavigation.registerCard}
                  />
                </div>
              </details>
            ) : (
              <div className="fundeb-balances__secondary">
                <FundebPublicMetric
                  label="Saldo conciliado"
                  model={reconciledBalanceModel}
                  onSelect={handleIndicatorSelect}
                  registerButton={detailNavigation.registerCard}
                />
              </div>
            )}
          </section>
          <FinancialSourcesFooter
            periods="Os períodos mostrados em cada linha correspondem ao exercício declarado pela fonte."
            source="FNDE/Fundeb e demonstrativos financeiros municipais."
          >
            Receita, ingressos, despesas, pagamentos e disponibilidade são conceitos distintos e não devem ser somados entre si.
          </FinancialSourcesFooter>
        </div>
      )}
    </div>
  )
}
