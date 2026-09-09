import { useEffect, useId, useMemo, useRef, useState } from 'react'
import { PME_DATA_LABELS, formatPmeValue } from './pmeFormatting'
import { loadPmeEvidenceHistory, type PmeEvidenceHistory, type PmeEvidenceHistoryPoint } from './pmeEvidenceHistory'
import type { PmeEvidence } from './pmeTypes'
import './styles/pme-history.css'

type HistoryState = { status: 'loading' } | { status: 'error'; message: string } | { status: 'ready'; history: PmeEvidenceHistory }
interface ChartPoint extends PmeEvidenceHistoryPoint { x: number; y: number }

const chartFrame = { height: 232, left: 64, right: 18, top: 16, bottom: 32 }
const printChartFrame = { height: 252, left: 64, right: 18, top: 16, bottom: 32 }

function humanUnit(unit: string) {
  if (unit === 'percent') return 'Percentual (%)'
  if (unit === 'count') return 'Quantidade'
  if (unit === 'years') return 'Anos'
  return 'Valor'
}

function chartModel(points: readonly PmeEvidenceHistoryPoint[], width: number, frame = chartFrame) {
  const geometry = { ...frame, width }
  const values = points.flatMap((point) => point.value === null ? [] : [point.value])
  if (!values.length) return { geometry, points: [] as ChartPoint[], segments: [] as ChartPoint[][], ticks: [] as number[], years: [] as number[], xByYear: {} as Record<number, number> }
  const rawMin = Math.min(...values)
  const rawMax = Math.max(...values)
  const spread = rawMax - rawMin || Math.max(Math.abs(rawMax) * 0.16, 1)
  const minimum = rawMin - spread * 0.14
  const maximum = rawMax + spread * 0.14
  const firstYear = points[0]?.year || 0
  const lastYear = points[points.length - 1]?.year || firstYear
  const plotWidth = geometry.width - geometry.left - geometry.right
  const plotHeight = geometry.height - geometry.top - geometry.bottom
  const x = (year: number) => firstYear === lastYear ? geometry.left + plotWidth / 2 : geometry.left + ((year - firstYear) / (lastYear - firstYear)) * plotWidth
  const y = (value: number) => geometry.top + ((maximum - value) / (maximum - minimum)) * plotHeight
  const scaled: Array<ChartPoint | null> = points.map((point) => point.value === null ? null : { ...point, x: x(point.year), y: y(point.value) })
  const segments: ChartPoint[][] = []
  let segment: ChartPoint[] = []
  for (const point of scaled) {
    if (point) segment.push(point)
    else if (segment.length) { segments.push(segment); segment = [] }
  }
  if (segment.length) segments.push(segment)
  const years = points.length <= 6 ? points.map((point) => point.year) : [...new Set([points[0]?.year, points[Math.round((points.length - 1) / 4)]?.year, points[Math.round((points.length - 1) / 2)]?.year, points[Math.round((points.length - 1) * 0.75)]?.year, points[points.length - 1]?.year].filter((year): year is number => year !== undefined))]
  return { geometry, points: scaled.filter((point): point is ChartPoint => point !== null), segments, ticks: Array.from({ length: 5 }, (_, index) => minimum + ((maximum - minimum) * index) / 4), years, xByYear: Object.fromEntries(points.map((point) => [point.year, x(point.year)])) as Record<number, number> }
}

