import {
  existsSync,
  readFileSync,
  readdirSync,
  statSync,
} from 'node:fs'
import path from 'node:path'

export const DEFAULT_PLATFORM_STATE = 'RS'
export const STATE_CONFIG_SCHEMA_VERSION = 'state-config-v1'
export const MUNICIPALITY_REGISTRY_SCHEMA_VERSION = 'municipality-registry-v1'
export const STATE_PUBLICATION_SCHEMA_VERSION = 'state-publication-v3'

const STATE_CONFIG_FIELDS = [
  'schemaVersion',
  'stateCode',
  'stateName',
  'stateNameForms',
  'municipalityIbgePrefix',
  'expectedMunicipalityCount',
  'locale',
]
const STATE_NAME_FORM_FIELDS = ['nominative', 'withDe', 'withCom']
const MUNICIPALITY_REGISTRY_FIELDS = [
  'schemaVersion',
  'stateCode',
  'municipalityCount',
  'municipalities',
]
const MUNICIPALITY_FIELDS = ['ibgeCode', 'name', 'slug']
const STATE_PUBLICATION_FIELDS = [
  'schemaVersion',
  'stateCode',
  'stateConfigPath',
  'municipalityRegistryPath',
  'publicDataDirectory',
  'analyticsStatus',
  'analyticsMessage',
  'enabledProducts',
]
const ANALYTICS_STATUSES = new Set(['complete', 'partial', 'identity-only'])
// Vocabulário espelhado em src/config/analyticsProducts.ts e
// data_pipeline/src/state_publication.py.
export const ANALYTICS_PRODUCTS = ['pne', 'educacao', 'financiamento']
const PUBLIC_INDEX_FIELDS = ['generated_at', 'total_municipios', 'municipios']
const PUBLIC_INDEX_ENTRY_FIELDS = ['nome', 'id_municipio', 'slug', 'path']

