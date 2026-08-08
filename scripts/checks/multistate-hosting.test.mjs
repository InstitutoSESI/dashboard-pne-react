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
import { loadStateBuildProfile } from '../lib/state-build-profile.mjs'
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

test('RS e AL resolvem produtos e raízes de dados independentes', () => {
  const rs = loadStateBuildProfile({ repoRoot, stateCode: 'RS' })
  const al = loadStateBuildProfile({ repoRoot, stateCode: 'AL' })

  assert.equal(rs.publication.analyticsStatus, 'complete')
  assert.equal(rs.municipalityRegistry.municipalityCount, 497)
  assert.equal(al.publication.analyticsStatus, 'identity-only')
  assert.equal(al.municipalityRegistry.municipalityCount, 102)
  assert.notEqual(rs.publicDataDirectory, al.publicDataDirectory)
  assert.ok(rs.municipalityRegistry.municipalities.every(({ ibgeCode }) => ibgeCode.startsWith('43')))
  assert.ok(al.municipalityRegistry.municipalities.every(({ ibgeCode }) => ibgeCode.startsWith('27')))
})

test('raiz AL contém apenas o contrato de identidade indisponível', () => {
  const al = loadStateBuildProfile({ repoRoot, stateCode: 'AL' })
  const observed = allFiles(al.publicDataDirectory)
  const expected = [
    'municipios_index.json',
    'publication.json',
    ...al.municipalityRegistry.municipalities.map(
      ({ ibgeCode }) => `municipios/${ibgeCode}/index.json`,
    ),
  ].toSorted()
  assert.deepEqual(observed, expected)
  assert.ok(observed.every((relative) => !relative.includes('educacao')))
  assert.ok(observed.every((relative) => !relative.includes('financeiro')))
  assert.ok(observed.every((relative) => !relative.includes('pne')))

  for (const { ibgeCode, name, slug } of al.municipalityRegistry.municipalities) {
    const payload = JSON.parse(readFileSync(
      path.join(al.publicDataDirectory, 'municipios', ibgeCode, 'index.json'),
      'utf8',
    ))
    assert.equal(payload.id_municipio, ibgeCode)
    assert.equal(typeof payload.id_municipio, 'string')
    assert.equal(payload.municipio, name)
    assert.equal(payload.slug, slug)
    assert.deepEqual(
      { status: payload.analytics.status, reason: payload.analytics.reason },
      { status: 'unavailable', reason: 'analytics_not_published' },
    )
  }
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
    assert.equal(existsSync(path.join(output, 'data', 'indicadores.json')), false)
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
