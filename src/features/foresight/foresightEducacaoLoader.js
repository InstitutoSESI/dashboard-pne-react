/*
 * Leitura dos Cenários da educação municipal publicados em
 * `public/data/foresight-educacao/`.
 *
 * O manifesto é a única porta de entrada: ele decide quais municípios têm
 * cenário publicado. O pacote municipal só é aceito depois de conferir o hash
 * do próprio arquivo, a identidade do município, a versão de conteúdo e a
 * linguagem pública. Toda falha vira erro estruturado e nada é exibido.
 *
 * Este módulo não calcula cenário, não interpreta fator, não combina série,
 * não recorre a outro município e não converte ausência em zero. Ele lê o que
 * a camada de pesquisa aprovou e a materialização publicou.
 */

import {
  assertPublicText,
  HORIZON_SCAN_YEAR,
  HORIZON_STATE_YEAR,
  LAST_OBSERVED_YEAR,
} from './foresightPublicLanguage.js'

export const FORESIGHT_MANIFEST_PATH = '/data/foresight-educacao/manifest.json'
export const FORESIGHT_MUNICIPAL_PATH = '/data/foresight-educacao/municipios/{municipalityId}.json'
export const FORESIGHT_MUNICIPAL_FILE_PATTERN = 'municipios/{municipalityId}.json'

export const FORESIGHT_MANIFEST_SCHEMA = 'foresight-educacao-manifest-v1'
export const FORESIGHT_DOCUMENT_SCHEMA = 'foresight-educacao-1.0.0'
export const FORESIGHT_SOURCE_VERSION = 'v0.4.0-rc4'
export const FORESIGHT_PUBLICATION_SCOPE = 'pilot'
export const FORESIGHT_SCENARIO_COUNT = 4

/** As sete seções públicas de cada cenário, na ordem aprovada. */
export const FORESIGHT_SECTION_KEYS = Object.freeze([
  'de-onde-o-municipio-parte',
  'como-a-educacao-chegou-a-essa-situacao',
  'como-este-cenario-se-forma',
  'o-que-pode-mudar-no-sistema-educacional',
  'o-que-precisa-ocorrer-para-este-cenario-ganhar-forca',
  'o-que-acompanhar',
  'limite-especifico',
])

/** As seções que todo cenário publicado precisa trazer. */
export const FORESIGHT_REQUIRED_SECTION_KEYS = Object.freeze(
  FORESIGHT_SECTION_KEYS.filter((key) => key !== 'limite-especifico'),
)

const SHA256_PATTERN = /^[a-f0-9]{64}$/
const IBGE7_PATTERN = /^\d{7}$/
const ISO_DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/
const SLUG_PATTERN = /^[a-z0-9]+(?:-[a-z0-9]+)*$/
const UF_PATTERN = /^[A-Z]{2}$/

const MANIFEST_FIELDS = new Set([
  'schemaVersion',
  'documentSchemaVersion',
  'contentVersion',
  'generatedAt',
  'generatorVersion',
  'sourceVersion',
  'sourceMethodologyStatus',
  'publicationScope',
  'municipalFilePattern',
  'horizonStateYear',
  'scanThroughYear',
  'municipalities',
])
const MANIFEST_ENTRY_FIELDS = new Set([
  'ibgeCode',
  'name',
  'uf',
  'slug',
  'path',
  'contentHash',
  'contentVersion',
  'byteSize',
  'publicationStatus',
  'scenarioCount',
  'sourceArtifacts',
])
const SOURCE_ARTIFACT_FIELDS = new Set(['name', 'sha256'])

