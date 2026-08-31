import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import {
  canonicalJson,
  MATRIZ_GENERATOR_VERSION,
  MATRIZ_MANIFEST_PATH,
  MATRIZ_PUBLIC_ROOT,
  MatrizIngestionError,
  parseSourceMatrizManifest,
  readPublishedManifest,
  reconcileSource,
  sha256,
} from './generate-pne-matriz.mjs'
import {
  parsePne2026Matriz,
  parsePne2026MatrizManifest,
  PNE_2026_MATRIZ_MANIFEST_SCHEMA,
  PNE_2026_MATRIZ_MUNICIPAL_FILE_PATTERN,
} from '../src/features/matriz/pne2026MatrizLoader.js'

const REPO_ROOT = fileURLToPath(new URL('../', import.meta.url))
const TEMP_ROOT = fileURLToPath(new URL('../.tmp/', import.meta.url))
const PUBLIC_ROOT = fileURLToPath(MATRIZ_PUBLIC_ROOT)
const PUBLIC_MANIFEST_PATH = fileURLToPath(MATRIZ_MANIFEST_PATH)
const RS_REGISTRY_PATH = fileURLToPath(new URL('../config/municipalities/rs.json', import.meta.url))
const CONTRACT_PATH = fileURLToPath(
  new URL('../contracts/pne2026-goal-indicator-contract.json', import.meta.url),
)

const COLLECTION_SCHEMA_VERSION = 'pne-priority-matrix-collection-v1'
const COLLECTION_MANIFEST_NAME = 'collection-manifest.json'
const COLLECTION_FIELDS = [
  'builderVersion',
  'counts',
  'invariants',
  'intermediateArtifacts',
  'matrixBuilderVersion',
  'matrixSchemaVersion',
  'municipalities',
  'municipalityCount',
  'officialDiagnosticReleaseId',
  'referenceDate',
  'schemaVersion',
  'sourceCatalog',
  'sourceContract',
  'sourceObservations',
  'sourceRegistry',
  'stateCode',
]
const COLLECTION_ENTRY_FIELDS = [
  'manifestByteSize',
  'manifestPath',
  'manifestSha256',
  'matrixByteSize',
  'matrixPath',
  'matrixSha256',
  'municipalityIbge7',
  'municipalityName',
  'priorityGoalIds',
]
const PUBLIC_MANIFEST_FIELDS = [
  'generatorVersion',
  'matrizSchemaVersion',
  'municipalFilePattern',
  'municipalities',
  'schemaVersion',
  'sourceManifestSchemaVersion',
]
const IBGE7_PATTERN = /^\d{7}$/
const SHA256_PATTERN = /^[a-f0-9]{64}$/

function invariant(condition, message) {
  if (!condition) throw new MatrizIngestionError(`Coleção da Matriz de Prioridades inválida: ${message}`)
}

function isRecord(value) {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value)
}

function assertExactFields(candidate, fields, label) {
  invariant(isRecord(candidate), `${label} deve ser objeto.`)
  const expected = [...fields].toSorted()
  const actual = Object.keys(candidate).toSorted()
  invariant(
    JSON.stringify(actual) === JSON.stringify(expected),
    `${label} deve conter exatamente ${expected.join(', ')}; recebeu ${actual.join(', ')}.`,
  )
}

function assertSha(value, label) {
  invariant(typeof value === 'string' && SHA256_PATTERN.test(value), `${label} deve ser sha256.`)
}

function readJson(filePath, label) {
  invariant(fs.existsSync(filePath), `${label} ausente: ${filePath}.`)
  try {
    return JSON.parse(fs.readFileSync(filePath, 'utf8'))
  } catch (error) {
    throw new MatrizIngestionError(
      `${label} não é JSON válido: ${error instanceof Error ? error.message : String(error)}`,
    )
  }
}

function readCanonicalRegistry() {
  const raw = fs.readFileSync(RS_REGISTRY_PATH)
  const registry = JSON.parse(raw.toString('utf8'))
  invariant(registry.schemaVersion === 'municipality-registry-v1', 'schema do registro RS divergente.')
  invariant(registry.stateCode === 'RS', 'registro canônico pertence a outra UF.')
  invariant(registry.municipalityCount === 497, 'registro canônico do RS deve conter 497 municípios.')
  invariant(
    Array.isArray(registry.municipalities)
      && registry.municipalities.length === registry.municipalityCount,
    'lista do registro canônico do RS é incoerente.',
  )
  const byId = new Map()
  for (const record of registry.municipalities) {
    invariant(typeof record.ibgeCode === 'string' && IBGE7_PATTERN.test(record.ibgeCode), 'ibgeCode canônico inválido.')
    invariant(!byId.has(record.ibgeCode), `ibgeCode canônico duplicado: ${record.ibgeCode}.`)
    byId.set(record.ibgeCode, record)
  }
  return { byId, raw, registry }
}

