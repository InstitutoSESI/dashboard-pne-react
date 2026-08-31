import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { readFile, stat } from 'node:fs/promises'
import path from 'node:path'
import test from 'node:test'
import {
  CENARIOS_EDUCACAO_PATHS,
  assertCenariosEducacaoBundle,
  checkCenariosEducacaoPublication,
  materializeCenariosEducacaoPublication,
  promoteCenariosEducacaoPublication,
} from '../lib/cenarios-educacao-publication.mjs'

const repoRoot = path.resolve(import.meta.dirname, '..', '..')
const bundlePath = path.join(repoRoot, CENARIOS_EDUCACAO_PATHS.bundle)
const registryPath = path.join(repoRoot, CENARIOS_EDUCACAO_PATHS.registry)
const advancedPath = path.join(repoRoot, CENARIOS_EDUCACAO_PATHS.advancedBundle)
const authoringPath = path.join(repoRoot, CENARIOS_EDUCACAO_PATHS.authoringContract)

function serialize(value) {
  return JSON.stringify(value, null, 2) + '\n'
}

function sha256(value) {
  return createHash('sha256').update(value, 'utf8').digest('hex')
}

function descriptor(relativePath, bytes) {
  return {
    path: relativePath.replaceAll('\\', '/'),
    sha256: sha256(bytes),
    byteSize: Buffer.byteLength(bytes, 'utf8'),
  }
}

function collectStrings(value, output = []) {
  if (typeof value === 'string') output.push(value)
  else if (Array.isArray(value)) value.forEach((item) => collectStrings(item, output))
  else if (value !== null && typeof value === 'object') Object.values(value).forEach((item) => collectStrings(item, output))
  return output
}

function normalize(value) {
  return value.normalize('NFKC').replace(/\s+/gu, ' ').trim().toLocaleLowerCase('pt-BR')
}

function findMeasures(value, output = []) {
  if (Array.isArray(value)) value.forEach((item) => findMeasures(item, output))
  else if (value !== null && typeof value === 'object') {
    if (typeof value.measureId === 'string') output.push(value)
    Object.values(value).forEach((item) => findMeasures(item, output))
  }
  return output
}

function median(values) {
  const ordered = [...values].sort((left, right) => left - right)
  return (ordered[4] + ordered[5]) / 2
}

test('materialização é determinística e coincide com os artefatos promovidos', async () => {
  const first = await materializeCenariosEducacaoPublication(repoRoot)
  const second = await materializeCenariosEducacaoPublication(repoRoot)
  assert.equal(first.bundleBytes, second.bundleBytes)
  assert.equal(first.registryBytes, second.registryBytes)
  assert.equal(first.registry.bundleSha256, sha256(first.bundleBytes))
  assert.equal(first.registry.bundleByteSize, Buffer.byteLength(first.bundleBytes, 'utf8'))
  await assert.doesNotReject(() => checkCenariosEducacaoPublication(repoRoot))
})

test('publicação ativa contém somente a fronteira editorial e a lente focal', async () => {
  const bundle = JSON.parse(await readFile(bundlePath, 'utf8'))
  const registry = JSON.parse(await readFile(registryPath, 'utf8'))
  assert.equal(bundle.schemaVersion, 'vocacoes-pne-foresight-v2')
  assert.equal(bundle.publicationStatus, 'exploratory_model_public_data_audited')
  assert.equal(bundle.baseline, undefined)
  assert.deepEqual(Object.keys(bundle.region), ['stateCode', 'slug', 'name', 'municipalityCount'])
  assert.equal(bundle.municipalities.length, 1)
  assert.equal(bundle.municipalities[0].municipalityIbgeCode, '4313375')
  assert.equal(bundle.municipalities[0].baselineContribution, undefined)
  assert.equal(registry.focalMunicipalityIbgeCode, '4313375')
  assert.equal(registry.regionalMunicipalityCount, 10)
  assert.equal(registry.publicDataValidationStatus, 'passed')
  const activeText = serialize({ bundle, registry })
  for (const removedText of ['Novo Hamburgo', '4313409', 'contraste', 'oficina', 'validação humana']) {
    assert.ok(!activeText.toLocaleLowerCase('pt-BR').includes(removedText.toLocaleLowerCase('pt-BR')))
  }
})

