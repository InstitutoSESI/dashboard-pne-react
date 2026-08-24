/*
 * Mapa município→região da UF ativa, injetado no build a partir de
 * `config/regions/<uf>.json`.
 *
 * A ausência do mapa é a única chave da análise regional: uma UF sem arquivo
 * de regiões não tem menu, não tem página e não tem artefato. Nada aqui
 * inventa recorte, deriva região por prefixo de código ou recorre a outra UF.
 *
 * O recorte é institucional, mas o nome da instituição que o mantém não é
 * público: a guarda de linguagem repete no runtime o que o build já barrou.
 */

import { ACTIVE_STATE_CONFIG } from './stateConfig'

declare const __ACTIVE_REGIONS_CONFIG__: unknown

export const REGIONS_CONFIG_SCHEMA_VERSION = 'regions-config-v1' as const

const REGIONS_CONFIG_FIELDS = [
  'schemaVersion',
  'stateCode',
  'provenance',
  'regionCount',
  'municipalityCount',
  'regions',
] as const
const REGION_FIELDS = ['slug', 'name', 'municipalityCount', 'municipalityIbgeCodes'] as const
const FORBIDDEN_REGION_TOKENS = ['fiergs', 'senai', 'sesi'] as const
const SLUG_PATTERN = /^[a-z0-9]+(?:-[a-z0-9]+)*$/
const IBGE7_PATTERN = /^\d{7}$/

export interface RegionConfig {
  readonly slug: string
  readonly name: string
  readonly municipalityCount: number
  readonly municipalityIbgeCodes: readonly string[]
}

