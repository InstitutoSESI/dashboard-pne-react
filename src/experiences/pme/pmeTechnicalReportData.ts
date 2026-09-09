import {
  SCHOOL_INFRASTRUCTURE_CONTRACT_VERSION,
  type SchoolInfrastructureContract,
} from '../../data/schoolInfrastructureContract'
import {
  buildEducationModel,
  buildPneComplementaryTheme,
} from '../../features/education/educationViewModels'
import { isSpecialEducationIndicatorId } from '../../features/education/specialEducationTypes'
import type { IndicadoresPayload, MunicipioData } from '../../types/data'
import type { EducationMunicipioData } from '../../features/education/educationTypes'
import type { HigherEducationMunicipalDocument } from '../../features/education/higherEducationTypes'
import type { MunicipalEducationOverviewV1 } from '../../features/education/municipalEducationOverviewTypes'
import type { SpecialEducationMunicipalDocument } from '../../features/education/specialEducationTypes'
import type { Pne2026DiagnosticLoaderResult } from '../../features/diagnostic/diagnosticTypes'
import type { PmeMunicipalityIdentity } from './pmeTypes'

interface PmeMunicipioData extends MunicipioData {
  pne_2026_2036?: {
    cenarios_planejamento?: Record<string, unknown>
    indicadores?: Record<string, unknown>
    projecoes?: Record<string, unknown>
  }
}

export interface PmeTechnicalReportDataInput {
  education: EducationMunicipioData
  indicadores: IndicadoresPayload
  municipioData: PmeMunicipioData
  specialEducationItems: Array<{ key: string; [property: string]: unknown }>
}

/** Undefined requests the local loader; null is an explicit unavailable module. */
export function resolvePmeTechnicalReportDiagnostic(
  diagnostic: Pne2026DiagnosticLoaderResult | null | undefined,
  loadedDiagnostic: Pne2026DiagnosticLoaderResult | null,
): Pne2026DiagnosticLoaderResult | null {
  return diagnostic === undefined ? loadedDiagnostic : diagnostic
}

export function validatePmeTechnicalReportIdentity({
  diagnostic,
  education,
  higherEducation,
  municipioData,
  municipality,
  overview,
  specialEducation,
}: {
  diagnostic?: Pne2026DiagnosticLoaderResult | null
  education: EducationMunicipioData
  higherEducation?: HigherEducationMunicipalDocument | null
  municipioData: PmeMunicipioData
  municipality: PmeMunicipalityIdentity
  overview?: MunicipalEducationOverviewV1 | null
  specialEducation?: SpecialEducationMunicipalDocument | null
}): string | null {
  const { ibgeCode, name } = municipality
  const educationMunicipalityName = typeof education.municipio === 'string' ? education.municipio : null
  if (education.id_municipio !== ibgeCode || educationMunicipalityName !== name) {
    return 'A base de indicadores educacionais não corresponde ao município selecionado.'
  }
  if (municipioData.id_municipio !== ibgeCode) {
    return 'A base municipal do PNE não corresponde ao município selecionado.'
  }
  if (overview && (overview.municipality.idMunicipality !== ibgeCode || overview.municipality.name !== name)) {
    return 'O panorama educacional não corresponde ao município selecionado.'
  }
  if (higherEducation && (higherEducation.municipality.id !== ibgeCode || higherEducation.municipality.name !== name)) {
    return 'A base de Educação Superior não corresponde ao município selecionado.'
  }
  if (specialEducation && (
    specialEducation.municipality.code !== ibgeCode
    || specialEducation.municipality.name !== name
  )) {
    return 'A base de Educação Especial não corresponde ao município selecionado.'
  }
  if (diagnostic && (diagnostic.municipalityId !== ibgeCode || diagnostic.municipalityName !== name)) {
    return 'O diagnóstico do PNE não corresponde ao município selecionado.'
  }
  return null
}

/** Keeps the PME report's data composition equal to the established Education report. */
export function buildPmeTechnicalReportData({
  education,
  indicadores,
  municipioData,
  specialEducationItems,
}: PmeTechnicalReportDataInput) {
  const model = buildEducationModel(education.blocos ?? {})
  const schoolInfrastructure = education.blocos?.rede_escolar?.infraestrutura?.contractVersion
    === SCHOOL_INFRASTRUCTURE_CONTRACT_VERSION
    ? education.blocos.rede_escolar.infraestrutura as SchoolInfrastructureContract
    : null
  const pneComplementaryTheme = buildPneComplementaryTheme({
    indicadores,
    rede: education.blocos?.rede_escolar,
    results: municipioData.pne_2026_2036?.indicadores,
  })

  return {
    educationItems: [
      ...model.items,
      ...(pneComplementaryTheme?.items ?? []).filter((item) => !isSpecialEducationIndicatorId(item.key)),
      ...specialEducationItems,
    ],
    municipalityPopulation: municipioData.municipio?.populacao
      ?? municipioData.municipio?.population
      ?? municipioData.municipio?.populacao_total,
    pmeReferenceData: {
      planningScenarios: municipioData.pne_2026_2036?.cenarios_planejamento,
      projections: municipioData.pne_2026_2036?.projecoes,
    },
    schoolInfrastructure,
  }
}
