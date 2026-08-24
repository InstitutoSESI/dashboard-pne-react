# Briefing — Matriz de Prioridades do PNE 2026–2036: o que ela faz e quais causas se ligam a quais indicadores

Documento de consulta externa. Objetivo: obter orientação metodológica para **tornar o
catálogo de causas menos genérico e mais tecnicamente ancorado em documentos oficiais do
MEC e do governo brasileiro** (Lei nº 15.388/2026 e suas estratégias, PAR, Censo Escolar,
Saeb, PNATE/PNAE, Busca Ativa Escolar, Compromisso Nacional Criança Alfabetizada,
Pé-de-Meia, Escola em Tempo Integral, PDDE, Sistema Nacional de Educação etc.).

- Município piloto: Nova Santa Rita/RS (IBGE 4313375), artefato de 2026-08-14.
- Estado atual: matriz em produção com 7 metas prioritárias e 9 causas.
- Catálogo de causas: 37 fatores (`F_*`), curados na camada de pesquisa.

---

## 1. O que a Matriz de Prioridades faz

É uma camada de apoio à decisão municipal para a oficina de elaboração/revisão do plano
municipal de educação. Ela responde a duas perguntas na frente do gestor:

1. **Isso é grave aqui?** (severidade)
2. **A prefeitura consegue agir?** (governabilidade)

A matriz **não recalcula indicador**. Valor, referência, distância e veredito vêm do
diagnóstico oficial publicado. Ela **não pede dado à prefeitura**: todo sinal vem de fonte
pública. O que só o município sabe entra como **pergunta de oficina**, nunca como prova.

Saída por município: uma lista de **metas prioritárias**, cada uma com poucas **causas**
posicionadas, mais três blocos de honestidade — *outras causas possíveis*, *fora do
alcance municipal* e *metas sem dado*.

### Cadeia lógica

```
indicador oficial (valor x referência)  ->  severidade da meta
        v
causa (fator F_*) vinculada ao indicador pelo catálogo curado
        v
sinal público local adverso (prova)  ->  a causa entra como carta
        v
governabilidade (municipal | compartilhada)  ->  posição
        v
primeiro passo (verificação local ou instrumento federal)
```

### Regras de severidade

Severidade combina duas leituras publicadas prontas:

| leitura | vocabulário fechado |
|---|---|
| Distância à referência | `far_from_target` · `below_target` · `near_or_at_target` |
| Desvio frente aos pares | `much_worse_than_peers` · `worse_than_peers` · `in_line_with_peers` · `better_than_peers` |

- **Grupo de pares**: municípios do mesmo estado, mesma faixa de porte populacional
  (até 5 mil, 5–20 mil, 20–100 mil, 100 mil+), mínimo de 20; no piloto, n = 88 (RS,
  faixa 20k–100k, população 2025).
- **Severidade alta** = longe da referência **e** pior que os pares.
- **Severidade média** = apenas uma das duas condições.
- Perto da referência e em linha com os pares → não vira carta.

### Regras de entrada de uma causa

Uma causa vira carta quando **todas** valem:

1. Está vinculada, no catálogo curado, a pelo menos um indicador com resultado oficial
   publicado e abaixo da referência.
2. Tem pelo menos um **sinal público local adverso** com inferência melhor que
   "existência declarada" (`declared_existence_only` nunca posiciona carta).
3. Passou a curadoria como hipótese (`context` e `excluded` não viram carta).
4. Governabilidade é `municipal` ou `shared` (`external` vai para "fora do alcance").

Teto duro de **10 causas por município**; o excedente cai em "outras causas possíveis".
Deduplicação: uma carta por causa por meta, com as metas afetadas listadas.

### Rastreabilidade

Toda posição carrega `placementRationale` com valores e limiares. Exemplo real:

> Âncora 1.a/creche: valor 35,10 contra referência 60,0 (faltam 24,90; 41,5% da
> referência, acima do limiar de 33,3% → `far_from_target`). No grupo de 88 municípios do
> RS na faixa 20k_100k, o valor fica abaixo do primeiro quartil (Q1 = 37,1) →
> `much_worse_than_peers`. Severidade alta.

---

## 2. Fontes de sinal já usadas

Contagem de sinais no artefato do piloto, por família de medida:

