import { createHash } from 'node:crypto'

import {
  parseVocacoesPneNarrative,
  VOCACOES_PNE_NARRATIVE_CONTRACT_VERSION,
  VOCACOES_PNE_NARRATIVE_SCHEMA,
} from '../../src/features/vocacoes-regiao/vocacoesPneNarrativeContract.js'

export const VOCACOES_PNE_PUBLICATION_QUEUE_SCHEMA =
  'vocacoes-pne-publication-queue-v1'
export const VOCACOES_PNE_TRANSFER_COVERAGE_SCHEMA =
  'vocacoes-pne-transfer-coverage-r9-v1'
export const VOCACOES_PNE_PUBLICATION_ENGINE_VERSION =
  'vocacoes-pne-publication-engine-v1.0.0'

export const VOCACOES_PNE_PUBLICATION_REASON_CODES = Object.freeze({
  FIRST_OUTPUT_ARTIFACT_MISSING: 'FIRST_OUTPUT_ARTIFACT_MISSING',
  SECOND_OUTPUT_ARTIFACT_MISSING: 'SECOND_OUTPUT_ARTIFACT_MISSING',
  TRANSFER_NOT_AUDITED: 'TRANSFER_NOT_AUDITED',
  NARRATIVE_ROLLED_BACK: 'NARRATIVE_ROLLED_BACK',
})

const EXPECTED_REGION_COUNT = 10
const REGISTRY_SCHEMA = 'vocacoes-pne-narrative-registry-v1'
const LEGACY_MANIFEST_SCHEMA = 'vocacoes-regiao-manifest-v2'
const LEGACY_DOCUMENT_SCHEMA = 'vocacoes-regiao-2.9.0'
const SHA256_PATTERN = /^[a-f0-9]{64}$/u
const REGISTRY_ENTRY_FIELDS = [
  'slug',
  'name',
  'stateCode',
  'municipalityCount',
  'narrativeSchemaVersion',
  'narrativeContractVersion',
  'legacySourceVersion',
  'legacyContentVersion',
  'narrativeByteSize',
  'narrativeSha256',
  'status',
]
const DOCUMENT_FIELDS = ['path', 'raw']
const COVERAGE_FIELDS = [
  'slug',
  'auditStatus',
  'firstOutputArtifactStatus',
  'secondOutputArtifactStatus',
]
const STATUS_VALUES = new Set(['published', 'rolled_back'])
const AUDIT_STATUS_VALUES = new Set(['complete', 'not_audited'])
const ARTIFACT_STATUS_VALUES = new Set(['available', 'missing', 'not_audited'])

export class VocacoesPnePublicationError extends Error {
  constructor(message, options) {
    super(message, options)
    this.name = 'VocacoesPnePublicationError'
  }
}

function fail(message, options) {
  throw new VocacoesPnePublicationError(message, options)
}

function isRecord(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
}

function assertRecord(value, label) {
  if (!isRecord(value)) fail(`${label} deve ser objeto`)
}

function assertExactKeys(value, expected, label) {
  assertRecord(value, label)
  const actual = Object.keys(value).sort()
  const wanted = [...expected].sort()
  if (
    actual.length !== wanted.length
    || actual.some((key, index) => key !== wanted[index])
  ) {
    fail(`${label} contém campos extras ou ausentes; esperados: ${expected.join(', ')}`)
  }
}

function assertNonEmptyString(value, label) {
  if (typeof value !== 'string' || value.trim().length === 0) {
    fail(`${label} deve ser string não vazia`)
  }
  return value
}

function assertPositiveInteger(value, label) {
  if (!Number.isInteger(value) || value <= 0) {
    fail(`${label} deve ser inteiro positivo`)
  }
  return value
}

function assertSha256(value, label) {
  if (typeof value !== 'string' || !SHA256_PATTERN.test(value)) {
    fail(`${label} deve ser SHA-256 minúsculo`)
  }
  return value
}

function compareSlugs(left, right) {
  if (left.slug < right.slug) return -1
  if (left.slug > right.slug) return 1
  return 0
}

