import {
  PNE_2026_CONTRACT_HASH,
  PNE_2026_PRESENTATION_POLICY_HASH,
  PNE_2026_PUBLIC_DIAGNOSTIC_V3_SCHEMA,
  parsePne2026PublicDiagnosticV3,
  resolvePne2026PublicDiagnosticV3,
} from './pne2026PublicDiagnosticV3.js'

export const PNE_2026_DIAGNOSTIC_V3_CURRENT_PATH =
  '/data/pne2026-diagnostic-v3/current.json'
export const PNE_2026_DIAGNOSTIC_V3_RELEASE_MANIFEST_PATH =
  '/data/pne2026-diagnostic-v3/releases/{releaseId}/manifest.json'
export const PNE_2026_DIAGNOSTIC_V3_RELEASE_MUNICIPAL_PATH =
  '/data/pne2026-diagnostic-v3/releases/{releaseId}/municipios/{municipalityId}.json'

const POINTER_SCHEMA = 'pne2026-diagnostic-release-pointer-v1'
const RELEASE_MANIFEST_SCHEMA =
  'pne2026-public-diagnostic-v3-release-manifest-v3'
const CONTRACT_VERSION = '1.9.0'
const PRESENTATION_POLICY_VERSION = '1.7.0'
const MUNICIPAL_FILE_PATTERN = 'municipios/{municipalityId}.json'
const SHA256_PATTERN = /^[a-f0-9]{64}$/
const POINTER_FIELDS = new Set([
  'schemaVersion',
  'releaseId',
  'manifestPath',
  'aggregateHash',
  'contractVersion',
  'contractHash',
  'presentationPolicyVersion',
  'presentationPolicyHash',
])
const RELEASE_MANIFEST_FIELDS = new Set([
  'schemaVersion',
  'diagnosticSchemaVersion',
  'contractVersion',
  'contractHash',
  'presentationPolicyVersion',
  'presentationPolicyHash',
  'municipalityCount',
  'resultCount',
  'progressResultCount',
  'trackingResultCount',
  'complementaryResultCount',
  'legalReferenceResultCount',
  'monitoringReferenceResultCount',
  'dataStatusCounts',
  'classificationCounts',
  'presentationPriorityCounts',
  'minimumResultsPerMunicipality',
  'maximumResultsPerMunicipality',
  'percentValuesAbove100Count',
  'countValuesAbove100Count',
  'hiddenExcludedCount',
  'aggregateHash',
  'semanticHash',
  'municipalFilePattern',
])
const FIXED_RELEASE_IDENTITY = Object.freeze({
  schemaVersion: RELEASE_MANIFEST_SCHEMA,
  diagnosticSchemaVersion: PNE_2026_PUBLIC_DIAGNOSTIC_V3_SCHEMA,
  contractVersion: CONTRACT_VERSION,
  contractHash: PNE_2026_CONTRACT_HASH,
  presentationPolicyVersion: PRESENTATION_POLICY_VERSION,
  presentationPolicyHash: PNE_2026_PRESENTATION_POLICY_HASH,
  municipalFilePattern: MUNICIPAL_FILE_PATTERN,
})

function invariant(condition, message) {
  if (!condition) throw new TypeError(`Publicação PNE V3 inválida: ${message}`)
}

function isObject(value) {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value)
}

function canonicalJson(value) {
  if (Array.isArray(value)) return value.map(canonicalJson)
  if (!isObject(value)) return value
  return Object.fromEntries(
    Object.keys(value)
      .sort()
      .map((key) => [key, canonicalJson(value[key])]),
  )
}

function validateExactFields(candidate, expected, label) {
  invariant(isObject(candidate), `${label} deve ser objeto.`)
  const unknown = Object.keys(candidate).filter((field) => !expected.has(field))
  const missing = [...expected].filter((field) => !Object.hasOwn(candidate, field))
  invariant(!unknown.length, `${label} contém campos desconhecidos: ${unknown.join(', ')}.`)
  invariant(!missing.length, `${label} não contém: ${missing.join(', ')}.`)
}

function memoized(cache, key, producer) {
  if (cache.has(key)) return cache.get(key)
  const pending = Promise.resolve().then(producer)
  cache.set(key, pending)
  pending.catch(() => {
    if (cache.get(key) === pending) cache.delete(key)
  })
  return pending
}

async function defaultFetchJson(path, options) {
  const response = await fetch(path, options)
  if (!response.ok) {
    throw new Error(`Erro ao carregar ${path} (${response.status})`)
  }
  return response.json()
}

export class Pne2026DiagnosticLoadError extends Error {
  constructor(message, {
    cause,
    code,
    municipalityId = null,
    path = null,
    stage,
  }) {
    super(message, { cause })
    this.name = 'Pne2026DiagnosticLoadError'
    this.code = code
    this.stage = stage
    this.municipalityId = municipalityId
    this.path = path
  }
}

function structuredError(error, details) {
  if (error instanceof Pne2026DiagnosticLoadError) return error
  return new Pne2026DiagnosticLoadError(
    error instanceof Error ? error.message : String(error),
    { ...details, cause: error },
  )
}