function parseCollectionManifest(candidate, registryRaw, contractRaw) {
  assertExactFields(candidate, COLLECTION_FIELDS, COLLECTION_MANIFEST_NAME)
  invariant(candidate.schemaVersion === COLLECTION_SCHEMA_VERSION, 'schemaVersion da coleção divergente.')
  invariant(candidate.stateCode === 'RS', 'a coleção deve ser exclusivamente do RS.')
  invariant(candidate.matrixSchemaVersion === 'matriz-4.0.0', 'a coleção deve usar matriz-4.0.0.')
  invariant(candidate.municipalityCount === 497, 'a coleção deve declarar 497 municípios.')
  invariant(Array.isArray(candidate.municipalities), 'municipalities deve ser lista.')
  invariant(candidate.municipalities.length === 497, 'municipalities deve conter 497 entradas.')
  assertSha(candidate.sourceRegistry?.sha256, 'sourceRegistry.sha256')
  assertSha(candidate.sourceContract?.sha256, 'sourceContract.sha256')
  invariant(candidate.sourceRegistry.sha256 === sha256(registryRaw), 'registro da pesquisa diverge do registro canônico da plataforma.')
  invariant(candidate.sourceContract.sha256 === sha256(contractRaw), 'contrato da pesquisa diverge do contrato canônico da plataforma.')
  assertSha(candidate.officialDiagnosticReleaseId, 'officialDiagnosticReleaseId')
  invariant(Array.isArray(candidate.sourceObservations) && candidate.sourceObservations.length > 0, 'sourceObservations deve registrar as edições lidas.')
  invariant(candidate.invariants?.municipalityIdentity === 'ibge7_text', 'a identidade municipal deve ser ibge7_text.')
  invariant(candidate.invariants?.formulasChanged === false, 'a coleção não pode declarar alteração de fórmulas.')
  invariant(candidate.invariants?.databaseWrite === 'not_requested', 'a geração não pode ter usado banco.')
  invariant(candidate.invariants?.networkAccess === 'not_requested', 'a geração não pode ter usado rede.')
  for (const [index, entry] of candidate.municipalities.entries()) {
    assertExactFields(entry, COLLECTION_ENTRY_FIELDS, `municipalities[${index}]`)
    invariant(IBGE7_PATTERN.test(entry.municipalityIbge7), `código inválido em municipalities[${index}].`)
    assertSha(entry.matrixSha256, `municipalities[${index}].matrixSha256`)
    assertSha(entry.manifestSha256, `municipalities[${index}].manifestSha256`)
    invariant(
      entry.matrixPath === `municipios/${entry.municipalityIbge7}/matriz.json`,
      `matrixPath não canônico para ${entry.municipalityIbge7}.`,
    )
    invariant(
      entry.manifestPath === `municipios/${entry.municipalityIbge7}/matriz-manifest.json`,
      `manifestPath não canônico para ${entry.municipalityIbge7}.`,
    )
    invariant(Array.isArray(entry.priorityGoalIds), `priorityGoalIds inválido para ${entry.municipalityIbge7}.`)
  }
  return structuredClone(candidate)
}

