import { PNE_2026_GOAL_INDICATOR_CONTRACT } from './pne2026GoalIndicatorContract.js'

// Adapter de compatibilidade: a definição autoral permanece no contrato canônico.
export const PNE_2026_GOAL_TEXTS = Object.freeze(
  Object.fromEntries(
    Object.values(PNE_2026_GOAL_INDICATOR_CONTRACT.goals)
      .toSorted((left, right) => left.legalOrder - right.legalOrder)
      .map((goal) => [
        goal.goalId,
        Object.freeze({
          objective: `Objetivo ${goal.objectiveId}`,
          shortTitle: goal.publicTitle,
          originalText: goal.legalText,
          displayText: goal.legalText,
          ...(goal.dashboardText ? { dashboardText: goal.dashboardText } : {}),
        }),
      ]),
  ),
)
