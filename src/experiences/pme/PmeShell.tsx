import { useRef, useState, type ReactNode } from 'react'
import { BookOpen, ChartNoAxesCombined, ClipboardList, FileDown, House, Info, Landmark, LayoutDashboard, Map, Menu, X } from 'lucide-react'
import { MunicipalitySelector } from '../../components/MunicipalitySelector'
import { InstitutionalTopBarSignature } from '../../components/InstitutionalTopBarSignature'
import { PLATFORM_LABEL } from '../../config/stateConfig'
import { PME_MUNICIPALITIES } from './pmeRegistry'
import { PME_PAGES, pmeLink, type PmePage, type PmeRoute } from './pmeRoutes'

const navigation = [
  ['apresentacao', House], ['inicio', LayoutDashboard], ['objetivos', Map], ['agenda', ClipboardList],
  ['evidencias', ChartNoAxesCombined], ['financiamento', Landmark], ['relatorios', FileDown],
] as const

export function PmeShell({ route, children }: { route: PmeRoute; children: ReactNode }) {
  const [menuOpen, setMenuOpen] = useState(false)
  const menuButton = useRef<HTMLButtonElement>(null)
  const activePage: PmePage = route.page === 'objetivo' ? 'objetivos'
    : route.page === 'relatorio-tecnico' ? 'relatorios' : route.page
  return (
    <div className="pme-app" data-page={activePage} onKeyDown={(event) => {
      if (event.key === 'Escape' && menuOpen) { setMenuOpen(false); menuButton.current?.focus() }
    }}>
      <a className="pme-skip-link" href="#pme-main" onClick={(event) => {
        event.preventDefault()
        document.getElementById('pme-main')?.focus()
      }}>Ir para o conteúdo</a>
      <aside className={'pme-sidebar' + (menuOpen ? ' is-open' : '')}>
        <a className="pme-brand" href={pmeLink(route, 'apresentacao', { objectiveId: null, themeId: null, evidenceFilter: 'todas' })} onClick={() => setMenuOpen(false)}>
          <BookOpen aria-hidden="true" size={25} strokeWidth={1.5} />
          <span><strong>{PLATFORM_LABEL}</strong><span>Evidências para o PME</span></span>
        </a>
        <nav id="pme-navigation" className="pme-navigation" aria-label="Percurso de leitura PME">
          {navigation.map(([page, Icon]) => (
            <a key={page} href={pmeLink(route, page)} aria-current={activePage === page ? 'page' : undefined} onClick={() => setMenuOpen(false)}>
              <Icon aria-hidden="true" size={20} strokeWidth={1.6} />{PME_PAGES[page]}
            </a>
          ))}
          <a className="pme-navigation-source" href={pmeLink(route, 'transparencia')} aria-current={activePage === 'transparencia' ? 'page' : undefined} onClick={() => setMenuOpen(false)}><Info aria-hidden="true" size={20} />Fontes e critérios</a>
        </nav>
        <div className="pme-navigation-note"><p>Observatório da Educação<br />SESI-RS</p><span>Rio Grande do Sul</span></div>
      </aside>
      <div className="pme-workspace">
        <header className="pme-topbar">
          <button ref={menuButton} type="button" className="pme-menu-toggle" aria-label={menuOpen ? 'Fechar menu' : 'Abrir menu'} aria-expanded={menuOpen} aria-controls="pme-navigation" onClick={() => setMenuOpen((open) => !open)}>{menuOpen ? <X aria-hidden="true" size={23} /> : <Menu aria-hidden="true" size={23} />}</button>
          <MunicipalitySelector
            municipalities={PME_MUNICIPALITIES}
            selectedMunicipalityId={route.municipalityId}
            onChange={(municipalityId) => { window.location.hash = pmeLink(route, route.page === 'apresentacao' && municipalityId ? 'inicio' : route.page, { municipalityId }) }}
            placeholder="Busque seu município no RS"
          />
          <a className="pme-topbar-help" href={pmeLink(route, 'transparencia')}><Info aria-hidden="true" size={18} /><span>Sobre os dados</span></a>
          <InstitutionalTopBarSignature />
        </header>
        <main id="pme-main" className="pme-main" tabIndex={-1}>{children}</main>
        <footer className="pme-footer"><p>Painel SESI de Educação <span>Rio Grande do Sul</span></p><a href={pmeLink(route, 'transparencia')}>Fontes e critérios de leitura</a></footer>
      </div>
    </div>
  )
}
