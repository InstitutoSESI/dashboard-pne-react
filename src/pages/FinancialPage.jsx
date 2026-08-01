import { useEffect, useState } from 'react'
import { ErrorState } from '../components/ErrorState'
import { FinancialSectionHeader } from '../components/FinancialIndicatorPrimitives'
import { FinancialCompactModuleSelector } from '../components/FinancialCompactModuleSelector'
import { NavigationEntryCard } from '../components/NavigationEntryCard'
import { FundebPanel } from '../components/FundebPanel'
import { LoadingState } from '../components/LoadingState'
import { PnatePanel } from '../components/PnatePanel'
import { SiopeIndicatorsPanel } from '../components/SiopeIndicatorsPanel'
import { VaarPanel } from '../components/VaarPanel'
import { EducationCompactHeader } from '../features/education/components/EducationCompactHeader'
import { loadEducationMunicipio } from '../data/educationData'
import {
  FINANCIAL_MODULES,
  FINANCIAL_OVERVIEW_COPY,
  FINANCIAL_PAGE_COPY,
  FINANCIAL_PAGE_KEYS,
  getFinancialModuleByPageKey,
} from '../data/financialModules'
import { useAsyncData } from '../utils/useAsyncData'
import { getHashContext, mergeHashContext } from '../utils/hashNavigation'
import { municipalFinanceLoader } from '../data/municipalFinance'
import '../styles/education-pages.css'

export function FinancialPage({
  municipalityId,
  municipioData,
  municipioError,
  municipioLoading,
  pageKey,
  selectedMunicipio,
}) {
  const module = getFinancialModuleByPageKey(pageKey)
  const isOverview = pageKey === FINANCIAL_PAGE_KEYS.overview
  const usesEducationCatalogLayout = ['siope', 'fundeb', 'pnate'].includes(module?.panel)
  const [detailKey, setDetailKey] = useState(() => getHashContext().params.get('detalhe') ?? '')

  const selectedId = municipalityId
  const educationMunicipioState = useAsyncData(
    () => (module && selectedId ? loadEducationMunicipio(selectedId) : null),
    [module?.pageKey, selectedId],
  )

  useEffect(() => {
    if (!module) return

    const { params, route } = getHashContext()
    const nextDetailKey = params.get('detalhe') ?? ''
    setDetailKey(nextDetailKey)

    if (route !== module.pageKey || params.has('modulo') || params.has('module')) {
      mergeHashContext(module.pageKey, { detalhe: nextDetailKey, modulo: null, module: null })
    }
  }, [module])

  if (isOverview) return <FinancialOverviewPage />
  if (!module) return null

  return (
    <div className={`page-stack financial-page financial-module-page${usesEducationCatalogLayout ? ' financial-page--education-catalog' : ''}${detailKey ? ' financial-page--detail' : ''}`}>
      {!detailKey ? (
        <FinancialPageHeader module={module} />
      ) : null}
      {!detailKey && !usesEducationCatalogLayout ? <FinancialCompactModuleSelector activePageKey={pageKey} /> : null}

      {!selectedId ? (
        <FinancialModuleEmpty module={module} />
      ) : municipioLoading ? (
        <LoadingState message={FINANCIAL_PAGE_COPY.module.municipalityLoading(selectedMunicipio)} />
      ) : municipioError ? (
        <ErrorState title={FINANCIAL_PAGE_COPY.module.municipalityErrorTitle} message={municipioError} />
      ) : (
        <FinancialModulePanel
          detailKey={detailKey}
          educationMunicipioState={educationMunicipioState}
          module={module}
          municipioData={municipioData}
          onDetailChange={(nextDetailKey) => {
            setDetailKey(nextDetailKey)
            mergeHashContext(module.pageKey, { detalhe: nextDetailKey, modulo: null, module: null })
          }}
          selectedId={selectedId}
          selectedMunicipio={selectedMunicipio}
        />
      )}
    </div>
  )
}

function getFinancialModuleTitle(module) {
  if (module.panel === 'pnate') return 'PNATE'
  if (module.panel === 'fundeb') return 'Fundeb: recursos, aplicação e saldos'
  return module.title
}

