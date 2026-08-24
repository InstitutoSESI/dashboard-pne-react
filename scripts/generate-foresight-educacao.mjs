import { createHash } from 'node:crypto'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import {
  FORESIGHT_DOCUMENT_SCHEMA,
  FORESIGHT_MANIFEST_SCHEMA,
  FORESIGHT_MUNICIPAL_FILE_PATTERN,
  FORESIGHT_PUBLICATION_SCOPE,
  FORESIGHT_SCENARIO_COUNT,
  FORESIGHT_SECTION_KEYS,
  FORESIGHT_SOURCE_VERSION,
  parseForesightDocument,
  parseForesightManifest,
  serializeForContentVersion,
} from '../src/features/foresight/foresightEducacaoLoader.js'
import {
  HORIZON_SCAN_YEAR,
  HORIZON_STATE_YEAR,
  LAST_OBSERVED_YEAR,
} from '../src/features/foresight/foresightPublicLanguage.js'

/*
 * Materialização pública dos Cenários da educação municipal.
 *
 * O material chega fechado da camada de pesquisa: texto aprovado, séries
 * congeladas e horizonte definido. Este gerador não decide nada — ele confere
 * os resumos de entrada, projeta somente os campos que a interface renderiza,
 * recusa qualquer município sem cenário publicável e falha fechado diante de
 * linguagem técnica ou de número atribuído a ano futuro.
 *
 * A mesma entrada produz sempre a mesma saída: nenhuma data de relógio,
 * nenhum sorteio, nenhuma consulta de rede, nenhum modelo de linguagem.
 */

export const FORESIGHT_GENERATOR_VERSION = 'foresight-educacao-generator-v1'

const REPOSITORY_ROOT = new URL('../', import.meta.url)
const PUBLIC_ROOT = new URL('public/data/foresight-educacao/', REPOSITORY_ROOT)
const MANIFEST_OUTPUT = new URL('manifest.json', PUBLIC_ROOT)
const SCHEMA_OUTPUT = new URL('schema.json', PUBLIC_ROOT)

const CANONICAL_SOURCE_ROOT = 'C:\\Users\\rnbirck\\PROJETOS\\SESI\\PNE\\foresight'
const STAGING_SOURCE_ROOT = fileURLToPath(new URL('staging/foresight_rodada_04g/', REPOSITORY_ROOT))
const PROMOTION_MANIFEST_NAME = 'MANIFESTO_PROMOCAO_V0_4_0_RC4_PARA_CANONICO.json'

/*
 * Municípios candidatos à publicação. A lista existe para o gerador saber onde
 * procurar; a publicação em si depende do que o pacote declara. Muliterno está
 * aqui de propósito: ele precisa ser lido e recusado, não ignorado.
 */
const CANDIDATES = Object.freeze([
  { directory: 'nova_santa_rita', fileSuffix: 'nova_santa_rita' },
  { directory: 'sao_leopoldo', fileSuffix: 'sao_leopoldo' },
  { directory: 'muliterno', fileSuffix: 'muliterno' },
])

const CATALOG_RELATIVE_PATH = 'base_conhecimento/11_linguagem_publica/catalogo_linguagem_publica_foresight_v0.4.0-rc4.json'
const CONTRACT_RELATIVE_PATH = 'base_conhecimento/07_contratos_validadores/contrato_cenarios_educacao_v0.4.0-rc4.json'

/* Moldura editorial da página. Texto institucional, revisado, sem número
 * além do horizonte declarado. */
const PAGE_COPY = Object.freeze({
  eyebrow: 'Planejamento educacional',
  title: 'Cenários da educação municipal',
  description: 'Quatro configurações exploratórias mostram como a educação do município pode se organizar até 2031, considerando as trajetórias já observadas e diferentes combinações de condições. A leitura acompanha sinais até 2036.',
  neutralityNote: 'Os cenários não são previsões, não recebem probabilidade e não representam uma ordem do pior para o melhor.',
})

