import { useEffect, useRef, useState } from 'react'
import { Compass, FileText, GraduationCap, House, Landmark, Menu, Target, X } from 'lucide-react'
import {
  NAV_GROUPS,
  NAV_ROOT_ITEMS,
  getOwnerGroupId,
} from '../app/navigationRegistry'
import { resolvePageProduct } from '../config/analyticsProducts'
import { ANALYTICS_AVAILABLE, isProductEnabled } from '../config/publicationConfig'
import { ACTIVE_STATE_CONFIG, PLATFORM_LABEL } from '../config/stateConfig'
import { useMunicipality } from '../context/MunicipalityContext'
import { EDUCATION_SECTION_CATALOG } from '../data/educationIndicatorCatalog'
import { FINANCIAL_NAV_ITEMS, FINANCIAL_PAGE_KEYS } from '../data/financialModules'
import { isForesightPublished, useForesightPublication } from '../hooks/useForesightEducacao'
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
    page: 'educacao',
    icon: isEducationDomain(section.key)
      ? () => <EducationDomainIcon domain={section.key} size="sm" />
      : isNavGlyphName(section.key)
        ? () => <NavGlyphIcon name={section.key} size="sm" />
        : null,
  }))

const navGlyph = (name) => () => <NavGlyphIcon name={name} size="sm" />

const GROUP_ICONS = { Target, GraduationCap, Landmark, FileText, Compass }

/*
 * Os grupos que já tinham catálogo próprio continuam se alimentando dele: o
 * registro de navegação declara a fonte, o cabeçalho a resolve. Assim nenhum
 * rótulo de seção educacional ou de módulo financeiro é duplicado.
 */
const DYNAMIC_GROUP_ITEMS = {
  'education-sections': EDUCATION_NAV_ITEMS,
  'financial-modules': FINANCIAL_NAV_ITEMS.map((item) => ({
    key: item.pageKey,
    label: item.label,
    target: item.pageKey,
    page: item.pageKey,
    icon: navGlyph(item.pageKey),
  })),
}

const toRenderableItem = (item) => ({
  key: item.key,
  label: item.label,
  target: item.target,
  page: item.page,
  condition: item.condition,
  icon: item.glyph ? navGlyph(item.glyph) : null,
})

/*
 * Visibilidade é decidida item a item, pelo produto da página que ele abre — um
 * grupo pode reunir páginas de produtos diferentes, e numa publicação parcial
 * só some o que não foi publicado. As páginas ocultas continuam alcançáveis por
 * URL e caem no aviso de indisponibilidade. Um grupo sem item algum não é
 * renderizado.
 */
function isItemVisible(item) {
  const product = resolvePageProduct(item.page)
  return product === null || isProductEnabled(product)
}

const NAV_BLOCKS = NAV_GROUPS
  .map((group) => ({
    icon: GROUP_ICONS[group.icon],
    id: group.id,
    label: group.label,
    items: (group.dynamicItems
      ? DYNAMIC_GROUP_ITEMS[group.dynamicItems]
      : group.items.map(toRenderableItem)
    ).filter(isItemVisible),
  }))
  .filter((block) => block.items.length > 0)

const ROOT_NAV_ITEMS = NAV_ROOT_ITEMS.map(toRenderableItem).filter(isItemVisible)

/*
 * Os Cenários da educação existem para os municípios que o manifesto público
 * declara publicados. A entrada aparece só nesse caso — sem item desabilitado,
 * sem aviso de indisponibilidade e sem código IBGE escrito na interface. O
 * registro marca o item como condicional; o gate é aplicado aqui.
 */
function withForesightItem(block, isVisible) {
  if (isVisible || !block.items.some((item) => item.condition === 'foresight')) return block
  return { ...block, items: block.items.filter((item) => item.condition !== 'foresight') }
}

const PANEL_LABEL = PLATFORM_LABEL
const PANEL_FULL_LABEL = `${PANEL_LABEL} · Inteligência Analítica Municipal`

export function Header({ activeEducationSection, activePage, onNavigate }) {
  const [isDrawerOpen, setIsDrawerOpen] = useState(false)
  const [openGroup, setOpenGroup] = useState(() => getOwnerGroup(activePage))
  const [isMobile, setIsMobile] = useState(false)
  const closeButtonRef = useRef(null)
  const drawerRef = useRef(null)
  const menuButtonRef = useRef(null)
  const restoreFocusRef = useRef(null)
  const { selectedMunicipalityId } = useMunicipality()
  const foresightPublication = useForesightPublication()
  const foresightVisible = isForesightPublished(foresightPublication, selectedMunicipalityId)

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
        <div className="brand-lockup" aria-label={PANEL_FULL_LABEL}>
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
              {NAV_BLOCKS.map((block) => withForesightItem(block, foresightVisible)).map((item) => (
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

              {ROOT_NAV_ITEMS.map((item) => {
                const ItemIcon = item.icon ?? FileText

                return (
                  <a
                    aria-current={activePage === item.page ? 'page' : undefined}
                    className={activePage === item.page ? 'nav-item is-active' : 'nav-item'}
                    href={`#${item.target}`}
                    key={item.key}
                    onClick={(event) => {
                      event.preventDefault()
                      navigate(item.target)
                    }}
                  >
                    <span className="nav-item__icon" aria-hidden="true"><ItemIcon /></span>
                    <span className="nav-item__label">{item.label}</span>
                  </a>
                )
              })}
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
        <div className="sidebar-mobile-bar__brand" aria-label={PANEL_FULL_LABEL}>
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
  return getOwnerGroupId(activePage)
}

function getActiveItemKey(groupId, activePage, activeEducationSection) {
  if (groupId === 'educacao') return activePage === 'educacao' ? activeEducationSection : null
  if (groupId === 'financeiros' && activePage === 'financeiros') return FINANCIAL_PAGE_KEYS.overview
  return activePage
}
