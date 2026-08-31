# ADENDO ANALÍTICO PERMANENTE — Vocações da Região × PNE V7

## Aprofundamento socioeconômico, relações diretas e página reveladora

**Status:** orientação permanente para os Jobs 5L, 5M e eventuais manutenções posteriores
**Projeto:** Painel SESI-RS de Inteligência Analítica Municipal — Vocações da Região × PNE
**Região inicial:** Vale do Sinos
**Município de reconstrução obrigatória:** Nova Santa Rita — IBGE `4313375`
**Executor:** GPT-5.6 Sol, esforço `MAX`
**Julgador dos checkpoints:** GPT-5.6 Pro
**Validação do produto:** gestora
**Gate 11:** fechado até validação humana

---

# 1. Problema que este adendo corrige

Os Jobs 5I e 5K construíram uma base visual e editorial robusta, mas algumas relações foram tratadas de forma excessivamente binária:

```text
associação robusta
ou
exclusão/rebaixamento
```

Essa regra é inadequada para uma página territorial porque:

- muitas relações relevantes são descritivas, distributivas, condicionais ou contextuais;
- dez municípios oferecem baixo poder para vários testes ecológicos;
- algumas fontes observam apenas um ano;
- município, escola, estudante, residência e estabelecimento de trabalho pertencem a níveis e lentes diferentes;
- uma relação pode ser valiosa para planejamento sem autorizar causalidade;
- um resultado negativo pode limitar uma explicação, sem apagar os fatos materiais.

A regra permanente passa a ser:

> **O rigor determina o teto da linguagem e o papel editorial; não elimina automaticamente uma relação útil.**

É proibido interpretar:

```text
NOT_SUPPORTED
```

como:

```text
IRRELEVANTE
NÃO EXISTE RELAÇÃO
REMOVER OS FATOS DA PÁGINA
```

---

# 2. Objetivo permanente

Produzir uma página simples para a gestora, mas apoiada por análises profundas, capaz de revelar:

1. como o contexto socioeconômico modifica a interpretação dos resultados educacionais;
2. como estudo e trabalho coexistem entre jovens, quando uma fonte observa a mesma pessoa;
3. como mudou a composição educacional, contratual e remuneratória do trabalho juvenil;
4. que funções diferentes os municípios exercem como lugar de residência, trabalho, estudo e formação;
5. como migração e mudança populacional alteram a organização da oferta;
6. como o público adulto, suas condições de trabalho e a localização da EJA se distribuem;
7. quais relações são diretamente observadas, quais são comparações ajustadas, quais são padrões territoriais e quais são apenas sinais apoiados pela literatura.

A página pública não deve mostrar modelos, coeficientes ou jargão. O trabalho técnico existe para produzir conclusões melhores.

---

# 3. Regra canônica de rede

Toda análise educacional municipal continua obedecendo:

```text
network_scope = total_all_dependencies
administrative_dependency_is_analytic_dimension = false
administrative_dependency_is_QA_dimension = true
```

A dependência administrativa pode ser usada apenas para reconstrução, proveniência, fechamento, disponibilidade e QA.

Mesmo quando a estimação interna usar escolas como unidades, a saída municipal deve representar a rede total. Dependência administrativa não pode ser covariável explicativa, estrato de comparação, filtro, ranking ou narrativa.

---

# 4. Lentes territoriais

Preservar separadamente:

```text
resident_population
student_residence
school_location
rural_school_location
workplace
municipal_executor
```

Quando microdados oficiais observarem educação e trabalho na mesma pessoa, criar uma lente própria:

```text
person_residence_same_record
```

Isso não autoriza vincular essa pessoa a RAIS, Caged, Censo Escolar ou qualquer outra fonte.

Cada conclusão deve declarar internamente:

- unidade observada;
- lente;
- período;
- universo;
- se as mesmas pessoas são ou não observadas;
- se a relação é descritiva, preditiva, associativa ou causal.

---

# 5. Escada de evidência

Toda conclusão candidata deve receber exatamente um nível.

