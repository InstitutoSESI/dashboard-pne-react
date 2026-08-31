import { FINANCIAL_PAGE_KEYS } from '../data/financialPageKeys.js'
import type { AppPageKey } from '../types/app'

/**
 * Vocabulário canônico de produtos analíticos.
 *
 * Um produto é uma frente publicável inteira, não uma página: uma publicação
 * `partial` libera produtos completos e mantém os demais explicitamente
 * indisponíveis. A lista precisa ser idêntica à de
 * `data_pipeline/src/state_publication.py` e `scripts/lib/state-build-profile.mjs`.
 */
export const ANALYTICS_PRODUCTS = ['pne', 'educacao', 'financiamento'] as const

export type AnalyticsProduct = (typeof ANALYTICS_PRODUCTS)[number]

export const ANALYTICS_PRODUCT_LABELS: Readonly<Record<AnalyticsProduct, string>> = Object.freeze({
  pne: 'Metas do PNE',
  educacao: 'Indicadores educacionais',
  financiamento: 'Financiamento da educação',
})

export function isAnalyticsProduct(value: unknown): value is AnalyticsProduct {
  return typeof value === 'string'
    && (ANALYTICS_PRODUCTS as readonly string[]).includes(value)
}

const PAGE_PRODUCTS: Readonly<Record<string, AnalyticsProduct>> = Object.freeze({
  'pne-overview': 'pne',
  'pne-legal-goals': 'pne',
  'matriz-prioridades': 'pne',
  pne2014: 'pne',
  pne2026: 'pne',
  diagnostico: 'pne',
  educacao: 'educacao',
  'relatorio-tecnico-municipal': 'educacao',
  'analise-regional': 'educacao',
  'vocacoes-regiao': 'educacao',
  'cenarios-educacao': 'educacao',
  'cenarios-educacao-dados': 'educacao',
  [FINANCIAL_PAGE_KEYS.overview]: 'financiamento',
  [FINANCIAL_PAGE_KEYS.panorama]: 'financiamento',
  [FINANCIAL_PAGE_KEYS.application]: 'financiamento',
  [FINANCIAL_PAGE_KEYS.fundeb]: 'financiamento',
  [FINANCIAL_PAGE_KEYS.vaar]: 'financiamento',
  [FINANCIAL_PAGE_KEYS.pnate]: 'financiamento',
})

/** A Home não pertence a produto algum: ela é a moldura da plataforma. */
export function resolvePageProduct(page: AppPageKey): AnalyticsProduct | null {
  return PAGE_PRODUCTS[page] ?? null
}

/**
 * Decisão pura do contrato: `complete` libera tudo, `partial` libera apenas o
 * que declarou e `identity-only` não libera produto algum. Mantida separada da
 * publicação ativa para poder ser exercitada com fixtures.
 */
export function isProductEnabledFor(
  analyticsStatus: string,
  enabledProducts: readonly string[] | null,
  product: AnalyticsProduct,
): boolean {
  if (analyticsStatus === 'complete') return true
  if (analyticsStatus === 'partial') return enabledProducts?.includes(product) ?? false
  return false
}

/** Uma página é navegável quando não pertence a produto ou o produto está ativo. */
export function isPageNavigable(
  page: AppPageKey,
  analyticsStatus: string,
  enabledProducts: readonly string[] | null,
): boolean {
  const product = resolvePageProduct(page)
  if (product === null) return true
  return isProductEnabledFor(analyticsStatus, enabledProducts, product)
}
