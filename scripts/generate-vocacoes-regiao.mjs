/*
 * Publica o Vocações da Região em `public/data/vocacoes-regiao/`.
 *
 * O gerador atravessa a fronteira uma vez, em tempo de publicação: lê o pacote
 * regional aprovado na camada de pesquisa, reconfere o resumo de cada arquivo
 * contra o manifesto da origem, transpõe para o contrato público
 * `vocacoes-regiao-2.0.0` e escreve. Depois disso a plataforma não sabe mais
 * que a camada de pesquisa existe — ela valida o artefato publicado, e só ele.
 *
 * Nada aqui inventa cenário, transpõe o pacote municipal para a região nem
 * reaproveita narrativa de outro escopo. A Fase A não tem cenários: o bloco
 * deles é da Fase B e entra por versão aditiva do contrato, não por campo
 * opcional deixado vazio.
 *
 * Determinismo: sem rede, sem relógio, sem modelo. A data de publicação vem da
 * data que a origem declara, não de `Date.now()` — dois `generate` seguidos
 * produzem os mesmos bytes, e é isso que o `--check` afirma.
 *
 * Uso:
 *   node scripts/generate-vocacoes-regiao.mjs            publica
 *   node scripts/generate-vocacoes-regiao.mjs --check    confere sem escrever
 *   node scripts/generate-vocacoes-regiao.mjs --source <dir>   origem explícita
 */

import fs from 'node:fs'
import path from 'node:path'
import { createHash } from 'node:crypto'
import { fileURLToPath } from 'node:url'

import {
  VOCACOES_MANIFEST_SCHEMA,
  VOCACOES_REGION_FILE_PATTERN,
  VOCACOES_SCOPE_TYPE,
  parseVocacoesManifest,
} from '../src/features/vocacoes-regiao/vocacoesRegiaoLoader.js'
import {
  AGGREGATION_LABELS,
  EVIDENCE_CLASS_LABELS,
  PROHIBITED_CLAIM_OPENER,
  UNIVERSE_LABELS,
  VOCACOES_DOCUMENT_SCHEMA,
  createVocacoesDocumentParser,
  slugify,
} from '../src/features/vocacoes-regiao/vocacoesRegiaoContract.js'
import {
  assertPublicationRules,
  createPublicLanguageGuard,
  scanPublicDocument,
} from './lib/vocacoes-public-language.mjs'

const REPOSITORY_ROOT = new URL('../', import.meta.url)
const OUTPUT_ROOT = new URL('public/data/vocacoes-regiao/', REPOSITORY_ROOT)

export const VOCACOES_GENERATOR_VERSION = 'vocacoes-regiao-generator-v2'
export const STATE_CODE = 'RS'
export const VOCACOES_PUBLICATION_SCOPE = 'estadual'

/*
 * Enquanto não houver origem aprovada, estes são os valores que o manifesto
 * vazio declara. Eles não descrevem conteúdo publicado: descrevem a ausência
 * dele, de um jeito que o leitor consegue validar.
 */
export const EMPTY_MANIFEST_SOURCE_VERSION = 'nao-publicado'
export const EMPTY_MANIFEST_METHODOLOGY_STATUS = 'contrato_de_origem_pendente'
export const EMPTY_MANIFEST_PUBLICATION_SCOPE = 'none'
export const EMPTY_MANIFEST_GENERATED_AT = '2026-08-24'
export const EMPTY_MANIFEST_REFERENCE_YEAR = 2026
export const EMPTY_MANIFEST_REFERENCE_MONTH = 8

/** Origem canônica do pacote regional, promovida na Rodada 4 do plano. */
export const DEFAULT_SOURCE_ROOT = 'C:/Users/rnbirck/PROJETOS/SESI/PNE/foresight/vocacoes-regiao'

export const PUBLIC_CONTRACT_APPROVAL_FILE = 'CONTRATO_PUBLICO_APROVADO.json'
export const ORIGIN_MANIFEST_FILE = 'MANIFESTO_ORIGEM.json'
export const RESEARCH_CONTRACT_FILE = 'contrato/contrato_vocacoes_regiao_pesquisa_v0_1.json'
export const REGISTRY_FILE = 'registro/registro_regioes_rs_v0_1.json'

