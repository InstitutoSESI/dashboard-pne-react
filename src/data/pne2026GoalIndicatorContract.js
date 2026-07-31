import contract from '../../contracts/pne2026-goal-indicator-contract.json' with { type: 'json' }

export const PNE_2026_RELATIONSHIP_MODES = Object.freeze({
  PROGRESS: 'progress',
  TRACKING: 'tracking',
  COMPLEMENTARY: 'complementary',
  HIDDEN: 'hidden',
})

const VALID_MODES = new Set(Object.values(PNE_2026_RELATIONSHIP_MODES))
const COMPARABLE_MODES = new Set([
  PNE_2026_RELATIONSHIP_MODES.PROGRESS,
  PNE_2026_RELATIONSHIP_MODES.TRACKING,
])
const CLASSIFYING_CAPABILITIES = ['canDistance', 'canStatus', 'canProjection']
const PUBLIC_CAPABILITIES = ['includeInDiagnostic', 'includeInReferenceSummary']
const RELATION_ELIGIBILITY_FLAGS = ['includeInCycleGoalRefs']
const ATTENDANCE_RUNTIME_FORMULA_IDS = new Set([
  'formula.creche',
  'formula.pre_escola',
  'formula.basico_6_17',
  'formula.basico_15_17',
  'formula.basico_integral',
])
const ATTENDANCE_PROJECTION_FORMULA_IDS = new Set([
  'formula.creche',
  'formula.pre_escola',
  'formula.basico_6_17',
  'formula.basico_15_17',
])
const ATTENDANCE_NUMERATOR_MODELS = new Set([
  'last_observation_persistence',
  'state_aggregate_damped_holt',
  'municipal_state_shrunk_theil_sen_log',
])

function invariant(condition, message) {
  if (!condition) {
    throw new Error(`Contrato PNE 2026–2036 inválido: ${message}`)
  }
}

function entriesOf(collection, label) {
  invariant(collection && typeof collection === 'object' && !Array.isArray(collection), `${label} deve ser um objeto`)
  return Object.entries(collection)
}

function validateKeyedIds(collection, label, idField) {
  for (const [key, value] of entriesOf(collection, label)) {
    invariant(value && typeof value === 'object', `${label}.${key} deve ser um objeto`)
    invariant(value[idField] === key, `${label}.${key}.${idField} deve coincidir com a chave`)
  }
}

function validateRelations(relations) {
  invariant(Array.isArray(relations), 'relations deve ser uma lista ordenada')
  const relationIds = new Set()
  for (const relation of relations) {
    invariant(relation && typeof relation === 'object', 'cada relação deve ser um objeto')
    invariant(typeof relation.relationId === 'string', 'cada relação deve declarar relationId')
    invariant(!relationIds.has(relation.relationId), `relationId duplicado: ${relation.relationId}`)
    relationIds.add(relation.relationId)
  }
}

