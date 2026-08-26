# Plano — Vocações da Região V2: rodadas de melhoria (revisão D12)

Data: 2026-08-25
Origem: este plano é a **revisão total prevista pela decisão D12** do
`docs/PLANO_VOCACOES_REGIAO_V1.md` — conduzida pelo mantenedor com o Fable, cobrindo todas as
Rodadas 0–10 do V1 e o pedido original da gestão. O V1 está encerrado; a partir daqui vale este
documento.
Status: **aprovado para execução** (protocolo v3, §4).

---

## 1. Veredito da revisão: o que o V1 entregou frente ao pedido da gestão

O pedido da gestão define duas saídas cruzando dados educacionais com dados territoriais do
Vocações, mais uma camada temporal:

| Camada pedida | Estado no ar (contrato 2.1.0, 2026-08-25) | Veredito |
|---|---|---|
| **Saída 1 — o território explica a educação** (PME → Vocações) | Bloco "associações": 6 associações por região, cada uma com resultado educacional, fatores territoriais, dados de sustentação, interpretação permitida/proibida e hipóteses — sem causalidade, como pedido. | **Parcial.** Existe e a linguagem está correta, mas (a) as **mesmas 6 associações valem para as 10 regiões** — template estadual com valores regionais, não curadoria a partir do resultado saliente de cada região; (b) os resultados educacionais cobertos são só **estoque de matrícula** — distorção idade-série, conclusão, permanência e abandono (metade da lista da gestão) estão declarados fora porque a série regional não existe. |
| **Saída 2 — o futuro do território exige da educação** (Vocações → PNE) | Bloco "cenários": 4 cenários (3 exploratórios + 1 normativo) com implicações educacionais por etapa (rede/oferta, EM e EP, EJA, profissionais do ensino). | **Parcial.** Publicado em **2 de 10 regiões** (Vale do Rio Pardo e Noroeste); as outras 8 declaram ausência (D12 suspendeu a expansão). **Zero menção às metas e estratégias do PNE** no documento publicado — a ponte "implicação → agenda do PNE" não foi construída. E o pedido fala em "transformações projetadas **para o município** e para a região": a camada municipal não existe (a sucessora definida na D11 não foi construída). |
| **Camada temporal — transformações simultâneas** | Bloco "pares temporais": 6 pares por região com séries longas (demografia × matrículas EM; emprego por escolaridade × EJA; indústria × EP técnica; nascimentos defasados × 3 etapas), janelas idênticas por par. | **Cumprida no essencial.** ~20 anos de dado (RAIS 2006–2025, SINASC 1994+, PIB 2002–2023) como a gestão pediu. Ressalvas: o par "emprego/renda × permanência" virou proxy via EJA (permanência não existe no dado); e os pares também são o **mesmo template nas 10 regiões**. |

Além disso, dois compromissos internos do V1 ficaram pendentes:

1. **D11 não executada** — o produto municipal `foresight-educacao` continua no ar; a remoção
   com os três pontos de "portar antes de deletar" (inventário na Rodada 10 do V1) não ocorreu.
2. **Higiene de git** — `main` está à frente do remoto sem push desde a R5; o branch
   `vocacoes-regiao/rodada-05` carrega o trabalho da R9 com arquivos modificados não
   consolidados.

**Resposta curta à pergunta da gestão:** a plataforma já entrega a *forma* das duas saídas com
a disciplina de linguagem certa (associação sem causalidade, cenário sem projeção numérica),
mas não entrega ainda a *substância completa*: falta metade dos resultados educacionais
(fluxo escolar), falta curadoria específica por região, faltam cenários em 8 regiões, falta a
camada municipal, e falta a ponte explícita com o PNE (metas/estratégias e a matriz municipal —
hoje os dois produtos não se referenciam em nenhum ponto do código ou dos dados).

## 2. Lacunas nomeadas (insumo das rodadas)