| fonte | sinais | o que traz |
|---|---|---|
| `inep.afd` | 293 | Adequação da formação docente por etapa e grupo |
| `midr.atlas` | 282 | Atlas Digital de Desastres (danos, prejuízos, COBRADE, S2iD) |
| `inep.rendimento` | 166 | Aprovação, reprovação, abandono por etapa |
| `inep.had` | 98 | Média de horas-aula diárias |
| `inep.transicao` | 63 | Promoção, repetência, evasão, migração para EJA |
| `inep.tdi` | 56 | Distorção idade-série |
| `inep.ideb` | 40 | Ideb, fluxo e aprendizado |
| `inep.censo_escolar` | 20 | Sinopse e microdados (rural, transporte, infraestrutura) |
| `mds.censo_suas` | 4 | Equipamentos e serviços socioassistenciais |
| `inep.alfabetizacao` | 4 | Indicador Criança Alfabetizada |
| `sinisa.*` | 4 | Água, esgoto, resíduos, drenagem |
| `ibge.munic` | 1 | Pesquisa de Informações Básicas Municipais |

Cada sinal carrega `maxInference` (`measured_value_within_source_scope`,
`known_cases_or_events_only`, `contextual_association_only`,
`declared_existence_only`), `observability`, `direction`, `period`, `unit` e uma cautela
textual explícita.

---

## 3. Catálogo de causas (37 fatores)

`nome de pesquisa` → `título em linguagem clara exibido ao gestor`.

| id | nome de pesquisa | título exibido |
|---|---|---|
| F_DISTANCE | Distância, tempo, custo e transporte | Distância e transporte até a escola |
| F_POV_CCT | Pobreza, custo de oportunidade e proteção de renda | Pobreza e apoio de renda às famílias |
| F_DEMAND_DISCOVERY | Identificação da demanda e comunicação | Encontrar quem precisa de vaga |
| F_EC_QUALITY | Qualidade da educação infantil | Qualidade da creche e da pré-escola |
| F_ATTEND | Frequência, busca ativa e alerta precoce | Frequência e busca ativa |
| F_MGMT | Gestão e organização escolar | Gestão e organização da escola |
| F_FOUNDATION | Pré-requisitos de alfabetização e numeracia | Bases de leitura e matemática |
| F_TIME_QUALITY | Tempo efetivo de instrução | Tempo de aula efetivo |
| F_HOME_LEARNING | Aprendizagem em casa | Apoio à aprendizagem em casa |
| F_TEACH_COACH | Observação, feedback e coaching docente | Acompanhamento dos professores |
| F_TEACH_MATCH | Adequação da formação à disciplina/etapa | Professores fora da sua área de formação |
| F_STRUCT_PED | Pedagogia estruturada, materiais alinhados e avaliação formativa | Currículo, material e avaliação em sala |
| F_FOOD | Alimentação escolar e insegurança alimentar | Alimentação escolar |
| F_INTERGOV | Cooperação federativa | Parceria com o estado e a União |
| F_DISASTER | Desastres e interrupções climáticas | Desastres e eventos climáticos |
| F_REPETITION | Reprovação e distorção acumuladas | Reprovação e atraso escolar |
| F_HEALTH | Saúde física e mental | Saúde física e mental dos alunos |
| F_WORK | Trabalho infantil/juvenil e jornada de adultos | Trabalho que concorre com o estudo |
| F_PREG_CARE | Gravidez, parentalidade e cuidado de dependentes | Gravidez e cuidado de dependentes |
| F_BULLY | Violência, bullying e clima escolar | Violência, bullying e clima escolar |
| F_HEAT | Calor e conforto térmico | Calor e conforto nas salas |
| F_BASIC_INFRA | Infraestrutura básica, salubridade e acessibilidade | Infraestrutura básica da escola |
| F_FULLTIME_DESIGN | Desenho da jornada integral | Organização do tempo integral |
| F_DIG_PHYS | Infraestrutura e serviço físico de conectividade | Internet e equipamentos na escola |
| F_DIG_PED | Uso pedagógico guiado da tecnologia | Uso da tecnologia em sala |
| F_ENV_CURR | Currículo e prática de educação ambiental | Educação ambiental na prática |
| F_INDIG_RELEV | Relevância territorial, linguística e cultural indígena | Adequação da escola indígena |
| F_INCLUSION_SUPPORT | Apoio educacional individualizado e AEE | Apoio à inclusão e atendimento especializado |
| F_EJA_FIT | Adequação da oferta de EJA | Oferta de EJA para jovens e adultos |
| F_CASH_AID_HE | Auxílio financeiro e permanência no superior/EPT | Ajuda de custo no superior e técnico |
| F_EPT_BUNDLE | Pacote de oferta e qualidade da EPT | Oferta e qualidade da educação profissional |
| F_HE_FACULTY | Corpo docente e condições no superior | Professores e condições no ensino superior |
| F_HE_OFFER | Oferta de ensino superior | Oferta de ensino superior na região |
| F_CAREER_PAY | Atratividade, remuneração e carreira | Carreira e salário dos professores |
| F_POSTGRAD_CAP | Capacidade de pós-graduação e pesquisa | Capacidade de pós-graduação e pesquisa |
| F_GOV_AUDIT | Transparência e fiscalização | Transparência e fiscalização |
| F_PARTICIPATION | Participação e governança democrática | Participação e conselhos |

