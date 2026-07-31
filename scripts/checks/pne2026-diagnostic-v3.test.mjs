import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

import {
  PNE_2026_GOAL_INDICATOR_CONTRACT,
} from '../../src/data/pne2026GoalIndicatorContract.js'
import {
  sanitizePne2026PublicDiagnostic,
} from './support/pne2026DiagnosticV2Audit.mjs'
import {
  PNE_2026_CONTRACT_HASH,
  PNE_2026_PRESENTATION_POLICY_HASH,
  PNE_2026_V3_RESULT_FIELDS,
  parsePne2026PublicDiagnosticV3,
  resolvePne2026PublicDiagnosticV3,
} from '../../src/features/diagnostic/pne2026PublicDiagnosticV3.js'


const REPO_ROOT = new URL('../../', import.meta.url)
const contract = JSON.parse(execFileSync(
  'git',
  ['show', 'HEAD:public/data/municipios/4300034/diagnostico.json'],
  { cwd: REPO_ROOT, encoding: 'utf8', maxBuffer: 32 * 1024 * 1024 },
))
const pythonBuilder = [
  'import json,sys',
  'from data_pipeline.src.pne2026_public_diagnostic_v3 import build_pne2026_public_diagnostic_v3',
  'from data_pipeline.scripts.materialize_pne2026_public_diagnostic_v3 import _goal_11b_results',
  'payload=json.load(sys.stdin)',
  'goal11b,_=_goal_11b_results()',
  'municipality_id=str(payload["pne2026PublicDiagnosticV2"]["municipalityId"])',
  'json.dump(build_pne2026_public_diagnostic_v3(payload,methodology_results=goal11b[municipality_id]),sys.stdout,ensure_ascii=False,allow_nan=False,separators=(",",":"))',
].join(';')
const v3 = JSON.parse(execFileSync(
  'python',
  ['-c', pythonBuilder],
  {
    cwd: REPO_ROOT,
    input: JSON.stringify(contract),
    encoding: 'utf8',
    maxBuffer: 32 * 1024 * 1024,
  },
))
const relationsById = new Map(
  PNE_2026_GOAL_INDICATOR_CONTRACT.relations.map((relation) => [
    relation.relationId,
    relation,
  ]),
)


function flatten(viewModel) {
  return viewModel.goals.flatMap((goal) => goal.results)
}

function normalizedView(viewModel) {
  return flatten(viewModel)
    .map((result) => ({
      relationId: result.relationId,
      goalId: result.goalId,
      indicatorId: result.indicatorId,
      mode: result.mode,
      title: result.goalTitle,
      publicName: result.publicName,
      value: result.current?.value ?? null,
      displayValue: result.current?.displayValue ?? null,
      displayText: result.current?.displayText ?? null,
      year: result.current?.year ?? null,
      unit: result.current?.unit ?? null,
      reference: result.mode === 'progress' && result.indicatorReference
        ? {
          value: result.indicatorReference.value,
          year: result.indicatorReference.year,
          direction: result.indicatorReference.direction,
          validationStatus: result.indicatorReference.validationStatus,
        }
        : null,
      distance: result.mode === 'progress' ? result.distance : null,
      remainingGap: result.mode === 'progress' ? result.remainingGap : null,
      favorableDifference: result.mode === 'progress'
        ? result.favorableDifference
        : null,
      status: result.mode === 'progress' ? result.status : null,
      classification: result.mode === 'progress' ? result.classification : null,
      stateComparison: result.mode === 'progress' ? result.stateComparison : null,
      statewidePosition: result.mode === 'progress' ? result.statewidePosition : null,
      similarMunicipalities: result.mode === 'progress'
        ? result.similarMunicipalities
        : null,
      trajectory: result.mode === 'progress' ? result.trajectory : null,
      publicReading: result.publicReading,
      themeId: result.themeId,
      displayOrder: result.displayOrder,
      summaryPriority: result.summaryPriority,
      displayGroup: result.displayGroup,
      dataStatus: result.dataStatus,
    }))
    .toSorted((left, right) => left.relationId.localeCompare(right.relationId))
}


