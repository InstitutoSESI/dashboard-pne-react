# Contrato de produto e de linguagem — Vocações × PNE

**Versão documental:** 2.1.0 (contrato analítico V7 + decisão de promoção oficial)

**Origem normativa:** `docs/arquivo/planos-vocacoes-regiao/PLANO_APROFUNDAMENTO_VOCACOES_PNE.md`, evidências do Job 0 e `docs/DECISAO_PROMOCAO_OFICIAL_VOCACOES_PNE.md`

**Piloto:** Vale do Sinos; validação municipal obrigatória em Nova Santa Rita (`4313375`)

**Estado:** leitura agregada observacional promovida para a rota oficial em 2026-08-30; o Gate 11 histórico do fluxo Job 5M permanece fechado

**Aplicação:** este contrato governa a V7. A promoção 2.1 usa os bundles validados dos Jobs 5I/5K na rota oficial do Vale do Sinos; a implementação V6 descrita no Anexo A permanece como rollback automático.

---

## 0. Decisão de promoção oficial — 2026-08-30

A solicitação explícita de promoção autoriza uma superfície oficial **agregada e
observacional** para o Vale do Sinos, incluindo a leitura municipal de Nova
Santa Rita (`4313375`). A decisão não altera fórmulas nem reabre os resultados
históricos dos Jobs 5J–5L: ela transforma os resultados julgados em narrativa
de planejamento com alcance proporcional à evidência.

A superfície promovida deve conter:

- quatro leituras em `educacao_para_territorio` e três agendas em
  `territorio_para_educacao`;
- três conexões complementares quando disponíveis no recorte selecionado:
  contexto socioeconômico × trajetória, ruralidade × oferta/transporte e
  educação especial × AEE;
- evidências, períodos, lentes territoriais, mecanismo plausível, pergunta de
  planejamento, responsabilidade e limite de interpretação em cada cartão;
- resultado negativo ou instável como **fronteira visível**, quando isso evitar
  uma relação forçada e ainda produzir uma decisão útil de monitoramento;
- fallback integral para a narrativa V6 se identidade, hash, cobertura ou
  runtime da superfície promovida falhar.

Continuam proibidos: afirmação causal; ligação de registros das mesmas pessoas;
recomendação automática de curso; cenário numérico municipal; conversão de
código IBGE; escrita manual em `public/data`.

Esta seção prevalece sobre as regras históricas de “retenção silenciosa” apenas
para relações avaliadas que aparecem explicitamente como limite de evidência,
sem conclusão positiva. O Gate 11 permanece fechado para uma futura publicação
automatizada Job 5M e não deve ser reescrito retroativamente.

---

## 1. Limite desta aprovação

A aprovação documental da V7 fixa perguntas, limites e gates. Ela não:

- altera fórmulas, fontes, dados públicos, schemas ou interface;
- aprova como insight qualquer candidata ainda não calculada;
- autoriza aquisição de nova fonte;
- abre o Gate 11 do piloto;
- substitui a validação humana.

Nenhum código deve ser implementado antes do aceite deste contrato. A transição
deve evoluir os artefatos canônicos existentes, sem criar arquitetura paralela.

## 2. Princípios invariantes

1. Código IBGE textual de sete dígitos é a identidade municipal.
2. População significa moradores; matrícula, escolas localizadas; vínculo,
   estabelecimentos localizados. Contraste entre lentes não é junção de pessoas.
3. Associação territorial não demonstra causa nem identifica os mesmos indivíduos.
4. Fotografia, série observada, tendência sustentada e cenário são bases distintas.
5. Zero, `null`, indisponível, suprimido e não aplicável permanecem distintos.
6. Toda história integra fatos para mudar uma decisão; justapor séries não basta.
7. Toda questão nomeia público/etapa, fenômeno, recorte, indicador e responsabilidade.
8. Candidata reprovada é registrada internamente e omitida da interface.
9. Não há score sintético, ranking opaco ou preenchimento editorial de quantidade.
10. Toda frase pública resolve para fatos, período, lente, fonte e cálculo.

## 3. Contrato das duas saídas

### 3.1 O território ajuda a compreender a educação

A direção `educacao_para_territorio` parte de mudança educacional observada e
responde, nessa ordem:

1. o que mudou;
2. quanto acompanha a demografia, quando pertinente;
3. o que trajetória, oferta, trabalho, EJA ou formação acrescentam;
4. onde se concentram municípios, redes, etapas e públicos;
5. como o município selecionado difere ou contribui;
6. que questão específica entra no planejamento.

O Vale do Sinos exige quatro histórias aprovadas. No máximo uma pode ter núcleo
demográfico; pelo menos duas devem continuar úteis sem variáveis demográficas.

### 3.2 O futuro do território coloca temas na agenda da educação

A direção `territorio_para_educacao` parte de mudança observada, tendência
sustentada ou cenário publicado e responde:

1. o que está mudando no território;
2. quais municípios e públicos estão expostos;
3. qual é o ponto de partida educacional;
4. que preparação ou coordenação isso exige;
5. quais temas do PNE e indicadores devem ser acompanhados.

O Vale do Sinos exige três agendas aprovadas. Uma delas deve tratar de trabalho e
formação profissional; a saída não pode depender apenas de coortes e mobilidade.

### 3.3 Mínimo conjunto

O piloto ampliado precisa conter simultaneamente:

- quatro histórias na primeira direção e três agendas na segunda;
- trajetória/permanência;
- trabalho juvenil ou trabalho e escolaridade;
- EJA ou população adulta sem educação básica concluída;
- trabalho e formação profissional;
- pelo menos duas histórias principais não demográficas;
- camada integrada de Nova Santa Rita;
- distinção entre ação municipal, coordenação estadual e articulação regional;
- nenhuma mensagem pública de ausência, fraqueza, insuficiência ou falha.

Uma candidata pode satisfazer mais de um tema, mas conta em apenas uma direção e
uma vez no total 4+3. A mesma base só sustenta histórias nas duas direções quando
pergunta, interpretação e decisão forem materialmente diferentes.

## 4. Catálogo V7 de candidatas

Os identificadores são estáveis no contrato analítico. A implementação posterior
deve mapeá-los à arquitetura canônica existente.

### 4.1 Primeira direção

