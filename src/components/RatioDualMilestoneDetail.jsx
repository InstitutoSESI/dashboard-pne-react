import { forwardRef, useMemo } from 'react'
import { ComplementaryEnrollmentChart } from './ComplementaryEnrollmentChart'
import { IndicatorHistoryChart } from './IndicatorHistoryChart'
import { MetricCard } from './MetricCard'
import { PneSourceNotes } from './PneSourceNotes'
import { buildObservedPercentageScale } from '../utils/pneChartSystem'
import { getIndicatorTitle } from '../utils/format'
import '../styles/ratio-dual-milestone.css'

const countFormatter = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 0 })
const percentFormatter = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 1 })

export const RatioDualMilestoneDetail = forwardRef(function RatioDualMilestoneDetail({
  cycle,
  details,
  detailsStatus = 'loading',
  item,
  legalReference,
  presentation,
  result,
}, ref) {
  const rows = useMemo(
    () => normalizeComponentRows(
      details?.series_components_by_cycle?.[cycle] ?? details?.series_components,
    ),
    [cycle, details],
  )
  const latest = rows.at(-1) ?? null
  const recentRows = rows.slice(-5)
  const references = resolveMilestoneReferences(cycle, legalReference, result)
  const milestone = references[0] ?? null
  const finalTarget = references.at(-1) ?? null
  const consolidatedValue = toFiniteNumber(result?.end_value)
  const consolidatedYear = toFiniteNumber(result?.end_year)
  const currentValue = consolidatedValue ?? latest?.percentual ?? null
  const distanceToMilestone = Number.isFinite(currentValue) && Number.isFinite(milestone?.value)
    ? currentValue - milestone.value
    : null
  const observedScale = buildObservedPercentageScale(
    recentRows.map((row) => row.percentual).filter(Number.isFinite),
  )
  const numeratorSeries = rows.map((row) => ({ ano: row.ano, valor: row.numerador }))
  const denominatorSeries = rows.map((row) => ({ ano: row.ano, valor: row.denominador }))
  const sourceContext = {
    block: 'pne',
    cycle,
    details,
    indicatorKey: item?.key,
    item,
    presentation,
    result,
    title: item?.label,
  }

  if (!latest) {
    const hasConsolidatedValue = consolidatedValue !== null
    const viewState = hasConsolidatedValue
      ? 'readyWithoutBreakdown'
      : detailsStatus === 'error'
        ? 'error'
        : 'unavailable'

    return (
      <section
        className="detail-panel detail-panel--organized detail-panel--ratio-dual"
        data-ratio-detail-state={viewState}
        ref={ref}
      >
        <div className="detail-heading">
          <div className="detail-heading__copy">
            <h2 data-detail-title tabIndex={-1}>{getIndicatorTitle(item, result)}</h2>
          </div>
        </div>
        {hasConsolidatedValue ? (
          <ConsolidatedRatioDetail
            currentValue={consolidatedValue}
            currentYear={consolidatedYear}
            presentation={presentation}
            result={result}
          />
        ) : (
          <div className="state-box state-box--empty ratio-dual-data-state" role="status">
            <strong>
              {viewState === 'error'
                ? 'Não foi possível carregar o resultado'
                : 'Resultado indisponível'}
            </strong>
            <p>
              Não há resultado consolidado suficiente para apresentar este indicador no município selecionado.
            </p>
          </div>
        )}
        <footer className="pne-detail-footer ratio-dual-footer">
          <PneSourceNotes context={sourceContext} />
        </footer>
      </section>
    )
  }

  const currentLabel = formatPercent(currentValue, 'Resultado não calculável')
  const milestoneLabel = formatPercent(milestone?.value)
  const finalTargetLabel = formatPercent(finalTarget?.value)
  const distanceLabel = formatDistance(distanceToMilestone)
  const metricSummary = [
    `resultado atual ${currentLabel}`,
    `${formatCount(latest.numerador)} de ${formatCount(latest.denominador)} matrículas`,
    `marco ${milestone?.year ?? 'não disponível'} de ${milestoneLabel}`,
    distanceLabel,
    `meta final ${finalTarget?.year ?? 'não disponível'} de ${finalTargetLabel}`,
  ].join('; ')

  return (
    <section
      className="detail-panel detail-panel--organized detail-panel--ratio-dual"
      data-ratio-detail-state="readyWithBreakdown"
      ref={ref}
    >
      <div className="detail-heading">
        <div className="detail-heading__copy">
          <h2 data-detail-title tabIndex={-1}>{getIndicatorTitle(item, result)}</h2>
        </div>
      </div>

      <div className="ratio-dual-metrics" aria-label={metricSummary}>
        <MetricCard
          detail="Percentual das matrículas de EJA articuladas à educação profissional."
          icon="current"
          label={`Resultado atual — ${latest.ano}`}
          size="large"
          value={currentLabel}
        />
        <MetricCard
          detail={`${formatCount(latest.numerador)} de ${formatCount(latest.denominador)} matrículas de EJA`}
          icon="type"
          label="Matrículas articuladas"
          value={formatCount(latest.numerador)}
        />
        <MetricCard
          detail="Primeira referência do PNE"
          icon="start"
          label={`Marco — ${milestone?.year ?? '—'}`}
          value={milestoneLabel}
        />
        <MetricCard
          icon="distance"
          label="Distância até o marco"
          tone={Number.isFinite(distanceToMilestone) && distanceToMilestone >= 0 ? 'success' : 'warning'}
          value={distanceLabel}
        />
        <MetricCard
          detail="Referência final do ciclo"
          icon="target"
          label={`Meta final — ${finalTarget?.year ?? '—'}`}
          value={finalTargetLabel}
        />
      </div>

      <DualMilestoneRuler
        currentValue={currentValue}
        distanceLabel={distanceLabel}
        finalTarget={finalTarget}
        milestone={milestone}
      />

      <div className="ratio-dual-primary">
        <div className="indicator-chart-card ratio-dual-main-chart">
          <IndicatorHistoryChart
            domainOverride={observedScale.domain}
            endYear={recentRows.at(-1)?.ano}
            essentialLabels
            series={recentRows.map((row) => ({ ano: row.ano, valor: row.percentual }))}
            showMetaLine={false}
            showMissingPoints
            startYear={recentRows[0]?.ano}
            subtitle="Percentual das matrículas de EJA articuladas à educação profissional."
            title="Evolução recente do indicador"
            unit="percent"
            pneLayout
          />
          <PneSourceNotes compact context={sourceContext} includeMethodology={false} />
        </div>
        <QuickReading
          currentValue={currentValue}
          distanceLabel={distanceLabel}
          finalTarget={finalTarget}
          latest={latest}
          milestone={milestone}
          recentRows={recentRows}
        />
      </div>

      <section className="ratio-dual-support" aria-labelledby="ratio-dual-support-title">
        <header className="ratio-dual-section-heading">
          <span className="eyebrow">Aprofundamento</span>
          <h3 id="ratio-dual-support-title">Dados de apoio da meta</h3>
          <p>As duas séries mostram os volumes que formam o percentual do indicador.</p>
        </header>
        <div className="ratio-dual-support-grid">
          <SupportChartCard
            description="Evolução anual do numerador utilizado no indicador."
            series={numeratorSeries}
            title="Matrículas de EJA articuladas à educação profissional"
          />
          <SupportChartCard
            description="Evolução anual do universo utilizado como denominador."
            series={denominatorSeries}
            title="Total de matrículas de EJA consideradas no cálculo"
          />
        </div>
      </section>

      <CalculationEquation latest={latest} />
      <HistoricalCalculationTable rows={rows.slice().reverse()} />

      <footer className="pne-detail-footer ratio-dual-footer">
        <PneSourceNotes context={sourceContext} />
      </footer>
    </section>
  )
})

