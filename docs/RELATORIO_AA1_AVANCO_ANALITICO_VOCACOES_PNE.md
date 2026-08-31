# Relatório AA1 — painel alinhado do RS com recortes aprofundados do Vale

**Objetivo:** materializar uma base longa comum para cruzamentos entre educação,
demografia, trabalho, estrutura econômica, EPT, escolaridade adulta, EJA,
vulnerabilidade, ruralidade, inclusão e finanças, preservando o alcance e a lente de
cada fonte.
**Classificação:** `DATA_LOGIC`.
**Estado:** `AA1_COMPLETE_OPUS_RECONCILED`.

## 1. Resultado

O AA1 produziu 177.265 observações, 96 métricas e seis famílias. O rótulo funcional
correto é `RS_ALIGNED_WITH_VALE_DEEP_DIVES`: há núcleos estaduais, mas F3, F4 e
partes de F5/F6 são recortes dos dez municípios do Vale do Sinos. O nome canônico do
arquivo é mantido por estabilidade do plano, sem autorizar a leitura de que todas as
métricas são estaduais.

| Família | Linhas | Métricas | Cobertura declarada | `network_scope` por linha |
| --- | ---: | ---: | --- | --- |
| F1 trajetória e condições | 61.095 | 7 | `RS_497` | `total_all_dependencies`: 61.095 |
| F2 demografia, matrícula e oferta | 63.616 | 10 | `RS_497` | não educacional: 19.880; educação total: 43.736 |
| F3 trabalho juvenil e aprendizagem | 11.316 | 23 | `VALE_10` | não aplicável: 11.316 |
| F4 ocupações, setores e EPT | 22.875 | 9 | `VALE_10` | trabalho: 22.141; educação total: 734 |
| F5 escolaridade adulta e EJA | 2.845 | 6 | adulto `RS_497`; EJA `VALE_10` | adulto: 2.485; educação total: 360 |
| F6 vulnerabilidade, ruralidade, inclusão e finanças | 15.518 | 41 | finanças `RS_497`; demais `VALE_10` | social: 110; finanças: 11.928; educação total: 3.480 |

As 96 métricas têm o conjunto municipal exato do `coverage_scope` declarado. O
painel preserva 21.656 zeros observados e 1.379 indisponibilidades, sem chaves
duplicadas. Nova Santa Rita é conferida pelo código textual `4313375`, com 123 linhas
em F1, 128 em F2, 1.130 em F3, 1.569 em F4, 41 em F5 e 383 em F6.

## 2. Contrato de cobertura e de referência

Cada linha contém três proteções novas:

- `coverage_scope`: `RS_497` ou `VALE_10`;
- `coverage_reason`: `STATEWIDE_SOURCE_AVAILABLE` ou
  `FROZEN_ANALYTICAL_SOURCE_RESTRICTED_TO_VALE_10`;
- `reference_scope`: `NO_EXTERNAL_REFERENCE` ou
  `RS_SAME_VERSION_COMPONENT_BENCHMARK`;
- `aggregation_guard`: `WITHIN_DECLARED_COVERAGE_ONLY` ou
  `DO_NOT_AGGREGATE_AS_RS_TOTAL`.

As 3.305 linhas dos cinco componentes `labor.shift_share.*` são valores municipais
do Vale calculados com benchmark RS da mesma versão. Elas carregam a segunda opção
de referência e a proibição de agregá-las como total estadual. Nenhum campo de total
RS (`state_sector`, `reference_total` ou equivalente) é emitido no painel. O
shift-share permanece decomposição contábil, não associação ou causalidade.

O painel é esparso no grão observado pela fonte: `SOURCE_OBSERVATION_SPARSE`. Uma
linha ausente após um `join` futuro significa `row_absent_outside_source_or_grain` e
não pode ser convertida em `observed_zero`, `unavailable`, `suppressed` ou
`not_applicable`. Essa regra é requisito de entrada do AA2.

O sidecar `COBERTURA_FAMILIAS_AA1.json` registra a cobertura e a razão nas 96
métricas, incorpora o rótulo `RS_ALIGNED_WITH_VALE_DEEP_DIVES`, vincula
explicitamente essas declarações ao arquivo
`PAINEL_ANALITICO_ESTADUAL_AA1.csv.gz` e fixa os dez códigos do Vale a partir de
`config/regions/rs.json`, cujo SHA-256 também é registrado.

O sidecar `RECONCILIACAO_GRAO_AA1.json` não inventa uma grade cartesiana para fontes
naturalmente esparsas. Ele recompõe o output por uma contabilidade independente de
16 fluxos: linhas municipais da fonte × regra de expansão codificada. O esperado e
o emitido fecham em 177.265, delta zero, para os 16 fluxos e para cada uma das 96
métricas. Também publica a distribuição de linhas por município em F3 e F4; assim,
uma ausência legítima pode ser distinguida de perda silenciosa no pipeline.

