# Plano de execução — avanço analítico Vocações × PNE

**Programa:** `vocacoes-pne-advanced-analytics-v1`
**Classificação principal:** `DATA_LOGIC`
**Domínios associados:** `SOURCE_REFRESH`, `DATA_PRESENTATION` e `UI_ONLY`, somente nas etapas que os declarem
**Estado:** `AA0_FECHADO_OPUS_ON_TRACK`; `AA1_EM_EXECUCAO`
**Data de abertura:** 30 de agosto de 2026
**Piloto público:** Vale do Sinos
**Município obrigatório:** Nova Santa Rita — IBGE textual `4313375`

## 1. Objetivo terminal

Transformar a página oficial de Vocações da Região em uma leitura integrada entre
educação, desenvolvimento econômico, condições sociais, demografia e futuro do
território, capaz de subsidiar revisão e planejamento do PNE sem transformar
associação ecológica ou teoria em causalidade local.

O programa está concluído somente quando:

1. existir um painel analítico estadual alinhado e reproduzível;
2. seis a oito perguntas substantivas estiverem pré-registradas e executadas;
3. cada resultado tiver método, incerteza, robustez, teto de afirmação e resultado
   negativo ou indisponibilidade preservados;
4. os mecanismos teóricos usados na interpretação tiverem referências rastreáveis;
5. existirem dossiês de evidência para o Vale do Sinos e Nova Santa Rita;
6. transformações observadas e cenários de planejamento estiverem ligados a ações,
   responsáveis, indicadores, gatilhos e cadência de revisão;
7. a página oficial publicar somente as leituras que passam todos os gates;
8. dados, narrativa, interface, impressão e fallback tiverem validação proporcional
   ao risco;
9. a versão final estiver pronta para validação humana da gestora, sem representar
   essa validação como executada antes de ela ocorrer.

## 2. Invariantes

- Código IBGE textual de sete dígitos é a única identidade municipal.
- O universo educacional público é `total_all_dependencies`; dependência
  administrativa serve apenas a reconstrução, disponibilidade, proveniência e QA.
- Preservar separadamente `resident_population`, `student_residence`,
  `school_location`, `rural_school_location`, `workplace` e `municipal_executor`.
- Não misturar estoque RAIS, eventos Caged, pessoas, matrículas ou estabelecimentos.
- Zero observado, `null`, `unavailable`, `suppressed` e `not_applicable` permanecem
  distintos; denominador zero produz `null`.
- Cálculos usam valor bruto; arredondamento ocorre apenas na apresentação ou
  serialização final.
- Nenhum índice sintético opaco e nenhum ranking municipal.
- Nenhuma triagem irrestrita de todos os pares. Mecanismo e pergunta vêm antes do
  teste.
- Teoria define mecanismo e alternativas; não prova efeito local.
- Efeitos fixos e correlações ajustadas permanecem associativos sem desenho de
  identificação.
- Linguagem causal local só pode existir para decomposição aritmética claramente
  rotulada ou quase-experimento que passe um contrato específico.
- Nenhuma alteração manual de `public/data`.
- Geração analítica modificada deve ser determinística, transacional, validada antes
  da promoção, com manifesto por último e rollback quando administrar vários arquivos.
- RS e AL permanecem isolados; este programa não amplia escopo para AL.
- A superfície oficial atual continua como fallback até o novo pacote passar o gate
  final.

### 2.1 Matriz de invariantes e prova