export function canonicalJson(value) {
  return `${JSON.stringify(value, null, 2)}\n`
}

export function sha256Utf8(value) {
  return createHash('sha256').update(value, 'utf8').digest('hex')
}

function parseLegacyManifest(value) {
  assertRecord(value, 'manifest')
  if (value.schemaVersion !== LEGACY_MANIFEST_SCHEMA) {
    fail('manifest.schemaVersion incompatível')
  }
  if (value.documentSchemaVersion !== LEGACY_DOCUMENT_SCHEMA) {
    fail('manifest.documentSchemaVersion incompatível')
  }
  if (value.stateCode !== 'RS') fail('manifest.stateCode deve ser RS')
  const sourceVersion = assertNonEmptyString(value.sourceVersion, 'manifest.sourceVersion')
  if (!Array.isArray(value.regions) || value.regions.length !== EXPECTED_REGION_COUNT) {
    fail(`manifest.regions deve conter exatamente ${EXPECTED_REGION_COUNT} regiões`)
  }

  const regionsBySlug = new Map()
  value.regions.forEach((region, index) => {
    const label = `manifest.regions[${index}]`
    assertRecord(region, label)
    const slug = assertNonEmptyString(region.slug, `${label}.slug`)
    const name = assertNonEmptyString(region.name, `${label}.name`)
    if (region.uf !== 'RS') fail(`${label}.uf deve ser RS`)
    const municipalityCount = assertPositiveInteger(
      region.municipalityCount,
      `${label}.municipalityCount`,
    )
    const contentVersion = assertSha256(
      region.contentVersion,
      `${label}.contentVersion`,
    )
    if (region.publicationStatus !== 'published') {
      fail(`${label}.publicationStatus deve ser published`)
    }
    if (regionsBySlug.has(slug)) fail(`${label}.slug duplicado: ${slug}`)
    regionsBySlug.set(slug, Object.freeze({
      slug,
      name,
      stateCode: 'RS',
      municipalityCount,
      sourceVersion,
      contentVersion,
    }))
  })

  return Object.freeze({ sourceVersion, regionsBySlug })
}

function parseCoverage(value, legacy) {
  assertExactKeys(value, ['schemaVersion', 'stateCode', 'regions'], 'coverage')
  if (value.schemaVersion !== VOCACOES_PNE_TRANSFER_COVERAGE_SCHEMA) {
    fail('coverage.schemaVersion incompatível')
  }
  if (value.stateCode !== 'RS') fail('coverage.stateCode deve ser RS')
  if (!Array.isArray(value.regions) || value.regions.length !== EXPECTED_REGION_COUNT) {
    fail(`coverage.regions deve conter exatamente ${EXPECTED_REGION_COUNT} regiões`)
  }

  const coverageBySlug = new Map()
  value.regions.forEach((region, index) => {
    const label = `coverage.regions[${index}]`
    assertExactKeys(region, COVERAGE_FIELDS, label)
    const slug = assertNonEmptyString(region.slug, `${label}.slug`)
    if (!legacy.regionsBySlug.has(slug)) fail(`${label}.slug desconhecido: ${slug}`)
    if (coverageBySlug.has(slug)) fail(`${label}.slug duplicado: ${slug}`)
    if (!AUDIT_STATUS_VALUES.has(region.auditStatus)) {
      fail(`${label}.auditStatus inválido`)
    }
    for (const field of ['firstOutputArtifactStatus', 'secondOutputArtifactStatus']) {
      if (!ARTIFACT_STATUS_VALUES.has(region[field])) fail(`${label}.${field} inválido`)
    }
    if (region.auditStatus === 'not_audited') {
      if (
        region.firstOutputArtifactStatus !== 'not_audited'
        || region.secondOutputArtifactStatus !== 'not_audited'
      ) {
        fail(`${label} não auditado deve manter ambos os artefatos como not_audited`)
      }
    } else if (
      region.firstOutputArtifactStatus === 'not_audited'
      || region.secondOutputArtifactStatus === 'not_audited'
    ) {
      fail(`${label} auditado não pode manter artefato como not_audited`)
    }
    coverageBySlug.set(slug, Object.freeze({ ...region }))
  })

  for (const slug of legacy.regionsBySlug.keys()) {
    if (!coverageBySlug.has(slug)) fail(`coverage sem a região ${slug}`)
  }
  return coverageBySlug
}

