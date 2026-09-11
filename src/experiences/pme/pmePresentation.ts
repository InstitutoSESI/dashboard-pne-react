import {
  PNE_2026_GOAL_INDICATOR_CONTRACT,
  PNE_2026_RELATIONSHIP_MODES,
} from '../../data/pne2026GoalIndicatorContract.js'
import { getPmeEditorialPaths, getPmeObjectiveEditorial } from './pmeCatalog'
import type { Pne2026DiagnosticLoaderResult } from '../../features/diagnostic/diagnosticTypes'
import type { Pne2026DiagnosticResultViewModel } from '../../features/diagnostic/diagnosticTypes'
import type {
  PmeAgendaItem,
  PmeAgendaModel,
  PmeDataState,
  PmeDiagnosticModuleState,
  PmeEvidence,
  PmeMatrizGoalWithoutOwnCause,
  PmeMatrizObjectiveContext,
  PmeMatrizLoaderResult,
  PmeMatrizModuleState,
  PmeMatrizPriorityGoal,
  PmeModuleError,
  PmeMunicipalBuildInput,
  PmeObjectiveBuildInput,
  PmeObjectiveModel,
  PmePublicObjectivesBundle,
  PmeMunicipalModel,
  PmeRelationshipCounts,
  PmeSourceProvenance,
} from './pmeTypes'

const IBGE7_PATTERN = /^\d{7}$/
type ContractRelation = (typeof PNE_2026_GOAL_INDICATOR_CONTRACT.relations)[number]
type ContractGoal = (typeof PNE_2026_GOAL_INDICATOR_CONTRACT.goals)[keyof typeof PNE_2026_GOAL_INDICATOR_CONTRACT.goals]
type ComparableDiagnosticResult = Exclude<Pne2026DiagnosticResultViewModel, { mode: 'complementary' }>

function isDiagnosticResult(value: unknown): value is Pne2026DiagnosticLoaderResult {
  return Boolean(value) && typeof value === 'object' && (value as { diagnosticSource?: string }).diagnosticSource === 'v3'
}

function isMatrizResult(value: unknown): value is PmeMatrizLoaderResult {
  return Boolean(value) && typeof value === 'object' && (value as { schemaVersion?: string }).schemaVersion === 'pne2026-matriz-loader-result-v3'
}

function errorShape(error: unknown): PmeModuleError {
  const source = error && typeof error === 'object' ? error as Record<string, unknown> : {}
  return {
    code: typeof source.code === 'string' ? source.code : 'module_error',
    message: error instanceof Error ? error.message : String(source.message ?? error ?? 'Erro desconhecido.'),
    stage: typeof source.stage === 'string' ? source.stage : null,
  }
}

export function normalizePmeDiagnosticModule(value: PmeMunicipalBuildInput['diagnostic']): PmeDiagnosticModuleState {
  if (!value) return { status: 'not_loaded' }
  if (isDiagnosticResult(value)) return { status: 'available', value }
  return value as PmeDiagnosticModuleState
}

export function normalizePmeMatrizModule(value: PmeMunicipalBuildInput['matriz']): PmeMatrizModuleState {
  if (!value) return { status: 'not_loaded' }
  if (isMatrizResult(value)) return { status: 'available', value }
  return value as PmeMatrizModuleState
}

function emptyCounts(): PmeRelationshipCounts {
  return {
    methodologicalRelationships: 0,
    observedRelationships: 0,
    nullRelationships: 0,
    unavailableRelationships: 0,
    suppressedRelationships: 0,
    notApplicableRelationships: 0,
    notPublishedRelationships: 0,
    notLoadedRelationships: 0,
    complementaryRelationships: 0,
  }
}

function sumCounts(items: PmeRelationshipCounts[]): PmeRelationshipCounts {
  return items.reduce((total, current) => {
    for (const key of Object.keys(total) as Array<keyof PmeRelationshipCounts>) total[key] += current[key]
    return total
  }, emptyCounts())
}

function countEvidence(evidence: PmeEvidence[]): PmeRelationshipCounts {
  const counts = emptyCounts()
  for (const item of evidence) {
    counts.methodologicalRelationships += 1
    if (item.mode === 'complementary') counts.complementaryRelationships += 1
    if (item.dataState === 'observed') counts.observedRelationships += 1
    if (item.dataState === 'null') counts.nullRelationships += 1
    if (item.dataState === 'unavailable') counts.unavailableRelationships += 1
    if (item.dataState === 'suppressed') counts.suppressedRelationships += 1
    if (item.dataState === 'not_applicable') counts.notApplicableRelationships += 1
    if (item.dataState === 'not_published') counts.notPublishedRelationships += 1
    if (item.dataState === 'not_loaded') counts.notLoadedRelationships += 1
  }
  return counts
}