| Invariante | Prova obrigatória |
| --- | --- |
| IBGE textual de sete dígitos; nenhum join por nome | schema com `pattern`, teste com código de zero à esquerda e busca estática por coerções proibidas |
| `total_all_dependencies`; dependência administrativa apenas QA | contrato do painel, asserção de unicidade do universo e teste que rejeita dependência como covariável/estrato |
| Lentes territoriais separadas | catálogo de séries e teste que rejeita relação sem declarar as lentes de ambos os lados |
| Estados de disponibilidade preservados | distribuição por `availability_state` e testes distintos para zero, nulo, indisponível, suprimido e não aplicável |
| Denominador zero e ausência de truncamento | testes unitários com denominador zero e percentual bruto acima de 100% |
| Sem mineração irrestrita, ranking ou índice opaco | pré-registro fechado, catálogo default-deny e testes adversariais |
| Causalidade limitada ao desenho | `claim_ceiling` obrigatório e linter que bloqueia linguagem acima da classe de evidência |
| Sem escrita manual em `public/data` | digest antes/depois e ausência de `public/data` no conjunto de paths alterados pelo estágio |
| Publicação determinística e fail-closed | duas materializações, digest idêntico, teste de falha/rollback e manifesto por último |
| RS isolado de AL | teste de configuração/identidade e digest da publicação AL inalterado |
| Fallback oficial preservado | hashes AA0 dos bundles, teste de resolução e teste que força falha do pacote novo |

## 3. Estado inicial congelado em AA0

### 3.1 Repositório e publicação

- `main` em `4b62e17ff83e811e6826dee6c268e6b2974c9824`, cinco commits à frente de
  `origin/main` na abertura.
- O lote V7 e a promoção oficial estão no working tree; 19 paths rastreados estavam
  modificados/removidos e 224 paths estavam não rastreados.
- Nada desse lote pode ser apagado, restaurado, movido ou reescrito como efeito
  colateral deste programa.
- A promoção oficial observacional usa os bundles dos Jobs 5I/5K; o Gate 11 histórico
  do Job 5M continua fechado.

### 3.2 Evidência analítica reaproveitável, ainda não equivalente ao novo painel

- Job 5J: oito relações pré-especificadas, 33 testes/contrastes, 30 testes na família
  Benjamini–Hochberg e limites ecológicos explícitos.
- Job 5L-final F1: `497 × 3 × 4 = 5.964` resultados de trajetória; 11 de 12 modelos
  elegíveis e ganho fora da amostra do contexto em 10; 2025 é o único holdout
  temporal.
- Job 5L-final RAIS: 12.450 linhas e reconciliação canônica de 140/140 células, sem
  divergência.
- A existência desses artefatos prova viabilidade e oferece código reutilizável; não
  prova cobertura estadual alinhada para trabalho juvenil × trajetória, EPT,
  EJA, demografia, inclusão, ruralidade ou financiamento.

### 3.2.1 Matriz de reaproveitamento

| Pergunta do programa | Evidência existente | Estado em AA0 | Lacuna que AA1/AA2 deve fechar |
| --- | --- | --- | --- |
| `P1_CONTEXT_ADJUSTED_TRAJECTORY` | Job 5L-final F1, 5.964 resultados e validação municipal/temporal | `REUSABLE_WITH_LIMITS` | auditar covariáveis, calibração por subgrupos, estabilidade regional e apenas um holdout temporal |
| `P2_DEMOGRAPHY_ENROLLMENT_DECOMPOSITION` | Job 5I/5K e decomposições E2 regionais | `REUSABLE_REGIONAL_CORE` | painel municipal estadual, etapas/redes compatíveis e heterogeneidade sem rotular residual como migração |
| `P3_SCHOOL_CONDITIONS_AND_TRAJECTORY` | Job 3 H2, Job 5J R6 e contexto F1 | `PARTIAL_RESEARCH_EVIDENCE` | cobertura estadual alinhada de turmas, docentes, jornada, INSE e trajetória; modelo hierárquico validado |
| `P4_YOUTH_WORK_AND_HIGH_SCHOOL` | Job 5J R3 negativo/instável; Job 5L-final RAIS reconciliada | `FACTS_READY_ASSOCIATION_UNRESOLVED` | painel RS/497 com lentes separadas, defasagens, leads placebo e leave-one-region-out |
| `P5_OCCUPATIONS_AND_EPT` | Job 5J R4, painel CBO/setores, EPT e ponte normativa | `TERRITORIAL_MISMATCH_READY` | distribuição estadual comparável, mudança ocupacional, oferta formativa e incerteza da ponte muitos-para-muitos |
| `P6_ADULT_SCHOOLING_WORK_AND_EJA` | Job 5J R5 e Job 5L-final I5 | `STAGE_SEPARATED_DISTRIBUTION_READY` | integrar trabalho adulto sem chamar público potencial de demanda e preservar incompatibilidade do fundamental |
| `P7_RURALITY_INCLUSION_AND_ACCESS` | Job 5J R7/R8 | `PLANNING_SIGNALS_ONLY` | denominadores compatíveis, séries estaduais e distinção entre escola rural, residência, AEE e executor PNATE |
| `P8_FINANCING_OFFER_AND_CAPACITY` | fontes financeiras e contexto municipal existentes no produto | `NOT_ALIGNED_FOR_RELATION` | painel temporal, defasagem pré-registrada, capacidade/oferta separada de resultado e controle de endogeneidade |

