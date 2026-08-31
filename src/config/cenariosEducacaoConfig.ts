export const CENARIOS_EDUCACAO_REGION_SLUG = 'vale-do-sinos' as const
export const CENARIOS_EDUCACAO_MUNICIPALITY_IBGE_CODE = '4313375' as const

export function isCenariosEducacaoRegionSupported(regionSlug: string | null | undefined): boolean {
  return regionSlug === CENARIOS_EDUCACAO_REGION_SLUG
}
