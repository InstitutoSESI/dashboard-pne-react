import type { EducationIndicatorResult } from './educationTypes.js'
import { applyEducationIndicatorStageOption } from './educationViewModels.js'

interface TrajectoryStageDefinition {
  description: string
  key: string
  label: string
  question?: string
}

export interface TrajectoryStageCard {
  cardKey: string
  indicator: EducationIndicatorResult
  stageKey: string
}

export interface TrajectoryStageGroup extends TrajectoryStageDefinition {
  items: TrajectoryStageCard[]
}

export interface TrajectoryDetailSequenceItem extends EducationIndicatorResult {
  indicatorKey: string
  stageKey: string
}

const TRAJECTORY_STAGES: readonly TrajectoryStageDefinition[] = [
  {
    key: 'fundamental',
    label: 'Ensino Fundamental',
    description: 'Aprovação, reprovação, abandono e distorção idade-série no ensino fundamental.',
  },
  {
    key: 'fundamental_anos_iniciais',
    label: 'Ensino Fundamental — Anos iniciais',
    description: 'Fluxo escolar, aprendizagem e alfabetização nos anos iniciais do ensino fundamental.',
  },
  {
    key: 'fundamental_anos_finais',
    label: 'Ensino Fundamental — Anos finais',
    description: 'Fluxo escolar e aprendizagem nos anos finais do ensino fundamental.',
  },
  {
    key: 'medio',
    label: 'Ensino Médio',
    description: 'Fluxo escolar e aprendizagem no ensino médio.',
  },
  {
    key: 'contexto',
    label: 'Contexto educacional',
    question: 'Que contexto ajuda a interpretar os resultados educacionais?',
    description: 'Indicadores de contexto que não possuem recorte por etapa.',
  },
]

const TRAJECTORY_STAGE_OVERRIDES: Readonly<Record<string, readonly string[]>> = {
  'apr-alfabetizacao': ['fundamental_anos_iniciais'],
  'fluxo-aprovacao': ['fundamental'],
  'fluxo-aprovacao-medio': ['medio'],
}

export function trajectoryStageCardKey(indicatorKey: string, stageKey?: string) {
  return stageKey ? `${indicatorKey}:${stageKey}` : indicatorKey
}

export function buildTrajectoryStageGroups(
  indicators: readonly EducationIndicatorResult[],
): TrajectoryStageGroup[] {
  const groups = new Map(
    TRAJECTORY_STAGES.map((stage) => [
      stage.key,
      { ...stage, items: [] as TrajectoryStageCard[] },
    ]),
  )

  indicators.forEach((indicator) => {
    const stageOptions = getStageOptions(indicator)
    const stageKeys = TRAJECTORY_STAGE_OVERRIDES[indicator.key]
      ?? (stageOptions.length ? stageOptions.map((option) => option.key) : inferStageKeys(indicator))

    stageKeys.forEach((stageKey) => {
      const group = groups.get(stageKey) ?? groups.get('contexto')
      if (!group) return
      const selectedStageKey = stageOptions.some((option) => option.key === stageKey) ? stageKey : ''
      group.items.push({
        cardKey: trajectoryStageCardKey(indicator.key, stageKey),
        indicator: selectedStageKey
          ? applyEducationIndicatorStageOption(indicator, selectedStageKey)
          : indicator,
        stageKey: selectedStageKey,
      })
    })
  })

  return TRAJECTORY_STAGES
    .map((stage) => groups.get(stage.key))
    .filter((group): group is TrajectoryStageGroup => Boolean(group?.items.length))
}

export function buildTrajectoryDetailSequence(
  indicators: readonly EducationIndicatorResult[],
): TrajectoryDetailSequenceItem[] {
  return buildTrajectoryStageGroups(indicators).flatMap((group) => group.items.map((item) => ({
    ...item.indicator,
    indicatorKey: item.indicator.key,
    key: item.cardKey,
    stageKey: item.stageKey,
  })))
}

function getStageOptions(indicator: EducationIndicatorResult) {
  if (!Array.isArray(indicator.stageFilterOptions)) return []
  return indicator.stageFilterOptions.filter(
    (option): option is { key: string } => Boolean(option)
      && typeof option === 'object'
      && typeof option.key === 'string',
  )
}

function inferStageKeys(indicator: EducationIndicatorResult) {
  const categories = Array.isArray(indicator.categories) ? indicator.categories : []
  if (categories.includes('medio')) return ['medio']
  if (categories.includes('fundamental')) return ['fundamental']
  return ['contexto']
}
