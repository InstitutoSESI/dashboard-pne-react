import { PmeEvidenceBlock } from './PmeEvidence'
import { PmeEditorialPaths } from './PmeEditorialPaths'
import { PmePageHeading } from './PmePrimitives'
import { resolveSignalReading } from '../../features/matriz/matrizSignalLanguage'
import { pmeLink, type PmeRoute } from './pmeRoutes'
import type { PmeAgendaItem, PmeObjectiveModel, PmeSourceProvenance } from './pmeTypes'
import type { PmeReportModel } from './pmeReports'

function publishedTexts(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : []
}

const PUBLIC_TEXT_REPLACEMENTS: Record<string, string> = {
  'rota/tempo/km/dias sem serviço': 'Verificar rotas, tempos, distâncias e dias sem transporte escolar.',
}

function publicText(value: string): string {
  const trimmed = value.trim()
  return PUBLIC_TEXT_REPLACEMENTS[trimmed] || trimmed
}

function uniqueTexts(values: string[]): string[] {
  const seen = new Set<string>()
  return values.map(publicText).filter((value) => {
    const key = value.replace(/\s+/gu, ' ').toLocaleLowerCase('pt-BR')
    if (!key || seen.has(key)) return false
    seen.add(key)
    return true
  })
}

function textKey(value: string): string {
  return publicText(value).replace(/\s+/gu, ' ').toLocaleLowerCase('pt-BR')
}

function publicProof(proof: Record<string, unknown> | null) {
  if (!proof || !['measureId', 'unit', 'period'].every((key) => typeof proof[key] === 'string')
    || !(typeof proof.valueRaw === 'string' || typeof proof.valueRaw === 'number')) return null
  return resolveSignalReading({
    measureId: String(proof.measureId), unit: String(proof.unit), period: String(proof.period),
    valueRaw: String(proof.valueRaw), dimensions: typeof proof.dimensions === 'string' ? proof.dimensions : '',
    caution: typeof proof.caution === 'string' ? proof.caution : '', direction: 'descriptive',
    maxInference: typeof proof.maxInference === 'string' ? proof.maxInference : '', observability: '', stance: '',
  })
}

