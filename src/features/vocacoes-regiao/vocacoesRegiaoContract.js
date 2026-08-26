/*
 * Contrato público do Vocações da Região — `vocacoes-regiao-2.1.0`.
 *
 * Quatro blocos por região: retrato e transformações do território (Bloco 1),
 * leitura associativa entre educação e território (Bloco 2), comparação
 * temporal em pares curados (Bloco 3) e **cenários da região (Bloco 4)**.
 *
 * O `2.1.0` é **aditivo** sobre o `2.0.0`: nenhum campo dos três primeiros
 * blocos mudou de forma, de nome ou de regra. O que entra é um campo novo no
 * documento, `scenarios`, e nada mais.
 *
 * O Bloco 4 não é um campo opcional deixado vazio nas regiões sem cenário. Ele
 * é obrigatório em todas as dez, e **declara em qual dos dois estados está**:
 * publicado, com o bloco inteiro; ou ausente, com a frase que diz ao leitor que
 * ali não há cenários e por quê. Campo opcional deixaria a ausência silenciosa,
 * e ausência silenciosa é indistinguível de bloco que se perdeu no caminho.
 *
 * **Os quatro cenários de uma região não têm o mesmo peso.** Três são
 * exploratórios e um é normativo, e o estatuto de cada um é campo obrigatório
 * do contrato — decisão `D3` do plano. A regra pública da família municipal
 * (`foresight-educacao`), em que os quatro cenários têm peso igual, permanece
 * intacta e **não vale aqui**: são duas famílias, com duas metodologias e duas
 * regras públicas próprias, e o `schema.json` de cada uma declara a sua.
 *
 * Por que este contrato não é o dos Cenários municipais: até a versão `1.0.0`
 * o slot regional emprestava a fábrica de validador do foresight, porque o
 * pacote regional projetado era a transposição literal do municipal — mesma
 * forma, identidade trocada. A Fase A não é isso. O corpo do documento é
 * disjunto do corpo do foresight: onde lá há cenários, sinais e condições
 * partilhadas, aqui há séries, associações e pares. Alargar a fábrica do
 * foresight para caber nos dois relaxaria o contrato municipal — um pacote
 * municipal sem cenários passaria a ser válido. O contrato regional é próprio,
 * e o que ele compartilha com o municipal é a disciplina, não os campos:
 * conjunto de campos fechado em todo nível, texto não vazio, ausência
 * declarada em vez de valor inventado, e recusa em vez de tolerância.
 *
 * Fechado significa fechado: campo desconhecido em qualquer nível — documento,
 * região, bloco, série, ponto, associação, par — é recusa, não campo ignorado.
 * É o padrão do `matriz-4.0.0`, e existe porque o modo mais silencioso de um
 * artefato mentir é trazer um campo que ninguém valida e alguém renderiza.
 */

export const VOCACOES_DOCUMENT_SCHEMA = 'vocacoes-regiao-2.1.0'

/** Classes de evidência aceitas, e a frase pública de cada uma. */
export const EVIDENCE_CLASS_LABELS = Object.freeze({
  observed: 'Observado na fonte.',
  preliminary: 'Prévia da fonte, sujeita a revisão.',
  calculated: 'Calculado a partir de séries observadas.',
  estimated_indirect: 'Estimativa indireta.',
})

/** Regras de agregação aceitas, e a frase pública de cada uma. */
export const AGGREGATION_LABELS = Object.freeze({
  sum: 'Soma dos municípios da região.',
  ratio_of_sums: 'Soma dos numeradores dividida pela soma dos denominadores.',
  regional_native: 'Publicado pela fonte já no recorte da região.',
})

/*
 * Universos aceitos, e a frase pública de cada um.
 *
 * A divisão de trabalho é esta: a camada de pesquisa **declara** o universo de
 * cada série, por enum fechado; a plataforma **escreve** a frase que o leitor
 * lê. O enum não chega ao público — `cadastral_registry` é vocabulário de
 * processo, e o plano proíbe enum de processo em texto público.
 *
 * Por que a frase não vem da origem junto com o enum: ela vem, e é por isso
 * que esta tabela existe. As frases do contrato da pesquisa estão escritas sem
 * acento, porque nasceram do lado Python da fronteira. Publicá-las como estão
 * poria português sem acento na tela. O gerador confere que esta tabela cobre
 * todo enum que a origem declara — origem que inventar um universo novo não
 * publica, em vez de publicar sem frase.
 */
export const UNIVERSE_LABELS = Object.freeze({
  cadastral_registry:
    'Universo cadastral: pessoas e famílias inscritas no cadastro, tal como o cadastro as '
    + 'registra. Não é a população da região nem uma taxa sobre ela.',
  resident_population:
    'Universo populacional: pessoas residentes na região, conforme a fonte demográfica declarada.',
  live_births:
    'Universo de nascimentos: nascidos vivos por residência da mãe, conforme a fonte declarada.',
  formal_employment_links:
    'Universo de vínculos: vínculos formais de emprego declarados à fonte administrativa.',
  school_enrollments: 'Universo de matrículas: matrículas declaradas ao censo escolar.',
  establishments: 'Universo de estabelecimentos: unidades declaradas à fonte administrativa.',
})

const UNIVERSE_LABEL_VALUES = Object.freeze(Object.values(UNIVERSE_LABELS))

/*
 * Estatuto do cenário, e a frase pública de cada um.
 *
 * Mesma divisão de trabalho do universo: a camada de pesquisa **declara** o
 * estatuto por enum fechado, e a plataforma **escreve** a frase que o leitor lê.
 * Aqui isso não é preferência de estilo — é o que impede a assimetria de virar
 * detalhe editorial. Os dois pacotes promovidos na Rodada 9 chegaram com frases
 * de estatuto **diferentes entre si** para o mesmo enum; publicá-las como
 * vieram faria o mesmo estatuto significar duas coisas em duas páginas da mesma
 * divisão.
 *
 * A frase do normativo diz, ela mesma, que ele não é previsão nem compromisso:
 * um cenário que descreve um ideal técnico e é lido como plano aprovado é o
 * modo mais provável de esta página enganar alguém.
 */
export const SCENARIO_STATUTE_LABELS = Object.freeze({
  exploratory:
    'Cenário exploratório: descreve uma configuração possível do território, sem preferência '
    + 'declarada entre ela e as outras, e sem probabilidade atribuída.',
  normative:
    'Cenário normativo: descreve um ideal técnico provisório, e não uma configuração prevista. '
    + 'Não é previsão, não é compromisso e não foi pactuado com ninguém.',
})

export const SCENARIO_STATUTES = Object.freeze(Object.keys(SCENARIO_STATUTE_LABELS))

/*
 * Direção observada da âncora, e a frase pública de cada uma.
 *
 * O enum da origem (`alta`, `baixa`, `estabilidade`) não chega ao público: é
 * vocabulário de processo. O que chega é a frase — e o contrato confere que ela
 * **não contradiz os dois valores da própria âncora**: quem diz alta precisa
 * terminar acima de onde começou, e quem diz baixa precisa terminar abaixo.
 *
 * A estabilidade não recebe conferência de sinal, e o motivo está declarado: a
 * origem a atribui por limiar percentual, e o limiar é da camada de pesquisa. A
 * plataforma não o conhece e não vai adivinhá-lo — conferir sinal estrito aqui
 * recusaria uma série honesta que variou meio por cento.
 */
export const SCENARIO_DIRECTION_LABELS = Object.freeze({
  alta: 'com alta observada na janela',
  baixa: 'com baixa observada na janela',
  estabilidade: 'sem mudança de sentido observada na janela',
})

const SCENARIO_DIRECTION_LABEL_VALUES = Object.freeze(Object.values(SCENARIO_DIRECTION_LABELS))
const SCENARIO_DIRECTION_RISING = SCENARIO_DIRECTION_LABELS.alta
const SCENARIO_DIRECTION_FALLING = SCENARIO_DIRECTION_LABELS.baixa

