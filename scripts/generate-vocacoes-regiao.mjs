/*
 * Publica o Vocações da Região em `public/data/vocacoes-regiao/`.
 *
 * O gerador atravessa a fronteira uma vez, em tempo de publicação: lê o pacote
 * regional aprovado na camada de pesquisa, reconfere o resumo de cada arquivo
 * contra o manifesto da origem, transpõe para o contrato público
 * `vocacoes-regiao-2.9.0` e escreve. Depois disso a plataforma não sabe mais
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
  ASSOCIATIVE_GRAMMAR_VERSION,
  ASSOCIATIVE_METHOD_NOTE,
  DECOMPOSITION_CRITERIA,
  DECOMPOSITION_EMPLOYMENT_SOURCE_LABEL,
  DECOMPOSITION_FRAMING,
  DECOMPOSITION_REASON_CODES,
  DECOMPOSITION_STAGE_CONFIG,
  DECOMPOSITION_STAGES,
  EDITORIAL_CRITERIA_STATEMENT,
  EDITORIAL_READING_CRITERIA,
  E2_EMPLOYMENT_METHOD_STATEMENT,
  E2_ENROLLMENT_METHOD_STATEMENT,
  EVIDENCE_CLASS_LABELS,
  MUNICIPAL_KIND_LABELS,
  PROHIBITED_CLAIM_OPENER,
  PNE_SERIES_THEME_MAP,
  SCENARIO_FRAMING,
  SCENARIO_DIRECTION_LABELS,
  SCENARIO_STATUTES,
  SCENARIO_STATUTE_LABELS,
  SYNTHESIS_FRAMING,
  SYNTHESIS_KIND_LABELS,
  SYNTHESIS_REQUIRED_OPENERS,
  SCREENED_ORIGIN_STATEMENT,
  SCREENED_RELATIONS_CRITERIA,
  SCREENING_EXCLUDED_SERIES_IDS,
  UNIVERSE_LABELS,
  VOCACOES_DOCUMENT_SCHEMA,
  commonScenarioAgendaThemes,
  computeComovement,
  computeDirectionConcordance,
  computePearsonDelta,
  computeSpearmanDelta,
  correlationStrength,
  createVocacoesDocumentParser,
  formatDecimalComma,
  formatPublicNumber,
  renderAgendaSynthesis,
  renderComovementStatement,
  renderConcordanceStatement,
  renderContrastStatement,
  renderCorrelationStatement,
  renderEditorialNoteStatement,
  renderE2AbsenceStatement,
  renderE2EmploymentStatement,
  renderE2EnrollmentStatement,
  renderLaggedStatement,
  roundHalfAwayFromZero,
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

/*
 * Changelog do gerador: v7 → v8 acompanha o contrato público 2.8.0 → 2.9.0.
 * V5 R3: hero + títulos-história; aditivo. Nenhum campo 2.8.0 é removido ou
 * reinterpretado; os novos valores e statements nascem das séries públicas.
 */
export const VOCACOES_GENERATOR_VERSION = 'vocacoes-regiao-generator-v8'
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
export const RESEARCH_CONTRACT_FILE = 'contrato/contrato_vocacoes_regiao_pesquisa_v0_6.json'
export const REGISTRY_FILE = 'registro/registro_regioes_rs_v0_1.json'

export const RESEARCH_CONTRACT_VERSION = 'vocacoes-regiao-pesquisa-v0.6'
export const RESEARCH_ROUND = 'v5-rodada-03'
export const ASSOCIATIVE_PACKAGE_SCHEMA = 'vocacoes-regiao-pesquisa-associativo-v0.3'
export const EDITORIAL_PACKAGE_SCHEMA = 'vocacoes-regiao-pesquisa-associativo-v0.2'

const T_HERO_TITLE = 'O território mudou de perfil. A educação da região está acompanhando?'
const T_HERO_LEDE =
  'Duas perguntas organizam esta página: o que anda junto com a educação no território — e o '
  + 'que o futuro do território pede da educação. As respostas vêm de séries longas de emprego, '
  + 'demografia e matrícula, lidas lado a lado. Nenhuma leitura afirma causa além do grau '
  + 'declarado em cada cartão.'
const T_HERO_METHOD =
  'Os quatro números-síntese usam as mesmas séries do retrato do território: o valor mais '
  + 'recente fechado de cada série, a variação desde o primeiro ano fechado e, quando a leitura '
  + 'existe no pacote, a posição da região entre as 10 do estado. Prévia não entra no '
  + 'número-síntese.'

const T_TILE_VALUE = '{endValue} {unidadeCurta} · {endYear}'
const T_TILE_DELTA_PERCENTUAL = '{sinal}{pct}% desde {startYear}'
const T_TILE_DELTA_NIVEL = 'eram {startValue} em {startYear}'

const HERO_TILE_CONFIG = Object.freeze([
  Object.freeze({
    tileId: 'ensino-medio',
    seriesId: 'matriculas-no-ensino-medio',
    entity: 'education',
    label: 'Ensino médio',
    shortUnit: 'matrículas',
    deltaKind: 'percentual',
  }),
  Object.freeze({
    tileId: 'educacao-tecnica',
    seriesId: 'matriculas-na-educacao-profissional-tecnica',
    entity: 'education',
    label: 'Educação técnica',
    shortUnit: 'matrículas',
    deltaKind: 'percentual',
  }),
  Object.freeze({
    tileId: 'escolaridade-do-emprego',
    seriesId: 'vinculos-formais-de-pessoas-com-ensino-medio-completo-por-cem-vinculos-formais',
    entity: 'territory',
    label: 'Escolaridade do emprego',
    shortUnit: 'de cada 100 vínculos com ensino médio completo',
    deltaKind: 'nivel',
  }),
  Object.freeze({
    tileId: 'nascimentos',
    seriesId: 'nascidos-vivos-por-residencia-da-mae',
    entity: 'territory',
    label: 'Nascimentos',
    shortUnit: 'nascidos vivos',
    deltaKind: 'nivel',
  }),
])

const T_TITLE_DEF = 'O que nasce hoje chega à escola {lagYears} anos depois'
const T_TITLE_DUO =
  '{Short(primeira)} {verbo(primeira)}, {short(segunda)} {verbo(segunda)}'

const TITLE_VERBS = Object.freeze({
  positive: Object.freeze({ s: 'cresceu', p: 'cresceram' }),
  negative: Object.freeze({ s: 'caiu', p: 'caíram' }),
  zero: Object.freeze({ s: 'não saiu do lugar', p: 'não saíram do lugar' }),
})

const SHORT_LABELS = Object.freeze({
  'escolas-com-matriculas-na-educacao-basica': Object.freeze({ short: 'as escolas com matrícula', number: 'plural' }),
  'escolas-rurais-com-matriculas-na-educacao-basica': Object.freeze({ short: 'as escolas rurais', number: 'plural' }),
  'familias-inscritas-no-cadastro-social-posicao-de-dezembro': Object.freeze({ short: 'as famílias no cadastro social', number: 'plural' }),
  'massa-salarial-de-dezembro-a-precos-de-2025': Object.freeze({ short: 'a massa salarial', number: 'singular' }),
  'matriculas-na-educacao-de-jovens-e-adultos': Object.freeze({ short: 'a matrícula na EJA', number: 'singular' }),
  'matriculas-na-educacao-infantil': Object.freeze({ short: 'a matrícula na educação infantil', number: 'singular' }),
  'matriculas-na-educacao-profissional-tecnica': Object.freeze({ short: 'a matrícula técnica', number: 'singular' }),
  'matriculas-no-ensino-fundamental': Object.freeze({ short: 'a matrícula no fundamental', number: 'singular' }),
  'matriculas-no-ensino-medio': Object.freeze({ short: 'a matrícula no ensino médio', number: 'singular' }),
  'nascidos-vivos-por-residencia-da-mae': Object.freeze({ short: 'os nascimentos', number: 'plural' }),
  'pessoas-de-60-anos-ou-mais-por-cem-pessoas-de-0-a-14-anos': Object.freeze({ short: 'o índice de envelhecimento', number: 'singular' }),
  'pessoas-inscritas-no-perfil-de-baixa-renda-posicao-de-dezembro': Object.freeze({ short: 'as pessoas no perfil de baixa renda', number: 'plural' }),
  'populacao-de-0-a-14-anos': Object.freeze({ short: 'a população de 0 a 14 anos', number: 'singular' }),
  'populacao-de-60-anos-ou-mais': Object.freeze({ short: 'a população de 60 anos ou mais', number: 'singular' }),
  'populacao-estimada': Object.freeze({ short: 'a população estimada', number: 'singular' }),
  'produto-interno-bruto-da-agropecuaria-a-precos-de-2023': Object.freeze({ short: 'o PIB da agropecuária', number: 'singular' }),
  'produto-interno-bruto-da-industria-a-precos-de-2023': Object.freeze({ short: 'o PIB da indústria', number: 'singular' }),
  'produto-interno-bruto-dos-servicos-a-precos-de-2023': Object.freeze({ short: 'o PIB de serviços', number: 'singular' }),
  'vinculos-formais-ativos': Object.freeze({ short: 'o emprego formal', number: 'singular' }),
  'vinculos-formais-de-pessoas-com-ensino-medio-completo-por-cem-vinculos-formais': Object.freeze({ short: 'a fatia de vínculos com ensino médio completo', number: 'singular' }),
  'vinculos-formais-de-pessoas-com-ensino-superior-completo': Object.freeze({ short: 'os vínculos com ensino superior', number: 'plural' }),
  'vinculos-formais-de-profissionais-do-ensino': Object.freeze({ short: 'os vínculos de profissionais do ensino', number: 'plural' }),
  'vinculos-formais-na-industria': Object.freeze({ short: 'o emprego na indústria', number: 'singular' }),
})

const DECOMPOSITION_SOURCE_CONFIG = Object.freeze({
  educacao_infantil: Object.freeze({
    outcomeSeriesKey: 'matriculas_educacao_infantil',
    cohortSeriesKey: 'nascidos_vivos_residencia_mae',
  }),
  ensino_fundamental: Object.freeze({
    outcomeSeriesKey: 'matriculas_ensino_fundamental',
    cohortSeriesKey: 'nascidos_vivos_residencia_mae',
  }),
  ensino_medio: Object.freeze({
    outcomeSeriesKey: 'matriculas_ensino_medio',
    cohortSeriesKey: 'nascidos_vivos_residencia_mae',
  }),
})

const RESEARCH_STAGES_WITHOUT_COHORT = Object.freeze([
  'matriculas_educacao_jovens_adultos',
  'matriculas_educacao_profissional',
])

const RESEARCH_DECOMPOSITION_CRITERIA = Object.freeze({
  cohortAges: DECOMPOSITION_CRITERIA.cohortAges,
  stagesWithoutCohort: RESEARCH_STAGES_WITHOUT_COHORT,
  minIntervals: DECOMPOSITION_CRITERIA.minIntervals,
  sectors: DECOMPOSITION_CRITERIA.sectors,
  reference: DECOMPOSITION_CRITERIA.reference,
  rounding: DECOMPOSITION_CRITERIA.rounding,
  closureToleranceAbs: DECOMPOSITION_CRITERIA.closureToleranceAbs,
})

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

/** Pacote obrigatório da leitura associativa quantificada da Rodada 1 do V3. */
export const ASSOCIATIVE_LAYER_PACKAGE_PATTERN = 'pacotes/associativo/{regionSlug}.json'

export const SCREENED_RELATIONS_FRAMING = Object.freeze({
  label: 'Relações observadas por triagem',
  description:
    'Relações adicionais entre séries observadas que atendem aos critérios declarados; a '
    + 'triagem descreve movimento conjunto e não afirma causa.',
})

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

