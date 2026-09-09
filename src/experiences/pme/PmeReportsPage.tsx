import { useEffect, useMemo, useState } from 'react'
import { flushSync } from 'react-dom'
import { PmeAgendaCard } from './PmeAgenda'
import { PmeObjectiveSheet } from './PmeObjectiveSheet'
import { PmeObjectiveFilters } from './PmeObjectives'
import { PmePageHeading, PmeState, PmeTableRegion } from './PmePrimitives'
import { buildPmeReport, loadPmeReportHistories, PME_REPORT_TITLES, type PmeReportModel } from './pmeReports'
import { formatPmeValue, PME_DATA_LABELS } from './pmeFormatting'
import { pmeLink, type PmeReportKind, type PmeRoute } from './pmeRoutes'
import type { PmeDataState, PmeEvidence, PmeMunicipalModel } from './pmeTypes'

const REPORT_CHOICES: Array<{ kind: PmeReportKind; title: string; description: string }> = [
  { kind: 'sintese', title: 'Síntese', description: 'Principais resultados, cobertura e leituras para uma conversa executiva.' },
  { kind: 'caderno', title: 'Caderno', description: 'Metas, evidências, perguntas e caminhos de consulta por objetivo.' },
  { kind: 'agenda', title: 'Agenda', description: 'Situações publicadas e perguntas para orientar a discussão municipal.' },
]

function ReportCoverage({ report }: { report: PmeReportModel }) {
  return <PmeTableRegion label="Dados disponíveis por objetivo"><table>
    <caption>Dados disponíveis por objetivo</caption>
    <thead><tr><th scope="col">Objetivo</th><th className="pme-numeric" scope="col">Metas</th><th className="pme-numeric" scope="col">Medidas acompanhadas</th><th className="pme-numeric" scope="col">Com dados</th><th scope="col">Informações ausentes</th></tr></thead>
    <tbody>{report.objectives.map((objective) => {
      const missing = ([
        [objective.counts.unavailableRelationships, 'indisponíveis'], [objective.counts.nullRelationships, 'com valor nulo'],
        [objective.counts.suppressedRelationships, 'suprimidas'], [objective.counts.notApplicableRelationships, 'não aplicáveis'],
        [objective.counts.notPublishedRelationships, 'sem publicação'], [objective.counts.notLoadedRelationships, 'não carregadas'],
      ] as Array<[number, string]>).filter(([count]) => count > 0).map(([count, label]) => `${count} ${label}`).join('; ')
      return <tr key={objective.objectiveId}>
        <th scope="row">{objective.objectiveId}. {objective.title}</th><td className="pme-numeric">{objective.goals.length}</td><td className="pme-numeric">{objective.counts.methodologicalRelationships}</td><td className="pme-numeric">{objective.counts.observedRelationships}</td>
        <td>{missing || '—'}</td>
      </tr>
    })}</tbody>
  </table></PmeTableRegion>
}

function ReportEvidenceTable({ report }: { report: PmeReportModel }) {
  return <PmeTableRegion label="Evidências do relatório, com valor, ano, situação e fonte"><table className="pme-report-table">
    <caption>Evidências do recorte</caption>
    <thead><tr><th className="pme-report-indicator" scope="col">Indicador e meta</th><th className="pme-report-value pme-numeric" scope="col">Valor</th><th className="pme-report-year pme-numeric" scope="col">Ano</th><th className="pme-report-state" scope="col">Situação</th><th className="pme-report-source" scope="col">Fonte</th></tr></thead>
    <tbody>{report.rows.map((row) => <tr key={row.relationId}>
      <th scope="row">{row.title}<small>Meta {row.goalId}</small>{row.limit && <small>{row.limit}</small>}</th><td className="pme-numeric">{formatPmeValue(row.displayValue ?? row.rawValue, row.unit)}</td>
      <td className="pme-numeric">{row.period ?? '—'}</td><td>{PME_DATA_LABELS[row.dataState as PmeDataState]}</td><td>{row.source}</td>
    </tr>)}</tbody>
  </table></PmeTableRegion>
}

