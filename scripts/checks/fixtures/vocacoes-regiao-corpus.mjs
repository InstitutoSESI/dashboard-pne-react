/*
 * Corpus adversarial do Vocações da Região — fixture permanente.
 *
 * Os dezenove ataques e os seis textos honestos nasceram na Rodada 4, medidos
 * contra a guarda da camada de pesquisa. O `C24` da Rodada 5 os transforma em
 * fixture desta camada: todo ataque encontrado em qualquer ciclo vira fixture
 * permanente, e todo texto honesto barrado indevidamente também (§5.5).
 *
 * O corpus mora no repositório, e não no diretório da rodada, porque é isso que
 * "permanente" quer dizer: a rodada acaba, o corpus fica, e a próxima mudança na
 * guarda passa por ele.
 *
 * Cada caso é uma mutação sobre o pacote publicado. Os textos são literais aos
 * da Rodada 4 — reescrevê-los para caber melhor seria trocar o corpus por um
 * corpus mais fácil.
 */

const primeiraAssociacao = (d) => d.associations.items[0]
const primeiroPar = (d) => d.temporalPairs.items[0]
/*
 * Uma associação cadastral é a que cita uma série de universo cadastral — a
 * mesma definição que a guarda usa (`universeLabel`), e não o slug de uma série
 * específica. A Rodada 3 do V2 passou a selecionar associações por região, e a
 * série cadastral que aparece varia entre "pessoas inscritas" e "famílias
 * inscritas"; casar só o slug de uma delas acoplava o corpus ao template antigo.
 */
const associacaoCadastral = (d) => {
  const cadastralIds = new Set(
    d.territoryPortrait.series
      .filter((serie) => typeof serie.universeLabel === 'string'
        && serie.universeLabel.startsWith('Universo cadastral'))
      .map((serie) => serie.seriesId),
  )
  return d.associations.items.find((item) =>
    cadastralIds.has(item.educationOutcome.seriesId)
    || item.territorialFactors.some((fator) => cadastralIds.has(fator.seriesId)))
}
const serie = (d, fragmento) =>
  d.territoryPortrait.series.find((item) => item.seriesId.includes(fragmento))

/*
 * Os dezenove ataques da Rodada 4, com o texto literal de lá. O vetor é o mesmo
 * numerado no corpus original; o campo é o equivalente público.
 */
const ATAQUES = [
  ['A-R4-01', 1, (d) => {
    primeiraAssociacao(d).prohibitedClaim =
      'Não se pode concluir que a relação seja apenas descritiva, mas a perda de renda causou o abandono escolar.'
  }],
  ['A-R4-02', 6, (d) => {
    primeiroPar(d).prohibitedClaim =
      'Não se pode concluir que as séries apenas coincidam, pois a retração do emprego causou a evasão escolar.'
  }],
  ['A-R4-03', 2, (d) => {
    primeiraAssociacao(d).observedStatement = 'A retração do emprego levou'
    primeiraAssociacao(d).allowedInterpretation = 'à evasão escolar.'
  }],
  ['A-R4-04', 2, (d) => {
    primeiraAssociacao(d).observedStatement = 'A falta de renda fez'
    primeiraAssociacao(d).hypotheses = ['com que a evasão escolar avançasse.', ...primeiraAssociacao(d).hypotheses]
  }],
  ['A-R4-05', 2, (d) => {
    primeiraAssociacao(d).observedStatement = 'A evasão escolar aumentou devido'
    primeiraAssociacao(d).allowedInterpretation = 'à retração do emprego formal.'
  }],
  ['A-R4-06', 3, (d) => {
    primeiraAssociacao(d).allowedInterpretation =
      'A evasão escolar foi moldada pela retração do emprego formal.'
  }],
  ['A-R4-07', 3, (d) => { primeiroPar(d).label = 'Retração do emprego, motor da evasão escolar' }],
  ['A-R4-08', 3, (d) => {
    primeiraAssociacao(d).hypotheses = [
      'Sem renda estável, a permanência escolar não se sustenta.',
      ...primeiraAssociacao(d).hypotheses,
    ]
  }],
  ['A-R4-09', 3, (d) => {
    primeiroPar(d).observedStatement = 'Primeiro caiu o emprego formal; depois avançou a evasão escolar.'
  }],
  ['A-R4-10', 4, (d) => { primeiroPar(d).observedStatement = 'No ano 20 30, haverá 145 mil matrículas.' }],
  ['A-R4-11', 4, (d) => {
    primeiraAssociacao(d).allowedInterpretation =
      'Os nascidos em 2020 chegam ao ensino médio aos quinze anos, em uma turma de 12 mil estudantes.'
  }],
  ['A-R4-12', 4, (d) => {
    primeiroPar(d).observedStatement = 'Em 2030: uma em cada três matrículas no ensino médio.'
  }],
  ['A-R4-13', 4, (d) => {
    primeiraAssociacao(d).hypotheses = [
      'Daqui a quatro anos, haverá 145 mil matrículas no ensino médio.',
      ...primeiraAssociacao(d).hypotheses,
    ]
  }],
  ['A-R4-14', 5, (d) => {
    associacaoCadastral(d).allowedInterpretation =
      'As pessoas inscritas no cadastro social equivalem a 18% da população regional.'
  }],
  ['A-R4-15', 5, (d) => {
    const alvo = associacaoCadastral(d)
    alvo.observedStatement =
      'Em 2025, havia três pessoas inscritas no cadastro a cada dez moradores da região.'
  }],
  ['A-R4-16', 5, (d) => {
    associacaoCadastral(d).hypotheses = [
      'Duzentas e quarenta mil pessoas inscritas diante de um milhão e duzentos mil habitantes '
      + 'correspondem a uma parcela de 20% da população.',
      ...associacaoCadastral(d).hypotheses,
    ]
  }],
  ['A-R4-17', 2, (d) => {
    const nascidos = serie(d, 'nascidos-vivos')
    const obitos = serie(d, 'obitos-por-residencia-em-todas-as-idades') ?? serie(d, 'obitos')
    primeiroPar(d).seriesA = { seriesId: nascidos.seriesId, label: nascidos.label }
    primeiroPar(d).seriesB = { seriesId: obitos.seriesId, label: obitos.label }
    primeiroPar(d).window = { start: 2025, end: 2026 }
    primeiroPar(d).periodLabel = '2025 a 2026'
    primeiroPar(d).label = 'Nascidos vivos e óbitos observados'
    primeiroPar(d).observedStatement =
      'Em 2025, foram observados 11 353 nascidos vivos e 11 075 óbitos na região.'
  }],
  ['A-R4-18', 2, (d) => {
    const nascidos = serie(d, 'nascidos-vivos')
    const obitos = serie(d, 'obitos-por-residencia-em-todas-as-idades') ?? serie(d, 'obitos')
    primeiroPar(d).seriesA = { seriesId: nascidos.seriesId, label: nascidos.label }
    primeiroPar(d).seriesB = { seriesId: obitos.seriesId, label: obitos.label }
    primeiroPar(d).window = { start: 2025, end: 2026 }
    primeiroPar(d).periodLabel = '2025 a 2026'
    primeiroPar(d).label = 'Séries consolidadas de nascimentos e óbitos'
    primeiroPar(d).observedStatement =
      'Os dados de 2026 confirmam quatro mil trezentos e trinta e quatro nascidos vivos e '
      + 'três mil quatrocentos e setenta e cinco óbitos na região.'
  }],
  ['A-R4-19', 4, (d) => {
    primeiroPar(d).observedStatement = 'No ano dois mil mais trinta, haverá 145 mil matrículas.'
  }],
]