| ID | História e pergunta | Base e lente mínimas | Limite da afirmação | Papel |
|---|---|---|---|---|
| `H1_DEMOGRAFIA_REDE` | **Como a mudança das gerações está reorganizando a demanda educacional?** | população residente por idade; matrículas, turmas, escolas e rede; janela comum; contribuição municipal | parcela da mudança associada às coortes e resposta observada da rede; nunca projeção municipal | obrigatória; consolida os três cartões demográficos V6 em um módulo com troca de etapa |
| `H2_TRAJETORIA_PERMANENCIA` | **Onde e em quais redes a trajetória escolar se rompe ou melhora?** | rendimento 2018–2025; TDI 2019–2025; rede e etapa; condições somente no mesmo painel | padrões simultâneos e diferenças municipais; sem atribuir resultados às condições | obrigatória |
| `H3_TRABALHO_JUVENIL_MEDIO` | **Em quais municípios trabalho juvenil e ensino médio entram na mesma agenda?** | RAIS 15–17 e 18–24 em 2019–2025; trajetória do médio; Caged somente após validação | coexistência territorial, setores/ocupações e redes; nunca os mesmos indivíduos | obrigatória |
| `H4_EJA_DISTRIBUICAO` | **A oferta de EJA está distribuída de forma semelhante à população adulta sem a etapa concluída?** | fotografia 2022 por EF/EM; moradores sem conclusão; matrículas nas escolas; rede e EJA integrada | diferenças de distribuição; nunca demanda, cobertura ou probabilidade | obrigatória |
| `H5_FORMACAO_OCUPACOES` | **A formação profissional acompanha as ocupações e setores que mudam?** | EPT; painel ocupacional; cursos/eixos com cobertura comprovada; ponte versionada | composição no recorte coberto; ausência de registro não é ausência de oferta | opcional aqui; não pode repetir `A3` |

As quatro primeiras formam o conjunto-alvo inicial. `H5` só entra se entregar
uma decisão diferente de `A3`.

### 4.2 Segunda direção

| ID | Agenda e pergunta | Base futura admitida | Limite da afirmação | Papel |
|---|---|---|---|---|
| `A1_COORTES_REDE` | **Como municípios em retração, estabilidade e crescimento precisam organizar respostas diferentes da rede?** | séries observadas de população, nascimentos, matrículas, turmas e escolas | pressões observadas e tipos transparentes; sem prever vagas ou abrir/fechar escolas | obrigatória |
| `A2_TRABALHO_PERMANENCIA` | **Que mudanças no trabalho juvenil precisam entrar na coordenação do ensino médio?** | RAIS; Caged completo/validado; aprendizagem; trajetória do médio | setores, ocupações, municípios, redes e indicadores a acompanhar | obrigatória |
| `A3_OCUPACOES_FORMACAO` | **Que mudanças do trabalho colocam questões para a formação profissional?** | tendências ocupacionais/setoriais; EPT; cursos/eixos com cobertura do Vale; cenário apenas se publicado | composição, públicos, oferta e articulação no recorte comprovado | obrigatória e bloqueante para o Gate 11 |
| `A4_MOBILIDADE_COORDENACAO` | **Que decisões educacionais exigem coordenação entre municípios?** | fotografia de deslocamento; fluxos OD somente quando conhecidos | concentração e coordenação no limite da fonte | reserva; sem destino, não nomeia corredor, rota ou receptor |
| `A5_TEMAS_CENARIOS` | **Quais temas educacionais permanecem relevantes em diferentes futuros?** | quatro cenários do Vale sob governança aprovada | temas robustos; nenhum número futuro inventado | inativa pela decisão da seção 8 |

`A1`, `A2` e `A3` formam o conjunto-alvo inicial. Trabalho × formação
continua bloqueado até existir cobertura comprovada dos dez municípios do Vale do
Sinos, distinguindo zero observado de ausência de cobertura. Ingressantes e
concluintes enriquecem, mas não bloqueiam se curso, eixo e matrícula estiverem
completos.

### 4.3 Registro obrigatório por candidata

Antes da narrativa, toda candidata registra:

- ID, direção, pergunta e mecanismo previstos;
- fatos educacionais e territoriais, lente, grão, unidade e período;
- natureza temporal: fotografia, série, tendência ou cenário;
- região, município, RS e comparador canônico;
- distribuição, divergência e contribuição municipal quando recomputável;
- estabilidade temporal e territorial;
- leitura de Nova Santa Rita;
- rede, etapa e público;
- questão de planejamento e tema/meta PNE;
- responsabilidade primária, atores e, se necessária, responsabilidade secundária;
- `demography_only_counterfactual`, `decision_delta` e fatos que os sustentam;
- limite máximo da afirmação, decisão C1–C12 e razão de retenção;
- visual principal e rastreabilidade completa.

## 5. Camada municipal

### 5.1 Bloco “No município selecionado”

Toda história publicada tem bloco dinâmico, derivado dos mesmos fatos regionais,
que responde em até três frases e um visual compacto:

1. direção local igual ou diferente da região;
2. contribuição local, somente se a métrica for aditiva ou recomputável;
3. rede, etapa e público;
4. fator adicional que muda a leitura local;
5. questão e responsabilidade específicas.

Campos lógicos mínimos:

| Campo | Regra |
|---|---|
| `municipality_id` | código IBGE textual de sete dígitos |
| `direction_vs_region` | `mesma_direcao`, `direcao_oposta`, `estavel_local` ou `nao_comparavel` |
| `regional_contribution` | valor e método; ausente não vira zero |
| `network_stage_public` | rede, etapa e público em linguagem pública |
| `local_interpretive_factor` | segundo fato que altera a interpretação |
| `planning_question` | questão concreta |
| `institutional_responsibility` | taxonomia da seção 6 |
| `facts` | fatos, períodos, lentes e fontes |

São proibidos texto municipal manual, join por nome/slug, cluster de pares ad hoc,
atribuição municipal de obrigação estadual e repetição da síntese regional com
mera troca do nome.

### 5.2 Síntese municipal

A síntese mostra **até três** prioridades aprovadas. Nunca completa uma vaga com
texto fraco. No piloto, Nova Santa Rita precisa ter ao menos três candidatas
elegíveis para satisfazer o Gate 11, ainda que a interface permaneça capaz de
mostrar menos para outro município.

A seleção não usa score:

1. considerar somente histórias publicadas e com camada municipal completa;
2. separar por etapa, mecanismo e responsabilidade;
3. escolher primeiro a maior prioridade explícita do diagnóstico PNE/PME com
   evidência municipal atual;
4. escolher a segunda pela divergência ou intensidade local, sem repetir a decisão;
5. escolher a terceira pela contribuição regional ou necessidade de articulação;
6. desempatar por cobertura, atualidade e responsabilidade acionável;
7. registrar critério decisivo e exclusões por redundância.

Cada prioridade mostra fato local, contraste regional, responsabilidade e
indicador de acompanhamento. Comparadores admitidos: município, região, RS e
pares já canônicos no PNE.

### 5.3 Nova Santa Rita

Nova Santa Rita é caso de validação, não exceção codificada. A reconstrução deve
testar, sem assumir o resultado:

- demanda escolar distinta da região;
- trajetória nos anos finais e no ensino médio;
- rede municipal versus estadual;
- mobilidade no limite da fotografia disponível;
- trabalho juvenil;
- distribuição de público e matrícula EJA;
- formação profissional, quando a cobertura estiver fechada.

Uma história não conta para o piloto se seu bloco de Nova Santa Rita não for
reconstruível. O componente deve funcionar para os dez municípios do Vale.

