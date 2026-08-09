export const HIGHER_EDUCATION_SCHEMA_VERSION = 1 as const

export type HigherEducationAvailability = 'current' | 'historical_only' | 'unavailable'
export type HigherEducationValueStatus = 'observed' | 'derived_zero' | 'unavailable' | 'not_applicable'

export interface HigherEducationSource {
  year: number
  table: string
  fileName: string
  sha256: string
  universe: string
  territorialReference: string
}

export interface HigherEducationCategoryDefinition {
  id: string
  label: string
}

export interface HigherEducationManifestIndicator {
  id: string
  universe: string
  territorialReference: string
  sourceTable: string
  coverageByYear: Record<string, number>
}

export interface HigherEducationManifestBreakdown extends HigherEducationManifestIndicator {
  categories: HigherEducationCategoryDefinition[]
}

export interface HigherEducationManifest {
  schemaVersion: typeof HIGHER_EDUCATION_SCHEMA_VERSION
  dataVersion: string
  firstYear: number
  latestYear: number
  availableYears: number[]
  municipalityCount: number
  indicators: HigherEducationManifestIndicator[]
  breakdowns: HigherEducationManifestBreakdown[]
  sources: Record<string, HigherEducationSource>
}

export interface HigherEducationAnnualPoint {
  year: number
  value: number | null
  status: HigherEducationValueStatus
  sourceId?: string | null
  sourceIds?: string[]
}

export interface HigherEducationIndicatorSeries {
  id: string
  universe: string
  territorialReference: string
  series: HigherEducationAnnualPoint[]
}

export interface HigherEducationBreakdownCategory {
  id: string
  label: string
  value: number | null
  status: HigherEducationValueStatus
}

export interface HigherEducationBreakdown {
  id: string
  year: number
  universe: string
  territorialReference: string
  exhaustive: boolean
  status: HigherEducationValueStatus
  sourceId: string | null
  categories: HigherEducationBreakdownCategory[]
}

export interface HigherEducationMunicipalDocument {
  schemaVersion: typeof HIGHER_EDUCATION_SCHEMA_VERSION
  municipality: { id: string; name: string }
  availability: HigherEducationAvailability
  indicators: Record<string, HigherEducationIndicatorSeries>
  breakdowns: HigherEducationBreakdown[]
}

export interface HigherEducationIndicatorCatalogItem {
  id: string
  title: string
  description: string
  unit: string
  format: 'integer'
  universe: string
  territorialReference: string
  group: string
  order: number
  relatedBreakdowns: string[]
  readingDirection: 'contextual'
}

export interface HigherEducationBreakdownCatalogItem {
  id: string
  title: string
  description: string
  group: string
  order: number
  shareAllowed: boolean
}

export interface HigherEducationIndicatorViewModel extends HigherEducationIndicatorCatalogItem {
  series: HigherEducationAnnualPoint[]
  usefulPoints: HigherEducationAnnualPoint[]
  firstPoint: HigherEducationAnnualPoint | null
  latestPoint: HigherEducationAnnualPoint | null
  currentYear: number | null
  currentValue: number | null
  currentStatus: HigherEducationValueStatus | null
  absoluteVariation: number | null
  percentVariation: number | null
  effectiveSourceIds: string[]
  availability: HigherEducationAvailability
}

export interface HigherEducationBreakdownViewModel extends HigherEducationBreakdownCatalogItem {
  year: number | null
  status: HigherEducationValueStatus | null
  exhaustive: boolean
  sourceId: string | null
  universe: string | null
  territorialReference: string | null
  categories: Array<HigherEducationBreakdownCategory & { share: number | null }>
}

export interface HigherEducationViewModel {
  municipality: HigherEducationMunicipalDocument['municipality']
  availability: HigherEducationAvailability
  globalPeriod: string
  latestMunicipalUsableYear: number | null
  groups: Array<{ id: string; title: string; contextTitle?: string; description: string; order: number }>
  indicators: HigherEducationIndicatorViewModel[]
  breakdowns: HigherEducationBreakdownViewModel[]
  quickReads: string[]
  effectiveSources: Array<HigherEducationSource & { id: string }>
  methodNotes: string[]
  modalityComposition: {
    year: number
    presential: number
    distance: number
    denominator: number
    presentialShare: number
    distanceShare: number
  } | null
}
