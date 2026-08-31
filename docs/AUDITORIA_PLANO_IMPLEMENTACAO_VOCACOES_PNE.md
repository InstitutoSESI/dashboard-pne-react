# Auditoria do Plano de Implementação Vocações × PNE

- **Data da auditoria:** 28 de agosto de 2026
- **Plano auditado:** `docs/arquivo/planos-vocacoes-regiao/PLANO_IMPLEMENTACAO_VOCACOES_PNE.md` (V6)
- **Piloto:** Vale do Sinos, com foco municipal em Nova Santa Rita (`4313375`)
- **Finalidade:** entregar ao GPT Pro um retrato técnico, analítico e de produto do que já foi feito, do que foi encontrado, do que foi descartado ou retido e do que ainda bloqueia o objetivo da página.

## 1. Resumo técnico

O trabalho avançou muito além do planejamento inicial, mas o plano **não está concluído**.

- As **Etapas 0 a 8** foram implementadas e tiveram seus gates técnicos aprovados.
- As **Etapas 9 e 10** foram implementadas e aprovadas tecnicamente: há compilador, contrato de linguagem, página narrativa, testes, fallback e rollback. O GA humano previsto ao fim da rodada não foi realizado.
- A **Etapa 11** foi executada como auditoria, mas ficou **bloqueada**. Os cinco cartões existentes são confiáveis; o bloqueio é de produto e conteúdo: a página não permite cumprir a tarefa de identificar uma relação integrada entre trabalho e formação profissional, e o teste humano não foi executado.
- A **Etapa 12** não foi aprovada. Vale do Rio Pardo e Noroeste têm dados legados e cenários, mas não têm resultados R5/R6 nem documento narrativo compilado.
- A **Etapa 13** foi implementada apenas no aspecto de governança e publicação progressiva. O lote atual, contendo somente o Vale do Sinos, é válido; isso não equivale a escalar a metodologia.

Assim, há duas respostas possíveis para “até onde chegamos”:

1. **Última etapa analítica e de produto concluída tecnicamente:** Etapa 10.
2. **Última etapa em que houve algum avanço de implementação:** Etapa 13, mas somente na infraestrutura de fila, registro, fallback e rollback de um lote com uma região.

O primeiro gate não aprovado é o **Gate 11**. O **Gate 12** também não foi aprovado. O plano não pode ser declarado encerrado.

### Números centrais do avanço

| Item | Resultado auditado |
|---|---:|
| Séries-raiz registradas e classificadas | 103 |
| Séries já disponíveis na plataforma | 71 |
| Séries-raiz adicionais disponíveis na pesquisa | 32 |
| Mecanismos substantivos catalogados | 16, em 7 famílias |
| Candidatas efetivamente avaliadas no V6 | 11 |
| Candidatas publicáveis | 5 |
| Candidatas retidas silenciosamente | 6 |
| Cartões da primeira saída | 3 |
| Cartões da segunda saída | 2 |
| Regiões na experiência narrativa | 1 de 10 |
| Regiões `almost_ready` | 2 de 10 |
| Regiões ainda não auditadas para transferência | 7 de 10 |

O V6 reduziu o percurso principal de 18 leituras para 5 cartões, retirou os 8 cartões de triagem automática da interface, preservou as 71 séries na consulta e criou 2 cartões efetivos para a segunda pergunta, que antes não tinha conteúdo no Vale do Sinos.

## 2. O que o produto pretende responder

A reconstrução organiza a página em duas perguntas da gestão:

1. **O que o território ajuda a compreender sobre a educação?**
2. **O que o futuro do território coloca na agenda da educação?**

O V6 abandonou a ideia de selecionar pares porque têm correlação alta. A unidade editorial passou a ser uma leitura que precisa:

- começar por uma pergunta substantiva;
- usar populações e escalas compatíveis;
- separar componentes antes de relacionar variáveis;
- incluir diferenças entre municípios;
- resistir a janelas alternativas e à retirada de um município;
- produzir uma questão concreta de planejamento;
- ser integralmente rastreável;
- evitar linguagem causal quando o desenho é descritivo.

Nenhuma relação descrita neste relatório estabelece causalidade. “Relação encontrada” significa relação descritiva, decomposição contábil, transformação observada ou tendência sustentada nos limites declarados.

## 3. Estado etapa a etapa