function ConsolidatedRatioDetail({
  currentValue,
  currentYear,
  presentation,
  result,
}) {
  const referenceValue = toFiniteNumber(result?.meta)
  const currentText = presentation?.currentText ?? formatPercent(currentValue)
  const referenceText = presentation?.referenceText ?? formatPercent(referenceValue)
  const distanceText = presentation?.distanceText
    ?? formatSignedPp(currentValue - referenceValue)
  const statusText = presentation?.statusText
    ?? (currentValue >= referenceValue ? 'Referência alcançada' : 'Abaixo da referência')
  const statusTone = currentValue >= referenceValue ? 'success' : 'warning'

  return (
    <>
      <div
        className="ratio-dual-comparison-metrics"
        aria-label={`${currentText}; ${referenceText}; ${distanceText}; ${statusText}`}
      >
        <MetricCard
          detail="Resultado consolidado disponível para o município."
          icon="current"
          label={Number.isFinite(currentYear)
            ? `Resultado disponível — ${currentYear}`
            : 'Resultado disponível'}
          size="large"
          value={currentText}
        />
        <MetricCard
          icon="target"
          label={presentation?.referenceLabel ?? 'Referência prevista na meta'}
          value={referenceText}
        />
        <MetricCard
          icon="distance"
          label={presentation?.distanceLabel ?? 'Distância da referência'}
          tone={statusTone}
          value={distanceText}
        />
        <MetricCard
          icon="status"
          label="Situação"
          tone={statusTone}
          value={statusText}
        />
      </div>

      <ConsolidatedComparisonRuler
        currentText={currentText}
        currentValue={currentValue}
        referenceLabel={presentation?.referenceLabel ?? 'Referência prevista na meta'}
        referenceText={referenceText}
        referenceValue={referenceValue}
      />

      <div className="ratio-dual-consolidated-grid">
        <section className="indicator-data-card ratio-dual-consolidated-data" aria-labelledby="ratio-consolidated-data-title">
          <header className="indicator-data-card__heading">
            <h3 id="ratio-consolidated-data-title">Dados do indicador</h3>
            <p>Resultado municipal consolidado no ano de referência.</p>
          </header>
          <div className="ratio-dual-data-state" role="note">
            <strong>Resultado consolidado disponível.</strong>
            <p>Os componentes de numerador e denominador não estão publicados para este recorte.</p>
          </div>
          <dl className="indicator-data-summary ratio-dual-consolidated-summary">
            <div className="indicator-data-summary__item">
              <dt>Ano</dt>
              <dd>{Number.isFinite(currentYear) ? currentYear : '—'}</dd>
            </div>
            <div className="indicator-data-summary__item">
              <dt>Resultado</dt>
              <dd>{currentText}</dd>
            </div>
          </dl>
        </section>

        <aside className="indicator-quick-reading ratio-dual-consolidated-reading" aria-label="Leitura rápida do indicador">
          <h3>Leitura rápida</h3>
          <ol>
            <ReadingItem
              label="Resultado atual"
              text={`${currentText} em ${Number.isFinite(currentYear) ? currentYear : 'ano não informado'}.`}
            />
            <ReadingItem
              label={presentation?.referenceLabel ?? 'Referência prevista na meta'}
              text={`O valor previsto para comparação é ${referenceText}.`}
            />
            <ReadingItem
              label="Situação atual"
              text={statusText}
            />
            <ReadingItem
              label={presentation?.distanceLabel ?? 'Distância da referência'}
              text={distanceText}
            />
          </ol>
        </aside>
      </div>
    </>
  )
}

