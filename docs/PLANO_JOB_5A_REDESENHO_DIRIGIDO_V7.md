# Plano do Job 5A — Redesenho Dirigido V7

**Estado:** PLANNED_NOT_STARTED
**Classificação futura:** DATA_LOGIC
**Pré-condição:** aprovação documental do Job 4B
**Pré-registro:** [PRE_REGISTRO_JOB_5A_REDESENHO_DIRIGIDO_V7.yaml](PRE_REGISTRO_JOB_5A_REDESENHO_DIRIGIDO_V7.yaml)

## 1. Objetivo

Executar, em job futuro e isolado, três frentes previamente delimitadas:

1. H2_TRAJETORIA_MUNICIPAL_V2;
2. A4_MOBILIDADE_COORDENACAO;
3. contexto juvenil opcional de A3_OCUPACOES_FORMACAO.

O Job 5A deverá produzir fatos e decisões de passagem, sem autoria pública,
interface ou publicação. Este plano não executa nenhuma dessas etapas.

## 2. Entradas e artefatos congelados

Entradas documentais:

- [decisão de rede total](DECISAO_ESCOPO_REDE_TOTAL_JOB_4B_V7.md);
- [julgamento externo final](DECISAO_JULGAMENTO_EXTERNO_FINAL_JOB_4B_V7.md);
- [matriz de decisão final](MATRIZ_DECISAO_FINAL_CANDIDATAS_JOB_4B_V7.csv);
- [aditivo provisório 3+2](ADITIVO_PROVISORIO_PORTFOLIO_3_MAIS_2_V7.md);
- pré-registro 1.0.0 do Job 3, somente leitura;
- pacote e auditorias do Job 4A, somente leitura.

Entradas factuais congeladas:

- Job 2: 20/20 artefatos e manifest operacional SHA-256
  28ca53d020af6eb8168eef15af2a7752034c149ada942b4323756e55ef8f8d85;
- Job 3: 17/17 artefatos e manifest operacional SHA-256
  eb123990bd04a28e8fe4995f8d350e7573cf1a0a74a7cffb3f35d981bb4074ea;
- Job 4A: matrizes H2/H3/A3, sínteses, dossiê, auditorias e correções C9.

Todos devem ser verificados por tamanho e SHA-256 antes da execução. Nenhum
artefato congelado pode ser regravado, normalizado ou corrigido no lugar.

## 3. Ordem futura de execução

1. validar a reconstrução da rede total;
2. executar H2_TRAJETORIA_MUNICIPAL_V2;
3. executar A4_MOBILIDADE_COORDENACAO;
4. testar o contexto juvenil opcional de A3;
5. produzir pacote factual;
6. parar para julgamento externo do GPT-5.6 Pro.

Falha em uma validação bloqueante encerra o job com código não zero e sem
promoção parcial. A ordem não será executada no Job 4B.

## 4. Regras de rede total

O Job 5A deve obedecer:

    network_scope = total_all_dependencies
    administrative_dependency_is_analytic_dimension = false
    administrative_dependency_is_QA_dimension = true

Contagens são somadas somente entre parcelas compatíveis. Taxas usam primeiro o
registro oficial total e, quando necessário, são recomputadas pela soma dos
numeradores dividida pela soma dos denominadores. Média simples, soma de
percentuais, ponderador não declarado e imputação de ausência como zero são
proibidos.

Dependência administrativa pode ser lida apenas para reconstrução, fechamento,
duplicidade, proveniência e QA.

## 5. Cálculos autorizados

### H2_TRAJETORIA_MUNICIPAL_V2

- reconstrução de aprovação, reprovação, abandono e distorção por município,
  ano e etapa;
- direção recente e persistência em pelo menos dois anos, quando possível;
- comparação com Vale do Sinos, RS, Nova Santa Rita e comparadores aprovados;
- diferença de direção ou intensidade municipal;
- uso auxiliar de condições escolares com período, etapa e fato municipal
  compatíveis;
- indicadores de acompanhamento e questão específica de planejamento.

### A4_MOBILIDADE_COORDENACAO

- total de residentes estudantes, total que estudava fora e participação;
- diferença municipal versus Vale e versus RS;
- distribuição e concentração por etapa;
- comparação dos dez municípios e reconstrução obrigatória de Nova Santa Rita;
- delimitação de público, etapa, município, indicador e contexto de coordenação.

### Contexto juvenil opcional de A3

- CAGED 15–17 e 18–24 por CBO, CNAE e aprendiz, mantendo admissões,
  desligamentos e saldo como fluxos;
- RAIS como estoque ocupacional de A3;
- oferta de educação profissional em rede total;
- teste de especificidade por faixa etária, ocupação ou subgrupo, setor,
  município, curso ou eixo e questão de articulação.

## 6. Cálculos e inferências proibidos