export function validatePne2026GoalIndicatorContract(candidate = contract) {
  invariant(candidate?.schemaVersion === 'pne2026-goal-indicator-contract-v1', 'schemaVersion não reconhecida')
  invariant(typeof candidate.contractVersion === 'string' && candidate.contractVersion.length > 0, 'contractVersion ausente')
  invariant(candidate.cycle?.cycleId === 'pne_2026_2036', 'cycle.cycleId deve identificar o PNE 2026–2036')
  invariant(candidate.cycle?.startYear === 2026, 'cycle.startYear deve ser 2026')
  invariant(candidate.cycle?.endYear === 2036, 'cycle.endYear deve ser 2036')

  validateKeyedIds(candidate.goals, 'goals', 'goalId')
  validateKeyedIds(candidate.indicators, 'indicators', 'indicatorId')
  validateRelations(candidate.relations)
  validateKeyedIds(candidate.sources, 'sources', 'sourceId')
  validateKeyedIds(candidate.formulas, 'formulas', 'formulaId')
  validateKeyedIds(candidate.valuePolicies, 'valuePolicies', 'valuePolicyId')
  validateKeyedIds(candidate.missingPolicies, 'missingPolicies', 'missingPolicyId')
  validateKeyedIds(candidate.projectionPolicies, 'projectionPolicies', 'projectionPolicyId')
  validateKeyedIds(candidate.monitoringReferences, 'monitoringReferences', 'referenceId')

  const attendanceProjectionPolicy = candidate.projectionPolicies
    .attendance_backtested_hybrid_minimum_five_consecutive ?? {}
  invariant(
    attendanceProjectionPolicy.selectionMetric
      === '100_abs_predicted_minus_observed_numerator_over_observed_target_population',
    'política de projeção deve declarar a métrica bruta de seleção',
  )
  invariant(
    attendanceProjectionPolicy.selectionAndValidationValuePolicy
      === 'raw_without_display_cap',
    'seleção e validação de projeções devem usar valores brutos',
  )
  invariant(
    attendanceProjectionPolicy.displayPolicy
      === 'cap_at_100_preserve_raw_for_audit',
    'teto de 100% deve ser exclusivamente uma política de apresentação',
  )

  invariant(Object.keys(candidate.goals).length === 73, 'o ciclo deve conter exatamente 73 metas legais')

  const referenceById = new Map()
  for (const [goalId, goal] of entriesOf(candidate.goals, 'goals')) {
    invariant(Number.isInteger(goal.legalOrder) && goal.legalOrder > 0, `goals.${goalId}.legalOrder inválida`)
    invariant(candidate.sources[goal.legalSourceId], `goals.${goalId}.legalSourceId inexistente`)

    const milestoneYears = new Set()
    for (const reference of goal.legalReferences ?? []) {
      invariant(
        typeof reference.referenceId === 'string' && !referenceById.has(reference.referenceId),
        `referência legal duplicada em ${goalId}`,
      )
      invariant(Array.isArray(reference.milestones) && reference.milestones.length > 0, `${reference.referenceId} sem marcos`)
      for (const milestone of reference.milestones) {
        const milestoneKey = `${reference.referenceId}:${milestone.year}:${milestone.dimension ?? 'overall'}`
        invariant(Number.isInteger(milestone.year), `${milestoneKey} tem ano inválido`)
        invariant(!milestoneYears.has(milestoneKey), `${milestoneKey} está duplicado`)
        invariant(milestone.unit === reference.unit, `${milestoneKey} tem unidade incompatível`)
        milestoneYears.add(milestoneKey)
      }
      referenceById.set(reference.referenceId, { goalId, reference })
    }
  }

  for (const [indicatorId, indicator] of entriesOf(candidate.indicators, 'indicators')) {
    invariant(candidate.formulas[indicator.formulaId], `indicators.${indicatorId}.formulaId inexistente`)
    invariant(candidate.valuePolicies[indicator.valuePolicyId], `indicators.${indicatorId}.valuePolicyId inexistente`)
    invariant(candidate.missingPolicies[indicator.missingPolicyId], `indicators.${indicatorId}.missingPolicyId inexistente`)
    invariant(Array.isArray(indicator.sourceIds) && indicator.sourceIds.length > 0, `indicators.${indicatorId}.sourceIds vazio`)
    for (const sourceId of indicator.sourceIds) {
      invariant(candidate.sources[sourceId], `indicators.${indicatorId} referencia a fonte inexistente ${sourceId}`)
    }
  }

  for (const [formulaId, formula] of entriesOf(candidate.formulas, 'formulas')) {
    invariant(
      typeof formula.implementationKey === 'string' && formula.implementationKey.length > 0,
      `formulas.${formulaId}.implementationKey ausente`,
    )
    invariant(
      ['registered_existing', 'blocked_pending_methodology'].includes(formula.status),
      `formulas.${formulaId}.status não reconhecido`,
    )
    if (formulaId.endsWith('.v2')) {
      for (const field of [
        'description',
        'sourceId',
        'universe',
        'numerator',
        'denominator',
        'zeroPolicy',
        'missingPolicy',
        'negativePolicy',
        'above100Policy',
        'statePolicy',
      ]) {
        invariant(
          typeof formula[field] === 'string' && formula[field].length > 0,
          `formulas.${formulaId}.${field} ausente`,
        )
      }
      invariant(candidate.sources[formula.sourceId], `formulas.${formulaId}.sourceId inexistente`)
      invariant(
        formula.catalogProjection && typeof formula.catalogProjection === 'object',
        `formulas.${formulaId}.catalogProjection ausente`,
      )
    }
    if (ATTENDANCE_RUNTIME_FORMULA_IDS.has(formulaId)) {
      invariant(
        formula.runtime && typeof formula.runtime === 'object',
        `formulas.${formulaId}.runtime ausente`,
      )
      for (const field of [
        'strategy',
        'loaderKey',
        'numeratorField',
        'denominatorField',
        'denominatorAggregation',
      ]) {
        invariant(
          typeof formula.runtime[field] === 'string' && formula.runtime[field].length > 0,
          `formulas.${formulaId}.runtime.${field} ausente`,
        )
      }
      invariant(
        formula.catalogProjection && typeof formula.catalogProjection === 'object',
        `formulas.${formulaId}.catalogProjection ausente`,
      )
      if (ATTENDANCE_PROJECTION_FORMULA_IDS.has(formulaId)) {
        const projection = formula.runtime.projection
        invariant(
          projection && typeof projection === 'object',
          `formulas.${formulaId}.runtime.projection ausente`,
        )
        invariant(
          ATTENDANCE_NUMERATOR_MODELS.has(projection.numeratorModel),
          `formulas.${formulaId}.runtime.projection.numeratorModel inválido`,
        )
        invariant(
          projection.denominatorModel === 'municipal_base_times_rs_age_factor',
          `formulas.${formulaId}.runtime.projection.denominatorModel inválido`,
        )
        invariant(
          projection.minimumComparableObservations === 5,
          `formulas.${formulaId}.runtime.projection.minimumComparableObservations deve ser 5`,
        )
        invariant(
          projection.requiredObservationIntervalYears === 1,
          `formulas.${formulaId}.runtime.projection.requiredObservationIntervalYears deve ser 1`,
        )
        if (projection.numeratorModel === 'municipal_state_shrunk_theil_sen_log') {
          const parameters = projection.parameters
          invariant(
            parameters && typeof parameters === 'object',
            `formulas.${formulaId}.runtime.projection.parameters ausente`,
          )
          invariant(
            parameters.historyStartYear === 2014,
            `formulas.${formulaId}: historyStartYear deve ser 2014`,
          )
          invariant(
            [5, 8].includes(parameters.windowObservations),
            `formulas.${formulaId}: janela inválida`,
          )
          invariant(
            parameters.damping === 0.8,
            `formulas.${formulaId}: damping deve ser 0.8`,
          )
          invariant(
            parameters.shrinkage === 4,
            `formulas.${formulaId}: shrinkage deve ser 4`,
          )
          invariant(
            Array.isArray(parameters.excludedYears)
              && parameters.excludedYears.length === 0,
            `formulas.${formulaId}: excludedYears deve ser vazio`,
          )
          invariant(
            parameters.maximumAbsoluteAnnualLogTrend === 0.15,
            `formulas.${formulaId}: limite de tendência inválido`,
          )
        }
      }
    }
  }

  for (const [sourceId, source] of entriesOf(candidate.sources, 'sources')) {
    invariant(typeof source.kind === 'string' && source.kind.length > 0, `sources.${sourceId}.kind ausente`)
    invariant(
      typeof source.publicTitle === 'string' && source.publicTitle.length > 0,
      `sources.${sourceId}.publicTitle ausente`,
    )
    if (source.lineage != null) {
      invariant(
        source.lineage && typeof source.lineage === 'object' && !Array.isArray(source.lineage),
        `sources.${sourceId}.lineage inválida`,
      )
      invariant(
        typeof source.officialUrl === 'string' && source.officialUrl.length > 0,
        `sources.${sourceId}.officialUrl ausente para fonte com linhagem`,
      )
      const serializedLineage = JSON.stringify(source.lineage)
      invariant(
        !['C:\\\\Users\\\\', 'C:/Users/', '/home/'].some((marker) =>
          serializedLineage.includes(marker)),
        `sources.${sourceId}.lineage contém caminho local absoluto`,
      )
    }
  }

  for (const [referenceId, reference] of entriesOf(
    candidate.monitoringReferences,
    'monitoringReferences',
  )) {
    invariant(candidate.goals[reference.goalId], `monitoringReferences.${referenceId}.goalId inexistente`)
    invariant(reference.referenceKind === 'monitoring', `monitoringReferences.${referenceId}.referenceKind inválido`)
    invariant(
      ['percent', 'index', 'count', 'years'].includes(reference.unit),
      `monitoringReferences.${referenceId}.unit inválida`,
    )
    invariant(Number.isFinite(reference.value), `monitoringReferences.${referenceId}.value inválido`)
    invariant(
      ['at_least', 'at_most'].includes(reference.direction),
      `monitoringReferences.${referenceId}.direction inválida`,
    )
  }

  const relationPairs = new Set()
  for (const relation of candidate.relations) {
    const { relationId } = relation
    invariant(candidate.goals[relation.goalId], `${relationId} referencia a meta inexistente ${relation.goalId}`)
    invariant(candidate.indicators[relation.indicatorId], `${relationId} referencia o indicador inexistente ${relation.indicatorId}`)
    invariant(VALID_MODES.has(relation.mode), `${relationId}.mode inválido`)

    const pair = `${relation.goalId}:${relation.indicatorId}`
    invariant(!relationPairs.has(pair), `par meta×indicador duplicado: ${pair}`)
    relationPairs.add(pair)

    for (const capability of [
      ...CLASSIFYING_CAPABILITIES,
      ...PUBLIC_CAPABILITIES,
      ...RELATION_ELIGIBILITY_FLAGS,
    ]) {
      invariant(typeof relation[capability] === 'boolean', `${relationId}.${capability} deve ser booleano`)
    }
    invariant(
      relation.referenceDimension === null || typeof relation.referenceDimension === 'string',
      `${relationId}.referenceDimension deve ser texto ou nulo`,
    )

    if (relation.referenceId !== null) {
      const registered = referenceById.get(relation.referenceId)
      invariant(registered, `${relationId}.referenceId inexistente`)
      invariant(registered.goalId === relation.goalId, `${relationId}.referenceId pertence a outra meta`)
      invariant(
        registered.reference.unit === candidate.indicators[relation.indicatorId].unit,
        `${relationId}.referenceId usa unidade incompatível com o indicador`,
      )
      if (relation.referenceDimension !== null) {
        const referenceYears = new Set(
          registered.reference.milestones.map((milestone) => milestone.year),
        )
        const dimensionYears = new Set(
          registered.reference.milestones
            .filter((milestone) => milestone.dimension === relation.referenceDimension)
            .map((milestone) => milestone.year),
        )
        invariant(
          referenceYears.size === dimensionYears.size
          && [...referenceYears].every((year) => dimensionYears.has(year)),
          `${relationId}.referenceDimension não cobre todos os marcos da referência`,
        )
      }
    } else {
      invariant(
        relation.referenceDimension === null,
        `${relationId}.referenceDimension exige referenceId`,
      )
    }

    for (const field of ['includeInCycleSummary', 'includeInLegalSummary']) {
      if (relation[field] !== undefined) {
        invariant(typeof relation[field] === 'boolean', `${relationId}.${field} deve ser booleano`)
      }
    }

    if (relation.mode === PNE_2026_RELATIONSHIP_MODES.TRACKING) {
      const monitoringReference = candidate.monitoringReferences[relation.comparisonReferenceId]
      invariant(relation.referenceKind === 'monitoring', `${relationId}.referenceKind deve ser monitoring`)
      invariant(monitoringReference, `${relationId}.comparisonReferenceId inexistente`)
      invariant(monitoringReference.goalId === relation.goalId, `${relationId}.comparisonReferenceId pertence a outra meta`)
      invariant(
        monitoringReference.unit === candidate.indicators[relation.indicatorId].unit,
        `${relationId}.comparisonReferenceId usa unidade incompatível`,
      )
      invariant(
        relation.comparisonDirection === monitoringReference.direction,
        `${relationId}.comparisonDirection diverge da referência`,
      )
      invariant(relation.canDistance && relation.canStatus, `${relationId} deve calcular distância e situação`)
      invariant(!relation.canProjection && relation.projectionPolicyId === null, `${relationId} tracking não pode projetar`)
      invariant(relation.includeInCycleSummary === true, `${relationId}.includeInCycleSummary deve ser verdadeiro`)
      invariant(relation.includeInLegalSummary === false, `${relationId}.includeInLegalSummary deve ser falso`)
    }

    if (relation.projectionPolicyId !== null) {
      invariant(candidate.projectionPolicies[relation.projectionPolicyId], `${relationId}.projectionPolicyId inexistente`)
      invariant(relation.canProjection, `${relationId} tem política de projeção sem capacidade de projeção`)
    }

    if (!COMPARABLE_MODES.has(relation.mode)) {
      for (const capability of CLASSIFYING_CAPABILITIES) {
        invariant(!relation[capability], `${relationId}.${capability} deve ser falso no modo ${relation.mode}`)
      }
      invariant(relation.referenceId === null, `${relationId}.referenceId deve ser nulo no modo ${relation.mode}`)
      invariant(relation.referenceDimension === null, `${relationId}.referenceDimension deve ser nulo no modo ${relation.mode}`)
      invariant(
        !relation.includeInReferenceSummary,
        `${relationId}.includeInReferenceSummary deve ser falso no modo ${relation.mode}`,
      )
    }

    if (relation.mode === PNE_2026_RELATIONSHIP_MODES.PROGRESS) {
      invariant(
        relation.includeInLegalSummary === undefined
          || relation.includeInLegalSummary === relation.includeInReferenceSummary,
        `${relationId}.includeInLegalSummary diverge do resumo legal`,
      )
    } else if (relation.includeInLegalSummary !== undefined) {
      invariant(!relation.includeInLegalSummary, `${relationId}.includeInLegalSummary deve ser falso`)
    }

    if (relation.mode === PNE_2026_RELATIONSHIP_MODES.HIDDEN) {
      for (const capability of PUBLIC_CAPABILITIES) {
        invariant(!relation[capability], `${relationId}.${capability} deve ser falso no modo hidden`)
      }
    }
  }

  return candidate
}

