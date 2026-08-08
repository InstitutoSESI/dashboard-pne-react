import { ACTIVE_STATE_CONFIG } from './stateConfig'

export const STATE_PUBLICATION_SCHEMA_VERSION = 'state-publication-v2' as const

export type AnalyticsStatus = 'complete' | 'identity-only'

export interface PublicationConfig {
  schemaVersion: typeof STATE_PUBLICATION_SCHEMA_VERSION
  stateCode: string
  analyticsStatus: AnalyticsStatus
  analyticsMessage: string | null
}

declare const __ACTIVE_PUBLICATION_CONFIG__: unknown

const PUBLICATION_FIELDS = [
  'schemaVersion',
  'stateCode',
  'analyticsStatus',
  'analyticsMessage',
] as const

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
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
  if (payload.analyticsStatus !== 'complete' && payload.analyticsStatus !== 'identity-only') {
    throw new Error('Configuração de publicação possui analyticsStatus inválido.')
  }
  let analyticsMessage: string | null
  if (payload.analyticsStatus === 'complete') {
    if (payload.analyticsMessage !== null) {
      throw new Error('Publicação analítica completa deve usar analyticsMessage null.')
    }
    analyticsMessage = null
  } else {
    if (typeof payload.analyticsMessage !== 'string' || payload.analyticsMessage.trim() === '') {
      throw new Error('Publicação identity-only exige mensagem de indisponibilidade.')
    }
    analyticsMessage = payload.analyticsMessage
  }

  return Object.freeze({
    schemaVersion: STATE_PUBLICATION_SCHEMA_VERSION,
    stateCode: payload.stateCode,
    analyticsStatus: payload.analyticsStatus,
    analyticsMessage,
  })
}

export const ACTIVE_PUBLICATION_CONFIG = parsePublicationConfig(
  __ACTIVE_PUBLICATION_CONFIG__,
)

export const ANALYTICS_AVAILABLE = (
  ACTIVE_PUBLICATION_CONFIG.analyticsStatus === 'complete'
)
