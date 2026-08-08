import assert from 'node:assert/strict'
import {
  existsSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from 'node:fs'
import { tmpdir } from 'node:os'
import path from 'node:path'
import test from 'node:test'
import { fileURLToPath } from 'node:url'
import {
  loadStateBuildProfile,
  normalizePlatformState,
} from '../lib/state-build-profile.mjs'
import {
  copyStatePublicAssets,
  resolveStateDataRequestPath,
} from '../lib/state-public-assets.mjs'

const repoRoot = fileURLToPath(new URL('../..', import.meta.url))

function writeJson(filePath, payload) {
  mkdirSync(path.dirname(filePath), { recursive: true })
  writeFileSync(filePath, `${JSON.stringify(payload, null, 2)}\n`, 'utf8')
}

function createAlFixture(publicationOverrides = {}) {
  const root = mkdtempSync(path.join(tmpdir(), 'dashboard-pne-state-publication-'))
  const municipalities = [
    { ibgeCode: '2700102', name: 'Água Branca', slug: 'agua-branca' },
    { ibgeCode: '2700201', name: 'Anadia', slug: 'anadia' },
  ]
  writeJson(path.join(root, 'config/states/al.json'), {
    schemaVersion: 'state-config-v1',
    stateCode: 'AL',
    stateName: 'Alagoas',
    municipalityIbgePrefix: '27',
    expectedMunicipalityCount: municipalities.length,
    locale: 'pt-BR',
  })
  writeJson(path.join(root, 'config/municipalities/al.json'), {
    schemaVersion: 'municipality-registry-v1',
    stateCode: 'AL',
    municipalityCount: municipalities.length,
    municipalities,
  })
  writeJson(path.join(root, 'config/publications/al.json'), {
    schemaVersion: 'state-publication-v3',
    stateCode: 'AL',
    stateConfigPath: 'config/states/al.json',
    municipalityRegistryPath: 'config/municipalities/al.json',
    publicDataDirectory: 'state-publications/al/data',
    analyticsStatus: 'identity-only',
    analyticsMessage: 'Indicadores ainda não publicados.',
    enabledProducts: null,
    ...publicationOverrides,
  })
  writeJson(path.join(root, 'state-publications/al/data/municipios_index.json'), {
    generated_at: '2026-08-07T00:00:00Z',
    total_municipios: municipalities.length,
    municipios: municipalities.map((municipality) => ({
      nome: municipality.name,
      id_municipio: municipality.ibgeCode,
      slug: municipality.slug,
      path: `/data/municipios/${municipality.ibgeCode}/index.json`,
    })),
  })
  for (const municipality of municipalities) {
    mkdirSync(path.join(root, 'state-publications/al/data/municipios', municipality.ibgeCode), {
      recursive: true,
    })
  }
  mkdirSync(path.join(root, 'public/data'), { recursive: true })
  writeFileSync(path.join(root, 'public/data/rs-only.json'), '{"state":"RS"}\n', 'utf8')
  writeFileSync(path.join(root, 'public/favicon.svg'), '<svg/>\n', 'utf8')
  return { root, municipalities }
}

test('perfil real de RS reconcilia configuração, registro e publicação', () => {
  const profile = loadStateBuildProfile({ repoRoot, stateCode: ' rs ' })
  assert.equal(profile.stateCode, 'RS')
  assert.equal(profile.publication.schemaVersion, 'state-publication-v3')
  assert.equal(profile.publication.enabledProducts, null)
  assert.equal(profile.stateConfig.expectedMunicipalityCount, 497)
  assert.equal(profile.municipalityRegistry.municipalityCount, 497)
  assert.equal(profile.publication.publicDataDirectory, 'public/data')
  assert.equal(profile.publication.analyticsStatus, 'complete')
  assert.equal(profile.publicDataDirectory, path.join(repoRoot, 'public', 'data'))
  assert.doesNotMatch(
    readFileSync(path.join(repoRoot, 'src/config/stateConfig.ts'), 'utf8'),
    /config\/states\/rs\.json/,
  )
})

test('normaliza UF textual e rejeita valor inválido sem fallback', () => {
  assert.equal(normalizePlatformState('al'), 'AL')
  assert.throws(() => normalizePlatformState(''), /PLATFORM_STATE inválido/)
  const alProfile = loadStateBuildProfile({ repoRoot, stateCode: 'AL', requirePublication: false })
  assert.equal(alProfile.stateConfig.stateName, 'Alagoas')
  assert.equal(alProfile.publication.analyticsStatus, 'partial')
  assert.equal(alProfile.municipalityRegistry, null)
  assert.equal(alProfile.publicDataDirectory, null)
})

test('perfil real de AL publica Educação para 102 municípios sem ativar analytics do RS', () => {
  const profile = loadStateBuildProfile({ repoRoot, stateCode: 'AL' })
  assert.equal(profile.stateConfig.expectedMunicipalityCount, 102)
  assert.equal(profile.municipalityRegistry.municipalityCount, 102)
  assert.equal(profile.publication.analyticsStatus, 'partial')
  assert.deepEqual([...profile.publication.enabledProducts], ['educacao'])
  assert.equal(profile.publication.publicDataDirectory, 'state-publications/al/data')
  assert.ok(profile.municipalityRegistry.municipalities.every(({ ibgeCode }) => ibgeCode.startsWith('27')))
})

test('aceita um perfil AL completo e preserva códigos IBGE como texto', () => {
  const fixture = createAlFixture()
  try {
    const profile = loadStateBuildProfile({ repoRoot: fixture.root, stateCode: 'AL' })
    assert.equal(profile.stateConfig.municipalityIbgePrefix, '27')
    assert.deepEqual(
      profile.municipalityRegistry.municipalities.map(({ ibgeCode }) => ibgeCode),
      ['2700102', '2700201'],
    )
    assert.ok(profile.municipalityRegistry.municipalities.every(({ ibgeCode }) => typeof ibgeCode === 'string'))
  } finally {
    rmSync(fixture.root, { recursive: true, force: true })
  }
})

test('publicação partial habilita somente os produtos declarados', () => {
  const fixture = createAlFixture({
    analyticsStatus: 'partial',
    analyticsMessage: 'Somente Educação foi publicada para Alagoas.',
    enabledProducts: ['educacao'],
  })
  try {
    const profile = loadStateBuildProfile({ repoRoot: fixture.root, stateCode: 'AL' })
    assert.equal(profile.publication.analyticsStatus, 'partial')
    assert.deepEqual([...profile.publication.enabledProducts], ['educacao'])
    assert.equal(profile.municipalityRegistry.municipalityCount, 2)
  } finally {
    rmSync(fixture.root, { recursive: true, force: true })
  }
})

test('publicação partial é fail-closed em mensagem e em enabledProducts', () => {
  const cases = [
    [
      { analyticsStatus: 'partial', analyticsMessage: 'x', enabledProducts: null },
      /exige enabledProducts como lista não vazia/,
    ],
    [
      { analyticsStatus: 'partial', analyticsMessage: 'x', enabledProducts: [] },
      /exige enabledProducts como lista não vazia/,
    ],
    [
      { analyticsStatus: 'partial', analyticsMessage: 'x', enabledProducts: ['saude'] },
      /produto analítico desconhecido/,
    ],
    [
      {
        analyticsStatus: 'partial',
        analyticsMessage: 'x',
        enabledProducts: ['educacao', 'educacao'],
      },
      /produto analítico duplicado/,
    ],
    [
      {
        analyticsStatus: 'partial',
        analyticsMessage: 'x',
        enabledProducts: ['pne', 'educacao', 'financiamento'],
      },
      /deve declarar analyticsStatus complete/,
    ],
    [
      { analyticsStatus: 'partial', analyticsMessage: '   ', enabledProducts: ['pne'] },
      /publicação partial exige analyticsMessage não vazio/,
    ],
    [
      { analyticsStatus: 'identity-only', analyticsMessage: 'x', enabledProducts: ['pne'] },
      /publicação identity-only deve declarar enabledProducts null/,
    ],
    [
      { analyticsStatus: 'complete', analyticsMessage: null, enabledProducts: ['pne'] },
      /publicação complete deve declarar enabledProducts null/,
    ],
  ]
  for (const [overrides, expected] of cases) {
    const fixture = createAlFixture(overrides)
    try {
      assert.throws(
        () => loadStateBuildProfile({ repoRoot: fixture.root, stateCode: 'AL' }),
        expected,
      )
    } finally {
      rmSync(fixture.root, { recursive: true, force: true })
    }
  }
})

test('schemaVersion antigo é recusado sem migração silenciosa', () => {
  const fixture = createAlFixture({ schemaVersion: 'state-publication-v2' })
  try {
    assert.throws(
      () => loadStateBuildProfile({ repoRoot: fixture.root, stateCode: 'AL' }),
      /schemaVersion deve ser state-publication-v3/,
    )
  } finally {
    rmSync(fixture.root, { recursive: true, force: true })
  }
})

test('recusa publicação AL contaminada por identidade de outro estado', () => {
  const fixture = createAlFixture()
  try {
    const indexPath = path.join(fixture.root, 'state-publications/al/data/municipios_index.json')
    const index = JSON.parse(readFileSync(indexPath, 'utf8'))
    index.municipios[0].id_municipio = '4300034'
    index.municipios[0].path = '/data/municipios/4300034/index.json'
    writeJson(indexPath, index)
    assert.throws(
      () => loadStateBuildProfile({ repoRoot: fixture.root, stateCode: 'AL' }),
      /diverge do registro canônico de AL/,
    )
  } finally {
    rmSync(fixture.root, { recursive: true, force: true })
  }
})

test('empacota ativos compartilhados e somente os dados da UF selecionada', async () => {
  const fixture = createAlFixture()
  const outDir = path.join(fixture.root, 'dist-test')
  try {
    const profile = loadStateBuildProfile({ repoRoot: fixture.root, stateCode: 'AL' })
    await copyStatePublicAssets({
      repoRoot: fixture.root,
      sharedPublicDirectory: profile.sharedPublicDirectory,
      publicDataDirectory: profile.publicDataDirectory,
      outDir,
    })
    assert.equal(existsSync(path.join(outDir, 'favicon.svg')), true)
    assert.equal(existsSync(path.join(outDir, 'data/municipios_index.json')), true)
    assert.equal(existsSync(path.join(outDir, 'data/rs-only.json')), false)
  } finally {
    rmSync(fixture.root, { recursive: true, force: true })
  }
})

test('servidor estadual intercepta /data e bloqueia travessia de diretório', () => {
  const dataRoot = path.join(repoRoot, 'public', 'data')
  assert.equal(
    resolveStateDataRequestPath(dataRoot, '/data/municipios_index.json'),
    path.join(dataRoot, 'municipios_index.json'),
  )
  assert.equal(resolveStateDataRequestPath(dataRoot, '/brands/SESI.png'), null)
  assert.throws(
    () => resolveStateDataRequestPath(dataRoot, '/data/%2e%2e/config/states/rs.json'),
    /dentro da publicação estadual/,
  )
})