const DOCUMENT_FIELDS = new Set([
  'schemaVersion',
  'contentVersion',
  'sourceVersion',
  'sourceMethodologyStatus',
  'generatedAt',
  'publicationScope',
  'municipality',
  'page',
  'horizon',
  'howToRead',
  'startingPoint',
  'observedSeries',
  'sharedConditions',
  'scenarios',
  'signals',
  'sources',
  'limitations',
  'provenance',
])
const MUNICIPALITY_FIELDS = new Set(['ibgeCode', 'name', 'uf', 'slug'])
const PAGE_FIELDS = new Set(['eyebrow', 'title', 'description', 'neutralityNote'])
const HORIZON_FIELDS = new Set(['stateYear', 'scanThroughYear', 'stateLabel', 'scanLabel'])
const TEXT_BLOCK_FIELDS = new Set(['label', 'description', 'items'])
const STARTING_POINT_FIELDS = new Set(['label', 'description', 'movements', 'tensions', 'limits'])
const SCENARIO_FIELDS = new Set(['slug', 'title', 'summary', 'sections'])
const SCENARIO_SECTION_FIELDS = new Set(['key', 'label', 'items'])
const SOURCES_FIELDS = new Set(['label', 'description', 'series', 'notes'])
const OBSERVED_SERIES_FIELDS = new Set(['label', 'description', 'items'])
const OBSERVED_SERIE_FIELDS = new Set(['label', 'unitLabel', 'fullPeriod', 'recentWindow'])
const OBSERVED_WINDOW_FIELDS = new Set([
  'startYear',
  'endYear',
  'periodLabel',
  'startValue',
  'endValue',
  'directionLabel',
  'caveat',
])
const SERIES_FIELDS = new Set(['label', 'unitLabel', 'startYear', 'endYear', 'periodLabel'])
const PROVENANCE_FIELDS = new Set([
  'methodologySource',
  'methodologyStatus',
  'publicationScope',
  'artifacts',
])

export class ForesightLoadError extends Error {
  constructor(message, { cause, code, municipalityId = null, path = null, stage }) {
    super(message, { cause })
    this.name = 'ForesightLoadError'
    this.code = code
    this.stage = stage
    this.municipalityId = municipalityId
    this.path = path
  }
}

function invariant(condition, message) {
  if (!condition) throw new Error(`Cenários da educação inválidos: ${message}`)
}

function isRecord(value) {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value)
}

function validateExactFields(value, allowed, label) {
  invariant(isRecord(value), `${label} deve ser um objeto.`)
  for (const key of Object.keys(value)) {
    invariant(allowed.has(key), `${label} traz o campo desconhecido "${key}".`)
  }
  for (const key of allowed) {
    invariant(key in value, `${label} não traz o campo obrigatório "${key}".`)
  }
}

function validateText(value, label, { kind = 'evidence' } = {}) {
  invariant(typeof value === 'string' && value.trim().length > 0, `${label} deve ser um texto não vazio.`)
  invariant(value === value.trim(), `${label} não pode começar nem terminar com espaço.`)
  try {
    assertPublicText(value, { kind, label })
  } catch (error) {
    invariant(false, error instanceof Error ? error.message : String(error))
  }
  return value
}

function validateTextList(value, label, { kind = 'evidence', min = 1 } = {}) {
  invariant(Array.isArray(value), `${label} deve ser uma lista.`)
  invariant(value.length >= min, `${label} precisa de ao menos ${min} item.`)
  const seen = new Set()
  value.forEach((item, index) => {
    validateText(item, `${label}[${index}]`, { kind })
    invariant(!seen.has(item), `${label} repete o mesmo texto.`)
    seen.add(item)
  })
  return value
}

function validateSha256(value, label) {
  invariant(typeof value === 'string' && SHA256_PATTERN.test(value), `${label} deve ser um resumo de 64 caracteres.`)
  return value
}

function validateIbgeCode(value, label) {
  invariant(typeof value === 'string' && IBGE7_PATTERN.test(value), `${label} deve ser o código IBGE textual de 7 dígitos.`)
  return value
}

/*
 * Uma janela observada carrega os dois valores das pontas, já formatados pela
 * materialização, e a direção declarada. Nenhum ano pode ultrapassar o último
 * ano observado: esta é a camada do que aconteceu, não do que virá.
 */
function validateObservedWindow(value, label, { required }) {
  if (value === null) {
    invariant(!required, `${label} é obrigatório.`)
    return null
  }
  validateExactFields(value, OBSERVED_WINDOW_FIELDS, label)
  invariant(
    Number.isInteger(value.startYear) && value.startYear >= 1990 && value.startYear <= LAST_OBSERVED_YEAR,
    `${label}.startYear precisa ser um ano observado.`,
  )
  invariant(
    Number.isInteger(value.endYear) && value.endYear >= value.startYear && value.endYear <= LAST_OBSERVED_YEAR,
    `${label}.endYear precisa ser um ano observado, igual ou posterior ao inicial.`,
  )
  validateText(value.periodLabel, `${label}.periodLabel`)
  validateText(value.startValue, `${label}.startValue`)
  validateText(value.endValue, `${label}.endValue`)
  validateText(value.directionLabel, `${label}.directionLabel`)
  if (value.caveat !== null) validateText(value.caveat, `${label}.caveat`)
  return value
}