O sidecar `AUDITORIA_TEMPORAL_AA1.json` classifica as 96 métricas: 66 séries anuais
contínuas, dez snapshots de período único, duas séries INSE de calendário oficial
não anual, duas comparações apenas entre endpoints, cinco decomposições de intervalo
e onze snapshots de mês de referência. Não há padrão temporal não declarado.
Vinte e três métricas têm duas assinaturas de definição porque F3 preserva universos
paralelos por grupo etário; nenhuma delas muda de definição ao longo do tempo dentro
do mesmo universo e, portanto, não há quebra temporal não resolvida.

## 3. Fontes e retenção

- snapshot local congelado do Job 5L para trajetória, população, matrícula,
  condições escolares e escolaridade adulta;
- painel RAIS 2019–2025 reconciliado do Job 5L-final;
- painéis congelados Job 5GCR para EPT, ocupações, setores e shift-share;
- painéis congelados Job 5GBR para EJA, ruralidade, AEE e vulnerabilidade;
- 497 contratos municipais de `data_pipeline/export/municipal_finance`;
- registros canônicos de municípios e regiões do RS;
- manifesto protegido do AA0.

O inventário contém 518 arquivos com tamanho e SHA-256 e falha de forma fechada se
qualquer entrada desaparecer ou mudar. As entradas e o pacote analítico permanecem
locais em áreas ignoradas do repositório; o AA1 não os promove a fonte pública ou
versionada sem autorização. A reprodutibilidade do AA2 depende da preservação desses
ativos locais congelados, já protegidos operacionalmente contra limpeza comum.

## 4. Fórmulas e semântica

- Fórmulas oficiais alteradas: nenhuma.
- Valores recalculados: nenhum; o AA1 normaliza resultados já materializados.
- Educação usa exclusivamente `total_all_dependencies`; nenhuma dependência
  administrativa é estrato analítico do painel.
- RAIS significa estoque de vínculos formais ativos em 31/12 no local do
  estabelecimento. F3 usa apenas `active_bonds`, percentuais de vínculos, meses,
  horas semanais e remuneração nominal; não contém fluxo Caged nem contagem de
  pessoas residentes.
- Escolaridade adulta usa população residente; EJA e EPT usam localização da
  escola; trabalho usa local do estabelecimento; finanças usa executor municipal.
- Zero observado, nulo, indisponível, suprimido e não aplicável continuam distintos.
- Não há ranking nem afirmação causal no schema.

## 5. Grão, controles e artefatos

A chave única é: `family_id`, `municipality_ibge_code`, período, grupo/etapa,
`metric_id`, `dimension_id`, universo, lente territorial, escopo de rede,
`coverage_scope` e `reference_scope`.

Os 41 controles cobrem: colunas e não vazio; identidade IBGE e nomes canônicos;
unicidade; vocabulário de disponibilidade; coerência valor/zero/nulo; lentes, rede,
unidades e fontes; cobertura por família; presença de `4313375`; 497 arquivos
financeiros; integridade de `public/data`; ausência de banco/rede; rede total para
educação; enums de cobertura/razão/referência/agregação; cobertura exata das 96
métricas; fence do benchmark RS; semântica dos estoques RAIS F3/F4; ausência de
Caged; denominador zero; reconciliação fonte→output; padrões temporais; fechamento
contábil shift-share; metadata não nulo; unidade única por família/métrica; razões
de indisponibilidade; e gate fail-closed do AA2.

O censo completo de disponibilidade está materializado e protegido pelo hash do
`QA_SUMMARY_AA1.json`. Ele fecha as 177.265 linhas: 154.230 `observed`, 21.656
`observed_zero`, 1.379 `unavailable`, zero `suppressed` e zero `not_applicable`. As
1.379 indisponibilidades são decompostas por vocabulário fechado em 653
`SOURCE_VALUE_MISSING`, 570 `SOURCE_DECLARED_UNAVAILABLE` e 156
`REFERENCE_COMPONENT_UNAVAILABLE_ZERO_BASE`; há zero nas demais razões. Não existe
denominador zero no snapshot, e um teste sintético prova que esse caso é normalizado
para nulo indisponível.

Criados no repositório:

- `data_pipeline/contracts/vocacoes-pne-advanced-panel-v1.json`;
- `data_pipeline/contracts/vocacoes-pne-aa1-allowlist.json`;
- `data_pipeline/src/vocacoes_pne_advanced_panel.py`;
- `data_pipeline/scripts/run_vocacoes_pne_advanced_panel.py`;
- `data_pipeline/tests/test_vocacoes_pne_advanced_panel.py`;
- este relatório e a revisão Opus AA1.

O pacote local `.tmp/vocacoes-pne/advanced-analytics-v1/aa1` contém painel, catálogo,
cobertura, reconciliação de grão, auditoria temporal, gate de entrada do AA2,
inventário, QA e manifesto. `public/data` não foi escrito.

O gate `AA2_ENTRY_GATE_AA1.json` é um artefato hashado do pacote. Antes de liberar a
leitura dos resultados, o loader do AA2 deverá conferir o nome do painel, os cinco
campos obrigatórios, os vocabulários fechados, o inventário, a reconciliação de grão,
a auditoria temporal, o digest público e a regra de que somente `RS_497` autoriza
inferência estadual.

## 6. Determinismo, QA e testes

