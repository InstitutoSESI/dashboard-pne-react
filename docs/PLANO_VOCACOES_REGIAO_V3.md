# Plano — Vocações da Região V3: relações explícitas (pedido da gestão)

Data: 2026-08-26
Origem: pedido direto da gestão (2026-08-26) por **relações explícitas** entre os dados
educacionais (PNE) e os dados territoriais (Vocações), em dois sentidos, com camada
temporal — somado ao diagnóstico do mantenedor de que a plataforma hoje "apresenta os
dados e declara que não tem como trazer relação", o que não faz sentido para o usuário.
Este plano **sucede o V2** (`docs/PLANO_VOCACOES_REGIAO_V2.md`): as Rodadas 0–4 do V2
estão fechadas CONFORME, a R5 está construída e pendente de encerramento (absorvida na
R0 daqui), e as R6–R7 do V2 são absorvidas e redesenhadas nas R3–R4 daqui.
Status: **aprovado para execução** (protocolo v4, §4).

---

## 1. O pedido da gestão (referência de todas as rodadas)

Duas saídas construídas a partir do cruzamento dos dados educacionais com os territoriais:

1. **Saída 1 — O que o território ajuda a explicar sobre a educação?** (PNE → Vocações)
   Parte de um resultado educacional (queda de matrículas no EM, distorção idade-série,
   baixa conclusão, redução da população em idade escolar, permanência) e busca no
   Vocações variáveis que ajudem a compreendê-lo (evolução populacional, migração de
   jovens, renda, emprego formal, setores predominantes, expansão/retração, perfil
   etário, mercado de trabalho). **Regra de ouro da própria gestão:** a plataforma não
   afirma que uma variável causou a outra — aponta **fatores associados e hipóteses
   explicativas, mostrando os dados que sustentam essa leitura**.
2. **Saída 2 — O que o futuro do território exige da educação?** (Vocações → PNE)
   Parte das tendências do território (setores que crescem/retraem, mudanças
   demográficas, novas ocupações, transformação tecnológica, perfil de emprego e renda,
   cenários futuros) e pergunta quais questões educacionais precisam entrar na agenda de
   planejamento — escolaridade, EM, EJA, educação profissional, aprendizagem,
   abandono/permanência, metas e estratégias do PNE.
3. **Camada temporal** dentro das duas saídas: com ~20 anos de dado, mostrar se
   determinadas transformações **ocorreram simultaneamente** (demografia × matrículas;
   emprego/renda × permanência; setores × trajetórias formativas).

## 2. Diagnóstico: o que está construído × o que falta

| Camada | Estado (contrato 2.5.0 no working tree, 2026-08-26) | O que falta |
|---|---|---|
| Saída 1 | Associações **curadas por região** (R3 do V2: seleção determinística, 14 candidatas), com interpretação permitida/proibida e conclusões observadas (V2-D8). | **A leitura é rasa e a moldura é invertida**: o texto só afirma "coexistência na mesma janela" e a página dá à negação ("o que não se conclui") o mesmo peso da leitura. O usuário sai achando que a plataforma se recusa a relacionar. |
| Saída 2 | Cenários em 2/10 regiões; **ponte com o PNE construída na R4 do V2** (bloco territorial na matriz municipal + temas de agenda, contrato 2.3.0); camada municipal construída na R5 (2.4.0), pendente de encerramento. | Cenários ausentes em **8 regiões**; encerramento da R5; legibilidade da agenda. |
| Temporal | Pares temporais por região com séries longas (RAIS 2006+, SINASC 1994+, PIB 2002+), janelas idênticas. | **Nenhuma quantificação do co-movimento**: os pares citam pontas, não dizem como as séries se moveram juntas. |
| Consolidação | **Nada do V2 R1–R5 está commitado** — contrato 2.2.0→2.5.0, remoção do foresight municipal, ponte, camada municipal, conclusões e redesign de UI vivem só no working tree. | Commit, push, baseline. |