function parseRegistry(value, legacy = null) {
  assertExactKeys(value, ['schemaVersion', 'entries'], 'registry')
  if (value.schemaVersion !== REGISTRY_SCHEMA) fail('registry.schemaVersion incompatível')
  if (!Array.isArray(value.entries)) fail('registry.entries deve ser lista')

  const entriesBySlug = new Map()
  const entries = value.entries.map((entry, index) => {
    const label = `registry.entries[${index}]`
    assertExactKeys(entry, REGISTRY_ENTRY_FIELDS, label)
    const slug = assertNonEmptyString(entry.slug, `${label}.slug`)
    assertNonEmptyString(entry.name, `${label}.name`)
    if (entry.stateCode !== 'RS') fail(`${label}.stateCode deve ser RS`)
    assertPositiveInteger(entry.municipalityCount, `${label}.municipalityCount`)
    if (entry.narrativeSchemaVersion !== VOCACOES_PNE_NARRATIVE_SCHEMA) {
      fail(`${label}.narrativeSchemaVersion incompatível`)
    }
    if (entry.narrativeContractVersion !== VOCACOES_PNE_NARRATIVE_CONTRACT_VERSION) {
      fail(`${label}.narrativeContractVersion incompatível`)
    }
    assertNonEmptyString(entry.legacySourceVersion, `${label}.legacySourceVersion`)
    assertSha256(entry.legacyContentVersion, `${label}.legacyContentVersion`)
    assertPositiveInteger(entry.narrativeByteSize, `${label}.narrativeByteSize`)
    assertSha256(entry.narrativeSha256, `${label}.narrativeSha256`)
    if (!STATUS_VALUES.has(entry.status)) fail(`${label}.status inválido`)
    if (entriesBySlug.has(slug)) fail(`${label}.slug duplicado: ${slug}`)

    if (legacy !== null) {
      const region = legacy.regionsBySlug.get(slug)
      if (region === undefined) fail(`${label}.slug desconhecido no manifesto: ${slug}`)
      if (entry.name !== region.name) fail(`${label}.name divergente do manifesto`)
      if (entry.stateCode !== region.stateCode) fail(`${label}.stateCode divergente`)
      if (entry.municipalityCount !== region.municipalityCount) {
        fail(`${label}.municipalityCount divergente do manifesto`)
      }
      if (entry.legacySourceVersion !== region.sourceVersion) {
        fail(`${label}.legacySourceVersion divergente do manifesto`)
      }
      if (entry.legacyContentVersion !== region.contentVersion) {
        fail(`${label}.legacyContentVersion divergente do manifesto`)
      }
    }

    const parsed = Object.freeze({ ...entry })
    entriesBySlug.set(slug, parsed)
    return parsed
  })

  return Object.freeze({ entries, entriesBySlug })
}

function parseNarrativeDocuments(value) {
  if (!Array.isArray(value)) fail('documents deve ser lista')
  const paths = new Set()
  return value.map((document, index) => {
    const label = `documents[${index}]`
    assertExactKeys(document, DOCUMENT_FIELDS, label)
    const documentPath = assertNonEmptyString(document.path, `${label}.path`)
    if (paths.has(documentPath)) fail(`${label}.path duplicado: ${documentPath}`)
    paths.add(documentPath)
    if (typeof document.raw !== 'string' || document.raw.length === 0) {
      fail(`${label}.raw deve ser string não vazia`)
    }
    return Object.freeze({
      path: documentPath,
      raw: document.raw,
      byteSize: Buffer.byteLength(document.raw, 'utf8'),
      sha256: sha256Utf8(document.raw),
    })
  })
}

