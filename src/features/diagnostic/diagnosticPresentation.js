import presentationPolicy from '../../../contracts/pne2026-diagnostic-presentation-policy.json' with { type: 'json' }
import {
  PNE_2026_GOAL_INDICATOR_CONTRACT,
  PNE_2026_RELATIONSHIP_MODES,
  getPne2026Goal,
  getPne2026Indicator,
} from '../../data/pne2026GoalIndicatorContract.js'
import {
  getPne2026PublicDescription,
} from './pne2026DiagnosticPresentationCatalog.js'
import { getPne2026PublicFormulaDescription } from '../../utils/dataSourceNotes.js'

export const DIAGNOSTIC_VIEW_MODEL_VERSION = 'pne2026-diagnostic-view-model-v1'
export const DIAGNOSTIC_RESULT_VIEWS = Object.freeze({
  LEGAL: 'legal',
  TRACKING: 'tracking',
})

const relationsById = new Map(
  PNE_2026_GOAL_INDICATOR_CONTRACT.relations.map((relation) => [relation.relationId, relation]),
)
const presentationByRelationId = new Map(
  presentationPolicy.relations.map((entry) => [entry.relationId, entry]),
)
const reportedResolutionIssues = new Set()

function isStrictResolutionEnvironment() {
  if (typeof globalThis.process === 'object' && globalThis.process?.env) {
    return globalThis.process.env.NODE_ENV !== 'production'
  }
  return Boolean(import.meta.env?.DEV || import.meta.env?.MODE === 'test')
}

function reportResolutionIssue(message) {
  if (isStrictResolutionEnvironment()) throw new Error(message)
  if (reportedResolutionIssues.has(message)) return
  reportedResolutionIssues.add(message)
  console.error(message)
}

function resolveCanonicalRelation(goalId, result) {
  if (!result?.relationId) {
    reportResolutionIssue(
      `Diagnóstico PNE inconsistente: relationId ausente para ${goalId} × ${result?.indicatorId ?? 'indicador ausente'}.`,
    )
    return null
  }
  const relation = relationsById.get(result.relationId)
  if (!relation) {
    reportResolutionIssue(
      `Diagnóstico PNE inconsistente: relationId desconhecido ${result.relationId}.`,
    )
    return null
  }
  if (
    relation.goalId !== goalId
    || relation.indicatorId !== result.indicatorId
  ) {
    reportResolutionIssue(
      `Diagnóstico PNE inconsistente: ${result.relationId} não corresponde a ${goalId} × ${result.indicatorId}.`,
    )
    return null
  }
  return relation
}

function relationshipPresentation(mode) {
  if (mode === PNE_2026_RELATIONSHIP_MODES.COMPLEMENTARY) {
    return {
      relationshipLabel: 'Indicador complementar',
      relationshipNote: 'Este indicador apoia a leitura da meta, sem medir seu cumprimento.',
    }
  }

  return { relationshipLabel: null, relationshipNote: '' }
}

const EXPLICIT_COMPLEMENTARY_READINGS = new Set([
  'relation.9.d.educacao_indigena_cobertura_estimada_4_17',
  'relation.10.b.aee_oferta_escolas_elegiveis',
  'relation.14.c.superior_concluintes_oferta_local',
  'relation.15.c.superior_docentes_mestres_doutores_sede',
  'relation.17.c.munic_planos_carreira_declarados',
  'relation.18.c.munic_forum_educacao_declarado',
  'relation.16.a.capes_titulados_oferta_local',
  'relation.15.a.cpc_cursos_oferta_local',
  'relation.17.e.enade_licenciaturas_oferta_local',
])

function normalizeCurrent(current) {
  if (!current || typeof current !== 'object') return current
  if (current.unit !== 'percent' || !Number.isFinite(current.value)) return current
  return {
    ...current,
    displayValue: current.value,
    displayText: formatPublicValue(current.value, current.unit),
  }
}

