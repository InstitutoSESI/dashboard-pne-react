export type MatrizDistanceToTarget =
  | 'far_from_target'
  | 'below_target'
  | 'near_or_at_target'

export type MatrizPeerDeviation =
  | 'much_worse_than_peers'
  | 'worse_than_peers'
  | 'in_line_with_peers'
  | 'better_than_peers'

export type MatrizSeverityLevel = 'high' | 'medium'
export type MatrizGovernability = 'municipal' | 'shared'
export type MatrizProofStatus = 'adverse_local_signal' | 'no_adverse_local_signal'
export type MatrizProofInference =
  | 'measured_value_within_source_scope'
  | 'known_cases_or_events_only'
  | 'contextual_association_only'
export type MatrizOtherCauseReason = 'weak_signal_only' | 'no_eligible_anchor' | 'over_card_cap'
export type MatrizTrendDirection = 'improved' | 'worsened' | 'stable'
export type MatrizNetworkConcentrationClassification =
  | 'concentrated_in_few_schools'
  | 'spread_across_network'

export interface MatrizMunicipality {
  readonly ibge7: string
  readonly name: string
  readonly uf: string
}

export interface MatrizPeerGroup {
  readonly criteria: string
  readonly band: string
  readonly n: number
  readonly populationPeriod: string
  readonly releaseId: string
  readonly expansions: readonly string[]
}

export interface MatrizSignal {
  readonly caution: string
  readonly dimensions: string
  readonly direction: string
  readonly maxInference: string
  readonly measureId: string
  readonly observability: string
  readonly period: string
  readonly stance: string
  readonly unit: string
  readonly valueRaw: string
  readonly peerBenchmark?: MatrizPeerBenchmark
}

export interface MatrizProof {
  readonly measureId: string
  readonly valueRaw: string
  readonly unit: string
  readonly period: string
  readonly maxInference: MatrizProofInference
  readonly caution: string
  readonly dimensions: string
  readonly peerBenchmark?: MatrizPeerBenchmark
}

export interface MatrizPeerBenchmark {
  readonly statistic: 'median'
  readonly valueRaw: string
  readonly differenceRaw: string
  readonly unit: string
  readonly year: string
  readonly n: number
}

export interface MatrizSeverity {
  readonly level: MatrizSeverityLevel
  readonly distanceToTarget: MatrizDistanceToTarget
  readonly peerDeviation: MatrizPeerDeviation
  readonly peerN: number
  readonly peerBenchmark: MatrizPeerBenchmark | null
  readonly placementRationale: string
}

export interface MatrizCause {
  readonly factorId: string
  readonly name: string
  readonly governability: MatrizGovernability
  readonly proofStatus: MatrizProofStatus
  readonly proof: MatrizProof | null
  readonly firstStep: {
    readonly kind: 'local_check' | 'federal_instrument'
    readonly text: string
    readonly ref: string
  }
  readonly workshopQuestions: readonly string[]
  readonly collapsed: {
    readonly signals: readonly MatrizSignal[]
    readonly mechanism: string
    readonly expectedRelationship: string
    readonly howToConfirmLocally: readonly string[]
  }
}

export interface MatrizPriorityGoal {
  readonly goalId: string
  readonly indicatorId: string
  readonly title: string
  readonly valueRaw: string
  readonly referenceRaw: string
  readonly unit: string
  readonly year: string
  readonly severity: MatrizSeverity
  readonly causes: readonly MatrizCause[]
  readonly trend?: {
    readonly previousValueRaw: string
    readonly previousYear: string
    readonly direction: MatrizTrendDirection
  }
  readonly networkConcentration?: {
    readonly measureId: string
    readonly classification: MatrizNetworkConcentrationClassification
    readonly affectedSchools: number
    readonly totalSchools: number
  }
}

export interface MatrizGoalWithoutOwnCause {
  readonly goalId: string
  readonly title: string
  readonly valueRaw: string
  readonly referenceRaw: string
  readonly severity: MatrizSeverity
  readonly causesShownIn: readonly string[]
}

export interface MatrizDocument {
  readonly schemaVersion: 'matriz-3.0.0' | 'matriz-4.0.0'
  readonly municipality: MatrizMunicipality
  readonly referenceDate: string
  readonly sourceDiagnostic: {
    readonly builderVersion: string
    readonly catalogSha256: string
    readonly diagnosticCsvSha256: string
  }
  readonly sourceWorkbook: {
    readonly schemaVersion: string
    readonly sha256: string
  }
  readonly peerGroup: MatrizPeerGroup
  readonly curation: {
    readonly sha256: string
    readonly version: string
  }
  readonly priorityGoals: readonly MatrizPriorityGoal[]
  readonly goalsWithoutOwnCause: readonly MatrizGoalWithoutOwnCause[]
  readonly outOfReach: readonly {
    readonly factorId: string
    readonly name: string
    readonly reason: 'external_governability'
  }[]
  readonly otherPossibleCauses: readonly {
    readonly factorId: string
    readonly name: string
    readonly goalId: string
    readonly reason: MatrizOtherCauseReason
  }[]
  readonly summary: {
    readonly goalsOnTrack: readonly string[]
    readonly goalsWithoutData: readonly string[]
  }
}

export interface MatrizLoaderResult {
  readonly schemaVersion: 'pne2026-matriz-loader-result-v3'
  readonly municipalityId: string
  readonly municipalityName: string
  readonly referenceDate: string
  readonly outputSha256: string
  readonly matriz: MatrizDocument
}