function validateMunicipality(value, label) {
  validateExactFields(value, MUNICIPALITY_FIELDS, label)
  validateIbgeCode(value.ibgeCode, `${label}.ibgeCode`)
  validateText(value.name, `${label}.name`)
  invariant(typeof value.uf === 'string' && UF_PATTERN.test(value.uf), `${label}.uf deve ter duas letras maiúsculas.`)
  invariant(typeof value.slug === 'string' && SLUG_PATTERN.test(value.slug), `${label}.slug deve ser um slug de rota.`)
  return value
}

/** Valida o manifesto público e devolve uma cópia congelada. */
export function parseForesightManifest(candidate) {
  validateExactFields(candidate, MANIFEST_FIELDS, 'manifesto')
  invariant(candidate.schemaVersion === FORESIGHT_MANIFEST_SCHEMA, 'esquema do manifesto desconhecido.')
  invariant(candidate.documentSchemaVersion === FORESIGHT_DOCUMENT_SCHEMA, 'esquema do pacote municipal desconhecido.')
  invariant(candidate.sourceVersion === FORESIGHT_SOURCE_VERSION, 'versão de origem inesperada.')
  invariant(candidate.publicationScope === FORESIGHT_PUBLICATION_SCOPE, 'escopo de publicação inesperado.')
  invariant(
    candidate.municipalFilePattern === FORESIGHT_MUNICIPAL_FILE_PATTERN,
    'padrão de caminho municipal inesperado.',
  )
  invariant(candidate.horizonStateYear === HORIZON_STATE_YEAR, 'ano do estado futuro diverge do contrato.')
  invariant(candidate.scanThroughYear === HORIZON_SCAN_YEAR, 'ano final da varredura diverge do contrato.')
  invariant(
    typeof candidate.generatedAt === 'string' && ISO_DATE_PATTERN.test(candidate.generatedAt),
    'manifesto.generatedAt deve ser uma data ISO.',
  )
  invariant(typeof candidate.generatorVersion === 'string' && candidate.generatorVersion.length > 0,
    'manifesto.generatorVersion ausente.')
  invariant(typeof candidate.sourceMethodologyStatus === 'string' && candidate.sourceMethodologyStatus.length > 0,
    'manifesto.sourceMethodologyStatus ausente.')
  validateSha256(candidate.contentVersion, 'manifesto.contentVersion')

  invariant(Array.isArray(candidate.municipalities), 'manifesto.municipalities deve ser uma lista.')
  const codes = new Set()
  candidate.municipalities.forEach((entry, index) => {
    const label = `manifesto.municipalities[${index}]`
    validateExactFields(entry, MANIFEST_ENTRY_FIELDS, label)
    validateIbgeCode(entry.ibgeCode, `${label}.ibgeCode`)
    invariant(!codes.has(entry.ibgeCode), `${label} repete o código ${entry.ibgeCode}.`)
    codes.add(entry.ibgeCode)
    validateText(entry.name, `${label}.name`)
    invariant(typeof entry.uf === 'string' && UF_PATTERN.test(entry.uf), `${label}.uf inválida.`)
    invariant(typeof entry.slug === 'string' && SLUG_PATTERN.test(entry.slug), `${label}.slug inválido.`)
    invariant(
      entry.path === FORESIGHT_MUNICIPAL_FILE_PATTERN.replace('{municipalityId}', entry.ibgeCode),
      `${label}.path não corresponde ao código municipal.`,
    )
    validateSha256(entry.contentHash, `${label}.contentHash`)
    validateSha256(entry.contentVersion, `${label}.contentVersion`)
    invariant(
      Number.isInteger(entry.byteSize) && entry.byteSize > 0,
      `${label}.byteSize deve ser um inteiro positivo.`,
    )
    invariant(entry.publicationStatus === 'published', `${label}.publicationStatus deve ser "published".`)
    invariant(
      entry.scenarioCount === FORESIGHT_SCENARIO_COUNT,
      `${label}.scenarioCount deve ser ${FORESIGHT_SCENARIO_COUNT}.`,
    )
    invariant(Array.isArray(entry.sourceArtifacts) && entry.sourceArtifacts.length > 0,
      `${label}.sourceArtifacts deve listar os documentos de origem.`)
    entry.sourceArtifacts.forEach((artifact, artifactIndex) => {
      const artifactLabel = `${label}.sourceArtifacts[${artifactIndex}]`
      validateExactFields(artifact, SOURCE_ARTIFACT_FIELDS, artifactLabel)
      invariant(typeof artifact.name === 'string' && artifact.name.length > 0, `${artifactLabel}.name ausente.`)
      validateSha256(artifact.sha256, `${artifactLabel}.sha256`)
    })
  })

  return structuredClone(candidate)
}

