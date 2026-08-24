import { FINANCIAL_PAGE_KEYS } from '../data/financialPageKeys.js'
import type { AppPageKey, FinancialPageKey } from '../types/app'
import type { LocationLike, ParsedAppLocation, ParsedHash } from '../types/navigation'
import { normalizeRouteValue, parseAppHash, parseAppLocation } from './appHash.js'

const HASH_PAGE_MAP: Readonly<Record<string, AppPageKey>> = Object.freeze({
  home: 'home',
  pneoverview: 'pne-overview',
  pnelegalgoals: 'pne-legal-goals',
  metaslegais: 'pne-legal-goals',
  matrizprioridades: 'matriz-prioridades',
  caderno: 'caderno',
  cadernodehipoteses: 'caderno',
  cenariosdaeducacao: 'cenarios-educacao',
  cenariosdaeducacaomunicipal: 'cenarios-educacao',
  cenarioseducacao: 'cenarios-educacao',
  pne2014: 'pne2014',
  pne2024: 'pne2014',
  pne2026: 'pne2026',
  diagnostico: 'diagnostico',
  educacao: 'educacao',
  relatoriotecnicomunicipal: 'relatorio-tecnico-municipal',
  financeiros: 'financeiros',
  financeirospanorama: FINANCIAL_PAGE_KEYS.panorama,
  panoramafinanceiro: FINANCIAL_PAGE_KEYS.panorama,
  financeirosaplicacaorecursos: FINANCIAL_PAGE_KEYS.application,
  financeirosfundeb: FINANCIAL_PAGE_KEYS.fundeb,
  financeirospnate: FINANCIAL_PAGE_KEYS.pnate,
  financeirosvaar: FINANCIAL_PAGE_KEYS.vaar,
  fundeb: FINANCIAL_PAGE_KEYS.fundeb,
  pnate: FINANCIAL_PAGE_KEYS.pnate,
  siope: FINANCIAL_PAGE_KEYS.application,
  vaar: FINANCIAL_PAGE_KEYS.vaar,
  sistemas: 'educacao',
  escolassistemas: 'educacao',
} satisfies Record<string, AppPageKey>)

const FINANCIAL_PAGES: ReadonlySet<FinancialPageKey> = new Set(Object.values(FINANCIAL_PAGE_KEYS))

export function isFinancialPage(page: AppPageKey): page is FinancialPageKey {
  return FINANCIAL_PAGES.has(page as FinancialPageKey)
}

export function resolveActivePage({ params, route }: Pick<ParsedHash, 'params' | 'route'>): AppPageKey {
  if (route === 'financeiros') {
    const requestedModule = params.get('modulo') ?? params.get('module')
    const normalizedModule = normalizeRouteValue(requestedModule)

    if (normalizedModule === 'fundeb') return FINANCIAL_PAGE_KEYS.fundeb
    if (normalizedModule === 'pnate') return FINANCIAL_PAGE_KEYS.pnate
    if (normalizedModule === 'vaar' || normalizedModule === 'complementacaovaar') return FINANCIAL_PAGE_KEYS.vaar
    if (normalizedModule === 'siope' || normalizedModule === 'aplicacaorecursos') return FINANCIAL_PAGE_KEYS.application
  }

  return HASH_PAGE_MAP[route] ?? 'home'
}

export function resolveActivePageFromHash(hash?: unknown): AppPageKey {
  return resolveActivePage(parseAppHash(hash))
}

export function getNavigationContextFromLocation(
  location: LocationLike | null = typeof window === 'undefined' ? null : window.location,
): ParsedAppLocation {
  return parseAppLocation(location ?? {})
}

export function getActivePageFromLocation(
  location: LocationLike | null = typeof window === 'undefined' ? null : window.location,
): AppPageKey {
  return location ? resolveActivePage(getNavigationContextFromLocation(location)) : 'home'
}
