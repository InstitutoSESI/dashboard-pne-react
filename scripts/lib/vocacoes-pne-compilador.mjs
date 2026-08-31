import { createHash } from 'node:crypto'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import { buildExpectedOutput as buildFirstExpectedOutput } from '../generate-vocacoes-pne-primeira-saida.mjs'
import { buildExpectedOutput as buildSecondExpectedOutput } from '../generate-vocacoes-pne-segunda-saida.mjs'
import {
  lintPublicDocument,
  loadVocabulario,
  serializePublic,
} from './vocacoes-pne-linter.mjs'
import {
  parseVocacoesPneNarrative,
  VOCACOES_PNE_NARRATIVE_CONTRACT_VERSION,
  VOCACOES_PNE_NARRATIVE_SCHEMA,
} from '../../src/features/vocacoes-regiao/vocacoesPneNarrativeContract.js'

const ROOT = fileURLToPath(new URL('../../', import.meta.url))
const FIXTURES = path.join(ROOT, 'scripts', 'checks', 'fixtures', 'vocacoes-pne')

export const COMPILER_VERSION = 'vocacoes-pne-compilador-v1.0.0'
export const TRACE_SCHEMA = 'vocacoes-pne-narrative-trace-v1'

export const COMPILER_PATHS = Object.freeze({
  firstResearch: path.join(FIXTURES, 'primeira-saida-pesquisa-vale-do-sinos.json'),
  firstIntegrated: path.join(FIXTURES, 'primeira-saida-vale-do-sinos.json'),
  secondResearch: path.join(FIXTURES, 'segunda-saida-pesquisa-vale-do-sinos.json'),
  secondIntegrated: path.join(FIXTURES, 'segunda-saida-vale-do-sinos.json'),
  authorship: path.join(FIXTURES, 'compilador-autoria.json'),
  publicOutput: path.join(
    ROOT,
    'src',
    'features',
    'vocacoes-regiao',
    'generated',
    'vocacoesPneValeDoSinos.json',
  ),
  traceOutput: path.join(FIXTURES, 'compilador-registro-vale-do-sinos.json'),
})

export const FROZEN_INPUTS = Object.freeze({
  firstResearch: '9852d0d106deaa3df3dcefc587a08bf3f5e14d2909d159ebe013593d55d213cd',
  firstIntegrated: 'cc7989a0d3417f0ba5f39f29283de9f61b1c734b03238e0ded252c1d59f7e9ea',
  secondResearch: 'bee5d4b7a255631eb6dd49a8c0cb80e7ae68d2f8ff0c5ccc26e78047e31754b8',
  secondIntegrated: 'daae50bcb85294af78c3fabdfa9ce233fc42f05bc904082ec8ccb74c35118078',
})

export const FUTURE_LABELS = Object.freeze({
  mudanca_observada: 'Mudança já em curso',
  tendencia_sustentada: 'Tendência para os próximos anos',
  estudo_setorial: 'Tendência para os próximos anos',
  cenario: 'Tema presente nos cenários',
})

const GATE_IDS = Object.freeze([
  'G1',
  'G2',
  'G3',
  'G4',
  'G5',
  'G6',
  'G7',
  'G8',
  'G9',
  'G10',
])

const BLOCKED_PUBLIC_KEYS = new Set([
  'internal',
  'gates',
  'checks',
  'mechanism_id',
  'mechanismId',
  'reasonCode',
  'evidenceFactIds',
  'factId',
  'factIds',
  'visualizationId',
  'visualizationIds',
  'visualization_ids',
  'research_candidate_id',
  'researchArtifact',
  'researchPath',
  'retainedCandidates',
  'transformation_class',
  'future_basis',
  'publication_decision',
  'universe_check',
  'temporal_check',
  'sensitivity_check',
  'territorial_check',
])

const AUTHORSHIP_ROOT_KEYS = [
  'schemaVersion',
  'contractVersion',
  'page',
  'highlights',
  'sections',
  'details',
  'consultation',
  'visuals',
]

export class VocacoesPneCompilerError extends Error {
  constructor(message, options) {
    super(message, options)
    this.name = 'VocacoesPneCompilerError'
  }
}

export function sha256(bytes) {
  return createHash('sha256').update(bytes).digest('hex')
}

export function canonicalJson(value) {
  return `${JSON.stringify(value, null, 2)}\n`
}

function fail(message) {
  throw new VocacoesPneCompilerError(message)
}

function isRecord(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
}

function assertRecord(value, label) {
  if (!isRecord(value)) fail(`${label} deve ser objeto`)
}

