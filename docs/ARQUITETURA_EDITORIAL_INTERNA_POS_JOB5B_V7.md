# Arquitetura editorial interna pós-Job 5B — V7

**Classificação:** `DOCUMENTATION_ONLY` — arquitetura de produto/editorial
**Estado:** `INTERNAL_ARCHITECTURE_FOR_EXTERNAL_PRODUCT_JUDGMENT`
**Data de referência:** 28 de agosto de 2026
**Autorização pública:** narrativa `false`; interface `false`; publicação `false`

## 1. Objetivo e limite

Este documento converte os quatro blocos aprovados após o Job 5B em um percurso
editorial interno para a futura página Vocações da Região × PNE. Ele define
função, ordem, fatos, fontes, períodos, lentes, acompanhamento, planejamento e
limites de cada módulo. Não é texto público, template de compilador ou
especificação de interface.

O estado canônico aplicado é:

| Frente | Estado vigente | Papel neste documento |
|---|---|---|
| `H1_DEMOGRAFIA_REDE` | `APPROVED_FOR_EDITORIAL_AUTHORING` | módulo disponível |
| `H4_EJA_DISTRIBUICAO` | `APPROVED_FOR_EDITORIAL_AUTHORING_WITH_C9_FIX` | módulo disponível com fundamental e médio separados |
| `A3_OCUPACOES_FORMACAO` | `APPROVED_FOR_EDITORIAL_PROTOTYPE_WITH_LIMITS` | módulo disponível dentro do envelope limitado |
| `A4_MOBILIDADE_COORDENACAO` | `APPROVED_FOR_EDITORIAL_PROTOTYPE_WITH_LIMITS_AND_C9_FIX` | módulo disponível, sem destino |
| `H2_TRAJETORIA_MUNICIPAL_V2` | `NOT_EVALUABLE_DUE_TO_DATA_OR_QA_LIMIT` | lacuna interna; nenhum fato editorial autorizado |
| `A3_OPTIONAL_YOUTH_CONTEXT` | `SILENTLY_DISCARDED_FROM_CURRENT_EDITORIAL_ENVELOPE` | ausente da arquitetura |

H3, A1 e A2 permanecem retidas. Nenhuma candidata foi criada ou restaurada.

## 2. Regras transversais

Toda leitura educacional usa `network_scope=total_all_dependencies`.
Dependência administrativa não é filtro, estrato, comparação, ranking,
explicação ou conclusão. Ela permanece apenas em reconstrução, fechamento,
proveniência, duplicidades, disponibilidade e QA. A ação institucional pode ser
descrita como acompanhamento, articulação, diálogo ou coordenação, sem atribuir
o resultado agregado a um ente.

As quatro lentes permanecem separadas:

| Lente | Unidade territorial | Uso |
|---|---|---|
| população | residência | coortes e público adulto |
| educação | localização da escola | matrículas, escolas, turmas, cursos e eixos |
| mobilidade | residência do estudante | residentes estudantes e residentes que estudavam fora |
| trabalho | estabelecimento | vínculos RAIS, ocupações e setores |

Não se presume que os universos contenham as mesmas pessoas. Zero observado,
`null`, `unavailable`, `suppressed` e `not_applicable` continuam distintos.
Denominador zero produz `null`; valores brutos regem decisões e o arredondamento
é apenas de apresentação.

## 3. Arquitetura disponível agora

O percurso começa por mudanças educacionais observadas e termina em agendas que
exigem articulação territorial. A contagem interna de módulos não vira conceito
da página.

| Ordem | Direção | Módulo | Função editorial interna | Transição |
|---:|---|---|---|---|
| 1 | D1 — o território ajuda a compreender a educação | H1 — Demografia, demanda e organização da oferta | consolidar educação infantil, fundamental e médio e mostrar que população e resposta observada não mudam de modo uniforme | da mudança das gerações para a distribuição territorial de públicos e oferta |
| 2 | D1 — o território ajuda a compreender a educação | H4 — EJA, escolaridade adulta e distribuição da oferta | acrescentar uma leitura não demográfica sobre onde reside o público adulto e onde se localizam as matrículas | da fotografia de escolaridade adulta para transformações do trabalho |
| 3 | D2 — o território coloca temas na agenda da educação | A3 — Ocupações e formação profissional | organizar movimentos ocupacionais, composição formativa e concentração municipal numa questão de articulação | da composição trabalho–formação para decisões que atravessam limites municipais |
| 4 | D2 — o território coloca temas na agenda da educação | A4 — Mobilidade e coordenação regional | mostrar, por residência e etapa, a parcela que estudava fora e delimitar uma agenda de coordenação | encerra com indicadores e perguntas que pedem acompanhamento compartilhado |

