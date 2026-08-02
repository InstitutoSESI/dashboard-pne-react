import { useEffect, useMemo, useState } from 'react'
import { DataSourceNote } from './DataSourceNote'
import { FinancialIndicatorDisclosures } from './FinancialIndicatorMetadata'
import { ContentState } from './ContentState'
import {
  FinancialChartFrame,
  FinancialDetailHeader,
  FinancialDetailNavigation,
  FinancialMetricGrid,
  FinancialQuickReading,
  FinancialPrimaryAnalysis,
  FinancialSourcesFooter,
} from './FinancialIndicatorPrimitives'
import { IndicatorHistoryChart } from './IndicatorHistoryChart'
import {
  getSiopeOfficialGroup,
  buildSiopeExerciseReading,
  buildSiopeMdeAnalysis,
  loadSiopeDashboardData,
  SIOPE_DASHBOARD_YEARS,
  SIOPE_INDICATOR_READING_GUIDES,
} from '../data/siopeIndicators'
import { municipalFinanceLoader } from '../data/municipalFinance'
import { FINANCIAL_PAGE_KEYS } from '../data/financialPageKeys'
import { getFinancialIndicatorMetadata } from '../data/financialIndicatorMetadata'
import { useAsyncData } from '../utils/useAsyncData'
import { isPublishableFinancialIndicator, isPublishableFinancialValue } from '../utils/financialPresentation'
import { resolveDetailSequence, useDetailViewNavigation } from '../hooks/useDetailViewNavigation'

const EM = '\u2014'
const SIOPE_SOURCE = 'SIOPE / FNDE'
const APPLICATION_PRIMARY_KEYS = [
  'aplicacao_mde_percentual',
]
const APPLICATION_SECONDARY_KEYS = [
  'investimento_aluno_infantil_reais',
  'investimento_aluno_fundamental_reais',
  'despesa_professores_aluno_basica_reais',
]
const REMOVED_INDICATOR_KEYS = new Set([
  'receitas_impostos_total_percentual',
  'resultado_financeiro_exercicio_reais',
])
const METHOD_COMPLEMENTARY_KEYS = new Set([
  'despesas_educacao_total_percentual',
])
const SUMMARY_ONLY_KEYS = new Set([
  'valor_aplicado_mde_reais',
  'investimento_aluno_basica_reais',
])
const NO_DETAIL_KEYS = new Set([
  'despesas_educacao_total_percentual',
  'despesa_professores_aluno_basica_reais',
])
const FUNDEB_KEYS = new Set([
  'fundeb_remuneracao_profissionais_percentual',
  'fundeb_nao_aplicado_percentual',
  'fundeb_educacao_infantil_percentual',
  'fundeb_ensino_fundamental_percentual',
  'saldo_financeiro_fundeb_reais',
])
const PUBLIC_LABELS = {
  aplicacao_mde_percentual: 'Aplicação em manutenção e desenvolvimento do ensino',
  valor_aplicado_mde_reais: 'Valor aplicado em MDE — SIOPE',
  despesas_educacao_total_percentual: 'Participação da função Educação nas despesas municipais',
  investimento_aluno_basica_reais: 'Gasto médio por estudante da educação básica',
  investimento_aluno_infantil_reais: 'Gasto médio por estudante da educação infantil',
  investimento_aluno_fundamental_reais: 'Gasto médio por estudante do ensino fundamental',
  despesa_professores_aluno_basica_reais: 'Despesa com professores por estudante da educação básica',
  receitas_impostos_total_percentual: 'Participação dos impostos na receita municipal',
  resultado_financeiro_exercicio_reais: 'Resultado financeiro do exercício',
}

const SIOPE_LEGAL_STATUS_RULES = {
  aplicacao_mde_percentual: {
    limit: 25,
    passLabel: 'Cumpriu mínimo',
    failLabel: 'Não cumpriu o mínimo',
    type: 'min',
  },
  fundeb_remuneracao_profissionais_percentual: {
    limit: 70,
    passLabel: 'Cumpriu mínimo',
    failLabel: 'Abaixo do mínimo',
    type: 'min',
  },
  fundeb_nao_aplicado_percentual: {
    limit: 10,
    passLabel: 'Dentro do limite',
    failLabel: 'Acima do limite',
    type: 'max',
  },
}

function hasNumber(value) {
  return value !== null && value !== undefined && Number.isFinite(Number(value))
}

function formatSiopeValue(value, unidade, compact = false) {
  if (!hasNumber(value)) return EM
  const numeric = Number(value)

  if (unidade === 'percentual') {
    return `${numeric.toLocaleString('pt-BR', {
      minimumFractionDigits: 1,
      maximumFractionDigits: 1,
    })}%`
  }

  if (unidade === 'reais') {
    return numeric.toLocaleString('pt-BR', {
      style: 'currency',
      currency: 'BRL',
      maximumFractionDigits: 0,
    })
  }

  return numeric.toLocaleString('pt-BR', {
    maximumFractionDigits: compact ? 0 : 2,
  })
}

