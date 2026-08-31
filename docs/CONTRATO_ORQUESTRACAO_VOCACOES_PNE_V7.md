# CONTRATO DE ORQUESTRAÇÃO — VOCAÇÕES DA REGIÃO × PNE V7

**Status:** contrato permanente de execução e julgamento
**Projeto:** Painel SESI-RS de Inteligência Analítica Municipal
**Região-piloto:** Vale do Sinos — dez municípios
**Município obrigatório de reconstrução:** Nova Santa Rita — IBGE `4313375`
**Executor:** GPT-5.6 Sol — esforço `MAX`
**Julgador de checkpoints:** GPT-5.6 Pro
**Validação de produto:** gestora

---

## 1. Função deste documento

Este arquivo é a constituição operacional permanente do restante do projeto. Os prompts de cada job devem ser menores e conter apenas:

- o identificador do job;
- o objetivo específico da rodada;
- eventuais deltas em relação a este contrato;
- o estado final esperado.

O executor deve ler este documento, os manifests e outputs canônicos do projeto e o julgamento externo imediatamente anterior. Não deve reiniciar o projeto, repetir etapas já concluídas nem voltar a uma arquitetura limitada de módulos.

---

## 2. Diagnóstico do checkpoint atual

O Job 5I produziu uma base técnica e visual ampla, com séries, fatos, comparações e estados de disponibilidade. Porém, a página atual funciona principalmente como **explorador de evidências**: apresenta indicadores educacionais e territoriais, mas ainda não demonstra com clareza o que os dados dizem quando analisados em conjunto.

A etapa faltante é:

```text
fatos e séries
→ relações testadas
→ conclusões integradas
→ julgamento externo
→ autoria e interface orientadas por insights
```

A infraestrutura do Job 5I deve ser preservada. Ela será reutilizada como camada de evidências, não tratada como produto analítico final.

---

## 3. Pedido central da gestora

A página deve responder, de forma simultaneamente regional e municipal:

1. **O que o território ajuda a compreender sobre a educação?**
2. **O que as transformações do território colocam na agenda da educação?**

A resposta não pode ser apenas uma coleção de indicadores. Cada conteúdo principal deve explicitar:

- o resultado educacional observado;
- a transformação ou condição territorial relacionada;
- o mecanismo substantivo que justifica analisar os dados em conjunto;
- o padrão empírico encontrado;
- o que esse padrão acrescenta além dos dados isolados;
- a implicação concreta para planejamento e coordenação;
- o que os dados não permitem concluir.

---

## 4. Regra canônica de rede

Para toda análise educacional municipal:

```text
network_scope = total_all_dependencies
administrative_dependency_is_analytic_dimension = false
administrative_dependency_is_QA_dimension = true
```

A dependência administrativa pode ser usada somente para reconstrução, proveniência, fechamento, detecção de duplicidade, cobertura e QA.

É proibida como filtro, série, cartão, ranking, comparação, seleção, modelo ou narrativa.

Responsabilidades municipal, estadual, federal ou intermunicipal podem aparecer somente como contexto de governança e coordenação.

---

## 5. Lentes territoriais

Preservar separadamente:

- `resident_population` — moradores;
- `student_residence` — residência do estudante;
- `school_location` — localização da escola e da oferta;
- `rural_school_location` — localização rural da escola;
- `workplace` — localização do estabelecimento de trabalho;
- `municipal_executor` — município executor ou declarante.

É permitido analisar contrastes entre lentes, desde que cada medida seja nomeada e não se afirme que as bases observam as mesmas pessoas.

São proibidos sem fonte e desenho apropriados:

- microvínculo;
- inferência de residência pelo estabelecimento;
- inferência de destino do estudante;
- causalidade entre trabalho e trajetória;
- causalidade entre financiamento e resultado;
- inferência de acesso ou cobertura a partir de matrícula localizada.

---

## 6. Modelo operacional para reduzir rodadas

### 6.1 Regra geral

```text
INTERNAL_ITERATIONS = UNBOUNDED_WITHIN_SCOPE
USER_VISIBLE_CHECKPOINTS = ONE_PER_MACRO_JOB
AUTONOMY_MODE = MAX_WITH_GUARDRAILS
```

