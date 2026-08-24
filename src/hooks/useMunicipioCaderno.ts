import { createPne2026CadernoLoader } from '../features/caderno/pne2026CadernoLoader'
import type { CadernoLoaderResult } from '../features/caderno/cadernoTypes'
import type { AsyncDataState } from '../types/async'
import { useAsyncData } from '../utils/useAsyncData'

const cadernoLoader = createPne2026CadernoLoader()

export function useMunicipioCaderno(
  idMunicipio: string | null | undefined,
): AsyncDataState<CadernoLoaderResult | null> {
  return useAsyncData(
    async () => {
      if (!idMunicipio) return null
      return cadernoLoader.load(idMunicipio) as Promise<CadernoLoaderResult>
    },
    [idMunicipio],
  )
}