validatePne2026GoalIndicatorContract(contract)

export const PNE_2026_GOAL_INDICATOR_CONTRACT = contract
export const PNE_2026_CONTRACT_VERSION = contract.contractVersion

const relationsByPair = new Map()
const relationsByGoal = new Map()
const relationsByIndicator = new Map()

for (const relation of Object.values(contract.relations)) {
  relationsByPair.set(`${relation.goalId}:${relation.indicatorId}`, relation)
  relationsByGoal.set(relation.goalId, [...(relationsByGoal.get(relation.goalId) ?? []), relation])
  relationsByIndicator.set(relation.indicatorId, [...(relationsByIndicator.get(relation.indicatorId) ?? []), relation])
}

export function getPne2026Goal(goalId) {
  return contract.goals[String(goalId ?? '')]
}

export function getPne2026Indicator(indicatorId) {
  return contract.indicators[String(indicatorId ?? '')]
}

export function getPne2026Formula(formulaId) {
  return contract.formulas[String(formulaId ?? '')]
}

export function getPne2026FormulaForIndicator(indicatorId) {
  const indicator = getPne2026Indicator(indicatorId)
  return indicator ? getPne2026Formula(indicator.formulaId) : undefined
}

export function getPne2026Relation(goalId, indicatorId) {
  return relationsByPair.get(`${String(goalId ?? '')}:${String(indicatorId ?? '')}`)
}