function validateNarrativeDocuments(registry, documents) {
  if (documents.length !== registry.entries.length) {
    fail('documents deve corresponder exatamente às entradas do registro')
  }

  const validatedBySlug = new Map()
  const consumedPaths = new Set()
  for (const entry of registry.entries) {
    const matches = documents.filter((document) => document.sha256 === entry.narrativeSha256)
    if (matches.length === 0) fail(`documento narrativo ausente para ${entry.slug}`)
    if (matches.length > 1) fail(`documento narrativo duplicado para ${entry.slug}`)
    const documentFile = matches[0]
    if (documentFile.byteSize !== entry.narrativeByteSize) {
      fail(`documento narrativo com tamanho divergente para ${entry.slug}`)
    }

    let document
    try {
      document = parseVocacoesPneNarrative(JSON.parse(documentFile.raw))
    } catch (error) {
      fail(`documento narrativo inválido para ${entry.slug}`, { cause: error })
    }
    if (document.schemaVersion !== entry.narrativeSchemaVersion) {
      fail(`schema narrativo divergente para ${entry.slug}`)
    }
    if (document.contractVersion !== entry.narrativeContractVersion) {
      fail(`contrato narrativo divergente para ${entry.slug}`)
    }
    if (document.region.slug !== entry.slug) fail(`slug narrativo divergente para ${entry.slug}`)
    if (document.region.name !== entry.name) fail(`nome narrativo divergente para ${entry.slug}`)
    if (document.region.stateCode !== entry.stateCode) {
      fail(`UF narrativa divergente para ${entry.slug}`)
    }
    if (document.region.municipalityCount !== entry.municipalityCount) {
      fail(`contagem municipal narrativa divergente para ${entry.slug}`)
    }
    const firstCount = document.sections[0].cards.length
    const secondCount = document.sections[1].cards.length
    if (firstCount < 3 || firstCount > 5) {
      fail(`primeira saída fora da cardinalidade para ${entry.slug}`)
    }
    if (secondCount < 2 || secondCount > 5) {
      fail(`segunda saída fora da cardinalidade para ${entry.slug}`)
    }
    consumedPaths.add(documentFile.path)
    validatedBySlug.set(entry.slug, Object.freeze({ entry, document, documentFile }))
  }

  for (const document of documents) {
    if (!consumedPaths.has(document.path)) {
      fail(`documento narrativo extra ou sem registro: ${document.path}`)
    }
  }
  return validatedBySlug
}

function classifyRegion(region, coverage, registered) {
  const reasonCodes = []
  let readiness
  let publicationMode

  if (registered?.entry.status === 'published') {
    if (
      coverage.auditStatus !== 'complete'
      || coverage.firstOutputArtifactStatus !== 'available'
      || coverage.secondOutputArtifactStatus !== 'available'
    ) {
      fail(`região publicada sem cobertura completa dos artefatos: ${region.slug}`)
    }
    readiness = 'ready'
    publicationMode = 'narrative'
  } else if (registered?.entry.status === 'rolled_back') {
    readiness = 'blocked'
    publicationMode = 'legacy'
    reasonCodes.push(VOCACOES_PNE_PUBLICATION_REASON_CODES.NARRATIVE_ROLLED_BACK)
  } else if (coverage.auditStatus === 'not_audited') {
    readiness = 'blocked'
    publicationMode = 'legacy'
    reasonCodes.push(VOCACOES_PNE_PUBLICATION_REASON_CODES.TRANSFER_NOT_AUDITED)
  } else {
    if (coverage.firstOutputArtifactStatus === 'missing') {
      reasonCodes.push(
        VOCACOES_PNE_PUBLICATION_REASON_CODES.FIRST_OUTPUT_ARTIFACT_MISSING,
      )
    }
    if (coverage.secondOutputArtifactStatus === 'missing') {
      reasonCodes.push(
        VOCACOES_PNE_PUBLICATION_REASON_CODES.SECOND_OUTPUT_ARTIFACT_MISSING,
      )
    }
    if (reasonCodes.length === 0) {
      fail(`região auditada sem bloqueio e sem entrada narrativa: ${region.slug}`)
    }
    readiness = 'almost_ready'
    publicationMode = 'legacy'
  }

  return Object.freeze({
    slug: region.slug,
    name: region.name,
    stateCode: region.stateCode,
    municipalityCount: region.municipalityCount,
    readiness,
    publicationMode,
    reasonCodes: Object.freeze(reasonCodes),
    legacy: Object.freeze({
      sourceVersion: region.sourceVersion,
      contentVersion: region.contentVersion,
    }),
    narrative: registered === undefined
      ? null
      : Object.freeze({
        schemaVersion: registered.entry.narrativeSchemaVersion,
        contractVersion: registered.entry.narrativeContractVersion,
        byteSize: registered.entry.narrativeByteSize,
        sha256: registered.entry.narrativeSha256,
        status: registered.entry.status,
      }),
  })
}