| # | Lacuna | Evidência | Rodada |
|---|---|---|---|
| L1 | Pendências de consolidação: push de `main`, merge do branch da R9, suíte baseline | git status 2026-08-25 | R0 |
| L2 | D11 não executada; D3 precisa virar regra única da família regional | inventário da Rodada 10 do V1 | R1 |
| L3 | Fluxo escolar regional inexistente: distorção idade-série, rendimento (aprovação/reprovação/abandono), conclusão | limitação declarada nos 10 pacotes | R2 |
| L4 | Associações e pares idênticos nas 10 regiões (template, não curadoria) | `associationId`/`pairId` byte-idênticos nas 10 | R3 |
| L5 | Nenhuma referência às metas/estratégias do PNE na Saída 2; matriz municipal e produto regional não se cruzam | 0 ocorrências de "PNE"/"meta" nos pacotes; 0 referências cruzadas em `src/features/matriz` | R4 |
| L6 | Camada municipal dentro do cenário regional (sucessora da D11) não construída | decisão D11, Rodada 10 do V1 | R5 |
| L7 | Cenários ausentes em 8 regiões; veredito de transferibilidade em aberto | `scenarioStatus: absent` em 8 manifestos | R6 |
| L8 | Backlog herdado do V1: 6º par de intercambialidade corrigido e não verificado (R7); caixa morfológica que não elimina nada (B26); governança de manutenção (B39/B40/B42, D13) | atas/relatórios do V1 | R0 (triagem), R6, R7 |
| L9 | Legibilidade das implicações educacionais: cenário de continuidade lê-se como "nada muda" em vez de agenda de planejamento | leitura amostral do pacote VRP | R7 |

## 3. Decisões desta revisão

| # | Decisão | Registro |
|---|---|---|
| V2-D1 | **Protocolo v3** (§4): Opus 4.8 executa; GPT 5.6 sol xhigh orquestra e audita cada rodada como gate de avanço, podendo aplicar correções diretamente; rotina de vivacidade obrigatória para todo job do GPT. | 2026-08-25 |
| V2-D2 | **Sequência dirigida pelo pedido da gestão**, não pela arquitetura: primeiro fechar o que falta das duas saídas (fluxo escolar, curadoria regional, ponte PNE), depois expandir cenários. | 2026-08-25 |
| V2-D3 | A **expansão dos cenários às 8 regiões (R6) revoga a suspensão da D12** somente se o gate de transferibilidade da própria R6 fechar verde; caso contrário a suspensão continua e o fato é levado à gestão como limitação declarada. | 2026-08-25 |
| V2-D4 | Invariantes do V1 permanecem: fluxo pesquisa→gerador→plataforma fail-closed (D7), sem causalidade, sem número futuro, prévia rotulada, CadÚnico com universo, classe `calculated` na migração, guardas de linguagem com corpus bilateral. | herdadas |

## 4. Protocolo de execução v3

### 4.1 Papéis

- **Executor — Opus 4.8** (sessão Claude Code, contexto limpo por rodada): constrói todas as
  entregas da rodada, deriva o checklist fechado da seção Aceite, roda os instrumentos, escreve
  o dossiê. Não encerra a rodada sozinho.
- **Orquestrador-auditor — GPT 5.6 sol xhigh** (plugin Codex, agente `codex-rescue`, modelo
  **`gpt-5.6-sol`**, reasoning **xhigh** — nunca outro id: `gpt-5.6` retorna 400 e
  `gpt-5.6-codex` trava em starting): audita o dossiê de cada rodada contra este plano e emite
  o **veredito de gate** (CONFORME / CONFORME COM CORREÇÕES APLICADAS / NÃO CONFORME). Quando
  julgar que os ajustes necessários são de escopo fechado (correção de texto, guarda, teste,
  configuração), **ele mesmo aplica** — job com `--write` — e registra o diff no parecer.
  Mudança estrutural (contrato, arquitetura, dado novo) volta ao executor com lista fechada.
- **Árbitro — o mantenedor**: gates humanos (GA-3 e ratificações previstas nas rodadas),
  mudanças de plano, e o caso de auditoria duplamente morta (§4.3).

### 4.2 Ciclo da rodada

1. Mantenedor abre a rodada colando o prompt de abertura numa sessão nova do Opus 4.8.
2. Executor deriva o checklist fechado do Aceite (um item = um instrumento nomeado) e o grava
   no diretório da rodada antes da primeira construção.
3. Construção com verificação contínua; item FAIL → correção → re-verificação, sem limite de
   iterações.
4. Dossiê pronto → **auditoria de gate** ao GPT 5.6 sol xhigh (job `codex-rescue`, uma chamada
   = uma auditoria, saída obrigatória em arquivo `PARECER_RODADA_<NN>.md` no diretório da
   rodada; `--write` autorizado desde o início para que o auditor possa corrigir).
