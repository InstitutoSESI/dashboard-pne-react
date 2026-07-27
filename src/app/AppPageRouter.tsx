import { ErrorState } from '../components/ErrorState'
import { LoadingState } from '../components/LoadingState'
import { lazy, Suspense, useEffect, useMemo, useRef, type ComponentType, type ReactNode } from 'react'
import { useMunicipality } from '../context/MunicipalityContext'
import { FINANCIAL_PAGE_KEYS } from '../data/financialPageKeys'
import { EDUCATION_SECTION_KEYS, resolveEducationSection } from '../data/educationIndicatorCatalog'
import { useMunicipioData } from '../hooks/useMunicipioData'
import { Home } from '../pages/Home'
import type { AppPageKey } from '../types/app'
import type { IndicadoresPayload, MunicipioIndexEntry, MunicipioName } from '../types/data'
import type { Navigate, ParsedAppLocation } from '../types/navigation'
import { isFinancialPage } from './appRoutes'
import { EmptyMunicipioState } from './EmptyMunicipioState'
import { PageLoadBoundary } from './PageLoadBoundary'
import { replaceHashContext } from '../utils/hashNavigation'

const LazyCyclePage = lazy(() => import('../pages/CyclePage').then((module) => ({ default: module.CyclePage })))
const LazyDiagnostico = lazy(() => import('../pages/Diagnostico').then((module) => ({ default: module.Diagnostico })))
const LazyEducationPage = lazy(() => import('../features/education/EducationPage').then((module) => ({ default: module.EducationPage })))
const LazyFinancialPage = lazy(() => import('../pages/FinancialPage').then((module) => ({ default: module.FinancialPage })))
const LazyMunicipalFinancePanoramaPage = lazy(() => import('../features/municipal-finance/MunicipalFinancePanoramaPage').then((module) => ({ default: module.MunicipalFinancePanoramaPage })))
const LazyPneLegalGoalsPage = lazy(() => import('../pages/PneLegalGoalsPage').then((module) => ({ default: module.PneLegalGoalsPage })))
const LazyPneOverviewPage = lazy(() => import('../pages/PneOverviewPage').then((module) => ({ default: module.PneOverviewPage })))

interface AppPageRouterProps {
  activePage: AppPageKey
  indicadores: IndicadoresPayload
  municipios: MunicipioName[]
  municipiosIndex: MunicipioIndexEntry[]
  navigationContext: ParsedAppLocation
  onNavigate: Navigate
}

type PneLegalGoalsPageProps = {
  indicadores: IndicadoresPayload
  municipioData?: unknown
  municipios?: MunicipioName[]
  onMunicipioChange: (value: MunicipioName | null) => void
  onNavigate: Navigate
  selectedMunicipio: MunicipioName | null
}

const TypedPneLegalGoalsPage = LazyPneLegalGoalsPage as ComponentType<PneLegalGoalsPageProps>

function LazyPageBoundary({ children, page }: { children: ReactNode; page: AppPageKey }) {
  return (
    <PageLoadBoundary key={page}>
      <Suspense fallback={<LoadingState message="Carregando página..." />}>
        {children}
      </Suspense>
    </PageLoadBoundary>
  )
}

