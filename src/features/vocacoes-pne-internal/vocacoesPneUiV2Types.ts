import type { MunicipalityRef } from '../../types/data'
import type { VocacoesPneJob5KBundle } from './vocacoesPneJob5kTypes'

export type AvailabilityState =
  | 'observed'
  | 'observed_zero'
  | 'unavailable'
  | 'not_applicable'
  | 'suppressed'

export type TerritorialLens =
  | 'resident_population'
  | 'student_residence'
  | 'school_location'
  | 'rural_school_location'
  | 'workplace'
  | 'municipal_executor'

export type EditorialLayer =
  | 'PRIMARY_NARRATIVE_PATH'
  | 'EXPANDED_EVIDENCE_LAYER'
  | 'INTERNAL_TECHNICAL_LAYER'

export interface UiV2Direction {
  directionId: string
  sequence: number
  title: string
  summary: string
}

export interface UiV2Macroblock {
  macroblockId: string
  directionId: string
  sequence: number
  title: string
  summary: string
  primaryQuestion: string
  familyIds: string[]
  visualContractId: string
}

export interface UiV2Family {
  storyFamilyId: string
  directionId: string
  macroblockId: string
  layer: EditorialLayer
  title: string
  summary: string
  regionalQuestion: string
  municipalQuestion: string
  planningQuestion: string
  primaryVisual: string
  sourceRefs: string[]
  territorialLenses: TerritorialLens[]
  networkScope: 'total_all_dependencies'
  materializedInputs: string[]
  visiblePneGoalRefs: string[]
  hiddenPneLinkJustifications: Array<{ legalGoalRef: string; reason: string }>
  pmeGoalRefs: []
}

export interface UiV2Variant {
  variantId: string
  storyFamilyId: string
  variantScope: 'region' | 'municipality'
  entityId: string
  municipalityIbgeCode: string | null
  municipalityName: string | null
  localFactIds: string[]
  seriesIds: string[]
  distributionIds: string[]
  evidenceIds: string[]
  availabilityState: AvailabilityState
  zeroState: 'not_zero' | 'observed_zero' | 'mixed' | 'not_applicable'
  sourceRefs: string[]
}

export interface UiV2Fact {
  factId: string
  storyFamilyId: string
  entityId: string
  metricId: string
  label: string
  value: number | null
  availabilityState: AvailabilityState
  unit: string
  numerator: number | null
  denominator: number | null
  rawRatio: number | null
  displayValue: number | null
  displayUnit: string
  scaleContract: string
  period: string
  sourceRef: string
  territorialLens: TerritorialLens
  aggregationRule: string
  comparisonRole: string
  ageGroup: string
  populationScope: string
  educationalStage: string
  offerUniverse: string
  networkScope: 'total_all_dependencies'
  note: string
}

export interface UiV2SeriesPoint {
  year: number
  value: number | null
  availabilityState: AvailabilityState
  unit: string
  sourceRef: string
  territorialLens: TerritorialLens
  breakOrCautionState:
    | 'none'
    | 'continuity_caution'
    | 'series_break'
    | 'planning_forecast'
    | 'snapshot_only'
  aggregationRule: string
  numerator: number | null
  denominator: number | null
  rawRatio: number | null
  displayValue: number | null
  displayUnit: string
  scaleContract: string
}

export interface UiV2Series {
  seriesId: string
  storyFamilyId: string
  entityId: string
  metricId: string
  title: string
  unit: string
  period: string
  territorialLens: TerritorialLens
  networkScope: 'total_all_dependencies'
  ageGroup: string
  populationScope: string
  educationalStage: string
  offerUniverse: string
  temporalNature:
    | 'observed_series'
    | 'observed_endpoints'
    | 'single_year_snapshot'
    | 'planning_stages'
  points: UiV2SeriesPoint[]
}

export interface UiV2Distribution {
  distributionId: string
  storyFamilyId: string
  metricId: string
  educationalStage: string
  year: number
  unit: string
  label: string
  municipalValues: Array<{
    municipalityIbgeCode: string
    value: number | null
    availabilityState: AvailabilityState
    numerator: number | null
    denominator: number | null
    rawRatio: number | null
    displayValue: number | null
    displayUnit: 'percent'
    scaleContract: 'source_percent_0_100'
  }>
  valeMunicipalMedian: number | null
  valeMedianLabel: string
  rsMunicipalDistribution: {
    minimum: number | null
    quartile1: number | null
    median: number | null
    quartile3: number | null
    maximum: number | null
    municipalityCount: number | null
    label: string
  }
  sourceRef: string
  territorialLens: TerritorialLens
  comparisonRule: string
  breakOrCautionState: string
}

