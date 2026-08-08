const fs = require('node:fs')
const path = require('node:path')

const REPO_ROOT = path.resolve(__dirname, '..', '..')

// O universo municipal e a versao metodologica saem da configuracao estadual
// ativa: nenhum numero de UF fica fixo neste verificador.
function parseArguments(argv) {
  const positional = []
  let stateCode = 'RS'
  for (let index = 0; index < argv.length; index += 1) {
    if (argv[index] === '--state') {
      const value = argv[index + 1]
      if (typeof value !== 'string' || !/^[A-Za-z]{2}$/.test(value.trim())) {
        throw new Error('--state exige uma UF textual com duas letras.')
      }
      stateCode = value.trim().toUpperCase()
      index += 1
      continue
    }
    positional.push(argv[index])
  }
  return { positional, stateCode }
}

function loadStateContract(stateCode) {
  const publicationPath = path.join(
    REPO_ROOT,
    'config',
    'publications',
    `${stateCode.toLowerCase()}.json`,
  )
  if (!fs.existsSync(publicationPath)) {
    throw new Error(`Publicação estadual ausente para ${stateCode}: ${publicationPath}.`)
  }
  const publication = JSON.parse(fs.readFileSync(publicationPath, 'utf8'))
  if (publication.stateCode !== stateCode) {
    throw new Error(`Publicação estadual diverge de ${stateCode}.`)
  }
  if (typeof publication.stateConfigPath !== 'string' || publication.stateConfigPath === '') {
    throw new Error(`Publicação estadual de ${stateCode} não declara stateConfigPath.`)
  }
  const stateConfig = JSON.parse(
    fs.readFileSync(path.join(REPO_ROOT, publication.stateConfigPath), 'utf8'),
  )
  if (stateConfig.stateCode !== stateCode) {
    throw new Error(`Configuração estadual diverge de ${stateCode}.`)
  }
  if (!Number.isInteger(stateConfig.expectedMunicipalityCount) || stateConfig.expectedMunicipalityCount <= 0) {
    throw new Error(`Configuração de ${stateCode} não declara expectedMunicipalityCount válido.`)
  }
  return {
    stateCode,
    publicDataDirectory: publication.publicDataDirectory,
    expectedMunicipalities: stateConfig.expectedMunicipalityCount,
  }
}

const { positional, stateCode } = parseArguments(process.argv.slice(2))
const stateContract = loadStateContract(stateCode)
const expectedMunicipalities = stateContract.expectedMunicipalities

const filePath = positional[0]
  ? path.resolve(positional[0])
  : path.join(
      REPO_ROOT,
      stateContract.publicDataDirectory,
      'pne_2026_2036',
      'referencia_estadual.json',
    )

const payload = JSON.parse(fs.readFileSync(filePath, 'utf8'))
const isClosedCycle = payload.cycle === 'pne_2014_2024'
const expectedMethodologyVersion = isClosedCycle
  ? `pne2014-${stateCode.toLowerCase()}-reference-v1`
  : `pne2026-${stateCode.toLowerCase()}-reference-v1`
const expectedRegistryCount = isClosedCycle ? 24 : 50
const requiredRegistryFields = [
  'indicator_id',
  'aggregation_method',
  'numerator_definition',
  'denominator_definition',
  'filters',
  'source',
  'source_type',
  'null_policy',
  'methodology_version',
  'comparison_status',
  'notes',
]
const requiredSeriesFields = [
  'indicator_id',
  'year',
  'value',
  'numerator',
  'denominator',
  'aggregation_method',
  'municipalities_valid',
  'municipalities_expected',
  'municipal_coverage_percent',
  'denominator_coverage_percent',
  'source',
  'source_type',
  'methodology_version',
  'comparison_status',
  'notes',
]
const blocked = new Set(
  Object.entries(payload.indicators)
    .filter(([, indicator]) => indicator.comparison_status === 'methodology_pending')
    .map(([indicatorId]) => indicatorId),
)

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

function isFiniteNumber(value) {
  return typeof value === 'number' && Number.isFinite(value)
}

assert(payload.municipalities_expected === expectedMunicipalities, `O universo estadual de ${stateCode} deve ter ${expectedMunicipalities} municípios.`)
assert(payload.methodology_version === expectedMethodologyVersion, `Versão metodológica incorreta; esperada ${expectedMethodologyVersion}.`)
assert(blocked.size > 0, 'O artefato deve registrar explicitamente pendências metodológicas.')
assert(Object.keys(payload.registry).length === expectedRegistryCount, `O registro deve conter ${expectedRegistryCount} indicadores.`)
assert(Object.keys(payload.indicators).length === expectedRegistryCount, `O artefato deve conter ${expectedRegistryCount} indicadores.`)
if (isClosedCycle) {
  assert(Array.isArray(payload.enabled_indicators), 'Lista de indicadores habilitados ausente.')
  assert(
    JSON.stringify(payload.unavailable_indicators) === JSON.stringify([
      'ensino_fundamental_ou_completo_pop_6_14',
      'ensino_medio_ou_basica_completa_pop_15_17',
    ]),
    'Indicadores sem referência estadual não estão documentados.',
  )
  assert(!Object.prototype.hasOwnProperty.call(payload.registry, 'medio_tecnico_articulado_percentual'), 'A nova chave não pode aparecer no ciclo encerrado.')
  assert(Object.prototype.hasOwnProperty.call(payload.registry, 'medio_tecnico'), 'O indicador legado deve permanecer no ciclo encerrado.')
} else {
  assert(Object.prototype.hasOwnProperty.call(payload.registry, 'medio_tecnico_articulado_percentual'), 'A nova chave ausente na referência do ciclo vigente.')
  assert(!Object.prototype.hasOwnProperty.call(payload.registry, 'medio_tecnico'), 'O indicador integrado-only legado não deve ser exposto na referência do ciclo vigente.')
}