export class VocacoesGeneratorError extends Error {
  constructor(message) {
    super(`Vocações da Região: ${message}`)
    this.name = 'VocacoesGeneratorError'
  }
}

function invariant(condition, message) {
  if (!condition) throw new VocacoesGeneratorError(message)
}

function sha256(buffer) {
  return createHash('sha256').update(buffer).digest('hex')
}

export function buildEmptyManifest() {
  return {
    schemaVersion: VOCACOES_MANIFEST_SCHEMA,
    documentSchemaVersion: VOCACOES_DOCUMENT_SCHEMA,
    scopeType: VOCACOES_SCOPE_TYPE,
    generatedAt: EMPTY_MANIFEST_GENERATED_AT,
    generatorVersion: VOCACOES_GENERATOR_VERSION,
    sourceVersion: EMPTY_MANIFEST_SOURCE_VERSION,
    sourceMethodologyStatus: EMPTY_MANIFEST_METHODOLOGY_STATUS,
    publicationScope: EMPTY_MANIFEST_PUBLICATION_SCOPE,
    referenceYear: EMPTY_MANIFEST_REFERENCE_YEAR,
    referenceMonth: EMPTY_MANIFEST_REFERENCE_MONTH,
    regionFilePattern: VOCACOES_REGION_FILE_PATTERN,
    stateCode: STATE_CODE,
    regions: [],
  }
}

/*
 * Recusa registrada, não exceção: origem que existe sem aprovação do contrato
 * público é o estado projetado das Rodadas 1–4. O gerador publica o manifesto
 * vazio e registra a recusa. Só é erro alto o estado inesperado — aprovação
 * presente declarando uma versão de contrato que este gerador não implementa.
 */
export function resolveSource(sourceRoot) {
  const resolved = path.resolve(sourceRoot ?? DEFAULT_SOURCE_ROOT)
  if (!fs.existsSync(resolved)) {
    return { available: false, root: resolved, refusal: null, approval: null }
  }
  const approvalPath = path.join(resolved, PUBLIC_CONTRACT_APPROVAL_FILE)
  if (!fs.existsSync(approvalPath)) {
    return {
      available: false,
      root: resolved,
      refusal:
        `a origem existe em ${resolved}, mas o contrato público "${VOCACOES_DOCUMENT_SCHEMA}" `
        + 'ainda não foi aprovado ali; o gerador publica o manifesto vazio e não transpõe '
        + 'nada por conta própria.',
      approval: null,
    }
  }
  const approval = JSON.parse(fs.readFileSync(approvalPath, 'utf8'))
  invariant(
    approval.publicContractVersion === VOCACOES_DOCUMENT_SCHEMA,
    `a origem em ${resolved} aprova o contrato público "${approval.publicContractVersion}", `
    + `mas esta versão do gerador implementa "${VOCACOES_DOCUMENT_SCHEMA}". Implemente a `
    + 'transposição da versão aprovada antes de publicar.',
  )
  return { available: true, root: resolved, refusal: null, approval }
}

/*
 * Índice de integridade da origem. Todo arquivo lido daqui em diante passa por
 * `readVerified`: resumo e tamanho conferidos contra o manifesto que a Rodada 4
 * promoveu. Divergência aborta a publicação — é o fail-closed do D7 aplicado à
 * fronteira, não ao runtime.
 */
function openVerifiedSource(root) {
  const manifestPath = path.join(root, ORIGIN_MANIFEST_FILE)
  invariant(fs.existsSync(manifestPath), `a origem em ${root} não traz ${ORIGIN_MANIFEST_FILE}.`)
  const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'))
  invariant(
    typeof manifest.contractVersion === 'string' && manifest.contractVersion !== '',
    'o manifesto da origem não declara a versão do contrato de pesquisa.',
  )
  invariant(Array.isArray(manifest.files), 'o manifesto da origem não lista arquivos.')

  const index = new Map()
  for (const entry of manifest.files) index.set(entry.path, entry)

  function readVerified(relative) {
    const entry = index.get(relative)
    invariant(entry !== undefined, `o manifesto da origem não declara "${relative}".`)
    const absolute = path.join(root, relative.split('/').join(path.sep))
    invariant(fs.existsSync(absolute), `o arquivo declarado na origem não existe em disco: ${relative}.`)
    const bytes = fs.readFileSync(absolute)
    const digest = sha256(bytes)
    invariant(
      digest === entry.sha256,
      `o resumo do arquivo de origem "${relative}" diverge do manifesto `
      + `(manifesto ${entry.sha256}, disco ${digest}).`,
    )
    invariant(
      bytes.byteLength === entry.byteSize,
      `o tamanho do arquivo de origem "${relative}" diverge do manifesto `
      + `(manifesto ${entry.byteSize}, disco ${bytes.byteLength}).`,
    )
    return bytes
  }

  return {
    manifest,
    readVerified,
    readVerifiedJson: (relative) => JSON.parse(readVerified(relative).toString('utf8')),
    sha256Of: (relative) => {
      const entry = index.get(relative)
      invariant(entry !== undefined, `o manifesto da origem não declara "${relative}".`)
      return entry.sha256
    },
  }
}

