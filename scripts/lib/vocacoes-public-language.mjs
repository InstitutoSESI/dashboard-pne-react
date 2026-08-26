/*
 * Guarda de linguagem pública do Vocações da Região, no lado da plataforma.
 *
 * Esta é a **segunda** camada. A camada de pesquisa já tem a sua, exercitada
 * pelas Rodadas 1–4 e medida contra um corpus adversarial bilateral. Repetir a
 * varredura aqui não é desconfiança do artefato: é o invariante D7 — a
 * plataforma valida o que publica, fail-closed, sem depender de a origem ter
 * validado direito.
 *
 * De onde vêm os padrões. Copiá-los da pesquisa produziria duas listas que
 * divergem com o tempo, e a que ninguém olha é a que envelhece. Importá-los em
 * runtime é proibido (a plataforma nunca lê a camada de pesquisa em runtime).
 * A solução é a terceira: o gerador lê o contrato da pesquisa **em tempo de
 * publicação** e usa as listas de lá — e este módulo declara um **piso
 * próprio**, um conjunto de padrões que o contrato da pesquisa precisa conter.
 * Contrato que perdeu um padrão do piso não publica. Assim a guarda da
 * plataforma nunca é mais fraca que a da pesquisa, e nunca fica em silêncio
 * quando a pesquisa afrouxa.
 */

/*
 * Piso da plataforma: os padrões que o contrato da pesquisa é obrigado a
 * trazer. A lista é curta de propósito — ela não tenta cobrir a linguagem
 * causal inteira, e sim ancorar as classes que o plano nomeia como risco
 * (§8.1, §8.7, §8.8, §8.9). Cada entrada aqui é uma promessa que a plataforma
 * faz por conta própria.
 */
export const CAUSAL_FLOOR = Object.freeze([
  '\\bcausou\\b',
  '\\bprovoc',
  '\\bdevido a',
  '\\bpor causa d',
  '\\bem raz[ãa]o d',
  '\\brespons[áa]vel\\s+(?:por|pel)',
  '\\bgerou\\b',
  '\\blevou a\\b',
  '\\bimpactou\\b',
])

export const TOKEN_FLOOR = Object.freeze(['fiergs', 'senai', 'sesi', 'regiao_fiergs', 'id_municipio'])

/*
 * Tokens internos que são desta camada, não da pesquisa: nomes de arquivo e de
 * diretório do acervo de origem, que só existem do lado de cá porque é o
 * gerador que os lê.
 */
export const PLATFORM_FORBIDDEN_TOKENS = Object.freeze([
  'csv-dashboard',
  'manifesto_datasets',
  'dicionario_colunas',
  'manifesto_origem',
  'pacotes/regioes',
  'foresight',
  'vocacoes-regiao-pesquisa',
])

/*
 * Chave interna: a taxonomia `snake_case` da camada de pesquisa. Três ou mais
 * segmentos unidos por sublinhado não é um jeito de escrever em português — é
 * um identificador que vazou.
 */
const INTERNAL_KEY_PATTERN = /\b[a-z0-9]+(?:_[a-z0-9]+){2,}\b/u

/* Identificadores de processo do foresight municipal e da matriz. */
const INTERNAL_ID_PATTERNS = Object.freeze([
  /\b(?:RM|GC|DIM)-?\d{1,2}\b/u,
  /\b[CDEFHNS]-?\d{2}\b/u,
  /\bC[1-4]\b/u,
])

/*
 * Negação com escopo de oração — o item `B5` que a Rodada 4 endereçou a esta
 * rodada.
 *
 * A guarda da camada de pesquisa procura a expressão causal sem olhar para a
 * negação, e por isso recusa a ressalva honesta que a própria regra exige:
 * "o saldo não é um fluxo migratório medido", "esta página não afirma causa".
 * §5.5 é explícito — falso positivo sobre limitação honesta é defeito tão grave
 * quanto falso negativo.
 *
 * A janela é a **oração**, do delimitador anterior até a expressão, e não o
 * texto inteiro: negar numa frase não dá licença para afirmar na seguinte.
 *
 * O que esta versão acrescenta à da Rodada 4: a negação **da negação** não
 * isenta. "Não se pode negar que a seca causou a queda" tem "não" na oração e
 * afirma causalidade assim mesmo — a versão da R4 a deixaria passar. Um verbo
 * que inverte a negação dentro da mesma oração cancela a isenção.
 */
const NEGATION_MARKERS = /\b(?:nao|nunca|nem|jamais|longe de ser|em vez de|sem que|impede|impedem)\b/u
const NEGATION_REVERSERS = /\b(?:negar|negam|nega|duvidar|duvida|descartar|descarta|excluir|exclui|contestar|contesta)\b/u
const CLAUSE_DELIMITERS = /[.;:!?,]/u

/** Limites da oração que contém a posição, e da oração seguinte. */
function clauseBounds(normalized, position) {
  let start = 0
  for (let index = position - 1; index >= 0; index -= 1) {
    if (CLAUSE_DELIMITERS.test(normalized[index])) { start = index + 1; break }
  }
  let end = normalized.length
  let next = normalized.length
  let seen = 0
  for (let index = position; index < normalized.length; index += 1) {
    if (!CLAUSE_DELIMITERS.test(normalized[index])) continue
    seen += 1
    if (seen === 1) { end = index; continue }
    next = index
    break
  }
  return { start, end, next }
}

