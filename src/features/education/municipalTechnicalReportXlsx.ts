import {
  buildMunicipalTechnicalReportWorkbook,
  type MunicipalTechnicalReportWorkbookInput,
} from './municipalTechnicalReportWorkbook.js'

export async function downloadMunicipalTechnicalReportXlsx(
  input: MunicipalTechnicalReportWorkbookInput,
) {
  const workbook = buildMunicipalTechnicalReportWorkbook(input)
  const { default: writeXlsxFile } = await import('write-excel-file/browser')
  await writeXlsxFile(workbook.sheets, {
    fontFamily: 'Arial',
    fontSize: 10,
  }).toFile(workbook.fileName)
  return workbook.fileName
}