function assertExactKeys(value, expected, label) {
  assertRecord(value, label)
  const actual = Object.keys(value).sort()
  const wanted = [...expected].sort()
  if (
    actual.length !== wanted.length
    || actual.some((key, index) => key !== wanted[index])
  ) {
    fail(`${label} contém campos extras ou ausentes; esperados: ${expected.join(', ')}`)
  }
}

function assertNonEmptyString(value, label) {
  if (typeof value !== 'string' || value.trim().length === 0) {
    fail(`${label} deve ser string não vazia`)
  }
}

function assertStringMap(value, label) {
  assertRecord(value, label)
  if (Object.keys(value).length === 0) fail(`${label} deve ser objeto não vazio`)
  for (const [key, item] of Object.entries(value)) {
    assertNonEmptyString(key, `${label}.chave`)
    assertNonEmptyString(item, `${label}.${key}`)
  }
}

function assertAuthorship(authorship, cardIds) {
  assertExactKeys(authorship, AUTHORSHIP_ROOT_KEYS, 'autoria')
  if (authorship.schemaVersion !== 'vocacoes-pne-compilador-autoria-v1') {
    fail('autoria.schemaVersion inválido')
  }
  if (authorship.contractVersion !== VOCACOES_PNE_NARRATIVE_CONTRACT_VERSION) {
    fail('autoria.contractVersion incompatível')
  }

  assertExactKeys(
    authorship.page,
    ['eyebrow', 'titleTemplate', 'framing', 'referenceLabel'],
    'autoria.page',
  )
  for (const field of ['eyebrow', 'titleTemplate', 'framing', 'referenceLabel']) {
    assertNonEmptyString(authorship.page[field], `autoria.page.${field}`)
  }
  if (!authorship.page.titleTemplate.includes('{regionName}')) {
    fail('autoria.page.titleTemplate deve conter {regionName}')
  }

  if (!Array.isArray(authorship.highlights) || authorship.highlights.length !== 3) {
    fail('autoria.highlights deve conter exatamente três itens')
  }
  const highlighted = new Set()
  authorship.highlights.forEach((highlight, index) => {
    assertExactKeys(highlight, ['cardId', 'label'], `autoria.highlights[${index}]`)
    assertNonEmptyString(highlight.cardId, `autoria.highlights[${index}].cardId`)
    assertNonEmptyString(highlight.label, `autoria.highlights[${index}].label`)
    if (!cardIds.has(highlight.cardId)) fail(`destaque sem cartão: ${highlight.cardId}`)
    if (highlighted.has(highlight.cardId)) fail(`destaque duplicado: ${highlight.cardId}`)
    highlighted.add(highlight.cardId)
  })

  assertExactKeys(
    authorship.sections,
    ['educacao_para_territorio', 'territorio_para_educacao'],
    'autoria.sections',
  )
  for (const direction of ['educacao_para_territorio', 'territorio_para_educacao']) {
    const section = authorship.sections[direction]
    assertExactKeys(section, ['id', 'title', 'question'], `autoria.sections.${direction}`)
    for (const field of ['id', 'title', 'question']) {
      assertNonEmptyString(section[field], `autoria.sections.${direction}.${field}`)
    }
  }

  assertExactKeys(
    authorship.details,
    ['evolution', 'municipalities', 'pne', 'sources'],
    'autoria.details',
  )
  for (const field of ['evolution', 'municipalities', 'pne', 'sources']) {
    assertNonEmptyString(authorship.details[field], `autoria.details.${field}`)
  }

  assertExactKeys(authorship.consultation, ['title', 'description'], 'autoria.consultation')
  assertNonEmptyString(authorship.consultation.title, 'autoria.consultation.title')
  assertNonEmptyString(authorship.consultation.description, 'autoria.consultation.description')

  assertRecord(authorship.visuals, 'autoria.visuals')
  const visualIds = Object.keys(authorship.visuals).sort()
  const expectedIds = [...cardIds].sort()
  if (
    visualIds.length !== expectedIds.length
    || visualIds.some((id, index) => id !== expectedIds[index])
  ) {
    fail('autoria.visuals deve declarar exatamente um visual para cada cartão')
  }
  for (const [cardId, visual] of Object.entries(authorship.visuals)) {
    if (cardId === 'vds-deslocamento-oferta') {
      assertExactKeys(
        visual,
        ['title', 'categoryLabels', 'seriesLabels'],
        `autoria.visuals.${cardId}`,
      )
      assertStringMap(visual.categoryLabels, `autoria.visuals.${cardId}.categoryLabels`)
    } else {
      assertExactKeys(visual, ['title', 'seriesLabels'], `autoria.visuals.${cardId}`)
    }
    assertNonEmptyString(visual.title, `autoria.visuals.${cardId}.title`)
    assertStringMap(visual.seriesLabels, `autoria.visuals.${cardId}.seriesLabels`)
  }
}

