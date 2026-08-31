#!/usr/bin/env node
import {
  checkCenariosEducacaoPublication,
  promoteCenariosEducacaoPublication,
} from './lib/cenarios-educacao-publication.mjs'

const checkOnly = process.argv.slice(2).includes('--check')
const result = checkOnly
  ? await checkCenariosEducacaoPublication()
  : await promoteCenariosEducacaoPublication()

console.log(JSON.stringify({
  state: checkOnly ? 'EDUCATION_SCENARIOS_OUTPUTS_MATCH' : 'EDUCATION_SCENARIOS_OUTPUTS_PROMOTED',
  publicationStatus: result.registry.publicationStatus,
  bundleSha256: result.registry.bundleSha256,
  bundleByteSize: result.registry.bundleByteSize,
  scenarioCount: result.registry.scenarioCount,
  factorCount: result.registry.factorCount,
  domainCount: result.registry.domainCount,
  minimumPairwiseHammingDistance: result.registry.minimumPairwiseHammingDistance,
  regionalMunicipalityCount: result.registry.regionalMunicipalityCount,
  focalMunicipalityIbgeCode: result.registry.focalMunicipalityIbgeCode,
  publicDataValidationStatus: result.registry.publicDataValidationStatus,
  diagnosticDuplicateCount: result.registry.diagnosticDuplicateCount,
  regionalPublicInputsSha256: result.registry.regionalPublicInputsSha256,
}, null, 2))
