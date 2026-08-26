# Plano — Vocações da Região V5: relações fortes, leitura leve

Data: 2026-08-26
Status: **aprovado para execução** (pedido do mantenedor, 2026-08-26; protocolo v4 do V3, §4).
Origem: diagnóstico medido da página (2026-08-26) + decisão do mantenedor: a página deve
trazer **apenas relações fortes e indicativas**, com riqueza de análise e insights por
região — as relações fracas saem da leitura — e o layout deve ser **leve, objetivo e
interessante**, no lugar do atual (19.001px de altura no Vale do Sinos, texto a 35% da
largura útil, 61% da página em pilhas de frases de template).
Sucede o **V3** (`docs/PLANO_VOCACOES_REGIAO_V3.md`): R0–R2 executadas (R2 verificada
C1–C8; GA humano, commits e relatório pendentes — fecham na R0 daqui); as R3–R4 do V3
são absorvidas nas R4–R5 daqui.
Absorve o **V4** (`docs/PLANO_VOCACOES_REGIAO_V4.md`, rascunho nunca aprovado): o grau
E2 (relação contábil) entra neste plano como rodada própria; E3–E5 permanecem
condicionais à decisão V4-P1 da gestão e ficam no backlog (§6).
Referência visual: **mockup aprovado como direção** —
https://claude.ai/code/artifact/74847d52-00fd-42e8-b39f-af993c8e4b91 (dados reais do
Vale do Sinos, contrato 2.6.0).

---

## 1. A tese do plano

O V1–V3 construíram uma camada associativa honesta; o custo foi uma página exaustiva:
toda relação computada vira frases na tela, tenha força ou não (a correlação de −0,01
ganha o mesmo espaço da de −0,71). O V5 inverte o critério de publicação:

1. **Editorial por força**: a página lidera com as relações **moderadas e fortes** de
   cada região — cada região com o seu conjunto próprio, achado nos seus dados — mais as
   relações **estruturais** (defasagem demográfica declarada), que valem pelo mecanismo
   e não pelo coeficiente. As fracas saem da leitura.
2. **Foco no PNE**: toda relação publicada parte de um resultado educacional e aponta
   os indicadores e temas do novo PNE que ela toca (a ponte da matriz municipal já
   existe, contrato 2.3.0); as demais variáveis do território (emprego, renda, setores,
   demografia, CadÚnico, PIB) entram como fatores da análise, nunca como fim.
3. **Um grau novo de linguagem**: a decomposição contábil (E2) libera "explica X p.p."
   na forma decomposta — aritmética visível, não inferência — defensável sob a regra de
   ouro atual da gestão (o próprio V4 §6.3 registra isso).
4. **A página do mockup**: hero com números-síntese, escada de evidência visível,
   cartões de relação compactos em grade, triagem em lista, retrato como camada de
   consulta. Meta: ~19.000px → ≤ 7.000px sem perder nenhuma guarda.

## 2. Decisões

