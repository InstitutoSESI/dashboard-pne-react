import {
  PNE_2026_RELATIONSHIP_MODES,
  resolvePne2026Relation,
} from './pne2026GoalIndicatorContract.js'

export { PNE_2026_RELATIONSHIP_MODES }

export function getPne2026RelationshipPolicy(legalGoalId, indicatorId) {
  const relation = resolvePne2026Relation(legalGoalId, indicatorId)

  return {
    monitoringMode: relation?.mode ?? PNE_2026_RELATIONSHIP_MODES.PROGRESS,
    ...(relation?.publicDescriptionOverride
      ? { publicDescription: relation.publicDescriptionOverride }
      : {}),
    ...(relation?.publicLabelOverride ? { publicName: relation.publicLabelOverride } : {}),
    ...(relation
      ? {
          canDistance: relation.canDistance,
          canStatus: relation.canStatus,
          canProjection: relation.canProjection,
          includeInDiagnostic: relation.includeInDiagnostic,
          includeInReferenceSummary: relation.includeInReferenceSummary,
          relationId: relation.relationId,
        }
      : {}),
  }
}

export function getPne2026RelationshipMode({ indicatorId, item, legalGoalId, relation, result } = {}) {
  const resolvedGoalId = legalGoalId ?? relation?.legalGoalId ?? item?.metaRef
  const resolvedIndicatorId = indicatorId ?? relation?.indicatorId ?? item?.key
  const canonicalRelation = resolvePne2026Relation(resolvedGoalId, resolvedIndicatorId)
  if (canonicalRelation) return canonicalRelation.mode

  const explicitMode =
    relation?.monitoringMode ??
    relation?.monitoring_mode ??
    item?.monitoringMode ??
    item?.monitoring_mode ??
    result?.monitoringMode ??
    result?.monitoring_mode

  if (Object.values(PNE_2026_RELATIONSHIP_MODES).includes(explicitMode)) {
    return explicitMode
  }

  return PNE_2026_RELATIONSHIP_MODES.PROGRESS
}

export function isPne2026ComplementaryRelationship(context) {
  return getPne2026RelationshipMode(context) === PNE_2026_RELATIONSHIP_MODES.COMPLEMENTARY
}

export function isPne2026HiddenRelationship(context) {
  return getPne2026RelationshipMode(context) === PNE_2026_RELATIONSHIP_MODES.HIDDEN
}

export function applyPne2026MethodologySafety(legalGoalId, relation) {
  const policy = getPne2026RelationshipPolicy(legalGoalId, relation?.indicatorId)

  return {
    ...relation,
    legalGoalId,
    monitoringMode: policy.monitoringMode,
    ...(policy.publicDescription ? { publicDescription: policy.publicDescription } : {}),
    ...(policy.publicName ? { publicName: policy.publicName } : {}),
    ...(typeof policy.canDistance === 'boolean' ? { hasDistance: policy.canDistance } : {}),
    ...(typeof policy.canProjection === 'boolean'
      ? { hasProjection2036: policy.canProjection }
      : {}),
  }
}
