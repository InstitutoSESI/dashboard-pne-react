import {
  lintCard,
  serializePublic,
  validateCardContract,
} from './vocacoes-pne-linter.mjs'
import {
  validateCardCatalog,
  validatePair,
} from './vocacoes-pne-compatibilidade.mjs'

export const GATE_IDS = Object.freeze(
  Array.from({ length: 10 }, (_, index) => `G${index + 1}`),
)

const RESEARCH_SCHEMA = 'vocacoes-pne-r6-engine-v1'
const AUTHORSHIP_SCHEMA = 'vocacoes-pne-r6-authorship-v1'
const OUTPUT_SCHEMA = 'vocacoes-pne-segunda-saida-v1'
const CONTRACT_VERSION = '1.4.0'
const RESEARCH_FIXTURE_PATH = (
  'scripts/checks/fixtures/vocacoes-pne/segunda-saida-pesquisa-vale-do-sinos.json'
)
const BUILDER_VERSION = 'generate-vocacoes-pne-segunda-saida.mjs v1.0.0'
const PUBLIC_KEYS = new Set([
  'id',
  'direction',
  'title',
  'territorial_transformation',
  'territorial_facts',
  'education_starting_point',
  'exposed_groups_or_municipalities',
  'education_agenda',
  'pne_topics',
  'monitoring_indicators',
  'horizon',
  'sources',
])
const REQUIRED_NARRATIVE_PATHS = [
  'title',
  'territorial_transformation',
  'education_starting_point',
  'exposed_groups_or_municipalities',
  'education_agenda',
]
const FUTURE_BASIS_KEYS = new Set([
  'basisType',
  'seriesIds',
  'observedPeriod',
  'supportsTrend',
  'scenarioId',
  'futureNumericValues',
  'claimBoundary',
])

export class SegundaSaidaError extends Error {}

function fail(message) {
  throw new SegundaSaidaError(message)
}

function isRecord(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
}

function isNonEmptyString(value) {
  return typeof value === 'string' && value.trim().length > 0
}

function isFiniteNumber(value) {
  return typeof value === 'number' && Number.isFinite(value)
}

function nearlyEqual(left, right, tolerance = 1e-8) {
  return isFiniteNumber(left)
    && isFiniteNumber(right)
    && Math.abs(left - right) <= tolerance
}

function assertExactKeys(value, keys, field) {
  if (!isRecord(value)) fail(`${field} deve ser objeto`)
  const observed = Object.keys(value).sort()
  const expected = [...keys].sort()
  if (JSON.stringify(observed) !== JSON.stringify(expected)) {
    fail(`${field} tem chaves divergentes: ${JSON.stringify(observed)}`)
  }
}

function assertStringArray(value, field, { allowEmpty = false } = {}) {
  if (
    !Array.isArray(value)
    || (!allowEmpty && value.length === 0)
    || value.some((item) => !isNonEmptyString(item))
    || new Set(value).size !== value.length
  ) {
    fail(`${field} deve conter strings únicas${allowEmpty ? '' : ' e não pode ser vazio'}`)
  }
}

function compareSets(left, right) {
  return (
    left.size === right.size
    && [...left].every((item) => right.has(item))
  )
}

function factById(candidate, id) {
  return candidate.facts.find((fact) => fact.id === id)
}

function collectFactIds(candidate) {
  return new Set(candidate.facts.map(({ id }) => id))
}

function validateFact(fact, sourceIds, candidateId) {
  if (!isRecord(fact)) fail(`${candidateId}: fato inválido`)
  for (const field of ['id', 'kind', 'seriesId', 'unit', 'sourceId']) {
    if (!isNonEmptyString(fact[field])) fail(`${candidateId}: fato sem ${field}`)
  }
  if (!fact.id.startsWith(`${candidateId}.`)) {
    fail(`${candidateId}: fato fora do namespace: ${fact.id}`)
  }
  if (
    !isRecord(fact.period)
    || !Number.isInteger(fact.period.start)
    || !Number.isInteger(fact.period.end)
    || fact.period.start > fact.period.end
    || !isRecord(fact.values)
  ) {
    fail(`${candidateId}: fato ${fact.id} sem período/valores estruturados`)
  }
  if (!sourceIds.has(fact.sourceId)) {
    fail(`${candidateId}: sourceId desconhecido em ${fact.id}`)
  }
}

function validateGateMap(gates, candidateId, factIds) {
  assertExactKeys(gates, GATE_IDS, `${candidateId}.gates`)
  for (const gateId of GATE_IDS) {
    const gate = gates[gateId]
    if (
      !isRecord(gate)
      || !['ok', 'reprovado', 'pendente_autoria', 'nao_avaliado'].includes(gate.status)
      || !isNonEmptyString(gate.reasonCode)
      || !Array.isArray(gate.evidenceFactIds)
      || gate.evidenceFactIds.some((factId) => !factIds.has(factId))
      || new Set(gate.evidenceFactIds).size !== gate.evidenceFactIds.length
    ) {
      fail(`${candidateId}.${gateId} inválido`)
    }
  }
}

function deriveEngineDecision(gates) {
  if (GATE_IDS.some((gateId) => gates[gateId].status === 'reprovado')) {
    return 'retida'
  }
  return GATE_IDS
    .filter((gateId) => gateId !== 'G8')
    .every((gateId) => gates[gateId].status === 'ok')
    ? 'apta_para_autoria'
    : 'retida'
}