export function getPne2026RelationsForGoal(goalId) {
  return relationsByGoal.get(String(goalId ?? '')) ?? []
}

export function getPne2026RelationsForIndicator(indicatorId) {
  return relationsByIndicator.get(String(indicatorId ?? '')) ?? []
}

export function resolvePne2026Relation(goalId, indicatorId) {
  const directRelation = getPne2026Relation(goalId, indicatorId)
  if (directRelation) return directRelation

  const indicatorRelations = getPne2026RelationsForIndicator(indicatorId)
  return indicatorRelations.length === 1 ? indicatorRelations[0] : undefined
}

export function getPne2026PublicRelationsForGoal(goalId) {
  return getPne2026RelationsForGoal(goalId).filter(
    (relation) => relation.mode !== PNE_2026_RELATIONSHIP_MODES.HIDDEN,
  )
}

export function getPne2026RelationCapabilities(goalId, indicatorId) {
  const relation = getPne2026Relation(goalId, indicatorId)
  if (!relation) return undefined

  return {
    canDistance: relation.canDistance,
    canStatus: relation.canStatus,
    canProjection: relation.canProjection,
    includeInCycleGoalRefs: relation.includeInCycleGoalRefs,
    includeInDiagnostic: relation.includeInDiagnostic,
    includeInReferenceSummary: relation.includeInReferenceSummary,
    referenceDimension: relation.referenceDimension,
    referenceKind: getPne2026RelationReferenceKind(relation),
    comparisonReferenceId: getPne2026ComparisonReferenceId(relation),
    comparisonDirection: getPne2026ComparisonDirection(relation),
    includeInCycleSummary: canPne2026RelationEnterCycleSummary(relation),
    includeInLegalSummary: canPne2026RelationEnterLegalSummary(relation),
  }
}