function validateAssociativeApproval(approval, registry) {
  const layer = approval.associativeReadingLayer
  invariant(isRecord(layer), 'o contrato público 2.7.0 não declara associativeReadingLayer.')
  const expectedRegions = registry.regions
    .map((region) => region.slug)
    .sort((left, right) => left.localeCompare(right, 'en'))
  assertSameArray(layer.regions, expectedRegions, 'associativeReadingLayer.regions')
  invariant(
    layer.packagePattern === ASSOCIATIVE_LAYER_PACKAGE_PATTERN,
    `associativeReadingLayer.packagePattern deve ser "${ASSOCIATIVE_LAYER_PACKAGE_PATTERN}".`,
  )
  invariant(
    layer.schemaVersion === 'vocacoes-regiao-pesquisa-associativo-v0.1',
    `associativeReadingLayer.schemaVersion desconhecida: "${layer.schemaVersion}".`,
  )
  invariant(
    layer.grammarVersion === ASSOCIATIVE_GRAMMAR_VERSION,
    `associativeReadingLayer.grammarVersion deve ser "${ASSOCIATIVE_GRAMMAR_VERSION}".`,
  )
  for (const field of [
    'requiredInAssociations',
    'requiredInTemporalPairs',
    'laggedItemsRequired',
    'screenedRelationsRequired',
  ]) {
    invariant(layer[field] === true, `associativeReadingLayer.${field} deve ser true.`)
  }
  return layer
}

function validateEditorialLayer(layer, label) {
  invariant(isRecord(layer), `${label} não declara editorialLayer.`)
  assertExactKeys(layer, [
    'saliences',
    'leadStrengths',
    'structuralAlwaysLead',
    'gradeEnum',
    'screeningCriteria',
    'associativeSchemaVersion',
  ], `${label}.editorialLayer`)
  assertSameArray(layer.saliences, ['lead', 'note'], `${label}.editorialLayer.saliences`)
  assertSameArray(
    layer.leadStrengths,
    EDITORIAL_READING_CRITERIA.leadStrengths,
    `${label}.editorialLayer.leadStrengths`,
  )
  invariant(
    layer.structuralAlwaysLead === EDITORIAL_READING_CRITERIA.structuralAlwaysLead,
    `${label}.editorialLayer.structuralAlwaysLead diverge do contrato público.`,
  )
  assertSameArray(
    layer.gradeEnum,
    EDITORIAL_READING_CRITERIA.gradeEnum,
    `${label}.editorialLayer.gradeEnum`,
  )
  invariant(
    layer.associativeSchemaVersion === EDITORIAL_PACKAGE_SCHEMA,
    `${label}.editorialLayer.associativeSchemaVersion deve ser "${EDITORIAL_PACKAGE_SCHEMA}".`,
  )
  assertExactKeys(layer.screeningCriteria, [
    'minIntervals',
    'minAbsPearson',
    'maxItems',
    'excludedSeries',
  ], `${label}.editorialLayer.screeningCriteria`)
  for (const [field, expected] of Object.entries(SCREENED_RELATIONS_CRITERIA)) {
    invariant(
      layer.screeningCriteria[field] === expected,
      `${label}.editorialLayer.screeningCriteria.${field} diverge do contrato público.`,
    )
  }
  invariant(
    Array.isArray(layer.screeningCriteria.excludedSeries)
      && layer.screeningCriteria.excludedSeries.length === SCREENING_EXCLUDED_SERIES_IDS.length,
    `${label}.editorialLayer.screeningCriteria.excludedSeries deve declarar as 13 exclusões.`,
  )
  const ordered = [...layer.screeningCriteria.excludedSeries].sort()
  assertSameArray(
    layer.screeningCriteria.excludedSeries,
    ordered,
    `${label}.editorialLayer.screeningCriteria.excludedSeries`,
  )
  invariant(
    new Set(ordered).size === ordered.length,
    `${label}.editorialLayer.screeningCriteria.excludedSeries repete série.`,
  )
  return layer
}

function validateDecompositionLayer(layer, label) {
  invariant(isRecord(layer), `${label} não declara decompositionLayer.`)
  assertExactKeys(layer, [
    'cohortAges',
    'stagesWithoutCohort',
    'minIntervals',
    'sectors',
    'reference',
    'rounding',
    'closureToleranceAbs',
    'reasonCodes',
    'associativeSchemaVersion',
  ], `${label}.decompositionLayer`)
  const criteria = {
    cohortAges: layer.cohortAges,
    stagesWithoutCohort: layer.stagesWithoutCohort,
    minIntervals: layer.minIntervals,
    sectors: layer.sectors,
    reference: layer.reference,
    rounding: layer.rounding,
    closureToleranceAbs: layer.closureToleranceAbs,
  }
  assertCanonicalEqual(
    criteria,
    RESEARCH_DECOMPOSITION_CRITERIA,
    `${label}.decompositionLayer.criteria`,
  )
  assertSameArray(
    layer.reasonCodes,
    DECOMPOSITION_REASON_CODES,
    `${label}.decompositionLayer.reasonCodes`,
  )
  invariant(
    layer.associativeSchemaVersion === ASSOCIATIVE_PACKAGE_SCHEMA,
    `${label}.decompositionLayer.associativeSchemaVersion deve ser `
    + `"${ASSOCIATIVE_PACKAGE_SCHEMA}".`,
  )
  return layer
}