function buildCommonViewModel({ editorial, goalId, relation, result }) {
  const indicator = getPne2026Indicator(relation.indicatorId)
  const goal = getPne2026Goal(relation.goalId)
  const formula = PNE_2026_GOAL_INDICATOR_CONTRACT.formulas[indicator?.formulaId]
  const catalogProjection = formula?.catalogProjection
  const current = normalizeCurrent(result.current)
  const presentation = relationshipPresentation(relation.mode)
  const publicName = relation.publicLabelOverride
    ?? indicator?.publicTitle
    ?? result.publicName
  const publicDescription = relation.publicDescriptionOverride
    ?? indicator?.publicDescription
    ?? result.publicDescription
    ?? getPne2026PublicDescription(relation.relationId)
  const methodologyDescription = getPne2026PublicFormulaDescription(
    indicator?.formulaId,
    indicator?.publicDescription,
  )

  return {
    relationId: relation.relationId,
    mode: relation.mode,
    goalId: relation.goalId,
    goalTitle: goal?.publicTitle ?? result.goalTitle ?? `Meta ${goalId}`,
    indicatorId: relation.indicatorId,
    themeId: editorial.themeId,
    displayOrder: editorial.displayOrder,
    summaryPriority: editorial.summaryPriority,
    displayGroup: editorial.displayGroup,
    publicName,
    publicDescription,
    current,
    rawValue: current?.value ?? null,
    year: current?.year ?? null,
    unit: indicator?.unit ?? current?.unit ?? null,
    numerator: current?.numerator ?? result.numeratorValue ?? null,
    denominator: current?.denominator ?? result.denominatorValue ?? null,
    numeratorField: result.numeratorField ?? catalogProjection?.numerator ?? null,
    denominatorField: result.denominatorField ?? catalogProjection?.denominator ?? null,
    sourceIds: [...(indicator?.sourceIds ?? result.sourceIds ?? [])],
    territoriality: indicator?.territoriality ?? null,
    methodology: catalogProjection && methodologyDescription
      ? {
          description: methodologyDescription,
        }
      : null,
    dataStatus: result.dataStatus
      ?? (Number.isFinite(current?.value) ? 'available' : 'unavailable'),
    reasonCode: result.reasonCode ?? null,
    dataStatusLabel: result.dataStatusLabel ?? null,
    publicReading: result.publicReading ?? result.dataStatusLabel ?? '',
    ...presentation,
  }
}

function resolvePublicResult(goalId, result) {
  const relation = resolveCanonicalRelation(goalId, result)
  if (!relation) return null
  if (
    relation.mode === PNE_2026_RELATIONSHIP_MODES.HIDDEN
    || relation.includeInDiagnostic !== true
  ) return null

  const editorial = presentationByRelationId.get(relation.relationId)
  if (!editorial) {
    reportResolutionIssue(
      `Diagnóstico PNE inconsistente: política editorial ausente para ${relation.relationId}.`,
    )
    return null
  }

  const common = buildCommonViewModel({ editorial, goalId, relation, result })
  if (relation.mode === PNE_2026_RELATIONSHIP_MODES.COMPLEMENTARY) {
    return {
      ...common,
      publicReading: EXPLICIT_COMPLEMENTARY_READINGS.has(relation.relationId)
        ? common.publicReading || buildObservationalPublicReading(common.current)
        : buildObservationalPublicReading(common.current),
    }
  }

  return {
    ...common,
    publicReading: relation.canDistance && relation.canStatus
      ? common.publicReading
      : buildObservationalPublicReading(common.current),
    direction: relation.comparisonDirection
      ?? getPne2026Goal(relation.goalId)?.direction
      ?? null,
    indicatorReference: relation.comparisonReferenceId || relation.referenceId
      ? result.indicatorReference ?? null
      : null,
    classification: relation.mode === PNE_2026_RELATIONSHIP_MODES.PROGRESS
      && relation.canStatus
      ? result.classification ?? null
      : null,
    status: relation.canStatus ? result.status ?? null : null,
    distance: relation.canDistance ? result.distance ?? null : null,
    remainingGap: relation.canDistance ? result.remainingGap ?? null : null,
    favorableDifference: relation.canDistance ? result.favorableDifference ?? null : null,
    stateComparison: relation.stateReferencePolicy !== 'none'
      ? result.stateComparison ?? null
      : null,
    statewidePosition: relation.stateReferencePolicy !== 'none'
      ? result.statewidePosition ?? null
      : null,
    similarMunicipalities: relation.stateReferencePolicy !== 'none'
      ? result.similarMunicipalities ?? null
      : null,
    trajectory: relation.canProjection ? result.trajectory ?? null : null,
  }
}

