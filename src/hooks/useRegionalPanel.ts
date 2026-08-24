import { createRegionalLoader } from '../features/regional/regionalLoader'
import {
  ACTIVE_REGIONS_CONFIG,
  REGIONAL_ANALYSIS_AVAILABLE,
  resolveRegionForMunicipality,
  type RegionConfig,
} from '../config/regionsConfig'
import type { RegionalDocument, RegionalLoaderResult } from '../features/regional/regionalTypes'
import type { AsyncDataState } from '../types/async'
import { useAsyncData } from '../utils/useAsyncData'

/*
 * Um único leitor por sessão: o manifesto regional é lido uma vez e cada
 * painel fica em cache por resumo de conteúdo mais slug. Trocar de município
 * troca a região e, com ela, a chave.
 */
const regionalLoader = createRegionalLoader()

export interface RegionalPanelResult {
  readonly region: RegionConfig
  readonly document: RegionalDocument
}

export { REGIONAL_ANALYSIS_AVAILABLE, resolveRegionForMunicipality }

/** A região do município selecionado, ou `null` quando não há mapa nem seleção. */
export function useRegionForMunicipality(
  municipalityId: string | null | undefined,
): RegionConfig | null {
  return resolveRegionForMunicipality(municipalityId)
}

/*
 * Painel da região a que o município pertence. Sem mapa, sem município ou sem
 * região publicada, o resultado é `null` — a página decide o que dizer, e nada
 * é inventado no caminho.
 */
export function useRegionalPanel(
  municipalityId: string | null | undefined,
): AsyncDataState<RegionalPanelResult | null> {
  const region = resolveRegionForMunicipality(municipalityId)

  return useAsyncData(
    async () => {
      if (ACTIVE_REGIONS_CONFIG === null || region === null) return null
      const loaded = (await regionalLoader.loadRegion(region.slug)) as RegionalLoaderResult
      return { region, document: loaded.document }
    },
    [region?.slug ?? null],
  )
}
