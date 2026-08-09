import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import path from 'node:path'
import test from 'node:test'
import { pathToFileURL } from 'node:url'

const repoRoot = path.resolve(import.meta.dirname, '..', '..')
const temporaryOutput = mkdtempSync(path.join(tmpdir(), 'dashboard-pne-municipality-identity-'))
writeFileSync(path.join(temporaryOutput, 'package.json'), '{"type":"module"}\n')
execFileSync(
  process.execPath,
  [
    path.resolve(repoRoot, 'node_modules/typescript/bin/tsc'),
    '--project',
    path.resolve(repoRoot, 'scripts/checks/tsconfig.municipality-identity.json'),
    '--outDir',
    temporaryOutput,
  ],
  { cwd: repoRoot, stdio: 'inherit' },
)

process.on('exit', () => rmSync(temporaryOutput, { force: true, recursive: true }))

const compiledModule = (relativePath) => (
  pathToFileURL(path.join(temporaryOutput, relativePath)).href
)

const rawStateConfig = JSON.parse(
  readFileSync(path.join(repoRoot, 'config/states/rs.json'), 'utf8'),
)
globalThis.__ACTIVE_STATE_CONFIG__ = rawStateConfig

const stateConfigModule = await import(compiledModule('src/config/stateConfig.js'))
const registryModule = await import(compiledModule('src/domain/municipalityRegistry.js'))
const routingModule = await import(compiledModule('src/domain/municipalityRouting.js'))
const selectorModelModule = await import(compiledModule('src/domain/municipalitySelectorModel.js'))
const storageModule = await import(compiledModule('src/domain/municipalityStorage.js'))
const payloadIdentityModule = await import(compiledModule('src/domain/municipalityDataIdentity.js'))
const staticDataModule = await import(compiledModule('src/data/staticData.js'))

const rawMunicipalityIndex = JSON.parse(
  readFileSync(path.join(repoRoot, 'public/data/municipios_index.json'), 'utf8'),
)
const activeState = stateConfigModule.ACTIVE_STATE_CONFIG
const municipalities = registryModule.buildMunicipalityRegistry(rawMunicipalityIndex, activeState)
const agudo = municipalities.find((municipality) => municipality.ibgeCode === '4300109')
const alegria = municipalities.find((municipality) => municipality.name === 'Alegria')

function clone(value) {
  return structuredClone(value)
}

function createMemoryStorage(initial = {}) {
  const values = new Map(Object.entries(initial))
  return {
    getItem: (key) => values.get(key) ?? null,
    removeItem: (key) => values.delete(key),
    setItem: (key, value) => values.set(key, value),
    snapshot: () => Object.fromEntries(values),
  }
}

test('valida e congela a configuração estadual canônica do RS', () => {
  assert.equal(activeState.schemaVersion, 'state-config-v1')
  assert.equal(activeState.stateCode, 'RS')
  assert.equal(activeState.stateName, 'Rio Grande do Sul')
  assert.deepEqual(activeState.stateNameForms, {
    nominative: 'o Rio Grande do Sul',
    withDe: 'do Rio Grande do Sul',
    withCom: 'com o Rio Grande do Sul',
  })
  assert.equal(Object.isFrozen(activeState.stateNameForms), true)
  assert.equal(activeState.municipalityIbgePrefix, '43')
  assert.equal(activeState.expectedMunicipalityCount, 497)
  assert.equal(activeState.locale, 'pt-BR')
  assert.equal(Object.isFrozen(activeState), true)
})

test('rejeita configurações estaduais inválidas sem fallback silencioso', () => {
  assert.throws(
    () => stateConfigModule.parseStateConfig({ ...rawStateConfig, schemaVersion: 'state-config-v2' }),
    /schemaVersion desconhecido/,
  )
  assert.throws(
    () => stateConfigModule.parseStateConfig({ ...rawStateConfig, stateCode: 'rs' }),
    /duas letras maiúsculas/,
  )
  assert.throws(
    () => stateConfigModule.parseStateConfig({ ...rawStateConfig, expectedMunicipalityCount: 0 }),
    /inteiro positivo/,
  )
  assert.throws(
    () => stateConfigModule.parseStateConfig({ ...rawStateConfig, locale: 'locale inválido' }),
    /locale/,
  )
  assert.throws(
    () => stateConfigModule.parseStateConfig({ ...rawStateConfig, stateNameForms: null }),
    /stateNameForms/,
  )
  assert.throws(
    () => stateConfigModule.parseStateConfig({
      ...rawStateConfig,
      stateNameForms: { ...rawStateConfig.stateNameForms, extra: 'blocked' },
    }),
    /campos de stateNameForms divergentes/,
  )
})

