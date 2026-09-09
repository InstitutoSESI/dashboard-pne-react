import type {
  Pne2026DiagnosticLoaderResult,
  Pne2026DiagnosticSimilarMunicipalities,
  Pne2026DiagnosticStateComparison,
  Pne2026DiagnosticTrajectory,
} from '../../features/diagnostic/diagnosticTypes'

export type PmeIbgeCode = string
export type PmeDataState = 'observed' | 'null' | 'unavailable' | 'suppressed' | 'not_applicable' | 'not_published' | 'not_loaded'
export type PmeModuleStatus = 'available' | 'not_published' | 'error' | 'not_loaded'
export type PmeRelationshipMode = 'progress' | 'tracking' | 'complementary'

/** The IBGE code remains the identity; name and slug are display and route metadata. */
export interface PmeMunicipalityIdentity {
  ibgeCode: PmeIbgeCode
  name: string
  slug: string
  stateCode: 'RS'
}

export interface PmeModuleError {
  code: string
  message: string
  stage?: string | null
}

export type PmeDiagnosticModuleState =
  | { status: 'available'; value: Pne2026DiagnosticLoaderResult }
  | { status: 'error'; error: PmeModuleError }
  | { status: 'not_loaded' }

export interface PmeMatrizLoaderResult {
  schemaVersion: 'pne2026-matriz-loader-result-v3'
  municipalityId: string
  municipalityName: string
  referenceDate: string
  outputSha256: string
  matriz: PmeMatrizDocument
}

/** Only fields read by the presentation adapter; the Matriz loader validates the full schema. */
export interface PmeMatrizDocument {
  municipality: { ibge7: string; name: string; uf: 'RS' }
  referenceDate: string
  sourceDiagnostic: { builderVersion: string; catalogSha256: string; diagnosticCsvSha256: string }
  sourceWorkbook: { schemaVersion: string; sha256: string }
  curation: { version: string; sha256: string }
  priorityGoals: PmeMatrizPriorityGoal[]
  goalsWithoutOwnCause: PmeMatrizGoalWithoutOwnCause[]
  outOfReach: PmeMatrizOutOfReach[]
  otherPossibleCauses: PmeMatrizOtherPossibleCause[]
  summary: { goalsOnTrack: string[]; goalsWithoutData: string[] }
}

export interface PmeMatrizPriorityGoal {
  goalId: string
  indicatorId: string
  title: string
  valueRaw: string
  referenceRaw: string
  unit: string
  year: string
  severity: Record<string, unknown>
  causes: PmeMatrizCause[]
}
export interface PmeMatrizGoalWithoutOwnCause { goalId: string; title: string; valueRaw: string; referenceRaw: string; severity: Record<string, unknown>; causesShownIn: string[] }
export interface PmeMatrizOutOfReach { factorId: string; name: string; reason: string }
export interface PmeMatrizOtherPossibleCause { factorId: string; name: string; goalId: string; reason: string }
export interface PmeMatrizCause {
  factorId: string
  name: string
  governability: string
  proofStatus: string
  proof: Record<string, unknown>
  firstStep: { kind: 'local_check' | 'federal_instrument'; text: string; ref: string }
  workshopQuestions: string[]
  collapsed: Record<string, unknown>
}

export type PmeMatrizModuleState =
  | { status: 'available'; value: PmeMatrizLoaderResult }
  | { status: 'not_published' }
  | { status: 'error'; error: PmeModuleError }
  | { status: 'not_loaded' }

export interface PmeSourceProvenance {
  sourceId: string
  title: string
  officialUrl: string | null
  period: string | null
  diagnosticReleaseId: string | null
  matrizReferenceDate: string | null
  matrizOutputSha256: string | null
}

export interface PmeEvidencePermissions {
  canDistance: boolean
  canStatus: boolean
  canProjection: boolean
}