const HORIZON_COPY = Object.freeze({
  stateLabel: 'Configuração descrita até 2031',
  scanLabel: 'Sinais acompanhados até 2036',
})

const HOW_TO_READ = Object.freeze({
  label: 'Como ler os cenários',
  description: 'Cada cenário é uma leitura possível do mesmo município, escrita a partir das séries já observadas e de condições que podem se combinar de maneiras diferentes.',
  items: Object.freeze([
    'Leia os quatro com o mesmo peso: nenhum é preferível, nenhum é mais esperado que os outros.',
    'Cada cenário parte dos mesmos números observados e muda apenas a forma como as condições se combinam.',
    'A leitura descreve uma configuração até 2031 e indica sinais para acompanhar até 2036, sem atribuir valor a anos futuros.',
    'Os sinais indicados servem para revisar a leitura quando novas edições dos dados forem divulgadas.',
  ]),
})

const STARTING_POINT_COPY = Object.freeze({
  label: 'De onde o município parte',
  description: 'Síntese dos movimentos já observados no município, das tensões entre as dimensões acompanhadas e do que limita esta leitura.',
})

const OBSERVED_SERIES_COPY = Object.freeze({
  label: 'O que já foi observado',
  description: 'Os valores abaixo são os das séries públicas do município, nos períodos efetivamente comparados. Eles descrevem o passado; nenhum deles é estendido para os anos à frente.',
})

const SIGNALS_COPY = Object.freeze({
  label: 'Sinais para acompanhar',
  description: 'Reunidos dos quatro cenários. Acompanhar estes sinais é o que permite revisar a leitura quando novas edições dos dados forem divulgadas.',
})

/*
 * Rótulos de direção e formatação numérica idênticos aos da camada de pesquisa.
 * Cada valor formatado é conferido contra o texto aprovado antes de ser
 * publicado: se divergir de uma vírgula, a materialização falha.
 */
const DIRECTION_LABELS = Object.freeze({
  increase: 'alta no período',
  decrease: 'queda no período',
  stable: 'estabilidade no período',
  oscillation: 'oscilação no período',
  not_comparable: 'sem direção única no período',
})

const SHARED_CONDITIONS_COPY = Object.freeze({
  label: 'Condições comuns aos quatro cenários',
  description: 'Estas condições e ressalvas valem para os quatro cenários e por isso aparecem uma única vez.',
})

const SOURCES_COPY = Object.freeze({
  label: 'Fontes e metodologia',
  description: 'As séries abaixo são as mesmas já publicadas para o município nesta plataforma, com os períodos efetivamente usados na leitura.',
})

const LIMITATIONS_COPY = Object.freeze({
  label: 'Limites desta leitura',
  description: 'O que esta página deliberadamente não faz.',
})

const SOURCE_NOTES = Object.freeze([
  'A leitura descreve uma configuração até 2031 e acompanha sinais até 2036.',
  'Nenhum valor é calculado para os anos à frente: os cenários descrevem configurações, não quantidades.',
  'Nesta versão, a dimensão demográfica utiliza as séries municipais já validadas e não apresenta projeções numéricas de nascimentos ou população.',
])

const LIMITATION_ITEMS = Object.freeze([
  'Os quatro cenários não recebem probabilidade, ordem de preferência nem pontuação.',
  'Nenhum número é atribuído a anos futuros; os valores citados são os observados nas séries públicas.',
  'Nesta versão, a dimensão demográfica utiliza as séries municipais já validadas e não apresenta projeções numéricas de nascimentos ou população.',
])

export class ForesightIngestionError extends Error {
  constructor(message) {
    super(message)
    this.name = 'ForesightIngestionError'
  }
}

function invariant(condition, message) {
  if (!condition) throw new ForesightIngestionError(`Cenários da educação — ${message}`)
}

function sha256(buffer) {
  return createHash('sha256').update(buffer).digest('hex')
}

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, 'utf8'))
}

