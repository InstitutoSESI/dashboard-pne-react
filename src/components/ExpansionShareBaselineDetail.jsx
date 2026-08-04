import { ArrowRight } from 'lucide-react'
import { DisclosureChevron } from './DisclosureChevron'
import { QuickReadingHeading } from './QuickReadingHeading'
import { selectPneYearTicks } from '../utils/pneChartSystem'

const countFormatter = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 0 })
const percentFormatter = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 1 })

export function ExpansionShareBaselineAnalysis({ model }) {
  const data = model.composition

  return (
    <section className="expansion-share-analysis" aria-labelledby="expansion-share-analysis-title">
      <header className="expansion-share-analysis__header">
        <div>
          <span className="eyebrow">Leitura do período</span>
          <h3 id="expansion-share-analysis-title">O que aconteceu no período</h3>
          <p>Comparação entre o primeiro e o último ano do recorte disponível.</p>
        </div>
        <span className="expansion-share-analysis__period">{data.period ?? 'Período indisponível'}</span>
      </header>

      <div className="expansion-before-after-grid">
        <BeforeAfterCard
          change={data.publicExpansion}
          changePercent={data.publicChangePercent}
          endValue={data.publicEnd}
          label="Matrículas públicas"
          startValue={data.publicStart}
          years={`${data.startYear ?? '—'} → ${data.endYear ?? '—'}`}
        />
        <BeforeAfterCard
          change={data.totalExpansion}
          changePercent={data.totalChangePercent}
          endValue={data.totalEnd}
          label="Total de matrículas da EPT"
          startValue={data.totalStart}
          years={`${data.startYear ?? '—'} → ${data.endYear ?? '—'}`}
        />
      </div>

      <section className="expansion-explanation" aria-labelledby="expansion-explanation-title">
        <span className="eyebrow">Como interpretar</span>
        <h4 id="expansion-explanation-title">{getExplanationTitle(data)}</h4>
        <p>{data.interpretation}</p>
        <div className="expansion-explanation__result">
          <span>Participação pública calculada</span>
          <strong>{formatPercent(data.currentValue)}</strong>
        </div>
      </section>

      <section className="expansion-reference" aria-labelledby="expansion-reference-title">
        <div>
          <span className="eyebrow">Referência para o novo ciclo</span>
          <h4 id="expansion-reference-title">Pelo menos 50% da expansão deve ocorrer no segmento público</h4>
          <p>{data.distanceNarrative} O recorte apresentado é anterior ao início do acompanhamento do PNE 2026–2036.</p>
        </div>
        <div className="expansion-reference__values">
          <span><small>Resultado</small><strong>{formatPercent(data.currentValue)}</strong></span>
          <span><small>Referência</small><strong>50%</strong></span>
          <span><small>Distância</small><strong>{formatDistance(data.currentValue, data.targetValue)}</strong></span>
        </div>
        <span className={`expansion-reference__seal expansion-reference__seal--${getResultState(data.currentValue)}`}>
          {getResultStateLabel(data.currentValue)}
        </span>
      </section>
    </section>
  )
}

function BeforeAfterCard({ change, changePercent, endValue, label, startValue, years }) {
  const isNegative = Number(change) < 0
  return (
    <article className="expansion-before-after-card">
      <header><span>{label}</span><small>{years}</small></header>
      <div className="expansion-before-after-card__values">
        <strong>{formatCount(startValue)}</strong><ArrowRight aria-hidden="true" size={18} /><strong>{formatCount(endValue)}</strong>
      </div>
      <p className={isNegative ? 'is-negative' : 'is-positive'}>
        {formatSignedCount(change)} · {formatChangeLabel(changePercent)}
      </p>
    </article>
  )
}

export function ExpansionShareQuickReading({ model }) {
  const data = model.composition
  return (
    <aside className="indicator-quick-reading expansion-share-reading" aria-label="Leitura rápida do indicador">
      <QuickReadingHeading />
      <dl>
        <div><dt>O que mudou</dt><dd>{formatSignedCount(data.publicExpansion)} na rede pública e {formatSignedCount(data.totalExpansion)} no total da EPT.</dd></div>
        <div><dt>O que significa</dt><dd>{getShortMeaning(data)}</dd></div>
        <div><dt>Resultado</dt><dd><strong>{formatPercent(data.currentValue)}</strong> da expansão acumulada.</dd></div>
        <div><dt>Referência</dt><dd><strong>50%</strong> para o segmento público.</dd></div>
        <div><dt>Recorte</dt><dd>{data.period ?? 'Período indisponível'} · contexto pré-ciclo.</dd></div>
      </dl>
    </aside>
  )
}