/*
 * A expressão está sob negação?
 *
 * A janela é a **oração inteira** que a contém — antes e depois —, e não só o
 * que vem antes dela. "pois as séries não permitem inferência causal" nega
 * depois do conectivo, e uma janela só de prefixo recusaria a ressalva honesta
 * que a própria regra exige. Negar numa oração continua não dando licença para
 * afirmar na seguinte.
 *
 * Para o conectivo, a janela vai uma oração além: "portanto, 2030 não integra o
 * período observado" nega no consequente, que é onde a honestidade dele mora.
 * Um conectivo só é causal quando o que ele introduz é afirmado.
 *
 * A negação **da negação** não isenta, nos dois casos: "não se pode negar que a
 * seca causou a queda" tem "não" na oração e afirma causalidade assim mesmo.
 */
function isNegatedInClause(normalized, position, { extended = false } = {}) {
  const { start, end, next } = clauseBounds(normalized, position)
  const clause = normalized.slice(start, extended ? next : end)
  if (!NEGATION_MARKERS.test(clause)) return false
  return !NEGATION_REVERSERS.test(clause)
}

/**
 * Primeira ocorrência do padrão que esteja de fato **afirmada** — isto é, que
 * não esteja sob negação na própria oração. Devolve o trecho encontrado, já
 * normalizado, ou `null`. O texto original inteiro viaja no erro, então o
 * trecho serve para apontar, não para citar.
 */
function findAsserted(text, pattern, options = {}) {
  const normalized = normalize(text)
  const scanner = new RegExp(pattern.source, `${pattern.flags.replace('g', '')}g`)
  let match = scanner.exec(normalized)
  while (match !== null) {
    if (!isNegatedInClause(normalized, match.index, options)) return match[0]
    /* Padrão de largura zero não pode travar a varredura. */
    if (match[0] === '') scanner.lastIndex += 1
    match = scanner.exec(normalized)
  }
  return null
}

/*
 * Conjunções que viram a alegação proibida do avesso. "Não se pode concluir que
 * a relação seja descritiva, **mas** a perda de renda causou o abandono" começa
 * como proibição e termina como afirmação — e a alegação proibida é justamente
 * o campo isento da varredura causal, porque precisa nomear a leitura causal.
 * A isenção vale para uma proibição, não para uma proibição com apêndice.
 */
const CLAIM_REVERSERS = /\b(?:mas|porem|contudo|todavia|entretanto|no entanto|pois|porque|ja que|embora|apesar de)\b/u

/*
 * Futuro sem ano escrito por extenso em dígitos. Os dois casos que a Rodada 4
 * encontrou: o ano partido por espaço ("20 30") e o futuro relativo sem ano
 * nenhum ("daqui a quatro anos"). Nenhum dos dois é pego por uma varredura de
 * `\d{4}`.
 */
/*
 * Prosa de cenário que desmente o estatuto dele.
 *
 * A revisão adversarial do contrato `2.1.0` fez a pergunta certa: o estatuto é
 * estrutural — enum fechado, frase renderizada do enum, exatamente um normativo
 * —, e ainda assim `centralMechanism` podia dizer «este cenário é a previsão
 * oficial e o plano aprovado pela região» e passar por tudo. A estrutura
 * garante que a ressalva **está na página**; ela não garante qual das duas
 * frases o leitor toma como a verdadeira.
 *
 * Esta guarda ataca a metade que é atacável: as afirmações que contradizem o
 * estatuto de forma explícita — previsão, plano aprovado, pactuação, decisão
 * tomada, certeza sobre o que vai ocorrer. Ela roda com o mesmo detector de
 * negação das outras: «não é previsão» e «não foi pactuado» são exatamente o
 * que o bloco precisa poder dizer, e dizem.
 *
 * O que ela **não** fecha está declarado: uma narrativa pode induzir leitura de
 * previsão sem usar nenhuma destas palavras, e nenhuma lista fecha isso. O que
 * resta é risco editorial, e é assim que ele é reportado — não como garantia.
 */
const STATUTE_CONTRADICTION_PATTERNS = Object.freeze([
  /\bprevisao oficial\b/u,
  /\bplano aprovado\b/u,
  /\bfoi aprovad[oa]\b/u,
  /\besta aprovad[oa]\b/u,
  /\bfoi pactuad[oa]\b/u,
  /\besta pactuad[oa]\b/u,
  /\bcompromisso assumido\b/u,
  /\bdecisao ja tomada\b/u,
  /\bcenario mais provavel\b/u,
  /\bmais provavel\b/u,
  /\bvai acontecer\b/u,
  /\bira acontecer\b/u,
  /\bacontecera\b/u,
  /\bo que vai ocorrer\b/u,
  /\bcom certeza\b/u,
])

/*
 * Futuro sem ano escrito por extenso em dígitos. Os dois casos que a Rodada 4
 * encontrou: o ano partido por espaço ("20 30") e o futuro relativo sem ano
 * nenhum ("daqui a quatro anos"). Nenhum dos dois é pego por uma varredura de
 * `\d{4}`.
 */
const SPLIT_YEAR_PATTERN = /\b(?:19|20)\s+\d\s*\d\b/u
const RELATIVE_FUTURE_PATTERN = /\b(?:daqui a|nos proximos|nas proximas|dentro de|ate o fim d|em \d+ anos)\b/u

/*
 * O subconjunto da lista cadastral que fala de população e de taxa. Escrito
 * aqui, e não derivado por subtração da lista da pesquisa: derivar por
 * subtração faria a guarda mudar sozinha quando a lista de lá crescesse, e o
 * ponto deste subconjunto é ser uma decisão desta camada.
 */
const CADASTRAL_RATE_TERMS = Object.freeze([
  'populacao',
  'habitantes',
  'moradores',
  'residentes',
  'todas as pessoas',
  'todos os moradores',
  'taxa',
  'percentual',
  'proporcao',
  'por cento',
  'per capita',
  'por mil',
  'por 100',
  '%',
])

