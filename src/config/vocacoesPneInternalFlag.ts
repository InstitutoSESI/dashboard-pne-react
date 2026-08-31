const ENABLED_VALUES = new Set(['1', 'true', 'yes', 'on'])

export function resolveVocacoesPneInternalEnabled(
  env: Record<string, unknown> | undefined = import.meta.env,
): boolean {
  const rawValue = env?.VITE_ENABLE_VOCACOES_PNE_INTERNAL
  if (rawValue === true) return true
  if (typeof rawValue !== 'string') return false
  return ENABLED_VALUES.has(rawValue.trim().toLocaleLowerCase('en-US'))
}

export const VOCACOES_PNE_INTERNAL_ENABLED = resolveVocacoesPneInternalEnabled()

export const VOCACOES_PNE_INTERNAL_ROUTE = 'vocacoespneinterno'

export function resolveVocacoesPneInternalPage(
  route: string,
  enabled = VOCACOES_PNE_INTERNAL_ENABLED,
): 'vocacoes-pne-internal' | null {
  return route === VOCACOES_PNE_INTERNAL_ROUTE && enabled
    ? 'vocacoes-pne-internal'
    : null
}
