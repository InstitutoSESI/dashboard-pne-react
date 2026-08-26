/*
 * Publica o Vocações da Região em `public/data/vocacoes-regiao/`.
 *
 * O gerador atravessa a fronteira uma vez, em tempo de publicação: lê o pacote
 * regional aprovado na camada de pesquisa, reconfere o resumo de cada arquivo
 * contra o manifesto da origem, transpõe para o contrato público
 * `vocacoes-regiao-2.3.0` e escreve. Depois disso a plataforma não sabe mais
 * que a camada de pesquisa existe — ela valida o artefato publicado, e só ele.
 *
 * Nada aqui inventa cenário nem transpõe o pacote municipal para a região. Duas
 * regiões têm cenários construídos na camada de pesquisa, e o gerador os
 * transpõe do pacote promovido delas; as outras oito publicam o Bloco 4
 * **declarando que não há cenário**, com a frase que o leitor lê. Ausência
 * declarada, nunca campo vazio.
 *
 * Os cenários vivem num arquivo separado do pacote da Fase A, e é assim de
 * propósito: o gerador transpõe os blocos 1–3 do pacote que a Rodada 4
 * promoveu, o Bloco 4 do pacote de cenários, e **recusa publicar se os dois
 * discordarem em qualquer byte dos três primeiros blocos**. Publicar cenário
 * não pode reescrever o retrato do território, e essa garantia é conferida aqui
 * em vez de prometida.
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
  AGENDA_THEME_LABELS,
  AGENDA_THEMES,
  AGGREGATION_LABELS,
  EVIDENCE_CLASS_LABELS,
  MUNICIPAL_KIND_LABELS,
  PROHIBITED_CLAIM_OPENER,
  SCENARIO_FRAMING,
  SCENARIO_DIRECTION_LABELS,
  SCENARIO_STATUTES,
  SCENARIO_STATUTE_LABELS,
  SYNTHESIS_FRAMING,
  SYNTHESIS_KIND_LABELS,
  SYNTHESIS_REQUIRED_OPENERS,
  UNIVERSE_LABELS,
  VOCACOES_DOCUMENT_SCHEMA,
  commonScenarioAgendaThemes,
  createVocacoesDocumentParser,
  renderAgendaSynthesis,
  slugify,
  synthesisAssociationBasisLabel,
  synthesisTemporalPairBasisLabel,
} from '../src/features/vocacoes-regiao/vocacoesRegiaoContract.js'
import {
  assertPublicationRules,
  createPublicLanguageGuard,
  scanPublicDocument,
} from './lib/vocacoes-public-language.mjs'

const REPOSITORY_ROOT = new URL('../', import.meta.url)
const OUTPUT_ROOT = new URL('public/data/vocacoes-regiao/', REPOSITORY_ROOT)

export const VOCACOES_GENERATOR_VERSION = 'vocacoes-regiao-generator-v4'
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
export const RESEARCH_CONTRACT_FILE = 'contrato/contrato_vocacoes_regiao_pesquisa_v0_2.json'
export const REGISTRY_FILE = 'registro/registro_regioes_rs_v0_1.json'

/** Pacote de cenários promovido na Rodada 9. Existe só nas regiões da Fase B. */
export const SCENARIO_PACKAGE_PATTERN = 'pacotes/cenarios/{regionSlug}.json'

/*
 * Pacote da camada municipal, promovido na Rodada 5 do V2 (sucessora da D11).
 * Existe só nas regiões que publicam cenário, e é conferido pelo manifesto como
 * qualquer outro arquivo de origem. A moldura da seção é editorial desta camada,
 * como a do Bloco 4 — o texto de composição e exposição vem da pesquisa.
 */
export const MUNICIPAL_LAYER_PACKAGE_PATTERN = 'pacotes/cenarios/municipal/{regionSlug}.json'

/** Pacote obrigatório da camada de conclusões promovida na Rodada 6 do V2. */
export const SYNTHESIS_LAYER_PACKAGE_PATTERN = 'pacotes/conclusoes/{regionSlug}.json'

export const MUNICIPAL_LAYER_FRAMING = Object.freeze({
  label: 'Os municípios no cenário',
  description:
    'Como cada município da região se posiciona nas séries que se decompõem ao município — '
    + 'demografia, cadastro social e fluxo escolar do ensino médio — e como essa composição '
    + 'observada se liga a cada cenário. Nenhum número é atribuído a um município no futuro, e '
    + 'nenhum cenário é atribuído a um município como destino: a leitura é de composição '
    + 'observada, não de previsão.',
})

/** Blocos que o pacote de cenários repete do pacote da Fase A, sem alterar. */
const SHARED_BLOCKS = Object.freeze(['series', 'associations', 'temporalPairs', 'region'])

/*
 * Ponte Vocações → PNE: temas de agenda por cenário (decisão `V2-D6`).
 *
 * É configuração versionada, e é editorial desta camada — o PNE não existe na
 * camada de pesquisa do Vocações. A chave é `regionSlug` → `order` do cenário
 * (o número estável 1..4, nunca a chave interna), e cada tema nomeia **a meta**
 * (enum de `AGENDA_THEME_LABELS`) e **o rótulo da implicação que o sustenta**
 * (`stageLabel`). O gerador resolve o `stageLabel` para a frase da implicação já
 * publicada no cenário — nenhuma prosa nova, nenhum número de meta. Um
 * `stageLabel` que não exista no cenário, ou um `theme` fora do enum, aborta a
 * publicação: a ponte não pode apontar para uma implicação que a página não tem.
 *
 * Cada tema aparece **uma vez por cenário**; um mesmo `stageLabel` pode
 * sustentar dois temas (a implicação de "ensino médio e educação profissional"
 * sustenta os dois temas de agenda correspondentes).
 */
export const AGENDA_THEME_MAP = Object.freeze({
  'vale-do-rio-pardo': {
    1: [
      { theme: 'oferta_e_rede', stageLabel: 'Rede e oferta' },
      { theme: 'ensino_medio', stageLabel: 'Ensino médio e educação profissional' },
      { theme: 'educacao_profissional', stageLabel: 'Ensino médio e educação profissional' },
      { theme: 'eja', stageLabel: 'Educação de jovens e adultos' },
      { theme: 'formacao_docente', stageLabel: 'Profissionais do ensino' },
    ],
    2: [
      { theme: 'oferta_e_rede', stageLabel: 'Rede e oferta' },
      { theme: 'ensino_medio', stageLabel: 'Ensino médio e educação profissional' },
      { theme: 'educacao_profissional', stageLabel: 'Ensino médio e educação profissional' },
      { theme: 'formacao_docente', stageLabel: 'Educação superior e formação continuada' },
    ],
    3: [
      { theme: 'ensino_medio', stageLabel: 'Fluxo escolar' },
      { theme: 'oferta_e_rede', stageLabel: 'Rede rural' },
      { theme: 'educacao_profissional', stageLabel: 'Educação profissional' },
      { theme: 'eja', stageLabel: 'Educação de jovens e adultos' },
    ],
    4: [
      { theme: 'gestao_e_planejamento', stageLabel: 'Planejamento da formação' },
      { theme: 'educacao_profissional', stageLabel: 'Educação profissional' },
    ],
  },
  noroeste: {
    1: [
      { theme: 'oferta_e_rede', stageLabel: 'Rede e alcance' },
      { theme: 'formacao_docente', stageLabel: 'Profissionais do ensino' },
      { theme: 'ensino_medio', stageLabel: 'Ensino médio e educação profissional' },
      { theme: 'educacao_profissional', stageLabel: 'Ensino médio e educação profissional' },
    ],
    2: [
      { theme: 'ensino_medio', stageLabel: 'Ensino médio e educação profissional' },
      { theme: 'educacao_profissional', stageLabel: 'Trabalho e formação' },
      { theme: 'formacao_docente', stageLabel: 'Profissionais do ensino' },
      { theme: 'eja', stageLabel: 'Educação de jovens e adultos' },
    ],
    3: [
      { theme: 'oferta_e_rede', stageLabel: 'Rede e alcance' },
      { theme: 'educacao_profissional', stageLabel: 'Trabalho e formação' },
    ],
    4: [
      { theme: 'gestao_e_planejamento', stageLabel: 'Arranjo de decisão' },
      { theme: 'oferta_e_rede', stageLabel: 'Rede e alcance' },
      { theme: 'formacao_docente', stageLabel: 'Profissionais do ensino' },
    ],
  },
})

