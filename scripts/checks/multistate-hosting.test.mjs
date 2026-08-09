import assert from 'node:assert/strict'
import {
  existsSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  readdirSync,
  rmSync,
} from 'node:fs'
import path from 'node:path'
import test from 'node:test'
import { fileURLToPath } from 'node:url'
import { ANALYTICS_PRODUCTS, loadStateBuildProfile } from '../lib/state-build-profile.mjs'
import { copyStatePublicAssets } from '../lib/state-public-assets.mjs'
import { parseStateViteArguments } from '../run-state-vite.mjs'

const repoRoot = fileURLToPath(new URL('../..', import.meta.url))

function allFiles(root) {
  const files = []
  const visit = (directory) => {
    for (const entry of readdirSync(directory, { withFileTypes: true })) {
      const absolute = path.join(directory, entry.name)
      if (entry.isDirectory()) visit(absolute)
      else if (entry.isFile()) files.push(path.relative(root, absolute).replaceAll('\\', '/'))
    }
  }
  visit(root)
  return files.toSorted()
}

function readJson(filePath) {
  return JSON.parse(readFileSync(filePath, 'utf8'))
}

test('RS e AL resolvem produtos e raízes de dados independentes', () => {
  const rs = loadStateBuildProfile({ repoRoot, stateCode: 'RS' })
  const al = loadStateBuildProfile({ repoRoot, stateCode: 'AL' })

  assert.equal(rs.publication.schemaVersion, 'state-publication-v3')
  assert.equal(al.publication.schemaVersion, 'state-publication-v3')
  assert.equal(rs.publication.enabledProducts, null)
  assert.equal(al.publication.enabledProducts, null)
  assert.equal(rs.publication.analyticsStatus, 'complete')
  assert.equal(rs.municipalityRegistry.municipalityCount, 497)
  assert.equal(al.publication.analyticsStatus, 'complete')
  assert.equal(al.municipalityRegistry.municipalityCount, 102)
  assert.notEqual(rs.publicDataDirectory, al.publicDataDirectory)
  assert.ok(rs.municipalityRegistry.municipalities.every(({ ibgeCode }) => ibgeCode.startsWith('43')))
  assert.ok(al.municipalityRegistry.municipalities.every(({ ibgeCode }) => ibgeCode.startsWith('27')))
})

test('AL publica PNE, Educação e Financiamento como estado completo', () => {
  const manifest = JSON.parse(
    readFileSync(path.join(repoRoot, 'config/publications/al.json'), 'utf8'),
  )
  assert.equal(manifest.schemaVersion, 'state-publication-v3')
  assert.equal(manifest.analyticsStatus, 'complete')
  assert.equal(manifest.enabledProducts, null)
  assert.equal(manifest.analyticsMessage, null)
  assert.equal(manifest.stateConfigPath, 'config/states/al.json')
  assert.equal(manifest.municipalityRegistryPath, 'config/municipalities/al.json')
})

test('o vocabulário de produtos é idêntico nas três camadas do contrato', () => {
  const frontend = readFileSync(
    path.join(repoRoot, 'src/config/analyticsProducts.ts'),
    'utf8',
  )
  const pipeline = readFileSync(
    path.join(repoRoot, 'data_pipeline/src/state_publication.py'),
    'utf8',
  )
  const frontendProducts = /export const ANALYTICS_PRODUCTS = \[([^\]]+)\]/
    .exec(frontend)?.[1]
  const pipelineProducts = /ANALYTICS_PRODUCTS = \(([^)]+)\)/.exec(pipeline)?.[1]
  assert.ok(frontendProducts, 'vocabulário do frontend não encontrado')
  assert.ok(pipelineProducts, 'vocabulário do pipeline não encontrado')

  const parse = (source) => [...source.matchAll(/'([a-z]+)'|"([a-z]+)"/g)]
    .map((match) => match[1] ?? match[2])
  assert.deepEqual(parse(frontendProducts), [...ANALYTICS_PRODUCTS])
  assert.deepEqual(parse(pipelineProducts), [...ANALYTICS_PRODUCTS])
})

test('raiz AL contém os três produtos nos subtrees canônicos', () => {
  const al = loadStateBuildProfile({ repoRoot, stateCode: 'AL' })
  const observed = allFiles(al.publicDataDirectory)
  const identityFiles = [
    'municipios_index.json',
    ...al.municipalityRegistry.municipalities.map(
      ({ ibgeCode }) => `municipios/${ibgeCode}/index.json`,
    ),
  ]
  assert.ok(identityFiles.every((relative) => observed.includes(relative)))
  assert.ok(observed.includes('educacao/index.json'))
  assert.ok(observed.includes('educacao/municipios_index.json'))
  assert.equal(observed.filter((relative) => /^educacao\/municipios\/27\d{5}\.json$/.test(relative)).length, 102)
  assert.equal(observed.filter((relative) => /^educacao\/visao-geral-municipal\/27\d{5}\.json$/.test(relative)).length, 102)
  assert.ok(observed.some((relative) => relative.startsWith('educacao/educacao-especial/')))
  assert.ok(observed.some((relative) => relative.startsWith('educacao/superior/')))
  assert.ok(observed.includes('financeiro/manifest.json'))
  assert.ok(observed.includes('financeiro/catalogos.json'))
  assert.ok(observed.includes('financeiro/cobertura.json'))
  assert.ok(observed.includes('financeiro/qse-anual-manifest.json'))
  assert.equal(observed.filter((relative) => /^municipios\/27\d{5}\/financeiro\.json$/.test(relative)).length, 102)
  assert.equal(observed.filter((relative) => /^municipios\/27\d{5}\/qse-anual\.json$/.test(relative)).length, 102)
  assert.equal(observed.filter((relative) => /^municipios\/27\d{5}\/details\.json$/.test(relative)).length, 102)
  assert.ok(observed.includes('indicadores.json'))
  assert.ok(observed.includes('pne_2014_2024/referencia_estadual.json'))
  assert.ok(observed.includes('pne_2026_2036/referencia_estadual.json'))
  assert.ok(observed.includes('pne2026-diagnostic-v3/current.json'))
  assert.equal(observed.includes('publication.json'), false)
  assert.ok(observed.every((relative) => !relative.includes('4300034')))

  for (const { ibgeCode, name, slug } of al.municipalityRegistry.municipalities) {
    const payload = JSON.parse(readFileSync(
      path.join(al.publicDataDirectory, 'municipios', ibgeCode, 'index.json'),
      'utf8',
    ))
    assert.equal(payload.id_municipio, ibgeCode)
    assert.equal(typeof payload.id_municipio, 'string')
    assert.equal(payload.municipio, name)
    assert.equal(payload.slug, slug)
    assert.equal(payload.analytics, undefined)
    assert.equal(typeof payload.pne_2014_2024, 'object')
    assert.equal(typeof payload.pne_2026_2036, 'object')
  }
})