| Etapa | O que foi entregue | Situação auditada | Pendência principal |
|---|---|---|---|
| 0 — congelar e auditar | baseline 2.9.0, tag `baseline-pre-v6`, hashes, inventário, problemas reproduzidos e matriz de destino | **Aprovada com pendências não bloqueantes** | pendências de screenshots e reexecução da pesquisa foram tratadas em rodadas posteriores |
| 1 — contrato de produto e conteúdo | duas saídas, mínimos 3/2, schemas, guia editorial, vocabulário, exemplos e linter | **Aprovada** | nenhuma pendência bloqueante |
| 2 — catálogo de mecanismos | 16 mecanismos M1–M7, pares permitidos/provisórios, default-deny | **Aprovada** | mecanismos não garantem, sozinhos, disponibilidade municipal |
| 3 — registro de séries e universos | 103 séries, 12 universos, 6 lentes territoriais, denominadores e bloqueios | **Aprovada** | diferenciar sempre residente, escola e estabelecimento |
| 4 — dados já disponíveis | demografia etária, fluxo, tempo integral, redes, EP por modalidade, EJA potencial e trabalho juvenil | **Aprovada** | parte do material está no repositório de pesquisa, não na publicação pública |
| 5 — fontes novas dirigidas | deslocamento 2022, ocupações CBO e correspondência cursos–ocupações; duas fontes recusadas | **Aprovada com pendências não bloqueantes** | matriz origem–destino e PDF CNCT permanecem incompletos |
| 6 — primeira saída | 6 candidatas avaliadas, 3 publicáveis, decomposições e heterogeneidade municipal | **Aprovada** | EJA, EP e tempo integral retidos |
| 7 — segunda saída | 5 transformações avaliadas, 2 agendas publicáveis | **Aprovada** | trabalho/formação, rede rural e EJA/emprego retidos |
| 8 — comparação temporal e territorial | quatro janelas, comparação com RS, concentração, direção e `leave-one-out` | **Aprovada nas duas direções** | não há projeção futura para o Vale; isso é deliberado |
| 9 — compilador e linguagem | três camadas, 212 textos rastreados, linter e geração determinística | **Aprovada tecnicamente** | GA humano pendente |
| 10 — experiência da página | página `3 + 2`, 20 detalhes, 5 visuais, consulta, responsividade, impressão e fallback | **Aprovada tecnicamente** | GA humano pendente; código ainda local/não entregue por commit |
| 11 — validação do piloto | auditoria numérica, metodológica, editorial e visual sem divergência | **Bloqueada** | falta a leitura trabalho × formação e falta o teste humano |
| 12 — transferência | contrato regional e candidatas contrastantes selecionadas | **Não aprovada** | VRP e Noroeste não têm artefatos R5/R6/R7 |
| 13 — escala | fila, manifesto, registro narrativo e rollback regional | **Aprovada somente para o lote atual** | 1 região narrativa, 9 no legado; não há escala analítica concluída |

### Leitura correta das Rodadas 8 e 9

A Rodada 8 instruiu não iniciar a Rodada 9 antes de fechar o Gate 11. Depois, em modo remoto, o mantenedor autorizou avançar sem o GA humano. Essa autorização permitiu construir a governança de publicação, mas **não transformou o Gate 11 em aprovado** e não criou uma validação humana inexistente.

## 4. Evidência e método usados na auditoria

Foram confrontados:

- o plano V6 e os planos V1–V5;
- os relatórios e checklists locais das Rodadas 0–9;
- o baseline 2.9.0 do Vale do Sinos;
- o contrato de produto e os catálogos de mecanismos, universos, séries e referências;
- os artefatos de pesquisa e as saídas integradas das Rodadas 5 e 6;
- a projeção narrativa e o registro interno do compilador;
- a fila de publicação regional;
- dados municipais usados pelos motores, inclusive o CSV local de fluxo do INEP;
- testes atuais do working tree.

Em caso de conflito, a auditoria tratou implementação e artefatos atuais como evidência mais forte que textos aspiracionais do plano.

Não foram criados gráficos novos: este documento é uma auditoria de lookup exato, decisões, gates e rastreabilidade. As tabelas preservam melhor os números e os motivos de retenção; os cinco visuais da página já foram auditados em seu contexto final.

## 5. Como as relações passaram a ser selecionadas

### 5.1 Os dez gates

Cada candidata pública precisa fechar G1–G10:

| Gate | Pergunta de controle |
|---|---|
| G1 — relevância | a questão é relevante para o PNE e para o planejamento? |
| G2 — mecanismo | existe mecanismo substantivo previamente catalogado? |
| G3 — universo | numerador, denominador, população e lente territorial são compatíveis? |
| G4 — tempo | janela, defasagem e condição de fotografia/tendência são válidas? |
| G5 — estabilidade | o padrão é municipalmente decomponível, não dominado e robusto? |
| G6 — valor | a integração acrescenta interpretação, e não apenas põe séries lado a lado? |
| G7 — planejamento | público, etapa, fenômeno, recorte e indicador são nomeados? |
| G8 — clareza | a autoria pública passa no contrato e no linter? |
| G9 — não redundância | o cartão não duplica outro enredo? |
| G10 — rastreabilidade | fatos, períodos, fontes e cálculos estão manifestados? |

