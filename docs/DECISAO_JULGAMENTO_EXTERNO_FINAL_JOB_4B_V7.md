# Decisão do julgamento externo final — Job 4B V7

**Data:** 28 de agosto de 2026
**Classificação:** DOCUMENTATION_ONLY
**Escopo:** julgamento documental posterior ao Job 4A
**Regra de rede:** total_all_dependencies
**Efeito imediato:** nenhum cálculo, narrativa pública, interface ou publicação

## 1. Metodologia do julgamento

O julgamento confrontou:

- o contrato analítico V7;
- o pré-registro 1.0.0 congelado do Job 3;
- os 20 artefatos do Job 2 e os 17 artefatos do Job 3;
- o relatório e o pacote de revisão do Job 3;
- as matrizes e sínteses H2/H3 do Job 4A;
- o dossiê e a matriz A3 do Job 4A;
- as auditorias de pré-registro e fechamento de portfólio;
- as correções C9 pós-Job 3;
- a [decisão canônica de rede total](DECISAO_ESCOPO_REDE_TOTAL_JOB_4B_V7.md).

O método separa evidência executada, conformidade histórica, correção posterior
de escopo, valor decisório, comunicabilidade e autorização de produto. Nenhuma
decisão decorre apenas de valor-p, coeficiente, ranking, quantidade de cartões ou
necessidade de completar o portfólio.

## 2. Níveis de autorização

| Nível | Significado |
|---|---|
| Elegibilidade analítica | Há fatos rastreáveis suficientes para julgamento; não equivale a texto público. |
| Revisão necessária | A candidata ou seu redesenho ainda precisa resolver questões metodológicas e decisórias. |
| Protótipo editorial | É permitido preparar um protótipo interno, dentro do envelope aprovado, para nova revisão. |
| Narrativa pública | Texto destinado ao usuário final; não autorizado neste job. |
| Interface | Implementação em React, CSS, rotas ou componentes; não autorizada neste job. |
| Publicação | Promoção para corpus ou dados públicos; não autorizada neste job. |

Toda linha da [matriz final](MATRIZ_DECISAO_FINAL_CANDIDATAS_JOB_4B_V7.csv)
mantém public_narrative_allowed_now=false, interface_allowed_now=false e
publication_allowed_now=false.

## 3. Interpretação futura de C1–C12

Os critérios passam a ser lidos assim:

- C1 — relevância para PNE/PME;
- C2 — mecanismo definido antes do resultado;
- C3 — universos e lentes compatíveis;
- C4 — período coerente;
- C5 — estabilidade suficiente;
- C6 — integração de fatos;
- C7 — diferença municipal útil;
- C8 — município, etapa, público, indicador e questão de planejamento;
- C9 — comunicabilidade editorial;
- C10 — rastreabilidade;
- C11 — não redundância;
- C12 — valor incremental além da demografia.

A dependência administrativa não integra C8. A responsabilidade institucional
continua obrigatória apenas como ação, coordenação, articulação ou
acompanhamento contextual.

Legenda da matriz de julgamento: A = atende; AF = atende com correção obrigatória;
R = exige revisão; N = não atende para passagem; NA = não aplicável após retenção.

| Candidata | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 | C9 | C10 | C11 | C12 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| H1_DEMOGRAFIA_REDE | A | A | A | AF | A | A | A | A | AF | A | A | A |
| H2_TRAJETORIA_PERMANENCIA | A | R | A | R | R | R | R | R | R | A | A | R |
| H3_TRABALHO_JUVENIL_MEDIO | A | A | A | R | R | R | R | N | R | A | A | N |
| H4_EJA_DISTRIBUICAO | A | A | A | A | A | A | A | A | AF | A | A | A |
| A1_COORTES_REDE | A | A | A | A | A | A | A | A | A | A | N | N |
| A2_TRABALHO_PERMANENCIA | A | A | A | R | R | R | R | N | R | A | N | N |
| A3_OCUPACOES_FORMACAO | A | A | A | AF | R | A | A | A | AF | A | A | A |

## 4. Decisão por candidata

### H1_DEMOGRAFIA_REDE

**Estado:** APPROVED_FOR_EDITORIAL_AUTHORING.

Rede significa oferta escolar total localizada no município. A futura autoria
deve usar matrículas, escolas e turmas totais por etapa, sem estratificação por
dependência, e preservar população residente versus matrícula localizada.

C9 obrigatório:

- declarar a janela de cada número;
- manter separados materiais 2014–2025 e 2015–2025;
- não combinar janelas distintas na mesma frase, tabela ou cálculo;
- não recomendar abertura ou fechamento automático de escolas.

### H2_TRAJETORIA_PERMANENCIA

**Estado:** REVIEW_REQUIRED_AFTER_PRODUCT_SCOPE_CORRECTION.

H2 não fica definitivamente retida. Os 162 modelos executados usam rede total e,
por isso, estão alinhados à decisão atual. A ausência da antiga estratificação
administrativa não é falha nem critério de passagem.

Permanecem questões reais:

1. janelas pré-registradas não executadas;
2. ponderação H2 não executada;
3. pequeno denominador não tratado;
4. conjunto preferido de fatores não executado;
5. lacunas de documentação em sensibilidades;
6. ausência da série municipal da condição mais estável para Nova Santa Rita;
7. decision_delta ainda genérico;
8. proibição de linguagem causal.

A relação alunos por turma × abandono no ensino médio segue relevante para
revisão, mas não autoriza narrativa pública. O único redesenho autorizado é
H2_TRAJETORIA_MUNICIPAL_V2, exclusivamente em rede total.

### H3_TRABALHO_JUVENIL_MEDIO