Fatores de **contexto** (não viram carta; descrevem o território):
`F_SES`, `F_EC_OFFER`, `F_HEALTH`, `F_TEACH_STABILITY`, `F_FINANCING_EXECUTION`,
`F_EPT_DEMAND`.

---

## 4. Mapa completo causa × indicador

Relação vigente no catálogo curado, por meta do PNE 2026–2036. `adverso` = classe com
sinal público adverso; `sem dado` = causa plausível sem sinal público suficiente;
`protetor` = fator presente com sinal favorável.

### Meta 1 — Educação infantil
Indicadores: `creche` (1.a), `pre_escola` (1.c)

| causa | classe | governabilidade | indicadores |
|---|---|---|---|
| F_DISTANCE | adverso | compartilhada | creche, pre_escola |
| F_POV_CCT | adverso | compartilhada | creche, pre_escola |
| F_DEMAND_DISCOVERY | sem dado | municipal | creche, pre_escola |

### Meta 3 — Alfabetização
Indicador: `alfabetizacao` (3.a)

| causa | classe | governabilidade |
|---|---|---|
| F_ATTEND | adverso | municipal |
| F_FOUNDATION | adverso | municipal |
| F_TIME_QUALITY | adverso | municipal |
| F_TEACH_COACH | sem dado | municipal |
| F_STRUCT_PED | sem dado | municipal |
| F_FOOD | protetor | compartilhada |

### Meta 4 — Acesso e fluxo na educação básica
Indicadores: `basico_6_17`, `basico_15_17` (4.a), `idade_regular_quinto` (4.b),
`idade_regular_nono` (4.c), `idade_regular_medio` (4.d)

| causa | classe | governabilidade | indicadores |
|---|---|---|---|
| F_DISASTER | adverso | compartilhada | basico_6_17, basico_15_17 |
| F_DISTANCE | adverso | compartilhada | basico_6_17, basico_15_17 |
| F_ATTEND | adverso | municipal | todos os cinco |
| F_FOUNDATION | adverso | municipal | idade_regular_quinto, _nono, _medio |
| F_REPETITION | adverso | municipal | idade_regular_quinto, _nono, _medio |
| F_WORK | adverso | compartilhada | todos os cinco |
| F_PREG_CARE | sem dado | compartilhada | todos os cinco |

### Meta 5 — Aprendizagem (Saeb)
Indicadores: `saeb_portugues_anos_iniciais`, `saeb_matematica_anos_iniciais` (5.a),
`saeb_*_anos_finais` (5.b), `saeb_*_ensino_medio` (5.d)

| causa | classe | governabilidade | indicadores |
|---|---|---|---|
| F_ATTEND | adverso | municipal | todos os seis |
| F_FOUNDATION | adverso | municipal | todos os seis |
| F_TIME_QUALITY | adverso | municipal | todos os seis |
| F_TEACH_COACH | sem dado | municipal | todos os seis |
| F_STRUCT_PED | sem dado | municipal | todos os seis |
| F_FOOD | protetor | compartilhada | todos os seis |

### Meta 6 — Tempo integral
Indicadores: `basico_integral`, `escolas_integral` (6.a)

| causa | classe | governabilidade |
|---|---|---|
| F_DISTANCE | adverso | compartilhada |
| F_BASIC_INFRA | adverso | compartilhada |
| F_FULLTIME_DESIGN | sem dado | municipal |
| F_FOOD | protetor | compartilhada |

### Meta 7 — Conectividade
Indicadores: `internet`, `banda_larga`, `rede_local`, `rede_wireless`,
`internet_alunos`, `internet_aprendizagem` (7.a)