test('normaliza 497 municípios preservando ordem, nomes e códigos como texto', () => {
  assert.equal(municipalities.length, activeState.expectedMunicipalityCount)
  assert.equal(new Set(municipalities.map(({ ibgeCode }) => ibgeCode)).size, 497)
  assert.equal(new Set(municipalities.map(({ slug }) => slug)).size, 497)
  assert.ok(municipalities.every(({ ibgeCode }) => /^43\d{5}$/.test(ibgeCode)))
  assert.ok(municipalities.every(({ stateCode }) => stateCode === 'RS'))
  assert.deepEqual(
    municipalities.map(({ name }) => name),
    rawMunicipalityIndex.municipios.map(({ nome }) => nome),
  )
  assert.deepEqual(
    municipalities.map(({ ibgeCode }) => ibgeCode),
    rawMunicipalityIndex.municipios.map(({ id_municipio }) => id_municipio),
  )
})

test('rejeita duplicidade, prefixo de outro estado, total divergente e path trocado', () => {
  const duplicate = clone(rawMunicipalityIndex)
  duplicate.municipios[1].id_municipio = duplicate.municipios[0].id_municipio
  assert.throws(
    () => registryModule.buildMunicipalityRegistry(duplicate, activeState),
    /id_municipio.*repete/,
  )

  const anotherState = clone(rawMunicipalityIndex)
  anotherState.municipios[0].id_municipio = '4200035'
  anotherState.municipios[0].path = '/data/municipios/4200035/index.json'
  assert.throws(
    () => registryModule.buildMunicipalityRegistry(anotherState, activeState),
    /prefixo 43/,
  )

  const divergentTotal = clone(rawMunicipalityIndex)
  divergentTotal.total_municipios = 496
  assert.throws(
    () => registryModule.buildMunicipalityRegistry(divergentTotal, activeState),
    /total_municipios.*496.*497/,
  )

  const mismatchedPath = clone(rawMunicipalityIndex)
  mismatchedPath.municipios[0].path = '/data/municipios/4300109/index.json'
  assert.throws(
    () => registryModule.buildMunicipalityRegistry(mismatchedPath, activeState),
    /path.*4300034/,
  )
})

test('indexa por código e resolve nome somente quando a correspondência é única', () => {
  const byId = registryModule.indexMunicipalitiesById(municipalities)
  assert.equal(registryModule.findMunicipalityById(byId, agudo.ibgeCode), agudo)
  assert.equal(registryModule.findUniqueMunicipalityByName(municipalities, 'ÁGUDO'), agudo)

  const ambiguous = [
    { ...agudo, name: 'Nome repetido' },
    { ...alegria, name: 'Nôme Repetido' },
  ]
  assert.equal(registryModule.findUniqueMunicipalityByName(ambiguous, 'nome repetido'), null)
})

test('restaura contexto v2 válido e dá precedência a ele sobre a chave antiga', () => {
  const storage = createMemoryStorage({
    [storageModule.MUNICIPALITY_STORAGE_KEY]: storageModule.serializeDashboardContextV2(
      activeState.stateCode,
      agudo.ibgeCode,
    ),
    [storageModule.LEGACY_MUNICIPALITY_STORAGE_KEY]: alegria.name,
  })
  assert.deepEqual(
    storageModule.restoreMunicipalitySelection(storage, municipalities, activeState),
    { municipalityId: agudo.ibgeCode, source: 'v2' },
  )
  assert.equal(storage.getItem(storageModule.LEGACY_MUNICIPALITY_STORAGE_KEY), null)
})