### 3.2.2 Linha de base obrigatória de Nova Santa Rita

| Artefato | Cobertura de `4313375` | Disponibilidade e limite |
| --- | --- | --- |
| Job 5L-final F1 | 12 linhas em 2025: 3 etapas × 4 resultados | 12 resultados observados; 11 comparações dentro do intervalo esperado e 1 `NOT_EVALUABLE` (abandono nos anos iniciais); 11 valores esperados; lentes `school_location` e `resident_population_context_kept_separate` explícitas |
| Job 5L-final RAIS | 1.130 linhas, 2019–2025, faixas 15–17 e 18–24, 23 métricas | 1.002 `observed`, 128 `observed_zero`, nenhum valor nulo; 256 valores numéricos iguais a zero preservados; lente única `establishment_location_workplace` |
| Job 5J heterogeneidade | 9 linhas: R1–R8, com fundamental e médio separados em R5 | 9 linhas `observed`; lentes de população residente, residência estudantil, localização da escola, escola rural, trabalho e executor municipal permanecem separadas |

Esta cobertura não autoriza ligar as mesmas pessoas, ler local de trabalho como
residência nem transformar `NOT_EVALUABLE` em zero ou média regional.

### 3.2.3 Reconciliação da multiplicidade do Job 5J

Os 33 testes/contrastes se dividem em:

- 30 testes com p-valor, todos pertencentes à única família
  Benjamini–Hochberg e todos com `p_value_bh` materializado;
- 2 distâncias de variação total da EJA (fundamental e médio), que são medidas
  descritivas de distribuição sem p-valor amostral;
- 1 contexto PNATE pré-registrado como não regressável, devido a lentes e períodos
  não equivalentes.

Os três últimos mantêm `multiplicity_interpretation =
not_applicable_no_p_value`. Em AA2, toda família deve declarar antes do resultado
quais testes geram p-valor e qual regra metodológica legítima deixa um contraste fora
do ajuste. Ausência de p-valor nunca pode ser decidida depois de observar o efeito.

### 3.3 Linha de base validada

- `npm run test:vocacoes-pne`: 103/103 testes.
- `uv run python -m pytest data_pipeline/tests/test_vocacoes_pne_job5j.py
  data_pipeline/tests/test_vocacoes_pne_job5l_final.py -vv -s`: 17/17 testes.
- `npm run check:fast`: typecheck, lint, compilador e build app-only aprovados.
- `git diff --check`: aprovado, com apenas avisos de normalização LF/CRLF.

## 4. Escada de afirmação

