/*
 * Leitura do painel regional publicado em `public/data/regioes/`.
 *
 * O manifesto é a única porta de entrada: ele decide quais regiões existem e
 * com que conteúdo. O arquivo da região só é aceito depois de conferir o
 * resumo do próprio arquivo, a identidade da região, a versão de conteúdo e o
 * esquema declarado. Toda falha vira erro estruturado e nada é exibido.
 *
 * Este módulo não agrega, não recalcula percentual, não completa ano faltante
 * e não recorre a outra região. Ele lê o que o gerador determinístico
 * publicou — inclusive os nulos, que continuam nulos.
 */

export const REGIOES_MANIFEST_PATH = '/data/regioes/manifest.json'
export const REGIOES_REGION_PATH = '/data/regioes/{regionSlug}.json'

export const REGIOES_MANIFEST_SCHEMA = 'regioes-manifest-v1'
export const REGIOES_DOCUMENT_SCHEMA = 'regioes-1.0.0'

const SHA256_PATTERN = /^[a-f0-9]{64}$/
const SLUG_PATTERN = /^[a-z0-9]+(?:-[a-z0-9]+)*$/
const IBGE7_PATTERN = /^\d{7}$/
const ISO_DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/

const MANIFEST_FIELDS = new Set([
  'schemaVersion',
  'documentSchemaVersion',
  'generatorVersion',
  'generatedAt',
  'stateCode',
  'regionFilePattern',
  'regionCount',
  'municipalityCount',
  'regions',
])
const MANIFEST_ENTRY_FIELDS = new Set([
  'slug',
  'name',
  'path',
  'municipalityCount',
  'contentHash',
  'contentVersion',
  'byteSize',
])
const DOCUMENT_FIELDS = new Set([
  'schemaVersion',
  'generatorVersion',
  'generatedAt',
  'stateCode',
  'regiao',
  'pagina',
  'atendimento',
  'matriculas',
  'metodologia',
  'fontes',
  'contentVersion',
])
const REGION_FIELDS = new Set(['slug', 'nome', 'totalMunicipios', 'municipios'])
const REGION_MUNICIPALITY_FIELDS = new Set(['ibgeCode', 'nome', 'slug'])
const PAGE_FIELDS = new Set(['eyebrow', 'titulo', 'descricao'])
const COVERAGE_FIELDS = new Set(['label', 'descricao', 'indicadores'])
const INDICATOR_FIELDS = new Set([
  'chave',
  'titulo',
  'faixaEtaria',
  'unidade',
  'baseTerritorial',
  'campos',
  'ultimoAno',
  'valorUltimoAno',
  'series',
])
const COVERAGE_POINT_FIELDS = new Set([
  'ano',
  'numerador',
  'denominador',
  'valor',
  'municipiosComDado',
])
const ENROLLMENT_FIELDS = new Set([
  'label',
  'descricao',
  'ultimoAno',
  'totalUltimoAno',
  'series',
])
const ENROLLMENT_BREAKDOWN_KEYS = ['por_etapa', 'por_dependencia', 'por_localizacao']
const SOURCE_FIELDS = new Set(['nome', 'uso'])

