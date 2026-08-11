import type { MunicipalFinanceDocumentV1 } from '../diagnostic/municipalFinanceTypes'
import { isPublishableFinancialValue } from '../../utils/financialPresentation'

export interface FinancePresentationContext {
  indicatorIds: readonly string[]
  programIds: readonly string[]
}

export interface FinancingProgramsCatalog {
  programs: readonly {
    programId: string
    title: string
  }[]
}

export interface IndicatorCatalog {
  indicators: readonly {
    indicatorId: string
    name: string
  }[]
}

interface FinanceRelationPresentation {
  key: string
  indicatorLabel: string
  programLabel: string
  relationLabel: string
  reading: string
}

const fullCurrencyFormatter = new Intl.NumberFormat('pt-BR', {
  style: 'currency',
  currency: 'BRL',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
})

const decimalFormatter = new Intl.NumberFormat('pt-BR', {
  maximumFractionDigits: 2,
})

const integerFormatter = new Intl.NumberFormat('pt-BR', {
  maximumFractionDigits: 0,
})

export function formatFullCurrency(value: number): string {
  return fullCurrencyFormatter.format(value)
}

export function formatCompactCurrency(value: number): string {
  const absolute = Math.abs(value)
  if (absolute >= 1_000_000_000) return `R$ ${decimalFormatter.format(value / 1_000_000_000)} bi`
  if (absolute >= 1_000_000) return `R$ ${decimalFormatter.format(value / 1_000_000)} mi`
  if (absolute >= 1_000) return `R$ ${decimalFormatter.format(value / 1_000)} mil`
  return formatFullCurrency(value)
}

export function formatPercent(value: number): string {
  return `${decimalFormatter.format(value)}%`
}

export function formatIcmsSharePercent(value: number): string {
  return `${decimalFormatter.format(value)}%`
}

export function formatIndexScore(value: number): string {
  return decimalFormatter.format(value)
}

export function formatCount(value: number): string {
  return integerFormatter.format(value)
}

export function formatCoefficient(value: number): string {
  return new Intl.NumberFormat('pt-BR', {
    minimumFractionDigits: 6,
    maximumFractionDigits: 8,
  }).format(value)
}

export function splitFinanceContextIds(value: string | null | undefined): string[] {
  return Array.from(new Set(
    String(value ?? '')
      .split(',')
      .map((item) => item.trim())
      .filter(Boolean),
  ))
}

export function buildMunicipalFinancePresentation(
  document: MunicipalFinanceDocumentV1,
  programsCatalog: FinancingProgramsCatalog,
  indicatorsCatalog: IndicatorCatalog,
  context: FinancePresentationContext,
) {
  const programById = new Map(programsCatalog.programs.map((program) => [program.programId, program]))
  const indicatorById = new Map(indicatorsCatalog.indicators.map((indicator) => [indicator.indicatorId, indicator]))

  const fundebNonBeneficiaryLabels = [
    ['VAAF', document.programStatuses.fundebVaaf.status],
    ['VAAT', document.programStatuses.fundebVaat.status],
    ['VAAR', document.programStatuses.fundebVaar.status],
  ].filter(([, status]) => status === 'confirmed_non_beneficiary').map(([label]) => label)

  const hasQseData = [
    document.amounts.qseDistributedClosedYear,
    document.amounts.qseOfficialEstimateCurrentYear,
    document.qse.enrollmentsClosedYear,
  ].some((value) => isPublishableFinancialValue(value))

  const contextIndicatorIds = new Set(context.indicatorIds)
  const contextProgramIds = new Set(context.programIds)
  const hasContext = contextIndicatorIds.size > 0 || contextProgramIds.size > 0
  const relatedLinks = document.educationLinks.filter((link) => (
    (!hasContext || contextIndicatorIds.has(link.indicatorId) || contextProgramIds.has(link.programId))
    && isPublishableFinancialValue(resolveDocumentReference(document, link.amountReferenceId))
  ))
  const relations: readonly FinanceRelationPresentation[] = relatedLinks.map((link) => ({
    key: `${link.indicatorId}-${link.programId}-${link.relationType}`,
    indicatorLabel: indicatorById.get(link.indicatorId)?.name ?? link.indicatorId,
    programLabel: programById.get(link.programId)?.title ?? link.programId,
    relationLabel: {
      general_mde: 'Fonte geral de MDE',
      conditional_support: 'Apoio condicionado',
      accounting_context: 'Contexto contábil',
      direct_cost_driver: 'Relação direta registrada',
    }[link.relationType],
    reading: relationReading(link, programById.get(link.programId)?.title ?? link.programId),
  }))

  return {
    fundebNonBeneficiaryLabels,
    hasQseData,
    relations,
  }
}

function resolveDocumentReference(document: MunicipalFinanceDocumentV1, path: string): unknown {
  return path.split('.').reduce<unknown>((value, key) => {
    if (!value || typeof value !== 'object') return null
    return (value as Record<string, unknown>)[key]
  }, document)
}

function relationReading(
  link: MunicipalFinanceDocumentV1['educationLinks'][number],
  programLabel: string,
): string {
  if (link.relationType === 'general_mde') {
    return `${programLabel} é fonte geral de MDE. Não há confirmação de destinação específica para este indicador.`
  }
  if (link.relationType === 'accounting_context') {
    return 'A evidência oferece contexto contábil de execução e não representa fonte adicional de recurso.'
  }
  if (link.relationType === 'direct_cost_driver') {
    return 'A relação direta está registrada; ela não altera a prioridade educacional nem comprova aplicação do valor.'
  }
  if (link.municipalStatus === 'confirmed_beneficiary' && link.programId === 'fundeb_vaar') {
    return 'O município é beneficiário nominal do VAAR em 2026, mas o valor apresentado é previsão e não comprova recebimento ou aplicação.'
  }
  if (link.municipalStatus === 'confirmed_non_beneficiary') {
    return `O município está registrado como não beneficiário de ${programLabel} no período; nenhum valor potencial é apresentado.`
  }
  return `${programLabel} é apoio condicionado. Não há confirmação de recebimento, aplicação ou efeito sobre o indicador.`
}
