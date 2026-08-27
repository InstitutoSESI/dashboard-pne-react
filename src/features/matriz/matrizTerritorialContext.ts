/*
 * A ponte PNE → Vocações, do lado da matriz municipal (Rodada 4 do V2).
 *
 * A matriz lê a região à qual o município pertence e apresenta, ao lado do
 * diagnóstico municipal, um resumo das leituras entre educação e território da
 * região — os dados vêm do pacote regional **já publicado**, e nenhuma origem
 * nova é aberta (o plano manda: "a plataforma pode ler o próprio publicado").
 *
 * A disciplina de linguagem é a razão de este módulo existir separado da página:
 * a única leitura honesta é "a região do município apresenta…". A região não
 * explica o município nem o determina — o município é lido na própria matriz. As
 * frases de moldura são constantes aqui, e a guarda do bloco ponte
 * (`checkBridgeText`) as varre num teste; texto que afirme causalidade
 * município←região não é publicável.
 *
 * Este módulo não busca nada: recebe o documento regional já carregado e a
 * identidade do município, e devolve o resumo pronto. Quem busca é o contêiner
 * (`MatrizPage`), e `LoadedMatrizPage` segue puro — sem pacote regional, o bloco
 * simplesmente não existe (fail-closed por ausência).
 */

import { buildAppHash } from '../../app/appHash'
import type {
  VocacoesCorrelation,
  VocacoesDocument,
} from '../vocacoes-regiao/vocacoesRegiaoTypes'

/** Quantas leituras da região o bloco resume. Um recorte, não a página inteira. */
const MAX_READINGS = 4

export interface MatrizTerritorialReading {
  readonly title: string
  readonly factors: string
  readonly reading: string | null
  readonly correlationStrength: VocacoesCorrelation['strength'] | null
}

export interface MatrizTerritorialContext {
  readonly regionName: string
  readonly regionSlug: string
  readonly municipalityCount: number
  readonly intro: string
  readonly readingNote: string
  readonly readings: readonly MatrizTerritorialReading[]
  readonly link: { readonly label: string; readonly href: string }
}

/** Rótulo curto de plural sem depender de biblioteca. */
function municipalitiesLabel(count: number): string {
  return count === 1 ? '1 município' : `${count} municípios`
}

/*
 * A frase de introdução. "A região do município … apresenta …" — a forma
 * honesta. Nenhuma variação afirma que a região explica o resultado municipal.
 */
export function buildTerritorialIntro(regionName: string, municipalityCount: number): string {
  return (
    `A região do município — ${regionName} — apresenta as leituras abaixo entre educação e `
    + `território, somando os ${municipalitiesLabel(municipalityCount)} da região.`
  )
}

/*
 * A ressalva, palavra por palavra. A negação é explícita e fica na mesma oração
 * ("não explicam … nem determinam"), que é o que a mantém do lado honesto da
 * guarda: negar na oração não é afirmar.
 */
export const TERRITORIAL_READING_NOTE =
  'Estas leituras descrevem a região, não o município. Elas não explicam o resultado do '
  + 'município nem o determinam — o resultado municipal é lido na matriz acima, e a região '
  + 'é o contexto em que ele acontece.'

export const TERRITORIAL_LINK_LABEL = 'Ver as vocações da região completas'

export function buildMatrizTerritorialContext(
  document: VocacoesDocument,
  municipalityId: string,
): MatrizTerritorialContext {
  const readings = document.associations.items.slice(0, MAX_READINGS).map((association) => {
    const factorReading = association.associativeReading.factorReadings[0]
    const correlation = factorReading?.correlation
    const readingCandidates = factorReading
      ? [
          factorReading.correlation,
          factorReading.directionConcordance,
          factorReading.comovement,
        ]
      : []
    const selectedReading = readingCandidates.find((candidate) => !('reasonCode' in candidate))

    return {
      title: association.educationOutcome.label,
      factors: association.territorialFactors.map((factor) => factor.label).join(' · '),
      reading: selectedReading && !('reasonCode' in selectedReading)
        ? selectedReading.statement
        : null,
      correlationStrength: correlation && !('reasonCode' in correlation)
        ? correlation.strength
        : null,
    }
  })

  return {
    regionName: document.region.name,
    regionSlug: document.region.slug,
    municipalityCount: document.region.municipalityCount,
    intro: buildTerritorialIntro(document.region.name, document.region.municipalityCount),
    readingNote: TERRITORIAL_READING_NOTE,
    readings,
    link: {
      label: TERRITORIAL_LINK_LABEL,
      href: buildAppHash('vocacoes-da-regiao', { municipio: municipalityId }),
    },
  }
}