export function ExpansionShareTechnicalDisclosure({ model }) {
  const data = model.composition
  return (
    <details className="accumulative-history-disclosure expansion-technical-disclosure">
      <summary>
        <span>Metodologia e memória do cálculo</span>
        <small>Fórmula, interpretação e regras metodológicas</small>
        <DisclosureChevron />
      </summary>
      <div className="accumulative-history-disclosure__body expansion-technical-disclosure__body">
        <section className="expansion-technical-disclosure__result" aria-labelledby="expansion-technical-formula">
          <h4 id="expansion-technical-formula">Memória do resultado</h4>
          {isFiniteMetric(data.currentValue) ? (
            <div
              aria-label={`${formatSignedCount(data.publicExpansion)} divididas por ${formatSignedCount(data.totalExpansion)}, multiplicado por 100, resulta em ${formatPercent(data.currentValue)}.`}
              className="expansion-technical-disclosure__formula"
            >
              <span><small>Variação pública</small><strong>{formatSignedCount(data.publicExpansion)}</strong></span>
              <b aria-hidden="true">÷</b>
              <span><small>Variação total</small><strong>{formatSignedCount(data.totalExpansion)}</strong></span>
              <b aria-hidden="true">× 100 =</b>
              <span className="expansion-technical-disclosure__formula-result"><small>Participação calculada</small><strong>{formatPercent(data.currentValue)}</strong></span>
            </div>
          ) : (
            <p className="expansion-technical-disclosure__formula expansion-technical-disclosure__formula--unavailable"><strong>Resultado não calculável para o período.</strong></p>
          )}
          <p className="expansion-technical-disclosure__interpretation"><strong>Como interpretar:</strong> o resultado pode ser negativo quando as matrículas públicas diminuem enquanto o total cresce. Pode superar 100% quando o crescimento público é maior que a expansão líquida total. Sem expansão total positiva ou dados comparáveis, o resultado não é calculável.</p>
        </section>
        <section className="expansion-technical-disclosure__method" aria-labelledby="expansion-technical-method">
          <h4 id="expansion-technical-method">Metodologia</h4>
          <ul>
            {model.methodology.map((paragraph) => <li key={paragraph}>{paragraph}</li>)}
          </ul>
        </section>
      </div>
    </details>
  )
}

export function IndexedEnrollmentComparison({ series }) {
  const points = normalizeIndexedSeries(series)
  if (points.length < 2) return <p className="expansion-index-chart__empty">Série comparável insuficiente para construir o índice.</p>
  const allValues = points.flatMap((point) => [point.publicIndex, point.totalIndex])
  const rawMin = Math.min(100, ...allValues)
  const rawMax = Math.max(100, ...allValues)
  const padding = Math.max(5, (rawMax - rawMin) * 0.15)
  const min = Math.floor((rawMin - padding) / 5) * 5
  const max = Math.ceil((rawMax + padding) / 5) * 5
  const x = (index) => 58 + (index / (points.length - 1)) * 586
  const y = (value) => 214 - ((value - min) / Math.max(1, max - min)) * 172
  const yearTicks = selectPneYearTicks(
    points.map((point, index) => ({ ...point, x: x(index) })),
    6,
  )

  return (
    <div className="expansion-index-chart">
      <div className="expansion-index-chart__legend" aria-hidden="true"><span><i className="expansion-index-chart__key expansion-index-chart__key--public" />Público</span><span><i className="expansion-index-chart__key expansion-index-chart__key--total" />Total da EPT</span></div>
      <svg role="img" aria-label={`Evolução relativa das matrículas de ${points[0].year} a ${points.at(-1).year}; ${points[0].year} igual a 100.`} viewBox="0 0 700 250">
        <line className="expansion-index-chart__grid" x1="58" x2="644" y1={y(100)} y2={y(100)} />
        <text className="expansion-index-chart__axis-label" x="50" y={y(100) + 4} textAnchor="end">100</text>
        <path className="expansion-index-chart__line expansion-index-chart__line--public" d={buildPath(points, (point) => point.publicIndex, x, y)} />
        <path className="expansion-index-chart__line expansion-index-chart__line--total" d={buildPath(points, (point) => point.totalIndex, x, y)} />
        {yearTicks.map((point) => <text className="expansion-index-chart__axis-label" key={point.year} x={point.x} y="240" textAnchor="middle">{point.year}</text>)}
        {points.map((point, index) => <g key={point.year}><circle className="expansion-index-chart__point expansion-index-chart__point--public" cx={x(index)} cy={y(point.publicIndex)} r="4" tabIndex="0"><title>{`${point.year}: Público, índice ${formatNumber(point.publicIndex)}.`}</title></circle><circle className="expansion-index-chart__point expansion-index-chart__point--total" cx={x(index)} cy={y(point.totalIndex)} r="4" tabIndex="0"><title>{`${point.year}: Total da EPT, índice ${formatNumber(point.totalIndex)}.`}</title></circle></g>)}
      </svg>
    </div>
  )
}

