import type { AvailabilityState, UiV2BridgeSummary } from './vocacoesPneUiV2Types'

export interface Job5KKeyFigure {
  label: string
  value: string
  period: string
}

export interface Job5KEndpoint {
  series_id: string
  availability_state: AvailabilityState
  initial_year: number | null
  initial_value: number | null
  final_year: number | null
  final_value: number | null
  absolute_change: number | null
  unit: string
  territorial_lens?: string
}

export interface Job5KStoryVariant {
  variant_id: string
  entity_id: string
  municipality_ibge_code: string | null
  title_conclusion: string
  integrated_summary: string
  selected_municipality_read: string
  key_figures: Job5KKeyFigure[]
  territorial_function: string
  availability_state: AvailabilityState
  zero_state: 'not_zero' | 'observed_zero' | 'mixed'
  primary_evidence_entity_id: string
  secondary_evidence_entity_id: string
}

export interface Job5KStoryCommon {
  story_id:
    | 'STORY_HIGH_SCHOOL_TRAJECTORY'
    | 'STORY_EJA_TERRITORY'
    | 'STORY_LOGISTICS_EPT'
    | 'STORY_YOUTH_WORK_APPRENTICESHIP'
  direction_id:
    | 'DIRECTION_EDUCATION_TERRITORY'
    | 'DIRECTION_WORK_EDUCATION_COORDINATION'
  editorial_role: string
  analytical_sources: string[]
  analytical_relation_states: Record<string, string>
  title_conclusion: string
  integrated_summary: string
  regional_read: string
  selected_municipality_read: {
    generator_contract: string
    municipality_overrides: false
    variants: Job5KStoryVariant[]
  }
  planning_implication: string
  monitoring_indicators: string[]
  institutional_coordination: string[]
  interpretation_boundary: string
  allowed_claims: string[]
  forbidden_claims: string[]
  source_refs: string[]
  periods: string[]
  territorial_lenses: string[]
  network_scope: 'total_all_dependencies'
  availability_state: AvailabilityState
  zero_state: 'mixed'
  manager_review_state: 'pending'
  public_narrative_authorized: false
  pne_goal_refs: string[]
}

export interface Job5KHighSchoolDistributionItem {
  municipality_ibge_code: string
  municipality_name: string
  initial_value: number
  final_value: number
  absolute_change: number
  change_direction: 'expanded' | 'contracted' | 'stable'
  availability_state: AvailabilityState
}

export interface Job5KHighSchoolEvidence {
  entity_id: string
  high_school: Job5KEndpoint
  classes: Job5KEndpoint
}

export interface Job5KHighSchoolSecondaryEvidence {
  entity_id: string
  trajectory_2025: Record<string, {
    value: number | null
    availability_state: AvailabilityState
    series_id: string
  }>
  mobility_2022: {
    value: number | null
    availability_state: AvailabilityState
    unit: string
    series_id: string
  }
  inse_2023: number | null
  mechanical_pressure_2030: {
    value: number | null
    availability_state: AvailabilityState
    unit: 'ratio'
    fact_id: string
    editorial_visibility: 'secondary_non_predictive_detail'
  }
}

export interface Job5KHighSchoolStory extends Job5KStoryCommon {
  story_id: 'STORY_HIGH_SCHOOL_TRAJECTORY'
  ten_municipality_distribution: Job5KHighSchoolDistributionItem[]
  primary_evidence: { by_entity: Job5KHighSchoolEvidence[] }
  secondary_evidence: { by_entity: Job5KHighSchoolSecondaryEvidence[] }
}

export interface Job5KEjaStageDistribution {
  resident_public_share_percent: number
  located_eja_share_percent: number
  difference_percentage_points: number
  availability_state: AvailabilityState
}

export interface Job5KEjaDistributionItem {
  municipality_ibge_code: string
  municipality_name: string
  fundamental: Job5KEjaStageDistribution
  high_school: Job5KEjaStageDistribution
}

export interface Job5KEjaStory extends Job5KStoryCommon {
  story_id: 'STORY_EJA_TERRITORY'
  ten_municipality_distribution: Job5KEjaDistributionItem[]
  primary_evidence: {
    regional_distance_percentage_points: {
      fundamental: number
      high_school: number
    }
    distribution_id: string
  }
  secondary_evidence: {
    by_entity: Array<{ entity_id: string; eja_history: Job5KEndpoint }>
    regional_history: Job5KEndpoint
  }
}

export interface Job5KLogisticsDistributionItem {
  municipality_ibge_code: string
  municipality_name: string
  cbo_414140_initial_value: number
  cbo_414140_final_value: number
  cbo_414140_absolute_change: number
  share_of_positive_regional_change_percent: number
  technical_enrollments_2025: number
  technical_enrollments_availability_state: AvailabilityState
  share_of_regional_ept_percent: number
  share_difference_percentage_points: number
}

export interface Job5KLogisticsEvidence {
  entity_id: string
  occupation: {
    initial_value: number
    final_value: number
    absolute_change: number
    unit: 'active_bonds'
  }
  ept: Job5KEndpoint
  occupation_change_share_percent: number | null
  ept_share_percent: number | null
  share_difference_percentage_points: number | null
}

export interface Job5KLogisticsSecondaryEvidence {
  entity_id: string
  youth_work_18_24: Job5KEndpoint
  youth_regional_change_contribution_percent: number | null
  bridge: UiV2BridgeSummary | null
}