export function validateFrozenInputBytes(label, bytes) {
  if (!Object.hasOwn(FROZEN_INPUTS, label)) fail(`input congelado desconhecido: ${label}`)
  const actual = sha256(bytes)
  if (actual !== FROZEN_INPUTS[label]) {
    fail(`${label}: SHA-256 divergente (${actual})`)
  }
  return actual
}

function assertIntegratedRecomposition(label, integratedBytes, expected) {
  const expectedBytes = Buffer.from(canonicalJson(expected), 'utf8')
  if (!integratedBytes.equals(expectedBytes)) {
    fail(`${label}: artefato integrado diverge da recomposição do buildExpectedOutput()`)
  }
}

function assertIdentity(inputs) {
  const identities = [
    ['pesquisa R5', inputs.firstResearch.region],
    ['integrado R5', inputs.firstIntegrated.region],
    ['pesquisa R6', inputs.secondResearch.region],
    ['integrado R6', inputs.secondIntegrated.region],
  ]
  const expected = JSON.stringify(identities[0][1])
  for (const [label, identity] of identities) {
    if (JSON.stringify(identity) !== expected) {
      fail(`${label}: identidade regional diverge dos quatro insumos`)
    }
  }
  const region = identities[0][1]
  if (
    region.stateCode !== 'RS'
    || region.slug !== 'vale-do-sinos'
    || region.municipalityCount !== 10
    || !Array.isArray(region.municipalities)
    || region.municipalities.length !== 10
  ) {
    fail('identidade regional fora do piloto Vale do Sinos/RS')
  }
  const seenCodes = new Set()
  for (const [index, municipality] of region.municipalities.entries()) {
    assertExactKeys(municipality, ['ibge7', 'name'], `region.municipalities[${index}]`)
    if (typeof municipality.ibge7 !== 'string' || !/^\d{7}$/u.test(municipality.ibge7)) {
      fail(`region.municipalities[${index}].ibge7 deve permanecer string de sete dígitos`)
    }
    assertNonEmptyString(municipality.name, `region.municipalities[${index}].name`)
    if (seenCodes.has(municipality.ibge7)) fail(`código IBGE duplicado: ${municipality.ibge7}`)
    seenCodes.add(municipality.ibge7)
  }
  return region
}

function assertAllGatesOk(card, label) {
  const gates = card.internal?.gates
  assertRecord(gates, `${label}.internal.gates`)
  const actual = Object.keys(gates).sort()
  const expected = [...GATE_IDS].sort()
  if (
    actual.length !== expected.length
    || actual.some((gateId, index) => gateId !== expected[index])
  ) {
    fail(`${label}: conjunto G1–G10 incompleto`)
  }
  for (const gateId of GATE_IDS) {
    if (gates[gateId]?.status !== 'ok') fail(`${label}.${gateId}: gate não aprovado`)
  }
  if (card.internal.publication_decision !== 'publicada') {
    fail(`${label}: decisão final não publicada`)
  }
}

function assertPublicProjection(integrated, direction, expectedCount, label) {
  if (!Array.isArray(integrated.cards) || integrated.cards.length !== expectedCount) {
    fail(`${label}: deve conter exatamente ${expectedCount} cartões integrados`)
  }
  if (
    !Array.isArray(integrated.publicProjection)
    || integrated.publicProjection.length !== expectedCount
  ) {
    fail(`${label}: publicProjection deve conter exatamente ${expectedCount} cartões`)
  }
  for (const [index, card] of integrated.cards.entries()) {
    if (card.direction !== direction) fail(`${label}.cards[${index}]: direção inválida`)
    assertAllGatesOk(card, `${label}.cards[${index}]`)
  }
  const projectedIds = integrated.publicProjection.map(({ id }) => id)
  const integratedIds = integrated.cards.map(({ id }) => id)
  if (JSON.stringify(projectedIds) !== JSON.stringify(integratedIds)) {
    fail(`${label}: ordem da publicProjection diverge dos cartões aprovados`)
  }
}

function assertSecondOutputFutureRules(secondIntegrated) {
  for (const card of secondIntegrated.cards) {
    const internal = card.internal
    const futureBasis = internal.future_basis
    if (!Object.hasOwn(FUTURE_LABELS, internal.transformation_class)) {
      fail(`${card.id}: transformation_class fora da tabela fechada`)
    }
    if (internal.transformation_class === 'cenario') {
      fail(`${card.id}: cenário é recusado no piloto`)
    }
    if (!['observed_series', 'observed_snapshot'].includes(futureBasis?.basisType)) {
      fail(`${card.id}: base futura não observada no piloto`)
    }
    if (futureBasis.scenarioId !== null) fail(`${card.id}: scenarioId deve ser null`)
    if (
      !Array.isArray(futureBasis.futureNumericValues)
      || futureBasis.futureNumericValues.length !== 0
    ) {
      fail(`${card.id}: número futuro é recusado no piloto`)
    }
  }
}

