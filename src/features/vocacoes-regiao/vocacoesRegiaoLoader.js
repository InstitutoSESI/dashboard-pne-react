/*
 * Leitura do Vocações da Região publicado em `public/data/vocacoes-regiao/`.
 *
 * O slot existiu antes do conteúdo, e o manifesto vazio continua sendo um
 * estado válido: enquanto nenhuma região constar dele, não há item de menu,
 * não há rota alcançável e não há pacote a ler — fail-closed por ausência, sem
 * página vazia e sem erro no console. Nada disso mudou com a publicação da
 * Fase A; o que mudou é que agora há regiões no manifesto.
 *
 * A validação do pacote vive em `vocacoesRegiaoContract.js`, que é o contrato
 * público `vocacoes-regiao-2.3.0`. Este módulo cuida do que é leitura: buscar,
 * conferir o resumo do arquivo contra o manifesto, casar identidade e versão de
 * conteúdo, e memorizar. A separação importa — o contrato precisa rodar também
 * no gerador, em Node, sem nada de rede.
 */

import {
  VOCACOES_DOCUMENT_SCHEMA,
  createVocacoesDocumentParser as createContractParser,
  validateRegionIdentity,
} from './vocacoesRegiaoContract.js'

export const VOCACOES_MANIFEST_PATH = '/data/vocacoes-regiao/manifest.json'
export const VOCACOES_REGION_PATH = '/data/vocacoes-regiao/regioes/{regionSlug}.json'
export const VOCACOES_REGION_FILE_PATTERN = 'regioes/{regionSlug}.json'

/*
 * `v2` porque a entrada de região ganhou dois campos obrigatórios com o Bloco 4,
 * e o conjunto de campos da entrada é fechado. Manifesto cujo formato mudou e
 * cuja versão não mudou é a maneira mais silenciosa de um leitor antigo aceitar
 * um arquivo que não entende.
 */
export const VOCACOES_MANIFEST_SCHEMA = 'vocacoes-regiao-manifest-v2'
export const VOCACOES_SCOPE_TYPE = 'region'

export { VOCACOES_DOCUMENT_SCHEMA, validateRegionIdentity }

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
  'referenceYear',
  'referenceMonth',
  'regionFilePattern',
  'stateCode',
  'regions',
])
/*
 * A contagem por bloco substitui a contagem de cenários da versão `1.0.0`. Ela
 * não é enfeite de manifesto: é o que permite ao leitor recusar um pacote que
 * perdeu um bloco pelo caminho sem precisar abrir o arquivo inteiro — e é a
 * razão de o manifesto declarar três números em vez de um.
 */
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
  'seriesCount',
  'associationCount',
  'temporalPairCount',
  /*
   * O Bloco 4 contado de fora do documento. `scenarioStatus` diz em qual dos
   * dois estados a região está e `scenarioCount` diz quantos cenários ela
   * publica — zero quando não publica nenhum. Sem os dois, uma região que
   * perdesse o bloco pelo caminho seria indistinguível de uma região que nunca
   * o teve, e a diferença entre as duas é justamente o que o plano manda
   * declarar de forma verificável.
   */
  'scenarioStatus',
  'scenarioCount',
])

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
  invariant(
    Number.isInteger(candidate.referenceYear) && candidate.referenceYear >= 2000,
    'manifesto.referenceYear deve ser um ano.',
  )
  /*
   * O mês de referência não é enfeite: sem ele, um ponto de dezembro do ano de
   * referência — mês que ainda não aconteceu — passaria pela regra do período
   * futuro, porque o ano não é futuro.
   */
  invariant(
    Number.isInteger(candidate.referenceMonth)
      && candidate.referenceMonth >= 1 && candidate.referenceMonth <= 12,
    'manifesto.referenceMonth deve estar entre 1 e 12.',
  )

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
      entry.scenarioStatus === 'published' || entry.scenarioStatus === 'absent',
      `${label}.scenarioStatus deve ser "published" ou "absent".`,
    )
    invariant(
      Number.isInteger(entry.scenarioCount) && entry.scenarioCount >= 0,
      `${label}.scenarioCount deve ser inteiro não negativo.`,
    )
    /* Os dois campos precisam concordar nos dois sentidos: contar cenário sem
     * declarar publicação, ou declarar publicação e contar zero, são os dois
     * jeitos de o manifesto mentir sobre o Bloco 4. */
    invariant(
      (entry.scenarioStatus === 'published') === (entry.scenarioCount > 0),
      `${label}.scenarioStatus e ${label}.scenarioCount não concordam.`,
    )
    for (const field of ['seriesCount', 'associationCount', 'temporalPairCount']) {
      invariant(
        Number.isInteger(entry[field]) && entry[field] > 0,
        `${label}.${field} deve ser inteiro positivo.`,
      )
    }
    return Object.freeze({ ...entry })
  })

  return Object.freeze({ ...candidate, regions: Object.freeze(regions) })
}

