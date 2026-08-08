import { ErrorState } from '../components/ErrorState'
import { LoadingState } from '../components/LoadingState'
import {
  lazy,
  Suspense,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  type ReactNode,
} from 'react'
import { resolvePageProduct } from '../config/analyticsProducts'
import { isProductEnabled } from '../config/publicationConfig'
import { useMunicipality } from '../context/MunicipalityContext'
import { FINANCIAL_PAGE_KEYS } from '../data/financialPageKeys'
import { EDUCATION_SECTION_KEYS, resolveEducationSection } from '../data/educationIndicatorCatalog'
import {
  getEffectiveMunicipality,
  resolveMunicipalityRouteRequest,
} from '../domain/municipalityRouting'
import { useMunicipioData } from '../hooks/useMunicipioData'
import { Home } from '../pages/Home'
import { ProductUnavailablePage } from '../pages/ProductUnavailablePage'
import type { AppPageKey } from '../types/app'
import type { IndicadoresPayload, MunicipalityId, MunicipalityRef } from '../types/data'
import type { Navigate, ParsedAppLocation } from '../types/navigation'
import { replaceHashContext } from '../utils/hashNavigation'
import { isFinancialPage } from './appRoutes'
import { EmptyMunicipioState } from './EmptyMunicipioState'
import { PageLoadBoundary } from './PageLoadBoundary'

const LazyCyclePage = lazy(() => import('../pages/CyclePage').then((module) => ({ default: module.CyclePage })))
const LazyDiagnostico = lazy(() => import('../pages/Diagnostico').then((module) => ({ default: module.Diagnostico })))
const LazyEducationPage = lazy(() => import('../features/education/EducationPage').then((module) => ({ default: module.EducationPage })))
const LazyFinancialPage = lazy(() => import('../pages/FinancialPage').then((module) => ({ default: module.FinancialPage })))
const LazyPriorityMatrixPage = lazy(() => import('../pages/PriorityMatrixPage').then((module) => ({ default: module.PriorityMatrixPage })))
const LazyMunicipalFinancePanoramaPage = lazy(() => import('../features/municipal-finance/MunicipalFinancePanoramaPage').then((module) => ({ default: module.MunicipalFinancePanoramaPage })))
const LazyPneLegalGoalsPage = lazy(() => import('../pages/PneLegalGoalsPage').then((module) => ({ default: module.PneLegalGoalsPage })))
const LazyPneOverviewPage = lazy(() => import('../pages/PneOverviewPage').then((module) => ({ default: module.PneOverviewPage })))

interface AppPageRouterProps {
  activePage: AppPageKey
  indicadores: IndicadoresPayload | null
  municipalities: MunicipalityRef[]
  navigationContext: ParsedAppLocation
  onNavigate: Navigate
}

/**
 * Publicação parcial sem PNE não possui `indicadores.json`. O catálogo vazio
 * mantém os consumidores tipados sem inventar conteúdo analítico.
 */
const EMPTY_INDICADORES: IndicadoresPayload = Object.freeze({})