- qualquer estratificação de desempenho por dependência administrativa;
- média simples de taxas;
- causalidade ou vínculo entre as mesmas pessoas;
- atribuição de resultado agregado a ente específico;
- ranking como critério de passagem;
- seleção automática por coeficiente ou valor-p;
- mistura de RAIS e CAGED;
- inferência de primeiro emprego, vaga, capacidade, destino, rota ou receptor;
- combinação mecânica de mobilidade com oferta localizada;
- criação de cartão próprio de trabalho juvenil;
- alteração pós-resultado da aprovação de A3;
- execução de cenário, A5 ou qualquer candidata para completar quantidade.

## 7. Outputs esperados

O Job 5A deverá produzir, em staging controlado:

- inventário de entrada com hashes;
- QA de reconstrução da rede total;
- matriz factual e síntese de H2_TRAJETORIA_MUNICIPAL_V2;
- matriz factual e síntese de A4_MOBILIDADE_COORDENACAO;
- registro de uso ou descarte silencioso do contexto juvenil de A3;
- fatos municipais de Nova Santa Rita;
- matriz C1–C12 das frentes executadas;
- pacote factual para revisão externa;
- manifest com paths, tamanhos, hashes, fontes, períodos e contagens;
- registro de falhas e estados de disponibilidade.

Os paths definitivos devem ser resolvidos pelo executor contra a arquitetura
canônica antes da primeira escrita. A geração ocorre em staging; validação
integral precede qualquer promoção autorizada.

## 8. Critérios de passagem

Aplicam-se C1–C12 na interpretação do Job 4B:

- relevância PNE/PME;
- mecanismo prévio;
- universos e lentes compatíveis;
- período coerente;
- estabilidade;
- integração;
- diferença municipal útil;
- município, etapa, público, indicador e questão de planejamento;
- comunicabilidade;
- rastreabilidade;
- não redundância;
- valor além da demografia.

H2 só passa com padrão municipal por etapa, mais de um ano relevante, diferença
útil, público, indicador e questão específica. A4 só passa quando a distribuição
por município e etapa produzir coordenação concreta além de afirmar que há
residentes estudando fora. O contexto juvenil só entra em A3 se cumprir todos os
campos pré-registrados; caso contrário, é descartado sem criar candidata.

## 9. QA e testes

Antes da execução:

- conferir hashes dos Jobs 2, 3 e 4A;
- validar YAML do pré-registro;
- confirmar código IBGE textual;
- confirmar universo de dez municípios e caso 4313375;
- confirmar ausência de escrita em public/data.

Durante e após a execução:

- fechamento da rede total contra parcelas disponíveis;
- duplicidades e chaves por grão;
- fechamento de contagens;
- recomputação de taxas a partir de componentes;
- denominador zero, zero observado e estados de ausência;
- compatibilidade de período, etapa, unidade e lente;
- repetibilidade e arredondamento tardio;
- comparação município, Vale, RS e pares;
- QA específico de Nova Santa Rita;
- checagem de RAIS estoque versus CAGED fluxo;
- checagem de destination_available=false em A4;
- validação de schema, manifest, hashes e contagens;
- testes focados do domínio e git diff --check.

Não haverá build frontend no Job 5A, salvo nova autorização explícita e mudança
de escopo. Nenhum teste será enfraquecido para obter passagem.

## 10. Limites de linguagem

O pacote é factual e interno. Não transportar coeficientes, valor-p ou jargão à
futura camada pública. Não usar causalidade, atribuição individual, recomendação
genérica ou responsabilidade derivada de estratificação administrativa.

Para A3, preservar o envelope do julgamento: movimento líquido observado,
composição, concentração, subgrupos, cursos e eixos mapeados. Continuam
proibidas alegações de alinhamento, aderência, déficit, demanda futura,
adequação, empregabilidade, suficiência, vagas, capacidade, expansão, promessa
de emprego ou trajetória aluno–trabalho.

## 11. Limites de lentes

Permanecem distintos:

- moradores do município;
- matrículas nas escolas do município;
- residentes que estudam fora;
- vínculos nos estabelecimentos do município.

A oferta técnica é localizada por escola; RAIS e CAGED são localizados por
estabelecimento de trabalho; A4 parte da residência. Nenhuma frente pode inferir
que os universos contêm as mesmas pessoas.

## 12. Revisão externa e parada obrigatória

Concluído o pacote factual, o Job 5A deve parar para julgamento externo do
GPT-5.6 Pro. O julgador decidirá passagem, retenção ou revisão das frentes, sem
reescrever silenciosamente o pré-registro.

O Job 5A não autoriza automaticamente:

- autoria pública;
- alteração de contrato canônico;
- React, CSS, rotas ou interface;
- corpus ou dados públicos;
- abertura do PILOT_GATE_11_V7;
- Job 6 ou qualquer etapa posterior.
