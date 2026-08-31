import { readFileSync } from 'node:fs'
import path from 'node:path'

const DIRECTIONS = {
  educacao_para_territorio: {
    publicFields: [
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
    ],
    arrayFields: new Set([
      'education_facts',
      'territorial_facts',
      'pne_topics',
      'monitoring_indicators',
      'sources',
    ]),
    internalFields: [
      'mechanism_id',
      'universe_check',
      'temporal_check',
      'sensitivity_check',
      'territorial_check',
      'publication_decision',
    ],
    domains: {
      universe_check: new Set(['ok', 'incompativel']),
      temporal_check: new Set(['ok', 'incoerente']),
      sensitivity_check: new Set(['ok', 'instavel']),
      territorial_check: new Set(['ok', 'concentrado']),
      publication_decision: new Set(['publicada', 'retida']),
    },
    consistencyChecks: [
      'universe_check',
      'temporal_check',
      'sensitivity_check',
      'territorial_check',
    ],
  },
  territorio_para_educacao: {
    publicFields: [
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
    ],
    arrayFields: new Set([
      'territorial_facts',
      'pne_topics',
      'monitoring_indicators',
      'sources',
    ]),
    internalFields: [
      'transformation_class',
      'mechanism_id',
      'future_basis',
      'sensitivity_check',
      'publication_decision',
    ],
    domains: {
      transformation_class: new Set([
        'mudanca_observada',
        'tendencia_sustentada',
        'estudo_setorial',
        'cenario',
      ]),
      sensitivity_check: new Set(['ok', 'instavel']),
      publication_decision: new Set(['publicada', 'retida']),
    },
    consistencyChecks: ['sensitivity_check'],
  },
}

const INTERNAL_KEYS = new Set([
  'internal',
  'mechanism_id',
  'universe_check',
  'temporal_check',
  'sensitivity_check',
  'territorial_check',
  'publication_decision',
  'transformation_class',
  'future_basis',
])

const DEFAULT_VOCABULARY_PATH = new URL(
  '../checks/fixtures/vocacoes-pne/vocabulario.json',
  import.meta.url,
)

function isRecord(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
}

function isNonEmptyString(value) {
  return typeof value === 'string' && value.trim().length > 0
}

function isFutureBasis(value, transformationClass) {
  if (!isRecord(value)) return false
  const basisTypes = new Set([
    'observed_series',
    'observed_snapshot',
    'sector_study',
    'scenario',
  ])
  const observedPeriod = value.observedPeriod
  const baseShapeIsValid = (
    basisTypes.has(value.basisType)
    && Array.isArray(value.seriesIds)
    && value.seriesIds.length > 0
    && value.seriesIds.every(isNonEmptyString)
    && isRecord(observedPeriod)
    && Number.isInteger(observedPeriod.start)
    && Number.isInteger(observedPeriod.end)
    && observedPeriod.start <= observedPeriod.end
    && typeof value.supportsTrend === 'boolean'
    && (value.scenarioId === null || isNonEmptyString(value.scenarioId))
    && Array.isArray(value.futureNumericValues)
    && value.futureNumericValues.every(Number.isFinite)
    && isNonEmptyString(value.claimBoundary)
  )
  if (!baseShapeIsValid) return false
  if (
    value.basisType !== 'scenario'
    && (value.scenarioId !== null || value.futureNumericValues.length > 0)
  ) {
    return false
  }
  if (value.basisType === 'observed_snapshot' && value.supportsTrend !== false) {
    return false
  }
  if (value.basisType === 'scenario' && !isNonEmptyString(value.scenarioId)) {
    return false
  }
  const expectedBasisType = {
    mudanca_observada: 'observed_snapshot',
    tendencia_sustentada: 'observed_series',
    estudo_setorial: 'sector_study',
    cenario: 'scenario',
  }[transformationClass]
  if (expectedBasisType !== value.basisType) return false
  if (
    ['tendencia_sustentada', 'estudo_setorial'].includes(transformationClass)
    && value.supportsTrend !== true
  ) {
    return false
  }
  return true
}

