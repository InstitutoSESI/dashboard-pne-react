import { buildCadernoDecisionWorkbook } from './cadernoDecisionWorkbook.js'
import type { CadernoDocument } from './cadernoTypes'

export async function downloadCadernoDecisionXlsx(
  caderno: CadernoDocument,
  selectedKeys: readonly string[],
) {
  const { fileName, sheets } = buildCadernoDecisionWorkbook(caderno, selectedKeys)
  const { default: writeXlsxFile } = await import('write-excel-file/browser')
  await writeXlsxFile(sheets, {
    fontFamily: 'Arial',
    fontSize: 10,
  }).toFile(fileName)
  return fileName
}