function validateAssociativeResearchContract(researchContract) {
  const layer = researchContract.associativeReadingLayer
  invariant(isRecord(layer), 'o contrato de pesquisa v0.6 não declara associativeReadingLayer.')
  invariant(
    layer.packagePattern === ASSOCIATIVE_LAYER_PACKAGE_PATTERN
      && layer.schemaVersion === 'vocacoes-regiao-pesquisa-associativo-v0.1'
      && layer.grammarVersion === ASSOCIATIVE_GRAMMAR_VERSION,
    'o contrato de pesquisa v0.6 diverge da camada associativa herdada.',
  )
  assertCanonicalEqual(
    layer.criteria,
    {
      minIntervals: SCREENED_RELATIONS_CRITERIA.minIntervals,
      minAbsPearson: SCREENED_RELATIONS_CRITERIA.minAbsPearson,
      maxItems: 5,
    },
    'contrato de pesquisa.associativeReadingLayer.criteria',
  )
  invariant(
    layer.correlationClosedGrammarOnly === true && layer.pValueForbidden === true,
    'o contrato de pesquisa não fecha a gramática da correlação ou permite p-valor.',
  )
  const editorialLayer = validateEditorialLayer(researchContract.editorialLayer, 'contrato de pesquisa')
  const decompositionLayer = validateDecompositionLayer(
    researchContract.decompositionLayer,
    'contrato de pesquisa',
  )
  return { layer, editorialLayer, decompositionLayer }
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

function renderClosedTemplate(template, replacements, label) {
  const rendered = template.replace(/\{([^{}]+)\}/gu, (placeholder, key) => {
    invariant(
      Object.hasOwn(replacements, key),
      `${label} não recebeu valor para o placeholder ${placeholder}.`,
    )
    return String(replacements[key])
  })
  invariant(!/[{}]/u.test(rendered), `${label} deixou placeholder sem resolver.`)
  return rendered
}

function firstStateContrastStatement(associations, temporalPairs, seriesId) {
  const readings = [
    ...associations.map((item) => item.associativeReading.stateContrast),
    ...temporalPairs.map((item) => item.associativeReading.stateContrast),
  ]
  const match = readings.find((reading) =>
    reading.seriesId === seriesId && typeof reading.statement === 'string')
  return match?.statement ?? null
}

function renderTileValueStatement(endValue, endYear, config) {
  return renderClosedTemplate(T_TILE_VALUE, {
    endValue: formatPublicNumber(endValue),
    unidadeCurta: config.shortUnit,
    endYear,
  }, 'template T-TILE-VALUE')
}

function renderTileDeltaStatement(startValue, startYear, deltaValue, config) {
  if (config.deltaKind === 'nivel') {
    return renderClosedTemplate(T_TILE_DELTA_NIVEL, {
      startValue: formatPublicNumber(startValue),
      startYear,
    }, 'template T-TILE-DELTA')
  }
  const sign = deltaValue > 0 ? '+' : deltaValue < 0 ? '-' : ''
  return renderClosedTemplate(T_TILE_DELTA_PERCENTUAL, {
    sinal: sign,
    pct: formatDecimalComma(Math.abs(deltaValue), 1),
    startYear,
  }, 'template T-TILE-DELTA')
}

export function buildVocacoesHero({ series, associations, temporalPairs }) {
  const seriesById = new Map(series.map((serie) => [serie.seriesId, serie]))
  const tiles = HERO_TILE_CONFIG.map((config) => {
    const serie = seriesById.get(config.seriesId)
    invariant(
      serie !== undefined,
      `hero não pode ser composto: série obrigatória ausente (${config.seriesId}).`,
    )
    invariant(
      serie.periodGranularity === 'annual',
      `hero não pode usar série não anual (${config.seriesId}).`,
    )
    const closed = serie.points.filter((point) => point.evidenceClass !== 'preliminary')
    invariant(
      closed.length > 0,
      `hero não pode ser composto: série sem ponto fechado (${config.seriesId}).`,
    )
    const first = closed[0]
    const last = closed[closed.length - 1]
    let deltaValue = null
    if (config.deltaKind === 'percentual') {
      invariant(
        first.value !== 0,
        `hero não pode calcular variação percentual com denominador zero (${config.seriesId}).`,
      )
      deltaValue = roundHalfAwayFromZero((last.value - first.value) / first.value * 100, 1)
    }
    return {
      tileId: config.tileId,
      seriesId: config.seriesId,
      entity: config.entity,
      label: config.label,
      window: { start: first.period, end: last.period },
      startValue: first.value,
      endValue: last.value,
      valueStatement: renderTileValueStatement(last.value, last.period, config),
      deltaKind: config.deltaKind,
      deltaValue,
      deltaStatement: renderTileDeltaStatement(first.value, first.period, deltaValue, config),
      contrastStatement: firstStateContrastStatement(associations, temporalPairs, config.seriesId),
    }
  })
  return {
    title: T_HERO_TITLE,
    lede: T_HERO_LEDE,
    methodNote: T_HERO_METHOD,
    tiles,
  }
}

function storyMovementVerb(delta, number) {
  const direction = delta > 0 ? 'positive' : delta < 0 ? 'negative' : 'zero'
  return TITLE_VERBS[direction][number === 'plural' ? 'p' : 's']
}

function storySeriesLabel(seriesId, label) {
  const entry = SHORT_LABELS[seriesId]
  invariant(entry !== undefined, `${label} cita seriesId fora de SHORT_LABELS: ${seriesId}.`)
  return entry
}

function renderStoryDuo(firstSeriesId, firstDelta, secondSeriesId, secondDelta, label) {
  const first = storySeriesLabel(firstSeriesId, label)
  const second = storySeriesLabel(secondSeriesId, label)
  const capitalizedFirst = `${first.short[0].toUpperCase()}${first.short.slice(1)}`
  return renderClosedTemplate(T_TITLE_DUO, {
    'Short(primeira)': capitalizedFirst,
    'verbo(primeira)': storyMovementVerb(firstDelta, first.number),
    'short(segunda)': second.short,
    'verbo(segunda)': storyMovementVerb(secondDelta, second.number),
  }, 'template T-TITLE-DUO')
}

function renderStoryTitle(reference, { associations, temporalPairs }, label) {
  if (reference.kind === 'structural') {
    return renderClosedTemplate(T_TITLE_DEF, {
      lagYears: reference.lagYears,
    }, 'template T-TITLE-DEF')
  }
  if (reference.kind === 'curated_association') {
    const association = associations.find((item) => item.associationId === reference.associationId)
    invariant(association !== undefined, `${label} referencia associação ausente.`)
    const reading = association.associativeReading.factorReadings.find((item) =>
      item.factorSeriesId === reference.factorSeriesId)
    invariant(reading !== undefined, `${label} referencia leitura de fator ausente.`)
    if (Object.hasOwn(reading.comovement, 'reasonCode')) return association.label
    return renderStoryDuo(
      reference.factorSeriesId,
      reading.comovement.factor.delta,
      association.educationOutcome.seriesId,
      reading.comovement.outcome.delta,
      label,
    )
  }
  invariant(reference.kind === 'curated_pair', `${label}.kind não admite storyTitle.`)
  const pair = temporalPairs.find((item) => item.pairId === reference.pairId)
  invariant(pair !== undefined, `${label} referencia par temporal ausente.`)
  if (Object.hasOwn(pair.associativeReading.comovement, 'reasonCode')) return pair.label
  return renderStoryDuo(
    pair.seriesA.seriesId,
    pair.associativeReading.comovement.a.delta,
    pair.seriesB.seriesId,
    pair.associativeReading.comovement.b.delta,
    label,
  )
}

export function addStoryTitlesToEditorialReading(editorialReading, context) {
  return {
    ...editorialReading,
    leads: editorialReading.leads.map((reference, index) => reference.kind === 'screened'
      ? reference
      : {
        ...reference,
        storyTitle: renderStoryTitle(reference, context, `editorial.leads[${index}]`),
      }),
  }
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
        'Duas perguntas organizam esta página: quais características do território podem estar '
        + 'relacionadas ao cenário educacional da região — e o que o futuro do território exige '
        + 'da educação dela. As respostas vêm em séries longas, leituras quantificadas entre '
        + 'educação e território e, onde já publicados, cenários para o horizonte declarado.',
      neutralityNote:
        'Esta página não afirma causa. Duas séries que se movem juntas são duas séries que se '
        + 'movem juntas: cada leitura mostra os números que a sustentam e diz, ela mesma, o que '
        + 'não se pode concluir dela.',
    },
    howToRead: {
      label: 'Como ler esta página',
      description:
        'Esta página responde a duas perguntas: quais características do território podem estar '
        + 'relacionadas ao cenário educacional — e o que o futuro do território exige da educação. '
        + 'Seis avisos valem para tudo o que vem abaixo.',
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
        'Correlação não é causa: as leituras quantificadas descrevem co-movimento entre séries — '
        + 'em quantos anos andaram juntas, quanto variaram na mesma janela e com que força — e '
        + 'cada leitura diz, ela mesma, o que não se pode concluir dela.',
      ],
    },
    territoryPortrait: {
      label: 'Retrato e transformações do território',
      description:
        'Séries longas da região: emprego formal, produção, demografia, nascimentos, cadastro '
        + 'social, comércio exterior e eventos climáticos. Todas vêm da soma dos municípios.',
    },
    associations: {
      label: 'Quais características do território podem estar relacionadas ao cenário educacional?',
      description:
        'Cada leitura parte de um resultado educacional observado na região e mostra, em '
        + 'números, como os fatores territoriais se moveram junto dele: anos de movimento '
        + 'conjunto, variação na mesma janela, correlação com força declarada e a posição da '
        + 'região entre as dez. Nenhuma delas afirma que um moveu o outro.',
    },
    temporalPairs: {
      label: 'Transformações simultâneas',
      description:
        'Pares de séries que mudaram ao mesmo tempo na região, cada par na sua janela, com o '
        + 'movimento conjunto medido — a camada temporal da primeira pergunta. Andar junto não é '
        + 'mover.',
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

function resolveAssociativeSeriesId(seriesKey, seriesIdByKey, label) {
  const seriesId = seriesIdByKey.get(seriesKey)
  invariant(seriesId !== undefined, `${label} referencia série ausente do pacote: "${seriesKey}".`)
  return seriesId
}

function resolvePneThemes(seriesIds, label) {
  const resolved = new Set()
  for (const seriesId of seriesIds) {
    for (const theme of PNE_SERIES_THEME_MAP[seriesId] ?? []) resolved.add(theme)
  }
  const themes = AGENDA_THEMES.filter((theme) => resolved.has(theme))
  invariant(themes.length > 0, `${label} não resolve nenhum tema do PNE.`)
  return themes.map((theme) => ({ theme, themeLabel: AGENDA_THEME_LABELS[theme] }))
}

function transposeDirectionConcordance(block) {
  if (Object.prototype.hasOwnProperty.call(block, 'reasonCode')) return { reasonCode: block.reasonCode }
  return {
    windowStart: block.windowStart,
    windowEnd: block.windowEnd,
    intervals: block.intervals,
    concordant: block.concordant,
    opposite: block.opposite,
    ties: block.ties,
    statement: block.statement,
  }
}

function transposeComovement(block, roles, seriesIdByKey, label) {
  if (Object.prototype.hasOwnProperty.call(block, 'reasonCode')) return { reasonCode: block.reasonCode }
  const transposeSeries = (source, role) => ({
    seriesId: resolveAssociativeSeriesId(source.seriesKey, seriesIdByKey, `${label}.${role}`),
    effStart: source.effStart,
    effEnd: source.effEnd,
    valueStart: source.valueStart,
    valueEnd: source.valueEnd,
    delta: source.delta,
    deltaKind: source.deltaKind,
  })
  return {
    [roles[0]]: transposeSeries(block[roles[0]], roles[0]),
    [roles[1]]: transposeSeries(block[roles[1]], roles[1]),
    statement: block.statement,
  }
}

function transposeCorrelation(block) {
  if (Object.prototype.hasOwnProperty.call(block, 'reasonCode')) return { reasonCode: block.reasonCode }
  const transposed = {
    intervals: block.intervals,
    pearsonDelta: block.pearsonDelta,
    spearmanDelta: block.spearmanDelta,
    strength: block.strength,
    direction: block.direction,
  }
  if (Object.prototype.hasOwnProperty.call(block, 'statement')) {
    transposed.statement = block.statement
  }
  return transposed
}

function transposeStateContrast(block, seriesIdByKey, label) {
  if (Object.prototype.hasOwnProperty.call(block, 'reasonCode')) return { reasonCode: block.reasonCode }
  return {
    seriesId: resolveAssociativeSeriesId(block.seriesId, seriesIdByKey, label),
    statistic: block.statistic,
    value: block.value,
    rank: block.rank,
    totalComparable: block.totalComparable,
    sameDirectionCount: block.sameDirectionCount,
    direction: block.direction,
    statement: block.statement,
  }
}

function transposeAssociationReading(sourceReading, seriesIdByKey, associationLabel) {
  return {
    grammarVersion: ASSOCIATIVE_GRAMMAR_VERSION,
    methodNote: ASSOCIATIVE_METHOD_NOTE,
    factorReadings: sourceReading.factorReadings.map((reading, index) => ({
      outcomeSeriesId: resolveAssociativeSeriesId(
        reading.outcomeSeriesKey,
        seriesIdByKey,
        `${associationLabel}.factorReadings[${index}].outcomeSeriesKey`,
      ),
      factorSeriesId: resolveAssociativeSeriesId(
        reading.factorSeriesKey,
        seriesIdByKey,
        `${associationLabel}.factorReadings[${index}].factorSeriesKey`,
      ),
      directionConcordance: transposeDirectionConcordance(reading.directionConcordance),
      comovement: transposeComovement(
        reading.comovement,
        ['outcome', 'factor'],
        seriesIdByKey,
        `${associationLabel}.factorReadings[${index}].comovement`,
      ),
      correlation: transposeCorrelation(reading.correlation),
      salience: reading.salience,
      grade: reading.grade,
    })),
    stateContrast: transposeStateContrast(
      sourceReading.stateContrast,
      seriesIdByKey,
      `${associationLabel}.stateContrast`,
    ),
  }
}

function transposeTemporalReading(sourceReading, seriesIdByKey, pairLabel) {
  return {
    grammarVersion: ASSOCIATIVE_GRAMMAR_VERSION,
    methodNote: ASSOCIATIVE_METHOD_NOTE,
    directionConcordance: transposeDirectionConcordance(sourceReading.directionConcordance),
    comovement: transposeComovement(
      sourceReading.comovement,
      ['a', 'b'],
      seriesIdByKey,
      `${pairLabel}.comovement`,
    ),
    correlation: transposeCorrelation(sourceReading.correlation),
    stateContrast: transposeStateContrast(
      sourceReading.stateContrast,
      seriesIdByKey,
      `${pairLabel}.stateContrast`,
    ),
    salience: sourceReading.salience,
    grade: sourceReading.grade,
  }
}

function transposeAssociation(sourceAssociation, sourceReading, seriesIdByKey) {
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
    associativeReading: transposeAssociationReading(
      sourceReading,
      seriesIdByKey,
      `associação "${sourceAssociation.associationKey}"`,
    ),
    pneThemes: resolvePneThemes([outcomeId], `associação "${sourceAssociation.associationKey}"`),
  }
}

function transposeTemporalPair(sourcePair, sourceReading, seriesIdByKey, labelByKey) {
  const build = (key, label) => {
    const seriesId = seriesIdByKey.get(key)
    invariant(seriesId !== undefined, `o par temporal referencia série ausente do pacote: "${key}".`)
    return { seriesId, label: labelByKey.get(key) ?? label }
  }
  const seriesA = build(sourcePair.seriesKeyA)
  const seriesB = build(sourcePair.seriesKeyB)
  return {
    pairId: slugify(sourcePair.publicLabel),
    label: sourcePair.publicLabel,
    window: { start: sourcePair.window.start, end: sourcePair.window.end },
    periodLabel: formatWindowLabel(sourcePair.window),
    seriesA,
    seriesB,
    observedStatement: sourcePair.observedStatement,
    prohibitedClaim: composeProhibitedClaim(sourcePair.forbiddenInterpretation.prohibitedClaim),
    associativeReading: transposeTemporalReading(
      sourceReading,
      seriesIdByKey,
      `par temporal "${sourcePair.pairKey}"`,
    ),
    pneThemes: resolvePneThemes(
      [seriesA.seriesId, seriesB.seriesId],
      `par temporal "${sourcePair.pairKey}"`,
    ),
  }
}

/* ------------------------------------------------------------------ *
 * Leitura associativa quantificada — reverificação da origem.
 *
 * O parser 2.9.0 fará a mesma conferência sobre o documento público. Esta
 * primeira passagem trabalha ainda com as seriesKeys do pacote de pesquisa e
 * impede que um statement ou um rank divergente atravesse a transposição.
 * ------------------------------------------------------------------ */

function assertCanonicalEqual(actual, expected, label) {
  invariant(
    JSON.stringify(canonicalize(actual)) === JSON.stringify(canonicalize(expected)),
    `${label} diverge da recomputação da plataforma.`,
  )
}

function sourceSeriesByKey(sourcePackage, label) {
  const byKey = new Map(sourcePackage.series.map((serie) => [serie.seriesKey, serie]))
  invariant(byKey.size === sourcePackage.series.length, `${label} repete seriesKey.`)
  return byKey
}