| Classe interna | Evidência mínima | Linguagem pública máxima |
| --- | --- | --- |
| `OBSERVED_FACT` | fato rastreável na fonte | “foi de… para…” |
| `DISTRIBUTIONAL_PATTERN` | distribuição reconciliada e estável | “concentra-se mais/menos…” |
| `ACCOUNTING_DECOMPOSITION` | identidade que fecha no bruto | “responde por X pontos da variação” |
| `CONTEXT_ADJUSTED_COMPARISON` | validação fora da amostra e intervalo calibrado | “ficou dentro/acima/abaixo do observado em contextos semelhantes” |
| `ROBUST_ASSOCIATION` | efeito, intervalo e sensibilidades pré-registradas | “há associação ajustada consistente” |
| `LITERATURE_COMPATIBLE_MECHANISM` | literatura primária + configuração local | “mecanismo reconhecido; configuração local compatível” |
| `QUASI_EXPERIMENTAL_EFFECT` | evento, contrafactual e testes de identificação | “efeito estimado após o evento” |
| `PLANNING_SIGNAL` | fato material sem relação estável | “coloca o tema na agenda de acompanhamento” |
| `NOT_SUPPORTED_OR_UNAVAILABLE` | teste negativo ou fonte/grão ausente | não gera explicação positiva; fatos válidos podem permanecer |

Coeficiente, intervalo, p-valor, ajuste de multiplicidade, nome do modelo e classe
interna ficam na camada técnica. A página mostra conclusão, evidência, implicação,
limite curto e fonte.

## 5. Etapas e gates

### AA0 — Auditoria, preservação e contrato

**Entregáveis**

- este plano;
- inventário do estado inicial, hashes e testes;
- matriz de reaproveitamento dos Jobs 5J/5L;
- pacote mínimo para auditoria independente do Opus.

**Gate AA0**

- baseline reproduzido;
- working tree preservado;
- cada etapa posterior possui prova de aceite;
- revisão Opus reconciliada, com achados aceitos, rejeitados ou pendentes.

### AA1 — Painel analítico estadual alinhado

Construir, somente a partir de fontes locais congeladas e autorizadas, painéis
canônicos que compartilhem identidade e metadados, não necessariamente uma tabela
larga única.

**Famílias mínimas**

1. trajetória e condições escolares;
2. demografia, coortes, matrículas e organização da oferta;
3. trabalho juvenil, aprendizagem e composição dos vínculos;
4. ocupações, setores e oferta EPT;
5. escolaridade adulta e EJA por etapa;
6. vulnerabilidade, ruralidade, educação especial/AEE e capacidade financeira, onde
   os períodos e lentes forem compatíveis.

**Contrato mínimo por observação**

```text
municipality_ibge_code
year_or_reference_period
stage_or_population_group
metric_id
raw_value
unit
availability_state
universe
territorial_lens
network_scope
source_ref
source_period
method_state
```

**Gate AA1**

- 497 códigos canônicos para famílias declaradas estaduais ou razão explícita de
  cobertura parcial;
- chaves únicas no grão contratado;
- cobertura, nulos, supressões, duplicações, intervalos e quebras temporais auditados;
- fontes, fórmulas e transformações versionadas;
- duas materializações independentes com digest de árvore idêntico;
- `public/data`, banco e rede externa inalterados;
- testes focados, QA e revisão Opus aprovados ou reconciliados.

### AA2 — Pré-registro e laboratório analítico

Pré-registrar no máximo oito perguntas principais:

1. `P1_CONTEXT_ADJUSTED_TRAJECTORY`;
2. `P2_DEMOGRAPHY_ENROLLMENT_DECOMPOSITION`;
3. `P3_SCHOOL_CONDITIONS_AND_TRAJECTORY`;
4. `P4_YOUTH_WORK_AND_HIGH_SCHOOL`;
5. `P5_OCCUPATIONS_AND_EPT`;
6. `P6_ADULT_SCHOOLING_WORK_AND_EJA`;
7. `P7_RURALITY_INCLUSION_AND_ACCESS`;
8. `P8_FINANCING_OFFER_AND_CAPACITY`.

Cada pergunta registra mecanismo, resultado, exposição, lente, janela, população,
modelo principal, até duas alternativas, defasagens, sensibilidades, família de
multiplicidade, critérios de estabilidade, teto de linguagem e condição de retenção.

**Métodos permitidos conforme a pergunta**

