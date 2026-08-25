import { useMemo, useState } from 'react'
import { LoadingState } from '../../components/LoadingState'
import { PnePageHeader } from '../../components/PnePageHeader'
import { ACTIVE_STATE_CONFIG } from '../../config/stateConfig'
import { useVocacoesRegiao } from '../../hooks/useVocacoesRegiao'
import type {
  VocacoesAssociation,
  VocacoesDocument,
  VocacoesSeries,
  VocacoesSeriesReference,
  VocacoesTemporalPair,
  VocacoesWindow,
} from './vocacoesRegiaoTypes'
import { buildSparklineModel } from '../../utils/sparkline'
import '../../styles/vocacoes-regiao-page.css'

/*
 * Vocações da Região — Fase A.
 *
 * Três blocos, nenhum cenário. O Bloco 1 é o retrato do território em séries
 * longas; o Bloco 2 põe um resultado educacional e os fatores territoriais lado
 * a lado, com os dados que sustentam a leitura visíveis na própria associação;
 * o Bloco 3 mostra pares de séries que mudaram ao mesmo tempo.
 *
 * A página não calcula nada. Toda agregação vive no builder da camada de
 * pesquisa e toda transposição vive no gerador — o que chega aqui já foi
 * conferido contra o manifesto, e renderizar é a única coisa que sobra.
 *
 * O que ela faz de deliberado: nunca apresenta prévia como observação, nunca
 * esconde a classe de evidência e nunca mostra uma leitura associativa sem a
 * proibição que vem junto dela. Os três não são enfeite editorial — são o
 * produto.
 */

const integerFormatter = new Intl.NumberFormat(ACTIVE_STATE_CONFIG.locale, {
  maximumFractionDigits: 0,
})
const decimalFormatter = new Intl.NumberFormat(ACTIVE_STATE_CONFIG.locale, {
  maximumFractionDigits: 1,
  minimumFractionDigits: 1,
})

function formatValue(value: number): string {
  return Number.isInteger(value) ? integerFormatter.format(value) : decimalFormatter.format(value)
}

const MONTH_LABELS = [
  'jan.', 'fev.', 'mar.', 'abr.', 'mai.', 'jun.',
  'jul.', 'ago.', 'set.', 'out.', 'nov.', 'dez.',
]

function formatPeriod(period: number, granularity: VocacoesSeries['periodGranularity']): string {
  if (granularity === 'annual') return String(period)
  const year = Math.floor(period / 100)
  const month = period % 100
  return `${MONTH_LABELS[month - 1]} ${year}`
}

/* O ano de um período, seja ele anual ou mensal — é assim que a janela de uma
 * associação, sempre anual, conversa com uma série mensal. */
function periodYear(period: number, granularity: VocacoesSeries['periodGranularity']): number {
  return granularity === 'annual' ? period : Math.floor(period / 100)
}

function pointsInWindow(serie: VocacoesSeries, window: VocacoesWindow) {
  return serie.points.filter((point) => {
    const year = periodYear(point.period, serie.periodGranularity)
    return year >= window.start && year <= window.end
  })
}

/*
 * Rótulo curto da classe de evidência, para a etiqueta. A frase inteira fica no
 * detalhe da série: a etiqueta avisa, a frase explica.
 */
const EVIDENCE_BADGES: Readonly<Record<VocacoesSeries['evidenceClass'], string>> = Object.freeze({
  observed: 'observado',
  preliminary: 'prévia',
  calculated: 'calculado',
  estimated_indirect: 'estimativa indireta',
})

function EvidenceBadge({ evidenceClass }: { evidenceClass: VocacoesSeries['evidenceClass'] }) {
  return (
    <span
      className={`vocacoes-badge vocacoes-badge--${evidenceClass.replace('_', '-')}`}
      data-evidence={evidenceClass}
    >
      {EVIDENCE_BADGES[evidenceClass]}
    </span>
  )
}

