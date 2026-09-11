import registry from '../../../config/municipalities/rs.json'
import { createPne2026DiagnosticLoader } from '../../features/diagnostic/pne2026DiagnosticLoader.js'
import { createPne2026MatrizLoader } from '../../features/matriz/pne2026MatrizLoader.js'
import { buildPmeMunicipalModel, toPmeDiagnosticError, toPmeMatrizError } from './pmePresentation'
import type {
  PmeDiagnosticModuleState,
  PmeMatrizModuleState,
  PmeMatrizLoaderResult,
  PmeMunicipalityIdentity,
  PmeMunicipalModel,
} from './pmeTypes'

const RS_MUNICIPALITIES = registry.municipalities
const municipalityByIbgeCode = new Map(
  RS_MUNICIPALITIES.map((municipality) => [municipality.ibgeCode, municipality]),
)

if (RS_MUNICIPALITIES.length !== 497) {
  throw new Error('O cadastro canônico do RS deve conter 497 municípios para o carregador PME.')
}

export function resolvePmeMunicipality(ibgeCode: string): PmeMunicipalityIdentity | null {
  const municipality = municipalityByIbgeCode.get(ibgeCode)
  return municipality ? { ...municipality, stateCode: 'RS' } : null
}

export async function loadPmeMatrizOptional(
  loadMatriz: (municipalityId: string) => Promise<unknown>,
  municipalityId: string,
): Promise<PmeMatrizModuleState> {
  try {
    return { status: 'available', value: await loadMatriz(municipalityId) as PmeMatrizLoaderResult }
  } catch (error) {
    if (error && typeof error === 'object' && (error as { code?: unknown }).code === 'municipality_not_published') {
      return { status: 'not_published' }
    }
    return toPmeMatrizError(error)
  }
}

export async function loadPmeDiagnosticOptional(
  loadDiagnostic: (municipalityId: string) => Promise<unknown>,
  municipalityId: string,
): Promise<PmeDiagnosticModuleState> {
  try {
    return { status: 'available', value: await loadDiagnostic(municipalityId) as import('../../features/diagnostic/diagnosticTypes').Pne2026DiagnosticLoaderResult }
  } catch (error) {
    return toPmeDiagnosticError(error)
  }
}

export interface PmeMunicipalLoader {
  /** Emits a complete, internally consistent model as each independent module settles. */
  load: (ibgeCode: string, onUpdate?: (model: PmeMunicipalModel) => void) => Promise<PmeMunicipalModel>
}

function diagnosticForMunicipality(
  state: PmeDiagnosticModuleState,
  municipality: PmeMunicipalityIdentity,
): PmeDiagnosticModuleState {
  if (state.status !== 'available') return state
  if (state.value.municipalityId === municipality.ibgeCode) return state
  return {
    status: 'error',
    error: {
      code: 'diagnostic_municipality_mismatch',
      message: 'O diagnóstico carregado não corresponde ao município selecionado.',
      stage: 'identity_validation',
    },
  }
}

function matrizForMunicipality(
  state: PmeMatrizModuleState,
  municipality: PmeMunicipalityIdentity,
): PmeMatrizModuleState {
  if (state.status !== 'available') return state
  const { value } = state
  if (
    value.municipalityId === municipality.ibgeCode
    && value.matriz.municipality.ibge7 === municipality.ibgeCode
    && value.matriz.municipality.uf === municipality.stateCode
  ) return state
  return {
    status: 'error',
    error: {
      code: 'matriz_municipality_mismatch',
      message: 'A Matriz carregada não corresponde ao município selecionado.',
      stage: 'identity_validation',
    },
  }
}

export function createPmeMunicipalLoader({
  loadDiagnostic = createPne2026DiagnosticLoader({ expectedMunicipalityCount: RS_MUNICIPALITIES.length }).load,
  loadMatriz = createPne2026MatrizLoader().load,
}: {
  loadDiagnostic?: (municipalityId: string) => Promise<unknown>
  loadMatriz?: (municipalityId: string) => Promise<unknown>
} = {}): PmeMunicipalLoader {
  return {
    async load(ibgeCode: string, onUpdate?: (model: PmeMunicipalModel) => void): Promise<PmeMunicipalModel> {
      const municipality = resolvePmeMunicipality(ibgeCode)
      if (!municipality) throw new TypeError('O PME requer um código IBGE textual pertencente ao cadastro canônico do RS.')
      let diagnostic: PmeDiagnosticModuleState = { status: 'not_loaded' }
      let matriz: PmeMatrizModuleState = { status: 'not_loaded' }
      const emit = () => onUpdate?.(buildPmeMunicipalModel({ municipality, diagnostic, matriz }))
      emit()
      const diagnosticTask = loadPmeDiagnosticOptional(loadDiagnostic, municipality.ibgeCode).then((result) => {
        diagnostic = diagnosticForMunicipality(result, municipality)
        emit()
      })
      const matrizTask = loadPmeMatrizOptional(loadMatriz, municipality.ibgeCode).then((result) => {
        matriz = matrizForMunicipality(result, municipality)
        emit()
      })
      await Promise.all([diagnosticTask, matrizTask])
      return buildPmeMunicipalModel({ municipality, diagnostic, matriz })
    },
  }
}
