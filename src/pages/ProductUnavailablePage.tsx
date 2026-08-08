import { ANALYTICS_PRODUCT_LABELS, type AnalyticsProduct } from '../config/analyticsProducts'
import { ACTIVE_PUBLICATION_CONFIG, ENABLED_PRODUCTS } from '../config/publicationConfig'
import { ACTIVE_STATE_CONFIG } from '../config/stateConfig'

interface ProductUnavailablePageProps {
  product: AnalyticsProduct
}

/**
 * Indisponibilidade de um produto numa publicação parcial. Reutiliza o bloco
 * visual de `StatePublicationStatusPage`; nenhum estilo novo é introduzido.
 */
export function ProductUnavailablePage({ product }: ProductUnavailablePageProps) {
  const productLabel = ANALYTICS_PRODUCT_LABELS[product]
  const availableLabels = ENABLED_PRODUCTS.map((item) => ANALYTICS_PRODUCT_LABELS[item])

  return (
    <div className="state-publication-status">
      <header className="state-publication-status__hero">
        <p className="state-publication-status__eyebrow">
          Publicação municipal · {ACTIVE_STATE_CONFIG.stateCode}
        </p>
        <h1>{productLabel} ainda não foi publicado para {ACTIVE_STATE_CONFIG.stateName}.</h1>
        <p className="state-publication-status__lead">
          Esta publicação é parcial: apenas as frentes já validadas com fontes próprias do
          estado estão disponíveis. As demais permanecem indisponíveis até que seus dados
          sejam produzidos e validados integralmente.
        </p>
      </header>

      <section className="state-publication-status__notice" aria-live="polite">
        <div>
          <p className="state-publication-status__notice-label">Frentes disponíveis</p>
          <h2>
            {availableLabels.length > 0
              ? availableLabels.join(' · ')
              : 'Nenhuma frente analítica publicada'}
          </h2>
          <p>
            Use a navegação lateral para consultar as frentes já publicadas. Nenhum indicador de{' '}
            {productLabel} foi gerado para este território.
          </p>
        </div>
        <p className="state-publication-status__message">
          {ACTIVE_PUBLICATION_CONFIG.analyticsMessage}
        </p>
      </section>
    </div>
  )
}
