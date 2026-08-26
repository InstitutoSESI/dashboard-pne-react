import { useMemo, useState } from 'react'
import type { MouseEvent as ReactMouseEvent } from 'react'
import { LoadingState } from '../../components/LoadingState'
import { PnePageHeader } from '../../components/PnePageHeader'
import { ACTIVE_STATE_CONFIG } from '../../config/stateConfig'
import { useVocacoesRegiao } from '../../hooks/useVocacoesRegiao'
import type {
  VocacoesAssociation,
  VocacoesAssociationReading,
  VocacoesAssociativeReasonCode,
  VocacoesDocument,
  VocacoesMunicipalLayer,
  VocacoesScenario,
  VocacoesScenarioBlock,
  VocacoesScenarios,
  VocacoesScreenedRelations,
  VocacoesSeries,
  VocacoesSeriesReference,
  VocacoesSynthesis,
  VocacoesSynthesisItem,
  VocacoesTemporalPair,
  VocacoesTemporalReading,
  VocacoesWindow,
} from './vocacoesRegiaoTypes'
import { buildSparklineModel } from '../../utils/sparkline'
import '../../styles/vocacoes-regiao-page.css'

/*
 * Vocações da Região.
 *
 * Quatro blocos. O Bloco 1 é o retrato do território em séries longas; o Bloco 2
 * põe um resultado educacional e os fatores territoriais lado a lado, com os
 * dados que sustentam a leitura visíveis na própria associação; o Bloco 3
 * mostra pares de séries que mudaram ao mesmo tempo; o Bloco 4 traz os cenários
 * da região — em duas regiões, e **declarando a ausência** nas outras oito.
 *
 * O Bloco 4 tem uma regra que os outros três não têm, e ela é a razão de a nota
 * de estatuto aparecer antes de qualquer cenário: os quatro cenários não têm o
 * mesmo peso. Três são exploratórios e um é normativo, e um leitor que não
 * souber disso lerá o normativo como previsão. É a diferença mais fácil de
 * perder e a mais cara de perder.
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

const ABSENCE_STATEMENTS: Readonly<Record<VocacoesAssociativeReasonCode, string>> = Object.freeze({
  sem_intervalos_comparaveis: 'Sem intervalos anuais comparáveis entre as duas séries nesta janela.',
  janela_curta: 'A janela comum entre as duas séries é curta demais para esta leitura.',
  variancia_nula: 'Uma das séries quase não varia nesta janela, e a leitura não se computa.',
  variacao_nula: 'Uma das séries terminou a janela onde começou, e a leitura de co-movimento não se computa.',
  contraste_sem_regioes_comparaveis: 'Não há regiões comparáveis para posicionar esta região no estado.',
  defasagem_sem_janela_suficiente: 'A janela disponível não comporta a defasagem declarada.',
  serie_ausente: 'Uma das séries desta leitura não está disponível no pacote publicado.',
})

type VocacoesAssociativeBlock =
  | { readonly statement: string }
  | { readonly reasonCode: VocacoesAssociativeReasonCode }

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
 * detalhe da série: a etiqueta avisa, a frase descreve.
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
function SeriesSparkline({
  serie,
  points = serie.points,
  compact = false,
}: {
  serie: VocacoesSeries
  points?: VocacoesSeries['points']
  compact?: boolean
}) {
  const model = useMemo(
    () => buildSparklineModel(points.map((point) => ({ ano: point.period, valor: point.value }))),
    [points],
  )
  if (!model) return <span className="vocacoes-spark vocacoes-spark--empty">série curta demais para uma linha</span>
  return (
    <span aria-hidden="true" className={`vocacoes-spark${compact ? ' vocacoes-spark--compact' : ''}`}>
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

      <details className="vocacoes-series__detail">
        <summary>Como esta série foi construída</summary>
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
      <SeriesSparkline compact points={inWindow} serie={serie} />
      {first === undefined || last === undefined ? (
        <p className="vocacoes-chip vocacoes-chip--value">Sem valor fechado dentro da janela.</p>
      ) : (
        <p className="vocacoes-chip vocacoes-chip--value">
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
    <details className="vocacoes-prohibited">
      <summary className="vocacoes-prohibited__mark">
        Nota metodológica — o que não se conclui
      </summary>
      <p>{claim}</p>
    </details>
  )
}

const OBSERVED_SYNTHESIS_LABEL = 'Do observado'
const CROSS_SCENARIO_SYNTHESIS_LABELS = new Set([
  'Sustentado nos quatro cenários',
  'Frentes da agenda mobilizadas',
])

function associationSynthesisBasisLabel(association: VocacoesAssociation): string {
  return [
    association.educationOutcome.label,
    ...association.territorialFactors.map((factor) => factor.label),
  ].join(' · ')
}

function ConclusionVerdict({ item }: { item: VocacoesSynthesisItem }) {
  return (
    <p className="vocacoes-allowed vocacoes-conclusion-verdict">
      <span className="vocacoes-allowed__mark vocacoes-conclusion-verdict__label">
        Conclusão observada
      </span>
      {item.statement}
    </p>
  )
}

function SynthesisPanel({ synthesis }: { synthesis: VocacoesSynthesis }) {
  const groups = synthesis.items.reduce<Map<string, VocacoesSynthesisItem[]>>((result, item) => {
    const entries = result.get(item.kindLabel) ?? []
    entries.push(item)
    result.set(item.kindLabel, entries)
    return result
  }, new Map())

  return (
    <section aria-labelledby="vocacoes-conclusoes" className="vocacoes-panel vocacoes-synthesis">
      <div className="vocacoes-panel__head">
        <h2 className="vocacoes-panel__title" id="vocacoes-conclusoes">{synthesis.label}</h2>
        <p className="vocacoes-panel__text">{synthesis.description}</p>
      </div>

      <div className="vocacoes-card-stack">
        {[...groups].map(([kindLabel, items]) => (
          <section key={kindLabel}>
            <h3 className="vocacoes-subtitle">{kindLabel}</h3>
            <ul className="vocacoes-list vocacoes-synthesis__items">
              {items.map((item) => (
                <li key={`${item.kindLabel}:${item.basisLabel ?? item.statement}`}>
                  <p>{item.statement}</p>
                  {item.basisLabel === undefined ? null : (
                    <span className="vocacoes-synthesis__basis">{item.basisLabel}</span>
                  )}
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>

      {synthesis.absentKinds.length === 0 ? null : (
        <div className="vocacoes-neutrality vocacoes-synthesis__absences">
          {synthesis.absentKinds.map((absence) => (
            <p key={absence.kindLabel}>
              <span>{absence.kindLabel}</span>
              {absence.statement}
            </p>
          ))}
        </div>
      )}

      <details className="vocacoes-reading-detail vocacoes-synthesis__method">
        <summary>Como estas conclusões foram compostas</summary>
        <p>{synthesis.methodNote}</p>
      </details>
    </section>
  )
}

function scrollToPageSection(
  event: ReactMouseEvent<HTMLAnchorElement>,
  targetId: string,
) {
  event.preventDefault()
  if (typeof document === 'undefined') return
  document.getElementById(targetId)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

function AssociativeStatement({ block }: { block: VocacoesAssociativeBlock }) {
  const isAbsence = 'reasonCode' in block
  return (
    <p
      className={`vocacoes-associative-reading__statement${
        isAbsence ? ' vocacoes-associative-reading__absence' : ''
      }`}
    >
      {isAbsence ? ABSENCE_STATEMENTS[block.reasonCode] : block.statement}
    </p>
  )
}

function AssociationReadingPanel({
  allowedInterpretation,
  reading,
}: {
  allowedInterpretation: string
  reading: VocacoesAssociationReading
}) {
  return (
    <div aria-label="Leitura quantificada" className="vocacoes-associative-reading">
      <div className="vocacoes-associative-reading__statements">
        {reading.factorReadings.map((factorReading) => (
          <div
            className="vocacoes-associative-reading__factor"
            key={`${factorReading.outcomeSeriesId}:${factorReading.factorSeriesId}`}
          >
            <AssociativeStatement block={factorReading.correlation} />
            <AssociativeStatement block={factorReading.directionConcordance} />
            <AssociativeStatement block={factorReading.comovement} />
          </div>
        ))}
        <AssociativeStatement block={reading.stateContrast} />
      </div>

      <p className="vocacoes-allowed">
        <span className="vocacoes-allowed__mark">O que se pode ler</span>
        {allowedInterpretation}
      </p>

      <details className="vocacoes-reading-detail vocacoes-associative-reading__method">
        <summary>Como esta leitura foi computada</summary>
        <p>{reading.methodNote}</p>
      </details>
    </div>
  )
}

function TemporalReadingPanel({ reading }: { reading: VocacoesTemporalReading }) {
  return (
    <div aria-label="Leitura quantificada" className="vocacoes-associative-reading">
      <div className="vocacoes-associative-reading__statements">
        <AssociativeStatement block={reading.directionConcordance} />
        <AssociativeStatement block={reading.comovement} />
        <AssociativeStatement block={reading.correlation} />
        <AssociativeStatement block={reading.stateContrast} />
      </div>

      <details className="vocacoes-reading-detail vocacoes-associative-reading__method">
        <summary>Como esta leitura foi computada</summary>
        <p>{reading.methodNote}</p>
      </details>
    </div>
  )
}

function AssociationCard({
  association,
  conclusion,
  series,
}: {
  association: VocacoesAssociation
  conclusion: VocacoesSynthesisItem
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

      <ConclusionVerdict item={conclusion} />

      <AssociationReadingPanel
        allowedInterpretation={association.allowedInterpretation}
        reading={association.associativeReading}
      />

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

      <details className="vocacoes-reading-detail">
        <summary>Leitura por extenso</summary>
        <p className="vocacoes-card__statement">{association.observedStatement}</p>
      </details>

      <div className="vocacoes-hypotheses">
        <h4 className="vocacoes-subtitle">
          Hipóteses explicativas — a verificar com dado local
        </h4>
        <ul className="vocacoes-list">
          {association.hypotheses.map((hypothesis) => (
            <li key={hypothesis}>{hypothesis}</li>
          ))}
        </ul>
      </div>

      <ProhibitedClaim claim={association.prohibitedClaim} />
    </article>
  )
}

function TemporalPairCard({
  conclusion,
  pair,
  series,
}: {
  conclusion: VocacoesSynthesisItem
  pair: VocacoesTemporalPair
  series: ReadonlyMap<string, VocacoesSeries>
}) {
  return (
    <article className="vocacoes-card">
      <header className="vocacoes-card__head">
        <h3 className="vocacoes-card__title">{pair.label}</h3>
        <p className="vocacoes-card__period">{pair.periodLabel}</p>
      </header>

      <ConclusionVerdict item={conclusion} />

      <TemporalReadingPanel reading={pair.associativeReading} />

      <div className="vocacoes-supports">
        <SupportingSeries reference={pair.seriesA} role="Primeira série" series={series} window={pair.window} />
        <SupportingSeries reference={pair.seriesB} role="Segunda série" series={series} window={pair.window} />
      </div>

      <details className="vocacoes-reading-detail">
        <summary>Leitura por extenso</summary>
        <p className="vocacoes-card__statement">{pair.observedStatement}</p>
      </details>

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
/* ------------------------------------------------------------------ *
 * Bloco 4 — cenários da região.
 * ------------------------------------------------------------------ */