export function derivePublicationDecision(gates) {
  const factIds = new Set(
    Object.values(gates ?? {}).flatMap(({ evidenceFactIds = [] }) => evidenceFactIds),
  )
  validateGateMap(gates, 'publication', factIds)
  return GATE_IDS.every((gateId) => gates[gateId].status === 'ok')
    ? 'publicada'
    : 'retida'
}

function validateFutureBasis(candidate) {
  const basis = candidate.futureBasis
  assertExactKeys(basis, FUTURE_BASIS_KEYS, `${candidate.id}.futureBasis`)
  assertStringArray(basis.seriesIds, `${candidate.id}.futureBasis.seriesIds`)
  if (
    !['observed_series', 'observed_snapshot'].includes(basis.basisType)
    || !isRecord(basis.observedPeriod)
    || !Number.isInteger(basis.observedPeriod.start)
    || !Number.isInteger(basis.observedPeriod.end)
    || basis.observedPeriod.start > basis.observedPeriod.end
    || typeof basis.supportsTrend !== 'boolean'
    || basis.scenarioId !== null
    || !Array.isArray(basis.futureNumericValues)
    || basis.futureNumericValues.length !== 0
    || !isNonEmptyString(basis.claimBoundary)
  ) {
    fail(`${candidate.id}: base futura observada inválida`)
  }
  const expected = candidate.transformationClass === 'tendencia_sustentada'
    ? ['observed_series', true]
    : ['observed_snapshot', false]
  if (basis.basisType !== expected[0] || basis.supportsTrend !== expected[1]) {
    fail(`${candidate.id}: classe e base futura incompatíveis`)
  }
}

function assertPairAllowed(candidate, pairDependencies) {
  if (!Array.isArray(candidate.pairs) || candidate.pairs.length === 0) {
    fail(`${candidate.id}: candidato apto sem pares`)
  }
  for (const pair of candidate.pairs) {
    const result = validatePair(
      { ...pair, mechanismId: candidate.mechanismId },
      pairDependencies,
    )
    if (!result.allowed) {
      fail(`${candidate.id}: par bloqueado por ${result.reasonCode}`)
    }
  }
}

function validateChange(values, field) {
  if (
    !isFiniteNumber(values?.start)
    || !isFiniteNumber(values?.end)
    || !isFiniteNumber(values?.absoluteChange)
    || !isFiniteNumber(values?.percentageChange)
    || values.start === 0
    || !nearlyEqual(values.absoluteChange, values.end - values.start)
    || !nearlyEqual(
      values.percentageChange,
      (values.end / values.start - 1) * 100,
    )
  ) {
    fail(`${field} não é uma mudança recomputável`)
  }
}