function formatCompactCurrency(value) {
  if (!hasNumber(value)) return ''
  const num = Number(value)
  const abs = Math.abs(num)
  const sign = num < 0 ? '-' : ''
  if (abs >= 1e9) return `${sign}R$ ${(abs / 1e9).toLocaleString('pt-BR', { maximumFractionDigits: 1 })} bi`
  if (abs >= 1e6) return `${sign}R$ ${(abs / 1e6).toLocaleString('pt-BR', { maximumFractionDigits: 1 })} mi`
  if (abs >= 1e3) return `${sign}R$ ${(abs / 1e3).toLocaleString('pt-BR', { maximumFractionDigits: 1 })} mil`
  return formatSiopeValue(num, 'reais', true)
}

function formatCompactDataLabel(value, unidade) {
  if (!hasNumber(value)) return ''
  if (unidade === 'percentual') return `${Math.round(Number(value))}%`
  if (unidade === 'reais') return formatCompactCurrency(value)
  return Number(value).toLocaleString('pt-BR', { maximumFractionDigits: 0 })
}

function getIndicatorUnit(indicator) {
  if (indicator?.unidade === 'percentual') return 'percent'
  if (indicator?.unidade === 'reais') return 'currency'
  return 'count'
}

function getIndicatorTypeLabel(indicator) {
  if (indicator?.unidade === 'percentual') return 'Percentual'
  if (indicator?.unidade === 'reais') return 'Financeiro'
  return 'Número'
}

function getMunicipalityRecord(wide, idMunicipio) {
  const municipios = wide?.municipios ?? {}
  return idMunicipio ? municipios[String(idMunicipio)] ?? null : null
}

function buildGroups(indicators) {
  const groups = new Map()
  indicators.forEach((indicator) => {
    const officialGroup = getSiopeOfficialGroup(indicator.codigo_indicador)
    if (!officialGroup) return
    if (!groups.has(officialGroup.key)) {
      groups.set(officialGroup.key, {
        count: 0,
        items: [],
        key: officialGroup.key,
        label: officialGroup.label,
        order: officialGroup.order,
      })
    }
    const group = groups.get(officialGroup.key)
    group.items.push(indicator)
    group.count += 1
  })
  return Array.from(groups.values()).sort((a, b) => a.order - b.order)
}

function buildIndicatorSeries(municipality, indicator) {
  return SIOPE_DASHBOARD_YEARS.map((year) => {
    const yearData = municipality?.anos?.[String(year)]
    const indicatorData = yearData?.indicadores?.[indicator.slug]
    const value = hasNumber(indicatorData?.valor) ? Number(indicatorData.valor) : null
    const hasValue = hasNumber(value)

    return {
      ano: year,
      hasValue,
      valor: value,
    }
  })
}

function latestAvailable(series) {
  return [...series]
    .filter((point) => hasNumber(point.valor))
    .sort((a, b) => Number(b.ano) - Number(a.ano))[0] ?? null
}

function firstAvailable(series) {
  return [...series]
    .filter((point) => hasNumber(point.valor))
    .sort((a, b) => Number(a.ano) - Number(b.ano))[0] ?? null
}

function formatVariationDisplay(raw, unidade) {
  if (!hasNumber(raw)) return EM
  const numeric = Number(raw)
  const sign = numeric > 0 ? '+' : ''
  if (unidade === 'percentual') {
    return `${sign}${numeric.toLocaleString('pt-BR', { maximumFractionDigits: 1 })} p.p.`
  }
  return `${sign}${numeric.toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%`
}

function calculateSiopeVariation(first, latest, unidade) {
  if (!hasNumber(first?.valor) || !hasNumber(latest?.valor)) {
    return { display: EM, raw: null, tone: 'muted' }
  }

  const diff = Number(latest.valor) - Number(first.valor)
  const raw = unidade === 'percentual'
    ? diff
    : Number(first.valor) === 0
      ? null
      : (diff / Math.abs(Number(first.valor))) * 100

  return {
    display: raw === null ? EM : formatVariationDisplay(raw, unidade),
    raw,
    tone: raw === null ? 'muted' : raw > 0 ? 'success' : raw < 0 ? 'warning' : 'muted',
  }
}

function getLegalStatus(indicator, latest) {
  const rule = SIOPE_LEGAL_STATUS_RULES[indicator?.slug]
  if (!rule || !hasNumber(latest?.valor)) return null

  const value = Number(latest.valor)
  const isCompliant = rule.type === 'min'
    ? value >= rule.limit
    : value <= rule.limit

  return {
    label: isCompliant ? rule.passLabel : rule.failLabel,
    tone: isCompliant ? 'success' : 'warning',
  }
}

function getFinancialStatus(latest, variation, indicator) {
  if (!hasNumber(latest?.valor)) return { label: null, tone: 'default' }
  const legalStatus = getLegalStatus(indicator, latest)
  if (legalStatus) return legalStatus
  return { label: null, tone: variation.raw === null ? 'default' : 'info' }
}