function ingestCollectionSources(collectionRoot, collectionManifest, registryById) {
  const entries = []
  const outputs = []
  const seen = new Set()
  const goalCounts = new Map()
  let matrixSchemaVersion = null
  let sourceManifestSchemaVersion = null

  for (const sourceEntry of collectionManifest.municipalities) {
    const code = sourceEntry.municipalityIbge7
    const registryRecord = registryById.get(code)
    invariant(registryRecord, `município fora do registro canônico: ${code}.`)
    invariant(!seen.has(code), `município repetido: ${code}.`)
    seen.add(code)
    invariant(sourceEntry.municipalityName === registryRecord.name, `nome divergente para ${code}.`)

    const matrixPath = path.resolve(collectionRoot, ...sourceEntry.matrixPath.split('/'))
    const sourceManifestPath = path.resolve(collectionRoot, ...sourceEntry.manifestPath.split('/'))
    invariant(matrixPath.startsWith(`${collectionRoot}${path.sep}`), `matrixPath escapa da coleção para ${code}.`)
    invariant(sourceManifestPath.startsWith(`${collectionRoot}${path.sep}`), `manifestPath escapa da coleção para ${code}.`)
    const rawInput = fs.readFileSync(matrixPath)
    const rawSourceManifest = fs.readFileSync(sourceManifestPath)
    invariant(rawInput.byteLength === sourceEntry.matrixByteSize, `tamanho de matriz.json diverge para ${code}.`)
    invariant(sha256(rawInput) === sourceEntry.matrixSha256, `hash de matriz.json diverge para ${code}.`)
    invariant(rawSourceManifest.byteLength === sourceEntry.manifestByteSize, `tamanho do manifesto diverge para ${code}.`)
    invariant(sha256(rawSourceManifest) === sourceEntry.manifestSha256, `hash do manifesto diverge para ${code}.`)

    const matriz = parsePne2026Matriz(JSON.parse(rawInput.toString('utf8')))
    const sourceManifest = parseSourceMatrizManifest(JSON.parse(rawSourceManifest.toString('utf8')))
    reconcileSource(matriz, sourceManifest, rawInput)
    invariant(matriz.municipality.ibge7 === code, `documento pertence a outro município: ${code}.`)
    invariant(matriz.municipality.name === registryRecord.name, `nome interno divergente para ${code}.`)
    invariant(matriz.municipality.uf === 'RS', `UF interna divergente para ${code}.`)
    invariant(matriz.referenceDate === collectionManifest.referenceDate, `data interna divergente para ${code}.`)
    invariant(
      matriz.peerGroup.releaseId === collectionManifest.officialDiagnosticReleaseId,
      `release oficial divergente para ${code}.`,
    )
    invariant(
      JSON.stringify(matriz.priorityGoals.map((goal) => goal.goalId))
        === JSON.stringify(sourceEntry.priorityGoalIds),
      `lista de metas prioritárias divergente para ${code}.`,
    )
    for (const goal of matriz.priorityGoals) {
      goalCounts.set(goal.goalId, (goalCounts.get(goal.goalId) ?? 0) + 1)
    }
    matrixSchemaVersion ??= matriz.schemaVersion
    sourceManifestSchemaVersion ??= sourceManifest.schemaVersion
    invariant(matrixSchemaVersion === matriz.schemaVersion, `schema municipal heterogêneo em ${code}.`)
    invariant(sourceManifestSchemaVersion === sourceManifest.schemaVersion, `schema de manifesto heterogêneo em ${code}.`)

    const output = Buffer.from(`${canonicalJson(matriz)}\n`, 'utf8')
    const publicPath = PNE_2026_MATRIZ_MUNICIPAL_FILE_PATTERN.replace('{municipalityId}', code)
    entries.push({
      ibge7: code,
      name: registryRecord.name,
      uf: 'RS',
      referenceDate: matriz.referenceDate,
      path: publicPath,
      inputSha256: sha256(rawInput),
      sourceManifestSha256: sha256(rawSourceManifest),
      outputSha256: sha256(output),
      outputByteSize: output.byteLength,
      peerGroup: structuredClone(matriz.peerGroup),
    })
    outputs.push({ contents: output, relativePath: publicPath })
  }

  invariant(seen.size === registryById.size, `coleção cobre ${seen.size} de ${registryById.size} municípios.`)
  for (const code of registryById.keys()) invariant(seen.has(code), `município canônico ausente: ${code}.`)
  const declaredGoalCounts = collectionManifest.counts?.byPriorityGoalId
  invariant(isRecord(declaredGoalCounts), 'counts.byPriorityGoalId deve ser objeto.')
  invariant(
    canonicalJson(Object.fromEntries([...goalCounts].toSorted(([left], [right]) => left.localeCompare(right))))
      === canonicalJson(declaredGoalCounts),
    'contagens por meta prioritária divergem do manifesto da coleção.',
  )
  return { entries, matrixSchemaVersion, outputs, sourceManifestSchemaVersion }
}

