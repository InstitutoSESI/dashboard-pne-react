import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { PnePageHeader } from '../../components/PnePageHeader'
import { ForesightObservedSeriesList } from './ForesightObservedSeries'
import { ForesightScenarioComparison } from './ForesightScenarioComparison'
import { ForesightScenarioTabs, foresightPanelId, foresightTabId } from './ForesightScenarioTabs'
import type { ForesightDocument, ForesightScenario } from './foresightTypes'
import '../../styles/foresight-page.css'

/*
 * Leitura de cenários exploratórios, sem escopo territorial próprio.
 *
 * A página apresenta o que o pacote público traz e não decide nada: não
 * ordena, não pontua, não atribui probabilidade e não gera número para ano
 * futuro. Os quatro cenários recebem o mesmo peso visual — mesma superfície,
 * mesma tipografia, mesma altura de cartão — porque nenhum deles é preferível.
 *
 * A leitura tem três camadas, do concreto para o exploratório: o que já foi
 * observado, o que é comum aos quatro cenários e, então, cada cenário.
 *
 * O território entra por `context`, e só ali: o corpo do relatório lê apenas
 * `document.*`. É isso que permite ao Vocações da Região reusar esta mesma
 * leitura com a identidade regional no lugar da municipal, sem ramificação.
 */

/*
 * O relatório só conhece o corpo do pacote: a identidade territorial fica de
 * fora do tipo, exatamente como fica de fora do JSX.
 */
export type ForesightScenarioDocument = Omit<ForesightDocument, 'municipality'>

const SUMMARY_ANCHORS = [
  { id: 'cenarios-ponto-de-partida', label: 'De onde o município parte' },
  { id: 'cenarios-condicoes-comuns', label: 'Condições comuns' },
  { id: 'cenarios-entrada', label: 'Os quatro cenários' },
  { id: 'cenarios-comparacao-titulo', label: 'Comparação' },
  { id: 'cenarios-detalhe-titulo', label: 'Leitura de cada cenário' },
  { id: 'cenarios-fontes', label: 'Fontes e metodologia' },
]

function ScenarioCard({
  isSelected,
  onExplore,
  scenario,
}: {
  isSelected: boolean
  onExplore: (slug: string) => void
  scenario: ForesightScenario
}) {
  const watch = scenario.sections.find((section) => section.key === 'o-que-acompanhar')
  const limit = scenario.sections.find((section) => section.key === 'limite-especifico')

  return (
    <li className="foresight-card">
      <article aria-labelledby={`cartao-${scenario.slug}`}>
        <h3 className="foresight-card__title" id={`cartao-${scenario.slug}`}>{scenario.title}</h3>
        <p className="foresight-card__summary">{scenario.summary}</p>
        <dl className="foresight-card__facets">
          <div>
            <dt>Sinais indicados</dt>
            <dd>{watch?.items.length ?? 0}</dd>
          </div>
          <div>
            <dt>Limite específico</dt>
            <dd>{limit ? 'declarado' : 'não declarado'}</dd>
          </div>
        </dl>
        <button
          aria-current={isSelected ? 'true' : undefined}
          className="foresight-card__action"
          onClick={() => onExplore(scenario.slug)}
          type="button"
        >
          Explorar cenário
          <span className="u-sr-only">: {scenario.title}</span>
        </button>
      </article>
    </li>
  )
}

function TextList({ items }: { items: readonly string[] }) {
  return (
    <ul className="foresight-list">
      {items.map((item) => <li key={item}>{item}</li>)}
    </ul>
  )
}

