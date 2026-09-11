import registry from '../../../config/municipalities/rs.json' with { type: 'json' }
import type { PmeMunicipalityIdentity } from './pmeTypes'

// The canonical registry, not the public index or Matriz coverage, defines the universe.
export const PME_MUNICIPALITIES: PmeMunicipalityIdentity[] = registry.municipalities.map((municipality) => ({
  ...municipality,
  stateCode: 'RS',
}))
const municipalitiesById = new Map(PME_MUNICIPALITIES.map((municipality) => [municipality.ibgeCode, municipality]))

export function findPmeMunicipality(id: string | null): PmeMunicipalityIdentity | null {
  return id ? municipalitiesById.get(id) ?? null : null
}
