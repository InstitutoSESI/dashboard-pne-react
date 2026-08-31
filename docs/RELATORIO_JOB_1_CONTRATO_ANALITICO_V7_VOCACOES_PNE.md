# Relatório do Job 1 — contrato analítico V7 Vocações × PNE

**Data:** 28/08/2026

**Classificação:** `DOCUMENTATION_ONLY`

**Veredito:** **Aprovado com pendências não bloqueantes**

## 1. Objetivo

Transformar o plano de aprofundamento em contrato de produto verificável antes
de qualquer nova materialização ou implementação. O aceite deste job aprova as
perguntas, os limites e os gates da V7; não aprova novos insights, narrativas,
dados ou publicação.

## 2. Fontes confrontadas

- `docs/arquivo/planos-vocacoes-regiao/PLANO_APROFUNDAMENTO_VOCACOES_PNE.md`;
- `docs/arquivo/planos-vocacoes-regiao/PLANO_IMPLEMENTACAO_VOCACOES_PNE.md`;
- `docs/AUDITORIA_PLANO_IMPLEMENTACAO_VOCACOES_PNE.md`;
- `docs/CONTRATO_PRODUTO_VOCACOES_PNE.md`, baseline V6;
- `docs/INVENTARIO_DADOS_PNE_VOCACOES.md`;
- `docs/MATRIZ_COBERTURA_ANALITICA.csv`;
- `docs/MATRIZ_PRONTIDAO_INSIGHTS.csv`;
- `docs/LACUNAS_REAIS_E_PRIORIDADES.md`;
- `docs/RELATORIO_JOB_0_APROFUNDAMENTO_VOCACOES_PNE.md`;
- `README.md`, `PRODUCT.md`, `docs/ARQUITETURA.md` e
  `docs/OPERACAO.md`.

Não houve consulta a fonte externa. Os caminhos e achados factuais vieram do
baseline e do inventário local do Job 0.

## 3. Decisões aprovadas

### 3.1 Produto

- mínimo de quatro histórias na primeira direção e três agendas na segunda;
- no máximo uma história principal de núcleo demográfico;
- pelo menos duas histórias principais úteis sem variáveis demográficas;
- consolidação dos três cartões demográficos V6 em um módulo por etapa;
- trajetória, trabalho juvenil, EJA e trabalho × formação obrigatórios no
  conjunto do piloto;
- uma candidata conta uma única vez no total 4+3;
- a mesma base só pode aparecer nas duas direções com pergunta e decisão distintas.

O catálogo contém cinco candidatas em cada direção. O conjunto-alvo inicial é:

1. primeira direção: demografia/rede, trajetória, trabalho juvenil e EJA;
2. segunda direção: coortes/rede, trabalho/permanência e ocupações/formação.

### 3.2 Camada municipal

Cada história deve ter bloco dinâmico por código IBGE textual com:

- direção local versus região;
- contribuição, somente quando recomputável;
- rede, etapa e público;
- segundo fator interpretativo;
- questão e responsabilidade específicas;
- rastreabilidade aos mesmos fatos regionais.

A síntese usa até três prioridades e uma regra de seleção explicável, sem score.
Nova Santa Rita é o caso obrigatório de validação, não um hardcode editorial. Para
abrir o Gate 11, ela precisa ter três prioridades elegíveis.

### 3.3 EJA 2022

Aprovada como fotografia transversal, separada entre ensino fundamental e médio:

- público: moradores adultos sem a etapa concluída;
- oferta observada: matrículas EJA em escolas localizadas;
- medidas principais: participações regionais e diferença em pontos percentuais;
- medida secundária: matrículas por mil, nunca cobertura ou demanda;
- série 2014–2025 de matrículas mantida como contexto independente.

Denominador zero produz `null`. Zero, ausência e supressão permanecem
distintos. A decisão aprova o desenho, não a narrativa ou os resultados.

### 3.4 Cenários do Vale do Sinos

Aprovada a opção de concluir a V7 histórica com mudanças observadas e tendências
sustentadas. Cenários do Vale do Rio Pardo e Noroeste não serão transferidos
silenciosamente. Até cenário próprio validado:

- nenhum número futuro será publicado;
- coorte observada não será chamada de projeção;
- exposição municipal não será chamada de cenário municipal;
- a ausência de cenário permanecerá silenciosa na interface;
- a aceitação da gestora sobre essa escolha será registrada na validação humana.

### 3.5 Responsabilidade e valor incremental

A taxonomia interna fechada possui cinco classes:

1. `acao_direta_rede_municipal`;
2. `coordenacao_rede_estadual`;
3. `articulacao_intermunicipal_regional`;
4. `articulacao_formacao_trabalho`;
5. `acompanhamento_sem_atribuicao_direta`.

O valor além da demografia exige um contrafactual explícito
`demography_only_counterfactual`, uma mudança de decisão
`decision_delta` e fatos rastreáveis. Gráfico adicional, correlação,
ranking ou heterogeneidade sem consequência não passam.

