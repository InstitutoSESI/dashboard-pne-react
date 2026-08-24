import type { MunicipalityStorage } from './municipalityStorage'

/* O plano da matriz é decisão municipal e permanece no navegador. */
export const MATRIZ_FRONTS_STORAGE_KEY_PREFIX = 'pne_matriz_frentes_v5'
export const MATRIZ_FRONTS_SCHEMA_VERSION = 'matriz-frentes-v5'
export const MATRIZ_FRONTS_LEGACY_KEY_PREFIX_V4 = 'pne_matriz_frentes_v4'
export const MATRIZ_FRONTS_LEGACY_SCHEMA_VERSION_V4 = 'matriz-frentes-v4'
export const MATRIZ_FRONTS_LEGACY_KEY_PREFIX_V3 = 'pne_matriz_frentes_v3'
export const MATRIZ_FRONTS_LEGACY_SCHEMA_VERSION_V3 = 'matriz-frentes-v3'

export type MatrizPlanStatus = 'todo' | 'doing' | 'done'

export interface MatrizPlanEntry {
  readonly key: string
  readonly status: MatrizPlanStatus
  readonly note: string
  /** Rótulos públicos preservados para explicar uma frente retirada em leitura futura. */
  readonly goalTitle?: string
  readonly frontTitle?: string
}

export interface MatrizFrontsScope {
  readonly municipalityIbge7: string
  readonly referenceDate: string
}

interface MatrizPlanPayload {
  readonly schemaVersion: typeof MATRIZ_FRONTS_SCHEMA_VERSION
  readonly municipalityIbge7: string
  readonly referenceDate: string
  readonly entries: readonly MatrizPlanEntry[]
}

export interface PreviousMatrizPlan {
  readonly referenceDate: string
  readonly entries: readonly MatrizPlanEntry[]
}

export interface MatrizPlanReconciliation {
  readonly kept: readonly MatrizPlanEntry[]
  readonly removed: readonly MatrizPlanEntry[]
}

interface EnumerableMatrizStorage extends MunicipalityStorage {
  readonly length: number
  key(index: number): string | null
}

const IBGE7_PATTERN = /^\d{7}$/
const ISO_DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/
const FRENTE_KEY_PATTERN = /^\d{1,2}\.[a-z]\|[a-z0-9-]+$/
const CONTROL_CHARACTER_PATTERN = /\p{Cc}/gu
const PLAN_STATUSES = new Set<MatrizPlanStatus>(['todo', 'doing', 'done'])
const STORAGE_PREFIX_PRIORITY = new Map([
  [MATRIZ_FRONTS_LEGACY_KEY_PREFIX_V3, 1],
  [MATRIZ_FRONTS_LEGACY_KEY_PREFIX_V4, 2],
  [MATRIZ_FRONTS_STORAGE_KEY_PREFIX, 3],
])

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function sanitizeNote(value: unknown): string {
  if (typeof value !== 'string') return ''
  return value
    .replace(CONTROL_CHARACTER_PATTERN, ' ')
    .replace(/\s{2,}/g, ' ')
    .trim()
    .slice(0, 280)
}

function sanitizePlanLabel(value: unknown): string | undefined {
  if (typeof value !== 'string') return undefined
  const sanitized = value
    .replace(CONTROL_CHARACTER_PATTERN, ' ')
    .replace(/\s{2,}/g, ' ')
    .trim()
    .slice(0, 180)
  return sanitized || undefined
}

function normalizeStatus(value: unknown): MatrizPlanStatus {
  return typeof value === 'string' && PLAN_STATUSES.has(value as MatrizPlanStatus)
    ? value as MatrizPlanStatus
    : 'todo'
}

function freezeEntries(entries: readonly MatrizPlanEntry[]): readonly MatrizPlanEntry[] {
  const byKey = new Map<string, MatrizPlanEntry>()
  for (const entry of entries) {
    const goalTitle = sanitizePlanLabel(entry.goalTitle)
    const frontTitle = sanitizePlanLabel(entry.frontTitle)
    byKey.set(entry.key, Object.freeze({
      key: entry.key,
      note: sanitizeNote(entry.note),
      status: normalizeStatus(entry.status),
      ...(goalTitle ? { goalTitle } : {}),
      ...(frontTitle ? { frontTitle } : {}),
    }))
  }
  return Object.freeze([...byKey.values()].sort((left, right) => left.key.localeCompare(right.key)))
}