function findCandidate(research, cardId) {
  const candidate = research.candidates?.find(({ id }) => id === cardId)
  if (!candidate) fail(`candidata publicada ausente na pesquisa: ${cardId}`)
  return candidate
}

function findFact(candidate, predicate, label) {
  const facts = candidate.facts?.filter(predicate) ?? []
  if (facts.length !== 1) fail(`${candidate.id}: fato ${label} deve resolver uma vez`)
  return facts[0]
}

function findVisual(candidate, id) {
  const visual = candidate.visualizations?.find((item) => item.id === id)
  if (!visual) fail(`${candidate.id}: visual aprovado ausente: ${id}`)
  return visual
}

function assertFiniteValues(values, label) {
  if (!Array.isArray(values) || values.length === 0 || !values.every(Number.isFinite)) {
    fail(`${label}: valores devem ser números finitos não vazios`)
  }
}

function buildAlignedVisual(card, candidate, authorVisual) {
  const visualId = card.internal.visualization_ids.find((id) => id.endsWith('.visual.temporal'))
  if (!visualId) fail(`${card.id}: visual temporal não declarado`)
  const visual = findVisual(candidate, visualId)
  if (visual.kind !== 'aligned-mini-charts') fail(`${card.id}: template temporal incompatível`)
  if (!Array.isArray(visual.periods) || visual.periods.length < 2) {
    fail(`${card.id}: períodos do visual ausentes`)
  }
  if (!Array.isArray(visual.series) || visual.series.length !== 2) {
    fail(`${card.id}: visual deve conter duas séries aprovadas`)
  }
  const declaredLabels = Object.keys(authorVisual.seriesLabels).sort()
  const expectedLabels = visual.series.map(({ seriesId }) => seriesId).sort()
  if (
    declaredLabels.length !== expectedLabels.length
    || declaredLabels.some((seriesId, index) => seriesId !== expectedLabels[index])
  ) {
    fail(`${card.id}: rótulos autorais não correspondem às duas séries aprovadas`)
  }
  const series = visual.series.map((entry) => {
    const label = authorVisual.seriesLabels[entry.seriesId]
    assertNonEmptyString(label, `autoria.visuals.${card.id}.seriesLabels.${entry.seriesId}`)
    const facts = candidate.facts.filter((fact) => fact.seriesId === entry.seriesId)
    const unit = entry.unit ?? facts.find((fact) => typeof fact.unit === 'string')?.unit
    assertNonEmptyString(unit, `${card.id}: unidade da série ${entry.seriesId}`)
    const points = entry.points ?? []
    if (
      points.length !== visual.periods.length
      || points.some((point, index) => point.period !== visual.periods[index])
    ) {
      fail(`${card.id}: pontos do visual não alinham com os períodos`)
    }
    const values = points.map(({ value }) => value)
    assertFiniteValues(values, `${card.id}: série ${entry.seriesId}`)
    const endpointFact = facts.find((fact) => (
      Number.isFinite(fact.values?.start) && Number.isFinite(fact.values?.end)
    ))
    if (
      !endpointFact
      || values[0] !== endpointFact.values.start
      || values.at(-1) !== endpointFact.values.end
    ) {
      fail(`${card.id}: visual diverge dos valores inicial/final do fato ${entry.seriesId}`)
    }
    return { label, unit, values }
  })
  return {
    publicVisual: {
      template: 'aligned_series',
      title: authorVisual.title,
      alt_text: authorVisual.title,
      periods: [...visual.periods],
      series,
    },
    trace: {
      visualizationIds: [visual.id],
      factIds: visual.series.flatMap(({ seriesId }) => (
        candidate.facts.filter((fact) => fact.seriesId === seriesId).map(({ id }) => id)
      )),
    },
  }
}

