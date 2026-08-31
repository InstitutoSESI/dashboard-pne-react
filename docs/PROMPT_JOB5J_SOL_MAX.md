# PROMPT — JOB 5J — LABORATÓRIO DE RELAÇÕES E INSIGHTS INTEGRADOS

Estamos continuando o projeto Vocações da Região × PNE V7 no checkpoint pós-Job 5I.

```text
MODEL = GPT-5.6 Sol
EFFORT = MAX
AUTONOMY_MODE = MAX_WITH_GUARDRAILS
JOB = 5J
CLASSIFICATION = DATA_LOGIC + ANALYTICAL_RELATIONSHIP_LAB + INSIGHT_CONTRACTS
FRONTEND = FORBIDDEN
PUBLICATION = FORBIDDEN
PUBLIC_DATA_WRITES = FORBIDDEN
PUBLIC_NAVIGATION = FORBIDDEN
GATE_11 = CLOSED
INTERNAL_ITERATIONS = UNBOUNDED_WITHIN_SCOPE
USER_VISIBLE_CHECKPOINTS = ONE
MAX_SHARED_FILES_PER_CHECKPOINT = 12
```

## Leitura obrigatória

Leia integralmente, antes de executar:

1. `docs/VOCACOES_PNE_V7_ORCHESTRATION_CONTRACT.md` — fonte permanente de verdade para objetivo, métodos, guardrails, cadência e pacote de revisão;
2. o julgamento externo pós-Job 5I que concluiu que a página atual é um explorador de evidências, mas ainda não responde satisfatoriamente ao pedido da gestora;
3. manifests, contratos, bundles, dossiês, registries e testes congelados dos Jobs 5G-A-R, 5G-B-R, 5G-C-R, 5G-D, 5H e 5I;
4. o código da página interna Job 5I apenas para compreender os dados disponíveis; não alterar frontend;
5. fontes e contratos canônicos apontados pelos `source_refs`.

Não reinicie o projeto. Não refaça materializações já aprovadas sem necessidade. Não abra nova frente de aquisição. Não transforme ausência localizada em bloqueio global.

## Objetivo central

Usar o acervo já materializado para testar relações substantivas entre educação e território e produzir conclusões integradas que respondam:

1. O que o território ajuda a compreender sobre a educação?
2. O que as transformações do território colocam na agenda da educação?

O Job 5J deve preencher a etapa que faltou entre os dados e a interface:

```text
fatos e séries
→ relações testadas
→ conclusões integradas
→ julgamento externo
```

O resultado não pode ser uma nova coleção de indicadores, famílias ou gráficos paralelos.

## Escalas obrigatórias

Toda relação material deve ser analisada, conforme a cobertura disponível, para:

- RS ou universo estadual compatível, preferencialmente os 497 municípios quando o desenho exigir referência ajustada;
- Vale do Sinos;
- distribuição dos dez municípios;
- município selecionado;
- Nova Santa Rita `4313375` como reconstrução obrigatória.

## Regra canônica

```text
network_scope = total_all_dependencies
administrative_dependency_is_analytic_dimension = false
administrative_dependency_is_QA_dimension = true
```

Dependência administrativa não pode entrar em modelos, comparações, seleções ou narrativas.

Preservar separadamente residência, residência do estudante, localização da escola, localização rural, estabelecimento de trabalho e executor municipal.

## Relações prioritárias

Execute o catálogo R1–R8 definido no contrato de orquestração, com prioridade substantiva para:

1. demografia/coortes × matrículas/escolas/turmas;
2. trajetória × oferta × mobilidade;
3. trabalho juvenil × aprendizagem × ensino médio;
4. ocupações/setores × distribuição da EPT;
5. escolaridade adulta × distribuição da EJA;
6. perfil socioeconômico × trajetória;
7. ruralidade × oferta × PNATE como contexto;
8. educação especial/AEE apenas se acrescentar valor além das contagens.

Pode acrescentar uma relação não prevista somente quando:

- houver mecanismo substantivo explícito;
- os dados já estiverem materializados;
- ela responder diretamente a uma das duas perguntas da gestora;
- não duplicar uma relação existente.

## Plano interno de execução

Conclua autonomamente todas as fases abaixo na mesma execução.

### Fase 0 — preservação e inventário