## 6. Responsabilidade institucional

| Valor interno | Rótulo público | Uso |
|---|---|---|
| `acao_direta_rede_municipal` | Ação direta da rede municipal | oferta e condições sob competência municipal |
| `coordenacao_rede_estadual` | Coordenação com a rede estadual | ensino médio ou outra oferta estadual |
| `articulacao_intermunicipal_regional` | Articulação intermunicipal e regional | questão comprovadamente supramunicipal |
| `articulacao_formacao_trabalho` | Articulação entre formação e trabalho | EPT, aprendizagem, setores e ocupações |
| `acompanhamento_sem_atribuicao_direta` | Acompanhamento territorial | tema relevante sem execução direta do ente |

Regras:

1. toda questão tem responsabilidade primária, atores e fatos;
2. admite-se uma secundária apenas quando a coordenação for necessária;
3. a classe deriva de rede, etapa, lente e competência, não do nome do indicador;
4. o rótulo indica capacidade de ação, não culpa;
5. ensino médio estadual não recebe `acao_direta_rede_municipal`;
6. o município pode atuar em transição, transporte e coordenação sem assumir a
   oferta estadual;
7. EPT/trabalho nomeia, quando cabível, Estado, União, instituições privadas e
   Sistema S;
8. “acompanhamento” não pode ocultar rede responsável conhecida;
9. o texto público diz quem precisa coordenar o quê; o enum fica interno.

## 7. Decisão formal — EJA 2022

**Aprovada:** o contraste principal será fotografia de distribuição de 2022,
separada entre ensino fundamental e médio.

```text
participacao_publico_i = publico_residente_sem_conclusao_i / publico_residente_sem_conclusao_regiao
participacao_matriculas_i = matriculas_eja_localizadas_i / matriculas_eja_localizadas_regiao
diferenca_distribuicao_pp = participacao_matriculas_i - participacao_publico_i
matriculas_por_mil = 1000 * matriculas_eja_localizadas_i / publico_residente_sem_conclusao_i
```

As participações e sua diferença sustentam a história. `matriculas_por_mil` é
medida auxiliar, nunca cobertura.

Regras bloqueantes:

- usar faixa etária e nível exatamente como publicados pela fonte;
- não compartilhar denominador entre fundamental e médio;
- denominador zero produz `null`;
- preservar zero, ausência e supressão;
- recomputar a região por somas;
- rotular moradores e matrículas nas escolas;
- “público potencial” é estoque estatístico, não demanda manifesta;
- manter a série de matrícula EJA 2014–2025 como contexto separado;
- não interpolar o estoque adulto entre censos;
- não afirmar alcance, atendimento, probabilidade, dependência intermunicipal ou
  município receptor;
- manter intensidade por mil em plano secundário;
- aprovar a narrativa somente depois do cálculo e julgamento.

## 8. Decisão formal — cenários do Vale do Sinos

**Aprovada a opção metodológica 3:** a V7 do Vale do Sinos operará com mudanças
observadas e tendências sustentadas até existir cenário próprio validado.

- cenários do Vale do Rio Pardo e Noroeste não serão transferidos neste job;
- a segunda direção pode fechar com três agendas históricas, incluindo trabalho ×
  formação;
- nenhum número futuro ou rótulo “cenário/projeção municipal” será publicado;
- coortes já nascidas continuam sendo observação, não previsão;
- exposição municipal não é cenário municipal;
- a ausência de cenário não gera mensagem pública;
- `A5_TEMAS_CENARIOS` permanece inativa;
- a aderência completa ao pedido de cenários depende de aceite da gestora na
  validação humana.

Reabrir a decisão exige método e governança comuns, base/horizonte, quatro futuros
coerentes, forças e incertezas rastreáveis, ligação educacional sem números
inventados, temas robustos e separação regional/municipal.

## 9. Valor incremental além da demografia

Uma candidata não demográfica passa somente se:

1. retirada a demografia, restar leitura sustentada por trajetória, trabalho, EJA,
   formação, oferta ou condições;
2. o segundo domínio mudar ao menos uma dimensão de decisão: público/etapa,
   município/rede, ação/coordenação, indicador ou horizonte;
3. a camada municipal acrescentar divergência, concentração ou contribuição útil;
4. a questão nomear responsabilidade e indicador;
5. nenhuma outra história entregar a mesma decisão;
6. `demography_only_counterfactual`, `decision_delta` e fatos forem
   rastreáveis.

`H1` só passa se resposta da rede, oferta ou mobilidade alterar a questão de
planejamento. Duas séries no mesmo sentido, correlação, gráfico extra, ranking,
heterogeneidade sem consequência e recomendação genérica falham.

## 10. Checks por candidata — C1 a C12

Os identificadores C1–C12 evitam colisão com o Gate 11 macro do piloto. A
implementação posterior deve documentar a migração dos G1–G10 V6.

| Check | Critério |
|---|---|
| C1 | relevância PNE/PME |
| C2 | mecanismo previsto antes do resultado |
| C3 | universos e lentes compatíveis |
| C4 | tempo e natureza temporal coerentes |
| C5 | estabilidade temporal e territorial |
| C6 | integração além de séries isoladas |
| C7 | diferença municipal útil |
| C8 | planejamento com público, etapa, rede, ação e indicador |
| C9 | clareza sem jargão |
| C10 | rastreabilidade total |
| C11 | não redundância |
| C12 | valor incremental além da demografia |

Falha em qualquer check retém a candidata. Quantidade não reduz limiar.

Migração conceitual do baseline:

| V6 | V7 | Observação |
|---|---|---|
| G1 relevância | C1 | preservado |
| G2 mecanismo | C2 | preservado |
| G3 universo | C3 | ampliado para explicitar lentes |
| G4 tempo | C4 | ampliado para fotografia/tendência/cenário |
| G5 estabilidade | C5 | preservado |
| G6 valor além de indicadores isolados | C6 | integração; não substitui C12 |
| G7 questão concreta | C8 | planejamento agora inclui responsabilidade |
| G8 clareza | C9 | preservado |
| G9 não redundância | C11 | preservado e reposicionado |
| G10 rastreabilidade | C10 | preservado |
| sem equivalente próprio | C7 | território municipal útil |
| sem equivalente próprio | C12 | valor além da demografia |

A correspondência é documental. Alterar identificadores, schemas ou decisões
derivadas pertence aos jobs de implementação e requer migração compatível.

## 11. `PILOT_GATE_11_V7` — completude e utilidade

Este é gate de release do produto, não C11. Sua especificação está aprovada; seu
estado permanece **BLOQUEADO**.

Só pode abrir quando todos os itens forem verdadeiros:

- mínimo 4+3 e todos os cartões aprovados em C1–C12;
- trajetória, trabalho juvenil, EJA e trabalho × formação presentes;
- ao menos duas histórias não demográficas;
- segunda saída não limitada a coortes/mobilidade;
- cobertura de trabalho × formação fechada para os dez municípios do Vale;
- cada história com camada municipal;
- Nova Santa Rita integrada e com três prioridades elegíveis;
- responsabilidades municipal, estadual e regional distinguíveis;
- percurso principal não maior que o V6, sem mensagem técnica ou genérica;
- testes, fallback e rollback aprovados;
- validação humana, sem explicação prévia, comprova que a pessoa identifica:
  desafio além da demografia, diferença de Nova Santa Rita, trabalho × ensino
  médio, distribuição EJA, trabalho × formação, responsabilidades e três temas
  prioritários.

O registro humano contém respostas, tempo, dúvidas, termos não compreendidos,
informação útil/ignorada, decisão sugerida e ajustes.

## 12. Contrato de linguagem pública V7

### 12.1 Funções de cada frase

Cada frase pública deve declarar mudança, mostrar distribuição, acrescentar
interpretação, localizar público/rede, formular decisão específica ou indicar
responsabilidade. Frase sem uma dessas funções é removida.

Rótulos de lente:

- **Moradores do município**;
- **Matrículas nas escolas do município**;
- **Vínculos nos estabelecimentos do município**;
- **Rede responsável pela oferta**.

### 12.2 Formas aprovadas e reprovadas

Os exemplos usam marcadores entre colchetes; não são texto publicável nem
autorizam números fictícios.

| Tema | Forma aprovada | Forma reprovada | Motivo |
|---|---|---|---|
| Demografia e rede | “Enquanto a população de [faixa] mudou [direção], matrículas e turmas de [etapa] responderam de modo diferente entre os municípios.” | “A demografia explica a educação da região.” | causalidade e apagamento da rede |
| Trajetória | “A reprovação e a distorção se concentraram em [rede/etapa/municípios] no período [janela], colocando [indicadores] na coordenação com [ator].” | “A infraestrutura ruim causou o baixo desempenho.” | causa não demonstrada |
| Trabalho juvenil | “Trabalho juvenil e dificuldades de trajetória do ensino médio se concentram nos mesmos municípios; [redes/atores] precisam acompanhar [indicadores] em conjunto.” | “Os alunos abandonam a escola para trabalhar.” | identifica pessoas e causa |
| EJA 2022 | “Em 2022, a participação de [município] entre os moradores sem [etapa] concluída diferia de sua participação nas matrículas de EJA da região.” | “A EJA atende [x]% da demanda municipal.” | fotografia entre lentes não mede demanda/cobertura |
| Trabalho e formação | “As ocupações de [famílias] ganharam espaço em [período], enquanto a formação disponível se concentrou em [eixos/municípios]; a agenda envolve [atores].” | “Faltam cursos para as profissões do futuro.” | cobertura, futuro e insuficiência não demonstrados |
| Município | “Em [município], [fato local] seguiu direção diferente da região; a questão envolve [rede/etapa] e [responsabilidade].” | “[Município] é o pior da região e precisa agir.” | ranking, julgamento e atribuição vaga |
| Responsabilidade | “No ensino médio, o acompanhamento municipal precisa ser coordenado com a rede estadual em torno de [indicadores].” | “A prefeitura deve resolver a reprovação do ensino médio.” | competência institucional incorreta |
| Cenários | “A mudança observada em [período] coloca [tema] na agenda dos próximos anos.” | “O cenário do Vale prevê [número futuro].” | cenário do Vale inexistente |
| Mobilidade | “A parcela de moradores que estudava fora reforça a necessidade de coordenação regional.” | “Os estudantes se deslocam para [município receptor].” | a fonte atual não informa destino |

### 12.3 Proibições adicionais

Além do vocabulário V6, a camada pública não pode:

- dizer “pode estar relacionado” como substituto de interpretação;
- usar “fortalecer políticas”, “aprofundar análise” ou “acompanhar dados” sem
  sujeito, etapa, fenômeno e indicador;
- chamar fotografia de tendência;
- misturar estoque RAIS e fluxo Caged;
- comparar 2026 parcial do Caged com ano completo;
- chamar exposição de cenário municipal;
- dizer “primeiro emprego” sem dicionário oficial;
- tratar ausência de curso como oferta zero;
- usar CAPES como EPT;
- mostrar enum, check, score, retenção ou limitação técnica no percurso principal.

### 12.4 Aprovação dos exemplos

As formas aprovadas autorizam somente a estrutura semântica. No Job 6, exemplos
que passarem pelos Jobs 2–4 devem migrar para o corpus canônico
`scripts/checks/fixtures/vocacoes-pne/exemplos-cartoes.json` e para o
vocabulário/linter existente. Até lá, fixtures e código permanecem inalterados.

## 13. Aceite e pendências

Aprovados no Job 1:

- arquitetura 4+3 e catálogo de candidatas;
- consolidação demográfica;
- camada municipal;
- fotografia EJA 2022;
- opção sem cenários do Vale por enquanto;
- taxonomia institucional;
- C1–C12, valor incremental e especificação do Gate 11;
- formas editoriais estruturais.

Permanecem pendentes:

- cálculos, fatos e narrativas das novas histórias;
- cobertura trabalho × formação;
- blocos completos de Nova Santa Rita;
- aceitação humana da decisão sobre cenários;
- teste humano e aprovação efetiva do Gate 11;
- qualquer mudança em dados, código, fixtures ou interface.

---

# Anexo A — baseline operacional V6

O conteúdo abaixo é preservado integralmente como contrato da implementação V6,
referência de regressão e rollback. Em conflito com as seções 1–13 para o desenho
da V7, prevalecem as seções 1–13. Até a promoção da V7, os schemas, números,
mínimos, geradores e gates deste anexo continuam governando a página publicada.

## 1. As duas saídas

A página existe para responder duas perguntas da gestão, e somente elas:

| Direção | Pergunta da gestão | Conteúdo |
|---|---|---|
| `educacao_para_territorio` | O que o território ajuda a compreender sobre a educação? | **Leituras integradas**: partem de um resultado educacional, separam seus componentes e usam o território para interpretá-lo. |
| `territorio_para_educacao` | O que o futuro do território coloca na agenda da educação? | **Questões de agenda**: partem de uma transformação territorial e chegam a uma implicação concreta para o planejamento educacional. |

A comparação temporal e a heterogeneidade municipal são **incorporadas** a cada cartão das duas direções — nunca uma terceira seção.

### 1.1 Limites e mínimos

| Regra | Valor |
|---|---|
| Leituras publicadas (`educacao_para_territorio`) | mínimo 3, máximo 5 |
| Questões publicadas (`territorio_para_educacao`) | mínimo 2, máximo 5 |
| Página publicável para uma região | somente com os dois mínimos atingidos |
| Região abaixo do mínimo | permanece na rota anterior, **sem mensagem pública de ausência** |

### 1.2 Regra de publicação de um cartão

Um conteúdo só vira cartão quando o insight:

1. combina educação e território;
2. responde a uma das duas perguntas da gestão;
3. é sustentado por dados rastreáveis;
4. altera ou qualifica uma questão de planejamento;
5. é explicável em linguagem pública, sem jargão metodológico;
6. não repete outra leitura já publicada.

Falhou em qualquer item: o cartão **não existe** — nem como aviso, nem como espaço vazio rotulado.

---

## 2. Tipologia do conteúdo

Cinco categorias, com alcance distinto. Todo texto público pertence a uma delas e não pode reivindicar o alcance de outra.

| Categoria | O que é | Exemplo de forma |
|---|---|---|
| **Fato observado** | Número ou variação medida em fonte identificada, período fechado. | "Entre 2014 e 2025, as matrículas no ensino médio passaram de 31.789 para 26.911." |
| **Leitura integrada** | Combinação de dois ou mais fatos compatíveis que interpreta um resultado, sem afirmar causa. | "A redução da população jovem foi maior do que a queda das matrículas; a relação entre matrículas e população da idade aumentou." |
| **Questão de planejamento** | Consequência prática da leitura: nomeia o público **ou** a etapa, o fenômeno e o indicador; o recorte territorial ou temporal entra quando cabível (plano §3.7). Na segunda saída, o afetado pode ser grupo, etapa **ou** território (plano Etapa 7.3). | "O ajuste da oferta precisa ocorrer junto com ações de permanência, sobretudo onde reprovação e abandono se concentram." |
| **Tendência futura** | Extensão de uma mudança sustentada por série observada, projeção adequada ou estudo setorial aprovado (plano Etapa 7.1); sem número futuro fora de cenário; base declarada em `future_basis`. | "As coortes que chegarão ao ensino médio nos próximos anos já nasceram e são menores." |
| **Cenário** | Caminho possível vindo da metodologia de cenários publicada; sempre plural, nunca previsão. | "Em diferentes futuros considerados, a qualificação de adultos permanece na agenda." |

Regras de fronteira:

- fato nunca é apresentado como leitura ("a matrícula caiu" não é insight);
- leitura nunca afirma causa nem oferece explicação não sustentada. Verbos como **acompanhar, ajudar a compreender, interpretar, conviver com, indicar** são exemplos seguros — a regra é o alcance, não uma lista fechada: proibido atribuir uma mudança à outra (**causar, provocar, determinar, levar a, ser responsável por**);
- tendência futura exige base rastreável (`future_basis`); número futuro só dentro de cenário publicado (invariante herdada, V6-D5);
- cenário nunca substitui dado observado; enriquece a segunda saída onde existir (no piloto Vale do Sinos **não há cenários** — V6-D3 — e a segunda saída se apoia em mudanças observadas e tendências sustentadas).

---

## 3. Anatomia dos cartões

### 3.1 Cartão da primeira saída (`educacao_para_territorio`)

Blocos públicos, nesta ordem:

1. **Título com a principal leitura** — uma frase completa que já entrega o insight; nunca o nome de um indicador ou de um par de variáveis.
2. **O que mudou na educação** — fatos educacionais com valores, período e variação.
3. **O que o território ajuda a compreender** — a leitura integrada com os fatos territoriais.
4. **Como isso aparece entre os municípios** — contribuição municipal, direções divergentes, concentração.
5. **O que entra no planejamento** — a questão de planejamento.
6. **Indicadores e fontes** — em detalhe recolhido ("Ver dados e fontes").

Schema lógico (campos públicos + camada interna, plano §6.1):

```yaml
id:                       # estável, kebab-case
direction: educacao_para_territorio
title:                    # string, a leitura principal
education_question:       # a pergunta educacional de origem (catálogo §5 do plano)
education_facts: []       # fatos observados, quantitativos ou qualitativos; cada um reconstruível
                          # com período e fonte (no cartão via period/sources; internamente via
                          # fatos estruturados — ver §3.4); valor numérico obrigatório apenas
                          # quando a afirmação for quantitativa
territorial_facts: []     # fatos territoriais compatíveis
integrated_reading:       # a leitura integrada (texto público central)
municipal_pattern:        # como varia entre municípios
planning_question:        # questão concreta: etapa+público+fenômeno+recorte+indicador
pne_topics: []            # temas/metas do PNE relacionados
monitoring_indicators: [] # o que acompanhar
period:                   # janela da leitura (ex.: "2014–2025")
sources: []               # fontes nomeadas
internal:                 # NUNCA chega ao documento público
  mechanism_id:           # mecanismo do catálogo (M1–M7)
  universe_check:         # ok | incompativel
  temporal_check:         # ok | incoerente
  sensitivity_check:      # ok | instavel
  territorial_check:      # ok | concentrado
  publication_decision:   # publicada | retida; derivada de gates
  gates:                  # G1–G10: status, reasonCode e evidenceFactIds
  fact_references:        # cada trecho público → ids dos fatos que o sustentam
  planning_components:    # etapa, público, fenômeno, recorte e indicadores
  visualization_ids:      # visuais aprovados para a leitura
  research_candidate_id:  # vínculo estável com o artefato de pesquisa
```

### 3.2 Cartão da segunda saída (`territorio_para_educacao`)

Blocos públicos, nesta ordem:

1. **Transformação do território** (título com a transformação e sua consequência educacional)
2. **O que já está mudando** — fatos territoriais observados.
3. **Ponto de partida da educação** — situação educacional atual relacionada.
4. **O que essa mudança coloca na agenda** — a questão de agenda.
5. **Municípios ou públicos mais expostos**
6. **Indicadores para acompanhar**
7. **Metas e temas relacionados** (PNE)

Schema lógico (plano §6.2):

```yaml
id:
direction: territorio_para_educacao
title:
territorial_transformation:        # a transformação em curso, nomeada
territorial_facts: []
education_starting_point:          # ponto de partida educacional
exposed_groups_or_municipalities:  # quem é mais afetado
education_agenda:                  # o que entra na agenda (texto público central)
pne_topics: []
monitoring_indicators: []
horizon:                           # "próximos anos" / janela do cenário; nunca ano+número futuro fora de cenário
sources: []
internal:
  transformation_class:  # mudanca_observada | tendencia_sustentada | estudo_setorial | cenario
  mechanism_id:
  future_basis:
    basisType:           # observed_series | observed_snapshot | sector_study | scenario
    seriesIds: []        # séries que sustentam a classificação
    observedPeriod:      # { start, end }; período fechado e observado
    supportsTrend:       # fotografia observada = false
    scenarioId:          # null fora de cenário; id obrigatório dentro de cenário
    futureNumericValues: # [] fora de cenário
    claimBoundary:       # limite textual do que a base permite afirmar
  sensitivity_check:     # ok | instavel
  publication_decision:  # publicada | retida; derivada de gates
  gates:                 # G1–G10: status, reasonCode e evidenceFactIds
  fact_references:       # cada trecho público → ids dos fatos que o sustentam
  planning_components:   # grupo/etapa, fenômeno, recorte e indicadores
  transformation_map:    # transformação → séries territoriais, educação e afetados
  visualization_ids:     # visuais aprovados para a agenda
  research_candidate_id: # vínculo estável com o artefato de pesquisa
```