function ChartSvg({ chart, unit, className, activeYear, interactive, onActivate, onDeactivate, tooltipId }: {
  chart: ReturnType<typeof chartModel>
  unit: string
  className: string
  activeYear?: number | null
  interactive?: boolean
  onActivate?: (year: number) => void
  onDeactivate?: () => void
  tooltipId?: string
}) {
  const geometry = chart.geometry
  const bottom = geometry.height - geometry.bottom
  const right = geometry.width - geometry.right
  const xForYear = (year: number) => chart.xByYear[year] || geometry.left
  const yForTick = (tick: number) => {
    const lowest = chart.ticks[0] || 0
    const highest = chart.ticks[chart.ticks.length - 1] || 1
    return geometry.top + ((highest - tick) / (highest - lowest)) * (bottom - geometry.top)
  }
  return <svg aria-hidden={interactive ? undefined : true} className={className} height={geometry.height} role={interactive ? 'group' : undefined} style={interactive ? { width: geometry.width, height: geometry.height } : undefined} viewBox={'0 0 ' + geometry.width + ' ' + geometry.height} width={geometry.width} aria-label={interactive ? 'Evolução anual em ' + humanUnit(unit) + '. Valores completos disponíveis em Dados por ano.' : undefined}>
    <g className="pme-history-chart__grid">{chart.ticks.map((tick) => <g key={tick}><line x1={geometry.left} x2={right} y1={yForTick(tick)} y2={yForTick(tick)} /><text x={geometry.left - 12} y={yForTick(tick) + 4}>{formatPmeValue(tick, unit)}</text></g>)}</g>
    <line className="pme-history-chart__axis" x1={geometry.left} x2={right} y1={bottom} y2={bottom} />
    {chart.segments.map((segment) => <path className="pme-history-chart__line" d={segment.map((point, index) => (index ? 'L' : 'M') + point.x.toFixed(1) + ' ' + point.y.toFixed(1)).join(' ')} key={segment[0]?.year} />)}
    {chart.years.map((year) => <text className="pme-history-chart__year" key={year} x={xForYear(year)} y={geometry.height - 14}>{year}</text>)}
    {chart.points.map((point) => <circle aria-describedby={activeYear === point.year ? tooltipId : undefined} aria-label={interactive ? point.year + ': ' + formatPmeValue(point.value, unit) : undefined} className={'pme-history-chart__point' + (activeYear === point.year ? ' is-active' : '')} cx={point.x} cy={point.y} key={point.year} onBlur={interactive ? onDeactivate : undefined} onClick={interactive ? () => onActivate?.(point.year) : undefined} onFocus={interactive ? () => onActivate?.(point.year) : undefined} onKeyDown={interactive ? (event) => { if (event.key === 'Escape') onDeactivate?.(); if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); onActivate?.(point.year) } } : undefined} onMouseEnter={interactive ? () => onActivate?.(point.year) : undefined} onMouseLeave={interactive ? onDeactivate : undefined} r={activeYear === point.year ? 6 : 4.5} role={interactive ? 'button' : undefined} tabIndex={interactive ? 0 : undefined}><title>{point.year + ': ' + formatPmeValue(point.value, unit)}</title></circle>)}
  </svg>
}

function HistoryChart({ points, unit }: { points: readonly PmeEvidenceHistoryPoint[]; unit: string }) {
  const [activeYear, setActiveYear] = useState<number | null>(null)
  const surfaceRef = useRef<HTMLDivElement>(null)
  const [chartWidth, setChartWidth] = useState(760)
  const tooltipId = useId()
  useEffect(() => {
    const surface = surfaceRef.current
    if (!surface) return
    const measure = () => setChartWidth(Math.max(360, Math.round(surface.clientWidth)))
    measure()
    const observer = new ResizeObserver(measure)
    observer.observe(surface)
    return () => observer.disconnect()
  }, [])
  const chart = useMemo(() => chartModel(points, chartWidth), [points, chartWidth])
  const printChart = useMemo(() => chartModel(points, 500, printChartFrame), [points])
  const geometry = chart.geometry
  const active = chart.points.find((point) => point.year === activeYear) || null
  if (chart.points.length < 2) return null
  return <figure className="pme-history-chart">
    <div className="pme-history-chart__heading"><div><h5>Evolução ao longo dos anos</h5><p>{humanUnit(unit)}<span className="pme-no-print">. Selecione um ponto para ler o valor.</span></p></div><span aria-hidden="true" className="pme-history-chart__key"><i /> Valor anual</span></div>
    <div className="pme-history-chart__surface" ref={surfaceRef}>
      <ChartSvg activeYear={active?.year} chart={chart} className="pme-history-chart__screen-svg" interactive onActivate={setActiveYear} onDeactivate={() => setActiveYear(null)} tooltipId={tooltipId} unit={unit} />
      <ChartSvg chart={printChart} className="pme-history-chart__print-svg" unit={unit} />
      {active && <div className="pme-history-chart__tooltip" id={tooltipId} role="tooltip" style={{ left: Math.min(88, Math.max(12, (active.x / geometry.width) * 100)) + '%', top: Math.max(8, (active.y / geometry.height) * 100) + '%' }}><span>{active.year}</span><strong>{formatPmeValue(active.value, unit)}</strong></div>}
      <span className="pme-history-chart__sr" aria-live="polite">{active ? active.year + ': ' + formatPmeValue(active.value, unit) : ''}</span>
    </div>
  </figure>
}