function ConsolidatedComparisonRuler({
  currentText,
  currentValue,
  referenceLabel,
  referenceText,
  referenceValue,
}) {
  const currentPosition = valueToPosition(currentValue, 100)
  const referencePosition = valueToPosition(referenceValue, 100)
  const tone = currentValue >= referenceValue ? 'success' : 'warning'

  return (
    <section className="ratio-dual-ruler-card ratio-dual-ruler-card--consolidated" aria-labelledby="ratio-consolidated-ruler-title">
      <header className="ratio-dual-section-heading">
        <h3 id="ratio-consolidated-ruler-title">Comparação com a referência</h3>
        <p>Resultado municipal e referência prevista na meta na escala percentual.</p>
      </header>
      <div
        className="goal-progress ratio-dual-ruler"
        role="img"
        aria-label={`Resultado ${currentText}; ${referenceLabel} ${referenceText}.`}
      >
        <div className="goal-progress__track ratio-dual-ruler__track">
          <span
            className={`goal-progress__fill goal-progress__fill--${tone}`}
            style={{ width: `${currentPosition}%` }}
          />
          <CurrentRulerMarker
            position={currentPosition}
            tone={tone}
            value={currentText}
          />
          <RulerTarget
            label={referenceLabel}
            position={referencePosition}
            tone="final"
            value={referenceText}
          />
        </div>
      </div>
    </section>
  )
}

