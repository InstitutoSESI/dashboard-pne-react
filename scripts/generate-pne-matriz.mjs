import { createHash } from 'node:crypto'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import {
  parsePne2026Matriz,
  parsePne2026MatrizManifest,
  PNE_2026_MATRIZ_MANIFEST_SCHEMA,
  PNE_2026_MATRIZ_MUNICIPAL_FILE_PATTERN,
  PNE_2026_MATRIZ_SCHEMA,
  PNE_2026_MATRIZ_SCHEMAS,
  PNE_2026_MATRIZ_SOURCE_MANIFEST_SCHEMA,
  PNE_2026_MATRIZ_SOURCE_MANIFEST_SCHEMAS,
} from '../src/features/matriz/pne2026MatrizLoader.js'

/*
 * Ingestão versionada da Matriz de Prioridades.
 *
 * O artefato nasce na camada de pesquisa e chega fechado. Este gerador não
 * calcula severidade, associação entre meta e causa nem prova: valida o documento e o manifesto de
 * origem campo a campo, reconcilia seus hashes e publica a mesma informação em
 * `public/data/pne2026-matriz/`. A promoção usa staging, escrita atômica por
 * arquivo e rollback do lote quando qualquer troca falha.
 */

const MATRIZ_PUBLIC_ROOT = new URL('../public/data/pne2026-matriz/', import.meta.url)
const MATRIZ_MANIFEST_PATH = new URL('manifest.json', MATRIZ_PUBLIC_ROOT)

export const MATRIZ_GENERATOR_VERSION = 'pne2026-matriz-generator-v4'

const DEFAULT_INPUT_PATH = fileURLToPath(new URL('../.tmp/matriz/artefato/matriz.json', import.meta.url))
const DEFAULT_SOURCE_MANIFEST_PATH = fileURLToPath(
  new URL('../.tmp/matriz/artefato/matriz-manifest.json', import.meta.url),
)

const SOURCE_MANIFEST_FIELDS = [
  'builderVersion',
  'curation',
  'diagnosticReferenceDate',
  'inputSha256',
  'matrixSchemaVersion',
  'municipalityIbge7',
  'municipalityName',
  'outputs',
  'peerGroup',
  'schemaVersion',
  'sourceDiagnostic',
  'sourceWorkbook',
  'uf',
]
const SOURCE_CURATION_FIELDS = ['name', 'sha256', 'version']
const SOURCE_OUTPUT_FIELDS = ['byteSize', 'name', 'sha256']
const SOURCE_DIAGNOSTIC_FIELDS = [
  'builderVersion',
  'catalogSha256',
  'diagnosticCsvSha256',
  'path',
]
const SOURCE_WORKBOOK_FIELDS = ['schemaVersion', 'sha256']
const PEER_GROUP_FIELDS = ['band', 'criteria', 'expansions', 'n', 'populationPeriod', 'releaseId']

const SHA256_PATTERN = /^[a-f0-9]{64}$/
const IBGE7_PATTERN = /^\d{7}$/
const ISO_DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/

export class MatrizIngestionError extends Error {
  constructor(message) {
    super(message)
    this.name = 'MatrizIngestionError'
  }
}

function invariant(condition, message) {
  if (!condition) throw new MatrizIngestionError(`Matriz de Prioridades inválida: ${message}`)
}

function isRecord(value) {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value)
}

function assertExactFields(candidate, expectedFields, label) {
  invariant(isRecord(candidate), `${label} deve ser objeto.`)
  const expected = [...expectedFields].toSorted()
  const actual = Object.keys(candidate).toSorted()
  const unknown = actual.filter((field) => !expected.includes(field))
  const missing = expected.filter((field) => !actual.includes(field))
  invariant(!unknown.length, `${label} contém campos desconhecidos: ${unknown.join(', ')}.`)
  invariant(!missing.length, `${label} não contém: ${missing.join(', ')}.`)
}

