import type {
  BreakdownValue,
  MunicipalEducationOverviewV1,
  SnapshotPercentage,
  SnapshotValue,
} from './municipalEducationOverviewTypes'

type DisplayValue = Pick<SnapshotValue | SnapshotPercentage, 'state' | 'value'>

const numberFormatter = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 0 })
const percentageFormatter = new Intl.NumberFormat('pt-BR', {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
})

function hasPublicValue(value: DisplayValue): value is DisplayValue & { value: number } {
  return (value.state === 'observed' || value.state === 'derived_zero')
    && typeof value.value === 'number'
    && Number.isFinite(value.value)
}

/*
 * Valor numerico para uso em visualizacao (barra de proporcao).
 *
 * Devolve null sempre que o dado nao for publicavel. Isso e deliberado: zero
 * observado e um dado ("nenhuma matricula nesta rede"), enquanto ausente e
 * nao aplicavel nao sao. Tratar os tres como 0 desenharia uma barra que afirma
 * algo que a fonte nao diz.
 */
export function getOverviewNumericValue(value: DisplayValue | undefined): number | null {
  if (!value) return null
  return hasPublicValue(value) ? value.value : null
}

export function formatOverviewEnrollments(value: DisplayValue): string {
  return hasPublicValue(value) ? numberFormatter.format(value.value) : '—'
}

export function formatOverviewPercentage(value: SnapshotPercentage | undefined): string {
  return value && hasPublicValue(value) ? `${percentageFormatter.format(value.value)}%` : '—'
}

export function formatSchoolPerformanceRate(value: SnapshotValue): string {
  return hasPublicValue(value) ? `${percentageFormatter.format(value.value)}%` : '—'
}

export function describeOverviewMatrixValue(value: BreakdownValue): string {
  const enrollments = formatOverviewEnrollments(value.enrollments)
  if (enrollments === '—') return 'Indisponível'
  const percentage = formatOverviewPercentage(value.share)
  return percentage === '—'
    ? `${enrollments} matrículas; participação indisponível`
    : `${enrollments} matrículas; ${percentage} de participação`
}

export function getMunicipalOverviewMethodologyHighlights(data: MunicipalEducationOverviewV1): string[] {
  const notes = [...data.universe.methodologyNotes, ...data.methodology].join(' ').toLocaleLowerCase('pt-BR')
  const highlights: string[] = []

  if (notes.includes('2025')) highlights.push('O retrato considera exclusivamente as matrículas de 2025.')
  if (notes.includes('localiza')) highlights.push('Os recortes urbana e rural se referem à localização da escola.')
  if (notes.includes('educação básica') || notes.includes('educacao básica')) {
    highlights.push('O total da Educação Básica segue o dado oficial do Censo Escolar.')
  }

  return highlights
}