O percurso não afirma que H4 decorre de H1, que A3 decorre de H4 ou que A4
explica qualquer outro módulo. As transições são editoriais; não são nexos
causais ou individuais.

## 4. Arquitetura-alvo condicional

Se uma futura aquisição encontrar o denominador exato das taxas de trajetória
no grão aceito, houver regra documentada de pequeno denominador, C5 for
integralmente atendido e novo julgamento aprovar a frente, uma função de
trajetória poderá ocupar a posição entre H1 e H4:

`H1 → posição condicional de trajetória → H4 → A3 → A4`

A função reservada responderia o que a trajetória escolar acrescenta depois da
leitura de população, matrículas, escolas e turmas, antes da passagem ao público
adulto da EJA. Ela acrescentaria indicadores de permanência e fluxo ao bloco
municipal e poderia alterar a seleção das três leituras prioritárias. Até essa
aprovação, a posição não recebe texto, cartão, número, visual ou conclusão. A
lacuna e suas condições estão registradas apenas no mapa interno de lacunas.

## 5. Contrato dos módulos

### 5.1 H1 — Como a mudança das gerações está reorganizando a demanda educacional

**Função.** Consolidar educação infantil, ensino fundamental e ensino médio em
uma história navegável por etapa. População residente é ponto de partida;
matrículas, escolas e turmas localizadas acrescentam a resposta observada.

**Pergunta regional.** Como população compatível, matrículas, escolas e turmas
mudaram por etapa entre 2014 e 2025, e quais municípios seguiram direção
diferente do Vale?

**Mensagem a sustentar.** O Vale teve crescimento de matrículas em creche e
pré-escola e redução no fundamental e médio, enquanto municípios específicos
seguiram trajetórias diferentes. A organização da oferta acrescenta informação
à mudança populacional, sem ser tratada como efeito causal dela.

**Fatos aprovados.** `H1-REGION-ALL-*–2014-2025`, os fatos municipais de mesmo
grão e, para Nova Santa Rita, os seis IDs listados na matriz de módulos. Entre os
marcos internos: Vale, fundamental, 117.469→104.328; Vale, médio,
31.789→26.911; Nova Santa Rita, fundamental, 3.873→3.957; Nova Santa Rita,
médio, 799→840. Os valores pertencem à janela 2014–2025.

**Fontes e período.** População por idade do PostgreSQL SESI, lente de
residência; Censo Escolar agregado no PostgreSQL SESI, lente de escola;
materializações Job 2E e fatos Job 3. Janela principal 2014–2025. Materiais de
2015–2025 permanecem separados e não podem ser combinados com esta janela.

**Escalas.** Vale do Sinos, seus dez municípios e RS apenas quando o campo é
comparável. O bloco “No município selecionado” usa a mesma etapa e janela do
contraste regional.

**Acompanhamento.** População residente na faixa compatível, matrículas totais
localizadas, escolas e turmas, sempre por etapa e ano.

**Questão de planejamento.** Onde preservar acesso, reorganizar a oferta e
acompanhar transições diante de ritmos municipais diferentes, sem produzir uma
decisão automática sobre escolas?

**Vínculo PNE/PME.** Acesso à educação infantil; universalização e continuidade
no fundamental e no médio; planejamento territorial da oferta.

**Visual conceitual.** Perfil por etapa com população e matrícula em lentes
visualmente separadas, complementado por uma distribuição municipal compacta.
A decomposição pode sustentar a leitura, mas não deve virar jargão no primeiro
nível.

**Limites.** Não misturar janelas, chamar a relação matrícula/população de taxa
individual, atribuir resultado a dependência administrativa, inferir causa ou
recomendar abertura/fechamento automático de escola.

### 5.2 H4 — O público que ainda não concluiu a educação básica e a oferta de EJA estão distribuídos de forma diferente

