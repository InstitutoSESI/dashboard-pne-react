import { Database, MapPinned, ShieldCheck } from 'lucide-react'
import { ACTIVE_PUBLICATION_CONFIG } from '../config/publicationConfig'
import { ACTIVE_STATE_CONFIG } from '../config/stateConfig.js'
import { useMunicipality } from '../context/MunicipalityContext'

export function StatePublicationStatusPage() {
  const { selectedMunicipality } = useMunicipality()

  return (
    <div className="state-publication-status">
      <header className="state-publication-status__hero">
        <p className="state-publication-status__eyebrow">
          Publicação municipal · {ACTIVE_STATE_CONFIG.stateCode}
        </p>
        <h1>{ACTIVE_STATE_CONFIG.stateName} já está configurada para hospedagem.</h1>
        <p className="state-publication-status__lead">
          O cadastro territorial oficial está ativo e isolado na publicação {ACTIVE_STATE_CONFIG.stateNameForms.withDe}.
          Os módulos analíticos serão liberados somente depois da validação das fontes próprias de
          Alagoas.
        </p>
      </header>

      <section className="state-publication-status__facts" aria-label="Situação da publicação">
        <article>
          <MapPinned aria-hidden="true" />
          <span>Território disponível</span>
          <strong>{ACTIVE_STATE_CONFIG.expectedMunicipalityCount} municípios</strong>
          <p>Códigos IBGE textuais, nomes oficiais e rotas municipais validadas.</p>
        </article>
        <article>
          <ShieldCheck aria-hidden="true" />
          <span>Isolamento confirmado</span>
          <strong>Sem dados de outras UFs</strong>
          <p>O artefato de AL possui uma raiz pública própria e falha diante de contaminação.</p>
        </article>
        <article>
          <Database aria-hidden="true" />
          <span>Indicadores analíticos</span>
          <strong>Em preparação</strong>
          <p>PNE, Educação, Financiamento e Diagnóstico permanecem indisponíveis.</p>
        </article>
      </section>

      <section className="state-publication-status__notice" aria-live="polite">
        <div>
          <p className="state-publication-status__notice-label">Estado dos dados</p>
          <h2>{selectedMunicipality ? selectedMunicipality.name : 'Selecione um município'}</h2>
          {selectedMunicipality ? (
            <p>
              Município IBGE <strong>{selectedMunicipality.ibgeCode}</strong> selecionado. O cadastro
              está pronto; nenhum resultado analítico foi publicado para este território.
            </p>
          ) : (
            <p>Use o seletor no topo para consultar o cadastro municipal de Alagoas.</p>
          )}
        </div>
        <p className="state-publication-status__message">
          {ACTIVE_PUBLICATION_CONFIG.analyticsMessage}
        </p>
      </section>
    </div>
  )
}