/** Estados possíveis do Bloco 4 numa região. Não há terceiro. */
export const SCENARIO_BLOCK_STATUSES = Object.freeze(['published', 'absent'])

/*
 * A moldura editorial do Bloco 4, palavra por palavra — e é o contrato que a
 * guarda, não o gerador.
 *
 * A revisão adversarial do `2.1.0` mostrou por quê. As duas implicações de
 * estado eram conferidas nos dois sentidos e ainda assim este documento
 * passava:
 *
 *     { "status": "absent", "block": null, "statuteReadingNote": null,
 *       "absenceStatement": "Há quatro cenários publicados nesta região." }
 *
 * Forma coerente, frase mentindo. `absenceStatement` era texto livre, e texto
 * livre prova que existe uma frase — não que a frase declara ausência. O mesmo
 * valia para `description`, que podia dizer o oposto do estado em qualquer um
 * dos dois lados.
 *
 * A correção é a mesma que a Fase A aplicou ao universo da série: a camada de
 * pesquisa declara o **estado**, e a frase que o leitor lê é renderizada de uma
 * tabela fechada. Uma frase que não está aqui não é publicável, e por isso não
 * existe frase de ausência que afirme presença.
 */
export const SCENARIO_FRAMING = Object.freeze({
  label: 'Cenários da região',
  publishedDescription:
    'Quatro configurações possíveis para o território e para a educação dele no horizonte '
    + 'declarado, construídas a partir das mesmas séries que estão nesta página. Cada cenário '
    + 'declara de onde parte, o que o distingue dos outros três e o que ele pede de quem '
    + 'planeja a educação da região.',
  absentDescription:
    'Os cenários regionais são construídos região a região, a partir das séries de cada '
    + 'território. Esta região ainda não os tem.',
  statuteReadingNote:
    'Os quatro cenários desta página não têm o mesmo peso, e essa é a diferença mais '
    + 'importante entre eles. Três são exploratórios: descrevem configurações possíveis do '
    + 'território, sem preferência declarada entre elas. O quarto é normativo: descreve um '
    + 'ideal técnico provisório, que não é previsão, não foi pactuado com ninguém e não '
    + 'descreve nada que esteja decidido. O estatuto de cada cenário vem escrito nele mesmo.',
  absenceStatement:
    'Esta região ainda não tem cenários publicados. Os cenários regionais foram construídos, '
    + 'até aqui, para duas regiões do estado, e esta não é uma delas. O que está publicado '
    + 'nesta página são os três blocos anteriores: o retrato do território, a leitura entre '
    + 'educação e território, e as transformações simultâneas.',
})

export const EVIDENCE_CLASSES = Object.freeze(Object.keys(EVIDENCE_CLASS_LABELS))
export const AGGREGATION_RULES = Object.freeze(Object.keys(AGGREGATION_LABELS))
export const PERIOD_GRANULARITIES = Object.freeze(['annual', 'monthly'])

/*
 * Identificador público de série, associação e par.
 *
 * A primeira versão conferia só o formato, e a revisão adversarial mostrou o
 * que o formato sozinho permite: `cadastro-social-familias-inscritas` é
 * kebab-case perfeito e é a chave interna transcodificada, e
 * `regiao-fiergs-matriculas` é kebab-case e carrega um nome institucional que o
 * contrato de origem proíbe em texto público. Formato não é procedência.
 *
 * O identificador agora precisa **ser** o slug do rótulo. Isso não é uma
 * conferência a mais: é a única que prova a procedência, porque um
 * identificador que sai do rótulo não pode carregar nada que o rótulo não
 * carregue — e o rótulo passa pela guarda de linguagem inteira.
 *
 * `slugify` mora aqui, e não no gerador, exatamente por isso: as duas pontas
 * precisam da mesma função, e o leitor precisa dela no navegador.
 */
const PUBLIC_ID_PATTERN = /^[a-z0-9]+(?:-[a-z0-9]+)*$/

/** Nome institucional do recorte: proibido em texto público, e no identificador. */
const FORBIDDEN_ID_TOKENS = Object.freeze(['fiergs', 'senai', 'sesi'])

/**
 * Slug de rota derivado do rótulo público. Determinística, sem dependências, e
 * idêntica nas duas pontas da fronteira — o gerador a importa daqui.
 */
export function slugify(value) {
  const slug = String(value)
    .normalize('NFD')
    .replace(/\p{Diacritic}/gu, '')
    .toLocaleLowerCase('pt-BR')
    .replace(/[^a-z0-9]+/gu, '-')
    .replace(/^-+|-+$/gu, '')
  invariant(slug.length > 0, `não foi possível derivar um identificador público de "${value}".`)
  return slug
}

const SHA256_PATTERN = /^[a-f0-9]{64}$/
const SLUG_PATTERN = /^[a-z0-9]+(?:-[a-z0-9]+)*$/
const UF_PATTERN = /^[A-Z]{2}$/
const ISO_DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/

const DOCUMENT_FIELDS = new Set([
  'schemaVersion',
  'contentVersion',
  'generatedAt',
  'generatorVersion',
  'sourceVersion',
  'sourceMethodologyStatus',
  'publicationScope',
  'region',
  'page',
  'howToRead',
  'territoryPortrait',
  'associations',
  'temporalPairs',
  'scenarios',
  'sources',
  'limitations',
  'provenance',
])

const REGION_FIELDS = new Set(['slug', 'name', 'uf', 'municipalityCount'])
const PAGE_FIELDS = new Set(['eyebrow', 'title', 'description', 'neutralityNote'])
const TEXT_BLOCK_FIELDS = new Set(['label', 'description', 'items'])
const PORTRAIT_FIELDS = new Set(['label', 'description', 'series'])
const WINDOW_FIELDS = new Set(['start', 'end'])
const RATIO_FIELDS = new Set(['numeratorLabel', 'denominatorLabel'])
/*
 * Os dois campos de cenário fecham a cadeia até o esqueleto congelado da rodada
 * que os construiu, e são `null` nas regiões sem cenário. Sem eles, o documento
 * publicado provaria a procedência dos três primeiros blocos e nenhuma do
 * quarto — que é justamente o bloco em que a procedência mais importa.
 */
const PROVENANCE_FIELDS = new Set([
  'sourcePackageSha256',
  'sourceContractVersion',
  'sourceBuilderVersion',
  'sourceGeneratedAt',
  'registrySha256',
  'scenarioPackageSha256',
  'scenarioSourceSha256',
])

const SERIES_FIELDS = new Set([
  'seriesId',
  'label',
  'unitLabel',
  'sourceLabel',
  'evidenceClass',
  'evidenceLabel',
  'universeLabel',
  'aggregationLabel',
  'ratioOf',
  'periodGranularity',
  'periodStart',
  'periodEnd',
  'periodLabel',
  'preliminaryPeriods',
  'limitations',
  'points',
])
const POINT_FIELDS = new Set(['period', 'value', 'evidenceClass'])

const ASSOCIATION_FIELDS = new Set([
  'associationId',
  'label',
  'window',
  'periodLabel',
  'educationOutcome',
  'territorialFactors',
  'observedStatement',
  'allowedInterpretation',
  'prohibitedClaim',
  'hypotheses',
])
const SERIES_REF_FIELDS = new Set(['seriesId', 'label'])

const TEMPORAL_PAIR_FIELDS = new Set([
  'pairId',
  'label',
  'window',
  'periodLabel',
  'seriesA',
  'seriesB',
  'observedStatement',
  'prohibitedClaim',
])

const SOURCE_ITEM_FIELDS = new Set(['label', 'periodLabel'])

/*
 * Bloco 4 — cenários da região.
 *
 * `label`, `description` e `statuteReadingNote` são moldura editorial desta
 * camada e existem nas dez regiões, com ou sem cenário. `status` diz em qual
 * estado o bloco está, e os outros dois campos são a consequência exata dele:
 * ausente traz frase de ausência e `block` nulo; publicado traz `block` e
 * frase de ausência nula. As duas implicações são conferidas nos dois sentidos.
 */
