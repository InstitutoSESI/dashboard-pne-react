# Arquitetura editorial interna revisada — V7

**Classificação:** `DATA_PRESENTATION`
**Estado:** `INTERNAL_MANAGER_REVIEW_ONLY`
**Data de referência:** 28 de agosto de 2026
**publication_allowed_now:** `false`
**interface_allowed_now:** `false`
**compiler_allowed_now:** `false`

## 1. Objetivo

Esta arquitetura transforma os quatro módulos vigentes em uma página
compreensível para a gestora, sem implementar texto público, compilador ou
interface. O percurso explica como a página funcionará, que fatos apresentará e
quais decisões permanecerão para expansão.

Módulos disponíveis:

1. `H1_DEMOGRAFIA_REDE`;
2. `H4_EJA_DISTRIBUICAO`;
3. `A3_OCUPACOES_FORMACAO`;
4. `A4_MOBILIDADE_COORDENACAO`.

`H2_TRAJETORIA_MUNICIPAL_V2` fica fora do protótipo:
`NOT_EVALUABLE_DUE_TO_DATA_OR_QA_LIMIT` e
`DEFERRED_FROM_CURRENT_OPEN_DATA_PILOT`. H3, A1, A2 e o contexto juvenil
opcional de A3 não são restaurados. A posição de H2 não produz vazio visível.

## 2. Regras transversais

Toda análise educacional usa `network_scope=total_all_dependencies`. A
dependência administrativa pode existir somente para reconstrução, fechamento,
proveniência, disponibilidade e QA. Atribuições institucionais aparecem apenas
como ação, articulação, diálogo ou coordenação.

As lentes permanecem separadas:

| Conteúdo | Lente |
|---|---|
| população | residência |
| matrículas, escolas, turmas, cursos e eixos | localização da escola |
| mobilidade | residência do estudante |
| trabalho | localização do estabelecimento |

Esses universos não são presumidos como as mesmas pessoas. Não há causalidade,
score, recomendação automática ou cruzamento individual.

## 3. Ordem e função do percurso

| Ordem | Direção | Função |
|---:|---|---|
| 1 | o território ajuda a compreender a educação | consolidar população, matrículas e organização observada por etapa |
| 2 | o território ajuda a compreender a educação | comparar a distribuição do público adulto residente com a das matrículas de EJA, por etapa |
| 3 | o território coloca temas na agenda da educação | mostrar movimentos observados do trabalho e composição da formação em painéis independentes |
| 4 | o território coloca temas na agenda da educação | mostrar mobilidade por residência e formular uma questão de coordenação |

As transições são editoriais. Um módulo não explica nem causa o seguinte.

## 4. Títulos de trabalho

Os títulos são internos e dependem da decisão da gestora.

| Módulo | Recomendado | Alternativas |
|---|---|---|
| H1 | **População e organização educacional mudam em ritmos diferentes** | Gerações e matrículas seguem ritmos diferentes no Vale; Etapas e municípios mostram mudanças distintas |
| H4 | **Público adulto e matrículas de EJA têm distribuições diferentes** | A distribuição da EJA muda entre fundamental e médio; Moradia e matrículas de EJA formam mapas distintos |
| A3 | **Mudanças nas ocupações e composição da formação profissional** | Ocupações e formação profissional em dois retratos do Vale; Trabalho formal e cursos técnicos mostram composições territoriais |
| A4 | **Moradia e local de estudo ultrapassam limites municipais** | Estudar fora do município pede acompanhamento compartilhado; Mobilidade educacional varia por etapa e município |

Nenhuma opção é título público definitivo.

## 5. Contratos editoriais

### 5.1 População e organização educacional

**Função.** Reunir educação infantil, fundamental e médio numa navegação por
etapa, mostrando mudança regional, diferença municipal e organização observada.

**Painéis.**

1. população residente, com contagens e unidade próprias;
2. matrículas, escolas e turmas por localização da escola, em painel distinto.

As séries têm cores, legendas e eixos próprios. Não existe razão implícita nem
eixo que sugira cobertura ou equivalência individual.

**Fatos.** O Vale registra, entre 2014 e 2025, matrículas de creche
13.943→19.617, pré-escola 17.251→20.716, fundamental 117.469→104.328 e médio
31.789→26.911. A camada municipal usa a mesma etapa e janela.