const SOURCE_DECOMPOSITIONS_FIELDS = Object.freeze(['criteria', 'enrollment', 'employment'])
const SOURCE_ENROLLMENT_FIELDS = Object.freeze(['items', 'absences'])
const SOURCE_ENROLLMENT_ITEM_FIELDS = Object.freeze([
  'stage',
  'outcomeSeriesKey',
  'cohortSeriesKey',
  'cohortAges',
  'window',
  'terms',
  'contributions',
  'grade',
])
const SOURCE_ENROLLMENT_ABSENCE_FIELDS = Object.freeze(['stage', 'reasonCode'])
const SOURCE_EMPLOYMENT_FIELDS = Object.freeze(['item', 'absence'])
const SOURCE_EMPLOYMENT_ITEM_FIELDS = Object.freeze([
  'window',
  'sectors',
  'totals',
  'excludedSectorLinks',
  'contributions',
  'grade',
])
const SOURCE_EMPLOYMENT_ABSENCE_FIELDS = Object.freeze(['reasonCode'])
const DECOMPOSITION_WINDOW_FIELDS = Object.freeze(['start', 'end', 'intervals'])
const ENROLLMENT_TERMS_FIELDS = Object.freeze([
  'enrollmentStart',
  'enrollmentEnd',
  'cohortStart',
  'cohortEnd',
  'ratioStartPerHundred',
  'ratioEndPerHundred',
])
const ENROLLMENT_CONTRIBUTION_FIELDS = Object.freeze([
  'totalPct',
  'demographicPp',
  'ratioPp',
])
const EMPLOYMENT_COUNT_FIELDS = Object.freeze([
  'regionStart',
  'regionEnd',
  'stateStart',
  'stateEnd',
])
const EMPLOYMENT_SECTOR_FIELDS = Object.freeze(['sectorLabel', ...EMPLOYMENT_COUNT_FIELDS])
const EMPLOYMENT_CONTRIBUTION_FIELDS = Object.freeze([
  'totalPct',
  'statePp',
  'mixPp',
  'ownPp',
])

function canonicalEquals(actual, expected) {
  return JSON.stringify(canonicalize(actual)) === JSON.stringify(canonicalize(expected))
}

function assertFinite(value, label) {
  invariant(typeof value === 'number' && Number.isFinite(value), `${label} deve ser número finito.`)
}

function assertCount(value, label) {
  invariant(Number.isInteger(value) && value >= 0, `${label} deve ser contagem inteira não negativa.`)
}

function validateSourceDecompositionWindow(window, label) {
  assertExactKeys(window, DECOMPOSITION_WINDOW_FIELDS, label)
  for (const field of DECOMPOSITION_WINDOW_FIELDS) {
    invariant(Number.isInteger(window[field]), `${label}.${field} deve ser inteiro.`)
  }
  invariant(window.end > window.start, `${label}.end deve ser posterior a start.`)
  invariant(window.intervals === window.end - window.start, `${label}.intervals deve ser end - start.`)
}

function validateSourceEnrollmentItem(item, label) {
  assertExactKeys(item, SOURCE_ENROLLMENT_ITEM_FIELDS, label)
  invariant(DECOMPOSITION_STAGES.includes(item.stage), `${label}.stage fora do contrato E2.`)
  const publicConfig = DECOMPOSITION_STAGE_CONFIG[item.stage]
  const sourceConfig = DECOMPOSITION_SOURCE_CONFIG[item.stage]
  invariant(
    item.outcomeSeriesKey === sourceConfig.outcomeSeriesKey
      && item.cohortSeriesKey === sourceConfig.cohortSeriesKey,
    `${label} referencia séries diferentes das séries fechadas da etapa.`,
  )
  assertExactKeys(item.cohortAges, ['min', 'max'], `${label}.cohortAges`)
  invariant(
    item.cohortAges.min === publicConfig.cohortAges.min
      && item.cohortAges.max === publicConfig.cohortAges.max,
    `${label}.cohortAges diverge da faixa fechada da etapa.`,
  )
  validateSourceDecompositionWindow(item.window, `${label}.window`)
  assertExactKeys(item.terms, ENROLLMENT_TERMS_FIELDS, `${label}.terms`)
  for (const field of ['enrollmentStart', 'enrollmentEnd', 'cohortStart', 'cohortEnd']) {
    assertCount(item.terms[field], `${label}.terms.${field}`)
  }
  for (const field of ['ratioStartPerHundred', 'ratioEndPerHundred']) {
    assertFinite(item.terms[field], `${label}.terms.${field}`)
  }
  assertExactKeys(item.contributions, ENROLLMENT_CONTRIBUTION_FIELDS, `${label}.contributions`)
  for (const field of ENROLLMENT_CONTRIBUTION_FIELDS) {
    assertFinite(item.contributions[field], `${label}.contributions.${field}`)
  }
  invariant(item.grade === 'E2', `${label}.grade deve ser "E2".`)
}

function validateSourceEnrollmentAbsence(absence, label) {
  assertExactKeys(absence, SOURCE_ENROLLMENT_ABSENCE_FIELDS, label)
  invariant(DECOMPOSITION_STAGES.includes(absence.stage), `${label}.stage fora do contrato E2.`)
  invariant(
    DECOMPOSITION_REASON_CODES.includes(absence.reasonCode),
    `${label}.reasonCode fora do contrato E2.`,
  )
}

function validateSourceEmploymentItem(item, label) {
  assertExactKeys(item, SOURCE_EMPLOYMENT_ITEM_FIELDS, label)
  validateSourceDecompositionWindow(item.window, `${label}.window`)
  invariant(
    Array.isArray(item.sectors) && item.sectors.length === DECOMPOSITION_CRITERIA.sectors.length,
    `${label}.sectors deve trazer os cinco setores E2.`,
  )
  item.sectors.forEach((sector, index) => {
    const sectorLabel = `${label}.sectors[${index}]`
    assertExactKeys(sector, EMPLOYMENT_SECTOR_FIELDS, sectorLabel)
    invariant(
      sector.sectorLabel === DECOMPOSITION_CRITERIA.sectors[index],
      `${sectorLabel}.sectorLabel diverge do enum ou da ordem fechada.`,
    )
    for (const field of EMPLOYMENT_COUNT_FIELDS) assertCount(sector[field], `${sectorLabel}.${field}`)
  })
  for (const [name, counts] of [
    ['totals', item.totals],
    ['excludedSectorLinks', item.excludedSectorLinks],
  ]) {
    assertExactKeys(counts, EMPLOYMENT_COUNT_FIELDS, `${label}.${name}`)
    for (const field of EMPLOYMENT_COUNT_FIELDS) assertCount(counts[field], `${label}.${name}.${field}`)
  }
  assertExactKeys(item.contributions, EMPLOYMENT_CONTRIBUTION_FIELDS, `${label}.contributions`)
  for (const field of EMPLOYMENT_CONTRIBUTION_FIELDS) {
    assertFinite(item.contributions[field], `${label}.contributions.${field}`)
  }
  invariant(item.grade === 'E2', `${label}.grade deve ser "E2".`)
}

function validateSourceDecompositions(decompositions, label) {
  assertExactKeys(decompositions, SOURCE_DECOMPOSITIONS_FIELDS, label)
  assertCanonicalEqual(decompositions.criteria, RESEARCH_DECOMPOSITION_CRITERIA, `${label}.criteria`)
  assertExactKeys(decompositions.enrollment, SOURCE_ENROLLMENT_FIELDS, `${label}.enrollment`)
  invariant(Array.isArray(decompositions.enrollment.items), `${label}.enrollment.items deve ser lista.`)
  invariant(
    Array.isArray(decompositions.enrollment.absences),
    `${label}.enrollment.absences deve ser lista.`,
  )
  const seenStages = new Set()
  for (const [name, validator] of [
    ['items', validateSourceEnrollmentItem],
    ['absences', validateSourceEnrollmentAbsence],
  ]) {
    let previousOrder = -1
    decompositions.enrollment[name].forEach((entry, index) => {
      const entryLabel = `${label}.enrollment.${name}[${index}]`
      validator(entry, entryLabel)
      const order = DECOMPOSITION_STAGES.indexOf(entry.stage)
      invariant(order > previousOrder, `${entryLabel}.stage está fora da ordem fechada.`)
      invariant(!seenStages.has(entry.stage), `${entryLabel}.stage está repetida.`)
      previousOrder = order
      seenStages.add(entry.stage)
    })
  }
  invariant(
    seenStages.size === DECOMPOSITION_STAGES.length,
    `${label}.enrollment deve declarar item ou ausência para cada etapa com coorte.`,
  )

  assertExactKeys(decompositions.employment, SOURCE_EMPLOYMENT_FIELDS, `${label}.employment`)
  const hasEmploymentItem = decompositions.employment.item !== null
  const hasEmploymentAbsence = decompositions.employment.absence !== null
  invariant(
    hasEmploymentItem !== hasEmploymentAbsence,
    `${label}.employment deve declarar exatamente um item ou uma ausência.`,
  )
  if (hasEmploymentItem) {
    validateSourceEmploymentItem(decompositions.employment.item, `${label}.employment.item`)
  } else {
    assertExactKeys(
      decompositions.employment.absence,
      SOURCE_EMPLOYMENT_ABSENCE_FIELDS,
      `${label}.employment.absence`,
    )
    invariant(
      DECOMPOSITION_REASON_CODES.includes(decompositions.employment.absence.reasonCode),
      `${label}.employment.absence.reasonCode fora do contrato E2.`,
    )
  }
  return decompositions
}

function observedNonPreliminarySourcePoints(serie) {
  const preliminary = new Set(serie.preliminaryPeriods)
  return serie.points
    .filter((point) => point.evidenceClass === 'observed' && !preliminary.has(point.period))
    .sort((left, right) => left.period - right.period)
}