### 5.2 Testes quantitativos principais

- Janela primária da primeira saída: 2015–2025.
- Sensibilidades: 2014–2025, 2016–2025 e 2015–2024.
- Concentração municipal máxima: 50% da mudança absoluta.
- Direção municipal mínima, quando aplicável: 60%.
- Retirada de cada município: a direção regional precisa permanecer.
- Valores brutos nos cálculos; arredondamento somente na apresentação.
- Taxas de fluxo são distribuições municipais; nunca são somadas.
- Fotografia censitária de 2022 não é promovida a tendência.
- O Vale do Sinos não recebeu número futuro nem cenário por não ter cenário publicado.

### 5.3 Decomposição contábil usada nas três leituras da primeira saída

O motor usa:

```text
M = P × R

componente_população = (P1 - P0) × (R0 + R1) / 2
componente_relação   = (R1 - R0) × (P0 + P1) / 2
```

`M` é matrícula localizada, `P` é população residente da idade e `R` é a relação aparente matrícula/população. `R` **não é taxa de cobertura**: pode absorver deslocamentos, migração, rede atendendo residentes de outros municípios e outras diferenças de lente.

## 6. Variáveis inventariadas e variáveis efetivamente analisadas

### 6.1 Inventário canônico

O registro contém 103 entradas-raiz. Isso não significa que 103 relações tenham sido testadas no V6. O registro classifica o que existe e impede cruzamentos incompatíveis.

| Universo | Entradas-raiz | Exemplos |
|---|---:|---|
| cadastro social | 12 | famílias e pessoas inscritas, baixa renda, cadastro atualizado |
| coortes censitárias | 18 | população, óbitos e saldo migratório aparente por coorte |
| economia local | 5 | PIB agropecuário, industrial, serviços, administração e exportações |
| eventos | 1 | eventos climáticos registrados |
| fluxo/rendimento | 16 | aprovação, reprovação, abandono e distorção por etapa |
| matrículas localizadas | 9 | etapas, EJA, EP, redes, modalidades e tempo integral |
| nascimentos por residência | 1 | nascidos vivos por residência da mãe |
| óbitos por residência | 14 | faixas etárias e total |
| oferta física | 2 | escolas totais e rurais |
| população residente | 12 | faixas etárias, rural, idosos e escolaridade adulta |
| residência × estudo | 2 | deslocamento total e por curso/etapa |
| trabalho formal local | 11 | vínculos, massa salarial, escolaridade, idade, indústria e ocupações |

As 103 entradas se distribuem em 71 `disponivel_plataforma` e 32 `disponivel_pesquisa`; 77 são observadas, 18 calculadas e 8 estimadas indiretamente.

Seis entradas-raiz são compostas:

| Entrada | Componentes |
|---|---:|
| ocupações por subgrupo CBO | 48 |
| matrículas de EP por modalidade | 8 |
| deslocamento por curso frequentado | 8 |
| matrículas em tempo integral | 5 |
| matrículas da educação básica por rede | 4 |
| deslocamento para estudo | 4 |

### 6.2 Variáveis usadas nas cinco leituras aprovadas

| Leitura | Variáveis educacionais | Variáveis territoriais/contextuais | Validação adicional |
|---|---|---|---|
| educação infantil | matrículas na educação infantil | população 0–3 e 4–5 | decomposição municipal e comparação com RS |
| ensino fundamental | matrículas no fundamental | população 6–14 | reprovação, abandono e distorção no fundamental |
| ensino médio | matrículas no médio | população 15–17 | reprovação, abandono e distorção no médio |
| coortes e rede | matrículas por etapa e escolas | população 0–14, nascimentos e índice de envelhecimento | quatro janelas, municípios e RS |
| deslocamento e oferta | matrículas no médio como ponto de partida | residentes que estudam fora, total/fundamental/médio | municípios e RS, com universos separados |

### 6.3 Variáveis avaliadas nas candidatas retidas

- EJA: matrículas de EJA; adultos 18+ sem fundamental ou médio completo.
- Educação profissional: matrículas totais/técnicas e por modalidade; ocupações CBO; correspondência cursos–ocupações.
- Tempo integral: matrículas em tempo integral; presença de famílias/trabalhadores no emprego formal.
- Rede rural: escolas rurais; população rural; atividade agropecuária.
- Escolaridade do emprego × EJA: composição dos vínculos por escolaridade; matrícula de EJA.
- Trabalho × formação: mudança ocupacional; oferta/matrículas de formação profissional.

## 7. O que o baseline anterior havia calculado

O contrato 2.9.0 do Vale do Sinos continha:

- 18 leituras `lead`;
- 8 leituras `note`;
- 4 decomposições E2;
- 15 conclusões;
- 71 séries territoriais;
- 6 associações curadas;
- 5 pares temporais e 1 par defasado;
- 8 pares de triagem automática.

Esses resultados são parte do histórico e da camada de consulta; não devem ser confundidos com as cinco relações aprovadas no V6.

### 7.1 Relações antigas e seu destino no V6

| Relação do baseline | Resultado antigo | Destino no V6 |
|---|---|---|
| nascimentos × matrículas do fundamental, defasagem de 6 anos | `r=-0,18`, 4/11 variações no mesmo sentido | não vira cartão de par; o mecanismo demográfico entra por coorte/decomposição |
| vínculos com EM completo × EP | triagem forte negativa | removida da interface; sem mecanismo suficiente como par bruto |
| população total × fundamental | triagem forte negativa | substituída pela população correta de 6–14 anos |
| indústria × EP técnica | correlação forte negativa | permitida apenas como contexto; agenda depende de ocupações/formação compatíveis e segue retida |
| vínculos com EM completo × EP técnica | triagem forte negativa | não publicada; par bruto insuficiente |
| CadÚnico × fundamental | correlação moderada | bloqueada: cadastro social não é denominador da demanda escolar |
| EM × composição do emprego | associação com hipótese herdada do fator errado | bloqueada; conteúdo estava metodologicamente mal configurado |
| vínculos totais × EP técnica | triagem moderada | bloqueada: sem recorte etário/ocupacional e fora do catálogo |
| população 0–14 × ensino médio | triagem moderada | bloqueada por faixa etária incompatível; substituída por 15–17 |
| PIB de serviços × EJA | correlação moderada | bloqueada: nenhum mecanismo catalogado |
| baixa renda no cadastro × EJA | correlação moderada negativa | bloqueada: cadastro social não mede público potencial da EJA |
| população total × escolas rurais | associação moderada | substituída por população rural e atividade agropecuária; candidata final retida em G5 |
| envelhecimento × escolas | correlação moderada | reaproveitada e transformada no cartão aprovado `coortes × rede` |
| escolaridade do emprego × EJA | associação moderada | enredo admitido uma única vez, mas retido em G5 por falta de decomposição municipal |
| mesmo par escolaridade do emprego × EJA repetido | duplicação associação/par | deduplicado; máximo de um cartão |
| emprego formal total × ensino médio | associação moderada | bloqueada: variável ampla e sem mecanismo suficiente |
| massa salarial × EJA | relação fraca | bloqueada: fora do catálogo |
| EP técnica × ensino superior completo | relação fraca | bloqueada: fora do catálogo |
| EM × profissionais do ensino | relação praticamente nula | bloqueada: fora do catálogo |
| EM × massa salarial | relação fraca | bloqueada: massa salarial somente como contexto, não explicação |
| escolas rurais × PIB agropecuário | relação fraca | admitida como contexto no M5; insuficiente para publicação sem decomposição municipal |

Os demais itens de triagem automática foram todos impedidos de chegar à interface por `default-deny`. Coeficiente alto deixou de ser critério de publicação.

### 7.2 Oito relações fracas mantidas como `note` no baseline

Estas foram computadas, mas não tinham força nem mecanismo para aparecer na leitura principal:

1. EP técnica × vínculos com ensino superior completo (`Pearson 0,14`).
2. EP técnica × proporção de vínculos com ensino médio completo (`-0,29`).
3. Ensino médio × profissionais do ensino (`-0,01`).
4. Ensino médio × massa salarial (`0,11`).
5. Escolas rurais × PIB agropecuário (`0,27`).
6. EJA × vínculos ativos (`-0,16`).
7. EJA × massa salarial (`-0,08`).
8. Massa salarial × EJA como par temporal (`-0,20`).

No V6, relações fracas ou descartadas não são conteúdo público. Seus motivos permanecem internos.

## 8. Relações aprovadas no Vale do Sinos

### 8.1 A educação infantil cresceu apesar da redução da população de 0 a 5 anos

Entre 2015 e 2025:

- matrículas: 34.568 → 40.333, **+5.765** (+16,7%);
- população 0–5: 71.337 → 60.661, **-10.676** (-15,0%);
- componente ligado ao tamanho da população: **-6.136 matrículas**;
- componente ligado à relação matrícula/população: **+11.901**.

O segundo componente compensou o primeiro. A direção e o componente dominante permanecem nas quatro janelas de sensibilidade, e nenhum município sozinho determina o resultado.

### 8.2 A queda do fundamental acompanha principalmente a redução da população de 6 a 14 anos

Entre 2015 e 2025:

