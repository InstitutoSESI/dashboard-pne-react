import { FINANCIAL_PAGE_KEYS } from '../data/financialPageKeys.js'
import {
  VOCACOES_PNE_INTERNAL_ENABLED,
  VOCACOES_PNE_INTERNAL_ROUTE,
  resolveVocacoesPneInternalPage,
} from '../config/vocacoesPneInternalFlag.js'
import type { AppPageKey, FinancialPageKey } from '../types/app'
import type { LocationLike, ParsedAppLocation, ParsedHash } from '../types/navigation'
import { normalizeRouteValue, parseAppHash, parseAppLocation } from './appHash.js'
import { buildHashPageMap } from './navigationRegistry.js'

/*
 * O mapa de rotas nasce do registro unico de navegacao: cada pagina declara la
 * sua rota canonica e seus aliases, e este modulo apenas os projeta na forma
 * normalizada que o parser consulta. Rota nova se registra no registro, nao
 * aqui.
 */
const HASH_PAGE_MAP: Readonly<Record<string, AppPageKey>> = buildHashPageMap()

const FINANCIAL_PAGES: ReadonlySet<FinancialPageKey> = new Set(Object.values(FINANCIAL_PAGE_KEYS))

export function isFinancialPage(page: AppPageKey): page is FinancialPageKey {
  return FINANCIAL_PAGES.has(page as FinancialPageKey)
}

export function resolveActivePage({ params, route }: Pick<ParsedHash, 'params' | 'route'>): AppPageKey {
  if (route === VOCACOES_PNE_INTERNAL_ROUTE) {
    return resolveVocacoesPneInternalPage(route, VOCACOES_PNE_INTERNAL_ENABLED) ?? 'home'
  }

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