export function getPne2026RelationReferenceKind(relation) {
  if (['legal', 'monitoring'].includes(relation?.referenceKind)) {
    return relation.referenceKind
  }
  return relation?.referenceId ? 'legal' : null
}

export function getPne2026ComparisonReferenceId(relation) {
  return relation?.comparisonReferenceId ?? relation?.referenceId ?? null
}

export function getPne2026ComparisonDirection(relation) {
  if (relation?.comparisonDirection) return relation.comparisonDirection
  if (!relation?.referenceId) return null
  return resolvePne2026LegalReference(
    relation.goalId,
    relation.referenceId,
  )?.milestone?.direction ?? null
}

export function canPne2026RelationEnterCycleSummary(relation) {
  if (typeof relation?.includeInCycleSummary === 'boolean') {
    return relation.includeInCycleSummary
  }
  return Boolean(
    relation?.mode === PNE_2026_RELATIONSHIP_MODES.PROGRESS
    && relation?.includeInCycleGoalRefs
    && relation?.canDistance
    && relation?.canStatus
  )
}

export function canPne2026RelationEnterLegalSummary(relation) {
  if (typeof relation?.includeInLegalSummary === 'boolean') {
    return relation.includeInLegalSummary
  }
  return Boolean(
    relation?.mode === PNE_2026_RELATIONSHIP_MODES.PROGRESS
    && relation?.includeInReferenceSummary
  )
}