## E1 — RELAÇÃO DIRETA NO MESMO REGISTRO

A fonte observa, na mesma pessoa ou unidade:

- estudo;
- trabalho;
- escolaridade;
- deslocamento;
- renda;
- jornada;
- demais dimensões usadas na conclusão.

Linguagem permitida:

> “Entre os residentes observados…”

> “A parcela que estudava e trabalhava era…”

Não transformar um corte transversal em trajetória ou causalidade.

## E2 — COMPARAÇÃO AJUSTADA AO CONTEXTO

O resultado observado é comparado a uma distribuição ou intervalo estimado para contextos semelhantes.

Exemplos:

- trajetória observada versus intervalo esperado considerando INSE, porte, ruralidade, condições escolares e trajetória anterior;
- município versus pares semelhantes construídos por método transparente.

Linguagem permitida:

> “Considerando o contexto observado…”

> “O resultado ficou dentro/acima/abaixo do intervalo observado em contextos semelhantes…”

Isso é comparação contextualizada, não efeito causal nem ranking.

## E3 — PADRÃO TERRITORIAL CONVERGENTE

Fontes diferentes, com lentes preservadas, mostram concentração, divergência ou função territorial compatível.

Exemplos:

- participação na transformação do trabalho versus participação na EPT;
- participação no público adulto versus participação na EJA;
- residência juvenil versus vínculos no local de trabalho.

Linguagem permitida:

> “O conjunto mostra…”

> “As distribuições apontam…”

> “O município exerce uma função mais concentrada em…”

Não afirmar que as fontes observam as mesmas pessoas.

## E4 — MECANISMO DA LITERATURA COMPATÍVEL COM O CONTEXTO LOCAL

Literatura oficial ou acadêmica primária sustenta um mecanismo; os dados locais mostram uma configuração compatível, mas não estimam o efeito local.

Linguagem permitida:

> “A literatura identifica esse fator como relevante; os dados locais mostram uma configuração que merece acompanhamento.”

A literatura não substitui o dado local e não transforma compatibilidade em causalidade.

## E5 — SINAL DESCRITIVO DE PLANEJAMENTO

Há um fato material, mas a relação permanece incerta, transversal, instável ou incompleta.

Linguagem permitida:

> “O movimento coloca na agenda…”

> “A dimensão deve ser acompanhada…”

## E6 — RELAÇÃO NÃO SUSTENTADA

O teste não sustenta a associação proposta.

A consequência é:

- bloquear a explicação;
- preservar fatos materiais;
- registrar o resultado negativo como fronteira;
- reformular a pergunta quando houver método/fonte mais apropriado.

Linguagem permitida:

> “Nos dados disponíveis, a comparação não mostrou um padrão consistente.”

Nunca:

> “Não existe relação.”

---

# 6. Critério editorial

A decisão editorial deve combinar:

```text
evidence_level
claim_ceiling
manager_value
local_materiality
regional_materiality
stability
communicability
data_quality
incremental_value_beyond_separate_charts
```

Não usar score único opaco.

Estados permitidos:

```text
PRIMARY_INSIGHT
SECONDARY_CONTEXT
CONDITIONAL_EVIDENCE
INTERPRETATION_BOUNDARY
TECHNICAL_ONLY
UNAVAILABLE_WITH_REASON
```

Uma relação pode ser `E6` e ainda ter:

```text
component_facts = PRIMARY_OR_SECONDARY
association_claim = INTERPRETATION_BOUNDARY
```

---

# 7. Prioridades analíticas permanentes

## P1 — Trajetória ajustada ao contexto socioeconômico

Pergunta:

> A trajetória do município está dentro ou fora do intervalo observado em escolas e municípios de contexto semelhante?

Usar, quando disponíveis e comparáveis:

- INSE;
- escolaridade adulta;
- vulnerabilidade social oficial;
- porte;
- composição etária;
- ruralidade;
- tamanho da escola;
- tempo integral;
- adequação e regularidade docente;
- infraestrutura e conectividade;
- trajetória anterior;
- efeitos de ano.

