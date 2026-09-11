import { PmeEvidenceSources } from './PmeEvidence'
import { PmePageHeading, PmeState } from './PmePrimitives'
import { PmeObjectiveFilters, filterPmeObjectives } from './PmeObjectives'
import { formatPmeValue } from './pmeFormatting'
import { pmeLink, type PmeRoute } from './pmeRoutes'
import type { PmeAgendaItem, PmeMunicipalModel, PmeSourceProvenance } from './pmeTypes'

function publicQuestion(text: string): string {
  return text.trim() === 'rota/tempo/km/dias sem serviço'
    ? 'Verificar rotas, tempos, distâncias e dias sem transporte escolar.'
    : text
}

export function PmeAgendaCard({ item, sources, route, compact = false }: {
  item: PmeAgendaItem; sources: PmeSourceProvenance[]; route: PmeRoute; compact?: boolean
}) {
  return <article className="pme-agenda-item">
    <p className="pme-agenda-context"><span className={`pme-tag${item.classification === 'advance' ? ' pme-tag--attention' : ''}`}>{item.classification === 'advance' ? 'Avançar' : 'Manter o acompanhamento'}</span> <span className="pme-note">Objetivo {item.objectiveId} • Meta {item.goalId}</span></p>
    <h3>{item.title}</h3>
    <p className="pme-observation"><strong>{formatPmeValue(item.evidence.displayValue ?? item.evidence.rawValue, item.evidence.unit)}</strong> em {item.evidence.period}. {item.publicReading || item.evidence.status}</p>
    {compact ? <p className="pme-note">{item.evidence.relationshipNote || 'Confira a ficha para entender o resultado e sua relação com a meta.'}</p> : <>
      <div className="pme-agenda-detail">
        <section className="pme-agenda-detail__reading"><h4>Situação do indicador</h4><p>{item.evidence.status || 'Consulte a referência e o resultado na ficha do objetivo.'}</p>
          <h4>Cuidados na interpretação</h4><p>{item.evidence.relationshipNote || item.evidence.methodologyDescription || 'A evidência está limitada ao universo e ao período do indicador.'}</p><p>{item.evidence.comparisonNote || 'Uma comparação, por si só, não explica as causas do resultado.'}</p>
        </section>
        <section className="pme-agenda-detail__questions"><h4>Perguntas para discussão</h4><ul>{item.questions.map((question) => <li key={question}>{publicQuestion(question)}</li>)}</ul>
        </section>
        <section className="pme-agenda-detail__paths"><h4>Caminhos relacionados</h4><ul>{item.paths.map((path) => <li key={path.id}><a href={pmeLink(route, 'financiamento', { objectiveId: item.objectiveId })}>{path.title}</a></li>)}</ul>
          {!item.paths.length && <p className="pme-note">Não há instrumentos associados a esta meta nesta consulta. Consulte o contexto financeiro do município.</p>}
        </section>
      </div>
      <PmeEvidenceSources evidence={item.evidence} sources={sources} />
    </>}
    <div className="pme-actions"><a className="pme-button pme-button--secondary" href={pmeLink(route, 'objetivo', { objectiveId: item.objectiveId, themeId: null })}>Ver objetivo {item.objectiveId}</a><a href={pmeLink(route, 'evidencias', { objectiveId: item.objectiveId, relationId: item.relationId, evidenceFilter: 'todas', themeId: null })}>Ver indicador</a></div>
  </article>
}

export function PmeAgendaPage({ model, route }: { model: PmeMunicipalModel; route: PmeRoute }) {
  const objectives = filterPmeObjectives(model.objectives, route)
  const visibleIds = new Set(objectives.map((objective) => objective.objectiveId))
  const items = model.agenda.items.filter((item) => visibleIds.has(item.objectiveId))
  return <>
    <PmePageHeading title={`Agenda de Análise de ${model.municipality.name}`} description="Situações observadas nas fontes públicas, perguntas para examinar e caminhos de consulta. A agenda oferece material para discussão nas instâncias municipais." />
    <p className="pme-note">As situações aparecem em ordem de meta, conforme a classificação dos indicadores. Elas apoiam a discussão; as prioridades são definidas pelo município.</p>
    <PmeObjectiveFilters objectives={model.objectives} route={route} />
    <p>{items.length} situações nesta seleção.</p>
    <div className="pme-actions"><a className="pme-button" href={pmeLink(route, 'relatorios', { reportKind: 'agenda' })}>Preparar agenda para discussão</a><a href={pmeLink(route, 'objetivos', { objectiveId: null, themeId: null })}>Consultar os 19 objetivos</a></div>
    {!items.length ? <PmeState title={model.modules.diagnostic.status === 'error' ? 'Não foi possível consultar as situações do município' : 'Nenhuma situação nesta seleção'}><p>Isso não significa ausência de questões educacionais. Consulte as evidências e as lacunas das fichas.</p></PmeState> : <div className="pme-agenda-list">{items.map((item) => <PmeAgendaCard key={item.relationId} item={item} sources={model.sources} route={route} />)}</div>}
  </>
}
