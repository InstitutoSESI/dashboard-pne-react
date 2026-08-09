import assert from 'node:assert/strict'
import { access, readFile, readdir } from 'node:fs/promises'
import test from 'node:test'

import {
  createPne2026DiagnosticLoader,
  PNE_2026_DIAGNOSTIC_V3_CURRENT_PATH,
  PNE_2026_DIAGNOSTIC_V3_RELEASE_MANIFEST_PATH,
  PNE_2026_DIAGNOSTIC_V3_RELEASE_MUNICIPAL_PATH,
  Pne2026DiagnosticLoadError,
  parsePne2026DiagnosticReleasePointer,
} from '../../src/features/diagnostic/pne2026DiagnosticLoader.js'
import {
  parsePne2026PublicDiagnosticV3,
  resolvePne2026PublicDiagnosticV3,
} from '../../src/features/diagnostic/pne2026PublicDiagnosticV3.js'

const MUNICIPALITY_ID = '4300034'
const JAGUARI_ID = '4311106'
const VITORIA_ES_ID = '3205309'
const CAPES_RELATION_ID = 'relation.16.a.capes_titulados_oferta_local'
const currentUrl = new URL(
  '../../public/data/pne2026-diagnostic-v3/current.json',
  import.meta.url,
)
const current = JSON.parse(await readFile(currentUrl, 'utf8'))
const RELEASE_ID = current.releaseId
const releaseRoot = new URL(
  `../../public/data/pne2026-diagnostic-v3/releases/${RELEASE_ID}/`,
  import.meta.url,
)
const MANIFEST_PATH = PNE_2026_DIAGNOSTIC_V3_RELEASE_MANIFEST_PATH.replace(
  '{releaseId}',
  RELEASE_ID,
)
const MUNICIPAL_PATH = PNE_2026_DIAGNOSTIC_V3_RELEASE_MUNICIPAL_PATH
  .replace('{releaseId}', RELEASE_ID)
  .replace('{municipalityId}', MUNICIPALITY_ID)
const releaseManifest = JSON.parse(await readFile(
  new URL('manifest.json', releaseRoot),
  'utf8',
))
const v3Payload = JSON.parse(await readFile(
  new URL(`municipios/${MUNICIPALITY_ID}.json`, releaseRoot),
  'utf8',
))
const capesSource = JSON.parse(await readFile(
  new URL(
    '../../data_pipeline/data/pne_macro_sources/capes_2024/normalized.json',
    import.meta.url,
  ),
  'utf8',
))

function createFixtureLoader({
  expectedMunicipalityCount = 497,
  pointer = current,
  manifest = releaseManifest,
  payload = v3Payload,
  currentError,
  manifestError,
  municipalError,
} = {}) {
  const calls = []
  const logs = []
  const loader = createPne2026DiagnosticLoader({
    expectedMunicipalityCount,
    fetchJson: async (path, options) => {
      calls.push({ path, options })
      if (path === PNE_2026_DIAGNOSTIC_V3_CURRENT_PATH) {
        if (currentError) throw currentError
        return structuredClone(pointer)
      }
      if (path.endsWith('/manifest.json')) {
        if (manifestError) throw manifestError
        return structuredClone(manifest)
      }
      if (municipalError) throw municipalError
      return structuredClone(payload)
    },
    logger: (...items) => logs.push(items),
  })
  return { calls, load: loader.load, logs }
}

test('happy path requests only current, active manifest, and active municipality', async () => {
  const fixture = createFixtureLoader()
  const [first, second] = await Promise.all([
    fixture.load(MUNICIPALITY_ID),
    fixture.load(MUNICIPALITY_ID),
  ])
  assert.deepEqual(first, second)
  assert.equal(first.diagnosticSource, 'v3')
  assert.equal(first.diagnosticReleaseId, RELEASE_ID)
  assert.equal(first.pne2026PublicDiagnostic.municipalityId, MUNICIPALITY_ID)
  assert.deepEqual(
    fixture.calls.map(({ path }) => path),
    [PNE_2026_DIAGNOSTIC_V3_CURRENT_PATH, MANIFEST_PATH, MUNICIPAL_PATH],
  )
  assert.deepEqual(fixture.calls[0].options, { cache: 'no-store' })
  assert.equal(fixture.logs.length, 0)
})