test('ponte diagnóstica resolve IDs e prova zero cópia de afirmações longas', async () => {
  const bundle = JSON.parse(await readFile(bundlePath, 'utf8'))
  const advanced = JSON.parse(await readFile(advancedPath, 'utf8'))
  const bridge = bundle.diagnosticBridge
  assert.equal(bridge.route, '#vocacoes-regiao')
  assert.equal(bridge.evidenceRefCount, 18)
  assert.equal(bridge.resolvedEvidenceRefCount, 18)
  assert.equal(bridge.copiedDiagnosticAssertions, 0)
  assert.equal(bridge.deDuplicationAudit.minimumLength, 80)
  assert.deepEqual(bridge.deDuplicationAudit.whitelist, [])
  assert.equal(bridge.deDuplicationAudit.duplicateCount, 0)

  const advancedStrings = new Set(
    collectStrings(advanced)
      .map(normalize)
      .filter((text) => text.length >= 80),
  )
  const scenarioSlice = {
    crossCuttingDrivers: bundle.crossCuttingDrivers,
    crossImpactMatrix: bundle.crossImpactMatrix,
    scenarios: bundle.scenarios,
    municipalities: bundle.municipalities,
    pneStressTest: bundle.pneStressTest,
    actions: bundle.actions,
    sentinelIndicators: bundle.sentinelIndicators,
  }
  const duplicated = collectStrings(scenarioSlice)
    .map(normalize)
    .filter((text) => text.length >= 80 && advancedStrings.has(text))
  assert.deepEqual(duplicated, [])
})

test('transversais preservam maturidades assimétricas e limites de afirmação', async () => {
  const bundle = JSON.parse(await readFile(bundlePath, 'utf8'))
  assert.deepEqual(
    bundle.crossCuttingDrivers.map((driver) => [driver.driverId, driver.maturity, driver.availability]),
    [
      ['X_CLIMATE', 'OBSERVED_PUBLIC_SENTINEL', 'calculated'],
      ['X_TECHNOLOGY', 'OBSERVED_SERIES', 'calculated'],
      ['X_FISCAL', 'OBSERVED_RECONCILED_CONTEXT', 'calculated'],
      ['X_REGULATION', 'EXPLICIT_GAP', 'unavailable'],
    ],
  )
  for (const driver of bundle.crossCuttingDrivers) {
    assert.equal(driver.coverage.municipalityCount, 10)
    assert.equal(driver.coverage.expectedMunicipalityCount, 10)
    assert.ok(driver.claimCeiling.length > 80)
    assert.ok(driver.unresolvedGap.length > 60)
  }
  const regulation = bundle.crossCuttingDrivers.find((driver) => driver.driverId === 'X_REGULATION')
  assert.equal(regulation.proxyAudit.eligiblePublicEvidenceCount, 0)
  assert.equal(regulation.proxyAudit.municipalitiesWithExcludedProxy, 10)
})

test('indicadores tecnológicos reproduzem razões ponderadas sem arredondar o cálculo', async () => {
  const bundle = JSON.parse(await readFile(bundlePath, 'utf8'))
  const contract = JSON.parse(await readFile(authoringPath, 'utf8'))
  const driver = bundle.crossCuttingDrivers.find((candidate) => candidate.driverId === 'X_TECHNOLOGY')
  for (const metric of driver.metrics) {
    let numerator = 0
    let denominator = 0
    for (const code of contract.region.municipalityIbgeCodes) {
      const details = JSON.parse(await readFile(path.join(repoRoot, 'public', 'data', 'municipios', code, 'details.json'), 'utf8'))
      const point = details[metric.metricId].series_components.find((candidate) => candidate.ano === 2025)
      numerator += point.numerador
      denominator += point.denominador
    }
    assert.equal(metric.region.numerator, numerator)
    assert.equal(metric.region.denominator, denominator)
    assert.equal(metric.region.valueRaw, denominator === 0 ? null : (numerator / denominator) * 100)
  }
  assert.deepEqual(
    driver.metrics.map((metric) => [metric.metricId, metric.region.numerator, metric.region.denominator]),
    [
      ['internet_aprendizagem', 604, 734],
      ['acesso_internet_computador', 342, 734],
    ],
  )
})