test('V3 parser accepts only the pinned schema, versions, hashes, and allowlist', () => {
  const parsed = parsePne2026PublicDiagnosticV3(v3)
  assert.equal(parsed.schemaVersion, 'pne2026-public-diagnostic-v4')
  assert.equal(parsed.contractVersion, '1.9.0')
  assert.equal(parsed.contractHash, PNE_2026_CONTRACT_HASH)
  assert.equal(parsed.presentationPolicyVersion, '1.7.0')
  assert.equal(
    parsed.presentationPolicyHash,
    PNE_2026_PRESENTATION_POLICY_HASH,
  )
  assert.deepEqual(
    new Set(Object.keys(parsed.results[0])).difference(PNE_2026_V3_RESULT_FIELDS),
    new Set(),
  )

  const badHash = structuredClone(v3)
  badHash.presentationPolicyHash = '0'.repeat(64)
  assert.throws(
    () => parsePne2026PublicDiagnosticV3(badHash),
    /presentationPolicyHash/,
  )
  const deprecated = structuredClone(v3)
  deprecated.results[0].relationshipType = 'direct'
  assert.throws(
    () => parsePne2026PublicDiagnosticV3(deprecated),
    /campos desconhecidos/,
  )
})

test('V3 relationId is mandatory, authoritative, and cannot fall back to the pair', () => {
  const missing = structuredClone(v3)
  delete missing.results[0].relationId
  assert.throws(() => parsePne2026PublicDiagnosticV3(missing), /relationId/)

  const mismatch = structuredClone(v3)
  mismatch.results[0].goalId = '1.c'
  assert.throws(
    () => parsePne2026PublicDiagnosticV3(mismatch),
    /identidade canônica/,
  )

  const unknown = structuredClone(v3)
  unknown.results[0].relationId = 'relation.unknown'
  assert.throws(() => parsePne2026PublicDiagnosticV3(unknown), /desconhecido/)
})

test('basico_15_17 uses the canonical municipal reference without a relation-specific bridge', async () => {
  const adapterSource = await readFile(
    new URL('../../src/features/diagnostic/pne2026PublicDiagnosticV3.js', import.meta.url),
    'utf8',
  )
  assert.doesNotMatch(adapterSource, /V2_REFERENCE_COMPATIBILITY_BY_RELATION_ID/)
  assert.doesNotMatch(adapterSource, /relation\.4\.a\.basico_15_17/)

  const rawV3 = v3.results.find(
    (result) => result.relationId === 'relation.4.a.basico_15_17',
  )
  assert.ok(rawV3)
  for (const field of [
    'classification',
    'stateComparison',
    'statewidePosition',
    'similarMunicipalityComparison',
    'trend',
    'projection',
  ]) {
    assert.equal(Object.hasOwn(rawV3, field), false, field)
  }
  assert.equal(rawV3.resolvedReferenceId, 'monitoring.4.a.basico_15_17')
  assert.equal(rawV3.distance, rawV3.value - 100)
  assert.equal(rawV3.remainingGap, Math.max(0, 100 - rawV3.value))
  assert.equal(rawV3.favorableDifference, rawV3.distance)
  assert.match(
    rawV3.status,
    rawV3.value >= 100 ? /^Referência alcançada$/ : /^Abaixo da refer/,
  )

  const fromV2 = flatten(sanitizePne2026PublicDiagnostic(
    contract.pne2026PublicDiagnosticV2,
  )).find((result) => result.relationId === 'relation.4.a.basico_15_17')
  const fromV3 = flatten(resolvePne2026PublicDiagnosticV3(v3))
    .find((result) => result.relationId === 'relation.4.a.basico_15_17')
  assert.equal(fromV2.mode, 'tracking')
  assert.equal(fromV3.mode, 'tracking')
  assert.equal(fromV2.current.value, fromV3.current.value)
  assert.equal(fromV2.current.year, fromV3.current.year)
  assert.equal(fromV3.indicatorReference.value, 100)
  assert.equal(fromV3.indicatorReference.kind, 'municipal_monitoring_reference')
  assert.equal(fromV3.distance, rawV3.distance)
  assert.equal(fromV3.classification, null)
  assert.equal(fromV3.trajectory, null)
})

