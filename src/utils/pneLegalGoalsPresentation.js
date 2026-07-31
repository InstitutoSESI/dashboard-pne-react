import {
  PNE_2026_GOAL_INDICATOR_CONTRACT,
  PNE_2026_RELATIONSHIP_MODES,
  getPne2026Indicator,
  getPne2026PublicRelationsForGoal,
} from '../data/pne2026GoalIndicatorContract.js'
import {
  getPne2026PresentationThemeForRelation,
} from '../data/thematicGroups.js'

export const PNE_LEGAL_GOAL_CATEGORIES = Object.freeze({
  DIRECT: 'direct',
  PARTIAL: 'partial',
  COMPLEMENTARY: 'complementary',
  WITHOUT_INDICATOR: 'without_indicator',
})

export const PNE_LEGAL_GOAL_CATEGORY_LABELS = Object.freeze({
  [PNE_LEGAL_GOAL_CATEGORIES.DIRECT]: 'Acompanhamento direto',
  [PNE_LEGAL_GOAL_CATEGORIES.PARTIAL]: 'Acompanhamento parcial',
  [PNE_LEGAL_GOAL_CATEGORIES.COMPLEMENTARY]: 'Informação complementar',
  [PNE_LEGAL_GOAL_CATEGORIES.WITHOUT_INDICATOR]: 'Sem indicador municipal',
})

const DATA_STATUS_LABELS = Object.freeze({
  unavailable: 'Sem resultado comparável no período',
  not_applicable: 'Não se aplica ao município',
  suppressed: 'Dado suprimido pela fonte',
})

const TERRITORIALITY_LABELS = Object.freeze({
  higher_education_course_offer_location: 'oferta de cursos localizada no município',
  higher_education_institution_headquarters: 'instituições de ensino superior com sede no município',
  municipal_government_declaration: 'declaração da administração municipal',
  postgraduate_program_location: 'programas de pós-graduação localizados no município',
  residence: 'população residente no município',
  resident_population: 'população residente no município',
  school_location: 'estabelecimentos de ensino localizados no município',
  school_location_over_resident_indigenous_population_2022:
    'matrículas por localização da escola e população indígena residente em 2022',
  school_location_over_resident_population:
    'matrículas por localização da escola e população residente estimada',
})

export function getPneLegalGoalCategory(goalOrId) {
  const goalId = typeof goalOrId === 'string'
    ? goalOrId
    : goalOrId?.legalGoalId ?? goalOrId?.goalId
  const relations = getPne2026PublicRelationsForGoal(goalId)
  const comparableRelations = relations.filter(
    (relation) => relation.mode !== PNE_2026_RELATIONSHIP_MODES.COMPLEMENTARY,
  )

  if (comparableRelations.some((relation) => relation.legacyCoverage === 'direta')) {
    return PNE_LEGAL_GOAL_CATEGORIES.DIRECT
  }
  if (comparableRelations.length) {
    return PNE_LEGAL_GOAL_CATEGORIES.PARTIAL
  }
  if (relations.some(
    (relation) => relation.mode === PNE_2026_RELATIONSHIP_MODES.COMPLEMENTARY,
  )) {
    return PNE_LEGAL_GOAL_CATEGORIES.COMPLEMENTARY
  }
  return PNE_LEGAL_GOAL_CATEGORIES.WITHOUT_INDICATOR
}

export function buildPneLegalGoalsSummary(goals) {
  const summary = {
    complementary: 0,
    direct: 0,
    partial: 0,
    total: 0,
    withIndicator: 0,
    withoutIndicator: 0,
  }

  for (const goal of goals) {
    const category = getPneLegalGoalCategory(goal)
    summary.total += 1
    if (category === PNE_LEGAL_GOAL_CATEGORIES.DIRECT) summary.direct += 1
    if (category === PNE_LEGAL_GOAL_CATEGORIES.PARTIAL) summary.partial += 1
    if (category === PNE_LEGAL_GOAL_CATEGORIES.COMPLEMENTARY) {
      summary.complementary += 1
    }
    if (category === PNE_LEGAL_GOAL_CATEGORIES.WITHOUT_INDICATOR) {
      summary.withoutIndicator += 1
    } else {
      summary.withIndicator += 1
    }
  }

  return summary
}