/** Slug público derivado do próprio texto aprovado, sem identificador interno. */
export function slugify(value) {
  const slug = String(value)
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLocaleLowerCase('pt-BR')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
  invariant(slug.length > 0, `não foi possível derivar um identificador de rota de "${value}".`)
  return slug
}

/**
 * Resolve a raiz dos documentos aprovados. O canônico tem precedência; o
 * staging verificado é o recurso quando a promoção ainda não alcançou o disco.
 */
export function resolveSourceRoot(explicitRoot) {
  const candidates = explicitRoot
    ? [explicitRoot]
    : [CANONICAL_SOURCE_ROOT, STAGING_SOURCE_ROOT]
  for (const candidate of candidates) {
    if (fs.existsSync(path.join(candidate, PROMOTION_MANIFEST_NAME))) {
      return {
        root: candidate,
        origin: path.resolve(candidate) === path.resolve(CANONICAL_SOURCE_ROOT) ? 'canonical' : 'staging',
      }
    }
  }
  throw new ForesightIngestionError(
    `nenhuma raiz de origem verificada encontrada (${candidates.join(', ')}).`,
  )
}

/** Confere os resumos declarados no manifesto de promoção antes de ler qualquer conteúdo. */
export function verifySourceIntegrity(root) {
  const promotion = readJson(path.join(root, PROMOTION_MANIFEST_NAME))
  invariant(promotion.candidateVersion === FORESIGHT_SOURCE_VERSION, 'a origem não é a versão aprovada.')
  invariant(promotion.stablePromotion === false, 'a origem foi declarada estável; esta publicação é de candidata.')
  invariant(
    typeof promotion.canonicalPromotionStatus === 'string' && promotion.canonicalPromotionStatus.length > 0,
    'a origem não declara o estado de promoção.',
  )
  const declared = promotion.artifactSha256
  invariant(declared && typeof declared === 'object', 'a origem não declara os resumos dos documentos.')

  const verified = new Map()
  for (const [relative, expected] of Object.entries(declared)) {
    const absolute = path.join(root, relative.split('/').join(path.sep))
    invariant(fs.existsSync(absolute), `documento de origem ausente: ${relative}.`)
    const actual = sha256(fs.readFileSync(absolute))
    invariant(actual === expected, `resumo divergente em ${relative}.`)
    verified.set(relative, actual)
  }

  return {
    generatedAt: promotion.issuedAt,
    methodologyStatus: promotion.canonicalPromotionStatus,
    promotionExecuted: promotion.promotionExecuted === true,
    verified,
  }
}

function relativeFromRoot(root, absolute) {
  return path.relative(root, absolute).split(path.sep).join('/')
}

function requireVerified(integrity, relative) {
  const digest = integrity.verified.get(relative)
  invariant(Boolean(digest), `documento fora do conjunto verificado: ${relative}.`)
  return digest
}

function buildConceptIndex(catalog) {
  invariant(catalog.schemaVersion === 'public-language-catalog-v0.4.0-rc4', 'catálogo de linguagem inesperado.')
  const index = new Map()
  for (const concept of catalog.concepts) {
    index.set(concept.publicConceptId, {
      label: concept.publicShortLabel,
      unitLabel: concept.unitLabel,
    })
  }
  return index
}

function readContract(root) {
  const contract = readJson(path.join(root, CONTRACT_RELATIVE_PATH.split('/').join(path.sep)))
  invariant(contract.schemaVersion === 'education-scenario-contract-v0.4.0-rc4', 'contrato de cenários inesperado.')
  invariant(contract.frozenMethodology.horizonStateYear === HORIZON_STATE_YEAR, 'horizonte divergente do contrato.')
  invariant(contract.frozenMethodology.scanThroughYear === HORIZON_SCAN_YEAR, 'ano de varredura divergente do contrato.')
  invariant(
    contract.frozenMethodology.scoresWeightsRankingsProbabilitiesAllowed === false,
    'o contrato passou a admitir pontuação, peso, ranking ou probabilidade.',
  )
  invariant(
    contract.frozenMethodology.futureNumericProjectionAllowed === false,
    'o contrato passou a admitir projeção numérica futura.',
  )
  invariant(contract.frozenMethodology.failClosed === true, 'o contrato deixou de falhar fechado.')
  invariant(
    Array.isArray(contract.publicNarrativeStructure)
      && contract.publicNarrativeStructure.length === FORESIGHT_SECTION_KEYS.length
      && contract.publicNarrativeStructure.every(
        (label, index) => slugify(label) === FORESIGHT_SECTION_KEYS[index],
      ),
    'a estrutura pública das seções diverge do contrato.',
  )
  return contract
}

