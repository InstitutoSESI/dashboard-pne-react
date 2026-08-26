/*
 * Corpus adversarial do bloco ponte — fixture permanente (Rodada 4 do V2).
 *
 * A ponte tem dois sentidos e dois vetores próprios, e este corpus os fixa:
 *
 *   - **PNE → Vocações** (bloco territorial da matriz): a leitura honesta é "a
 *     região do município apresenta…"; a proibida é a região **explicando** ou
 *     **determinando** o resultado do município.
 *   - **Vocações → PNE** (temas de agenda): o tema nomeia a meta, nunca o
 *     número dela. "Meta 3", "estratégia 3.1", ano futuro de meta são o vetor.
 *
 * Cada caso é um texto literal, varrido por `checkBridgeText` (o perfil do bloco
 * ponte). Ataque tem de ser recusado; honesto tem de passar. Os furos de classe
 * aberta que a guarda não fecha estão declarados em `DECLARED_GAPS`, não
 * escondidos — mesma disciplina do corpus da Fase A (§5.5).
 */

/* Ataques que a guarda do bloco ponte precisa recusar. */
export const ATTACKS = Object.freeze([
  /* Causalidade município ← região, forma explícita. */
  ['B-PONTE-01', 'Isto explica o resultado do município.'],
  ['B-PONTE-02', 'A vocação econômica da região explica o município.'],
  ['B-PONTE-03', 'A composição do território determina o resultado do município.'],
  ['B-PONTE-04', 'O município apresenta esse quadro porque a região concentra indústria.'],
  /* Causalidade genérica, herdada da guarda causal. */
  ['B-PONTE-05', 'A retração do emprego na região causou o baixo desempenho do município.'],
  ['B-PONTE-06', 'A perda de renda regional levou à evasão escolar no município.'],
  /* Meta do PNE com número. */
  ['B-PONTE-07', 'A meta 3 do PNE exige universalização do ensino médio na região.'],
  ['B-PONTE-08', 'Cumprir a estratégia 3.1 do plano nacional na região.'],
  ['B-PONTE-09', 'A região precisa avançar nas metas 6 e 7 do PNE.'],
  /* Número futuro de meta. */
  ['B-PONTE-10', 'Até 2031 a região universaliza o ensino médio.'],
  ['B-PONTE-11', 'Em 2031 serão 145 mil matrículas no ensino médio da região.'],
  /* Grafias alternativas do número de meta — ataques da auditoria de gate. */
  ['B-PONTE-12', 'A meta número 3 do PNE orienta este tema.'],
  ['B-PONTE-13', 'A meta n. 3 do PNE orienta este tema.'],
  ['B-PONTE-14', 'A meta #3 do PNE orienta este tema.'],
  ['B-PONTE-15', 'A meta-3 do PNE orienta este tema.'],
  ['B-PONTE-16', 'A Meta III do PNE orienta este tema.'],
  ['B-PONTE-17', 'A meta ３ do PNE orienta este tema.'],
  ['B-PONTE-18', 'A meta ³ do PNE orienta este tema.'],
  ['B-PONTE-19', 'A estratégia de número 3.1 do PNE orienta este tema.'],
  ['B-PONTE-20', 'A meta três do PNE orienta este tema.'],
  /* Formas causais município ← região não cobertas pelo corpus original. */
  ['B-PONTE-21', 'O resultado do município se explica pela estrutura da região.'],
  ['B-PONTE-22', 'A região condiciona o desempenho do município.'],
  ['B-PONTE-23', 'A estrutura da região responde pelo resultado do município.'],
  ['B-PONTE-24', 'A estratégia N° 3.1 do PNE orienta este tema.'],
])

/* Textos honestos que a guarda do bloco ponte precisa aceitar. */
export const HONEST = Object.freeze([
  ['H-PONTE-01', 'A região do município apresenta leituras entre educação e território.'],
  ['H-PONTE-02', 'Estas leituras descrevem a região, não o município: não explicam o resultado do município.'],
  ['H-PONTE-03', 'Universalização e permanência no ensino médio é um tema da agenda educacional da região.'],
  ['H-PONTE-04', 'A região apresenta alta concentração industrial observada na janela.'],
  ['H-PONTE-05', 'A janela termina em 2025; portanto, 2031 não integra o período observado da região.'],
  ['H-PONTE-06', 'Educação de jovens e adultos e educação profissional aparecem entre os temas da região.'],
  /* Controles da auditoria: a ampliação não pode barrar negação honesta nem
   * número que não identifica uma meta/estratégia. */
  ['H-PONTE-07', 'A estratégia foi analisada em três municípios.'],
  ['H-PONTE-08', 'O resultado do município não se explica pela estrutura da região.'],
  ['H-PONTE-09', 'A região não condiciona o desempenho do município.'],
  ['H-PONTE-10', 'A estrutura da região não responde pelo resultado do município.'],
  ['H-PONTE-11', 'A estratégia civil de educação é apresentada sem numeração de meta.'],
])

/*
 * Furos de classe aberta declarados — a guarda não os fecha, e dizer isso é a
 * regra. São construções causais que não usam nenhum verbo da lista causal nem
 * a forma "explica/determina o município": voz passiva com agente e
 * enquadramento por ordem. Fechá-los exigiria casar semântica, não léxico —
 * item de backlog, como os `A-R4-06/08/09` da Fase A.
 */
export const DECLARED_GAPS = Object.freeze([
  ['B-PONTE-GAP-01', 'O resultado do município é moldado pelo território da região.'],
  ['B-PONTE-GAP-02', 'Primeiro a região perdeu indústria; depois o município perdeu matrículas.'],
])

export const ATTACK_COUNT = ATTACKS.length
export const HONEST_COUNT = HONEST.length