function buildHistorySummary(model) {
  if (!model.initialYear || !model.currentYear || model.initialYear === model.currentYear) return ''
  return `Série de ${model.initialYear} a ${model.currentYear}: ${model.initialDisplay} no início e ${model.currentDisplay} no dado mais recente.`
}

function buildQuickReading(model) {
  if (!model.currentYear || model.currentDisplay === EM) return ''
  if (model.variationDisplay === EM) {
    return `Valor informado em ${model.currentYear}.`
  }
  const variation = model.variationDisplay.replace(/^[+-]/, '')
  if (model.variationRaw > 0) return `Entre ${model.initialYear} e ${model.currentYear}, aumentou ${variation}.`
  if (model.variationRaw < 0) return `Entre ${model.initialYear} e ${model.currentYear}, reduziu ${variation}.`
  return `Entre ${model.initialYear} e ${model.currentYear}, o valor não variou.`
}

function formatPercentagePoints(value, withSign = false) {
  if (!hasNumber(value)) return EM
  const numeric = Number(value)
  const sign = withSign && numeric > 0 ? '+' : ''
  return `${sign}${numeric.toLocaleString('pt-BR', {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  })} p.p.`
}

function buildSiopeIndicatorModel(indicator, municipality, activeGroup) {
  const series = buildIndicatorSeries(municipality, indicator)
  const latest = latestAvailable(series)
  const first = firstAvailable(series)
  const variation = calculateSiopeVariation(first, latest, indicator.unidade)
  const status = getFinancialStatus(latest, variation, indicator)
  const readingGuide = SIOPE_INDICATOR_READING_GUIDES[indicator.slug] ?? {}
  const model = {
    description: indicator.descricao_curta,
    initialDisplay: first ? formatSiopeValue(first.valor, indicator.unidade) : EM,
    initialYear: first?.ano ?? null,
    key: indicator.slug,
    label: PUBLIC_LABELS[indicator.slug] ?? indicator.nome_dashboard,
    moduleLabel: 'Aplicação e execução da educação',
    currentDisplay: latest ? formatSiopeValue(latest.valor, indicator.unidade) : EM,
    currentDisplayCompact: latest ? formatCompactDataLabel(latest.valor, indicator.unidade) : EM,
    currentYear: latest?.ano ?? null,
    sourceLabel: latest?.ano ? `SIOPE/FNDE ${latest.ano}` : 'SIOPE/FNDE',
    statusLabel: status.label,
    statusTone: status.tone,
    unitLabel: getIndicatorTypeLabel(indicator),
    variationDisplay: variation.display,
    variationRaw: variation.raw,
    variationLabel: first?.ano ? `Variação desde ${first.ano}` : 'Variação no período',
    variationTone: variation.tone,
    series: series.map((point) => ({ ano: point.ano, valor: point.valor })),
    raw: indicator,
    readingGuide,
    groupLabel: activeGroup?.label,
  }

  return {
    ...model,
    historySummary: buildHistorySummary(model),
    quickReading: buildQuickReading(model),
  }
}

function SiopeMetricIcon({ name = 'education' }) {
  const paths = {
    application: <><path d="M5 19h14" /><path d="M7 16V9h3v7m2 0V5h3v11m2 0v-4h2v4" /></>,
    education: <><path d="m3 9 9-5 9 5-9 5z" /><path d="M7 12v4c2.7 2 7.3 2 10 0v-4" /></>,
    payment: <><rect x="3" y="6" width="18" height="12" rx="2" /><path d="M3 10h18M7 15h4" /></>,
    students: <><circle cx="8" cy="8" r="3" /><circle cx="17" cy="9" r="2" /><path d="M3 20c.5-4 2.5-6 5-6s4.5 2 5 6m2-5c3 0 5 1.5 6 4" /></>,
    trend: <><path d="M4 18V6m0 12h16" /><path d="m7 14 4-4 3 2 5-6" /></>,
    book: <><path d="M4 5.5A3.5 3.5 0 0 1 7.5 2H12v17H7.5A3.5 3.5 0 0 0 4 22z" /><path d="M20 5.5A3.5 3.5 0 0 0 16.5 2H12v17h4.5A3.5 3.5 0 0 1 20 22z" /></>,
  }
  return (
    <span className="siope-metric-icon" aria-hidden="true">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
        {paths[name] ?? paths.education}
      </svg>
    </span>
  )
}

function PublicMetric({ icon = null, label, model, compact = false }) {
  return (
    <article className={`siope-public-metric${compact ? ' siope-public-metric--compact' : ''}`}>
      {icon ? <SiopeMetricIcon name={icon} /> : null}
      <div>
        <span>{label}</span>
        <strong>{model.currentDisplay}</strong>
        {model.currentYear ? <small>Período: {model.currentYear}</small> : null}
      </div>
    </article>
  )
}

function SummaryMetric({ icon, label, value, year }) {
  return (
    <article className="siope-public-summary__item">
      <div className="siope-public-summary__label">
        <SiopeMetricIcon name={icon} />
        <span>{label}</span>
      </div>
      <strong>{value}</strong>
      {year ? <small>Período: {year}</small> : null}
    </article>
  )
}

