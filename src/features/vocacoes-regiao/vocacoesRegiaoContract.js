/*
 * Contrato público do Vocações da Região — `vocacoes-regiao-2.6.0`.
 *
 * Quatro blocos por região: retrato e transformações do território (Bloco 1),
 * leitura associativa entre educação e território (Bloco 2), comparação
 * temporal em pares curados (Bloco 3) e **cenários da região (Bloco 4)**.
 *
 * Changelog do contrato:
 *   - `2.0.0` → `2.1.0`: **aditivo**. Nenhum campo dos três primeiros blocos
 *     mudou de forma, de nome ou de regra; o único acréscimo ao documento é o
 *     campo `scenarios` (Bloco 4), mais os dois resumos de procedência do
 *     cenário.
 *   - `2.1.0` → `2.2.0` (Rodada 1 do V2, decisão `V2` da D11): **a forma do
 *     documento não muda** — nenhum campo entra ou sai. Muda a regra pública do
 *     `schema.json` da família: a decisão `D3` deixa de ser «duas famílias com
 *     regras diferentes» e passa a ser «esta família tem esta regra». A família
 *     dos cenários municipais foi **removida da plataforma** (D11); com ela
 *     fora, o contrato não pode mais nomear a regra da outra família como a que
 *     não vale aqui — declara a sua e só a sua. O
 *     motivo do salto de versão é essa mudança de contrato público, não uma
 *     mudança de forma do documento.
 *   - `2.2.0` → `2.3.0` (Rodada 4 do V2, decisão `V2-D6`): **aditivo**. O único
 *     campo novo do **documento** continua sendo `scenarios`; o acréscimo é um
 *     subcampo obrigatório do item de cenário — `agendaThemes` —, a ponte
 *     Vocações → PNE. Cada tema é um enum fechado alinhado a uma **meta do PNE**
 *     (o tema da meta, nunca o número dela com valor), e a frase que o sustenta
 *     é **byte-idêntica a uma implicação educacional já publicada no próprio
 *     cenário**: o tema de agenda não escreve prosa nova, ele aponta para a
 *     implicação que o justifica. É a mesma disciplina da âncora — o Bloco 4 não
 *     digita número, e agora também não digita frase de agenda.
 *   - `2.3.0` → `2.4.0` (Rodada 5 do V2, sucessora da D11): **aditivo**. O único
 *     acréscimo é `scenarios.block.municipalLayer` — a **camada municipal dentro
 *     do cenário**, presente só nas regiões que publicam cenário (o bloco é
 *     `null` nas outras oito, e a camada com ele). Para cada município da região,
 *     ela traz a **composição observada** dele na região (participação em
 *     demografia e cadastro social, sinal de fluxo escolar) e, por cenário, uma
 *     leitura de **exposição derivada dessa composição** — nunca uma projeção
 *     municipal nem uma probabilidade. Emprego setorial e matrícula-por-etapa,
 *     que os cenários também citam, estão em grão regional e a camada os declara
 *     como ausência por município (decisão `V2-D7`). A guarda de linguagem barra
 *     número futuro municipal, probabilidade municipal, ranking implícito de
 *     municípios e causalidade município←região.
 *   - `2.4.0` → `2.5.0` (Rodada 6 do V2, decisão `V2-D8`): **aditivo**. O
 *     documento passa a trazer `synthesis`, uma camada de conclusões com quatro
 *     construções fechadas. As frases nascem de dados e templates promovidos,
 *     perdem os enums internos na fronteira e são reverificadas contra as
 *     associações, pares, séries, âncoras e temas do próprio documento.
 *   - `2.5.0` → `2.6.0` (Rodada 1 do V3, decisão `V3-D8`): **aditivo**. As
 *     associações e os pares ganham leitura associativa quantificada; entram a
 *     leitura defasada e a triagem estatística. Coeficientes, bins e frases são
 *     recomputados a partir das séries do próprio documento.
 *
 * O Bloco 4 não é um campo opcional deixado vazio nas regiões sem cenário. Ele
 * é obrigatório em todas as dez, e **declara em qual dos dois estados está**:
 * publicado, com o bloco inteiro; ou ausente, com a frase que diz ao leitor que
 * ali não há cenários e por quê. Campo opcional deixaria a ausência silenciosa,
 * e ausência silenciosa é indistinguível de bloco que se perdeu no caminho.
 *
 * **Os quatro cenários de uma região não têm o mesmo peso.** Três são
 * exploratórios e um é normativo, e o estatuto de cada um é campo obrigatório
 * do contrato — decisão `D3` do plano. Essa assimetria é a regra própria desta
 * família, declarada no seu `schema.json` e reconferida na página, onde o
 * estatuto de cada cenário vem escrito nele mesmo — o leitor desatento que lê o
 * normativo como previsão encontra, ao lado, a frase que o desmente.
 *
 * O corpo do documento é próprio, não uma transposição de outro produto: há
 * séries, associações e pares, e o conjunto de campos é fechado em todo nível,
 * texto não vazio, ausência declarada em vez de valor inventado, e recusa em
 * vez de tolerância.
 *
 * Fechado significa fechado: campo desconhecido em qualquer nível — documento,
 * região, bloco, série, ponto, associação, par — é recusa, não campo ignorado.
 * É o padrão do `matriz-4.0.0`, e existe porque o modo mais silencioso de um
 * artefato mentir é trazer um campo que ninguém valida e alguém renderiza.
 */

export const VOCACOES_DOCUMENT_SCHEMA = 'vocacoes-regiao-2.6.0'

export const ASSOCIATIVE_GRAMMAR_VERSION = 'vocacoes-regiao-associativo-v0.1'

export const ASSOCIATIVE_METHOD_NOTE =
  'Concordância, co-movimento e correlação descrevem movimento conjunto no período observado; '
  + 'não medem causa nem permitem projeção.'

export const SCREENED_ORIGIN_STATEMENT =
  'Relação observada por triagem estatística entre as séries da região; não integra a curadoria '
  + 'e não traz hipóteses.'

export const ASSOCIATIVE_REASON_CODES = Object.freeze([
  'sem_intervalos_comparaveis',
  'janela_curta',
  'variancia_nula',
  'variacao_nula',
  'contraste_sem_regioes_comparaveis',
  'defasagem_sem_janela_suficiente',
  'serie_ausente',
])

export const SCREENED_RELATIONS_CRITERIA = Object.freeze({
  minIntervals: 8,
  minAbsPearson: 0.6,
  maxItems: 5,
})

const ASSOCIATIVE_REASON_CODE_SET = new Set(ASSOCIATIVE_REASON_CODES)
const COMPARISON_REASON_CODES = new Set(['sem_intervalos_comparaveis'])
const CORRELATION_REASON_CODES = new Set(['janela_curta', 'variancia_nula'])
const CONTRAST_REASON_CODES = new Set([
  'variacao_nula',
  'contraste_sem_regioes_comparaveis',
])
const LAGGED_REASON_CODES = new Set([
  'defasagem_sem_janela_suficiente',
  'serie_ausente',
])
const ASSOCIATIVE_STRENGTHS = new Set(['fraca', 'moderada', 'forte'])
const ASSOCIATIVE_DIRECTIONS = new Set(['positiva', 'negativa', 'nula'])
const COMOVEMENT_DELTA_KINDS = new Set(['nivel', 'pontos'])
const CONTRAST_DIRECTIONS = new Set(['alta', 'queda'])
const CONTRAST_STATISTICS = new Set(['variacao_percentual', 'variacao_em_pontos'])
const LAGGED_RATIONALE =
  'a coorte nascida em um ano atinge a idade de ingresso no ensino fundamental seis anos depois'

function roundedScaledInteger(value, decimals) {
  invariant(typeof value === 'number' && Number.isFinite(value), 'valor para arredondamento deve ser finito.')
  invariant(
    Number.isInteger(decimals) && decimals >= 0 && decimals <= 20,
    'casas decimais devem ser um inteiro entre 0 e 20.',
  )
  const negative = value < 0
  const [coefficient, exponentText = '0'] = Math.abs(value).toString().toLowerCase().split('e')
  const exponent = Number(exponentText)
  const [integerPart, fractionPart = ''] = coefficient.split('.')
  const digits = (integerPart + fractionPart).replace(/^0+(?=\d)/u, '') || '0'
  const shift = decimals + exponent - fractionPart.length
  let scaled
  if (shift >= 0) {
    scaled = BigInt(digits) * (10n ** BigInt(shift))
  } else {
    const divisor = 10n ** BigInt(-shift)
    const absolute = BigInt(digits)
    scaled = absolute / divisor
    if ((absolute % divisor) * 2n >= divisor) scaled += 1n
  }
  return { negative: negative && scaled !== 0n, scaled }
}

function scaledIntegerText({ negative, scaled }, decimals) {
  const digits = scaled.toString().padStart(decimals + 1, '0')
  const sign = negative ? '-' : ''
  if (decimals === 0) return `${sign}${digits}`
  const splitAt = digits.length - decimals
  return `${sign}${digits.slice(0, splitAt)}.${digits.slice(splitAt)}`
}

/** Arredondamento decimal half-away-from-zero, sem depender de `toFixed`. */
export function roundHalfAwayFromZero(value, decimals) {
  return Number(scaledIntegerText(roundedScaledInteger(value, decimals), decimals))
}

