export type Pne2026DiagnosticDirection = 'at_least' | 'at_most'
export type Pne2026DiagnosticClassification = 'maintain' | 'advance' | null
export type Pne2026DiagnosticSummaryPriority = 'essential' | 'standard'
export type Pne2026DiagnosticDataStatus =
  | 'available'
  | 'unavailable'
  | 'not_applicable'
  | 'suppressed'

export interface Pne2026DiagnosticStateComparison {
  state: 'above' | 'near' | 'below'
  municipalityValue: number
  stateValue: number
  year: number
  unit: 'percent' | 'index' | 'count' | 'years'
  difference: number
  favorableDifference: number
  reading: string
  valueReading: string
}

export interface Pne2026DiagnosticSimilarMunicipalities {
  year?: number | null
  median: number
  unit: 'percent' | 'index' | 'count' | 'years'
  title: 'Municípios com oferta educacional de tamanho semelhante'
  reading: string
}

export interface Pne2026DiagnosticTrajectory {
  estimatedAchievementYear?: number
  historicalReading?: string
  achievementReading?: string
  modelReading?: string
  denominatorReading?: string
  uncertaintyReading?: string
}

export interface Pne2026DiagnosticTheme {
  id: string
  order: number
  label: string
}

export interface Pne2026DiagnosticSource {
  id: string
  organization?: string
  publicTitle: string
  period?: string
  officialUrl?: string
}

export interface Pne2026PublicDiagnosticSummaryV3 {
  visibleResultCount: number
  progressResultCount: number
  trackingResultCount: number
  complementaryResultCount: number
  legalReferenceResultCount: number
  monitoringReferenceResultCount: number
  dataStatusCounts: Record<Pne2026DiagnosticDataStatus, number>
  classificationCounts: {
    advance: number
    maintain: number
    unclassified: number
  }
  presentationPriorityCounts: {
    essential: number
    standard: number
  }
}

export interface Pne2026PublicDiagnosticResultV3 {
  relationId: string
  goalId: string
  indicatorId: string
  dataStatus: Pne2026DiagnosticDataStatus
  reasonCode?: string
  year?: number
  value?: number
  numeratorField?: string
  numeratorValue?: number
  denominatorField?: string
  denominatorValue?: number
  resolvedReferenceId?: string
  distance?: number
  remainingGap?: number
  favorableDifference?: number
  status?: string
  classification?: Exclude<Pne2026DiagnosticClassification, null> | null
  publicReading?: string
  stateComparison?: Pne2026DiagnosticStateComparison
  statewidePosition?: { reading: string }
  similarMunicipalityComparison?: Pne2026DiagnosticSimilarMunicipalities
  trend?: Pick<Pne2026DiagnosticTrajectory, 'historicalReading'>
  projection?: Pick<
    Pne2026DiagnosticTrajectory,
    | 'estimatedAchievementYear'
    | 'achievementReading'
    | 'modelReading'
    | 'denominatorReading'
    | 'uncertaintyReading'
  >
}

export interface Pne2026PublicDiagnosticV3 {
  schemaVersion: 'pne2026-public-diagnostic-v4'
  contractVersion: '1.9.0'
  contractHash: 'c9f4baaee43a7f105863a07bcac69d2f56a90095b75d0c7bcde25ca533fedab5'
  presentationPolicyVersion: '1.7.0'
  presentationPolicyHash: 'c330fb98c727dbb461b809a5f178f92ac73661ee3fe4e9c73cfb9b38ea9f1d3b'
  municipality: {
    id: string
    name: string
  }
  summary: Pne2026PublicDiagnosticSummaryV3
  results: Pne2026PublicDiagnosticResultV3[]
}

export interface Pne2026DiagnosticCurrentViewModel {
  value: number
  displayValue: number
  displayText?: string
  year: number
  unit: 'percent' | 'index' | 'count' | 'years'
}

export interface Pne2026DiagnosticResultViewBase {
  relationId: string
  goalId: string
  goalTitle: string
  indicatorId: string
  themeId: string
  displayOrder: number
  summaryPriority: Pne2026DiagnosticSummaryPriority
  displayGroup: string
  publicName: string
  publicDescription: string
  current: Pne2026DiagnosticCurrentViewModel
  rawValue: number | null
  year: number | null
  unit: Pne2026DiagnosticCurrentViewModel['unit'] | null
  numerator: number | null
  denominator: number | null
  numeratorField: string | null
  denominatorField: string | null
  sourceIds: string[]
  territoriality: string | null
  methodology: {
    description: string
  } | null
  dataStatus: Pne2026DiagnosticDataStatus
  reasonCode: string | null
  dataStatusLabel: string | null
  publicReading: string
  relationshipLabel: string | null
  relationshipNote: string
}

export interface Pne2026ProgressResultViewModel
  extends Pne2026DiagnosticResultViewBase {
  mode: 'progress'
  direction: Pne2026DiagnosticDirection | null
  indicatorReference: {
    value: number
    year: number
    direction?: Pne2026DiagnosticDirection
    label?: string
    kind?: string
    validationStatus?: string
  } | null
  classification: Pne2026DiagnosticClassification
  status: string | null
  distance: number | null
  remainingGap: number | null
  favorableDifference: number | null
  stateComparison: Pne2026DiagnosticStateComparison | null
  statewidePosition: { reading: string } | null
  similarMunicipalities: Pne2026DiagnosticSimilarMunicipalities | null
  trajectory: Pne2026DiagnosticTrajectory | null
}

export type Pne2026TrackingResultViewModel = Omit<
  Pne2026ProgressResultViewModel,
  'mode' | 'classification' | 'trajectory'
> & {
  mode: 'tracking'
  classification: null
  trajectory: null
}

export interface Pne2026ComplementaryResultViewModel
  extends Pne2026DiagnosticResultViewBase {
  mode: 'complementary'
}

export type Pne2026DiagnosticResultViewModel =
  | Pne2026ProgressResultViewModel
  | Pne2026TrackingResultViewModel
  | Pne2026ComplementaryResultViewModel

export interface Pne2026DiagnosticGoalViewModel {
  goalId: string
  title: string
  order: number
  results: Pne2026DiagnosticResultViewModel[]
}

export interface Pne2026DiagnosticThemeSummaryViewModel {
  total: number
  advance: number
  maintain: number
  unclassified: number
}

export interface Pne2026DiagnosticViewModel {
  viewModelVersion: 'pne2026-diagnostic-view-model-v1'
  municipalityId: string
  municipalityName: string
  summary: {
    availableResultCount: number
    unavailableResultCount: number
    essentialAvailableCount: number
    standardPriorityAvailableCount: number
    complementaryResultCount: number
    trackingResultCount: number
    advanceCount: number
    maintainCount: number
    unclassifiedCount: number
    stateAboveOrNearCount: number
    stateBelowCount: number
  }
  presentation: {
    themes: Pne2026DiagnosticTheme[]
  }
  goals: Pne2026DiagnosticGoalViewModel[]
  themeSummaries: Record<string, Pne2026DiagnosticThemeSummaryViewModel>
  sources: Pne2026DiagnosticSource[]
}

export interface Pne2026DiagnosticLoaderResult {
  schemaVersion: 'pne2026-diagnostic-loader-result-v1'
  municipalityId: string
  municipalityName: string
  diagnosticSource: 'v3'
  diagnosticReleaseId: string
  pne2026PublicDiagnostic: Pne2026DiagnosticViewModel
}
