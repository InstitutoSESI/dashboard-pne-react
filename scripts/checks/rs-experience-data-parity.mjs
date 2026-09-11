import { createHash } from 'node:crypto'
import { lstat, readFile, readdir, realpath } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

async function inventory(directory) {
  const entries = []
  async function walk(current, prefix = '') {
    for (const entry of (await readdir(current, { withFileTypes: true })).sort((a, b) => a.name.localeCompare(b.name, 'en'))) {
      const name = prefix ? `${prefix}/${entry.name}` : entry.name
      const fullPath = path.join(current, entry.name)
      if (entry.isSymbolicLink()) throw new Error(`O artefato de release contém link simbólico: ${name}`)
      if (entry.isDirectory()) await walk(fullPath, name)
      else if (entry.isFile()) {
        const bytes = await readFile(fullPath)
        entries.push({ path: name, size: bytes.length, sha256: createHash('sha256').update(bytes).digest('hex') })
      } else throw new Error(`Tipo de arquivo inesperado no artefato: ${name}`)
    }
  }
  await walk(directory)
  if (!entries.length) throw new Error('A raiz de dados de release está vazia.')
  return entries
}

/** Read-only release gate; never builds, regenerates or promotes public data. */
export async function compareRsExperienceDataDirectories(currentDirectory, pmeDirectory) {
  if (!currentDirectory || !pmeDirectory) throw new Error('Informe as duas raízes data de releases RS já construídas.')
  const requested = [path.resolve(currentDirectory), path.resolve(pmeDirectory)]
  for (const directory of requested) {
    const stat = await lstat(directory)
    if (!stat.isDirectory() || stat.isSymbolicLink()) throw new Error('Cada raiz deve ser um diretório real de release.')
  }
  const [currentRoot, pmeRoot] = await Promise.all(requested.map((directory) => realpath(directory)))
  if (currentRoot === pmeRoot) throw new Error('Compare duas saídas distintas; a mesma raiz não comprova paridade entre experiências.')
  const [current, pme] = await Promise.all([inventory(currentRoot), inventory(pmeRoot)])
  const currentMap = new Map(current.map((entry) => [entry.path, entry]))
  const pmeMap = new Map(pme.map((entry) => [entry.path, entry]))
  const differences = [...new Set([...currentMap.keys(), ...pmeMap.keys()])].sort().filter((name) => currentMap.get(name)?.sha256 !== pmeMap.get(name)?.sha256)
  if (differences.length) throw new Error(`Dados RS divergentes em ${differences.length} arquivo(s): ${differences.slice(0, 10).join(', ')}`)
  const aggregate = createHash('sha256')
  for (const entry of [...current].sort((a, b) => a.path < b.path ? -1 : a.path > b.path ? 1 : 0)) {
    aggregate.update(`${entry.path}\0${entry.size}\0${entry.sha256}\n`)
  }
  return { fileCount: current.length, totalBytes: current.reduce((sum, entry) => sum + entry.size, 0), sha256: aggregate.digest('hex') }
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    if (process.argv.length !== 4) throw new Error('Uso: node scripts/checks/rs-experience-data-parity.mjs dist/rs/data dist/rs-pme/data')
    const result = await compareRsExperienceDataDirectories(process.argv[2], process.argv[3])
    console.log(`Paridade RS confirmada: ${result.fileCount} arquivos, ${result.totalBytes} bytes; SHA-256 agregado ${result.sha256}`)
  } catch (error) {
    console.error(error instanceof Error ? error.message : String(error))
    process.exitCode = 1
  }
}
