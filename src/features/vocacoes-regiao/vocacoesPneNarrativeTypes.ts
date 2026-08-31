export type VocacoesPneNarrativeDirection =
  | 'educacao_para_territorio'
  | 'territorio_para_educacao'

export interface VocacoesPneAlignedSeriesVisual {
  readonly template: 'aligned_series'
  readonly title: string
  readonly alt_text: string
  readonly periods: readonly number[]
  readonly series: readonly [
    {
      readonly label: string
      readonly unit: string
      readonly values: readonly number[]
    },
    {
      readonly label: string
      readonly unit: string
      readonly values: readonly number[]
    },
  ]
}

export interface VocacoesPneCategoryBarsVisual {
  readonly template: 'category_bars'
  readonly title: string
  readonly alt_text: string
  readonly unit: string
  readonly series_labels: {
    readonly region: string
    readonly state: string
  }
  readonly categories: readonly [
    VocacoesPneCategoryBar,
    VocacoesPneCategoryBar,
    VocacoesPneCategoryBar,
  ]
}

export interface VocacoesPneCategoryBar {
  readonly label: string
  readonly region_value: number
  readonly state_value: number
}

export type VocacoesPnePrimaryVisual =
  | VocacoesPneAlignedSeriesVisual
  | VocacoesPneCategoryBarsVisual

export interface VocacoesPneMunicipalDistribution {
  readonly unit: string
  readonly period: {
    readonly start: number
    readonly end: number
  }
  readonly items: readonly {
    readonly name: string
    readonly value: number
  }[]
}

interface VocacoesPneCardBase {
  readonly id: string
  readonly title: string
  readonly pne_topics: readonly string[]
  readonly monitoring_indicators: readonly string[]
  readonly sources: readonly string[]
  readonly primary_visual: VocacoesPnePrimaryVisual
  readonly municipal_distribution: VocacoesPneMunicipalDistribution
}

export interface VocacoesPneEducationToTerritoryCard extends VocacoesPneCardBase {
  readonly direction: 'educacao_para_territorio'
  readonly education_question: string
  readonly education_facts: readonly string[]
  readonly territorial_facts: readonly string[]
  readonly integrated_reading: string
  readonly municipal_pattern: string
  readonly planning_question: string
  readonly period: string
}

export type VocacoesPneFutureLabel =
  | 'Mudança já em curso'
  | 'Tendência para os próximos anos'
  | 'Tema presente nos cenários'

export interface VocacoesPneTerritoryToEducationCard extends VocacoesPneCardBase {
  readonly direction: 'territorio_para_educacao'
  readonly territorial_transformation: string
  readonly territorial_facts: readonly string[]
  readonly education_starting_point: string
  readonly exposed_groups_or_municipalities: string
  readonly education_agenda: string
  readonly horizon: string
  readonly future_label: VocacoesPneFutureLabel
}

export type VocacoesPneNarrativeCard =
  | VocacoesPneEducationToTerritoryCard
  | VocacoesPneTerritoryToEducationCard

export interface VocacoesPneNarrativeSection {
  readonly id: string
  readonly title: string
  readonly question: string
  readonly cards: readonly VocacoesPneNarrativeCard[]
}

export interface VocacoesPneNarrativeDocument {
  readonly schemaVersion: 'vocacoes-pne-narrative-pilot-v1'
  readonly contractVersion: '1.5.0'
  readonly region: {
    readonly slug: string
    readonly name: string
    readonly stateCode: 'RS'
    readonly municipalityCount: number
  }
  readonly page: {
    readonly eyebrow: string
    readonly title: string
    readonly framing: string
    readonly referenceLabel: string
    readonly details: {
      readonly evolution: string
      readonly municipalities: string
      readonly pne: string
      readonly sources: string
    }
  }
  readonly highlights: readonly [
    VocacoesPneHighlight,
    VocacoesPneHighlight,
    VocacoesPneHighlight,
  ]
  readonly sections: readonly [
    VocacoesPneNarrativeSection,
    VocacoesPneNarrativeSection,
  ]
  readonly consultation: {
    readonly title: string
    readonly description: string
  }
  readonly generation: {
    readonly deterministic: true
    readonly clockUsed: false
    readonly modelUsed: false
    readonly networkUsed: false
    readonly databaseUsed: false
    readonly compilerVersion: string
  }
}

