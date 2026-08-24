# Matriz de Prioridades — plano de evolução da página

Documento de planejamento. Registra a revisão feita em 2026-08-18 sobre o estado
atual da página e propõe as próximas etapas de evolução, mantendo o contrato
editorial de `docs/MATRIZ_FRENTES_RECOMENDADAS.md`.

- Antecedentes: `docs/MATRIZ_DE_PRIORIDADES.md` (causas) e
  `docs/MATRIZ_FRENTES_RECOMENDADAS.md` (frentes, contrato vigente).
- O artefato publicado (`public/data/pne2026-matriz/`) só muda quando uma fase
  depende de informação comparativa nova e rastreável. A classificação vigente
  não é recalculada na interface.
- Decisão editorial de 2026-08-18: a página é expositiva. A experiência "Meu
  plano de ação" e o "Guia rápido" foram retirados; rótulos visíveis não tratam
  diretamente o usuário.

---

## 1. Estado atual (o que a página já entrega)

- Resumo com contagem de metas e caminhos, mais uma síntese de até duas metas
  com maior diferença frente ao grupo de comparação.
- Matriz comparativa compacta, organizada pela distância da referência e pela
  situação entre cidades parecidas, com acesso ao detalhamento de cada meta.
- 7 blocos de meta, cada um com situação numérica, distância da referência,
  leitura de pares e rótulo de atenção.
- 7 seções "Caminhos para avançar": um parágrafo curto e exatamente dois
  cartões por meta, ligando contexto, fato relevante, verificação e ação.
- 14 cartões: contexto e resultado esperado ficam visíveis; etapas, apoio
  federal, base legal e informações relacionadas abrem sob demanda.
- Blocos de honestidade recolhidos: outras metas abaixo do esperado e onde o
  município está bem.
- Guarda-corpos de linguagem testados em `scripts/checks/matriz-language.test.mjs`.

### Diagnóstico da revisão

1. **A grade anterior não evidenciava a prioridade relativa.** As metas eram
   apresentadas individualmente, sem mostrar no mesmo plano o cruzamento entre
   distância da referência e situação entre cidades parecidas.
2. **Não há noção de tempo.** A página mostra uma foto; não mostra se o
   município melhorou desde a leitura anterior nem convida a voltar.

## 2. Princípios (o que não muda)

- A regra central do contrato editorial: orientação oficial define as frentes;
  dados municipais só contextualizam; nada afirma causa local.
- Nenhuma fase recalcula indicador. Mudanças no artefato ou na camada de
  pesquisa exigem versão de contrato, testes de domínio e publicação controlada.
- Todo texto novo visível passa pelo check de linguagem (sem "causa", sem
  vocabulário técnico, sem identificadores internos).
- A página não solicita registro, seleção ou anotação ao usuário final.

## 3. Fase A — síntese comparativa (anti-massante)

> **Status:** refinada em 2026-08-19 (executor GPT, verificação
> independente: testes de linguagem, typecheck, lint e inspeção no navegador).

Objetivo: permitir a identificação das metas mais críticas em uma leitura
inicial curta, sem ampliar o volume de conteúdo.

1. **Matriz comparativa de entrada.** Acima dos blocos de meta, as 7 metas são
   distribuídas pelo cruzamento de duas classificações já publicadas: distância
   da referência e situação entre cidades parecidas. Cada cartão mantém título,
   valor e acesso ao bloco da meta. O selo de atenção permanece no detalhamento,
   sem repetir no quadro o que os eixos já sintetizam. A matriz substitui a
   antiga grade; não acrescenta fórmula, inferência ou seção.
2. **Dois caminhos por meta.** Cada cartão reúne contexto, fato útil,
   verificação e resultado esperado; etapas, apoio federal, base legal e
   aprofundamento abrem sob demanda (`details`).
   A página elimina os blocos paralelos e reduz o piloto a 14 cartões.
3. **Primeiro movimento.** Em cada meta, um caminho de natureza estruturante é
   identificado editorialmente — em geral o caminho de conhecimento ou
   diagnóstico (ex.: "Conhecer a procura por vaga" na creche). O selo não
   afirma causa local nem solicita uma ação na própria página.

Critérios de aceite: a informação decisiva permanece; os detalhes ficam
recolhidos; o check de linguagem continua verde; cada meta tem dois caminhos.

## 4. Fase B — retirada por decisão editorial

> **Status:** retirada em 2026-08-18. Painel, seleção de frentes, estados,
> anotações, exportação do plano e versão para reunião não fazem parte da página.

A Matriz apresenta evidências e frentes recomendadas. A organização de um plano
de ação ocorre fora desta tela e não deve retornar sem nova decisão de produto.
Registros locais antigos não são lidos nem apagados pela interface.

## 5. Fase C — tempo e escala

Objetivo: dar noção de progresso entre leituras e preparar a saída do piloto.