| causa | classe | governabilidade |
|---|---|---|
| F_DIG_PHYS | adverso | compartilhada |
| F_DIG_PED | sem dado | municipal |

### Meta 8 — Clima, conforto e educação ambiental
Indicadores: `salas_climatizadas` (8.b), `educacao_ambiental` (8.c)

| causa | classe | governabilidade | indicador |
|---|---|---|---|
| F_BASIC_INFRA | adverso | compartilhada | salas_climatizadas |
| F_ENV_CURR | sem dado | municipal | educacao_ambiental |

### Meta 9 — Educação escolar indígena
Indicador: `educacao_indigena_cobertura_estimada_4_17` (9.d)

| causa | classe | governabilidade |
|---|---|---|
| F_DISTANCE | adverso | compartilhada |
| F_INDIG_RELEV | sem dado | compartilhada |

### Meta 10 — Educação especial e AEE
Indicador: `aee_oferta_escolas_elegiveis` (10.b)

| causa | classe | governabilidade |
|---|---|---|
| F_INCLUSION_SUPPORT | adverso | municipal |
| F_DISTANCE | adverso | compartilhada |

### Meta 11 — EJA e escolaridade da população adulta
Indicadores: `alfabetizacao_pop_15_mais` (11.a), `fundamental_concluido_15_29` e
`_15_mais` (11.b), `medio_concluido_18_29` e `_18_mais` (11.c),
`eja_atendimento_18_mais` (11.d)

| causa | classe | governabilidade | indicadores |
|---|---|---|---|
| F_EJA_FIT | adverso | municipal | todos os seis |
| F_DISTANCE | adverso | compartilhada | alfabetizacao_pop_15_mais, eja_atendimento_18_mais |
| F_ATTEND | adverso | municipal | todos os seis |
| F_WORK | adverso | compartilhada | todos os seis |
| F_PREG_CARE | sem dado | compartilhada | todos os seis |

### Meta 12 — Educação profissional e técnica
Indicadores: `medio_tecnico_articulado_percentual`, `medio_tecnico_participacao_publica`
(12.a), `subsequente_expansao` (12.b), `eja_integrada_educacao_profissional_percentual`
(12.c)

| causa | classe | governabilidade | indicadores |
|---|---|---|---|
| F_EJA_FIT | adverso | municipal | eja_integrada_educacao_profissional_percentual |
| F_WORK | adverso | compartilhada | todos |
| F_EPT_BUNDLE | sem dado | compartilhada | todos |

### Meta 14 — Ensino superior
Indicadores: `graduacao_frequencia_18_24` (14.a), `superior_completo_25_34` (14.b),
`superior_concluintes_oferta_local` (14.c), `taxa_bruta_graduacao` (14.d)

| causa | classe | governabilidade |
|---|---|---|
| F_DISTANCE | adverso | compartilhada |
| F_WORK | adverso | compartilhada |
| F_CASH_AID_HE | sem dado | baixa (federal/estadual) |
| F_PREG_CARE | sem dado | compartilhada |

