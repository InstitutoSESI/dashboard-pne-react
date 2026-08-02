import { loadMunicipioData, primeMunicipioCache } from '../data/staticData'
import type { AsyncDataState } from '../types/async'
import type { MunicipalityId, MunicipioData } from '../types/data'
import { useAsyncData } from '../utils/useAsyncData'

export function useMunicipioData(
  selectedMunicipalityId: MunicipalityId | null,
): AsyncDataState<MunicipioData | null> {
  return useAsyncData(
    async () => {
      if (!selectedMunicipalityId) return null

      const data = await loadMunicipioData(selectedMunicipalityId)
      primeMunicipioCache(selectedMunicipalityId, data)
      return data
    },
    [selectedMunicipalityId],
  )
}