1. **Comparação entre datas de referência.** Quando houver mais de uma
   publicação do artefato para o município, mostrar por meta: "na leitura de
   {data anterior}: X · hoje: Y". Exige guardar (ou publicar) a leitura
   anterior — decidir entre histórico no artefato ou snapshot local. Sem
   segunda leitura, a seção não aparece (sem mensagem de ausência, mesma regra
   das frentes).
2. **Mais municípios.** Replicar a publicação para além de Nova Santa Rita
   seguindo o processo do piloto. Depende da camada `SESI\PNE`; nesta
   plataforma é só receber artefatos. Gate: validação do piloto com usuários
   reais.

## 5-D. Fase D — profundidade que ajuda (conteúdo)

Registrada em 2026-08-18 a pedido do operador. Restrição central, nas palavras
dele: **não pode virar de novo uma lista de vários dados que espanta quem usa;
tem que auxiliar de verdade e ser o diferencial da plataforma.**

### Princípio único

> Cada frente responde às três perguntas do gestor — *onde estou, o que fazer
> primeiro, com que apoio conto* — e só mostra um número quando ele muda uma
> decisão. Número sem consequência prática não entra.

A profundidade ocupa **um parágrafo e dois cartões por meta**. Contexto e ação
ficam no mesmo cartão; nenhum fato municipal aparece em um bloco paralelo.

### D1. Leitura acompanhada (dados do próprio município)

> **Status:** implementada em 2026-08-18 e integrada aos caminhos em 2026-08-19.
> O contrato inicial por frente e a leitura separada foram substituídos por um
> único cartão, deixando o dado junto do mecanismo e da ação correspondente.

- Cada leitura continua sendo **número + frase de uso**, agora no cartão:
  a frase diz o que o número muda na investigação e explicita seu limite.
- Fonte: medidas já publicadas no artefato, hoje sem uso na página. Curadoria
  frente a frente; entra apenas o que passa no teste da frase de uso.
- **Teto reduzido e testado: 1 fato por mecanismo e 2 mecanismos por meta.**
  Sem frase honesta possível, o fato fica de fora e permanece apenas a
  verificação local.

### D2. Uma leitura de pares por indicador

> **Status:** implementada em 2026-08-19. O contrato `matriz-3.0.0` publica a
> mediana anônima, a diferença `município − mediana`, unidade, ano e tamanho do
> grupo. Os sete indicadores prioritários do piloto têm leitura comparável.

- A comparação pertence ao indicador, não a uma frente. Por isso substitui o
  rótulo genérico já existente na linha de situação da meta, sem se repetir nos
  14 cartões e sem criar novo bloco.
- No resumo existente, no máximo duas metas da faixa de maior defasagem são
  citadas com diferença e ano. A seleção usa somente comparações percentuais já
  publicadas; na ausência delas, permanece apenas o tamanho do grupo.
- Formato público: `Cidades parecidas do RS (88, 2025): mediana 50,9% ·
  município 15,8 p.p. abaixo`.
- A leitura só é publicada quando indicador, unidade e ano coincidem em todo o
  grupo efetivamente usado. Caso contrário, `peerBenchmark` é `null` e nenhum
  texto numérico aparece.
- Continua proibido: tabela, ranking, posição ordinal, nome ou valor individual
  de outro município.

### D3. Guia rápido federal por frente

> **Status:** retirada em 2026-08-18. O bloco duplicava as ações recomendadas e
> criava tom excessivamente instrucional. As fontes essenciais continuam nos
> programas federais e na base legal de cada frente.

### D4. Pontes internas do painel

> **Status:** revisada em 2026-08-19. Treze caminhos levam a uma seção
> temática do painel de Educação com o mesmo código IBGE. A frente climática não
> recebeu link porque nenhuma tela interna aprofunda o tema; não foi criado um
> atalho genérico só para completar a contagem.

- Onde outra tela do painel já aprofunda o tema da frente (financiamento,
  indicadores), a frente ganha **1 link interno** de uma linha
  ("Recursos de transporte escolar no município"), preservando o
  município selecionado.
- Teto testado: 1 ponte por frente. A matriz nunca duplica conteúdo das outras
  telas.

### D5. Resultado esperado por caminho

> **Status:** revisada em 2026-08-19. Os 14 caminhos receberam uma entrega
> verificável, derivada das ações federais já registradas e visível antes do
> conteúdo expandido.

- Cada caminho apresenta **1 frase** sob o rótulo "Resultado esperado".
  A frase traduz as orientações em um resultado operacional observável, sem
  definir prazo, responsável ou afirmar uma condição local não publicada.
- O resultado é editorial: não representa nova meta numérica, cálculo, indicador ou
  campo do artefato. Sua fonte continua sendo o conjunto de ações e referências
  oficiais já curado para o caminho.
- O texto aparece antes do `details`, para que a entrega pretendida não dependa
  da abertura do apoio. O teste exige presença, pontuação final e teto de 160
  caracteres por caminho.

