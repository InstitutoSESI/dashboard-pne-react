import { useEffect, useState } from 'react'
import { loadMunicipalFinanceCatalog, municipalFinanceLoader, type MunicipalFinanceCatalog } from '../../data/municipalFinance'
import type { CompactFinancialValue, MunicipalFinanceDocumentV1 } from '../../features/diagnostic/municipalFinanceTypes'
import { formatFullCurrency, formatPercent, formatCoefficient } from '../../features/municipal-finance/municipalFinancePresentation'
import { PmePageHeading, PmeState, PmeTableRegion } from './PmePrimitives'
import { buildPmeFinancialMetrics, PME_FINANCIAL_STAGE_LABELS, type PmeFinancialMetric } from './pmeFinancePresentation'
import { pmeLink, type PmeRoute } from './pmeRoutes'
import type { PmeMunicipalityIdentity, PmeObjectiveModel, PmeModuleStatus } from './pmeTypes'
import { getPmeObjectiveEditorial } from './pmeCatalog'
import { PmeEditorialPaths } from './PmeEditorialPaths'
import './styles/pme-finance.css'

interface FinanceState {
  id: string
  status: 'loading' | 'ready' | 'absent' | 'error'
  document: MunicipalFinanceDocumentV1 | null
  catalog: MunicipalFinanceCatalog | null
  metrics: PmeFinancialMetric[]
  error: string | null
}

function displayAmount(amount: CompactFinancialValue): string {
  if (amount.value === null) return amount.financialStage === 'not_applicable' ? 'Não aplicável' : 'Indisponível'
  if (amount.unit === 'percent') return formatPercent(amount.value)
  if (amount.unit === 'BRL') return formatFullCurrency(amount.value)
  if (amount.unit === 'BRL_per_student') return `${formatFullCurrency(amount.value)} / matrícula`
  if (amount.unit === 'coefficient') return formatCoefficient(amount.value)
  return new Intl.NumberFormat('pt-BR').format(amount.value)
}

function FinanceSource({ amount, catalog }: { amount: CompactFinancialValue; catalog: MunicipalFinanceCatalog | null }) {
  const source = catalog?.sources.find((entry) => entry.sourceId === amount.sourceId)
  const reason = amount.nullReasonCode ? catalog?.reasonMessages[amount.nullReasonCode] : null
  const sourceName = source?.name || (amount.sourceId.startsWith('siope_rreo_constitutional_reconciliation_') ? 'SIOPE/FNDE e RREO — conferência entre fontes' : 'Referência oficial não informada')
  return <small className="pme-finance-source">Fonte: {source?.url ? <a href={source.url}>{sourceName}</a> : sourceName}.
    {reason ? <> {reason}</> : amount.value === null ? <> O valor não está disponível para este período na publicação.</> : null}
  </small>
}

function metricReading(metric: PmeFinancialMetric) {
  const readings: Record<string, string> = {
    paid: 'Despesa declarada na função Educação.',
    mde: 'Percentual declarado para manutenção e desenvolvimento do ensino.',
    remuneration: 'Percentual de recursos do Fundeb destinado à remuneração de profissionais.',
    fundeb: 'Previsão anual do Fundeb; os componentes abaixo já fazem parte dessa composição.',
    vaaf: 'Previsão anual da complementação VAAF.',
    vaat: 'Previsão anual da complementação VAAT.',
    vaar: 'Previsão anual da complementação VAAR; o recebimento depende dos demonstrativos do exercício.',
    qse: 'Valor distribuído no exercício encerrado.',
    'qse-forecast': 'Estimativa oficial para o exercício indicado; não equivale a repasse.',
    'qse-student': 'Valor por matrícula já divulgado; não representa o gasto total por estudante.',
  }
  return readings[metric.id] || 'Valor publicado para o período indicado.'
}

function reconciliationReading(status: MunicipalFinanceDocumentV1['reconciliation']['status']) {
  const labels: Record<MunicipalFinanceDocumentV1['reconciliation']['status'], string> = {
    reconciled: 'Informações conciliadas entre as fontes publicadas.',
    not_required: 'Não há conciliação adicional indicada para esta leitura.',
    pending_source: 'Ainda há fonte oficial pendente de publicação.',
    mapping_pending: 'A relação entre as fontes ainda está em conferência.',
    reconciliation_required: 'A comparação entre as fontes ainda precisa de conferência.',
    source_missing: 'Uma das fontes necessárias não está disponível.',
    divergent_explained: 'Há diferença entre fontes com explicação registrada.',
    divergent_unexplained: 'Há diferença entre fontes que ainda precisa de esclarecimento.',
    divergent: 'Há diferença entre fontes que exige conferência.',
    unavailable: 'Não foi possível apresentar a conciliação para este período.',
  }
  return labels[status]
}

