import { useState, type ReactNode } from 'react'
import { formatPmeValue, PME_DATA_LABELS, PME_UNIVERSE_LABELS } from './pmeFormatting'
import { pmeLink, type PmeRoute } from './pmeRoutes'
import type { PmeEvidence, PmeSourceProvenance } from './pmeTypes'
import { PmeEvidenceHistory, PmeEvidenceHistoryContent } from './PmeEvidenceHistoryView'
import type { PmeReportHistoryEntry } from './pmeReports'
import './styles/pme-evidence.css'

function EvidenceSection({ title, children, className = '' }: { title: string; children: ReactNode; className?: string }) {
  return <section className={`pme-evidence__section ${className}`}>
    <h4>{title}</h4>
    {children}
  </section>
}

export function PmeEvidenceSources({ evidence, sources }: { evidence: PmeEvidence; sources: PmeSourceProvenance[] }) {
  const provenance = evidence.sourceIds.map((sourceId) => sources.find((entry) => entry.sourceId === sourceId))
  if (provenance.length === 0) return null

  return <EvidenceSection title="Fonte e período de referência" className="pme-evidence__sources">
    <ul className="pme-evidence__source-list" aria-label="Fontes desta evidência">
      {provenance.map((source, index) => <li key={evidence.sourceIds[index]}>
        {source?.officialUrl ? <a href={source.officialUrl}>{source.title}</a> : source?.title || 'Fonte oficial do indicador'}
        {source?.period ? <span>Período da fonte: {source.period}</span> : null}
      </li>)}
    </ul>
  </EvidenceSection>
}

function DetailContent({ evidence, sources, route, open, history }: {
  evidence: PmeEvidence
  sources: PmeSourceProvenance[]
  route: PmeRoute
  open: boolean
  history?: PmeReportHistoryEntry | null
}) {
  const universe = evidence.territoriality
    ? PME_UNIVERSE_LABELS[evidence.territoriality] || 'Recorte descrito na metodologia da fonte.'
    : 'Consulte o público e o território descritos na metodologia da fonte.'
  const projectionNotes = [
    evidence.projection?.modelReading,
    evidence.projection?.denominatorReading,
    evidence.projection?.uncertaintyReading,
  ].filter(Boolean).join(' ')

  return <div className="pme-evidence__details">
    <EvidenceSection title="Como ler esta evidência">
      <p>{evidence.description}</p>
      {evidence.relationshipNote && <p className="pme-evidence__limit"><strong>Limite desta relação:</strong> {evidence.relationshipNote}</p>}
    </EvidenceSection>

    <EvidenceSection title="Recorte e método">
      <dl className="pme-evidence__facts">
        <div><dt>Alcance / universo</dt><dd>{universe}</dd></div>
        <div><dt>Metodologia</dt><dd>{evidence.methodologyDescription || 'Descrição adicional não publicada.'}</dd></div>
      </dl>
    </EvidenceSection>

    {evidence.permissions.canStatus && evidence.indicatorReference && <EvidenceSection title="Referência publicada">
      <p><strong>{formatPmeValue(evidence.indicatorReference.value, evidence.unit)}</strong> em {evidence.indicatorReference.year}{evidence.indicatorReference.label ? ` · ${evidence.indicatorReference.label}` : ''}.</p>
      {evidence.permissions.canDistance && evidence.distance !== null && <p className="pme-evidence__supporting-reading">Distância publicada em relação à referência: <strong>{formatPmeValue(evidence.distance, evidence.unit === 'percent' ? null : evidence.unit)}{evidence.unit === 'percent' ? ' p.p.' : ''}</strong>. O sinal positivo ou negativo segue o método deste indicador.</p>}
    </EvidenceSection>}

    {(evidence.stateComparison || evidence.similarMunicipalities || evidence.statewidePosition || evidence.comparisonNote) && <EvidenceSection title="Comparações publicadas">
      <div className="pme-evidence__comparison-grid">
        {evidence.stateComparison && <article className="pme-evidence__comparison">
          <h5>Rio Grande do Sul</h5>
          <p>{evidence.stateComparison.valueReading}</p>
          <p className="pme-evidence__supporting-reading">{evidence.stateComparison.reading} Ano: {evidence.stateComparison.year}.</p>
        </article>}
        {evidence.similarMunicipalities && <article className="pme-evidence__comparison">
          <h5>{evidence.similarMunicipalities.title}</h5>
          <p>Mediana: <strong>{formatPmeValue(evidence.similarMunicipalities.median, evidence.similarMunicipalities.unit)}</strong> em {evidence.similarMunicipalities.year}.</p>
          <p className="pme-evidence__supporting-reading">{evidence.similarMunicipalities.reading}</p>
        </article>}
        {evidence.statewidePosition && <article className="pme-evidence__comparison">
          <h5>Posição no conjunto estadual</h5>
          <p>{evidence.statewidePosition.reading}</p>
        </article>}
      </div>
      {evidence.comparisonNote && evidence.comparisonNote !== evidence.stateComparison?.reading && <p className="pme-evidence__limit">{evidence.comparisonNote}</p>}
    </EvidenceSection>}

    <EvidenceSection title="Série histórica">
      <p>{evidence.historicalReading || 'Não há leitura histórica utilizável nesta relação. Uma observação isolada não demonstra tendência.'}</p>
      {evidence.historicalLimit && <p className="pme-evidence__limit">{evidence.historicalLimit}</p>}
      {history === undefined ? route.municipalityId && open && <PmeEvidenceHistory municipalityId={route.municipalityId} evidence={evidence} />
        : history === null ? <p className="pme-evidence__supporting-reading">Preparando a série de apoio…</p>
          : history.status === 'error' ? <p className="pme-evidence__limit" role="alert">Não foi possível carregar a série histórica. Tente novamente mais tarde.</p>
            : <PmeEvidenceHistoryContent history={history} evidenceTitle={evidence.title} />}
    </EvidenceSection>

    {evidence.permissions.canProjection && evidence.projection?.achievementReading && <EvidenceSection title="Projeção já publicada">
      <p>{evidence.projection.achievementReading}</p>
      {projectionNotes && <p className="pme-evidence__limit">{projectionNotes}</p>}
    </EvidenceSection>}

    <PmeEvidenceSources evidence={evidence} sources={sources} />
  </div>
}

