/*
 * Contrato público do Vocações da Região — `vocacoes-regiao-2.0.0`.
 *
 * A Fase A publica três blocos por região e **nenhum cenário**: retrato e
 * transformações do território (Bloco 1), leitura associativa entre educação e
 * território (Bloco 2) e comparação temporal em pares curados (Bloco 3). O
 * bloco de cenários é da Fase B e entra por versão aditiva (`2.1.0`), não por
 * campo opcional aqui.
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

export const VOCACOES_DOCUMENT_SCHEMA = 'vocacoes-regiao-2.0.0'

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
const PROVENANCE_FIELDS = new Set([
  'sourcePackageSha256',
  'sourceContractVersion',
  'sourceBuilderVersion',
  'sourceGeneratedAt',
  'registrySha256',
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