const SCENARIOS_FIELDS = new Set([
  'label',
  'description',
  'statuteReadingNote',
  'status',
  'absenceStatement',
  'block',
])

const SCENARIO_BLOCK_FIELDS = new Set([
  'methodologyLabel',
  'focalQuestion',
  'maturityNote',
  'statuteNote',
  'baseYear',
  'targetYear',
  'longScanTargetYear',
  'baseYearStatement',
  'horizonStatement',
  'longScanStatement',
  'compatibilityCeilingStatement',
  'items',
  'normativeCriteria',
  'realizationConditions',
  'robustImplications',
  'conditionalImplication',
  'prohibitedClaim',
])

const SCENARIO_ITEM_FIELDS = new Set([
  'scenarioId',
  'order',
  'profileLabel',
  'title',
  'statute',
  'statuteLabel',
  'centralMechanism',
  'startingPointStatement',
  'trajectoryStatement',
  'stateAtHorizonStatement',
  'anchors',
  'educationImplications',
  'contraryEvidence',
  'limits',
  'prohibitedClaim',
])

const SCENARIO_ANCHOR_FIELDS = new Set([
  'seriesId',
  'label',
  'window',
  'periodLabel',
  'startValue',
  'endValue',
  'directionLabel',
])

const SCENARIO_IMPLICATION_FIELDS = new Set(['stageLabel', 'statement'])

const NORMATIVE_CRITERION_FIELDS = new Set([
  'order',
  'publicName',
  'definition',
  'requiredState',
  'tradeOff',
  'failureMode',
  'whatToFollow',
])

/*
 * A alegação proibida é publicada como frase inteira, composta com o abridor
 * fixo da camada de pesquisa. Conferir o abridor aqui é a segunda camada: se o
 * gerador algum dia compuser errado, o leitor recusa em vez de renderizar uma
 * proibição que virou afirmação.
 */
export const PROHIBITED_CLAIM_OPENER = 'Não se pode concluir que '

export class VocacoesContractError extends Error {
  constructor(message) {
    super(message)
    this.name = 'VocacoesContractError'
  }
}

function invariant(condition, message) {
  if (!condition) throw new VocacoesContractError(message)
}

