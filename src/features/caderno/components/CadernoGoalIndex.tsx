import { countGoalCauses, goalShortTitle, plural } from '../cadernoVocabulary.js'
import type { CadernoGoal } from '../cadernoTypes'

/*
 * Índice dos objetivos — a espinha de navegação do caderno.
 *
 * Fica visível o tempo todo (fixo no desktop, faixa rolável no celular) para
 * que escolher uma meta nunca reorganize a página: só o painel de detalhe à
 * direita troca de conteúdo. A ordem é a do artefato.
 */

export function CadernoGoalIndex({
  goals,
  selectedGoalId,
  onSelect,
  planCounts,
}: {
  goals: readonly CadernoGoal[]
  selectedGoalId: string
  onSelect: (goalId: string) => void
  planCounts: ReadonlyMap<string, number>
}) {
  return (
    <nav aria-label="Objetivos do PNE 2026–2036" className="caderno-index">
      <p className="caderno-index__label">Objetivos</p>
      <ul className="caderno-index__list">
        {goals.map((goal) => {
          const causeCount = countGoalCauses(goal)
          const inPlan = planCounts.get(goal.goalId) ?? 0
          const isCurrent = goal.goalId === selectedGoalId
          return (
            <li key={goal.goalId}>
              <button
                aria-current={isCurrent ? 'true' : undefined}
                className="caderno-index__item"
                onClick={() => onSelect(goal.goalId)}
                type="button"
              >
                <span className="caderno-index__number">{goal.goalId}</span>
                <span className="caderno-index__text">
                  <span className="caderno-index__title">{goalShortTitle(goal)}</span>
                  <span className="caderno-index__meta">
                    {causeCount === 0 ? (
                      <span className="caderno-index__meta-context">leitura de contexto</span>
                    ) : (
                      plural(causeCount, 'possível causa', 'possíveis causas')
                    )}
                    {inPlan > 0 ? <span className="caderno-index__plan">{inPlan} no plano</span> : null}
                  </span>
                </span>
              </button>
            </li>
          )
        })}
      </ul>
    </nav>
  )
}