/** Decimal com vírgula e quantidade fixa de casas, usando o arredondamento do contrato. */
export function formatDecimalComma(value, decimals) {
  return scaledIntegerText(roundedScaledInteger(value, decimals), decimals).replace('.', ',')
}

function groupIntegerDigits(digits) {
  return digits.replace(/\B(?=(\d{3})+(?!\d))/gu, ' ')
}

/* O `numero_publico` canônico usa o arredondamento do formatador de `float` do
 * Python. Ele é half-even sobre o double binário, não o arredondamento decimal
 * half-away empregado em percentuais, pontos e coeficientes. */
function roundedBinaryHalfEvenScaledInteger(value, decimals) {
  const buffer = new ArrayBuffer(8)
  const view = new DataView(buffer)
  view.setFloat64(0, Math.abs(value), false)
  const high = view.getUint32(0, false)
  const low = view.getUint32(4, false)
  const exponentBits = (high >>> 20) & 0x7ff
  const fraction = (BigInt(high & 0xfffff) << 32n) | BigInt(low)
  const mantissa = exponentBits === 0 ? fraction : (1n << 52n) | fraction
  const binaryExponent = exponentBits === 0
    ? -1074 + decimals
    : exponentBits - 1023 - 52 + decimals
  const numerator = mantissa * (5n ** BigInt(decimals))
  let scaled
  if (binaryExponent >= 0) {
    scaled = numerator << BigInt(binaryExponent)
  } else {
    const divisor = 1n << BigInt(-binaryExponent)
    scaled = numerator / divisor
    const remainder = numerator % divisor
    if (remainder * 2n > divisor || (remainder * 2n === divisor && scaled % 2n === 1n)) {
      scaled += 1n
    }
  }
  return { negative: value < 0 && scaled !== 0n, scaled }
}

/** Formatação de nível idêntica a `numero_publico`: espaço de milhar e vírgula decimal. */
export function formatPublicNumber(value) {
  invariant(typeof value === 'number' && Number.isFinite(value), 'número público deve ser finito.')
  const decimals = Number.isInteger(value) ? 0 : 1
  const rounded = roundedBinaryHalfEvenScaledInteger(value, decimals)
  const digits = rounded.scaled.toString().padStart(decimals + 1, '0')
  const splitAt = digits.length - decimals
  const integer = decimals === 0 ? digits : digits.slice(0, splitAt)
  const fraction = decimals === 0 ? '' : `,${digits.slice(splitAt)}`
  return `${rounded.negative ? '-' : ''}${groupIntegerDigits(integer)}${fraction}`
}

function pointValueMap(points) {
  return new Map(points.map((point) => [point.period, point.value]))
}

function computeDeltaPairs(pointsA, pointsB, window, lagYears = 0) {
  const valuesA = pointValueMap(pointsA)
  const valuesB = pointValueMap(pointsB)
  const pairs = []
  for (let period = window.start + 1; period <= window.end; period += 1) {
    if (
      valuesA.has(period - 1)
      && valuesA.has(period)
      && valuesB.has(period + lagYears - 1)
      && valuesB.has(period + lagYears)
    ) {
      pairs.push({
        period,
        deltaA: valuesA.get(period) - valuesA.get(period - 1),
        deltaB: valuesB.get(period + lagYears) - valuesB.get(period + lagYears - 1),
      })
    }
  }
  return pairs
}

function directionSign(value) {
  return value > 0 ? 1 : value < 0 ? -1 : 0
}

export function computeDirectionConcordance(pointsA, pointsB, window) {
  const pairs = computeDeltaPairs(pointsA, pointsB, window)
  if (pairs.length === 0) return { reasonCode: 'sem_intervalos_comparaveis' }
  const concordant = pairs.filter(({ deltaA, deltaB }) =>
    directionSign(deltaA) * directionSign(deltaB) === 1).length
  const opposite = pairs.filter(({ deltaA, deltaB }) =>
    directionSign(deltaA) * directionSign(deltaB) === -1).length
  return {
    windowStart: window.start,
    windowEnd: window.end,
    intervals: pairs.length,
    concordant,
    opposite,
    ties: pairs.length - concordant - opposite,
  }
}

export function computeComovement(points, window, deltaKind) {
  invariant(COMOVEMENT_DELTA_KINDS.has(deltaKind), `deltaKind fora do contrato: ${deltaKind}.`)
  const available = points
    .filter((point) => point.period >= window.start && point.period <= window.end)
    .sort((left, right) => left.period - right.period)
  if (available.length < 2 || available[0].period >= available[available.length - 1].period) {
    return { reasonCode: 'sem_intervalos_comparaveis' }
  }
  const first = available[0]
  const last = available[available.length - 1]
  return {
    effStart: first.period,
    effEnd: last.period,
    valueStart: first.value,
    valueEnd: last.value,
    delta: last.value - first.value,
    deltaKind,
  }
}

function pearson(valuesA, valuesB) {
  const meanA = valuesA.reduce((total, value) => total + value, 0) / valuesA.length
  const meanB = valuesB.reduce((total, value) => total + value, 0) / valuesB.length
  let varianceA = 0
  let varianceB = 0
  let covariance = 0
  for (let index = 0; index < valuesA.length; index += 1) {
    const centeredA = valuesA[index] - meanA
    const centeredB = valuesB[index] - meanB
    varianceA += centeredA ** 2
    varianceB += centeredB ** 2
    covariance += centeredA * centeredB
  }
  if (varianceA === 0 || varianceB === 0) return null
  return covariance / (varianceA ** 0.5 * varianceB ** 0.5)
}

function averageRanks(values) {
  const order = values.map((value, index) => ({ value, index }))
    .sort((left, right) => left.value - right.value)
  const ranks = Array(values.length).fill(0)
  let start = 0
  while (start < order.length) {
    let end = start
    while (end + 1 < order.length && order[end + 1].value === order[start].value) end += 1
    const average = (start + end) / 2 + 1
    for (let index = start; index <= end; index += 1) ranks[order[index].index] = average
    start = end + 1
  }
  return ranks
}

export function computePearsonDelta(pointsA, pointsB, window) {
  const pairs = computeDeltaPairs(pointsA, pointsB, window)
  if (pairs.length < 5) return null
  return pearson(pairs.map((pair) => pair.deltaA), pairs.map((pair) => pair.deltaB))
}

export function computeSpearmanDelta(pointsA, pointsB, window) {
  const pairs = computeDeltaPairs(pointsA, pointsB, window)
  if (pairs.length < 5) return null
  return pearson(
    averageRanks(pairs.map((pair) => pair.deltaA)),
    averageRanks(pairs.map((pair) => pair.deltaB)),
  )
}

export function correlationStrength(absPearson) {
  invariant(typeof absPearson === 'number' && Number.isFinite(absPearson), 'correlação deve ser finita.')
  return absPearson >= 0.7 ? 'forte' : absPearson >= 0.3 ? 'moderada' : 'fraca'
}

export function renderConcordanceStatement({
  concordant,
  intervals,
  windowStart,
  windowEnd,
  labelA,
  labelB,
}) {
  return `Em ${concordant} dos ${intervals} intervalos anuais entre ${windowStart} e `
    + `${windowEnd}, ${labelA} e ${labelB} variaram no mesmo sentido.`
}

function renderComovementSegment(label, movement) {
  let direction
  if (movement.delta === 0) {
    direction = 'estável'
  } else {
    const directionLabel = movement.delta > 0 ? 'alta' : 'queda'
    if (movement.deltaKind === 'pontos') {
      const magnitude = formatDecimalComma(Math.abs(movement.delta), 1)
      direction = `${directionLabel} de ${magnitude} ${magnitude === '1,0' ? 'ponto' : 'pontos'}`
    } else if (movement.valueStart > 0) {
      const magnitude = formatDecimalComma(
        Math.abs(movement.delta) / movement.valueStart * 100,
        1,
      )
      direction = `${directionLabel} de ${magnitude}%`
    } else {
      direction = directionLabel
    }
  }
  return `${label}, de ${formatPublicNumber(movement.valueStart)} em ${movement.effStart} para `
    + `${formatPublicNumber(movement.valueEnd)} em ${movement.effEnd} (${direction})`
}

export function renderComovementStatement({ a, b, labelA, labelB }) {
  return `Movimento acumulado na janela: ${renderComovementSegment(labelA, a)}; `
    + `${renderComovementSegment(labelB, b)}.`
}

export function renderCorrelationStatement({
  windowStart,
  windowEnd,
  pearsonDelta,
  strength,
  direction,
}) {
  if (direction === 'nula') {
    return `Na janela de ${windowStart} a ${windowEnd}, a correlação entre as variações anuais `
      + 'das duas séries é nula.'
  }
  return `Na janela de ${windowStart} a ${windowEnd}, a correlação entre as variações anuais `
    + `das duas séries é de ${formatDecimalComma(pearsonDelta, 2)} — ${strength} e ${direction}.`
}

