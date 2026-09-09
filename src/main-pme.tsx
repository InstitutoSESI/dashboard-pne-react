import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import '@fontsource/source-sans-3/latin-400.css'
import '@fontsource/source-sans-3/latin-500.css'
import '@fontsource/source-sans-3/latin-600.css'
import '@fontsource/source-sans-3/latin-700.css'
import '@fontsource/source-serif-4/latin-600.css'
import './styles/design-tokens.css'
import './experiences/pme/styles/pme.css'
import { PmeApp } from './experiences/pme/PmeApp'
import { ACTIVE_STATE_CONFIG, PLATFORM_LABEL } from './config/stateConfig'

if (ACTIVE_STATE_CONFIG.stateCode !== 'RS') throw new Error('A experiência PME está disponível somente para o RS.')
document.title = `${PLATFORM_LABEL} | Evidências para o PME`
document.querySelector('meta[name="description"]')?.setAttribute('content',
  'Dados públicos dos municípios do Rio Grande do Sul para leitura dos objetivos do PNE, análise municipal e discussão do PME.')
const root = document.getElementById('root')
if (!root) throw new Error('Elemento de montagem da experiência PME ausente.')
createRoot(root).render(<StrictMode><PmeApp /></StrictMode>)