### D6. Contexto e mecanismos para decisão

> **Status:** implementada em 2026-08-19 a partir da metodologia do Vocações.

- Cada meta ganhou uma sequência única e curta: **situação → foco da decisão →
  dois caminhos**, cada um ligando mecanismo, contexto e ação.
- A comparação com cidades parecidas permanece uma única vez no cabeçalho da
  meta; não é repetida nos cartões.
- Todo mecanismo termina em "Antes de agir, confira", convertendo o contexto em
  uma checagem concreta com registros municipais, escolas e equipes.
- No piloto, são 14 mecanismos e 8 contextos públicos selecionados. Não há nova
  tabela, ranking, formulário ou recálculo.
- Sete contextos continuam resolvidos do artefato da matriz. O oitavo é o
  recorte de acessibilidade por rede da publicação educacional validada: em
  2025, 53,8% das salas municipais e 0% das estaduais foram declaradas
  acessíveis. O texto explicita que declaração administrativa orienta vistoria,
  mas não substitui avaliação técnica.
- Na EJA, o resultado de integração profissional informa se a modalidade já
  aparece nas matrículas, mas não define curso nem comprova demanda profissional.

### Guarda-corpos anti-massante (todos verificáveis em código)

1. A comparação de pares substitui a leitura genérica do indicador; a síntese
   no resumo tem teto de duas metas e não cria seção, cartão ou tabela.
2. Tetos: 2 mecanismos e 2 caminhos por meta, 1 fato por mecanismo, 1 resultado
   esperado e 1 ponte interna por caminho.
3. Toda leitura tem frase de uso e verificação local; nenhum texto novo viola o check de linguagem
   vigente nem trata diretamente o usuário final.
4. Continua proibido: afirmar razão local, ranking de municípios, tabela de
   dados dentro de frente, mensagem de ausência de dado.

### Ordem interna sugerida

| passo | entrega | dá para começar |
|---|---|---|
| D1 | leituras acompanhadas | entregue em 2026-08-18 |
| D4 | pontes internas | entregue em 2026-08-18 |
| D5 | resultados esperados | revisado em 2026-08-19 |
| D2 | mediana anônima por indicador | entregue em 2026-08-19 |
| D6 | contexto e mecanismos para decisão | entregue em 2026-08-19 |

## 6. Ordem recomendada e dependências

| ordem | entrega | depende de |
|---|---|---|
| 1 | Fase A inteira (matriz comparativa, dois caminhos e primeiro movimento) | nada |
| 2 | C1 (comparação entre leituras) | segunda publicação do artefato |
| 3 | C3 (mais municípios) | validação do piloto |
| paralelo | D1, D4, D5 e D6 (profundidade que ajuda) | Fase A publicada |
| paralelo | D2 (mediana anônima por indicador) | entregue no artefato v3 |

Fase A responde ao risco de uma página massante e não mexe em dados. Fase C
depende de fatos externos (nova publicação e validação).

## 7. Fora de escopo (deliberado)

- Qualquer recálculo ou nova inferência sobre dados municipais.
- Contas de usuário, seleção de frentes, anotações ou montagem de plano na tela.
- Editar o conteúdo dos 14 caminhos sem revisão editorial explícita conforme o
  contrato de `docs/MATRIZ_FRENTES_RECOMENDADAS.md`.

## 8. Revisões da implementação (2026-08-18)

A matriz comparativa usa tabela semântica e botões com rolagem e foco
programáticos, sem disputar a rota por hash. Em telas estreitas, as células são
apresentadas por faixa de distância, sem rolagem horizontal. A margem de rolagem
mantém o título da meta abaixo da barra fixa. As experiências de plano e guia
foram removidas por decisão editorial e não representam o estado atual.

Na revisão de 2026-08-19, leitura para decisão e frentes foram reunidas em
"Caminhos para avançar". Cada meta passou a ter dois cartões; o resultado
esperado ficou visível e as etapas e apoios permaneceram recolhidos. O recorte
validado de acessibilidade por rede foi integrado somente à meta em que altera a
responsabilidade de ação. Os cartões da mesma linha mantêm altura própria.

### Próximo passo

O próximo avanço não é acrescentar outro bloco genérico. D2 e D6 estão
concluídas e C1 aguarda uma segunda data de referência. C3 continua condicionada
à validação do piloto com gestores. Até esses fatos existirem, o foco é validar
com a gestão se os 14 mecanismos selecionados orientam decisões reais e ajustar
o conteúdo sem ampliar os tetos.

> **Nota de 2026-08-20:** a evolução da plataforma para receber trajetória,
> concentração na rede e medianas por medida foi especificada no
> [contrato `matriz-4.0.0`](MATRIZ_CONTRATO_V4.md). Os cálculos e as decisões
> metodológicas correspondentes permanecem na camada de pesquisa.
