# Plano — Vocações da Região na Plataforma PNE (V1)

Data: 2026-08-24 (reestruturado em rodadas na mesma data)
Revisão: 2026-08-25 — protocolo de execução v2 (D9), adotado pelo mantenedor após as
Rodadas 0–2 esgotarem os ciclos do v1 sem dupla concordância; v2.1 (D10) na mesma data —
Codex sai do caminho crítico da construção.
Status: aprovado em conversa (sequência, metodologia, cobertura e protocolo de execução
decididos pelo mantenedor)
Antecessores: `docs/PLANO_REORGANIZACAO_PLATAFORMA_V1.md` (Fases 0–6 fechadas; §6 reservou este
trabalho), `docs/FORESIGHT_EDUCACAO_INTEGRACAO_PLATAFORMA_V0_4_0_RC4.md` (gabarito de publicação).

---

## 1. Objetivo e origem

Trazer para a divisão **Análise Regional** da plataforma PNE a análise de cenários das regiões
desenvolvida no projeto Vocações, com foco na educação da região relacionada aos indicadores
socioeconômicos do território. A proposta da gestão define três camadas:

1. **Saída 1 — O que o território ajuda a explicar sobre a educação (PNE → Vocações).**
   Parte de um resultado educacional observado e apresenta variáveis territoriais associadas.
   A plataforma **não afirma causalidade**: aponta fatores associados e hipóteses explicativas,
   sempre com os dados que sustentam a leitura.
2. **Saída 2 — O que o futuro do território exige da educação (Vocações → PNE).**
   Parte das tendências e cenários do território e deriva implicações para o planejamento
   educacional (Ensino Médio, EJA, educação profissional, permanência, metas do PNE).
3. **Camada temporal — transformações simultâneas.** Pares de séries longas mostrando
   co-evolução (demografia × matrículas; emprego/renda × permanência; setores × trajetórias
   formativas), sem inferência causal.

As camadas 1 e 3 são trabalho de dados e curadoria; a camada 2 é o foresight regional.
Essa assimetria define o faseamento (Fase A = camadas 1 e 3 nas 10 regiões; Fase B = cenários).

## 2. Decisões

| # | Decisão | Registro |
|---|---|---|
| D1 | **Sequência: Fase A primeiro.** Dados + leitura associativa + comparação temporal publicados nas 10 regiões antes dos cenários; Fase B corre depois, na camada de pesquisa. | decidido 2026-08-24 |
| D2 | **Metodologia dos cenários regionais: Vocações v1.6 pura** (`SESI\VOCACOES\metodologia\guia_metodologico_cenarios_regionais.md`, contrato `foresight-vocacoes-regionais` v1.6). C1–C4 com perfis fixos, análise morfológica, C4 **normativo** ("ideal técnico provisório"). | decidido 2026-08-24 |
| D3 | Consequência de D2: a regra pública "os quatro cenários têm o mesmo peso" (família `foresight-educacao`) **não vale para o artefato regional**. O contrato `vocacoes-regiao` declara o estatuto de cada cenário (3 exploratórios + 1 normativo) e a página o apresenta com transparência. A regra municipal permanece intacta. | derivado de D2 |
| D4 | **Cobertura da Fase B: Vale do Rio Pardo + 1 região de contraste** (perfil distinto — candidatas: Metropolitana ou Noroeste). Expansão às demais 8 regiões só após veredito de transferibilidade. | decidido 2026-08-24 |
| D5 | **Unidade territorial: as mesmas 10 regiões** já ativas na plataforma (`config/regions/rs.json`), idênticas ao recorte do Vocações (partição exata dos 497 municípios). Nenhum crosswalk novo. Guarda de linguagem vigente (`FORBIDDEN_REGION_TOKENS`) vale para todo texto público novo. | herdada |
| D6 | A relação entre os **Cenários da educação (municipais)** e os regionais é o debate D6 já armado no plano da reorganização — disparado ao fim da Fase B, não antes. | herdada |
| D7 | **Fluxo arquitetural inalterado**: pesquisa produz artefato canônico com manifesto + hash; gerador `.mjs` determinístico transpõe; plataforma valida fail-closed. A plataforma nunca lê a camada de pesquisa em runtime. | invariante |
| D8 | **Protocolo de execução em rodadas com dupla concordância** (§5, v1): Opus 5 high executa cada rodada a partir de contexto limpo; GPT 5.6 xhigh revisa o feito contra o planejado; a rodada só encerra quando os dois concordarem que está conforme este plano. Vigorou nas Rodadas 0–2. | decidido 2026-08-24 |
| D9 | **Protocolo v2 (a partir da R3), substitui o ciclo do D8.** Papéis invertidos: **GPT 5.6 sol xhigh constrói** (via codex-rescue, sempre xhigh); **Opus 5 high orquestra** — escreve specs fechadas, monitora e destrava a execução, verifica por **checklist fechado derivado do Aceite** e julga por instrumento. Sem dupla concordância: encerramento = checklist verde; julgamento vincula só entregáveis; garantia declarada só com prova; achado fora do aceite vira backlog, não bloqueio. Motivo: nas Rodadas 0–2 nenhum encerramento veio por dupla concordância e as maiores fontes de reprovação foram prosa (sobreafirmação de garantia, contradição de documentação), não defeito de entregável. | decidido 2026-08-25 |
| D10 | **Protocolo v2.1 — Codex fora do caminho crítico.** O orquestrador Opus 5 high passa a ser também o **executor**: constrói diretamente, sem esperar job de delegação. O GPT 5.6 sol xhigh vira **consultor adversarial**: consultas pontuais e de escopo fechado (ataque a guardas, revisão de contrato, posição independente), disparadas **em background e em paralelo** ao trabalho do executor, com saída em arquivo; consulta que morrer é reexecutada uma vez ou descartada com registro — nunca bloqueia a rodada. Motivo: sob D9, toda construção esperava um job xhigh lento e sujeito a morrer; a independência entre modelos rende no adversarial, não na construção. | decidido 2026-08-25 |

## 3. Arquitetura do fluxo