export function renderLaggedStatement({
  aSeriesLabel,
  bSeriesLabel,
  lagYears,
  rationale,
  windowA,
  windowB,
  concordant,
  intervals,
  correlation,
  reasonCode,
}) {
  if (reasonCode !== undefined) {
    const reasonLabel = reasonCode === 'defasagem_sem_janela_suficiente'
      ? 'a janela comum às duas séries é curta demais para a leitura'
      : 'uma das séries não está disponível na região'
    return `A leitura defasada de ${aSeriesLabel} sobre ${bSeriesLabel} não é publicada nesta `
      + `região: ${reasonLabel}.`
  }
  const base = `Com defasagem de ${lagYears} anos — ${rationale} —, em ${concordant} dos `
    + `${intervals} intervalos anuais ${aSeriesLabel} (${windowA.start} a ${windowA.end}) e `
    + `${bSeriesLabel} (${windowB.start} a ${windowB.end}) variaram no mesmo sentido`
  if (correlation?.reasonCode !== undefined) return `${base}.`
  return `${base}; a correlação das variações anuais nessa defasagem é de `
    + `${formatDecimalComma(correlation.pearsonDelta, 2)}.`
}

export function renderContrastStatement({
  totalComparable,
  rank,
  direction,
  label,
  sameDirectionCount,
}) {
  const position = rank === 1 ? 'a maior' : `a ${rank}ª maior`
  return `Entre as ${totalComparable} regiões comparáveis do estado, esta é ${position} `
    + `${direction} acumulada de ${label} nessa janela; ${sameDirectionCount} das `
    + `${totalComparable} regiões registraram ${direction}.`
}

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
 * Temas de agenda do PNE — a ponte Vocações → PNE (decisão `V2-D6`).
 *
 * Mesma divisão de trabalho do universo e do estatuto: um enum fechado declara o
 * tema, e a plataforma escreve a frase pública. Aqui a razão é mais forte que
 * estilo — é o que mantém a ponte do lado certo da fronteira do número futuro. O
 * tema nomeia **a meta**, não o número dela: "Universalização e permanência no
 * ensino médio", nunca "meta 3" nem "atingir 85% até 2031". Um número de meta com
 * valor é justamente a alegação que o plano proíbe, e o enum fechado torna
 * impossível escrevê-lo por descuido no rótulo.
 *
 * O vocabulário é do lado da plataforma porque o PNE é do lado da plataforma: a
 * camada de pesquisa do Vocações não conhece meta nem estratégia do PNE. A ponte
 * é, por natureza, editorial desta camada — como a moldura de `buildFraming`.
 */
export const AGENDA_THEME_LABELS = Object.freeze({
  ensino_medio: 'Universalização e permanência no ensino médio',
  educacao_profissional: 'Educação profissional e técnica',
  eja: 'Educação de jovens e adultos',
  alfabetizacao: 'Alfabetização na idade certa',
  formacao_docente: 'Formação e valorização dos profissionais do ensino',
  oferta_e_rede: 'Oferta e organização da rede',
  gestao_e_planejamento: 'Gestão e planejamento da educação',
})

export const AGENDA_THEMES = Object.freeze(Object.keys(AGENDA_THEME_LABELS))

/*
 * Camada de conclusões (V2-D8). O enum da pesquisa morre na fronteira: o
 * documento público carrega somente estes rótulos, e o validador resolve o
 * rótulo de volta à construção apenas para conferir sua gramática.
 */
export const SYNTHESIS_KIND_LABELS = Object.freeze({
  observed: 'Do observado',
  state_position: 'De posição na comparação estadual',
  scenario_invariant: 'Sustentado nos quatro cenários',
  agenda: 'Frentes da agenda mobilizadas',
})

export const SYNTHESIS_REQUIRED_OPENERS = Object.freeze({
  observed: 'Conclui-se do observado que',
  state_position: 'Conclui-se que',
  scenario_invariant: 'Conclui-se que',
  agenda: 'Conclui-se que',
})

export const SYNTHESIS_FRAMING = Object.freeze({
  label: 'O que se conclui',
  description:
    'Conclusões compostas a partir do que foi observado, da comparação estadual e, onde existem, '
    + 'dos quatro cenários publicados para a região.',
  methodNote:
    'As frases seguem quatro construções fixas e são reverificadas contra as séries, associações, '
    + 'pares e âncoras deste documento. A conclusão de agenda usa somente os temas presentes nos '
    + 'quatro cenários publicados do próprio documento.',
})

const SYNTHESIS_KIND_BY_LABEL = new Map(
  Object.entries(SYNTHESIS_KIND_LABELS).map(([kind, label]) => [label, kind]),
)

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
  label: 'O que o futuro do território exige da educação?',
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
    + 'nesta página são os blocos anteriores: o retrato do território, a leitura entre educação '
    + 'e território, as transformações simultâneas e as relações observadas por triagem.',
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
  'synthesis',
  'territoryPortrait',
  'associations',
  'temporalPairs',
  'screenedRelations',
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
  'municipalPackageSha256',
  'synthesisPackageSha256',
])

const SYNTHESIS_FIELDS = new Set([
  'label',
  'description',
  'methodNote',
  'items',
  'absentKinds',
])
const SYNTHESIS_ITEM_REQUIRED_FIELDS = new Set(['kindLabel', 'statement'])
const SYNTHESIS_ITEM_OPTIONAL_FIELDS = new Set(['basisLabel'])
const SYNTHESIS_ABSENCE_FIELDS = new Set(['kindLabel', 'statement'])

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
  'associativeReading',
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
  'associativeReading',
])

const TEMPORAL_PAIRS_BLOCK_FIELDS = new Set(['label', 'description', 'items', 'laggedItems'])
const ASSOCIATION_READING_FIELDS = new Set([
  'grammarVersion',
  'methodNote',
  'factorReadings',
  'stateContrast',
])
const FACTOR_READING_FIELDS = new Set([
  'outcomeSeriesId',
  'factorSeriesId',
  'directionConcordance',
  'comovement',
  'correlation',
])
const TEMPORAL_READING_FIELDS = new Set([
  'grammarVersion',
  'methodNote',
  'directionConcordance',
  'comovement',
  'correlation',
  'stateContrast',
])
const REASON_FIELDS = new Set(['reasonCode'])
const DIRECTION_CONCORDANCE_FIELDS = new Set([
  'windowStart',
  'windowEnd',
  'intervals',
  'concordant',
  'opposite',
  'ties',
  'statement',
])
const COMOVEMENT_FIELDS_BY_ROLE = Object.freeze({
  association: new Set(['outcome', 'factor', 'statement']),
  temporal: new Set(['a', 'b', 'statement']),
  screened: new Set(['a', 'b', 'statement']),
})
const COMOVEMENT_SERIES_FIELDS = new Set([
  'seriesId',
  'effStart',
  'effEnd',
  'valueStart',
  'valueEnd',
  'delta',
  'deltaKind',
])
const CORRELATION_FIELDS = new Set([
  'intervals',
  'pearsonDelta',
  'spearmanDelta',
  'strength',
  'direction',
  'statement',
])
const LAGGED_CORRELATION_FIELDS = new Set([
  'intervals',
  'pearsonDelta',
  'spearmanDelta',
  'strength',
  'direction',
])
const STATE_CONTRAST_FIELDS = new Set([
  'seriesId',
  'statistic',
  'value',
  'rank',
  'totalComparable',
  'sameDirectionCount',
  'direction',
  'statement',
])
const LAGGED_ITEM_FIELDS = new Set([
  'aSeriesId',
  'bSeriesId',
  'lagYears',
  'rationale',
  'windowA',
  'windowB',
  'intervals',
  'concordant',
  'opposite',
  'ties',
  'correlation',
  'statement',
])
const LAGGED_ABSENCE_FIELDS = new Set([
  'aSeriesId',
  'bSeriesId',
  'lagYears',
  'reasonCode',
  'statement',
])
const SCREENED_RELATIONS_FIELDS = new Set([
  'label',
  'description',
  'methodNote',
  'criteria',
  'items',
])
const SCREENED_CRITERIA_FIELDS = new Set(['minIntervals', 'minAbsPearson', 'maxItems'])
const SCREENED_RELATION_FIELDS = new Set([
  'relationId',
  'seriesAId',
  'seriesBId',
  'window',
  'directionConcordance',
  'comovement',
  'correlation',
  'originStatement',
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
  'municipalLayer',
])

/*
 * Camada municipal (Rodada 5 do V2, sucessora da D11) — vive dentro do bloco de
 * cenários, e por isso só existe onde há cenário. Para cada município da região:
 * a composição observada dele (uma linha por dimensão que se decompõe ao
 * município) e, por cenário, a leitura de exposição derivada dessa composição.
 *
 * `municipalityId` é o código IBGE de sete dígitos — identificador público
 * oficial, não vocabulário de processo. `dimensionLabel` e `statement` são texto
 * já composto pela camada de pesquisa, como o `observedStatement` da associação;
 * a plataforma não reescreve, confere. A alegação proibida é frase inteira com o
 * abridor do contrato, e a guarda de linguagem faz a varredura de número futuro,
 * probabilidade e causalidade.
 */
