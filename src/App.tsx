import './App.css'
import './styles/chart-system.css'
import './styles/pne-cycle-experience.css'
import './styles/platform-ui.css'
import './styles/financial-pages.css'
import './styles/navigation-shell.css'
import { AppContent } from './app/AppContent'
import { Layout } from './components/Layout'
import { MunicipalityProvider } from './context/MunicipalityContext'
import { useAppHashNavigation } from './hooks/useAppHashNavigation'
import { useInitialAppData } from './hooks/useInitialAppData'

function App() {
  const {
    activeEducationSection,
    activePage,
    navigationContext,
    navigate,
  } = useAppHashNavigation()
  const initialData = useInitialAppData()

  return (
    <MunicipalityProvider municipalities={initialData.municipalities}>
      <Layout
        activePage={activePage}
        activeEducationSection={activeEducationSection}
        municipalities={initialData.municipalities}
        onNavigate={navigate}
      >
        <AppContent
          activePage={activePage}
          initialData={initialData}
          navigationContext={navigationContext}
          onNavigate={navigate}
        />
      </Layout>
    </MunicipalityProvider>
  )
}

export default App