export class PublicLanguageError extends Error {
  constructor(message, { code, field, excerpt } = {}) {
    super(message)
    this.name = 'PublicLanguageError'
    this.code = code
    this.field = field
    this.excerpt = excerpt
  }
}

function fail(code, field, message, excerpt) {
  throw new PublicLanguageError(
    `Vocações da Região — ${message}${field ? ` (campo ${field})` : ''}.`,
    { code, field, excerpt },
  )
}

function normalize(text) {
  return text
    .normalize('NFD')
    .replace(/\p{Diacritic}/gu, '')
    .toLocaleLowerCase('pt-BR')
}

/*
 * O contrato da pesquisa precisa conter o piso. A comparação é por texto do
 * padrão, não por comportamento: um padrão do piso que sumiu do contrato é
 * exatamente o caso que este teste existe para pegar, e reescrever o padrão
 * "de outro jeito equivalente" também precisa passar por aqui — de propósito.
 */
export function assertResearchContractCoversFloor(researchContract) {
  const causal = new Set(researchContract.causalLanguagePatterns ?? [])
  for (const pattern of CAUSAL_FLOOR) {
    /*
     * Comparação por texto exato do padrão, e não por equivalência de
     * comportamento. É deliberadamente rígido: reescrever um padrão "de outro
     * jeito equivalente" também precisa passar por aqui, porque equivalência
     * de expressão regular não é conferível por inspeção — e o caso que este
     * piso existe para pegar (o padrão sumiu) é indistinguível, por
     * comportamento, do caso em que ele só mudou de forma.
     */
    if (!causal.has(pattern)) {
      fail(
        'RESEARCH_CONTRACT_BELOW_FLOOR',
        null,
        `o contrato da camada de pesquisa não traz o padrão causal exigido pelo piso da plataforma: ${pattern}`,
      )
    }
  }
  const tokens = new Set((researchContract.forbiddenPublicTokens ?? []).map(normalize))
  for (const token of TOKEN_FLOOR) {
    if (!tokens.has(normalize(token))) {
      fail(
        'RESEARCH_CONTRACT_BELOW_FLOOR',
        null,
        `o contrato da camada de pesquisa não traz o token proibido exigido pelo piso da plataforma: ${token}`,
      )
    }
  }
  return true
}

function compile(patterns) {
  return patterns.map((pattern) => new RegExp(pattern, 'iu'))
}

/**
 * Constrói a guarda a partir do contrato da pesquisa lido em tempo de
 * publicação. Nunca em runtime: quem chama isto é o gerador.
 */