function recomputeEnrollmentFromSource(stage, sourceSeriesMap, label) {
  const publicConfig = DECOMPOSITION_STAGE_CONFIG[stage]
  const sourceConfig = DECOMPOSITION_SOURCE_CONFIG[stage]
  const outcomeSerie = sourceSeriesMap.get(sourceConfig.outcomeSeriesKey)
  const cohortSerie = sourceSeriesMap.get(sourceConfig.cohortSeriesKey)
  if (outcomeSerie === undefined || cohortSerie === undefined) {
    return { kind: 'absence', stage, reasonCode: 'serie_ausente' }
  }
  invariant(outcomeSerie.periodGranularity === 'annual', `${label}: matrícula E2 deve ser anual.`)
  invariant(cohortSerie.periodGranularity === 'annual', `${label}: coorte E2 deve ser anual.`)

  const outcomes = observedNonPreliminarySourcePoints(outcomeSerie)
  const cohortPreliminary = new Set(cohortSerie.preliminaryPeriods)
  const cohortByPeriod = new Map(cohortSerie.points.map((point) => [point.period, point]))
  const computable = []
  let cohortFailures = 0
  for (const outcome of outcomes) {
    let cohort = 0
    let complete = true
    for (let age = publicConfig.cohortAges.min; age <= publicConfig.cohortAges.max; age += 1) {
      const birthPeriod = outcome.period - age
      const point = cohortByPeriod.get(birthPeriod)
      if (
        point === undefined
        || cohortPreliminary.has(birthPeriod)
        || point.evidenceClass !== 'observed'
      ) {
        complete = false
        break
      }
      cohort += point.value
    }
    if (complete) computable.push({ period: outcome.period, enrollment: outcome.value, cohort })
    else cohortFailures += 1
  }

  if (computable.length === 0) {
    return {
      kind: 'absence',
      stage,
      reasonCode: outcomes.length > 0 && cohortFailures === outcomes.length
        ? 'coorte_incompleta'
        : 'janela_insuficiente',
    }
  }
  const first = computable[0]
  const last = computable[computable.length - 1]
  const intervals = last.period - first.period
  if (intervals < DECOMPOSITION_CRITERIA.minIntervals) {
    return { kind: 'absence', stage, reasonCode: 'janela_insuficiente' }
  }
  for (const [field, value] of Object.entries({
    enrollmentStart: first.enrollment,
    enrollmentEnd: last.enrollment,
    cohortStart: first.cohort,
    cohortEnd: last.cohort,
  })) assertCount(value, `${label}.${field} recomputado`)
  if (first.enrollment === 0 || first.cohort === 0 || last.cohort === 0) {
    return { kind: 'absence', stage, reasonCode: 'termo_nulo' }
  }

  const ratioStart = first.enrollment / first.cohort
  const ratioEnd = last.enrollment / last.cohort
  const totalPctRaw = 100 * (last.enrollment - first.enrollment) / first.enrollment
  const demographicPpRaw = 100
    * (last.cohort - first.cohort)
    * ((ratioStart + ratioEnd) / 2)
    / first.enrollment
  const ratioPpRaw = 100
    * (ratioEnd - ratioStart)
    * ((first.cohort + last.cohort) / 2)
    / first.enrollment
  invariant(
    Math.abs(totalPctRaw - demographicPpRaw - ratioPpRaw)
      <= DECOMPOSITION_CRITERIA.closureToleranceAbs,
    `${label}: a identidade de Bennet não fecha no valor cru.`,
  )
  const decimals = DECOMPOSITION_CRITERIA.rounding.published
  return {
    kind: 'item',
    stage,
    outcomeSeriesKey: sourceConfig.outcomeSeriesKey,
    cohortSeriesKey: sourceConfig.cohortSeriesKey,
    cohortAges: { min: publicConfig.cohortAges.min, max: publicConfig.cohortAges.max },
    window: { start: first.period, end: last.period, intervals },
    terms: {
      enrollmentStart: first.enrollment,
      enrollmentEnd: last.enrollment,
      cohortStart: first.cohort,
      cohortEnd: last.cohort,
      ratioStartPerHundred: roundHalfAwayFromZero(ratioStart * 100, decimals),
      ratioEndPerHundred: roundHalfAwayFromZero(ratioEnd * 100, decimals),
    },
    contributions: {
      totalPct: roundHalfAwayFromZero(totalPctRaw, decimals),
      demographicPp: roundHalfAwayFromZero(demographicPpRaw, decimals),
      ratioPp: roundHalfAwayFromZero(ratioPpRaw, decimals),
    },
    grade: 'E2',
  }
}

function publicEnrollmentAbsence(stage, reasonCode) {
  const absence = {
    stage,
    stageLabel: DECOMPOSITION_STAGE_CONFIG[stage].stageLabel,
    reasonCode,
  }
  return { ...absence, statement: renderE2AbsenceStatement(absence) }
}

function publicEnrollmentItem(sourceItem) {
  const config = DECOMPOSITION_STAGE_CONFIG[sourceItem.stage]
  const item = {
    stage: sourceItem.stage,
    stageLabel: config.stageLabel,
    outcomeSeriesId: config.outcomeSeriesId,
    cohortSeriesId: config.cohortSeriesId,
    cohortAges: { ...sourceItem.cohortAges },
    window: { ...sourceItem.window },
    terms: { ...sourceItem.terms },
    contributions: { ...sourceItem.contributions },
    grade: 'E2',
    pneThemes: resolvePneThemes(
      [config.outcomeSeriesId],
      `decomposição de matrícula ${sourceItem.stage}`,
    ),
  }
  return { ...item, statement: renderE2EnrollmentStatement(item) }
}

function recomputeEmploymentFromSource(sourceItem, label) {
  if (sourceItem.window.intervals < DECOMPOSITION_CRITERIA.minIntervals) {
    return { kind: 'absence', reasonCode: 'janela_insuficiente' }
  }
  const totals = Object.fromEntries(EMPLOYMENT_COUNT_FIELDS.map((field) => [
    field,
    sourceItem.sectors.reduce((sum, sector) => sum + sector[field], 0),
  ]))
  if (
    totals.regionStart === 0
    || totals.stateStart === 0
    || sourceItem.sectors.some((sector) => sector.stateStart === 0)
  ) return { kind: 'absence', reasonCode: 'termo_nulo' }

  const stateGrowth = (totals.stateEnd - totals.stateStart) / totals.stateStart
  const stateTerm = totals.regionStart * stateGrowth
  let mixTerm = 0
  let ownTerm = 0
  for (const sector of sourceItem.sectors) {
    const sectorStateGrowth = (sector.stateEnd - sector.stateStart) / sector.stateStart
    mixTerm += sector.regionStart * (sectorStateGrowth - stateGrowth)
    ownTerm += (sector.regionEnd - sector.regionStart) - sector.regionStart * sectorStateGrowth
  }
  const totalTerm = totals.regionEnd - totals.regionStart
  const totalPctRaw = 100 * totalTerm / totals.regionStart
  const statePpRaw = 100 * stateTerm / totals.regionStart
  const mixPpRaw = 100 * mixTerm / totals.regionStart
  const ownPpRaw = 100 * ownTerm / totals.regionStart
  invariant(
    Math.abs(totalPctRaw - statePpRaw - mixPpRaw - ownPpRaw)
      <= DECOMPOSITION_CRITERIA.closureToleranceAbs,
    `${label}: a identidade shift-share não fecha no valor cru.`,
  )
  const decimals = DECOMPOSITION_CRITERIA.rounding.published
  return {
    kind: 'item',
    window: { ...sourceItem.window },
    sectors: sourceItem.sectors.map((sector) => ({ ...sector })),
    totals,
    excludedSectorLinks: { ...sourceItem.excludedSectorLinks },
    contributions: {
      totalPct: roundHalfAwayFromZero(totalPctRaw, decimals),
      statePp: roundHalfAwayFromZero(statePpRaw, decimals),
      mixPp: roundHalfAwayFromZero(mixPpRaw, decimals),
      ownPp: roundHalfAwayFromZero(ownPpRaw, decimals),
    },
    grade: 'E2',
  }
}

function publicEmploymentAbsence(reasonCode) {
  const absence = { reasonCode }
  return { ...absence, statement: renderE2AbsenceStatement(absence) }
}

function publicEmploymentItem(sourceItem) {
  const item = {
    window: { ...sourceItem.window },
    sectors: sourceItem.sectors.map((sector) => ({ ...sector })),
    totals: { ...sourceItem.totals },
    excludedSectorLinks: { ...sourceItem.excludedSectorLinks },
    contributions: { ...sourceItem.contributions },
    grade: 'E2',
    sourceLabel: DECOMPOSITION_EMPLOYMENT_SOURCE_LABEL,
  }
  return { ...item, statement: renderE2EmploymentStatement(item) }
}

function publicDecompositionCriteria() {
  return {
    cohortAges: Object.fromEntries(Object.entries(DECOMPOSITION_CRITERIA.cohortAges)
      .map(([stage, ages]) => [stage, [...ages]])),
    stagesWithoutCohort: [...DECOMPOSITION_CRITERIA.stagesWithoutCohort],
    minIntervals: DECOMPOSITION_CRITERIA.minIntervals,
    sectors: [...DECOMPOSITION_CRITERIA.sectors],
    reference: DECOMPOSITION_CRITERIA.reference,
    rounding: { ...DECOMPOSITION_CRITERIA.rounding },
    closureToleranceAbs: DECOMPOSITION_CRITERIA.closureToleranceAbs,
  }
}

/**
 * Transpõe E2 somente depois de recomputar. Divergência não vaza o item:
 * produz ausência `conta_nao_fecha`, deixando as leituras associativas E1 no
 * restante do documento exatamente como estavam.
 */
export function transposeDecompositions({ associativePackage, sourcePackage }) {
  const source = validateSourceDecompositions(
    associativePackage.decompositions,
    `pacote associativo de "${sourcePackage.region.slug}".decompositions`,
  )
  const sourceSeriesMap = sourceSeriesByKey(
    sourcePackage,
    `pacote regional de "${sourcePackage.region.slug}"`,
  )
  const sourceEnrollmentByStage = new Map([
    ...source.enrollment.items.map((item) => [item.stage, { kind: 'item', value: item }]),
    ...source.enrollment.absences.map((absence) => [
      absence.stage,
      { kind: 'absence', value: absence },
    ]),
  ])
  const items = []
  const absences = []
  for (const stage of DECOMPOSITION_STAGES) {
    const published = sourceEnrollmentByStage.get(stage)
    const recomputed = recomputeEnrollmentFromSource(
      stage,
      sourceSeriesMap,
      `decomposição de matrícula ${stage}`,
    )
    const { kind: _kind, ...recomputedValue } = recomputed
    if (
      published.kind === 'item'
      && recomputed.kind === 'item'
      && canonicalEquals(published.value, recomputedValue)
    ) {
      items.push(publicEnrollmentItem(recomputed))
      continue
    }
    if (
      published.kind === 'absence'
      && recomputed.kind === 'absence'
      && published.value.reasonCode === recomputed.reasonCode
    ) {
      absences.push(publicEnrollmentAbsence(stage, recomputed.reasonCode))
      continue
    }
    absences.push(publicEnrollmentAbsence(stage, 'conta_nao_fecha'))
  }

  let employmentItem = null
  let employmentAbsence = null
  if (source.employment.item === null) {
    employmentAbsence = publicEmploymentAbsence(source.employment.absence.reasonCode)
  } else {
    const recomputed = recomputeEmploymentFromSource(
      source.employment.item,
      'decomposição de vínculos formais',
    )
    const { kind: _kind, ...recomputedValue } = recomputed
    if (recomputed.kind === 'item' && canonicalEquals(source.employment.item, recomputedValue)) {
      employmentItem = publicEmploymentItem(recomputed)
    } else {
      employmentAbsence = publicEmploymentAbsence('conta_nao_fecha')
    }
  }

  return {
    ...DECOMPOSITION_FRAMING,
    enrollment: {
      methodStatement: E2_ENROLLMENT_METHOD_STATEMENT,
      criteria: publicDecompositionCriteria(),
      items,
      absences,
    },
    employment: {
      methodStatement: E2_EMPLOYMENT_METHOD_STATEMENT,
      criteria: publicDecompositionCriteria(),
      item: employmentItem,
      absence: employmentAbsence,
    },
  }
}

function validateResearchScreeningCriteria(criteria, sourceSeriesMap, label) {
  assertExactKeys(criteria, [
    'minIntervals',
    'minAbsPearson',
    'maxItems',
    'excludedSeries',
  ], label)
  for (const [field, expected] of Object.entries(SCREENED_RELATIONS_CRITERIA)) {
    invariant(criteria[field] === expected, `${label}.${field} diverge do contrato público.`)
  }
  invariant(
    Array.isArray(criteria.excludedSeries)
      && criteria.excludedSeries.length === SCREENING_EXCLUDED_SERIES_IDS.length,
    `${label}.excludedSeries deve declarar as 13 exclusões da triagem.`,
  )
  assertSameArray(criteria.excludedSeries, [...criteria.excludedSeries].sort(), `${label}.excludedSeries`)
  invariant(
    new Set(criteria.excludedSeries).size === criteria.excludedSeries.length,
    `${label}.excludedSeries repete seriesKey.`,
  )
  const translated = criteria.excludedSeries.map((seriesKey) => {
    const serie = sourceSeriesMap.get(seriesKey)
    invariant(serie !== undefined, `${label}.excludedSeries referencia série ausente: "${seriesKey}".`)
    return slugify(serie.publicLabel)
  })
  assertSameArray(translated, SCREENING_EXCLUDED_SERIES_IDS, `${label}.excludedSeries traduzida`)
  return new Set(criteria.excludedSeries)
}