Fora de cenário, `scenarioId` é obrigatoriamente `null` e
`futureNumericValues` é obrigatoriamente `[]`. `observed_snapshot` nunca
sustenta tendência. No piloto Vale do Sinos, somente `observed_series` e
`observed_snapshot` são aceitos: a Rodada 6 não usa cenário, projeção ou número
futuro.

Rótulo público da classe (único vocabulário permitido para o futuro):

| `transformation_class` | Rótulo público |
|---|---|
| `mudanca_observada` | **Mudança já em curso** |
| `tendencia_sustentada` | **Tendência para os próximos anos** |
| `estudo_setorial` | **Tendência para os próximos anos** |
| `cenario` | **Tema presente nos cenários** |

O rótulo público é **derivado** pelo compilador (Rodada 7) a partir de
`transformation_class` — campo público `future_label`, preenchido antes da
remoção de `internal` e validado contra esta tabela. Nenhum texto autoral
digita o rótulo.

### 3.3 Regras estruturais

- Campo público vazio = cartão inválido (fail-closed no gerador; nenhum bloco renderiza vazio). **Vazio** = string em branco após trim, array `[]`, ou array contendo apenas strings em branco. Itens de `pne_topics`, `monitoring_indicators` e `sources` são strings não vazias e únicas e, desde a Rodada 2, resolvem por label exato contra `catalogo-referencias.json` (item em branco, desconhecido ou duplicado = violação individual). O `internal.mechanism_id` resolve contra `catalogo-mecanismos.json`, e a direção do cartão deve estar entre as direções permitidas do mecanismo.
- A serialização pública **constrói um objeto novo por allowlist** dos campos públicos da direção — não apenas remove `internal`. Campo desconhecido no autoral não passa; nenhuma chave interna (`mechanism_id`, checks, `publication_decision`, `transformation_class`, `future_basis`) pode existir no resultado. O teste de contrato verifica.
- `publication_decision: publicada` exige todos os checks internos `ok` e, na segunda saída, `future_basis` estruturalmente válida. Qualquer check reprovado força `retida`. Cartão `retida` não aparece e não gera mensagem. Nas duas saídas, a decisão é **derivada** do registro de gates G1–G10, nunca digitada; G8 muda de `pendente_autoria` para `ok` somente depois do linter e da revisão editorial.
- Uma mesma história não é dividida em vários cartões de pares; um cartão carrega a história inteira.

### 3.4 Camada interna estruturada e evolução prevista

Os motores das Rodadas 5 e 6 fecharam as lacunas estruturais originalmente
apontadas pela revisão adversarial da R1 para as duas direções. A unificação no
compilador público permanece restrita à Rodada 7:

| Compromisso | Situação |
|---|---|
| Fato estruturado com id, série/indicador, valor+unidade, janela e `sourceId`; cada trecho narrativo referencia os fatos que o sustentam | **Entregue na R5 e na R6** para as duas saídas |
| Registro interno dos gates G1–G10 por cartão; `publication_decision` derivada | **Entregue na R5 e na R6** |
| Componentes estruturados da questão de planejamento (público/etapa, fenômeno, recorte, indicador) validados estruturalmente | **Entregue na R5 e na R6** |
| `future_basis` estruturada por tipo, séries, janela observada, limite da afirmação, `scenarioId` e valores futuros | **Entregue na R6**; piloto restrito a bases observadas |
| Schema autoral e projeção pública com `additionalProperties: false` nos dois lados | **Entregue na R7** pelo compilador e pelo parser de runtime |

Os artefatos de pesquisa das R5–R6 usam fatos com `id`, `kind`, `seriesId`,
`unit`, `period`, `values` e `sourceId`. A autoria não recebe liberdade para
alterar esses valores: referencia seus ids por campo narrativo. Cada gerador
valida o hash do artefato importado, recompõe a decisão dos dez gates e constrói
a projeção pública por allowlist. As candidatas retidas guardam apenas
identificador, gate reprovado e `reasonCode`; fatos, visualizações e texto
público permanecem ausentes.

O compilador da Rodada 7 recompõe os artefatos R5/R6 pelos respectivos
`buildExpectedOutput()`, exige identidade byte a byte dos resultados integrados,
valida os hashes congelados, a identidade regional e G1–G10, e só então indexa
fatos e visualizações das cinco candidatas publicadas. A projeção usa o schema
`vocacoes-pne-narrative-pilot-v1`, versão de contrato `1.5.0`, com raiz fechada:
`schemaVersion`, `contractVersion`, `region`, `page`, `highlights`, `sections`,
`consultation` e `generation`.

As duas seções carregam respectivamente três e dois cartões. Cada cartão parte
byte a byte da allowlist pública R5/R6 e recebe somente o rótulo futuro derivado
quando cabível, um `primary_visual` e uma `municipal_distribution`. Os templates
visuais fechados são `aligned_series` e `category_bars`; seus números são
copiados dos fatos e visuais aprovados, sem recálculo metodológico ou
arredondamento. A distribuição pública usa nome municipal e valor; o registro
interno conserva o código IBGE textual de sete dígitos e a rastreabilidade por
fato, visual e fonte.

O linter percorre recursivamente todo o documento público — moldura, navegação,
rótulos, gráficos, detalhes, fontes e texto alternativo. O parser de runtime
aplica campos exatos em todos os níveis. Chaves internas, candidatas retidas,
`reasonCode`, ids de fatos ou mecanismos e paths da pesquisa são recusados. O
gerador grava os dois outputs de forma transacional, preserva bytes idênticos e
oferece `--check` sem escrita para o gate de CI.

---

## 4. Requisito da gestora → bloco da página

| Requisito (plano §2.1) | Campo/bloco |
|---|---|
| o que mudou | `education_facts` / `territorial_facts` + bloco 2 |
| qual parte da mudança acompanha demografia, trajetória, oferta | `integrated_reading` (decomposição traduzida) |
| características do território que ajudam a interpretar | `territorial_facts` + `integrated_reading` |
| variação entre municípios | `municipal_pattern` / `exposed_groups_or_municipalities` |
| questão concreta de planejamento | `planning_question` / `education_agenda` |
| transformação em curso | `territorial_transformation` + bloco 2 |
| ponto de partida educacional | `education_starting_point` |
| temas e metas do PNE | `pne_topics` |
| indicadores a acompanhar | `monitoring_indicators` |
| comparação temporal | `period`/`horizon` + fatos com janelas; incorporada, não seção |
| fontes | `sources` (detalhe recolhido) |

---

## 5. O que nunca aparece ao usuário

Nenhum destes, em nenhum campo público (a lista operacional, com padrões, vive em `vocabulario.json`):