function parseScenario(candidate, label) {
  validateExactFields(candidate, SCENARIO_FIELDS, label)
  invariant(typeof candidate.slug === 'string' && SLUG_PATTERN.test(candidate.slug), `${label}.slug inválido.`)
  validateText(candidate.title, `${label}.title`)
  validateText(candidate.summary, `${label}.summary`)

  invariant(Array.isArray(candidate.sections), `${label}.sections deve ser uma lista.`)
  const keys = candidate.sections.map((section, index) => {
    const sectionLabel = `${label}.sections[${index}]`
    validateExactFields(section, SCENARIO_SECTION_FIELDS, sectionLabel)
    invariant(
      FORESIGHT_SECTION_KEYS.includes(section.key),
      `${sectionLabel}.key "${section.key}" não pertence à estrutura pública.`,
    )
    validateText(section.label, `${sectionLabel}.label`)
    validateTextList(section.items, `${sectionLabel}.items`)
    return section.key
  })

  invariant(new Set(keys).size === keys.length, `${label} repete uma seção.`)
  const expectedOrder = FORESIGHT_SECTION_KEYS.filter((key) => keys.includes(key))
  invariant(
    expectedOrder.every((key, index) => keys[index] === key),
    `${label} apresenta as seções fora da ordem pública.`,
  )
  for (const required of FORESIGHT_REQUIRED_SECTION_KEYS) {
    invariant(keys.includes(required), `${label} não traz a seção obrigatória "${required}".`)
  }
  return candidate
}

