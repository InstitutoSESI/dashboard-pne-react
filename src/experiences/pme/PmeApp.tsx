import { Component, lazy, Suspense, useEffect, useState, type ReactNode } from 'react'
import { PmeShell } from './PmeShell'
import { PmePageHeading, PmeState } from './PmePrimitives'
import { parsePmeHash, pmeLink, type PmeRoute } from './pmeRoutes'
import { findPmeMunicipality } from './pmeRegistry'
import { buildPmeMunicipalModel, buildPmePublicObjectives } from './pmePresentation'
import { createPmeMunicipalLoader } from './pmeLoaders'
import { PmeHomePage } from './PmeHomePage'
import { PmeIntroduction } from './PmeIntroduction'
import { PmeEvidencePage, PmeObjectivesPage } from './PmeObjectives'
import { PmeAgendaPage } from './PmeAgenda'
import { PmeObjectiveSheet } from './PmeObjectiveSheet'
import { PmeTransparencyPage } from './PmeTransparencyPage'
import type { PmeMunicipalityIdentity, PmeMunicipalModel } from './pmeTypes'

const PmeFinancePage = lazy(() => import('./PmeFinancePage').then((module) => ({ default: module.PmeFinancePage })))
const PmeReportsPage = lazy(() => import('./PmeReportsPage').then((module) => ({ default: module.PmeReportsPage })))
const PmeTechnicalReport = lazy(() => import('./PmeTechnicalReport').then((module) => ({ default: module.PmeTechnicalReport })))
const publicBundle = buildPmePublicObjectives()
const municipalLoader = createPmeMunicipalLoader()

class PmePageBoundary extends Component<{ children: ReactNode; resetKey: string }, { failed: boolean; resetKey: string }> {
  state = { failed: false, resetKey: this.props.resetKey }
  static getDerivedStateFromProps(props: { resetKey: string }, state: { resetKey: string }) {
    return props.resetKey === state.resetKey ? null : { failed: false, resetKey: props.resetKey }
  }
  static getDerivedStateFromError() { return { failed: true } }
  render() {
    return this.state.failed ? <PmeState kind="error" title="Não foi possível apresentar esta leitura" onRetry={() => this.setState({ failed: false })}><p>Não foi possível confirmar uma informação necessária à página. Tente novamente ou acesse outra consulta pelo menu.</p></PmeState> : this.props.children
  }
}

function ModuleStates({ model, retry }: { model: PmeMunicipalModel; retry: () => void }) {
  const { diagnostic, matriz } = model.modules
  return <div className="pme-module-states">
    {diagnostic.status === 'not_loaded' && <PmeState kind="loading" title="Carregando o diagnóstico municipal…" />}
    {diagnostic.status === 'error' && <PmeState kind="error" title="Não foi possível carregar o diagnóstico" onRetry={retry}><p>Os resultados municipais não puderam ser consultados com segurança. Tente novamente. As metas e as demais páginas continuam acessíveis.</p></PmeState>}
    {matriz.status === 'not_loaded' && <p className="pme-note" role="status">Consultando os dados de apoio à discussão…</p>}
    {matriz.status === 'not_published' && <p className="pme-note">Os dados de apoio da Matriz ainda não foram publicados para este município. Os indicadores disponíveis continuam acessíveis.</p>}
    {matriz.status === 'error' && <PmeState kind="error" title="Não foi possível carregar os dados de apoio" onRetry={retry}><p>A consulta à Matriz municipal apresentou um problema. Tente novamente para recuperar esses dados. Os demais resultados continuam disponíveis.</p></PmeState>}
  </div>
}