function assertVocabularyShape(vocab, filePath) {
  const fail = (message) => {
    throw new Error(`Vocabulário inválido em ${filePath}: ${message}`)
  }

  if (!isRecord(vocab)) fail('a raiz deve ser um objeto')
  if (!isNonEmptyString(vocab.version)) fail('version deve ser uma string não vazia')
  if (!isNonEmptyString(vocab.descricao)) fail('descricao deve ser uma string não vazia')
  if (!Array.isArray(vocab.regras) || vocab.regras.length === 0) {
    fail('regras deve ser um array não vazio')
  }
  if (!isRecord(vocab.rotulosPublicosPermitidos)) {
    fail('rotulosPublicosPermitidos deve ser um objeto')
  }
  if (!Array.isArray(vocab.traducoes)) fail('traducoes deve ser um array')
  if (!Array.isArray(vocab.guardasFalsoPositivo)) {
    fail('guardasFalsoPositivo deve ser um array')
  }
  if (!isRecord(vocab.limites)) fail('limites deve ser um objeto')

  const ids = new Set()
  for (const [index, rule] of vocab.regras.entries()) {
    if (!isRecord(rule)) fail(`regras[${index}] deve ser um objeto`)
    for (const field of ['id', 'classe', 'pattern', 'exemploBloqueado']) {
      if (!isNonEmptyString(rule[field])) {
        fail(`regras[${index}].${field} deve ser uma string não vazia`)
      }
    }
    if (ids.has(rule.id)) fail(`id de regra duplicado: ${rule.id}`)
    ids.add(rule.id)
  }

  for (const [index, translation] of vocab.traducoes.entries()) {
    if (
      !isRecord(translation)
      || !isNonEmptyString(translation.interno)
      || !isNonEmptyString(translation.publico)
    ) {
      fail(`traducoes[${index}] deve conter interno e publico não vazios`)
    }
  }

  for (const [index, guard] of vocab.guardasFalsoPositivo.entries()) {
    if (!isNonEmptyString(guard)) {
      fail(`guardasFalsoPositivo[${index}] deve ser uma string não vazia`)
    }
  }

  for (const direction of Object.keys(DIRECTIONS)) {
    const limits = vocab.limites[direction]
    if (!isRecord(limits)) fail(`limites.${direction} deve ser um objeto`)
    if (!Number.isInteger(limits.min) || limits.min < 0) {
      fail(`limites.${direction}.min deve ser um inteiro não negativo`)
    }
    if (!Number.isInteger(limits.max) || limits.max < limits.min) {
      fail(`limites.${direction}.max deve ser um inteiro maior ou igual a min`)
    }
  }
}

function compileRules(vocab, filePath) {
  return vocab.regras.map((rule) => {
    try {
      return { ...rule, regex: new RegExp(rule.pattern, 'iu') }
    } catch (error) {
      throw new Error(
        `Vocabulário inválido em ${filePath}: pattern inválido na regra ${rule.id}`,
        { cause: error },
      )
    }
  })
}

function excerptAround(text, index, matchLength) {
  const maximumLength = 80
  if (text.length <= maximumLength) return text

  const center = index + Math.floor(matchLength / 2)
  let start = Math.max(0, center - Math.floor(maximumLength / 2))
  let end = start + maximumLength
  if (end > text.length) {
    end = text.length
    start = Math.max(0, end - maximumLength)
  }
  return text.slice(start, end)
}

function fieldIsPresent(card, field, arrayFields) {
  const value = card[field]
  return arrayFields.has(field)
    ? Array.isArray(value) && value.length > 0
    : isNonEmptyString(value)
}

function cloneValue(value) {
  if (Array.isArray(value)) return value.map(cloneValue)
  if (!isRecord(value)) return value
  return Object.fromEntries(
    Object.entries(value).map(([key, child]) => [key, cloneValue(child)]),
  )
}

function assertNoInternalKeys(value, field = '') {
  if (Array.isArray(value)) {
    value.forEach((item, index) => assertNoInternalKeys(item, `${field}[${index}]`))
    return
  }
  if (!isRecord(value)) return

  for (const [key, child] of Object.entries(value)) {
    const childField = field ? `${field}.${key}` : key
    if (INTERNAL_KEYS.has(key)) {
      throw new Error(`serializePublic encontrou chave interna em ${childField}`)
    }
    assertNoInternalKeys(child, childField)
  }
}

export function loadVocabulario(filePath = DEFAULT_VOCABULARY_PATH) {
  const source = filePath instanceof URL ? filePath : path.resolve(filePath)
  const sourceLabel = source instanceof URL ? source.href : source
  const vocab = JSON.parse(readFileSync(source, 'utf8'))
  assertVocabularyShape(vocab, sourceLabel)
  return { ...vocab, regras: compileRules(vocab, sourceLabel) }
}

export function lintText(text, vocab) {
  if (typeof text !== 'string') return []

  const violations = []
  for (const rule of vocab.regras) {
    const regex = rule.regex instanceof RegExp
      ? rule.regex
      : new RegExp(rule.pattern, 'iu')
    regex.lastIndex = 0
    const match = regex.exec(text)
    if (match) {
      violations.push({
        ruleId: rule.id,
        excerpt: excerptAround(text, match.index, match[0].length),
      })
    }
  }
  return violations
}

