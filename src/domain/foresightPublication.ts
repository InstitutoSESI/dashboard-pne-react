/*
 * Decisão pura de visibilidade dos Cenários da educação municipal.
 *
 * Separada do hook de propósito: a política de publicação é um contrato que
 * precisa ser exercitado com fixtures, sem React e sem rede. A interface nunca
 * conhece códigos IBGE — ela pergunta ao conjunto que veio do manifesto.
 */

export interface ForesightPublication {
  /** `null` enquanto o manifesto não foi lido: a navegação ainda não decide. */
  readonly publishedIds: ReadonlySet<string> | null
  readonly ready: boolean
}

export const FORESIGHT_PUBLICATION_PENDING: ForesightPublication = Object.freeze({
  publishedIds: null,
  ready: false,
})

/** Um município só é navegável quando o manifesto o declara publicado. */
export function isForesightPublished(
  publication: ForesightPublication,
  municipalityId: string | null | undefined,
): boolean {
  if (!publication.ready || !publication.publishedIds || !municipalityId) return false
  return publication.publishedIds.has(municipalityId)
}
