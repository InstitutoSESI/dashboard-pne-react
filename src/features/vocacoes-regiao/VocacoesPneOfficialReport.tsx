import { BookOpenCheck, MapPinned, Printer } from 'lucide-react'
import type { MouseEvent } from 'react'
import { PnePageHeader } from '../../components/PnePageHeader'
import { VocacoesPneManagerReview } from '../vocacoes-pne-internal/components/VocacoesPneManagerReview'
import type { VocacoesPneLoadedBundle } from '../vocacoes-pne-internal/vocacoesPneUiV2Types'
import { VOCACOES_PNE_OFFICIAL_PROMOTION } from './vocacoesPneOfficialPromotion'
import type { VocacoesDocument } from './vocacoesRegiaoTypes'
import '../../styles/vocacoes-pne-internal.css'
import '../../styles/vocacoes-pne-official.css'

function scrollToSection(event: MouseEvent<HTMLAnchorElement>, id: string) {
  event.preventDefault()
  const target = document.getElementById(id)
  if (!(target instanceof HTMLElement)) return
  const reducedMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
  target.scrollIntoView({ behavior: reducedMotion ? 'auto' : 'smooth', block: 'start' })
  if (target.tabIndex < 0) target.tabIndex = -1
  target.focus({ preventScroll: true })
}

export function VocacoesPneOfficialReport({
  bundle,
  legacyDocument,
  municipalityId,
  advancedScopeNotice = false,
}: {
  bundle: VocacoesPneLoadedBundle
  legacyDocument: VocacoesDocument
  municipalityId: string | null
  advancedScopeNotice?: boolean
}) {
  const municipality = municipalityId === null
    ? null
    : bundle.core.municipalities.find((item) => item.ibgeCode === municipalityId) ?? null
  if (municipalityId !== null && municipality === null) {
    throw new TypeError('Leitura integrada oficial: município não pertence ao Vale do Sinos.')
  }

  const entityName = municipality?.name ?? bundle.core.region.name
  const entityContext = municipality
    ? `${bundle.core.region.name} · leitura municipal e regional`
    : `${bundle.core.region.municipalityCount} municípios · ${bundle.core.region.stateCode}`

  return (
    <div
      className="page-stack vocacoes-pne-official-page"
      data-contract-version={VOCACOES_PNE_OFFICIAL_PROMOTION.contractVersion}
      data-publication="official"
      data-region={legacyDocument.region.slug}
    >
      <PnePageHeader
        actions={null}
        asideContent={null}
        asideLabel={null}
        context={entityContext}
        description="Uma leitura integrada para compreender como educação, demografia, condições sociais e transformações do trabalho se encontram no território — e o que isso coloca na agenda dos próximos anos."
        eyebrow="Vocações da Região · leitura integrada"
        title={`${entityName}: educação e território`}
        variant="editorial"
      />

      <main className="vocacoes-pne-internal-page vocacoes-pne-official-content">
        {advancedScopeNotice ? (
          <aside className="vpo-advanced-scope-note" data-advanced-scope-note role="note">
            <b>Escopo da leitura avançada.</b>
            <span>
              Nesta etapa, o novo dossiê analítico está disponível para o Vale do Sinos e Nova Santa Rita.
              {` ${entityName} permanece na leitura oficial anterior até possuir um dossiê municipal validado.`}
            </span>
          </aside>
        ) : null}

        <section className="vpo-overview" aria-labelledby="vpo-overview-title">
          <div className="vpo-overview__copy">
            <p className="vpi-eyebrow">Leitura orientada a decisões</p>
            <h2 id="vpo-overview-title">Os dados ganham sentido quando cada conexão termina em uma pergunta de planejamento.</h2>
            <p>O percurso começa pelo diagnóstico educacional, faz o caminho inverso a partir das mudanças do território e fecha com conexões complementares. Cada leitura mostra os números, o mecanismo plausível e o limite da evidência.</p>
            <div className="vpo-overview__facts" aria-label="Escopo da página oficial">
              <span><b>4</b> leituras educação → território</span>
              <span><b>3</b> agendas território → educação</span>
              <span><b>8</b> relações avaliadas</span>
            </div>
          </div>
          <aside className="vpo-overview__scope">
            <MapPinned aria-hidden="true" />
            <div>
              <span>Recorte ativo</span>
              <strong>{entityName}</strong>
              <small>{bundle.core.region.name} sempre aparece como contexto</small>
            </div>
            <button type="button" onClick={() => window.print()}>
              <Printer aria-hidden="true" /> Imprimir leitura
            </button>
          </aside>
        </section>

        <nav className="vpo-section-nav" aria-label="Seções da leitura integrada">
          <a href="#vpm-priorities-title" onClick={(event) => scrollToSection(event, 'vpm-priorities-title')}>Síntese</a>
          <a href="#education-to-territory" onClick={(event) => scrollToSection(event, 'education-to-territory')}>Educação → território</a>
          <a href="#territory-to-education" onClick={(event) => scrollToSection(event, 'territory-to-education')}>Território → educação</a>
          <a href="#conexoes-complementares" onClick={(event) => scrollToSection(event, 'conexoes-complementares')}>Outras conexões</a>
        </nav>

        <VocacoesPneManagerReview
          bundle={bundle}
          municipalityEntityId={municipality?.ibgeCode ?? null}
          municipalityName={municipality?.name ?? null}
          surface="official"
        />

        <footer className="vpo-footer">
          <BookOpenCheck aria-hidden="true" />
          <div>
            <b>Fontes oficiais e medidas preservadas.</b>
            <p>Os cartões usam os pacotes analíticos validados dos Censos Escolar e Demográfico, Indicadores Educacionais, RAIS, Novo Caged, EPT e contratos territoriais do Vale do Sinos. Moradores, matrículas, vínculos e eventos permanecem lentes distintas.</p>
          </div>
        </footer>
      </main>
    </div>
  )
}