const MUNICIPAL_LAYER_FIELDS = new Set([
  'label',
  'description',
  'methodNote',
  'dimensions',
  'undecomposableDomains',
  'municipalities',
])
const MUNICIPAL_DIMENSION_FIELDS = new Set([
  'label',
  'sourceLabel',
  'unitLabel',
  'periodLabel',
  'kindLabel',
  'universeLabel',
])
const MUNICIPAL_UNDECOMPOSABLE_FIELDS = new Set(['label', 'consultedSource', 'reason'])
const MUNICIPAL_MUNICIPALITY_FIELDS = new Set([
  'municipalityId',
  'name',
  'composition',
  'scenarioExposure',
])
const MUNICIPAL_COMPOSITION_FIELDS = new Set(['dimensionLabel', 'statement'])
const MUNICIPAL_EXPOSURE_FIELDS = new Set([
  'order',
  'exposureStatement',
  'allowedInterpretation',
  'prohibitedClaim',
])
const MUNICIPALITY_ID_PATTERN = /^\d{7}$/

/** Frase pública da natureza de cada dimensão municipal — enum → frase. */
export const MUNICIPAL_KIND_LABELS = Object.freeze({
  share: 'Participação: o valor do município sobre a soma dos municípios da região.',
  rate: 'Taxa municipal: a posição do município ante a mediana dos municípios da região, sem soma.',
})

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
  'agendaThemes',
  'contraryEvidence',
  'limits',
  'prohibitedClaim',
])

/*
 * O tema de agenda tem três campos e nenhum a mais: o enum (`theme`), a frase
 * pública do enum (`themeLabel`) e a frase de implicação que o sustenta
 * (`statement`). Não há campo de número de meta, nem de valor, nem de ano — de
 * propósito: o contrato não guarda o que ele proíbe.
 */
const SCENARIO_AGENDA_THEME_FIELDS = new Set(['theme', 'themeLabel', 'statement'])

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