function uniqueTexts(values) {
  const seen = new Set()
  const output = []
  for (const value of values) {
    if (seen.has(value)) continue
    seen.add(value)
    output.push(value)
  }
  return output
}

/** Mesma regra da camada de pesquisa: inteiro com ponto de milhar, decimal com vírgula. */
function formatObservedValue(value, unit) {
  const number = Number(value)
  invariant(Number.isFinite(number), 'valor observado não numérico.')
  const formatted = Number.isInteger(number)
    ? new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 0 }).format(number)
    : number.toFixed(1).replace('.', ',')
  return unit === 'percent' ? `${formatted}%` : formatted
}

function splitSentences(text) {
  return String(text).split(/(?<=[.;!?])\s+/).map((sentence) => sentence.trim()).filter(Boolean)
}

/**
 * Uma janela observada: os dois valores das pontas, a direção declarada e a
 * ressalva que o texto aprovado carrega quando o período não é comparável.
 */
function buildWindow(assertion) {
  const { displayedValues: values, displayedWindow: window } = assertion
  const startValue = formatObservedValue(values.startValue, assertion.unit)
  const endValue = formatObservedValue(values.endValue, assertion.unit)

  invariant(
    assertion.publicText.includes(startValue) && assertion.publicText.includes(endValue),
    `os valores formatados divergem do texto aprovado em ${assertion.publicConceptId}.`,
  )
  const directionLabel = DIRECTION_LABELS[assertion.directionClass]
  invariant(Boolean(directionLabel), `direção sem rótulo público: ${assertion.directionClass}.`)
  invariant(
    window.endYear <= LAST_OBSERVED_YEAR,
    `janela observada com ano posterior ao último ano observado em ${assertion.publicConceptId}.`,
  )

  const caveat = splitSentences(assertion.publicText)
    .filter((sentence) => !sentence.includes(startValue) && !sentence.includes(endValue))
    .join(' ')

  return {
    startYear: window.startYear,
    endYear: window.endYear,
    periodLabel: `${window.startYear} a ${window.endYear}`,
    startValue,
    endValue,
    directionLabel,
    caveat: caveat.length > 0 ? caveat : null,
  }
}

/**
 * Séries observadas com valores, para a leitura de onde o município parte.
 * O período completo é a leitura principal; o trecho recente entra como
 * segunda linha quando a origem o declara, porque é onde as reversões
 * aparecem.
 */
function collectObservedSeries(trajectory, concepts) {
  const byConcept = new Map()

  for (const assertion of trajectory.assertions) {
    const concept = concepts.get(assertion.publicConceptId)
    invariant(Boolean(concept), `conceito público desconhecido: ${assertion.publicConceptId}.`)
    const current = byConcept.get(assertion.publicConceptId) ?? {
      label: concept.label,
      unitLabel: concept.unitLabel,
      fullPeriod: null,
      recentWindow: null,
    }
    if (assertion.trajectoryScope === 'full_period' && current.fullPeriod === null) {
      current.fullPeriod = buildWindow(assertion)
    }
    if (assertion.trajectoryScope === 'recent_window' && current.recentWindow === null) {
      current.recentWindow = buildWindow(assertion)
    }
    byConcept.set(assertion.publicConceptId, current)
  }

  const series = [...byConcept.values()]
  for (const serie of series) {
    invariant(serie.fullPeriod !== null, `série sem período completo: ${serie.label}.`)
  }
  return series
}