export interface PmeEvidence {
  relationId: string
  goalId: string
  indicatorId: string
  title: string
  description: string
  relationshipNote: string
  mode: PmeRelationshipMode
  dataState: PmeDataState
  rawValue: number | null
  displayValue: number | null
  unit: string | null
  period: number | null
  sourceIds: string[]
  reasonCode: string | null
  dataStatusLabel: string | null
  territoriality: string | null
  methodologyDescription: string | null
  indicatorReference: {
    value: number
    year: number
    direction?: 'at_least' | 'at_most'
    label?: string
    kind?: string
    validationStatus?: string
  } | null
  numeratorField: string | null
  numerator: number | null
  denominatorField: string | null
  denominator: number | null
  permissions: PmeEvidencePermissions
  classification: 'advance' | 'maintain' | 'unclassified' | null
  status: string | null
  distance: number | null
  trajectory: Pne2026DiagnosticTrajectory | null
  historicalReading: string | null
  historicalLimit: string | null
  projection: Omit<Pne2026DiagnosticTrajectory, 'historicalReading'> | null
  comparisonCompatibility: 'compatible' | 'incompatible' | 'not_available'
  stateComparison: Pne2026DiagnosticStateComparison | null
  similarMunicipalities: Pne2026DiagnosticSimilarMunicipalities | null
  statewidePosition: { reading: string } | null
  publicReading: string | null
  comparisonNote: string | null
}

export interface PmeRelationshipCounts {
  methodologicalRelationships: number
  observedRelationships: number
  nullRelationships: number
  unavailableRelationships: number
  suppressedRelationships: number
  notApplicableRelationships: number
  notPublishedRelationships: number
  notLoadedRelationships: number
  complementaryRelationships: number
}

export interface PmeGoalModel {
  goalId: string
  legalOrder: number
  title: string
  legalText: string
  legalSourceId: string
  evidence: PmeEvidence[]
  counts: PmeRelationshipCounts
}

export interface PmeEditorialPath {
  id: string
  goalId: string
  title: string
  kind: 'orientation' | 'finance_context' | 'program' | 'transfer' | 'instrument'
  origin: 'fallback' | 'matriz_first_step' | 'matriz_editorial'
  programId: string | null
  sourceId: string
  officialUrl: string | null
  competence: string
  relationReason: string
  verificationStatus: 'not_verified'
  validity: null
  knownConditions: string[] | null
  evidenceRequired: string[] | null
  verifiedAt: null
  sourceDocument: string
  sourceVersion: string | null
  limitations: string
}

export interface PmeMatrizObjectiveContext {
  goalId: string
  title: string
  sourceVersion: string
  kind: 'priority_goal' | 'shared_cause'
  priorityGoal: PmeMatrizPriorityGoal | null
  sharedCause: PmeMatrizGoalWithoutOwnCause | null
  questions: string[]
  federalFirstSteps: Array<{ factorId: string; text: string; ref: string }>
}

export interface PmeObjectiveModel {
  objectiveId: string
  title: string
  themeId: string
  themeLabel: string
  guidingQuestion: string
  goals: PmeGoalModel[]
  counts: PmeRelationshipCounts
  paths: PmeEditorialPath[]
  matrizContexts: PmeMatrizObjectiveContext[]
}

export interface PmeAgendaItem {
  relationId: string
  objectiveId: string
  goalId: string
  classification: 'advance' | 'maintain'
  title: string
  publicReading: string | null
  evidence: PmeEvidence
  matrizContext: PmeMatrizPriorityGoal | PmeMatrizGoalWithoutOwnCause | null
  questions: string[]
  paths: PmeEditorialPath[]
}

export interface PmeAgendaModel {
  items: PmeAgendaItem[]
  highlights: PmeAgendaItem[]
  criterion: string
}

export interface PmeMunicipalModel {
  schemaVersion: 'pme-municipal-model-v1'
  municipality: PmeMunicipalityIdentity
  objectives: PmeObjectiveModel[]
  agenda: PmeAgendaModel
  sources: PmeSourceProvenance[]
  modules: { diagnostic: PmeDiagnosticModuleState; matriz: PmeMatrizModuleState }
}

export interface PmeMunicipalBuildInput {
  municipality: PmeMunicipalityIdentity
  diagnostic?: PmeDiagnosticModuleState | Pne2026DiagnosticLoaderResult | null
  matriz?: PmeMatrizModuleState | PmeMatrizLoaderResult | null
  highlightLimit?: number
}

/** Enables the legal 19-objective panorama before a municipality is selected. */
export interface PmeObjectiveBuildInput {
  diagnostic?: PmeDiagnosticModuleState | Pne2026DiagnosticLoaderResult | null
  matriz?: PmeMatrizModuleState | PmeMatrizLoaderResult | null
}

export interface PmePublicObjectivesBundle {
  objectives: PmeObjectiveModel[]
  sources: PmeSourceProvenance[]
  modules: { diagnostic: PmeDiagnosticModuleState; matriz: PmeMatrizModuleState }
}