function validateCoortesEvidence(candidate, municipalityIds) {
  const population = factById(candidate, `${candidate.id}.populacao-0-14`)
  const births = factById(candidate, `${candidate.id}.nascimentos`)
  const schools = factById(candidate, `${candidate.id}.rede`)
  const enrollments = factById(candidate, `${candidate.id}.matriculas-etapas`)
  const municipal = factById(candidate, `${candidate.id}.municipios`)
  const state = factById(candidate, `${candidate.id}.comparacao-rs`)
  const sensitivity = factById(candidate, `${candidate.id}.estabilidade`)
  const aging = factById(candidate, `${candidate.id}.envelhecimento`)
  if ([population, births, schools, enrollments, municipal, state, sensitivity, aging]
    .some((fact) => fact === undefined)) {
    fail(`${candidate.id}: conjunto de fatos demográficos incompleto`)
  }

  validateChange(population.values, population.id)
  validateChange(births.values, births.id)
  validateChange(schools.values, schools.id)
  if (births.values.lastFinalYear !== births.period.end) {
    fail(`${candidate.id}: último ano final do SINASC divergente`)
  }

  const enrollmentEntries = enrollments.values.entries
  const expectedSeries = new Set([
    'matriculas-na-educacao-infantil',
    'matriculas-no-ensino-fundamental',
    'matriculas-no-ensino-medio',
  ])
  if (
    !Array.isArray(enrollmentEntries)
    || enrollmentEntries.length !== 3
    || !compareSets(new Set(enrollmentEntries.map(({ seriesId }) => seriesId)), expectedSeries)
    || enrollmentEntries.some((entry) => (
      !isFiniteNumber(entry.start)
      || !isFiniteNumber(entry.end)
      || !nearlyEqual(entry.absoluteChange, entry.end - entry.start)
    ))
  ) {
    fail(`${candidate.id}: ponto de partida educacional inválido`)
  }

  const entries = municipal.values.entries
  if (!Array.isArray(entries) || entries.length !== 10) {
    fail(`${candidate.id}: decomposição municipal incompleta`)
  }
  const observedIds = new Set(entries.map(({ ibgeCode }) => ibgeCode))
  if (!compareSets(observedIds, municipalityIds)) {
    fail(`${candidate.id}: identidades municipais divergentes`)
  }
  const totalAbsoluteChange = entries.reduce(
    (sum, { change }) => sum + Math.abs(change),
    0,
  )
  const regionalChange = entries.reduce((sum, { change }) => sum + change, 0)
  let maximumConcentration = 0
  let directionCount = 0
  let leaveOneOutStable = true
  for (const entry of entries) {
    if (
      !/^\d{7}$/u.test(entry.ibgeCode)
      || !isNonEmptyString(entry.name)
      || !isFiniteNumber(entry.start)
      || !isFiniteNumber(entry.end)
      || !nearlyEqual(entry.change, entry.end - entry.start)
    ) {
      fail(`${candidate.id}: contribuição municipal inválida`)
    }
    const share = Math.abs(entry.change) / totalAbsoluteChange
    const leaveOneOut = regionalChange - entry.change
    if (
      !nearlyEqual(entry.absoluteShare, share)
      || !nearlyEqual(entry.leaveOneOutChange, leaveOneOut)
    ) {
      fail(`${candidate.id}: teste municipal não recomputável`)
    }
    maximumConcentration = Math.max(maximumConcentration, share)
    if (Math.sign(entry.change) === Math.sign(regionalChange)) directionCount += 1
    leaveOneOutStable &&= Math.sign(leaveOneOut) === Math.sign(regionalChange)
  }
  const directionShare = directionCount / entries.length
  const oppositeDirection = entries
    .filter(({ change }) => Math.sign(change) !== Math.sign(regionalChange))
    .map(({ ibgeCode }) => ibgeCode)
  const topNegativeContributors = [...entries]
    .filter(({ change }) => change < 0)
    .sort((left, right) => left.change - right.change)
    .slice(0, 3)
    .map(({ ibgeCode }) => ibgeCode)
  const tests = municipal.values.tests
  if (
    regionalChange !== population.values.absoluteChange
    || municipal.values.regionalChange !== regionalChange
    || !nearlyEqual(tests.maximumConcentration, maximumConcentration)
    || !nearlyEqual(tests.directionShare, directionShare)
    || tests.leaveOneOutStable !== leaveOneOutStable
    || tests.passed !== (
      maximumConcentration <= 0.5
      && directionShare >= 0.6
      && leaveOneOutStable
    )
    || tests.passed !== true
    || JSON.stringify(municipal.values.oppositeDirection) !== JSON.stringify(oppositeDirection)
    || JSON.stringify(municipal.values.topNegativeContributors)
      !== JSON.stringify(topNegativeContributors)
  ) {
    fail(`${candidate.id}: conclusão territorial não derivada`)
  }

  if (
    !nearlyEqual(
      state.values.population.regionPercentageChange,
      population.values.percentageChange,
    )
    || !nearlyEqual(
      state.values.schools.regionPercentageChange,
      schools.values.percentageChange,
    )
    || !isFiniteNumber(state.values.population.statePercentageChange)
    || !isFiniteNumber(state.values.schools.statePercentageChange)
  ) {
    fail(`${candidate.id}: comparação com RS inválida`)
  }

  const windows = sensitivity.values.windows
  const expectedWindows = new Set(['2014-2025', '2015-2025', '2016-2025', '2015-2024'])
  if (
    !Array.isArray(windows)
    || windows.length !== 4
    || !compareSets(
      new Set(windows.map(({ start, end }) => `${start}-${end}`)),
      expectedWindows,
    )
  ) {
    fail(`${candidate.id}: janelas de estabilidade inválidas`)
  }
  const referenceDirection = Math.sign(population.values.absoluteChange)
  for (const window of windows) {
    if (
      !Number.isInteger(window.start)
      || !Number.isInteger(window.end)
      || !nearlyEqual(window.change, window.endValue - window.startValue)
      || window.direction !== Math.sign(window.change)
      || window.direction !== referenceDirection
    ) {
      fail(`${candidate.id}: janela de estabilidade não recomputável`)
    }
  }
  if (
    sensitivity.values.tests.minimumPoints < 2
    || sensitivity.values.tests.sameDirection !== true
    || sensitivity.values.tests.passed !== true
  ) {
    fail(`${candidate.id}: teste de estabilidade reprovado`)
  }
  if (
    !isFiniteNumber(aging.values.start)
    || !isFiniteNumber(aging.values.end)
    || !nearlyEqual(
      aging.values.absoluteChange,
      aging.values.end - aging.values.start,
    )
    || aging.values.absoluteChange <= 0
  ) {
    fail(`${candidate.id}: contexto de envelhecimento inválido`)
  }
}

