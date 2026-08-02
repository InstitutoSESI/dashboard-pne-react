import type { MunicipalityRef } from '../types/data'

export function normalizeMunicipalitySearchText(value: unknown, locale: string): string {
  return String(value ?? '')
    .normalize('NFD')
    .replace(/\p{Diacritic}/gu, '')
    .toLocaleLowerCase(locale)
    .trim()
}

export function sortMunicipalitiesByName(
  municipalities: readonly MunicipalityRef[],
  locale: string,
): MunicipalityRef[] {
  return [...municipalities].sort((left, right) => (
    left.name.localeCompare(right.name, locale, { sensitivity: 'base' })
    || left.ibgeCode.localeCompare(right.ibgeCode)
  ))
}

export function filterMunicipalitiesByName(
  municipalities: readonly MunicipalityRef[],
  query: string,
  locale: string,
): MunicipalityRef[] {
  const normalizedQuery = normalizeMunicipalitySearchText(query, locale)
  return normalizedQuery
    ? municipalities.filter((municipality) => (
        normalizeMunicipalitySearchText(municipality.name, locale).includes(normalizedQuery)
      ))
    : [...municipalities]
}