test('ignora JSON inválido, estado incompatível e código inexistente com segurança', () => {
  for (const invalidValue of [
    '{json',
    JSON.stringify({
      schemaVersion: storageModule.DASHBOARD_CONTEXT_SCHEMA_VERSION,
      stateCode: 'SC',
      municipalityId: agudo.ibgeCode,
    }),
    storageModule.serializeDashboardContextV2(activeState.stateCode, '4399999'),
  ]) {
    const storage = createMemoryStorage({
      [storageModule.MUNICIPALITY_STORAGE_KEY]: invalidValue,
    })
    assert.deepEqual(
      storageModule.restoreMunicipalitySelection(storage, municipalities, activeState),
      { municipalityId: null, source: 'none' },
    )
    assert.equal(storage.getItem(storageModule.MUNICIPALITY_STORAGE_KEY), null)
  }
})

test('migra uma vez o nome legado para código e remove a chave antiga', () => {
  const storage = createMemoryStorage({
    [storageModule.LEGACY_MUNICIPALITY_STORAGE_KEY]: 'Águdo',
  })
  assert.deepEqual(
    storageModule.restoreMunicipalitySelection(storage, municipalities, activeState),
    { municipalityId: agudo.ibgeCode, source: 'legacy' },
  )
  assert.equal(storage.getItem(storageModule.LEGACY_MUNICIPALITY_STORAGE_KEY), null)
  assert.deepEqual(
    storageModule.parseDashboardContextV2(storage.getItem(storageModule.MUNICIPALITY_STORAGE_KEY)),
    {
      schemaVersion: storageModule.DASHBOARD_CONTEXT_SCHEMA_VERSION,
      stateCode: activeState.stateCode,
      municipalityId: agudo.ibgeCode,
    },
  )
})

test('não migra nome ambíguo e tolera armazenamento indisponível', () => {
  const ambiguousMunicipalities = [
    { ...agudo, name: 'Nome repetido' },
    { ...alegria, name: 'Nôme Repetido' },
  ]
  const storage = createMemoryStorage({
    [storageModule.LEGACY_MUNICIPALITY_STORAGE_KEY]: 'nome repetido',
  })
  assert.deepEqual(
    storageModule.restoreMunicipalitySelection(storage, ambiguousMunicipalities, activeState),
    { municipalityId: null, source: 'none' },
  )
  assert.deepEqual(
    storageModule.restoreMunicipalitySelection(null, municipalities, activeState),
    { municipalityId: null, source: 'none' },
  )
})

test('limpar seleção remove a persistência versionada', () => {
  const storage = createMemoryStorage()
  assert.equal(
    storageModule.persistMunicipalitySelection(
      storage,
      municipalities,
      activeState,
      agudo.ibgeCode,
    ),
    true,
  )
  assert.ok(storage.getItem(storageModule.MUNICIPALITY_STORAGE_KEY))
  assert.equal(
    storageModule.persistMunicipalitySelection(storage, municipalities, activeState, null),
    true,
  )
  assert.deepEqual(storage.snapshot(), {})
})

test('modelo do seletor pesquisa sem acentos e ordena nome com desempate por código', () => {
  const tiedNames = [
    { ...agudo, ibgeCode: '4300002', name: 'Mesmo nome' },
    { ...alegria, ibgeCode: '4300001', name: 'Mesmo nome' },
  ]
  assert.deepEqual(
    selectorModelModule.sortMunicipalitiesByName(tiedNames, activeState.locale)
      .map(({ ibgeCode }) => ibgeCode),
    ['4300001', '4300002'],
  )
  assert.deepEqual(
    selectorModelModule.filterMunicipalitiesByName(municipalities, 'sao leopoldo', activeState.locale)
      .map(({ name }) => name),
    ['São Leopoldo'],
  )
})

test('seletor exibe nome, retorna código, limpa com null e usa código em key e ARIA', () => {
  const source = readFileSync(
    path.join(repoRoot, 'src/components/MunicipalitySelector.tsx'),
    'utf8',
  )
  assert.match(source, /selectedMunicipality\?\.name/)
  assert.match(source, /onChange\(municipality\.ibgeCode\)/)
  assert.match(source, /onChange\(null\)/)
  assert.match(source, /key=\{municipality\.ibgeCode\}/)
  assert.match(source, /aria-selected=\{municipality\.ibgeCode === selectedMunicipalityId\}/)
  assert.match(source, /municipio-option-\$\{instanceId\}-\$\{municipality\.ibgeCode\}/)
})