O executor pode realizar quantas subetapas internas forem necessárias, corrigir falhas mecânicas, repetir testes e reorganizar a implementação sem interromper o usuário.

O executor deve parar somente diante de:

- mudança substantiva de indicador;
- conflito com contrato legal canônico;
- necessidade de fonte não oficial;
- impossibilidade de preservar lentes;
- inferência causal indispensável;
- conflito real de produto;
- operação destrutiva;
- publicação ou abertura do Gate 11.

### 6.2 Restante do projeto em dois macro-jobs

#### Job 5J — Laboratório de relações e insights integrados

- sem alteração de frontend;
- testa relações pré-especificadas;
- produz conclusões defensáveis para Vale, dez municípios e Nova Santa Rita;
- classifica o grau de sustentação de cada relação;
- entrega um único pacote compacto para julgamento do GPT-5.6 Pro.

#### Job 5K — Página insight-first

- executado somente após julgamento do Job 5J;
- transforma relações aprovadas em títulos-conclusão, sínteses, evidências e implicações de planejamento;
- reutiliza o Job 5I como camada de evidência;
- implementa a versão interna para validação da gestora;
- continua sem publicação e com Gate 11 fechado.

Não eliminar o checkpoint entre 5J e 5K. Esse é o único corte estrutural indispensável: **primeiro provar as relações; depois construir a página em torno delas**.

---

## 7. Catálogo prioritário de relações do Job 5J

O executor pode acrescentar relações quando houver justificativa forte, mas deve testar primeiro as seguintes famílias.

### R1 — Demografia, coortes e resposta da oferta

Relacionar, por etapa:

- população da faixa etária;
- matrículas localizadas;
- escolas;
- turmas;
- unidades de docência;
- tempo integral, quando comparável.

Pergunta: a oferta acompanha, diverge ou responde em ritmo distinto às mudanças das coortes?

### R2 — Trajetória, oferta e mobilidade

Relacionar:

- aprovação;
- reprovação;
- abandono;
- distorção idade-série;
- matrículas e turmas do ensino médio;
- residentes que estudavam em outro município em 2022.

Pergunta: o desafio do ensino médio é apenas quantitativo ou envolve permanência, transição e coordenação territorial?

### R3 — Trabalho juvenil, aprendizagem e ensino médio

Relacionar, preservando estoque e fluxo:

- RAIS 15–17;
- admissões e desligamentos Caged 15–17;
- aprendizagem profissional;
- trajetória do ensino médio;
- matrículas e tempo integral, quando pertinente.

Pergunta: que interface entre escola e trabalho precisa ser acompanhada, sem afirmar que trabalhar causa abandono ou reprovação?

### R4 — Transformação de ocupações e setores × EPT

Relacionar:

- mudanças ocupacionais e setoriais;
- contribuição municipal para a transformação regional;
- distribuição territorial da EPT;
- cursos e eixos observados;
- ponte CBO–CNCT como correspondência normativa muitos-para-muitos.

Pergunta: onde a transformação do trabalho e a localização da formação não coincidem territorialmente, e que coordenação isso coloca na agenda?

### R5 — Escolaridade adulta × distribuição da EJA

Relacionar separadamente fundamental e médio:

- participação municipal no público residente sem a etapa concluída;
- participação municipal nas matrículas EJA localizadas;
- diferença entre essas participações;
- evolução da matrícula EJA;
- EJA integrada à EPT.

Pergunta: a distribuição territorial da oferta acompanha a distribuição regional do público residente considerado?

Nunca chamar essa diferença de cobertura, demanda ou taxa de atendimento.

### R6 — Perfil socioeconômico × trajetória escolar

Quando a cobertura estadual permitir, usar os 497 municípios do RS para estimar uma referência ajustada com variáveis como:

- porte e composição etária;
- INSE ou medida socioeconômica canônica;
- escolaridade adulta;
- urbanização/ruralidade;
- condições escolares disponíveis;
- trajetória educacional.

Pergunta: o resultado do município está dentro ou fora do intervalo observado entre municípios de perfil semelhante?

### R7 — Ruralidade, oferta e transporte