function buildResolvedGoals(publicDiagnostic) {
  const orderedResults = (publicDiagnostic.goals ?? [])
    .flatMap((goal) => (goal.results ?? []).map((result) => ({ goalId: goal.goalId, result })))
    .map(({ goalId, result }) => resolvePublicResult(goalId, result))
    .filter(Boolean)
    .toSorted((left, right) => left.displayOrder - right.displayOrder)
  const seenRelationIds = new Set()
  const uniqueResults = orderedResults.filter((result) => {
    if (!seenRelationIds.has(result.relationId)) {
      seenRelationIds.add(result.relationId)
      return true
    }
    reportResolutionIssue(
      `Diagnóstico PNE inconsistente: resultado duplicado para ${result.relationId}.`,
    )
    return false
  })
  const goalsById = new Map()
  for (const result of uniqueResults) {
    const current = goalsById.get(result.goalId) ?? {
      goalId: result.goalId,
      title: result.goalTitle,
      order: result.displayOrder,
      results: [],
    }
    current.order = Math.min(current.order, result.displayOrder)
    current.results.push(result)
    goalsById.set(result.goalId, current)
  }
  return [...goalsById.values()].toSorted((left, right) => left.order - right.order)
}

function buildResolvedSummary(goals = []) {
  const results = goals.flatMap((goal) => goal.results)
  const available = results.filter((result) => result.dataStatus === 'available')
  const progress = available.filter((result) => result.mode === PNE_2026_RELATIONSHIP_MODES.PROGRESS)
  const stateResults = progress.filter((result) => result.stateComparison)
  return {
    availableResultCount: available.length,
    unavailableResultCount: results.length - available.length,
    essentialAvailableCount: available.filter(
      (result) => result.summaryPriority === 'essential',
    ).length,
    standardPriorityAvailableCount: available.filter(
      (result) => result.summaryPriority === 'standard',
    ).length,
    complementaryResultCount: available.filter(
      (result) => result.mode === PNE_2026_RELATIONSHIP_MODES.COMPLEMENTARY,
    ).length,
    trackingResultCount: available.filter(
      (result) => result.mode === PNE_2026_RELATIONSHIP_MODES.TRACKING,
    ).length,
    advanceCount: progress.filter((result) => result.classification === 'advance').length,
    maintainCount: progress.filter((result) => result.classification === 'maintain').length,
    unclassifiedCount: progress.filter((result) => !result.classification).length,
    stateAboveOrNearCount: stateResults.filter((result) => (
      result.stateComparison?.state === 'above'
      || result.stateComparison?.state === 'near'
    )).length,
    stateBelowCount: stateResults.filter(
      (result) => result.stateComparison?.state === 'below',
    ).length,
  }
}

function buildThemeSummaries(goals) {
  const summaries = {}
  for (const result of goals.flatMap((goal) => goal.results)) {
    const summary = summaries[result.themeId] ?? {
      total: 0,
      advance: 0,
      maintain: 0,
      unclassified: 0,
    }
    if (result.mode === PNE_2026_RELATIONSHIP_MODES.PROGRESS) {
      summary.total += 1
      summary.advance += Number(result.classification === 'advance')
      summary.maintain += Number(result.classification === 'maintain')
      summary.unclassified += Number(result.classification == null)
    }
    summaries[result.themeId] = summary
  }
  return summaries
}

export function selectMunicipalDiagnosticContract(municipioData) {
  if (!municipioData) return { contract: null, status: 'missing' }
  if (
    municipioData.schemaVersion !== 'pne2026-diagnostic-loader-result-v1'
    || municipioData.diagnosticSource !== 'v3'
    || municipioData.pne2026PublicDiagnostic?.viewModelVersion
    !== DIAGNOSTIC_VIEW_MODEL_VERSION
  ) {
    return { contract: null, status: 'incompatible_version' }
  }
  return { contract: municipioData, status: 'ready' }
}

export function resolvePne2026DiagnosticViewModel(publicDiagnostic) {
  if (publicDiagnostic.viewModelVersion === DIAGNOSTIC_VIEW_MODEL_VERSION) {
    return publicDiagnostic
  }

  const goals = buildResolvedGoals(publicDiagnostic)
  const summary = buildResolvedSummary(goals)
  return {
    viewModelVersion: DIAGNOSTIC_VIEW_MODEL_VERSION,
    municipalityId: publicDiagnostic.municipalityId,
    municipalityName: publicDiagnostic.municipalityName,
    presentation: {
      themes: presentationPolicy.themes
        .map((theme) => ({
          id: theme.themeId,
          order: theme.displayOrder,
          label: theme.label,
        }))
        .toSorted((left, right) => left.order - right.order),
    },
    goals,
    summary,
    themeSummaries: buildThemeSummaries(goals),
    sources: publicDiagnostic.sources ?? [],
  }
}

