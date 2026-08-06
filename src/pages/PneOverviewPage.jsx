import { InteractionChevron } from '../components/InteractionChevron'
import { EditorialExpandableGrid } from '../components/EditorialExpandableGrid'
import { PnePageHeader } from '../components/PnePageHeader'
import { pneOverviewContent } from '../data/pneOverviewContent'

const INTERNAL_NAV_ITEMS = [
  { label: 'Diretrizes', targetId: 'pne-diretrizes' },
  { label: 'Objetivos', targetId: 'pne-objetivos' },
  { label: 'Metas', targetId: 'pne-metas' },
  { label: 'Estratégias', targetId: 'pne-estrategias' },
  { label: 'Monitoramento', targetId: 'pne-monitoramento' },
]

function navigateWithinPage(targetId) {
  const target = document.getElementById(targetId)
  if (!target) return

  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  target.scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth', block: 'start' })
}

export function PneOverviewPage({ onNavigate }) {
  const {
    conceptCards,
    entryCards,
    entrySection,
    goalStrategyExplainers,
    goalStrategySection,
    governanceMonitoringItems,
    governanceSection,
    guidelineGroups,
    guidelineSection,
    hero,
    introduction,
    objectiveGroups,
    objectiveSection,
    sources,
  } = pneOverviewContent

  return (
    <div className="page-stack pne-overview-page">
      <PnePageHeader
        asideLabel="Resumo da base legal do PNE"
        asideContent={(
          <>
            <span className="pne-page-header__aside-title">Base legal</span>
            <strong className="pne-page-header__aside-highlight">Lei nº 15.388/2026</strong>
            <dl className="pne-page-header__facts">
              {hero.legalFacts.slice(1).map((fact) => (
                <div key={`${fact.label}-${fact.value}`}>
                  <dt>{fact.label}</dt>
                  <dd>{fact.value}</dd>
                </div>
              ))}
            </dl>
          </>
        )}
        description={hero.description}
        eyebrow={hero.eyebrow}
        title={hero.title}
        variant="editorial"
      />

      <nav className="pne-overview-internal-nav" aria-label="Navegação nesta página">
        {INTERNAL_NAV_ITEMS.map((item) => (
          <button key={item.targetId} type="button" onClick={() => navigateWithinPage(item.targetId)}>
            {item.label}
          </button>
        ))}
      </nav>

      <section className="page-card pne-overview-intro">
        <div className="pne-overview-intro__heading">
          <span className="eyebrow">{introduction.eyebrow}</span>
          <h2>{introduction.title}</h2>
          <p>{introduction.lead}</p>
        </div>
        <div className="pne-intro-grid">
          {introduction.points.map((point) => (
            <article className="pne-intro-card" key={point.title}>
              <span aria-hidden="true" />
              <h3>{point.title}</h3>
              <p>{point.body}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="pne-overview-section">
        <div className="pne-overview-section__heading">
          <span className="eyebrow">COMO A LEI ORGANIZA O PLANO</span>
          <h2>Diretrizes, objetivos, metas e estratégias</h2>
          <p>
            Quatro peças ajudam a transformar a lei em acompanhamento: princípios,
            mudanças esperadas, referências de verificação e caminhos de ação.
          </p>
        </div>
        <div className="pne-concept-grid">
          {conceptCards.map((concept, index) => (
            <article className="pne-concept-card" key={concept.title}>
              <span className="pne-concept-card__index">{String(index + 1).padStart(2, '0')}</span>
              <h3>{concept.title}</h3>
              <p>{concept.description}</p>
              <p className="pne-concept-card__note">{concept.panelUse}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="page-card pne-overview-section pne-overview-section--guided" id="pne-diretrizes">
        <div className="pne-overview-section__heading">
          <span className="eyebrow">{guidelineSection.eyebrow}</span>
          <h2>{guidelineSection.title}</h2>
          <p>{guidelineSection.description}</p>
        </div>
        <div className="pne-guideline-summary" aria-label="Resumo das diretrizes do PNE">
          {guidelineSection.summaryItems.map((item) => (
            <span key={item}>{item}</span>
          ))}
        </div>
        <EditorialExpandableGrid items={guidelineGroups} />
      </section>

      <section className="pne-overview-section" id="pne-objetivos">
        <div className="pne-overview-section__heading">
          <span className="eyebrow">{objectiveSection.eyebrow}</span>
          <h2>{objectiveSection.title}</h2>
          <p>{objectiveSection.description}</p>
        </div>
        <EditorialExpandableGrid items={objectiveGroups} />
      </section>

      <section className="page-card pne-overview-section pne-overview-section--guided" id="pne-metas">
        <div className="pne-overview-section__heading">
          <span className="eyebrow">{goalStrategySection.eyebrow}</span>
          <h2>{goalStrategySection.title}</h2>
          <p>{goalStrategySection.description}</p>
        </div>
        <div className="pne-anchor-grid">
          {goalStrategySection.anchors.map((anchor) => (
            <article className="pne-anchor-card" key={anchor.title}>
              <h3>{anchor.title}</h3>
              <p>{anchor.body}</p>
            </article>
          ))}
        </div>
        <div id="pne-estrategias">
          <EditorialExpandableGrid className="pne-expandable-grid--wide" items={goalStrategyExplainers} />
        </div>
      </section>

      <section className="pne-overview-section" id="pne-monitoramento">
        <div className="pne-overview-section__heading">
          <span className="eyebrow">{governanceSection.eyebrow}</span>
          <h2>{governanceSection.title}</h2>
          <p>{governanceSection.description}</p>
        </div>
        <EditorialExpandableGrid items={governanceMonitoringItems} />
      </section>

      <section className="pne-overview-section pne-overview-entries">
        <div className="pne-overview-section__heading">
          <span className="eyebrow">{entrySection.eyebrow}</span>
          <h2>{entrySection.title}</h2>
          <p>{entrySection.description}</p>
        </div>
        <div className="pne-entry-grid">
          {entryCards.map((entry) => (
            <button
              className="pne-entry-card interaction-card--navigation"
              data-entry-accent={entry.page === 'diagnostico' ? 'slate' : 'green'}
              key={entry.page}
              type="button"
              onClick={() => onNavigate?.(entry.page)}
            >
              <span className="pne-entry-card__indicator">
                <span aria-hidden="true" />
                {entry.indicator}
              </span>
              <span className="pne-entry-card__title">{entry.title}</span>
              <p>{entry.description}</p>
              <span className="pne-entry-card__footer">
                <strong>{entry.actionLabel}</strong>
                <InteractionChevron className="interaction-chevron--navigation" />
              </span>
            </button>
          ))}
        </div>
      </section>

      <footer className="pne-overview-source">
        <p>{sources.label}</p>
        <p>{sources.complementary}</p>
        <div>
          <a href={sources.planaltoUrl} target="_blank" rel="noreferrer">
            Presidência da República / Planalto
          </a>
          <a href={sources.camaraUrl} target="_blank" rel="noreferrer">
            Câmara dos Deputados
          </a>
        </div>
      </footer>
    </div>
  )
}