export function createPublicLanguageGuard(researchContract) {
  assertResearchContractCoversFloor(researchContract)

  const causal = compile(researchContract.causalLanguagePatterns ?? [])
  const connectives = compile(researchContract.causalConnectivePatterns ?? [])
  const forbiddenTokens = [
    ...(researchContract.forbiddenPublicTokens ?? []),
    ...PLATFORM_FORBIDDEN_TOKENS,
  ].map(normalize)
  const cadastralForbidden = (researchContract.cadastralSeriesForbiddenTerms ?? []).map(normalize)
  const assertionVerbs = (researchContract.futureYearAssertionVerbs ?? []).map(normalize)
  const negationMarkers = (researchContract.futureYearNegationMarkers ?? []).map(normalize)
  const numberWords = (researchContract.futureYearNumberWords ?? []).map(normalize)
  const spelledYearPrefixes = Object.keys(researchContract.spelledYearPrefixes ?? {}).map(normalize)
  const referenceYear = researchContract.referenceYear

  function checkTokens(text, field) {
    const normalized = normalize(text)
    for (const token of forbiddenTokens) {
      if (normalized.includes(token)) {
        fail('INTERNAL_TOKEN_IN_PUBLIC_TEXT', field, `o texto público expõe o token interno "${token}"`, text)
      }
    }
    const key = INTERNAL_KEY_PATTERN.exec(text)
    if (key !== null) {
      fail('INTERNAL_KEY_IN_PUBLIC_TEXT', field, `o texto público expõe a chave interna "${key[0]}"`, text)
    }
    for (const pattern of INTERNAL_ID_PATTERNS) {
      const found = pattern.exec(text)
      if (found !== null) {
        fail('INTERNAL_ID_IN_PUBLIC_TEXT', field, `o texto público expõe o identificador de processo "${found[0]}"`, text)
      }
    }
  }

  /*
   * Ano futuro. Só acusa quando o ano futuro aparece junto de um número ou de
   * um verbo de afirmação: dizer "a série não alcança 2030" é honesto, e uma
   * guarda que barra isso impede o pacote de declarar o próprio limite. O
   * marcador de negação é específico ("não há observação"), nunca a negação
   * genérica — a lição da Rodada 2: "não há dúvida de que em 2030 serão 145 000"
   * usava a negação como máscara da afirmação.
   */
  function checkFutureYear(text, field) {
    const normalized = normalize(text)

    /*
     * Ano futuro é recusado por padrão, e não só quando vem acompanhado de
     * número. A permissão é explícita: um dos marcadores de ausência
     * declarados no contrato, na mesma oração — "a série não alcança 2030",
     * "2030 não integra o período observado". A regra invertida (recusar só se
     * houver número por perto) deixava passar "Em 2030: uma em cada três
     * matrículas", que não tem dígito nenhum e afirma o mesmo.
     *
     * O marcador é específico, nunca a negação genérica: "não há dúvida de que
     * em 2030 serão 145 mil" usa a negação como máscara da afirmação — a lição
     * da Rodada 2, que esta camada herda em vez de reaprender.
     */
    const sentencas = normalized.split(/(?<=[.;])\s+/u)
    for (const sentenca of sentencas) {
      const permitido = negationMarkers.some((marker) => sentenca.includes(marker))
      if (permitido) continue

      const anos = [...sentenca.matchAll(/\b(?:19|20)\d{2}\b/gu)]
        .map((match) => Number.parseInt(match[0], 10))
        .filter((year) => year > referenceYear)
      if (anos.length > 0) {
        fail('FUTURE_YEAR_IN_PUBLIC_TEXT', field,
          `o texto público cita o ano futuro ${anos[0]} sem declarar que não há observação para ele`, text)
      }

      /* Ano partido por espaço: "no ano 20 30". */
      if (SPLIT_YEAR_PATTERN.test(sentenca)) {
        const partido = SPLIT_YEAR_PATTERN.exec(sentenca)[0]
        const juntado = Number.parseInt(partido.replace(/\s+/gu, ''), 10)
        if (juntado > referenceYear) {
          fail('FUTURE_YEAR_IN_PUBLIC_TEXT', field,
            `o texto público cita o ano futuro ${juntado}, escrito com espaço no meio`, text)
        }
      }

      /* Ano por extenso: o prefixo vem do contrato da pesquisa. */
      const temAnoEscrito = spelledYearPrefixes.some((prefix) => sentenca.includes(prefix))
      const temVerbo = assertionVerbs.some((verb) => sentenca.includes(verb))
      const temNumero = /\d/u.test(sentenca) || numberWords.some((word) => sentenca.includes(word))
      if (temAnoEscrito && temVerbo) {
        fail('FUTURE_YEAR_IN_PUBLIC_TEXT', field,
          'o texto público afirma um número para um ano escrito por extenso', text)
      }

      /* Futuro relativo, sem ano nenhum: "daqui a quatro anos, haverá 145 mil". */
      if (RELATIVE_FUTURE_PATTERN.test(sentenca) && temVerbo && temNumero) {
        fail('FUTURE_YEAR_IN_PUBLIC_TEXT', field,
          'o texto público afirma um número para um futuro relativo', text)
      }
    }
  }

  function checkCausal(text, field, { exemptCausal = false, exemptConnective = false } = {}) {
    if (!exemptCausal) {
      for (const pattern of causal) {
        const found = findAsserted(text, pattern)
        if (found !== null) {
          fail('CAUSAL_LANGUAGE_IN_PUBLIC_TEXT', field, `o texto público afirma causalidade: "${found}"`, text)
        }
      }
    }
    if (!exemptConnective) {
      for (const pattern of connectives) {
        const found = findAsserted(text, pattern, { extended: true })
        if (found !== null) {
          fail('CAUSAL_CONNECTIVE_IN_PUBLIC_TEXT', field, `o texto público usa o conectivo causal "${found}"`, text)
        }
      }
    }
  }

  /*
   * Contradição de universo. O `universeLabel` vem do enum e não pode ser
   * contrariado pelo rótulo: uma série do cadastro social rotulada como
   * "população" ou como "taxa" redefine o universo por baixo da declaração.
   */
  function checkCadastralUniverse(text, field) {
    const normalized = normalize(text)
    for (const term of cadastralForbidden) {
      if (normalized.includes(term)) {
        fail(
          'UNIVERSE_CONTRADICTED_BY_PUBLIC_TEXT',
          field,
          `a série de universo cadastral usa o termo "${term}", que contradiz o universo declarado`,
          text,
        )
      }
    }
  }

  /*
   * A mesma contradição, um nível acima: no texto de uma associação ou de um
   * par que cita série do cadastro social. O risco 8 do plano é exatamente
   * este — "as pessoas inscritas equivalem a 18% da população regional" —, e
   * ele não mora na série, mora na frase que fala dela.
   *
   * A lista aqui é **menor** que a da série, de propósito. A da série proíbe
   * também os objetos de outros universos ("matrícula", "vínculo", "nascidos
   * vivos"), porque rotular a série cadastral com o objeto alheio redefine o
   * universo. Numa associação isso se inverte: ela cita o cadastro **ao lado**
   * da matrícula, e essa é a leitura que o plano pede. Herdar a lista inteira
   * recusaria toda associação cadastral honesta — o falso positivo que o §5.5
   * trata como defeito igual ao falso negativo.
   */
  function checkCadastralComparison(text, field) {
    const normalized = normalize(text)
    for (const term of CADASTRAL_RATE_TERMS) {
      if (normalized.includes(term)) {
        fail(
          'UNIVERSE_CONTRADICTED_BY_PUBLIC_TEXT',
          field,
          `o texto cita série do cadastro social e usa "${term}", que a lê como população ou como taxa`,
          text,
        )
      }
    }
  }

  /*
   * A alegação proibida é isenta da varredura causal porque precisa nomear a
   * leitura causal. A isenção vale para uma proibição — não para uma proibição
   * seguida de um apêndice que a desfaz.
   */
  function checkProhibitedClaim(text, field) {
    checkTokens(text, field)
    checkFutureYear(text, field)
    const found = CLAIM_REVERSERS.exec(normalize(text))
    if (found !== null) {
      fail(
        'PROHIBITED_CLAIM_REVERSED',
        field,
        `a alegação proibida traz "${found[0]}", que a transforma em afirmação`,
        text,
      )
    }
  }

  /*
   * Frase pública que termina no meio.
   *
   * O vetor mais barato da Rodada 4 não escondia a causalidade em sinônimo:
   * partia a oração entre dois campos. "A retração do emprego levou" num, "à
   * evasão escolar." no outro — cada metade passa sozinha e o leitor lê as duas
   * juntas, uma embaixo da outra. A varredura do texto corrido pega a maioria
   * dos casos, mas ela depende de os dois campos ficarem adjacentes na
   * concatenação, e nem sempre ficam.
   *
   * Esta regra ataca a condição, não o sintoma: um campo de prosa que não
   * termina em pontuação final é uma oração incompleta, e oração incompleta não
   * é texto publicável — com ou sem causalidade dentro.
   */
  function checkSentenceComplete(text, field) {
    const trimmed = text.trimEnd()
    if (!/[.!?]$/u.test(trimmed)) {
      fail(
        'PUBLIC_SENTENCE_INCOMPLETE',
        field,
        'a frase pública não termina em pontuação final, e continua noutro campo',
        text,
      )
    }
  }

  /*
   * Texto de horizonte: a única isenção da regra de ano futuro nesta camada, e
   * ela é estreita de propósito.
   *
   * O que o plano proíbe é **número atribuído a ano futuro** — dizer quantas
   * matrículas haverá em 2031. Dizer que o horizonte dos cenários alcança 2031
   * não é isso: é declarar o recorte do exercício, e um bloco de cenários que
   * não pode nomear o próprio horizonte não pode existir.
   *
   * A isenção vale só nos campos de horizonte, e dentro deles vale só assim:
   *
   *   1. o ano citado precisa ser **um dos anos de horizonte que o bloco
   *      declara** — 2031 e 2041 aqui, não um ano qualquer; e
   *   2. a oração em que ele aparece **não pode trazer nenhuma outra
   *      quantidade**: nem outro grupo de dígitos, nem palavra de número da
   *      lista do contrato.
   *
   * Com as duas juntas, "o horizonte alcança 2031" passa e "em 2031 serão
   * 145 000 matrículas" e "em 2031 serão mil matrículas" continuam sendo
   * recusadas — que é exatamente a fronteira que a regra queria.
   */
  function checkHorizonText(text, field, { allowedYears = [] } = {}) {
    checkTokens(text, field)
    checkCausal(text, field)

    const permitidos = new Set(allowedYears)
    const normalized = normalize(text)
    const sentencas = normalized.split(/(?<=[.;])\s+/u)
    for (const sentenca of sentencas) {
      const anos = [...sentenca.matchAll(/\b(?:19|20)\d{2}\b/gu)]
        .map((match) => Number.parseInt(match[0], 10))
        .filter((year) => year > referenceYear)
      if (anos.length === 0) continue

      const forasteiro = anos.find((year) => !permitidos.has(year))
      if (forasteiro !== undefined) {
        fail(
          'FUTURE_YEAR_IN_PUBLIC_TEXT',
          field,
          `o campo de horizonte cita ${forasteiro}, que não é um dos anos de horizonte declarados`,
          text,
        )
      }

      const outrosDigitos = [...sentenca.matchAll(/\d[\d\s.,]*/gu)]
        .map((match) => match[0].replace(/[\s.,]+$/u, ''))
        .filter((grupo) => !anos.includes(Number.parseInt(grupo.replace(/[\s.,]/gu, ''), 10)))
      if (outrosDigitos.length > 0) {
        fail(
          'FUTURE_YEAR_IN_PUBLIC_TEXT',
          field,
          `o campo de horizonte atribui a quantidade "${outrosDigitos[0].trim()}" a um ano futuro`,
          text,
        )
      }

      for (const word of numberWords) {
        if (sentenca.includes(word)) {
          fail(
            'FUTURE_YEAR_IN_PUBLIC_TEXT',
            field,
            `o campo de horizonte atribui a quantidade "${word}" a um ano futuro`,
            text,
          )
        }
      }
    }
    return text
  }

  /** Prosa de cenário que afirma previsão, aprovação ou pactuação. */
  function checkStatuteContradiction(text, field) {
    for (const pattern of STATUTE_CONTRADICTION_PATTERNS) {
      const found = findAsserted(text, pattern, { extended: true })
      if (found !== null) {
        fail(
          'SCENARIO_STATUTE_CONTRADICTED',
          field,
          `o texto do cenário afirma "${found}", que contradiz o estatuto declarado dele`,
          text,
        )
      }
    }
    return text
  }

  /** Uma passagem de texto público, com as isenções declaradas por campo. */
  function checkText(text, field, options = {}) {
    checkTokens(text, field)
    checkFutureYear(text, field)
    checkCausal(text, field, options)
    if (options.cadastral === true) checkCadastralUniverse(text, field)
    return text
  }

  return {
    checkText,
    checkTokens,
    checkFutureYear,
    checkHorizonText,
    checkStatuteContradiction,
    checkCausal,
    checkCadastralUniverse,
    checkCadastralComparison,
    checkProhibitedClaim,
    checkSentenceComplete,
    referenceYear,
  }
}