**A peça central deste plano** (que o V2 não tinha): a **leitura associativa
quantificada** — transformar "coexistência" em **co-movimento documentado** com
estatística descritiva não causal, e inverter a moldura da página para que a leitura
lidere e a negação vire nota metodológica. É isso que responde à frase da gestão
"mostrando os dados que sustentam essa leitura".

## 3. Decisões

| # | Decisão | Registro |
|---|---|---|
| V3-D1 | **Protocolo v4** (§4): papéis invertidos em relação ao v3 — o **Fable arquiteta, orquestra, revisa e é o gate**; o **GPT 5.6 sol xhigh executa o código** sob especificação fechada; o mantenedor arbitra e faz os GA humanos. | 2026-08-26 |
| V3-D2 | **Garantia de progresso**: o processo nunca para esperando job morto — vivacidade é responsabilidade ativa do Fable; segunda morte de um job = o Fable executa a tarefa ele mesmo e registra (§4.3.4). | 2026-08-26 |
| V3-D3 | **Invariantes herdadas do V1/V2 permanecem**: sem causalidade, sem número futuro, fail-closed pesquisa→gerador→plataforma, prévia rotulada, taxa nunca somada, classe `calculated`, guardas de linguagem com corpus bilateral, "portar antes de deletar". | herdadas |
| V3-D4 | **Estatística associativa é descritiva e fechada por construção** (R1): concordância de direção, co-movimento por janela, defasagem declarada e contraste com a distribuição estadual — computadas na pesquisa, reverificadas na plataforma, **nunca** correlação apresentada como causa, **nunca** r/p-valor solto na página sem gramática fechada. | 2026-08-26 |
| V3-D5 | **Sequência dirigida pelo pedido**: primeiro dar força e legibilidade ao que já está no ar (R0–R2), depois expandir cobertura (R3), depois entregar (R4). Opção C da R5 do V2 (matrícula municipal via microdados do Censo Escolar) vai ao backlog como rodada condicional, não bloqueia. | 2026-08-26 |
| V3-D6 | **GA de leitura da R5 do V2 dispensado pelo mantenedor** (árbitro) na Rodada 0: "não li, mas vamos avançando sem minha revisão". Não é sign-off de leitura; registrado como desvio §4.2.6 em `GA_HUMANO_RODADA_05.md` e `ENCERRAMENTO_R5.md`. Compensações mecânicas do gate registradas; achado futuro do mantenedor entra como correção na rodada em que surgir. | 2026-08-26 |

## 4. Protocolo de execução v4

### 4.1 Papéis

- **Arquiteto-orquestrador-revisor — Fable 5** (sessão Claude Code, contexto limpo por
  rodada): deriva o checklist fechado da rodada; escreve a **especificação fechada de
  cada tarefa de código** (arquivo `TAREFA_<id>.md` no diretório da rodada: escopo,
  arquivos, instrumentos de aceite, proibições); despacha os jobs ao executor; monitora
  a vivacidade; **verifica cada entrega com instrumentos próprios** (testes, greps,
  builds, leitura do diff — nunca aceita o relato do executor como prova); emite o
  veredito de encerramento da rodada. É o gate.
- **Executor — GPT 5.6 sol xhigh** (plugin Codex, agente `codex-rescue`, modelo
  **`gpt-5.6-sol`**, reasoning **xhigh** — nunca outro id: `gpt-5.6` retorna 400 e
  `gpt-5.6-codex` trava em starting): executa as tarefas de escrita de código conforme a
  especificação. Regras operacionais: **um job = uma chamada**; `--write` obrigatório
  para escrever; sem `--cd`; saída obrigatória em arquivo declarado em `.tmp/`; o
  diagnóstico real vive no **log da task**, não na lista de processos.
- **Árbitro — o mantenedor**: abre cada rodada numa sessão nova do Fable; faz os GA
  humanos marcados; decide mudanças de plano e empates.

### 4.2 Ciclo da rodada