function validateMobilityEvidence(candidate, municipalityIds) {
  const mobility = factById(candidate, `${candidate.id}.deslocamento`)
  const education = factById(candidate, `${candidate.id}.ponto-partida-educacao`)
  const municipal = factById(candidate, `${candidate.id}.municipios`)
  const state = factById(candidate, `${candidate.id}.comparacao-rs`)
  if ([mobility, education, municipal, state].some((fact) => fact === undefined)) {
    fail(`${candidate.id}: conjunto de fatos de deslocamento incompleto`)
  }
  const universes = ['total', 'fundamental', 'medio']
  const mobilityEntries = mobility.values.entries
  if (
    !Array.isArray(mobilityEntries)
    || JSON.stringify(mobilityEntries.map(({ universe }) => universe))
      !== JSON.stringify(universes)
  ) {
    fail(`${candidate.id}: universos de deslocamento divergentes`)
  }
  const usedSeriesIds = new Set()
  for (const entry of mobilityEntries) {
    const seriesIds = Object.values(entry.seriesIds ?? {})
    if (
      !Number.isInteger(entry.outsideMunicipality)
      || !Number.isInteger(entry.total)
      || !Number.isInteger(entry.residual)
      || entry.total <= 0
      || !nearlyEqual(
        entry.outsideSharePercent,
        entry.outsideMunicipality / entry.total * 100,
      )
      || Math.abs(entry.residual) > Math.max(5, entry.total * 0.01)
      || seriesIds.length !== 4
      || seriesIds.some((seriesId) => !isNonEmptyString(seriesId))
      || seriesIds.some((seriesId) => usedSeriesIds.has(seriesId))
    ) {
      fail(`${candidate.id}: universo ${entry.universe} não recomputável`)
    }
    seriesIds.forEach((seriesId) => usedSeriesIds.add(seriesId))
  }
  if (
    education.values.territorialLens !== 'school_location'
    || !Number.isInteger(education.values.value)
    || education.values.value <= 0
  ) {
    fail(`${candidate.id}: ponto de partida educacional inválido`)
  }

  const municipalEntries = municipal.values.entries
  if (!Array.isArray(municipalEntries) || municipalEntries.length !== 10) {
    fail(`${candidate.id}: exposição municipal incompleta`)
  }
  const observedIds = new Set(municipalEntries.map(({ ibgeCode }) => ibgeCode))
  if (!compareSets(observedIds, municipalityIds)) {
    fail(`${candidate.id}: identidades municipais divergentes`)
  }
  const regionalByUniverse = new Map(
    mobilityEntries.map((entry) => [entry.universe, entry]),
  )
  const sums = Object.fromEntries(
    universes.map((universe) => [universe, { outside: 0, total: 0 }]),
  )
  for (const entry of municipalEntries) {
    if (!/^\d{7}$/u.test(entry.ibgeCode) || !isNonEmptyString(entry.name)) {
      fail(`${candidate.id}: identidade municipal inválida`)
    }
    for (const universe of universes) {
      const values = entry.universes?.[universe]
      if (
        !Number.isInteger(values?.outsideMunicipality)
        || !Number.isInteger(values?.total)
        || values.total <= 0
        || !nearlyEqual(
          values.outsideSharePercent,
          values.outsideMunicipality / values.total * 100,
        )
      ) {
        fail(`${candidate.id}: exposição municipal ${universe} inválida`)
      }
      sums[universe].outside += values.outsideMunicipality
      sums[universe].total += values.total
    }
    const expectedAbsoluteShare = (
      entry.universes.total.outsideMunicipality
      / regionalByUniverse.get('total').outsideMunicipality
    )
    if (!nearlyEqual(entry.absoluteOutsideShare, expectedAbsoluteShare)) {
      fail(`${candidate.id}: participação municipal absoluta inválida`)
    }
  }
  for (const universe of universes) {
    const regional = regionalByUniverse.get(universe)
    if (
      sums[universe].outside !== regional.outsideMunicipality
      || sums[universe].total !== regional.total
    ) {
      fail(`${candidate.id}: soma municipal de ${universe} não reconcilia`)
    }
  }
  const maximumConcentration = Math.max(
    ...municipalEntries.map(({ absoluteOutsideShare }) => absoluteOutsideShare),
  )
  const topAbsoluteOutside = [...municipalEntries]
    .sort((left, right) => (
      right.universes.total.outsideMunicipality
      - left.universes.total.outsideMunicipality
    ))
    .slice(0, 3)
    .map(({ ibgeCode }) => ibgeCode)
  const topHighSchoolShare = [...municipalEntries]
    .sort((left, right) => (
      right.universes.medio.outsideSharePercent
      - left.universes.medio.outsideSharePercent
    ))
    .slice(0, 3)
    .map(({ ibgeCode }) => ibgeCode)
  if (
    !nearlyEqual(municipal.values.tests.maximumConcentration, maximumConcentration)
    || municipal.values.tests.municipalityCount !== 10
    || municipal.values.tests.passed !== (maximumConcentration <= 0.5)
    || municipal.values.tests.passed !== true
    || JSON.stringify(municipal.values.topAbsoluteOutside)
      !== JSON.stringify(topAbsoluteOutside)
    || JSON.stringify(municipal.values.topHighSchoolShare)
      !== JSON.stringify(topHighSchoolShare)
  ) {
    fail(`${candidate.id}: conclusão municipal de deslocamento não derivada`)
  }

  const stateEntries = state.values.entries
  if (
    !Array.isArray(stateEntries)
    || JSON.stringify(stateEntries.map(({ universe }) => universe))
      !== JSON.stringify(universes)
  ) {
    fail(`${candidate.id}: comparação com RS incompleta`)
  }
  for (const entry of stateEntries) {
    if (
      !nearlyEqual(
        entry.regionOutsideSharePercent,
        regionalByUniverse.get(entry.universe).outsideSharePercent,
      )
      || !isFiniteNumber(entry.stateOutsideSharePercent)
    ) {
      fail(`${candidate.id}: comparação com RS inválida`)
    }
  }
}

