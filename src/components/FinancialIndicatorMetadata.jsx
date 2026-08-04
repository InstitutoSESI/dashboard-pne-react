import { DisclosureChevron } from './DisclosureChevron'

function hasText(value) {
  return value !== null && value !== undefined && String(value).trim().length > 0
}

function getPublishedRows(series) {
  if (!Array.isArray(series)) return []

  return series
    .filter((point) => point?.ano !== null && point?.ano !== undefined && Number.isFinite(Number(point?.valor)))
    .sort((left, right) => Number(left.ano) - Number(right.ano))
}

function DisclosureSummary({ description, title }) {
  return (
    <summary className="platform-support-disclosure__summary">
      <div>
        <h3>{title}</h3>
        <p>{description}</p>
      </div>
      <DisclosureChevron />
    </summary>
  )
}

export function FinancialIndicatorDisclosures({
  formatValue,
  indicator,
  metadata,
  series,
  showDataDisclosure = true,
  source,
}) {
  const rows = getPublishedRows(series)
  const sourceText = source ?? metadata?.financingSource
  const period = rows.length
    ? rows.length === 1
      ? String(rows[0].ano)
      : `${rows[0].ano}–${rows[rows.length - 1].ano}`
    : indicator?.currentYear
      ? String(indicator.currentYear)
      : 'Período não informado'
  const renderValue = typeof formatValue === 'function'
    ? formatValue
    : (value) => String(value)

  return (
    <div className="financial-detail-disclosures">
      {showDataDisclosure ? (
        <details className="platform-support-disclosure financial-detail-disclosure">
          <DisclosureSummary
            description="Tabela anual, unidade e regra da variação exibida."
            title="Dados usados no cálculo"
          />
          <div className="platform-support-disclosure__body financial-detail-disclosure__body">
            {rows.length ? (
              <div className="platform-data-table-region" role="region" aria-label={`Tabela anual de ${indicator?.label ?? 'dados usados no cálculo'}`} tabIndex="0">
                <table className="platform-data-table">
                  <caption className="u-sr-only">Dados anuais usados no cálculo de {indicator?.label}</caption>
                  <thead>
                    <tr>
                      <th scope="col">Exercício</th>
                      <th scope="col">Valor publicado</th>
                      <th scope="col">Unidade</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((row) => (
                      <tr key={row.ano}>
                        <th scope="row">{row.ano}</th>
                        <td className="platform-data-cell--numeric">{renderValue(row.valor)}</td>
                        <td>{indicator?.unitLabel ?? 'Conforme a fonte'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : <p>Não há valores anuais publicados para este indicador.</p>}
            <p className="financial-detail-disclosure__note">
              Período exibido: {period}. A variação só é apresentada quando há dois exercícios comparáveis; zero oficial permanece visível.
            </p>
          </div>
        </details>
      ) : null}

      <details className="platform-support-disclosure financial-detail-disclosure">
        <DisclosureSummary
          description="O que o indicador mede, por que importa e seus limites de leitura."
          title="Conceito e interpretação"
        />
        <div className="platform-support-disclosure__body financial-detail-disclosure__body">
          <dl className="financial-detail-disclosure__definition-list">
            {hasText(metadata?.definition) ? <div><dt>O que o indicador mede</dt><dd>{metadata.definition}</dd></div> : null}
            {hasText(metadata?.relevance) ? <div><dt>Por que é importante</dt><dd>{metadata.relevance}</dd></div> : null}
            {hasText(metadata?.referenceRule) ? <div><dt>Limite de interpretação</dt><dd>{metadata.referenceRule}</dd></div> : null}
          </dl>
        </div>
      </details>

      <details className="platform-support-disclosure financial-detail-disclosure">
        <DisclosureSummary
          description="Fonte oficial, competência, fórmula, regra aplicável e limitações."
          title="Fontes e metodologia"
        />
        <div className="platform-support-disclosure__body financial-detail-disclosure__body">
          <dl className="financial-detail-disclosure__definition-list">
            {hasText(sourceText) ? <div><dt>Fonte oficial</dt><dd>{sourceText}</dd></div> : null}
            <div><dt>Competência</dt><dd>{period}</dd></div>
            {hasText(metadata?.calculation) ? <div><dt>Fórmula</dt><dd>{metadata.calculation}</dd></div> : null}
            {hasText(metadata?.legalBasis) ? <div><dt>Regra legal</dt><dd>{metadata.legalBasis}</dd></div> : null}
            {hasText(metadata?.methodNote) ? <div><dt>Limitações</dt><dd>{metadata.methodNote}</dd></div> : null}
          </dl>
        </div>
      </details>
    </div>
  )
}