/*
 * O validador de pacote nasce do manifesto: é ele que declara a versão de
 * origem, o escopo de publicação e o ano de referência que o pacote precisa
 * repetir. Assim o leitor aceita a próxima versão da origem sem que este
 * arquivo precise saber qual será o número dela.
 */
export function createVocacoesDocumentParser(manifest) {
  return createContractParser({
    documentSchema: manifest.documentSchemaVersion,
    sourceVersion: manifest.sourceVersion,
    publicationScope: manifest.publicationScope,
    referenceYear: manifest.referenceYear,
    referenceMonth: manifest.referenceMonth,
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
  /*
   * Regiões retratadas. O manifesto é uma promessa barata — ele declara o que
   * *deveria* estar publicado, e é o que decide o menu sem baixar dez pacotes.
   * Quando o pacote de uma região não sustenta a promessa (resumo divergente,
   * identidade trocada, campo fora do contrato), o manifesto sozinho deixaria a
   * região no menu e a página em branco. A retratação fecha esse vão: a região
   * sai do conjunto publicado, o item some e a rota volta para o Panorama.
   *
   * É deliberadamente irreversível dentro da sessão. Um pacote que falhou a
   * validação uma vez não passa a valer porque uma segunda leitura deu certo.
   */
  const retracted = new Set()
  const listeners = new Set()
  let manifestPending = null
  let manifestResolved = null

  function retract(regionSlug) {
    if (retracted.has(regionSlug)) return
    retracted.add(regionSlug)
    for (const listener of listeners) listener()
  }

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
      .then((manifest) => manifest.regions
        .map((entry) => entry.slug)
        .filter((slug) => !retracted.has(slug)))
      .catch((error) => {
        reportOnce(structuredError(error, { code: 'manifest_unavailable', stage: 'manifest' }))
        return []
      })
  }

  /** Avisa quando o conjunto publicado encolhe, para a navegação reagir. */
  function subscribe(listener) {
    listeners.add(listener)
    return () => listeners.delete(listener)
  }

  async function loadRegion(regionSlug) {
    const manifest = await loadManifest()
    const entry = retracted.has(regionSlug)
      ? null
      : manifest.regions.find((candidate) => candidate.slug === regionSlug) ?? null
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
        retract(regionSlug)
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
        /*
         * Os três blocos conferidos contra o manifesto. Um pacote que perdeu
         * um bloco pelo caminho ainda seria um documento válido — o contrato
         * exige "ao menos um" de cada — e passaria sem esta conferência. O
         * manifesto é quem sabe quantos deveriam estar lá.
         */
        invariant(
          document.territoryPortrait.series.length === entry.seriesCount,
          `quantidade de séries divergente do manifesto em ${regionSlug}.`,
        )
        invariant(
          document.associations.items.length === entry.associationCount,
          `quantidade de associações divergente do manifesto em ${regionSlug}.`,
        )
        invariant(
          document.temporalPairs.items.length === entry.temporalPairCount,
          `quantidade de pares temporais divergente do manifesto em ${regionSlug}.`,
        )
        return { document, entry, integrity }
      } catch (error) {
        /*
         * Retratar antes de propagar: quem esperar o erro para decidir chega
         * tarde, porque a navegacao ja se decidiu pelo manifesto.
         */
        retract(regionSlug)
        throw structuredError(error, { code: 'invalid_payload', regionSlug, path, stage: 'region' })
      }
    })
  }

  return { listPublishedRegionSlugs, loadManifest, loadRegion, subscribe }
}
