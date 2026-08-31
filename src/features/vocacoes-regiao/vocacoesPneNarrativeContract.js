export const VOCACOES_PNE_NARRATIVE_SCHEMA = 'vocacoes-pne-narrative-pilot-v1'
export const VOCACOES_PNE_NARRATIVE_CONTRACT_VERSION = '1.5.0'

const DIRECTIONS = [
  'educacao_para_territorio',
  'territorio_para_educacao',
]

const CARD_FIELDS = {
  educacao_para_territorio: [
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
    'primary_visual',
    'municipal_distribution',
  ],
  territorio_para_educacao: [
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
    'future_label',
    'primary_visual',
    'municipal_distribution',
  ],
}

const ARRAY_FIELDS = {
  educacao_para_territorio: [
    'education_facts',
    'territorial_facts',
    'pne_topics',
    'monitoring_indicators',
    'sources',
  ],
  territorio_para_educacao: [
    'territorial_facts',
    'pne_topics',
    'monitoring_indicators',
    'sources',
  ],
}

function fail(path, message) {
  throw new TypeError(`${path}: ${message}`)
}

function isRecord(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
}

function record(value, path) {
  if (!isRecord(value)) fail(path, 'deve ser objeto')
  return value
}

function exactKeys(value, expected, path) {
  record(value, path)
  const actual = Object.keys(value).sort()
  const wanted = [...expected].sort()
  if (
    actual.length !== wanted.length
    || actual.some((key, index) => key !== wanted[index])
  ) {
    fail(path, `campos exatos esperados: ${expected.join(', ')}`)
  }
}

function nonEmptyString(value, path) {
  if (typeof value !== 'string' || value.trim().length === 0) {
    fail(path, 'deve ser string não vazia')
  }
  return value
}

function finiteNumber(value, path) {
  if (!Number.isFinite(value)) fail(path, 'deve ser número finito')
  return value
}

function integer(value, path) {
  if (!Number.isInteger(value)) fail(path, 'deve ser inteiro')
  return value
}

function boolean(value, path) {
  if (typeof value !== 'boolean') fail(path, 'deve ser booleano')
  return value
}

function stringList(value, path) {
  if (!Array.isArray(value) || value.length === 0) {
    fail(path, 'deve ser array não vazio')
  }
  const result = value.map((item, index) => nonEmptyString(item, `${path}[${index}]`))
  if (new Set(result).size !== result.length) fail(path, 'não aceita duplicatas')
  return result
}

function parseRegion(value, path) {
  exactKeys(value, ['slug', 'name', 'stateCode', 'municipalityCount'], path)
  nonEmptyString(value.slug, `${path}.slug`)
  nonEmptyString(value.name, `${path}.name`)
  if (nonEmptyString(value.stateCode, `${path}.stateCode`) !== 'RS') {
    fail(`${path}.stateCode`, 'documento restrito ao RS')
  }
  const municipalityCount = integer(value.municipalityCount, `${path}.municipalityCount`)
  if (municipalityCount <= 0) {
    fail(`${path}.municipalityCount`, 'deve ser positivo')
  }
  return municipalityCount
}

function parsePage(value, path) {
  exactKeys(
    value,
    ['eyebrow', 'title', 'framing', 'referenceLabel', 'details'],
    path,
  )
  for (const key of ['eyebrow', 'title', 'framing', 'referenceLabel']) {
    nonEmptyString(value[key], `${path}.${key}`)
  }
  exactKeys(
    value.details,
    ['evolution', 'municipalities', 'pne', 'sources'],
    `${path}.details`,
  )
  for (const key of ['evolution', 'municipalities', 'pne', 'sources']) {
    nonEmptyString(value.details[key], `${path}.details.${key}`)
  }
}

function parseHighlights(value, path, cardIds) {
  if (!Array.isArray(value) || value.length !== 3) {
    fail(path, 'deve conter exatamente três destaques')
  }
  const seen = new Set()
  value.forEach((highlight, index) => {
    const itemPath = `${path}[${index}]`
    exactKeys(highlight, ['cardId', 'label'], itemPath)
    const cardId = nonEmptyString(highlight.cardId, `${itemPath}.cardId`)
    nonEmptyString(highlight.label, `${itemPath}.label`)
    if (!cardIds.has(cardId)) fail(`${itemPath}.cardId`, 'não resolve para cartão')
    if (seen.has(cardId)) fail(`${itemPath}.cardId`, 'destaque duplicado')
    seen.add(cardId)
  })
}