export function isComparableLegalDiagnosticResult(result) {
  return (
    result?.mode === PNE_2026_RELATIONSHIP_MODES.PROGRESS
    && result.dataStatus === 'available'
    && Number.isFinite(result.current?.value)
    && Number.isFinite(result.indicatorReference?.value)
    && Number.isFinite(result.distance)
    && ['advance', 'maintain'].includes(result.classification)
  )
}

export function isAvailableTrackingDiagnosticResult(result) {
  return (
    result?.mode === PNE_2026_RELATIONSHIP_MODES.TRACKING
    && result.dataStatus === 'available'
    && Number.isFinite(result.current?.value)
    && Number.isFinite(result.indicatorReference?.value)
  )
}

export function selectDiagnosticResults(
  publicDiagnostic,
  view = DIAGNOSTIC_RESULT_VIEWS.LEGAL,
) {
  const predicate = view === DIAGNOSTIC_RESULT_VIEWS.TRACKING
    ? isAvailableTrackingDiagnosticResult
    : isComparableLegalDiagnosticResult
  return flattenPublicResults(publicDiagnostic).filter(({ result }) => predicate(result))
}

export function selectDiagnosticOfficialSources(
  publicDiagnostic,
  view = DIAGNOSTIC_RESULT_VIEWS.LEGAL,
) {
  const sourceIds = new Set(
    selectDiagnosticResults(publicDiagnostic, view)
      .flatMap(({ result }) => result.sourceIds ?? []),
  )
  return getPublicOfficialSources(publicDiagnostic?.sources)
    .filter((source) => sourceIds.has(source.id))
}

export function selectLegalResultsWithoutComparison(publicDiagnostic) {
  return flattenPublicResults(publicDiagnostic).filter(({ result }) => (
    result.mode === PNE_2026_RELATIONSHIP_MODES.PROGRESS
    && !isComparableLegalDiagnosticResult(result)
  ))
}

export function getDiagnosticSituationKey(result) {
  if (result?.mode === PNE_2026_RELATIONSHIP_MODES.TRACKING) {
    if (['Referência alcançada', 'Dentro do limite'].includes(result.status)) {
      return 'maintain'
    }
    if (['Abaixo da referência', 'Acima do limite'].includes(result.status)) {
      return 'advance'
    }
    return 'unclassified'
  }
  return ['advance', 'maintain'].includes(result?.classification)
    ? result.classification
    : 'unclassified'
}

export function summarizeDiagnosticResults(items = []) {
  return items.reduce((summary, { result }) => {
    const situation = getDiagnosticSituationKey(result)
    return {
      total: summary.total + 1,
      advance: summary.advance + Number(situation === 'advance'),
      maintain: summary.maintain + Number(situation === 'maintain'),
    }
  }, {
    total: 0,
    advance: 0,
    maintain: 0,
  })
}

export function selectLegalDiagnosticSummary(publicDiagnostic) {
  const comparable = selectDiagnosticResults(
    publicDiagnostic,
    DIAGNOSTIC_RESULT_VIEWS.LEGAL,
  )
  const withoutComparison = selectLegalResultsWithoutComparison(publicDiagnostic)
  const counts = summarizeDiagnosticResults(comparable)
  const stateResults = comparable.filter(({ result }) => result.stateComparison)
  return {
    totalIndicatorCount: comparable.length + withoutComparison.length,
    comparableIndicatorCount: comparable.length,
    unavailableComparisonCount: withoutComparison.length,
    advanceCount: counts.advance,
    maintainCount: counts.maintain,
    stateAboveOrNearCount: stateResults.filter(({ result }) => (
      result.stateComparison?.state === 'above'
      || result.stateComparison?.state === 'near'
    )).length,
    stateBelowCount: stateResults.filter(
      ({ result }) => result.stateComparison?.state === 'below',
    ).length,
  }
}

