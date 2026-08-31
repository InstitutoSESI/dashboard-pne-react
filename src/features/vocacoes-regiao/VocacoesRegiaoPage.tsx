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
  VocacoesCorrelation,
  VocacoesDocument,
  VocacoesEditorialLead,
  VocacoesEnrollmentDecompositionItem,
  VocacoesFactorReading,
  VocacoesLaggedReading,
  VocacoesMunicipalLayer,
  VocacoesScenario,
  VocacoesScenarioBlock,
  VocacoesScenarios,
  VocacoesScreenedRelation,
  VocacoesSeries,
  VocacoesSeriesReference,
  VocacoesStateContrast,
  VocacoesSynthesis,
  VocacoesSynthesisItem,
  VocacoesTemporalPair,
  VocacoesTemporalReading,
  VocacoesWindow,
} from './vocacoesRegiaoTypes'
import { buildSparklineModel } from '../../utils/sparkline'
import { VocacoesPneNarrativeReport } from './VocacoesPneNarrativeReport'
import { VocacoesPneAdvancedReport } from './VocacoesPneAdvancedReport'
import { VocacoesPneOfficialReport } from './VocacoesPneOfficialReport'
import { isVocacoesPneAdvancedScopeSupported } from './vocacoesPneAdvancedContract'
import { resolveRegisteredVocacoesPneNarrative } from './vocacoesPneNarrativeRegistry.js'
import { useVocacoesPneAdvancedBundle } from './useVocacoesPneAdvancedBundle'
import { useVocacoesPneOfficialBundle } from './useVocacoesPneOfficialBundle'
import { matchesVocacoesPneOfficialPromotion } from './vocacoesPneOfficialPromotion'
import { resolveVocacoesPneSurface } from './vocacoesPneSurfaceResolution'
import type { VocacoesPneNarrativeDocument } from './vocacoesPneNarrativeTypes'
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
const correlationFormatter = new Intl.NumberFormat(ACTIVE_STATE_CONFIG.locale, {
  maximumFractionDigits: 2,
  minimumFractionDigits: 2,
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

type PublishedStatement = { readonly statement: string }

const EVIDENCE_LADDER = [
  'E1 · associação quantificada — no ar',
  'E2 · relação contábil — no ar',
  'E3 · precedência temporal — não publicado',
  'E4 · efeito estimado em painel — não publicado',
  'E5 · quase-experimento — não publicado',
] as const

const NON_SCREENED_LEAD_KINDS = new Set<VocacoesEditorialLead['kind']>([
  'structural',
  'curated_association',
  'curated_pair',
])

const STRENGTH_LEVELS: Readonly<Record<VocacoesCorrelation['strength'], number>> = Object.freeze({
  fraca: 1,
  moderada: 2,
  forte: 3,
})

function hasStatement(block: VocacoesAssociativeBlock): block is PublishedStatement {
  return 'statement' in block
}

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
  entity,
}: {
  serie: VocacoesSeries
  points?: VocacoesSeries['points']
  compact?: boolean
  entity?: 'education' | 'territory'
}) {
  const model = useMemo(
    () => buildSparklineModel(points.map((point) => ({ ano: point.period, valor: point.value }))),
    [points],
  )
  if (!model) return <span className="vocacoes-spark vocacoes-spark--empty">série curta demais para uma linha</span>
  return (
    <span
      aria-hidden="true"
      className={[
        'vocacoes-spark',
        compact ? 'vocacoes-spark--compact' : '',
        entity === undefined ? '' : `vocacoes-spark--${entity}`,
      ].filter(Boolean).join(' ')}
    >
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
  entity,
}: {
  reference: VocacoesSeriesReference
  series: ReadonlyMap<string, VocacoesSeries>
  window: VocacoesWindow
  role?: string
  entity?: 'education' | 'territory'
}) {
  const serie = series.get(reference.seriesId)
  if (serie === undefined) return null
  const inWindow = pointsInWindow(serie, window)
  const closed = inWindow.filter((point) => point.evidenceClass !== 'preliminary')
  const first = closed[0]
  const last = closed[closed.length - 1]

  return (
    <div className={`vocacoes-support${entity === undefined ? '' : ` vocacoes-support--${entity}`}`}>
      {role === undefined ? null : <p className="vocacoes-support__role">{role}</p>}
      <p className="vocacoes-support__label">{serie.label}</p>
      <SeriesSparkline compact entity={entity} points={inWindow} serie={serie} />
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

function visibleRelationStatement(
  comovement: VocacoesAssociativeBlock,
  correlation: VocacoesAssociativeBlock,
): string {
  if (hasStatement(comovement)) return comovement.statement
  if (hasStatement(correlation)) return correlation.statement
  return ABSENCE_STATEMENTS[comovement.reasonCode]
}

function StrengthBar({ correlation }: { correlation: Pick<VocacoesCorrelation, 'strength'> }) {
  const level = STRENGTH_LEVELS[correlation.strength]
  return (
    <span aria-hidden="true" className="vocacoes-strength" data-strength={correlation.strength}>
      {[1, 2, 3].map((step) => (
        <i className={step <= level ? 'is-active' : ''} key={step} />
      ))}
    </span>
  )
}

function ConcordanceSegments({
  concordant,
  intervals,
}: {
  concordant: number
  intervals: number
}) {
  return (
    <span aria-hidden="true" className="vocacoes-concordance">
      {Array.from({ length: intervals }, (_, index) => (
        <i className={index < concordant ? 'is-active' : ''} key={index} />
      ))}
    </span>
  )
}

function RankStrip({ contrast }: { contrast: VocacoesStateContrast }) {
  return (
    <span aria-hidden="true" className="vocacoes-rank-strip">
      {Array.from({ length: contrast.totalComparable }, (_, index) => (
        <i className={index + 1 === contrast.rank ? 'is-current' : ''} key={index} />
      ))}
    </span>
  )
}

function RelationFacts({
  correlation,
  directionConcordance,
  stateContrast,
}: {
  correlation: VocacoesFactorReading['correlation']
  directionConcordance: VocacoesFactorReading['directionConcordance']
  stateContrast: VocacoesAssociationReading['stateContrast']
}) {
  return (
    <div className="vocacoes-relation-facts">
      {hasStatement(correlation) ? (
        <span className="vocacoes-relation-fact">
          <span className="vocacoes-relation-fact__label">Pearson</span>
          <StrengthBar correlation={correlation} />
          <strong>{correlationFormatter.format(correlation.pearsonDelta)}</strong>
          <span>{correlation.strength}</span>
        </span>
      ) : null}
      {hasStatement(directionConcordance) ? (
        <span className="vocacoes-relation-fact">
          <span className="vocacoes-relation-fact__label">Concordância</span>
          <ConcordanceSegments
            concordant={directionConcordance.concordant}
            intervals={directionConcordance.intervals}
          />
          <strong>{`${directionConcordance.concordant} de ${directionConcordance.intervals}`}</strong>
        </span>
      ) : null}
      {hasStatement(stateContrast) ? (
        <span className="vocacoes-relation-fact">
          <span className="vocacoes-relation-fact__label">Entre as regiões</span>
          <RankStrip contrast={stateContrast} />
          <strong>{`${stateContrast.rank}ª de ${stateContrast.totalComparable}`}</strong>
        </span>
      ) : null}
    </div>
  )
}

function HeroPanel({
  document,
  series,
}: {
  document: VocacoesDocument
  series: ReadonlyMap<string, VocacoesSeries>
}) {
  return (
    <section aria-labelledby="vocacoes-hero-title" className="vocacoes-hero" id="vocacoes-hero">
      <div className="vocacoes-hero__copy">
        <h2 id="vocacoes-hero-title">{document.hero.title}</h2>
        <p>{document.hero.lede}</p>
      </div>

      <div className="vocacoes-hero-tiles">
        {document.hero.tiles.map((tile) => {
          const serie = series.get(tile.seriesId)
          const points = serie === undefined
            ? []
            : pointsInWindow(serie, tile.window)
              .filter((point) => point.evidenceClass !== 'preliminary')
          return (
            <article
              aria-label={`${tile.label}: ${tile.valueStatement}. ${tile.deltaStatement}`}
              className={`vocacoes-hero-tile vocacoes-hero-tile--${tile.entity}`}
              data-tile-id={tile.tileId}
              key={tile.tileId}
            >
              <p className="vocacoes-hero-tile__label">
                <i aria-hidden="true" />
                {tile.label}
              </p>
              <p className="vocacoes-hero-tile__value">{tile.valueStatement}</p>
              <p className="vocacoes-hero-tile__delta">{tile.deltaStatement}</p>
              {serie === undefined ? null : (
                <SeriesSparkline compact entity={tile.entity} points={points} serie={serie} />
              )}
              {tile.contrastStatement === null ? null : (
                <p className="vocacoes-hero-tile__contrast">{tile.contrastStatement}</p>
              )}
            </article>
          )
        })}
      </div>

      <p className="vocacoes-neutrality vocacoes-hero__neutrality">
        {document.page.neutralityNote}
      </p>
      <p className="vocacoes-hero__method">{document.hero.methodNote}</p>
    </section>
  )
}

function EvidenceLadder() {
  return (
    <aside aria-label="Grau de evidência das leituras" className="vocacoes-evidence-ladder">
      <strong>Grau de evidência das leituras:</strong>
      <div className="vocacoes-evidence-ladder__steps">
        {EVIDENCE_LADDER.map((step, index) => (
          <span
            className={index < 2 ? 'is-published' : 'is-unpublished'}
            key={step}
          >
            {step}
          </span>
        ))}
      </div>
      <p>
        Cada leitura carrega o grau mais alto que o dado sustenta. Nada nesta página afirma causa além do grau declarado.
      </p>
    </aside>
  )
}

function AnalysisGuard({ claim }: { claim: string }) {
  return (
    <div className="vocacoes-prohibited">
      <span className="vocacoes-prohibited__mark">Nota metodológica — o que não se conclui</span>
      <p>{claim}</p>
    </div>
  )
}

function AssociationLeadCard({
  association,
  conclusion,
  factorReading,
  series,
  storyTitle,
}: {
  association: VocacoesAssociation
  conclusion: VocacoesSynthesisItem
  factorReading: VocacoesFactorReading
  series: ReadonlyMap<string, VocacoesSeries>
  storyTitle: string
}) {
  const factor = association.territorialFactors.find(
    (candidate) => candidate.seriesId === factorReading.factorSeriesId,
  )
  if (factor === undefined) return null

  return (
    <article className="vocacoes-card vocacoes-relation-card" data-lead-kind="curated_association">
      <header className="vocacoes-relation-card__head">
        <h3>{storyTitle}</h3>
        <span className="vocacoes-grade">E1 · associação</span>
      </header>
      <p className="vocacoes-relation-card__reading">
        {visibleRelationStatement(factorReading.comovement, factorReading.correlation)}
      </p>
      <div className="vocacoes-supports vocacoes-supports--paired">
        <SupportingSeries
          entity="territory"
          reference={factor}
          series={series}
          window={association.window}
        />
        <SupportingSeries
          entity="education"
          reference={association.educationOutcome}
          series={series}
          window={association.window}
        />
      </div>
      <RelationFacts
        correlation={factorReading.correlation}
        directionConcordance={factorReading.directionConcordance}
        stateContrast={association.associativeReading.stateContrast}
      />
      <details className="vocacoes-analysis-detail">
        <summary>Análise completa — hipóteses, método e o que não se conclui</summary>
        <div className="vocacoes-analysis-detail__body">
          {association.associativeReading.factorReadings.map((reading) => (
            <div
              className="vocacoes-associative-reading__factor"
              key={`${reading.outcomeSeriesId}:${reading.factorSeriesId}`}
            >
              <AssociativeStatement block={reading.correlation} />
              <AssociativeStatement block={reading.directionConcordance} />
              <AssociativeStatement block={reading.comovement} />
            </div>
          ))}
          <AssociativeStatement block={association.associativeReading.stateContrast} />
          <ConclusionVerdict item={conclusion} />
          <p className="vocacoes-allowed">
            <span className="vocacoes-allowed__mark">O que se pode ler</span>
            {association.allowedInterpretation}
          </p>
          <p className="vocacoes-card__statement">{association.observedStatement}</p>
          <ul className="vocacoes-list">
            {association.hypotheses.map((hypothesis) => <li key={hypothesis}>{hypothesis}</li>)}
          </ul>
          <p>{association.associativeReading.methodNote}</p>
          <AnalysisGuard claim={association.prohibitedClaim} />
        </div>
      </details>
    </article>
  )
}

function PairLeadCard({
  conclusion,
  pair,
  series,
  storyTitle,
}: {
  conclusion: VocacoesSynthesisItem
  pair: VocacoesTemporalPair
  series: ReadonlyMap<string, VocacoesSeries>
  storyTitle: string
}) {
  const reading = pair.associativeReading
  return (
    <article className="vocacoes-card vocacoes-relation-card" data-lead-kind="curated_pair">
      <header className="vocacoes-relation-card__head">
        <h3>{storyTitle}</h3>
        <span className="vocacoes-grade">E1 · associação</span>
      </header>
      <p className="vocacoes-relation-card__reading">
        {visibleRelationStatement(reading.comovement, reading.correlation)}
      </p>
      <div className="vocacoes-supports vocacoes-supports--paired">
        <SupportingSeries
          entity="territory"
          reference={pair.seriesA}
          series={series}
          window={pair.window}
        />
        <SupportingSeries
          entity="education"
          reference={pair.seriesB}
          series={series}
          window={pair.window}
        />
      </div>
      <RelationFacts
        correlation={reading.correlation}
        directionConcordance={reading.directionConcordance}
        stateContrast={reading.stateContrast}
      />
      <details className="vocacoes-analysis-detail">
        <summary>Análise completa — hipóteses, método e o que não se conclui</summary>
        <div className="vocacoes-analysis-detail__body">
          <AssociativeStatement block={reading.correlation} />
          <AssociativeStatement block={reading.directionConcordance} />
          <AssociativeStatement block={reading.comovement} />
          <AssociativeStatement block={reading.stateContrast} />
          <ConclusionVerdict item={conclusion} />
          <p className="vocacoes-card__statement">{pair.observedStatement}</p>
          <p>{reading.methodNote}</p>
          <AnalysisGuard claim={pair.prohibitedClaim} />
        </div>
      </details>
    </article>
  )
}

function StructuralLeadCard({
  reading,
  series,
  storyTitle,
}: {
  reading: VocacoesLaggedReading
  series: ReadonlyMap<string, VocacoesSeries>
  storyTitle: string
}) {
  const first = series.get(reading.aSeriesId)
  const second = series.get(reading.bSeriesId)
  return (
    <article className="vocacoes-card vocacoes-relation-card" data-lead-kind="structural">
      <header className="vocacoes-relation-card__head">
        <h3>{storyTitle}</h3>
        <span className="vocacoes-grade">E1 · defasagem declarada</span>
      </header>
      <p className="vocacoes-relation-card__reading">{reading.statement}</p>
      <div className="vocacoes-supports vocacoes-supports--paired">
        {first === undefined ? null : (
          <SupportingSeries
            entity="territory"
            reference={{ label: first.label, seriesId: first.seriesId }}
            series={series}
            window={reading.windowA}
          />
        )}
        {second === undefined ? null : (
          <SupportingSeries
            entity="education"
            reference={{ label: second.label, seriesId: second.seriesId }}
            series={series}
            window={reading.windowB}
          />
        )}
      </div>
      <div className="vocacoes-relation-facts">
        <span className="vocacoes-relation-fact">
          <span className="vocacoes-relation-fact__label">Defasagem</span>
          <strong>{`${reading.lagYears} anos`}</strong>
        </span>
        <span className="vocacoes-relation-fact">
          <span className="vocacoes-relation-fact__label">Concordância</span>
          <ConcordanceSegments concordant={reading.concordant} intervals={reading.intervals} />
          <strong>{`${reading.concordant} de ${reading.intervals}`}</strong>
        </span>
        {'reasonCode' in reading.correlation ? null : (
          <span className="vocacoes-relation-fact">
            <span className="vocacoes-relation-fact__label">Pearson</span>
            <StrengthBar correlation={reading.correlation} />
            <strong>{correlationFormatter.format(reading.correlation.pearsonDelta)}</strong>
            <span>{reading.correlation.strength}</span>
          </span>
        )}
      </div>
      <details className="vocacoes-analysis-detail">
        <summary>Análise completa — hipóteses, método e o que não se conclui</summary>
        <div className="vocacoes-analysis-detail__body">
          <p>{reading.statement}</p>
          <p>{reading.rationale}</p>
        </div>
      </details>
    </article>
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
    <section aria-labelledby="vocacoes-conclusoes-title" className="vocacoes-panel vocacoes-synthesis">
      <div className="vocacoes-panel__head">
        <h2 className="vocacoes-panel__title" id="vocacoes-conclusoes-title">{synthesis.label}</h2>
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

function EditorialLeadCard({
  document,
  lead,
  observedConclusionByBasis,
  series,
}: {
  document: VocacoesDocument
  lead: VocacoesEditorialLead
  observedConclusionByBasis: ReadonlyMap<string | undefined, VocacoesSynthesisItem>
  series: ReadonlyMap<string, VocacoesSeries>
}) {
  if (lead.kind === 'screened') return null
  if (lead.kind === 'structural') {
    const reading = document.temporalPairs.laggedItems.find((item) => (
      'rationale' in item
      && item.aSeriesId === lead.aSeriesId
      && item.bSeriesId === lead.bSeriesId
      && item.lagYears === lead.lagYears
    ))
    return reading === undefined || !('rationale' in reading) ? null : (
      <StructuralLeadCard reading={reading} series={series} storyTitle={lead.storyTitle} />
    )
  }
  if (lead.kind === 'curated_association') {
    const association = document.associations.items.find(
      (item) => item.associationId === lead.associationId,
    )
    const factorReading = association?.associativeReading.factorReadings.find(
      (reading) => reading.factorSeriesId === lead.factorSeriesId,
    )
    const conclusion = association === undefined
      ? undefined
      : observedConclusionByBasis.get(associationSynthesisBasisLabel(association))
    return association === undefined || factorReading === undefined || conclusion === undefined
      ? null
      : (
        <AssociationLeadCard
          association={association}
          conclusion={conclusion}
          factorReading={factorReading}
          series={series}
          storyTitle={lead.storyTitle}
        />
      )
  }
  const pair = document.temporalPairs.items.find((item) => item.pairId === lead.pairId)
  const conclusion = pair === undefined ? undefined : observedConclusionByBasis.get(pair.label)
  return pair === undefined || conclusion === undefined ? null : (
    <PairLeadCard
      conclusion={conclusion}
      pair={pair}
      series={series}
      storyTitle={lead.storyTitle}
    />
  )
}

function SupportingReadingsArchive({
  document,
  observedConclusionByBasis,
  series,
}: {
  document: VocacoesDocument
  observedConclusionByBasis: ReadonlyMap<string | undefined, VocacoesSynthesisItem>
  series: ReadonlyMap<string, VocacoesSeries>
}) {
  const associationIds = new Set(
    document.editorialReading.leads
      .filter((lead) => lead.kind === 'curated_association')
      .map((lead) => lead.associationId),
  )
  const pairIds = new Set(
    document.editorialReading.leads
      .filter((lead) => lead.kind === 'curated_pair')
      .map((lead) => lead.pairId),
  )
  const structuralKeys = new Set(
    document.editorialReading.leads
      .filter((lead) => lead.kind === 'structural')
      .map((lead) => `${lead.aSeriesId}:${lead.bSeriesId}:${lead.lagYears}`),
  )
  const associations = document.associations.items.filter(
    (association) => !associationIds.has(association.associationId),
  )
  const pairs = document.temporalPairs.items.filter((pair) => !pairIds.has(pair.pairId))
  const laggedItems = document.temporalPairs.laggedItems.filter((item) => (
    !structuralKeys.has(`${item.aSeriesId}:${item.bSeriesId}:${item.lagYears}`)
  ))

  return (
    <div className="vocacoes-supporting-archive">
      {associations.length === 0 ? null : (
        <details>
          <summary>{document.associations.label}</summary>
          <p>{document.associations.description}</p>
          <div className="vocacoes-card-stack">
            {associations.map((association) => (
              <AssociationCard
                association={association}
                conclusion={observedConclusionByBasis.get(
                  associationSynthesisBasisLabel(association),
                )!}
                key={association.associationId}
                series={series}
              />
            ))}
          </div>
        </details>
      )}
      {pairs.length === 0 && laggedItems.length === 0 ? null : (
        <details>
          <summary>{document.temporalPairs.label}</summary>
          <p>{document.temporalPairs.description}</p>
          <div className="vocacoes-card-stack">
            {pairs.map((pair) => (
              <TemporalPairCard
                conclusion={observedConclusionByBasis.get(pair.label)!}
                key={pair.pairId}
                pair={pair}
                series={series}
              />
            ))}
          </div>
          <LaggedReadings items={laggedItems} />
        </details>
      )}
    </div>
  )
}

function proportionalWidths(values: readonly number[]): number[] {
  const total = values.reduce((sum, value) => sum + Math.abs(value), 0)
  return values.map((value) => total === 0 ? 0 : Math.abs(value) / total * 100)
}

function DecompositionBar({
  terms,
}: {
  terms: readonly {
    readonly className: string
    readonly label: string
    readonly value: number
  }[]
}) {
  const widths = proportionalWidths(terms.map((term) => term.value))
  return (
    <div className="vocacoes-decomposition">
      <div aria-hidden="true" className="vocacoes-decomposition__bar">
        {terms.map((term, index) => (
          <i
            className={term.className}
            key={term.label}
            style={{ width: `${widths[index]}%` }}
          />
        ))}
      </div>
      <div className="vocacoes-decomposition__legend">
        {terms.map((term) => (
          <span key={term.label}>
            <i aria-hidden="true" className={term.className} />
            {term.label}
            <strong>{`${formatValue(term.value)} p.p.`}</strong>
          </span>
        ))}
      </div>
    </div>
  )
}

function EnrollmentDecompositionCard({
  item,
  methodStatement,
  series,
}: {
  item: VocacoesEnrollmentDecompositionItem
  methodStatement: string
  series: ReadonlyMap<string, VocacoesSeries>
}) {
  const outcome = series.get(item.outcomeSeriesId)
  const cohort = series.get(item.cohortSeriesId)
  const terms = [
    {
      className: 'is-territory',
      label: cohort?.label ?? item.stageLabel,
      value: item.contributions.demographicPp,
    },
    {
      className: 'is-education',
      label: outcome?.label ?? item.stageLabel,
      value: item.contributions.ratioPp,
    },
  ]
  return (
    <article className="vocacoes-e2-card">
      <header className="vocacoes-relation-card__head">
        <h4>{item.stageLabel}</h4>
        <span className="vocacoes-grade vocacoes-grade--e2">E2 · relação contábil</span>
      </header>
      <p>{item.statement}</p>
      <DecompositionBar terms={terms} />
      <details className="vocacoes-analysis-detail">
        <summary>{item.stageLabel}</summary>
        <p>{methodStatement}</p>
        <dl className="vocacoes-meta">
          <div>
            <dt>{outcome?.label ?? item.stageLabel}</dt>
            <dd>{`${formatValue(item.terms.enrollmentStart)} → ${formatValue(item.terms.enrollmentEnd)}`}</dd>
          </div>
          <div>
            <dt>{cohort?.label ?? item.stageLabel}</dt>
            <dd>{`${formatValue(item.terms.cohortStart)} → ${formatValue(item.terms.cohortEnd)}`}</dd>
          </div>
          <div>
            <dt>Taxa de atendimento aparente</dt>
            <dd>{`${formatValue(item.terms.ratioStartPerHundred)} → ${formatValue(item.terms.ratioEndPerHundred)}`}</dd>
          </div>
        </dl>
      </details>
    </article>
  )
}

function EmploymentDecompositionCard({
  document,
}: {
  document: VocacoesDocument
}) {
  const item = document.decompositions.employment.item
  if (item === null) return null
  const terms = [
    {
      className: 'is-territory',
      label: 'ritmo comum do estado',
      value: item.contributions.statePp,
    },
    {
      className: 'is-territory-soft',
      label: 'composição setorial de partida',
      value: item.contributions.mixPp,
    },
    {
      className: 'is-territory-deep',
      label: 'dinâmica própria dos setores',
      value: item.contributions.ownPp,
    },
  ]
  return (
    <article className="vocacoes-e2-card">
      <header className="vocacoes-relation-card__head">
        <h4>{item.sourceLabel}</h4>
        <span className="vocacoes-grade vocacoes-grade--e2">E2 · relação contábil</span>
      </header>
      <p>{item.statement}</p>
      <DecompositionBar terms={terms} />
      <details className="vocacoes-analysis-detail">
        <summary>{item.sourceLabel}</summary>
        <p>{document.decompositions.employment.methodStatement}</p>
        <dl className="vocacoes-meta">
          <div>
            <dt>{item.sourceLabel}</dt>
            <dd>{`${formatValue(item.totals.regionStart)} → ${formatValue(item.totals.regionEnd)}`}</dd>
          </div>
          <div>
            <dt>{document.decompositions.employment.criteria.reference}</dt>
            <dd>{`${formatValue(item.totals.stateStart)} → ${formatValue(item.totals.stateEnd)}`}</dd>
          </div>
        </dl>
        <div className="vocacoes-table-scroll">
          <table className="vocacoes-table">
            <thead>
              <tr>
                <th scope="col">Setor</th>
                <th scope="col">Região</th>
                <th scope="col">Estado</th>
              </tr>
            </thead>
            <tbody>
              {item.sectors.map((sector) => (
                <tr key={sector.sectorLabel}>
                  <th scope="row">{sector.sectorLabel}</th>
                  <td>{`${formatValue(sector.regionStart)} → ${formatValue(sector.regionEnd)}`}</td>
                  <td>{`${formatValue(sector.stateStart)} → ${formatValue(sector.stateEnd)}`}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </article>
  )
}

function DecompositionsPanel({
  document,
  series,
}: {
  document: VocacoesDocument
  series: ReadonlyMap<string, VocacoesSeries>
}) {
  const { decompositions } = document
  return (
    <section aria-labelledby="vocacoes-e2-title" className="vocacoes-e2" id="vocacoes-e2">
      <header className="vocacoes-section__head">
        <p className="vocacoes-section__kicker">Relação contábil · grau E2</p>
        <h3 id="vocacoes-e2-title">{decompositions.label}</h3>
        <p>{decompositions.description}</p>
      </header>
      <div className="vocacoes-e2__grid">
        {decompositions.enrollment.items.map((item) => (
          <EnrollmentDecompositionCard
            item={item}
            key={item.stage}
            methodStatement={decompositions.enrollment.methodStatement}
            series={series}
          />
        ))}
        <EmploymentDecompositionCard document={document} />
      </div>
      <div className="vocacoes-e2__absences">
        {decompositions.enrollment.absences.map((absence) => (
          <p key={absence.stage}>{absence.statement}</p>
        ))}
        {decompositions.employment.absence === null ? null : (
          <p>{decompositions.employment.absence.statement}</p>
        )}
      </div>
    </section>
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

function ScreenedRelationRow({
  relation,
  series,
}: {
  relation: VocacoesScreenedRelation
  series: ReadonlyMap<string, VocacoesSeries>
}) {
  const correlation = hasStatement(relation.correlation) ? relation.correlation : null
  return (
    <details className="vocacoes-screened-row">
      <summary>
        <span className="vocacoes-screened-row__pair">
          <strong>{series.get(relation.seriesAId)?.label}</strong>
          {' × '}
          <span>{series.get(relation.seriesBId)?.label}</span>
        </span>
        {correlation === null ? null : (
          <>
            <span className="vocacoes-screened-row__correlation">
              {`r = ${correlationFormatter.format(correlation.pearsonDelta)} · ${correlation.strength}`}
            </span>
            <StrengthBar correlation={correlation} />
          </>
        )}
      </summary>
      <div className="vocacoes-screened-row__detail">
        <p>{relation.originStatement}</p>
        <AssociativeStatement block={relation.correlation} />
        <AssociativeStatement block={relation.directionConcordance} />
        <AssociativeStatement block={relation.comovement} />
      </div>
    </details>
  )
}

function ScreenedRelationsPanel({
  document,
  series,
}: {
  document: VocacoesDocument
  series: ReadonlyMap<string, VocacoesSeries>
}) {
  const { screenedRelations } = document
  return (
    <section aria-labelledby="vocacoes-triagem" className="vocacoes-section vocacoes-screening">
      <header className="vocacoes-section__head">
        <p className="vocacoes-section__kicker">Varredura automática</p>
        <h2 id="vocacoes-triagem">
          Relações que a triagem encontrou
          <span className="u-sr-only"> · {screenedRelations.label}</span>
        </h2>
      </header>

      <div className="vocacoes-screened-relations">
        {screenedRelations.items.map((relation) => (
          <ScreenedRelationRow key={relation.relationId} relation={relation} series={series} />
        ))}
      </div>

      <details className="vocacoes-screening__method">
        <summary>{screenedRelations.description}</summary>
        <p>{document.editorialReading.criteriaStatement}</p>
        <p>{document.editorialReading.noteStatement}</p>
        <p>{screenedRelations.methodNote}</p>
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
  absenceThemes,
  conclusions,
  scenarios,
  series,
  regionName,
}: {
  absenceThemes: readonly string[]
  conclusions: readonly VocacoesSynthesisItem[]
  scenarios: VocacoesScenarios
  series: Map<string, VocacoesSeries>
  regionName: string
}) {
  const block = scenarios.block

  return (
    <section aria-labelledby="vocacoes-cenarios" className="vocacoes-section vocacoes-p2">
      <header className="vocacoes-section__head">
        <p className="vocacoes-section__kicker vocacoes-section__kicker--territory">
          Pergunta 2 · Território → Educação
        </p>
        <h2 id="vocacoes-cenarios">O que o futuro do território pede da educação?</h2>
        <p className="vocacoes-section__document-label">{scenarios.label}</p>
        <p className="vocacoes-panel__text">{scenarios.description}</p>
      </header>

      {/*
        * A região sem cenário não recebe seção vazia nem seção escondida: recebe
        * a frase que diz que não há cenário aqui. Esconder a seção faria a
        * ausência parecer um bloco que se perdeu no caminho; deixá-la vazia
        * faria parecer um erro de carregamento.
        */}
      {block === null ? (
        <>
          <p className="vocacoes-scenarios__absence">{scenarios.absenceStatement}</p>
          <div className="vocacoes-scenarios__themes">
            {absenceThemes.map((theme) => (
              <span className="vocacoes-chip vocacoes-chip--theme" key={theme}>{theme}</span>
            ))}
          </div>
        </>
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
    <section aria-labelledby="vocacoes-retrato-title" className="vocacoes-panel">
      <div className="vocacoes-panel__head">
        <h2 className="vocacoes-panel__title" id="vocacoes-retrato-title">
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

function editorialLeadKey(lead: VocacoesEditorialLead): string {
  if (lead.kind === 'structural') {
    return `${lead.kind}:${lead.aSeriesId}:${lead.bSeriesId}:${lead.lagYears}`
  }
  if (lead.kind === 'curated_association') {
    return `${lead.kind}:${lead.associationId}:${lead.factorSeriesId}`
  }
  if (lead.kind === 'curated_pair') return `${lead.kind}:${lead.pairId}`
  return `${lead.kind}:${lead.relationId}`
}

function leadThemes(document: VocacoesDocument, lead: VocacoesEditorialLead) {
  if (lead.kind === 'structural') {
    const reading = document.temporalPairs.laggedItems.find((item) => (
      'pneThemes' in item
      && item.aSeriesId === lead.aSeriesId
      && item.bSeriesId === lead.bSeriesId
      && item.lagYears === lead.lagYears
    ))
    return reading !== undefined && 'pneThemes' in reading ? reading.pneThemes : []
  }
  if (lead.kind === 'curated_association') {
    return document.associations.items.find(
      (association) => association.associationId === lead.associationId,
    )?.pneThemes ?? []
  }
  if (lead.kind === 'curated_pair') {
    return document.temporalPairs.items.find((pair) => pair.pairId === lead.pairId)?.pneThemes ?? []
  }
  return []
}

function PageSectionNav({ hasMunicipalLayer }: { hasMunicipalLayer: boolean }) {
  const items = [
    { id: 'vocacoes-hero', label: 'Síntese' },
    { id: 'vocacoes-p1', label: 'Pergunta 1' },
    { id: 'vocacoes-e2', label: 'E2' },
    { id: 'vocacoes-triagem', label: 'Triagem' },
    { id: 'vocacoes-cenarios', label: 'Pergunta 2' },
    ...(hasMunicipalLayer ? [{ id: 'vocacoes-municipios', label: 'Municípios' }] : []),
    { id: 'vocacoes-conclusoes', label: 'Conclusões' },
    { id: 'vocacoes-retrato', label: 'Retrato' },
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
  const visibleLeads = useMemo(
    () => document.editorialReading.leads.filter((lead) => (
      NON_SCREENED_LEAD_KINDS.has(lead.kind)
    )),
    [document.editorialReading.leads],
  )
  const absenceThemes = useMemo(() => {
    const themes: string[] = []
    const seen = new Set<string>()
    for (const lead of visibleLeads) {
      for (const theme of leadThemes(document, lead)) {
        if (seen.has(theme.theme)) continue
        seen.add(theme.theme)
        themes.push(theme.themeLabel)
      }
    }
    return themes
  }, [document, visibleLeads])

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

      <HeroPanel document={document} series={seriesById} />

      <EvidenceLadder />

      <section aria-labelledby="vocacoes-p1-title" className="vocacoes-section vocacoes-p1" id="vocacoes-p1">
        <header className="vocacoes-section__head">
          <p className="vocacoes-section__kicker">Pergunta 1 · Educação × Território</p>
          <h2 id="vocacoes-p1-title">O que anda junto com a educação no território?</h2>
          <p>
            As relações mais fortes desta região, na ordem da força medida. Em cada cartão: as duas séries lado a lado, a força do co-movimento e a posição da região entre as 10 do estado. A análise completa — hipóteses, método e o que não se conclui — abre sob demanda.
          </p>
        </header>

        <div className="vocacoes-relations-grid">
          {visibleLeads.map((lead) => (
            <EditorialLeadCard
              document={document}
              key={editorialLeadKey(lead)}
              lead={lead}
              observedConclusionByBasis={observedConclusionByBasis}
              series={seriesById}
            />
          ))}
        </div>

        <SupportingReadingsArchive
          document={document}
          observedConclusionByBasis={observedConclusionByBasis}
          series={seriesById}
        />

        <DecompositionsPanel document={document} series={seriesById} />
      </section>

      <ScreenedRelationsPanel
        document={document}
        series={seriesById}
      />

      <ScenariosPanel
        absenceThemes={absenceThemes}
        conclusions={crossScenarioConclusions}
        regionName={document.region.name}
        scenarios={document.scenarios}
        series={seriesById}
      />

      <details className="vocacoes-consultation" id="vocacoes-conclusoes">
        <summary>{document.synthesis.label}</summary>
        <div className="vocacoes-consultation__body">
          <SynthesisPanel synthesis={document.synthesis} />
        </div>
      </details>

      <details className="vocacoes-consultation" id="vocacoes-retrato">
        <summary>Explorar as séries do território</summary>
        <div className="vocacoes-consultation__body">
          <TerritoryPortrait document={document} />
        </div>
      </details>

      <footer className="vocacoes-footer" id="vocacoes-fontes">
        <section className="vocacoes-footer__panel">
          <h2>Fontes</h2>
          <p>{document.sources.description}</p>
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

        <section className="vocacoes-footer__panel">
          <h2>Como ler · o que não se conclui</h2>
          <p>{document.howToRead.description}</p>
          <details>
            <summary>{document.howToRead.label}</summary>
            <ul className="vocacoes-list">
              {document.howToRead.items.map((item) => <li key={item}>{item}</li>)}
            </ul>
            <h3>{document.limitations.label}</h3>
            <p>{document.limitations.description}</p>
            <ul className="vocacoes-list">
              {document.limitations.items.map((item) => <li key={item}>{item}</li>)}
            </ul>
          </details>
        </section>
      </footer>
    </div>
  )
}

export function VocacoesRegiaoPage({
  municipalityId,
}: {
  municipalityId: string | null
}) {
  const { data, loading } = useVocacoesRegiao(municipalityId)
  const officialPromotionEligible = data !== null
    && data !== undefined
    && matchesVocacoesPneOfficialPromotion(data.document, ACTIVE_STATE_CONFIG.stateCode)
    && resolveVocacoesPneNarrative(data.document) !== null
  const advancedScopeRequested = officialPromotionEligible
    && isVocacoesPneAdvancedScopeSupported(municipalityId)
  const advancedBundle = useVocacoesPneAdvancedBundle(advancedScopeRequested)
  const officialBundle = useVocacoesPneOfficialBundle(officialPromotionEligible)

  const advancedScopeSupported = advancedBundle.status === 'ready'
    && (municipalityId === null
      || (municipalityId === '4313375'
        && advancedBundle.data.region.advancedMunicipalityIbgeCodes.includes(municipalityId)))
  const officialScopeSupported = officialBundle.status === 'ready'
    && (municipalityId === null
      || officialBundle.data.core.municipalities.some((item) => item.ibgeCode === municipalityId))
  const selectedSurface = resolveVocacoesPneSurface({
    eligible: officialPromotionEligible,
    advancedRequested: advancedScopeRequested,
    advancedStatus: advancedBundle.status,
    advancedScopeSupported,
    officialStatus: officialBundle.status,
    officialScopeSupported,
  })

  if (loading) {
    return <LoadingState message="Carregando as vocações da região…" />
  }

  /*
   * Quem decide a visibilidade é o roteador, a partir do manifesto. Chegar
   * aqui sem pacote significa falha de integridade, e nesse caso não há o que
   * apresentar.
   */
  if (!data) return null

  if (selectedSurface === 'loading') {
    return <LoadingState message="Preparando a leitura integrada de educação e território…" />
  }

  if (selectedSurface === 'advanced' && advancedBundle.status === 'ready') {
    return (
      <VocacoesPneAdvancedReport
        bundle={advancedBundle.data}
        municipalityId={municipalityId}
      />
    )
  }

  if (selectedSurface === 'official_previous' && officialBundle.status === 'ready') {
    return (
      <VocacoesPneOfficialReport
        advancedScopeNotice={municipalityId !== null && !isVocacoesPneAdvancedScopeSupported(municipalityId)}
        bundle={officialBundle.data}
        legacyDocument={data.document}
        municipalityId={municipalityId}
      />
    )
  }

  // Resolução fail-closed: pacote avançado, página oficial anterior e, por fim,
  // relatório narrativo/legado. Falhas nunca produzem uma rota parcialmente vazia.
  return <VocacoesResolvedReport legacyDocument={data.document} />
}

export function resolveVocacoesPneNarrative(
  legacyDocument: VocacoesDocument,
): VocacoesPneNarrativeDocument | null {
  return resolveRegisteredVocacoesPneNarrative(
    legacyDocument,
    ACTIVE_STATE_CONFIG.stateCode,
  ) as VocacoesPneNarrativeDocument | null
}

export const resolveVocacoesPneNarrativePilot = resolveVocacoesPneNarrative

export function VocacoesResolvedReport({
  legacyDocument,
}: {
  legacyDocument: VocacoesDocument
}) {
  const narrative = resolveVocacoesPneNarrative(legacyDocument)
  if (narrative === null) return <VocacoesReport document={legacyDocument} />
  return (
    <VocacoesPneNarrativeReport
      legacyDocument={legacyDocument}
      narrative={narrative}
    />
  )
}
