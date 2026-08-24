import { useEffect, useState } from 'react'
import { resolveRegionForMunicipality } from '../config/regionsConfig'
import {
  VOCACOES_PUBLICATION_PENDING,
  isVocacoesPublished,
  type VocacoesPublication,
} from '../domain/vocacoesRegiaoPublication'
import { createVocacoesRegiaoLoader } from '../features/vocacoes-regiao/vocacoesRegiaoLoader'
import type { ForesightDocument } from '../features/foresight/foresightTypes'
import type { AsyncDataState } from '../types/async'
import { useAsyncData } from '../utils/useAsyncData'

export { isVocacoesPublished }
export type { VocacoesPublication }

/*
 * Um único leitor por sessão. O manifesto é lido uma vez; enquanto ele estiver
 * vazio, nenhum pacote é pedido e nenhuma requisição sai.
 */
const vocacoesLoader = createVocacoesRegiaoLoader()

/*
 * O pacote regional tem a mesma forma do municipal, com a identidade da região
 * no lugar do município — é a transposição que a metodologia-mãe já previa. Os
 * componentes declarativos dos Cenários leem `document.*` e por isso servem aos
 * dois escopos sem alteração.
 */
export type VocacoesDocument = Omit<ForesightDocument, 'municipality'> & {
  readonly region: {
    readonly slug: string
    readonly name: string
    readonly uf: string
    readonly municipalityCount: number
  }
}

export interface VocacoesResult {
  readonly document: VocacoesDocument
}

/** Pacote da região do município selecionado, ou `null` quando não há nenhum. */
export function useVocacoesRegiao(
  municipalityId: string | null | undefined,
): AsyncDataState<VocacoesResult | null> {
  const region = resolveRegionForMunicipality(municipalityId)

  return useAsyncData(
    async () => {
      if (region === null) return null
      const slugs = await vocacoesLoader.listPublishedRegionSlugs()
      if (!slugs.includes(region.slug)) return null
      const loaded = await vocacoesLoader.loadRegion(region.slug)
      return { document: loaded.document as VocacoesDocument }
    },
    [region?.slug ?? null],
  )
}

/*
 * Visibilidade vem do manifesto, nunca de uma lista fixa na interface. Enquanto
 * o manifesto não chega, `ready` é falso e a entrada de navegação simplesmente
 * não existe. Se o manifesto falhar, o conjunto publicado fica vazio e a rota
 * fecha.
 */
export function useVocacoesPublication(): VocacoesPublication {
  const [publication, setPublication] = useState<VocacoesPublication>(VOCACOES_PUBLICATION_PENDING)

  useEffect(() => {
    let cancelled = false
    vocacoesLoader
      .listPublishedRegionSlugs()
      .then((slugs: string[]) => {
        if (cancelled) return
        setPublication({ publishedSlugs: new Set(slugs), ready: true })
      })
      .catch(() => {
        if (cancelled) return
        setPublication({ publishedSlugs: new Set<string>(), ready: true })
      })
    return () => {
      cancelled = true
    }
  }, [])

  return publication
}