export function selectDiagnosticThemeGroups(
  publicDiagnostic,
  {
    situation = 'all',
    view = DIAGNOSTIC_RESULT_VIEWS.LEGAL,
  } = {},
) {
  const visibleResults = selectDiagnosticResults(publicDiagnostic, view)
    .filter(({ result }) => (
      situation === 'all' || getDiagnosticSituationKey(result) === situation
    ))

  return (publicDiagnostic?.presentation?.themes ?? [])
    .map((theme) => ({
      results: visibleResults.filter(({ result }) => result.themeId === theme.id),
      theme,
    }))
    .filter(({ results }) => results.length)
    .map(({ results, theme }, index) => ({
      results,
      summary: summarizeDiagnosticResults(results),
      theme: {
        ...theme,
        visibleOrder: index + 1,
      },
    }))
}

function buildObservationalPublicReading(current) {
  if (!current || !Number.isFinite(current.value)) return ''
  return `Em ${current.year}, o município registrou ${formatPublicValue(current.value, current.unit)} neste indicador.`
}

export function buildPublicSummaryText(summary = {}) {
  const comparableCount = Number.isFinite(summary.comparableIndicatorCount)
    ? summary.comparableIndicatorCount
    : (summary.advanceCount ?? 0) + (summary.maintainCount ?? 0)
  if (!comparableCount) {
    return 'O diagnóstico não possui indicadores com comparação legal disponível neste momento.'
  }
  return `Entre os ${comparableCount} indicadores com comparação disponível, ${summary.maintainCount} ${summary.maintainCount === 1 ? 'referência foi alcançada' : 'referências foram alcançadas'} e ${summary.advanceCount} ${summary.advanceCount === 1 ? 'está abaixo da referência' : 'estão abaixo da referência'}.`
}

export function buildPublicDiagnosticCopy(publicDiagnostic, municipio) {
  if (
    publicDiagnostic?.viewModelVersion
    !== DIAGNOSTIC_VIEW_MODEL_VERSION
  ) return ''

  const legalSummary = selectLegalDiagnosticSummary(publicDiagnostic)
  const legalResults = selectDiagnosticResults(
    publicDiagnostic,
    DIAGNOSTIC_RESULT_VIEWS.LEGAL,
  )
  const essentials = legalResults
    .filter(({ result }) => result.summaryPriority === 'essential')
    .toSorted((left, right) => left.result.displayOrder - right.result.displayOrder)
  const essentialIds = new Set(essentials.map(({ result }) => result.relationId))
  const lines = [
    `Diagnóstico educacional de ${municipio}`,
    'Plano Nacional de Educação (PNE) 2026–2036',
    '',
    'Resumo do diagnóstico',
    ...buildSummaryCopyLines(legalSummary),
  ]

  if (essentials.length) {
    lines.push('', 'Resultados essenciais')
    for (const item of essentials) appendCopyResult(lines, item)
  }

  const remainingGoals = legalResults
    .filter(({ result }) => !essentialIds.has(result.relationId))
    .reduce((goals, { goal, result }) => {
      const current = goals.find((item) => item.goalId === goal.goalId)
      if (current) current.results.push(result)
      else goals.push({ ...goal, results: [result] })
      return goals
    }, [])

  if (remainingGoals.length) {
    lines.push('', 'Demais resultados')
    for (const goal of remainingGoals) {
      for (const result of goal.results) appendCopyResult(lines, { goal, result })
    }
  }

  const officialSources = selectDiagnosticOfficialSources(
    publicDiagnostic,
    DIAGNOSTIC_RESULT_VIEWS.LEGAL,
  )
  if (officialSources.length) {
    lines.push('', 'Fontes das informações')
    for (const source of officialSources) {
      lines.push(`${source.organization} — ${source.publicTitle} — ${source.period}.`)
    }
  }

  return lines
    .filter((line) => line !== null && line !== undefined && !String(line).includes('NaN'))
    .join('\n')
    .replace(/\n{3,}/g, '\n\n')
    .trim()
}

export function formatPublicValue(value, unit) {
  if (!Number.isFinite(value)) return ''
  const formatted = value.toLocaleString('pt-BR', { maximumFractionDigits: 1 })
  if (unit === 'percent') return `${formatted}%`
  if (unit === 'years') return `${formatted} anos`
  return formatted
}