export interface RegionsConfig {
  readonly schemaVersion: typeof REGIONS_CONFIG_SCHEMA_VERSION
  readonly stateCode: string
  readonly provenance: string
  readonly regionCount: number
  readonly municipalityCount: number
  readonly regions: readonly RegionConfig[]
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function assertExactFields(
  value: Record<string, unknown>,
  expectedFields: readonly string[],
  label: string,
): void {
  const actual = Object.keys(value).sort()
  const expected = [...expectedFields].sort()
  if (actual.length !== expected.length || actual.some((field, index) => field !== expected[index])) {
    throw new Error(`${label}: campos divergentes; esperados ${expected.join(', ')}.`)
  }
}

function readPublicText(value: Record<string, unknown>, field: string, label: string): string {
  const text = value[field]
  if (typeof text !== 'string' || text.trim() === '') {
    throw new Error(`${label}: "${field}" deve ser texto não vazio.`)
  }
  const normalized = text
    .normalize('NFD')
    .replace(/\p{Diacritic}/gu, '')
    .toLocaleLowerCase('pt-BR')
  for (const token of FORBIDDEN_REGION_TOKENS) {
    if (normalized.includes(token)) {
      throw new Error(`${label}: o recorte regional não pode expor o nome institucional "${token}".`)
    }
  }
  return text
}

export function parseRegionsConfig(candidate: unknown, stateCode: string): RegionsConfig {
  const label = `Mapa regional de ${stateCode} inválido`
  if (!isRecord(candidate)) throw new Error(`${label}: o documento deve ser um objeto.`)
  assertExactFields(candidate, REGIONS_CONFIG_FIELDS, label)
  if (candidate.schemaVersion !== REGIONS_CONFIG_SCHEMA_VERSION) {
    throw new Error(`${label}: schemaVersion deve ser ${REGIONS_CONFIG_SCHEMA_VERSION}.`)
  }
  if (candidate.stateCode !== stateCode) {
    throw new Error(`${label}: stateCode diverge de ${stateCode}.`)
  }
  const provenance = readPublicText(candidate, 'provenance', label)
  if (!Number.isInteger(candidate.regionCount) || Number(candidate.regionCount) <= 0) {
    throw new Error(`${label}: regionCount deve ser inteiro positivo.`)
  }
  if (!Number.isInteger(candidate.municipalityCount) || Number(candidate.municipalityCount) <= 0) {
    throw new Error(`${label}: municipalityCount deve ser inteiro positivo.`)
  }
  if (!Array.isArray(candidate.regions) || candidate.regions.length !== candidate.regionCount) {
    throw new Error(`${label}: regions deve cobrir exatamente regionCount.`)
  }

  const slugs = new Set<string>()
  const owners = new Map<string, string>()
  const regions = candidate.regions.map((rawRegion, index): RegionConfig => {
    const regionLabel = `${label}: região na posição ${index + 1}`
    if (!isRecord(rawRegion)) throw new Error(`${regionLabel}: deve ser um objeto.`)
    assertExactFields(rawRegion, REGION_FIELDS, regionLabel)
    const slug = readPublicText(rawRegion, 'slug', regionLabel)
    if (!SLUG_PATTERN.test(slug)) {
      throw new Error(`${regionLabel}: slug deve usar somente minúsculas, dígitos e hífens.`)
    }
    if (slugs.has(slug)) throw new Error(`${regionLabel}: slug duplicado ${slug}.`)
    slugs.add(slug)
    const name = readPublicText(rawRegion, 'name', regionLabel)
    const codes = rawRegion.municipalityIbgeCodes
    if (!Array.isArray(codes) || codes.length === 0) {
      throw new Error(`${regionLabel}: municipalityIbgeCodes deve ser lista não vazia.`)
    }
    if (rawRegion.municipalityCount !== codes.length) {
      throw new Error(`${regionLabel}: municipalityCount diverge da lista de municípios.`)
    }
    const municipalityIbgeCodes = codes.map((code): string => {
      if (typeof code !== 'string' || !IBGE7_PATTERN.test(code)) {
        throw new Error(`${regionLabel}: código IBGE inválido.`)
      }
      const owner = owners.get(code)
      if (owner !== undefined) {
        throw new Error(`${label}: município ${code} aparece em ${owner} e em ${slug}.`)
      }
      owners.set(code, slug)
      return code
    })
    return Object.freeze({
      slug,
      name,
      municipalityCount: municipalityIbgeCodes.length,
      municipalityIbgeCodes: Object.freeze(municipalityIbgeCodes),
    })
  })

  if (owners.size !== candidate.municipalityCount) {
    throw new Error(`${label}: municipalityCount diverge da cobertura efetiva do mapa.`)
  }

  return Object.freeze({
    schemaVersion: REGIONS_CONFIG_SCHEMA_VERSION,
    stateCode,
    provenance,
    regionCount: regions.length,
    municipalityCount: owners.size,
    regions: Object.freeze(regions),
  })
}

function resolveActiveRegionsConfig(): RegionsConfig | null {
  const injected = typeof __ACTIVE_REGIONS_CONFIG__ === 'undefined' ? null : __ACTIVE_REGIONS_CONFIG__
  if (injected === null || injected === undefined) return null
  return parseRegionsConfig(injected, ACTIVE_STATE_CONFIG.stateCode)
}

export const ACTIVE_REGIONS_CONFIG: RegionsConfig | null = resolveActiveRegionsConfig()

/** A UF ativa publica análise regional? Falso sempre que não houver mapa. */
export const REGIONAL_ANALYSIS_AVAILABLE = ACTIVE_REGIONS_CONFIG !== null

/** A região à qual o município pertence, ou null quando não há mapa. */
export function resolveRegionForMunicipality(
  municipalityId: string | null | undefined,
): RegionConfig | null {
  if (ACTIVE_REGIONS_CONFIG === null) return null
  if (typeof municipalityId !== 'string' || !IBGE7_PATTERN.test(municipalityId)) return null
  return (
    ACTIVE_REGIONS_CONFIG.regions.find((region) =>
      region.municipalityIbgeCodes.includes(municipalityId),
    ) ?? null
  )
}