function dataStateFor(result: Pick<Pne2026DiagnosticResultViewModel, 'dataStatus' | 'rawValue'> | undefined, diagnosticStatus: PmeDiagnosticModuleState['status']): PmeDataState {
  if (!result) return diagnosticStatus === 'available' ? 'not_published' : 'not_loaded'
  if (result.dataStatus === 'available') return result.rawValue === null ? 'null' : 'observed'
  if (result.dataStatus === 'unavailable') return 'unavailable'
  if (result.dataStatus === 'suppressed') return 'suppressed'
  if (result.dataStatus === 'not_applicable') return 'not_applicable'
  return 'not_loaded'
}

function isComparableResult(result: Pne2026DiagnosticResultViewModel | undefined): result is ComparableDiagnosticResult {
  return result?.mode === 'progress' || result?.mode === 'tracking'
}

function comparisonCompatibility(
  relation: ContractRelation,
  indicator: { unit: string; territoriality: string },
  result: ComparableDiagnosticResult | null,
  state: PmeDataState,
): PmeEvidence['comparisonCompatibility'] {
  if (!result || state !== 'observed' || !relation.canStatus || relation.stateReferencePolicy === 'none') {
    return 'not_available'
  }
  const comparison = result.stateComparison
  if (!comparison) return 'not_available'
  return comparison.year === result.year
    && comparison.unit === result.unit
    && comparison.unit === indicator.unit
    && comparison.municipalityValue === result.rawValue
    && result.territoriality === indicator.territoriality
    ? 'compatible'
    : 'incompatible'
}

function buildEvidence(relation: ContractRelation, result: Pne2026DiagnosticResultViewModel | undefined, diagnosticStatus: PmeDiagnosticModuleState['status']): PmeEvidence {
  const indicator = Object.values(PNE_2026_GOAL_INDICATOR_CONTRACT.indicators)
    .find((candidate) => candidate.indicatorId === relation.indicatorId)
  if (!indicator) throw new TypeError(`Indicador ausente no contrato: ${relation.indicatorId}.`)
  const permissions = {
    canDistance: relation.canDistance === true,
    canStatus: relation.canStatus === true,
    canProjection: relation.canProjection === true,
  }
  const state = dataStateFor(result, diagnosticStatus)
  const comparable = isComparableResult(result) ? result : null
  const comparisonCompatibilityResult = comparisonCompatibility(relation, indicator, comparable, state)
  const hasComparison = comparisonCompatibilityResult === 'compatible'
  const hasStatus = permissions.canStatus && state === 'observed' && comparable !== null
  const peers = comparable?.similarMunicipalities
  const hasPeers = hasStatus && peers != null && relation.stateReferencePolicy !== 'none'
    && typeof peers.year === 'number' && peers.year === result?.year
    && peers.unit === result?.unit && peers.unit === indicator.unit
    && result?.territoriality === indicator.territoriality
  const peersIncompatible = hasStatus && peers != null && !hasPeers
  // A historical reading is a published qualitative observation. It stays
  // separate from the optional projection and is never manufactured from one.
  const historicalReading = state === 'observed' ? comparable?.trajectory?.historicalReading ?? null : null
  const projectionFields = comparable?.trajectory
  const hasProjection = projectionFields && (
    projectionFields.estimatedAchievementYear !== undefined
    || projectionFields.achievementReading !== undefined
    || projectionFields.modelReading !== undefined
    || projectionFields.denominatorReading !== undefined
    || projectionFields.uncertaintyReading !== undefined
  )
  const projection = permissions.canProjection && state === 'observed' && hasProjection && projectionFields
    ? {
        estimatedAchievementYear: projectionFields.estimatedAchievementYear,
        achievementReading: projectionFields.achievementReading,
        modelReading: projectionFields.modelReading,
        denominatorReading: projectionFields.denominatorReading,
        uncertaintyReading: projectionFields.uncertaintyReading,
      }
    : null
  return {
    relationId: relation.relationId,
    goalId: relation.goalId,
    indicatorId: relation.indicatorId,
    title: result?.publicName ?? relation.publicLabelOverride ?? indicator.publicTitle ?? relation.indicatorId,
    description: (result?.publicDescription ?? indicator.publicDescription ?? '').replace(/\bsnapshot\b/g, 'levantamento'),
    relationshipNote: (result?.relationshipNote || relation.internalNote || 'Limitação metodológica não detalhada no resultado municipal.').replace(/\bsnapshot\b/g, 'levantamento'),
    mode: relation.mode as PmeEvidence['mode'],
    dataState: state,
    rawValue: result?.rawValue ?? null,
    displayValue: result?.current?.displayValue ?? null,
    unit: result?.unit ?? indicator.unit ?? null,
    period: result?.year ?? result?.current?.year ?? null,
    sourceIds: result?.sourceIds ?? indicator.sourceIds ?? [],
    reasonCode: result?.reasonCode ?? null,
    dataStatusLabel: result?.dataStatusLabel ?? null,
    territoriality: result?.territoriality ?? indicator.territoriality ?? null,
    methodologyDescription: (result?.methodology?.description ?? indicator.methodologyNote)?.replace(/\bsnapshot\b/g, 'levantamento') ?? null,
    indicatorReference: permissions.canStatus && comparable ? comparable.indicatorReference ?? null : null,
    numeratorField: result?.numeratorField ?? null,
    numerator: result?.numerator ?? null,
    denominatorField: result?.denominatorField ?? null,
    denominator: result?.denominator ?? null,
    permissions,
    classification: hasStatus && (comparable?.classification === 'advance' || comparable?.classification === 'maintain')
      ? comparable.classification : null,
    status: hasStatus ? comparable?.status ?? null : null,
    distance: permissions.canDistance && comparable ? comparable.distance ?? null : null,
    trajectory: historicalReading ? { historicalReading } : null,
    historicalReading,
    historicalLimit: historicalReading ? 'Leitura histórica reproduzida da publicação; este modelo não acrescenta série nem infere tendência.' : null,
    projection,
    comparisonCompatibility: comparisonCompatibilityResult,
    stateComparison: hasComparison ? comparable?.stateComparison ?? null : null,
    similarMunicipalities: hasPeers ? peers : null,
    statewidePosition: hasComparison ? comparable?.statewidePosition ?? null : null,
    publicReading: result?.publicReading ?? null,
    comparisonNote: [hasComparison ? comparable?.stateComparison?.reading
      : comparisonCompatibilityResult === 'incompatible'
        ? 'Comparação publicada não exibida porque período, unidade, valor municipal ou recorte não são compatíveis com a evidência apresentada.' : null,
    peersIncompatible ? 'Comparação com municípios semelhantes não exibida: seu período, unidade ou universo não é compatível com a evidência atual.' : null].filter(Boolean).join(' ') || null,
  }
}