5. Veredito: **CONFORME** → executor escreve `RELATORIO_RODADA_<NN>.md` e encerra.
   **CONFORME COM CORREÇÕES APLICADAS** → executor confere o diff do auditor com os
   instrumentos do checklist (correção que quebre instrumento reverte e vira NÃO CONFORME) e
   encerra. **NÃO CONFORME** → executor aplica a lista fechada, resubmete **só os itens
   apontados**; máximo **2 ciclos de auditoria** por rodada, depois arbitragem do mantenedor.
6. Achado fora do checklist → backlog nomeado no relatório, nunca bloqueio.
7. Desvio que altere o plano → edição deste documento na própria rodada + linha na tabela §3.
   Desvio omitido é falha da rodada.

### 4.3 Vivacidade — nenhum processo espera calado

Regra nova, exigida pela experiência do V1 (jobs do Codex morrem sem stdout):

1. Todo job do GPT declara **antes do disparo**: arquivo de saída esperado, task id e horário.
   O executor registra os três no dossiê.
2. O executor **verifica o log da task a cada ~5 minutos** (o diagnóstico real vive no log da
   task, não na lista de processos). Log sem progresso por **10 minutos** = job morto.
3. Job morto → **relançamento imediato, uma vez**, com escopo igual ou reduzido. Enquanto
   espera qualquer job, o executor **adianta as tarefas da rodada que não dependem do
   veredito** — a espera nunca é ociosa e nunca segura tarefa independente.
4. Segunda morte de uma **auditoria de gate** → o executor NÃO encerra a rodada sozinho:
   empacota o dossiê + os dois logs de falha e aciona o mantenedor, que decide entre
   (a) terceira tentativa, (b) auditoria reduzida a checklist mecânico, ou (c) avanço com
   ausência de auditoria declarada no relatório. Segunda morte de consulta **não-gate** →
   descarte com registro, como no v2.1.
5. O relatório de toda rodada tem uma seção **"Vivacidade"**: cada job com horários de
   disparo/conclusão, relançamentos e mortes. Job sem essa contabilidade = desvio.

## 5. Rodadas

Sequência: `R0 → R1 → R2 → R3 → R4 → R5 → R6 → R7`. R2 e R1 podem correr em paralelo a
critério do mantenedor (R1 não toca a origem de dados; R2 não toca a plataforma). R3 depende
de R2; R4 depende de R3; R5 depende de R1 (a sucessora da D11 pressupõe o municipal removido);
R6 depende de R5; R7 fecha.

Diretórios de trabalho: `.tmp/vocacoes-regiao-v2/rodada-<NN>/` (gitignored).

---

### Rodada 0 — Consolidação e triagem do legado

**Objetivo:** deixar o repositório e o backlog em estado limpo antes de qualquer mudança.

**Tarefas:**
1. Consolidar o branch `vocacoes-regiao/rodada-05`: revisar o diff pendente (trabalho da R9),
   commitar, mergear em `main`.
2. `git push` de `main` (está à frente do remoto desde a R5 do V1) — confirmar com o
   mantenedor antes do push se houver qualquer dúvida sobre o remoto.
3. Suíte baseline completa (`test:unit`, `test:foresight`, `test:regional`,
   `test:vocacoes-regiao`, `check:*`) com resultado real registrado; falhas pré-existentes
   nomeadas, não caçadas.
4. Triagem do backlog do V1: ler os relatórios das rodadas 0–10, extrair todo item de backlog
   nomeado (B1…B42+) para uma tabela única `BACKLOG_V2.md` com destino (rodada deste plano,
   descartado com motivo, ou "fora de escopo declarado").
5. Snapshot dos 10 pacotes publicados (hashes do manifesto) como baseline de comparação.

**Aceite:** branch mergeado e `main` sincronizada com o remoto; suíte com resultado real
registrado; `BACKLOG_V2.md` com 100% dos itens do V1 triados; snapshot de hashes gravado.

**Prompt de abertura:**
```text
Leia docs/PLANO_VOCACOES_REGIAO_V2.md (§1–§4 e Rodada 0 do §5). Execute a Rodada 0 conforme
o protocolo v3 (§4): derive o checklist, execute, monte o dossiê e submeta à auditoria de
gate do GPT 5.6 sol xhigh via codex-rescue (modelo gpt-5.6-sol, xhigh, saída em arquivo,
vivacidade §4.3). Relate em .tmp/vocacoes-regiao-v2/rodada-00/. Não inicie a rodada seguinte.
```