function collectSeries(trajectory, concepts) {
  const byConcept = new Map()
  for (const assertion of trajectory.assertions) {
    const concept = concepts.get(assertion.publicConceptId)
    invariant(Boolean(concept), `conceito público desconhecido: ${assertion.publicConceptId}.`)
    const windows = [assertion.displayedWindow, assertion.recentWindow, assertion.priorWindow]
      .filter((window) => window && Number.isInteger(window.startYear) && Number.isInteger(window.endYear))
    invariant(windows.length > 0, `série sem janela declarada em ${assertion.publicConceptId}.`)
    const current = byConcept.get(assertion.publicConceptId) ?? {
      label: concept.label,
      unitLabel: concept.unitLabel,
      startYear: Number.POSITIVE_INFINITY,
      endYear: Number.NEGATIVE_INFINITY,
    }
    for (const window of windows) {
      current.startYear = Math.min(current.startYear, window.startYear)
      current.endYear = Math.max(current.endYear, window.endYear)
    }
    byConcept.set(assertion.publicConceptId, current)
  }

  return [...byConcept.values()].map((serie) => {
    invariant(
      serie.endYear <= LAST_OBSERVED_YEAR,
      `a série "${serie.label}" declara um ano posterior ao último ano observado.`,
    )
    return {
      label: serie.label,
      unitLabel: serie.unitLabel,
      startYear: serie.startYear,
      endYear: serie.endYear,
      periodLabel: serie.startYear === serie.endYear
        ? `${serie.startYear}`
        : `${serie.startYear} a ${serie.endYear}`,
    }
  })
}

function buildScenarios(narrative, contract) {
  const assertionsById = new Map(narrative.assertions.map((assertion) => [assertion.assertionId, assertion]))
  const scenariosById = new Map(narrative.scenarios.map((scenario) => [scenario.scenarioId, scenario]))

  return narrative.scenarioOrder.map((scenarioId) => {
    const scenario = scenariosById.get(scenarioId)
    invariant(Boolean(scenario), `cenário ausente na narrativa aprovada.`)

    const sections = scenario.sections.map((section) => {
      const items = section.assertionIds.map((assertionId) => {
        const assertion = assertionsById.get(assertionId)
        invariant(Boolean(assertion), 'afirmação referenciada e ausente na narrativa aprovada.')
        invariant(
          assertion.temporality !== 'future_quantitative',
          'afirmação com quantidade futura recusada.',
        )
        return assertion.publicText
      })
      const labels = new Set(
        section.assertionIds.map((assertionId) => assertionsById.get(assertionId).publicLabel),
      )
      invariant(labels.size === 1, 'a seção mistura rótulos públicos diferentes.')
      const [label] = labels
      const key = slugify(label)
      invariant(
        contract.publicNarrativeStructure.includes(label),
        `rótulo de seção fora da estrutura pública: "${label}".`,
      )
      return { key, label, items }
    })

    const formation = sections.find((section) => section.key === 'como-este-cenario-se-forma')
    invariant(Boolean(formation) && formation.items.length > 0, 'cenário sem a seção que descreve sua formação.')

    return {
      slug: slugify(scenario.publicTitle),
      title: scenario.publicTitle,
      summary: formation.items[0],
      sections,
    }
  })
}

function sectionTexts(scenarios, key) {
  return uniqueTexts(
    scenarios.flatMap((scenario) => scenario.sections.find((section) => section.key === key)?.items ?? []),
  )
}

