import type { CompactFinancialValue, MunicipalFinanceDocumentV1 } from '../../features/diagnostic/municipalFinanceTypes'
import type { PmeMunicipalityIdentity } from './pmeTypes'

export interface PmeFinancialMetric {
  id: string
  label: string
  amount: CompactFinancialValue
  scope: string
}

export const PME_FINANCIAL_STAGE_LABELS: Record<string, string> = {
  forecast: 'Previsão', authorized: 'Autorizado', committed: 'Empenhado', transferred: 'Transferido',
  received: 'Recebido', budgeted: 'Orçado', empenhado: 'Empenhado', liquidado: 'Liquidado',
  paid: 'Pago', balance: 'Saldo declarado', calculated_indicator: 'Indicador publicado', not_applicable: 'Não aplicável',
}

/** Projection only: no new totals, ratios, eligibility rules or comparisons. */
export function buildPmeFinancialMetrics(document: MunicipalFinanceDocumentV1, municipality: PmeMunicipalityIdentity): PmeFinancialMetric[] {
  if (document?.schemaVersion !== 'municipal-finance-v1'
    || document.municipality?.ibgeCode !== municipality.ibgeCode
    || document.municipality.name !== municipality.name
    || document.municipality.uf !== 'RS') {
    throw new Error('A identidade ou a versão do documento financeiro diverge do município solicitado.')
  }
  if (!document.dataVersion || !document.methodologyVersion || !document.generatedAt) {
    throw new Error('O documento financeiro não identifica suas versões e sua emissão.')
  }
  const metrics: PmeFinancialMetric[] = [
    { id: 'paid', label: 'Despesa paga em educação', amount: document.execution?.dcaEducation?.paid, scope: 'Função 12 — Educação. Despesa declarada pelo município.' },
    { id: 'mde', label: 'Aplicação em manutenção e desenvolvimento do ensino', amount: document.constitutionalApplication?.mdeAppliedRate?.canonical, scope: 'Resultado após conferência das informações do SIOPE e do RREO.' },
    { id: 'remuneration', label: 'Remuneração dos profissionais com recursos do Fundeb', amount: document.constitutionalApplication?.fundebProfessionalRemunerationRate?.canonical, scope: 'Percentual do conjunto de recursos; não representa remuneração individual.' },
    { id: 'fundeb', label: 'Fundeb total previsto', amount: document.amounts?.fundebTotalAnnualForecast, scope: 'Previsão anual oficial. Componentes já incluídos não podem ser somados outra vez.' },
    { id: 'vaaf', label: 'Complementação VAAF prevista', amount: document.amounts?.fundebVaafAnnualForecast, scope: 'Componente do Fundeb conforme composição publicada.' },
    { id: 'vaat', label: 'Complementação VAAT prevista', amount: document.amounts?.fundebVaatAnnualForecast, scope: 'Componente do Fundeb conforme composição publicada.' },
    { id: 'vaar', label: 'Complementação VAAR prevista', amount: document.amounts?.fundebVaarAnnualForecast, scope: 'A situação municipal depende dos demonstrativos oficiais do exercício.' },
    { id: 'qse', label: 'Quota do Salário-Educação distribuída', amount: document.amounts?.qseDistributedClosedYear, scope: 'Valor distribuído no exercício encerrado.' },
    { id: 'qse-forecast', label: 'Quota do Salário-Educação estimada', amount: document.amounts?.qseOfficialEstimateCurrentYear, scope: 'Estimativa oficial para o exercício indicado; não equivale a repasse.' },
    { id: 'qse-student', label: 'Quota do Salário-Educação por matrícula', amount: document.perStudent?.qseDistributedPerEnrollment, scope: 'Valor divulgado por matrícula; não representa gasto total por estudante.' },
  ]
  for (const metric of metrics) {
    assertAmount(metric.amount, metric.id)
  }
  if (!Array.isArray(document.execution?.dcaEducation?.history)
    || !Array.isArray(document.dataQuality?.reasonCodes) || !document.reconciliation?.status) {
    throw new Error('Histórico ou notas de qualidade do documento financeiro inválidos.')
  }
  for (const row of document.execution.dcaEducation.history) {
    if (!Number.isInteger(row.referenceYear) || !row.sourceId) throw new Error('Período ou fonte do histórico financeiro inválidos.')
    for (const key of ['committed', 'liquidated', 'paid'] as const) {
      assertAmount(row[key], `histórico.${key}`)
      if (row[key].referenceYear !== row.referenceYear || row[key].sourceId !== row.sourceId) {
        throw new Error('O histórico financeiro contém valores de períodos ou fontes divergentes.')
      }
    }
  }
  return metrics
}

function assertAmount(amount: CompactFinancialValue, field: string) {
  if (!amount || !(amount.value === null || (typeof amount.value === 'number' && Number.isFinite(amount.value)))
    || !Number.isInteger(amount.referenceYear) || !['BRL', 'percent', 'count', 'coefficient', 'BRL_per_student'].includes(amount.unit)
    || !amount.sourceId || !Object.prototype.hasOwnProperty.call(PME_FINANCIAL_STAGE_LABELS, amount.financialStage)) {
    throw new Error(`O campo financeiro ${field} não possui valor, estado e proveniência válidos.`)
  }
}