export function getPublicCurrentValue(result) {
  if (result?.dataStatus !== 'available') {
    return result?.dataStatusLabel || 'Não disponível para o período'
  }
  const current = result?.current
  if (!current) return ''
  if (result.indicatorId === 'munic_planos_carreira_declarados') {
    const declaredRequirements = Number.isFinite(result.numerator)
      ? result.numerator
      : current.value
    return `${declaredRequirements.toLocaleString('pt-BR')} de 2 requisitos`
  }
  if (result.indicatorId === 'munic_forum_educacao_declarado') {
    return Number(current.value) >= 1 ? 'Declarado' : 'Não declarado'
  }
  if (current.unit === 'percent') {
    return formatPublicValue(current.value ?? current.displayValue, current.unit)
  }
  return current.displayText
    || formatPublicValue(current.displayValue ?? current.value, current.unit)
}

export function getPublicResultReading(result) {
  if (!isNonEmptyText(result?.publicReading)) return ''
  if (
    result?.relationId
    === 'relation.9.d.educacao_indigena_cobertura_estimada_4_17'
  ) {
    return normalizePublicPercentages(result.publicReading)
  }
  if (result?.current?.unit === 'percent' && Number(result.current.value) > 100) {
    return `Em ${result.current.year}, o município registrou ${formatPublicValue(result.current.value, 'percent')} neste indicador.`
  }
  return normalizePublicPercentages(result.publicReading)
}

export function formatPublicDistance(value, unit) {
  if (!Number.isFinite(value)) return ''
  const formatted = value.toLocaleString('pt-BR', {
    maximumFractionDigits: 1,
    signDisplay: 'always',
  })
  return unit === 'percent' ? `${formatted} p.p.` : formatted
}

export function getPublicResultStatus(result) {
  if (result?.dataStatus !== 'available') {
    return {
      key: 'followup',
      label: result?.dataStatusLabel || 'Não disponível para o período',
    }
  }
  if (result.mode === PNE_2026_RELATIONSHIP_MODES.COMPLEMENTARY) {
    return { key: 'context', label: 'Indicador complementar' }
  }
  if (result.mode === PNE_2026_RELATIONSHIP_MODES.TRACKING) {
    if (result.status === 'Referência alcançada' || result.status === 'Dentro do limite') {
      return { key: 'maintain', label: 'Na referência de acompanhamento' }
    }
    if (result.status === 'Acima do limite' || result.status === 'Abaixo da referência') {
      return { key: 'advance', label: 'Abaixo da referência de acompanhamento' }
    }
    return { key: 'followup', label: 'Situação de acompanhamento indisponível' }
  }
  if (result.classification === 'advance') {
    return { key: 'advance', label: 'Abaixo da referência' }
  }
  if (result.classification === 'maintain') {
    return { key: 'maintain', label: 'Referência alcançada' }
  }
  return { key: 'followup', label: 'Situação indisponível' }
}

export function getPublicRelationshipNote(result) {
  return isNonEmptyText(result?.relationshipNote) ? result.relationshipNote : ''
}

export function getPublicSupportingReadings(result) {
  if (![
    PNE_2026_RELATIONSHIP_MODES.PROGRESS,
    PNE_2026_RELATIONSHIP_MODES.TRACKING,
  ].includes(result?.mode)) return []
  const readings = []
  if (
    result.statewidePosition
    && typeof result.statewidePosition === 'object'
    && isNonEmptyText(result.statewidePosition.reading)
  ) {
    readings.push({
      kind: 'position',
      title: 'Posição entre os municípios do RS',
      lines: [normalizePublicPercentages(result.statewidePosition.reading)],
    })
  }
  if (isNonEmptyText(result.similarMunicipalities?.reading)) {
    readings.push({
      kind: 'similar',
      title: isNonEmptyText(result.similarMunicipalities.title)
        ? result.similarMunicipalities.title
        : 'Municípios com oferta educacional de tamanho semelhante',
      lines: [normalizePublicPercentages(result.similarMunicipalities.reading)],
    })
  }
  const trajectoryLines = [
    result.trajectory?.historicalReading,
    result.trajectory?.modelReading,
    result.trajectory?.denominatorReading,
    result.trajectory?.achievementReading,
    result.trajectory?.uncertaintyReading,
  ].filter(isNonEmptyText)
  if (trajectoryLines.length) {
    readings.push({
      kind: 'trajectory',
      title: 'Evolução recente',
      lines: trajectoryLines.map(normalizePublicPercentages),
    })
  }
  return readings
}