export function indexPne2026DiagnosticResults(diagnostic) {
  return new Map(
    (diagnostic?.goals ?? []).flatMap((goal) => (
      (goal.results ?? []).map((result) => [result.relationId, result])
    )),
  )
}

export function getPneLegalRelationPresentation({
  diagnosticResult,
  item,
  relation,
} = {}) {
  const indicator = getPne2026Indicator(relation?.indicatorId)
  const publicDescription = diagnosticResult?.publicDescription
    ?? relation?.publicDescription
    ?? indicator?.publicDescription
    ?? item?.desc
    ?? ''
  const relationshipNote = diagnosticResult?.relationshipNote
    ?? relation?.relationNote
    ?? ''
  const mode = relation?.monitoringMode ?? relation?.mode
  const isComplementary = mode === PNE_2026_RELATIONSHIP_MODES.COMPLEMENTARY
  const isTracking = mode === PNE_2026_RELATIONSHIP_MODES.TRACKING

  return {
    category: relation?.coverage === 'direta' ? 'direct' : 'partial',
    dataStatusLabel: DATA_STATUS_LABELS[
      diagnosticResult?.dataStatus
    ] ?? null,
    indicator,
    limitation: deriveLimitation(publicDescription, relationshipNote),
    measurement: publicDescription || 'Descrição pública não disponível no contrato.',
    mode,
    modeLabel: isComplementary
      ? 'Informação complementar'
      : isTracking
        ? 'Acompanhamento municipal'
        : 'Acompanhamento da meta',
    publicDescription,
    publicName: diagnosticResult?.publicName
      ?? relation?.publicName
      ?? indicator?.publicTitle
      ?? item?.label
      ?? relation?.indicatorId,
    referenceNatureLabel: isComplementary
      ? 'Informação complementar — sem referência municipal'
      : isTracking
        ? 'Referência de acompanhamento'
        : 'Referência prevista na meta',
    relationship: relationshipNote || 'Relação pública registrada no contrato canônico.',
    territorialityLabel: TERRITORIALITY_LABELS[indicator?.territoriality]
      ?? indicator?.territoriality
      ?? 'territorialidade não informada',
  }
}

export function getPneLegalDataStatusLabel(dataStatus) {
  return DATA_STATUS_LABELS[dataStatus] ?? null
}

export function getPne2026CanonicalCycleItems() {
  const existing = new Set()
  return PNE_2026_GOAL_INDICATOR_CONTRACT.relations.flatMap((relation) => {
    if (
      relation.mode === PNE_2026_RELATIONSHIP_MODES.HIDDEN
      || existing.has(relation.indicatorId)
    ) {
      return []
    }
    existing.add(relation.indicatorId)
    const indicator = getPne2026Indicator(relation.indicatorId)
    if (!indicator) return []
    const theme = getPne2026PresentationThemeForRelation(relation.relationId)
    return [{
      categoryKey: theme?.key ?? 'outros_temas_pne',
      categoryLabel: theme?.label ?? 'Outros temas do PNE',
      categoryOrder: theme?.order ?? Number.MAX_SAFE_INTEGER,
      desc: indicator.publicDescription,
      key: indicator.indicatorId,
      label: relation.publicLabelOverride ?? indicator.publicTitle,
      relationId: relation.relationId,
      title: relation.publicLabelOverride ?? indicator.publicTitle,
      value_mode: indicator.unit,
    }]
  })
}

function deriveLimitation(publicDescription, relationshipNote) {
  const descriptionSentences = splitSentences(publicDescription)
  if (descriptionSentences.length > 1) {
    return descriptionSentences.slice(1).join(' ')
  }

  const noteSentences = splitSentences(relationshipNote)
  const explicitLimits = noteSentences.filter((sentence) => (
    /\b(não|sem|apenas|somente|combina|diferen|limita|aproxim|proxy)\b/i.test(sentence)
  ))
  return explicitLimits.join(' ')
    || relationshipNote
    || publicDescription
    || 'Limitação específica não registrada no contrato.'
}

function splitSentences(value) {
  return String(value ?? '')
    .match(/[^.!?]+[.!?]+|[^.!?]+$/g)
    ?.map((sentence) => sentence.trim())
    .filter(Boolean)
    ?? []
}