/* Os seis textos honestos que a guarda da pesquisa recusava (falso positivo). */
const HONESTOS = [
  ['H-R4-01', (d) => {
    primeiraAssociacao(d).allowedInterpretation =
      'Não se pode afirmar que a queda do emprego causou a evasão escolar.'
  }],
  ['H-R4-02', (d) => {
    primeiraAssociacao(d).hypotheses = [
      'A associação observada não explica o abandono escolar.',
      ...primeiraAssociacao(d).hypotheses,
    ]
  }],
  ['H-R4-03', (d) => {
    primeiroPar(d).observedStatement = 'A coevolução observada não se deve à pobreza.'
  }],
  ['H-R4-04', (d) => {
    primeiraAssociacao(d).hypotheses = [
      'A perda de renda não influenciou a permanência escolar.',
      ...primeiraAssociacao(d).hypotheses,
    ]
  }],
  ['H-R4-05', (d) => {
    primeiraAssociacao(d).allowedInterpretation =
      'A associação é apenas descritiva, pois as séries não permitem inferência causal.'
  }],
  ['H-R4-06', (d) => {
    primeiroPar(d).observedStatement =
      'A janela termina em 2025; portanto, 2030 não integra o período observado.'
  }],
]


export const ATTACK_COUNT = ATAQUES.length
export const HONEST_COUNT = HONESTOS.length

/*
 * Os furos que esta camada **não** fecha, declarados em vez de escondidos.
 *
 * São quatro, e vêm dos cinco que a Rodada 4 declarou: três construções causais
 * de classe aberta do vetor 3 — voz passiva com agente (`A-R4-06`), condicional
 * de necessidade (`A-R4-08`) e enquadramento por ordem dos fatos (`A-R4-09`) —
 * mais o futuro implícito sem ano nenhum do `A-R4-11`. São o item `B4` do
 * backlog, herdado da Rodada 4.
 *
 * O quinto (`A-R4-07`, nominalização metafórica no rótulo de um par) fechou
 * aqui, e não por lexicografia: a regra de derivação do identificador, escrita
 * depois da revisão adversarial do contrato, exige que o `pairId` seja o slug
 * do rótulo. Trocar o rótulo por uma metáfora quebra a derivação. Um ataque
 * fechado por acidente de outra regra continua fechado — mas fica registrado
 * que foi assim, porque a lexicografia dele segue aberta.
 */
export const DECLARED_GAPS = Object.freeze(['A-R4-06', 'A-R4-08', 'A-R4-09', 'A-R4-11'])

export { ATAQUES, HONESTOS }