function deltaKindOf(sourceSeries) {
  return sourceSeries.ratioOf !== null && sourceSeries.ratioOf !== undefined ? 'pontos' : 'nivel'
}

function expectedDirectionConcordance(serieA, serieB, window) {
  const computed = computeDirectionConcordance(serieA.points, serieB.points, window)
  if (Object.prototype.hasOwnProperty.call(computed, 'reasonCode')) return computed
  return {
    ...computed,
    statement: renderConcordanceStatement({
      ...computed,
      labelA: serieA.publicLabel,
      labelB: serieB.publicLabel,
    }),
  }
}

function expectedComovement(serieA, serieB, window, roles) {
  const movementA = computeComovement(serieA.points, window, deltaKindOf(serieA))
  const movementB = computeComovement(serieB.points, window, deltaKindOf(serieB))
  if (
    Object.prototype.hasOwnProperty.call(movementA, 'reasonCode')
    || Object.prototype.hasOwnProperty.call(movementB, 'reasonCode')
  ) {
    return { reasonCode: 'sem_intervalos_comparaveis' }
  }
  return {
    [roles[0]]: { seriesKey: serieA.seriesKey, ...movementA },
    [roles[1]]: { seriesKey: serieB.seriesKey, ...movementB },
    statement: renderComovementStatement({
      a: movementA,
      b: movementB,
      labelA: serieA.publicLabel,
      labelB: serieB.publicLabel,
    }),
  }
}

function expectedCorrelation(serieA, serieB, window, { statement = true } = {}) {
  const concordance = computeDirectionConcordance(serieA.points, serieB.points, window)
  const intervals = Object.prototype.hasOwnProperty.call(concordance, 'reasonCode')
    ? 0
    : concordance.intervals
  if (intervals < 5) return { reasonCode: 'janela_curta' }
  const pearsonRaw = computePearsonDelta(serieA.points, serieB.points, window)
  const spearmanRaw = computeSpearmanDelta(serieA.points, serieB.points, window)
  if (pearsonRaw === null || spearmanRaw === null) return { reasonCode: 'variancia_nula' }
  const direction = pearsonRaw > 0 ? 'positiva' : pearsonRaw < 0 ? 'negativa' : 'nula'
  const result = {
    intervals,
    pearsonDelta: roundHalfAwayFromZero(pearsonRaw, 2),
    spearmanDelta: roundHalfAwayFromZero(spearmanRaw, 2),
    strength: correlationStrength(Math.abs(pearsonRaw)),
    direction,
  }
  if (statement) {
    result.statement = renderCorrelationStatement({
      windowStart: window.start,
      windowEnd: window.end,
      pearsonDelta: result.pearsonDelta,
      strength: result.strength,
      direction,
    })
  }
  return result
}

function expectedSalience(serieA, serieB, window) {
  const correlation = expectedCorrelation(serieA, serieB, window, { statement: false })
  return correlation.reasonCode === undefined
    && EDITORIAL_READING_CRITERIA.leadStrengths.includes(correlation.strength)
    ? 'lead'
    : 'note'
}

function verifyReadingClassification(reading, serieA, serieB, window, label) {
  const salience = expectedSalience(serieA, serieB, window)
  invariant(
    reading.salience === salience,
    `${label}.salience diverge da recomputação: esperado ${salience}, recebido ${reading.salience}.`,
  )
  invariant(
    EDITORIAL_READING_CRITERIA.gradeEnum.includes(reading.grade),
    `${label}.grade fora do enum editorial.`,
  )
}

function comparableStateMovements(seriesKey, window, allSourcePackagesBySlug) {
  const comparable = []
  for (const [regionSlug, sourcePackage] of allSourcePackagesBySlug) {
    const sourceSeries = sourcePackage.series.find((serie) => serie.seriesKey === seriesKey)
    if (sourceSeries === undefined) continue
    const movement = computeComovement(sourceSeries.points, window, deltaKindOf(sourceSeries))
    if (Object.prototype.hasOwnProperty.call(movement, 'reasonCode')) continue
    if (movement.deltaKind === 'nivel' && movement.valueStart === 0) continue
    comparable.push({
      regionSlug,
      value: movement.deltaKind === 'pontos'
        ? movement.delta
        : movement.delta / movement.valueStart * 100,
      movement,
      sourceSeries,
    })
  }
  return comparable
}

function expectedStateContrast({
  seriesKey,
  window,
  regionSlug,
  allSourcePackagesBySlug,
}) {
  const comparable = comparableStateMovements(seriesKey, window, allSourcePackagesBySlug)
  if (comparable.length < 2) return { reasonCode: 'contraste_sem_regioes_comparaveis' }
  const own = comparable.find((entry) => entry.regionSlug === regionSlug)
  invariant(own !== undefined, `o contraste estadual de "${regionSlug}" excluiu a própria região.`)
  if (own.value === 0) return { reasonCode: 'variacao_nula' }
  const direction = own.value > 0 ? 'alta' : 'queda'
  const rank = 1 + comparable.filter((entry) =>
    direction === 'alta' ? entry.value > own.value : entry.value < own.value).length
  const sameDirectionCount = comparable.filter((entry) =>
    direction === 'alta' ? entry.value > 0 : entry.value < 0).length
  const statistic = own.movement.deltaKind === 'pontos'
    ? 'variacao_em_pontos'
    : 'variacao_percentual'
  const result = {
    seriesId: seriesKey,
    statistic,
    value: roundHalfAwayFromZero(own.value, 1),
    rank,
    totalComparable: comparable.length,
    sameDirectionCount,
    direction,
  }
  return {
    ...result,
    statement: renderContrastStatement({
      ...result,
      label: own.sourceSeries.publicLabel,
    }),
  }
}

function verifyComparisonReading({
  reading,
  serieA,
  serieB,
  window,
  roles,
  label,
}) {
  assertCanonicalEqual(
    reading.directionConcordance,
    expectedDirectionConcordance(serieA, serieB, window),
    `${label}.directionConcordance`,
  )
  assertCanonicalEqual(
    reading.comovement,
    expectedComovement(serieA, serieB, window, roles),
    `${label}.comovement`,
  )
  assertCanonicalEqual(
    reading.correlation,
    expectedCorrelation(serieA, serieB, window),
    `${label}.correlation`,
  )
  verifyReadingClassification(reading, serieA, serieB, window, label)
}

function lagComparablePeriods(serieA, serieB, lagYears) {
  const valuesA = new Map(serieA.points.map((point) => [point.period, point.value]))
  const valuesB = new Map(serieB.points.map((point) => [point.period, point.value]))
  const periods = []
  for (const period of [...valuesA.keys()].sort((left, right) => left - right)) {
    if (
      valuesA.has(period - 1)
      && valuesB.has(period + lagYears - 1)
      && valuesB.has(period + lagYears)
    ) periods.push(period)
  }
  return periods
}

function expectedLaggedPair(sourcePair, sourceSeriesMap) {
  const serieA = sourceSeriesMap.get(sourcePair.aSeriesKey)
  const serieB = sourceSeriesMap.get(sourcePair.bSeriesKey)
  if (serieA === undefined || serieB === undefined) {
    return {
      aSeriesKey: sourcePair.aSeriesKey,
      bSeriesKey: sourcePair.bSeriesKey,
      lagYears: sourcePair.lagYears,
      reasonCode: 'serie_ausente',
      statement: renderLaggedStatement({
        aSeriesLabel: serieA?.publicLabel ?? sourcePair.aSeriesKey,
        bSeriesLabel: serieB?.publicLabel ?? sourcePair.bSeriesKey,
        lagYears: sourcePair.lagYears,
        reasonCode: 'serie_ausente',
      }),
    }
  }
  const periods = lagComparablePeriods(serieA, serieB, sourcePair.lagYears)
  if (periods.length < 5) {
    return {
      aSeriesKey: sourcePair.aSeriesKey,
      bSeriesKey: sourcePair.bSeriesKey,
      lagYears: sourcePair.lagYears,
      reasonCode: 'defasagem_sem_janela_suficiente',
      statement: renderLaggedStatement({
        aSeriesLabel: serieA.publicLabel,
        bSeriesLabel: serieB.publicLabel,
        lagYears: sourcePair.lagYears,
        reasonCode: 'defasagem_sem_janela_suficiente',
      }),
    }
  }
  const windowA = { start: periods[0] - 1, end: periods[periods.length - 1] }
  const windowB = {
    start: windowA.start + sourcePair.lagYears,
    end: windowA.end + sourcePair.lagYears,
  }
  const shiftedB = {
    ...serieB,
    points: serieB.points.map((point) => ({ ...point, period: point.period - sourcePair.lagYears })),
  }
  const concordance = computeDirectionConcordance(serieA.points, shiftedB.points, windowA)
  invariant(!Object.prototype.hasOwnProperty.call(concordance, 'reasonCode'),
    'a janela defasada suficiente não produziu intervalos comparáveis.')
  const correlation = expectedCorrelation(serieA, shiftedB, windowA, { statement: false })
  const result = {
    aSeriesKey: sourcePair.aSeriesKey,
    bSeriesKey: sourcePair.bSeriesKey,
    lagYears: sourcePair.lagYears,
    rationale: sourcePair.rationale,
    windowA,
    windowB,
    intervals: concordance.intervals,
    concordant: concordance.concordant,
    opposite: concordance.opposite,
    ties: concordance.ties,
    correlation,
    salience: 'lead',
    grade: EDITORIAL_READING_CRITERIA.gradeEnum[0],
  }
  return {
    ...result,
    statement: renderLaggedStatement({
      aSeriesLabel: serieA.publicLabel,
      bSeriesLabel: serieB.publicLabel,
      lagYears: result.lagYears,
      rationale: result.rationale,
      windowA,
      windowB,
      concordant: result.concordant,
      intervals: result.intervals,
      correlation,
    }),
  }
}

function researchEditorialRefId(reference) {
  if (reference.kind === 'structural') {
    return `${reference.kind}/${reference.aSeriesKey}/${reference.bSeriesKey}/${reference.lagYears}`
  }
  if (reference.kind === 'curated_association') {
    return `${reference.kind}/${reference.associationKey}/${reference.factorSeriesKey}`
  }
  if (reference.kind === 'curated_pair') return `${reference.kind}/${reference.pairKey}`
  return `${reference.kind}/${reference.relationId}`
}

