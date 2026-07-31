import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { spawnSync } from 'node:child_process'
import test from 'node:test'

import {
  PNE_2026_GOAL_INDICATOR_CONTRACT,
  PNE_2026_RELATIONSHIP_MODES,
  canPne2026RelationEnterCycleSummary,
  getPne2026FormulaForIndicator,
  getPne2026IndicatorReferenceProfile,
  getPne2026Relation,
  getPne2026RelationContext,
  reconcilePne2026MunicipalResult,
  resolvePne2026ComparisonReference,
  resolvePne2026LegalReference,
  stableStringifyPne2026GoalIndicatorContract,
  validatePne2026GoalIndicatorContract,
} from '../../src/data/pne2026GoalIndicatorContract.js'
import { PNE_2026_GOAL_TEXTS } from '../../src/data/pne2026GoalTexts.js'
import { PNE_2026_INDICATOR_GOAL_REFS } from '../../src/data/pne2026IndicatorGoalRefs.js'
import {
  PNE_2026_LEGAL_GOAL_INDICATOR_MAP,
  getPne2026PublicLegalGoalRelations,
} from '../../src/data/pne2026LegalGoalIndicatorMap.js'

const repositoryRoot = resolve(import.meta.dirname, '../..')
const diagnosticCatalog = JSON.parse(
  readFileSync(
    resolve(
      repositoryRoot,
      'data_pipeline/src/data/pne2026_diagnostic_presentation_v2.json',
    ),
    'utf8',
  ),
)
const indicatorCatalog = JSON.parse(
  readFileSync(
    resolve(repositoryRoot, 'src/data/diagnostic/indicatorCatalog.json'),
    'utf8',
  ),
)

function legacyRelations() {
  return PNE_2026_LEGAL_GOAL_INDICATOR_MAP.flatMap((goal) =>
    goal.relatedIndicators.map((relation) => ({
      ...relation,
      goalId: goal.legalGoalId,
    })),
  )
}

test('canonical contract validates and has stable cardinalities and modes', () => {
  assert.equal(
    validatePne2026GoalIndicatorContract(PNE_2026_GOAL_INDICATOR_CONTRACT),
    PNE_2026_GOAL_INDICATOR_CONTRACT,
  )
  assert.equal(Object.keys(PNE_2026_GOAL_INDICATOR_CONTRACT.goals).length, 73)
  assert.equal(Object.keys(PNE_2026_GOAL_INDICATOR_CONTRACT.indicators).length, 59)
  assert.equal(PNE_2026_GOAL_INDICATOR_CONTRACT.relations.length, 59)
  assert.equal(Object.keys(PNE_2026_GOAL_INDICATOR_CONTRACT.sources).length, 17)
  assert.equal(Object.keys(PNE_2026_GOAL_INDICATOR_CONTRACT.formulas).length, 59)
  assert.equal(PNE_2026_GOAL_INDICATOR_CONTRACT.contractVersion, '1.9.0')

  const modes = Object.groupBy(
    PNE_2026_GOAL_INDICATOR_CONTRACT.relations,
    (relation) => relation.mode,
  )
  assert.equal(modes.progress.length, 27)
  assert.equal(modes.tracking.length, 15)
  assert.equal(modes.complementary.length, 15)
  assert.equal(modes.hidden.length, 2)

  for (const relation of [
    ...modes[PNE_2026_RELATIONSHIP_MODES.COMPLEMENTARY],
    ...modes[PNE_2026_RELATIONSHIP_MODES.HIDDEN],
  ]) {
    assert.equal(relation.canDistance, false)
    assert.equal(relation.canStatus, false)
    assert.equal(relation.canProjection, false)
    assert.equal(relation.referenceId, null)
  }
  for (const relation of modes[PNE_2026_RELATIONSHIP_MODES.HIDDEN]) {
    assert.equal(relation.includeInDiagnostic, false)
    assert.equal(relation.includeInReferenceSummary, false)
  }
  for (const relation of modes[PNE_2026_RELATIONSHIP_MODES.TRACKING]) {
    assert.equal(relation.referenceKind, 'monitoring')
    assert.equal(relation.canDistance, true)
    assert.equal(relation.canStatus, true)
    assert.equal(relation.canProjection, false)
    assert.equal(relation.includeInCycleSummary, true)
    assert.equal(relation.includeInLegalSummary, false)
    const reference = resolvePne2026ComparisonReference(
      relation.goalId,
      relation.indicatorId,
    )
    assert.equal(reference.referenceId, relation.comparisonReferenceId)
  }

  const trackingAttendance = getPne2026Relation('4.a', 'basico_15_17')
  assert.equal(trackingAttendance.mode, PNE_2026_RELATIONSHIP_MODES.TRACKING)
  assert.equal(trackingAttendance.referenceId, null)
  assert.equal(trackingAttendance.includeInDiagnostic, true)
  assert.equal(trackingAttendance.includeInCycleGoalRefs, true)
  assert.equal(
    PNE_2026_GOAL_INDICATOR_CONTRACT.goals['4.a'].legalReferences.some(
      (reference) => reference.referenceId === 'reference.4.a.basico_15_17',
    ),
    false,
  )
  assert.equal(getPne2026Relation('4.a', 'basico_6_17').mode, 'progress')
})