### Metas 15 e 16 — Qualidade do superior e pós-graduação
Sem dado municipal utilizável no piloto; nenhuma causa é oferecida (bloco "metas sem
dado").

### Meta 17 — Profissionais da educação
Indicadores: `adequacao_ai`, `adequacao_af`, `adequacao_em` (17.a),
`munic_planos_carreira_declarados` (17.c), `temporarios` (17.d), `pos_graduacao` (17.f)

| causa | classe | governabilidade | indicadores |
|---|---|---|---|
| F_TEACH_MATCH | adverso | compartilhada | adequacao_ai, _af, _em |
| F_CAREER_PAY | sem dado | compartilhada | todos os seis |

### Meta 18 — Gestão democrática
Indicadores: `conselho_escolar` (18.b), `munic_forum_educacao_declarado` (18.c)

| causa | classe | governabilidade |
|---|---|---|
| F_PARTICIPATION | adverso | municipal |

### Meta 19 — Financiamento e infraestrutura
Indicador: `salas_acessiveis` (19.c)

| causa | classe | governabilidade |
|---|---|---|
| F_BASIC_INFRA | adverso | compartilhada |

---

## 5. O que a matriz produziu no piloto (Nova Santa Rita/RS)

Grupo de pares: RS, faixa 20k–100k, n = 88, população 2025.

| meta | indicador âncora | valor | referência | severidade | causas |
|---|---|---|---|---|---|
| 1.a Creche | creche | 35,1% | 60 | alta (longe · muito pior que pares) | F_DISTANCE |
| 5.a Aprendizagem anos iniciais | saeb_matematica_anos_iniciais | 43,5% | 70 | alta | F_ATTEND, F_FOUNDATION, F_TIME_QUALITY |
| 11.c Conclusão do médio 18+ | medio_concluido_18_29 | 57,2% | 100 | alta | F_EJA_FIT |
| 17.a Formação docente | adequacao_af | 65,8% | 100 | alta | F_TEACH_MATCH |
| 4.a Acesso 6–17 | basico_6_17 | 91,1% | 100 | média | F_DISASTER |
| 4.b Conclusão do 5º ano na idade | idade_regular_quinto | 92,2% | 100 | média | F_REPETITION |
| 19.c Infraestrutura mínima | salas_acessiveis | 47,1% | 100 | média | F_BASIC_INFRA |

Metas cujas causas foram mostradas em outra meta (deduplicação): 3.a, 4.c, 4.d, 5.b, 5.d,
1.c, 6.a, 11.b, 11.d, 12.c, 14.d.

Caíram para "outras causas possíveis": F_POV_CCT (meta 1), F_WORK (meta 4),
F_DIG_PHYS (meta 7), F_INCLUSION_SUPPORT (meta 10), F_PARTICIPATION (meta 18).

Metas sem dado: 15 e 16.

### Como uma causa aparece hoje (texto real, F_DISTANCE na meta 1.a)

- **Mecanismo**: "Tempo, custo, segurança e irregularidade do transporte tornam a
  frequência mais onerosa."
- **Relação esperada**: "Deslocamentos mais difíceis tendem a reduzir acesso e
  permanência."
- **Prova**: `midr.atlas.public_transport_loss` = R$ 3.400.000 (2025), inferência
  `known_cases_or_events_only`, cautela: "Perda financeira não identifica rota escolar,
  aluno transportado ou tempo de viagem."
- **Primeiro passo**: "Levantar as rotas do transporte escolar: quilometragem, tempo de
  viagem e dias sem serviço."
- **Perguntas de oficina**: rota/tempo/km/dias sem serviço; tempo real de deslocamento;
  segurança da viagem escolar.

---

## 6. O problema que queremos resolver

As causas estão **genéricas demais**. Sintomas observados:

1. **Formulação de senso comum.** "Distância e transporte até a escola" ou "Frequência e
   busca ativa" descrevem categorias amplas, não mecanismos verificáveis. O gestor lê e
   responde "isso vale para qualquer município".
2. **Baixa ancoragem normativa.** O texto da causa não conversa com a norma que rege o
   tema. Não cita dispositivo, programa, instrumento de financiamento nem obrigação legal
   correspondente.
3. **Descolamento entre causa e alavanca.** O "primeiro passo" é quase sempre uma
   verificação local genérica; raramente aponta o instrumento federal ou estadual que a
   prefeitura pode acionar (PAR, PNATE, PNAE, PDDE, Escola em Tempo Integral,
   Pé-de-Meia, Busca Ativa Escolar, Compromisso Criança Alfabetizada, novo FUNDEB,
   assistência técnica do MEC).
4. **Granularidade errada.** Uma mesma causa (por exemplo F_BASIC_INFRA) cobre água,
   sanitário, energia, acessibilidade, biblioteca e manutenção — itens com regimes legais,
   fontes de financiamento e responsáveis diferentes.
5. **Governabilidade grosseira.** Só há `municipal` e `shared`. A norma distingue
   competências com muito mais precisão (regime de colaboração, SNE, competências do
   art. 11 da LDB, responsabilidades do FNDE).

---

## 7. O que pedimos de orientação

1. **Reescrita técnica de cada causa** em três camadas fixas: (a) mecanismo causal
   explícito e verificável; (b) ancoragem normativa — dispositivo da Lei nº 15.388/2026,
   LDB, FUNDEB, resolução do FNDE ou portaria do MEC aplicável; (c) alavanca operacional
   — o instrumento concreto que o município aciona.
2. **Critério de decomposição.** Quais causas devem ser quebradas em subcausas e por qual
   critério (responsável legal? fonte de financiamento? etapa de ensino? item de
   infraestrutura?).
3. **Mapa causa × estratégia do PNE.** Para cada fator, quais estratégias nominais do PNE
   2026–2036 o sustentam. Hoje existe apenas um resumo editorial por meta.
4. **Revisão do vínculo causa × indicador** da seção 4: vínculos faltantes, vínculos
   frouxos que deveriam sair, e indicadores oficiais que deveriam ser âncora e não são.
5. **Critério de governabilidade fundamentado na norma**, substituindo o par
   `municipal`/`shared` por uma classificação defensável no regime de colaboração.
6. **Sinais oficiais subutilizados.** Quais bases públicas do MEC/INEP/FNDE/IBGE
   permitiriam prova mais forte do que os proxies atuais — especialmente para transporte
   escolar, busca ativa, tempo de instrução e infraestrutura.

Restrições invioláveis a respeitar em qualquer sugestão:

- Não recalcular indicador oficial.
- Não solicitar dado às prefeituras.
- Vocabulário fechado em todo campo classificatório.
- Comparação com pares nunca vira ranking nominal entre municípios.
- Máximo de 10 causas por município — a matriz é para uma reunião de duas horas.

---

## 8. Anexo — critérios da curadoria e causas já descartadas

O catálogo tem 137 vínculos meta×causa avaliados: **50 hipóteses**, **33 contextos** e
**54 excluídos**. Os testes aplicados:

| teste | o que exige |
|---|---|
| C1 — especificidade | A formulação nomeia condição concreta e observável, não um tema amplo. |
| C2 — verificabilidade | Existe base pública municipal ou territorial capaz de sustentar o vínculo. |
| C3 — mecanismo direto | A cadeia causa → indicador é curta e compreensível para o gestor. |
| C4 — acionabilidade | Existe resposta municipal possível ou articulação concreta. |
| S | Sobreposição/redundância com outra causa ou com o próprio indicador. |
| CTX | Rebaixado a contexto: descreve o território, não é alavanca. |

Exclusões que merecem revisão externa (podem ser perdas indevidas de conteúdo técnico):

| causa | metas em que foi excluída | motivo registrado |
|---|---|---|
| F_MGMT | 3, 4(C1), 5, 6, 7, 8, 15, 18 | "Gestão e organização" é tema amplo demais (reprova C1) |
| F_INTERGOV | 4, 5, 9, 10, 11, 12, 14, 16, 17 | Descreve a esfera responsável, não um mecanismo (C1/C4) |
| F_GOV_AUDIT | 17, 18, 19 | "Transparência e fiscalização" genérico (C1) |
| F_HOME_LEARNING | 3, 5 | Sem base municipal e risco de responsabilizar a família (C2/C4) |
| F_BULLY | 4, 5, 11 | Mecanismo claro, mas sem base municipal utilizável (C2/C3) |
| F_HEAT | 5, 8 | Redundante com o próprio indicador de conforto térmico (C3/S) |
| F_EC_QUALITY | 1, 3 | Indicador da meta 1 é cobertura, não qualidade (C3); meta 3 sobrepõe (S) |
| F_BASIC_INFRA | 7, 10 | Sobreposição com causa mais específica (S) |
| F_FOUNDATION | 11, 14, 17 | Cadeia causal longa demais nessas metas (C3) |
| F_CASH_AID_HE | 12, 16, 17 | Sobreposição e cadeia longa (S/C3) |
| F_HE_FACULTY | 14, 16, 17 | Fora do alcance municipal ou sobreposto (C3/C4/S) |
| F_FINANCING_EXECUTION | 15, 17 | Rebaixado ou excluído por acionabilidade (C4/S) |

Fatores mantidos apenas como **contexto** (aparecem no texto, nunca como carta):
`F_SES`, `F_EC_OFFER`, `F_POV_CCT` (metas 4, 11, 14), `F_HEALTH`, `F_TEACH_STABILITY`,
`F_TEACH_MATCH` (metas 5, 10), `F_FINANCING_EXECUTION`, `F_EPT_DEMAND`, `F_HE_OFFER`,
`F_POSTGRAD_CAP`, `F_DISASTER` (meta 8), `F_DISTANCE` (meta 12).

Pergunta específica ao revisor: várias exclusões por C1 ("tema amplo demais") sugerem que
o problema não é o tema, e sim a **formulação genérica**. Gestão escolar, cooperação
federativa e controle social têm regime normativo próprio no PNE, na LDB e no PAR.
Uma reescrita tecnicamente ancorada permitiria readmitir esses fatores como causas
específicas? Se sim, com qual formulação e qual prova pública?
