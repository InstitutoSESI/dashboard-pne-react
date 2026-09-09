import { PmeAgendaCard } from './PmeAgenda'
import { PmePageHeading } from './PmePrimitives'
import { pmeLink, type PmeRoute } from './pmeRoutes'
import type { PmeMunicipalModel } from './pmeTypes'

export function PmeHomePage({ model, route }: { model: PmeMunicipalModel; route: PmeRoute }) {
  const allGoals = model.objectives.flatMap((objective) => objective.goals)
  const evidence = allGoals.flatMap((goal) => goal.evidence)
  const histories = evidence.filter((item) => item.historicalReading)
  const gaps = allGoals.filter((goal) => !goal.evidence.length || goal.evidence.every((item) => item.dataState !== 'observed'))
  const diagnosticReady = model.modules.diagnostic.status === 'available'
  return <>
    <PmePageHeading title={`Panorama de ${model.municipality.name}`} description="Conheça os resultados da educação municipal e os temas que merecem atenção na discussão do PME." />
    <p className="pme-note">Rio Grande do Sul • Os anos de referência aparecem junto aos resultados.</p>
    <dl className="pme-counts"><div><dt>Objetivos do PNE</dt><dd>{model.objectives.length}</dd></div><div><dt>Metas com indicadores</dt><dd>{allGoals.filter((goal) => goal.evidence.length).length} / {allGoals.length}</dd></div><div><dt>Leituras com dados</dt><dd>{diagnosticReady ? evidence.filter((item) => item.dataState === 'observed').length : '—'}</dd></div></dl>
    <p className="pme-note">Um indicador pode apoiar a leitura de mais de uma meta. Estas contagens mostram a cobertura dos dados disponíveis.</p>
    <div className="pme-actions"><a className="pme-button" href={pmeLink(route, 'agenda', { objectiveId: null, themeId: null })}>Abrir Agenda de Análise</a><a className="pme-button pme-button--secondary" href={pmeLink(route, 'relatorios', { reportKind: 'sintese', objectiveId: null, themeId: null })}>Preparar síntese executiva</a></div>
    <section className="pme-section"><div className="pme-section-heading"><h2>Situações para examinar</h2><a href={pmeLink(route, 'agenda', { objectiveId: null, themeId: null })}>Ver todas as situações</a></div>
      <p className="pme-note">Destaques em ordem de meta, conforme a situação dos indicadores. A definição das prioridades cabe ao município.</p>
      {model.agenda.highlights.length ? <div className="pme-agenda-list pme-agenda-list--summary">{model.agenda.highlights.map((item) => <PmeAgendaCard key={item.relationId} item={item} sources={model.sources} route={route} compact />)}</div>
        : <p>Não há destaques disponíveis nesta consulta. As fichas mostram quais informações estão disponíveis para cada meta.</p>}
    </section>
    <section className="pme-section pme-panorama-context"><div><h2>O que mudou ao longo dos anos</h2>
      {histories.length ? <ul className="pme-reading-list">{histories.slice(0, 4).map((item) => <li key={item.relationId}><a href={pmeLink(route, 'evidencias', { objectiveId: item.goalId.split('.')[0], relationId: item.relationId, themeId: null, evidenceFilter: 'todas' })}>Meta {item.goalId} — {item.title}</a><p>{item.historicalReading}</p></li>)}</ul>
        : <p>Não há leitura histórica utilizável nesta seleção. Uma observação isolada não demonstra avanço ou persistência.</p>}
      <p className="pme-note">Até quatro destaques, em ordem de meta. Consulte as fichas para ver os gráficos e as demais séries disponíveis.</p>
    </div>
    <div><h2>O que ainda falta conhecer</h2>{diagnosticReady ? <p>{gaps.length} metas estão sem indicador associado ou sem resultado disponível. A falta de dados não significa que a necessidade educacional deixou de existir.</p> : <p>A contagem das lacunas estará disponível quando os resultados municipais forem carregados. Todas as metas continuam acessíveis.</p>}
      <h3>Aprofunde a leitura</h3><ul className="pme-reading-list"><li><a href={pmeLink(route, 'objetivos', { objectiveId: null, themeId: null })}>Percorrer os 19 objetivos e todas as metas</a></li><li><a href={pmeLink(route, 'financiamento', { objectiveId: null, themeId: null })}>Consultar o contexto financeiro municipal</a></li><li><a href={pmeLink(route, 'evidencias', { objectiveId: null, themeId: null, evidenceFilter: 'lacunas' })}>Identificar as leituras sem resultado disponível</a></li></ul>
    </div></section>
  </>
}