- matrículas: 114.192 → 104.328, **-9.864** (-8,6%);
- população 6–14: 113.469 → 104.481, **-8.988** (-7,9%);
- componente população: **-9.010**;
- componente relação matrícula/população: **-854**.

Em 2025, a distorção idade-série municipal variou de 2,5% a 14,4%; a mediana regional foi 7,5%, contra 8,1% no RS. A leitura não reduz o problema a demografia: diferenças de fluxo seguem relevantes.

### 8.3 A queda do ensino médio também é dominada pela redução da população de 15 a 17 anos

Entre 2015 e 2025:

- matrículas: 30.847 → 26.911, **-3.936** (-12,8%);
- população 15–17: 42.781 → 33.093, **-9.688** (-22,6%);
- componente população: **-7.432**;
- componente relação matrícula/população: **+3.496**.

Em 2025, as medianas municipais de reprovação (6,0%) e abandono (2,8%) no Vale superaram as do RS (2,7% e 1,5%). A demografia explica o componente dominante, mas não elimina a agenda de permanência e conclusão.

### 8.4 Coortes menores e envelhecimento colocam a distribuição da rede na agenda

Entre 2015 e 2025:

- população 0–14: 184.806 → 165.142, **-19.664** (-10,6%);
- nascimentos: 13.004 em 2015 → 9.276 em 2024, **-3.728** (-28,7%);
- escolas com matrículas: 679 → 693, **+14** (+2,1%);
- índice de envelhecimento: 62,6 → 103,9 idosos por cem crianças, **+41,3 pontos**.

A população 0–14 caiu mais no Vale (-10,6%) que no RS (-8,8%), enquanto o número de escolas cresceu 2,1% no Vale e caiu 1,9% no estado. Isso sustenta uma agenda de redistribuição, não uma projeção numérica automática de fechamento ou abertura de escolas.

### 8.5 O deslocamento para estudo coloca a oferta do ensino médio em escala regional

Fotografia de 2022:

| Universo | Vale do Sinos | RS |
|---|---:|---:|
| total que estudava em outro município | 33.868 / 229.441 = **14,8%** | **8,8%** |
| fundamental | 7.507 / 107.060 = **7,0%** | **3,3%** |
| ensino médio | 5.812 / 38.516 = **15,1%** | **8,2%** |

O dado é por residência e não informa o município de destino. A matrícula de 2025 é por local da escola. A página declara essa diferença e não soma ou divide universos incompatíveis.

## 9. Nova Santa Rita: o que os dados mostram

Nova Santa Rita é especialmente importante porque funciona como contraexemplo à leitura agregada de encolhimento regional. Em quatro das cinco leituras, o município aparece explicitamente no texto público; nos cinco cartões, aparece na distribuição municipal.

### 9.1 Matrículas e população por etapa

| Dimensão, 2015–2025 | Nova Santa Rita | Direção do Vale | Posição municipal |
|---|---:|---|---|
| matrículas na educação infantil | 802 → 1.414, **+612** (+76,3%) | +5.765 | 4º maior aumento |
| população 0–5 | 2.458 → 2.435, **-23** (-0,9%) | -10.676 | quase estável |
| matrículas no fundamental | 3.747 → 3.957, **+210** (+5,6%) | -9.864 | 3º maior aumento |
| população 6–14 | 3.710 → 4.073, **+363** (+9,8%) | -8.988 | direção oposta à região |
| matrículas no ensino médio | 757 → 840, **+83** (+11,0%) | -3.936 | 2º maior aumento |
| população 15–17 | 1.284 → 1.253, **-31** (-2,4%) | -9.688 | mesma direção, queda muito menor |
| população 0–14 | 6.168 → 6.508, **+340** (+5,5%) | -19.664 | maior aumento entre os 10 municípios |

As relações aparentes matrícula/população mudaram assim:

- educação infantil: 32,6 → 58,1 matrículas por cem residentes da idade, +25,4 p.p.;
- fundamental: 101,0 → 97,2 por cem, -3,8 p.p.;
- médio: 59,0 → 67,0 por cem, +8,1 p.p.

Essas razões não são cobertura. O fundamental acima de 100 no início mostra por que a lente precisa ser declarada: matrículas são localizadas nas escolas e população é residente.

### 9.2 Trajetória escolar em 2025

| Etapa/recorte | Aprovação | Reprovação | Abandono | Distorção idade-série |
|---|---:|---:|---:|---:|
| fundamental total | 93,9% | 5,9% | 0,2% | 14,1% |
| anos iniciais | 96,0% | 3,9% | 0,1% | 7,8% |
| anos finais | 90,9% | 8,8% | 0,3% | 22,7% |
| ensino médio | 81,1% | **15,7%** | 3,2% | **24,8%** |

