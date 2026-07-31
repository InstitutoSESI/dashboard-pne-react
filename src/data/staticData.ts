import type {
  IndicadoresPayload,
  MunicipioData,
  MunicipiosIndexPayload,
  MunicipiosPayload,
} from '../types/data'
import type { MunicipalInequalityDocument } from '../types/municipalInequality'

type JsonObject = Record<string, unknown>

const dataCache = new Map<string, unknown>()
const pendingCache = new Map<string, Promise<unknown>>()

export function loadJson<T>(path: string, validate?: (data: T) => unknown): Promise<T> {
  if (dataCache.has(path)) {
    // The cache is keyed by the complete path, so this is the single typed boundary for cached JSON.
    return Promise.resolve(dataCache.get(path) as T)
  }

  if (pendingCache.has(path)) {
    // A pending request for the same path has the same public payload contract.
    return pendingCache.get(path) as Promise<T>
  }

  const promise: Promise<T> = fetch(path)
    .then(async (response) => {
      if (!response.ok) {
        throw new Error(`Erro ao carregar ${path} (${response.status})`)
      }
      // JSON is untrusted at this boundary; detailed runtime validation is intentionally deferred.
      const data = await response.json() as T
      validate?.(data)
      dataCache.set(path, data)
      return data
    })
    .catch((error: unknown) => {
      throw error instanceof Error
        ? error
        : new Error(`Erro ao carregar ${path}: ${String(error)}`)
    })
    .finally(() => {
      pendingCache.delete(path)
    })

  pendingCache.set(path, promise)
  return promise
}

export function loadMunicipios(): Promise<MunicipiosPayload> {
  return loadJson<MunicipiosPayload>('/data/municipios.json')
}

export function loadIndicadores(): Promise<IndicadoresPayload> {
  return loadJson<IndicadoresPayload>('/data/indicadores.json')
}

export function loadMunicipiosIndex(): Promise<MunicipiosIndexPayload> {
  return loadJson<MunicipiosIndexPayload>('/data/municipios_index.json')
}

export function loadMunicipioData(idMunicipio: string): Promise<MunicipioData> {
  return loadJson<MunicipioData>(`/data/municipios/${idMunicipio}/index.json`)
}

export function loadMunicipioInequality(idMunicipio: string): Promise<MunicipalInequalityDocument> {
  return loadJson<MunicipalInequalityDocument>(`/data/municipios/${idMunicipio}/diagnostico.json`)
}

export function loadMunicipioDetails(idMunicipio: string): Promise<JsonObject> {
  if (!idMunicipio) return Promise.resolve({})
  return loadJson<JsonObject>(`/data/municipios/${idMunicipio}/details.json`).catch(() => ({}))
}

export function loadIndicatorDetail(idMunicipio: string, indicatorKey: string): Promise<unknown | null> {
  if (!indicatorKey) return Promise.resolve(null)
  return loadMunicipioDetails(idMunicipio).then((details) => details[indicatorKey] ?? null)
}

export function loadPneStateReference(cycle = 'pne_2026_2036'): Promise<unknown> {
  return loadJson<unknown>(`/data/${cycle}/referencia_estadual.json`)
}

export function primeMunicipioCache(idMunicipio: string, data: MunicipioData): void {
  if (!idMunicipio) return
  dataCache.set(`/data/municipios/${idMunicipio}/index.json`, data)
}

export function loadMunicipioSharedInfo(idMunicipio: string, sectionKey: string): Promise<unknown | null> {
  if (!idMunicipio || !sectionKey) return Promise.resolve(null)
  return loadJson<JsonObject>(`/data/municipios/${idMunicipio}/details.json`).then(
    (details) => {
      const shared = details._shared
      return shared && typeof shared === 'object'
        ? (shared as JsonObject)[sectionKey] ?? null
        : null
    },
    () => null,
  )
}