/** Valida o pacote municipal público e devolve uma cópia congelada. */
export function parseForesightDocument(candidate) {
  validateExactFields(candidate, DOCUMENT_FIELDS, 'pacote')
  invariant(candidate.schemaVersion === FORESIGHT_DOCUMENT_SCHEMA, 'esquema do pacote desconhecido.')
  invariant(candidate.sourceVersion === FORESIGHT_SOURCE_VERSION, 'versão de origem inesperada.')
  invariant(candidate.publicationScope === FORESIGHT_PUBLICATION_SCOPE, 'escopo de publicação inesperado.')
  invariant(
    typeof candidate.sourceMethodologyStatus === 'string' && candidate.sourceMethodologyStatus.length > 0,
    'pacote.sourceMethodologyStatus ausente.',
  )
  invariant(
    typeof candidate.generatedAt === 'string' && ISO_DATE_PATTERN.test(candidate.generatedAt),
    'pacote.generatedAt deve ser uma data ISO.',
  )
  validateSha256(candidate.contentVersion, 'pacote.contentVersion')
  validateMunicipality(candidate.municipality, 'pacote.municipality')

  validateExactFields(candidate.page, PAGE_FIELDS, 'pacote.page')
  validateText(candidate.page.eyebrow, 'pacote.page.eyebrow', { kind: 'framing' })
  validateText(candidate.page.title, 'pacote.page.title', { kind: 'framing' })
  validateText(candidate.page.description, 'pacote.page.description', { kind: 'framing' })
  validateText(candidate.page.neutralityNote, 'pacote.page.neutralityNote', { kind: 'framing' })

  validateExactFields(candidate.horizon, HORIZON_FIELDS, 'pacote.horizon')
  invariant(candidate.horizon.stateYear === HORIZON_STATE_YEAR, 'pacote.horizon.stateYear diverge do contrato.')
  invariant(
    candidate.horizon.scanThroughYear === HORIZON_SCAN_YEAR,
    'pacote.horizon.scanThroughYear diverge do contrato.',
  )
  validateText(candidate.horizon.stateLabel, 'pacote.horizon.stateLabel', { kind: 'framing' })
  validateText(candidate.horizon.scanLabel, 'pacote.horizon.scanLabel', { kind: 'framing' })

  validateExactFields(candidate.howToRead, TEXT_BLOCK_FIELDS, 'pacote.howToRead')
  validateText(candidate.howToRead.label, 'pacote.howToRead.label', { kind: 'framing' })
  validateText(candidate.howToRead.description, 'pacote.howToRead.description', { kind: 'framing' })
  validateTextList(candidate.howToRead.items, 'pacote.howToRead.items', { kind: 'framing' })

  validateExactFields(candidate.startingPoint, STARTING_POINT_FIELDS, 'pacote.startingPoint')
  validateText(candidate.startingPoint.label, 'pacote.startingPoint.label', { kind: 'framing' })
  validateText(candidate.startingPoint.description, 'pacote.startingPoint.description', { kind: 'framing' })
  validateTextList(candidate.startingPoint.movements, 'pacote.startingPoint.movements')
  validateTextList(candidate.startingPoint.tensions, 'pacote.startingPoint.tensions')
  validateTextList(candidate.startingPoint.limits, 'pacote.startingPoint.limits')

  validateExactFields(candidate.observedSeries, OBSERVED_SERIES_FIELDS, 'pacote.observedSeries')
  validateText(candidate.observedSeries.label, 'pacote.observedSeries.label', { kind: 'framing' })
  validateText(candidate.observedSeries.description, 'pacote.observedSeries.description', { kind: 'framing' })
  invariant(
    Array.isArray(candidate.observedSeries.items) && candidate.observedSeries.items.length > 0,
    'pacote.observedSeries.items deve listar as séries observadas.',
  )
  candidate.observedSeries.items.forEach((serie, index) => {
    const label = `pacote.observedSeries.items[${index}]`
    validateExactFields(serie, OBSERVED_SERIE_FIELDS, label)
    validateText(serie.label, `${label}.label`)
    validateText(serie.unitLabel, `${label}.unitLabel`)
    validateObservedWindow(serie.fullPeriod, `${label}.fullPeriod`, { required: true })
    validateObservedWindow(serie.recentWindow, `${label}.recentWindow`, { required: false })
  })

  validateExactFields(candidate.sharedConditions, TEXT_BLOCK_FIELDS, 'pacote.sharedConditions')
  validateText(candidate.sharedConditions.label, 'pacote.sharedConditions.label', { kind: 'framing' })
  validateText(candidate.sharedConditions.description, 'pacote.sharedConditions.description', { kind: 'framing' })
  validateTextList(candidate.sharedConditions.items, 'pacote.sharedConditions.items')

  invariant(Array.isArray(candidate.scenarios), 'pacote.scenarios deve ser uma lista.')
  invariant(
    candidate.scenarios.length === FORESIGHT_SCENARIO_COUNT,
    `pacote.scenarios deve trazer exatamente ${FORESIGHT_SCENARIO_COUNT} cenários.`,
  )
  const slugs = new Set()
  const titles = new Set()
  candidate.scenarios.forEach((scenario, index) => {
    parseScenario(scenario, `pacote.scenarios[${index}]`)
    invariant(!slugs.has(scenario.slug), `pacote.scenarios repete o identificador de rota "${scenario.slug}".`)
    invariant(!titles.has(scenario.title), `pacote.scenarios repete o título "${scenario.title}".`)
    slugs.add(scenario.slug)
    titles.add(scenario.title)
  })

  validateExactFields(candidate.signals, TEXT_BLOCK_FIELDS, 'pacote.signals')
  validateText(candidate.signals.label, 'pacote.signals.label', { kind: 'framing' })
  validateText(candidate.signals.description, 'pacote.signals.description', { kind: 'framing' })
  validateTextList(candidate.signals.items, 'pacote.signals.items')

  validateExactFields(candidate.sources, SOURCES_FIELDS, 'pacote.sources')
  validateText(candidate.sources.label, 'pacote.sources.label', { kind: 'framing' })
  validateText(candidate.sources.description, 'pacote.sources.description', { kind: 'framing' })
  invariant(Array.isArray(candidate.sources.series) && candidate.sources.series.length > 0,
    'pacote.sources.series deve listar as séries usadas.')
  candidate.sources.series.forEach((serie, index) => {
    const label = `pacote.sources.series[${index}]`
    validateExactFields(serie, SERIES_FIELDS, label)
    validateText(serie.label, `${label}.label`)
    validateText(serie.unitLabel, `${label}.unitLabel`)
    invariant(
      Number.isInteger(serie.startYear) && serie.startYear >= 1990 && serie.startYear <= LAST_OBSERVED_YEAR,
      `${label}.startYear precisa ser um ano observado.`,
    )
    invariant(
      Number.isInteger(serie.endYear) && serie.endYear >= serie.startYear && serie.endYear <= LAST_OBSERVED_YEAR,
      `${label}.endYear precisa ser um ano observado, igual ou posterior ao inicial.`,
    )
    validateText(serie.periodLabel, `${label}.periodLabel`)
  })
  validateTextList(candidate.sources.notes, 'pacote.sources.notes', { kind: 'framing' })

  validateExactFields(candidate.limitations, TEXT_BLOCK_FIELDS, 'pacote.limitations')
  validateText(candidate.limitations.label, 'pacote.limitations.label', { kind: 'framing' })
  validateText(candidate.limitations.description, 'pacote.limitations.description', { kind: 'framing' })
  validateTextList(candidate.limitations.items, 'pacote.limitations.items', { kind: 'framing' })

  validateExactFields(candidate.provenance, PROVENANCE_FIELDS, 'pacote.provenance')
  invariant(candidate.provenance.methodologySource === FORESIGHT_SOURCE_VERSION,
    'pacote.provenance.methodologySource diverge da versão de origem.')
  invariant(typeof candidate.provenance.methodologyStatus === 'string'
    && candidate.provenance.methodologyStatus.length > 0, 'pacote.provenance.methodologyStatus ausente.')
  invariant(candidate.provenance.publicationScope === FORESIGHT_PUBLICATION_SCOPE,
    'pacote.provenance.publicationScope inesperado.')
  invariant(Array.isArray(candidate.provenance.artifacts) && candidate.provenance.artifacts.length > 0,
    'pacote.provenance.artifacts deve listar os documentos de origem.')
  candidate.provenance.artifacts.forEach((artifact, index) => {
    const label = `pacote.provenance.artifacts[${index}]`
    validateExactFields(artifact, SOURCE_ARTIFACT_FIELDS, label)
    invariant(typeof artifact.name === 'string' && artifact.name.length > 0, `${label}.name ausente.`)
    validateSha256(artifact.sha256, `${label}.sha256`)
  })

  return structuredClone(candidate)
}