| # | Decisão | Registro |
|---|---|---|
| V5-D1 | **Protocolo v4 do V3 mantido** (§4 do V3): Fable arquiteta/orquestra/verifica e é o gate; GPT 5.6 sol xhigh (`gpt-5.6-sol`, xhigh, `--write`, um job por chamada) executa; mantenedor arbitra e faz os GA. Vivacidade §4.3 do V3. Piloto **Vale do Sinos × Nova Santa Rita** herdado (V3-D7). | 2026-08-26 |
| V5-D2 | **Relevância editorial por força**: o builder classifica cada leitura publicável em `lead` (força moderada/forte, ou estrutural com defasagem declarada) e `note` (fraca). A página renderiza `lead` como leitura; `note` não vira frase — a existência do cálculo fica registrada na nota metodológica ("as demais leituras computadas não atingiram força de publicação"). O dado permanece no pacote (SSR e guardas intactos); muda a renderização e a moldura. Limiar pelas faixas fechadas já existentes (V3-D8). | 2026-08-26 |
| V5-D3 | **Conjunto próprio por região**: a curadoria deixa de fixar as mesmas hipóteses nas 10 regiões — a seleção determinística (R3 do V2) passa a ordenar por força e a triagem (V3-D8) amplia a varredura para todo o cruzamento educação×território das séries do retrato; cada região publica as suas relações mais fortes, com teto fixo e prova anti-template de que os conjuntos diferem entre regiões. | 2026-08-26 |
| V5-D4 | **Âncora no PNE**: mapa editorial fechado série-educacional ↔ metas/temas do novo PNE (mesma disciplina da ponte 2.3.0); cada cartão de relação publica os temas do PNE que toca; os temas de agenda dos cenários usam o mesmo vocabulário. Nenhum texto livre: tabela fechada no gerador, reverificada na plataforma. | 2026-08-26 |
| V5-D5 | **E2 liberado, E3+ retidos**: a decomposição contábil (matrícula = coorte defasada × taxa de atendimento; shift-share do emprego) entra com gramática própria ("a queda de nascimentos explica X p.p. da queda de matrículas; o restante decorre de atendimento e fluxo") — só na forma decomposta, com os termos da conta visíveis. E3–E5 (precedência, painel, quase-experimento) ficam no backlog até a gestão decidir V4-P1. A escada E1–E5 aparece na página com o grau declarado por relação. | 2026-08-26 |
| V5-D6 | **UI conforme o mockup**, com metas mensuráveis: altura total ≤ 7.000px na região piloto; texto corrido ≥ 60% da largura útil do painel; cartões de relação em grade ≥ 2 colunas no desktop; correlação/concordância/contraste estadual como encoding visual (barra de força, segmentos, faixa de 10 pontos) além da frase; retrato completo recolhido como camada de consulta; hipóteses/método/"não se conclui" em `details` únicos por cartão. SSR mantém todo o conteúdo no markup (restrição herdada). Cores por entidade validadas para daltonismo: educação `#0E7B54`/`#21A878`, território `#3D6FD1`/`#5E8FE6` (claro/escuro). | 2026-08-26 |
| V5-D7 | **Invariantes herdadas** (V3-D3): fail-closed pesquisa→gerador→plataforma, prévia rotulada, taxa nunca somada, classe `calculated`, corpus bilateral, "portar antes de deletar", sem número futuro fora dos cenários, sem p-valor. A linguagem causal continua bloqueada fora do template do grau declarado. | herdadas |
| V5-D8 | **Alocação de modelos e agentes por etapa** (§2.1): cada tarefa do plano tem um agente indicado pelo tipo de resultado esperado, sob quatro regras fixas — (a) quem escreve não verifica; (b) linguagem pública e estatística de gate nunca são delegadas; (c) o juiz de teste cego nunca é o gate nem o autor do texto julgado; (d) vivacidade V3-D2: segunda morte de um job = o Fable executa e registra. | 2026-08-26 |
| V5-D9 | **GA da R2 do V3 adiado pelo árbitro na R0**: o mantenedor não avaliou a página no layout atual ("muita informação... atrapalha trazer conclusões") e decidiu seguir direto ao redesenho. O GA transfere-se para o **GA humano da R3** (piloto Vale do Sinos × NSR contra o mockup), que cobre também a inversão da moldura da R2 do V3. Após o piloto completo, o mantenedor confirma as análises e o rumo. Registro: `GA_HUMANO_RODADA_02.md`. | 2026-08-26 |

### 2.1 Alocação de modelos e agentes (V5-D8)

**Papéis fixos, em todas as rodadas:**