/** Projeta um município publicável; devolve `null` quando não há cenário. */
export function buildMunicipalDocument({ concepts, contract, integrity, narrative, root, technical, trajectory }) {
  if (technical.packageStatus !== 'scenarios_generated') return null
  if (!Array.isArray(technical.scenarios) || technical.scenarios.length === 0) return null
  if (!technical.narrativeAssertionsRef || !technical.scenarioMarkdownRef) return null

  invariant(narrative !== null && trajectory !== null, 'município com cenários e sem texto aprovado.')
  invariant(
    narrative.schemaVersion === 'public-scenario-narrative-v0.4.0-rc4',
    'esquema da narrativa aprovada inesperado.',
  )
  invariant(narrative.generation.llmUsed === false, 'a narrativa de origem não é determinística.')
  invariant(narrative.generation.networkUsed === false, 'a narrativa de origem consultou a rede.')
  invariant(narrative.generation.technicalIdsRendered === false, 'a narrativa de origem renderiza identificadores técnicos.')
  invariant(
    narrative.scenarioOrder.length === FORESIGHT_SCENARIO_COUNT,
    `a narrativa aprovada não traz ${FORESIGHT_SCENARIO_COUNT} cenários.`,
  )
  invariant(
    trajectory.municipality.ibgeCode === narrative.municipality.ibgeCode
      && technical.municipality.ibgeCode === narrative.municipality.ibgeCode,
    'os documentos de origem pertencem a municípios diferentes.',
  )

  const scenarios = buildScenarios(narrative, contract)
  const sharedItems = narrative.sharedConditions.map((condition) => condition.publicText)
  invariant(sharedItems.length > 0, 'município sem condições comuns declaradas.')

  const artifacts = [
    { name: 'pacote municipal', relative: relativeFromRoot(root, technical.__path) },
    { name: 'narrativa pública', relative: relativeFromRoot(root, narrative.__path) },
    { name: 'afirmações de trajetória', relative: relativeFromRoot(root, trajectory.__path) },
  ].map((artifact) => ({
    name: artifact.name,
    sha256: requireVerified(integrity, artifact.relative),
  }))

  const body = {
    schemaVersion: FORESIGHT_DOCUMENT_SCHEMA,
    sourceVersion: FORESIGHT_SOURCE_VERSION,
    sourceMethodologyStatus: integrity.methodologyStatus,
    generatedAt: integrity.generatedAt,
    publicationScope: FORESIGHT_PUBLICATION_SCOPE,
    municipality: {
      ibgeCode: narrative.municipality.ibgeCode,
      name: narrative.municipality.name,
      uf: narrative.municipality.state,
      slug: narrative.municipality.slug,
    },
    page: { ...PAGE_COPY },
    horizon: {
      stateYear: HORIZON_STATE_YEAR,
      scanThroughYear: HORIZON_SCAN_YEAR,
      ...HORIZON_COPY,
    },
    howToRead: { ...HOW_TO_READ, items: [...HOW_TO_READ.items] },
    startingPoint: {
      ...STARTING_POINT_COPY,
      movements: sectionTexts(scenarios, 'de-onde-o-municipio-parte'),
      tensions: sectionTexts(scenarios, 'como-a-educacao-chegou-a-essa-situacao'),
      limits: sectionTexts(scenarios, 'limite-especifico'),
    },
    observedSeries: {
      ...OBSERVED_SERIES_COPY,
      items: collectObservedSeries(trajectory, concepts),
    },
    sharedConditions: { ...SHARED_CONDITIONS_COPY, items: sharedItems },
    scenarios,
    signals: {
      ...SIGNALS_COPY,
      items: sectionTexts(scenarios, 'o-que-acompanhar'),
    },
    sources: {
      ...SOURCES_COPY,
      series: collectSeries(trajectory, concepts),
      notes: [...SOURCE_NOTES],
    },
    limitations: { ...LIMITATIONS_COPY, items: [...LIMITATION_ITEMS] },
    provenance: {
      methodologySource: FORESIGHT_SOURCE_VERSION,
      methodologyStatus: integrity.methodologyStatus,
      publicationScope: FORESIGHT_PUBLICATION_SCOPE,
      artifacts,
    },
  }

  invariant(body.startingPoint.limits.length > 0, 'município sem limites declarados para a leitura.')

  const document = { ...body, contentVersion: sha256(serializeForContentVersion(body)) }
  return parseForesightDocument(document)
}