function buildCategoryVisual(card, candidate, authorVisual) {
  assertExactKeys(
    authorVisual.categoryLabels,
    ['total', 'fundamental', 'medio'],
    `autoria.visuals.${card.id}.categoryLabels`,
  )
  assertExactKeys(
    authorVisual.seriesLabels,
    ['region', 'state'],
    `autoria.visuals.${card.id}.seriesLabels`,
  )
  const regionFact = findFact(
    candidate,
    ({ id }) => id === `${card.id}.deslocamento`,
    'deslocamento regional',
  )
  const stateFact = findFact(
    candidate,
    ({ id }) => id === `${card.id}.comparacao-rs`,
    'comparação estadual',
  )
  const regionByUniverse = new Map(
    regionFact.values.entries.map((entry) => [entry.universe, entry.outsideSharePercent]),
  )
  const stateByUniverse = new Map(
    stateFact.values.entries.map((entry) => [entry.universe, entry.stateOutsideSharePercent]),
  )
  const stateRegionByUniverse = new Map(
    stateFact.values.entries.map((entry) => [entry.universe, entry.regionOutsideSharePercent]),
  )
  const universes = ['total', 'fundamental', 'medio']
  const categories = universes.map((universe) => {
    const regionValue = regionByUniverse.get(universe)
    const stateValue = stateByUniverse.get(universe)
    if (!Number.isFinite(regionValue) || !Number.isFinite(stateValue)) {
      fail(`${card.id}: percentual ausente para o universo ${universe}`)
    }
    if (stateRegionByUniverse.get(universe) !== regionValue) {
      fail(`${card.id}: comparação RS diverge do fato regional em ${universe}`)
    }
    return {
      label: authorVisual.categoryLabels[universe],
      region_value: regionValue,
      state_value: stateValue,
    }
  })
  for (const label of categories.map((category) => category.label)) {
    assertNonEmptyString(label, `${card.id}: rótulo de categoria`)
  }
  const visualizationIds = [
    `${card.id}.visual.etapas`,
    `${card.id}.visual.rs`,
  ]
  visualizationIds.forEach((visualId) => {
    if (!card.internal.visualization_ids.includes(visualId)) {
      fail(`${card.id}: visual não aprovado: ${visualId}`)
    }
    findVisual(candidate, visualId)
  })
  return {
    publicVisual: {
      template: 'category_bars',
      title: authorVisual.title,
      alt_text: authorVisual.title,
      unit: 'percentual',
      series_labels: {
        region: authorVisual.seriesLabels.region,
        state: authorVisual.seriesLabels.state,
      },
      categories,
    },
    trace: {
      visualizationIds,
      factIds: [regionFact.id, stateFact.id],
    },
  }
}

function buildMunicipalDistribution(card, candidate, region) {
  const fact = findFact(
    candidate,
    ({ kind }) => ['municipal-decomposition', 'municipal-exposure'].includes(kind),
    'municipal',
  )
  const entries = fact.values?.entries
  if (!Array.isArray(entries) || entries.length !== 10) {
    fail(`${card.id}: fato municipal deve conter dez municípios`)
  }
  const municipalityByCode = new Map(
    region.municipalities.map(({ ibge7, name }) => [ibge7, name]),
  )
  const seenCodes = new Set()
  const items = entries.map((entry) => {
    let value
    let unit
    if (card.direction === 'educacao_para_territorio') {
      value = entry.education?.change
      unit = 'matrículas'
    } else if (card.id === 'vds-coortes-rede') {
      value = entry.change
      unit = 'pessoas'
    } else {
      value = entry.universes?.medio?.outsideSharePercent
      unit = 'percentual'
    }
    if (!Number.isFinite(value)) fail(`${card.id}: valor municipal inválido para ${entry.ibgeCode}`)
    if (typeof entry.ibgeCode !== 'string' || !/^\d{7}$/u.test(entry.ibgeCode)) {
      fail(`${card.id}: código IBGE municipal inválido`)
    }
    assertNonEmptyString(entry.name, `${card.id}: nome municipal`)
    if (!municipalityByCode.has(entry.ibgeCode)) {
      fail(`${card.id}: município fora da identidade regional: ${entry.ibgeCode}`)
    }
    if (municipalityByCode.get(entry.ibgeCode) !== entry.name) {
      fail(`${card.id}: nome municipal diverge da identidade para ${entry.ibgeCode}`)
    }
    if (seenCodes.has(entry.ibgeCode)) fail(`${card.id}: município duplicado ${entry.ibgeCode}`)
    seenCodes.add(entry.ibgeCode)
    return {
      publicItem: { name: entry.name, value },
      traceItem: { ibgeCode: entry.ibgeCode, name: entry.name },
      unit,
    }
  })
  if (new Set(items.map(({ unit }) => unit)).size !== 1) fail(`${card.id}: unidade municipal divergente`)
  if (seenCodes.size !== municipalityByCode.size) fail(`${card.id}: cobertura municipal incompleta`)
  return {
    publicDistribution: {
      unit: items[0].unit,
      period: { start: fact.period.start, end: fact.period.end },
      items: items.map(({ publicItem }) => publicItem),
    },
    trace: {
      factId: fact.id,
      municipalities: items.map(({ traceItem }) => traceItem),
    },
  }
}

