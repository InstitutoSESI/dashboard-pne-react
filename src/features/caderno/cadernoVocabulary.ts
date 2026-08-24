/*
 * Vocabulário de apresentação do caderno — camada final para o município.
 *
 * A ficha e o artefato guardam toda a base técnica (classes de observabilidade,
 * códigos de fator, sinais de medição). Esta camada NÃO os mostra: traduz o
 * conteúdo em linguagem de plano de ação. Regras que permanecem:
 * - nenhum rótulo implica gravidade relativa entre causas; sem cor semafórica,
 *   sem ordenação, sem escore;
 * - nada é inventado: os textos de causa (nome, mecanismo, relação esperada)
 *   vêm verbatim do artefato.
 */

import type { CadernoGoal } from './cadernoTypes'

/** As três seções do artefato, na ordem canônica — usadas para varrer frentes. */
export const CADERNO_ALL_SECTION_KEYS = [
  'adverse_signal',
  'no_public_data',
  'protective_present',
] as const

export type CadernoSectionKey = (typeof CADERNO_ALL_SECTION_KEYS)[number]

/**
 * As causas apresentadas ao município: primeiro as com indício nos dados
 * públicos, depois as teóricas a investigar. A ordem interna é a do artefato.
 * A marca é apenas informativa — não ordena nem prioriza uma causa sobre outra.
 */
export const CADERNO_CAUSE_SECTIONS = ['adverse_signal', 'no_public_data'] as const

export const PROTECTIVE_SECTION_KEY = 'protective_present' as const

/*
 * Escopo de ação da causa (governabilidade), em linguagem de decisão.
 *
 * O tom apenas distingue de quem é a alavanca — não sugere que uma causa pese
 * mais que outra.
 */
export type CadernoScopeTone = 'municipal' | 'shared' | 'external'

export interface CadernoScope {
  readonly label: string
  readonly tone: CadernoScopeTone
}

const GOVERNABILITY_SCOPES: Readonly<Record<string, CadernoScope>> = Object.freeze({
  high_municipal: { label: 'Ação do município', tone: 'municipal' },
  shared: { label: 'Ação compartilhada', tone: 'shared' },
  low_municipal: { label: 'Depende de outras esferas', tone: 'external' },
})

export function governabilityScope(code: string): CadernoScope {
  return GOVERNABILITY_SCOPES[code] ?? { label: 'Escopo a definir', tone: 'shared' }
}

/*
 * O caderno NÃO formata valor de indicador: todo número exibido é o resultado
 * já publicado no PNE 2026–2036, renderizado pelos formatadores canônicos de
 * `diagnosticPresentation`. Assim o município nunca vê dois números para o
 * mesmo indicador. Os valores da ficha de pesquisa seguem no artefato, servindo
 * à classificação das causas — não à leitura pública da meta.
 */

/** Contadores concordam com o número: "1 frente", "2 frentes". */
export function plural(count: number, singular: string, many: string): string {
  return `${count.toLocaleString('pt-BR')} ${count === 1 ? singular : many}`
}

/*
 * Títulos da meta. Um objetivo do PNE reúne uma ou mais metas legais; o índice
 * mostra a primeira com a contagem das demais, e o detalhe mostra todas.
 */
function goalTitles(goal: CadernoGoal): readonly string[] {
  const titles: string[] = []
  for (const legalGoal of goal.legalGoals) {
    if (!titles.includes(legalGoal.title)) titles.push(legalGoal.title)
  }
  return titles
}

export function goalFullTitle(goal: CadernoGoal): string {
  return goalTitles(goal).join(' · ')
}

export function goalShortTitle(goal: CadernoGoal): string {
  const titles = goalTitles(goal)
  const [first = ''] = titles
  return titles.length > 1 ? `${first} +${titles.length - 1}` : first
}

export function countGoalCauses(goal: CadernoGoal): number {
  return CADERNO_CAUSE_SECTIONS.reduce(
    (total, key) => total + goal.hypotheses[key].length,
    0,
  )
}