test('contexto fiscal usa distribuição municipal reconciliada, sem soma indevida', async () => {
  const bundle = JSON.parse(await readFile(bundlePath, 'utf8'))
  const contract = JSON.parse(await readFile(authoringPath, 'utf8'))
  const margins = []
  for (const code of contract.region.municipalityIbgeCodes) {
    const finance = JSON.parse(await readFile(path.join(repoRoot, 'public', 'data', 'municipios', code, 'financeiro.json'), 'utf8'))
    assert.equal(finance.constitutionalApplication.status, 'reconciled')
    assert.equal(finance.reconciliation.status, 'reconciled')
    assert.equal(finance.constitutionalApplication.referenceYear, 2025)
    margins.push(finance.constitutionalApplication.mdeMarginFromMinimum.value)
  }
  const driver = bundle.crossCuttingDrivers.find((candidate) => candidate.driverId === 'X_FISCAL')
  assert.equal(driver.calculation.minimumMarginPercentagePoints, Math.min(...margins))
  assert.equal(driver.calculation.medianMarginPercentagePoints, median(margins))
  assert.equal(driver.calculation.maximumMarginPercentagePoints, Math.max(...margins))
  assert.equal(driver.calculation.novaSantaRitaMarginPercentagePoints, 0.09)
  assert.equal(driver.calculation.medianMarginPercentagePoints, 1.505)
})

test('sentinela climática deduplica protocolo municipal e preserva o recorte temporal', async () => {
  const bundle = JSON.parse(await readFile(bundlePath, 'utf8'))
  const contract = JSON.parse(await readFile(authoringPath, 'utf8'))
  const protocols = new Set()
  const focalProtocols = new Set()
  for (const code of contract.region.municipalityIbgeCodes) {
    const matrix = JSON.parse(await readFile(path.join(repoRoot, 'public', 'data', 'pne2026-matriz', 'municipios', code + '.json'), 'utf8'))
    for (const measure of findMeasures(matrix).filter((candidate) => candidate.measureId.startsWith('midr.atlas.'))) {
      const protocol = /(?:^|;)protocolS2id=([^;]+)/u.exec(String(measure.dimensions ?? ''))
      const year = Number(measure.period)
      if (protocol === null || year < 2014 || year > 2025) continue
      const key = code + '|' + protocol[1]
      protocols.add(key)
      if (code === '4313375') focalProtocols.add(key)
    }
  }
  const driver = bundle.crossCuttingDrivers.find((candidate) => candidate.driverId === 'X_CLIMATE')
  assert.equal(driver.calculation.uniqueRegisteredOrRecognizedEventProtocols, protocols.size)
  assert.equal(driver.calculation.novaSantaRitaUniqueEventProtocols, focalProtocols.size)
  assert.equal(protocols.size, 66)
  assert.equal(focalProtocols.size, 9)
})

