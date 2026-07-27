import { normalizeRouteValue } from '../../app/appHash.js'
import {
  EDUCATION_SECTION_KEYS,
  getEducationThemeForIndicator,
  getEducationThemeForSection,
  resolveEducationNavigation,
} from '../../data/educationIndicatorCatalog.js'
import { resolveDetailSequence } from '../../hooks/detailNavigation.js'
import type {
  EducationIndicatorResult,
  EducationNavigationState,
  EducationSection,
  EducationSectionGroup,
} from './educationTypes'

const PANORAMA_THEME_KEYS = {
  matriculas: 'matriculas',
  escolasSistemaS: 'escolasSistemaS',
} as const

const LEGACY_EDUCATION_THEME_KEYS = [
  'matriculas',
  'rede',
  'turmas',
  'docentes',
  'fluxo',
  'aprendizagem',
  'oferta',
]

export function getInitialEducationNavigation(navigationContext: unknown): EducationNavigationState {
  const fallback: EducationNavigationState = {
    panoramaTheme: PANORAMA_THEME_KEYS.matriculas,
    section: EDUCATION_SECTION_KEYS.overview,
    detailKey: '',
    shouldApplyTheme: false,
  }
  const resolvedNavigation = resolveEducationNavigation(
    navigationContext as Parameters<typeof resolveEducationNavigation>[0],
  )
  if (!resolvedNavigation) return fallback

  const {
    detailKey,
    hasSystemTheme,
    requestedSection,
    requestedTheme,
    section,
  } = resolvedNavigation
  const themeValue = normalizeRouteValue(requestedTheme)
  const detailTheme = getEducationThemeForIndicator(detailKey)
  const legacyTheme = [...Object.values(PANORAMA_THEME_KEYS), ...LEGACY_EDUCATION_THEME_KEYS]
    .find((key) => normalizeRouteValue(key) === themeValue)

  let panoramaTheme = fallback.panoramaTheme
  if (hasSystemTheme) panoramaTheme = PANORAMA_THEME_KEYS.escolasSistemaS
  else if (detailTheme) panoramaTheme = detailTheme
  else if (legacyTheme) panoramaTheme = legacyTheme
  else if (requestedSection) panoramaTheme = getEducationThemeForSection(requestedSection) ?? panoramaTheme

  return {
    ...fallback,
    panoramaTheme,
    section: hasSystemTheme ? EDUCATION_SECTION_KEYS.modalities : section,
    detailKey,
    shouldApplyTheme: Boolean(detailKey || requestedSection || requestedTheme || hasSystemTheme),
  }
}

export function normalizeEducationSearch(value: string): string {
  return value.trim().toLocaleLowerCase('pt-BR')
}

export function filterEducationIndicators<T extends EducationIndicatorResult>(items: T[], searchQuery: string): T[] {
  const query = normalizeEducationSearch(searchQuery)
  if (!query) return items
  return items.filter((item) => [item.label, item.description, item.themeLabel, item.categoryLabel, item.searchText]
    .filter((value): value is string => typeof value === 'string')
    .join(' ')
    .toLocaleLowerCase('pt-BR')
    .includes(query))
}

export function selectEducationSectionItems<T extends EducationIndicatorResult>(
  items: T[],
  section: EducationSection | undefined,
): T[] {
  const itemsByKey = new Map(items.map((item) => [item.key, item]))
  return (section?.indicatorKeys ?? []).flatMap((key) => {
    const item = itemsByKey.get(key)
    return item ? [item] : []
  })
}

export function selectEducationVisibleGroups<T extends EducationIndicatorResult>(
  groups: EducationSectionGroup[],
  items: T[],
): Array<EducationSectionGroup & { items: T[] }> {
  const itemsByKey = new Map(items.map((item) => [item.key, item]))
  return groups
    .map((group) => ({
      ...group,
      items: group.indicatorKeys.flatMap((key) => {
        const item = itemsByKey.get(key)
        return item ? [item] : []
      }),
    }))
    .filter((group) => group.items.length > 0)
}

export function selectActiveEducationIndicator<T extends EducationIndicatorResult>(items: T[], key: string): T | null {
  return items.find((item) => item.key === key) ?? null
}

export function selectEducationDetailSequence<T extends EducationIndicatorResult>(items: T[], activeKey?: string) {
  return resolveDetailSequence(items, activeKey) as {
    activeIndex: number
    previousItem: T | null
    nextItem: T | null
  }
}

export function isEducationIndicatorAvailable(value: unknown): boolean {
  return value !== null && value !== undefined && value !== ''
}

export function sortEducationIndicators<T extends EducationIndicatorResult>(items: T[]): T[] {
  return [...items].sort((left, right) => left.label.localeCompare(right.label, 'pt-BR'))
}