**Acompanhar.** População compatível, matrículas localizadas, escolas e turmas
por etapa.

**Questão.** Onde preservar acesso, reorganizar a oferta e acompanhar
transições sem produzir decisão automática sobre escolas?

**Fontes/período.** População por idade e Censo Escolar agregado; residência e
localização da escola; 2014–2025. Materiais 2015–2025 ficam separados.

### 5.2 EJA e população adulta

**Função.** Apresentar uma fotografia de 2022 com fundamental e médio
separados, comparando a distribuição do público residente e a distribuição das
matrículas localizadas.

**Visual.** Pares de participações municipais, em dois painéis por etapa e com
mesma escala. Os totais regionais dão contexto, mas não criam medida individual.

**Regra de cálculo editorial.** Participação municipal do público, participação
municipal das matrículas e diferença distributiva. O cálculo
`matriculas_por_mil` é somente documental/QA:
`public_eligible=false` e `editorial_message_allowed=false`.

**Acompanhar.** Participações e diferenças distributivas por etapa na próxima
fotografia compatível.

**Questão.** Que articulação local e regional deve acompanhar distribuições
distintas no fundamental e no médio?

**Fontes/período.** Censo 2022 por escolaridade da população residente e Censo
Escolar/EJA por localização da escola; fotografia 2022.

### 5.3 Ocupações e formação profissional

**Função.** Colocar lado a lado, sem somar, movimentos líquidos observados no
trabalho formal entre 2019 e 2025 e a composição de cursos/eixos observada em
2023–2025.

**Visual.** Dois painéis independentes: ocupações/setores por estabelecimento e
cursos/eixos por escola. A ponte normativa organiza apenas os subgrupos
cobertos; é parcial e não aditiva.

**Fatos.** No Vale, escriturários 33.704→39.635, técnicos de ciências físicas,
químicas e engenharia 6.232→8.103, e trabalhadores têxteis, de curtimento,
vestuário e artes gráficas 21.748→18.843. Em 2025, 39 de 44 cursos e 12.664 de
13.945 matrículas estavam mapeados; cinco cursos e 1.281 matrículas não estavam
mapeados.

**Acompanhar.** Estoque RAIS, composição de cursos/eixos, concentração e
cobertura da ponte.

**Questão.** Que agenda de observação e articulação deve confrontar as duas
composições sem ligar pessoas ou prometer resultados?

**Fontes/períodos.** RAIS 2019–2025; Censo Escolar/cursos técnicos 2023–2025;
ponte CNCT–CBO, fotografia 2025.

### 5.4 Mobilidade e coordenação

**Função.** Mostrar a fotografia de 2022 para total, fundamental e médio:
residentes estudantes, residentes que estudavam fora e participação, com Vale
e RS como referências.

**Visual.** Barras municipais por etapa e referências territoriais; contagens
no detalhe. Não há mapa de fluxos.

**Limite central.** O destino não está disponível. Não se inferem rota, escola
receptora, vaga, capacidade ou ente responsável; estudar fora não é falha em
si.

**Acompanhar.** A mesma tríade na próxima fotografia compatível.

**Questão.** Que rotina de transição, transporte como contexto e diálogo
territorial deve ser organizada?

**Fonte/período.** Mobilidade educacional por residência do estudante;
fotografia 2022.

## 6. Camada municipal

Cada módulo contém “No município selecionado”, preenchido por código IBGE
textual de sete dígitos. O bloco traz fato, contraste compatível, período,
fonte, indicador, questão, contexto de ação e inferências proibidas.

A síntese municipal seleciona no máximo três leituras, sem pontuação. Quando
trabalho/formação e mobilidade ocupam uma leitura, usam subtítulos independentes
e não formam uma conclusão conjunta.

Nova Santa Rita (`4313375`) é o caso obrigatório. Seu protótipo específico
está em `PROTOTIPO_NOVA_SANTA_RITA_GESTORA_V7.md`.

## 7. Encerramento

O fechamento reúne indicadores a acompanhar e separa três tipos de decisão:

- observação de tendências e composições;
- articulação entre responsáveis e instituições;
- coordenação quando os fatos atravessam limites municipais.

Fontes e períodos permanecem acessíveis em cada módulo. Nenhuma leitura produz
recomendação automática. O pacote termina em decisão humana de escopo.
