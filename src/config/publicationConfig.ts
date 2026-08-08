import {
  ANALYTICS_PRODUCTS,
  isAnalyticsProduct,
  isProductEnabledFor,
  type AnalyticsProduct,
} from './analyticsProducts'
import { ACTIVE_STATE_CONFIG } from './stateConfig'

export const STATE_PUBLICATION_SCHEMA_VERSION = 'state-publication-v3' as const

export type AnalyticsStatus = 'complete' | 'partial' | 'identity-only'

export interface PublicationConfig {
  schemaVersion: typeof STATE_PUBLICATION_SCHEMA_VERSION
  stateCode: string
  analyticsStatus: AnalyticsStatus
  analyticsMessage: string | null
  enabledProducts: readonly AnalyticsProduct[] | null
}

declare const __ACTIVE_PUBLICATION_CONFIG__: unknown

const PUBLICATION_FIELDS = [
  'schemaVersion',
  'stateCode',
  'analyticsStatus',
  'analyticsMessage',
  'enabledProducts',
] as const

const ANALYTICS_STATUSES: readonly AnalyticsStatus[] = ['complete', 'partial', 'identity-only']

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function isAnalyticsStatus(value: unknown): value is AnalyticsStatus {
  return typeof value === 'string' && (ANALYTICS_STATUSES as readonly string[]).includes(value)
}

function parseEnabledProducts(
  value: unknown,
  analyticsStatus: AnalyticsStatus,
): readonly AnalyticsProduct[] | null {
  if (analyticsStatus !== 'partial') {
    if (value !== null) {
      throw new Error(`Publicação ${analyticsStatus} deve declarar enabledProducts null.`)
    }
    return null
  }
  if (!Array.isArray(value) || value.length === 0) {
    throw new Error('Publicação parcial exige enabledProducts como lista não vazia.')
  }
  const products: AnalyticsProduct[] = []
  for (const item of value) {
    if (!isAnalyticsProduct(item)) {
      throw new Error('Publicação parcial declara produto analítico desconhecido.')
    }
    if (products.includes(item)) {
      throw new Error('Publicação parcial declara produto analítico duplicado.')
    }
    products.push(item)
  }
  if (products.length === ANALYTICS_PRODUCTS.length) {
    throw new Error('Publicação com todos os produtos deve declarar analyticsStatus complete.')
  }
  return Object.freeze(products)
}

export function parsePublicationConfig(payload: unknown): PublicationConfig {
  if (!isRecord(payload)) {
    throw new Error('Configuração de publicação ausente ou inválida.')
  }
  const actualFields = Object.keys(payload).sort()
  const expectedFields = [...PUBLICATION_FIELDS].sort()
  if (
    actualFields.length !== expectedFields.length
    || actualFields.some((field, index) => field !== expectedFields[index])
  ) {
    throw new Error('Configuração de publicação possui campos divergentes.')
  }
  if (payload.schemaVersion !== STATE_PUBLICATION_SCHEMA_VERSION) {
    throw new Error('Configuração de publicação possui schemaVersion desconhecido.')
  }
  if (payload.stateCode !== ACTIVE_STATE_CONFIG.stateCode) {
    throw new Error('Configuração de publicação diverge do estado ativo.')
  }
  if (!isAnalyticsStatus(payload.analyticsStatus)) {
    throw new Error('Configuração de publicação possui analyticsStatus inválido.')
  }
  const analyticsStatus = payload.analyticsStatus
  let analyticsMessage: string | null
  if (analyticsStatus === 'complete') {
    if (payload.analyticsMessage !== null) {
      throw new Error('Publicação analítica completa deve usar analyticsMessage null.')
    }
    analyticsMessage = null
  } else {
    if (typeof payload.analyticsMessage !== 'string' || payload.analyticsMessage.trim() === '') {
      throw new Error(`Publicação ${analyticsStatus} exige mensagem de indisponibilidade.`)
    }
    analyticsMessage = payload.analyticsMessage
  }
  const enabledProducts = parseEnabledProducts(payload.enabledProducts, analyticsStatus)

  return Object.freeze({
    schemaVersion: STATE_PUBLICATION_SCHEMA_VERSION,
    stateCode: payload.stateCode,
    analyticsStatus,
    analyticsMessage,
    enabledProducts,
  })
}

export const ACTIVE_PUBLICATION_CONFIG = parsePublicationConfig(
  __ACTIVE_PUBLICATION_CONFIG__,
)

/**
 * A moldura analítica (navegação, seletor, páginas de produto) só existe quando
 * há pelo menos um produto publicado. `identity-only` continua sem moldura.
 */
export const ANALYTICS_AVAILABLE = (
  ACTIVE_PUBLICATION_CONFIG.analyticsStatus === 'complete'
  || ACTIVE_PUBLICATION_CONFIG.analyticsStatus === 'partial'
)

export function isProductEnabled(
  product: AnalyticsProduct,
  publication: PublicationConfig = ACTIVE_PUBLICATION_CONFIG,
): boolean {
  return isProductEnabledFor(
    publication.analyticsStatus,
    publication.enabledProducts,
    product,
  )
}

export const ENABLED_PRODUCTS: readonly AnalyticsProduct[] = Object.freeze(
  ANALYTICS_PRODUCTS.filter((product) => isProductEnabled(product)),
)