test('manifest follows the active state municipality count and rejects another universe', async () => {
  const alManifest = {
    ...structuredClone(releaseManifest),
    municipalityCount: 102,
  }
  const alFixture = createFixtureLoader({
    expectedMunicipalityCount: 102,
    manifest: alManifest,
  })
  const result = await alFixture.load(MUNICIPALITY_ID)
  assert.equal(result.diagnosticSource, 'v3')

  const mismatchedFixture = createFixtureLoader({
    expectedMunicipalityCount: 102,
  })
  await assert.rejects(mismatchedFixture.load(MUNICIPALITY_ID), {
    code: 'invalid_manifest',
    stage: 'manifest',
  })
})

test('same release deduplicates payloads while current is refreshed', async () => {
  const fixture = createFixtureLoader()
  await fixture.load(MUNICIPALITY_ID)
  await fixture.load(MUNICIPALITY_ID)
  assert.deepEqual(
    fixture.calls.map(({ path }) => path),
    [
      PNE_2026_DIAGNOSTIC_V3_CURRENT_PATH,
      MANIFEST_PATH,
      MUNICIPAL_PATH,
      PNE_2026_DIAGNOSTIC_V3_CURRENT_PATH,
    ],
  )
})

test('a new release cannot reuse the previous release payload cache', async () => {
  const pointer = structuredClone(current)
  const calls = []
  const secondRelease = 'a'.repeat(64)
  const loader = createPne2026DiagnosticLoader({
    expectedMunicipalityCount: 497,
    fetchJson: async (path) => {
      calls.push(path)
      if (path === PNE_2026_DIAGNOSTIC_V3_CURRENT_PATH) {
        return structuredClone(pointer)
      }
      if (path.endsWith('/manifest.json')) {
        return {
          ...structuredClone(releaseManifest),
          aggregateHash: pointer.releaseId,
        }
      }
      return structuredClone(v3Payload)
    },
  })
  const first = await loader.load(MUNICIPALITY_ID)
  Object.assign(pointer, {
    releaseId: secondRelease,
    aggregateHash: secondRelease,
    manifestPath: `releases/${secondRelease}/manifest.json`,
  })
  const second = await loader.load(MUNICIPALITY_ID)
  assert.equal(first.diagnosticReleaseId, RELEASE_ID)
  assert.equal(second.diagnosticReleaseId, secondRelease)
  assert.equal(
    calls.filter((path) => path.endsWith(`/${MUNICIPALITY_ID}.json`)).length,
    2,
  )
})

test('pointer rejects traversal, absolute URLs, and release/hash divergence', () => {
  for (const mutate of [
    (pointer) => { pointer.manifestPath = '../manifest.json' },
    (pointer) => { pointer.manifestPath = 'https://example.test/manifest.json' },
    (pointer) => { pointer.aggregateHash = 'a'.repeat(64) },
  ]) {
    const pointer = structuredClone(current)
    mutate(pointer)
    assert.throws(
      () => parsePne2026DiagnosticReleasePointer(pointer),
      /Publicação PNE V3 inválida/,
    )
  }
})

const failures = [
  ['current missing', 'current_unavailable', () => ({
    currentError: new Error('404'),
  })],
  ['current invalid', 'invalid_pointer', () => {
    const pointer = structuredClone(current)
    pointer.manifestPath = '../manifest.json'
    return { pointer }
  }],
  ['release missing', 'release_unavailable', () => ({
    manifestError: new Error('404'),
  })],
  ['manifest invalid', 'invalid_manifest', () => {
    const manifest = structuredClone(releaseManifest)
    manifest.schemaVersion = 'future'
    return { manifest }
  }],
  ['release hash mismatch', 'invalid_manifest', () => {
    const manifest = structuredClone(releaseManifest)
    manifest.aggregateHash = '0'.repeat(64)
    return { manifest }
  }],
  ['municipal file missing', 'municipality_unavailable', () => ({
    municipalError: new Error('404'),
  })],
  ['municipal payload invalid', 'invalid_payload', () => {
    const payload = structuredClone(v3Payload)
    payload.schemaVersion = 'future'
    return { payload }
  }],
  ['relationId mismatch', 'invalid_payload', () => {
    const payload = structuredClone(v3Payload)
    payload.results[0].relationId = 'relation.unknown'
    return { payload }
  }],
  ['summary mismatch', 'invalid_payload', () => {
    const payload = structuredClone(v3Payload)
    payload.summary.visibleResultCount += 1
    return { payload }
  }],
]