function validateVisualizations(candidate) {
  if (!Array.isArray(candidate.visualizations) || candidate.visualizations.length < 3) {
    fail(`${candidate.id}: Gate 8 sem visualizações suficientes`)
  }
  const factIds = collectFactIds(candidate)
  const visualizationIds = new Set()
  for (const visualization of candidate.visualizations) {
    if (
      !isNonEmptyString(visualization.id)
      || visualizationIds.has(visualization.id)
      || !isNonEmptyString(visualization.kind)
      || !isNonEmptyString(visualization.addsInformation)
    ) {
      fail(`${candidate.id}: visualização inválida`)
    }
    visualizationIds.add(visualization.id)
    const references = [
      ...(isNonEmptyString(visualization.factId) ? [visualization.factId] : []),
      ...(Array.isArray(visualization.factIds) ? visualization.factIds : []),
    ]
    if (references.some((factId) => !factIds.has(factId))) {
      fail(`${candidate.id}: visualização referencia fato desconhecido`)
    }
    if (visualization.kind === 'aligned-mini-charts') {
      for (const series of visualization.series ?? []) {
        if (
          JSON.stringify(series.points?.map(({ period }) => period))
          !== JSON.stringify(visualization.periods)
        ) {
          fail(`${candidate.id}: minigráficos com períodos desalinhados`)
        }
      }
    }
  }
}

function validateReadyCandidate(candidate, pairDependencies, municipalityIds) {
  if (candidate.gates.G8.status !== 'pendente_autoria') {
    fail(`${candidate.id}: G8 técnico deve aguardar autoria`)
  }
  for (const gateId of GATE_IDS.filter((id) => id !== 'G8')) {
    if (candidate.gates[gateId].status !== 'ok') {
      fail(`${candidate.id}: ${gateId} técnico não aprovado`)
    }
  }
  if (!['mudanca_observada', 'tendencia_sustentada'].includes(candidate.transformationClass)) {
    fail(`${candidate.id}: classe de transformação inválida`)
  }
  validateFutureBasis(candidate)
  assertPairAllowed(candidate, pairDependencies)
  assertExactKeys(
    candidate.transformationMap,
    new Set(['affected', 'educationSeriesIds', 'territorialSeriesIds']),
    `${candidate.id}.transformationMap`,
  )
  for (const field of ['affected', 'educationSeriesIds', 'territorialSeriesIds']) {
    assertStringArray(candidate.transformationMap[field], `${candidate.id}.transformationMap.${field}`)
  }
  assertExactKeys(
    candidate.planningComponents,
    new Set(['affectedGroupOrStage', 'indicatorIds', 'phenomenon', 'scope']),
    `${candidate.id}.planningComponents`,
  )
  for (const field of ['affectedGroupOrStage', 'phenomenon', 'scope']) {
    if (!isNonEmptyString(candidate.planningComponents[field])) {
      fail(`${candidate.id}: planningComponents.${field} ausente`)
    }
  }
  assertStringArray(
    candidate.planningComponents.indicatorIds,
    `${candidate.id}.planningComponents.indicatorIds`,
  )
  if (candidate.id === 'vds-coortes-rede') {
    validateCoortesEvidence(candidate, municipalityIds)
  } else if (candidate.id === 'vds-deslocamento-oferta') {
    validateMobilityEvidence(candidate, municipalityIds)
  } else {
    fail(`${candidate.id}: candidato apto desconhecido`)
  }
  validateVisualizations(candidate)
}