export interface Job5KLogisticsStory extends Job5KStoryCommon {
  story_id: 'STORY_LOGISTICS_EPT'
  ten_municipality_distribution: {
    distribution_id: string
    positive_change_denominator_contract: string
    positive_change_denominator: number
    regional_ept_denominator: number
    regional_distribution_divergence_percentage_points: number
    rows: Job5KLogisticsDistributionItem[]
  }
  primary_evidence: { by_entity: Job5KLogisticsEvidence[] }
  secondary_evidence: { by_entity: Job5KLogisticsSecondaryEvidence[] }
}

export interface Job5KYouthDistributionItem {
  municipality_ibge_code: string
  municipality_name: string
  rais_15_17_initial_value: number
  rais_15_17_final_value: number
  rais_15_17_absolute_change: number
  apprenticeship_events_2025: number
  youth_admission_events_2025: number
  apprenticeship_share_percent_2025: number
  availability_state: AvailabilityState
}

export interface Job5KYouthEvidence {
  entity_id: string
  rais_15_17: Job5KEndpoint
  apprenticeship_15_17: Job5KEndpoint
  apprenticeship_share_2025: {
    numerator: number
    denominator: number
    percent: number
    availability_state: AvailabilityState
    fact_id: string
  }
}

export interface Job5KYouthSecondaryEvidence {
  entity_id: string
  rais_18_24: Job5KEndpoint
  caged_admissions_15_17: Job5KEndpoint
  caged_admissions_18_24: Job5KEndpoint
  school_trajectory: { dropout_percent_2025: number; series_id: string } | null
}

export interface Job5KYouthStory extends Job5KStoryCommon {
  story_id: 'STORY_YOUTH_WORK_APPRENTICESHIP'
  ten_municipality_distribution: Job5KYouthDistributionItem[]
  primary_evidence: { by_entity: Job5KYouthEvidence[] }
  secondary_evidence: { by_entity: Job5KYouthSecondaryEvidence[] }
}

export type Job5KStory =
  | Job5KHighSchoolStory
  | Job5KEjaStory
  | Job5KLogisticsStory
  | Job5KYouthStory

export interface Job5KRuralContextVariant {
  entity_id: string
  municipality_ibge_code: string | null
  title: string
  summary: string
  rural_enrollments: Job5KEndpoint
  rural_schools: Job5KEndpoint
  rural_high_school_enrollments: Job5KEndpoint
  pnate_2026: {
    value: number | null
    availability_state: AvailabilityState
    unit: string
    series_id: string
    planning_only: true
  }
  availability_state: AvailabilityState
  zero_state: 'not_zero' | 'observed_zero'
}

export interface Job5KSpecialContextVariant {
  entity_id: string
  municipality_ibge_code: string | null
  title: string
  summary: string
  special_enrollments: Job5KEndpoint
  schools_reporting_aee: Job5KEndpoint
  interpretation_boundary: string
  availability_state: AvailabilityState
  zero_state: 'mixed'
}

export type Job5KConditionalContext =
  | {
    context_id: 'CONTEXT_RURALITY_TRANSPORT'
    direction_id: 'DIRECTION_EDUCATION_TERRITORY'
    analytical_source: string
    analytical_relation_state: string
    editorial_story_state: 'CONDITIONAL_EXPANDED'
    source_refs: string[]
    territorial_lenses: string[]
    network_scope: 'total_all_dependencies'
    variants: Job5KRuralContextVariant[]
  }
  | {
    context_id: 'CONTEXT_SPECIAL_AEE'
    direction_id: 'DIRECTION_EDUCATION_TERRITORY'
    analytical_source: string
    analytical_relation_state: string
    editorial_story_state: 'DESCRIPTIVE_CONTEXT_ONLY'
    source_refs: string[]
    territorial_lenses: string[]
    network_scope: 'total_all_dependencies'
    variants: Job5KSpecialContextVariant[]
  }

export interface VocacoesPneJob5KBundle {
  schema_version: 'vocacoes-pne-insight-first-bundle-v1'
  contract_version: string
  meta: {
    job_id: 'v7-job5k'
    generated_at: string
    internal_only: true
    feature_flag: 'VITE_ENABLE_VOCACOES_PNE_INTERNAL'
    public_narrative_authorized: false
    publication_authorized: false
    public_data_writes_authorized: false
    gate11: 'CLOSED'
    external_judgment_required: true
    manager_validation_started: false
    network_used: false
    database_used: false
    new_acquisition_performed: false
    official_formulas_altered: false
  }
  preflight: Record<string, unknown>
  external_judgment: Record<string, unknown>
  editorial_promotion_contract: Array<Record<string, unknown>>
  region: {
    entity_id: 'REGION_VALE_DO_SINOS'
    name: string
    slug: string
    state_code: 'RS'
    municipality_count: 10
  }
  fallback_municipality_ibge_code: string
  municipalities: Array<{ ibgeCode: string; name: string }>
  directions: Array<{
    direction_id: string
    sequence: number
    title: string
    manager_question: string
    story_ids: string[]
  }>
  stories: Job5KStory[]
  conditional_contexts: Job5KConditionalContext[]
  source_registry: Array<{
    sourceRef: string
    label: string
    period: string
    territorialLenses: string[]
  }>
  evidence_layer: Record<string, unknown>
  pne_contract: Record<string, unknown>
  pme_contract: { state: 'not_materialized'; goal_refs: []; planning_themes_are_not_goals: true }
  normalization: Record<string, boolean>
  job5j_catalog_state: string
  counts: {
    direction_count: 2
    primary_story_count: 4
    story_variant_count: 44
    conditional_context_count: 2
    conditional_variant_count: 22
    municipality_count: 10
    relation_count: 8
  }
}