test('V3 rejects hidden and classification fields on complementary results', () => {
  const complementary = structuredClone(v3)
  const complementaryResult = complementary.results.find(
    (result) => relationsById.get(result.relationId).mode === 'complementary',
  )
  complementaryResult.classification = 'advance'
  assert.throws(
    () => parsePne2026PublicDiagnosticV3(complementary),
    /não autorizado|complementar/,
  )

  const hidden = structuredClone(v3)
  const hiddenRelation = PNE_2026_GOAL_INDICATOR_CONTRACT.relations.find(
    (relation) => relation.mode === 'hidden',
  )
  Object.assign(hidden.results[0], {
    relationId: hiddenRelation.relationId,
    goalId: hiddenRelation.goalId,
    indicatorId: hiddenRelation.indicatorId,
  })
  assert.throws(() => parsePne2026PublicDiagnosticV3(hidden), /oculta/)
})

test('V4 publishes every editorial relation and keeps negative states non-comparable', () => {
  const fromV3 = resolvePne2026PublicDiagnosticV3(v3)
  const results = flatten(fromV3)
  const eligibleRelationIds = new Set(
    PNE_2026_GOAL_INDICATOR_CONTRACT.relations
      .filter((relation) => relation.includeInDiagnostic && relation.mode !== 'hidden')
      .map((relation) => relation.relationId),
  )
  assert.deepEqual(new Set(results.map((result) => result.relationId)), eligibleRelationIds)
  assert.equal(results.length, 51)
  const negative = results.filter((result) => result.dataStatus !== 'available')
  assert.ok(negative.length > 0)
  assert.equal(
    negative.every((result) => (
      result.current.value == null
      && result.indicatorReference == null
      && result.distance == null
      && result.status == null
      && result.classification == null
    )),
    true,
  )
  const goal11b = results.filter((result) => result.goalId === '11.b')
  assert.deepEqual(
    goal11b.map((result) => result.indicatorId).toSorted(),
    ['fundamental_concluido_15_29', 'fundamental_concluido_15_mais'],
  )
  assert.equal(goal11b.some((result) => result.indicatorId === 'fundamental_concluido_18_mais'), false)
})

test('V3 preserves above-100 values and complementary neutrality in the view model', () => {
  const viewModel = resolvePne2026PublicDiagnosticV3(v3)
  const results = flatten(viewModel)
  assert.equal(
    Number(results.find((result) => result.indicatorId === 'pre_escola').current.value.toFixed(1)),
    122.2,
  )
  assert.equal(
    Number(results.find((result) => result.indicatorId === 'basico_6_17').current.value.toFixed(1)),
    111.8,
  )
  for (const result of results.filter((item) => item.mode === 'complementary')) {
    for (const field of [
      'distance',
      'status',
      'classification',
      'trajectory',
      'indicatorReference',
    ]) {
      assert.equal(field in result, false, `${result.relationId}:${field}`)
    }
  }
})

test('public loader is exclusively V3 while preserving the existing view-model consumers', async () => {
  const [hookSource, loaderSource, panelSource, presentationSource] = await Promise.all([
    readFile(new URL('../../src/hooks/useMunicipioDiagnostic.ts', import.meta.url), 'utf8'),
    readFile(new URL('../../src/features/diagnostic/pne2026DiagnosticLoader.js', import.meta.url), 'utf8'),
    readFile(new URL('../../src/components/DiagnosticPanel.jsx', import.meta.url), 'utf8'),
    readFile(new URL('../../src/features/diagnostic/diagnosticPresentation.js', import.meta.url), 'utf8'),
  ])
  assert.match(hookSource, /Pne2026DiagnosticLoaderResult/)
  assert.doesNotMatch(hookSource, /VITE_PNE_DIAGNOSTIC_SOURCE|configuredSource|allowDual/)
  assert.match(loaderSource, /createPne2026DiagnosticLoader/)
  assert.match(loaderSource, /diagnosticSource: 'v3'/)
  assert.doesNotMatch(loaderSource, /v2-fallback|loadV2|allowDual/)
  assert.match(panelSource, /pne2026PublicDiagnostic/)
  assert.doesNotMatch(panelSource, /pne2026PublicDiagnosticV2/)
  assert.doesNotMatch(panelSource, /PublicDiagnosticV3|diagnostic-v3/)
  assert.doesNotMatch(presentationSource, /PublicDiagnosticV3|diagnostic-v3/)
})
