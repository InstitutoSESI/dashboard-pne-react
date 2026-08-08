import { useEffect, useRef, useState } from 'react'
import { FileText, GraduationCap, House, Landmark, Menu, Target, X } from 'lucide-react'
import { ANALYTICS_AVAILABLE } from '../config/publicationConfig'
import { ACTIVE_STATE_CONFIG } from '../config/stateConfig'
import { EDUCATION_SECTION_CATALOG } from '../data/educationIndicatorCatalog'
import { FINANCIAL_NAV_ITEMS, FINANCIAL_PAGE_KEYS } from '../data/financialModules'
import { EducationDomainIcon, isEducationDomain } from './icons/EducationDomainIcon'
import { NavGlyphIcon, isNavGlyphName } from './icons/NavGlyphIcon'
import { SidebarAccordionGroup } from './SidebarAccordionGroup'
import { SidebarInstitutionalSignature } from './SidebarInstitutionalSignature'

const EDUCATION_NAV_ITEMS = EDUCATION_SECTION_CATALOG
  .filter((section) => section.key !== 'relatorio-tecnico-municipal')
  .map((section) => ({
    key: section.key,
    label: section.label,
    target: `educacao?secao=${section.key}`,
    icon: isEducationDomain(section.key)
      ? () => <EducationDomainIcon domain={section.key} size="sm" />
      : isNavGlyphName(section.key)
        ? () => <NavGlyphIcon name={section.key} size="sm" />
        : null,
  }))

const navGlyph = (name) => () => <NavGlyphIcon name={name} size="sm" />

const NAV_BLOCKS = [
  {
    icon: Target,
    id: 'pne',
    label: 'PNE',
    items: [
      { key: 'pne-overview', label: 'O que é o PNE', target: 'pne-overview', icon: navGlyph('pne-overview') },
      { key: 'pne-legal-goals', label: 'Metas legais', target: 'pne-legal-goals', icon: navGlyph('pne-legal-goals') },
      { key: 'pne2014', label: 'PNE 2014–2024', target: 'pne2014', icon: navGlyph('pne2014') },
      { key: 'pne2026', label: 'PNE 2026–2036', target: 'pne2026', icon: navGlyph('pne2026') },
      { key: 'diagnostico', label: 'Diagnóstico municipal', target: 'diagnostico', icon: navGlyph('diagnostico') },
      { key: 'matriz-prioridades', label: 'Matriz de Prioridades', target: 'matriz-prioridades', icon: navGlyph('matriz-prioridades') },
    ],
  },
  {
    icon: GraduationCap,
    id: 'educacao',
    label: 'Indicadores educacionais',
    items: EDUCATION_NAV_ITEMS,
  },
  {
    icon: Landmark,
    id: 'financeiros',
    label: 'Financiamento',
    items: FINANCIAL_NAV_ITEMS.map((item) => ({
      key: item.pageKey,
      label: item.label,
      target: item.pageKey,
      icon: navGlyph(item.pageKey),
    })),
  },
]

const PNE_PAGES = new Set(['pne-overview', 'pne2014', 'pne2026', 'pne-legal-goals', 'diagnostico', 'matriz-prioridades'])
const FINANCIAL_PAGES = new Set(Object.values(FINANCIAL_PAGE_KEYS))
const PANEL_LABEL = `Painel SESI-${ACTIVE_STATE_CONFIG.stateCode}`

