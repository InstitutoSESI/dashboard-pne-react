import { getPne2026Relation } from '../../../src/data/pne2026GoalIndicatorContract.js'
import {
  DIAGNOSTIC_VIEW_MODEL_VERSION,
  resolvePne2026DiagnosticViewModel,
} from '../../../src/features/diagnostic/diagnosticPresentation.js'

const LEGACY_CONTRACT_SCHEMA_VERSION = 'municipal-diagnostic-v2'
const LEGACY_PUBLIC_VERSION = 'pne2026-public-diagnostic-v2'
const reportedLegacyIssues = new Set()

function reportLegacyIssue(message) {
  const isProduction = process.env.NODE_ENV === 'production'
  if (!isProduction) throw new TypeError(message)
  if (reportedLegacyIssues.has(message)) return
  reportedLegacyIssues.add(message)
  console.error(message)
}

function resolveLegacyRelation(goalId, result) {
  const relation = getPne2026Relation(goalId, result?.indicatorId)
  if (result?.relationId) {
    if (relation?.relationId !== result.relationId) {
      reportLegacyIssue(
        relation
          ? `Diagnóstico PNE V2 inconsistente: ${result.relationId} não corresponde a ${goalId} × ${result.indicatorId}.`
          : `Diagnóstico PNE V2 inconsistente: relationId desconhecido ${result.relationId}.`,
      )
      return null
    }
    return result.relationId
  }
  if (!relation) {
    reportLegacyIssue(
      `Diagnóstico PNE V2 inconsistente: relação ausente para ${goalId} × ${result?.indicatorId ?? 'indicador ausente'}.`,
    )
    return null
  }
  return relation.relationId
}

function adaptLegacyPublicDiagnostic(publicDiagnostic) {
  return {
    municipalityId: publicDiagnostic.municipalityId,
    municipalityName: publicDiagnostic.municipalityName,
    goals: (publicDiagnostic.goals ?? []).map((goal) => ({
      goalId: goal.goalId,
      results: (goal.results ?? []).flatMap((result) => {
        const relationId = resolveLegacyRelation(goal.goalId, result)
        return relationId ? [{ ...result, relationId }] : []
      }),
    })),
    sources: publicDiagnostic.sources ?? [],
  }
}

export function sanitizePne2026PublicDiagnostic(publicDiagnostic) {
  if (publicDiagnostic?.viewModelVersion === DIAGNOSTIC_VIEW_MODEL_VERSION) {
    return publicDiagnostic
  }
  if (publicDiagnostic?.version !== LEGACY_PUBLIC_VERSION) {
    return publicDiagnostic
  }
  return resolvePne2026DiagnosticViewModel(
    adaptLegacyPublicDiagnostic(publicDiagnostic),
  )
}

export function sanitizeMunicipalDiagnosticContract(contract) {
  if (!contract?.pne2026PublicDiagnosticV2) return contract
  const viewModel = sanitizePne2026PublicDiagnostic(
    contract.pne2026PublicDiagnosticV2,
  )
  return {
    ...contract,
    pne2026PublicDiagnostic: viewModel,
    pne2026PublicDiagnosticV2: viewModel,
  }
}

export function selectMunicipalDiagnosticContract(municipioData) {
  const contract = municipioData?.schemaVersion
    ? municipioData
    : municipioData?.pne_2026_2036?.diagnostico_v2
  if (!contract) return { contract: null, status: 'missing' }
  if (
    contract.schemaVersion !== LEGACY_CONTRACT_SCHEMA_VERSION
    || contract.pne2026PublicDiagnosticV2?.version !== LEGACY_PUBLIC_VERSION
  ) {
    return { contract: null, status: 'incompatible_version' }
  }
  return {
    contract: sanitizeMunicipalDiagnosticContract(contract),
    status: 'ready',
  }
}

function canonicalJson(value) {
  if (Array.isArray(value)) return value.map(canonicalJson)
  if (!value || typeof value !== 'object') return value
  return Object.fromEntries(
    Object.keys(value)
      .sort()
      .map((key) => [key, canonicalJson(value[key])]),
  )
}

function flatten(viewModel) {
  return (viewModel?.goals ?? []).flatMap((goal) => goal.results ?? [])
}

export function normalizePne2026DiagnosticViewModel(viewModel) {
  const results = flatten(viewModel)
    .map((result) => ({
      relationId: result.relationId,
      goalId: result.goalId,
      indicatorId: result.indicatorId,
      mode: result.mode,
      title: result.goalTitle,
      publicName: result.publicName,
      publicDescription: result.publicDescription,
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
          label: result.indicatorReference.label,
          kind: result.indicatorReference.kind,
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
      statewidePosition: result.mode === 'progress'
        ? result.statewidePosition
        : null,
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
  return canonicalJson({
    results,
    summary: viewModel?.summary,
    themeSummaries: viewModel?.themeSummaries,
    sources: (viewModel?.sources ?? []).filter((source) => (
      typeof source.organization === 'string'
      && typeof source.period === 'string'
      && typeof source.officialUrl === 'string'
    )),
  })
}

export function assertPne2026DiagnosticViewModelParity(v2, v3) {
  const left = JSON.stringify(normalizePne2026DiagnosticViewModel(v2))
  const right = JSON.stringify(normalizePne2026DiagnosticViewModel(v3))
  if (left !== right) {
    throw new Error('Auditoria histórica PNE V2 × V3 divergiu no view model normalizado.')
  }
}