/*
 * A varredura do documento inteiro. Ela conhece o contrato `2.0.0` campo a
 * campo — de propósito: uma varredura genérica "todo string do JSON" não sabe
 * quais campos são isentos, e trataria a alegação proibida (que precisa nomear
 * a leitura causal) como violação.
 */
export function scanPublicDocument(document, guard) {
  const cadastralUniverse = guard.cadastralUniverseLabel

  guard.checkText(document.region.name, 'region.name')
  for (const key of ['eyebrow', 'title', 'description', 'neutralityNote']) {
    guard.checkText(document.page[key], `page.${key}`)
  }
  guard.checkText(document.howToRead.label, 'howToRead.label')
  guard.checkText(document.howToRead.description, 'howToRead.description')
  document.howToRead.items.forEach((item, index) => {
    guard.checkText(item, `howToRead.items[${index}]`)
  })

  guard.checkText(document.territoryPortrait.label, 'territoryPortrait.label')
  guard.checkText(document.territoryPortrait.description, 'territoryPortrait.description')
  document.territoryPortrait.series.forEach((serie, index) => {
    const field = `territoryPortrait.series[${index}]`
    const cadastral = serie.universeLabel === cadastralUniverse
    guard.checkText(serie.label, `${field}.label`, { cadastral })
    guard.checkText(serie.unitLabel, `${field}.unitLabel`, { cadastral })
    guard.checkText(serie.sourceLabel, `${field}.sourceLabel`, { cadastral })
    guard.checkText(serie.periodLabel, `${field}.periodLabel`)
    if (serie.universeLabel !== null) guard.checkText(serie.universeLabel, `${field}.universeLabel`)
    if (serie.ratioOf !== null) {
      guard.checkText(serie.ratioOf.numeratorLabel, `${field}.ratioOf.numeratorLabel`)
      guard.checkText(serie.ratioOf.denominatorLabel, `${field}.ratioOf.denominatorLabel`)
    }
    /*
     * A limitação é onde o pacote declara o próprio limite, e "porque" é a
     * língua natural disso. O conectivo é isento aqui — e só aqui. A camada
     * forte (afirmação causal entre fenômenos) continua valendo.
     */
    serie.limitations.forEach((limitation, position) => {
      guard.checkText(limitation, `${field}.limitations[${position}]`, { exemptConnective: true })
    })
    /* O identificador público também passa: ele nasce do rótulo, e é onde uma
     * chave interna entraria sem ser lida por ninguém. */
    guard.checkTokens(serie.seriesId, `${field}.seriesId`)
  })

  /* Quais séries são do cadastro social — a resposta é do documento, não de
   * uma lista de nomes mantida à parte. */
  const cadastralSeriesIds = new Set(
    document.territoryPortrait.series
      .filter((serie) => serie.universeLabel === cadastralUniverse)
      .map((serie) => serie.seriesId),
  )
  const citesCadastral = (...references) =>
    references.some((reference) => cadastralSeriesIds.has(reference.seriesId))

  guard.checkText(document.associations.label, 'associations.label')
  guard.checkText(document.associations.description, 'associations.description')
  document.associations.items.forEach((association, index) => {
    const field = `associations.items[${index}]`
    const cadastral = citesCadastral(association.educationOutcome, ...association.territorialFactors)
    guard.checkTokens(association.associationId, `${field}.associationId`)
    guard.checkText(association.label, `${field}.label`)
    guard.checkText(association.periodLabel, `${field}.periodLabel`)
    guard.checkText(association.observedStatement, `${field}.observedStatement`)
    guard.checkSentenceComplete(association.observedStatement, `${field}.observedStatement`)
    guard.checkText(association.allowedInterpretation, `${field}.allowedInterpretation`)
    guard.checkSentenceComplete(association.allowedInterpretation, `${field}.allowedInterpretation`)
    /*
     * A alegação proibida precisa nomear a leitura causal — e só ela. Fica
     * fora da varredura causal e continua sob token interno e ano futuro.
     */
    guard.checkProhibitedClaim(association.prohibitedClaim, `${field}.prohibitedClaim`)
    association.hypotheses.forEach((hypothesis, position) => {
      guard.checkText(hypothesis, `${field}.hypotheses[${position}]`)
      guard.checkSentenceComplete(hypothesis, `${field}.hypotheses[${position}]`)
    })
    guard.checkText(association.educationOutcome.label, `${field}.educationOutcome.label`)
    association.territorialFactors.forEach((factor, position) => {
      guard.checkText(factor.label, `${field}.territorialFactors[${position}].label`)
    })
    /*
     * A frase partida entre dois campos. Um dos vetores da Rodada 4 escrevia
     * "A retração do emprego levou" num campo e "à evasão escolar." no
     * seguinte: cada metade passa sozinha, e o leitor lê as duas juntas, uma
     * embaixo da outra. A varredura por campo não vê isso — a concatenação vê.
     */
    guard.checkCausal(
      [
        association.observedStatement,
        association.allowedInterpretation,
        ...association.hypotheses,
      ].join(' '),
      `${field} (texto corrido)`,
    )

    if (cadastral) {
      guard.checkCadastralComparison(association.observedStatement, `${field}.observedStatement`)
      guard.checkCadastralComparison(association.allowedInterpretation, `${field}.allowedInterpretation`)
      guard.checkCadastralComparison(association.prohibitedClaim, `${field}.prohibitedClaim`)
      association.hypotheses.forEach((hypothesis, position) => {
        guard.checkCadastralComparison(hypothesis, `${field}.hypotheses[${position}]`)
      })
      association.territorialFactors.forEach((factor, position) => {
        guard.checkCadastralComparison(factor.label, `${field}.territorialFactors[${position}].label`)
      })
    }
  })

  guard.checkText(document.temporalPairs.label, 'temporalPairs.label')
  guard.checkText(document.temporalPairs.description, 'temporalPairs.description')
  document.temporalPairs.items.forEach((pair, index) => {
    const field = `temporalPairs.items[${index}]`
    guard.checkTokens(pair.pairId, `${field}.pairId`)
    guard.checkText(pair.label, `${field}.label`)
    guard.checkText(pair.periodLabel, `${field}.periodLabel`)
    guard.checkText(pair.observedStatement, `${field}.observedStatement`)
    guard.checkSentenceComplete(pair.observedStatement, `${field}.observedStatement`)
    guard.checkProhibitedClaim(pair.prohibitedClaim, `${field}.prohibitedClaim`)
    guard.checkText(pair.seriesA.label, `${field}.seriesA.label`)
    guard.checkText(pair.seriesB.label, `${field}.seriesB.label`)
    guard.checkCausal(
      [pair.label, pair.observedStatement].join(' '),
      `${field} (texto corrido)`,
    )

    if (citesCadastral(pair.seriesA, pair.seriesB)) {
      guard.checkCadastralComparison(pair.label, `${field}.label`)
      guard.checkCadastralComparison(pair.observedStatement, `${field}.observedStatement`)
      guard.checkCadastralComparison(pair.prohibitedClaim, `${field}.prohibitedClaim`)
    }
  })

  scanScenarios(document, guard, { citesCadastral })

  guard.checkText(document.sources.label, 'sources.label')
  guard.checkText(document.sources.description, 'sources.description')
  document.sources.items.forEach((item, index) => {
    guard.checkText(item.label, `sources.items[${index}].label`)
    guard.checkText(item.periodLabel, `sources.items[${index}].periodLabel`)
  })

  guard.checkText(document.limitations.label, 'limitations.label')
  guard.checkText(document.limitations.description, 'limitations.description')
  document.limitations.items.forEach((item, index) => {
    guard.checkText(item, `limitations.items[${index}]`, { exemptConnective: true })
  })

  return document
}