function Absence({ history }: { history: Extract<PmeEvidenceHistory, { status: 'absent' }> }) {
  const description = history.reason === 'evidence_not_observed'
    ? 'A evidência atual está marcada como “' + PME_DATA_LABELS[history.dataState] + '”; a evolução anual não é exibida para não reinterpretar essa condição.'
    : history.reason === 'indicator_not_mapped'
      ? 'Não há relação publicada entre esta evidência e uma série anual municipal.'
      : history.reason === 'series_empty'
        ? 'A série anual não contém registros para exibir.'
        : 'Não há série anual disponível para esta evidência no município selecionado.'
  return <p className="pme-note" role="status">{description}</p>
}

function compatibilityNote(history: Extract<PmeEvidenceHistory, { status: 'available' }>) {
  if (history.temporalCompatibility === 'same_period_different_value') return 'O valor da evidência atual difere do valor registrado para o mesmo ano. A evolução anual oferece contexto e não substitui a evidência.'
  if (history.temporalCompatibility === 'period_not_in_series') return 'O ano da evidência atual não aparece nesta evolução. A série anual oferece apenas contexto.'
  if (history.temporalCompatibility === 'current_period_not_published') return 'O ano da evidência atual não aparece nesta evolução. A série anual oferece apenas contexto.'
  return null
}

export function PmeEvidenceHistoryContent({ history, evidenceTitle }: { history: PmeEvidenceHistory; evidenceTitle: string }) {
  if (history.status === 'absent') return <Absence history={history} />
  return <AvailableHistory history={history} evidenceTitle={evidenceTitle} />
}

function AvailableHistory({ history, evidenceTitle }: { history: Extract<PmeEvidenceHistory, { status: 'available' }>; evidenceTitle: string }) {
  const [tableVisible, setTableVisible] = useState(true)
  const tableId = useId()
  const note = compatibilityNote(history)
  return <section className="pme-history" aria-label={'Evolução anual de ' + evidenceTitle}>
    <header className="pme-history__intro"><div><h4>Dados por ano</h4><p>{humanUnit(history.unit)}{history.universe ? ' • ' + history.universe : ''}</p></div><button aria-controls={tableId} aria-expanded={tableVisible} className="pme-history__table-toggle" onClick={() => setTableVisible((visible) => !visible)} type="button">{tableVisible ? 'Ocultar tabela' : 'Mostrar tabela'}</button></header>
    {note && <p className="pme-history__note">{note}</p>}
    <div className={'pme-history__layout' + (tableVisible ? '' : ' pme-history__layout--chart-only')}>
      <HistoryChart points={history.points} unit={history.unit} />
      <div role="region" aria-label="Tabela de dados anuais" className={'pme-history__table-panel' + (tableVisible ? '' : ' is-hidden')} id={tableId} tabIndex={0}><table><caption>Dados por ano</caption><thead><tr><th scope="col">Ano</th><th scope="col">Valor</th></tr></thead><tbody>{history.points.map((point) => <tr key={point.year}><th scope="row">{point.year}</th><td>{point.value === null ? 'Valor nulo na publicação' : formatPmeValue(point.value, history.unit)}</td></tr>)}</tbody></table></div>
    </div>
    {history.sources.length > 0 && <p className="pme-history__sources">Fontes: {history.sources.map((source) => source.title).join('; ')}.</p>}
  </section>
}

export function PmeEvidenceHistory({ municipalityId, evidence }: { municipalityId: string; evidence: PmeEvidence }) {
  const [state, setState] = useState<HistoryState>({ status: 'loading' })
  const historyEvidence = useMemo(() => ({ dataState: evidence.dataState, goalId: evidence.goalId, indicatorId: evidence.indicatorId, period: evidence.period, rawValue: evidence.rawValue, relationId: evidence.relationId, unit: evidence.unit }), [evidence.dataState, evidence.goalId, evidence.indicatorId, evidence.period, evidence.rawValue, evidence.relationId, evidence.unit])
  useEffect(() => {
    let cancelled = false
    setState({ status: 'loading' })
    void loadPmeEvidenceHistory(municipalityId, historyEvidence).then((history) => { if (!cancelled) setState({ status: 'ready', history }) }, (error: unknown) => { if (!cancelled) setState({ status: 'error', message: error instanceof Error ? error.message : 'Não foi possível carregar a série municipal.' }) })
    return () => { cancelled = true }
  }, [municipalityId, historyEvidence])
  if (state.status === 'loading') return <p className="pme-note" role="status">Carregando a evolução anual…</p>
  if (state.status === 'error') return <p className="pme-note" role="alert">Não foi possível carregar a evolução anual. Tente novamente mais tarde.</p>
  return <PmeEvidenceHistoryContent history={state.history} evidenceTitle={evidence.title} />
}
