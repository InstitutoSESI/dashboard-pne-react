export type MunicipioName = string

export interface MunicipioIndexEntry {
  nome: MunicipioName
  id_municipio: string
  slug: string
  path?: string
}

export interface MunicipiosIndexPayload {
  generated_at?: string
  total_municipios?: number
  municipios: MunicipioIndexEntry[]
}

export interface MunicipioData {
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
      municipios: MunicipioName[]
      municipiosIndex: MunicipioIndexEntry[]
    }
  | {
      status: 'success'
      error: null
      indicadores: IndicadoresPayload
      loading: false
      municipios: MunicipioName[]
      municipiosIndex: MunicipioIndexEntry[]
    }
  | {
      status: 'error'
      error: string
      indicadores: null
      loading: false
      municipios: MunicipioName[]
      municipiosIndex: MunicipioIndexEntry[]
    }
