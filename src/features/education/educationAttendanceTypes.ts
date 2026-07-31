export type EducationAttendanceIndicatorKey =
  | 'creche'
  | 'pre_escola'
  | 'basico_6_17'
  | 'basico_15_17'
  | 'infantil_0_5'
  | 'obrigatoria_4_17'
  | 'escolar_6_14'

export interface DisplayPercentage {
  displayValue: number | null
  displayWasCapped: boolean
  rawValue: number | null
}

export interface EducationAttendancePoint {
  denominator: number | null
  displayValue?: number | null
  numerator: number | null
  rawValue: number | null
  year: number
}

export interface EducationAttendanceDiagnostics {
  above100: boolean
  invalidDenominator: boolean
  numeratorAboveDenominator: boolean
  smallDenominator: boolean
  smallDenominatorThreshold: number | null
  warnings: string[]
}

export interface EducationAttendancePresentation {
  headline: string
  insightLines: string[]
  interpretationStatus: 'available' | 'available_with_warning' | 'unavailable' | 'above_population_reference'
  statusLabel: string
}

export interface EducationAttendanceScenarioPoint extends EducationAttendancePoint {
  displayValue?: number | null
}

export interface EducationAttendanceReferenceTrajectoryPoint {
  denominator?: number | null
  displayValue?: number | null
  numerator?: number | null
  rawValue?: number | null
  value?: number | null
  year: number
}

export interface EducationProjectionTrend {
  aggregateModel?: {
    alpha: number
    anchoredAtLastObservation: boolean
    beta: number
    damping: number
    stateBaseValue: number
    territory: string
    transform: 'identity' | 'log1p'
  }
  municipalStateModel?: {
    candidateId: string
    damping: number
    excludedYears: number[]
    fallback: string | null
    historyStartYear: number
    maximumAbsoluteAnnualLogTrend: number
    municipalAnnualLogTrend: number | null
    municipalObservationCount: number
    municipalWeight: number
    selectedAnnualLogTrend: number | null
    shrinkage: number
    stateAnnualLogTrend: number | null
    stateObservationCount: number
    stateWeight: number
    territory: string
    windowObservations: number
  }
  baseValue?: number
  baseYear?: number
  dampingFactor: number | null
  diverges: boolean
  historicalDiagnosticMethod?: string
  longTermAnnualChange: number
  method: string
  observationCount: number
  recentAnnualChange: number
  recentWindowObservationCount: number
  selectedAnnualChange: number
  selectedAnnualChangeBeforeDamping: number
  selectedBasis: string
}

export interface EducationProjectionDenominatorModel {
  formula: string
  historicalPopulationSourceId: string
  method: string
  methodCode: string
  municipalBaseYear: number
  populationAgeGroup: string
  projectionRevision: string
  projectionSourceId: string
  projectionSourceSha256?: string | null
  stateProjectionBaseYear: number
  territorialBasis: string
}

export interface EducationProjectionUncertainty {
  backtest?: {
    developmentMunicipalities: number
    displayCapApplied?: boolean
    heldOutMaePercentagePoints: number
    heldOutMunicipalities: number
    heldOutPeriod: number[]
    improvementBootstrap95?: number[]
    improvementPercentagePoints?: number
    improvementPercent?: number
    method: string
    metric: string
    previousModel?: string
    previousModelMaePercentagePoints?: number
    persistenceMaePercentagePoints?: number
    selectedCandidate?: string
    selectedModel: string
    selectionReason: string
    unit: string
    validatedHorizonsYears: number[]
    valuePolicy?: 'raw_without_display_cap'
  }
  interval: null
  interpretation: string
  reason: string
  status: 'not_estimated' | 'backtested_no_probability_interval'
}

export interface EducationProjectionScenario {
  denominatorModel?: EducationProjectionDenominatorModel | null
  historicalEndYear: number | null
  horizonYear: number | null
  method: string | null
  model?: string | null
  projected: EducationAttendanceScenarioPoint[]
  status: 'available' | 'unavailable'
  trend?: EducationProjectionTrend | null
  type: 'conditional_projection' | 'trend_scenario' | 'pne_reference_trajectory'
  uncertainty?: EducationProjectionUncertainty | null
}

export interface EducationAttendanceIndicator {
  ageRange: string
  ageRangeDetails: { end: number; label: string; start: number }
  contractVersion: 'education-attendance-v2'
  diagnostics: EducationAttendanceDiagnostics
  fields: { denominator: string; numerator: string }
  formulaId?: string | null
  historical: EducationAttendancePoint[]
  historicalChangePercentagePoints: number | null
  indicatorKey: EducationAttendanceIndicatorKey
  indicatorType: 'age_coverage_proxy' | 'mandatory_age_summary'
  kind: 'age_coverage'
  observed: EducationAttendancePoint | null
  populationModel: {
    baseValue: number | null
    baseYear: number
    absoluteChange: number | null
    changeAbsolute: number | null
    changePercent: number | null
    horizonYear: number
    label: string
    formula?: string | null
    historicalPopulationSourceId?: string
    method: string
    methodCode: string
    modelStatus: 'modeled_estimate'
    modeledValue: number | null
    percentageChange: number | null
    projectionSourceId?: string
    status: 'modeled'
    uncertainty?: EducationProjectionUncertainty | null
  } | null
  presentation: EducationAttendancePresentation
  reference: {
    direction: 'at_least'
    kind: 'legal' | 'monitoring'
    label: string
    milestones: Array<{
      dimension?: string
      direction: 'at_least'
      unit: 'percent'
      value: number
      year: number
    }>
    referenceId: string
    unit: 'percent'
    validationStatus: string
    value: number
    year: number | null
  } | null
  scenario: EducationProjectionScenario
  sourceIds?: string[]
  territorialBasis: { denominator: string; numerator: string }
  title: string
}

export interface EducationIntegralIndicator {
  contractVersion: 'education-attendance-v2'
  diagnostics: EducationAttendanceDiagnostics
  fields: { denominator: string; numerator: string }
  formulaId?: string
  historical: EducationAttendancePoint[]
  indicatorKey: 'basico_integral'
  indicatorType: 'integral_enrollment_share'
  kind: 'integral_coverage'
  observed: EducationAttendancePoint | null
  presentation: EducationAttendancePresentation
  reference: {
    kind?: 'legal' | 'configured'
    label?: string
    referenceId?: string | null
    targets: Array<{
      direction?: 'at_least'
      referenceId?: string
      type: string
      unit?: 'percent'
      value: number
      year: number
    }>
    trajectory?: EducationAttendanceReferenceTrajectoryPoint[]
    validationStatus: string
  }
  scenario: EducationProjectionScenario
  sourceIds?: string[]
  territorialBasis: { denominator: string; numerator: string }
  title: string
}

export type EducationProjectedIndicator = EducationAttendanceIndicator | EducationIntegralIndicator

export interface EducationAttendancePayload {
  ageCoverage: Record<EducationAttendanceIndicatorKey, EducationAttendanceIndicator>
  contractVersion: 'education-attendance-v2'
  integral: { overall: EducationIntegralIndicator | null }
  municipality: string
}
