/*
 * Leitura do caderno de hipóteses publicado em `public/data/pne2026-caderno/`.
 *
 * O fluxo segue a mesma disciplina do diagnóstico V3: o manifesto é a única
 * porta de entrada, o documento municipal só é aceito quando bate com a
 * entrada declarada no manifesto e o carregamento falha fechado com erro
 * estruturado. O caderno é um artefato de leitura: nada aqui recalcula,
 * reordena ou resume o conteúdo publicado.
 */

export const PNE_2026_CADERNO_MANIFEST_PATH = '/data/pne2026-caderno/manifest.json'
export const PNE_2026_CADERNO_MUNICIPAL_PATH = '/data/pne2026-caderno/municipios/{municipalityId}.json'

export const PNE_2026_CADERNO_SCHEMA = 'pne2026-caderno-v2'
export const PNE_2026_CADERNO_MANIFEST_SCHEMA = 'pne2026-caderno-manifest-v2'
export const PNE_2026_WORKBOOK_SCHEMA = 'pne-priority-hypothesis-workbook-v2'
export const PNE_2026_CADERNO_MUNICIPAL_FILE_PATTERN = 'municipios/{municipalityId}.json'

export const CADERNO_HYPOTHESIS_SECTIONS = Object.freeze([
  'adverse_signal',
  'no_public_data',
  'protective_present',
])

const MANIFEST_FIELDS = new Set([
  'schemaVersion',
  'cadernoSchemaVersion',
  'workbookSchemaVersion',
  'generatorVersion',
  'contractVersion',
  'municipalFilePattern',
  'municipalities',
])
const MANIFEST_ENTRY_FIELDS = new Set([
  'ibge7',
  'name',
  'uf',
  'referenceDate',
  'path',
  'inputSha256',
  'outputSha256',
  'outputByteSize',
])
const DOCUMENT_FIELDS = new Set([
  'schemaVersion',
  'workbookSchemaVersion',
  'contractVersion',
  'municipality',
  'referenceDate',
  'disclaimer',
  'curation',
  'sourceDiagnostic',
  'goals',
])
const CURATION_FIELDS = new Set(['sha256', 'version'])
const MUNICIPALITY_FIELDS = new Set(['ibge7', 'name', 'uf'])
const SOURCE_DIAGNOSTIC_FIELDS = new Set(['builderVersion', 'catalogSha256', 'diagnosticCsvSha256'])
const GOAL_FIELDS = new Set([
  'goalId',
  'legalGoals',
  'indicators',
  'hypotheses',
  'readingCautions',
  'monitoring_context',
])
const LEGAL_GOAL_FIELDS = new Set(['legalGoalId', 'title'])
const INDICATOR_FIELDS = new Set([
  'availability',
  'caveat',
  'collectionTrigger',
  'gapRaw',
  'indicatorId',
  'indicatorTitle',
  'legalGoalTitle',
  'relationId',
  'targetReference',
  'trend',
  'unit',
  'valueRaw',
  'year',
])
const HYPOTHESIS_FIELDS = new Set([
  'classDate',
  'diagnosticRole',
  'evidence',
  'expectedRelationship',
  'factorId',
  'governability',
  'howToConfirmLocally',
  'mechanism',
  'name',
  'relations',
  'signals',
])
const SIGNAL_FIELDS = new Set([
  'caution',
  'dimensions',
  'direction',
  'maxInference',
  'measureId',
  'observability',
  'period',
  'stance',
  'unit',
  'valueRaw',
])
const EVIDENCE_FIELDS = new Set(['designLevel', 'finding', 'id', 'levelForRelationship'])
const RELATION_FIELDS = new Set([
  'classificationRationale',
  'deliberationClass',
  'indicatorId',
  'relationId',
])
const READING_CAUTION_FIELDS = new Set(['factorId', 'name', 'note'])
const MONITORING_CONTEXT_FIELDS = new Set(['factorId', 'name', 'relations', 'signals'])
const MONITORING_SIGNAL_FIELDS = new Set([
  'dimensions',
  'direction',
  'measureId',
  'period',
  'unit',
  'valueRaw',
])

const SHA256_PATTERN = /^[a-f0-9]{64}$/
const IBGE7_PATTERN = /^\d{7}$/
const ISO_DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/

function invariant(condition, message) {
  if (!condition) throw new TypeError(`Caderno de hipóteses inválido: ${message}`)
}

function isObject(value) {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value)
}