function getFinancialModuleDescription(module) {
  if (module.panel === 'pnate') {
    return 'Valores do programa de transporte escolar rural e estudantes considerados no cálculo.'
  }
  if (module.panel === 'fundeb') {
    return 'Veja os recursos declarados, como foram utilizados e a disponibilidade financeira do Fundeb.'
  }
  if (module.panel === 'vaar') {
    return 'Condições consideradas e resultados dos componentes no exercício publicado.'
  }
  return module.description
}

function getFinancialOverviewHref() {
  const params = new URLSearchParams(getHashContext().params)
  params.delete('detalhe')
  params.delete('modulo')
  params.delete('module')
  const query = params.toString()
  return `#${FINANCIAL_PAGE_KEYS.overview}${query ? `?${query}` : ''}`
}

function FinancialOverviewPage() {
  const { hero, panorama, resources, dashboard, concepts, sources } = FINANCIAL_OVERVIEW_COPY

  return (
    <div className="page-stack financial-page financial-overview-page pne-overview-page">
      <section className="page-card pne-overview-hero financial-overview-hero">
        <div className="pne-overview-hero__copy">
          <span className="eyebrow">{FINANCIAL_OVERVIEW_COPY.eyebrow}</span>
          <h1>{hero.title}</h1>
          <p>{hero.description}</p>
        </div>
      </section>

      <section className="page-card financial-overview-panorama" aria-labelledby="financial-panorama-title">
        <div className="financial-overview-panorama__icon" aria-hidden="true"><PanoramaIcon /></div>
        <div className="financial-overview-panorama__copy">
          <span className="eyebrow">{panorama.eyebrow}</span>
          <h2 id="financial-panorama-title">{panorama.title}</h2>
          <p>{panorama.description}</p>
        </div>
        <a className="financial-overview-panorama__action" href={`#${FINANCIAL_PAGE_KEYS.panorama}`}>
          <span>{panorama.actionLabel}</span>
          <span aria-hidden="true">→</span>
        </a>
      </section>

      <FinancialCompactModuleSelector activePageKey={FINANCIAL_PAGE_KEYS.overview} />

      <section className="pne-overview-section pne-overview-entries financial-editorial-section financial-module-directory" aria-labelledby="financial-dashboard-title">
        <FinancialSectionHeader eyebrow={dashboard.eyebrow} title={dashboard.title} description={dashboard.description} titleId="financial-dashboard-title" />
        <div className="pne-entry-grid financial-module-entry-grid">
          {FINANCIAL_MODULES.map((module) => (
            <NavigationEntryCard
              ariaLabel={`Abrir ${module.title}`}
              bodyText={module.overview.description}
              footerText={dashboard.actionLabel}
              href={`#${module.pageKey}`}
              icon={FINANCIAL_OVERVIEW_MODULE_ICONS[module.key]}
              key={module.key}
              title={module.overview.title}
            />
          ))}
        </div>
      </section>

      <section className="pne-overview-section financial-editorial-section financial-mechanisms" aria-labelledby="financial-resources-title">
        <FinancialSectionHeader eyebrow={resources.eyebrow} title={resources.title} titleId="financial-resources-title" />
        <div className="pne-concept-grid financial-mechanisms__grid">
          {resources.cards.map((card) => (
            <article className="pne-concept-card financial-mechanisms__card" key={card.title}>
              <h3>{card.title}</h3>
              <p>{card.body}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="financial-overview-concepts" aria-labelledby="financial-concepts-title">
        <header className="financial-overview-concepts__header">
          <div>
            <span className="eyebrow">{concepts.eyebrow}</span>
            <h2 id="financial-concepts-title">{concepts.title}</h2>
          </div>
        </header>
        <div className="financial-overview-concepts__body">
          <p>{concepts.description}</p>
          <div className="financial-overview-concepts__grid">
            {concepts.items.map((item) => (
              <article className="financial-overview-concept" key={item.title}>
                <h3>{item.title}</h3>
                <p>{item.summary}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <footer className="financial-overview-source financial-sources-footer" aria-labelledby="financial-overview-sources-title">
        <div className="financial-sources-footer__heading">
          <span className="eyebrow">Referências oficiais</span>
          <h2 id="financial-overview-sources-title">{sources.title}</h2>
          {sources.description ? <span>{sources.description}</span> : null}
        </div>
        <ul>
          {sources.references.map((reference) => (
            <li key={reference.label}>
              <a href={reference.url} rel="noreferrer" target="_blank">{reference.label}</a>
            </li>
          ))}
        </ul>
      </footer>
    </div>
  )
}

const FINANCIAL_OVERVIEW_MODULE_ICONS = Object.freeze({
  siope: ApplicationIcon,
  fundeb: FundebIcon,
  vaar: VaarIcon,
  pnate: PnateIcon,
})

function PanoramaIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 19h16" />
      <path d="M6 16v-5m4 5V7m4 9v-3m4 3V4" />
      <path d="m5 8 4-3 4 4 5-5" />
    </svg>
  )
}

function ApplicationIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      <path d="M5 8.5h14v10H5z" />
      <path d="M8 8.5V6.75A1.75 1.75 0 0 1 9.75 5h4.5A1.75 1.75 0 0 1 16 6.75V8.5" />
      <path d="M9 13h6m-3-3v6" />
    </svg>
  )
}

function FundebIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      <path d="M5 9h11l-2.5-2.5M19 15H8l2.5 2.5" />
      <path d="M18 6.5A8 8 0 0 1 19 15M6 17.5A8 8 0 0 1 5 9" />
    </svg>
  )
}

function VaarIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 3.5 18 6v5.25c0 4.05-2.45 7.65-6 9.25-3.55-1.6-6-5.2-6-9.25V6z" />
      <path d="m9 11.75 2 2 4-4" />
    </svg>
  )
}

function PnateIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      <path d="M5 5.5h14v11H5z" />
      <path d="M5 10h14M8 8h2m2 0h2" />
      <path d="M8 20a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3Zm8 0a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3Z" />
    </svg>
  )
}

function FinancialPageHeader({ module }) {
  return (
    <EducationCompactHeader
      backLink={{
        href: getFinancialOverviewHref(),
        label: 'Voltar à visão geral de financiamento',
      }}
      className={`financial-page-header financial-page-header--${module.panel}`}
      description={getFinancialModuleDescription(module)}
      eyebrow="Financiamento da educação"
      title={getFinancialModuleTitle(module)}
    />
  )
}

function FinancialModuleEmpty({ module }) {
  return (
    <section className="empty-state financial-module-empty">
      <div className="empty-state__icon" aria-hidden="true"><FinanceIcon /></div>
      <h2>{FINANCIAL_PAGE_COPY.module.emptyTitle} {module.title}</h2>
      <p>{FINANCIAL_PAGE_COPY.module.emptyDescription}</p>
    </section>
  )
}

function FinancialModulePanel({
  detailKey,
  educationMunicipioState,
  module,
  municipioData,
  onDetailChange,
  selectedId,
  selectedMunicipio,
}) {
  const municipalFinanceState = useAsyncData(
    () => (module.panel === 'vaar' && selectedId ? municipalFinanceLoader.load(String(selectedId)) : null),
    [module.panel, selectedId],
  )

  if (educationMunicipioState.loading) {
    return <LoadingState message={FINANCIAL_PAGE_COPY.module.moduleLoading(module.title)} />
  }

  if (educationMunicipioState.error) {
    return (
      <ErrorState
        title={FINANCIAL_PAGE_COPY.module.moduleErrorTitle(module.title)}
        message={educationMunicipioState.error}
      />
    )
  }

  const educationData = educationMunicipioState.data

  if (module.panel === 'siope') {
    return (
      <SiopeIndicatorsPanel
        detailKey={detailKey}
        idMunicipio={selectedId}
        onDetailChange={onDetailChange}
      />
    )
  }

  if (module.panel === 'fundeb') {
    return (
      <FundebPanel
        detailKey={detailKey}
        embedded={true}
        municipioData={municipioData}
        onDetailChange={onDetailChange}
        selectedMunicipio={selectedMunicipio}
      />
    )
  }

  if (module.panel === 'vaar') {
    return <VaarPanel financialData={municipalFinanceState.data} vaarData={educationData?.blocos?.vaar} />
  }

  return (
    <PnatePanel
      detailKey={detailKey}
      onDetailChange={onDetailChange}
      pnateData={educationData?.blocos?.pnate ?? municipioData?.blocos?.pnate}
      selectedMunicipio={selectedMunicipio}
    />
  )
}

function FinanceIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 18h16" />
      <path d="M7 18V9h3v9M12 18V5h3v13M17 18v-6h3v6" />
      <path d="M4 6h3" />
    </svg>
  )
}
