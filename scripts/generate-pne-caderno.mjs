import { createHash } from 'node:crypto'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import contract from '../contracts/pne2026-goal-indicator-contract.json' with { type: 'json' }

/*
 * Ingestão versionada do caderno de hipóteses causais por meta.
 *
 * O caderno nasce no pipeline de pesquisa (SESI\PNE,
 * `build_pne_priority_hypothesis_workbook.py`) e chega aqui como um artefato
 * fechado: nada é recalculado, reordenado ou reescrito. Este gerador apenas
 * (1) valida o esquema `pne-priority-hypothesis-workbook-v2` chave a chave,
 * (2) acrescenta os títulos oficiais do catálogo PNE 2026 já vigente na
 * plataforma — a mesma fonte que CyclePage e Diagnóstico usam — e
 * (3) publica o resultado sob `public/data/pne2026-caderno/` com os hashes da
 * entrada e da saída registrados no manifesto.
 *
 * `public/data` só nasce de gerador versionado: nenhuma das saídas abaixo pode
 * ser editada à mão.
 */

const CADERNO_PUBLIC_ROOT = new URL('../public/data/pne2026-caderno/', import.meta.url)
const CADERNO_MANIFEST_PATH = new URL('manifest.json', CADERNO_PUBLIC_ROOT)

export const CADERNO_GENERATOR_VERSION = 'pne2026-caderno-generator-v2'
export const CADERNO_SCHEMA_VERSION = 'pne2026-caderno-v2'
export const CADERNO_MANIFEST_SCHEMA_VERSION = 'pne2026-caderno-manifest-v2'
export const WORKBOOK_SCHEMA_VERSION = 'pne-priority-hypothesis-workbook-v2'
export const CADERNO_MUNICIPAL_FILE_PATTERN = 'municipios/{municipalityId}.json'

const ROOT_FIELDS = ['curation', 'disclaimer', 'goals', 'municipality', 'referenceDate', 'schemaVersion', 'sourceDiagnostic']
const CURATION_FIELDS = ['sha256', 'version']
const MUNICIPALITY_FIELDS = ['ibge7', 'name', 'uf']
const SOURCE_DIAGNOSTIC_FIELDS = ['builderVersion', 'catalogSha256', 'diagnosticCsvSha256']
const GOAL_FIELDS = ['goalId', 'hypotheses', 'indicators', 'monitoring_context', 'readingCautions']
const HYPOTHESIS_SECTIONS = ['adverse_signal', 'no_public_data', 'protective_present']
const INDICATOR_FIELDS = [
  'availability',
  'caveat',
  'collectionTrigger',
  'gapRaw',
  'indicatorId',
  'relationId',
  'targetReference',
  'trend',
  'unit',
  'valueRaw',
  'year',
]
const HYPOTHESIS_FIELDS = [
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
]
const SIGNAL_FIELDS = [
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
]
const EVIDENCE_FIELDS = ['designLevel', 'finding', 'id', 'levelForRelationship']
const RELATION_FIELDS = ['classificationRationale', 'deliberationClass', 'indicatorId', 'relationId']
const READING_CAUTION_FIELDS = ['factorId', 'name', 'note']
const MONITORING_CONTEXT_FIELDS = ['factorId', 'name', 'relations', 'signals']
const MONITORING_SIGNAL_FIELDS = ['dimensions', 'direction', 'measureId', 'period', 'unit', 'valueRaw']

const SHA256_PATTERN = /^[a-f0-9]{64}$/
const IBGE7_PATTERN = /^\d{7}$/
const ISO_DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/
const GOAL_ID_PATTERN = /^\d+$/

export class CadernoIngestionError extends Error {
  constructor(message) {
    super(message)
    this.name = 'CadernoIngestionError'
  }
}

function invariant(condition, message) {
  if (!condition) throw new CadernoIngestionError(`Caderno de hipóteses inválido: ${message}`)
}

function isRecord(value) {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value)
}