function recomputeResearchEditorial(associativePackage, sourcePackage, sourceSeriesMap) {
  const structural = []
  const ranked = []
  let noteCount = 0

  for (const pair of associativePackage.laggedPairs) {
    if (!Object.prototype.hasOwnProperty.call(pair, 'reasonCode')) {
      structural.push({
        kind: 'structural',
        aSeriesKey: pair.aSeriesKey,
        bSeriesKey: pair.bSeriesKey,
        lagYears: pair.lagYears,
      })
    }
  }

  for (const association of associativePackage.associations) {
    for (const reading of association.factorReadings) {
      const outcome = sourceSeriesMap.get(reading.outcomeSeriesKey)
      const factor = sourceSeriesMap.get(reading.factorSeriesKey)
      invariant(outcome !== undefined && factor !== undefined, 'editorial referencia série curada ausente.')
      if (expectedSalience(outcome, factor, association.window) === 'note') {
        noteCount += 1
        continue
      }
      const reference = {
        kind: 'curated_association',
        associationKey: association.associationKey,
        factorSeriesKey: reading.factorSeriesKey,
      }
      ranked.push({
        reference,
        absPearson: Math.abs(computePearsonDelta(outcome.points, factor.points, association.window)),
        refId: researchEditorialRefId(reference),
      })
    }
  }

  for (const pair of associativePackage.temporalPairs) {
    const regionalPair = sourcePackage.temporalPairs.find((candidate) => candidate.pairKey === pair.pairKey)
    invariant(regionalPair !== undefined, `editorial referencia pairKey ausente: "${pair.pairKey}".`)
    const a = sourceSeriesMap.get(regionalPair.seriesKeyA)
    const b = sourceSeriesMap.get(regionalPair.seriesKeyB)
    invariant(a !== undefined && b !== undefined, `editorial referencia par curado ausente: "${pair.pairKey}".`)
    if (expectedSalience(a, b, pair.window) === 'note') {
      noteCount += 1
      continue
    }
    const reference = { kind: 'curated_pair', pairKey: pair.pairKey }
    ranked.push({
      reference,
      absPearson: Math.abs(computePearsonDelta(a.points, b.points, pair.window)),
      refId: researchEditorialRefId(reference),
    })
  }

  for (const item of associativePackage.screenedRelations.items) {
    const serieA = sourceSeriesMap.get(item.aSeriesKey)
    const serieB = sourceSeriesMap.get(item.bSeriesKey)
    invariant(serieA !== undefined && serieB !== undefined, 'editorial referencia relação triada ausente.')
    if (expectedSalience(serieA, serieB, item.window) === 'note') {
      noteCount += 1
      continue
    }
    const reference = { kind: 'screened', relationId: item.relationId }
    ranked.push({
      reference,
      absPearson: Math.abs(computePearsonDelta(serieA.points, serieB.points, item.window)),
      refId: researchEditorialRefId(reference),
    })
  }

  ranked.sort((left, right) => {
    if (left.absPearson !== right.absPearson) return right.absPearson - left.absPearson
    return left.refId === right.refId ? 0 : left.refId < right.refId ? -1 : 1
  })
  return {
    leads: [...structural, ...ranked.map((entry) => entry.reference)],
    noteCount,
  }
}

export function verifyAssociativePackage({
  associativePackage,
  sourcePackage,
  sourcePackageSha256,
  sourceRelative,
  registryRegion,
  allRegionPackageSha256,
  allSourcePackagesBySlug,
}) {
  assertExactKeys(associativePackage, [
    'associations',
    'decompositions',
    'editorial',
    'generation',
    'grammarVersion',
    'laggedPairs',
    'method',
    'provenance',
    'region',
    'schemaVersion',
    'screenedRelations',
    'temporalPairs',
  ], `pacote associativo de "${registryRegion.slug}"`)
  invariant(
    associativePackage.schemaVersion === ASSOCIATIVE_PACKAGE_SCHEMA,
    `o pacote associativo de "${registryRegion.slug}" traz schema desconhecido.`,
  )
  invariant(
    associativePackage.grammarVersion === ASSOCIATIVE_GRAMMAR_VERSION,
    `o pacote associativo de "${registryRegion.slug}" traz grammarVersion desconhecida.`,
  )
  invariant(
    associativePackage.method?.methodNote === ASSOCIATIVE_METHOD_NOTE,
    `o pacote associativo de "${registryRegion.slug}" altera a nota metodológica fechada.`,
  )
  invariant(
    associativePackage.generation?.deterministic === true
      && associativePackage.generation.networkUsed === false
      && associativePackage.generation.clockUsed === false
      && associativePackage.generation.modelUsed === false,
    `o pacote associativo de "${registryRegion.slug}" não se declara determinístico.`,
  )
  invariant(
    associativePackage.region.slug === registryRegion.slug
      && associativePackage.region.name === registryRegion.name
      && associativePackage.region.uf === registryRegion.uf
      && associativePackage.region.municipalityCount === registryRegion.municipalityCount
      && associativePackage.region.registrySha256 === sourcePackage.region.registrySha256,
    `a identidade do pacote associativo diverge do registro em "${registryRegion.slug}".`,
  )
  invariant(
    associativePackage.provenance?.regionPackageRef === sourceRelative,
    `o pacote associativo de "${registryRegion.slug}" referencia outro pacote regional.`,
  )
  invariant(
    associativePackage.provenance.regionPackageSha256 === sourcePackageSha256,
    `o pacote associativo de "${registryRegion.slug}" não referencia o sha256 do pacote `
    + 'regional correspondente no manifesto.',
  )
  assertCanonicalEqual(
    associativePackage.provenance.allRegionPackagesSha256,
    allRegionPackageSha256,
    `pacote associativo de "${registryRegion.slug}".provenance.allRegionPackagesSha256`,
  )

  const sourceSeriesMap = sourceSeriesByKey(sourcePackage, `pacote regional de "${registryRegion.slug}"`)
  validateSourceDecompositions(
    associativePackage.decompositions,
    `pacote associativo de "${registryRegion.slug}".decompositions`,
  )
  assertCanonicalEqual(
    associativePackage.method?.decompositionCriteria,
    RESEARCH_DECOMPOSITION_CRITERIA,
    `pacote associativo de "${registryRegion.slug}".method.decompositionCriteria`,
  )
  const screeningLabel = `pacote associativo de "${registryRegion.slug}".screenedRelations.criteria`
  const excludedSeries = validateResearchScreeningCriteria(
    associativePackage.screenedRelations?.criteria,
    sourceSeriesMap,
    screeningLabel,
  )
  assertCanonicalEqual(
    associativePackage.method?.screeningCriteria,
    associativePackage.screenedRelations.criteria,
    `pacote associativo de "${registryRegion.slug}".method.screeningCriteria`,
  )
  assertCanonicalEqual(
    associativePackage.method?.editorialCriteria,
    EDITORIAL_READING_CRITERIA,
    `pacote associativo de "${registryRegion.slug}".method.editorialCriteria`,
  )
  assertCanonicalEqual(
    associativePackage.editorial?.criteria,
    EDITORIAL_READING_CRITERIA,
    `pacote associativo de "${registryRegion.slug}".editorial.criteria`,
  )
  invariant(
    associativePackage.associations.length === sourcePackage.associations.length,
    `o pacote associativo de "${registryRegion.slug}" não cobre todas as associações.`,
  )
  sourcePackage.associations.forEach((association, index) => {
    const reading = associativePackage.associations[index]
    const label = `pacote associativo.associations[${index}]`
    invariant(reading.associationKey === association.associationKey,
      `${label}.associationKey diverge da associação regional correspondente.`)
    invariant(reading.window.start === association.window.start
      && reading.window.end === association.window.end,
    `${label}.window diverge da associação regional correspondente.`)
    invariant(reading.factorReadings.length === association.territorialFactors.length,
      `${label}.factorReadings não cobre todos os fatores territoriais.`)
    const outcome = sourceSeriesMap.get(association.educationOutcome.seriesKey)
    invariant(outcome !== undefined, `${label} referencia resultado educacional ausente.`)
    reading.factorReadings.forEach((factorReading, factorIndex) => {
      const factorRef = association.territorialFactors[factorIndex]
      invariant(
        factorReading.outcomeSeriesKey === association.educationOutcome.seriesKey
          && factorReading.factorSeriesKey === factorRef.seriesKey,
        `${label}.factorReadings[${factorIndex}] diverge da ordem curada.`,
      )
      const factor = sourceSeriesMap.get(factorRef.seriesKey)
      invariant(factor !== undefined, `${label} referencia fator territorial ausente.`)
      verifyComparisonReading({
        reading: factorReading,
        serieA: outcome,
        serieB: factor,
        window: association.window,
        roles: ['outcome', 'factor'],
        label: `${label}.factorReadings[${factorIndex}]`,
      })
    })
    assertCanonicalEqual(
      reading.stateContrast,
      expectedStateContrast({
        seriesKey: association.educationOutcome.seriesKey,
        window: association.window,
        regionSlug: registryRegion.slug,
        allSourcePackagesBySlug,
      }),
      `${label}.stateContrast`,
    )
  })

  invariant(
    associativePackage.temporalPairs.length === sourcePackage.temporalPairs.length,
    `o pacote associativo de "${registryRegion.slug}" não cobre todos os pares temporais.`,
  )
  sourcePackage.temporalPairs.forEach((pair, index) => {
    const reading = associativePackage.temporalPairs[index]
    const label = `pacote associativo.temporalPairs[${index}]`
    invariant(reading.pairKey === pair.pairKey, `${label}.pairKey diverge do par regional.`)
    invariant(reading.window.start === pair.window.start && reading.window.end === pair.window.end,
      `${label}.window diverge do par regional.`)
    const serieA = sourceSeriesMap.get(pair.seriesKeyA)
    const serieB = sourceSeriesMap.get(pair.seriesKeyB)
    invariant(serieA !== undefined && serieB !== undefined, `${label} referencia série ausente.`)
    verifyComparisonReading({
      reading,
      serieA,
      serieB,
      window: pair.window,
      roles: ['a', 'b'],
      label,
    })
    assertCanonicalEqual(
      reading.stateContrast,
      expectedStateContrast({
        seriesKey: pair.seriesKeyB,
        window: pair.window,
        regionSlug: registryRegion.slug,
        allSourcePackagesBySlug,
      }),
      `${label}.stateContrast`,
    )
  })

  invariant(
    Array.isArray(associativePackage.laggedPairs) && associativePackage.laggedPairs.length === 1,
    `o pacote associativo de "${registryRegion.slug}" deve trazer uma leitura defasada.`,
  )
  assertCanonicalEqual(
    associativePackage.laggedPairs[0],
    expectedLaggedPair(associativePackage.laggedPairs[0], sourceSeriesMap),
    'pacote associativo.laggedPairs[0]',
  )

  invariant(Array.isArray(associativePackage.screenedRelations.items),
    'pacote associativo.screenedRelations.items deve ser lista.')
  invariant(
    associativePackage.screenedRelations.items.length <= SCREENED_RELATIONS_CRITERIA.maxItems,
    `pacote associativo.screenedRelations.items excede o teto de ${SCREENED_RELATIONS_CRITERIA.maxItems}.`,
  )
  associativePackage.screenedRelations.items.forEach((item, index) => {
    const label = `pacote associativo.screenedRelations.items[${index}]`
    const serieA = sourceSeriesMap.get(item.aSeriesKey)
    const serieB = sourceSeriesMap.get(item.bSeriesKey)
    invariant(serieA !== undefined && serieB !== undefined, `${label} referencia série ausente.`)
    invariant(
      !excludedSeries.has(item.aSeriesKey),
      `${label}.aSeriesKey usa série excluída da elegibilidade da triagem: "${item.aSeriesKey}".`,
    )
    invariant(item.relationId === `${slugify(serieA.publicLabel)}--${slugify(serieB.publicLabel)}`,
      `${label}.relationId não deriva dos rótulos públicos.`)
    invariant(item.originStatement === SCREENED_ORIGIN_STATEMENT,
      `${label}.originStatement fora do contrato.`)
    verifyComparisonReading({
      reading: item,
      serieA,
      serieB,
      window: item.window,
      roles: ['a', 'b'],
      label,
    })
    const direction = computeDirectionConcordance(serieA.points, serieB.points, item.window)
    const pearson = computePearsonDelta(serieA.points, serieB.points, item.window)
    invariant(
      !Object.prototype.hasOwnProperty.call(direction, 'reasonCode')
        && direction.intervals >= SCREENED_RELATIONS_CRITERIA.minIntervals,
      `${label} não alcança o mínimo de intervalos da triagem.`,
    )
    invariant(
      pearson !== null && Math.abs(pearson) >= SCREENED_RELATIONS_CRITERIA.minAbsPearson,
      `${label} não alcança o piso de correlação da triagem.`,
    )
  })
  assertCanonicalEqual(
    associativePackage.editorial,
    {
      criteria: EDITORIAL_READING_CRITERIA,
      ...recomputeResearchEditorial(associativePackage, sourcePackage, sourceSeriesMap),
    },
    `pacote associativo de "${registryRegion.slug}".editorial`,
  )
  return associativePackage
}

