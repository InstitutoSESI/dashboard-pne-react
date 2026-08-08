import { useEffect, useState } from 'react'
import { ANALYTICS_AVAILABLE } from '../config/publicationConfig'
import { ACTIVE_STATE_CONFIG } from '../config/stateConfig'
import { loadIndicadores, loadMunicipiosIndex } from '../data/staticData'
import { buildMunicipalityRegistry } from '../domain/municipalityRegistry'
import type { InitialAppData } from '../types/data'

const INITIAL_APP_DATA: InitialAppData = {
  status: 'loading',
  error: null,
  indicadores: null,
  loading: true,
  municipalities: [],
}

export function useInitialAppData(): InitialAppData {
  const [initialData, setInitialData] = useState<InitialAppData>(INITIAL_APP_DATA)

  useEffect(() => {
    let cancelled = false

    async function loadInitialData(): Promise<void> {
      try {
        const [municipiosIndexPayload, indicadoresPayload] = await Promise.all([
          loadMunicipiosIndex(),
          ANALYTICS_AVAILABLE ? loadIndicadores() : Promise.resolve(null),
        ])
        const municipalities = buildMunicipalityRegistry(
          municipiosIndexPayload,
          ACTIVE_STATE_CONFIG,
        )

        if (!cancelled) {
          setInitialData({
            status: 'success',
            error: null,
            indicadores: indicadoresPayload,
            loading: false,
            municipalities,
          })
        }
      } catch (error: unknown) {
        if (!cancelled) {
          setInitialData({
            status: 'error',
            error: error instanceof Error ? error.message : 'Erro inesperado.',
            indicadores: null,
            loading: false,
            municipalities: [],
          })
        }
      }
    }

    void loadInitialData()

    return () => {
      cancelled = true
    }
  }, [])

  return initialData
}
