import { useState, type ReactNode } from 'react'
import { PmeEvidenceBlock } from './PmeEvidence'
import { PmePageHeading, PmeState } from './PmePrimitives'
import { pmeLink, type PmeRoute } from './pmeRoutes'
import type { PmeObjectiveModel, PmeSourceProvenance } from './pmeTypes'

export function PmeObjectiveFilters({ objectives, route, showAvailability = false, children }: {
  objectives: PmeObjectiveModel[]; route: PmeRoute; showAvailability?: boolean; children?: ReactNode
}) {
  const themes = [...new Map(objectives.map((objective) => [objective.themeId, objective.themeLabel])).entries()]
  return <div className="pme-filters pme-no-print">
    <label>Objetivo<select value={route.objectiveId || ''} onChange={(event) => { window.location.hash = pmeLink(route, route.page, { objectiveId: event.target.value || null }) }}>
      <option value="">Todos os 19 objetivos</option>{objectives.map((objective) => <option key={objective.objectiveId} value={objective.objectiveId}>{objective.objectiveId}. {objective.title}</option>)}
    </select></label>
    <label>Tema<select value={route.themeId || ''} onChange={(event) => { window.location.hash = pmeLink(route, route.page, { themeId: event.target.value || null }) }}>
      <option value="">Todos os temas</option>{themes.map(([id, label]) => <option key={id} value={id}>{label}</option>)}
    </select></label>
    {showAvailability && <label>Situação dos dados<select value={route.evidenceFilter} onChange={(event) => { window.location.hash = pmeLink(route, route.page, { evidenceFilter: event.target.value as PmeRoute['evidenceFilter'] }) }}>
      <option value="todas">Todos os resultados</option><option value="observadas">Com dados disponíveis</option><option value="lacunas">Sem resultado disponível</option>
    </select></label>}
    {children}
    <a href={pmeLink(route, route.page, { objectiveId: null, themeId: null, evidenceFilter: 'todas', relationId: null })}>Limpar filtros</a>
  </div>
}

export function filterPmeObjectives(objectives: PmeObjectiveModel[], route: PmeRoute): PmeObjectiveModel[] {
  return objectives.filter((objective) => (!route.objectiveId || objective.objectiveId === route.objectiveId)
    && (!route.themeId || objective.themeId === route.themeId))
}

export function PmeObjectiveMap({ objectives, route }: { objectives: PmeObjectiveModel[]; route: PmeRoute }) {
  return <div className="pme-objective-grid">{objectives.map((objective) => <a key={objective.objectiveId} className="pme-objective-card" href={pmeLink(route, 'objetivo', { objectiveId: objective.objectiveId, themeId: null })}>
    <h3><span aria-label={`Objetivo ${objective.objectiveId}`}>{objective.objectiveId}</span>{objective.title}</h3>
    <p>{objective.goals.length} {objective.goals.length === 1 ? 'meta' : 'metas'} • {objective.counts.methodologicalRelationships} {objective.counts.methodologicalRelationships === 1 ? 'medida acompanhada' : 'medidas acompanhadas'}</p>
    <small className="pme-coverage">{objective.counts.notLoadedRelationships ? route.municipalityId ? 'Aguardando os resultados municipais.' : 'Selecione um município para ver os resultados.' : `${objective.counts.observedRelationships} ${objective.counts.observedRelationships === 1 ? 'leitura' : 'leituras'} com dados disponíveis.`}
      {!objective.counts.methodologicalRelationships && ' Sem indicador municipal associado.'}
    </small>
  </a>)}</div>
}

export function PmeObjectivesPage({ objectives, route }: { objectives: PmeObjectiveModel[]; route: PmeRoute }) {
  const filtered = filterPmeObjectives(objectives, route)
  const goals = objectives.reduce((count, objective) => count + objective.goals.length, 0)
  return <>
    <PmePageHeading title="Panorama dos 19 objetivos" description={`Explore as ${goals} metas e os resultados disponíveis. Os títulos resumem o tema de cada objetivo; a redação oficial das metas está nas fichas.`} />
    <PmeObjectiveFilters objectives={objectives} route={route} />
    <p className="pme-note">{filtered.length} de {objectives.length} objetivos nesta seleção.</p>
    {filtered.length ? <PmeObjectiveMap objectives={filtered} route={route} /> : <PmeState title="Nenhum objetivo neste recorte"><p>Limpe os filtros para retornar aos 19 objetivos.</p></PmeState>}
    <section className="pme-section"><h2>Como ler a cobertura</h2><p>Cada medida acompanhada associa um indicador a uma meta. Um mesmo indicador pode contribuir para mais de uma meta. As fichas mostram os resultados disponíveis e explicam quando um dado está ausente, protegido ou não se aplica.</p><p>A ausência de informação não demonstra ausência de uma questão educacional.</p></section>
  </>
}

export function PmeEvidencePage({ objectives, sources, route }: { objectives: PmeObjectiveModel[]; sources: PmeSourceProvenance[]; route: PmeRoute }) {
  const [query, setQuery] = useState('')
  const foldedQuery = query.normalize('NFD').replace(/\p{Diacritic}/gu, '').toLocaleLowerCase('pt-BR')
  const rows = filterPmeObjectives(objectives, route).flatMap((objective) => objective.goals.flatMap((goal) => goal.evidence))
    .filter((evidence) => (!route.relationId || evidence.relationId === route.relationId)
      && (route.evidenceFilter === 'todas' || (route.evidenceFilter === 'observadas' ? evidence.dataState === 'observed' : evidence.dataState !== 'observed'))
      && `${evidence.title} ${evidence.goalId}`.normalize('NFD').replace(/\p{Diacritic}/gu, '').toLocaleLowerCase('pt-BR').includes(foldedQuery))
  return <>
    <PmePageHeading title="Evidências e indicadores" description="Encontre os indicadores de cada meta, compare resultados e acompanhe sua evolução. Abra os detalhes para consultar o método e as fontes." />
    <PmeObjectiveFilters objectives={objectives} route={route} showAvailability>
      <label>Buscar indicador ou meta<input type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Ex.: creche ou 1.a" /></label>
    </PmeObjectiveFilters>
    <p role="status">{rows.length} leituras nesta seleção.</p>
    {!rows.length ? <PmeState title="Nenhum resultado nesta seleção"><p>Revise a busca e os filtros. Os objetivos sem indicador continuam disponíveis no panorama.</p></PmeState> : rows.map((evidence) => <PmeEvidenceBlock key={evidence.relationId} evidence={evidence} sources={sources} route={route} />)}
  </>
}
