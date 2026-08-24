import { resolvePageProduct } from '../config/analyticsProducts'
import { ANALYTICS_AVAILABLE, isProductEnabled } from '../config/publicationConfig'
import { ACTIVE_STATE_CONFIG } from '../config/stateConfig'
import { FINANCIAL_PAGE_COPY, getFinancialPageByKey } from '../data/financialModules'
import { InstitutionalTopBarSignature } from './InstitutionalTopBarSignature'
import { MunicipalitySelector } from './MunicipalitySelector'

const PAGE_CRUMBS = {
  caderno: 'Metas do PNE / Planejamento municipal / Caderno de hipóteses',
  'cenarios-educacao': 'Metas do PNE / Planejamento municipal / Cenários da educação',
  diagnostico: 'Metas do PNE / Ciclo vigente / Diagnóstico municipal',
  educacao: 'Indicadores de Educação',
  financeiros: FINANCIAL_PAGE_COPY.parentLabel,
  home: 'Home',
  'matriz-prioridades': 'Metas do PNE / Planejamento municipal / Matriz de Prioridades',
  'pne-legal-goals': 'Metas legais do PNE 2026-2036 / Ciclo vigente',
  pne2014: 'Metas do PNE / Ciclo encerrado / Resultado consolidado',
  pne2026: 'Metas do PNE / Ciclo vigente / Acompanhamento atual',
}

export function ContextBar({
  activePage,
  municipalities,
  onMunicipalityChange,
  selectedMunicipalityId,
}) {
  const financialPage = getFinancialPageByKey(activePage)
  const activeProduct = resolvePageProduct(activePage)
  const productAvailable = activeProduct === null || isProductEnabled(activeProduct)
  const crumb = !ANALYTICS_AVAILABLE
    ? `Cadastro municipal / ${ACTIVE_STATE_CONFIG.stateName}`
    : !productAvailable
        ? `Publicação parcial / ${ACTIVE_STATE_CONFIG.stateName}`
        : (financialPage
            ? `${FINANCIAL_PAGE_COPY.parentLabel} / ${financialPage.title}`
            : PAGE_CRUMBS[activePage] ?? 'Dashboard PNE')

  return (
    <div className="context-bar">
      <div className="context-bar__selector">
        <MunicipalitySelector
          municipalities={municipalities}
          selectedMunicipalityId={selectedMunicipalityId}
          onChange={onMunicipalityChange}
          placeholder="Buscar município"
        />
      </div>

      <div className="context-bar__spacer" aria-hidden="true" />

      <InstitutionalTopBarSignature />

      <div className="context-bar__crumb" aria-label="Localização atual">
        {crumb}
      </div>

      <div className="context-bar__meta">
        {ANALYTICS_AVAILABLE && productAvailable
          ? 'Dados oficiais do painel'
          : 'Cadastro territorial oficial'}
      </div>
    </div>
  )
}