export function PmeEvidenceBlock({ evidence, sources, route, expanded = false, history }: {
  evidence: PmeEvidence; sources: PmeSourceProvenance[]; route: PmeRoute; expanded?: boolean; history?: PmeReportHistoryEntry | null
}) {
  const [open, setOpen] = useState(expanded)
  const mode = evidence.mode === 'complementary' ? 'Evidência complementar'
    : evidence.mode === 'tracking' ? 'Referência de acompanhamento' : 'Relação com a referência do PNE'
  const value = evidence.dataState === 'observed'
    ? formatPmeValue(evidence.displayValue ?? evidence.rawValue, evidence.unit)
    : '—'
  const publishedReading = evidence.publicReading?.trim()
  const repeatsState = evidence.dataState !== 'observed' && publishedReading === PME_DATA_LABELS[evidence.dataState]
  const reading = repeatsState
    ? 'Consulte o recorte e a fonte antes de usar esta observação na tomada de decisão.'
    : publishedReading || 'Consulte o recorte e a fonte antes de usar esta observação na tomada de decisão.'
  const hasDistinctDataStatus = Boolean(evidence.dataStatusLabel)
    && evidence.dataStatusLabel !== publishedReading
    && evidence.dataStatusLabel !== evidence.status
    && evidence.dataStatusLabel !== PME_DATA_LABELS[evidence.dataState]
  const detail = <DetailContent evidence={evidence} sources={sources} route={route} open={open} history={history} />

  return <article className="pme-evidence">
    <header className="pme-evidence__heading">
      <div>
        <p className="pme-evidence__eyebrow">Meta {evidence.goalId} · {mode}</p>
        <h3>{evidence.title}</h3>
      </div>
      <span className="pme-evidence__state">{PME_DATA_LABELS[evidence.dataState]}</span>
    </header>

    <div className="pme-evidence__lead">
      <div className="pme-evidence__metric">
        <span>Leitura municipal</span>
        <strong aria-label={evidence.dataState !== 'observed' ? PME_DATA_LABELS[evidence.dataState] : undefined}>{value}</strong>
        <small>{evidence.period === null ? 'Período não disponível' : `Ano ${evidence.period}`}</small>
      </div>
      <div className="pme-evidence__reading">
        <p>{reading}</p>
        {evidence.status && <p><strong>Situação publicada:</strong> {evidence.status}</p>}
        {hasDistinctDataStatus && <p className="pme-evidence__limit">{evidence.dataStatusLabel}</p>}
      </div>
    </div>

    {evidence.rawValue !== null && evidence.rawValue !== evidence.displayValue && <p className="pme-evidence__published-value">Valor informado na publicação: {formatPmeValue(evidence.rawValue, evidence.unit)}. Consulte o método para entender a diferença em relação ao valor exibido.</p>}
    {expanded ? detail : <details className="pme-evidence__disclosure" open={open} onToggle={(event) => setOpen(event.currentTarget.open)}>
      <summary>Ver contexto, fontes e série histórica</summary>
      {detail}
    </details>}
    {!expanded && route.page !== 'objetivo' && <a className="pme-evidence__objective-link pme-no-print" href={pmeLink(route, 'objetivo', { objectiveId: evidence.goalId.split('.')[0] })}>Ver ficha do objetivo {evidence.goalId.split('.')[0]}</a>}
  </article>
}