function ScenarioAnchors({
  scenario,
  series,
}: {
  scenario: VocacoesScenario
  series: Map<string, VocacoesSeries>
}) {
  return (
    <div className="vocacoes-table-scroll">
      <table className="vocacoes-table vocacoes-anchors">
        <caption className="u-sr-only">
          {`Séries que ancoram o cenário ${scenario.title}`}
        </caption>
        <thead>
          <tr>
            <th scope="col">Série</th>
            <th scope="col">Janela</th>
            <th scope="col">Início</th>
            <th scope="col">Fim</th>
            <th scope="col">Na janela</th>
          </tr>
        </thead>
        <tbody>
          {scenario.anchors.map((anchor) => {
            const serie = series.get(anchor.seriesId)
            return (
              <tr key={anchor.seriesId}>
                <th scope="row">{anchor.label}</th>
                <td>{anchor.periodLabel}</td>
                <td>{formatValue(anchor.startValue)}</td>
                <td>{formatValue(anchor.endValue)}</td>
                <td>
                  {anchor.directionLabel}
                  {serie === undefined ? null : ` · ${serie.unitLabel}`}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

function ScenarioComparison({ scenarios }: { scenarios: readonly VocacoesScenario[] }) {
  return (
    <div aria-label="Comparação dos cenários" className="vocacoes-scenario-ruler">
      {scenarios.map((scenario) => (
        <a
          className="vocacoes-scenario-ruler__item"
          href={`#vocacoes-cenario-${scenario.scenarioId}`}
          key={scenario.scenarioId}
          onClick={(event) => scrollToPageSection(event, `vocacoes-cenario-${scenario.scenarioId}`)}
        >
          <span className="vocacoes-scenario__profile">{scenario.profileLabel}</span>
          <strong className="vocacoes-scenario-ruler__title">{scenario.title}</strong>
          <span className={`vocacoes-statute vocacoes-statute--${scenario.statute}`}>
            {scenario.statuteLabel}
          </span>
          <span className="vocacoes-scenario-ruler__directions">
            {scenario.anchors.map((anchor) => (
              <span className="vocacoes-direction-chip" key={anchor.seriesId}>
                <span>{anchor.label}</span>
                <strong>{anchor.directionLabel}</strong>
              </span>
            ))}
          </span>
        </a>
      ))}
    </div>
  )
}

function LaggedReadings({
  items,
}: {
  items: VocacoesDocument['temporalPairs']['laggedItems']
}) {
  if (items.length === 0) return null

  return (
    <div className="vocacoes-lagged-readings">
      <h3 className="vocacoes-subtitle">Leituras com defasagem declarada</h3>
      <div className="vocacoes-lagged-readings__items">
        {items.map((item) => (
          <article
            className="vocacoes-lagged-reading"
            key={`${item.aSeriesId}:${item.bSeriesId}:${item.lagYears}`}
          >
            <p>{item.statement}</p>
            {'rationale' in item ? (
              <details className="vocacoes-reading-detail">
                <summary>Por que esta defasagem</summary>
                <p>{item.rationale}</p>
              </details>
            ) : null}
          </article>
        ))}
      </div>
    </div>
  )
}

function ScreenedRelationsPanel({
  screenedRelations,
  series,
}: {
  screenedRelations: VocacoesScreenedRelations
  series: ReadonlyMap<string, VocacoesSeries>
}) {
  return (
    <section aria-labelledby="vocacoes-triagem" className="vocacoes-panel">
      <div className="vocacoes-panel__head">
        <h2 className="vocacoes-panel__title" id="vocacoes-triagem">
          {screenedRelations.label}
        </h2>
        <p className="vocacoes-panel__text">{screenedRelations.description}</p>
      </div>

      <div className="vocacoes-screened-relations">
        {screenedRelations.items.map((relation) => (
          <article className="vocacoes-screened-relation" key={relation.relationId}>
            <header className="vocacoes-card__head">
              <h3 className="vocacoes-card__title">
                <span>{series.get(relation.seriesAId)?.label}</span>
                {' · '}
                <span>{series.get(relation.seriesBId)?.label}</span>
              </h3>
              <p className="vocacoes-card__period">
                {`Janela: ${relation.window.start} a ${relation.window.end}`}
              </p>
            </header>

            <div className="vocacoes-associative-reading__statements">
              <AssociativeStatement block={relation.correlation} />
              <AssociativeStatement block={relation.directionConcordance} />
              <AssociativeStatement block={relation.comovement} />
            </div>
            <p className="vocacoes-screened-relation__origin">{relation.originStatement}</p>
          </article>
        ))}
      </div>

      <details className="vocacoes-reading-detail vocacoes-screened-relations__method">
        <summary>Como a triagem funciona</summary>
        <p>{screenedRelations.methodNote}</p>
        <p>
          {`Critérios fixos: correlação absoluta mínima de ${formatValue(screenedRelations.criteria.minAbsPearson)}, pelo menos ${formatValue(screenedRelations.criteria.minIntervals)} intervalos anuais, no máximo ${formatValue(screenedRelations.criteria.maxItems)} relações por região.`}
        </p>
      </details>
    </section>
  )
}

function ScenarioCard({
  defaultOpen,
  scenario,
  series,
}: {
  defaultOpen: boolean
  scenario: VocacoesScenario
  series: Map<string, VocacoesSeries>
}) {
  return (
    <details
      className="vocacoes-card vocacoes-scenario"
      id={`vocacoes-cenario-${scenario.scenarioId}`}
      open={defaultOpen}
    >
      <summary className="vocacoes-scenario__summary">
        <span className="vocacoes-scenario__profile">{scenario.profileLabel}</span>
        <span className="vocacoes-card__title">{scenario.title}</span>
        <span className={`vocacoes-statute vocacoes-statute--${scenario.statute}`}>
          {scenario.statuteLabel}
        </span>
      </summary>

      <div className="vocacoes-scenario__body">
        <p className="vocacoes-card__statement vocacoes-scenario__mechanism">
          {scenario.centralMechanism}
        </p>

        <ScenarioAnchors scenario={scenario} series={series} />

        <dl className="vocacoes-meta vocacoes-scenario__horizon">
          <div>
            <dt>Como fica no horizonte</dt>
            <dd>{scenario.stateAtHorizonStatement}</dd>
          </div>
        </dl>

        <details className="vocacoes-reading-detail">
          <summary>Leitura por extenso</summary>
          <dl className="vocacoes-meta vocacoes-scenario__arc">
            <div>
              <dt>De onde parte</dt>
              <dd>{scenario.startingPointStatement}</dd>
            </div>
            <div>
              <dt>O que acontece com as séries</dt>
              <dd>{scenario.trajectoryStatement}</dd>
            </div>
          </dl>
        </details>

        <div className="vocacoes-agenda__head">
          <p className="vocacoes-subtitle">O que isso pede da educação da região</p>
          <p className="vocacoes-agenda__label">Temas da agenda do PNE</p>
        </div>
        <ul className="vocacoes-list vocacoes-agenda">
          {scenario.educationImplications.map((implication) => {
            const themes = scenario.agendaThemes.filter(
              (theme) => theme.statement === implication.statement,
            )
            return (
              <li key={implication.stageLabel}>
                <strong>{implication.stageLabel}.</strong> {implication.statement}
                {themes.length > 0 ? (
                  <span className="vocacoes-chip-row">
                    {themes.map((theme) => (
                      <span className="vocacoes-chip vocacoes-chip--theme" key={theme.theme}>
                        {theme.themeLabel}
                      </span>
                    ))}
                  </span>
                ) : null}
              </li>
            )
          })}
        </ul>

        <div className="vocacoes-scenario__secondary">
          <details className="vocacoes-reading-detail">
            <summary>O que enfraqueceria este cenário</summary>
            <ul className="vocacoes-list">
              {scenario.contraryEvidence.map((evidence) => (
                <li key={evidence}>{evidence}</li>
              ))}
            </ul>
          </details>

          <details className="vocacoes-reading-detail">
            <summary>O que este cenário não alcança</summary>
            <ul className="vocacoes-list">
              {scenario.limits.map((limit) => (
                <li key={limit}>{limit}</li>
              ))}
            </ul>
          </details>
        </div>

        <ProhibitedClaim claim={scenario.prohibitedClaim} />
      </div>
    </details>
  )
}

/*
 * Camada municipal (sucessora da D11): a leitura de cada município dentro do
 * cenário regional. A página não calcula nada aqui também — a composição e a
 * exposição já vêm compostas e conferidas. O que ela faz é deixar o leitor
 * escolher um município e ler a posição observada dele, ao lado da declaração do
 * que **não** se decompõe ao município nesta fonte. Nenhum ranking: os
 * municípios aparecem em ordem alfabética, e a leitura de cada um é ante a
 * mediana da região, nunca ante os outros.
 */
function MunicipalLayerPanel({
  layer,
  block,
}: {
  layer: VocacoesMunicipalLayer
  block: VocacoesScenarioBlock
}) {
  const municipalities = useMemo(
    () => [...layer.municipalities].sort((left, right) => left.name.localeCompare(right.name, 'pt-BR')),
    [layer.municipalities],
  )
  const titleByOrder = useMemo(
    () => new Map(block.items.map((scenario) => [scenario.order, scenario.title])),
    [block.items],
  )
  const dimensionByLabel = useMemo(
    () => new Map(layer.dimensions.map((dimension) => [dimension.label, dimension])),
    [layer.dimensions],
  )
  const [selectedId, setSelectedId] = useState(municipalities[0]?.municipalityId ?? '')
  const selected = municipalities.find((item) => item.municipalityId === selectedId)
    ?? municipalities[0]
  const methodologicalFrame = municipalities[0]?.scenarioExposure[0]?.allowedInterpretation

  return (
    <section
      aria-labelledby="vocacoes-municipal-heading"
      className="vocacoes-municipal"
      id="vocacoes-municipios"
    >
      <h3 className="vocacoes-subtitle" id="vocacoes-municipal-heading">{layer.label}</h3>
      <p className="vocacoes-panel__text">{layer.description}</p>
      <p className="vocacoes-neutrality">{layer.methodNote}</p>
      {methodologicalFrame === undefined ? null : (
        <p className="vocacoes-neutrality vocacoes-municipal__frame">{methodologicalFrame}</p>
      )}

      <details className="vocacoes-municipal__method">
        <summary>Quais séries a camada usa, e quais não se decompõem ao município</summary>
        <div className="vocacoes-table-scroll">
          <table className="vocacoes-table">
            <caption className="u-sr-only">Séries municipais desta camada</caption>
            <thead>
              <tr>
                <th scope="col">Série</th>
                <th scope="col">Natureza</th>
                <th scope="col">Fonte</th>
                <th scope="col">Período</th>
              </tr>
            </thead>
            <tbody>
              {layer.dimensions.map((dimension) => (
                <tr key={dimension.label}>
                  <th scope="row">{dimension.label}</th>
                  <td>
                    {dimension.kindLabel}
                    {dimension.universeLabel !== null ? (
                      <span className="vocacoes-municipal__universe">
                        {dimension.universeLabel}
                      </span>
                    ) : null}
                  </td>
                  <td>{dimension.sourceLabel}</td>
                  <td>{dimension.periodLabel}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="vocacoes-subtitle">O que não se decompõe ao município nesta fonte</p>
        <ul className="vocacoes-list">
          {layer.undecomposableDomains.map((domain) => (
            <li key={domain.label}>
              <strong>{domain.label}.</strong> {domain.reason} Fonte consultada: {domain.consultedSource}.
            </li>
          ))}
        </ul>
      </details>

      <div className="vocacoes-municipal__picker">
        <label htmlFor="vocacoes-municipal-select">Escolha um município da região</label>
        <select
          className="vocacoes-municipal__select"
          id="vocacoes-municipal-select"
          onChange={(event) => setSelectedId(event.target.value)}
          value={selected?.municipalityId ?? ''}
        >
          {municipalities.map((municipality) => (
            <option key={municipality.municipalityId} value={municipality.municipalityId}>
              {municipality.name}
            </option>
          ))}
        </select>
      </div>

      {selected !== undefined ? (
        <article className="vocacoes-card vocacoes-municipal__card">
          <header className="vocacoes-card__head">
            <h4 className="vocacoes-card__title">{selected.name}</h4>
          </header>

          <div className="vocacoes-table-scroll vocacoes-municipal__composition">
            <table className="vocacoes-table">
              <caption>Composição observada na região</caption>
              <thead>
                <tr>
                  <th scope="col">Dimensão</th>
                  <th scope="col">Composição</th>
                </tr>
              </thead>
              <tbody>
                {selected.composition.map((line) => {
                  const dimension = dimensionByLabel.get(line.dimensionLabel)
                  return (
                    <tr key={line.dimensionLabel}>
                      <th scope="row">
                        {line.dimensionLabel}
                        {dimension?.universeLabel === null || dimension?.universeLabel === undefined
                          ? null
                          : (
                            <span className="vocacoes-municipal__universe">
                              {dimension.universeLabel}
                            </span>
                          )}
                      </th>
                      <td>{line.statement}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>

          <p className="vocacoes-subtitle">Como o município se liga a cada cenário</p>
          <div className="vocacoes-municipal__exposures">
            {selected.scenarioExposure.map((exposure) => (
              <details className="vocacoes-municipal__exposure" key={exposure.order}>
                <summary>
                  {titleByOrder.get(exposure.order) ?? `Cenário ${exposure.order}`}
                </summary>
                <p className="vocacoes-panel__text">{exposure.exposureStatement}</p>
                <ProhibitedClaim claim={exposure.prohibitedClaim} />
              </details>
            ))}
          </div>
        </article>
      ) : null}
    </section>
  )
}

function ScenariosPanel({
  conclusions,
  scenarios,
  series,
  regionName,
}: {
  conclusions: readonly VocacoesSynthesisItem[]
  scenarios: VocacoesScenarios
  series: Map<string, VocacoesSeries>
  regionName: string
}) {
  const block = scenarios.block

  return (
    <section aria-labelledby="vocacoes-cenarios" className="vocacoes-panel">
      <div className="vocacoes-panel__head">
        <h2 className="vocacoes-panel__title" id="vocacoes-cenarios">{scenarios.label}</h2>
        <p className="vocacoes-panel__text">{scenarios.description}</p>
      </div>

      {/*
        * A região sem cenário não recebe seção vazia nem seção escondida: recebe
        * a frase que diz que não há cenário aqui. Esconder a seção faria a
        * ausência parecer um bloco que se perdeu no caminho; deixá-la vazia
        * faria parecer um erro de carregamento.
        */}
      {block === null ? (
        <p className="vocacoes-scenarios__absence">{scenarios.absenceStatement}</p>
      ) : (
        <>
          <p className="vocacoes-neutrality vocacoes-scenarios__statute-note">
            {scenarios.statuteReadingNote}
          </p>

          <p className="vocacoes-panel__text">{block.statuteNote}</p>

          <section
            aria-labelledby="vocacoes-cenarios-conclusoes"
            className="vocacoes-scenarios__conclusions"
          >
            <h3 className="vocacoes-subtitle" id="vocacoes-cenarios-conclusoes">
              O que vale em qualquer cenário
            </h3>
            <ul className="vocacoes-list vocacoes-synthesis__items">
              {conclusions.map((item) => (
                <li key={`${item.kindLabel}:${item.statement}`}>
                  <span className="vocacoes-synthesis__basis">{item.kindLabel}</span>
                  <p>{item.statement}</p>
                </li>
              ))}
            </ul>
          </section>

          <ScenarioComparison scenarios={block.items} />

          <dl className="vocacoes-meta">
            <div>
              <dt>Pergunta que os cenários respondem</dt>
              <dd>{block.focalQuestion}</dd>
            </div>
            <div>
              <dt>Horizonte</dt>
              <dd>
                {block.horizonStatement} {block.longScanStatement}
              </dd>
            </div>
            <div>
              <dt>Linha de base</dt>
              <dd>{block.baseYearStatement}</dd>
            </div>
            <div>
              <dt>Alcance da leitura entre trabalho e educação</dt>
              <dd>{block.compatibilityCeilingStatement}</dd>
            </div>
            <div>
              <dt>Como foram construídos</dt>
              <dd>
                {block.methodologyLabel}. {block.maturityNote}
              </dd>
            </div>
          </dl>

          <div className="vocacoes-card-stack">
            {block.items.map((scenario, index) => (
              <ScenarioCard
                defaultOpen={index === 0}
                key={scenario.scenarioId}
                scenario={scenario}
                series={series}
              />
            ))}
          </div>

          <details className="vocacoes-scenarios__closing">
            <summary>Critérios e condições do cenário normativo</summary>
            <div className="vocacoes-scenarios__closing-body">
            <p className="vocacoes-subtitle">O que vale em qualquer um dos quatro</p>
            <ul className="vocacoes-list">
              {block.robustImplications.map((implication) => (
                <li key={implication}>{implication}</li>
              ))}
            </ul>

            <p className="vocacoes-subtitle">
              {`O que o cenário normativo exigiria da região ${regionName}`}
            </p>
            <div className="vocacoes-table-scroll">
              <table className="vocacoes-table">
                <caption className="u-sr-only">
                  {`Critérios do cenário normativo da região ${regionName}`}
                </caption>
                <thead>
                  <tr>
                    <th scope="col">Critério</th>
                    <th scope="col">O que significa</th>
                    <th scope="col">O que precisaria estar valendo</th>
                    <th scope="col">O que se perde no caminho</th>
                    <th scope="col">Como ele falha</th>
                    <th scope="col">O que acompanhar</th>
                  </tr>
                </thead>
                <tbody>
                  {block.normativeCriteria.map((criterion) => (
                    <tr key={criterion.publicName}>
                      <th scope="row">{criterion.publicName}</th>
                      <td>{criterion.definition}</td>
                      <td>{criterion.requiredState}</td>
                      <td>{criterion.tradeOff}</td>
                      <td>{criterion.failureMode}</td>
                      <td>{criterion.whatToFollow}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <p className="vocacoes-subtitle">O que precisaria existir para ele ganhar força</p>
            <ul className="vocacoes-list">
              {block.realizationConditions.map((condition) => (
                <li key={condition}>{condition}</li>
              ))}
            </ul>

            <p className="vocacoes-panel__text">{block.conditionalImplication}</p>
            <ProhibitedClaim claim={block.prohibitedClaim} />
            </div>
          </details>

          <MunicipalLayerPanel layer={block.municipalLayer} block={block} />
        </>
      )}
    </section>
  )
}

function TerritoryPortrait({ document }: { document: VocacoesDocument }) {
  const [query, setQuery] = useState('')
  const normalized = query.trim().toLocaleLowerCase('pt-BR')
  const seriesInUseIds = useMemo(() => {
    const ids = new Set<string>()
    for (const association of document.associations.items) {
      ids.add(association.educationOutcome.seriesId)
      for (const factor of association.territorialFactors) ids.add(factor.seriesId)
    }
    for (const pair of document.temporalPairs.items) {
      ids.add(pair.seriesA.seriesId)
      ids.add(pair.seriesB.seriesId)
    }
    for (const relation of document.screenedRelations.items) {
      ids.add(relation.seriesAId)
      ids.add(relation.seriesBId)
    }
    if (document.scenarios.block !== null) {
      for (const scenario of document.scenarios.block.items) {
        for (const anchor of scenario.anchors) ids.add(anchor.seriesId)
      }
    }
    return ids
  }, [
    document.associations.items,
    document.scenarios.block,
    document.screenedRelations.items,
    document.temporalPairs.items,
  ])
  const seriesInUse = useMemo(
    () => document.territoryPortrait.series.filter((serie) => seriesInUseIds.has(serie.seriesId)),
    [document.territoryPortrait.series, seriesInUseIds],
  )
  const remainingBySource = useMemo(() => {
    const groups = new Map<string, VocacoesSeries[]>()
    for (const serie of document.territoryPortrait.series) {
      if (seriesInUseIds.has(serie.seriesId)) continue
      const group = groups.get(serie.sourceLabel)
      if (group === undefined) groups.set(serie.sourceLabel, [serie])
      else group.push(serie)
    }
    return [...groups.entries()]
  }, [document.territoryPortrait.series, seriesInUseIds])
  const filtered = normalized === ''
    ? []
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
        {normalized === ''
          ? `${seriesInUse.length} séries em uso · ${document.territoryPortrait.series.length} séries no território`
          : `${filtered.length} de ${document.territoryPortrait.series.length} séries`}
      </p>

      {normalized !== '' && filtered.length === 0 ? (
        <p className="vocacoes-panel__text">Nenhuma série corresponde ao filtro.</p>
      ) : normalized !== '' ? (
        <div className="vocacoes-series-grid">
          {filtered.map((serie) => (
            <SeriesCard key={serie.seriesId} serie={serie} />
          ))}
        </div>
      ) : (
        <>
          <div className="vocacoes-series-view__head">
            <h3 className="vocacoes-subtitle">Séries em uso nas leituras desta página</h3>
            <span className="vocacoes-chip">{seriesInUse.length}</span>
          </div>
          <div className="vocacoes-series-grid">
            {seriesInUse.map((serie) => (
              <SeriesCard key={serie.seriesId} serie={serie} />
            ))}
          </div>

          <details className="vocacoes-all-series">
            <summary>
              <span>{`Todas as séries do território (${document.territoryPortrait.series.length})`}</span>
              <span className="vocacoes-chip">{`+${document.territoryPortrait.series.length - seriesInUse.length}`}</span>
            </summary>
            <div className="vocacoes-series-sources">
              {remainingBySource.map(([sourceLabel, series]) => (
                <section className="vocacoes-series-source" key={sourceLabel}>
                  <div className="vocacoes-series-source__head">
                    <h3>{sourceLabel}</h3>
                    <span className="vocacoes-chip">{series.length}</span>
                  </div>
                  <div className="vocacoes-series-grid">
                    {series.map((serie) => (
                      <SeriesCard key={serie.seriesId} serie={serie} />
                    ))}
                  </div>
                </section>
              ))}
            </div>
          </details>
        </>
      )}
    </section>
  )
}

function PageSectionNav({ hasMunicipalLayer }: { hasMunicipalLayer: boolean }) {
  const items = [
    { id: 'vocacoes-conclusoes', label: 'Conclusões' },
    { id: 'vocacoes-retrato', label: 'Retrato' },
    { id: 'vocacoes-associacoes', label: 'Território e educação' },
    { id: 'vocacoes-pares', label: 'Simultâneas' },
    { id: 'vocacoes-triagem', label: 'Triagem' },
    { id: 'vocacoes-cenarios', label: 'Cenários' },
    ...(hasMunicipalLayer ? [{ id: 'vocacoes-municipios', label: 'Municípios' }] : []),
    { id: 'vocacoes-fontes', label: 'Fontes' },
  ]

  return (
    <nav aria-label="Seções de Vocações da Região" className="vocacoes-section-nav">
      <div className="vocacoes-section-nav__track">
        {items.map((item) => (
          <a
            href={`#${item.id}`}
            key={item.id}
            onClick={(event) => scrollToPageSection(event, item.id)}
          >
            {item.label}
          </a>
        ))}
      </div>
    </nav>
  )
}

/*
 * Exportado para o teste de renderização: é o componente que recebe o pacote já
 * validado e desenha os quatro blocos. A página pública continua sendo
 * `VocacoesRegiaoPage`, que resolve a carga antes de chegar aqui.
 */
export function VocacoesReport({ document }: { document: VocacoesDocument }) {
  const seriesById = useMemo(
    () => new Map(document.territoryPortrait.series.map((serie) => [serie.seriesId, serie])),
    [document.territoryPortrait.series],
  )
  const observedConclusionByBasis = useMemo(
    () => new Map(
      document.synthesis.items
        .filter((item) => item.kindLabel === OBSERVED_SYNTHESIS_LABEL)
        .map((item) => [item.basisLabel, item]),
    ),
    [document.synthesis.items],
  )
  const crossScenarioConclusions = useMemo(
    () => document.synthesis.items.filter((item) =>
      CROSS_SCENARIO_SYNTHESIS_LABELS.has(item.kindLabel)),
    [document.synthesis.items],
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

      <PageSectionNav hasMunicipalLayer={document.scenarios.block !== null} />

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

      <SynthesisPanel synthesis={document.synthesis} />

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
              conclusion={observedConclusionByBasis.get(
                associationSynthesisBasisLabel(association),
              )!}
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
            <TemporalPairCard
              conclusion={observedConclusionByBasis.get(pair.label)!}
              key={pair.pairId}
              pair={pair}
              series={seriesById}
            />
          ))}
        </div>
        <LaggedReadings items={document.temporalPairs.laggedItems} />
      </section>

      <ScreenedRelationsPanel
        screenedRelations={document.screenedRelations}
        series={seriesById}
      />

      <ScenariosPanel
        conclusions={crossScenarioConclusions}
        regionName={document.region.name}
        scenarios={document.scenarios}
        series={seriesById}
      />

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