/*
 * Versão de conteúdo: resumo determinístico do corpo do pacote, calculado sem
 * o próprio campo. Gerador e loader precisam concordar byte a byte, por isso a
 * serialização usa chaves ordenadas.
 */
function canonicalize(value) {
  if (Array.isArray(value)) return value.map(canonicalize)
  if (isRecord(value)) {
    return Object.keys(value)
      .sort()
      .reduce((accumulator, key) => {
        accumulator[key] = canonicalize(value[key])
        return accumulator
      }, {})
  }
  return value
}

export function serializeForContentVersion(document) {
  const body = { ...document }
  delete body.contentVersion
  return JSON.stringify(canonicalize(body))
}

const HEX = Array.from({ length: 256 }, (_, index) => index.toString(16).padStart(2, '0'))

function toHex(buffer) {
  let output = ''
  for (const byte of new Uint8Array(buffer)) output += HEX[byte]
  return output
}

/** SHA-256 de um texto UTF-8, ou `null` quando a plataforma não oferece o cálculo. */
export async function digestText(text) {
  const subtle = globalThis.crypto?.subtle
  if (!subtle) return null
  const bytes = new TextEncoder().encode(text)
  return toHex(await subtle.digest('SHA-256', bytes))
}

async function defaultFetchText(path, options) {
  const response = await fetch(path, options)
  if (!response.ok) throw new Error(`Falha ao carregar ${path}: HTTP ${response.status}.`)
  return response.text()
}