export function resolvePne2026LegalReference(goalId, referenceOrIndicatorId, observedYear) {
  const goal = getPne2026Goal(goalId)
  const relation = getPne2026Relation(goalId, referenceOrIndicatorId)
  const referenceId = relation?.referenceId ?? referenceOrIndicatorId
  const reference = goal?.legalReferences?.find((item) => item.referenceId === referenceId)
  if (!reference) return undefined

  const milestones = [...reference.milestones].sort((left, right) => left.year - right.year)
  const numericObservedYear = Number(observedYear)
  const targetYear = Number.isFinite(numericObservedYear)
    ? milestones.find((item) => item.year >= numericObservedYear)?.year ?? milestones.at(-1)?.year
    : milestones.at(-1)?.year
  const milestonesAtYear = milestones.filter((item) => item.year === targetYear)

  return {
    ...reference,
    targetYear,
    milestonesAtYear,
    ...(milestonesAtYear.length === 1 ? { milestone: milestonesAtYear[0] } : {}),
  }
}

export function resolvePne2026ComparisonReference(
  goalId,
  referenceOrIndicatorId,
  observedYear,
) {
  const relation = getPne2026Relation(goalId, referenceOrIndicatorId)
    ?? getPne2026RelationsForGoal(goalId).find(
      (item) => getPne2026ComparisonReferenceId(item) === referenceOrIndicatorId,
    )
  if (!relation) {
    return resolvePne2026LegalReference(goalId, referenceOrIndicatorId, observedYear)
  }
  if (getPne2026RelationReferenceKind(relation) === 'legal') {
    return resolvePne2026LegalReference(
      relation.goalId,
      relation.indicatorId,
      observedYear,
    )
  }
  return contract.monitoringReferences[getPne2026ComparisonReferenceId(relation)]
}

export function getPne2026RelationContext(goalId, indicatorId, observedYear) {
  const relation = resolvePne2026Relation(goalId, indicatorId)
  if (!relation) return undefined
  const comparisonReference = resolvePne2026ComparisonReference(
    relation.goalId,
    relation.indicatorId,
    observedYear,
  )
  const unfilteredReference = getPne2026RelationReferenceKind(relation) === 'legal'
    ? comparisonReference
    : undefined
  const dimensionMilestones = relation.referenceDimension
    ? unfilteredReference?.milestonesAtYear?.filter(
        (milestone) => milestone.dimension === relation.referenceDimension,
      )
    : unfilteredReference?.milestonesAtYear
  let legalReference = unfilteredReference
  if (unfilteredReference && relation.referenceDimension) {
    const referenceWithoutMilestone = { ...unfilteredReference }
    delete referenceWithoutMilestone.milestone
    legalReference = {
      ...referenceWithoutMilestone,
      milestonesAtYear: dimensionMilestones ?? [],
      ...(dimensionMilestones?.length === 1
        ? { milestone: dimensionMilestones[0] }
        : {}),
    }
  }

  return {
    goal: getPne2026Goal(relation.goalId),
    indicator: getPne2026Indicator(relation.indicatorId),
    relation,
    legalReference,
    comparisonReference,
  }
}