function assertTextFields(candidate, fields, label) {
  for (const field of fields) {
    invariant(typeof candidate[field] === 'string', `${label}.${field} deve ser texto.`)
  }
}

function assertSha256(value, label) {
  invariant(typeof value === 'string' && SHA256_PATTERN.test(value), `${label} deve ser sha256.`)
}

function sha256(contents) {
  return createHash('sha256').update(contents).digest('hex')
}

function canonicalJson(value) {
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(',')}]`
  if (isRecord(value)) {
    return `{${Object.keys(value)
      .toSorted()
      .map((key) => `${JSON.stringify(key)}:${canonicalJson(value[key])}`)
      .join(',')}}`
  }
  return JSON.stringify(value)
}

function assertPeerGroup(candidate, label) {
  assertExactFields(candidate, PEER_GROUP_FIELDS, label)
  assertTextFields(candidate, ['band', 'criteria', 'populationPeriod', 'releaseId'], label)
  invariant(Number.isInteger(candidate.n) && candidate.n >= 20, `${label}.n deve ser inteiro maior ou igual a 20.`)
  assertSha256(candidate.releaseId, `${label}.releaseId`)
  invariant(Array.isArray(candidate.expansions), `${label}.expansions deve ser lista.`)
  candidate.expansions.forEach((item, index) => {
    invariant(typeof item === 'string', `${label}.expansions[${index}] deve ser texto.`)
  })
}

function samePeerGroup(left, right) {
  return canonicalJson(left) === canonicalJson(right)
}

export function parseSourceMatrizManifest(candidate) {
  assertExactFields(candidate, SOURCE_MANIFEST_FIELDS, 'matriz-manifest.json')
  invariant(
    PNE_2026_MATRIZ_SOURCE_MANIFEST_SCHEMAS.includes(candidate.schemaVersion),
    `schemaVersion deve estar entre ${PNE_2026_MATRIZ_SOURCE_MANIFEST_SCHEMAS.join(', ')}.`,
  )
  invariant(PNE_2026_MATRIZ_SCHEMAS.includes(candidate.matrixSchemaVersion), 'matrixSchemaVersion divergente.')
  assertTextFields(
    candidate,
    [
      'builderVersion',
      'diagnosticReferenceDate',
      'inputSha256',
      'matrixSchemaVersion',
      'municipalityIbge7',
      'municipalityName',
      'schemaVersion',
      'uf',
    ],
    'matriz-manifest.json',
  )
  invariant(IBGE7_PATTERN.test(candidate.municipalityIbge7), 'municipalityIbge7 inválido.')
  invariant(ISO_DATE_PATTERN.test(candidate.diagnosticReferenceDate), 'diagnosticReferenceDate inválida.')
  invariant(/^[A-Z]{2}$/.test(candidate.uf), 'uf inválida.')
  assertSha256(candidate.inputSha256, 'matriz-manifest.json.inputSha256')

  assertExactFields(candidate.curation, SOURCE_CURATION_FIELDS, 'matriz-manifest.json.curation')
  assertTextFields(candidate.curation, SOURCE_CURATION_FIELDS, 'matriz-manifest.json.curation')
  assertSha256(candidate.curation.sha256, 'matriz-manifest.json.curation.sha256')

  invariant(Array.isArray(candidate.outputs) && candidate.outputs.length === 1, 'outputs deve conter apenas matriz.json.')
  assertExactFields(candidate.outputs[0], SOURCE_OUTPUT_FIELDS, 'matriz-manifest.json.outputs[0]')
  assertTextFields(candidate.outputs[0], ['name', 'sha256'], 'matriz-manifest.json.outputs[0]')
  invariant(candidate.outputs[0].name === 'matriz.json', 'outputs[0].name deve ser matriz.json.')
  invariant(Number.isInteger(candidate.outputs[0].byteSize) && candidate.outputs[0].byteSize > 0, 'outputs[0].byteSize inválido.')
  assertSha256(candidate.outputs[0].sha256, 'matriz-manifest.json.outputs[0].sha256')

  assertPeerGroup(candidate.peerGroup, 'matriz-manifest.json.peerGroup')

  assertExactFields(candidate.sourceDiagnostic, SOURCE_DIAGNOSTIC_FIELDS, 'matriz-manifest.json.sourceDiagnostic')
  assertTextFields(candidate.sourceDiagnostic, SOURCE_DIAGNOSTIC_FIELDS, 'matriz-manifest.json.sourceDiagnostic')
  assertSha256(candidate.sourceDiagnostic.catalogSha256, 'matriz-manifest.json.sourceDiagnostic.catalogSha256')
  assertSha256(candidate.sourceDiagnostic.diagnosticCsvSha256, 'matriz-manifest.json.sourceDiagnostic.diagnosticCsvSha256')

  assertExactFields(candidate.sourceWorkbook, SOURCE_WORKBOOK_FIELDS, 'matriz-manifest.json.sourceWorkbook')
  assertTextFields(candidate.sourceWorkbook, SOURCE_WORKBOOK_FIELDS, 'matriz-manifest.json.sourceWorkbook')
  assertSha256(candidate.sourceWorkbook.sha256, 'matriz-manifest.json.sourceWorkbook.sha256')
  return structuredClone(candidate)
}

function reconcileSource(document, sourceManifest, rawInput) {
  const output = sourceManifest.outputs[0]
  invariant(output.byteSize === rawInput.byteLength, 'byteSize de matriz.json diverge do manifesto de origem.')
  invariant(output.sha256 === sha256(rawInput), 'sha256 de matriz.json diverge do manifesto de origem.')
  invariant(document.municipality.ibge7 === sourceManifest.municipalityIbge7, 'código municipal diverge do manifesto de origem.')
  invariant(document.municipality.name === sourceManifest.municipalityName, 'nome municipal diverge do manifesto de origem.')
  invariant(document.municipality.uf === sourceManifest.uf, 'UF diverge do manifesto de origem.')
  invariant(document.referenceDate === sourceManifest.diagnosticReferenceDate, 'data de referência diverge do manifesto de origem.')
  invariant(document.schemaVersion === sourceManifest.matrixSchemaVersion, 'schema do documento diverge do manifesto de origem.')
  invariant(samePeerGroup(document.peerGroup, sourceManifest.peerGroup), 'peerGroup diverge do manifesto de origem.')
  invariant(canonicalJson(document.curation) === canonicalJson({
    sha256: sourceManifest.curation.sha256,
    version: sourceManifest.curation.version,
  }), 'curation diverge do manifesto de origem.')
  invariant(
    canonicalJson(document.sourceDiagnostic) === canonicalJson({
      builderVersion: sourceManifest.sourceDiagnostic.builderVersion,
      catalogSha256: sourceManifest.sourceDiagnostic.catalogSha256,
      diagnosticCsvSha256: sourceManifest.sourceDiagnostic.diagnosticCsvSha256,
    }),
    'sourceDiagnostic diverge do manifesto de origem.',
  )
  invariant(
    canonicalJson(document.sourceWorkbook) === canonicalJson(sourceManifest.sourceWorkbook),
    'sourceWorkbook diverge do manifesto de origem.',
  )
}

function readPublishedManifest() {
  if (!fs.existsSync(MATRIZ_MANIFEST_PATH)) return null
  const candidate = JSON.parse(fs.readFileSync(MATRIZ_MANIFEST_PATH, 'utf8'))
  if (
    candidate.schemaVersion !== PNE_2026_MATRIZ_MANIFEST_SCHEMA
    || !PNE_2026_MATRIZ_SCHEMAS.includes(candidate.matrizSchemaVersion)
    || !PNE_2026_MATRIZ_SOURCE_MANIFEST_SCHEMAS.includes(candidate.sourceManifestSchemaVersion)
  ) return null
  return parsePne2026MatrizManifest(candidate)
}

export function buildManifest(previousManifest, entry, {
  matrizSchemaVersion = previousManifest?.matrizSchemaVersion ?? PNE_2026_MATRIZ_SCHEMA,
  sourceManifestSchemaVersion = previousManifest?.sourceManifestSchemaVersion
    ?? PNE_2026_MATRIZ_SOURCE_MANIFEST_SCHEMA,
} = {}) {
  const preserved = (previousManifest?.municipalities ?? []).filter(
    (municipality) => municipality.ibge7 !== entry.ibge7,
  )
  invariant(
    preserved.length === 0
      || (
        previousManifest.matrizSchemaVersion === matrizSchemaVersion
        && previousManifest.sourceManifestSchemaVersion === sourceManifestSchemaVersion
      ),
    `a release da coleção deve ser homogênea: as versões da nova ingestão (${matrizSchemaVersion}; ${sourceManifestSchemaVersion}) divergem do manifesto publicado (${previousManifest?.matrizSchemaVersion}; ${previousManifest?.sourceManifestSchemaVersion}) enquanto há municípios preservados. A troca de contrato exige republicar todos os municípios da coleção na mesma versão.`,
  )
  const manifest = {
    schemaVersion: PNE_2026_MATRIZ_MANIFEST_SCHEMA,
    matrizSchemaVersion,
    sourceManifestSchemaVersion,
    generatorVersion: MATRIZ_GENERATOR_VERSION,
    municipalFilePattern: PNE_2026_MATRIZ_MUNICIPAL_FILE_PATTERN,
    municipalities: [...preserved, entry].toSorted(
      (left, right) => left.ibge7.localeCompare(right.ibge7),
    ),
  }
  return parsePne2026MatrizManifest(manifest)
}

function identicalFile(targetPath, contents) {
  return fs.existsSync(targetPath) && fs.readFileSync(targetPath).equals(contents)
}

function promoteGeneratedFiles(files) {
  const changed = files.filter(({ contents, targetPath }) => !identicalFile(targetPath, contents))
  if (!changed.length) return { changed: 0, preserved: files.length }

  const stamp = `${process.pid}-${Date.now()}`
  const staged = changed.map(({ targetPath, contents }, index) => {
    fs.mkdirSync(path.dirname(targetPath), { recursive: true })
    const temporaryPath = path.join(path.dirname(targetPath), `.${path.basename(targetPath)}.${stamp}-${index}.tmp`)
    const backupPath = path.join(path.dirname(targetPath), `.${path.basename(targetPath)}.${stamp}-${index}.bak`)
    fs.writeFileSync(temporaryPath, contents)
    return { targetPath, temporaryPath, backupPath, hadTarget: fs.existsSync(targetPath) }
  })

  const promoted = []
  try {
    for (const file of staged) {
      if (file.hadTarget) fs.renameSync(file.targetPath, file.backupPath)
      try {
        fs.renameSync(file.temporaryPath, file.targetPath)
        promoted.push(file)
      } catch (error) {
        if (file.hadTarget && fs.existsSync(file.backupPath)) fs.renameSync(file.backupPath, file.targetPath)
        throw error
      }
    }
    for (const file of staged) {
      if (fs.existsSync(file.backupPath)) fs.unlinkSync(file.backupPath)
    }
  } catch (error) {
    for (const file of promoted.toReversed()) {
      if (fs.existsSync(file.targetPath)) fs.unlinkSync(file.targetPath)
      if (file.hadTarget && fs.existsSync(file.backupPath)) fs.renameSync(file.backupPath, file.targetPath)
    }
    for (const file of staged) {
      if (fs.existsSync(file.temporaryPath)) fs.unlinkSync(file.temporaryPath)
      if (fs.existsSync(file.backupPath) && !fs.existsSync(file.targetPath)) {
        fs.renameSync(file.backupPath, file.targetPath)
      }
    }
    throw new MatrizIngestionError(`Falha na promoção transacional: ${error instanceof Error ? error.message : String(error)}`)
  }
  return { changed: changed.length, preserved: files.length - changed.length }
}

export function ingestMatriz(inputPath, sourceManifestPath) {
  const rawInput = fs.readFileSync(inputPath)
  const rawSourceManifest = fs.readFileSync(sourceManifestPath)
  const matriz = parsePne2026Matriz(JSON.parse(rawInput.toString('utf8')))
  const sourceManifest = parseSourceMatrizManifest(JSON.parse(rawSourceManifest.toString('utf8')))
  reconcileSource(matriz, sourceManifest, rawInput)

  const output = Buffer.from(`${canonicalJson(matriz)}\n`, 'utf8')
  const municipalPath = PNE_2026_MATRIZ_MUNICIPAL_FILE_PATTERN.replace(
    '{municipalityId}',
    matriz.municipality.ibge7,
  )
  const entry = {
    ibge7: matriz.municipality.ibge7,
    name: matriz.municipality.name,
    uf: matriz.municipality.uf,
    referenceDate: matriz.referenceDate,
    path: municipalPath,
    inputSha256: sha256(rawInput),
    sourceManifestSha256: sha256(rawSourceManifest),
    outputSha256: sha256(output),
    outputByteSize: output.byteLength,
    peerGroup: structuredClone(matriz.peerGroup),
  }
  const manifest = buildManifest(readPublishedManifest(), entry, {
    matrizSchemaVersion: matriz.schemaVersion,
    sourceManifestSchemaVersion: sourceManifest.schemaVersion,
  })
  const manifestContents = Buffer.from(`${JSON.stringify(manifest, null, 2)}\n`, 'utf8')

  // Revalidação final antes de qualquer escrita pública.
  parsePne2026Matriz(JSON.parse(output.toString('utf8')))
  parsePne2026MatrizManifest(JSON.parse(manifestContents.toString('utf8')))

  const promotion = promoteGeneratedFiles([
    {
      targetPath: fileURLToPath(new URL(municipalPath, MATRIZ_PUBLIC_ROOT)),
      contents: output,
    },
    { targetPath: fileURLToPath(MATRIZ_MANIFEST_PATH), contents: manifestContents },
  ])
  return { entry, manifest, matriz, promotion }
}

function parseArguments(argv) {
  const inputIndex = argv.indexOf('--input')
  const manifestIndex = argv.indexOf('--source-manifest')
  if (inputIndex === -1 && manifestIndex === -1) {
    return {
      input: DEFAULT_INPUT_PATH,
      sourceManifest: DEFAULT_SOURCE_MANIFEST_PATH,
    }
  }
  if (inputIndex === -1 || !argv[inputIndex + 1] || manifestIndex === -1 || !argv[manifestIndex + 1]) {
    throw new MatrizIngestionError(
      'Informe os artefatos de origem: node scripts/generate-pne-matriz.mjs --input <matriz.json> --source-manifest <matriz-manifest.json>',
    )
  }
  return {
    input: path.resolve(argv[inputIndex + 1]),
    sourceManifest: path.resolve(argv[manifestIndex + 1]),
  }
}

function run() {
  const { input, sourceManifest } = parseArguments(process.argv.slice(2))
  const { entry, matriz, promotion } = ingestMatriz(input, sourceManifest)
  const causeCount = matriz.priorityGoals.reduce((total, goal) => total + goal.causes.length, 0)
  console.log(
    [
      `Matriz publicada: ${entry.ibge7} ${entry.name}/${entry.uf} (${entry.referenceDate})`,
      `Metas prioritarias: ${matriz.priorityGoals.length} | causas: ${causeCount} | grupo de pares: ${matriz.peerGroup.n}`,
      `Entrada sha256: ${entry.inputSha256}`,
      `Saida   sha256: ${entry.outputSha256} (${entry.outputByteSize} bytes)`,
      `Promocao: ${promotion.changed} arquivo(s) alterado(s), ${promotion.preserved} preservado(s)`,
      `Arquivo: public/data/pne2026-matriz/${entry.path}`,
    ].join('\n'),
  )
}

if (process.argv[1] === fileURLToPath(import.meta.url)) run()