function validateExactFields(candidate, expected, label) {
  invariant(isObject(candidate), `${label} deve ser objeto.`)
  const unknown = Object.keys(candidate).filter((field) => !expected.has(field))
  const missing = [...expected].filter((field) => !Object.hasOwn(candidate, field))
  invariant(!unknown.length, `${label} contém campos desconhecidos: ${unknown.join(', ')}.`)
  invariant(!missing.length, `${label} não contém: ${missing.join(', ')}.`)
}

function validateTextFields(candidate, expected, label) {
  for (const field of expected) {
    invariant(typeof candidate[field] === 'string', `${label}.${field} deve ser texto.`)
  }
}

function validateTextList(candidate, label) {
  invariant(Array.isArray(candidate), `${label} deve ser lista.`)
  candidate.forEach((item, index) => {
    invariant(typeof item === 'string', `${label}[${index}] deve ser texto.`)
  })
}

function validateItems(items, fields, label) {
  invariant(Array.isArray(items), `${label} deve ser lista.`)
  for (const item of items) {
    validateExactFields(item, fields, `${label}[]`)
    validateTextFields(item, fields, `${label}[]`)
  }
}

export function parsePne2026CadernoManifest(candidate) {
  validateExactFields(candidate, MANIFEST_FIELDS, 'manifest.json')
  invariant(candidate.schemaVersion === PNE_2026_CADERNO_MANIFEST_SCHEMA, 'schema do manifesto divergente.')
  invariant(candidate.cadernoSchemaVersion === PNE_2026_CADERNO_SCHEMA, 'cadernoSchemaVersion divergente.')
  invariant(candidate.workbookSchemaVersion === PNE_2026_WORKBOOK_SCHEMA, 'workbookSchemaVersion divergente.')
  invariant(
    candidate.municipalFilePattern === PNE_2026_CADERNO_MUNICIPAL_FILE_PATTERN,
    'municipalFilePattern divergente.',
  )
  validateTextFields(candidate, ['generatorVersion', 'contractVersion'], 'manifest.json')
  invariant(Array.isArray(candidate.municipalities), 'manifest.json.municipalities deve ser lista.')

  const seen = new Set()
  for (const entry of candidate.municipalities) {
    validateExactFields(entry, MANIFEST_ENTRY_FIELDS, 'manifest.json.municipalities[]')
    validateTextFields(
      entry,
      ['ibge7', 'name', 'uf', 'referenceDate', 'path', 'inputSha256', 'outputSha256'],
      'manifest.json.municipalities[]',
    )
    invariant(IBGE7_PATTERN.test(entry.ibge7), `código municipal inválido no manifesto: ${entry.ibge7}.`)
    invariant(!seen.has(entry.ibge7), `município duplicado no manifesto: ${entry.ibge7}.`)
    seen.add(entry.ibge7)
    invariant(ISO_DATE_PATTERN.test(entry.referenceDate), `referenceDate inválida em ${entry.ibge7}.`)
    for (const field of ['inputSha256', 'outputSha256']) {
      invariant(SHA256_PATTERN.test(entry[field]), `${field} inválido em ${entry.ibge7}.`)
    }
    invariant(
      entry.path === PNE_2026_CADERNO_MUNICIPAL_FILE_PATTERN.replace('{municipalityId}', entry.ibge7),
      `caminho publicado fora do padrão em ${entry.ibge7}.`,
    )
    invariant(
      Number.isInteger(entry.outputByteSize) && entry.outputByteSize > 0,
      `outputByteSize inválido em ${entry.ibge7}.`,
    )
  }
  return structuredClone(candidate)
}