/*
 * Bloco 4 — cenários da região.
 *
 * Todo campo público do bloco corre no perfil mais severo da guarda: causal,
 * conectivo causal e ano futuro, **sem isenção** — o mesmo perfil que a
 * hipótese de uma associação. É o que o contrato da camada de pesquisa declara
 * campo a campo em `scenarioPublicTextFields`, e a razão é simples: o Bloco 4 é
 * o único do documento que fala do futuro, e é onde uma frase causal custa
 * mais.
 *
 * As duas exceções são declaradas, e são as mesmas da Fase A:
 *   - a alegação proibida, que precisa nomear a leitura causal;
 *   - o campo de horizonte, que precisa nomear o próprio horizonte.
 *
 * A região sem cenários passa por aqui do mesmo jeito: a frase de ausência é
 * texto público como qualquer outro.
 */
function scanScenarios(document, guard, { citesCadastral }) {
  const scenarios = document.scenarios
  guard.checkText(scenarios.label, 'scenarios.label')
  guard.checkText(scenarios.description, 'scenarios.description')

  if (scenarios.status === 'absent') {
    guard.checkText(scenarios.absenceStatement, 'scenarios.absenceStatement')
    guard.checkSentenceComplete(scenarios.absenceStatement, 'scenarios.absenceStatement')
    return document
  }

  guard.checkText(scenarios.statuteReadingNote, 'scenarios.statuteReadingNote')

  const block = scenarios.block
  const horizonYears = [block.targetYear, block.longScanTargetYear]

  guard.checkText(block.methodologyLabel, 'scenarios.block.methodologyLabel')
  guard.checkText(block.focalQuestion, 'scenarios.block.focalQuestion')
  guard.checkText(block.maturityNote, 'scenarios.block.maturityNote')
  guard.checkSentenceComplete(block.maturityNote, 'scenarios.block.maturityNote')
  guard.checkText(block.statuteNote, 'scenarios.block.statuteNote')
  guard.checkSentenceComplete(block.statuteNote, 'scenarios.block.statuteNote')
  guard.checkText(block.baseYearStatement, 'scenarios.block.baseYearStatement')
  guard.checkSentenceComplete(block.baseYearStatement, 'scenarios.block.baseYearStatement')
  guard.checkText(block.compatibilityCeilingStatement, 'scenarios.block.compatibilityCeilingStatement')
  guard.checkText(block.conditionalImplication, 'scenarios.block.conditionalImplication')
  guard.checkSentenceComplete(block.conditionalImplication, 'scenarios.block.conditionalImplication')

  guard.checkHorizonText(block.horizonStatement, 'scenarios.block.horizonStatement', {
    allowedYears: horizonYears,
  })
  guard.checkSentenceComplete(block.horizonStatement, 'scenarios.block.horizonStatement')
  guard.checkHorizonText(block.longScanStatement, 'scenarios.block.longScanStatement', {
    allowedYears: horizonYears,
  })
  guard.checkSentenceComplete(block.longScanStatement, 'scenarios.block.longScanStatement')

  block.realizationConditions.forEach((condition, index) => {
    guard.checkText(condition, `scenarios.block.realizationConditions[${index}]`)
    guard.checkSentenceComplete(condition, `scenarios.block.realizationConditions[${index}]`)
    guard.checkStatuteContradiction(condition, `scenarios.block.realizationConditions[${index}]`)
  })
  block.robustImplications.forEach((implication, index) => {
    guard.checkText(implication, `scenarios.block.robustImplications[${index}]`)
    guard.checkSentenceComplete(implication, `scenarios.block.robustImplications[${index}]`)
  })
  guard.checkProhibitedClaim(block.prohibitedClaim, 'scenarios.block.prohibitedClaim')

  block.normativeCriteria.forEach((criterion, index) => {
    const field = `scenarios.block.normativeCriteria[${index}]`
    guard.checkText(criterion.publicName, `${field}.publicName`)
    for (const key of ['definition', 'requiredState', 'tradeOff', 'failureMode', 'whatToFollow']) {
      guard.checkText(criterion[key], `${field}.${key}`)
      guard.checkSentenceComplete(criterion[key], `${field}.${key}`)
    }
  })

  block.items.forEach((item, index) => {
    const field = `scenarios.block.items[${index}]`
    guard.checkTokens(item.scenarioId, `${field}.scenarioId`)
    guard.checkText(item.title, `${field}.title`)
    guard.checkText(item.profileLabel, `${field}.profileLabel`)
    guard.checkText(item.statuteLabel, `${field}.statuteLabel`)

    const prose = [
      item.centralMechanism,
      item.startingPointStatement,
      item.trajectoryStatement,
      item.stateAtHorizonStatement,
    ]
    const proseFields = [
      'centralMechanism',
      'startingPointStatement',
      'trajectoryStatement',
      'stateAtHorizonStatement',
    ]
    prose.forEach((text, position) => {
      guard.checkText(text, `${field}.${proseFields[position]}`)
      guard.checkSentenceComplete(text, `${field}.${proseFields[position]}`)
      guard.checkStatuteContradiction(text, `${field}.${proseFields[position]}`)
    })

    item.anchors.forEach((anchor, position) => {
      guard.checkText(anchor.label, `${field}.anchors[${position}].label`)
      guard.checkText(anchor.periodLabel, `${field}.anchors[${position}].periodLabel`)
      guard.checkText(anchor.directionLabel, `${field}.anchors[${position}].directionLabel`)
      guard.checkTokens(anchor.seriesId, `${field}.anchors[${position}].seriesId`)
    })

    item.educationImplications.forEach((implication, position) => {
      guard.checkText(implication.stageLabel, `${field}.educationImplications[${position}].stageLabel`)
      guard.checkText(implication.statement, `${field}.educationImplications[${position}].statement`)
      guard.checkSentenceComplete(
        implication.statement,
        `${field}.educationImplications[${position}].statement`,
      )
      guard.checkStatuteContradiction(
        implication.statement,
        `${field}.educationImplications[${position}].statement`,
      )
    })

    item.contraryEvidence.forEach((evidence, position) => {
      guard.checkText(evidence, `${field}.contraryEvidence[${position}]`)
      guard.checkSentenceComplete(evidence, `${field}.contraryEvidence[${position}]`)
    })
    /* O limite do cenário é onde ele declara o que não alcança — mesma língua
     * natural da limitação de série, e mesma isenção de conectivo causal. */
    item.limits.forEach((limit, position) => {
      guard.checkText(limit, `${field}.limits[${position}]`, { exemptConnective: true })
      guard.checkSentenceComplete(limit, `${field}.limits[${position}]`)
    })

    guard.checkProhibitedClaim(item.prohibitedClaim, `${field}.prohibitedClaim`)

    /*
     * A frase partida entre dois campos, de novo: o cenário tem quatro campos
     * de prosa longa que a página renderiza um embaixo do outro, e a varredura
     * por campo não vê a oração que atravessa a fronteira entre eles.
     */
    guard.checkCausal([...prose, ...item.contraryEvidence].join(' '), `${field} (texto corrido)`)

    if (citesCadastral(...item.anchors)) {
      for (const text of prose) guard.checkCadastralComparison(text, `${field} (prosa)`)
      item.educationImplications.forEach((implication, position) => {
        guard.checkCadastralComparison(
          implication.statement,
          `${field}.educationImplications[${position}].statement`,
        )
      })
    }
  })

  return document
}

