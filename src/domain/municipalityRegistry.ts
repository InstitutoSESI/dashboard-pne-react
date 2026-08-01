import type { StateConfig } from '../config/stateConfig'
import type {
  MunicipalityId,
  MunicipalityIndexEntryPayload,
  MunicipalityRef,
  MunicipiosIndexPayload,
} from '../types/data'

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function municipalityLabel(entry: Record<string, unknown>, index: number): string {
  const name = typeof entry.nome === 'string' && entry.nome.trim() ? entry.nome : null
  const id = typeof entry.id_municipio === 'string' && entry.id_municipio ? entry.id_municipio : null
  return name ?? id ?? `posição ${index + 1}`
}

function invalidEntry(label: string, field: keyof MunicipalityIndexEntryPayload, detail: string): never {
  throw new Error(`Município "${label}": campo "${field}" ${detail}.`)
}

function normalizeSlug(value: string): string {
  return value.trim().toLocaleLowerCase('pt-BR')
}

export function normalizeMunicipalityName(value: string): string {
  return value
    .normalize('NFD')
    .replace(/\p{Diacritic}/gu, '')
    .toLocaleLowerCase('pt-BR')
    .trim()
    .replace(/\s+/g, ' ')
}

export function buildMunicipalityRegistry(
  payload: MunicipiosIndexPayload,
  stateConfig: StateConfig,
): MunicipalityRef[] {
  if (!isRecord(payload) || !Array.isArray(payload.municipios)) {
    throw new Error('Catálogo municipal inválido: "municipios" deve ser uma lista.')
  }

  const entries: unknown[] = payload.municipios
  if (entries.length !== stateConfig.expectedMunicipalityCount) {
    throw new Error(
      `Catálogo municipal inválido: esperados ${stateConfig.expectedMunicipalityCount} municípios de ${stateConfig.stateCode}, recebidos ${entries.length}.`,
    )
  }

  if (payload.total_municipios !== undefined) {
    if (!Number.isInteger(payload.total_municipios)) {
      throw new Error('Catálogo municipal inválido: "total_municipios" deve ser inteiro quando presente.')
    }
    if (payload.total_municipios !== entries.length) {
      throw new Error(
        `Catálogo municipal inválido: "total_municipios" declara ${payload.total_municipios}, mas há ${entries.length} entradas.`,
      )
    }
  }

  const seenIds = new Set<MunicipalityId>()
  const seenSlugs = new Set<string>()

  return entries.map((entry, index) => {
    if (!isRecord(entry)) {
      throw new Error(`Município na posição ${index + 1}: entrada deve ser um objeto.`)
    }

    const label = municipalityLabel(entry, index)
    if (typeof entry.nome !== 'string' || entry.nome.trim() === '') {
      invalidEntry(label, 'nome', 'deve ser texto não vazio')
    }
    if (typeof entry.id_municipio !== 'string' || !/^\d{7}$/.test(entry.id_municipio)) {
      invalidEntry(label, 'id_municipio', 'deve conter exatamente sete dígitos')
    }
    if (!entry.id_municipio.startsWith(stateConfig.municipalityIbgePrefix)) {
      invalidEntry(
        label,
        'id_municipio',
        `deve começar pelo prefixo ${stateConfig.municipalityIbgePrefix} de ${stateConfig.stateCode}`,
      )
    }
    if (seenIds.has(entry.id_municipio)) {
      invalidEntry(label, 'id_municipio', `repete o código ${entry.id_municipio}`)
    }

    if (typeof entry.slug !== 'string' || entry.slug.trim() === '') {
      invalidEntry(label, 'slug', 'deve ser texto não vazio')
    }
    const normalizedSlug = normalizeSlug(entry.slug)
    if (seenSlugs.has(normalizedSlug)) {
      invalidEntry(label, 'slug', `repete o slug ${entry.slug}`)
    }

    let path: string | undefined
    if (entry.path !== undefined) {
      if (typeof entry.path !== 'string' || entry.path.trim() === '') {
        invalidEntry(label, 'path', 'deve ser texto não vazio quando presente')
      }
      const pathMunicipalityId = entry.path.match(
        /(?:^|\/)municipios\/(\d{7})\/index\.json(?:[?#].*)?$/,
      )?.[1]
      if (pathMunicipalityId !== entry.id_municipio) {
        invalidEntry(label, 'path', `deve apontar para o código ${entry.id_municipio}`)
      }
      path = entry.path
    }

    seenIds.add(entry.id_municipio)
    seenSlugs.add(normalizedSlug)

    return Object.freeze({
      ibgeCode: entry.id_municipio,
      name: entry.nome,
      slug: entry.slug,
      stateCode: stateConfig.stateCode,
      ...(path === undefined ? {} : { path }),
    })
  })
}

export function indexMunicipalitiesById(
  municipalities: readonly MunicipalityRef[],
): Map<MunicipalityId, MunicipalityRef> {
  const index = new Map<MunicipalityId, MunicipalityRef>()
  for (const municipality of municipalities) {
    if (index.has(municipality.ibgeCode)) {
      throw new Error(`Código IBGE municipal duplicado no registro: ${municipality.ibgeCode}.`)
    }
    index.set(municipality.ibgeCode, municipality)
  }
  return index
}

export function findMunicipalityById(
  municipalitiesById: ReadonlyMap<MunicipalityId, MunicipalityRef>,
  municipalityId: MunicipalityId | null | undefined,
): MunicipalityRef | null {
  return municipalityId ? municipalitiesById.get(municipalityId) ?? null : null
}

export function findUniqueMunicipalityByName(
  municipalities: readonly MunicipalityRef[],
  name: string,
): MunicipalityRef | null {
  const normalizedName = normalizeMunicipalityName(name)
  if (!normalizedName) return null

  const matches = municipalities.filter(
    (municipality) => normalizeMunicipalityName(municipality.name) === normalizedName,
  )
  return matches.length === 1 ? matches[0] : null
}

export function resolveMunicipalityRouteValue(
  municipalities: readonly MunicipalityRef[],
  routeValue: string,
): MunicipalityRef | null {
  const value = routeValue.trim()
  if (!value) return null

  const byId = indexMunicipalitiesById(municipalities)
  const byCode = findMunicipalityById(byId, value)
  if (byCode) return byCode

  const normalizedSlug = normalizeSlug(value)
  const slugMatches = municipalities.filter(
    (municipality) => normalizeSlug(municipality.slug) === normalizedSlug,
  )
  if (slugMatches.length === 1) return slugMatches[0]
  if (slugMatches.length > 1) return null

  return findUniqueMunicipalityByName(municipalities, value)
}
