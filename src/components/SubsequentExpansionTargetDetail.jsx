import { CalendarCheck2, CalendarDays } from 'lucide-react'
import { QuickReadingHeading } from './QuickReadingHeading'

const countFormatter = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 0 })
const percentFormatter = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 1 })

export function SubsequentExpansionTracking({ model }) {
  const data = model.composition
  const progress = clampPercent(data.progress)
  const hasPostStartingPointData = Number(data.currentYear) > Number(data.baselineYear)

  if (!hasPostStartingPointData) {
    return (
      <section className="absolute-expansion-tracking absolute-expansion-tracking--waiting" aria-label="Início do acompanhamento">
        <CalendarDays aria-hidden="true" className="absolute-expansion-tracking__icon" />
        <div>
          <span>Acompanhamento</span>
          <strong>Começa com os dados de 2026</strong>
          <p>O valor de 2025 define apenas o ponto de partida; ainda não representa desempenho do ciclo.</p>
        </div>
      </section>
    )
  }

  return (
    <section className="absolute-expansion-tracking" aria-label="Acompanhamento atual da meta">
      <div className="absolute-expansion-tracking__heading">
        <span>Acompanhamento atual da meta</span>
        <strong>{formatPercent(progress)} do crescimento necessário realizado</strong>
      </div>
      <div className="absolute-expansion-tracking__values">
        <span><small>Início do ciclo</small><strong>{formatCount(data.baselineValue)}</strong></span>
        <span><small>Atual · {data.currentYear}</small><strong>{formatCount(data.currentValue)}</strong></span>
        <span><small>Meta 2036</small><strong>{formatCount(data.targetValue)}</strong></span>
      </div>
      <div className="absolute-expansion-tracking__track" aria-hidden="true">
        <span style={{ width: `${progress}%` }} />
      </div>
    </section>
  )
}

export function SubsequentExpansionTargetAnalysis({ model }) {
  const data = model.composition
  const hasValues = [data.baselineValue, data.currentValue, data.targetValue].every(isFiniteMetric)
  const hasPostStartingPointData = Number(data.currentYear) > Number(data.baselineYear)

  return (
    <section className="absolute-expansion-analysis" aria-labelledby="absolute-expansion-analysis-title">
      <header className="absolute-expansion-analysis__header">
        <span className="eyebrow">Como ler a meta</span>
        <h3 id="absolute-expansion-analysis-title">Como a meta de 2036 é formada</h3>
        {hasValues ? (
          <p>Partimos de <strong>{formatCount(data.baselineValue)} matrículas</strong> em 2025, precisamos acrescentar <strong>{formatCount(data.targetIncrease)}</strong> e chegar a <strong>{formatCount(data.targetValue)} matrículas</strong> em 2036.</p>
        ) : <p>Carregando os valores que formam a meta de 2036.</p>}
      </header>

      {hasValues ? <AbsoluteExpansionEquation data={data} /> : (
        <div className="absolute-expansion-analysis__empty">Carregando o ponto de partida e a meta.</div>
      )}

      <div className={`absolute-expansion-analysis__summary${hasPostStartingPointData ? '' : ' absolute-expansion-analysis__summary--waiting'}`}>
        <CalendarIcon />
        <div>
          <strong>{hasPostStartingPointData ? `Acompanhamento atualizado até ${data.currentYear}` : 'Acompanhamento começa em 2026'}</strong>
          <span>{hasPostStartingPointData
            ? `${formatCount(data.currentIncrease)} matrículas acrescentadas desde 2025 — ${formatPercent(data.progress)} da expansão prevista.`
            : 'Como 2025 é o ponto de partida, ainda não há evolução do ciclo para avaliar.'}</span>
        </div>
      </div>
      <p className="absolute-expansion-analysis__context">Os dados anteriores a 2025 são apresentados apenas como contexto histórico e não representam o avanço oficial do ciclo.</p>
    </section>
  )
}

function AbsoluteExpansionEquation({ data }) {
  return (
    <div
      aria-label={`Ponto de partida em 2025: ${formatCount(data.baselineValue)} matrículas, mais expansão necessária de ${formatCount(data.targetIncrease)} matrículas, igual à meta de ${formatCount(data.targetValue)} matrículas em 2036.`}
      className="absolute-expansion-equation"
      role="img"
    >
      <EquationTerm label="Ponto de partida" note="em 2025" value={formatCount(data.baselineValue)} />
      <span className="absolute-expansion-equation__operator" aria-hidden="true">+</span>
      <EquationTerm label="Expansão necessária" note="+60%" tone="growth" value={`+${formatCount(data.targetIncrease)}`} />
      <span className="absolute-expansion-equation__operator" aria-hidden="true">=</span>
      <EquationTerm label="Meta" note="em 2036" tone="target" value={formatCount(data.targetValue)} />
    </div>
  )
}

function EquationTerm({ label, note, tone = 'start', value }) {
  return (
    <span className={`absolute-expansion-equation__term absolute-expansion-equation__term--${tone}`}>
      <small>{label}</small>
      <strong>{value}</strong>
      <span>matrículas</span>
      <em>{note}</em>
    </span>
  )
}

function CalendarIcon() {
  return <CalendarCheck2 aria-hidden="true" className="absolute-expansion-analysis__summary-icon" />
}

export function SubsequentExpansionQuickReading({ legalGoal, metaRef, model }) {
  const data = model.composition
  const hasPostStartingPointData = Number(data.currentYear) > Number(data.baselineYear)
  const goalText = legalGoal?.dashboardText || legalGoal?.displayText || legalGoal?.originalText

  return (
    <aside className="indicator-quick-reading absolute-expansion-reading" aria-label="Leitura rápida do indicador">
      <QuickReadingHeading />
      <dl>
        <div><dt>Referência do PNE</dt><dd><strong>Meta {metaRef || 'do PNE'}</strong>{goalText ? ` — ${goalText}` : ' — acompanhar a expansão das matrículas em cursos técnicos subsequentes.'}</dd></div>
        <div><dt>Ponto de partida</dt><dd><strong>{formatCount(data.baselineValue)} matrículas</strong> registradas em 2025.</dd></div>
        <div><dt>O que precisa acontecer</dt><dd>Acrescentar <strong>{formatCount(data.targetIncrease)} matrículas</strong> até 2036.</dd></div>
        <div><dt>Quando começa</dt><dd>{hasPostStartingPointData ? `Já há dados de ${data.currentYear} para acompanhar a evolução.` : 'Com a publicação dos dados de 2026.'}</dd></div>
        <div><dt>Como interpretar agora</dt><dd>{hasPostStartingPointData ? `${formatPercent(data.progress)} da expansão prevista foi realizada.` : '2025 define o ponto de partida; ainda não há desempenho do ciclo para avaliar.'}</dd></div>
      </dl>
    </aside>
  )
}

function clampPercent(value) {
  const numeric = Number(value)
  if (!Number.isFinite(numeric)) return 0
  return Math.max(0, Math.min(100, numeric))
}

function formatCount(value) {
  return isFiniteMetric(value) ? countFormatter.format(Number(value)) : '—'
}

function formatPercent(value) {
  return `${percentFormatter.format(clampPercent(value))}%`
}

function isFiniteMetric(value) {
  return value !== null && value !== undefined && value !== '' && Number.isFinite(Number(value))
}
