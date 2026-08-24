import { useEffect, useState } from 'react'
import {
  FORESIGHT_PUBLICATION_PENDING,
  isForesightPublished,
  type ForesightPublication,
} from '../domain/foresightPublication'
import { createForesightEducacaoLoader } from '../features/foresight/foresightEducacaoLoader'
import type { ForesightLoaderResult } from '../features/foresight/foresightTypes'
import type { AsyncDataState } from '../types/async'
import { useAsyncData } from '../utils/useAsyncData'

export { isForesightPublished }
export type { ForesightPublication }

/*
 * Um único loader por sessão: o manifesto é lido uma vez e o pacote municipal
 * fica em cache por resumo de conteúdo mais código IBGE. Trocar de município
 * troca a chave; nunca reaproveita o pacote anterior.
 */
const foresightLoader = createForesightEducacaoLoader()

/** Pacote municipal publicado, ou `null` quando não há município selecionado. */
export function useForesightEducacao(
  municipalityId: string | null | undefined,
): AsyncDataState<ForesightLoaderResult | null> {
  return useAsyncData(
    async () => {
      if (!municipalityId) return null
      return foresightLoader.load(municipalityId) as Promise<ForesightLoaderResult>
    },
    [municipalityId],
  )
}

/*
 * Visibilidade vem do manifesto, nunca de uma lista fixa na interface. Enquanto
 * o manifesto não chega, `ready` é falso e a entrada de navegação simplesmente
 * não existe — sem item desabilitado, sem aviso, sem espaço reservado. Se o
 * manifesto falhar, o conjunto publicado fica vazio e a rota fecha.
 */
export function useForesightPublication(): ForesightPublication {
  const [publication, setPublication] = useState<ForesightPublication>(FORESIGHT_PUBLICATION_PENDING)

  useEffect(() => {
    let cancelled = false
    foresightLoader
      .listPublishedMunicipalityIds()
      .then((ids: string[]) => {
        if (cancelled) return
        setPublication({ publishedIds: new Set(ids), ready: true })
      })
      .catch(() => {
        if (cancelled) return
        setPublication({ publishedIds: new Set<string>(), ready: true })
      })
    return () => {
      cancelled = true
    }
  }, [])

  return publication
}
