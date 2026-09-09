import type { PmeAgendaItem, PmeEvidence, PmeMunicipalModel, PmeObjectiveModel } from './pmeTypes'
import type { PmeReportKind, PmeRoute } from './pmeRoutes'
import { loadPmeEvidenceHistory, type PmeEvidenceHistory } from './pmeEvidenceHistory'

export const PME_REPORT_TITLES: Record<PmeReportKind, string> = {
  sintese: 'Síntese executiva municipal', caderno: 'Caderno por objetivo', agenda: 'Agenda para discussão',
}

export interface PmeReportRow {
  objectiveId: string
  goalId: string
  relationId: string
  title: string
  rawValue: number | null
  displayValue: number | null
  unit: string | null
  period: number | null
  dataState: string
  source: string
  sourceUrls: string
  universe: string
  limit: string
  reading: string
}

export interface PmeReportModel {
  kind: PmeReportKind
  title: string
  emittedAt: string
  municipality: PmeMunicipalModel['municipality']
  scopeLabel: string
  objectives: PmeObjectiveModel[]
  evidence: PmeEvidence[]
  agendaItems: PmeAgendaItem[]
  rows: PmeReportRow[]
  caveats: string[]
  sourceModel: PmeMunicipalModel
  sources: PmeMunicipalModel['sources']
  histories: Record<string, PmeReportHistoryEntry>
}

export type PmeReportHistoryEntry = PmeEvidenceHistory | { status: 'error'; message: string }

/** The cached municipal loader makes one request even when many relations use its series. */
export async function loadPmeReportHistories(municipalityId: string, evidence: PmeEvidence[]): Promise<Record<string, PmeReportHistoryEntry>> {
  const results = await Promise.allSettled(evidence.map((item) => loadPmeEvidenceHistory(municipalityId, item)))
  return Object.fromEntries(evidence.map((item, index) => {
    const result = results[index]
    return [item.relationId, result.status === 'fulfilled' ? result.value : { status: 'error', message: result.reason instanceof Error ? result.reason.message : 'A série pública não pôde ser validada.' }]
  }))
}

/** One frozen scope feeds the screen, print and XLSX. Numeric values stay raw. */
export function buildPmeReport(model: PmeMunicipalModel, route: PmeRoute, emittedAt: string, histories: Record<string, PmeReportHistoryEntry> = {}): PmeReportModel {
  if (!Number.isFinite(Date.parse(emittedAt))) throw new Error('Data de emissão do relatório inválida.')
  if (route.municipalityId !== model.municipality.ibgeCode) throw new Error('O município do relatório diverge do endereço solicitado.')
  if (route.reportKind === 'caderno' && !route.objectiveId) throw new Error('Selecione um objetivo para preparar o caderno.')
  const objectives = model.objectives.filter((objective) => (!route.objectiveId || objective.objectiveId === route.objectiveId)
    && (!route.themeId || objective.themeId === route.themeId))
  const objectiveIds = new Set(objectives.map((objective) => objective.objectiveId))
  const evidence = [...new Map(objectives.flatMap((objective) => objective.goals.flatMap((goal) => goal.evidence)).map((item) => [item.relationId, item])).values()]
  const agendaItems = model.agenda.items.filter((item) => objectiveIds.has(item.objectiveId))
  const sources = new Map(model.sources.map((source) => [source.sourceId, source]))
  const scopeSourceIds = new Set([...evidence.flatMap((item) => item.sourceIds), ...objectives.flatMap((objective) => objective.goals.map((goal) => goal.legalSourceId))])
  if (objectives.some((objective) => objective.matrizContexts.length)) scopeSourceIds.add('pne2026_matriz')
  const scopeSources = model.sources.filter((source) => scopeSourceIds.has(source.sourceId))
  const rows: PmeReportRow[] = evidence.map((item) => ({
    objectiveId: item.goalId.split('.')[0], goalId: item.goalId, relationId: item.relationId, title: item.title,
    rawValue: item.rawValue, displayValue: item.displayValue, unit: item.unit, period: item.period, dataState: item.dataState,
    source: item.sourceIds.map((id) => sources.get(id)?.title || 'Fonte oficial disponível').join('; '),
    sourceUrls: item.sourceIds.map((id) => sources.get(id)?.officialUrl).filter(Boolean).join('; '),
    universe: item.territoriality || 'Universo não detalhado nesta relação',
    limit: [item.relationshipNote, item.comparisonNote, item.historicalLimit].filter(Boolean).join(' '),
    reading: item.publicReading || item.dataStatusLabel || '',
  }))
  const caveats = [
    'Os valores, situações e leituras reproduzem as publicações disponíveis. Este material não cria pontuação, ranking ou relação de causa e efeito.',
    'Zero observado, valor nulo, indisponibilidade, supressão, não aplicabilidade e ausência de publicação são situações diferentes.',
    'Cada indicador mantém o seu próprio ano, recorte e fonte. A data de emissão não altera essas referências.',
  ]
  if (objectives.some((objective) => objective.paths.length)) caveats.push('Indicações de instrumentos servem para consulta e não confirmam vigência, adesão, elegibilidade, saldo ou disponibilidade de recursos.')
  if (model.modules.diagnostic.status !== 'available') caveats.unshift('As observações municipais não puderam ser incluídas nesta leitura porque a publicação necessária não ficou disponível.')
  if (model.modules.matriz.status === 'error') caveats.unshift('O apoio complementar de orientações locais não pôde ser usado nesta leitura. As informações municipais disponíveis permanecem no material.')
  const selectedHistories = Object.fromEntries(evidence.flatMap((item) => histories[item.relationId] ? [[item.relationId, histories[item.relationId]]] : []))
  if (Object.values(selectedHistories).some((history) => history.status === 'error')) caveats.push('Uma ou mais séries anuais de apoio não puderam ser apresentadas. Nenhuma observação do relatório foi substituída.')
  if (Object.values(selectedHistories).some((history) => history.status === 'available' && history.temporalCompatibility !== 'same_period_and_value')) caveats.push('Algumas séries anuais oferecem apenas contexto temporal e não substituem a observação apresentada no relatório.')
  return {
    kind: route.reportKind, title: PME_REPORT_TITLES[route.reportKind], emittedAt, municipality: model.municipality,
    scopeLabel: `${route.objectiveId ? `Objetivo ${route.objectiveId}` : 'Todos os objetivos'}${route.themeId ? `; tema ${objectives[0]?.themeLabel || route.themeId}` : ''}; ${objectives.length} ${objectives.length === 1 ? 'objetivo' : 'objetivos'} e ${objectives.reduce((total, objective) => total + objective.goals.length, 0)} metas no recorte.`,
    objectives, evidence, agendaItems, rows, caveats, sourceModel: model, sources: scopeSources, histories: selectedHistories,
  }
}
