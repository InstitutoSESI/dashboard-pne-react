# Relatório Job 3 — Laboratório analítico V7 Vocações × PNE

## Veredito executivo

**Aprovado para julgamento externo.** O laboratório avaliou as sete candidatas, preservou o pré-registro 1.0.0, produziu três candidatas ANALYTICALLY_ELIGIBLE, duas REVIEW_REQUIRED e reteve duas por redundância. Isso não aprova narrativa, interface ou publicação.

| Candidata | Estado | Decisão alterada ou limite |
|---|---|---|
| H1_DEMOGRAFIA_REDE | ANALYTICALLY_ELIGIBLE | Monitor stage- and network-specific observed response and municipalities moving differently from the region, not cohort size alone. |
| H2_TRAJETORIA_PERMANENCIA | REVIEW_REQUIRED | Potentially changes which stage, network and condition should be investigated together; external technical judgment is still required because stability varies. |
| H3_TRABALHO_JUVENIL_MEDIO | REVIEW_REQUIRED | Potentially adds joint work-education monitoring by age group and municipality; ecological stability still needs external judgment. |
| H4_EJA_DISTRIBUICAO | ANALYTICALLY_ELIGIBLE | Adds stage-specific regional coordination and network responsibility monitoring without calling the metric coverage or service. |
| A1_COORTES_REDE | RETAINED | At current evidence it reaches the same stage-network-territory monitoring decision as H1. |
| A2_TRABALHO_PERMANENCIA | RETAINED | At current evidence it reaches the same joint monitoring and coordination decision as H3. |
| A3_OCUPACOES_FORMACAO | ANALYTICALLY_ELIGIBLE | Adds a concrete coordination agenda for the State, municipalities, offering institutions and Sistema S around composition and bridge gaps. |

## Gate factual do Job 2

Os subjobs 2A–2E estavam READY. Foram verificados 20 artefatos com 840,105 linhas e manifesto SHA-256 28ca53d020af6eb8168eef15af2a7752034c149ada942b4323756e55ef8f8d85. Nenhuma lacuna localizada foi convertida em zero ou proxy.

## Método e pré-registro

- Gate: docs/GATE_ENTRADA_JOB_3_V7.yaml.
- Pré-registro congelado antes dos resultados: docs/PRE_REGISTRO_ANALITICO_JOB_3_V7.yaml, versão 1.0.0, sem POST_RESULT_ADJUSTMENT.
- Biblioteca local: docs/BIBLIOTECA_MECANISMOS_JOB_3_V7.md.
- Identidade: código IBGE textual de sete dígitos; Vale do Sinos FIERGS com dez municípios; Nova Santa Rita 4313375.
- Escalas: dez municípios para reconstrução regional, Nova Santa Rita como caso obrigatório e 497 municípios do RS quando a cobertura confirmou o mesmo campo.
- Inferência: exclusivamente ecológica e não causal.

## H1 — Demografia e rede

A decomposição simétrica fecha exatamente M = P × R: a mudança de matrícula é a soma da parcela associada à população compatível e da parcela associada à relação matrícula/população. A relação não é taxa individual de atendimento porque população e matrícula usam lentes diferentes.

| Etapa | População Vale Δ% | Matrícula Vale Δ% | Parcela população | Parcela relação | População NSR Δ% | Matrícula NSR Δ% |
|---|---:|---:|---:|---:|---:|---:|
| creche | -17,71 | 40,69 | -3.345,3 | 9.019,3 | -1,49 | 85,27 |
| preschool | -6,08 | 20,09 | -1.195,2 | 4.660,2 | 11,73 | 79,30 |
| early_fundamental | -4,70 | -8,78 | -3.025,3 | -2.746,7 | 15,33 | 6,84 |
| final_fundamental | -16,37 | -14,24 | -8.575,5 | 1.206,5 | 3,43 | -3,66 |
| fundamental | -10,20 | -11,19 | -11.922,1 | -1.218,9 | 9,81 | 2,17 |
| high_school | -23,51 | -15,34 | -7.872,2 | 2.994,2 | -1,26 | 5,13 |

O resultado foi ANALYTICALLY_ELIGIBLE: rede, turmas, escolas e distribuição municipal mudam a pergunta de planejamento além de “há mais ou menos crianças”. Não há projeção nem recomendação de abrir ou fechar escola.

## H2 — Trajetória e permanência

Foram reconstruídas aprovação, reprovação, abandono e distorção por etapa, com as quatro famílias pré-registradas de condições. Os modelos usam efeitos fixos de município e ano, erros agrupados por município, até três especificações principais por resultado, correção Benjamini–Hochberg e sensibilidades de janela, pandemia, defasagem, INSE, etapa, sem efeitos fixos e retirada dos municípios do Vale.

O estado é REVIEW_REQUIRED: as associações não são critério isolado, as coberturas temporais diferem e a estabilidade de sinal/magnitude exige julgamento técnico. Água, biblioteca e quadra permaneceram indisponíveis onde o Job 2 as registrou como null.

## H3 — Trabalho juvenil e ensino médio

