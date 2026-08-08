import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import '@fontsource/source-sans-3/latin-400.css'
import '@fontsource/source-sans-3/latin-500.css'
import '@fontsource/source-sans-3/latin-600.css'
import '@fontsource/source-sans-3/latin-700.css'
import '@fontsource/source-serif-4/latin-600.css'
import '@fontsource/source-serif-4/latin-700.css'
import './index.css'
import App from './App'
import { ACTIVE_STATE_CONFIG } from './config/stateConfig'
import './styles/institutional-refresh.css'
import './styles/typography-system.css'

const platformLabel = `Painel SESI-${ACTIVE_STATE_CONFIG.stateCode}`
document.title = `${platformLabel} · Inteligência Analítica Municipal`
document.querySelector('meta[name="description"]')?.setAttribute(
  'content',
  `${platformLabel} para compreender, acompanhar e planejar a educação municipal em ${ACTIVE_STATE_CONFIG.stateName}.`,
)

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