| Agente | Modelo/canal | O que faz | O que nunca faz |
|---|---|---|---|
| Gate | **Fable 5** (sessão Claude Code, contexto limpo por rodada) | Arquiteta, escreve especificação fechada, verifica com instrumentos próprios (testes, greps, hashes, DOM, screenshots), recomputa estatística em amostra, faz leitura adversarial, emite veredito | Aceitar relato do executor como prova; escrever código de produção fora do fallback de vivacidade |
| Executor | **GPT 5.6 sol xhigh** — sempre o id `gpt-5.6-sol`, reasoning xhigh, plugin Codex/`codex-rescue`, `--write`, um job por chamada, saída declarada em `.tmp/` (`gpt-5.6` retorna 400; `gpt-5.6-codex` trava em starting) | Todo código de produção e de teste sob especificação fechada: builder, gerador, contrato, componentes, harness de corpus | Definir critérios, redigir linguagem pública, verificar o próprio trabalho |
| Juiz cego | **Job `gpt-5.6-sol` separado, não-gate** | Teste cego dos cenários (R4): julgar por realidade sem ver o gabarito | Ser o mesmo job que construiu ou verificou o texto |
| Apoio de varredura | **Subagente Claude (Explore)**, opcional | Fan-out só-leitura no repositório quando o Fable precisar localizar código em muitos arquivos | Qualquer papel de gate ou escrita |
| Árbitro | **Mantenedor** | GA humano, empates, mudanças de plano | — |

**Alocação por rodada — quem entrega o resultado esperado:**

| Rodada | Resultado esperado | Executa | Verifica | Observação |
|---|---|---|---|---|
| R0 | V3 fechado, git limpo | **Fable direto** (juízo editorial + git, não há código novo; especificar custaria mais que fazer) | Mantenedor (GA da R2 do V3) | `gpt-5.6-sol` só entra se o GA gerar correção de código |
| R1 | Curadoria por força correta e determinística | `gpt-5.6-sol` xhigh (builder, varredura, contrato 2.7.0, mapa PNE, harness) | **Fable recomputa a estatística em amostra — nunca delegado**; ataques do corpus redigidos pelo Fable, implementados pelo executor | Estatística é fronteira de risco: dupla origem obrigatória |
| R2 | Conta E2 que fecha e linguagem que não escorrega | `gpt-5.6-sol` xhigh (decomposição no builder, contrato 2.8.0) | **Gramática E2 redigida pelo Fable antes de qualquer número** (linguagem pública fica com o gate); Fable refaz a conta do piloto a partir do dado bruto | Rebaixamento E2→E1 provado por teste, não por leitura |
| R3 | Página leve conforme o mockup, sem perder guarda | `gpt-5.6-sol` xhigh (componentes, CSS, testes de arquitetura) com o mockup como referência visual na spec | **Fable faz o QA visual no navegador** (screenshots + instrumento DOM de altura/largura) e roda o byte a byte das guardas | Decisão estética vive na spec/mockup, não no executor |
| R4 | 8 regiões de cenários distintos e fiéis aos números | `gpt-5.6-sol` xhigh (esqueletos e narrativa, etapa a etapa do guia v1.6) | Fable audita narrativa×números e intercambialidade; **teste cego com juiz `gpt-5.6-sol` não-gate** | Três papéis, três origens: autor, auditor e juiz nunca coincidem |
| R5 | Documento que a gestão reconheça | **Documento de entrega e governança redigidos pelo Fable** (voz do produto); correções de código pelo executor | Mantenedor (e gestora, se possível) em leitura humana | Texto à gestão não é tarefa de executor sob spec |

## 3. Rodadas

Sequência: `R0 → R1 → R2 → R3 → R4 → R5`. Cada rodada em sessão nova do Fable.
Diretórios: `.tmp/vocacoes-v5/rodada-<NN>/` (gitignored). Piloto obrigatório em todas:
Vale do Sinos × Nova Santa Rita.

---

### Rodada 0 — Encerramento do V3 e baseline

**Objetivo:** fechar a R2 do V3 (pendências C9–C12 do checklist) e consolidar.

