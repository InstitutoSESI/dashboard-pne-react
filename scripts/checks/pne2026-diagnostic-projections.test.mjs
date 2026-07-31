import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { spawnSync } from 'node:child_process'
import test from 'node:test'

import {
  FORBIDDEN_PRESENTATION_FIELDS,
  projectDiagnosticCompatibilityArtifacts,
  projectPublicIndicatorCatalog,
  renderPneContractDocumentation,
  validateDiagnosticPresentationPolicy,
} from '../generate-diagnostic-catalog.mjs'

const root = resolve(import.meta.dirname, '../..')
const paths = {
  contract: resolve(root, 'contracts/pne2026-goal-indicator-contract.json'),
  policy: resolve(root, 'contracts/pne2026-diagnostic-presentation-policy.json'),
  indicator: resolve(root, 'src/data/diagnostic/indicatorCatalog.json'),
  publicIndicator: resolve(root, 'public/data/indicadores.json'),
  documentation: resolve(root, 'docs/generated/PNE_2026_CONTRACT.md'),
  presentation: resolve(
    root,
    'data_pipeline/src/data/pne2026_diagnostic_presentation_v2.json',
  ),
}
const readJson = (path) => JSON.parse(readFileSync(path, 'utf8'))
const hash = (path) => createHash('sha256').update(readFileSync(path)).digest('hex')

test('presentation policy is editorial, complete, and cannot reactivate relations', () => {
  const contract = readJson(paths.contract)
  const policy = readJson(paths.policy)
  assert.equal(validateDiagnosticPresentationPolicy(policy, contract), policy)
  assert.equal(policy.themes.length, 10)
  assert.equal(policy.relations.length, 51)
  assert.equal(
    policy.relations.filter((entry) => entry.summaryPriority === 'essential').length,
    13,
  )
  assert.equal(
    policy.relations.filter((entry) => entry.summaryPriority === 'standard').length,
    38,
  )
  assert.deepEqual(
    new Set(policy.relations.map((entry) => entry.summaryPriority)),
    new Set(['essential', 'standard']),
  )
  for (const entry of policy.relations) {
    assert.deepEqual(
      Object.keys(entry).filter((key) => FORBIDDEN_PRESENTATION_FIELDS.has(key)),
      [],
    )
    const relation = contract.relations.find(
      (candidate) => candidate.relationId === entry.relationId,
    )
    assert.equal(relation.includeInDiagnostic, true)
    assert.notEqual(relation.mode, 'hidden')
  }

  const reactivated = structuredClone(policy)
  reactivated.relations.push({
    relationId: 'relation.17.b.rendimento_magisterio',
    themeId: 'profissionais_educacao_v2',
    displayOrder: 99,
    summaryPriority: 'standard',
    displayGroup: 'details',
  })
  assert.throws(
    () => validateDiagnosticPresentationPolicy(reactivated, contract),
    /hidden|não é elegível/,
  )
})

test('V3 catalog projection is deterministic while the V2 artifact stays frozen', () => {
  const inputs = {
    contract: readJson(paths.contract),
    policy: readJson(paths.policy),
    indicatorCatalog: readJson(paths.indicator),
    presentationCatalog: readJson(paths.presentation),
  }
  const first = projectDiagnosticCompatibilityArtifacts(inputs)
  const second = projectDiagnosticCompatibilityArtifacts(structuredClone(inputs))
  assert.deepEqual(first, second)
  assert.deepEqual(first.indicatorCatalog, inputs.indicatorCatalog)
  assert.notDeepEqual(first.presentationCatalog, inputs.presentationCatalog)
})

test('public catalog and documentation are deterministic contract projections', () => {
  const contract = readJson(paths.contract)
  const publicIndicator = readJson(paths.publicIndicator)
  const projected = projectPublicIndicatorCatalog(publicIndicator, contract)
  assert.deepEqual(projected, publicIndicator)

  const items = projected.cycles.pne_2026_2036.categories
    .flatMap((category) => category.items)
  const byId = Object.fromEntries(items.map((item) => [item.key, item]))
  assert.equal(byId.pre_escola.meta_label, 'Meta PNE 2028')
  assert.equal(byId.basico_6_17.meta_label, 'Meta PNE 2029')
  assert.equal(byId.basico_15_17.meta_label, 'Referência de acompanhamento')
  assert.equal(byId.basico_15_17.reference.kind, 'monitoring')
  assert.equal(byId.basico_15_17.reference.value, 100)
  assert.equal(
    byId.creche.formula,
    '100 * sum(mat_basico_0_3) / denominator_aggregate(pop_0_3)',
  )

  const documentation = readFileSync(paths.documentation, 'utf8')
  assert.equal(documentation, `${renderPneContractDocumentation(contract)}\n`)
  assert.match(documentation, /POPULATION_PROJECTION_SOURCE_PATH/)
  assert.match(documentation, /sem prazo legal/)
})

test('--check is read-only and detects stale contract or policy projections', () => {
  const before = {
    indicator: hash(paths.indicator),
    presentation: hash(paths.presentation),
    publicIndicator: hash(paths.publicIndicator),
    documentation: hash(paths.documentation),
  }
  const check = spawnSync(
    process.execPath,
    ['scripts/generate-diagnostic-catalog.mjs', '--check'],
    { cwd: root, encoding: 'utf8' },
  )
  assert.equal(check.status, 0, check.stderr)
  assert.deepEqual(
    {
      indicator: hash(paths.indicator),
      presentation: hash(paths.presentation),
      publicIndicator: hash(paths.publicIndicator),
      documentation: hash(paths.documentation),
    },
    before,
  )

  const inputs = {
    contract: readJson(paths.contract),
    policy: readJson(paths.policy),
    indicatorCatalog: readJson(paths.indicator),
    presentationCatalog: readJson(paths.presentation),
  }
  const changed = structuredClone(inputs)
  changed.contract.indicators.creche.publicTitle = 'Título canônico alterado'
  const projected = projectDiagnosticCompatibilityArtifacts(changed)
  assert.notDeepEqual(projected.presentationCatalog, inputs.presentationCatalog)
  assert.notDeepEqual(
    projectPublicIndicatorCatalog(
      readJson(paths.publicIndicator),
      changed.contract,
    ),
    readJson(paths.publicIndicator),
  )
  assert.notEqual(
    `${renderPneContractDocumentation(changed.contract)}\n`,
    readFileSync(paths.documentation, 'utf8'),
  )
})