- decomposição aritmética e shift-share;
- comparações de contexto com holdout municipal e temporal;
- painel com efeitos de município e ano, erro adequado e efeitos em escala
  interpretável;
- modelos hierárquicos com pooling parcial, quando superarem baseline e tiverem
  validação fora da amostra;
- defasagens 0–2, exclusão ou indicador de 2020–2021, lead placebo, direção inversa e
  leave-one-region-out;
- Benjamini–Hochberg por família pré-registrada;
- quase-experimento somente após inventário e contrato próprios.

**Gate AA2**

- pré-registro tem hash e precede resultados;
- todos os resultados, inclusive negativos e indisponíveis, são materializados;
- tamanho de efeito e incerteza têm precedência sobre significância isolada;
- comparação RS, Vale e Nova Santa Rita usa a mesma medida;
- nenhum resultado depende de lente fundida ou aproximação proibida;
- pacote reproduzível, testes focados e revisão Opus reconciliada.

### AA3 — Biblioteca teórica e teto de afirmação

Completar para cada candidata:

```text
mechanism_id
manager_question
primary_official_or_academic_refs
expected_observable_pattern
local_variables
alternative_explanations
falsification_or_boundary
claim_ceiling
transferability_notes
```

Priorizar literatura brasileira e documentação metodológica oficial. Nova busca ou
aquisição externa só pode ocorrer com autorização explícita e proveniência completa;
até lá, usar somente referências locais já congeladas e marcar lacunas.

**Gate AA3**

- toda referência sustenta diretamente o mecanismo atribuído;
- nenhum número externo é convertido em estimativa municipal;
- explicações alternativas e condições de refutação são públicas na camada técnica;
- literatura ausente reduz o teto, não é preenchida por prosa genérica;
- revisão Opus reconciliada.

### AA4 — Dossiês e cenários de planejamento

Produzir cinco dossiês principais para Vale do Sinos e Nova Santa Rita:

1. trajetória ajustada ao contexto;
2. demografia, coortes e rede;
3. trabalho juvenil e ensino médio;
4. transformação econômica e EPT;
5. escolaridade adulta, trabalho e EJA.

Ruralidade, inclusão/AEE e financiamento entram como dossiê adicional ou camada
transversal quando acrescentarem valor não redundante.

Os cenários do Vale serão condicionais e transparentes, combinando coortes já
nascidas, transformação do trabalho, vulnerabilidade e organização regional. Não
publicar número futuro municipal fora de modelo validado e cenário identificado.

Cada agenda contém:

- transformação observada ou condição de cenário;
- público, etapa e território expostos;
- situação educacional de partida;
- ação ou decisão concreta;
- responsabilidade `municipal`, `regional/shared` ou `external`;
- indicadores, baseline, gatilho e cadência de revisão;
- evidência que fortaleceria ou enfraqueceria a leitura.

**Gate AA4**

- cinco dossiês completos ou indisponibilidade substantiva demonstrada;
- cenários internamente coerentes, não intercambiáveis e sem previsão disfarçada;
- fatos e narrativas reconciliados no valor bruto;
- utilidade incremental além de gráficos separados;
- revisão Opus reconciliada.

### AA5 — Seleção editorial e integração oficial

Selecionar entre três e cinco leituras e entre duas e quatro agendas. A seleção não
é automática: exige evidência, materialidade, estabilidade, comunicação e valor para
o planejamento.

Cada cartão público contém:

1. conclusão;
2. duas ou três evidências;
3. comparação municipal/regional/estadual compatível;
4. mecanismo e alternativas em detalhe recolhido;
5. implicação para o planejamento;
6. indicadores de acompanhamento;
7. limite curto e fontes.

**Gate AA5**

- bundles gerados por allowlist, com hash, tamanho e registro;
- fallback oficial atual preservado e acionado em falha;
- nenhuma candidata retida aparece ou gera ausência ruidosa;
- identidade municipal e camada regional reconciliadas;
- desktop, tablet, mobile e impressão legíveis;
- revisão Opus reconciliada antes de avançar.