export function parsePne2026Caderno(candidate) {
  validateExactFields(candidate, DOCUMENT_FIELDS, 'caderno municipal')
  invariant(candidate.schemaVersion === PNE_2026_CADERNO_SCHEMA, 'schema do caderno divergente.')
  invariant(candidate.workbookSchemaVersion === PNE_2026_WORKBOOK_SCHEMA, 'workbookSchemaVersion divergente.')
  validateTextFields(candidate, ['contractVersion', 'referenceDate', 'disclaimer'], 'caderno municipal')
  invariant(candidate.disclaimer.trim().length > 0, 'o aviso do caderno não pode ser vazio.')
  invariant(ISO_DATE_PATTERN.test(candidate.referenceDate), 'referenceDate inválida.')

  validateExactFields(candidate.curation, CURATION_FIELDS, 'curation')
  validateTextFields(candidate.curation, CURATION_FIELDS, 'curation')
  invariant(SHA256_PATTERN.test(candidate.curation.sha256), 'curation.sha256 inválido.')

  validateExactFields(candidate.municipality, MUNICIPALITY_FIELDS, 'municipality')
  validateTextFields(candidate.municipality, MUNICIPALITY_FIELDS, 'municipality')
  invariant(IBGE7_PATTERN.test(candidate.municipality.ibge7), 'municipality.ibge7 inválido.')

  validateExactFields(candidate.sourceDiagnostic, SOURCE_DIAGNOSTIC_FIELDS, 'sourceDiagnostic')
  validateTextFields(candidate.sourceDiagnostic, SOURCE_DIAGNOSTIC_FIELDS, 'sourceDiagnostic')

  invariant(Array.isArray(candidate.goals) && candidate.goals.length > 0, 'goals deve ser lista não vazia.')
  const seenGoals = new Set()
  for (const goal of candidate.goals) {
    validateExactFields(goal, GOAL_FIELDS, 'goals[]')
    invariant(typeof goal.goalId === 'string' && /^\d+$/.test(goal.goalId), 'goals[].goalId inválido.')
    invariant(!seenGoals.has(goal.goalId), `meta duplicada: ${goal.goalId}.`)
    seenGoals.add(goal.goalId)
    const label = `meta ${goal.goalId}`

    validateItems(goal.legalGoals, LEGAL_GOAL_FIELDS, `${label}.legalGoals`)
    invariant(goal.legalGoals.length > 0, `${label}: nenhuma meta legal identificada.`)
    validateItems(goal.indicators, INDICATOR_FIELDS, `${label}.indicators`)
    invariant(goal.indicators.length > 0, `${label}: nenhum indicador publicado.`)

    validateExactFields(goal.hypotheses, new Set(CADERNO_HYPOTHESIS_SECTIONS), `${label}.hypotheses`)
    for (const section of CADERNO_HYPOTHESIS_SECTIONS) {
      const hypotheses = goal.hypotheses[section]
      invariant(Array.isArray(hypotheses), `${label}.hypotheses.${section} deve ser lista.`)
      for (const hypothesis of hypotheses) {
        const hypothesisLabel = `${label}.${section}[${hypothesis?.factorId ?? '?'}]`
        validateExactFields(hypothesis, HYPOTHESIS_FIELDS, hypothesisLabel)
        validateTextFields(
          hypothesis,
          [
            'classDate',
            'diagnosticRole',
            'expectedRelationship',
            'factorId',
            'governability',
            'mechanism',
            'name',
          ],
          hypothesisLabel,
        )
        invariant(
          hypothesis.classDate === candidate.referenceDate,
          `${hypothesisLabel}: classDate divergente da data de referência.`,
        )
        validateTextList(hypothesis.howToConfirmLocally, `${hypothesisLabel}.howToConfirmLocally`)
        validateItems(hypothesis.signals, SIGNAL_FIELDS, `${hypothesisLabel}.signals`)
        validateItems(hypothesis.evidence, EVIDENCE_FIELDS, `${hypothesisLabel}.evidence`)
        validateItems(hypothesis.relations, RELATION_FIELDS, `${hypothesisLabel}.relations`)
        invariant(hypothesis.relations.length > 0, `${hypothesisLabel}: nenhuma relação declarada.`)
      }
    }

    validateItems(goal.readingCautions, READING_CAUTION_FIELDS, `${label}.readingCautions`)
    invariant(Array.isArray(goal.monitoring_context), `${label}.monitoring_context deve ser lista.`)
    for (const context of goal.monitoring_context) {
      validateExactFields(context, MONITORING_CONTEXT_FIELDS, `${label}.monitoring_context[]`)
      validateTextFields(context, ['factorId', 'name'], `${label}.monitoring_context[]`)
      validateItems(context.relations, RELATION_FIELDS, `${label}.monitoring_context[].relations`)
      invariant(
        context.relations.length > 0,
        `${label}.monitoring_context[]: nenhuma relação declarada.`,
      )
      for (const relation of context.relations) {
        invariant(
          goal.indicators.some(
            (indicator) => indicator.relationId === relation.relationId
              && indicator.indicatorId === relation.indicatorId,
          ),
          `${label}.monitoring_context[]: relação ${relation.relationId}×${relation.indicatorId} não pertence à meta.`,
        )
      }
      validateItems(context.signals, MONITORING_SIGNAL_FIELDS, `${label}.monitoring_context[].signals`)
    }
  }

  return candidate
}

async function defaultFetchJson(path, options) {
  const response = await fetch(path, options)
  if (!response.ok) {
    throw new Error(`Erro ao carregar ${path} (${response.status})`)
  }
  return response.json()
}

export class CadernoLoadError extends Error {
  constructor(message, { cause, code, municipalityId = null, path = null, stage }) {
    super(message, { cause })
    this.name = 'CadernoLoadError'
    this.code = code
    this.stage = stage
    this.municipalityId = municipalityId
    this.path = path
  }
}