const MONTH_NAMES = Object.freeze([
  'janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho',
  'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro',
])

export function formatPeriodLabel(start, end, granularity) {
  if (granularity === 'annual') {
    return start === end ? `${start}` : `${start} a ${end}`
  }
  const render = (period) => {
    const year = Math.floor(period / 100)
    const month = period % 100
    return `${MONTH_NAMES[month - 1]} de ${year}`
  }
  return start === end ? render(start) : `${render(start)} a ${render(end)}`
}

function formatWindowLabel(window) {
  return window.start === window.end ? `${window.start}` : `${window.start} a ${window.end}`
}

/* ------------------------------------------------------------------ *
 * Moldura editorial.
 *
 * O contrato da pesquisa declara `freeRegionalTextAccepted: false`: a camada de
 * pesquisa não escreve prosa regional. A moldura da página — como ler, o que
 * cada bloco é, a nota de neutralidade — é editorial e é desta camada. Ela é
 * idêntica nas dez regiões, e só o nome da região varia: texto que mudasse de
 * região para região sem dado por trás seria narrativa inventada.
 * ------------------------------------------------------------------ */

function buildFraming(regionName) {
  return {
    page: {
      eyebrow: 'Análise regional',
      title: `Vocações da Região — ${regionName}`,
      description:
        `O que o território da região ${regionName} mostra sobre a educação dela: séries longas `
        + 'do território, leituras que colocam um resultado educacional e os fatores territoriais '
        + 'lado a lado, e pares de séries que mudaram ao mesmo tempo.',
      neutralityNote:
        'Esta página não afirma causa. Duas séries que se movem juntas são duas séries que se '
        + 'movem juntas: cada leitura mostra os números que a sustentam e diz, ela mesma, o que '
        + 'não se pode concluir dela.',
    },
    howToRead: {
      label: 'Como ler esta página',
      description:
        'Cinco avisos que valem para tudo o que vem abaixo, e que mudam o que os números querem '
        + 'dizer.',
      items: [
        'Os números somam os municípios da região. A soma não descreve nenhum município em '
        + 'particular, e uma região pode reunir realidades muito diferentes.',
        'Cada série diz de onde veio, que período cobre e como foi agregada.',
        'Prévia é prévia: os períodos ainda sujeitos a revisão aparecem marcados e nunca contam '
        + 'como observação fechada.',
        'Estimativa é estimativa: o que foi calculado a partir de outras séries vem com a nota de '
        + 'método que diz o que aquele número reúne.',
        'Cada leitura traz junto a interpretação que ela permite e a que ela proíbe. As duas fazem '
        + 'parte da leitura.',
      ],
    },
    territoryPortrait: {
      label: 'Retrato e transformações do território',
      description:
        'Séries longas da região: emprego formal, produção, demografia, nascimentos, cadastro '
        + 'social, comércio exterior e eventos climáticos. Todas vêm da soma dos municípios.',
    },
    associations: {
      label: 'Educação e território, lado a lado',
      description:
        'Cada leitura parte de um resultado educacional observado na região e mostra os fatores '
        + 'territoriais observados junto dele, com os números que sustentam a leitura. Nenhuma '
        + 'delas afirma que um moveu o outro.',
    },
    temporalPairs: {
      label: 'Transformações simultâneas',
      description:
        'Pares de séries que mudaram ao mesmo tempo na região, cada par na sua janela. Andar '
        + 'junto não é mover.',
    },
    sources: {
      label: 'Fontes',
      description: 'As fontes de onde vieram as séries desta página, com o período que cada uma cobre.',
    },
    limitations: {
      label: 'O que este retrato não alcança',
      description:
        'Os limites declarados pelo próprio pacote de origem. Eles não são ressalva de rodapé: '
        + 'são parte do que os números querem dizer.',
    },
  }
}