### AA6 — Validação final e entrega

**Provas obrigatórias**

- testes Python das unidades analíticas e materializações;
- testes de contrato, linguagem, dados e publicação;
- `npm run typecheck`, `npm run lint`, `npm run check:fast`;
- E2E oficial em desktop, tablet, mobile e impressão;
- `git diff --check` e `npm run check:hygiene` antes de qualquer commit;
- auditoria de fontes, fórmulas, arquivos, efeito sobre dados públicos, hashes,
  contagens, banco, rede e build completo;
- auditoria final Opus sobre requisitos e evidência, seguida de reconciliação;
- pacote e roteiro de validação humana para a gestora.

O programa pode ficar tecnicamente pronto para validação humana. Somente a gestora
ou o mantenedor podem registrar que a validação humana ocorreu e abrir um gate que a
exija; o sistema nunca fabricará essa aprovação.

### 5.1 Artefatos, comandos e limiares canônicos

Todo estágio produz `docs/RELATORIO_AA<N>_AVANCO_ANALITICO_VOCACOES_PNE.md` e
`docs/REVISAO_OPUS_AA<N>_AVANCO_ANALITICO_VOCACOES_PNE.md`. Mudança de nome exige
aditivo neste plano antes da execução.

O verificador do AA0 possui dois modos deliberadamente distintos. Sem `--allowlist`,
`--check` recompõe o manifesto do estado protegido e exige igualdade byte a byte.
Com `--allowlist <arquivo.json>`, o manifesto AA0 armazenado é a referência: apenas
os paths exatos ou prefixos `/**` declarados para o estágio podem ser criados,
alterados ou removidos; toda entrada anterior fora da lista continua conferida por
estado Git, blob do índice, tamanho e SHA-256. Novos paths sujos fora da lista falham.
Os cinco bundles oficiais, o plano, `HEAD` e upstream também permanecem conferidos,
salvo quando um path for explicitamente autorizado. A própria allowlist é evidência
do estágio e deve permanecer versionada ou no pacote canônico correspondente.