/** Corpo do relatório de cenários. `document` traz o pacote já validado. */
export function ForesightScenarioReport({
  context,
  document,
}: {
  context: string | null
  document: ForesightScenarioDocument
}) {
  const detailRef = useRef<HTMLElement | null>(null)
  const shouldFocusDetail = useRef(false)

  const scenarios = useMemo(() => document?.scenarios ?? [], [document])
  const [selectedSlug, setSelectedSlug] = useState<string>('')

  /* Trocar de município reinicia a seleção: nenhum estado do anterior sobrevive. */
  useEffect(() => {
    setSelectedSlug(scenarios[0]?.slug ?? '')
  }, [scenarios])

  const activeSlug = scenarios.some((scenario) => scenario.slug === selectedSlug)
    ? selectedSlug
    : scenarios[0]?.slug ?? ''
  const activeScenario = scenarios.find((scenario) => scenario.slug === activeSlug) ?? null

  const explore = useCallback((slug: string) => {
    shouldFocusDetail.current = true
    setSelectedSlug(slug)
  }, [])

  useEffect(() => {
    if (!shouldFocusDetail.current || !activeSlug) return
    shouldFocusDetail.current = false
    const tab = detailRef.current?.querySelector<HTMLButtonElement>(`#${CSS.escape(foresightTabId(activeSlug))}`)
    detailRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    tab?.focus({ preventScroll: true })
  }, [activeSlug])

  const {
    horizon,
    howToRead,
    limitations,
    observedSeries,
    page,
    sharedConditions,
    signals,
    sources,
    startingPoint,
  } = document

  return (
    <div className="page-stack foresight-page">
      <PnePageHeader
        actions={null}
        asideContent={null}
        asideLabel={null}
        context={context}
        description={page.description}
        eyebrow={page.eyebrow}
        title={page.title}
        variant="editorial"
      />

      <div className="foresight-lede">
        <p className="foresight-neutrality" role="note">{page.neutralityNote}</p>
        <p className="foresight-horizon">
          <span>{horizon.stateLabel}</span>
          <span>{horizon.scanLabel}</span>
          <span>{`${scenarios.length} cenários, sem ordem entre eles`}</span>
        </p>
        <nav aria-label="Seções desta página" className="foresight-summary">
          {SUMMARY_ANCHORS.map((anchor) => (
            <a href={`#${anchor.id}`} key={anchor.id}>{anchor.label}</a>
          ))}
        </nav>
      </div>

      <section aria-labelledby="cenarios-como-ler" className="foresight-panel foresight-panel--reading">
        <div className="foresight-panel__head">
          <h2 className="foresight-panel__title" id="cenarios-como-ler">{howToRead.label}</h2>
          <p className="foresight-panel__text">{howToRead.description}</p>
        </div>
        <TextList items={howToRead.items} />
      </section>

      <section aria-labelledby="cenarios-ponto-de-partida" className="foresight-panel">
        <div className="foresight-panel__head">
          <h2 className="foresight-panel__title" id="cenarios-ponto-de-partida">{startingPoint.label}</h2>
          <p className="foresight-panel__text">{startingPoint.description}</p>
        </div>

        <section aria-labelledby="ponto-series">
          <h3 className="foresight-subtitle" id="ponto-series">{observedSeries.label}</h3>
          <p className="foresight-panel__text">{observedSeries.description}</p>
          <ForesightObservedSeriesList items={observedSeries.items} />
        </section>

        <div className="foresight-starting-point">
          <section aria-labelledby="ponto-movimentos">
            <h3 className="foresight-subtitle" id="ponto-movimentos">Como esses movimentos são lidos</h3>
            <TextList items={startingPoint.movements} />
          </section>
          <section aria-labelledby="ponto-tensoes">
            <h3 className="foresight-subtitle" id="ponto-tensoes">Tensões entre as dimensões</h3>
            <TextList items={startingPoint.tensions} />
          </section>
          <section aria-labelledby="ponto-limites">
            <h3 className="foresight-subtitle" id="ponto-limites">O que limita esta leitura</h3>
            <TextList items={startingPoint.limits} />
          </section>
        </div>
      </section>

      <section aria-labelledby="cenarios-condicoes-comuns" className="foresight-panel foresight-panel--shared">
        <div className="foresight-panel__head">
          <h2 className="foresight-panel__title" id="cenarios-condicoes-comuns">{sharedConditions.label}</h2>
          <p className="foresight-panel__text">{sharedConditions.description}</p>
        </div>
        <TextList items={sharedConditions.items} />
      </section>

      <section aria-labelledby="cenarios-entrada" className="foresight-panel foresight-panel--grid">
        <div className="foresight-panel__head">
          <h2 className="foresight-panel__title" id="cenarios-entrada">Os quatro cenários</h2>
          <p className="foresight-panel__text">
            Cada cenário descreve uma forma diferente de a educação do município se organizar.
            Eles são apresentados sem ordem de preferência.
          </p>
        </div>
        <ul className="foresight-grid">
          {scenarios.map((scenario) => (
            <ScenarioCard
              isSelected={scenario.slug === activeSlug}
              key={scenario.slug}
              onExplore={explore}
              scenario={scenario}
            />
          ))}
        </ul>
      </section>

      <section aria-labelledby="cenarios-comparacao-titulo" className="foresight-panel foresight-panel--comparison">
        <div className="foresight-panel__head">
          <h2 className="foresight-panel__title" id="cenarios-comparacao-titulo">O que distingue cada cenário</h2>
          <p className="foresight-panel__text">
            As mesmas três perguntas, respondidas pelos quatro cenários. É aqui que a diferença
            entre eles fica visível de uma vez só.
          </p>
        </div>
        <ForesightScenarioComparison activeSlug={activeSlug} scenarios={scenarios} />
      </section>

      <section
        aria-labelledby="cenarios-detalhe-titulo"
        className="foresight-panel foresight-panel--detail"
        id="cenarios-detalhe"
        ref={detailRef}
      >
        <div className="foresight-panel__head">
          <h2 className="foresight-panel__title" id="cenarios-detalhe-titulo">Leitura de cada cenário</h2>
          <p className="foresight-panel__text">
            Selecione um cenário para ler de onde o município parte, como ele se forma,
            o que pode mudar e o que acompanhar.
          </p>
        </div>

        <ForesightScenarioTabs
          onSelect={setSelectedSlug}
          scenarios={scenarios}
          selectedSlug={activeSlug}
        />

        {activeScenario ? (
          <div
            aria-labelledby={foresightTabId(activeScenario.slug)}
            className="foresight-detail"
            id={foresightPanelId(activeScenario.slug)}
            role="tabpanel"
            tabIndex={-1}
          >
            <h3 className="foresight-detail__title">{activeScenario.title}</h3>
            {activeScenario.sections.map((section) => (
              <section className="foresight-detail__section" key={section.key}>
                <h4 className="foresight-subtitle">{section.label}</h4>
                <TextList items={section.items} />
              </section>
            ))}
          </div>
        ) : null}
      </section>

      <section aria-labelledby="cenarios-sinais" className="foresight-panel foresight-panel--signals">
        <div className="foresight-panel__head">
          <h2 className="foresight-panel__title" id="cenarios-sinais">{signals.label}</h2>
          <p className="foresight-panel__text">{signals.description}</p>
        </div>
        <TextList items={signals.items} />
      </section>

      <section aria-labelledby="cenarios-fontes" className="foresight-panel foresight-panel--sources">
        <div className="foresight-panel__head">
          <h2 className="foresight-panel__title" id="cenarios-fontes">{sources.label}</h2>
          <p className="foresight-panel__text">{sources.description}</p>
        </div>

        <div className="foresight-sources__table-wrapper">
          <table className="foresight-sources__table">
            <caption className="u-sr-only">Séries públicas usadas e seus períodos</caption>
            <thead>
              <tr>
                <th scope="col">Série</th>
                <th scope="col">Unidade</th>
                <th scope="col">Período</th>
              </tr>
            </thead>
            <tbody>
              {sources.series.map((serie) => (
                <tr key={serie.label}>
                  <td>{serie.label}</td>
                  <td>{serie.unitLabel}</td>
                  <td>{serie.periodLabel}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <TextList items={sources.notes} />

        <div className="foresight-limitations">
          <h3 className="foresight-subtitle">{limitations.label}</h3>
          <p className="foresight-panel__text">{limitations.description}</p>
          <TextList items={limitations.items} />
        </div>
      </section>
    </div>
  )
}