Preferir:

- painel RS;
- escola-ano para estimação interna;
- saída municipal de rede total;
- modelos multinível ou hierárquicos;
- intervalos preditivos;
- validação temporal/holdout;
- calibração;
- análise de sensibilidade.

Não usar:

- dependência administrativa como explicação;
- ranking;
- “valor agregado” sem desenho apropriado;
- linguagem causal;
- comparação ajustada sem validação fora da amostra.

## P2 — Estudo e trabalho na mesma pessoa

Quando os microdados oficiais do Censo 2022 estiverem disponíveis e suportarem a precisão:

Para 15–17 e 18–24 anos, estimar:

- somente estuda;
- estuda e trabalha;
- somente trabalha;
- não estuda nem trabalha;
- frequência por etapa;
- nível de instrução;
- jornada;
- rendimento;
- deslocamento para estudo;
- deslocamento para trabalho;
- tempo de residência/migração, quando disponível.

Usar:

- pesos amostrais;
- desenho amostral conforme documentação;
- erro-padrão;
- coeficiente de variação;
- contagem não ponderada;
- estados de precisão e indisponibilidade.

Quando o município não tiver precisão suficiente, usar Vale ou agrupamento territorial compatível. Não fabricar estimativa municipal.

## P3 — Qualidade e composição do trabalho juvenil

Usar RAIS oficial, com dicionário oficial versionado, para observar:

- escolaridade;
- remuneração;
- jornada contratual;
- tipo de vínculo;
- aprendizagem;
- permanência/tempo no vínculo, quando disponível;
- ocupação;
- setor;
- tamanho do estabelecimento, quando disponível.

Separar:

- 15–17;
- 18–24;
- estoque;
- fluxo;
- remuneração nominal e real.

Só afirmar crescimento real de remuneração com deflator oficial e contrato explícito.

## P4 — Balanço funcional dos municípios

Comparar participações territoriais, sem score:

- jovens residentes;
- estudantes residentes;
- matrículas localizadas;
- vínculos nos estabelecimentos;
- aprendizagem;
- transformação ocupacional;
- EPT;
- público adulto;
- EJA.

Produzir diferenças em pontos percentuais, razões e decomposições transparentes.

Permitir perfis descritivos como:

- concentração maior de trabalho que de formação;
- concentração maior de formação que de trabalho;
- residência juvenil acima/abaixo da concentração de vínculos;
- participação na EJA diferente da participação no público adulto.

Não chamar de déficit, excesso, demanda ou desempenho.

## P5 — Migração e reorganização da oferta

Quando os microdados permitirem:

- migração recente;
- famílias com crianças/adolescentes;
- idade;
- frequência escolar;
- trabalho;
- escolaridade;
- deslocamentos.

Relacionar por padrão territorial e sequência temporal, sem inferir causalidade.

## P6 — Escolaridade adulta, trabalho e EJA

Investigar:

- idade;
- trabalho;
- jornada;
- rendimento;
- deslocamento;
- situação de frequência;
- etapa não concluída;
- distribuição da EJA localizada.

Distinguir:

- necessidade potencial;
- matrícula localizada;
- frequência observada;
- barreira plausível;
- acesso efetivamente medido.

Nunca chamar o público residente de demanda manifesta.

---

# 8. Política de literatura

É permitido usar:

- documentos oficiais;
- artigos acadêmicos revisados por pares;
- working papers de instituições públicas reconhecidas;
- documentação metodológica das fontes;
- literatura brasileira prioritariamente;
- estudos internacionais apenas para mecanismos gerais transferíveis.

Não usar como base substantiva:

- blogs;
- textos promocionais;
- consultorias sem método verificável;
- matérias jornalísticas como fonte metodológica;
- rankings comerciais.

A literatura deve:

1. pré-especificar mecanismos;
2. justificar métodos;
3. definir o teto de linguagem;
4. oferecer comparação conceitual;
5. nunca fornecer números municipais.