export function AppPageRouter({
  activePage,
  indicadores,
  municipios,
  municipiosIndex,
  navigationContext,
  onNavigate,
}: AppPageRouterProps) {
  const { selectedMunicipio, setSelectedMunicipio } = useMunicipality()
  const {
    data: municipioData,
    error: municipioError,
    loading: municipioLoading,
  } = useMunicipioData(municipiosIndex, selectedMunicipio)
  const selectedMunicipalityEntry = useMemo(() => (
    municipiosIndex.find((item) => item.nome === selectedMunicipio) ?? null
  ), [municipiosIndex, selectedMunicipio])
  const isEducationDataPage = activePage === 'educacao' || activePage === 'relatorio-tecnico-municipal'
  const isLegacyTechnicalReportRoute = activePage === 'educacao'
    && resolveEducationSection({
      requestedSection: navigationContext.params.get('secao'),
    }) === EDUCATION_SECTION_KEYS.technicalReport
  const requestedMunicipalityValue = activePage === FINANCIAL_PAGE_KEYS.panorama || isEducationDataPage
    ? navigationContext.params.get('municipio')?.trim() ?? ''
    : ''
  const requestedMunicipalityEntry = useMemo(() => {
    if (!requestedMunicipalityValue) return null
    const normalized = requestedMunicipalityValue.toLocaleLowerCase('pt-BR')
    return municipiosIndex.find((item) => (
      item.slug === normalized
      || item.id_municipio === normalized
      || item.nome.toLocaleLowerCase('pt-BR') === normalized
    )) ?? null
  }, [municipiosIndex, requestedMunicipalityValue])
  const loadedMunicipalityId = typeof municipioData?.id_municipio === 'string'
    ? municipioData.id_municipio
    : null
  const educationUrlSyncRef = useRef<{ pending: boolean; slug: string } | null>(null)

  useEffect(() => {
    if (!isLegacyTechnicalReportRoute) return
    replaceHashContext('relatorio-tecnico-municipal', {
      detalhe: null,
      secao: null,
      tema: null,
      theme: null,
    })
  }, [isLegacyTechnicalReportRoute])

  useEffect(() => {
    if (
      activePage === FINANCIAL_PAGE_KEYS.panorama
      && requestedMunicipalityEntry
      && requestedMunicipalityEntry.nome !== selectedMunicipio
    ) {
      setSelectedMunicipio(requestedMunicipalityEntry.nome)
    }
  }, [activePage, requestedMunicipalityEntry, selectedMunicipio, setSelectedMunicipio])

  useEffect(() => {
    if (!isEducationDataPage || !requestedMunicipalityEntry) return

    const currentSync = educationUrlSyncRef.current
    if (currentSync?.slug === requestedMunicipalityEntry.slug) {
      if (currentSync.pending && requestedMunicipalityEntry.nome === selectedMunicipio) {
        currentSync.pending = false
      }
      return
    }

    educationUrlSyncRef.current = {
      pending: requestedMunicipalityEntry.nome !== selectedMunicipio,
      slug: requestedMunicipalityEntry.slug,
    }
    if (requestedMunicipalityEntry.nome !== selectedMunicipio) {
      setSelectedMunicipio(requestedMunicipalityEntry.nome)
    }
  }, [isEducationDataPage, requestedMunicipalityEntry, selectedMunicipio, setSelectedMunicipio])

  useEffect(() => {
    if (!isEducationDataPage || isLegacyTechnicalReportRoute) return

    const route = navigationContext.rawRoute
      || (activePage === 'relatorio-tecnico-municipal' ? 'relatorio-tecnico-municipal' : 'educacao')
    if (requestedMunicipalityEntry) {
      const currentSync = educationUrlSyncRef.current
      if (
        currentSync?.slug === requestedMunicipalityEntry.slug
        && !currentSync.pending
        && selectedMunicipalityEntry
        && selectedMunicipalityEntry.slug !== requestedMunicipalityEntry.slug
      ) {
        educationUrlSyncRef.current = { pending: false, slug: selectedMunicipalityEntry.slug }
        replaceHashContext(route, { municipio: selectedMunicipalityEntry.slug })
        return
      }
      if (requestedMunicipalityValue !== requestedMunicipalityEntry.slug) {
        replaceHashContext(route, { municipio: requestedMunicipalityEntry.slug })
      }
      return
    }

    educationUrlSyncRef.current = null
    replaceHashContext(route, { municipio: selectedMunicipalityEntry?.slug ?? null })
  }, [
    activePage,
    isEducationDataPage,
    isLegacyTechnicalReportRoute,
    navigationContext.rawRoute,
    requestedMunicipalityEntry,
    requestedMunicipalityValue,
    selectedMunicipalityEntry,
  ])

  if (activePage === 'home') {
    return <Home onNavigate={onNavigate} selectedMunicipio={selectedMunicipio} />
  }

  if (activePage === 'pne-overview') {
    return (
      <LazyPageBoundary page={activePage}>
        <LazyPneOverviewPage onNavigate={onNavigate} />
      </LazyPageBoundary>
    )
  }

  if (activePage === 'pne-legal-goals' && !selectedMunicipio) {
    return (
      <LazyPageBoundary page={activePage}>
        <TypedPneLegalGoalsPage
          indicadores={indicadores}
          municipios={municipios}
          onMunicipioChange={setSelectedMunicipio}
          onNavigate={onNavigate}
          selectedMunicipio={selectedMunicipio}
        />
      </LazyPageBoundary>
    )
  }

  if (activePage === FINANCIAL_PAGE_KEYS.panorama) {
    return (
      <LazyPageBoundary page={activePage}>
        <LazyMunicipalFinancePanoramaPage
          municipalityIdentifier={requestedMunicipalityEntry?.id_municipio ?? loadedMunicipalityId}
          municipalityName={requestedMunicipalityEntry?.nome ?? selectedMunicipio}
          navigationContext={navigationContext}
        />
      </LazyPageBoundary>
    )
  }

  if (isFinancialPage(activePage)) {
    return (
      <LazyPageBoundary page={activePage}>
        <LazyFinancialPage
          municipioData={municipioData}
          municipioError={municipioError}
          municipioLoading={municipioLoading}
          pageKey={activePage}
          selectedMunicipio={selectedMunicipio}
        />
      </LazyPageBoundary>
    )
  }

  if (
    isEducationDataPage
    && requestedMunicipalityEntry
    && requestedMunicipalityEntry.nome !== selectedMunicipio
  ) {
    return <LoadingState message={`Carregando dados de ${requestedMunicipalityEntry.nome}...`} />
  }

  if (!selectedMunicipio) {
    return (
      <EmptyMunicipioState
        onNavigate={onNavigate}
        onMunicipioChange={setSelectedMunicipio}
        municipios={municipios}
      />
    )
  }

  if (municipioLoading) {
    return <LoadingState message={`Carregando dados de ${selectedMunicipio}...`} />
  }

  if (municipioError) {
    return (
      <ErrorState
        title="Erro ao carregar dados do município"
        message={municipioError}
      />
    )
  }

  if (activePage === 'pne2014') {
    return (
      <LazyPageBoundary page={activePage}>
        <LazyCyclePage
        cycle="pne_2014_2024"
        indicadores={indicadores}
        municipioData={municipioData}
        selectedMunicipio={selectedMunicipio}
        title="PNE 2014–2024"
        />
      </LazyPageBoundary>
    )
  }

  if (activePage === 'pne2026') {
    return (
      <LazyPageBoundary page={activePage}>
        <LazyCyclePage
        cycle="pne_2026_2036"
        indicadores={indicadores}
        municipioData={municipioData}
        selectedMunicipio={selectedMunicipio}
        title="PNE 2026–2036"
        />
      </LazyPageBoundary>
    )
  }

  if (activePage === 'pne-legal-goals') {
    return (
      <LazyPageBoundary page={activePage}>
        <TypedPneLegalGoalsPage
          indicadores={indicadores}
          municipioData={municipioData}
          municipios={municipios}
          onMunicipioChange={setSelectedMunicipio}
          onNavigate={onNavigate}
          selectedMunicipio={selectedMunicipio}
        />
      </LazyPageBoundary>
    )
  }

  if (activePage === 'diagnostico') {
    return (
      <LazyPageBoundary page={activePage}>
        <LazyDiagnostico
          municipioData={municipioData}
          selectedMunicipio={selectedMunicipio}
        />
      </LazyPageBoundary>
    )
  }

  if (isEducationDataPage) {
    return (
      <LazyPageBoundary page={activePage}>
        <LazyEducationPage
          indicadores={indicadores}
          municipioData={municipioData}
          municipalitySlug={selectedMunicipalityEntry?.slug ?? null}
          navigationContext={navigationContext}
          selectedMunicipio={selectedMunicipio}
        />
      </LazyPageBoundary>
    )
  }

  return null
}