function loadCandidate(root, candidate) {
  const base = path.join(root, 'pilotos', candidate.directory, FORESIGHT_SOURCE_VERSION)
  const technicalPath = path.join(base, `pacote_tecnico_${candidate.fileSuffix}.json`)
  if (!fs.existsSync(technicalPath)) return null

  const technical = readJson(technicalPath)
  technical.__path = technicalPath

  const narrativePath = path.join(base, `afirmacoes_narrativas_${candidate.fileSuffix}.json`)
  const trajectoryPath = path.join(base, `afirmacoes_trajetoria_${candidate.fileSuffix}.json`)
  const narrative = fs.existsSync(narrativePath) ? readJson(narrativePath) : null
  const trajectory = fs.existsSync(trajectoryPath) ? readJson(trajectoryPath) : null
  if (narrative) narrative.__path = narrativePath
  if (trajectory) trajectory.__path = trajectoryPath

  return { narrative, technical, trajectory }
}

function serializeDocument(document) {
  return `${JSON.stringify(document, null, 2)}\n`
}

/** Constrói manifesto e pacotes municipais sem tocar no disco. */
export function buildPublication({ sourceRoot } = {}) {
  const { origin, root } = resolveSourceRoot(sourceRoot)
  const integrity = verifySourceIntegrity(root)
  const contract = readContract(root)
  const concepts = buildConceptIndex(readJson(path.join(root, CATALOG_RELATIVE_PATH.split('/').join(path.sep))))

  const documents = []
  const refused = []

  for (const candidate of CANDIDATES) {
    const loaded = loadCandidate(root, candidate)
    if (!loaded) {
      refused.push({ candidate: candidate.directory, reason: 'documento de origem ausente' })
      continue
    }
    const document = buildMunicipalDocument({ concepts, contract, integrity, root, ...loaded })
    if (document === null) {
      refused.push({
        candidate: candidate.directory,
        ibgeCode: loaded.technical.municipality.ibgeCode,
        reason: 'município sem cenário publicável na origem aprovada',
      })
      continue
    }
    documents.push(document)
  }

  invariant(documents.length > 0, 'nenhum município publicável.')

  const files = documents.map((document) => {
    const serialized = serializeDocument(document)
    return {
      byteSize: Buffer.byteLength(serialized, 'utf8'),
      contentHash: sha256(Buffer.from(serialized, 'utf8')),
      document,
      path: FORESIGHT_MUNICIPAL_FILE_PATTERN.replace('{municipalityId}', document.municipality.ibgeCode),
      serialized,
    }
  })

  const municipalities = files.map((file) => ({
    ibgeCode: file.document.municipality.ibgeCode,
    name: file.document.municipality.name,
    uf: file.document.municipality.uf,
    slug: file.document.municipality.slug,
    path: file.path,
    contentHash: file.contentHash,
    contentVersion: file.document.contentVersion,
    byteSize: file.byteSize,
    publicationStatus: 'published',
    scenarioCount: file.document.scenarios.length,
    sourceArtifacts: file.document.provenance.artifacts.map((artifact) => ({ ...artifact })),
  }))

  const manifestBody = {
    schemaVersion: FORESIGHT_MANIFEST_SCHEMA,
    documentSchemaVersion: FORESIGHT_DOCUMENT_SCHEMA,
    generatedAt: integrity.generatedAt,
    generatorVersion: FORESIGHT_GENERATOR_VERSION,
    sourceVersion: FORESIGHT_SOURCE_VERSION,
    sourceMethodologyStatus: integrity.methodologyStatus,
    publicationScope: FORESIGHT_PUBLICATION_SCOPE,
    municipalFilePattern: FORESIGHT_MUNICIPAL_FILE_PATTERN,
    horizonStateYear: HORIZON_STATE_YEAR,
    scanThroughYear: HORIZON_SCAN_YEAR,
    municipalities,
  }
  const manifest = parseForesightManifest({
    ...manifestBody,
    contentVersion: sha256(serializeForContentVersion({ ...manifestBody, contentVersion: '' })),
  })

  return { files, integrity, manifest, origin, refused, root }
}

