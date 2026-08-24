import type { MatrizPlanEntry } from '../../domain/matrizFrontsStorage.js'
import type { MatrizDocument } from './matrizTypes.js'
import { buildMatrizFrentesWorkbook } from './matrizFrentesWorkbook.js'

export async function downloadMatrizFrentesXlsx(
  matriz: MatrizDocument,
  selection: readonly (string | MatrizPlanEntry)[],
) {
  const { fileName, sheets } = buildMatrizFrentesWorkbook(matriz, selection)
  const { default: writeXlsxFile } = await import('write-excel-file/browser')
  await writeXlsxFile(sheets, {
    fontFamily: 'Arial',
    fontSize: 10,
  }).toFile(fileName)
  return fileName
}