function isRecord(value) {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function assertRecord(value, label) {
  if (!isRecord(value)) {
    throw new Error(`${label}: o documento deve ser um objeto JSON.`)
  }
  return value
}

function assertExactFields(value, expectedFields, label) {
  const actual = Object.keys(value).toSorted()
  const expected = [...expectedFields].toSorted()
  if (actual.length !== expected.length || actual.some((field, index) => field !== expected[index])) {
    throw new Error(
      `${label}: campos divergentes; esperados ${expected.join(', ')}, recebidos ${actual.join(', ')}.`,
    )
  }
}

function requireNonEmptyString(value, field, label) {
  if (typeof value[field] !== 'string' || value[field].trim() === '') {
    throw new Error(`${label}: "${field}" deve ser texto não vazio.`)
  }
  return value[field]
}

function readJson(filePath, label) {
  if (!existsSync(filePath)) {
    throw new Error(`${label} ausente: ${filePath}.`)
  }
  try {
    return JSON.parse(readFileSync(filePath, 'utf8'))
  } catch (error) {
    throw new Error(`${label} inválido em ${filePath}: ${error.message}`, { cause: error })
  }
}

function isPathInside(parent, candidate) {
  const relative = path.relative(parent, candidate)
  return relative !== '' && relative !== '..' && !relative.startsWith(`..${path.sep}`) && !path.isAbsolute(relative)
}

function resolveRepositoryPath(repoRoot, configuredPath, label) {
  if (path.isAbsolute(configuredPath)) {
    throw new Error(`${label}: o caminho deve ser relativo ao repositório.`)
  }
  const resolved = path.resolve(repoRoot, configuredPath)
  if (!isPathInside(repoRoot, resolved)) {
    throw new Error(`${label}: o caminho deve permanecer dentro do repositório.`)
  }
  const firstSegment = path.relative(repoRoot, resolved).split(path.sep)[0]
  if (['.git', 'build', 'dist', 'node_modules'].includes(firstSegment)) {
    throw new Error(`${label}: o caminho não pode usar a árvore operacional "${firstSegment}".`)
  }
  return resolved
}

export function normalizePlatformState(value = DEFAULT_PLATFORM_STATE) {
  if (typeof value !== 'string') {
    throw new Error('PLATFORM_STATE deve ser texto com duas letras.')
  }
  const normalized = value.trim().toUpperCase()
  if (!/^[A-Z]{2}$/.test(normalized)) {
    throw new Error(`PLATFORM_STATE inválido ${JSON.stringify(value)}; informe duas letras.`)
  }
  return normalized
}

export function parseBuildStateConfig(payload, requestedStateCode) {
  const config = assertRecord(payload, 'Configuração estadual inválida')
  assertExactFields(config, STATE_CONFIG_FIELDS, 'Configuração estadual inválida')

  if (config.schemaVersion !== STATE_CONFIG_SCHEMA_VERSION) {
    throw new Error(`Configuração estadual inválida: schemaVersion desconhecido ${JSON.stringify(config.schemaVersion)}.`)
  }
  const stateCode = requireNonEmptyString(config, 'stateCode', 'Configuração estadual inválida')
  if (!/^[A-Z]{2}$/.test(stateCode) || stateCode !== requestedStateCode) {
    throw new Error(`Configuração estadual inválida: stateCode ${JSON.stringify(stateCode)} diverge de ${requestedStateCode}.`)
  }
  const stateName = requireNonEmptyString(config, 'stateName', 'Configuração estadual inválida')
  const stateNameForms = assertRecord(
    config.stateNameForms,
    'Configuração estadual inválida: stateNameForms',
  )
  assertExactFields(
    stateNameForms,
    STATE_NAME_FORM_FIELDS,
    'Configuração estadual inválida: stateNameForms',
  )
  const parsedStateNameForms = Object.freeze({
    nominative: requireNonEmptyString(
      stateNameForms,
      'nominative',
      'Configuração estadual inválida: stateNameForms',
    ),
    withDe: requireNonEmptyString(
      stateNameForms,
      'withDe',
      'Configuração estadual inválida: stateNameForms',
    ),
    withCom: requireNonEmptyString(
      stateNameForms,
      'withCom',
      'Configuração estadual inválida: stateNameForms',
    ),
  })
  const municipalityIbgePrefix = requireNonEmptyString(
    config,
    'municipalityIbgePrefix',
    'Configuração estadual inválida',
  )
  if (!/^\d{2}$/.test(municipalityIbgePrefix)) {
    throw new Error('Configuração estadual inválida: municipalityIbgePrefix deve conter dois dígitos.')
  }
  if (!Number.isInteger(config.expectedMunicipalityCount) || config.expectedMunicipalityCount <= 0) {
    throw new Error('Configuração estadual inválida: expectedMunicipalityCount deve ser inteiro positivo.')
  }
  const locale = requireNonEmptyString(config, 'locale', 'Configuração estadual inválida')
  try {
    const canonicalLocales = Intl.getCanonicalLocales(locale)
    if (
      canonicalLocales.length !== 1
      || Intl.DateTimeFormat.supportedLocalesOf(canonicalLocales).length !== 1
    ) {
      throw new Error('locale inválido')
    }
  } catch {
    throw new Error(`Configuração estadual inválida: locale ${JSON.stringify(locale)} não é válido.`)
  }

  return Object.freeze({
    schemaVersion: STATE_CONFIG_SCHEMA_VERSION,
    stateCode,
    stateName,
    stateNameForms: parsedStateNameForms,
    municipalityIbgePrefix,
    expectedMunicipalityCount: config.expectedMunicipalityCount,
    locale,
  })
}

function parseMunicipalityRegistry(payload, stateConfig) {
  const registry = assertRecord(payload, 'Registro municipal inválido')
  assertExactFields(registry, MUNICIPALITY_REGISTRY_FIELDS, 'Registro municipal inválido')
  if (registry.schemaVersion !== MUNICIPALITY_REGISTRY_SCHEMA_VERSION) {
    throw new Error(`Registro municipal inválido: schemaVersion deve ser ${MUNICIPALITY_REGISTRY_SCHEMA_VERSION}.`)
  }
  if (registry.stateCode !== stateConfig.stateCode) {
    throw new Error(`Registro municipal inválido: stateCode diverge de ${stateConfig.stateCode}.`)
  }
  if (
    !Number.isInteger(registry.municipalityCount)
    || registry.municipalityCount !== stateConfig.expectedMunicipalityCount
  ) {
    throw new Error(
      `Registro municipal inválido: municipalityCount deve ser ${stateConfig.expectedMunicipalityCount}.`,
    )
  }
  if (!Array.isArray(registry.municipalities) || registry.municipalities.length !== registry.municipalityCount) {
    throw new Error('Registro municipal inválido: municipalities deve cobrir exatamente municipalityCount.')
  }

  const ids = new Set()
  const slugs = new Set()
  const municipalities = registry.municipalities.map((rawMunicipality, index) => {
    const label = `Município na posição ${index + 1}`
    const municipality = assertRecord(rawMunicipality, label)
    assertExactFields(municipality, MUNICIPALITY_FIELDS, label)
    const ibgeCode = requireNonEmptyString(municipality, 'ibgeCode', label)
    if (!new RegExp(`^${stateConfig.municipalityIbgePrefix}\\d{5}$`).test(ibgeCode)) {
      throw new Error(`${label}: ibgeCode deve ser texto de sete dígitos com prefixo ${stateConfig.municipalityIbgePrefix}.`)
    }
    const name = requireNonEmptyString(municipality, 'name', label)
    const slug = requireNonEmptyString(municipality, 'slug', label)
    const normalizedSlug = slug.toLocaleLowerCase(stateConfig.locale)
    if (ids.has(ibgeCode)) throw new Error(`${label}: ibgeCode duplicado ${ibgeCode}.`)
    if (slugs.has(normalizedSlug)) throw new Error(`${label}: slug duplicado ${slug}.`)
    ids.add(ibgeCode)
    slugs.add(normalizedSlug)
    return Object.freeze({ ibgeCode, name, slug })
  })

  return Object.freeze({
    schemaVersion: MUNICIPALITY_REGISTRY_SCHEMA_VERSION,
    stateCode: stateConfig.stateCode,
    municipalityCount: registry.municipalityCount,
    municipalities: Object.freeze(municipalities),
  })
}

function parseEnabledProducts(value, analyticsStatus) {
  if (analyticsStatus !== 'partial') {
    if (value !== null) {
      throw new Error(
        `Publicação estadual inválida: publicação ${analyticsStatus} deve declarar enabledProducts null.`,
      )
    }
    return null
  }
  if (!Array.isArray(value) || value.length === 0) {
    throw new Error(
      'Publicação estadual inválida: publicação partial exige enabledProducts como lista não vazia.',
    )
  }
  const products = []
  for (const item of value) {
    if (typeof item !== 'string' || !ANALYTICS_PRODUCTS.includes(item)) {
      throw new Error(
        `Publicação estadual inválida: produto analítico desconhecido em enabledProducts: ${JSON.stringify(item)}.`,
      )
    }
    if (products.includes(item)) {
      throw new Error(
        `Publicação estadual inválida: produto analítico duplicado em enabledProducts: ${item}.`,
      )
    }
    products.push(item)
  }
  if (products.length === ANALYTICS_PRODUCTS.length) {
    throw new Error(
      'Publicação estadual inválida: publicação com todos os produtos deve declarar analyticsStatus complete.',
    )
  }
  return Object.freeze(products)
}

function parseStatePublication(payload, requestedStateCode, repoRoot) {
  const publication = assertRecord(payload, 'Publicação estadual inválida')
  assertExactFields(publication, STATE_PUBLICATION_FIELDS, 'Publicação estadual inválida')
  if (publication.schemaVersion !== STATE_PUBLICATION_SCHEMA_VERSION) {
    throw new Error(`Publicação estadual inválida: schemaVersion deve ser ${STATE_PUBLICATION_SCHEMA_VERSION}.`)
  }
  if (publication.stateCode !== requestedStateCode) {
    throw new Error(`Publicação estadual inválida: stateCode diverge de ${requestedStateCode}.`)
  }
  const configuredStateConfigPath = requireNonEmptyString(
    publication,
    'stateConfigPath',
    'Publicação estadual inválida',
  )
  const configuredMunicipalityRegistryPath = requireNonEmptyString(
    publication,
    'municipalityRegistryPath',
    'Publicação estadual inválida',
  )
  const configuredDataDirectory = requireNonEmptyString(
    publication,
    'publicDataDirectory',
    'Publicação estadual inválida',
  )
  const analyticsStatus = requireNonEmptyString(
    publication,
    'analyticsStatus',
    'Publicação estadual inválida',
  )
  if (!ANALYTICS_STATUSES.has(analyticsStatus)) {
    throw new Error(
      'Publicação estadual inválida: analyticsStatus deve ser "complete", "partial" ou "identity-only".',
    )
  }
  const analyticsMessage = publication.analyticsMessage
  if (analyticsStatus === 'complete' && analyticsMessage !== null) {
    throw new Error('Publicação estadual inválida: publicação completa deve usar analyticsMessage null.')
  }
  if (
    analyticsStatus !== 'complete'
    && (typeof analyticsMessage !== 'string' || analyticsMessage.trim() === '')
  ) {
    throw new Error(
      `Publicação estadual inválida: publicação ${analyticsStatus} exige analyticsMessage não vazio.`,
    )
  }
  const enabledProducts = parseEnabledProducts(publication.enabledProducts, analyticsStatus)

  const resolvedStateConfigPath = resolveRepositoryPath(
    repoRoot,
    configuredStateConfigPath,
    'Publicação estadual inválida',
  )
  const resolvedMunicipalityRegistryPath = resolveRepositoryPath(
    repoRoot,
    configuredMunicipalityRegistryPath,
    'Publicação estadual inválida',
  )
  const resolvedPublicDataDirectory = resolveRepositoryPath(
    repoRoot,
    configuredDataDirectory,
    'Publicação estadual inválida',
  )
  return Object.freeze({
    schemaVersion: STATE_PUBLICATION_SCHEMA_VERSION,
    stateCode: requestedStateCode,
    stateConfigPath: configuredStateConfigPath,
    municipalityRegistryPath: configuredMunicipalityRegistryPath,
    publicDataDirectory: configuredDataDirectory,
    analyticsStatus,
    analyticsMessage,
    enabledProducts,
    resolvedStateConfigPath,
    resolvedMunicipalityRegistryPath,
    resolvedPublicDataDirectory,
  })
}

function validatePublicMunicipalityProjection(publicDataDirectory, registry, stateConfig) {
  const indexPath = path.join(publicDataDirectory, 'municipios_index.json')
  const rawIndex = assertRecord(readJson(indexPath, 'Índice municipal publicado'), 'Índice municipal publicado inválido')
  assertExactFields(rawIndex, PUBLIC_INDEX_FIELDS, 'Índice municipal publicado inválido')
  if (typeof rawIndex.generated_at !== 'string' || rawIndex.generated_at.trim() === '') {
    throw new Error('Índice municipal publicado inválido: generated_at deve ser texto não vazio.')
  }
  if (rawIndex.total_municipios !== registry.municipalityCount || !Array.isArray(rawIndex.municipios)) {
    throw new Error(
      `Índice municipal publicado inválido: cobertura deve conter ${registry.municipalityCount} municípios.`,
    )
  }
  if (rawIndex.municipios.length !== registry.municipalityCount) {
    throw new Error(
      `Índice municipal publicado inválido: recebidos ${rawIndex.municipios.length}, esperados ${registry.municipalityCount}.`,
    )
  }

  rawIndex.municipios.forEach((rawEntry, index) => {
    const label = `Entrada publicada na posição ${index + 1}`
    const entry = assertRecord(rawEntry, label)
    assertExactFields(entry, PUBLIC_INDEX_ENTRY_FIELDS, label)
    const canonical = registry.municipalities[index]
    const expected = {
      nome: canonical.name,
      id_municipio: canonical.ibgeCode,
      slug: canonical.slug,
      path: `/data/municipios/${canonical.ibgeCode}/index.json`,
    }
    for (const field of PUBLIC_INDEX_ENTRY_FIELDS) {
      if (entry[field] !== expected[field]) {
        throw new Error(`${label}: ${field} diverge do registro canônico de ${stateConfig.stateCode}.`)
      }
    }
  })

  const municipalRoot = path.join(publicDataDirectory, 'municipios')
  if (!existsSync(municipalRoot) || !statSync(municipalRoot).isDirectory()) {
    throw new Error(`Diretório municipal publicado ausente: ${municipalRoot}.`)
  }
  const directoryEntries = readdirSync(municipalRoot, { withFileTypes: true }).filter((entry) => entry.isDirectory())
  const invalidDirectories = directoryEntries.filter((entry) => !/^\d{7}$/.test(entry.name))
  if (invalidDirectories.length > 0) {
    throw new Error(
      `Diretórios municipais publicados devem usar somente código IBGE: ${invalidDirectories.map(({ name }) => name).join(', ')}.`,
    )
  }
  const publishedIds = directoryEntries.map(({ name }) => name).toSorted()
  const registryIds = registry.municipalities.map(({ ibgeCode }) => ibgeCode).toSorted()
  if (publishedIds.length !== registryIds.length || publishedIds.some((id, index) => id !== registryIds[index])) {
    throw new Error(`Diretórios municipais publicados divergem do universo canônico de ${stateConfig.stateCode}.`)
  }
}

export function loadStateBuildProfile({
  repoRoot = process.cwd(),
  stateCode = process.env.PLATFORM_STATE,
  requirePublication = true,
} = {}) {
  const resolvedRepoRoot = path.resolve(repoRoot)
  const normalizedStateCode = normalizePlatformState(
    stateCode === undefined ? DEFAULT_PLATFORM_STATE : stateCode,
  )
  const stateKey = normalizedStateCode.toLocaleLowerCase('en-US')
  const publicationPath = path.join(
    resolvedRepoRoot,
    'config',
    'publications',
    `${stateKey}.json`,
  )
  const publication = parseStatePublication(
    readJson(publicationPath, `Publicação estadual de ${normalizedStateCode}`),
    normalizedStateCode,
    resolvedRepoRoot,
  )
  const stateConfig = parseBuildStateConfig(
    readJson(
      publication.resolvedStateConfigPath,
      `Configuração estadual de ${normalizedStateCode}`,
    ),
    normalizedStateCode,
  )

  const baseProfile = {
    repoRoot: resolvedRepoRoot,
    stateCode: normalizedStateCode,
    stateConfig,
    sharedPublicDirectory: path.join(resolvedRepoRoot, 'public'),
    municipalityRegistry: null,
    publication,
    publicDataDirectory: null,
  }
  if (!requirePublication) return Object.freeze(baseProfile)

  const municipalityRegistry = parseMunicipalityRegistry(
    readJson(
      publication.resolvedMunicipalityRegistryPath,
      `Registro municipal de ${normalizedStateCode}`,
    ),
    stateConfig,
  )
  if (
    !existsSync(publication.resolvedPublicDataDirectory)
    || !statSync(publication.resolvedPublicDataDirectory).isDirectory()
  ) {
    throw new Error(
      `Diretório de dados publicados ausente para ${stateConfig.stateCode}: `
      + `${publication.resolvedPublicDataDirectory}.`,
    )
  }
  validatePublicMunicipalityProjection(
    publication.resolvedPublicDataDirectory,
    municipalityRegistry,
    stateConfig,
  )

  return Object.freeze({
    ...baseProfile,
    municipalityRegistry,
    publication,
    publicDataDirectory: publication.resolvedPublicDataDirectory,
  })
}