test('digest regional cobre exatamente 30 arquivos locais e é reproduzível', async () => {
  const bundle = JSON.parse(await readFile(bundlePath, 'utf8'))
  const contract = JSON.parse(await readFile(authoringPath, 'utf8'))
  const specs = contract.region.municipalityIbgeCodes.flatMap((code) => [
    { municipalityIbgeCode: code, kind: 'details', relativePath: 'public/data/municipios/' + code + '/details.json' },
    { municipalityIbgeCode: code, kind: 'finance', relativePath: 'public/data/municipios/' + code + '/financeiro.json' },
    { municipalityIbgeCode: code, kind: 'pneMatrix', relativePath: 'public/data/pne2026-matriz/municipios/' + code + '.json' },
  ])
  const files = []
  for (const spec of specs) {
    const bytes = await readFile(path.join(repoRoot, spec.relativePath), 'utf8')
    files.push({
      municipalityIbgeCode: spec.municipalityIbgeCode,
      kind: spec.kind,
      ...descriptor(spec.relativePath, bytes),
    })
  }
  const manifest = {
    schemaVersion: 'cenarios-educacao-regional-public-inputs-v1',
    regionSlug: 'vale-do-sinos',
    files,
  }
  assert.equal(files.length, 30)
  assert.equal(sha256(serialize(manifest)), bundle.sourceSnapshot.regionalPublicInputs.sha256)
})

test('quatro configurações mantêm distância morfológica mínima quatro e peso equivalente', async () => {
  const bundle = JSON.parse(await readFile(bundlePath, 'utf8'))
  const factorIds = bundle.factorRegistry.map((factor) => factor.factorId)
  const distances = []
  for (let left = 0; left < bundle.scenarios.length; left += 1) {
    for (let right = left + 1; right < bundle.scenarios.length; right += 1) {
      distances.push(factorIds.reduce(
        (distance, factorId) => distance
          + Number(bundle.scenarios[left].configurationStates[factorId] !== bundle.scenarios[right].configurationStates[factorId]),
        0,
      ))
    }
  }
  assert.equal(Math.min(...distances), 4)
  assert.equal(bundle.publicationPolicy.equalScenarioWeight, true)
  assert.equal(bundle.publicationPolicy.futureProbabilitiesAllowed, false)
  assert.equal(bundle.publicationPolicy.automaticRecommendationAllowed, false)
})

test('assertor falha fechado em mutações estruturais e semânticas', async () => {
  const bundle = JSON.parse(await readFile(bundlePath, 'utf8'))
  const mutations = [
    ['cenário ausente', (candidate) => candidate.scenarios.pop(), /quatro cenários/u],
    ['maturidade adulterada', (candidate) => { candidate.crossCuttingDrivers[0].maturity = 'EXPLICIT_GAP' }, /maturidade publicada/u],
    ['duplicação declarada', (candidate) => { candidate.diagnosticBridge.deDuplicationAudit.duplicateCount = 1 }, /zero duplicações/u],
    ['lente focal adulterada', (candidate) => { candidate.municipalities[0].municipalityIbgeCode = '4303905' }, /lente exclusiva/u],
    ['distância enfraquecida', (candidate) => { candidate.morphologicalField.minimumObservedPairwiseHammingDistance = 2 }, /distância morfológica/u],
  ]
  for (const [label, mutate, expected] of mutations) {
    const candidate = structuredClone(bundle)
    mutate(candidate)
    assert.throws(() => assertCenariosEducacaoBundle(candidate), expected, label)
  }
})

test('promoção idêntica preserva bytes e mtime dos dois artefatos', async () => {
  const before = {
    bundle: await stat(bundlePath),
    registry: await stat(registryPath),
    bundleBytes: await readFile(bundlePath, 'utf8'),
    registryBytes: await readFile(registryPath, 'utf8'),
  }
  await promoteCenariosEducacaoPublication(repoRoot)
  const after = {
    bundle: await stat(bundlePath),
    registry: await stat(registryPath),
    bundleBytes: await readFile(bundlePath, 'utf8'),
    registryBytes: await readFile(registryPath, 'utf8'),
  }
  assert.equal(after.bundleBytes, before.bundleBytes)
  assert.equal(after.registryBytes, before.registryBytes)
  assert.equal(after.bundle.mtimeMs, before.bundle.mtimeMs)
  assert.equal(after.registry.mtimeMs, before.registry.mtimeMs)
})