function parseMatrizPlanPayload(
  rawValue: string | null,
  scope: MatrizFrontsScope,
): readonly MatrizPlanEntry[] | null {
  if (!rawValue) return null
  try {
    const value: unknown = JSON.parse(rawValue)
    if (
      !isRecord(value)
      || value.schemaVersion !== MATRIZ_FRONTS_SCHEMA_VERSION
      || value.municipalityIbge7 !== scope.municipalityIbge7
      || value.referenceDate !== scope.referenceDate
      || !Array.isArray(value.entries)
    ) return null
    const entries = value.entries.flatMap((item): MatrizPlanEntry[] => {
      if (!isRecord(item) || typeof item.key !== 'string' || !FRENTE_KEY_PATTERN.test(item.key)) {
        return []
      }
      return [{
        key: item.key,
        note: sanitizeNote(item.note),
        status: normalizeStatus(item.status),
        goalTitle: sanitizePlanLabel(item.goalTitle),
        frontTitle: sanitizePlanLabel(item.frontTitle),
      }]
    })
    return freezeEntries(entries)
  } catch {
    return null
  }
}

function parseLegacyMatrizPlanPayloadV4(
  rawValue: string | null,
  scope: MatrizFrontsScope,
): readonly MatrizPlanEntry[] | null {
  if (!rawValue) return null
  try {
    const value: unknown = JSON.parse(rawValue)
    if (
      !isRecord(value)
      || value.schemaVersion !== MATRIZ_FRONTS_LEGACY_SCHEMA_VERSION_V4
      || value.municipalityIbge7 !== scope.municipalityIbge7
      || value.referenceDate !== scope.referenceDate
      || !Array.isArray(value.entries)
    ) return null
    return freezeEntries(value.entries.flatMap((item): MatrizPlanEntry[] => {
      if (!isRecord(item) || typeof item.key !== 'string' || !FRENTE_KEY_PATTERN.test(item.key)) {
        return []
      }
      return [{
        key: item.key,
        note: sanitizeNote(item.note),
        status: normalizeStatus(item.status),
      }]
    }))
  } catch {
    return null
  }
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

export function matrizPlanStorageKey({ municipalityIbge7, referenceDate }: MatrizFrontsScope): string {
  return `${MATRIZ_FRONTS_STORAGE_KEY_PREFIX}:${municipalityIbge7}:${referenceDate}`
}

export function parseMatrizPlan(
  rawValue: string | null,
  scope: MatrizFrontsScope,
): readonly MatrizPlanEntry[] {
  return parseMatrizPlanPayload(rawValue, scope) ?? Object.freeze([])
}

export function parseLegacyMatrizFrontsV3(
  rawValue: string | null,
  scope: MatrizFrontsScope,
): readonly string[] {
  if (!rawValue) return Object.freeze([])
  try {
    const value: unknown = JSON.parse(rawValue)
    if (
      !isRecord(value)
      || value.schemaVersion !== MATRIZ_FRONTS_LEGACY_SCHEMA_VERSION_V3
      || value.municipalityIbge7 !== scope.municipalityIbge7
      || value.referenceDate !== scope.referenceDate
      || !Array.isArray(value.selections)
    ) return Object.freeze([])
    return Object.freeze([...new Set(value.selections.filter(
      (item): item is string => typeof item === 'string' && FRENTE_KEY_PATTERN.test(item),
    ))].sort())
  } catch {
    return Object.freeze([])
  }
}

export function serializeMatrizPlan(
  scope: MatrizFrontsScope,
  entries: readonly MatrizPlanEntry[],
): string {
  if (!IBGE7_PATTERN.test(scope.municipalityIbge7) || !ISO_DATE_PATTERN.test(scope.referenceDate)) {
    throw new Error('Escopo inválido para o plano da matriz.')
  }
  if (entries.some((entry) => !isRecord(entry) || typeof entry.key !== 'string' || !FRENTE_KEY_PATTERN.test(entry.key))) {
    throw new Error('Chave inválida para o plano da matriz.')
  }
  const payload: MatrizPlanPayload = {
    schemaVersion: MATRIZ_FRONTS_SCHEMA_VERSION,
    municipalityIbge7: scope.municipalityIbge7,
    referenceDate: scope.referenceDate,
    entries: freezeEntries(entries),
  }
  return JSON.stringify(payload)
}

export function getBrowserMatrizStorage(): MunicipalityStorage | null {
  try {
    return globalThis.localStorage ?? null
  } catch {
    return null
  }
}

export function restoreMatrizPlan(
  storage: MunicipalityStorage | null,
  scope: MatrizFrontsScope,
): readonly MatrizPlanEntry[] {
  if (!storage) return Object.freeze([])
  const current = parseMatrizPlanPayload(safeGet(storage, matrizPlanStorageKey(scope)), scope)
  if (current !== null) return current

  const legacyV4Key = `${MATRIZ_FRONTS_LEGACY_KEY_PREFIX_V4}:${scope.municipalityIbge7}:${scope.referenceDate}`
  const legacyV4 = parseLegacyMatrizPlanPayloadV4(safeGet(storage, legacyV4Key), scope)
  if (legacyV4 !== null) {
    if (safeSet(storage, matrizPlanStorageKey(scope), serializeMatrizPlan(scope, legacyV4))) {
      safeRemove(storage, legacyV4Key)
    }
    return legacyV4
  }

  const legacyKey = `${MATRIZ_FRONTS_LEGACY_KEY_PREFIX_V3}:${scope.municipalityIbge7}:${scope.referenceDate}`
  const migrated = freezeEntries(parseLegacyMatrizFrontsV3(safeGet(storage, legacyKey), scope).map((key) => ({
    key,
    note: '',
    status: 'todo',
  })))
  if (migrated.length > 0 && safeSet(storage, matrizPlanStorageKey(scope), serializeMatrizPlan(scope, migrated))) {
    safeRemove(storage, legacyKey)
  }
  return migrated
}

function isEnumerableMatrizStorage(storage: MunicipalityStorage): storage is EnumerableMatrizStorage {
  const candidate = storage as Partial<EnumerableMatrizStorage>
  return typeof candidate.length === 'number' && typeof candidate.key === 'function'
}

function parseStoredPlanKey(key: string): (MatrizFrontsScope & { prefix: string }) | null {
  for (const prefix of STORAGE_PREFIX_PRIORITY.keys()) {
    const match = key.match(new RegExp(`^${prefix}:(\\d{7}):(\\d{4}-\\d{2}-\\d{2})$`, 'u'))
    if (match) {
      return {
        prefix,
        municipalityIbge7: match[1],
        referenceDate: match[2],
      }
    }
  }
  return null
}

function parseStoredPlan(
  rawValue: string | null,
  scope: MatrizFrontsScope,
  prefix: string,
): readonly MatrizPlanEntry[] | null {
  if (prefix === MATRIZ_FRONTS_STORAGE_KEY_PREFIX) return parseMatrizPlanPayload(rawValue, scope)
  if (prefix === MATRIZ_FRONTS_LEGACY_KEY_PREFIX_V4) return parseLegacyMatrizPlanPayloadV4(rawValue, scope)
  if (prefix === MATRIZ_FRONTS_LEGACY_KEY_PREFIX_V3) {
    if (!rawValue) return null
    return freezeEntries(parseLegacyMatrizFrontsV3(rawValue, scope).map((key) => ({
      key,
      note: '',
      status: 'todo',
    })))
  }
  return null
}

/** Localiza somente o plano não vazio mais recente anterior à leitura atual. */
export function findPreviousMatrizPlan(
  storage: MunicipalityStorage | null,
  currentScope: MatrizFrontsScope,
): PreviousMatrizPlan | null {
  if (!storage || !isEnumerableMatrizStorage(storage)) return null
  const byDate = new Map<string, { plan: PreviousMatrizPlan; priority: number }>()

  try {
    for (let index = 0; index < storage.length; index += 1) {
      const key = storage.key(index)
      if (!key) continue
      const storedScope = parseStoredPlanKey(key)
      if (
        !storedScope
        || storedScope.municipalityIbge7 !== currentScope.municipalityIbge7
        || storedScope.referenceDate >= currentScope.referenceDate
      ) continue
      const entries = parseStoredPlan(safeGet(storage, key), storedScope, storedScope.prefix)
      if (!entries || entries.length === 0) continue
      const priority = STORAGE_PREFIX_PRIORITY.get(storedScope.prefix) ?? 0
      const previous = byDate.get(storedScope.referenceDate)
      if (!previous || priority > previous.priority) {
        byDate.set(storedScope.referenceDate, {
          plan: Object.freeze({
            entries,
            referenceDate: storedScope.referenceDate,
          }),
          priority,
        })
      }
    }
  } catch {
    return null
  }

  const sortedDates = [...byDate.keys()].sort()
  const latestDate = sortedDates[sortedDates.length - 1]
  return latestDate ? byDate.get(latestDate)?.plan ?? null : null
}

export function reconcileMatrizPlanEntries(
  entries: readonly MatrizPlanEntry[],
  availableFrontKeys: ReadonlySet<string>,
): MatrizPlanReconciliation {
  return Object.freeze({
    kept: freezeEntries(entries.filter((entry) => availableFrontKeys.has(entry.key))),
    removed: freezeEntries(entries.filter((entry) => !availableFrontKeys.has(entry.key))),
  })
}

export function persistMatrizPlan(
  storage: MunicipalityStorage | null,
  scope: MatrizFrontsScope,
  entries: readonly MatrizPlanEntry[],
): boolean {
  if (!storage) return false
  const key = matrizPlanStorageKey(scope)
  if (entries.length === 0) {
    safeRemove(storage, key)
    return true
  }
  return safeSet(storage, key, serializeMatrizPlan(scope, entries))
}
