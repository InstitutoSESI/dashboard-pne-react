export const SPECIAL_EDUCATION_SCHEMA_VERSION = 'special-education-v1'

export const SPECIAL_EDUCATION_CUTS = [
  'total',
  'publica',
  'municipal',
  'estadual',
  'federal',
  'privada',
  'urbana',
  'rural',
] as const

export type SpecialEducationCut = typeof SPECIAL_EDUCATION_CUTS[number]
export type SpecialEducationPointState =
  | 'observed'
  | 'derived_zero'
  | 'partial'
  | 'unavailable'
  | 'not_applicable'

export interface SpecialEducationPoint {
  value: number | null
  state: SpecialEducationPointState
  sourceId: string
  reason?: string
  numerator?: number
  denominator?: number
  observedSchools?: number
  missingSchools?: number
}

export interface SpecialEducationMetrics {
  enrollments: SpecialEducationPoint
  commonClassEnrollments: SpecialEducationPoint
  exclusiveClassEnrollments: SpecialEducationPoint
  classes: SpecialEducationPoint
  commonClassClasses: SpecialEducationPoint
  exclusiveClassClasses: SpecialEducationPoint
  teacherAssignments: SpecialEducationPoint
  commonClassTeacherAssignments: SpecialEducationPoint
  exclusiveClassTeacherAssignments: SpecialEducationPoint
  schools: SpecialEducationPoint
  teacherAssignmentsInSchools: SpecialEducationPoint
  fullTimeEnrollments: SpecialEducationPoint
  fullTimeClasses: SpecialEducationPoint
  stages: Record<string, SpecialEducationPoint>
}

export interface SpecialEducationAeeMetrics {
  eligibleSchools: SpecialEducationPoint
  schoolsOfferingAee: SpecialEducationPoint
  schoolsExclusiveAee: SpecialEducationPoint
  schoolsWithResourceRoom: SpecialEducationPoint
  schoolsWithExclusiveClassEnrollment: SpecialEducationPoint
  shareOfferingAee: SpecialEducationPoint
  shareWithResourceRoom: SpecialEducationPoint
}

export interface SpecialEducationBilingualMetrics {
  enrollments: SpecialEducationPoint
  classes: SpecialEducationPoint
  teacherAssignments: SpecialEducationPoint
  interpreterAssignments: SpecialEducationPoint
  guideInterpreterAssignments: SpecialEducationPoint
  librasCurriculumClasses: SpecialEducationPoint
  librasCurriculumTeacherAssignments: SpecialEducationPoint
  bilingualSpecializationTeacherAssignments: SpecialEducationPoint
  managementSpecializationTeacherAssignments: SpecialEducationPoint
  schools: SpecialEducationPoint
  schoolsWithMaterials: SpecialEducationPoint
}

export interface SpecialEducationYearCut {
  specialEducation: SpecialEducationMetrics
  commonClassInclusionRate: SpecialEducationPoint
  aee: SpecialEducationAeeMetrics
  bilingualDeafEducation: SpecialEducationBilingualMetrics
}

export interface SpecialEducationMunicipalDocument {
  schemaVersion: typeof SPECIAL_EDUCATION_SCHEMA_VERSION
  municipality: { code: string; name: string; slug?: string | null }
  sources: Array<{ id: string; provider: string; survey: string; url?: string }>
  fieldAvailability: Record<string, unknown>
  cuts: SpecialEducationCut[]
  years: Array<{ year: number; cuts: Record<SpecialEducationCut, SpecialEducationYearCut> }>
}

export interface SpecialEducationManifest {
  schemaVersion: typeof SPECIAL_EDUCATION_SCHEMA_VERSION
  contentHash: string
  municipalityCount: number
  fileCount: number
  municipalitiesPath: string
  cuts: SpecialEducationCut[]
  years: number[]
}

export const SPECIAL_EDUCATION_INDICATOR_IDS = [
  'educacao-especial-matriculas',
  'educacao-especial-inclusao-classes-comuns',
  'aee',
  'educacao-bilingue-surdos',
] as const

export type SpecialEducationIndicatorId = typeof SPECIAL_EDUCATION_INDICATOR_IDS[number]

export function isSpecialEducationIndicatorId(value: string): value is SpecialEducationIndicatorId {
  return (SPECIAL_EDUCATION_INDICATOR_IDS as readonly string[]).includes(value)
}