/** Esquema público resumido, publicado ao lado dos dados. */
export function buildPublicSchema() {
  return {
    $schema: 'https://json-schema.org/draft/2020-12/schema',
    $id: 'https://painel.pne/data/foresight-educacao/schema.json',
    title: 'Cenários da educação municipal — contrato público',
    description: 'Projeção pública dos cenários exploratórios da educação municipal. Contém apenas os campos renderizados pela interface.',
    documentSchemaVersion: FORESIGHT_DOCUMENT_SCHEMA,
    manifestSchemaVersion: FORESIGHT_MANIFEST_SCHEMA,
    horizon: { stateYear: HORIZON_STATE_YEAR, scanThroughYear: HORIZON_SCAN_YEAR },
    sectionKeys: [...FORESIGHT_SECTION_KEYS],
    scenarioCount: FORESIGHT_SCENARIO_COUNT,
    publicationScope: FORESIGHT_PUBLICATION_SCOPE,
    rules: [
      'Somente municípios listados no manifesto possuem cenários publicados.',
      'Nenhum identificador interno, enum de processo ou resumo criptográfico aparece em texto renderizado.',
      'Nenhum valor numérico é atribuído a ano posterior ao último ano observado.',
      'Os quatro cenários têm o mesmo peso: não há ordem, pontuação ou probabilidade.',
    ],
  }
}

function writeFileAtomic(targetUrl, contents) {
  const target = fileURLToPath(targetUrl)
  fs.mkdirSync(path.dirname(target), { recursive: true })
  const temporary = `${target}.tmp`
  fs.writeFileSync(temporary, contents, 'utf8')
  fs.renameSync(temporary, target)
}

function main(argv) {
  const checkOnly = argv.includes('--check')
  const explicitIndex = argv.indexOf('--source')
  const sourceRoot = explicitIndex >= 0 ? argv[explicitIndex + 1] : undefined

  const publication = buildPublication({ sourceRoot })
  const manifestContents = `${JSON.stringify(publication.manifest, null, 2)}\n`
  const schemaContents = `${JSON.stringify(buildPublicSchema(), null, 2)}\n`

  const outputs = [
    { contents: manifestContents, url: MANIFEST_OUTPUT },
    { contents: schemaContents, url: SCHEMA_OUTPUT },
    ...publication.files.map((file) => ({
      contents: file.serialized,
      url: new URL(file.path, PUBLIC_ROOT),
    })),
  ]

  if (checkOnly) {
    let drift = 0
    for (const output of outputs) {
      const target = fileURLToPath(output.url)
      const current = fs.existsSync(target) ? fs.readFileSync(target, 'utf8') : null
      if (current !== output.contents) {
        drift += 1
        process.stderr.write(`divergente: ${relativeFromRoot(fileURLToPath(REPOSITORY_ROOT), target)}\n`)
      }
    }
    if (drift > 0) {
      process.exitCode = 1
      return
    }
    process.stdout.write(`Cenários da educação: ${publication.files.length} municípios conferidos, sem divergência.\n`)
    return
  }

  for (const output of outputs) writeFileAtomic(output.url, output.contents)

  process.stdout.write(
    `Cenários da educação publicados a partir da origem ${publication.origin}: `
    + `${publication.files.length} municípios (${publication.files.map((file) => file.document.municipality.name).join(', ')}).\n`,
  )
  for (const refusal of publication.refused) {
    process.stdout.write(`  recusado: ${refusal.candidate} — ${refusal.reason}.\n`)
  }
}

if (import.meta.url === `file://${process.argv[1]?.split(path.sep).join('/')}`
  || fileURLToPath(import.meta.url) === path.resolve(process.argv[1] ?? '')) {
  main(process.argv.slice(2))
}