1. **Método estatístico**: correlação, Pearson, Spearman, significância, p-valor, coeficientes.
2. **Força e grau**: relação fraca/moderada/forte, escada E1–E5, grau de evidência (V6-D2).
3. **Maquinaria interna**: triagem (automática), lead, note, decomposição Bennett, shift-share, efeito demográfico, efeito taxa, taxa de atendimento aparente, universo incompatível, fail-closed, gates/checks internos, hipótese. *Nota: o plano (§9.2) veda "hipótese a verificar"; este contrato amplia deliberadamente para qualquer uso de "hipótese" na camada pública — decisão editorial da R1, registrada aqui.*
4. **Mensagens negativas** (§3.6 do plano): "não foi possível medir", "relação fraca", "dados insuficientes", "cenário ausente"/"não há cenários", "hipótese a verificar", "não se pode concluir", "a plataforma não possui dados". **Ausência é silêncio**, nunca conteúdo.
5. **Recomendações genéricas** (§3.7): "aprofundar a análise", "acompanhar os dados", "realizar ações", "investigar as causas" sem sujeito, etapa, fenômeno e indicador.
6. **Causalidade**: causou/provocou/acarretou/determinou/é responsável por/por causa de. A proteção contra conclusão indevida é a redação, não o aviso.
7. **Listas técnicas**: relações descartadas, classificações da triagem, detalhes de método como conteúdo de primeiro nível.

Traduções obrigatórias (interno → público, plano §9.3):

| Interno | Público |
|---|---|
| efeito demográfico | parte da mudança ligada ao tamanho da população |
| taxa de atendimento aparente | matrículas em relação à população da idade |
| defasagem de seis anos | seis anos depois |
| correlação das variações | mudanças ocorridas no mesmo período |
| contribuição municipal | participação de cada município na mudança regional |
| público elegível da EJA | adultos que ainda não concluíram essa etapa |
| shift-share | componentes da mudança do emprego |
| cenário invariante | questão que permanece importante em diferentes futuros |

---

## 6. Texto de enquadramento da página

Texto fixo, único aviso metodológico da página (adotado do plano, Etapa 1.8):

> Esta página reúne mudanças da educação e do território ao longo do tempo. Os dados são apresentados em conjunto quando ajudam a interpretar uma mesma questão de planejamento. A leitura não atribui automaticamente uma mudança à outra.

---

## 7. Guia editorial

### 7.1 Título

- Frase completa com a leitura principal ("A queda das matrículas no ensino médio acompanha principalmente a redução da população jovem"), nunca rótulo de par ("Matrículas × população 15–17").
- O título deve continuar verdadeiro se lido sozinho, sem o corpo do cartão.
- O título descreve o mesmo período e a mesma métrica que o corpo (problema P4 da auditoria: título de pontas com métrica de variações anuais é proibido).

### 7.2 Números

- Todo número público tem período e fonte reconstruíveis (fato estruturado por trás).
- Arredondamento só na exibição; valores absolutos com separador de milhar; variações com sinal e uma casa decimal.
- Sem número futuro fora de cenário publicado (V6-D5).
- Taxas acima de 100 não recebem nota técnica no cartão principal: a redação usa a forma "para cada 100 pessoas na idade, há X matrículas, o que inclui alunos de outras idades ou de outros municípios" apenas quando a leitura precisar do valor; caso contrário, o valor fica na camada de consulta.

### 7.3 Tempo

Traduzir sempre a relação temporal: "no mesmo período", "seis anos depois", "desde o início da série", "a mudança começou antes", "a diferença se concentrou nos anos X–Y". Nunca o termo técnico.

### 7.4 Municípios

- Toda leitura regional informa como se distribui: quem mais contribuiu, quem foi na direção contrária, se a mudança está concentrada.
- Leitura que depende quase exclusivamente de um município não é publicada como característica da região (check interno `territorial_check`).

### 7.5 Estratégia de redação (plano §9.5)

Redigir apenas o que os dados permitem; o limite aparece na escolha das frases, não em avisos.

- Evitar: "A relação entre emprego formal e matrícula do ensino médio é moderada e não permite concluir causalidade."
- Preferir: "Enquanto o emprego formal cresceu, a matrícula do ensino médio diminuiu. A queda da população de 15 a 17 anos foi ainda maior, indicando que a mudança demográfica é central para interpretar esse resultado."

### 7.6 Teste de valor (bloqueante, plano §9.6)

Antes de publicar qualquer cartão:

1. O usuário aprende algo que não obteria olhando um único indicador?
2. Há ao menos um fato educacional e um territorial combinados?
3. Existe questão de planejamento específica?
4. O texto se sustenta sem método estatístico?
5. Cada frase tem números e fontes por trás?
6. O conteúdo difere dos demais cartões?

Uma resposta negativa bloqueia a publicação.

---

## 8. Gates de publicação (plano §7)

G1 relevância PNE · G2 mecanismo catalogado · G3 universo compatível · G4 tempo coerente · G5 estabilidade (janela/município dominante) · G6 valor além dos indicadores isolados · G7 questão de planejamento concreta · G8 clareza sem jargão · G9 não redundância · G10 rastreabilidade total.

Falha em qualquer gate = cartão não publicado, sem mensagem. G2/G3 são verificáveis por máquina desde a Rodada 2: o catálogo de mecanismos (M1–M7, default-deny — nenhum par fora de `paresPermitidos`/`paresProvisorios` alimenta cartão) e o registro canônico de séries (universo, lente territorial, faixa etária, denominadores) sustentam `validatePair` e `validateCardCatalog`, que bloqueiam os erros conhecidos do piloto (população 0–14 × ensino médio, cadastro social como denominador de EJA, vínculos totais como trabalho juvenil, lente mista não declarada, fotografia censitária como série anual).

Desde a Rodada 5, a primeira saída também verifica por máquina G4, G5, G8 e G10. A Rodada 6 aplica os mesmos gates à segunda saída e acrescenta suas invariantes próprias: série observada com quatro janelas para sustentar tendência; fotografia censitária de 2022 mantida como fotografia preliminar, nunca tendência; universos total, fundamental e médio sem mistura de denominadores; residual censitário preservado dentro da tolerância; reconciliação municipal, concentração máxima de 50%, direção mínima de 60% quando aplicável e retirada de cada município; comparação com RS recomposta na mesma medida; questão concreta com grupo/etapa, fenômeno, recorte e indicadores; três ou mais visuais por cartão; fatos, fontes e autoria ligados por referências e handshake SHA-256. A decisão final só é `publicada` quando G1–G10 estão `ok`.

---

## 9. Verificação por máquina

