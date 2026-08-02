import type { StateConfig } from '../config/stateConfig'
import type { MunicipalityId, MunicipalityRef, StateCode } from '../types/data'
import { findUniqueMunicipalityByName, indexMunicipalitiesById } from './municipalityRegistry.js'

export const MUNICIPALITY_STORAGE_KEY = 'pne_dashboard_context_v2'
export const LEGACY_MUNICIPALITY_STORAGE_KEY = 'pne_dashboard_municipio'
export const DASHBOARD_CONTEXT_SCHEMA_VERSION = 'dashboard-context-v2'

export interface DashboardContextV2 {
  readonly schemaVersion: typeof DASHBOARD_CONTEXT_SCHEMA_VERSION
  readonly stateCode: StateCode
  readonly municipalityId: MunicipalityId
}

export interface MunicipalityStorage {
  getItem(key: string): string | null
  setItem(key: string, value: string): void
  removeItem(key: string): void
}

export interface RestoredMunicipalitySelection {
  municipalityId: MunicipalityId | null
  source: 'v2' | 'legacy' | 'none'
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function isStateCode(value: unknown): value is StateCode {
  return typeof value === 'string' && /^[A-Z]{2}$/.test(value)
}

function isMunicipalityId(value: unknown): value is MunicipalityId {
  return typeof value === 'string' && /^\d{7}$/.test(value)
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

export function parseDashboardContextV2(rawValue: string | null): DashboardContextV2 | null {
  if (!rawValue) return null

  try {
    const value: unknown = JSON.parse(rawValue)
    if (
      !isRecord(value)
      || value.schemaVersion !== DASHBOARD_CONTEXT_SCHEMA_VERSION
      || !isStateCode(value.stateCode)
      || !isMunicipalityId(value.municipalityId)
    ) {
      return null
    }
    return Object.freeze({
      schemaVersion: DASHBOARD_CONTEXT_SCHEMA_VERSION,
      stateCode: value.stateCode,
      municipalityId: value.municipalityId,
    })
  } catch {
    return null
  }
}

export function serializeDashboardContextV2(
  stateCode: StateCode,
  municipalityId: MunicipalityId,
): string {
  if (!isStateCode(stateCode) || !isMunicipalityId(municipalityId)) {
    throw new Error('Contexto municipal inválido para serialização.')
  }
  return JSON.stringify({
    schemaVersion: DASHBOARD_CONTEXT_SCHEMA_VERSION,
    stateCode,
    municipalityId,
  })
}

export function getBrowserMunicipalityStorage(): MunicipalityStorage | null {
  try {
    return globalThis.localStorage ?? null
  } catch {
    return null
  }
}

export function restoreMunicipalitySelection(
  storage: MunicipalityStorage | null,
  municipalities: readonly MunicipalityRef[],
  activeState: StateConfig,
): RestoredMunicipalitySelection {
  if (!storage) return { municipalityId: null, source: 'none' }

  const municipalitiesById = indexMunicipalitiesById(municipalities)
  const storedV2 = safeGet(storage, MUNICIPALITY_STORAGE_KEY)
  if (storedV2 !== null) {
    const context = parseDashboardContextV2(storedV2)
    if (
      context
      && context.stateCode === activeState.stateCode
      && municipalitiesById.has(context.municipalityId)
    ) {
      safeRemove(storage, LEGACY_MUNICIPALITY_STORAGE_KEY)
      return { municipalityId: context.municipalityId, source: 'v2' }
    }
    safeRemove(storage, MUNICIPALITY_STORAGE_KEY)
  }

  const legacyName = safeGet(storage, LEGACY_MUNICIPALITY_STORAGE_KEY)
  if (legacyName !== null) {
    const municipality = findUniqueMunicipalityByName(municipalities, legacyName)
    safeRemove(storage, LEGACY_MUNICIPALITY_STORAGE_KEY)
    if (municipality) {
      safeSet(
        storage,
        MUNICIPALITY_STORAGE_KEY,
        serializeDashboardContextV2(activeState.stateCode, municipality.ibgeCode),
      )
      return { municipalityId: municipality.ibgeCode, source: 'legacy' }
    }
  }

  return { municipalityId: null, source: 'none' }
}

export function persistMunicipalitySelection(
  storage: MunicipalityStorage | null,
  municipalities: readonly MunicipalityRef[],
  activeState: StateConfig,
  municipalityId: MunicipalityId | null,
): boolean {
  if (!storage) return false

  if (municipalityId === null) {
    safeRemove(storage, MUNICIPALITY_STORAGE_KEY)
    safeRemove(storage, LEGACY_MUNICIPALITY_STORAGE_KEY)
    return true
  }

  const municipalitiesById = indexMunicipalitiesById(municipalities)
  if (!municipalitiesById.has(municipalityId)) return false

  const saved = safeSet(
    storage,
    MUNICIPALITY_STORAGE_KEY,
    serializeDashboardContextV2(activeState.stateCode, municipalityId),
  )
  if (saved) safeRemove(storage, LEGACY_MUNICIPALITY_STORAGE_KEY)
  return saved
}