export class VocacoesGeneratorError extends Error {
  constructor(message) {
    super(`Vocações da Região: ${message}`)
    this.name = 'VocacoesGeneratorError'
  }
}

function invariant(condition, message) {
  if (!condition) throw new VocacoesGeneratorError(message)
}

function isRecord(value) {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function assertExactKeys(value, expected, label) {
  invariant(isRecord(value), `${label} deve ser um objeto.`)
  const actual = Object.keys(value).sort()
  const wanted = [...expected].sort()
  invariant(
    JSON.stringify(actual) === JSON.stringify(wanted),
    `${label} deve trazer exatamente [${wanted.join(', ')}], mas traz [${actual.join(', ')}].`,
  )
}

function assertSameArray(actual, expected, label) {
  invariant(Array.isArray(actual), `${label} deve ser uma lista.`)
  invariant(
    JSON.stringify(actual) === JSON.stringify(expected),
    `${label} diverge do contrato (esperado ${JSON.stringify(expected)}, recebido `
    + `${JSON.stringify(actual)}).`,
  )
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
    declares: (relative) => index.has(relative),
    readVerifiedJson: (relative) => JSON.parse(readVerified(relative).toString('utf8')),
    sha256Of: (relative) => {
      const entry = index.get(relative)
      invariant(entry !== undefined, `o manifesto da origem não declara "${relative}".`)
      return entry.sha256
    },
  }
}