function DualMilestoneRuler({ currentValue, distanceLabel, finalTarget, milestone }) {
  const finalValue = Number(finalTarget?.value)
  const current = Number(currentValue)
  const baseMax = Number.isFinite(finalValue) && finalValue > 0 ? finalValue : 100
  const domainMax = Number.isFinite(current) && current > baseMax
    ? Math.ceil((current * 1.1) / 5) * 5
    : baseMax
  const currentPosition = Number.isFinite(current) ? valueToPosition(current, domainMax) : null
  const milestonePosition = valueToPosition(milestone?.value, domainMax)
  const finalPosition = valueToPosition(finalTarget?.value, domainMax)
  const currentTone = Number.isFinite(current) && current >= Number(milestone?.value)
    ? 'success'
    : 'warning'
  const accessibleText = Number.isFinite(current)
    ? `Valor atual ${formatPercent(current)}; próximo marco ${formatPercent(milestone?.value)} em ${milestone?.year}; meta final ${formatPercent(finalTarget?.value)} em ${finalTarget?.year}; ${distanceLabel}`
    : `Resultado atual não calculável; próximo marco ${formatPercent(milestone?.value)} em ${milestone?.year}; meta final ${formatPercent(finalTarget?.value)} em ${finalTarget?.year}.`

  return (
    <section className="ratio-dual-ruler-card" aria-labelledby="ratio-dual-ruler-title">
      <header className="ratio-dual-section-heading">
        <h3 id="ratio-dual-ruler-title">Caminho até as metas do PNE</h3>
        <p>Primeiro marco: {formatPercent(milestone?.value)} em {milestone?.year}. Meta final: {formatPercent(finalTarget?.value)} em {finalTarget?.year}.</p>
      </header>
      <div className="goal-progress ratio-dual-ruler" role="img" aria-label={accessibleText}>
        <div className="goal-progress__track ratio-dual-ruler__track">
        {Number.isFinite(currentPosition) ? (
            <>
              <span
                className={`goal-progress__fill goal-progress__fill--${currentTone}`}
                style={{ width: `${currentPosition}%` }}
              />
              <CurrentRulerMarker
                position={currentPosition}
                tone={currentTone}
                value={formatPercent(current)}
              />
            </>
        ) : null}
          <RulerTarget
          label={`Marco — ${milestone?.year ?? '—'}`}
          position={milestonePosition}
          tone="milestone"
          value={formatPercent(milestone?.value)}
        />
          <RulerTarget
          label={`Meta final — ${finalTarget?.year ?? '—'}`}
          position={finalPosition}
          tone="final"
          value={formatPercent(finalTarget?.value)}
        />
        </div>
      </div>
      <p className="ratio-dual-ruler__distance">
        {Number.isFinite(currentValue)
          ? `${distanceLabel} para o marco de ${milestone?.year}`
          : 'A distância até o marco não pode ser calculada porque não havia matrículas de EJA no denominador.'}
      </p>
    </section>
  )
}

function CurrentRulerMarker({ position, tone, value }) {
  const edgeClass = position <= 8
    ? ' goal-progress__marker--edge-start'
    : position >= 92
      ? ' goal-progress__marker--edge-end'
      : ''
  return (
    <span
      className={`goal-progress__marker goal-progress__marker--${tone}${edgeClass}`}
      style={{ left: `${position}%` }}
    >
      <em>{value}</em>
    </span>
  )
}

function RulerTarget({ label, position, tone, value }) {
  const edgeClass = position <= 5
    ? ' goal-progress__target-label--edge-start'
    : position >= 95
      ? ' goal-progress__target-label--edge-end'
      : ''
  const labelStyle = position <= 5
    ? { left: 0 }
    : position >= 95
      ? { right: 0, left: 'auto' }
      : { left: `${position}%` }
  return (
    <>
      <span
        aria-hidden="true"
        className={`goal-progress__target-tick ratio-dual-ruler__target-tick ratio-dual-ruler__target-tick--${tone}`}
        style={{ left: `${position}%` }}
      />
      <span
        className={`goal-progress__target-label ratio-dual-ruler__target-label ratio-dual-ruler__target-label--${tone}${edgeClass}`}
        style={labelStyle}
      >
        <span>{label}</span>
        <strong>{value}</strong>
      </span>
    </>
  )
}