**Tarefas:**
1. GA humano da R2 do V3 (mantenedor lê Vale do Sinos + NSR na matriz contra o print
   da gestão); achados viram correções na hora.
2. `VIVACIDADE.md` e `RELATORIO_RODADA_02.md` da R2 do V3 concluídos; commits temáticos
   do working tree (inversão da moldura, renderização 2.6.0); push de `main`.
3. Nota de encerramento no `docs/PLANO_VOCACOES_REGIAO_V3.md` (R3–R4 absorvidas aqui) e
   no `docs/PLANO_VOCACOES_REGIAO_V4.md` (rascunho absorvido: E2 → R2 deste plano,
   E3+ → backlog §6).
4. Suíte baseline completa com resultado real registrado; snapshot dos hashes.

**Aceite:** working tree limpo, `main` sincronizada, V3/V4 anotados, baseline gravada.

**Prompt de abertura:**
```text
Leia docs/PLANO_VOCACOES_REGIAO_V5.md (§1–§3, Rodada 0) e
.tmp/vocacoes-v3/rodada-02/CHECKLIST_RODADA_02.md. Execute a Rodada 0 conforme o
protocolo v4 (§4 do V3): feche as pendências da R2 do V3, GA humano comigo, commits e
push, notas de encerramento nos planos V3 e V4, baseline. Relate em
.tmp/vocacoes-v5/rodada-00/. Não inicie a rodada seguinte.
```

---

### Rodada 1 — Curadoria por força: cada região com as suas relações

**Objetivo:** V5-D2/D3/D4 — a leitura de cada região passa a ser o conjunto das suas
relações fortes, ancoradas nos indicadores do PNE; as fracas saem da página.

**Tarefas:**
1. **Builder (pesquisa, SESI\PNE):** varredura ampliada educação×território sobre todas
   as séries do retrato (limiar, mínimo de intervalos e teto por região fixos);
   classificação `lead`/`note` por faixas fechadas; ordenação determinística por força;
   relações estruturais (defasagem declarada) sempre `lead` com o mecanismo nomeado.
2. **Mapa PNE:** tabela fechada série-educacional ↔ metas/temas do novo PNE no gerador,
   reverificada na plataforma; cada relação `lead` carrega seus temas.
3. **Contrato 2.6.0 → 2.7.0 (aditivo):** campos de saliência, força, grau (E1) e temas
   do PNE; reverificação fail-closed; changelog com motivo.
4. Piloto Vale do Sinos verde de ponta a ponta antes do rebuild; recomputação
   independente do Fable em amostra (2 regiões × 3 relações, incluindo o piloto).
5. Rebuild das 10; prova anti-template de que os conjuntos `lead` diferem entre regiões;
   corpus bilateral com ataques novos (fraca apresentada como forte, força fora da faixa).

**Aceite:** piloto primeiro; hash estável ×2; recomputação bate; 2.7.0 verde nas 10;
anti-template verde; corpus 100%; suíte sem regressão.

**Prompt de abertura:**
```text
Leia docs/PLANO_VOCACOES_REGIAO_V5.md (§1–§3, Rodada 1) e o relatório da rodada
anterior. Execute a Rodada 1 conforme o protocolo v4 (§4 do V3): você especifica e
verifica (com recomputação independente em amostra), o GPT 5.6 sol xhigh executa;
vivacidade §4.3. Relate em .tmp/vocacoes-v5/rodada-01/. Não inicie a rodada seguinte.
```

---

### Rodada 2 — E2: a relação contábil ("explica X p.p.")

**Objetivo:** V5-D5 — o primeiro grau acima da associação: decomposição demográfica da
matrícula e shift-share do emprego, com a linguagem "explica" na forma decomposta.

**Tarefas:**
1. **Builder:** decomposição matrícula = coorte SINASC defasada × taxa de atendimento,
   por região e etapa onde a janela comporta; shift-share do emprego formal (composição
   setorial × dinâmica própria). Termos da conta publicados junto do resultado.