export function parsePne2026DiagnosticReleasePointer(candidate) {
  validateExactFields(candidate, POINTER_FIELDS, 'current.json')
  invariant(candidate.schemaVersion === POINTER_SCHEMA, 'schema do ponteiro divergente.')
  invariant(SHA256_PATTERN.test(candidate.releaseId), 'releaseId inválido.')
  invariant(
    candidate.aggregateHash === candidate.releaseId,
    'aggregateHash diverge de releaseId.',
  )
  const expectedManifestPath = `releases/${candidate.releaseId}/manifest.json`
  invariant(
    candidate.manifestPath === expectedManifestPath,
    'manifestPath não está confinado ao release ativo.',
  )
  invariant(
    !candidate.manifestPath.includes('..')
      && !candidate.manifestPath.startsWith('/')
      && !/^[a-z]+:/i.test(candidate.manifestPath),
    'manifestPath inseguro.',
  )
  for (const [field, expected] of Object.entries({
    contractVersion: CONTRACT_VERSION,
    contractHash: PNE_2026_CONTRACT_HASH,
    presentationPolicyVersion: PRESENTATION_POLICY_VERSION,
    presentationPolicyHash: PNE_2026_PRESENTATION_POLICY_HASH,
  })) {
    invariant(candidate[field] === expected, `${field} divergente.`)
  }
  return structuredClone(candidate)
}

export function parsePne2026DiagnosticV3Manifest(
  candidate,
  pointer,
  expectedMunicipalityCount,
) {
  validateExactFields(candidate, RELEASE_MANIFEST_FIELDS, 'manifesto do release')
  for (const [field, expected] of Object.entries(FIXED_RELEASE_IDENTITY)) {
    invariant(
      JSON.stringify(canonicalJson(candidate[field]))
        === JSON.stringify(canonicalJson(expected)),
      `manifesto diverge em ${field}.`,
    )
  }
  invariant(SHA256_PATTERN.test(candidate.aggregateHash), 'aggregateHash inválido.')
  invariant(SHA256_PATTERN.test(candidate.semanticHash), 'semanticHash inválido.')
  invariant(
    Number.isInteger(expectedMunicipalityCount) && expectedMunicipalityCount > 0,
    'expectedMunicipalityCount inválido.',
  )
  invariant(
    candidate.municipalityCount === expectedMunicipalityCount,
    'municipalityCount divergente.',
  )
  const nonNegativeInteger = (value) => (
    Number.isInteger(value) && value >= 0
  )
  for (const field of [
    'resultCount',
    'progressResultCount',
    'trackingResultCount',
    'complementaryResultCount',
    'legalReferenceResultCount',
    'monitoringReferenceResultCount',
    'minimumResultsPerMunicipality',
    'maximumResultsPerMunicipality',
    'percentValuesAbove100Count',
    'countValuesAbove100Count',
    'hiddenExcludedCount',
  ]) {
    invariant(nonNegativeInteger(candidate[field]), `${field} inválido.`)
  }
  invariant(
    candidate.resultCount
      === candidate.progressResultCount
        + candidate.trackingResultCount
        + candidate.complementaryResultCount,
    'contagens de modo não reconciliam.',
  )
  invariant(
    candidate.legalReferenceResultCount <= candidate.progressResultCount
      && candidate.monitoringReferenceResultCount <= candidate.trackingResultCount,
    'contagens por tipo de referência excedem os modos.',
  )
  invariant(
    isObject(candidate.classificationCounts)
      && Object.keys(candidate.classificationCounts).toSorted().join(',')
        === 'advance,maintain,unclassified'
      && Object.values(candidate.classificationCounts).every(nonNegativeInteger)
      && Object.values(candidate.classificationCounts)
        .reduce((total, value) => total + value, 0)
        === candidate.legalReferenceResultCount,
    'classificationCounts inválido.',
  )
  invariant(
    isObject(candidate.dataStatusCounts)
      && Object.keys(candidate.dataStatusCounts).toSorted().join(',')
        === 'available,not_applicable,suppressed,unavailable'
      && Object.values(candidate.dataStatusCounts).every(nonNegativeInteger)
      && Object.values(candidate.dataStatusCounts)
        .reduce((total, value) => total + value, 0)
        === candidate.resultCount,
    'dataStatusCounts inválido.',
  )
  invariant(
    isObject(candidate.presentationPriorityCounts)
      && Object.keys(candidate.presentationPriorityCounts).toSorted().join(',')
        === 'essential,standard'
      && Object.values(candidate.presentationPriorityCounts).every(nonNegativeInteger)
      && Object.values(candidate.presentationPriorityCounts)
        .reduce((total, value) => total + value, 0)
        === candidate.resultCount,
    'presentationPriorityCounts inválido.',
  )
  invariant(
    candidate.minimumResultsPerMunicipality
      <= candidate.maximumResultsPerMunicipality,
    'intervalo municipal inválido.',
  )
  invariant(
    candidate.aggregateHash === pointer.releaseId
      && candidate.aggregateHash === pointer.aggregateHash,
    'manifesto não corresponde ao ponteiro ativo.',
  )
  return structuredClone(candidate)
}