1. Mantenedor abre a rodada colando o prompt de abertura numa **sessão nova** do Fable.
2. Fable deriva o checklist fechado (um item = um instrumento nomeado) e o grava no
   diretório da rodada antes de qualquer despacho.
3. Fable fatia o trabalho em tarefas de código com especificação fechada e despacha ao
   executor, **uma tarefa por job**, paralelizando só tarefas sem interseção de arquivos.
4. A cada entrega: Fable roda os instrumentos da tarefa sobre o diff real. PASS →
   próxima tarefa. FAIL → lista fechada de correções de volta ao executor; **máximo 2
   ciclos de correção por tarefa**, depois o Fable corrige diretamente e registra o fato
   e o diff no dossiê.
5. Checklist 100% verde → Fable escreve `RELATORIO_RODADA_<NN>.md` (com seções
   Vivacidade e Backlog) e encerra. GA humano marcado na rodada acontece **antes** do
   encerramento.
6. Achado fora do checklist → backlog nomeado, nunca bloqueio. Desvio que altere o plano
   → edição deste documento na própria rodada + linha na tabela §3.
7. Commits: ao final de cada rodada, com mensagem descritiva; push conforme a rodada
   mandar. Nenhum commit no meio de tarefa.

### 4.3 Vivacidade — o processo nunca para

1. Todo job declara **antes do disparo**: task id, arquivo de saída esperado e horário.
   Os três entram no dossiê.
2. O Fable **verifica o log da task a cada ~5 minutos**. Log sem progresso por **10
   minutos** = job morto. Job "concluído" sem o arquivo de saída declarado = morto.
3. Job morto → **relançamento imediato, uma vez**, com escopo igual ou reduzido.
4. **Segunda morte da mesma tarefa → o Fable executa a tarefa ele mesmo**, registra a
   troca de executor no dossiê e segue. Nenhuma tarefa espera um terceiro relançamento.
5. Enquanto espera qualquer job, o Fable **adianta trabalho que não depende dele**:
   especificação da próxima tarefa, preparação dos instrumentos, leitura de diffs
   anteriores. A espera nunca é ociosa.
6. O relatório de toda rodada tem seção **"Vivacidade"**: cada job com horários de
   disparo/conclusão, relançamentos, mortes e trocas de executor. Job sem contabilidade
   = desvio.

## 5. Rodadas

Sequência: `R0 → R1 → R2 → R3 → R4`. Cada rodada em sessão nova do Fable.
Diretórios de trabalho: `.tmp/vocacoes-v3/rodada-<NN>/` (gitignored).

---

### Rodada 0 — Encerramento do V2 e consolidação

**Objetivo:** fechar a R5 do V2 (pendente), commitar todo o legado do V2 e estabelecer a
baseline.

**Tarefas:**
1. **Fechamento da R5 do V2**: o Fable faz a revisão pedida no
   `.tmp/vocacoes-regiao-v2/rodada-05/HANDOFF_RODADA_05.md` (era endereçado a ele);
   trata os 2 itens não-código do parecer NÃO CONFORME (ciclo 1); GA humano do
   mantenedor (leitura de 4 municípios sorteados, 2 por região) — achados viram
   correções na hora (executor GPT, ou Fable se triviais).
2. **Consolidação git**: revisar o diff completo do working tree (contrato
   2.2.0→2.5.0, remoção do foresight municipal, ponte R4, camada municipal R5,
   conclusões V2-D8, redesign de UI); commitar em commits temáticos; push de `main`.
3. Suíte baseline completa (`test:unit`, `test:regional`, `test:vocacoes-regiao`,
   `test:matriz`, `check:*`, `typecheck`, `lint`) com resultado real registrado; falhas
   pré-existentes nomeadas (ex.: `pne-frontend-ux.test.mjs`), não caçadas.
4. Snapshot dos hashes do manifesto como baseline.
5. Nota de encerramento no `docs/PLANO_VOCACOES_REGIAO_V2.md` (status + decisão V2-D9
   apontando para este plano).

