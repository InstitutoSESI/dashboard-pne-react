export type MatrizEducationContextKey = 'accessibility_by_network'

export interface MatrizEducationContextReference {
  readonly key: MatrizEducationContextKey
  /** Consequência prática e limite do recorte para a decisão. */
  readonly use: string
}

export interface MatrizAccessibilityByNetwork {
  readonly year: number
  readonly municipalSchools: number
  readonly municipalAccessibleRoomsPercent: number
  readonly stateSchools: number
  readonly stateAccessibleRoomsPercent: number
  readonly publicSchools: number
  readonly publicAccessibleRoomsPercent: number
}

export interface MatrizEducationContext {
  readonly accessibilityByNetwork: MatrizAccessibilityByNetwork | null
}

export interface MatrizEducationContextFact {
  readonly display: string
  readonly label: string
  readonly period: string
  readonly use: string
}

interface InfrastructureNetworkRow {
  readonly dependency: string
  readonly schools: number
  readonly accessibleRoomsPercent: number
  readonly year: number
}

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null
  return value as Record<string, unknown>
}

function finiteNumber(value: unknown): number | null {
  if (typeof value !== 'number' || !Number.isFinite(value)) return null
  return value
}

function normalizeNetworkRow(value: unknown): InfrastructureNetworkRow | null {
  const row = asRecord(value)
  if (!row || typeof row.dependencia !== 'string') return null
  const year = finiteNumber(row.ano)
  const schools = finiteNumber(row.escolas)
  const accessibleRoomsPercent = finiteNumber(row.perc_salas_acessiveis)
  if (
    year === null
    || !Number.isInteger(year)
    || schools === null
    || !Number.isInteger(schools)
    || schools < 0
    || accessibleRoomsPercent === null
    || accessibleRoomsPercent < 0
    || accessibleRoomsPercent > 100
  ) return null

  return Object.freeze({
    dependency: row.dependencia,
    schools,
    accessibleRoomsPercent,
    year,
  })
}

function findNetworkRow(
  rows: readonly InfrastructureNetworkRow[],
  dependency: string,
  year: number,
): InfrastructureNetworkRow | null {
  return rows.find((row) => row.dependency === dependency && row.year === year) ?? null
}

/**
 * Extrai somente o recorte necessário da publicação educacional já validada.
 * Falhas ou campos incompletos omitem o contexto adicional, sem inventar zero.
 */
export function buildMatrizEducationContext(document: unknown): MatrizEducationContext {
  const root = asRecord(document)
  const blocks = asRecord(root?.blocos)
  const schoolNetwork = asRecord(blocks?.rede_escolar)
  const infrastructure = asRecord(schoolNetwork?.infraestrutura)
  const rawRows = Array.isArray(infrastructure?.por_rede) ? infrastructure.por_rede : []
  const rows = rawRows
    .map(normalizeNetworkRow)
    .filter((row): row is InfrastructureNetworkRow => row !== null)
  const years = [...new Set(rows.map((row) => row.year))].sort((left, right) => right - left)

  for (const year of years) {
    const municipal = findNetworkRow(rows, 'municipal', year)
    const state = findNetworkRow(rows, 'estadual', year)
    const publicNetwork = findNetworkRow(rows, 'publica', year)
    if (!municipal || !state || !publicNetwork) continue

    return Object.freeze({
      accessibilityByNetwork: Object.freeze({
        year,
        municipalSchools: municipal.schools,
        municipalAccessibleRoomsPercent: municipal.accessibleRoomsPercent,
        stateSchools: state.schools,
        stateAccessibleRoomsPercent: state.accessibleRoomsPercent,
        publicSchools: publicNetwork.schools,
        publicAccessibleRoomsPercent: publicNetwork.accessibleRoomsPercent,
      }),
    })
  }

  return Object.freeze({ accessibilityByNetwork: null })
}

function formatPercent(value: number): string {
  return `${value.toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%`
}

export function resolveMatrizEducationContextFact(
  context: MatrizEducationContext | null | undefined,
  reference: MatrizEducationContextReference,
): MatrizEducationContextFact | null {
  if (reference.key !== 'accessibility_by_network' || !context?.accessibilityByNetwork) return null
  const accessibility = context.accessibilityByNetwork
  return Object.freeze({
    label: 'Acessibilidade por rede',
    display: `Rede municipal: ${formatPercent(accessibility.municipalAccessibleRoomsPercent)} das salas · rede estadual: ${formatPercent(accessibility.stateAccessibleRoomsPercent)}`,
    period: String(accessibility.year),
    use: reference.use,
  })
}