function MunicipalPages({ municipality, route }: { municipality: PmeMunicipalityIdentity; route: PmeRoute }) {
  const [model, setModel] = useState(() => buildPmeMunicipalModel({ municipality }))
  const [error, setError] = useState<string | null>(null)
  const [attempt, setAttempt] = useState(0)
  useEffect(() => {
    let cancelled = false
    setError(null)
    const accept = (result: PmeMunicipalModel) => {
      if (!cancelled && result.municipality.ibgeCode === municipality.ibgeCode) setModel(result)
    }
    void municipalLoader.load(municipality.ibgeCode, accept).then(accept).catch(() => {
      if (!cancelled) setError('Não foi possível confirmar os dados do município selecionado. Tente novamente.')
    })
    return () => { cancelled = true }
  }, [municipality, attempt])
  const objective = model.objectives.find((item) => item.objectiveId === route.objectiveId)
  return <>
    {error && <PmeState kind="error" title="Não foi possível consultar o município" onRetry={() => setAttempt((value) => value + 1)}><p>{error}</p></PmeState>}
    <ModuleStates model={model} retry={() => setAttempt((value) => value + 1)} />
    {route.page === 'inicio' && <PmeHomePage model={model} route={route} />}
    {route.page === 'objetivos' && <PmeObjectivesPage objectives={model.objectives} route={route} />}
    {route.page === 'objetivo' && objective && <PmeObjectiveSheet objective={objective} sources={model.sources} agendaItems={model.agenda.items.filter((item) => item.objectiveId === objective.objectiveId)} route={route} />}
    {route.page === 'agenda' && <PmeAgendaPage model={model} route={route} />}
    {route.page === 'evidencias' && <PmeEvidencePage objectives={model.objectives} sources={model.sources} route={route} />}
    {route.page === 'financiamento' && <PmeFinancePage municipality={municipality} route={route} objectives={model.objectives} matrizStatus={model.modules.matriz.status} />}
    {route.page === 'relatorios' && <PmeReportsPage key={`${route.reportKind}:${route.objectiveId}:${route.themeId}`} model={model} route={route} />}
    {route.page === 'relatorio-tecnico' && model.modules.diagnostic.status !== 'not_loaded' && <PmeTechnicalReport municipality={municipality} route={route} diagnostic={model.modules.diagnostic.status === 'available' ? model.modules.diagnostic.value : null} />}
    {route.page === 'transparencia' && <PmeTransparencyPage sources={model.sources} model={model} />}
  </>
}

function PublicPages({ route }: { route: PmeRoute }) {
  const objective = publicBundle.objectives.find((item) => item.objectiveId === route.objectiveId)
  if (route.page === 'transparencia') return <PmeTransparencyPage sources={publicBundle.sources} />
  if (route.page === 'objetivos') return <PmeObjectivesPage objectives={publicBundle.objectives} route={route} />
  if (route.page === 'objetivo' && objective) return <><PmeState title="Selecione um município para consultar suas observações"><p>A redação das metas e a descrição dos indicadores estão disponíveis abaixo.</p></PmeState><PmeObjectiveSheet objective={objective} sources={publicBundle.sources} route={route} /></>
  if (route.page !== 'inicio') return <><PmePageHeading title="Selecione seu município" /><PmeState title="Consulta municipal"><p>Use o seletor no topo para abrir esta etapa. Enquanto isso, consulte <a href={pmeLink(route, 'objetivos')}>os 19 objetivos e suas metas</a>.</p></PmeState></>
  return <PmeIntroduction route={route} />
}

export function PmeApp() {
  const [route, setRoute] = useState(() => parsePmeHash(window.location.hash))
  useEffect(() => {
    const onHashChange = () => {
      setRoute(parsePmeHash(window.location.hash))
      window.requestAnimationFrame(() => document.querySelector<HTMLHeadingElement>('.pme-main h1')?.focus())
    }
    window.addEventListener('hashchange', onHashChange)
    return () => window.removeEventListener('hashchange', onHashChange)
  }, [])
  const municipality = findPmeMunicipality(route.municipalityId)
  const error = route.error || (route.municipalityId && !municipality ? 'Este código não pertence ao registro municipal do RS.' : null)
  return <PmeShell route={route}>
    <PmePageBoundary key={route.municipalityId} resetKey={`${route.page}:${route.objectiveId}`}><Suspense fallback={<PmeState kind="loading" title="Preparando a página…" />}>
      {error ? <><PmePageHeading title="Endereço inválido" /><PmeState kind="error" title="Não foi possível abrir esta seleção"><p>O endereço não corresponde a uma página ou município disponível. Use o menu ou retorne ao início para refazer a consulta.</p><a href={pmeLink(route, 'apresentacao', { municipalityId: null, objectiveId: null, themeId: null, evidenceFilter: 'todas' })}>Retornar ao início</a></PmeState></>
        : route.page === 'apresentacao' ? <PmeIntroduction route={route} municipality={municipality || undefined} />
          : municipality ? <MunicipalPages key={municipality.ibgeCode} municipality={municipality} route={route} /> : <PublicPages route={route} />}
    </Suspense></PmePageBoundary>
  </PmeShell>
}
