export type MunicipioName = string
export type MunicipalityId = string
export type StateCode = string

export interface MunicipalityRef {
  ibgeCode: MunicipalityId
  name: MunicipioName
  slug: string
  stateCode: StateCode
  path?: string
}

export interface MunicipalityIndexEntryPayload {
  nome: MunicipioName
  id_municipio: string
  slug: string
  path?: string
}

export interface MunicipiosIndexPayload {
  generated_at?: string
  total_municipios?: number
  municipios: MunicipalityIndexEntryPayload[]
}

export interface MunicipioData {
  id_municipio?: string
  municipio?: Record<string, unknown>
  [section: string]: unknown
}

export interface IndicadoresPayload {
  generated_at?: string
  cycles?: Record<string, unknown>
  [section: string]: unknown
}

export type InitialAppData =
  | {
      status: 'loading'
      error: null
      indicadores: null
      loading: true
      municipalities: MunicipalityRef[]
    }
  | {
      status: 'success'
      error: null
      indicadores: IndicadoresPayload
      loading: false
      municipalities: MunicipalityRef[]
    }
  | {
      status: 'error'
      error: string
      indicadores: null
      loading: false
      municipalities: MunicipalityRef[]
    }