Nova Santa Rita teve a **maior reprovação no ensino médio** entre os dez municípios (15,7%) e a **maior distorção idade-série no ensino médio** (24,8%). O abandono de 3,2% também ficou acima da mediana regional de 2,8% e da mediana estadual de 1,5%. No fundamental, a distorção de 14,1% ficou próxima do máximo regional de 14,4% e bem acima da mediana de 7,5%.

O achado mais relevante é a combinação, não um número isolado: o município aumentou matrículas no fundamental e no médio, mas mantém sinais fortes de trajetória, sobretudo nos anos finais e no médio. Planejar apenas pelo tamanho da coorte perderia essa dimensão.

### 9.3 Deslocamento para estudo em 2022

| Universo de residentes | Estudava fora do município | Total que frequentava | Participação |
|---|---:|---:|---:|
| total | 1.349 | 7.666 | **17,6%** |
| fundamental | 355 | 4.090 | **8,7%** |
| ensino médio | 220 | 1.151 | **19,1%** |

No ensino médio, Nova Santa Rita teve a terceira maior participação de residentes estudando em outro município, atrás de Estância Velha (32,6%) e Esteio (21,3%). Isso reforça que oferta, permanência e transporte precisam ser lidos em escala intermunicipal. O dado não revela para onde os estudantes se deslocam.

### 9.4 Interpretação integrada para Nova Santa Rita

O retrato disponível sustenta quatro conclusões descritivas:

1. **Nova Santa Rita não está na mesma trajetória demográfica do agregado regional.** Foi o município com maior aumento da população de 0 a 14 anos no período analisado.
2. **A demanda educacional local não pode ser dimensionada por uma narrativa regional de retração.** Matrículas cresceram nas três etapas analisadas.
3. **O crescimento quantitativo convive com desafios fortes de trajetória.** Reprovação e distorção no ensino médio são os maiores do Vale.
4. **Parte relevante dos estudantes depende de oferta fora do município.** No médio, quase um em cada cinco residentes que estudava o fazia em outro município em 2022.

Esses pontos indicam uma necessidade de página em duas escalas: a região informa coordenação e transformação territorial; o município informa intensidade, direção divergente e prioridades de ação.

## 10. Relações retidas: não publicadas, mas não “refutadas”

Uma retenção não prova ausência de relação. Significa que a candidata não passou todos os gates necessários para virar insight público.

| Candidata | Gate | Motivo registrado | O que falta |
|---|---|---|---|
| EJA × público potencial | G4 | `nivel-e-janela-do-publico-potencial-nao-fechados` | fechar uma leitura de nível 2022 ou obter janela comparável; não tratar fotografia como série |
| EP × ocupações | G5 | `matricula-por-modalidade-sem-decomposicao-municipal-compativel` | oferta/matrícula por modalidade no mesmo grão municipal das ocupações |
| tempo integral × trabalho/famílias | G5 | `fator-territorial-sem-decomposicao-municipal-compativel` | fator territorial municipal e comparável |
| ocupações × formação | G5 | `transformacao-ocupacional-sem-decomposicao-municipal` | mudança ocupacional municipal, estabilidade e retirada de município |
| rede rural × território | G5 | `rede-rural-sem-decomposicao-municipal-compativel` | rede e população rural no mesmo grão municipal/temporal |
| escolaridade do emprego × EJA | G5 | `escolaridade-do-emprego-sem-decomposicao-municipal` | decomposição municipal do emprego e confronto com EJA |

Cinco das seis retenções têm o mesmo gargalo estrutural: falta decomposição municipal compatível. O principal problema já não é “achar mais correlações”; é materializar variáveis no mesmo grão e universo.

## 11. Relações e fontes descartadas

### 11.1 Descartes metodológicos

- população 0–14 × ensino médio: faixa etária incompatível;
- população total × fundamental: denominador amplo; substituído por 6–14;
- CadÚnico como público potencial de EJA ou demanda escolar: cadastro não é denominador;
- vínculos totais como trabalho juvenil: ausência de recorte de idade;
- matrícula localizada ÷ população residente sem declarar lente mista: bloqueado;
- fotografia censitária tratada como série anual: bloqueado;
- pares inventados fora do catálogo: `default-deny`;
- triagem automática por correlação: não alimenta mais a interface;
- duplicação EJA × escolaridade do emprego: consolidada em um único enredo interno;
- EP × exportações: permanece bloqueada por janela insuficiente; 2019–2025 tem 7 pontos e o mínimo é 8.

### 11.2 Decisões sobre fontes na Etapa 5

