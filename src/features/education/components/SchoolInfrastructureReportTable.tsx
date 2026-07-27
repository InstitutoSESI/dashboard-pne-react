import {
  formatSchoolInfrastructureReportCell,
  SCHOOL_INFRASTRUCTURE_INDICATOR_ORDER,
  SCHOOL_INFRASTRUCTURE_METHODOLOGY,
  SCHOOL_INFRASTRUCTURE_PUBLIC_COPY,
  SCHOOL_INFRASTRUCTURE_SOURCE,
  selectSchoolInfrastructureResult,
  type SchoolInfrastructureContract,
} from '../../../data/schoolInfrastructureContract'
import { ReportNote, ReportTableRegion } from './MunicipalTechnicalReportLayout'

export function SchoolInfrastructureReportTable({
  contract,
}: {
  contract: SchoolInfrastructureContract
}) {
  return (
    <>
      <ReportTableRegion
        ariaLabel="Infraestrutura escolar: todas as escolas e rede municipal"
        className="municipal-technical-report__school-infrastructure-table-wrap"
        description="Disponibilidade observada nas escolas em atividade."
        metadata={`${SCHOOL_INFRASTRUCTURE_SOURCE} · ${contract.referenceYear}`}
        title="Bloco C — Infraestrutura"
        variant="compact"
      >
        <table className="municipal-technical-report__table municipal-technical-report__table--school-infrastructure">
          <caption className="municipal-technical-report__table-caption--semantic">
            Indicadores de infraestrutura escolar por recorte
          </caption>
          <thead>
            <tr>
              <th scope="col">Dimensão</th>
              <th scope="col">Todas as escolas</th>
              <th scope="col">Rede municipal</th>
            </tr>
          </thead>
          <tbody>
            {SCHOOL_INFRASTRUCTURE_INDICATOR_ORDER.map((indicatorKey) => (
              <tr key={indicatorKey}>
                <th scope="row">{SCHOOL_INFRASTRUCTURE_PUBLIC_COPY[indicatorKey].shortLabel}</th>
                <td className="municipal-technical-report__numeric">
                  {formatSchoolInfrastructureReportCell(
                    selectSchoolInfrastructureResult(contract, indicatorKey, 'total'),
                  )}
                </td>
                <td className="municipal-technical-report__numeric">
                  {formatSchoolInfrastructureReportCell(
                    selectSchoolInfrastructureResult(contract, indicatorKey, 'municipal'),
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </ReportTableRegion>
      <ReportNote placement="table">{SCHOOL_INFRASTRUCTURE_METHODOLOGY}</ReportNote>
    </>
  )
}