export function getPne2026IndicatorReferenceProfile(indicatorId, observedYear) {
  const relations = getPne2026RelationsForIndicator(indicatorId)
  if (relations.length !== 1) return undefined
  const relation = relations[0]
  const context = getPne2026RelationContext(
    relation.goalId,
    relation.indicatorId,
    observedYear,
  )
  const referenceKind = getPne2026RelationReferenceKind(relation)
  const reference = context?.comparisonReference
  if (!reference || !['legal', 'monitoring'].includes(referenceKind)) return undefined

  if (referenceKind === 'legal') {
    const milestone = context.legalReference?.milestone
    if (!milestone) return undefined
    return {
      kind: 'legal',
      label: 'Meta do PNE',
      referenceId: reference.referenceId,
      value: milestone.value,
      year: milestone.year,
      unit: milestone.unit,
      direction: milestone.direction,
      validationStatus: reference.validationStatus,
      milestones: [...reference.milestones],
    }
  }

  return {
    kind: 'monitoring',
    label: 'Referência de acompanhamento',
    referenceId: reference.referenceId,
    value: reference.value,
    year: null,
    unit: reference.unit,
    direction: reference.direction,
    validationStatus: reference.validationStatus,
    milestones: [],
  }
}

function numericValuesDiffer(left, right) {
  const leftNumber = Number(left)
  const rightNumber = Number(right)
  return (
    Number.isFinite(leftNumber) &&
    Number.isFinite(rightNumber) &&
    Math.abs(leftNumber - rightNumber) > 1e-9
  )
}

function canonicalDistanceForResult(result, milestone) {
  const currentValue = Number(result?.end_value)
  const targetValue = Number(milestone?.value)
  if (!Number.isFinite(currentValue) || !Number.isFinite(targetValue)) {
    return null
  }
  return milestone.direction === 'at_most'
    ? targetValue - currentValue
    : currentValue - targetValue
}

function formatCanonicalDistance(distance, unit) {
  if (!Number.isFinite(distance)) return undefined
  const sign = distance > 0 ? '+' : ''
  const formatted = distance.toLocaleString('pt-BR', {
    maximumFractionDigits: unit === 'count' ? 0 : 1,
    minimumFractionDigits: 0,
  })
  if (unit === 'percent') return `${sign}${formatted} p.p.`
  if (unit === 'years') return `${sign}${formatted} anos`
  return `${sign}${formatted}`
}

export function reconcilePne2026MunicipalResult({
  goalId,
  indicatorId,
  result,
  strict = false,
} = {}) {
  const context = getPne2026RelationContext(
    goalId,
    indicatorId,
    result?.end_year,
  )
  if (!context || !result || typeof result !== 'object') {
    return { context, issues: [], result }
  }

  const { comparisonReference, relation } = context
  const issues = []
  const explicitMode = result.monitoringMode ?? result.monitoring_mode
  if (VALID_MODES.has(explicitMode) && explicitMode !== relation.mode) {
    issues.push(`monitoringMode municipal=${explicitMode}; contrato=${relation.mode}`)
  }

  if (relation.canStatus && result.tracks_goal === false) {
    issues.push('tracks_goal municipal desabilita uma relação classificável no contrato')
  }
  if (relation.canDistance && result.hasDistance === false) {
    issues.push('hasDistance municipal desabilita a distância autorizada no contrato')
  }

  const referenceMilestone = comparisonReference?.milestone ?? (
    Number.isFinite(comparisonReference?.value)
      ? {
          value: comparisonReference.value,
          direction: comparisonReference.direction,
          unit: comparisonReference.unit,
        }
      : null
  )
  const canonicalDistance = canonicalDistanceForResult(result, referenceMilestone)
  const canonicalAchieved = Number.isFinite(canonicalDistance)
    ? canonicalDistance >= 0
    : null
  if (relation.canDistance && referenceMilestone) {
    if (numericValuesDiffer(result.meta, referenceMilestone.value)) {
      issues.push(`meta municipal=${result.meta}; contrato=${referenceMilestone.value}`)
    }
    if (result.direction && result.direction !== referenceMilestone.direction) {
      issues.push(
        `direction municipal=${result.direction}; contrato=${referenceMilestone.direction}`,
      )
    }
    if (result.distance != null && numericValuesDiffer(result.distance, canonicalDistance)) {
      issues.push(`distance municipal=${result.distance}; contrato=${canonicalDistance}`)
    }
    if (
      typeof result.atingida === 'boolean'
      && canonicalAchieved !== null
      && result.atingida !== canonicalAchieved
    ) {
      issues.push(`atingida municipal=${result.atingida}; contrato=${canonicalAchieved}`)
    }

    const municipalDeadline = result.deadline ?? result.meta_deadline
    if (
      Number.isFinite(referenceMilestone.year)
      &&
      municipalDeadline != null &&
      numericValuesDiffer(municipalDeadline, referenceMilestone.year)
    ) {
      issues.push(
        `deadline municipal=${municipalDeadline}; contrato=${referenceMilestone.year}`,
      )
    }

    const labelYear = String(result.meta_label ?? '').match(/\b20\d{2}\b/)?.[0]
    if (labelYear && Number(labelYear) !== referenceMilestone.year) {
      issues.push(
        `meta_label municipal referencia ${labelYear}; contrato=${referenceMilestone.year}`,
      )
    }
  }

  if (strict && issues.length > 0) {
    throw new Error(
      `Resultado municipal incompatível com ${relation.relationId}: ${issues.join('; ')}`,
    )
  }

  const authoritativeResult = {
    ...result,
    monitoringMode: relation.mode,
    monitoring_mode: relation.mode,
    tracks_goal: relation.canStatus,
    hasDistance: relation.canDistance,
    hasProjection: relation.canProjection,
    ...(relation.canDistance && referenceMilestone
      ? {
          atingida: canonicalAchieved,
          direction: referenceMilestone.direction,
          distance: canonicalDistance,
          meta: referenceMilestone.value,
          meta_label: 'Referência',
          ...(Number.isFinite(referenceMilestone.year)
            ? {
                deadline: referenceMilestone.year,
                meta_deadline: referenceMilestone.year,
              }
            : {}),
          display: {
            ...result.display,
            distance: formatCanonicalDistance(
              canonicalDistance,
              context.indicator?.unit,
            ),
          },
        }
      : {}),
  }

  return { context, issues, result: authoritativeResult }
}

