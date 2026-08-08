import { ACTIVE_MUNICIPALITY_ID_PATTERN } from '../config/stateConfig.js'

export const QSE_ANNUAL_SCHEMA_VERSION = 'qse-annual-v1' as const

export interface QseAnnualPoint {
  year: number
  distributedAmount: number
  enrollmentBasis: number | null
  distributionCoefficient: number | null
  distributedPerEnrollment: number | null
  sourceId: string
  sourceFileReference: string
  sourceFileSha256: string
  cutoffDate: string
}

export interface QseAnnualDocumentV1 {
  schemaVersion: typeof QSE_ANNUAL_SCHEMA_VERSION
  dataVersion: string
  indicatorId: 'qse.distributed_amount'
  municipality: {
    ibgeCode: string
    name: string
  }
  series: readonly QseAnnualPoint[]
}

export type QseAnnualLoadStatus = 'idle' | 'loading' | 'ready' | 'absent' | 'error'

export interface QseAnnualLoadState {
  status: QseAnnualLoadStatus
  data: QseAnnualDocumentV1 | null
}

type FetchLike = (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>

export class QseAnnualLoadError extends Error {
  readonly code: 'invalid_identifier' | 'absent' | 'http_error' | 'invalid_contract'

  constructor(code: QseAnnualLoadError['code'], message: string) {
    super(message)
    this.name = 'QseAnnualLoadError'
    this.code = code
  }
}

export const resolveQseAnnualPath = (ibgeCode: string): string => {
  const normalized = ibgeCode.trim()
  if (!ACTIVE_MUNICIPALITY_ID_PATTERN.test(normalized)) {
    throw new QseAnnualLoadError('invalid_identifier', 'Código municipal inválido.')
  }
  return `/data/municipios/${normalized}/qse-anual.json`
}

export const prepareQseAnnualSeries = (
  series: readonly QseAnnualPoint[],
  maximumPoints = 8,
): readonly QseAnnualPoint[] => {
  const byYear = new Map<number, QseAnnualPoint>()
  series.forEach((point) => {
    if (
      Number.isInteger(point.year)
      && Number.isFinite(point.distributedAmount)
      && point.distributedAmount >= 0
      && !byYear.has(point.year)
    ) {
      byYear.set(point.year, point)
    }
  })
  return [...byYear.values()]
    .sort((left, right) => left.year - right.year)
    .slice(-maximumPoints)
}

export const calculateQseAnnualVariation = (
  series: readonly QseAnnualPoint[],
): { current: QseAnnualPoint; previous: QseAnnualPoint; percentage: number | null } | null => {
  const ordered = prepareQseAnnualSeries(series)
  if (ordered.length < 2) return null
  const current = ordered[ordered.length - 1]
  const previous = ordered[ordered.length - 2]
  return {
    current,
    previous,
    percentage: previous.distributedAmount === 0
      ? null
      : ((current.distributedAmount - previous.distributedAmount) / previous.distributedAmount) * 100,
  }
}

const validatePoint = (point: unknown): point is QseAnnualPoint => {
  if (!point || typeof point !== 'object') return false
  const candidate = point as Partial<QseAnnualPoint>
  return Number.isInteger(candidate.year)
    && typeof candidate.distributedAmount === 'number'
    && Number.isFinite(candidate.distributedAmount)
    && candidate.distributedAmount >= 0
    && (candidate.enrollmentBasis === null || Number.isInteger(candidate.enrollmentBasis))
    && (candidate.distributionCoefficient === null || typeof candidate.distributionCoefficient === 'number')
    && (candidate.distributedPerEnrollment === null || typeof candidate.distributedPerEnrollment === 'number')
    && typeof candidate.sourceId === 'string'
    && typeof candidate.sourceFileReference === 'string'
    && typeof candidate.sourceFileSha256 === 'string'
    && typeof candidate.cutoffDate === 'string'
}

export const isQseAnnualDocument = (payload: unknown): payload is QseAnnualDocumentV1 => {
  if (!payload || typeof payload !== 'object') return false
  const candidate = payload as Partial<QseAnnualDocumentV1>
  if (
    candidate.schemaVersion !== QSE_ANNUAL_SCHEMA_VERSION
    || candidate.indicatorId !== 'qse.distributed_amount'
    || typeof candidate.dataVersion !== 'string'
    || !candidate.municipality
    || !ACTIVE_MUNICIPALITY_ID_PATTERN.test(candidate.municipality.ibgeCode)
    || !Array.isArray(candidate.series)
    || !candidate.series.every(validatePoint)
  ) return false
  const years = candidate.series.map((point) => point.year)
  return new Set(years).size === years.length
    && years.every((year, index) => index === 0 || years[index - 1] < year)
}

export const createQseAnnualLoader = (fetchImpl: FetchLike = fetch) => {
  const cache = new Map<string, Promise<QseAnnualDocumentV1>>()
  const states = new Map<string, QseAnnualLoadState>()

  const getState = (ibgeCode: string): QseAnnualLoadState => (
    states.get(ibgeCode) ?? { status: 'idle', data: null }
  )

  const load = (ibgeCode: string): Promise<QseAnnualDocumentV1> => {
    const path = resolveQseAnnualPath(ibgeCode)
    const cached = cache.get(ibgeCode)
    if (cached) return cached
    states.set(ibgeCode, { status: 'loading', data: null })
    const request = (async () => {
      try {
        const response = await fetchImpl(path)
        if (response.status === 404) throw new QseAnnualLoadError('absent', 'Histórico anual ausente.')
        if (!response.ok) throw new QseAnnualLoadError('http_error', 'Falha ao carregar o histórico anual.')
        const payload: unknown = await response.json()
        if (!isQseAnnualDocument(payload)) {
          throw new QseAnnualLoadError('invalid_contract', 'Histórico anual incompatível.')
        }
        states.set(ibgeCode, { status: 'ready', data: payload })
        return payload
      } catch (error) {
        cache.delete(ibgeCode)
        const normalized = error instanceof QseAnnualLoadError
          ? error
          : new QseAnnualLoadError('http_error', 'Falha ao carregar o histórico anual.')
        states.set(ibgeCode, {
          status: normalized.code === 'absent' ? 'absent' : 'error',
          data: null,
        })
        throw normalized
      }
    })()
    cache.set(ibgeCode, request)
    return request
  }

  return { load, getState }
}

export const qseAnnualLoader = createQseAnnualLoader()
