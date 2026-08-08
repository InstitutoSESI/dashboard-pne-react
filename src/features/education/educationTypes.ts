import type {
  IndicadoresPayload,
  MunicipalityId,
  MunicipioData,
  MunicipioName,
} from '../../types/data'
import type { ParsedAppLocation } from '../../types/navigation'
import type { EducationAttendancePayload } from './educationAttendanceTypes'
import type { SchoolInfrastructureContract } from '../../data/schoolInfrastructureContract'

export type EducationSectionKey = string
export type EducationIndicatorKey = string
export type EducationThemeKey = string

export interface EducationIndicatorCatalogItem {
  key: EducationIndicatorKey
  section?: EducationSectionKey
  sections?: EducationSectionKey[]
  label?: string
  description?: string
  themeKey?: EducationThemeKey
}

export interface EducationIndicatorResult {
  key: EducationIndicatorKey
  label: string
  description?: string
  themeLabel?: string
  categoryLabel?: string
  searchText?: string
  [property: string]: unknown
}

export interface EducationSection {
  key: EducationSectionKey
  label?: string
  question?: string
  description?: string
  indicatorKeys?: EducationIndicatorKey[]
  indicatorCount?: number
  navigableContentCount?: number
}

export interface EducationSectionGroup {
  key?: string
  label?: string
  question?: string
  description?: string
  indicatorKeys: EducationIndicatorKey[]
  indicatorCount?: number
  [property: string]: unknown
}

export interface EducationNavigationState {
  panoramaTheme: EducationThemeKey
  section: EducationSectionKey
  detailKey: EducationIndicatorKey
  shouldApplyTheme: boolean
}

export interface EducationPneContext {
  cenarios_planejamento?: Record<string, unknown>
  indicadores?: Record<string, unknown>
  projecoes?: Record<string, unknown>
}

export interface EducationMunicipioData extends MunicipioData {
  blocos?: {
    rede_escolar?: {
      infraestrutura?: SchoolInfrastructureContract & Record<string, unknown>
      [property: string]: unknown
    }
    [property: string]: unknown
  }
  educacao?: {
    atendimento_cenarios?: EducationAttendancePayload
  }
  pne_2026_2036?: EducationPneContext
}

export interface EducationPageProps {
  indicadores: IndicadoresPayload
  municipioData?: EducationMunicipioData | null
  municipalityId: MunicipalityId
  municipalitySlug?: string | null
  navigationContext: ParsedAppLocation
  selectedMunicipio: MunicipioName
}