export function Header({ activeEducationSection, activePage, onNavigate }) {
  const [isDrawerOpen, setIsDrawerOpen] = useState(false)
  const [openGroup, setOpenGroup] = useState(() => getOwnerGroup(activePage))
  const [isMobile, setIsMobile] = useState(false)
  const closeButtonRef = useRef(null)
  const drawerRef = useRef(null)
  const menuButtonRef = useRef(null)
  const restoreFocusRef = useRef(null)

  const ownerGroup = getOwnerGroup(activePage)

  useEffect(() => {
    setOpenGroup(ownerGroup)
  }, [ownerGroup])

  useEffect(() => {
    const mediaQuery = window.matchMedia('(max-width: 1079px)')
    const updateViewport = () => setIsMobile(mediaQuery.matches)
    updateViewport()
    mediaQuery.addEventListener?.('change', updateViewport)
    return () => mediaQuery.removeEventListener?.('change', updateViewport)
  }, [])

  useEffect(() => {
    if (!isDrawerOpen) return undefined

    restoreFocusRef.current = document.activeElement instanceof HTMLElement
      ? document.activeElement
      : null
    const frame = window.requestAnimationFrame(() => closeButtonRef.current?.focus())
    const previousOverflow = document.body.style.overflow
    const drawerElement = drawerRef.current

    function handleDrawerKeyDown(event) {
      if (event.key === 'Escape') {
        event.preventDefault()
        closeDrawer(true)
        return
      }

      if (event.key !== 'Tab') return
      const focusable = drawerRef.current?.querySelectorAll(
        'button:not([disabled]), a[href], input:not([disabled]), select:not([disabled]), textarea:not([disabled])',
      )
      if (!focusable?.length) return

      const first = focusable[0]
      const last = focusable[focusable.length - 1]
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault()
        first.focus()
      }
    }

    document.body.style.overflow = 'hidden'
    drawerElement?.addEventListener('keydown', handleDrawerKeyDown)

    return () => {
      window.cancelAnimationFrame(frame)
      document.body.style.overflow = previousOverflow
      drawerElement?.removeEventListener('keydown', handleDrawerKeyDown)
    }
  }, [isDrawerOpen])

  function closeDrawer(restoreFocus = false) {
    setIsDrawerOpen(false)
    if (restoreFocus) {
      window.requestAnimationFrame(() => {
        ;(restoreFocusRef.current ?? menuButtonRef.current)?.focus()
      })
    }
  }

  function navigate(target) {
    onNavigate(target)
    if (isDrawerOpen) closeDrawer(false)
  }

  function openDrawer() {
    restoreFocusRef.current = document.activeElement instanceof HTMLElement
      ? document.activeElement
      : null
    setIsDrawerOpen(true)
  }

  return (
    <>
      <aside
        ref={drawerRef}
        aria-hidden={isMobile && !isDrawerOpen ? 'true' : undefined}
        className={`app-header${isDrawerOpen ? ' is-drawer-open' : ''}`}
        inert={isMobile && !isDrawerOpen ? true : undefined}
        aria-label={`Navegação principal do ${PANEL_LABEL}`}
      >
        <div className="brand-lockup" aria-label={`${PANEL_LABEL} de Inteligência Analítica Municipal`}>
          <div className="brand-copy">
            <span className="brand-eyebrow">{PANEL_LABEL}</span>
            <strong className="brand-title">Inteligência Municipal</strong>
          </div>
          <button
            ref={closeButtonRef}
            aria-label="Fechar menu"
            className="sidebar-close-button"
            type="button"
            onClick={() => closeDrawer(true)}
          >
            <X aria-hidden="true" />
          </button>
        </div>

        <nav className="top-nav" aria-label="Navegação global">
          <span className="sidebar-nav-label">NAVEGAÇÃO</span>

          <a
            aria-current={activePage === 'home' ? 'page' : undefined}
            className={activePage === 'home' ? 'nav-item nav-item--home is-active' : 'nav-item nav-item--home'}
            href="#home"
            onClick={(event) => {
              event.preventDefault()
              navigate('home')
            }}
          >
            <span className="nav-item__icon" aria-hidden="true"><House /></span>
            <span className="nav-item__label">Home</span>
          </a>

          {ANALYTICS_AVAILABLE ? (
            <>
              {NAV_BLOCKS.map((item) => (
                <SidebarAccordionGroup
                  activeItemKey={getActiveItemKey(item.id, activePage, activeEducationSection)}
                  icon={item.icon}
                  id={item.id}
                  isOpen={openGroup === item.id}
                  items={item.items}
                  key={item.id}
                  label={item.label}
                  onNavigate={navigate}
                  onToggle={(groupId) => setOpenGroup((current) => current === groupId ? null : groupId)}
                />
              ))}

              <a
                aria-current={activePage === 'relatorio-tecnico-municipal' ? 'page' : undefined}
                className={activePage === 'relatorio-tecnico-municipal' ? 'nav-item is-active' : 'nav-item'}
                href="#relatorio-tecnico-municipal"
                onClick={(event) => {
                  event.preventDefault()
                  navigate('relatorio-tecnico-municipal')
                }}
              >
                <span className="nav-item__icon" aria-hidden="true"><FileText /></span>
                <span className="nav-item__label">Relatório Técnico Municipal</span>
              </a>
            </>
          ) : (
            <div className="sidebar-publication-note" role="status">
              <strong>Cadastro municipal ativo</strong>
              <span>Indicadores de {ACTIVE_STATE_CONFIG.stateName} em preparação.</span>
            </div>
          )}
        </nav>

        <SidebarInstitutionalSignature compact />
      </aside>

      <div className="sidebar-mobile-bar">
        <button
          ref={menuButtonRef}
          aria-expanded={isDrawerOpen}
          aria-controls="sidebar-pne-items sidebar-educacao-items sidebar-financeiros-items"
          className="sidebar-menu-button"
          type="button"
          onClick={openDrawer}
        >
          <Menu aria-hidden="true" />
          <span>Menu</span>
        </button>
        <div className="sidebar-mobile-bar__brand" aria-label={`${PANEL_LABEL} de Inteligência Analítica Municipal`}>
          <span>{PANEL_LABEL}</span>
          <strong>Inteligência Municipal</strong>
        </div>
      </div>

      {isDrawerOpen ? (
        <button
          aria-label="Fechar menu"
          className="sidebar-backdrop"
          type="button"
          onClick={() => closeDrawer(true)}
        />
      ) : null}
    </>
  )
}

function getOwnerGroup(activePage) {
  if (PNE_PAGES.has(activePage)) return 'pne'
  if (activePage === 'educacao') return 'educacao'
  if (activePage === 'financeiros' || FINANCIAL_PAGES.has(activePage)) return 'financeiros'
  return null
}

function getActiveItemKey(groupId, activePage, activeEducationSection) {
  if (groupId === 'educacao') return activePage === 'educacao' ? activeEducationSection : null
  if (groupId === 'financeiros' && activePage === 'financeiros') return FINANCIAL_PAGE_KEYS.overview
  return activePage
}
