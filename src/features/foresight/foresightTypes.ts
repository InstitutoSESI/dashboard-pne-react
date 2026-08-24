/*
 * Contrato público dos Cenários da educação municipal, do lado da interface.
 *
 * Os tipos descrevem exatamente o que o JSON publicado entrega — nada além.
 * Nenhum identificador metodológico, enum de processo ou resumo criptográfico
 * de conteúdo narrativo aparece aqui, porque nada disso é renderizado.
 */

export interface ForesightMunicipality {
  readonly ibgeCode: string
  readonly name: string
  readonly uf: string
  readonly slug: string
}

export interface ForesightPageCopy {
  readonly eyebrow: string
  readonly title: string
  readonly description: string
  readonly neutralityNote: string
}

export interface ForesightHorizon {
  readonly stateYear: number
  readonly scanThroughYear: number
  readonly stateLabel: string
  readonly scanLabel: string
}

export interface ForesightTextBlock {
  readonly label: string
  readonly description: string
  readonly items: readonly string[]
}

export interface ForesightStartingPoint {
  readonly label: string
  readonly description: string
  readonly movements: readonly string[]
  readonly tensions: readonly string[]
  readonly limits: readonly string[]
}

export interface ForesightObservedWindow {
  readonly startYear: number
  readonly endYear: number
  readonly periodLabel: string
  readonly startValue: string
  readonly endValue: string
  readonly directionLabel: string
  readonly caveat: string | null
}

export interface ForesightObservedSerie {
  readonly label: string
  readonly unitLabel: string
  readonly fullPeriod: ForesightObservedWindow
  readonly recentWindow: ForesightObservedWindow | null
}

export interface ForesightObservedSeries {
  readonly label: string
  readonly description: string
  readonly items: readonly ForesightObservedSerie[]
}

export interface ForesightScenarioSection {
  readonly key: string
  readonly label: string
  readonly items: readonly string[]
}

export interface ForesightScenario {
  readonly slug: string
  readonly title: string
  readonly summary: string
  readonly sections: readonly ForesightScenarioSection[]
}

export interface ForesightSeries {
  readonly label: string
  readonly unitLabel: string
  readonly startYear: number
  readonly endYear: number
  readonly periodLabel: string
}

export interface ForesightSources {
  readonly label: string
  readonly description: string
  readonly series: readonly ForesightSeries[]
  readonly notes: readonly string[]
}

export interface ForesightProvenanceArtifact {
  readonly name: string
  readonly sha256: string
}

export interface ForesightProvenance {
  readonly methodologySource: string
  readonly methodologyStatus: string
  readonly publicationScope: string
  readonly artifacts: readonly ForesightProvenanceArtifact[]
}

export interface ForesightDocument {
  readonly schemaVersion: string
  readonly contentVersion: string
  readonly sourceVersion: string
  readonly sourceMethodologyStatus: string
  readonly generatedAt: string
  readonly publicationScope: string
  readonly municipality: ForesightMunicipality
  readonly page: ForesightPageCopy
  readonly horizon: ForesightHorizon
  readonly howToRead: ForesightTextBlock
  readonly startingPoint: ForesightStartingPoint
  readonly observedSeries: ForesightObservedSeries
  readonly sharedConditions: ForesightTextBlock
  readonly scenarios: readonly ForesightScenario[]
  readonly signals: ForesightTextBlock
  readonly sources: ForesightSources
  readonly limitations: ForesightTextBlock
  readonly provenance: ForesightProvenance
}

export interface ForesightLoaderResult {
  readonly schemaVersion: 'foresight-educacao-loader-result-v1'
  readonly municipalityId: string
  readonly municipalityName: string
  readonly contentHash: string
  readonly contentVersion: string
  readonly integrity: 'verified' | 'declared'
  readonly document: ForesightDocument
}