- registrar hashes dos inputs congelados;
- preservar Job 5I e `public/data`;
- mapear séries, períodos, unidades, lentes e cobertura estadual/regional;
- identificar quais relações podem usar os 497 municípios e quais ficam restritas ao Vale.

### Fase 1 — pré-especificação

Antes de observar resultados, materializar para cada relação:

- pergunta;
- mecanismo;
- resultado educacional;
- fator territorial;
- período e defasagem plausível;
- universo;
- método principal;
- testes de robustez;
- critérios de sustentação;
- claims permitidos e proibidos.

### Fase 2 — painel analítico alinhado

Criar uma camada analítica própria, sem alterar os outputs congelados, com:

- código IBGE textual;
- município e ano;
- escala territorial;
- etapa/faixa etária;
- numeradores e denominadores;
- lentes;
- flags de 2020–2021;
- pesos;
- estados zero/ausente;
- fontes e hashes.

Não fundir universos. Não interpolar. Não suavizar.

### Fase 3 — relações descritivas estruturais

Calcular, no mínimo:

- ritmos e diferenças entre coortes e oferta;
- contribuição municipal para mudanças regionais;
- diferenças de participação territorial EJA e EPT;
- concentração e distribuição, sem rótulos valorativos;
- contrastes município–Vale–RS;
- heterogeneidade entre os dez municípios.

### Fase 4 — associações e referências ajustadas

Quando cobertura e desenho permitirem:

- painel municipal anual;
- primeiras diferenças;
- efeitos fixos de município e ano;
- defasagens de um e dois anos justificadas;
- comparação com municípios semelhantes;
- modelos ponderados pelos denominadores;
- intervalos de incerteza.

Para perfil socioeconômico × trajetória, usar o RS como universo de referência sempre que os contratos permitirem.

Não executar regressão por hábito. Use-a somente quando responder à pergunta e o desenho for defensável.

### Fase 5 — robustez

Aplicar, conforme a relação:

- com e sem 2020–2021;
- janelas alternativas;
- nível e mudança;
- ponderado e não ponderado;
- leave-one-out;
- Vale versus restante do RS;
- inspeção de influência e pequenos denominadores;
- estabilidade da direção e magnitude.

Nunca selecionar por `p-value` isolado.

### Fase 6 — síntese de insights

Para cada candidata, produzir o contrato completo definido no arquivo de orquestração.

A conclusão precisa explicar:

- o que os dados integrados mostram;
- o que acrescentam além dos gráficos separados;
- a implicação concreta para planejamento;
- o que permanece proibido concluir.

Classificar em:

- `STRUCTURAL_CONTRAST`;
- `ROBUST_ASSOCIATION`;
- `TERRITORIAL_MISMATCH`;
- `PLANNING_SIGNAL`;
- `DESCRIPTIVE_CONTEXT_ONLY`;
- `NOT_SUPPORTED`;
- `NOT_EVALUABLE`.

Nenhuma categoria é causal.

### Fase 7 — autocrítica e reparo

Antes de finalizar:

- procurar justaposições disfarçadas de insight;
- procurar claims que excedem o desenho;
- procurar relações sustentadas por um único município dominante;
- verificar compatibilidade de período e lente;
- verificar se Nova Santa Rita foi reconstruída a partir das tabelas, não de texto manual;
- corrigir falhas mecânicas e repetir os testes;
- rebaixar candidatas fracas em vez de tentar preenchê-las.

## Relações mínimas a serem reconstruídas para Nova Santa Rita

Sem forçar resultado, investigar explicitamente:

1. expansão de matrículas e turmas do ensino médio versus retração regional;
2. trajetória do ensino médio versus mobilidade para outro município;
3. crescimento do trabalho formal 15–17, peso da aprendizagem e trajetória escolar;
4. crescimento do trabalho formal 18–24 e contribuição para a mudança regional;
5. transformação logística `CBO 414140`, preservando Vale `303 → 2.124` e Nova Santa Rita `17 → 722`;
6. EPT localizada igual a zero observado versus oferta regional;
7. escolaridade adulta versus distribuição da EJA;
8. perfil socioeconômico versus trajetória, se avaliável com cobertura estadual.

Não transformar nenhum desses anchors em conclusão automática.

## Exemplos de conclusão aceitável

