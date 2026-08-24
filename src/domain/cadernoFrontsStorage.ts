import type { MunicipalityStorage } from './municipalityStorage'

/*
 * Frentes que o município escolheu atacar.
 *
 * A seleção é decisão municipal: nunca sai do navegador, exceto pela
 * exportação explícita da planilha da oficina, e jamais altera as classes
 * públicas do diagnóstico. Segue o padrão de `municipalityStorage.ts`: chave
 * versionada, payload com `schemaVersion` conferido campo a campo e acessos
 * embrulhados para tolerar storage indisponível.
 */

export const CADERNO_FRONTS_STORAGE_KEY_PREFIX = 'pne_caderno_frentes_v1'
export const CADERNO_FRONTS_SCHEMA_VERSION = 'caderno-frentes-v1'

export interface CadernoFrontsScope {
  readonly municipalityIbge7: string
  readonly referenceDate: string
}

export interface CadernoFrontsSelection {
  readonly schemaVersion: typeof CADERNO_FRONTS_SCHEMA_VERSION
  readonly municipalityIbge7: string
  readonly referenceDate: string
  readonly selections: readonly string[]
}

const IBGE7_PATTERN = /^\d{7}$/
const ISO_DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function safeGet(storage: MunicipalityStorage, key: string): string | null {
  try {
    return storage.getItem(key)
  } catch {
    return null
  }
}

function safeSet(storage: MunicipalityStorage, key: string, value: string): boolean {
  try {
    storage.setItem(key, value)
    return true
  } catch {
    return false
  }
}

function safeRemove(storage: MunicipalityStorage, key: string): void {
  try {
    storage.removeItem(key)
  } catch {
    // Storage can be unavailable in restricted browser contexts.
  }
}

/** Identidade de uma frente: a hipótese é única pelo par meta × fator. */
export function cadernoFrontKey(goalId: string, factorId: string): string {
  return `${goalId}::${factorId}`
}

export function parseCadernoFrontKey(key: string): { goalId: string; factorId: string } | null {
  const [goalId, factorId, ...rest] = key.split('::')
  if (!goalId || !factorId || rest.length > 0) return null
  return { goalId, factorId }
}

export function cadernoFrontsStorageKey({ municipalityIbge7, referenceDate }: CadernoFrontsScope): string {
  return `${CADERNO_FRONTS_STORAGE_KEY_PREFIX}:${municipalityIbge7}:${referenceDate}`
}

export function parseCadernoFronts(
  rawValue: string | null,
  scope: CadernoFrontsScope,
): readonly string[] {
  if (!rawValue) return []

  try {
    const value: unknown = JSON.parse(rawValue)
    if (
      !isRecord(value)
      || value.schemaVersion !== CADERNO_FRONTS_SCHEMA_VERSION
      || value.municipalityIbge7 !== scope.municipalityIbge7
      || value.referenceDate !== scope.referenceDate
      || !Array.isArray(value.selections)
    ) {
      return []
    }
    const selections = value.selections.filter(
      (item): item is string => typeof item === 'string' && parseCadernoFrontKey(item) !== null,
    )
    return Object.freeze([...new Set(selections)].sort())
  } catch {
    return []
  }
}

export function serializeCadernoFronts(
  scope: CadernoFrontsScope,
  selections: readonly string[],
): string {
  if (!IBGE7_PATTERN.test(scope.municipalityIbge7) || !ISO_DATE_PATTERN.test(scope.referenceDate)) {
    throw new Error('Escopo inválido para as frentes do caderno.')
  }
  const payload: CadernoFrontsSelection = {
    schemaVersion: CADERNO_FRONTS_SCHEMA_VERSION,
    municipalityIbge7: scope.municipalityIbge7,
    referenceDate: scope.referenceDate,
    selections: [...new Set(selections)].sort(),
  }
  return JSON.stringify(payload)
}

export function getBrowserCadernoStorage(): MunicipalityStorage | null {
  try {
    return globalThis.localStorage ?? null
  } catch {
    return null
  }
}

export function restoreCadernoFronts(
  storage: MunicipalityStorage | null,
  scope: CadernoFrontsScope,
): readonly string[] {
  if (!storage) return []
  return parseCadernoFronts(safeGet(storage, cadernoFrontsStorageKey(scope)), scope)
}

export function persistCadernoFronts(
  storage: MunicipalityStorage | null,
  scope: CadernoFrontsScope,
  selections: readonly string[],
): boolean {
  if (!storage) return false
  const key = cadernoFrontsStorageKey(scope)
  if (selections.length === 0) {
    safeRemove(storage, key)
    return true
  }
  return safeSet(storage, key, serializeCadernoFronts(scope, selections))
}