/**
 * @param {{
 *   expectedMunicipalityCount?: number,
 *   fetchJson?: (path: any, options: any) => Promise<any>,
 *   logger?: (...data: any[]) => void,
 * }} [options]
 */
export function createPne2026DiagnosticLoader({
  expectedMunicipalityCount,
  fetchJson = defaultFetchJson,
  logger = console.error,
} = {}) {
  const manifestCache = new Map()
  const v3Cache = new Map()
  const reportedErrors = new Set()
  let currentPending = null

  function reportOnce(error) {
    const key = [
      error.code,
      error.stage,
      error.municipalityId,
      error.path,
      error.message,
    ].join(':')
    if (reportedErrors.has(key)) return
    reportedErrors.add(key)
    logger(error)
  }

  function loadCurrent() {
    if (currentPending) return currentPending
    currentPending = Promise.resolve()
      .then(() => fetchJson(
        PNE_2026_DIAGNOSTIC_V3_CURRENT_PATH,
        { cache: 'no-store' },
      ))
      .catch((error) => {
        throw structuredError(error, {
          code: 'current_unavailable',
          path: PNE_2026_DIAGNOSTIC_V3_CURRENT_PATH,
          stage: 'current',
        })
      })
      .then((candidate) => {
        try {
          return parsePne2026DiagnosticReleasePointer(candidate)
        } catch (error) {
          throw structuredError(error, {
            code: 'invalid_pointer',
            path: PNE_2026_DIAGNOSTIC_V3_CURRENT_PATH,
            stage: 'current',
          })
        }
      })
      .finally(() => {
        currentPending = null
      })
    return currentPending
  }

  function releaseManifestPath(releaseId) {
    return PNE_2026_DIAGNOSTIC_V3_RELEASE_MANIFEST_PATH.replace(
      '{releaseId}',
      releaseId,
    )
  }

  function releaseMunicipalPath(releaseId, municipalityId) {
    return PNE_2026_DIAGNOSTIC_V3_RELEASE_MUNICIPAL_PATH
      .replace('{releaseId}', releaseId)
      .replace('{municipalityId}', municipalityId)
  }

  function loadManifest(pointer) {
    return memoized(manifestCache, pointer.releaseId, async () => {
      const path = releaseManifestPath(pointer.releaseId)
      let candidate
      try {
        candidate = await fetchJson(path)
      } catch (error) {
        throw structuredError(error, {
          code: 'release_unavailable',
          path,
          stage: 'manifest',
        })
      }
      try {
        return parsePne2026DiagnosticV3Manifest(
          candidate,
          pointer,
          expectedMunicipalityCount,
        )
      } catch (error) {
        throw structuredError(error, {
          code: 'invalid_manifest',
          path,
          stage: 'manifest',
        })
      }
    })
  }

  async function loadResolvedV3(municipalityId) {
    const pointer = await loadCurrent()
    await loadManifest(pointer)
    const key = `${pointer.releaseId}:${municipalityId}`
    return memoized(v3Cache, key, async () => {
      const path = releaseMunicipalPath(pointer.releaseId, municipalityId)
      let candidate
      try {
        candidate = await fetchJson(path)
      } catch (error) {
        throw structuredError(error, {
          code: 'municipality_unavailable',
          municipalityId,
          path,
          stage: 'municipality',
        })
      }
      try {
        const payload = parsePne2026PublicDiagnosticV3(candidate)
        if (payload.municipality.id !== municipalityId) {
          throw new Error(
            `Diagnóstico PNE V3 municipal divergente: ${municipalityId}.`,
          )
        }
        return {
          releaseId: pointer.releaseId,
          viewModel: resolvePne2026PublicDiagnosticV3(payload),
        }
      } catch (error) {
        throw structuredError(error, {
          code: 'invalid_payload',
          municipalityId,
          path,
          stage: 'municipality',
        })
      }
    })
  }

  function v3Result(municipalityId, resolved) {
    return {
      schemaVersion: 'pne2026-diagnostic-loader-result-v1',
      municipalityId,
      municipalityName: resolved.viewModel.municipalityName,
      diagnosticSource: 'v3',
      diagnosticReleaseId: resolved.releaseId,
      pne2026PublicDiagnostic: resolved.viewModel,
    }
  }

  function load(municipalityId) {
    const normalizedId = String(municipalityId)
    if (!/^\d{7}$/.test(normalizedId)) {
      const error = new Pne2026DiagnosticLoadError(
        `Código municipal inválido: ${normalizedId}.`,
        {
          code: 'invalid_municipality',
          municipalityId: normalizedId,
          stage: 'input',
        },
      )
      reportOnce(error)
      return Promise.reject(error)
    }
    return loadResolvedV3(normalizedId)
      .then((resolved) => v3Result(normalizedId, resolved))
      .catch((error) => {
        const structured = structuredError(error, {
          code: 'diagnostic_unavailable',
          municipalityId: normalizedId,
          stage: 'load',
        })
        if (structured.municipalityId === null) {
          structured.municipalityId = normalizedId
        }
        reportOnce(structured)
        throw structured
      })
  }

  return { load }
}