function FinancialAmount({ value }) {
  if (!isPublishableFinancialValue(value)) return EM
  return formatSiopeValue(value.value, 'reais')
}

function ExecutionSection({ execution }) {
  if (!execution) return null

  const stages = [
    { key: 'committed', label: 'Valor comprometido no orçamento', value: execution.committed },
    { key: 'liquidated', label: 'Despesa reconhecida', value: execution.liquidated },
    { key: 'paid', label: 'Despesas da função Educação pagas — Siconfi/DCA', value: execution.paid },
  ].filter((stage) => isPublishableFinancialValue(stage.value))
  const rates = [
    { key: 'liquidated', label: 'Do valor comprometido, quanto já foi reconhecido', value: execution.derivedRates.liquidatedToCommittedRate },
    { key: 'paidCommitted', label: 'Do valor comprometido, quanto já foi pago', value: execution.derivedRates.paidToCommittedRate },
    { key: 'paidLiquidated', label: 'Da despesa reconhecida, quanto já foi pago', value: execution.derivedRates.paidToLiquidatedRate },
  ].filter((rate) => hasNumber(rate.value?.value))
  const history = (execution.history ?? []).filter((item) => (
    isPublishableFinancialValue(item.committed)
    && isPublishableFinancialValue(item.liquidated)
    && isPublishableFinancialValue(item.paid)
  ))
  const latestHistory = history.at(-1)
  const firstHistory = history[0]
  const outstanding = latestHistory ? [
    { key: 'nonProcessed', label: 'Empenhadas ainda não liquidadas', value: latestHistory.committedNotLiquidated },
    { key: 'processed', label: 'Liquidadas ainda não pagas', value: latestHistory.liquidatedNotPaid },
  ].filter((item) => isPublishableFinancialValue(item.value)) : []
  const latestPaidRate = latestHistory?.derivedRates?.paidToCommittedRate?.value
  const firstPaidRate = firstHistory?.derivedRates?.paidToCommittedRate?.value
  const statePaidRate = latestHistory?.stateReference?.paidToCommittedRate?.value
  const stateDifference = hasNumber(latestPaidRate) && hasNumber(statePaidRate)
    ? Number(latestPaidRate) - Number(statePaidRate)
    : null

  return (
    <section className="page-card siope-public-section siope-execution" aria-labelledby="siope-execution-title">
      <div className="siope-public-section-heading">
        <span className="eyebrow">Execução das despesas</span>
        <h2 id="siope-execution-title">Quanto das despesas avançou até o pagamento?</h2>
        <p>As etapas mostram momentos da mesma despesa e não devem ser somadas.</p>
      </div>
      <div className="siope-execution__layout">
        <ol className="siope-execution__stages">
          {stages.map((stage, index) => (
            <li key={stage.key}>
              <span>{index + 1}</span>
              <div>
                <small>{stage.label}</small>
                <strong><FinancialAmount value={stage.value} /></strong>
                <b>Período: {stage.value.referenceYear}</b>
              </div>
            </li>
          ))}
        </ol>
        {rates.length ? (
          <aside className="siope-execution__rates" aria-label="Avanço entre as etapas">
            <h3>Avanço entre as etapas</h3>
            <ul>
              {rates.map((rate) => (
                <li key={rate.key}>
                  <strong>{formatSiopeValue(rate.value.value, 'percentual')}</strong>
                  <span>{rate.label}</span>
                </li>
              ))}
            </ul>
          </aside>
        ) : null}
      </div>
      {outstanding.length ? (
        <div className="siope-execution__outstanding">
          <h3>Valores ainda a pagar</h3>
          <dl>
            {outstanding.map((item) => (
              <div key={item.key}>
                <dt>{item.label}</dt>
                <dd><FinancialAmount value={item.value} /></dd>
                <small>Período: {item.value.referenceYear}</small>
              </div>
            ))}
          </dl>
        </div>
      ) : null}
      {history.length > 1 ? (
        <div className="siope-history-block siope-execution-history">
          <div className="siope-history-block__reading">
            <h3>Histórico da execução</h3>
            <p>
              Em {latestHistory.referenceYear}, {formatSiopeValue(latestPaidRate, 'percentual')} do valor empenhado foi pago.
              {hasNumber(firstPaidRate) ? ` A taxa variou ${formatPercentagePoints(Number(latestPaidRate) - Number(firstPaidRate), true)} desde ${firstHistory.referenceYear}.` : ''}
            </p>
            {hasNumber(stateDifference) ? (
              <p>
                {formatPercentagePoints(Math.abs(stateDifference))} {stateDifference >= 0 ? 'acima' : 'abaixo'} da referência RS,
                calculada pela soma dos valores pagos dividida pela soma dos valores empenhados dos 497 municípios.
              </p>
            ) : null}
          </div>
          <div className="siope-execution-history__comparison" aria-label="Comparação da execução por exercício">
            {history.map((item) => {
              const comparisons = [
                { key: 'committed', label: 'Empenhado', value: item.committed, rate: 100 },
                { key: 'liquidated', label: 'Liquidado', value: item.liquidated, rate: item.derivedRates.liquidatedToCommittedRate.value },
                { key: 'paid', label: 'Pago', value: item.paid, rate: item.derivedRates.paidToCommittedRate.value },
              ].filter((comparison) => hasNumber(comparison.rate))
              return (
                <article key={item.referenceYear}>
                  <header>
                    <div><span>Exercício</span><strong>{item.referenceYear}</strong></div>
                    {hasNumber(item.derivedRates.paidToCommittedRate.value) ? (
                      <div className="siope-execution-history__paid-rate">
                        <strong>{formatSiopeValue(item.derivedRates.paidToCommittedRate.value, 'percentual')}</strong>
                        <span>pago sobre empenhado</span>
                      </div>
                    ) : null}
                  </header>
                  <ul>
                    {comparisons.map((comparison) => (
                      <li key={comparison.key}>
                        <div><span>{comparison.label}</span><strong><FinancialAmount value={comparison.value} /></strong></div>
                        <progress
                          aria-label={`${comparison.label} em ${item.referenceYear}: ${formatSiopeValue(comparison.rate, 'percentual')}`}
                          max="100"
                          value={comparison.rate}
                        />
                      </li>
                    ))}
                  </ul>
                </article>
              )
            })}
          </div>
        </div>
      ) : null}
      <details className="platform-support-disclosure siope-method-disclosure siope-method-disclosure--execution">
        <summary className="platform-support-disclosure__summary">
          <div><h3>Conceitos e fórmulas da execução</h3><p>Como interpretar as etapas, pendências e percentuais.</p></div>
        </summary>
        <div className="platform-support-disclosure__body">
          <p>Empenhado, liquidado e pago são etapas da mesma despesa e não devem ser somados.</p>
          <p>Empenhado ainda não liquidado = empenhado − liquidado. Liquidado ainda não pago = liquidado − pago. As taxas dividem a etapa posterior pela etapa anterior; denominador zero não produz resultado.</p>
          <p>Fonte: SICONFI/DCA, função 12 — Educação. Série histórica: {history[0]?.referenceYear}–{history.at(-1)?.referenceYear}.</p>
        </div>
      </details>
    </section>
  )
}