function transposeLaggedItems(laggedPairs, seriesIdByKey) {
  return laggedPairs.map((pair, index) => {
    const base = {
      aSeriesId: resolveAssociativeSeriesId(
        pair.aSeriesKey, seriesIdByKey, `laggedPairs[${index}].aSeriesKey`),
      bSeriesId: resolveAssociativeSeriesId(
        pair.bSeriesKey, seriesIdByKey, `laggedPairs[${index}].bSeriesKey`),
      lagYears: pair.lagYears,
    }
    if (Object.prototype.hasOwnProperty.call(pair, 'reasonCode')) {
      return { ...base, reasonCode: pair.reasonCode, statement: pair.statement }
    }
    return {
      ...base,
      rationale: pair.rationale,
      windowA: { start: pair.windowA.start, end: pair.windowA.end },
      windowB: { start: pair.windowB.start, end: pair.windowB.end },
      intervals: pair.intervals,
      concordant: pair.concordant,
      opposite: pair.opposite,
      ties: pair.ties,
      correlation: transposeCorrelation(pair.correlation),
      statement: pair.statement,
      salience: pair.salience,
      grade: pair.grade,
      pneThemes: resolvePneThemes(
        [base.bSeriesId],
        `laggedPairs[${index}]`,
      ),
    }
  })
}

function transposeScreenedRelations(screenedRelations, seriesIdByKey) {
  return {
    ...SCREENED_RELATIONS_FRAMING,
    methodNote: ASSOCIATIVE_METHOD_NOTE,
    criteria: {
      ...SCREENED_RELATIONS_CRITERIA,
      excludedSeries: [...SCREENING_EXCLUDED_SERIES_IDS],
    },
    items: screenedRelations.items.map((item, index) => {
      const seriesAId = resolveAssociativeSeriesId(
        item.aSeriesKey, seriesIdByKey, `screenedRelations.items[${index}].aSeriesKey`)
      const seriesBId = resolveAssociativeSeriesId(
        item.bSeriesKey, seriesIdByKey, `screenedRelations.items[${index}].bSeriesKey`)
      return {
        relationId: item.relationId,
        seriesAId,
        seriesBId,
        window: { start: item.window.start, end: item.window.end },
        directionConcordance: transposeDirectionConcordance(item.directionConcordance),
        comovement: transposeComovement(
          item.comovement,
          ['a', 'b'],
          seriesIdByKey,
          `screenedRelations.items[${index}].comovement`,
        ),
        correlation: transposeCorrelation(item.correlation),
        originStatement: item.originStatement,
        salience: item.salience,
        grade: item.grade,
        pneThemes: resolvePneThemes([seriesBId], `screenedRelations.items[${index}]`),
      }
    }),
  }
}

function transposeEditorialReading({
  editorial,
  sourcePackage,
  associations,
  temporalPairs,
  seriesIdByKey,
}) {
  const associationIdByKey = new Map(sourcePackage.associations.map((association, index) => [
    association.associationKey,
    associations[index].associationId,
  ]))
  const pairIdByKey = new Map(sourcePackage.temporalPairs.map((pair, index) => [
    pair.pairKey,
    temporalPairs[index].pairId,
  ]))
  const leads = editorial.leads.map((reference, index) => {
    const label = `editorial.leads[${index}]`
    if (reference.kind === 'structural') {
      return {
        kind: reference.kind,
        aSeriesId: resolveAssociativeSeriesId(reference.aSeriesKey, seriesIdByKey, label),
        bSeriesId: resolveAssociativeSeriesId(reference.bSeriesKey, seriesIdByKey, label),
        lagYears: reference.lagYears,
      }
    }
    if (reference.kind === 'curated_association') {
      const associationId = associationIdByKey.get(reference.associationKey)
      invariant(associationId !== undefined, `${label} referencia associationKey ausente.`)
      return {
        kind: reference.kind,
        associationId,
        factorSeriesId: resolveAssociativeSeriesId(reference.factorSeriesKey, seriesIdByKey, label),
      }
    }
    if (reference.kind === 'curated_pair') {
      const pairId = pairIdByKey.get(reference.pairKey)
      invariant(pairId !== undefined, `${label} referencia pairKey ausente.`)
      return { kind: reference.kind, pairId }
    }
    invariant(reference.kind === 'screened', `${label}.kind fora do contrato editorial.`)
    return { kind: reference.kind, relationId: reference.relationId }
  })
  const leadsWithTitles = addStoryTitlesToEditorialReading(
    { leads },
    { associations, temporalPairs },
  ).leads
  return {
    criteria: {
      leadStrengths: [...EDITORIAL_READING_CRITERIA.leadStrengths],
      structuralAlwaysLead: EDITORIAL_READING_CRITERIA.structuralAlwaysLead,
      gradeEnum: [...EDITORIAL_READING_CRITERIA.gradeEnum],
      orderedBy: EDITORIAL_READING_CRITERIA.orderedBy,
    },
    criteriaStatement: EDITORIAL_CRITERIA_STATEMENT,
    leads: leadsWithTitles,
    noteCount: editorial.noteCount,
    noteStatement: renderEditorialNoteStatement(editorial.noteCount),
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
  associativePackage,
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
  const decompositions = transposeDecompositions({ associativePackage, sourcePackage })
  const framing = buildFraming(registryRegion.name)
  const publishesScenarios = scenarioPackage !== null
  const associations = sourcePackage.associations.map((association, index) =>
    transposeAssociation(association, associativePackage.associations[index], seriesIdByKey))
  const temporalPairs = sourcePackage.temporalPairs.map((pair, index) =>
    transposeTemporalPair(
      pair,
      associativePackage.temporalPairs[index],
      seriesIdByKey,
      labelByKey,
    ))
  const laggedItems = transposeLaggedItems(associativePackage.laggedPairs, seriesIdByKey)
  const screenedRelations = transposeScreenedRelations(
    associativePackage.screenedRelations,
    seriesIdByKey,
  )
  const editorialReading = transposeEditorialReading({
    editorial: associativePackage.editorial,
    sourcePackage,
    associations,
    temporalPairs,
    seriesIdByKey,
  })
  const hero = buildVocacoesHero({ series, associations, temporalPairs })
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
    hero,
    synthesis,
    territoryPortrait: { ...framing.territoryPortrait, series },
    decompositions,
    associations: {
      ...framing.associations,
      items: associations,
    },
    temporalPairs: {
      ...framing.temporalPairs,
      items: temporalPairs,
      laggedItems,
    },
    screenedRelations,
    editorialReading,
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
  invariant(
    verified.manifest.contractVersion === RESEARCH_CONTRACT_VERSION
      && verified.manifest.round === RESEARCH_ROUND,
    `o manifesto da origem não declara o contrato ${RESEARCH_CONTRACT_VERSION} e a rodada `
    + `${RESEARCH_ROUND}.`,
  )
  const verifiedApproval = verified.readVerifiedJson(PUBLIC_CONTRACT_APPROVAL_FILE)
  invariant(
    JSON.stringify(canonicalize(verifiedApproval)) === JSON.stringify(canonicalize(source.approval)),
    'o contrato público lido no handshake diverge do contrato sha-verificado pelo manifesto.',
  )
  invariant(
    verifiedApproval.supersedes === 'vocacoes-regiao-2.8.0'
      && verifiedApproval.approvedInRound === RESEARCH_ROUND
      && verifiedApproval.researchContractVersion === RESEARCH_CONTRACT_VERSION,
    'a aprovação do contrato público 2.9.0 não declara a sucessão e a rodada V5 R3 esperadas.',
  )
  const researchContract = verified.readVerifiedJson(RESEARCH_CONTRACT_FILE)
  invariant(
    researchContract.contractVersion === verified.manifest.contractVersion.replace(/^.*-/u, '')
      || verified.manifest.contractVersion.endsWith(researchContract.contractVersion),
    'a versão do contrato de pesquisa diverge do manifesto da origem.',
  )
  validateAssociativeResearchContract(researchContract)
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
  validateAssociativeApproval(verifiedApproval, registry)
  const approvedEditorial = validateEditorialLayer(verifiedApproval.editorialLayer, 'aprovação pública')
  assertCanonicalEqual(
    approvedEditorial,
    researchContract.editorialLayer,
    'aprovação pública.editorialLayer',
  )
  const approvedDecomposition = validateDecompositionLayer(
    verifiedApproval.decompositionLayer,
    'aprovação pública',
  )
  assertCanonicalEqual(
    approvedDecomposition,
    researchContract.decompositionLayer,
    'aprovação pública.decompositionLayer',
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

  /*
   * Os dez pacotes regionais são abertos antes da primeira região porque o
   * contraste estadual é uma estatística cruzada. A leitura associativa não
   * pode confiar no rank pronto da pesquisa: a plataforma o recompõe sobre
   * estes mesmos dez arquivos, todos sha-verificados pelo manifesto.
   */
  const orderedRegistryRegions = [...registry.regions].sort((left, right) =>
    left.slug.localeCompare(right.slug, 'en'))
  const regionalLayers = new Map()
  for (const registryRegion of orderedRegistryRegions) {
    const relative = `pacotes/regioes/${registryRegion.slug}.json`
    regionalLayers.set(registryRegion.slug, {
      relative,
      package: verified.readVerifiedJson(relative),
      sha256: verified.sha256Of(relative),
    })
  }
  const allSourcePackagesBySlug = new Map(
    orderedRegistryRegions.map((region) => [region.slug, regionalLayers.get(region.slug).package]),
  )
  const allRegionPackageSha256 = Object.fromEntries(
    orderedRegistryRegions.map((region) => [region.slug, regionalLayers.get(region.slug).sha256]),
  )
  const associativeLayers = new Map()
  for (const registryRegion of orderedRegistryRegions) {
    const associativeRelative = ASSOCIATIVE_LAYER_PACKAGE_PATTERN.replace(
      '{regionSlug}', registryRegion.slug)
    invariant(
      verified.declares(associativeRelative),
      `o manifesto da origem não declara o pacote associativo "${associativeRelative}".`,
    )
    const regional = regionalLayers.get(registryRegion.slug)
    const associativePackage = verified.readVerifiedJson(associativeRelative)
    verifyAssociativePackage({
      associativePackage,
      sourcePackage: regional.package,
      sourcePackageSha256: regional.sha256,
      sourceRelative: regional.relative,
      registryRegion,
      allRegionPackageSha256,
      allSourcePackagesBySlug,
    })
    associativeLayers.set(registryRegion.slug, associativePackage)
  }

  for (const registryRegion of orderedRegistryRegions) {
    const regional = regionalLayers.get(registryRegion.slug)
    const relative = regional.relative
    const sourcePackage = regional.package
    const associativePackage = associativeLayers.get(registryRegion.slug)

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
      sourcePackageSha256: regional.sha256,
      associativePackage,
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
      'relacoes-observadas-por-triagem',
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
      'Toda associação e todo par temporal publica leitura associativa quantificada; as frases '
      + 'são recompostas dos números e os ranks estaduais são recomputados sobre as dez regiões.',
      'Correlação aparece somente na gramática fechada da leitura associativa, sem p-valor, '
      + 'inferência causal ou projeção.',
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