export function validateResearchArtifact(research, pairDependencies) {
  if (!isRecord(research)) fail('artefato de pesquisa deve ser objeto')
  if (
    research.schemaVersion !== RESEARCH_SCHEMA
    || research.contractVersion !== CONTRACT_VERSION
  ) {
    fail('schema/contrato de pesquisa divergente')
  }
  if (
    research.region?.slug !== 'vale-do-sinos'
    || research.region?.stateCode !== 'RS'
    || research.region?.municipalityCount !== 10
    || research.region?.municipalities?.length !== 10
  ) {
    fail('identidade regional da pesquisa divergente')
  }
  const municipalityCodes = research.region.municipalities.map(({ ibge7 }) => ibge7)
  const municipalityIds = new Set(municipalityCodes)
  if (
    municipalityIds.size !== 10
    || municipalityCodes.some((code) => typeof code !== 'string' || !/^\d{7}$/u.test(code))
  ) {
    fail('códigos IBGE municipais inválidos na pesquisa')
  }
  if (
    research.generation?.deterministic !== true
    || research.generation?.networkUsed !== false
    || research.generation?.databaseUsed !== false
    || research.generation?.clockUsed !== false
    || research.generation?.modelUsed !== false
    || research.generation?.scenarioUsed !== false
  ) {
    fail('geração da pesquisa usou recurso proibido nesta rodada')
  }
  if (!Array.isArray(research.sourceCatalog) || !Array.isArray(research.sourceManifest)) {
    fail('fontes da pesquisa ausentes')
  }
  const sourceIds = new Set(research.sourceCatalog.map(({ id }) => id))
  if (
    sourceIds.size !== research.sourceCatalog.length
    || research.sourceCatalog.some(({ id, label, evidenceClass }) => (
      !isNonEmptyString(id)
      || !isNonEmptyString(label)
      || !isNonEmptyString(evidenceClass)
    ))
  ) {
    fail('catálogo de fontes da pesquisa inválido')
  }
  const manifestPaths = new Set()
  if (
    research.sourceManifest.length < 20
    || research.sourceManifest.some((item) => (
      !isNonEmptyString(item.path)
      || manifestPaths.has(item.path)
      || !/^[a-f0-9]{64}$/u.test(item.sha256)
      || !Number.isInteger(item.byteSize)
      || item.byteSize <= 0
      || (manifestPaths.add(item.path), false)
    ))
  ) {
    fail('manifesto de fontes da pesquisa inválido')
  }
  if (!Array.isArray(research.candidates) || research.candidates.length !== 5) {
    fail('pesquisa deve conter cinco candidatos')
  }
  const candidateIds = new Set()
  for (const [index, candidate] of research.candidates.entries()) {
    if (
      !isNonEmptyString(candidate.id)
      || candidateIds.has(candidate.id)
      || candidate.direction !== 'territorio_para_educacao'
      || candidate.editorialOrder !== index + 1
      || !isNonEmptyString(candidate.mechanismId)
      || !Array.isArray(candidate.facts)
      || new Set(candidate.facts.map(({ id }) => id)).size !== candidate.facts.length
    ) {
      fail(`candidato de pesquisa inválido na posição ${index}`)
    }
    candidateIds.add(candidate.id)
    candidate.facts.forEach((fact) => validateFact(fact, sourceIds, candidate.id))
    const factIds = collectFactIds(candidate)
    validateGateMap(candidate.gates, candidate.id, factIds)
    if (candidate.engineDecision !== deriveEngineDecision(candidate.gates)) {
      fail(`${candidate.id}: decisão técnica não derivada`)
    }
    if (candidate.engineDecision === 'apta_para_autoria') {
      validateReadyCandidate(candidate, pairDependencies, municipalityIds)
    } else if (
      candidate.facts.length !== 0
      || candidate.visualizations?.length !== 0
      || candidate.planningComponents !== null
      || candidate.transformationMap !== null
      || candidate.futureBasis !== null
      || Object.values(candidate.gates)
        .filter(({ status }) => status === 'reprovado').length !== 1
    ) {
      fail(`${candidate.id}: retenção técnica inválida`)
    }
  }
  const readyIds = research.candidates
    .filter(({ engineDecision }) => engineDecision === 'apta_para_autoria')
    .map(({ id }) => id)
  const retainedIds = research.candidates
    .filter(({ engineDecision }) => engineDecision === 'retida')
    .map(({ id }) => id)
  const expectedSummary = {
    candidateCount: 5,
    readyForAuthorshipCount: 2,
    readyForAuthorshipIds: readyIds,
    retainedCount: 3,
    retainedIds,
    technicalGate7: 'aprovado',
    technicalGate8: 'aprovado',
  }
  if (
    JSON.stringify(readyIds) !== JSON.stringify([
      'vds-coortes-rede',
      'vds-deslocamento-oferta',
    ])
    || JSON.stringify(research.summary) !== JSON.stringify(expectedSummary)
  ) {
    fail('resumo técnico da segunda saída divergente')
  }
  return true
}

function requiredReferencePaths(publicCard) {
  return [
    ...REQUIRED_NARRATIVE_PATHS,
    ...publicCard.territorial_facts.map((_, index) => `territorial_facts[${index}]`),
  ]
}

function validateFactReferences(authorItem, candidate, research, dependencies) {
  const requiredPaths = requiredReferencePaths(authorItem.public)
  assertExactKeys(
    authorItem.factReferences,
    new Set(requiredPaths),
    `${candidate.id}.factReferences`,
  )
  const factsById = new Map(candidate.facts.map((fact) => [fact.id, fact]))
  for (const path of requiredPaths) {
    const factIds = authorItem.factReferences[path]
    if (
      !Array.isArray(factIds)
      || factIds.length === 0
      || new Set(factIds).size !== factIds.length
      || factIds.some((factId) => !factsById.has(factId))
    ) {
      fail(`${candidate.id}: referência factual inválida em ${path}`)
    }
  }

  const sourceLabelById = new Map(
    research.sourceCatalog.map(({ id, label }) => [id, label]),
  )
  const referencedSourceLabels = new Set(
    Object.values(authorItem.factReferences)
      .flat()
      .map((factId) => sourceLabelById.get(factsById.get(factId).sourceId)),
  )
  if (!compareSets(referencedSourceLabels, new Set(authorItem.public.sources))) {
    fail(`${candidate.id}: fontes públicas não cobrem os fatos narrados`)
  }

  const indicatorIdByLabel = new Map(
    dependencies.cardDependencies.referencias.indicadores
      .map(({ id, label }) => [label, id]),
  )
  const publicIndicatorIds = new Set(
    authorItem.public.monitoring_indicators.map((label) => indicatorIdByLabel.get(label)),
  )
  if (
    publicIndicatorIds.has(undefined)
    || !compareSets(
      publicIndicatorIds,
      new Set(candidate.planningComponents.indicatorIds),
    )
  ) {
    fail(`${candidate.id}: indicadores públicos divergem do mapa de planejamento`)
  }

  const mechanism = dependencies.cardDependencies.mecanismos.mecanismos
    .find(({ id }) => id === candidate.mechanismId)
  const topicIdByLabel = new Map(
    dependencies.cardDependencies.referencias.temasPne
      .map(({ id, label }) => [label, id]),
  )
  if (
    !mechanism
    || authorItem.public.pne_topics
      .map((label) => topicIdByLabel.get(label))
      .some((id) => !mechanism.temasPne.includes(id))
  ) {
    fail(`${candidate.id}: temas do PNE incompatíveis com o mecanismo`)
  }
}

