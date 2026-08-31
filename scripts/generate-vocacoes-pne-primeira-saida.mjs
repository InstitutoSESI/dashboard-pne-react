import { createHash } from 'node:crypto'
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
  buildFirstOutputArtifact,
  PrimeiraSaidaError,
} from './lib/vocacoes-pne-primeira-saida.mjs'
import { loadVocabulario } from './lib/vocacoes-pne-linter.mjs'
import {
  loadCatalogoMecanismos,
  loadCatalogoReferencias,
  loadRegistroSeries,
  loadRegrasUniverso,
} from './lib/vocacoes-pne-registro.mjs'

const ROOT = fileURLToPath(new URL('../', import.meta.url))
const FIXTURE_DIRECTORY = path.join(
  ROOT,
  'scripts',
  'checks',
  'fixtures',
  'vocacoes-pne',
)
const RESEARCH_PATH = path.join(
  FIXTURE_DIRECTORY,
  'primeira-saida-pesquisa-vale-do-sinos.json',
)
const AUTHORSHIP_PATH = path.join(
  FIXTURE_DIRECTORY,
  'primeira-saida-autoria.json',
)
const OUTPUT_PATH = path.join(
  FIXTURE_DIRECTORY,
  'primeira-saida-vale-do-sinos.json',
)
const RESEARCH_RELATIVE_PATH = (
  'scripts/checks/fixtures/vocacoes-pne/'
  + 'primeira-saida-pesquisa-vale-do-sinos.json'
)

function sha256(bytes) {
  return createHash('sha256').update(bytes).digest('hex')
}

function canonicalJson(value) {
  return `${JSON.stringify(value, null, 2)}\n`
}

function loadJson(filePath) {
  return JSON.parse(readFileSync(filePath, 'utf8'))
}

function buildDependencies() {
  const mecanismos = loadCatalogoMecanismos()
  const referencias = loadCatalogoReferencias()
  return {
    vocab: loadVocabulario(),
    pairDependencies: {
      mecanismos,
      registro: loadRegistroSeries(),
      regras: loadRegrasUniverso(),
    },
    cardDependencies: { mecanismos, referencias },
  }
}

export function buildExpectedOutput() {
  const researchBytes = readFileSync(RESEARCH_PATH)
  const research = JSON.parse(researchBytes.toString('utf8'))
  const authorship = loadJson(AUTHORSHIP_PATH)
  return buildFirstOutputArtifact(
    research,
    authorship,
    {
      path: RESEARCH_RELATIVE_PATH,
      sha256: sha256(researchBytes),
      byteSize: researchBytes.length,
    },
    buildDependencies(),
  )
}

function atomicWrite(filePath, content) {
  mkdirSync(path.dirname(filePath), { recursive: true })
  const temporaryPath = `${filePath}.tmp-${process.pid}`
  try {
    writeFileSync(temporaryPath, content, 'utf8')
    renameSync(temporaryPath, filePath)
  } finally {
    if (existsSync(temporaryPath)) rmSync(temporaryPath)
  }
}

function parseArguments(argv) {
  let check = false
  let researchSource = null
  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index]
    if (argument === '--check') {
      check = true
    } else if (argument === '--research-source') {
      if (!argv[index + 1]) throw new PrimeiraSaidaError('--research-source requer caminho')
      researchSource = path.resolve(argv[index + 1])
      index += 1
    } else {
      throw new PrimeiraSaidaError(`argumento desconhecido: ${argument}`)
    }
  }
  return { check, researchSource }
}

function assertResearchHandshake(researchSource) {
  if (researchSource === null) return
  if (!existsSync(researchSource)) {
    throw new PrimeiraSaidaError(`artefato de pesquisa ausente: ${researchSource}`)
  }
  const imported = readFileSync(RESEARCH_PATH)
  const source = readFileSync(researchSource)
  if (!imported.equals(source)) {
    throw new PrimeiraSaidaError(
      `handshake divergente: ${RESEARCH_RELATIVE_PATH} não é idêntico a ${researchSource}`,
    )
  }
}

export function run(argv = process.argv.slice(2)) {
  const { check, researchSource } = parseArguments(argv)
  assertResearchHandshake(researchSource)
  const content = canonicalJson(buildExpectedOutput())
  if (check) {
    if (!existsSync(OUTPUT_PATH)) {
      throw new PrimeiraSaidaError(`saída ausente: ${OUTPUT_PATH}`)
    }
    if (readFileSync(OUTPUT_PATH, 'utf8') !== content) {
      throw new PrimeiraSaidaError('saída da primeira direção divergente; execute sem --check')
    }
    console.log(`OK: primeira saída Vocações × PNE idêntica (${OUTPUT_PATH})`)
    return
  }
  atomicWrite(OUTPUT_PATH, content)
  console.log(`OK: primeira saída Vocações × PNE escrita (${OUTPUT_PATH})`)
}

const isMainModule = (
  process.argv[1]
  && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)
)

if (isMainModule) {
  try {
    run()
  } catch (error) {
    console.error(error instanceof Error ? error.message : error)
    process.exitCode = 1
  }
}