function sourceIndex(firstResearch, secondResearch) {
  const result = new Map()
  for (const source of [...firstResearch.sourceCatalog, ...secondResearch.sourceCatalog]) {
    const existing = result.get(source.id)
    if (existing && JSON.stringify(existing) !== JSON.stringify(source)) {
      fail(`sourceId divergente entre pesquisas: ${source.id}`)
    }
    result.set(source.id, source)
  }
  return result
}

function factIndex(candidate) {
  const result = new Map()
  for (const fact of candidate.facts) {
    if (result.has(fact.id)) fail(`${candidate.id}: fact id duplicado ${fact.id}`)
    result.set(fact.id, fact)
  }
  return result
}

function unique(values) {
  return [...new Set(values)]
}

function collectStringLeaves(value, field = '', result = []) {
  if (typeof value === 'string') {
    result.push({ field, value })
    return result
  }
  if (Array.isArray(value)) {
    value.forEach((item, index) => collectStringLeaves(item, `${field}[${index}]`, result))
    return result
  }
  if (!isRecord(value)) return result
  for (const [key, child] of Object.entries(value)) {
    collectStringLeaves(child, field ? `${field}.${key}` : key, result)
  }
  return result
}

function sourceIdsForFacts(factIds, facts) {
  return unique(factIds.map((factId) => facts.get(factId)?.sourceId).filter(Boolean))
}

function buildTextTrace(document, cardContexts, sources) {
  return collectStringLeaves(document).map(({ field, value }) => {
    const cardMatch = /^sections\[(\d+)\]\.cards\[(\d+)\]\.(.+)$/u.exec(field)
    if (!cardMatch) {
      const origin = field.startsWith('region.')
        ? 'research_identity'
        : field.startsWith('generation.') || ['schemaVersion', 'contractVersion'].includes(field)
          ? 'compiler_contract'
          : 'authorship'
      return {
        publicPath: field,
        valueSha256: sha256(Buffer.from(value, 'utf8')),
        origin,
        factIds: [],
        visualizationIds: [],
        sourceIds: [],
      }
    }

    const context = cardContexts.get(`${cardMatch[1]}:${cardMatch[2]}`)
    if (!context) fail(`trace sem contexto para ${field}`)
    const localPath = cardMatch[3]
    let origin = 'integrated_card'
    let factIds = context.card.internal.fact_references[localPath] ?? []
    let visualizationIds = []

    if (localPath === 'future_label') origin = 'derived_label'
    if (localPath.startsWith('primary_visual.')) {
      origin = 'authorship_visual'
      factIds = context.visualTrace.factIds
      visualizationIds = context.visualTrace.visualizationIds
    } else if (localPath.startsWith('municipal_distribution.items[')) {
      origin = 'research_fact'
      factIds = [context.municipalTrace.factId]
    } else if (/^sources\[\d+\]$/u.test(localPath)) {
      const matching = [...sources.values()].find(({ label }) => label === value)
      factIds = context.candidate.facts
        .filter(({ sourceId }) => sourceId === matching?.id)
        .map(({ id }) => id)
    }

    const facts = factIndex(context.candidate)
    return {
      publicPath: field,
      valueSha256: sha256(Buffer.from(value, 'utf8')),
      origin,
      factIds: [...factIds],
      visualizationIds: [...visualizationIds],
      sourceIds: sourceIdsForFacts(factIds, facts),
    }
  })
}

function assertNoBlockedPublicContent(value, retainedIds) {
  const visit = (item, field = '') => {
    if (typeof item === 'string') {
      if (retainedIds.has(item)) fail(`candidata retida vazou em ${field}`)
      if (/primeira-saida-pesquisa|segunda-saida-pesquisa|scripts[\\/]checks[\\/]fixtures/iu.test(item)) {
        fail(`path de pesquisa vazou em ${field}`)
      }
      return
    }
    if (Array.isArray(item)) {
      item.forEach((child, index) => visit(child, `${field}[${index}]`))
      return
    }
    if (!isRecord(item)) return
    for (const [key, child] of Object.entries(item)) {
      const childField = field ? `${field}.${key}` : key
      if (BLOCKED_PUBLIC_KEYS.has(key)) fail(`chave interna vazou em ${childField}`)
      visit(child, childField)
    }
  }
  visit(value)
}

function clone(value) {
  return structuredClone(value)
}