export function getPublicStateComparison(result) {
  if (![
    PNE_2026_RELATIONSHIP_MODES.PROGRESS,
    PNE_2026_RELATIONSHIP_MODES.TRACKING,
  ].includes(result?.mode)) return null
  const comparison = result?.stateComparison
  if (
    !comparison
    || !Number.isFinite(comparison.municipalityValue)
    || !Number.isFinite(comparison.stateValue)
    || !Number.isFinite(comparison.year)
    || !Number.isFinite(comparison.difference)
    || !isNonEmptyText(comparison.reading)
  ) return null

  const unit = comparison.unit || result.current?.unit
  return {
    municipalityValue: formatPublicValue(comparison.municipalityValue, unit),
    stateValue: formatPublicValue(comparison.stateValue, unit),
    difference: formatPublicDistance(comparison.difference, unit),
    year: comparison.year,
    reading: normalizePublicPercentages(comparison.reading),
    valueReading: normalizePublicPercentages(comparison.valueReading),
  }
}

export function getPublicOfficialSources(sources = []) {
  return sources.filter((source) => (
    isNonEmptyText(source.organization)
    && isNonEmptyText(source.publicTitle)
    && isNonEmptyText(source.period)
    && isNonEmptyText(source.officialUrl)
  ))
}

function flattenPublicResults(publicDiagnostic) {
  return (publicDiagnostic?.goals ?? []).flatMap((goal) => (
    goal.results.map((result) => ({ goal, result }))
  ))
}

function buildSummaryCopyLines(summary = {}) {
  return [
    Number.isFinite(summary.comparableIndicatorCount)
      ? `Indicadores com comparação disponível: ${summary.comparableIndicatorCount}.`
      : '',
    summary.maintainCount > 0 ? `Referências alcançadas: ${summary.maintainCount}.` : '',
    summary.advanceCount > 0 ? `Abaixo da referência: ${summary.advanceCount}.` : '',
    summary.unavailableComparisonCount > 0
      ? `Sem comparação no período: ${summary.unavailableComparisonCount}.`
      : '',
    Number.isFinite(summary.stateAboveOrNearCount)
      ? `Acima ou próximos do RS: ${summary.stateAboveOrNearCount}.`
      : '',
    Number.isFinite(summary.stateBelowCount)
      ? `Abaixo do RS: ${summary.stateBelowCount}.`
      : '',
  ].filter(Boolean)
}

function appendCopyResult(lines, { goal, result }) {
  lines.push(
    '',
    `Meta ${goal.goalId} — ${goal.title}`,
    result.publicName,
    getPublicResultStatus(result).label,
    `Resultado do município: ${displayCurrentValue(result)} (${result.current.year}).`,
  )
  if (
    [
      PNE_2026_RELATIONSHIP_MODES.PROGRESS,
      PNE_2026_RELATIONSHIP_MODES.TRACKING,
    ].includes(result.mode)
    && Number.isFinite(result.indicatorReference?.value)
  ) {
    lines.push(
      Number.isFinite(result.indicatorReference.year)
        ? `Referência: ${formatPublicValue(result.indicatorReference.value, result.current.unit)} até ${result.indicatorReference.year}.`
        : `Referência: ${formatPublicValue(result.indicatorReference.value, result.current.unit)}.`,
    )
  }
  const publicReading = getPublicResultReading(result)
  if (publicReading) lines.push(publicReading)
  const relationshipNote = getPublicRelationshipNote(result)
  if (relationshipNote) lines.push(relationshipNote)
  const stateComparison = getPublicStateComparison(result)
  if (stateComparison) {
    lines.push(
      'Comparação com o RS',
      isNonEmptyText(stateComparison.valueReading)
        ? stateComparison.valueReading
        : `Município ${stateComparison.municipalityValue}; Rio Grande do Sul ${stateComparison.stateValue}; ${stateComparison.year}.`,
      stateComparison.reading,
    )
  }
  for (const reading of getPublicSupportingReadings(result)) {
    lines.push(reading.title, ...reading.lines)
  }
}

function displayCurrentValue(result) {
  return getPublicCurrentValue(result)
}

function normalizePublicPercentages(text) {
  if (!isNonEmptyText(text)) return text
  return text
}

function isNonEmptyText(value) {
  return typeof value === 'string' && value.trim().length > 0
}
