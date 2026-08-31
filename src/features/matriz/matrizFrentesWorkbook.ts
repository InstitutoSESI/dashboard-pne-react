import type { CellObject, Row, Sheet } from 'write-excel-file/browser'
import {
  parseMatrizPlan,
  serializeMatrizPlan,
  type MatrizPlanEntry,
} from '../../domain/matrizFrontsStorage.js'
import {
  matrizFrenteKey,
  resolveMatrizFrentes,
  resolveMatrizGoalSupport,
} from './matrizFrentes.js'
import { resolveMatrizGoalInsight } from './matrizInsights.js'
import type { MatrizDocument } from './matrizTypes.js'
import {
  formatMatrizGoalSituation,
  formatMatrizReferenceDate,
  MATRIZ_PLAN_STATUS_LABEL,
  MATRIZ_SEVERITY_LABEL,
  matrizPeerBenchmarkComparison,
} from './matrizVocabulary.js'

export interface MatrizFrentesWorkbookRow {
  readonly meta: string
  readonly situacao: string
  readonly gravidade: string
  readonly comparacao: string
  readonly frente: string
  readonly pontoDeAtencao: string
  readonly comoAvancar: string
  readonly apoioFederal: string
  readonly baseLegal: string
  readonly estado: string
  readonly anotacao: string
  readonly dataDeReferencia: string
}

export interface MatrizFrentesWorkbook {
  readonly fileName: string
  readonly rows: readonly MatrizFrentesWorkbookRow[]
  readonly sheets: Sheet<Blob>[]
}

const COLUMNS: readonly {
  readonly header: string
  readonly key: keyof MatrizFrentesWorkbookRow
  readonly width: number
}[] = Object.freeze([
  { key: 'meta', header: 'Meta', width: 32 },
  { key: 'situacao', header: 'Situação', width: 26 },
  { key: 'gravidade', header: 'Atenção', width: 16 },
  { key: 'comparacao', header: 'Comparação', width: 34 },
  { key: 'frente', header: 'Frente', width: 36 },
  { key: 'pontoDeAtencao', header: 'Ponto de atenção', width: 52 },
  { key: 'comoAvancar', header: 'Como avançar', width: 52 },
  { key: 'apoioFederal', header: 'Apoios e referências oficiais', width: 52 },
  { key: 'baseLegal', header: 'Base legal', width: 34 },
  { key: 'estado', header: 'Estado', width: 18 },
  { key: 'anotacao', header: 'Anotação', width: 52 },
  { key: 'dataDeReferencia', header: 'Data de referência', width: 24 },
])

function headerCell(value: string): CellObject {
  return { value, fontWeight: 'bold', wrap: true }
}

function contentCell(value: string): CellObject {
  return { value, wrap: true }
}

export function buildMatrizFrentesWorkbook(
  matriz: MatrizDocument,
  selection: readonly (string | MatrizPlanEntry)[],
): MatrizFrentesWorkbook {
  const scope = {
    municipalityIbge7: matriz.municipality.ibge7,
    referenceDate: matriz.referenceDate,
  }
  const entries = parseMatrizPlan(serializeMatrizPlan(scope, selection.map((item) => (
    typeof item === 'string' ? { key: item, status: 'todo', note: '' } : item
  ))), scope)
  const selected = new Map(entries.map((entry) => [entry.key, entry]))
  const rows: MatrizFrentesWorkbookRow[] = []

  for (const goal of matriz.priorityGoals) {
    const insight = resolveMatrizGoalInsight(goal.goalId)
    const sharedPrograms = resolveMatrizGoalSupport(goal.goalId)?.programs ?? []
    for (const frente of resolveMatrizFrentes(goal.goalId)) {
      const entry = selected.get(matrizFrenteKey(goal.goalId, frente.id))
      if (!entry) continue
      const mechanism = insight?.mechanisms.find((candidate) => (
        candidate.id === frente.mechanismId
      ))
      rows.push(Object.freeze({
        meta: goal.title,
        situacao: formatMatrizGoalSituation(goal),
        gravidade: MATRIZ_SEVERITY_LABEL[goal.severity.level],
        comparacao: matrizPeerBenchmarkComparison(goal, matriz.municipality.uf),
        frente: frente.title,
        pontoDeAtencao: mechanism?.explanation ?? '',
        comoAvancar: frente.steps.join('\n'),
        apoioFederal: [...sharedPrograms, ...frente.programs]
          .filter((program, index, programs) => programs.findIndex((candidate) => (
            candidate.url === program.url
          )) === index)
          .map((program) => `${program.name} — ${program.description}`)
          .join('\n'),
        baseLegal: frente.legalRef,
        estado: MATRIZ_PLAN_STATUS_LABEL[entry.status],
        anotacao: entry.note,
        dataDeReferencia: formatMatrizReferenceDate(matriz.referenceDate),
      }))
    }
  }

  const data: Row[] = [
    COLUMNS.map(({ header }) => headerCell(header)),
    ...rows.map((row) => COLUMNS.map(({ key }) => contentCell(row[key]))),
  ]

  return {
    fileName: `plano-frentes-${matriz.municipality.ibge7}-${matriz.referenceDate}.xlsx`,
    rows: Object.freeze(rows),
    sheets: [{
      sheet: 'Plano de ação',
      data,
      columns: COLUMNS.map(({ width }) => ({ width })),
      stickyRowsCount: 1,
      orientation: 'landscape',
      showGridLines: false,
    }],
  }
}