/*
 * A linha do tempo é decorativa e por isso fica escondida do leitor de tela: os
 * mesmos números estão na tabela de pontos, que é o conteúdo de verdade. Séries
 * com menos de três pontos não desenham nada — e dizem que não desenham, em vez
 * de mostrar uma linha reta que sugere estabilidade inexistente.
 */
function SeriesSparkline({ serie }: { serie: VocacoesSeries }) {
  const model = useMemo(
    () => buildSparklineModel(serie.points.map((point) => ({ ano: point.period, valor: point.value }))),
    [serie.points],
  )
  if (!model) return <span className="vocacoes-spark vocacoes-spark--empty">série curta demais para uma linha</span>
  return (
    <span aria-hidden="true" className="vocacoes-spark">
      <svg viewBox="0 0 320 56">
        <path className="vocacoes-spark__area" d={model.areaPath} />
        <path className="vocacoes-spark__line" d={model.linePath} />
        <circle className="vocacoes-spark__end" cx={model.lastPoint.x} cy={model.lastPoint.y} r={3.4} />
      </svg>
    </span>
  )
}

/*
 * Extremos observados da série. "Observado" aqui é literal: a prévia fica de
 * fora do par de extremos, porque comparar um valor fechado com uma prévia
 * apresenta como variação o que pode ser só revisão pendente. Quando só há
 * prévia, a página diz isso.
 */
function seriesEdges(serie: VocacoesSeries) {
  const closed = serie.points.filter((point) => point.evidenceClass !== 'preliminary')
  if (closed.length === 0) return null
  return { first: closed[0], last: closed[closed.length - 1] }
}

