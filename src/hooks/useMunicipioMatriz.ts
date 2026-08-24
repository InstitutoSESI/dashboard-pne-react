import { createPne2026MatrizLoader } from '../features/matriz/pne2026MatrizLoader'
import type { MatrizLoaderResult } from '../features/matriz/matrizTypes'
import type { AsyncDataState } from '../types/async'
import { useAsyncData } from '../utils/useAsyncData'

const matrizLoader = createPne2026MatrizLoader()

export function useMunicipioMatriz(
  idMunicipio: string | null | undefined,
): AsyncDataState<MatrizLoaderResult | null> {
  return useAsyncData(
    async () => {
      if (!idMunicipio) return null
      return matrizLoader.load(idMunicipio) as Promise<MatrizLoaderResult>
    },
    [idMunicipio],
  )
}