function buildPublishedManifest(previousManifest, incoming) {
  const preserved = (previousManifest?.municipalities ?? []).filter((entry) => entry.uf !== 'RS')
  if (preserved.length > 0) {
    invariant(previousManifest.matrizSchemaVersion === incoming.matrixSchemaVersion, 'schema da coleção preservada é incompatível.')
    invariant(previousManifest.sourceManifestSchemaVersion === incoming.sourceManifestSchemaVersion, 'schema dos manifestos preservados é incompatível.')
  }
  const manifest = {
    schemaVersion: PNE_2026_MATRIZ_MANIFEST_SCHEMA,
    matrizSchemaVersion: incoming.matrixSchemaVersion,
    sourceManifestSchemaVersion: incoming.sourceManifestSchemaVersion,
    generatorVersion: MATRIZ_GENERATOR_VERSION,
    municipalFilePattern: PNE_2026_MATRIZ_MUNICIPAL_FILE_PATTERN,
    municipalities: [...preserved, ...incoming.entries].toSorted(
      (left, right) => left.ibge7.localeCompare(right.ibge7),
    ),
  }
  assertExactFields(manifest, PUBLIC_MANIFEST_FIELDS, 'manifesto público')
  return parsePne2026MatrizManifest(manifest)
}

function assertManagedTempPath(candidate, expectedPrefix) {
  const resolved = path.resolve(candidate)
  invariant(path.dirname(resolved) === path.resolve(TEMP_ROOT), `path temporário fora de .tmp: ${resolved}.`)
  invariant(path.basename(resolved).startsWith(expectedPrefix), `path temporário inesperado: ${resolved}.`)
  return resolved
}

function removeManagedTree(candidate, expectedPrefix) {
  const resolved = assertManagedTempPath(candidate, expectedPrefix)
  if (fs.existsSync(resolved)) fs.rmSync(resolved, { recursive: true })
}

function stageFile(stageRoot, relativePath, contents) {
  const stagedPath = path.join(stageRoot, ...relativePath.split('/'))
  const currentPath = path.join(PUBLIC_ROOT, ...relativePath.split('/'))
  fs.mkdirSync(path.dirname(stagedPath), { recursive: true })
  if (fs.existsSync(currentPath) && fs.readFileSync(currentPath).equals(contents)) {
    fs.linkSync(currentPath, stagedPath)
    return 'preserved'
  }
  fs.writeFileSync(stagedPath, contents)
  return 'changed'
}

function validateStagedPublication(stageRoot, manifest) {
  const expected = new Set(['manifest.json', ...manifest.municipalities.map((entry) => entry.path)])
  const actual = new Set()
  const visit = (directory) => {
    for (const item of fs.readdirSync(directory, { withFileTypes: true })) {
      const itemPath = path.join(directory, item.name)
      if (item.isDirectory()) visit(itemPath)
      else if (item.isFile()) actual.add(path.relative(stageRoot, itemPath).split(path.sep).join('/'))
      else invariant(false, `tipo de arquivo inesperado no staging: ${itemPath}.`)
    }
  }
  visit(stageRoot)
  invariant(canonicalJson([...actual].toSorted()) === canonicalJson([...expected].toSorted()), 'inventário do staging diverge do manifesto público.')
  const parsedManifest = parsePne2026MatrizManifest(
    JSON.parse(fs.readFileSync(path.join(stageRoot, 'manifest.json'), 'utf8')),
  )
  invariant(canonicalJson(parsedManifest) === canonicalJson(manifest), 'manifesto staged diverge do manifesto validado.')
  for (const entry of manifest.municipalities) {
    const filePath = path.join(stageRoot, ...entry.path.split('/'))
    const raw = fs.readFileSync(filePath)
    invariant(raw.byteLength === entry.outputByteSize, `tamanho público divergente para ${entry.ibge7}.`)
    invariant(sha256(raw) === entry.outputSha256, `hash público divergente para ${entry.ibge7}.`)
    const matriz = parsePne2026Matriz(JSON.parse(raw.toString('utf8')))
    invariant(matriz.municipality.ibge7 === entry.ibge7, `identidade pública divergente para ${entry.ibge7}.`)
    invariant(matriz.municipality.name === entry.name, `nome público divergente para ${entry.ibge7}.`)
    invariant(matriz.municipality.uf === entry.uf, `UF pública divergente para ${entry.ibge7}.`)
    invariant(matriz.referenceDate === entry.referenceDate, `data pública divergente para ${entry.ibge7}.`)
  }
}

