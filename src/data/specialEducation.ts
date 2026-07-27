import {
  SPECIAL_EDUCATION_CUTS,
  SPECIAL_EDUCATION_SCHEMA_VERSION,
  type SpecialEducationManifest,
  type SpecialEducationMunicipalDocument,
  type SpecialEducationPoint,
} from '../features/education/specialEducationTypes.js'

const MANIFEST_URL = '/data/educacao/educacao-especial/index.json'
const MUNICIPAL_BASE_URL = '/data/educacao/educacao-especial/municipios'
const VALID_STATES = new Set(['observed', 'derived_zero', 'partial', 'unavailable', 'not_applicable'])

let manifestPromise: Promise<SpecialEducationManifest> | null = null
const municipalityPromises = new Map<string, Promise<SpecialEducationMunicipalDocument>>()

export class SpecialEducationDataError extends Error {
  constructor(message: string, public readonly url: string) {
    super(message)
    this.name = 'SpecialEducationDataError'
  }
}

async function fetchJson(url: string): Promise<unknown> {
  const response = await fetch(url)
  if (!response.ok) throw new SpecialEducationDataError(`Falha HTTP ${response.status} ao carregar os dados.`, url)
  try {
    return await response.json()
  } catch {
    throw new SpecialEducationDataError('A resposta não contém JSON válido.', url)
  }
}

function object(value: unknown, label: string): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error(`${label} inválido`)
  return value as Record<string, unknown>
}

function point(value: unknown, label: string): SpecialEducationPoint {
  const candidate = object(value, label)
  if (!(candidate.value === null || typeof candidate.value === 'number') || !Number.isFinite(candidate.value ?? 0)) {
    throw new Error(`${label}.value inválido`)
  }
  if (typeof candidate.state !== 'string' || !VALID_STATES.has(candidate.state)) throw new Error(`${label}.state inválido`)
  if (typeof candidate.sourceId !== 'string') throw new Error(`${label}.sourceId inválido`)
  return candidate as unknown as SpecialEducationPoint
}

function pointRecord(value: unknown, label: string, nestedStages = false) {
  const candidate = object(value, label)
  Object.entries(candidate).forEach(([key, item]) => {
    if (nestedStages && key === 'stages') {
      const stages = object(item, `${label}.stages`)
      Object.entries(stages).forEach(([stage, stagePoint]) => point(stagePoint, `${label}.stages.${stage}`))
    } else {
      point(item, `${label}.${key}`)
    }
  })
}

export function validateSpecialEducationManifest(value: unknown): SpecialEducationManifest {
  const manifest = object(value, 'manifesto')
  if (manifest.schemaVersion !== SPECIAL_EDUCATION_SCHEMA_VERSION) throw new Error('schemaVersion incompatível')
  if (typeof manifest.contentHash !== 'string' || !manifest.contentHash) throw new Error('contentHash ausente')
  if (!Array.isArray(manifest.years) || !manifest.years.every(Number.isInteger)) throw new Error('anos inválidos')
  const manifestCuts = manifest.cuts
  if (!Array.isArray(manifestCuts) || SPECIAL_EDUCATION_CUTS.some((cut) => !manifestCuts.includes(cut))) throw new Error('recortes inválidos')
  if (!Number.isInteger(manifest.municipalityCount) || !Number.isInteger(manifest.fileCount)) throw new Error('contagens inválidas')
  return manifest as unknown as SpecialEducationManifest
}

export function validateSpecialEducationMunicipalDocument(
  value: unknown,
  municipalityId: string,
  manifest: SpecialEducationManifest,
): SpecialEducationMunicipalDocument {
  const document = object(value, 'documento municipal')
  const municipality = object(document.municipality, 'município')
  if (document.schemaVersion !== SPECIAL_EDUCATION_SCHEMA_VERSION) throw new Error('schemaVersion incompatível')
  if (String(municipality.code) !== municipalityId) throw new Error('município diferente do solicitado')
  const documentCuts = document.cuts
  if (!Array.isArray(documentCuts) || SPECIAL_EDUCATION_CUTS.some((cut) => !documentCuts.includes(cut))) throw new Error('recortes incompletos')
  if (!Array.isArray(document.years) || document.years.length !== manifest.years.length) throw new Error('série anual incompleta')
  document.years.forEach((rawYear, index) => {
    const year = object(rawYear, `ano ${index}`)
    if (year.year !== manifest.years[index]) throw new Error(`ano ${index} incompatível`)
    const cuts = object(year.cuts, `ano ${year.year}.cuts`)
    SPECIAL_EDUCATION_CUTS.forEach((cut) => {
      const payload = object(cuts[cut], `ano ${year.year}.${cut}`)
      pointRecord(payload.specialEducation, `ano ${year.year}.${cut}.specialEducation`, true)
      point(payload.commonClassInclusionRate, `ano ${year.year}.${cut}.commonClassInclusionRate`)
      pointRecord(payload.aee, `ano ${year.year}.${cut}.aee`)
      pointRecord(payload.bilingualDeafEducation, `ano ${year.year}.${cut}.bilingualDeafEducation`)
    })
  })
  return document as unknown as SpecialEducationMunicipalDocument
}

export function loadSpecialEducationManifest(): Promise<SpecialEducationManifest> {
  if (!manifestPromise) {
    manifestPromise = fetchJson(MANIFEST_URL)
      .then(validateSpecialEducationManifest)
      .catch((error) => {
        manifestPromise = null
        throw new SpecialEducationDataError(
          error instanceof Error ? `Manifesto de Educação Especial inválido: ${error.message}` : 'Manifesto inválido.',
          MANIFEST_URL,
        )
      })
  }
  return manifestPromise
}

export async function loadSpecialEducationMunicipality(
  municipalityId: string,
): Promise<SpecialEducationMunicipalDocument> {
  const normalizedId = String(municipalityId)
  const manifest = await loadSpecialEducationManifest()
  const cacheKey = `${manifest.contentHash}:${normalizedId}`
  const cached = municipalityPromises.get(cacheKey)
  if (cached) return cached
  const url = `${MUNICIPAL_BASE_URL}/${encodeURIComponent(normalizedId)}.json`
  const pending = fetchJson(url)
    .then((value) => validateSpecialEducationMunicipalDocument(value, normalizedId, manifest))
    .catch((error) => {
      municipalityPromises.delete(cacheKey)
      if (error instanceof SpecialEducationDataError) throw error
      throw new SpecialEducationDataError(
        error instanceof Error ? `Dados municipais de Educação Especial inválidos: ${error.message}` : 'Dados municipais inválidos.',
        url,
      )
    })
  municipalityPromises.set(cacheKey, pending)
  return pending
}

export function clearSpecialEducationDataCache() {
  manifestPromise = null
  municipalityPromises.clear()
}