Relacionar como história secundária:

- escolas e matrículas rurais;
- ensino médio rural;
- PNATE por estágio;
- mobilidade somente como fotografia separada.

PNATE não mede rota, distância, uso efetivo, mobilidade ou resultado.

### R8 — Educação especial/AEE e distribuição territorial

Tratar como conteúdo condicional quando houver valor analítico além da descrição de contagens localizadas.

---

## 8. Métodos autorizados e exigências de robustez

O executor deve escolher o método adequado antes de observar o resultado e documentar a escolha.

Métodos possíveis:

- decomposição de mudanças e ritmos;
- diferenças de participação territorial;
- contribuição municipal para a mudança regional;
- comparação com municípios semelhantes;
- painel municipal anual;
- primeiras diferenças;
- efeitos fixos de município e ano;
- defasagens de um e dois anos quando substantivamente justificadas;
- modelos ponderados pelos denominadores educacionais;
- intervalos de incerteza;
- análise de heterogeneidade;
- testes de sensibilidade.

Testes mínimos quando aplicáveis:

- especificação em nível e em mudança;
- com e sem 2020–2021;
- janelas temporais alternativas;
- ponderado e não ponderado;
- leave-one-out de municípios dominantes;
- Vale versus restante do RS;
- efeito, intervalo e magnitude substantiva;
- direção e estabilidade do resultado.

É proibido selecionar uma relação apenas por `p-value`.

Uma associação estatística só pode gerar conclusão visível quando:

- o mecanismo foi pré-especificado;
- os universos e períodos são compatíveis;
- a magnitude é substantivamente relevante;
- o resultado é razoavelmente estável;
- as limitações permitem uma formulação pública honesta.

---

## 9. Estados analíticos permitidos

Cada candidata deve receber um dos estados:

- `STRUCTURAL_CONTRAST` — contraste contábil ou territorial diretamente demonstrado;
- `ROBUST_ASSOCIATION` — associação não causal estável em especificações adequadas;
- `TERRITORIAL_MISMATCH` — distribuição territorial de dois universos diverge de forma material;
- `PLANNING_SIGNAL` — combinação descritiva útil, mas insuficiente para afirmar associação;
- `DESCRIPTIVE_CONTEXT_ONLY` — contexto válido sem relação integrada demonstrada;
- `NOT_SUPPORTED` — relação testada e não sustentada;
- `NOT_EVALUABLE` — dados ou desenho insuficientes.

Nenhum estado representa causalidade.

---

## 10. Contrato de insight

Cada insight candidato deve conter:

```text
insight_id
manager_question
education_outcome
territorial_transformation
substantive_mechanism
territorial_scales
population_or_stage
period_alignment
methods_used
main_effect_or_contrast
uncertainty_or_stability
statewide_result
vale_result
ten_municipality_heterogeneity
selected_municipality_result
nova_santa_rita_result
incremental_value_beyond_separate_charts
integrated_conclusion_draft
planning_implication
monitoring_indicators
institutional_coordination
allowed_claims
forbidden_claims
limitations
recommended_visual
recommended_editorial_role
external_judgment_required
```

O campo `incremental_value_beyond_separate_charts` é obrigatório. Uma candidata que não consiga explicar o que acrescenta além da justaposição deve ser rebaixada ou rejeitada.

---

## 11. Política de arquivos para o orquestrador

### 11.1 Princípio

O executor pode criar quantos artefatos internos forem necessários no staging, mas deve entregar ao usuário um **pacote de revisão curado**, não uma descarga completa do diretório.

```text
MAX_SHARED_FILES_PER_CHECKPOINT = 12
MAX_SHARED_SCREENSHOTS_PER_CHECKPOINT = 4
MAX_TOTAL_SHARED_FILES = 16
```

Não criar um arquivo por município, método, teste ou figura. Consolidar em tabelas, registries e dossiês.

### 11.2 Pacote obrigatório do Job 5J — máximo 12 arquivos

1. `CHECKPOINT_JOB5J_FOR_PRO.md`
   Síntese executiva, decisões solicitadas e mapa dos resultados.