### 3.6 Gates e linguagem

Os checks de candidata foram separados como C1–C12. O gate macro recebeu o nome
`PILOT_GATE_11_V7` para não colidir com C11, que significa não redundância.
O Gate 11 teve sua especificação aprovada, mas permanece bloqueado.

O contrato inclui formas aprovadas e reprovadas para:

- demografia/rede;
- trajetória;
- trabalho juvenil;
- EJA 2022;
- trabalho/formação;
- camada municipal;
- responsabilidade institucional;
- cenários;
- mobilidade.

Os exemplos aprovam estruturas semânticas com marcadores, nunca números ou textos
finais fictícios.

## 4. Revisão independente

Duas revisões somente leitura foram separadas da redação:

1. mapa de lacunas V6 → V7 e descoberta dos caminhos canônicos;
2. julgamento de produto e método sobre histórias, município, EJA, cenários,
   responsabilidade, valor incremental e Gate 11.

As revisões convergiram em:

- evoluir o contrato canônico em vez de criar árvore V7 paralela;
- preservar V6 como baseline operacional e de rollback;
- aprovar o contrato, não os insights;
- separar C1–C12 do Gate 11 do piloto;
- manter trabalho × formação e validação humana como pendências;
- não iniciar implementação neste job.

Correções incorporadas após a revisão:

- regra inequívoca de contagem 4+3;
- catálogo com estado e limite de cada candidata;
- exigência de cobertura dos dez municípios para trabalho × formação;
- mobilidade limitada à fotografia sem destino;
- síntese municipal capaz de mostrar menos de três prioridades fora do gate do
  piloto;
- atores e fatos vinculados à responsabilidade institucional;
- aceitação humana da decisão sobre cenários.

## 5. Arquivos

### Alterado

- `docs/CONTRATO_PRODUTO_VOCACOES_PNE.md`: elevado à versão documental
  2.0.0; seções V7 inseridas; conteúdo V6 preservado integralmente como Anexo A.

### Criado

- `docs/RELATORIO_JOB_1_CONTRATO_ANALITICO_V7_VOCACOES_PNE.md`.

### Removidos ou movidos

- nenhum.

Não foi criado `CONTRATO_PRODUTO_VOCACOES_PNE_V7.md` nem contrato de
linguagem paralelo. Produto e linguagem permanecem no caminho canônico existente.

## 6. Fórmulas e efeito sobre dados

Nenhuma fórmula de produção foi alterada. O Job 1 apenas formalizou, para futura
implementação, as medidas EJA já previstas no plano: participação regional do
público, participação regional das matrículas, diferença em pontos percentuais e
intensidade secundária por mil.

- `public/data` alterado: não;
- `data_pipeline/data` alterado: não;
- schema/runtime alterado: não;
- fixtures, testes, geradores ou componentes alterados: não;
- publicação promovida: não.

## 7. Validações

Executadas:

- `git diff --check -- docs/CONTRATO_PRODUTO_VOCACOES_PNE.md`: aprovado;
- verificação local de links Markdown do contrato: aprovada;
- busca dirigida de todos os IDs, decisões, enum, EJA e Gate 11: aprovada;
- inspeção de `public/data` e `data_pipeline/data` no Git: sem mudanças.

Não executados, por não terem relação com `DOCUMENTATION_ONLY`:

- testes frontend e Python;
- `npm run check:fast`;
- build app-only ou completo;
- atualização de dados;
- acesso ao banco.

O `check:hygiene` não foi repetido: o Job 0 já registrou uma falha preexistente
de correspondência textual singular/plural entre o teste e `AGENTS.md`, sem
relação com este contrato.

## 8. Estado do Git e operações externas

- branch: `main`, cinco commits à frente de `origin/main` no início do job;
- working tree já continha mudanças V6 e arquivos não rastreados do trabalho
  anterior; foram preservados;
- commit, tag, push, pull request, stash, reset e restore: não executados;
- banco: não usado;
- rede: não usada;
- build completo: não executado.

## 9. Pendências

Bloqueiam conteúdo ou release, mas não o encerramento documental do Job 1:

1. materializações dos Jobs 2A–2E;
2. cálculos e candidatas do Job 3;
3. revisão metodológica independente do Job 4;
4. cobertura curso/eixo/matrícula nos dez municípios do Vale do Sinos;
5. fatos e blocos completos de Nova Santa Rita;
6. narrativa pública e migração do corpus de exemplos;
7. implementação de schema, compilador e interface;
8. validação humana, inclusive aceite da escolha sobre cenários;
9. aprovação efetiva de `PILOT_GATE_11_V7`.

## 10. Veredito

**Aprovado com pendências não bloqueantes.**

O contrato está suficientemente fechado para encerrar o Job 1 e preparar o Job 2.
Isso não autoriza iniciar automaticamente a próxima etapa: o plano exige decisão
explícita antes de materializações, novas fontes, narrativa ou promoção.