| Estágio | Artefatos canônicos | Comandos mínimos | Condição de aprovação |
| --- | --- | --- | --- |
| AA0 | este plano; `data_pipeline/manifests/vocacoes-pne-aa0-worktree-baseline.json`; `scripts/checks/generate-vocacoes-pne-aa0-baseline.mjs`; relatório e revisão Opus AA0 | `node scripts/checks/generate-vocacoes-pne-aa0-baseline.mjs --check`; `npm run test:vocacoes-pne`; pytest Jobs 5J/5L-final; `npm run check:fast`; `git diff --check` | 19 paths rastreados e 224 não rastreados do baseline preservados; 5 bundles oficiais com hash; 103/103 JS, 17/17 Python, `check:fast` e diff aprovados; Opus sem achado alto não resolvido |
| AA1 | `data_pipeline/contracts/vocacoes-pne-advanced-panel-v1.json`; `data_pipeline/src/vocacoes_pne_advanced_panel.py`; runner; teste focado; pacote `.tmp/vocacoes-pne/advanced-analytics-v1/aa1/` com painel normalizado, catálogo, QA e manifesto | `uv run python -m pytest data_pipeline/tests/test_vocacoes_pne_advanced_panel.py -vv`; runner `--check`; baseline AA0 `--check`; `git diff --check` | 497 códigos válidos nas famílias estaduais ou cobertura parcial nomeada; 0 chave duplicada; 0 fonte/lente/unidade não resolvida; todos os estados de disponibilidade válidos; dois pacotes com digest idêntico; `public/data` inalterado; Opus reconciliado |
| AA2 | `data_pipeline/contracts/vocacoes-pne-advanced-analysis-v1.json`; pré-registro versionado; módulo/runner/teste; pacote AA2 com resultados, robustez, heterogeneidade, claims, QA e manifesto | pytest AA2; runner `--check`; validação do hash do pré-registro; baseline AA0 `--check`; `git diff --check` | exatamente 8 perguntas com estado terminal; 100% dos p-valores na família pré-declarada recebem BH; 0 candidata sem efeito/intervalo/robustez/teto; RS, Vale e NSR comparáveis; negativos preservados; Opus reconciliado |
| AA3 | `data_pipeline/contracts/vocacoes-pne-mechanism-library-v1.json`; `docs/BIBLIOTECA_MECANISMOS_AVANCO_ANALITICO_VOCACOES_PNE.md`; validador/teste de referências | pytest do catálogo; verificador de referências locais; baseline AA0 `--check`; `git diff --check` | 8/8 perguntas com mecanismo, padrão, alternativas, fronteira e teto; 0 referência órfã; candidata pública sem referência primária = 0; lacuna não preenchida por fonte inventada; Opus reconciliado |
| AA4 | módulo/runner/teste de dossiês; pacote AA4 com 5 dossiês regionais, 5 dossiês NSR, cenários, agendas, QA e manifesto | pytest AA4; runner `--check`; recomposição numérica; baseline AA0 `--check`; `git diff --check` | 5/5 famílias com dossiê ou indisponibilidade provada; NSR presente; ao menos 3 cenários condicionais não intercambiáveis; cada agenda tem responsável, indicadores, baseline, gatilho e cadência; 0 número futuro não autorizado; Opus reconciliado |
| AA5 | `src/features/vocacoes-regiao/generated/vocacoesPneAdvancedInsightsValeDoSinos.json`; registro/hash; componente oficial e estilos; testes de dados, contrato, rota e E2E | testes AA5; `npm run test:vocacoes-pne`; `npm run check:fast`; E2E desktop/tablet/mobile/print; teste forçado de fallback; baseline AA0 com allowlist dos paths AA5; `git diff --check` | 3–5 leituras e 2–4 agendas; 10 municípios canônicos e NSR; allowlist sem chave interna; fallback válido; 0 overflow/bloqueio de foco; impressão legível; Opus reconciliado |
| AA6 | relatório final, inventário de fontes/fórmulas/arquivos/hashes, pacote de validação humana e revisão Opus final | suítes AA1–AA5; `npm run test:vocacoes-pne`; `npm run check:fast`; `npm run check:hygiene`; E2E oficial; build completo somente se a promoção de release for autorizada; `git diff --check` | 0 falha; hashes e contagens reconciliados; nenhum dado público parcial; banco/rede/build declarados; todos os requisitos auditados; nenhuma lacuna material do Opus sem resolução; pronto para validação humana |

O build completo é deliberadamente adiado de AA0 para AA6: ele copia toda a árvore
de dados e não acrescenta prova ao contrato documental inicial. AA5 usa build
app-only e E2E; AA6 executa build completo apenas quando houver autorização para a
validação de release, preservando a regra operacional do repositório.

## 6. Política de auditoria Opus

Ao final de AA0–AA6:

1. preparar pacote mínimo sem credenciais, dados pessoais ou arquivos alheios;
2. enviar plano/aceite e evidências da etapa ao executor guardado
   `opus-verifier`, modelo exato Claude Opus 5 e esforço máximo;
3. registrar o veredito `ON_TRACK`, `AT_RISK`, `OFF_TRACK` ou
   `INSUFFICIENT_EVIDENCE`;
4. verificar cada achado no repositório;
5. aplicar ajustes válidos antes de avançar;
6. documentar achados rejeitados com evidência contrária;
7. não substituir o Opus por outro modelo se o executor guardado falhar.

## 7. Definição de pronto

O programa termina somente quando todos os gates AA0–AA6 estiverem provados por
evidência atual, a auditoria final não tiver lacuna material não reconciliada e a
página estiver pronta para avaliação humana. Falta de dado legítima pode permanecer,
mas deve reduzir o teto de afirmação e não pode ser mascarada por proxy ou prosa.