---

### Rodada 1 — Execução da D11: remoção do produto municipal

**Objetivo:** remover `foresight-educacao` da plataforma executando o inventário fechado da
Rodada 10 do V1, sem quebrar o produto regional que fica no ar.

**Tarefas (ordem obrigatória — portar antes de deletar):**
1. **Portar o teste da D3:** `scripts/checks/vocacoes-regiao-cenarios.test.mjs` deixa de ler
   `public/data/foresight-educacao/schema.json`; a regra de estatuto por cenário passa a ser
   provada contra o próprio `public/data/vocacoes-regiao/schema.json`.
2. **Reescrever a D3 como regra única:** `schema.json` regional remove `distinctFrom.family:
   "foresight-educacao"` e passa a declarar a regra da própria família (3 exploratórios + 1
   normativo com estatuto explícito) sem referência à família extinta; nota de leitura da
   página ajustada na mesma linha. Isso é mudança de contrato público: versão do documento
   sobe (`2.1.0` → `2.2.0`), gerador (`generate-vocacoes-regiao.mjs`) atualizado, e o
   changelog do contrato registra o motivo.
3. **Remover o produto municipal** pelo inventário da Rodada 10 do V1: `src/features/foresight/`
   (8 arquivos), `useForesightEducacao.ts`, `foresightPublication.ts`,
   `public/data/foresight-educacao/`, `generate-foresight-educacao.mjs`, 4 suítes, tsconfig,
   4 scripts do `package.json`, referências em `navigationRegistry.ts`, `Header.jsx`,
   `AppPageRouter.tsx`, `NavGlyphIcon.tsx`, `analyticsProducts.ts`, `types/app.ts`,
   `app-routing-test.mjs`; docs `BRIEFING_FORESIGHT_EDUCACAO_MUNICIPAL.md` e
   `FORESIGHT_EDUCACAO_INTEGRACAO_PLATAFORMA_V0_4_0_RC4.md` movidos para um diretório de
   arquivo morto (`docs/arquivo/`) com nota de remoção, não deletados do histórico.
4. Suíte completa + navegação manual (menu sem o item municipal; regional intacto; nenhuma
   rota órfã).