function assertExactFields(candidate, expectedFields, label) {
  invariant(isRecord(candidate), `${label} deve ser um objeto.`)
  const expected = [...expectedFields].toSorted()
  const actual = Object.keys(candidate).toSorted()
  const unknown = actual.filter((field) => !expected.includes(field))
  const missing = expected.filter((field) => !actual.includes(field))
  invariant(!unknown.length, `${label} contém campos desconhecidos: ${unknown.join(', ')}.`)
  invariant(!missing.length, `${label} não contém: ${missing.join(', ')}.`)
}

function assertTextFields(candidate, fields, label) {
  for (const field of fields) {
    invariant(typeof candidate[field] === 'string', `${label}.${field} deve ser texto.`)
  }
}

function assertTextList(candidate, label) {
  invariant(Array.isArray(candidate), `${label} deve ser uma lista.`)
  candidate.forEach((item, index) => {
    invariant(typeof item === 'string', `${label}[${index}] deve ser texto.`)
  })
}

function sha256(contents) {
  return createHash('sha256').update(contents).digest('hex')
}

/** Serialização canônica: chaves ordenadas e sem espaços, como no pipeline de origem. */
function canonicalJson(value) {
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(',')}]`
  if (isRecord(value)) {
    return `{${Object.keys(value)
      .toSorted()
      .map((key) => `${JSON.stringify(key)}:${canonicalJson(value[key])}`)
      .join(',')}}`
  }
  return JSON.stringify(value)
}

/**
 * Valida o caderno recebido do pipeline de pesquisa sem tocar em uma vírgula do
 * conteúdo: chaves fechadas, todo valor textual, nenhuma lista reordenada.
 */
export function parseHypothesisWorkbook(candidate) {
  assertExactFields(candidate, ROOT_FIELDS, 'caderno.json')
  invariant(
    candidate.schemaVersion === WORKBOOK_SCHEMA_VERSION,
    `schemaVersion deve ser ${WORKBOOK_SCHEMA_VERSION}.`,
  )
  assertTextFields(candidate, ['disclaimer', 'referenceDate'], 'caderno.json')
  invariant(candidate.disclaimer.trim().length > 0, 'disclaimer não pode ser vazio.')
  invariant(
    ISO_DATE_PATTERN.test(candidate.referenceDate),
    'referenceDate deve usar o formato AAAA-MM-DD.',
  )

  assertExactFields(candidate.curation, CURATION_FIELDS, 'curation')
  assertTextFields(candidate.curation, CURATION_FIELDS, 'curation')
  invariant(SHA256_PATTERN.test(candidate.curation.sha256), 'curation.sha256 deve ser um sha256.')

  assertExactFields(candidate.municipality, MUNICIPALITY_FIELDS, 'municipality')
  assertTextFields(candidate.municipality, MUNICIPALITY_FIELDS, 'municipality')
  invariant(
    IBGE7_PATTERN.test(candidate.municipality.ibge7),
    'municipality.ibge7 deve ser o código IBGE textual de sete dígitos.',
  )
  invariant(/^[A-Z]{2}$/.test(candidate.municipality.uf), 'municipality.uf deve ter duas letras.')
  invariant(candidate.municipality.name.trim().length > 0, 'municipality.name não pode ser vazio.')

  assertExactFields(candidate.sourceDiagnostic, SOURCE_DIAGNOSTIC_FIELDS, 'sourceDiagnostic')
  assertTextFields(candidate.sourceDiagnostic, SOURCE_DIAGNOSTIC_FIELDS, 'sourceDiagnostic')
  for (const field of ['catalogSha256', 'diagnosticCsvSha256']) {
    invariant(
      SHA256_PATTERN.test(candidate.sourceDiagnostic[field]),
      `sourceDiagnostic.${field} deve ser um sha256.`,
    )
  }

  invariant(Array.isArray(candidate.goals) && candidate.goals.length > 0, 'goals deve ser uma lista não vazia.')
  const seenGoals = new Set()
  for (const goal of candidate.goals) {
    assertExactFields(goal, GOAL_FIELDS, 'goals[]')
    invariant(typeof goal.goalId === 'string' && GOAL_ID_PATTERN.test(goal.goalId), 'goals[].goalId deve ser o número da meta.')
    invariant(!seenGoals.has(goal.goalId), `meta duplicada: ${goal.goalId}.`)
    seenGoals.add(goal.goalId)
    const label = `meta ${goal.goalId}`

    invariant(Array.isArray(goal.indicators) && goal.indicators.length > 0, `${label}: indicators deve ser uma lista não vazia.`)
    for (const indicator of goal.indicators) {
      assertExactFields(indicator, INDICATOR_FIELDS, `${label}.indicators[]`)
      assertTextFields(indicator, INDICATOR_FIELDS, `${label}.indicators[]`)
      invariant(
        indicator.relationId.split('.')[0] === goal.goalId,
        `${label}: o indicador ${indicator.relationId} pertence a outra meta.`,
      )
    }

    assertExactFields(goal.hypotheses, HYPOTHESIS_SECTIONS, `${label}.hypotheses`)
    for (const section of HYPOTHESIS_SECTIONS) {
      const hypotheses = goal.hypotheses[section]
      invariant(Array.isArray(hypotheses), `${label}.hypotheses.${section} deve ser uma lista.`)
      for (const hypothesis of hypotheses) {
        const hypothesisLabel = `${label}.${section}[${hypothesis?.factorId ?? '?'}]`
        assertExactFields(hypothesis, HYPOTHESIS_FIELDS, hypothesisLabel)
        assertTextFields(
          hypothesis,
          ['classDate', 'diagnosticRole', 'expectedRelationship', 'factorId', 'governability', 'mechanism', 'name'],
          hypothesisLabel,
        )
        invariant(
          hypothesis.classDate === candidate.referenceDate,
          `${hypothesisLabel}: classDate deve ser a data de referência da ficha.`,
        )
        assertTextList(hypothesis.howToConfirmLocally, `${hypothesisLabel}.howToConfirmLocally`)
        invariant(Array.isArray(hypothesis.signals), `${hypothesisLabel}.signals deve ser uma lista.`)
        for (const signal of hypothesis.signals) {
          assertExactFields(signal, SIGNAL_FIELDS, `${hypothesisLabel}.signals[]`)
          assertTextFields(signal, SIGNAL_FIELDS, `${hypothesisLabel}.signals[]`)
        }
        invariant(Array.isArray(hypothesis.evidence), `${hypothesisLabel}.evidence deve ser uma lista.`)
        for (const evidence of hypothesis.evidence) {
          assertExactFields(evidence, EVIDENCE_FIELDS, `${hypothesisLabel}.evidence[]`)
          assertTextFields(evidence, EVIDENCE_FIELDS, `${hypothesisLabel}.evidence[]`)
        }
        invariant(
          Array.isArray(hypothesis.relations) && hypothesis.relations.length > 0,
          `${hypothesisLabel}.relations deve ser uma lista não vazia.`,
        )
        for (const relation of hypothesis.relations) {
          assertExactFields(relation, RELATION_FIELDS, `${hypothesisLabel}.relations[]`)
          assertTextFields(relation, RELATION_FIELDS, `${hypothesisLabel}.relations[]`)
          invariant(
            goal.indicators.some(
              (indicator) => indicator.relationId === relation.relationId
                && indicator.indicatorId === relation.indicatorId,
            ),
            `${hypothesisLabel}: a relação ${relation.relationId}×${relation.indicatorId} não pertence à meta.`,
          )
        }
      }
    }

    invariant(Array.isArray(goal.readingCautions), `${label}.readingCautions deve ser uma lista.`)
    for (const caution of goal.readingCautions) {
      assertExactFields(caution, READING_CAUTION_FIELDS, `${label}.readingCautions[]`)
      assertTextFields(caution, READING_CAUTION_FIELDS, `${label}.readingCautions[]`)
    }

    invariant(Array.isArray(goal.monitoring_context), `${label}.monitoring_context deve ser uma lista.`)
    for (const context of goal.monitoring_context) {
      assertExactFields(context, MONITORING_CONTEXT_FIELDS, `${label}.monitoring_context[]`)
      assertTextFields(context, ['factorId', 'name'], `${label}.monitoring_context[]`)
      invariant(
        Array.isArray(context.relations) && context.relations.length > 0,
        `${label}.monitoring_context[].relations deve ser uma lista não vazia.`,
      )
      for (const relation of context.relations) {
        assertExactFields(relation, RELATION_FIELDS, `${label}.monitoring_context[].relations[]`)
        assertTextFields(relation, RELATION_FIELDS, `${label}.monitoring_context[].relations[]`)
        invariant(
          goal.indicators.some(
            (indicator) => indicator.relationId === relation.relationId
              && indicator.indicatorId === relation.indicatorId,
          ),
          `${label}.monitoring_context[]: a relação ${relation.relationId}×${relation.indicatorId} não pertence à meta.`,
        )
      }
      invariant(Array.isArray(context.signals), `${label}.monitoring_context[].signals deve ser uma lista.`)
      for (const signal of context.signals) {
        assertExactFields(signal, MONITORING_SIGNAL_FIELDS, `${label}.monitoring_context[].signals[]`)
        assertTextFields(signal, MONITORING_SIGNAL_FIELDS, `${label}.monitoring_context[].signals[]`)
      }
    }
  }

  return candidate
}

/**
 * Título oficial da meta legal, verbatim do contrato PNE 2026 da plataforma.
 *
 * O caderno agrupa por número de meta (`1`), enquanto o catálogo público nomeia
 * cada meta legal do número (`1.a`, `1.c`). Cada relação do caderno carrega o
 * seu `relationId`, então o título vem de lá — nada é sintetizado. Uma meta
 * legal ausente do catálogo interrompe a ingestão.
 */
function resolveLegalGoalTitle(relationId) {
  const legalGoal = contract.goals[relationId]
  invariant(
    legalGoal !== undefined,
    `a meta legal ${relationId} não existe no catálogo PNE 2026 da plataforma `
    + '(contracts/pne2026-goal-indicator-contract.json); publique o contrato antes de ingerir o caderno.',
  )
  invariant(
    typeof legalGoal.publicTitle === 'string' && legalGoal.publicTitle.trim().length > 0,
    `a meta legal ${relationId} não tem título oficial (publicTitle) no catálogo PNE 2026 da plataforma.`,
  )
  return legalGoal.publicTitle
}

function resolveIndicatorTitle(indicatorId) {
  const indicator = contract.indicators[indicatorId]
  invariant(
    indicator !== undefined,
    `o indicador ${indicatorId} não existe no catálogo PNE 2026 da plataforma.`,
  )
  invariant(
    typeof indicator.publicTitle === 'string' && indicator.publicTitle.trim().length > 0,
    `o indicador ${indicatorId} não tem título oficial (publicTitle) no catálogo PNE 2026 da plataforma.`,
  )
  return indicator.publicTitle
}

/**
 * Projeta o caderno validado no documento publicado. A ordem das metas, das
 * seções e de cada lista é a do artefato de origem e não pode ser alterada.
 */
export function projectCaderno(workbook) {
  return {
    schemaVersion: CADERNO_SCHEMA_VERSION,
    workbookSchemaVersion: workbook.schemaVersion,
    contractVersion: contract.contractVersion,
    municipality: { ...workbook.municipality },
    referenceDate: workbook.referenceDate,
    disclaimer: workbook.disclaimer,
    curation: workbook.curation,
    sourceDiagnostic: { ...workbook.sourceDiagnostic },
    goals: workbook.goals.map((goal) => {
      const legalGoalIds = []
      for (const indicator of goal.indicators) {
        if (!legalGoalIds.includes(indicator.relationId)) legalGoalIds.push(indicator.relationId)
      }

      return {
        goalId: goal.goalId,
        legalGoals: legalGoalIds.map((legalGoalId) => ({
          legalGoalId,
          title: resolveLegalGoalTitle(legalGoalId),
        })),
        indicators: goal.indicators.map((indicator) => ({
          ...indicator,
          legalGoalTitle: resolveLegalGoalTitle(indicator.relationId),
          indicatorTitle: resolveIndicatorTitle(indicator.indicatorId),
        })),
        hypotheses: {
          adverse_signal: goal.hypotheses.adverse_signal,
          no_public_data: goal.hypotheses.no_public_data,
          protective_present: goal.hypotheses.protective_present,
        },
        readingCautions: goal.readingCautions,
        monitoring_context: goal.monitoring_context,
      }
    }),
  }
}

function readManifest() {
  if (!fs.existsSync(CADERNO_MANIFEST_PATH)) return null
  const manifest = JSON.parse(fs.readFileSync(CADERNO_MANIFEST_PATH, 'utf8'))
  invariant(isRecord(manifest), 'manifest.json publicado deve ser um objeto.')
  invariant(Array.isArray(manifest.municipalities), 'manifest.json publicado deve declarar municipalities.')
  return manifest
}

export function buildManifest(previousManifest, entry) {
  const preserved = (previousManifest?.municipalities ?? []).filter(
    (municipality) => municipality.ibge7 !== entry.ibge7,
  )
  return {
    schemaVersion: CADERNO_MANIFEST_SCHEMA_VERSION,
    cadernoSchemaVersion: CADERNO_SCHEMA_VERSION,
    workbookSchemaVersion: WORKBOOK_SCHEMA_VERSION,
    generatorVersion: CADERNO_GENERATOR_VERSION,
    contractVersion: contract.contractVersion,
    municipalFilePattern: CADERNO_MUNICIPAL_FILE_PATTERN,
    municipalities: [...preserved, entry].toSorted(
      (left, right) => left.ibge7.localeCompare(right.ibge7),
    ),
  }
}

function writeGeneratedFile(targetUrl, contents) {
  fs.mkdirSync(new URL('.', targetUrl), { recursive: true })
  fs.writeFileSync(targetUrl, contents)
}

export function ingestCaderno(inputPath) {
  const rawInput = fs.readFileSync(inputPath)
  const workbook = parseHypothesisWorkbook(JSON.parse(rawInput.toString('utf8')))
  const caderno = projectCaderno(workbook)
  const output = `${canonicalJson(caderno)}\n`
  const municipalPath = CADERNO_MUNICIPAL_FILE_PATTERN.replace(
    '{municipalityId}',
    caderno.municipality.ibge7,
  )
  const entry = {
    ibge7: caderno.municipality.ibge7,
    name: caderno.municipality.name,
    uf: caderno.municipality.uf,
    referenceDate: caderno.referenceDate,
    path: municipalPath,
    inputSha256: sha256(rawInput),
    outputSha256: sha256(output),
    outputByteSize: Buffer.byteLength(output),
  }
  const manifest = buildManifest(readManifest(), entry)
  const manifestContents = `${JSON.stringify(manifest, null, 2)}\n`

  writeGeneratedFile(new URL(municipalPath, CADERNO_PUBLIC_ROOT), output)
  writeGeneratedFile(CADERNO_MANIFEST_PATH, manifestContents)

  return { caderno, entry, manifest }
}

function parseArguments(argv) {
  const inputIndex = argv.indexOf('--input')
  if (inputIndex === -1 || !argv[inputIndex + 1]) {
    throw new CadernoIngestionError(
      'Informe o caderno de origem: node scripts/generate-pne-caderno.mjs --input <caminho do caderno.json>',
    )
  }
  return { input: path.resolve(argv[inputIndex + 1]) }
}

function run() {
  const { input } = parseArguments(process.argv.slice(2))
  const { caderno, entry } = ingestCaderno(input)
  const goalCount = caderno.goals.length
  const indicatorCount = caderno.goals.reduce((total, goal) => total + goal.indicators.length, 0)
  console.log(
    [
      `Caderno publicado: ${entry.ibge7} ${entry.name}/${entry.uf} (${entry.referenceDate})`,
      `Metas: ${goalCount} | blocos de indicador: ${indicatorCount}`,
      `Entrada sha256: ${entry.inputSha256}`,
      `Saida  sha256: ${entry.outputSha256} (${entry.outputByteSize} bytes)`,
      `Arquivo: public/data/pne2026-caderno/${entry.path}`,
    ].join('\n'),
  )
}

if (process.argv[1] === fileURLToPath(import.meta.url)) run()