function qualityReadings(document: MunicipalFinanceDocumentV1, catalog: MunicipalFinanceCatalog | null) {
  const readings = document.dataQuality.reasonCodes
    .map((reason) => catalog?.reasonMessages[reason])
    .filter((reason): reason is string => Boolean(reason))
  return readings.length ? readings : ['A publicação registra limites de cobertura que devem ser considerados na leitura dos valores.']
}

export function PmeFinancePage({ municipality, route, objectives, matrizStatus }: { municipality: PmeMunicipalityIdentity; route: PmeRoute; objectives: PmeObjectiveModel[]; matrizStatus: PmeModuleStatus }) {
  const [attempt, setAttempt] = useState(0)
  const [state, setState] = useState<FinanceState>({ id: municipality.ibgeCode, status: 'loading', document: null, catalog: null, metrics: [], error: null })
  useEffect(() => {
    let cancelled = false
    setState({ id: municipality.ibgeCode, status: 'loading', document: null, catalog: null, metrics: [], error: null })
    void Promise.allSettled([
      municipalFinanceLoader.load(municipality.ibgeCode, { force: attempt > 0 }),
      loadMunicipalFinanceCatalog(),
    ]).then(([financial, catalog]) => {
      if (cancelled) return
      const sourceCatalog = catalog.status === 'fulfilled' ? catalog.value : null
      if (financial.status === 'rejected') {
        const code: unknown = financial.reason?.code
        setState({ id: municipality.ibgeCode, status: code === 'contract_absent' ? 'absent' : 'error', document: null, catalog: sourceCatalog, metrics: [], error: String(financial.reason?.message || 'Falha ao carregar o documento financeiro.') })
        return
      }
      try {
        const metrics = buildPmeFinancialMetrics(financial.value, municipality)
        setState({ id: municipality.ibgeCode, status: 'ready', document: financial.value, catalog: sourceCatalog, metrics, error: null })
      } catch (error) {
        setState({ id: municipality.ibgeCode, status: 'error', document: null, catalog: sourceCatalog, metrics: [], error: error instanceof Error ? error.message : 'Documento financeiro inválido.' })
      }
    })
    return () => { cancelled = true }
  }, [municipality, attempt])
  const current = state.id === municipality.ibgeCode ? state : null
  const document = current?.status === 'ready' ? current.document : null
  const objectiveId = route.objectiveId
  const objective = objectiveId ? getPmeObjectiveEditorial(objectiveId) : null
  const paths = objectives.filter((item) => !objectiveId || item.objectiveId === objectiveId).flatMap((item) => item.paths)
  return <>
    <PmePageHeading title={`Financiamento em ${municipality.name}`} description="Leia execução, previsões e condições de financiamento junto às evidências educacionais. Cada valor mantém o seu exercício e a sua natureza." />
    {objective && <p className="pme-note">Contexto da ficha: <a href={pmeLink(route, 'objetivo')}>Objetivo {objectiveId} — {objective.title}</a>. Os instrumentos são relacionados ao tema, sem inferência de elegibilidade.</p>}
    {!current || current.status === 'loading' ? <PmeState kind="loading" title="Carregando o contexto financeiro…" />
      : current.status === 'absent' ? <PmeState kind="unavailable" title="Documento financeiro não publicado"><p>As demais evidências do município continuam acessíveis.</p></PmeState>
        : current.status === 'error' ? <PmeState kind="error" title="Não foi possível carregar os dados financeiros" onRetry={() => setAttempt((value) => value + 1)}><p>Não foi possível confirmar os valores do município selecionado. Tente novamente para consultar os dados.</p></PmeState> : null}
    {document && <>
      {!current?.catalog && <PmeState kind="error" title="Referências oficiais não carregadas" onRetry={() => setAttempt((value) => value + 1)}><p>Os valores permanecem disponíveis, mas os nomes e links das fontes não puderam ser apresentados nesta sessão.</p></PmeState>}
      <section className="pme-finance-values" aria-label="Contexto financeiro publicado">
        {current?.metrics.slice(0, 4).map((metric) => <article className="pme-finance-value" key={metric.id}>
          <h2>{metric.label}</h2><strong>{displayAmount(metric.amount)}</strong>
          <p>{PME_FINANCIAL_STAGE_LABELS[metric.amount.financialStage] || 'Etapa não informada'} • {metric.amount.referenceYear}</p>
          <p className="pme-note">{metricReading(metric)} {metric.scope}</p><FinanceSource amount={metric.amount} catalog={current.catalog} />
        </article>)}
      </section>
      <section className="pme-section pme-finance-reading"><h2>Valores para consulta</h2><p>Os valores mantêm exercício, etapa e natureza próprios. Previsões não devem ser somadas à execução, e os componentes do Fundeb já incluídos no total não formam recursos adicionais.</p></section>
      <PmeTableRegion label="Valores financeiros por exercício, etapa e fonte">
        <table><caption>Valores publicados, sem somar previsões e execução</caption>
          <thead><tr><th scope="col">Informação</th><th scope="col">Valor e unidade</th><th scope="col">Exercício / etapa</th><th scope="col">Fonte e limite</th></tr></thead>
          <tbody>{current?.metrics.map((metric) => <tr key={metric.id}>
            <th scope="row">{metric.label}<small>{metricReading(metric)}</small></th><td className="pme-numeric">{displayAmount(metric.amount)}</td>
            <td>{metric.amount.referenceYear}<small>{PME_FINANCIAL_STAGE_LABELS[metric.amount.financialStage] || 'Etapa não informada'}</small></td>
            <td><FinanceSource amount={metric.amount} catalog={current.catalog} /><small>{metric.scope}</small></td>
          </tr>)}</tbody>
        </table>
      </PmeTableRegion>
      {document.execution.dcaEducation.history.length > 0 && <PmeTableRegion label="Histórico público de execução orçamentária">
        <table><caption>Execução na função Educação — valores nominais de cada ano</caption><thead><tr><th scope="col">Ano</th><th scope="col">Empenhado</th><th scope="col">Liquidado</th><th scope="col">Pago</th><th scope="col">Fonte</th></tr></thead>
          <tbody>{document.execution.dcaEducation.history.map((entry) => <tr key={entry.referenceYear}>
            <th scope="row">{entry.referenceYear}</th><td className="pme-numeric">{displayAmount(entry.committed)}</td><td className="pme-numeric">{displayAmount(entry.liquidated)}</td><td className="pme-numeric">{displayAmount(entry.paid)}</td><td><FinanceSource amount={entry.paid} catalog={current?.catalog || null} /></td>
          </tr>)}</tbody>
        </table>
      </PmeTableRegion>}
      <p className="pme-note">A série reúne valores nominais e não mede evolução real do poder de compra. Previsão, empenho, liquidação e pagamento são etapas distintas. A presença de um programa não demonstra saldo livre para financiar uma ação.</p>
      <details className="pme-finance-disclosure"><summary>Limites e conferência dos valores</summary><div className="pme-detail-body">
        <p><strong>Conferência entre fontes:</strong> {reconciliationReading(document.reconciliation.status)}</p>
        <p><strong>Ressalvas da publicação:</strong></p><ul>{qualityReadings(document, current?.catalog || null).map((reading) => <li key={reading}>{reading}</li>)}</ul>
        <p>Quando a conferência depender de informações ainda não publicadas, consulte a fonte oficial do exercício antes de usar o valor em deliberação.</p>
      </div></details>
    </>}
    <section className="pme-section"><h2>Caminhos para consulta</h2>
      <p>Instrumentos e orientações relacionados {objective ? 'ao objetivo selecionado' : 'ao financiamento e às condições de oferta'}. A análise municipal exige verificar as regras do exercício nas fontes oficiais.</p>
      {matrizStatus === 'not_loaded' ? <p role="status">Carregando os caminhos relacionados pela Matriz…</p> : <PmeEditorialPaths paths={paths} />}
    </section>
    <div className="pme-actions"><a className="pme-button pme-button--secondary" href={pmeLink(route, 'relatorio-tecnico')}>Abrir Relatório Técnico Municipal</a><a href={pmeLink(route, 'agenda')}>Retomar a Agenda de Análise</a></div>
  </>
}