5. A camada de pesquisa municipal (`SESI\PNE\foresight\` fora deste repo) **não é tocada**
   nesta rodada — inventário do que ela contém entra no relatório para a R5 decidir reuso.

**Aceite:** zero referências a `foresight-educacao` no código e nos dados publicados (grep
como instrumento); contrato `2.2.0` publicado com regra única e `generate`+`check` verdes;
teste da D3 portado e passando; suíte sem regressão nova; docs arquivados com nota.

**Auditoria de gate (obrigatória):** foco no contrato 2.2.0 — o auditor ataca a regra única
(a página ainda declara o estatuto do C4 com transparência? alguma frase pública ficou órfã da
comparação com a família extinta?).

**Prompt de abertura:**
```text
Leia docs/PLANO_VOCACOES_REGIAO_V2.md (§1–§4 e Rodada 1 do §5) e o relatório da Rodada 0 em
.tmp/vocacoes-regiao-v2/rodada-00/. Execute a Rodada 1 conforme o protocolo v3 (§4): porte
os três pontos de dependência, reescreva a D3 como regra única (contrato 2.2.0), remova o
produto municipal pelo inventário, e submeta à auditoria de gate do GPT 5.6 sol xhigh
(gpt-5.6-sol, xhigh, vivacidade §4.3). Relate em .tmp/vocacoes-regiao-v2/rodada-01/. Não
inicie a rodada seguinte.
```

---

### Rodada 2 — Aquisição do fluxo escolar regional (INEP)

**Objetivo:** fechar a lacuna L3 — adquirir os indicadores de fluxo que a gestão pediu e que
hoje estão declarados fora: taxas de rendimento (aprovação, reprovação, abandono) e distorção
idade-série, por município, para agregação regional.

**Fontes-alvo (verificar disponibilidade real, sem proxy inventado):**
1. INEP — indicadores educacionais por município: taxas de rendimento e distorção idade-série,
   por etapa, série histórica pública (2014+ no mínimo; mais se houver).
2. INEP — taxa de conclusão / indicadores de trajetória, se existirem no grão municipal.
3. O que não existir no grão necessário vira **limitação declarada com a fonte consultada
   nomeada** — mesma disciplina da 5C; nenhuma imputação.

**Tarefas:**
1. Aquisição com manifesto (sha256 + URL + parâmetros + timestamp por resposta bruta), padrão
   da Rodada 2 do V1.
2. **Regra de agregação regional decidida antes do código e registrada em configuração**: taxa
   regional só por soma de numeradores sobre soma de denominadores; onde o INEP publicar só a
   taxa pronta (sem numerador/denominador), a série entra como **mediana/faixa municipal
   declarada, nunca como taxa regional** — ou fica fora, com limitação declarada.
3. Séries regionais gravadas no formato do contrato de pesquisa v0.2, validadas pelo validador
   existente; `municipiosComDado` por série.
4. Extensão do builder do Bloco 1: novas séries entram no retrato das 10 regiões; reexecução
   com hash estável.

**Aceite:** manifesto de aquisição reproduzível; séries de fluxo das 10 regiões validadas (ou
ausência declarada por fonte consultada); regra de agregação em configuração versionada;
builder determinístico com hash estável; nenhuma taxa regional calculada a partir de taxas
prontas.

**Auditoria de gate:** foco na regra de agregação e nos rótulos das séries novas (o auditor
ataca: alguma taxa virou média de taxas? alguma prévia virou observado?).

**Prompt de abertura:**
```text
Leia docs/PLANO_VOCACOES_REGIAO_V2.md (§1–§4 e Rodada 2 do §5) e o relatório da rodada
anterior. Execute a Rodada 2 conforme o protocolo v3 (§4): aquisição INEP de fluxo escolar
com manifesto, agregação regional por regra declarada, extensão do builder, auditoria de
gate do GPT 5.6 sol xhigh (gpt-5.6-sol, xhigh, vivacidade §4.3). Relate em
.tmp/vocacoes-regiao-v2/rodada-02/. Não inicie a rodada seguinte.
```

---

### Rodada 3 — Curadoria regional específica (Saída 1 de verdade)

**Objetivo:** fechar a lacuna L4 — cada região passa a partir **do seu próprio diagnóstico
educacional**, como o pedido da gestão descreve ("partimos de um resultado encontrado no
PNE"), em vez do template estadual de 6 associações.

**Tarefas:**
1. **Cardápio ampliado de associações candidatas** (configuração versionada, não código):
   incorporar os resultados de fluxo da R2 (distorção, abandono, aprovação) e renda
   (remuneração média/massa salarial RAIS) como fatores; manter as 6 atuais como candidatas.
   Meta: ≥ 12 associações candidatas e ≥ 10 pares temporais candidatos, cada um com
   interpretação permitida/proibida escrita.
2. **Regra de seleção determinística por região** (o precedente é a regra da rodada 4B do
   foresight municipal): critérios mensuráveis sobre as séries da própria região (magnitude da
   variação, completude do dado, saliência relativa às demais regiões) escolhem, por região,
   6–8 associações e 5–7 pares. A regra vive em configuração, roda no builder e é reproduzível.
3. Cada associação selecionada ganha uma frase de **por que esta região a destaca**, gerada de
   dados (comparação com a distribuição estadual), sem adjetivo livre.
4. Rebuild dos 10 pacotes; prova de que **os conjuntos selecionados diferem entre regiões**
   (instrumento: a interseção total das 10 seleções deve ser menor que o conjunto de uma
   região — se as 10 saírem idênticas de novo, a regra reprova).
5. Teste de intercambialidade textual das associações (herdado da disciplina da R8 do V1):
   trocar a região de uma associação e o texto tem de denunciar a troca pelos números.
6. Promoção canônica + publicação (gerador + página; a página já renderiza listas — mudança
   de dados, não de componente, exceto a frase do item 3).

**Aceite:** cardápio e regra de seleção em configuração versionada; 10 pacotes com seleções
comprovadamente distintas; toda associação nova com interpretação permitida/proibida e dados
de sustentação; fluxo escolar presente nas associações das regiões onde a R2 obteve dado;
suíte + guardas de linguagem verdes; GA-3 humano em 2 regiões sorteadas.

**Auditoria de gate:** foco na regra de seleção (o auditor ataca: a regra é mesmo
determinística? há grau de liberdade editorial escondido? as frases do item 3 afirmam
causalidade?).

**Prompt de abertura:**
```text
Leia docs/PLANO_VOCACOES_REGIAO_V2.md (§1–§4 e Rodada 3 do §5) e o relatório da rodada
anterior. Execute a Rodada 3 conforme o protocolo v3 (§4): cardápio ampliado + regra de
seleção determinística por região + rebuild + publicação, GA-3 com o mantenedor antes do
encerramento, auditoria de gate do GPT 5.6 sol xhigh (gpt-5.6-sol, xhigh, vivacidade §4.3).
Relate em .tmp/vocacoes-regiao-v2/rodada-03/. Não inicie a rodada seguinte.
```

---

### Rodada 4 — Ponte PNE ↔ Vocações (a costura que falta)

**Objetivo:** fechar a lacuna L5 — os dois sentidos do cruzamento pedidos pela gestão passam a
se referenciar de fato: a leitura municipal do PNE aponta para o território, e o cenário
regional aponta para a agenda do PNE.

**Tarefas:**
1. **Sentido PME → Vocações:** na página da matriz municipal do PNE, bloco novo "Contexto
   territorial da região" — identifica a região do município e apresenta um resumo das
   associações da região (dados regionais + link para a página regional). Dados vêm do pacote
   regional publicado (a plataforma pode ler o próprio publicado); nenhuma nova origem.
   Linguagem: "a região do município apresenta…", nunca "isto explica o resultado do
   município".
2. **Sentido Vocações → PNE:** no bloco de cenários regionais, as implicações educacionais
   ganham um campo estruturado de **temas de agenda** — vocabulário fechado alinhado às
   metas do PNE em vigor (ex.: universalização do EM, EJA, educação profissional, alfabetização
   etária, formação docente), cada tema com a frase de implicação que o sustenta. O contrato
   sobe minor (`2.2.0` → `2.3.0` aditivo). A referência é ao **tema da meta**, não ao número
   da meta com valor — número futuro segue proibido.
3. Guarda de linguagem nova para o bloco ponte: corpus bilateral (ataques: causalidade
   município←região, meta com número futuro; honestos: associação regional legítima).
   Verificação por injeção.
4. Testes: rota da matriz renderiza o bloco para município de cada região; fail-closed se o
   pacote regional da região do município estiver ausente/inválido (bloco some, página não
   quebra).

**Aceite:** bloco territorial no ar na matriz municipal para os municípios com região
publicada; temas de agenda no contrato 2.3.0 nas 2 regiões com cenário; guarda nova com
corpus bilateral 100/100 e furos conhecidos declarados; fail-closed provado por mutação;
suíte verde.

**Auditoria de gate:** foco na guarda nova e no vocabulário de temas (o auditor ataca a
fronteira "tema da meta" × "meta com número").

**Prompt de abertura:**
```text
Leia docs/PLANO_VOCACOES_REGIAO_V2.md (§1–§4 e Rodada 4 do §5) e o relatório da rodada
anterior. Execute a Rodada 4 conforme o protocolo v3 (§4): bloco territorial na matriz
municipal + temas de agenda no contrato 2.3.0 + guarda nova com corpus, auditoria de gate
do GPT 5.6 sol xhigh (gpt-5.6-sol, xhigh, vivacidade §4.3). Relate em
.tmp/vocacoes-regiao-v2/rodada-04/. Não inicie a rodada seguinte.
```

---

### Rodada 5 — Camada municipal dentro do cenário regional (sucessora da D11)

**Objetivo:** construir a camada que a D11 definiu como substituta dos cenários municipais:
para cada município da região, **como ele contribui para o cenário regional e como é afetado
por ele** — primeiro nas 2 regiões com cenário (VRP e Noroeste).

**Tarefas:**
1. Desenho do contrato da camada (pesquisa): por município, posição nos dados que sustentam o
   cenário (participação no emprego setorial, na matrícula, na demografia — tudo observado,
   nada projetado por município) + leitura qualitativa de exposição por mecanismo do cenário,
   com interpretação permitida/proibida. **Nenhum número futuro municipal, nenhuma
   probabilidade** — a exposição é derivada da composição observada, e o texto declara isso.
2. Builder determinístico da camada na pesquisa (VRP: 23 municípios; Noroeste: 133 — atenção
   à escala: o texto municipal é composto de dados + frases padronizadas, não prosa livre por
   município; heterogeneidade interna declarada via `municipiosComDado`).
3. Reuso avaliado da camada de pesquisa municipal aposentada (inventário da R1): o que servir
   como insumo observado entra pela porta da pesquisa com manifesto; o resto fica fora.
4. Contrato da plataforma sobe minor (`2.3.0` → `2.4.0` aditivo): bloco municipal dentro do
   bloco de cenários; página ganha a seção (seleção de município dentro da página regional);
   fail-closed por região inalterado.
5. Teste de intercambialidade municipal: trocar dois municípios da mesma região e o texto tem
   de denunciar pelos dados; teste cego amostral com juiz independente (consulta não-gate ao
   GPT, §4.3).
6. GA humano: o mantenedor lê 4 municípios sorteados (2 por região) antes do encerramento.

**Aceite:** camada publicada para VRP e Noroeste; zero número futuro municipal (guarda +
grep); exposição sempre derivada de composição observada com método declarado;
intercambialidade municipal zero na amostra; GA humano realizado; suíte verde.

**Auditoria de gate:** foco no contrato da camada (o auditor ataca: algum texto municipal
lê-se como previsão? a exposição virou ranking implícito de municípios?).

**Prompt de abertura:**
```text
Leia docs/PLANO_VOCACOES_REGIAO_V2.md (§1–§4 e Rodada 5 do §5) e o relatório da rodada
anterior. Execute a Rodada 5 conforme o protocolo v3 (§4): contrato + builder da camada
municipal dos cenários (VRP e Noroeste), contrato 2.4.0, página, testes de
intercambialidade, GA humano com o mantenedor, auditoria de gate do GPT 5.6 sol xhigh
(gpt-5.6-sol, xhigh, vivacidade §4.3). Relate em .tmp/vocacoes-regiao-v2/rodada-05/. Não
inicie a rodada seguinte.
```

---

### Rodada 6 — Expansão dos cenários às 8 regiões restantes

**Objetivo:** fechar a lacuna L7 — Saída 2 nas 10 regiões (condição V2-D3: só avança se o
gate de transferibilidade fechar).

**Tarefas:**
1. **Gate de transferibilidade (abre a rodada):** revisitar o processo VRP+Noroeste com o
   material das rodadas 6–8 do V1 e emitir o veredito que a D4 do V1 deixou em aberto —
   instrumento: checklist de transferibilidade (dados suficientes por região? regra de seleção
   morfológica reproduzível? item B26 — caixa que não elimina nada — resolvido ou aceito com
   registro?). Veredito negativo = rodada encerra aqui, suspensão continua, fato declarado.
2. Construção em **2 lotes de 4 regiões** (agrupadas por disponibilidade de dado), cada lote
   pelas 8 etapas do guia v1.6 com esqueleto fixado antes da narrativa.
3. Por lote: teste de intercambialidade contra **todas** as regiões já publicadas (não só
   par a par com VRP), teste cego de identificação por realidade (juiz independente via
   consulta não-gate), verificação de que trajetória não contradiz número citado (defeito da
   4F municipal como teste permanente), e o **6º par de intercambialidade herdado do V1**
   verificado no primeiro lote.
4. Camada municipal (R5) construída junto, por região do lote.
5. GA humano por lote: 1 região sorteada, leitura integral do mantenedor.
6. Publicação incremental por lote (manifesto passa a declarar `scenarioStatus: published`
   região a região; ausência declarada continua válida no meio do caminho).

**Aceite:** veredito de transferibilidade registrado; para cada lote publicado —
intercambialidade zero, teste cego 100% por realidade, zero contradição
trajetória×número, camada municipal presente, GA humano feito, suíte verde. Se o gate
reprovar: relatório com o veredito e este plano editado (a suspensão da D12 continua).

**Auditoria de gate:** uma por lote, foco na narrativa dos 4 cenários do lote.

**Prompt de abertura:**
```text
Leia docs/PLANO_VOCACOES_REGIAO_V2.md (§1–§4 e Rodada 6 do §5) e o relatório da rodada
anterior. Execute a Rodada 6 conforme o protocolo v3 (§4): primeiro o gate de
transferibilidade; se verde, 2 lotes de 4 regiões pelas 8 etapas do guia v1.6, com
intercambialidade, teste cego, camada municipal e GA humano por lote, e auditoria de gate
do GPT 5.6 sol xhigh por lote (gpt-5.6-sol, xhigh, vivacidade §4.3). Relate em
.tmp/vocacoes-regiao-v2/rodada-06/. Não inicie a rodada seguinte.
```

---

### Rodada 7 — Legibilidade, governança e entrega à gestão

**Objetivo:** o produto responde, em linguagem que a gestão reconheça, às duas perguntas do
pedido — e ganha dono, cadência e regra de expiração.

**Tarefas:**
1. **Revisão editorial dirigida pelo pedido (L9):** ler as duas páginas (regional e matriz
   municipal) contra as duas perguntas literais da gestão ("quais características do
   território podem estar relacionadas ao cenário educacional observado?"; "quais questões
   educacionais precisam entrar na agenda dos próximos anos?"). Cada seção deve responder
   visivelmente a uma delas — títulos e "como ler" ajustados onde não respondem. Em
   particular: implicações de cenário de continuidade reescritas como agenda ("o que
   acompanhar / o que decidir"), não como inventário do que não muda — sem afrouxar nenhuma
   guarda.
2. Teste de leitura humano: o mantenedor (e, se possível, a gestora) lê 1 região completa e
   1 município; achados viram correções na própria rodada.
3. **Governança (D13/L8):** responsável nomeado, cadência de atualização por fonte (RAIS
   anual, SINASC mensal/prévia, INEP anual, CadÚnico mensal), regra de expiração (dado além
   da cadência vira rótulo "desatualizado" na página — mecanismo fail-visible), canal de
   contestação territorial. Registrado em `docs/GOVERNANCA_VOCACOES_REGIAO.md`.
4. Documento de encerramento para a gestão: 2–3 páginas mapeando cada item do pedido original
   ao que está no ar, com as limitações declaradas (o que o dado não permite e por quê).
5. Varredura final: suíte completa, guardas, coerência de docs (probe padrão), push.

**Aceite:** páginas respondem às duas perguntas (leitura humana registrada); governança
publicada com mecanismo de expiração implementado ou explicitamente adiado por decisão do
mantenedor; documento de entrega pronto; suíte verde; tudo pushado.

**Auditoria de gate:** o auditor faz a leitura adversarial final do produto inteiro na pele
da gestora — a pergunta dele é "isso responde ao pedido?", com citação de onde não responde.

**Prompt de abertura:**
```text
Leia docs/PLANO_VOCACOES_REGIAO_V2.md completo e o relatório da rodada anterior. Execute a
Rodada 7 conforme o protocolo v3 (§4): revisão editorial dirigida pelo pedido da gestão,
teste de leitura humano com o mantenedor, governança em docs/GOVERNANCA_VOCACOES_REGIAO.md,
documento de entrega, varredura final, e auditoria de gate do GPT 5.6 sol xhigh
(gpt-5.6-sol, xhigh, vivacidade §4.3). Relate em .tmp/vocacoes-regiao-v2/rodada-07/. Este é
o encerramento do plano V2.
```

---

## 6. Riscos deste plano

1. **Fluxo escolar pode não existir no grão regional agregável** (R2) — mitigação: a regra
   "mediana/faixa municipal declarada ou ausência declarada" já está na rodada; a R3 seleciona
   só o que a R2 entregou.
2. **Regra de seleção regional degenerar em template de novo** (R3) — mitigação: instrumento
   de distinção entre regiões no aceite; se as 10 seleções saírem iguais, a regra reprova.
3. **Escala da Noroeste (133 municípios) na camada municipal** (R5) — mitigação: texto
   composto de dados + frases padronizadas; prosa livre por município está proibida por
   desenho.
4. **Gate de transferibilidade reprovar** (R6) — não é falha do plano: a suspensão da D12
   continua e a limitação vai à gestão nomeada no documento de entrega da R7.
5. **Autoverificação complacente** — menor que no v2.1: quem audita (GPT) não é quem constrói
   (Opus 4.8), e o gate é dele. O risco simétrico (auditoria morta segurando tudo) é coberto
   pela rotina de vivacidade §4.3.
6. **Correção do auditor quebrar o build** — coberta: o executor re-roda os instrumentos
   sobre o diff do auditor antes de encerrar (§4.2.5).
