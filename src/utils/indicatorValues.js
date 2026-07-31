import { reconcilePne2026MunicipalResult } from '../data/pne2026GoalIndicatorContract.js'

const emittedPne2026ReconciliationWarnings = new Set()

/**
 * Mantém a API histórica sem alterar valores publicados.
 *
 * A decisão de cumprimento, as séries e as exibições devem usar o valor bruto.
 * Limites visuais pertencem apenas às escalas dos componentes e não podem
 * substituir os dados do indicador.
 */
export function normalizePopulationPercentResults(
  results = {},
  items = [],
  cycleId,
) {
  if (cycleId === 'pne_2026_2036') {
    const incompatibilities = items.flatMap((item) => {
      const reconciliation = reconcilePne2026MunicipalResult({
        goalId: item.metaRef ?? item.goalId,
        indicatorId: item.key ?? item.indicatorId,
        result: results?.[item.key ?? item.indicatorId],
      })
      return reconciliation.issues.map((issue) => ({
        indicatorId: item.key ?? item.indicatorId,
        issue,
      }))
    })

    if (import.meta.env?.DEV && incompatibilities.length > 0) {
      const warning = `Resultados municipais PNE 2026 divergentes do contrato canônico: ${
        incompatibilities
          .map(({ indicatorId, issue }) => `${indicatorId}: ${issue}`)
          .join('; ')
      }`

      if (!emittedPne2026ReconciliationWarnings.has(warning)) {
        emittedPne2026ReconciliationWarnings.add(warning)
        console.warn(warning)
      }
    }
  }

  return results
}
