import { createHash } from 'node:crypto'
import {
  existsSync,
  readFileSync,
  renameSync,
  unlinkSync,
  writeFileSync,
} from 'node:fs'
import path from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

import {
  buildSecondOutputArtifact,
  SEGUNDA_SAIDA_CONTRACT,
  validateResearchArtifact,
} from './lib/vocacoes-pne-segunda-saida.mjs'
import { loadVocabulario } from './lib/vocacoes-pne-linter.mjs'
import {
  loadCatalogoMecanismos,
  loadCatalogoReferencias,
  loadRegistroSeries,
  loadRegrasUniverso,
} from './lib/vocacoes-pne-registro.mjs'

const fixtureDirectory = new URL('./checks/fixtures/vocacoes-pne/', import.meta.url)
const researchUrl = new URL(
  'segunda-saida-pesquisa-vale-do-sinos.json',
  fixtureDirectory,
)
const authorshipUrl = new URL('segunda-saida-autoria.json', fixtureDirectory)
const outputUrl = new URL('segunda-saida-vale-do-sinos.json', fixtureDirectory)

function loadDependencies() {
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

function sha256(bytes) {
  return createHash('sha256').update(bytes).digest('hex')
}

function parseJson(bytes, label) {
  try {
    return JSON.parse(bytes.toString('utf8'))
  } catch (error) {
    throw new Error(`${label}: JSON inválido`, { cause: error })
  }
}

function writeAtomicIfChanged(targetUrl, bytes) {
  if (existsSync(targetUrl) && readFileSync(targetUrl).equals(bytes)) return false
  const targetPath = fileURLToPath(targetUrl)
  const temporaryPath = `${targetPath}.tmp-${process.pid}`
  try {
    writeFileSync(temporaryPath, bytes)
    renameSync(temporaryPath, targetPath)
  } finally {
    if (existsSync(temporaryPath)) unlinkSync(temporaryPath)
  }
  return true
}

function parseArguments(argv) {
  const options = {
    check: false,
    importResearch: false,
    researchSource: null,
  }
  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index]
    if (argument === '--check') {
      options.check = true
    } else if (argument === '--import-research') {
      options.importResearch = true
    } else if (argument === '--research-source') {
      const value = argv[index + 1]
      if (!value || value.startsWith('--')) {
        throw new Error('--research-source exige um path')
      }
      options.researchSource = path.resolve(value)
      index += 1
    } else {
      throw new Error(`argumento desconhecido: ${argument}`)
    }
  }
  if (options.check && options.importResearch) {
    throw new Error('--check e --import-research são incompatíveis')
  }
  if (options.importResearch && options.researchSource === null) {
    throw new Error('--import-research exige --research-source')
  }
  return options
}

function importResearchArtifact(sourcePath, dependencies) {
  const sourceBytes = readFileSync(sourcePath)
  const research = parseJson(sourceBytes, sourcePath)
  validateResearchArtifact(research, dependencies.pairDependencies)
  writeAtomicIfChanged(researchUrl, sourceBytes)
  return sourceBytes
}

export function buildExpectedOutput() {
  const dependencies = loadDependencies()
  const researchBytes = readFileSync(researchUrl)
  const research = parseJson(researchBytes, fileURLToPath(researchUrl))
  const authorship = parseJson(
    readFileSync(authorshipUrl),
    fileURLToPath(authorshipUrl),
  )
  const researchReference = {
    path: SEGUNDA_SAIDA_CONTRACT.researchFixturePath,
    sha256: sha256(researchBytes),
    byteSize: researchBytes.length,
  }
  return buildSecondOutputArtifact(
    research,
    authorship,
    researchReference,
    dependencies,
  )
}

function checkResearchHandshake(sourcePath) {
  if (sourcePath === null) return
  const sourceBytes = readFileSync(sourcePath)
  const fixtureBytes = readFileSync(researchUrl)
  if (!sourceBytes.equals(fixtureBytes)) {
    throw new Error(
      'handshake falhou: a fonte de pesquisa difere do artefato importado',
    )
  }
}

function main() {
  const options = parseArguments(process.argv.slice(2))
  const dependencies = loadDependencies()
  if (options.importResearch) {
    importResearchArtifact(options.researchSource, dependencies)
  }
  checkResearchHandshake(options.researchSource)
  const expected = buildExpectedOutput()
  const expectedBytes = Buffer.from(`${JSON.stringify(expected, null, 2)}\n`, 'utf8')
  if (options.check) {
    if (!existsSync(outputUrl) || !readFileSync(outputUrl).equals(expectedBytes)) {
      throw new Error(
        'segunda saída divergente; execute npm run generate:vocacoes-pne-segunda-saida',
      )
    }
    console.log(
      `Segunda saída válida: ${expected.summary.publishedCount} publicadas, `
      + `${expected.summary.retainedCount} retidas.`,
    )
    return
  }
  const changed = writeAtomicIfChanged(outputUrl, expectedBytes)
  console.log(
    `${changed ? 'Gerada' : 'Preservada'} segunda saída: `
    + `${expected.summary.publishedCount} publicadas, `
    + `${expected.summary.retainedCount} retidas.`,
  )
}

const isMain = (
  process.argv[1]
  && pathToFileURL(path.resolve(process.argv[1])).href === import.meta.url
)
if (isMain) main()