for (const [name, expectedCode, arrange] of failures) {
  test(`V3 ${name} returns a structured error once and never returns partial data`, async () => {
    const fixture = createFixtureLoader(arrange())
    const results = await Promise.allSettled([
      fixture.load(MUNICIPALITY_ID),
      fixture.load(MUNICIPALITY_ID),
    ])
    for (const result of results) {
      assert.equal(result.status, 'rejected')
      assert.ok(result.reason instanceof Pne2026DiagnosticLoadError)
      assert.equal(result.reason.code, expectedCode)
      assert.equal(result.reason.municipalityId, MUNICIPALITY_ID)
    }
    assert.equal(fixture.logs.length, 1)
    assert.ok(fixture.calls.every(({ path }) => (
      path.startsWith('/data/pne2026-diagnostic-v3/')
    )))
  })
}

test('a failed request can be retried through the existing loader', async () => {
  let currentAttempts = 0
  const loader = createPne2026DiagnosticLoader({
    expectedMunicipalityCount: 497,
    logger: () => {},
    fetchJson: async (path) => {
      if (path === PNE_2026_DIAGNOSTIC_V3_CURRENT_PATH) {
        currentAttempts += 1
        if (currentAttempts === 1) throw new Error('temporary')
        return structuredClone(current)
      }
      if (path.endsWith('/manifest.json')) return structuredClone(releaseManifest)
      return structuredClone(v3Payload)
    },
  })
  await assert.rejects(loader.load(MUNICIPALITY_ID), {
    code: 'current_unavailable',
  })
  const result = await loader.load(MUNICIPALITY_ID)
  assert.equal(result.diagnosticReleaseId, RELEASE_ID)
  assert.equal(currentAttempts, 2)
})

test('invalid municipality is structured and causes no network request', async () => {
  const fixture = createFixtureLoader()
  await assert.rejects(fixture.load('../4300034'), {
    code: 'invalid_municipality',
    stage: 'input',
  })
  assert.deepEqual(fixture.calls, [])
  assert.equal(fixture.logs.length, 1)
})

test('runtime import graph contains no V2 source, fallback, dual mode, or root manifest', async () => {
  const [hook, loader, types, v3] = await Promise.all([
    readFile(new URL('../../src/hooks/useMunicipioDiagnostic.ts', import.meta.url), 'utf8'),
    readFile(new URL('../../src/features/diagnostic/pne2026DiagnosticLoader.js', import.meta.url), 'utf8'),
    readFile(new URL('../../src/features/diagnostic/diagnosticTypes.ts', import.meta.url), 'utf8'),
    readFile(new URL('../../src/features/diagnostic/pne2026PublicDiagnosticV3.js', import.meta.url), 'utf8'),
  ])
  const runtime = `${hook}\n${loader}\n${types}\n${v3}`
  assert.doesNotMatch(runtime, /VITE_PNE_DIAGNOSTIC_SOURCE/)
  assert.doesNotMatch(runtime, /pne2026DiagnosticV2Compatibility|staticData/)
  assert.doesNotMatch(runtime, /v2-fallback|configuredSource|allowDual|loadV2/)
  assert.doesNotMatch(runtime, /Pne2026\w*V2|MunicipalDiagnostic\w*V2/)
  assert.doesNotMatch(
    types,
    /\btracksGoal\b|\btracks_goal\b|\bhasDistance\b|\brelationshipType\b|\btier\b|\bpriorityOrder\b|\bclassificationPolicy\b|\bvaluePolicy\b|\bmeta_label\b/,
  )
  assert.doesNotMatch(runtime, /\/pne2026-diagnostic-v3\/manifest\.json/)
  await assert.rejects(access(
    new URL(
      '../../src/features/diagnostic/pne2026DiagnosticV2Compatibility.js',
      import.meta.url,
    ),
  ))
})