Cada mecanismo deve registrar:

```text
mechanism_id
question
literature_refs
expected_observable_pattern
local_variables
alternative_explanations
claim_ceiling
```

---

# 9. Política de fontes

Dados municipais e estaduais devem vir de fontes oficiais ou de outputs oficiais já congelados.

Nova aquisição pode ocorrer somente quando:

- a fonte é oficial;
- há documentação e proveniência;
- o arquivo bruto é preservado;
- URL/landing page/data/hash/licença são registrados;
- o método respeita as lentes;
- não há acesso restrito ou identificação indevida.

Microdados públicos não identificados podem ser usados.

Dados pessoais identificáveis, acesso restrito ou microvinculação entre bases são proibidos.

---

# 10. Produto analítico

Cada candidata deve possuir:

```text
insight_id
manager_question
evidence_level
analytical_state
editorial_state
education_outcome
territorial_or_socioeconomic_dimension
same_record
same_person
unit_of_analysis
territorial_lens
period
universe
method
validation
regional_result
ten_municipality_heterogeneity
selected_municipality_result
nova_santa_rita_result
context_adjusted_result
precision_state
literature_mechanism
integrated_conclusion
incremental_value_beyond_separate_charts
planning_implication
monitoring_indicators
institutional_coordination
allowed_claims
forbidden_claims
limitations
recommended_visual
manager_review_state
```

O catálogo final de uma rodada não deve conter mais de oito candidatas principais. Resultados auxiliares permanecem indexados internamente.

---

# 11. Linguagem da futura página

A página deve mostrar:

1. conclusão;
2. duas ou três evidências;
3. o que muda no planejamento;
4. limite curto;
5. fonte e método em detalhe recolhido.

Não mostrar por padrão:

- coeficiente;
- p-valor;
- intervalo técnico;
- nome do modelo;
- ajuste BH;
- efeito fixo;
- C1–C12;
- nível E1–E6;
- hashes;
- schemas;
- códigos internos.

Esses elementos permanecem na camada técnica.

---

# 12. Operação com Codex

O executor deve trabalhar em uma única execução longa por macrojob.

```text
INTERNAL_ITERATIONS = UNBOUNDED_WITHIN_SCOPE
USER_VISIBLE_CHECKPOINTS = ONE
```

Antes de executar, deve criar e manter um `EXECPLAN` interno com:

- objetivo;
- frentes;
- dependências;
- milestones;
- testes;
- decisões;
- bloqueios;
- estado de cada frente.

O ExecPlan não entra automaticamente no pacote compartilhado.

Não interromper por:

- ausência de uma fonte condicional;
- uma candidata negativa;
- necessidade de ajustar método;
- necessidade de reexecutar modelos;
- escolha entre implementações equivalentes;
- falha mecânica do código novo.

Parar apenas por:

- mudança substantiva de indicador;
- necessidade de fonte não autorizada;
- risco de identificação;
- impossibilidade de preservar lentes;
- inferência causal indispensável;
- alteração destrutiva;
- publicação/Gate 11.

---

# 13. Política de arquivos

Artefatos internos:

```text
sem limite fixo, desde que indexados e reproduzíveis
```

Pacote compartilhado:

```text
máximo de 12 arquivos para job analítico
máximo de 15 arquivos para job de interface
```

Todo pacote deve conter:

- checkpoint orientado ao GPT-5.6 Pro;
- catálogo consolidado;
- método e robustez;
- dossiê Nova Santa Rita;
- dossiê regional;
- limites/claims;
- QA;
- índice de todos os artefatos;
- manifesto.

Não criar um arquivo por município, modelo ou hipótese no pacote compartilhado.

---

# 14. Sequência autorizada

```text
Job 5L — aprofundamento socioeconômico e relações diretas
→ julgamento GPT-5.6 Pro
→ Job 5M — integração final insight-first
→ validação da gestora
→ Gate 11
```

Job 5L não altera frontend.

Job 5M não cria nova análise substantiva; apenas consome o que foi aprovado.