2. **Gramática fechada do E2** escrita e atacada por corpus **antes** de qualquer
   número na página (ataques bilaterais: "explica" sem decomposição, decomposição
   apresentada como efeito futuro, resto atribuído a causa nomeada).
3. **Contrato 2.7.0 → 2.8.0 (aditivo):** bloco de decomposição com grau E2 declarado;
   rebaixamento fail-closed (se a conta não fecha no rebuild, a relação volta a E1).
4. Piloto: decomposição do ensino médio do Vale do Sinos verificada por recomputação
   manual do Fable (conta refeita do dado bruto); só então rebuild das 10.
5. Registro à gestão no dossiê: por que E2 respeita a regra de ouro ("mostrando os
   dados que sustentam essa leitura" — a decomposição É o dado).

**Aceite:** gramática atacada antes dos números; recomputação manual bate; rebaixamento
provado em teste; 2.8.0 verde; corpus 100%; suíte sem regressão.

**Prompt de abertura:**
```text
Leia docs/PLANO_VOCACOES_REGIAO_V5.md (§1–§3, Rodada 2) e o relatório da rodada
anterior. Execute a Rodada 2 conforme o protocolo v4 (§4 do V3): gramática E2 primeiro,
depois builder e contrato 2.8.0; você recomputa a decomposição do piloto manualmente;
GPT 5.6 sol xhigh executa; vivacidade §4.3. Relate em .tmp/vocacoes-v5/rodada-02/.
Não inicie a rodada seguinte.
```

---

### Rodada 3 — A página nova (o mockup vira produto)

**Objetivo:** V5-D6 — o layout do mockup implementado em `VocacoesRegiaoPage.tsx` e na
matriz municipal, com as metas mensuráveis batidas.

**Tarefas:**
1. Hero: números-síntese da região (stat tiles com sparkline, delta e contraste
   estadual) compostos no gerador a partir das conclusões observadas — nada calculado
   na página.
2. Escada de evidência como componente (grau por cartão; E2 destacado onde existir);
   duas perguntas da gestão como as duas seções de leitura; cor por entidade (V5-D6).
3. Cartões de relação compactos (título-história composto de template fechado, uma
   frase de leitura, minigráficos pareados, encodings de força/concordância/contraste,
   `details` único para hipóteses+método+"não se conclui"); triagem em lista de uma
   linha; retrato recolhido como consulta; fontes+limites em rodapé.
4. Mesma direção no bloco territorial da matriz municipal (NSR como referência).
5. **Instrumento de altura e largura**: medição automatizada (DOM) na região piloto —
   altura ≤ 7.000px, texto ≥ 60% da largura útil — como teste da rodada.
6. Zero mudança de conteúdo nas frases de guarda (byte a byte, instrumento da R2 do
   V3); SSR com conteúdo no markup; **GA humano** do mantenedor no piloto contra o
   mockup e contra o print da gestão.

**Aceite:** metas de altura/largura batidas por instrumento; 1.442+ frases de guarda
byte-idênticas; SSR verde; GA humano registrado; suíte + guardas verdes.

**Prompt de abertura:**
```text
Leia docs/PLANO_VOCACOES_REGIAO_V5.md (§1–§3, Rodada 3) e o relatório da rodada
anterior; abra o mockup (link no cabeçalho do plano). Execute a Rodada 3 conforme o
protocolo v4 (§4 do V3): GPT 5.6 sol xhigh executa por especificação sua, você verifica
com os instrumentos de altura/largura e de guarda, GA humano comigo antes do
encerramento; vivacidade §4.3. Relate em .tmp/vocacoes-v5/rodada-03/. Não inicie a
rodada seguinte.
```

---

### Rodada 4 — Cenários nas 8 regiões restantes (herdada do V3)

**Objetivo:** Saída 2 nas 10 regiões, já no layout novo. Idêntica à R3 do V3 (gate de
transferibilidade → 2 lotes de 4 pelas 8 etapas do guia v1.6, Vale do Sinos abre o
lote 1, intercambialidade + teste cego + camada municipal por lote, GA humano por
lote), com duas mudanças: os cartões de cenário nascem no formato da R3 daqui, e os
temas de agenda usam o vocabulário PNE da R1 (V5-D4).

**Aceite:** o da R3 do V3, mais conformidade ao layout novo por instrumento.

**Prompt de abertura:**
```text
Leia docs/PLANO_VOCACOES_REGIAO_V5.md (§1–§3, Rodada 4), a Rodada 3 do §5 do V3 e o
relatório da rodada anterior. Execute a Rodada 4 conforme o protocolo v4 (§4 do V3):
gate de transferibilidade primeiro; se verde, 2 lotes de 4 regiões, GA humano comigo
por lote; vivacidade §4.3. Relate em .tmp/vocacoes-v5/rodada-04/. Não inicie a rodada
seguinte.
```

---

### Rodada 5 — Entrega, governança e encerramento (herdada do V3)

**Objetivo:** o da R4 do V3, atualizado: leitura adversarial contra as duas perguntas
da gestão; teste de leitura humano no par piloto; `docs/GOVERNANCA_VOCACOES_REGIAO.md`
(dono, cadência por fonte, expiração fail-visible, re-execução anual — grau E2 pode
rebaixar quando o dado novo chega); documento de entrega à gestão (2–3 páginas) mapeando
o pedido original + o pedido deste plano ao que está no ar, com o destino declarado de
E3–E5 e da Opção C; varredura final e push.

**Aceite:** o da R4 do V3, mais o mapa de graus por relação no documento de entrega.

**Prompt de abertura:**
```text
Leia docs/PLANO_VOCACOES_REGIAO_V5.md completo e o relatório da rodada anterior.
Execute a Rodada 5 conforme o protocolo v4 (§4 do V3): revisão editorial, teste de
leitura comigo, governança, documento de entrega, varredura final e push; GPT 5.6 sol
xhigh executa as correções. Relate em .tmp/vocacoes-v5/rodada-05/. Este é o
encerramento do plano V5.
```

---

## 4. Riscos

1. **"Forte" virar caça a correlação espúria** (varredura ampliada acha pares sem
   sentido) — mitigação: teto por região, mínimo de intervalos, relações `lead` da
   varredura publicadas como "observadas por triagem" (sem hipótese curada), leitura
   adversarial do gate sobre cada conjunto regional.
2. **Retirar as fracas parecer esconder dado** — mitigação: V5-D2 mantém o cálculo no
   pacote e declara o critério na nota metodológica; o corpus ataca a omissão indevida
   (força alta rebaixada a `note`).
3. **E2 com janela insuficiente em alguma região/etapa** — mitigação: a decomposição só
   publica onde a conta fecha; ausência declarada com motivo (mesmo padrão dos
   `reasonCode` da R1 do V3).
4. **Redesign quebrar guardas ou SSR** — mitigação: instrumento byte a byte das frases
   de guarda (provado na R2 do V3) e asserções de SSR como testes da rodada.
5. **Gestão não validar a linguagem E2** — degrada bem: os cartões E2 rebaixam para E1
   (frase associativa) sem tocar o layout; a escada continua visível.

## 5. Backlog

- **E3–E5** (precedência temporal, painel municipal 497×20, quase-experimento):
  bloqueados por V4-P1/P2/P4 (decisão da gestão + inferência + ferramental); o painel
  municipal do V4 §3 é o caminho quando liberar.
- **Opção C da R5 do V2** (matrícula municipal via microdados do Censo Escolar).
- **Catálogo de mecanismos com lastro em literatura** para as hipóteses `lead`.
- Backlog herdado (`BACKLOG_V2.md`) permanece com destinos válidos.