for (const [indicatorId, registry] of Object.entries(payload.registry)) {
  for (const field of requiredRegistryFields) {
    assert(Object.prototype.hasOwnProperty.call(registry, field), `${indicatorId}: campo de registro ausente: ${field}`)
  }
  if (!isClosedCycle) {
    assert(registry.unit === 'percent', `${indicatorId}: unidade estadual incompatível.`)
    assert(registry.compatibility?.yearRule === 'same_year_required', `${indicatorId}: regra de ano ausente.`)
    assert(registry.compatibility?.formulaStatus === 'curated_equivalent', `${indicatorId}: compatibilidade de fórmula ausente.`)
    assert(registry.compatibility?.rangeStatus === 'curated_equivalent', `${indicatorId}: compatibilidade de faixa ausente.`)
    assert(registry.compatibility?.stageStatus === 'curated_equivalent', `${indicatorId}: compatibilidade de etapa ausente.`)
    assert(registry.compatibility?.universeStatus === 'curated_equivalent', `${indicatorId}: compatibilidade de universo ausente.`)
    assert(registry.compatibility?.administrativeDependenceStatus === 'registry_filters_required', `${indicatorId}: dependência administrativa ausente.`)
    assert(registry.compatibility?.aggregationRuleStatus === 'curated_equivalent', `${indicatorId}: regra de agregação ausente.`)
    assert(registry.compatibility?.territorialBasisStatus === 'curated_equivalent', `${indicatorId}: base territorial ausente.`)
  }
  const indicator = payload.indicators[indicatorId]
  assert(indicator, `${indicatorId}: indicador ausente.`)
  if (blocked.has(indicatorId)) {
    assert(indicator.comparison_status === 'methodology_pending', `${indicatorId}: bloqueio ausente.`)
    assert(indicator.series.length === 0, `${indicatorId}: indicador bloqueado não pode ter série.`)
    continue
  }

  if (indicator.comparison_status === 'unavailable') {
    assert(indicator.series.length === 0, `${indicatorId}: indicador sem referência não pode ter série.`)
    continue
  }

  const years = new Set()
  for (const record of indicator.series) {
    for (const field of requiredSeriesFields) {
      assert(Object.prototype.hasOwnProperty.call(record, field), `${indicatorId}: campo de série ausente: ${field}`)
    }
    assert(!years.has(record.year), `${indicatorId}: ano duplicado: ${record.year}`)
    years.add(record.year)
    assert(record.municipalities_expected === expectedMunicipalities, `${indicatorId}: universo anual incorreto; esperado ${expectedMunicipalities}.`)
    assert(record.numerator === null || record.denominator !== null, `${indicatorId}/${record.year}: numerador sem denominador.`)
    if (record.aggregation_method === 'ratio_of_sums' && isFiniteNumber(record.value)) {
      assert(isFiniteNumber(record.numerator) && isFiniteNumber(record.denominator) && record.denominator > 0, `${indicatorId}/${record.year}: razão inválida.`)
      const expected = 100 * record.numerator / record.denominator
      assert(Math.abs(expected - record.value) < 1e-9, `${indicatorId}/${record.year}: razão não é de somas.`)
    }
  }
}

if (isClosedCycle) {
  assert(!payload.projections || Object.keys(payload.projections).length === 0, 'O ciclo encerrado não pode conter projeções.')
} else {
  assert(payload.projections.creche.source.includes('sem média municipal'), 'Projeção estadual não declara sua fonte agregada.')
  assert(payload.projections.alfabetizacao_pop_15_mais.projection_status === 'not_applicable', 'Censo não pode ser projetado.')
  const articulated = payload.indicators.medio_tecnico_articulado_percentual
  assert(articulated, 'Série estadual do indicador aproximado ausente.')
  assert(articulated.series.every((record) => record.year >= 2015 && record.year <= 2025), 'A série estadual aproximada deve ficar entre 2015 e 2025.')
  assert(payload.projections.medio_tecnico_articulado_percentual?.projection_status === 'not_applicable', 'O indicador aproximado não pode ter projeção.')
}

console.log(`Referência estadual válida: ${filePath}`)
console.log(`Indicadores: ${Object.keys(payload.indicators).length}; municípios esperados: ${payload.municipalities_expected}`)
console.log(`Comparáveis: ${Object.values(payload.indicators).filter((indicator) => indicator.comparison_status === 'comparable').length}; pendentes: ${blocked.size}`)
