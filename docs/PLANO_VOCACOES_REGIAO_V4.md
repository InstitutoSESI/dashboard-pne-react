# Plano — Vocações da Região V4: da associação à explicação causal graduada

Data: 2026-08-26
Status: **RASCUNHO ABSORVIDO PELO V5 — nunca aprovado para execução isolada.**
Nota de absorção (R0 do V5, 2026-08-26): o grau **E2** (relação contábil) foi
absorvido como a **Rodada 2 do `docs/PLANO_VOCACOES_REGIAO_V5.md`** (decisão V5-D5);
**E3–E5** permanecem condicionais à decisão V4-P1 da gestão e vivem no **backlog §5
do V5**. Este documento fica como referência conceitual da escada E1–E5; nenhuma
rodada dele executa a partir daqui.
Origem: diagnóstico do mantenedor (2026-08-26) de que a página segue conservadora
demais — "muitos avisos de que não é possível afirmar causas, afirmações apenas
descritivas de séries que andam juntas, nunca estabelecendo causa e relação" — e o
pedido de avançar para **estabelecer causa e relação** entre variáveis do Vocações e
variáveis educacionais do PNE.
Sucede o V3 (`docs/PLANO_VOCACOES_REGIAO_V3.md`): pressupõe a R1 do V3 fechada
(contrato 2.6.0, leitura associativa quantificada) e recomenda que a **R2 do V3
(inversão da moldura) rode antes ou em paralelo** — ela resolve a metade visível do
incômodo (a negação como protagonista) sem depender deste plano.

---

## 1. O problema que este plano ataca

O V1–V3 construíram uma camada associativa honesta e verificável, mas com um **teto
único de linguagem**: tudo o que a plataforma pode dizer é "as séries se moveram
juntas". Esse teto veio da regra de ouro da gestão (§1 do V3: "a plataforma não afirma
que uma variável causou a outra") e virou invariante técnica (V3-D3/D4: sem
causalidade, sem p-valor, sem inferência).

O resultado é o incômodo atual: relações que **são** causais em sentido forte
(demografia → matrícula é quase contábil) recebem a mesma moldura tímida de relações
meramente correlacionais. O usuário lê dez avisos de "não se conclui" e sai achando
que a plataforma não sabe nada.

**A tese deste plano:** o salto não é trocar "andam juntas" por "X causa Y" em todo
lugar — é substituir o teto único por uma **escada de evidência com graus fechados**,
onde cada relação publicada carrega o grau mais alto que o dado sustenta, e a
linguagem causal é liberada **por grau**, com gramática fechada por construção (mesma
disciplina de V2-D8/V3-D8).

## 2. A escada de evidência (E1–E5)

| Grau | Nome | O que estabelece | Método | Linguagem liberada (template) |
|---|---|---|---|---|
| E1 | Associação quantificada | co-movimento | R1 do V3 (pronto): concordância, correlação com força/sentido, contraste estadual | "moveram-se juntas", "correlação forte/negativa" |
| E2 | Relação contábil | causa em sentido aritmético | decomposição: matrícula = coorte × taxa de atendimento; shift-share do emprego | **"a queda de nascimentos explica X p.p. da queda de matrículas; o restante decorre de taxa de atendimento/fluxo"** |
| E3 | Precedência temporal | ordem sistemática | teste de defasagem (estilo Granger) sobre o painel: X antecede ΔY além da história da própria Y, e o inverso não | "X antecede sistematicamente Y em k anos; o inverso não se observa" |
| E4 | Efeito estimado em painel | evidência de efeito | painel municipal 497×~20 anos com efeitos fixos de município e ano; elasticidade com IC | "evidência consistente com efeito de X sobre Y: +1% em X associa-se a β% em Y (IC 95%)" |
| E5 | Quase-experimento | efeito identificado | evento discreto no território (grande empregador, campus) com diferenças-em-diferenças / controle sintético | "após [evento], Y mudou Δ além do contrafactual estimado" |

Regras da escada:

1. **Grau declarado por relação**: todo bloco publicado nomeia o grau e o instrumento
   que o sustenta; a plataforma reverifica fail-closed (grau sem instrumento = recusa).
2. **Linguagem por grau, fechada por template**: "explica" só a partir de E2 e só na
   forma decomposta; "efeito" só a partir de E4; corpus adversarial bilateral por grau
   (ataque novo: linguagem de grau alto em relação de grau baixo).
