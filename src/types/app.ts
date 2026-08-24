import type { FINANCIAL_PAGE_KEYS } from '../data/financialPageKeys'

export type FinancialPageKey = (typeof FINANCIAL_PAGE_KEYS)[keyof typeof FINANCIAL_PAGE_KEYS]

export type AppPageKey =
  | 'home'
  | 'pne-overview'
  | 'pne-legal-goals'
  | 'matriz-prioridades'
  | 'caderno'
  | 'cenarios-educacao'
  | 'pne2014'
  | 'pne2026'
  | 'diagnostico'
  | 'educacao'
  | 'relatorio-tecnico-municipal'
  | FinancialPageKey