```
VOCACOES (dados regionais)          SESI\PNE\foresight\vocacoes-regiao\   PNE-REACT
bases\csv-dashboard\RS\*.csv   →    builder da camada de pesquisa     →   scripts/generate-vocacoes-regiao.mjs
bases\regionalizacao\...            (pacote canônico por região,          → public/data/vocacoes-regiao/
cenarios-agroindustria\01_evid.\     manifesto + sha256 + validador)      → vocacoesRegiaoLoader (fail-closed)
aplicacoes\...\pacote_vocacoes\                                           → VocacoesRegiaoPage
```

Já pronto do lado da plataforma (Fase 6 da reorganização, commit `747b525fe`) e **imutável neste
plano**: manifesto vazio publicado, `vocacoesRegiaoLoader.js` (fábrica compartilhada com o
foresight), `useVocacoesRegiao`, `VocacoesRegiaoPage.tsx`, gate de menu por manifesto, teste de
slot. O que evolui: o contrato do documento (`vocacoes-regiao-1.0.0` → `2.0.0` sem cenários na
Fase A; → `2.1.0` aditivo com cenários na Fase B), o corpo do gerador e os componentes da página.

O diretório de origem `SESI\PNE\foresight\vocacoes-regiao\` **não existe hoje**; criá-lo com
contrato aprovado é a Rodada 1. `resolveSource()` do gerador já recusa origem sem contrato —
essa recusa é o teste de partida.

## 4. O produto: três blocos por região

Um documento por região em `public/data/vocacoes-regiao/regioes/<slug>.json`, com:

1. **Retrato e transformações do território** — séries longas regionais: emprego formal e
   massa salarial (RAIS 2006–2025), setores e ocupações (2006–2025), PIB setorial (2002–2021),
   demografia e envelhecimento (2010–2025), **nascidos vivos por residência da mãe (SINASC,
   1994 em diante; prévias sempre declaradas como prévias)**, **contabilidade de coortes
   censitárias (2010→2022) com saldo migratório aparente de coortes jovens (estimativa
   indireta calculada — ver Rodada 4)**, exportações, eventos climáticos. Fontes: acervo
   regionalizado do Vocações (90 datasets, `bases\csv-dashboard\RS\` + `manifesto_datasets.csv`
   + `dicionario_colunas.csv`) e aquisição estadual SINASC/SIM/CadÚnico (Rodada 2).
2. **Leitura associativa educação ↔ território (Saída 1)** — para cada resultado educacional
   destacado da região (matrículas EM, distorção, permanência, conclusão), os fatores
   territoriais associados com os dados que sustentam a leitura, incluindo o contexto de
   vulnerabilidade social via CadÚnico — sempre como universo cadastral em lente de contexto,
   nunca como população nem como taxa populacional. Cada associação declara interpretação
   permitida e proibida (instrumento herdado do mapa de relações prospectivas do foresight).
   Nunca "X causou Y"; sempre "X e Y observados em conjunto; hipóteses: …".
3. **Comparação temporal (Camada 3)** — pares curados de séries co-evoluindo, com janelas
   idênticas nas duas séries de cada par; janelas mistas apenas em frases separadas.
4. **Cenários da região (Saída 2)** — ausente na Fase A; adicionado na Fase B (`2.1.0`).
   C1–C4 da metodologia Vocações v1.6 com foco educacional, estatuto declarado por cenário
   (D3), implicações para a agenda educacional.

## 5. Protocolo de execução por rodadas (D8, revisto por D9)

**Protocolo v2 — vigente a partir da Rodada 3.** As Rodadas 0–2 correram sob o protocolo
v1 (dupla concordância executor↔revisor, máx. 3 ciclos, cláusulas de arbitragem
adicionadas rodada a rodada); as atas delas são o registro válido daquele regime e devem
ser lidas com as regras da época. O v1 não fechou nenhuma rodada por dupla concordância e
exigiu arbitragem do mantenedor nas três — o v2 transfere a fricção do consenso entre
modelos para instrumentos verificáveis.

**Encerramento da Rodada 2:** suspensa sob o v1 com correções aplicadas e não revisadas
(`NC-C3-1`, `NC-C3-2` e os dois ajustes posteriores autorizados), a R2 encerra-se com a
adoção deste protocolo. A verificação dessas correções entra no checklist da Rodada 3
como **bloco herdado de escopo fechado** — mesma mecânica do carry-over do v1, válida por
uma rodada só.

### 5.1 Papéis (v2.1, D10)

- **Executor-orquestrador — Opus 5 high (Claude)**: conduz e **constrói** a rodada.
  Deriva o checklist de aceite, executa as tarefas diretamente, verifica cada entrega
  contra o checklist com probes e testes, escreve o relatório e encerra a rodada. O
  julgamento é por instrumento, não por opinião — e vale igualmente sobre o que ele
  mesmo construiu.
- **Consultor adversarial — GPT 5.6 sol xhigh** (via plugin Codex, agente `codex-rescue`,
  reasoning xhigh): recebe **consultas pontuais de escopo fechado**, nunca tarefas de
  construção — atacar uma guarda, revisar um contrato/validador, produzir posição
  independente. Consultas rodam **em background, em paralelo** ao trabalho do executor
  (§5.3). Toda saída em arquivo — o job pode morrer sem stdout, e o arquivo é a única
  prova de conclusão.
- **Árbitro — o mantenedor**: gates humanos previstos (GA-3, ratificações), mudanças de
  plano e impasses reais. Não é acionado para fechar rodada normal.

### 5.2 Ciclo da rodada

1. O mantenedor abre a rodada colando o **prompt de abertura** (fim de cada rodada em §6)
   numa sessão nova do orquestrador — **contexto limpo, sem memória de rodadas
   anteriores**. Todo o contexto vem deste plano, do relatório da rodada anterior e dos
   artefatos em disco.
2. O orquestrador deriva da seção **Aceite** da rodada um **checklist fechado**: um item
   por critério, cada um com o instrumento que o prova (probe, teste, hash, comando ou
   inspeção nomeada). O checklist entra no relatório antes da primeira construção e é o
   único juiz do encerramento.
3. Construção **direta pelo executor**, em tarefas delimitadas na ordem que o checklist
   pedir. Nos artefatos de maior risco da rodada (guardas de linguagem, contrato,
   validador), o executor dispara **em background** a consulta adversarial ao consultor
   (§5.3) e segue construindo — o resultado da consulta é incorporado quando chegar.
4. Verificação contínua: a cada entrega, o executor roda os instrumentos do checklist
   que ela cobre. Item FAIL vira correção e re-verificação. **Não há número máximo de
   iterações**: sem consenso a negociar, o critério de parada é o checklist verde.
5. Encerramento: `RELATORIO_RODADA_<NN>.md` no diretório da rodada
   (`.tmp/vocacoes-regiao/rodada-<NN>/` em PNE-REACT, gitignored) com o checklist inteiro
   PASS e a evidência de cada item, caminhos e hashes dos entregáveis, **todo desvio do
   plano declarado com justificativa** (desvio omitido é falha da rodada) e a seção
   **Encerramento** — que substitui a ata separada do v1. Achado fora do checklist vira
   item nomeado de **backlog** no relatório: insumo da rodada seguinte, nunca bloqueio
   desta.
6. Desvio aceito que **altera o plano** exige edição deste documento na própria rodada
   (seção afetada + linha na tabela de decisões, se for decisão nova). Mudança silenciosa
   de plano segue sendo falha automática.
7. Sobem ao mantenedor apenas: os gates humanos previstos na rodada, desvio que altere
   este plano, e impasse real — um item de aceite impossível de cumprir como escrito.

### 5.3 Consultas adversariais (fora do caminho crítico)

- **Uma consulta por chamada; saída sempre em arquivo.** Sem arquivo, a consulta não
  aconteceu — parecer nunca é inventado a partir de stdout parcial.
- **Sempre em background, sempre em paralelo.** O executor dispara a consulta e continua
  construindo; nenhuma tarefa da rodada espera o consultor. Consultas independentes
  podem rodar simultaneamente.
- **Trava não suspende nada.** Consulta morta ou sem saída no tempo esperado: reexecutar
  **uma vez**, com escopo igual ou reduzido. Na segunda falha, a consulta é **descartada
  com registro no relatório** — o item que ela cobriria é verificado pelos instrumentos
  do executor, e a ausência da segunda opinião fica declarada, não escondida.
- **Consulta é insumo, não veredito.** O achado do consultor entra no checklist (se
  refutar uma garantia) ou no backlog (se for melhoria fora do aceite). Não existe ciclo
  de concordância.
- **Quando consultar:** recomendada uma consulta adversarial por rodada sobre o artefato
  de maior risco (guarda de linguagem nova, contrato novo, validador alterado); rodadas
  sem artefato dessa classe podem fechar sem consulta, com a dispensa registrada.

### 5.4 Regras de convergência (o que o v2 muda do v1)

1. **O julgamento vincula entregáveis, não prosa.** Defeito em relatório ou documentação
   da rodada é corrigido e registrado — nunca reabre a rodada nem gera ciclo.
2. **Checklist fechado, derivado literalmente do Aceite.** Nada fora dele bloqueia o
   encerramento; achado novo vira backlog nomeado.
3. **Garantia declarada só com prova.** O relatório afirma apenas o que um probe/teste
   prova, com referência ao instrumento; sem prova, escreve "não provado". As duas
   maiores fontes de reprovação das Rodadas 1–2 foram sobreafirmação de garantia e
   contradição interna de documentação — a conferência mecânica de números do relatório
   (padrão `probe-coerencia-docs.py` da R2) roda antes do encerramento de toda rodada.
4. **Correção textual é self-service.** Aplicada, registrada, seguida em frente.
5. **Instrumento novo verifica-se por injeção.** Probe que nunca reprovou nada não provou
   nada: todo probe novo demonstra que acusa o defeito que diz pegar (lição da R2).

### 5.5 Regras transversais de qualidade (valem em toda rodada)

- Reprovação de um item do checklist não é fracasso — é o instrumento funcionando.
  Relatórios reportam falhas e limitações com o output real (testes que falharam, fontes
  indisponíveis).
- Builders e geradores: determinísticos, sem rede/relógio/modelo no caminho de geração,
  escrita atômica, `--check` comparando disco × gerado, reexecução com hash estável.
- Linguagem pública: sem causalidade, sem token interno (ids E/F/H/N/S/C, nomes
  institucionais do recorte, enums de processo), sem número atribuído a ano futuro,
  prévia nunca como observado, CadÚnico sempre com universo declarado.
- Promoções ao canônico: manifesto com hash origem+destino, pré-voo sem colisão, aditivo.
- **Guardas de linguagem natural — critério de aceite por corpus, não por completude**
  (arbitragem da Rodada 1): o aceite de uma guarda é (a) **corpus de regressão bilateral
  versionado** — todo ataque encontrado em qualquer ciclo vira fixture permanente, e todo
  texto honesto barrado indevidamente vira fixture também; a guarda deve recusar 100% do
  corpus de ataques e aceitar 100% do corpus honesto; e (b) **furos conhecidos ainda não
  fechados declarados** junto à guarda. "Nenhum furo desconhecido" **não** é critério de
  aceite: furo novo achado depois é item de trabalho novo, não reprovação retroativa da
  rodada. A guarda é uma camada de defesa — o orquestrador e as revisões humanas (GA-3)
  continuam sendo a rede semântica; falso positivo sobre limitação honesta é defeito tão
  grave quanto falso negativo.

## 6. Rodadas

Mapa geral: R0 pré-requisito · R1–R5 = Fase A · R6–R9 = Fase B · R10 = Fase C.

**Estado (2026-08-25):** R0–R2 executadas e encerradas sob o protocolo v1 — os textos e
prompts delas abaixo são registro histórico e não devem ser reexecutados; as referências a
"revisor", "dupla concordância" e §5.2.8–10 nessas três rodadas remetem ao §5 da versão
anterior deste documento, preservado nas atas. A partir da R3 vale o protocolo v2.1 (§5).

---

### Rodada 0 — Fechamento da reorganização (pré-requisito)

**Objetivo:** concluir a Fase 7 de `docs/PLANO_REORGANIZACAO_PLATAFORMA_V1.md` e mergear
`reorg/menus-e-regional` em `main`. Este plano trabalha sobre o slot criado naquele branch.

**Tarefas:** suíte integral (`npm run test:unit`, `test:foresight`, `test:regional`,
`test:vocacoes-regiao`, `check:*`), revisão do diff acumulado do branch, navegação manual
RS + AL, atualização de docs pendentes, merge. Falhas pré-existentes já conhecidas
(`check:hygiene`, `pne-frontend-ux.test.mjs`) são registradas, não caçadas aqui.

**Aceite:** branch mergeado; nenhuma regressão nova; relatório com o resultado real da suíte.

**Prompt de abertura (colar no Opus 5 high, sessão nova):**
```text
Leia docs/PLANO_VOCACOES_REGIAO_V1.md (§1–§5 e a Rodada 0 do §6) e
docs/PLANO_REORGANIZACAO_PLATAFORMA_V1.md (Fase 7). Execute a Rodada 0 conforme o
protocolo do §5: execute, relate em .tmp/vocacoes-regiao/rodada-00/, submeta o dossiê
ao revisor GPT 5.6 xhigh via codex-rescue, itere até dupla concordância (máx. 3 ciclos)
e escreva a ata. Não inicie a rodada seguinte.
```

---

### Rodada 1 — Fundação da origem canônica

**Objetivo:** criar `SESI\PNE\foresight\vocacoes-regiao\` — a origem que o gerador da
plataforma hoje recusa por não existir.

**Entradas:** `config/regions/rs.json` (PNE-REACT);
`SESI\VOCACOES\bases\regionalizacao\regioes_fiergs_2026.xlsx` + `README.md`;
`SESI\PNE\foresight\base_conhecimento\07_contratos_validadores\` (padrão de contrato).

**Tarefas:**
1. Registro canônico das 10 regiões (slug, nome público, uf, municípios com ibge7,
   `municipalityCount`), derivado dos dois recortes com verificação de partição exata
   (497 municípios, sem sobra/duplicata) e hash do registro.
2. Contrato `vocacoes-regiao-pesquisa-v0.1` (JSON Schema): estrutura do pacote por região
   com os blocos do §4, conjunto **fechado** de campos, classes de evidência
   (`observed/calculated/...`), campos de universo/prévia, interpretação permitida/proibida
   por associação.
3. `README.md` da fronteira: o que o builder pode ler, o que nunca publica (tokens internos,
   colunas `regiao_fiergs`, ids de dataset), relação com o gerador da plataforma.
4. Validador do pacote (script determinístico) + teste com fixture mínima.

**Aceite:** diretório criado com registro + contrato + validador; validador recusa fixture
com campo desconhecido, token interno e número futuro; partição das 10 regiões verificada.

**Prompt de abertura:**
```text
Leia docs/PLANO_VOCACOES_REGIAO_V1.md (§1–§5 e Rodada 1 do §6) e a ata da Rodada 0 em
.tmp/vocacoes-regiao/rodada-00/. Execute a Rodada 1 conforme o protocolo do §5: crie a
origem canônica em C:\Users\rnbirck\PROJETOS\SESI\PNE\foresight\vocacoes-regiao\, relate
em .tmp/vocacoes-regiao/rodada-01/, submeta ao revisor GPT 5.6 xhigh via codex-rescue,
itere até dupla concordância (máx. 3 ciclos) e escreva a ata. Não inicie a rodada seguinte.
```

---

### Rodada 2 — Aquisição estadual SINASC / SIM / CadÚnico

**Objetivo:** adquirir, para os 497 municípios do RS, as fontes que a rodada 5C do foresight
municipal adquiriu para 3 pilotos — na mesma disciplina, em escala estadual.

**Entradas (gabarito):** `.tmp\foresight-5c\` (PNE-REACT) — em especial
`insumos\fontes\MANIFESTO_AQUISICAO_5C.json`, os scripts de aquisição e o schema de séries
v0.5.1. A aquisição é **independente da promoção canônica da 5C** (pendente): reusa método
e scripts como referência, não os artefatos municipais em staging.

**Item herdado da Rodada 1 (§5.2.10):** a Rodada 1 foi encerrada por arbitragem **com
verificação transferida**. O dossiê desta rodada deve submeter, como bloco separado do
material próprio, as **três correções do ciclo delta da R1** ainda não revisadas — guarda de
unicidade da tabela de grafia; reclassificação H-18→A-23 com `seriesKind` no corpus; ataques
A-24…A-30 — com os probes que as provam. O parecer responde aos dois blocos separadamente.
Item herdado NÃO CONFORME é não conformidade **desta** rodada. Detalhes e caminhos:
`.tmp/vocacoes-regiao/rodada-01/ATA_ENCERRAMENTO_RODADA_01.md`.

**Tarefas:**
1. **SINASC** (TABNET/DATASUS, `nvrs.def` RS): nascidos vivos por residência da mãe, por
   município, desde 1994. Finais vs prévias conforme a regra da 5C (prévia nunca vira
   `observed`; valor de prévia em campo próprio).
2. **SIM** (TABNET/DATASUS): óbitos por residência e idade (insumo da contabilidade de
   coortes da Rodada 4), mesma disciplina.
3. **CadÚnico** (API MI Social/SAGI): famílias/pessoas cadastradas e perfil, mensal
   2012–presente, por município, com `universe` declarado por série.
4. Manifesto de aquisição estadual: sha256 + URL + parâmetros + timestamp por resposta bruta.
5. Agregação regional por soma (fluxos e contagens são aditivos), gravada como séries
   regionais no formato do contrato v0.1 da Rodada 1.

**Aceite:** manifesto de aquisição completo e reproduzível; séries regionais das 10 regiões
para as três fontes validadas pelo validador da Rodada 1; lacunas de fonte documentadas sem
proxy inventado (CECAD/IVCAD permanecem fora — classe não reproduzível, como na 5C). Acresce
ao aceite o **item herdado da R1**: parecer explícito sobre as três correções do ciclo delta.

**Instrumentos de prova (lição da R1):** o dossiê declara, para cada artefato de verificação
que a rodada produzir (corpus, tabela, fixture, probe), **quais garantias ele mesmo oferece e
quais não oferece**. Na R1, dois dos três achados substantivos do delta estavam dentro dos
próprios instrumentos de prova.

**Prompt de abertura:**
```text
Leia docs/PLANO_VOCACOES_REGIAO_V1.md (§1–§5 e Rodada 2 do §6) e a ata da Rodada 1 em
.tmp/vocacoes-regiao/rodada-01/ATA_ENCERRAMENTO_RODADA_01.md — a R1 foi encerrada por
arbitragem com verificação transferida (§5.2.10), e o item herdado entra no dossiê desta
rodada como bloco separado. Execute a Rodada 2 conforme o protocolo do §5: aquisição
estadual SINASC/SIM/CadÚnico com manifesto, relate em .tmp/vocacoes-regiao/rodada-02/,
submeta ao revisor GPT 5.6 xhigh via codex-rescue (material próprio + item herdado, com
parecer separado para cada), itere até dupla concordância (máx. 3 ciclos) e escreva a ata.
Não inicie a rodada seguinte.
```

---

### Rodada 3 — Builder do pacote regional (Bloco 1)

**Objetivo:** builder determinístico na camada de pesquisa que materializa o Bloco 1
(retrato e transformações do território) das 10 regiões.

**Entradas:** `SESI\VOCACOES\bases\csv-dashboard\RS\` (90 datasets + `manifesto_datasets.csv`
+ `dicionario_colunas.csv` + `metodologia_agregacao_regional.csv`);
`SESI\VOCACOES\cenarios-agroindustria\01_evidencias\historico_demografia_educacao_regioes_2010_2025.csv`;
`public/data/regioes/<slug>.json` (educação regional já publicada — pesquisa pode ler o
publicado; o inverso é proibido); séries da Rodada 2.

**Bloco herdado da Rodada 2 (§5, encerramento):** verificar as correções aplicadas após o
último parecer da R2 — proibição de layout por classe Unicode (`NC-C3-1`,
`probe-layout-unicode.py`), coerência da documentação (`NC-C3-2`,
`probe-coerencia-docs.py`), e os dois ajustes posteriores (probe de coerência como gate;
quinta porta do builder, matriz × séries, verificada por injeção). Itens de escopo fechado
no checklist desta rodada; herança de uma rodada só. Detalhes:
`.tmp/vocacoes-regiao/rodada-02/ATA_ENCERRAMENTO_RODADA_02.md`.

**Tarefas:**
1. Seleção inicial de séries por bloco em **arquivo de configuração versionado** (não em
   código), com fonte, período e regra de agregação por série.
2. Builder: agregações regionais; taxas só por soma de numeradores sobre soma de
   denominadores (regra herdada do contrato do foresight municipal); Ideb/Saeb/INSE **fora**,
   com limitação declarada no pacote.
3. Saída: 10 pacotes JSON (Bloco 1 preenchido; Blocos 2–3 vazios-válidos) + manifesto com
   sha256 por arquivo + relatório de validação.
4. Reexecução com hash estável (prova de determinismo).

**Aceite:** 10 pacotes validados pelo validador da Rodada 1; hash estável em reexecução;
nenhum token interno; toda série com fonte, período e regra de agregação rastreáveis à
configuração.

**Prompt de abertura:**
```text
Leia docs/PLANO_VOCACOES_REGIAO_V1.md (§1–§5 e Rodada 3 do §6) e a ata da Rodada 2 em
.tmp/vocacoes-regiao/rodada-02/ATA_ENCERRAMENTO_RODADA_02.md. Execute a Rodada 3 conforme
o protocolo v2.1 (§5): derive o checklist de aceite (incluindo o bloco herdado da R2),
construa o builder do Bloco 1 diretamente, dispare em background a consulta adversarial
ao GPT 5.6 sol xhigh via codex-rescue sobre o artefato de maior risco (§5.3), verifique
cada item com os instrumentos do checklist, relate em .tmp/vocacoes-regiao/rodada-03/ e
encerre com o checklist verde. Não inicie a rodada seguinte.
```

---

### Rodada 4 — Curadoria: associações, pares temporais e migração de coortes

**Objetivo:** preencher os Blocos 2 e 3 das 10 regiões e promover os pacotes ao canônico.

**Tarefas:**
1. **Catálogo de associações por região** (Saída 1): resultado educacional → fatores
   territoriais associados, cada um com séries de sustentação, interpretação
   permitida/proibida e limitações. CadÚnico entra como contexto de vulnerabilidade
   (universo cadastral; proibido derivar "taxa da população").
2. **Catálogo de pares temporais** (Camada 3). Pontos de partida: demografia jovem ×
   matrículas EM; vínculos por escolaridade × permanência; setores em expansão/retração ×
   matrículas técnicas por eixo; **nascimentos defasados × matrículas por etapa (nascidos em
   t × pré-escola em t+4, fundamental em t+6, EM em t+15) — só defasagens históricas: as
   duas pontas do par em anos já observados; coorte menor já nascida vira direção
   qualitativa, nunca número futuro.**
3. **Migração de jovens em dois níveis:**
   a. **Saldo migratório aparente de coortes (classe `calculated`)**: nascidos da coorte
      (SINASC) − óbitos da coorte (SIM) vs contagem da mesma coorte nos Censos 2010→2022.
      Resíduo da equação de coortes; mais robusto na escala regional. Publicado com nota de
      método e rótulo próprio — **nunca** como fluxo migratório observado.
   b. **Tarefa de verificação (não promessa)**: módulo de migração da amostra do Censo 2022
      no SIDRA, por município e idade. Se existir no grão necessário, âncora observada
      pontual; se não, limitação declarada e o nível (a) permanece sozinho.
   c. Proxies existentes (contração da base jovem) seguem válidos como leitura complementar,
      nomeados como proxy.
4. **Promoção canônica**: pacotes completos promovidos a
   `SESI\PNE\foresight\vocacoes-regiao\` com manifesto de promoção (hash origem+destino,
   pré-voo sem colisão).
5. **Revisão humana amostral** (gate GA-3): 2 regiões sorteadas — nenhuma frase causal,
   toda associação com dado de sustentação visível. O executor prepara o material; o
   mantenedor executa a leitura antes do encerramento da rodada.

**Aceite:** 10 pacotes completos e promovidos; validador verde; estimativa de migração com
classe `calculated` e nota de método; nenhum par temporal com janelas mistas na mesma frase;
GA-3 realizado.

**Prompt de abertura:**
```text
Leia docs/PLANO_VOCACOES_REGIAO_V1.md (§1–§5 e Rodada 4 do §6) e o relatório da Rodada 3
em .tmp/vocacoes-regiao/rodada-03/. Execute a Rodada 4 conforme o protocolo v2.1 (§5):
Blocos 2 e 3 das 10 regiões + estimativa de migração de coortes + promoção canônica,
construção direta com verificação por checklist e consulta adversarial em background
(§5.3); acione o mantenedor para a revisão amostral GA-3 antes do encerramento e relate
em .tmp/vocacoes-regiao/rodada-04/. Não inicie a rodada seguinte.
```

---

### Rodada 5 — Plataforma: contrato 2.0.0, gerador e página (estreia das 10 regiões)

**Objetivo:** publicar a Fase A na plataforma.

**Entradas:** origem canônica promovida (Rodada 4);
`docs/FORESIGHT_EDUCACAO_INTEGRACAO_PLATAFORMA_V0_4_0_RC4.md` (gabarito);
`scripts/generate-vocacoes-regiao.mjs`, `src/features/vocacoes-regiao/*`,
`scripts/checks/vocacoes-regiao-slot.test.mjs`.

**Tarefas:**
1. `documentSchemaVersion` → `vocacoes-regiao-2.0.0`: blocos 1–3, **sem** cenários, conjunto
   de campos fechado (padrão `matriz-4.0.0`).
2. `generate-vocacoes-regiao.mjs`: implementar `buildPublication()` — reconferir hashes da
   origem, transpor, validar linguagem pública (incluindo as regras novas: prévia rotulada,
   universo CadÚnico, qualificador de estimativa na migração), escrita atômica; `--check`.
3. Loader: estender a validação da fábrica ao novo conjunto de campos; política de
   visibilidade e gate de menu inalterados.
4. Página: componentes dos blocos 1–3 (séries, associações com "dados que sustentam",
   pares temporais). `ForesightScenarioReport` fica reservado à Fase B.
5. Rotas novas nomeadas em `ADDED_ROUTES`; testes de slot atualizados; teste de mutação
   provando fail-closed (região sem pacote válido some do menu).
6. Publicar: `npm run generate:vocacoes-regiao` + `check` + suíte.

**Aceite (gates GA-1 e GA-2):** 10 regiões publicadas e navegáveis; `generate`+`check`+testes
verdes; fail-closed comprovado por mutação; nenhuma série com token interno ou número futuro;
prévia SINASC nunca `observed`; CadÚnico com universo; migração com classe `calculated`.

**Prompt de abertura:**
```text
Leia docs/PLANO_VOCACOES_REGIAO_V1.md (§1–§5 e Rodada 5 do §6) e o relatório da Rodada 4
em .tmp/vocacoes-regiao/rodada-04/. Execute a Rodada 5 conforme o protocolo v2.1 (§5):
contrato 2.0.0 + gerador + página + testes + publicação das 10 regiões, construção direta
com verificação por checklist e consulta adversarial em background sobre o contrato
2.0.0 (§5.3), relate em .tmp/vocacoes-regiao/rodada-05/ e encerre com o checklist verde.
Não inicie a rodada seguinte.
```

---

### Rodada 6 — Fase B, abertura metodológica

**Objetivo:** instanciar a metodologia Vocações v1.6 para o domínio focal educação e escolher
a região de contraste.

**Entradas:** `SESI\VOCACOES\metodologia\guia_metodologico_cenarios_regionais.md` (v1.6) +
`contrato_metodologia.json`; templates TSV em
`metodologia\skills\construir-plataforma-vocacoes\assets\templates\pacote_minimo\`.

**Tarefas:**
1. Instanciar o pacote técnico (templates TSV) com domínio focal educação: as 6 dimensões do
   sistema regional permanecem; diagnóstico e implicações concentrados em educação, usando os
   módulos versionados `trajetorias_trabalho_educacao` (v1.0) e
   `compatibilidade_trabalho_educacao` (v1.1, nível B no máximo — recomendação de curso
   exigiria nível C, fora de escopo).
2. Escolher a região de contraste (Metropolitana ou Noroeste) com justificativa de perfil
   escrita — decisão ratificada pelo mantenedor no encerramento.
3. Registrar as salvaguardas transversais que valem mesmo sob v1.6 pura: sem probabilidade,
   sem projeção numérica futura, matrículas × vínculos nunca como balanço de oferta e demanda,
   horizonte t0→t+5 (2026→2031) com varredura separada.

**Aceite:** pacote instanciado e validado pelo validador da metodologia
(`validar_pacote_plataforma.py`); contraste escolhido e justificado; salvaguardas registradas.

**Prompt de abertura:**
```text
Leia docs/PLANO_VOCACOES_REGIAO_V1.md (§1–§5 e Rodada 6 do §6) e o relatório da Rodada 5
em .tmp/vocacoes-regiao/rodada-05/. Execute a Rodada 6 conforme o protocolo v2.1 (§5):
instancie a metodologia Vocações v1.6 com foco educacional e proponha a região de
contraste, construção direta com verificação por checklist e consulta adversarial em
background quando couber (§5.3); obtenha a ratificação do mantenedor para o contraste
antes do encerramento e relate em .tmp/vocacoes-regiao/rodada-06/. Não inicie a rodada
seguinte.
```

---

### Rodada 7 — Cenários do Vale do Rio Pardo (aproveitamento)

**Objetivo:** reorientar o foresight regional completo do VRP para o domínio educacional e
prepará-lo no formato do contrato regional.

**Entradas:** `SESI\VOCACOES\aplicacoes\vocacoes-regionais\dados\vale-do-rio-pardo\pacote_vocacoes\`
(`status_foresight=completo`, maturidade `tecnico_nao_participativo`);
`SESI\VOCACOES\analises-extras\vale-do-rio-pardo\` (inclusive `PMEs_Vale_do_Rio_Pardo.md`).

**Tarefas:** reorientar a narrativa dos 4 cenários para educação (não reconstruir a
morfologia); derivar as implicações educacionais por cenário; transpor ao formato do bloco de
cenários do contrato regional (estatuto por cenário, C4 como "ideal técnico provisório" com
condições de realização e critérios N01–N05 em linguagem pública); nenhuma afirmação de
trajetória pode contradizer os números citados (o defeito da rodada 4F do foresight municipal
vira teste aqui).

**Aceite (gate GB-1):** pacote VRP no formato regional validado; afirmações de trajetória
conferidas contra as séries; linguagem pública limpa.

**Prompt de abertura:**
```text
Leia docs/PLANO_VOCACOES_REGIAO_V1.md (§1–§5 e Rodada 7 do §6) e o relatório da Rodada 6
em .tmp/vocacoes-regiao/rodada-06/. Execute a Rodada 7 conforme o protocolo v2.1 (§5):
reoriente os cenários do Vale do Rio Pardo para o domínio educacional no formato do
contrato regional, construção direta com verificação por checklist e consulta adversarial
em background sobre a linguagem pública dos cenários (§5.3), relate em
.tmp/vocacoes-regiao/rodada-07/ e encerre com o checklist verde. Não inicie a rodada
seguinte.
```

---

### Rodada 8 — Cenários da região de contraste (construção completa)

**Objetivo:** executar as 8 etapas do guia v1.6 (`Preparar → … → Acompanhar`) para a região
escolhida na Rodada 6, com gate por etapa.

**Entradas:** dados regionais já existentes (csv-dashboard + evidências do exercício
agroindústria onde couber + pacotes da Fase A); pacote instanciado da Rodada 6.

**Tarefas:** as 8 etapas com seus gates internos; análise morfológica (fatores × estados,
caixa, eliminação de combinações, seleção dos 4); títulos regionais próprios; **teste de
intercambialidade**: os cenários do contraste não podem ser intercambiáveis com os do VRP
(teste de troca de território, como nas rodadas 4E–4G do foresight municipal — teste cego de
identificação por realidade).

**Aceite (gate GB-2):** 4 cenários completos com esqueleto fixado antes da narrativa;
intercambialidade zero no teste cego; memória técnica auditável (evidências, fatores,
hipóteses, sinais com ids internos — que nunca chegam ao público).

**Prompt de abertura:**
```text
Leia docs/PLANO_VOCACOES_REGIAO_V1.md (§1–§5 e Rodada 8 do §6) e o relatório da Rodada 7
em .tmp/vocacoes-regiao/rodada-07/. Execute a Rodada 8 conforme o protocolo v2.1 (§5):
construa os 4 cenários da região de contraste pelas 8 etapas do guia v1.6, com teste de
intercambialidade contra o VRP; o teste cego de identificação pode usar o GPT 5.6 sol
xhigh como juiz independente (consulta em background, §5.3). Verificação por checklist,
relatório em .tmp/vocacoes-regiao/rodada-08/, encerramento com o checklist verde. Não
inicie a rodada seguinte.
```

---

### Rodada 9 — Publicação dos cenários (contrato 2.1.0)

**Objetivo:** publicar os cenários das duas regiões na plataforma.

**Tarefas:**
1. Contrato `vocacoes-regiao-2.1.0` (aditivo sobre 2.0.0): bloco de cenários com campo de
   estatuto por cenário; `schema.json` da família declara as regras públicas próprias —
   distintas da família municipal (D3); nota de leitura na página explicando a diferença de
   estatuto do C4.
2. Promoção canônica dos pacotes de cenários (manifesto hash origem+destino).
3. Gerador + loader + página estendidos ao bloco de cenários (reaproveitando
   `ForesightScenarioReport` no que couber); testes.
4. Publicar VRP + contraste; as demais 8 regiões permanecem com blocos 1–3 apenas — o
   documento declara a ausência de cenários de forma verificável, não silenciosa.

**Aceite (gates GB-3 e GB-4):** linguagem pública com zero tokens internos e zero causalidade;
estatuto do C4 explícito; promoção com manifesto íntegro; suíte verde; regiões sem cenário
continuam válidas no contrato.

**Prompt de abertura:**
```text
Leia docs/PLANO_VOCACOES_REGIAO_V1.md (§1–§5 e Rodada 9 do §6) e o relatório da Rodada 8
em .tmp/vocacoes-regiao/rodada-08/. Execute a Rodada 9 conforme o protocolo v2.1 (§5):
contrato 2.1.0 + promoção + publicação dos cenários de VRP e contraste, construção direta
com verificação por checklist e consulta adversarial em background sobre o contrato
2.1.0 (§5.3), relate em .tmp/vocacoes-regiao/rodada-09/ e encerre com o checklist verde.
Não inicie a rodada seguinte.
```

---

### Rodada 10 — Debate D6 e decisão de expansão

**Objetivo:** decidir (a) o papel dos Cenários da educação municipais após a estreia dos
regionais (coexistência, aposentadoria ou reposicionamento) e (b) se/como expandir os
cenários às 8 regiões restantes.

**Formato:** debate estruturado — o orquestrador prepara o dossiê (estado publicado,
tensões D3, custo de expansão), o construtor (GPT 5.6 sol xhigh) produz posição
independente em arquivo, o orquestrador confronta as duas e entrega ao mantenedor uma
recomendação com as divergências explícitas. **A decisão é do mantenedor**; a rodada
encerra com a decisão registrada neste plano (tabela de decisões).

**Prompt de abertura:**
```text
Leia docs/PLANO_VOCACOES_REGIAO_V1.md (§1–§5 e Rodada 10 do §6) e o relatório da Rodada 9
em .tmp/vocacoes-regiao/rodada-09/. Execute a Rodada 10 conforme o protocolo v2.1 (§5):
prepare o dossiê do debate D6 + expansão, obtenha a posição independente do GPT 5.6 sol
xhigh via codex-rescue (consulta em background, saída em arquivo, §5.3 — prepare o
dossiê enquanto ela roda), confronte as posições e entregue a
recomendação ao mantenedor com as divergências explícitas. A rodada encerra com a decisão
do mantenedor registrada no plano.
```

---

## 7. Inventário de dados (referência rápida)

| Bloco | Fonte principal | Período |
|---|---|---|
| Emprego, setores, ocupações, escolaridade dos vínculos, remuneração | RAIS via `bases\csv-dashboard\RS\037–058` | 2006–2025 |
| PIB regional e setorial | `059–061` | 2002–2023 |
| Demografia, envelhecimento | `004–008` + Censos 2010/2022 + estimativas | 2010–2025 |
| Demografia × matrículas (pronto) | `cenarios-agroindustria\01_evidencias\historico_demografia_educacao_regioes_2010_2025.csv` | 2010–2025 |
| Educação regional (cobertura, matrículas) | `public/data/regioes/<slug>.json` (7 indicadores + séries) | 2014–2025 |
| Exportações | `002` + históricos por complexo | 1997–2025 |
| Eventos climáticos | `036` (Atlas de Desastres) | 1991–2024 |
| Nascidos vivos por residência | SINASC via TABNET/DATASUS (Rodada 2) | 1994–presente (prévias declaradas) |
| Óbitos por idade (insumo de coortes) | SIM via TABNET/DATASUS (Rodada 2) | conforme aquisição |
| Vulnerabilidade social (contexto) | CadÚnico via API MI Social/SAGI (Rodada 2) | 2012–presente (mensal) |
| Coortes censitárias e saldo migratório aparente | SINASC + SIM + Censos 2010/2022 (calculado) | pontos censitários 2010→2022 |
| Cenários (VRP) | `aplicacoes\vocacoes-regionais\dados\vale-do-rio-pardo\pacote_vocacoes\` | t0 2026 → 2031 |

Exclusões e limitações declaradas: Ideb/Saeb/INSE (não agregam regionalmente sem microdados);
migração de jovens sem fluxo observado — coberta por estimativa indireta de coortes +
verificação do módulo do Censo 2022 (Rodada 4), nunca apresentada como fluxo; CECAD/IVCAD
(fontes não reproduzíveis, mesma classe da rodada 5C); fluxo escolar regional além do que a
plataforma já publica (fora da v1, como no Panorama).

## 8. Riscos e salvaguardas

1. **Causalidade implícita** — o risco central do produto. Mitigação: contrato de associação
   com interpretação permitida/proibida por item + validador de linguagem + revisão GA-3.
2. **Média regional lida como condição uniforme** — doutrina Vocações: agregado nunca é
   condição uniforme; onde a heterogeneidade interna for alta, o documento a declara
   (contagem de municípios no dado, como o `municipiosComDado` do Panorama).
3. **C4 normativo × regra municipal "mesmo peso"** — resolvido por D3 (regras públicas por
   família), mas exige nota de leitura clara e retorna no debate D6 (Rodada 10).
4. **Texto genérico entre regiões** — teste de intercambialidade (Rodada 8) desde o primeiro
   par de regiões.
5. **Tokens internos do recorte regional** — guarda dupla (pesquisa + plataforma) já ativa.
6. **Períodos heterogêneos entre séries** — cada par temporal declara sua janela; janelas
   diferentes nunca na mesma frase.
7. **Estimativa indireta lida como fluxo observado** — o saldo migratório aparente de coortes
   é resíduo calculado, sensível a erro censitário e de registro. Mitigação: classe de
   evidência `calculated` visível, nota de método no documento, e validador de linguagem
   recusando "migração observada"/"jovens que saíram" sem o qualificador de estimativa.
8. **CadÚnico lido como população** — universo cadastral varia com política de cadastramento;
   série pode refletir mutirão, não mudança social. Mitigação: `universe` declarado por série,
   lente de contexto, e nunca dividir CadÚnico por população para produzir "taxa".
9. **Prévia SINASC lida como dado final** — anos recentes são prévias sujeitas a revisão.
   Mitigação: regra da 5C (prévia nunca vira `observed`; valor de prévia em campo próprio,
   rotulado na página).
10. **Risco do próprio protocolo (D9/D10)** — no v2.1, quem constrói também escreve o
    checklist e julga: risco de autoverificação complacente. Mitigação: o checklist
    deriva literalmente da seção Aceite escrita neste plano, que o executor não altera
    sozinho (§5.2.6); garantia só com prova e probes verificados por injeção (§5.4);
    consulta adversarial do GPT 5.6 sol xhigh sobre o artefato de maior risco de cada
    rodada (§5.3); revisão humana GA-3 mantida como rede semântica. Risco simétrico:
    consulta que trava — coberta pelo §5.3 (retry único, depois descarte registrado;
    nunca vira impasse).

## 9. Sequência e dependências

```
R0 (merge reorg) → R1 → R2 → R3 → R4 → R5  [Fase A publicada: 10 regiões, blocos 1–3]
                                   → R6 → R7 → R8 → R9  [Fase B: cenários VRP + contraste]
                                                  → R10 [D6 + expansão]
```

- Cada rodada começa em sessão nova do orquestrador Opus 5 high (contexto limpo), com o
  prompt de abertura da rodada. Nenhuma rodada depende de memória de conversa — só deste
  plano, dos relatórios/atas anteriores e dos artefatos em disco.
- R6 pode, a critério do mantenedor, abrir em paralelo a R4–R5 (trabalho de pesquisa que
  não toca a plataforma); R7+ dependem de R6; R9 depende de R5 (contrato 2.0.0 publicado).
- Alterações neste plano só dentro de rodadas, como desvio declarado e aceito (§5.2.6),
  ou por decisão direta do mantenedor registrada na tabela de decisões.