Uma conclusão pode afirmar coexistência, contraste, contribuição, divergência territorial, associação robusta ou sinal de planejamento.

Pode dizer, se os testes sustentarem:

- que a oferta local se move em direção diferente da região;
- que o desafio não se limita à quantidade de matrículas;
- que a aprendizagem ocupa papel relevante nas admissões de 15–17;
- que uma parcela material da transformação regional ocorreu no município;
- que trabalho e formação estão territorialmente distribuídos de forma distinta;
- que um resultado está acima ou abaixo do intervalo observado em municípios semelhantes.

Não pode dizer, sem desenho causal:

- que trabalho provoca abandono;
- que mobilidade provoca reprovação;
- que falta um curso;
- que existe demanda por uma formação específica;
- que financiamento explica desempenho;
- que EPT zero localizada significa ausência de acesso;
- que a mesma pessoa aparece em educação e trabalho.

## Sem frontend

Não alterar:

- componentes React;
- CSS;
- rota interna;
- bundle UI do Job 5I;
- navegação;
- `public/data`.

O Job 5I permanece como explorador de evidências congelado.

## Outputs internos

Você pode criar quantos artefatos internos forem necessários em:

```text
.tmp/vocacoes-pne/v7-job5j
```

Não liste todos na resposta final.

## Pacote curado obrigatório — máximo 12 arquivos compartilháveis

Entregue exatamente as classes abaixo, consolidadas:

1. `CHECKPOINT_JOB5J_FOR_PRO.md`
2. `CATALOGO_INSIGHTS_CANDIDATOS_JOB5J.json`
3. `MATRIZ_RELACOES_TESTADAS_JOB5J.csv.gz`
4. `MATRIZ_HETEROGENEIDADE_10_MUNICIPIOS_JOB5J.csv.gz`
5. `DOSSIE_ANALITICO_NOVA_SANTA_RITA_JOB5J.md`
6. `DOSSIE_ANALITICO_VALE_DO_SINOS_JOB5J.md`
7. `METODOS_E_ROBUSTEZ_JOB5J.md`
8. `LIMITACOES_E_CLAIMS_JOB5J.json`
9. `QA_SUMMARY_JOB5J.json`
10. `ARTIFACT_INDEX_JOB5J.json`
11. `PACOTE_REVISAO_EXTERNA_JOB5J.json`
12. `MANIFEST_JOB5J.json`

Não criar um arquivo por município, método, relação, modelo ou teste.

O `ARTIFACT_INDEX_JOB5J.json` deve listar todos os arquivos internos adicionais com path, hash, tamanho, função e dependências, permitindo recuperação posterior sob demanda.

## QA obrigatório

Validar:

- dez municípios exatos;
- Nova Santa Rita `4313375`;
- códigos IBGE textuais;
- rede total;
- dependência administrativa somente em QA;
- lentes separadas;
- períodos alinhados;
- zero distinto de ausência;
- RAIS como estoque;
- Caged como fluxo;
- eventos distintos de pessoas;
- mobilidade somente 2022;
- PNATE não usado como mobilidade ou execução;
- EPT localizada distinta de acesso;
- ponte não aditiva;
- nenhuma seleção por ordem física/código;
- nenhum `p-value` isolado como critério;
- resultados negativos preservados;
- nenhuma causalidade;
- determinismo em duas execuções;
- testes regressivos 5G–5I;
- hashes congelados preservados;
- `public/data` intacto;
- nenhum frontend alterado.

## Estado final

Entregue um dos seguintes:

```text
JOB_5J_READY_FOR_EXTERNAL_JUDGMENT
JOB_5J_READY_WITH_EXPLICIT_LIMITS_FOR_EXTERNAL_JUDGMENT
JOB_5J_STOPPED_FOR_SUBSTANTIVE_DECISION
```

Não aprove o próprio trabalho. Não iniciar Job 5K.

Na resposta final, apresentar:

1. estado final;
2. decisão solicitada ao GPT-5.6 Pro;
3. relações testadas;
4. relações sustentadas, fracas, negativas e não avaliáveis;
5. principais conclusões do Vale;
6. reconstrução de Nova Santa Rita;
7. heterogeneidade entre os dez municípios;
8. métodos e robustez;
9. limites e claims;
10. testes e preservação;
11. lista apenas dos doze arquivos do pacote curado.