function SiopeEmpty({ children }) {
  return (
    <ContentState kind="empty" className="siope-empty">
      <p>{children}</p>
    </ContentState>
  )
}

export function SiopeIndicatorsPanel({ idMunicipio, detailKey = '', onDetailChange }) {
  const state = useAsyncData(() => loadSiopeDashboardData(), [])
  const financeState = useAsyncData(
    () => (idMunicipio ? municipalFinanceLoader.load(String(idMunicipio)) : null),
    [idMunicipio],
  )
  const [selectedIndicatorKey, setSelectedIndicatorKey] = useState(detailKey)
  const [isDetailOpen, setIsDetailOpen] = useState(Boolean(detailKey))
  const detailNavigation = useDetailViewNavigation({
    activeKey: selectedIndicatorKey,
    isOpen: isDetailOpen,
  })

  const model = useMemo(() => {
    const catalogIndicators = state.data?.catalogo?.indicadores ?? []
    const groups = buildGroups(catalogIndicators)
    const municipality = getMunicipalityRecord(state.data?.wide, idMunicipio)

    return {
      catalogIndicators,
      groups,
      municipality,
    }
  }, [idMunicipio, state.data])

  useEffect(() => {
    if (!detailKey) return setIsDetailOpen(false)
    if (
      !NO_DETAIL_KEYS.has(detailKey)
      && model.groups.some((group) => group.items?.some((indicator) => indicator.slug === detailKey))
    ) {
      setSelectedIndicatorKey(detailKey)
      setIsDetailOpen(true)
    } else if (!state.loading) {
      setIsDetailOpen(false)
      onDetailChange?.('')
    }
  }, [detailKey, model.groups, onDetailChange, state.loading])

  if (!idMunicipio) {
    return <SiopeEmpty>Selecione um município para consultar os dados declarados ao SIOPE/FNDE.</SiopeEmpty>
  }

  if (state.loading || financeState.loading) {
    return <div className="page-stack"><ContentState as="p" kind="loading" className="state-box state-box--loading">Carregando informações de aplicação e execução...</ContentState></div>
  }

  if (state.error) {
    return (
      <div className="page-stack">
        <div className="state-box state-box--error">
          <strong>Erro ao carregar SIOPE/FNDE</strong>
          <span>{state.error}</span>
        </div>
      </div>
    )
  }

  if (!model.municipality) {
    return <SiopeEmpty>Não há informações financeiras do SIOPE/FNDE para este município.</SiopeEmpty>
  }

  const indicatorModels = model.catalogIndicators
    .filter((indicator) => !REMOVED_INDICATOR_KEYS.has(indicator.slug))
    .map((indicator) => {
      const group = model.groups.find((item) => item.items?.some((candidate) => candidate.slug === indicator.slug))
      return buildSiopeIndicatorModel(indicator, model.municipality, group)
    })
    .filter(isPublishableFinancialIndicator)
  const detailIndicatorModels = indicatorModels.filter((indicator) => !NO_DETAIL_KEYS.has(indicator.key))
  const selectedIndicatorModel = detailIndicatorModels.find((indicator) => indicator.key === selectedIndicatorKey) ?? detailIndicatorModels[0]
  const selectedMetadata = selectedIndicatorModel
    ? getFinancialIndicatorMetadata('siope', selectedIndicatorModel.key)
    : null
  const selectedIndicator = selectedIndicatorModel?.raw
  const series = selectedIndicator
    ? buildIndicatorSeries(model.municipality, selectedIndicator)
    : []
  const validSeries = series.filter((point) => hasNumber(point.valor))
  const chartSeries = validSeries.map((point) => ({ ano: point.ano, valor: point.valor }))
  const publicModelByKey = new Map(indicatorModels.map((indicator) => [indicator.key, indicator]))
  const applicationPrimary = APPLICATION_PRIMARY_KEYS.map((key) => publicModelByKey.get(key)).filter(Boolean)
  const applicationSecondary = APPLICATION_SECONDARY_KEYS.map((key) => publicModelByKey.get(key)).filter(Boolean)
  const functionShareModel = publicModelByKey.get('despesas_educacao_total_percentual')
  const catalogIndicators = indicatorModels.filter((indicator) => (
    !FUNDEB_KEYS.has(indicator.key)
    && !APPLICATION_PRIMARY_KEYS.includes(indicator.key)
    && !APPLICATION_SECONDARY_KEYS.includes(indicator.key)
    && !METHOD_COMPLEMENTARY_KEYS.has(indicator.key)
    && !SUMMARY_ONLY_KEYS.has(indicator.key)
  ))
  const execution = financeState.data?.execution?.dcaEducation ?? null
  const paidValue = execution && isPublishableFinancialValue(execution.paid) ? execution.paid : null
  const hasMixedScopeValues = Boolean(publicModelByKey.get('valor_aplicado_mde_reais') && paidValue)
  const mdeAnalysis = buildSiopeMdeAnalysis(model.municipality)
  const exerciseReading = buildSiopeExerciseReading(mdeAnalysis, execution)
  const { activeIndex: selectedIndex, previousItem: previousIndicator, nextItem: nextIndicator } = resolveDetailSequence(detailIndicatorModels, selectedIndicatorModel?.key)

  function handleIndicatorSelect(indicatorKey) {
    detailNavigation.prepareDetail(indicatorKey, {
      captureGridPosition: !isDetailOpen,
    })
    setSelectedIndicatorKey(indicatorKey)
    setIsDetailOpen(true)
    onDetailChange?.(indicatorKey)
  }

  function handleBackToGrid() {
    const returnKey = selectedIndicatorKey
    setIsDetailOpen(false)
    setSelectedIndicatorKey('')
    onDetailChange?.('')
    detailNavigation.restoreGrid(returnKey)
  }

  return (
    <div className="siope-panel">
      {!isDetailOpen ? (
        <>
          <section className="page-card siope-public-summary" aria-labelledby="siope-summary-title">
            <div className="siope-public-section-heading">
              <span className="eyebrow">Resumo principal</span>
              <h2 id="siope-summary-title">Números mais recentes</h2>
            </div>
            <div className="siope-public-summary__grid">
              {publicModelByKey.get('aplicacao_mde_percentual') ? (
                <SummaryMetric
                  icon="application"
                  label={PUBLIC_LABELS.aplicacao_mde_percentual}
                  value={publicModelByKey.get('aplicacao_mde_percentual').currentDisplay}
                  year={publicModelByKey.get('aplicacao_mde_percentual').currentYear}
                />
              ) : null}
              {mdeAnalysis ? (
                <SummaryMetric
                  icon="trend"
                  label="Margem sobre o mínimo constitucional"
                  value={`${formatPercentagePoints(Math.abs(mdeAnalysis.latestMarginFromMinimum))} ${mdeAnalysis.latestMarginFromMinimum >= 0 ? 'acima' : 'abaixo'}`}
                  year={mdeAnalysis.latestYear}
                />
              ) : null}
              {publicModelByKey.get('valor_aplicado_mde_reais') ? (
                <SummaryMetric
                  icon="education"
                  label={PUBLIC_LABELS.valor_aplicado_mde_reais}
                  value={publicModelByKey.get('valor_aplicado_mde_reais').currentDisplay}
                  year={publicModelByKey.get('valor_aplicado_mde_reais').currentYear}
                />
              ) : null}
              {paidValue ? (
                <SummaryMetric icon="payment" label="Despesas da função Educação pagas — Siconfi/DCA" value={<FinancialAmount value={paidValue} />} year={paidValue.referenceYear} />
              ) : null}
              {publicModelByKey.get('investimento_aluno_basica_reais') ? (
                <SummaryMetric
                  icon="students"
                  label={PUBLIC_LABELS.investimento_aluno_basica_reais}
                  value={publicModelByKey.get('investimento_aluno_basica_reais').currentDisplay}
                  year={publicModelByKey.get('investimento_aluno_basica_reais').currentYear}
                />
              ) : null}
            </div>
            {hasMixedScopeValues ? (
              <div className="siope-public-summary__scope-note">
                <span className="siope-info-icon" aria-hidden="true">i</span>
                <p>Os valores do SIOPE e do Siconfi utilizam classificações contábeis diferentes e não representam etapas do mesmo total.</p>
              </div>
            ) : null}
          </section>

          <section className="page-card siope-public-section siope-application" aria-labelledby="siope-application-title">
            <div className="siope-public-section-heading">
              <span className="eyebrow">Aplicação constitucional</span>
              <h2 id="siope-application-title">Aplicação em manutenção e desenvolvimento do ensino</h2>
            </div>
            {applicationPrimary.length ? (
              <div className="siope-application__status-strip">
                <article>
                  <span>Aplicação em MDE</span>
                  <strong>{applicationPrimary[0].currentDisplay}</strong>
                  <small>Período: {applicationPrimary[0].currentYear}</small>
                </article>
                {mdeAnalysis ? (
                  <article>
                    <span>Margem sobre o mínimo</span>
                    <strong>{formatPercentagePoints(Math.abs(mdeAnalysis.latestMarginFromMinimum))} {mdeAnalysis.latestMarginFromMinimum >= 0 ? 'acima' : 'abaixo'}</strong>
                    <small>Mínimo constitucional: 25%</small>
                  </article>
                ) : null}
                {applicationPrimary[0].statusLabel ? (
                  <article>
                    <span>Situação em {applicationPrimary[0].currentYear}</span>
                    <strong className={`siope-application__status siope-application__status--${applicationPrimary[0].statusTone}`}>
                      {applicationPrimary[0].statusLabel}
                    </strong>
                    <button type="button" onClick={() => handleIndicatorSelect(applicationPrimary[0].key)}>Ver detalhe</button>
                  </article>
                ) : null}
              </div>
            ) : null}
            {mdeAnalysis?.series.length > 1 || exerciseReading ? (
              <div className="siope-mde-analysis">
                {mdeAnalysis?.series.length > 1 ? (
                  <div className="siope-mde-history">
                    <div className="siope-history-block__reading">
                      <h3>Histórico da aplicação em MDE</h3>
                      <p>
                        Cumpriu o mínimo constitucional em {mdeAnalysis.compliantYears} dos últimos {mdeAnalysis.series.length} exercícios com dado.
                        {' '}A aplicação variou entre {formatSiopeValue(mdeAnalysis.minimumRate, 'percentual')} e {formatSiopeValue(mdeAnalysis.maximumRate, 'percentual')} no período.
                      </p>
                      <p>
                        Entre {mdeAnalysis.firstYear} e {mdeAnalysis.latestYear}, a variação foi de {formatPercentagePoints(mdeAnalysis.variationFromFirst, true)}.
                      </p>
                    </div>
                    <div className="siope-mde-history__plot" aria-label={`Aplicação em MDE de ${mdeAnalysis.firstYear} a ${mdeAnalysis.latestYear}; referência constitucional de 25 por cento`}>
                      <div className="siope-mde-history__reference"><span>Mínimo constitucional — 25%</span></div>
                      {mdeAnalysis.series.map((point) => (
                        <div className="siope-mde-history__item" key={point.year}>
                          <div className="siope-mde-history__bar-track">
                            <span style={{ height: `${Math.min(100, point.rate / 40 * 100)}%` }} />
                          </div>
                          <strong>{formatSiopeValue(point.rate, 'percentual')}</strong>
                          <small>{point.year}</small>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : null}
                {exerciseReading ? (
                  <aside className="siope-exercise-reading" aria-labelledby="siope-exercise-reading-title">
                    <div className="siope-exercise-reading__title">
                      <SiopeMetricIcon name="trend" />
                      <h3 id="siope-exercise-reading-title">Leitura do exercício</h3>
                    </div>
                    <p>{exerciseReading}</p>
                  </aside>
                ) : null}
              </div>
            ) : null}
            {mdeAnalysis?.series.length > 1 ? (
              <details className="platform-support-disclosure siope-method-disclosure siope-method-disclosure--application">
                <summary className="platform-support-disclosure__summary">
                  <SiopeMetricIcon name="book" />
                  <div><h3>Fonte e método da aplicação constitucional</h3><p>Período, referência e cálculo da margem.</p></div>
                </summary>
                <div className="platform-support-disclosure__body">
                  <div className="siope-method-disclosure__columns">
                    <section>
                      <h4>Fonte e período</h4>
                      <p>Fonte: SIOPE/FNDE, indicador 1.1. Série histórica: {mdeAnalysis.firstYear}–{mdeAnalysis.latestYear}.</p>
                      <p>A linha de referência marca o mínimo constitucional de 25%.</p>
                      {functionShareModel ? (
                        <div className="siope-method-complement">
                          <div className="siope-method-complement__value">
                            <strong>{functionShareModel.currentDisplay}</strong>
                            <small>Período: {functionShareModel.currentYear}</small>
                          </div>
                          <div>
                            <span>{PUBLIC_LABELS.despesas_educacao_total_percentual}</span>
                            <p>Indicador complementar com denominador próprio: compara a função Educação com as despesas municipais e não mede o cumprimento do mínimo constitucional em MDE.</p>
                          </div>
                        </div>
                      ) : null}
                    </section>
                    <section>
                      <h4>Cálculo da margem</h4>
                      <p>Margem em pontos percentuais = percentual aplicado em MDE − 25.</p>
                      <p>Não há projeção ou preenchimento de exercícios ausentes.</p>
                      <p className="siope-method-disclosure__caveat">Os valores mínimo obrigatório e aplicado acima do mínimo em reais não são apresentados porque a base constitucional oficial separada, no mesmo exercício, não está integrada.</p>
                    </section>
                  </div>
                </div>
              </details>
            ) : null}
            {applicationSecondary.length ? (
              <div className="siope-application__secondary" aria-label="Outros indicadores de aplicação">
                {applicationSecondary.map((indicator, index) => (
                  <PublicMetric
                    compact
                    icon={index === 2 ? 'education' : 'students'}
                    key={indicator.key}
                    label={PUBLIC_LABELS[indicator.key] ?? indicator.label}
                    model={indicator}
                  />
                ))}
              </div>
            ) : null}
          </section>

          <ExecutionSection execution={execution} />

          <aside className="page-card siope-fundeb-link" aria-label="Indicadores do Fundeb">
            <div>
              <span className="eyebrow">Fundeb</span>
              <strong>Veja recursos, aplicação e saldos do Fundeb.</strong>
            </div>
            <a className="platform-navigation-button" href={`#${FINANCIAL_PAGE_KEYS.fundeb}`}>Abrir página do Fundeb</a>
          </aside>

          {catalogIndicators.length ? (
            <section className="page-card siope-public-section siope-secondary-catalog" aria-labelledby="siope-secondary-title">
              <div className="siope-public-section-heading">
                <span className="eyebrow">Para aprofundar</span>
                <h2 id="siope-secondary-title">Indicadores secundários</h2>
              </div>
              <div className="siope-secondary-catalog__list">
                {catalogIndicators.map((indicator) => (
                  <PublicMetric
                    compact
                    key={indicator.key}
                    label={PUBLIC_LABELS[indicator.key] ?? indicator.label}
                    model={indicator}
                  />
                ))}
              </div>
            </section>
          ) : null}

          <FinancialSourcesFooter
            periods="Os períodos exibidos correspondem ao ano publicado em cada valor; execução das despesas usa o exercício informado."
            source="SIOPE/FNDE e SICONFI/DCA."
          />
        </>
      ) : null}

      {isDetailOpen && selectedIndicatorModel && selectedIndicator ? (
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
            total={detailIndicatorModels.length}
          />
          <section className="detail-panel educacao-detail-panel financial-detail-panel siope-detail">
            <FinancialDetailHeader indicator={selectedIndicatorModel} />
            <FinancialMetricGrid indicator={selectedIndicatorModel} />

            <FinancialPrimaryAnalysis>
              {validSeries.length >= 2 ? (
              <FinancialChartFrame
                subtitle={selectedIndicatorModel.description}
                source={<DataSourceNote className="fundeb-data-source siope-chart-source" source={SIOPE_SOURCE} />}
              >
                <IndicatorHistoryChart
                    chartType={selectedIndicator.unidade === 'reais' && validSeries.length <= 3 ? 'bar' : 'line'}
                    chartHeight={300}
                    endYear={2025}
                    formatDataLabel={(value) => formatCompactDataLabel(value, selectedIndicator.unidade)}
                    formatYAxis={selectedIndicator.unidade === 'reais' ? formatCompactCurrency : undefined}
                    item={{ label: selectedIndicatorModel.label }}
                    labelMode="all"
                    missingLabel={EM}
                    result={null}
                    series={chartSeries}
                    showMetaLine={false}
                    showMissingPoints={false}
                    startYear={2021}
                    title={selectedIndicatorModel.label}
                    unit={getIndicatorUnit(selectedIndicator)}
                    yTickCount={5}
                  />
              </FinancialChartFrame>
              ) : null}
              <FinancialQuickReading
                description={selectedIndicatorModel.description}
                indicator={selectedIndicatorModel}
                metadata={selectedMetadata}
                readingGuide={selectedIndicatorModel.readingGuide}
                text={selectedIndicatorModel.quickReading}
              />
            </FinancialPrimaryAnalysis>

            <FinancialIndicatorDisclosures
              formatValue={(value) => formatSiopeValue(value, selectedIndicator?.unidade)}
              indicator={selectedIndicatorModel}
              metadata={selectedMetadata}
              series={chartSeries}
              showDataDisclosure={false}
              source={SIOPE_SOURCE}
            />
          </section>
        </div>
      ) : null}
    </div>
  )
}