export interface UiV2OccupationEvidence {
  evidenceId: string
  entityId: string
  kind: 'occupation' | 'sector'
  dimensionCode: string
  label: string
  initialYear: number
  finalYear: number
  initialValue: number | null
  finalValue: number | null
  absoluteChange: number | null
  relativeChangePercent: number | null
  relativeChangeState: string
  observedYearCount: number | null
  volume: number
  regionalContributionContext: {
    regionalInitialValue: number | null
    regionalFinalValue: number | null
    regionalAbsoluteChange: number | null
  }
  coverageState: string
  smallVolumeSensitive: boolean
  selectionRole: string
  selectionIsPriorityOrRanking: false
  sourceRef: string
  territorialLens: 'workplace'
  unit: 'active_bonds'
  temporalNature: 'observed_endpoints'
  points: Array<{ year: number; value: number | null; availabilityState: AvailabilityState }>
  note: string
}

export interface UiV2BridgeSummary {
  entityId: string
  availabilityState: AvailabilityState
  year: number
  observedCourses: number | null
  mappedCourses: number | null
  unmappedCourses: number | null
  mappedEnrollments: number | null
  unmappedEnrollments: number | null
  correspondenceCount: number | null
  stateContractCoverage: Record<string, number> | null
  observedValeOfferCoverage: Record<string, number> | null
  additiveAcrossBridgeRows: false
  samePersonLink: false
  causalLink: false
  sourceRef: string
  territorialLens: TerritorialLens
  note: string
}

export interface UiV2Source {
  sourceRef: string
  label: string
  period: string
  territorialLenses: TerritorialLens[]
  relativePath: string
  sha256: string
  byteSize: number
  officialOrCanonical: true
  frozenInput: true
  networkUsedByJob5I: false
}

export interface UiV2VisualContract {
  visualContractId: string
  macroblockId: string
  title: string
  measure: string
  unit: string
  period: string
  sourceRefs: string[]
  territorialLenses: TerritorialLens[]
  comparisonRule: string
  tooltip: string
  zeroState: string
  absentState: string
  mobileFallback: string
  printBehavior: string
}

export interface UiV2SummaryBlueprintItem {
  summaryItemId: string
  sourceKind: 'series' | 'fact' | 'evidence'
  familyId: string
  metricId: string
  educationalStage: string
  ageGroup: string
  label: string
  presentation: 'observed_endpoints' | 'latest' | 'snapshot'
}

export interface VocacoesPneCoreBundle {
  schemaVersion: 'vocacoes-pne-ui-bundle-v2'
  contractVersion: string
  meta: {
    jobId: 'v7-job5i'
    generatedAt: string
    internalOnly: true
    featureFlag: 'VITE_ENABLE_VOCACOES_PNE_INTERNAL'
    publicNarrativeAuthorized: false
    publicationAuthorized: false
    publicDataWritesAuthorized: false
    gate11: 'CLOSED'
    externalJudgmentRequired: true
    managerValidationStarted: false
    networkUsed: false
    databaseUsed: false
  }
  region: {
    entityId: 'REGION_VALE_DO_SINOS'
    name: string
    slug: string
    stateCode: 'RS'
    municipalityCount: 10
  }
  fallbackMunicipalityIbgeCode: string
  municipalities: MunicipalityRef[]
  directions: UiV2Direction[]
  macroblocks: UiV2Macroblock[]
  families: UiV2Family[]
  variants: UiV2Variant[]
  facts: UiV2Fact[]
  distributions: UiV2Distribution[]
  occupationEvidence: UiV2OccupationEvidence[]
  bridgeSummaries: UiV2BridgeSummary[]
  bridgeCorrespondences: unknown[]
  sourceRegistry: UiV2Source[]
  limitRegistry: Array<{ limitId: string; appliesTo: string; statement: string }>
  visualContracts: UiV2VisualContract[]
  languageContract: Record<string, unknown>
  parallelSeriesContract: Record<string, false>
  occupationSelectionContract: Record<string, unknown>
  bridgeContract: Record<string, unknown>
  pneContract: Record<string, unknown>
  pmeContract: { state: 'not_materialized'; goalRefs: []; planningThemesAreNotGoals: true }
  summaryBlueprint: UiV2SummaryBlueprintItem[]
  indices: Record<string, unknown[]>
  counts: Record<string, number>
  seriesBundle: {
    schemaVersion: 'vocacoes-pne-ui-series-bundle-v2'
    dynamicImport: string
    seriesCount: number
    seriesPointCount: number
  }
  technicalBundle: {
    schemaVersion: 'vocacoes-pne-ui-technical-bundle-v2'
    dynamicImport: string
    visibleByDefault: false
    printedForManager: false
  }
}

export interface VocacoesPneSeriesBundle {
  schemaVersion: 'vocacoes-pne-ui-series-bundle-v2'
  series: UiV2Series[]
}

export interface VocacoesPneTechnicalBundle {
  schemaVersion: 'vocacoes-pne-ui-technical-bundle-v2'
  technicalEvidence: {
    visibleByDefault: false
    printedForManager: false
    c1C12: Array<Record<string, string>>
    qa: Array<Record<string, string>>
    shiftShare: Array<Record<string, unknown>>
    frozenJob5hManifestSha256: string
    rawCagedDetailExposed: false
  }
}

export interface VocacoesPneLoadedBundle {
  core: VocacoesPneCoreBundle
  series: UiV2Series[]
  insights: VocacoesPneJob5KBundle
}
