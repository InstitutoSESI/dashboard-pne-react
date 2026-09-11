import type { CellObject, Row, Sheet } from 'write-excel-file/browser'
import type { PmeReportHistoryEntry, PmeReportModel } from './pmeReports'
import { PME_DATA_LABELS, PME_UNIVERSE_LABELS } from './pmeFormatting'
import type { PmeDataState, PmeRelationshipMode } from './pmeTypes'

/** Explicit String cells remain text even when their content starts with =, +, - or @. */
function textCell(value: unknown): CellObject {
  return { value: String(value ?? ''), type: String, format: '@', wrap: true, alignVertical: 'top' }
}
function numericCell(value: number | null): CellObject | null {
  return value === null ? null : { value, type: Number, format: '0.###############', alignVertical: 'top' }
}
function sheet(name: string, headings: string[], rows: Row[], widths: number[]): Sheet<Blob> {
  return { sheet: name, data: [headings.map((heading) => ({ ...textCell(heading), fontWeight: 'bold', backgroundColor: '#10382f', textColor: '#ffffff' })), ...rows], columns: widths.map((width) => ({ width })), stickyRowsCount: 1, showGridLines: false }
}
function dataStateLabel(state: string): string {
  return PME_DATA_LABELS[state as PmeDataState] || 'Situação não informada na publicação'
}
function unitLabel(unit: string | null): string {
  if (unit === 'percent') return 'Percentual (%)'
  if (unit === 'count') return 'Quantidade'
  if (unit === 'years') return 'Anos'
  return unit ? 'Unidade conforme a publicação' : 'Unidade não informada na publicação'
}
function universeLabel(universe: string | null): string {
  if (!universe) return 'Universo não detalhado na publicação'
  if (PME_UNIVERSE_LABELS[universe]) return PME_UNIVERSE_LABELS[universe]
  return /^[a-z][a-z0-9_]*$/.test(universe) ? 'Universo definido na metodologia da fonte' : universe
}
function modeLabel(mode: PmeRelationshipMode): string {
  if (mode === 'tracking') return 'Referência de acompanhamento'
  if (mode === 'complementary') return 'Evidência complementar'
  return 'Relação com a referência do PNE'
}
function classificationLabel(classification: 'advance' | 'maintain'): string {
  return classification === 'advance' ? 'Avançar no acompanhamento' : 'Manter o acompanhamento'
}
function historyNote(history: PmeReportHistoryEntry): string {
  if (history.status === 'error') return 'A série anual não pôde ser apresentada nesta leitura.'
  if (history.status === 'absent') {
    if (history.reason === 'evidence_not_observed') return `A evidência atual está marcada como “${dataStateLabel(history.dataState)}”; não há série anual exibida.`
    if (history.reason === 'indicator_not_mapped') return 'Não há série anual municipal publicada para esta evidência.'
    if (history.reason === 'series_empty') return 'A série anual não contém registros para exibir.'
    return 'Não há série anual disponível para esta evidência no município selecionado.'
  }
  if (history.temporalCompatibility === 'same_period_different_value') return 'O valor anual oferece contexto e difere da observação do relatório no mesmo ano.'
  if (history.temporalCompatibility === 'period_not_in_series' || history.temporalCompatibility === 'current_period_not_published') return 'A série anual oferece contexto; o ano da observação não aparece nesta série.'
  return 'A série anual coincide com a observação do relatório no mesmo ano.'
}