Após todas as correções de código e contrato, inclusive a portabilidade de paths e
o enum de referência seguro para CSV, duas materializações completas foram criadas
do zero por dois processos Python novos, com `PYTHONHASHSEED=101` e `202`, contra a
implementação `213d6e43...`. Nenhum artefato da execução anterior foi reutilizado.
Os dois conjuntos e as duas árvores finais foram idênticos.

Nos dois processos, conexões de socket e SQLite ficaram bloqueadas em runtime;
nenhum cliente conhecido de banco ou HTTP foi carregado. Cada processo calculou o
digest de `public/data` antes e depois e encontrou o mesmo valor protegido.

- 41/41 controles aprovados;
- `uv run python -m pytest data_pipeline/tests/test_vocacoes_pne_advanced_panel.py -vv -s`:
  13/13 em 92,71 s;
- runner `--check`: aprovado, com 177.265 linhas, 96 métricas e 497 municípios;
- baseline AA0 com allowlist AA1: 243 entradas protegidas e sete paths de estágio;
- `npm run check:fast`: typecheck, lint, compilador narrativo e build app-only
  aprovados; existe apenas o aviso conhecido de chunks grandes;
- `git diff --check`: código zero, com avisos LF/CRLF preexistentes.

As sete entradas permitidas são exatamente contrato, allowlist, implementação,
runner, teste, relatório e revisão Opus AA1. A primeira repetição transacional após
o novo metadata contract detectou que `NONE` era lido como ausente pelo CSV; o enum
foi substituído por `NO_EXTERNAL_REFERENCE` e o ciclo escrita/leitura passou.

O painel projetado sobre as 26 colunas anteriores ao adendo tem SHA-256
`1f500c731acecc52ceb2beaee1884a48607ec2f102220b956e5846cc3674fb0a`, exatamente
igual ao painel pré-adendo. As únicas colunas excluídas dessa comparação são
`coverage_reason` e `unavailability_reason`; a contagem de diferenças de valor ou
fórmula é zero.

## 7. Hashes finais

- contrato: `9975620e3ed269be6ac967d1f3c47e65c27e2f4ad644d27b7c2853334adbded8`;
- implementação: `213d6e4372610ede85d4d954b3f175c3ceea644cfe2873f5204957d3c5d728ec`;
- runner: `f99d87731b03fd1fb6703090eb6795b5a90bf8e7e1056ac6726f3162a552aa0f`;
- testes: `1a24795c4448effeeb7be54e42be26ff14015500bc4f25ec1d59f6b19642443d`;
- allowlist: `cd09c191ed39bbccc5f34f313dcbc52c927ba29fcd08a1da19d613da74bb6d77`;
- inventário de fontes: `32849be03876b579ab463d09690f97520253c3828133319da959350ef67f9389`;
- painel GZIP: `d6cadfec911863b93699b826da6ef340687db5c0f77350319a9eeefa0dfb652f`;
- cobertura: `f508f76c31fcf405e83311c2449aa09c3b6006ce9f82017dc85801dcf56a4296`;
- reconciliação de grão: `1fe45affc3a9abf1bbb4f12e092f923b2da269a21f51a8c27e6e1c48dd7babf3`;
- auditoria temporal: `947312850dbbc380d983296cf62f44050e4bf58d65a08eb08057585e4d3b014d`;
- censo/QA: `e8881846aee5d157cee69548f0779e598cbac90ede3be8cdae949ee6ba8dad68`;
- gate AA2: `8baef0754bd6e7b5caa5428e9cf16d8ae3c01d3eace4de68d24d1e42ba286f02`;
- conjunto sem manifesto: `b5209061aff00ecae4b279165f3fd380b9324bcc845d1ad279a31a42f8bd3366`;
- árvore final: `a4cce5d7e833f6ccd55da667e2d47eb4af116741502225b89a215a37d4c2aa6b`;
- `public/data` antes/depois:
  `4a52e3891163cb3427c5c01f2ef5414c5fe7855dd491a9a125b509899dcc23e1`.

## 8. Reconciliação independente e estado operacional

O Opus emitiu `ON_TRACK` no primeiro parecer, `AT_RISK` no segundo depois de uma
auditoria mais exigente e `ON_TRACK` no terceiro parecer delimitado, com confiança
0,72. As dez correções solicitadas no segundo parecer foram aceitas ou
explicitamente reenquadradas. O apêndice final recomendado no terceiro parecer foi
incorporado acima sem modificar valores, fórmulas ou universos. A trilha detalhada
está em `docs/REVISAO_OPUS_AA1_AVANCO_ANALITICO_VOCACOES_PNE.md`.

- Git: `main`, lote anterior sujo e protegido; nenhum commit, push, pull, stash,
  reset ou troca de branch.
- Banco do projeto: não usado.
- Rede para aquisição de dados: não usada.
- Build completo: não executado; somente build app-only.
- Rede externa usada apenas nas três auditorias Opus autorizadas pelo usuário; o
  modelo recebeu pacotes de evidência delimitados e não acessou o repositório.
- Pendência AA1: nenhuma. O AA2 só pode avançar depois de executar e aprovar o gate
  hashado de entrada.