function buildCard(authorItem, candidate, research, dependencies) {
  assertExactKeys(
    authorItem,
    new Set(['candidateId', 'public', 'factReferences']),
    `${candidate.id}.autoria`,
  )
  assertExactKeys(authorItem.public, PUBLIC_KEYS, `${candidate.id}.public`)
  if (
    authorItem.candidateId !== candidate.id
    || authorItem.public.id !== candidate.id
    || authorItem.public.direction !== 'territorio_para_educacao'
  ) {
    fail(`${candidate.id}: autoria e candidato divergentes`)
  }
  validateFactReferences(authorItem, candidate, research, dependencies)
  const gates = structuredClone(candidate.gates)
  gates.G8 = {
    status: 'ok',
    reasonCode: 'texto-publico-e-visuais-aprovados',
    evidenceFactIds: [...new Set(Object.values(authorItem.factReferences).flat())],
  }
  const card = {
    ...structuredClone(authorItem.public),
    internal: {
      transformation_class: candidate.transformationClass,
      mechanism_id: candidate.mechanismId,
      future_basis: structuredClone(candidate.futureBasis),
      sensitivity_check: 'ok',
      publication_decision: derivePublicationDecision(gates),
      gates,
      fact_references: structuredClone(authorItem.factReferences),
      planning_components: structuredClone(candidate.planningComponents),
      transformation_map: structuredClone(candidate.transformationMap),
      visualization_ids: candidate.visualizations.map(({ id }) => id),
      research_candidate_id: candidate.id,
    },
  }
  const violations = [
    ...validateCardContract(card),
    ...validateCardCatalog(card, dependencies.cardDependencies),
    ...lintCard(card, dependencies.vocab),
  ]
  if (violations.length > 0) {
    fail(`${candidate.id}: autoria viola contrato: ${JSON.stringify(violations)}`)
  }
  return card
}

function expectedRetainedCandidates(research) {
  return research.candidates
    .filter(({ engineDecision }) => engineDecision === 'retida')
    .map((candidate) => ({
      candidateId: candidate.id,
      publicationDecision: 'retida',
      failedGates: GATE_IDS.filter(
        (gateId) => candidate.gates[gateId].status === 'reprovado',
      ).map((gateId) => ({
        gateId,
        reasonCode: candidate.gates[gateId].reasonCode,
      })),
    }))
}

export function buildSecondOutputArtifact(
  research,
  authorship,
  researchReference,
  dependencies,
) {
  validateResearchArtifact(research, dependencies.pairDependencies)
  if (
    authorship?.schemaVersion !== AUTHORSHIP_SCHEMA
    || authorship?.contractVersion !== CONTRACT_VERSION
    || authorship?.regionSlug !== research.region.slug
    || !Array.isArray(authorship.cards)
    || authorship.cards.length !== 2
  ) {
    fail('autoria da segunda saída inválida')
  }
  if (
    researchReference?.path !== RESEARCH_FIXTURE_PATH
    || !/^[a-f0-9]{64}$/u.test(researchReference?.sha256)
    || !Number.isInteger(researchReference?.byteSize)
    || researchReference.byteSize <= 0
  ) {
    fail('referência ao artefato de pesquisa inválida')
  }
  const candidatesById = new Map(
    research.candidates.map((candidate) => [candidate.id, candidate]),
  )
  const cards = authorship.cards.map((authorItem) => {
    const candidate = candidatesById.get(authorItem.candidateId)
    if (!candidate || candidate.engineDecision !== 'apta_para_autoria') {
      fail(`autoria aponta para candidato não apto: ${authorItem.candidateId}`)
    }
    return buildCard(authorItem, candidate, research, dependencies)
  })
  const readyIds = research.candidates
    .filter(({ engineDecision }) => engineDecision === 'apta_para_autoria')
    .map(({ id }) => id)
  if (JSON.stringify(cards.map(({ id }) => id)) !== JSON.stringify(readyIds)) {
    fail('autoria não cobre exatamente os candidatos aptos, na ordem editorial')
  }
  const retainedCandidates = expectedRetainedCandidates(research)
  const artifact = {
    schemaVersion: OUTPUT_SCHEMA,
    contractVersion: CONTRACT_VERSION,
    region: structuredClone(research.region),
    researchArtifact: structuredClone(researchReference),
    cards,
    retainedCandidates,
    publicProjection: cards.map(serializePublic),
    summary: {
      candidateCount: research.candidates.length,
      publishedCount: cards.length,
      retainedCount: retainedCandidates.length,
      gate7: cards.length >= 2 && cards.length <= 5 ? 'aprovado' : 'reprovado',
      gate8: cards.every((card) => (
        card.internal.visualization_ids.length >= 3
        && card.internal.gates.G4.status === 'ok'
        && card.internal.gates.G5.status === 'ok'
      )) ? 'aprovado' : 'reprovado',
    },
    generation: {
      deterministic: true,
      clockUsed: false,
      modelUsed: false,
      networkUsed: false,
      databaseUsed: false,
      scenarioUsed: false,
      builderVersion: BUILDER_VERSION,
    },
  }
  validateSecondOutputArtifact(artifact, research, dependencies)
  return artifact
}

function collectInternalKeyPaths(value, field = '') {
  const internalKeys = new Set([
    'internal',
    'mechanism_id',
    'future_basis',
    'publication_decision',
    'gates',
    'fact_references',
    'planning_components',
    'transformation_map',
    'visualization_ids',
    'research_candidate_id',
  ])
  if (Array.isArray(value)) {
    return value.flatMap(
      (item, index) => collectInternalKeyPaths(item, `${field}[${index}]`),
    )
  }
  if (!isRecord(value)) return []
  return Object.entries(value).flatMap(([key, child]) => {
    const childField = field ? `${field}.${key}` : key
    return [
      ...(internalKeys.has(key) ? [childField] : []),
      ...collectInternalKeyPaths(child, childField),
    ]
  })
}