function QuickReading({ currentValue, distanceLabel, finalTarget, latest, milestone, recentRows }) {
  return (
    <aside className="indicator-quick-reading ratio-dual-reading" aria-label="Leitura rápida do indicador">
      <h3>Leitura rápida</h3>
      <ol>
        <ReadingItem label="Resultado atual" text={buildCurrentReading(latest, currentValue)} />
        <ReadingItem
          label="Próximo marco"
          text={`O primeiro objetivo é alcançar ${formatPercent(milestone?.value)} em ${milestone?.year}. ${distanceLabel}`}
        />
        <ReadingItem
          label="Meta final"
          text={`A referência final para ${finalTarget?.year} é de ${formatPercent(finalTarget?.value)}.`}
        />
        <ReadingItem label="Trajetória recente" text={buildTrajectoryReading(recentRows)} />
      </ol>
    </aside>
  )
}

function ReadingItem({ label, text }) {
  return (
    <li>
      <span aria-hidden="true" className="ratio-dual-reading__index" />
      <div><strong>{label}</strong><p>{text}</p></div>
    </li>
  )
}

function SupportChartCard({ description, series, title }) {
  return (
    <article className="ratio-dual-support-card" aria-label={`${title}. ${description}`}>
      <header>
        <h4>{title}</h4>
        <p>{description}</p>
      </header>
      <ComplementaryEnrollmentChart
        maxYearTicks={3}
        series={series}
        showHeading={false}
        title={title}
        unit="Matrículas"
        valueMode="count"
        valueFormatter={formatCount}
      />
    </article>
  )
}

function CalculationEquation({ latest }) {
  const calculable = latest.denominador > 0 && Number.isFinite(latest.percentual)
  return (
    <section className="ratio-dual-equation-card" aria-labelledby="ratio-dual-equation-title">
      <header className="ratio-dual-section-heading">
        <h3 id="ratio-dual-equation-title">Como o indicador é calculado</h3>
        <p>Valores do ano mais recente disponível: {latest.ano}.</p>
      </header>
      <div className="ratio-dual-equation" aria-label={calculable
        ? `${formatCount(latest.numerador)} matrículas articuladas dividido por ${formatCount(latest.denominador)} matrículas de EJA é igual a ${formatPercent(latest.percentual)}`
        : `${formatCount(latest.numerador)} matrículas articuladas dividido por zero matrículas de EJA: resultado não calculável`}>
        <EquationSegment label="Matrículas articuladas" value={formatCount(latest.numerador)} />
        <span aria-hidden="true" className="ratio-dual-equation__operator">÷</span>
        <EquationSegment label="Matrículas de EJA" value={formatCount(latest.denominador)} />
        <span aria-hidden="true" className="ratio-dual-equation__operator">=</span>
        <EquationSegment
          accent
          label="Percentual"
          value={calculable ? formatPercent(latest.percentual) : 'Resultado não calculável'}
        />
      </div>
      {!calculable ? <p className="ratio-dual-equation__notice">Não havia matrículas de EJA no denominador neste ano.</p> : null}
    </section>
  )
}

function EquationSegment({ accent = false, label, value }) {
  return (
    <div className={`ratio-dual-equation__segment${accent ? ' is-accent' : ''}`}>
      <strong>{value}</strong>
      <span>{label}</span>
    </div>
  )
}