**Função.** Introduzir uma fotografia de 2022 sobre a distribuição territorial
do público adulto residente e das matrículas localizadas, mantendo fundamental
e médio como leituras independentes.

**Pergunta regional.** Como as participações municipais do público residente e
das matrículas de EJA se distribuem em 2022, separadamente no fundamental e no
médio?

**Mensagem a sustentar.** A participação de cada município no público adulto e
sua participação nas matrículas não coincidem necessariamente e podem ter
sentidos opostos entre etapas. Isso define uma questão de distribuição e
coordenação, não uma medida individual.

**Fatos aprovados.** `H4-REGION-FUNDAMENTAL-2022`,
`H4-REGION-HIGH_SCHOOL-2022` e os fatos municipais. Em Nova Santa Rita, no
fundamental, 5,390738% das matrículas ante 2,742475% do público; no médio,
0,886391% ante 3,491485%. A correção C9 proíbe uma direção municipal única.

**Fontes e período.** Censos de população residente de 2022 por escolaridade e
Censo Escolar/EJA de 2022 por localização da escola, materializados no Job 2C
e julgados no Job 3/4B. A evolução de matrículas 2014–2025 pode aparecer apenas
como contexto temporal separado.

**Escalas.** Vale do Sinos e dez municípios; RS como referência quando o mesmo
universo está completo. O bloco municipal mostra ambas as etapas, ainda que uma
delas não seja selecionada para a síntese final.

**Acompanhamento.** Participações do público residente e das matrículas
localizadas por etapa na próxima fotografia compatível; matrícula anual de EJA
somente em série contextual separada.

**Questão de planejamento.** Que articulação local e regional deve acompanhar
as diferenças de distribuição por etapa, considerando onde residem os públicos
e onde estão as matrículas?

**Vínculo PNE/PME.** EJA; elevação da escolaridade da população adulta;
integração da EJA à educação profissional quando observada em fonte própria.

**Visual conceitual.** Pares de participações lado a lado por município, com
fundamental e médio em painéis separados e mesma escala visual.

**Limites.** Não unificar sentidos opostos, usar “próximo/near”, interpretar as
medidas como cobertura, atendimento, demanda, alcance, suficiência ou
capacidade, nem tratar moradores e matrículas como as mesmas pessoas.

### 5.3 A3 — As mudanças do trabalho não chegam da mesma forma à oferta de formação profissional

**Função.** Partir de movimentos líquidos observados no trabalho formal e
organizar, em quadro separado, composição e concentração dos cursos/eixos
efetivamente mapeados.

**Pergunta regional.** Quais subgrupos, ocupações e setores mudaram entre 2019 e
2025 e como a composição formativa observada em 2023–2025 se distribui no Vale?

**Mensagem a sustentar.** Mudanças ocupacionais específicas coexistem com uma
composição formativa concentrada em alguns municípios. A ponte normativa ajuda
a organizar a observação, mas é parcial, não aditiva e não mede resultado
individual ou necessidade futura.

**Fatos aprovados.** Movimento líquido 2019–2025 dos subgrupos cobertos;
composição regional de 44 cursos e 13.945 matrículas em 2025; 39 cursos e
12.664 matrículas mapeados; cinco cursos e 1.281 matrículas não mapeados;
concentração municipal observada. Para Nova Santa Rita, o estoque RAIS passou
de 8.473 para 11.591 vínculos e os fatos ocupacionais/setoriais de logística,
transporte, administração e comércio constam do dossiê Job 4A. O zero observado
da oferta técnica local no recorte não é título, conclusão ou prova de ausência
fora da fonte.

**Fontes e períodos.** RAIS por estabelecimento, 2019–2025; suplementos locais
do Censo Escolar e tabela de cursos técnicos, 2023–2025; projeção versionada da
ponte CNCT–CBO, fotografia 2025. CAGED só pode apoiar fato autorizado como
fluxo; o contexto juvenil opcional do Job 5A não integra este envelope.

**Escalas.** Vale, municípios e Nova Santa Rita. Trabalho é localizado no
estabelecimento; formação, na escola. A fonte não permite seguir residentes,
estudantes ou trabalhadores entre municípios.

**Acompanhamento.** Estoque RAIS por subgrupo/ocupação/setor; composição de
cursos/eixos e matrículas; concentração municipal; cobertura e não aditividade
da ponte.

