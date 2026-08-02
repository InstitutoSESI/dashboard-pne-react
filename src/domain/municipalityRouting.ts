import type { MunicipalityRef } from '../types/data'
import { resolveMunicipalityRouteValue } from './municipalityRegistry.js'

export interface MunicipalityRouteResolution {
  municipality: MunicipalityRef | null
  shouldNormalize: boolean
}

export function resolveMunicipalityRouteRequest(
  municipalities: readonly MunicipalityRef[],
  requestedValue: string,
): MunicipalityRouteResolution {
  const value = requestedValue.trim()
  const municipality = value
    ? resolveMunicipalityRouteValue(municipalities, value)
    : null
  return {
    municipality,
    shouldNormalize: Boolean(municipality && value !== municipality.slug),
  }
}

export function getEffectiveMunicipality(
  requestedValue: string,
  requestedMunicipality: MunicipalityRef | null,
  persistedMunicipality: MunicipalityRef | null,
): MunicipalityRef | null {
  return requestedValue.trim() ? requestedMunicipality : persistedMunicipality
}