function HistoricalCalculationTable({ rows }) {
  return (
    <section className="ratio-dual-table-card" aria-labelledby="ratio-dual-table-title">
      <header className="ratio-dual-section-heading">
        <h3 id="ratio-dual-table-title">Dados usados no cálculo</h3>
        <p>Numerador, denominador e percentual que compõem o indicador.</p>
      </header>
      <div className="ratio-dual-table-wrap" role="region" aria-label="Tabela histórica dos dados usados no cálculo" tabIndex="0">
        <table className="ratio-dual-table">
          <caption className="u-sr-only">Dados históricos usados no cálculo do indicador</caption>
          <thead>
            <tr>
              <th scope="col">Ano</th>
              <th scope="col">Matrículas articuladas à educação profissional</th>
              <th scope="col">Total de matrículas de EJA</th>
              <th scope="col">Percentual</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.ano}>
                <td>{row.ano}</td>
                <td>{formatCount(row.numerador)}</td>
                <td>{formatCount(row.denominador)}</td>
                <td>{Number.isFinite(row.percentual) ? formatPercent(row.percentual) : 'Não calculável'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}

function normalizeComponentRows(rows) {
  if (!Array.isArray(rows)) return []
  return rows
    .map((row) => {
      const ano = Number(row?.ano)
      const numerador = Number(row?.numerador)
      const denominador = Number(row?.denominador)
      const rawPercent = Number(row?.percentual)
      return {
        ano,
        numerador: Number.isFinite(numerador) ? numerador : null,
        denominador: Number.isFinite(denominador) ? denominador : null,
        percentual: denominador > 0 && Number.isFinite(rawPercent) ? rawPercent : null,
      }
    })
    .filter((row) => Number.isFinite(row.ano) && Number.isFinite(row.numerador) && Number.isFinite(row.denominador))
    .sort((a, b) => a.ano - b.ano)
}

function resolveMilestoneReferences(cycle, legalReference, result) {
  const sourceReferences = cycle === 'pne_2026_2036'
    ? legalReference?.milestones
    : result?.meta_references
  const references = (sourceReferences ?? [])
    .map((reference) => ({
      label: reference?.label ?? `Meta PNE ${reference?.year}`,
      value: Number(reference?.value),
      year: Number(reference?.year),
    }))
    .filter((reference) => Number.isFinite(reference.value) && Number.isFinite(reference.year))
    .sort((a, b) => a.year - b.year)

  if (references.length > 0) return references
  if (cycle === 'pne_2026_2036') return []

  const fallbackValue = Number(result?.meta)
  const fallbackYear = Number(String(result?.meta_label ?? '').match(/\d{4}/)?.[0])
  return Number.isFinite(fallbackValue) && Number.isFinite(fallbackYear)
    ? [{ label: result?.meta_label, value: fallbackValue, year: fallbackYear }]
    : []
}

function buildCurrentReading(latest, currentValue) {
  if (latest.denominador === 0) {
    return `Em ${latest.ano}, o resultado não é calculável porque não havia matrículas de EJA no denominador.`
  }
  if (latest.numerador === 0) {
    return `Em ${latest.ano}, não houve matrículas articuladas à educação profissional entre as ${formatCount(latest.denominador)} matrículas de EJA consideradas.`
  }
  return `Em ${latest.ano}, ${formatCount(latest.numerador)} de ${formatCount(latest.denominador)} matrículas de EJA estavam articuladas à educação profissional, equivalente a ${formatPercent(currentValue)}.`
}

function buildTrajectoryReading(rows) {
  const valid = rows.filter((row) => Number.isFinite(row.percentual))
  if (valid.length === 0) return 'Não há valores calculáveis no período recente.'
  if (valid.every((row) => row.percentual === 0)) {
    return 'O indicador permaneceu em 0% no período recente.'
  }
  const latest = valid.at(-1)
  const previous = valid.at(-2)
  if (previous) {
    return `O indicador passou de ${formatPercent(previous.percentual)} em ${previous.ano} para ${formatPercent(latest.percentual)} em ${latest.ano}.`
  }
  const first = valid[0]
  return `O resultado passou de ${formatPercent(first.percentual)} em ${first.ano} para ${formatPercent(latest.percentual)} em ${latest.ano}.`
}

function formatDistance(difference) {
  if (!Number.isFinite(difference)) return 'Resultado não calculável'
  if (Math.abs(difference) < 0.05) return 'Marco alcançado'
  return difference < 0
    ? `Faltam ${formatPp(Math.abs(difference))}`
    : `Supera em ${formatPp(difference)}`
}

function formatPercent(value, fallback = '—') {
  return hasFiniteValue(value) ? `${percentFormatter.format(Number(value))}%` : fallback
}

function formatPp(value) {
  return `${percentFormatter.format(Number(value))} p.p.`
}

function formatSignedPp(value) {
  if (!Number.isFinite(value)) return '—'
  return `${value > 0 ? '+' : ''}${percentFormatter.format(value)} p.p.`
}

function toFiniteNumber(value) {
  if (value === null || value === undefined || value === '') return null
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric : null
}

function formatCount(value) {
  return hasFiniteValue(value) ? countFormatter.format(Number(value)) : '—'
}

function valueToPosition(value, domainMax) {
  if (!hasFiniteValue(value)) return 0
  const numericValue = Number(value)
  if (!Number.isFinite(numericValue) || !Number.isFinite(domainMax) || domainMax <= 0) return 0
  return Math.max(0, Math.min(100, (numericValue / domainMax) * 100))
}

function hasFiniteValue(value) {
  return value !== null && value !== undefined && value !== '' && Number.isFinite(Number(value))
}
