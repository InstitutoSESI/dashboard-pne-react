/*
 * Leitura do Vocações da Região publicado em `public/data/vocacoes-regiao/`.
 *
 * O slot existe antes do conteúdo. O manifesto vazio é publicado desde já e é
 * válido: enquanto nenhuma região constar dele, não há item de menu, não há
 * rota alcançável e não há pacote a ler — fail-closed por ausência, sem página
 * vazia e sem erro no console.
 *
 * O contrato do pacote é o mesmo dos Cenários da educação municipal, com uma
 * única diferença: a identidade é a região, não o município. Por isso este
 * módulo não reimplementa validação alguma — ele instancia a fábrica de
 * validador do foresight com a identidade regional e a versão de origem que o
 * próprio manifesto declara. Quando a camada de pesquisa publicar o contrato
 * "vocacoes-regiao v0.1", nada aqui precisa mudar além do manifesto.
 */

import { createDocumentParser } from '../foresight/foresightEducacaoLoader.js'

export const VOCACOES_MANIFEST_PATH = '/data/vocacoes-regiao/manifest.json'
export const VOCACOES_REGION_PATH = '/data/vocacoes-regiao/regioes/{regionSlug}.json'
export const VOCACOES_REGION_FILE_PATTERN = 'regioes/{regionSlug}.json'

export const VOCACOES_MANIFEST_SCHEMA = 'vocacoes-regiao-manifest-v1'
export const VOCACOES_DOCUMENT_SCHEMA = 'vocacoes-regiao-1.0.0'
export const VOCACOES_SCOPE_TYPE = 'region'

const SHA256_PATTERN = /^[a-f0-9]{64}$/
const SLUG_PATTERN = /^[a-z0-9]+(?:-[a-z0-9]+)*$/
const UF_PATTERN = /^[A-Z]{2}$/
const ISO_DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/

const MANIFEST_FIELDS = new Set([
  'schemaVersion',
  'documentSchemaVersion',
  'scopeType',
  'generatedAt',
  'generatorVersion',
  'sourceVersion',
  'sourceMethodologyStatus',
  'publicationScope',
  'regionFilePattern',
  'stateCode',
  'regions',
])
const MANIFEST_ENTRY_FIELDS = new Set([
  'slug',
  'name',
  'uf',
  'path',
  'municipalityCount',
  'contentHash',
  'contentVersion',
  'byteSize',
  'publicationStatus',
  'scenarioCount',
])
const REGION_IDENTITY_FIELDS = new Set(['slug', 'name', 'uf', 'municipalityCount'])

/** Erro de carga do Vocações da Região, sempre com estágio e código. */
export class VocacoesLoadError extends Error {
  constructor(message, { code, stage, regionSlug = null, path = null, cause } = {}) {
    super(message, cause === undefined ? undefined : { cause })
    this.name = 'VocacoesLoadError'
    this.code = code
    this.stage = stage
    this.regionSlug = regionSlug
    this.path = path
  }
}

function invariant(condition, message) {
  if (!condition) throw new Error(message)
}

