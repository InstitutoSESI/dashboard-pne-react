import { useEffect, useRef } from 'react'
import { useMunicipality } from '../context/MunicipalityContext'
import { scrollPageToTop } from '../utils/navigationScroll'
import { ContextBar } from './ContextBar'
import { Header } from './Header'

// Assinatura de cor por area: verde = Home/PNE (plano/marca), teal = Educacao,
// navy = Financiamento, slate = Diagnostico/Relatorio (analise). Dirige
// --page-signature no content-area; ver src/styles/design-tokens.css.
function pageSignatureFor(activePage) {
  if (typeof activePage !== 'string') return 'plan'
  if (activePage === 'educacao') return 'teal'
  if (activePage === 'diagnostico' || activePage === 'relatorio-tecnico-municipal') return 'slate'
  if (activePage.startsWith('financeiros')) return 'navy'
  return 'plan'
}

export function Layout({
  activePage,
  activeEducationSection,
  children,
  municipalities,
  onNavigate,
}) {
  const {
    selectedMunicipalityId,
    setSelectedMunicipalityId,
  } = useMunicipality()
  const contentRef = useRef(null)

  useEffect(() => {
    scrollPageToTop()
    let observer = null

    function focusPageTitle() {
      const pageTitle = contentRef.current?.querySelector('h1')
      if (!(pageTitle instanceof HTMLElement)) return false
      pageTitle.tabIndex = -1
      pageTitle.classList.add('programmatic-focus-target')
      pageTitle.focus({ preventScroll: true })
      return true
    }

    const frame = window.requestAnimationFrame(() => {
      if (focusPageTitle()) return
      observer = new MutationObserver(() => {
        if (focusPageTitle()) observer?.disconnect()
      })
      if (contentRef.current) {
        observer.observe(contentRef.current, { childList: true, subtree: true })
      }
    })

    return () => {
      window.cancelAnimationFrame(frame)
      observer?.disconnect()
    }
  }, [activeEducationSection, activePage])

  return (
    <div className="dashboard-shell">
      <Header
        activePage={activePage}
        activeEducationSection={activeEducationSection}
        onNavigate={onNavigate}
      />

      <div className="dashboard-main">
        <ContextBar
          activePage={activePage}
          municipalities={municipalities}
          selectedMunicipalityId={selectedMunicipalityId}
          onMunicipalityChange={setSelectedMunicipalityId}
        />
        <main className="content-area" data-page-signature={pageSignatureFor(activePage)} ref={contentRef}>{children}</main>
      </div>
    </div>
  )
}