**Estado:** RETAINED_INSUFFICIENT_DECISION_DELTA.

A retenção decorre da natureza ecológica, da inversão de sinal no lag 2, da
magnitude regional não equivalente à estadual, da ausência de concentração
conjunta delimitada, da conclusão restrita a monitoramento territorial e da
falta de decisão concreta sobre aprendizagem, horários, transição, permanência
ou formação. Localização do trabalho e localização da escola permanecem lentes
distintas.

A ausência de estratificação administrativa educacional não é fundamento da
retenção. Os resultados educacionais agregados estão no escopo correto. A2 não
é reativada. Fatos juvenis só poderão ser testados como contexto factual de A3,
sem transportar coeficientes ou interpretação causal.

### H4_EJA_DISTRIBUICAO

**Estado:** APPROVED_FOR_EDITORIAL_AUTHORING_WITH_C9_FIX.

Usar matrículas totais de EJA no município, com fundamental e médio separados.
Em Nova Santa Rita:

- fundamental: enrollment_share_above_public_share;
- médio: enrollment_share_below_public_share.

É proibido produzir uma direção municipal única, usar near ou próximo e
interpretar as medidas como cobertura, atendimento, demanda, alcance,
suficiência ou capacidade. População residente e matrícula localizada
permanecem lentes distintas.

### A1_COORTES_REDE

**Estado:** RETAINED_REDUNDANT_WITH_H1.

A retenção é preservada. A redundância de pergunta, público, indicadores e
decisão independe da nova regra de rede total. A1 não será restaurada para
preencher quantidade.

### A2_TRABALHO_PERMANENCIA

**Estado:** RETAINED_REDUNDANT_WITH_H3.

A retenção é preservada mesmo com H3 retida. A orientação inicial é diferente,
mas o decision_delta produzido permaneceu materialmente equivalente. A2 não
será restaurada para preencher quantidade.

### A3_OCUPACOES_FORMACAO

**Estado:** APPROVED_FOR_EDITORIAL_PROTOTYPE_WITH_LIMITS.

O protótipo futuro deve usar a oferta técnica total observada e tratar
instituições ofertantes somente como atores de governança. O envelope permitido
é descrever movimento líquido observado entre 2019 e 2025, subgrupos, cursos e
eixos efetivamente mapeados, composição, concentração e questões de articulação.

Limites obrigatórios:

- não usar transformação sustentada sem teste próprio;
- não ligar automaticamente uma ocupação nominal a curso quando a ponte opera
  por subgrupo;
- observed_zero não pode ser título ou conclusão;
- bridge_gap não pode ser o insight principal;
- registrar cinco cursos e 1.281 matrículas não mapeadas;
- preservar a não aditividade da ponte;
- separar oferta por escola de vínculo por estabelecimento de trabalho.

São proibidas alegações de alinhamento, aderência, déficit, demanda futura,
adequação, empregabilidade, suficiência, vagas, capacidade, necessidade de
expansão, promessa de emprego ou trajetória aluno–trabalho.

## 5. Fatos que não podem fundamentar decisões

Não podem ser usados:

- ausência de estratificação administrativa como falha de H2 ou H3;
- atribuição do resultado agregado a município, Estado ou instituição
  ofertante;
- reclassificação retroativa de NOT_EXECUTED;
- coeficiente ou valor-p como autorização editorial;
- combinação de janelas H1 distintas;
- direção EJA única para etapas opostas;
- zero observado ou lacuna de ponte como conclusão A3;
- vínculo causal ou individual entre trabalho, escola, curso e emprego;
- destino, rota, receptor, escola, vaga ou capacidade inferidos da mobilidade.

## 6. Correção do estado de H2 e pré-registro histórico

A correção de H2 é prospectiva. O pré-registro 1.0.0 permanece congelado e a
auditoria do Job 4A permanece correta. Somente a consequência de produto muda:
a antiga ausência de estratificação administrativa deixa de bloquear H2. As
demais divergências continuam em vigor e justificam REVIEW_REQUIRED.

Nenhuma candidata é aprovada ou retida retroativamente por esta correção.

## 7. Estado real do portfólio

Primeira direção:

- aprovadas: H1_DEMOGRAFIA_REDE e H4_EJA_DISTRIBUICAO;
- em revisão: H2_TRAJETORIA_PERMANENCIA;
- retida: H3_TRABALHO_JUVENIL_MEDIO.

Segunda direção:

- aprovada para protótipo editorial futuro: A3_OCUPACOES_FORMACAO;
- retidas: A1_COORTES_REDE e A2_TRABALHO_PERMANENCIA.

Contagem atual:

- primeira direção aprovada: 2;
- segunda direção aprovada: 1;
- portfólio atual: 2+1;
- H2 não conta enquanto permanecer REVIEW_REQUIRED;
- PILOT_GATE_11_V7 permanece BLOQUEADO.

O [aditivo provisório](ADITIVO_PROVISORIO_PORTFOLIO_3_MAIS_2_V7.md) registra o
alvo 3+2 sem alterar o contrato canônico.

## 8. Próximo passo permitido

Após aprovação documental deste Job 4B, o único próximo job permitido é o
[Job 5A — Redesenho Dirigido V7](PLANO_JOB_5A_REDESENHO_DIRIGIDO_V7.md), nas
três frentes congeladas pelo
[pré-registro](PRE_REGISTRO_JOB_5A_REDESENHO_DIRIGIDO_V7.yaml):

1. H2_TRAJETORIA_MUNICIPAL_V2;
2. A4_MOBILIDADE_COORDENACAO;
3. contexto juvenil opcional de A3.

O Job 5A não começa automaticamente. Este julgamento não abre o Gate 11 e não
autoriza autoria pública, interface ou publicação.