function validateClosedFields(value, required, optional, label) {
  invariant(isRecord(value), `${label} deve ser um objeto.`)
  const keys = Object.keys(value)
  const accepted = new Set([...required, ...optional])
  const unexpected = keys.filter((key) => !accepted.has(key))
  const missing = [...required].filter((key) => !keys.includes(key))
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

function validateReasonBlock(candidate, label, allowedReasonCodes, expectedReasonCode = null) {
  validateExactFields(candidate, REASON_FIELDS, label)
  invariant(
    ASSOCIATIVE_REASON_CODE_SET.has(candidate.reasonCode),
    `${label}.reasonCode fora do contrato: ${candidate.reasonCode}.`,
  )
  invariant(
    allowedReasonCodes.has(candidate.reasonCode),
    `${label}.reasonCode não é admitido neste bloco: ${candidate.reasonCode}.`,
  )
  if (expectedReasonCode !== null) {
    invariant(
      candidate.reasonCode === expectedReasonCode,
      `${label}.reasonCode diverge da recomputação: esperado ${expectedReasonCode}, `
      + `recebido ${candidate.reasonCode}.`,
    )
  }
  return candidate
}

function validateAssociativeSeries(seriesId, label, seriesById) {
  validatePublicId(seriesId, label)
  const serie = seriesById.get(seriesId)
  invariant(serie !== undefined, `${label} não resolve em nenhuma série do documento.`)
  invariant(
    serie.periodGranularity === 'annual',
    `${label} referencia série não anual; a leitura associativa exige séries anuais.`,
  )
  return serie
}

function expectedDeltaKind(serie) {
  return serie.ratioOf === null ? 'nivel' : 'pontos'
}

function validateDirectionConcordance(candidate, label, serieA, serieB, window) {
  const expected = computeDirectionConcordance(serieA.points, serieB.points, window)
  if (expected.reasonCode !== undefined) {
    return validateReasonBlock(candidate, label, COMPARISON_REASON_CODES, expected.reasonCode)
  }
  validateExactFields(candidate, DIRECTION_CONCORDANCE_FIELDS, label)
  for (const field of ['windowStart', 'windowEnd', 'intervals', 'concordant', 'opposite', 'ties']) {
    invariant(Number.isInteger(candidate[field]), `${label}.${field} deve ser inteiro.`)
    invariant(
      candidate[field] === expected[field],
      `${label}.${field} diverge da recomputação: esperado ${expected[field]}, `
      + `recebido ${candidate[field]}.`,
    )
  }
  validateText(candidate.statement, `${label}.statement`)
  const statement = renderConcordanceStatement({
    ...expected,
    labelA: serieA.label,
    labelB: serieB.label,
  })
  invariant(
    candidate.statement === statement,
    `${label}.statement diverge do template T-CONC.`,
  )
  return candidate
}

function validateComovementSeries(candidate, expected, seriesId, label) {
  validateExactFields(candidate, COMOVEMENT_SERIES_FIELDS, label)
  invariant(candidate.seriesId === seriesId, `${label}.seriesId diverge da série esperada.`)
  for (const field of ['effStart', 'effEnd']) {
    invariant(Number.isInteger(candidate[field]), `${label}.${field} deve ser inteiro.`)
  }
  for (const field of ['valueStart', 'valueEnd', 'delta']) {
    invariant(
      typeof candidate[field] === 'number' && Number.isFinite(candidate[field]),
      `${label}.${field} deve ser número finito.`,
    )
  }
  invariant(
    COMOVEMENT_DELTA_KINDS.has(candidate.deltaKind),
    `${label}.deltaKind fora do contrato: ${candidate.deltaKind}.`,
  )
  for (const field of ['effStart', 'effEnd', 'valueStart', 'valueEnd', 'delta', 'deltaKind']) {
    invariant(
      candidate[field] === expected[field],
      `${label}.${field} diverge da recomputação: esperado ${expected[field]}, `
      + `recebido ${candidate[field]}.`,
    )
  }
  return candidate
}

function validateComovement(candidate, label, serieA, serieB, window, role) {
  const expectedA = computeComovement(serieA.points, window, expectedDeltaKind(serieA))
  const expectedB = computeComovement(serieB.points, window, expectedDeltaKind(serieB))
  if (expectedA.reasonCode !== undefined || expectedB.reasonCode !== undefined) {
    return validateReasonBlock(
      candidate,
      label,
      COMPARISON_REASON_CODES,
      'sem_intervalos_comparaveis',
    )
  }
  validateExactFields(candidate, COMOVEMENT_FIELDS_BY_ROLE[role], label)
  const keyA = role === 'association' ? 'outcome' : 'a'
  const keyB = role === 'association' ? 'factor' : 'b'
  validateComovementSeries(candidate[keyA], expectedA, serieA.seriesId, `${label}.${keyA}`)
  validateComovementSeries(candidate[keyB], expectedB, serieB.seriesId, `${label}.${keyB}`)
  validateText(candidate.statement, `${label}.statement`)
  const statement = renderComovementStatement({
    a: expectedA,
    b: expectedB,
    labelA: serieA.label,
    labelB: serieB.label,
  })
  invariant(candidate.statement === statement, `${label}.statement diverge do template T-COMOV.`)
  return candidate
}

function correlationFromPairs(pairs) {
  if (pairs.length < 5) return { reasonCode: 'janela_curta' }
  const valuesA = pairs.map((pair) => pair.deltaA)
  const valuesB = pairs.map((pair) => pair.deltaB)
  const pearsonDelta = pearson(valuesA, valuesB)
  if (pearsonDelta === null) return { reasonCode: 'variancia_nula' }
  return {
    intervals: pairs.length,
    pearsonDelta,
    spearmanDelta: pearson(averageRanks(valuesA), averageRanks(valuesB)),
    strength: correlationStrength(Math.abs(pearsonDelta)),
    direction: pearsonDelta > 0 ? 'positiva' : pearsonDelta < 0 ? 'negativa' : 'nula',
  }
}

function validateCorrelationFromPairs(
  candidate,
  label,
  pairs,
  { window = null, statement = true } = {},
) {
  const expected = correlationFromPairs(pairs)
  if (expected.reasonCode !== undefined) {
    return validateReasonBlock(candidate, label, CORRELATION_REASON_CODES, expected.reasonCode)
  }
  validateExactFields(
    candidate,
    statement ? CORRELATION_FIELDS : LAGGED_CORRELATION_FIELDS,
    label,
  )
  invariant(Number.isInteger(candidate.intervals), `${label}.intervals deve ser inteiro.`)
  invariant(
    candidate.intervals === expected.intervals,
    `${label}.intervals diverge da recomputação.`,
  )
  for (const field of ['pearsonDelta', 'spearmanDelta']) {
    invariant(
      typeof candidate[field] === 'number' && Number.isFinite(candidate[field]),
      `${label}.${field} deve ser número finito.`,
    )
    const rounded = roundHalfAwayFromZero(expected[field], 2)
    invariant(
      candidate[field] === rounded,
      `${label}.${field} diverge da recomputação: esperado ${rounded}, `
      + `recebido ${candidate[field]}.`,
    )
  }
  invariant(
    ASSOCIATIVE_STRENGTHS.has(candidate.strength),
    `${label}.strength fora do contrato: ${candidate.strength}.`,
  )
  invariant(
    candidate.strength === expected.strength,
    `${label}.strength diverge do bin recomputado: esperado ${expected.strength}, `
    + `recebido ${candidate.strength}.`,
  )
  invariant(
    ASSOCIATIVE_DIRECTIONS.has(candidate.direction),
    `${label}.direction fora do contrato: ${candidate.direction}.`,
  )
  invariant(
    candidate.direction === expected.direction,
    `${label}.direction diverge do sinal recomputado: esperado ${expected.direction}, `
    + `recebido ${candidate.direction}.`,
  )
  if (statement) {
    validateText(candidate.statement, `${label}.statement`)
    const expectedStatement = renderCorrelationStatement({
      windowStart: window.start,
      windowEnd: window.end,
      pearsonDelta: candidate.pearsonDelta,
      strength: candidate.strength,
      direction: candidate.direction,
    })
    invariant(
      candidate.statement === expectedStatement,
      `${label}.statement diverge do template T-CORR.`,
    )
  }
  return candidate
}

function validateCorrelation(candidate, label, serieA, serieB, window) {
  return validateCorrelationFromPairs(
    candidate,
    label,
    computeDeltaPairs(serieA.points, serieB.points, window),
    { window },
  )
}

function validateStateContrast(candidate, label, targetSerie) {
  if (isRecord(candidate) && Object.prototype.hasOwnProperty.call(candidate, 'reasonCode')) {
    return validateReasonBlock(candidate, label, CONTRAST_REASON_CODES)
  }
  validateExactFields(candidate, STATE_CONTRAST_FIELDS, label)
  invariant(candidate.seriesId === targetSerie.seriesId, `${label}.seriesId diverge da série-alvo.`)
  const expectedStatistic = expectedDeltaKind(targetSerie) === 'pontos'
    ? 'variacao_em_pontos'
    : 'variacao_percentual'
  invariant(
    CONTRAST_STATISTICS.has(candidate.statistic) && candidate.statistic === expectedStatistic,
    `${label}.statistic diverge da unidade da série-alvo.`,
  )
  invariant(
    typeof candidate.value === 'number' && Number.isFinite(candidate.value),
    `${label}.value deve ser número finito.`,
  )
  invariant(
    Number.isInteger(candidate.rank) && candidate.rank >= 1,
    `${label}.rank deve ser inteiro positivo.`,
  )
  invariant(
    Number.isInteger(candidate.totalComparable) && candidate.totalComparable >= 2,
    `${label}.totalComparable deve ser inteiro ao menos 2.`,
  )
  invariant(candidate.rank <= candidate.totalComparable, `${label}.rank excede totalComparable.`)
  invariant(
    Number.isInteger(candidate.sameDirectionCount)
      && candidate.sameDirectionCount >= 1
      && candidate.sameDirectionCount <= candidate.totalComparable,
    `${label}.sameDirectionCount deve estar entre 1 e totalComparable.`,
  )
  invariant(
    CONTRAST_DIRECTIONS.has(candidate.direction),
    `${label}.direction fora do contrato: ${candidate.direction}.`,
  )
  validateText(candidate.statement, `${label}.statement`)
  const statement = renderContrastStatement({
    totalComparable: candidate.totalComparable,
    rank: candidate.rank,
    direction: candidate.direction,
    label: targetSerie.label,
    sameDirectionCount: candidate.sameDirectionCount,
  })
  invariant(candidate.statement === statement, `${label}.statement diverge do template T-CONTRASTE.`)
  return candidate
}

function validateAssociationReading(candidate, label, association, seriesById) {
  validateExactFields(candidate, ASSOCIATION_READING_FIELDS, label)
  invariant(
    candidate.grammarVersion === ASSOCIATIVE_GRAMMAR_VERSION,
    `${label}.grammarVersion fora do contrato.`,
  )
  invariant(candidate.methodNote === ASSOCIATIVE_METHOD_NOTE, `${label}.methodNote fora do contrato.`)
  invariant(Array.isArray(candidate.factorReadings), `${label}.factorReadings deve ser uma lista.`)
  invariant(
    candidate.factorReadings.length === association.territorialFactors.length,
    `${label}.factorReadings não cobre todos os fatores territoriais.`,
  )
  const outcomeSerie = validateAssociativeSeries(
    association.educationOutcome.seriesId,
    `${label}.outcomeSeriesId`,
    seriesById,
  )
  candidate.factorReadings.forEach((reading, index) => {
    const readingLabel = `${label}.factorReadings[${index}]`
    validateExactFields(reading, FACTOR_READING_FIELDS, readingLabel)
    const factorReference = association.territorialFactors[index]
    invariant(
      reading.outcomeSeriesId === association.educationOutcome.seriesId,
      `${readingLabel}.outcomeSeriesId diverge do resultado educacional da associação.`,
    )
    invariant(
      reading.factorSeriesId === factorReference.seriesId,
      `${readingLabel}.factorSeriesId diverge do fator territorial correspondente.`,
    )
    const factorSerie = validateAssociativeSeries(
      reading.factorSeriesId,
      `${readingLabel}.factorSeriesId`,
      seriesById,
    )
    validateDirectionConcordance(
      reading.directionConcordance,
      `${readingLabel}.directionConcordance`,
      outcomeSerie,
      factorSerie,
      association.window,
    )
    validateComovement(
      reading.comovement,
      `${readingLabel}.comovement`,
      outcomeSerie,
      factorSerie,
      association.window,
      'association',
    )
    validateCorrelation(
      reading.correlation,
      `${readingLabel}.correlation`,
      outcomeSerie,
      factorSerie,
      association.window,
    )
  })
  validateStateContrast(candidate.stateContrast, `${label}.stateContrast`, outcomeSerie)
  return candidate
}

function validateTemporalReading(candidate, label, pair, seriesById) {
  validateExactFields(candidate, TEMPORAL_READING_FIELDS, label)
  invariant(
    candidate.grammarVersion === ASSOCIATIVE_GRAMMAR_VERSION,
    `${label}.grammarVersion fora do contrato.`,
  )
  invariant(candidate.methodNote === ASSOCIATIVE_METHOD_NOTE, `${label}.methodNote fora do contrato.`)
  const serieA = validateAssociativeSeries(pair.seriesA.seriesId, `${label}.seriesA`, seriesById)
  const serieB = validateAssociativeSeries(pair.seriesB.seriesId, `${label}.seriesB`, seriesById)
  validateDirectionConcordance(
    candidate.directionConcordance,
    `${label}.directionConcordance`,
    serieA,
    serieB,
    pair.window,
  )
  validateComovement(
    candidate.comovement,
    `${label}.comovement`,
    serieA,
    serieB,
    pair.window,
    'temporal',
  )
  validateCorrelation(
    candidate.correlation,
    `${label}.correlation`,
    serieA,
    serieB,
    pair.window,
  )
  validateStateContrast(candidate.stateContrast, `${label}.stateContrast`, serieB)
  return candidate
}

function allLaggedDeltaPairs(serieA, serieB, lagYears) {
  const periodsA = serieA.points.map((point) => point.period)
  const window = { start: Math.min(...periodsA), end: Math.max(...periodsA) }
  return computeDeltaPairs(serieA.points, serieB.points, window, lagYears)
}

function validateLaggedItem(candidate, label, seriesById, referenceYear) {
  invariant(isRecord(candidate), `${label} deve ser um objeto.`)
  const isAbsence = Object.prototype.hasOwnProperty.call(candidate, 'reasonCode')
  validateExactFields(candidate, isAbsence ? LAGGED_ABSENCE_FIELDS : LAGGED_ITEM_FIELDS, label)
  invariant(candidate.lagYears === 6, `${label}.lagYears deve ser 6 nesta rodada.`)
  const serieA = validateAssociativeSeries(candidate.aSeriesId, `${label}.aSeriesId`, seriesById)
  const serieB = validateAssociativeSeries(candidate.bSeriesId, `${label}.bSeriesId`, seriesById)
  invariant(serieA.seriesId !== serieB.seriesId, `${label} compara uma série com ela mesma.`)
  const pairs = allLaggedDeltaPairs(serieA, serieB, candidate.lagYears)

  if (pairs.length < 5) {
    invariant(isAbsence, `${label} deveria declarar ausência por janela defasada curta.`)
    validateReasonBlock(
      { reasonCode: candidate.reasonCode },
      `${label}.reasonCode`,
      LAGGED_REASON_CODES,
      'defasagem_sem_janela_suficiente',
    )
    const statement = renderLaggedStatement({
      aSeriesLabel: serieA.label,
      bSeriesLabel: serieB.label,
      lagYears: candidate.lagYears,
      reasonCode: candidate.reasonCode,
    })
    invariant(candidate.statement === statement, `${label}.statement diverge do template T-LAG.`)
    return candidate
  }

  invariant(!isAbsence, `${label} declara ausência apesar de haver janela defasada suficiente.`)
  invariant(candidate.rationale === LAGGED_RATIONALE, `${label}.rationale fora do contrato.`)
  validateWindow(candidate.windowA, `${label}.windowA`, referenceYear)
  validateWindow(candidate.windowB, `${label}.windowB`, referenceYear)
  const firstPeriod = pairs[0].period
  const lastPeriod = pairs[pairs.length - 1].period
  const expectedWindowA = { start: firstPeriod - 1, end: lastPeriod }
  const expectedWindowB = {
    start: expectedWindowA.start + candidate.lagYears,
    end: expectedWindowA.end + candidate.lagYears,
  }
  for (const field of ['start', 'end']) {
    invariant(
      candidate.windowA[field] === expectedWindowA[field],
      `${label}.windowA.${field} diverge da recomputação.`,
    )
    invariant(
      candidate.windowB[field] === expectedWindowB[field],
      `${label}.windowB.${field} diverge da recomputação.`,
    )
  }
  const concordant = pairs.filter(({ deltaA, deltaB }) =>
    directionSign(deltaA) * directionSign(deltaB) === 1).length
  const opposite = pairs.filter(({ deltaA, deltaB }) =>
    directionSign(deltaA) * directionSign(deltaB) === -1).length
  const expectedCounts = {
    intervals: pairs.length,
    concordant,
    opposite,
    ties: pairs.length - concordant - opposite,
  }
  for (const [field, expected] of Object.entries(expectedCounts)) {
    invariant(Number.isInteger(candidate[field]), `${label}.${field} deve ser inteiro.`)
    invariant(candidate[field] === expected, `${label}.${field} diverge da recomputação.`)
  }
  validateCorrelationFromPairs(candidate.correlation, `${label}.correlation`, pairs, {
    statement: false,
  })
  validateText(candidate.statement, `${label}.statement`)
  const statement = renderLaggedStatement({
    aSeriesLabel: serieA.label,
    bSeriesLabel: serieB.label,
    lagYears: candidate.lagYears,
    rationale: candidate.rationale,
    windowA: expectedWindowA,
    windowB: expectedWindowB,
    concordant,
    intervals: pairs.length,
    correlation: candidate.correlation,
  })
  invariant(candidate.statement === statement, `${label}.statement diverge do template T-LAG.`)
  return candidate
}

function validateScreenedRelations(candidate, label, seriesById, referenceYear) {
  validateExactFields(candidate, SCREENED_RELATIONS_FIELDS, label)
  invariant(candidate.label === 'Relações observadas por triagem', `${label}.label fora do contrato.`)
  validateText(candidate.description, `${label}.description`)
  invariant(candidate.methodNote === ASSOCIATIVE_METHOD_NOTE, `${label}.methodNote fora do contrato.`)
  validateExactFields(candidate.criteria, SCREENED_CRITERIA_FIELDS, `${label}.criteria`)
  for (const [field, expected] of Object.entries(SCREENED_RELATIONS_CRITERIA)) {
    invariant(candidate.criteria[field] === expected, `${label}.criteria.${field} fora do contrato.`)
  }
  invariant(Array.isArray(candidate.items), `${label}.items deve ser uma lista.`)
  invariant(
    candidate.items.length <= SCREENED_RELATIONS_CRITERIA.maxItems,
    `${label}.items excede o teto de triagem.`,
  )
  const relationIds = new Set()
  let previous = null
  candidate.items.forEach((item, index) => {
    const itemLabel = `${label}.items[${index}]`
    validateExactFields(item, SCREENED_RELATION_FIELDS, itemLabel)
    const serieA = validateAssociativeSeries(item.seriesAId, `${itemLabel}.seriesAId`, seriesById)
    const serieB = validateAssociativeSeries(item.seriesBId, `${itemLabel}.seriesBId`, seriesById)
    invariant(serieA.seriesId !== serieB.seriesId, `${itemLabel} compara uma série com ela mesma.`)
    invariant(
      item.relationId === `${item.seriesAId}--${item.seriesBId}`,
      `${itemLabel}.relationId não deriva das duas séries.`,
    )
    invariant(!relationIds.has(item.relationId), `${itemLabel}.relationId repetido.`)
    relationIds.add(item.relationId)
    validateWindow(item.window, `${itemLabel}.window`, referenceYear)
    validateWindowAgainstSeries(item.window, serieA, `${itemLabel}.seriesAId`)
    validateWindowAgainstSeries(item.window, serieB, `${itemLabel}.seriesBId`)
    validateDirectionConcordance(
      item.directionConcordance,
      `${itemLabel}.directionConcordance`,
      serieA,
      serieB,
      item.window,
    )
    validateComovement(
      item.comovement,
      `${itemLabel}.comovement`,
      serieA,
      serieB,
      item.window,
      'screened',
    )
    validateCorrelation(item.correlation, `${itemLabel}.correlation`, serieA, serieB, item.window)
    const intervals = computeDeltaPairs(serieA.points, serieB.points, item.window).length
    const pearsonDelta = computePearsonDelta(serieA.points, serieB.points, item.window)
    invariant(
      intervals >= SCREENED_RELATIONS_CRITERIA.minIntervals,
      `${itemLabel} não alcança o mínimo de intervalos da triagem.`,
    )
    invariant(
      pearsonDelta !== null
        && Math.abs(pearsonDelta) >= SCREENED_RELATIONS_CRITERIA.minAbsPearson,
      `${itemLabel} não alcança o limiar de correlação da triagem.`,
    )
    validateText(item.originStatement, `${itemLabel}.originStatement`)
    invariant(
      item.originStatement === SCREENED_ORIGIN_STATEMENT,
      `${itemLabel}.originStatement fora do contrato.`,
    )
    const ordering = { absPearson: Math.abs(pearsonDelta), relationId: item.relationId }
    if (previous !== null) {
      invariant(
        previous.absPearson > ordering.absPearson
          || (previous.absPearson === ordering.absPearson
            && previous.relationId.localeCompare(ordering.relationId) <= 0),
        `${itemLabel} está fora da ordem determinística da triagem.`,
      )
    }
    previous = ordering
  })
  return candidate
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
  validateAssociationReading(
    candidate.associativeReading,
    `${label}.associativeReading`,
    candidate,
    seriesById,
  )
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
  validateTemporalReading(
    candidate.associativeReading,
    `${label}.associativeReading`,
    candidate,
    seriesById,
  )
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
  const implicationStatements = new Set()
  candidate.educationImplications.forEach((implication, index) => {
    const implicationLabel = `${label}.educationImplications[${index}]`
    validateExactFields(implication, SCENARIO_IMPLICATION_FIELDS, implicationLabel)
    validateText(implication.stageLabel, `${implicationLabel}.stageLabel`)
    validateText(implication.statement, `${implicationLabel}.statement`)
    implicationStatements.add(implication.statement)
  })

  /*
   * Temas de agenda — a ponte Vocações → PNE. A regra que fecha a fronteira do
   * número futuro é a mesma disciplina da âncora: o tema não digita frase, ele
   * aponta para uma implicação **já publicada neste cenário**. `statement`
   * precisa ser byte-idêntico a uma das implicações acima; um tema que
   * inventasse a própria frase abriria uma porta de texto que ninguém guardou.
   */
  invariant(
    Array.isArray(candidate.agendaThemes) && candidate.agendaThemes.length > 0,
    `${label}.agendaThemes deve trazer ao menos um tema de agenda.`,
  )
  const seenThemes = new Set()
  candidate.agendaThemes.forEach((theme, index) => {
    const themeLabel = `${label}.agendaThemes[${index}]`
    validateExactFields(theme, SCENARIO_AGENDA_THEME_FIELDS, themeLabel)
    invariant(
      AGENDA_THEMES.includes(theme.theme),
      `${themeLabel}.theme fora do contrato: ${theme.theme}.`,
    )
    invariant(
      theme.themeLabel === AGENDA_THEME_LABELS[theme.theme],
      `${themeLabel}.themeLabel não é a frase declarada para o tema ${theme.theme}.`,
    )
    invariant(
      !seenThemes.has(theme.theme),
      `${themeLabel}.theme repetido no mesmo cenário: ${theme.theme}.`,
    )
    seenThemes.add(theme.theme)
    validateText(theme.statement, `${themeLabel}.statement`)
    invariant(
      implicationStatements.has(theme.statement),
      `${themeLabel}.statement não é a frase de nenhuma implicação educacional deste cenário.`,
    )
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

/*
 * Camada municipal — a leitura de cada município dentro do cenário regional.
 *
 * O que a torna honesta não é o que ela afirma, é o que ela recusa afirmar: o
 * `statement` de composição é observado e passado da pesquisa sem reescrita; a
 * exposição é derivada dessa composição, com a alegação proibida escrita ao lado
 * em frase inteira; e a guarda de linguagem, que corre depois, barra número
 * futuro municipal, probabilidade, ranking e causalidade município←região.
 *
 * `scenarioOrders` é o conjunto de `order` dos cenários deste bloco: cada
 * município traz exatamente uma leitura de exposição por cenário, nem mais nem
 * menos — um município sem exposição para um cenário publicado deixaria um
 * cenário sem a sua leitura, e um `order` que não é de cenário nenhum apontaria
 * para um cenário que não existe.
 */
function validateMunicipalLayer(candidate, label, scenarioOrders) {
  validateExactFields(candidate, MUNICIPAL_LAYER_FIELDS, label)
  validateText(candidate.label, `${label}.label`)
  validateText(candidate.description, `${label}.description`)
  validateText(candidate.methodNote, `${label}.methodNote`)

  invariant(
    Array.isArray(candidate.dimensions) && candidate.dimensions.length > 0,
    `${label}.dimensions deve trazer ao menos uma dimensão.`,
  )
  const dimensionLabels = new Set()
  candidate.dimensions.forEach((dimension, index) => {
    const dimensionLabel = `${label}.dimensions[${index}]`
    validateExactFields(dimension, MUNICIPAL_DIMENSION_FIELDS, dimensionLabel)
    validateText(dimension.label, `${dimensionLabel}.label`)
    validateText(dimension.sourceLabel, `${dimensionLabel}.sourceLabel`)
    validateText(dimension.unitLabel, `${dimensionLabel}.unitLabel`)
    validateText(dimension.periodLabel, `${dimensionLabel}.periodLabel`)
    invariant(
      Object.values(MUNICIPAL_KIND_LABELS).includes(dimension.kindLabel),
      `${dimensionLabel}.kindLabel não é uma das frases de natureza do contrato.`,
    )
    invariant(
      dimension.universeLabel === null || UNIVERSE_LABEL_VALUES.includes(dimension.universeLabel),
      `${dimensionLabel}.universeLabel não é null nem uma das frases de universo do contrato.`,
    )
    invariant(
      !dimensionLabels.has(dimension.label),
      `${dimensionLabel}.label repetido: "${dimension.label}".`,
    )
    dimensionLabels.add(dimension.label)
  })

  invariant(
    Array.isArray(candidate.undecomposableDomains) && candidate.undecomposableDomains.length > 0,
    `${label}.undecomposableDomains deve declarar ao menos um domínio não decomponível.`,
  )
  candidate.undecomposableDomains.forEach((domain, index) => {
    const domainLabel = `${label}.undecomposableDomains[${index}]`
    validateExactFields(domain, MUNICIPAL_UNDECOMPOSABLE_FIELDS, domainLabel)
    validateText(domain.label, `${domainLabel}.label`)
    validateText(domain.consultedSource, `${domainLabel}.consultedSource`)
    validateText(domain.reason, `${domainLabel}.reason`)
  })

  invariant(
    Array.isArray(candidate.municipalities) && candidate.municipalities.length > 0,
    `${label}.municipalities deve trazer ao menos um município.`,
  )
  const municipalityIds = new Set()
  candidate.municipalities.forEach((municipality, index) => {
    const municipalityLabel = `${label}.municipalities[${index}]`
    validateExactFields(municipality, MUNICIPAL_MUNICIPALITY_FIELDS, municipalityLabel)
    invariant(
      typeof municipality.municipalityId === 'string'
        && MUNICIPALITY_ID_PATTERN.test(municipality.municipalityId),
      `${municipalityLabel}.municipalityId deve ser o código IBGE de sete dígitos.`,
    )
    invariant(
      !municipalityIds.has(municipality.municipalityId),
      `${municipalityLabel}.municipalityId repetido: ${municipality.municipalityId}.`,
    )
    municipalityIds.add(municipality.municipalityId)
    validateText(municipality.name, `${municipalityLabel}.name`)

    invariant(
      Array.isArray(municipality.composition) && municipality.composition.length > 0,
      `${municipalityLabel}.composition deve trazer ao menos uma linha.`,
    )
    municipality.composition.forEach((line, lineIndex) => {
      const lineLabel = `${municipalityLabel}.composition[${lineIndex}]`
      validateExactFields(line, MUNICIPAL_COMPOSITION_FIELDS, lineLabel)
      validateText(line.dimensionLabel, `${lineLabel}.dimensionLabel`)
      invariant(
        dimensionLabels.has(line.dimensionLabel),
        `${lineLabel}.dimensionLabel não é uma das dimensões declaradas na camada.`,
      )
      validateText(line.statement, `${lineLabel}.statement`)
    })

    invariant(
      Array.isArray(municipality.scenarioExposure)
        && municipality.scenarioExposure.length === scenarioOrders.size,
      `${municipalityLabel}.scenarioExposure deve trazer uma leitura por cenário `
      + `(${scenarioOrders.size}).`,
    )
    const seenOrders = new Set()
    municipality.scenarioExposure.forEach((exposure, exposureIndex) => {
      const exposureLabel = `${municipalityLabel}.scenarioExposure[${exposureIndex}]`
      validateExactFields(exposure, MUNICIPAL_EXPOSURE_FIELDS, exposureLabel)
      invariant(
        Number.isInteger(exposure.order) && scenarioOrders.has(exposure.order),
        `${exposureLabel}.order não é a ordem de nenhum cenário deste bloco.`,
      )
      invariant(!seenOrders.has(exposure.order), `${exposureLabel}.order repetido: ${exposure.order}.`)
      seenOrders.add(exposure.order)
      validateText(exposure.exposureStatement, `${exposureLabel}.exposureStatement`)
      validateText(exposure.allowedInterpretation, `${exposureLabel}.allowedInterpretation`)
      validateProhibitedClaim(exposure.prohibitedClaim, `${exposureLabel}.prohibitedClaim`)
    })
  })
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

  /*
   * A camada municipal é obrigatória onde há bloco de cenários: uma região que
   * publica cenário mas não os municípios dela deixaria a sucessora da D11 pela
   * metade sem que nada o acusasse. Ela recebe o conjunto de `order` deste bloco
   * para provar que cada município tem uma leitura por cenário, nem mais nem menos.
   */
  validateMunicipalLayer(candidate.municipalLayer, `${label}.municipalLayer`, orders)
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

export function synthesisAssociationBasisLabel(association) {
  return [
    association.educationOutcome.label,
    ...association.territorialFactors.map((factor) => factor.label),
  ].join(' · ')
}

export function synthesisTemporalPairBasisLabel(pair) {
  return pair.label
}

function synthesisNumberLabel(value) {
  invariant(Number.isFinite(value), 'a síntese tentou renderizar número não finito.')
  const displayValue = Number.isInteger(value) ? String(value) : value.toFixed(1)
  const [integer, fraction] = displayValue.split('.')
  const sign = integer.startsWith('-') ? '-' : ''
  const digits = sign === '' ? integer : integer.slice(1)
  const grouped = digits.replace(/\B(?=(\d{3})+(?!\d))/gu, ' ')
  return fraction === undefined ? `${sign}${grouped}` : `${sign}${grouped},${fraction}`
}

function synthesisPeriodYear(period, granularity) {
  return granularity === 'monthly' ? Math.floor(period / 100) : period
}

function synthesisSeriesEdges(reference, window, seriesById, label) {
  const serie = seriesById.get(reference.seriesId)
  invariant(serie !== undefined, `${label} cita série ausente: ${reference.seriesId}.`)
  const points = serie.points.filter((point) => {
    const year = synthesisPeriodYear(point.period, serie.periodGranularity)
    return year >= window.start && year <= window.end
  })
  invariant(points.length > 0, `${label} não encontra pontos da série dentro da janela.`)
  const start = points[0]
  const end = points[points.length - 1]
  return {
    label: reference.label,
    startValue: start.value,
    endValue: end.value,
  }
}

function renderObservedSynthesis(references, window, seriesById, label) {
  const clauses = references.map((reference, index) => {
    const edge = synthesisSeriesEdges(reference, window, seriesById, `${label}.series[${index}]`)
    return `${edge.label} passou de ${synthesisNumberLabel(edge.startValue)} para `
      + `${synthesisNumberLabel(edge.endValue)}`
  })
  invariant(clauses.length >= 2, `${label} precisa citar ao menos duas séries.`)
  return `Conclui-se do observado que, entre ${window.start} e ${window.end}, ${clauses[0]} `
    + `e, no mesmo período, ${clauses.slice(1).join(' e ')}.`
}

function expectedObservedSynthesis(associations, temporalPairs, seriesById) {
  const expected = new Map()
  for (const association of associations) {
    const basisLabel = synthesisAssociationBasisLabel(association)
    invariant(!expected.has(basisLabel), `basisLabel repetido na síntese observada: "${basisLabel}".`)
    expected.set(
      basisLabel,
      renderObservedSynthesis(
        [association.educationOutcome, ...association.territorialFactors],
        association.window,
        seriesById,
        `síntese da associação "${basisLabel}"`,
      ),
    )
  }
  for (const pair of temporalPairs) {
    const basisLabel = synthesisTemporalPairBasisLabel(pair)
    invariant(!expected.has(basisLabel), `basisLabel repetido na síntese observada: "${basisLabel}".`)
    expected.set(
      basisLabel,
      renderObservedSynthesis(
        [pair.seriesA, pair.seriesB],
        pair.window,
        seriesById,
        `síntese do par "${basisLabel}"`,
      ),
    )
  }
  return expected
}

function expectedScenarioInvariantSynthesis(scenarios) {
  if (scenarios.status !== 'published') return new Map()
  const scenarioItems = [...scenarios.block.items].sort((left, right) => left.order - right.order)
  const anchorsByScenario = scenarioItems.map((scenario) =>
    new Map(scenario.anchors.map((anchor) => [anchor.seriesId, anchor])))
  const expected = new Map()
  for (const [seriesId, first] of anchorsByScenario[0]) {
    const anchors = anchorsByScenario.map((anchorsById) => anchorsById.get(seriesId))
    if (anchors.some((anchor) => anchor === undefined)) continue
    const sameProof = anchors.every((anchor) =>
      anchor.label === first.label
      && anchor.window.start === first.window.start
      && anchor.window.end === first.window.end
      && Object.is(anchor.startValue, first.startValue)
      && Object.is(anchor.endValue, first.endValue)
      && anchor.directionLabel === first.directionLabel)
    if (!sameProof) continue
    expected.set(
      first.label,
      `Conclui-se que ${first.label}, de ${synthesisNumberLabel(first.startValue)} para `
      + `${synthesisNumberLabel(first.endValue)} entre ${first.window.start} e ${first.window.end}, `
      + 'ancora os quatro cenários publicados da região.',
    )
  }
  return expected
}

export function commonScenarioAgendaThemes(scenarios) {
  if (scenarios.status !== 'published') return []
  const themesByScenario = scenarios.block.items.map((scenario) =>
    new Set(scenario.agendaThemes.map((theme) => theme.theme)))
  return AGENDA_THEMES.filter((theme) =>
    themesByScenario.every((scenarioThemes) => scenarioThemes.has(theme)))
}

export function renderAgendaSynthesis(themes) {
  const labels = themes.map((theme) => AGENDA_THEME_LABELS[theme])
  invariant(labels.length > 0 && labels.every((label) => label !== undefined),
    'a conclusão de agenda precisa de ao menos um tema do enum público.')
  return 'Conclui-se que as evidências desta região mobilizam, em qualquer dos quatro cenários, '
    + `as frentes da agenda do PNE: ${labels.join(', ')}.`
}

export function validateSynthesis(candidate, label, {
  associations,
  temporalPairs,
  scenarios,
  seriesById,
}) {
  validateExactFields(candidate, SYNTHESIS_FIELDS, label)
  invariant(candidate.label === SYNTHESIS_FRAMING.label,
    `${label}.label não é o rótulo declarado para a síntese.`)
  invariant(candidate.description === SYNTHESIS_FRAMING.description,
    `${label}.description não é a descrição declarada para a síntese.`)
  invariant(candidate.methodNote === SYNTHESIS_FRAMING.methodNote,
    `${label}.methodNote não é a nota de método declarada para a síntese.`)
  invariant(Array.isArray(candidate.items) && candidate.items.length > 0,
    `${label}.items deve trazer ao menos uma conclusão.`)
  invariant(Array.isArray(candidate.absentKinds), `${label}.absentKinds deve ser uma lista.`)

  const expectedObserved = expectedObservedSynthesis(associations, temporalPairs, seriesById)
  const expectedInvariant = expectedScenarioInvariantSynthesis(scenarios)
  const commonThemes = commonScenarioAgendaThemes(scenarios)
  const expectedAgenda = commonThemes.length > 0 ? renderAgendaSynthesis(commonThemes) : null
  const observedBases = new Set()
  const invariantBases = new Set()
  let agendaCount = 0

  candidate.items.forEach((item, index) => {
    const itemLabel = `${label}.items[${index}]`
    validateClosedFields(
      item,
      SYNTHESIS_ITEM_REQUIRED_FIELDS,
      SYNTHESIS_ITEM_OPTIONAL_FIELDS,
      itemLabel,
    )
    validateText(item.kindLabel, `${itemLabel}.kindLabel`)
    validateText(item.statement, `${itemLabel}.statement`)
    const kind = SYNTHESIS_KIND_BY_LABEL.get(item.kindLabel)
    invariant(kind !== undefined, `${itemLabel}.kindLabel fora do contrato: "${item.kindLabel}".`)
    const opener = SYNTHESIS_REQUIRED_OPENERS[kind]
    invariant(item.statement.startsWith(opener),
      `${itemLabel}.statement não começa com o abridor obrigatório "${opener}".`)

    if (kind === 'observed') {
      validateText(item.basisLabel, `${itemLabel}.basisLabel`)
      const expected = expectedObserved.get(item.basisLabel)
      invariant(expected !== undefined,
        `${itemLabel}.basisLabel não resolve em associação ou par do documento.`)
      invariant(item.statement === expected,
        `${itemLabel}.statement não coincide com os valores observados da base "${item.basisLabel}".`)
      invariant(!observedBases.has(item.basisLabel),
        `${itemLabel}.basisLabel repete uma conclusão observada.`)
      observedBases.add(item.basisLabel)
      return
    }

    if (kind === 'state_position') {
      validateText(item.basisLabel, `${itemLabel}.basisLabel`)
      const associationBases = new Set(associations.map(synthesisAssociationBasisLabel))
      invariant(associationBases.has(item.basisLabel),
        `${itemLabel}.basisLabel não resolve em associação do documento.`)
      invariant(
        /^Conclui-se que a mediana dos municípios da região em .+ está em -?\d[\d ]*(?:,\d+)?, ante a mediana estadual de -?\d[\d ]*(?:,\d+)?\.$/u.test(item.statement),
        `${itemLabel}.statement não segue a gramática fechada da comparação estadual.`,
      )
      return
    }

    if (kind === 'scenario_invariant') {
      validateText(item.basisLabel, `${itemLabel}.basisLabel`)
      const expected = expectedInvariant.get(item.basisLabel)
      invariant(expected !== undefined,
        `${itemLabel}.basisLabel não é uma série que ancora os quatro cenários.`)
      invariant(item.statement === expected,
        `${itemLabel}.statement não coincide com as quatro âncoras do documento.`)
      invariant(!invariantBases.has(item.basisLabel), `${itemLabel}.basisLabel repetido.`)
      invariantBases.add(item.basisLabel)
      return
    }

    invariant(!Object.prototype.hasOwnProperty.call(item, 'basisLabel'),
      `${itemLabel}.basisLabel não existe na conclusão de agenda.`)
    invariant(expectedAgenda !== null,
      `${itemLabel} traz conclusão de agenda sem tema comum aos quatro cenários.`)
    invariant(item.statement === expectedAgenda,
      `${itemLabel}.statement cita tema fora da interseção dos quatro cenários.`)
    agendaCount += 1
  })

  invariant(observedBases.size === expectedObserved.size,
    `${label} publica ${observedBases.size} conclusões observadas para ${expectedObserved.size} bases.`)
  invariant(invariantBases.size === expectedInvariant.size,
    `${label} publica ${invariantBases.size} conclusões invariantes para ${expectedInvariant.size} séries.`)
  invariant(agendaCount === (expectedAgenda === null ? 0 : 1),
    `${label} publica ${agendaCount} conclusões de agenda quando o contrato espera `
    + `${expectedAgenda === null ? 0 : 1}.`)

  const absenceLabels = new Set()
  candidate.absentKinds.forEach((absence, index) => {
    const absenceLabel = `${label}.absentKinds[${index}]`
    validateExactFields(absence, SYNTHESIS_ABSENCE_FIELDS, absenceLabel)
    validateText(absence.kindLabel, `${absenceLabel}.kindLabel`)
    validateText(absence.statement, `${absenceLabel}.statement`)
    invariant(
      absence.kindLabel === SYNTHESIS_KIND_LABELS.scenario_invariant
        || absence.kindLabel === SYNTHESIS_KIND_LABELS.agenda,
      `${absenceLabel}.kindLabel não admite ausência declarada.`,
    )
    invariant(!absenceLabels.has(absence.kindLabel), `${absenceLabel}.kindLabel repetido.`)
    absenceLabels.add(absence.kindLabel)
  })
  invariant(
    absenceLabels.has(SYNTHESIS_KIND_LABELS.scenario_invariant) === (expectedInvariant.size === 0),
    `${label} não declara corretamente a ausência da conclusão invariante dos cenários.`,
  )
  invariant(
    absenceLabels.has(SYNTHESIS_KIND_LABELS.agenda) === (expectedAgenda === null),
    `${label} não declara corretamente a ausência da conclusão de agenda.`,
  )
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
    validateExactFields(candidate.temporalPairs, TEMPORAL_PAIRS_BLOCK_FIELDS, 'pacote.temporalPairs')
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
    invariant(
      Array.isArray(candidate.temporalPairs.laggedItems)
        && candidate.temporalPairs.laggedItems.length === 1,
      'pacote.temporalPairs.laggedItems deve trazer exatamente uma leitura defasada.',
    )
    candidate.temporalPairs.laggedItems.forEach((item, index) => {
      validateLaggedItem(
        item,
        `pacote.temporalPairs.laggedItems[${index}]`,
        seriesById,
        referenceYear,
      )
    })

    /* Relações adicionais aprovadas pela triagem estatística fechada. */
    validateScreenedRelations(
      candidate.screenedRelations,
      'pacote.screenedRelations',
      seriesById,
      referenceYear,
    )

    /* Bloco 4 — cenários da região, publicados ou declaradamente ausentes. */
    validateScenarios(candidate.scenarios, 'pacote.scenarios', seriesById, referenceYear)

    /* Camada de conclusões — aditiva e obrigatória nas dez regiões. */
    validateSynthesis(candidate.synthesis, 'pacote.synthesis', {
      associations: candidate.associations.items,
      temporalPairs: candidate.temporalPairs.items,
      scenarios: candidate.scenarios,
      seriesById,
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
    invariant(
      typeof candidate.provenance.synthesisPackageSha256 === 'string'
        && SHA256_PATTERN.test(candidate.provenance.synthesisPackageSha256),
      'pacote.provenance.synthesisPackageSha256 deve ser sha256.',
    )
    /*
     * Os dois resumos do cenário existem juntos ou não existem: um documento
     * que nomeia o pacote de cenários e não nomeia a origem dele prova metade
     * da cadeia, e metade de uma cadeia de procedência não é procedência.
     */
    const scenarioHashes = [
      candidate.provenance.scenarioPackageSha256,
      candidate.provenance.scenarioSourceSha256,
      candidate.provenance.municipalPackageSha256,
    ]
    const scenarioHashNames = ['scenarioPackageSha256', 'scenarioSourceSha256', 'municipalPackageSha256']
    const publishesScenarios = candidate.scenarios.status === 'published'
    scenarioHashes.forEach((value, index) => {
      const name = scenarioHashNames[index]
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