test('roteamento resolve slug, código e nome e só normaliza valores não canônicos', () => {
  const bySlug = routingModule.resolveMunicipalityRouteRequest(municipalities, agudo.slug)
  const byCode = routingModule.resolveMunicipalityRouteRequest(municipalities, agudo.ibgeCode)
  const byName = routingModule.resolveMunicipalityRouteRequest(municipalities, agudo.name)
  assert.equal(bySlug.municipality, agudo)
  assert.equal(bySlug.shouldNormalize, false)
  assert.equal(byCode.municipality, agudo)
  assert.equal(byCode.shouldNormalize, true)
  assert.equal(byName.municipality, agudo)
  assert.equal(byName.shouldNormalize, true)
  assert.equal(
    routingModule.getEffectiveMunicipality(agudo.slug, agudo, alegria),
    agudo,
  )
  assert.equal(
    routingModule.getEffectiveMunicipality('', null, alegria),
    alegria,
  )
})

test('nome de rota ambíguo falha fechado em vez de escolher o primeiro', () => {
  const ambiguousMunicipalities = [
    { ...agudo, name: 'Nome repetido' },
    { ...alegria, name: 'Nôme Repetido' },
  ]
  const resolution = routingModule.resolveMunicipalityRouteRequest(
    ambiguousMunicipalities,
    'nome repetido',
  )
  assert.equal(resolution.municipality, null)
  assert.equal(
    routingModule.getEffectiveMunicipality('nome repetido', null, agudo),
    null,
  )
})

test('payload municipal divergente falha fechado', () => {
  assert.doesNotThrow(() => (
    payloadIdentityModule.assertMunicipalityPayloadMatchesRequest(
      { id_municipio: agudo.ibgeCode },
      agudo.ibgeCode,
    )
  ))
  assert.throws(
    () => payloadIdentityModule.assertMunicipalityPayloadMatchesRequest(
      { id_municipio: alegria.ibgeCode },
      agudo.ibgeCode,
    ),
    /Identidade municipal divergente/,
  )
})

test('loader rejeita resposta cujo ID declarado diverge do código solicitado', async () => {
  const originalFetch = globalThis.fetch
  globalThis.fetch = async () => ({
    ok: true,
    json: async () => ({ id_municipio: agudo.ibgeCode }),
    status: 200,
  })

  try {
    await assert.rejects(
      staticDataModule.loadMunicipioData(alegria.ibgeCode),
      /Identidade municipal divergente/,
    )
  } finally {
    globalThis.fetch = originalFetch
  }
})

test('loader usa somente o código no caminho e preserva cache e deduplicação', async () => {
  const originalFetch = globalThis.fetch
  const requests = []
  globalThis.fetch = async (requestPath) => {
    requests.push(String(requestPath))
    const requestedId = String(requestPath).match(/municipios\/(\d{7})\/index\.json/)?.[1]
    return {
      ok: true,
      json: async () => ({ id_municipio: requestedId }),
      status: 200,
    }
  }

  try {
    const [first, second] = await Promise.all([
      staticDataModule.loadMunicipioData(agudo.ibgeCode),
      staticDataModule.loadMunicipioData(agudo.ibgeCode),
    ])
    assert.equal(first.id_municipio, agudo.ibgeCode)
    assert.equal(second.id_municipio, agudo.ibgeCode)
    assert.deepEqual(requests, [`/data/municipios/${agudo.ibgeCode}/index.json`])
    await staticDataModule.loadMunicipioData(agudo.ibgeCode)
    assert.equal(requests.length, 1)
  } finally {
    globalThis.fetch = originalFetch
  }
})

test('integrações usam código para hook, Educação, relatório e panorama financeiro', () => {
  const hookSource = readFileSync(path.join(repoRoot, 'src/hooks/useMunicipioData.ts'), 'utf8')
  const routerSource = readFileSync(path.join(repoRoot, 'src/app/AppPageRouter.tsx'), 'utf8')
  assert.doesNotMatch(hookSource, /\.nome|selectedMunicipio/)
  assert.match(hookSource, /loadMunicipioData\(selectedMunicipalityId\)/)
  assert.match(hookSource, /primeMunicipioCache\(selectedMunicipalityId, data\)/)
  assert.match(routerSource, /municipalityIdentifier=\{effectiveMunicipalityId\}/)
  assert.match(routerSource, /municipalityId=\{effectiveMunicipalityId\}/)
  assert.match(routerSource, /municipalitySlug=\{effectiveMunicipality\.slug\}/)
  assert.match(routerSource, /isEducationDataPage/)
})