| Fonte | Decisão | Justificativa |
|---|---|---|
| nova aquisição RAIS por CBO | rejeitada | a lacuna já foi preenchida por derivação local do CSV existente |
| Novo Caged | rejeitada nesta rodada | nenhum mecanismo exigia granularidade mensal |
| Censo 2022 — deslocamento | incorporada com escopo restrito | permite residência × estudo; sem destino municipal e sem tendência temporal |
| correspondência cursos × CBO | incorporada condicionalmente para o RS | lastro para formação × ocupações, mas não resolve a decomposição municipal |

O PDF integral da 4ª edição do CNCT segue pendente por bloqueio 403; 104 fichas HTML manifestadas sustentam o mapa atual. A matriz origem–destino municipal aguarda microdados da amostra do Censo 2022.

## 12. O que já foi validado e o que permanece incerto

### 12.1 Confiança alta

- cálculos dos cinco cartões;
- decomposições `M = P × R`;
- quatro janelas de sensibilidade;
- somas municipais fechando os resultados regionais;
- comparações com RS dentro do mesmo universo;
- distribuições de fluxo do INEP;
- deslocamento com denominadores separados;
- ausência de cenário e número futuro no Vale;
- rastreabilidade dos textos, fatos, fontes e visuais;
- fallback para a experiência 2.9.0;
- fila e rollback do lote atual.

### 12.2 Incertezas e lacunas que mudam a decisão

1. **Trabalho × formação profissional:** maior bloqueio de conteúdo e do Gate 11.
2. **Validação humana:** nenhuma medição de tempo, compreensão, dúvida ou utilidade foi feita com o mantenedor ou a gestora.
3. **Transferência regional:** a cadeia analítica não rodou em VRP e Noroeste.
4. **Deslocamento:** fotografia preliminar de 2022, sem destino e sem comparabilidade temporal.
5. **EJA:** público potencial é fotografia censitária; falta contrato de leitura de nível ou série comparável.
6. **Demanda qualitativa:** não há vagas ofertadas, procura por curso, motivo de evasão ou pesquisa de ocupações em falta.
7. **Futuro:** o Vale usa tendências observadas, não projeções oficiais por idade escolar nem cenário publicado.
8. **Estado de entrega:** a implementação narrativa está no working tree local, sem alteração de `public/data`, commit ou push desta linha final.

## 13. Recomendações para avançar

### Prioridade 0 — fechar o Gate 11 sem enfraquecer G5

Materializar no mesmo grão municipal:

- ocupações CBO ao longo do tempo;
- matrículas/oferta de educação profissional por curso ou modalidade;
- correspondência curso–ocupação já versionada;
- identidade municipal e períodos compatíveis.

Depois, exigir:

- janela mínima;
- concentração municipal abaixo de 50%;
- estabilidade por retirada de município;
- distinção entre oferta localizada e trabalhadores vinculados a estabelecimentos;
- uma questão concreta de formação, sem afirmar que a oferta causa o emprego ou vice-versa.

Somente após isso deve ser criado o cartão trabalho × formação e reaberto o Gate 11.

### Prioridade 1 — aprofundar Nova Santa Rita como caso de heterogeneidade

Uma próxima análise municipal deveria integrar:

- matrículas e população por faixa, já disponíveis;
- fluxo por ano escolar e rede, não apenas etapa agregada;
- turmas, escolas e capacidade/oferta por rede;
- deslocamento por etapa e, quando disponível, origem–destino;
- comparação com pares de porte e crescimento semelhantes;
- prioridades municipais do PNE e indicadores de acompanhamento.

O objetivo não deve ser criar uma página exclusiva para Nova Santa Rita dentro do produto regional, mas usar o município para testar se a página explica adequadamente trajetórias divergentes do agregado.

### Prioridade 2 — decidir o contrato da EJA

Há duas rotas metodologicamente honestas:

1. aceitar um cartão de **fotografia de nível** em 2022, com matrícula e público potencial no mesmo grão e sem linguagem de tendência; ou
2. adquirir/materializar uma série comparável do público potencial.

A decisão precisa ser de produto e metodologia; não se deve afrouxar a janela temporal silenciosamente.

### Prioridade 3 — transferir antes de escalar

Parametrizar os motores R5/R6/R7 para Vale do Rio Pardo e Noroeste, sem texto manual por região. A transferência precisa provar:

- mesmos gates;
- mesmos schemas;
- ausência de ajuste autoral ad hoc;
- resultados úteis em estruturas territoriais contrastantes;
- fallback quando não houver mínimos 3/2.

### Prioridade 4 — executar o GA humano de verdade

O roteiro já existe. Ele deve medir se o usuário consegue:

1. explicar a queda do ensino médio;
2. encontrar o que preocupa além da demografia;
3. compreender a agenda criada pela redução dos nascimentos;
4. identificar trabalho × formação;
5. localizar municípios que contribuíram para uma mudança.