**Questão de planejamento.** Que agenda de observação e articulação entre
municípios, Estado, instituições ofertantes e Sistema S deve confrontar a
composição do trabalho e a formação observada, preservando as duas lentes?

**Vínculo PNE/PME.** Educação profissional e tecnológica; formação de jovens e
adultos; articulação territorial da oferta formativa.

**Visual conceitual.** Dois painéis coordenados, mas não somáveis: movimento
ocupacional/setorial e composição/concentração formativa, ligados apenas pelos
subgrupos cobertos pela ponte normativa.

**Limites.** Não alegar alinhamento, aderência, déficit, demanda futura,
adequação, empregabilidade, suficiência, vagas, capacidade, expansão
necessária, promessa de emprego ou trajetória aluno–trabalho. Não somar
matrículas repetidas pela ponte nem misturar RAIS estoque com CAGED fluxo.

### 5.4 A4 — Algumas decisões educacionais dependem de coordenação além dos limites municipais

**Função.** Encerrar a segunda direção com uma fotografia de residência e
etapa, mostrando o volume e a participação dos residentes estudantes que
estudavam fora em 2022.

**Pergunta regional.** Em quais municípios e etapas a participação de
residentes que estudavam fora difere do Vale e do RS, e que rotina de
coordenação isso coloca na agenda?

**Mensagem a sustentar.** A mobilidade tem intensidades diferentes por
município e etapa. Estudar fora não é problema por si só; o fato delimita uma
agenda de acompanhamento, transição e coordenação sem identificar destino.

**Fatos aprovados.** No Vale: total 33.868/229.441 (14,7611%); fundamental
7.507/107.060 (7,0120%); médio 5.812/38.516 (15,0898%). Em Nova Santa Rita:
total 1.349/7.666 (17,5972%); fundamental 355/4.090 (8,6797%); médio 220/1.151
(19,1138%). Os comparadores estaduais oficiais permanecem separados.

**Fonte e período.** Artefato R6 de mobilidade incorporado ao Job 2E e matriz
factual Job 5A; fotografia 2022; lente de residência do estudante.

**Escalas.** Vale, dez municípios, Nova Santa Rita e comparação oficial com RS.
`destination_available=false` em todas as escalas.

**Acompanhamento.** Total de residentes estudantes, residentes que estudavam
fora e participação, por fundamental, médio e total na próxima fotografia
compatível.

**Questão de planejamento.** Que acompanhamento de transições, transporte como
contexto e diálogo territorial deve ser organizado quando residentes estudam
fora, sem presumir o lugar em que estudam?

**Vínculo PNE/PME.** Acesso e continuidade no fundamental e médio; planejamento
territorial; regime de colaboração e coordenação regional.

**Visual conceitual.** Barras de participação por município e etapa, com Vale e
RS como referências; contagens disponíveis no detalhe. Não usar mapa de fluxos.

**Limites.** Não inferir destino, rota, corredor, escola receptora, vaga,
capacidade ou dependência responsável; não combinar mecanicamente mobilidade e
oferta localizada; não apresentar estudar fora como falha.

## 6. Camada municipal e síntese

Cada módulo contém um bloco dinâmico “No município selecionado” com fato,
contraste territorial, período, fonte, indicador, questão, contexto de ação e
limite de inferência. O contrato completo está em
`ESPECIFICACAO_CAMADA_MUNICIPAL_V7.md`.

A síntese municipal seleciona no máximo três leituras, sem score ou ranking. A
regra combina: diferença útil em relação ao Vale; especificidade da questão;
cobertura das duas direções; não redundância; e preservação das lentes. O caso
de Nova Santa Rita está em `SINTESE_NOVA_SANTA_RITA_INTERNA_V7.md`.

## 7. Lacunas e gate

O mapa interno registra a posição condicional de trajetória, a ausência de
destinos em A4, a ponte parcial e a persistência não testada de A3, a decisão
pendente sobre cenários do Vale e a validação humana ainda não executada. Nada
disso vira mensagem pública de falha.

`PILOT_GATE_11_V7` permanece `BLOCKED`. Esta arquitetura pode seguir apenas para
julgamento externo de produto; não autoriza narrativa final, compilador,
interface ou publicação.