export function compileNarrativeDocument(inputs, { vocab = loadVocabulario() } = {}) {
  const region = assertIdentity(inputs)
  assertPublicProjection(
    inputs.firstIntegrated,
    'educacao_para_territorio',
    3,
    'integrado R5',
  )
  assertPublicProjection(
    inputs.secondIntegrated,
    'territorio_para_educacao',
    2,
    'integrado R6',
  )
  assertSecondOutputFutureRules(inputs.secondIntegrated)

  const firstProjection = JSON.stringify(inputs.firstIntegrated.publicProjection)
  const firstAllowlist = JSON.stringify(inputs.firstIntegrated.cards.map(serializePublic))
  const secondProjection = JSON.stringify(inputs.secondIntegrated.publicProjection)
  const secondAllowlist = JSON.stringify(inputs.secondIntegrated.cards.map(serializePublic))
  if (firstProjection !== firstAllowlist || secondProjection !== secondAllowlist) {
    fail('publicProjection diverge byte a byte da allowlist dos cartões integrados')
  }

  const approvedIds = new Set([
    ...inputs.firstIntegrated.publicProjection.map(({ id }) => id),
    ...inputs.secondIntegrated.publicProjection.map(({ id }) => id),
  ])
  if (approvedIds.size !== 5) fail('ids publicados devem ser cinco e únicos')
  assertAuthorship(inputs.authorship, approvedIds)

  const cardContexts = new Map()
  const buildCards = (integrated, research, sectionIndex) => (
    integrated.cards.map((card, cardIndex) => {
      const candidate = findCandidate(research, card.id)
      const authorVisual = inputs.authorship.visuals[card.id]
      const visual = card.id === 'vds-deslocamento-oferta'
        ? buildCategoryVisual(card, candidate, authorVisual)
        : buildAlignedVisual(card, candidate, authorVisual)
      const municipal = buildMunicipalDistribution(card, candidate, region)
      const publicCard = clone(
        integrated.publicProjection.find(({ id }) => id === card.id),
      )
      if (card.direction === 'territorio_para_educacao') {
        publicCard.future_label = FUTURE_LABELS[card.internal.transformation_class]
      }
      publicCard.primary_visual = visual.publicVisual
      publicCard.municipal_distribution = municipal.publicDistribution
      cardContexts.set(`${sectionIndex}:${cardIndex}`, {
        card,
        candidate,
        visualTrace: visual.trace,
        municipalTrace: municipal.trace,
      })
      return publicCard
    })
  )

  const firstCards = buildCards(inputs.firstIntegrated, inputs.firstResearch, 0)
  const secondCards = buildCards(inputs.secondIntegrated, inputs.secondResearch, 1)
  const firstSection = inputs.authorship.sections.educacao_para_territorio
  const secondSection = inputs.authorship.sections.territorio_para_educacao
  const title = inputs.authorship.page.titleTemplate.replace('{regionName}', region.name)
  if (title.includes('{regionName}')) fail('titleTemplate não foi resolvido uma única vez')

  const document = {
    schemaVersion: VOCACOES_PNE_NARRATIVE_SCHEMA,
    contractVersion: VOCACOES_PNE_NARRATIVE_CONTRACT_VERSION,
    region: {
      slug: region.slug,
      name: region.name,
      stateCode: region.stateCode,
      municipalityCount: region.municipalityCount,
    },
    page: {
      eyebrow: inputs.authorship.page.eyebrow,
      title,
      framing: inputs.authorship.page.framing,
      referenceLabel: inputs.authorship.page.referenceLabel,
      details: clone(inputs.authorship.details),
    },
    highlights: clone(inputs.authorship.highlights),
    sections: [
      {
        id: firstSection.id,
        title: firstSection.title,
        question: firstSection.question,
        cards: firstCards,
      },
      {
        id: secondSection.id,
        title: secondSection.title,
        question: secondSection.question,
        cards: secondCards,
      },
    ],
    consultation: clone(inputs.authorship.consultation),
    generation: {
      deterministic: true,
      clockUsed: false,
      modelUsed: false,
      networkUsed: false,
      databaseUsed: false,
      compilerVersion: COMPILER_VERSION,
    },
  }

  parseVocacoesPneNarrative(document)
  const retainedIds = new Set([
    ...(inputs.firstIntegrated.retainedCandidates ?? []).map(({ candidateId }) => candidateId),
    ...(inputs.secondIntegrated.retainedCandidates ?? []).map(({ candidateId }) => candidateId),
  ])
  assertNoBlockedPublicContent(document, retainedIds)
  const lintViolations = lintPublicDocument(document, vocab)
  if (lintViolations.length > 0) {
    const first = lintViolations[0]
    fail(`linter reprovou ${first.field}: ${first.ruleId}`)
  }

  const sources = sourceIndex(inputs.firstResearch, inputs.secondResearch)
  const textTrace = buildTextTrace(document, cardContexts, sources)
  const publicStringCount = collectStringLeaves(document).length
  if (textTrace.length !== publicStringCount) fail('registro textual incompleto')

  return { document, cardContexts, textTrace }
}

function inputReference(role, filePath, bytes) {
  return {
    role,
    path: path.relative(ROOT, filePath).replaceAll('\\', '/'),
    sha256: sha256(bytes),
    byteSize: bytes.length,
  }
}