export function validateSecondOutputArtifact(artifact, research, dependencies) {
  validateResearchArtifact(research, dependencies.pairDependencies)
  if (
    artifact?.schemaVersion !== OUTPUT_SCHEMA
    || artifact?.contractVersion !== CONTRACT_VERSION
    || JSON.stringify(artifact.region) !== JSON.stringify(research.region)
  ) {
    fail('saída final com schema, contrato ou região divergente')
  }
  if (
    artifact.researchArtifact?.path !== RESEARCH_FIXTURE_PATH
    || !/^[a-f0-9]{64}$/u.test(artifact.researchArtifact?.sha256)
    || !Number.isInteger(artifact.researchArtifact?.byteSize)
    || artifact.researchArtifact.byteSize <= 0
  ) {
    fail('referência de pesquisa da saída final inválida')
  }
  if (
    artifact.generation?.deterministic !== true
    || artifact.generation?.clockUsed !== false
    || artifact.generation?.modelUsed !== false
    || artifact.generation?.networkUsed !== false
    || artifact.generation?.databaseUsed !== false
    || artifact.generation?.scenarioUsed !== false
    || artifact.generation?.builderVersion !== BUILDER_VERSION
  ) {
    fail('metadados de geração da saída final inválidos')
  }
  const readyCandidates = research.candidates
    .filter(({ engineDecision }) => engineDecision === 'apta_para_autoria')
  if (
    !Array.isArray(artifact.cards)
    || artifact.cards.length !== 2
    || JSON.stringify(artifact.cards.map(({ id }) => id))
      !== JSON.stringify(readyCandidates.map(({ id }) => id))
  ) {
    fail('saída final não cobre os dois candidatos aptos')
  }
  const internalKeys = new Set([
    'transformation_class',
    'mechanism_id',
    'future_basis',
    'sensitivity_check',
    'publication_decision',
    'gates',
    'fact_references',
    'planning_components',
    'transformation_map',
    'visualization_ids',
    'research_candidate_id',
  ])
  for (const [index, card] of artifact.cards.entries()) {
    const candidate = readyCandidates[index]
    assertExactKeys(card.internal, internalKeys, `${card.id}.internal`)
    if (
      card.direction !== 'territorio_para_educacao'
      || card.internal.transformation_class !== candidate.transformationClass
      || card.internal.mechanism_id !== candidate.mechanismId
      || JSON.stringify(card.internal.future_basis) !== JSON.stringify(candidate.futureBasis)
      || card.internal.sensitivity_check !== 'ok'
      || card.internal.publication_decision !== 'publicada'
      || derivePublicationDecision(card.internal.gates) !== 'publicada'
      || card.internal.gates.G8.reasonCode !== 'texto-publico-e-visuais-aprovados'
      || JSON.stringify(card.internal.planning_components)
        !== JSON.stringify(candidate.planningComponents)
      || JSON.stringify(card.internal.transformation_map)
        !== JSON.stringify(candidate.transformationMap)
      || JSON.stringify(card.internal.visualization_ids)
        !== JSON.stringify(candidate.visualizations.map(({ id }) => id))
      || card.internal.research_candidate_id !== candidate.id
    ) {
      fail(`${card.id}: camada interna diverge da pesquisa`)
    }
    validateFactReferences(
      {
        public: serializePublic(card),
        factReferences: card.internal.fact_references,
      },
      candidate,
      research,
      dependencies,
    )
    const violations = [
      ...validateCardContract(card),
      ...validateCardCatalog(card, dependencies.cardDependencies),
      ...lintCard(card, dependencies.vocab),
    ]
    if (violations.length > 0) {
      fail(`${card.id}: regressão de contrato: ${JSON.stringify(violations)}`)
    }
  }
  const publicProjection = artifact.cards.map(serializePublic)
  if (
    JSON.stringify(artifact.publicProjection) !== JSON.stringify(publicProjection)
    || collectInternalKeyPaths(artifact.publicProjection).length > 0
  ) {
    fail('projeção pública diverge da allowlist ou vaza camada interna')
  }
  if (
    JSON.stringify(artifact.retainedCandidates)
    !== JSON.stringify(expectedRetainedCandidates(research))
  ) {
    fail('retenções finais inválidas ou expostas')
  }
  const expectedSummary = {
    candidateCount: 5,
    publishedCount: 2,
    retainedCount: 3,
    gate7: 'aprovado',
    gate8: 'aprovado',
  }
  if (JSON.stringify(artifact.summary) !== JSON.stringify(expectedSummary)) {
    fail('Gates 7 e 8 finais não aprovados')
  }
  return true
}

export const SEGUNDA_SAIDA_CONTRACT = Object.freeze({
  researchSchema: RESEARCH_SCHEMA,
  authorshipSchema: AUTHORSHIP_SCHEMA,
  outputSchema: OUTPUT_SCHEMA,
  contractVersion: CONTRACT_VERSION,
  researchFixturePath: RESEARCH_FIXTURE_PATH,
  builderVersion: BUILDER_VERSION,
})