/* ------------------------------------------------------------------ *
 * Transposição.
 * ------------------------------------------------------------------ */

function transposeSeries(sourceSeries, researchContract, seriesIdByKey, labelByKey) {
  const universeType = sourceSeries.universe?.universeType ?? null
  let universeLabel = null
  if (universeType !== null) {
    invariant(
      Object.prototype.hasOwnProperty.call(researchContract.universeStatements ?? {}, universeType),
      `a origem usa o universo "${universeType}", que o próprio contrato dela não declara.`,
    )
    universeLabel = UNIVERSE_LABELS[universeType] ?? null
    invariant(
      universeLabel !== null,
      `o contrato público não tem frase para o universo "${universeType}". `
      + 'Escreva a frase antes de publicar a série — o enum não vai ao público.',
    )
  }

  const evidenceLabel = EVIDENCE_CLASS_LABELS[sourceSeries.evidenceClass]
  invariant(
    evidenceLabel !== undefined,
    `classe de evidência desconhecida na origem: "${sourceSeries.evidenceClass}".`,
  )
  const aggregationLabel = AGGREGATION_LABELS[sourceSeries.aggregationRule]
  invariant(
    aggregationLabel !== undefined,
    `regra de agregação desconhecida na origem: "${sourceSeries.aggregationRule}".`,
  )

  let ratioOf = null
  if (sourceSeries.ratioOf !== null && sourceSeries.ratioOf !== undefined) {
    const numerator = labelByKey.get(sourceSeries.ratioOf.numeratorSeriesKey)
    const denominator = labelByKey.get(sourceSeries.ratioOf.denominatorSeriesKey)
    invariant(
      numerator !== undefined && denominator !== undefined,
      `a série de razão "${sourceSeries.seriesKey}" referencia série que não está no pacote.`,
    )
    ratioOf = { numeratorLabel: numerator, denominatorLabel: denominator }
  }

  return {
    seriesId: seriesIdByKey.get(sourceSeries.seriesKey),
    label: sourceSeries.publicLabel,
    unitLabel: sourceSeries.unit,
    sourceLabel: sourceSeries.source.publicName,
    evidenceClass: sourceSeries.evidenceClass,
    evidenceLabel,
    universeLabel,
    aggregationLabel,
    ratioOf,
    periodGranularity: sourceSeries.periodGranularity,
    periodStart: sourceSeries.periodStart,
    periodEnd: sourceSeries.periodEnd,
    periodLabel: formatPeriodLabel(
      sourceSeries.periodStart,
      sourceSeries.periodEnd,
      sourceSeries.periodGranularity,
    ),
    preliminaryPeriods: [...sourceSeries.preliminaryPeriods],
    limitations: [...sourceSeries.limitations],
    points: sourceSeries.points.map((point) => ({
      period: point.period,
      value: point.value,
      evidenceClass: point.evidenceClass,
    })),
  }
}

function composeProhibitedClaim(claim) {
  const trimmed = claim.trim()
  invariant(trimmed !== '', 'a alegação proibida da origem está vazia.')
  const suffix = trimmed.endsWith('.') ? '' : '.'
  return `${PROHIBITED_CLAIM_OPENER}${trimmed}${suffix}`
}

