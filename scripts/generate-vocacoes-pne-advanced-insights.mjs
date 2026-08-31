#!/usr/bin/env node
import {
  checkVocacoesPneAdvancedPublication,
  promoteVocacoesPneAdvancedPublication,
} from './lib/vocacoes-pne-advanced-publication.mjs'

const checkOnly = process.argv.slice(2).includes('--check')
const result = checkOnly
  ? await checkVocacoesPneAdvancedPublication()
  : await promoteVocacoesPneAdvancedPublication()

console.log(JSON.stringify({
  state: checkOnly ? 'AA5_GENERATED_OUTPUTS_MATCH' : 'AA5_GENERATED_OUTPUTS_PROMOTED',
  bundleSha256: result.registry.bundleSha256,
  bundleByteSize: result.registry.bundleByteSize,
  readingCount: result.registry.readingCount,
  agendaCount: result.registry.agendaCount,
  municipalityCount: result.registry.canonicalMunicipalityCount,
}, null, 2))
