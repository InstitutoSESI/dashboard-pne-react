import {
  PNE_2026_GOAL_INDICATOR_CONTRACT,
  PNE_2026_RELATIONSHIP_MODES,
  canPne2026RelationEnterCycleSummary,
} from './pne2026GoalIndicatorContract.js'

const COMPARABLE_MODES = new Set([
  PNE_2026_RELATIONSHIP_MODES.PROGRESS,
  PNE_2026_RELATIONSHIP_MODES.TRACKING,
])

export const PNE_2026_INDICATOR_GOAL_REFS = Object.freeze(
  Object.fromEntries(
    PNE_2026_GOAL_INDICATOR_CONTRACT.relations
      .filter((relation) => (
        relation.includeInCycleGoalRefs
        && COMPARABLE_MODES.has(relation.mode)
        && canPne2026RelationEnterCycleSummary(relation)
      ))
      .map((relation) => [
        relation.indicatorId,
        relation.goalId,
      ]),
  ),
)
