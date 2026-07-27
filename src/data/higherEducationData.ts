import type {
  HigherEducationManifest,
  HigherEducationMunicipalDocument,
} from '../features/education/higherEducationTypes.js'
import {
  validateHigherEducationManifest,
  validateHigherEducationMunicipalDocument,
} from './higherEducationValidation.js'

const MANIFEST_URL = '/data/educacao/superior/index.json'
const MUNICIPAL_BASE_URL = '/data/educacao/superior/municipios'

export class HigherEducationDataNotFoundError extends Error {
  constructor(public readonly url: string) {
    super(`Dados de Educação Superior não encontrados em ${url}.`)
    this.name = 'HigherEducationDataNotFoundError'
  }
}

export class HigherEducationInvalidDataError extends Error {
  constructor(public readonly url: string, cause: unknown) {
    super(`Dados de Educação Superior inválidos em ${url}: ${cause instanceof Error ? cause.message : 'erro desconhecido'}`)
    this.name = 'HigherEducationInvalidDataError'
  }
}

let manifestPromise: Promise<HigherEducationManifest> | null = null
const municipalPromises = new Map<string, Promise<HigherEducationMunicipalDocument>>()

async function fetchJson(url: string): Promise<unknown> {
  const response = await fetch(url)
  if (response.status === 404) throw new HigherEducationDataNotFoundError(url)
  if (!response.ok) throw new Error(`Falha HTTP ${response.status} ao carregar ${url}.`)
  try {
    return await response.json()
  } catch (error) {
    throw new HigherEducationInvalidDataError(url, error)
  }
}

export function loadHigherEducationManifest(): Promise<HigherEducationManifest> {
  if (!manifestPromise) {
    manifestPromise = fetchJson(MANIFEST_URL)
      .then((value) => {
        try {
          return validateHigherEducationManifest(value)
        } catch (error) {
          throw new HigherEducationInvalidDataError(MANIFEST_URL, error)
        }
      })
      .catch((error) => {
        manifestPromise = null
        throw error
      })
  }
  return manifestPromise
}

export function loadHigherEducationMunicipality(
  municipalityId: string,
): Promise<HigherEducationMunicipalDocument> {
  const normalizedId = String(municipalityId)
  const cached = municipalPromises.get(normalizedId)
  if (cached) return cached
  const url = `${MUNICIPAL_BASE_URL}/${encodeURIComponent(normalizedId)}.json`
  const promise = Promise.all([loadHigherEducationManifest(), fetchJson(url)])
    .then(([manifest, value]) => {
      try {
        return validateHigherEducationMunicipalDocument(value, normalizedId, manifest)
      } catch (error) {
        throw new HigherEducationInvalidDataError(url, error)
      }
    })
    .catch((error) => {
      municipalPromises.delete(normalizedId)
      throw error
    })
  municipalPromises.set(normalizedId, promise)
  return promise
}

export function clearHigherEducationDataCache() {
  manifestPromise = null
  municipalPromises.clear()
}