function sourceProvenance(diagnostic: PmeDiagnosticModuleState, matriz: PmeMatrizModuleState): PmeSourceProvenance[] {
  const sourceIds = new Set<string>()
  const diagnosticSourcesById = new Map(
    diagnostic.status === 'available'
      ? diagnostic.value.pne2026PublicDiagnostic.sources.map((source) => [source.id, source] as const)
      : [],
  )
  if (diagnostic.status === 'available') {
    diagnostic.value.pne2026PublicDiagnostic.sources.forEach((source) => sourceIds.add(source.id))
    diagnostic.value.pne2026PublicDiagnostic.goals.forEach((goal) => {
      goal.results.forEach((result) => result.sourceIds.forEach((sourceId) => sourceIds.add(sourceId)))
    })
  }
  Object.values(PNE_2026_GOAL_INDICATOR_CONTRACT.goals).forEach((goal) => sourceIds.add(goal.legalSourceId))
  Object.values(PNE_2026_GOAL_INDICATOR_CONTRACT.indicators)
    .forEach((indicator) => indicator.sourceIds.forEach((sourceId) => sourceIds.add(sourceId)))
  const diagnosticReleaseId = diagnostic.status === 'available' ? diagnostic.value.diagnosticReleaseId : null
  const matrizReferenceDate = matriz.status === 'available' ? matriz.value.referenceDate : null
  const matrizOutputSha256 = matriz.status === 'available' ? matriz.value.outputSha256 : null
  const sources: PmeSourceProvenance[] = [...sourceIds].sort().flatMap((sourceId) => {
    const source = Object.values(PNE_2026_GOAL_INDICATOR_CONTRACT.sources)
      .find((candidate) => candidate.sourceId === sourceId)
    const diagnosticSource = diagnosticSourcesById.get(sourceId)
    return [{
      sourceId,
      title: diagnosticSource?.publicTitle ?? source?.publicTitle ?? sourceId,
      officialUrl: diagnosticSource?.officialUrl ?? (source && 'officialUrl' in source ? source.officialUrl ?? null : null),
      period: diagnosticSource?.period ?? null,
      diagnosticReleaseId,
      matrizReferenceDate,
      matrizOutputSha256,
    }]
  })
  if (matriz.status === 'available') {
    sources.push({ sourceId: 'pne2026_matriz', title: 'Matriz de Prioridades publicada', officialUrl: null, period: matriz.value.referenceDate, diagnosticReleaseId: null, matrizReferenceDate, matrizOutputSha256 })
  }
  return sources
}

