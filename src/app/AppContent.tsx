import { ErrorState } from '../components/ErrorState'
import { LoadingState } from '../components/LoadingState'
import { ANALYTICS_AVAILABLE } from '../config/publicationConfig'
import { StatePublicationStatusPage } from '../pages/StatePublicationStatusPage'
import type { AppPageKey } from '../types/app'
import type { InitialAppData } from '../types/data'
import type { Navigate, ParsedAppLocation } from '../types/navigation'
import { AppPageRouter } from './AppPageRouter'

interface AppContentProps {
  activePage: AppPageKey
  initialData: InitialAppData
  navigationContext: ParsedAppLocation
  onNavigate: Navigate
}

export function AppContent({ activePage, initialData, navigationContext, onNavigate }: AppContentProps) {
  if (initialData.loading) {
    return <LoadingState message="Carregando base do dashboard..." />
  }

  if (initialData.error) {
    return <ErrorState title="Erro ao carregar dados iniciais" message={initialData.error} />
  }

  if (!ANALYTICS_AVAILABLE) {
    return <StatePublicationStatusPage />
  }

  if (!initialData.indicadores) {
    return <LoadingState message="Preparando município..." />
  }

  return (
    <AppPageRouter
      activePage={activePage}
      indicadores={initialData.indicadores}
      municipalities={initialData.municipalities}
      navigationContext={navigationContext}
      onNavigate={onNavigate}
    />
  )
}
