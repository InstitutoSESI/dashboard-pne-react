import { loadJson } from './staticData.js'
import { getSchoolInfrastructureContractFromDocument } from './schoolInfrastructureContract.js'

const educationCache = new Map()

function loadEducationJson(path, validate) {
  if (educationCache.has(path)) {
    return Promise.resolve(educationCache.get(path))
  }
  const promise = loadJson(path, validate)
    .then((data) => {
      educationCache.set(path, data)
      return data
    })
    .catch((error) => {
      if (educationCache.get(path) === promise) educationCache.delete(path)
      if (import.meta.env?.DEV) console.error(`[educationData] Falha ao validar/carregar ${path}`, error)
      throw error
    })
  educationCache.set(path, promise)
  return promise
}

export function loadEducationMunicipiosIndex() {
  return loadEducationJson('/data/educacao/municipios_index.json')
}

export function loadEducationMunicipio(idMunicipio) {
  if (!idMunicipio) return Promise.reject(new Error('id_municipio obrigatorio'))
  return loadEducationJson(
    `/data/educacao/municipios/${idMunicipio}.json`,
    getSchoolInfrastructureContractFromDocument,
  )
}