function transposeAssociation(sourceAssociation, seriesIdByKey) {
  const outcomeId = seriesIdByKey.get(sourceAssociation.educationOutcome.seriesKey)
  invariant(
    outcomeId !== undefined,
    `a associação referencia um resultado educacional que não está no pacote: `
    + `"${sourceAssociation.educationOutcome.seriesKey}".`,
  )
  const factors = sourceAssociation.territorialFactors.map((factor) => {
    const seriesId = seriesIdByKey.get(factor.seriesKey)
    invariant(
      seriesId !== undefined,
      `a associação referencia um fator territorial que não está no pacote: "${factor.seriesKey}".`,
    )
    return { seriesId, label: factor.publicLabel }
  })

  /*
   * Duas associações da mesma região podem partir do mesmo resultado
   * educacional — na origem, "Matrículas no ensino médio" aparece duas vezes,
   * uma com a base demográfica e outra com o saldo de coortes. O identificador
   * público precisa separá-las, e o único material honesto para isso é o
   * rótulo dos fatores: derivá-lo da chave interna reintroduziria a taxonomia
   * que a guarda recusa.
   */
  const associationId = slugify(
    `${sourceAssociation.educationOutcome.publicLabel} e ${factors[0].label}`,
  )

  return {
    associationId,
    label: sourceAssociation.educationOutcome.publicLabel,
    window: { start: sourceAssociation.window.start, end: sourceAssociation.window.end },
    periodLabel: formatWindowLabel(sourceAssociation.window),
    educationOutcome: { seriesId: outcomeId, label: sourceAssociation.educationOutcome.publicLabel },
    territorialFactors: factors,
    observedStatement: sourceAssociation.observedStatement,
    allowedInterpretation: sourceAssociation.allowedInterpretation,
    prohibitedClaim: composeProhibitedClaim(
      sourceAssociation.forbiddenInterpretation.prohibitedClaim,
    ),
    hypotheses: [...sourceAssociation.hypotheses],
  }
}

function transposeTemporalPair(sourcePair, seriesIdByKey, labelByKey) {
  const build = (key, label) => {
    const seriesId = seriesIdByKey.get(key)
    invariant(seriesId !== undefined, `o par temporal referencia série ausente do pacote: "${key}".`)
    return { seriesId, label: labelByKey.get(key) ?? label }
  }
  return {
    pairId: slugify(sourcePair.publicLabel),
    label: sourcePair.publicLabel,
    window: { start: sourcePair.window.start, end: sourcePair.window.end },
    periodLabel: formatWindowLabel(sourcePair.window),
    seriesA: build(sourcePair.seriesKeyA),
    seriesB: build(sourcePair.seriesKeyB),
    observedStatement: sourcePair.observedStatement,
    prohibitedClaim: composeProhibitedClaim(sourcePair.forbiddenInterpretation.prohibitedClaim),
  }
}

/*
 * Fontes: uma linha por fonte pública, com a união dos períodos das séries que
 * vêm dela. A união é calculada na granularidade de cada série e apresentada em
 * anos — a página lista de onde veio o dado, não o recorte exato de cada série,
 * que já está na própria série.
 */
function buildSources(series) {
  const byLabel = new Map()
  for (const serie of series) {
    const startYear = serie.periodGranularity === 'annual'
      ? serie.periodStart
      : Math.floor(serie.periodStart / 100)
    const endYear = serie.periodGranularity === 'annual'
      ? serie.periodEnd
      : Math.floor(serie.periodEnd / 100)
    const current = byLabel.get(serie.sourceLabel)
    if (current === undefined) {
      byLabel.set(serie.sourceLabel, { start: startYear, end: endYear })
    } else {
      current.start = Math.min(current.start, startYear)
      current.end = Math.max(current.end, endYear)
    }
  }
  return [...byLabel.entries()]
    .sort((left, right) => left[0].localeCompare(right[0], 'pt-BR'))
    .map(([label, window]) => ({
      label,
      periodLabel: window.start === window.end ? `${window.start}` : `${window.start} a ${window.end}`,
    }))
}

/*
 * Versão de conteúdo: resumo determinístico do corpo, calculado sem o próprio
 * campo e com as chaves ordenadas. Gerador e leitor precisam concordar byte a
 * byte, e a ordenação é o que torna isso possível sem depender da ordem de
 * inserção.
 */
function canonicalize(value) {
  if (Array.isArray(value)) return value.map(canonicalize)
  if (typeof value === 'object' && value !== null) {
    return Object.keys(value)
      .sort()
      .reduce((accumulator, key) => {
        accumulator[key] = canonicalize(value[key])
        return accumulator
      }, {})
  }
  return value
}

export function computeContentVersion(documentWithoutVersion) {
  const body = { ...documentWithoutVersion }
  delete body.contentVersion
  return sha256(Buffer.from(JSON.stringify(canonicalize(body)), 'utf8'))
}

