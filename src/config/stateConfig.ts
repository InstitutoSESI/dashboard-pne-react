import type { StateCode } from '../types/data'

declare const __ACTIVE_STATE_CONFIG__: unknown

const STATE_CONFIG_SCHEMA_VERSION = 'state-config-v1'
const STATE_CONFIG_FIELDS = [
  'schemaVersion',
  'stateCode',
  'stateName',
  'stateNameForms',
  'municipalityIbgePrefix',
  'expectedMunicipalityCount',
  'locale',
] as const
const STATE_NAME_FORM_FIELDS = ['nominative', 'withDe', 'withCom'] as const

export interface StateNameForms {
  readonly nominative: string
  readonly withDe: string
  readonly withCom: string
}

export interface StateConfig {
  readonly schemaVersion: typeof STATE_CONFIG_SCHEMA_VERSION
  readonly stateCode: StateCode
  readonly stateName: string
  readonly stateNameForms: StateNameForms
  readonly municipalityIbgePrefix: string
  readonly expectedMunicipalityCount: number
  readonly locale: string
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function readNonEmptyString(
  config: Record<string, unknown>,
  field: string,
): string {
  const value = config[field]
  if (typeof value !== 'string' || value.trim() === '') {
    throw new Error(`Configuração estadual inválida: "${field}" deve ser texto não vazio.`)
  }
  return value
}

function assertExactFields(
  value: Record<string, unknown>,
  expectedFields: readonly string[],
  label: string,
): void {
  const actual = Object.keys(value).sort()
  const expected = [...expectedFields].sort()
  if (actual.length !== expected.length || actual.some((field, index) => field !== expected[index])) {
    throw new Error(
      `Configuração estadual inválida: campos de ${label} divergentes; esperados ${expected.join(', ')}.`,
    )
  }
}

function readStateNameForms(config: Record<string, unknown>): StateNameForms {
  const value = config.stateNameForms
  if (!isRecord(value)) {
    throw new Error('Configuração estadual inválida: "stateNameForms" deve ser um objeto.')
  }
  assertExactFields(value, STATE_NAME_FORM_FIELDS, 'stateNameForms')
  return Object.freeze({
    nominative: readNonEmptyString(value, 'nominative'),
    withDe: readNonEmptyString(value, 'withDe'),
    withCom: readNonEmptyString(value, 'withCom'),
  })
}

function validateLocale(locale: string): void {
  try {
    const canonical = Intl.getCanonicalLocales(locale)
    if (canonical.length !== 1 || Intl.DateTimeFormat.supportedLocalesOf(canonical).length !== 1) {
      throw new Error('locale não suportado')
    }
  } catch {
    throw new Error(`Configuração estadual inválida: locale "${locale}" não é válido.`)
  }
}

export function parseStateConfig(value: unknown): StateConfig {
  if (!isRecord(value)) {
    throw new Error('Configuração estadual inválida: o documento deve ser um objeto JSON.')
  }
  assertExactFields(value, STATE_CONFIG_FIELDS, 'stateConfig')

  const schemaVersion = readNonEmptyString(value, 'schemaVersion')
  if (schemaVersion !== STATE_CONFIG_SCHEMA_VERSION) {
    throw new Error(`Configuração estadual inválida: schemaVersion desconhecido "${schemaVersion}".`)
  }

  const stateCode = readNonEmptyString(value, 'stateCode')
  if (!/^[A-Z]{2}$/.test(stateCode)) {
    throw new Error('Configuração estadual inválida: "stateCode" deve conter duas letras maiúsculas.')
  }

  const stateName = readNonEmptyString(value, 'stateName')
  const stateNameForms = readStateNameForms(value)
  const municipalityIbgePrefix = readNonEmptyString(value, 'municipalityIbgePrefix')
  if (!/^\d{2}$/.test(municipalityIbgePrefix)) {
    throw new Error('Configuração estadual inválida: "municipalityIbgePrefix" deve conter dois dígitos.')
  }

  const expectedMunicipalityCount = value.expectedMunicipalityCount
  if (!Number.isInteger(expectedMunicipalityCount) || Number(expectedMunicipalityCount) <= 0) {
    throw new Error('Configuração estadual inválida: "expectedMunicipalityCount" deve ser inteiro positivo.')
  }

  const locale = readNonEmptyString(value, 'locale')
  validateLocale(locale)

  return Object.freeze({
    schemaVersion: STATE_CONFIG_SCHEMA_VERSION,
    stateCode,
    stateName,
    stateNameForms,
    municipalityIbgePrefix,
    expectedMunicipalityCount: Number(expectedMunicipalityCount),
    locale,
  })
}

function readInjectedActiveStateConfig(): unknown {
  if (typeof __ACTIVE_STATE_CONFIG__ === 'undefined') {
    throw new Error('Configuração estadual ativa não foi injetada pelo build.')
  }
  return __ACTIVE_STATE_CONFIG__
}

export const ACTIVE_STATE_CONFIG: StateConfig = parseStateConfig(readInjectedActiveStateConfig())

/**
 * Nome da plataforma. Por decisão de produto é idêntico em todos os estados: o
 * recorte estadual é comunicado pelo conteúdo, não pela marca.
 */
export const PLATFORM_LABEL = 'Painel SESI de Educação'

/**
 * Identificador municipal IBGE (7 dígitos) do estado ativo. Contratos de dados
 * municipais devem validar contra este padrão, nunca contra um prefixo fixo.
 */
export const ACTIVE_MUNICIPALITY_ID_PATTERN = new RegExp(
  `^${ACTIVE_STATE_CONFIG.municipalityIbgePrefix}\\d{5}$`,
)
