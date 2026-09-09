import { buildPmeReportWorkbook } from './pmeReportWorkbook'
import type { PmeReportModel } from './pmeReports'

export async function downloadPmeReportXlsx(report: PmeReportModel): Promise<string> {
  const workbook = buildPmeReportWorkbook(report)
  const { default: writeXlsxFile } = await import('write-excel-file/browser')
  await writeXlsxFile(workbook.sheets, { fontFamily: 'Arial', fontSize: 10 }).toFile(workbook.fileName)
  return workbook.fileName
}
