import type { PmeDataState } from './pmeTypes'

export const PME_DATA_LABELS: Record<PmeDataState, string> = {
  observed: 'Observação disponível',
  null: 'Valor nulo na publicação',
  unavailable: 'Indisponível na fonte',
  suppressed: 'Dado suprimido',
  not_applicable: 'Não aplicável',
  not_loaded: 'Observação ainda não carregada',
  not_published: 'Relação sem observação publicada',
}

export function formatPmeValue(value: number | null, unit: string | null): string {
  if (value === null) return '—'
  const formatted = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: unit === 'count' ? 0 : unit === 'percent' ? 1 : 2 }).format(value)
  return unit === 'percent' ? `${formatted}%` : unit === 'years' ? `${formatted} anos` : formatted
}

export const PME_UNIVERSE_LABELS: Record<string, string> = {
  school_location_over_resident_population: 'Matrículas pela localização da escola / população residente estimada',
  resident_population: 'População residente no município',
  school_location: 'Escolas localizadas no município',
  institution_location: 'Instituições localizadas no município',
  municipality: 'Recorte municipal definido na metodologia do indicador',
}