export function PmeReportsPage({ model, route }: { model: PmeMunicipalModel; route: PmeRoute }) {
  const [emittedAt, setEmittedAt] = useState(() => new Date().toISOString())
  const [downloadStatus, setDownloadStatus] = useState<'idle' | 'busy' | 'done' | 'error'>('idle')
  const needsObjective = route.reportKind === 'caderno' && !route.objectiveId
  const scopeEvidence = useMemo(() => model.objectives.filter((objective) => (!route.objectiveId || objective.objectiveId === route.objectiveId) && (!route.themeId || objective.themeId === route.themeId))
    .flatMap((objective) => objective.goals.flatMap((goal) => goal.evidence)), [model.objectives, route.objectiveId, route.themeId])
  const [historyState, setHistoryState] = useState<{ evidence: PmeEvidence[]; entries: PmeReportModel['histories'] } | null>(null)
  const diagnosticStatus = model.modules.diagnostic.status
  useEffect(() => {
    if (needsObjective || diagnosticStatus === 'not_loaded') return
    let cancelled = false
    void loadPmeReportHistories(model.municipality.ibgeCode, scopeEvidence).then((entries) => {
      if (!cancelled) setHistoryState({ evidence: scopeEvidence, entries })
    })
    return () => { cancelled = true }
  }, [model.municipality.ibgeCode, scopeEvidence, needsObjective, diagnosticStatus])
  const histories = historyState?.evidence === scopeEvidence ? historyState.entries : undefined
  const report = useMemo(() => needsObjective ? null : buildPmeReport(model, route, emittedAt, histories), [model, route, emittedAt, needsObjective, histories])
  const loading = diagnosticStatus === 'not_loaded' || model.modules.matriz.status === 'not_loaded' || histories === undefined
  const canExport = !loading && !!report?.objectives.length
  async function download() {
    if (!canExport) return
    setDownloadStatus('busy')
    const emission = new Date().toISOString()
    setEmittedAt(emission)
    try {
      const { downloadPmeReportXlsx } = await import('./pmeReportXlsx')
      await downloadPmeReportXlsx(buildPmeReport(model, route, emission, histories))
      setDownloadStatus('done')
    } catch {
      setDownloadStatus('error')
    }
  }
  function print() {
    if (!canExport) return
    const title = document.title
    flushSync(() => setEmittedAt(new Date().toISOString()))
    document.title = `PME - ${PME_REPORT_TITLES[route.reportKind]} - ${model.municipality.name}`
    try { window.print() } finally { document.title = title }
  }
  return <>
    <div className="pme-no-print"><PmePageHeading title="Materiais para leitura e discussão" description="Prepare uma síntese, um caderno por objetivo ou uma agenda. Confira a prévia e exporte em PDF ou Excel." /></div>
    <div className="pme-report-choice pme-no-print" aria-label="Escolha o material">
      {REPORT_CHOICES.map((choice) => <button aria-pressed={route.reportKind === choice.kind} key={choice.kind} onClick={() => {
        window.location.hash = pmeLink(route, 'relatorios', { reportKind: choice.kind, objectiveId: route.objectiveId, themeId: null, evidenceFilter: 'todas' })
      }} type="button"><strong>{choice.title}</strong><span>{choice.description}</span></button>)}
    </div>
    <PmeObjectiveFilters objectives={model.objectives} route={route} />
    {needsObjective ? <PmeState title="Selecione um objetivo para preparar o caderno"><p>O caderno reúne as metas, evidências, perguntas e instrumentos do objetivo escolhido.</p></PmeState> : report && <>
      <div className="pme-actions"><button className="pme-button" type="button" onClick={print} disabled={!canExport}>Imprimir / salvar PDF</button><button className="pme-button pme-button--secondary" type="button" onClick={() => { void download() }} disabled={!canExport || downloadStatus === 'busy'}>{downloadStatus === 'busy' ? 'Preparando XLSX…' : 'Baixar XLSX'}</button><a href={pmeLink(route, 'relatorio-tecnico')}>Abrir Relatório Técnico Municipal</a></div>
      {loading && <p className="pme-no-print" role="status">Preparando os dados do material…</p>}
      {downloadStatus === 'done' && <p className="pme-no-print" role="status">Planilha preparada para download.</p>}
      {downloadStatus === 'error' && <PmeState kind="error" title="Não foi possível gerar a planilha"><p>Tente baixar novamente. O documento permanece disponível para leitura e impressão.</p></PmeState>}
      <article className="pme-report">
        <header className="pme-report-header"><h2>{report.title}</h2><div className="pme-report-meta"><span><strong>Local:</strong> {report.municipality.name} / RS</span><span><strong>Escopo:</strong> {report.scopeLabel}</span><span><strong>Data:</strong> {new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short', timeStyle: 'short' }).format(new Date(report.emittedAt))}</span></div></header>
        {!report.objectives.length && <PmeState title="Nenhum objetivo neste recorte"><p>Revise os filtros antes de utilizar o material.</p></PmeState>}
        {report.kind === 'caderno' ? report.objectives.map((objective) => <PmeObjectiveSheet key={objective.objectiveId} objective={objective} sources={model.sources} agendaItems={report.agendaItems.filter((item) => item.objectiveId === objective.objectiveId)} route={route} histories={report.histories} forReport />)
          : <>
            <section className="pme-section"><h2>{report.kind === 'sintese' ? 'Principais resultados' : 'Situações e perguntas para discussão'}</h2><p className="pme-note">Os resultados estão organizados por meta. A definição de prioridades cabe ao município.</p>
              <div className={`pme-agenda-list${report.kind === 'sintese' ? ' pme-agenda-list--summary' : ''}`}>{(report.kind === 'sintese' ? report.agendaItems.slice(0, 4) : report.agendaItems).map((item) => <PmeAgendaCard compact={report.kind === 'sintese'} key={item.relationId} item={item} sources={model.sources} route={route} />)}</div>
              {!report.agendaItems.length && <p>Nenhuma situação classificada disponível neste recorte. Essa ausência não demonstra adequação nem ausência de questão municipal.</p>}
            </section>
            {report.kind === 'sintese' && <section className="pme-section"><h2>Leituras históricas disponíveis</h2><ul>{report.evidence.filter((item) => item.historicalReading).slice(0, 4).map((item) => <li key={item.relationId}>Meta {item.goalId}: {item.historicalReading} Fonte: {item.sourceIds.map((id) => model.sources.find((source) => source.sourceId === id)?.title || 'Fonte oficial disponível').join('; ')}.</li>)}</ul><p className="pme-note">Sem leitura histórica disponível, não se afirma tendência.</p></section>}
            <ReportCoverage report={report} />
          </>}
        <section className="pme-section"><h2>Tabelas de apoio</h2><ReportEvidenceTable report={report} /></section>
        <section className="pme-section"><h2>Cuidados para a leitura</h2><ul className="pme-note-list">{report.caveats.map((caveat) => <li key={caveat}>{caveat}</li>)}</ul></section>
        <section className="pme-section"><h2>Fontes consultadas</h2><ul className="pme-source-list">{report.sources.map((source) => <li key={source.sourceId}>{source.officialUrl ? <a href={source.officialUrl}>{source.title}</a> : source.title}{source.period ? ` • Período da fonte: ${source.period}` : ''}</li>)}</ul></section>
      </article>
    </>}
  </>
}