test('all 497 immutable V3 payloads preserve the validated release totals', async (t) => {
  const municipalityDirectory = new URL('municipios/', releaseRoot)
  const files = (await readdir(municipalityDirectory))
    .filter((name) => /^\d{7}\.json$/.test(name))
    .toSorted()
  const totals = {
    municipalities: 0,
    results: 0,
    progress: 0,
    tracking: 0,
    complementary: 0,
    advance: 0,
    maintain: 0,
    unclassified: 0,
    percentAbove100: 0,
    countAbove100: 0,
    duplicates: 0,
  }
  const rows = []
  const relationIds = new Set()
  const essentialRelationIds = new Set()
  const standardRelationIds = new Set()
  const themeIds = new Set()
  const capesResultsByMunicipality = new Map()
  let jaguariPayload
  let jaguariViewModel

  for (const file of files) {
    const payload = parsePne2026PublicDiagnosticV3(JSON.parse(
      await readFile(new URL(file, municipalityDirectory), 'utf8'),
    ))
    const viewModel = resolvePne2026PublicDiagnosticV3(payload)
    const results = viewModel.goals.flatMap((goal) => goal.results)
    const ids = results.map((result) => result.relationId)
    const progressResults = results.filter((result) => result.mode === 'progress')
    const trackingResults = results.filter((result) => result.mode === 'tracking')
    const complementaryResults = results.filter(
      (result) => result.mode === 'complementary',
    )
    const availableProgressResults = progressResults.filter(
      (result) => result.dataStatus === 'available',
    )
    const availableTrackingResults = trackingResults.filter(
      (result) => result.dataStatus === 'available',
    )
    const capesResult = payload.results.find(
      (result) => result.relationId === CAPES_RELATION_ID,
    )
    assert.match(payload.municipality.id, /^43\d{5}$/)
    assert.notEqual(payload.municipality.id, VITORIA_ES_ID)
    assert.equal(
      payload.results.every((result) => (
        typeof result.relationId === 'string'
        && result.relationId.length > 0
      )),
      true,
    )
    assert.equal(results.some((result) => result.mode === 'hidden'), false)
    assert.equal(payload.summary.visibleResultCount, results.length)
    assert.equal(payload.summary.progressResultCount, progressResults.length)
    assert.equal(payload.summary.trackingResultCount, trackingResults.length)
    assert.equal(
      payload.summary.legalReferenceResultCount,
      availableProgressResults.length,
    )
    assert.equal(
      payload.summary.monitoringReferenceResultCount,
      availableTrackingResults.length,
    )
    assert.equal(
      payload.summary.complementaryResultCount,
      complementaryResults.length,
    )
    totals.municipalities += 1
    totals.results += results.length
    totals.progress += progressResults.length
    totals.tracking += trackingResults.length
    totals.complementary += complementaryResults.length
    totals.advance += progressResults.filter(
      (result) => result.classification === 'advance',
    ).length
    totals.maintain += progressResults.filter(
      (result) => result.classification === 'maintain',
    ).length
    totals.unclassified += availableProgressResults.filter(
      (result) => result.classification == null,
    ).length
    totals.percentAbove100 += results.filter(
      (result) => result.current.unit === 'percent' && result.current.value > 100,
    ).length
    totals.countAbove100 += results.filter(
      (result) => result.current.unit === 'count' && result.current.value > 100,
    ).length
    totals.duplicates += ids.length - new Set(ids).size
    if (capesResult?.dataStatus === 'available') {
      capesResultsByMunicipality.set(payload.municipality.id, capesResult)
    }
    if (payload.municipality.id === JAGUARI_ID) {
      jaguariPayload = payload
      jaguariViewModel = viewModel
    }
    for (const result of results) {
      relationIds.add(result.relationId)
      themeIds.add(result.themeId)
      if (result.summaryPriority === 'essential') {
        essentialRelationIds.add(result.relationId)
      } else {
        standardRelationIds.add(result.relationId)
      }
    }
    rows.push({
      id: payload.municipality.id,
      name: payload.municipality.name,
      resultCount: results.length,
    })
  }

  assert.equal(files.length, releaseManifest.municipalityCount)
  assert.equal(
    releaseManifest.progressResultCount
      + releaseManifest.trackingResultCount
      + releaseManifest.complementaryResultCount,
    releaseManifest.resultCount,
  )
  assert.deepEqual(totals, {
    municipalities: releaseManifest.municipalityCount,
    results: releaseManifest.resultCount,
    progress: releaseManifest.progressResultCount,
    tracking: releaseManifest.trackingResultCount,
    complementary: releaseManifest.complementaryResultCount,
    advance: releaseManifest.classificationCounts.advance,
    maintain: releaseManifest.classificationCounts.maintain,
    unclassified: releaseManifest.classificationCounts.unclassified,
    percentAbove100: releaseManifest.percentValuesAbove100Count,
    countAbove100: releaseManifest.countValuesAbove100Count,
    duplicates: 0,
  })
  assert.equal(
    Math.min(...rows.map((row) => row.resultCount)),
    releaseManifest.minimumResultsPerMunicipality,
  )
  assert.equal(
    Math.max(...rows.map((row) => row.resultCount)),
    releaseManifest.maximumResultsPerMunicipality,
  )
  assert.equal(relationIds.size, 51)
  assert.equal(themeIds.size, 10)
  assert.equal(essentialRelationIds.size, 13)
  assert.equal(standardRelationIds.size, 38)
  assert.equal(rows.find((row) => row.id === MUNICIPALITY_ID)?.name, 'Aceguá')
  assert.equal(rows.find((row) => row.id === '4319356')?.name, 'São Pedro da Serra')
  assert.equal(rows.some((row) => row.id === VITORIA_ES_ID), false)

  const positiveCapesMunicipalities = Object.values(capesSource.records)
    .filter((record) => (
      record.mastersAwarded + record.doctoratesAwarded > 0
    ))
  assert.equal(capesResultsByMunicipality.size, 35)
  assert.equal(capesResultsByMunicipality.size, positiveCapesMunicipalities.length)
  for (const record of positiveCapesMunicipalities) {
    const result = capesResultsByMunicipality.get(record.municipalityId)
    assert.ok(result, `CAPES ausente em ${record.municipalityId}`)
    assert.equal(
      result.value,
      record.mastersAwarded + record.doctoratesAwarded,
    )
    assert.equal(result.dataStatus, 'available')
  }

  const jaguariCapes = jaguariPayload?.results.find(
    (result) => result.relationId === CAPES_RELATION_ID,
  )
  const resolvedJaguariCapes = jaguariViewModel?.goals
    .flatMap((goal) => goal.results)
    .find((result) => result.relationId === CAPES_RELATION_ID)
  assert.ok(jaguariCapes)
  assert.ok(resolvedJaguariCapes)
  assert.equal(jaguariCapes.value, 24)
  assert.equal(jaguariCapes.numeratorValue, 24)
  assert.equal(jaguariCapes.year, 2024)
  assert.equal(jaguariCapes.dataStatus, 'available')
  assert.equal(resolvedJaguariCapes.mode, 'complementary')
  for (const forbidden of [
    'distance',
    'remainingGap',
    'favorableDifference',
    'status',
    'classification',
    'trend',
    'projection',
    'resolvedReferenceId',
  ]) {
    assert.equal(Object.hasOwn(jaguariCapes, forbidden), false)
  }
  for (const forbidden of [
    'indicatorReference',
    'reference',
    'distance',
    'status',
    'classification',
    'trajectory',
    'projection',
  ]) {
    assert.equal(Object.hasOwn(resolvedJaguariCapes, forbidden), false)
  }
  t.diagnostic(`v3-release=${JSON.stringify(totals)}`)
  t.diagnostic(`inspection-cases=${JSON.stringify({
    acegua: rows.find((row) => row.id === MUNICIPALITY_ID),
    saoPedroDaSerra: rows.find((row) => row.id === '4319356'),
    minimum: rows.find((row) => row.resultCount === 51),
    maximum: rows.find((row) => row.resultCount === 51),
  })}`)
})