export function transposeRegion({
  registryRegion,
  sourcePackage,
  sourcePackageSha256,
  researchContract,
  guard,
}) {
  invariant(
    sourcePackage.packageStatus === 'complete',
    `o pacote da região "${registryRegion.slug}" está em "${sourcePackage.packageStatus}", `
    + 'e a Fase A só publica pacote completo.',
  )
  invariant(
    sourcePackage.scenarios === null,
    `o pacote da região "${registryRegion.slug}" traz cenários, e o contrato `
    + `${VOCACOES_DOCUMENT_SCHEMA} não os publica.`,
  )
  invariant(
    sourcePackage.generation.deterministic === true
      && sourcePackage.generation.networkUsed === false
      && sourcePackage.generation.clockUsed === false
      && sourcePackage.generation.modelUsed === false,
    `o pacote da região "${registryRegion.slug}" não se declara de geração determinística.`,
  )
  invariant(
    sourcePackage.region.slug === registryRegion.slug
      && sourcePackage.region.name === registryRegion.name
      && sourcePackage.region.uf === registryRegion.uf
      && sourcePackage.region.municipalityCount === registryRegion.municipalityCount,
    `a identidade do pacote diverge do registro territorial em "${registryRegion.slug}".`,
  )

  /*
   * Identificadores públicos e rótulos, resolvidos antes da transposição: as
   * associações e os pares referenciam séries pela chave interna, e é aqui que
   * a chave para de existir.
   */
  const seriesIdByKey = new Map()
  const labelByKey = new Map()
  const usedIds = new Map()
  for (const serie of sourcePackage.series) {
    const seriesId = slugify(serie.publicLabel)
    const previous = usedIds.get(seriesId)
    invariant(
      previous === undefined,
      `o identificador público "${seriesId}" sai de dois rótulos diferentes em `
      + `"${registryRegion.slug}": "${previous}" e "${serie.publicLabel}".`,
    )
    usedIds.set(seriesId, serie.publicLabel)
    seriesIdByKey.set(serie.seriesKey, seriesId)
    labelByKey.set(serie.seriesKey, serie.publicLabel)
  }

  const series = sourcePackage.series.map((serie) =>
    transposeSeries(serie, researchContract, seriesIdByKey, labelByKey))
  const framing = buildFraming(registryRegion.name)

  const body = {
    schemaVersion: VOCACOES_DOCUMENT_SCHEMA,
    generatedAt: sourcePackage.provenance.generatedAt,
    generatorVersion: VOCACOES_GENERATOR_VERSION,
    sourceVersion: researchContract.schemaVersion,
    sourceMethodologyStatus: researchContract.status,
    publicationScope: VOCACOES_PUBLICATION_SCOPE,
    region: {
      slug: registryRegion.slug,
      name: registryRegion.name,
      uf: registryRegion.uf,
      municipalityCount: registryRegion.municipalityCount,
    },
    page: framing.page,
    howToRead: framing.howToRead,
    territoryPortrait: { ...framing.territoryPortrait, series },
    associations: {
      ...framing.associations,
      items: sourcePackage.associations.map((association) =>
        transposeAssociation(association, seriesIdByKey)),
    },
    temporalPairs: {
      ...framing.temporalPairs,
      items: sourcePackage.temporalPairs.map((pair) =>
        transposeTemporalPair(pair, seriesIdByKey, labelByKey)),
    },
    sources: { ...framing.sources, items: buildSources(series) },
    limitations: {
      ...framing.limitations,
      items: sourcePackage.limitations.map((limitation) => limitation.statement),
    },
    provenance: {
      sourcePackageSha256,
      sourceContractVersion: sourcePackage.contractVersion,
      sourceBuilderVersion: sourcePackage.provenance.builderVersion,
      sourceGeneratedAt: sourcePackage.provenance.generatedAt,
      registrySha256: sourcePackage.region.registrySha256,
    },
  }

  const document = { ...body, contentVersion: computeContentVersion(body) }

  /* As duas guardas, na ordem em que interessam: linguagem primeiro, contrato
   * depois. Um documento que viola a linguagem não deve nem chegar a ser
   * validado como estrutura — a mensagem útil é a primeira. */
  scanPublicDocument(document, guard)
  assertPublicationRules(document, { cadastralUniverseLabel: guard.cadastralUniverseLabel })

  return document
}