function parseAlignedVisual(value, path) {
  exactKeys(value, ['template', 'title', 'alt_text', 'periods', 'series'], path)
  if (value.template !== 'aligned_series') fail(`${path}.template`, 'inválido')
  nonEmptyString(value.title, `${path}.title`)
  nonEmptyString(value.alt_text, `${path}.alt_text`)
  if (!Array.isArray(value.periods) || value.periods.length < 2) {
    fail(`${path}.periods`, 'deve conter ao menos dois períodos')
  }
  value.periods.forEach((period, index) => integer(period, `${path}.periods[${index}]`))
  if (!Array.isArray(value.series) || value.series.length !== 2) {
    fail(`${path}.series`, 'deve conter exatamente duas séries')
  }
  value.series.forEach((series, index) => {
    const seriesPath = `${path}.series[${index}]`
    exactKeys(series, ['label', 'unit', 'values'], seriesPath)
    nonEmptyString(series.label, `${seriesPath}.label`)
    nonEmptyString(series.unit, `${seriesPath}.unit`)
    if (!Array.isArray(series.values) || series.values.length !== value.periods.length) {
      fail(`${seriesPath}.values`, 'deve alinhar um valor por período')
    }
    series.values.forEach((point, pointIndex) => (
      finiteNumber(point, `${seriesPath}.values[${pointIndex}]`)
    ))
  })
}

function parseCategoryVisual(value, path) {
  exactKeys(
    value,
    ['template', 'title', 'alt_text', 'unit', 'series_labels', 'categories'],
    path,
  )
  if (value.template !== 'category_bars') fail(`${path}.template`, 'inválido')
  for (const key of ['title', 'alt_text', 'unit']) {
    nonEmptyString(value[key], `${path}.${key}`)
  }
  exactKeys(value.series_labels, ['region', 'state'], `${path}.series_labels`)
  nonEmptyString(value.series_labels.region, `${path}.series_labels.region`)
  nonEmptyString(value.series_labels.state, `${path}.series_labels.state`)
  if (!Array.isArray(value.categories) || value.categories.length !== 3) {
    fail(`${path}.categories`, 'deve conter exatamente três categorias')
  }
  value.categories.forEach((category, index) => {
    const categoryPath = `${path}.categories[${index}]`
    exactKeys(category, ['label', 'region_value', 'state_value'], categoryPath)
    nonEmptyString(category.label, `${categoryPath}.label`)
    finiteNumber(category.region_value, `${categoryPath}.region_value`)
    finiteNumber(category.state_value, `${categoryPath}.state_value`)
  })
}

function parsePrimaryVisual(value, path) {
  record(value, path)
  if (value.template === 'aligned_series') parseAlignedVisual(value, path)
  else if (value.template === 'category_bars') parseCategoryVisual(value, path)
  else fail(`${path}.template`, 'template desconhecido')
}

function parseMunicipalDistribution(value, path, municipalityCount) {
  exactKeys(value, ['unit', 'period', 'items'], path)
  nonEmptyString(value.unit, `${path}.unit`)
  exactKeys(value.period, ['start', 'end'], `${path}.period`)
  const start = integer(value.period.start, `${path}.period.start`)
  const end = integer(value.period.end, `${path}.period.end`)
  if (start > end) fail(`${path}.period`, 'janela invertida')
  if (!Array.isArray(value.items) || value.items.length !== municipalityCount) {
    fail(`${path}.items`, `deve conter os ${municipalityCount} municípios`)
  }
  const names = new Set()
  value.items.forEach((item, index) => {
    const itemPath = `${path}.items[${index}]`
    exactKeys(item, ['name', 'value'], itemPath)
    const name = nonEmptyString(item.name, `${itemPath}.name`)
    finiteNumber(item.value, `${itemPath}.value`)
    if (names.has(name)) fail(`${itemPath}.name`, 'município duplicado')
    names.add(name)
  })
}