function isRecord(value) {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function validateExactFields(value, allowed, label) {
  invariant(isRecord(value), `${label} deve ser um objeto.`)
  const keys = Object.keys(value)
  const unexpected = keys.filter((key) => !allowed.has(key))
  const missing = [...allowed].filter((key) => !keys.includes(key))
  invariant(unexpected.length === 0, `${label} traz campos fora do contrato: ${unexpected.join(', ')}.`)
  invariant(missing.length === 0, `${label} não traz os campos obrigatórios: ${missing.join(', ')}.`)
}

function validateText(value, label) {
  invariant(typeof value === 'string' && value.trim() !== '', `${label} deve ser texto não vazio.`)
  return value
}

/** Identidade regional: o que substitui o município no pacote transposto. */
export function validateRegionIdentity(value, label) {
  validateExactFields(value, REGION_IDENTITY_FIELDS, label)
  invariant(
    typeof value.slug === 'string' && SLUG_PATTERN.test(value.slug),
    `${label}.slug deve ser um slug de rota.`,
  )
  validateText(value.name, `${label}.name`)
  invariant(
    typeof value.uf === 'string' && UF_PATTERN.test(value.uf),
    `${label}.uf deve ter duas letras maiúsculas.`,
  )
  invariant(
    Number.isInteger(value.municipalityCount) && value.municipalityCount > 0,
    `${label}.municipalityCount deve ser inteiro positivo.`,
  )
  return value
}

/** Valida o manifesto público e devolve uma cópia congelada. */
export function parseVocacoesManifest(candidate) {
  validateExactFields(candidate, MANIFEST_FIELDS, 'manifesto')
  invariant(candidate.schemaVersion === VOCACOES_MANIFEST_SCHEMA, 'esquema do manifesto desconhecido.')
  invariant(
    candidate.documentSchemaVersion === VOCACOES_DOCUMENT_SCHEMA,
    'esquema do pacote regional desconhecido.',
  )
  invariant(candidate.scopeType === VOCACOES_SCOPE_TYPE, 'escopo territorial do manifesto inesperado.')
  invariant(
    candidate.regionFilePattern === VOCACOES_REGION_FILE_PATTERN,
    'padrão de caminho regional inesperado.',
  )
  validateText(candidate.generatorVersion, 'manifesto.generatorVersion')
  invariant(
    typeof candidate.generatedAt === 'string' && ISO_DATE_PATTERN.test(candidate.generatedAt),
    'manifesto.generatedAt deve ser uma data ISO.',
  )
  invariant(
    typeof candidate.stateCode === 'string' && UF_PATTERN.test(candidate.stateCode),
    'manifesto.stateCode deve ter duas letras maiúsculas.',
  )
  validateText(candidate.sourceVersion, 'manifesto.sourceVersion')
  validateText(candidate.sourceMethodologyStatus, 'manifesto.sourceMethodologyStatus')
  validateText(candidate.publicationScope, 'manifesto.publicationScope')

  /*
   * Lista vazia é o estado normal enquanto o contrato de origem não existe.
   * Um manifesto sem regiões é válido e significa exatamente uma coisa: não há
   * nada publicado.
   */
  invariant(Array.isArray(candidate.regions), 'manifesto.regions deve ser uma lista.')

  const slugs = new Set()
  const regions = candidate.regions.map((entry, index) => {
    const label = `manifesto.regions[${index}]`
    validateExactFields(entry, MANIFEST_ENTRY_FIELDS, label)
    invariant(
      typeof entry.slug === 'string' && SLUG_PATTERN.test(entry.slug),
      `${label}.slug deve ser um slug de rota.`,
    )
    invariant(!slugs.has(entry.slug), `${label}.slug repetido: ${entry.slug}.`)
    slugs.add(entry.slug)
    validateText(entry.name, `${label}.name`)
    invariant(typeof entry.uf === 'string' && UF_PATTERN.test(entry.uf), `${label}.uf inválido.`)
    invariant(
      entry.path === VOCACOES_REGION_FILE_PATTERN.replace('{regionSlug}', entry.slug),
      `${label}.path diverge do padrão declarado.`,
    )
    invariant(
      Number.isInteger(entry.municipalityCount) && entry.municipalityCount > 0,
      `${label}.municipalityCount deve ser inteiro positivo.`,
    )
    invariant(
      typeof entry.contentHash === 'string' && SHA256_PATTERN.test(entry.contentHash),
      `${label}.contentHash deve ser sha256.`,
    )
    invariant(
      typeof entry.contentVersion === 'string' && SHA256_PATTERN.test(entry.contentVersion),
      `${label}.contentVersion deve ser sha256.`,
    )
    invariant(
      Number.isInteger(entry.byteSize) && entry.byteSize > 0,
      `${label}.byteSize deve ser inteiro positivo.`,
    )
    invariant(entry.publicationStatus === 'published', `${label}.publicationStatus deve ser "published".`)
    invariant(
      Number.isInteger(entry.scenarioCount) && entry.scenarioCount > 0,
      `${label}.scenarioCount deve ser inteiro positivo.`,
    )
    return Object.freeze({ ...entry })
  })

  return Object.freeze({ ...candidate, regions: Object.freeze(regions) })
}

/*
 * O validador de pacote nasce do manifesto: é ele que declara a versão de
 * origem e o escopo de publicação que o pacote precisa repetir. Assim o slot
 * aceita o contrato v0.1 no dia em que a pesquisa o publicar, sem que este
 * arquivo precise saber qual será o número.
 */
export function createVocacoesDocumentParser(manifest) {
  return createDocumentParser({
    documentSchema: manifest.documentSchemaVersion,
    sourceVersion: manifest.sourceVersion,
    publicationScope: manifest.publicationScope,
    identityKey: 'region',
    validateIdentity: validateRegionIdentity,
  })
}

export async function digestText(text) {
  const subtle = globalThis.crypto?.subtle
  if (!subtle) return null
  const bytes = new TextEncoder().encode(text)
  const digest = await subtle.digest('SHA-256', bytes)
  return [...new Uint8Array(digest)].map((byte) => byte.toString(16).padStart(2, '0')).join('')
}

async function defaultFetchText(path, options) {
  const response = await fetch(path, options)
  if (!response.ok) throw new Error(`Falha ao ler ${path}: HTTP ${response.status}.`)
  return response.text()
}

function structuredError(error, details) {
  if (error instanceof VocacoesLoadError) return error
  return new VocacoesLoadError(
    error instanceof Error ? error.message : String(error),
    { ...details, cause: error },
  )
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

/**
 * @param {{
 *   fetchText?: (path: string, options?: RequestInit) => Promise<string>,
 *   logger?: (...data: unknown[]) => void,
 * }} [options]
 */
export function createVocacoesRegiaoLoader({
  fetchText = defaultFetchText,
  logger = console.error,
} = {}) {
  const documentCache = new Map()
  const reportedErrors = new Set()
  let manifestPending = null
  let manifestResolved = null

  function reportOnce(error) {
    const key = [error.code, error.stage, error.regionSlug, error.path, error.message].join(':')
    if (reportedErrors.has(key)) return
    reportedErrors.add(key)
    logger(error)
  }

  function loadManifest() {
    if (manifestResolved) return manifestResolved
    if (manifestPending) return manifestPending
    manifestPending = Promise.resolve()
      .then(() => fetchText(VOCACOES_MANIFEST_PATH, { cache: 'no-store' }))
      .catch((error) => {
        throw structuredError(error, {
          code: 'manifest_unavailable',
          path: VOCACOES_MANIFEST_PATH,
          stage: 'manifest',
        })
      })
      .then((raw) => {
        try {
          return parseVocacoesManifest(JSON.parse(raw))
        } catch (error) {
          throw structuredError(error, {
            code: 'invalid_manifest',
            path: VOCACOES_MANIFEST_PATH,
            stage: 'manifest',
          })
        }
      })
      .then((manifest) => {
        manifestResolved = Promise.resolve(manifest)
        return manifest
      })
      .finally(() => {
        manifestPending = null
      })
    return manifestPending
  }

  /*
   * Conjunto publicado, na forma que a navegação consome. Falha de manifesto
   * vira conjunto vazio: o item some, em vez de aparecer quebrado.
   */
  function listPublishedRegionSlugs() {
    return loadManifest()
      .then((manifest) => manifest.regions.map((entry) => entry.slug))
      .catch((error) => {
        reportOnce(structuredError(error, { code: 'manifest_unavailable', stage: 'manifest' }))
        return []
      })
  }

  async function loadRegion(regionSlug) {
    const manifest = await loadManifest()
    const entry = manifest.regions.find((candidate) => candidate.slug === regionSlug) ?? null
    if (entry === null) {
      throw new VocacoesLoadError(
        `O Vocações da Região não está publicado para ${regionSlug}.`,
        { code: 'region_not_published', regionSlug, stage: 'manifest' },
      )
    }

    return memoized(documentCache, `${entry.contentHash}:${regionSlug}`, async () => {
      const path = VOCACOES_REGION_PATH.replace('{regionSlug}', regionSlug)
      let raw
      try {
        raw = await fetchText(path)
      } catch (error) {
        throw structuredError(error, { code: 'region_unavailable', regionSlug, path, stage: 'region' })
      }

      let integrity = 'declared'
      try {
        const digest = await digestText(raw)
        if (digest !== null) {
          invariant(digest === entry.contentHash, `resumo do arquivo diverge do manifesto em ${regionSlug}.`)
          integrity = 'verified'
        }
        const document = createVocacoesDocumentParser(manifest)(JSON.parse(raw))
        invariant(
          document.region.slug === regionSlug,
          `o arquivo carregado pertence a outra região: ${document.region.slug}.`,
        )
        invariant(
          document.region.name === entry.name
            && document.region.uf === entry.uf
            && document.region.municipalityCount === entry.municipalityCount,
          `identidade regional divergente do manifesto em ${regionSlug}.`,
        )
        invariant(
          document.contentVersion === entry.contentVersion,
          `versão de conteúdo divergente do manifesto em ${regionSlug}.`,
        )
        invariant(
          document.sourceMethodologyStatus === manifest.sourceMethodologyStatus
            && document.generatedAt === manifest.generatedAt,
          `origem ou data divergentes do manifesto em ${regionSlug}.`,
        )
        invariant(
          document.scenarios.length === entry.scenarioCount,
          `quantidade de cenários divergente do manifesto em ${regionSlug}.`,
        )
        return { document, entry, integrity }
      } catch (error) {
        throw structuredError(error, { code: 'invalid_payload', regionSlug, path, stage: 'region' })
      }
    })
  }

  return { listPublishedRegionSlugs, loadManifest, loadRegion }
}