| Artefato | Papel |
|---|---|
| `scripts/checks/fixtures/vocacoes-pne/vocabulario.json` | Fonte canônica das regras de linguagem (termos, frases, padrões, rótulos permitidos). Versionado; muda só por decisão de gate. |
| `scripts/checks/fixtures/vocacoes-pne/exemplos-cartoes.json` | Exemplos aprovados (0 violações) e reprovados (violações esperadas nomeadas). Corpus dos testes; os números dos aprovados são ilustrativos (do plano) e serão recalculados na Etapa 6 antes de qualquer publicação. |
| `scripts/lib/vocacoes-pne-linter.mjs` | Linter: aplica o vocabulário a todos os campos públicos de um cartão; valida estrutura, decisão de publicação e serialização pública. |
| `scripts/checks/vocacoes-pne-linguagem.test.mjs` | Linter × corpus + injeção sintética de cada regra. |
| `scripts/checks/vocacoes-pne-contrato.test.mjs` | Schema, mínimos/máximos, coerência de `publication_decision`, remoção de `internal`. |
| `scripts/checks/fixtures/vocacoes-pne/catalogo-mecanismos.json` | Catálogo versionado M1–M7 (Etapa 2): pergunta, justificativa, universo de referência, pares permitidos/provisórios, leitura pública máxima, afirmações proibidas, disponibilidade. Substância muda só por decisão de gate. |
| `scripts/checks/fixtures/vocacoes-pne/registro-series.json` | Registro canônico das séries (Etapa 3), GERADO por `scripts/generate-vocacoes-pne-registro.mjs` (`--check` byte a byte): universo, lente territorial, faixa etária, `ratioOf`, status (`disponivel_plataforma` / `disponivel_pesquisa` / `pendente_*`). |
| `scripts/checks/fixtures/vocacoes-pne/regras-universo.json` | Taxonomia de universos e lentes, classificação por padrão, dicionário de denominadores (adequados e proibidos) e ordem das regras de par com `reasonCode`. |
| `scripts/checks/fixtures/vocacoes-pne/catalogo-referencias.json` | Catálogos de temas do PNE, indicadores de acompanhamento e fontes; itens dos cartões resolvem por label exato. |
| `scripts/lib/vocacoes-pne-registro.mjs` | Loaders fail-closed + referências cruzadas (mecanismos × registro × referências). |
| `scripts/lib/vocacoes-pne-compatibilidade.mjs` | `validatePair` (default-deny + regras de universo, janela e lente) e `validateCardCatalog` (mecanismo, direção, itens de catálogo). |
| `scripts/checks/vocacoes-pne-mecanismos.test.mjs` | Catálogo × corpus × triagem do pacote (default-deny). |
| `scripts/checks/vocacoes-pne-series.test.mjs` | Registro × pacote publicado + bloqueio nomeado dos erros conhecidos. |
| `scripts/export-vocacoes-pne-r5-insumo.mjs` | Exportador controlado e determinístico das matrículas municipais de 2015/2025 para a pesquisa; valida identidade, schema, estado dos valores e proveniência sem editar `public/data`. |
| `scripts/checks/fixtures/vocacoes-pne/primeira-saida-pesquisa-vale-do-sinos.json` | Cópia byte a byte do resultado do motor de pesquisa; seis candidatas, fatos, fontes, gates técnicos e visualizações. |
| `scripts/checks/fixtures/vocacoes-pne/primeira-saida-autoria.json` | Texto público autoral da primeira saída e referências obrigatórias de cada trecho aos fatos aprovados. |
| `scripts/lib/vocacoes-pne-primeira-saida.mjs` | Validação fail-closed dos fatos, pares, decomposição, janelas, heterogeneidade municipal, G1–G10, autoria e projeção pública. |
| `scripts/generate-vocacoes-pne-primeira-saida.mjs` | Gerador determinístico e atômico da primeira saída; `--check` prova identidade byte a byte e `--research-source` prova o handshake com a pesquisa. |
| `scripts/checks/fixtures/vocacoes-pne/primeira-saida-vale-do-sinos.json` | Artefato integrado da R5: três cartões publicáveis, três retenções silenciosas, vínculo por hash e projeção pública por allowlist. |
| `scripts/checks/vocacoes-pne-primeira-saida.test.mjs` | Recomputa números, gates e limiares; testa rastreabilidade, determinismo, identidade textual, visuais e adulterações adversariais. |
| `scripts/checks/fixtures/vocacoes-pne/segunda-saida-pesquisa-vale-do-sinos.json` | Cópia byte a byte do resultado do motor da R6: registro de cinco transformações, mapa transformação × educação, fatos, bases futuras observadas, gates técnicos e sete visualizações. |
| `scripts/checks/fixtures/vocacoes-pne/segunda-saida-autoria.json` | Duas questões de agenda autorais e referências obrigatórias de cada trecho aos fatos aprovados. |
| `scripts/lib/vocacoes-pne-segunda-saida.mjs` | Validação fail-closed de base futura, pares, coortes, mobilidade, universos censitários, heterogeneidade municipal, G1–G10, autoria e projeção pública. |
| `scripts/generate-vocacoes-pne-segunda-saida.mjs` | Importador e gerador determinístico e atômico da R6; `--check` prova identidade byte a byte e `--research-source` prova o handshake com a pesquisa. |
| `scripts/checks/fixtures/vocacoes-pne/segunda-saida-vale-do-sinos.json` | Artefato integrado da R6: duas agendas publicáveis, três retenções silenciosas, vínculo por hash e projeção pública por allowlist. |
| `scripts/checks/vocacoes-pne-segunda-saida.test.mjs` | Recomputa coortes, mobilidade, universos, gates e limiares; testa V6-D3, rastreabilidade, determinismo e adulterações adversariais. |
| `scripts/lib/vocacoes-pne-compilador.mjs` | Compilador R7 em três camadas: valida/recompõe os insumos congelados, aplica autoria e linter, constrói as allowlists pública e interna. |
| `scripts/generate-vocacoes-pne-compilador.mjs` | Gerador transacional e determinístico dos dois outputs R7; `--check` compara todos os bytes sem escrever. |
| `src/features/vocacoes-regiao/generated/vocacoesPneValeDoSinos.json` | Projeção pública fechada do piloto Vale do Sinos, schema `vocacoes-pne-narrative-pilot-v1`. |
| `scripts/checks/fixtures/vocacoes-pne/compilador-registro-vale-do-sinos.json` | Registro interno de hashes e rastreabilidade texto → fatos, visuais, fontes e municípios por código IBGE. |
| `src/features/vocacoes-regiao/vocacoesPneNarrativeContract.js` | Parser fail-closed da projeção narrativa, com campos exatos em todos os níveis. |
| `src/features/vocacoes-regiao/vocacoesPneNarrativeTypes.ts` | Tipos TypeScript espelhados do documento validado em runtime. |
| `scripts/checks/vocacoes-pne-compilador.test.mjs` | Determinismo, hashes, mínimos, linter bilateral, rastreabilidade e adulterações adversariais do compilador. |

O linter é **necessário, não suficiente**: ele captura vocabulário e estrutura. Nas duas saídas, valor, mecanismo, universo, estabilidade e rastreabilidade também são validações de máquina; o julgamento editorial permanece responsável pela clareza e utilidade concreta da leitura.