RAIS foi tratada como estoque anual e CAGED como fluxo mensal/anual; 2026 não entrou. O painel ecológico compara os resultados do ensino médio ao estoque formal jovem com defasagens 0, 1 e 2, controle demográfico pré-registrado, ponderação populacional alternativa, exclusão de 2020–2021, municípios pequenos, maiores municípios do RS e cada município do Vale.

O estado é REVIEW_REQUIRED: trabalho formal acrescenta uma dimensão de coordenação que a demografia não contém, mas não identifica as mesmas pessoas, primeiro emprego, informalidade, desemprego ou causalidade.

## H4 — Distribuição de EJA

Fotografia de 2022, com fundamental e médio separados. A diferença fica armazenada em fração 0–1; a tabela abaixo converte somente para apresentação em pontos percentuais.

| Etapa NSR | Público potencial | Matrículas | Participação público % | Participação matrículas % | Diferença pp |
|---|---:|---:|---:|---:|---:|
| fundamental | 6.068 | 298 | 2,74 | 5,39 | 2,65 |
| high_school | 4.447 | 82 | 3,49 | 0,89 | -2,61 |

As participações municipais fecham em um e as diferenças em aproximadamente zero para ambas as etapas. A comparação estadual usa o mesmo universo de 2022: 497 municípios com componentes completos. O resultado é ANALYTICALLY_ELIGIBLE, sem usar os termos cobertura, demanda, alcance, atendimento ou suficiência.

## A1 — Coortes e rede

O ponto de partida territorial foi calculado, inclusive municípios em direção distinta da região. A candidata foi RETAINED: no estado atual, público, responsabilidade, indicadores e decisão convergem com H1. Nenhum número futuro de matrícula, cenário municipal ou extrapolação foi produzido.

## A2 — Trabalho e permanência

O ponto de partida no trabalho formal foi reconstruído com estoques, fluxos e composição. A candidata foi RETAINED: apesar da orientação diferente, ela chega à mesma agenda de monitoramento conjunto de H3 e não apresenta decision_delta materialmente distinto.

## A3 — Ocupações e formação

A oferta observada cobre 2023–2025; o painel ocupacional, 2019–2025. Em 2025, a ponte preserva cobertura parcial e não aditiva. Há 3 municípios com zero observado de oferta técnica no recorte, incluindo Nova Santa Rita; isso não significa inexistência fora da fonte.

O resultado é ANALYTICALLY_ELIGIBLE para uma agenda de coordenação e monitoramento de composição. A ponte não mede adequação, empregabilidade, suficiência ou necessidade futura; matrículas não são ingressos, concluintes, vagas ou capacidade.

## Modelos internos

| Candidata | Modelos | Linhas de termos | Municípios min–máx | Observações min–máx |
|---|---:|---:|---:|---:|
| H2_TRAJETORIA_PERMANENCIA | 162 | 180 | 495–497 | 1482–3479 |
| H3_TRABALHO_JUVENIL_MEDIO | 66 | 75 | 10–496 | 70–3472 |

Falhas de especificação registradas: 0. Cada falha permanece no manifesto e não foi substituída por outra variável. Coeficientes e valores-p são exclusivamente internos.

## Nova Santa Rita e comparadores

O pacote factual foi gerado pelo mesmo código da camada dos dez municípios. Os comparadores internos, escolhidos sem resultados educacionais, foram: Estância Velha (4307609), Portão (4314803), Campo Bom (4303905). O cálculo usa porte 0–14, crescimento 0–14, composição municipal do médio, INSE e participação de trabalho formal 15–17; o score não é publicado.

## Não redundância

- H1_DEMOGRAFIA_REDE × A1_COORTES_REDE: RETAIN_A1_KEEP_H1 — At current evidence both reach the same operational monitoring decision; H1 preserves the exact decomposition and network increment.
- H3_TRABALHO_JUVENIL_MEDIO × A2_TRABALHO_PERMANENCIA: RETAIN_A2_KEEP_H3 — The orientation differs, but current public, responsibility, indicators and decision do not differ materially.
- H5_FORMACAO_OCUPACOES × A3_OCUPACOES_FORMACAO: NO_H5_CREATED — No additional candidate was authorized; A3 remains the only occupations-training candidate.
- H2_TRAJETORIA_PERMANENCIA × unplanned_conditions_candidate: NO_NEW_CANDIDATE_CREATED — All pre-registered school conditions remain inside H2.

## QA, rastreabilidade e segurança

- Fechamento máximo absoluto da decomposição: 0,000000000053.
- V6 permaneceu byte a byte idêntica no inventário versionado.
- Consultas PostgreSQL: somente leitura; escritas: zero.
- Internet, API, FTP, BigQuery, download e instalação externa: não usados.
- Tabela CEI.public.estoque_emprego_faixa_etaria: não usada.
- public/data, frontend, compilador público, fila/registro de publicação e PILOT_GATE_11_V7: inalterados pelo Job 3.
- Build completo: não executado.

## Limites para julgamento externo

O julgamento deve decidir se H2 e H3 possuem estabilidade substantiva suficiente, se o limiar descritivo de proximidade da H4 é comunicável sem confundir lentes e se a utilidade de coordenação da A3 é suficiente diante da cobertura parcial da ponte. C9 permanece PENDING_EDITORIAL para todas as candidatas.
