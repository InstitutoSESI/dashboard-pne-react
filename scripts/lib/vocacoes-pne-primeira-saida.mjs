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

const RESEARCH_SCHEMA = 'vocacoes-pne-r5-engine-v1'
const AUTHORSHIP_SCHEMA = 'vocacoes-pne-r5-authorship-v1'
const OUTPUT_SCHEMA = 'vocacoes-pne-primeira-saida-v1'
const CONTRACT_VERSION = '1.3.0'
const REQUIRED_NARRATIVE_PATHS = [
  'title',
  'education_question',
  'integrated_reading',
  'municipal_pattern',
  'planning_question',
]
const PUBLIC_KEYS = new Set([
  'id',
  'direction',
  'title',
  'education_question',
  'education_facts',
  'territorial_facts',
  'integrated_reading',
  'municipal_pattern',
  'planning_question',
  'pne_topics',
  'monitoring_indicators',
  'period',
  'sources',
])

export class PrimeiraSaidaError extends Error {}

function fail(message) {
  throw new PrimeiraSaidaError(message)
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

function collectFactIds(candidate) {
  return new Set(candidate.facts.map(({ id }) => id))
}

function validateFact(fact, sourceIds, candidateId) {
  for (const field of ['id', 'kind', 'seriesId', 'unit', 'sourceId']) {
    if (!isNonEmptyString(fact?.[field])) {
      fail(`${candidateId}: fato sem ${field}`)
    }
  }
  if (!fact.id.startsWith(`${candidateId}.`)) {
    fail(`${candidateId}: fato fora do namespace: ${fact.id}`)
  }
  if (!isRecord(fact.period) || !isRecord(fact.values)) {
    fail(`${candidateId}: fato ${fact.id} sem período/valores estruturados`)
  }
  if (!sourceIds.has(fact.sourceId)) {
    fail(`${candidateId}: sourceId desconhecido em ${fact.id}`)
  }
}

function validateGateMap(gates, candidateId) {
  assertExactKeys(gates, GATE_IDS, `${candidateId}.gates`)
  for (const gateId of GATE_IDS) {
    const item = gates[gateId]
    if (
      !isRecord(item)
      || !['ok', 'reprovado', 'pendente_autoria', 'nao_avaliado'].includes(item.status)
      || !isNonEmptyString(item.reasonCode)
      || !Array.isArray(item.evidenceFactIds)
    ) {
      fail(`${candidateId}.${gateId} inválido`)
    }
  }
}

function deriveEngineDecision(gates) {
  if (GATE_IDS.some((gateId) => gates[gateId].status === 'reprovado')) {
    return 'retida'
  }
  const technicalGateIds = GATE_IDS.filter((gateId) => gateId !== 'G8')
  if (technicalGateIds.every((gateId) => gates[gateId].status === 'ok')) {
    return 'apta_para_autoria'
  }
  return 'retida'
}

export function derivePublicationDecision(gates) {
  validateGateMap(gates, 'publication')
  return GATE_IDS.every((gateId) => gates[gateId].status === 'ok')
    ? 'publicada'
    : 'retida'
}

function assertPairAllowed(candidate, pairDependencies) {
  if (!Array.isArray(candidate.pairs) || candidate.pairs.length === 0) {
    fail(`${candidate.id}: candidato apto sem pares`)
  }
  for (const pair of candidate.pairs) {
    const result = validatePair(pair, pairDependencies)
    if (!result.allowed) {
      fail(`${candidate.id}: par bloqueado por ${result.reasonCode}`)
    }
  }
}

function factByKind(candidate, kind) {
  return candidate.facts.find((fact) => fact.kind === kind)
}

function validateAccountingEvidence(candidate) {
  const education = factByKind(candidate, 'observed-change')
  const population = factByKind(candidate, 'estimated-change')
  const ratio = factByKind(candidate, 'calculated-ratio')
  const components = factByKind(candidate, 'accounting-decomposition')
  if (!education || !population || !ratio || !components) {
    fail(`${candidate.id}: fatos contábeis incompletos`)
  }

  const educationValues = education.values
  const populationValues = population.values
  const ratioValues = ratio.values
  const componentValues = components.values
  const requiredValues = [
    educationValues.start,
    educationValues.end,
    educationValues.absoluteChange,
    populationValues.start,
    populationValues.end,
    populationValues.absoluteChange,
    ratioValues.start,
    ratioValues.end,
    ratioValues.absoluteChange,
    componentValues.populationComponent,
    componentValues.ratioComponent,
    componentValues.totalChange,
    componentValues.reconciliationDifference,
  ]
  if (
    requiredValues.some((value) => !isFiniteNumber(value))
    || populationValues.start <= 0
    || populationValues.end <= 0
  ) {
    fail(`${candidate.id}: valores contábeis inválidos`)
  }

  const educationChange = educationValues.end - educationValues.start
  const populationChange = populationValues.end - populationValues.start
  const ratioStart = educationValues.start / populationValues.start
  const ratioEnd = educationValues.end / populationValues.end
  const populationComponent = populationChange * (ratioStart + ratioEnd) / 2
  const ratioComponent = (
    (ratioEnd - ratioStart)
    * (populationValues.start + populationValues.end)
    / 2
  )
  const dominantComponent = (
    Math.abs(populationComponent) >= Math.abs(ratioComponent)
      ? 'population'
      : 'ratio'
  )
  if (
    !nearlyEqual(educationValues.absoluteChange, educationChange)
    || !nearlyEqual(populationValues.absoluteChange, populationChange)
    || !nearlyEqual(ratioValues.start, ratioStart)
    || !nearlyEqual(ratioValues.end, ratioEnd)
    || !nearlyEqual(ratioValues.absoluteChange, ratioEnd - ratioStart)
    || !nearlyEqual(componentValues.populationComponent, populationComponent)
    || !nearlyEqual(componentValues.ratioComponent, ratioComponent)
    || !nearlyEqual(componentValues.totalChange, educationChange)
    || !nearlyEqual(
      componentValues.reconciliationDifference,
      populationComponent + ratioComponent - educationChange,
    )
    || componentValues.dominantComponent !== dominantComponent
  ) {
    fail(`${candidate.id}: decomposição contábil não recomputável`)
  }
  return { educationValues, populationValues, dominantComponent }
}

function validateSensitivityEvidence(candidate, accounting) {
  const sensitivity = factByKind(candidate, 'sensitivity-check')
  const windows = sensitivity?.values?.windows
  const tests = sensitivity?.values?.tests
  const expectedWindows = new Set(['2015-2025', '2014-2025', '2016-2025', '2015-2024'])
  if (!Array.isArray(windows) || windows.length !== 4 || !isRecord(tests)) {
    fail(`${candidate.id}: sensibilidade temporal incompleta`)
  }
  const observedWindows = new Set()
  let educationDirectionStable = true
  let populationDirectionStable = true
  let dominantComponentStable = true
  let reconciled = true
  for (const window of windows) {
    const numericFields = [
      'educationStart',
      'educationEnd',
      'educationChange',
      'populationStart',
      'populationEnd',
      'populationChange',
      'ratioStart',
      'ratioEnd',
      'ratioChange',
      'populationComponent',
      'ratioComponent',
      'reconciliationDifference',
    ]
    if (
      !Number.isInteger(window.start)
      || !Number.isInteger(window.end)
      || numericFields.some((field) => !isFiniteNumber(window[field]))
      || window.populationStart <= 0
      || window.populationEnd <= 0
    ) {
      fail(`${candidate.id}: janela de sensibilidade inválida`)
    }
    observedWindows.add(`${window.start}-${window.end}`)
    const educationChange = window.educationEnd - window.educationStart
    const populationChange = window.populationEnd - window.populationStart
    const ratioStart = window.educationStart / window.populationStart
    const ratioEnd = window.educationEnd / window.populationEnd
    const populationComponent = populationChange * (ratioStart + ratioEnd) / 2
    const ratioComponent = (
      (ratioEnd - ratioStart) * (window.populationStart + window.populationEnd) / 2
    )
    const dominantComponent = (
      Math.abs(populationComponent) >= Math.abs(ratioComponent)
        ? 'population'
        : 'ratio'
    )
    if (
      !nearlyEqual(window.educationChange, educationChange)
      || !nearlyEqual(window.populationChange, populationChange)
      || !nearlyEqual(window.ratioStart, ratioStart)
      || !nearlyEqual(window.ratioEnd, ratioEnd)
      || !nearlyEqual(window.ratioChange, ratioEnd - ratioStart)
      || !nearlyEqual(window.populationComponent, populationComponent)
      || !nearlyEqual(window.ratioComponent, ratioComponent)
      || !nearlyEqual(
        window.reconciliationDifference,
        populationComponent + ratioComponent - educationChange,
      )
    ) {
      fail(`${candidate.id}: janela de sensibilidade não recomputável`)
    }
    educationDirectionStable &&= (
      Math.sign(educationChange) === Math.sign(accounting.educationValues.absoluteChange)
    )
    populationDirectionStable &&= (
      Math.sign(populationChange) === Math.sign(accounting.populationValues.absoluteChange)
    )
    dominantComponentStable &&= dominantComponent === accounting.dominantComponent
    reconciled &&= Math.abs(window.reconciliationDifference) <= 1e-8
  }
  if (
    observedWindows.size !== expectedWindows.size
    || [...expectedWindows].some((item) => !observedWindows.has(item))
    || tests.educationDirectionStable !== educationDirectionStable
    || tests.populationDirectionStable !== populationDirectionStable
    || tests.dominantComponentStable !== dominantComponentStable
    || tests.reconciled !== reconciled
    || tests.passed !== (
      educationDirectionStable
      && populationDirectionStable
      && dominantComponentStable
      && reconciled
    )
    || tests.passed !== true
  ) {
    fail(`${candidate.id}: conclusão de sensibilidade não derivada`)
  }
}

function validateMunicipalEvidence(candidate, accounting) {
  const municipal = factByKind(candidate, 'municipal-decomposition')
  const entries = municipal?.values?.entries
  const tests = municipal?.values?.tests
  if (!Array.isArray(entries) || entries.length !== 10 || !isRecord(tests)) {
    fail(`${candidate.id}: decomposição municipal incompleta`)
  }
  const municipalityCodes = new Set()
  let educationChange = 0
  let populationChange = 0
  let educationAbsoluteTotal = 0
  let populationAbsoluteTotal = 0
  for (const entry of entries) {
    if (
      typeof entry.ibgeCode !== 'string'
      || !/^\d{7}$/u.test(entry.ibgeCode)
      || municipalityCodes.has(entry.ibgeCode)
      || !isNonEmptyString(entry.name)
      || !isRecord(entry.education)
      || !isRecord(entry.population)
    ) {
      fail(`${candidate.id}: identidade municipal inválida`)
    }
    municipalityCodes.add(entry.ibgeCode)
    for (const values of [entry.education, entry.population]) {
      if (
        ['start', 'end', 'change', 'absoluteShare', 'leaveOneOutChange']
          .some((field) => !isFiniteNumber(values[field]))
        || !nearlyEqual(values.change, values.end - values.start)
      ) {
        fail(`${candidate.id}: contribuição municipal inválida`)
      }
    }
    educationChange += entry.education.change
    populationChange += entry.population.change
    educationAbsoluteTotal += Math.abs(entry.education.change)
    populationAbsoluteTotal += Math.abs(entry.population.change)
  }
  if (
    !nearlyEqual(educationChange, accounting.educationValues.absoluteChange)
    || !nearlyEqual(populationChange, accounting.populationValues.absoluteChange)
    || educationAbsoluteTotal === 0
    || populationAbsoluteTotal === 0
  ) {
    fail(`${candidate.id}: soma municipal não reconcilia`)
  }

  let educationConcentration = 0
  let populationConcentration = 0
  let educationDirectionCount = 0
  let populationDirectionCount = 0
  let educationLeaveOneOutStable = true
  let populationLeaveOneOutStable = true
  for (const entry of entries) {
    const expectedEducationShare = Math.abs(entry.education.change) / educationAbsoluteTotal
    const expectedPopulationShare = Math.abs(entry.population.change) / populationAbsoluteTotal
    const expectedEducationLeaveOneOut = educationChange - entry.education.change
    const expectedPopulationLeaveOneOut = populationChange - entry.population.change
    if (
      !nearlyEqual(entry.education.absoluteShare, expectedEducationShare)
      || !nearlyEqual(entry.population.absoluteShare, expectedPopulationShare)
      || !nearlyEqual(entry.education.leaveOneOutChange, expectedEducationLeaveOneOut)
      || !nearlyEqual(entry.population.leaveOneOutChange, expectedPopulationLeaveOneOut)
    ) {
      fail(`${candidate.id}: teste municipal não recomputável`)
    }
    educationConcentration = Math.max(educationConcentration, expectedEducationShare)
    populationConcentration = Math.max(populationConcentration, expectedPopulationShare)
    if (Math.sign(entry.education.change) === Math.sign(educationChange)) {
      educationDirectionCount += 1
    }
    if (Math.sign(entry.population.change) === Math.sign(populationChange)) {
      populationDirectionCount += 1
    }
    educationLeaveOneOutStable &&= (
      Math.sign(expectedEducationLeaveOneOut) === Math.sign(educationChange)
    )
    populationLeaveOneOutStable &&= (
      Math.sign(expectedPopulationLeaveOneOut) === Math.sign(populationChange)
    )
  }
  const educationDirectionShare = educationDirectionCount / entries.length
  const populationDirectionShare = populationDirectionCount / entries.length
  const passed = (
    educationConcentration <= 0.5
    && populationConcentration <= 0.5
    && educationDirectionShare >= 0.6
    && populationDirectionShare >= 0.6
    && educationLeaveOneOutStable
    && populationLeaveOneOutStable
  )
  if (
    !nearlyEqual(tests.educationConcentration, educationConcentration)
    || !nearlyEqual(tests.populationConcentration, populationConcentration)
    || !nearlyEqual(tests.educationDirectionShare, educationDirectionShare)
    || !nearlyEqual(tests.populationDirectionShare, populationDirectionShare)
    || tests.educationLeaveOneOutStable !== educationLeaveOneOutStable
    || tests.populationLeaveOneOutStable !== populationLeaveOneOutStable
    || tests.passed !== passed
    || tests.passed !== true
  ) {
    fail(`${candidate.id}: conclusão municipal não derivada`)
  }
}

function validateReadyCandidate(candidate, pairDependencies) {
  assertPairAllowed(candidate, pairDependencies)
  if (candidate.gates.G8.status !== 'pendente_autoria') {
    fail(`${candidate.id}: G8 técnico deve aguardar autoria`)
  }
  for (const gateId of GATE_IDS.filter((id) => id !== 'G8')) {
    if (candidate.gates[gateId].status !== 'ok') {
      fail(`${candidate.id}: ${gateId} técnico não aprovado`)
    }
  }
  const accounting = validateAccountingEvidence(candidate)
  validateSensitivityEvidence(candidate, accounting)
  validateMunicipalEvidence(candidate, accounting)
  if (
    !isRecord(candidate.planningComponents)
    || !Array.isArray(candidate.planningComponents.indicatorIds)
    || candidate.planningComponents.indicatorIds.length === 0
  ) {
    fail(`${candidate.id}: componentes de planejamento inválidos`)
  }
  for (const field of ['stage', 'audience', 'phenomenon', 'scope']) {
    if (!isNonEmptyString(candidate.planningComponents[field])) {
      fail(`${candidate.id}: planningComponents.${field} ausente`)
    }
  }
  if (!Array.isArray(candidate.visualizations) || candidate.visualizations.length < 3) {
    fail(`${candidate.id}: Gate 8 sem visualizações suficientes`)
  }
  for (const visualization of candidate.visualizations) {
    if (!isNonEmptyString(visualization.id) || !isNonEmptyString(visualization.addsInformation)) {
      fail(`${candidate.id}: visualização sem id/valor adicional`)
    }
    if (visualization.kind === 'aligned-mini-charts') {
      for (const series of visualization.series ?? []) {
        const periods = series.points?.map(({ period }) => period)
        if (JSON.stringify(periods) !== JSON.stringify(visualization.periods)) {
          fail(`${candidate.id}: minigráficos com períodos desalinhados`)
        }
      }
    }
  }
}

export function validateResearchArtifact(research, pairDependencies) {
  if (!isRecord(research)) fail('artefato de pesquisa deve ser objeto')
  if (research.schemaVersion !== RESEARCH_SCHEMA) fail('schema de pesquisa divergente')
  if (research.contractVersion !== CONTRACT_VERSION) fail('contrato de pesquisa divergente')
  if (
    research.region?.slug !== 'vale-do-sinos'
    || research.region?.stateCode !== 'RS'
    || research.region?.municipalityCount !== 10
    || research.region?.municipalities?.length !== 10
  ) {
    fail('identidade regional da pesquisa divergente')
  }
  const municipalityCodes = research.region.municipalities.map(({ ibge7 }) => ibge7)
  if (
    new Set(municipalityCodes).size !== 10
    || municipalityCodes.some((code) => typeof code !== 'string' || !/^\d{7}$/u.test(code))
  ) {
    fail('códigos IBGE municipais inválidos na pesquisa')
  }
  if (
    research.generation?.networkUsed !== false
    || research.generation?.databaseUsed !== false
    || research.generation?.clockUsed !== false
    || research.generation?.modelUsed !== false
  ) {
    fail('geração da pesquisa usou recurso proibido nesta rodada')
  }
  if (!Array.isArray(research.sourceCatalog) || !Array.isArray(research.sourceManifest)) {
    fail('fontes da pesquisa ausentes')
  }
  const sourceIds = new Set(research.sourceCatalog.map(({ id }) => id))
  if (sourceIds.size !== research.sourceCatalog.length) fail('sourceId duplicado')
  if (
    research.sourceManifest.length < 20
    || research.sourceManifest.some(
      (item) => !isNonEmptyString(item.path) || !/^[a-f0-9]{64}$/u.test(item.sha256),
    )
  ) {
    fail('manifesto de fontes da pesquisa incompleto')
  }
  if (!Array.isArray(research.candidates) || research.candidates.length !== 6) {
    fail('pesquisa deve conter seis candidatos')
  }
  const candidateIds = new Set()
  const globalFactIds = new Set()
  let readyCount = 0
  let retainedCount = 0
  for (const candidate of research.candidates) {
    if (!isNonEmptyString(candidate.id) || candidateIds.has(candidate.id)) {
      fail('candidate id ausente ou duplicado')
    }
    candidateIds.add(candidate.id)
    validateGateMap(candidate.gates, candidate.id)
    if (!Array.isArray(candidate.facts)) fail(`${candidate.id}: facts não é array`)
    const factIds = collectFactIds(candidate)
    if (factIds.size !== candidate.facts.length) fail(`${candidate.id}: fato duplicado`)
    for (const fact of candidate.facts) {
      validateFact(fact, sourceIds, candidate.id)
      if (globalFactIds.has(fact.id)) fail(`fato global duplicado: ${fact.id}`)
      globalFactIds.add(fact.id)
    }
    for (const gateId of GATE_IDS) {
      for (const factId of candidate.gates[gateId].evidenceFactIds) {
        if (!factIds.has(factId)) fail(`${candidate.id}.${gateId}: fato desconhecido`)
      }
    }
    const expectedDecision = deriveEngineDecision(candidate.gates)
    if (candidate.engineDecision !== expectedDecision) {
      fail(`${candidate.id}: decisão técnica não derivada`)
    }
    if (expectedDecision === 'apta_para_autoria') {
      readyCount += 1
      validateReadyCandidate(candidate, pairDependencies)
    } else {
      retainedCount += 1
      if (
        candidate.facts.length !== 0
        || candidate.visualizations.length !== 0
        || candidate.planningComponents !== null
      ) {
        fail(`${candidate.id}: retenção deveria ser silenciosa`)
      }
    }
  }
  if (readyCount !== 3 || retainedCount !== 3) {
    fail(`contagem técnica inesperada: ${readyCount}/${retainedCount}`)
  }
  if (
    research.summary?.technicalGate6 !== 'aprovado'
    || research.summary?.technicalGate8 !== 'aprovado'
  ) {
    fail('gates técnicos 6 e 8 não aprovados')
  }
  return true
}

function requiredNarrativePaths(publicCard) {
  return [
    ...REQUIRED_NARRATIVE_PATHS,
    ...publicCard.education_facts.map((_, index) => `education_facts[${index}]`),
    ...publicCard.territorial_facts.map((_, index) => `territorial_facts[${index}]`),
  ]
}

function validateFactReferences(authorItem, candidate) {
  const references = authorItem.factReferences
  const required = requiredNarrativePaths(authorItem.public).sort()
  assertExactKeys(references, required, `${candidate.id}.factReferences`)
  const factIds = collectFactIds(candidate)
  for (const [field, ids] of Object.entries(references)) {
    if (
      !Array.isArray(ids)
      || ids.length === 0
      || new Set(ids).size !== ids.length
      || ids.some((id) => !factIds.has(id))
    ) {
      fail(`${candidate.id}.${field}: referências de fatos inválidas`)
    }
  }
}

function cloneGates(candidate) {
  return Object.fromEntries(
    GATE_IDS.map((gateId) => [gateId, structuredClone(candidate.gates[gateId])]),
  )
}

function buildCard(authorItem, candidate, dependencies) {
  assertExactKeys(authorItem.public, PUBLIC_KEYS, `${candidate.id}.public`)
  if (
    authorItem.candidateId !== candidate.id
    || authorItem.public.id !== candidate.id
    || authorItem.public.direction !== 'educacao_para_territorio'
  ) {
    fail(`${candidate.id}: identidade da autoria divergente`)
  }
  validateFactReferences(authorItem, candidate)
  const languageViolations = lintCard(authorItem.public, dependencies.vocab)
  if (languageViolations.length > 0) {
    fail(`${candidate.id}: linguagem bloqueada: ${JSON.stringify(languageViolations)}`)
  }
  const gates = cloneGates(candidate)
  gates.G8 = {
    status: 'ok',
    reasonCode: 'texto-publico-aprovado-pelo-linter-e-revisao-editorial',
    evidenceFactIds: [],
  }
  const publicationDecision = derivePublicationDecision(gates)
  if (publicationDecision !== 'publicada') {
    fail(`${candidate.id}: autoria não fechou os dez gates`)
  }
  const card = {
    ...structuredClone(authorItem.public),
    internal: {
      mechanism_id: candidate.mechanismId,
      universe_check: 'ok',
      temporal_check: 'ok',
      sensitivity_check: 'ok',
      territorial_check: 'ok',
      publication_decision: publicationDecision,
      gates,
      fact_references: structuredClone(authorItem.factReferences),
      planning_components: structuredClone(candidate.planningComponents),
      visualization_ids: candidate.visualizations.map(({ id }) => id),
      research_candidate_id: candidate.id,
    },
  }
  const contractViolations = validateCardContract(card)
  const catalogViolations = validateCardCatalog(card, dependencies.cardDependencies)
  if (contractViolations.length > 0 || catalogViolations.length > 0) {
    fail(
      `${candidate.id}: contrato/catálogo: ${JSON.stringify([
        ...contractViolations,
        ...catalogViolations,
      ])}`,
    )
  }
  return card
}

export function buildFirstOutputArtifact(
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
    || authorship.cards.length !== 3
  ) {
    fail('autoria da primeira saída inválida')
  }
  if (
    researchReference?.path !== 'scripts/checks/fixtures/vocacoes-pne/primeira-saida-pesquisa-vale-do-sinos.json'
    || !/^[a-f0-9]{64}$/u.test(researchReference?.sha256)
    || !Number.isInteger(researchReference?.byteSize)
  ) {
    fail('referência ao artefato de pesquisa inválida')
  }

  const candidateById = new Map(
    research.candidates.map((candidate) => [candidate.id, candidate]),
  )
  const authoredIds = new Set()
  const cards = authorship.cards.map((authorItem) => {
    const candidate = candidateById.get(authorItem.candidateId)
    if (!candidate || candidate.engineDecision !== 'apta_para_autoria') {
      fail(`autoria aponta para candidato não apto: ${authorItem.candidateId}`)
    }
    if (authoredIds.has(candidate.id)) fail(`autoria duplicada: ${candidate.id}`)
    authoredIds.add(candidate.id)
    return buildCard(authorItem, candidate, dependencies)
  })
  const readyIds = research.candidates
    .filter(({ engineDecision }) => engineDecision === 'apta_para_autoria')
    .map(({ id }) => id)
  if (JSON.stringify([...authoredIds]) !== JSON.stringify(readyIds)) {
    fail('autoria não cobre exatamente os candidatos aptos, na ordem editorial')
  }
  const educationalSeriesIds = cards.map(
    (card) => candidateById.get(card.id).educationalSeriesId,
  )
  if (new Set(educationalSeriesIds).size !== cards.length) {
    fail('G9: histórias redundantes por resultado educacional')
  }
  const retained = research.candidates
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

  const artifact = {
    schemaVersion: OUTPUT_SCHEMA,
    contractVersion: CONTRACT_VERSION,
    region: structuredClone(research.region),
    researchArtifact: structuredClone(researchReference),
    cards,
    retainedCandidates: retained,
    publicProjection: cards.map(serializePublic),
    summary: {
      candidateCount: research.candidates.length,
      publishedCount: cards.length,
      retainedCount: retained.length,
      gate6: cards.length >= 3 && cards.length <= 5 ? 'aprovado' : 'reprovado',
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
      builderVersion: 'generate-vocacoes-pne-primeira-saida.mjs v1.0.0',
    },
  }
  validateFirstOutputArtifact(artifact, research, dependencies)
  return artifact
}