test('diagnóstico PNE de AL publica as mesmas relações de RS sem falsos vazios', () => {
  const contract = readJson(
    path.join(repoRoot, 'contracts', 'pne2026-goal-indicator-contract.json'),
  )
  const eligibleRelations = contract.relations.filter(
    (relation) => relation.mode !== 'hidden' && relation.includeInDiagnostic === true,
  )
  const expectedRelationIds = eligibleRelations
    .map(({ relationId }) => relationId)
    .toSorted()
  const relationById = new Map(
    eligibleRelations.map((relation) => [relation.relationId, relation]),
  )

  const activeReleaseRoot = (dataRoot) => {
    const current = readJson(path.join(dataRoot, 'pne2026-diagnostic-v3', 'current.json'))
    return path.join(dataRoot, 'pne2026-diagnostic-v3', 'releases', current.releaseId)
  }
  const rs = loadStateBuildProfile({ repoRoot, stateCode: 'RS' })
  const al = loadStateBuildProfile({ repoRoot, stateCode: 'AL' })
  const rsReleaseRoot = activeReleaseRoot(rs.publicDataDirectory)
  const alReleaseRoot = activeReleaseRoot(al.publicDataDirectory)
  const rsReference = readJson(
    path.join(rsReleaseRoot, 'municipios', '4300034.json'),
  )
  assert.deepEqual(
    rsReference.results.map(({ relationId }) => relationId).toSorted(),
    expectedRelationIds,
  )

  const falseEmptyResults = []
  for (const { ibgeCode } of al.municipalityRegistry.municipalities) {
    const diagnostic = readJson(
      path.join(alReleaseRoot, 'municipios', `${ibgeCode}.json`),
    )
    assert.deepEqual(
      diagnostic.results.map(({ relationId }) => relationId).toSorted(),
      expectedRelationIds,
      `${ibgeCode}: conjunto de relações divergente`,
    )
    const cycle = readJson(
      path.join(al.publicDataDirectory, 'municipios', ibgeCode, 'index.json'),
    ).pne_2026_2036.indicadores
    for (const result of diagnostic.results) {
      const relation = relationById.get(result.relationId)
      const source = cycle[relation.indicatorId]
      if (
        result.dataStatus === 'unavailable'
        && result.reasonCode === 'no_observation'
        && source?.available === true
        && Number.isInteger(source.end_year)
        && Number.isFinite(source.end_value)
      ) {
        falseEmptyResults.push(`${ibgeCode}:${result.relationId}`)
      }
    }
  }
  assert.equal(
    falseEmptyResults.length,
    0,
    `resultados municipais disponíveis foram publicados como vazios: ${falseEmptyResults.slice(0, 10).join(', ')}`,
  )
})

test('empacotamento AL não copia nenhum arquivo da publicação RS', async () => {
  const al = loadStateBuildProfile({ repoRoot, stateCode: 'AL' })
  const testRoot = path.join(repoRoot, 'tmp', 'multistate-hosting')
  mkdirSync(testRoot, { recursive: true })
  const output = mkdtempSync(path.join(testRoot, 'al-'))
  try {
    await copyStatePublicAssets({
      repoRoot,
      sharedPublicDirectory: al.sharedPublicDirectory,
      publicDataDirectory: al.publicDataDirectory,
      outDir: output,
    })
    const copiedData = allFiles(path.join(output, 'data'))
    assert.deepEqual(copiedData, allFiles(al.publicDataDirectory))
    assert.equal(existsSync(path.join(output, 'data', 'indicadores.json')), true)
    assert.equal(existsSync(path.join(output, 'data', 'municipios', '4300034')), false)
  } finally {
    rmSync(output, { recursive: true, force: true })
  }
})

test('comandos explícitos de hospedagem fixam a UF sem depender do shell', () => {
  const packageJson = JSON.parse(readFileSync(path.join(repoRoot, 'package.json'), 'utf8'))
  assert.equal(
    packageJson.scripts['build:cloudflare:rs'],
    'node scripts/run-state-vite.mjs build RS --outDir dist',
  )
  assert.equal(
    packageJson.scripts['build:cloudflare:al'],
    'node scripts/run-state-vite.mjs build AL --outDir dist',
  )
  assert.deepEqual(
    parseStateViteArguments(['build', 'al', '--outDir', 'dist']),
    { command: 'build', stateCode: 'AL', viteArguments: ['--outDir', 'dist'] },
  )
  assert.throws(() => parseStateViteArguments(['build', 'RS;AL']), /UF inválida/)
})
