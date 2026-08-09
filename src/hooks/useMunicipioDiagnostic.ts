import { createPne2026DiagnosticLoader } from '../features/diagnostic/pne2026DiagnosticLoader'
import { ACTIVE_STATE_CONFIG } from '../config/stateConfig.js'
import type { Pne2026DiagnosticLoaderResult } from '../features/diagnostic/diagnosticTypes'
import type { AsyncDataState } from '../types/async'
import { useAsyncData } from '../utils/useAsyncData'

const diagnosticLoader = createPne2026DiagnosticLoader({
  expectedMunicipalityCount: ACTIVE_STATE_CONFIG.expectedMunicipalityCount,
})

export function useMunicipioDiagnostic(
  idMunicipio: string | null | undefined,
): AsyncDataState<Pne2026DiagnosticLoaderResult | null> {
  return useAsyncData(
    async () => {
      if (!idMunicipio) return null
      return diagnosticLoader.load(idMunicipio) as Promise<Pne2026DiagnosticLoaderResult>
    },
    [idMunicipio],
  )
}