**Aceite:** R5 do V2 encerrada com GA humano registrado; working tree limpo; `main`
sincronizada com o remoto; suíte com resultado real registrado; snapshot gravado; V2
anotado como encerrado.

**Prompt de abertura:**
```text
Leia docs/PLANO_VOCACOES_REGIAO_V3.md (§1–§4 e Rodada 0 do §5) e
.tmp/vocacoes-regiao-v2/rodada-05/HANDOFF_RODADA_05.md. Execute a Rodada 0 conforme o
protocolo v4 (§4): você arquiteta, orquestra e verifica; o GPT 5.6 sol xhigh
(codex-rescue, gpt-5.6-sol, xhigh, --write) executa o código que você especificar;
vivacidade §4.3 sob sua responsabilidade. GA humano comigo antes do encerramento.
Relate em .tmp/vocacoes-v3/rodada-00/. Não inicie a rodada seguinte.
```

---

### Rodada 1 — Leitura associativa quantificada (a peça nova)

**Objetivo:** transformar "coexistência na mesma janela" em **co-movimento documentado**
— a resposta direta à frase da gestão "mostrando os dados que sustentam essa leitura" e
à camada temporal do pedido.

**Tarefas:**
1. **Camada de estatística descritiva na pesquisa** (SESI\PNE, builder determinístico),
   por associação e por par temporal de cada região:
   - **Concordância de direção**: em quantos dos N anos da janela as duas séries
     variaram no mesmo sentido ("em 8 dos 11 anos, as duas caíram juntas");
   - **Co-movimento por janela**: variação acumulada de cada série em janelas
     idênticas, com sentido e magnitude relatados lado a lado;
   - **Defasagem declarada** onde a estrutura do par já a define (SINASC → matrículas
     k anos depois): concordância computada na janela defasada, com k explícito;
   - **Contraste estadual**: posição da região na distribuição das 10 para a mesma
     estatística ("esta região é a 2ª maior queda entre as 10").
   Tudo **fechado por construção**: números computados, frases montadas de template com
   gramática fechada (mesma disciplina de V2-D8), zero prosa livre.
2. **Proibições verificadas por guarda + corpus**: nenhum termo causal ("explica",
   "determina", "impacto de", "por causa de"), nenhum coeficiente de correlação nu na
   página, nenhuma extrapolação. Corpus bilateral com ataques novos (correlação
   travestida, causalidade por ordem temporal).
3. **Contrato público 2.5.0 → 2.6.0 (aditivo)**: bloco `associativeReading` por
   associação/par, com dados de sustentação, estatística, interpretação
   permitida/proibida; reverificação fail-closed na plataforma
   (`vocacoesRegiaoContract.js`); gerador atualizado; changelog com motivo.
4. Rebuild das 10 regiões; prova de que as estatísticas **diferem entre regiões**
   (anti-template, instrumento da R3 do V2); teste de intercambialidade (trocar a região
   e o texto denuncia pelos números).
5. Publicação (dados; a renderização muda na R2).

**Aceite:** builder determinístico com hash estável ×2; estatística correta provada por
recomputação independente do Fable em amostra (2 regiões × 3 associações, cálculo
próprio × valor publicado); contrato 2.6.0 verde; corpus bilateral 100%; anti-template
verde; suíte sem regressão.

**Prompt de abertura:**
```text
Leia docs/PLANO_VOCACOES_REGIAO_V3.md (§1–§4 e Rodada 1 do §5) e o relatório da rodada
anterior. Execute a Rodada 1 conforme o protocolo v4 (§4): você especifica e verifica
(inclusive recomputação independente da estatística em amostra); o GPT 5.6 sol xhigh
executa o código; vivacidade §4.3. Relate em .tmp/vocacoes-v3/rodada-01/. Não inicie a
rodada seguinte.
```

---

### Rodada 2 — Inversão da moldura: a leitura lidera a página

**Objetivo:** o problema do print da gestão — a página passa a **responder** à pergunta
"quais características do território podem estar relacionadas ao cenário educacional?"
em vez de liderar com o que não se pode concluir.