function parseCard(value, path, expectedDirection, municipalityCount) {
  record(value, path)
  const direction = value.direction
  if (!DIRECTIONS.includes(direction)) fail(`${path}.direction`, 'inválida')
  if (direction !== expectedDirection) fail(`${path}.direction`, 'seção incompatível')
  exactKeys(value, CARD_FIELDS[direction], path)
  nonEmptyString(value.id, `${path}.id`)
  for (const field of CARD_FIELDS[direction]) {
    if (
      !['id', 'direction', 'primary_visual', 'municipal_distribution', ...ARRAY_FIELDS[direction]]
        .includes(field)
    ) {
      nonEmptyString(value[field], `${path}.${field}`)
    }
  }
  ARRAY_FIELDS[direction].forEach((field) => stringList(value[field], `${path}.${field}`))
  if (
    direction === 'territorio_para_educacao'
    && ![
      'Mudança já em curso',
      'Tendência para os próximos anos',
      'Tema presente nos cenários',
    ].includes(value.future_label)
  ) {
    fail(`${path}.future_label`, 'rótulo futuro fora da tabela fechada')
  }
  parsePrimaryVisual(value.primary_visual, `${path}.primary_visual`)
  parseMunicipalDistribution(
    value.municipal_distribution,
    `${path}.municipal_distribution`,
    municipalityCount,
  )
}

function parseSections(value, path, municipalityCount) {
  if (!Array.isArray(value) || value.length !== 2) {
    fail(path, 'deve conter exatamente duas seções')
  }
  const ids = new Set()
  const cardIds = new Set()
  value.forEach((section, sectionIndex) => {
    const sectionPath = `${path}[${sectionIndex}]`
    exactKeys(section, ['id', 'title', 'question', 'cards'], sectionPath)
    const id = nonEmptyString(section.id, `${sectionPath}.id`)
    nonEmptyString(section.title, `${sectionPath}.title`)
    nonEmptyString(section.question, `${sectionPath}.question`)
    if (ids.has(id)) fail(`${sectionPath}.id`, 'seção duplicada')
    ids.add(id)
    const direction = DIRECTIONS[sectionIndex]
    const minimumCount = sectionIndex === 0 ? 3 : 2
    const maximumCount = 5
    if (
      !Array.isArray(section.cards)
      || section.cards.length < minimumCount
      || section.cards.length > maximumCount
    ) {
      fail(
        `${sectionPath}.cards`,
        `deve conter entre ${minimumCount} e ${maximumCount} cartões`,
      )
    }
    section.cards.forEach((card, cardIndex) => {
      parseCard(
        card,
        `${sectionPath}.cards[${cardIndex}]`,
        direction,
        municipalityCount,
      )
      if (cardIds.has(card.id)) fail(`${sectionPath}.cards[${cardIndex}].id`, 'duplicado')
      cardIds.add(card.id)
    })
  })
  return cardIds
}

function parseConsultation(value, path) {
  exactKeys(value, ['title', 'description'], path)
  nonEmptyString(value.title, `${path}.title`)
  nonEmptyString(value.description, `${path}.description`)
}

function parseGeneration(value, path) {
  exactKeys(
    value,
    ['deterministic', 'clockUsed', 'modelUsed', 'networkUsed', 'databaseUsed', 'compilerVersion'],
    path,
  )
  if (!boolean(value.deterministic, `${path}.deterministic`)) {
    fail(`${path}.deterministic`, 'deve ser true')
  }
  for (const key of ['clockUsed', 'modelUsed', 'networkUsed', 'databaseUsed']) {
    if (boolean(value[key], `${path}.${key}`)) fail(`${path}.${key}`, 'deve ser false')
  }
  nonEmptyString(value.compilerVersion, `${path}.compilerVersion`)
}

export function parseVocacoesPneNarrative(value) {
  exactKeys(
    value,
    [
      'schemaVersion',
      'contractVersion',
      'region',
      'page',
      'highlights',
      'sections',
      'consultation',
      'generation',
    ],
    'document',
  )
  if (value.schemaVersion !== VOCACOES_PNE_NARRATIVE_SCHEMA) {
    fail('document.schemaVersion', 'schema incompatível')
  }
  if (value.contractVersion !== VOCACOES_PNE_NARRATIVE_CONTRACT_VERSION) {
    fail('document.contractVersion', 'versão de contrato incompatível')
  }
  const municipalityCount = parseRegion(value.region, 'document.region')
  parsePage(value.page, 'document.page')
  const cardIds = parseSections(value.sections, 'document.sections', municipalityCount)
  parseHighlights(value.highlights, 'document.highlights', cardIds)
  parseConsultation(value.consultation, 'document.consultation')
  parseGeneration(value.generation, 'document.generation')
  return value
}

export function isVocacoesPneNarrative(value) {
  try {
    parseVocacoesPneNarrative(value)
    return true
  } catch {
    return false
  }
}

export const isVocacoesPneNarrativePilot = isVocacoesPneNarrative
