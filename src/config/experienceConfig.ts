import type { StateCode } from '../types/data'

declare const __ACTIVE_EXPERIENCE_CONFIG__: unknown

export const EXPERIENCE_CONFIG_SCHEMA_VERSION = 'experience-config-v1' as const
export const PLATFORM_EXPERIENCES = ['atual', 'pme'] as const

export type PlatformExperience = typeof PLATFORM_EXPERIENCES[number]

export interface ExperienceConfig {
  readonly schemaVersion: typeof EXPERIENCE_CONFIG_SCHEMA_VERSION
  readonly stateCode: StateCode
  readonly experience: PlatformExperience
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

export function parseExperienceConfig(value: unknown): ExperienceConfig {
  if (!isRecord(value)) {
    throw new Error('Configuração da experiência inválida: o documento deve ser um objeto.')
  }
  const expectedFields = ['experience', 'schemaVersion', 'stateCode']
  const actualFields = Object.keys(value).sort()
  if (
    actualFields.length !== expectedFields.length
    || actualFields.some((field, index) => field !== expectedFields[index])
  ) {
    throw new Error('Configuração da experiência inválida: campos divergentes.')
  }
  if (value.schemaVersion !== EXPERIENCE_CONFIG_SCHEMA_VERSION) {
    throw new Error('Configuração da experiência inválida: schemaVersion desconhecido.')
  }
  if (typeof value.stateCode !== 'string' || !/^[A-Z]{2}$/.test(value.stateCode)) {
    throw new Error('Configuração da experiência inválida: stateCode deve conter duas letras maiúsculas.')
  }
  if (
    typeof value.experience !== 'string'
    || !PLATFORM_EXPERIENCES.includes(value.experience as PlatformExperience)
  ) {
    throw new Error('Configuração da experiência inválida: experiência desconhecida.')
  }
  if (value.experience === 'pme' && value.stateCode !== 'RS') {
    throw new Error('Configuração da experiência inválida: PME está disponível somente para RS.')
  }

  return Object.freeze({
    schemaVersion: EXPERIENCE_CONFIG_SCHEMA_VERSION,
    stateCode: value.stateCode as StateCode,
    experience: value.experience as PlatformExperience,
  })
}

export const ACTIVE_EXPERIENCE_CONFIG = parseExperienceConfig(__ACTIVE_EXPERIENCE_CONFIG__)