function SeriesCard({ serie }: { serie: VocacoesSeries }) {
  const edges = seriesEdges(serie)
  const preliminary = serie.points.filter((point) => point.evidenceClass === 'preliminary')
  /*
   * O detalhe so e montado quando aberto. `<details>` fechado esconde o
   * conteudo do olho, mas nao do DOM: com setenta e uma series na pagina, a
   * tabela de pontos de todas elas somava dezenas de milhares de linhas e
   * travava o renderizador. Montar sob demanda e o que torna o Bloco 1
   * navegavel — e nada se perde, porque `<details>` fechado ja era invisivel.
   */
  const [detailOpen, setDetailOpen] = useState(false)

  return (
    <article className="vocacoes-series">
      <header className="vocacoes-series__head">
        <h3 className="vocacoes-series__title">{serie.label}</h3>
        <EvidenceBadge evidenceClass={serie.evidenceClass} />
      </header>

      <p className="vocacoes-series__period">{serie.periodLabel}</p>
      <SeriesSparkline serie={serie} />

      {edges === null ? (
        <p className="vocacoes-series__reading">
          Esta série só tem períodos de prévia; nenhum valor fechado a resume.
        </p>
      ) : (
        <p className="vocacoes-series__reading">
          {`De ${formatValue(edges.first.value)} em ${formatPeriod(edges.first.period, serie.periodGranularity)}`}
          {` para ${formatValue(edges.last.value)} em ${formatPeriod(edges.last.period, serie.periodGranularity)}`}
          {` — ${serie.unitLabel}.`}
        </p>
      )}

      {preliminary.length > 0 && (
        <p className="vocacoes-series__preliminary">
          {`Prévia, sujeita a revisão: ${preliminary
            .map((point) => `${formatPeriod(point.period, serie.periodGranularity)} (${formatValue(point.value)})`)
            .join(', ')}.`}
        </p>
      )}

      <details
        className="vocacoes-series__detail"
        onToggle={(event) => setDetailOpen(event.currentTarget.open)}
      >
        <summary>Como esta série foi construída</summary>
        {detailOpen && (
        <>
        <dl className="vocacoes-meta">
          <div>
            <dt>Fonte</dt>
            <dd>{serie.sourceLabel}</dd>
          </div>
          <div>
            <dt>Unidade</dt>
            <dd>{serie.unitLabel}</dd>
          </div>
          <div>
            <dt>Agregação na região</dt>
            <dd>{serie.aggregationLabel}</dd>
          </div>
          <div>
            <dt>Classe do dado</dt>
            <dd>{serie.evidenceLabel}</dd>
          </div>
          {serie.universeLabel !== null && (
            <div>
              <dt>Universo</dt>
              <dd>{serie.universeLabel}</dd>
            </div>
          )}
          {serie.ratioOf !== null && (
            <div>
              <dt>Razão entre</dt>
              <dd>{`${serie.ratioOf.numeratorLabel} sobre ${serie.ratioOf.denominatorLabel}`}</dd>
            </div>
          )}
        </dl>

        {serie.limitations.length > 0 && (
          <>
            <p className="vocacoes-subtitle">O que esta série não diz</p>
            <ul className="vocacoes-list">
              {serie.limitations.map((limitation) => (
                <li key={limitation}>{limitation}</li>
              ))}
            </ul>
          </>
        )}

        <div className="vocacoes-table-scroll">
          <table className="vocacoes-table">
            <caption className="u-sr-only">{`Pontos da série ${serie.label}`}</caption>
            <thead>
              <tr>
                <th scope="col">Período</th>
                <th scope="col">Valor</th>
                <th scope="col">Classe</th>
              </tr>
            </thead>
            <tbody>
              {serie.points.map((point) => (
                <tr key={point.period}>
                  <th scope="row">{formatPeriod(point.period, serie.periodGranularity)}</th>
                  <td>{formatValue(point.value)}</td>
                  <td>{EVIDENCE_BADGES[point.evidenceClass]}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        </>
        )}
      </details>
    </article>
  )
}

/*
 * "Os dados que sustentam a leitura", que o plano exige por escrito: cada série
 * citada por uma associação ou por um par aparece junto dela, com os extremos
 * da janela declarada. Sem isto, a associação seria uma afirmação sem prova à
 * vista.
 */
function SupportingSeries({
  reference,
  series,
  window,
  role,
}: {
  reference: VocacoesSeriesReference
  series: ReadonlyMap<string, VocacoesSeries>
  window: VocacoesWindow
  role: string
}) {
  const serie = series.get(reference.seriesId)
  if (serie === undefined) return null
  const inWindow = pointsInWindow(serie, window)
  const closed = inWindow.filter((point) => point.evidenceClass !== 'preliminary')
  const first = closed[0]
  const last = closed[closed.length - 1]

  return (
    <div className="vocacoes-support">
      <p className="vocacoes-support__role">{role}</p>
      <p className="vocacoes-support__label">{serie.label}</p>
      {first === undefined || last === undefined ? (
        <p className="vocacoes-support__value">Sem valor fechado dentro da janela.</p>
      ) : (
        <p className="vocacoes-support__value">
          {`${formatValue(first.value)} (${formatPeriod(first.period, serie.periodGranularity)})`}
          {' → '}
          {`${formatValue(last.value)} (${formatPeriod(last.period, serie.periodGranularity)})`}
        </p>
      )}
      <p className="vocacoes-support__meta">
        {serie.unitLabel}
        {' · '}
        {EVIDENCE_BADGES[serie.evidenceClass]}
      </p>
    </div>
  )
}

function ProhibitedClaim({ claim }: { claim: string }) {
  return (
    <p className="vocacoes-prohibited">
      <span className="vocacoes-prohibited__mark">O que não se conclui</span>
      {claim}
    </p>
  )
}

function AssociationCard({
  association,
  series,
}: {
  association: VocacoesAssociation
  series: ReadonlyMap<string, VocacoesSeries>
}) {
  return (
    <article className="vocacoes-card">
      <header className="vocacoes-card__head">
        <h3 className="vocacoes-card__title">{association.label}</h3>
        <p className="vocacoes-card__context">
          {`Fatores territoriais: ${association.territorialFactors.map((factor) => factor.label).join(' · ')}`}
        </p>
        <p className="vocacoes-card__period">{association.periodLabel}</p>
      </header>

      <p className="vocacoes-card__statement">{association.observedStatement}</p>

      <div className="vocacoes-supports">
        <SupportingSeries
          reference={association.educationOutcome}
          role="Resultado educacional"
          series={series}
          window={association.window}
        />
        {association.territorialFactors.map((factor) => (
          <SupportingSeries
            key={factor.seriesId}
            reference={factor}
            role="Fator territorial"
            series={series}
            window={association.window}
          />
        ))}
      </div>

      <p className="vocacoes-allowed">
        <span className="vocacoes-allowed__mark">O que se pode ler</span>
        {association.allowedInterpretation}
      </p>
      <ProhibitedClaim claim={association.prohibitedClaim} />

      <p className="vocacoes-subtitle">Hipóteses a verificar com dado local</p>
      <ul className="vocacoes-list">
        {association.hypotheses.map((hypothesis) => (
          <li key={hypothesis}>{hypothesis}</li>
        ))}
      </ul>
    </article>
  )
}

function TemporalPairCard({
  pair,
  series,
}: {
  pair: VocacoesTemporalPair
  series: ReadonlyMap<string, VocacoesSeries>
}) {
  return (
    <article className="vocacoes-card">
      <header className="vocacoes-card__head">
        <h3 className="vocacoes-card__title">{pair.label}</h3>
        <p className="vocacoes-card__period">{pair.periodLabel}</p>
      </header>

      <p className="vocacoes-card__statement">{pair.observedStatement}</p>

      <div className="vocacoes-supports">
        <SupportingSeries reference={pair.seriesA} role="Primeira série" series={series} window={pair.window} />
        <SupportingSeries reference={pair.seriesB} role="Segunda série" series={series} window={pair.window} />
      </div>

      <ProhibitedClaim claim={pair.prohibitedClaim} />
    </article>
  )
}

/*
 * Setenta e uma séries numa página só é muita coisa para percorrer com o olho.
 * O filtro é de texto e nada mais: ele não reordena, não classifica e não
 * esconde nada por conta própria — quem não digita vê tudo, na ordem em que o
 * pacote publicou.
 */
function TerritoryPortrait({ document }: { document: VocacoesDocument }) {
  const [query, setQuery] = useState('')
  const normalized = query.trim().toLocaleLowerCase('pt-BR')
  const visible = normalized === ''
    ? document.territoryPortrait.series
    : document.territoryPortrait.series.filter((serie) =>
      `${serie.label} ${serie.sourceLabel} ${serie.unitLabel}`
        .toLocaleLowerCase('pt-BR')
        .includes(normalized))

  return (
    <section aria-labelledby="vocacoes-retrato" className="vocacoes-panel">
      <div className="vocacoes-panel__head">
        <h2 className="vocacoes-panel__title" id="vocacoes-retrato">
          {document.territoryPortrait.label}
        </h2>
        <p className="vocacoes-panel__text">{document.territoryPortrait.description}</p>
      </div>

      <label className="vocacoes-filter">
        <span className="vocacoes-filter__label">Filtrar as séries</span>
        <input
          className="vocacoes-filter__input"
          onChange={(event) => setQuery(event.target.value)}
          placeholder="matrículas, vínculos, nascidos vivos…"
          type="search"
          value={query}
        />
      </label>
      <p className="vocacoes-filter__count">
        {visible.length === document.territoryPortrait.series.length
          ? `${document.territoryPortrait.series.length} séries`
          : `${visible.length} de ${document.territoryPortrait.series.length} séries`}
      </p>

      {visible.length === 0 ? (
        <p className="vocacoes-panel__text">Nenhuma série corresponde ao filtro.</p>
      ) : (
        <div className="vocacoes-series-grid">
          {visible.map((serie) => (
            <SeriesCard key={serie.seriesId} serie={serie} />
          ))}
        </div>
      )}
    </section>
  )
}

function VocacoesReport({ document }: { document: VocacoesDocument }) {
  const seriesById = useMemo(
    () => new Map(document.territoryPortrait.series.map((serie) => [serie.seriesId, serie])),
    [document.territoryPortrait.series],
  )

  return (
    <div className="page-stack vocacoes-page">
      <PnePageHeader
        actions={null}
        asideContent={null}
        asideLabel={null}
        context={`${document.region.municipalityCount} municípios · ${document.region.uf}`}
        description={document.page.description}
        eyebrow={document.page.eyebrow}
        title={document.page.title}
        variant="editorial"
      />

      <p className="vocacoes-neutrality">{document.page.neutralityNote}</p>

      <section aria-labelledby="vocacoes-como-ler" className="vocacoes-panel">
        <div className="vocacoes-panel__head">
          <h2 className="vocacoes-panel__title" id="vocacoes-como-ler">{document.howToRead.label}</h2>
          <p className="vocacoes-panel__text">{document.howToRead.description}</p>
        </div>
        <ul className="vocacoes-list">
          {document.howToRead.items.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </section>

      <TerritoryPortrait document={document} />

      <section aria-labelledby="vocacoes-associacoes" className="vocacoes-panel">
        <div className="vocacoes-panel__head">
          <h2 className="vocacoes-panel__title" id="vocacoes-associacoes">{document.associations.label}</h2>
          <p className="vocacoes-panel__text">{document.associations.description}</p>
        </div>
        <div className="vocacoes-card-stack">
          {document.associations.items.map((association) => (
            <AssociationCard
              association={association}
              key={association.associationId}
              series={seriesById}
            />
          ))}
        </div>
      </section>

      <section aria-labelledby="vocacoes-pares" className="vocacoes-panel">
        <div className="vocacoes-panel__head">
          <h2 className="vocacoes-panel__title" id="vocacoes-pares">{document.temporalPairs.label}</h2>
          <p className="vocacoes-panel__text">{document.temporalPairs.description}</p>
        </div>
        <div className="vocacoes-card-stack">
          {document.temporalPairs.items.map((pair) => (
            <TemporalPairCard key={pair.pairId} pair={pair} series={seriesById} />
          ))}
        </div>
      </section>

      <section aria-labelledby="vocacoes-fontes" className="vocacoes-panel">
        <div className="vocacoes-panel__head">
          <h2 className="vocacoes-panel__title" id="vocacoes-fontes">{document.sources.label}</h2>
          <p className="vocacoes-panel__text">{document.sources.description}</p>
        </div>
        <div className="vocacoes-table-scroll">
          <table className="vocacoes-table">
            <caption className="u-sr-only">{`Fontes usadas na região ${document.region.name}`}</caption>
            <thead>
              <tr>
                <th scope="col">Fonte</th>
                <th scope="col">Período</th>
              </tr>
            </thead>
            <tbody>
              {document.sources.items.map((item) => (
                <tr key={item.label}>
                  <th scope="row">{item.label}</th>
                  <td>{item.periodLabel}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section aria-labelledby="vocacoes-limites" className="vocacoes-panel">
        <div className="vocacoes-panel__head">
          <h2 className="vocacoes-panel__title" id="vocacoes-limites">{document.limitations.label}</h2>
          <p className="vocacoes-panel__text">{document.limitations.description}</p>
        </div>
        <ul className="vocacoes-list">
          {document.limitations.items.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </section>
    </div>
  )
}

export function VocacoesRegiaoPage({
  municipalityId,
}: {
  municipalityId: string | null
}) {
  const { data, loading } = useVocacoesRegiao(municipalityId)

  if (loading) {
    return <LoadingState message="Carregando as vocações da região…" />
  }

  /*
   * Quem decide a visibilidade é o roteador, a partir do manifesto. Chegar
   * aqui sem pacote significa falha de integridade, e nesse caso não há o que
   * apresentar.
   */
  if (!data) return null

  return <VocacoesReport document={data.document} />
}