/** Erro de carga do painel regional, sempre com estágio e código. */
export class RegionalLoadError extends Error {
  constructor(message, { code, stage, regionSlug = null, path = null, cause } = {}) {
    super(message, cause === undefined ? undefined : { cause })
    this.name = 'RegionalLoadError'
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

function assertExactFields(value, expected, label) {
  invariant(isRecord(value), `${label}: deve ser um objeto.`)
  const actual = Object.keys(value)
  invariant(
    actual.length === expected.size && actual.every((field) => expected.has(field)),
    `${label}: campos divergentes; esperados ${[...expected].toSorted().join(', ')}.`,
  )
}

function readText(value, field, label) {
  const text = value[field]
  invariant(typeof text === 'string' && text.trim() !== '', `${label}: "${field}" deve ser texto não vazio.`)
  return text
}

function readInteger(value, field, label) {
  const number = value[field]
  invariant(Number.isInteger(number), `${label}: "${field}" deve ser inteiro.`)
  return number
}

/** Número ou null. Ausência nunca vira zero. */
function readNullableNumber(value, field, label) {
  const number = value[field]
  if (number === null) return null
  invariant(
    typeof number === 'number' && Number.isFinite(number),
    `${label}: "${field}" deve ser número finito ou null.`,
  )
  return number
}

function readNullableInteger(value, field, label) {
  const number = value[field]
  if (number === null) return null
  invariant(Number.isInteger(number), `${label}: "${field}" deve ser inteiro ou null.`)
  return number
}

export function parseRegioesManifest(candidate) {
  const label = 'Manifesto do painel regional inválido'
  assertExactFields(candidate, MANIFEST_FIELDS, label)
  invariant(
    candidate.schemaVersion === REGIOES_MANIFEST_SCHEMA,
    `${label}: schemaVersion deve ser ${REGIOES_MANIFEST_SCHEMA}.`,
  )
  invariant(
    candidate.documentSchemaVersion === REGIOES_DOCUMENT_SCHEMA,
    `${label}: documentSchemaVersion deve ser ${REGIOES_DOCUMENT_SCHEMA}.`,
  )
  readText(candidate, 'generatorVersion', label)
  const generatedAt = readText(candidate, 'generatedAt', label)
  invariant(ISO_DATE_PATTERN.test(generatedAt), `${label}: generatedAt deve ser data ISO.`)
  const stateCode = readText(candidate, 'stateCode', label)
  invariant(/^[A-Z]{2}$/.test(stateCode), `${label}: stateCode deve ter duas letras maiúsculas.`)
  readText(candidate, 'regionFilePattern', label)
  const regionCount = readInteger(candidate, 'regionCount', label)
  const municipalityCount = readInteger(candidate, 'municipalityCount', label)
  invariant(regionCount > 0, `${label}: regionCount deve ser positivo.`)
  invariant(municipalityCount > 0, `${label}: municipalityCount deve ser positivo.`)
  invariant(
    Array.isArray(candidate.regions) && candidate.regions.length === regionCount,
    `${label}: regions deve cobrir exatamente regionCount.`,
  )

  const slugs = new Set()
  let coveredMunicipalities = 0
  const regions = candidate.regions.map((rawEntry, index) => {
    const entryLabel = `${label}: região na posição ${index + 1}`
    assertExactFields(rawEntry, MANIFEST_ENTRY_FIELDS, entryLabel)
    const slug = readText(rawEntry, 'slug', entryLabel)
    invariant(SLUG_PATTERN.test(slug), `${entryLabel}: slug fora do padrão.`)
    invariant(!slugs.has(slug), `${entryLabel}: slug duplicado ${slug}.`)
    slugs.add(slug)
    const name = readText(rawEntry, 'name', entryLabel)
    const path = readText(rawEntry, 'path', entryLabel)
    invariant(path === `${slug}.json`, `${entryLabel}: path deve ser ${slug}.json.`)
    const entryMunicipalityCount = readInteger(rawEntry, 'municipalityCount', entryLabel)
    invariant(entryMunicipalityCount > 0, `${entryLabel}: municipalityCount deve ser positivo.`)
    coveredMunicipalities += entryMunicipalityCount
    const contentHash = readText(rawEntry, 'contentHash', entryLabel)
    invariant(SHA256_PATTERN.test(contentHash), `${entryLabel}: contentHash deve ser sha256.`)
    const contentVersion = readText(rawEntry, 'contentVersion', entryLabel)
    invariant(SHA256_PATTERN.test(contentVersion), `${entryLabel}: contentVersion deve ser sha256.`)
    const byteSize = readInteger(rawEntry, 'byteSize', entryLabel)
    invariant(byteSize > 0, `${entryLabel}: byteSize deve ser positivo.`)
    return Object.freeze({
      slug,
      name,
      path,
      municipalityCount: entryMunicipalityCount,
      contentHash,
      contentVersion,
      byteSize,
    })
  })
  invariant(
    coveredMunicipalities === municipalityCount,
    `${label}: a soma das regiões cobre ${coveredMunicipalities} municípios, e não ${municipalityCount}.`,
  )

  return Object.freeze({
    schemaVersion: candidate.schemaVersion,
    documentSchemaVersion: candidate.documentSchemaVersion,
    generatorVersion: candidate.generatorVersion,
    generatedAt,
    stateCode,
    regionFilePattern: candidate.regionFilePattern,
    regionCount,
    municipalityCount,
    regions: Object.freeze(regions),
  })
}

function parseCoverageSeries(candidate, label) {
  invariant(Array.isArray(candidate) && candidate.length > 0, `${label}: série deve ser lista não vazia.`)
  let previousYear = null
  return Object.freeze(
    candidate.map((rawPoint, index) => {
      const pointLabel = `${label}: ponto ${index + 1}`
      assertExactFields(rawPoint, COVERAGE_POINT_FIELDS, pointLabel)
      const year = readInteger(rawPoint, 'ano', pointLabel)
      invariant(previousYear === null || year > previousYear, `${pointLabel}: anos fora de ordem.`)
      previousYear = year
      const numerator = readNullableNumber(rawPoint, 'numerador', pointLabel)
      const denominator = readNullableNumber(rawPoint, 'denominador', pointLabel)
      const value = readNullableNumber(rawPoint, 'valor', pointLabel)
      const municipalitiesWithData = readInteger(rawPoint, 'municipiosComDado', pointLabel)
      invariant(
        (numerator === null) === (value === null) && (denominator === null) === (value === null),
        `${pointLabel}: numerador, denominador e valor devem estar todos presentes ou todos nulos.`,
      )
      return Object.freeze({
        ano: year,
        numerador: numerator,
        denominador: denominator,
        valor: value,
        municipiosComDado: municipalitiesWithData,
      })
    }),
  )
}

function parseCountSeries(candidate, label, { withPercent = false } = {}) {
  invariant(Array.isArray(candidate) && candidate.length > 0, `${label}: série deve ser lista não vazia.`)
  const expected = withPercent
    ? new Set(['ano', 'valor', 'municipiosComDado', 'percentual'])
    : new Set(['ano', 'valor', 'municipiosComDado'])
  let previousYear = null
  return Object.freeze(
    candidate.map((rawPoint, index) => {
      const pointLabel = `${label}: ponto ${index + 1}`
      assertExactFields(rawPoint, expected, pointLabel)
      const year = readInteger(rawPoint, 'ano', pointLabel)
      invariant(previousYear === null || year > previousYear, `${pointLabel}: anos fora de ordem.`)
      previousYear = year
      const point = {
        ano: year,
        valor: readNullableNumber(rawPoint, 'valor', pointLabel),
        municipiosComDado: readInteger(rawPoint, 'municipiosComDado', pointLabel),
      }
      if (withPercent) point.percentual = readNullableNumber(rawPoint, 'percentual', pointLabel)
      return Object.freeze(point)
    }),
  )
}

export function parseRegiaoDocument(candidate) {
  const label = 'Painel regional inválido'
  assertExactFields(candidate, DOCUMENT_FIELDS, label)
  invariant(
    candidate.schemaVersion === REGIOES_DOCUMENT_SCHEMA,
    `${label}: schemaVersion deve ser ${REGIOES_DOCUMENT_SCHEMA}.`,
  )
  readText(candidate, 'generatorVersion', label)
  const generatedAt = readText(candidate, 'generatedAt', label)
  invariant(ISO_DATE_PATTERN.test(generatedAt), `${label}: generatedAt deve ser data ISO.`)
  const stateCode = readText(candidate, 'stateCode', label)
  const contentVersion = readText(candidate, 'contentVersion', label)
  invariant(SHA256_PATTERN.test(contentVersion), `${label}: contentVersion deve ser sha256.`)

  const rawRegion = candidate.regiao
  assertExactFields(rawRegion, REGION_FIELDS, `${label}: regiao`)
  const slug = readText(rawRegion, 'slug', `${label}: regiao`)
  invariant(SLUG_PATTERN.test(slug), `${label}: regiao.slug fora do padrão.`)
  const name = readText(rawRegion, 'nome', `${label}: regiao`)
  const totalMunicipalities = readInteger(rawRegion, 'totalMunicipios', `${label}: regiao`)
  invariant(
    Array.isArray(rawRegion.municipios) && rawRegion.municipios.length === totalMunicipalities,
    `${label}: regiao.municipios deve cobrir totalMunicipios.`,
  )
  const seenCodes = new Set()
  const municipalities = Object.freeze(
    rawRegion.municipios.map((rawMunicipality, index) => {
      const municipalityLabel = `${label}: município na posição ${index + 1}`
      assertExactFields(rawMunicipality, REGION_MUNICIPALITY_FIELDS, municipalityLabel)
      const ibgeCode = readText(rawMunicipality, 'ibgeCode', municipalityLabel)
      invariant(IBGE7_PATTERN.test(ibgeCode), `${municipalityLabel}: ibgeCode deve ter sete dígitos.`)
      invariant(!seenCodes.has(ibgeCode), `${municipalityLabel}: município repetido ${ibgeCode}.`)
      seenCodes.add(ibgeCode)
      return Object.freeze({
        ibgeCode,
        nome: readText(rawMunicipality, 'nome', municipalityLabel),
        slug: readText(rawMunicipality, 'slug', municipalityLabel),
      })
    }),
  )

  assertExactFields(candidate.pagina, PAGE_FIELDS, `${label}: pagina`)
  const page = Object.freeze({
    eyebrow: readText(candidate.pagina, 'eyebrow', `${label}: pagina`),
    titulo: readText(candidate.pagina, 'titulo', `${label}: pagina`),
    descricao: readText(candidate.pagina, 'descricao', `${label}: pagina`),
  })

  assertExactFields(candidate.atendimento, COVERAGE_FIELDS, `${label}: atendimento`)
  invariant(
    Array.isArray(candidate.atendimento.indicadores) && candidate.atendimento.indicadores.length > 0,
    `${label}: atendimento.indicadores deve ser lista não vazia.`,
  )
  const indicators = Object.freeze(
    candidate.atendimento.indicadores.map((rawIndicator, index) => {
      const indicatorLabel = `${label}: indicador na posição ${index + 1}`
      assertExactFields(rawIndicator, INDICATOR_FIELDS, indicatorLabel)
      invariant(rawIndicator.unidade === 'percent', `${indicatorLabel}: unidade deve ser percent.`)
      assertExactFields(
        rawIndicator.baseTerritorial,
        new Set(['numerador', 'denominador']),
        `${indicatorLabel}: baseTerritorial`,
      )
      assertExactFields(
        rawIndicator.campos,
        new Set(['numerador', 'denominador']),
        `${indicatorLabel}: campos`,
      )
      const series = parseCoverageSeries(rawIndicator.series, indicatorLabel)
      const lastYear = readNullableInteger(rawIndicator, 'ultimoAno', indicatorLabel)
      const lastValue = readNullableNumber(rawIndicator, 'valorUltimoAno', indicatorLabel)
      const observed = series.findLast((point) => point.valor !== null) ?? null
      invariant(
        (observed === null && lastYear === null && lastValue === null)
          || (observed !== null && observed.ano === lastYear && observed.valor === lastValue),
        `${indicatorLabel}: ultimoAno e valorUltimoAno devem refletir o último ano com valor.`,
      )
      return Object.freeze({
        chave: readText(rawIndicator, 'chave', indicatorLabel),
        titulo: readText(rawIndicator, 'titulo', indicatorLabel),
        faixaEtaria: readText(rawIndicator, 'faixaEtaria', indicatorLabel),
        unidade: 'percent',
        baseTerritorial: Object.freeze({ ...rawIndicator.baseTerritorial }),
        campos: Object.freeze({ ...rawIndicator.campos }),
        ultimoAno: lastYear,
        valorUltimoAno: lastValue,
        series,
      })
    }),
  )

  assertExactFields(candidate.matriculas, ENROLLMENT_FIELDS, `${label}: matriculas`)
  const rawSeries = candidate.matriculas.series
  invariant(isRecord(rawSeries), `${label}: matriculas.series deve ser objeto.`)
  const seriesKeys = Object.keys(rawSeries).toSorted()
  invariant(
    seriesKeys.length === ENROLLMENT_BREAKDOWN_KEYS.length + 2
      && seriesKeys.includes('total')
      && seriesKeys.includes('integral')
      && ENROLLMENT_BREAKDOWN_KEYS.every((key) => seriesKeys.includes(key)),
    `${label}: matriculas.series deve trazer total, integral e os recortes declarados.`,
  )
  const enrollmentSeries = {
    total: parseCountSeries(rawSeries.total, `${label}: matriculas.total`),
    integral: parseCountSeries(rawSeries.integral, `${label}: matriculas.integral`, {
      withPercent: true,
    }),
  }
  for (const key of ENROLLMENT_BREAKDOWN_KEYS) {
    const rawBreakdown = rawSeries[key]
    invariant(isRecord(rawBreakdown), `${label}: matriculas.${key} deve ser objeto.`)
    const categories = Object.keys(rawBreakdown).toSorted()
    invariant(categories.length > 0, `${label}: matriculas.${key} deve trazer ao menos uma categoria.`)
    const parsed = {}
    for (const category of categories) {
      parsed[category] = parseCountSeries(rawBreakdown[category], `${label}: matriculas.${key}.${category}`)
    }
    enrollmentSeries[key] = Object.freeze(parsed)
  }

  const enrollmentLastYear = readNullableInteger(candidate.matriculas, 'ultimoAno', `${label}: matriculas`)
  const enrollmentLastTotal = readNullableNumber(
    candidate.matriculas,
    'totalUltimoAno',
    `${label}: matriculas`,
  )
  const observedTotal = enrollmentSeries.total.findLast((point) => point.valor !== null) ?? null
  invariant(
    (observedTotal === null && enrollmentLastYear === null && enrollmentLastTotal === null)
      || (observedTotal !== null
        && observedTotal.ano === enrollmentLastYear
        && observedTotal.valor === enrollmentLastTotal),
    `${label}: matriculas.ultimoAno e totalUltimoAno devem refletir o último ano com valor.`,
  )

  invariant(
    Array.isArray(candidate.metodologia) && candidate.metodologia.length > 0,
    `${label}: metodologia deve ser lista não vazia.`,
  )
  for (const note of candidate.metodologia) {
    invariant(typeof note === 'string' && note.trim() !== '', `${label}: nota de metodologia vazia.`)
  }
  invariant(
    Array.isArray(candidate.fontes) && candidate.fontes.length > 0,
    `${label}: fontes deve ser lista não vazia.`,
  )
  const sources = Object.freeze(
    candidate.fontes.map((rawSource, index) => {
      const sourceLabel = `${label}: fonte na posição ${index + 1}`
      assertExactFields(rawSource, SOURCE_FIELDS, sourceLabel)
      return Object.freeze({
        nome: readText(rawSource, 'nome', sourceLabel),
        uso: readText(rawSource, 'uso', sourceLabel),
      })
    }),
  )

  return Object.freeze({
    schemaVersion: candidate.schemaVersion,
    generatorVersion: candidate.generatorVersion,
    generatedAt,
    stateCode,
    contentVersion,
    regiao: Object.freeze({
      slug,
      nome: name,
      totalMunicipios: totalMunicipalities,
      municipios: municipalities,
    }),
    pagina: page,
    atendimento: Object.freeze({
      label: readText(candidate.atendimento, 'label', `${label}: atendimento`),
      descricao: readText(candidate.atendimento, 'descricao', `${label}: atendimento`),
      indicadores: indicators,
    }),
    matriculas: Object.freeze({
      label: readText(candidate.matriculas, 'label', `${label}: matriculas`),
      descricao: readText(candidate.matriculas, 'descricao', `${label}: matriculas`),
      ultimoAno: enrollmentLastYear,
      totalUltimoAno: enrollmentLastTotal,
      series: Object.freeze(enrollmentSeries),
    }),
    metodologia: Object.freeze([...candidate.metodologia]),
    fontes: sources,
  })
}

/** Serialização canônica idêntica à do gerador, para conferir contentVersion. */
export function serializeForContentVersion(value) {
  if (Array.isArray(value)) return `[${value.map(serializeForContentVersion).join(',')}]`
  if (value !== null && typeof value === 'object') {
    return `{${Object.keys(value)
      .toSorted()
      .map((key) => `${JSON.stringify(key)}:${serializeForContentVersion(value[key])}`)
      .join(',')}}`
  }
  return JSON.stringify(value ?? null)
}

/** Resumo sha256 do texto, ou null onde a plataforma não expõe WebCrypto. */
export async function digestText(text) {
  const subtle = globalThis.crypto?.subtle
  if (!subtle) return null
  const bytes = new TextEncoder().encode(text)
  const digest = await subtle.digest('SHA-256', bytes)
  return [...new Uint8Array(digest)].map((byte) => byte.toString(16).padStart(2, '0')).join('')
}

async function defaultFetchText(path, options) {
  const response = await fetch(path, options)
  if (!response.ok) {
    throw new Error(`Falha ao ler ${path}: HTTP ${response.status}.`)
  }
  return response.text()
}

function structuredError(error, details) {
  if (error instanceof RegionalLoadError) return error
  return new RegionalLoadError(
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
export function createRegionalLoader({ fetchText = defaultFetchText, logger = console.error } = {}) {
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
      .then(() => fetchText(REGIOES_MANIFEST_PATH, { cache: 'no-store' }))
      .catch((error) => {
        throw structuredError(error, {
          code: 'manifest_unavailable',
          path: REGIOES_MANIFEST_PATH,
          stage: 'manifest',
        })
      })
      .then((raw) => {
        try {
          return parseRegioesManifest(JSON.parse(raw))
        } catch (error) {
          throw structuredError(error, {
            code: 'invalid_manifest',
            path: REGIOES_MANIFEST_PATH,
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

  async function loadRegion(regionSlug) {
    const manifest = await loadManifest()
    const entry = manifest.regions.find((candidate) => candidate.slug === regionSlug) ?? null
    if (entry === null) {
      throw new RegionalLoadError(
        `O painel regional não está publicado para ${regionSlug}.`,
        { code: 'region_not_published', regionSlug, stage: 'manifest' },
      )
    }

    return memoized(documentCache, `${entry.contentHash}:${regionSlug}`, async () => {
      const path = REGIOES_REGION_PATH.replace('{regionSlug}', regionSlug)
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
        const document = parseRegiaoDocument(JSON.parse(raw))
        invariant(
          document.regiao.slug === regionSlug,
          `o arquivo carregado pertence a outra região: ${document.regiao.slug}.`,
        )
        invariant(
          document.regiao.nome === entry.name
            && document.regiao.totalMunicipios === entry.municipalityCount,
          `identidade regional divergente do manifesto em ${regionSlug}.`,
        )
        invariant(
          document.contentVersion === entry.contentVersion,
          `versão de conteúdo divergente do manifesto em ${regionSlug}.`,
        )
        invariant(
          document.schemaVersion === manifest.documentSchemaVersion,
          `esquema do painel diverge do manifesto em ${regionSlug}.`,
        )
        invariant(
          document.generatorVersion === manifest.generatorVersion
            && document.stateCode === manifest.stateCode,
          `origem divergente do manifesto em ${regionSlug}.`,
        )
        return { document, entry, integrity }
      } catch (error) {
        throw structuredError(error, { code: 'invalid_payload', regionSlug, path, stage: 'region' })
      }
    })
  }

  return {
    loadManifest,
    loadRegion,
    reportOnce,
  }
}