function validateSynthesisApproval(approval, registry) {
  const layer = approval.synthesisLayer
  invariant(isRecord(layer), 'o contrato público 2.5.0 não declara synthesisLayer.')
  const expectedRegions = registry.regions
    .map((region) => region.slug)
    .sort((left, right) => left.localeCompare(right, 'en'))
  assertSameArray(layer.regions, expectedRegions, 'synthesisLayer.regions')
  invariant(
    layer.packagePattern === SYNTHESIS_LAYER_PACKAGE_PATTERN,
    `synthesisLayer.packagePattern deve ser "${SYNTHESIS_LAYER_PACKAGE_PATTERN}".`,
  )
  invariant(
    layer.schemaVersion === 'vocacoes-regiao-pesquisa-conclusoes-v0.1',
    `synthesisLayer.schemaVersion desconhecida: "${layer.schemaVersion}".`,
  )
  assertSameArray(layer.allowedKinds, Object.keys(SYNTHESIS_KIND_LABELS),
    'synthesisLayer.allowedKinds')
  assertSameArray(layer.absenceDeclaredKinds, ['scenario_invariant', 'agenda'],
    'synthesisLayer.absenceDeclaredKinds')
  assertExactKeys(
    layer.requiredOpeners,
    Object.keys(SYNTHESIS_REQUIRED_OPENERS),
    'synthesisLayer.requiredOpeners',
  )
  for (const [kind, opener] of Object.entries(SYNTHESIS_REQUIRED_OPENERS)) {
    invariant(
      layer.requiredOpeners[kind] === opener,
      `synthesisLayer.requiredOpeners.${kind} diverge do abridor implementado.`,
    )
  }
  return layer
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
    /*
     * A moldura do Bloco 4 não é escrita aqui: ela vive no contrato, que é quem
     * a confere. A revisão adversarial do `2.1.0` mostrou que uma frase de
     * ausência livre podia afirmar que havia quatro cenários publicados, com o
     * documento inteiro em estado de ausência e a forma toda coerente. Frase
     * que o leitor lê sobre haver ou não cenário é tabela fechada, como a
     * frase do universo da série.
     */
    scenarios: SCENARIO_FRAMING,
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

/* ------------------------------------------------------------------ *
 * Bloco 4 — cenários da região.
 *
 * A transposição faz aqui o mesmo que faz na série: **a chave interna para de
 * existir**. `scenarioKey`, `anchorKey`, `implicationKey` e `criterionKey` são
 * vocabulário de processo e não atravessam a fronteira; o identificador público
 * do cenário nasce do título dele, como o da série nasce do rótulo.
 *
 * Dois enums da origem viram frase desta camada, e nunca o contrário: o
 * estatuto e a direção observada da âncora. A origem os declara; a plataforma
 * escreve o que o leitor lê. Foi assim que a Fase A tratou o universo da série,
 * e a razão é a mesma — os dois pacotes promovidos chegaram com frases de
 * estatuto diferentes entre si para o mesmo enum.
 * ------------------------------------------------------------------ */

function transposeAnchor(sourceAnchor, seriesIdByKey, labelByKey) {
  const seriesId = seriesIdByKey.get(sourceAnchor.seriesKey)
  invariant(
    seriesId !== undefined,
    `a âncora "${sourceAnchor.anchorKey}" cita uma série que não está no pacote: `
    + `"${sourceAnchor.seriesKey}".`,
  )
  const directionLabel = SCENARIO_DIRECTION_LABELS[sourceAnchor.observedDirection]
  invariant(
    directionLabel !== undefined,
    `direção observada desconhecida na origem: "${sourceAnchor.observedDirection}". `
    + 'Escreva a frase pública antes de publicar a âncora — o enum não vai ao público.',
  )
  return {
    seriesId,
    label: labelByKey.get(sourceAnchor.seriesKey) ?? sourceAnchor.publicLabel,
    window: { start: sourceAnchor.window.start, end: sourceAnchor.window.end },
    periodLabel: formatWindowLabel(sourceAnchor.window),
    startValue: sourceAnchor.startValue,
    endValue: sourceAnchor.endValue,
    directionLabel,
  }
}

/*
 * Temas de agenda de um cenário, resolvidos da configuração `AGENDA_THEME_MAP`
 * contra as implicações **já transpostas** do próprio cenário. É aqui que a
 * disciplina se fecha: cada tema aponta para a frase de uma implicação que a
 * página vai renderizar, e um `stageLabel` que não exista entre elas aborta a
 * publicação em vez de inventar uma frase.
 */
function buildAgendaThemes(regionSlug, order, implications) {
  const byRegion = AGENDA_THEME_MAP[regionSlug]
  invariant(
    byRegion !== undefined,
    `a região "${regionSlug}" publica cenários mas não declara temas de agenda em AGENDA_THEME_MAP.`,
  )
  const entries = byRegion[order]
  invariant(
    Array.isArray(entries) && entries.length > 0,
    `o cenário de ordem ${order} da região "${regionSlug}" não tem temas de agenda declarados.`,
  )
  const statementByStage = new Map(
    implications.map((implication) => [implication.stageLabel, implication.statement]),
  )
  return entries.map((entry) => {
    const label = AGENDA_THEME_LABELS[entry.theme]
    invariant(
      label !== undefined,
      `tema de agenda desconhecido em AGENDA_THEME_MAP: "${entry.theme}".`,
    )
    const statement = statementByStage.get(entry.stageLabel)
    invariant(
      statement !== undefined,
      `o tema "${entry.theme}" do cenário ${order} de "${regionSlug}" aponta para a etapa `
      + `"${entry.stageLabel}", que não é uma implicação educacional deste cenário.`,
    )
    return { theme: entry.theme, themeLabel: label, statement }
  })
}

function transposeScenarioItem(sourceItem, seriesIdByKey, labelByKey, regionSlug) {
  invariant(
    SCENARIO_STATUTES.includes(sourceItem.statute),
    `estatuto de cenário desconhecido na origem: "${sourceItem.statute}".`,
  )
  const educationImplications = sourceItem.educationImplications.map((implication) => ({
    stageLabel: implication.stageLabel,
    statement: implication.statement,
  }))
  return {
    scenarioId: slugify(sourceItem.publicTitle),
    order: sourceItem.order,
    profileLabel: sourceItem.profileLabel,
    title: sourceItem.publicTitle,
    statute: sourceItem.statute,
    statuteLabel: SCENARIO_STATUTE_LABELS[sourceItem.statute],
    centralMechanism: sourceItem.centralMechanism,
    startingPointStatement: sourceItem.startingPointStatement,
    trajectoryStatement: sourceItem.trajectoryStatement,
    stateAtHorizonStatement: sourceItem.stateAtHorizonStatement,
    anchors: sourceItem.anchors.map((anchor) =>
      transposeAnchor(anchor, seriesIdByKey, labelByKey)),
    educationImplications,
    agendaThemes: buildAgendaThemes(regionSlug, sourceItem.order, educationImplications),
    contraryEvidence: [...sourceItem.contraryEvidence],
    limits: [...sourceItem.limits],
    prohibitedClaim: composeProhibitedClaim(sourceItem.forbiddenInterpretation.prohibitedClaim),
  }
}

/*
 * Camada municipal — a leitura de cada município dentro do cenário regional.
 *
 * A transposição faz aqui o que faz no resto do Bloco 4: a **chave interna para
 * de existir**. `dimensionKey` é vocabulário de processo e não atravessa; o que
 * a página recebe é o rótulo público da dimensão, resolvido do próprio pacote. O
 * `municipalityId` é o código IBGE — identificador público oficial, e o único
 * que separa dois municípios de mesmo nome em estados diferentes (aqui, todos do
 * RS, mas o código é a identidade). A alegação proibida vira frase inteira com o
 * abridor do contrato, como na associação.
 */
function transposeMunicipalLayer(municipalPackage) {
  const labelByDimKey = new Map(
    municipalPackage.dimensions.map((dimension) => [dimension.key, dimension.publicLabel]),
  )
  const exposureByMunicipality = new Map()
  for (const scenario of municipalPackage.scenarioExposure) {
    for (const entry of scenario.municipalities) {
      if (!exposureByMunicipality.has(entry.ibge7)) exposureByMunicipality.set(entry.ibge7, [])
      exposureByMunicipality.get(entry.ibge7).push({
        order: scenario.order,
        exposureStatement: entry.exposureStatement,
        allowedInterpretation: entry.allowedInterpretation,
        prohibitedClaim: composeProhibitedClaim(entry.forbiddenInterpretation.prohibitedClaim),
      })
    }
  }

  return {
    label: MUNICIPAL_LAYER_FRAMING.label,
    description: MUNICIPAL_LAYER_FRAMING.description,
    methodNote: [
      municipalPackage.method.shareRule,
      municipalPackage.method.tierRule,
      municipalPackage.method.noProjection,
    ].join(' '),
    dimensions: municipalPackage.dimensions.map((dimension) => {
      const kindLabel = MUNICIPAL_KIND_LABELS[dimension.kind]
      invariant(
        kindLabel !== undefined,
        `a dimensão municipal "${dimension.key}" declara a natureza "${dimension.kind}", `
        + 'que o contrato público não tem frase para escrever.',
      )
      let universeLabel = null
      if (dimension.universeType !== undefined && dimension.universeType !== null) {
        universeLabel = UNIVERSE_LABELS[dimension.universeType] ?? null
        invariant(
          universeLabel !== null,
          `o contrato público não tem frase para o universo "${dimension.universeType}" da `
          + 'dimensão municipal.',
        )
      }
      return {
        label: dimension.publicLabel,
        sourceLabel: dimension.source.publicName,
        unitLabel: dimension.unit,
        periodLabel: formatMunicipalPeriod(dimension.referencePeriod),
        kindLabel,
        universeLabel,
      }
    }),
    undecomposableDomains: municipalPackage.undecomposableDomains.map((domain) => ({
      label: domain.label,
      consultedSource: domain.consultedSource,
      reason: domain.reason,
    })),
    municipalities: municipalPackage.municipalities.map((municipality) => {
      const exposures = exposureByMunicipality.get(municipality.ibge7) ?? []
      return {
        municipalityId: municipality.ibge7,
        name: municipality.name,
        composition: municipality.composition.map((line) => {
          const dimensionLabel = labelByDimKey.get(line.dimensionKey)
          invariant(
            dimensionLabel !== undefined,
            `a composição do município ${municipality.ibge7} cita a dimensão `
            + `"${line.dimensionKey}", que não está entre as dimensões do pacote.`,
          )
          return { dimensionLabel, statement: line.statement }
        }),
        scenarioExposure: [...exposures].sort((left, right) => left.order - right.order),
      }
    }),
  }
}

function formatMunicipalPeriod(period) {
  if (period >= 100000) {
    const year = Math.floor(period / 100)
    const month = period % 100
    return `${MONTH_NAMES[month - 1]} de ${year}`
  }
  return `${period}`
}

function transposeScenarioBlock(sourceBlock, seriesIdByKey, labelByKey, regionSlug, municipalPackage) {
  /*
   * O teto de compatibilidade da origem é uma letra (`B`) — marca de nível
   * interna, do vocabulário da metodologia. O que atravessa a fronteira é a
   * frase que explica o alcance da leitura; a letra fica do lado de lá.
   */
  return {
    methodologyLabel: `${sourceBlock.methodologyName}, versão ${sourceBlock.methodologyVersion}`,
    focalQuestion: sourceBlock.focalQuestion,
    maturityNote: sourceBlock.maturityNote,
    statuteNote: sourceBlock.statuteNote,
    baseYear: sourceBlock.baseYear,
    targetYear: sourceBlock.targetYear,
    longScanTargetYear: sourceBlock.longScanTargetYear,
    baseYearStatement: sourceBlock.baseYearStatement,
    horizonStatement: sourceBlock.horizonStatement,
    longScanStatement: sourceBlock.longScanStatement,
    compatibilityCeilingStatement: sourceBlock.compatibilityCeilingStatement,
    items: [...sourceBlock.items]
      .sort((left, right) => left.order - right.order)
      .map((item) => transposeScenarioItem(item, seriesIdByKey, labelByKey, regionSlug)),
    normativeCriteria: [...sourceBlock.normativeCriteria]
      .sort((left, right) => left.order - right.order)
      .map((criterion) => ({
        order: criterion.order,
        publicName: criterion.publicName,
        definition: criterion.definition,
        requiredState: criterion.requiredState,
        tradeOff: criterion.tradeOff,
        failureMode: criterion.failureMode,
        whatToFollow: criterion.whatToFollow,
      })),
    realizationConditions: [...sourceBlock.realizationConditions],
    robustImplications: [...sourceBlock.robustImplications],
    conditionalImplication: sourceBlock.conditionalImplication,
    prohibitedClaim: composeProhibitedClaim(sourceBlock.forbiddenInterpretation.prohibitedClaim),
    municipalLayer: transposeMunicipalLayer(municipalPackage),
  }
}

/* ------------------------------------------------------------------ *
 * Camada de conclusões — transposição e reverificação fail-closed.
 * ------------------------------------------------------------------ */

const SYNTHESIS_PACKAGE_FIELDS = Object.freeze([
  'absentKinds',
  'generation',
  'items',
  'method',
  'provenance',
  'publicContractVersion',
  'region',
  'schemaVersion',
])
const SYNTHESIS_ITEM_FIELDS = Object.freeze(['basis', 'kind', 'statement'])
const SYNTHESIS_ABSENCE_FIELDS = Object.freeze(['kind', 'reasonCode', 'statement'])
const SYNTHESIS_CITATION_FIELDS = Object.freeze([
  'endDisplay',
  'endPeriod',
  'endValue',
  'publicLabel',
  'seriesId',
  'startDisplay',
  'startPeriod',
  'startValue',
])
const SYNTHESIS_OBSERVED_ASSOCIATION_BASIS_FIELDS = Object.freeze([
  'associationId', 'citations', 'seriesIds', 'type', 'window',
])
const SYNTHESIS_OBSERVED_PAIR_BASIS_FIELDS = Object.freeze([
  'citations', 'pairId', 'seriesIds', 'type', 'window',
])
const SYNTHESIS_STATE_POSITION_BASIS_FIELDS = Object.freeze([
  'associationId',
  'flowSeriesId',
  'indicatorLabel',
  'municipalitiesWithData',
  'qualifyingRegionSlugs',
  'referencePeriod',
  'regionalMedian',
  'regionalMedianDisplay',
  'seriesIds',
  'sourceRef',
  'stateMedian',
  'stateMedianDisplay',
  'type',
])
const SYNTHESIS_INVARIANT_BASIS_FIELDS = Object.freeze([
  'anchorRefs',
  'endValue',
  'endValueDisplay',
  'observedDirection',
  'publicLabel',
  'scenarioOrders',
  'seriesIds',
  'startValue',
  'startValueDisplay',
  'type',
  'window',
])

function parseSynthesisDisplay(value, label) {
  invariant(typeof value === 'string' && value.trim() !== '', `${label} deve ser texto não vazio.`)
  const normalized = value.replace(/\u00a0/gu, ' ').trim()
  invariant(
    /^-?(?:\d{1,3}(?: \d{3})+|\d+)(?:,\d+)?$/u.test(normalized),
    `${label} não é uma representação numérica fechada: "${value}".`,
  )
  const parsed = Number(normalized.replace(/ /gu, '').replace(',', '.'))
  invariant(Number.isFinite(parsed), `${label} não representa número finito.`)
  return parsed
}

function synthesisDisplayMatches(value, rawValue, label) {
  const parsed = parseSynthesisDisplay(value, label)
  const normalized = value.replace(/\u00a0/gu, ' ').trim()
  const decimals = normalized.includes(',') ? normalized.split(',')[1].length : 0
  const tolerance = (0.5 * (10 ** -decimals)) + (Number.EPSILON * Math.abs(rawValue) * 2)
  return Math.abs(parsed - rawValue) <= tolerance
}

function synthesisPeriodYear(period, granularity) {
  return granularity === 'monthly' ? Math.floor(period / 100) : period
}

function assertBasisWindow(actual, expected, label) {
  assertExactKeys(actual, ['end', 'start'], label)
  invariant(
    actual.start === expected.start && actual.end === expected.end,
    `${label} diverge da janela da base referenciada.`,
  )
}

function renderResearchObservedStatement(basis) {
  const clauses = basis.citations.map((citation) =>
    `${citation.publicLabel} passou de ${citation.startDisplay} para ${citation.endDisplay}`)
  return `Conclui-se do observado que, entre ${basis.window.start} e ${basis.window.end}, `
    + `${clauses[0]} e, no mesmo período, ${clauses.slice(1).join(' e ')}.`
}

function validateSynthesisCitation({
  citation,
  expectedSeriesKey,
  sourceSeriesByKey,
  publicSeriesById,
  seriesIdByKey,
  labelByKey,
  window,
  label,
}) {
  assertExactKeys(citation, SYNTHESIS_CITATION_FIELDS, label)
  invariant(citation.seriesId === expectedSeriesKey,
    `${label}.seriesId diverge da série da base referenciada.`)
  invariant(citation.publicLabel === labelByKey.get(expectedSeriesKey),
    `${label}.publicLabel diverge do rótulo da série referenciada.`)
  invariant(citation.startPeriod <= citation.endPeriod,
    `${label} declara períodos em ordem inversa.`)
  const sourceSeries = sourceSeriesByKey.get(expectedSeriesKey)
  invariant(sourceSeries !== undefined, `${label} cita série ausente do pacote regional.`)
  const startPoint = sourceSeries.points.find((point) => point.period === citation.startPeriod)
  const endPoint = sourceSeries.points.find((point) => point.period === citation.endPeriod)
  invariant(startPoint !== undefined && endPoint !== undefined,
    `${label} cita borda que não existe na série regional.`)
  invariant(Object.is(startPoint.value, citation.startValue),
    `${label}.startValue diverge da série regional.`)
  invariant(Object.is(endPoint.value, citation.endValue),
    `${label}.endValue diverge da série regional.`)
  invariant(synthesisPeriodYear(citation.startPeriod, sourceSeries.periodGranularity) === window.start,
    `${label}.startPeriod não é a borda inicial da janela.`)
  invariant(synthesisPeriodYear(citation.endPeriod, sourceSeries.periodGranularity) === window.end,
    `${label}.endPeriod não é a borda final da janela.`)
  invariant(synthesisDisplayMatches(
    citation.startDisplay, citation.startValue, `${label}.startDisplay`),
  `${label}.startDisplay não representa startValue.`)
  invariant(synthesisDisplayMatches(
    citation.endDisplay, citation.endValue, `${label}.endDisplay`),
  `${label}.endDisplay não representa endValue.`)

  const publicSeriesId = seriesIdByKey.get(expectedSeriesKey)
  const publicSeries = publicSeriesById.get(publicSeriesId)
  invariant(publicSeries !== undefined, `${label} não resolve na série pública.`)
  invariant(
    publicSeries.points.some((point) =>
      point.period === citation.startPeriod && Object.is(point.value, citation.startValue)),
    `${label}.startValue não reconfere na série pública.`,
  )
  invariant(
    publicSeries.points.some((point) =>
      point.period === citation.endPeriod && Object.is(point.value, citation.endValue)),
    `${label}.endValue não reconfere na série pública.`,
  )
}

function transposeObservedConclusion(item, context, label) {
  const basis = item.basis
  invariant(isRecord(basis), `${label}.basis deve ser um objeto.`)
  let sourceNode
  let publicNode
  let expectedSeriesKeys
  let basisLabel

  if (basis.type === 'association') {
    assertExactKeys(basis, SYNTHESIS_OBSERVED_ASSOCIATION_BASIS_FIELDS, `${label}.basis`)
    sourceNode = context.associationByResearchId.get(basis.associationId)
    publicNode = context.publicAssociationByResearchId.get(basis.associationId)
    invariant(sourceNode !== undefined && publicNode !== undefined,
      `${label}.basis.associationId não resolve no pacote regional.`)
    expectedSeriesKeys = [
      sourceNode.educationOutcome.seriesKey,
      ...sourceNode.territorialFactors.map((factor) => factor.seriesKey),
    ]
    basisLabel = synthesisAssociationBasisLabel(publicNode)
  } else {
    invariant(basis.type === 'temporal_pair', `${label}.basis.type fora do contrato.`)
    assertExactKeys(basis, SYNTHESIS_OBSERVED_PAIR_BASIS_FIELDS, `${label}.basis`)
    sourceNode = context.pairByResearchId.get(basis.pairId)
    publicNode = context.publicPairByResearchId.get(basis.pairId)
    invariant(sourceNode !== undefined && publicNode !== undefined,
      `${label}.basis.pairId não resolve no pacote regional.`)
    expectedSeriesKeys = [sourceNode.seriesKeyA, sourceNode.seriesKeyB]
    basisLabel = synthesisTemporalPairBasisLabel(publicNode)
  }

  assertBasisWindow(basis.window, sourceNode.window, `${label}.basis.window`)
  assertSameArray(basis.seriesIds, expectedSeriesKeys, `${label}.basis.seriesIds`)
  invariant(Array.isArray(basis.citations) && basis.citations.length === expectedSeriesKeys.length,
    `${label}.basis.citations não cobre as séries da base.`)
  basis.citations.forEach((citation, index) => validateSynthesisCitation({
    citation,
    expectedSeriesKey: expectedSeriesKeys[index],
    sourceSeriesByKey: context.sourceSeriesByKey,
    publicSeriesById: context.publicSeriesById,
    seriesIdByKey: context.seriesIdByKey,
    labelByKey: context.labelByKey,
    window: basis.window,
    label: `${label}.basis.citations[${index}]`,
  }))
  invariant(item.statement === renderResearchObservedStatement(basis),
    `${label}.statement não é o template T1 renderizado do basis.`)
  return { kindLabel: SYNTHESIS_KIND_LABELS.observed, statement: item.statement, basisLabel }
}

function transposeStatePositionConclusion(item, context, label) {
  const basis = item.basis
  assertExactKeys(basis, SYNTHESIS_STATE_POSITION_BASIS_FIELDS, `${label}.basis`)
  invariant(basis.type === 'state_position', `${label}.basis.type fora do contrato.`)
  const association = context.publicAssociationByResearchId.get(basis.associationId)
  invariant(association !== undefined, `${label}.basis.associationId não resolve.`)
  invariant(typeof basis.flowSeriesId === 'string' && basis.flowSeriesId !== '',
    `${label}.basis.flowSeriesId deve ser texto não vazio.`)
  assertSameArray(basis.seriesIds, [basis.flowSeriesId], `${label}.basis.seriesIds`)
  invariant(Number.isInteger(basis.referencePeriod),
    `${label}.basis.referencePeriod deve ser inteiro.`)
  invariant(context.synthesisSourcePaths.has(basis.sourceRef),
    `${label}.basis.sourceRef não está entre as fontes sha-verificadas do pacote.`)
  invariant(Number.isInteger(basis.municipalitiesWithData)
    && basis.municipalitiesWithData > 0
    && basis.municipalitiesWithData <= context.registryRegion.municipalityCount,
  `${label}.basis.municipalitiesWithData fora da cobertura regional.`)
  invariant(Array.isArray(basis.qualifyingRegionSlugs)
    && basis.qualifyingRegionSlugs.length > 0
    && new Set(basis.qualifyingRegionSlugs).size === basis.qualifyingRegionSlugs.length,
  `${label}.basis.qualifyingRegionSlugs deve ser lista não vazia e sem repetição.`)
  invariant(basis.qualifyingRegionSlugs.includes(context.registryRegion.slug),
    `${label}.basis.qualifyingRegionSlugs não inclui a própria região.`)
  invariant(synthesisDisplayMatches(
    basis.regionalMedianDisplay, basis.regionalMedian, `${label}.basis.regionalMedianDisplay`),
  `${label}.basis.regionalMedianDisplay não representa regionalMedian.`)
  invariant(synthesisDisplayMatches(
    basis.stateMedianDisplay, basis.stateMedian, `${label}.basis.stateMedianDisplay`),
  `${label}.basis.stateMedianDisplay não representa stateMedian.`)
  const expected = `Conclui-se que a mediana dos municípios da região em ${basis.indicatorLabel} `
    + `está em ${basis.regionalMedianDisplay}, ante a mediana estadual de ${basis.stateMedianDisplay}.`
  invariant(item.statement === expected, `${label}.statement não é o template T2 renderizado do basis.`)
  return {
    kindLabel: SYNTHESIS_KIND_LABELS.state_position,
    statement: item.statement,
    basisLabel: synthesisAssociationBasisLabel(association),
  }
}

function transposeScenarioInvariantConclusion(item, context, label) {
  const basis = item.basis
  assertExactKeys(basis, SYNTHESIS_INVARIANT_BASIS_FIELDS, `${label}.basis`)
  invariant(basis.type === 'scenario_invariant', `${label}.basis.type fora do contrato.`)
  invariant(context.scenarioPackage !== null && context.publicScenarios.status === 'published',
    `${label} traz T3 para região sem cenários publicados.`)
  invariant(Array.isArray(basis.seriesIds) && basis.seriesIds.length === 1,
    `${label}.basis.seriesIds deve identificar uma série.`)
  const researchSeriesId = basis.seriesIds[0]
  const publicSeriesId = context.seriesIdByKey.get(researchSeriesId)
  const publicSeries = context.publicSeriesById.get(publicSeriesId)
  invariant(publicSeries !== undefined, `${label}.basis.seriesIds não resolve na série pública.`)
  invariant(basis.publicLabel === publicSeries.label,
    `${label}.basis.publicLabel diverge da série pública.`)
  assertSameArray(basis.scenarioOrders, [1, 2, 3, 4], `${label}.basis.scenarioOrders`)
  invariant(Array.isArray(basis.anchorRefs) && basis.anchorRefs.length === 4,
    `${label}.basis.anchorRefs deve trazer as quatro ordens.`)
  const publicScenarioByOrder = new Map(
    context.publicScenarios.block.items.map((scenario) => [scenario.order, scenario]),
  )
  const sourceScenarioByOrder = new Map(
    context.scenarioPackage.scenarios.items.map((scenario) => [scenario.order, scenario]),
  )
  basis.anchorRefs.forEach((reference, index) => {
    const refLabel = `${label}.basis.anchorRefs[${index}]`
    assertExactKeys(reference, ['anchorKey', 'scenarioOrder', 'seriesId'], refLabel)
    invariant(reference.scenarioOrder === basis.scenarioOrders[index],
      `${refLabel}.scenarioOrder fora da ordem declarada.`)
    invariant(reference.seriesId === researchSeriesId, `${refLabel}.seriesId diverge de T3.`)
    const sourceAnchor = sourceScenarioByOrder.get(reference.scenarioOrder)?.anchors
      .find((anchor) => anchor.anchorKey === reference.anchorKey)
    invariant(sourceAnchor !== undefined && sourceAnchor.seriesKey === researchSeriesId,
      `${refLabel} não resolve na âncora do cenário de pesquisa.`)
    invariant(sourceAnchor.observedDirection === basis.observedDirection,
      `${refLabel} diverge da direção observada comum.`)
    invariant(sourceAnchor.window.start === basis.window.start
      && sourceAnchor.window.end === basis.window.end
      && Object.is(sourceAnchor.startValue, basis.startValue)
      && Object.is(sourceAnchor.endValue, basis.endValue),
    `${refLabel} diverge da janela ou dos valores comuns.`)
    const publicAnchor = publicScenarioByOrder.get(reference.scenarioOrder)?.anchors
      .find((anchor) => anchor.seriesId === publicSeriesId)
    invariant(publicAnchor !== undefined
      && publicAnchor.window.start === basis.window.start
      && publicAnchor.window.end === basis.window.end
      && Object.is(publicAnchor.startValue, basis.startValue)
      && Object.is(publicAnchor.endValue, basis.endValue)
      && publicAnchor.directionLabel === SCENARIO_DIRECTION_LABELS[basis.observedDirection],
    `${refLabel} não reconfere na âncora pública.`)
  })
  invariant(synthesisDisplayMatches(
    basis.startValueDisplay, basis.startValue, `${label}.basis.startValueDisplay`),
  `${label}.basis.startValueDisplay não representa startValue.`)
  invariant(synthesisDisplayMatches(
    basis.endValueDisplay, basis.endValue, `${label}.basis.endValueDisplay`),
  `${label}.basis.endValueDisplay não representa endValue.`)
  const expected = `Conclui-se que ${basis.publicLabel}, de ${basis.startValueDisplay} para `
    + `${basis.endValueDisplay} entre ${basis.window.start} e ${basis.window.end}, ancora os `
    + 'quatro cenários publicados da região.'
  invariant(item.statement === expected, `${label}.statement não é o template T3 renderizado do basis.`)
  return {
    kindLabel: SYNTHESIS_KIND_LABELS.scenario_invariant,
    statement: item.statement,
    basisLabel: publicSeries.label,
  }
}

export function transposeSynthesis({
  synthesisPackage,
  sourcePackage,
  sourcePackageSha256,
  scenarioPackage,
  scenarioPackageSha256,
  registryRegion,
  publicSeries,
  publicAssociations,
  publicTemporalPairs,
  publicScenarios,
  seriesIdByKey,
  labelByKey,
}) {
  assertExactKeys(synthesisPackage, SYNTHESIS_PACKAGE_FIELDS, 'pacote de conclusões')
  invariant(synthesisPackage.schemaVersion === 'vocacoes-regiao-pesquisa-conclusoes-v0.1',
    `schema do pacote de conclusões desconhecido: "${synthesisPackage.schemaVersion}".`)
  invariant(synthesisPackage.publicContractVersion === VOCACOES_DOCUMENT_SCHEMA,
    'o pacote de conclusões não declara o contrato público implementado.')
  invariant(synthesisPackage.region.slug === registryRegion.slug
    && synthesisPackage.region.name === registryRegion.name
    && synthesisPackage.region.uf === registryRegion.uf
    && synthesisPackage.region.municipalityCount === registryRegion.municipalityCount
    && synthesisPackage.region.registrySha256 === sourcePackage.region.registrySha256,
  `a identidade do pacote de conclusões diverge do registro em "${registryRegion.slug}".`)
  assertExactKeys(
    synthesisPackage.generation,
    ['clockUsed', 'deterministic', 'modelUsed', 'networkUsed'],
    'pacote de conclusões.generation',
  )
  invariant(synthesisPackage.generation.deterministic === true
    && synthesisPackage.generation.clockUsed === false
    && synthesisPackage.generation.modelUsed === false
    && synthesisPackage.generation.networkUsed === false,
  `o pacote de conclusões de "${registryRegion.slug}" não se declara determinístico.`)
  invariant(synthesisPackage.provenance.regionPackageSha256 === sourcePackageSha256,
    `o pacote de conclusões de "${registryRegion.slug}" não referencia o pacote regional lido.`)
  invariant(synthesisPackage.provenance.scenarioPackageSha256 === scenarioPackageSha256,
    `o pacote de conclusões de "${registryRegion.slug}" não referencia o pacote de cenários lido.`)
  invariant(Array.isArray(synthesisPackage.items), 'pacote de conclusões.items deve ser uma lista.')
  invariant(Array.isArray(synthesisPackage.absentKinds),
    'pacote de conclusões.absentKinds deve ser uma lista.')
  invariant(Array.isArray(synthesisPackage.method?.sources),
    'pacote de conclusões.method.sources deve ser uma lista.')

  const context = {
    associationByResearchId: new Map(sourcePackage.associations.map((association) =>
      [association.associationKey, association])),
    publicAssociationByResearchId: new Map(sourcePackage.associations.map((association, index) =>
      [association.associationKey, publicAssociations[index]])),
    pairByResearchId: new Map(sourcePackage.temporalPairs.map((pair) => [pair.pairKey, pair])),
    publicPairByResearchId: new Map(sourcePackage.temporalPairs.map((pair, index) =>
      [pair.pairKey, publicTemporalPairs[index]])),
    sourceSeriesByKey: new Map(sourcePackage.series.map((serie) => [serie.seriesKey, serie])),
    publicSeriesById: new Map(publicSeries.map((serie) => [serie.seriesId, serie])),
    publicScenarios,
    registryRegion,
    scenarioPackage,
    seriesIdByKey,
    synthesisSourcePaths: new Set(synthesisPackage.method.sources.map((source) => source.path)),
    labelByKey,
  }
  const observedResearchBases = new Set()
  const publicItems = synthesisPackage.items.map((item, index) => {
    const label = `pacote de conclusões.items[${index}]`
    assertExactKeys(item, SYNTHESIS_ITEM_FIELDS, label)
    invariant(Object.prototype.hasOwnProperty.call(SYNTHESIS_KIND_LABELS, item.kind),
      `${label}.kind fora do contrato: "${item.kind}".`)
    invariant(typeof item.statement === 'string' && item.statement.trim() !== '',
      `${label}.statement deve ser texto não vazio.`)
    if (item.kind === 'observed') {
      const transposed = transposeObservedConclusion(item, context, label)
      invariant(!observedResearchBases.has(transposed.basisLabel),
        `${label} repete a base observada "${transposed.basisLabel}".`)
      observedResearchBases.add(transposed.basisLabel)
      return transposed
    }
    if (item.kind === 'state_position') {
      return transposeStatePositionConclusion(item, context, label)
    }
    if (item.kind === 'scenario_invariant') {
      return transposeScenarioInvariantConclusion(item, context, label)
    }
    invariant(false,
      `${label} traz agenda da pesquisa; T4 é derivado dos temas emitidos pela plataforma.`)
  })
  invariant(
    observedResearchBases.size === sourcePackage.associations.length + sourcePackage.temporalPairs.length,
    `o pacote de conclusões de "${registryRegion.slug}" não traz um T1 por associação e par.`,
  )

  const seenAbsences = new Set()
  let publicAbsences = synthesisPackage.absentKinds.map((absence, index) => {
    const label = `pacote de conclusões.absentKinds[${index}]`
    assertExactKeys(absence, SYNTHESIS_ABSENCE_FIELDS, label)
    invariant(absence.kind === 'scenario_invariant' || absence.kind === 'agenda',
      `${label}.kind não admite ausência declarada.`)
    invariant(!seenAbsences.has(absence.kind), `${label}.kind repetido.`)
    invariant(typeof absence.reasonCode === 'string' && absence.reasonCode !== '',
      `${label}.reasonCode deve ser texto não vazio.`)
    invariant(typeof absence.statement === 'string' && absence.statement !== '',
      `${label}.statement deve ser texto não vazio.`)
    seenAbsences.add(absence.kind)
    return { kindLabel: SYNTHESIS_KIND_LABELS[absence.kind], statement: absence.statement }
  })

  const commonThemes = commonScenarioAgendaThemes(publicScenarios)
  if (commonThemes.length > 0) {
    invariant(seenAbsences.has('agenda'),
      `o pacote de conclusões de "${registryRegion.slug}" não traz a ausência T4 a substituir.`)
    publicAbsences = publicAbsences.filter((absence) =>
      absence.kindLabel !== SYNTHESIS_KIND_LABELS.agenda)
    publicItems.push({
      kindLabel: SYNTHESIS_KIND_LABELS.agenda,
      statement: renderAgendaSynthesis(commonThemes),
    })
  }

  return {
    ...SYNTHESIS_FRAMING,
    items: publicItems,
    absentKinds: publicAbsences,
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
  scenarioPackage = null,
  scenarioPackageSha256 = null,
  municipalPackage = null,
  municipalPackageSha256 = null,
  synthesisPackage,
  synthesisPackageSha256,
  researchContract,
  guard,
}) {
  invariant(
    sourcePackage.packageStatus === 'complete',
    `o pacote da região "${registryRegion.slug}" está em "${sourcePackage.packageStatus}", `
    + 'e a Fase A só publica pacote completo.',
  )
  /*
   * O pacote da Fase A nunca traz cenários — é o pacote de cenários que os
   * traz. Um pacote da Fase A que passasse a trazê-los publicaria um Bloco 4
   * que ninguém promoveu, por um caminho que ninguém confere.
   */
  invariant(
    sourcePackage.scenarios === null,
    `o pacote da Fase A da região "${registryRegion.slug}" traz cenários; eles vêm do pacote `
    + 'promovido em pacotes/cenarios/, não daqui.',
  )
  if (scenarioPackage !== null) {
    invariant(
      scenarioPackage.scenarios !== null,
      `o pacote de cenários da região "${registryRegion.slug}" não traz o bloco de cenários.`,
    )
    /*
     * A garantia que dá nome à rodada: publicar cenário não reescreve o retrato.
     * Ela é conferida aqui, byte a byte na forma canônica, e não prometida no
     * relatório — os dois pacotes precisam concordar em tudo o que não é o
     * Bloco 4.
     */
    for (const block of SHARED_BLOCKS) {
      invariant(
        JSON.stringify(canonicalize(scenarioPackage[block]))
          === JSON.stringify(canonicalize(sourcePackage[block])),
        `o pacote de cenários da região "${registryRegion.slug}" altera o bloco "${block}" do `
        + 'pacote da Fase A; a publicação dos cenários é aditiva.',
      )
    }
    invariant(
      scenarioPackage.packageStatus === 'complete',
      `o pacote de cenários da região "${registryRegion.slug}" não está completo.`,
    )
    invariant(
      scenarioPackage.generation.deterministic === true
        && scenarioPackage.generation.networkUsed === false
        && scenarioPackage.generation.clockUsed === false
        && scenarioPackage.generation.modelUsed === false,
      `o pacote de cenários da região "${registryRegion.slug}" não se declara determinístico.`,
    )
    /*
     * A camada municipal é obrigatória onde há cenário (sucessora da D11). Ela
     * é conferida com o mesmo rigor do pacote de cenários: completa,
     * determinística, e da mesma região — uma camada de outra região no lugar
     * publicaria municípios que não são os desta.
     */
    invariant(
      municipalPackage !== null,
      `a região "${registryRegion.slug}" publica cenário mas não traz a camada municipal.`,
    )
    invariant(
      municipalPackage.packageStatus === 'complete',
      `a camada municipal da região "${registryRegion.slug}" não está completa.`,
    )
    invariant(
      municipalPackage.generation.deterministic === true
        && municipalPackage.generation.networkUsed === false
        && municipalPackage.generation.clockUsed === false
        && municipalPackage.generation.modelUsed === false,
      `a camada municipal da região "${registryRegion.slug}" não se declara determinística.`,
    )
    invariant(
      municipalPackage.region.slug === registryRegion.slug
        && municipalPackage.region.name === registryRegion.name
        && municipalPackage.region.uf === registryRegion.uf
        && municipalPackage.region.municipalityCount === registryRegion.municipalityCount,
      `a identidade da camada municipal diverge do registro em "${registryRegion.slug}".`,
    )
    invariant(
      municipalPackage.municipalities.length === registryRegion.municipalityCount,
      `a camada municipal de "${registryRegion.slug}" traz ${municipalPackage.municipalities.length} `
      + `municípios, e o registro declara ${registryRegion.municipalityCount}.`,
    )

    /*
     * Contagem igual não prova cobertura: um município poderia sair e outro,
     * de fora da região, entrar sem alterar 23/133. O código IBGE textual é a
     * identidade canônica; por isso a fronteira de publicação reconfere o
     * conjunto exato e o nome de apresentação contra o registro territorial.
     */
    const registryMunicipalityById = new Map(
      registryRegion.municipalities.map((municipality) => [municipality.ibge7, municipality.name]),
    )
    const municipalPackageIds = new Set()
    municipalPackage.municipalities.forEach((municipality, index) => {
      invariant(
        registryMunicipalityById.has(municipality.ibge7),
        `a camada municipal de "${registryRegion.slug}" traz o código IBGE `
        + `"${municipality.ibge7}" fora do registro da região.`,
      )
      invariant(
        registryMunicipalityById.get(municipality.ibge7) === municipality.name,
        `a camada municipal de "${registryRegion.slug}" diverge do nome canônico do `
        + `município ${municipality.ibge7}.`,
      )
      invariant(
        !municipalPackageIds.has(municipality.ibge7),
        `a camada municipal de "${registryRegion.slug}" repete o código IBGE `
        + `"${municipality.ibge7}" no item ${index}.`,
      )
      municipalPackageIds.add(municipality.ibge7)
    })
    invariant(
      municipalPackageIds.size === registryMunicipalityById.size,
      `a camada municipal de "${registryRegion.slug}" não cobre exatamente o conjunto `
      + 'de códigos IBGE do registro da região.',
    )
  }
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
  const publishesScenarios = scenarioPackage !== null
  const associations = sourcePackage.associations.map((association) =>
    transposeAssociation(association, seriesIdByKey))
  const temporalPairs = sourcePackage.temporalPairs.map((pair) =>
    transposeTemporalPair(pair, seriesIdByKey, labelByKey))
  const scenarios = publishesScenarios
    ? {
      label: SCENARIO_FRAMING.label,
      description: SCENARIO_FRAMING.publishedDescription,
      statuteReadingNote: SCENARIO_FRAMING.statuteReadingNote,
      status: 'published',
      absenceStatement: null,
      block: transposeScenarioBlock(
        scenarioPackage.scenarios,
        seriesIdByKey,
        labelByKey,
        registryRegion.slug,
        municipalPackage,
      ),
    }
    : {
      label: SCENARIO_FRAMING.label,
      description: SCENARIO_FRAMING.absentDescription,
      statuteReadingNote: null,
      status: 'absent',
      absenceStatement: SCENARIO_FRAMING.absenceStatement,
      block: null,
    }
  const synthesis = transposeSynthesis({
    synthesisPackage,
    sourcePackage,
    sourcePackageSha256,
    scenarioPackage,
    scenarioPackageSha256,
    registryRegion,
    publicSeries: series,
    publicAssociations: associations,
    publicTemporalPairs: temporalPairs,
    publicScenarios: scenarios,
    seriesIdByKey,
    labelByKey,
  })

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
    synthesis,
    territoryPortrait: { ...framing.territoryPortrait, series },
    associations: {
      ...framing.associations,
      items: associations,
    },
    temporalPairs: {
      ...framing.temporalPairs,
      items: temporalPairs,
    },
    scenarios,
    sources: { ...framing.sources, items: buildSources(series) },
    limitations: {
      /*
       * As limitações vêm do pacote que de fato foi publicado. Onde há cenário,
       * é o pacote de cenários que declara os limites que os cenários criam — e
       * publicar o bloco sem eles seria publicar o cenário sem a ressalva que o
       * torna honesto.
       */
      ...framing.limitations,
      items: (publishesScenarios ? scenarioPackage : sourcePackage).limitations.map(
        (limitation) => limitation.statement,
      ),
    },
    provenance: {
      sourcePackageSha256,
      sourceContractVersion: sourcePackage.contractVersion,
      sourceBuilderVersion: sourcePackage.provenance.builderVersion,
      sourceGeneratedAt: sourcePackage.provenance.generatedAt,
      registrySha256: sourcePackage.region.registrySha256,
      scenarioPackageSha256: publishesScenarios ? scenarioPackageSha256 : null,
      scenarioSourceSha256: publishesScenarios
        ? scenarioPackage.provenance.scenarioSourceSha256
        : null,
      municipalPackageSha256: publishesScenarios ? municipalPackageSha256 : null,
      synthesisPackageSha256,
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
  const verifiedApproval = verified.readVerifiedJson(PUBLIC_CONTRACT_APPROVAL_FILE)
  invariant(
    JSON.stringify(canonicalize(verifiedApproval)) === JSON.stringify(canonicalize(source.approval)),
    'o contrato público lido no handshake diverge do contrato sha-verificado pelo manifesto.',
  )
  const researchContract = verified.readVerifiedJson(RESEARCH_CONTRACT_FILE)
  invariant(
    researchContract.contractVersion === verified.manifest.contractVersion.replace(/^.*-/u, '')
      || verified.manifest.contractVersion.endsWith(researchContract.contractVersion),
    'a versão do contrato de pesquisa diverge do manifesto da origem.',
  )
  /*
   * O contrato da pesquisa precisa **prever** o Bloco 4 para que o gerador o
   * publique. Enquanto ele dizia `absent_in_v0_1`, publicar cenário aqui seria
   * a plataforma inventando um bloco que a origem não reconhece.
   */
  invariant(
    researchContract.blocks.block4RegionalScenarios === 'optional_in_v0_2',
    `o contrato da pesquisa declara o bloco de cenários como `
    + `"${researchContract.blocks.block4RegionalScenarios}", e esta versão do gerador publica `
    + 'a partir de "optional_in_v0_2".',
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
  validateSynthesisApproval(verifiedApproval, registry)

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

    /*
     * O pacote de cenários existe só nas regiões da Fase B, e a pergunta «existe?»
     * é feita ao **manifesto da origem**, não ao sistema de arquivos: um arquivo
     * que aparecesse no disco sem constar do manifesto seria publicado sem
     * ninguém ter conferido o resumo dele.
     */
    const scenarioRelative = SCENARIO_PACKAGE_PATTERN.replace('{regionSlug}', registryRegion.slug)
    const hasScenarios = verified.declares(scenarioRelative)
    const scenarioPackage = hasScenarios ? verified.readVerifiedJson(scenarioRelative) : null
    const scenarioPackageSha256 = hasScenarios ? verified.sha256Of(scenarioRelative) : null

    /*
     * A camada municipal (sucessora da D11) acompanha o cenário: onde há um, há a
     * outra, e a mesma pergunta «existe?» é feita ao manifesto, nunca ao disco.
     */
    const municipalRelative = MUNICIPAL_LAYER_PACKAGE_PATTERN.replace(
      '{regionSlug}', registryRegion.slug)
    const hasMunicipal = verified.declares(municipalRelative)
    invariant(
      hasScenarios === hasMunicipal,
      `a região "${registryRegion.slug}" declara cenário e camada municipal em desacordo `
      + `(cenário: ${hasScenarios}, camada: ${hasMunicipal}).`,
    )
    const municipalPackage = hasMunicipal ? verified.readVerifiedJson(municipalRelative) : null
    const municipalPackageSha256 = hasMunicipal ? verified.sha256Of(municipalRelative) : null

    /*
     * A síntese é obrigatória nas dez regiões. Diferentemente dos cenários, a
     * ausência do pacote não representa cobertura parcial: representa uma
     * quebra do contrato 2.5.0 e encerra a publicação.
     */
    const synthesisRelative = SYNTHESIS_LAYER_PACKAGE_PATTERN.replace(
      '{regionSlug}', registryRegion.slug)
    invariant(
      verified.declares(synthesisRelative),
      `o manifesto da origem não declara o pacote de conclusões "${synthesisRelative}".`,
    )
    const synthesisPackage = verified.readVerifiedJson(synthesisRelative)
    const synthesisPackageSha256 = verified.sha256Of(synthesisRelative)

    const document = transposeRegion({
      registryRegion,
      sourcePackage,
      sourcePackageSha256: verified.sha256Of(relative),
      scenarioPackage,
      scenarioPackageSha256,
      municipalPackage,
      municipalPackageSha256,
      synthesisPackage,
      synthesisPackageSha256,
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
      /*
       * A ausência de cenário é contável no manifesto, e não só legível dentro
       * do documento. Sem estas duas linhas, saber quais regiões têm cenário
       * exigiria abrir os dez arquivos — e uma região que perdesse o bloco pelo
       * caminho seria indistinguível de uma região que nunca o teve.
       */
      scenarioStatus: document.scenarios.status,
      scenarioCount: document.scenarios.block === null ? 0 : document.scenarios.block.items.length,
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

/*
 * O `schema.json` da família — um arquivo público que declara, em linguagem que
 * não é código, o que esta família garante ao leitor.
 *
 * Ele carrega a regra que distingue esta família (decisão `D3` do plano): os
 * quatro cenários de uma região **não têm o mesmo peso** — três são
 * exploratórios e um é normativo, e o estatuto de cada um é campo obrigatório do
 * documento. A regra é declarada aqui, ao lado do dado, porque é a diferença
 * que um leitor precisa ver escrita e não subentendida. Até a Rodada 1 do V2 o
 * schema também nomeava a família dos cenários municipais como aquela cuja
 * regra de peso igual «não valia aqui»; essa família foi removida da plataforma
 * (D11), e a regra passou a ser declarada como única desta família, sem apontar
 * para o que não existe mais.
 */
export function buildFamilySchema(manifest) {
  const withScenarios = manifest.regions
    .filter((entry) => entry.scenarioStatus === 'published')
    .map((entry) => entry.slug)
  const withoutScenarios = manifest.regions
    .filter((entry) => entry.scenarioStatus === 'absent')
    .map((entry) => entry.slug)

  return {
    $schema: 'https://json-schema.org/draft/2020-12/schema',
    $id: 'https://painel.pne/data/vocacoes-regiao/schema.json',
    title: 'Vocações da Região — contrato público',
    description:
      'Projeção pública do retrato regional, da leitura entre educação e território, das '
      + 'transformações simultâneas, dos cenários e das conclusões da região. Contém apenas os campos que a '
      + 'interface renderiza.',
    documentSchemaVersion: manifest.documentSchemaVersion,
    manifestSchemaVersion: manifest.schemaVersion,
    publicationScope: manifest.publicationScope,
    referenceYear: manifest.referenceYear,
    blocks: [
      'retrato-e-transformacoes-do-territorio',
      'educacao-e-territorio-lado-a-lado',
      'transformacoes-simultaneas',
      'cenarios-da-regiao',
      'o-que-se-conclui',
    ],
    scenarioStatutes: {
      exploratory: SCENARIO_STATUTE_LABELS.exploratory,
      normative: SCENARIO_STATUTE_LABELS.normative,
    },
    scenarioCoverage: {
      regionsWithScenarios: withScenarios,
      regionsWithoutScenarios: withoutScenarios,
      scenariosPerRegion: 4,
      absenceIsDeclared: true,
    },
    rules: [
      'Somente as regiões listadas no manifesto têm documento publicado.',
      'Nenhum identificador interno, enum de processo ou resumo criptográfico aparece em texto '
      + 'renderizado.',
      'Nenhuma leitura desta família afirma causa. Cada uma declara, ela mesma, a interpretação '
      + 'que permite e a que proíbe.',
      'Nenhum valor numérico é atribuído a ano posterior ao ano de referência. O horizonte dos '
      + 'cenários é declarado como horizonte, e nenhuma quantidade é atribuída a ele.',
      'Os quatro cenários de uma região não têm o mesmo peso: três são exploratórios e um é '
      + 'normativo, e o estatuto de cada um é campo obrigatório do documento.',
      'O cenário normativo descreve um ideal técnico provisório. Não é previsão, não é '
      + 'compromisso e não foi pactuado.',
      'Todo valor citado por um cenário é reconferido contra a série publicada no mesmo '
      + 'documento, no mesmo ano.',
      'Região sem cenários publica o bloco declarando a ausência, com a frase que o leitor lê — '
      + 'nunca um bloco vazio.',
      'Toda região publica a camada de conclusões. Os tipos são rótulos públicos fechados; T1 '
      + 'reconfere associações e pares, T3 reconfere as quatro âncoras e T4 usa somente a '
      + 'interseção dos temas presentes nos quatro cenários do documento.',
    ],
  }
}

function writeStagedFile(targetUrl, contents, runId) {
  const target = fileURLToPath(targetUrl)
  fs.mkdirSync(path.dirname(target), { recursive: true })
  const temporary = `${target}.tmp-${runId}`
  invariant(!fs.existsSync(temporary), `o staging já existe: ${temporary}.`)
  const descriptor = fs.openSync(temporary, 'wx')
  try {
    fs.writeFileSync(descriptor, contents, 'utf8')
    fs.fsyncSync(descriptor)
  } finally {
    fs.closeSync(descriptor)
  }
  return { target, temporary }
}

function promoteOutputsTransactional(outputs, stale) {
  const runId = `${process.pid}`
  const staged = []
  const journal = []
  try {
    /* Todo o lote vai a staging antes da primeira troca pública. */
    for (const output of outputs) staged.push(writeStagedFile(output.url, output.contents, runId))

    for (const entry of staged) {
      const current = fs.existsSync(entry.target) ? fs.readFileSync(entry.target) : null
      const candidate = fs.readFileSync(entry.temporary)
      if (current !== null && current.equals(candidate)) {
        fs.rmSync(entry.temporary)
        continue
      }
      const backup = `${entry.target}.bak-${runId}`
      invariant(!fs.existsSync(backup), `o backup transacional já existe: ${backup}.`)
      const event = { target: entry.target, backup, originalMoved: false, promoted: false }
      journal.push(event)
      if (fs.existsSync(entry.target)) {
        fs.renameSync(entry.target, backup)
        event.originalMoved = true
      }
      fs.renameSync(entry.temporary, entry.target)
      event.promoted = true
    }

    for (const orphan of stale) {
      const backup = `${orphan}.bak-${runId}`
      invariant(!fs.existsSync(backup), `o backup transacional já existe: ${backup}.`)
      const event = { target: orphan, backup, originalMoved: false, promoted: false }
      journal.push(event)
      fs.renameSync(orphan, backup)
      event.originalMoved = true
    }

    for (const event of journal) {
      if (event.originalMoved && fs.existsSync(event.backup)) fs.rmSync(event.backup)
    }
  } catch (error) {
    for (const event of [...journal].reverse()) {
      try {
        if (event.promoted && fs.existsSync(event.target)) fs.rmSync(event.target)
        if (event.originalMoved && fs.existsSync(event.backup)) {
          fs.renameSync(event.backup, event.target)
        }
      } catch (rollbackError) {
        error.message += ` Rollback falhou em ${event.target}: ${rollbackError.message}`
      }
    }
    for (const entry of staged) {
      if (fs.existsSync(entry.temporary)) fs.rmSync(entry.temporary)
    }
    throw error
  }
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
    {
      contents: `${JSON.stringify(buildFamilySchema(publication.manifest), null, 2)}\n`,
      url: new URL('schema.json', OUTPUT_ROOT),
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

  promoteOutputsTransactional(outputs, stale)

  if (publication.available) {
    const totals = publication.manifest.regions.reduce(
      (accumulator, entry) => ({
        series: accumulator.series + entry.seriesCount,
        associations: accumulator.associations + entry.associationCount,
        pairs: accumulator.pairs + entry.temporalPairCount,
        scenarios: accumulator.scenarios + entry.scenarioCount,
        withScenarios: accumulator.withScenarios + (entry.scenarioStatus === 'published' ? 1 : 0),
      }),
      { series: 0, associations: 0, pairs: 0, scenarios: 0, withScenarios: 0 },
    )
    process.stdout.write(
      `Vocações da Região: ${publication.manifest.regions.length} regiões publicadas — `
      + `${totals.series} séries, ${totals.associations} associações, ${totals.pairs} pares `
      + `temporais, ${totals.scenarios} cenários em ${totals.withScenarios} regiões, a partir de `
      + `${publication.origin}.\n`,
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
