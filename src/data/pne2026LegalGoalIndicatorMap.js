import {
  PNE_2026_GOAL_INDICATOR_CONTRACT,
  PNE_2026_RELATIONSHIP_MODES,
  getPne2026Indicator,
  getPne2026RelationContext,
  getPne2026RelationsForGoal,
} from './pne2026GoalIndicatorContract.js'

const NO_MUNICIPAL_INDICATOR_REASON =
  'Sem indicador municipal disponível atualmente na plataforma.'

const legalSource =
  PNE_2026_GOAL_INDICATOR_CONTRACT.sources.lei_15388_2026
const orderedGoals = Object.values(PNE_2026_GOAL_INDICATOR_CONTRACT.goals)
  .toSorted((left, right) => left.legalOrder - right.legalOrder)

function publicLegalReference(relation) {
  if (!relation.referenceId) return null

  const resolved = getPne2026RelationContext(
    relation.goalId,
    relation.indicatorId,
    PNE_2026_GOAL_INDICATOR_CONTRACT.cycle.endYear,
  )?.legalReference
  if (!resolved) return null

  return {
    referenceId: resolved.referenceId,
    deadline: resolved.targetYear,
    unit: resolved.unit,
    milestones: resolved.milestonesAtYear,
  }
}

function projectPublicRelation(relation) {
  const indicator = getPne2026Indicator(relation.indicatorId)
  const legalReference = publicLegalReference(relation)
  const direction =
    legalReference?.milestones?.[0]?.direction ??
    PNE_2026_GOAL_INDICATOR_CONTRACT.goals[relation.goalId].direction

  return Object.freeze({
    relationId: relation.relationId,
    indicatorId: relation.indicatorId,
    coverage: relation.legacyCoverage,
    relationNote: relation.internalNote,
    hasMunicipalResult: relation.hasMunicipalResult,
    hasDistance: relation.canDistance,
    hasProjection2036: relation.canProjection,
    legalGoalId: relation.goalId,
    monitoringMode: relation.mode,
    referenceId: relation.referenceId,
    legalReference,
    deadline: legalReference?.deadline ?? null,
    direction,
    unit: indicator.unit,
    canDistance: relation.canDistance,
    canStatus: relation.canStatus,
    canProjection: relation.canProjection,
    includeInCycleGoalRefs: relation.includeInCycleGoalRefs,
    includeInDiagnostic: relation.includeInDiagnostic,
    includeInReferenceSummary: relation.includeInReferenceSummary,
    referenceDimension: relation.referenceDimension,
    publicDescription:
      relation.publicDescriptionOverride ?? indicator.publicDescription,
    publicName:
      relation.publicLabelOverride ?? indicator.publicTitle,
  })
}

function buildPublicGoal(goal) {
  const relatedIndicators = getPne2026RelationsForGoal(goal.goalId)
    .map(projectPublicRelation)

  return Object.freeze({
    legalGoalId: goal.goalId,
    objectiveId: goal.objectiveId,
    legalText: goal.legalText,
    relatedIndicators: Object.freeze(relatedIndicators),
    noMunicipalIndicatorReason: relatedIndicators.length
      ? null
      : NO_MUNICIPAL_INDICATOR_REASON,
  })
}

// Projeção pública única: metas, relações e capacidades vêm do contrato.
export const PNE_2026_LEGAL_GOAL_INDICATOR_MAP = Object.freeze(
  orderedGoals.map(buildPublicGoal),
)

export function getPne2026PublicLegalGoalRelations(goalId) {
  const goal = PNE_2026_LEGAL_GOAL_INDICATOR_MAP
    .find((item) => item.legalGoalId === String(goalId ?? ''))

  return (goal?.relatedIndicators ?? []).filter(
    (relation) => relation.monitoringMode !== PNE_2026_RELATIONSHIP_MODES.HIDDEN,
  )
}

const allGoalsHaveOfficialLineValidation = orderedGoals.every(
  (goal) => goal.referenceStatus === 'structured_for_current_relations',
)

export const PNE_2026_LEGAL_GOAL_MAPPING_METADATA = Object.freeze({
  law: legalSource.publicTitle.split(' — ')[0],
  officialLawUrl: legalSource.officialUrl,
  totalLegalGoals: orderedGoals.length,
  validatedAgainstOfficialLaw: allGoalsHaveOfficialLineValidation,
  validationNote: allGoalsHaveOfficialLineValidation
    ? 'As metas locais foram validadas linha a linha contra a fonte oficial.'
    : `A estrutura local possui ${orderedGoals.length} metas com originalText, mas a comparacao linha a linha com a fonte oficial ainda precisa de revisao humana.`,
})
