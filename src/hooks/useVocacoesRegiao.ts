import { useEffect, useState } from 'react'
import { resolveRegionForMunicipality } from '../config/regionsConfig'
import {
  VOCACOES_PUBLICATION_PENDING,
  isVocacoesPublished,
  type VocacoesPublication,
} from '../domain/vocacoesRegiaoPublication'
import { createVocacoesRegiaoLoader } from '../features/vocacoes-regiao/vocacoesRegiaoLoader'
import type { VocacoesDocument } from '../features/vocacoes-regiao/vocacoesRegiaoTypes'
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
 * A forma do pacote é a do contrato público `vocacoes-regiao-2.0.0`: três
 * blocos e nenhum cenário. Até a versão `1.0.0` este arquivo derivava o tipo do
 * pacote municipal, porque o pacote regional projetado era a transposição
 * literal dele. A Fase A não é isso — os cenários são da Fase B —, e o tipo
 * agora vem do contrato próprio.
 */
export type { VocacoesDocument }

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
    function refresh() {
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
    }
    refresh()
    /*
     * O manifesto e uma promessa; o pacote e a prova. Quando um pacote nao
     * sustenta a promessa, o leitor retrata a regiao e avisa aqui — o item de
     * menu some e a rota fecha, em vez de levar a uma pagina em branco.
     */
    const unsubscribe = vocacoesLoader.subscribe(refresh)
    return () => {
      cancelled = true
      unsubscribe()
    }
  }, [])

  return publication
}