function structuredError(error, details) {
  if (error instanceof ForesightLoadError) return error
  return new ForesightLoadError(
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
export function createForesightEducacaoLoader({
  fetchText = defaultFetchText,
  logger = console.error,
} = {}) {
  const documentCache = new Map()
  const reportedErrors = new Set()
  let manifestPending = null
  let manifestResolved = null

  function reportOnce(error) {
    const key = [error.code, error.stage, error.municipalityId, error.path, error.message].join(':')
    if (reportedErrors.has(key)) return
    reportedErrors.add(key)
    logger(error)
  }

  function loadManifest() {
    if (manifestResolved) return manifestResolved
    if (manifestPending) return manifestPending
    manifestPending = Promise.resolve()
      .then(() => fetchText(FORESIGHT_MANIFEST_PATH, { cache: 'no-store' }))
      .catch((error) => {
        throw structuredError(error, {
          code: 'manifest_unavailable',
          path: FORESIGHT_MANIFEST_PATH,
          stage: 'manifest',
        })
      })
      .then((raw) => {
        try {
          return parseForesightManifest(JSON.parse(raw))
        } catch (error) {
          throw structuredError(error, {
            code: 'invalid_manifest',
            path: FORESIGHT_MANIFEST_PATH,
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

  function findEntry(manifest, municipalityId) {
    return manifest.municipalities.find((entry) => entry.ibgeCode === municipalityId) ?? null
  }

  async function loadDocument(municipalityId) {
    const manifest = await loadManifest()
    const entry = findEntry(manifest, municipalityId)
    if (!entry) {
      throw new ForesightLoadError(
        `Os cenários da educação não estão publicados para ${municipalityId}.`,
        { code: 'municipality_not_published', municipalityId, stage: 'manifest' },
      )
    }

    return memoized(documentCache, `${entry.contentHash}:${municipalityId}`, async () => {
      const path = FORESIGHT_MUNICIPAL_PATH.replace('{municipalityId}', municipalityId)
      let raw
      try {
        raw = await fetchText(path)
      } catch (error) {
        throw structuredError(error, {
          code: 'municipality_unavailable',
          municipalityId,
          path,
          stage: 'municipality',
        })
      }

      let integrity = 'declared'
      try {
        const digest = await digestText(raw)
        if (digest !== null) {
          invariant(digest === entry.contentHash, `resumo do arquivo diverge do manifesto em ${municipalityId}.`)
          integrity = 'verified'
        }
        const document = parseForesightDocument(JSON.parse(raw))
        invariant(
          document.municipality.ibgeCode === municipalityId,
          `o arquivo carregado pertence a outro município: ${document.municipality.ibgeCode}.`,
        )
        invariant(
          document.municipality.name === entry.name
            && document.municipality.uf === entry.uf
            && document.municipality.slug === entry.slug,
          `identidade municipal divergente do manifesto em ${municipalityId}.`,
        )
        invariant(
          document.contentVersion === entry.contentVersion,
          `versão de conteúdo divergente do manifesto em ${municipalityId}.`,
        )
        invariant(
          document.schemaVersion === manifest.documentSchemaVersion,
          `esquema do pacote diverge do manifesto em ${municipalityId}.`,
        )
        invariant(
          document.sourceVersion === manifest.sourceVersion
            && document.generatedAt === manifest.generatedAt,
          `origem ou data divergentes do manifesto em ${municipalityId}.`,
        )
        invariant(
          document.scenarios.length === entry.scenarioCount,
          `quantidade de cenários divergente do manifesto em ${municipalityId}.`,
        )
        return { document, entry, integrity }
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

  /** Códigos IBGE com cenário publicado, na ordem do manifesto. */
  function listPublishedMunicipalityIds() {
    return loadManifest()
      .then((manifest) => manifest.municipalities.map((entry) => entry.ibgeCode))
      .catch((error) => {
        reportOnce(structuredError(error, { code: 'manifest_unavailable', stage: 'manifest' }))
        return []
      })
  }

  function load(municipalityId) {
    const normalizedId = String(municipalityId ?? '')
    if (!IBGE7_PATTERN.test(normalizedId)) {
      const error = new ForesightLoadError(`Código municipal inválido: ${normalizedId}.`, {
        code: 'invalid_municipality',
        municipalityId: normalizedId,
        stage: 'input',
      })
      reportOnce(error)
      return Promise.reject(error)
    }
    return loadDocument(normalizedId)
      .then(({ document, entry, integrity }) => ({
        schemaVersion: 'foresight-educacao-loader-result-v1',
        municipalityId: normalizedId,
        municipalityName: document.municipality.name,
        contentHash: entry.contentHash,
        contentVersion: entry.contentVersion,
        integrity,
        document,
      }))
      .catch((error) => {
        const structured = structuredError(error, {
          code: 'unexpected_failure',
          municipalityId: normalizedId,
          stage: 'municipality',
        })
        reportOnce(structured)
        throw structured
      })
  }

  return { listPublishedMunicipalityIds, load, loadManifest }
}
