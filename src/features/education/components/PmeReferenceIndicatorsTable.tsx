import { Fragment, useMemo } from 'react'
import type { Pne2026PublicDiagnosticV2 } from '../../diagnostic/diagnosticTypes'
import {
  buildPmeReferenceTableModel,
  type PmeReferenceDataSources,
  type PmeReferenceTableModel,
} from '../pmeReferenceTableViewModel'
import { ReportMetrics, ReportTableRegion } from './MunicipalTechnicalReportLayout'

interface PmeReferenceIndicatorsTableProps {
  dataSources?: PmeReferenceDataSources
  diagnostic: Pne2026PublicDiagnosticV2 | null
  error?: string | null
  loading?: boolean
}

function PmeScreenTable({ model }: { model: PmeReferenceTableModel }) {
  return (
    <ReportTableRegion
      ariaLabel="Tabela de referências do PNE 2026–2036. Deslize horizontalmente para consultar todas as colunas."
      className="municipal-technical-report__pme-table-scroll municipal-technical-report__pme-screen"
      focusable
      variant="historical"
    >
      <table className="municipal-technical-report__pme-table municipal-technical-report__pme-table--screen">
        <caption>Referências do PNE 2026–2036 aplicáveis ao planejamento municipal</caption>
        <colgroup>
          <col className="municipal-technical-report__pme-col-id" />
          <col className="municipal-technical-report__pme-col-description" />
          <col className="municipal-technical-report__pme-col-year" />
          <col className="municipal-technical-report__pme-col-component" />
          <col className="municipal-technical-report__pme-col-component" />
          <col className="municipal-technical-report__pme-col-result" />
          <col className="municipal-technical-report__pme-col-target" />
          <col className="municipal-technical-report__pme-col-effort" />
          <col className="municipal-technical-report__pme-col-source" />
        </colgroup>
        <thead>
          <tr>
            <th rowSpan={2} scope="col">Meta / indicador</th>
            <th rowSpan={2} scope="col">Descrição</th>
            <th colSpan={4} scope="colgroup">Cálculo no último ano disponível</th>
            <th rowSpan={2} scope="col">Meta de referência do PNE</th>
            <th rowSpan={2} scope="col">Situação atual em relação à referência</th>
            <th rowSpan={2} scope="col">Fonte</th>
          </tr>
          <tr>
            <th scope="col">Ano</th>
            <th scope="col">Numerador</th>
            <th scope="col">Denominador</th>
            <th scope="col">Resultado atual</th>
          </tr>
        </thead>
        <tbody>
          {model.groups.map((group) => (
            <Fragment key={`theme:${group.id}`}>
              <tr className="municipal-technical-report__pme-theme">
                <th colSpan={9} scope="rowgroup">{group.label}</th>
              </tr>
              {group.rows.map((row) => (
                <tr key={row.key}>
                  <th scope="row">
                    <span>{row.goalLabel}</span>
                    <small>{row.indicatorLabel}</small>
                  </th>
                  <td className="municipal-technical-report__pme-description">
                    {row.description}
                    {row.relationshipLabel ? <small>{row.relationshipLabel}</small> : null}
                  </td>
                  <td className="municipal-technical-report__numeric">{row.year}</td>
                  <td className="municipal-technical-report__numeric">{row.numerator}</td>
                  <td className="municipal-technical-report__numeric">{row.denominator}</td>
                  <td className="municipal-technical-report__numeric municipal-technical-report__pme-current">{row.currentResult}</td>
                  <td className="municipal-technical-report__numeric municipal-technical-report__pme-target">{row.target}</td>
                  <td className={row.effort.atOrBeyondReference ? 'municipal-technical-report__pme-position--at-or-beyond' : undefined}>
                    {row.effort.text}
                  </td>
                  <td>{row.source}</td>
                </tr>
              ))}
            </Fragment>
          ))}
        </tbody>
      </table>
    </ReportTableRegion>
  )
}