function normalizeIndexedSeries(series) {
  if (!Array.isArray(series) || series.length < 2) return []
  const first = series[0]
  if (!first.publicEnrollment || !first.totalEnrollment) return []
  return series.map((point) => ({ ...point, year: point.ano, publicIndex: (point.publicEnrollment / first.publicEnrollment) * 100, totalIndex: (point.totalEnrollment / first.totalEnrollment) * 100 })).filter((point) => Number.isFinite(point.publicIndex) && Number.isFinite(point.totalIndex))
}

function buildPath(points, getValue, x, y) { return points.map((point, index) => `${index === 0 ? 'M' : 'L'} ${x(index)} ${y(getValue(point))}`).join(' ') }
function getShortMeaning(data) { return !isFiniteMetric(data.currentValue) ? data.interpretation : Number(data.currentValue) < 0 ? 'A rede pública não acompanhou o crescimento total no período.' : Number(data.currentValue) > 100 ? 'O crescimento público superou a expansão líquida total.' : Number(data.currentValue) >= 50 ? 'A participação pública ficou no patamar de referência ou acima.' : 'A participação pública ficou abaixo do patamar de referência.' }
function getExplanationTitle(data) { if (!isFiniteMetric(data.currentValue)) return 'Não há base suficiente para calcular o resultado'; if (Number(data.currentValue) < 0) return 'O total cresceu, mas a rede pública encolheu'; if (Number(data.currentValue) > 100) return 'O crescimento público superou a expansão líquida total'; if (Number(data.currentValue) >= 50) return 'A rede pública respondeu por pelo menos metade da expansão'; return 'A rede pública participou de menos da metade da expansão' }
function getResultState(value) { if (!isFiniteMetric(value)) return 'unavailable'; if (Number(value) < 0) return 'negative'; if (Number(value) > 100) return 'above-maximum'; if (Number(value) >= 50) return 'reached'; return 'below' }
function getResultStateLabel(value) { return ({ unavailable: 'Resultado não calculável', negative: 'Participação pública negativa', 'above-maximum': 'Resultado acima de 100%', reached: 'No patamar ou acima', below: 'Abaixo do patamar' })[getResultState(value)] }
function formatDistance(value, target) { if (!isFiniteMetric(value) || !isFiniteMetric(target)) return '—'; const difference = Number(value) - Number(target); if (Math.abs(difference) < 1e-9) return 'No patamar'; return `${difference < 0 ? '−' : '+'}${formatNumber(Math.abs(difference))} p.p.` }
function formatChangeLabel(value) { const numeric = Number(value); if (!Number.isFinite(numeric)) return 'variação indisponível'; if (numeric === 0) return 'Sem variação'; return `${numeric < 0 ? 'Queda' : 'Crescimento'} de ${formatNumber(Math.abs(numeric))}%` }
function formatCount(value) { return Number.isFinite(Number(value)) ? countFormatter.format(Number(value)) : '—' }
function formatSignedCount(value) { const numeric = Number(value); if (!Number.isFinite(numeric)) return 'indisponível'; return `${numeric > 0 ? '+' : numeric < 0 ? '−' : ''}${formatCount(Math.abs(numeric))} matrículas` }
function formatPercent(value) { if (!isFiniteMetric(value)) return 'não calculável'; const numeric = Number(value); return `${numeric < 0 ? '−' : ''}${percentFormatter.format(Math.abs(numeric))}%` }
function formatNumber(value) { return percentFormatter.format(Number(value)) }
function isFiniteMetric(value) { return value !== null && value !== undefined && value !== '' && Number.isFinite(Number(value)) }