function isRecord(value) {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function validateExactFields(value, allowed, label) {
  invariant(isRecord(value), `${label} deve ser um objeto.`)
  const keys = Object.keys(value)
  const unexpected = keys.filter((key) => !allowed.has(key))
  const missing = [...allowed].filter((key) => !keys.includes(key))
  invariant(
    unexpected.length === 0,
    `${label} traz campo desconhecido fora do contrato: ${unexpected.join(', ')}.`,
  )
  invariant(
    missing.length === 0,
    `${label} não traz os campos obrigatórios: ${missing.join(', ')}.`,
  )
}

function validateText(value, label) {
  invariant(
    typeof value === 'string' && value.trim() !== '',
    `${label} deve ser texto não vazio.`,
  )
  return value
}

function validateTextList(value, label, { minimum = 1 } = {}) {
  invariant(Array.isArray(value), `${label} deve ser uma lista.`)
  invariant(value.length >= minimum, `${label} deve trazer ao menos ${minimum} item.`)
  value.forEach((item, index) => validateText(item, `${label}[${index}]`))
  return value
}

function validatePublicId(value, label, derivedFrom = null) {
  invariant(
    typeof value === 'string' && PUBLIC_ID_PATTERN.test(value),
    `${label} deve ser um identificador público derivado do rótulo.`,
  )
  for (const token of FORBIDDEN_ID_TOKENS) {
    invariant(
      !value.includes(token),
      `${label} expõe o nome institucional "${token}".`,
    )
  }
  if (derivedFrom !== null) {
    invariant(
      value === slugify(derivedFrom),
      `${label} não é o identificador do rótulo que ele nomeia `
      + `(esperado "${slugify(derivedFrom)}", recebido "${value}").`,
    )
  }
  return value
}

function validateWindow(value, label, referenceYear) {
  validateExactFields(value, WINDOW_FIELDS, label)
  invariant(Number.isInteger(value.start), `${label}.start deve ser inteiro.`)
  invariant(Number.isInteger(value.end), `${label}.end deve ser inteiro.`)
  invariant(value.end >= value.start, `${label}.end não pode preceder ${label}.start.`)
  /*
   * A janela também é um período, e a regra do período futuro vale para ela.
   * Sem esta linha, `{start: 2026, end: 2099}` passava — a revisão adversarial
   * a encontrou junto com a interseção frouxa, e as duas juntas publicavam uma
   * associação declarando alcançar setenta e três anos que não existem.
   */
  invariant(
    value.end <= referenceYear,
    `${label}.end ultrapassa o ano de referência do documento.`,
  )
  return value
}

/** Identidade regional: o que substitui o município no pacote transposto. */
export function validateRegionIdentity(value, label) {
  validateExactFields(value, REGION_FIELDS, label)
  invariant(
    typeof value.slug === 'string' && SLUG_PATTERN.test(value.slug),
    `${label}.slug deve ser um slug de rota.`,
  )
  validateText(value.name, `${label}.name`)
  invariant(
    typeof value.uf === 'string' && UF_PATTERN.test(value.uf),
    `${label}.uf deve ter duas letras maiúsculas.`,
  )
  invariant(
    Number.isInteger(value.municipalityCount) && value.municipalityCount > 0,
    `${label}.municipalityCount deve ser inteiro positivo.`,
  )
  return value
}

/*
 * Período: ano de quatro dígitos na série anual, AAAAMM na mensal. Sem valor
 * padrão — a granularidade é declarada pela série, porque um default silencioso
 * é como uma série mensal viraria anual sem ninguém notar.
 */
function validatePeriod(value, granularity, label) {
  invariant(Number.isInteger(value), `${label} deve ser inteiro.`)
  if (granularity === 'annual') {
    invariant(value >= 1900 && value <= 2999, `${label} deve ser um ano de quatro dígitos.`)
    return value
  }
  const year = Math.floor(value / 100)
  const month = value % 100
  invariant(
    year >= 1900 && year <= 2999 && month >= 1 && month <= 12,
    `${label} deve estar no formato AAAAMM.`,
  )
  return value
}

function validateSeries(candidate, label, referenceYear, referenceMonth) {
  validateExactFields(candidate, SERIES_FIELDS, label)
  validateText(candidate.label, `${label}.label`)
  validatePublicId(candidate.seriesId, `${label}.seriesId`, candidate.label)
  validateText(candidate.unitLabel, `${label}.unitLabel`)
  validateText(candidate.sourceLabel, `${label}.sourceLabel`)
  validateText(candidate.periodLabel, `${label}.periodLabel`)

  invariant(
    EVIDENCE_CLASSES.includes(candidate.evidenceClass),
    `${label}.evidenceClass fora do contrato: ${candidate.evidenceClass}.`,
  )
  /*
   * A frase da classe é renderizada do enum, nunca escrita à mão. Guardar as
   * duas e exigir que concordem impede o caso em que a classe diz uma coisa e
   * a frase que o leitor lê diz outra.
   */
  invariant(
    candidate.evidenceLabel === EVIDENCE_CLASS_LABELS[candidate.evidenceClass],
    `${label}.evidenceLabel não é a frase declarada para a classe ${candidate.evidenceClass}.`,
  )
  invariant(
    Object.values(AGGREGATION_LABELS).includes(candidate.aggregationLabel),
    `${label}.aggregationLabel fora do contrato.`,
  )

  /*
   * Universo ausente é `null` explícito, não campo omitido: séries de PIB e de
   * exportação não têm universo de pessoas, e dizer isso é diferente de
   * esquecer de dizer.
   */
  invariant(
    candidate.universeLabel === null || UNIVERSE_LABEL_VALUES.includes(candidate.universeLabel),
    `${label}.universeLabel não é null nem uma das frases de universo do contrato.`,
  )

  /*
   * Razão entre somas e `ratioOf` são a mesma informação dita duas vezes, e por
   * isso a implicação vale nos dois sentidos. A primeira versão exigia só um
   * deles: uma série podia declarar-se razão entre somas e não dizer entre o
   * quê — a revisão adversarial mostrou o caso.
   */
  const declaresRatio = candidate.aggregationLabel === AGGREGATION_LABELS.ratio_of_sums
  invariant(
    declaresRatio === (candidate.ratioOf !== null),
    `${label}: razão entre somas e ${label}.ratioOf precisam concordar.`,
  )
  if (candidate.ratioOf !== null) {
    validateExactFields(candidate.ratioOf, RATIO_FIELDS, `${label}.ratioOf`)
    validateText(candidate.ratioOf.numeratorLabel, `${label}.ratioOf.numeratorLabel`)
    validateText(candidate.ratioOf.denominatorLabel, `${label}.ratioOf.denominatorLabel`)
  }

  invariant(
    PERIOD_GRANULARITIES.includes(candidate.periodGranularity),
    `${label}.periodGranularity fora do contrato.`,
  )
  const granularity = candidate.periodGranularity
  validatePeriod(candidate.periodStart, granularity, `${label}.periodStart`)
  validatePeriod(candidate.periodEnd, granularity, `${label}.periodEnd`)
  invariant(
    candidate.periodEnd >= candidate.periodStart,
    `${label}.periodEnd não pode preceder ${label}.periodStart.`,
  )

  validateTextList(candidate.limitations, `${label}.limitations`, { minimum: 0 })

  invariant(Array.isArray(candidate.preliminaryPeriods), `${label}.preliminaryPeriods deve ser uma lista.`)
  const preliminary = new Set()
  candidate.preliminaryPeriods.forEach((period, index) => {
    validatePeriod(period, granularity, `${label}.preliminaryPeriods[${index}]`)
    invariant(
      !preliminary.has(period),
      `${label}.preliminaryPeriods repete o período ${period}.`,
    )
    preliminary.add(period)
  })

  invariant(
    Array.isArray(candidate.points) && candidate.points.length > 0,
    `${label}.points deve trazer ao menos um ponto.`,
  )
  const seen = new Set()
  let previous = null
  candidate.points.forEach((point, index) => {
    const pointLabel = `${label}.points[${index}]`
    validateExactFields(point, POINT_FIELDS, pointLabel)
    validatePeriod(point.period, granularity, `${pointLabel}.period`)
    invariant(!seen.has(point.period), `${pointLabel}.period repetido: ${point.period}.`)
    seen.add(point.period)
    invariant(
      previous === null || point.period > previous,
      `${pointLabel}.period fora de ordem crescente.`,
    )
    previous = point.period
    invariant(
      point.period >= candidate.periodStart && point.period <= candidate.periodEnd,
      `${pointLabel}.period está fora da janela declarada pela série.`,
    )
    invariant(
      typeof point.value === 'number' && Number.isFinite(point.value),
      `${pointLabel}.value deve ser um número finito.`,
    )
    invariant(
      EVIDENCE_CLASSES.includes(point.evidenceClass),
      `${pointLabel}.evidenceClass fora do contrato.`,
    )
    /*
     * A regra herdada da rodada 5C do foresight municipal, e o risco 9 do
     * plano: prévia nunca vira observação. O período declarado como prévia
     * chega ao leitor com a classe `preliminary` — se chegasse como
     * `observed`, a página o desenharia como dado fechado.
     */
    if (preliminary.has(point.period)) {
      invariant(
        point.evidenceClass === 'preliminary',
        `${pointLabel} está em período de prévia e não pode ter classe ${point.evidenceClass}.`,
      )
    } else {
      invariant(
        point.evidenceClass !== 'preliminary',
        `${pointLabel} tem classe de prévia sem que o período conste em ${label}.preliminaryPeriods.`,
      )
    }
  })

  for (const period of preliminary) {
    invariant(
      seen.has(period),
      `${label}.preliminaryPeriods declara ${period} sem ponto correspondente.`,
    )
  }

  /*
   * Nenhum número atribuído a período futuro. O corte é o ano de referência do
   * documento; na série mensal o corte é o **mês** de referência, porque
   * dezembro do ano de referência ainda não aconteceu e o ano, sozinho, não
   * denuncia. A primeira versão desta linha prometia o mês de referência no
   * comentário e calculava dezembro no código — a revisão adversarial mostrou
   * um ponto em dezembro de 2026 passando por ela.
   */
  const cutoff = granularity === 'annual' ? referenceYear : referenceYear * 100 + referenceMonth
  invariant(
    candidate.periodEnd <= cutoff,
    `${label}.periodEnd ultrapassa o período de referência do documento.`,
  )

  return candidate
}

function validateSeriesReference(candidate, label, seriesById) {
  validateExactFields(candidate, SERIES_REF_FIELDS, label)
  validateText(candidate.label, `${label}.label`)
  validatePublicId(candidate.seriesId, `${label}.seriesId`, candidate.label)
  const serie = seriesById.get(candidate.seriesId)
  invariant(serie !== undefined, `${label}.seriesId não resolve em nenhuma série do documento.`)
  invariant(
    serie.label === candidate.label,
    `${label}.label diverge do rótulo da série que ele referencia.`,
  )
  return candidate
}

function validateProhibitedClaim(value, label) {
  validateText(value, label)
  invariant(
    value.startsWith(PROHIBITED_CLAIM_OPENER),
    `${label} deve começar pelo abridor de proibição do contrato.`,
  )
  /*
   * Uma sentença só. Guardar a alegação separada do abridor deixava passar uma
   * segunda frase afirmativa depois da proibição — a lição do ciclo delta da
   * Rodada 1, que esta camada herda em vez de reaprender.
   *
   * A regra é sobre o **corpo**, não sobre espaços. A primeira versão procurava
   * pontuação seguida de espaço e de um caractere, e a revisão adversarial
   * mostrou que ela tinha os dois defeitos ao mesmo tempo: deixava passar a
   * segunda frase emendada sem espaço ("…A caiu.B subiu.") e recusava texto
   * honesto com abreviação ("art. 5º"). Trocar `\s+` por `\s*` fecharia o
   * primeiro e pioraria o segundo.
   *
   * A regra que fica é mais simples de enunciar e de conferir: **o corpo da
   * proibição vai do abridor até o ponto final, e não contém pontuação de
   * sentença nenhuma pelo caminho**. Ela recusa `A caiu.B subiu`, `A; B causou
   * C`, `A: B causou C` e as reticências. O preço é recusar decimal com ponto e
   * abreviação com ponto dentro da alegação — construções que não têm o que
   * fazer numa frase cujo trabalho é nomear uma leitura proibida, e cuja recusa
   * fica aqui declarada em vez de descoberta depois.
   */
  invariant(value.endsWith('.'), `${label} deve terminar em ponto final.`)
  const body = value.slice(PROHIBITED_CLAIM_OPENER.length, -1)
  validateText(body, `${label} (alegação)`)
  invariant(
    !/[.!?;:…]/u.test(body),
    `${label} deve ser uma única sentença, sem pontuação de sentença no corpo da alegação.`,
  )
  /*
   * Nenhum caractere de controle ou de formatação: a alegação proibida é o
   * único campo do documento cujo sentido inverte com um caractere invisível.
   * A regra é por classe Unicode, não por lista — lista esquece a próxima borda.
   */
  invariant(
    !/[\p{Cc}\p{Cf}\p{Zl}\p{Zp}]/u.test(value) && !/[^\S ]/u.test(value),
    `${label} não aceita caractere de controle, de formatação ou espaço fora de U+0020.`,
  )
  return value
}

/*
 * A janela precisa **caber** na série, não apenas encostar nela.
 *
 * A primeira versão exigia interseção, e a revisão adversarial mostrou o que
 * isso permite: uma associação declarando janela de 2026 a 2099 passava, desde
 * que a série tivesse um ponto em 2026. Interseção é frouxa demais para o que a
 * janela promete — que os dados que sustentam a leitura existem no período
 * declarado.
 *
 * A contenção é conferida **em anos**, e não no período nativo da série. Uma
 * série mensal do cadastro social começa em maio de 2015; uma janela de 2015 a
 * 2025 é honesta e a contenção mês a mês a recusaria, porque janeiro de 2015
 * não existe naquela série. O ano é a unidade em que a janela é declarada, e é
 * nela que a contenção faz sentido.
 */
function seriesYearRange(serie) {
  const toYear = (period) =>
    serie.periodGranularity === 'annual' ? period : Math.floor(period / 100)
  return { start: toYear(serie.periodStart), end: toYear(serie.periodEnd) }
}

function validateWindowAgainstSeries(window, serie, label) {
  const range = seriesYearRange(serie)
  invariant(
    window.start >= range.start && window.end <= range.end,
    `${label}: a janela declarada (${window.start}–${window.end}) não cabe na série `
    + `"${serie.label}" (${range.start}–${range.end}).`,
  )
}

function validateAssociation(candidate, label, seriesById, referenceYear) {
  validateExactFields(candidate, ASSOCIATION_FIELDS, label)
  validatePublicId(candidate.associationId, `${label}.associationId`)
  validateText(candidate.label, `${label}.label`)
  /*
   * O identificador da associação sai do resultado educacional mais o primeiro
   * fator territorial: duas associações da mesma região podem partir do mesmo
   * resultado, e o rótulo sozinho não as separa.
   */
  validateText(candidate.periodLabel, `${label}.periodLabel`)
  validateWindow(candidate.window, `${label}.window`, referenceYear)

  const outcome = validateSeriesReference(
    candidate.educationOutcome,
    `${label}.educationOutcome`,
    seriesById,
  )
  invariant(
    Array.isArray(candidate.territorialFactors) && candidate.territorialFactors.length > 0,
    `${label}.territorialFactors deve trazer ao menos um fator.`,
  )
  candidate.territorialFactors.forEach((factor, index) => {
    validateSeriesReference(factor, `${label}.territorialFactors[${index}]`, seriesById)
  })

  validateWindowAgainstSeries(
    candidate.window,
    seriesById.get(outcome.seriesId),
    `${label}.window`,
  )
  candidate.territorialFactors.forEach((factor, index) => {
    validateWindowAgainstSeries(
      candidate.window,
      seriesById.get(factor.seriesId),
      `${label}.territorialFactors[${index}]`,
    )
  })

  invariant(
    candidate.associationId
      === slugify(`${candidate.educationOutcome.label} e ${candidate.territorialFactors[0].label}`),
    `${label}.associationId não é o identificador do resultado educacional com o primeiro fator.`,
  )

  validateText(candidate.observedStatement, `${label}.observedStatement`)
  validateText(candidate.allowedInterpretation, `${label}.allowedInterpretation`)
  validateProhibitedClaim(candidate.prohibitedClaim, `${label}.prohibitedClaim`)
  validateTextList(candidate.hypotheses, `${label}.hypotheses`)
  return candidate
}

function validateTemporalPair(candidate, label, seriesById, referenceYear) {
  validateExactFields(candidate, TEMPORAL_PAIR_FIELDS, label)
  validateText(candidate.label, `${label}.label`)
  validatePublicId(candidate.pairId, `${label}.pairId`, candidate.label)
  validateText(candidate.periodLabel, `${label}.periodLabel`)
  validateWindow(candidate.window, `${label}.window`, referenceYear)
  const first = validateSeriesReference(candidate.seriesA, `${label}.seriesA`, seriesById)
  const second = validateSeriesReference(candidate.seriesB, `${label}.seriesB`, seriesById)
  invariant(
    first.seriesId !== second.seriesId,
    `${label} compara uma série com ela mesma.`,
  )
  validateWindowAgainstSeries(candidate.window, seriesById.get(first.seriesId), `${label}.seriesA`)
  validateWindowAgainstSeries(candidate.window, seriesById.get(second.seriesId), `${label}.seriesB`)
  validateText(candidate.observedStatement, `${label}.observedStatement`)
  validateProhibitedClaim(candidate.prohibitedClaim, `${label}.prohibitedClaim`)
  return candidate
}

/* ------------------------------------------------------------------ *
 * Bloco 4 — cenários da região.
 * ------------------------------------------------------------------ */

/*
 * A âncora é o único lugar do Bloco 4 em que há número, e é por isso que ela é
 * o lugar mais perigoso dele. Todo o resto do bloco é prosa que alguém curou; a
 * âncora é a ponte entre a prosa e a série publicada logo acima, na mesma
 * página.
 *
 * A regra: **os dois valores da âncora são reconferidos contra os pontos da
 * própria série publicada neste documento**. Não «existe uma série com esse
 * identificador», nem «a janela encosta na série» — o valor inicial precisa ser
 * o valor que a série tem no ano de início, e o final o do ano de fim. Um
 * cenário que cita um número que a série não tem para de ser publicável, e não
 * há como corrigir isso reescrevendo a narrativa.
 *
 * A âncora exige série **anual**: a janela dela é declarada em anos, e casar um
 * ano com um ponto mensal exigiria escolher um mês — escolha que a origem não
 * declara e que a plataforma não vai inventar.
 */
function validateScenarioAnchor(candidate, label, seriesById, referenceYear) {
  validateExactFields(candidate, SCENARIO_ANCHOR_FIELDS, label)
  validateText(candidate.label, `${label}.label`)
  validatePublicId(candidate.seriesId, `${label}.seriesId`, candidate.label)
  const serie = seriesById.get(candidate.seriesId)
  invariant(serie !== undefined, `${label}.seriesId não resolve em nenhuma série do documento.`)
  invariant(
    serie.label === candidate.label,
    `${label}.label diverge do rótulo da série que ele referencia.`,
  )
  invariant(
    serie.periodGranularity === 'annual',
    `${label} ancora numa série mensal; a janela da âncora é declarada em anos.`,
  )

  /* O rótulo de período da âncora sai da janela dela. Enquanto era texto
   * livre, uma âncora de 2014 a 2025 podia anunciar-se como "2019 a 2025" e
   * passar — a revisão adversarial encontrou a folga, e ela é barata de
   * fechar porque a derivação é de uma linha. */
  validateWindow(candidate.window, `${label}.window`, referenceYear)
  const expectedPeriodLabel = candidate.window.start === candidate.window.end
    ? `${candidate.window.start}`
    : `${candidate.window.start} a ${candidate.window.end}`
  invariant(
    candidate.periodLabel === expectedPeriodLabel,
    `${label}.periodLabel não descreve a janela da âncora `
    + `(esperado "${expectedPeriodLabel}", recebido "${candidate.periodLabel}").`,
  )
  validateWindowAgainstSeries(candidate.window, serie, label)

  invariant(
    typeof candidate.startValue === 'number' && Number.isFinite(candidate.startValue),
    `${label}.startValue deve ser um número finito.`,
  )
  invariant(
    typeof candidate.endValue === 'number' && Number.isFinite(candidate.endValue),
    `${label}.endValue deve ser um número finito.`,
  )

  const pointAt = (period) => serie.points.find((point) => point.period === period)
  const first = pointAt(candidate.window.start)
  const last = pointAt(candidate.window.end)
  invariant(
    first !== undefined,
    `${label}: a série "${serie.label}" não tem ponto em ${candidate.window.start}.`,
  )
  invariant(
    last !== undefined,
    `${label}: a série "${serie.label}" não tem ponto em ${candidate.window.end}.`,
  )
  invariant(
    first.value === candidate.startValue,
    `${label}.startValue não é o valor da série em ${candidate.window.start} `
    + `(série ${first.value}, âncora ${candidate.startValue}).`,
  )
  invariant(
    last.value === candidate.endValue,
    `${label}.endValue não é o valor da série em ${candidate.window.end} `
    + `(série ${last.value}, âncora ${candidate.endValue}).`,
  )

  invariant(
    SCENARIO_DIRECTION_LABEL_VALUES.includes(candidate.directionLabel),
    `${label}.directionLabel não é uma das frases de direção do contrato.`,
  )
  if (candidate.directionLabel === SCENARIO_DIRECTION_RISING) {
    invariant(
      candidate.endValue > candidate.startValue,
      `${label} declara alta e termina em ${candidate.endValue}, que não é maior que `
      + `${candidate.startValue}.`,
    )
  }
  if (candidate.directionLabel === SCENARIO_DIRECTION_FALLING) {
    invariant(
      candidate.endValue < candidate.startValue,
      `${label} declara baixa e termina em ${candidate.endValue}, que não é menor que `
      + `${candidate.startValue}.`,
    )
  }
  return candidate
}

/*
 * Todo número escrito na prosa de um cenário precisa de âncora por trás.
 *
 * Esta é a segunda metade da garantia de que nenhum número do Bloco 4 é
 * digitado, e ela existe porque a primeira metade não bastava. A revisão
 * adversarial trocou `14 527` por `999 999` **na frase**, deixou a âncora e a
 * série intactas, e o documento passava: o contrato reconferia a âncora e nunca
 * lia a frase que o leitor lê.
 *
 * Como a regra funciona, na ordem:
 *
 *   1. os rótulos das séries citadas saem do texto primeiro, do mais longo para
 *      o mais curto. Um número que vive **dentro do nome** de uma série
 *      ("Pessoas de 60 anos ou mais…") é nome, não alegação — e casar o rótulo
 *      curto antes do longo faria "Matrículas na educação profissional" comer
 *      "…profissional técnica", que é a série realmente citada;
 *   2. o que sobra é varrido atrás de números, com o separador de milhar em
 *      espaço e o decimal em vírgula, como a origem os escreve;
 *   3. cada número precisa ser um ano de janela de âncora, ou o valor de uma
 *      âncora **na precisão em que foi escrito** — a âncora guarda 84,17533…, a
 *      frase mostra 84,2, e exigir igualdade exata recusaria o arredondamento
 *      honesto que a própria origem faz ao compor a frase.
 *
 * O que esta regra **não** alcança está declarado: a afirmação comparativa sem
 * dígito ("fica acima do observado na ponta inicial") não é pega por varredura
 * de número nenhuma, e fechá-la exigiria casar uma frase com uma série por
 * semântica. Fica como limitação declarada, e não como regra que recusaria
 * texto honesto.
 */
const SCENARIO_PROSE_FIELDS = Object.freeze([
  'centralMechanism',
  'startingPointStatement',
  'trajectoryStatement',
  'stateAtHorizonStatement',
])

const SCENARIO_NUMBER_PATTERN = /\d[\d\u00a0 ]*(?:,\d+)?/gu

function validateScenarioProseNumbers(candidate, label, seriesById) {
  const anchoredLabels = new Set(candidate.anchors.map((anchor) => anchor.label))
  const years = new Set()
  const values = []
  for (const anchor of candidate.anchors) {
    years.add(anchor.window.start)
    years.add(anchor.window.end)
    values.push(anchor.startValue, anchor.endValue)
  }

  const allLabels = [...seriesById.values()]
    .map((serie) => serie.label)
    .sort((left, right) => right.length - left.length)

  for (const field of SCENARIO_PROSE_FIELDS) {
    let remaining = candidate[field]
    for (const seriesLabel of allLabels) {
      if (!remaining.includes(seriesLabel)) continue
      invariant(
        anchoredLabels.has(seriesLabel),
        `${label}.${field} cita a série "${seriesLabel}" sem ancorá-la neste cenário.`,
      )
      remaining = remaining.split(seriesLabel).join(' ')
    }

    for (const match of remaining.matchAll(SCENARIO_NUMBER_PATTERN)) {
      const written = match[0].replace(/[\u00a0 ]+$/u, '')
      if (written === '') continue
      const [whole, fraction = ''] = written.split(',')
      const decimals = fraction.length
      const parsed = Number.parseFloat(`${whole.replace(/[\u00a0 ]/gu, '')}.${fraction || '0'}`)
      if (!Number.isFinite(parsed)) continue
      if (decimals === 0 && years.has(parsed)) continue
      const supported = values.some(
        (value) => Number(value.toFixed(decimals)) === Number(parsed.toFixed(decimals)),
      )
      invariant(
        supported,
        `${label}.${field} escreve o número "${written}", que nenhuma âncora deste cenário `
        + 'sustenta.',
      )
    }
  }
  return candidate
}

function validateScenarioItem(candidate, label, seriesById, referenceYear) {
  validateExactFields(candidate, SCENARIO_ITEM_FIELDS, label)
  validateText(candidate.title, `${label}.title`)
  validatePublicId(candidate.scenarioId, `${label}.scenarioId`, candidate.title)
  invariant(
    Number.isInteger(candidate.order) && candidate.order > 0,
    `${label}.order deve ser inteiro positivo.`,
  )
  validateText(candidate.profileLabel, `${label}.profileLabel`)

  invariant(
    SCENARIO_STATUTES.includes(candidate.statute),
    `${label}.statute fora do contrato: ${candidate.statute}.`,
  )
  /* Mesma regra da classe de evidência: a frase é a do enum, nunca escrita à
   * mão. Estatuto que diz uma coisa e frase que diz outra é o defeito que esta
   * linha existe para tornar impossível. */
  invariant(
    candidate.statuteLabel === SCENARIO_STATUTE_LABELS[candidate.statute],
    `${label}.statuteLabel não é a frase declarada para o estatuto ${candidate.statute}.`,
  )

  validateText(candidate.centralMechanism, `${label}.centralMechanism`)
  validateText(candidate.startingPointStatement, `${label}.startingPointStatement`)
  validateText(candidate.trajectoryStatement, `${label}.trajectoryStatement`)
  validateText(candidate.stateAtHorizonStatement, `${label}.stateAtHorizonStatement`)

  invariant(
    Array.isArray(candidate.anchors) && candidate.anchors.length > 0,
    `${label}.anchors deve trazer ao menos uma âncora.`,
  )
  const anchorSeries = new Set()
  candidate.anchors.forEach((anchor, index) => {
    const anchorLabel = `${label}.anchors[${index}]`
    validateScenarioAnchor(anchor, anchorLabel, seriesById, referenceYear)
    invariant(
      !anchorSeries.has(anchor.seriesId),
      `${anchorLabel} ancora duas vezes na mesma série: ${anchor.seriesId}.`,
    )
    anchorSeries.add(anchor.seriesId)
  })

  invariant(
    Array.isArray(candidate.educationImplications) && candidate.educationImplications.length > 0,
    `${label}.educationImplications deve trazer ao menos uma implicação.`,
  )
  candidate.educationImplications.forEach((implication, index) => {
    const implicationLabel = `${label}.educationImplications[${index}]`
    validateExactFields(implication, SCENARIO_IMPLICATION_FIELDS, implicationLabel)
    validateText(implication.stageLabel, `${implicationLabel}.stageLabel`)
    validateText(implication.statement, `${implicationLabel}.statement`)
  })

  validateTextList(candidate.contraryEvidence, `${label}.contraryEvidence`)
  validateTextList(candidate.limits, `${label}.limits`)
  validateProhibitedClaim(candidate.prohibitedClaim, `${label}.prohibitedClaim`)
  validateScenarioProseNumbers(candidate, label, seriesById)
  return candidate
}

function validateNormativeCriterion(candidate, label) {
  validateExactFields(candidate, NORMATIVE_CRITERION_FIELDS, label)
  invariant(
    Number.isInteger(candidate.order) && candidate.order > 0,
    `${label}.order deve ser inteiro positivo.`,
  )
  validateText(candidate.publicName, `${label}.publicName`)
  validateText(candidate.definition, `${label}.definition`)
  validateText(candidate.requiredState, `${label}.requiredState`)
  validateText(candidate.tradeOff, `${label}.tradeOff`)
  validateText(candidate.failureMode, `${label}.failureMode`)
  validateText(candidate.whatToFollow, `${label}.whatToFollow`)
  return candidate
}

function validateScenarioBlock(candidate, label, seriesById, referenceYear) {
  validateExactFields(candidate, SCENARIO_BLOCK_FIELDS, label)
  validateText(candidate.methodologyLabel, `${label}.methodologyLabel`)
  validateText(candidate.focalQuestion, `${label}.focalQuestion`)
  validateText(candidate.maturityNote, `${label}.maturityNote`)
  validateText(candidate.statuteNote, `${label}.statuteNote`)
  validateText(candidate.baseYearStatement, `${label}.baseYearStatement`)
  validateText(candidate.horizonStatement, `${label}.horizonStatement`)
  validateText(candidate.longScanStatement, `${label}.longScanStatement`)
  validateText(candidate.compatibilityCeilingStatement, `${label}.compatibilityCeilingStatement`)
  validateText(candidate.conditionalImplication, `${label}.conditionalImplication`)

  /*
   * Os três anos do bloco são os únicos números do documento que apontam para
   * depois do ano de referência, e são anos **de horizonte**, não valores
   * atribuídos a ano futuro: dizer que o horizonte alcança 2031 não é dizer
   * quantas matrículas haverá em 2031. A ordenação entre eles é conferida
   * porque uma varredura de prazo mais longo que termina antes do horizonte
   * comum seria uma contradição que ninguém veria lendo a página.
   */
  invariant(
    Number.isInteger(candidate.baseYear) && candidate.baseYear <= referenceYear,
    `${label}.baseYear deve ser inteiro e não pode ultrapassar o ano de referência.`,
  )
  invariant(
    Number.isInteger(candidate.targetYear) && candidate.targetYear > referenceYear,
    `${label}.targetYear deve ser um ano posterior ao ano de referência.`,
  )
  invariant(
    Number.isInteger(candidate.longScanTargetYear)
      && candidate.longScanTargetYear > candidate.targetYear,
    `${label}.longScanTargetYear deve ser posterior a ${label}.targetYear.`,
  )

  invariant(
    Array.isArray(candidate.items) && candidate.items.length > 0,
    `${label}.items deve trazer ao menos um cenário.`,
  )
  const scenarioIds = new Set()
  const titles = new Set()
  const orders = new Set()
  let normativeCount = 0
  candidate.items.forEach((item, index) => {
    const itemLabel = `${label}.items[${index}]`
    validateScenarioItem(item, itemLabel, seriesById, referenceYear)
    invariant(!scenarioIds.has(item.scenarioId), `${itemLabel}.scenarioId repetido: ${item.scenarioId}.`)
    invariant(!titles.has(item.title), `${itemLabel}.title repetido: "${item.title}".`)
    invariant(!orders.has(item.order), `${itemLabel}.order repetido: ${item.order}.`)
    scenarioIds.add(item.scenarioId)
    titles.add(item.title)
    orders.add(item.order)
    if (item.statute === 'normative') normativeCount += 1
  })

  /*
   * A assimetria de estatuto é **estrutural**, não editorial (decisão `D3`).
   * Um conjunto sem normativo publicaria quatro exploratórios sob uma nota de
   * leitura que promete um normativo; um conjunto com dois publicaria dois
   * ideais técnicos concorrentes sob a mesma nota. Os dois estados são recusa.
   */
  invariant(
    normativeCount === 1,
    `${label} publica ${normativeCount} cenários normativos, e o contrato regional exige `
    + 'exatamente um.',
  )

  invariant(
    Array.isArray(candidate.normativeCriteria) && candidate.normativeCriteria.length > 0,
    `${label}.normativeCriteria deve trazer ao menos um critério — há um cenário normativo.`,
  )
  const criterionOrders = new Set()
  candidate.normativeCriteria.forEach((criterion, index) => {
    const criterionLabel = `${label}.normativeCriteria[${index}]`
    validateNormativeCriterion(criterion, criterionLabel)
    invariant(
      !criterionOrders.has(criterion.order),
      `${criterionLabel}.order repetido: ${criterion.order}.`,
    )
    criterionOrders.add(criterion.order)
  })

  validateTextList(candidate.realizationConditions, `${label}.realizationConditions`)
  validateTextList(candidate.robustImplications, `${label}.robustImplications`)
  validateProhibitedClaim(candidate.prohibitedClaim, `${label}.prohibitedClaim`)
  return candidate
}

/*
 * O Bloco 4 existe nas dez regiões. Nas oito sem cenário, ele existe **dizendo
 * que não há cenário** — e é o contrato, não a página, que garante isso.
 *
 * As duas implicações são conferidas nos dois sentidos de propósito. Conferir
 * só uma delas deixaria passar o par que mais engana: `status` dizendo ausente
 * com bloco preenchido logo abaixo, que a página renderizaria como cenário
 * publicado enquanto o manifesto contaria zero.
 */
function validateScenarios(candidate, label, seriesById, referenceYear) {
  validateExactFields(candidate, SCENARIOS_FIELDS, label)
  invariant(
    candidate.label === SCENARIO_FRAMING.label,
    `${label}.label não é o rótulo declarado para o Bloco 4.`,
  )
  invariant(
    SCENARIO_BLOCK_STATUSES.includes(candidate.status),
    `${label}.status fora do contrato: ${candidate.status}.`,
  )
  /* A descrição é a do estado, e só a do estado: a de quem publica cenários
   * numa região sem cenários seria uma promessa de quatro cenários que a
   * página não tem, e a inversa seria a negação do que ela mostra. */
  const expectedDescription = candidate.status === 'published'
    ? SCENARIO_FRAMING.publishedDescription
    : SCENARIO_FRAMING.absentDescription
  invariant(
    candidate.description === expectedDescription,
    `${label}.description não é a descrição declarada para o estado "${candidate.status}".`,
  )

  if (candidate.status === 'absent') {
    invariant(
      candidate.absenceStatement === SCENARIO_FRAMING.absenceStatement,
      `${label}.absenceStatement não é a frase de ausência declarada pelo contrato.`,
    )
    invariant(
      candidate.block === null,
      `${label} declara ausência de cenários e traz bloco de cenários.`,
    )
    /*
     * A nota de estatuto explica a diferença entre três cenários exploratórios
     * e um normativo. Numa região sem cenário nenhum ela não é só inútil: é
     * falsa, porque promete ao leitor quatro cenários que a página não tem. Por
     * isso ela é `null` aqui, e o contrato recusa a região que a traga assim
     * mesmo.
     */
    invariant(
      candidate.statuteReadingNote === null,
      `${label} declara ausência de cenários e traz a nota de estatuto, que fala de quatro `
      + 'cenários que esta região não publica.',
    )
    return candidate
  }

  invariant(
    candidate.absenceStatement === null,
    `${label} publica cenários e traz frase de ausência.`,
  )
  invariant(
    candidate.statuteReadingNote === SCENARIO_FRAMING.statuteReadingNote,
    `${label}.statuteReadingNote não é a nota de estatuto declarada pelo contrato.`,
  )
  invariant(candidate.block !== null, `${label} declara cenários publicados e não traz o bloco.`)
  validateScenarioBlock(candidate.block, `${label}.block`, seriesById, referenceYear)
  return candidate
}

/*
 * O validador nasce do manifesto: é ele que declara a versão de origem, o
 * escopo de publicação e o ano de referência que o pacote precisa repetir.
 * Assim o contrato aceita a próxima versão da origem sem que este arquivo
 * precise saber qual será o número dela.
 */
export function createVocacoesDocumentParser({
  documentSchema = VOCACOES_DOCUMENT_SCHEMA,
  sourceVersion,
  publicationScope,
  referenceYear,
  referenceMonth,
}) {
  invariant(typeof sourceVersion === 'string' && sourceVersion !== '', 'versão de origem ausente.')
  invariant(
    typeof publicationScope === 'string' && publicationScope !== '',
    'escopo de publicação ausente.',
  )
  invariant(Number.isInteger(referenceYear), 'ano de referência ausente.')
  invariant(
    Number.isInteger(referenceMonth) && referenceMonth >= 1 && referenceMonth <= 12,
    'mês de referência ausente ou fora de 1–12.',
  )

  return function parseVocacoesDocument(candidate) {
    validateExactFields(candidate, DOCUMENT_FIELDS, 'pacote')
    invariant(candidate.schemaVersion === documentSchema, 'esquema do pacote desconhecido.')
    invariant(candidate.sourceVersion === sourceVersion, 'versão de origem inesperada.')
    invariant(candidate.publicationScope === publicationScope, 'escopo de publicação inesperado.')
    validateText(candidate.sourceMethodologyStatus, 'pacote.sourceMethodologyStatus')
    validateText(candidate.generatorVersion, 'pacote.generatorVersion')
    invariant(
      typeof candidate.generatedAt === 'string' && ISO_DATE_PATTERN.test(candidate.generatedAt),
      'pacote.generatedAt deve ser uma data ISO.',
    )
    invariant(
      typeof candidate.contentVersion === 'string' && SHA256_PATTERN.test(candidate.contentVersion),
      'pacote.contentVersion deve ser sha256.',
    )
    validateRegionIdentity(candidate.region, 'pacote.region')

    validateExactFields(candidate.page, PAGE_FIELDS, 'pacote.page')
    validateText(candidate.page.eyebrow, 'pacote.page.eyebrow')
    validateText(candidate.page.title, 'pacote.page.title')
    validateText(candidate.page.description, 'pacote.page.description')
    validateText(candidate.page.neutralityNote, 'pacote.page.neutralityNote')

    validateExactFields(candidate.howToRead, TEXT_BLOCK_FIELDS, 'pacote.howToRead')
    validateText(candidate.howToRead.label, 'pacote.howToRead.label')
    validateText(candidate.howToRead.description, 'pacote.howToRead.description')
    validateTextList(candidate.howToRead.items, 'pacote.howToRead.items')

    /* Bloco 1 — retrato e transformações do território. */
    validateExactFields(candidate.territoryPortrait, PORTRAIT_FIELDS, 'pacote.territoryPortrait')
    validateText(candidate.territoryPortrait.label, 'pacote.territoryPortrait.label')
    validateText(candidate.territoryPortrait.description, 'pacote.territoryPortrait.description')
    invariant(
      Array.isArray(candidate.territoryPortrait.series)
        && candidate.territoryPortrait.series.length > 0,
      'pacote.territoryPortrait.series deve trazer ao menos uma série.',
    )

    const seriesById = new Map()
    const seriesLabels = new Set()
    candidate.territoryPortrait.series.forEach((serie, index) => {
      const label = `pacote.territoryPortrait.series[${index}]`
      validateSeries(serie, label, referenceYear, referenceMonth)
      invariant(!seriesById.has(serie.seriesId), `${label}.seriesId repetido: ${serie.seriesId}.`)
      /*
       * Rótulo repetido é tão grave quanto identificador repetido: o leitor
       * distingue as séries pelo rótulo, e duas séries com o mesmo rótulo são
       * indistinguíveis na página, mesmo que o identificador as separe.
       */
      invariant(!seriesLabels.has(serie.label), `${label}.label repetido: "${serie.label}".`)
      seriesById.set(serie.seriesId, serie)
      seriesLabels.add(serie.label)
    })

    /* Bloco 2 — leitura associativa educação ↔ território. */
    validateExactFields(candidate.associations, TEXT_BLOCK_FIELDS, 'pacote.associations')
    validateText(candidate.associations.label, 'pacote.associations.label')
    validateText(candidate.associations.description, 'pacote.associations.description')
    invariant(
      Array.isArray(candidate.associations.items) && candidate.associations.items.length > 0,
      'pacote.associations.items deve trazer ao menos uma associação.',
    )
    const associationIds = new Set()
    candidate.associations.items.forEach((association, index) => {
      const label = `pacote.associations.items[${index}]`
      validateAssociation(association, label, seriesById, referenceYear)
      invariant(
        !associationIds.has(association.associationId),
        `${label}.associationId repetido: ${association.associationId}.`,
      )
      associationIds.add(association.associationId)
    })

    /* Bloco 3 — comparação temporal em pares curados. */
    validateExactFields(candidate.temporalPairs, TEXT_BLOCK_FIELDS, 'pacote.temporalPairs')
    validateText(candidate.temporalPairs.label, 'pacote.temporalPairs.label')
    validateText(candidate.temporalPairs.description, 'pacote.temporalPairs.description')
    invariant(
      Array.isArray(candidate.temporalPairs.items) && candidate.temporalPairs.items.length > 0,
      'pacote.temporalPairs.items deve trazer ao menos um par.',
    )
    const pairIds = new Set()
    candidate.temporalPairs.items.forEach((pair, index) => {
      const label = `pacote.temporalPairs.items[${index}]`
      validateTemporalPair(pair, label, seriesById, referenceYear)
      invariant(!pairIds.has(pair.pairId), `${label}.pairId repetido: ${pair.pairId}.`)
      pairIds.add(pair.pairId)
    })

    /* Bloco 4 — cenários da região, publicados ou declaradamente ausentes. */
    validateScenarios(candidate.scenarios, 'pacote.scenarios', seriesById, referenceYear)

    validateExactFields(candidate.sources, TEXT_BLOCK_FIELDS, 'pacote.sources')
    validateText(candidate.sources.label, 'pacote.sources.label')
    validateText(candidate.sources.description, 'pacote.sources.description')
    invariant(
      Array.isArray(candidate.sources.items) && candidate.sources.items.length > 0,
      'pacote.sources.items deve listar as fontes usadas.',
    )
    candidate.sources.items.forEach((item, index) => {
      const label = `pacote.sources.items[${index}]`
      validateExactFields(item, SOURCE_ITEM_FIELDS, label)
      validateText(item.label, `${label}.label`)
      validateText(item.periodLabel, `${label}.periodLabel`)
    })

    validateExactFields(candidate.limitations, TEXT_BLOCK_FIELDS, 'pacote.limitations')
    validateText(candidate.limitations.label, 'pacote.limitations.label')
    validateText(candidate.limitations.description, 'pacote.limitations.description')
    validateTextList(candidate.limitations.items, 'pacote.limitations.items')

    validateExactFields(candidate.provenance, PROVENANCE_FIELDS, 'pacote.provenance')
    invariant(
      typeof candidate.provenance.sourcePackageSha256 === 'string'
        && SHA256_PATTERN.test(candidate.provenance.sourcePackageSha256),
      'pacote.provenance.sourcePackageSha256 deve ser sha256.',
    )
    invariant(
      typeof candidate.provenance.registrySha256 === 'string'
        && SHA256_PATTERN.test(candidate.provenance.registrySha256),
      'pacote.provenance.registrySha256 deve ser sha256.',
    )
    /*
     * Os dois resumos do cenário existem juntos ou não existem: um documento
     * que nomeia o pacote de cenários e não nomeia a origem dele prova metade
     * da cadeia, e metade de uma cadeia de procedência não é procedência.
     */
    const scenarioHashes = [
      candidate.provenance.scenarioPackageSha256,
      candidate.provenance.scenarioSourceSha256,
    ]
    const publishesScenarios = candidate.scenarios.status === 'published'
    scenarioHashes.forEach((value, index) => {
      const name = index === 0 ? 'scenarioPackageSha256' : 'scenarioSourceSha256'
      if (publishesScenarios) {
        invariant(
          typeof value === 'string' && SHA256_PATTERN.test(value),
          `pacote.provenance.${name} deve ser sha256 num documento que publica cenários.`,
        )
      } else {
        invariant(
          value === null,
          `pacote.provenance.${name} não pode existir num documento sem cenários.`,
        )
      }
    })

    validateText(candidate.provenance.sourceContractVersion, 'pacote.provenance.sourceContractVersion')
    validateText(candidate.provenance.sourceBuilderVersion, 'pacote.provenance.sourceBuilderVersion')
    invariant(
      typeof candidate.provenance.sourceGeneratedAt === 'string'
        && ISO_DATE_PATTERN.test(candidate.provenance.sourceGeneratedAt),
      'pacote.provenance.sourceGeneratedAt deve ser uma data ISO.',
    )

    return Object.freeze(candidate)
  }
}