export function isPne2026ProgressRelation(goalId, indicatorId) {
  return getPne2026Relation(goalId, indicatorId)?.mode === PNE_2026_RELATIONSHIP_MODES.PROGRESS
}

export function isPne2026ComplementaryRelation(goalId, indicatorId) {
  return getPne2026Relation(goalId, indicatorId)?.mode === PNE_2026_RELATIONSHIP_MODES.COMPLEMENTARY
}

export function isPne2026TrackingRelation(goalId, indicatorId) {
  return getPne2026Relation(goalId, indicatorId)?.mode === PNE_2026_RELATIONSHIP_MODES.TRACKING
}

export function isPne2026HiddenRelation(goalId, indicatorId) {
  return getPne2026Relation(goalId, indicatorId)?.mode === PNE_2026_RELATIONSHIP_MODES.HIDDEN
}

export function canPne2026RelationProject(goalId, indicatorId) {
  return getPne2026Relation(goalId, indicatorId)?.canProjection === true
}

export function canPne2026RelationEnterDiagnostic(goalId, indicatorId) {
  return getPne2026Relation(goalId, indicatorId)?.includeInDiagnostic === true
}

export const getGoal = getPne2026Goal
export const getIndicator = getPne2026Indicator
export const getRelation = getPne2026Relation
export const getRelationsForGoal = getPne2026RelationsForGoal
export const getRelationsForIndicator = getPne2026RelationsForIndicator
export const resolveRelation = resolvePne2026Relation
export const getPublicRelationsForGoal = getPne2026PublicRelationsForGoal
export const getRelationCapabilities = getPne2026RelationCapabilities
export const getRelationContext = getPne2026RelationContext
export const resolveLegalReference = resolvePne2026LegalReference
export const resolveComparisonReference = resolvePne2026ComparisonReference
export const isProgressRelation = isPne2026ProgressRelation
export const isTrackingRelation = isPne2026TrackingRelation
export const isComplementaryRelation = isPne2026ComplementaryRelation
export const isHiddenRelation = isPne2026HiddenRelation
export const canRelationProject = canPne2026RelationProject
export const canRelationEnterDiagnostic = canPne2026RelationEnterDiagnostic

export function normalizePne2026GoalIndicatorContract(value = contract) {
  if (Array.isArray(value)) {
    return value.map((item) => normalizePne2026GoalIndicatorContract(item))
  }

  if (value && typeof value === 'object') {
    return Object.fromEntries(
      Object.keys(value)
        .sort()
        .map((key) => [key, normalizePne2026GoalIndicatorContract(value[key])]),
    )
  }

  return value
}

export function stableStringifyPne2026GoalIndicatorContract(value = contract) {
  return JSON.stringify(normalizePne2026GoalIndicatorContract(value))
}
