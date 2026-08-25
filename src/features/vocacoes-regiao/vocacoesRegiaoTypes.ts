/*
 * A forma do pacote público `vocacoes-regiao-2.0.0`, do lado de quem renderiza.
 *
 * Estes tipos descrevem o que o validador já garantiu. Eles não repetem a
 * validação — repetir daria a ilusão de duas camadas onde há uma: em runtime só
 * o validador existe, e o TypeScript some na compilação. O que os tipos fazem é
 * impedir que a página leia um campo que o contrato não tem.
 */

export type VocacoesEvidenceClass =
  | 'observed'
  | 'preliminary'
  | 'calculated'
  | 'estimated_indirect'

export type VocacoesPeriodGranularity = 'annual' | 'monthly'

export interface VocacoesPoint {
  readonly period: number
  readonly value: number
  readonly evidenceClass: VocacoesEvidenceClass
}

export interface VocacoesSeries {
  readonly seriesId: string
  readonly label: string
  readonly unitLabel: string
  readonly sourceLabel: string
  readonly evidenceClass: VocacoesEvidenceClass
  readonly evidenceLabel: string
  readonly universeLabel: string | null
  readonly aggregationLabel: string
  readonly ratioOf: { readonly numeratorLabel: string; readonly denominatorLabel: string } | null
  readonly periodGranularity: VocacoesPeriodGranularity
  readonly periodStart: number
  readonly periodEnd: number
  readonly periodLabel: string
  readonly preliminaryPeriods: readonly number[]
  readonly limitations: readonly string[]
  readonly points: readonly VocacoesPoint[]
}

export interface VocacoesSeriesReference {
  readonly seriesId: string
  readonly label: string
}

export interface VocacoesWindow {
  readonly start: number
  readonly end: number
}

export interface VocacoesAssociation {
  readonly associationId: string
  readonly label: string
  readonly window: VocacoesWindow
  readonly periodLabel: string
  readonly educationOutcome: VocacoesSeriesReference
  readonly territorialFactors: readonly VocacoesSeriesReference[]
  readonly observedStatement: string
  readonly allowedInterpretation: string
  readonly prohibitedClaim: string
  readonly hypotheses: readonly string[]
}

export interface VocacoesTemporalPair {
  readonly pairId: string
  readonly label: string
  readonly window: VocacoesWindow
  readonly periodLabel: string
  readonly seriesA: VocacoesSeriesReference
  readonly seriesB: VocacoesSeriesReference
  readonly observedStatement: string
  readonly prohibitedClaim: string
}

interface TextBlock<Item> {
  readonly label: string
  readonly description: string
  readonly items: readonly Item[]
}

export interface VocacoesDocument {
  readonly schemaVersion: string
  readonly contentVersion: string
  readonly generatedAt: string
  readonly generatorVersion: string
  readonly sourceVersion: string
  readonly sourceMethodologyStatus: string
  readonly publicationScope: string
  readonly region: {
    readonly slug: string
    readonly name: string
    readonly uf: string
    readonly municipalityCount: number
  }
  readonly page: {
    readonly eyebrow: string
    readonly title: string
    readonly description: string
    readonly neutralityNote: string
  }
  readonly howToRead: TextBlock<string>
  readonly territoryPortrait: {
    readonly label: string
    readonly description: string
    readonly series: readonly VocacoesSeries[]
  }
  readonly associations: TextBlock<VocacoesAssociation>
  readonly temporalPairs: TextBlock<VocacoesTemporalPair>
  readonly sources: TextBlock<{ readonly label: string; readonly periodLabel: string }>
  readonly limitations: TextBlock<string>
  readonly provenance: {
    readonly sourcePackageSha256: string
    readonly sourceContractVersion: string
    readonly sourceBuilderVersion: string
    readonly sourceGeneratedAt: string
    readonly registrySha256: string
  }
}