/*
 * As três regras que o plano nomeia por escrito na Tarefa 2 da Rodada 5 —
 * prévia rotulada, universo do cadastro social declarado, qualificador de
 * estimativa na migração. Elas são estruturais, não lexicais: o contrato já
 * recusa prévia com classe de observação, e aqui se confere que o documento
 * publicado de fato **carrega** a marcação que a página vai renderizar.
 */
export function assertPublicationRules(document, { cadastralUniverseLabel }) {
  let preliminaryPeriods = 0
  let cadastralSeries = 0
  let estimateSeries = 0

  for (const serie of document.territoryPortrait.series) {
    const field = `série "${serie.label}"`

    if (serie.preliminaryPeriods.length > 0) {
      preliminaryPeriods += serie.preliminaryPeriods.length
      for (const period of serie.preliminaryPeriods) {
        const point = serie.points.find((candidate) => candidate.period === period)
        if (point === undefined || point.evidenceClass !== 'preliminary') {
          fail('PRELIMINARY_NOT_LABELLED', field, `o período de prévia ${period} não chega rotulado como prévia`)
        }
      }
    }

    if (serie.universeLabel === cadastralUniverseLabel) {
      cadastralSeries += 1
    }

    /*
     * Estimativa e cálculo nunca viajam sozinhos. O saldo migratório aparente
     * é resíduo de uma equação de coortes, e o risco 7 do plano é ele ser lido
     * como fluxo observado. Nenhuma série calculada ou estimada sai daqui sem
     * a ressalva que a torna honesta.
     */
    if (serie.evidenceClass === 'calculated' || serie.evidenceClass === 'estimated_indirect') {
      estimateSeries += 1
      if (serie.limitations.length === 0) {
        fail(
          'ESTIMATE_WITHOUT_METHOD_NOTE',
          field,
          `a série de classe ${serie.evidenceClass} não traz nota de método`,
        )
      }
    }
  }

  /*
   * O universo do cadastro social é obrigatório sempre que houver série dele.
   * Zero séries cadastrais é um estado possível e legítimo; série cadastral sem
   * universo não é — e o contrato já a recusaria antes de chegar aqui.
   */
  return { preliminaryPeriods, cadastralSeries, estimateSeries }
}