function matrizContext(matriz: PmeMatrizModuleState, goalId: string): PmeMatrizPriorityGoal | PmeMatrizGoalWithoutOwnCause | null {
  if (matriz.status !== 'available') return null
  return matriz.value.matriz.priorityGoals.find((item) => item.goalId === goalId)
    ?? matriz.value.matriz.goalsWithoutOwnCause.find((item) => item.goalId === goalId)
    ?? null
}

export function getPmeMatrizContextsForObjective(
  matriz: PmeMatrizModuleState,
  objectiveId: string,
): PmeMatrizObjectiveContext[] {
  if (matriz.status !== 'available') return []
  const matchesObjective = (goalId: string) => goalId.startsWith(`${objectiveId}.`)
  const contexts: PmeMatrizObjectiveContext[] = [
    ...matriz.value.matriz.priorityGoals
      .filter((goal) => matchesObjective(goal.goalId))
      .map((goal) => ({
        goalId: goal.goalId,
        title: goal.title,
        sourceVersion: matriz.value.matriz.curation.version,
        kind: 'priority_goal' as const,
        priorityGoal: goal,
        sharedCause: null,
        questions: goal.causes.flatMap((cause) => cause.workshopQuestions),
        federalFirstSteps: goal.causes
          .filter((cause) => cause.firstStep.kind === 'federal_instrument')
          .map((cause) => ({ factorId: cause.factorId, text: cause.firstStep.text, ref: cause.firstStep.ref })),
      })),
    ...matriz.value.matriz.goalsWithoutOwnCause
      .filter((goal) => matchesObjective(goal.goalId))
      .map((goal) => ({
        goalId: goal.goalId,
        title: goal.title,
        sourceVersion: matriz.value.matriz.curation.version,
        kind: 'shared_cause' as const,
        priorityGoal: null,
        sharedCause: goal,
        questions: [],
        federalFirstSteps: [],
      })),
  ]
  return contexts.sort((left, right) => {
    const leftOrder = (PNE_2026_GOAL_INDICATOR_CONTRACT.goals as Record<string, ContractGoal>)[left.goalId]?.legalOrder ?? Number.MAX_SAFE_INTEGER
    const rightOrder = (PNE_2026_GOAL_INDICATOR_CONTRACT.goals as Record<string, ContractGoal>)[right.goalId]?.legalOrder ?? Number.MAX_SAFE_INTEGER
    return leftOrder - rightOrder
  })
}

/** Uses classifications already published by the diagnostic. `advance` is not a trend statement. */
export function buildPmeAgendaModel(objectives: PmeMunicipalModel['objectives'], matriz: PmeMatrizModuleState, highlightLimit = 4): PmeAgendaModel {
  const items: PmeAgendaItem[] = []
  for (const objective of objectives) {
    for (const goal of objective.goals) {
      for (const evidence of goal.evidence) {
        if (evidence.classification !== 'advance' && evidence.classification !== 'maintain') continue
        const context = matrizContext(matriz, goal.goalId)
        const matrizQuestions = context && 'causes' in context
          ? context.causes.flatMap((cause) => cause.workshopQuestions) : []
        items.push({
          relationId: evidence.relationId,
          objectiveId: objective.objectiveId,
          goalId: goal.goalId,
          classification: evidence.classification,
          title: evidence.title,
          publicReading: evidence.publicReading,
          evidence,
          matrizContext: context,
          questions: [objective.guidingQuestion, ...matrizQuestions],
          paths: objective.paths.filter((path) => path.goalId === goal.goalId),
        })
      }
    }
  }
  return {
    items,
    highlights: items.slice(0, Math.max(0, highlightLimit)),
    criterion: 'Os destaques seguem a ordem canônica dos objetivos, metas e relações com classificação já publicada. “Avanço” é uma classificação do diagnóstico, não uma afirmação de tendência.',
  }
}