O Gate 11 só deve ser reclassificado após registrar respostas, tempo, dúvidas, termos mal compreendidos, informação útil e informação ignorada.

## 14. Perguntas recomendadas ao GPT Pro

1. A arquitetura `3 + 2` responde suficientemente às duas perguntas da gestão ou ainda parece uma seleção de casos?
2. Como incorporar a divergência de Nova Santa Rita sem transformar a página regional em dez mini-relatórios municipais?
3. Qual é o desenho mínimo e metodologicamente defensável para trabalho × formação profissional no grão municipal?
4. O teste humano deve manter trabalho × formação como tarefa bloqueante ou o contrato de produto deveria ser revisto enquanto o dado municipal não existe?
5. Qual visual torna mais clara a combinação “matrículas crescem, população jovem cresce ou cai pouco, fluxo preocupa e há deslocamento” em Nova Santa Rita?
6. A EJA deve aceitar uma fotografia de nível de 2022 ou aguardar série temporal?
7. Como distinguir visualmente, sem jargão, matrícula por local da escola e população por residência?
8. Quais indicadores municipais deveriam entrar no cartão do ensino médio para evitar que a decomposição demográfica esconda reprovação, abandono e distorção?
9. Como transferir a metodologia para VRP e Noroeste sem editar narrativas manualmente por região?
10. Que evidência adicional mudaria de fato uma decisão de planejamento, em vez de apenas enriquecer a descrição?

## 15. Artefatos, hashes e testes desta auditoria

### Artefatos principais

| Artefato | Bytes | SHA-256 |
|---|---:|---|
| pesquisa da primeira saída | 97.967 | `9852d0d106deaa3df3dcefc587a08bf3f5e14d2909d159ebe013593d55d213cd` |
| saída integrada da primeira saída | 30.874 | `cc7989a0d3417f0ba5f39f29283de9f61b1c734b03238e0ded252c1d59f7e9ea` |
| pesquisa da segunda saída | 51.191 | `bee5d4b7a255631eb6dd49a8c0cb80e7ae68d2f8ff0c5ccc26e78047e31754b8` |
| saída integrada da segunda saída | 21.326 | `daae50bcb85294af78c3fabdfa9ce233fc42f05bc904082ec8ccb74c35118078` |
| página narrativa do Vale do Sinos | 25.963 | `8f9515bf35283bb2622f823830dc1c5ff5cad4aa711158ce120edc07eab64f2c` |
| fila regional | 5.963 | `8e118bfe1e9cf7e3566bd03b783808c3168bff76f0b9332e1d834ab35cdf7274` |

### Testes reexecutados em 28 de agosto de 2026

- `npm run test:vocacoes-pne`: **98/98**;
- `npm run test:vocacoes-pne-page`: **13/13**;
- `npm run test:vocacoes-pne-publication`: **12/12**;
- `npm run check:vocacoes-pne-compilador`: bytes idênticos;
- `npm run check:vocacoes-pne-publication`: bytes idênticos.

As duas suítes que iniciam Vite foram disparadas em paralelo e emitiram um aviso transitório de porta WebSocket já em uso; ambas terminaram com código zero e todas as asserções passaram.

## 16. Estado operacional e Git

- Classificação desta tarefa: `DOCUMENTATION_ONLY`.
- Arquivo criado: este relatório.
- Fórmulas, fontes, anos, indicadores, schemas e metodologia: preservados.
- Efeito em dados públicos: nenhum.
- Banco: não usado.
- Rede externa: não usada.
- Atualização de dados: não executada.
- Build completo: não executado.
- Branch: `main`, 5 commits à frente de `origin/main` no início da auditoria.
- O working tree já continha mudanças e arquivos não rastreados da implementação Vocações × PNE; nada foi revertido, staged, commitado ou enviado.

## 17. Veredito final

O núcleo analítico do piloto está consistente e a nova página representa uma melhoria substancial sobre o baseline: menos cartões, mecanismos explícitos, variáveis compatíveis, decomposição antes da associação, heterogeneidade municipal, segunda saída efetiva e linguagem pública rastreável.

O resultado ainda não está pronto para ser tratado como plano concluído ou produto regional escalado. A falta da leitura trabalho × formação impede uma das tarefas de usuário previstas; a ausência de GA humano impede afirmar compreensão e utilidade; e a metodologia não foi transferida para duas regiões contrastantes.

Para Nova Santa Rita, os dados já mostram por que a evolução da página é necessária: o município cresce onde a região retrai, concentra problemas de trajetória no ensino médio e tem mobilidade escolar relevante. O próximo avanço de maior valor é transformar essa heterogeneidade em decisão de planejamento sem perder a escala regional nem ultrapassar o que os dados sustentam.
