import {
  buildPublicSummaryText,
  DIAGNOSTIC_RESULT_VIEWS,
  formatPublicDistance,
  formatPublicValue,
  getPublicCurrentValue,
  getPublicResultReading,
  getPublicResultStatus,
  getPublicStateComparison,
  getPublicSupportingReadings,
  selectDiagnosticResults,
  selectDiagnosticOfficialSources,
  selectDiagnosticThemeGroups,
  selectLegalDiagnosticSummary,
} from '../features/diagnostic/diagnosticPresentation'

export function DiagnosticPrintReport({ description, municipio, publicDiagnostic }) {
  const allResults = selectDiagnosticResults(
    publicDiagnostic,
    DIAGNOSTIC_RESULT_VIEWS.LEGAL,
  )
  const themeGroups = selectDiagnosticThemeGroups(publicDiagnostic)
  const legalSummary = selectLegalDiagnosticSummary(publicDiagnostic)
  const sources = selectDiagnosticOfficialSources(
    publicDiagnostic,
    DIAGNOSTIC_RESULT_VIEWS.LEGAL,
  )
  const hasAbove100 = allResults.some(({ result }) => (
    result.current?.unit === 'percent' && Number(result.current?.value) > 100
  ))
  const summaryItems = [
    ['Indicadores com comparação disponível', legalSummary.comparableIndicatorCount],
    ['Referências alcançadas', legalSummary.maintainCount],
    ['Abaixo da referência', legalSummary.advanceCount],
    ['Sem comparação no período', legalSummary.unavailableComparisonCount],
  ]

  return (
    <article className="diagnostic-print-report">
      <header className="diagnostic-print-report__header">
        <p className="diagnostic-print-report__institution">Painel SESI-RS de Inteligência Municipal</p>
        <div className="diagnostic-print-report__title-row">
          <div>
            <h1>Diagnóstico educacional</h1>
            <p className="diagnostic-print-report__municipality">{municipio}</p>
          </div>
          <p className="diagnostic-print-report__cycle">PNE 2026–2036</p>
        </div>
        <p className="diagnostic-print-report__description">{description}</p>
        <p className="diagnostic-print-report__summary-reading">
          {buildPublicSummaryText(legalSummary)}
        </p>
        <dl className="diagnostic-print-report__summary">
          {summaryItems.map(([label, value]) => (
            <div key={label}>
              <dt>{label}</dt>
              <dd>{value}</dd>
            </div>
          ))}
        </dl>
      </header>

      <div className="diagnostic-print-report__themes">
        {themeGroups.map(({ results, theme }) => (
          <section className="diagnostic-print-theme" key={theme.id}>
            <div className="diagnostic-print-theme__indicators">
              <div className="diagnostic-print-theme__opening">
                <header className="diagnostic-print-theme__header">
                  <div>
                    <p>Tema {theme.visibleOrder}</p>
                    <h2>{theme.label}</h2>
                  </div>
                  <p>{results.length} {results.length === 1 ? 'indicador' : 'indicadores'}</p>
                </header>
                <DiagnosticPrintIndicator
                  goal={results[0].goal}
                  result={results[0].result}
                />
              </div>
              {results.slice(1).map(({ goal, result }) => (
                <DiagnosticPrintIndicator
                  goal={goal}
                  key={`${goal.goalId}-${result.indicatorId}`}
                  result={result}
                />
              ))}
            </div>
          </section>
        ))}
      </div>

      {sources.length ? (
        <section className="diagnostic-print-report__sources">
          <h2>Fontes oficiais</h2>
          <ul>
            {sources.map((source) => (
              <li key={source.id}>
                <strong>{source.organization}</strong>
                <span>{source.publicTitle} · {source.period}</span>
              </li>
            ))}
          </ul>
          {hasAbove100 ? (
            <p>Há resultado percentual acima de 100% neste município. O valor bruto foi preservado; esse comportamento pode decorrer da combinação entre matrículas por local de oferta e estimativas da população residente.</p>
          ) : null}
        </section>
      ) : null}

      <footer className="diagnostic-print-report__footer">
        <span>{municipio}</span>
        <span>Diagnóstico municipal — PNE 2026–2036</span>
      </footer>
    </article>
  )
}