test('attendance references, formulas, and population lineage are contract-derived', () => {
  const expectedReferences = {
    creche: { kind: 'legal', value: 60, year: 2036 },
    pre_escola: { kind: 'legal', value: 100, year: 2028 },
    basico_6_17: { kind: 'legal', value: 100, year: 2029 },
    basico_15_17: { kind: 'monitoring', value: 100, year: null },
  }
  for (const [indicatorId, expected] of Object.entries(expectedReferences)) {
    const reference = getPne2026IndicatorReferenceProfile(indicatorId, 2025)
    assert.equal(reference.kind, expected.kind)
    assert.equal(reference.value, expected.value)
    assert.equal(reference.year, expected.year)

    const formula = getPne2026FormulaForIndicator(indicatorId)
    assert.equal(formula.runtime.strategy, 'ratio_of_counts')
    assert.ok(formula.runtime.numeratorField)
    assert.ok(formula.runtime.denominatorField)
    assert.equal(
      formula.catalogProjection.displayPolicy,
      'cap_at_100_preserve_raw_for_audit',
    )
  }

  const historical = PNE_2026_GOAL_INDICATOR_CONTRACT.sources
    .municipal_age_population_panel
  assert.equal(historical.organization, 'Ministério da Saúde (MS) / DATASUS')
  assert.match(historical.officialUrl, /^https:\/\/datasus\.saude\.gov\.br\//)
  assert.equal(historical.lineage.pathConfiguration, 'SESI_DB_DIR')
  assert.match(historical.lineage.latestSourceSha256, /^[a-f0-9]{64}$/)

  const projection = PNE_2026_GOAL_INDICATOR_CONTRACT.sources
    .ibge_population_projection_2024
  assert.match(projection.officialUrl, /^https:\/\/www\.ibge\.gov\.br\//)
  assert.equal(
    projection.lineage.pathConfiguration,
    'POPULATION_PROJECTION_SOURCE_PATH',
  )
  assert.match(projection.lineage.sourceSha256, /^[a-f0-9]{64}$/)

  const serialized = JSON.stringify(PNE_2026_GOAL_INDICATOR_CONTRACT)
  assert.doesNotMatch(serialized, /[A-Za-z]:[\\/]+Users[\\/]/)
})

test('73 legal goal texts and canonical relations remain in parity', () => {
  assert.equal(PNE_2026_LEGAL_GOAL_INDICATOR_MAP.length, 73)
  assert.equal(legacyRelations().length, 59)
  assert.deepEqual(
    PNE_2026_LEGAL_GOAL_INDICATOR_MAP.map((goal) => goal.legalGoalId),
    Object.values(PNE_2026_GOAL_INDICATOR_CONTRACT.goals)
      .toSorted((left, right) => left.legalOrder - right.legalOrder)
      .map((goal) => goal.goalId),
  )

  for (const goal of PNE_2026_LEGAL_GOAL_INDICATOR_MAP) {
    const canonical = PNE_2026_GOAL_INDICATOR_CONTRACT.goals[goal.legalGoalId]
    const legacyText = PNE_2026_GOAL_TEXTS[goal.legalGoalId]
    assert.ok(canonical)
    assert.equal(canonical.objectiveId, goal.objectiveId)
    assert.equal(canonical.publicTitle, legacyText.shortTitle)
    assert.equal(canonical.legalText, legacyText.originalText)
    assert.equal(canonical.legalText, legacyText.displayText)
    assert.equal(canonical.dashboardText ?? undefined, legacyText.dashboardText)
    assert.equal(canonical.legalText, goal.legalText)
  }

  for (const legacy of legacyRelations()) {
    const canonical = getPne2026Relation(legacy.goalId, legacy.indicatorId)
    assert.ok(canonical)
    if (new Set([
      'relation.11.b.fundamental_concluido_18_mais',
      'relation.11.b.fundamental_concluido_15_mais',
      'relation.12.a.medio_tecnico_articulado_percentual',
      'relation.12.a.medio_tecnico_participacao_publica',
      'relation.12.b.subsequente_expansao',
      'relation.3.a.alfabetizacao',
      'relation.9.d.educacao_indigena_cobertura_estimada_4_17',
      'relation.10.b.aee_oferta_escolas_elegiveis',
    ]).has(canonical.relationId)) continue
    assert.equal(canonical.mode, legacy.monitoringMode)
    assert.equal(canonical.legacyCoverage, legacy.coverage)
    assert.equal(canonical.internalNote, legacy.relationNote)
    assert.equal(canonical.hasMunicipalResult, legacy.hasMunicipalResult)
    assert.equal(canonical.canDistance, legacy.hasDistance)
    assert.equal(canonical.canStatus, legacy.canStatus)
    assert.equal(canonical.canProjection, legacy.hasProjection2036)
    assert.equal(canonical.includeInCycleGoalRefs, legacy.includeInCycleGoalRefs)
    assert.equal(canonical.referenceDimension, legacy.referenceDimension)
    assert.equal(
      canonical.publicLabelOverride
        ?? PNE_2026_GOAL_INDICATOR_CONTRACT.indicators[canonical.indicatorId].publicTitle,
      legacy.publicName,
    )
    assert.equal(
      canonical.publicDescriptionOverride
        ?? PNE_2026_GOAL_INDICATOR_CONTRACT.indicators[canonical.indicatorId].publicDescription,
      legacy.publicDescription,
    )
    if (canonical.referenceId) {
      const context = getPne2026RelationContext(
        canonical.goalId,
        canonical.indicatorId,
        PNE_2026_GOAL_INDICATOR_CONTRACT.cycle.endYear,
      )
      assert.equal(legacy.deadline, context.legalReference.targetYear)
      assert.equal(legacy.direction, context.legalReference.milestone.direction)
      assert.equal(legacy.unit, context.indicator.unit)
      assert.equal(legacy.referenceId, context.legalReference.referenceId)
    }
  }
})

test('cycle goal references expose the 42 comparable relations without conflating the 50 contract flags', () => {
  const contractGoalRefRelations = PNE_2026_GOAL_INDICATOR_CONTRACT.relations
    .filter((relation) => relation.includeInCycleGoalRefs)
  const comparableRelations = contractGoalRefRelations.filter((relation) => (
    [
      PNE_2026_RELATIONSHIP_MODES.PROGRESS,
      PNE_2026_RELATIONSHIP_MODES.TRACKING,
    ].includes(relation.mode)
    && canPne2026RelationEnterCycleSummary(relation)
  ))
  assert.equal(contractGoalRefRelations.length, 50)
  assert.equal(comparableRelations.length, 42)
  assert.equal(Object.keys(PNE_2026_INDICATOR_GOAL_REFS).length, comparableRelations.length)
  assert.deepEqual(
    PNE_2026_INDICATOR_GOAL_REFS,
    Object.fromEntries(
      comparableRelations.map((relation) => [relation.indicatorId, relation.goalId]),
    ),
  )
  for (const [indicatorId, goalId] of Object.entries(PNE_2026_INDICATOR_GOAL_REFS)) {
    assert.ok(getPne2026Relation(goalId, indicatorId))
  }
  assert.equal(PNE_2026_INDICATOR_GOAL_REFS.internet, undefined)
  assert.equal(PNE_2026_INDICATOR_GOAL_REFS.alfabetizacao, '3.a')
})

test('compatibility adapters are contract-derived and the public selector excludes hidden relations', () => {
  const goalTextsSource = readFileSync(
    resolve(repositoryRoot, 'src/data/pne2026GoalTexts.js'),
    'utf8',
  )
  const legalMapSource = readFileSync(
    resolve(repositoryRoot, 'src/data/pne2026LegalGoalIndicatorMap.js'),
    'utf8',
  )
  const goalRefsSource = readFileSync(
    resolve(repositoryRoot, 'src/data/pne2026IndicatorGoalRefs.js'),
    'utf8',
  )

  assert.match(goalTextsSource, /PNE_2026_GOAL_INDICATOR_CONTRACT/)
  assert.match(legalMapSource, /getPne2026RelationsForGoal/)
  assert.match(goalRefsSource, /includeInCycleGoalRefs/)
  assert.match(goalRefsSource, /canPne2026RelationEnterCycleSummary/)
  assert.doesNotMatch(goalTextsSource, /['"]1\.a['"]\s*:/)
  assert.doesNotMatch(legalMapSource, /indicatorId:\s*['"]creche['"]/)
  assert.doesNotMatch(goalRefsSource, /creche:\s*['"]1\.a['"]/)

  const hiddenGoalRelations = getPne2026PublicLegalGoalRelations('17.b')
  assert.equal(hiddenGoalRelations.length, 0)
  assert.equal(getPne2026PublicLegalGoalRelations('4.b').length, 1)

  const expectedStageLabels = {
    '4.b': 'Estudantes matriculados sem distorção — anos iniciais',
    '4.c': 'Estudantes matriculados sem distorção — anos finais',
    '4.d': 'Estudantes matriculados sem distorção — Ensino Médio',
  }
  for (const [goalId, expectedLabel] of Object.entries(expectedStageLabels)) {
    assert.equal(
      getPne2026PublicLegalGoalRelations(goalId)[0].publicName,
      expectedLabel,
    )
  }

  const publicGoal12a = getPne2026PublicLegalGoalRelations('12.a')
  assert.deepEqual(
    publicGoal12a.map((relation) => relation.indicatorId),
    [
      'medio_tecnico_articulado_percentual',
      'medio_tecnico_participacao_publica',
    ],
  )
  assert.equal(
    publicGoal12a[0].publicName,
    'Matrículas técnicas integradas ou concomitantes em relação às matrículas do Ensino Médio',
  )
  assert.deepEqual(
    getPne2026PublicLegalGoalRelations('12.b').map((relation) => relation.indicatorId),
    ['subsequente_expansao'],
  )
})

test('diagnostic compatibility catalog has 34 pairs and 31 public relations', () => {
  assert.equal(diagnosticCatalog.results.length, 34)
  const visible = []
  const frozenMethodologyRelations = new Set([
    'relation.11.b.fundamental_concluido_18_mais',
    'relation.11.b.fundamental_concluido_15_mais',
    'relation.12.a.medio_tecnico_articulado_percentual',
    'relation.12.a.medio_tecnico_participacao_publica',
    'relation.12.b.subsequente_expansao',
    'relation.3.a.alfabetizacao',
    'relation.9.d.educacao_indigena_cobertura_estimada_4_17',
    'relation.10.b.aee_oferta_escolas_elegiveis',
  ])
  for (const definition of diagnosticCatalog.results) {
    const relation = getPne2026Relation(
      definition.goalId,
      definition.indicatorId,
    )
    assert.ok(relation)
    if (
      !frozenMethodologyRelations.has(relation.relationId)
      && relation.mode !== PNE_2026_RELATIONSHIP_MODES.TRACKING
    ) {
      assert.equal(definition.monitoringMode ?? 'progress', relation.mode)
    }
    if ((definition.monitoringMode ?? 'progress') !== 'hidden') visible.push(relation)
    if (
      relation.publicLabelOverride
      && !frozenMethodologyRelations.has(relation.relationId)
      && relation.mode !== PNE_2026_RELATIONSHIP_MODES.TRACKING
    ) {
      assert.equal(definition.publicName, relation.publicLabelOverride)
    }
  }
  assert.equal(visible.length, 31)
  assert.equal(
    visible.filter((relation) => relation.mode === 'complementary').length,
    2,
  )
})

test('the frozen V2 registry recognizes canonical indicators except the V3-only macro package', () => {
  const indicatorsById = Object.fromEntries(
    indicatorCatalog.indicators.map((indicator) => [
      indicator.indicatorId,
      indicator,
    ]),
  )
  const v3OnlyIndicatorIds = new Set([
    'eja_atendimento_18_mais',
    'graduacao_frequencia_18_24',
    'superior_completo_25_34',
    'taxa_bruta_graduacao',
    'docentes_tempo_integral_ies',
    'docentes_tempo_integral_universidades',
    'docentes_tempo_integral_centros_universitarios',
    'docentes_tempo_integral_faculdades',
    'munic_planos_carreira_declarados',
    'munic_forum_educacao_declarado',
    'capes_titulados_oferta_local',
    'cpc_cursos_oferta_local',
    'enade_licenciaturas_oferta_local',
  ])
  for (const indicator of Object.values(PNE_2026_GOAL_INDICATOR_CONTRACT.indicators)) {
    if (v3OnlyIndicatorIds.has(indicator.indicatorId)) {
      assert.equal(indicatorsById[indicator.indicatorId], undefined)
      continue
    }
    const registered = indicatorsById[indicator.indicatorId]
    assert.ok(registered, indicator.indicatorId)
    assert.equal(registered.unit, indicator.unit)
    assert.deepEqual(registered.sourceIds, indicator.sourceIds)
  }
})

test('legal reference resolution preserves distinct dimensions at the same year', () => {
  const direct = resolvePne2026LegalReference('1.c', 'pre_escola', 2027)
  assert.equal(direct.targetYear, 2028)
  assert.equal(direct.milestone.value, 100)

  const multidimensional = resolvePne2026LegalReference(
    '5.a',
    'saeb_matematica_anos_iniciais',
    2030,
  )
  assert.equal(multidimensional.targetYear, 2031)
  assert.deepEqual(
    multidimensional.milestonesAtYear.map((item) => item.dimension),
    ['basic_or_higher', 'adequate_or_higher'],
  )
  assert.equal(multidimensional.milestone, undefined)

  const relationContext = getPne2026RelationContext(
    '5.a',
    'saeb_matematica_anos_iniciais',
    2030,
  )
  assert.equal(relationContext.relation.referenceDimension, 'adequate_or_higher')
  assert.equal(relationContext.legalReference.milestone.dimension, 'adequate_or_higher')
  assert.equal(relationContext.legalReference.milestonesAtYear.length, 1)
})

test('municipal reconciliation reports divergence without allowing local policy overrides', () => {
  const context = getPne2026RelationContext('1.a', 'creche', 2026)
  const milestone = context.legalReference.milestone
  const compatible = {
    atingida: false,
    direction: milestone.direction,
    distance: -1,
    end_year: 2026,
    end_value: milestone.value - 1,
    meta: milestone.value,
    meta_label: `Meta ${milestone.year}`,
    tracks_goal: true,
  }

  assert.deepEqual(
    reconcilePne2026MunicipalResult({
      goalId: '1.a',
      indicatorId: 'creche',
      result: compatible,
      strict: true,
    }).issues,
    [],
  )

  const incompatible = {
    ...compatible,
    meta: milestone.value + 1,
    monitoring_mode: PNE_2026_RELATIONSHIP_MODES.COMPLEMENTARY,
    tracks_goal: false,
  }
  const reconciled = reconcilePne2026MunicipalResult({
    goalId: '1.a',
    indicatorId: 'creche',
    result: incompatible,
  })
  assert.equal(reconciled.context.relation.mode, PNE_2026_RELATIONSHIP_MODES.PROGRESS)
  assert.ok(reconciled.issues.length >= 3)
  assert.equal(reconciled.result.monitoring_mode, PNE_2026_RELATIONSHIP_MODES.PROGRESS)
  assert.equal(reconciled.result.meta, milestone.value)
  assert.equal(reconciled.result.direction, milestone.direction)
  assert.equal(reconciled.result.deadline, milestone.year)
  assert.equal(reconciled.result.tracks_goal, true)
  assert.throws(
    () => reconcilePne2026MunicipalResult({
      goalId: '1.a',
      indicatorId: 'creche',
      result: incompatible,
      strict: true,
    }),
    /Resultado municipal incompatível/,
  )
})

test('JavaScript and Python normalize the same version, counts, capabilities, and SHA-256', () => {
  const javascriptHash = createHash('sha256')
    .update(stableStringifyPne2026GoalIndicatorContract())
    .digest('hex')
  const python = spawnSync(
    process.env.PYTHON ?? 'python',
    [
      '-c',
      [
        'import json',
        'from src.pne.goal_indicator_contract import CONTRACT, contract_hash',
        "relations=[{key:item[key] for key in ('relationId','canDistance','canStatus','canProjection','includeInCycleGoalRefs','includeInDiagnostic','includeInReferenceSummary','referenceDimension')} for item in CONTRACT['relations']]",
        "print(json.dumps({'version':CONTRACT['contractVersion'],'goals':len(CONTRACT['goals']),'indicators':len(CONTRACT['indicators']),'relations':len(relations),'capabilities':relations,'hash':contract_hash()},separators=(',',':')))",
      ].join(';'),
    ],
    {
      cwd: repositoryRoot,
      encoding: 'utf8',
      env: {
        ...process.env,
        PYTHONDONTWRITEBYTECODE: '1',
        PYTHONPATH: resolve(repositoryRoot, 'data_pipeline'),
      },
    },
  )

  assert.equal(python.status, 0, python.stderr)
  const pythonParity = JSON.parse(python.stdout)
  assert.equal(pythonParity.version, PNE_2026_GOAL_INDICATOR_CONTRACT.contractVersion)
  assert.equal(pythonParity.goals, Object.keys(PNE_2026_GOAL_INDICATOR_CONTRACT.goals).length)
  assert.equal(
    pythonParity.indicators,
    Object.keys(PNE_2026_GOAL_INDICATOR_CONTRACT.indicators).length,
  )
  assert.equal(pythonParity.relations, PNE_2026_GOAL_INDICATOR_CONTRACT.relations.length)
  assert.deepEqual(
    pythonParity.capabilities,
    PNE_2026_GOAL_INDICATOR_CONTRACT.relations.map((relation) =>
      Object.fromEntries(
        [
          'relationId',
          'canDistance',
          'canStatus',
          'canProjection',
          'includeInCycleGoalRefs',
          'includeInDiagnostic',
          'includeInReferenceSummary',
          'referenceDimension',
        ].map((key) => [key, relation[key]]),
      )),
  )
  assert.equal(pythonParity.hash, javascriptHash)
})