export function lintCard(card, vocab) {
  const violations = []

  const visit = (value, field) => {
    if (typeof value === 'string') {
      violations.push(
        ...lintText(value, vocab).map((violation) => ({ ...violation, field })),
      )
      return
    }
    if (Array.isArray(value)) {
      value.forEach((item, index) => visit(item, `${field}[${index}]`))
      return
    }
    if (!isRecord(value)) return

    for (const [key, child] of Object.entries(value)) {
      if (key === 'internal') continue
      visit(child, field ? `${field}.${key}` : key)
    }
  }

  visit(card, '')
  return violations
}

/**
 * Aplica o vocabulário a qualquer projeção pública. Diferentemente de
 * `lintCard`, não conhece nem ignora a chave `internal`: o compilador chama
 * esta função somente depois de construir o documento público por allowlist.
 */
export function lintPublicDocument(document, vocab) {
  const violations = []

  const visit = (value, field) => {
    if (typeof value === 'string') {
      violations.push(
        ...lintText(value, vocab).map((violation) => ({ ...violation, field })),
      )
      return
    }
    if (Array.isArray(value)) {
      value.forEach((item, index) => visit(item, `${field}[${index}]`))
      return
    }
    if (!isRecord(value)) return

    for (const [key, child] of Object.entries(value)) {
      visit(child, field ? `${field}.${key}` : key)
    }
  }

  visit(document, '')
  return violations
}

export function validateCardContract(card) {
  if (!isRecord(card) || !Object.hasOwn(DIRECTIONS, card.direction)) {
    return [{ ruleId: 'direcao-invalida', field: 'direction' }]
  }

  const contract = DIRECTIONS[card.direction]
  const violations = []
  for (const field of contract.publicFields) {
    if (!fieldIsPresent(card, field, contract.arrayFields)) {
      violations.push({ ruleId: `campo-obrigatorio:${field}`, field })
    }
  }

  const internal = isRecord(card.internal) ? card.internal : {}
  for (const field of contract.internalFields) {
    const fieldIsValid = (
      field === 'future_basis'
        ? isFutureBasis(internal[field], internal.transformation_class)
        : isNonEmptyString(internal[field])
    )
    if (!fieldIsValid) {
      const qualifiedField = `internal.${field}`
      violations.push({
        ruleId: `campo-obrigatorio:${qualifiedField}`,
        field: qualifiedField,
      })
    }
  }

  for (const [field, allowedValues] of Object.entries(contract.domains)) {
    if (isNonEmptyString(internal[field]) && !allowedValues.has(internal[field])) {
      const qualifiedField = `internal.${field}`
      violations.push({
        ruleId: `valor-invalido:${qualifiedField}`,
        field: qualifiedField,
      })
    }
  }

  if (internal.publication_decision === 'publicada') {
    const failedCheck = contract.consistencyChecks.some(
      (field) => internal[field] !== 'ok',
    )
    const missingFutureBasis = (
      card.direction === 'territorio_para_educacao'
      && !isFutureBasis(internal.future_basis, internal.transformation_class)
    )
    if (failedCheck || missingFutureBasis) {
      violations.push({
        ruleId: 'decisao-incoerente',
        field: 'internal.publication_decision',
      })
    }
  }

  return violations
}

export function serializePublic(card) {
  if (!isRecord(card) || !Object.hasOwn(DIRECTIONS, card.direction)) {
    throw new Error('serializePublic requer uma direction válida')
  }

  const result = {}
  for (const field of DIRECTIONS[card.direction].publicFields) {
    if (Object.hasOwn(card, field)) result[field] = cloneValue(card[field])
  }
  assertNoInternalKeys(result)
  return result
}

export function validateCardSet(cards, vocab) {
  if (!Array.isArray(cards)) throw new TypeError('cards deve ser um array')

  const violations = []
  const seenIds = new Set()
  const porDirecao = Object.fromEntries(
    Object.keys(vocab.limites).map((direction) => [direction, 0]),
  )

  for (const card of cards) {
    violations.push(...validateCardContract(card), ...lintCard(card, vocab))

    if (isRecord(card) && isNonEmptyString(card.id)) {
      if (seenIds.has(card.id)) {
        violations.push({ ruleId: 'id-duplicado', field: 'id' })
      } else {
        seenIds.add(card.id)
      }
    }

    if (
      isRecord(card)
      && card.internal?.publication_decision === 'publicada'
      && Object.hasOwn(porDirecao, card.direction)
    ) {
      porDirecao[card.direction] += 1
    }
  }

  const publishable = Object.entries(vocab.limites).every(
    ([direction, limits]) => (
      porDirecao[direction] >= limits.min
      && porDirecao[direction] <= limits.max
    ),
  )

  return { violations, publishable, counts: { porDirecao } }
}