function listTreeFiles(root) {
  if (!fs.existsSync(root)) return []
  const files = []
  const visit = (directory) => {
    for (const item of fs.readdirSync(directory, { withFileTypes: true })) {
      const itemPath = path.join(directory, item.name)
      if (item.isDirectory()) visit(itemPath)
      else if (item.isFile()) files.push(path.relative(root, itemPath).split(path.sep).join('/'))
      else invariant(false, `tipo de arquivo inesperado na promoção: ${itemPath}.`)
    }
  }
  visit(root)
  return files.toSorted()
}

function promoteStagedTree(stageRoot, manifest) {
  const backupRoot = assertManagedTempPath(
    path.join(TEMP_ROOT, `.pne2026-matriz-backup-${process.pid}-${Date.now()}`),
    '.pne2026-matriz-backup-',
  )
  const expectedFiles = listTreeFiles(stageRoot)
  invariant(expectedFiles.includes('manifest.json'), 'staging sem manifesto público.')
  const expectedSet = new Set(expectedFiles)
  const currentFiles = listTreeFiles(PUBLIC_ROOT)
  const staleFiles = currentFiles.filter((relativePath) => !expectedSet.has(relativePath))
  const promotionOrder = [
    ...expectedFiles.filter((relativePath) => relativePath !== 'manifest.json'),
    'manifest.json',
  ]
  const backups = []
  const promoted = []

  fs.mkdirSync(PUBLIC_ROOT, { recursive: true })
  fs.mkdirSync(backupRoot)

  const backupExisting = (relativePath) => {
    const targetPath = path.join(PUBLIC_ROOT, ...relativePath.split('/'))
    const backupPath = path.join(backupRoot, ...relativePath.split('/'))
    fs.mkdirSync(path.dirname(backupPath), { recursive: true })
    fs.renameSync(targetPath, backupPath)
    backups.push(relativePath)
  }

  try {
    for (const relativePath of staleFiles) backupExisting(relativePath)

    for (const relativePath of promotionOrder) {
      const stagedPath = path.join(stageRoot, ...relativePath.split('/'))
      const targetPath = path.join(PUBLIC_ROOT, ...relativePath.split('/'))
      if (fs.existsSync(targetPath) && fs.readFileSync(targetPath).equals(fs.readFileSync(stagedPath))) {
        continue
      }
      if (fs.existsSync(targetPath)) backupExisting(relativePath)
      fs.mkdirSync(path.dirname(targetPath), { recursive: true })
      fs.renameSync(stagedPath, targetPath)
      promoted.push(relativePath)
    }

    // O manifesto é o marcador de commit e foi promovido por último. Assim, uma
    // coleção nova só se torna carregável depois que todos os documentos existem.
    validateStagedPublication(PUBLIC_ROOT, manifest)
  } catch (error) {
    const rollbackErrors = []
    for (const relativePath of promoted.toReversed()) {
      const targetPath = path.join(PUBLIC_ROOT, ...relativePath.split('/'))
      try {
        if (fs.existsSync(targetPath)) fs.unlinkSync(targetPath)
      } catch (rollbackError) {
        rollbackErrors.push(`${relativePath}: ${rollbackError instanceof Error ? rollbackError.message : String(rollbackError)}`)
      }
    }
    for (const relativePath of backups.toReversed()) {
      const targetPath = path.join(PUBLIC_ROOT, ...relativePath.split('/'))
      const backupPath = path.join(backupRoot, ...relativePath.split('/'))
      try {
        if (fs.existsSync(targetPath)) fs.unlinkSync(targetPath)
        if (fs.existsSync(backupPath)) {
          fs.mkdirSync(path.dirname(targetPath), { recursive: true })
          fs.renameSync(backupPath, targetPath)
        }
      } catch (rollbackError) {
        rollbackErrors.push(`${relativePath}: ${rollbackError instanceof Error ? rollbackError.message : String(rollbackError)}`)
      }
    }
    if (fs.existsSync(stageRoot)) removeManagedTree(stageRoot, '.pne2026-matriz-staging-')
    if (!rollbackErrors.length && fs.existsSync(backupRoot)) {
      removeManagedTree(backupRoot, '.pne2026-matriz-backup-')
    }
    const rollbackDetail = rollbackErrors.length
      ? ` Rollback incompleto: ${rollbackErrors.join(' | ')}. Backups preservados em ${backupRoot}.`
      : ' Rollback concluído.'
    throw new MatrizIngestionError(
      `Falha na promoção transacional da coleção: ${error instanceof Error ? error.message : String(error)}.${rollbackDetail}`,
    )
  }
  removeManagedTree(stageRoot, '.pne2026-matriz-staging-')
  removeManagedTree(backupRoot, '.pne2026-matriz-backup-')
}

