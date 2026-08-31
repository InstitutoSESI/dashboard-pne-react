import narrativeRegistryRaw from './generated/vocacoesPneNarrativeRegistry.json'
import narrativeValeDoSinosRaw from './generated/vocacoesPneValeDoSinos.json?raw'
import {
  VOCACOES_PNE_NARRATIVE_CONTRACT_VERSION,
  VOCACOES_PNE_NARRATIVE_SCHEMA,
  parseVocacoesPneNarrative,
} from './vocacoesPneNarrativeContract.js'
import { VOCACOES_DOCUMENT_SCHEMA } from './vocacoesRegiaoContract.js'

export const VOCACOES_PNE_NARRATIVE_REGISTRY_SCHEMA =
  'vocacoes-pne-narrative-registry-v1'

const ENTRY_FIELDS = [
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

const DOCUMENT_FIELDS = ['slug', 'path', 'raw']
const SHA256_PATTERN = /^[a-f0-9]{64}$/u
const KNOWN_DOCUMENT_PATHS = Object.freeze({
  'vale-do-sinos': './generated/vocacoesPneValeDoSinos.json',
})

export const VOCACOES_PNE_NARRATIVE_REGISTRY_MANIFEST = narrativeRegistryRaw

export const VOCACOES_PNE_NARRATIVE_IMPORTED_DOCUMENTS = Object.freeze([
  Object.freeze({
    slug: 'vale-do-sinos',
    path: './generated/vocacoesPneValeDoSinos.json',
    raw: narrativeValeDoSinosRaw,
  }),
])

const SHA256_CONSTANTS = new Uint32Array([
  0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5,
  0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
  0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
  0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
  0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc,
  0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
  0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7,
  0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
  0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
  0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
  0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3,
  0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
  0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5,
  0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
  0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
  0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
])

function fail(path, message) {
  throw new TypeError(`${path}: ${message}`)
}

function isRecord(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
}

function exactKeys(value, expected, path) {
  if (!isRecord(value)) fail(path, 'deve ser objeto')
  const actual = Object.keys(value).sort()
  const wanted = [...expected].sort()
  if (
    actual.length !== wanted.length
    || actual.some((key, index) => key !== wanted[index])
  ) {
    fail(path, `campos exatos esperados: ${expected.join(', ')}`)
  }
}

function nonEmptyString(value, path) {
  if (typeof value !== 'string' || value.trim().length === 0) {
    fail(path, 'deve ser string não vazia')
  }
  return value
}

function positiveInteger(value, path) {
  if (!Number.isInteger(value) || value <= 0) fail(path, 'deve ser inteiro positivo')
  return value
}

function lowercaseSha256(value, path) {
  if (typeof value !== 'string' || !SHA256_PATTERN.test(value)) {
    fail(path, 'deve ser SHA-256 minúsculo')
  }
  return value
}

function rotateRight(value, amount) {
  return (value >>> amount) | (value << (32 - amount))
}

function canonicalize(value) {
  if (Array.isArray(value)) return value.map(canonicalize)
  if (isRecord(value)) {
    return Object.keys(value).sort().reduce((result, key) => {
      result[key] = canonicalize(value[key])
      return result
    }, {})
  }
  return value
}

export function sha256Utf8(value) {
  const bytes = new TextEncoder().encode(value)
  const bitLength = bytes.length * 8
  const paddedLength = Math.ceil((bytes.length + 9) / 64) * 64
  const padded = new Uint8Array(paddedLength)
  padded.set(bytes)
  padded[bytes.length] = 0x80
  const paddedView = new DataView(padded.buffer)
  paddedView.setUint32(paddedLength - 8, Math.floor(bitLength / 0x100000000))
  paddedView.setUint32(paddedLength - 4, bitLength >>> 0)

  const hash = new Uint32Array([
    0x6a09e667,
    0xbb67ae85,
    0x3c6ef372,
    0xa54ff53a,
    0x510e527f,
    0x9b05688c,
    0x1f83d9ab,
    0x5be0cd19,
  ])
  const words = new Uint32Array(64)

  for (let offset = 0; offset < padded.length; offset += 64) {
    for (let index = 0; index < 16; index += 1) {
      words[index] = paddedView.getUint32(offset + (index * 4))
    }
    for (let index = 16; index < 64; index += 1) {
      const word15 = words[index - 15]
      const word2 = words[index - 2]
      const sigma0 = rotateRight(word15, 7) ^ rotateRight(word15, 18) ^ (word15 >>> 3)
      const sigma1 = rotateRight(word2, 17) ^ rotateRight(word2, 19) ^ (word2 >>> 10)
      words[index] = (words[index - 16] + sigma0 + words[index - 7] + sigma1) >>> 0
    }

    let a = hash[0]
    let b = hash[1]
    let c = hash[2]
    let d = hash[3]
    let e = hash[4]
    let f = hash[5]
    let g = hash[6]
    let h = hash[7]

    for (let index = 0; index < 64; index += 1) {
      const sum1 = rotateRight(e, 6) ^ rotateRight(e, 11) ^ rotateRight(e, 25)
      const choice = (e & f) ^ (~e & g)
      const temporary1 = (h + sum1 + choice + SHA256_CONSTANTS[index] + words[index]) >>> 0
      const sum0 = rotateRight(a, 2) ^ rotateRight(a, 13) ^ rotateRight(a, 22)
      const majority = (a & b) ^ (a & c) ^ (b & c)
      const temporary2 = (sum0 + majority) >>> 0
      h = g
      g = f
      f = e
      e = (d + temporary1) >>> 0
      d = c
      c = b
      b = a
      a = (temporary1 + temporary2) >>> 0
    }

    hash[0] = (hash[0] + a) >>> 0
    hash[1] = (hash[1] + b) >>> 0
    hash[2] = (hash[2] + c) >>> 0
    hash[3] = (hash[3] + d) >>> 0
    hash[4] = (hash[4] + e) >>> 0
    hash[5] = (hash[5] + f) >>> 0
    hash[6] = (hash[6] + g) >>> 0
    hash[7] = (hash[7] + h) >>> 0
  }

  return [...hash].map((word) => word.toString(16).padStart(8, '0')).join('')
}

function computeLegacyContentVersion(legacyDocument) {
  const body = { ...legacyDocument }
  delete body.contentVersion
  return sha256Utf8(JSON.stringify(canonicalize(body)))
}

function parseRegistryEntry(value, path) {
  exactKeys(value, ENTRY_FIELDS, path)
  const slug = nonEmptyString(value.slug, `${path}.slug`)
  nonEmptyString(value.name, `${path}.name`)
  if (value.stateCode !== 'RS') fail(`${path}.stateCode`, 'deve ser RS')
  positiveInteger(value.municipalityCount, `${path}.municipalityCount`)
  if (value.narrativeSchemaVersion !== VOCACOES_PNE_NARRATIVE_SCHEMA) {
    fail(`${path}.narrativeSchemaVersion`, 'schema narrativo incompatível')
  }
  if (value.narrativeContractVersion !== VOCACOES_PNE_NARRATIVE_CONTRACT_VERSION) {
    fail(`${path}.narrativeContractVersion`, 'versão narrativa incompatível')
  }
  nonEmptyString(value.legacySourceVersion, `${path}.legacySourceVersion`)
  lowercaseSha256(value.legacyContentVersion, `${path}.legacyContentVersion`)
  positiveInteger(value.narrativeByteSize, `${path}.narrativeByteSize`)
  lowercaseSha256(value.narrativeSha256, `${path}.narrativeSha256`)
  if (!['published', 'rolled_back'].includes(value.status)) {
    fail(`${path}.status`, 'deve ser published ou rolled_back')
  }
  if (!Object.hasOwn(KNOWN_DOCUMENT_PATHS, slug)) fail(`${path}.slug`, 'desconhecido')
  return value
}

function parseImportedDocuments(importedDocuments) {
  if (!Array.isArray(importedDocuments)) fail('documents', 'deve ser lista')
  const documentsBySlug = new Map()
  const paths = new Set()
  importedDocuments.forEach((document, index) => {
    const path = `documents[${index}]`
    exactKeys(document, DOCUMENT_FIELDS, path)
    const slug = nonEmptyString(document.slug, `${path}.slug`)
    const documentPath = nonEmptyString(document.path, `${path}.path`)
    nonEmptyString(document.raw, `${path}.raw`)
    if (!Object.hasOwn(KNOWN_DOCUMENT_PATHS, slug)) fail(`${path}.slug`, 'desconhecido')
    if (documentPath !== KNOWN_DOCUMENT_PATHS[slug]) fail(`${path}.path`, 'divergente')
    if (documentsBySlug.has(slug)) fail(`${path}.slug`, 'documento duplicado')
    if (paths.has(documentPath)) fail(`${path}.path`, 'path duplicado')
    documentsBySlug.set(slug, document)
    paths.add(documentPath)
  })
  return documentsBySlug
}

export function parseVocacoesPneNarrativeRegistry(
  value,
  importedDocuments = VOCACOES_PNE_NARRATIVE_IMPORTED_DOCUMENTS,
) {
  exactKeys(value, ['schemaVersion', 'entries'], 'registry')
  if (value.schemaVersion !== VOCACOES_PNE_NARRATIVE_REGISTRY_SCHEMA) {
    fail('registry.schemaVersion', 'schema incompatível')
  }
  if (!Array.isArray(value.entries)) fail('registry.entries', 'deve ser lista')

  const documentsBySlug = parseImportedDocuments(importedDocuments)
  const entriesBySlug = new Map()
  value.entries.forEach((candidate, index) => {
    const entry = parseRegistryEntry(candidate, `registry.entries[${index}]`)
    if (entriesBySlug.has(entry.slug)) {
      fail(`registry.entries[${index}].slug`, 'entrada duplicada')
    }
    entriesBySlug.set(entry.slug, entry)
  })

  for (const slug of documentsBySlug.keys()) {
    if (!entriesBySlug.has(slug)) fail(`documents.${slug}`, 'documento não registrado')
  }
  for (const slug of entriesBySlug.keys()) {
    if (!documentsBySlug.has(slug)) {
      fail(`registry.entries.${slug}`, 'entrada fora dos documentos importados')
    }
  }
  if (entriesBySlug.size === 0) fail('registry.entries', 'deve conter ao menos uma entrada')

  const resolvedBySlug = new Map()
  for (const [slug, documentImport] of documentsBySlug) {
    const entry = entriesBySlug.get(slug)
    const bytes = new TextEncoder().encode(documentImport.raw)
    if (bytes.length !== entry.narrativeByteSize) {
      fail(`documents.${slug}`, 'tamanho divergente')
    }
    if (sha256Utf8(documentImport.raw) !== entry.narrativeSha256) {
      fail(`documents.${slug}`, 'hash divergente')
    }

    let document
    try {
      document = parseVocacoesPneNarrative(JSON.parse(documentImport.raw))
    } catch {
      fail(`documents.${slug}`, 'documento narrativo inválido')
    }
    if (document.region.slug !== entry.slug) fail(`documents.${slug}`, 'slug divergente')
    if (document.region.name !== entry.name) fail(`documents.${slug}`, 'nome divergente')
    if (document.region.stateCode !== entry.stateCode) fail(`documents.${slug}`, 'UF divergente')
    if (document.region.municipalityCount !== entry.municipalityCount) {
      fail(`documents.${slug}`, 'contagem municipal divergente')
    }
    if (document.schemaVersion !== entry.narrativeSchemaVersion) {
      fail(`documents.${slug}`, 'schema narrativo divergente')
    }
    if (document.contractVersion !== entry.narrativeContractVersion) {
      fail(`documents.${slug}`, 'versão narrativa divergente')
    }
    resolvedBySlug.set(slug, Object.freeze({ document, entry }))
  }

  return Object.freeze({
    resolve(slug) {
      return resolvedBySlug.get(slug) ?? null
    },
  })
}

export function createVocacoesPneNarrativeRegistry(
  value,
  importedDocuments = VOCACOES_PNE_NARRATIVE_IMPORTED_DOCUMENTS,
) {
  try {
    return parseVocacoesPneNarrativeRegistry(value, importedDocuments)
  } catch {
    return null
  }
}

const narrativeRegistry = createVocacoesPneNarrativeRegistry(
  VOCACOES_PNE_NARRATIVE_REGISTRY_MANIFEST,
)

export function resolveRegisteredVocacoesPneNarrative(
  legacyDocument,
  activeStateCode,
  registry = narrativeRegistry,
) {
  if (registry === null || activeStateCode !== 'RS' || !isRecord(legacyDocument)) return null
  if (legacyDocument.schemaVersion !== VOCACOES_DOCUMENT_SCHEMA) return null
  if (!isRecord(legacyDocument.region)) return null
  const registered = registry.resolve(legacyDocument.region.slug)
  if (registered === null) return null
  const { document, entry } = registered
  if (entry.status !== 'published') return null
  if (legacyDocument.contentVersion !== entry.legacyContentVersion) return null
  if (legacyDocument.sourceVersion !== entry.legacySourceVersion) return null
  if (legacyDocument.region.slug !== entry.slug) return null
  if (legacyDocument.region.name !== entry.name) return null
  if (legacyDocument.region.uf !== entry.stateCode) return null
  if (legacyDocument.region.municipalityCount !== entry.municipalityCount) return null
  if (document.schemaVersion !== entry.narrativeSchemaVersion) return null
  if (document.contractVersion !== entry.narrativeContractVersion) return null
  try {
    if (computeLegacyContentVersion(legacyDocument) !== entry.legacyContentVersion) return null
  } catch {
    return null
  }
  return document
}
