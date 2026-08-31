import assert from 'node:assert/strict'
import { createHash, webcrypto } from 'node:crypto'
import { readFile } from 'node:fs/promises'
import path from 'node:path'
import { after, test } from 'node:test'
import { createServer } from 'vite'

const repoRoot = path.resolve(import.meta.dirname, '..', '..')
const bundleRaw = await readFile(
  path.join(repoRoot, 'src/features/cenarios-educacao/generated/cenariosEducacaoValeDoSinos.json'),
  'utf8',
)
const registry = JSON.parse(await readFile(
  path.join(repoRoot, 'src/features/cenarios-educacao/generated/cenariosEducacaoRegistry.json'),
  'utf8',
))
const bundle = JSON.parse(bundleRaw)

if (globalThis.crypto === undefined) {
  Object.defineProperty(globalThis, 'crypto', { value: webcrypto })
}

const vite = await createServer({
  appType: 'custom',
  logLevel: 'silent',
  optimizeDeps: { include: [], noDiscovery: true },
  publicDir: false,
  server: { hmr: false, middlewareMode: true, watch: null },
})
const loaderModule = await vite.ssrLoadModule('/src/features/cenarios-educacao/useCenariosEducacaoBundle.ts')
const contractModule = await vite.ssrLoadModule('/src/features/cenarios-educacao/cenariosEducacaoContract.ts')

after(async () => {
  await vite.close()
})

function serialized(value) {
  return JSON.stringify(value, null, 2) + '\n'
}

function registryFor(candidateRaw) {
  return {
    ...registry,
    bundleSha256: createHash('sha256').update(candidateRaw, 'utf8').digest('hex'),
    bundleByteSize: Buffer.byteLength(candidateRaw, 'utf8'),
  }
}

test('loader valida bytes, contrato, fontes e reutiliza a instância validada', async () => {
  let calls = 0
  const load = loaderModule.createCenariosEducacaoLoader(async () => {
    calls += 1
    return { bundleRaw, registry }
  })
  const [first, second] = await Promise.all([load(), load()])
  assert.equal(first, second)
  assert.equal(calls, 1)
  assert.equal(first.schemaVersion, 'vocacoes-pne-foresight-v2')
  assert.equal(first.qualityGate.status, 'passed')
  assert.equal(first.diagnosticBridge.deDuplicationAudit.duplicateCount, 0)
})

test('loader rejeita corrupção de bytes antes de interpretar o conteúdo', async () => {
  const corrupted = bundleRaw.replace('Cenários da Educação', 'Cenários da Educaçã0')
  const load = loaderModule.createCenariosEducacaoLoader(async () => ({
    bundleRaw: corrupted,
    registry,
  }))
  await assert.rejects(load, /hash do bundle diverge/u)
})

const mutations = [
  ['cenário ausente', (candidate) => { candidate.scenarios.pop() }, /quatro cenários/u],
  ['maturidade transversal adulterada', (candidate) => {
    candidate.crossCuttingDrivers[0].maturity = 'EXPLICIT_GAP'
  }, /maturidade do transversal/u],
  ['cobertura transversal incompleta', (candidate) => {
    candidate.crossCuttingDrivers[1].coverage.municipalityCount = 9
  }, /cobertura 10\/10/u],
  ['duplicação diagnóstica declarada', (candidate) => {
    candidate.diagnosticBridge.deDuplicationAudit.duplicateCount = 1
  }, /zero duplicações/u],
  ['lente municipal adulterada', (candidate) => {
    candidate.municipalities[0].municipalityIbgeCode = '4303905'
  }, /lente exclusiva/u],
  ['distância morfológica adulterada', (candidate) => {
    candidate.morphologicalField.minimumObservedPairwiseHammingDistance = 2
  }, /distância morfológica/u],
  ['gate de rede adulterado', (candidate) => {
    candidate.qualityGate.networkDownloadUsed = true
  }, /sem rede nem banco/u],
]

for (const [label, mutate, expected] of mutations) {
  test('loader falha fechado com ' + label, async () => {
    const candidate = structuredClone(bundle)
    mutate(candidate)
    const candidateRaw = serialized(candidate)
    const load = loaderModule.createCenariosEducacaoLoader(async () => ({
      bundleRaw: candidateRaw,
      registry: registryFor(candidateRaw),
    }))
    await assert.rejects(load, expected)
  })
}

test('loader confere os hashes das fontes contra o registro', async () => {
  const load = loaderModule.createCenariosEducacaoLoader(async () => ({
    bundleRaw,
    registry: { ...registry, regionalPublicInputsSha256: '0'.repeat(64) },
  }))
  await assert.rejects(load, /hash de entradas públicas regionais diverge/u)
})

test('assertor de registro rejeita status e contagens adulterados', () => {
  assert.doesNotThrow(() => contractModule.assertCenariosEducacaoRegistry(registry))
  assert.throws(
    () => contractModule.assertCenariosEducacaoRegistry({ ...registry, publicDataValidationStatus: 'pending' }),
    /status do gate público/u,
  )
  assert.throws(
    () => contractModule.assertCenariosEducacaoRegistry({ ...registry, regionalMunicipalityCount: 9 }),
    /região do registro/u,
  )
  assert.throws(
    () => contractModule.assertCenariosEducacaoRegistry({ ...registry, bundleByteSize: 0 }),
    /integridade do bundle/u,
  )
})
