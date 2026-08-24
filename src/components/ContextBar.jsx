import { buildPageCrumbs } from '../app/navigationRegistry'
import { resolvePageProduct } from '../config/analyticsProducts'
import { ANALYTICS_AVAILABLE, isProductEnabled } from '../config/publicationConfig'
import { ACTIVE_STATE_CONFIG } from '../config/stateConfig'
import { FINANCIAL_PAGE_COPY, getFinancialPageByKey } from '../data/financialModules'
import { InstitutionalTopBarSignature } from './InstitutionalTopBarSignature'
import { MunicipalitySelector } from './MunicipalitySelector'

/*
 * As migalhas não financeiras vêm do registro único de navegação, para que
 * mover uma página de grupo mude a localização anunciada no mesmo lugar em que
 * muda o menu. O catálogo financeiro resolve todas as páginas financeiras
 * antes desta tabela.
 */
const PAGE_CRUMBS = buildPageCrumbs()

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