export function buildPublication({ sourceRoot } = {}) {
  const source = resolveSource(sourceRoot)
  if (!source.available) {
    const manifest = buildEmptyManifest()
    parseVocacoesManifest(structuredClone(manifest))
    return { manifest, files: [], origin: source.root, available: false, refusal: source.refusal }
  }

  const verified = openVerifiedSource(source.root)
  const researchContract = verified.readVerifiedJson(RESEARCH_CONTRACT_FILE)
  invariant(
    researchContract.contractVersion === verified.manifest.contractVersion.replace(/^.*-/u, '')
      || verified.manifest.contractVersion.endsWith(researchContract.contractVersion),
    'a versão do contrato de pesquisa diverge do manifesto da origem.',
  )
  invariant(
    researchContract.blocks.block4RegionalScenarios === 'absent_in_v0_1',
    'o contrato da pesquisa passou a prever cenários; a Fase A não os publica.',
  )

  const guard = createPublicLanguageGuard(researchContract)
  guard.cadastralUniverseLabel = UNIVERSE_LABELS.cadastral_registry

  const registry = verified.readVerifiedJson(REGISTRY_FILE)
  invariant(registry.stateCode === STATE_CODE, `o registro territorial não é de ${STATE_CODE}.`)
  invariant(
    registry.partitionVerified === true,
    'o registro territorial não declara a partição verificada dos municípios.',
  )
  invariant(
    Array.isArray(registry.regions) && registry.regions.length === registry.regionCount,
    'o registro territorial não lista as regiões que declara.',
  )

  const parseDocument = createVocacoesDocumentParser({
    sourceVersion: researchContract.schemaVersion,
    publicationScope: VOCACOES_PUBLICATION_SCOPE,
    referenceYear: researchContract.referenceYear,
    referenceMonth: researchContract.referenceMonth,
  })

  const regions = []
  const files = []
  let generatedAt = null
  let methodologyStatus = null

  for (const registryRegion of [...registry.regions].sort((left, right) =>
    left.slug.localeCompare(right.slug, 'en'))) {
    const relative = `pacotes/regioes/${registryRegion.slug}.json`
    const sourcePackage = verified.readVerifiedJson(relative)
    const document = transposeRegion({
      registryRegion,
      sourcePackage,
      sourcePackageSha256: verified.sha256Of(relative),
      researchContract,
      guard,
    })

    /* O validador de produção roda sobre o que vai ao disco, não sobre o que o
     * gerador tinha em memória: é o mesmo código que o navegador executará. */
    parseDocument(structuredClone(document))

    const serialized = `${JSON.stringify(document, null, 2)}\n`
    const buffer = Buffer.from(serialized, 'utf8')
    const relativeOutput = VOCACOES_REGION_FILE_PATTERN.replace('{regionSlug}', registryRegion.slug)

    if (generatedAt === null) {
      generatedAt = document.generatedAt
      methodologyStatus = document.sourceMethodologyStatus
    }
    invariant(
      document.generatedAt === generatedAt && document.sourceMethodologyStatus === methodologyStatus,
      `a região "${registryRegion.slug}" declara data ou estado de origem diferente das anteriores.`,
    )

    files.push({ path: relativeOutput, serialized })
    regions.push({
      slug: document.region.slug,
      name: document.region.name,
      uf: document.region.uf,
      path: relativeOutput,
      municipalityCount: document.region.municipalityCount,
      contentHash: sha256(buffer),
      contentVersion: document.contentVersion,
      byteSize: buffer.byteLength,
      publicationStatus: 'published',
      seriesCount: document.territoryPortrait.series.length,
      associationCount: document.associations.items.length,
      temporalPairCount: document.temporalPairs.items.length,
    })
  }

  invariant(
    regions.length === registry.regionCount,
    `foram transpostas ${regions.length} regiões, e o registro declara ${registry.regionCount}.`,
  )

  const manifest = {
    schemaVersion: VOCACOES_MANIFEST_SCHEMA,
    documentSchemaVersion: VOCACOES_DOCUMENT_SCHEMA,
    scopeType: VOCACOES_SCOPE_TYPE,
    generatedAt,
    generatorVersion: VOCACOES_GENERATOR_VERSION,
    sourceVersion: researchContract.schemaVersion,
    sourceMethodologyStatus: methodologyStatus,
    publicationScope: VOCACOES_PUBLICATION_SCOPE,
    referenceYear: researchContract.referenceYear,
    referenceMonth: researchContract.referenceMonth,
    regionFilePattern: VOCACOES_REGION_FILE_PATTERN,
    stateCode: STATE_CODE,
    regions,
  }
  parseVocacoesManifest(structuredClone(manifest))

  return { manifest, files, origin: source.root, available: true, refusal: null }
}