function buildTraceRecord(inputs, compiled, references, publicBytes) {
  const sourceCatalog = sourceIndex(inputs.firstResearch, inputs.secondResearch)
  const cards = [...compiled.cardContexts.values()].map((context) => {
    const facts = factIndex(context.candidate)
    const factReferences = Object.entries(context.card.internal.fact_references).map(
      ([publicField, factIds]) => ({
        publicField,
        factIds: [...factIds],
        sourceIds: sourceIdsForFacts(factIds, facts),
      }),
    )
    const visualFactIds = context.visualTrace.factIds
    const municipalFactIds = [context.municipalTrace.factId]
    return {
      id: context.card.id,
      direction: context.card.direction,
      factReferences,
      primaryVisual: {
        visualizationIds: context.visualTrace.visualizationIds,
        factIds: visualFactIds,
        sourceIds: sourceIdsForFacts(visualFactIds, facts),
      },
      municipalDistribution: {
        factId: context.municipalTrace.factId,
        sourceIds: sourceIdsForFacts(municipalFactIds, facts),
        municipalities: context.municipalTrace.municipalities,
      },
    }
  })
  for (const card of cards) {
    for (const reference of card.factReferences) {
      for (const sourceId of reference.sourceIds) {
        if (!sourceCatalog.has(sourceId)) fail(`sourceId sem catálogo: ${sourceId}`)
      }
    }
  }
  return {
    schemaVersion: TRACE_SCHEMA,
    contractVersion: VOCACOES_PNE_NARRATIVE_CONTRACT_VERSION,
    region: {
      slug: inputs.firstResearch.region.slug,
      stateCode: inputs.firstResearch.region.stateCode,
      municipalities: inputs.firstResearch.region.municipalities.map(({ ibge7, name }) => ({
        ibgeCode: ibge7,
        name,
      })),
    },
    publicDocument: {
      path: path.relative(ROOT, COMPILER_PATHS.publicOutput).replaceAll('\\', '/'),
      sha256: sha256(publicBytes),
      byteSize: publicBytes.length,
    },
    inputs: references,
    cards,
    textTrace: compiled.textTrace,
    generation: {
      deterministic: true,
      clockUsed: false,
      modelUsed: false,
      networkUsed: false,
      databaseUsed: false,
      compilerVersion: COMPILER_VERSION,
    },
  }
}

export function buildCompilerArtifacts() {
  const bytes = {
    firstResearch: readFileSync(COMPILER_PATHS.firstResearch),
    firstIntegrated: readFileSync(COMPILER_PATHS.firstIntegrated),
    secondResearch: readFileSync(COMPILER_PATHS.secondResearch),
    secondIntegrated: readFileSync(COMPILER_PATHS.secondIntegrated),
    authorship: readFileSync(COMPILER_PATHS.authorship),
  }
  for (const label of Object.keys(FROZEN_INPUTS)) validateFrozenInputBytes(label, bytes[label])

  const firstExpected = buildFirstExpectedOutput()
  const secondExpected = buildSecondExpectedOutput()
  assertIntegratedRecomposition('integrado R5', bytes.firstIntegrated, firstExpected)
  assertIntegratedRecomposition('integrado R6', bytes.secondIntegrated, secondExpected)

  const inputs = Object.fromEntries(
    Object.entries(bytes).map(([label, content]) => {
      try {
        return [label, JSON.parse(content.toString('utf8'))]
      } catch (error) {
        throw new VocacoesPneCompilerError(`${label}: JSON inválido`, { cause: error })
      }
    }),
  )
  const compiled = compileNarrativeDocument(inputs)
  const publicBytes = Buffer.from(canonicalJson(compiled.document), 'utf8')
  const references = [
    inputReference('primeira_saida_pesquisa', COMPILER_PATHS.firstResearch, bytes.firstResearch),
    inputReference('primeira_saida_integrada', COMPILER_PATHS.firstIntegrated, bytes.firstIntegrated),
    inputReference('segunda_saida_pesquisa', COMPILER_PATHS.secondResearch, bytes.secondResearch),
    inputReference('segunda_saida_integrada', COMPILER_PATHS.secondIntegrated, bytes.secondIntegrated),
    inputReference('autoria_publica', COMPILER_PATHS.authorship, bytes.authorship),
  ]
  const trace = buildTraceRecord(inputs, compiled, references, publicBytes)
  const traceBytes = Buffer.from(canonicalJson(trace), 'utf8')
  return {
    document: compiled.document,
    trace,
    publicBytes,
    traceBytes,
    paths: {
      publicOutput: COMPILER_PATHS.publicOutput,
      traceOutput: COMPILER_PATHS.traceOutput,
    },
  }
}