/** The legal 19-objective/73-goal panorama is available without a selected municipality. */
export function buildPmeObjectiveModels(input: PmeObjectiveBuildInput = {}): PmeObjectiveModel[] {
  const diagnostic = normalizePmeDiagnosticModule(input.diagnostic)
  const matriz = normalizePmeMatrizModule(input.matriz)
  const resultsByRelationId = new Map(
    diagnostic.status === 'available'
      ? diagnostic.value.pne2026PublicDiagnostic.goals.flatMap((goal) => goal.results.map((result) => [result.relationId, result] as const))
      : [],
  )
  const relationsByGoalId = new Map<string, ContractRelation[]>()
  for (const relation of PNE_2026_GOAL_INDICATOR_CONTRACT.relations) {
    if (relation.mode === PNE_2026_RELATIONSHIP_MODES.HIDDEN) continue
    const current = relationsByGoalId.get(relation.goalId) ?? []
    current.push(relation)
    relationsByGoalId.set(relation.goalId, current)
  }
  const goalsByObjective = new Map<string, ContractGoal[]>()
  for (const goal of Object.values(PNE_2026_GOAL_INDICATOR_CONTRACT.goals) as ContractGoal[]) {
    const current = goalsByObjective.get(goal.objectiveId) ?? []
    current.push(goal)
    goalsByObjective.set(goal.objectiveId, current)
  }
  return Array.from({ length: 19 }, (_, index) => String(index + 1)).map((objectiveId) => {
    const editorial = getPmeObjectiveEditorial(objectiveId)
    const matrizContexts = getPmeMatrizContextsForObjective(matriz, objectiveId)
    const goals = [...(goalsByObjective.get(objectiveId) ?? [])]
      .sort((left, right) => left.legalOrder - right.legalOrder)
      .map((goal) => {
        const evidence = (relationsByGoalId.get(goal.goalId) ?? []).map((relation) => (
          buildEvidence(relation, resultsByRelationId.get(relation.relationId), diagnostic.status)
        ))
        return { goalId: goal.goalId, legalOrder: goal.legalOrder, title: goal.publicTitle, legalText: goal.legalText, legalSourceId: goal.legalSourceId, evidence, counts: countEvidence(evidence) }
      })
    return { objectiveId, title: editorial.title, themeId: editorial.themeId, themeLabel: editorial.themeLabel, guidingQuestion: editorial.guidingQuestion, goals, counts: sumCounts(goals.map((goal) => goal.counts)), paths: getPmeEditorialPaths(objectiveId, matrizContexts), matrizContexts }
  })
}

export function buildPmeSources(input: PmeObjectiveBuildInput = {}): PmeSourceProvenance[] {
  return sourceProvenance(
    normalizePmeDiagnosticModule(input.diagnostic),
    normalizePmeMatrizModule(input.matriz),
  )
}

export function buildPmePublicObjectives(input: PmeObjectiveBuildInput = {}): PmePublicObjectivesBundle {
  const diagnostic = normalizePmeDiagnosticModule(input.diagnostic)
  const matriz = normalizePmeMatrizModule(input.matriz)
  return {
    objectives: buildPmeObjectiveModels({ diagnostic, matriz }),
    sources: sourceProvenance(diagnostic, matriz),
    modules: { diagnostic, matriz },
  }
}

/**
 * Projects existing diagnostic and Matriz publications into a presentation
 * model. It does not calculate statuses, distances, trends or coverage scores.
 */
export function buildPmeMunicipalModel(input: PmeMunicipalBuildInput): PmeMunicipalModel {
  const { municipality } = input
  if (!IBGE7_PATTERN.test(municipality.ibgeCode) || municipality.stateCode !== 'RS') {
    throw new TypeError('O modelo PME requer um código IBGE textual válido do Rio Grande do Sul.')
  }
  const diagnostic = normalizePmeDiagnosticModule(input.diagnostic)
  const matriz = normalizePmeMatrizModule(input.matriz)
  if (diagnostic.status === 'available' && diagnostic.value.municipalityId !== municipality.ibgeCode) {
    throw new TypeError('Diagnóstico municipal divergente da identidade PME.')
  }
  if (matriz.status === 'available' && matriz.value.municipalityId !== municipality.ibgeCode) {
    throw new TypeError('Matriz municipal divergente da identidade PME.')
  }
  const objectives = buildPmeObjectiveModels({ diagnostic, matriz })
  const draft: Omit<PmeMunicipalModel, 'agenda'> = { schemaVersion: 'pme-municipal-model-v1', municipality, objectives, sources: sourceProvenance(diagnostic, matriz), modules: { diagnostic, matriz } }
  return { ...draft, agenda: buildPmeAgendaModel(objectives, matriz, input.highlightLimit) }
}

export function toPmeDiagnosticError(error: unknown): PmeDiagnosticModuleState {
  return { status: 'error', error: errorShape(error) }
}

export function toPmeMatrizError(error: unknown): PmeMatrizModuleState {
  return { status: 'error', error: errorShape(error) }
}