export function buildVocacoesPnePublicationQueue({
  legacyManifest,
  narrativeRegistry,
  narrativeDocuments,
  transferCoverage,
}) {
  const legacy = parseLegacyManifest(legacyManifest)
  const coverageBySlug = parseCoverage(transferCoverage, legacy)
  const registry = parseRegistry(narrativeRegistry, legacy)
  const documents = parseNarrativeDocuments(narrativeDocuments)
  const validatedBySlug = validateNarrativeDocuments(registry, documents)

  const regions = [...legacy.regionsBySlug.values()]
    .sort(compareSlugs)
    .map((region) => classifyRegion(
      region,
      coverageBySlug.get(region.slug),
      validatedBySlug.get(region.slug),
    ))
  const readySlugs = regions
    .filter((region) => region.readiness === 'ready')
    .map((region) => region.slug)
  const count = (status) => regions.filter((region) => region.readiness === status).length
  const legacyCount = regions.filter((region) => region.publicationMode === 'legacy').length

  return Object.freeze({
    schemaVersion: VOCACOES_PNE_PUBLICATION_QUEUE_SCHEMA,
    engineVersion: VOCACOES_PNE_PUBLICATION_ENGINE_VERSION,
    stateCode: 'RS',
    sourceManifestSchemaVersion: LEGACY_MANIFEST_SCHEMA,
    sourceDocumentSchemaVersion: LEGACY_DOCUMENT_SCHEMA,
    summary: Object.freeze({
      regionCount: regions.length,
      readyCount: count('ready'),
      almostReadyCount: count('almost_ready'),
      blockedCount: count('blocked'),
      narrativeCount: readySlugs.length,
      legacyCount,
      batchCount: readySlugs.length > 0 ? 1 : 0,
    }),
    regions: Object.freeze(regions),
    batches: Object.freeze(readySlugs.length === 0 ? [] : [Object.freeze({
      batchId: 'vocacoes-pne-r9-initial',
      publicationMode: 'narrative',
      regionSlugs: Object.freeze(readySlugs),
      rollback: Object.freeze({
        unit: 'region',
        proposalStatus: 'rolled_back',
        fallbackPublicationMode: 'legacy',
        automaticMutation: false,
      }),
    })]),
    rollbackPolicy: Object.freeze({
      unit: 'region',
      sourceStatus: 'published',
      proposalStatus: 'rolled_back',
      fallbackPublicationMode: 'legacy',
      automaticMutation: false,
    }),
  })
}

export function createVocacoesPneRollbackProposal(narrativeRegistry, slug) {
  const targetSlug = assertNonEmptyString(slug, 'rollback.slug')
  const registry = parseRegistry(narrativeRegistry)
  const target = registry.entriesBySlug.get(targetSlug)
  if (target === undefined) fail(`rollback.slug desconhecido: ${targetSlug}`)
  if (target.status !== 'published') fail(`rollback.slug já está inativo: ${targetSlug}`)

  return {
    schemaVersion: REGISTRY_SCHEMA,
    entries: registry.entries.map((entry) => ({
      ...entry,
      status: entry.slug === targetSlug ? 'rolled_back' : entry.status,
    })),
  }
}