interface MunicipalityRouteSync {
  routeKey: string
  municipalityId: MunicipalityId | null
}

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
  indicadores: rawIndicadores,
  municipalities,
  navigationContext,
  onNavigate,
}: AppPageRouterProps) {
  const indicadores = rawIndicadores ?? EMPTY_INDICADORES
  const activeProduct = resolvePageProduct(activePage)
  const {
    selectedMunicipality,
    selectedMunicipalityId,
    selectionReady,
    setSelectedMunicipalityId,
  } = useMunicipality()
  const isEducationDataPage = activePage === 'educacao'
    || activePage === 'relatorio-tecnico-municipal'
  const isLegacyTechnicalReportRoute = activePage === 'educacao'
    && resolveEducationSection({
      requestedSection: navigationContext.params.get('secao'),
    }) === EDUCATION_SECTION_KEYS.technicalReport
  const requestedMunicipalityValue = navigationContext.params.get('municipio')?.trim() ?? ''
  const shouldSyncMunicipalityUrl = isEducationDataPage
    || activePage === FINANCIAL_PAGE_KEYS.panorama
    || navigationContext.params.has('municipio')
  const routeResolution = useMemo(() => (
    shouldSyncMunicipalityUrl
      ? resolveMunicipalityRouteRequest(municipalities, requestedMunicipalityValue)
      : { municipality: null, shouldNormalize: false }
  ), [municipalities, requestedMunicipalityValue, shouldSyncMunicipalityUrl])
  const requestedMunicipality = routeResolution.municipality
  const effectiveMunicipality = getEffectiveMunicipality(
    shouldSyncMunicipalityUrl ? requestedMunicipalityValue : '',
    requestedMunicipality,
    selectedMunicipality,
  )
  const effectiveMunicipalityId = effectiveMunicipality?.ibgeCode ?? null
  const selectedMunicipio = effectiveMunicipality?.name ?? null
  const routeSyncRef = useRef<MunicipalityRouteSync | null>(null)
  const {
    data: municipioData,
    error: municipioError,
    loading: municipioLoading,
  } = useMunicipioData(effectiveMunicipalityId)
  const loadedMunicipalityId = typeof municipioData?.id_municipio === 'string'
    ? municipioData.id_municipio
    : null
  const municipalityPayloadChanging = Boolean(
    effectiveMunicipalityId
    && municipioData
    && loadedMunicipalityId !== effectiveMunicipalityId,
  )

  useEffect(() => {
    if (!isLegacyTechnicalReportRoute) return
    replaceHashContext('relatorio-tecnico-municipal', {
      detalhe: null,
      secao: null,
      tema: null,
      theme: null,
    })
  }, [isLegacyTechnicalReportRoute])

  useLayoutEffect(() => {
    if (!selectionReady || !shouldSyncMunicipalityUrl || isLegacyTechnicalReportRoute) {
      routeSyncRef.current = null
      return
    }

    const route = navigationContext.rawRoute
      || (activePage === 'relatorio-tecnico-municipal'
        ? 'relatorio-tecnico-municipal'
        : activePage)
    const routeKey = `${route}\u0000${requestedMunicipalityValue}`
    const currentSync = routeSyncRef.current

    if (requestedMunicipality) {
      if (!currentSync || currentSync.routeKey !== routeKey) {
        routeSyncRef.current = {
          routeKey,
          municipalityId: requestedMunicipality.ibgeCode,
        }
        if (selectedMunicipalityId !== requestedMunicipality.ibgeCode) {
          setSelectedMunicipalityId(requestedMunicipality.ibgeCode)
        }
        if (routeResolution.shouldNormalize) {
          replaceHashContext(route, { municipio: requestedMunicipality.slug })
        }
        return
      }

      if (selectedMunicipalityId !== currentSync.municipalityId) {
        routeSyncRef.current = null
        replaceHashContext(route, { municipio: selectedMunicipality?.slug ?? null })
        return
      }

      if (routeResolution.shouldNormalize) {
        replaceHashContext(route, { municipio: requestedMunicipality.slug })
      }
      return
    }

    if (requestedMunicipalityValue) {
      if (!currentSync || currentSync.routeKey !== routeKey) {
        routeSyncRef.current = {
          routeKey,
          municipalityId: selectedMunicipalityId,
        }
        return
      }

      if (currentSync.municipalityId !== selectedMunicipalityId) {
        routeSyncRef.current = null
        replaceHashContext(route, { municipio: selectedMunicipality?.slug ?? null })
      }
      return
    }

    routeSyncRef.current = null
    if (selectedMunicipality) {
      replaceHashContext(route, { municipio: selectedMunicipality.slug })
    }
  }, [
    activePage,
    isLegacyTechnicalReportRoute,
    navigationContext.rawRoute,
    requestedMunicipality,
    requestedMunicipalityValue,
    routeResolution.shouldNormalize,
    selectedMunicipality,
    selectedMunicipalityId,
    selectionReady,
    setSelectedMunicipalityId,
    shouldSyncMunicipalityUrl,
  ])

  if (!selectionReady) {
    return <LoadingState message="Preparando município..." />
  }

  if (activeProduct !== null && !isProductEnabled(activeProduct)) {
    return <ProductUnavailablePage product={activeProduct} />
  }

  if (activePage === 'home') {
    return <Home onNavigate={onNavigate} />
  }

  if (activePage === 'pne-overview') {
    return (
      <LazyPageBoundary page={activePage}>
        <LazyPneOverviewPage onNavigate={onNavigate} />
      </LazyPageBoundary>
    )
  }

  if (activePage === 'matriz-prioridades') {
    return (
      <LazyPageBoundary page={activePage}>
        <LazyPriorityMatrixPage onNavigate={onNavigate} />
      </LazyPageBoundary>
    )
  }

  if (activePage === 'pne-legal-goals' && !effectiveMunicipalityId) {
    return (
      <LazyPageBoundary page={activePage}>
        <LazyPneLegalGoalsPage
          indicadores={indicadores}
          municipioData={null}
          municipalities={municipalities}
          onMunicipalityChange={setSelectedMunicipalityId}
          onNavigate={onNavigate}
          selectedMunicipalityId={null}
          selectedMunicipio={null}
        />
      </LazyPageBoundary>
    )
  }

  if (activePage === FINANCIAL_PAGE_KEYS.panorama) {
    return (
      <LazyPageBoundary page={activePage}>
        <LazyMunicipalFinancePanoramaPage
          municipalityIdentifier={effectiveMunicipalityId}
          municipalityName={selectedMunicipio}
          navigationContext={navigationContext}
        />
      </LazyPageBoundary>
    )
  }

  if (isFinancialPage(activePage)) {
    return (
      <LazyPageBoundary page={activePage}>
        <LazyFinancialPage
          municipalityId={effectiveMunicipalityId}
          municipioData={municipioData}
          municipioError={municipioError}
          municipioLoading={municipioLoading || municipalityPayloadChanging}
          pageKey={activePage}
          selectedMunicipio={selectedMunicipio}
        />
      </LazyPageBoundary>
    )
  }

  if (!effectiveMunicipalityId || !effectiveMunicipality) {
    return (
      <EmptyMunicipioState
        onNavigate={onNavigate}
        onMunicipalityChange={setSelectedMunicipalityId}
        municipalities={municipalities}
      />
    )
  }

  if (municipioLoading || municipalityPayloadChanging) {
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
        <LazyPneLegalGoalsPage
          indicadores={indicadores}
          municipioData={municipioData}
          municipalities={municipalities}
          onMunicipalityChange={setSelectedMunicipalityId}
          onNavigate={onNavigate}
          selectedMunicipalityId={effectiveMunicipalityId}
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
          municipalityId={effectiveMunicipalityId}
          municipalitySlug={effectiveMunicipality.slug}
          navigationContext={navigationContext}
          selectedMunicipio={effectiveMunicipality.name}
        />
      </LazyPageBoundary>
    )
  }

  return null
}