**Tarefas:**
1. **Nova hierarquia do bloco de associação** (página regional): 1º a leitura
   associativa quantificada (R1) + conclusão observada; 2º os dados de sustentação
   (séries); 3º hipóteses explicativas com os dados que as motivam; por último, "o que
   não se conclui" **recolhido como nota metodológica** (`details`, padrão do redesign
   2026-08-26) — presente, honesto, mas não protagonista.
2. Mesma inversão no bloco territorial da matriz municipal (ponte R4 do V2) e nos pares
   temporais.
3. Títulos e "como ler" reescritos contra as duas perguntas literais da gestão (cada
   seção responde visivelmente a uma).
4. Nenhuma guarda afrouxada: o conteúdo da nota é o mesmo; muda posição e peso visual.
   Guardas de linguagem e testes de arquitetura de UI atualizados junto.
5. **GA humano**: o mantenedor lê 1 região completa e 1 município na tela, comparando
   com o print original da gestão; achados viram correções na própria rodada.

**Aceite:** hierarquia nova no ar nas 10 regiões + matriz; SSR mantém conteúdo no
markup (restrição conhecida do redesign); zero mudança de conteúdo nas frases de guarda;
GA humano registrado; suíte + guardas verdes.

**Prompt de abertura:**
```text
Leia docs/PLANO_VOCACOES_REGIAO_V3.md (§1–§4 e Rodada 2 do §5) e o relatório da rodada
anterior. Execute a Rodada 2 conforme o protocolo v4 (§4): inversão da moldura nas
páginas regional e municipal, GPT 5.6 sol xhigh executa, você verifica, GA humano
comigo antes do encerramento; vivacidade §4.3. Relate em .tmp/vocacoes-v3/rodada-02/.
Não inicie a rodada seguinte.
```

---

### Rodada 3 — Expansão dos cenários às 8 regiões (Saída 2 completa)

**Objetivo:** Saída 2 nas 10 regiões — cenários, temas de agenda do PNE e camada
municipal. Absorve a R6 do V2, com a condição V2-D3 herdada.

**Tarefas:**
1. **Gate de transferibilidade (abre a rodada)**: veredito do Fable sobre o processo
   VRP+Noroeste (dados suficientes por região? regra morfológica reproduzível? item B26
   resolvido ou aceito com registro?). Veredito negativo = rodada encerra aqui, fato
   declarado à gestão na R4.
2. Construção em **2 lotes de 4 regiões** pelas 8 etapas do guia v1.6 (esqueleto fixado
   antes da narrativa); o executor constrói sob especificação por etapa; o Fable audita
   a narrativa de cada lote (papel que era do GPT no v3 — agora invertido).
3. Por lote: intercambialidade contra **todas** as já publicadas; teste cego por
   realidade (juiz = job GPT não-gate); zero contradição trajetória×número; temas de
   agenda; leitura associativa (R1) e moldura (R2) aplicadas; **camada municipal** da
   região construída junto (contrato 2.4.0 já cobre).
4. GA humano por lote: 1 região sorteada, leitura integral do mantenedor.
5. Publicação incremental por lote (`scenarioStatus: published` região a região).

**Aceite:** veredito de transferibilidade registrado; por lote publicado —
intercambialidade zero, teste cego 100%, zero contradição, camada municipal presente,
GA humano feito, suíte verde. Gate reprovado = relatório + edição deste plano.

**Prompt de abertura:**
```text
Leia docs/PLANO_VOCACOES_REGIAO_V3.md (§1–§4 e Rodada 3 do §5) e o relatório da rodada
anterior. Execute a Rodada 3 conforme o protocolo v4 (§4): primeiro o gate de
transferibilidade; se verde, 2 lotes de 4 regiões — GPT 5.6 sol xhigh executa por
especificação sua, você audita narrativa e instrumentos, GA humano comigo por lote;
vivacidade §4.3. Relate em .tmp/vocacoes-v3/rodada-03/. Não inicie a rodada seguinte.
```