function PmePrintTable({ model }: { model: PmeReferenceTableModel }) {
  return (
    <div className="municipal-technical-report__pme-print municipal-technical-report__table-region--stacked" data-print-variant="stacked">
      <table className="municipal-technical-report__pme-table municipal-technical-report__pme-table--print">
        <caption>Referências do PNE 2026–2036 aplicáveis ao planejamento municipal</caption>
        <colgroup>
          <col className="municipal-technical-report__pme-print-col-id" />
          <col className="municipal-technical-report__pme-print-col-description" />
          <col className="municipal-technical-report__pme-print-col-calculation" />
          <col className="municipal-technical-report__pme-print-col-target" />
          <col className="municipal-technical-report__pme-print-col-effort" />
          <col className="municipal-technical-report__pme-print-col-source" />
        </colgroup>
        <thead>
          <tr>
            <th scope="col">Meta / indicador</th>
            <th scope="col">Descrição</th>
            <th scope="col">Cálculo no último ano disponível</th>
            <th scope="col">Meta de referência do PNE</th>
            <th scope="col">Situação atual em relação à referência</th>
            <th scope="col">Fonte</th>
          </tr>
        </thead>
        <tbody>
          {model.groups.map((group) => (
            <Fragment key={`print-theme:${group.id}`}>
              <tr className="municipal-technical-report__pme-theme">
                <th colSpan={6} scope="rowgroup">{group.label}</th>
              </tr>
              {group.rows.map((row) => (
                <tr key={`print:${row.key}`}>
                  <th scope="row">
                    <span>{row.goalLabel}</span>
                    <small>{row.indicatorLabel}</small>
                  </th>
                  <td>
                    {row.description}
                    {row.relationshipLabel ? <small>{row.relationshipLabel}</small> : null}
                  </td>
                  <td>
                    <dl className="municipal-technical-report__pme-calculation">
                      <div><dt>Ano</dt><dd>{row.year}</dd></div>
                      <div><dt>Numerador</dt><dd>{row.numerator}</dd></div>
                      <div><dt>Denominador</dt><dd>{row.denominator}</dd></div>
                      <div><dt>Resultado atual</dt><dd>{row.currentResult}</dd></div>
                    </dl>
                  </td>
                  <td>{row.target}</td>
                  <td className={row.effort.atOrBeyondReference ? 'municipal-technical-report__pme-position--at-or-beyond' : undefined}>
                    {row.effort.text}
                  </td>
                  <td>{row.source}</td>
                </tr>
              ))}
            </Fragment>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function PmeReferenceIndicatorsTable({
  dataSources,
  diagnostic,
  error,
  loading = false,
}: PmeReferenceIndicatorsTableProps) {
  const model = useMemo(
    () => diagnostic ? buildPmeReferenceTableModel(diagnostic, dataSources) : null,
    [dataSources, diagnostic],
  )

  if (loading) {
    return (
      <p className="municipal-technical-report__pme-status" role="status">
        Carregando as referências do PNE 2026–2036...
      </p>
    )
  }

  if (error || !model?.indicatorCount) {
    return (
      <p className="municipal-technical-report__pme-status">
        Não há referências do PNE 2026–2036 disponíveis para este município.
      </p>
    )
  }

  return (
    <div className="municipal-technical-report__pme">
      <ReportMetrics
        ariaLabel="Resumo da tabela de referências do PNE"
        compact
        items={[
          { label: 'Indicadores', value: model.indicatorCount },
          { label: 'Com comparação direta', value: model.quantitativeCalculableCount },
          { label: 'Acompanhamento descritivo', value: model.nonQuantitativeCalculableCount },
          { label: 'Temas', value: model.themeCount },
        ]}
      />

      <PmeScreenTable model={model} />
      <PmePrintTable model={model} />

      <div className="municipal-technical-report__pme-method">
        <p>
          A situação atual compara o valor municipal e a referência apenas quando
          direção, unidade e valores são metodologicamente compatíveis. A redação
          distingue referências mínimas de limites máximos.
        </p>
        <p>
          Componentes parciais e indicadores contextuais são apresentados como apoio
          ao planejamento e não encerram a avaliação do ciclo futuro.
        </p>
      </div>

      <div className="municipal-technical-report__pme-sources">
        <h4>Fontes utilizadas no painel</h4>
        <ul>
          {model.sources.map((source) => (
            <li key={source.id}>
              {source.organization ? <strong>{source.organization}</strong> : null}
              {source.organization ? ' — ' : null}
              {source.title}
              {source.period ? `, ${source.period}` : ''}
              {source.url ? <> · <a href={source.url}>fonte oficial</a></> : null}
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}