3. **Rebaixamento é fail-closed**: se o instrumento do grau falha no rebuild, a
   relação cai para o maior grau que passa — nunca some, nunca mente para cima.
4. **Mecanismo obrigatório de E3 para cima**: nenhuma relação sobe de E2 sem um
   mecanismo plausível registrado (catálogo com lastro em literatura, §6 do V3).

## 3. A alavanca de dados: painel municipal

O V1–V3 operam com n=10 regiões — bom para retrato, insuficiente para inferência. As
mesmas fontes existem em grão municipal: **497 municípios do RS × ~20 anos** (RAIS
2006+, SINASC 1994+, INEP fluxo escolar local, PIB municipal 2002+, CadÚnico). É esse
painel que sustenta E3/E4; os resultados são **agregados de volta por região** para
publicação (a página continua regional; a estatística é municipal).

## 4. Decisões pendentes (bloqueiam a aprovação, não a discussão)

| # | Decisão | De quem |
|---|---|---|
| V4-P1 | **Graduação da regra de ouro da gestão**: a regra "a plataforma não afirma causa" foi da gestão (§1 do V3). Este plano propõe substituí-la por "a plataforma afirma o que o grau de evidência sustenta, com o grau declarado". Precisa de aceite registrado da gestão — sem isso, o produto contradiz o pedido original. | Gestão + mantenedor |
| V4-P2 | **Revogação parcial de V3-D4/D8 (sem p-valor / sem inferência)**: E4 exige inferência (IC, erro padrão agrupado por município). Proposta: inferência permitida **só dentro do template do grau**, nunca solta. | Mantenedor |
| V4-P3 | **Sequência com o V3**: rodar R2 do V3 antes (recomendado — resolve a moldura já), em paralelo, ou absorver R2–R4 do V3 neste plano. | Mantenedor |
| V4-P4 | **Ferramental de E3/E4**: statsmodels/linearmodels no builder da pesquisa (SESI\PNE) — nova dependência no ambiente de staging. | Mantenedor |

## 5. Rodadas propostas (protocolo v4 do V3, inalterado)

Piloto obrigatório em todas: **Vale do Sinos × Nova Santa Rita** (V3-D7 herdada).

- **R0 — Escopo e regra de linguagem**: decisões V4-P1..P4 registradas; gramática
  fechada dos 5 graus escrita e atacada por corpus antes de qualquer número; inventário
  do painel municipal (cobertura real por fonte × município × ano).
- **R1 — E2, a relação contábil (maior ganho imediato)**: decomposição demográfica da
  matrícula em todas as regiões (coorte SINASC defasada × taxa de atendimento) e
  shift-share do emprego; primeira linguagem "explica X p.p." no ar. Contrato 2.7.0.
- **R2 — E3/E4, o painel municipal**: construção do painel na pesquisa; precedência
  temporal e efeitos fixos para os pares curados; só sobem de grau os pares que passam
  nos instrumentos; recomputação independente do Fable em amostra.
- **R3 — E5 oportunista + integração na página**: varredura de eventos discretos
  documentáveis (≥1 região se existir); renderização da escada (grau visível, "como
  ler" por grau); GA humano com o print da gestão como contraste.
- **R4 — Entrega**: documento à gestão mapeando cada relação ao seu grau, com o que
  subiu, o que ficou em E1 e por quê; governança de re-execução anual da escada
  (grau pode cair quando o dado novo chega); push.

## 6. Riscos

1. **Linguagem causal escorregar além do grau** — mitigação: corpus por grau com
   ataques bilaterais; rebaixamento fail-closed; leitura adversarial do gate.
2. **E4 frágil** (endogeneidade, choques correlacionados): efeitos fixos não são
   identificação perfeita — por isso a linguagem de E4 é "evidência consistente com
   efeito", não "causa provada"; mecanismo obrigatório e teste de placebo (defasagem
   invertida) como instrumento.
3. **Gestão não aceitar a graduação da regra de ouro** (V4-P1) — o plano degrada bem:
   E2 (contábil) é defensável mesmo sob a regra atual ("mostrando os dados que
   sustentam essa leitura" — a decomposição É o dado); E3+ ficam retidos.
4. **Painel municipal com buracos** (municípios pequenos, sigilo RAIS/INEP) —
   inventário na R0 antes de prometer grau; mínimos de cobertura fixos no builder.
