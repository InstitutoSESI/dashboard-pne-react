import { FINANCIAL_PAGE_COPY, getFinancialPageByKey } from '../data/financialModules'
import { InstitutionalTopBarSignature } from './InstitutionalTopBarSignature'
import { MunicipalitySelector } from './MunicipalitySelector'

const PAGE_CRUMBS = {
  diagnostico: 'Metas do PNE / Ciclo vigente / Diagnóstico municipal',
  educacao: 'Indicadores de Educação',
  financeiros: FINANCIAL_PAGE_COPY.parentLabel,
  home: 'Home',
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
  const crumb = financialPage
    ? `${FINANCIAL_PAGE_COPY.parentLabel} / ${financialPage.title}`
    : PAGE_CRUMBS[activePage] ?? 'Dashboard PNE'

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

      <div className="context-bar__meta">Dados oficiais do painel</div>
    </div>
  )
}