function writeFileAtomic(targetUrl, contents) {
  const target = fileURLToPath(targetUrl)
  fs.mkdirSync(path.dirname(target), { recursive: true })
  const temporary = `${target}.tmp`
  fs.writeFileSync(temporary, contents, 'utf8')
  fs.renameSync(temporary, target)
}

/*
 * Arquivo publicado que o manifesto não declara é resíduo: uma região retirada
 * da publicação continuaria alcançável por caminho direto. O gerador remove o
 * que sobrou, e o `--check` acusa a sobra em vez de ignorá-la.
 */
function listStaleRegionFiles(manifest) {
  const directory = fileURLToPath(new URL('regioes/', OUTPUT_ROOT))
  if (!fs.existsSync(directory)) return []
  const declared = new Set(manifest.regions.map((entry) => `${entry.slug}.json`))
  return fs
    .readdirSync(directory)
    .filter((name) => name.endsWith('.json') && !declared.has(name))
    .map((name) => path.join(directory, name))
}

function main(argv) {
  const checkOnly = argv.includes('--check')
  const sourceIndex = argv.indexOf('--source')
  const sourceRoot = sourceIndex >= 0 ? argv[sourceIndex + 1] : undefined

  const publication = buildPublication({ sourceRoot })
  const outputs = [
    {
      contents: `${JSON.stringify(publication.manifest, null, 2)}\n`,
      url: new URL('manifest.json', OUTPUT_ROOT),
    },
    ...publication.files.map((file) => ({
      contents: file.serialized,
      url: new URL(file.path, OUTPUT_ROOT),
    })),
  ]
  const stale = listStaleRegionFiles(publication.manifest)

  if (checkOnly) {
    let drift = 0
    for (const output of outputs) {
      const target = fileURLToPath(output.url)
      const current = fs.existsSync(target) ? fs.readFileSync(target, 'utf8') : null
      if (current !== output.contents) {
        drift += 1
        process.stderr.write(`divergente: ${path.relative(fileURLToPath(REPOSITORY_ROOT), target)}\n`)
      }
    }
    for (const orphan of stale) {
      drift += 1
      process.stderr.write(`não declarado no manifesto: ${path.relative(fileURLToPath(REPOSITORY_ROOT), orphan)}\n`)
    }
    if (drift > 0) {
      process.exitCode = 1
      return
    }
    process.stdout.write(
      `Vocações da Região: conferido, ${publication.manifest.regions.length} regiões publicadas.\n`,
    )
    if (publication.refusal) {
      process.stdout.write(`Vocações da Região: recusa registrada — ${publication.refusal}\n`)
    }
    return
  }

  for (const output of outputs) writeFileAtomic(output.url, output.contents)
  for (const orphan of stale) fs.rmSync(orphan)

  if (publication.available) {
    const totals = publication.manifest.regions.reduce(
      (accumulator, entry) => ({
        series: accumulator.series + entry.seriesCount,
        associations: accumulator.associations + entry.associationCount,
        pairs: accumulator.pairs + entry.temporalPairCount,
      }),
      { series: 0, associations: 0, pairs: 0 },
    )
    process.stdout.write(
      `Vocações da Região: ${publication.manifest.regions.length} regiões publicadas — `
      + `${totals.series} séries, ${totals.associations} associações, ${totals.pairs} pares `
      + `temporais, a partir de ${publication.origin}.\n`,
    )
  } else if (publication.refusal) {
    process.stdout.write(
      `Vocações da Região: manifesto vazio publicado. Recusa registrada — ${publication.refusal}\n`,
    )
  } else {
    process.stdout.write(
      'Vocações da Região: manifesto vazio publicado — nenhuma região tem pacote, '
      + `a origem não existe em ${publication.origin}.\n`,
    )
  }
}

if (fileURLToPath(import.meta.url) === path.resolve(process.argv[1] ?? '')) {
  main(process.argv.slice(2))
}
