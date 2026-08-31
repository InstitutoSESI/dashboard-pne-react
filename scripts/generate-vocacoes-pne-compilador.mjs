import {
  existsSync,
  mkdirSync,
  readFileSync,
  renameSync,
  rmSync,
  writeFileSync,
} from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import {
  buildCompilerArtifacts,
  VocacoesPneCompilerError,
} from './lib/vocacoes-pne-compilador.mjs'

const DEFAULT_FS = Object.freeze({
  existsSync,
  mkdirSync,
  readFileSync,
  renameSync,
  rmSync,
  writeFileSync,
})

function parseArguments(argv) {
  const options = { check: false }
  for (const argument of argv) {
    if (argument === '--check') options.check = true
    else throw new VocacoesPneCompilerError(`argumento desconhecido: ${argument}`)
  }
  return options
}

function sameBytes(filePath, expected, fs = DEFAULT_FS) {
  return fs.existsSync(filePath) && fs.readFileSync(filePath).equals(expected)
}

function checkOutputs(outputs) {
  const divergent = outputs.filter(({ filePath, bytes }) => !sameBytes(filePath, bytes))
  if (divergent.length > 0) {
    throw new VocacoesPneCompilerError(
      `saída do compilador divergente: ${divergent.map(({ filePath }) => filePath).join(', ')}`,
    )
  }
}

export function promoteTransactional(
  outputs,
  { fs = DEFAULT_FS, runId = `${process.pid}` } = {},
) {
  const changed = outputs.filter(
    ({ filePath, bytes }) => !sameBytes(filePath, bytes, fs),
  )
  if (changed.length === 0) return 0

  const staged = []
  const journal = []
  let promotionSucceeded = false
  try {
    for (const { filePath, bytes } of changed) {
      fs.mkdirSync(path.dirname(filePath), { recursive: true })
      const temporaryPath = `${filePath}.tmp-${runId}`
      fs.writeFileSync(temporaryPath, bytes)
      staged.push({ filePath, temporaryPath })
    }
    for (const { filePath, temporaryPath } of staged) {
      const backupPath = `${filePath}.backup-${runId}`
      const existed = fs.existsSync(filePath)
      if (existed) fs.renameSync(filePath, backupPath)
      journal.push({ filePath, backupPath, existed })
      fs.renameSync(temporaryPath, filePath)
    }
    promotionSucceeded = true
  } catch (error) {
    const rollbackErrors = []
    for (const entry of [...journal].reverse()) {
      try {
        if (fs.existsSync(entry.filePath)) fs.rmSync(entry.filePath)
        if (entry.existed) {
          if (!fs.existsSync(entry.backupPath)) {
            throw new Error(`backup de rollback ausente: ${entry.backupPath}`)
          }
          fs.renameSync(entry.backupPath, entry.filePath)
        }
      } catch (rollbackError) {
        rollbackErrors.push(rollbackError)
      }
    }
    if (rollbackErrors.length > 0) {
      throw new VocacoesPneCompilerError(
        'promoção falhou e o rollback ficou incompleto; backups recuperáveis foram preservados',
        { cause: new AggregateError([error, ...rollbackErrors], 'rollback incompleto') },
      )
    }
    throw new VocacoesPneCompilerError('promoção transacional do compilador falhou', {
      cause: error,
    })
  } finally {
    for (const { temporaryPath } of staged) {
      if (fs.existsSync(temporaryPath)) fs.rmSync(temporaryPath)
    }
    if (promotionSucceeded) {
      for (const { backupPath } of journal) {
        if (fs.existsSync(backupPath)) fs.rmSync(backupPath)
      }
    }
  }
  return changed.length
}

export function run(argv = process.argv.slice(2)) {
  const options = parseArguments(argv)
  const artifacts = buildCompilerArtifacts()
  const outputs = [
    { filePath: artifacts.paths.publicOutput, bytes: artifacts.publicBytes },
    { filePath: artifacts.paths.traceOutput, bytes: artifacts.traceBytes },
  ]
  if (options.check) {
    checkOutputs(outputs)
    console.log('OK: projeção narrativa e registro interno idênticos byte a byte.')
    return { changed: 0, ...artifacts }
  }
  const changed = promoteTransactional(outputs)
  console.log(
    `${changed === 0 ? 'Preservados' : 'Gerados'} dois artefatos do compilador; `
    + `${changed} arquivo(s) alterado(s).`,
  )
  return { changed, ...artifacts }
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