2. `CATALOGO_INSIGHTS_CANDIDATOS_JOB5J.json`
   Contrato completo de cada candidata.

3. `MATRIZ_RELACOES_TESTADAS_JOB5J.csv.gz`
   Uma linha por relação, especificação e escala relevante.

4. `MATRIZ_HETEROGENEIDADE_10_MUNICIPIOS_JOB5J.csv.gz`
   Vale + dez municípios, sem um arquivo por cidade.

5. `DOSSIE_ANALITICO_NOVA_SANTA_RITA_JOB5J.md`

6. `DOSSIE_ANALITICO_VALE_DO_SINOS_JOB5J.md`

7. `METODOS_E_ROBUSTEZ_JOB5J.md`

8. `LIMITACOES_E_CLAIMS_JOB5J.json`

9. `QA_SUMMARY_JOB5J.json`

10. `ARTIFACT_INDEX_JOB5J.json`
    Índice de todos os artefatos internos não compartilhados, com path, tamanho, hash, função e dependências.

11. `PACOTE_REVISAO_EXTERNA_JOB5J.json`

12. `MANIFEST_JOB5J.json`

O executor deve listar na resposta final somente esses arquivos. Arquivos adicionais permanecem no staging e são recuperados apenas sob demanda.

### 11.3 Pacote obrigatório do Job 5K — máximo 16 arquivos

1. `CHECKPOINT_JOB5K_FOR_PRO.md`
2. `CONTRATO_INSIGHT_FIRST_JOB5K.json`
3. `BUNDLE_INSIGHTS_UI_JOB5K.json`
4. `DOSSIE_PAGINA_NOVA_SANTA_RITA_JOB5K.md`
5. `DOSSIE_PAGINA_VALE_DO_SINOS_JOB5K.md`
6. `MATRIZ_COBERTURA_INSIGHTS_10_MUNICIPIOS_JOB5K.csv.gz`
7. `MATRIZ_QA_VISUAL_JOB5K.json`
8. `VALIDATION_REPORT_JOB5K.json`
9. `ARTIFACT_INDEX_JOB5K.json`
10. `PACOTE_REVISAO_EXTERNA_JOB5K.json`
11. `MANIFEST_JOB5K.json`
12–15. no máximo quatro screenshots representativas:
   - Nova Santa Rita desktop;
   - Vale desktop;
   - mobile;
   - impressão.

Não compartilhar quinze screenshots redundantes em uma única rodada.

---

## 12. Resposta final orientada ao orquestrador

A resposta final de cada macro-job deve ser curta o suficiente para leitura, mas precisa conter:

1. estado final;
2. decisão que o GPT-5.6 Pro precisa tomar;
3. principais resultados e resultados negativos;
4. relações que realmente acrescentam valor;
5. relações descartadas e motivo;
6. resultados de Nova Santa Rita;
7. heterogeneidade regional;
8. limites;
9. testes;
10. preservação e Git;
11. lista do pacote curado, respeitando o limite de arquivos.

O executor não aprova o próprio trabalho.

---

## 13. Regras para o Job 5K

O Job 5K deve transformar somente relações aprovadas ou explicitamente autorizadas pelo julgamento externo.

A página deve seguir:

```text
conclusão
→ evidências que sustentam a conclusão
→ como o território modifica a leitura
→ diferenças entre os municípios
→ implicação concreta para planejamento
→ limites e fontes recolhidos
```

A interface do Job 5I deve permanecer disponível como camada de evidências, mas o percurso principal não pode começar por uma grade de indicadores.

Cada história principal precisa ter:

- título-conclusão;
- síntese integrada de duas ou três frases;
- evidência visual principal;
- leitura do Vale;
- leitura do município selecionado;
- diferenças entre os dez municípios;
- implicação específica;
- limite curto;
- fontes e detalhes recolhidos.

---

## 14. Publicação e Gate 11

Até validação da gestora:

```text
PUBLICATION = FORBIDDEN
PUBLIC_DATA_WRITES = FORBIDDEN
PUBLIC_NAVIGATION = FORBIDDEN
GATE_11 = CLOSED
```

Nenhum job pode promover dados, publicar narrativa, alterar a navegação pública ou aprovar o produto final.