export interface VocacoesPneHighlight {
  readonly cardId: string
  readonly label: string
}

export interface VocacoesPneNarrativeRegistryEntry {
  readonly slug: string
  readonly name: string
  readonly stateCode: 'RS'
  readonly municipalityCount: number
  readonly narrativeSchemaVersion: 'vocacoes-pne-narrative-pilot-v1'
  readonly narrativeContractVersion: '1.5.0'
  readonly legacySourceVersion: string
  readonly legacyContentVersion: string
  readonly narrativeByteSize: number
  readonly narrativeSha256: string
  readonly status: 'published' | 'rolled_back'
}

export interface VocacoesPneNarrativeRegistry {
  readonly schemaVersion: 'vocacoes-pne-narrative-registry-v1'
  readonly entries: readonly VocacoesPneNarrativeRegistryEntry[]
}

export type VocacoesPnePublicationReadiness =
  | 'ready'
  | 'almost_ready'
  | 'blocked'

export type VocacoesPnePublicationMode = 'narrative' | 'legacy'

export type VocacoesPnePublicationReasonCode =
  | 'FIRST_OUTPUT_ARTIFACT_MISSING'
  | 'SECOND_OUTPUT_ARTIFACT_MISSING'
  | 'TRANSFER_NOT_AUDITED'
  | 'NARRATIVE_ROLLED_BACK'

export interface VocacoesPnePublicationQueueRegion {
  readonly slug: string
  readonly name: string
  readonly stateCode: 'RS'
  readonly municipalityCount: number
  readonly readiness: VocacoesPnePublicationReadiness
  readonly publicationMode: VocacoesPnePublicationMode
  readonly reasonCodes: readonly VocacoesPnePublicationReasonCode[]
  readonly legacy: {
    readonly sourceVersion: string
    readonly contentVersion: string
  }
  readonly narrative: null | {
    readonly schemaVersion: 'vocacoes-pne-narrative-pilot-v1'
    readonly contractVersion: '1.5.0'
    readonly byteSize: number
    readonly sha256: string
    readonly status: 'published' | 'rolled_back'
  }
}

export interface VocacoesPnePublicationQueue {
  readonly schemaVersion: 'vocacoes-pne-publication-queue-v1'
  readonly engineVersion: string
  readonly stateCode: 'RS'
  readonly sourceManifestSchemaVersion: 'vocacoes-regiao-manifest-v2'
  readonly sourceDocumentSchemaVersion: 'vocacoes-regiao-2.9.0'
  readonly summary: {
    readonly regionCount: number
    readonly readyCount: number
    readonly almostReadyCount: number
    readonly blockedCount: number
    readonly narrativeCount: number
    readonly legacyCount: number
    readonly batchCount: number
  }
  readonly regions: readonly VocacoesPnePublicationQueueRegion[]
  readonly batches: readonly {
    readonly batchId: string
    readonly publicationMode: 'narrative'
    readonly regionSlugs: readonly string[]
    readonly rollback: {
      readonly unit: 'region'
      readonly proposalStatus: 'rolled_back'
      readonly fallbackPublicationMode: 'legacy'
      readonly automaticMutation: false
    }
  }[]
  readonly rollbackPolicy: {
    readonly unit: 'region'
    readonly sourceStatus: 'published'
    readonly proposalStatus: 'rolled_back'
    readonly fallbackPublicationMode: 'legacy'
    readonly automaticMutation: false
  }
}