export function ingestMatrizCollection(collectionRootInput) {
  const collectionRoot = path.resolve(collectionRootInput)
  const { byId, raw: registryRaw } = readCanonicalRegistry()
  const contractRaw = fs.readFileSync(CONTRACT_PATH)
  const rawCollectionManifest = fs.readFileSync(path.join(collectionRoot, COLLECTION_MANIFEST_NAME))
  const collectionManifest = parseCollectionManifest(
    JSON.parse(rawCollectionManifest.toString('utf8')),
    registryRaw,
    contractRaw,
  )
  const incoming = ingestCollectionSources(collectionRoot, collectionManifest, byId)
  const publicManifest = buildPublishedManifest(readPublishedManifest(), incoming)
  const manifestContents = Buffer.from(`${JSON.stringify(publicManifest, null, 2)}\n`, 'utf8')

  fs.mkdirSync(TEMP_ROOT, { recursive: true })
  const stageRoot = assertManagedTempPath(
    path.join(TEMP_ROOT, `.pne2026-matriz-staging-${process.pid}-${Date.now()}`),
    '.pne2026-matriz-staging-',
  )
  invariant(!fs.existsSync(stageRoot), `staging já existe: ${stageRoot}.`)
  fs.mkdirSync(stageRoot)
  let changed = 0
  let preserved = 0
  try {
    const incomingPaths = new Set(incoming.outputs.map((item) => item.relativePath))
    for (const output of incoming.outputs) {
      if (stageFile(stageRoot, output.relativePath, output.contents) === 'preserved') preserved += 1
      else changed += 1
    }
    for (const entry of publicManifest.municipalities) {
      if (incomingPaths.has(entry.path)) continue
      const currentPath = path.join(PUBLIC_ROOT, ...entry.path.split('/'))
      invariant(fs.existsSync(currentPath), `arquivo preservado ausente: ${entry.path}.`)
      const contents = fs.readFileSync(currentPath)
      invariant(contents.byteLength === entry.outputByteSize, `tamanho preservado divergente: ${entry.path}.`)
      invariant(sha256(contents) === entry.outputSha256, `hash preservado divergente: ${entry.path}.`)
      stageFile(stageRoot, entry.path, contents)
      preserved += 1
    }
    fs.writeFileSync(path.join(stageRoot, 'manifest.json'), manifestContents)
    validateStagedPublication(stageRoot, publicManifest)
    const existingManifest = fs.existsSync(PUBLIC_MANIFEST_PATH)
      ? fs.readFileSync(PUBLIC_MANIFEST_PATH)
      : null
    if (existingManifest?.equals(manifestContents) && changed === 0) {
      removeManagedTree(stageRoot, '.pne2026-matriz-staging-')
      return {
        changed: 0,
        collectionManifestSha256: sha256(rawCollectionManifest),
        manifest: publicManifest,
        preserved,
        promoted: false,
      }
    }
    promoteStagedTree(stageRoot, publicManifest)
    return {
      changed: changed + 1,
      collectionManifestSha256: sha256(rawCollectionManifest),
      manifest: publicManifest,
      preserved,
      promoted: true,
    }
  } catch (error) {
    if (fs.existsSync(stageRoot)) removeManagedTree(stageRoot, '.pne2026-matriz-staging-')
    throw error
  }
}

function parseArguments(argv) {
  const index = argv.indexOf('--collection')
  if (index === -1 || !argv[index + 1]) {
    throw new MatrizIngestionError(
      'Informe a coleção: node scripts/generate-pne-matriz-collection.mjs --collection <diretório>.',
    )
  }
  return path.resolve(argv[index + 1])
}

function run() {
  const collectionRoot = parseArguments(process.argv.slice(2))
  const result = ingestMatrizCollection(collectionRoot)
  console.log([
    `Coleção publicada: ${result.manifest.municipalities.length} municípios`,
    `Manifesto da coleção sha256: ${result.collectionManifestSha256}`,
    `Promoção: ${result.promoted ? 'concluída' : 'dispensada (conteúdo idêntico)'}`,
    `Arquivos alterados: ${result.changed} | preservados por conteúdo: ${result.preserved}`,
    `Destino: ${path.relative(REPO_ROOT, PUBLIC_ROOT)}`,
  ].join('\n'))
}

if (process.argv[1] === fileURLToPath(import.meta.url)) run()