export function PmeObjectiveSheet({ objective, sources, agendaItems = [], route, forReport = false, histories }: {
  objective: PmeObjectiveModel; sources: PmeSourceProvenance[]; agendaItems?: PmeAgendaItem[]; route: PmeRoute; forReport?: boolean; histories?: PmeReportModel['histories']
}) {
  const guidingQuestion = publicText(objective.guidingQuestion)
  const questions = uniqueTexts([...objective.matrizContexts.flatMap((context) => context.questions), ...agendaItems.flatMap((item) => item.questions)])
    .filter((question) => textKey(question) !== textKey(guidingQuestion))
  const causes = [...new Map(objective.matrizContexts.flatMap((context) => context.priorityGoal?.causes || []).map((cause) => [cause.factorId, cause])).values()]
  const shownQuestionKeys = new Set([textKey(guidingQuestion), ...questions.map(textKey)])
  const observationsLoaded = objective.counts.notLoadedRelationships === 0
  return <>
    {!forReport && <PmePageHeading title={`Objetivo ${objective.objectiveId} — ${objective.title}`} description={objective.guidingQuestion} />}
    <p className="pme-note">Consulte a redação oficial de cada meta e os indicadores que ajudam a acompanhar o município.</p>
    <dl className="pme-counts"><div><dt>Metas do objetivo</dt><dd>{objective.goals.length}</dd></div><div><dt>Medidas acompanhadas</dt><dd>{objective.counts.methodologicalRelationships}</dd></div><div><dt>Leituras com dados</dt><dd>{observationsLoaded ? objective.counts.observedRelationships : '—'}</dd></div></dl>
    {!forReport && <div className="pme-actions"><a className="pme-button" href={pmeLink(route, 'relatorios', { reportKind: 'caderno', objectiveId: objective.objectiveId, themeId: null })}>Preparar caderno deste objetivo</a><a href={pmeLink(route, 'agenda', { objectiveId: objective.objectiveId, themeId: null })}>Ver situações na Agenda</a><a href={pmeLink(route, 'financiamento', { objectiveId: objective.objectiveId })}>Consultar financiamento</a></div>}
    <section className="pme-section"><h2>Metas, evidências e limites</h2>
      {objective.goals.map((goal) => {
        const source = sources.find((entry) => entry.sourceId === goal.legalSourceId)
        return <section className="pme-goal" key={goal.goalId} data-goal-id={goal.goalId}>
          <h3>Meta {goal.goalId} — {goal.title}</h3><p className="pme-legal-text">{goal.legalText}</p>
          <p className="pme-note">Referência: {source?.officialUrl ? <a href={source.officialUrl}>{source.title}</a> : source?.title || 'Plano Nacional de Educação'}.</p>
          {goal.evidence.length ? goal.evidence.map((evidence) => <PmeEvidenceBlock key={evidence.relationId} evidence={evidence} sources={sources} route={route} expanded={forReport} history={histories ? histories[evidence.relationId] ?? null : undefined} />)
            : <p className="pme-note">Ainda não há indicador municipal associado a esta meta. A falta de dados não permite avaliar se a situação está adequada.</p>}
        </section>
      })}
    </section>
    <section className="pme-section pme-context-discussion"><div className="pme-context-questions"><h2>Questões para a discussão municipal</h2>
      {forReport && <p className="pme-context-questions__lead"><strong>Pergunta de abertura:</strong> {guidingQuestion}</p>}
      <p>Use estas perguntas para relacionar os resultados ao contexto local e orientar a discussão do PME.</p>
      {questions.length ? <ul>{questions.map((question) => <li key={question}>{question}</li>)}</ul> : <p className="pme-note">A pergunta de abertura desta ficha orienta a discussão deste objetivo.</p>}
    </div>
      {causes.length ? <div className="pme-context-cause-list">{causes.map((cause) => {
        const proof = publicProof(cause.proof)
        const checks = uniqueTexts(publishedTexts(cause.collapsed.howToConfirmLocally)).filter((question) => !shownQuestionKeys.has(textKey(question)))
        const firstStep = publicText(cause.firstStep.text)
        const firstStepAlreadyShown = shownQuestionKeys.has(textKey(firstStep)) || checks.some((question) => textKey(question) === textKey(firstStep))
        return <section className="pme-support" key={cause.factorId}>
        <h3>Hipótese a investigar: {cause.name}</h3>
        {proof && <p><strong>{proof.label}:</strong> {proof.display} • {proof.period}.</p>}
        <p className="pme-note">{String(cause.proof?.caution || 'O resultado, por si só, não confirma esta hipótese.')}</p>
        {checks.length > 0 && <ul>{checks.map((question) => <li key={question}>{question}</li>)}</ul>}
        {!firstStepAlreadyShown && <p><strong>Primeiro passo sugerido:</strong> {firstStep}</p>}
      </section>})}</div> : <p className="pme-note">Não há dados de apoio adicionais para esta ficha. Ao aprofundar a discussão, consulte informações locais sobre escolas, redes e grupos atendidos.</p>}
    </section>
    <section className="pme-section"><h2>Financiamento e instrumentos relacionados</h2>
      <PmeEditorialPaths paths={objective.paths} />
      <p><a href={pmeLink(route, 'financiamento', { objectiveId: objective.objectiveId })}>Examinar o contexto financeiro municipal deste objetivo</a></p>
    </section>
    <section className="pme-section"><h2>Antes de levar à reunião</h2>
      <ol><li>Confira período, fonte, universo e limitações dos indicadores antes da comparação.</li><li>Separe o resultado observado das hipóteses que dependem de verificação local.</li><li>Examine as competências municipais e as responsabilidades compartilhadas.</li><li>Verifique regras, custos e etapas financeiras nas fontes competentes antes de deliberar.</li><li>Utilize o caderno na discussão do PME e registre as decisões pelos meios próprios do município.</li></ol>
    </section>
  </>
}