function DiagnosticPrintIndicator({ goal, result }) {
  const isComplementary = result.mode === 'complementary'
  const isAvailable = result.dataStatus === 'available'
  const stateComparison = getPublicStateComparison(result)
  const supportingReadings = getPublicSupportingReadings(result)
  const publicReading = getPublicResultReading(result)
  const status = getPublicResultStatus(result)
  const contextReadings = supportingReadings.filter(({ kind }) => kind !== 'trajectory')
  const trajectoryReading = supportingReadings.find(({ kind }) => kind === 'trajectory')
  const comparisonItemCount = Number(Boolean(stateComparison?.reading)) + contextReadings.length
  const closingItemCount = Number(Boolean(trajectoryReading)) + Number(Boolean(publicReading))
  const measures = [
    {
      label: 'Município',
      value: getPublicCurrentValue(result),
      detail: Number.isFinite(result.current?.year) ? `Ano ${result.current.year}` : '',
    },
    ...(!isComplementary && isAvailable ? [
      {
        label: result.mode === 'tracking'
          ? 'Referência de acompanhamento'
          : 'Referência prevista na meta',
        value: formatPublicValue(result.indicatorReference?.value, result.current?.unit),
        detail: Number.isFinite(result.indicatorReference?.year)
          ? `Prazo ${result.indicatorReference.year}`
          : '',
      },
      {
        label: 'Distância',
        value: formatPublicDistance(result.distance, result.current?.unit),
      },
    ] : []),
    {
      label: 'Referência RS',
      value: stateComparison?.stateValue,
      detail: stateComparison ? `Ano ${stateComparison.year}` : '',
    },
    {
      label: 'Município x RS',
      value: stateComparison?.difference,
    },
  ].filter(({ value }) => value !== '' && value !== null && value !== undefined)

  return (
    <article className="diagnostic-print-indicator">
      <div className="diagnostic-print-indicator__top-row">
        <header className="diagnostic-print-indicator__header">
          <p>Meta {goal.goalId} — {goal.title}</p>
          <h3>{result.publicName}</h3>
          {!isComplementary && isAvailable ? <span>{status.label}</span> : null}
        </header>

        {measures.length ? (
          <dl className={`diagnostic-print-indicator__measures diagnostic-print-indicator__measures--count-${measures.length}`}>
            {measures.map(({ detail, label, value }) => (
              <div key={label}>
                <dt>{label}</dt>
                <dd>
                  <strong>{value}</strong>
                  {detail ? <span>{detail}</span> : null}
                </dd>
              </div>
            ))}
          </dl>
        ) : null}
      </div>

      {comparisonItemCount ? (
        <section className={`diagnostic-print-indicator__comparison-row diagnostic-print-indicator__comparison-row--count-${comparisonItemCount}`}>
          {stateComparison?.reading ? (
            <DiagnosticPrintReading title="Comparação com o RS">
              <p>{stateComparison.reading}</p>
            </DiagnosticPrintReading>
          ) : null}
          {contextReadings.map((reading) => (
            <DiagnosticPrintReading key={`${reading.kind}-${reading.title}`} title={reading.title}>
              {reading.lines.map((line) => <p key={line}>{line}</p>)}
            </DiagnosticPrintReading>
          ))}
        </section>
      ) : null}

      {closingItemCount ? (
        <section className={`diagnostic-print-indicator__closing-row diagnostic-print-indicator__closing-row--count-${closingItemCount}`}>
          {trajectoryReading ? (
            <DiagnosticPrintReading title={trajectoryReading.title}>
              {trajectoryReading.lines.map((line) => <p key={line}>{line}</p>)}
            </DiagnosticPrintReading>
          ) : null}
          {publicReading ? (
            <DiagnosticPrintReading title="Leitura do indicador">
              <p>{publicReading}</p>
            </DiagnosticPrintReading>
          ) : null}
        </section>
      ) : null}
    </article>
  )
}

function DiagnosticPrintReading({ children, title }) {
  return (
    <section className="diagnostic-print-indicator__reading">
      <strong>{title}</strong>
      <div>{children}</div>
    </section>
  )
}