function collectInternalKeyPaths(value, field = '') {
  const internalKeys = new Set([
    'internal',
    'mechanism_id',
    'publication_decision',
    'gates',
    'fact_references',
    'planning_components',
    'visualization_ids',
    'research_candidate_id',
  ])
  if (Array.isArray(value)) {
    return value.flatMap((item, index) => collectInternalKeyPaths(item, `${field}[${index}]`))
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

export function validateFirstOutputArtifact(artifact, research, dependencies) {
  validateResearchArtifact(research, dependencies.pairDependencies)
  if (
    artifact?.schemaVersion !== OUTPUT_SCHEMA
    || artifact?.contractVersion !== CONTRACT_VERSION
  ) {
    fail('saída final com schema/contrato divergente')
  }
  if (JSON.stringify(artifact.region) !== JSON.stringify(research.region)) {
    fail('identidade regional da saída final divergente')
  }
  if (
    artifact.researchArtifact?.path
      !== 'scripts/checks/fixtures/vocacoes-pne/primeira-saida-pesquisa-vale-do-sinos.json'
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
    || artifact.generation?.builderVersion
      !== 'generate-vocacoes-pne-primeira-saida.mjs v1.0.0'
  ) {
    fail('metadados de geração da saída final inválidos')
  }
  if (!Array.isArray(artifact.cards) || artifact.cards.length !== 3) {
    fail('saída final deve conter três cartões')
  }
  const candidateById = new Map(
    research.candidates.map((candidate) => [candidate.id, candidate]),
  )
  const readyIds = research.candidates
    .filter(({ engineDecision }) => engineDecision === 'apta_para_autoria')
    .map(({ id }) => id)
  const cardIds = artifact.cards.map(({ id }) => id)
  if (JSON.stringify(cardIds) !== JSON.stringify(readyIds)) {
    fail('saída final não cobre os candidatos aptos na ordem editorial')
  }
  for (const card of artifact.cards) {
    const candidate = candidateById.get(card.id)
    if (!candidate || candidate.engineDecision !== 'apta_para_autoria') {
      fail(`cartão sem candidato apto: ${card.id}`)
    }
    assertExactKeys(
      card.internal,
      new Set([
        'mechanism_id',
        'universe_check',
        'temporal_check',
        'sensitivity_check',
        'territorial_check',
        'publication_decision',
        'gates',
        'fact_references',
        'planning_components',
        'visualization_ids',
        'research_candidate_id',
      ]),
      `${card.id}.internal`,
    )
    if (derivePublicationDecision(card.internal.gates) !== 'publicada') {
      fail(`${card.id}: decisão final não derivada dos gates`)
    }
    if (
      card.internal.publication_decision !== 'publicada'
      || card.internal.mechanism_id !== candidate.mechanismId
      || card.internal.research_candidate_id !== candidate.id
      || ['universe_check', 'temporal_check', 'sensitivity_check', 'territorial_check']
        .some((field) => card.internal[field] !== 'ok')
      || JSON.stringify(card.internal.planning_components)
        !== JSON.stringify(candidate.planningComponents)
      || JSON.stringify(card.internal.visualization_ids)
        !== JSON.stringify(candidate.visualizations.map(({ id }) => id))
    ) {
      fail(`${card.id}: campos internos divergentes da pesquisa`)
    }
    validateFactReferences(
      {
        public: serializePublic(card),
        factReferences: card.internal.fact_references,
      },
      candidate,
    )
    if (lintCard(card, dependencies.vocab).length > 0) {
      fail(`${card.id}: regressão de linguagem`)
    }
    if (
      validateCardContract(card).length > 0
      || validateCardCatalog(card, dependencies.cardDependencies).length > 0
    ) {
      fail(`${card.id}: regressão de contrato/catálogo`)
    }
  }
  const projection = artifact.cards.map(serializePublic)
  if (JSON.stringify(artifact.publicProjection) !== JSON.stringify(projection)) {
    fail('projeção pública não corresponde à allowlist')
  }
  if (collectInternalKeyPaths(artifact.publicProjection).length > 0) {
    fail('projeção pública contém chave interna')
  }
  const expectedRetained = research.candidates
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
  if (JSON.stringify(artifact.retainedCandidates) !== JSON.stringify(expectedRetained)) {
    fail('retenções finais inválidas ou expostas')
  }
  const expectedSummary = {
    candidateCount: research.candidates.length,
    publishedCount: artifact.cards.length,
    retainedCount: expectedRetained.length,
    gate6: 'aprovado',
    gate8: 'aprovado',
  }
  if (JSON.stringify(artifact.summary) !== JSON.stringify(expectedSummary)) {
    fail('Gates 6 e 8 finais não aprovados')
  }
  return true
}
