import { createHash } from 'node:crypto'
import {
  existsSync,
  mkdirSync,
  readFileSync,
  readdirSync,
  renameSync,
  rmSync,
  writeFileSync,
} from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import {
  buildVocacoesPnePublicationQueue,
  canonicalJson,
  createVocacoesPneRollbackProposal,
  VocacoesPnePublicationError,
} from './lib/vocacoes-pne-publication.mjs'

const ROOT = fileURLToPath(new URL('../', import.meta.url))
const GENERATED_DIRECTORY = path.join(
  ROOT,
  'src',
  'features',
  'vocacoes-regiao',
  'generated',
)

export const VOCACOES_PNE_PUBLICATION_PATHS = Object.freeze({
  legacyManifest: path.join(ROOT, 'public', 'data', 'vocacoes-regiao', 'manifest.json'),
  narrativeRegistry: path.join(GENERATED_DIRECTORY, 'vocacoesPneNarrativeRegistry.json'),
  narrativeDirectory: GENERATED_DIRECTORY,
  transferCoverage: path.join(
    ROOT,
    'scripts',
    'checks',
    'fixtures',
    'vocacoes-pne',
    'transfer-coverage-r9.json',
  ),
  output: path.join(GENERATED_DIRECTORY, 'vocacoesPnePublicationQueue.json'),
})

const DEFAULT_FS = Object.freeze({
  existsSync,
  mkdirSync,
  readFileSync,
  readdirSync,
  renameSync,
  rmSync,
  writeFileSync,
})

function fail(message, options) {
  throw new VocacoesPnePublicationError(message, options)
}

export function parseArguments(argv) {
  const options = { check: false, rollbackSlug: null }
  for (const argument of argv) {
    if (argument === '--check') {
      if (options.check) fail('argumento duplicado: --check')
      options.check = true
    } else if (argument.startsWith('--rollback=')) {
      if (options.rollbackSlug !== null) fail('argumento duplicado: --rollback')
      const slug = argument.slice('--rollback='.length)
      if (slug.length === 0) fail('--rollback exige um slug')
      options.rollbackSlug = slug
    } else {
      fail(`argumento desconhecido: ${argument}`)
    }
  }
  if (options.check && options.rollbackSlug !== null) {
    fail('--check e --rollback são incompatíveis')
  }
  return Object.freeze(options)
}

function readJson(filePath, label, fs) {
  try {
    return JSON.parse(fs.readFileSync(filePath, 'utf8'))
  } catch (error) {
    fail(`não foi possível ler ${label}: ${filePath}`, { cause: error })
  }
}

function listNarrativeDocuments(paths, fs, narrativeRegistry) {
  let names
  try {
    names = fs.readdirSync(paths.narrativeDirectory, { withFileTypes: true })
  } catch (error) {
    fail('não foi possível listar os documentos narrativos gerados', { cause: error })
  }
  const expectedHashes = new Set(
    Array.isArray(narrativeRegistry?.entries)
      ? narrativeRegistry.entries
        .map((entry) => entry?.narrativeSha256)
        .filter((value) => typeof value === 'string')
      : [],
  )
  return names
    .filter((entry) => entry.isFile())
    .map((entry) => entry.name)
    .filter((name) => (
      /^vocacoesPne[A-Z].*\.json$/u.test(name)
      && name !== 'vocacoesPneNarrativeRegistry.json'
      && name !== 'vocacoesPnePublicationQueue.json'
    ))
    .sort()
    .map((name) => {
      const raw = fs.readFileSync(path.join(paths.narrativeDirectory, name), 'utf8')
      return { path: name, raw }
    })
    .filter(({ raw }) => expectedHashes.has(
      createHash('sha256').update(raw, 'utf8').digest('hex'),
    ))
}

export function buildPublicationArtifacts({
  paths = VOCACOES_PNE_PUBLICATION_PATHS,
  fs = DEFAULT_FS,
} = {}) {
  const legacyManifest = readJson(paths.legacyManifest, 'manifesto legado', fs)
  const narrativeRegistry = readJson(paths.narrativeRegistry, 'registro narrativo', fs)
  const transferCoverage = readJson(paths.transferCoverage, 'cobertura de transferência', fs)
  const narrativeDocuments = listNarrativeDocuments(paths, fs, narrativeRegistry)
  const queue = buildVocacoesPnePublicationQueue({
    legacyManifest,
    narrativeRegistry,
    narrativeDocuments,
    transferCoverage,
  })
  return Object.freeze({
    queue,
    bytes: Buffer.from(canonicalJson(queue), 'utf8'),
    narrativeRegistry,
  })
}

function sameBytes(filePath, expected, fs) {
  return fs.existsSync(filePath) && fs.readFileSync(filePath).equals(expected)
}

export function checkPublicationOutput(filePath, expected, fs = DEFAULT_FS) {
  if (!sameBytes(filePath, expected, fs)) {
    fail(`fila de publicação divergente: ${filePath}`)
  }
}

export function writePublicationOutputAtomic(
  filePath,
  bytes,
  { fs = DEFAULT_FS, runId = `${process.pid}` } = {},
) {
  if (sameBytes(filePath, bytes, fs)) return false
  fs.mkdirSync(path.dirname(filePath), { recursive: true })
  const temporaryPath = `${filePath}.tmp-${runId}`
  try {
    fs.writeFileSync(temporaryPath, bytes, { flag: 'wx' })
    fs.renameSync(temporaryPath, filePath)
  } catch (error) {
    fail('gravação atômica da fila de publicação falhou', { cause: error })
  } finally {
    if (fs.existsSync(temporaryPath)) fs.rmSync(temporaryPath)
  }
  return true
}

export function run(
  argv = process.argv.slice(2),
  {
    paths = VOCACOES_PNE_PUBLICATION_PATHS,
    fs = DEFAULT_FS,
    logger = console,
    runId,
  } = {},
) {
  const options = parseArguments(argv)
  const artifacts = buildPublicationArtifacts({ paths, fs })

  if (options.rollbackSlug !== null) {
    const proposal = createVocacoesPneRollbackProposal(
      artifacts.narrativeRegistry,
      options.rollbackSlug,
    )
    logger.log(canonicalJson(proposal).trimEnd())
    return Object.freeze({ mode: 'rollback', changed: false, proposal, ...artifacts })
  }

  if (options.check) {
    checkPublicationOutput(paths.output, artifacts.bytes, fs)
    logger.log('OK: fila narrativa regional idêntica byte a byte.')
    return Object.freeze({ mode: 'check', changed: false, ...artifacts })
  }

  const changed = writePublicationOutputAtomic(
    paths.output,
    artifacts.bytes,
    { fs, runId },
  )
  logger.log(changed ? 'Fila narrativa regional gerada.' : 'Fila narrativa regional preservada.')
  return Object.freeze({ mode: 'generate', changed, ...artifacts })
}

const isMain = (
  process.argv[1]
  && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)
)

if (isMain) {
  try {
    run()
  } catch (error) {
    console.error(error instanceof Error ? error.message : error)
    process.exitCode = 1
  }
}