function structuredError(error, details) {
  if (error instanceof CadernoLoadError) return error
  return new CadernoLoadError(
    error instanceof Error ? error.message : String(error),
    { ...details, cause: error },
  )
}

function memoized(cache, key, producer) {
  if (cache.has(key)) return cache.get(key)
  const pending = Promise.resolve().then(producer)
  cache.set(key, pending)
  pending.catch(() => {
    if (cache.get(key) === pending) cache.delete(key)
  })
  return pending
}

/**
 * @param {{
 *   fetchJson?: (path: any, options: any) => Promise<any>,
 *   logger?: (...data: any[]) => void,
 * }} [options]
 */
export function createPne2026CadernoLoader({
  fetchJson = defaultFetchJson,
  logger = console.error,
} = {}) {
  const documentCache = new Map()
  const reportedErrors = new Set()
  let manifestPending = null

  function reportOnce(error) {
    const key = [error.code, error.stage, error.municipalityId, error.path, error.message].join(':')
    if (reportedErrors.has(key)) return
    reportedErrors.add(key)
    logger(error)
  }

  function loadManifest() {
    if (manifestPending) return manifestPending
    manifestPending = Promise.resolve()
      .then(() => fetchJson(PNE_2026_CADERNO_MANIFEST_PATH, { cache: 'no-store' }))
      .catch((error) => {
        throw structuredError(error, {
          code: 'manifest_unavailable',
          path: PNE_2026_CADERNO_MANIFEST_PATH,
          stage: 'manifest',
        })
      })
      .then((candidate) => {
        try {
          return parsePne2026CadernoManifest(candidate)
        } catch (error) {
          throw structuredError(error, {
            code: 'invalid_manifest',
            path: PNE_2026_CADERNO_MANIFEST_PATH,
            stage: 'manifest',
          })
        }
      })
      .finally(() => {
        manifestPending = null
      })
    return manifestPending
  }

  function municipalPath(municipalityId) {
    return PNE_2026_CADERNO_MUNICIPAL_PATH.replace('{municipalityId}', municipalityId)
  }

  async function loadDocument(municipalityId) {
    const manifest = await loadManifest()
    const entry = manifest.municipalities.find(
      (municipality) => municipality.ibge7 === municipalityId,
    )
    if (!entry) {
      throw new CadernoLoadError(
        `O caderno de hipóteses ainda não foi publicado para ${municipalityId}.`,
        { code: 'municipality_not_published', municipalityId, stage: 'manifest' },
      )
    }
    const key = `${entry.outputSha256}:${municipalityId}`
    return memoized(documentCache, key, async () => {
      const path = municipalPath(municipalityId)
      let candidate
      try {
        candidate = await fetchJson(path)
      } catch (error) {
        throw structuredError(error, {
          code: 'municipality_unavailable',
          municipalityId,
          path,
          stage: 'municipality',
        })
      }
      try {
        const caderno = parsePne2026Caderno(candidate)
        invariant(
          caderno.municipality.ibge7 === municipalityId,
          `documento municipal divergente: ${municipalityId}.`,
        )
        invariant(
          caderno.referenceDate === entry.referenceDate,
          `data de referência divergente do manifesto em ${municipalityId}.`,
        )
        invariant(
          caderno.municipality.name === entry.name && caderno.municipality.uf === entry.uf,
          `identidade municipal divergente do manifesto em ${municipalityId}.`,
        )
        return { caderno, entry }
      } catch (error) {
        throw structuredError(error, {
          code: 'invalid_payload',
          municipalityId,
          path,
          stage: 'municipality',
        })
      }
    })
  }

  function load(municipalityId) {
    const normalizedId = String(municipalityId)
    if (!IBGE7_PATTERN.test(normalizedId)) {
      const error = new CadernoLoadError(`Código municipal inválido: ${normalizedId}.`, {
        code: 'invalid_municipality',
        municipalityId: normalizedId,
        stage: 'input',
      })
      reportOnce(error)
      return Promise.reject(error)
    }
    return loadDocument(normalizedId)
      .then(({ caderno, entry }) => ({
        schemaVersion: 'pne2026-caderno-loader-result-v1',
        municipalityId: normalizedId,
        municipalityName: caderno.municipality.name,
        referenceDate: caderno.referenceDate,
        outputSha256: entry.outputSha256,
        caderno,
      }))
      .catch((error) => {
        const structured = structuredError(error, {
          code: 'caderno_unavailable',
          municipalityId: normalizedId,
          stage: 'load',
        })
        if (structured.municipalityId === null) {
          structured.municipalityId = normalizedId
        }
        reportOnce(structured)
        throw structured
      })
  }

  return { load }
}
