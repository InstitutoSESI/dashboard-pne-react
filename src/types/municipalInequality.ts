export type MunicipalInequalityStatus =
  | 'available'
  | 'suppressed_small_cell'
  | 'missing'
  | 'not_applicable'
  | 'methodology_incompatible'

export interface MunicipalInequalityGroup {
  groupCode: 'urban' | 'rural'
  status: MunicipalInequalityStatus
  publicationStatus: MunicipalInequalityStatus
  year: number | null
  numerator: number | null
  denominator: number | null
  percentage: number | null
  coverage: 'municipality_public_network' | 'missing'
  suppressionReasonCode: 'small_cell' | 'complementary_suppression' | null
}

export interface MunicipalInequalityPilot {
  status: MunicipalInequalityStatus
  methodologyVersion: 'municipal-inequality-p4b-v1'
  indicatorId: 'basico_integral'
  dimension: 'urban_rural'
  year: number | null
  universeCode: 'public_basic_education_enrollments'
  formulaCode: 'integral_enrollments_over_eligible_enrollments'
  minimumCellSize: 10
  observedDifferencePercentagePoints: number | null
  groups: MunicipalInequalityGroup[]
}

export interface MunicipalInequalityDocument {
  inequalityPilot: MunicipalInequalityPilot
}