---

### Rodada 4 — Legibilidade final, governança e entrega à gestão

**Objetivo:** o produto responde, em linguagem que a gestão reconheça, às duas
perguntas do pedido — com dono, cadência e regra de expiração. Absorve a R7 do V2.

**Tarefas:**
1. Revisão editorial dirigida pelo pedido: leitura adversarial do Fable das duas
   páginas contra as duas perguntas literais; implicações de continuidade reescritas
   como agenda ("o que acompanhar / o que decidir"); correções pelo executor.
2. Teste de leitura humano: mantenedor (e, se possível, a gestora) lê 1 região completa
   e 1 município; achados viram correções na própria rodada.
3. Governança (`docs/GOVERNANCA_VOCACOES_REGIAO.md`): responsável, cadência por fonte
   (RAIS anual, SINASC mensal/prévia, INEP anual, CadÚnico mensal), regra de expiração
   fail-visible ("desatualizado" na página), canal de contestação.
4. **Documento de entrega à gestão** (2–3 páginas): cada item do pedido original mapeado
   ao que está no ar, com as limitações declaradas (o que o dado não permite e por quê)
   — inclusive o destino da Opção C (matrícula municipal) e do que o gate da R3 tiver
   deixado fora.
5. Varredura final: suíte completa, guardas, coerência de docs, push.

**Aceite:** páginas respondem às duas perguntas (leitura humana registrada); governança
publicada; documento de entrega pronto; suíte verde; tudo pushado.

**Prompt de abertura:**
```text
Leia docs/PLANO_VOCACOES_REGIAO_V3.md completo e o relatório da rodada anterior.
Execute a Rodada 4 conforme o protocolo v4 (§4): revisão editorial dirigida pelo
pedido, teste de leitura humano comigo, governança, documento de entrega, varredura
final; GPT 5.6 sol xhigh executa as correções, você verifica; vivacidade §4.3. Relate
em .tmp/vocacoes-v3/rodada-04/. Este é o encerramento do plano V3.
```

---

## 6. Backlog e rodadas condicionais

- **Opção C da R5 do V2**: matrícula municipal por etapa via microdados do Censo Escolar
  (`SESI/DB/data/censo_escolar`), com manifesto novo — engrossaria a camada municipal
  sem tocar RAIS. Rodada condicional pós-R4, a critério do mantenedor.
- **Furos de classe aberta da guarda ponte** (voz passiva com agente, causalidade por
  ordem temporal): declarados no corpus; fechá-los exige semântica, não léxico.
- **Catálogo de mecanismos com lastro em literatura** para as hipóteses explicativas
  (consulta não-gate ao GPT ou pesquisa externa): opcional, agrega substância às
  hipóteses; pode entrar na R2 ou na R4 se o mantenedor pedir.
- Backlog herdado do V2 permanece em `BACKLOG_V2.md` com destinos válidos.

## 7. Riscos

1. **Executor GPT em tarefa grande** (R1 e R3 são as maiores) — mitigação: fatiamento em
   tarefas de escopo fechado, um job por tarefa; vivacidade §4.3 com fallback de
   execução pelo Fable (V3-D2).
2. **Estatística descritiva escorregar para linguagem causal** (R1/R2) — mitigação:
   V3-D4, corpus com ataques novos, recomputação independente e leitura adversarial do
   Fable, que agora é o gate.
3. **Quem verifica é quem orquestra** (Fable acumula papéis) — mitigação: instrumentos
   mecânicos (testes, greps, hashes, recomputação) como base do veredito, não juízo; GA
   humano nas rodadas de página; teste cego da R3 com juiz GPT independente.
4. **Gate de transferibilidade reprovar** (R3) — não é falha do plano: a limitação vai
   nomeada no documento de entrega da R4.
5. **Consolidação da R0 encontrar conflito no remoto** — mitigação: push só após revisão
   do diff; qualquer dúvida sobre o remoto vai ao mantenedor antes.