export function buildPmeReportWorkbook(report: PmeReportModel): { fileName: string; sheets: Sheet<Blob>[] } {
  const sourceById = new Map(report.sources.map((source) => [source.sourceId, source]))
  const metadata: Row[] = [
    ['Material', report.title], ['Município', report.municipality.name], ['Código IBGE', report.municipality.ibgeCode], ['UF', 'RS'],
    ['Emitido em', new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short', timeStyle: 'short' }).format(new Date(report.emittedAt))],
    ['Recorte', report.scopeLabel], ['Organização da agenda', 'Os resultados são organizados por meta para apoiar a leitura; o município define suas prioridades.'],
    ...report.caveats.map((caveat) => ['Limite de uso', caveat]),
  ].map((values) => values.map(textCell))
  const evidenceRows: Row[] = report.rows.map((row) => [
    textCell(row.objectiveId), textCell(row.goalId), textCell(row.title), numericCell(row.rawValue), numericCell(row.displayValue),
    textCell(unitLabel(row.unit)), numericCell(row.period), textCell(dataStateLabel(row.dataState)), textCell(row.source), textCell(row.sourceUrls),
    textCell(universeLabel(row.universe)), textCell(row.limit), textCell(row.reading),
  ])
  const goals: Row[] = report.objectives.flatMap((objective) => objective.goals.map((goal) => {
    const source = sourceById.get(goal.legalSourceId)
    return [
      textCell(objective.objectiveId), textCell(objective.title), textCell(goal.goalId), textCell(goal.title), textCell(goal.legalText),
      numericCell(goal.evidence.length), numericCell(goal.counts.observedRelationships),
      textCell(goal.evidence.length ? 'Há evidências relacionadas; isso não significa cobertura integral da meta.' : 'Não há evidência municipal relacionada a esta meta.'),
      textCell(source?.title || 'Fonte oficial indicada no conjunto publicado'), textCell(source?.officialUrl),
    ]
  }))
  const agenda: Row[] = report.agendaItems.map((item) => [
    textCell(item.objectiveId), textCell(item.goalId), textCell(item.title), textCell(classificationLabel(item.classification)),
    textCell(item.publicReading), textCell(item.evidence.relationshipNote), textCell(item.questions.join('\n')),
    textCell(item.paths.map((path) => `${path.title}: ${path.relationReason} ${path.limitations}`).join('\n')),
  ])
  const instruments: Row[] = report.objectives.flatMap((objective) => objective.paths.map((path) => [
    textCell(objective.objectiveId), textCell(path.title), textCell(path.relationReason), textCell(path.competence), textCell(path.officialUrl),
    textCell(path.knownConditions?.join('\n')), textCell(path.evidenceRequired?.join('\n')), textCell(path.limitations),
  ]))
  const methods: Row[] = report.evidence.map((item) => [
    textCell(`Meta ${item.goalId} — ${item.title}`), textCell(modeLabel(item.mode)), textCell(item.methodologyDescription),
    textCell(item.historicalReading), textCell(item.historicalLimit), textCell(item.stateComparison?.valueReading),
    textCell(item.comparisonNote), textCell(item.projection?.achievementReading),
    textCell([item.projection?.modelReading, item.projection?.denominatorReading, item.projection?.uncertaintyReading].filter(Boolean).join(' ')),
  ])
  const sources: Row[] = report.sources.map((source) => [textCell(source.title), textCell(source.officialUrl), textCell(source.period)])
  const histories: Row[] = Object.entries(report.histories).flatMap(([relationId, history]) => {
    const evidence = report.evidence.find((item) => item.relationId === relationId)
    const title = evidence ? `Meta ${evidence.goalId} — ${evidence.title}` : 'Evidência municipal'
    if (history.status === 'available') return history.points.map((point) => [
      textCell(title), numericCell(point.year), numericCell(point.value), textCell(dataStateLabel(point.value === null ? 'null' : 'observed')),
      textCell(unitLabel(history.unit)), textCell(universeLabel(history.universe)), textCell(history.sources.map((source) => source.title).join('; ')), textCell(historyNote(history)),
    ])
    return [[textCell(title), null, null, textCell(history.status === 'error' ? 'Série anual não disponível' : dataStateLabel(history.dataState)), null, null, null, textCell(historyNote(history))]]
  })
  return {
    fileName: `pme-${report.kind}-${report.municipality.ibgeCode}${report.kind === 'caderno' ? `-objetivo-${report.objectives[0]?.objectiveId || 'sem-recorte'}` : ''}-${report.emittedAt.slice(0, 10)}.xlsx`,
    sheets: [
      sheet('Leitura do material', ['Campo', 'Conteúdo'], metadata, [35, 105]),
      sheet('Metas e cobertura', ['Objetivo', 'Tema', 'Meta', 'Título', 'Texto da meta', 'Evidências relacionadas', 'Com observação', 'Nota de cobertura', 'Fonte da meta', 'URL oficial'], goals, [12, 28, 12, 34, 85, 20, 18, 55, 42, 75]),
      sheet('Evidências', ['Objetivo', 'Meta', 'Indicador', 'Valor informado', 'Valor exibido', 'Unidade', 'Ano', 'Situação', 'Fonte', 'URL oficial', 'Universo', 'Limites e notas', 'Leitura publicada'], evidenceRows, [12, 12, 60, 22, 22, 16, 12, 32, 60, 70, 55, 85, 85]),
      sheet('Agenda', ['Objetivo', 'Meta', 'Evidência', 'Situação para acompanhamento', 'Leitura publicada', 'Limites da relação', 'Perguntas para discussão', 'Caminhos de consulta'], agenda, [12, 12, 60, 34, 90, 80, 100, 100]),
      sheet('Instrumentos', ['Objetivo', 'Instrumento', 'Relação com a meta', 'Competência', 'Fonte oficial', 'Condições a verificar', 'Informações necessárias', 'Limites de uso'], instruments, [12, 55, 80, 65, 70, 90, 90, 100]),
      sheet('Método e leituras', ['Meta e evidência', 'Finalidade da evidência', 'Método publicado', 'Leitura histórica', 'Limite histórico', 'Comparação estadual', 'Nota de comparação', 'Projeção publicada', 'Limites da projeção'], methods, [70, 32, 90, 90, 90, 90, 90, 90, 90]),
      sheet('Fontes', ['Fonte', 'URL oficial', 'Período da fonte'], sources, [80, 90, 35]),
      sheet('Séries anuais de apoio', ['Meta e evidência', 'Ano', 'Valor informado', 'Situação', 'Unidade', 'Universo', 'Fontes', 'Nota de leitura'], histories, [70, 14, 22, 32, 18, 70, 80, 90]),
    ],
  }
}
