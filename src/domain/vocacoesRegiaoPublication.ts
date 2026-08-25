/*
 * Decisão pura de visibilidade do Vocações da Região.
 *
 * Separada do hook de propósito: a política de publicação é um contrato que
 * precisa ser exercitado com fixtures, sem React e sem rede. A interface nunca
 * conhece nomes de região — ela pergunta ao conjunto que veio do manifesto.
 *
 * A regra não mudou com a publicação da Fase A, e não devia mudar: ela fechava
 * o slot quando o conjunto era vazio e agora abre as regiões que o manifesto
 * declara — sem nenhum caso especial na navegação, nos dois estados. Região
 * retratada pelo leitor (pacote que não sustentou a promessa do manifesto)
 * simplesmente não entra no conjunto.
 */

export interface VocacoesPublication {
  /** `null` enquanto o manifesto não foi lido: a navegação ainda não decide. */
  readonly publishedSlugs: ReadonlySet<string> | null
  readonly ready: boolean
}

export const VOCACOES_PUBLICATION_PENDING: VocacoesPublication = Object.freeze({
  publishedSlugs: null,
  ready: false,
})

/** Uma região só é navegável quando o manifesto a declara publicada. */
export function isVocacoesPublished(
  publication: VocacoesPublication,
  regionSlug: string | null | undefined,
): boolean {
  if (!publication.ready || !publication.publishedSlugs || !regionSlug) return false
  return publication.publishedSlugs.has(regionSlug)
}
